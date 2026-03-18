"""
db_connection.py
================
Connects to Microsoft Fabric Lakehouse via Delta Lake (deltalake library).
Writes proper Delta tables to Tables/dbo/{table_name} — visible in SQL endpoint & Power BI.
Falls back to parquet in Files/ if deltalake write fails.
"""

import os
import io
import time
import logging

import requests
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────
FABRIC_CLIENT_ID = os.getenv("FABRIC_CLIENT_ID")
FABRIC_CLIENT_SECRET = os.getenv("FABRIC_CLIENT_SECRET")
FABRIC_TENANT_ID = os.getenv("FABRIC_TENANT_ID")
WORKSPACE_NAME = os.getenv("FABRIC_WORKSPACE_NAME", "DPA_PowerPlatform")
LAKEHOUSE_NAME = os.getenv("FABRIC_LAKEHOUSE_NAME", "MC_ProjectManagement_LH")
APP_USER = os.getenv("APP_USER", "unknown")

ONELAKE_DFS = "https://onelake.dfs.fabric.microsoft.com"
ABFSS_BASE = f"abfss://{WORKSPACE_NAME}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_NAME}.Lakehouse"

# ── Token Cache ───────────────────────────────────────────────────────
_token_cache = {}


def _get_token(scope):
    """Get Azure AD token with caching."""
    cached = _token_cache.get(scope)
    if cached and cached["expires"] > time.time():
        return cached["token"]

    resp = requests.post(
        f"https://login.microsoftonline.com/{FABRIC_TENANT_ID}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": FABRIC_CLIENT_ID,
            "client_secret": FABRIC_CLIENT_SECRET,
            "scope": scope,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache[scope] = {
        "token": data["access_token"],
        "expires": time.time() + data.get("expires_in", 3600) - 60,
    }
    return data["access_token"]


def _storage_token():
    return _get_token("https://storage.azure.com/.default")


def _storage_options():
    return {"bearer_token": _storage_token(), "use_fabric_endpoint": "true"}


def _storage_headers():
    return {"Authorization": f"Bearer {_storage_token()}"}


def _onelake_base():
    return f"{ONELAKE_DFS}/{WORKSPACE_NAME}/{LAKEHOUSE_NAME}.Lakehouse"


# ═══════════════════════════════════════════════════════════════════════
#  READ — Delta Lake (with fallback to parquet in Files/)
# ═══════════════════════════════════════════════════════════════════════

def read_table(table_name):
    """
    Read a table. Tries Delta Lake first (Tables/dbo/), 
    then falls back to parquet (Files/app_data/).
    Returns a pandas DataFrame.
    """
    # Try Delta Lake first
    try:
        from deltalake import DeltaTable
        delta_path = f"{ABFSS_BASE}/Tables/dbo/{table_name}"
        dt = DeltaTable(delta_path, storage_options=_storage_options())
        df = dt.to_pandas()
        logger.info("Read %d rows from Delta table %s", len(df), table_name)
        return df
    except Exception as e:
        logger.debug("Delta read failed for %s: %s, trying parquet", table_name, e)

    # Fallback to parquet in Files/
    try:
        url = f"{_onelake_base()}/Files/app_data/{table_name}.parquet"
        resp = requests.get(url, headers=_storage_headers(), timeout=60)
        if resp.status_code == 200:
            df = pd.read_parquet(io.BytesIO(resp.content))
            logger.info("Read %d rows from parquet %s", len(df), table_name)
            return df
    except Exception as e:
        logger.debug("Parquet read also failed for %s: %s", table_name, e)

    return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════
#  WRITE — Delta Lake (with fallback to parquet)
# ═══════════════════════════════════════════════════════════════════════

def write_table(table_name, df):
    """
    Write a DataFrame as a Delta Lake table to Tables/dbo/{table_name}.
    Falls back to parquet in Files/ if Delta write fails.
    """
    # Try Delta Lake write
    try:
        from deltalake import write_deltalake
        delta_path = f"{ABFSS_BASE}/Tables/dbo/{table_name}"
        write_deltalake(
            delta_path, df,
            mode="overwrite",
            storage_options=_storage_options(),
        )
        logger.info("Wrote %d rows to Delta table %s", len(df), table_name)
        return
    except Exception as e:
        logger.warning("Delta write failed for %s: %s, falling back to parquet", table_name, e)

    # Fallback to parquet
    _write_parquet_fallback(table_name, df)


def _write_parquet_fallback(table_name, df):
    """Write as parquet to Files/app_data/ (fallback)."""
    url = f"{_onelake_base()}/Files/app_data/{table_name}.parquet"
    headers = _storage_headers()
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    parquet_bytes = buf.getvalue()

    try:
        requests.delete(url, headers=headers, timeout=15)
    except Exception:
        pass

    requests.put(url, headers={**headers, "Content-Length": "0"},
        params={"resource": "file"}, timeout=15).raise_for_status()
    requests.patch(url, headers={**headers, "Content-Length": str(len(parquet_bytes)),
        "Content-Type": "application/octet-stream"},
        params={"action": "append", "position": "0"},
        data=parquet_bytes, timeout=30).raise_for_status()
    requests.patch(url, headers=headers,
        params={"action": "flush", "position": str(len(parquet_bytes))},
        timeout=15).raise_for_status()
    logger.info("Wrote %d rows to parquet %s (fallback)", len(df), table_name)


def append_row(table_name, row_dict):
    """Append a single row. Ensures consistent schema across all rows."""
    existing = read_table(table_name)
    new_row = pd.DataFrame([row_dict])

    if existing.empty:
        combined = new_row
    else:
        # Ensure both DataFrames have the same columns
        all_cols = list(dict.fromkeys(list(existing.columns) + list(new_row.columns)))
        for col in all_cols:
            if col not in existing.columns:
                existing[col] = ""
            if col not in new_row.columns:
                new_row[col] = ""
        # Reorder to match
        new_row = new_row[all_cols]
        existing = existing[all_cols]
        combined = pd.concat([existing, new_row], ignore_index=True)

    # Fill any NaN with empty string to prevent schema issues
    combined = combined.fillna("")
    write_table(table_name, combined)
    return len(combined)


def update_table(table_name, df):
    """Replace entire table."""
    write_table(table_name, df)


# ═══════════════════════════════════════════════════════════════════════
#  CONNECTION TEST
# ═══════════════════════════════════════════════════════════════════════

def test_connection():
    """Test OneLake connectivity."""
    try:
        url = f"{_onelake_base()}/Files"
        resp = requests.get(url, headers=_storage_headers(),
            params={"resource": "filesystem", "recursive": "false"}, timeout=15)
        return resp.status_code == 200
    except Exception as e:
        logger.error("Connection test failed: %s", e)
        return False


if __name__ == "__main__":
    print(f"Workspace:  {WORKSPACE_NAME}")
    print(f"Lakehouse:  {LAKEHOUSE_NAME}")
    print(f"Delta path: {ABFSS_BASE}/Tables/dbo/")
    print()
    if test_connection():
        print("SUCCESS - Connected!")
        df = read_table("Lookups")
        if not df.empty:
            print(f"Lookups: {len(df)} rows")
        else:
            print("Lookups: empty or not created yet")
    else:
        print("FAILED")

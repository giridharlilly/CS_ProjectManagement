"""
db_connection.py
================
Connects to Microsoft Fabric Lakehouse via OneLake HTTPS API.

Data is stored in Files/app_data/ as parquet files.
To access from Power BI, use OneLake shortcut or direct parquet connection.

Data paths:
  - Files/app_data/Lookups.parquet
  - Files/app_data/Projects.parquet
  - Files/app_data/ResourceUtilization.parquet
"""

import os
import io
import time
import logging

import requests
import pandas as pd
import pyarrow.parquet as pq

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
DATA_FOLDER = "Files/app_data"

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


def _storage_headers():
    return {"Authorization": f"Bearer {_get_token('https://storage.azure.com/.default')}"}


def _onelake_base():
    return f"{ONELAKE_DFS}/{WORKSPACE_NAME}/{LAKEHOUSE_NAME}.Lakehouse"


def _file_url(table_name):
    return f"{_onelake_base()}/{DATA_FOLDER}/{table_name}.parquet"


# ═══════════════════════════════════════════════════════════════════════
#  READ
# ═══════════════════════════════════════════════════════════════════════

def read_table(table_name):
    """
    Read a parquet file from Files/app_data/{table_name}.parquet.
    Returns a pandas DataFrame.
    """
    url = _file_url(table_name)
    resp = requests.get(url, headers=_storage_headers(), timeout=60)
    if resp.status_code == 404:
        return pd.DataFrame()
    resp.raise_for_status()
    return pd.read_parquet(io.BytesIO(resp.content))


# ═══════════════════════════════════════════════════════════════════════
#  WRITE
# ═══════════════════════════════════════════════════════════════════════

def write_table(table_name, df):
    """
    Write a DataFrame to Files/app_data/{table_name}.parquet.
    Overwrites the existing file.
    """
    url = _file_url(table_name)
    headers = _storage_headers()

    # Convert to parquet bytes
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    parquet_bytes = buf.getvalue()

    # Delete existing file (ignore if not found)
    try:
        requests.delete(url, headers=headers, timeout=15)
    except Exception:
        pass

    # Create file
    requests.put(
        url,
        headers={**headers, "Content-Length": "0"},
        params={"resource": "file"},
        timeout=15,
    ).raise_for_status()

    # Upload data
    requests.patch(
        url,
        headers={**headers, "Content-Length": str(len(parquet_bytes)),
                 "Content-Type": "application/octet-stream"},
        params={"action": "append", "position": "0"},
        data=parquet_bytes,
        timeout=30,
    ).raise_for_status()

    # Flush
    requests.patch(
        url,
        headers=headers,
        params={"action": "flush", "position": str(len(parquet_bytes))},
        timeout=15,
    ).raise_for_status()

    logger.info("Wrote %d rows to %s/%s.parquet", len(df), DATA_FOLDER, table_name)


def append_row(table_name, row_dict):
    """Append a single row. Reads existing data, appends, writes back."""
    existing = read_table(table_name)
    new_row = pd.DataFrame([row_dict])
    combined = pd.concat([existing, new_row], ignore_index=True) if not existing.empty else new_row
    write_table(table_name, combined)
    return len(combined)


def update_table(table_name, df):
    """Replace entire table."""
    write_table(table_name, df)


# ═══════════════════════════════════════════════════════════════════════
#  CLEANUP: Remove unidentified tables from Tables folder
# ═══════════════════════════════════════════════════════════════════════

def cleanup_tables_folder():
    """Remove any files accidentally written to Tables/ folder."""
    headers = _storage_headers()
    base = _onelake_base()
    for name in ["Lookups", "TestTable", "dbo/TestTable"]:
        try:
            requests.delete(f"{base}/Tables/{name}",
                          headers=headers, params={"recursive": "true"}, timeout=15)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════
#  CONNECTION TEST
# ═══════════════════════════════════════════════════════════════════════

def test_connection():
    """Test OneLake connectivity."""
    try:
        url = f"{_onelake_base()}/Files"
        resp = requests.get(
            url, headers=_storage_headers(),
            params={"resource": "filesystem", "recursive": "false"},
            timeout=15,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error("Connection test failed: %s", e)
        return False


if __name__ == "__main__":
    print(f"Workspace:  {WORKSPACE_NAME}")
    print(f"Lakehouse:  {LAKEHOUSE_NAME}")
    print(f"Data path:  {DATA_FOLDER}/")
    print()
    if test_connection():
        print("SUCCESS - Connected!")
        df = read_table("Lookups")
        if not df.empty:
            print(f"Lookups: {len(df)} rows")
            print(df.head())
        else:
            print("Lookups: empty")
    else:
        print("FAILED")

"""
db_connection.py
================
Connects to Microsoft Fabric Lakehouse via OneLake HTTPS API.
Writes to the Tables folder so data appears in the SQL analytics endpoint
and Power BI can query it directly.

Data paths:
  - Tables/Lookups/          → dropdown values (visible in Power BI)
  - Tables/Projects/         → project data (visible in Power BI)
  - Tables/ResourceUtilization/ → resource data (visible in Power BI)
"""

import os
import io
import time
import logging
from datetime import datetime, timezone

import requests
import pandas as pd
import pyarrow as pa
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


# ═══════════════════════════════════════════════════════════════════════
#  READ OPERATIONS
# ═══════════════════════════════════════════════════════════════════════

def _list_files(path):
    """List files at an OneLake path."""
    url = f"{_onelake_base()}/{path}"
    resp = requests.get(
        url,
        headers=_storage_headers(),
        params={"resource": "filesystem", "recursive": "true"},
        timeout=30,
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("paths", [])


def _read_file(path):
    """Read a file from OneLake, returns bytes."""
    url = f"{_onelake_base()}/{path}"
    resp = requests.get(url, headers=_storage_headers(), timeout=60)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.content


def read_table(table_name):
    """
    Read a table from the Lakehouse Tables folder.
    Reads all parquet files in Tables/{table_name}/ and returns a DataFrame.
    """
    table_path = f"Tables/{table_name}"
    files = _list_files(table_path)
    parquet_files = [
        f["name"] for f in files
        if f["name"].endswith(".parquet") and not f.get("isDirectory")
    ]

    if not parquet_files:
        return pd.DataFrame()

    dfs = []
    for pf in parquet_files:
        file_bytes = _read_file(pf)
        if file_bytes:
            df = pd.read_parquet(io.BytesIO(file_bytes))
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════
#  WRITE OPERATIONS — writes to Tables/ folder
# ═══════════════════════════════════════════════════════════════════════

def _upload_file(path, data_bytes):
    """Upload a file to OneLake (create + append + flush)."""
    url = f"{_onelake_base()}/{path}"
    headers = _storage_headers()

    # Create file
    requests.put(
        url,
        headers={**headers, "Content-Length": "0"},
        params={"resource": "file"},
        timeout=30,
    ).raise_for_status()

    # Append data
    requests.patch(
        url,
        headers={**headers, "Content-Length": str(len(data_bytes)), "Content-Type": "application/octet-stream"},
        params={"action": "append", "position": "0"},
        data=data_bytes,
        timeout=60,
    ).raise_for_status()

    # Flush
    requests.patch(
        url,
        headers=headers,
        params={"action": "flush", "position": str(len(data_bytes))},
        timeout=30,
    ).raise_for_status()


def _delete_file(path):
    """Delete a file from OneLake."""
    url = f"{_onelake_base()}/{path}"
    try:
        resp = requests.delete(url, headers=_storage_headers(), params={"recursive": "true"}, timeout=30)
    except Exception:
        pass


def _df_to_parquet_bytes(df):
    """Convert DataFrame to parquet bytes."""
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    return buf.getvalue()


def write_table(table_name, df):
    """
    Write/overwrite a table in the Lakehouse Tables folder.
    Writes a single parquet file to: Tables/{table_name}/data.parquet

    This makes the table visible in:
    - Lakehouse SQL analytics endpoint
    - Power BI
    - Any SQL query tool
    """
    # Delete existing data file first (overwrite)
    _delete_file(f"Tables/{table_name}/data.parquet")

    # Write new data
    path = f"Tables/{table_name}/data.parquet"
    parquet_bytes = _df_to_parquet_bytes(df)
    _upload_file(path, parquet_bytes)
    logger.info("Wrote %d rows to Tables/%s", len(df), table_name)


def append_row(table_name, row_dict):
    """
    Append a single row to an existing table.
    Reads current data from Tables folder, appends the row, writes back.
    """
    existing = read_table(table_name)
    new_row = pd.DataFrame([row_dict])

    if existing.empty:
        combined = new_row
    else:
        combined = pd.concat([existing, new_row], ignore_index=True)

    write_table(table_name, combined)
    return len(combined)


def update_table(table_name, df):
    """
    Replace entire table with new data.
    Used for editing/deleting rows.
    """
    write_table(table_name, df)


# ═══════════════════════════════════════════════════════════════════════
#  CONNECTION TEST
# ═══════════════════════════════════════════════════════════════════════

def test_connection():
    """Test OneLake connectivity."""
    try:
        url = f"{_onelake_base()}/Tables"
        resp = requests.get(
            url,
            headers=_storage_headers(),
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
    print(f"Method:     OneLake HTTPS (port 443)")
    print(f"Data path:  Tables/ (visible in Power BI)")
    print()
    if test_connection():
        print("SUCCESS - Connected to Lakehouse!")
    else:
        print("FAILED - Check credentials.")

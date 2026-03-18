"""
db_operations.py - CRUD operations for Medical Creatives app.
Data stored as Delta Lake tables in Files/delta/
"""

import os
import uuid
import logging
from datetime import datetime, timezone

import pandas as pd
from db_connection import read_table, write_table, append_row, test_connection

logger = logging.getLogger(__name__)
APP_USER = os.getenv("APP_USER", "unknown")

PROJECTS_TABLE = "Projects"
RESOURCE_TABLE = "ResourceUtilization"
LOOKUPS_TABLE = "Lookups"

# ── Cache ─────────────────────────────────────────────────────────────
_cache = {}
_cache_ts = {}
CACHE_TTL = 300

def _get_cached(table_name, force_refresh=False):
    now = datetime.now().timestamp()
    if not force_refresh and table_name in _cache and (now - _cache_ts.get(table_name, 0)) < CACHE_TTL:
        return _cache[table_name].copy()
    df = read_table(table_name)
    _cache[table_name] = df
    _cache_ts[table_name] = now
    return df.copy()

def clear_cache(table_name=None):
    if table_name:
        _cache.pop(table_name, None)
        _cache_ts.pop(table_name, None)
    else:
        _cache.clear()
        _cache_ts.clear()

# ── Lookups ───────────────────────────────────────────────────────────
def get_lookup_values(field_name):
    df = _get_cached(LOOKUPS_TABLE)
    if df.empty or "FieldName" not in df.columns: return []
    return df[df["FieldName"] == field_name].sort_values("Value")["Value"].tolist()

def get_dropdown_options(field_name):
    return [{"label": v, "value": v} for v in get_lookup_values(field_name)]

def save_lookup_values(field_name, values_list):
    df = _get_cached(LOOKUPS_TABLE, force_refresh=True)
    if not df.empty: df = df[df["FieldName"] != field_name]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    new = pd.DataFrame({"FieldName": [field_name]*len(values_list), "Value": values_list,
        "UpdatedBy": [APP_USER]*len(values_list), "UpdatedAt": [now]*len(values_list)})
    write_table(LOOKUPS_TABLE, pd.concat([df, new], ignore_index=True))
    clear_cache(LOOKUPS_TABLE)

def get_all_lookup_fields():
    df = _get_cached(LOOKUPS_TABLE)
    return sorted(df["FieldName"].unique().tolist()) if not df.empty else []

# ── Projects ──────────────────────────────────────────────────────────
def get_all_projects(force_refresh=False):
    return _get_cached(PROJECTS_TABLE, force_refresh)

def submit_project(form_data):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    form_data.update({"RowID": str(uuid.uuid4()), "CreatedBy": APP_USER, "CreatedAt": now,
        "UpdatedBy": APP_USER, "UpdatedAt": now})
    # Keep ALL columns — replace None with empty string so schema stays consistent
    form_data = {k: ("" if v is None else v) for k, v in form_data.items()}
    try:
        append_row(PROJECTS_TABLE, form_data)
        clear_cache(PROJECTS_TABLE)
        return {"status": "success", "message": "Project saved!"}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}

def update_project(row_id, changes):
    df = _get_cached(PROJECTS_TABLE, force_refresh=True)
    if df.empty: return {"status": "error", "message": "No projects"}
    mask = df["RowID"] == row_id
    if mask.sum() == 0: return {"status": "error", "message": "Not found"}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for col, val in changes.items():
        if col in df.columns:
            col_dtype = df[col].dtype
            try:
                if pd.api.types.is_integer_dtype(col_dtype):
                    val = int(float(val)) if val and str(val).strip() else 0
                elif pd.api.types.is_float_dtype(col_dtype):
                    val = float(val) if val and str(val).strip() else 0.0
            except (ValueError, TypeError):
                val = str(val)
        df.loc[mask, col] = val
    df.loc[mask, "UpdatedBy"] = APP_USER
    df.loc[mask, "UpdatedAt"] = now
    write_table(PROJECTS_TABLE, df)
    clear_cache(PROJECTS_TABLE)
    return {"status": "success", "message": "Project updated!"}

def delete_project(row_id):
    df = _get_cached(PROJECTS_TABLE, force_refresh=True)
    df = df[df["RowID"] != row_id]
    write_table(PROJECTS_TABLE, df)
    clear_cache(PROJECTS_TABLE)
    return {"status": "success", "message": "Deleted!"}

# ── Resource Utilization ──────────────────────────────────────────────
def get_all_resources(force_refresh=False):
    return _get_cached(RESOURCE_TABLE, force_refresh)

def submit_resource(form_data):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    form_data.update({"RowID": str(uuid.uuid4()), "CreatedBy": APP_USER, "CreatedAt": now,
        "UpdatedBy": APP_USER, "UpdatedAt": now})
    # Keep ALL columns — replace None with empty string so schema stays consistent
    form_data = {k: ("" if v is None else v) for k, v in form_data.items()}
    try:
        append_row(RESOURCE_TABLE, form_data)
        clear_cache(RESOURCE_TABLE)
        return {"status": "success", "message": "Entry saved!"}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}

def delete_resource(row_id):
    df = _get_cached(RESOURCE_TABLE, force_refresh=True)
    df = df[df["RowID"] != row_id]
    write_table(RESOURCE_TABLE, df)
    clear_cache(RESOURCE_TABLE)
    return {"status": "success", "message": "Deleted!"}

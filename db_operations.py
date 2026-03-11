"""
db_operations.py
================
CRUD operations for the Medical Creatives app.
All data is stored in the Lakehouse Tables/ folder so it's visible in Power BI.

Tables:
  - Tables/Lookups/         → dropdown values
  - Tables/Projects/        → project data
  - Tables/ResourceUtilization/ → resource tracking data
"""

import os
import uuid
import logging
from datetime import datetime, timezone

import pandas as pd
from db_connection import read_table, write_table, append_row, test_connection

logger = logging.getLogger(__name__)
APP_USER = os.getenv("APP_USER", "unknown")

# ── Table names (stored in Tables/ folder) ────────────────────────────
PROJECTS_TABLE = "Projects"
RESOURCE_TABLE = "ResourceUtilization"
LOOKUPS_TABLE = "Lookups"


# ═══════════════════════════════════════════════════════════════════════
#  DATA CACHE (for performance)
# ═══════════════════════════════════════════════════════════════════════

_cache = {}
_cache_ts = {}
CACHE_TTL = 300  # 5 minutes


def _get_cached(table_name, force_refresh=False):
    """Read table with caching."""
    now = datetime.now().timestamp()
    if not force_refresh and table_name in _cache and (now - _cache_ts.get(table_name, 0)) < CACHE_TTL:
        return _cache[table_name].copy()

    df = read_table(table_name)
    _cache[table_name] = df
    _cache_ts[table_name] = now
    return df.copy()


def clear_cache(table_name=None):
    """Clear cache for a specific table or all tables."""
    if table_name:
        _cache.pop(table_name, None)
        _cache_ts.pop(table_name, None)
    else:
        _cache.clear()
        _cache_ts.clear()


# ═══════════════════════════════════════════════════════════════════════
#  LOOKUP / DROPDOWN OPERATIONS
# ═══════════════════════════════════════════════════════════════════════

def get_lookup_values(field_name):
    """
    Get dropdown options for a field.
    Returns list of strings.
    """
    df = _get_cached(LOOKUPS_TABLE)
    if df.empty:
        return []
    filtered = df[df["FieldName"] == field_name].sort_values("Value")
    return filtered["Value"].tolist()


def get_dropdown_options(field_name):
    """
    Get dropdown options formatted for Dash dcc.Dropdown.
    Returns [{"label": "...", "value": "..."}, ...]
    """
    values = get_lookup_values(field_name)
    return [{"label": v, "value": v} for v in values]


def save_lookup_values(field_name, values_list):
    """
    Save/overwrite all dropdown values for a field.
    values_list: list of strings.
    """
    df = _get_cached(LOOKUPS_TABLE, force_refresh=True)

    # Remove existing values for this field
    if not df.empty:
        df = df[df["FieldName"] != field_name]

    # Add new values
    new_rows = pd.DataFrame({
        "FieldName": [field_name] * len(values_list),
        "Value": values_list,
        "UpdatedBy": [APP_USER] * len(values_list),
        "UpdatedAt": [datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")] * len(values_list),
    })

    combined = pd.concat([df, new_rows], ignore_index=True)
    write_table(LOOKUPS_TABLE, combined)
    clear_cache(LOOKUPS_TABLE)


def get_all_lookup_fields():
    """Get list of all field names that have lookup values."""
    df = _get_cached(LOOKUPS_TABLE)
    if df.empty:
        return []
    return sorted(df["FieldName"].unique().tolist())


def initialize_default_lookups():
    """
    Initialize lookup table with default dropdown values.
    Only runs if the lookup table is empty.
    """
    df = _get_cached(LOOKUPS_TABLE, force_refresh=True)
    if not df.empty:
        return  # Already initialized

    defaults = {
        "BU": ["Oncology", "Immunology", "Neuroscience", "Diabetes", "Cardiology", "Other"],
        "ProjectType": ["New", "Revision", "Derivative", "Archive"],
        "ClassificationMedia": ["Digital", "Print", "Video", "Social Media", "Email", "Other"],
        "TacticType": ["Banner Ad", "Email", "Brochure", "Sell Sheet", "Detail Aid", "Video", "Social Post", "Other"],
        "InternalStatus": ["Not Started", "In Progress", "In Review", "Approved", "On Hold", "Completed", "Cancelled"],
        "AssignerName": [],
        "DesignerAssigned": [],
        "QCReviewer": [],
        "MailSent": ["Yes", "No", "N/A"],
        "TacticStage": ["Draft", "Review", "Final", "Approved", "Published"],
        "Stakeholder": [],
        "Complexity": ["Simple", "Medium", "Complex"],
        "ContentStatus": ["Draft", "In Review", "Approved", "Published", "Archived"],
        "Revision1": ["Yes", "No", "N/A"],
        "Revision2": ["Yes", "No", "N/A"],
        "Revision3OrMore": ["Yes", "No", "N/A"],
    }

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for field, values in defaults.items():
        for v in values:
            rows.append({
                "FieldName": field,
                "Value": v,
                "UpdatedBy": APP_USER,
                "UpdatedAt": now,
            })

    if rows:
        df = pd.DataFrame(rows)
        write_table(LOOKUPS_TABLE, df)
        clear_cache(LOOKUPS_TABLE)


# ═══════════════════════════════════════════════════════════════════════
#  PROJECTS OPERATIONS
# ═══════════════════════════════════════════════════════════════════════

def get_all_projects(force_refresh=False):
    """Get all projects as DataFrame."""
    return _get_cached(PROJECTS_TABLE, force_refresh)


def submit_project(form_data):
    """
    Submit a new project row.
    form_data: dict of field_name → value
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    form_data["RowID"] = str(uuid.uuid4())
    form_data["CreatedBy"] = APP_USER
    form_data["CreatedAt"] = now
    form_data["UpdatedBy"] = APP_USER
    form_data["UpdatedAt"] = now

    # Remove None values
    form_data = {k: v for k, v in form_data.items() if v is not None}

    try:
        append_row(PROJECTS_TABLE, form_data)
        clear_cache(PROJECTS_TABLE)
        return {"status": "success", "message": "Project saved successfully!"}
    except Exception as e:
        logger.error("submit_project failed: %s", e)
        return {"status": "error", "message": f"Failed to save: {str(e)}"}


def update_project(row_id, changes):
    """Update a project row by RowID."""
    df = _get_cached(PROJECTS_TABLE, force_refresh=True)
    if df.empty:
        return {"status": "error", "message": "No projects found"}

    mask = df["RowID"] == row_id
    if mask.sum() == 0:
        return {"status": "error", "message": f"Row {row_id} not found"}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for col, val in changes.items():
        df.loc[mask, col] = val
    df.loc[mask, "UpdatedBy"] = APP_USER
    df.loc[mask, "UpdatedAt"] = now

    write_table(PROJECTS_TABLE, df)
    clear_cache(PROJECTS_TABLE)
    return {"status": "success", "message": "Project updated!"}


def delete_project(row_id):
    """Delete a project row by RowID."""
    df = _get_cached(PROJECTS_TABLE, force_refresh=True)
    df = df[df["RowID"] != row_id]
    write_table(PROJECTS_TABLE, df)
    clear_cache(PROJECTS_TABLE)
    return {"status": "success", "message": "Project deleted!"}


# ═══════════════════════════════════════════════════════════════════════
#  RESOURCE UTILIZATION OPERATIONS
# ═══════════════════════════════════════════════════════════════════════

def get_all_resources(force_refresh=False):
    """Get all resource utilization entries."""
    return _get_cached(RESOURCE_TABLE, force_refresh)


def submit_resource(form_data):
    """Submit a new resource utilization entry."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    form_data["RowID"] = str(uuid.uuid4())
    form_data["CreatedBy"] = APP_USER
    form_data["CreatedAt"] = now
    form_data["UpdatedBy"] = APP_USER
    form_data["UpdatedAt"] = now

    form_data = {k: v for k, v in form_data.items() if v is not None}

    try:
        append_row(RESOURCE_TABLE, form_data)
        clear_cache(RESOURCE_TABLE)
        return {"status": "success", "message": "Resource entry saved!"}
    except Exception as e:
        logger.error("submit_resource failed: %s", e)
        return {"status": "error", "message": f"Failed to save: {str(e)}"}


def delete_resource(row_id):
    """Delete a resource entry by RowID."""
    df = _get_cached(RESOURCE_TABLE, force_refresh=True)
    df = df[df["RowID"] != row_id]
    write_table(RESOURCE_TABLE, df)
    clear_cache(RESOURCE_TABLE)
    return {"status": "success", "message": "Entry deleted!"}

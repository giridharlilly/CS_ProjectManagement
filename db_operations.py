"""
db_operations.py — CRUD + QC Auto-Assignment
=============================================
Includes VBA macro logic: when InternalStatus = "Move to QC",
auto-assign QC Reviewer with lowest count (excluding designer).
"""

import os, uuid, logging
from datetime import datetime, timezone
import pandas as pd
from db_connection import read_table, write_table, append_row, test_connection

logger = logging.getLogger(__name__)
APP_USER = os.getenv("APP_USER", "unknown")

PROJECTS_TABLE = "Projects"
RESOURCE_TABLE = "ResourceUtilization"
LOOKUPS_TABLE = "Lookups"
REVIEWER_STATE_TABLE = "ReviewerState"

# ── Cache ─────────────────────────────────────────────────────────────
_cache = {}
_cache_ts = {}
CACHE_TTL = 300

def _get_cached(tn, force=False):
    now = datetime.now().timestamp()
    if not force and tn in _cache and (now - _cache_ts.get(tn, 0)) < CACHE_TTL:
        return _cache[tn].copy()
    df = read_table(tn)
    _cache[tn] = df
    _cache_ts[tn] = now
    return df.copy()

def clear_cache(tn=None):
    if tn:
        _cache.pop(tn, None); _cache_ts.pop(tn, None)
    else:
        _cache.clear(); _cache_ts.clear()

# ── Numeric fields ────────────────────────────────────────────────────
NUMERIC_FIELDS = {
    "PageSlide", "GDReworkPct", "POCReworkPct",
    # Revision groups (11 revisions x 7 fields each)
    "R1_Asset", "R1_Total", "R1_GDRework", "R1_POCRework", "R1_Simple", "R1_Medium", "R1_Complex", "R1_Derivatives",
    "R2_Total", "R2_GDRework", "R2_POCRework", "R2_Simple", "R2_Medium", "R2_Complex", "R2_Derivatives",
    "R3_Total", "R3_GDRework", "R3_POCRework", "R3_Simple", "R3_Medium", "R3_Complex", "R3_Derivatives",
    "R4_Total", "R4_GDRework", "R4_POCRework", "R4_Simple", "R4_Medium", "R4_Complex", "R4_Derivatives",
    "R5_Total", "R5_GDRework", "R5_POCRework",
    "R6_Total", "R6_GDRework", "R6_POCRework",
    "R7_Total", "R7_GDRework", "R7_POCRework",
    "R8_Total", "R8_GDRework", "R8_POCRework",
    "R9_Total", "R9_GDRework", "R9_POCRework",
    "R10_Total", "R10_GDRework", "R10_POCRework",
    "R11_Total", "R11_GDRework", "R11_POCRework",
    "TotalAssets", "TotalGDRework", "TotalPOCRework",
    # Resource fields
    "ProjectTaskNA", "StakeholderTouchpoints", "InternalTeamMeetings", "GCHTrainings",
    "ToolsTechTesting", "InnovationProcessImprovement", "CrossFunctionalSupports",
    "SiteGCHActivities", "TownhallsHRIT", "OneOne", "SuccessFactorLinkedIn",
    "OtherTrainings", "HiringOnboarding", "LeavesHolidays", "OpenTime", "TotalHours",
}

def _clean(data):
    cleaned = {}
    for k, v in data.items():
        if v is None or v == "":
            cleaned[k] = 0 if k in NUMERIC_FIELDS else ""
        elif k in NUMERIC_FIELDS:
            try: cleaned[k] = float(v) if "." in str(v) else int(v)
            except: cleaned[k] = 0
        else:
            cleaned[k] = v
    return cleaned

# ── Lookups ───────────────────────────────────────────────────────────
def get_lookup_values(fn):
    df = _get_cached(LOOKUPS_TABLE)
    if df.empty or "FieldName" not in df.columns: return []
    return df[df["FieldName"] == fn].sort_values("Value")["Value"].tolist()

def get_dropdown_options(fn):
    return [{"label": v, "value": v} for v in get_lookup_values(fn)]

def save_lookup_values(fn, vals):
    df = _get_cached(LOOKUPS_TABLE, force=True)
    if not df.empty: df = df[df["FieldName"] != fn]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    new = pd.DataFrame({"FieldName": [fn]*len(vals), "Value": vals,
        "UpdatedBy": [APP_USER]*len(vals), "UpdatedAt": [now]*len(vals)})
    write_table(LOOKUPS_TABLE, pd.concat([df, new], ignore_index=True))
    clear_cache(LOOKUPS_TABLE)

def get_all_lookup_fields():
    df = _get_cached(LOOKUPS_TABLE)
    return sorted(df["FieldName"].unique().tolist()) if not df.empty else []

# ═══════════════════════════════════════════════════════════════════════
#  QC REVIEWER AUTO-ASSIGNMENT (translated from VBA macro)
# ═══════════════════════════════════════════════════════════════════════

# Reviewer -> Email mapping
REVIEWER_EMAILS = {
    "Anoosha Gopinath": "gopinath_anoosha@lilly.com",
    "Aswin VM": "v_m_aswin@lilly.com",
    "Karthikeyan M": "m_kartikeyan@lilly.com",
    "Muthamilselvan Uthandam": "uthandam_muthamilselvan@lilly.com",
    "Shashi Vishwakarma": "vishwakarma_shashi@lilly.com",
    "Subhajit Das": "subhajitdas@lilly.com",
    "Vinothkumar A": "a_vinoth_kumar@lilly.com",
    "Chandesh Sirasapalli": "sirasapalli.chandesh@lilly.com",
    "Manoj K": "manoj.k@lilly.com",
}

def _get_reviewer_state():
    """Get or initialize reviewer assignment counts."""
    df = _get_cached(REVIEWER_STATE_TABLE, force=True)
    if df.empty or "Reviewer" not in df.columns:
        # Initialize with all reviewers at count 0
        reviewers = sorted(REVIEWER_EMAILS.keys())
        df = pd.DataFrame({"Reviewer": reviewers, "Count": [0]*len(reviewers)})
        write_table(REVIEWER_STATE_TABLE, df)
        clear_cache(REVIEWER_STATE_TABLE)
    return df

def assign_qc_reviewer(designer_name):
    """
    Auto-assign QC reviewer (VBA macro logic):
    1. Get all reviewers sorted alphabetically
    2. Find reviewer with LOWEST assignment count
    3. Skip the designer (reviewer != designer)
    4. On tie, pick first alphabetically
    5. Increment count and save
    Returns: (reviewer_name, reviewer_email)
    """
    state = _get_reviewer_state()
    designer_upper = str(designer_name).upper().strip()

    # Filter out the designer
    eligible = state[state["Reviewer"].str.upper().str.strip() != designer_upper].copy()
    if eligible.empty:
        return "", ""

    # Ensure Count is numeric
    eligible["Count"] = pd.to_numeric(eligible["Count"], errors="coerce").fillna(0).astype(int)

    # Find minimum count
    min_count = eligible["Count"].min()
    candidates = eligible[eligible["Count"] == min_count]

    # Tie-break: first alphabetically (already sorted)
    chosen = candidates.iloc[0]
    reviewer_name = chosen["Reviewer"]

    # Increment count in state
    state.loc[state["Reviewer"] == reviewer_name, "Count"] = int(chosen["Count"]) + 1
    write_table(REVIEWER_STATE_TABLE, state)
    clear_cache(REVIEWER_STATE_TABLE)

    email = REVIEWER_EMAILS.get(reviewer_name, "")
    return reviewer_name, email

# ═══════════════════════════════════════════════════════════════════════
#  PROJECTS
# ═══════════════════════════════════════════════════════════════════════

def get_all_projects(force=False):
    return _get_cached(PROJECTS_TABLE, force)

def submit_project(form_data):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    form_data.update({"RowID": str(uuid.uuid4()), "CreatedBy": APP_USER,
        "CreatedAt": now, "UpdatedBy": APP_USER, "UpdatedAt": now})

    # Auto-assign QC when status is "Move to QC"
    if str(form_data.get("InternalStatus", "")).strip().upper() == "MOVE TO QC":
        designer = form_data.get("DesignerAssigned", "")
        if designer:
            qc_name, qc_email = assign_qc_reviewer(designer)
            form_data["QCReviewer"] = qc_name
            form_data["QCEmailer"] = qc_email

    # Calculate totals
    form_data = _calc_project_totals(form_data)
    form_data = _clean(form_data)
    try:
        append_row(PROJECTS_TABLE, form_data)
        clear_cache(PROJECTS_TABLE)
        qc_msg = ""
        if form_data.get("QCReviewer"):
            qc_msg = f" QC assigned: {form_data['QCReviewer']}"
        return {"status": "success", "message": f"Project saved!{qc_msg}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}

def _calc_project_totals(d):
    """Calculate Total Assets, Total GD Rework, Total POC Rework, GD%, POC%"""
    def _int(v):
        try: return int(float(v)) if v and str(v).strip() else 0
        except: return 0

    # Sum all revision totals
    total_assets = 0
    total_gd = 0
    total_poc = 0
    for i in range(1, 12):
        total_assets += _int(d.get(f"R{i}_Total", 0))
        total_gd += _int(d.get(f"R{i}_GDRework", 0))
        total_poc += _int(d.get(f"R{i}_POCRework", 0))
    # Also add R1_Asset
    total_assets += _int(d.get("R1_Asset", 0))

    d["TotalAssets"] = total_assets
    d["TotalGDRework"] = total_gd
    d["TotalPOCRework"] = total_poc
    d["GDReworkPct"] = round(total_gd / total_assets * 100, 1) if total_assets > 0 else 0
    d["POCReworkPct"] = round(total_poc / total_assets * 100, 1) if total_assets > 0 else 0
    return d

def update_project(row_id, changes):
    df = _get_cached(PROJECTS_TABLE, force=True)
    if df.empty: return {"status": "error", "message": "No projects"}
    mask = df["RowID"] == row_id
    if mask.sum() == 0: return {"status": "error", "message": "Not found"}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Check if status changed to "Move to QC"
    old_status = str(df.loc[mask, "InternalStatus"].values[0]) if "InternalStatus" in df.columns else ""
    new_status = changes.get("InternalStatus", old_status)
    if str(new_status).strip().upper() == "MOVE TO QC" and old_status.strip().upper() != "MOVE TO QC":
        designer = changes.get("DesignerAssigned", str(df.loc[mask, "DesignerAssigned"].values[0]) if "DesignerAssigned" in df.columns else "")
        if designer:
            qc_name, qc_email = assign_qc_reviewer(designer)
            changes["QCReviewer"] = qc_name
            changes["QCEmailer"] = qc_email

    for col, val in changes.items():
        if col in df.columns:
            col_dtype = df[col].dtype
            try:
                if pd.api.types.is_integer_dtype(col_dtype):
                    val = int(float(val)) if val and str(val).strip() else 0
                elif pd.api.types.is_float_dtype(col_dtype):
                    val = float(val) if val and str(val).strip() else 0.0
            except: val = str(val)
        df.loc[mask, col] = val
    df.loc[mask, "UpdatedBy"] = APP_USER
    df.loc[mask, "UpdatedAt"] = now
    write_table(PROJECTS_TABLE, df)
    clear_cache(PROJECTS_TABLE)
    qc_msg = ""
    if "QCReviewer" in changes and changes["QCReviewer"]:
        qc_msg = f" QC assigned: {changes['QCReviewer']}"
    return {"status": "success", "message": f"Project updated!{qc_msg}"}

def delete_project(row_id):
    df = _get_cached(PROJECTS_TABLE, force=True)
    df = df[df["RowID"] != row_id]
    write_table(PROJECTS_TABLE, df)
    clear_cache(PROJECTS_TABLE)
    return {"status": "success", "message": "Deleted!"}

# ═══════════════════════════════════════════════════════════════════════
#  RESOURCE UTILIZATION
# ═══════════════════════════════════════════════════════════════════════

def get_all_resources(force_refresh=False):
    return _get_cached(RESOURCE_TABLE, force_refresh)

def submit_resource(form_data):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    form_data.update({"RowID": str(uuid.uuid4()), "CreatedBy": APP_USER,
        "CreatedAt": now, "UpdatedBy": APP_USER, "UpdatedAt": now})

    # Auto-calculate TotalHours
    hour_fields = ["ProjectTaskNA", "StakeholderTouchpoints", "InternalTeamMeetings",
        "GCHTrainings", "ToolsTechTesting", "InnovationProcessImprovement",
        "CrossFunctionalSupports", "SiteGCHActivities", "TownhallsHRIT",
        "OneOne", "SuccessFactorLinkedIn", "OtherTrainings",
        "HiringOnboarding", "LeavesHolidays", "OpenTime"]
    total = 0
    for f in hour_fields:
        try: total += float(form_data.get(f, 0) or 0)
        except: pass
    form_data["TotalHours"] = total

    form_data = _clean(form_data)
    try:
        append_row(RESOURCE_TABLE, form_data)
        clear_cache(RESOURCE_TABLE)
        return {"status": "success", "message": "Entry saved!"}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}

def delete_resource(row_id):
    df = _get_cached(RESOURCE_TABLE, force=True)
    df = df[df["RowID"] != row_id]
    write_table(RESOURCE_TABLE, df)
    clear_cache(RESOURCE_TABLE)
    return {"status": "success", "message": "Deleted!"}

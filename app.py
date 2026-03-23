"""
app.py - Medical Creatives UT (Full Version)
Project Summary: 80 columns from MDCL, 11 revision groups, auto QC assignment
Resource Utilization: Calendar view, 20 fields from Medical_Creatives.xlsx
Settings: Self-service dropdown management
"""

import os
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback, ctx, ALL
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import date, datetime, timedelta
import calendar

from db_operations import (
    get_all_projects, submit_project, update_project, delete_project,
    get_all_resources, submit_resource, delete_resource,
    get_dropdown_options, get_lookup_values, save_lookup_values,
    get_all_lookup_fields, clear_cache, REVIEWER_EMAILS,
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True, title="Medical Creatives UT")
server = app.server

C = {"primary": "#1E2761", "accent": "#3B82F6", "success": "#10B981",
    "danger": "#EF4444", "bg": "#F8FAFC", "text": "#1E293B", "muted": "#64748B"}
TH = {"backgroundColor": C["primary"], "color": "white", "fontWeight": "bold", "fontSize": "11px"}

# ── Helpers ───────────────────────────────────────────────────────────
def mf(label, comp, w=3):
    return dbc.Col([dbc.Label(label, className="fw-semibold small text-muted mb-1"), comp], md=w, className="mb-2")

def mdd(fid, ph="Select..."):
    return dcc.Dropdown(id=fid, options=[], placeholder=ph, className="mb-0", style={"fontSize": "12px"})

def mi(fid, t="text", ph="", v=""):
    return dbc.Input(id=fid, type=t, placeholder=ph, value=v, size="sm", style={"fontSize": "12px"})

def mdt(fid):
    return dcc.DatePickerSingle(id=fid, date=None, display_format="YYYY-MM-DD", className="w-100")

def section_header(title, color=C["accent"]):
    return html.H6(title, className="mt-3 mb-2 py-1 px-2 text-white small fw-bold",
        style={"backgroundColor": color, "borderRadius": "4px"})


# ═══════════════════════════════════════════════════════════════════════
#  TAB 1: PROJECT SUMMARY (80 columns from MDCL)
# ═══════════════════════════════════════════════════════════════════════
def revision_group(prefix, label, show_smcd=True):
    """Generate fields for one revision group."""
    fields = []
    if show_smcd:
        fields.extend([
            mf("Simple", mi(f"{prefix}-simple", "number", "0"), 2),
            mf("Medium", mi(f"{prefix}-medium", "number", "0"), 2),
            mf("Complex", mi(f"{prefix}-complex", "number", "0"), 2),
            mf("Derivatives", mi(f"{prefix}-deriv", "number", "0"), 2),
        ])
    fields.extend([
        mf("Total", mi(f"{prefix}-total", "number", "0"), 2),
        mf("GD Rework", mi(f"{prefix}-gd", "number", "0"), 1),
        mf("POC Rework", mi(f"{prefix}-poc", "number", "0"), 1),
    ])
    return dbc.Card(dbc.CardBody([
        html.Small(label, className="fw-bold text-muted"),
        dbc.Row(fields),
    ]), className="mb-2", style={"backgroundColor": "#F8FAFC"})


def tab_project_summary():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Project Summary", className="text-primary fw-bold"), md=6),
            dbc.Col([
                dbc.Button([html.I(className="fas fa-plus me-1"), "New Project"], id="proj-new-btn", color="success", size="sm", className="me-2"),
                dbc.Button([html.I(className="fas fa-sync me-1"), "Refresh"], id="proj-refresh-btn", color="secondary", size="sm", outline=True),
            ], md=6, className="text-end"),
        ], className="mb-3 align-items-center"),

        dbc.Collapse(dbc.Card(dbc.CardBody([
            html.H5("Add New Project", className="mb-3 text-primary"),

            section_header("Basic Information"),
            dbc.Row([mf("Assigned Date", mdt("proj-assigned-date")), mf("Project Name", mi("proj-name", ph="Project name"), 3),
                mf("BU", mdd("proj-bu")), mf("Project ID", mi("proj-id"), 3)]),
            dbc.Row([mf("Veeva ID", mi("proj-veeva-id")), mf("Project Type", mdd("proj-type")),
                mf("Classification/Media", mdd("proj-media")), mf("Page/Slide #", mi("proj-page-slide", "number", "0"))]),

            section_header("Assignment & Status"),
            dbc.Row([mf("Tactic Type", mdd("proj-tactic")), mf("Internal Status", mdd("proj-status")),
                mf("First Proof Due", mdt("proj-proof-due")), mf("Assigner Name", mdd("proj-assigner"))]),
            dbc.Row([mf("Designer Assigned", mdd("proj-designer")), mf("QC Reviewer", mi("proj-qc", ph="Auto-assigned on Move to QC")),
                mf("Mail Sent", mdd("proj-mail")), mf("QC Emailer", mi("proj-qc-emailer", ph="Auto-filled"))]),
            html.Small("QC Reviewer and QC Emailer are auto-assigned when Internal Status = 'Move to QC'",
                className="text-info small fst-italic mb-2 d-block"),

            section_header("Tactic Details"),
            dbc.Row([mf("Tactic Stage", mdd("proj-stage")), mf("Stakeholder", mdd("proj-stakeholder")),
                mf("Complexity", mdd("proj-complexity")), mf("Content Status", mdd("proj-content-status"))]),

            section_header("Revision Status"),
            dbc.Row([mf("Revision 1", mdd("proj-rev1")), mf("Revision 2", mdd("proj-rev2")),
                mf("Revision 3+", mdd("proj-rev3")), mf("Comments", mi("proj-comments"), 3)]),

            section_header("Revision 1 — Asset Count", "#0D9488"),
            dbc.Row([mf("Asset #", mi("proj-r1-asset", "number", "0"), 2)]),
            revision_group("proj-r1", "Revision 1"),

            section_header("Revision 2"),
            revision_group("proj-r2", "Revision 2"),

            section_header("Revision 3"),
            revision_group("proj-r3", "Revision 3"),

            section_header("Revision 4"),
            revision_group("proj-r4", "Revision 4"),

            section_header("Revisions 5-11 (Total + Rework only)", "#64748B"),
            dbc.Row([
                dbc.Col([html.Small(f"Rev {i}", className="fw-bold text-muted d-block"),
                    dbc.Row([mf("Total", mi(f"proj-r{i}-total", "number", "0"), 4),
                        mf("GD", mi(f"proj-r{i}-gd", "number", "0"), 4),
                        mf("POC", mi(f"proj-r{i}-poc", "number", "0"), 4)])
                ], md=3) for i in range(5, 12)
            ]),

            section_header("Calculated Totals (Auto)", "#94A3B8"),
            dbc.Row([
                mf("GD Rework %", mi("proj-gd-pct", ph="Auto", t="text"), 2),
                mf("POC Rework %", mi("proj-poc-pct", ph="Auto", t="text"), 2),
                mf("Total Assets", mi("proj-total-assets", ph="Auto", t="text"), 2),
                mf("Total GD Rework", mi("proj-total-gd", ph="Auto", t="text"), 2),
                mf("Total POC Rework", mi("proj-total-poc", ph="Auto", t="text"), 2),
            ]),

            html.Hr(),
            dbc.Row([
                dbc.Col(dbc.Button("Submit", id="proj-submit-btn", color="primary", className="me-2"), width="auto"),
                dbc.Col(dbc.Button("Cancel", id="proj-cancel-btn", color="secondary", outline=True), width="auto"),
                dbc.Col(html.Div(id="proj-submit-msg"), className="align-self-center"),
            ]),
        ]), className="shadow-sm mb-3"), id="proj-form-collapse", is_open=False),

        html.Div(id="proj-table-container"),

        # View/Edit Modal
        dbc.Modal([dbc.ModalHeader(dbc.ModalTitle(id="proj-modal-title")), dbc.ModalBody(id="proj-modal-body"),
            dbc.ModalFooter([dbc.Button("Save Changes", id="proj-modal-save", color="primary", className="me-2", style={"display": "none"}),
                dbc.Button("Close", id="proj-modal-close", color="secondary")])],
            id="proj-modal", size="xl", scrollable=True, is_open=False),
        dcc.Store(id="proj-selected-row-id"), dcc.Store(id="proj-modal-mode"), html.Div(id="proj-delete-msg"),

        # Delete Confirmation
        dbc.Modal([dbc.ModalHeader(dbc.ModalTitle("Confirm Delete")),
            dbc.ModalBody("Are you sure you want to delete this project? This action cannot be undone."),
            dbc.ModalFooter([dbc.Button("Yes, Delete", id="proj-confirm-delete", color="danger", className="me-2"),
                dbc.Button("Cancel", id="proj-cancel-delete", color="secondary")])],
            id="proj-delete-modal", is_open=False, centered=True),
        dcc.Store(id="proj-delete-row-id"),
    ], fluid=True, className="py-3")


# ── Project Callbacks ─────────────────────────────────────────────────
@callback(Output("proj-form-collapse", "is_open"),
    [Input("proj-new-btn", "n_clicks"), Input("proj-cancel-btn", "n_clicks"), Input("proj-submit-btn", "n_clicks")],
    State("proj-form-collapse", "is_open"), prevent_initial_call=True)
def toggle_pf(n1, n2, n3, o):
    return True if ctx.triggered_id == "proj-new-btn" else False


# Build all State fields for project form
_proj_states = [
    State("proj-assigned-date", "date"), State("proj-name", "value"), State("proj-bu", "value"), State("proj-id", "value"),
    State("proj-veeva-id", "value"), State("proj-type", "value"), State("proj-media", "value"), State("proj-page-slide", "value"),
    State("proj-tactic", "value"), State("proj-status", "value"), State("proj-proof-due", "date"), State("proj-assigner", "value"),
    State("proj-designer", "value"), State("proj-qc", "value"), State("proj-mail", "value"), State("proj-qc-emailer", "value"),
    State("proj-stage", "value"), State("proj-stakeholder", "value"), State("proj-complexity", "value"), State("proj-content-status", "value"),
    State("proj-rev1", "value"), State("proj-rev2", "value"), State("proj-rev3", "value"), State("proj-comments", "value"),
    State("proj-r1-asset", "value"),
    State("proj-r1-simple", "value"), State("proj-r1-medium", "value"), State("proj-r1-complex", "value"), State("proj-r1-deriv", "value"),
    State("proj-r1-total", "value"), State("proj-r1-gd", "value"), State("proj-r1-poc", "value"),
    State("proj-r2-simple", "value"), State("proj-r2-medium", "value"), State("proj-r2-complex", "value"), State("proj-r2-deriv", "value"),
    State("proj-r2-total", "value"), State("proj-r2-gd", "value"), State("proj-r2-poc", "value"),
    State("proj-r3-simple", "value"), State("proj-r3-medium", "value"), State("proj-r3-complex", "value"), State("proj-r3-deriv", "value"),
    State("proj-r3-total", "value"), State("proj-r3-gd", "value"), State("proj-r3-poc", "value"),
    State("proj-r4-simple", "value"), State("proj-r4-medium", "value"), State("proj-r4-complex", "value"), State("proj-r4-deriv", "value"),
    State("proj-r4-total", "value"), State("proj-r4-gd", "value"), State("proj-r4-poc", "value"),
] + [s for i in range(5, 12) for s in [
    State(f"proj-r{i}-total", "value"), State(f"proj-r{i}-gd", "value"), State(f"proj-r{i}-poc", "value"),
]] + [
    State("proj-gd-pct", "value"), State("proj-poc-pct", "value"),
    State("proj-total-assets", "value"), State("proj-total-gd", "value"), State("proj-total-poc", "value"),
]

# All form field outputs to clear after submit
_proj_clear_outputs = [
    Output("proj-assigned-date", "date", allow_duplicate=True), Output("proj-name", "value", allow_duplicate=True),
    Output("proj-bu", "value", allow_duplicate=True), Output("proj-id", "value", allow_duplicate=True),
    Output("proj-veeva-id", "value", allow_duplicate=True), Output("proj-type", "value", allow_duplicate=True),
    Output("proj-media", "value", allow_duplicate=True), Output("proj-page-slide", "value", allow_duplicate=True),
    Output("proj-tactic", "value", allow_duplicate=True), Output("proj-status", "value", allow_duplicate=True),
    Output("proj-proof-due", "date", allow_duplicate=True), Output("proj-assigner", "value", allow_duplicate=True),
    Output("proj-designer", "value", allow_duplicate=True), Output("proj-qc", "value", allow_duplicate=True),
    Output("proj-mail", "value", allow_duplicate=True), Output("proj-qc-emailer", "value", allow_duplicate=True),
    Output("proj-stage", "value", allow_duplicate=True), Output("proj-stakeholder", "value", allow_duplicate=True),
    Output("proj-complexity", "value", allow_duplicate=True), Output("proj-content-status", "value", allow_duplicate=True),
    Output("proj-rev1", "value", allow_duplicate=True), Output("proj-rev2", "value", allow_duplicate=True),
    Output("proj-rev3", "value", allow_duplicate=True), Output("proj-comments", "value", allow_duplicate=True),
    Output("proj-r1-asset", "value", allow_duplicate=True),
] + [Output(f"proj-r{i}-{f}", "value", allow_duplicate=True)
     for i in range(1, 5) for f in ["simple", "medium", "complex", "deriv", "total", "gd", "poc"]
] + [Output(f"proj-r{i}-{f}", "value", allow_duplicate=True)
     for i in range(5, 12) for f in ["total", "gd", "poc"]
] + [
    Output("proj-gd-pct", "value", allow_duplicate=True), Output("proj-poc-pct", "value", allow_duplicate=True),
    Output("proj-total-assets", "value", allow_duplicate=True), Output("proj-total-gd", "value", allow_duplicate=True),
    Output("proj-total-poc", "value", allow_duplicate=True),
]

# Empty values for all 79 fields
_proj_empty = [None, '', None, '', '', None, None, '', None, None, None, None, None, '', None, '', None, None, None, None, None, None, None, ''] + [''] * 55

@callback([Output("proj-submit-msg", "children"), Output("proj-table-container", "children", allow_duplicate=True)] + _proj_clear_outputs,
    Input("proj-submit-btn", "n_clicks"), _proj_states, prevent_initial_call=True)
def submit_p(n, ad, name, bu, pid, vid, pt, media, ps, tactic, status, pf, assigner, designer, qc, mail, qce,
    stage, sh, comp, cs, r1, r2, r3, comments, r1_asset,
    r1s, r1m, r1c, r1d, r1t, r1g, r1p, r2s, r2m, r2c, r2d, r2t, r2g, r2p,
    r3s, r3m, r3c, r3d, r3t, r3g, r3p, r4s, r4m, r4c, r4d, r4t, r4g, r4p,
    r5t, r5g, r5p, r6t, r6g, r6p, r7t, r7g, r7p, r8t, r8g, r8p, r9t, r9g, r9p, r10t, r10g, r10p, r11t, r11g, r11p,
    gd_pct, poc_pct, ta, tgd, tpoc):
    if not name:
        return [dbc.Alert("Project Name required.", color="danger", duration=3000), dash.no_update] + [dash.no_update] * 79
    data = {
        "AssignedDate": ad, "ProjectName": name, "BU": bu, "ProjectID": pid, "VeevaID": vid, "ProjectType": pt,
        "ClassificationMedia": media, "PageSlide": ps, "TacticType": tactic, "InternalStatus": status,
        "FirstProofDue": pf, "AssignerName": assigner, "DesignerAssigned": designer, "QCReviewer": qc,
        "MailSent": mail, "QCEmailer": qce, "TacticStage": stage, "Stakeholder": sh,
        "Complexity": comp, "ContentStatus": cs, "Revision1": r1, "Revision2": r2, "Revision3OrMore": r3, "Comments": comments,
        "R1_Asset": r1_asset,
        "R1_Simple": r1s, "R1_Medium": r1m, "R1_Complex": r1c, "R1_Derivatives": r1d, "R1_Total": r1t, "R1_GDRework": r1g, "R1_POCRework": r1p,
        "R2_Simple": r2s, "R2_Medium": r2m, "R2_Complex": r2c, "R2_Derivatives": r2d, "R2_Total": r2t, "R2_GDRework": r2g, "R2_POCRework": r2p,
        "R3_Simple": r3s, "R3_Medium": r3m, "R3_Complex": r3c, "R3_Derivatives": r3d, "R3_Total": r3t, "R3_GDRework": r3g, "R3_POCRework": r3p,
        "R4_Simple": r4s, "R4_Medium": r4m, "R4_Complex": r4c, "R4_Derivatives": r4d, "R4_Total": r4t, "R4_GDRework": r4g, "R4_POCRework": r4p,
        "R5_Total": r5t, "R5_GDRework": r5g, "R5_POCRework": r5p,
        "R6_Total": r6t, "R6_GDRework": r6g, "R6_POCRework": r6p,
        "R7_Total": r7t, "R7_GDRework": r7g, "R7_POCRework": r7p,
        "R8_Total": r8t, "R8_GDRework": r8g, "R8_POCRework": r8p,
        "R9_Total": r9t, "R9_GDRework": r9g, "R9_POCRework": r9p,
        "R10_Total": r10t, "R10_GDRework": r10g, "R10_POCRework": r10p,
        "R11_Total": r11t, "R11_GDRework": r11g, "R11_POCRework": r11p,
    }
    r = submit_project(data)
    color = "success" if r["status"] == "success" else "danger"
    msg = dbc.Alert(r["message"] + " Click Refresh to see changes.", color=color, duration=6000)
    table_msg = dbc.Alert("Project saved! Click Refresh.", color="success", duration=5000)
    return [msg, table_msg] + _proj_empty


@callback(Output("proj-table-container", "children"),
    [Input("proj-refresh-btn", "n_clicks"), Input("tabs", "active_tab")])
def refresh_pt(n, tab):
    if tab != "tab-projects" and not n: return dash.no_update
    return build_pt()

def build_pt():
    df = get_all_projects(force=True)
    if df.empty: return dbc.Alert("No projects yet.", color="info")
    rows = []
    for _, row in df.iterrows():
        rid = row.get("RowID", "")
        rows.append(html.Tr([
            html.Td(str(row.get("ProjectName", ""))[:40], className="small"),
            html.Td(row.get("BU", ""), className="small"),
            html.Td(row.get("InternalStatus", ""), className="small"),
            html.Td(row.get("Complexity", ""), className="small"),
            html.Td(row.get("DesignerAssigned", ""), className="small"),
            html.Td(row.get("QCReviewer", ""), className="small"),
            html.Td(str(row.get("AssignedDate", ""))[:10], className="small"),
            html.Td([
                dbc.Button([html.I(className="fas fa-eye")], id={"type": "proj-view-btn", "index": rid}, color="info", size="sm", className="me-1"),
                dbc.Button([html.I(className="fas fa-edit")], id={"type": "proj-edit-btn", "index": rid}, color="warning", size="sm", className="me-1"),
                dbc.Button([html.I(className="fas fa-trash")], id={"type": "proj-del-btn", "index": rid}, color="danger", size="sm", outline=True),
            ], className="text-nowrap"),
        ]))
    return dbc.Table([
        html.Thead(html.Tr([html.Th(c, style=TH) for c in ["Project Name", "BU", "Status", "Complexity", "Designer", "QC Reviewer", "Date", "Actions"]])),
        html.Tbody(rows)], bordered=True, hover=True, responsive=True, size="sm", className="mt-2")


# View/Edit Modal
DROPDOWN_EDIT_FIELDS = {"BU", "ProjectType", "ClassificationMedia", "TacticType", "InternalStatus",
    "AssignerName", "DesignerAssigned", "QCReviewer", "MailSent", "TacticStage",
    "Stakeholder", "Complexity", "ContentStatus", "Revision1", "Revision2", "Revision3OrMore"}

@callback([Output("proj-modal", "is_open"), Output("proj-modal-title", "children"),
    Output("proj-modal-body", "children"), Output("proj-modal-save", "style"),
    Output("proj-selected-row-id", "data"), Output("proj-modal-mode", "data")],
    [Input({"type": "proj-view-btn", "index": ALL}, "n_clicks"),
     Input({"type": "proj-edit-btn", "index": ALL}, "n_clicks"),
     Input("proj-modal-close", "n_clicks")], prevent_initial_call=True)
def open_pm(vc, ec, cc):
    if ctx.triggered_id == "proj-modal-close":
        return False, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    t = ctx.triggered_id
    if not t or not isinstance(t, dict): return [dash.no_update]*6
    if not any(c for c in (vc or []) + (ec or []) if c): return [dash.no_update]*6
    rid = t["index"]; mode = "edit" if t["type"] == "proj-edit-btn" else "view"
    df = get_all_projects()
    if df.empty or "RowID" not in df.columns: return False, "", "", {"display": "none"}, None, None
    row = df[df["RowID"] == rid]
    if row.empty: return False, "", "", {"display": "none"}, None, None
    row = row.iloc[0]
    title = f"{'Edit' if mode == 'edit' else 'View'}: {row.get('ProjectName', '')}"
    edit_options = {}
    if mode == "edit":
        try:
            from db_connection import read_table as _rt
            ldf = _rt("Lookups")
            if not ldf.empty:
                for f in DROPDOWN_EDIT_FIELDS:
                    vals = ldf[ldf["FieldName"] == f].sort_values("Value")["Value"].tolist()
                    edit_options[f] = [{"label": v, "value": v} for v in vals]
        except: pass
    fields = []
    skip = {"RowID", "CreatedBy", "CreatedAt", "UpdatedBy", "UpdatedAt"}
    for col in df.columns:
        if col in skip: continue
        v = row.get(col, ""); v = "" if pd.isna(v) else v
        if mode == "edit":
            if col in DROPDOWN_EDIT_FIELDS and col in edit_options:
                fc = dcc.Dropdown(id={"type": "proj-edit-field", "index": col}, options=edit_options[col],
                    value=str(v) if v else None, placeholder="Select...", className="mb-0")
            else:
                fc = dbc.Input(id={"type": "proj-edit-field", "index": col}, value=str(v), size="sm")
            fields.append(dbc.Row([dbc.Col(dbc.Label(col, className="fw-semibold small"), md=4),
                dbc.Col(fc, md=8)], className="mb-2"))
        else:
            fields.append(dbc.Row([dbc.Col(html.Span(col, className="fw-semibold small text-muted"), md=4),
                dbc.Col(html.Span(str(v), className="small"), md=8)], className="mb-2 border-bottom pb-1"))
    fields.append(html.Hr())
    fields.append(html.Small(f"Created by {row.get('CreatedBy', '')} at {row.get('CreatedAt', '')}", className="text-muted"))
    save_style = {"display": "inline-block"} if mode == "edit" else {"display": "none"}
    return True, title, html.Div(fields), save_style, rid, mode

@callback([Output("proj-modal", "is_open", allow_duplicate=True), Output("proj-submit-msg", "children", allow_duplicate=True)],
    Input("proj-modal-save", "n_clicks"),
    [State("proj-selected-row-id", "data"), State({"type": "proj-edit-field", "index": ALL}, "value"),
     State({"type": "proj-edit-field", "index": ALL}, "id")], prevent_initial_call=True)
def save_pe(n, rid, vals, ids):
    if not rid or not vals: return dash.no_update, dash.no_update
    changes = {id_obj["index"]: val for val, id_obj in zip(vals, ids) if val is not None}
    r = update_project(rid, changes)
    return False, dbc.Alert(f"{r['message']} Click Refresh.", color="success" if r["status"] == "success" else "danger", duration=5000)

# Delete with confirmation
@callback([Output("proj-delete-modal", "is_open"), Output("proj-delete-row-id", "data")],
    Input({"type": "proj-del-btn", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def ask_dp(nc):
    if not ctx.triggered_id or not isinstance(ctx.triggered_id, dict) or not any(c for c in nc if c): return False, None
    return True, ctx.triggered_id["index"]

@callback([Output("proj-delete-msg", "children"), Output("proj-delete-modal", "is_open", allow_duplicate=True)],
    [Input("proj-confirm-delete", "n_clicks"), Input("proj-cancel-delete", "n_clicks")],
    State("proj-delete-row-id", "data"), prevent_initial_call=True)
def conf_dp(y, n, rid):
    if ctx.triggered_id == "proj-cancel-delete" or not rid: return dash.no_update, False
    delete_project(rid)
    return dbc.Alert("Project deleted. Click Refresh.", color="warning", duration=4000), False


# ═══════════════════════════════════════════════════════════════════════
#  TAB 2: RESOURCE UTILIZATION (Calendar View)
# ═══════════════════════════════════════════════════════════════════════
def tab_resource():
    today = date.today()
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Resource Utilization", className="text-primary fw-bold"), md=4),
            dbc.Col([dbc.ButtonGroup([
                dbc.Button(html.I(className="fas fa-chevron-left"), id="cal-prev", color="secondary", size="sm", outline=True),
                html.Span(id="cal-month-label", className="px-3 align-self-center fw-bold", style={"fontSize": "16px"}),
                dbc.Button(html.I(className="fas fa-chevron-right"), id="cal-next", color="secondary", size="sm", outline=True),
            ], className="me-3")], md=4, className="text-center"),
            dbc.Col([
                dbc.Button([html.I(className="fas fa-sync me-1"), "Refresh"], id="res-refresh-btn", color="secondary", size="sm", outline=True, className="me-2"),
                dbc.Button([html.I(className="fas fa-table me-1"), "Manager View"], id="res-manager-btn", color="primary", size="sm"),
            ], md=4, className="text-end"),
        ], className="mb-3 align-items-center"),
        dcc.Store(id="cal-year", data=today.year), dcc.Store(id="cal-month", data=today.month),
        html.Div(id="cal-grid"),
        dbc.Collapse(dbc.Card(dbc.CardBody([html.H5("Manager Summary", className="text-primary mb-3"),
            html.Div(id="manager-summary-content")]), className="shadow-sm mt-3"), id="manager-collapse", is_open=False),

        # Entry Modal
        dbc.Modal([dbc.ModalHeader(dbc.ModalTitle(id="res-modal-title")),
            dbc.ModalBody([
                html.Div(id="res-existing-entries"), html.Hr(),
                html.H6("Add New Entry", className="text-primary"),
                dbc.Row([mf("BU", mdd("res-bu")), mf("Designer Name", mdd("res-designer")),
                    mf("Reporting Manager", mdd("res-manager")), mf("", html.Div(), 3)]),
                section_header("Hours Breakdown"),
                dbc.Row([mf("Project Task N/A", mi("res-proj-task", "number", "0")),
                    mf("Stakeholder Touchpoints", mi("res-stakeholder", "number", "0")),
                    mf("Internal Team Meetings", mi("res-meetings", "number", "0")),
                    mf("GCH Trainings", mi("res-gch", "number", "0"))]),
                dbc.Row([mf("Tools & Tech Testing", mi("res-tools", "number", "0")),
                    mf("Innovation/Process", mi("res-innovation", "number", "0")),
                    mf("Cross Functional", mi("res-cross", "number", "0")),
                    mf("Site/GCH Activities", mi("res-site", "number", "0"))]),
                dbc.Row([mf("Townhalls/HR/IT", mi("res-townhall", "number", "0")),
                    mf("One:One", mi("res-oneone", "number", "0")),
                    mf("SuccessFactor/LinkedIn", mi("res-sf", "number", "0")),
                    mf("Other Trainings", mi("res-other-train", "number", "0"))]),
                dbc.Row([mf("Hiring/Onboarding", mi("res-hiring", "number", "0")),
                    mf("Leaves/Holidays", mi("res-leaves", "number", "0")),
                    mf("Open Time", mi("res-open", "number", "0")),
                    mf("Total Hours", mi("res-total-hours", ph="Auto-calculated", t="text"), 3)]),
                html.Small("Total Hours is auto-calculated as sum of all hour fields above.", className="text-info small fst-italic"),
            ]),
            dbc.ModalFooter([dbc.Button("Save Entry", id="res-submit-btn", color="primary", className="me-2"),
                dbc.Button("Close", id="res-modal-close", color="secondary")])],
            id="res-modal", size="xl", scrollable=True, is_open=False),
        dcc.Store(id="res-selected-date"), html.Div(id="res-submit-msg"), html.Div(id="res-delete-msg"),

        # Delete Confirmation
        dbc.Modal([dbc.ModalHeader(dbc.ModalTitle("Confirm Delete")),
            dbc.ModalBody("Are you sure you want to delete this entry?"),
            dbc.ModalFooter([dbc.Button("Yes, Delete", id="res-confirm-delete", color="danger", className="me-2"),
                dbc.Button("Cancel", id="res-cancel-delete", color="secondary")])],
            id="res-delete-modal", is_open=False, centered=True),
        dcc.Store(id="res-delete-row-id"),
    ], fluid=True, className="py-3")


# Calendar callbacks
@callback([Output("cal-year", "data"), Output("cal-month", "data")],
    [Input("cal-prev", "n_clicks"), Input("cal-next", "n_clicks")],
    [State("cal-year", "data"), State("cal-month", "data")], prevent_initial_call=True)
def nav_m(p, nx, y, m):
    if ctx.triggered_id == "cal-prev": return (y-1, 12) if m == 1 else (y, m-1)
    return (y+1, 1) if m == 12 else (y, m+1)

@callback([Output("cal-grid", "children"), Output("cal-month-label", "children")],
    [Input("cal-year", "data"), Input("cal-month", "data"), Input("res-refresh-btn", "n_clicks"), Input("tabs", "active_tab")])
def build_cal(year, month, ref, tab):
    if tab != "tab-resource" and not ref: return dash.no_update, dash.no_update
    label = f"{calendar.month_name[month]} {year}"
    df = get_all_resources(force_refresh=True)
    ebd = {}
    if not df.empty and "Date" in df.columns:
        for _, row in df.iterrows():
            d = str(row.get("Date", ""))[:10]
            if d.startswith(f"{year}-{month:02d}"): ebd.setdefault(d, []).append(row)
    cal = calendar.monthcalendar(year, month); today = date.today()
    header = html.Tr([html.Th(d, className="text-center small fw-bold text-muted", style={"padding": "8px"})
        for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]])
    rows = []
    for week in cal:
        cells = []
        for day in week:
            if day == 0:
                cells.append(html.Td("", style={"backgroundColor": "#F1F5F9", "height": "80px", "width": "14.28%"}))
            else:
                ds = f"{year}-{month:02d}-{day:02d}"; it = date(year, month, day) == today
                entries = ebd.get(ds, []); ec = len(entries)
                dc = [html.Div(str(day), className="fw-bold small" + (" text-white" if it else ""),
                    style={"backgroundColor": C["accent"] if it else "transparent", "borderRadius": "50%",
                           "width": "24px", "height": "24px", "display": "flex", "alignItems": "center", "justifyContent": "center"})]
                if ec > 0:
                    th = sum(float(e.get("TotalHours", 0) or 0) for e in entries)
                    dc.append(dbc.Badge(f"{ec} | {th:.0f}h", color="success", className="mt-1", style={"fontSize": "9px"}))
                cells.append(html.Td(html.Div(dc, id={"type": "cal-day", "index": ds},
                    style={"cursor": "pointer", "height": "70px", "padding": "4px"}, className="h-100"),
                    style={"backgroundColor": "#ECFDF5" if ec > 0 else "white",
                           "border": f"2px solid {C['accent']}" if it else "1px solid #E2E8F0",
                           "verticalAlign": "top", "width": "14.28%"}))
        rows.append(html.Tr(cells))
    return dbc.Table([html.Thead(header), html.Tbody(rows)], bordered=True, className="mb-0", style={"tableLayout": "fixed"}), label

@callback([Output("res-modal", "is_open"), Output("res-modal-title", "children"),
    Output("res-selected-date", "data"), Output("res-existing-entries", "children")],
    [Input({"type": "cal-day", "index": ALL}, "n_clicks"), Input("res-modal-close", "n_clicks")], prevent_initial_call=True)
def open_rm(dc, cc):
    if ctx.triggered_id == "res-modal-close": return False, "", None, ""
    t = ctx.triggered_id
    if not t or not isinstance(t, dict) or not any(c for c in dc if c): return [dash.no_update]*4
    ds = t["index"]; df = get_all_resources()
    existing = []
    if not df.empty and "Date" in df.columns:
        de = df[df["Date"].astype(str).str.startswith(ds)]
        for _, row in de.iterrows():
            rid = row.get("RowID", "")
            existing.append(dbc.Card(dbc.CardBody(dbc.Row([
                dbc.Col([html.Span(f"{row.get('DesignerName', '?')} ", className="fw-bold small"),
                    html.Span(f"| {row.get('BU', '')} | {row.get('TotalHours', 0)}h", className="small text-muted")], md=9),
                dbc.Col(dbc.Button([html.I(className="fas fa-trash")], id={"type": "res-del-btn", "index": rid},
                    color="danger", size="sm", outline=True), md=3, className="text-end")])), className="mb-2 shadow-sm"))
    ed = html.Div([html.H6(f"Existing Entries ({len(existing)})", className="text-muted mb-2"),
        html.Div(existing or [html.P("No entries.", className="text-muted small")])])
    return True, f"Resource Entry — {ds}", ds, ed

@callback([Output("res-submit-msg", "children"), Output("res-modal", "is_open", allow_duplicate=True),
    Output("res-bu", "value", allow_duplicate=True), Output("res-designer", "value", allow_duplicate=True),
    Output("res-manager", "value"), Output("res-proj-task", "value"), Output("res-stakeholder", "value"),
    Output("res-meetings", "value"), Output("res-gch", "value"), Output("res-tools", "value"),
    Output("res-innovation", "value"), Output("res-cross", "value"), Output("res-site", "value"),
    Output("res-townhall", "value"), Output("res-oneone", "value"), Output("res-sf", "value"),
    Output("res-other-train", "value"), Output("res-hiring", "value"), Output("res-leaves", "value"),
    Output("res-open", "value"), Output("res-total-hours", "value")],
    Input("res-submit-btn", "n_clicks"),
    [State("res-selected-date", "data"), State("res-bu", "value"), State("res-designer", "value"),
     State("res-manager", "value"), State("res-proj-task", "value"), State("res-stakeholder", "value"),
     State("res-meetings", "value"), State("res-gch", "value"), State("res-tools", "value"),
     State("res-innovation", "value"), State("res-cross", "value"), State("res-site", "value"),
     State("res-townhall", "value"), State("res-oneone", "value"), State("res-sf", "value"),
     State("res-other-train", "value"), State("res-hiring", "value"), State("res-leaves", "value"),
     State("res-open", "value"), State("res-total-hours", "value")], prevent_initial_call=True)
def submit_r(n, dt, bu, des, mgr, pt, sh, mtg, gch, tools, innov, cross, site, town, oo, sf, ot, hire, leave, opn, tot):
    data = {"Date": dt, "BU": bu, "DesignerName": des, "ReportingManager": mgr, "ProjectTaskNA": pt,
        "StakeholderTouchpoints": sh, "InternalTeamMeetings": mtg, "GCHTrainings": gch, "ToolsTechTesting": tools,
        "InnovationProcessImprovement": innov, "CrossFunctionalSupports": cross, "SiteGCHActivities": site,
        "TownhallsHRIT": town, "OneOne": oo, "SuccessFactorLinkedIn": sf, "OtherTrainings": ot,
        "HiringOnboarding": hire, "LeavesHolidays": leave, "OpenTime": opn, "TotalHours": tot}
    r = submit_resource(data)
    msg = dbc.Alert(r["message"], color="success" if r["status"] == "success" else "danger", duration=4000)
    return [msg, False] + [None, None, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]

# Delete with confirmation
@callback([Output("res-delete-modal", "is_open"), Output("res-delete-row-id", "data")],
    Input({"type": "res-del-btn", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def ask_dr(nc):
    if not ctx.triggered_id or not isinstance(ctx.triggered_id, dict) or not any(c for c in nc if c): return False, None
    return True, ctx.triggered_id["index"]

@callback([Output("res-delete-msg", "children"), Output("res-delete-modal", "is_open", allow_duplicate=True)],
    [Input("res-confirm-delete", "n_clicks"), Input("res-cancel-delete", "n_clicks")],
    State("res-delete-row-id", "data"), prevent_initial_call=True)
def conf_dr(y, n, rid):
    if ctx.triggered_id == "res-cancel-delete" or not rid: return dash.no_update, False
    delete_resource(rid)
    return dbc.Alert("Deleted. Click Refresh.", color="warning", duration=4000), False

# Manager view
@callback(Output("manager-collapse", "is_open"), Input("res-manager-btn", "n_clicks"),
    State("manager-collapse", "is_open"), prevent_initial_call=True)
def toggle_mgr(n, o): return not o

@callback(Output("manager-summary-content", "children"), Input("manager-collapse", "is_open"),
    [State("cal-year", "data"), State("cal-month", "data")], prevent_initial_call=True)
def load_mgr(o, y, m):
    if not o: return ""
    df = get_all_resources(force_refresh=True)
    if df.empty: return dbc.Alert("No data.", color="info")
    mp = f"{y}-{m:02d}"
    if "Date" in df.columns: df = df[df["Date"].astype(str).str.startswith(mp)]
    if df.empty: return dbc.Alert(f"No entries for {calendar.month_name[m]} {y}.", color="info")
    nc = ["ProjectTaskNA", "StakeholderTouchpoints", "InternalTeamMeetings", "GCHTrainings",
        "ToolsTechTesting", "InnovationProcessImprovement", "CrossFunctionalSupports", "SiteGCHActivities",
        "TownhallsHRIT", "OneOne", "SuccessFactorLinkedIn", "OtherTrainings", "HiringOnboarding", "LeavesHolidays", "OpenTime", "TotalHours"]
    for c in nc:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    if "DesignerName" in df.columns and "TotalHours" in df.columns:
        s = df.groupby("DesignerName").agg(Entries=("RowID", "count"), TotalHours=("TotalHours", "sum"),
            Meetings=("InternalTeamMeetings", "sum"), Leaves=("LeavesHolidays", "sum")).reset_index()
        return dbc.Table([html.Thead(html.Tr([html.Th(c, style=TH) for c in ["Designer", "Entries", "Hours", "Meetings", "Leaves"]])),
            html.Tbody([html.Tr([html.Td(r["DesignerName"], className="small fw-bold"),
                html.Td(r["Entries"], className="small"), html.Td(f"{r['TotalHours']:.0f}h", className="small"),
                html.Td(f"{r['Meetings']:.0f}h", className="small"), html.Td(f"{r['Leaves']:.0f}h", className="small")])
                for _, r in s.iterrows()])], bordered=True, hover=True, size="sm")
    return dbc.Alert("Missing columns.", color="warning")


# ═══════════════════════════════════════════════════════════════════════
#  TAB 3: SETTINGS
# ═══════════════════════════════════════════════════════════════════════
DD_FIELDS = [
    {"label": "BU", "value": "BU"}, {"label": "Project Type", "value": "ProjectType"},
    {"label": "Classification/Media", "value": "ClassificationMedia"}, {"label": "Tactic Type", "value": "TacticType"},
    {"label": "Internal Status", "value": "InternalStatus"}, {"label": "Assigner Name", "value": "AssignerName"},
    {"label": "Designer Assigned", "value": "DesignerAssigned"}, {"label": "QC Reviewer", "value": "QCReviewer"},
    {"label": "Mail Sent", "value": "MailSent"}, {"label": "Tactic Stage", "value": "TacticStage"},
    {"label": "Stakeholder", "value": "Stakeholder"}, {"label": "Complexity", "value": "Complexity"},
    {"label": "Content Status", "value": "ContentStatus"}, {"label": "Revision 1", "value": "Revision1"},
    {"label": "Revision 2", "value": "Revision2"}, {"label": "Revision 3+", "value": "Revision3OrMore"},
    {"label": "Reporting Manager", "value": "ReportingManager"},
]

def tab_settings():
    return dbc.Container([
        html.H4("Settings — Manage Dropdowns", className="text-primary fw-bold mb-3"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H6("Select Field", className="text-muted mb-2"),
                dcc.Dropdown(id="settings-field-select", options=DD_FIELDS, placeholder="Select..."), html.Hr(),
                html.H6("Or Add New", className="text-muted mb-2"),
                dbc.InputGroup([dbc.Input(id="settings-new-field", placeholder="Field name"),
                    dbc.Button("Add", id="settings-add-field-btn", color="primary", size="sm")]),
                html.Div(id="settings-add-field-msg", className="mt-2")]), className="shadow-sm"), md=4),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6(id="settings-edit-title", children="Select a field", className="text-muted mb-2"),
                dbc.Textarea(id="settings-values-textarea", placeholder="One value per line...", style={"height": "300px"}), html.Hr(),
                dbc.Row([dbc.Col(dbc.Button("Save Values", id="settings-save-btn", color="success", className="me-2"), width="auto"),
                    dbc.Col(html.Div(id="settings-save-msg"), className="align-self-center")])]), className="shadow-sm"), md=8)])
    ], fluid=True, className="py-3")

@callback([Output("settings-values-textarea", "value"), Output("settings-edit-title", "children")],
    Input("settings-field-select", "value"), prevent_initial_call=True)
def load_fv(f):
    if not f: return "", "Select a field"
    return "\n".join(get_lookup_values(f)), f"Editing: {f}"

@callback(Output("settings-save-msg", "children"), Input("settings-save-btn", "n_clicks"),
    [State("settings-field-select", "value"), State("settings-values-textarea", "value")], prevent_initial_call=True)
def save_fv(n, f, txt):
    if not f: return dbc.Alert("Select a field.", color="warning", duration=3000)
    vals = [v.strip() for v in txt.strip().split("\n") if v.strip()]
    try: save_lookup_values(f, vals); return dbc.Alert(f"Saved {len(vals)} values!", color="success", duration=3000)
    except Exception as e: return dbc.Alert(f"Error: {e}", color="danger", duration=5000)

@callback([Output("settings-field-select", "options"), Output("settings-add-field-msg", "children")],
    Input("settings-add-field-btn", "n_clicks"), State("settings-new-field", "value"), prevent_initial_call=True)
def add_f(n, nf):
    if not nf: return dash.no_update, dbc.Alert("Enter name.", color="warning", duration=3000)
    fn = nf.strip().replace(" ", ""); save_lookup_values(fn, []); clear_cache()
    opts = sorted(set([d["value"] for d in DD_FIELDS] + get_all_lookup_fields() + [fn]))
    return [{"label": f, "value": f} for f in opts], dbc.Alert(f"Added: {fn}", color="success", duration=3000)


# ═══════════════════════════════════════════════════════════════════════
#  LAZY LOAD DROPDOWNS
# ═══════════════════════════════════════════════════════════════════════
DD_MAP = {
    "proj-bu": "BU", "proj-type": "ProjectType", "proj-media": "ClassificationMedia",
    "proj-tactic": "TacticType", "proj-status": "InternalStatus", "proj-assigner": "AssignerName",
    "proj-designer": "DesignerAssigned", "proj-mail": "MailSent", "proj-stage": "TacticStage",
    "proj-stakeholder": "Stakeholder", "proj-complexity": "Complexity",
    "proj-content-status": "ContentStatus", "proj-rev1": "Revision1", "proj-rev2": "Revision2",
    "proj-rev3": "Revision3OrMore",
    "res-bu": "BU", "res-designer": "DesignerAssigned", "res-manager": "ReportingManager",
}

@callback([Output(dd, "options") for dd in DD_MAP.keys()],
    [Input("proj-new-btn", "n_clicks"), Input("res-submit-btn", "n_clicks"),
     Input("proj-refresh-btn", "n_clicks"), Input("res-refresh-btn", "n_clicks"),
     Input("tabs", "active_tab")])
def load_dd(n1, n2, n3, n4, tab):
    if tab not in ("tab-projects", "tab-resource") and not any([n1, n2, n3, n4]):
        return [dash.no_update] * len(DD_MAP)
    try:
        from db_connection import read_table; df = read_table("Lookups")
    except: df = pd.DataFrame()
    results = []
    for dd, ln in DD_MAP.items():
        if df.empty or "FieldName" not in df.columns: results.append([])
        else: results.append([{"label": v, "value": v} for v in df[df["FieldName"] == ln].sort_values("Value")["Value"].tolist()])
    return results


# ═══════════════════════════════════════════════════════════════════════
#  LAYOUT
# ═══════════════════════════════════════════════════════════════════════
app.layout = html.Div([
    dbc.Navbar(dbc.Container([
        dbc.NavbarBrand([html.I(className="fas fa-palette me-2"), "Medical Creatives UT"], className="fw-bold text-white"),
        html.Span(f"User: {os.getenv('APP_USER', 'unknown')}", className="text-light small"),
    ], fluid=True), color=C["primary"], dark=True, className="mb-0"),
    dbc.Tabs(id="tabs", active_tab="tab-projects", className="px-3 pt-2", children=[
        dbc.Tab(tab_project_summary(), label="Project Summary", tab_id="tab-projects", label_style={"fontWeight": "600"}),
        dbc.Tab(tab_resource(), label="Resource Utilization", tab_id="tab-resource", label_style={"fontWeight": "600"}),
        dbc.Tab(tab_settings(), label="Settings", tab_id="tab-settings", label_style={"fontWeight": "600"}),
    ]),
], style={"backgroundColor": C["bg"], "minHeight": "100vh"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

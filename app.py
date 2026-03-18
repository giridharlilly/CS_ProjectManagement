"""
app.py - Medical Creatives UT
Tabs: Project Summary | Resource Utilization (Calendar) | Settings
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
    get_all_lookup_fields, clear_cache,
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True, title="Medical Creatives UT")
server = app.server

C = {"primary": "#1E2761", "accent": "#3B82F6", "success": "#10B981",
    "danger": "#EF4444", "bg": "#F8FAFC", "text": "#1E293B", "muted": "#64748B"}

TH = {"backgroundColor": C["primary"], "color": "white", "fontWeight": "bold", "fontSize": "12px"}

# ── Helpers ───────────────────────────────────────────────────────────
def mf(label, comp, w=4):
    return dbc.Col([dbc.Label(label, className="fw-semibold small text-muted mb-1"), comp], md=w, className="mb-3")

def mdd(fid, ph="Select..."):
    return dcc.Dropdown(id=fid, options=[], placeholder=ph, className="mb-0")

def mi(fid, t="text", ph=""):
    return dbc.Input(id=fid, type=t, placeholder=ph, size="sm")

def mdt(fid):
    return dcc.DatePickerSingle(id=fid, date=None, display_format="YYYY-MM-DD", className="w-100")


# ═══════════════════════════════════════════════════════════════════════
#  TAB 1: PROJECT SUMMARY
# ═══════════════════════════════════════════════════════════════════════
def tab_project_summary():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Project Summary", className="text-primary fw-bold"), md=6),
            dbc.Col([
                dbc.Button([html.I(className="fas fa-plus me-1"), "New Project"], id="proj-new-btn", color="success", size="sm", className="me-2"),
                dbc.Button([html.I(className="fas fa-sync me-1"), "Refresh"], id="proj-refresh-btn", color="secondary", size="sm", outline=True),
            ], md=6, className="text-end"),
        ], className="mb-3 align-items-center"),

        # New Project Form
        dbc.Collapse(dbc.Card(dbc.CardBody([
            html.H5("Add New Project", className="mb-3 text-primary"),
            dbc.Row([mf("Assigned Date", mdt("proj-assigned-date"), 3), mf("Project Name", mi("proj-name", ph="Project name"), 3),
                mf("BU", mdd("proj-bu"), 3), mf("Project ID", mi("proj-id", ph="Project ID"), 3)]),
            dbc.Row([mf("Veeva ID", mi("proj-veeva-id"), 3), mf("Project Type", mdd("proj-type"), 3),
                mf("Classification Media", mdd("proj-media"), 3), mf("Page/Slide #", mi("proj-page-slide", "number", "0"), 3)]),
            dbc.Row([mf("Tactic Type", mdd("proj-tactic"), 3), mf("Internal Status", mdd("proj-status"), 3),
                mf("First Proof Due", mdt("proj-proof-due"), 3), mf("Assigner Name", mdd("proj-assigner"), 3)]),
            dbc.Row([mf("Designer Assigned", mdd("proj-designer"), 3), mf("QC Reviewer", mdd("proj-qc"), 3),
                mf("Mail Sent", mdd("proj-mail"), 3), mf("QC Emailer", mi("proj-qc-emailer"), 3)]),
            dbc.Row([mf("Tactic Stage", mdd("proj-stage"), 3), mf("Stakeholder", mdd("proj-stakeholder"), 3),
                mf("Complexity", mdd("proj-complexity"), 3), mf("Content Status", mdd("proj-content-status"), 3)]),
            dbc.Row([mf("Revision 1", mdd("proj-rev1"), 3), mf("Revision 2", mdd("proj-rev2"), 3),
                mf("Revision 3+", mdd("proj-rev3"), 3), mf("Comments", mi("proj-comments"), 3)]),
            dbc.Row([mf("GD Rework %", mi("proj-gd-pct", "number", "0"), 2), mf("POC Rework %", mi("proj-poc-pct", "number", "0"), 2),
                mf("Asset #", mi("proj-asset", "number", "0"), 2), mf("Total #", mi("proj-total", "number", "0"), 2),
                mf("Simple #", mi("proj-simple", "number", "0"), 2), mf("Medium #", mi("proj-medium", "number", "0"), 2)]),
            dbc.Row([mf("Complex #", mi("proj-complex", "number", "0"), 2), mf("Derivatives #", mi("proj-deriv", "number", "0"), 2),
                mf("GD Rework", mi("proj-gd-rework", "number", "0"), 2), mf("POC Rework", mi("proj-poc-rework", "text"), 2),
                mf("Total Assets", mi("proj-total-assets", "number", "0"), 2), mf("Total GD Rework", mi("proj-total-gd", "number", "0"), 2)]),
            html.Hr(),
            dbc.Row([
                dbc.Col(dbc.Button("Submit", id="proj-submit-btn", color="primary", className="me-2"), width="auto"),
                dbc.Col(dbc.Button("Cancel", id="proj-cancel-btn", color="secondary", outline=True), width="auto"),
                dbc.Col(html.Div(id="proj-submit-msg"), className="align-self-center"),
            ]),
        ]), className="shadow-sm mb-3"), id="proj-form-collapse", is_open=False),

        # Table
        html.Div(id="proj-table-container"),

        # View/Edit Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="proj-modal-title")),
            dbc.ModalBody(id="proj-modal-body"),
            dbc.ModalFooter([
                dbc.Button("Save Changes", id="proj-modal-save", color="primary", className="me-2", style={"display": "none"}),
                dbc.Button("Close", id="proj-modal-close", color="secondary"),
            ]),
        ], id="proj-modal", size="xl", scrollable=True, is_open=False),
        dcc.Store(id="proj-selected-row-id"),
        dcc.Store(id="proj-modal-mode"),
        html.Div(id="proj-delete-msg"),
    ], fluid=True, className="py-3")


# Toggle form + close after submit
@callback(Output("proj-form-collapse", "is_open"),
    [Input("proj-new-btn", "n_clicks"), Input("proj-cancel-btn", "n_clicks"), Input("proj-submit-btn", "n_clicks")],
    State("proj-form-collapse", "is_open"), prevent_initial_call=True)
def toggle_proj_form(n1, n2, n3, is_open):
    tid = ctx.triggered_id
    if tid == "proj-new-btn":
        return True
    # Close on cancel OR after submit
    return False


@callback([Output("proj-submit-msg", "children"), Output("proj-table-container", "children", allow_duplicate=True),
    # Clear all form fields after submit
    Output("proj-assigned-date", "date"), Output("proj-name", "value"), Output("proj-bu", "value"), Output("proj-id", "value"),
    Output("proj-veeva-id", "value"), Output("proj-type", "value"), Output("proj-media", "value"), Output("proj-page-slide", "value"),
    Output("proj-tactic", "value"), Output("proj-status", "value"), Output("proj-proof-due", "date"), Output("proj-assigner", "value"),
    Output("proj-designer", "value"), Output("proj-qc", "value"), Output("proj-mail", "value"), Output("proj-qc-emailer", "value"),
    Output("proj-stage", "value"), Output("proj-stakeholder", "value"), Output("proj-complexity", "value"), Output("proj-content-status", "value"),
    Output("proj-rev1", "value"), Output("proj-rev2", "value"), Output("proj-rev3", "value"), Output("proj-comments", "value"),
    Output("proj-gd-pct", "value"), Output("proj-poc-pct", "value"), Output("proj-asset", "value"), Output("proj-total", "value"),
    Output("proj-simple", "value"), Output("proj-medium", "value"), Output("proj-complex", "value"), Output("proj-deriv", "value"),
    Output("proj-gd-rework", "value"), Output("proj-poc-rework", "value"), Output("proj-total-assets", "value"), Output("proj-total-gd", "value")],
    Input("proj-submit-btn", "n_clicks"),
    [State("proj-assigned-date", "date"), State("proj-name", "value"), State("proj-bu", "value"), State("proj-id", "value"),
     State("proj-veeva-id", "value"), State("proj-type", "value"), State("proj-media", "value"), State("proj-page-slide", "value"),
     State("proj-tactic", "value"), State("proj-status", "value"), State("proj-proof-due", "date"), State("proj-assigner", "value"),
     State("proj-designer", "value"), State("proj-qc", "value"), State("proj-mail", "value"), State("proj-qc-emailer", "value"),
     State("proj-stage", "value"), State("proj-stakeholder", "value"), State("proj-complexity", "value"), State("proj-content-status", "value"),
     State("proj-rev1", "value"), State("proj-rev2", "value"), State("proj-rev3", "value"), State("proj-comments", "value"),
     State("proj-gd-pct", "value"), State("proj-poc-pct", "value"), State("proj-asset", "value"), State("proj-total", "value"),
     State("proj-simple", "value"), State("proj-medium", "value"), State("proj-complex", "value"), State("proj-deriv", "value"),
     State("proj-gd-rework", "value"), State("proj-poc-rework", "value"), State("proj-total-assets", "value"), State("proj-total-gd", "value")],
    prevent_initial_call=True)
def submit_proj(n, ad, name, bu, pid, vid, pt, media, ps, tactic, status, pf, assigner, designer, qc, mail, qce, stage, sh, comp, cs, r1, r2, r3, comments, gp, pp, asset, total, simple, med, cmplx, deriv, gr, pr, ta, tg):
    # 34 form fields to clear = 34 None/empty values
    empty = [None, "", None, "",
             "", None, None, "",
             None, None, None, None,
             None, None, None, "",
             None, None, None, None,
             None, None, None, "",
             "", "", "", "",
             "", "", "", "",
             "", "", "", ""]
    if not name:
        return [dbc.Alert("Project Name required.", color="danger", duration=3000), dash.no_update] + [dash.no_update] * 34
    data = {"AssignedDate": ad, "ProjectName": name, "BU": bu, "ProjectID": pid, "VeevaID": vid, "ProjectType": pt,
        "ClassificationMedia": media, "PageSlide": ps, "TacticType": tactic, "InternalStatus": status,
        "FirstProofDue": pf, "AssignerName": assigner, "DesignerAssigned": designer, "QCReviewer": qc,
        "MailSent": mail, "QCEmailer": qce, "TacticStage": stage, "Stakeholder": sh,
        "Complexity": comp, "ContentStatus": cs, "Revision1": r1, "Revision2": r2, "Revision3OrMore": r3,
        "Comments": comments, "GDReworkPct": gp, "POCReworkPct": pp, "Asset": asset, "Total": total,
        "Simple": simple, "Medium": med, "Complex": cmplx, "Derivatives": deriv,
        "GDRework": gr, "POCRework": pr, "TotalAssets": ta, "TotalGDRework": tg}
    r = submit_project(data)
    msg = dbc.Alert(r["message"], color="success" if r["status"] == "success" else "danger", duration=4000)
    table_msg = dbc.Alert("Project saved! Click Refresh to see it.", color="success", duration=5000)
    return [msg, table_msg] + empty


# Auto-load table on tab switch
@callback(Output("proj-table-container", "children"),
    [Input("proj-refresh-btn", "n_clicks"), Input("tabs", "active_tab")])
def refresh_proj_table(n, tab):
    if tab != "tab-projects" and not n:
        return dash.no_update
    return build_proj_table()


def build_proj_table():
    df = get_all_projects(force_refresh=True)
    if df.empty:
        return dbc.Alert("No projects yet. Click 'New Project' to add one.", color="info")
    rows = []
    for _, row in df.iterrows():
        rid = row.get("RowID", "")
        rows.append(html.Tr([
            html.Td(row.get("ProjectName", ""), className="small"),
            html.Td(row.get("BU", ""), className="small"),
            html.Td(row.get("InternalStatus", ""), className="small"),
            html.Td(row.get("Complexity", ""), className="small"),
            html.Td(row.get("DesignerAssigned", ""), className="small"),
            html.Td(row.get("AssignedDate", ""), className="small"),
            html.Td([
                dbc.Button([html.I(className="fas fa-eye")], id={"type": "proj-view-btn", "index": rid}, color="info", size="sm", className="me-1"),
                dbc.Button([html.I(className="fas fa-edit")], id={"type": "proj-edit-btn", "index": rid}, color="warning", size="sm", className="me-1"),
                dbc.Button([html.I(className="fas fa-trash")], id={"type": "proj-del-btn", "index": rid}, color="danger", size="sm", outline=True),
            ], className="text-nowrap"),
        ]))
    return dbc.Table([
        html.Thead(html.Tr([html.Th(c, style=TH) for c in ["Project Name", "BU", "Status", "Complexity", "Designer", "Date", "Actions"]])),
        html.Tbody(rows),
    ], bordered=True, hover=True, responsive=True, size="sm", className="mt-2")


# View/Edit Modal — FIXED: only opens on actual button click
@callback(
    [Output("proj-modal", "is_open"), Output("proj-modal-title", "children"),
     Output("proj-modal-body", "children"), Output("proj-modal-save", "style"),
     Output("proj-selected-row-id", "data"), Output("proj-modal-mode", "data")],
    [Input({"type": "proj-view-btn", "index": ALL}, "n_clicks"),
     Input({"type": "proj-edit-btn", "index": ALL}, "n_clicks"),
     Input("proj-modal-close", "n_clicks")],
    prevent_initial_call=True)
def open_proj_modal(view_clicks, edit_clicks, close_click):
    if ctx.triggered_id == "proj-modal-close":
        return False, "", "", {"display": "none"}, None, None

    # Check if an actual button was clicked (not just initial render)
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # Verify actual click happened (not None)
    all_clicks = (view_clicks or []) + (edit_clicks or [])
    if not any(c for c in all_clicks if c):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    rid = triggered["index"]
    mode = "edit" if triggered["type"] == "proj-edit-btn" else "view"

    df = get_all_projects()
    if df.empty or "RowID" not in df.columns:
        return False, "", "", {"display": "none"}, None, None
    row = df[df["RowID"] == rid]
    if row.empty:
        return False, "", "", {"display": "none"}, None, None
    row = row.iloc[0]

    title = f"{'Edit' if mode == 'edit' else 'View'}: {row.get('ProjectName', '')}"
    fields = []
    skip = ["RowID", "CreatedBy", "CreatedAt", "UpdatedBy", "UpdatedAt"]
    for col in df.columns:
        if col in skip:
            continue
        v = row.get(col, "")
        v = "" if pd.isna(v) else v
        if mode == "edit":
            fields.append(dbc.Row([
                dbc.Col(dbc.Label(col, className="fw-semibold small"), md=4),
                dbc.Col(dbc.Input(id={"type": "proj-edit-field", "index": col}, value=str(v), size="sm"), md=8),
            ], className="mb-2"))
        else:
            fields.append(dbc.Row([
                dbc.Col(html.Span(col, className="fw-semibold small text-muted"), md=4),
                dbc.Col(html.Span(str(v), className="small"), md=8),
            ], className="mb-2 border-bottom pb-1"))
    fields.append(html.Hr())
    fields.append(html.Small(f"Created by {row.get('CreatedBy', '')} at {row.get('CreatedAt', '')}", className="text-muted"))

    save_style = {"display": "inline-block"} if mode == "edit" else {"display": "none"}
    return True, title, html.Div(fields), save_style, rid, mode


@callback(
    [Output("proj-modal", "is_open", allow_duplicate=True), Output("proj-submit-msg", "children", allow_duplicate=True)],
    Input("proj-modal-save", "n_clicks"),
    [State("proj-selected-row-id", "data"),
     State({"type": "proj-edit-field", "index": ALL}, "value"),
     State({"type": "proj-edit-field", "index": ALL}, "id")],
    prevent_initial_call=True)
def save_proj_edit(n, rid, values, ids):
    if not rid or not values:
        return dash.no_update, dash.no_update
    changes = {id_obj["index"]: val for val, id_obj in zip(values, ids) if val}
    result = update_project(rid, changes)
    color = "success" if result["status"] == "success" else "danger"
    return False, dbc.Alert(f"{result['message']} Click Refresh.", color=color, duration=5000)


@callback(Output("proj-delete-msg", "children"),
    Input({"type": "proj-del-btn", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def del_proj(nc):
    if not ctx.triggered_id or not isinstance(ctx.triggered_id, dict):
        return dash.no_update
    if not any(c for c in nc if c):
        return dash.no_update
    delete_project(ctx.triggered_id["index"])
    return dbc.Alert("Project deleted. Click Refresh.", color="warning", duration=4000)


# ═══════════════════════════════════════════════════════════════════════
#  TAB 2: RESOURCE UTILIZATION (Calendar View)
# ═══════════════════════════════════════════════════════════════════════
def tab_resource():
    today = date.today()
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Resource Utilization", className="text-primary fw-bold"), md=4),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button(html.I(className="fas fa-chevron-left"), id="cal-prev", color="secondary", size="sm", outline=True),
                    html.Span(id="cal-month-label", className="px-3 align-self-center fw-bold", style={"fontSize": "16px"}),
                    dbc.Button(html.I(className="fas fa-chevron-right"), id="cal-next", color="secondary", size="sm", outline=True),
                ], className="me-3"),
            ], md=4, className="text-center"),
            dbc.Col([
                dbc.Button([html.I(className="fas fa-sync me-1"), "Refresh"], id="res-refresh-btn", color="secondary", size="sm", outline=True, className="me-2"),
                dbc.Button([html.I(className="fas fa-table me-1"), "Manager View"], id="res-manager-btn", color="primary", size="sm"),
            ], md=4, className="text-end"),
        ], className="mb-3 align-items-center"),

        # Calendar month/year store
        dcc.Store(id="cal-year", data=today.year),
        dcc.Store(id="cal-month", data=today.month),

        # Calendar Grid
        html.Div(id="cal-grid"),

        # Manager Summary (collapsible)
        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                html.H5("Manager Summary", className="text-primary mb-3"),
                html.Div(id="manager-summary-content"),
            ]), className="shadow-sm mt-3"),
            id="manager-collapse", is_open=False,
        ),

        # Entry Modal (opens when clicking a date)
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="res-modal-title")),
            dbc.ModalBody([
                html.Div(id="res-existing-entries"),
                html.Hr(),
                html.H6("Add New Entry", className="text-primary"),
                dbc.Row([mf("BU", mdd("res-bu"), 4), mf("Designer Name", mdd("res-designer"), 4),
                    mf("Reporting Manager", mi("res-manager"), 4)]),
                html.H6("Hours Breakdown", className="mt-2 mb-2 text-muted small"),
                dbc.Row([mf("Project Task N/A", mi("res-proj-task", "number", "0"), 3),
                    mf("Stakeholder Touchpoints", mi("res-stakeholder", "number", "0"), 3),
                    mf("Internal Team Meetings", mi("res-meetings", "number", "0"), 3),
                    mf("GCH Trainings", mi("res-gch", "number", "0"), 3)]),
                dbc.Row([mf("Tools & Tech", mi("res-tools", "number", "0"), 3),
                    mf("Innovation/Process", mi("res-innovation", "number", "0"), 3),
                    mf("Cross Functional", mi("res-cross", "number", "0"), 3),
                    mf("Site/GCH Activities", mi("res-site", "number", "0"), 3)]),
                dbc.Row([mf("Townhalls/HR/IT", mi("res-townhall", "number", "0"), 3),
                    mf("One:One", mi("res-oneone", "number", "0"), 3),
                    mf("SuccessFactor/LinkedIn", mi("res-sf", "number", "0"), 3),
                    mf("Other Trainings", mi("res-other-train", "number", "0"), 3)]),
                dbc.Row([mf("Hiring/Onboarding", mi("res-hiring", "number", "0"), 3),
                    mf("Leaves/Holidays", mi("res-leaves", "number", "0"), 3),
                    mf("Open Time", mi("res-open", "number", "0"), 3),
                    mf("Total Hours", mi("res-total-hours", "number", "0"), 3)]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Save Entry", id="res-submit-btn", color="primary", className="me-2"),
                dbc.Button("Close", id="res-modal-close", color="secondary"),
            ]),
        ], id="res-modal", size="xl", scrollable=True, is_open=False),
        dcc.Store(id="res-selected-date"),
        html.Div(id="res-submit-msg"),
        html.Div(id="res-delete-msg"),
    ], fluid=True, className="py-3")


# Navigate months
@callback([Output("cal-year", "data"), Output("cal-month", "data")],
    [Input("cal-prev", "n_clicks"), Input("cal-next", "n_clicks")],
    [State("cal-year", "data"), State("cal-month", "data")], prevent_initial_call=True)
def nav_month(prev, nxt, year, month):
    if ctx.triggered_id == "cal-prev":
        if month == 1:
            return year - 1, 12
        return year, month - 1
    else:
        if month == 12:
            return year + 1, 1
        return year, month + 1


# Build Calendar Grid
@callback([Output("cal-grid", "children"), Output("cal-month-label", "children")],
    [Input("cal-year", "data"), Input("cal-month", "data"),
     Input("res-refresh-btn", "n_clicks"), Input("tabs", "active_tab")])
def build_calendar(year, month, refresh, tab):
    if tab != "tab-resource" and not refresh:
        return dash.no_update, dash.no_update

    month_name = calendar.month_name[month]
    label = f"{month_name} {year}"

    # Get existing entries for this month
    df = get_all_resources(force_refresh=True)
    entries_by_date = {}
    if not df.empty and "Date" in df.columns:
        for _, row in df.iterrows():
            d = str(row.get("Date", ""))[:10]
            if d.startswith(f"{year}-{month:02d}"):
                if d not in entries_by_date:
                    entries_by_date[d] = []
                entries_by_date[d].append(row)

    # Build calendar
    cal = calendar.monthcalendar(year, month)
    today = date.today()

    header = html.Tr([html.Th(d, className="text-center small fw-bold text-muted", style={"padding": "8px"})
        for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]])

    rows = []
    for week in cal:
        cells = []
        for day in week:
            if day == 0:
                cells.append(html.Td("", style={"backgroundColor": "#F1F5F9", "height": "80px", "width": "14.28%"}))
            else:
                dt_str = f"{year}-{month:02d}-{day:02d}"
                is_today = (date(year, month, day) == today)
                entries = entries_by_date.get(dt_str, [])
                entry_count = len(entries)

                # Day cell content
                day_content = [
                    html.Div(str(day), className="fw-bold small" + (" text-white" if is_today else ""),
                        style={"backgroundColor": C["accent"] if is_today else "transparent",
                               "borderRadius": "50%", "width": "24px", "height": "24px",
                               "display": "flex", "alignItems": "center", "justifyContent": "center"}),
                ]
                if entry_count > 0:
                    total_hrs = sum(float(e.get("TotalHours", 0) or 0) for e in entries)
                    day_content.append(
                        dbc.Badge(f"{entry_count} entry | {total_hrs:.0f}h",
                            color="success", className="mt-1", style={"fontSize": "9px"})
                    )

                cells.append(html.Td(
                    html.Div(day_content, id={"type": "cal-day", "index": dt_str},
                        style={"cursor": "pointer", "height": "70px", "padding": "4px"},
                        className="h-100"),
                    style={"backgroundColor": "#ECFDF5" if entry_count > 0 else "white",
                           "border": f"2px solid {C['accent']}" if is_today else "1px solid #E2E8F0",
                           "verticalAlign": "top", "width": "14.28%"},
                    className="position-relative",
                ))
        rows.append(html.Tr(cells))

    table = dbc.Table([html.Thead(header), html.Tbody(rows)],
        bordered=True, className="mb-0", style={"tableLayout": "fixed"})

    return table, label


# Open entry modal when clicking a date
@callback(
    [Output("res-modal", "is_open"), Output("res-modal-title", "children"),
     Output("res-selected-date", "data"), Output("res-existing-entries", "children")],
    [Input({"type": "cal-day", "index": ALL}, "n_clicks"), Input("res-modal-close", "n_clicks")],
    prevent_initial_call=True)
def open_res_modal(day_clicks, close_click):
    if ctx.triggered_id == "res-modal-close":
        return False, "", None, ""

    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not any(c for c in day_clicks if c):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    dt_str = triggered["index"]

    # Show existing entries for this date
    df = get_all_resources()
    existing = []
    if not df.empty and "Date" in df.columns:
        day_entries = df[df["Date"].astype(str).str.startswith(dt_str)]
        if not day_entries.empty:
            for _, row in day_entries.iterrows():
                rid = row.get("RowID", "")
                existing.append(dbc.Card(dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Span(f"{row.get('DesignerName', 'Unknown')} ", className="fw-bold small"),
                            html.Span(f"| {row.get('BU', '')} | {row.get('TotalHours', 0)}h", className="small text-muted"),
                        ], md=9),
                        dbc.Col([
                            dbc.Button([html.I(className="fas fa-trash")], id={"type": "res-del-btn", "index": rid},
                                color="danger", size="sm", outline=True),
                        ], md=3, className="text-end"),
                    ]),
                ]), className="mb-2 shadow-sm"))

    existing_div = html.Div([
        html.H6(f"Existing Entries ({len(existing)})", className="text-muted mb-2"),
        html.Div(existing if existing else [html.P("No entries for this date.", className="text-muted small")]),
    ])

    title = f"Resource Entry — {dt_str}"
    return True, title, dt_str, existing_div


# Submit resource entry
@callback(
    [Output("res-submit-msg", "children"), Output("res-modal", "is_open", allow_duplicate=True),
     # Clear all form fields after submit
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
     State("res-open", "value"), State("res-total-hours", "value")],
    prevent_initial_call=True)
def submit_res(n, dt, bu, des, mgr, pt, sh, mtg, gch, tools, innov, cross, site, town, oo, sf, ot, hire, leave, opn, tot):
    data = {"Date": dt, "BU": bu, "DesignerName": des, "ReportingManager": mgr, "ProjectTaskNA": pt,
        "StakeholderTouchpoints": sh, "InternalTeamMeetings": mtg, "GCHTrainings": gch, "ToolsTechTesting": tools,
        "InnovationProcessImprovement": innov, "CrossFunctionalSupports": cross, "SiteGCHActivities": site,
        "TownhallsHRIT": town, "OneOne": oo, "SuccessFactorLinkedIn": sf, "OtherTrainings": ot,
        "HiringOnboarding": hire, "LeavesHolidays": leave, "OpenTime": opn, "TotalHours": tot}
    r = submit_resource(data)
    msg = dbc.Alert(r["message"], color="success" if r["status"] == "success" else "danger", duration=4000)
    # Return: msg, close modal, then clear all 17 form fields
    return [msg, False, None, None, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]


# Delete resource entry
@callback(Output("res-delete-msg", "children"),
    Input({"type": "res-del-btn", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def del_res(nc):
    if not ctx.triggered_id or not isinstance(ctx.triggered_id, dict):
        return dash.no_update
    if not any(c for c in nc if c):
        return dash.no_update
    delete_resource(ctx.triggered_id["index"])
    return dbc.Alert("Deleted. Click Refresh.", color="warning", duration=4000)


# Manager View toggle
@callback(Output("manager-collapse", "is_open"),
    Input("res-manager-btn", "n_clicks"), State("manager-collapse", "is_open"), prevent_initial_call=True)
def toggle_manager(n, is_open):
    return not is_open


@callback(Output("manager-summary-content", "children"),
    Input("manager-collapse", "is_open"),
    [State("cal-year", "data"), State("cal-month", "data")], prevent_initial_call=True)
def load_manager_summary(is_open, year, month):
    if not is_open:
        return ""
    df = get_all_resources(force_refresh=True)
    if df.empty:
        return dbc.Alert("No resource data yet.", color="info")

    # Filter to current month
    month_prefix = f"{year}-{month:02d}"
    if "Date" in df.columns:
        df = df[df["Date"].astype(str).str.startswith(month_prefix)]

    if df.empty:
        return dbc.Alert(f"No entries for {calendar.month_name[month]} {year}.", color="info")

    # Summary by designer
    num_cols = ["ProjectTaskNA", "StakeholderTouchpoints", "InternalTeamMeetings", "GCHTrainings",
        "ToolsTechTesting", "InnovationProcessImprovement", "CrossFunctionalSupports", "SiteGCHActivities",
        "TownhallsHRIT", "OneOne", "SuccessFactorLinkedIn", "OtherTrainings",
        "HiringOnboarding", "LeavesHolidays", "OpenTime", "TotalHours"]

    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "DesignerName" in df.columns and "TotalHours" in df.columns:
        summary = df.groupby("DesignerName").agg(
            Entries=("RowID", "count"),
            TotalHours=("TotalHours", "sum"),
            Meetings=("InternalTeamMeetings", "sum"),
            Leaves=("LeavesHolidays", "sum"),
        ).reset_index()

        return dbc.Table([
            html.Thead(html.Tr([html.Th(c, style=TH) for c in ["Designer", "Entries", "Total Hours", "Meetings", "Leaves"]])),
            html.Tbody([html.Tr([
                html.Td(row["DesignerName"], className="small fw-bold"),
                html.Td(row["Entries"], className="small"),
                html.Td(f"{row['TotalHours']:.0f}h", className="small"),
                html.Td(f"{row['Meetings']:.0f}h", className="small"),
                html.Td(f"{row['Leaves']:.0f}h", className="small"),
            ]) for _, row in summary.iterrows()]),
        ], bordered=True, hover=True, size="sm")
    else:
        return dbc.Alert("Missing columns in data.", color="warning")


# ═══════════════════════════════════════════════════════════════════════
#  TAB 3: SETTINGS
# ═══════════════════════════════════════════════════════════════════════
DD_FIELDS = [
    {"label": "BU", "value": "BU"}, {"label": "Project Type", "value": "ProjectType"},
    {"label": "Classification Media", "value": "ClassificationMedia"}, {"label": "Tactic Type", "value": "TacticType"},
    {"label": "Internal Status", "value": "InternalStatus"}, {"label": "Assigner Name", "value": "AssignerName"},
    {"label": "Designer Assigned", "value": "DesignerAssigned"}, {"label": "QC Reviewer", "value": "QCReviewer"},
    {"label": "Mail Sent", "value": "MailSent"}, {"label": "Tactic Stage", "value": "TacticStage"},
    {"label": "Stakeholder", "value": "Stakeholder"}, {"label": "Complexity", "value": "Complexity"},
    {"label": "Content Status", "value": "ContentStatus"}, {"label": "Revision 1", "value": "Revision1"},
    {"label": "Revision 2", "value": "Revision2"}, {"label": "Revision 3+", "value": "Revision3OrMore"},
]

def tab_settings():
    return dbc.Container([
        html.H4("Settings — Manage Dropdowns", className="text-primary fw-bold mb-3"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Select Field", className="text-muted mb-2"),
                dcc.Dropdown(id="settings-field-select", options=DD_FIELDS, placeholder="Select..."),
                html.Hr(),
                html.H6("Or Add New", className="text-muted mb-2"),
                dbc.InputGroup([dbc.Input(id="settings-new-field", placeholder="Field name"),
                    dbc.Button("Add", id="settings-add-field-btn", color="primary", size="sm")]),
                html.Div(id="settings-add-field-msg", className="mt-2"),
            ]), className="shadow-sm"), md=4),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6(id="settings-edit-title", children="Select a field", className="text-muted mb-2"),
                dbc.Textarea(id="settings-values-textarea", placeholder="One value per line...", style={"height": "300px"}),
                html.Hr(),
                dbc.Row([
                    dbc.Col(dbc.Button("Save Values", id="settings-save-btn", color="success", className="me-2"), width="auto"),
                    dbc.Col(html.Div(id="settings-save-msg"), className="align-self-center"),
                ]),
            ]), className="shadow-sm"), md=8),
        ]),
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
    try:
        save_lookup_values(f, vals)
        return dbc.Alert(f"Saved {len(vals)} values!", color="success", duration=3000)
    except Exception as e:
        return dbc.Alert(f"Error: {e}", color="danger", duration=5000)

@callback([Output("settings-field-select", "options"), Output("settings-add-field-msg", "children")],
    Input("settings-add-field-btn", "n_clicks"), State("settings-new-field", "value"), prevent_initial_call=True)
def add_f(n, nf):
    if not nf: return dash.no_update, dbc.Alert("Enter name.", color="warning", duration=3000)
    fn = nf.strip().replace(" ", "")
    save_lookup_values(fn, [])
    clear_cache()
    opts = sorted(set([d["value"] for d in DD_FIELDS] + get_all_lookup_fields() + [fn]))
    return [{"label": f, "value": f} for f in opts], dbc.Alert(f"Added: {fn}", color="success", duration=3000)


# ═══════════════════════════════════════════════════════════════════════
#  LAZY LOAD DROPDOWNS
# ═══════════════════════════════════════════════════════════════════════
DD_MAP = {
    "proj-bu": "BU", "proj-type": "ProjectType", "proj-media": "ClassificationMedia",
    "proj-tactic": "TacticType", "proj-status": "InternalStatus", "proj-assigner": "AssignerName",
    "proj-designer": "DesignerAssigned", "proj-qc": "QCReviewer", "proj-mail": "MailSent",
    "proj-stage": "TacticStage", "proj-stakeholder": "Stakeholder", "proj-complexity": "Complexity",
    "proj-content-status": "ContentStatus", "proj-rev1": "Revision1", "proj-rev2": "Revision2",
    "proj-rev3": "Revision3OrMore", "res-bu": "BU", "res-designer": "DesignerAssigned",
}

@callback([Output(dd, "options") for dd in DD_MAP.keys()],
    [Input("proj-new-btn", "n_clicks"), Input("res-submit-btn", "n_clicks"),
     Input("proj-refresh-btn", "n_clicks"), Input("res-refresh-btn", "n_clicks"),
     Input("tabs", "active_tab")])
def load_dd(n1, n2, n3, n4, tab):
    if tab not in ("tab-projects", "tab-resource") and not any([n1, n2, n3, n4]):
        return [dash.no_update] * len(DD_MAP)
    try:
        from db_connection import read_table
        df = read_table("Lookups")
    except Exception:
        df = pd.DataFrame()
    results = []
    for dd, ln in DD_MAP.items():
        if df.empty or "FieldName" not in df.columns:
            results.append([])
        else:
            results.append([{"label": v, "value": v} for v in df[df["FieldName"] == ln].sort_values("Value")["Value"].tolist()])
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

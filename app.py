"""
app.py - Medical Creatives UT
Features: Analytics | Project Summary (CRUD) | Resource Utilization (CRUD) | Settings
"""

import os, json
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback, ctx, ALL, MATCH
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from db_operations import (
    get_all_projects, submit_project, update_project, delete_project,
    get_all_resources, submit_resource, delete_resource,
    get_dropdown_options, get_lookup_values, save_lookup_values,
    get_all_lookup_fields, clear_cache,
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True, title="Medical Creatives UT")
server = app.server

COLORS = {"primary": "#1E2761", "accent": "#3B82F6", "success": "#10B981",
    "danger": "#EF4444", "bg": "#F8FAFC", "card": "#FFFFFF", "text": "#1E293B", "muted": "#64748B"}

TH = {"backgroundColor": COLORS["primary"], "color": "white", "fontWeight": "bold", "fontSize": "12px"}
TC = {"fontSize": "12px", "padding": "8px", "textAlign": "left"}
TD = [{"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFC"}]

# ── Helpers ───────────────────────────────────────────────────────────
def make_field(label, component, width=4):
    return dbc.Col([dbc.Label(label, className="fw-semibold small text-muted mb-1"), component], md=width, className="mb-3")

def make_dropdown(field_id, placeholder="Select..."):
    return dcc.Dropdown(id=field_id, options=[], placeholder=placeholder, className="mb-0")

def make_input(field_id, input_type="text", placeholder=""):
    return dbc.Input(id=field_id, type=input_type, placeholder=placeholder, size="sm")

def make_date(field_id):
    return dcc.DatePickerSingle(id=field_id, date=None, display_format="YYYY-MM-DD", className="w-100")

def _empty_fig(msg="Click 'Refresh Data' to load"):
    fig = go.Figure()
    fig.update_layout(annotations=[{"text": msg, "xref": "paper", "yref": "paper",
        "showarrow": False, "font": {"size": 16, "color": "#94A3B8"}}],
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis={"visible": False}, yaxis={"visible": False}, height=300)
    return fig


# ═══════════════════════════════════════════════════════════════════════
#  TAB 1: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════
def tab_analytics():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Analytics Dashboard", className="text-primary fw-bold"), md=8),
            dbc.Col(dbc.Button("Refresh Data", id="analytics-refresh", color="primary", size="sm", className="float-end"), md=4),
        ], className="mb-4 align-items-center"),
        html.Div(id="analytics-kpis"),
        dbc.Row([dbc.Col(dcc.Graph(id="chart-status"), md=6), dbc.Col(dcc.Graph(id="chart-bu"), md=6)], className="mb-3"),
        dbc.Row([dbc.Col(dcc.Graph(id="chart-complexity"), md=6), dbc.Col(dcc.Graph(id="chart-timeline"), md=6)]),
    ], fluid=True, className="py-3")

@callback([Output("analytics-kpis", "children"), Output("chart-status", "figure"),
    Output("chart-bu", "figure"), Output("chart-complexity", "figure"), Output("chart-timeline", "figure")],
    Input("analytics-refresh", "n_clicks"), prevent_initial_call=True)
def update_analytics(n):
    df = get_all_projects(force_refresh=True)
    total = len(df)
    ip = len(df[df["InternalStatus"] == "In Progress"]) if not df.empty and "InternalStatus" in df.columns else 0
    comp = len(df[df["InternalStatus"] == "Completed"]) if not df.empty and "InternalStatus" in df.columns else 0
    oh = len(df[df["InternalStatus"] == "On Hold"]) if not df.empty and "InternalStatus" in df.columns else 0
    kpis = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H2(total, className="text-primary fw-bold mb-0"), html.P("Total", className="text-muted small mb-0")]), className="shadow-sm"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H2(ip, className="text-warning fw-bold mb-0"), html.P("In Progress", className="text-muted small mb-0")]), className="shadow-sm"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H2(comp, className="text-success fw-bold mb-0"), html.P("Completed", className="text-muted small mb-0")]), className="shadow-sm"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H2(oh, className="text-danger fw-bold mb-0"), html.P("On Hold", className="text-muted small mb-0")]), className="shadow-sm"), md=3),
    ], className="mb-4")
    ef = _empty_fig("No data")
    if df.empty: return kpis, ef, ef, ef, ef
    fs = ef
    if "InternalStatus" in df.columns:
        sc = df["InternalStatus"].value_counts().reset_index(); sc.columns = ["Status", "Count"]
        fs = px.pie(sc, names="Status", values="Count", title="By Status", color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)
        fs.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20))
    fb = ef
    if "BU" in df.columns:
        bc = df["BU"].value_counts().reset_index(); bc.columns = ["BU", "Count"]
        fb = px.bar(bc, x="BU", y="Count", title="By BU", color_discrete_sequence=[COLORS["accent"]])
        fb.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20), showlegend=False)
    fc = ef
    if "Complexity" in df.columns:
        cc = df["Complexity"].value_counts().reset_index(); cc.columns = ["Complexity", "Count"]
        fc = px.pie(cc, names="Complexity", values="Count", title="By Complexity", color_discrete_sequence=["#10B981","#F59E0B","#EF4444"], hole=0.4)
        fc.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20))
    ft = ef
    if "AssignedDate" in df.columns:
        try:
            df["AssignedDate"] = pd.to_datetime(df["AssignedDate"], errors="coerce")
            tl = df.groupby(df["AssignedDate"].dt.to_period("M")).size().reset_index(); tl.columns = ["Month","Count"]; tl["Month"] = tl["Month"].astype(str)
            ft = px.line(tl, x="Month", y="Count", title="Over Time", markers=True, color_discrete_sequence=[COLORS["accent"]])
            ft.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20))
        except: pass
    return kpis, fs, fb, fc, ft


# ═══════════════════════════════════════════════════════════════════════
#  TAB 2: PROJECT SUMMARY (with View/Edit/Delete)
# ═══════════════════════════════════════════════════════════════════════
def tab_project_summary():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Project Summary", className="text-primary fw-bold"), md=6),
            dbc.Col([
                dbc.Button("New Project", id="proj-new-btn", color="success", size="sm", className="me-2"),
                dbc.Button("Refresh", id="proj-refresh-btn", color="secondary", size="sm", outline=True),
            ], md=6, className="text-end"),
        ], className="mb-3 align-items-center"),

        # New Project Form
        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                html.H5("Add New Project", className="mb-3 text-primary"),
                dbc.Row([make_field("Assigned Date", make_date("proj-assigned-date"), 3), make_field("Project Name", make_input("proj-name", placeholder="Project name"), 3),
                    make_field("BU", make_dropdown("proj-bu"), 3), make_field("Project ID", make_input("proj-id", placeholder="Project ID"), 3)]),
                dbc.Row([make_field("Veeva ID", make_input("proj-veeva-id"), 3), make_field("Project Type", make_dropdown("proj-type"), 3),
                    make_field("Classification Media", make_dropdown("proj-media"), 3), make_field("Page/Slide #", make_input("proj-page-slide", "number", "0"), 3)]),
                dbc.Row([make_field("Tactic Type", make_dropdown("proj-tactic"), 3), make_field("Internal Status", make_dropdown("proj-status"), 3),
                    make_field("First Proof Due", make_date("proj-proof-due"), 3), make_field("Assigner Name", make_dropdown("proj-assigner"), 3)]),
                dbc.Row([make_field("Designer Assigned", make_dropdown("proj-designer"), 3), make_field("QC Reviewer", make_dropdown("proj-qc"), 3),
                    make_field("Mail Sent", make_dropdown("proj-mail"), 3), make_field("QC Emailer", make_input("proj-qc-emailer"), 3)]),
                dbc.Row([make_field("Tactic Stage", make_dropdown("proj-stage"), 3), make_field("Stakeholder", make_dropdown("proj-stakeholder"), 3),
                    make_field("Complexity", make_dropdown("proj-complexity"), 3), make_field("Content Status", make_dropdown("proj-content-status"), 3)]),
                dbc.Row([make_field("Revision 1", make_dropdown("proj-rev1"), 3), make_field("Revision 2", make_dropdown("proj-rev2"), 3),
                    make_field("Revision 3+", make_dropdown("proj-rev3"), 3), make_field("Comments", make_input("proj-comments"), 3)]),
                dbc.Row([make_field("GD Rework %", make_input("proj-gd-pct", "number", "0"), 2), make_field("POC Rework %", make_input("proj-poc-pct", "number", "0"), 2),
                    make_field("Asset #", make_input("proj-asset", "number", "0"), 2), make_field("Total #", make_input("proj-total", "number", "0"), 2),
                    make_field("Simple #", make_input("proj-simple", "number", "0"), 2), make_field("Medium #", make_input("proj-medium", "number", "0"), 2)]),
                dbc.Row([make_field("Complex #", make_input("proj-complex", "number", "0"), 2), make_field("Derivatives #", make_input("proj-deriv", "number", "0"), 2),
                    make_field("GD Rework", make_input("proj-gd-rework", "number", "0"), 2), make_field("POC Rework", make_input("proj-poc-rework", "text"), 2),
                    make_field("Total Assets", make_input("proj-total-assets", "number", "0"), 2), make_field("Total GD Rework", make_input("proj-total-gd", "number", "0"), 2)]),
                html.Hr(),
                dbc.Row([dbc.Col(dbc.Button("Submit", id="proj-submit-btn", color="primary", className="me-2"), width="auto"),
                    dbc.Col(dbc.Button("Cancel", id="proj-cancel-btn", color="secondary", outline=True), width="auto"),
                    dbc.Col(html.Div(id="proj-submit-msg"), className="align-self-center")]),
            ]), className="shadow-sm mb-3"),
            id="proj-form-collapse", is_open=False),

        # Data Table with Actions
        html.Div(id="proj-table-container"),

        # View/Edit Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="proj-modal-title")),
            dbc.ModalBody(id="proj-modal-body"),
            dbc.ModalFooter([
                dbc.Button("Save Changes", id="proj-modal-save", color="primary", className="me-2", style={"display": "none"}),
                dbc.Button("Close", id="proj-modal-close", color="secondary"),
            ]),
        ], id="proj-modal", size="xl", scrollable=True),

        # Hidden stores
        dcc.Store(id="proj-selected-row-id"),
        dcc.Store(id="proj-modal-mode"),  # "view" or "edit"
        html.Div(id="proj-delete-msg"),
    ], fluid=True, className="py-3")


@callback(Output("proj-form-collapse", "is_open"),
    [Input("proj-new-btn", "n_clicks"), Input("proj-cancel-btn", "n_clicks")],
    State("proj-form-collapse", "is_open"), prevent_initial_call=True)
def toggle_proj_form(n1, n2, is_open):
    return True if ctx.triggered_id == "proj-new-btn" else False


@callback([Output("proj-submit-msg", "children"), Output("proj-table-container", "children", allow_duplicate=True)],
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
    if not name: return dbc.Alert("Project Name required.", color="danger", duration=3000), dash.no_update
    data = {"AssignedDate": ad, "ProjectName": name, "BU": bu, "ProjectID": pid, "VeevaID": vid, "ProjectType": pt,
        "ClassificationMedia": media, "PageSlide": ps, "TacticType": tactic, "InternalStatus": status,
        "FirstProofDue": pf, "AssignerName": assigner, "DesignerAssigned": designer, "QCReviewer": qc,
        "MailSent": mail, "QCEmailer": qce, "TacticStage": stage, "Stakeholder": sh,
        "Complexity": comp, "ContentStatus": cs, "Revision1": r1, "Revision2": r2, "Revision3OrMore": r3,
        "Comments": comments, "GDReworkPct": gp, "POCReworkPct": pp, "Asset": asset, "Total": total,
        "Simple": simple, "Medium": med, "Complex": cmplx, "Derivatives": deriv,
        "GDRework": gr, "POCRework": pr, "TotalAssets": ta, "TotalGDRework": tg}
    result = submit_project(data)
    return dbc.Alert(result["message"], color="success" if result["status"] == "success" else "danger", duration=4000), build_proj_table()


@callback(Output("proj-table-container", "children"), Input("proj-refresh-btn", "n_clicks"), prevent_initial_call=True)
def refresh_proj(n): return build_proj_table()


def build_proj_table():
    df = get_all_projects(force_refresh=True)
    if df.empty:
        return dbc.Alert("No projects yet. Click 'New Project' to add one.", color="info")

    rows = []
    for _, row in df.iterrows():
        row_id = row.get("RowID", "")
        rows.append(
            html.Tr([
                html.Td(row.get("ProjectName", ""), className="small"),
                html.Td(row.get("BU", ""), className="small"),
                html.Td(row.get("InternalStatus", ""), className="small"),
                html.Td(row.get("Complexity", ""), className="small"),
                html.Td(row.get("DesignerAssigned", ""), className="small"),
                html.Td(row.get("AssignedDate", ""), className="small"),
                html.Td([
                    dbc.Button("View", id={"type": "proj-view-btn", "index": row_id}, color="info", size="sm", className="me-1"),
                    dbc.Button("Edit", id={"type": "proj-edit-btn", "index": row_id}, color="warning", size="sm", className="me-1"),
                    dbc.Button("Delete", id={"type": "proj-del-btn", "index": row_id}, color="danger", size="sm", outline=True),
                ], className="text-nowrap"),
            ])
        )

    return dbc.Table([
        html.Thead(html.Tr([html.Th(c, style={"backgroundColor": COLORS["primary"], "color": "white", "fontSize": "12px"})
            for c in ["Project Name", "BU", "Status", "Complexity", "Designer", "Date", "Actions"]])),
        html.Tbody(rows),
    ], bordered=True, hover=True, responsive=True, size="sm", className="mt-2")


# View/Edit Modal
@callback(
    [Output("proj-modal", "is_open"), Output("proj-modal-title", "children"),
     Output("proj-modal-body", "children"), Output("proj-modal-save", "style"),
     Output("proj-selected-row-id", "data"), Output("proj-modal-mode", "data")],
    [Input({"type": "proj-view-btn", "index": ALL}, "n_clicks"),
     Input({"type": "proj-edit-btn", "index": ALL}, "n_clicks"),
     Input("proj-modal-close", "n_clicks")],
    prevent_initial_call=True)
def open_proj_modal(view_clicks, edit_clicks, close_click):
    if not ctx.triggered_id or ctx.triggered_id == "proj-modal-close":
        return False, "", "", {"display": "none"}, None, None

    triggered = ctx.triggered_id
    row_id = triggered["index"]
    mode = "edit" if triggered["type"] == "proj-edit-btn" else "view"

    df = get_all_projects()
    if df.empty or "RowID" not in df.columns:
        return False, "", "", {"display": "none"}, None, None
    row = df[df["RowID"] == row_id]
    if row.empty:
        return False, "", "", {"display": "none"}, None, None
    row = row.iloc[0]

    title = f"{'Edit' if mode == 'edit' else 'View'} Project: {row.get('ProjectName', '')}"

    # Build field display
    fields = []
    skip = ["RowID", "CreatedBy", "CreatedAt", "UpdatedBy", "UpdatedAt"]
    for col in df.columns:
        if col in skip: continue
        val = row.get(col, "")
        if pd.isna(val): val = ""

        if mode == "edit":
            fields.append(dbc.Row([
                dbc.Col(dbc.Label(col, className="fw-semibold small"), md=4),
                dbc.Col(dbc.Input(id={"type": "proj-edit-field", "index": col}, value=str(val), size="sm"), md=8),
            ], className="mb-2"))
        else:
            fields.append(dbc.Row([
                dbc.Col(html.Span(col, className="fw-semibold small text-muted"), md=4),
                dbc.Col(html.Span(str(val), className="small"), md=8),
            ], className="mb-2 border-bottom pb-1"))

    # Add audit info at bottom
    fields.append(html.Hr())
    fields.append(html.Small(f"Created by {row.get('CreatedBy','')} at {row.get('CreatedAt','')}", className="text-muted"))

    save_style = {"display": "inline-block"} if mode == "edit" else {"display": "none"}
    return True, title, html.Div(fields), save_style, row_id, mode


@callback(
    [Output("proj-modal", "is_open", allow_duplicate=True), Output("proj-submit-msg", "children", allow_duplicate=True)],
    Input("proj-modal-save", "n_clicks"),
    [State("proj-selected-row-id", "data"),
     State({"type": "proj-edit-field", "index": ALL}, "value"),
     State({"type": "proj-edit-field", "index": ALL}, "id")],
    prevent_initial_call=True)
def save_proj_edit(n_clicks, row_id, values, ids):
    if not row_id or not values: return dash.no_update, dash.no_update
    changes = {}
    for val, id_obj in zip(values, ids):
        col = id_obj["index"]
        if val: changes[col] = val
    result = update_project(row_id, changes)
    color = "success" if result["status"] == "success" else "danger"
    return False, dbc.Alert(f"{result['message']} Click Refresh to see changes.", color=color, duration=5000)


# Delete Project
@callback(
    Output("proj-delete-msg", "children"),
    Input({"type": "proj-del-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True)
def del_proj(n_clicks):
    if not ctx.triggered_id or not any(n_clicks): return dash.no_update
    row_id = ctx.triggered_id["index"]
    delete_project(row_id)
    return dbc.Alert("Project deleted. Click Refresh to update.", color="warning", duration=4000)


# ═══════════════════════════════════════════════════════════════════════
#  TAB 3: RESOURCE UTILIZATION (with View/Edit/Delete)
# ═══════════════════════════════════════════════════════════════════════
def tab_resource_utilization():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Resource Utilization Tracker", className="text-primary fw-bold"), md=6),
            dbc.Col([
                dbc.Button("New Entry", id="res-new-btn", color="success", size="sm", className="me-2"),
                dbc.Button("Refresh", id="res-refresh-btn", color="secondary", size="sm", outline=True),
            ], md=6, className="text-end"),
        ], className="mb-3 align-items-center"),

        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                html.H5("Add Resource Entry", className="mb-3 text-primary"),
                dbc.Row([make_field("Date", make_date("res-date"), 3), make_field("BU", make_dropdown("res-bu"), 3),
                    make_field("Designer Name", make_dropdown("res-designer"), 3), make_field("Reporting Manager", make_input("res-manager"), 3)]),
                html.H6("Hours Breakdown", className="mt-2 mb-2 text-muted"),
                dbc.Row([make_field("Project Task N/A", make_input("res-proj-task", "number", "0"), 3), make_field("Stakeholder Touchpoints", make_input("res-stakeholder", "number", "0"), 3),
                    make_field("Internal Team Meetings", make_input("res-meetings", "number", "0"), 3), make_field("GCH Trainings", make_input("res-gch", "number", "0"), 3)]),
                dbc.Row([make_field("Tools & Tech Testing", make_input("res-tools", "number", "0"), 3), make_field("Innovation/Process", make_input("res-innovation", "number", "0"), 3),
                    make_field("Cross Functional", make_input("res-cross", "number", "0"), 3), make_field("Site/GCH Activities", make_input("res-site", "number", "0"), 3)]),
                dbc.Row([make_field("Townhalls/HR/IT", make_input("res-townhall", "number", "0"), 3), make_field("One:One", make_input("res-oneone", "number", "0"), 3),
                    make_field("SuccessFactor/LinkedIn", make_input("res-sf", "number", "0"), 3), make_field("Other Trainings", make_input("res-other-train", "number", "0"), 3)]),
                dbc.Row([make_field("Hiring/Onboarding", make_input("res-hiring", "number", "0"), 3), make_field("Leaves/Holidays", make_input("res-leaves", "number", "0"), 3),
                    make_field("Open Time", make_input("res-open", "number", "0"), 3), make_field("Total Hours", make_input("res-total-hours", "number", "0"), 3)]),
                html.Hr(),
                dbc.Row([dbc.Col(dbc.Button("Submit", id="res-submit-btn", color="primary", className="me-2"), width="auto"),
                    dbc.Col(dbc.Button("Cancel", id="res-cancel-btn", color="secondary", outline=True), width="auto"),
                    dbc.Col(html.Div(id="res-submit-msg"), className="align-self-center")]),
            ]), className="shadow-sm mb-3"),
            id="res-form-collapse", is_open=False),

        html.Div(id="res-table-container"),

        # View/Edit Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="res-modal-title")),
            dbc.ModalBody(id="res-modal-body"),
            dbc.ModalFooter([
                dbc.Button("Save Changes", id="res-modal-save", color="primary", className="me-2", style={"display": "none"}),
                dbc.Button("Close", id="res-modal-close", color="secondary"),
            ]),
        ], id="res-modal", size="xl", scrollable=True),
        dcc.Store(id="res-selected-row-id"),
        dcc.Store(id="res-modal-mode"),
        html.Div(id="res-delete-msg"),
    ], fluid=True, className="py-3")


@callback(Output("res-form-collapse", "is_open"),
    [Input("res-new-btn", "n_clicks"), Input("res-cancel-btn", "n_clicks")],
    State("res-form-collapse", "is_open"), prevent_initial_call=True)
def toggle_res_form(n1, n2, is_open):
    return True if ctx.triggered_id == "res-new-btn" else False


@callback([Output("res-submit-msg", "children"), Output("res-table-container", "children", allow_duplicate=True)],
    Input("res-submit-btn", "n_clicks"),
    [State("res-date", "date"), State("res-bu", "value"), State("res-designer", "value"), State("res-manager", "value"),
     State("res-proj-task", "value"), State("res-stakeholder", "value"), State("res-meetings", "value"), State("res-gch", "value"),
     State("res-tools", "value"), State("res-innovation", "value"), State("res-cross", "value"), State("res-site", "value"),
     State("res-townhall", "value"), State("res-oneone", "value"), State("res-sf", "value"), State("res-other-train", "value"),
     State("res-hiring", "value"), State("res-leaves", "value"), State("res-open", "value"), State("res-total-hours", "value")],
    prevent_initial_call=True)
def submit_res(n, dt, bu, des, mgr, pt, sh, mtg, gch, tools, innov, cross, site, town, oo, sf, ot, hire, leave, opn, tot):
    data = {"Date": dt, "BU": bu, "DesignerName": des, "ReportingManager": mgr, "ProjectTaskNA": pt,
        "StakeholderTouchpoints": sh, "InternalTeamMeetings": mtg, "GCHTrainings": gch, "ToolsTechTesting": tools,
        "InnovationProcessImprovement": innov, "CrossFunctionalSupports": cross, "SiteGCHActivities": site,
        "TownhallsHRIT": town, "OneOne": oo, "SuccessFactorLinkedIn": sf, "OtherTrainings": ot,
        "HiringOnboarding": hire, "LeavesHolidays": leave, "OpenTime": opn, "TotalHours": tot}
    result = submit_resource(data)
    return dbc.Alert(result["message"], color="success" if result["status"] == "success" else "danger", duration=4000), build_res_table()


@callback(Output("res-table-container", "children"), Input("res-refresh-btn", "n_clicks"), prevent_initial_call=True)
def refresh_res(n): return build_res_table()


def build_res_table():
    df = get_all_resources(force_refresh=True)
    if df.empty:
        return dbc.Alert("No entries yet. Click 'New Entry' to add one.", color="info")
    rows = []
    for _, row in df.iterrows():
        rid = row.get("RowID", "")
        rows.append(html.Tr([
            html.Td(row.get("Date", ""), className="small"), html.Td(row.get("BU", ""), className="small"),
            html.Td(row.get("DesignerName", ""), className="small"), html.Td(row.get("TotalHours", ""), className="small"),
            html.Td([
                dbc.Button("View", id={"type": "res-view-btn", "index": rid}, color="info", size="sm", className="me-1"),
                dbc.Button("Edit", id={"type": "res-edit-btn", "index": rid}, color="warning", size="sm", className="me-1"),
                dbc.Button("Delete", id={"type": "res-del-btn", "index": rid}, color="danger", size="sm", outline=True),
            ], className="text-nowrap"),
        ]))
    return dbc.Table([
        html.Thead(html.Tr([html.Th(c, style={"backgroundColor": COLORS["primary"], "color": "white", "fontSize": "12px"})
            for c in ["Date", "BU", "Designer", "Total Hours", "Actions"]])),
        html.Tbody(rows),
    ], bordered=True, hover=True, responsive=True, size="sm", className="mt-2")


@callback(
    [Output("res-modal", "is_open"), Output("res-modal-title", "children"),
     Output("res-modal-body", "children"), Output("res-modal-save", "style"),
     Output("res-selected-row-id", "data"), Output("res-modal-mode", "data")],
    [Input({"type": "res-view-btn", "index": ALL}, "n_clicks"),
     Input({"type": "res-edit-btn", "index": ALL}, "n_clicks"),
     Input("res-modal-close", "n_clicks")],
    prevent_initial_call=True)
def open_res_modal(view_clicks, edit_clicks, close_click):
    if not ctx.triggered_id or ctx.triggered_id == "res-modal-close":
        return False, "", "", {"display": "none"}, None, None
    triggered = ctx.triggered_id
    row_id = triggered["index"]
    mode = "edit" if triggered["type"] == "res-edit-btn" else "view"
    df = get_all_resources()
    if df.empty or "RowID" not in df.columns: return False, "", "", {"display": "none"}, None, None
    row = df[df["RowID"] == row_id]
    if row.empty: return False, "", "", {"display": "none"}, None, None
    row = row.iloc[0]
    title = f"{'Edit' if mode == 'edit' else 'View'} Entry: {row.get('DesignerName', '')} - {row.get('Date', '')}"
    fields = []
    skip = ["RowID", "CreatedBy", "CreatedAt", "UpdatedBy", "UpdatedAt"]
    for col in df.columns:
        if col in skip: continue
        val = row.get(col, ""); val = "" if pd.isna(val) else val
        if mode == "edit":
            fields.append(dbc.Row([dbc.Col(dbc.Label(col, className="fw-semibold small"), md=4),
                dbc.Col(dbc.Input(id={"type": "res-edit-field", "index": col}, value=str(val), size="sm"), md=8)], className="mb-2"))
        else:
            fields.append(dbc.Row([dbc.Col(html.Span(col, className="fw-semibold small text-muted"), md=4),
                dbc.Col(html.Span(str(val), className="small"), md=8)], className="mb-2 border-bottom pb-1"))
    fields.append(html.Hr())
    fields.append(html.Small(f"Created by {row.get('CreatedBy','')} at {row.get('CreatedAt','')}", className="text-muted"))
    save_style = {"display": "inline-block"} if mode == "edit" else {"display": "none"}
    return True, title, html.Div(fields), save_style, row_id, mode


@callback(
    [Output("res-modal", "is_open", allow_duplicate=True), Output("res-submit-msg", "children", allow_duplicate=True)],
    Input("res-modal-save", "n_clicks"),
    [State("res-selected-row-id", "data"), State({"type": "res-edit-field", "index": ALL}, "value"),
     State({"type": "res-edit-field", "index": ALL}, "id")],
    prevent_initial_call=True)
def save_res_edit(n, row_id, values, ids):
    if not row_id or not values: return dash.no_update, dash.no_update
    changes = {id_obj["index"]: val for val, id_obj in zip(values, ids) if val}
    df = get_all_resources(force_refresh=True)
    mask = df["RowID"] == row_id
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for col, val in changes.items():
        df.loc[mask, col] = val
    df.loc[mask, "UpdatedBy"] = os.getenv("APP_USER", "unknown")
    df.loc[mask, "UpdatedAt"] = now
    from db_connection import write_table
    write_table("ResourceUtilization", df)
    clear_cache("ResourceUtilization")
    return False, dbc.Alert("Entry updated! Click Refresh to see changes.", color="success", duration=5000)


@callback(
    Output("res-delete-msg", "children"),
    Input({"type": "res-del-btn", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def del_res(n_clicks):
    if not ctx.triggered_id or not any(n_clicks): return dash.no_update
    delete_resource(ctx.triggered_id["index"])
    return dbc.Alert("Entry deleted. Click Refresh to update.", color="warning", duration=4000)


# ═══════════════════════════════════════════════════════════════════════
#  TAB 4: SETTINGS
# ═══════════════════════════════════════════════════════════════════════
DROPDOWN_FIELDS = [
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
        html.H4("Settings — Manage Dropdown Values", className="text-primary fw-bold mb-3"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Select Dropdown Field", className="text-muted mb-2"),
                dcc.Dropdown(id="settings-field-select", options=DROPDOWN_FIELDS, placeholder="Select a field..."),
                html.Hr(),
                html.H6("Or Add New Field", className="text-muted mb-2"),
                dbc.InputGroup([dbc.Input(id="settings-new-field", placeholder="New field name"),
                    dbc.Button("Add", id="settings-add-field-btn", color="primary", size="sm")]),
                html.Div(id="settings-add-field-msg", className="mt-2"),
            ]), className="shadow-sm"), md=4),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6(id="settings-edit-title", children="Select a field to edit", className="text-muted mb-2"),
                dbc.Textarea(id="settings-values-textarea", placeholder="Enter one value per line...", style={"height": "300px"}),
                html.Hr(),
                dbc.Row([dbc.Col(dbc.Button("Save Values", id="settings-save-btn", color="success", className="me-2"), width="auto"),
                    dbc.Col(html.Div(id="settings-save-msg"), className="align-self-center")]),
            ]), className="shadow-sm"), md=8),
        ]),
    ], fluid=True, className="py-3")

@callback([Output("settings-values-textarea", "value"), Output("settings-edit-title", "children")],
    Input("settings-field-select", "value"), prevent_initial_call=True)
def load_field_vals(f):
    if not f: return "", "Select a field"
    return "\n".join(get_lookup_values(f)), f"Editing: {f}"

@callback(Output("settings-save-msg", "children"), Input("settings-save-btn", "n_clicks"),
    [State("settings-field-select", "value"), State("settings-values-textarea", "value")], prevent_initial_call=True)
def save_vals(n, f, txt):
    if not f: return dbc.Alert("Select a field.", color="warning", duration=3000)
    vals = [v.strip() for v in txt.strip().split("\n") if v.strip()]
    try:
        save_lookup_values(f, vals)
        return dbc.Alert(f"Saved {len(vals)} values!", color="success", duration=3000)
    except Exception as e: return dbc.Alert(f"Error: {e}", color="danger", duration=5000)

@callback([Output("settings-field-select", "options"), Output("settings-add-field-msg", "children")],
    Input("settings-add-field-btn", "n_clicks"), State("settings-new-field", "value"), prevent_initial_call=True)
def add_field(n, nf):
    if not nf: return dash.no_update, dbc.Alert("Enter a name.", color="warning", duration=3000)
    fn = nf.strip().replace(" ", "")
    save_lookup_values(fn, []); clear_cache()
    opts = sorted(set([d["value"] for d in DROPDOWN_FIELDS] + get_all_lookup_fields() + [fn]))
    return [{"label": f, "value": f} for f in opts], dbc.Alert(f"Added: {fn}", color="success", duration=3000)


# ═══════════════════════════════════════════════════════════════════════
#  LAZY LOAD DROPDOWNS
# ═══════════════════════════════════════════════════════════════════════
DROPDOWN_MAP = {
    "proj-bu": "BU", "proj-type": "ProjectType", "proj-media": "ClassificationMedia",
    "proj-tactic": "TacticType", "proj-status": "InternalStatus", "proj-assigner": "AssignerName",
    "proj-designer": "DesignerAssigned", "proj-qc": "QCReviewer", "proj-mail": "MailSent",
    "proj-stage": "TacticStage", "proj-stakeholder": "Stakeholder", "proj-complexity": "Complexity",
    "proj-content-status": "ContentStatus", "proj-rev1": "Revision1", "proj-rev2": "Revision2",
    "proj-rev3": "Revision3OrMore", "res-bu": "BU", "res-designer": "DesignerAssigned",
}

@callback([Output(dd, "options") for dd in DROPDOWN_MAP.keys()],
    [Input("proj-new-btn", "n_clicks"), Input("res-new-btn", "n_clicks"),
     Input("proj-refresh-btn", "n_clicks"), Input("res-refresh-btn", "n_clicks")],
    prevent_initial_call=True)
def load_dropdowns(n1, n2, n3, n4):
    try:
        from db_connection import read_table
        df = read_table("Lookups")
    except: df = pd.DataFrame()
    results = []
    for dd, ln in DROPDOWN_MAP.items():
        if df.empty or "FieldName" not in df.columns: results.append([])
        else:
            vals = df[df["FieldName"] == ln].sort_values("Value")["Value"].tolist()
            results.append([{"label": v, "value": v} for v in vals])
    return results


# ═══════════════════════════════════════════════════════════════════════
#  LAYOUT
# ═══════════════════════════════════════════════════════════════════════
app.layout = html.Div([
    dbc.Navbar(dbc.Container([
        dbc.NavbarBrand([html.I(className="fas fa-palette me-2"), "Medical Creatives UT"], className="fw-bold text-white"),
        html.Span(f"User: {os.getenv('APP_USER', 'unknown')}", className="text-light small"),
    ], fluid=True), color=COLORS["primary"], dark=True, className="mb-0"),
    dbc.Tabs(id="tabs", active_tab="tab-analytics", className="px-3 pt-2", children=[
        dbc.Tab(tab_analytics(), label="Analytics", tab_id="tab-analytics", label_style={"fontWeight": "600"}),
        dbc.Tab(tab_project_summary(), label="Project Summary", tab_id="tab-projects", label_style={"fontWeight": "600"}),
        dbc.Tab(tab_resource_utilization(), label="Resource Utilization", tab_id="tab-resource", label_style={"fontWeight": "600"}),
        dbc.Tab(tab_settings(), label="Settings", tab_id="tab-settings", label_style={"fontWeight": "600"}),
    ]),
], style={"backgroundColor": COLORS["bg"], "minHeight": "100vh"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

"""
app.py
======
Medical Creatives UT — Project Management Dashboard
Tabs: Analytics | Project Summary | Resource Utilization | Settings
"""

import os
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback, ctx, ALL
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date

from db_operations import (
    get_all_projects, submit_project, delete_project,
    get_all_resources, submit_resource, delete_resource,
    get_dropdown_options, get_lookup_values, save_lookup_values,
    get_all_lookup_fields, initialize_default_lookups,
    clear_cache, test_connection,
)

# ── Initialize App ────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Medical Creatives UT",
)
server = app.server

# NOTE: No OneLake calls at startup — everything loads lazily via callbacks

# ── Color Palette ─────────────────────────────────────────────────────
COLORS = {
    "primary": "#1E2761",
    "accent": "#3B82F6",
    "success": "#10B981",
    "danger": "#EF4444",
    "bg": "#F8FAFC",
    "card": "#FFFFFF",
    "text": "#1E293B",
    "muted": "#64748B",
}

# ═══════════════════════════════════════════════════════════════════════
#  HELPER: Create a form field
# ═══════════════════════════════════════════════════════════════════════

def make_field(label, component, width=4):
    return dbc.Col([
        dbc.Label(label, className="fw-semibold small text-muted mb-1"),
        component,
    ], md=width, className="mb-3")


def make_dropdown(field_id, lookup_name, placeholder="Select...", multi=False):
    return dcc.Dropdown(
        id=field_id,
        options=[],
        placeholder=placeholder,
        multi=multi,
        className="mb-0",
    )


def make_input(field_id, input_type="text", placeholder=""):
    return dbc.Input(id=field_id, type=input_type, placeholder=placeholder, size="sm")


def make_date(field_id):
    return dcc.DatePickerSingle(id=field_id, date=None, display_format="YYYY-MM-DD", className="w-100")


# ═══════════════════════════════════════════════════════════════════════
#  TAB 1: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════

def tab_analytics():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Analytics Dashboard", className="text-primary fw-bold"), md=8),
            dbc.Col(dbc.Button("Refresh Data", id="analytics-refresh", color="primary", size="sm",
                               className="float-end"), md=4),
        ], className="mb-4 align-items-center"),

        # KPI Cards
        html.Div(id="analytics-kpis"),

        # Charts Row
        dbc.Row([
            dbc.Col(dcc.Graph(id="chart-status"), md=6),
            dbc.Col(dcc.Graph(id="chart-bu"), md=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(id="chart-complexity"), md=6),
            dbc.Col(dcc.Graph(id="chart-timeline"), md=6),
        ]),
    ], fluid=True, className="py-3")


@callback(
    [Output("analytics-kpis", "children"),
     Output("chart-status", "figure"),
     Output("chart-bu", "figure"),
     Output("chart-complexity", "figure"),
     Output("chart-timeline", "figure")],
    [Input("analytics-refresh", "n_clicks"),
     Input("tabs", "active_tab")],
)
def update_analytics(n_clicks, active_tab):
    df = get_all_projects(force_refresh=bool(n_clicks))

    # KPI Cards
    total = len(df)
    in_progress = len(df[df.get("InternalStatus", pd.Series()) == "In Progress"]) if not df.empty and "InternalStatus" in df.columns else 0
    completed = len(df[df.get("InternalStatus", pd.Series()) == "Completed"]) if not df.empty and "InternalStatus" in df.columns else 0
    on_hold = len(df[df.get("InternalStatus", pd.Series()) == "On Hold"]) if not df.empty and "InternalStatus" in df.columns else 0

    kpis = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H2(total, className="text-primary fw-bold mb-0"),
            html.P("Total Projects", className="text-muted small mb-0"),
        ]), className="shadow-sm"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H2(in_progress, className="text-warning fw-bold mb-0"),
            html.P("In Progress", className="text-muted small mb-0"),
        ]), className="shadow-sm"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H2(completed, className="text-success fw-bold mb-0"),
            html.P("Completed", className="text-muted small mb-0"),
        ]), className="shadow-sm"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H2(on_hold, className="text-danger fw-bold mb-0"),
            html.P("On Hold", className="text-muted small mb-0"),
        ]), className="shadow-sm"), md=3),
    ], className="mb-4")

    # Charts
    empty_fig = go.Figure()
    empty_fig.update_layout(
        annotations=[{"text": "No data yet", "xref": "paper", "yref": "paper",
                       "showarrow": False, "font": {"size": 16, "color": "#94A3B8"}}],
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis={"visible": False}, yaxis={"visible": False}, height=300,
    )

    if df.empty:
        return kpis, empty_fig, empty_fig, empty_fig, empty_fig

    # Status chart
    if "InternalStatus" in df.columns:
        status_counts = df["InternalStatus"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig_status = px.pie(status_counts, names="Status", values="Count", title="Projects by Status",
                            color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)
        fig_status.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20))
    else:
        fig_status = empty_fig

    # BU chart
    if "BU" in df.columns:
        bu_counts = df["BU"].value_counts().reset_index()
        bu_counts.columns = ["BU", "Count"]
        fig_bu = px.bar(bu_counts, x="BU", y="Count", title="Projects by Business Unit",
                        color_discrete_sequence=[COLORS["accent"]])
        fig_bu.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20), showlegend=False)
    else:
        fig_bu = empty_fig

    # Complexity chart
    if "Complexity" in df.columns:
        comp_counts = df["Complexity"].value_counts().reset_index()
        comp_counts.columns = ["Complexity", "Count"]
        fig_comp = px.pie(comp_counts, names="Complexity", values="Count", title="By Complexity",
                          color_discrete_sequence=["#10B981", "#F59E0B", "#EF4444"], hole=0.4)
        fig_comp.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20))
    else:
        fig_comp = empty_fig

    # Timeline chart
    if "AssignedDate" in df.columns:
        try:
            df["AssignedDate"] = pd.to_datetime(df["AssignedDate"], errors="coerce")
            timeline = df.groupby(df["AssignedDate"].dt.to_period("M")).size().reset_index()
            timeline.columns = ["Month", "Count"]
            timeline["Month"] = timeline["Month"].astype(str)
            fig_timeline = px.line(timeline, x="Month", y="Count", title="Projects Over Time",
                                   markers=True, color_discrete_sequence=[COLORS["accent"]])
            fig_timeline.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20))
        except Exception:
            fig_timeline = empty_fig
    else:
        fig_timeline = empty_fig

    return kpis, fig_status, fig_bu, fig_comp, fig_timeline


# ═══════════════════════════════════════════════════════════════════════
#  TAB 2: PROJECT SUMMARY
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

        # Form (collapsible)
        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                html.H5("Add New Project", className="mb-3 text-primary"),
                dbc.Row([
                    make_field("Assigned Date", make_date("proj-assigned-date"), 3),
                    make_field("Project Name", make_input("proj-name", placeholder="Enter project name"), 3),
                    make_field("BU", make_dropdown("proj-bu", "BU"), 3),
                    make_field("Project ID", make_input("proj-id", placeholder="Project ID"), 3),
                ]),
                dbc.Row([
                    make_field("Veeva ID", make_input("proj-veeva-id", placeholder="Veeva ID"), 3),
                    make_field("Project Type", make_dropdown("proj-type", "ProjectType"), 3),
                    make_field("Classification Media", make_dropdown("proj-media", "ClassificationMedia"), 3),
                    make_field("Page/Slide #", make_input("proj-page-slide", "number", "0"), 3),
                ]),
                dbc.Row([
                    make_field("Tactic Type", make_dropdown("proj-tactic", "TacticType"), 3),
                    make_field("Internal Status", make_dropdown("proj-status", "InternalStatus"), 3),
                    make_field("First Proof Due", make_date("proj-proof-due"), 3),
                    make_field("Assigner Name", make_dropdown("proj-assigner", "AssignerName"), 3),
                ]),
                dbc.Row([
                    make_field("Designer Assigned", make_dropdown("proj-designer", "DesignerAssigned"), 3),
                    make_field("QC Reviewer", make_dropdown("proj-qc", "QCReviewer"), 3),
                    make_field("Mail Sent", make_dropdown("proj-mail", "MailSent"), 3),
                    make_field("QC Emailer", make_input("proj-qc-emailer", placeholder="QC Emailer"), 3),
                ]),
                dbc.Row([
                    make_field("Tactic Stage", make_dropdown("proj-stage", "TacticStage"), 3),
                    make_field("Stakeholder", make_dropdown("proj-stakeholder", "Stakeholder"), 3),
                    make_field("Complexity", make_dropdown("proj-complexity", "Complexity"), 3),
                    make_field("Content Status", make_dropdown("proj-content-status", "ContentStatus"), 3),
                ]),
                dbc.Row([
                    make_field("Revision 1", make_dropdown("proj-rev1", "Revision1"), 3),
                    make_field("Revision 2", make_dropdown("proj-rev2", "Revision2"), 3),
                    make_field("Revision 3+", make_dropdown("proj-rev3", "Revision3OrMore"), 3),
                    make_field("Comments", make_input("proj-comments", placeholder="Comments"), 3),
                ]),
                dbc.Row([
                    make_field("GD Rework %", make_input("proj-gd-pct", "number", "0"), 2),
                    make_field("POC Rework %", make_input("proj-poc-pct", "number", "0"), 2),
                    make_field("Asset #", make_input("proj-asset", "number", "0"), 2),
                    make_field("Total #", make_input("proj-total", "number", "0"), 2),
                    make_field("Simple #", make_input("proj-simple", "number", "0"), 2),
                    make_field("Medium #", make_input("proj-medium", "number", "0"), 2),
                ]),
                dbc.Row([
                    make_field("Complex #", make_input("proj-complex", "number", "0"), 2),
                    make_field("Derivatives #", make_input("proj-deriv", "number", "0"), 2),
                    make_field("GD Rework", make_input("proj-gd-rework", "number", "0"), 2),
                    make_field("POC Rework", make_input("proj-poc-rework", "text", ""), 2),
                    make_field("Total Assets", make_input("proj-total-assets", "number", "0"), 2),
                    make_field("Total GD Rework", make_input("proj-total-gd", "number", "0"), 2),
                ]),
                html.Hr(),
                dbc.Row([
                    dbc.Col(dbc.Button("Submit Project", id="proj-submit-btn", color="primary", className="me-2"), width="auto"),
                    dbc.Col(dbc.Button("Cancel", id="proj-cancel-btn", color="secondary", outline=True), width="auto"),
                    dbc.Col(html.Div(id="proj-submit-msg"), className="align-self-center"),
                ]),
            ]), className="shadow-sm mb-3"),
            id="proj-form-collapse", is_open=False,
        ),

        # Data Table
        html.Div(id="proj-table-container"),
    ], fluid=True, className="py-3")


@callback(
    Output("proj-form-collapse", "is_open"),
    [Input("proj-new-btn", "n_clicks"), Input("proj-cancel-btn", "n_clicks")],
    State("proj-form-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_project_form(new_click, cancel_click, is_open):
    if ctx.triggered_id == "proj-new-btn":
        return True
    return False


@callback(
    [Output("proj-submit-msg", "children"), Output("proj-table-container", "children", allow_duplicate=True)],
    Input("proj-submit-btn", "n_clicks"),
    [
        State("proj-assigned-date", "date"), State("proj-name", "value"),
        State("proj-bu", "value"), State("proj-id", "value"),
        State("proj-veeva-id", "value"), State("proj-type", "value"),
        State("proj-media", "value"), State("proj-page-slide", "value"),
        State("proj-tactic", "value"), State("proj-status", "value"),
        State("proj-proof-due", "date"), State("proj-assigner", "value"),
        State("proj-designer", "value"), State("proj-qc", "value"),
        State("proj-mail", "value"), State("proj-qc-emailer", "value"),
        State("proj-stage", "value"), State("proj-stakeholder", "value"),
        State("proj-complexity", "value"), State("proj-content-status", "value"),
        State("proj-rev1", "value"), State("proj-rev2", "value"),
        State("proj-rev3", "value"), State("proj-comments", "value"),
        State("proj-gd-pct", "value"), State("proj-poc-pct", "value"),
        State("proj-asset", "value"), State("proj-total", "value"),
        State("proj-simple", "value"), State("proj-medium", "value"),
        State("proj-complex", "value"), State("proj-deriv", "value"),
        State("proj-gd-rework", "value"), State("proj-poc-rework", "value"),
        State("proj-total-assets", "value"), State("proj-total-gd", "value"),
    ],
    prevent_initial_call=True,
)
def submit_project_form(n_clicks,
    assigned_date, name, bu, proj_id, veeva_id, proj_type, media, page_slide,
    tactic, status, proof_due, assigner, designer, qc, mail, qc_emailer,
    stage, stakeholder, complexity, content_status,
    rev1, rev2, rev3, comments,
    gd_pct, poc_pct, asset, total, simple, medium, complex_n, deriv,
    gd_rework, poc_rework, total_assets, total_gd):

    if not name:
        return dbc.Alert("Project Name is required.", color="danger", duration=3000), dash.no_update

    data = {
        "AssignedDate": assigned_date, "ProjectName": name, "BU": bu,
        "ProjectID": proj_id, "VeevaID": veeva_id, "ProjectType": proj_type,
        "ClassificationMedia": media, "PageSlide": page_slide,
        "TacticType": tactic, "InternalStatus": status,
        "FirstProofDue": proof_due, "AssignerName": assigner,
        "DesignerAssigned": designer, "QCReviewer": qc,
        "MailSent": mail, "QCEmailer": qc_emailer,
        "TacticStage": stage, "Stakeholder": stakeholder,
        "Complexity": complexity, "ContentStatus": content_status,
        "Revision1": rev1, "Revision2": rev2, "Revision3OrMore": rev3,
        "Comments": comments, "GDReworkPct": gd_pct, "POCReworkPct": poc_pct,
        "Asset": asset, "Total": total, "Simple": simple, "Medium": medium,
        "Complex": complex_n, "Derivatives": deriv,
        "GDRework": gd_rework, "POCRework": poc_rework,
        "TotalAssets": total_assets, "TotalGDRework": total_gd,
    }

    result = submit_project(data)
    color = "success" if result["status"] == "success" else "danger"
    msg = dbc.Alert(result["message"], color=color, duration=4000)
    table = build_project_table()
    return msg, table


@callback(
    Output("proj-table-container", "children"),
    [Input("proj-refresh-btn", "n_clicks"), Input("tabs", "active_tab")],
)
def refresh_project_table(n_clicks, active_tab):
    return build_project_table()


def build_project_table():
    df = get_all_projects(force_refresh=True)
    if df.empty:
        return dbc.Alert("No projects yet. Click 'New Project' to add one.", color="info")

    # Show key columns in the table
    display_cols = [c for c in [
        "ProjectName", "BU", "InternalStatus", "Complexity",
        "DesignerAssigned", "TacticType", "AssignedDate", "CreatedBy",
    ] if c in df.columns]

    return dash_table.DataTable(
        data=df[display_cols].to_dict("records") if display_cols else df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in (display_cols or df.columns)],
        page_size=15, sort_action="native", filter_action="native",
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": COLORS["primary"], "color": "white", "fontWeight": "bold", "fontSize": "12px"},
        style_cell={"fontSize": "12px", "padding": "8px", "textAlign": "left"},
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFC"}],
    )


# ═══════════════════════════════════════════════════════════════════════
#  TAB 3: RESOURCE UTILIZATION
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

        # Form (collapsible)
        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                html.H5("Add Resource Entry", className="mb-3 text-primary"),
                dbc.Row([
                    make_field("Date", make_date("res-date"), 3),
                    make_field("BU", make_dropdown("res-bu", "BU"), 3),
                    make_field("Designer Name", make_dropdown("res-designer", "DesignerAssigned"), 3),
                    make_field("Reporting Manager", make_input("res-manager", placeholder="Manager name"), 3),
                ]),
                html.H6("Hours Breakdown", className="mt-2 mb-2 text-muted"),
                dbc.Row([
                    make_field("Project Task N/A in Workfront", make_input("res-proj-task", "number", "0"), 3),
                    make_field("Stakeholder Touchpoints", make_input("res-stakeholder", "number", "0"), 3),
                    make_field("Internal Team Meetings", make_input("res-meetings", "number", "0"), 3),
                    make_field("GCH Trainings", make_input("res-gch", "number", "0"), 3),
                ]),
                dbc.Row([
                    make_field("Tools & Tech Testing", make_input("res-tools", "number", "0"), 3),
                    make_field("Innovation/Process Improvement", make_input("res-innovation", "number", "0"), 3),
                    make_field("Cross Functional Supports", make_input("res-cross", "number", "0"), 3),
                    make_field("Site/GCH Activities", make_input("res-site", "number", "0"), 3),
                ]),
                dbc.Row([
                    make_field("Townhalls/HR/IT Meetings", make_input("res-townhall", "number", "0"), 3),
                    make_field("One:One", make_input("res-oneone", "number", "0"), 3),
                    make_field("SuccessFactor/LinkedIn", make_input("res-sf", "number", "0"), 3),
                    make_field("Other Trainings", make_input("res-other-train", "number", "0"), 3),
                ]),
                dbc.Row([
                    make_field("Hiring/Onboarding", make_input("res-hiring", "number", "0"), 3),
                    make_field("Leaves/Holidays", make_input("res-leaves", "number", "0"), 3),
                    make_field("Open Time", make_input("res-open", "number", "0"), 3),
                    make_field("Total Hours", make_input("res-total-hours", "number", "0"), 3),
                ]),
                html.Hr(),
                dbc.Row([
                    dbc.Col(dbc.Button("Submit Entry", id="res-submit-btn", color="primary", className="me-2"), width="auto"),
                    dbc.Col(dbc.Button("Cancel", id="res-cancel-btn", color="secondary", outline=True), width="auto"),
                    dbc.Col(html.Div(id="res-submit-msg"), className="align-self-center"),
                ]),
            ]), className="shadow-sm mb-3"),
            id="res-form-collapse", is_open=False,
        ),

        # Data Table
        html.Div(id="res-table-container"),
    ], fluid=True, className="py-3")


@callback(
    Output("res-form-collapse", "is_open"),
    [Input("res-new-btn", "n_clicks"), Input("res-cancel-btn", "n_clicks")],
    State("res-form-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_resource_form(new_click, cancel_click, is_open):
    if ctx.triggered_id == "res-new-btn":
        return True
    return False


@callback(
    [Output("res-submit-msg", "children"), Output("res-table-container", "children", allow_duplicate=True)],
    Input("res-submit-btn", "n_clicks"),
    [
        State("res-date", "date"), State("res-bu", "value"),
        State("res-designer", "value"), State("res-manager", "value"),
        State("res-proj-task", "value"), State("res-stakeholder", "value"),
        State("res-meetings", "value"), State("res-gch", "value"),
        State("res-tools", "value"), State("res-innovation", "value"),
        State("res-cross", "value"), State("res-site", "value"),
        State("res-townhall", "value"), State("res-oneone", "value"),
        State("res-sf", "value"), State("res-other-train", "value"),
        State("res-hiring", "value"), State("res-leaves", "value"),
        State("res-open", "value"), State("res-total-hours", "value"),
    ],
    prevent_initial_call=True,
)
def submit_resource_form(n_clicks,
    res_date, bu, designer, manager,
    proj_task, stakeholder, meetings, gch,
    tools, innovation, cross, site,
    townhall, oneone, sf, other_train,
    hiring, leaves, open_time, total_hours):

    data = {
        "Date": res_date, "BU": bu, "DesignerName": designer,
        "ReportingManager": manager, "ProjectTaskNA": proj_task,
        "StakeholderTouchpoints": stakeholder, "InternalTeamMeetings": meetings,
        "GCHTrainings": gch, "ToolsTechTesting": tools,
        "InnovationProcessImprovement": innovation, "CrossFunctionalSupports": cross,
        "SiteGCHActivities": site, "TownhallsHRIT": townhall,
        "OneOne": oneone, "SuccessFactorLinkedIn": sf,
        "OtherTrainings": other_train, "HiringOnboarding": hiring,
        "LeavesHolidays": leaves, "OpenTime": open_time, "TotalHours": total_hours,
    }

    result = submit_resource(data)
    color = "success" if result["status"] == "success" else "danger"
    msg = dbc.Alert(result["message"], color=color, duration=4000)
    table = build_resource_table()
    return msg, table


@callback(
    Output("res-table-container", "children"),
    [Input("res-refresh-btn", "n_clicks"), Input("tabs", "active_tab")],
)
def refresh_resource_table(n_clicks, active_tab):
    return build_resource_table()


def build_resource_table():
    df = get_all_resources(force_refresh=True)
    if df.empty:
        return dbc.Alert("No entries yet. Click 'New Entry' to add one.", color="info")

    display_cols = [c for c in [
        "Date", "BU", "DesignerName", "ReportingManager",
        "TotalHours", "LeavesHolidays", "InternalTeamMeetings", "CreatedBy",
    ] if c in df.columns]

    return dash_table.DataTable(
        data=df[display_cols].to_dict("records") if display_cols else df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in (display_cols or df.columns)],
        page_size=15, sort_action="native", filter_action="native",
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": COLORS["primary"], "color": "white", "fontWeight": "bold", "fontSize": "12px"},
        style_cell={"fontSize": "12px", "padding": "8px", "textAlign": "left"},
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFC"}],
    )


# ═══════════════════════════════════════════════════════════════════════
#  TAB 4: SETTINGS (Manage Dropdowns)
# ═══════════════════════════════════════════════════════════════════════

def tab_settings():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Settings — Manage Dropdown Values", className="text-primary fw-bold"), md=8),
            dbc.Col(dbc.Button("Refresh", id="settings-refresh", color="secondary", size="sm",
                               outline=True, className="float-end"), md=4),
        ], className="mb-3 align-items-center"),

        dbc.Row([
            # Left: Field selector
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H6("Select Dropdown Field", className="text-muted mb-2"),
                    dcc.Dropdown(
                        id="settings-field-select",
                        options=[
                            {"label": "BU", "value": "BU"},
                            {"label": "Project Type", "value": "ProjectType"},
                            {"label": "Classification Media", "value": "ClassificationMedia"},
                            {"label": "Tactic Type", "value": "TacticType"},
                            {"label": "Internal Status", "value": "InternalStatus"},
                            {"label": "Assigner Name", "value": "AssignerName"},
                            {"label": "Designer Assigned", "value": "DesignerAssigned"},
                            {"label": "QC Reviewer", "value": "QCReviewer"},
                            {"label": "Mail Sent", "value": "MailSent"},
                            {"label": "Tactic Stage", "value": "TacticStage"},
                            {"label": "Stakeholder", "value": "Stakeholder"},
                            {"label": "Complexity", "value": "Complexity"},
                            {"label": "Content Status", "value": "ContentStatus"},
                            {"label": "Revision 1", "value": "Revision1"},
                            {"label": "Revision 2", "value": "Revision2"},
                            {"label": "Revision 3+", "value": "Revision3OrMore"},
                        ],
                        placeholder="Select a field...",
                    ),
                    html.Hr(),
                    html.H6("Or Add New Dropdown Field", className="text-muted mb-2"),
                    dbc.InputGroup([
                        dbc.Input(id="settings-new-field", placeholder="New field name"),
                        dbc.Button("Add", id="settings-add-field-btn", color="primary", size="sm"),
                    ]),
                    html.Div(id="settings-add-field-msg", className="mt-2"),
                ]), className="shadow-sm"),
            ], md=4),

            # Right: Edit values
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H6(id="settings-edit-title", children="Select a field to edit", className="text-muted mb-2"),
                    dbc.Textarea(
                        id="settings-values-textarea",
                        placeholder="Enter one value per line...\n\nExample:\nOncology\nImmunology\nNeuroscience",
                        style={"height": "300px"},
                    ),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col(dbc.Button("Save Values", id="settings-save-btn", color="success", className="me-2"), width="auto"),
                        dbc.Col(html.Div(id="settings-save-msg"), className="align-self-center"),
                    ]),
                ]), className="shadow-sm"),
            ], md=8),
        ]),
    ], fluid=True, className="py-3")


@callback(
    [Output("settings-values-textarea", "value"),
     Output("settings-edit-title", "children")],
    Input("settings-field-select", "value"),
    prevent_initial_call=True,
)
def load_field_values(field_name):
    if not field_name:
        return "", "Select a field to edit"
    values = get_lookup_values(field_name)
    return "\n".join(values), f"Editing: {field_name}"


@callback(
    Output("settings-save-msg", "children"),
    Input("settings-save-btn", "n_clicks"),
    [State("settings-field-select", "value"), State("settings-values-textarea", "value")],
    prevent_initial_call=True,
)
def save_field_values(n_clicks, field_name, values_text):
    if not field_name:
        return dbc.Alert("Select a field first.", color="warning", duration=3000)

    values = [v.strip() for v in values_text.strip().split("\n") if v.strip()]
    try:
        save_lookup_values(field_name, values)
        return dbc.Alert(f"Saved {len(values)} values for {field_name}!", color="success", duration=3000)
    except Exception as e:
        return dbc.Alert(f"Error: {e}", color="danger", duration=5000)


@callback(
    [Output("settings-field-select", "options"),
     Output("settings-add-field-msg", "children")],
    Input("settings-add-field-btn", "n_clicks"),
    State("settings-new-field", "value"),
    prevent_initial_call=True,
)
def add_new_field(n_clicks, new_field):
    if not new_field or not new_field.strip():
        return dash.no_update, dbc.Alert("Enter a field name.", color="warning", duration=3000)

    field_name = new_field.strip().replace(" ", "")
    # Save with empty list to register the field
    save_lookup_values(field_name, [])
    clear_cache()

    # Rebuild options
    existing = [
        "BU", "ProjectType", "ClassificationMedia", "TacticType",
        "InternalStatus", "AssignerName", "DesignerAssigned", "QCReviewer",
        "MailSent", "TacticStage", "Stakeholder", "Complexity",
        "ContentStatus", "Revision1", "Revision2", "Revision3OrMore",
    ]
    all_fields = sorted(set(existing + get_all_lookup_fields() + [field_name]))
    options = [{"label": f, "value": f} for f in all_fields]

    return options, dbc.Alert(f"Added field: {field_name}", color="success", duration=3000)


# ═══════════════════════════════════════════════════════════════════════
#  MAIN LAYOUT
# ═══════════════════════════════════════════════════════════════════════

app.layout = html.Div([
    # Header
    dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand([
                html.I(className="fas fa-palette me-2"),
                "Medical Creatives UT"
            ], className="fw-bold text-white"),
            html.Span(f"User: {os.getenv('APP_USER', 'unknown')}", className="text-light small"),
        ], fluid=True),
        color=COLORS["primary"], dark=True, className="mb-0",
    ),

    # Tabs
    dbc.Tabs(id="tabs", active_tab="tab-analytics", className="px-3 pt-2", children=[
        dbc.Tab(tab_analytics(), label="Analytics", tab_id="tab-analytics",
                label_style={"fontWeight": "600"}),
        dbc.Tab(tab_project_summary(), label="Project Summary", tab_id="tab-projects",
                label_style={"fontWeight": "600"}),
        dbc.Tab(tab_resource_utilization(), label="Resource Utilization", tab_id="tab-resource",
                label_style={"fontWeight": "600"}),
        dbc.Tab(tab_settings(), label="Settings", tab_id="tab-settings",
                label_style={"fontWeight": "600"}),
    ]),
], style={"backgroundColor": COLORS["bg"], "minHeight": "100vh"})


# ═══════════════════════════════════════════════════════════════════════
#  LAZY LOAD: Populate all dropdowns — single OneLake read
# ═══════════════════════════════════════════════════════════════════════

# Mapping: dropdown component ID → lookup field name
DROPDOWN_LOOKUP_MAP = {
    # Project Summary dropdowns
    "proj-bu": "BU",
    "proj-type": "ProjectType",
    "proj-media": "ClassificationMedia",
    "proj-tactic": "TacticType",
    "proj-status": "InternalStatus",
    "proj-assigner": "AssignerName",
    "proj-designer": "DesignerAssigned",
    "proj-qc": "QCReviewer",
    "proj-mail": "MailSent",
    "proj-stage": "TacticStage",
    "proj-stakeholder": "Stakeholder",
    "proj-complexity": "Complexity",
    "proj-content-status": "ContentStatus",
    "proj-rev1": "Revision1",
    "proj-rev2": "Revision2",
    "proj-rev3": "Revision3OrMore",
    # Resource Utilization dropdowns
    "res-bu": "BU",
    "res-designer": "DesignerAssigned",
}


@callback(
    [Output(dd_id, "options") for dd_id in DROPDOWN_LOOKUP_MAP.keys()],
    [Input("proj-new-btn", "n_clicks"),
     Input("res-new-btn", "n_clicks"),
     Input("proj-refresh-btn", "n_clicks"),
     Input("res-refresh-btn", "n_clicks")],
    prevent_initial_call=True,
)
def load_all_dropdowns(n1, n2, n3, n4):
    """
    Load all dropdown options with a SINGLE OneLake read.
    Only triggers when user clicks New Project, New Entry, or Refresh.
    """
    try:
        from db_connection import read_table
        df = read_table("Lookups")
    except Exception:
        df = pd.DataFrame()

    results = []
    for dd_id, lookup_name in DROPDOWN_LOOKUP_MAP.items():
        if df.empty or "FieldName" not in df.columns:
            results.append([])
        else:
            filtered = df[df["FieldName"] == lookup_name].sort_values("Value")
            options = [{"label": v, "value": v} for v in filtered["Value"].tolist()]
            results.append(options)
    return results


# ═══════════════════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

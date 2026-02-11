from dash import Dash, html, dcc, dash_table, Input, Output, State
import pandas as pd
import uuid
from datetime import date

# -----------------------------
# Dummy project data (in-memory)
# -----------------------------
projects_df = pd.DataFrame([
    {
        "project_id": "PRJ-001",
        "project_name": "Oncology Campaign",
        "bu": "Oncology",
        "project_type": "Campaign",
        "classification_media": "Digital",
        "assigned_date": "2025-01-10",
        "designer": "Alice",
        "qc_reviewer": "Bob",
        "content_status": "In Progress",
        "gd_rework": 10,
        "poc_rework": 5,
        "comments": "Initial draft completed"
    },
    {
        "project_id": "PRJ-002",
        "project_name": "Cardio Visual Aid",
        "bu": "Cardiology",
        "project_type": "Visual Aid",
        "classification_media": "Print",
        "assigned_date": "2025-01-12",
        "designer": "Charlie",
        "qc_reviewer": "Diana",
        "content_status": "Completed",
        "gd_rework": 2,
        "poc_rework": 1,
        "comments": "Approved by stakeholder"
    }
])

# -----------------------------
# Dash App
# -----------------------------
app = Dash(__name__)
server = app.server

# -----------------------------
# Layout helpers
# -----------------------------
def header_section():
    return html.Div(
        children=[
            html.H2("Project Summary & Rework Management"),
            html.P("Create, update, and manage project details"),
            html.Hr()
        ]
    )

def filter_section():
    return html.Div(
        className="filters",
        children=[
            dcc.Dropdown(
                id="filter-bu",
                options=[{"label": bu, "value": bu} for bu in projects_df["bu"].unique()],
                placeholder="Filter by BU",
                clearable=True
            ),
            dcc.Dropdown(
                id="filter-status",
                options=[
                    {"label": s, "value": s}
                    for s in projects_df["content_status"].unique()
                ],
                placeholder="Filter by Status",
                clearable=True
            ),
            dcc.Input(
                id="search-project",
                type="text",
                placeholder="Search Project Name",
                style={"width": "250px"}
            ),
        ]
    )

def project_table():
    return dash_table.DataTable(
        id="project-table",
        columns=[
            {"name": "Project ID", "id": "project_id"},
            {"name": "Project Name", "id": "project_name"},
            {"name": "BU", "id": "bu"},
            {"name": "Status", "id": "content_status"},
            {"name": "Assigned Date", "id": "assigned_date"},
        ],
        row_selectable="single",
        page_size=10,
        style_table={"overflowY": "auto", "height": "450px"},
        style_cell={"textAlign": "left", "padding": "6px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f0f2f5"},
    )

def project_form():
    return html.Div(
        className="form-panel",
        children=[
            html.H4("Project Details"),

            dcc.Input(id="project-id", placeholder="Project ID", disabled=True),
            dcc.Input(id="project-name", placeholder="Project Name"),
            dcc.Dropdown(
                id="project-bu",
                options=[{"label": b, "value": b} for b in ["Oncology", "Cardiology", "Immunology"]],
                placeholder="Business Unit",
            ),
            dcc.Dropdown(
                id="project-type",
                options=[
                    {"label": p, "value": p}
                    for p in ["Campaign", "Visual Aid", "Emailer", "Banner"]
                ],
                placeholder="Project Type",
            ),
            dcc.Dropdown(
                id="classification-media",
                options=[
                    {"label": m, "value": m}
                    for m in ["Digital", "Print", "Video"]
                ],
                placeholder="Classification Media",
            ),

            html.Hr(),
            html.H5("Assignments"),

            dcc.DatePickerSingle(
                id="assigned-date",
                date=date.today(),
            ),
            dcc.Input(id="designer", placeholder="Designer Assigned"),
            dcc.Input(id="qc-reviewer", placeholder="QC Reviewer"),

            html.Hr(),
            html.H5("Rework Metrics"),

            dcc.Input(id="gd-rework", type="number", placeholder="GD Rework %"),
            dcc.Input(id="poc-rework", type="number", placeholder="POC Rework %"),

            html.Hr(),
            html.H5("Status & Comments"),

            dcc.Dropdown(
                id="content-status",
                options=[
                    {"label": s, "value": s}
                    for s in ["Not Started", "In Progress", "Completed"]
                ],
                placeholder="Content Status",
            ),
            dcc.Textarea(
                id="comments",
                placeholder="Comments",
                style={"width": "100%", "height": "80px"},
            ),

            html.Br(),
            html.Button("Save Project", id="save-project", className="primary-btn"),
            html.Span(id="save-message", style={"marginLeft": "10px"})
        ]
    )

# -----------------------------
# App Layout
# -----------------------------
app.layout = html.Div(
    className="app-container",
    children=[
        dcc.Store(id="projects-store", data=projects_df.to_dict("records")),
        header_section(),
        filter_section(),
        html.Div(
            className="content-row",
            children=[
                html.Div(className="left", children=[project_table()]),
                html.Div(className="right", children=[project_form()]),
            ],
        ),
    ],
)

# -----------------------------
# Callbacks
# -----------------------------
@app.callback(
    Output("project-table", "data"),
    Input("projects-store", "data"),
    Input("filter-bu", "value"),
    Input("filter-status", "value"),
    Input("search-project", "value"),
)
def update_table(data, bu, status, search):
    df = pd.DataFrame(data)
    if bu:
        df = df[df["bu"] == bu]
    if status:
        df = df[df["content_status"] == status]
    if search:
        df = df[df["project_name"].str.contains(search, case=False)]
    return df.to_dict("records")

@app.callback(
    [
        Output("project-id", "value"),
        Output("project-name", "value"),
        Output("project-bu", "value"),
        Output("project-type", "value"),
        Output("classification-media", "value"),
        Output("assigned-date", "date"),
        Output("designer", "value"),
        Output("qc-reviewer", "value"),
        Output("gd-rework", "value"),
        Output("poc-rework", "value"),
        Output("content-status", "value"),
        Output("comments", "value"),
    ],
    Input("project-table", "selected_rows"),
    State("project-table", "data"),
)
def load_project(selected_rows, table_data):
    if not selected_rows:
        return ["", "", None, None, None, date.today(), "", "", None, None, None, ""]
    row = table_data[selected_rows[0]]
    return (
        row["project_id"],
        row["project_name"],
        row["bu"],
        row["project_type"],
        row["classification_media"],
        row["assigned_date"],
        row["designer"],
        row["qc_reviewer"],
        row["gd_rework"],
        row["poc_rework"],
        row["content_status"],
        row["comments"],
    )

@app.callback(
    Output("projects-store", "data"),
    Output("save-message", "children"),
    Input("save-project", "n_clicks"),
    State("projects-store", "data"),
    State("project-id", "value"),
    State("project-name", "value"),
    State("project-bu", "value"),
    State("project-type", "value"),
    State("classification-media", "value"),
    State("assigned-date", "date"),
    State("designer", "value"),
    State("qc-reviewer", "value"),
    State("gd-rework", "value"),
    State("poc-rework", "value"),
    State("content-status", "value"),
    State("comments", "value"),
    prevent_initial_call=True,
)
def save_project(_, data, pid, name, bu, ptype, media, adate, designer, qc, gd, poc, status, comments):
    df = pd.DataFrame(data)

    if not pid:
        pid = f"PRJ-{uuid.uuid4().hex[:5].upper()}"
        df = pd.concat([
            df,
            pd.DataFrame([{
                "project_id": pid,
                "project_name": name,
                "bu": bu,
                "project_type": ptype,
                "classification_media": media,
                "assigned_date": adate,
                "designer": designer,
                "qc_reviewer": qc,
                "content_status": status,
                "gd_rework": gd,
                "poc_rework": poc,
                "comments": comments,
            }])
        ])
    else:
        df.loc[df["project_id"] == pid, :] = [
            pid, name, bu, ptype, media, adate, designer, qc, status, gd, poc, comments
        ]

    return df.to_dict("records"), "Saved successfully"

# -----------------------------
# Run locally
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)

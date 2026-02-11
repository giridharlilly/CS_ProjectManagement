from dash import Dash, html, dcc, dash_table, Input, Output, State, callback_context
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
import uuid

# -----------------------------
# Sample Data
# -----------------------------
projects_df = pd.DataFrame([
    {
        "project_id": "PRJ-001",
        "project_name": "Oncology Campaign Q1",
        "bu": "Oncology",
        "project_type": "Campaign",
        "classification_media": "Digital",
        "assigned_date": "2025-01-10",
        "designer": "Alice Johnson",
        "qc_reviewer": "Bob Smith",
        "content_status": "In Progress",
        "gd_rework": 10,
        "poc_rework": 5,
        "comments": "Initial draft completed, awaiting client feedback"
    },
    {
        "project_id": "PRJ-002",
        "project_name": "Cardio Visual Aid 2025",
        "bu": "Cardiology",
        "project_type": "Visual Aid",
        "classification_media": "Print",
        "assigned_date": "2025-01-12",
        "designer": "Charlie Brown",
        "qc_reviewer": "Diana Prince",
        "content_status": "Completed",
        "gd_rework": 2,
        "poc_rework": 1,
        "comments": "Approved by stakeholder"
    },
    {
        "project_id": "PRJ-003",
        "project_name": "Immunology Email Series",
        "bu": "Immunology",
        "project_type": "Emailer",
        "classification_media": "Digital",
        "assigned_date": "2025-01-15",
        "designer": "Alice Johnson",
        "qc_reviewer": "Bob Smith",
        "content_status": "In Progress",
        "gd_rework": 15,
        "poc_rework": 8,
        "comments": "Multiple revisions requested"
    },
    {
        "project_id": "PRJ-004",
        "project_name": "Oncology Banner Set",
        "bu": "Oncology",
        "project_type": "Banner",
        "classification_media": "Digital",
        "assigned_date": "2025-01-18",
        "designer": "Charlie Brown",
        "qc_reviewer": "Diana Prince",
        "content_status": "Not Started",
        "gd_rework": 0,
        "poc_rework": 0,
        "comments": "Scheduled to begin next week"
    }
])

# -----------------------------
# Initialize Dash App
# -----------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# -----------------------------
# Custom CSS
# -----------------------------
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Project Management Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background-color: #f5f7fa;
                color: #2d3748;
            }
            
            .app-container {
                max-width: 1600px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 12px;
                margin-bottom: 25px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .header h1 {
                font-size: 28px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            
            .header p {
                opacity: 0.9;
                font-size: 14px;
            }
            
            .kpi-section {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 20px;
                margin-bottom: 25px;
            }
            
            .kpi-card {
                background: white;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.08);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .kpi-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.12);
            }
            
            .kpi-label {
                font-size: 13px;
                color: #718096;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
                font-weight: 500;
            }
            
            .kpi-value {
                font-size: 32px;
                font-weight: 700;
                color: #2d3748;
                margin-bottom: 4px;
            }
            
            .kpi-trend {
                font-size: 12px;
                color: #48bb78;
            }
            
            .kpi-trend.negative {
                color: #f56565;
            }
            
            .content-section {
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.08);
                margin-bottom: 25px;
            }
            
            .section-title {
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 20px;
                color: #2d3748;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .section-title::before {
                content: "";
                width: 4px;
                height: 24px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 2px;
            }
            
            .filters-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            
            .main-grid {
                display: grid;
                grid-template-columns: 1fr 400px;
                gap: 25px;
            }
            
            @media (max-width: 1200px) {
                .main-grid {
                    grid-template-columns: 1fr;
                }
            }
            
            .form-panel {
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            }
            
            .form-group {
                margin-bottom: 18px;
            }
            
            .form-label {
                display: block;
                font-size: 13px;
                font-weight: 500;
                color: #4a5568;
                margin-bottom: 6px;
            }
            
            input[type="text"],
            input[type="number"],
            textarea {
                width: 100%;
                padding: 10px 12px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 14px;
                transition: border-color 0.2s;
            }
            
            input[type="text"]:focus,
            input[type="number"]:focus,
            textarea:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            textarea {
                resize: vertical;
                min-height: 80px;
            }
            
            .Select-control,
            .DateInput_input {
                border-radius: 6px !important;
                border-color: #e2e8f0 !important;
            }
            
            .primary-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: opacity 0.2s, transform 0.2s;
                width: 100%;
            }
            
            .primary-btn:hover {
                opacity: 0.9;
                transform: translateY(-1px);
            }
            
            .primary-btn:active {
                transform: translateY(0);
            }
            
            .secondary-btn {
                background: white;
                color: #667eea;
                border: 2px solid #667eea;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.2s;
                margin-left: 10px;
            }
            
            .secondary-btn:hover {
                background: #f7fafc;
            }
            
            .success-message {
                color: #48bb78;
                font-size: 13px;
                font-weight: 500;
                margin-top: 10px;
                display: inline-block;
            }
            
            .dash-table-container {
                border-radius: 8px;
                overflow: hidden;
            }
            
            .dash-spreadsheet {
                font-family: inherit !important;
            }
            
            .dash-spreadsheet-container .dash-spreadsheet-inner table {
                border-collapse: separate;
                border-spacing: 0;
            }
            
            .dash-spreadsheet-container .dash-spreadsheet-inner th {
                background-color: #f7fafc !important;
                color: #2d3748 !important;
                font-weight: 600 !important;
                border-bottom: 2px solid #e2e8f0 !important;
                padding: 14px 12px !important;
            }
            
            .dash-spreadsheet-container .dash-spreadsheet-inner td {
                border-bottom: 1px solid #f7fafc !important;
                padding: 12px !important;
            }
            
            .dash-spreadsheet-container .dash-spreadsheet-inner tr:hover td {
                background-color: #f7fafc !important;
            }
            
            .dash-spreadsheet-container .cell--selected {
                background-color: #e6f2ff !important;
            }
            
            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            
            .status-completed {
                background-color: #c6f6d5;
                color: #22543d;
            }
            
            .status-in-progress {
                background-color: #bee3f8;
                color: #2c5282;
            }
            
            .status-not-started {
                background-color: #fed7d7;
                color: #742a2a;
            }
            
            .divider {
                height: 1px;
                background-color: #e2e8f0;
                margin: 20px 0;
            }
            
            .button-group {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# -----------------------------
# Helper Functions
# -----------------------------
def calculate_kpis(df):
    """Calculate key performance indicators"""
    total_projects = len(df)
    completed = len(df[df['content_status'] == 'Completed'])
    in_progress = len(df[df['content_status'] == 'In Progress'])
    avg_rework = df['gd_rework'].mean() if len(df) > 0 else 0
    
    return {
        'total': total_projects,
        'completed': completed,
        'in_progress': in_progress,
        'avg_rework': round(avg_rework, 1)
    }

def create_status_chart(df):
    """Create status distribution pie chart"""
    status_counts = df['content_status'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=status_counts.index,
        values=status_counts.values,
        hole=0.4,
        marker=dict(colors=['#48bb78', '#4299e1', '#f56565']),
        textinfo='label+percent',
        textfont=dict(size=12)
    )])
    
    fig.update_layout(
        showlegend=True,
        height=300,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='inherit')
    )
    
    return fig

def create_rework_chart(df):
    """Create rework comparison bar chart"""
    rework_data = df.groupby('bu')[['gd_rework', 'poc_rework']].mean().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='GD Rework',
        x=rework_data['bu'],
        y=rework_data['gd_rework'],
        marker_color='#667eea'
    ))
    fig.add_trace(go.Bar(
        name='POC Rework',
        x=rework_data['bu'],
        y=rework_data['poc_rework'],
        marker_color='#764ba2'
    ))
    
    fig.update_layout(
        barmode='group',
        height=300,
        margin=dict(l=20, r=20, t=30, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='inherit'),
        xaxis=dict(title='Business Unit'),
        yaxis=dict(title='Rework %')
    )
    
    return fig

# -----------------------------
# Layout Components
# -----------------------------
def header():
    return html.Div(
        className="header",
        children=[
            html.H1("Project Management Dashboard"),
            html.P("Track and manage creative projects with real-time insights")
        ]
    )

def kpi_cards(kpis):
    return html.Div(
        className="kpi-section",
        children=[
            html.Div(
                className="kpi-card",
                children=[
                    html.Div("Total Projects", className="kpi-label"),
                    html.Div(str(kpis['total']), className="kpi-value"),
                ]
            ),
            html.Div(
                className="kpi-card",
                children=[
                    html.Div("Completed", className="kpi-label"),
                    html.Div(str(kpis['completed']), className="kpi-value"),
                    html.Div(f"{int(kpis['completed']/kpis['total']*100)}% completion rate", className="kpi-trend")
                ]
            ),
            html.Div(
                className="kpi-card",
                children=[
                    html.Div("In Progress", className="kpi-label"),
                    html.Div(str(kpis['in_progress']), className="kpi-value"),
                ]
            ),
            html.Div(
                className="kpi-card",
                children=[
                    html.Div("Avg. Rework", className="kpi-label"),
                    html.Div(f"{kpis['avg_rework']}%", className="kpi-value"),
                    html.Div(
                        "Below target" if kpis['avg_rework'] < 10 else "Above target",
                        className=f"kpi-trend {'positive' if kpis['avg_rework'] < 10 else 'negative'}"
                    )
                ]
            )
        ]
    )

def filters_section():
    return html.Div(
        className="content-section",
        children=[
            html.Div("Filters & Search", className="section-title"),
            html.Div(
                className="filters-grid",
                children=[
                    dcc.Dropdown(
                        id="filter-bu",
                        options=[{"label": bu, "value": bu} for bu in projects_df["bu"].unique()],
                        placeholder="Business Unit",
                        clearable=True
                    ),
                    dcc.Dropdown(
                        id="filter-status",
                        options=[
                            {"label": s, "value": s}
                            for s in projects_df["content_status"].unique()
                        ],
                        placeholder="Status",
                        clearable=True
                    ),
                    dcc.Dropdown(
                        id="filter-type",
                        options=[
                            {"label": t, "value": t}
                            for t in projects_df["project_type"].unique()
                        ],
                        placeholder="Project Type",
                        clearable=True
                    ),
                    dcc.Input(
                        id="search-project",
                        type="text",
                        placeholder="Search by project name..."
                    ),
                ]
            )
        ]
    )

def projects_table():
    return html.Div(
        className="content-section",
        children=[
            html.Div("Projects Overview", className="section-title"),
            dash_table.DataTable(
                id="project-table",
                columns=[
                    {"name": "Project ID", "id": "project_id"},
                    {"name": "Project Name", "id": "project_name"},
                    {"name": "Business Unit", "id": "bu"},
                    {"name": "Type", "id": "project_type"},
                    {"name": "Status", "id": "content_status"},
                    {"name": "Assigned Date", "id": "assigned_date"},
                    {"name": "Designer", "id": "designer"},
                    {"name": "GD Rework %", "id": "gd_rework"},
                    {"name": "POC Rework %", "id": "poc_rework"},
                ],
                row_selectable="single",
                page_size=10,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "left",
                    "padding": "12px",
                    "fontSize": "14px",
                    "fontFamily": "inherit"
                },
                style_header={
                    "fontWeight": "600",
                    "backgroundColor": "#f7fafc",
                    "borderBottom": "2px solid #e2e8f0"
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#fafafa'
                    }
                ]
            )
        ]
    )

def charts_section():
    df = projects_df
    return html.Div(
        className="content-section",
        children=[
            html.Div("Analytics", className="section-title"),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"},
                children=[
                    html.Div([
                        html.H4("Status Distribution", style={"fontSize": "14px", "marginBottom": "10px", "color": "#4a5568"}),
                        dcc.Graph(id="status-chart", figure=create_status_chart(df), config={'displayModeBar': False})
                    ]),
                    html.Div([
                        html.H4("Rework by BU", style={"fontSize": "14px", "marginBottom": "10px", "color": "#4a5568"}),
                        dcc.Graph(id="rework-chart", figure=create_rework_chart(df), config={'displayModeBar': False})
                    ])
                ]
            )
        ]
    )

def project_form():
    return html.Div(
        className="form-panel",
        children=[
            html.Div("Project Details", className="section-title"),
            
            html.Div(className="form-group", children=[
                html.Label("Project ID", className="form-label"),
                dcc.Input(id="project-id", disabled=True, style={"backgroundColor": "#f7fafc"})
            ]),
            
            html.Div(className="form-group", children=[
                html.Label("Project Name *", className="form-label"),
                dcc.Input(id="project-name", placeholder="Enter project name")
            ]),
            
            html.Div(className="form-group", children=[
                html.Label("Business Unit *", className="form-label"),
                dcc.Dropdown(
                    id="project-bu",
                    options=[{"label": b, "value": b} for b in ["Oncology", "Cardiology", "Immunology"]],
                    placeholder="Select business unit"
                )
            ]),
            
            html.Div(className="form-group", children=[
                html.Label("Project Type *", className="form-label"),
                dcc.Dropdown(
                    id="project-type",
                    options=[
                        {"label": p, "value": p}
                        for p in ["Campaign", "Visual Aid", "Emailer", "Banner"]
                    ],
                    placeholder="Select project type"
                )
            ]),
            
            html.Div(className="form-group", children=[
                html.Label("Classification Media", className="form-label"),
                dcc.Dropdown(
                    id="classification-media",
                    options=[
                        {"label": m, "value": m}
                        for m in ["Digital", "Print", "Video"]
                    ],
                    placeholder="Select media type"
                )
            ]),
            
            html.Div(className="divider"),
            
            html.Div(className="form-group", children=[
                html.Label("Assigned Date", className="form-label"),
                dcc.DatePickerSingle(
                    id="assigned-date",
                    date=date.today(),
                    display_format="YYYY-MM-DD"
                )
            ]),
            
            html.Div(className="form-group", children=[
                html.Label("Designer Assigned", className="form-label"),
                dcc.Input(id="designer", placeholder="Enter designer name")
            ]),
            
            html.Div(className="form-group", children=[
                html.Label("QC Reviewer", className="form-label"),
                dcc.Input(id="qc-reviewer", placeholder="Enter QC reviewer name")
            ]),
            
            html.Div(className="divider"),
            
            html.Div(className="form-group", children=[
                html.Label("GD Rework %", className="form-label"),
                dcc.Input(id="gd-rework", type="number", placeholder="0", min=0, max=100)
            ]),
            
            html.Div(className="form-group", children=[
                html.Label("POC Rework %", className="form-label"),
                dcc.Input(id="poc-rework", type="number", placeholder="0", min=0, max=100)
            ]),
            
            html.Div(className="divider"),
            
            html.Div(className="form-group", children=[
                html.Label("Content Status", className="form-label"),
                dcc.Dropdown(
                    id="content-status",
                    options=[
                        {"label": s, "value": s}
                        for s in ["Not Started", "In Progress", "Completed"]
                    ],
                    placeholder="Select status"
                )
            ]),
            
            html.Div(className="form-group", children=[
                html.Label("Comments", className="form-label"),
                dcc.Textarea(id="comments", placeholder="Enter any additional comments...")
            ]),
            
            html.Div(className="button-group", children=[
                html.Button("Save Project", id="save-project", className="primary-btn"),
            ]),
            html.Div(id="save-message", className="success-message")
        ]
    )

# -----------------------------
# Main Layout
# -----------------------------
app.layout = html.Div(
    className="app-container",
    children=[
        dcc.Store(id="projects-store", data=projects_df.to_dict("records")),
        header(),
        html.Div(id="kpi-container"),
        charts_section(),
        filters_section(),
        html.Div(
            className="main-grid",
            children=[
                projects_table(),
                project_form()
            ]
        )
    ]
)

# -----------------------------
# Callbacks
# -----------------------------
@app.callback(
    Output("kpi-container", "children"),
    Input("projects-store", "data")
)
def update_kpis(data):
    df = pd.DataFrame(data)
    kpis = calculate_kpis(df)
    return kpi_cards(kpis)

@app.callback(
    [Output("status-chart", "figure"),
     Output("rework-chart", "figure")],
    Input("projects-store", "data")
)
def update_charts(data):
    df = pd.DataFrame(data)
    return create_status_chart(df), create_rework_chart(df)

@app.callback(
    Output("project-table", "data"),
    [Input("projects-store", "data"),
     Input("filter-bu", "value"),
     Input("filter-status", "value"),
     Input("filter-type", "value"),
     Input("search-project", "value")]
)
def update_table(data, bu, status, proj_type, search):
    df = pd.DataFrame(data)
    
    if bu:
        df = df[df["bu"] == bu]
    if status:
        df = df[df["content_status"] == status]
    if proj_type:
        df = df[df["project_type"] == proj_type]
    if search:
        df = df[df["project_name"].str.contains(search, case=False, na=False)]
    
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
    prevent_initial_call=True
)
def load_project(selected_rows, table_data):
    if not selected_rows or len(selected_rows) == 0:
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
    [Output("projects-store", "data"),
     Output("save-message", "children")],
    Input("save-project", "n_clicks"),
    [State("projects-store", "data"),
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
     State("comments", "value")],
    prevent_initial_call=True
)
def save_project(n_clicks, data, pid, name, bu, ptype, media, adate, designer, qc, gd, poc, status, comments):
    if not name or not bu or not ptype:
        return data, "⚠️ Please fill in all required fields"
    
    df = pd.DataFrame(data)
    
    if not pid:
        # New project
        pid = f"PRJ-{uuid.uuid4().hex[:5].upper()}"
        new_project = pd.DataFrame([{
            "project_id": pid,
            "project_name": name,
            "bu": bu,
            "project_type": ptype,
            "classification_media": media,
            "assigned_date": adate,
            "designer": designer,
            "qc_reviewer": qc,
            "content_status": status,
            "gd_rework": gd or 0,
            "poc_rework": poc or 0,
            "comments": comments or "",
        }])
        df = pd.concat([df, new_project], ignore_index=True)
        message = f"✓ Project {pid} created successfully"
    else:
        # Update existing project
        df.loc[df["project_id"] == pid, ["project_name", "bu", "project_type", "classification_media",
                                          "assigned_date", "designer", "qc_reviewer", "content_status",
                                          "gd_rework", "poc_rework", "comments"]] = [
            name, bu, ptype, media, adate, designer, qc, status, gd or 0, poc or 0, comments or ""
        ]
        message = f"✓ Project {pid} updated successfully"
    
    return df.to_dict("records"), message

# -----------------------------
# Run Application
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8050)

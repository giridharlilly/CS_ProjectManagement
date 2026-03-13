"""
app.py - Medical Creatives UT
Auto-loads data on tab switch. Delta Lake storage.
"""

import os, json
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback, ctx, ALL
import dash_bootstrap_components as dbc
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

C = {"primary": "#1E2761", "accent": "#3B82F6", "success": "#10B981",
    "danger": "#EF4444", "bg": "#F8FAFC", "text": "#1E293B", "muted": "#64748B"}

TH = {"backgroundColor": C["primary"], "color": "white", "fontWeight": "bold", "fontSize": "12px"}

def make_field(label, comp, w=4):
    return dbc.Col([dbc.Label(label, className="fw-semibold small text-muted mb-1"), comp], md=w, className="mb-3")

def make_dd(fid, ph="Select..."):
    return dcc.Dropdown(id=fid, options=[], placeholder=ph, className="mb-0")

def make_inp(fid, t="text", ph=""):
    return dbc.Input(id=fid, type=t, placeholder=ph, size="sm")

def make_dt(fid):
    return dcc.DatePickerSingle(id=fid, date=None, display_format="YYYY-MM-DD", className="w-100")


# ═══════════════════════════════════════════════════════════════════════
#  TAB 1: PROJECT SUMMARY
# ═══════════════════════════════════════════════════════════════════════
def tab_project_summary():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H4("Project Summary",className="text-primary fw-bold"),md=6),
            dbc.Col([dbc.Button("New Project",id="proj-new-btn",color="success",size="sm",className="me-2"),
                dbc.Button("Refresh",id="proj-refresh-btn",color="secondary",size="sm",outline=True)],md=6,className="text-end"),
        ],className="mb-3 align-items-center"),
        dbc.Collapse(dbc.Card(dbc.CardBody([
            html.H5("Add New Project",className="mb-3 text-primary"),
            dbc.Row([make_field("Assigned Date",make_dt("proj-assigned-date"),3),make_field("Project Name",make_inp("proj-name",ph="Project name"),3),
                make_field("BU",make_dd("proj-bu"),3),make_field("Project ID",make_inp("proj-id",ph="Project ID"),3)]),
            dbc.Row([make_field("Veeva ID",make_inp("proj-veeva-id"),3),make_field("Project Type",make_dd("proj-type"),3),
                make_field("Classification Media",make_dd("proj-media"),3),make_field("Page/Slide #",make_inp("proj-page-slide","number","0"),3)]),
            dbc.Row([make_field("Tactic Type",make_dd("proj-tactic"),3),make_field("Internal Status",make_dd("proj-status"),3),
                make_field("First Proof Due",make_dt("proj-proof-due"),3),make_field("Assigner Name",make_dd("proj-assigner"),3)]),
            dbc.Row([make_field("Designer Assigned",make_dd("proj-designer"),3),make_field("QC Reviewer",make_dd("proj-qc"),3),
                make_field("Mail Sent",make_dd("proj-mail"),3),make_field("QC Emailer",make_inp("proj-qc-emailer"),3)]),
            dbc.Row([make_field("Tactic Stage",make_dd("proj-stage"),3),make_field("Stakeholder",make_dd("proj-stakeholder"),3),
                make_field("Complexity",make_dd("proj-complexity"),3),make_field("Content Status",make_dd("proj-content-status"),3)]),
            dbc.Row([make_field("Revision 1",make_dd("proj-rev1"),3),make_field("Revision 2",make_dd("proj-rev2"),3),
                make_field("Revision 3+",make_dd("proj-rev3"),3),make_field("Comments",make_inp("proj-comments"),3)]),
            dbc.Row([make_field("GD Rework %",make_inp("proj-gd-pct","number","0"),2),make_field("POC Rework %",make_inp("proj-poc-pct","number","0"),2),
                make_field("Asset #",make_inp("proj-asset","number","0"),2),make_field("Total #",make_inp("proj-total","number","0"),2),
                make_field("Simple #",make_inp("proj-simple","number","0"),2),make_field("Medium #",make_inp("proj-medium","number","0"),2)]),
            dbc.Row([make_field("Complex #",make_inp("proj-complex","number","0"),2),make_field("Derivatives #",make_inp("proj-deriv","number","0"),2),
                make_field("GD Rework",make_inp("proj-gd-rework","number","0"),2),make_field("POC Rework",make_inp("proj-poc-rework","text"),2),
                make_field("Total Assets",make_inp("proj-total-assets","number","0"),2),make_field("Total GD Rework",make_inp("proj-total-gd","number","0"),2)]),
            html.Hr(),
            dbc.Row([dbc.Col(dbc.Button("Submit",id="proj-submit-btn",color="primary",className="me-2"),width="auto"),
                dbc.Col(dbc.Button("Cancel",id="proj-cancel-btn",color="secondary",outline=True),width="auto"),
                dbc.Col(html.Div(id="proj-submit-msg"),className="align-self-center")]),
        ]),className="shadow-sm mb-3"),id="proj-form-collapse",is_open=False),
        html.Div(id="proj-table-container"),
        dbc.Modal([dbc.ModalHeader(dbc.ModalTitle(id="proj-modal-title")),dbc.ModalBody(id="proj-modal-body"),
            dbc.ModalFooter([dbc.Button("Save Changes",id="proj-modal-save",color="primary",className="me-2",style={"display":"none"}),
                dbc.Button("Close",id="proj-modal-close",color="secondary")])],id="proj-modal",size="xl",scrollable=True),
        dcc.Store(id="proj-selected-row-id"),dcc.Store(id="proj-modal-mode"),html.Div(id="proj-delete-msg"),
    ],fluid=True,className="py-3")

@callback(Output("proj-form-collapse","is_open"),[Input("proj-new-btn","n_clicks"),Input("proj-cancel-btn","n_clicks")],
    State("proj-form-collapse","is_open"),prevent_initial_call=True)
def toggle_pf(n1,n2,o): return True if ctx.triggered_id=="proj-new-btn" else False

@callback([Output("proj-submit-msg","children"),Output("proj-table-container","children",allow_duplicate=True)],
    Input("proj-submit-btn","n_clicks"),
    [State("proj-assigned-date","date"),State("proj-name","value"),State("proj-bu","value"),State("proj-id","value"),
     State("proj-veeva-id","value"),State("proj-type","value"),State("proj-media","value"),State("proj-page-slide","value"),
     State("proj-tactic","value"),State("proj-status","value"),State("proj-proof-due","date"),State("proj-assigner","value"),
     State("proj-designer","value"),State("proj-qc","value"),State("proj-mail","value"),State("proj-qc-emailer","value"),
     State("proj-stage","value"),State("proj-stakeholder","value"),State("proj-complexity","value"),State("proj-content-status","value"),
     State("proj-rev1","value"),State("proj-rev2","value"),State("proj-rev3","value"),State("proj-comments","value"),
     State("proj-gd-pct","value"),State("proj-poc-pct","value"),State("proj-asset","value"),State("proj-total","value"),
     State("proj-simple","value"),State("proj-medium","value"),State("proj-complex","value"),State("proj-deriv","value"),
     State("proj-gd-rework","value"),State("proj-poc-rework","value"),State("proj-total-assets","value"),State("proj-total-gd","value")],
    prevent_initial_call=True)
def submit_p(n,ad,name,bu,pid,vid,pt,media,ps,tactic,status,pf,assigner,designer,qc,mail,qce,stage,sh,comp,cs,r1,r2,r3,comments,gp,pp,asset,total,simple,med,cmplx,deriv,gr,pr,ta,tg):
    if not name: return dbc.Alert("Project Name required.",color="danger",duration=3000),dash.no_update
    data={"AssignedDate":ad,"ProjectName":name,"BU":bu,"ProjectID":pid,"VeevaID":vid,"ProjectType":pt,
        "ClassificationMedia":media,"PageSlide":ps,"TacticType":tactic,"InternalStatus":status,
        "FirstProofDue":pf,"AssignerName":assigner,"DesignerAssigned":designer,"QCReviewer":qc,
        "MailSent":mail,"QCEmailer":qce,"TacticStage":stage,"Stakeholder":sh,
        "Complexity":comp,"ContentStatus":cs,"Revision1":r1,"Revision2":r2,"Revision3OrMore":r3,
        "Comments":comments,"GDReworkPct":gp,"POCReworkPct":pp,"Asset":asset,"Total":total,
        "Simple":simple,"Medium":med,"Complex":cmplx,"Derivatives":deriv,
        "GDRework":gr,"POCRework":pr,"TotalAssets":ta,"TotalGDRework":tg}
    r=submit_project(data)
    return dbc.Alert(r["message"],color="success" if r["status"]=="success" else "danger",duration=4000),build_pt()

# Auto-load project table on tab switch + manual refresh
@callback(Output("proj-table-container","children"),
    [Input("proj-refresh-btn","n_clicks"),Input("tabs","active_tab")])
def refresh_pt(n,tab):
    if tab != "tab-projects" and not n: return dash.no_update
    return build_pt(force=True)

def build_pt(force=True):
    df=get_all_projects(force_refresh=force)
    if df.empty: return dbc.Alert("No projects yet.",color="info")
    rows=[]
    for _,row in df.iterrows():
        rid=row.get("RowID","")
        rows.append(html.Tr([html.Td(row.get("ProjectName",""),className="small"),html.Td(row.get("BU",""),className="small"),
            html.Td(row.get("InternalStatus",""),className="small"),html.Td(row.get("Complexity",""),className="small"),
            html.Td(row.get("DesignerAssigned",""),className="small"),html.Td(row.get("AssignedDate",""),className="small"),
            html.Td([dbc.Button("View",id={"type":"proj-view-btn","index":rid},color="info",size="sm",className="me-1"),
                dbc.Button("Edit",id={"type":"proj-edit-btn","index":rid},color="warning",size="sm",className="me-1"),
                dbc.Button("Delete",id={"type":"proj-del-btn","index":rid},color="danger",size="sm",outline=True)],className="text-nowrap")]))
    return dbc.Table([html.Thead(html.Tr([html.Th(c,style=TH) for c in ["Project Name","BU","Status","Complexity","Designer","Date","Actions"]])),
        html.Tbody(rows)],bordered=True,hover=True,responsive=True,size="sm",className="mt-2")

@callback([Output("proj-modal","is_open"),Output("proj-modal-title","children"),Output("proj-modal-body","children"),
    Output("proj-modal-save","style"),Output("proj-selected-row-id","data"),Output("proj-modal-mode","data")],
    [Input({"type":"proj-view-btn","index":ALL},"n_clicks"),Input({"type":"proj-edit-btn","index":ALL},"n_clicks"),
     Input("proj-modal-close","n_clicks")],prevent_initial_call=True)
def open_pm(vc,ec,cc):
    if not ctx.triggered_id or ctx.triggered_id=="proj-modal-close": return False,"","",{"display":"none"},None,None
    t=ctx.triggered_id;rid=t["index"];mode="edit" if t["type"]=="proj-edit-btn" else "view"
    df=get_all_projects();
    if df.empty or "RowID" not in df.columns: return False,"","",{"display":"none"},None,None
    r=df[df["RowID"]==rid]
    if r.empty: return False,"","",{"display":"none"},None,None
    r=r.iloc[0];title=f"{'Edit' if mode=='edit' else 'View'}: {r.get('ProjectName','')}"
    fields=[];skip=["RowID","CreatedBy","CreatedAt","UpdatedBy","UpdatedAt"]
    for col in df.columns:
        if col in skip: continue
        v=r.get(col,"");v="" if pd.isna(v) else v
        if mode=="edit": fields.append(dbc.Row([dbc.Col(dbc.Label(col,className="fw-semibold small"),md=4),
            dbc.Col(dbc.Input(id={"type":"proj-edit-field","index":col},value=str(v),size="sm"),md=8)],className="mb-2"))
        else: fields.append(dbc.Row([dbc.Col(html.Span(col,className="fw-semibold small text-muted"),md=4),
            dbc.Col(html.Span(str(v),className="small"),md=8)],className="mb-2 border-bottom pb-1"))
    fields.append(html.Hr());fields.append(html.Small(f"Created by {r.get('CreatedBy','')} at {r.get('CreatedAt','')}",className="text-muted"))
    return True,title,html.Div(fields),{"display":"inline-block"} if mode=="edit" else {"display":"none"},rid,mode

@callback([Output("proj-modal","is_open",allow_duplicate=True),Output("proj-submit-msg","children",allow_duplicate=True)],
    Input("proj-modal-save","n_clicks"),[State("proj-selected-row-id","data"),
    State({"type":"proj-edit-field","index":ALL},"value"),State({"type":"proj-edit-field","index":ALL},"id")],prevent_initial_call=True)
def save_pe(n,rid,vals,ids):
    if not rid or not vals: return dash.no_update,dash.no_update
    changes={i["index"]:v for v,i in zip(vals,ids) if v}
    r=update_project(rid,changes)
    return False,dbc.Alert(f"{r['message']} Click Refresh.",color="success" if r["status"]=="success" else "danger",duration=5000)

@callback(Output("proj-delete-msg","children"),Input({"type":"proj-del-btn","index":ALL},"n_clicks"),prevent_initial_call=True)
def del_p(nc):
    if not ctx.triggered_id or not any(nc): return dash.no_update
    delete_project(ctx.triggered_id["index"])
    return dbc.Alert("Deleted. Click Refresh.",color="warning",duration=4000)

# ═══════════════════════════════════════════════════════════════════════
#  TAB 3: RESOURCE UTILIZATION
# ═══════════════════════════════════════════════════════════════════════
def tab_resource():
    return dbc.Container([
        dbc.Row([dbc.Col(html.H4("Resource Utilization",className="text-primary fw-bold"),md=6),
            dbc.Col([dbc.Button("New Entry",id="res-new-btn",color="success",size="sm",className="me-2"),
                dbc.Button("Refresh",id="res-refresh-btn",color="secondary",size="sm",outline=True)],md=6,className="text-end")],className="mb-3 align-items-center"),
        dbc.Collapse(dbc.Card(dbc.CardBody([
            html.H5("Add Resource Entry",className="mb-3 text-primary"),
            dbc.Row([make_field("Date",make_dt("res-date"),3),make_field("BU",make_dd("res-bu"),3),
                make_field("Designer Name",make_dd("res-designer"),3),make_field("Reporting Manager",make_inp("res-manager"),3)]),
            html.H6("Hours Breakdown",className="mt-2 mb-2 text-muted"),
            dbc.Row([make_field("Project Task N/A",make_inp("res-proj-task","number","0"),3),make_field("Stakeholder Touchpoints",make_inp("res-stakeholder","number","0"),3),
                make_field("Internal Team Meetings",make_inp("res-meetings","number","0"),3),make_field("GCH Trainings",make_inp("res-gch","number","0"),3)]),
            dbc.Row([make_field("Tools & Tech",make_inp("res-tools","number","0"),3),make_field("Innovation/Process",make_inp("res-innovation","number","0"),3),
                make_field("Cross Functional",make_inp("res-cross","number","0"),3),make_field("Site/GCH",make_inp("res-site","number","0"),3)]),
            dbc.Row([make_field("Townhalls/HR/IT",make_inp("res-townhall","number","0"),3),make_field("One:One",make_inp("res-oneone","number","0"),3),
                make_field("SuccessFactor/LinkedIn",make_inp("res-sf","number","0"),3),make_field("Other Trainings",make_inp("res-other-train","number","0"),3)]),
            dbc.Row([make_field("Hiring/Onboarding",make_inp("res-hiring","number","0"),3),make_field("Leaves/Holidays",make_inp("res-leaves","number","0"),3),
                make_field("Open Time",make_inp("res-open","number","0"),3),make_field("Total Hours",make_inp("res-total-hours","number","0"),3)]),
            html.Hr(),
            dbc.Row([dbc.Col(dbc.Button("Submit",id="res-submit-btn",color="primary",className="me-2"),width="auto"),
                dbc.Col(dbc.Button("Cancel",id="res-cancel-btn",color="secondary",outline=True),width="auto"),
                dbc.Col(html.Div(id="res-submit-msg"),className="align-self-center")])
        ]),className="shadow-sm mb-3"),id="res-form-collapse",is_open=False),
        html.Div(id="res-table-container"),
        dbc.Modal([dbc.ModalHeader(dbc.ModalTitle(id="res-modal-title")),dbc.ModalBody(id="res-modal-body"),
            dbc.ModalFooter([dbc.Button("Save",id="res-modal-save",color="primary",className="me-2",style={"display":"none"}),
                dbc.Button("Close",id="res-modal-close",color="secondary")])],id="res-modal",size="xl",scrollable=True),
        dcc.Store(id="res-selected-row-id"),dcc.Store(id="res-modal-mode"),html.Div(id="res-delete-msg"),
    ],fluid=True,className="py-3")

@callback(Output("res-form-collapse","is_open"),[Input("res-new-btn","n_clicks"),Input("res-cancel-btn","n_clicks")],
    State("res-form-collapse","is_open"),prevent_initial_call=True)
def toggle_rf(n1,n2,o): return True if ctx.triggered_id=="res-new-btn" else False

@callback([Output("res-submit-msg","children"),Output("res-table-container","children",allow_duplicate=True)],
    Input("res-submit-btn","n_clicks"),
    [State("res-date","date"),State("res-bu","value"),State("res-designer","value"),State("res-manager","value"),
     State("res-proj-task","value"),State("res-stakeholder","value"),State("res-meetings","value"),State("res-gch","value"),
     State("res-tools","value"),State("res-innovation","value"),State("res-cross","value"),State("res-site","value"),
     State("res-townhall","value"),State("res-oneone","value"),State("res-sf","value"),State("res-other-train","value"),
     State("res-hiring","value"),State("res-leaves","value"),State("res-open","value"),State("res-total-hours","value")],
    prevent_initial_call=True)
def submit_r(n,dt,bu,des,mgr,pt,sh,mtg,gch,tools,innov,cross,site,town,oo,sf,ot,hire,leave,opn,tot):
    data={"Date":dt,"BU":bu,"DesignerName":des,"ReportingManager":mgr,"ProjectTaskNA":pt,
        "StakeholderTouchpoints":sh,"InternalTeamMeetings":mtg,"GCHTrainings":gch,"ToolsTechTesting":tools,
        "InnovationProcessImprovement":innov,"CrossFunctionalSupports":cross,"SiteGCHActivities":site,
        "TownhallsHRIT":town,"OneOne":oo,"SuccessFactorLinkedIn":sf,"OtherTrainings":ot,
        "HiringOnboarding":hire,"LeavesHolidays":leave,"OpenTime":opn,"TotalHours":tot}
    r=submit_resource(data)
    return dbc.Alert(r["message"],color="success" if r["status"]=="success" else "danger",duration=4000),build_rt()

# Auto-load resource table on tab switch
@callback(Output("res-table-container","children"),
    [Input("res-refresh-btn","n_clicks"),Input("tabs","active_tab")])
def refresh_rt(n,tab):
    if tab != "tab-resource" and not n: return dash.no_update
    return build_rt(force=True)

def build_rt(force=True):
    df=get_all_resources(force_refresh=force)
    if df.empty: return dbc.Alert("No entries yet.",color="info")
    rows=[]
    for _,row in df.iterrows():
        rid=row.get("RowID","")
        rows.append(html.Tr([html.Td(row.get("Date",""),className="small"),html.Td(row.get("BU",""),className="small"),
            html.Td(row.get("DesignerName",""),className="small"),html.Td(row.get("TotalHours",""),className="small"),
            html.Td([dbc.Button("View",id={"type":"res-view-btn","index":rid},color="info",size="sm",className="me-1"),
                dbc.Button("Edit",id={"type":"res-edit-btn","index":rid},color="warning",size="sm",className="me-1"),
                dbc.Button("Delete",id={"type":"res-del-btn","index":rid},color="danger",size="sm",outline=True)],className="text-nowrap")]))
    return dbc.Table([html.Thead(html.Tr([html.Th(c,style=TH) for c in ["Date","BU","Designer","Total Hours","Actions"]])),
        html.Tbody(rows)],bordered=True,hover=True,responsive=True,size="sm",className="mt-2")

@callback([Output("res-modal","is_open"),Output("res-modal-title","children"),Output("res-modal-body","children"),
    Output("res-modal-save","style"),Output("res-selected-row-id","data"),Output("res-modal-mode","data")],
    [Input({"type":"res-view-btn","index":ALL},"n_clicks"),Input({"type":"res-edit-btn","index":ALL},"n_clicks"),
     Input("res-modal-close","n_clicks")],prevent_initial_call=True)
def open_rm(vc,ec,cc):
    if not ctx.triggered_id or ctx.triggered_id=="res-modal-close": return False,"","",{"display":"none"},None,None
    t=ctx.triggered_id;rid=t["index"];mode="edit" if t["type"]=="res-edit-btn" else "view"
    df=get_all_resources()
    if df.empty or "RowID" not in df.columns: return False,"","",{"display":"none"},None,None
    r=df[df["RowID"]==rid]
    if r.empty: return False,"","",{"display":"none"},None,None
    r=r.iloc[0];title=f"{'Edit' if mode=='edit' else 'View'}: {r.get('DesignerName','')}-{r.get('Date','')}"
    fields=[];skip=["RowID","CreatedBy","CreatedAt","UpdatedBy","UpdatedAt"]
    for col in df.columns:
        if col in skip: continue
        v=r.get(col,"");v="" if pd.isna(v) else v
        if mode=="edit": fields.append(dbc.Row([dbc.Col(dbc.Label(col,className="fw-semibold small"),md=4),
            dbc.Col(dbc.Input(id={"type":"res-edit-field","index":col},value=str(v),size="sm"),md=8)],className="mb-2"))
        else: fields.append(dbc.Row([dbc.Col(html.Span(col,className="fw-semibold small text-muted"),md=4),
            dbc.Col(html.Span(str(v),className="small"),md=8)],className="mb-2 border-bottom pb-1"))
    fields.append(html.Hr());fields.append(html.Small(f"Created by {r.get('CreatedBy','')} at {r.get('CreatedAt','')}",className="text-muted"))
    return True,title,html.Div(fields),{"display":"inline-block"} if mode=="edit" else {"display":"none"},rid,mode

@callback([Output("res-modal","is_open",allow_duplicate=True),Output("res-submit-msg","children",allow_duplicate=True)],
    Input("res-modal-save","n_clicks"),[State("res-selected-row-id","data"),
    State({"type":"res-edit-field","index":ALL},"value"),State({"type":"res-edit-field","index":ALL},"id")],prevent_initial_call=True)
def save_re(n,rid,vals,ids):
    if not rid or not vals: return dash.no_update,dash.no_update
    changes={i["index"]:v for v,i in zip(vals,ids) if v}
    df=get_all_resources(force_refresh=True);mask=df["RowID"]==rid
    from datetime import datetime,timezone;now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for col,val in changes.items():
        if col in df.columns:
            try:
                if pd.api.types.is_integer_dtype(df[col].dtype): val=int(float(val)) if val and str(val).strip() else 0
                elif pd.api.types.is_float_dtype(df[col].dtype): val=float(val) if val and str(val).strip() else 0.0
            except: val=str(val)
        df.loc[mask,col]=val
    df.loc[mask,"UpdatedBy"]=os.getenv("APP_USER","unknown");df.loc[mask,"UpdatedAt"]=now
    from db_connection import write_table;write_table("ResourceUtilization",df);clear_cache("ResourceUtilization")
    return False,dbc.Alert("Updated! Click Refresh.",color="success",duration=5000)

@callback(Output("res-delete-msg","children"),Input({"type":"res-del-btn","index":ALL},"n_clicks"),prevent_initial_call=True)
def del_r(nc):
    if not ctx.triggered_id or not any(nc): return dash.no_update
    delete_resource(ctx.triggered_id["index"])
    return dbc.Alert("Deleted. Click Refresh.",color="warning",duration=4000)

# ═══════════════════════════════════════════════════════════════════════
#  TAB 4: SETTINGS
# ═══════════════════════════════════════════════════════════════════════
DD_FIELDS=[{"label":"BU","value":"BU"},{"label":"Project Type","value":"ProjectType"},
    {"label":"Classification Media","value":"ClassificationMedia"},{"label":"Tactic Type","value":"TacticType"},
    {"label":"Internal Status","value":"InternalStatus"},{"label":"Assigner Name","value":"AssignerName"},
    {"label":"Designer Assigned","value":"DesignerAssigned"},{"label":"QC Reviewer","value":"QCReviewer"},
    {"label":"Mail Sent","value":"MailSent"},{"label":"Tactic Stage","value":"TacticStage"},
    {"label":"Stakeholder","value":"Stakeholder"},{"label":"Complexity","value":"Complexity"},
    {"label":"Content Status","value":"ContentStatus"},{"label":"Revision 1","value":"Revision1"},
    {"label":"Revision 2","value":"Revision2"},{"label":"Revision 3+","value":"Revision3OrMore"}]

def tab_settings():
    return dbc.Container([html.H4("Settings — Manage Dropdowns",className="text-primary fw-bold mb-3"),
        dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.H6("Select Field",className="text-muted mb-2"),
            dcc.Dropdown(id="settings-field-select",options=DD_FIELDS,placeholder="Select..."),html.Hr(),
            html.H6("Or Add New",className="text-muted mb-2"),
            dbc.InputGroup([dbc.Input(id="settings-new-field",placeholder="Field name"),
                dbc.Button("Add",id="settings-add-field-btn",color="primary",size="sm")]),
            html.Div(id="settings-add-field-msg",className="mt-2")]),className="shadow-sm"),md=4),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6(id="settings-edit-title",children="Select a field",className="text-muted mb-2"),
                dbc.Textarea(id="settings-values-textarea",placeholder="One value per line...",style={"height":"300px"}),html.Hr(),
                dbc.Row([dbc.Col(dbc.Button("Save Values",id="settings-save-btn",color="success",className="me-2"),width="auto"),
                    dbc.Col(html.Div(id="settings-save-msg"),className="align-self-center")])]),className="shadow-sm"),md=8)])
    ],fluid=True,className="py-3")

@callback([Output("settings-values-textarea","value"),Output("settings-edit-title","children")],
    Input("settings-field-select","value"),prevent_initial_call=True)
def load_fv(f):
    if not f: return "","Select a field"
    return "\n".join(get_lookup_values(f)),f"Editing: {f}"

@callback(Output("settings-save-msg","children"),Input("settings-save-btn","n_clicks"),
    [State("settings-field-select","value"),State("settings-values-textarea","value")],prevent_initial_call=True)
def save_fv(n,f,txt):
    if not f: return dbc.Alert("Select a field.",color="warning",duration=3000)
    vals=[v.strip() for v in txt.strip().split("\n") if v.strip()]
    try: save_lookup_values(f,vals);return dbc.Alert(f"Saved {len(vals)} values!",color="success",duration=3000)
    except Exception as e: return dbc.Alert(f"Error: {e}",color="danger",duration=5000)

@callback([Output("settings-field-select","options"),Output("settings-add-field-msg","children")],
    Input("settings-add-field-btn","n_clicks"),State("settings-new-field","value"),prevent_initial_call=True)
def add_f(n,nf):
    if not nf: return dash.no_update,dbc.Alert("Enter name.",color="warning",duration=3000)
    fn=nf.strip().replace(" ","");save_lookup_values(fn,[]);clear_cache()
    opts=sorted(set([d["value"] for d in DD_FIELDS]+get_all_lookup_fields()+[fn]))
    return [{"label":f,"value":f} for f in opts],dbc.Alert(f"Added: {fn}",color="success",duration=3000)

# ═══════════════════════════════════════════════════════════════════════
#  LAZY LOAD DROPDOWNS
# ═══════════════════════════════════════════════════════════════════════
DD_MAP={"proj-bu":"BU","proj-type":"ProjectType","proj-media":"ClassificationMedia","proj-tactic":"TacticType",
    "proj-status":"InternalStatus","proj-assigner":"AssignerName","proj-designer":"DesignerAssigned",
    "proj-qc":"QCReviewer","proj-mail":"MailSent","proj-stage":"TacticStage","proj-stakeholder":"Stakeholder",
    "proj-complexity":"Complexity","proj-content-status":"ContentStatus","proj-rev1":"Revision1",
    "proj-rev2":"Revision2","proj-rev3":"Revision3OrMore","res-bu":"BU","res-designer":"DesignerAssigned"}

@callback([Output(dd,"options") for dd in DD_MAP.keys()],
    [Input("proj-new-btn","n_clicks"),Input("res-new-btn","n_clicks"),
     Input("proj-refresh-btn","n_clicks"),Input("res-refresh-btn","n_clicks"),
     Input("tabs","active_tab")])
def load_dd(n1,n2,n3,n4,tab):
    # Only load when on project or resource tabs
    if tab not in ("tab-projects","tab-resource") and not any([n1,n2,n3,n4]):
        return [dash.no_update] * len(DD_MAP)
    try:
        from db_connection import read_table;df=read_table("Lookups")
    except: df=pd.DataFrame()
    results=[]
    for dd,ln in DD_MAP.items():
        if df.empty or "FieldName" not in df.columns: results.append([])
        else: results.append([{"label":v,"value":v} for v in df[df["FieldName"]==ln].sort_values("Value")["Value"].tolist()])
    return results

# ═══════════════════════════════════════════════════════════════════════
#  LAYOUT
# ═══════════════════════════════════════════════════════════════════════
app.layout=html.Div([
    dbc.Navbar(dbc.Container([dbc.NavbarBrand([html.I(className="fas fa-palette me-2"),"Medical Creatives UT"],className="fw-bold text-white"),
        html.Span(f"User: {os.getenv('APP_USER','unknown')}",className="text-light small")],fluid=True),color=C["primary"],dark=True,className="mb-0"),
    dbc.Tabs(id="tabs",active_tab="tab-projects",className="px-3 pt-2",children=[
        dbc.Tab(tab_project_summary(),label="Project Summary",tab_id="tab-projects",label_style={"fontWeight":"600"}),
        dbc.Tab(tab_resource(),label="Resource Utilization",tab_id="tab-resource",label_style={"fontWeight":"600"}),
        dbc.Tab(tab_settings(),label="Settings",tab_id="tab-settings",label_style={"fontWeight":"600"}),
    ]),
],style={"backgroundColor":C["bg"],"minHeight":"100vh"})

if __name__=="__main__": app.run(debug=True,host="0.0.0.0",port=8050)

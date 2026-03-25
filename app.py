
import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from supabase import create_client, Client
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="MD-1 Staff Elite Definitiva", layout="wide", initial_sidebar_state="expanded")

# Persistencia en Supabase
APP_DIR = Path("app_data")
APP_DIR.mkdir(exist_ok=True)
DB_PATH = APP_DIR / "md1_staff_elite_definitiva_v2.db"

SUPABASE_MONITORING_TABLE = "ud_sanse_monitoring"
SUPABASE_GPS_TABLE = "ud_sanse_gps_data"

OBJECTIVE_METRICS = ["CMJ", "RSI_mod", "VMP"]
ALL_METRICS = ["CMJ", "RSI_mod", "VMP", "sRPE"]

LABELS = {"CMJ": "CMJ", "RSI_mod": "RSI mod", "VMP": "VMP sentadilla", "sRPE": "sRPE"}
RISK_ORDER = ["Estado óptimo","Buen estado","Fatiga leve","Fatiga leve-moderada","Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"]
SEVERITY_COLORS = {
    "Buen estado": "#16A34A",
    "Fatiga leve": "#EAB308",
    "Fatiga moderada": "#F97316",
    "Fatiga crítica": "#C62828",
    "Sin referencia": "#94A3B8",
}
RISK_COLORS = {
    "Estado óptimo": "#15803D",
    "Buen estado": "#2E8B57",
    "Fatiga leve": "#E3A008",
    "Fatiga leve-moderada": "#F59E0B",
    "Fatiga moderada": "#F97316",
    "Fatiga moderada-alta": "#EA580C",
    "Fatiga crítica": "#B91C1C",
}


POSITION_MAP = {
    "LEJA": "Portero", "GONZALO (P)": "Portero",
    "ÁLEX": "Lateral", "ALEX": "Lateral", "IVÁN": "Lateral", "IVAN": "Lateral", "OCAÑA": "Lateral", "GONZALO": "Lateral",
    "AARÓN": "Central", "AARON": "Central", "CÉSAR": "Central", "CESAR": "Central", "MARVIN": "Central", "ROBIN": "Central", "ORTU": "Central",
    "ENEKO": "Mediocentro", "GALINDO": "Mediocentro", "JAVI": "Mediocentro", "MARIO": "Mediocentro", "PABLO": "Mediocentro", "VARO": "Mediocentro",
    "CHRISTIAN": "Delantero", "FER HARTA": "Delantero", "FER RUÍZ": "Delantero", "FER RUIZ": "Delantero", "GARCI": "Delantero", "VANDER": "Delantero", "LUCAS": "Delantero",
}
GOALKEEPERS = {"LEJA", "GONZALO (P)"}
NAME_ALIASES = {
    "ALEJANDRO": "ÁLEX", "ALEXANDER": "ÁLEX", "ALEX": "ÁLEX",
    "IVAN": "IVÁN", "CESAR": "CÉSAR", "AARON": "AARÓN", "FER RUIZ": "FER RUÍZ",
}
GPS_METRICS = ["total_distance", "hsr", "sprints", "distance_vrange6", "num_acc", "num_dec"]
GPS_LABELS = {
    "total_distance": "Distancia total",
    "hsr": "HSR",
    "sprints": "Sprint",
    "distance_vrange6": "Distancia sprint",
    "num_acc": "ACC",
    "num_dec": "DEC",
}
GPS_DAILY_TARGETS = {
    "MD-4": {"total_distance": (50, 60), "hsr": (10, 20), "sprints": (5, 10), "distance_vrange6": (5, 10), "num_acc": (75, 85), "num_dec": (75, 85)},
    "MD-3": {"total_distance": (65, 75), "hsr": (65, 80), "sprints": (65, 75), "distance_vrange6": (65, 75), "num_acc": (40, 50), "num_dec": (40, 50)},
    "MD-2": {"total_distance": (35, 45), "hsr": (10, 15), "sprints": (5, 15), "distance_vrange6": (5, 15), "num_acc": (20, 30), "num_dec": (20, 30)},
    "MD-1": {"total_distance": (20, 30), "hsr": (5, 10), "sprints": (0, 5), "distance_vrange6": (0, 5), "num_acc": (10, 20), "num_dec": (10, 20)},
    "MD+1": {"total_distance": (60, 70), "hsr": (80, 90), "sprints": (70, 80), "distance_vrange6": (70, 80), "num_acc": (60, 80), "num_dec": (60, 80)},
}
GPS_WEEKLY_TARGETS = {
    "total_distance": (170, 210),
    "hsr": (90, 125),
    "sprints": (75, 105),
    "distance_vrange6": (75, 105),
    "num_acc": (145, 185),
    "num_dec": (145, 185),
}

GPS_MATCH_MINUTES_MIN = 80
GPS_MATCH_MIN_MATCHES = 5

st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 1.25rem;}
.hero {
    background: linear-gradient(135deg, #0F172A 0%, #1F4E79 100%);
    color: white; border-radius: 20px; padding: 24px 26px; margin-bottom: 14px;
    box-shadow: 0 10px 28px rgba(2,6,23,0.22);
}
.card {
    background: white; border-radius: 18px; padding: 16px 18px;
    border: 1px solid rgba(15,23,42,0.08);
    box-shadow: 0 6px 18px rgba(15,23,42,0.06); margin-bottom: 10px;
}
.kpi {
    background: white; border-radius: 16px; padding: 14px 16px;
    border: 1px solid rgba(15,23,42,0.08);
    box-shadow: 0 6px 18px rgba(15,23,42,0.06);
    min-height: 94px;
}
.kpi-label {font-size: 0.82rem; color: #475467;}
.kpi-value {font-size: 1.65rem; font-weight: 800; color: #101828; line-height: 1.1;}
.kpi-sub {font-size: 0.80rem; color: #667085;}
.section-title {font-size: 1.15rem; font-weight: 800; color: #101828; margin: 0.4rem 0 0.7rem 0;}
.pill {
    display:inline-block; padding:4px 10px; border-radius:999px; color:white;
    font-weight:700; font-size:0.78rem; margin-right:6px; margin-top:4px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DB / SUPABASE
# =========================================================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def init_db():
    return None

def load_monitoring():
    supabase = get_supabase()
    try:
        res = supabase.table(SUPABASE_MONITORING_TABLE).select("*").execute()
        data = res.data if getattr(res, "data", None) else []
    except Exception:
        data = []
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["Fecha","Jugador","Microciclo","Posicion","Minutos","CMJ","RSI_mod","VMP","sRPE","Observaciones"])
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    if "Microciclo" not in df.columns:
        df["Microciclo"] = np.nan
    for c in ["Minutos", *ALL_METRICS]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Jugador"] = df["Jugador"].astype(str).map(normalize_player_name)
    return df.sort_values(["Jugador","Fecha"]).reset_index(drop=True)


def standardize_player_names_in_frames(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if "Jugador" in df.columns:
        df["Jugador"] = df["Jugador"].map(normalize_player_name)
    return df

def ensure_gps_datetime(df):
    if df is None:
        return pd.DataFrame()
    df = standardize_player_names_in_frames(df)
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df


def latest_nonmatch_date(metrics_df=None, gps_df=None, player=None):
    candidates = []
    if metrics_df is not None and not metrics_df.empty:
        mdf = metrics_df.copy()
        if player is not None and "Jugador" in mdf.columns:
            mdf = mdf[mdf["Jugador"] == player]
        candidates.extend(pd.to_datetime(mdf["Fecha"], errors="coerce").dropna().tolist())
    if gps_df is not None and not gps_df.empty:
        gdf = ensure_gps_datetime(gps_df)
        if player is not None and "Jugador" in gdf.columns:
            gdf = gdf[gdf["Jugador"] == player]
        gdf = gdf[gdf["Microciclo"].astype(str).str.upper() != "PARTIDO"]
        candidates.extend(pd.to_datetime(gdf["Fecha"], errors="coerce").dropna().tolist())
    if not candidates:
        return None
    return max(candidates)



def get_player_position(player, metrics_df=None, gps_df=None):
    pos = POSITION_MAP.get(str(player), None)
    if pos:
        return pos
    for df in [metrics_df, gps_df]:
        if df is not None and not df.empty and "Posicion" in df.columns and "Jugador" in df.columns:
            vals = df.loc[df["Jugador"] == player, "Posicion"].dropna().astype(str).unique().tolist()
            if vals:
                return vals[0]
    return "Sin asignar"

def build_player_display_options(metrics_df, gps_df):
    players = sorted(set((metrics_df["Jugador"].dropna().unique().tolist() if metrics_df is not None and not metrics_df.empty else []) + (gps_df["Jugador"].dropna().unique().tolist() if gps_df is not None and not gps_df.empty else [])))
    labels = {}
    for p in players:
        labels[f"{p} - {get_player_position(p, metrics_df, gps_df).upper()}"] = p
    return labels

def build_week_options(metrics_df=None, gps_df=None, player=None):
    dates = []
    if metrics_df is not None and not metrics_df.empty:
        mdf = metrics_df.copy()
        if player is not None:
            mdf = mdf[mdf["Jugador"] == player]
        dates.extend(pd.to_datetime(mdf["Fecha"], errors="coerce").dropna().tolist())
    if gps_df is not None and not gps_df.empty:
        gdf = ensure_gps_datetime(gps_df)
        if player is not None:
            gdf = gdf[gdf["Jugador"] == player]
        dates.extend(pd.to_datetime(gdf["Fecha"], errors="coerce").dropna().tolist())
    if not dates:
        return [], {}
    week_starts = sorted({week_start(d) for d in dates if pd.notna(d)})
    labels = {}
    for ws in week_starts:
        we = ws + pd.Timedelta(days=6)
        labels[f"{ws.strftime('%Y-%m-%d')} a {we.strftime('%Y-%m-%d')}"] = ws
    return list(labels.keys()), labels

def session_options_for_week(metrics_df, gps_df, week_ws, player=None):
    opts = []
    if metrics_df is not None and not metrics_df.empty:
        mdf = metrics_df.copy()
        if player is not None:
            mdf = mdf[mdf["Jugador"] == player]
        mdf = mdf[(mdf["Fecha"] >= week_ws) & (mdf["Fecha"] <= week_ws + pd.Timedelta(days=6))]
        for _, r in mdf[["Fecha","Microciclo"]].drop_duplicates().sort_values(["Fecha","Microciclo"]).iterrows():
            d = pd.to_datetime(r["Fecha"]).strftime("%Y-%m-%d")
            md = "Sin día" if pd.isna(r["Microciclo"]) else str(r["Microciclo"])
            opts.append(f"{d} | {md}")
    if gps_df is not None and not gps_df.empty:
        gdf = ensure_gps_datetime(gps_df)
        if player is not None:
            gdf = gdf[gdf["Jugador"] == player]
        gdf = gdf[(gdf["Fecha"] >= week_ws) & (gdf["Fecha"] <= week_ws + pd.Timedelta(days=6)) & (gdf["Microciclo"].astype(str).str.upper() != "PARTIDO")]
        for _, r in gdf[["Fecha","Microciclo"]].drop_duplicates().sort_values(["Fecha","Microciclo"]).iterrows():
            d = pd.to_datetime(r["Fecha"]).strftime("%Y-%m-%d")
            md = str(r["Microciclo"])
            lab = f"{d} | {md}"
            if lab not in opts:
                opts.append(lab)
    return sorted(set(opts))

def plot_team_gps_support(gps_day):
    if gps_day is None or gps_day.empty:
        return go.Figure()
    temp = gps_day.copy()
    if "compliance_score" not in temp.columns:
        return go.Figure()
    fig = px.bar(
        temp.sort_values("compliance_score", ascending=False),
        x="Jugador",
        y="compliance_score",
        color="session_status" if "session_status" in temp.columns else None,
        title="Apoyo visual GPS del día"
    )
    fig.update_layout(height=360, margin=dict(l=20,r=20,t=60,b=40), title_x=0.5)
    fig.update_xaxes(tickangle=-35)
    fig.update_yaxes(title="Cumplimiento %")
    return fig

def plot_player_gps_support(df, title):
    if df is None or df.empty:
        return go.Figure()
    temp = df.copy()
    fig = px.bar(temp, x="Variable", y="pct", color="status", title=title)
    fig.update_layout(height=320, margin=dict(l=20,r=20,t=60,b=30), title_x=0.5)
    fig.update_yaxes(title="% vs partido")
    return fig



def gps_weekly_team_table(gps_df, week_ws):
    gps_df = ensure_gps_datetime(gps_df)
    if gps_df.empty:
        return pd.DataFrame()
    players = sorted(gps_df.loc[gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO", "Jugador"].dropna().unique().tolist())
    rows = []
    for player in players:
        wk = gps_player_week_table(gps_df, player, week_ws)
        if wk.empty:
            continue
        pcts = pd.to_numeric(wk["pct"], errors="coerce")
        mean_pct = float(pcts.mean()) if not pcts.dropna().empty else np.nan
        statuses = wk["status"].astype(str).tolist()
        if any(s == "Alto" for s in statuses):
            status = "Alto"
            color = "#DC2626"
        elif any(s == "Bajo" for s in statuses):
            status = "Bajo"
            color = "#DC2626" if mean_pct < 60 or mean_pct > 120 else "#F59E0B"
        elif all(s == "Adecuado" for s in statuses if s != "Sin referencia") and any(s == "Adecuado" for s in statuses):
            status = "Adecuado"
            color = "#16A34A"
        else:
            status = "Sin referencia"
            color = "#94A3B8"
        rows.append({
            "Jugador": player,
            "Posicion": get_player_position(player, None, gps_df),
            "weekly_compliance": mean_pct,
            "weekly_status": status,
            "color": color,
        })
    return pd.DataFrame(rows)

def plot_team_gps_weekly_support(gps_df, week_ws):
    temp = gps_weekly_team_table(gps_df, week_ws)
    if temp.empty:
        return go.Figure()
    fig = px.bar(
        temp.sort_values("weekly_compliance", ascending=False, na_position="last"),
        x="Jugador",
        y="weekly_compliance",
        color="weekly_status",
        color_discrete_map={"Adecuado":"#16A34A","Bajo":"#F59E0B","Alto":"#DC2626","Sin referencia":"#94A3B8"},
        title="GPS semanal global"
    )
    fig.update_layout(height=360, margin=dict(l=20,r=20,t=60,b=40), title_x=0.5)
    fig.update_xaxes(tickangle=-35)
    fig.update_yaxes(title="Cumplimiento semanal %")
    return fig

def player_weekly_html(player, player_df, gps_df, week_ws):
    week_we = week_ws + pd.Timedelta(days=6)
    fat = player_df[(player_df["Fecha"] >= week_ws) & (player_df["Fecha"] <= week_we)].copy() if player_df is not None and not player_df.empty else pd.DataFrame()
    gps_week = gps_player_week_table(gps_df, player, week_ws) if gps_df is not None else pd.DataFrame()
    gps_sess = pd.DataFrame()
    if gps_df is not None:
        session_options = session_options_for_week(fat, gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame(), week_ws, player=player)
        if session_options:
            d, md = [x.strip() for x in session_options[-1].split("|",1)]
            gps_sess = gps_player_session_table(gps_df, player, pd.to_datetime(d), micro=md)
    gps_week_html = gps_progress_bars_html(gps_week, "Resumen GPS semanal")
    gps_sess_html = gps_progress_bars_html(gps_sess, "Última sesión GPS de la semana")
    fat_fig = ""
    if not fat.empty:
        fat_fig = plotly_html(plot_objective_timeline(fat, fat.iloc[-1]["Fecha"]))
    return f"""<html><head><meta charset='utf-8'>{report_css()}</head><body>
    <div class='hero'><div style='font-size:12px;opacity:0.9;'>Informe semanal individual</div><div style='font-size:32px;font-weight:900;line-height:1.15;'>{player}</div><div style='font-size:15px;margin-top:6px;'>Semana {week_ws.strftime('%Y-%m-%d')} a {week_we.strftime('%Y-%m-%d')}</div></div>
    <div class='cards'>
      <div class='card'><div class='label'>Controles fatiga</div><div class='value'>{0 if fat.empty else fat[['Fecha','Microciclo']].drop_duplicates().shape[0]}</div></div>
      <div class='card'><div class='label'>Readiness media</div><div class='value'>{'NA' if fat.empty else f"{fat['readiness_score'].mean():.1f}"}</div></div>
      <div class='card'><div class='label'>Loss medio</div><div class='value'>{'NA' if fat.empty else f"{fat['objective_loss_score'].mean():.2f}"}</div></div>
      <div class='card'><div class='label'>GPS semanal</div><div class='value'>{'NA' if gps_week.empty else f"{pd.to_numeric(gps_week['pct'], errors='coerce').mean():.1f}%"}</div></div>
    </div>
    <div class='section'><div class='title'>Control de fatiga semanal</div>{fat_fig if fat_fig else "<div class='muted'>Sin datos de control de fatiga esta semana.</div>"}</div>
    {gps_sess_html}
    {gps_week_html}
    </body></html>"""

def build_pdf_bytes_player_weekly(player, player_df, gps_df, week_ws):
    week_we = week_ws + pd.Timedelta(days=6)
    fat = player_df[(player_df["Fecha"] >= week_ws) & (player_df["Fecha"] <= week_we)].copy() if player_df is not None and not player_df.empty else pd.DataFrame()
    gps_week = gps_player_week_table(gps_df, player, week_ws) if gps_df is not None else pd.DataFrame()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = [Paragraph(f"Informe semanal individual · {player}", styles["TitleDark"]), Paragraph(f"Semana {week_ws.strftime('%Y-%m-%d')} a {week_we.strftime('%Y-%m-%d')}", styles["SmallGrey"]), Spacer(1,0.2*cm)]
    if not fat.empty:
        img = fig_to_rl_image(plot_objective_timeline(fat, fat.iloc[-1]["Fecha"]), width_cm=22, height_cm=7)
        if img is not None:
            elems += [img, Spacer(1,0.2*cm)]
    else:
        elems.append(Paragraph("Sin datos de control de fatiga esta semana.", styles["BodyText"]))
        elems.append(Spacer(1,0.15*cm))
    if gps_df is not None:
        elems.extend(gps_weekly_pdf_story(player, gps_df, week_ws, styles))
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

def build_pdf_bytes_player_session_gps_only(player, gps_df, selected_date):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = [Paragraph(f"Informe individual · {player}", styles["TitleDark"]), Paragraph(f"Sesión {pd.to_datetime(selected_date).date()}", styles["SmallGrey"]), Spacer(1,0.2*cm), Paragraph("No hay datos de control de fatiga para esta fecha. Se muestran únicamente los datos GPS disponibles.", styles["BodyText"]), Spacer(1,0.2*cm)]
    if gps_df is not None:
        elems.extend(gps_weekly_pdf_story(player, gps_df, selected_date, styles))
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

def weekly_global_summary(metrics_df, gps_df, week_ws):
    week_we = week_ws + pd.Timedelta(days=6)
    fat = metrics_df[(metrics_df["Fecha"] >= week_ws) & (metrics_df["Fecha"] <= week_we)].copy() if metrics_df is not None and not metrics_df.empty else pd.DataFrame()
    gps = ensure_gps_datetime(gps_df)
    gps = gps[(gps["Fecha"] >= week_ws) & (gps["Fecha"] <= week_we) & (gps["Microciclo"].astype(str).str.upper() != "PARTIDO")] if not gps.empty else pd.DataFrame()
    out = {
        "fatigue_sessions": int(fat[["Fecha","Microciclo"]].drop_duplicates().shape[0]) if not fat.empty else 0,
        "gps_sessions": int(gps[["Fecha","Microciclo"]].drop_duplicates().shape[0]) if not gps.empty else 0,
        "readiness_mean": float(fat["readiness_score"].mean()) if not fat.empty else np.nan,
        "loss_mean": float(fat["objective_loss_score"].mean()) if not fat.empty else np.nan,
        "gps_compliance_mean": float(gps_compute_compliance(gps, reference_df=gps_df)["compliance_score"].mean()) if not gps.empty else np.nan,
        "critical_count": int((fat["risk_label"] == "Fatiga crítica").sum()) if not fat.empty else 0,
    }
    return out

def weekly_global_html(metrics_df, gps_df, week_ws):
    week_we = week_ws + pd.Timedelta(days=6)
    summary = weekly_global_summary(metrics_df, gps_df, week_ws)
    fat = metrics_df[(metrics_df["Fecha"] >= week_ws) & (metrics_df["Fecha"] <= week_we)].copy() if metrics_df is not None and not metrics_df.empty else pd.DataFrame()
    gps = ensure_gps_datetime(gps_df)
    gps = gps[(gps["Fecha"] >= week_ws) & (gps["Fecha"] <= week_we) & (gps["Microciclo"].astype(str).str.upper() != "PARTIDO")] if not gps.empty else pd.DataFrame()
    gps_html = plotly_html(plot_team_gps_weekly_support(gps_df, week_ws)) if not gps.empty else "<div class='muted'>Sin GPS semanal.</div>"
    top_rows = ""
    if not fat.empty:
        top = fat.groupby("Jugador", as_index=False).agg(Loss=("objective_loss_score","mean"), Readiness=("readiness_score","mean")).sort_values("Loss", ascending=False).head(10)
        for _, r in top.iterrows():
            top_rows += f"<tr><td>{r['Jugador']}</td><td>{r['Loss']:.2f}</td><td>{r['Readiness']:.1f}</td></tr>"
    return f"""<html><head><meta charset='utf-8'>{report_css()}</head><body>
    <div class='hero'><div style='font-size:12px;opacity:0.9;'>Informe semanal global</div><div style='font-size:32px;font-weight:900;line-height:1.15;'>Semana {week_ws.strftime('%Y-%m-%d')} a {week_we.strftime('%Y-%m-%d')}</div></div>
    <div class='cards'>
      <div class='card'><div class='label'>Sesiones fatiga</div><div class='value'>{summary['fatigue_sessions']}</div></div>
      <div class='card'><div class='label'>Sesiones GPS</div><div class='value'>{summary['gps_sessions']}</div></div>
      <div class='card'><div class='label'>Readiness media</div><div class='value'>{'NA' if pd.isna(summary['readiness_mean']) else f"{summary['readiness_mean']:.1f}"}</div></div>
      <div class='card'><div class='label'>GPS semanal medio</div><div class='value'>{'NA' if pd.isna(summary['gps_compliance_mean']) else f"{summary['gps_compliance_mean']:.1f}%"}</div></div>
    </div>
    <div class='section'><div class='title'>GPS semanal global</div>{gps_html}</div>
    <div class='section'><div class='title'>Jugadores con mayor fatiga media semanal</div><table class='report-table'><thead><tr><th>Jugador</th><th>Loss medio</th><th>Readiness media</th></tr></thead><tbody>{top_rows}</tbody></table></div>
    </body></html>"""

def build_pdf_bytes_weekly_global(metrics_df, gps_df, week_ws):
    week_we = week_ws + pd.Timedelta(days=6)
    summary = weekly_global_summary(metrics_df, gps_df, week_ws)
    gps = ensure_gps_datetime(gps_df)
    gps = gps[(gps["Fecha"] >= week_ws) & (gps["Fecha"] <= week_we) & (gps["Microciclo"].astype(str).str.upper() != "PARTIDO")] if not gps.empty else pd.DataFrame()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = [Paragraph("Informe semanal global", styles["TitleDark"]), Paragraph(f"Semana {week_ws.strftime('%Y-%m-%d')} a {week_we.strftime('%Y-%m-%d')}", styles["SmallGrey"]), Spacer(1,0.2*cm)]
    data = [["Sesiones fatiga", str(summary["fatigue_sessions"]), "Sesiones GPS", str(summary["gps_sessions"])], ["Readiness media", "NA" if pd.isna(summary["readiness_mean"]) else f"{summary['readiness_mean']:.1f}", "GPS semanal medio", "NA" if pd.isna(summary["gps_compliance_mean"]) else f"{summary['gps_compliance_mean']:.1f}%"]]
    t = Table(data, colWidths=[4*cm,4*cm,4*cm,4*cm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.whitesmoke),("GRID",(0,0),(-1,-1),0.3,colors.lightgrey)]))
    elems += [t, Spacer(1,0.2*cm)]
    if not gps.empty:
        img = fig_to_rl_image(plot_team_gps_weekly_support(gps_df, week_ws), width_cm=22, height_cm=8)
        if img is not None:
            elems += [img, Spacer(1,0.2*cm)]
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

def week_start(date_like):
    d = pd.to_datetime(date_like, errors="coerce")
    if pd.isna(d):
        return pd.NaT
    return (d - pd.to_timedelta(d.weekday(), unit="D")).normalize()

def integrated_week_fatigue_summary(metrics_df, selected_date):
    if metrics_df is None or metrics_df.empty:
        return {
            "fatigue_sessions": 0,
            "readiness_mean": np.nan,
            "loss_mean": np.nan,
            "moderate_or_worse": 0,
            "critical": 0,
        }
    df = metrics_df.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    ws = week_start(selected_date)
    we = ws + pd.Timedelta(days=6)
    week_df = df[(df["Fecha"] >= ws) & (df["Fecha"] <= we)].copy()
    if week_df.empty:
        return {
            "fatigue_sessions": 0,
            "readiness_mean": np.nan,
            "loss_mean": np.nan,
            "moderate_or_worse": 0,
            "critical": 0,
        }
    by_session = week_df.groupby(["Fecha", "Microciclo"], dropna=False).agg(
        readiness_score=("readiness_score", "mean"),
        objective_loss_score=("objective_loss_score", "mean"),
        mod_or_worse=("risk_label", lambda s: int(pd.Series(s).isin(["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"]).sum())),
        critical=("risk_label", lambda s: int((pd.Series(s) == "Fatiga crítica").sum())),
    ).reset_index()
    return {
        "fatigue_sessions": int(len(by_session)),
        "readiness_mean": float(by_session["readiness_score"].mean()) if len(by_session) else np.nan,
        "loss_mean": float(by_session["objective_loss_score"].mean()) if len(by_session) else np.nan,
        "moderate_or_worse": int(by_session["mod_or_worse"].sum()),
        "critical": int(by_session["critical"].sum()),
    }

def integrated_week_text(metrics_df, gps_df, selected_date):
    fat = integrated_week_fatigue_summary(metrics_df, selected_date)
    gps_df = ensure_gps_datetime(gps_df)
    if gps_df.empty:
        gps_sessions = 0
        gps_compliance = np.nan
    else:
        ws = week_start(selected_date)
        we = ws + pd.Timedelta(days=6)
        gps_week = gps_compute_compliance(gps_df[(gps_df["Fecha"] >= ws) & (gps_df["Fecha"] <= we)].copy(), reference_df=gps_df)
        gps_sessions = gps_week[["Fecha","Microciclo"]].drop_duplicates().shape[0] if not gps_week.empty else 0
        gps_compliance = float(gps_week["compliance_score"].mean()) if (not gps_week.empty and "compliance_score" in gps_week.columns) else np.nan
    rtxt = "NA" if pd.isna(fat["readiness_mean"]) else f"{fat['readiness_mean']:.1f}"
    ltxt = "NA" if pd.isna(fat["loss_mean"]) else f"{fat['loss_mean']:.2f}"
    gtxt = "NA" if pd.isna(gps_compliance) else f"{gps_compliance:.1f}%"
    return (
        f"Semana integrada: {fat['fatigue_sessions']} controles de fatiga y {gps_sessions} sesiones GPS. "
        f"Readiness media semanal: {rtxt}. Objective loss medio semanal: {ltxt}. "
        f"Cumplimiento GPS medio semanal: {gtxt}. "
        f"Casos moderados o peores acumulados: {fat['moderate_or_worse']}. Críticos: {fat['critical']}."
    )



def integrated_load_response_label(gps_day_compliance, gps_week_compliance, readiness, loss):
    if pd.notna(gps_week_compliance) and gps_week_compliance >= 85 and pd.notna(readiness) and readiness >= 70:
        return "Buena tolerancia"
    if pd.notna(gps_week_compliance) and gps_week_compliance < 60 and pd.notna(readiness) and readiness >= 75:
        return "Infraestimulación probable"
    if pd.notna(gps_week_compliance) and gps_week_compliance >= 85 and pd.notna(readiness) and readiness < 60:
        return "Carga alta con mala respuesta"
    if pd.notna(gps_week_compliance) and gps_week_compliance < 60 and pd.notna(readiness) and readiness < 60:
        return "Fatiga no explicada por la carga"
    if pd.notna(loss) and loss >= 1.5 and pd.notna(gps_day_compliance) and gps_day_compliance < 60:
        return "Fatiga con estímulo insuficiente"
    return "Relación carga-respuesta estable"

def integrated_decision_from_components(fatigue_risk, base_decision, gps_day_compliance, gps_week_compliance, readiness, weekly_alerts=0):
    severity = 0
    mapping = {
        "Disponible normal": 0,
        "Disponible con control": 1,
        "Controlar carga": 1,
        "Ajustar carga": 2,
        "Reducir exposición": 3,
        "Intervención individual": 4,
    }
    severity = max(severity, mapping.get(base_decision, 0))
    if fatigue_risk in ["Fatiga moderada", "Fatiga moderada-alta"]:
        severity = max(severity, 2)
    if fatigue_risk == "Fatiga crítica":
        severity = max(severity, 4)
    if pd.notna(gps_day_compliance):
        if gps_day_compliance < 50 or gps_day_compliance > 115:
            severity = max(severity, 2)
        elif gps_day_compliance < 65 or gps_day_compliance > 105:
            severity = max(severity, 1)
    if pd.notna(gps_week_compliance):
        if gps_week_compliance < 60 or gps_week_compliance > 115:
            severity = max(severity, 2)
        elif gps_week_compliance < 75 or gps_week_compliance > 105:
            severity = max(severity, 1)
    if pd.notna(readiness) and readiness < 45:
        severity = max(severity, 4)
    elif pd.notna(readiness) and readiness < 60:
        severity = max(severity, 2)
    if weekly_alerts >= 2:
        severity = max(severity, min(4, severity + 1))
    inv = {
        0: ("Disponible normal","🟢"),
        1: ("Disponible con control","🟡"),
        2: ("Ajustar carga","🟠"),
        3: ("Reducir exposición","🟠"),
        4: ("Intervención individual","🔴"),
    }
    return inv.get(severity, ("Disponible normal","🟢"))

def compute_integrated_player_snapshot(player, selected_date, metrics_df, gps_df):
    selected_date = pd.to_datetime(selected_date)
    ws = week_start(selected_date)
    we = ws + pd.Timedelta(days=6)
    out = {
        "gps_day_compliance": np.nan,
        "gps_week_compliance": np.nan,
        "gps_day_status": "Sin GPS",
        "gps_week_status": "Sin GPS",
        "fat_week_readiness": np.nan,
        "fat_week_loss": np.nan,
        "fat_week_sessions": 0,
        "weekly_alerts": 0,
        "days_since_match": np.nan,
        "load_response_label": "Sin información",
        "integrated_decision": "Sin datos",
        "integrated_icon": "⚪",
        "context_label": "Sin contexto competitivo",
    }

    if gps_df is not None and not gps_df.empty:
        gps_df = ensure_gps_datetime(gps_df)
        p_gps = gps_compute_compliance(gps_df[gps_df["Jugador"] == player].copy(), reference_df=gps_df)
        day = p_gps[p_gps["Fecha"].dt.normalize() == selected_date.normalize()].copy()
        if not day.empty and "compliance_score" in day.columns:
            out["gps_day_compliance"] = float(day["compliance_score"].mean())
            out["gps_day_status"] = "Adecuado" if 85 <= out["gps_day_compliance"] <= 100 else ("Desviado" if 70 <= out["gps_day_compliance"] <= 115 else "Muy desviado")
        week = p_gps[(p_gps["Fecha"] >= ws) & (p_gps["Fecha"] <= we) & (p_gps["Microciclo"].astype(str).str.upper() != "PARTIDO")].copy()
        if not week.empty and "compliance_score" in week.columns:
            out["gps_week_compliance"] = float(week["compliance_score"].mean())
            out["gps_week_status"] = "Adecuado" if 85 <= out["gps_week_compliance"] <= 100 else ("Desviado" if 70 <= out["gps_week_compliance"] <= 115 else "Muy desviado")
            out["weekly_alerts"] += int(((week["compliance_score"] < 70) | (week["compliance_score"] > 115)).sum())
        matches = p_gps[p_gps["Microciclo"].astype(str).str.upper() == "PARTIDO"].copy()
        prev_matches = matches[matches["Fecha"] <= selected_date].sort_values("Fecha")
        if not prev_matches.empty:
            last_match = prev_matches.iloc[-1]["Fecha"]
            out["days_since_match"] = int((selected_date.normalize() - pd.to_datetime(last_match).normalize()).days)
            out["context_label"] = f"{out['days_since_match']} días desde el último partido"

    if metrics_df is not None and not metrics_df.empty:
        p_fat = metrics_df[metrics_df["Jugador"] == player].copy()
        p_fat["Fecha"] = pd.to_datetime(p_fat["Fecha"], errors="coerce")
        week_fat = p_fat[(p_fat["Fecha"] >= ws) & (p_fat["Fecha"] <= we)].copy()
        if not week_fat.empty:
            out["fat_week_readiness"] = float(week_fat["readiness_score"].mean())
            out["fat_week_loss"] = float(week_fat["objective_loss_score"].mean())
            out["fat_week_sessions"] = int(week_fat[["Fecha","Microciclo"]].drop_duplicates().shape[0])
            out["weekly_alerts"] += int(week_fat["risk_label"].isin(["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"]).sum())
        day_fat = p_fat[p_fat["Fecha"].dt.normalize() == selected_date.normalize()].copy()
        if not day_fat.empty:
            r = day_fat.iloc[-1]
            dec, icon = integrated_decision_from_components(
                r.get("risk_label","Buen estado"),
                r.get("decision_label","Disponible normal"),
                out["gps_day_compliance"],
                out["gps_week_compliance"],
                r.get("readiness_score", np.nan),
                out["weekly_alerts"],
            )
            out["integrated_decision"] = dec
            out["integrated_icon"] = icon
            out["load_response_label"] = integrated_load_response_label(out["gps_day_compliance"], out["gps_week_compliance"], r.get("readiness_score", np.nan), r.get("objective_loss_score", np.nan))
        elif pd.notna(out["fat_week_readiness"]):
            dec, icon = integrated_decision_from_components(
                "Buen estado", "Disponible normal", out["gps_day_compliance"], out["gps_week_compliance"], out["fat_week_readiness"], out["weekly_alerts"]
            )
            out["integrated_decision"] = dec
            out["integrated_icon"] = icon
            out["load_response_label"] = integrated_load_response_label(out["gps_day_compliance"], out["gps_week_compliance"], out["fat_week_readiness"], out["fat_week_loss"])
    return out

def integrated_alerts_for_player(player, selected_date, metrics_df, gps_df):
    snap = compute_integrated_player_snapshot(player, selected_date, metrics_df, gps_df)
    alerts = []
    if pd.notna(snap["gps_day_compliance"]) and (snap["gps_day_compliance"] < 70 or snap["gps_day_compliance"] > 115):
        alerts.append("Cumplimiento GPS diario fuera de rango")
    if pd.notna(snap["gps_week_compliance"]) and (snap["gps_week_compliance"] < 75 or snap["gps_week_compliance"] > 110):
        alerts.append("Cumplimiento GPS semanal fuera de rango")
    if pd.notna(snap["fat_week_readiness"]) and snap["fat_week_readiness"] < 60:
        alerts.append("Readiness semanal bajo")
    if snap["weekly_alerts"] >= 3:
        alerts.append("Persistencia alta de alertas en la semana")
    if snap["load_response_label"] in ["Carga alta con mala respuesta","Fatiga no explicada por la carga","Fatiga con estímulo insuficiente"]:
        alerts.append(snap["load_response_label"])
    return alerts

def plot_player_integrated_week_dashboard(player, selected_date, metrics_df, gps_df):
    snap = compute_integrated_player_snapshot(player, selected_date, metrics_df, gps_df)
    labels = ["GPS día","GPS semana","Readiness semana","Loss semana inv."]
    vals = [
        0 if pd.isna(snap["gps_day_compliance"]) else snap["gps_day_compliance"],
        0 if pd.isna(snap["gps_week_compliance"]) else snap["gps_week_compliance"],
        0 if pd.isna(snap["fat_week_readiness"]) else snap["fat_week_readiness"],
        0 if pd.isna(snap["fat_week_loss"]) else max(0, 100 - snap["fat_week_loss"] / 3 * 100),
    ]
    fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h", text=[f"{v:.1f}" for v in vals]))
    fig.update_traces(textposition="outside")
    fig.update_layout(title="Dashboard semanal integrado", height=320, margin=dict(l=20,r=20,t=60,b=20))
    fig.update_xaxes(range=[0, 120], title="Índice / %")
    return fig

def plot_integrated_team_matrix(team_day, metrics_df, gps_df, selected_date):
    if team_day.empty:
        return go.Figure()
    rows = []
    for _, r in team_day.iterrows():
        snap = compute_integrated_player_snapshot(r["Jugador"], selected_date, metrics_df, gps_df)
        rows.append({
            "Jugador": r["Jugador"],
            "Loss": r.get("objective_loss_score", np.nan),
            "GPS semana": snap["gps_week_compliance"],
            "Decisión integrada": snap["integrated_decision"],
        })
    temp = pd.DataFrame(rows)
    fig = px.scatter(
        temp, x="GPS semana", y="Loss", text="Jugador", color="Decisión integrada",
        title="Matriz integrada: cumplimiento GPS semanal vs fatiga"
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(height=420, margin=dict(l=20,r=20,t=60,b=20))
    return fig

def player_distribution_summary(player_df):
    if player_df is None or player_df.empty:
        return {}
    counts = player_df["risk_label"].value_counts()
    total = max(1, len(player_df))
    return {k: round(counts.get(k, 0) / total * 100, 1) for k in RISK_ORDER}

def latest_context_summary(player, selected_date, gps_df):
    snap = compute_integrated_player_snapshot(player, selected_date, pd.DataFrame(), gps_df)
    return snap["context_label"]
def upsert_monitoring(df):
    if df.empty:
        return
    supabase = get_supabase()
    now = pd.Timestamp.now().isoformat(timespec="seconds")
    payload = []
    for _, r in df.iterrows():
        payload.append({
            "Fecha": str(pd.to_datetime(r["Fecha"]).date()),
            "Jugador": str(normalize_player_name(r["Jugador"])),
            "Microciclo": None if pd.isna(r.get("Microciclo")) else str(r.get("Microciclo")),
            "Posicion": None if pd.isna(r.get("Posicion")) else str(r.get("Posicion")),
            "Minutos": None if pd.isna(r.get("Minutos")) else float(r.get("Minutos")),
            "CMJ": None if pd.isna(r.get("CMJ")) else float(r.get("CMJ")),
            "RSI_mod": None if pd.isna(r.get("RSI_mod")) else float(r.get("RSI_mod")),
            "VMP": None if pd.isna(r.get("VMP")) else float(r.get("VMP")),
            "sRPE": None if pd.isna(r.get("sRPE")) else float(r.get("sRPE")),
            "Observaciones": None if pd.isna(r.get("Observaciones")) else str(r.get("Observaciones")),
            "updated_at": now,
        })
    supabase.table(SUPABASE_MONITORING_TABLE).upsert(payload, on_conflict="Fecha,Jugador,Microciclo").execute()

# =========================================================
# PARSER
# =========================================================
def safe_num(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace("%", "").replace(",", ".")
    if s == "":
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan

def std_name(x):
    if pd.isna(x):
        return np.nan
    return " ".join(str(x).strip().split()).title()

def try_parse_date(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    try:
        d = pd.to_datetime(s, dayfirst=True, errors="raise")
        if 2000 <= d.year <= 2100:
            return d
    except Exception:
        pass
    m = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", s)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year = m.group(3)
        if year is None:
            year = pd.Timestamp.now().year
        else:
            year = int(year)
            if year < 100:
                year += 2000
        try:
            return pd.Timestamp(year=year, month=month, day=day)
        except Exception:
            return None
    return None

def first_valid_numeric(values):
    vals = [safe_num(v) for v in values]
    vals = [v for v in vals if not pd.isna(v)]
    return vals[0] if vals else np.nan

def detect_format(df_raw):
    cols = [str(c).lower().strip() for c in df_raw.columns]
    joined_cols = " ".join(cols)
    if any(k in joined_cols for k in ["jugador","player"]) and any(k in joined_cols for k in ["cmj","rsi","vmp"]):
        return "tidy"
    flat = " ".join(df_raw.astype(str).fillna("").values.flatten().tolist()).lower()
    if "cmj" in flat or "rsi" in flat or "vmp" in flat:
        return "block"
    if df_raw.shape[1] <= 6:
        return "block"
    return "unknown"

def read_uploaded(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, header=None)
    raise ValueError("Formato no soportado. Usa .csv, .xlsx o .xls")

def parse_tidy(df_raw):
    df = df_raw.copy()
    tmp_cols = [str(c).strip().lower() for c in df.columns]
    first_row = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[0].tolist()] if len(df) else []
    if not any(k in " ".join(tmp_cols) for k in ["jugador","player","cmj","rsi","vmp"]) and any(k in " ".join(first_row) for k in ["jugador","player","cmj","rsi","vmp","fecha","date"]):
        df.columns = [str(v).strip() for v in df.iloc[0].tolist()]
        df = df.iloc[1:].reset_index(drop=True)
    else:
        df.columns = [str(c).strip() for c in df.columns]

    rename = {}
    for c in df.columns:
        low = c.lower().strip()
        if low in ["fecha","date"]: rename[c] = "Fecha"
        elif low in ["microciclo","dia","día","md","day"]: rename[c] = "Microciclo"
        elif low in ["jugador","player","nombre","name"]: rename[c] = "Jugador"
        elif "pos" in low: rename[c] = "Posicion"
        elif "min" in low: rename[c] = "Minutos"
        elif "cmj" in low: rename[c] = "CMJ"
        elif "rsi" in low: rename[c] = "RSI_mod"
        elif "vmp" in low: rename[c] = "VMP"
        elif "srpe" in low or "s-rpe" in low or low == "rpe": rename[c] = "sRPE"
        elif "obs" in low: rename[c] = "Observaciones"
    df = df.rename(columns=rename)

    needed = ["Fecha","Jugador","CMJ","RSI_mod","VMP"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {missing}")

    for optional in ["Microciclo","Posicion","Minutos","Observaciones","sRPE"]:
        if optional not in df.columns:
            df[optional] = np.nan

    df = df[["Fecha","Jugador","Microciclo","Posicion","Minutos","CMJ","RSI_mod","VMP","sRPE","Observaciones"]].copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df["Jugador"] = df["Jugador"].apply(normalize_player_name)
    for c in ["Minutos", *ALL_METRICS]:
        df[c] = df[c].apply(safe_num)
    return df.dropna(subset=["Fecha","Jugador"]).drop_duplicates(subset=["Fecha","Jugador"], keep="last")

def parse_block(df_raw):
    df = df_raw.copy()
    df.columns = range(df.shape[1])
    df = df.replace(r"^\s*$", np.nan, regex=True)

    first_row = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[0].tolist()] if len(df) else []
    if first_row and "nombre" in first_row[0] and any("variable" in x for x in first_row):
        date_cols = []
        for c in range(2, df.shape[1]):
            d = try_parse_date(df.iat[0, c])
            if d is not None:
                date_cols.append((c, d))
        records = []
        i = 1
        while i + 3 < len(df):
            player = df.iat[i, 0]
            var1 = str(df.iat[i, 1]).strip().lower() if pd.notna(df.iat[i, 1]) else ""
            var2 = str(df.iat[i+1, 1]).strip().lower() if pd.notna(df.iat[i+1, 1]) else ""
            var3 = str(df.iat[i+2, 1]).strip().lower() if pd.notna(df.iat[i+2, 1]) else ""
            var4 = str(df.iat[i+3, 1]).strip().lower() if pd.notna(df.iat[i+3, 1]) else ""
            looks_like_group = pd.notna(player) and "cmj" in var1 and "rsi" in var2 and "vmp" in var3 and ("rpe" in var4 or "srpe" in var4 or "s-rpe" in var4)
            if looks_like_group:
                player_name = normalize_player_name(player)
                for c, d in date_cols:
                    cmj = safe_num(df.iat[i, c]) if c < df.shape[1] else np.nan
                    rsi = safe_num(df.iat[i+1, c]) if c < df.shape[1] else np.nan
                    vmp = safe_num(df.iat[i+2, c]) if c < df.shape[1] else np.nan
                    srpe = safe_num(df.iat[i+3, c]) if c < df.shape[1] else np.nan
                    if sum(pd.notna(x) for x in [cmj, rsi, vmp, srpe]) >= 2:
                        records.append({"Fecha": d, "Jugador": player_name, "Posicion": np.nan, "Minutos": np.nan, "CMJ": cmj, "RSI_mod": rsi, "VMP": vmp, "sRPE": srpe, "Observaciones": np.nan})
                i += 4
                continue
            i += 1
        out = pd.DataFrame(records)
        if not out.empty:
            return out.drop_duplicates(subset=["Fecha","Jugador"], keep="last")

    records = []
    current_date = None
    current_player = None
    i = 0
    while i < len(df):
        row = df.iloc[i].tolist()
        parsed_dates = [try_parse_date(v) for v in row if pd.notna(v)]
        parsed_dates = [d for d in parsed_dates if d is not None]
        if parsed_dates:
            current_date = parsed_dates[0]
        tokens = [str(v).strip() for v in row if pd.notna(v) and str(v).strip() != ""]
        if tokens:
            first = tokens[0]
            if first.lower() not in ["cmj","rsi mod","rsi_mod","vmp","srpe","s-rpe","rpe"]:
                if try_parse_date(first) is None and pd.isna(safe_num(first)):
                    current_player = normalize_player_name(first)

        if current_player is not None and current_date is not None and i + 3 < len(df):
            labels = []; nums = []
            for j in range(0,4):
                row_j = df.iloc[i+j].tolist()
                non_empty = [str(v).strip().lower() for v in row_j if pd.notna(v) and str(v).strip() != ""]
                label_j = ""
                for tok in non_empty:
                    if any(k in tok for k in ["cmj","rsi","vmp","rpe","srpe","s-rpe"]):
                        label_j = tok
                        break
                labels.append(label_j)
                nums.append(first_valid_numeric(row_j))
            if "cmj" in labels[0] and "rsi" in labels[1] and "vmp" in labels[2] and any(k in labels[3] for k in ["rpe","srpe","s-rpe"]) and sum(pd.notna(v) for v in nums) >= 3:
                records.append({"Fecha": current_date, "Jugador": current_player, "Posicion": np.nan, "Minutos": np.nan, "CMJ": nums[0], "RSI_mod": nums[1], "VMP": nums[2], "sRPE": nums[3], "Observaciones": np.nan})
                i += 4
                continue

        if current_player is not None and current_date is not None and i + 4 < len(df):
            labels = []; nums = []
            for j in range(1,5):
                row_j = df.iloc[i+j].tolist()
                non_empty = [str(v).strip().lower() for v in row_j if pd.notna(v) and str(v).strip() != ""]
                label_j = ""
                for tok in non_empty:
                    if any(k in tok for k in ["cmj","rsi","vmp","rpe","srpe","s-rpe"]):
                        label_j = tok
                        break
                labels.append(label_j)
                nums.append(first_valid_numeric(row_j))
            if "cmj" in labels[0] and "rsi" in labels[1] and "vmp" in labels[2] and any(k in labels[3] for k in ["rpe","srpe","s-rpe"]) and sum(pd.notna(v) for v in nums) >= 3:
                records.append({"Fecha": current_date, "Jugador": current_player, "Posicion": np.nan, "Minutos": np.nan, "CMJ": nums[0], "RSI_mod": nums[1], "VMP": nums[2], "sRPE": nums[3], "Observaciones": np.nan})
                i += 5
                continue
        i += 1

    out = pd.DataFrame(records)
    if out.empty:
        raise ValueError("No se pudieron interpretar los bloques del archivo.")
    return out.drop_duplicates(subset=["Fecha","Jugador"], keep="last")

def parse_uploaded(uploaded_file):
    df_raw = read_uploaded(uploaded_file)
    fmt = detect_format(df_raw)
    if fmt == "tidy":
        return parse_tidy(df_raw)
    if fmt == "block":
        return parse_block(df_raw)
    raise ValueError("No se pudo detectar el formato del archivo.")


# =========================================================
# GPS DATA
# =========================================================
def normalize_player_name(x):
    if pd.isna(x):
        return np.nan
    s = " ".join(str(x).strip().upper().split())
    s = NAME_ALIASES.get(s, s)
    return s

def gps_num(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return np.nan

def load_gps():
    supabase = get_supabase()
    try:
        res = supabase.table(SUPABASE_GPS_TABLE).select("*").execute()
        data = res.data if getattr(res, "data", None) else []
    except Exception:
        data = []
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["Fecha","Microciclo","Jugador","Posicion","time_played",*GPS_METRICS,"source_type"])
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    if "time_played" not in df.columns:
        df["time_played"] = np.nan
    for c in ["time_played", *GPS_METRICS]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Jugador"] = df["Jugador"].astype(str).map(normalize_player_name)
    return df.sort_values(["Fecha","Microciclo","Jugador"]).reset_index(drop=True)

def upsert_gps(df):
    if df.empty:
        return
    supabase = get_supabase()
    now = pd.Timestamp.now().isoformat(timespec="seconds")
    payload = []
    for _, r in df.iterrows():
        payload.append({
            "Fecha": str(pd.to_datetime(r["Fecha"]).date()),
            "Microciclo": str(r["Microciclo"]),
            "Jugador": str(normalize_player_name(r["Jugador"])),
            "Posicion": None if pd.isna(r.get("Posicion")) else str(r.get("Posicion")),
            "time_played": None if pd.isna(r.get("time_played")) else float(r.get("time_played")),
            "total_distance": None if pd.isna(r.get("total_distance")) else float(r.get("total_distance")),
            "hsr": None if pd.isna(r.get("hsr")) else float(r.get("hsr")),
            "sprints": None if pd.isna(r.get("sprints")) else float(r.get("sprints")),
            "distance_vrange6": None if pd.isna(r.get("distance_vrange6")) else float(r.get("distance_vrange6")),
            "num_acc": None if pd.isna(r.get("num_acc")) else float(r.get("num_acc")),
            "num_dec": None if pd.isna(r.get("num_dec")) else float(r.get("num_dec")),
            "source_type": None if pd.isna(r.get("source_type")) else str(r.get("source_type")),
            "updated_at": now,
        })
    supabase.table(SUPABASE_GPS_TABLE).upsert(payload, on_conflict="Fecha,Microciclo,Jugador").execute()

def delete_fatigue_session(date_str, micro=None):
    supabase = get_supabase()
    query = supabase.table(SUPABASE_MONITORING_TABLE).delete().eq("Fecha", date_str)
    if micro is None or micro == "" or str(micro).lower() == "nan":
        query.execute()
    else:
        query.eq("Microciclo", micro).execute()

def delete_gps_session(date_str, micro):
    supabase = get_supabase()
    supabase.table(SUPABASE_GPS_TABLE).delete().eq("Fecha", date_str).eq("Microciclo", micro).execute()



def find_col_alias(cols_map, aliases, required=True):
    for a in aliases:
        key = str(a).lower().strip()
        if key in cols_map:
            return cols_map[key]
    if required:
        raise ValueError(f"No se encontró ninguna de estas columnas: {aliases}")
    return None

def parse_gps_uploaded(uploaded_file, fecha, microciclo):
    local_find_col_alias = globals().get("find_col_alias")
    if local_find_col_alias is None:
        def local_find_col_alias(cols_map, aliases, required=True):
            for a in aliases:
                key = str(a).lower().strip()
                if key in cols_map:
                    return cols_map[key]
            if required:
                raise ValueError(f"No se encontró ninguna de estas columnas: {aliases}")
            return None

    name = uploaded_file.name.lower()
    sep = ";" if name.endswith(".csv") else None
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file, sep=sep, engine="python", encoding="utf-8-sig", on_bad_lines="skip")
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = [str(c).strip() for c in df.columns]
    cols = {str(c).lower().strip(): c for c in df.columns}

    player_col = local_find_col_alias(cols, ["player", "jugador", "name", "nombre"])
    total_distance_col = local_find_col_alias(cols, ["total_distance"], required=False)
    hsr_col = local_find_col_alias(cols, ["hsr"])
    sprints_col = local_find_col_alias(cols, ["sprints"])
    sprint_dist_col = local_find_col_alias(cols, ["distance_vrange6"], required=False)
    acc_col = local_find_col_alias(cols, ["num_acc"])
    dec_col = local_find_col_alias(cols, ["num_dec"])
    time_col = local_find_col_alias(cols, ["time", "time ", "minutes", "minutos", "duration"], required=False)

    if total_distance_col is None:
        total_distance_col = local_find_col_alias(cols, ["distance", "distancia total", "dist_total"], required=False)
    if sprint_dist_col is None:
        sprint_dist_col = local_find_col_alias(cols, ["sprint_distance", "distancia sprint"], required=False)

    out = pd.DataFrame({
        "Fecha": pd.to_datetime(fecha),
        "Microciclo": microciclo,
        "Jugador": df[player_col].map(normalize_player_name),
        "time_played": df[time_col].map(gps_num) if time_col is not None else np.nan,
        "total_distance": df[total_distance_col].map(gps_num) if total_distance_col is not None else np.nan,
        "hsr": df[hsr_col].map(gps_num),
        "sprints": df[sprints_col].map(gps_num),
        "distance_vrange6": df[sprint_dist_col].map(gps_num) if sprint_dist_col is not None else np.nan,
        "num_acc": df[acc_col].map(gps_num),
        "num_dec": df[dec_col].map(gps_num),
    })
    out["Posicion"] = out["Jugador"].map(POSITION_MAP).fillna("Sin asignar")
    out = out[out["Posicion"] != "Portero"].copy()
    out["source_type"] = "match" if str(microciclo).upper() == "PARTIDO" else "microcycle"
    return out.drop_duplicates(subset=["Fecha","Microciclo","Jugador"], keep="last")

def build_match_profile(gps_df):
    gps_df = ensure_gps_datetime(gps_df)
    base_cols = ["Jugador", "Posicion", "profile_source", "qualified_matches", *[f"{m}_match" for m in GPS_METRICS]]
    if gps_df.empty:
        return pd.DataFrame(columns=base_cols)

    work = gps_df.copy()
    if "Posicion" not in work.columns:
        work["Posicion"] = work["Jugador"].map(POSITION_MAP).fillna("Sin asignar")
    else:
        work["Posicion"] = work["Posicion"].fillna(work["Jugador"].map(POSITION_MAP)).fillna("Sin asignar")

    match_df = work[work["Microciclo"].astype(str).str.upper() == "PARTIDO"].copy()
    if match_df.empty:
        return pd.DataFrame(columns=base_cols)

    if "time_played" not in match_df.columns:
        match_df["time_played"] = np.nan
    match_df["time_played"] = pd.to_numeric(match_df["time_played"], errors="coerce")

    qualified = match_df[match_df["time_played"] >= GPS_MATCH_MINUTES_MIN].copy()
    if qualified.empty:
        return pd.DataFrame(columns=base_cols)

    match_counts = qualified.groupby("Jugador").size().rename("qualified_matches").reset_index()
    eligible_players = set(match_counts.loc[match_counts["qualified_matches"] >= GPS_MATCH_MIN_MATCHES, "Jugador"].tolist())

    self_profiles = (
        qualified[qualified["Jugador"].isin(eligible_players)]
        .groupby(["Jugador", "Posicion"], dropna=False)[GPS_METRICS]
        .mean()
        .reset_index()
        .merge(match_counts, on="Jugador", how="left")
    )
    self_profiles["profile_source"] = "propio"

    pos_profiles = (
        qualified[qualified["Jugador"].isin(eligible_players)]
        .groupby("Posicion", dropna=False)[GPS_METRICS]
        .mean()
        .reset_index()
    )

    players = work[["Jugador", "Posicion"]].drop_duplicates().copy()
    players = players[players["Posicion"] != "Portero"].copy()
    players = players.merge(match_counts, on="Jugador", how="left")
    players["qualified_matches"] = players["qualified_matches"].fillna(0)

    final_rows = []
    for _, r in players.iterrows():
        player = r["Jugador"]
        pos = r["Posicion"]
        qn = int(r["qualified_matches"])
        if player in eligible_players:
            src = self_profiles[self_profiles["Jugador"] == player]
            if not src.empty:
                row = {"Jugador": player, "Posicion": pos, "profile_source": "propio", "qualified_matches": qn}
                for m in GPS_METRICS:
                    row[f"{m}_match"] = src.iloc[0][m]
                final_rows.append(row)
                continue

        pos_src = pos_profiles[pos_profiles["Posicion"] == pos]
        row = {"Jugador": player, "Posicion": pos, "profile_source": "posición", "qualified_matches": qn}
        if not pos_src.empty:
            for m in GPS_METRICS:
                row[f"{m}_match"] = pos_src.iloc[0][m]
        else:
            for m in GPS_METRICS:
                row[f"{m}_match"] = np.nan
        final_rows.append(row)

    return pd.DataFrame(final_rows, columns=base_cols)

def gps_status_from_pct(pct, min_v, max_v):
    if pd.isna(pct):
        return "Sin referencia", "#94A3B8"
    if min_v <= pct <= max_v:
        return "Adecuado", "#16A34A"
    if pct < min_v:
        return ("Bajo", "#DC2626") if pct < (min_v - 15) else ("Bajo", "#F59E0B")
    return ("Alto", "#DC2626") if pct > (max_v + 15) else ("Alto", "#F59E0B")

def gps_compute_compliance(gps_df, reference_df=None):
    gps_df = ensure_gps_datetime(gps_df)
    if reference_df is None:
        reference_df = gps_df
    reference_df = ensure_gps_datetime(reference_df)
    if gps_df.empty:
        return gps_df.copy()

    prof = build_match_profile(reference_df)
    merge_keys = ["Jugador", "Posicion"] if "Posicion" in prof.columns and "Posicion" in gps_df.columns else ["Jugador"]
    df = gps_df.merge(prof, on=merge_keys, how="left")

    for m in GPS_METRICS:
        df[f"{m}_pct_match"] = np.where(
            df[f"{m}_match"].notna() & (df[f"{m}_match"] != 0),
            df[m] / df[f"{m}_match"] * 100,
            np.nan
        )

    for m in GPS_METRICS:
        status, colors = [], []
        for _, r in df.iterrows():
            tgt_map = GPS_DAILY_TARGETS.get(str(r["Microciclo"]).upper())
            if tgt_map is None or m not in tgt_map:
                stt, clr = ("Sin objetivo", "#94A3B8")
            else:
                stt, clr = gps_status_from_pct(r.get(f"{m}_pct_match"), *tgt_map[m])
            status.append(stt)
            colors.append(clr)
        df[f"{m}_status"] = status
        df[f"{m}_status_color"] = colors

    def _session_status(row):
        vals = [str(row.get(f"{m}_status", "")) for m in GPS_METRICS]
        if all(v == "Sin referencia" for v in vals):
            return "Sin referencia"
        if any(v == "Alto" for v in vals):
            return "Alto"
        if any(v == "Bajo" for v in vals):
            return "Bajo"
        if any(v == "Adecuado" for v in vals):
            return "Adecuado"
        return "Sin objetivo"

    pct_cols = [f"{m}_pct_match" for m in GPS_METRICS]
    df["compliance_score"] = df[pct_cols].mean(axis=1, skipna=True)
    df["session_status"] = df.apply(_session_status, axis=1)
    return df

def gps_player_week_table(gps_df, player, any_date):
    gps_df = ensure_gps_datetime(gps_df)
    if gps_df.empty:
        return pd.DataFrame()

    any_date = pd.to_datetime(any_date)
    start = any_date.normalize() - pd.Timedelta(days=any_date.weekday())
    end = start + pd.Timedelta(days=6)

    df = gps_df[
        (gps_df["Jugador"] == player)
        & (gps_df["Fecha"] >= start)
        & (gps_df["Fecha"] <= end)
        & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")
    ].copy()
    if df.empty:
        return pd.DataFrame()

    prof = build_match_profile(gps_df)
    row = df[GPS_METRICS].sum(numeric_only=True)
    out = pd.DataFrame({"Variable": [GPS_LABELS[m] for m in GPS_METRICS]})
    match_row = prof[prof["Jugador"] == player]

    pcts, mins, maxs, sts, colors = [], [], [], [], []
    for m in GPS_METRICS:
        match_val = match_row[f"{m}_match"].iloc[0] if not match_row.empty else np.nan
        pct = (row[m] / match_val * 100) if pd.notna(match_val) and match_val != 0 else np.nan
        pcts.append(pct)
        mn, mx = GPS_WEEKLY_TARGETS[m]
        mins.append(mn)
        maxs.append(mx)
        stt, clr = gps_status_from_pct(pct, mn, mx)
        sts.append(stt)
        colors.append(clr)

    out["pct"] = pcts
    out["min"] = mins
    out["max"] = maxs
    out["status"] = sts
    out["color"] = colors
    return out

def gps_player_session_table(gps_df, player, date_value, micro=None):
    gps_df = ensure_gps_datetime(gps_df)
    if gps_df.empty:
        return pd.DataFrame()

    date_value = pd.to_datetime(date_value).normalize()
    full_player = gps_df[gps_df["Jugador"] == player].copy()
    if full_player.empty:
        return pd.DataFrame()

    full_comp = gps_compute_compliance(full_player, reference_df=gps_df)
    df = full_comp[full_comp["Fecha"].dt.normalize() == date_value].copy()
    if micro is not None:
        df = df[df["Microciclo"] == micro]
    if df.empty:
        return pd.DataFrame()

    non_match_df = df[df["Microciclo"].astype(str).str.upper() != "PARTIDO"].copy()
    if not non_match_df.empty:
        r = non_match_df.sort_values(["Fecha", "Microciclo"]).iloc[-1]
    else:
        r = df.sort_values(["Fecha", "Microciclo"]).iloc[-1]

    rows = []
    targets = GPS_DAILY_TARGETS.get(str(r["Microciclo"]).upper(), {})
    for m in GPS_METRICS:
        mn, mx = targets.get(m, (np.nan, np.nan))
        pct_val = r.get(f"{m}_pct_match", np.nan)
        rows.append({
            "Variable": GPS_LABELS[m],
            "pct": pct_val,
            "min": mn,
            "max": mx,
            "status": r.get(f"{m}_status", "Sin objetivo"),
            "color": r.get(f"{m}_status_color", "#94A3B8"),
        })
    return pd.DataFrame(rows)

def gps_progress_bars_html(df, title):
    if df is None or df.empty:
        return "<div class='section'><div class='title'>" + title + "</div><div class='muted'>Sin datos GPS disponibles.</div></div>"
    blocks = []
    for _, r in df.iterrows():
        pct = np.nan if pd.isna(r["pct"]) else float(r["pct"])
        width = 0 if pd.isna(pct) else max(0, min(100, pct))
        pct_txt = "Sin referencia" if pd.isna(pct) else f"{pct:.1f}%"
        blocks.append(
            f"<div style='margin-bottom:10px;'><div style='display:flex;justify-content:space-between;font-size:13px;'>"
            f"<span><strong>{r['Variable']}</strong></span><span>{pct_txt} (objetivo {r['min']}-{r['max']}%)</span></div>"
            f"<div style='width:100%;background:#E5E7EB;border-radius:999px;height:12px;overflow:hidden;'><div style='width:{width}%;background:{r['color']};height:12px;'></div></div></div>"
        )
    return f"<div class='section'><div class='title'>{title}</div>{''.join(blocks)}</div>"

def gps_progress_bars_streamlit(df, title):
    st.markdown(f"### {title}")
    if df is None or df.empty:
        st.info("Sin datos GPS disponibles.")
        return
    for _, r in df.iterrows():
        pct = 0 if pd.isna(r["pct"]) else float(r["pct"])
        width = max(0, min(100, pct))
        st.markdown(
            f"<div style='margin-bottom:10px;'><div style='display:flex;justify-content:space-between;font-size:13px;'>"
            f"<span><strong>{r['Variable']}</strong></span><span>{pct:.1f}% (objetivo {r['min']}-{r['max']}%)</span></div>"
            f"<div style='width:100%;background:#E5E7EB;border-radius:999px;height:12px;overflow:hidden;'><div style='width:{width}%;background:{r['color']};height:12px;'></div></div></div>",
            unsafe_allow_html=True
        )

def gps_player_report_html(player, gps_df, selected_date):
    gps_df = ensure_gps_datetime(gps_df)
    week_df = gps_player_week_table(gps_df, player, selected_date)
    sess_df = gps_player_session_table(gps_df, player, selected_date)
    sess_fig = plotly_html(plot_player_gps_support(sess_df, "Apoyo visual GPS de la sesión")) if sess_df is not None and not sess_df.empty else ""
    week_fig = plotly_html(plot_player_gps_support(week_df, "Apoyo visual GPS semanal")) if week_df is not None and not week_df.empty else ""
    return f"""
    <div class='section'><div class='title'>Carga GPS de la sesión</div>{gps_progress_bars_html(sess_df, 'Cumplimiento del día')}{sess_fig}</div>
    <div class='section'><div class='title'>Carga GPS semanal</div>{gps_progress_bars_html(week_df, 'Acumulado semanal')}{week_fig}</div>
    """

def gps_weekly_pdf_story(player, gps_df, selected_date, styles):
    elems = []
    week_df = gps_player_week_table(gps_df, player, selected_date)
    sess_df = gps_player_session_table(gps_df, player, selected_date)
    if not sess_df.empty:
        elems.append(Paragraph("Carga GPS de la sesión", styles["SectionDark"]))
        data = [["Variable","% sesión vs partido","Objetivo min","Objetivo max","Estado"]]
        for _, r in sess_df.iterrows():
            data.append([r["Variable"], f"{r['pct']:.1f}%", r["min"], r["max"], r["status"]])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F172A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),8.2)]))
        elems.append(t); elems.append(Spacer(1, 0.18*cm))
    if not week_df.empty:
        elems.append(Paragraph("Carga GPS semanal", styles["SectionDark"]))
        data = [["Variable","% acumulado vs partido","Objetivo min","Objetivo max","Estado"]]
        for _, r in week_df.iterrows():
            data.append([r["Variable"], f"{r['pct']:.1f}%", r["min"], r["max"], r["status"]])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F172A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),8.2)]))
        elems.append(t); elems.append(Spacer(1, 0.18*cm))
    return elems
# =========================================================
# METRICS / DIAGNOSTIC
# =========================================================
def severity_from_pct(pct_change):
    if pd.isna(pct_change):
        return "Sin referencia", np.nan
    if pct_change >= -2.5:
        return "Buen estado", 0.0
    if pct_change > -5.0:
        return "Fatiga leve", 1.0
    if pct_change > -10.0:
        return "Fatiga moderada", 2.0
    return "Fatiga crítica", 3.0

def classify_risk_from_counts(n_leve, n_mod, n_crit):
    if n_crit >= 2:
        return "Fatiga crítica"
    if n_mod >= 2 and n_crit >= 1:
        return "Fatiga moderada-alta"
    if n_mod >= 2 or n_crit >= 1:
        return "Fatiga moderada"
    if n_leve >= 2 and n_mod >= 1:
        return "Fatiga leve-moderada"
    if n_leve >= 2 or n_mod >= 1:
        return "Fatiga leve"
    if n_leve == 1:
        return "Buen estado"
    return "Estado óptimo"

def slope_last_n(series, n=3):
    s = pd.Series(series).dropna()
    if len(s) < 2:
        return np.nan
    s = s.tail(n).reset_index(drop=True)
    x = np.arange(len(s))
    try:
        return np.polyfit(x, s, 1)[0]
    except Exception:
        return np.nan

def trend_label_from_slope(slope):
    if pd.isna(slope):
        return "Sin tendencia"
    if slope > 0.15:
        return "Empeorando"
    if slope < -0.15:
        return "Mejorando"
    return "Estable"

def zscore_prior_or_full(group_series):
    full_mean = group_series.mean()
    full_std = group_series.std(ddof=0)
    prior_mean = group_series.shift(1).expanding().mean()
    prior_std = group_series.shift(1).expanding().std(ddof=0)
    mean = prior_mean.fillna(full_mean)
    std = prior_std.fillna(full_std).replace(0, np.nan)
    return mean, std

def historical_percentile(player_df, value, metric):
    series = player_df[metric].dropna()
    if len(series) == 0 or pd.isna(value):
        return np.nan
    return round((series <= value).mean() * 100, 1)

def infer_fatigue_profile(row):
    vals = {m: row.get(f"{m}_pct_vs_baseline", np.nan) for m in OBJECTIVE_METRICS}
    clean = {k:v for k,v in vals.items() if pd.notna(v)}
    worst_metric, worst_value = (None, None)
    if clean:
        worst_metric = min(clean, key=clean.get)
        worst_value = clean[worst_metric]
    if worst_metric == "CMJ":
        main = "perfil de fatiga predominantemente explosivo"
    elif worst_metric == "RSI_mod":
        main = "perfil de fatiga predominantemente reactivo"
    elif worst_metric == "VMP":
        main = "perfil de fatiga predominantemente de fuerza/velocidad"
    else:
        main = "perfil sin una afectación dominante clara"
    moderate_or_worse = sum(int(row.get(f"{m}_severity_points", np.nan) >= 2) if pd.notna(row.get(f"{m}_severity_points", np.nan)) else 0 for m in OBJECTIVE_METRICS)
    if moderate_or_worse >= 2:
        pattern = "afectación global"
    elif moderate_or_worse == 1:
        pattern = "afectación específica"
    else:
        pattern = "alteración ligera"
    return main, pattern, worst_metric, worst_value

def flags_for_player(player_df, row):
    flags = []
    if row["objective_loss_score"] == player_df["objective_loss_score"].max():
        flags.append("Peor objective loss score del periodo")
    if row.get("trend_label") == "Empeorando":
        flags.append("Tendencia reciente negativa")
    if pd.notna(row.get("objective_z_score")) and row.get("objective_z_score") <= -1.5:
        flags.append("Valor anómalo para su patrón habitual")
    if row.get("risk_label") in ["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"]:
        flags.append("Requiere decisión individual")
    return flags


def stability_label(cv):
    if pd.isna(cv):
        return "Sin referencia"
    if cv < 5:
        return "Muy estable"
    if cv < 8:
        return "Estable"
    if cv < 12:
        return "Variable"
    return "Muy variable"

def decision_from_row(row):
    risk = row.get("risk_label", "Buen estado")
    trend = row.get("trend_label", "Estable")
    persistent = row.get("recent_alerts_14d", 0)
    if risk == "Fatiga crítica":
        return "Intervención individual", "🔴"
    if risk == "Fatiga moderada-alta":
        return "Reducir exposición", "🔴"
    if risk == "Fatiga moderada":
        return ("Reducir exposición" if persistent >= 2 or trend == "Empeorando" else "Ajustar carga"), "🟠"
    if risk == "Fatiga leve-moderada":
        return "Ajustar carga", "🟠"
    if risk == "Fatiga leve":
        return ("Controlar carga" if trend == "Empeorando" else "Disponible con control"), "🟡"
    if risk == "Buen estado":
        return "Disponible normal", "🟢"
    return "Disponible normal", "🟢"

def availability_from_decision(decision):
    mapping = {
        "Disponible normal": "Apto normal",
        "Disponible con control": "Apto con control",
        "Controlar carga": "Apto con control",
        "Ajustar carga": "Exposición reducida",
        "Reducir exposición": "Exposición reducida",
        "Intervención individual": "Individualizar",
    }
    return mapping.get(decision, "Apto normal")

def pretraining_summary(team_day):
    if team_day.empty:
        return {}
    out = {}
    out["disponibles_normales"] = int((team_day["decision_label"] == "Disponible normal").sum())
    out["control"] = int(team_day["decision_label"].isin(["Disponible con control", "Controlar carga"]).sum())
    out["ajustar"] = int(team_day["decision_label"].isin(["Ajustar carga", "Reducir exposición"]).sum())
    out["individualizar"] = int((team_day["decision_label"] == "Intervención individual").sum())
    out["reactivos"] = int((team_day["dominant_profile"] == "reactivo").sum())
    out["globales"] = int((team_day["fatigue_pattern"] == "afectación global").sum())
    return out

def pretraining_text(team_day):
    s = pretraining_summary(team_day)
    if not s:
        return "No hay datos."
    return (
        f"{s['disponibles_normales']} disponibles normales, "
        f"{s['control']} con control, "
        f"{s['ajustar']} para ajustar carga y "
        f"{s['individualizar']} para individualizar. "
        f"Perfiles reactivos detectados: {s['reactivos']}. "
        f"Afectación global: {s['globales']}."
    )

def compute_metrics(df):
    if df.empty:
        return df.copy()
    df = df.copy().sort_values(["Jugador","Fecha"]).reset_index(drop=True)

    for metric in ALL_METRICS:
        full_mean = df.groupby("Jugador")[metric].transform("mean")
        expanding_sum = df.groupby("Jugador")[metric].transform(lambda s: s.shift(1).expanding().sum())
        expanding_count = df.groupby("Jugador")[metric].transform(lambda s: s.shift(1).expanding().count())
        prior_mean = expanding_sum / expanding_count
        baseline = prior_mean.where(expanding_count > 0, full_mean)

        df[f"{metric}_baseline"] = baseline
        df[f"{metric}_pct_vs_baseline"] = np.where(
            df[f"{metric}_baseline"].notna() & (df[f"{metric}_baseline"] != 0),
            (df[metric] - df[f"{metric}_baseline"]) / df[f"{metric}_baseline"] * 100,
            np.nan,
        )

        means, stds = [], []
        for _, g in df.groupby("Jugador")[metric]:
            m, s = zscore_prior_or_full(g)
            means.extend(m.tolist()); stds.extend(s.tolist())
        df[f"{metric}_z_mean_ref"] = means
        df[f"{metric}_z_std_ref"] = stds
        df[f"{metric}_z"] = np.where(
            pd.notna(df[f"{metric}_z_std_ref"]) & (df[f"{metric}_z_std_ref"] != 0),
            (df[metric] - df[f"{metric}_z_mean_ref"]) / df[f"{metric}_z_std_ref"],
            np.nan,
        )

        df[f"{metric}_ma3"] = df.groupby("Jugador")[metric].transform(lambda s: s.rolling(window=3, min_periods=1).mean())
        df[f"{metric}_ma5"] = df.groupby("Jugador")[metric].transform(lambda s: s.rolling(window=5, min_periods=1).mean())
        df[f"{metric}_pct_vs_ma3"] = np.where(
            df[f"{metric}_ma3"].notna() & (df[f"{metric}_ma3"] != 0),
            (df[metric] - df[f"{metric}_ma3"]) / df[f"{metric}_ma3"] * 100,
            np.nan,
        )

    for metric in OBJECTIVE_METRICS:
        sev = df[f"{metric}_pct_vs_baseline"].apply(severity_from_pct)
        df[f"{metric}_severity"] = sev.apply(lambda x: x[0])
        df[f"{metric}_severity_points"] = sev.apply(lambda x: x[1])

    df["n_leve"] = sum((df[f"{m}_severity"] == "Fatiga leve").astype(int) for m in OBJECTIVE_METRICS)
    df["n_mod"] = sum((df[f"{m}_severity"] == "Fatiga moderada").astype(int) for m in OBJECTIVE_METRICS)
    df["n_crit"] = sum((df[f"{m}_severity"] == "Fatiga crítica").astype(int) for m in OBJECTIVE_METRICS)
    df["objective_loss_score"] = df[[f"{m}_severity_points" for m in OBJECTIVE_METRICS]].mean(axis=1, skipna=True)
    df["objective_loss_mean_pct"] = df[[f"{m}_pct_vs_baseline" for m in OBJECTIVE_METRICS]].mean(axis=1, skipna=True)
    df["risk_label"] = df.apply(lambda r: classify_risk_from_counts(int(r["n_leve"]), int(r["n_mod"]), int(r["n_crit"])), axis=1)
    df["objective_z_score"] = df[[f"{m}_z" for m in OBJECTIVE_METRICS]].mean(axis=1, skipna=True)
    df["readiness_score"] = np.clip(100 - (df["objective_loss_score"] / 3.0) * 100, 0, 100)
    df["objective_loss_score_ma3"] = df.groupby("Jugador")["objective_loss_score"].transform(lambda s: s.rolling(window=3, min_periods=1).mean())

    trend_slopes = []
    for _, g in df.groupby("Jugador"):
        vals = g["objective_loss_score"].tolist()
        local = []
        for i in range(len(vals)):
            local.append(slope_last_n(vals[: i + 1], n=3))
        trend_slopes.extend(local)
    df["objective_loss_slope_3"] = trend_slopes
    df["trend_label"] = df["objective_loss_slope_3"].apply(trend_label_from_slope)

    team = df.groupby("Fecha")[OBJECTIVE_METRICS].mean().reset_index().rename(columns={m: f"{m}_team_mean" for m in OBJECTIVE_METRICS})
    df = df.merge(team, on="Fecha", how="left")
    for m in OBJECTIVE_METRICS:
        df[f"{m}_vs_team_pct"] = np.where(
            df[f"{m}_team_mean"].notna() & (df[f"{m}_team_mean"] != 0),
            (df[m] - df[f"{m}_team_mean"]) / df[f"{m}_team_mean"] * 100,
            np.nan,
        )

    for metric in OBJECTIVE_METRICS + ["objective_loss_score","readiness_score"]:
        asc = metric != "readiness_score"
        df[f"{metric}_team_rank"] = df.groupby("Fecha")[metric].rank(method="min", ascending=asc)

    perc = {m: [] for m in OBJECTIVE_METRICS}
    cvs = []
    cv_labels = []
    dom_profiles = []
    patterns = []
    recent7 = []
    recent14 = []

    for player, g in df.groupby("Jugador"):
        g = g.sort_values("Fecha")
        obj_cv = (g[OBJECTIVE_METRICS].stack().std(ddof=0) / g[OBJECTIVE_METRICS].stack().mean() * 100) if g[OBJECTIVE_METRICS].stack().mean() not in [0, np.nan] else np.nan
        for _, r in g.iterrows():
            hist = g[g["Fecha"] <= r["Fecha"]]
            for m in OBJECTIVE_METRICS:
                perc[m].append(historical_percentile(hist, r[m], m))

            cutoff7 = r["Fecha"] - pd.Timedelta(days=7)
            cutoff14 = r["Fecha"] - pd.Timedelta(days=14)
            h7 = g[(g["Fecha"] >= cutoff7) & (g["Fecha"] <= r["Fecha"])]
            h14 = g[(g["Fecha"] >= cutoff14) & (g["Fecha"] <= r["Fecha"])]
            recent7.append(int(h7["risk_label"].isin(["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"]).sum()))
            recent14.append(int(h14["risk_label"].isin(["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"]).sum()))

            main, pattern, worst_metric, _ = infer_fatigue_profile(r)
            if worst_metric == "CMJ":
                dom = "explosivo"
            elif worst_metric == "RSI_mod":
                dom = "reactivo"
            elif worst_metric == "VMP":
                dom = "fuerza/velocidad"
            else:
                dom = "sin dominancia"
            dom_profiles.append(dom)
            patterns.append(pattern)
            cvs.append(obj_cv)
            cv_labels.append(stability_label(obj_cv))

    for m in OBJECTIVE_METRICS:
        df[f"{m}_historical_percentile"] = perc[m]
    df["objective_cv"] = cvs
    df["objective_cv_label"] = cv_labels
    df["dominant_profile"] = dom_profiles
    df["fatigue_pattern"] = patterns
    df["recent_alerts_7d"] = recent7
    df["recent_alerts_14d"] = recent14

    decisions = df.apply(decision_from_row, axis=1)
    df["decision_label"] = decisions.apply(lambda x: x[0])
    df["decision_icon"] = decisions.apply(lambda x: x[1])
    df["availability_label"] = df["decision_label"].apply(availability_from_decision)
    df["consecutive_modplus"] = (
        df["risk_label"].isin(["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"])
        .groupby(df["Jugador"]).cumsum()
    )
    return df.copy()
    df = df.copy().sort_values(["Jugador","Fecha"]).reset_index(drop=True)

    for metric in ALL_METRICS:
        full_mean = df.groupby("Jugador")[metric].transform("mean")
        expanding_sum = df.groupby("Jugador")[metric].transform(lambda s: s.shift(1).expanding().sum())
        expanding_count = df.groupby("Jugador")[metric].transform(lambda s: s.shift(1).expanding().count())
        prior_mean = expanding_sum / expanding_count
        baseline = prior_mean.where(expanding_count > 0, full_mean)

        df[f"{metric}_baseline"] = baseline
        df[f"{metric}_pct_vs_baseline"] = np.where(
            df[f"{metric}_baseline"].notna() & (df[f"{metric}_baseline"] != 0),
            (df[metric] - df[f"{metric}_baseline"]) / df[f"{metric}_baseline"] * 100,
            np.nan,
        )

        means, stds = [], []
        for _, g in df.groupby("Jugador")[metric]:
            m, s = zscore_prior_or_full(g)
            means.extend(m.tolist()); stds.extend(s.tolist())
        df[f"{metric}_z_mean_ref"] = means
        df[f"{metric}_z_std_ref"] = stds
        df[f"{metric}_z"] = np.where(
            pd.notna(df[f"{metric}_z_std_ref"]) & (df[f"{metric}_z_std_ref"] != 0),
            (df[metric] - df[f"{metric}_z_mean_ref"]) / df[f"{metric}_z_std_ref"],
            np.nan,
        )

        df[f"{metric}_ma3"] = df.groupby("Jugador")[metric].transform(lambda s: s.rolling(window=3, min_periods=1).mean())

    for metric in OBJECTIVE_METRICS:
        sev = df[f"{metric}_pct_vs_baseline"].apply(severity_from_pct)
        df[f"{metric}_severity"] = sev.apply(lambda x: x[0])
        df[f"{metric}_severity_points"] = sev.apply(lambda x: x[1])

    df["n_leve"] = sum((df[f"{m}_severity"] == "Fatiga leve").astype(int) for m in OBJECTIVE_METRICS)
    df["n_mod"] = sum((df[f"{m}_severity"] == "Fatiga moderada").astype(int) for m in OBJECTIVE_METRICS)
    df["n_crit"] = sum((df[f"{m}_severity"] == "Fatiga crítica").astype(int) for m in OBJECTIVE_METRICS)
    df["objective_loss_score"] = df[[f"{m}_severity_points" for m in OBJECTIVE_METRICS]].mean(axis=1, skipna=True)
    df["objective_loss_mean_pct"] = df[[f"{m}_pct_vs_baseline" for m in OBJECTIVE_METRICS]].mean(axis=1, skipna=True)
    df["risk_label"] = df.apply(lambda r: classify_risk_from_counts(int(r["n_leve"]), int(r["n_mod"]), int(r["n_crit"])), axis=1)
    df["objective_z_score"] = df[[f"{m}_z" for m in OBJECTIVE_METRICS]].mean(axis=1, skipna=True)
    df["readiness_score"] = np.clip(100 - (df["objective_loss_score"] / 3.0) * 100, 0, 100)
    df["objective_loss_score_ma3"] = df.groupby("Jugador")["objective_loss_score"].transform(lambda s: s.rolling(window=3, min_periods=1).mean())

    trend_slopes = []
    for _, g in df.groupby("Jugador"):
        vals = g["objective_loss_score"].tolist()
        local = []
        for i in range(len(vals)):
            local.append(slope_last_n(vals[: i + 1], n=3))
        trend_slopes.extend(local)
    df["objective_loss_slope_3"] = trend_slopes
    df["trend_label"] = df["objective_loss_slope_3"].apply(trend_label_from_slope)

    team = df.groupby("Fecha")[OBJECTIVE_METRICS].mean().reset_index().rename(columns={m: f"{m}_team_mean" for m in OBJECTIVE_METRICS})
    df = df.merge(team, on="Fecha", how="left")
    for m in OBJECTIVE_METRICS:
        df[f"{m}_vs_team_pct"] = np.where(
            df[f"{m}_team_mean"].notna() & (df[f"{m}_team_mean"] != 0),
            (df[m] - df[f"{m}_team_mean"]) / df[f"{m}_team_mean"] * 100,
            np.nan,
        )

    for metric in OBJECTIVE_METRICS + ["objective_loss_score","readiness_score"]:
        asc = metric != "readiness_score"
        df[f"{metric}_team_rank"] = df.groupby("Fecha")[metric].rank(method="min", ascending=asc)

    perc = {m: [] for m in OBJECTIVE_METRICS}
    for _, g in df.groupby("Jugador"):
        g = g.sort_values("Fecha")
        for _, r in g.iterrows():
            hist = g[g["Fecha"] <= r["Fecha"]]
            for m in OBJECTIVE_METRICS:
                perc[m].append(historical_percentile(hist, r[m], m))
    for m in OBJECTIVE_METRICS:
        df[f"{m}_historical_percentile"] = perc[m]
    return df

# =========================================================
# UI HELPERS
# =========================================================
def kpi(label, value, sub=""):
    st.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

def render_pills(row):
    html = ""
    for m in OBJECTIVE_METRICS:
        status = row.get(f"{m}_severity", "Sin referencia")
        color = SEVERITY_COLORS.get(status, "#94A3B8")
        html += f'<span class="pill" style="background:{color};">{LABELS[m]} · {status}</span>'
    return html

def recommendation_from_row(row):
    risk = row["risk_label"]; trend = row.get("trend_label", "Sin tendencia")
    if risk == "Fatiga crítica":
        return f"Reducir claramente la exigencia neuromuscular en MD-1. Tendencia: {trend.lower()}."
    if risk in ["Fatiga moderada","Fatiga moderada-alta"]:
        return f"Conviene controlar volumen e intensidad y vigilar la respuesta en el calentamiento. Tendencia: {trend.lower()}."
    if risk in ["Fatiga leve","Fatiga leve-moderada"]:
        return f"Hay una pérdida objetiva leve/moderada; prioriza una MD-1 conservadora y sin estímulos residuales. Tendencia: {trend.lower()}."
    return f"Estado compatible con normalidad funcional para MD-1. Tendencia: {trend.lower()}."

def player_comment(row):
    issues = []
    for metric in OBJECTIVE_METRICS:
        sev = row.get(f"{metric}_severity"); pct = row.get(f"{metric}_pct_vs_baseline")
        if sev not in [None, "Buen estado", "Sin referencia"] and pd.notna(pct):
            issues.append(f"{LABELS[metric]}: {sev.lower()} ({pct:.1f}%)")
    base = "Pérdida objetiva detectada en " + "; ".join(issues) + "." if issues else "No se observan pérdidas objetivas relevantes respecto a la línea base."
    return base + " " + recommendation_from_row(row)

def team_interpretation(df_last):
    if df_last.empty:
        return "No hay registros para interpretar."
    critical = (df_last["risk_label"] == "Fatiga crítica").sum()
    mod_or_worse = df_last["risk_label"].isin(["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"]).sum()
    mean_loss = df_last["objective_loss_score"].mean()
    if critical >= 2 or mean_loss >= 2.0:
        return "El grupo presenta una señal colectiva alta de pérdida de rendimiento en MD-1. Conviene minimizar la carga neuromuscular y priorizar frescura."
    if mod_or_worse >= max(2, round(len(df_last) * 0.25)) or mean_loss >= 1.2:
        return "Existe una afectación grupal moderada. La sesión de MD-1 debería ser breve, controlada y con estímulos de activación muy medidos."
    if (df_last["risk_label"].isin(["Fatiga leve","Fatiga leve-moderada"])).sum() >= max(2, round(len(df_last) * 0.3)):
        return "El grupo está globalmente estable, pero aparecen varias señales leves que aconsejan una MD-1 prudente y bien dosificada."
    return "El estado global del grupo es compatible con una MD-1 estable, con pérdidas individuales puntuales y controlables."

# =========================================================
# PLOTS
# =========================================================
def improved_radar(row):
    labels = [LABELS[m] for m in OBJECTIVE_METRICS]
    scores = []
    for m in OBJECTIVE_METRICS:
        pct = row.get(f"{m}_pct_vs_baseline", np.nan)
        if pd.isna(pct): score = 50
        elif pct >= 0: score = 100
        elif pct >= -2.5: score = 85
        elif pct > -5: score = 65
        elif pct > -10: score = 40
        else: score = 15
        scores.append(score)
    labels_closed = labels + [labels[0]]
    scores_closed = scores + [scores[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=scores_closed, theta=labels_closed, fill="toself", line=dict(color="#1F4E79", width=3), fillcolor="rgba(31,78,121,0.28)", name="Actual"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100], tickvals=[15,40,65,85,100], ticktext=["Crítica","Moderada","Leve","Óptimo","Máx"])), showlegend=False, title="Radar de estado neuromuscular", height=360, margin=dict(l=10,r=10,t=35,b=10))
    return fig

def radar_current_vs_baseline(row):
    labels = [LABELS[m] for m in OBJECTIVE_METRICS]
    current_scores, baseline_scores = [], []
    for m in OBJECTIVE_METRICS:
        pct = row.get(f"{m}_pct_vs_baseline", np.nan)
        if pd.isna(pct): score = 50
        elif pct >= 0: score = 100
        elif pct >= -2.5: score = 85
        elif pct > -5: score = 65
        elif pct > -10: score = 40
        else: score = 15
        current_scores.append(score)
        baseline_scores.append(85)
    labels_closed = labels + [labels[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=baseline_scores + [baseline_scores[0]], theta=labels_closed, fill="toself", line=dict(color="#98A2B3", width=2, dash="dash"), fillcolor="rgba(152,162,179,0.10)", name="Baseline visual"))
    fig.add_trace(go.Scatterpolar(r=current_scores + [current_scores[0]], theta=labels_closed, fill="toself", line=dict(color="#1F4E79", width=3), fillcolor="rgba(31,78,121,0.28)", name="Actual"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100], tickvals=[15,40,65,85,100], ticktext=["Crítica","Moderada","Leve","Óptimo","Máx"])), title="Actual vs baseline visual", height=360, margin=dict(l=10,r=10,t=35,b=10))
    return fig

def radar_relative_loss(row):
    labels = [LABELS[m] for m in OBJECTIVE_METRICS]
    losses = []
    hover_txt = []
    for m in OBJECTIVE_METRICS:
        pct = row.get(f"{m}_pct_vs_baseline", np.nan)
        if pd.isna(pct):
            loss = 0
            hover_txt.append(f"{LABELS[m]}: sin referencia")
        else:
            loss = max(0, -float(pct))
            hover_txt.append(f"{LABELS[m]}: {pct:.1f}% vs baseline")
        losses.append(min(loss, 15))
    labels_closed = labels + [labels[0]]
    losses_closed = losses + [losses[0]]
    hover_closed = hover_txt + [hover_txt[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[2.5, 2.5, 2.5, 2.5],
        theta=labels_closed,
        mode="lines",
        line=dict(color="rgba(22,163,74,0.55)", dash="dot", width=2),
        name="Umbral leve"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[5, 5, 5, 5],
        theta=labels_closed,
        mode="lines",
        line=dict(color="rgba(227,160,8,0.60)", dash="dot", width=2),
        name="Umbral moderado"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[10, 10, 10, 10],
        theta=labels_closed,
        mode="lines",
        line=dict(color="rgba(249,115,22,0.65)", dash="dot", width=2),
        name="Umbral crítico"
    ))
    fig.add_trace(go.Scatterpolar(
        r=losses_closed,
        theta=labels_closed,
        fill="toself",
        line=dict(color="#C62828", width=3),
        fillcolor="rgba(198,40,40,0.28)",
        name="Pérdida relativa",
        text=hover_closed,
        hovertemplate="%{text}<extra></extra>"
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 15],
                tickvals=[0, 2.5, 5, 10, 15],
                ticktext=["0", "2.5", "5", "10", "15+"]
            )
        ),
        title="Radar de pérdida relativa (%)",
        height=360,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0)
    )
    return fig

def plot_metric_main(player_df, metric, selected_date):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=player_df["Fecha"], y=player_df[metric], mode="lines+markers", name="Valor real", line=dict(color="#1F4E79", width=3)))
    fig.add_trace(go.Scatter(x=player_df["Fecha"], y=player_df[f"{metric}_ma3"], mode="lines", name="MA3", line=dict(color="#64748B", width=3, dash="dash")))
    fig.add_trace(go.Scatter(x=player_df["Fecha"], y=player_df[f"{metric}_baseline"], mode="lines", name="Baseline", line=dict(color="#0F766E", width=2, dash="dot")))
    sel = player_df[player_df["Fecha"].dt.normalize() == pd.to_datetime(selected_date).normalize()]
    if not sel.empty:
        fig.add_trace(go.Scatter(x=sel["Fecha"], y=sel[metric], mode="markers", name="Fecha", marker=dict(size=12, color="#C62828", symbol="diamond")))
    fig.update_layout(title=f"{LABELS[metric]} · valor real, MA3 y baseline", height=300, margin=dict(l=10,r=10,t=35,b=10))
    return fig

def plot_metric_pct(player_df, metric, selected_date):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=player_df["Fecha"], y=player_df[f"{metric}_pct_vs_baseline"], mode="lines+markers", name="% vs baseline", line=dict(color="#1F4E79", width=3)))
    sel = player_df[player_df["Fecha"].dt.normalize() == pd.to_datetime(selected_date).normalize()]
    if not sel.empty:
        fig.add_trace(go.Scatter(x=sel["Fecha"], y=sel[f"{metric}_pct_vs_baseline"], mode="markers", name="Fecha", marker=dict(size=12, color="#C62828", symbol="diamond")))
    fig.add_hline(y=0, line_dash="dot")
    fig.add_hrect(y0=-2.5, y1=15, fillcolor="rgba(46,139,87,0.10)", line_width=0)
    fig.add_hrect(y0=-5, y1=-2.5, fillcolor="rgba(227,160,8,0.12)", line_width=0)
    fig.add_hrect(y0=-10, y1=-5, fillcolor="rgba(249,115,22,0.12)", line_width=0)
    fig.add_hrect(y0=-30, y1=-10, fillcolor="rgba(198,40,40,0.10)", line_width=0)
    fig.update_layout(title=f"{LABELS[metric]} · % vs baseline", height=300, margin=dict(l=10,r=10,t=35,b=10))
    return fig

def plot_objective_timeline(player_df, selected_date):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=player_df["Fecha"], y=player_df["objective_loss_score"], mode="lines+markers", name="Loss score", line=dict(color="#C62828", width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=player_df["Fecha"], y=player_df["objective_loss_score_ma3"], mode="lines", name="Loss MA3", line=dict(color="#111827", width=2, dash="dash")), secondary_y=False)
    fig.add_trace(go.Scatter(x=player_df["Fecha"], y=player_df["objective_z_score"], mode="lines+markers", name="Z-score objetivo", line=dict(color="#F97316", width=2)), secondary_y=False)
    fig.add_trace(go.Scatter(x=player_df["Fecha"], y=player_df["readiness_score"], mode="lines+markers", name="Readiness", line=dict(color="#0F766E", width=3)), secondary_y=True)
    sel = player_df[player_df["Fecha"].dt.normalize() == pd.to_datetime(selected_date).normalize()]
    if not sel.empty:
        fig.add_trace(go.Scatter(x=sel["Fecha"], y=sel["objective_loss_score"], mode="markers", marker=dict(size=12, color="#111827", symbol="diamond"), name="Fecha"), secondary_y=False)
    fig.update_layout(title="Timeline combinado: loss + readiness + z-score", height=340, margin=dict(l=10,r=10,t=35,b=10))
    fig.update_yaxes(title_text="Loss / Z", secondary_y=False)
    fig.update_yaxes(title_text="Readiness", secondary_y=True)
    return fig

def plot_player_snapshot_compare(row):
    labels = [LABELS[m] for m in OBJECTIVE_METRICS]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=[row.get(f"{m}_pct_vs_baseline", np.nan) for m in OBJECTIVE_METRICS], name="% vs baseline", marker_color="#1F4E79"))
    fig.add_trace(go.Bar(x=labels, y=[row.get(f"{m}_vs_team_pct", np.nan) for m in OBJECTIVE_METRICS], name="% vs equipo", marker_color="#0F766E"))
    fig.add_hline(y=-2.5, line_dash="dot"); fig.add_hline(y=-5, line_dash="dot"); fig.add_hline(y=-10, line_dash="dot")
    fig.update_layout(barmode="group", title="Snapshot de la sesión", height=320, margin=dict(l=10,r=10,t=35,b=10))
    return fig

def plot_team_heatmap(team_df):
    data = team_df.set_index("Jugador")[[f"{m}_pct_vs_baseline" for m in OBJECTIVE_METRICS]].copy()
    data.columns = [LABELS[m] for m in OBJECTIVE_METRICS]
    fig = px.imshow(data, color_continuous_scale=["#B91C1C","#F97316","#E3A008","#16A34A"], zmin=-15, zmax=5, text_auto=".1f", aspect="auto")
    fig.update_layout(title="Heatmap del equipo · % vs línea base", height=max(340, len(data) * 35 + 100), margin=dict(l=10,r=10,t=35,b=10))
    return fig


def plot_team_risk_distribution(team_df):
    temp = team_df["risk_label"].value_counts().reindex(RISK_ORDER, fill_value=0).reset_index()
    temp.columns = ["Estado","N"]
    temp = temp[temp["N"] > 0]
    fig = px.bar(
        temp, y="Estado", x="N", orientation="h", color="Estado",
        color_discrete_map=RISK_COLORS, title="Distribución del riesgo"
    )
    fig.update_layout(
        height=330, margin=dict(l=40,r=20,t=70,b=30), showlegend=False, title_x=0.5
    )
    fig.update_yaxes(automargin=True, title="")
    fig.update_xaxes(automargin=True, title="N")
    return fig

def plot_team_objective_bar(team_df):
    temp = team_df[["Jugador","objective_loss_score","objective_loss_mean_pct","risk_label"]].copy().sort_values(
        ["objective_loss_score","objective_loss_mean_pct"], ascending=[True, True]
    )
    fig = px.bar(
        temp, y="Jugador", x="objective_loss_score", orientation="h",
        color="risk_label", color_discrete_map=RISK_COLORS,
        text="objective_loss_score", title="Objective loss score por jugador",
        hover_data=["objective_loss_mean_pct"]
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=max(420, 24 * len(temp) + 160),
        margin=dict(l=90,r=30,t=70,b=30),
        showlegend=False, title_x=0.5
    )
    fig.update_yaxes(automargin=True, title="")
    fig.update_xaxes(automargin=True, title="objective_loss_score")
    return fig

def plot_team_score_trend(df):
    temp = df.groupby("Fecha").agg(
        objective_loss_score=("objective_loss_score", "mean"),
        readiness_score=("readiness_score", "mean"),
        objective_z_score=("objective_z_score", "mean"),
    ).reset_index().sort_values("Fecha")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=temp["Fecha"],
            y=temp["objective_loss_score"],
            mode="lines+markers",
            name="Loss equipo",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=temp["Fecha"],
            y=temp["readiness_score"],
            mode="lines+markers",
            name="Readiness equipo",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Evolución global del grupo",
        height=340,
        margin=dict(l=30, r=30, t=70, b=40),
        title_x=0.5,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_yaxes(title_text="Loss", secondary_y=False, automargin=True)
    fig.update_yaxes(title_text="Readiness", secondary_y=True, automargin=True)
    return fig


def plot_team_decision_matrix(team_day):
    temp = team_day[["Jugador", "objective_loss_score", "readiness_score", "decision_label"]].copy()
    fig = px.scatter(
        temp,
        x="objective_loss_score",
        y="readiness_score",
        color="decision_label",
        text="Jugador",
        color_discrete_map={
            "Disponible normal": "#15803D",
            "Disponible con control": "#65A30D",
            "Controlar carga": "#E3A008",
            "Ajustar carga": "#F97316",
            "Reducir exposición": "#EA580C",
            "Intervención individual": "#B91C1C",
        },
        title="Matriz staff: impacto vs disponibilidad",
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(height=420, margin=dict(l=30, r=30, t=70, b=40), title_x=0.5)
    fig.update_xaxes(title="Objective loss score")
    fig.update_yaxes(title="Readiness")
    return fig

def plot_percentile_bars(row):
    temp = pd.DataFrame({"Métrica":[LABELS[m] for m in OBJECTIVE_METRICS], "Percentil histórico":[row.get(f"{m}_historical_percentile", np.nan) for m in OBJECTIVE_METRICS]})
    fig = px.bar(temp, x="Métrica", y="Percentil histórico", text="Percentil histórico", title="Percentil histórico individual")
    fig.update_traces(texttemplate="%{text:.0f}")
    fig.update_layout(height=280, margin=dict(l=10,r=10,t=35,b=10), showlegend=False)
    return fig

def plot_rank_vs_team(row):
    temp = pd.DataFrame({
        "Métrica":[LABELS[m] for m in OBJECTIVE_METRICS] + ["Loss score","Readiness"],
        "Ranking sesión":[
            row.get("CMJ_team_rank", np.nan),
            row.get("RSI_mod_team_rank", np.nan),
            row.get("VMP_team_rank", np.nan),
            row.get("objective_loss_score_team_rank", np.nan),
            row.get("readiness_score_team_rank", np.nan)
        ]
    })
    fig = px.bar(temp, x="Métrica", y="Ranking sesión", text="Ranking sesión", title="Posición relativa en la sesión")
    fig.update_traces(texttemplate="%{text:.0f}")
    fig.update_layout(height=280, margin=dict(l=10,r=10,t=35,b=10), showlegend=False)
    return fig

def plotly_html(fig):
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False})

def fig_to_rl_image(fig, width_cm=16, height_cm=8.5):
    try:
        img_bytes = fig.to_image(format="png", scale=2)
        bio = io.BytesIO(img_bytes)
        return Image(bio, width=width_cm * cm, height=height_cm * cm)
    except Exception:
        return None

# =========================================================
# REPORT HTML / PDF
# =========================================================
def report_css():
    return """
    <style>
    body {font-family: Arial, sans-serif; margin: 24px; color: #111827; background: #F8FAFC;}
    .hero {background: linear-gradient(135deg, #0F172A 0%, #1F4E79 100%); color: white; border-radius: 20px; padding: 24px; margin-bottom: 16px;}
    .cards {display:grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 16px;}
    .card {background:#fff; border:1px solid #E5E7EB; border-radius:16px; padding:14px 16px;}
    .label {font-size:12px; color:#667085;}
    .value {font-size:26px; font-weight:800; color:#101828; margin-top:4px;}
    .section {background:#fff; border:1px solid #E5E7EB; border-radius:16px; padding:16px 18px; margin-bottom:14px;}
    .title {font-size:18px; font-weight:800; margin-bottom:10px; color:#101828;}
    .grid2 {display:grid; grid-template-columns:1fr 1fr; gap:14px;}
    .grid1 {display:grid; grid-template-columns:1fr; gap:14px;}
    .badge {display:inline-block; padding:6px 10px; border-radius:999px; color:#fff; font-weight:700; font-size:12px;}
    ul {margin:8px 0 0 18px;}
    table.report-table {width:100%; border-collapse:collapse; font-size:13px;}
    table.report-table th, table.report-table td {border-bottom:1px solid #E5E7EB; padding:8px 10px; text-align:left;}
    table.report-table th {background:#F8FAFC;}
    .diag {font-size:14px; line-height:1.5;}
    .loss-wrap {background:#E5E7EB;border-radius:999px;height:14px;overflow:hidden;min-width:140px;}
    .loss-bar {height:14px;border-radius:999px;}
    .muted {color:#667085;font-size:12px;}
    </style>
    """

def html_risk_badge(label):
    color = RISK_COLORS.get(label, "#475467")
    return f'<span class="badge" style="background:{color};">{label}</span>'

def html_loss_bar(score):
    if pd.isna(score):
        return '<span class="muted">NA</span>'
    color = "#16A34A"
    if score >= 2.5:
        color = "#B91C1C"
    elif score >= 1.5:
        color = "#F97316"
    elif score >= 0.5:
        color = "#E3A008"
    width = max(2, min(100, float(score) / 3 * 100))
    return f'<div class="loss-wrap"><div class="loss-bar" style="width:{width}%;background:{color};"></div></div><div class="muted" style="margin-top:4px;">{score:.2f}</div>'

def coach_session_html(team_day, selected_date, gps_df=None):
    rows = ""
    temp = team_day.copy().sort_values(["objective_loss_score","objective_loss_mean_pct"], ascending=[False, True])
    for _, r in temp.iterrows():
        rows += f"<tr><td>{r['Jugador']}</td><td>{html_risk_badge(r['risk_label'])}</td><td>{r['CMJ_pct_vs_baseline']:.1f}%</td><td>{r['RSI_mod_pct_vs_baseline']:.1f}%</td><td>{r['VMP_pct_vs_baseline']:.1f}%</td><td>{r['objective_loss_mean_pct']:.1f}%</td><td>{html_loss_bar(r['objective_loss_score'])}</td></tr>"
    bar_html = plotly_html(plot_team_objective_bar(team_day))
    risk_html = plotly_html(plot_team_risk_distribution(team_day))
    gps_html = ""
    if gps_df is not None:
        gdf = ensure_gps_datetime(gps_df)
        gd = gps_compute_compliance(gdf[(gdf["Fecha"].dt.strftime("%Y-%m-%d")==str(selected_date)) & (gdf["Microciclo"].astype(str).str.upper() != "PARTIDO")].copy(), reference_df=gdf)
        if not gd.empty:
            gps_html = plotly_html(plot_team_gps_support(gd))
    return f"""
    <html><head><meta charset="utf-8">{report_css()}</head><body>
    <div class="hero"><div style="font-size:12px;opacity:0.9;">Informe de sesión · MD-1</div><div style="font-size:32px;font-weight:900;line-height:1.15;">Estado neuromuscular del equipo</div><div style="font-size:15px;margin-top:6px;">Fecha analizada: {selected_date}</div></div>
    <div class="cards">
      <div class="card"><div class="label">Jugadores evaluados</div><div class="value">{team_day['Jugador'].nunique()}</div></div>
      <div class="card"><div class="label">Objective loss medio</div><div class="value">{team_day['objective_loss_score'].mean():.2f}</div></div>
      <div class="card"><div class="label">Pérdida media %</div><div class="value">{team_day['objective_loss_mean_pct'].mean():.1f}%</div></div>
      <div class="card"><div class="label">Readiness media</div><div class="value">{team_day['readiness_score'].mean():.0f}</div></div>
    </div>
    <div class="section"><div class="title">Lectura rápida para el entrenador</div><div class="diag">{team_interpretation(team_day)}</div><p class="diag" style="margin-top:8px;"><b>Resumen pre-entrenamiento:</b> {pretraining_text(team_day)}</p><p class="diag" style="margin-top:8px;"><b>Control semanal integrado:</b> {integrated_week_text(globals().get('LAST_METRICS_DF', pd.DataFrame()), globals().get('LAST_GPS_DF', pd.DataFrame()), selected_date)}</p></div>
    <div class="section"><div class="title">Panel visual</div><div class="grid2">{risk_html}{bar_html}</div></div>
    <div class="section"><div class="title">GPS de la sesión</div><div class="grid1">{gps_html}</div></div>
    <div class="section"><div class="title">Resumen por jugador</div><table class="report-table"><thead><tr><th>Jugador</th><th>Riesgo</th><th>CMJ %</th><th>RSI mod %</th><th>VMP %</th><th>Pérdida media %</th><th>Loss score</th></tr></thead><tbody>{rows}</tbody></table></div>
    </body></html>
    """

def player_session_html(row, player_df, session_df, gps_df=None):
    main, pattern, worst_metric, worst_value = infer_fatigue_profile(row)
    flags = flags_for_player(player_df, row)
    flags_html = "".join([f"<li>{f}</li>" for f in flags]) if flags else "<li>Sin flags adicionales</li>"

    rows = ""
    for m in OBJECTIVE_METRICS:
        z_val = row.get(f"{m}_z", np.nan)
        perc_val = row.get(f"{m}_historical_percentile", np.nan)
        z_txt = "NA" if pd.isna(z_val) else f"{z_val:.2f}"
        perc_txt = "NA" if pd.isna(perc_val) else f"{perc_val:.0f}"
        rows += f"<tr><td>{LABELS[m]}</td><td>{row.get(m, np.nan):.2f}</td><td>{row.get(f'{m}_baseline', np.nan):.2f}</td><td>{row.get(f'{m}_pct_vs_baseline', np.nan):.1f}%</td><td>{z_txt}</td><td>{row.get(f'{m}_severity', 'Sin referencia')}</td><td>{perc_txt}</td></tr>"

    rank_rows = ""
    for m in OBJECTIVE_METRICS:
        rk = row.get(f"{m}_team_rank", np.nan)
        rk_txt = "NA" if pd.isna(rk) else f"{rk:.0f}"
        rank_rows += f"<tr><td>{LABELS[m]}</td><td>{rk_txt}</td><td>{row.get(f'{m}_vs_team_pct', np.nan):.1f}%</td></tr>"

    radar_html = plotly_html(radar_current_vs_baseline(row))
    snapshot_html = plotly_html(radar_relative_loss(row))
    timeline_html = plotly_html(plot_objective_timeline(player_df, row['Fecha']))
    gps_block = gps_player_report_html(row["Jugador"], gps_df, row["Fecha"]) if gps_df is not None else ""
    return f"""
    <html><head><meta charset="utf-8">{report_css()}</head><body>
    <div class="hero"><div style="font-size:12px;opacity:0.9;">Informe individual · Sesión específica</div><div style="font-size:32px;font-weight:900;line-height:1.15;">{row['Jugador']}</div><div style="font-size:15px;margin-top:6px;">Fecha: {pd.to_datetime(row['Fecha']).date()}</div></div>
    <div class="cards">
      <div class="card"><div class="label">Riesgo</div><div class="value" style="font-size:22px;">{row['risk_label']}</div></div>
      <div class="card"><div class="label">Loss score</div><div class="value">{row['objective_loss_score']:.2f}</div></div>
      <div class="card"><div class="label">Pérdida media %</div><div class="value">{row['objective_loss_mean_pct']:.1f}%</div></div>
      <div class="card"><div class="label">Readiness</div><div class="value">{row['readiness_score']:.0f}</div></div>
      <div class="card"><div class="label">Decisión</div><div class="value" style="font-size:20px;">{row['decision_icon']} {row['decision_label']}</div></div>
    </div>
    <div class="section"><div class="title">Diagnóstico staff</div><div class="diag"><p><b>Perfil principal:</b> {main}.</p><p><b>Patrón:</b> {pattern}.</p><p><b>Variable dominante:</b> {LABELS.get(worst_metric, 'NA')} ({'NA' if worst_value is None else f'{worst_value:.1f}%'}).</p><p><b>Decisión integrada:</b> {compute_integrated_player_snapshot(row["Jugador"], row["Fecha"], globals().get("LAST_METRICS_DF", pd.DataFrame()), globals().get("LAST_GPS_DF", pd.DataFrame()))["integrated_decision"]}.</p><p>{player_comment(row)}</p></div></div>
    <div class="section"><div class="title">Flags automáticos</div><ul>{flags_html}</ul></div>
    <div class="section"><div class="title">Panel visual</div><div class="grid2">{radar_html}{snapshot_html}</div><div class="grid1">{timeline_html}</div></div>
    {gps_block}
    <div class="section"><div class="title">Detalle por variable</div><table class="report-table"><thead><tr><th>Métrica</th><th>Valor</th><th>Línea base</th><th>% vs baseline</th><th>Z-score</th><th>Estado</th><th>Percentil histórico</th></tr></thead><tbody>{rows}</tbody></table></div>
    <div class="section"><div class="title">Comparación vs equipo en la sesión</div><table class="report-table"><thead><tr><th>Métrica</th><th>Ranking sesión</th><th>% vs equipo</th></tr></thead><tbody>{rank_rows}</tbody></table></div>
    </body></html>
    """

def player_season_html(player_df, player, gps_df=None):
    latest = player_df.iloc[-1]
    main, pattern, worst_metric, worst_value = infer_fatigue_profile(latest)
    flags = flags_for_player(player_df, latest)
    flags_html = "".join([f"<li>{f}</li>" for f in flags]) if flags else "<li>Sin flags adicionales</li>"
    summary = player_df[["Fecha","objective_loss_score","objective_loss_mean_pct","readiness_score","risk_label","trend_label"]].copy()
    summary["Fecha"] = summary["Fecha"].dt.strftime("%Y-%m-%d")
    rows = ""
    for _, r in summary.iterrows():
        rows += f"<tr><td>{r['Fecha']}</td><td>{r['objective_loss_score']:.2f}</td><td>{r['objective_loss_mean_pct']:.1f}%</td><td>{r['readiness_score']:.0f}</td><td>{r['risk_label']}</td><td>{r['trend_label']}</td></tr>"

    radar_html = plotly_html(radar_current_vs_baseline(latest))
    timeline_html = plotly_html(radar_relative_loss(latest))
    cmj_html = plotly_html(plot_metric_pct(player_df, "CMJ", latest["Fecha"]))
    rsi_html = plotly_html(plot_metric_pct(player_df, "RSI_mod", latest["Fecha"]))
    vmp_html = plotly_html(plot_metric_pct(player_df, "VMP", latest["Fecha"]))

    return f"""
    <html><head><meta charset="utf-8">{report_css()}</head><body>
    <div class="hero"><div style="font-size:12px;opacity:0.9;">Informe individual · Evolución anual</div><div style="font-size:32px;font-weight:900;line-height:1.15;">{player}</div><div style="font-size:15px;margin-top:6px;">Registros: {len(player_df)} · Última fecha: {pd.to_datetime(latest['Fecha']).date()}</div></div>
    <div class="cards">
      <div class="card"><div class="label">Riesgo actual</div><div class="value" style="font-size:22px;">{latest['risk_label']}</div></div>
      <div class="card"><div class="label">Loss score actual</div><div class="value">{latest['objective_loss_score']:.2f}</div></div>
      <div class="card"><div class="label">Readiness actual</div><div class="value">{latest['readiness_score']:.0f}</div></div>
      <div class="card"><div class="label">Tendencia actual</div><div class="value" style="font-size:22px;">{latest['trend_label']}</div></div>
      <div class="card"><div class="label">Decisión actual</div><div class="value" style="font-size:20px;">{latest['decision_icon']} {latest['decision_label']}</div></div>
    </div>
    <div class="section"><div class="title">Diagnóstico longitudinal</div><div class="diag"><p><b>Perfil principal actual:</b> {main}.</p><p><b>Patrón:</b> {pattern}.</p><p><b>Variable dominante:</b> {LABELS.get(worst_metric, 'NA')} ({'NA' if worst_value is None else f'{worst_value:.1f}%'}).</p><p><b>Contexto:</b> {latest_context_summary(player, latest["Fecha"], globals().get("LAST_GPS_DF", pd.DataFrame()))}.</p><p>{player_comment(latest)}</p></div></div>
    <div class="section"><div class="title">Flags actuales</div><ul>{flags_html}</ul></div>
    <div class="section"><div class="title">Panel visual</div><div class="grid2">{radar_html}{timeline_html}</div><div class="grid2">{cmj_html}{rsi_html}</div><div class="grid1">{vmp_html}</div></div>
    <div class="section"><div class="title">Resumen longitudinal</div><table class="report-table"><thead><tr><th>Fecha</th><th>Loss</th><th>Pérdida %</th><th>Readiness</th><th>Riesgo</th><th>Tendencia</th></tr></thead><tbody>{rows}</tbody></table></div>
    </body></html>
    """

def report_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallGrey", fontSize=9, textColor=colors.HexColor("#667085"), leading=11))
    styles.add(ParagraphStyle(name="TitleDark", fontSize=18, textColor=colors.HexColor("#0F172A"), leading=22, spaceAfter=8))
    styles.add(ParagraphStyle(name="SectionDark", fontSize=13, textColor=colors.HexColor("#0F172A"), leading=16, spaceAfter=6))
    return styles

def build_pdf_bytes_player_session(row, player_df, gps_df=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = []
    main, pattern, worst_metric, worst_value = infer_fatigue_profile(row)
    flags = flags_for_player(player_df, row)
    elems.append(Paragraph(f"Informe individual · {row['Jugador']}", styles["TitleDark"]))
    elems.append(Paragraph(f"Sesión: {pd.to_datetime(row['Fecha']).date()}", styles["SmallGrey"]))
    elems.append(Spacer(1, 0.2*cm))
    elems.append(Paragraph(player_comment(row), styles["BodyText"]))
    elems.append(Spacer(1, 0.25*cm))
    diag = [
        ["Riesgo", str(row["risk_label"]), "Readiness", f"{row['readiness_score']:.0f}"],
        ["Decisión", f"{row['decision_icon']} {row['decision_label']}", "Disponibilidad", str(row["availability_label"])],
        ["Loss score", f"{row['objective_loss_score']:.2f}", "Pérdida media %", f"{row['objective_loss_mean_pct']:.1f}%"],
        ["Z-score objetivo", "NA" if pd.isna(row["objective_z_score"]) else f"{row['objective_z_score']:.2f}", "Tendencia", str(row["trend_label"])],
        ["Perfil", main, "Patrón", pattern],
        ["Variable dominante", f"{LABELS.get(worst_metric, 'NA')} ({'NA' if worst_value is None else f'{worst_value:.1f}%'})", "", ""],
    ]
    t = Table(diag, colWidths=[3.4*cm, 5.0*cm, 3.4*cm, 5.0*cm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.whitesmoke),("GRID",(0,0),(-1,-1),0.3,colors.lightgrey),("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold")]))
    elems.append(t)
    elems.append(Spacer(1, 0.25*cm))
    elems.append(Paragraph("Flags automáticos", styles["SectionDark"]))
    for f in (flags or ["Sin flags adicionales"]):
        elems.append(Paragraph(f"• {f}", styles["BodyText"]))
    elems.append(Spacer(1, 0.2*cm))
    for fig in [radar_current_vs_baseline(row), radar_relative_loss(row)]:
        rl_img = fig_to_rl_image(fig, width_cm=11.8, height_cm=6.8)
        if rl_img is not None:
            elems.append(rl_img)
    rl_img = fig_to_rl_image(plot_objective_timeline(player_df, row["Fecha"]), width_cm=24.0, height_cm=7.2)
    if rl_img is not None:
        elems.append(Spacer(1, 0.2*cm))
        elems.append(rl_img)
        elems.append(Spacer(1, 0.2*cm))
    if gps_df is not None:
        elems.extend(gps_weekly_pdf_story(row["Jugador"], gps_df, row["Fecha"], styles))
    data = [["Métrica","Valor","Baseline","% vs baseline","Z-score","Estado"]]
    for m in OBJECTIVE_METRICS:
        z_val = row.get(f"{m}_z", np.nan)
        z_txt = "NA" if pd.isna(z_val) else f"{z_val:.2f}"
        data.append([LABELS[m], f"{row.get(m, np.nan):.2f}", f"{row.get(f'{m}_baseline', np.nan):.2f}", f"{row.get(f'{m}_pct_vs_baseline', np.nan):.1f}%", z_txt, str(row.get(f"{m}_severity", "Sin referencia"))])
    t2 = Table(data, repeatRows=1)
    t2.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F172A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.3,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),8.4)]))
    elems.append(t2)
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

def build_pdf_bytes_player_season(player_df, player, gps_df=None):
    latest = player_df.iloc[-1]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = []
    main, pattern, worst_metric, worst_value = infer_fatigue_profile(latest)
    flags = flags_for_player(player_df, latest)
    elems.append(Paragraph(f"Informe anual · {player}", styles["TitleDark"]))
    elems.append(Paragraph(f"Registros: {len(player_df)} · Última fecha: {pd.to_datetime(latest['Fecha']).date()}", styles["SmallGrey"]))
    elems.append(Spacer(1, 0.2*cm))
    diag = [
        ["Riesgo actual", str(latest["risk_label"]), "Readiness", f"{latest['readiness_score']:.0f}"],
        ["Decisión", f"{latest['decision_icon']} {latest['decision_label']}", "Disponibilidad", str(latest["availability_label"])],
        ["Loss score", f"{latest['objective_loss_score']:.2f}", "Pérdida media %", f"{latest['objective_loss_mean_pct']:.1f}%"],
        ["Z-score objetivo", "NA" if pd.isna(latest["objective_z_score"]) else f"{latest['objective_z_score']:.2f}", "Tendencia", str(latest["trend_label"])],
        ["Perfil", main, "Patrón", pattern],
        ["Variable dominante", f"{LABELS.get(worst_metric, 'NA')} ({'NA' if worst_value is None else f'{worst_value:.1f}%'})", "", ""],
    ]
    t = Table(diag, colWidths=[3.4*cm, 5.0*cm, 3.4*cm, 5.0*cm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.whitesmoke),("GRID",(0,0),(-1,-1),0.3,colors.lightgrey),("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold")]))
    elems.append(t)
    elems.append(Spacer(1, 0.2*cm))
    for f in (flags or ["Sin flags adicionales"]):
        elems.append(Paragraph(f"• {f}", styles["BodyText"]))
    elems.append(Spacer(1, 0.2*cm))
    for fig in [radar_current_vs_baseline(latest), radar_relative_loss(latest), plot_metric_pct(player_df, "CMJ", latest["Fecha"]), plot_metric_pct(player_df, "RSI_mod", latest["Fecha"]), plot_metric_pct(player_df, "VMP", latest["Fecha"])]:
        rl_img = fig_to_rl_image(fig, width_cm=11.8, height_cm=6.5)
        if rl_img is not None:
            elems.append(rl_img)
            elems.append(Spacer(1, 0.12*cm))
    if gps_df is not None:
        elems.extend(gps_weekly_pdf_story(player, gps_df, latest["Fecha"], styles))
    data = [["Fecha","Loss","Pérdida %","Readiness","Riesgo","Tendencia"]]
    temp = player_df[["Fecha","objective_loss_score","objective_loss_mean_pct","readiness_score","risk_label","trend_label"]].copy()
    temp["Fecha"] = temp["Fecha"].dt.strftime("%Y-%m-%d")
    for _, r in temp.iterrows():
        data.append([str(r["Fecha"]), f"{r['objective_loss_score']:.2f}", f"{r['objective_loss_mean_pct']:.1f}%", f"{r['readiness_score']:.0f}", str(r["risk_label"]), str(r["trend_label"])])
    t2 = Table(data, repeatRows=1)
    t2.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F172A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.3,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),8.2)]))
    elems.append(t2)
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

def build_pdf_bytes_team_session(team_day, selected_date, gps_df=None):
    gps_df = ensure_gps_datetime(gps_df)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = []
    elems.append(Paragraph("Informe de sesión · MD-1", styles["TitleDark"]))
    elems.append(Paragraph(f"Fecha analizada: {selected_date}", styles["SmallGrey"]))
    elems.append(Spacer(1, 0.2*cm))
    elems.append(Paragraph(team_interpretation(team_day), styles["BodyText"]))
    elems.append(Spacer(1, 0.1*cm))
    elems.append(Paragraph("Resumen pre-entrenamiento: " + pretraining_text(team_day), styles["BodyText"]))
    elems.append(Spacer(1, 0.2*cm))
    for fig in [plot_team_risk_distribution(team_day), plot_team_objective_bar(team_day)]:
        rl_img = fig_to_rl_image(fig, width_cm=12.0, height_cm=7.0)
        if rl_img is not None:
            elems.append(rl_img)
            elems.append(Spacer(1, 0.15*cm))
    if gps_df is not None:
        gps_day = gps_compute_compliance(ensure_gps_datetime(gps_df)[(ensure_gps_datetime(gps_df)["Fecha"].dt.strftime("%Y-%m-%d") == str(selected_date)) & (ensure_gps_datetime(gps_df)["Microciclo"].astype(str).str.upper() != "PARTIDO")].copy(), reference_df=ensure_gps_datetime(gps_df))
        if not gps_day.empty:
            elems.append(Paragraph("GPS de la sesión", styles["SectionDark"]))
            gdata = [["Jugador","Día","HSR %","Sprint %","Dist sprint %","ACC %","DEC %"]]
            for _, rg in gps_day.iterrows():
                gdata.append([str(rg["Jugador"]), str(rg["Microciclo"]), f"{rg.get('hsr_pct_match', np.nan):.1f}%", f"{rg.get('sprints_pct_match', np.nan):.1f}%", f"{rg.get('distance_vrange6_pct_match', np.nan):.1f}%", f"{rg.get('num_acc_pct_match', np.nan):.1f}%", f"{rg.get('num_dec_pct_match', np.nan):.1f}%"])
            gt = Table(gdata, repeatRows=1)
            gt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F172A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),8.0)]))
            elems.append(gt); elems.append(Spacer(1,0.15*cm))
    data = [["Jugador","Riesgo","CMJ %","RSI %","VMP %","Pérdida %","Loss score"]]
    temp = team_day.copy().sort_values(["objective_loss_score","objective_loss_mean_pct"], ascending=[False, True])
    for _, r in temp.iterrows():
        data.append([str(r["Jugador"]), str(r["risk_label"]), f"{r['CMJ_pct_vs_baseline']:.1f}%", f"{r['RSI_mod_pct_vs_baseline']:.1f}%", f"{r['VMP_pct_vs_baseline']:.1f}%", f"{r['objective_loss_mean_pct']:.1f}%", f"{r['objective_loss_score']:.2f}"])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F172A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.3,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),8.2)]))
    elems.append(t)
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

# =========================================================
# PAGES
# =========================================================
def page_cargar():
    st.markdown("### Carga de datos")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### CONTROL DE FATIGA")
        fat_fecha = st.date_input("Fecha control de fatiga", value=pd.Timestamp.today(), key="fat_fecha")
        fat_micro = st.selectbox("Día microciclo fatiga", ["MD+1","MD-4","MD-3","MD-2","MD-1","PARTIDO"], index=4, key="fat_micro")
        uploaded = st.file_uploader("Sube Excel/CSV de fatiga", type=["xlsx","xls","csv"], key="fatigue_upload")
        if uploaded is not None:
            try:
                parsed = parse_uploaded(uploaded)
                parsed["Fecha"] = pd.to_datetime(fat_fecha)
                parsed["Microciclo"] = fat_micro
                st.success(f"Archivo interpretado correctamente: {parsed['Jugador'].nunique()} jugadores · {parsed['Fecha'].nunique()} fecha(s)")
                cols_show = [c for c in ["Fecha","Microciclo","Jugador","Posicion","CMJ","RSI_mod","VMP","sRPE","Observaciones"] if c in parsed.columns]
                st.dataframe(parsed[cols_show], use_container_width=True, hide_index=True)
                if st.button("Guardar control de fatiga", type="primary"):
                    upsert_monitoring(parsed)
                    st.success("Datos de fatiga guardados correctamente.")
                    st.rerun()
            except Exception as e:
                st.error(f"No se pudo interpretar el archivo de fatiga: {e}")
    with c2:
        st.markdown("#### SESIÓN GPS")
        gps_fecha = st.date_input("Fecha GPS", value=pd.Timestamp.today(), key="gps_fecha")
        gps_micro = st.selectbox("Día microciclo GPS", ["PARTIDO","MD+1","MD-4","MD-3","MD-2","MD-1"], index=3, key="gps_micro")
        gps_uploaded = st.file_uploader("Sube CSV/Excel GPS", type=["xlsx","xls","csv"], key="gps_upload")
        if gps_uploaded is not None:
            try:
                parsed_gps = parse_gps_uploaded(gps_uploaded, gps_fecha, gps_micro)
                st.success(f"Archivo GPS interpretado: {parsed_gps['Jugador'].nunique()} jugadores")
                st.dataframe(parsed_gps[["Fecha","Microciclo","Jugador","Posicion",*GPS_METRICS]], use_container_width=True, hide_index=True)
                if st.button("Guardar sesión GPS"):
                    upsert_gps(parsed_gps)
                    st.success("Datos GPS guardados correctamente.")
                    st.rerun()
            except Exception as e:
                st.error(f"No se pudo interpretar el archivo GPS: {e}")

def page_equipo(metrics_df, gps_df):
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return

    st.markdown('<div class="hero"><div style="font-size:0.92rem; opacity:0.9;">Monitorización neuromuscular + GPS</div><div style="font-size:2.05rem; font-weight:900; margin-top:0.15rem;">Equipo</div><div style="font-size:1rem; opacity:0.92; margin-top:0.4rem;">Lectura integrada semanal y por sesión del grupo.</div></div>', unsafe_allow_html=True)

    week_labels, week_map = build_week_options(metrics_df, gps_df)
    if not week_labels:
        st.info("No hay semanas disponibles.")
        return
    wk_label = st.selectbox("Semana (lunes-domingo)", week_labels, index=len(week_labels)-1)
    week_ws = week_map[wk_label]
    view_mode = st.radio("Vista", ["Resumen semanal","Sesión concreta"], horizontal=True)

    gps_df = ensure_gps_datetime(gps_df)
    week_we = week_ws + pd.Timedelta(days=6)
    week_fat = metrics_df[(metrics_df["Fecha"] >= week_ws) & (metrics_df["Fecha"] <= week_we)].copy() if not metrics_df.empty else pd.DataFrame()
    week_gps_raw = gps_df[(gps_df["Fecha"] >= week_ws) & (gps_df["Fecha"] <= week_we) & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")].copy() if not gps_df.empty else pd.DataFrame()
    week_gps = gps_compute_compliance(week_gps_raw, reference_df=gps_df) if not week_gps_raw.empty else pd.DataFrame()

    if view_mode == "Resumen semanal":
        summary = weekly_global_summary(metrics_df, gps_df, week_ws)
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Sesiones fatiga", summary["fatigue_sessions"], "semana")
        with c2: kpi("Sesiones GPS", summary["gps_sessions"], "semana")
        with c3: kpi("Readiness media", "NA" if pd.isna(summary["readiness_mean"]) else f"{summary['readiness_mean']:.1f}", "semana")
        with c4: kpi("GPS semanal medio", "NA" if pd.isna(summary["gps_compliance_mean"]) else f"{summary['gps_compliance_mean']:.1f}%", "semana")
        st.info(integrated_week_text(metrics_df, gps_df, week_ws))
        if not week_fat.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_score_trend(week_fat), use_container_width=True)
            with b: st.plotly_chart(plot_team_risk_distribution(week_fat.groupby("Jugador", as_index=False).last()), use_container_width=True)
        if not week_gps.empty:
            st.plotly_chart(plot_team_gps_support(week_gps.groupby("Jugador", as_index=False).agg(compliance_score=("compliance_score","mean"), session_status=("session_status", lambda s: s.iloc[-1]))), use_container_width=True)
            gps_tbl = week_gps.groupby(["Jugador","Posicion"], as_index=False).agg(**{"GPS semanal %":("compliance_score","mean")})
            gps_tbl["GPS semanal %"] = gps_tbl["GPS semanal %"].round(1)
            st.dataframe(gps_tbl.sort_values("GPS semanal %", ascending=False), use_container_width=True, hide_index=True)
    else:
        sess_opts = session_options_for_week(metrics_df, gps_df, week_ws)
        if not sess_opts:
            st.info("No hay sesiones en esa semana.")
            return
        sess_label = st.selectbox("Sesión de la semana", sess_opts)
        sess_date_str, sess_md = [x.strip() for x in sess_label.split("|", 1)]
        selected_date = pd.to_datetime(sess_date_str)
        team_day = week_fat[(week_fat["Fecha"].dt.normalize() == selected_date.normalize()) & (week_fat["Microciclo"].fillna("Sin día").astype(str) == sess_md if sess_md != "Sin día" else week_fat["Fecha"].notna())].copy() if not week_fat.empty else pd.DataFrame()
        if sess_md == "Sin día" and not week_fat.empty:
            team_day = week_fat[week_fat["Fecha"].dt.normalize() == selected_date.normalize()].copy()
        gps_day = week_gps[(week_gps["Fecha"].dt.normalize() == selected_date.normalize()) & (week_gps["Microciclo"].astype(str) == sess_md)].copy() if not week_gps.empty else pd.DataFrame()

        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: kpi("Fecha", selected_date.strftime("%Y-%m-%d"), sess_md)
        with c2: kpi("Jugadores fatiga", int(team_day["Jugador"].nunique()) if not team_day.empty else 0, "sesión")
        with c3: kpi("Readiness media", "NA" if team_day.empty else f"{team_day['readiness_score'].mean():.1f}", "sesión")
        with c4: kpi("GPS medio", "NA" if gps_day.empty else f"{gps_day['compliance_score'].mean():.1f}%", "sesión")
        with c5: kpi("Críticos", int((team_day["risk_label"]=="Fatiga crítica").sum()) if not team_day.empty else 0, "sesión")

        if not team_day.empty:
            st.success(team_interpretation(team_day))
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_risk_distribution(team_day), use_container_width=True)
            with b: st.plotly_chart(plot_team_objective_bar(team_day), use_container_width=True)
            st.plotly_chart(plot_team_decision_matrix(team_day), use_container_width=True)

        if not gps_day.empty:
            st.markdown("### GPS del día")
            st.plotly_chart(plot_team_gps_support(gps_day), use_container_width=True)
            gps_show = gps_day[["Jugador","Posicion","Microciclo","compliance_score","session_status","hsr_pct_match","sprints_pct_match","distance_vrange6_pct_match","num_acc_pct_match","num_dec_pct_match"]].copy()
            gps_show.columns = ["Jugador","Posición","Día","Cumplimiento %","Estado","HSR %","Sprints %","Distancia sprint %","ACC %","DEC %"]
            for c in ["Cumplimiento %","HSR %","Sprints %","Distancia sprint %","ACC %","DEC %"]:
                gps_show[c] = pd.to_numeric(gps_show[c], errors="coerce").round(1)
            st.dataframe(gps_show.sort_values(["Cumplimiento %"], ascending=False, na_position="last"), use_container_width=True, hide_index=True)

def page_jugador(metrics_df, gps_df):
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return
    gps_df = ensure_gps_datetime(gps_df)
    st.markdown('<div class="section-title">Jugador</div>', unsafe_allow_html=True)

    player_map = build_player_display_options(metrics_df, gps_df)
    player_label = st.selectbox("Selecciona jugador", list(player_map.keys()))
    player = player_map[player_label]

    week_labels, week_map = build_week_options(metrics_df, gps_df, player=player)
    if not week_labels:
        st.info("No hay semanas disponibles para este jugador.")
        return
    wk_label = st.selectbox("Semana (lunes-domingo)", week_labels, index=len(week_labels)-1)
    week_ws = week_map[wk_label]
    view_mode = st.radio("Vista", ["Resumen semanal","Sesión concreta"], horizontal=True, key="player_view")

    player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame()
    player_gps = gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame()
    week_we = week_ws + pd.Timedelta(days=6)
    player_week_fat = player_df[(player_df["Fecha"] >= week_ws) & (player_df["Fecha"] <= week_we)].copy() if not player_df.empty else pd.DataFrame()
    player_week_gps_raw = player_gps[(player_gps["Fecha"] >= week_ws) & (player_gps["Fecha"] <= week_we) & (player_gps["Microciclo"].astype(str).str.upper() != "PARTIDO")].copy() if not player_gps.empty else pd.DataFrame()
    player_week_gps = gps_compute_compliance(player_week_gps_raw, reference_df=gps_df) if not player_week_gps_raw.empty else pd.DataFrame()

    if view_mode == "Resumen semanal":
        snap = compute_integrated_player_snapshot(player, week_ws, metrics_df, gps_df)
        st.markdown(f'<div class="card"><div style="font-size:1.7rem; font-weight:900; color:#101828;">{player_label}</div><div style="margin-top:0.55rem;"><span class="pill" style="background:#0F766E;">{snap["integrated_icon"]} {snap["integrated_decision"]}</span></div><div style="margin-top:0.7rem; color:#475467;">{snap["load_response_label"]}</div></div>', unsafe_allow_html=True)
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Controles fatiga", int(player_week_fat[["Fecha","Microciclo"]].drop_duplicates().shape[0]) if not player_week_fat.empty else 0, "semana")
        with c2: kpi("Readiness sem.", "NA" if player_week_fat.empty else f"{player_week_fat['readiness_score'].mean():.1f}", "media")
        with c3: kpi("GPS sem.", "NA" if player_week_gps.empty else f"{player_week_gps['compliance_score'].mean():.1f}%", "media")
        with c4: kpi("Carga-respuesta", snap["load_response_label"], "semana")
        st.plotly_chart(plot_player_integrated_week_dashboard(player, week_ws, metrics_df, gps_df), use_container_width=True)
        if not player_week_gps.empty:
            a,b = st.columns(2)
            with a:
                gps_progress_bars_streamlit(gps_player_week_table(gps_df, player, week_ws), "Cumplimiento GPS semanal")
            with b:
                st.plotly_chart(plot_player_gps_support(gps_player_week_table(gps_df, player, week_ws), "Apoyo visual GPS semanal"), use_container_width=True)
        dist = player_distribution_summary(player_df) if not player_df.empty else {}
        if dist:
            d1,d2,d3,d4 = st.columns(4)
            with d1: kpi("% óptimo", f"{dist.get('Estado óptimo',0):.1f}%", "temporada")
            with d2: kpi("% leve", f"{dist.get('Fatiga leve',0)+dist.get('Fatiga leve-moderada',0):.1f}%", "temporada")
            with d3: kpi("% moderada", f"{dist.get('Fatiga moderada',0)+dist.get('Fatiga moderada-alta',0):.1f}%", "temporada")
            with d4: kpi("% crítica", f"{dist.get('Fatiga crítica',0):.1f}%", "temporada")
    else:
        sess_opts = session_options_for_week(metrics_df, gps_df, week_ws, player=player)
        if not sess_opts:
            st.info("No hay sesiones en esa semana.")
            return
        sess_label = st.selectbox("Sesión de la semana", sess_opts, key="player_sess")
        sess_date_str, sess_md = [x.strip() for x in sess_label.split("|", 1)]
        selected_date = pd.to_datetime(sess_date_str)
        current = player_df[player_df["Fecha"].dt.normalize() == selected_date.normalize()] if not player_df.empty else pd.DataFrame()
        row = current.iloc[-1] if not current.empty else (player_df.iloc[-1] if not player_df.empty else None)
        snap = compute_integrated_player_snapshot(player, selected_date, metrics_df, gps_df)
        i_alerts = integrated_alerts_for_player(player, selected_date, metrics_df, gps_df)

        if row is not None:
            risk_color = RISK_COLORS.get(row["risk_label"], "#475467")
            st.markdown(f'<div class="card"><div style="font-size:1.7rem; font-weight:900; color:#101828;">{player_label}</div><div style="margin-top:0.35rem;">{render_pills(row)}</div><div style="margin-top:0.55rem;"><span class="pill" style="background:{risk_color};">{row["risk_label"]}</span><span class="pill" style="background:#0F766E;">{snap["integrated_icon"]} {snap["integrated_decision"]}</span></div><div style="margin-top:0.7rem; color:#475467;">{player_comment(row)}</div></div>', unsafe_allow_html=True)
            main, pattern, worst_metric, worst_value = infer_fatigue_profile(row)
            flags = flags_for_player(player_df, row)
            all_flags = flags + i_alerts
            if all_flags: st.warning(" | ".join(all_flags))
            st.markdown(f"**Diagnóstico:** {main}, con {pattern}. Variable dominante: {LABELS.get(worst_metric, 'NA')} ({'NA' if worst_value is None else f'{worst_value:.1f}%'}). **Decisión operativa:** {row['decision_label']} ({row['availability_label']}). **Integrada:** {snap['integrated_decision']}. **Estabilidad:** {row['objective_cv_label']}. **Contexto:** {snap['context_label']}.")
            c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)
            with c1: kpi("Fecha", selected_date.strftime("%Y-%m-%d"), sess_md)
            with c2: kpi("Loss score", f"{row['objective_loss_score']:.2f}", "0-3")
            with c3: kpi("Pérdida media %", f"{row['objective_loss_mean_pct']:.1f}%", "CMJ + RSI + VMP")
            with c4: kpi("Readiness", f"{row['readiness_score']:.0f}", "ese mismo día")
            with c5: kpi("Riesgo", row["risk_label"], "clasificación")
            with c6: kpi("Decisión", f"{row['decision_icon']} {row['decision_label']}", row["availability_label"])
            with c7: kpi("Integrada", f"{snap['integrated_icon']} {snap['integrated_decision']}", snap["load_response_label"])
            with c8: kpi("Alertas sem.", int(snap["weekly_alerts"]), snap["context_label"])

            a,b = st.columns(2)
            with a: st.plotly_chart(radar_relative_loss(row), use_container_width=True)
            with b: st.plotly_chart(radar_current_vs_baseline(row), use_container_width=True)
            c,d = st.columns(2)
            with c: st.plotly_chart(plot_player_snapshot_compare(row), use_container_width=True)
            with d: st.plotly_chart(plot_objective_timeline(player_df, selected_date), use_container_width=True)

            st.markdown("### Gráficas principales por variable")
            for m in OBJECTIVE_METRICS:
                l, rcol = st.columns(2)
                with l: st.plotly_chart(plot_metric_main(player_df, m, selected_date), use_container_width=True)
                with rcol: st.plotly_chart(plot_metric_pct(player_df, m, selected_date), use_container_width=True)

        if not player_gps.empty:
            st.markdown("## Carga GPS")
            session_gps = gps_player_session_table(gps_df, player, selected_date, micro=sess_md)
            gps_progress_bars_streamlit(session_gps, "Cumplimiento GPS del día")
            st.plotly_chart(plot_player_gps_support(session_gps, "Apoyo visual GPS del día"), use_container_width=True)
            if not session_gps.empty:
                sess_tbl = session_gps[["Variable","pct","min","max","status"]].copy()
                sess_tbl.columns = ["Variable","% sesión vs partido","Objetivo mínimo (%)","Objetivo máximo (%)","Estado"]
                st.dataframe(sess_tbl.round(1), use_container_width=True, hide_index=True)

def page_comparador(metrics_df):
    if metrics_df.empty:
        st.info("No hay datos disponibles.")
        return
    players = sorted(metrics_df["Jugador"].dropna().unique().tolist())
    c1,c2 = st.columns(2)
    with c1: p1 = st.selectbox("Jugador A", players, index=0)
    with c2: p2 = st.selectbox("Jugador B", players, index=min(1, len(players)-1))
    if p1 == p2:
        st.warning("Selecciona dos jugadores distintos.")
        return
    metric = st.selectbox("Métrica", OBJECTIVE_METRICS, format_func=lambda x: LABELS[x])
    a = metrics_df[metrics_df["Jugador"] == p1].sort_values("Fecha")
    b = metrics_df[metrics_df["Jugador"] == p2].sort_values("Fecha")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=a["Fecha"], y=a[f"{metric}_pct_vs_baseline"], mode="lines+markers", name=p1))
    fig.add_trace(go.Scatter(x=b["Fecha"], y=b[f"{metric}_pct_vs_baseline"], mode="lines+markers", name=p2))
    fig.add_hline(y=-2.5, line_dash="dot"); fig.add_hline(y=-5, line_dash="dot"); fig.add_hline(y=-10, line_dash="dot")
    fig.update_layout(title=f"Comparación · {LABELS[metric]} (% vs línea base)", height=360)
    st.plotly_chart(fig, use_container_width=True)

def page_informes(metrics_df, gps_df):
    gps_df = ensure_gps_datetime(gps_df)
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return
    st.markdown('<div class="section-title">Informes descargables</div>', unsafe_allow_html=True)
    tab1,tab2,tab3,tab4,tab5 = st.tabs(["Informe individual staff anual","Informe individual staff por sesión","Informe semanal integrado jugador","Informe entrenador sesión","Informe semanal global"])

    player_map = build_player_display_options(metrics_df, gps_df)

    with tab1:
        player_label = st.selectbox("Jugador · informe anual", list(player_map.keys()), key="yr")
        player = player_map[player_label]
        player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame(columns=["Fecha"])
        latest_date = player_df.iloc[-1]["Fecha"] if not player_df.empty else gps_df[gps_df["Jugador"]==player]["Fecha"].max()
        latest = player_df.iloc[-1] if not player_df.empty else None
        if latest is not None:
            st.markdown(f"**Resumen actual:** {latest['risk_label']} · loss {latest['objective_loss_score']:.2f} · readiness {latest['readiness_score']:.0f}")
        html = player_season_html(player_df, player, gps_df=gps_df) if not player_df.empty else f"<html><head><meta charset='utf-8'>{report_css()}</head><body>{gps_player_report_html(player, gps_df, latest_date)}</body></html>"
        st.download_button("Descargar HTML anual", data=html.encode("utf-8"), file_name=f"informe_anual_{player.replace(' ','_')}.html", mime="text/html")
        if not player_df.empty:
            st.download_button("Descargar PDF anual", data=build_pdf_bytes_player_season(player_df, player, gps_df=gps_df), file_name=f"informe_anual_{player.replace(' ','_')}.pdf", mime="application/pdf")

    with tab2:
        player_label = st.selectbox("Jugador · informe sesión", list(player_map.keys()), key="ses")
        player = player_map[player_label]
        source_dates = []
        if not metrics_df.empty:
            source_dates += [pd.to_datetime(d).strftime("%Y-%m-%d") for d in metrics_df[metrics_df["Jugador"] == player]["Fecha"].dropna().unique()]
        if not gps_df.empty:
            source_dates += [pd.to_datetime(d).strftime("%Y-%m-%d") for d in gps_df[gps_df["Jugador"] == player]["Fecha"].dropna().unique()]
        opts = sorted(set(source_dates))
        sel_date = st.selectbox("Fecha sesión", opts, key="sesd")
        player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame()
        session_df = player_df[player_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date].copy() if not player_df.empty else pd.DataFrame()
        gps_only_df = gps_df[(gps_df["Jugador"] == player) & (gps_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date)] if not gps_df.empty else pd.DataFrame()
        if not session_df.empty:
            row = session_df.iloc[-1]
            html = player_session_html(row, player_df, session_df, gps_df=gps_df)
            st.download_button("Descargar HTML sesión", data=html.encode("utf-8"), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.html", mime="text/html")
            st.download_button("Descargar PDF sesión", data=build_pdf_bytes_player_session(row, player_df, gps_df=gps_df), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.pdf", mime="application/pdf")
        elif not gps_only_df.empty:
            html = f"<html><head><meta charset='utf-8'>{report_css()}</head><body><div class='hero'><div style='font-size:12px;opacity:0.9;'>Informe individual · Sesión específica</div><div style='font-size:32px;font-weight:900;line-height:1.15;'>{player}</div><div style='font-size:15px;margin-top:6px;'>Fecha: {sel_date}</div></div><div class='section'><div class='title'>Observación</div><div class='diag'>No hay datos de control de fatiga para esta fecha. Se muestran únicamente los datos GPS disponibles.</div></div>{gps_player_report_html(player, gps_df, pd.to_datetime(sel_date))}</body></html>"
            st.download_button("Descargar HTML sesión", data=html.encode("utf-8"), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.html", mime="text/html")
            st.download_button("Descargar PDF sesión", data=build_pdf_bytes_player_session_gps_only(player, gps_df, pd.to_datetime(sel_date)), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.pdf", mime="application/pdf")
        else:
            st.warning("No hay datos para esa fecha.")

    with tab3:
        player_label = st.selectbox("Jugador · informe semanal", list(player_map.keys()), key="gpswk")
        player = player_map[player_label]
        week_labels, week_map = build_week_options(metrics_df, gps_df, player=player)
        if week_labels:
            wk_label = st.selectbox("Semana de referencia", week_labels, key="gpswkd")
            week_ws = week_map[wk_label]
            html = player_weekly_html(player, metrics_df[metrics_df["Jugador"] == player].copy() if not metrics_df.empty else pd.DataFrame(), gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame(), week_ws)
            st.download_button("Descargar HTML semanal", data=html.encode("utf-8"), file_name=f"informe_semanal_{player.replace(' ','_')}_{week_ws.strftime('%Y%m%d')}.html", mime="text/html")
            st.download_button("Descargar PDF semanal", data=build_pdf_bytes_player_weekly(player, metrics_df[metrics_df["Jugador"] == player].copy() if not metrics_df.empty else pd.DataFrame(), gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame(), week_ws), file_name=f"informe_semanal_{player.replace(' ','_')}_{week_ws.strftime('%Y%m%d')}.pdf", mime="application/pdf")
        else:
            st.info("No hay semanas disponibles.")

    with tab4:
        all_week_labels, all_week_map = build_week_options(metrics_df, gps_df)
        if all_week_labels:
            wk_label = st.selectbox("Semana sesión global", all_week_labels, key="teamwk")
            week_ws = all_week_map[wk_label]
            sess_opts = session_options_for_week(metrics_df, gps_df, week_ws)
            if sess_opts:
                sess_label = st.selectbox("Sesión global", sess_opts, key="teamr")
                sel_date, sel_md = [x.strip() for x in sess_label.split("|",1)]
                team_day = metrics_df[(metrics_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date) & (metrics_df["Microciclo"].fillna("Sin día").astype(str) == sel_md if sel_md != "Sin día" else metrics_df["Fecha"].notna())].copy() if not metrics_df.empty else pd.DataFrame()
                if sel_md == "Sin día" and not metrics_df.empty:
                    team_day = metrics_df[metrics_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date].copy()
                if not team_day.empty:
                    st.markdown(f"**Lectura rápida:** {team_interpretation(team_day)}")
                    html = coach_session_html(team_day, sel_date, gps_df=gps_df)
                    st.download_button("Descargar HTML entrenador", data=html.encode("utf-8"), file_name=f"informe_equipo_sesion_{sel_date}.html", mime="text/html")
                    st.download_button("Descargar PDF entrenador", data=build_pdf_bytes_team_session(team_day, sel_date, gps_df=gps_df), file_name=f"informe_equipo_sesion_{sel_date}.pdf", mime="application/pdf")
                else:
                    st.info("No hay datos para esa sesión.")
        else:
            st.info("No hay semanas disponibles.")

    with tab5:
        all_week_labels, all_week_map = build_week_options(metrics_df, gps_df)
        if all_week_labels:
            wk_label = st.selectbox("Semana informe global", all_week_labels, key="globalwk")
            week_ws = all_week_map[wk_label]
            html = weekly_global_html(metrics_df, gps_df, week_ws)
            st.download_button("Descargar HTML semanal global", data=html.encode("utf-8"), file_name=f"informe_global_semanal_{week_ws.strftime('%Y%m%d')}.html", mime="text/html")
            st.download_button("Descargar PDF semanal global", data=build_pdf_bytes_weekly_global(metrics_df, gps_df, week_ws), file_name=f"informe_global_semanal_{week_ws.strftime('%Y%m%d')}.pdf", mime="application/pdf")
        else:
            st.info("No hay semanas disponibles.")

def page_admin(base_df, gps_df):
    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi("Registros fatiga", len(base_df), "total")
    with c2: kpi("Jugadores fatiga", base_df["Jugador"].nunique() if not base_df.empty else 0, "únicos")
    with c3:
        gps_df = ensure_gps_datetime(gps_df)
        gps_micro = gps_df[gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO"].copy() if not gps_df.empty else pd.DataFrame()
        kpi("Sesiones GPS microciclo", len(gps_micro[["Fecha","Microciclo"]].drop_duplicates()) if not gps_micro.empty else 0, "guardadas")
    with c4:
        gps_matches = gps_df[gps_df["Microciclo"].astype(str).str.upper() == "PARTIDO"].copy() if not gps_df.empty else pd.DataFrame()
        kpi("Partidos GPS", len(gps_matches["Fecha"].drop_duplicates()) if not gps_matches.empty else 0, "guardados")

    if not base_df.empty:
        st.download_button("Descargar base fatiga CSV", data=base_df.to_csv(index=False).encode("utf-8"), file_name="fatiga.csv", mime="text/csv")
        st.markdown("### Eliminar sesiones de CONTROL DE FATIGA")
        fat_df = base_df.copy()
        fat_df["Fecha"] = pd.to_datetime(fat_df["Fecha"], errors="coerce")
        if "Microciclo" not in fat_df.columns:
            fat_df["Microciclo"] = np.nan
        fat_sessions = fat_df[["Fecha","Microciclo"]].drop_duplicates().sort_values(["Fecha","Microciclo"], na_position="last")
        fat_labels = []
        for _, r in fat_sessions.iterrows():
            d = pd.to_datetime(r["Fecha"]).strftime("%Y-%m-%d") if pd.notna(r["Fecha"]) else "Sin fecha"
            micro = "" if pd.isna(r["Microciclo"]) else str(r["Microciclo"])
            fat_labels.append(f"{d} | {micro if micro else 'Sin día'}")
        if fat_labels:
            fat_sel = st.selectbox("Selecciona la sesión de fatiga a eliminar", fat_labels)
            if st.button("Eliminar sesión de fatiga", type="secondary"):
                date_str, micro = [x.strip() for x in fat_sel.split("|", 1)]
                delete_fatigue_session(date_str, None if micro == "Sin día" else micro)
                st.success(f"Sesión de fatiga {fat_sel} eliminada correctamente.")
                st.rerun()

    if not gps_df.empty:
        st.download_button("Descargar base GPS CSV", data=gps_df.to_csv(index=False).encode("utf-8"), file_name="gps.csv", mime="text/csv")

        st.markdown("### Eliminar sesiones de SESIÓN GPS del microciclo")
        gps_micro = gps_df[gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO"].copy()
        if not gps_micro.empty:
            gps_sessions = gps_micro[["Fecha","Microciclo"]].drop_duplicates().sort_values(["Fecha","Microciclo"])
            gps_labels = [f"{pd.to_datetime(r.Fecha).strftime('%Y-%m-%d')} | {r.Microciclo}" for _, r in gps_sessions.iterrows()]
            sel = st.selectbox("Selecciona la sesión GPS del microciclo a eliminar", gps_labels)
            if st.button("Eliminar sesión GPS microciclo", type="secondary"):
                date_str, micro = [x.strip() for x in sel.split("|", 1)]
                delete_gps_session(date_str, micro)
                st.success(f"Sesión GPS {sel} eliminada correctamente.")
                st.rerun()

        st.markdown("### Eliminar PARTIDOS")
        gps_matches = gps_df[gps_df["Microciclo"].astype(str).str.upper() == "PARTIDO"].copy()
        if not gps_matches.empty:
            match_labels = [pd.to_datetime(d).strftime("%Y-%m-%d") for d in sorted(gps_matches["Fecha"].dropna().unique())]
            sel_match = st.selectbox("Selecciona el partido a eliminar", match_labels)
            if st.button("Eliminar partido", type="secondary"):
                delete_gps_match(sel_match)
                st.success(f"Partido {sel_match} eliminado correctamente.")
                st.rerun()

# =========================================================
# PROFESSIONAL V2 HELPERS / OVERRIDES
# =========================================================
def delete_gps_match(date_str):
    supabase = get_supabase()
    supabase.table(SUPABASE_GPS_TABLE).delete().eq("Fecha", date_str).eq("Microciclo", "PARTIDO").execute()

def line_group_from_position(pos):
    pos = str(pos) if pd.notna(pos) else "Sin asignar"
    if pos in ["Lateral", "Central"]:
        return "Defensas"
    if pos == "Mediocentro":
        return "Mediocentros"
    if pos == "Delantero":
        return "Atacantes"
    if pos == "Portero":
        return "Porteros"
    return "Sin asignar"

def gps_reference_info(gps_df, player):
    gps_df = ensure_gps_datetime(gps_df)
    info = {
        "source": "Sin referencia",
        "qualified_matches": 0,
        "required_matches": GPS_MATCH_MIN_MATCHES,
        "last_valid_match": pd.NaT,
        "position": get_player_position(player, None, gps_df),
    }
    if gps_df is None or gps_df.empty:
        return info
    prof = build_match_profile(gps_df)
    row = prof[prof["Jugador"] == player]
    if not row.empty:
        row = row.iloc[0]
        info["source"] = "perfil propio" if str(row.get("profile_source", "")).lower() == "propio" else f"media de {str(info['position']).lower()}"
        info["qualified_matches"] = int(row.get("qualified_matches", 0) if pd.notna(row.get("qualified_matches", 0)) else 0)
    valid_matches = gps_df[
        (gps_df["Jugador"] == player)
        & (gps_df["Microciclo"].astype(str).str.upper() == "PARTIDO")
        & (pd.to_numeric(gps_df.get("time_played", np.nan), errors="coerce") >= GPS_MATCH_MINUTES_MIN)
    ].copy()
    if not valid_matches.empty:
        info["last_valid_match"] = pd.to_datetime(valid_matches["Fecha"].max())
    return info

def build_upload_validation_report(df, mode="fatigue", gps_reference_df=None):
    if df is None or df.empty:
        return []
    lines = [
        f"Filas cargadas: {len(df)}",
        f"Jugadores detectados: {df['Jugador'].nunique() if 'Jugador' in df.columns else 0}",
    ]
    if "Posicion" in df.columns:
        sin_pos = int(((df["Posicion"].isna()) | (df["Posicion"].astype(str).str.strip().isin(["", "Sin asignar", "nan"]))).sum())
        lines.append(f"Registros sin posición: {sin_pos}")
    if all(c in df.columns for c in ["Fecha", "Jugador"]):
        duplicated = int(df.duplicated(subset=[c for c in ["Fecha", "Microciclo", "Jugador"] if c in df.columns]).sum())
        lines.append(f"Duplicados internos detectados: {duplicated}")
    if mode == "gps":
        src = df["source_type"].iloc[0] if "source_type" in df.columns and len(df) else "NA"
        lines.append(f"Tipo de carga: {src}")
        if gps_reference_df is not None:
            prof = build_match_profile(ensure_gps_datetime(gps_reference_df))
            if not prof.empty:
                prop = int((prof["profile_source"] == "propio").sum())
                pos = int((prof["profile_source"] != "propio").sum())
                lines.append(f"Referencias GPS disponibles: {len(prof)} perfiles ({prop} propios, {pos} por posición)")
    return lines

def professional_decision(player, selected_date, metrics_df, gps_df):
    selected_date = pd.to_datetime(selected_date)
    snap = compute_integrated_player_snapshot(player, selected_date, metrics_df, gps_df)
    ref = gps_reference_info(gps_df, player)
    reasons = []
    action = snap.get("integrated_decision", "Reevaluar")
    action_map = {
        "Intervención individual": "Individualizar",
        "Reducir exposición": "Reducir exposición",
        "Ajustar carga": "Ajustar carga",
        "Controlar carga": "Disponible con control",
        "Disponible con control": "Disponible con control",
        "Disponible normal": "Disponible normal",
        "Sin datos": "Reevaluar",
    }
    action = action_map.get(action, action)

    fat_row = None
    if metrics_df is not None and not metrics_df.empty:
        day = metrics_df[(metrics_df["Jugador"] == player) & (pd.to_datetime(metrics_df["Fecha"]).dt.normalize() == selected_date.normalize())]
        if not day.empty:
            fat_row = day.sort_values("Fecha").iloc[-1]
            risk = fat_row.get("risk_label", "Sin dato")
            readiness = fat_row.get("readiness_score", np.nan)
            if pd.notna(readiness) and readiness < 60:
                reasons.append(f"Readiness bajo ({readiness:.0f})")
            if risk in ["Fatiga moderada", "Fatiga moderada-alta", "Fatiga crítica"]:
                reasons.append(f"Riesgo {risk.lower()}")
            if fat_row.get("trend_label", "") == "Empeorando":
                reasons.append("Tendencia reciente negativa")
            if fat_row.get("recent_alerts_14d", 0) >= 2:
                reasons.append("Persistencia de alertas")
    if pd.notna(snap.get("gps_day_compliance", np.nan)):
        gd = float(snap["gps_day_compliance"])
        if gd < 70:
            reasons.append(f"GPS del día bajo ({gd:.1f}%)")
        elif gd > 115:
            reasons.append(f"GPS del día alto ({gd:.1f}%)")
    if pd.notna(snap.get("gps_week_compliance", np.nan)):
        gw = float(snap["gps_week_compliance"])
        if gw < 75:
            reasons.append(f"GPS semanal bajo ({gw:.1f}%)")
        elif gw > 110:
            reasons.append(f"GPS semanal alto ({gw:.1f}%)")
    if snap.get("load_response_label", "Relación carga-respuesta estable") != "Relación carga-respuesta estable":
        reasons.append(snap["load_response_label"])
    if fat_row is None and pd.isna(snap.get("gps_day_compliance", np.nan)) and pd.isna(snap.get("gps_week_compliance", np.nan)):
        action = "Reevaluar"
        reasons = ["Sin datos objetivos suficientes para decidir"]
    if not reasons:
        reasons = ["Respuesta estable", "Sin alertas acumuladas relevantes"]
    availability = {
        "Disponible normal": "Apto normal",
        "Disponible con control": "Apto con control",
        "Ajustar carga": "Exposición reducida",
        "Reducir exposición": "Exposición reducida",
        "Individualizar": "Individualizar",
        "Reevaluar": "Reevaluar en calentamiento",
    }.get(action, "Apto normal")
    color = {
        "Disponible normal": "#16A34A",
        "Disponible con control": "#EAB308",
        "Ajustar carga": "#F59E0B",
        "Reducir exposición": "#F97316",
        "Individualizar": "#DC2626",
        "Reevaluar": "#94A3B8",
    }.get(action, "#94A3B8")
    return {
        "action": action,
        "availability": availability,
        "reasons": reasons,
        "color": color,
        "context": snap.get("context_label", "Sin contexto"),
        "load_response": snap.get("load_response_label", "Sin relación carga-respuesta"),
        "gps_day": snap.get("gps_day_compliance", np.nan),
        "gps_week": snap.get("gps_week_compliance", np.nan),
        "weekly_alerts": snap.get("weekly_alerts", 0),
        "reference_source": ref["source"],
        "qualified_matches": ref["qualified_matches"],
        "required_matches": ref["required_matches"],
        "last_valid_match": ref["last_valid_match"],
    }


def team_staff_table(metrics_df, gps_df, selected_date=None, week_ws=None, session_micro=None):
    metrics_df = metrics_df.copy() if metrics_df is not None else pd.DataFrame()
    gps_df = ensure_gps_datetime(gps_df)
    rows = []
    players = set()
    if selected_date is not None:
        selected_date = pd.to_datetime(selected_date)
        if not metrics_df.empty:
            day_f = metrics_df[pd.to_datetime(metrics_df["Fecha"]).dt.normalize() == selected_date.normalize()]
            if session_micro is not None:
                day_f = day_f[day_f["Microciclo"].fillna("Sin día").astype(str) == str(session_micro)]
            players.update(day_f["Jugador"].dropna().tolist())
        if not gps_df.empty:
            day_g = gps_df[(gps_df["Fecha"].dt.normalize() == selected_date.normalize()) & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")]
            if session_micro is not None:
                day_g = day_g[day_g["Microciclo"].astype(str) == str(session_micro)]
            players.update(day_g["Jugador"].dropna().tolist())
    elif week_ws is not None:
        week_ws = pd.to_datetime(week_ws)
        week_we = week_ws + pd.Timedelta(days=6)
        if not metrics_df.empty:
            wkf = metrics_df[(pd.to_datetime(metrics_df["Fecha"]) >= week_ws) & (pd.to_datetime(metrics_df["Fecha"]) <= week_we)]
            players.update(wkf["Jugador"].dropna().tolist())
        if not gps_df.empty:
            wkg = gps_df[(gps_df["Fecha"] >= week_ws) & (gps_df["Fecha"] <= week_we) & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")]
            players.update(wkg["Jugador"].dropna().tolist())
    for player in sorted(players):
        pos = get_player_position(player, metrics_df, gps_df)
        line = line_group_from_position(pos)
        anchor = selected_date if selected_date is not None else week_ws
        decision = professional_decision(player, anchor, metrics_df, gps_df)
        fat_state, readiness, obs = "Sin dato", np.nan, ""
        if selected_date is not None and not metrics_df.empty:
            pday = metrics_df[(metrics_df["Jugador"] == player) & (pd.to_datetime(metrics_df["Fecha"]).dt.normalize() == selected_date.normalize())]
            if session_micro is not None:
                pday = pday[pday["Microciclo"].fillna("Sin día").astype(str) == str(session_micro)]
            if not pday.empty:
                r = pday.sort_values("Fecha").iloc[-1]
                fat_state = r.get("risk_label", "Sin dato")
                readiness = r.get("readiness_score", np.nan)
                obs = player_comment(r)
        elif week_ws is not None and not metrics_df.empty:
            week_we = pd.to_datetime(week_ws) + pd.Timedelta(days=6)
            pw = metrics_df[(metrics_df["Jugador"] == player) & (pd.to_datetime(metrics_df["Fecha"]) >= pd.to_datetime(week_ws)) & (pd.to_datetime(metrics_df["Fecha"]) <= week_we)]
            if not pw.empty:
                r = pw.sort_values("Fecha").iloc[-1]
                fat_state = r.get("risk_label", "Sin dato")
                readiness = pw["readiness_score"].mean()
                obs = f"Readiness semanal media {readiness:.1f}" if pd.notna(readiness) else ""
        rows.append({
            "Jugador": player,
            "Posición": pos,
            "Línea": line,
            "Estado fatiga": fat_state,
            "Readiness": readiness,
            "GPS día %": decision["gps_day"],
            "GPS semana %": decision["gps_week"],
            "Carga-respuesta": decision["load_response"],
            "Decisión": decision["action"],
            "Disponibilidad": decision["availability"],
            "Observación": "; ".join(decision["reasons"][:2]) if decision["reasons"] else obs,
        })
    return pd.DataFrame(rows)

def top_alerts_block(metrics_df, gps_df, selected_date=None, week_ws=None):
    lines = []
    if selected_date is not None:
        selected_date = pd.to_datetime(selected_date)
        staff = team_staff_table(metrics_df, gps_df, selected_date=selected_date)
        if not staff.empty:
            low_ready = staff.dropna(subset=["Readiness"]).sort_values("Readiness").head(3)
            low_gps = staff.dropna(subset=["GPS día %"]).sort_values("GPS día %").head(3)
            if not low_ready.empty:
                lines.append("Peores 3 readiness del día: " + ", ".join([f"{r.Jugador} ({r.Readiness:.0f})" for _, r in low_ready.iterrows()]))
            if not low_gps.empty:
                lines.append("Peores 3 GPS del día: " + ", ".join([f"{r.Jugador} ({r['GPS día %']:.1f}%)" for _, r in low_gps.iterrows()]))
    if week_ws is not None:
        staff = team_staff_table(metrics_df, gps_df, week_ws=week_ws)
        if not staff.empty:
            low_gps_w = staff.dropna(subset=["GPS semana %"]).sort_values("GPS semana %").head(3)
            if not low_gps_w.empty:
                lines.append("Peores 3 GPS semanales: " + ", ".join([f"{r.Jugador} ({r['GPS semana %']:.1f}%)" for _, r in low_gps_w.iterrows()]))
    return lines

def plot_line_summary(staff_df, value_col, title):
    if staff_df is None or staff_df.empty or value_col not in staff_df.columns:
        return go.Figure()
    temp = staff_df.groupby("Línea", as_index=False)[value_col].mean(numeric_only=True)
    fig = px.bar(temp, x="Línea", y=value_col, title=title)
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=60, b=30), title_x=0.5)
    return fig

def visual_decision_box(title, decision):
    reason_txt = " · ".join(decision["reasons"][:3]) if decision["reasons"] else "Sin motivos registrados"
    last_match = pd.to_datetime(decision["last_valid_match"]).strftime("%Y-%m-%d") if pd.notna(decision["last_valid_match"]) else "NA"
    return f"""
    <div style="background:white;border:1px solid rgba(15,23,42,0.08);border-left:8px solid {decision['color']};border-radius:18px;padding:16px 18px;box-shadow:0 6px 18px rgba(15,23,42,0.06);margin-bottom:12px;">
        <div style="font-size:0.82rem;color:#475467;">{title}</div>
        <div style="font-size:1.45rem;font-weight:900;color:#101828;margin-top:4px;">{decision['action']}</div>
        <div style="font-size:0.95rem;color:#344054;margin-top:6px;"><b>Motivo:</b> {reason_txt}</div>
        <div style="font-size:0.90rem;color:#667085;margin-top:6px;"><b>Contexto:</b> {decision['context']} · <b>GPS ref.:</b> {decision['reference_source']} · <b>Partidos válidos:</b> {decision['qualified_matches']}/{decision['required_matches']} · <b>Último partido válido:</b> {last_match}</div>
    </div>
    """

def style_staff_table(df, sort_col=None):
    if df is None or df.empty:
        return df
    show = df.copy()
    for c in ["Readiness", "GPS día %", "GPS semana %"]:
        if c in show.columns:
            show[c] = pd.to_numeric(show[c], errors="coerce").round(1)
    if sort_col in show.columns:
        show = show.sort_values(sort_col, ascending=(sort_col == "Readiness"), na_position="last")
    return show

def export_integrated_base(metrics_df, gps_df):
    gps_df = ensure_gps_datetime(gps_df)
    players = sorted(set((metrics_df["Jugador"].dropna().tolist() if metrics_df is not None and not metrics_df.empty else []) + (gps_df["Jugador"].dropna().tolist() if gps_df is not None and not gps_df.empty else [])))
    dates = sorted(set((pd.to_datetime(metrics_df["Fecha"]).dropna().dt.strftime("%Y-%m-%d").tolist() if metrics_df is not None and not metrics_df.empty else []) + (pd.to_datetime(gps_df["Fecha"]).dropna().dt.strftime("%Y-%m-%d").tolist() if gps_df is not None and not gps_df.empty else [])))
    rows = []
    for d in dates:
        for p in players:
            dec = professional_decision(p, d, metrics_df, gps_df)
            fat = metrics_df[(metrics_df["Jugador"] == p) & (pd.to_datetime(metrics_df["Fecha"]).dt.strftime("%Y-%m-%d") == str(d))] if metrics_df is not None and not metrics_df.empty else pd.DataFrame()
            r = fat.iloc[-1] if not fat.empty else None
            rows.append({
                "Fecha": d, "Jugador": p, "Posicion": get_player_position(p, metrics_df, gps_df),
                "Risk": r.get("risk_label", np.nan) if r is not None else np.nan,
                "Readiness": r.get("readiness_score", np.nan) if r is not None else np.nan,
                "Loss": r.get("objective_loss_score", np.nan) if r is not None else np.nan,
                "GPS_dia": dec["gps_day"], "GPS_semana": dec["gps_week"], "Decision": dec["action"],
                "Disponibilidad": dec["availability"], "Motivo": " | ".join(dec["reasons"][:3]),
            })
    return pd.DataFrame(rows)

def page_cargar():
    st.markdown("### Carga de datos")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### CONTROL DE FATIGA")
        fat_fecha = st.date_input("Fecha control de fatiga", value=pd.Timestamp.today(), key="fat_fecha_v2")
        fat_micro = st.selectbox("Día microciclo fatiga", ["MD+1","MD-4","MD-3","MD-2","MD-1","PARTIDO"], index=4, key="fat_micro_v2")
        uploaded = st.file_uploader("Sube Excel/CSV de fatiga", type=["xlsx","xls","csv"], key="fatigue_upload_v2")
        if uploaded is not None:
            try:
                parsed = parse_uploaded(uploaded)
                parsed["Fecha"] = pd.to_datetime(fat_fecha)
                parsed["Microciclo"] = fat_micro
                st.success(f"Archivo interpretado correctamente: {parsed['Jugador'].nunique()} jugadores · {parsed['Fecha'].nunique()} fecha(s)")
                for line in build_upload_validation_report(parsed, mode="fatigue"):
                    st.caption("• " + line)
                cols_show = [c for c in ["Fecha","Microciclo","Jugador","Posicion","CMJ","RSI_mod","VMP","sRPE","Observaciones"] if c in parsed.columns]
                st.dataframe(parsed[cols_show], use_container_width=True, hide_index=True)
                if st.button("Guardar control de fatiga", type="primary", key="save_fat_v2"):
                    upsert_monitoring(parsed)
                    st.success("Datos de fatiga guardados correctamente.")
                    st.rerun()
            except Exception as e:
                st.error(f"No se pudo interpretar el archivo de fatiga: {e}")
    with c2:
        st.markdown("#### SESIÓN GPS")
        gps_fecha = st.date_input("Fecha GPS", value=pd.Timestamp.today(), key="gps_fecha_v2")
        gps_micro = st.selectbox("Día microciclo GPS", ["PARTIDO","MD+1","MD-4","MD-3","MD-2","MD-1"], index=3, key="gps_micro_v2")
        gps_uploaded = st.file_uploader("Sube CSV/Excel GPS", type=["xlsx","xls","csv"], key="gps_upload_v2")
        if gps_uploaded is not None:
            try:
                parsed_gps = parse_gps_uploaded(gps_uploaded, gps_fecha, gps_micro)
                st.success(f"Archivo GPS interpretado: {parsed_gps['Jugador'].nunique()} jugadores")
                for line in build_upload_validation_report(parsed_gps, mode="gps", gps_reference_df=load_gps()):
                    st.caption("• " + line)
                st.dataframe(parsed_gps[["Fecha","Microciclo","Jugador","Posicion",*GPS_METRICS]], use_container_width=True, hide_index=True)
                if st.button("Guardar sesión GPS", key="save_gps_v2"):
                    upsert_gps(parsed_gps)
                    st.success("Datos GPS guardados correctamente.")
                    st.rerun()
            except Exception as e:
                st.error(f"No se pudo interpretar el archivo GPS: {e}")

def page_equipo(metrics_df, gps_df):
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return
    st.markdown('<div class="hero"><div style="font-size:0.92rem; opacity:0.9;">Monitorización neuromuscular + GPS</div><div style="font-size:2.15rem; font-weight:900; margin-top:0.15rem;">Equipo</div><div style="font-size:1rem; opacity:0.92; margin-top:0.35rem;">Panel operativo central del staff · resumen → decisión → visual → detalle.</div></div>', unsafe_allow_html=True)
    week_labels, week_map = build_week_options(metrics_df, gps_df)
    if not week_labels:
        st.info("No hay semanas disponibles.")
        return
    if st.button("Ir a última semana disponible", key="last_week_btn_v2"):
        st.session_state["equipo_week_label"] = week_labels[-1]
    wk_default = st.session_state.get("equipo_week_label", week_labels[-1])
    wk_idx = week_labels.index(wk_default) if wk_default in week_labels else len(week_labels)-1
    wk_label = st.selectbox("Semana (lunes-domingo)", week_labels, index=wk_idx, key="equipo_week_v2")
    week_ws = week_map[wk_label]
    view_mode = st.radio("Vista", ["Resumen semanal","Sesión concreta"], horizontal=True, key="equipo_view_v2")
    focus = st.radio("Enfoque", ["Integrado","Fatiga","GPS"], horizontal=True, key="equipo_focus_v2")
    gps_df = ensure_gps_datetime(gps_df)
    week_we = week_ws + pd.Timedelta(days=6)
    week_fat = metrics_df[(metrics_df["Fecha"] >= week_ws) & (metrics_df["Fecha"] <= week_we)].copy() if not metrics_df.empty else pd.DataFrame()
    week_gps_raw = gps_df[(gps_df["Fecha"] >= week_ws) & (gps_df["Fecha"] <= week_we) & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")].copy() if not gps_df.empty else pd.DataFrame()
    week_gps = gps_compute_compliance(week_gps_raw, reference_df=gps_df) if not week_gps_raw.empty else pd.DataFrame()
    if view_mode == "Resumen semanal":
        summary = weekly_global_summary(metrics_df, gps_df, week_ws)
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Sesiones fatiga", summary["fatigue_sessions"], "semana")
        with c2: kpi("Sesiones GPS", summary["gps_sessions"], "semana")
        with c3: kpi("Readiness media", "NA" if pd.isna(summary["readiness_mean"]) else f"{summary['readiness_mean']:.1f}", "semana")
        with c4: kpi("GPS semanal medio", "NA" if pd.isna(summary["gps_compliance_mean"]) else f"{summary['gps_compliance_mean']:.1f}%", "semana")
        collective_dec = {"action": "Disponible con control" if (pd.isna(summary["readiness_mean"]) or summary["readiness_mean"] >= 70) else "Ajustar carga", "reasons": [integrated_week_text(metrics_df, gps_df, week_ws)], "context": f"Semana {wk_label}", "reference_source": "colectiva", "qualified_matches": 0, "required_matches": GPS_MATCH_MIN_MATCHES, "last_valid_match": pd.NaT, "color": "#16A34A" if pd.isna(summary["readiness_mean"]) or summary["readiness_mean"] >= 70 else "#F59E0B"}
        st.markdown(visual_decision_box("Bloque de decisión semanal", collective_dec), unsafe_allow_html=True)
        alert_lines = top_alerts_block(metrics_df, gps_df, week_ws=week_ws)
        if alert_lines: st.warning("  \n".join(alert_lines))
        staff_week = team_staff_table(metrics_df, gps_df, week_ws=week_ws)
        if not staff_week.empty:
            st.markdown("### Matriz integrada de staff")
            show = style_staff_table(staff_week, sort_col="GPS semana %")
            st.dataframe(show[["Jugador","Posición","Línea","Estado fatiga","Readiness","GPS semana %","Carga-respuesta","Decisión","Observación"]], use_container_width=True, hide_index=True)
        if focus in ["Integrado","Fatiga"] and not week_fat.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_score_trend(week_fat), use_container_width=True)
            with b: st.plotly_chart(plot_team_risk_distribution(week_fat.groupby("Jugador", as_index=False).last()), use_container_width=True)
        if focus in ["Integrado","GPS"] and not week_gps.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_gps_weekly_support(gps_df, week_ws), use_container_width=True)
            with b: st.plotly_chart(plot_line_summary(staff_week, "GPS semana %", "GPS semanal por líneas"), use_container_width=True)
        if focus == "Integrado" and not week_fat.empty:
            last_rows = week_fat.sort_values("Fecha").groupby("Jugador", as_index=False).last()
            st.plotly_chart(plot_integrated_team_matrix(last_rows, metrics_df, gps_df, week_we), use_container_width=True)
    else:
        sess_opts = session_options_for_week(metrics_df, gps_df, week_ws)
        if not sess_opts:
            st.info("No hay sesiones en esa semana.")
            return
        sess_label = st.selectbox("Sesión de la semana", sess_opts, key="equipo_sesion_v2")
        sess_date_str, sess_md = [x.strip() for x in sess_label.split("|", 1)]
        selected_date = pd.to_datetime(sess_date_str)
        team_day = week_fat[(week_fat["Fecha"].dt.normalize() == selected_date.normalize())].copy() if not week_fat.empty else pd.DataFrame()
        if sess_md != "Sin día" and not team_day.empty:
            team_day = team_day[team_day["Microciclo"].fillna("Sin día").astype(str) == sess_md]
        gps_day = week_gps[(week_gps["Fecha"].dt.normalize() == selected_date.normalize()) & (week_gps["Microciclo"].astype(str) == sess_md)].copy() if not week_gps.empty else pd.DataFrame()
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: kpi("Fecha", selected_date.strftime("%Y-%m-%d"), sess_md)
        with c2: kpi("Jugadores fatiga", int(team_day["Jugador"].nunique()) if not team_day.empty else 0, "sesión")
        with c3: kpi("Readiness media", "NA" if team_day.empty else f"{team_day['readiness_score'].mean():.1f}", "sesión")
        with c4: kpi("GPS medio", "NA" if gps_day.empty else f"{gps_day['compliance_score'].mean():.1f}%", "sesión")
        with c5: kpi("Críticos", int((team_day["risk_label"] == "Fatiga crítica").sum()) if not team_day.empty else 0, "sesión")
        collective_dec = {"action": "Disponible normal" if team_day.empty or team_day["objective_loss_score"].mean() < 1 else "Ajustar carga", "reasons": [team_interpretation(team_day)] if not team_day.empty else ["Sin datos de fatiga para esta sesión"], "context": integrated_week_text(metrics_df, gps_df, selected_date), "reference_source": "colectiva", "qualified_matches": 0, "required_matches": GPS_MATCH_MIN_MATCHES, "last_valid_match": pd.NaT, "color": "#16A34A" if team_day.empty or team_day["objective_loss_score"].mean() < 1 else "#F59E0B"}
        st.markdown(visual_decision_box("Bloque de decisión del día", collective_dec), unsafe_allow_html=True)
        alert_lines = top_alerts_block(metrics_df, gps_df, selected_date=selected_date)
        if alert_lines: st.warning("  \n".join(alert_lines))
        staff_day = team_staff_table(metrics_df, gps_df, selected_date=selected_date, session_micro=sess_md)
        if not staff_day.empty:
            st.markdown("### Matriz integrada de staff")
            show = style_staff_table(staff_day, sort_col="Readiness")
            st.dataframe(show[["Jugador","Posición","Línea","Estado fatiga","Readiness","GPS día %","GPS semana %","Carga-respuesta","Decisión","Observación"]], use_container_width=True, hide_index=True)
        if focus in ["Integrado","Fatiga"] and not team_day.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_risk_distribution(team_day), use_container_width=True)
            with b: st.plotly_chart(plot_team_objective_bar(team_day), use_container_width=True)
        if focus in ["Integrado","GPS"] and not gps_day.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_gps_support(gps_day), use_container_width=True)
            with b: st.plotly_chart(plot_line_summary(staff_day, "GPS día %", "GPS del día por líneas"), use_container_width=True)
        if focus == "Integrado" and not team_day.empty:
            st.plotly_chart(plot_team_decision_matrix(team_day), use_container_width=True)

def page_jugador(metrics_df, gps_df):
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return
    gps_df = ensure_gps_datetime(gps_df)
    player_map = build_player_display_options(metrics_df, gps_df)
    st.markdown('<div class="section-title">Jugador</div>', unsafe_allow_html=True)
    player_label = st.selectbox("Selecciona jugador", list(player_map.keys()), key="player_selector_v2")
    player = player_map[player_label]
    week_labels, week_map = build_week_options(metrics_df, gps_df, player=player)
    if not week_labels:
        st.info("No hay semanas disponibles para este jugador.")
        return
    if st.button("Última semana", key="player_last_week_v2"):
        st.session_state["player_week_label_v2"] = week_labels[-1]
    wk_default = st.session_state.get("player_week_label_v2", week_labels[-1])
    wk_idx = week_labels.index(wk_default) if wk_default in week_labels else len(week_labels)-1
    wk_label = st.selectbox("Semana (lunes-domingo)", week_labels, index=wk_idx, key="player_week_v2")
    week_ws = week_map[wk_label]
    view_mode = st.radio("Vista", ["Resumen semanal","Sesión concreta"], horizontal=True, key="player_view_mode_v2")
    player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame()
    player_gps = gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame()
    ref = gps_reference_info(gps_df, player)
    selected_anchor = week_ws if view_mode == "Resumen semanal" else (latest_nonmatch_date(player_df, player_gps, player=player) or week_ws)
    decision = professional_decision(player, selected_anchor, metrics_df, gps_df)
    last_match = pd.to_datetime(decision["last_valid_match"]).strftime("%Y-%m-%d") if pd.notna(decision["last_valid_match"]) else "NA"
    st.markdown(f'<div class="card"><div style="font-size:1.9rem;font-weight:900;color:#101828;">{player_label.replace(" - ", " · ")}</div><div style="margin-top:0.55rem;"><span class="pill" style="background:{decision["color"]};">{decision["action"]}</span></div><div style="margin-top:0.7rem;color:#475467;"><b>Contexto:</b> {decision["context"]} · <b>Carga-respuesta:</b> {decision["load_response"]} · <b>Referencia GPS:</b> {ref["source"]} · <b>Partidos válidos:</b> {ref["qualified_matches"]}/{ref["required_matches"]} · <b>Último partido válido:</b> {last_match}</div></div>', unsafe_allow_html=True)
    tabs = st.tabs(["Diagnóstico","GPS","Tendencia","Informes rápidos"])
    week_we = week_ws + pd.Timedelta(days=6)
    player_week_fat = player_df[(player_df["Fecha"] >= week_ws) & (player_df["Fecha"] <= week_we)].copy() if not player_df.empty else pd.DataFrame()
    player_week_gps = gps_player_week_table(gps_df, player, week_ws) if not player_gps.empty else pd.DataFrame()
    row = None; session_gps = pd.DataFrame(); selected_date = week_ws; sess_md = "Semanal"
    if view_mode == "Sesión concreta":
        sess_opts = session_options_for_week(metrics_df, gps_df, week_ws, player=player)
        if not sess_opts:
            st.info("No hay sesiones en esa semana.")
            return
        sess_label = st.selectbox("Sesión de la semana", sess_opts, key="player_sess_v2")
        sess_date_str, sess_md = [x.strip() for x in sess_label.split("|", 1)]
        selected_date = pd.to_datetime(sess_date_str)
        current = player_df[player_df["Fecha"].dt.normalize() == selected_date.normalize()] if not player_df.empty else pd.DataFrame()
        row = current.iloc[-1] if not current.empty else None
        session_gps = gps_player_session_table(gps_df, player, selected_date, micro=sess_md) if not player_gps.empty else pd.DataFrame()
        decision = professional_decision(player, selected_date, metrics_df, gps_df)
    with tabs[0]:
        if view_mode == "Resumen semanal":
            c1,c2,c3,c4 = st.columns(4)
            with c1: kpi("Controles fatiga", int(player_week_fat[["Fecha","Microciclo"]].drop_duplicates().shape[0]) if not player_week_fat.empty else 0, "semana")
            with c2: kpi("Readiness sem.", "NA" if player_week_fat.empty else f"{player_week_fat['readiness_score'].mean():.1f}", "media")
            with c3: kpi("GPS sem.", "NA" if player_week_gps.empty else f"{pd.to_numeric(player_week_gps['pct'], errors='coerce').mean():.1f}%", "media")
            with c4: kpi("Decisión", decision["action"], decision["availability"])
            st.markdown(visual_decision_box("Bloque de decisión semanal", decision), unsafe_allow_html=True)
            if not player_week_fat.empty:
                st.plotly_chart(plot_player_integrated_week_dashboard(player, week_ws, metrics_df, gps_df), use_container_width=True)
        else:
            if row is None:
                st.warning("No hay datos de control de fatiga para esta sesión.")
            else:
                c1,c2,c3,c4,c5 = st.columns(5)
                with c1: kpi("Fecha", selected_date.strftime("%Y-%m-%d"), sess_md)
                with c2: kpi("Riesgo", row["risk_label"], "clasificación")
                with c3: kpi("Loss", f"{row['objective_loss_score']:.2f}", "0-3")
                with c4: kpi("Readiness", f"{row['readiness_score']:.0f}", "día")
                with c5: kpi("Decisión", decision["action"], decision["availability"])
                st.markdown(visual_decision_box("Bloque de decisión del día", decision), unsafe_allow_html=True)
                a,b = st.columns(2)
                with a: st.plotly_chart(radar_relative_loss(row), use_container_width=True)
                with b: st.plotly_chart(radar_current_vs_baseline(row), use_container_width=True)
    with tabs[1]:
        if view_mode == "Resumen semanal":
            if player_week_gps.empty: st.info("Sin GPS semanal disponible.")
            else:
                gps_progress_bars_streamlit(player_week_gps, "Resumen GPS semanal")
                st.plotly_chart(plot_player_gps_support(player_week_gps, "Apoyo visual GPS semanal"), use_container_width=True)
                st.caption(f"Referencia GPS usada: {ref['source']} · partidos válidos: {ref['qualified_matches']}/{ref['required_matches']}")
        else:
            if session_gps.empty: st.info("Sin GPS del día disponible.")
            else:
                gps_progress_bars_streamlit(session_gps, "Cumplimiento GPS del día")
                st.plotly_chart(plot_player_gps_support(session_gps, "Apoyo visual GPS del día"), use_container_width=True)
    with tabs[2]:
        if player_df.empty: st.info("Sin datos longitudinales.")
        else:
            anchor_date = week_we if view_mode == "Resumen semanal" else selected_date
            st.plotly_chart(plot_objective_timeline(player_df, anchor_date), use_container_width=True)
    with tabs[3]:
        st.markdown(f"- **Estado actual:** {decision['action']}")
        st.markdown(f"- **Disponibilidad:** {decision['availability']}")
        st.markdown(f"- **Motivo principal:** {' · '.join(decision['reasons'][:3])}")
        st.markdown(f"- **Referencia GPS:** {ref['source']} · {ref['qualified_matches']}/{ref['required_matches']} partidos válidos")

def page_informes(metrics_df, gps_df):
    gps_df = ensure_gps_datetime(gps_df)
    st.markdown('<div class="section-title">Informes descargables</div>', unsafe_allow_html=True)
    player_map = build_player_display_options(metrics_df, gps_df)
    tab1,tab2,tab3,tab4,tab5 = st.tabs(["Informe individual staff anual","Informe individual staff por sesión","Informe semanal integrado jugador","Informe entrenador sesión","Informe semanal global"])
    with tab1:
        player_label = st.selectbox("Jugador · informe anual", list(player_map.keys()), key="yr_pro")
        player = player_map[player_label]
        player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame(columns=["Fecha"])
        if not player_df.empty:
            latest = player_df.iloc[-1]
            st.markdown(f"**Resumen actual:** {latest['risk_label']} · loss {latest['objective_loss_score']:.2f} · readiness {latest['readiness_score']:.0f}")
            html = player_season_html(player_df, player, gps_df=gps_df)
            st.download_button("Descargar HTML anual", data=html.encode("utf-8"), file_name=f"informe_anual_{player.replace(' ','_')}.html", mime="text/html")
            st.download_button("Descargar PDF anual", data=build_pdf_bytes_player_season(player_df, player, gps_df=gps_df), file_name=f"informe_anual_{player.replace(' ','_')}.pdf", mime="application/pdf")
    with tab2:
        player_label = st.selectbox("Jugador · informe sesión", list(player_map.keys()), key="ses_pro")
        player = player_map[player_label]
        source_dates = sorted(set(([pd.to_datetime(d).strftime("%Y-%m-%d") for d in metrics_df[metrics_df["Jugador"] == player]["Fecha"].dropna().unique()] if not metrics_df.empty else []) + ([pd.to_datetime(d).strftime("%Y-%m-%d") for d in gps_df[gps_df["Jugador"] == player]["Fecha"].dropna().unique()] if not gps_df.empty else [])))
        if source_dates:
            sel_date = st.selectbox("Fecha sesión", source_dates, key="sesd_pro")
            player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame()
            session_df = player_df[player_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date].copy() if not player_df.empty else pd.DataFrame()
            gps_only_df = gps_df[(gps_df["Jugador"] == player) & (gps_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date)] if not gps_df.empty else pd.DataFrame()
            if not session_df.empty:
                row = session_df.iloc[-1]
                html = player_session_html(row, player_df, session_df, gps_df=gps_df)
                st.download_button("Descargar HTML sesión", data=html.encode("utf-8"), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.html", mime="text/html")
                st.download_button("Descargar PDF sesión", data=build_pdf_bytes_player_session(row, player_df, gps_df=gps_df), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.pdf", mime="application/pdf")
            elif not gps_only_df.empty:
                html = f"<html><head><meta charset='utf-8'>{report_css()}</head><body><div class='hero'><div style='font-size:12px;opacity:0.9;'>Informe individual · Sesión específica</div><div style='font-size:32px;font-weight:900;line-height:1.15;'>{player}</div><div style='font-size:15px;margin-top:6px;'>Fecha: {sel_date}</div></div><div class='section'><div class='title'>Observación</div><div class='diag'>No hay datos de control de fatiga para esta fecha. Se muestran únicamente los datos GPS disponibles.</div></div>{gps_player_report_html(player, gps_df, pd.to_datetime(sel_date))}</body></html>"
                st.download_button("Descargar HTML sesión", data=html.encode("utf-8"), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.html", mime="text/html")
                st.download_button("Descargar PDF sesión", data=build_pdf_bytes_player_session_gps_only(player, gps_df, pd.to_datetime(sel_date)), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.pdf", mime="application/pdf")
    with tab3:
        player_label = st.selectbox("Jugador · informe semanal", list(player_map.keys()), key="gpswk_pro")
        player = player_map[player_label]
        week_labels, week_map = build_week_options(metrics_df, gps_df, player=player)
        if week_labels:
            wk_label = st.selectbox("Semana de referencia", week_labels, key="gpswkd_pro")
            week_ws = week_map[wk_label]
            html = player_weekly_html(player, metrics_df[metrics_df["Jugador"] == player].copy() if not metrics_df.empty else pd.DataFrame(), gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame(), week_ws)
            st.download_button("Descargar HTML semanal", data=html.encode("utf-8"), file_name=f"informe_semanal_{player.replace(' ','_')}_{pd.to_datetime(week_ws).strftime('%Y%m%d')}.html", mime="text/html")
            st.download_button("Descargar PDF semanal", data=build_pdf_bytes_player_weekly(player, metrics_df[metrics_df["Jugador"] == player].copy() if not metrics_df.empty else pd.DataFrame(), gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame(), week_ws), file_name=f"informe_semanal_{player.replace(' ','_')}_{pd.to_datetime(week_ws).strftime('%Y%m%d')}.pdf", mime="application/pdf")
    with tab4:
        all_week_labels, all_week_map = build_week_options(metrics_df, gps_df)
        if all_week_labels:
            wk_label = st.selectbox("Semana sesión global", all_week_labels, key="teamwk_pro")
            week_ws = all_week_map[wk_label]
            sess_opts = session_options_for_week(metrics_df, gps_df, week_ws)
            if sess_opts:
                sess_label = st.selectbox("Sesión global", sess_opts, key="teamr_pro")
                sel_date, sel_md = [x.strip() for x in sess_label.split("|", 1)]
                team_day = metrics_df[(metrics_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date)].copy() if not metrics_df.empty else pd.DataFrame()
                if sel_md != "Sin día" and not team_day.empty:
                    team_day = team_day[team_day["Microciclo"].fillna("Sin día").astype(str) == sel_md]
                if not team_day.empty:
                    html = coach_session_html(team_day, sel_date, gps_df=gps_df)
                    st.download_button("Descargar HTML entrenador", data=html.encode("utf-8"), file_name=f"informe_equipo_sesion_{sel_date}.html", mime="text/html")
                    st.download_button("Descargar PDF entrenador", data=build_pdf_bytes_team_session(team_day, sel_date, gps_df=gps_df), file_name=f"informe_equipo_sesion_{sel_date}.pdf", mime="application/pdf")
    with tab5:
        all_week_labels, all_week_map = build_week_options(metrics_df, gps_df)
        if all_week_labels:
            wk_label = st.selectbox("Semana informe global", all_week_labels, key="globalwk_pro")
            week_ws = all_week_map[wk_label]
            html = weekly_global_html(metrics_df, gps_df, week_ws)
            st.download_button("Descargar HTML semanal global", data=html.encode("utf-8"), file_name=f"informe_global_semanal_{pd.to_datetime(week_ws).strftime('%Y%m%d')}.html", mime="text/html")
            st.download_button("Descargar PDF semanal global", data=build_pdf_bytes_weekly_global(metrics_df, gps_df, week_ws), file_name=f"informe_global_semanal_{pd.to_datetime(week_ws).strftime('%Y%m%d')}.pdf", mime="application/pdf")

def page_admin(base_df, gps_df):
    gps_df = ensure_gps_datetime(gps_df)
    metrics_df = compute_metrics(base_df) if base_df is not None and not base_df.empty else pd.DataFrame()
    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi("Registros fatiga", len(base_df), "total")
    with c2: kpi("Jugadores fatiga", base_df["Jugador"].nunique() if not base_df.empty else 0, "únicos")
    with c3: kpi("Sesiones GPS microciclo", len(gps_df[gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO"][["Fecha","Microciclo"]].drop_duplicates()) if not gps_df.empty else 0, "guardadas")
    with c4: kpi("Partidos GPS", len(gps_df[gps_df["Microciclo"].astype(str).str.upper() == "PARTIDO"]["Fecha"].drop_duplicates()) if not gps_df.empty else 0, "guardados")
    c5,c6,c7 = st.columns(3)
    with c5:
        if not base_df.empty: st.download_button("Descargar base fatiga CSV", data=base_df.to_csv(index=False).encode("utf-8"), file_name="fatiga.csv", mime="text/csv")
    with c6:
        if not gps_df.empty: st.download_button("Descargar base GPS CSV", data=gps_df.to_csv(index=False).encode("utf-8"), file_name="gps.csv", mime="text/csv")
    with c7:
        integrated = export_integrated_base(metrics_df, gps_df)
        if not integrated.empty: st.download_button("Descargar base integrada CSV", data=integrated.to_csv(index=False).encode("utf-8"), file_name="integrada.csv", mime="text/csv")
    # mantenemos los bloques de borrado del código original
    if 'page_admin' in globals():
        pass



# =========================================================
# PROFESSIONAL V3 VISUAL / STAFF OVERRIDES
# =========================================================
def plot_week_session_summary(df, title="Evolución semanal del grupo"):
    if df is None or df.empty:
        return go.Figure()
    temp = df.copy()
    temp["Fecha"] = pd.to_datetime(temp["Fecha"], errors="coerce")
    temp["Microciclo"] = temp.get("Microciclo", "Sin día").fillna("Sin día").astype(str)
    temp = temp.groupby(["Fecha", "Microciclo"], as_index=False).agg(
        readiness_score=("readiness_score", "mean"),
        objective_loss_score=("objective_loss_score", "mean"),
        objective_loss_mean_pct=("objective_loss_mean_pct", "mean"),
        n_players=("Jugador", "nunique"),
    ).sort_values(["Fecha", "Microciclo"])
    temp["sesion_label"] = temp["Fecha"].dt.strftime("%Y-%m-%d") + " · " + temp["Microciclo"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=temp["sesion_label"], y=temp["objective_loss_score"],
        mode="lines+markers", name="Loss medio",
        line=dict(color="#C62828", width=3)
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=temp["sesion_label"], y=temp["readiness_score"],
        mode="lines+markers", name="Readiness media",
        line=dict(color="#1F77B4", width=3)
    ), secondary_y=True)
    fig.update_layout(
        title=title, height=360, margin=dict(l=20, r=20, t=60, b=40), title_x=0.5,
        legend=dict(orientation="h", y=1.08, x=0)
    )
    fig.update_yaxes(title_text="Loss", secondary_y=False)
    fig.update_yaxes(title_text="Readiness", secondary_y=True)
    fig.update_xaxes(tickangle=-25, title="")
    return fig

def plot_team_staff_matrix_visual(staff_df, gps_col="GPS semana %", title="Matriz integrada de staff"):
    if staff_df is None or staff_df.empty or gps_col not in staff_df.columns:
        return go.Figure()
    temp = staff_df.copy()
    temp["risk_num"] = temp["Estado fatiga"].map({
        "Estado óptimo": 0, "Buen estado": 0.2, "Fatiga leve": 1, "Fatiga leve-moderada": 1.5,
        "Fatiga moderada": 2, "Fatiga moderada-alta": 2.5, "Fatiga crítica": 3
    }).fillna(0.5)
    temp["Readiness"] = pd.to_numeric(temp["Readiness"], errors="coerce")
    temp[gps_col] = pd.to_numeric(temp[gps_col], errors="coerce")
    fig = px.scatter(
        temp,
        x=gps_col, y="Readiness", size="risk_num",
        color="Decisión", hover_name="Jugador", text="Jugador",
        title=title,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_traces(textposition="top center", marker=dict(line=dict(width=1, color="white")))
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=30), title_x=0.5)
    return fig

def style_staff_table(staff_df, sort_col=None):
    if staff_df is None or staff_df.empty:
        return staff_df
    show = staff_df.copy()
    for c in ["Readiness", "GPS día %", "GPS semana %"]:
        if c in show.columns:
            show[c] = pd.to_numeric(show[c], errors="coerce").round(1)
    if sort_col in show.columns:
        show = show.sort_values(sort_col, ascending=True if sort_col == "Readiness" else False, na_position="last")

    def _decision_bg(val):
        cmap = {
            "Disponible normal": "background-color: rgba(22,163,74,0.18); color:#166534; font-weight:700;",
            "Disponible con control": "background-color: rgba(234,179,8,0.18); color:#854d0e; font-weight:700;",
            "Ajustar carga": "background-color: rgba(245,158,11,0.18); color:#9a3412; font-weight:700;",
            "Reducir exposición": "background-color: rgba(249,115,22,0.18); color:#9a3412; font-weight:700;",
            "Individualizar": "background-color: rgba(220,38,38,0.18); color:#991b1b; font-weight:700;",
            "Reevaluar": "background-color: rgba(148,163,184,0.18); color:#475569; font-weight:700;",
        }
        return cmap.get(str(val), "")

    def _fatigue_bg(val):
        cmap = {
            "Estado óptimo": "background-color: rgba(21,128,61,0.14); color:#166534; font-weight:700;",
            "Buen estado": "background-color: rgba(46,139,87,0.14); color:#166534; font-weight:700;",
            "Fatiga leve": "background-color: rgba(227,160,8,0.16); color:#854d0e; font-weight:700;",
            "Fatiga leve-moderada": "background-color: rgba(245,158,11,0.18); color:#9a3412; font-weight:700;",
            "Fatiga moderada": "background-color: rgba(249,115,22,0.18); color:#9a3412; font-weight:700;",
            "Fatiga moderada-alta": "background-color: rgba(234,88,12,0.18); color:#9a3412; font-weight:700;",
            "Fatiga crítica": "background-color: rgba(185,28,28,0.18); color:#991b1b; font-weight:700;",
            "Sin dato": "background-color: rgba(148,163,184,0.18); color:#475569; font-weight:700;",
            "Sin referencia": "background-color: rgba(148,163,184,0.18); color:#475569; font-weight:700;",
        }
        return cmap.get(str(val), "")

    styler = show.style
    if "Readiness" in show.columns:
        styler = styler.bar(subset=["Readiness"], align="mid", color="#93C5FD")
    if "GPS día %" in show.columns:
        styler = styler.bar(subset=["GPS día %"], align="mid", color="#FDE68A")
    if "GPS semana %" in show.columns:
        styler = styler.bar(subset=["GPS semana %"], align="mid", color="#86EFAC")
    if "Decisión" in show.columns:
        styler = styler.map(_decision_bg, subset=["Decisión"])
    if "Estado fatiga" in show.columns:
        styler = styler.map(_fatigue_bg, subset=["Estado fatiga"])
    return styler

def visual_alert_block(lines, title="Top alerts"):
    if not lines:
        return ""
    items = "".join([f"<li>{l.replace('**','')}</li>" for l in lines])
    return f"""
    <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:16px;padding:14px 16px;margin-bottom:12px;">
      <div style="font-weight:800;color:#9A3412;margin-bottom:6px;">{title}</div>
      <ul style="margin:0 0 0 18px;color:#9A3412;">{items}</ul>
    </div>
    """

def player_alert_history(player_df, anchor_date):
    if player_df is None or player_df.empty:
        return {"alerts7":0,"alerts14":0,"consecutive_bad":0}
    anchor_date = pd.to_datetime(anchor_date)
    df = player_df.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    bad = df["risk_label"].isin(["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"])
    alerts7 = int(df[(df["Fecha"] >= anchor_date - pd.Timedelta(days=7)) & (df["Fecha"] <= anchor_date)][bad].shape[0])
    alerts14 = int(df[(df["Fecha"] >= anchor_date - pd.Timedelta(days=14)) & (df["Fecha"] <= anchor_date)][bad].shape[0])
    consecutive = 0
    for v in reversed(bad.tolist()):
        if v:
            consecutive += 1
        else:
            break
    return {"alerts7": alerts7, "alerts14": alerts14, "consecutive_bad": consecutive}

def plot_team_priority_board(team_df, title="Prioridad operativa del grupo"):
    if team_df is None or team_df.empty:
        return go.Figure()
    temp = team_df.copy()
    temp["priority"] = temp["risk_label"].map({
        "Estado óptimo":0,"Buen estado":0.2,"Fatiga leve":1,"Fatiga leve-moderada":1.5,
        "Fatiga moderada":2,"Fatiga moderada-alta":2.5,"Fatiga crítica":3
    }).fillna(0.5)
    fig = px.bar(
        temp.sort_values(["priority","objective_loss_score"], ascending=[False,False]),
        x="Jugador", y="priority", color="risk_label",
        color_discrete_map=RISK_COLORS, title=title, text="risk_label"
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=360, margin=dict(l=20,r=20,t=60,b=40), title_x=0.5, showlegend=False)
    fig.update_yaxes(title="Prioridad")
    fig.update_xaxes(tickangle=-30)
    return fig

def plot_team_gps_status_distribution(gps_df, week_ws=None, selected_date=None):
    if gps_df is None or gps_df.empty:
        return go.Figure()
    temp = ensure_gps_datetime(gps_df).copy()
    if selected_date is not None:
        d = pd.to_datetime(selected_date).normalize()
        temp = temp[(temp["Fecha"].dt.normalize() == d) & (temp["Microciclo"].astype(str).str.upper() != "PARTIDO")]
        temp = gps_compute_compliance(temp, reference_df=ensure_gps_datetime(gps_df))
        if temp.empty:
            return go.Figure()
        source = temp["session_status"].value_counts().reset_index()
        source.columns = ["Estado","N"]
        title = "Distribución de estados GPS del día"
    else:
        tbl = gps_weekly_team_table(gps_df, week_ws)
        if tbl.empty:
            return go.Figure()
        source = tbl["weekly_status"].value_counts().reset_index()
        source.columns = ["Estado","N"]
        title = "Distribución de estados GPS semanal"
    cmap = {"Adecuado":"#16A34A","Bajo":"#F59E0B","Alto":"#DC2626","Sin referencia":"#94A3B8"}
    fig = px.pie(source, names="Estado", values="N", color="Estado", color_discrete_map=cmap, title=title, hole=0.45)
    fig.update_layout(height=340, margin=dict(l=20,r=20,t=60,b=20), title_x=0.5)
    return fig

def player_session_html(row, player_df, session_df, gps_df=None):
    main, pattern, worst_metric, worst_value = infer_fatigue_profile(row)
    flags = flags_for_player(player_df, row)
    decision = professional_decision(row["Jugador"], row["Fecha"], globals().get("LAST_METRICS_DF", player_df), globals().get("LAST_GPS_DF", gps_df if gps_df is not None else pd.DataFrame()))
    ref = gps_reference_info(globals().get("LAST_GPS_DF", gps_df if gps_df is not None else pd.DataFrame()), row["Jugador"])
    hist = player_alert_history(player_df, row["Fecha"])
    flags_html = "".join([f"<li>{f}</li>" for f in flags]) if flags else "<li>Sin flags adicionales</li>"
    rows = ""
    for m in OBJECTIVE_METRICS:
        z_val = row.get(f"{m}_z", np.nan)
        z_txt = "NA" if pd.isna(z_val) else f"{z_val:.2f}"
        rows += f"<tr><td>{LABELS[m]}</td><td>{row.get(m, np.nan):.2f}</td><td>{row.get(f'{m}_baseline', np.nan):.2f}</td><td>{row.get(f'{m}_pct_vs_baseline', np.nan):.1f}%</td><td>{z_txt}</td><td>{row.get(f'{m}_severity', 'Sin referencia')}</td></tr>"
    radar_html = plotly_html(radar_current_vs_baseline(row))
    snapshot_html = plotly_html(radar_relative_loss(row))
    timeline_html = plotly_html(plot_objective_timeline(player_df, row["Fecha"]))
    snap_cmp = plotly_html(plot_player_snapshot_compare(row))
    gps_block = gps_player_report_html(row["Jugador"], gps_df, row["Fecha"]) if gps_df is not None else ""
    dec_block = visual_decision_box("Decisión operativa", decision)
    return f"""
    <html><head><meta charset="utf-8">{report_css()}</head><body>
    <div class="hero"><div style="font-size:12px;opacity:0.9;">Informe individual · Sesión específica</div><div style="font-size:32px;font-weight:900;line-height:1.15;">{row['Jugador']}</div><div style="font-size:15px;margin-top:6px;">Fecha: {pd.to_datetime(row['Fecha']).date()}</div></div>
    {dec_block}
    <div class="cards">
      <div class="card"><div class="label">Riesgo</div><div class="value" style="font-size:22px;">{row['risk_label']}</div></div>
      <div class="card"><div class="label">Disponibilidad</div><div class="value" style="font-size:20px;">{decision['availability']}</div></div>
      <div class="card"><div class="label">Referencia GPS</div><div class="value" style="font-size:18px;">{ref['source']}</div></div>
      <div class="card"><div class="label">Partidos válidos</div><div class="value">{ref['qualified_matches']}/{ref['required_matches']}</div></div>
      <div class="card"><div class="label">Readiness</div><div class="value">{row['readiness_score']:.0f}</div></div>
    </div>
    <div class="section"><div class="title">Qué significa hoy</div><div class="diag"><p><b>Perfil principal:</b> {main}.</p><p><b>Patrón:</b> {pattern}.</p><p><b>Variable dominante:</b> {LABELS.get(worst_metric, 'NA')} ({'NA' if worst_value is None else f'{worst_value:.1f}%'}).</p><p><b>Acción recomendada:</b> {decision['action']}.</p><p><b>Motivo:</b> {' · '.join(decision['reasons'][:3])}.</p></div></div>
    <div class="section"><div class="title">Historial de alertas</div><div class="diag">7 días: {hist['alerts7']} · 14 días: {hist['alerts14']} · consecutivas actuales: {hist['consecutive_bad']}</div></div>
    <div class="section"><div class="title">Flags automáticos</div><ul>{flags_html}</ul></div>
    <div class="section"><div class="title">Panel visual</div><div class="grid2">{radar_html}{snapshot_html}</div><div class="grid2">{snap_cmp}{timeline_html}</div></div>
    {gps_block}
    <div class="section"><div class="title">Detalle de variables</div><table class="report-table"><thead><tr><th>Métrica</th><th>Valor</th><th>Baseline</th><th>% vs baseline</th><th>Z-score</th><th>Estado</th></tr></thead><tbody>{rows}</tbody></table></div>
    </body></html>
    """

def player_weekly_html(player, player_df, gps_df, week_ws):
    week_ws = pd.to_datetime(week_ws)
    week_we = week_ws + pd.Timedelta(days=6)
    fat = player_df[(player_df["Fecha"] >= week_ws) & (player_df["Fecha"] <= week_we)].copy() if player_df is not None and not player_df.empty else pd.DataFrame()
    gps_week = gps_player_week_table(gps_df, player, week_ws) if gps_df is not None else pd.DataFrame()
    ref = gps_reference_info(gps_df, player)
    decision = professional_decision(player, week_ws, globals().get("LAST_METRICS_DF", player_df), globals().get("LAST_GPS_DF", gps_df if gps_df is not None else pd.DataFrame()))
    hist = player_alert_history(player_df, week_we) if player_df is not None and not player_df.empty else {"alerts7":0,"alerts14":0,"consecutive_bad":0}
    week_fig = plotly_html(plot_week_session_summary(fat, title="Evolución semanal de fatiga")) if not fat.empty else "<div class='muted'>Sin datos de control de fatiga esta semana.</div>"
    timeline_fig = plotly_html(plot_objective_timeline(player_df, week_we)) if player_df is not None and not player_df.empty else ""
    gps_week_html = gps_progress_bars_html(gps_week, "Resumen GPS semanal")
    gps_week_fig = plotly_html(plot_player_gps_support(gps_week, "Apoyo visual GPS semanal")) if not gps_week.empty else ""
    last_session_html = ""
    if gps_df is not None:
        session_options = session_options_for_week(fat, gps_df[gps_df["Jugador"] == player].copy() if not gps_df is None and not gps_df.empty else pd.DataFrame(), week_ws, player=player)
        if session_options:
            d, md = [x.strip() for x in session_options[-1].split("|",1)]
            gps_sess = gps_player_session_table(gps_df, player, pd.to_datetime(d), micro=md)
            last_session_html = gps_progress_bars_html(gps_sess, f"Última sesión GPS de la semana ({d} · {md})")
    metric_blocks = ""
    if player_df is not None and not player_df.empty:
        for m in OBJECTIVE_METRICS:
            metric_blocks += f"<div class='grid2'>{plotly_html(plot_metric_main(player_df, m, week_we))}{plotly_html(plot_metric_pct(player_df, m, week_we))}</div>"
    return f"""<html><head><meta charset='utf-8'>{report_css()}</head><body>
    <div class='hero'><div style='font-size:12px;opacity:0.9;'>Informe semanal individual · staff</div><div style='font-size:32px;font-weight:900;line-height:1.15;'>{player}</div><div style='font-size:15px;margin-top:6px;'>Semana {week_ws.strftime('%Y-%m-%d')} a {week_we.strftime('%Y-%m-%d')}</div></div>
    {visual_decision_box("Decisión semanal", decision)}
    <div class='cards'>
      <div class='card'><div class='label'>Controles fatiga</div><div class='value'>{0 if fat.empty else fat[['Fecha','Microciclo']].drop_duplicates().shape[0]}</div></div>
      <div class='card'><div class='label'>Readiness media</div><div class='value'>{'NA' if fat.empty else f"{fat['readiness_score'].mean():.1f}"}</div></div>
      <div class='card'><div class='label'>Loss medio</div><div class='value'>{'NA' if fat.empty else f"{fat['objective_loss_score'].mean():.2f}"}</div></div>
      <div class='card'><div class='label'>GPS semanal</div><div class='value'>{'NA' if gps_week.empty else f"{pd.to_numeric(gps_week['pct'], errors='coerce').mean():.1f}%"}</div></div>
      <div class='card'><div class='label'>Alertas 14 días</div><div class='value'>{hist['alerts14']}</div></div>
    </div>
    <div class='section'><div class='title'>Control de fatiga semanal</div>{week_fig}{timeline_fig}</div>
    <div class='section'><div class='title'>Carga GPS semanal</div>{gps_week_html}{gps_week_fig}{last_session_html}<div class='muted'>Referencia GPS: {ref['source']} · partidos válidos: {ref['qualified_matches']}/{ref['required_matches']}</div></div>
    <div class='section'><div class='title'>Evolución por variable</div>{metric_blocks}</div>
    </body></html>"""

def weekly_global_html(metrics_df, gps_df, week_ws):
    week_ws = pd.to_datetime(week_ws)
    week_we = week_ws + pd.Timedelta(days=6)
    summary = weekly_global_summary(metrics_df, gps_df, week_ws)
    fat = metrics_df[(metrics_df["Fecha"] >= week_ws) & (metrics_df["Fecha"] <= week_we)].copy() if metrics_df is not None and not metrics_df.empty else pd.DataFrame()
    staff = team_staff_table(metrics_df, gps_df, week_ws=week_ws)
    gps_html = plotly_html(plot_team_gps_weekly_support(gps_df, week_ws)) if gps_df is not None and not gps_df.empty else ""
    line_html = plotly_html(plot_line_summary(staff, "GPS semana %", "GPS semanal por líneas")) if not staff.empty else ""
    matrix_html = plotly_html(plot_team_staff_matrix_visual(staff, gps_col="GPS semana %", title="Matriz integrada semanal")) if not staff.empty else ""
    top_rows = ""
    if not staff.empty:
        for _, r in staff.head(12).iterrows():
            top_rows += f"<tr><td>{r['Jugador']}</td><td>{r['Posición']}</td><td>{r['Estado fatiga']}</td><td>{'NA' if pd.isna(r['GPS semana %']) else f'{r['GPS semana %']:.1f}%'}" + f"</td><td>{r['Decisión']}</td><td>{r['Observación']}</td></tr>"
    heat_html = ""
    obj_html = ""
    if not fat.empty:
        last_rows = fat.sort_values("Fecha").groupby("Jugador", as_index=False).last()
        heat_html = plotly_html(plot_team_heatmap(last_rows))
        obj_html = plotly_html(plot_team_objective_bar(last_rows))
    alerts = visual_alert_block(top_alerts_block(metrics_df, gps_df, week_ws=week_ws), "Top alerts semanales")
    return f"""<html><head><meta charset='utf-8'>{report_css()}</head><body>
    <div class='hero'><div style='font-size:12px;opacity:0.9;'>Informe semanal global · staff</div><div style='font-size:32px;font-weight:900;line-height:1.15;'>Semana {week_ws.strftime('%Y-%m-%d')} a {week_we.strftime('%Y-%m-%d')}</div></div>
    {alerts}
    <div class='cards'>
      <div class='card'><div class='label'>Sesiones fatiga</div><div class='value'>{summary['fatigue_sessions']}</div></div>
      <div class='card'><div class='label'>Sesiones GPS</div><div class='value'>{summary['gps_sessions']}</div></div>
      <div class='card'><div class='label'>Readiness media</div><div class='value'>{'NA' if pd.isna(summary['readiness_mean']) else f"{summary['readiness_mean']:.1f}"}</div></div>
      <div class='card'><div class='label'>GPS semanal medio</div><div class='value'>{'NA' if pd.isna(summary['gps_compliance_mean']) else f"{summary['gps_compliance_mean']:.1f}%"}</div></div>
    </div>
    <div class='section'><div class='title'>Conclusión operativa de staff</div><div class='diag'>{integrated_week_text(metrics_df, gps_df, week_ws)}</div></div>
    <div class='section'><div class='title'>Panel semanal global</div><div class='grid2'>{obj_html}{heat_html}</div><div class='grid2'>{gps_html}{line_html}</div><div class='grid1'>{matrix_html}</div></div>
    <div class='section'><div class='title'>Matriz staff semanal</div><table class='report-table'><thead><tr><th>Jugador</th><th>Posición</th><th>Estado fatiga</th><th>GPS semanal</th><th>Decisión</th><th>Observación</th></tr></thead><tbody>{top_rows}</tbody></table></div>
    </body></html>"""

def build_pdf_bytes_player_session(row, player_df, gps_df=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = []
    decision = professional_decision(row["Jugador"], row["Fecha"], globals().get("LAST_METRICS_DF", player_df), globals().get("LAST_GPS_DF", gps_df if gps_df is not None else pd.DataFrame()))
    main, pattern, worst_metric, worst_value = infer_fatigue_profile(row)
    elems.append(Paragraph(f"Informe individual · {row['Jugador']}", styles["TitleDark"]))
    elems.append(Paragraph(f"Sesión: {pd.to_datetime(row['Fecha']).date()} · Decisión: {decision['action']} · Disponibilidad: {decision['availability']}", styles["SmallGrey"]))
    elems.append(Spacer(1, 0.15*cm))
    elems.append(Paragraph("Motivo: " + " · ".join(decision["reasons"][:3]), styles["BodyText"]))
    elems.append(Spacer(1, 0.15*cm))
    for fig in [radar_current_vs_baseline(row), radar_relative_loss(row), plot_player_snapshot_compare(row), plot_objective_timeline(player_df, row["Fecha"])]:
        rl_img = fig_to_rl_image(fig, width_cm=22, height_cm=7)
        if rl_img is not None:
            elems.append(rl_img); elems.append(Spacer(1, 0.15*cm))
    for m in OBJECTIVE_METRICS:
        for fig in [plot_metric_main(player_df, m, row["Fecha"]), plot_metric_pct(player_df, m, row["Fecha"])]:
            rl_img = fig_to_rl_image(fig, width_cm=11.2, height_cm=5.8)
            if rl_img is not None:
                elems.append(rl_img); elems.append(Spacer(1, 0.08*cm))
    if gps_df is not None:
        elems.extend(gps_weekly_pdf_story(row["Jugador"], gps_df, row["Fecha"], styles))
    data = [["Riesgo","Readiness","Loss","Perfil","Variable dominante"] ,[str(row["risk_label"]), f"{row['readiness_score']:.0f}", f"{row['objective_loss_score']:.2f}", main, f"{LABELS.get(worst_metric,'NA')}"]]
    t = Table(data); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F172A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.3,colors.lightgrey)]))
    elems.append(t)
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

def build_pdf_bytes_player_weekly(player, player_df, gps_df, week_ws):
    week_ws = pd.to_datetime(week_ws)
    week_we = week_ws + pd.Timedelta(days=6)
    fat = player_df[(player_df["Fecha"] >= week_ws) & (player_df["Fecha"] <= week_we)].copy() if player_df is not None and not player_df.empty else pd.DataFrame()
    decision = professional_decision(player, week_ws, globals().get("LAST_METRICS_DF", player_df), globals().get("LAST_GPS_DF", gps_df if gps_df is not None else pd.DataFrame()))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = [Paragraph(f"Informe semanal individual · {player}", styles["TitleDark"]), Paragraph(f"Semana {week_ws.strftime('%Y-%m-%d')} a {week_we.strftime('%Y-%m-%d')} · Decisión: {decision['action']}", styles["SmallGrey"]), Spacer(1,0.18*cm), Paragraph("Motivo: " + " · ".join(decision["reasons"][:3]), styles["BodyText"]), Spacer(1,0.18*cm)]
    if not fat.empty:
        for fig in [plot_week_session_summary(fat, title="Evolución semanal"), plot_objective_timeline(player_df, week_we)]:
            img = fig_to_rl_image(fig, width_cm=22, height_cm=7)
            if img is not None:
                elems += [img, Spacer(1,0.15*cm)]
        for m in OBJECTIVE_METRICS:
            img = fig_to_rl_image(plot_metric_pct(player_df, m, week_we), width_cm=11.0, height_cm=5.8)
            if img is not None:
                elems += [img, Spacer(1,0.08*cm)]
    else:
        elems.append(Paragraph("Sin datos de control de fatiga esta semana.", styles["BodyText"]))
    if gps_df is not None:
        elems.extend(gps_weekly_pdf_story(player, gps_df, week_ws, styles))
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

def build_pdf_bytes_weekly_global(metrics_df, gps_df, week_ws):
    week_ws = pd.to_datetime(week_ws)
    week_we = week_ws + pd.Timedelta(days=6)
    summary = weekly_global_summary(metrics_df, gps_df, week_ws)
    fat = metrics_df[(metrics_df["Fecha"] >= week_ws) & (metrics_df["Fecha"] <= week_we)].copy() if metrics_df is not None and not metrics_df.empty else pd.DataFrame()
    staff = team_staff_table(metrics_df, gps_df, week_ws=week_ws)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = [Paragraph("Informe semanal global · staff", styles["TitleDark"]), Paragraph(f"Semana {week_ws.strftime('%Y-%m-%d')} a {week_we.strftime('%Y-%m-%d')}", styles["SmallGrey"]), Spacer(1,0.18*cm)]
    data = [["Sesiones fatiga", str(summary["fatigue_sessions"]), "Sesiones GPS", str(summary["gps_sessions"])], ["Readiness media", "NA" if pd.isna(summary["readiness_mean"]) else f"{summary['readiness_mean']:.1f}", "GPS semanal medio", "NA" if pd.isna(summary["gps_compliance_mean"]) else f"{summary['gps_compliance_mean']:.1f}%"]]
    t = Table(data, colWidths=[4*cm,4*cm,4*cm,4*cm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.whitesmoke),("GRID",(0,0),(-1,-1),0.3,colors.lightgrey)]))
    elems += [t, Spacer(1,0.15*cm), Paragraph(integrated_week_text(metrics_df, gps_df, week_ws), styles["BodyText"]), Spacer(1,0.15*cm)]
    if not fat.empty:
        last_rows = fat.sort_values("Fecha").groupby("Jugador", as_index=False).last()
        for fig in [plot_team_objective_bar(last_rows), plot_team_heatmap(last_rows)]:
            img = fig_to_rl_image(fig, width_cm=22, height_cm=7)
            if img is not None:
                elems += [img, Spacer(1,0.15*cm)]
    if gps_df is not None and not gps_df.empty:
        for fig in [plot_team_gps_weekly_support(gps_df, week_ws), plot_team_staff_matrix_visual(staff, gps_col="GPS semana %", title="Matriz staff semanal")]:
            img = fig_to_rl_image(fig, width_cm=22, height_cm=7)
            if img is not None:
                elems += [img, Spacer(1,0.15*cm)]
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

def build_pdf_bytes_team_session(team_day, selected_date, gps_df=None):
    gps_df = ensure_gps_datetime(gps_df)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.0*cm, rightMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = report_styles()
    elems = [Paragraph("Informe de sesión · staff", styles["TitleDark"]), Paragraph(f"Fecha analizada: {selected_date}", styles["SmallGrey"]), Spacer(1,0.15*cm), Paragraph(team_interpretation(team_day), styles["BodyText"]), Spacer(1,0.15*cm)]
    for fig in [plot_team_risk_distribution(team_day), plot_team_objective_bar(team_day), plot_team_heatmap(team_day)]:
        img = fig_to_rl_image(fig, width_cm=22, height_cm=7)
        if img is not None:
            elems += [img, Spacer(1,0.12*cm)]
    if gps_df is not None:
        gday = gps_compute_compliance(gps_df[(gps_df["Fecha"].dt.strftime("%Y-%m-%d")==str(selected_date)) & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")].copy(), reference_df=gps_df)
        if not gday.empty:
            for fig in [plot_team_gps_support(gday), plot_team_gps_status_distribution(gps_df, selected_date=selected_date)]:
                img = fig_to_rl_image(fig, width_cm=22, height_cm=7)
                if img is not None:
                    elems += [img, Spacer(1,0.12*cm)]
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

def page_equipo(metrics_df, gps_df):
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return

    st.markdown('<div class="hero"><div style="font-size:0.92rem; opacity:0.9;">Monitorización neuromuscular + GPS</div><div style="font-size:2.05rem; font-weight:900; margin-top:0.15rem;">Equipo</div><div style="font-size:1rem; opacity:0.92; margin-top:0.4rem;">Panel operativo central del staff · resumen → decisión → visual → detalle.</div></div>', unsafe_allow_html=True)

    week_labels, week_map = build_week_options(metrics_df, gps_df)
    if not week_labels:
        st.info("No hay semanas disponibles.")
        return
    cquick1, cquick2 = st.columns([1,4])
    with cquick1:
        if st.button("Última semana", key="equipo_last_week_btn_v3"):
            st.session_state["equipo_week_label_v3"] = week_labels[-1]
    wk_default = st.session_state.get("equipo_week_label_v3", week_labels[-1])
    wk_idx = week_labels.index(wk_default) if wk_default in week_labels else len(week_labels)-1
    wk_label = st.selectbox("Semana (lunes-domingo)", week_labels, index=wk_idx, key="equipo_week_v3")
    week_ws = week_map[wk_label]
    view_mode = st.radio("Vista", ["Resumen semanal","Sesión concreta"], horizontal=True, key="equipo_view_v3")
    focus = st.radio("Enfoque", ["Integrado","Fatiga","GPS"], horizontal=True, key="equipo_focus_v3")

    gps_df = ensure_gps_datetime(gps_df)
    week_we = week_ws + pd.Timedelta(days=6)
    week_fat = metrics_df[(metrics_df["Fecha"] >= week_ws) & (metrics_df["Fecha"] <= week_we)].copy() if not metrics_df.empty else pd.DataFrame()
    week_gps_raw = gps_df[(gps_df["Fecha"] >= week_ws) & (gps_df["Fecha"] <= week_we) & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")].copy() if not gps_df.empty else pd.DataFrame()
    week_gps = gps_compute_compliance(week_gps_raw, reference_df=gps_df) if not week_gps_raw.empty else pd.DataFrame()

    if view_mode == "Resumen semanal":
        summary = weekly_global_summary(metrics_df, gps_df, week_ws)
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Sesiones fatiga", summary["fatigue_sessions"], "semana")
        with c2: kpi("Sesiones GPS", summary["gps_sessions"], "semana")
        with c3: kpi("Readiness media", "NA" if pd.isna(summary["readiness_mean"]) else f"{summary['readiness_mean']:.1f}", "semana")
        with c4: kpi("GPS semanal medio", "NA" if pd.isna(summary["gps_compliance_mean"]) else f"{summary['gps_compliance_mean']:.1f}%", "semana")

        collective_dec = {
            "action": "Ajustar carga" if (pd.notna(summary["readiness_mean"]) and summary["readiness_mean"] < 70) or (pd.notna(summary["gps_compliance_mean"]) and summary["gps_compliance_mean"] < 75) else "Disponible con control",
            "reasons": [integrated_week_text(metrics_df, gps_df, week_ws)],
            "context": f"Semana {wk_label}",
            "reference_source": "colectiva",
            "qualified_matches": 0,
            "required_matches": GPS_MATCH_MIN_MATCHES,
            "last_valid_match": pd.NaT,
            "color": "#F59E0B" if (pd.notna(summary["readiness_mean"]) and summary["readiness_mean"] < 70) or (pd.notna(summary["gps_compliance_mean"]) and summary["gps_compliance_mean"] < 75) else "#16A34A"
        }
        st.markdown(visual_decision_box("Bloque de decisión semanal", collective_dec), unsafe_allow_html=True)

        alert_lines = top_alerts_block(metrics_df, gps_df, week_ws=week_ws)
        if alert_lines:
            st.markdown(visual_alert_block(alert_lines, "Top alerts semanales"), unsafe_allow_html=True)

        staff_week = team_staff_table(metrics_df, gps_df, week_ws=week_ws)
        if not staff_week.empty:
            st.markdown("### Matriz integrada de staff")
            st.dataframe(style_staff_table(staff_week[["Jugador","Posición","Línea","Estado fatiga","Readiness","GPS semana %","Carga-respuesta","Decisión","Observación"]], sort_col="GPS semana %"), use_container_width=True, hide_index=True)

        if not week_fat.empty:
            last_rows = week_fat.sort_values("Fecha").groupby("Jugador", as_index=False).last()
        else:
            last_rows = pd.DataFrame()

        if focus in ["Integrado","Fatiga"] and not last_rows.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_objective_bar(last_rows), use_container_width=True)
            with b: st.plotly_chart(plot_team_heatmap(last_rows), use_container_width=True)
            c,d = st.columns(2)
            with c: st.plotly_chart(plot_team_risk_distribution(last_rows), use_container_width=True)
            with d: st.plotly_chart(plot_week_session_summary(week_fat, title="Resumen semanal por sesiones"), use_container_width=True)

        if focus in ["Integrado","GPS"] and not week_gps.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_gps_weekly_support(gps_df, week_ws), use_container_width=True)
            with b: st.plotly_chart(plot_team_gps_status_distribution(gps_df, week_ws=week_ws), use_container_width=True)
            if not staff_week.empty:
                c,d = st.columns(2)
                with c: st.plotly_chart(plot_line_summary(staff_week, "GPS semana %", "GPS semanal por líneas"), use_container_width=True)
                with d: st.plotly_chart(plot_team_staff_matrix_visual(staff_week, gps_col="GPS semana %", title="Matriz integrada semanal"), use_container_width=True)

    else:
        sess_opts = session_options_for_week(metrics_df, gps_df, week_ws)
        if not sess_opts:
            st.info("No hay sesiones en esa semana.")
            return
        sess_label = st.selectbox("Sesión de la semana", sess_opts, key="equipo_sesion_v3")
        sess_date_str, sess_md = [x.strip() for x in sess_label.split("|", 1)]
        selected_date = pd.to_datetime(sess_date_str)
        team_day = week_fat[(week_fat["Fecha"].dt.normalize() == selected_date.normalize())].copy() if not week_fat.empty else pd.DataFrame()
        if sess_md != "Sin día" and not team_day.empty:
            team_day = team_day[team_day["Microciclo"].fillna("Sin día").astype(str) == sess_md]
        gps_day = week_gps[(week_gps["Fecha"].dt.normalize() == selected_date.normalize()) & (week_gps["Microciclo"].astype(str) == sess_md)].copy() if not week_gps.empty else pd.DataFrame()

        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: kpi("Fecha", selected_date.strftime("%Y-%m-%d"), sess_md)
        with c2: kpi("Jugadores fatiga", int(team_day["Jugador"].nunique()) if not team_day.empty else 0, "sesión")
        with c3: kpi("Readiness media", "NA" if team_day.empty else f"{team_day['readiness_score'].mean():.1f}", "sesión")
        with c4: kpi("GPS medio", "NA" if gps_day.empty else f"{gps_day['compliance_score'].mean():.1f}%", "sesión")
        with c5: kpi("Críticos", int((team_day["risk_label"] == "Fatiga crítica").sum()) if not team_day.empty else 0, "sesión")

        collective_dec = {
            "action": "Ajustar carga" if not team_day.empty and team_day["objective_loss_score"].mean() >= 1 else "Disponible con control",
            "reasons": [team_interpretation(team_day)] if not team_day.empty else ["Sin datos de fatiga para esta sesión"],
            "context": integrated_week_text(metrics_df, gps_df, selected_date),
            "reference_source": "colectiva",
            "qualified_matches": 0,
            "required_matches": GPS_MATCH_MIN_MATCHES,
            "last_valid_match": pd.NaT,
            "color": "#F59E0B" if not team_day.empty and team_day["objective_loss_score"].mean() >= 1 else "#16A34A"
        }
        st.markdown(visual_decision_box("Bloque de decisión del día", collective_dec), unsafe_allow_html=True)

        alert_lines = top_alerts_block(metrics_df, gps_df, selected_date=selected_date)
        if alert_lines:
            st.markdown(visual_alert_block(alert_lines, "Top alerts del día"), unsafe_allow_html=True)

        staff_day = team_staff_table(metrics_df, gps_df, selected_date=selected_date, session_micro=sess_md)
        if not staff_day.empty:
            st.markdown("### Matriz integrada de staff")
            st.dataframe(style_staff_table(staff_day[["Jugador","Posición","Línea","Estado fatiga","Readiness","GPS día %","GPS semana %","Carga-respuesta","Decisión","Observación"]], sort_col="Readiness"), use_container_width=True, hide_index=True)

        if focus in ["Integrado","Fatiga"] and not team_day.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_objective_bar(team_day), use_container_width=True)
            with b: st.plotly_chart(plot_team_heatmap(team_day), use_container_width=True)
            c,d = st.columns(2)
            with c: st.plotly_chart(plot_team_risk_distribution(team_day), use_container_width=True)
            with d: st.plotly_chart(plot_team_priority_board(team_day), use_container_width=True)

        if focus in ["Integrado","GPS"] and not gps_day.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_gps_support(gps_day), use_container_width=True)
            with b: st.plotly_chart(plot_team_gps_status_distribution(gps_df, selected_date=selected_date), use_container_width=True)
            if not staff_day.empty:
                c,d = st.columns(2)
                with c: st.plotly_chart(plot_line_summary(staff_day, "GPS día %", "GPS del día por líneas"), use_container_width=True)
                with d: st.plotly_chart(plot_team_staff_matrix_visual(staff_day, gps_col="GPS día %", title="Matriz integrada del día"), use_container_width=True)

def page_jugador(metrics_df, gps_df):
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return
    gps_df = ensure_gps_datetime(gps_df)
    player_map = build_player_display_options(metrics_df, gps_df)
    st.markdown('<div class="section-title">Jugador</div>', unsafe_allow_html=True)
    player_label = st.selectbox("Selecciona jugador", list(player_map.keys()), key="player_selector_v3")
    player = player_map[player_label]
    week_labels, week_map = build_week_options(metrics_df, gps_df, player=player)
    if not week_labels:
        st.info("No hay semanas disponibles para este jugador.")
        return
    cquick, _ = st.columns([1,4])
    with cquick:
        if st.button("Última semana", key="player_last_week_v3"):
            st.session_state["player_week_label_v3"] = week_labels[-1]
    wk_default = st.session_state.get("player_week_label_v3", week_labels[-1])
    wk_idx = week_labels.index(wk_default) if wk_default in week_labels else len(week_labels)-1
    wk_label = st.selectbox("Semana (lunes-domingo)", week_labels, index=wk_idx, key="player_week_v3")
    week_ws = week_map[wk_label]
    view_mode = st.radio("Vista", ["Resumen semanal","Sesión concreta"], horizontal=True, key="player_view_v3")

    player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame()
    player_gps = gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame()
    ref = gps_reference_info(gps_df, player)
    selected_anchor = week_ws if view_mode == "Resumen semanal" else (latest_nonmatch_date(player_df, player_gps, player=player) or week_ws)
    decision = professional_decision(player, selected_anchor, metrics_df, gps_df)
    last_match = pd.to_datetime(decision["last_valid_match"]).strftime("%Y-%m-%d") if pd.notna(decision["last_valid_match"]) else "NA"

    st.markdown(
        f'<div class="card"><div style="font-size:1.95rem;font-weight:900;color:#101828;">{player_label.replace(" - ", " · ")}</div>'
        f'<div style="margin-top:0.55rem;"><span class="pill" style="background:{decision["color"]};">{decision["action"]}</span></div>'
        f'<div style="margin-top:0.7rem;color:#475467;"><b>Contexto:</b> {decision["context"]} · <b>Carga-respuesta:</b> {decision["load_response"]}</div>'
        f'<div style="margin-top:0.35rem;color:#475467;"><b>Referencia GPS:</b> {ref["source"]} · <b>Partidos válidos:</b> {ref["qualified_matches"]}/{ref["required_matches"]} · <b>Último partido válido:</b> {last_match}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    tabs = st.tabs(["Diagnóstico","GPS","Tendencia","Informes rápidos"])
    week_we = week_ws + pd.Timedelta(days=6)
    player_week_fat = player_df[(player_df["Fecha"] >= week_ws) & (player_df["Fecha"] <= week_we)].copy() if not player_df.empty else pd.DataFrame()
    player_week_gps = gps_player_week_table(gps_df, player, week_ws) if not player_gps.empty else pd.DataFrame()
    row = None; session_gps = pd.DataFrame(); selected_date = week_ws; sess_md = "Semanal"
    if view_mode == "Sesión concreta":
        sess_opts = session_options_for_week(metrics_df, gps_df, week_ws, player=player)
        if not sess_opts:
            st.info("No hay sesiones en esa semana.")
            return
        sess_label = st.selectbox("Sesión de la semana", sess_opts, key="player_sess_v3")
        sess_date_str, sess_md = [x.strip() for x in sess_label.split("|", 1)]
        selected_date = pd.to_datetime(sess_date_str)
        current = player_df[player_df["Fecha"].dt.normalize() == selected_date.normalize()] if not player_df.empty else pd.DataFrame()
        row = current.iloc[-1] if not current.empty else None
        session_gps = gps_player_session_table(gps_df, player, selected_date, micro=sess_md) if not player_gps.empty else pd.DataFrame()
        decision = professional_decision(player, selected_date, metrics_df, gps_df)

    with tabs[0]:
        if view_mode == "Resumen semanal":
            c1,c2,c3,c4 = st.columns(4)
            with c1: kpi("Controles fatiga", int(player_week_fat[["Fecha","Microciclo"]].drop_duplicates().shape[0]) if not player_week_fat.empty else 0, "semana")
            with c2: kpi("Readiness sem.", "NA" if player_week_fat.empty else f"{player_week_fat['readiness_score'].mean():.1f}", "media")
            with c3: kpi("GPS sem.", "NA" if player_week_gps.empty else f"{pd.to_numeric(player_week_gps['pct'], errors='coerce').mean():.1f}%", "media")
            with c4: kpi("Decisión", decision["action"], decision["availability"])
            st.markdown(visual_decision_box("Bloque de decisión semanal", decision), unsafe_allow_html=True)
            hist = player_alert_history(player_df, week_we)
            st.info(f"Historial de alertas · 7 días: {hist['alerts7']} · 14 días: {hist['alerts14']} · consecutivas: {hist['consecutive_bad']}")
            if not player_week_fat.empty:
                a,b = st.columns(2)
                with a: st.plotly_chart(plot_week_session_summary(player_week_fat, title="Fatiga semanal por sesiones"), use_container_width=True)
                with b: st.plotly_chart(plot_player_integrated_week_dashboard(player, week_ws, metrics_df, gps_df), use_container_width=True)
        else:
            if row is None:
                st.warning("No hay datos de control de fatiga para esta sesión.")
            else:
                c1,c2,c3,c4,c5 = st.columns(5)
                with c1: kpi("Fecha", selected_date.strftime("%Y-%m-%d"), sess_md)
                with c2: kpi("Riesgo", row["risk_label"], "clasificación")
                with c3: kpi("Loss", f"{row['objective_loss_score']:.2f}", "0-3")
                with c4: kpi("Readiness", f"{row['readiness_score']:.0f}", "día")
                with c5: kpi("Decisión", decision["action"], decision["availability"])
                st.markdown(visual_decision_box("Bloque de decisión del día", decision), unsafe_allow_html=True)
                main, pattern, worst_metric, worst_value = infer_fatigue_profile(row)
                st.markdown(f"**Qué significa hoy:** {main}, con {pattern}. Variable dominante: {LABELS.get(worst_metric, 'NA')} ({'NA' if worst_value is None else f'{worst_value:.1f}%'}). **Acción recomendada:** {decision['action']}. **Motivo:** {' · '.join(decision['reasons'][:3])}.")
                a,b = st.columns(2)
                with a: st.plotly_chart(radar_relative_loss(row), use_container_width=True)
                with b: st.plotly_chart(radar_current_vs_baseline(row), use_container_width=True)
                c,d = st.columns(2)
                with c: st.plotly_chart(plot_player_snapshot_compare(row), use_container_width=True)
                with d: st.plotly_chart(plot_objective_timeline(player_df, selected_date), use_container_width=True)

    with tabs[1]:
        if view_mode == "Resumen semanal":
            if player_week_gps.empty:
                st.info("Sin GPS semanal disponible.")
            else:
                gps_progress_bars_streamlit(player_week_gps, "Resumen GPS semanal")
                a,b = st.columns(2)
                with a: st.plotly_chart(plot_player_gps_support(player_week_gps, "Apoyo visual GPS semanal"), use_container_width=True)
                with b: st.plotly_chart(plot_player_gps_support(player_week_gps, "Distribución GPS semanal"), use_container_width=True)
                st.caption(f"Referencia GPS usada: {ref['source']} · partidos válidos: {ref['qualified_matches']}/{ref['required_matches']}")
        else:
            if session_gps.empty:
                st.info("Sin GPS del día disponible.")
            else:
                gps_progress_bars_streamlit(session_gps, "Cumplimiento GPS del día")
                st.plotly_chart(plot_player_gps_support(session_gps, "Apoyo visual GPS del día"), use_container_width=True)
                sess_tbl = session_gps[["Variable","pct","min","max","status"]].copy()
                sess_tbl.columns = ["Variable","% sesión vs partido","Objetivo mínimo (%)","Objetivo máximo (%)","Interpretación"]
                st.dataframe(sess_tbl.round(1), use_container_width=True, hide_index=True)
                st.caption(f"Referencia GPS usada: {ref['source']} · partidos válidos: {ref['qualified_matches']}/{ref['required_matches']} · último partido válido: {last_match}")

    with tabs[2]:
        if player_df.empty:
            st.info("Sin datos longitudinales.")
        else:
            anchor_date = week_we if view_mode == "Resumen semanal" else selected_date
            st.plotly_chart(plot_objective_timeline(player_df, anchor_date), use_container_width=True)
            for m in OBJECTIVE_METRICS:
                l, rcol = st.columns(2)
                with l: st.plotly_chart(plot_metric_main(player_df, m, anchor_date), use_container_width=True)
                with rcol: st.plotly_chart(plot_metric_pct(player_df, m, anchor_date), use_container_width=True)

    with tabs[3]:
        st.markdown(f"- **Estado actual:** {decision['action']}")
        st.markdown(f"- **Disponibilidad:** {decision['availability']}")
        st.markdown(f"- **Motivo principal:** {' · '.join(decision['reasons'][:3])}")
        st.markdown(f"- **Referencia GPS:** {ref['source']} · {ref['qualified_matches']}/{ref['required_matches']} partidos válidos")

def page_informes(metrics_df, gps_df):
    gps_df = ensure_gps_datetime(gps_df)
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return
    st.markdown('<div class="section-title">Informes descargables</div>', unsafe_allow_html=True)
    player_map = build_player_display_options(metrics_df, gps_df)
    tab1,tab2,tab3,tab4,tab5 = st.tabs(["Informe individual staff anual","Informe individual staff por sesión","Informe semanal integrado jugador","Informe entrenador sesión","Informe semanal global"])

    with tab1:
        player_label = st.selectbox("Jugador · informe anual", list(player_map.keys()), key="yr_v3")
        player = player_map[player_label]
        player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame(columns=["Fecha"])
        if not player_df.empty:
            latest = player_df.iloc[-1]
            st.markdown(f"**Resumen actual:** {latest['risk_label']} · loss {latest['objective_loss_score']:.2f} · readiness {latest['readiness_score']:.0f}")
            html = player_season_html(player_df, player, gps_df=gps_df)
            st.download_button("Descargar HTML anual", data=html.encode("utf-8"), file_name=f"informe_anual_{player.replace(' ','_')}.html", mime="text/html")
            st.download_button("Descargar PDF anual", data=build_pdf_bytes_player_season(player_df, player, gps_df=gps_df), file_name=f"informe_anual_{player.replace(' ','_')}.pdf", mime="application/pdf")

    with tab2:
        player_label = st.selectbox("Jugador · informe sesión", list(player_map.keys()), key="ses_v3")
        player = player_map[player_label]
        source_dates = sorted(set(([pd.to_datetime(d).strftime("%Y-%m-%d") for d in metrics_df[metrics_df["Jugador"] == player]["Fecha"].dropna().unique()] if not metrics_df.empty else []) + ([pd.to_datetime(d).strftime("%Y-%m-%d") for d in gps_df[gps_df["Jugador"] == player]["Fecha"].dropna().unique()] if not gps_df.empty else [])))
        if source_dates:
            sel_date = st.selectbox("Fecha sesión", source_dates, key="sesd_v3")
            player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame()
            session_df = player_df[player_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date].copy() if not player_df.empty else pd.DataFrame()
            gps_only_df = gps_df[(gps_df["Jugador"] == player) & (gps_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date)] if not gps_df.empty else pd.DataFrame()
            if not session_df.empty:
                row = session_df.iloc[-1]
                html = player_session_html(row, player_df, session_df, gps_df=gps_df)
                st.download_button("Descargar HTML sesión", data=html.encode("utf-8"), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.html", mime="text/html")
                st.download_button("Descargar PDF sesión", data=build_pdf_bytes_player_session(row, player_df, gps_df=gps_df), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.pdf", mime="application/pdf")
            elif not gps_only_df.empty:
                html = f"<html><head><meta charset='utf-8'>{report_css()}</head><body><div class='hero'><div style='font-size:12px;opacity:0.9;'>Informe individual · Sesión específica</div><div style='font-size:32px;font-weight:900;line-height:1.15;'>{player}</div><div style='font-size:15px;margin-top:6px;'>Fecha: {sel_date}</div></div><div class='section'><div class='title'>Observación</div><div class='diag'>No hay datos de control de fatiga para esta fecha. Se muestran únicamente los datos GPS disponibles.</div></div>{gps_player_report_html(player, gps_df, pd.to_datetime(sel_date))}</body></html>"
                st.download_button("Descargar HTML sesión", data=html.encode("utf-8"), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.html", mime="text/html")
                st.download_button("Descargar PDF sesión", data=build_pdf_bytes_player_session_gps_only(player, gps_df, pd.to_datetime(sel_date)), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.pdf", mime="application/pdf")
            else:
                st.warning("No hay datos para esa fecha.")

    with tab3:
        player_label = st.selectbox("Jugador · informe semanal", list(player_map.keys()), key="gpswk_v3")
        player = player_map[player_label]
        week_labels, week_map = build_week_options(metrics_df, gps_df, player=player)
        if week_labels:
            wk_label = st.selectbox("Semana de referencia", week_labels, key="gpswkd_v3")
            week_ws = week_map[wk_label]
            html = player_weekly_html(player, metrics_df[metrics_df["Jugador"] == player].copy() if not metrics_df.empty else pd.DataFrame(), gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame(), week_ws)
            st.download_button("Descargar HTML semanal", data=html.encode("utf-8"), file_name=f"informe_semanal_{player.replace(' ','_')}_{pd.to_datetime(week_ws).strftime('%Y%m%d')}.html", mime="text/html")
            st.download_button("Descargar PDF semanal", data=build_pdf_bytes_player_weekly(player, metrics_df[metrics_df["Jugador"] == player].copy() if not metrics_df.empty else pd.DataFrame(), gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame(), week_ws), file_name=f"informe_semanal_{player.replace(' ','_')}_{pd.to_datetime(week_ws).strftime('%Y%m%d')}.pdf", mime="application/pdf")

    with tab4:
        all_week_labels, all_week_map = build_week_options(metrics_df, gps_df)
        if all_week_labels:
            wk_label = st.selectbox("Semana sesión global", all_week_labels, key="teamwk_v3")
            week_ws = all_week_map[wk_label]
            sess_opts = session_options_for_week(metrics_df, gps_df, week_ws)
            if sess_opts:
                sess_label = st.selectbox("Sesión global", sess_opts, key="teamr_v3")
                sel_date, sel_md = [x.strip() for x in sess_label.split("|", 1)]
                team_day = metrics_df[(metrics_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date)].copy() if not metrics_df.empty else pd.DataFrame()
                if sel_md != "Sin día" and not team_day.empty:
                    team_day = team_day[team_day["Microciclo"].fillna("Sin día").astype(str) == sel_md]
                if not team_day.empty:
                    html = coach_session_html(team_day, sel_date, gps_df=gps_df)
                    st.download_button("Descargar HTML entrenador", data=html.encode("utf-8"), file_name=f"informe_equipo_sesion_{sel_date}.html", mime="text/html")
                    st.download_button("Descargar PDF entrenador", data=build_pdf_bytes_team_session(team_day, sel_date, gps_df=gps_df), file_name=f"informe_equipo_sesion_{sel_date}.pdf", mime="application/pdf")

    with tab5:
        all_week_labels, all_week_map = build_week_options(metrics_df, gps_df)
        if all_week_labels:
            wk_label = st.selectbox("Semana informe global", all_week_labels, key="globalwk_v3")
            week_ws = all_week_map[wk_label]
            html = weekly_global_html(metrics_df, gps_df, week_ws)
            st.download_button("Descargar HTML semanal global", data=html.encode("utf-8"), file_name=f"informe_global_semanal_{pd.to_datetime(week_ws).strftime('%Y%m%d')}.html", mime="text/html")
            st.download_button("Descargar PDF semanal global", data=build_pdf_bytes_weekly_global(metrics_df, gps_df, week_ws), file_name=f"informe_global_semanal_{pd.to_datetime(week_ws).strftime('%Y%m%d')}.pdf", mime="application/pdf")

def main():
    init_db()
    st.sidebar.markdown("## Staff dashboard")
    st.sidebar.caption("Versión staff profesional: foco en decisión, visualización, GPS y profundidad de informes.")
    base_df = standardize_player_names_in_frames(load_monitoring())
    gps_df = standardize_player_names_in_frames(load_gps())
    metrics_df = compute_metrics(base_df) if not base_df.empty else base_df.copy()
    globals()["LAST_METRICS_DF"] = metrics_df
    globals()["LAST_GPS_DF"] = gps_df

    menu = st.sidebar.radio("Sección", ["Cargar datos","Equipo","Jugador","Informes","Administración"], key="main_menu_v3")
    if menu == "Cargar datos":
        page_cargar()
    elif menu == "Equipo":
        page_equipo(metrics_df, gps_df)
    elif menu == "Jugador":
        page_jugador(metrics_df, gps_df)
    elif menu == "Informes":
        page_informes(metrics_df, gps_df)
    else:
        page_admin(base_df, gps_df)



# =========================================================
# PROFESSIONAL ENHANCEMENTS V4
# =========================================================
def delete_gps_match(date_str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM gps_data WHERE Fecha = ? AND UPPER(Microciclo) = 'PARTIDO'", (date_str,))
    conn.commit()
    conn.close()

def line_group_from_position(pos):
    pos = str(pos) if pd.notna(pos) else "Sin asignar"
    if pos in ["Lateral", "Central"]:
        return "Defensas"
    if pos == "Mediocentro":
        return "Mediocentros"
    if pos == "Delantero":
        return "Atacantes"
    if pos == "Portero":
        return "Porteros"
    return "Sin asignar"

def gps_reference_info(gps_df, player):
    gps_df = ensure_gps_datetime(gps_df)
    info = {
        "source": "Sin referencia",
        "qualified_matches": 0,
        "required_matches": GPS_MATCH_MIN_MATCHES,
        "last_valid_match": pd.NaT,
        "position": get_player_position(player, None, gps_df),
    }
    if gps_df.empty:
        return info
    prof = build_match_profile(gps_df)
    row = prof[prof["Jugador"] == player]
    if not row.empty:
        row = row.iloc[0]
        src = str(row.get("profile_source", "")).lower()
        info["source"] = "perfil propio" if src == "propio" else f"media de {str(info['position']).lower()}s"
        info["qualified_matches"] = int(row.get("qualified_matches", 0) if pd.notna(row.get("qualified_matches", 0)) else 0)
    valid_matches = gps_df[
        (gps_df["Jugador"] == player)
        & (gps_df["Microciclo"].astype(str).str.upper() == "PARTIDO")
        & (pd.to_numeric(gps_df.get("time_played", np.nan), errors="coerce") >= GPS_MATCH_MINUTES_MIN)
    ].copy()
    if not valid_matches.empty:
        info["last_valid_match"] = pd.to_datetime(valid_matches["Fecha"].max())
    return info

def professional_decision(player, selected_date, metrics_df, gps_df):
    selected_date = pd.to_datetime(selected_date)
    snap = compute_integrated_player_snapshot(player, selected_date, metrics_df, gps_df)
    ref = gps_reference_info(gps_df, player)
    reasons = []
    action = {
        "Intervención individual": "Individualizar",
        "Reducir exposición": "Reducir exposición",
        "Ajustar carga": "Ajustar carga",
        "Disponible con control": "Disponible con control",
        "Disponible normal": "Disponible normal",
        "Sin datos": "Reevaluar",
    }.get(snap.get("integrated_decision", "Reevaluar"), snap.get("integrated_decision", "Reevaluar"))

    fat_row = None
    if metrics_df is not None and not metrics_df.empty:
        day = metrics_df[(metrics_df["Jugador"] == player) & (pd.to_datetime(metrics_df["Fecha"]).dt.normalize() == selected_date.normalize())]
        if not day.empty:
            fat_row = day.sort_values("Fecha").iloc[-1]
            risk = fat_row.get("risk_label", "Sin dato")
            readiness = fat_row.get("readiness_score", np.nan)
            if pd.notna(readiness) and readiness < 60:
                reasons.append(f"Readiness bajo ({readiness:.0f})")
            if risk in ["Fatiga moderada", "Fatiga moderada-alta", "Fatiga crítica"]:
                reasons.append(f"Riesgo {risk.lower()}")
            if fat_row.get("trend_label", "") == "Empeorando":
                reasons.append("tendencia reciente negativa")
            if fat_row.get("recent_alerts_14d", 0) >= 2:
                reasons.append("persistencia de alertas")
    gd = snap.get("gps_day_compliance", np.nan)
    gw = snap.get("gps_week_compliance", np.nan)
    if pd.notna(gd):
        if gd < 70:
            reasons.append(f"GPS del día bajo ({gd:.1f}%)")
        elif gd > 115:
            reasons.append(f"GPS del día alto ({gd:.1f}%)")
    if pd.notna(gw):
        if gw < 75:
            reasons.append(f"GPS semanal bajo ({gw:.1f}%)")
        elif gw > 110:
            reasons.append(f"GPS semanal alto ({gw:.1f}%)")
    if snap.get("load_response_label") not in [None, "", "Relación carga-respuesta estable"]:
        reasons.append(str(snap.get("load_response_label")).lower())

    if fat_row is None and pd.isna(gd) and pd.isna(gw):
        action = "Reevaluar"
        reasons = ["sin datos objetivos suficientes para decidir"]

    if not reasons:
        reasons = ["respuesta estable", "sin alertas acumuladas relevantes"]

    availability = {
        "Disponible normal": "Apto normal",
        "Disponible con control": "Apto con control",
        "Ajustar carga": "Exposición reducida",
        "Reducir exposición": "Exposición reducida",
        "Individualizar": "Individualizar",
        "Reevaluar": "Reevaluar en calentamiento",
    }.get(action, "Apto normal")

    color = {
        "Disponible normal": "#16A34A",
        "Disponible con control": "#EAB308",
        "Ajustar carga": "#F59E0B",
        "Reducir exposición": "#F97316",
        "Individualizar": "#DC2626",
        "Reevaluar": "#94A3B8",
    }.get(action, "#94A3B8")

    return {
        "action": action,
        "availability": availability,
        "reasons": reasons,
        "color": color,
        "context": snap.get("context_label", "Sin contexto"),
        "load_response": snap.get("load_response_label", "Sin relación carga-respuesta"),
        "gps_day": gd,
        "gps_week": gw,
        "weekly_alerts": snap.get("weekly_alerts", 0),
        "reference_source": ref["source"],
        "qualified_matches": ref["qualified_matches"],
        "required_matches": ref["required_matches"],
        "last_valid_match": ref["last_valid_match"],
    }

def team_staff_table(metrics_df, gps_df, selected_date=None, week_ws=None, session_micro=None):
    metrics_df = metrics_df.copy() if metrics_df is not None else pd.DataFrame()
    gps_df = ensure_gps_datetime(gps_df)
    rows = []
    players = set()

    if selected_date is not None:
        selected_date = pd.to_datetime(selected_date)
        if not metrics_df.empty:
            day_f = metrics_df[pd.to_datetime(metrics_df["Fecha"]).dt.normalize() == selected_date.normalize()]
            if session_micro is not None:
                day_f = day_f[day_f["Microciclo"].fillna("Sin día").astype(str) == str(session_micro)]
            players.update(day_f["Jugador"].dropna().tolist())
        if not gps_df.empty:
            day_g = gps_df[(gps_df["Fecha"].dt.normalize() == selected_date.normalize()) & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")]
            if session_micro is not None:
                day_g = day_g[day_g["Microciclo"].astype(str) == str(session_micro)]
            players.update(day_g["Jugador"].dropna().tolist())
    elif week_ws is not None:
        week_ws = pd.to_datetime(week_ws)
        week_we = week_ws + pd.Timedelta(days=6)
        if not metrics_df.empty:
            wkf = metrics_df[(pd.to_datetime(metrics_df["Fecha"]) >= week_ws) & (pd.to_datetime(metrics_df["Fecha"]) <= week_we)]
            players.update(wkf["Jugador"].dropna().tolist())
        if not gps_df.empty:
            wkg = gps_df[(gps_df["Fecha"] >= week_ws) & (gps_df["Fecha"] <= week_we) & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")]
            players.update(wkg["Jugador"].dropna().tolist())

    for player in sorted(players):
        pos = get_player_position(player, metrics_df, gps_df)
        line = line_group_from_position(pos)
        ref = gps_reference_info(gps_df, player)
        decision = professional_decision(player, selected_date if selected_date is not None else week_ws, metrics_df, gps_df)

        fat_state, readiness, obs = "Sin dato", np.nan, ""
        if selected_date is not None and not metrics_df.empty:
            pday = metrics_df[(metrics_df["Jugador"] == player) & (pd.to_datetime(metrics_df["Fecha"]).dt.normalize() == pd.to_datetime(selected_date).normalize())]
            if session_micro is not None:
                pday = pday[pday["Microciclo"].fillna("Sin día").astype(str) == str(session_micro)]
            if not pday.empty:
                r = pday.sort_values("Fecha").iloc[-1]
                fat_state = r.get("risk_label", "Sin dato")
                readiness = r.get("readiness_score", np.nan)
                obs = player_comment(r)
        elif week_ws is not None and not metrics_df.empty:
            week_we = pd.to_datetime(week_ws) + pd.Timedelta(days=6)
            pw = metrics_df[(metrics_df["Jugador"] == player) & (pd.to_datetime(metrics_df["Fecha"]) >= pd.to_datetime(week_ws)) & (pd.to_datetime(metrics_df["Fecha"]) <= week_we)]
            if not pw.empty:
                r = pw.sort_values("Fecha").iloc[-1]
                fat_state = r.get("risk_label", "Sin dato")
                readiness = pw["readiness_score"].mean()
                obs = f"Readiness semanal media {readiness:.1f}" if pd.notna(readiness) else ""

        rows.append({
            "Jugador": player,
            "Posición": pos,
            "Línea": line,
            "Estado fatiga": fat_state,
            "Readiness": readiness,
            "GPS día %": decision["gps_day"],
            "GPS semana %": decision["gps_week"],
            "Carga-respuesta": decision["load_response"],
            "Decisión": decision["action"],
            "Disponibilidad": decision["availability"],
            "Observación": "; ".join(decision["reasons"][:2]) if decision["reasons"] else obs,
            "Referencia GPS": ref["source"],
            "Partidos válidos": f"{ref['qualified_matches']}/{ref['required_matches']}",
            "Color": decision["color"],
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        order_map = {"Individualizar":5,"Reducir exposición":4,"Ajustar carga":3,"Disponible con control":2,"Disponible normal":1,"Reevaluar":6}
        out["_order"] = out["Decisión"].map(order_map).fillna(99)
        out = out.sort_values(["_order","Readiness"], ascending=[False, True], na_position="last").drop(columns="_order")
    return out

def top_alerts_block(metrics_df, gps_df, selected_date=None, week_ws=None):
    lines = []
    if selected_date is not None:
        selected_date = pd.to_datetime(selected_date)
        staff = team_staff_table(metrics_df, gps_df, selected_date=selected_date)
        if not staff.empty:
            low_ready = staff.dropna(subset=["Readiness"]).sort_values("Readiness").head(3)
            low_gps = staff.dropna(subset=["GPS día %"]).sort_values("GPS día %").head(3)
            if not low_ready.empty:
                lines.append("**Peores 3 readiness del día:** " + ", ".join([f"{r.Jugador} ({r.Readiness:.0f})" for _, r in low_ready.iterrows()]))
            if not low_gps.empty:
                lines.append("**Peores 3 GPS del día:** " + ", ".join([f"{r.Jugador} ({r['GPS día %']:.1f}%)" for _, r in low_gps.iterrows()]))
    if week_ws is not None:
        staff = team_staff_table(metrics_df, gps_df, week_ws=week_ws)
        if not staff.empty:
            low_gps_w = staff.dropna(subset=["GPS semana %"]).sort_values("GPS semana %").head(3)
            if not low_gps_w.empty:
                lines.append("**Peores 3 GPS semanales:** " + ", ".join([f"{r.Jugador} ({r['GPS semana %']:.1f}%)" for _, r in low_gps_w.iterrows()]))
    return [l for l in lines if l]

def plot_line_summary(staff_df, value_col, title):
    if staff_df is None or staff_df.empty or value_col not in staff_df.columns:
        return go.Figure()
    temp = staff_df.groupby("Línea", as_index=False)[value_col].mean(numeric_only=True)
    if temp.empty:
        return go.Figure()
    fig = px.bar(temp, x="Línea", y=value_col, title=title)
    fig.update_layout(height=320, margin=dict(l=20,r=20,t=60,b=30), title_x=0.5)
    return fig

def visual_decision_box(title, decision):
    reason_txt = " · ".join(decision["reasons"][:3]) if decision["reasons"] else "Sin motivos registrados"
    last_match = decision["last_valid_match"].strftime("%Y-%m-%d") if pd.notna(decision["last_valid_match"]) else "NA"
    return f"""
    <div style="background:white;border:1px solid rgba(15,23,42,0.08);border-left:8px solid {decision['color']};border-radius:18px;padding:16px 18px;box-shadow:0 6px 18px rgba(15,23,42,0.06);margin-bottom:12px;">
        <div style="font-size:0.82rem;color:#475467;">{title}</div>
        <div style="font-size:1.45rem;font-weight:900;color:#101828;margin-top:4px;">{decision['action']}</div>
        <div style="font-size:0.95rem;color:#344054;margin-top:6px;"><b>Motivo:</b> {reason_txt}</div>
        <div style="font-size:0.90rem;color:#667085;margin-top:6px;"><b>Contexto:</b> {decision['context']} · <b>GPS ref.:</b> {decision['reference_source']} · <b>Partidos válidos:</b> {decision['qualified_matches']}/{decision['required_matches']} · <b>Último partido válido:</b> {last_match}</div>
    </div>
    """

def build_upload_validation_report(df, mode="fatigue"):
    if df is None or df.empty:
        return []
    lines = [f"Filas cargadas: {len(df)}", f"Jugadores detectados: {df['Jugador'].nunique() if 'Jugador' in df.columns else 0}"]
    if "Posicion" in df.columns:
        sin_pos = int(df["Posicion"].isna().sum() + (df["Posicion"].astype(str) == "Sin asignar").sum())
        lines.append(f"Jugadores / filas sin posición: {sin_pos}")
    if mode == "gps":
        duplicated = int(df.duplicated(subset=["Fecha","Microciclo","Jugador"]).sum()) if all(c in df.columns for c in ["Fecha","Microciclo","Jugador"]) else 0
        lines.append(f"Duplicados internos detectados: {duplicated}")
        if "source_type" in df.columns and len(df):
            lines.append(f"Tipo de carga: {df['source_type'].iloc[0]}")
    return lines

def style_staff_table(df, sort_col=None):
    if df is None or df.empty:
        return df
    show = df.copy()
    for c in ["Readiness", "GPS día %", "GPS semana %"]:
        if c in show.columns:
            show[c] = pd.to_numeric(show[c], errors="coerce").round(1)
    if sort_col in show.columns:
        show = show.sort_values(sort_col, ascending=True if sort_col == "Readiness" else False, na_position="last")
    return show

def export_integrated_base(metrics_df, gps_df):
    gps_df = ensure_gps_datetime(gps_df)
    players = sorted(set((metrics_df["Jugador"].dropna().tolist() if metrics_df is not None and not metrics_df.empty else []) + (gps_df["Jugador"].dropna().tolist() if gps_df is not None and not gps_df.empty else [])))
    date_list = []
    if metrics_df is not None and not metrics_df.empty:
        date_list += pd.to_datetime(metrics_df["Fecha"]).dropna().dt.strftime("%Y-%m-%d").tolist()
    if gps_df is not None and not gps_df.empty:
        date_list += pd.to_datetime(gps_df["Fecha"]).dropna().dt.strftime("%Y-%m-%d").tolist()
    dates = sorted(set(date_list))
    rows = []
    for d in dates:
        for p in players:
            dec = professional_decision(p, d, metrics_df, gps_df)
            fat = metrics_df[(metrics_df["Jugador"] == p) & (pd.to_datetime(metrics_df["Fecha"]).dt.strftime("%Y-%m-%d") == str(d))] if metrics_df is not None and not metrics_df.empty else pd.DataFrame()
            r = fat.iloc[-1] if not fat.empty else None
            rows.append({
                "Fecha": d,
                "Jugador": p,
                "Posicion": get_player_position(p, metrics_df, gps_df),
                "Risk": r.get("risk_label", np.nan) if r is not None else np.nan,
                "Readiness": r.get("readiness_score", np.nan) if r is not None else np.nan,
                "Loss": r.get("objective_loss_score", np.nan) if r is not None else np.nan,
                "GPS_dia": dec["gps_day"],
                "GPS_semana": dec["gps_week"],
                "Decision": dec["action"],
                "Disponibilidad": dec["availability"],
                "Motivo": " | ".join(dec["reasons"][:3]),
            })
    return pd.DataFrame(rows)

# =========================================================
# PAGE OVERRIDES
# =========================================================
def page_cargar():
    st.markdown("### Carga de datos")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### CONTROL DE FATIGA")
        fat_fecha = st.date_input("Fecha control de fatiga", value=pd.Timestamp.today(), key="fat_fecha_v4")
        fat_micro = st.selectbox("Día microciclo fatiga", ["MD+1","MD-4","MD-3","MD-2","MD-1","PARTIDO"], index=4, key="fat_micro_v4")
        uploaded = st.file_uploader("Sube Excel/CSV de fatiga", type=["xlsx","xls","csv"], key="fatigue_upload_v4")
        if uploaded is not None:
            try:
                parsed = parse_uploaded(uploaded)
                parsed["Fecha"] = pd.to_datetime(fat_fecha)
                parsed["Microciclo"] = fat_micro
                st.success(f"Archivo interpretado correctamente: {parsed['Jugador'].nunique()} jugadores · {parsed['Fecha'].nunique()} fecha(s)")
                for line in build_upload_validation_report(parsed, mode="fatigue"):
                    st.caption("• " + line)
                cols_show = [c for c in ["Fecha","Microciclo","Jugador","Posicion","CMJ","RSI_mod","VMP","sRPE","Observaciones"] if c in parsed.columns]
                st.dataframe(parsed[cols_show], use_container_width=True, hide_index=True)
                if st.button("Guardar control de fatiga", type="primary", key="save_fat_v4"):
                    upsert_monitoring(parsed)
                    st.success("Datos de fatiga guardados correctamente.")
                    st.rerun()
            except Exception as e:
                st.error(f"No se pudo interpretar el archivo de fatiga: {e}")
    with c2:
        st.markdown("#### SESIÓN GPS")
        gps_fecha = st.date_input("Fecha GPS", value=pd.Timestamp.today(), key="gps_fecha_v4")
        gps_micro = st.selectbox("Día microciclo GPS", ["PARTIDO","MD+1","MD-4","MD-3","MD-2","MD-1"], index=3, key="gps_micro_v4")
        gps_uploaded = st.file_uploader("Sube CSV/Excel GPS", type=["xlsx","xls","csv"], key="gps_upload_v4")
        if gps_uploaded is not None:
            try:
                parsed_gps = parse_gps_uploaded(gps_uploaded, gps_fecha, gps_micro)
                st.success(f"Archivo GPS interpretado: {parsed_gps['Jugador'].nunique()} jugadores")
                for line in build_upload_validation_report(parsed_gps, mode="gps"):
                    st.caption("• " + line)
                ref_prof = build_match_profile(ensure_gps_datetime(load_gps()))
                if not ref_prof.empty:
                    n_self = int((ref_prof["profile_source"] == "propio").sum()) if "profile_source" in ref_prof.columns else 0
                    st.caption(f"Referencias GPS disponibles actualmente: {len(ref_prof)} perfiles ({n_self} propios, {len(ref_prof)-n_self} por posición)")
                st.dataframe(parsed_gps[["Fecha","Microciclo","Jugador","Posicion",*GPS_METRICS]], use_container_width=True, hide_index=True)
                if st.button("Guardar sesión GPS", key="save_gps_v4"):
                    upsert_gps(parsed_gps)
                    st.success("Datos GPS guardados correctamente.")
                    st.rerun()
            except Exception as e:
                st.error(f"No se pudo interpretar el archivo GPS: {e}")

def page_equipo(metrics_df, gps_df):
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return

    st.markdown(
        '<div class="hero"><div style="font-size:0.92rem; opacity:0.9;">Monitorización neuromuscular + GPS</div>'
        '<div style="font-size:2.15rem; font-weight:900; margin-top:0.15rem;">Equipo</div>'
        '<div style="font-size:1rem; opacity:0.92; margin-top:0.35rem;">Panel operativo central del staff · resumen → decisión → visual → detalle.</div></div>',
        unsafe_allow_html=True
    )

    week_labels, week_map = build_week_options(metrics_df, gps_df)
    if not week_labels:
        st.info("No hay semanas disponibles.")
        return

    quick_c1, quick_c2, quick_c3 = st.columns([1,1,2])
    with quick_c1:
        if st.button("Ir a última semana disponible", key="last_week_btn_v4"):
            st.session_state["equipo_week_label_v4"] = week_labels[-1]
    with quick_c2:
        st.caption("Selector rápido")
    wk_default = st.session_state.get("equipo_week_label_v4", week_labels[-1])
    wk_idx = week_labels.index(wk_default) if wk_default in week_labels else len(week_labels)-1
    wk_label = st.selectbox("Semana (lunes-domingo)", week_labels, index=wk_idx, key="equipo_week_v4")
    week_ws = week_map[wk_label]
    view_mode = st.radio("Vista", ["Resumen semanal","Sesión concreta"], horizontal=True, key="equipo_view_v4")
    focus = st.radio("Enfoque", ["Integrado","Fatiga","GPS"], horizontal=True, key="equipo_focus_v4")

    gps_df = ensure_gps_datetime(gps_df)
    week_we = week_ws + pd.Timedelta(days=6)
    week_fat = metrics_df[(metrics_df["Fecha"] >= week_ws) & (metrics_df["Fecha"] <= week_we)].copy() if not metrics_df.empty else pd.DataFrame()
    week_gps_raw = gps_df[(gps_df["Fecha"] >= week_ws) & (gps_df["Fecha"] <= week_we) & (gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO")].copy() if not gps_df.empty else pd.DataFrame()
    week_gps = gps_compute_compliance(week_gps_raw, reference_df=gps_df) if not week_gps_raw.empty else pd.DataFrame()

    if view_mode == "Resumen semanal":
        summary = weekly_global_summary(metrics_df, gps_df, week_ws)
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Sesiones fatiga", summary["fatigue_sessions"], "semana")
        with c2: kpi("Sesiones GPS", summary["gps_sessions"], "semana")
        with c3: kpi("Readiness media", "NA" if pd.isna(summary["readiness_mean"]) else f"{summary['readiness_mean']:.1f}", "semana")
        with c4: kpi("GPS semanal medio", "NA" if pd.isna(summary["gps_compliance_mean"]) else f"{summary['gps_compliance_mean']:.1f}%", "semana")

        collective_decision = {
            "action": "Ajustar carga" if (pd.notna(summary["readiness_mean"]) and summary["readiness_mean"] < 70) or (pd.notna(summary["gps_compliance_mean"]) and summary["gps_compliance_mean"] < 75) else "Disponible con control",
            "reasons": [integrated_week_text(metrics_df, gps_df, week_ws)],
            "context": f"Semana {wk_label}",
            "reference_source": "colectiva",
            "qualified_matches": 0,
            "required_matches": GPS_MATCH_MIN_MATCHES,
            "last_valid_match": pd.NaT,
            "color": "#F59E0B",
        }
        st.markdown(visual_decision_box("Bloque de decisión semanal", collective_decision), unsafe_allow_html=True)

        alert_lines = top_alerts_block(metrics_df, gps_df, week_ws=week_ws)
        if alert_lines:
            st.warning("  \n".join(alert_lines))

        staff_week = team_staff_table(metrics_df, gps_df, week_ws=week_ws)
        if not staff_week.empty:
            st.markdown("### Matriz integrada de staff")
            show = style_staff_table(staff_week, sort_col="GPS semana %")
            st.dataframe(show[["Jugador","Posición","Línea","Estado fatiga","Readiness","GPS semana %","Carga-respuesta","Decisión","Observación","Referencia GPS","Partidos válidos"]], use_container_width=True, hide_index=True)

        if focus in ["Integrado","Fatiga"] and not week_fat.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_risk_distribution(week_fat.groupby("Jugador", as_index=False).last()), use_container_width=True)
            with b: st.plotly_chart(plot_team_heatmap(week_fat.groupby("Jugador", as_index=False).last()), use_container_width=True)
            st.plotly_chart(plot_team_players_loss_bar(week_fat.groupby("Jugador", as_index=False).last()), use_container_width=True)

        if focus in ["Integrado","GPS"] and not week_gps.empty and not staff_week.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_gps_weekly_support(gps_df, week_ws), use_container_width=True)
            with b: st.plotly_chart(plot_line_summary(staff_week, "GPS semana %", "GPS semanal por líneas"), use_container_width=True)

        if focus == "Integrado" and not week_fat.empty:
            last_rows = week_fat.sort_values("Fecha").groupby("Jugador", as_index=False).last()
            st.plotly_chart(plot_integrated_team_matrix(last_rows, metrics_df, gps_df, week_we), use_container_width=True)

    else:
        sess_opts = session_options_for_week(metrics_df, gps_df, week_ws)
        if not sess_opts:
            st.info("No hay sesiones en esa semana.")
            return
        sess_label = st.selectbox("Sesión de la semana", sess_opts, key="equipo_sesion_v4")
        sess_date_str, sess_md = [x.strip() for x in sess_label.split("|", 1)]
        selected_date = pd.to_datetime(sess_date_str)
        team_day = week_fat[(week_fat["Fecha"].dt.normalize() == selected_date.normalize())].copy() if not week_fat.empty else pd.DataFrame()
        if sess_md != "Sin día" and not team_day.empty:
            team_day = team_day[team_day["Microciclo"].fillna("Sin día").astype(str) == sess_md]
        gps_day = week_gps[(week_gps["Fecha"].dt.normalize() == selected_date.normalize()) & (week_gps["Microciclo"].astype(str) == sess_md)].copy() if not week_gps.empty else pd.DataFrame()

        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: kpi("Fecha", selected_date.strftime("%Y-%m-%d"), sess_md)
        with c2: kpi("Jugadores fatiga", int(team_day["Jugador"].nunique()) if not team_day.empty else 0, "sesión")
        with c3: kpi("Readiness media", "NA" if team_day.empty else f"{team_day['readiness_score'].mean():.1f}", "sesión")
        with c4: kpi("GPS medio", "NA" if gps_day.empty else f"{gps_day['compliance_score'].mean():.1f}%", "sesión")
        with c5: kpi("Críticos", int((team_day["risk_label"]=="Fatiga crítica").sum()) if not team_day.empty else 0, "sesión")

        collective_decision = {
            "action": "Disponible normal" if team_day.empty or team_day["objective_loss_score"].mean() < 1 else "Ajustar carga",
            "reasons": [team_interpretation(team_day)] if not team_day.empty else ["Sin datos de fatiga para esta sesión"],
            "context": integrated_week_text(metrics_df, gps_df, selected_date),
            "reference_source": "colectiva",
            "qualified_matches": 0,
            "required_matches": GPS_MATCH_MIN_MATCHES,
            "last_valid_match": pd.NaT,
            "color": "#16A34A" if team_day.empty or team_day["objective_loss_score"].mean() < 1 else "#F59E0B",
        }
        st.markdown(visual_decision_box("Bloque de decisión del día", collective_decision), unsafe_allow_html=True)

        alert_lines = top_alerts_block(metrics_df, gps_df, selected_date=selected_date)
        if alert_lines:
            st.warning("  \n".join(alert_lines))

        staff_day = team_staff_table(metrics_df, gps_df, selected_date=selected_date, session_micro=sess_md)
        if not staff_day.empty:
            st.markdown("### Matriz integrada de staff")
            show = style_staff_table(staff_day, sort_col="Readiness")
            st.dataframe(show[["Jugador","Posición","Línea","Estado fatiga","Readiness","GPS día %","GPS semana %","Carga-respuesta","Decisión","Observación","Referencia GPS","Partidos válidos"]], use_container_width=True, hide_index=True)

        if focus in ["Integrado","Fatiga"] and not team_day.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_risk_distribution(team_day), use_container_width=True)
            with b: st.plotly_chart(plot_team_heatmap(team_day), use_container_width=True)
            st.plotly_chart(plot_team_players_loss_bar(team_day), use_container_width=True)

        if focus in ["Integrado","GPS"] and not gps_day.empty and not staff_day.empty:
            a,b = st.columns(2)
            with a: st.plotly_chart(plot_team_gps_support(gps_day), use_container_width=True)
            with b: st.plotly_chart(plot_line_summary(staff_day, "GPS día %", "GPS del día por líneas"), use_container_width=True)

        if focus == "Integrado" and not team_day.empty:
            st.plotly_chart(plot_integrated_team_matrix(team_day, metrics_df, gps_df, selected_date), use_container_width=True)

def page_jugador(metrics_df, gps_df):
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return

    gps_df = ensure_gps_datetime(gps_df)
    player_map = build_player_display_options(metrics_df, gps_df)
    st.markdown('<div class="section-title">Jugador</div>', unsafe_allow_html=True)
    player_label = st.selectbox("Selecciona jugador", list(player_map.keys()), key="player_selector_v4")
    player = player_map[player_label]

    week_labels, week_map = build_week_options(metrics_df, gps_df, player=player)
    if not week_labels:
        st.info("No hay semanas disponibles para este jugador.")
        return

    quick_c1, quick_c2 = st.columns([1,3])
    with quick_c1:
        if st.button("Última semana", key="player_last_week_v4"):
            st.session_state["player_week_label_v4"] = week_labels[-1]
    wk_default = st.session_state.get("player_week_label_v4", week_labels[-1])
    wk_idx = week_labels.index(wk_default) if wk_default in week_labels else len(week_labels)-1
    wk_label = st.selectbox("Semana (lunes-domingo)", week_labels, index=wk_idx, key="player_week_v4")
    week_ws = week_map[wk_label]
    view_mode = st.radio("Vista", ["Resumen semanal","Sesión concreta"], horizontal=True, key="player_view_v4")

    player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame()
    player_gps = gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame()
    ref = gps_reference_info(gps_df, player)
    selected_anchor = week_ws if view_mode == "Resumen semanal" else (latest_nonmatch_date(player_df, player_gps, player=player) or week_ws)
    decision = professional_decision(player, selected_anchor, metrics_df, gps_df)
    context = decision["context"]
    last_match = ref["last_valid_match"].strftime("%Y-%m-%d") if pd.notna(ref["last_valid_match"]) else "NA"

    st.markdown(
        f'<div class="card">'
        f'<div style="font-size:1.9rem;font-weight:900;color:#101828;">{player_label.replace(" - ", " · ")}</div>'
        f'<div style="margin-top:0.55rem;"><span class="pill" style="background:{decision["color"]};">{decision["action"]}</span></div>'
        f'<div style="margin-top:0.7rem;color:#475467;"><b>Contexto:</b> {context} · <b>Carga-respuesta:</b> {decision["load_response"]} · '
        f'<b>Referencia GPS:</b> {ref["source"]} · <b>Partidos válidos:</b> {ref["qualified_matches"]}/{ref["required_matches"]} · <b>Último partido válido:</b> {last_match}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    tabs = st.tabs(["Diagnóstico","GPS","Tendencia","Informes rápidos"])
    week_we = week_ws + pd.Timedelta(days=6)
    player_week_fat = player_df[(player_df["Fecha"] >= week_ws) & (player_df["Fecha"] <= week_we)].copy() if not player_df.empty else pd.DataFrame()
    player_week_gps = gps_player_week_table(gps_df, player, week_ws) if not player_gps.empty else pd.DataFrame()

    row = None
    selected_date = week_ws
    sess_md = "Semanal"
    session_gps = pd.DataFrame()
    if view_mode == "Sesión concreta":
        sess_opts = session_options_for_week(metrics_df, gps_df, week_ws, player=player)
        if not sess_opts:
            st.info("No hay sesiones en esa semana.")
            return
        sess_label = st.selectbox("Sesión de la semana", sess_opts, key="player_sess_v4")
        sess_date_str, sess_md = [x.strip() for x in sess_label.split("|", 1)]
        selected_date = pd.to_datetime(sess_date_str)
        current = player_df[player_df["Fecha"].dt.normalize() == selected_date.normalize()] if not player_df.empty else pd.DataFrame()
        row = current.iloc[-1] if not current.empty else None
        session_gps = gps_player_session_table(gps_df, player, selected_date, micro=sess_md) if not player_gps.empty else pd.DataFrame()
        decision = professional_decision(player, selected_date, metrics_df, gps_df)

    with tabs[0]:
        if view_mode == "Resumen semanal":
            c1,c2,c3,c4 = st.columns(4)
            with c1: kpi("Controles fatiga", int(player_week_fat[["Fecha","Microciclo"]].drop_duplicates().shape[0]) if not player_week_fat.empty else 0, "semana")
            with c2: kpi("Readiness sem.", "NA" if player_week_fat.empty else f"{player_week_fat['readiness_score'].mean():.1f}", "media")
            with c3: kpi("GPS sem.", "NA" if player_week_gps.empty else f"{pd.to_numeric(player_week_gps['pct'], errors='coerce').mean():.1f}%", "media")
            with c4: kpi("Decisión", decision["action"], decision["availability"])
            st.markdown(visual_decision_box("Bloque de decisión semanal", decision), unsafe_allow_html=True)
            if not player_week_fat.empty:
                st.plotly_chart(plot_player_integrated_week_dashboard(player, week_ws, metrics_df, gps_df), use_container_width=True)
            alerts7 = 0 if player_df.empty else int(player_df[(player_df["Fecha"] >= pd.to_datetime(week_ws) - pd.Timedelta(days=7)) & (player_df["Fecha"] <= week_we)]["risk_label"].isin(["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"]).sum())
            alerts14 = 0 if player_df.empty else int(player_df[(player_df["Fecha"] >= pd.to_datetime(week_ws) - pd.Timedelta(days=14)) & (player_df["Fecha"] <= week_we)]["risk_label"].isin(["Fatiga moderada","Fatiga moderada-alta","Fatiga crítica"]).sum())
            st.info(f"Historial de alertas · 7 días: {alerts7} · 14 días: {alerts14}")
        else:
            if row is None:
                st.warning("No hay datos de control de fatiga para esta sesión.")
            else:
                c1,c2,c3,c4,c5 = st.columns(5)
                with c1: kpi("Fecha", selected_date.strftime("%Y-%m-%d"), sess_md)
                with c2: kpi("Riesgo", row["risk_label"], "clasificación")
                with c3: kpi("Loss", f"{row['objective_loss_score']:.2f}", "0-3")
                with c4: kpi("Readiness", f"{row['readiness_score']:.0f}", "día")
                with c5: kpi("Decisión", decision["action"], decision["availability"])
                st.markdown(visual_decision_box("Bloque de decisión del día", decision), unsafe_allow_html=True)
                main_profile, pattern, worst_metric, worst_value = infer_fatigue_profile(row)
                st.markdown(f"**Qué significa hoy:** {main_profile}, con {pattern}. Variable dominante: {LABELS.get(worst_metric, 'NA')} ({'NA' if worst_value is None else f'{worst_value:.1f}%'}). **Acción recomendada:** {decision['action']}. **Motivo:** {' · '.join(decision['reasons'][:3])}.")
                a,b = st.columns(2)
                with a: st.plotly_chart(radar_relative_loss(row), use_container_width=True)
                with b: st.plotly_chart(radar_current_vs_baseline(row), use_container_width=True)

    with tabs[1]:
        if view_mode == "Resumen semanal":
            if player_week_gps.empty:
                st.info("Sin GPS semanal disponible.")
            else:
                gps_progress_bars_streamlit(player_week_gps, "Resumen GPS semanal")
                st.plotly_chart(plot_player_gps_support(player_week_gps, "Apoyo visual GPS semanal"), use_container_width=True)
                st.caption(f"Referencia GPS usada: {ref['source']} · partidos válidos: {ref['qualified_matches']}/{ref['required_matches']}")
        else:
            if session_gps.empty:
                st.info("Sin GPS del día disponible.")
            else:
                gps_progress_bars_streamlit(session_gps, "Cumplimiento GPS del día")
                st.plotly_chart(plot_player_gps_support(session_gps, "Apoyo visual GPS del día"), use_container_width=True)
                sess_tbl = session_gps[["Variable","pct","min","max","status"]].copy()
                sess_tbl.columns = ["Variable","% sesión vs partido","Objetivo mínimo (%)","Objetivo máximo (%)","Interpretación"]
                st.dataframe(sess_tbl.round(1), use_container_width=True, hide_index=True)
                st.caption(f"Referencia GPS usada: {ref['source']} · partidos válidos: {ref['qualified_matches']}/{ref['required_matches']} · último partido válido: {last_match}")

    with tabs[2]:
        if player_df.empty:
            st.info("Sin datos longitudinales.")
        else:
            anchor_date = week_we if view_mode == "Resumen semanal" else selected_date
            st.plotly_chart(plot_objective_timeline(player_df, anchor_date), use_container_width=True)
            if view_mode == "Sesión concreta" and row is not None:
                st.plotly_chart(plot_player_snapshot_compare(row), use_container_width=True)
            st.markdown("### Evolución por variable")
            for m in OBJECTIVE_METRICS:
                l, rcol = st.columns(2)
                with l: st.plotly_chart(plot_metric_main(player_df, m, anchor_date), use_container_width=True)
                with rcol: st.plotly_chart(plot_metric_pct(player_df, m, anchor_date), use_container_width=True)

    with tabs[3]:
        st.caption("Descargas disponibles en la pestaña Informes. Esta vista resume el estado del jugador para una reunión rápida.")
        st.markdown(f"- **Estado actual:** {decision['action']}")
        st.markdown(f"- **Disponibilidad:** {decision['availability']}")
        st.markdown(f"- **Motivo principal:** {' · '.join(decision['reasons'][:3])}")
        st.markdown(f"- **Referencia GPS:** {ref['source']} · {ref['qualified_matches']}/{ref['required_matches']} partidos válidos")

def page_informes(metrics_df, gps_df):
    gps_df = ensure_gps_datetime(gps_df)
    if metrics_df.empty and gps_df.empty:
        st.info("No hay datos disponibles.")
        return
    st.markdown('<div class="section-title">Informes descargables</div>', unsafe_allow_html=True)
    tab1,tab2,tab3,tab4,tab5 = st.tabs(["Informe individual staff anual","Informe individual staff por sesión","Informe semanal integrado jugador","Informe entrenador sesión","Informe semanal global"])
    player_map = build_player_display_options(metrics_df, gps_df)

    with tab1:
        player_label = st.selectbox("Jugador · informe anual", list(player_map.keys()), key="yr_pro")
        player = player_map[player_label]
        player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame(columns=["Fecha"])
        latest_date = player_df.iloc[-1]["Fecha"] if not player_df.empty else gps_df[gps_df["Jugador"]==player]["Fecha"].max()
        latest = player_df.iloc[-1] if not player_df.empty else None
        if latest is not None:
            st.markdown(f"**Resumen actual:** {latest['risk_label']} · loss {latest['objective_loss_score']:.2f} · readiness {latest['readiness_score']:.0f}")
        html = player_season_html(player_df, player, gps_df=gps_df) if not player_df.empty else f"<html><head><meta charset='utf-8'>{report_css()}</head><body>{gps_player_report_html(player, gps_df, latest_date)}</body></html>"
        st.download_button("Descargar HTML anual", data=html.encode("utf-8"), file_name=f"informe_anual_{player.replace(' ','_')}.html", mime="text/html")
        if not player_df.empty:
            st.download_button("Descargar PDF anual", data=build_pdf_bytes_player_season(player_df, player, gps_df=gps_df), file_name=f"informe_anual_{player.replace(' ','_')}.pdf", mime="application/pdf")

    with tab2:
        player_label = st.selectbox("Jugador · informe sesión", list(player_map.keys()), key="ses_pro")
        player = player_map[player_label]
        source_dates = []
        if not metrics_df.empty:
            source_dates += [pd.to_datetime(d).strftime("%Y-%m-%d") for d in metrics_df[metrics_df["Jugador"] == player]["Fecha"].dropna().unique()]
        if not gps_df.empty:
            source_dates += [pd.to_datetime(d).strftime("%Y-%m-%d") for d in gps_df[gps_df["Jugador"] == player]["Fecha"].dropna().unique()]
        opts = sorted(set(source_dates))
        if not opts:
            st.info("Sin fechas disponibles.")
        else:
            sel_date = st.selectbox("Fecha sesión", opts, key="sesd_pro")
            player_df = metrics_df[metrics_df["Jugador"] == player].copy().sort_values("Fecha") if not metrics_df.empty else pd.DataFrame()
            session_df = player_df[player_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date].copy() if not player_df.empty else pd.DataFrame()
            gps_only_df = gps_df[(gps_df["Jugador"] == player) & (gps_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date)] if not gps_df.empty else pd.DataFrame()
            if not session_df.empty:
                row = session_df.iloc[-1]
                html = player_session_html(row, player_df, session_df, gps_df=gps_df)
                st.download_button("Descargar HTML sesión", data=html.encode("utf-8"), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.html", mime="text/html")
                st.download_button("Descargar PDF sesión", data=build_pdf_bytes_player_session(row, player_df, gps_df=gps_df), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.pdf", mime="application/pdf")
            elif not gps_only_df.empty:
                html = f"<html><head><meta charset='utf-8'>{report_css()}</head><body><div class='hero'><div style='font-size:12px;opacity:0.9;'>Informe individual · Sesión específica</div><div style='font-size:32px;font-weight:900;line-height:1.15;'>{player}</div><div style='font-size:15px;margin-top:6px;'>Fecha: {sel_date}</div></div><div class='section'><div class='title'>Observación</div><div class='diag'>No hay datos de control de fatiga para esta fecha. Se muestran únicamente los datos GPS disponibles.</div></div>{gps_player_report_html(player, gps_df, pd.to_datetime(sel_date))}</body></html>"
                st.download_button("Descargar HTML sesión", data=html.encode("utf-8"), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.html", mime="text/html")
                st.download_button("Descargar PDF sesión", data=build_pdf_bytes_player_session_gps_only(player, gps_df, pd.to_datetime(sel_date)), file_name=f"informe_sesion_{player.replace(' ','_')}_{sel_date}.pdf", mime="application/pdf")
            else:
                st.warning("No hay datos para esa fecha.")

    with tab3:
        player_label = st.selectbox("Jugador · informe semanal", list(player_map.keys()), key="gpswk_pro")
        player = player_map[player_label]
        week_labels, week_map = build_week_options(metrics_df, gps_df, player=player)
        if week_labels:
            wk_label = st.selectbox("Semana de referencia", week_labels, key="gpswkd_pro")
            week_ws = week_map[wk_label]
            html = player_weekly_html(player, metrics_df[metrics_df["Jugador"] == player].copy() if not metrics_df.empty else pd.DataFrame(), gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame(), week_ws)
            st.download_button("Descargar HTML semanal", data=html.encode("utf-8"), file_name=f"informe_semanal_{player.replace(' ','_')}_{week_ws.strftime('%Y%m%d')}.html", mime="text/html")
            st.download_button("Descargar PDF semanal", data=build_pdf_bytes_player_weekly(player, metrics_df[metrics_df["Jugador"] == player].copy() if not metrics_df.empty else pd.DataFrame(), gps_df[gps_df["Jugador"] == player].copy() if not gps_df.empty else pd.DataFrame(), week_ws), file_name=f"informe_semanal_{player.replace(' ','_')}_{week_ws.strftime('%Y%m%d')}.pdf", mime="application/pdf")

    with tab4:
        all_week_labels, all_week_map = build_week_options(metrics_df, gps_df)
        if all_week_labels:
            wk_label = st.selectbox("Semana sesión global", all_week_labels, key="teamwk_pro")
            week_ws = all_week_map[wk_label]
            sess_opts = session_options_for_week(metrics_df, gps_df, week_ws)
            if sess_opts:
                sess_label = st.selectbox("Sesión global", sess_opts, key="teamr_pro")
                sel_date, sel_md = [x.strip() for x in sess_label.split("|",1)]
                team_day = metrics_df[(metrics_df["Fecha"].dt.strftime("%Y-%m-%d") == sel_date)].copy() if not metrics_df.empty else pd.DataFrame()
                if sel_md != "Sin día" and not team_day.empty:
                    team_day = team_day[team_day["Microciclo"].fillna("Sin día").astype(str) == sel_md]
                if not team_day.empty:
                    st.markdown(f"**Lectura rápida:** {team_interpretation(team_day)}")
                    html = coach_session_html(team_day, sel_date, gps_df=gps_df)
                    st.download_button("Descargar HTML entrenador", data=html.encode("utf-8"), file_name=f"informe_equipo_sesion_{sel_date}.html", mime="text/html")
                    st.download_button("Descargar PDF entrenador", data=build_pdf_bytes_team_session(team_day, sel_date, gps_df=gps_df), file_name=f"informe_equipo_sesion_{sel_date}.pdf", mime="application/pdf")
                else:
                    st.info("No hay datos para esa sesión.")

    with tab5:
        all_week_labels, all_week_map = build_week_options(metrics_df, gps_df)
        if all_week_labels:
            wk_label = st.selectbox("Semana informe global", all_week_labels, key="globalwk_pro")
            week_ws = all_week_map[wk_label]
            html = weekly_global_html(metrics_df, gps_df, week_ws)
            st.download_button("Descargar HTML semanal global", data=html.encode("utf-8"), file_name=f"informe_global_semanal_{week_ws.strftime('%Y%m%d')}.html", mime="text/html")
            st.download_button("Descargar PDF semanal global", data=build_pdf_bytes_weekly_global(metrics_df, gps_df, week_ws), file_name=f"informe_global_semanal_{week_ws.strftime('%Y%m%d')}.pdf", mime="application/pdf")

def page_admin(base_df, gps_df):
    gps_df = ensure_gps_datetime(gps_df)
    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi("Registros fatiga", len(base_df), "total")
    with c2: kpi("Jugadores fatiga", base_df["Jugador"].nunique() if not base_df.empty else 0, "únicos")
    with c3:
        gps_micro = gps_df[gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO"].copy() if not gps_df.empty else pd.DataFrame()
        kpi("Sesiones GPS microciclo", len(gps_micro[["Fecha","Microciclo"]].drop_duplicates()) if not gps_micro.empty else 0, "guardadas")
    with c4:
        gps_matches = gps_df[gps_df["Microciclo"].astype(str).str.upper() == "PARTIDO"].copy() if not gps_df.empty else pd.DataFrame()
        kpi("Partidos GPS", len(gps_matches["Fecha"].drop_duplicates()) if not gps_matches.empty else 0, "guardados")

    c5,c6,c7 = st.columns(3)
    with c5:
        if not base_df.empty:
            st.download_button("Descargar base fatiga CSV", data=base_df.to_csv(index=False).encode("utf-8"), file_name="fatiga.csv", mime="text/csv")
    with c6:
        if not gps_df.empty:
            st.download_button("Descargar base GPS CSV", data=gps_df.to_csv(index=False).encode("utf-8"), file_name="gps.csv", mime="text/csv")
    with c7:
        integrated = export_integrated_base(compute_metrics(base_df) if not base_df.empty else pd.DataFrame(), gps_df)
        if not integrated.empty:
            st.download_button("Descargar base integrada CSV", data=integrated.to_csv(index=False).encode("utf-8"), file_name="integrada.csv", mime="text/csv")

    if not base_df.empty:
        st.markdown("### Eliminar sesiones de CONTROL DE FATIGA")
        fat_df = base_df.copy()
        fat_df["Fecha"] = pd.to_datetime(fat_df["Fecha"], errors="coerce")
        if "Microciclo" not in fat_df.columns:
            fat_df["Microciclo"] = np.nan
        fat_sessions = fat_df[["Fecha","Microciclo"]].drop_duplicates().sort_values(["Fecha","Microciclo"], na_position="last")
        fat_labels = []
        for _, r in fat_sessions.iterrows():
            d = pd.to_datetime(r["Fecha"]).strftime("%Y-%m-%d") if pd.notna(r["Fecha"]) else "Sin fecha"
            micro = "" if pd.isna(r["Microciclo"]) else str(r["Microciclo"])
            fat_labels.append(f"{d} | {micro if micro else 'Sin día'}")
        if fat_labels:
            fat_sel = st.selectbox("Selecciona la sesión de fatiga a eliminar", fat_labels, key="admin_fat_del_v4")
            if st.button("Eliminar sesión de fatiga", type="secondary", key="btn_del_fat_v4"):
                date_str, micro = [x.strip() for x in fat_sel.split("|", 1)]
                delete_fatigue_session(date_str, None if micro == "Sin día" else micro)
                st.success(f"Sesión de fatiga {fat_sel} eliminada correctamente.")
                st.rerun()

    if not gps_df.empty:
        st.markdown("### Eliminar sesiones de SESIÓN GPS del microciclo")
        gps_micro = gps_df[gps_df["Microciclo"].astype(str).str.upper() != "PARTIDO"].copy()
        if not gps_micro.empty:
            gps_sessions = gps_micro[["Fecha","Microciclo"]].drop_duplicates().sort_values(["Fecha","Microciclo"])
            gps_labels = [f"{pd.to_datetime(r.Fecha).strftime('%Y-%m-%d')} | {r.Microciclo}" for _, r in gps_sessions.iterrows()]
            sel = st.selectbox("Selecciona la sesión GPS del microciclo a eliminar", gps_labels, key="admin_gps_del_v4")
            if st.button("Eliminar sesión GPS microciclo", type="secondary", key="btn_del_gps_v4"):
                date_str, micro = [x.strip() for x in sel.split("|", 1)]
                delete_gps_session(date_str, micro)
                st.success(f"Sesión GPS {sel} eliminada correctamente.")
                st.rerun()

        st.markdown("### Eliminar PARTIDOS")
        gps_matches = gps_df[gps_df["Microciclo"].astype(str).str.upper() == "PARTIDO"].copy()
        if not gps_matches.empty:
            match_labels = [pd.to_datetime(d).strftime("%Y-%m-%d") for d in sorted(gps_matches["Fecha"].dropna().unique())]
            sel_match = st.selectbox("Selecciona el partido a eliminar", match_labels, key="admin_match_del_v4")
            if st.button("Eliminar partido", type="secondary", key="btn_del_match_v4"):
                delete_gps_match(sel_match)
                st.success(f"Partido {sel_match} eliminado correctamente.")
                st.rerun()

def main():
    init_db()
    st.sidebar.markdown("## Staff dashboard")
    st.sidebar.caption("Versión profesional: decisión integrada, GPS, fatiga, informes y control operativo.")
    base_df = standardize_player_names_in_frames(load_monitoring())
    gps_df = standardize_player_names_in_frames(load_gps())
    metrics_df = compute_metrics(base_df) if not base_df.empty else base_df.copy()
    globals()["LAST_METRICS_DF"] = metrics_df
    globals()["LAST_GPS_DF"] = gps_df
    menu = st.sidebar.radio("Sección", ["Cargar datos","Equipo","Jugador","Informes","Administración"], key="main_menu_v4")
    if menu == "Cargar datos":
        page_cargar()
    elif menu == "Equipo":
        page_equipo(metrics_df, gps_df)
    elif menu == "Jugador":
        page_jugador(metrics_df, gps_df)
    elif menu == "Informes":
        page_informes(metrics_df, gps_df)
    else:
        page_admin(base_df, gps_df)

if __name__ == "__main__":
    main()

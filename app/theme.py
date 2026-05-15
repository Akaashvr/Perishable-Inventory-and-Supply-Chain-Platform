from __future__ import annotations
import streamlit as st

# Colour tokens 
C = {
    # Backgrounds
    "bg":        "#070D18", 
    "surface":   "#0D1726", 
    "surface2":  "#111F32", 
    "border":    "#1A2D42", 
    "border2":   "#2A3F57", 

    # Brand
    "green":     "#00C896", 
    "green_dim": "#007A5A",
    "orange":    "#FF8533",  
    "orange_dim":"#7A3D16",
    "blue":      "#00A8E8", 
    "blue_dim":  "#004A6E",
    "red":       "#FF4560", 
    "purple":    "#9B59F5",
    "yellow":    "#FFD60A", 

    # Text
    "text":      "#D9E5F2",
    "muted":     "#7A94AD",
    "dim":       "#3A5470",
}

# Plotly colour sequence (used across all charts)
CHART_COLORS = [
    C["green"], C["orange"], C["blue"],
    C["purple"], C["red"], C["yellow"],
    "#2ECC71", "#E74C3C", "#3498DB",
]

# Plotly layout defaults
def plotly_layout(**overrides) -> dict:
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12,24,39,0.55)",
        font=dict(color=C["text"], family="Inter, -apple-system, sans-serif", size=12),
        xaxis=dict(
            gridcolor=C["border"], linecolor=C["border"],
            tickcolor=C["muted"], zerolinecolor=C["border"],
            tickfont=dict(color=C["muted"], size=11),
        ),
        yaxis=dict(
            gridcolor=C["border"], linecolor=C["border"],
            tickcolor=C["muted"], zerolinecolor=C["border"],
            tickfont=dict(color=C["muted"], size=11),
        ),
        legend=dict(
            bgcolor="rgba(12,24,39,0.8)", bordercolor=C["border"],
            borderwidth=1, font=dict(color=C["muted"], size=11),
        ),
        hoverlabel=dict(
            bgcolor=C["surface2"], bordercolor=C["border"],
            font=dict(color=C["text"], size=12),
        ),
        colorway=CHART_COLORS,
        margin=dict(l=48, r=24, t=36, b=48),
        height=400,
    )
    base.update(overrides)
    return base


# CSS injection
_CSS = f"""
/* ── Remixicon CDN ── */
@import url('https://cdn.jsdelivr.net/npm/remixicon@3.5.0/fonts/remixicon.css');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset ── */
*, *::before, *::after {{ box-sizing: border-box; }}

/* ── App canvas: deep navy + hex supply-network pattern ── */
.stApp {{
    background-color: {C["bg"]};
    background-image:
        linear-gradient(30deg,  rgba(0,200,150,.022) 12%, transparent 12.5%,
                                transparent 87%,     rgba(0,200,150,.022) 87.5%),
        linear-gradient(150deg, rgba(0,200,150,.022) 12%, transparent 12.5%,
                                transparent 87%,     rgba(0,200,150,.022) 87.5%),
        linear-gradient(30deg,  rgba(0,200,150,.022) 12%, transparent 12.5%,
                                transparent 87%,     rgba(0,200,150,.022) 87.5%),
        linear-gradient(150deg, rgba(0,200,150,.022) 12%, transparent 12.5%,
                                transparent 87%,     rgba(0,200,150,.022) 87.5%),
        linear-gradient(60deg,  rgba(7,20,40,.45) 25%, transparent 25.5%,
                                transparent 75%,     rgba(7,20,40,.45) 75%),
        linear-gradient(60deg,  rgba(7,20,40,.45) 25%, transparent 25.5%,
                                transparent 75%,     rgba(7,20,40,.45) 75%);
    background-size: 84px 146px;
    background-position: 0 0, 0 0, 42px 73px, 42px 73px, 0 0, 42px 73px;
    background-attachment: fixed;
    font-family: 'Inter', -apple-system, sans-serif;
}}

/* Ambient colour glows (fresh green + warm orange + cold blue) */
.stApp::before {{
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 65% 55% at 8%  42%, rgba(0,200,150,.07)  0%, transparent 100%),
        radial-gradient(ellipse 50% 50% at 92% 55%, rgba(255,133,51,.05) 0%, transparent 100%),
        radial-gradient(ellipse 45% 40% at 52% 3%,  rgba(0,168,232,.04)  0%, transparent 100%);
    pointer-events: none;
    z-index: 0;
}}

/* ── Hide Streamlit chrome ── */


[data-testid="stSidebar"],
[data-testid="stSidebar"] * {{
    color: white !important;
}}

#MainMenu, footer, header {{ display: none !important; }}
[data-testid="stSidebarNav"]  {{ display: none !important; }}
[data-testid="stDecoration"]  {{ display: none !important; }}
.block-container {{ padding: 1rem 1.5rem; max-width: 100%; }}
[data-testid="stAppViewContainer"] > section:first-child {{
    padding-top: 0.5rem;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: {C["surface"]};
    border-right: 1px solid {C["border"]};
}}
[data-testid="stSidebar"] .block-container {{
    padding: 1.2rem 1rem;
}}
/* Sidebar toggle arrow button */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"] button {{
    background: linear-gradient(135deg, {C["green"]}, {C["blue"]}) !important;
    border: none !important;
    border-radius: 50% !important;
    color: {C["bg"]} !important;
    box-shadow: 0 0 12px rgba(0,200,150,.4) !important;
}}
[data-testid="collapsedControl"] {{
    background-color: {C["surface"]} !important;
    border-right: 1px solid {C["border"]} !important;
}}

/* ── Sidebar labels ── */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p {{
    color: {C["muted"]} !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: .7px;
    font-weight: 500;
}}

/* ── Sidebar inputs ── */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div {{
    background-color: {C["surface2"]} !important;
    border-color: {C["border"]} !important;
    border-radius: 8px !important;
    color: {C["text"]} !important;
}}
[data-testid="stSidebar"] [data-baseweb="tag"] {{
    background: rgba(0,200,150,.18) !important;
    border-radius: 6px !important;
}}

/* ── Navigation TABS ── */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent;
    border-bottom: 1px solid {C["border"]};
    gap: 2px;
    padding: 0 2px;
    margin-bottom: 1.4rem;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: {C["muted"]};
    font-size: 13px;
    font-weight: 500;
    padding: 10px 20px;
    letter-spacing: .3px;
    transition: all .18s ease;
    margin-bottom: -1px;
}}
.stTabs [data-baseweb="tab"]:hover {{
    color: {C["green"]};
    background: rgba(0,200,150,.05);
    border-radius: 8px 8px 0 0;
}}
.stTabs [aria-selected="true"] {{
    background: transparent !important;
    color: {C["green"]} !important;
    border-bottom: 2px solid {C["green"]} !important;
    border-radius: 0 !important;
}}
.stTabs [data-baseweb="tab-panel"] {{ padding: 0; }}

/* ── KPI metric cards ── */
[data-testid="metric-container"] {{
    background: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius: 14px;
    padding: 18px 20px;
    transition: all .2s ease;
    position: relative;
    overflow: hidden;
}}
[data-testid="metric-container"]::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, {C["green"]}, {C["blue"]});
    border-radius: 14px 14px 0 0;
}}
[data-testid="metric-container"]:hover {{
    border-color: {C["border2"]};
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(0,200,150,.1);
}}
[data-testid="metric-container"] label {{
    color: {C["muted"]} !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: .8px;
    font-weight: 500;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: white !important;
    font-size: 26px !important;
    font-weight: 700;
}}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {{
    color: white !important;
}}

[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {{
    color: white !important;
}}


[data-testid="stMetricDelta"] {{
    font-size: 12px !important;
    font-weight: 500;
}}

/* ── Dataframe ── */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] iframe {{
    border: 1px solid {C["border"]} !important;
    border-radius: 12px !important;
    overflow: hidden;
}}

/* ── Sliders ── */
[data-testid="stSlider"] [role="slider"] {{
    background: {C["green"]} !important;
    box-shadow: 0 0 8px rgba(0,200,150,.5) !important;
}}
.stSlider > div > div > div > div {{
    background: linear-gradient(90deg, {C["green"]}, {C["blue"]}) !important;
}}

/* ── Buttons ── */
.stButton > button {{
    background: linear-gradient(135deg, {C["green"]}, {C["blue"]});
    border: none;
    border-radius: 8px;
    color: {C["bg"]};
    font-weight: 600;
    font-size: 12px;
    padding: 8px 16px;
    transition: all .2s ease;
    width: 100%;
    letter-spacing: .4px;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 18px rgba(0,200,150,.35);
    background: linear-gradient(135deg, #00E6AD, #00C2FF);
}}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {{
    background: transparent;
    border: 1px solid {C["border2"]};
    color: {C["text"]};
    font-size: 12px;
    border-radius: 8px;
    width: 100%;
    transition: all .2s ease;
}}
[data-testid="stDownloadButton"] > button:hover {{
    border-color: {C["green"]};
    color: {C["green"]};
    background: rgba(0,200,150,.05);
}}

/* ── Text input (search) ── */
[data-testid="stTextInput"] input {{
    background: {C["surface2"]} !important;
    border-color: {C["border"]} !important;
    color: {C["text"]} !important;
    border-radius: 8px !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: {C["green"]} !important;
    box-shadow: 0 0 0 2px rgba(0,200,150,.15) !important;
}}

/* ── Selectbox ── */
[data-baseweb="select"] > div {{
    background-color: {C["surface2"]} !important;
    border-color: {C["border"]} !important;
    border-radius: 8px !important;
    color: {C["text"]} !important;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: {C["bg"]}; }}
::-webkit-scrollbar-thumb {{ background: {C["border2"]}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: {C["green"]}; }}

/* ── Section header HTML blocks ── */
.section-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 1.4rem 0 .5rem;
}}
.section-header .sh-icon {{
    width: 32px; height: 32px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}}
.section-header .sh-title {{
    font-size: 17px;
    font-weight: 700;
    color: {C["text"]};
    line-height: 1.2;
}}
.section-header .sh-sub {{
    font-size: 12px;
    color: {C["muted"]};
    margin-top: 2px;
}}

/* ── App header bar ── */
.app-header {{
    display: flex;
    align-items: center;
    gap: 14px;
    padding: .6rem 0 1.2rem;
    border-bottom: 1px solid {C["border"]};
    margin-bottom: .4rem;
}}
.app-header .logo-box {{
    width: 42px; height: 42px;
    background: linear-gradient(135deg, {C["green"]}, {C["blue"]});
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
}}
.app-header .app-title {{
    font-size: 20px;
    font-weight: 700;
    color: {C["text"]};
    line-height: 1.2;
}}
.app-header .app-sub {{
    font-size: 12px;
    color: {C["muted"]};
}}
.app-header .db-status {{
    margin-left: auto;
    display: flex; align-items: center; gap: 6px;
    font-size: 11px;
    color: {C["muted"]};
    background: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius: 20px;
    padding: 5px 12px;
}}
.db-dot-ok  {{ color: {C["green"]};  font-size: 8px; }}
.db-dot-err {{ color: {C["red"]};    font-size: 8px; }}

/* ── AI chat panel ── */
.ai-panel-header {{
    display: flex; align-items: center; gap: 8px;
    padding-bottom: 10px;
    border-bottom: 1px solid {C["border"]};
    margin-bottom: 10px;
}}
.ai-panel-header .ai-icon {{
    width: 28px; height: 28px;
    background: linear-gradient(135deg, {C["purple"]}, {C["blue"]});
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
}}
.ai-panel-header .ai-title {{
    font-size: 13px; font-weight: 600;
    color: {C["text"]};
}}
.ai-panel-header .ai-sub {{
    font-size: 10px; color: {C["muted"]};
}}

.chat-bubble-user {{
    background: rgba(0,200,150,.12);
    border: 1px solid rgba(0,200,150,.22);
    border-radius: 10px 10px 2px 10px;
    padding: 8px 11px;
    font-size: 12px;
    color: {C["text"]};
    margin: 4px 0;
    text-align: right;
}}
.chat-bubble-assistant {{
    background: {C["surface2"]};
    border: 1px solid {C["border"]};
    border-radius: 2px 10px 10px 10px;
    padding: 8px 11px;
    font-size: 12px;
    color: {C["text"]};
    margin: 4px 0;
    line-height: 1.55;
}}
.chat-bubble-system {{
    background: rgba(155,89,245,.08);
    border: 1px solid rgba(155,89,245,.2);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 11px;
    color: {C["muted"]};
    text-align: center;
    margin: 4px 0;
}}
.chat-empty {{
    text-align: center;
    padding: 20px 10px;
    color: {C["dim"]};
    font-size: 12px;
    line-height: 1.7;
}}

/* ── Sidebar brand block ── */
.sidebar-brand {{
    padding: 4px 2px 14px;
    border-bottom: 1px solid {C["border"]};
    margin-bottom: 14px;
}}
.sidebar-brand .sb-logo {{
    width: 34px; height: 34px;
    background: linear-gradient(135deg, {C["green"]}, {C["blue"]});
    border-radius: 9px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 17px; margin-bottom: 6px;
}}
.sidebar-brand .sb-title {{
    font-size: 13px; font-weight: 700;
    color: {C["text"]}; line-height: 1.2;
}}
.sidebar-brand .sb-sub {{
    font-size: 10px; color: {C["muted"]};
}}

.db-badge-ok {{
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(0,200,150,.1);
    border: 1px solid rgba(0,200,150,.25);
    border-radius: 6px; padding: 4px 10px;
    font-size: 11px; color: {C["green"]};
    margin-top: 8px; width: 100%;
}}
.db-badge-err {{
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,69,96,.1);
    border: 1px solid rgba(255,69,96,.25);
    border-radius: 6px; padding: 4px 10px;
    font-size: 11px; color: {C["red"]};
    margin-top: 8px; width: 100%;
}}

/* ── Plotly chart container ── */
.js-plotly-plot .plotly {{ border-radius: 12px; }}

/* ── Divider ── */
hr {{ border-color: {C["border"]} !important; margin: 1rem 0; }}

/* ── No-data info box ── */
[data-testid="stInfo"] {{
    background: {C["surface"]} !important;
    border-color: {C["border"]} !important;
    color: {C["muted"]} !important;
    border-radius: 10px !important;
}}

/* Column alignment */
[data-testid="column"] {{ min-width: 0; }}
"""


def inject_css() -> None:
    clean_css = _CSS.replace("}}", "}").replace("{{", "{")
    st.markdown(f"<style>{clean_css}</style>", unsafe_allow_html=True)


# HTML helpers

def section_header(title: str, subtitle: str = "", icon: str = "ri-bar-chart-line",
                   icon_bg: str | None = None) -> None:
    bg = icon_bg or f"rgba(0,200,150,.15)"
    st.markdown(
        f"""
        <div class="section-header">
          <div class="sh-icon" style="background:{bg}">
            <i class="{icon}" style="color:{C['green']}"></i>
          </div>
          <div>
            <div class="sh-title">{title}</div>
            {'<div class="sh-sub">' + subtitle + '</div>' if subtitle else ''}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def app_header(db_ok: bool) -> None:
    dot_class = "db-dot-ok" if db_ok else "db-dot-err"
    dot_icon  = "ri-checkbox-blank-circle-fill"
    db_text   = "Connected" if db_ok else "Disconnected"
    st.markdown(
        f"""
        <div class="app-header">
          <div>
            <div class="app-title">Perishable Supply Chain</div>
            <div class="app-sub">Live analytics — Neon Postgres Star Schema</div>
          </div>
          <div class="db-status">
            <i class="{dot_icon} {dot_class}"></i>
            <span>DB {db_text}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

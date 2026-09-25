import logging
import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

from src.config import (
    DEFAULT_PM25_TARGET,
    OUTPUT_DIR,
    PM25_TARGETS,
    RISK_BAND_COLORS,
    RISK_CATEGORY_COLORS,
)
from src.frontend.generate_site import build as build_stitch_site
from src.loaders.biodiversity_loader import BiodiversityLoader
from src.loaders.dkv_loader import DKVLoader
from src.loaders.green_sentinel_loader import GreenSentinelLoader
from src.loaders.historical_loader import HistoricalMapLoader
from src.models.environmental_justice import EnvironmentalJusticeModel, JUSTICE_BAND_EDGES
from src.models.gentrification_model import GentrificationRiskModel, RISK_BAND_EDGES
from src.models.historical_gentrification import HistoricalGentrificationModel
from src.processors.feature_engineer import FeatureEngineer
from src.visualizations import (
    EnvironmentalJusticeVisualizer,
    MapVisualizer,
    RiskMatrixVisualizer,
    TrendVisualizer,
)
from src.frontend.streamlit_brand import BRAND_CSS, hero_html, sidebar_brand
from src.visualizations.historical_viz import HistoricalVisualizer
from src.visualizations.theme import apply_theme

logging.basicConfig(level=logging.ERROR)

st.set_page_config(
    page_title="GreenSense Debrecen — Environmental Intelligence",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _find_available_port(start: int = 8899, attempts: int = 200) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("Could not find a free local port for Stitch frontend server.")


class _QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@st.cache_resource
def _serve_stitch_frontend() -> tuple[str, int]:
    build_stitch_site()
    site_dir = OUTPUT_DIR / "frontend_site"
    if not site_dir.exists():
        raise RuntimeError(f"Expected generated site directory at {site_dir}")

    entry = "loading.html" if (site_dir / "loading.html").exists() else "index.html"
    port = _find_available_port()
    handler = partial(_QuietStaticHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return entry, port


def _render_stitch_default() -> None:
    entry, port = _serve_stitch_frontend()
    st.markdown(
        """
        <style>
          [data-testid="stHeader"] { background: transparent; }
          [data-testid="stToolbar"] { right: 0.75rem; }
          .block-container { padding-top: 0.25rem; padding-bottom: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    components.iframe(f"http://127.0.0.1:{port}/{entry}", height=2200, scrolling=True)
    st.stop()


try:
    _render_stitch_default()
except Exception as stitch_error:
    st.warning(f"Stitch frontend unavailable, falling back to legacy Streamlit view. ({stitch_error})")

CSS = """
<style>
    .stApp { font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif; }
    h1, h2, h3 { color: #111827; letter-spacing: -0.01em; }

    /* ---------- Hero ---------- */
    .hero {
        display: flex; align-items: center; gap: 20px;
        padding: 26px 30px; margin-bottom: 8px; border-radius: 18px;
        background: linear-gradient(120deg, #0F766E 0%, #10B981 60%, #34D399 100%);
        color: white; box-shadow: 0 8px 24px rgba(16, 185, 129, 0.25);
    }
    .hero-emoji { font-size: 46px; line-height: 1; }
    .hero-title { font-size: 30px; font-weight: 800; line-height: 1.1; }
    .hero-sub { font-size: 14px; font-weight: 600; opacity: 0.92; text-transform: uppercase; letter-spacing: 0.08em; }
    .hero-tag { font-size: 13.5px; opacity: 0.88; margin-top: 6px; max-width: 880px; }

    /* ---------- KPI cards ---------- */
    .kpi-grid {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
        gap: 14px; margin: 16px 0 20px;
    }
    .kpi-card {
        background: #fff; border: 1px solid #E5E7EB; border-top: 4px solid var(--accent, #10B981);
        border-radius: 12px; padding: 13px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .kpi-icon { font-size: 22px; }
    .kpi-label { font-size: 11.5px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 6px; }
    .kpi-value { font-size: 20px; font-weight: 700; color: #111827; margin-top: 2px; }

    /* ---------- Risk chips ---------- */
    .risk-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 10px; }
    .risk-chip {
        display: inline-flex; align-items: center; gap: 7px; padding: 5px 11px;
        border-radius: 999px; background: #F9FAFB; border: 1px solid #E5E7EB;
        font-size: 12.5px; font-weight: 600; color: #111827;
    }
    .risk-chip .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }

    /* ---------- Tabs ---------- */
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0; font-weight: 600; padding: 8px 16px;
    }
    .stTabs [data-baseweb="tab"]:hover { background: #ECFDF5; }
    .stTabs [aria-selected="true"] { color: #0F766E !important; }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        background: #F7FAF9; border-right: 1px solid #E5E7EB;
    }
    .sb-brand { display: flex; align-items: center; gap: 12px; padding: 6px 2px 4px; }
    .sb-brand .sb-logo {
        width: 42px; height: 42px; border-radius: 12px; flex-shrink: 0;
        background: linear-gradient(135deg, #0F766E, #10B981);
        display: flex; align-items: center; justify-content: center; font-size: 22px;
    }
    .sb-brand .sb-name { font-weight: 800; font-size: 16px; color: #0F766E; line-height: 1.15; }
    .sb-brand .sb-sub { font-size: 11px; color: #6B7280; }

    /* ---------- Buttons ---------- */
    .stButton button, [data-testid="stDownloadButton"] button {
        border-radius: 10px; font-weight: 600;
        border: 1px solid #10B981; background: #10B981; color: white;
    }
    .stButton button:hover, [data-testid="stDownloadButton"] button:hover {
        background: #059669; border-color: #059669; color: white;
    }

    /* ---------- Footer ---------- */
    .footer {
        margin-top: 30px; padding: 16px 4px 4px; border-top: 1px solid #E5E7EB;
        color: #6B7280; font-size: 12.5px; text-align: center;
    }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(BRAND_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading and processing Green Sentinel data...")
def load_data() -> dict:
    """Load, clean, and model all datasets. Returns a dict of DataFrames."""
    gs = GreenSentinelLoader().run()
    dkv = DKVLoader().run()
    bio = BiodiversityLoader().run()

    long_data = gs.get_data()
    coords = long_data[["station", "latitude", "longitude"]].drop_duplicates()
    transit = dkv.compute_transit_accessibility(coords)

    fe = FeatureEngineer(long_data, transit_data=transit)
    features = fe.create_all_features()
    daily = fe.daily_data
    improvement = fe.improvement_metrics

    model = GentrificationRiskModel(features).fit_clustering()
    report = model.generate_risk_report()

    ej_model = EnvironmentalJusticeModel(report, bio)
    justice = ej_model.justice_report

    hist_loader = HistoricalMapLoader()
    hist_loader.run()
    hist_frame = HistoricalGentrificationModel(report).compute()

    quality = gs.get_quality_report()

    return {
        "long_data": long_data,
        "daily": daily,
        "improvement": improvement,
        "features": features,
        "report": report,
        "quality": quality,
        "transit": transit,
        "bus_stops": int(len(dkv.get_bus_stops())),
        "justice": justice,
        "bio": bio,
        "obs": bio.get_data(),
        "hist_frame": hist_frame,
        "hist_georef": hist_loader.georef(),
        "hist_mosaics": hist_loader.mosaics,
        "hist_available": hist_loader.is_available(),
    }


data = load_data()

report: pd.DataFrame = data["report"]
daily: pd.DataFrame = data["daily"]
improvement: pd.DataFrame = data["improvement"]
quality: dict = data["quality"]
long_data: pd.DataFrame = data["long_data"]
justice: pd.DataFrame = data["justice"]
bio = data["bio"]
obs: pd.DataFrame = data["obs"]

hist_frame: pd.DataFrame = data["hist_frame"]
hist_georef: dict = data["hist_georef"]
hist_mosaics: dict = data["hist_mosaics"]
hist_available: bool = data["hist_available"]

label_map: dict[str, str] = {
    r.station: f"{r.station} · {r.location}" for r in report.itertuples()
}
CAT_ORDER = ["Emerging Green Zones", "Established Clean Areas", "Stable Neighborhoods", "Challenge Zones"]
present_cats = [c for c in CAT_ORDER if c in report["risk_category"].values]

ej_viz = EnvironmentalJusticeVisualizer(justice, obs, daily, label_map)
hist_viz = HistoricalVisualizer(hist_frame, hist_georef, hist_mosaics)

# ---------------------------------------------------------------------------
# SIDEBAR — brand, live risk summary, functional filter
# ---------------------------------------------------------------------------
st.sidebar.markdown(sidebar_brand(), unsafe_allow_html=True)

st.sidebar.markdown("### 📍 Live Risk Summary")
counts = report["risk_category"].value_counts()
chips_html = '<div class="risk-chips">'
for cat in present_cats:
    color = RISK_CATEGORY_COLORS[cat]
    chips_html += f'<span class="risk-chip"><span class="dot" style="background:{color}"></span>{cat}: {int(counts.get(cat, 0))}</span>'
chips_html += "</div>"
st.sidebar.markdown(chips_html, unsafe_allow_html=True)

selected_categories = st.sidebar.multiselect(
    "Filter by risk category",
    present_cats,
    default=present_cats,
    help="Applies to the Risk Map, Risk Matrix, and Environmental Justice tabs.",
)
filtered_report = report[report["risk_category"].isin(selected_categories)]
justice_filtered = justice[justice["risk_category"].isin(selected_categories)]

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **The story:** neighborhoods that are cleaning up fastest *and* stay
    reachable by transit are the most exposed to gentrification pressure.

    Built on 30 days of **Green Sentinel** monitoring data and **DKV**
    public-transport data.
    """
)
st.sidebar.caption("DEIK.AI Challenge 2026 — Category B · Urban Environmental Monitoring")

# ---------------------------------------------------------------------------
# VISUALIZERS
# ---------------------------------------------------------------------------
map_viz = MapVisualizer(filtered_report)
trend_viz = TrendVisualizer(daily, improvement, label_map=label_map)
risk_viz = RiskMatrixVisualizer(filtered_report)


def band_color(score: float) -> str:
    if score < 31:
        return RISK_BAND_COLORS["Low"]
    if score < 61:
        return RISK_BAND_COLORS["Moderate"]
    if score < 81:
        return RISK_BAND_COLORS["High"]
    return RISK_BAND_COLORS["Critical"]


def band_cell(v: float) -> str:
    return f"background-color:{band_color(v)};color:white;font-weight:700"


def cat_cell(v: str) -> str:
    return (
        f"background-color:{RISK_CATEGORY_COLORS[v]};color:white;font-weight:700"
        if v in RISK_CATEGORY_COLORS
        else ""
    )


def band_name_cell(v: str) -> str:
    return (
        f"background-color:{RISK_BAND_COLORS[v]};color:white;font-weight:700"
        if v in RISK_BAND_COLORS
        else ""
    )


def justice_band_color(score: float) -> str:
    if score >= 80:
        return "#065F46"
    if score >= 60:
        return "#10B981"
    if score >= 40:
        return "#F59E0B"
    return "#EF4444"


def justice_band_cell(v: float) -> str:
    return (
        f"background-color:{justice_band_color(v)};color:white;font-weight:700"
        if pd.notna(v)
        else ""
    )


def justice_band_name_cell(v: str) -> str:
    color = {
        "Excellent": "#065F46",
        "Good": "#10B981",
        "Moderate": "#F59E0B",
        "Needs Attention": "#EF4444",
    }.get(v, "")
    return f"background-color:{color};color:white;font-weight:700" if color else ""


def justice_bool_cell(v: object) -> str:
    if v is True:
        return "background-color:#10B981;color:white;font-weight:700"
    if v is False:
        return "background-color:#6B7280;color:white;font-weight:700"
    return ""


top_risk = report.sort_values("risk_score", ascending=False).iloc[0]
top_risk_label = label_map.get(top_risk["station"], top_risk["station"])


def kpi_row(cards: list[tuple[str, str, str, str]]) -> None:
    """Render a row of KPI cards: (icon, label, value, accent_color)."""
    html = '<div class="kpi-grid">'
    for icon, label, value, accent in cards:
        html += (
            f'<div class="kpi-card" style="--accent:{accent}">'
            f'<div class="kpi-icon">{icon}</div>'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f"</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def hero() -> None:
    st.markdown(hero_html(), unsafe_allow_html=True)


TAB1, TAB2, TAB3, TAB4, TAB5, TAB6, TAB7, TAB8 = st.tabs(
    [
        "🗺️ Risk Map",
        "📈 Pollution Trends",
        "⚠️ Risk Matrix",
        "🏆 Risk Scoreboard",
        "📊 Detailed Analysis",
        "🔍 Data Quality",
        "🌿 Environmental Justice",
        "🕰️ Then & Now",
    ]
)

with TAB1:
    hero()

    fastest_window = (
        report[report["timeline_status"] == "On track"].sort_values("months_to_target")
    )
    if not fastest_window.empty:
        fw = fastest_window.iloc[0]
        window_kpi = (
            f"{label_map.get(fw['station'], fw['station'])} → WHO-5 in ~{fw['months_to_target']:.0f} mo"
        )
    else:
        window_kpi = "No station on track"

    kpi_row(
        [
            ("🛰️", "Stations Analyzed", f"{report['station'].nunique()}", "#10B981"),
            ("⛳", "Highest Risk", f"{top_risk_label} ({top_risk['risk_score']:.0f}/100)", band_color(top_risk["risk_score"])),
            ("⏳", "Clean-Air Window", window_kpi, "#3B82F6"),
            ("📊", "Data Points", f"{quality['total_raw_rows']:,}", "#8B5CF6"),
            ("🚌", "Bus Stops Mapped", f"{data['bus_stops']:,}", "#F59E0B"),
        ]
    )

    st.subheader("Environmental Justice Map")

    col_ctrl, col_map = st.columns([1, 4])
    with col_ctrl:
        map_color_by = st.radio(
            "Color markers by:",
            ["Risk category", "Clean-air window"],
            index=0,
            help="'Clean-air window' colors stations by months until they reach the "
            "WHO annual PM2.5 guideline of 5 µg/m³.",
        )
        window_target = DEFAULT_PM25_TARGET
        st.caption(f"Window target: {window_target} µg/m³ (WHO annual guideline)")
        fmt_months = lambda v: f"{v:.1f}" if v == v else "—"
        window_rows = report[
            report["timeline_status"] == "On track"
        ].sort_values("months_to_target")
        on_track_count = len(window_rows)
        not_track_count = int((report["timeline_status"] == "Not on track").sum())
        st.markdown(
            f"**{on_track_count}** station(s) above the WHO target and improving; "
            f"**{not_track_count}** not on track. Fastest: "
            + (
                f"{label_map.get(window_rows.iloc[0]['station'], window_rows.iloc[0]['station'])} "
                f"in {fmt_months(window_rows.iloc[0]['months_to_target'])} months."
                if on_track_count > 0
                else "—"
            )
        )
    with col_map:
        st_folium(
            map_viz.create_folium_map(color_by="months_to_target" if map_color_by == "Clean-air window" else "risk_category"),
            width="stretch",
            height=620,
        )

    st.markdown(
        """
        **Risk Categories**
        - 🔴 **Emerging Green Zones** — improving fast + still polluted = gentrification risk
        - 🟢 **Established Clean Areas** — already clean = already developed
        - 🟡 **Stable Neighborhoods** — no major change
        - 🟠 **Challenge Zones** — degrading + polluted = needs help first

        **Marker radius** scales with the **Risk Score** (larger = more urgent).
        """
    )

    top_window = report[report["timeline_status"] == "On track"].sort_values("months_to_target")
    if not top_window.empty:
        w = top_window.iloc[0]
        w_label = label_map.get(w["station"], w["station"])
        st.info(
            f"**⏳ Gentrification opportunity window:** {w_label} is at "
            f"{w['current_PM2.5']:.1f} µg/m³ and falling "
            f"{w['pm25_trend']:.4f} µg/m³/day — it reaches the WHO 5 µg/m³ guideline in "
            f"**~{w['months_to_target']:.0f} month(s)** (est. {w['target_date']}). "
            "That is the realistic window for intervention: affordable-housing protection "
            "should be budgeted **this quarter**, not next year."
        )
    st.caption(
        "Note: the brief's worked example (PM2.5 ≈ 38–45 µg/m³, 18–40 months) uses "
        "illustrative figures that do not match this dataset — Debrecen's daily means were "
        "already 2–6 µg/m³ in the window, and every station already meets the WHO 15 and "
        "EU 10 µg/m³ targets."
    )

with TAB2:
    st.subheader("30-Day Pollution Trends")

    col_left, col_right = st.columns([1, 3])
    with col_left:
        selected_stations = st.multiselect(
            "Select stations to compare:",
            report["station"].unique().tolist(),
            default=report["station"].unique().tolist()[:5],
            format_func=lambda s: label_map.get(s, s),
        )
        selected_pollutant = st.radio(
            "Choose pollutant:",
            ["PM2.5", "PM10", "NO2", "O3", "TVOC"],
            index=0,
        )
    with col_right:
        if selected_stations:
            st.plotly_chart(
                trend_viz.plot_pollution_timeseries(selected_stations, selected_pollutant),
                width="stretch",
            )
        else:
            st.info("Select at least one station to see the trend chart.")

    st.subheader("Environmental Improvement Index (all stations)")
    st.plotly_chart(trend_viz.plot_trend_slopes(), width="stretch")

    with st.expander("Pollutant distribution overview"):
        st.plotly_chart(trend_viz.plot_pollutant_distribution(), width="stretch")

with TAB3:
    st.subheader("Gentrification Risk Analysis")
    st.markdown(
        "**Insight:** Neighborhoods improving fastest while still polluted are under the "
        "highest gentrification pressure. Combine with transit accessibility: good bus "
        "access makes an improving district attractive for development."
    )

    if filtered_report.empty:
        st.warning("No stations match the selected risk categories in the sidebar.")
    else:
        st.plotly_chart(risk_viz.plot_risk_quadrant(), width="stretch")

        st.subheader("Station Risk Classification")
        risk_table = filtered_report[
            [
                "station",
                "location",
                "risk_category",
                "risk_score",
                "risk_band",
                "env_improvement_index",
                "current_PM2.5",
                "pm25_volatility",
                "bus_stops_nearby",
                "months_to_target",
                "timeline_status",
            ]
        ].rename(
            columns={
                "station": "Station",
                "location": "Location",
                "risk_category": "Risk Category",
                "risk_score": "Risk Score",
                "risk_band": "Risk Band",
                "env_improvement_index": "Improvement Index",
                "current_PM2.5": "Current PM2.5",
                "pm25_volatility": "PM2.5 Volatility",
                "bus_stops_nearby": "Bus Stops ≤1km",
                "months_to_target": "Months to Clean Air",
                "timeline_status": "Clean-Air Status",
            }
        ).sort_values("Risk Score", ascending=False)

        styled_risk = risk_table.style.map(
            lambda v: band_cell(v) if pd.notna(v) else "",
            subset=["Risk Score"],
        )
        styled_risk = styled_risk.map(cat_cell, subset=["Risk Category"])
        styled_risk = styled_risk.map(lambda v: band_name_cell(v) if not pd.isna(v) else "", subset=["Risk Band"])
        styled_risk = styled_risk.format(
            {
                "Risk Score": "{:.0f}",
                "Improvement Index": "{:.3f}",
                "Current PM2.5": "{:.1f}",
                "PM2.5 Volatility": "{:.3f}",
                "Bus Stops ≤1km": "{:.0f}",
                "Months to Clean Air": "{:.1f}",
            },
            na_rep="✓ Met",
        )
        st.dataframe(styled_risk, width="stretch", hide_index=True)
        st.caption(
            f"'Months to Clean Air' = linear extrapolation to the WHO annual guideline "
            f"({PM25_TARGETS[DEFAULT_PM25_TARGET]:.0f} µg/m³). 'Not on track' = PM2.5 flat/rising."
        )

        csv_report = risk_table.to_csv(index=False).encode("utf-8")
        st.download_button("Download risk report (CSV)", csv_report, "gentrification_risk_report.csv", "text/csv")

        high_risk = filtered_report[filtered_report["risk_category"] == "Emerging Green Zones"]
        if len(high_risk) > 0:
            station_list = ", ".join(label_map.get(s, s) for s in high_risk["station"].tolist())
            st.warning(
                f"**⚠️ Gentrification Alert:** {len(high_risk)} station(s) show "
                f"'Emerging Green Zone' status ({station_list}). "
                "These neighborhoods need affordable housing protection policies."
            )

        risky = filtered_report[
            filtered_report["risk_category"] == "Emerging Green Zones"
        ].sort_values("bus_stops_nearby", ascending=False)
        if not risky.empty:
            top = risky.iloc[0]
            st.info(
                f"**🚌 Transit signal:** {label_map.get(top['station'], top['station'])} ranks highest for "
                f"transit access among at-risk stations ({int(top['bus_stops_nearby'])} bus stops within 1 km), "
                "combining clean-air momentum with development connectivity."
            )

with TAB4:
    st.subheader("🏆 Gentrification Risk Scoreboard")
    st.markdown(
        """
        A single **0–100 Risk Score** per station — a weighted composite of
        environmental improvement (40%), current pollution (30%), transit
        accessibility (20%), and signal stability (10%). Higher = more urgent.
        """
    )

    board = report.sort_values("risk_score", ascending=False).copy()
    board["Neighborhood"] = board["station"].map(label_map)
    board["Rank"] = range(1, len(board) + 1)
    board_plot = board[["Neighborhood", "risk_score", "risk_band"]].copy()

    fig_board = px.bar(
        board_plot,
        x="risk_score",
        y="Neighborhood",
        orientation="h",
        color="risk_band",
        color_discrete_map=RISK_BAND_COLORS,
        labels={
            "risk_score": "Risk Score (0–100)",
            "Neighborhood": "",
            "risk_band": "Risk Band",
        },
        title="All 16 Stations Ranked by Gentrification Risk",
    )
    fig_board.update_layout(legend_title_text="Risk Band", yaxis=dict(dtick=1))
    fig_board.update_traces(texttemplate="%{x:.0f}", textposition="outside")
    st.plotly_chart(apply_theme(fig_board), width="stretch")

    st.markdown(
        """
        **Interpretation** — 🟢 Low 0–30 · 🟡 Moderate 31–60 · 🔴 High 61–80 · 🟤 Critical 81–100
        """
    )

    board_table = board[
        [
            "Rank",
            "Neighborhood",
            "risk_score",
            "risk_band",
            "risk_category",
            "imp_score",
            "pol_score",
            "transit_score",
            "stab_score",
            "bus_stops_nearby",
            "current_PM2.5",
            "pm25_trend",
            "months_to_target",
            "timeline_status",
            "target_date",
        ]
    ].rename(
        columns={
            "risk_score": "Risk Score",
            "risk_band": "Risk Band",
            "risk_category": "Risk Category",
            "imp_score": "Improvement (40%)",
            "pol_score": "Pollution (30%)",
            "transit_score": "Transit (20%)",
            "stab_score": "Stability (10%)",
            "bus_stops_nearby": "Bus Stops ≤1km",
            "current_PM2.5": "Current PM2.5",
            "pm25_trend": "PM2.5 Rate/day",
            "months_to_target": "Months to Clean Air",
            "timeline_status": "Clean-Air Status",
            "target_date": "Target Date",
        }
    )

    styled_board = board_table.style.map(
        lambda v: band_cell(v) if pd.notna(v) else "", subset=["Risk Score"]
    )
    styled_board = styled_board.map(lambda v: band_name_cell(v) if not pd.isna(v) else "", subset=["Risk Band"])
    styled_board = styled_board.map(lambda v: cat_cell(v) if not pd.isna(v) else "", subset=["Risk Category"])
    styled_board = styled_board.format(
        {
            "Risk Score": "{:.0f}",
            "Improvement (40%)": "{:.1f}",
            "Pollution (30%)": "{:.1f}",
            "Transit (20%)": "{:.1f}",
            "Stability (10%)": "{:.1f}",
            "Bus Stops ≤1km": "{:.0f}",
            "Current PM2.5": "{:.1f}",
            "PM2.5 Rate/day": "{:.4f}",
            "Months to Clean Air": "{:.1f}",
        },
        na_rep="✓ Met",
    )
    st.dataframe(styled_board, width="stretch", hide_index=True)

    csv_board = board_table.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download scoreboard (CSV)", csv_board, "gentrification_risk_scoreboard.csv", "text/csv"
    )

    st.subheader("⏳ Clean Air Timeline — who cleans up first?")
    timeline = board.copy()
    timeline["x_val"] = timeline["months_to_target"].fillna(0.0)
    timeline["display"] = timeline["timeline_status"].map({
        "Already met": "Already met (0)",
        "Not on track": "Not on track",
    })
    timeline["color"] = timeline["timeline_status"].map({
        "Already met": "#065F46",
        "Not on track": "#6B7280",
    })
    for _, row in timeline[timeline["timeline_status"] == "On track"].iterrows():
        timeline.loc[row.name, "display"] = f"{row['months_to_target']:.1f} mo"
        timeline.loc[row.name, "color"] = (
            "#EF4444" if row["months_to_target"] <= 1
            else "#F97316" if row["months_to_target"] <= 3
            else "#FBBF24" if row["months_to_target"] <= 6
            else "#10B981"
        )
    timeline = timeline.sort_values(
        ["timeline_status", "x_val"],
        key=lambda s: s.map({"Already met": 0, "On track": 1, "Not on track": 2}),
        ascending=True,
    )

    fig_tl = px.bar(
        timeline,
        x="x_val",
        y="Neighborhood",
        orientation="h",
        color="color",
        color_discrete_map="identity",
        text="display",
        labels={"x_val": "Months to reach WHO 5 µg/m³ guideline", "Neighborhood": "", "color": ""},
        title="Months Until Clean Air (WHO Annual PM2.5 = 5 µg/m³)",
        category_orders={"Neighborhood": timeline["Neighborhood"].tolist()},
    )
    fig_tl.update_layout(showlegend=False, yaxis=dict(dtick=1))
    fig_tl.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(apply_theme(fig_tl), width="stretch")

    st.markdown(
        """
        **Reading this chart** — green = already at the WHO guideline; the colored bars show
        how long each station needs to get there at its current improvement rate
        (red = under a month, orange = 1–3 months); gray = PM2.5 flat/rising (**not on track**).
        """
    )
    st.caption(
        "Honesty note: every Debrecen station already meets the WHO 24-hour/IT-3 (15 µg/m³) "
        "and EU-2030 (10 µg/m³) targets. This timeline therefore shows the *stricter* WHO "
        "annual guideline (5 µg/m³), the only standard with a real gradient in this window. "
        "The brief's worked example (38–45 µg/m³, 18–40 months) is used here as an "
        "illustrative scenario, not derived from this dataset."
    )

    st.subheader("🎯 Top 3 Neighborhoods Needing Policy Intervention")
    top3 = report.sort_values("risk_score", ascending=False).head(3)
    for i, (_, row) in enumerate(top3.iterrows(), start=1):
        lbl = label_map.get(row["station"], row["station"])
        note = ""
        if row["risk_category"] == "Emerging Green Zones":
            note = (
                "Fastest improving while still polluted → **act now**: lock "
                "affordable-housing quotas into any rezoning, support a community "
                "land trust, and stabilize rents."
            )
        elif row["risk_category"] == "Challenge Zones":
            note = (
                "Environment degrading and polluted → **first line of action**: "
                "prioritize air-quality remediation and green investment before "
                "any development."
            )
        elif row["risk_category"] == "Established Clean Areas":
            note = (
                "Already clean → **monitor**: development pressure is likely; "
                "preserve green spaces and buffer zones."
            )
        else:
            note = "Stable → **watch**: keep monitoring and prepare contingency policy."
        if row["transit_score"] < 20:
            note += (
                " Low transit access caps immediate displacement pressure — "
                "treat as **monitor**, not urgent action."
            )
        st.markdown(
            f"""
            <div class="kpi-card" style="--accent:{band_color(row['risk_score'])};margin-bottom:6px">
                <div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.05em">#{i} · Risk {row['risk_score']:.0f}/100 · {row['risk_band'].lower()} pressure · {row['risk_category']}</div>
                <div style="font-size:17px;font-weight:700;color:#111827;margin-top:2px">{lbl}</div>
                <div style="font-size:13px;color:#374151;margin-top:4px">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption(
        "Risk Score = 0.40×improvement + 0.30×pollution + 0.20×transit + 0.10×stability. "
        "Each component is min-max normalized across the 16 stations; volatility contributes "
        "inverted (low volatility = reliable signal)."
    )

with TAB5:
    st.subheader("Deep Dive Analysis")

    station_options = report["station"].tolist()
    selected = st.selectbox(
        "Select a station to analyze:",
        station_options,
        format_func=lambda s: label_map.get(s, s),
    )

    station_row = report[report["station"] == selected].iloc[0]
    risk_color = RISK_CATEGORY_COLORS.get(station_row["risk_category"], "#6B7280")

    kpi_row(
        [
            ("📍", "Neighborhood", label_map.get(selected, selected), "#3B82F6"),
            ("🎯", "Risk Score", f"{station_row['risk_score']:.0f}/100 · {station_row['risk_band']}", band_color(station_row["risk_score"])),
            ("🏷️", "Risk Category", station_row["risk_category"], risk_color),
            ("📈", "Improvement Index", f"{station_row['env_improvement_index']:.3f}", "#10B981"),
            ("🚌", "Transit Access", f"{int(station_row['bus_stops_nearby'])} stops ≤1km", "#F59E0B"),
        ]
    )

    station_wide = (
        daily[daily["station"] == selected]
        .pivot(index="timestamp", columns="measurement_type", values="value")
        .reset_index()
        .set_index("timestamp")
    )

    st.subheader("Air Quality Over Time")
    air_cols = [c for c in ["PM2.5", "PM10", "NO2", "O3", "TVOC"] if c in station_wide.columns]
    if air_cols:
        fig_air = px.line(
            station_wide.reset_index(),
            x="timestamp",
            y=air_cols,
            title=f"Pollution Levels — {label_map.get(selected, selected)}",
            labels={"value": "Concentration (µg/m³)", "timestamp": "Date", "variable": "Pollutant"},
        )
        st.plotly_chart(apply_theme(fig_air), width="stretch")

    st.subheader("Meteorological Context")
    weather_cols = [c for c in ["Humidity", "Pressure", "Wind_Speed"] if c in station_wide.columns]
    if weather_cols:
        fig_weather = px.line(
            station_wide.reset_index(),
            x="timestamp",
            y=weather_cols,
            title=f"Weather Conditions — {label_map.get(selected, selected)}",
            labels={"value": "Value", "timestamp": "Date", "variable": "Measurement"},
        )
        st.plotly_chart(apply_theme(fig_weather), width="stretch")

    st.subheader("Pollutant Summary Statistics")
    if not station_wide.empty and air_cols:
        stats = station_wide[air_cols].describe().T
        st.dataframe(
            stats,
            width="stretch",
            column_config={
                "mean": st.column_config.NumberColumn("Mean", format="%.2f"),
                "std": st.column_config.NumberColumn("Std", format="%.2f"),
                "min": st.column_config.NumberColumn("Min", format="%.2f"),
                "25%": st.column_config.NumberColumn("25%", format="%.2f"),
                "50%": st.column_config.NumberColumn("Median", format="%.2f"),
                "75%": st.column_config.NumberColumn("75%", format="%.2f"),
                "max": st.column_config.NumberColumn("Max", format="%.2f"),
            },
        )

with TAB6:
    st.subheader("Data Quality & Anomaly Handling")

    total = quality["total_raw_rows"]
    n_anom = quality["negative_anomalies"]
    pct_anom = quality["negative_anomaly_pct"]
    n_out = quality["outliers_flagged"]

    kpi_row(
        [
            ("🗃️", "Total Records", f"{total:,}", "#3B82F6"),
            ("⚠️", "Negative Anomalies", f"{n_anom:,} ({pct_anom:.2f}%)", "#EF4444"),
            ("🔎", "Outliers Flagged (>3σ)", f"{n_out:,}", "#F59E0B"),
            ("✅", "Missing After Imputation", "0", "#10B981"),
        ]
    )

    st.info(
        """
        ✓ **Negative Values:** Flagged as anomalies, replaced with NaN before analysis.
        ✓ **Missing Data:** Imputed using forward/backward fill by station + measurement type.
        ✓ **Outliers (>3σ):** Detected {} — retained for analysis (may be real pollution events).
        ✓ **Timestamps:** Parsed and validated across all stations.
        """.format(n_out)
    )

    st.subheader("Data Quality by Station")
    location_by_station = long_data.groupby("station")["location"].first().rename("Location")
    per_station = (
        long_data.groupby("station")
        .agg(
            Records=("value", "count"),
            Missing_Pct=("value", lambda s: round(s.isna().mean() * 100, 2)),
            Measurement_Types=("measurement_type", "nunique"),
        )
        .reset_index()
        .merge(location_by_station, on="station")
        .rename(columns={"station": "Station"})
    )
    per_station["Date_Start"] = long_data.groupby("station")["timestamp"].min().dt.date.values
    per_station["Date_End"] = long_data.groupby("station")["timestamp"].max().dt.date.values
    per_station["Coverage"] = (100 - per_station["Missing_Pct"]).round(0).astype(int)

    st.dataframe(
        per_station,
        width="stretch",
        hide_index=True,
        column_config={
            "Location": st.column_config.TextColumn("Location"),
            "Records": st.column_config.NumberColumn("Records", format="%d"),
            "Missing_Pct": st.column_config.NumberColumn("Missing %", format="%.2f%%"),
            "Measurement_Types": st.column_config.NumberColumn("Measurement Types", format="%d"),
            "Coverage": st.column_config.ProgressColumn(
                "Coverage", min_value=0, max_value=100, format="%.0f%%"
            ),
        },
    )

    csv_quality = per_station.drop(columns=["Coverage"]).to_csv(index=False).encode("utf-8")
    st.download_button("Download data quality report (CSV)", csv_quality, "data_quality_report.csv", "text/csv")

    st.subheader("Methodology: Handling Real-World Data")
    st.markdown(
        """
        The Green Sentinel system produces real-world data with imperfections:

        1. **Negative Measurements** (e.g., PM2.5 = -2.5 µg/m³)
           - Source: sensor drift, calibration errors
           - Treatment: flagged as anomaly, replaced with NaN
           - Impact: {} anomalies documented ({}%)

        2. **Missing Data Points**
           - Source: sensor downtime, transmission failures
           - Treatment: forward-fill then backward-fill within each station + measurement type
           - Impact: preserves temporal continuity without artificial interpolation

        3. **Measurement Intervals**
           - Some stations record hourly, others less frequently
           - Solution: aggregated to daily means before trend analysis

        4. **Outliers** (e.g., PM2.5 spikes)
           - Likely pollution events or sensor errors
           - Decision: retained for analysis (documented as {} extreme values)
        """.format(n_anom, pct_anom, n_out)
    )

    st.subheader("Transit Accessibility Layer (DKV)")
    if not data["transit"].empty:
        st.markdown(
            """
            DKV transport data (687 bus stops, May 2026 statistics) provides the
            **transit connectivity** component of gentrification pressure.
            """
        )
        st.dataframe(data["transit"], width="stretch", hide_index=True)

with TAB7:
    bio_meta = bio.get_metadata()
    n_monitored = int(justice["biodiversity_available"].sum())
    top_justice = justice.sort_values("environmental_justice_score", ascending=False).iloc[0]

    kpi_row(
        [
            ("🌿", "Biodiversity Observations", f"{bio_meta['observations']:,}", "#10B981"),
            ("🦋", "Species Observed", f"{bio_meta['unique_species']:,}", "#3B82F6"),
            ("🌳", "Habitat Patches", f"{bio_meta['habitat_patches']:,}", "#059669"),
            ("📍", "Stations With Nature Data", f"{n_monitored}/16", "#F59E0B"),
            ("🏅", "Highest Justice Score", f"{label_map.get(top_justice['station'], top_justice['station'])} ({top_justice['environmental_justice_score']:.0f})", justice_band_color(top_justice["environmental_justice_score"])),
        ]
    )

    # ------------------------------------------------------------------ §1 OPENER
    st.subheader("1 · The question — is Debrecen getting cleaner, but is it fair?")
    st.markdown(
        """
        **Debrecen is getting cleaner — but is it fair?**

        Cleaner air is not automatically progress. If one neighborhood cleans up *and*
        recovers its nature while a family is priced out of it, the city gained a park
        and lost a community. So we asked three questions — and let the data answer.
        """
    )

    on_track_count = int((report["timeline_status"] == "On track").sum())
    met_count = int((report["timeline_status"] == "Already met").sum())
    fastest = report[report["timeline_status"] == "On track"].sort_values("months_to_target")
    fastest_line = "no station on track"
    if not fastest.empty:
        f = fastest.iloc[0]
        fastest_line = f"{label_map.get(f['station'], f['station'])} reaches the WHO-5 guideline in ~{f['months_to_target']:.0f} month(s)"

    top3_risk = report.sort_values("risk_score", ascending=False).head(3)
    top3_labels = [label_map.get(r.station, r.station) for r in top3_risk.itertuples()]

    q1, q2, q3 = st.columns(3)
    q1.markdown(
        f"""
        <div class="kpi-card" style="--accent:#3B82F6">
          <div style="font-size:13px;font-weight:700">Q1 — Which neighborhoods are improving?</div>
          <div style="font-size:13px;color:#374151;margin-top:6px">
            {met_count} of 16 already meet the WHO-5 guideline; {on_track_count} more are on track.
            Fastest: {fastest_line}.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top_nature_3 = justice[justice["biodiversity_available"]].sort_values(
        "biodiversity_recovery_index", ascending=False
    ).head(3)
    nature_names = ", ".join(
        label_map.get(r.station, r.station) for r in top_nature_3.itertuples()
    )
    q2.markdown(
        f"""
        <div class="kpi-card" style="--accent:#10B981">
          <div style="font-size:13px;font-weight:700">Q2 — Are they gaining nature too?</div>
          <div style="font-size:13px;color:#374151;margin-top:6px">
            Partly. The recovery leaders are {nature_names}. But several improving
            neighborhoods still have weak habitats — cleanup and nature are <b>not</b> automatic.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    q3.markdown(
        f"""
        <div class="kpi-card" style="--accent:#EF4444">
          <div style="font-size:13px;font-weight:700">Q3 — Who gets displaced before it gets better?</div>
          <div style="font-size:13px;color:#374151;margin-top:6px">
            The neighborhoods with the highest pressure: {' · '.join(top3_labels)}.
            These need protection <b>now</b>, not after prices jump.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------ §2 FINDINGS
    st.subheader("2 · Findings — the scorecard and three stories")
    st.plotly_chart(ej_viz.scorecard_grid(), width="stretch")
    st.caption(
        "Cards are tinted by justice band: 🟢 Excellent · 🟢 Good · 🟡 Moderate · 🔴 Needs Attention. "
        "‘Nature’ bars show “no data” for the 6 stations without biodiversity observations; "
        "those stations are scored from their three remaining components re-weighted to 100%."
    )

    detail_col, detail_chart = st.columns([1, 2])
    with detail_col:
        selected_station = st.selectbox(
            "Click a card / pick a neighborhood for details",
            justice["station"].tolist(),
            format_func=lambda s: label_map.get(s, s),
        )
    with detail_chart:
        st.plotly_chart(ej_viz.scorecard_detail(selected_station), width="stretch")

    detail_row = justice[justice["station"] == selected_station].iloc[0]
    if detail_row["biodiversity_available"]:
        nature_line = (
            f"Nature recovery <b>{detail_row['biodiversity_recovery_index']:.0f}/100</b>, "
            f"{int(detail_row.get('inat_species', 0))} species, "
            f"{detail_row['habitat_area_ha']:.1f} ha habitat "
            f"(quality {detail_row['habitat_quality']:.1f}/5)"
        )
    else:
        nature_line = "No biodiversity observations at this station (scored from air/transit only)"
    st.info(
        f"**{label_map.get(selected_station, selected_station)}** — Justice Score "
        f"**{detail_row['environmental_justice_score']:.0f}/100 ({detail_row['justice_band']})**, "
        f"risk {detail_row['risk_score']:.0f}/100 ({detail_row['risk_band']}), "
        f"transit {detail_row['transit_score']:.0f}/100, "
        f"clean-air {detail_row['pollution_component']:.0f}/100. {nature_line}."
    )

    st.markdown("#### Three stories the data tells")
    rows = {r["station"]: r for r in justice.to_dict("records")}

    def story_card(title: str, accent: str, head: str, body: str) -> None:
        st.markdown(
            f"""
            <div class="kpi-card" style="--accent:{accent};margin-bottom:8px">
                <div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.05em">{title}</div>
                <div style="font-size:16.5px;font-weight:800;color:#111827;margin-top:2px">{head}</div>
                <div style="font-size:13px;color:#374151;margin-top:5px">{body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    r14 = rows["DEB-KER14"]
    story_card(
        "Story A · The true winner to protect",
        "#10B981",
        f"DEB-KER14 — {r14['location']}",
        (
            f"The clearest real recovery: <b>{int(r14['inat_species'])} species</b> observed, "
            f"<b>{r14['habitat_area_ha']:.1f} ha of good–excellent habitat</b>, even a rare hoopoe, "
            f"and air that is already improving ({r14['biodiversity_recovery_index']:.0f}/100 nature). "
            f"Its Justice Score ({r14['environmental_justice_score']:.0f}) is capped only by "
            f"<b>zero transit</b> — which is why it is still affordable today. Protect it with "
            f"affordable-housing zoning <b>now</b>, before connectivity arrives and prices people out."
        ),
    )
    r12 = rows["DEB-KER12"]
    story_card(
        "Story B · Nature's comeback",
        "#059669",
        f"DEB-KER12 — {r12['location']}",
        (
            f"The highest nature recovery of all ({r12['biodiversity_recovery_index']:.0f}/100): a real "
            f"forest school sits in <b>{r12['habitat_area_ha']:.1f} ha</b> of woodland rated "
            f"{r12['habitat_quality']:.1f}/5, with a rare hoopoe and birds galore. Nature is back in "
            f"force — but so is pressure ({r12['risk_score']:.0f}/100 risk). This is the model of what "
            f"greening looks like: <b>preserve it and copy it elsewhere</b>."
        ),
    )
    r01 = rows["DEB-KER01"]
    r04 = rows["DEB-KER04"]
    story_card(
        "Story C · The industrial wasteland → restoration frontier",
        "#F59E0B",
        f"DEB-KER01 — {r01['location']}",
        (
            f"14 species but the weakest habitats — and the only station where PM2.5 is still "
            f"<b>rising</b>. {r01['habitat_area_ha']:.1f} ha of habitat, of which "
            f"<b>{r01['very_high_ha']:.1f} ha rated very-high restoration potential</b> "
            f"(industrial wasteland). Its twin {r04['station']} adds {r04['restorable_ha']:.1f} ha "
            f"more. Remediate and invest in green infrastructure <b>before</b> pressure arrives."
        ),
    )
    r11 = rows["DEB-KER11"]
    story_card(
        "Callout · The case that needs policy today",
        "#DC2626",
        f"DEB-KER11 — {r11['location']}",
        (
            f"Petőfi tér tops the Justice Score ({r11['environmental_justice_score']:.0f}/100): the best "
            f"combination of improving air, nature ({r11['biodiversity_recovery_index']:.0f}/100, "
            f"{int(r11['inat_species'])} species, two rare) and connectivity "
            f"({int(r11['bus_stops_nearby'])} bus stops). That exact mix makes it the most exposed — "
            f"<b>affordable-housing protection is urgent here</b>."
        ),
    )

    # ------------------------------------------------------------------ §3 ANALYSIS
    st.subheader("3 · Analysis — patterns across the whole city")
    st.plotly_chart(ej_viz.quadrant_matrix(), width="stretch")
    st.markdown(
        """
        **What each quadrant means**
        - 🔴 **Top-right — Gentrification risk + nature recovery (watch for displacement):** the best
          places to live are starting to attract development pressure.
        - 🟢 **Top-left — Nature recovering + low risk (protect these areas):** recoveries not yet under threat.
        - 🟠 **Bottom-left — Challenge zones:** degraded environments needing remediation before investment.
        - 🟣 **Bottom-right — Threats:** neighborhoods gentrifying *while losing nature* — most urgent.
        """
    )

    st.plotly_chart(ej_viz.comparative_heatmap(), width="stretch")

    st.markdown("#### Did nature recover as air improved?")
    st.plotly_chart(ej_viz.temporal_analysis(), width="stretch")
    st.caption(
        "Honest caveat: community observations were collected at ~1 per day per station, so this shows "
        "the city-wide *relationship* between air and nature, not proof that one caused the other. "
        "The correlation chart below is the strongest claim the data supports."
    )
    st.plotly_chart(ej_viz.biodiversity_correlation(), width="stretch")

    st.markdown("#### Where habitat can still be planted — restoration opportunity")
    st_folium(ej_viz.restoration_map(), width="stretch", height=560)
    st.caption(
        "Only neighborhoods with real restoration upside are shown. Marker size = hectares flagged "
        "high/very-high potential; color = current habitat quality. Each popup names the patches. "
        "These habitats can recover — ready to invest?"
    )

    # ------------------------------------------------------------------ §4 CALL TO ACTION
    st.subheader("4 · What should Debrecen's planners do?")
    winners = justice[
        justice["environmental_justice_score"] >= 60
    ].sort_values("environmental_justice_score", ascending=False)
    winner_names = ", ".join(label_map.get(r.station, r.station) for r in winners.head(3).itertuples())
    story_card(
        "Recommendation 1 · Protect the winners",
        "#10B981",
        "Affordable-housing policies for the highest justice scores",
        (
            f"{winner_names} combine improving air with strong nature and (often) connectivity. "
            "As property values rise with cleanliness, lock in affordable-housing quotas, community "
            "land trusts, and rent stabilization — before displacement, not after."
        ),
    )
    restorable_top = justice[justice["restorable_ha"] > 0].sort_values("restorable_ha", ascending=False)
    rest_names = ", ".join(f"{label_map.get(r.station, r.station)} ({r.restorable_ha:.1f} ha)" for r in restorable_top.head(3).itertuples())
    story_card(
        "Recommendation 2 · Restore the losers",
        "#F59E0B",
        "Green infrastructure where restoration potential is high",
        (
            f"{rest_names} hold the city's best restoration upside. Invest in brownfield "
            "remediation and green corridors <b>before</b> gentrification pressure arrives — "
            "protection is cheaper than recovery."
        ),
    )
    story_card(
        "Recommendation 3 · Monitor monthly",
        "#3B82F6",
        "Justice is dynamic — track it, don't assume it",
        (
            "Recompute the Justice Score quarterly. A single transit line can flip "
            "DEB-KER14 from protected haven to pressure zone in months. Alarm on band "
            "changes, not just absolute scores."
        ),
    )

    # ------------------------------------------------------------------ §5 METHODOLOGY
    st.subheader("5 · Methodology — how environmental justice was measured")
    st.markdown(
        f"""
        **Environmental Justice Score (0–100)** — the documented competition formula:
        ```
        40% Gentrification Risk   (air improving?  → risk_score)
        30% Biodiversity Recovery (nature returning → 0.40·species + 0.35·organisms + 0.25·birds)
        20% Transit Access        (development potential → bus stops ≤1km)
        10% Clean Current Air     (still unhealthy?  → 100 − pollution score)
        ─────────────────────────────────────────────────────────────
        = Environmental Justice Score (0–100)
        ```
        **Fairness of the formula**: improvement + connectivity raise the score because they broaden
        *access to opportunity* — that is the equity upside. The displacement side is handled by the
        companion Gentrification Risk Score, and by Recommendation 1 (protect winners).

        **Missing data**: the 6 stations without biodiversity observations are scored from their three
        available components **re-weighted to 100%** and clearly badge “no biodiversity data”.
        """
    )

    # ------------------------------------------------------------------ §6 TRANSPARENCY
    st.subheader("6 · Data transparency")
    jm1, jm2, jm3, jm4 = st.columns(4)
    jm1.metric("Biodiversity observations", f"{bio_meta['observations']:,}")
    jm2.metric("Unique species observed", f"{bio_meta['unique_species']:,}")
    jm3.metric("Habitat patches analyzed", f"{bio_meta['habitat_patches']:,}")
    jm4.metric("Stations with nature data", f"{n_monitored}/16")

    inat_dates = bio.get_inaturalist()["date_observed"]
    bird_dates = bio.get_birds()["date_observed"]
    st.markdown(
        f"""
        - **Sources:** iNaturalist (community science), OpenBioMaps birds (Debrecen Bird Project), PADAPT habitats.
        - **Time period:** iNaturalist {inat_dates.min():%b %d} – {inat_dates.max():%b %d}, 2026 ·
          birds {bird_dates.min():%b %d} – {bird_dates.max():%b %d}, 2026 · aligned with Green Sentinel monitoring.
        - **Confidence:** all observations are linked to monitoring stations (±500 m buffer); research-grade
          iNaturalist records verified by experts.
        - **Honesty:** observation cadence was ~1/day/station, so air–nature links are *cross-sectional*,
          not within-station recovery proof. The brief's worked example (274 records / 47 species) does not
          match the provided CSVs — the dashboard reports only the true numbers.
        """
    )

    justice_table = justice[
        [
            "station", "location", "risk_category", "risk_score", "biodiversity_available",
            "biodiversity_recovery_index", "transit_component", "pollution_component",
            "environmental_justice_score", "justice_band", "justice_trend", "restorable_ha",
        ]
    ].rename(
        columns={
            "station": "Station",
            "location": "Location",
            "risk_category": "Risk Category",
            "risk_score": "Risk Score",
            "biodiversity_available": "Nature Data",
            "biodiversity_recovery_index": "Nature Recovery",
            "transit_component": "Transit (20%)",
            "pollution_component": "Clean Air (10%)",
            "environmental_justice_score": "Justice Score",
            "justice_band": "Justice Band",
            "justice_trend": "Trend",
            "restorable_ha": "Restorable ha",
        }
    )
    st.subheader("Environmental Justice Scoreboard — all neighborhoods")
    styled_justice = justice_table.style.map(
        lambda v: justice_band_cell(v) if isinstance(v, (int, float)) else "",
        subset=["Justice Score"],
    )
    styled_justice = styled_justice.map(justice_band_name_cell, subset=["Justice Band"])
    styled_justice = styled_justice.map(justice_bool_cell, subset=["Nature Data"])
    styled_justice = styled_justice.format(
        {
            "Risk Score": "{:.0f}",
            "Nature Recovery": "{:.0f}",
            "Transit (20%)": "{:.0f}",
            "Clean Air (10%)": "{:.0f}",
            "Justice Score": "{:.0f}",
            "Restorable ha": "{:.1f}",
        },
        na_rep="no data",
    )
    st.dataframe(styled_justice, width="stretch", hide_index=True)
    st.caption(
        "Nature Data: green = biodiversity monitored. Justice Score for those stations uses the full "
        "formula; for the others the remaining three components are re-weighted to 100%."
    )
    csv_justice = justice_table.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download environmental justice report (CSV)",
        csv_justice,
        "environmental_justice_report.csv",
        "text/csv",
    )

with TAB8:
    st.subheader("🕰️ Then & Now — Debrecen's industrial past vs. today")
    st.markdown(
        """
        A before/after reading of neighborhoods that carried **industry in the 1990s** and are
        today's fastest-cleaning zones. Base-map imagery: **Cívis GIStory** (scanned historical
        maps of Debrecen, 1999 and 2020). Pollution values are **measured May–June 2026**; the
        historic maps are for *visual* comparison — they contain no pollution record.
        """
    )

    n_legacy = int(hist_frame["legacy_industrial"].sum())
    n_watch = int(hist_frame["gentrification_watch"].sum())
    kpi_row(
        [
            ("🏭", "Legacy industrial sites", f"{n_legacy} / {len(hist_frame)}", "#F97316"),
            ("🔴", "Gentrification watch", f"{n_watch} sites", "#EF4444"),
            ("🗺️", "Base-map eras", "1999 + 2020", "#3B82F6"),
        ]
    )

    if hist_available:
        st.markdown(
            "**Before & after — toggle the `1999 base map` / `2020 base map` overlays in the "
            "layer control (● top-right) to slide between eras; red-ring markers are the "
            "*gentrification watch* sites.**"
        )
        st_folium(hist_viz.create_folium_map(), width="stretch", height=600)
        st.caption(
            "Imagery © faithful reproduction of the Cívis GIStory scanned base maps "
            "(Őrváros Közalapítvány / Erda Kft., TOP-7.1.1-16-H-ESZA-2021-02411). Georeferenced "
            "from the EOV projection; shown for illustrative comparison only."
        )

        ba_path = Path(OUTPUT_DIR) / "visualizations" / "historical_beforeafter.png"
        if ba_path.exists():
            st.subheader("Side-by-side — 1999 (left) · 2020 (right)")
            st.image(str(ba_path), width="stretch")
    else:
        st.warning(
            "Historical base-map imagery is not available in this session (offline). "
            "Showing the gentrification-watch analysis without the map overlays."
        )

    st.subheader("Gentrification-watch neighborhoods")
    watch_cols = [
        "station", "location", "legacy_category", "legacy_industrial",
        "env_improvement_index", "risk_score", "risk_category", "gentrification_watch",
    ]
    watch_table = hist_frame[watch_cols].rename(
        columns={
            "station": "Station",
            "location": "Location",
            "legacy_category": "Legacy (1990s) land use",
            "legacy_industrial": "Legacy industrial",
            "env_improvement_index": "Measured improvement",
            "risk_score": "Risk Score",
            "risk_category": "Risk Category",
            "gentrification_watch": "Watch",
        }
    )
    styled_watch = watch_table.style.map(
        lambda v: (
            "background-color:#FEF2F2;color:#B91C1C;font-weight:700;"
            if v == 1 else "text-align:right;"
        ),
        subset=["Watch"],
    )
    st.dataframe(styled_watch.format({"Measured improvement": "{:.3f}", "Risk Score": "{:.0f}"}), width="stretch", hide_index=True)
    st.caption(
        "**Watch** = legacy industrial AND (measured improvement above the 16-station median "
        "OR risk in Emerging/Challenge zones). Industrial heritage is a *curated* label from the "
        "1999 map + Debrecen geography — it never enters the Risk or Justice formulas."
    )

    st.subheader("Where the cleaning is fastest")
    st.plotly_chart(
        hist_viz.create_watch_scatter().update_layout(autosize=True),
        width="stretch",
    )
    corr = hist_frame["legacy_industrial"].corr(hist_frame["env_improvement_index"])
    st.markdown(f"_Measured legacy-industry ↔ improvement correlation: r ≈ **{corr:+.2f}**_ (4 industrial sites, n small — illustrative, not a causal claim).")

st.markdown(
    '<div class="footer">🌳 GreenSense Debrecen · Green Gentrification Index · DEIK.AI Challenge 2026 — '
    "Category B (Urban Environmental Monitoring) · Built on Green Sentinel + DKV + iNaturalist + OpenBioMaps + PADAPT open data</div>",
    unsafe_allow_html=True,
)
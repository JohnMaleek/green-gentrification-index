import folium
import folium.plugins
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.config import DEBRECEN_CENTER, MAP_ZOOM, RISK_CATEGORY_COLORS
from src.visualizations.theme import apply_theme


class MapVisualizer:
    """Folium interactive map and Plotly scatter map for station data."""

    def __init__(self, model_results: pd.DataFrame) -> None:
        self._results = model_results

    @staticmethod
    def _label(station: str, location: str) -> str:
        return f"{station} · {location}"

    @staticmethod
    def _window_color(months: float, status: str) -> str:
        if status == "Already met":
            return "#065F46"
        if status == "Not on track":
            return "#6B7280"
        if pd.isna(months):
            return "#6B7280"
        if months <= 1:
            return "#EF4444"
        if months <= 3:
            return "#F97316"
        if months <= 6:
            return "#FBBF24"
        return "#10B981"

    def create_folium_map(self, color_by: str = "risk_category") -> folium.Map:
        m = folium.Map(
            location=list(DEBRECEN_CENTER),
            zoom_start=MAP_ZOOM,
            tiles="OpenStreetMap",
        )
        for _, row in self._results.iterrows():
            risk_score = row.get("risk_score", 0)
            risk_band = row.get("risk_band", "")
            months = row.get("months_to_target", np.nan)
            status = row.get("timeline_status", "")
            if color_by == "months_to_target":
                color = self._window_color(months, status)
                legend_title = "Months to WHO PM2.5 ≤ 5"
            else:
                color = RISK_CATEGORY_COLORS.get(row.get("risk_category", ""), "#888888")
                legend_title = "Risk Categories"
            radius = max(6, min(18, 6 + risk_score / 100 * 12))
            label = self._label(row.get("station", ""), row.get("location", ""))
            timeline_line = ""
            if color_by == "months_to_target":
                if status == "Already met":
                    timeline_line = "Clean-air target: <b>already met</b>"
                elif status == "Not on track":
                    timeline_line = "Clean-air target: <b>not on track</b> (flat/rising)"
                else:
                    timeline_line = (
                        f"Months to WHO-5: <b>{months:.1f}</b> · est. {row.get('target_date', '—')}"
                    )
            popup_html = (
                f"<b>{label}</b><br>"
                f"Risk category: {row.get('risk_category', 'N/A')}<br>"
                f"<b>Risk Score: {risk_score:.0f}/100 ({risk_band or '—'})</b><br>"
                f"Improvement: {row.get('env_improvement_index', 0):.3f}<br>"
                f"Current PM2.5: {row.get('current_PM2.5', 0):.1f} µg/m³<br>"
                f"PM2.5 rate: {row.get('pm25_trend', 0):.4f} µg/m³/day<br>"
                f"Bus stops nearby: {row.get('bus_stops_nearby', 'N/A')}"
                + ("<br>" + timeline_line if timeline_line else "")
            )
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=(
                    f"{label} — {row.get('risk_category', '')} · "
                    f"Risk {risk_score:.0f}/100"
                ),
            ).add_to(m)

        folium.plugins.MeasureControl(
            position="bottomleft", primary_length_unit="kilometers", secondary_length_unit="meters"
        ).add_to(m)

        if color_by == "months_to_target":
            legend_items = (
                "<span style='color:#EF4444;'>&#9679;</span> ≤ 1 month (urgent)<br>"
                "<span style='color:#F97316;'>&#9679;</span> 1–3 months<br>"
                "<span style='color:#FBBF24;'>&#9679;</span> 3–6 months<br>"
                "<span style='color:#10B981;'>&#9679;</span> &gt; 6 months<br>"
                "<span style='color:#065F46;'>&#9679;</span> Already met<br>"
                "<span style='color:#6B7280;'>&#9679;</span> Not on track"
            )
        else:
            legend_items = (
                "<span style='color:#EF4444;'>&#9679;</span> Emerging Green Zones<br>"
                "<span style='color:#10B981;'>&#9679;</span> Established Clean Areas<br>"
                "<span style='color:#FBBF24;'>&#9679;</span> Stable Neighborhoods<br>"
                "<span style='color:#F97316;'>&#9679;</span> Challenge Zones"
            )
        legend_html = f"""
        <div style="position:fixed;top:30px;right:30px;z-index:1000;
            background:white;padding:12px 14px;border:1px solid #E5E7EB;
            border-radius:10px;font-size:13px;line-height:1.8;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);font-family:Inter, 'Segoe UI', sans-serif;">
        <b style="font-size:14px;">{legend_title}</b><br>
        {legend_items}
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        return m

    def create_plotly_scatter(self) -> go.Figure:
        df = self._results.copy()
        df["label"] = df.apply(lambda r: self._label(r["station"], r["location"]), axis=1)
        fig = px.scatter(
            df,
            x="bus_stops_nearby",
            y="env_improvement_index",
            size="pm25_volatility",
            color="risk_category",
            color_discrete_map=RISK_CATEGORY_COLORS,
            hover_name="label",
            hover_data={
                "label": False,
                "location": False,
                "env_improvement_index": ":.3f",
                "current_PM2.5": ":.1f",
                "pm25_volatility": ":.3f",
                "bus_stops_nearby": True,
            },
            labels={
                "bus_stops_nearby": "Transit Accessibility (Bus Stops ≤1km)",
                "env_improvement_index": "Environmental Improvement Index",
                "risk_category": "Risk Category",
                "pm25_volatility": "Volatility",
            },
            title="Transit Access vs. Environmental Improvement",
        )
        fig.update_layout(legend_title_text="Risk Category")
        return apply_theme(fig)
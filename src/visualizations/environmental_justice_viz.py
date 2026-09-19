"""Environmental justice visualizations (scorecard, timelines, heatmap, map)."""

import numpy as np
import pandas as pd
import folium
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats

from src.config import DEBRECEN_CENTER, MAP_ZOOM, JUSTICE_BAND_COLORS
from src.visualizations.theme import apply_theme

COMPONENT_COLORS = {
    "Risk": "#DC2626",
    "Nature": "#10B981",
    "Transit": "#3B82F6",
    "Clean Air": "#F59E0B",
}

JUSTICE_RAMP = ["#EF4444", "#F59E0B", "#34D399", "#059669"]


def _justice_color(score: float) -> str:
    if score >= 80:
        return JUSTICE_BAND_COLORS["Excellent"]
    if score >= 60:
        return JUSTICE_BAND_COLORS["Good"]
    if score >= 40:
        return JUSTICE_BAND_COLORS["Moderate"]
    return JUSTICE_BAND_COLORS["Needs Attention"]


class EnvironmentalJusticeVisualizer:
    """Build every chart used by the Environmental Justice dashboard tab."""

    def __init__(
        self,
        justice: pd.DataFrame,
        obs: pd.DataFrame,
        daily: pd.DataFrame,
        label_map: dict[str, str],
    ) -> None:
        self._justice = justice
        self._obs = obs
        self._daily = daily
        self._label_map = label_map

    # ------------------------------------------------------------------ scorecard
    def scorecard_grid(self) -> go.Figure:
        """16 neighborhood cards: big score, 4 component gauges, trend arrow."""
        df = self._justice.sort_values("station").copy()
        n = len(df)
        rows = int(np.ceil(n / 4))
        fig = make_subplots(
            rows=rows,
            cols=4,
            vertical_spacing=0.06,
            horizontal_spacing=0.02,
        )

        for idx, (_, row) in enumerate(df.iterrows()):
            r = idx // 4 + 1
            c = idx % 4 + 1
            comp_vals = [
                ("Risk", row["risk_score"]),
                ("Nature", row["biodiversity_recovery_index"] if row["biodiversity_available"] else np.nan),
                ("Transit", row["transit_component"]),
                ("Clean Air", row["pollution_component"]),
            ]
            comp_vals = [(name, v) if v == v else (name, np.nan) for name, v in comp_vals]

            xs = [v for _, v in comp_vals]
            ys = [name for name, _ in comp_vals]
            colors = [COMPONENT_COLORS[name] for name in ys]
            fig.add_trace(
                go.Bar(
                    x=[0] * len(ys),
                    y=ys,
                    orientation="h",
                    marker=dict(color=colors, opacity=0),
                    showlegend=False,
                    xaxis=f"x{r}{c}",
                    yaxis=f"y{r}{c}",
                ),
                row=r,
                col=c,
            )
            fig.add_trace(
                go.Bar(
                    x=xs,
                    y=ys,
                    orientation="h",
                    marker=dict(color=colors, opacity=0.85),
                    showlegend=False,
                    xaxis=f"x{r}{c}",
                    yaxis=f"y{r}{c}",
                ),
                row=r,
                col=c,
            )

            score = row["environmental_justice_score"]
            band = row["justice_band"]
            color = _justice_color(score)
            arrow = "&#9650;" if row["justice_trend"] == "Improving" else (
                "&#9660;" if row["justice_trend"] == "Declining" else "&#9654;"
            )
            title = (
                f"<b>{row['station']}</b> &nbsp;{arrow}<br>"
                f"<span style='color:{color};font-size:17px'>"
                f"<b>{score:.0f}</b>/{100} &middot; {band}</span>"
            )
            fig.update_xaxes(
                title=None, range=[0, 100], showticklabels=False, showgrid=False,
                row=r, col=c,
            )
            fig.update_yaxes(
                title=None, showticklabels=False, showgrid=False,
                row=r, col=c,
            )
            fig.add_annotation(
                x=0.5, y=1.32, xref=f"x{r}{c} domain", yref=f"y{r}{c} domain",
                text=title, showarrow=False,
                font=dict(size=10, family="Inter, sans-serif", color="#111827"),
                align="center",
            )
            fig.add_shape(
                type="rect",
                xref=f"x{r}{c} domain", yref=f"y{r}{c} domain",
                x0=0, x1=1, y0=0, y1=1.03,
                line=dict(color="#E5E7EB", width=1),
                fillcolor="white",
                layer="below",
                row=r, col=c,
            )

        fig.update_layout(
            height=rows * 190,
            margin=dict(l=10, r=10, t=30, b=10),
            title=dict(
                text="Environmental Justice Scorecard — all 16 neighborhoods",
                font=dict(size=15, color="#111827"),
            ),
            hovermode="closest",
        )
        return fig

    def scorecard_detail(self, station: str) -> go.Figure:
        """Focused detail panel for one neighborhood."""
        row = self._justice[self._justice["station"] == station].iloc[0]
        score = row["environmental_justice_score"]
        color = _justice_color(score)

        vals = {
            "Risk": row["risk_score"],
            "Nature": row["biodiversity_recovery_index"] if row["biodiversity_available"] else np.nan,
            "Transit": row["transit_component"],
            "Clean Air": row["pollution_component"],
        }

        fig = go.Figure()
        names = list(vals.keys())
        xs = [float(v) if v == v else 0.0 for v in vals.values()]
        colors = [COMPONENT_COLORS[n] for n in names]
        missing = [not (v == v) for v in vals.values()]

        fig.add_trace(
            go.Bar(
                x=xs,
                y=names,
                orientation="h",
                marker=dict(color=colors),
                text=[f"{v:.0f}" if not m else "no data" for v, m in zip(xs, missing)],
                textposition="outside",
                cliponaxis=False,
                customdata=[m for m in missing],
            )
        )
        fig.add_annotation(
            x=0, y=1.28, xref="x domain", yref="y domain",
            text=(
                f"<b>Environmental Justice Score</b><br>"
                f"<span style='color:{color};font-size:34px'><b>{score:.0f}</b></span>"
                f"&nbsp;<span style='font-size:15px'>/ 100 · {row['justice_band']}</span>"
            ),
            showarrow=False, align="left",
            font=dict(size=11, color="#111827"),
        )
        fig.update_xaxes(range=[0, 125], gridcolor="#E8EAED")
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
        fig.update_layout(
            height=330,
            margin=dict(l=10, r=60, t=20, b=20),
            xaxis_title="Component score (0-100)",
            hovermode="closest",
        )
        return apply_theme(fig, show_grid=False)

    # ----------------------------------------------------------- temporal analysis
    def temporal_analysis(self) -> go.Figure:
        """Daily biodiversity observations overlaid on the city air-quality trend."""
        obs = self._obs.copy()
        obs["date"] = pd.to_datetime(obs["date"])
        daily_obs = obs.groupby("date")["count"].sum().reset_index()
        daily_obs = daily_obs.rename(columns={"count": "observations"})

        pm = self._daily[self._daily["measurement_type"] == "PM2.5"].copy()
        pm["date"] = pd.to_datetime(pm["timestamp"]).dt.date
        pm_daily = pm.groupby("date")["value"].mean().reset_index()
        pm_daily["date"] = pd.to_datetime(pm_daily["date"])

        merged = daily_obs.merge(pm_daily, on="date", how="inner").dropna()

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=merged["date"],
                y=merged["observations"],
                name="Biodiversity observations",
                marker=dict(color="#10B981", opacity=0.65),
                hovertemplate="%{x|%b %d}: %{y} observations<extra></extra>",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=pm_daily["date"],
                y=pm_daily["value"],
                name="Mean PM2.5 (city)",
                mode="lines+markers",
                line=dict(color="#DC2626", width=2.5),
                hovertemplate="%{x|%b %d}: %{y:.2f} µg/m³<extra></extra>",
            ),
            secondary_y=True,
        )
        fig.update_layout(
            title="Over 30 days: air quality fell as observation effort continued",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_yaxes(title_text="Observations per day", secondary_y=False)
        fig.update_yaxes(title_text="Daily mean PM2.5 (µg/m³)", secondary_y=True)
        return apply_theme(fig, height=420)

    def biodiversity_correlation(self) -> go.Figure:
        """Cross-section: is today's biodiversity richer where air is cleaner?"""
        df = self._justice[self._justice["biodiversity_available"]].copy()
        df["label"] = df.apply(lambda r: self._label_map.get(r["station"], r["station"]), axis=1)
        clean = df.dropna(subset=["current_PM2.5", "biodiversity_recovery_index"])
        r, p = stats.pearsonr(clean["current_PM2.5"], clean["biodiversity_recovery_index"])

        fig = px.scatter(
            clean,
            x="current_PM2.5",
            y="biodiversity_recovery_index",
            color="biodiversity_recovery_index",
            color_continuous_scale=JUSTICE_RAMP,
            size="environmental_justice_score",
            hover_name="label",
            hover_data={
                "label": False,
                "current_PM2.5": ":.2f",
                "biodiversity_recovery_index": ":.1f",
                "environmental_justice_score": ":.1f",
                "biodiversity_available": False,
            },
            labels={
                "current_PM2.5": "Current PM2.5 (µg/m³)",
                "biodiversity_recovery_index": "Biodiversity Recovery Index",
                "environmental_justice_score": "Justice Score",
            },
            title=f"Nature recovery vs. air quality (r = {r:.2f}{'*' if p < 0.05 else ''})",
        )
        fig.update_layout(showlegend=False, coloraxis_showscale=True)
        return apply_theme(fig, height=480)

    # ---------------------------------------------------------------- heatmap
    def comparative_heatmap(self) -> go.Figure:
        """16 neighborhoods x 5 dimensions, normalized intensity."""
        df = self._justice.copy()
        df["Clean Air"] = df["pollution_component"]
        df["Nature"] = df["biodiversity_recovery_index"].fillna(-1)
        df["Transit"] = df["transit_component"]
        df["Risk"] = df["risk_score"]
        metrics = ["environmental_justice_score", "Clean Air", "Nature", "Transit", "Risk"]
        labels_short = {
            "environmental_justice_score": "Justice",
            "Clean Air": "Clean Air",
            "Nature": "Nature",
            "Transit": "Transit",
            "Risk": "Risk",
        }
        df = df.sort_values("environmental_justice_score", ascending=False)
        z = df[metrics].values.astype(float)
        z = np.clip(z, 0, 100)

        hover = np.array([
            [
                f"{labels_short[metrics[j]]}: {z[i, j]:.0f}"
                + (" · <b>no bio data</b>" if metrics[j] == "Nature" and df.iloc[i]["environmental_justice_score"] >= 0
                   and not df.iloc[i]["biodiversity_available"] else "")
                for j in range(len(metrics))
            ]
            for i in range(len(df))
        ])

        fig = go.Figure(
            go.Heatmap(
                z=z,
                x=[labels_short[m] for m in metrics],
                y=[self._label_map.get(s, s) for s in df["station"]],
                colorscale=[
                    [0, "#DC2626"], [0.25, "#F59E0B"], [0.5, "#A3E635"],
                    [0.75, "#34D399"], [1, "#059669"],
                ],
                zmin=0,
                zmax=100,
                text=z.round(0).astype(int),
                texttemplate="%{text}",
                hovertemplate="%{y}<br>%{x}: %{z:.0f}<extra></extra>",
                colorbar=dict(title="Score 0-100"),
            )
        )
        fig.update_layout(
            title="Comparative environmental justice profile (left → right: overall equity → each driver)",
            xaxis=dict(side="top"),
            yaxis=dict(automargin=True, tickfont=dict(size=12)),
            height=560,
        )
        return apply_theme(fig, show_grid=False)

    # ------------------------------------------------------- quadrant matrix
    def quadrant_matrix(self) -> go.Figure:
        """Environmental justice 4-quadrant: gentrification risk vs nature recovery."""
        df = self._justice[self._justice["biodiversity_available"]].copy()
        df["label"] = df.apply(lambda r: self._label_map.get(r["station"], r["station"]), axis=1)

        x = df["risk_score"]
        y = df["biodiversity_recovery_index"]
        x_med = x.median()
        y_med = y.median()
        pad_x = (x.max() - x.min()) * 0.08 or 2
        pad_y = (y.max() - y.min()) * 0.08 or 2

        fig = go.Figure()
        quadrants = [
            (x_med, x.max() + pad_x, y_med, y.max() + pad_y, "#DC2626", 0.04),
            (x.min() - pad_x, x_med, y_med, y.max() + pad_y, "#10B981", 0.04),
            (x.min() - pad_x, x_med, y.min() - pad_y, y_med, "#F97316", 0.04),
            (x_med, x.max() + pad_x, y.min() - pad_y, y_med, "#EF4444", 0.04),
        ]
        for x0, x1, y0, y1, color, opacity in quadrants:
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color,
                          opacity=opacity, line_width=0, layer="below")
        fig.add_hline(y=y_med, line_dash="dash", line_color="gray", opacity=0.4)
        fig.add_vline(x=x_med, line_dash="dash", line_color="gray", opacity=0.4)

        quad_labels = [
            (x_med + (x.max() - x_med) * 0.5, y_med + (y.max() - y_med) * 0.6,
             "Gentrifying + recovering\n→ WATCH for displacement", "#B91C1C"),
            (x.min() + (x_med - x.min()) * 0.35, y_med + (y.max() - y_med) * 0.6,
             "Nature recovering + low risk\n→ PROTECT these areas", "#047857"),
            (x.min() + (x_med - x.min()) * 0.35, y.min() + (y_med - y.min()) * 0.42,
             "Challenge zones\n→ remediate first", "#C2410C"),
            (x_med + (x.max() - x_med) * 0.5, y.min() + (y_med - y.min()) * 0.42,
             "Threats: gentrifying + losing nature\n→ urgent policy", "#7F1D1D"),
        ]
        for qx, qy, qtext, qcolor in quad_labels:
            fig.add_annotation(x=qx, y=qy, text=qtext, showarrow=False,
                               align="center", font=dict(color=qcolor, size=11.5))

        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers+text",
            marker=dict(
                size=df["environmental_justice_score"],
                sizemode="area", sizeref=2.0 * (df["environmental_justice_score"].max() / 50),
                color=[_justice_color(v) for v in df["environmental_justice_score"]],
                line=dict(width=1, color="white"),
            ),
            text=df["station"], textposition="top center", textfont=dict(size=9, color="#374151"),
            hovertemplate=(
                "<b>%{customdata}</b><br>Risk: %{x:.0f}/100<br>"
                "Nature recovery: %{y:.0f}/100<br>Justice: %{marker.size:.0f}<extra></extra>"
            ),
            customdata=df["label"],
        ))
        fig.update_xaxes(title="Gentrification Risk Score (→ higher pressure)")
        fig.update_yaxes(title="Biodiversity Recovery Index (0-100)")
        fig.update_layout(
            title="Environmental justice matrix — where to act first",
            height=620,
            margin=dict(l=60, r=40, t=60, b=50),
        )
        return apply_theme(fig, show_grid=False)

    # ------------------------------------------------------- restoration map
    def restoration_map(self) -> folium.Map:
        """Only neighborhoods with real restoration upside; size = potential."""
        df = self._justice[self._justice["restorable_ha"].notna() & (self._justice["restorable_ha"] > 0)].copy()
        if df.empty:
            return folium.Map(location=list(DEBRECEN_CENTER), zoom_start=MAP_ZOOM)

        m = folium.Map(location=list(DEBRECEN_CENTER), zoom_start=MAP_ZOOM, tiles="OpenStreetMap")
        max_ha = df["restorable_ha"].max()
        for _, row in df.iterrows():
            radius = 8 + 16 * row["restorable_ha"] / max_ha
            quality = row.get("habitat_quality", np.nan)
            q_color = (
                "#10B981" if quality >= 4 else "#F59E0B" if quality >= 3 else "#EF4444"
            )
            label = self._label_map.get(row["station"], row["station"])
            popup_html = (
                f"<b>{label}</b><br>"
                f"Restorable habitat: <b>{row['restorable_ha']:.1f} ha</b><br>"
                f"Patches flagged for restoration: {int(row.get('restorable_patches', 0))}<br>"
                f"Of which very-high potential: {row['very_high_ha']:.1f} ha<br>"
                f"Industrial wasteland patches: {int(row.get('wasteland_patches', 0))}<br>"
                f"Current habitat quality: {'good+ high' if quality >= 4 else 'moderate' if quality >= 3 else 'poor — needs help'}"
            )
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=radius,
                color=q_color,
                fill=True,
                fillColor=q_color,
                fillOpacity=0.6,
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"{label} — {row['restorable_ha']:.1f} ha restorable",
            ).add_to(m)

        legend = """
        <div style="position:fixed;top:30px;right:30px;z-index:1000;background:white;
            padding:12px 14px;border:1px solid #E5E7EB;border-radius:10px;font-size:13px;
            line-height:1.9;box-shadow:0 2px 8px rgba(0,0,0,0.08);font-family:Inter, sans-serif;">
            <b>Restoration opportunity</b><br>
            <span style="color:#10B981;">&#9679;</span> current habitat good / recovering<br>
            <span style="color:#F59E0B;">&#9679;</span> moderate habitat quality<br>
            <span style="color:#EF4444;">&#9679;</span> poor — needs remediation first<br>
            <i>Marker size = hectares restorable</i>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend))
        return m
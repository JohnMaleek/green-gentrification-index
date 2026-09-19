import plotly.graph_objects as go
import pandas as pd

from src.config import RISK_CATEGORY_COLORS
from src.visualizations.theme import apply_theme


class RiskMatrixVisualizer:
    """Gentrification risk quadrant scatter: improvement vs. current pollution."""

    def __init__(self, model_results: pd.DataFrame) -> None:
        self._results = model_results

    def plot_risk_quadrant(self) -> go.Figure:
        pol_col = next((c for c in self._results.columns if c.startswith("current_PM2.5")), None)
        if pol_col is None:
            raise ValueError("current_PM2.5 column not found in model results")

        x = self._results["env_improvement_index"]
        y = self._results[pol_col]
        x_med = x.median()
        y_med = y.median()
        x_lo, x_hi = float(x.min()), float(x.max())
        y_lo, y_hi = float(y.min()), float(y.max())
        pad_x = (x_hi - x_lo) * 0.08
        pad_y = max((y_hi - y_lo) * 0.08, 0.2)

        fig = go.Figure()

        # Shaded quadrants behind the points
        fig.add_shape(type="rect", x0=x_med, x1=x_hi + pad_x, y0=y_med, y1=y_hi + pad_y, fillcolor="#EF4444", opacity=0.05, line_width=0, layer="below")
        fig.add_shape(type="rect", x0=x_lo - pad_x, x1=x_med, y0=y_med, y1=y_hi + pad_y, fillcolor="#F97316", opacity=0.05, line_width=0, layer="below")
        fig.add_shape(type="rect", x0=x_lo - pad_x, x1=x_med, y0=y_lo - pad_y, y1=y_med, fillcolor="#FBBF24", opacity=0.05, line_width=0, layer="below")
        fig.add_shape(type="rect", x0=x_med, x1=x_hi + pad_x, y0=y_lo - pad_y, y1=y_med, fillcolor="#10B981", opacity=0.05, line_width=0, layer="below")

        fig.add_hline(y=y_med, line_dash="dash", line_color="gray", opacity=0.4)
        fig.add_vline(x=x_med, line_dash="dash", line_color="gray", opacity=0.4)

        for risk_cat, color in RISK_CATEGORY_COLORS.items():
            subset = self._results[self._results["risk_category"] == risk_cat]
            if len(subset) == 0:
                continue
            subset = subset.copy()
            subset["label"] = subset.apply(lambda r: f"{r['station']} · {r['location']}", axis=1)
            fig.add_trace(go.Scatter(
                x=subset["env_improvement_index"],
                y=subset[pol_col],
                mode="markers+text",
                marker=dict(size=12, color=color, line=dict(width=1, color="white")),
                text=subset["station"],
                textposition="top center",
                textfont=dict(size=10),
                name=risk_cat,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Improvement: %{x:.3f}<br>"
                    f"{pol_col}: %{{y:.1f}} µg/m³<extra>" + risk_cat + "</extra>"
                ),
                customdata=subset[["label"]],
            ))

        quadrant_labels = [
            (x_med + (x_hi - x_med) * 0.62, y_med + (y_hi - y_med) * 0.55, "Gentrification Risk", "#EF4444"),
            (x_lo + (x_med - x_lo) * 0.30, y_med + (y_hi - y_med) * 0.55, "Challenge Zones", "#F97316"),
            (x_lo + (x_med - x_lo) * 0.30, y_lo + (y_med - y_lo) * 0.40, "Stable", "#B45309"),
            (x_med + (x_hi - x_med) * 0.62, y_lo + (y_med - y_lo) * 0.40, "Established Clean", "#047857"),
        ]
        for qx, qy, qtext, qcolor in quadrant_labels:
            fig.add_annotation(
                x=qx, y=qy, text=qtext, showarrow=False,
                font=dict(color=qcolor, size=13, family="Inter, sans-serif"),
                opacity=0.75, xref="x", yref="y",
            )

        fig.update_layout(
            title="Gentrification Risk Matrix: Improvement vs. Pollution",
            xaxis_title="Environmental Improvement Trend (← degrading | improving →)",
            yaxis_title=f"Current {pol_col} Level (← clean | polluted →)",
            xaxis=dict(zeroline=False, range=[x_lo - pad_x, x_hi + pad_x]),
            yaxis=dict(zeroline=False, range=[y_lo - pad_y, y_hi + pad_y]),
            legend_title_text="Risk Category",
        )
        return apply_theme(fig, height=600)
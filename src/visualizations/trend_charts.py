import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.visualizations.theme import apply_theme


class TrendVisualizer:
    """Plotly time-series, bar, and distribution charts for pollution data."""

    def __init__(
        self,
        daily_data: pd.DataFrame,
        improvement_metrics: pd.DataFrame | None = None,
        label_map: dict[str, str] | None = None,
    ) -> None:
        self._daily = daily_data
        self._improvement = improvement_metrics
        self._label_map = label_map or {}

    def _label(self, station: str) -> str:
        return self._label_map.get(station, station)

    def plot_pollution_timeseries(self, selected_stations: list[str], pollutant: str = "PM2.5") -> go.Figure:
        data = self._daily[
            (self._daily["station"].isin(selected_stations))
            & (self._daily["measurement_type"] == pollutant)
        ].copy()
        if len(data) == 0:
            return px.line(title=f"Selected {pollutant} — 30-Day Trend")

        data["station_label"] = data["station"].map(self._label)
        fig = px.line(
            data,
            x="timestamp",
            y="value",
            color="station_label",
            title=f"{pollutant} Levels — 30-Day Trend",
            labels={"value": f"{pollutant} (µg/m³)", "timestamp": "Date", "station_label": "Station"},
        )
        fig.update_layout(legend_title_text="Station")
        return apply_theme(fig)

    def plot_trend_slopes(self, metrics: pd.DataFrame | None = None) -> go.Figure:
        data = (metrics or self._improvement).copy().sort_values("env_improvement_index", ascending=True)
        data["station_label"] = data["station"].map(self._label)

        fig = px.bar(
            data,
            x="env_improvement_index",
            y="station_label",
            orientation="h",
            color="env_improvement_index",
            color_continuous_scale=["#F97316", "#FBBF24", "#10B981"],
            title="Environmental Improvement Index by Station",
            labels={
                "env_improvement_index": "Improvement Index (↑ improving)",
                "station_label": "",
            },
        )
        fig.update_layout(coloraxis_showscale=False, yaxis=dict(dtick=1))
        return apply_theme(fig)

    def plot_pollutant_distribution(self, pollutants: list[str] | None = None) -> go.Figure:
        cols = pollutants or ["PM2.5", "PM10", "NO2", "O3"]
        available = [c for c in cols if c in self._daily["measurement_type"].unique()]
        data = self._daily[self._daily["measurement_type"].isin(available)].copy()
        fig = px.box(
            data,
            x="measurement_type",
            y="value",
            color="measurement_type",
            title="Pollutant Distribution (30-Day Daily Means)",
            labels={"value": "Concentration", "measurement_type": "Pollutant"},
        )
        fig.update_layout(showlegend=False)
        return apply_theme(fig)
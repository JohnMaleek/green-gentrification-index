"""Visualizations for the "Then & Now" historical maps feature.

Interactive folium map overlays the cached 1999 / 2020 Cívis GIStory base-map
mosaics on today's OpenStreetMap, with the gentrification-watch stations
highlighted. Also produces a static side-by-side image and a Plotly
improvement-x-risk scatter.
"""

import logging
from pathlib import Path

import folium
import folium.plugins
from folium.raster_layers import ImageOverlay
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

from src.config import DEBRECEN_CENTER, LEGACY_CATEGORY_COLORS, MAP_ZOOM, OUTPUT_DIR

logger = logging.getLogger(__name__)

WATCH_COLOR = "#EF4444"
LEGACY_COLOR = "#F97316"


class HistoricalVisualizer:
    """Build before/after and watch-signal visuals from the historical model."""

    def __init__(
        self,
        hist_frame: pd.DataFrame,
        georef: dict,
        mosaics: dict,
    ) -> None:
        self._frame = hist_frame
        self._georef = georef
        self._mosaics = mosaics

    @property
    def wgs84_bounds(self) -> list[list[float]] | None:
        b = self._georef.get("wgs84_bounds")
        if not b:
            return None
        return [[b[0], b[1]], [b[2], b[3]]]

    def _image_overlay(self, year: str, opacity: float = 0.8):
        bounds = self.wgs84_bounds
        path = self._mosaics.get(year)
        if not path or not bounds:
            return None
        try:
            return folium.raster_layers.ImageOverlay(
                image=str(path),
                bounds=bounds,
                opacity=opacity,
                name=f"{year} base map · Cívis GIStory",
                alt=f"{year} Debrecen base map (Cívis GIStory)",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Historical overlay %s failed: %s", year, exc)
            return None

    def create_folium_map(self) -> folium.Map:
        m = folium.Map(location=list(DEBRECEN_CENTER), zoom_start=MAP_ZOOM, tiles="OpenStreetMap")
        for year in ("1999", "2020"):
            overlay = self._image_overlay(year)
            if overlay is not None:
                overlay.add_to(m)

        for _, row in self._frame.iterrows():
            watch = bool(row.get("gentrification_watch", 0))
            legacy = bool(row.get("legacy_industrial", 0))
            color = WATCH_COLOR if watch else (LEGACY_COLOR if legacy else "#6B7280")
            radius = 11 if watch else 8
            label = f"{row.get('station', '')} · {row.get('location', '')}"
            legend_mark = "🔴 watch" if watch else ("🟠 legacy industrial" if legacy else "⚪")
            popup_html = (
                f"<b>{label}</b><br>"
                f"1990s land use: <b>{row.get('legacy_category', '?')}</b>"
                f" (industrial: {'yes' if legacy else 'no'})<br>"
                f"Gentrification watch: <b>{'YES' if watch else 'no'}</b><br>"
                f"Measured 2026 improvement: {row.get('env_improvement_index', 0):.3f}<br>"
                f"Current PM2.5: {row.get('current_PM2.5', 0):.1f} µg/m³ · "
                f"Risk {row.get('risk_score', 0):.0f}/100 "
                f"({row.get('risk_band', '—')}, {row.get('risk_category', '?')})"
            )
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=radius,
                color=WATCH_COLOR if watch else "#1F2937",
                weight=3 if watch else 1,
                fill=True,
                fillColor=color,
                fillOpacity=0.75,
                popup=folium.Popup(popup_html, max_width=360),
                tooltip=f"{label} — {legend_mark}",
            ).add_to(m)

        folium.LayerControl(collapsed=True).add_to(m)
        legend_html = """
        <div style="position:fixed;top:30px;right:30px;z-index:1000;
            background:white;padding:12px 14px;border:1px solid #E5E7EB;
            border-radius:10px;font-size:13px;line-height:1.8;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);font-family:Inter,'Segoe UI',sans-serif;">
        <b>Gentrification watch</b><br>
        <span style='color:#EF4444;'>&#9679;</span> Watch (legacy industrial + fast clean-up)<br>
        <span style='color:#F97316;'>&#9679;</span> Legacy industrial site<br>
        <span style='color:#6B7280;'>&#9679;</span> Other · <span style='color:#9CA3AF;'>&#9678;</span> 1999/2020 basemaps
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        return m

    def create_beforeafter_comparison(
        self, out_path: Path | str | None = None, height: int = 900
    ) -> Path:
        """Stitch the 1999 and 2020 mosaics side by side into one PNG."""
        a = self._mosaics.get("1999")
        b = self._mosaics.get("2020")
        if not a or not b:
            raise FileNotFoundError("Before/after needs both 1999 and 2020 mosaics.")
        imgs = []
        for p in (a, b):
            im = Image.open(p).convert("RGB")
            ratio = height / im.height
            imgs.append(im.resize((int(im.width * ratio), height), Image.LANCZOS))
        canvas = Image.new("RGB", (imgs[0].width + 16 + imgs[1].width, height), "white")
        canvas.paste(imgs[0], (0, 0))
        canvas.paste(imgs[1], (imgs[0].width + 16, 0))
        path = Path(out_path) if out_path else OUTPUT_DIR / "visualizations" / "historical_beforeafter.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(path)
        logger.info("Before/after comparison saved to %s", path)
        return path

    def create_watch_scatter(self) -> go.Figure:
        f = self._frame
        fig = px.scatter(
            f,
            x="env_improvement_index",
            y="risk_score",
            color="legacy_category",
            color_discrete_map=LEGACY_CATEGORY_COLORS,
            symbol="gentrification_watch",
            symbol_map={1: "diamond", 0: "circle"},
            hover_data={
                "station": True,
                "location": True,
                "legacy_category": True,
                "legacy_industrial": True,
                "gentrification_watch": True,
                "env_improvement_index": ":.3f",
                "current_PM2.5": ":.1f",
            },
            labels={
                "env_improvement_index": "Measured 2026 improvement index (−rate of clean-up)",
                "risk_score": "Risk score / 100",
                "legacy_category": "Legacy (1990s) land use",
                "gentrification_watch": "Watch",
            },
            title="Legacy industry, clean-up speed and pressure",
        )
        fig.update_traces(marker=dict(size=13))
        fig.update_layout(
            height=520,
            template="plotly_white",
            legend_title_text="Legacy land use",
        )
        return fig
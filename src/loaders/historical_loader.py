"""Historical base-map loader for the "Then & Now" feature.

Downloads scanned historic Debrecen base maps served by the Cívis GIStory
web map (project of the Őrváros Közalapítvány, funded by the municipality,
built by Erda Kft.) and caches the rasters locally.

The historic layers are rendered by a MapServer WMS that only paints the
scanned maps at relatively zoomed-in extent (>= ~1:27k), so the full city is
tiled into a small grid and stitched into a single georeferenced mosaic per
year. Everything is cached under ``data/historical``; the dashboard reads only
the cached PNGs + ``georef.json``, so a live demo never touches the remote
service.

Sources / attribution (displayed in-app and in the submission pack):
- Cívis GIStory — https://civisgistory.hu/  (Őrváros Közalapítvány, Debrecen)
- TOP-7.1.1-16-H-ESZA-2021-02411 "Cívis GIStory" project.
"""

import json
import logging
import urllib.request
import http.cookiejar
import re
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from src.config import (
    HISTORICAL_BBOX_EPSG23700,
    HISTORICAL_DIR,
    HISTORICAL_LAYERS_URL,
    HISTORICAL_MAINDIR,
    HISTORICAL_RASTER_HEIGHT,
    HISTORICAL_RASTER_WIDTH,
    HISTORICAL_SESSION_URL,
    HISTORICAL_WMS_URL,
    HISTORICAL_YEARS,
)
from src.loaders.base_loader import BaseLoader

logger = logging.getLogger(__name__)

EOV_TO_WGS84_TRANSFORMER = None


def eov_to_wgs84(x_eov: float, y_eov: float) -> tuple[float, float]:
    """EOV (EPSG:23700) -> WGS84 (lat, lon)."""
    global EOV_TO_WGS84_TRANSFORMER
    if EOV_TO_WGS84_TRANSFORMER is None:
        from pyproj import Transformer

        EOV_TO_WGS84_TRANSFORMER = Transformer.from_crs(23700, 4326, always_xy=True)
    lon, lat = EOV_TO_WGS84_TRANSFORMER.transform(x_eov, y_eov)
    return float(lat), float(lon)


# Reference bounds derived once with pyproj (checked against the web app).
_WGS84_BOUNDS_FALLBACK = [47.502465734877624, 21.55288004274823, 47.57269525211139, 21.709949887890726]


class HistoricalMapLoader(BaseLoader):
    """Fetch, cache and georeference historic Debrecen base maps."""

    def __init__(self, base_dir: Path | None = None, force: bool = False) -> None:
        super().__init__("historical")
        self._dir = base_dir or HISTORICAL_DIR
        self._force = force
        self._opener: urllib.request.OpenerDirector | None = None
        self._layer_map: dict[str, tuple[str, str]] = {}
        self._mosaics: dict[str, str] = {}
        self._available = False
        self._metadata = {
            "source": "Cívis GIStory (https://civisgistory.hu/)",
            "attribution": "Őrváros Közalapítvány · TOP-7.1.1-16-H-ESZA-2021-02411 · Erda Kft.",
            "note": "Historic base-map imagery for visual comparison; not a pollution record.",
        }

    # ------------------------------------------------------------------ session
    def _establish_session(self) -> bool:
        try:
            jar = http.cookiejar.CookieJar()
            op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            op.addheaders = [("User-Agent", "Mozilla/5.0")]
            op.open(HISTORICAL_SESSION_URL, timeout=30)
            self._opener = op
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Historical map: session failed (%s)", exc)
            return False

    def _discover_layers(self) -> bool:
        """Map each historic year -> (OLID, MVLAYERS) from the layer catalog."""
        if self._opener is None:
            return False
        try:
            raw = self._opener.open(
                f"{HISTORICAL_LAYERS_URL}?MainDir={HISTORICAL_MAINDIR}"
            ).read()
            txt = raw.decode("iso-8859-2")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Historical map: layer discovery failed (%s)", exc)
            return False

        def js_strs(name: str) -> dict[int, str]:
            out: dict[int, str] = {}
            pat = re.compile(
                rf"{re.escape(name)}\[(\d+)\]='([^']*)'"
            )
            for m in pat.finditer(txt):
                out[int(m.group(1))] = m.group(2)
            return out

        layer_id = js_strs("LayerId")
        layer_olid = js_strs("LayerOlid")
        for idx, lid in layer_id.items():
            for year in HISTORICAL_YEARS:
                if lid == f"gistory_terkep_{year}":
                    olid = layer_olid.get(idx, "alap")
                    self._layer_map[year] = (olid, lid)
                    logger.info("Historical map %s -> OLID=%s MVLAYERS=%s", year, olid, lid)
        return bool(self._layer_map)

    # ------------------------------------------------------------------ fetch
    def _wms_getmap(self, olid: str, mv: str, bbox: tuple[float, float, float, float],
                    width: int, height: int) -> bytes | None:
        if self._opener is None:
            return None
        url = (
            f"{HISTORICAL_WMS_URL}?MAINDIR={HISTORICAL_MAINDIR}"
            f"&QMODE=default&OLID={olid}&MVLAYERS={mv}"
            f"&WMSID=1001&WMSIDX=1001"
            f"&SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&SRS=EPSG:23700"
            f"&BBOX={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
            f"&WIDTH={width}&HEIGHT={height}&FORMAT=image/png&TRANSPARENT=TRUE"
        )
        for attempt in range(3):
            try:
                data = self._opener.open(url, timeout=45).read()
                if len(data) > 500:
                    return data
            except Exception as exc:  # noqa: BLE001
                logger.warning("Historical map getmap %s attempt %d: %s", mv, attempt + 1, exc)
        return None

    def _build_mosaic(self, year: str) -> bool:
        olid, mv = self._layer_map.get(year, ("alap", ""))
        if not mv:
            return False

        minx, miny, maxx, maxy = HISTORICAL_BBOX_EPSG23700
        cols, rows = 4, 3
        cell_w = (maxx - minx) / cols
        cell_h = (maxy - miny) / rows
        px_w = HISTORICAL_RASTER_WIDTH // cols
        px_h = HISTORICAL_RASTER_HEIGHT // rows

        cache = self._dir / "cache" / year
        cache.mkdir(parents=True, exist_ok=True)
        panels: list[list[Image.Image | None]] = []
        got_any = False
        for rr in range(rows):
            row_imgs: list[Image.Image | None] = []
            for cc in range(cols):
                path = cache / f"{rr}_{cc}.png"
                img: Image.Image | None = None
                if path.exists() and not self._force:
                    try:
                        img = Image.open(path).convert("RGBA")
                    except Exception:  # noqa: BLE001
                        img = None
                if img is None:
                    if self._opener is not None:
                        bbox = (
                            minx + cc * cell_w, miny + rr * cell_h,
                            minx + (cc + 1) * cell_w, miny + (rr + 1) * cell_h,
                        )
                        data = self._wms_getmap(olid, mv, bbox, px_w + 40, px_h + 40)
                        if data is not None:
                            img = Image.open(io_bytes(data)).convert("RGBA")
                            try:
                                img.save(path)
                            except Exception:  # noqa: BLE001
                                pass
                if img is not None:
                    got_any = True
                    img = img.crop((0, 0, px_w, px_h))
                row_imgs.append(img)
            panels.append(row_imgs)

        if not got_any:
            logger.warning("Historical map %s: no mosaic tiles fetched", year)
            return False

        mosaic = Image.new(
            "RGBA", (px_w * cols, px_h * rows), (0, 0, 0, 0)
        )
        for rr in range(rows):
            for cc in range(cols):
                img = panels[rr][cc]
                if img is None:
                    continue
                mosaic.paste(img, (cc * px_w, rr * px_h))
        out = self._dir / f"mosaic_{year}.png"
        mosaic.save(out)
        self._mosaics[year] = str(out)
        logger.info("Historical mosaics %s -> %s (%s px)", year, out, mosaic.size)
        return True

    def _write_georef(self) -> dict:
        minx, miny, maxx, maxy = HISTORICAL_BBOX_EPSG23700
        try:
            sw_lat, sw_lon = eov_to_wgs84(minx, miny)
            ne_lat, ne_lon = eov_to_wgs84(maxx, maxy)
        except Exception:  # noqa: BLE001  (pyproj optional at runtime)
            sw_lat, sw_lon, ne_lat, ne_lon = _WGS84_BOUNDS_FALLBACK
        ref = {
            "projection": "EPSG:23700 (EOV, HD72)",
            "bbox_eov_epsg23700": [minx, miny, maxx, maxy],
            "wgs84_bounds": [sw_lat, sw_lon, ne_lat, ne_lon],
            "years": {y: self._mosaics.get(y) for y in HISTORICAL_YEARS},
            "attribution": (
                "Cívis GIStory — https://civisgistory.hu/ · Őrváros Közalapítvány · "
                "TOP-7.1.1-16-H-ESZA-2021-02411 · Erda Kft."
            ),
        }
        (self._dir / "georef.json").write_text(
            json.dumps(ref, indent=2), encoding="utf-8"
        )
        return ref

    # ------------------------------------------------------------------ run
    def load(self) -> "HistoricalMapLoader":
        self._dir.mkdir(parents=True, exist_ok=True)
        return self

    def clean(self) -> "HistoricalMapLoader":
        return self

    def standardize_format(self) -> "HistoricalMapLoader":
        return self

    def run(self) -> "HistoricalMapLoader":
        self._available = False
        for year in HISTORICAL_YEARS:
            mosaic = self._dir / f"mosaic_{year}.png"
            if mosaic.exists() and not self._force:
                self._mosaics[year] = str(mosaic)
                self._available = True
                continue
            if not self._establish_session():
                logger.warning("Historical map %s: session unavailable", year)
                continue
            if not (self._layer_map or self._discover_layers()):
                logger.warning("Historical map %s: layer catalog unavailable", year)
                continue
            if self._build_mosaic(year):
                self._available = True
            else:
                logger.warning("Historical map %s unavailable; tab degrades", year)

        if self._mosaics:
            ref = self._write_georef()
            self._data = pd.DataFrame(
                [
                    {"year": y, "mosaic": p, "available": True}
                    for y, p in self._mosaics.items()
                ]
            )
            self._metadata["mosaics"] = self._mosaics
            self._metadata["georef"] = ref
        else:
            self._data = pd.DataFrame(
                [{"year": y, "mosaic": "", "available": False} for y in HISTORICAL_YEARS]
            )
        return self

    def georef(self) -> dict:
        path = self._dir / "georef.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    @property
    def mosaics(self) -> dict[str, str]:
        return dict(self._mosaics)

    def is_available(self) -> bool:
        return self._available


def io_bytes(data: bytes):
    """Wrap raw bytes in a BytesIO (kept as its own import-light helper)."""
    import io

    return io.BytesIO(data)
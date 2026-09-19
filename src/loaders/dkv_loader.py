import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import DKV_DIR
from src.loaders.base_loader import BaseLoader

logger = logging.getLogger(__name__)

_MONITORING_MONTH = "2026-05"


def _resolve_dkv_root(data_dir: str | Path) -> Path:
    root = Path(data_dir)
    candidates = [root, root / "DKV databases"]
    for candidate in candidates:
        if (candidate / "List of bus stops.xlsx").exists():
            return candidate
    return root


class DKVLoader(BaseLoader):
    """Load DKV transport data and compute per-station transit accessibility.

    Uses the bus-stop catalogue (coordinates of every stop), the service
    schedule, and the monthly summary stop statistics for the month
    overlapping the monitoring period (May 2026).
    """

    def __init__(self, data_dir: str | Path | None = None, month: str = _MONITORING_MONTH) -> None:
        super().__init__("dkv")
        self._data_dir = _resolve_dkv_root(Path(data_dir) if data_dir else DKV_DIR)
        self._month = month
        self._bus_stops: pd.DataFrame | None = None
        self._stop_stats: pd.DataFrame | None = None

    def load(self) -> "DKVLoader":
        stops_path = self._data_dir / "List of bus stops.xlsx"
        if stops_path.exists():
            self._bus_stops = pd.read_excel(stops_path, engine="openpyxl")
            logger.info("Loaded %d bus stops", len(self._bus_stops))
        else:
            self._bus_stops = pd.DataFrame()
            logger.warning("Bus stops file not found at %s", stops_path)

        year, month = self._month.split("-")
        stats_path = self._data_dir / "Summary stop statistics" / year / f"{month}.xlsx"
        if stats_path.exists():
            self._stop_stats = self._read_stop_stats(stats_path)
            logger.info("Loaded stop statistics: %d rows", len(self._stop_stats))
        else:
            self._stop_stats = pd.DataFrame()
            logger.warning("Stop statistics not found at %s", stats_path)
        return self

    @staticmethod
    def _read_stop_stats(path: Path) -> pd.DataFrame:
        """Read the summary stop statistics sheet.

        The file has 8 metadata rows followed by data, with a fixed 15-column
        layout: Stop id/name, planned stopping (APC/ALL), IN (total/avg),
        OUT (total/avg), frequency (total/avg), occupancy by arrival and
        departure (total/avg), and delay.
        """
        headers = [
            "Stop_id", "Stop_name",
            "Planned_stopping_APC", "Planned_stopping_ALL",
            "IN_total", "IN_avg", "OUT_total", "OUT_avg",
            "Frequency_total", "Frequency_avg",
            "Occupancy_Arrival_total", "Occupancy_Arrival_avg",
            "Occupancy_Departure_total", "Occupancy_Departure_avg",
            "Delay",
        ]
        df = pd.read_excel(path, header=None, skiprows=8, engine="openpyxl")
        df.columns = headers[: len(df.columns)]
        return df

    def clean(self) -> "DKVLoader":
        if self._bus_stops is not None and len(self._bus_stops) > 0:
            coords = self._bus_stops["Coordinates"].str.split(",", expand=True)
            self._bus_stops["lon"] = pd.to_numeric(coords[0], errors="coerce")
            self._bus_stops["lat"] = pd.to_numeric(coords[1], errors="coerce")
            self._bus_stops.dropna(subset=["lon", "lat"], inplace=True)
        if self._stop_stats is not None and len(self._stop_stats) > 0:
            for col in self._stop_stats.columns:
                if col not in ("Stop_id", "Stop_name"):
                    self._stop_stats[col] = pd.to_numeric(self._stop_stats[col], errors="coerce")
            self._stop_stats.dropna(subset=["Stop_id"], inplace=True)
        return self

    def standardize_format(self) -> "DKVLoader":
        self._data = self._bus_stops if self._bus_stops is not None else pd.DataFrame()
        self._metadata["bus_stop_count"] = int(len(self._data))
        self._metadata["has_stop_stats"] = bool(self._stop_stats is not None and len(self._stop_stats) > 0)
        return self

    def compute_transit_accessibility(
        self, station_coords: pd.DataFrame, radius_km: float = 1.0
    ) -> pd.DataFrame:
        """Compute transit accessibility for each monitoring station.

        Args:
            station_coords: DataFrame with columns ``station``, ``latitude``, ``longitude``.
            radius_km: Search radius in kilometres.

        Returns:
            DataFrame indexed by station with ``bus_stops_nearby`` and
            ``nearest_bus_stop_km`` columns.
        """
        if self._bus_stops is None or len(self._bus_stops) == 0:
            out = station_coords[["station"]].copy()
            out["bus_stops_nearby"] = 0
            out["nearest_bus_stop_km"] = np.nan
            return out

        stops = self._bus_stops.dropna(subset=["lat", "lon"]).copy()
        rows = []
        for _, r in station_coords.iterrows():
            slat, slon = r["latitude"], r["longitude"]
            dlat = stops["lat"] - slat
            dlon = (stops["lon"] - slon) * np.cos(np.radians(slat))
            dist_km = np.sqrt((dlat * 111.32) ** 2 + (dlon * 111.32) ** 2)
            rows.append({
                "station": r["station"],
                "bus_stops_nearby": int((dist_km <= radius_km).sum()),
                "nearest_bus_stop_km": round(float(dist_km.min()), 3),
            })
        return pd.DataFrame(rows)

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r_km = 6371.0
        p1, p2 = np.radians([lat1, lon1]), np.radians([lat2, lon2])
        dphi, dlmb = p2[0] - p1[0], p2[1] - p1[1]
        a = np.sin(dphi / 2) ** 2 + np.cos(p1[0]) * np.cos(p2[0]) * np.sin(dlmb / 2) ** 2
        return r_km * 2 * np.arcsin(np.sqrt(a))

    def get_bus_stops(self) -> pd.DataFrame:
        return self._bus_stops if self._bus_stops is not None else pd.DataFrame()

    def get_stop_stats(self) -> pd.DataFrame:
        return self._stop_stats if self._stop_stats is not None else pd.DataFrame()
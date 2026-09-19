import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import AIR_POLLUTANTS, GREEN_SENTINEL_DIR, GROUNDWATER_COLUMNS, NOISE_COLUMNS, OUTLIER_SIGMA
from src.loaders.base_loader import BaseLoader

logger = logging.getLogger(__name__)

COORD_REGEX = re.compile(r"\(([-\d.]+),\s*([-\d.]+)\)")

CATEGORY_TO_STANDARD = {
    "Levego": AIR_POLLUTANTS,
    "Felszin_alatti_viz": GROUNDWATER_COLUMNS,
    "Zaj": NOISE_COLUMNS,
}

ALL_STANDARD_COLUMNS = AIR_POLLUTANTS + GROUNDWATER_COLUMNS + NOISE_COLUMNS

UNIT_COLUMNS = ["timestamp", "latitude", "longitude", "location", "station", "measurement_type", "value", "unit"]

MEASUREMENT_NAME_MAP = {
    "LAEQ nappali": "LAEQ_day",
    "LAEQ éjszakai": "LAEQ_night",
}


class GreenSentinelLoader(BaseLoader):
    """Load, clean, and standardise all Green Sentinel monitoring stations.

    Raw files are long-format Excel sheets per station with columns:
        timestamp, Location, ``Mérőeszköz`` (measurement type),
        ``érték`` (value), ``mértékegység`` (unit).

    ``standardize_format`` produces one row per measurement in a standard
    8-column schema. ``to_wide`` pivots to one row per (timestamp, station).
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        super().__init__("green_sentinel")
        self._data_dir = Path(data_dir) if data_dir else GREEN_SENTINEL_DIR
        self._quality_report: dict = {}

    def load(self) -> "GreenSentinelLoader":
        frames: list[pd.DataFrame] = []
        for station_dir in sorted(self._data_dir.iterdir()):
            if not station_dir.is_dir():
                continue
            station_code = station_dir.name
            for excel_file in sorted(station_dir.glob("*.xlsx")):
                category = excel_file.stem.rsplit("_", 1)[-1]
                df = pd.read_excel(excel_file, engine="openpyxl")
                df.rename(
                    columns={"érték": "value_raw", "Mérőeszköz": "measurement_type"},
                    inplace=True,
                )
                df["station"] = station_code
                df["category"] = category
                frames.append(df)
                logger.debug("Loaded %s: %d rows", excel_file.name, len(df))
        if not frames:
            raise FileNotFoundError(f"No station folders found under {self._data_dir}")
        self._raw = pd.concat(frames, ignore_index=True)
        self._quality_report["total_raw_rows"] = int(len(self._raw))
        self._quality_report["raw_files"] = int(len(frames))
        logger.info("Loaded %d raw rows across %d files", len(self._raw), len(frames))
        return self

    def clean(self) -> "GreenSentinelLoader":
        df = self._raw.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d-%H-%M")
        df["value_raw"] = pd.to_numeric(df["value_raw"], errors="coerce")

        negative_mask = df["value_raw"] < 0
        self._quality_report["negative_anomalies"] = int(negative_mask.sum())
        pct = round(negative_mask.sum() / max(len(df), 1) * 100, 2)
        self._quality_report["negative_anomaly_pct"] = pct
        logger.info("Flagged %d negative anomalies (%.2f%%)", int(negative_mask.sum()), pct)
        df.loc[negative_mask, "value_raw"] = np.nan

        df["value_raw"] = df.groupby(["station", "measurement_type"])["value_raw"].transform(
            lambda s: s.ffill().bfill()
        )

        null_count = int(df["value_raw"].isna().sum())
        self._quality_report["remaining_nulls"] = null_count
        self._quality_report["remaining_null_pct"] = round(null_count / max(len(df), 1) * 100, 2)

        self._raw = df
        return self

    def standardize_format(self) -> "GreenSentinelLoader":
        df = self._raw.copy()

        coords = df["Location"].str.extract(COORD_REGEX)
        df["latitude"] = coords[0].astype(float)
        df["longitude"] = coords[1].astype(float)
        df["location"] = df["Location"].str.replace(COORD_REGEX, "", regex=True).str.rstrip(" ,")

        df["measurement_type"] = df["measurement_type"].replace(MEASUREMENT_NAME_MAP)
        df["unit"] = df["mértékegység"]
        df["value"] = pd.to_numeric(df["value_raw"], errors="coerce")

        self._data = df[UNIT_COLUMNS].copy()

        self._quality_report["stations"] = int(self._data["station"].nunique())
        self._quality_report["date_range"] = (
            self._data["timestamp"].min().isoformat(),
            self._data["timestamp"].max().isoformat(),
        )
        self._quality_report["categories"] = self._raw["category"].value_counts().to_dict()
        self._quality_report["measurement_types"] = sorted(self._data["measurement_type"].unique().tolist())

        outlier_flags = pd.Series(False, index=self._data.index)
        for mtype, group in self._data.groupby("measurement_type"):
            std = group["value"].std()
            mean = group["value"].mean()
            if pd.notna(std) and std > 0:
                outlier_flags |= ((group["value"] - mean).abs() > OUTLIER_SIGMA * std)
        self._quality_report["outliers_flagged"] = int(outlier_flags.sum())

        self._metadata["quality_report"] = self._quality_report
        return self

    def to_wide(self, measurement_types: list[str] | None = None) -> pd.DataFrame:
        """Pivot long data to one row per (timestamp, station)."""
        metrics = measurement_types or ALL_STANDARD_COLUMNS
        metrics = [m for m in metrics if m in self._data["measurement_type"].unique()]
        pivoted = self._data[self._data["measurement_type"].isin(metrics)].pivot_table(
            index=["timestamp", "station", "latitude", "longitude", "location"],
            columns="measurement_type",
            values="value",
            aggfunc="first",
        ).reset_index()
        pivoted.columns.name = None
        return pivoted

    def get_quality_report(self) -> dict:
        return self._quality_report
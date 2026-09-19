import logging

import numpy as np
import pandas as pd
from scipy import stats

from src.config import (
    GROUNDWATER_COLUMNS,
    NOISE_COLUMNS,
    POLLUTANT_COLUMNS,
    RANDOM_STATE,
)

logger = logging.getLogger(__name__)


def _linregress_slope(series: pd.Series) -> float:
    y = series.dropna().values
    if len(y) < 5:
        return np.nan
    x = np.arange(len(y))
    slope, _, _, _, _ = stats.linregress(x[: len(y)], y)
    return slope


class FeatureEngineer:
    """Create analysis features for gentrification risk modelling.

    Operates on the long-format standardised data and produces:
    - daily aggregates per station and measurement type
    - 30-day trend slopes for key pollutants
    - composite environmental improvement index
    - current pollution levels (last 7 days)
    - air quality volatility (std of daily PM2.5)
    - transit accessibility (from DKV data if available)

    The feature matrix has 16 rows (one per station) ready for clustering.
    """

    def __init__(self, long_data: pd.DataFrame, transit_data: pd.DataFrame | None = None) -> None:
        self._raw = long_data
        self._transit = transit_data
        self._daily: pd.DataFrame | None = None
        self._features: pd.DataFrame | None = None
        self._improvement_metrics: pd.DataFrame | None = None

    def create_daily_aggregates(self) -> pd.DataFrame:
        self._daily = (
            self._raw.groupby(["station", pd.Grouper(key="timestamp", freq="D"), "measurement_type"])["value"]
            .mean()
            .reset_index()
        )
        logger.info("Daily aggregates: %d rows", len(self._daily))
        return self._daily

    def _trends_for_measurements(self, stations: pd.DataFrame, measurement: str) -> pd.DataFrame:
        sub = stations[stations["measurement_type"] == measurement]
        slopes = []
        for station, grp in sub.groupby("station"):
            grp_sorted = grp.sort_values("timestamp")
            slopes.append({"station": station, f"{measurement}_trend": _linregress_slope(grp_sorted["value"])})
        return pd.DataFrame(slopes)

    def calculate_pollution_trends(self) -> pd.DataFrame:
        if self._daily is None:
            self.create_daily_aggregates()
        trend_dfs = []
        for mtype in POLLUTANT_COLUMNS:
            if mtype in self._daily["measurement_type"].unique():
                trend_dfs.append(self._trends_for_measurements(self._daily, mtype))
        if not trend_dfs:
            raise ValueError("No pollutant columns found in daily aggregates")
        result = trend_dfs[0]
        for df in trend_dfs[1:]:
            result = result.merge(df, on="station", how="outer")
        return result

    def create_environmental_improvement_index(self) -> pd.DataFrame:
        trends = self.calculate_pollution_trends()
        trend_cols = [c for c in trends.columns if c.endswith("_trend")]
        for col in trend_cols:
            trends[col] = trends[col].fillna(0)
        trends["env_improvement_index"] = -1 * trends[trend_cols].mean(axis=1)
        self._improvement_metrics = trends
        return trends

    def calculate_current_pollution_levels(self) -> pd.DataFrame:
        if self._daily is None:
            self.create_daily_aggregates()
        max_ts = self._daily["timestamp"].max()
        window = self._daily[self._daily["timestamp"] >= max_ts - pd.Timedelta(days=7)]

        result_parts = []
        for mtype in POLLUTANT_COLUMNS:
            if mtype in window["measurement_type"].unique():
                sub = window[window["measurement_type"] == mtype]
                agg = sub.groupby("station")["value"].mean().reset_index()
                agg.rename(columns={"value": f"current_{mtype}"}, inplace=True)
                result_parts.append(agg)

        if not result_parts:
            return pd.DataFrame({"station": []})

        result = result_parts[0]
        for df in result_parts[1:]:
            result = result.merge(df, on="station", how="outer")
        return result

    def calculate_air_quality_volatility(self) -> pd.DataFrame:
        if self._daily is None:
            self.create_daily_aggregates()
        pm25 = self._daily[self._daily["measurement_type"] == "PM2.5"]
        vol = pm25.groupby("station")["value"].std().reset_index()
        vol.rename(columns={"value": "pm25_volatility"}, inplace=True)
        return vol

    def create_all_features(self) -> pd.DataFrame:
        self.create_daily_aggregates()

        trends = self.create_environmental_improvement_index()
        current = self.calculate_current_pollution_levels()
        volatility = self.calculate_air_quality_volatility()

        meta = self._raw.groupby("station").agg(
            latitude=("latitude", "first"),
            longitude=("longitude", "first"),
            location=("location", "first"),
        ).reset_index()

        features = meta.merge(trends, on="station", how="left")
        features = features.merge(current, on="station", how="left")
        features = features.merge(volatility, on="station", how="left")

        if self._transit is not None and len(self._transit) > 0:
            features = features.merge(self._transit, on="station", how="left")

        self._features = features
        logger.info("Feature matrix: %d stations, %d features", len(features), len(features.columns) - 4)
        return features

    @property
    def daily_data(self) -> pd.DataFrame:
        if self._daily is None:
            self.create_daily_aggregates()
        return self._daily

    @property
    def improvement_metrics(self) -> pd.DataFrame:
        if self._improvement_metrics is None:
            self.create_environmental_improvement_index()
        return self._improvement_metrics

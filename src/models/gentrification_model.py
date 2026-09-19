import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from src.config import (
    DATA_END,
    DAYS_PER_MONTH,
    DEFAULT_PM25_TARGET,
    N_CLUSTERS,
    OUTPUT_DIR,
    PM25_TARGETS,
    RANDOM_STATE,
)

logger = logging.getLogger(__name__)

RISK_ORDER = ["Emerging Green Zones", "Established Clean Areas", "Stable Neighborhoods", "Challenge Zones"]
RISK_COLORS = {
    "Emerging Green Zones": "#EF4444",
    "Established Clean Areas": "#10B981",
    "Stable Neighborhoods": "#FBBF24",
    "Challenge Zones": "#F97316",
}

RISK_SCORE_WEIGHTS = {
    "improvement": 0.40,
    "pollution": 0.30,
    "transit": 0.20,
    "stability": 0.10,
}

RISK_BAND_EDGES = [
    ("Critical", 81, 100),
    ("High", 61, 80),
    ("Moderate", 31, 60),
    ("Low", 0, 30),
]


class GentrificationRiskModel:
    """K-means clustering model for environmental gentrification risk.

    Uses three core features (env_improvement_index, current_pm25, volatility)
    to cluster 16 stations into 4 risk categories with a simple auto-labelling
    rule based on improvement-pollution quadrants.
    """

    def __init__(self, feature_matrix: pd.DataFrame) -> None:
        self._features = feature_matrix
        self._scaler = StandardScaler()
        self._model = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
        self._cluster_labels: np.ndarray | None = None
        self._label_map: dict[int, str] = {}
        self._results: pd.DataFrame | None = None
        self._score_bounds: dict | None = None
        self._timeline_meta: dict | None = None

    def fit_clustering(self) -> "GentrificationRiskModel":
        feature_cols = self._get_feature_cols()
        X = self._features[feature_cols].fillna(0).values
        X_scaled = self._scaler.fit_transform(X)
        self._cluster_labels = self._model.fit_predict(X_scaled)
        sil = silhouette_score(X_scaled, self._cluster_labels)
        logger.info("K-means clustering: silhouette score = %.3f", sil)

        self._features = self._features.copy()
        self._features["cluster_id"] = self._cluster_labels
        self._label_map = self._auto_label_clusters()
        self._features["risk_category"] = self._features["cluster_id"].map(self._label_map)
        self._results = self._features.copy()
        self.compute_risk_scores()
        self.compute_clean_air_timeline()
        return self

    def _get_feature_cols(self) -> list[str]:
        """Core clustering features per the technical spec.

        Improvement trend, current PM2.5 level, and PM2.5 volatility.
        """
        cols = []
        for candidate in ["env_improvement_index", "current_PM2.5", "pm25_volatility"]:
            if candidate in self._features.columns:
                cols.append(candidate)
        if "current_PM2.5" not in cols:
            fallback = next((c for c in self._features.columns if c.startswith("current_")), None)
            if fallback:
                cols.append(fallback)
        if not cols:
            raise ValueError("No feature columns found in the feature matrix")
        return cols

    def _auto_label_clusters(self) -> dict[int, str]:
        """Assign a distinct risk label to each cluster based on its centroid.

        Clusters are split into the two with the highest environmental
        improvement and the two with the lowest. Within each pair the cluster
        with the higher current pollution takes the risk-relevant label. This
        guarantees one cluster per category even when the whole city is
        improving, which is the case for this monitoring period.
        """
        df = self._features.copy()
        imp_col = "env_improvement_index"
        pol_col = next((c for c in df.columns if c.startswith("current_PM2.5")), None)
        if pol_col is None:
            pol_col = next((c for c in df.columns if c.startswith("current_")), None)

        if pol_col is None:
            imp_median = df[imp_col].median()
            return {
                cid: ("Emerging Green Zones" if grp[imp_col].mean() > imp_median else "Stable Neighborhoods")
                for cid, grp in df.groupby("cluster_id")
            }

        stats = (
            df.groupby("cluster_id")
            .agg(imp=(imp_col, "mean"), pol=(pol_col, "mean"))
            .reset_index()
            .sort_values("imp", ascending=False)
            .reset_index(drop=True)
        )

        if len(stats) < 4:
            logger.warning("Fewer than 4 clusters: %d", len(stats))

        high_imp = stats.iloc[: len(stats) // 2].sort_values("pol", ascending=False)
        low_imp = stats.iloc[len(stats) // 2:].sort_values("pol", ascending=False)

        label_map: dict[int, str] = {}
        labels_high = ["Emerging Green Zones", "Established Clean Areas"]
        labels_low = ["Challenge Zones", "Stable Neighborhoods"]
        for (_, row), label in zip(high_imp.iterrows(), labels_high):
            label_map[int(row["cluster_id"])] = label
        for (_, row), label in zip(low_imp.iterrows(), labels_low):
            label_map[int(row["cluster_id"])] = label
        return label_map

    @staticmethod
    def _min_max_norm(series: pd.Series) -> pd.Series:
        rng = series.max() - series.min()
        if rng == 0:
            return pd.Series(50.0, index=series.index)
        return (series - series.min()) / rng * 100

    def compute_risk_scores(self) -> "GentrificationRiskModel":
        """Compute the 0-100 Gentrification Risk Score per station.

        Weighted composite of four normalized components (each 0-100, derived
        by min-max scaling across the monitored stations so the full 0-100
        range is used):

          Risk = 0.40 x improvement + 0.30 x pollution
               + 0.20 x transit      + 0.10 x stability

        - improvement: faster environmental improvement = more risk
        - pollution:   still polluted = price pressure potential
        - transit:     more bus stops within 1 km = development pressure
        - stability:   lower PM2.5 volatility = more reliable signal
        """
        if self._results is None:
            return self
        df = self._results.copy()

        imp_col = "env_improvement_index"
        pol_col = next((c for c in df.columns if c.startswith("current_PM2.5")), None)
        trn_col = next((c for c in df.columns if c == "bus_stops_nearby"), None)
        vol_col = next((c for c in df.columns if c == "pm25_volatility"), None)

        imp_score = self._min_max_norm(df[imp_col])
        pol_score = (
            self._min_max_norm(df[pol_col]) if pol_col is not None else pd.Series(0.0, index=df.index)
        )
        transit_score = (
            self._min_max_norm(df[trn_col]) if trn_col is not None else pd.Series(0.0, index=df.index)
        )
        stab_score = (
            100 - self._min_max_norm(df[vol_col]) if vol_col is not None else pd.Series(50.0, index=df.index)
        )

        w = RISK_SCORE_WEIGHTS
        risk_score = (
            w["improvement"] * imp_score
            + w["pollution"] * pol_score
            + w["transit"] * transit_score
            + w["stability"] * stab_score
        )

        def band(score: float) -> str:
            if score < 31:
                return "Low"
            if score < 61:
                return "Moderate"
            if score < 81:
                return "High"
            return "Critical"

        df["imp_score"] = imp_score.round(1)
        df["pol_score"] = pol_score.round(1)
        df["transit_score"] = transit_score.round(1)
        df["stab_score"] = stab_score.round(1)
        df["risk_score"] = risk_score.round(1)
        df["risk_band"] = df["risk_score"].apply(band)

        self._results = df
        self._score_bounds = {
            "improvement": {"min": float(df[imp_col].min()), "max": float(df[imp_col].max())},
            "pollution": {"min": float(df[pol_col].min()), "max": float(df[pol_col].max())}
            if pol_col is not None
            else None,
            "transit": {"min": float(df[trn_col].min()), "max": float(df[trn_col].max())}
            if trn_col is not None
            else None,
            "volatility": {"min": float(df[vol_col].min()), "max": float(df[vol_col].max())}
            if vol_col is not None
            else None,
        }
        top = df.sort_values("risk_score", ascending=False).iloc[0]
        logger.info(
            "Risk scores computed. Top: %s (%.0f/100, %s)",
            top["station"], top["risk_score"], top["risk_band"],
        )
        return self

    def compute_clean_air_timeline(
        self, target_pm25: float | str | None = None
    ) -> "GentrificationRiskModel":
        """Estimate months until each station reaches the chosen PM2.5 target.

        Simple linear extrapolation using that station's PM2.5 30-day trend
        (slope in µg/m³ per day) against its current (last-7-day) level:

            months = (current - target) / (|slope| x 30.437)

        Status per station:
          - Already met:  current <= target
          - On track:     current > target and slope < 0
          - Not on track: slope >= 0 (pollution flat or rising)
        """
        if self._results is None:
            return self
        if target_pm25 is None:
            target_pm25 = PM25_TARGETS[DEFAULT_PM25_TARGET]
        elif isinstance(target_pm25, str):
            target_pm25 = PM25_TARGETS[target_pm25]
        target_pm25 = float(target_pm25)
        df = self._results.copy()

        cur_col = next((c for c in df.columns if c == "current_PM2.5"), None)
        trend_col = next((c for c in df.columns if c == "PM2.5_trend"), None)

        months = pd.Series(np.nan, index=df.index)
        status = pd.Series("Already met", index=df.index)

        if cur_col is not None and trend_col is not None:
            cur = df[cur_col]
            rate = df[trend_col].fillna(0.0)
            above = cur - target_pm25
            on_track = (above > 0) & (rate < 0)
            months = months.mask(on_track, above[on_track] / (-rate[on_track]) / DAYS_PER_MONTH)
            status = status.where(~(above > 0), "On track")
            status = status.mask(rate >= 0, "Not on track")

        df["pm25_trend"] = df[trend_col].round(4) if trend_col is not None else np.nan
        df["months_to_target"] = months.round(1)
        df["timeline_status"] = status

        base = pd.Timestamp(DATA_END)
        days = pd.to_timedelta((df["months_to_target"].fillna(0) * DAYS_PER_MONTH).round(), unit="D")
        df["target_date"] = pd.NaT
        reachable = df["timeline_status"] == "On track"
        df.loc[reachable, "target_date"] = (base + days[reachable]).dt.date

        self._results = df
        self._timeline_meta = {
            "target_pm25": target_pm25,
            "basis_date": str(base.date()),
        }
        logger.info(
            "Clean-air timeline (target %.0f µg/m³): %d already met, %d on track, %d not on track",
            target_pm25,
            int((status == "Already met").sum()),
            int((status == "On track").sum()),
            int((status == "Not on track").sum()),
        )
        return self

    def generate_risk_report(self) -> pd.DataFrame:
        if self._results is None:
            self.fit_clustering()
        cols = ["station", "location", "latitude", "longitude", "cluster_id", "risk_category"]
        extra = [
            c for c in self._results.columns
            if c.startswith(("env_improvement", "current_PM", "pm25_volatility", "bus_stops"))
            or c in (
                "risk_score", "risk_band", "imp_score", "pol_score", "transit_score", "stab_score",
                "pm25_trend", "months_to_target", "target_date", "timeline_status",
            )
            or c.endswith("_trend")
        ]
        return self._results[cols + extra].sort_values("risk_score", ascending=False)

    def save(self, out_dir: Path | None = None) -> None:
        d = out_dir or OUTPUT_DIR / "models"
        d.mkdir(parents=True, exist_ok=True)
        report = self.generate_risk_report()
        report.to_csv(d / "clustering_results.csv", index=False)
        metrics = {
            "n_clusters": N_CLUSTERS,
            "silhouette_score": float(silhouette_score(
                self._scaler.transform(self._features[self._get_feature_cols()].fillna(0)),
                self._cluster_labels,
            )),
            "label_map": self._label_map,
            "risk_score_weights": RISK_SCORE_WEIGHTS,
            "risk_score_bounds": self._score_bounds,
            "clean_air_timeline": self._timeline_meta,
        }
        with open(d / "model_metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        logger.info("Model saved to %s", d)

"""Environmental justice scoring linking air quality, nature, and equity."""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    BIO_INDEX_WEIGHTS,
    CONSERVATION_QUALITY,
    JUSTICE_WEIGHTS,
    OUTPUT_DIR,
    RESTORATION_LEVEL,
)
from src.loaders.biodiversity_loader import BiodiversityLoader

logger = logging.getLogger(__name__)

JUSTICE_BAND_EDGES = [
    ("Excellent", 80, 100),
    ("Good", 60, 79),
    ("Moderate", 40, 59),
    ("Needs Attention", 0, 39),
]

RESTORABLE_LEVELS = {"very_high", "high"}


def _min_max_norm(series: pd.Series) -> pd.Series:
    rng = series.max() - series.min()
    if rng == 0:
        return pd.Series(50.0, index=series.index)
    return (series - series.min()) / rng * 100


class EnvironmentalJusticeModel:
    """Build Biodiversity Recovery and Environmental Justice scores.

    The two indices follow the formulas documented in the competition's
    ``BIODIVERSITY_DATASETS_README.md`` / ``DATA_INTEGRATION_GUIDE.md``.
    """

    def __init__(self, report: pd.DataFrame, biodiversity: BiodiversityLoader) -> None:
        self._report = report
        self._bio = biodiversity
        self._bio_metrics: pd.DataFrame | None = None
        self._justice: pd.DataFrame | None = None

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _area_weighted_richness(df: pd.DataFrame) -> float:
        if df.empty:
            return np.nan
        area = df["habitat_area_hectares"].fillna(0.0)
        if area.sum() <= 0:
            return df["species_richness_index"].mean()
        return float(np.average(df["species_richness_index"], weights=area))

    # ------------------------------------------------------------ bio metrics
    def compute_biodiversity_metrics(self) -> pd.DataFrame:
        inat = self._bio.get_inaturalist()
        birds = self._bio.get_birds()
        habitats = self._bio.get_habitats()

        rows: dict[str, dict] = {}

        if not inat.empty:
            for station, g in inat.groupby("debrecen_station"):
                r = rows.setdefault(station, {})
                r["inat_species"] = int(g["species_name"].nunique())
                r["inat_organisms"] = int(pd.to_numeric(g["count"], errors="coerce").sum())
                r["inat_research"] = int((g.get("quality_grade", "") == "research").sum())

        if not birds.empty:
            for station, g in birds.groupby("debrecen_station"):
                r = rows.setdefault(station, {})
                r["bird_species"] = int(g["species_english"].nunique())
                r["bird_abundance"] = int(pd.to_numeric(g["abundance"], errors="coerce").sum())
                r["bird_rare"] = int((g.get("rarity_status", "common") == "rare").sum())

        if not habitats.empty:
            habitats = habitats.copy()
            habitats["_quality"] = habitats["conservation_status"].map(CONSERVATION_QUALITY)
            habitats["_rest"] = habitats["restoration_potential"].map(RESTORATION_LEVEL)
            for station, g in habitats.groupby("station"):
                r = rows.setdefault(station, {})
                r["habitat_patches"] = int(len(g))
                r["habitat_area_ha"] = float(g["habitat_area_hectares"].sum())
                r["habitat_richness"] = self._area_weighted_richness(g)
                r["habitat_quality"] = float(g["_quality"].mean()) if g["_quality"].notna().any() else np.nan
                r["excellent_habitats"] = int((g["conservation_status"] == "excellent").sum())
                r["restorable_patches"] = int(g["restoration_potential"].isin(RESTORABLE_LEVELS).sum())
                r["restorable_ha"] = float(
                    g.loc[g["restoration_potential"].isin(RESTORABLE_LEVELS), "habitat_area_hectares"].sum()
                )
                r["very_high_ha"] = float(
                    g.loc[g["restoration_potential"] == "very_high", "habitat_area_hectares"].sum()
                )
                r["wasteland_patches"] = int((g["habitat_type"] == "industrial_wasteland").sum())

        bio = pd.DataFrame(rows.values(), index=pd.Index(rows.keys(), name="station"))
        if bio.empty:
            self._bio_metrics = bio
            return bio

        # --- Biodiversity Recovery Index (documented 40/35/25 formula) -------
        monitored = bio.index.tolist()
        bio["biodiversity_available"] = True
        bio["species_score"] = _min_max_norm(bio["inat_species"])
        bio["organism_score"] = _min_max_norm(bio["inat_organisms"])
        bio["bird_score"] = _min_max_norm(bio["bird_abundance"])
        bio["biodiversity_recovery_index"] = (
            BIO_INDEX_WEIGHTS["species"] * bio["species_score"]
            + BIO_INDEX_WEIGHTS["organism"] * bio["organism_score"]
            + BIO_INDEX_WEIGHTS["bird"] * bio["bird_score"]
        ).round(1)

        def bio_band(v: float) -> str:
            if pd.isna(v):
                return "No data"
            if v < 31:
                return "Low / declining"
            if v < 61:
                return "Moderate"
            return "High"

        bio["biodiversity_band"] = bio["biodiversity_recovery_index"].apply(bio_band)
        self._bio_metrics = bio
        logger.info(
            "Biodiversity metrics computed for %d monitored stations; top: %s",
            len(bio),
            bio["biodiversity_recovery_index"].idxmax(),
        )
        return bio

    # ---------------------------------------------------------- justice score
    def compute_environmental_justice_scores(self) -> pd.DataFrame:
        if self._bio_metrics is None:
            self.compute_biodiversity_metrics()

        report = self._report.copy()
        bio = self._bio_metrics.copy()

        just = report.merge(bio, left_on="station", right_index=True, how="left")
        just["biodiversity_available"] = just["biodiversity_available"].fillna(False)
        just["biodiversity_recovery_index"] = just["biodiversity_recovery_index"].where(
            just["biodiversity_available"], np.nan
        )

        # Component scores (each 0-100). Ship component labels straight through.
        just["transit_component"] = just["transit_score"].fillna(0.0)
        just["pollution_component"] = (100 - just["pol_score"].fillna(0.0)).clip(0, 100)
        just["biodiversity_component"] = just["biodiversity_recovery_index"]

        w = JUSTICE_WEIGHTS
        has_bio = just["biodiversity_available"]

        # Full formula when nature data is available.
        full = (
            w["risk"] * just["risk_score"]
            + w["biodiversity"] * just["biodiversity_component"].fillna(0.0)
            + w["transit"] * just["transit_component"]
            + w["pollution"] * just["pollution_component"]
        )
        # Re-weighted formula for the stations we cannot measure nature at.
        denom = w["risk"] + w["transit"] + w["pollution"]
        partial = (
            w["risk"] * just["risk_score"]
            + w["transit"] * just["transit_component"]
            + w["pollution"] * just["pollution_component"]
        ) / denom

        just["environmental_justice_score"] = np.where(has_bio, full, partial).round(1)

        def band(score: float) -> str:
            if score >= 80:
                return "Excellent"
            if score >= 60:
                return "Good"
            if score >= 40:
                return "Moderate"
            return "Needs Attention"

        just["justice_band"] = just["environmental_justice_score"].apply(band)
        just["justice_trend"] = np.where(
            just["pm25_trend"] < 0, "Improving",
            np.where(just["pm25_trend"] > 0, "Declining", "Flat"),
        )
        just = just.sort_values("environmental_justice_score", ascending=False).reset_index(drop=True)
        self._justice = just
        logger.info(
            "Environmental Justice scores: top %s (%.1f/100, %s)",
            just.iloc[0]["station"], just.iloc[0]["environmental_justice_score"],
            just.iloc[0]["justice_band"],
        )
        return just

    # ------------------------------------------------------------------ output
    def save(self, out_dir: Path | None = None) -> Path:
        if self._justice is None:
            self.compute_environmental_justice_scores()
        d = out_dir or OUTPUT_DIR / "models"
        d.mkdir(parents=True, exist_ok=True)
        self._justice.to_csv(d / "environmental_justice_scores.csv", index=False)
        if self._bio_metrics is not None:
            self._bio_metrics.to_csv(d / "biodiversity_metrics.csv")

        metrics = {
            "biodiversity_index_weights": BIO_INDEX_WEIGHTS,
            "justice_score_weights": JUSTICE_WEIGHTS,
            "justice_band_edges": JUSTICE_BAND_EDGES,
            "data_transparency": {
                "observations_total": int(self._bio.get_metadata().get("observations", 0)),
                "unique_species": int(self._bio.get_metadata().get("unique_species", 0)),
                "habitat_patches": int(self._bio.get_metadata().get("habitat_patches", 0)),
                "stations_monitored": self._bio.get_metadata().get("stations_monitored", []),
            },
            "stations_scored": int(self._justice["biodiversity_available"].sum()),
        }
        with open(d / "justice_metrics.json", "w", encoding="utf-8") as fh:
            json.dump(metrics, fh, indent=2, default=str)
        logger.info("Environmental justice model saved to %s", d)
        return d / "justice_metrics.json"

    @property
    def bio_metrics(self) -> pd.DataFrame:
        if self._bio_metrics is None:
            self.compute_biodiversity_metrics()
        return self._bio_metrics

    @property
    def justice_report(self) -> pd.DataFrame:
        if self._justice is None:
            self.compute_environmental_justice_scores()
        return self._justice
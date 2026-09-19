"""Historical "then & now" analysis: legacy land-use x measured recovery.

Links a *curated* 1990s land-use label for each station to the *measured*
2026 environmental data, exposing a gentrification-watch signal: neighbourhoods
that were industrial in the 1990s and have cleaned up fastest are where
displacement pressure concentrates.

Guardrail: ``legacy_industrial`` is a transparently attributed, curated signal.
It is used ONLY for correlation and the watch flag — it never enters the
Risk Score or Environmental Justice Score formulas.
"""

import json
import logging
from pathlib import Path

import pandas as pd

from src.config import HISTORICAL_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

LEGACY_CSV = HISTORICAL_DIR / "legacy_landuse.csv"


class HistoricalGentrificationModel:
    """Compute the legacy-land-use gentrification-watch model."""

    def __init__(self, report: pd.DataFrame, legacy_csv: Path | None = None) -> None:
        self._report = report
        self._legacy_csv = Path(legacy_csv) if legacy_csv else LEGACY_CSV
        self._frame: pd.DataFrame | None = None

    def _load_legacy(self) -> pd.DataFrame:
        df = pd.read_csv(self._legacy_csv)
        df["station"] = df["station"].astype(str).str.strip().str.upper()
        df["legacy_industrial"] = df["legacy_industrial"].astype(int)
        return df

    def compute(self) -> pd.DataFrame:
        legacy = self._load_legacy()
        frame = self._report.merge(legacy, on="station", how="left")
        frame["legacy_industrial"] = frame["legacy_industrial"].fillna(0).astype(int)
        frame["legacy_category"] = frame["legacy_category"].fillna("unknown")

        improvement_median = frame["env_improvement_index"].median()
        high_risk = frame["risk_category"].eq("Emerging Green Zones") | frame["risk_category"].eq("Challenge Zones")
        reached = frame["env_improvement_index"].gt(improvement_median)
        frame["gentrification_watch"] = (
            frame["legacy_industrial"].eq(1) & (reached | high_risk)
        ).astype(int)
        frame["recovery_from_legacy"] = frame["legacy_industrial"] * frame["env_improvement_index"]

        frame = frame.sort_values(
            ["gentrification_watch", "env_improvement_index"],
            ascending=[False, False],
        ).reset_index(drop=True)
        self._frame = frame
        return frame

    def correlation(self) -> dict:
        if self._frame is None:
            self.compute()
        f = self._frame
        out = {}
        num = f[["legacy_industrial", "env_improvement_index", "current_PM2.5", "risk_score", "transit_score"]].apply(pd.to_numeric, errors="coerce")
        valid = f["legacy_industrial"].eq(1) | f["legacy_industrial"].eq(0)
        for col in ["env_improvement_index", "current_PM2.5", "risk_score", "transit_score"]:
            sub = num.loc[valid, ["legacy_industrial", col]].dropna()
            if len(sub) > 2 and sub[col].nunique() > 1:
                r = sub["legacy_industrial"].corr(sub[col])
                out[col] = round(float(r), 3) if r == r else None
            else:
                out[col] = None
        out["n_legacy_industrial"] = int(f["legacy_industrial"].sum())
        out["n_watch"] = int(f["gentrification_watch"].sum())
        out["improvement_median"] = float(improvement_median) if (improvement_median := f["env_improvement_index"].median()) == improvement_median else None
        return out

    def save(self, out_dir: Path | None = None) -> Path:
        if self._frame is None:
            self.compute()
        d = out_dir or OUTPUT_DIR / "models"
        d.mkdir(parents=True, exist_ok=True)
        self._frame.to_csv(OUTPUT_DIR / "processed_data" / "historical_gentrification.csv", index=False)
        metrics = {
            "source_note": "legacy_landuse.csv curated from the 1999 Cívis GIStory base map and Debrecen geography; 2026 values are measured.",
            "signal_definition": "gentrification_watch = legacy_industrial AND (env_improvement_index above the 16-station median OR risk category in {Emerging Green Zones, Challenge Zones}).",
            "correlations_legacy_industrial": self.correlation(),
        }
        path = d / "historical_metrics.json"
        path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
        logger.info("Historical gentrification model saved to %s", path)
        return path

    @property
    def frame(self) -> pd.DataFrame:
        if self._frame is None:
            self.compute()
        return self._frame
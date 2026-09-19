"""Real-data catalogue for the GreenSense front-end site.

Rebuilds every number the Stitch design screens present from the serialised
pipeline outputs (output/processed_data + output/visualizations) so the static
site never fabricates a metric. All values come from the measured
May 21 - Jun 19, 2026 monitoring window.
"""

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.config import OUTPUT_DIR, PROCESSED_DIR

DATA_DIR = OUTPUT_DIR / "processed_data"


class SiteCatalog:
    """Lazy-loaded snapshot of every real value the site needs."""

    def __init__(self, out_dir: Optional[Path] = None) -> None:
        self.out = Path(out_dir or OUTPUT_DIR)
        self.data = self.out / "processed_data"

    # ------------------------------------------------------------------ loads
    def report(self) -> pd.DataFrame:
        return pd.read_csv(self.data / "clustering_results.csv")

    def justice(self) -> pd.DataFrame:
        return pd.read_csv(self.data / "environmental_justice_scores.csv")

    def hist(self) -> pd.DataFrame:
        return pd.read_csv(self.data / "historical_gentrification.csv")

    def quality(self) -> dict:
        raw = json.loads((self.data / "data_quality_report.json").read_text(encoding="utf-8"))
        return raw["green_sentinel"]["quality_report"]

    # ------------------------------------------------------------------ KPIs
    @property
    def stats(self) -> dict:
        q = self.quality()
        rep = self.report()
        jus = self.justice()
        n_monitored = int(jus["biodiversity_available"].sum())
        return {
            "raw_rows": int(q["total_raw_rows"]),
            "raw_files": int(q["raw_files"]),
            "negative_anomalies": int(q["negative_anomalies"]),
            "negative_anomaly_pct": float(q["negative_anomaly_pct"]),
            "outliers_flagged": int(q["outliers_flagged"]),
            "n_stations": int(q["stations"]),
            "n_monitored": n_monitored,
            "n_unmonitored": int(q["stations"]) - n_monitored,
            "measurement_types": len(q["measurement_types"]),
            "start": q["date_range"][0][:10],
            "end": q["date_range"][1][:10],
            "bus_stops": self.bus_stop_count,
            "window": "May 21 - June 19, 2026",
        }

    @property
    def bus_stop_count(self) -> int:
        raw = json.loads((self.data / "data_quality_report.json").read_text(encoding="utf-8"))
        return int(raw["dkv"]["bus_stop_count"])

    @property
    def city_pm(self) -> dict:
        rep = self.report()
        return {
            "pm25_mean": float(rep["current_PM2.5"].mean()),
            "pm10_mean": float(rep["current_PM10"].mean()),
            "pm25_median": float(rep["current_PM2.5"].median()),
            "improvement_median": float(rep["env_improvement_index"].median()),
        }

    @property
    def category_counts(self) -> dict:
        return self.report()["risk_category"].value_counts().to_dict()

    def stations(self) -> list[dict]:
        rep = self.report()
        jus = self.justice().set_index("station")
        hist = self.hist().set_index("station")
        rows: list[dict] = []
        for r in rep.to_dict("records"):
            s = r["station"]
            j = jus.loc[s]
            rows.append(
                {
                    "station": s,
                    "location": r["location"],
                    "lat": float(r["latitude"]),
                    "lon": float(r["longitude"]),
                    "category": r["risk_category"],
                    "risk_score": float(r["risk_score"]),
                    "risk_band": r["risk_band"],
                    "pm25": float(r["current_PM2.5"]),
                    "pm10": float(r["current_PM10"]),
                    "trend": float(r["pm25_trend"]),
                    "improvement": float(r["env_improvement_index"]),
                    "bus_stops": int(r["bus_stops_nearby"]),
                    "months": None if pd.isna(r["months_to_target"]) else float(r["months_to_target"]),
                    "timeline": r["timeline_status"],
                    "target_date": r["target_date"],
                    "justice_score": None if pd.isna(j["environmental_justice_score"]) else float(j["environmental_justice_score"]),
                    "justice_band": j["justice_band"],
                    "monitored": bool(j["biodiversity_available"]),
                    "nature_index": None if pd.isna(j["biodiversity_recovery_index"]) else float(j["biodiversity_recovery_index"]),
                    "watch": int(hist.loc[s]["gentrification_watch"]),
                    "legacy": int(hist.loc[s]["legacy_industrial"]),
                }
            )
        return rows

    def highlights(self) -> dict:
        rep = self.report()
        jus = self.justice()
        h = self.hist()
        top_risk = rep.sort_values("risk_score", ascending=False).iloc[0]
        top_justice = jus.sort_values("environmental_justice_score", ascending=False).iloc[0]
        monitored = jus[jus["biodiversity_available"]]
        top_nature = monitored.sort_values("biodiversity_recovery_index", ascending=False).iloc[0]
        return {
            "top_risk_station": top_risk["station"],
            "top_risk_score": float(top_risk["risk_score"]),
            "top_risk_band": top_risk["risk_band"],
            "top_risk_category": top_risk["risk_category"],
            "top_justice_station": top_justice["station"],
            "top_justice_score": float(top_justice["environmental_justice_score"]),
            "top_justice_band": top_justice["justice_band"],
            "top_nature_station": top_nature["station"],
            "top_nature_index": float(top_nature["biodiversity_recovery_index"]),
            "on_track": int((rep["timeline_status"] == "On track").sum()),
            "already_met": int((rep["timeline_status"] == "Already met").sum()),
            "not_on_track": int((rep["timeline_status"] == "Not on track").sum()),
            "legacy_industrial": int(h["legacy_industrial"].sum()),
            "watch": int(h["gentrification_watch"].sum()),
        }

    def ker11(self) -> Optional[dict]:
        for s in self.stations():
            if s["station"] == "DEB-KER11":
                return s
        return None

    def history(self) -> dict:
        h = self.hist()
        ind = sorted(h[h["legacy_industrial"] == 1]["station"].tolist())
        watch = sorted(h[h["gentrification_watch"] == 1]["station"].tolist())
        r = None
        if len(ind) > 1:
            r = h["legacy_industrial"].corr(h["env_improvement_index"])
        return {
            "industrial_sites": ind,
            "watch_sites": watch,
            "corr": r,
            "years": "1999 & 2020",
        }

    def per_station_quality(self) -> pd.DataFrame:
        long_path = self.data / "green_sentinel_cleaned.parquet"
        long = pd.read_parquet(long_path)
        g = (
            long.groupby("station")
            .agg(
                Records=("value", "count"),
                Missing_Pct=("value", lambda s: round(s.isna().mean() * 100, 2)),
                Measurement_Types=("measurement_type", "nunique"),
            )
            .reset_index()
        )
        g["Coverage"] = (100 - g["Missing_Pct"]).round(0).astype(int)
        return g
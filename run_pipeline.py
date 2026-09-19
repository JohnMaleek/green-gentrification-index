"""Run the full Green Gentrification Index pipeline end-to-end.

Loads all datasets, cleans them, engineers features, fits the clustering
model, generates every visualisation, and saves outputs under output/.
"""

import json
import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px

from src.config import OUTPUT_DIR, PROCESSED_DIR, RISK_BAND_COLORS
from src.frontend.generate_site import build as build_frontend_site
from src.loaders.biodiversity_loader import BiodiversityLoader
from src.loaders.dkv_loader import DKVLoader
from src.loaders.green_sentinel_loader import GreenSentinelLoader
from src.loaders.historical_loader import HistoricalMapLoader
from src.models.environmental_justice import EnvironmentalJusticeModel
from src.models.gentrification_model import GentrificationRiskModel
from src.models.historical_gentrification import HistoricalGentrificationModel
from src.pipeline import DataPipeline
from src.processors.feature_engineer import FeatureEngineer
from src.visualizations import (
    EnvironmentalJusticeVisualizer,
    MapVisualizer,
    RiskMatrixVisualizer,
    TrendVisualizer,
)
from src.visualizations.historical_viz import HistoricalVisualizer
from src.visualizations.theme import apply_theme

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def main() -> None:
    pipeline = DataPipeline()
    pipeline.add_dataset(GreenSentinelLoader()).add_dataset(DKVLoader())
    pipeline.load_all()

    long_data = pipeline.get_dataset("green_sentinel")
    dkv = pipeline.get_dataset("dkv")

    coords = long_data[["station", "latitude", "longitude"]].drop_duplicates()
    dkv_loader = DKVLoader().run()
    transit = dkv_loader.compute_transit_accessibility(coords)

    fe = FeatureEngineer(long_data, transit_data=transit)
    features = fe.create_all_features()
    daily = fe.daily_data
    improvement = fe.improvement_metrics

    model = GentrificationRiskModel(features).fit_clustering()
    report = model.generate_risk_report()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    long_data.to_parquet(PROCESSED_DIR / "green_sentinel_cleaned.parquet", index=False)
    daily.to_csv(PROCESSED_DIR / "daily_aggregates.csv", index=False)
    features.to_csv(PROCESSED_DIR / "improvement_metrics.csv", index=False)
    transit.to_csv(PROCESSED_DIR / "transit_accessibility.csv", index=False)

    out = OUTPUT_DIR / "processed_data"
    out.mkdir(parents=True, exist_ok=True)
    report.to_csv(out / "clustering_results.csv", index=False)
    long_data.to_parquet(out / "green_sentinel_cleaned.parquet", index=False)
    daily.to_csv(out / "daily_aggregates.csv", index=False)
    improvement.to_csv(out / "improvement_metrics.csv", index=False)
    features.to_csv(out / "feature_matrix.csv", index=False)
    transit.to_csv(out / "transit_accessibility.csv", index=False)

    with open(out / "data_quality_report.json", "w", encoding="utf-8") as fh:
        json.dump(pipeline.get_metadata(), fh, indent=2, default=str)

    model.save(OUTPUT_DIR / "models")

    viz_dir = OUTPUT_DIR / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)

    label_map = {r.station: f"{r.station} · {r.location}" for r in report.itertuples()}

    # ------------------------------------------------------------------ biodiversity & environmental justice
    bio = BiodiversityLoader().run()
    ej = EnvironmentalJusticeModel(report, bio)
    justice = ej.justice_report
    ej.save(OUTPUT_DIR / "models")

    ej_viz = EnvironmentalJusticeVisualizer(justice, bio.get_data(), daily, label_map)
    ej_viz.scorecard_grid().write_html(str(viz_dir / "justice_scorecard.html"))
    ej_viz.temporal_analysis().write_html(str(viz_dir / "justice_temporal.html"))
    ej_viz.biodiversity_correlation().write_html(str(viz_dir / "justice_correlation.html"))
    ej_viz.comparative_heatmap().write_html(str(viz_dir / "justice_heatmap.html"))
    ej_viz.quadrant_matrix().write_html(str(viz_dir / "justice_quadrant.html"))
    ej_viz.restoration_map().save(str(viz_dir / "justice_restoration_map.html"))
    justice.to_csv(OUTPUT_DIR / "processed_data" / "environmental_justice_scores.csv", index=False)

    # ------------------------------------------------------------------ historical "then & now"
    hist_loader = HistoricalMapLoader()
    hist_loader.run()
    hist_model = HistoricalGentrificationModel(report)
    hist_frame = hist_model.compute()
    hist_model.save(OUTPUT_DIR / "models")
    hist_frame.to_csv(OUTPUT_DIR / "processed_data" / "historical_gentrification.csv", index=False)

    hist_viz = HistoricalVisualizer(hist_frame, hist_loader.georef(), hist_loader.mosaics)
    if hist_loader.is_available():
        hist_viz.create_folium_map().save(str(viz_dir / "historical_then_now_map.html"))
        hist_viz.create_beforeafter_comparison()
    hist_viz.create_watch_scatter().write_html(str(viz_dir / "historical_watch_scatter.html"))
    watch_list = hist_frame[hist_frame["gentrification_watch"].eq(1)][["station", "location"]]
    logger.info(
        "Historical 'then & now': mosaics available=%s, watch sites=%s",
        hist_loader.is_available(),
        list(watch_list["station"]),
    )

    MapVisualizer(report).create_folium_map().save(str(viz_dir / "debrecen_risk_map.html"))
    map_viz = MapVisualizer(report)
    map_viz.create_plotly_scatter().write_html(str(viz_dir / "transit_improvement_scatter.html"))

    tv = TrendVisualizer(daily, improvement, label_map=label_map)
    tv.plot_pollution_timeseries(report["station"].unique().tolist()[:5], "PM2.5").write_html(
        str(viz_dir / "pm25_timeseries.html")
    )
    tv.plot_trend_slopes().write_html(str(viz_dir / "improvement_slopes.html"))
    tv.plot_pollutant_distribution().write_html(str(viz_dir / "pollutant_distributions.html"))

    RiskMatrixVisualizer(report).plot_risk_quadrant().write_html(str(viz_dir / "risk_matrix.html"))

    board = report.sort_values("risk_score", ascending=False).copy()
    board["Neighborhood"] = board["station"].map(label_map)
    fig_board = px.bar(
        board,
        x="risk_score",
        y="Neighborhood",
        orientation="h",
        color="risk_band",
        color_discrete_map=RISK_BAND_COLORS,
        labels={"risk_score": "Risk Score (0-100)", "Neighborhood": "", "risk_band": "Risk Band"},
        title="Gentrification Risk Scoreboard — Debrecen",
    )
    fig_board.update_layout(legend_title_text="Risk Band", yaxis=dict(dtick=1))
    fig_board.update_traces(texttemplate="%{x:.0f}", textposition="outside")
    apply_theme(fig_board).write_html(str(viz_dir / "risk_scoreboard.html"))

    tl = report.copy()
    tl["Neighborhood"] = tl["station"].map(label_map)
    tl["x_val"] = tl["months_to_target"].fillna(0.0)
    tl["display"] = tl["timeline_status"].map({
        "Already met": "Already met (0)", "Not on track": "Not on track"
    })
    tl["color"] = tl["timeline_status"].map({
        "Already met": "#065F46", "Not on track": "#6B7280"
    })
    for _, row in tl[tl["timeline_status"] == "On track"].iterrows():
        tl.loc[row.name, "display"] = f"{row['months_to_target']:.1f} mo"
        tl.loc[row.name, "color"] = (
            "#EF4444" if row["months_to_target"] <= 1
            else "#F97316" if row["months_to_target"] <= 3
            else "#FBBF24" if row["months_to_target"] <= 6
            else "#10B981"
        )
    tl = tl.sort_values(
        ["timeline_status", "x_val"],
        key=lambda s: s.map({"Already met": 0, "On track": 1, "Not on track": 2}),
        ascending=True,
    )
    fig_tl = px.bar(
        tl,
        x="x_val",
        y="Neighborhood",
        orientation="h",
        color="color",
        color_discrete_map="identity",
        text="display",
        labels={"x_val": "Months to reach WHO 5 µg/m³ guideline", "Neighborhood": "", "color": ""},
        title="Clean Air Timeline — Debrecen (WHO Annual PM2.5 = 5 µg/m³)",
        category_orders={"Neighborhood": tl["Neighborhood"].tolist()},
    )
    fig_tl.update_layout(showlegend=False, yaxis=dict(dtick=1))
    fig_tl.update_traces(textposition="outside", cliponaxis=False)
    apply_theme(fig_tl).write_html(str(viz_dir / "clean_air_timeline.html"))

    log_report = report.copy()
    log_report["label"] = log_report.apply(lambda r: f"{r.station} · {r.location}", axis=1)
    logger.info("Pipeline complete. Outputs written under %s", OUTPUT_DIR)
    logger.info("\n%s", log_report[["label", "risk_category", "env_improvement_index"]].to_string(index=False))

    justice_log = justice[
        ["station", "environmental_justice_score", "justice_band", "biodiversity_recovery_index"]
    ].copy()
    justice_log["label"] = justice_log["station"]
    logger.info(
        "\nEnvironmental Justice summary:\n%s",
        justice_log.sort_values("environmental_justice_score", ascending=False).set_index("label").to_string(),
    )

    build_frontend_site()
    logger.info("Static 'GreenSense Debrecen' site regenerated under output/frontend_site/")


if __name__ == "__main__":
    sys.exit(main())
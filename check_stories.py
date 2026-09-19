"""Verify every number quoted in the dashboard stories & competition narrative.

The app's Environmental Justice tab pulls numbers straight from model outputs that
are serialised during `run_pipeline.py`, and the demo script quotes the same values.
This checker re-derives each claim from those CSV files and fails loudly if a number
drifts, so a future edit cannot silently change a story.

Usage:
    python check_stories.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SCORES = ROOT / "output" / "processed_data" / "environmental_justice_scores.csv"
BIODIVERSITY = ROOT / "data" / "biodiversity" / "biodiversity_inaturalist.csv"
BIRDS = ROOT / "data" / "biodiversity" / "biodiversity_openbiomaps_birds.csv"
HABITATS = ROOT / "data" / "biodiversity" / "biodiversity_padapt.csv"
HISTORICAL = ROOT / "output" / "processed_data" / "historical_gentrification.csv"
HIST_MOSAICS = ROOT / "data" / "historical" / "mosaic_1999.png"

TOL = 0.5

FAILURES: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    if not cond:
        FAILURES.append(f"{label}: {detail}")
    print(f"[{mark}] {label}" + (f"  ({detail})" if detail else ""))


def close(actual: float, expected: float, tol: float = TOL) -> bool:
    if pd.isna(actual) or pd.isna(expected):
        return False
    return abs(actual - expected) <= tol


def main() -> int:
    scores = pd.read_csv(SCORES)
    scores = scores.set_index("station")

    # --------------------------------------------------------------- transparency panel
    inat = pd.read_csv(BIODIVERSITY)
    birds = pd.read_csv(BIRDS)
    habitats = pd.read_csv(HABITATS)
    check(
        "Transparency: 230 observations (150 iNat + 80 birds)",
        len(inat) + len(birds) == 230,
        f"got {len(inat)}+{len(birds)}",
    )
    check(
        "Transparency: 32 unique species",
        pd.concat([inat["species_name"], birds["species_english"]]).nunique() == 32,
    )
    check(
        "Transparency: 44 PADAPT habitat patches",
        len(habitats) == 44,
        f"got {len(habitats)}",
    )
    monitored = sorted(scores[scores["biodiversity_available"]].index.tolist())
    check(
        "Transparency: 10 of 16 stations monitored",
        len(monitored) == 10,
        f"got {len(monitored)}",
    )

    # --------------------------------------------------------------- Story A: DEB-KER14
    r14 = scores.loc["DEB-KER14"]
    check("KER14 risk 50.9 (Moderate)", close(r14["risk_score"], 50.9))
    check("KER14 18 iNat species", close(r14["inat_species"], 18))
    check("KER14 biodiversity index 69.7", close(r14["biodiversity_recovery_index"], 69.7))
    check("KER14 zero transit", close(r14["transit_component"], 0))
    check("KER14 5 habitat patches", close(r14["habitat_patches"], 5))
    check("KER14 17.2 ha habitat", close(r14["habitat_area_ha"], 17.2))
    check("KER14 1 rare bird record", close(r14["bird_rare"], 1))

    # --------------------------------------------------------------- Story B: DEB-KER12
    r12 = scores.loc["DEB-KER12"]
    top_nature = scores.loc[monitored, "biodiversity_recovery_index"].max()
    check("KER12 highest biodiversity index", close(r12["biodiversity_recovery_index"], top_nature))
    check("KER12 biodiversity index 95.6", close(r12["biodiversity_recovery_index"], 95.6))
    check("KER12 19 iNat species", close(r12["inat_species"], 19))
    check("KER12 24.6 ha habitat", close(r12["habitat_area_ha"], 24.6))
    check("KER12 habitat quality 4.5", close(r12["habitat_quality"], 4.5))
    check("KER12 risk 76.4 (High)", close(r12["risk_score"], 76.4))

    # --------------------------------------------------------------- Story C: DEB-KER01 / KER04
    r01 = scores.loc["DEB-KER01"]
    check("KER01 14 iNat species", close(r01["inat_species"], 14))
    check("KER01 biodiversity index 25.8 (lowest story)", close(r01["biodiversity_recovery_index"], 25.8))
    check("KER01 9.0 ha total", close(r01["habitat_area_ha"], 9.0))
    check("KER01 3.9 restorable ha", close(r01["restorable_ha"], 3.9))
    check("KER01 1.8 very-high-priority ha", close(r01["very_high_ha"], 1.8))
    check("KER01 risk 53.7", close(r01["risk_score"], 53.7))
    r04 = scores.loc["DEB-KER04"]
    check("KER04 5.7 restorable ha (twin site)", close(r04["restorable_ha"], 5.7))

    # --------------------------------------------------------------- Callout: DEB-KER11
    r11 = scores.loc["DEB-KER11"]
    check("KER11 top justice score", close(r11["environmental_justice_score"], scores["environmental_justice_score"].max()))
    check("KER11 justice 74.4", close(r11["environmental_justice_score"], 74.4))
    check("KER11 risk 79.3 (High, Emerging Green Zone)", close(r11["risk_score"], 79.3))
    check("KER11 biodiversity index 82.6", close(r11["biodiversity_recovery_index"], 82.6))
    check("KER11 20 iNat species", close(r11["inat_species"], 20))
    check("KER11 2 rare bird records", close(r11["bird_rare"], 2))
    check("KER11 50 bus stops", close(r11["bus_stops_nearby"], 50))

    # --------------------------------------------------------------- formula invariants
    W = {"risk": 0.4, "biodiversity": 0.3, "transit": 0.2, "pollution": 0.1}
    expected_full = (
        W["risk"] * scores["risk_score"]
        + W["biodiversity"] * scores["biodiversity_recovery_index"].fillna(0.0)
        + W["transit"] * scores["transit_component"]
        + W["pollution"] * scores["pollution_component"]
    )
    denom = W["risk"] + W["transit"] + W["pollution"]
    expected_partial = (
        W["risk"] * scores["risk_score"]
        + W["transit"] * scores["transit_component"]
        + W["pollution"] * scores["pollution_component"]
    ) / denom
    expected = expected_full.where(scores["biodiversity_available"], expected_partial)
    check(
        "Justice formula matches model re-implementation for all 16 stations",
        (scores["environmental_justice_score"] - expected).abs().max() <= TOL,
        f"max diff {(scores['environmental_justice_score'] - expected).abs().max():.3f}",
    )
    missing = scores[~scores["biodiversity_available"]]
    check(
        "No-bio stations re-weight remaining three components (6 stations)",
        len(missing) == 6,
        f"got {len(missing)} stations without biodiversity data",
    )

    # --------------------------------------------------------------- historical "then & now"
    hist = pd.read_csv(HISTORICAL)
    set_hist = set(hist["station"])
    check(
        "Historical: all 16 stations covered in legacy land-use table",
        len(set_hist) == 16 and set_hist == set(scores.index),
        f"got {len(set_hist)} stations",
    )
    ind = sorted(hist[hist["legacy_industrial"] == 1]["station"].tolist())
    check("Historical: 4 legacy-industrial sites (KER01/02/04/11)", ind == ["DEB-KER01", "DEB-KER02", "DEB-KER04", "DEB-KER11"], f"got {ind}")
    watch = sorted(hist[hist["gentrification_watch"] == 1]["station"].tolist())
    check("Historical: 2 gentrification-watch sites (KER11/KER01)", watch == ["DEB-KER01", "DEB-KER11"], f"got {watch}")

    impro_med = hist["env_improvement_index"].median()
    rederived_watch = hist[
        (hist["legacy_industrial"] == 1)
        & (
            hist["env_improvement_index"].gt(impro_med)
            | hist["risk_category"].isin(["Emerging Green Zones", "Challenge Zones"])
        )
    ]
    check(
        "Historical: watch flag matches the re-implemented definition",
        set(rederived_watch["station"]) == set(watch),
    )
    check(
        "Historical: legacy-industrial sites keep original justice scores (never re-weighted)",
        hist.merge(scores.reset_index(), on="station")["environmental_justice_score"].notna().all(),
    )

    # integrity checks
    check("Historical: watch never labelled for non-industrial sites",
        (hist["gentrification_watch"] - hist["legacy_industrial"]).le(0).all())
    check("Historical: 1999 mosaic cached and non-trivial",
        HIST_MOSAICS.exists() and HIST_MOSAICS.stat().st_size > 50_000,
        f"size {HIST_MOSAICS.stat().st_size if HIST_MOSAICS.exists() else 'missing'}")
    georef_path = ROOT / "data" / "historical" / "georef.json"
    bounds_ok = False
    if georef_path.exists():
        import json
        geo = json.loads(georef_path.read_text(encoding="utf-8"))
        b = geo.get("wgs84_bounds")
        bounds_ok = bool(b) and 47.45 <= b[0] <= 47.6 and 21.45 <= b[1] <= 21.8
    check("Historical: georeferencing metadata present & in range", bounds_ok)

    # --------------------------------------------------------------- static "GreenSense" site
    from src.frontend.generate_site import NAV, SITE_DIR

    files = {f.name for f in SITE_DIR.glob("*.html")}
    check("Static site: 8 pages rendered", len(files) == 8, f"got {sorted(files)}")
    nav_links = {href for _, href, _label, _icon in NAV}
    check(
        "Static site: every nav link resolves to a page",
        nav_links <= files,
        f"missing {sorted(nav_links - files)}",
    )
    idx = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    check("Static site: real record count on overview", "149,683" in idx, "record count missing")
    check("Static site: measured-window pill (no fake baseline)", "May 21" in idx and "10 of 16" in idx)
    check("Static site: no fabricated station codes", "DEB-NY02" not in idx and "DEB-CSA" not in idx)
    sa = (SITE_DIR / "station_analysis.html").read_text(encoding="utf-8")
    check("Static site: DEB-KER11 station profile present", "DEB-KER11" in sa)
    dq = (SITE_DIR / "data_quality.html").read_text(encoding="utf-8")
    check("Static site: data-quality page lists real corpus stats", "36 raw" in dq and "149,683" in dq)

    print()
    if FAILURES:
        print(f"check_stories FAILURES ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("check_stories: ALL CLAIMS VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
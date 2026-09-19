"""Render the Environmental Justice infographic (PNG) for the competition pack.

Reads the pipeline outputs (`environmental_justice_scores.csv`, daily aggregates)
and draws a single-page, printer-friendly infographic to
``output/competition_submission/infographic_environmental_justice.png``.

Usage:
    python make_infographic.py
"""

import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent
SCORES = ROOT / "output" / "processed_data" / "environmental_justice_scores.csv"
OUT = ROOT / "output" / "competition_submission" / "infographic_environmental_justice.png"
OUT_HIST = ROOT / "output" / "competition_submission" / "infographic_historical.png"
HIST_CSV = ROOT / "output" / "processed_data" / "historical_gentrification.csv"
MOSAIC_1999 = ROOT / "data" / "historical" / "mosaic_1999.png"
MOSAIC_2020 = ROOT / "data" / "historical" / "mosaic_2020.png"

BAND_COLORS = {
    "Excellent": "#065F46",
    "Good": "#10B981",
    "Moderate": "#F59E0B",
    "Needs Attention": "#EF4444",
}

BG = "#0B1220"
FG = "#E2E8F0"
MUT = "#94A3B8"


def headline_bbox(ax, x, y, w, h, label, value, sub, color):
    box = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.005,rounding_size=0.012",
        linewidth=0, facecolor="#111A2E", edgecolor=color,
    )
    ax.add_patch(box)
    ax.text(x + 0.015, y + h - 0.045, label, color=MUT, fontsize=9, va="top")
    ax.text(x + 0.015, y + h * 0.42, value, color=color, fontsize=20, weight="bold", va="center")
    ax.text(x + 0.015, y + 0.015, sub, color=MUT, fontsize=7.5, va="bottom")


def render_historical() -> None:
    try:
        hist = pd.read_csv(HIST_CSV)
    except FileNotFoundError:
        print("  (historical_gentrification.csv missing — pipeline not run; skipping historical infographic)")
        return
    has_imgs = MOSAIC_1999.exists() and MOSAIC_2020.exists()

    fig = plt.figure(figsize=(12.5, 15.5), dpi=160, facecolor=BG)
    fig.subplots_adjust(left=0.06, right=0.94, top=0.94, bottom=0.04)

    # ---- title ---------------------------------------------------------------
    ax = fig.add_axes([0.06, 0.92, 0.88, 0.05])
    ax.axis("off")
    ax.text(0, 0.5, "THEN & NOW — DEBRECEN'S INDUSTRIAL PAST VS. TODAY",
            color=FG, fontsize=18, weight="bold", va="center")
    ax.text(0.0, -0.45, "1999 Cívis GIStory base maps vs. measures May–June 2026",
            color=MUT, fontsize=10, va="center")

    # ---- before/after imagery -------------------------------------------------
    if has_imgs:
        ax_before = fig.add_axes([0.06, 0.61, 0.43, 0.30])
        ax_after = fig.add_axes([0.51, 0.61, 0.43, 0.30])
        for sub_ax, path, lab in ((ax_before, MOSAIC_1999, "1999 · scanned base map"),
                                  (ax_after, MOSAIC_2020, "2020 · scanned base map")):
            sub_ax.imshow(plt.imread(path))
            sub_ax.set_title(lab, color=MUT, fontsize=9, pad=6)
            sub_ax.axis("off")
        fig.text(0.06, 0.585, "Side-by-side at the same location — imagery is for visual comparison only, "
                              "it contains no pollution record.",
                 color=MUT, fontsize=8.5, ha="left")
    else:
        ax = fig.add_axes([0.06, 0.61, 0.88, 0.30])
        ax.axis("off")
        ax.text(0.5, 0.5, "Historical base-map mosaics (1999 / 2020) unavailable offline.\n"
                         "The Cívis GIStory service caches them when internet is available.",
                color=MUT, fontsize=11, ha="center", va="center")

    # ---- KPIs ----------------------------------------------------------------
    ax = fig.add_axes([0.06, 0.435, 0.88, 0.125])
    ax.axis("off")
    n_ind = int(hist["legacy_industrial"].sum())
    n_watch = int(hist["gentrification_watch"].sum())
    top_watch = hist[hist["gentrification_watch"] == 1]["station"].str[-2:].tolist()
    kpis = [
        (f"{n_ind} / {len(hist)}", "LEGACY INDUSTRIAL SITES", "curated from 1999 map", "#F97316"),
        (f"{n_watch}", "GENTRIFICATION WATCH", "clean-up × industrial legacy", "#EF4444"),
        ("2", "BASE-MAP ERAS CACHED", "1999 + 2020 (Cívis GIStory WMS)", "#3B82F6"),
        (f"{len(top_watch)} → " + "·".join(top_watch), "WATCH LIST", "KER0x station ids", "#10B981"),
    ]
    w = 0.212
    for i, (v, lab, sub, c) in enumerate(kpis):
        headline_bbox(ax, i * (w + 0.008), 0.0, w, 1.0, lab, v, sub, c)

    # ---- watch table ---------------------------------------------------------
    ax = fig.add_axes([0.06, 0.22, 0.88, 0.20])
    ax.axis("off")
    ax.text(0, 0.98, "THE GENTRIFICATION-WATCH LIST", color=FG, fontsize=12, weight="bold", va="top")
    rows = hist.sort_values("gentrification_watch", ascending=False)
    pm_map = dict(zip(hist["station"], hist["current_PM2.5"]))
    y0 = 0.80
    for r in rows.itertuples():
        if not getattr(r, "gentrification_watch", 0):
            break
        lab = f"{r.station} · {r.location} — legacy {r.legacy_category}"
        stat = (f"improvement {r.env_improvement_index:.3f} · risk {r.risk_score:.0f}/100 "
                f"({r.risk_category}) · PM2.5 {pm_map.get(r.station, float('nan')):.1f} µg/m³")
        ax.add_patch(FancyBboxPatch((0, y0 - 0.03), 0.012, 0.17, linewidth=0,
                                    facecolor="#EF4444", edgecolor="#EF4444"))
        ax.text(0.03, y0 + 0.09, lab, color="#FCA5A5", fontsize=9.5, weight="bold", va="top")
        ax.text(0.03, y0 + 0.02, stat, color=FG, fontsize=8.2, va="top")
        y0 -= 0.145

    # ---- honesty / formula ---------------------------------------------------
    ax = fig.add_axes([0.06, 0.075, 0.88, 0.13])
    ax.axis("off")
    ax.text(0, 0.9, "WHAT IS AND ISN'T HISTORY HERE", color=FG, fontsize=10, weight="bold", va="top")
    ax.text(0, 0.55, "Measured (May–June 2026): PM2.5, PM10, NO2, O3 trends, biodiversity, transit. "
                    "Curated from the 1999 map + Debrecen geography: the legacy land-use and watch labels.",
            color=MUT, fontsize=8.5, va="center")
    ax.text(0, 0.25, "The watch signal is a correlation read-out (r ≈ 0, |r| < 0.25 for all series, n=4 sites) — "
                    "illustrative, never a causal claim, excluded from the Risk / Justice formulas.",
            color=MUT, fontsize=8.5, va="center")

    fig.text(0.5, 0.015, "Imagery: Cívis GIStory (Őrváros Közalapítvány · TOP-7.1.1-16-H-ESZA-2021-02411 · Erda Kft.) · "
                         "Green Gentrification Index · DEIK.AI Challenge 2026",
             color=MUT, fontsize=8, ha="center")

    OUT_HIST.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_HIST, facecolor=BG)
    plt.close(fig)
    print(f"Historical infographic written to {OUT_HIST}")


def main() -> int:
    df = pd.read_csv(SCORES).sort_values("environmental_justice_score", ascending=False)
    band_counts = df["justice_band"].value_counts()
    top = df.head(6)

    fig = plt.figure(figsize=(12.5, 15.5), dpi=160, facecolor=BG)
    fig.subplots_adjust(left=0.06, right=0.94, top=0.94, bottom=0.04)

    # ---- title ---------------------------------------------------------------
    ax = fig.add_axes([0.06, 0.905, 0.88, 0.07])
    ax.axis("off")
    ax.text(0, 0.62, "ENVIRONMENTAL JUSTICE IN DEBRECEN",
            color=FG, fontsize=19, weight="bold", va="center")
    ax.text(0, 0.06, "Clean air · Green space · Transit — and the right to stay",
            color=MUT, fontsize=10, va="center")

    # ---- KPI tiles -----------------------------------------------------------
    ax = fig.add_axes([0.06, 0.78, 0.88, 0.105])
    ax.axis("off")
    kpis = [
        ("16", "NEIGHBOURHOODS SCORED", "justice score 0–100", "#10B981"),
        ("10 / 16", "INCLUDE NATURE DATA", "6 re-weighted, labelled", "#F59E0B"),
        ("149,683", "AIR-QUALITY MEASUREMENTS", "full cleaning log", "#3B82F6"),
        ("230", "BIODIVERSITY OBSERVATIONS", "iNat + birds, 32 species", "#8B5CF6"),
    ]
    w = 0.212
    for i, (v, lab, sub, c) in enumerate(kpis):
        headline_bbox(ax, i * (w + 0.008), 0.0, w, 1.0, lab, v, sub, c)

    # ---- justice ranking -----------------------------------------------------
    ax = fig.add_axes([0.06, 0.565, 0.5, 0.195])
    ax.axis("off")
    ax.text(0, 0.95, "JUSTICE SCORE — TOP 6", color=FG, fontsize=12, weight="bold", va="top")
    ax.text(0, 0.02, "Risk 40% · Nature 30% · Transit 20% · Clean air 10%",
            color=MUT, fontsize=8, va="bottom")
    names = [f"{r.station[-2:]} · {r.location.split(',')[0][:16]}"
             for r in top.itertuples()]
    scores = top["environmental_justice_score"].tolist()
    colors = [BAND_COLORS[r] for r in top["justice_band"]]
    bars = fig.add_axes([0.06, 0.575, 0.5, 0.235])
    bars.set_facecolor(BG)
    for sp in bars.spines.values():
        sp.set_color("#1E293B")
    bars.tick_params(colors=MUT, labelsize=9)
    bars.set_xlim(0, 100)
    bars.barh(range(len(top) - 1, -1, -1), scores[::-1], color=colors[::-1],
              height=0.62, zorder=3)
    bars.set_yticks(range(len(top)))
    bars.set_yticklabels(names[::-1])
    bars.set_xticks([])
    for i, s in enumerate(scores[::-1]):
        bars.text(s + 1.4, i, f"{s:.0f}", color=FG, fontsize=9, weight="bold", va="center")
    bars.grid(axis="x", color="#1E293B", linewidth=0.6, zorder=0)

    # ---- band distribution ---------------------------------------------------
    ax = fig.add_axes([0.585, 0.565, 0.355, 0.195])
    ax.axis("off")
    ax.text(0.5, 0.95, "SCORE BANDS", color=FG, fontsize=12, weight="bold",
            va="top", ha="center")
    order = ["Good", "Moderate", "Needs Attention"]
    values = [int(band_counts.get(b, 0)) for b in order]
    wedges, _, autotexts = ax.pie(
        values, colors=[BAND_COLORS[b] for b in order],
        startangle=90, counterclock=False,
        autopct=lambda p: f"{int(round(p * sum(values) / 100))}",
        textprops={"color": "white", "fontsize": 11, "weight": "bold"},
        wedgeprops={"linewidth": 0, "edgecolor": BG},
    )
    labels = [f"{b}  {v}" for b, v in zip(order, values)]
    ax.legend(wedges, labels, loc="center right", bbox_to_anchor=(0.42, 0.3),
              frameon=False, fontsize=9, labelcolor=FG)
    ax.text(0, -0.12, "No station is Excellent yet — the green winner to protect barely clears", 
            ha="center", color=MUT, fontsize=7.5)

    # ---- story highlights ----------------------------------------------------
    ax = fig.add_axes([0.06, 0.36, 0.88, 0.2])
    ax.axis("off")
    ax.text(0, 0.97, "WHAT THE SCORES SAY", color=FG, fontsize=12, weight="bold", va="top")
    stories = [
        ("KER11 · Petőfi tér — Justice 74.4 (top)",
         "Emerging Green Zone, risk 79.3. 50 bus stops + biodiversity 82.6. Displacement hotspot — protect housing now.", "#EF4444"),
        ("KER14 · Mikepércs — justice 46.2, nature 69.7",
         "Cleaner air than city average, 18 species. Zero transit hides its value — protect before the first bus line.", "#F59E0B"),
        ("KER12 · Hármashegy — nature 95.6 (best)",
         "Highest biodiversity in the city over 24.6 ha. Nature returns; affordability policy must keep up.", "#10B981"),
        ("KER01 / KER04 — restoration frontier",
         "Industrial wasteland → 3.9 + 5.7 restorable ha, 1.8 very-high priority. Clean air + habitat in one lever.", "#3B82F6"),
    ]
    y0 = 0.74
    for lab, desc, c in stories:
        ax.add_patch(FancyBboxPatch((0, y0 - 0.05), 0.012, 0.2, linewidth=0, facecolor=c, edgecolor=c))
        ax.text(0.025, y0 + 0.128, lab, color=c, fontsize=9.5, weight="bold", va="top")
        ax.text(0.025, y0 + 0.055, desc, color=FG, fontsize=8.2, va="top")
        y0 -= 0.245

    # ---- footer --------------------------------------------------------------
    ax = fig.add_axes([0.06, 0.26, 0.88, 0.09])
    ax.axis("off")
    ax.text(0, 0.86, "FORMULA (documented competition weights)", color=FG, fontsize=10, weight="bold", va="top")
    ax.text(0, 0.55, "Environmental Justice = 0.40×Risk  +  0.30×Biodiversity Recovery  +  0.20×Transit  +  0.10×Clean Air",
            color="#10B981", fontsize=11, weight="bold", va="center")
    ax.text(0, 0.25, "Biodiversity Recovery Index = 0.40×Species + 0.35×Organisms + 0.25×Birds · Stations without nature data re-weight the remaining three components to 100%.",
            color=MUT, fontsize=8.2, va="center")

    fig.text(0.5, 0.015, "All figures recomputed from pipeline outputs — see check_stories.py · Green Gentrification Index · DEIK.AI Challenge 2026",
             color=MUT, fontsize=8, ha="center")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG)
    plt.close(fig)
    print(f"Infographic written to {OUT}")

    render_historical()
    return 0


if __name__ == "__main__":
    sys.exit(main())
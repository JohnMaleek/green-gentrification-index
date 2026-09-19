"""Generate the GreenSense Debrecen static front-end from the Stitch design.

Keeps the Stitch design shell (sidebar / header / typography / colour language)
but replaces the mock-up's fabricated numbers with real values from the pipeline
outputs, and embeds the real Plotly / Folium visualisations.

Usage:
    python -m src.frontend.generate_site
"""

from __future__ import annotations

import shutil
from pathlib import Path

from src.config import OUTPUT_DIR
from src.frontend.data_catalog import SiteCatalog

TEMPLATES = Path(__file__).resolve().parent.parent.parent / "frontend" / "templates"
ASSETS = Path(__file__).resolve().parent.parent.parent / "frontend" / "assets"
SITE_DIR = OUTPUT_DIR / "frontend_site"
CHARTS_DIR = SITE_DIR / "charts"

WINDOW = "May 21 – June 19, 2026"
HONESTY = (
    "GreenSense reports **measured** values from the Green Sentinel monitoring "
    f"window ({WINDOW}; DKV transit database, May 2026 statistics). "
    "Indices on this page are computed from those measurements. It contains no "
    "AQI / NDVI / satellite estimates and no 2023–2025 baseline — legacy-land-use "
    "labels are curated from the 1999/2020 Cívis GIStory base maps for visual "
    "comparison only."
)

CAT_STYLE = {
    "Emerging Green Zones": ("#BE123C", "#FFF1F2"),
    "Established Clean Areas": ("#059669", "#ECFDF5"),
    "Stable Neighborhoods": ("#D97706", "#FFFBEB"),
    "Challenge Zones": ("#EA580C", "#FFF7ED"),
}
BAND_STYLE = {
    "Critical": "#7F1D1D",
    "High": "#DC2626",
    "Moderate": "#F59E0B",
    "Low": "#10B981",
}

NAV = [
    ("overview", "index.html", "Overview", "explore"),
    ("risk-map", "risk_map.html", "Risk Map", "my_location"),
    ("environmental-trends", "environmental_trends.html", "Environmental Trends", "trending_up"),
    ("risk-analysis", "risk_matrix.html", "Risk Analysis", "grid_view"),
    ("station-analysis", "station_analysis.html", "Station Analysis", "cell_tower"),
    ("data-quality", "data_quality.html", "Data Quality", "verified_user"),
]

REAL_CHARTS = {
    "debrecen_risk_map.html": "risk_map.html",
    "risk_matrix.html": "risk_matrix.html",
    "risk_scoreboard.html": "risk_scoreboard.html",
    "clean_air_timeline.html": "clean_air_timeline.html",
    "justice_scorecard.html": "justice_scorecard.html",
    "justice_quadrant.html": "justice_quadrant.html",
    "pm25_timeseries.html": "pm25_timeseries.html",
    "improvement_slopes.html": "improvement_slopes.html",
    "pollutant_distributions.html": "pollutant_distributions.html",
    "historical_then_now_map.html": "historical_then_now.html",
    "justice_restoration_map.html": "justice_restoration_map.html",
}


# ---------------------------------------------------------------------------
# HTML helpers (reuse the Stitch Tailwind design language)
# ---------------------------------------------------------------------------
def pill(text: str, cls: str = "bg-surface-container-low text-on-surface-variant", icon: str | None = None) -> str:
    icon_html = f"<span class=\"material-symbols-outlined text-[14px]\">{icon}</span>" if icon else ""
    return (
        f"<span class=\"inline-flex items-center gap-1 px-2.5 py-1 rounded-full {cls} "
        f"font-label-sm text-label-sm\">{icon_html} {text}</span>"
    )


def section_title(eyebrow: str, title: str, sub: str | None = None) -> str:
    sub_html = (
        f"<p class=\"font-body-md text-body-md text-on-surface-variant mt-1 max-w-3xl\">{sub}</p>"
        if sub
        else ""
    )
    return (
        f"<div class=\"flex flex-col gap-space-xs mb-space-md pt-space-md\">"
        f"<span class=\"font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">{eyebrow}</span>"
        f"<h2 class=\"font-headline-lg text-headline-lg text-on-surface tracking-tight\">{title}</h2>"
        f"{sub_html}</div>"
    )


def kpi_card(label: str, value: str, badge: str, desc: str, footer: str | None = None, icon: str = "monitoring") -> str:
    foot = (
        f"<div class=\"flex items-center justify-between pt-space-xs\"><span class=\"font-label-sm text-label-sm "
        f"text-on-surface-variant\">{footer}</span></div>"
        if footer
        else ""
    )
    return f"""
<div class="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow relative overflow-hidden">
  <div class="absolute top-0 right-0 w-24 h-24 bg-secondary-container/20 rounded-bl-full pointer-events-none"></div>
  <div class="flex items-center justify-between mb-space-xs">
    <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">{label}</span>
    <span class="material-symbols-outlined text-secondary text-[22px]">{icon}</span>
  </div>
  <div class="flex items-baseline gap-space-xs my-space-xs flex-wrap">
    <span class="font-headline-xl text-headline-xl text-on-surface font-bold">{value}</span>
    <span class="font-label-sm text-label-sm px-2 py-0.5 rounded-full bg-secondary-fixed/25 text-on-secondary-container font-semibold">{badge}</span>
  </div>
  <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed mb-space-sm">{desc}</p>
  {foot}
</div>"""


def chip(text: str, category: str, count: str | None = None) -> str:
    fg, bg = CAT_STYLE.get(category, ("#64748B", "#EFF4FF"))
    n = f"<span class=\"font-bold\">{count}</span>&nbsp;" if count else ""
    return (
        f"<span class=\"inline-flex items-center gap-1 px-2.5 py-1 rounded-full font-label-sm text-label-sm\" "
        f"style=\"color:{fg};background:{bg}\">"
        f"<span class=\"w-2 h-2 rounded-full\" style=\"background:{fg}\"></span>{n}{text}</span>"
    )


def band_pill(score: float) -> str:
    band = ("Low" if score < 31 else "Moderate" if score < 61 else "High" if score < 81 else "Critical")
    fg = BAND_STYLE[band].replace("#", "#")
    return pill(f"{band} {score:.0f}/100", cls=f"font-semibold", )


def hero(title: str, sub: str, pills_markup: str) -> str:
    return f"""
<section class="relative rounded-3xl bg-surface-container-lowest overflow-hidden shadow-sm p-space-lg lg:p-space-xl mb-space-lg">
  <div class="absolute -right-24 -top-24 w-96 h-96 rounded-full bg-secondary-fixed/20 blur-3xl pointer-events-none"></div>
  <div class="absolute right-1/3 bottom-0 w-80 h-80 rounded-full bg-tertiary-fixed/30 blur-3xl pointer-events-none"></div>
  <div class="relative z-10 flex flex-col gap-space-md">
    <div class="flex flex-wrap items-center gap-space-xs">{pills_markup}</div>
    <h1 class="font-headline-xl text-headline-xl text-on-surface tracking-tight leading-tight">{title}</h1>
    <p class="font-body-lg text-body-lg text-on-surface-variant max-w-3xl">{sub}</p>
  </div>
</section>"""


def chart_embed(src: str, height: int = 520, caption: str | None = None) -> str:
    cap = f"<p class=\"font-body-sm text-body-sm text-on-surface-variant mt-2\">{caption}</p>" if caption else ""
    return f"""
<div class="rounded-3xl bg-surface-container-lowest shadow-sm p-space-md flex flex-col overflow-hidden mb-space-lg">
  <iframe src="{src}" title="GreenSense chart" class="w-full border-0 rounded-xl" style="height:{height}px" loading="lazy"></iframe>
  {cap}
</div>"""


def data_card(title: str, rows: list[tuple[str, str]], accent_icon: str = "data_object") -> str:
    body = "".join(
        f"<div class=\"flex items-center justify-between py-1.5 border-b border-surface-container last:border-0\">"
        f"<span class=\"font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide\">{k}</span>"
        f"<span class=\"font-body-md text-body-md text-on-surface font-semibold\">{v}</span></div>"
        for k, v in rows
    )
    return f"""
<div class="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm hover:shadow-md transition-shadow">
  <div class="flex items-center justify-between mb-space-sm">
    <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">{title}</span>
    <span class="material-symbols-outlined text-secondary text-[20px]">{accent_icon}</span>
  </div>
  {body}
</div>"""


def honesty_note() -> str:
    return f"""
<section class="rounded-3xl bg-surface-container-low p-space-lg mt-space-lg">
  <div class="flex gap-space-sm">
    <span class="material-symbols-outlined text-secondary text-[20px]">verified</span>
    <div>
      <h3 class="font-headline-sm text-headline-sm text-on-surface">Methodology & sources</h3>
      <p class="font-body-sm text-body-sm text-on-surface-variant mt-1">{HONESTY}</p>
    </div>
  </div>
</section>"""


def open_main() -> str:
    return (
        "<main class=\"w-full pt-16 bg-surface min-h-screen px-margin-desktop py-space-xl\">"
        "<div class=\"flex flex-col w-full\">"
    )


def close_main() -> str:
    return "</div></main>"


# ---------------------------------------------------------------------------
# shell handling
# ---------------------------------------------------------------------------
def build_shell(template: Path, active: str) -> str:
    html = template.read_text(encoding="utf-8")
    i = html.find("<main")
    if i < 0:
        raise ValueError(f"{template.name}: no <main> tag found")
    shell = html[:i]

    # censor the two header pills
    shell = shell.replace(
        "2023–2025 Historical Baseline (30-day Rolling Live)",
        "May 21 – Jun 19, 2026 measured window",
    )
    shell = shell.replace(
        "2023-2025 Historical Baseline (30-day Rolling Live)",
        "May 21 – Jun 19, 2026 measured window",
    )
    shell = shell.replace(
        "Live Dataset: 16 Stations Active",
        "Live Dataset: 10 of 16 stations monitored",
    )

    # fix nav hrefs + active state
    for path, href, _label, _icon in NAV:
        if path == active:
            shell = shell.replace(
                f'data-path="{path}"',
                f'data-path="{path}" aria-current="page"',
            )
    # class-activate the current page link
    src_active = (
        "class=\"flex items-center gap-space-sm px-space-md py-space-sm rounded-lg bg-primary "
        "text-secondary-fixed font-bold shadow-sm\""
    )
    shell = shell.replace(src_active, src_active.replace("rounded-lg bg-primary", "rounded-lg cursor-default"))
    shell = shell.replace(f'href="#"', "href=\"#\"")  # no-op placeholder

    # turn data-path anchors into real links (remove data-path after href fix)
    for path, href, _label, _icon in NAV:
        shell = shell.replace(f'data-path="{path}" href="#"', f'href="{href}"')
        shell = shell.replace(f'data-path="{path}"', f'href="{href}"')
    return shell


ACTIVE_CLASS = (
    "class=\"flex items-center gap-space-sm px-space-md py-space-sm rounded-lg bg-primary "
    "text-secondary-fixed font-bold shadow-sm\""
)
IDLE_CLASS = (
    "class=\"flex items-center gap-space-sm px-space-md py-space-sm rounded-lg "
    "text-primary-fixed-dim hover:bg-primary hover:text-surface-container-lowest "
    "transition-all duration-150\""
)


def _shell_fragment(template: Path) -> str:
    """Return the page head + sidebar + header (everything before <main>)."""
    html = template.read_text(encoding="utf-8")
    i = html.find("<main")
    if i < 0:
        raise ValueError(f"{template.name}: no <main> tag")
    shell = html[:i]
    shell = shell.replace(
        "2023–2025 Historical Baseline (30-day Rolling Live)", "May 21 – Jun 19, 2026 measured window"
    )
    shell = shell.replace(
        "2023-2025 Historical Baseline (30-day Rolling Live)", "May 21 – Jun 19, 2026 measured window"
    )
    shell = shell.replace(
        "Live Dataset: 16 Stations Active", "Live Dataset: 10 of 16 stations monitored"
    )
    return shell


def nav_anchor(path: str, href: str, label: str, icon: str, active: bool) -> str:
    cls = (
        "flex items-center gap-space-sm px-space-md py-space-sm rounded-lg bg-primary "
        "cursor-default text-secondary-fixed font-bold shadow-sm"
        if active
        else "flex items-center gap-space-sm px-space-md py-space-sm rounded-lg text-primary-fixed-dim "
        "hover:bg-primary hover:text-surface-container-lowest transition-all duration-150"
    )
    cur = ' aria-current="page"' if active else ""
    return (
        f'<a href="{href}" class="{cls}"{cur}>'
        f'<span class="material-symbols-outlined text-[20px]">{icon}</span>'
        f'<span class="font-label-md text-label-md">{label}</span></a>'
    )


def shell_with_nav(template: Path, active: str) -> str:
    """Return the head+sidebar+header with nav wired to real pages."""
    shell = _shell_fragment(template)
    for path, href, label, icon in NAV:
        start = shell.find(f'data-path="{path}"')
        while start >= 0:
            tag_start = shell.rfind("<a ", 0, start)
            tag_end = shell.find("</a>", start)
            if tag_start >= 0 and tag_end > tag_start:
                a = nav_anchor(path, href, label, icon, path == active)
                shell = shell[:tag_start] + a + shell[tag_end + len("</a>"):]
            start = shell.find(f'data-path="{path}"')
    return shell


def wrap_page(template: Path, active: str, content: str) -> str:
    """Full HTML document: shell + main content + closing tags."""
    shell = shell_with_nav(template, active)
    return (
        shell
        + open_main()
        + content
        + close_main()
        + "</div>\n</body></html>\n"
    )


def finalize(content: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\"/>\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
        "<title>GreenSense Debrecen — Civic Environmental Intelligence</title>\n"
        "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\"/>\n"
        "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin/>\n"
        "<link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700&display=swap\" rel=\"stylesheet\"/>\n"
        "<link href=\"https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0\" rel=\"stylesheet\"/>\n"
        "<script src=\"https://cdn.tailwindcss.com\"></script>\n"
        "<style>html,body{margin:0;padding:0}body{overscroll-behavior:none}::-webkit-scrollbar{display:none}</style>\n"
        "</head>\n"
        "<body class=\"bg-surface font-body-md text-on-surface antialiased\">\n"
        + content
        + "\n</body></html>\n"
    )


# ---------------------------------------------------------------------------
# page builders
# ---------------------------------------------------------------------------
def page_overview(c: SiteCatalog) -> str:
    s = c.stats
    pm = c.city_pm
    counts = c.category_counts
    h = c.highlights()
    st = {x["station"]: x for x in c.stations()}

    pills_html = (
        pill("DEIK.AI 2026 · Category B", "bg-primary-container text-secondary-fixed", "bolt")
        + pill("16 stations · 10 monitored", "bg-surface-container-low text-on-surface-variant")
        + pill(f"{s['bus_stops']} DKV transit stops", "bg-surface-container-low text-on-tertiary-fixed-variant", "directions_bus")
        + pill("measured window", "bg-surface-container-high text-on-surface", "schedule")
    )
    top_n = st[h["top_nature_station"]]["location"]

    content = hero(
        "Is Debrecen getting cleaner — and is it fair?",
        "GreenSense fuses Green Sentinel municipal telemetry with DKV public-transit accessibility to find "
        "where air is improving fastest and how those neighbourhoods face development pressure. Every figure "
        "below is measured, not modelled.",
        pills_html,
    )

    kpis = (
        kpi_card("Raw records", f"{s['raw_rows']:,}", f"{s['raw_files']} files", "Imported Green Sentinel measurements across air, water and noise categories.", footer=s["window"], icon="database")
        + kpi_card("Stations", str(s["n_stations"]), f"{s['n_monitored']} monitored", "16 sensing nodes; 10 have validated biodiversity records in the window.", footer=f"{s['measurement_types']} measurement types", icon="sensors")
        + kpi_card("City PM2.5 (daily mean)", f"{pm['pm25_mean']:.1f} µg/m³", "measured", "Every station already meets the WHO 15 µg/m³ and EU 2030 10 µg/m³ targets.", footer="May 21 – Jun 19, 2026", icon="air")
        + kpi_card("Highest risk", f"{h['top_risk_station']} · {h['top_risk_score']:.0f}/100", f"{h['top_risk_band']}", f"{st[h['top_risk_station']]['location']} — {h['top_risk_category']}.", footer="Risk Score: 40/30/20/10 weighted", icon="priority_high")
        + kpi_card("Justice leader", f"{h['top_justice_station']} · {h['top_justice_score']:.0f}/100", f"{h['top_justice_band']}", "Best measured combination of improving air, nature recovery and transit access.", footer="Environmental Justice Score", icon="verified_user")
        + kpi_card("Nature recovery leader", f"{h['top_nature_station']} · {h['top_nature_index']:.0f}/100", "monitored", f"{top_n} shows the strongest biodiversity recovery in the dataset.", footer=f"{h['legacy_industrial']} legacy-industrial · {h['watch']} watch sites", icon="forest")
    )
    content += (
        '<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-space-md mb-space-lg">' + kpis + "</div>"
    )

    content += section_title(
        "Classification",
        "Risk categories across the municipal grid",
        "Colours follow the civic semantic scale used across the dashboard: emerald = already clean, amber = stable, coral = challenge, ruby = emerging green (fastest cleaning while still polluted).",
    )
    chips = '<div class="flex flex-wrap items-center gap-space-sm mb-space-lg">' + "".join(
        chip(cat, cat, str(counts.get(cat, 0))) for cat in ("Established Clean Areas", "Stable Neighborhoods", "Challenge Zones", "Emerging Green Zones")
    ) + "</div>"
    content += chips

    content += section_title(
        "Clean-air timeline",
        "Who cleans up first?",
        "8 of 16 stations already meet the stricter WHO-annual guideline (5 µg/m³); 6 are improving on track; 2 are not on track.",
    )
    content += chart_embed("charts/risk_scoreboard.html", 480, "Real risk scoreboard for all 16 stations, ranked by the 0–100 Risk Score.")
    content += chart_embed("charts/clean_air_timeline.html", 440, "Months until each station reaches the WHO-annual PM2.5 guideline at its measured improvement rate.")

    content += section_title(
        "Environmental justice",
        "Cleaning up — but is it fair?",
        "The Justice Score weighs gentrification risk (40%), biodiversity recovery (30%), transit access (20%) and current air (10%).",
    )
    content += chart_embed("charts/justice_scorecard.html", 460, "Justice scorecards for all neighbourhoods with measured biodiversity data.")
    content += honesty_note()
    return content


def station_table(c: SiteCatalog) -> str:
    rows = c.stations()
    rows.sort(key=lambda r: -r["risk_score"])
    trs = []
    for r in rows:
        fg, bg = CAT_STYLE[r["category"]]
        j = f"{r['justice_score']:.0f}" if r["justice_score"] is not None else "no bio data"
        months = f"{r['months']:.1f}" if r["months"] is not None else ("" if r["timeline"] == "Already met" else "—")
        mark = "▲ watch" if r["watch"] else "·"
        trs.append(
            "<tr class=\"border-b border-surface-container last:border-0 hover:bg-surface-container-low/60\">"
            f"<td class=\"px-4 py-3\"><span class=\"font-label-md text-label-md text-on-surface\">{r['station']}</span>"
            f"<span class=\"font-body-sm text-body-sm text-on-surface-variant block\">{r['location']}</span></td>"
            f"<td class=\"px-4 py-3\"><span class=\"inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-label-sm text-label-sm\" style=\"color:{fg};background:{bg}\">{r['category']}</span></td>"
            f"<td class=\"px-4 py-3 font-body-md text-body-md text-on-surface font-semibold\">{r['risk_score']:.0f}</td>"
            f"<td class=\"px-4 py-3 font-body-md text-body-md text-on-surface tabular-nums\">{r['pm25']:.1f} µg/m³</td>"
            f"<td class=\"px-4 py-3 font-body-md text-body-md tabular-nums\" style=\"color:{'#059669' if r['trend'] < 0 else '#DC2626'}\">{r['trend']:+.4f}/day</td>"
            f"<td class=\"px-4 py-3 font-body-md text-body-md text-on-surface tabular-nums\">{r['bus_stops']}</td>"
            f"<td class=\"px-4 py-3 font-body-md text-body-md text-on-surface tabular-nums\">{months}</td>"
            f"<td class=\"px-4 py-3 font-body-md text-body-md text-on-surface\">{j}</td>"
            f"<td class=\"px-4 py-3\"><span class=\"font-label-sm text-label-sm\" style=\"color:{'#BE123C' if r['watch'] else '#94A3B8'}\">{mark}</span></td>"
            "</tr>",
        )
    head = (
        "<tr class=\"text-left\">"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Station</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Category</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Risk</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">PM2.5</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">PM2.5 slope</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Bus stops ≤1 km</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Months→WHO5</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Justice</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Flag</th>"
        "</tr>"
    )
    return (
        '<div class="rounded-3xl bg-surface-container-lowest shadow-sm overflow-hidden mb-space-lg">'
        '<div class="overflow-x-auto"><table class="w-full text-sm">'
        + head + "".join(trs) + "</table></div></div>"
    )


def page_risk_map(c: SiteCatalog) -> str:
    s = c.stats
    pills_html = (
        pill("DEIK.AI 2026", "bg-primary-container text-secondary-fixed", "bolt")
        + pill(f"{s['n_stations']} stations · real coordinates", "bg-surface-container-low text-on-surface-variant", "location_on")
        + pill(s["window"], "bg-surface-container-high text-on-surface", "schedule")
    )
    content = hero(
        "Interactive risk map",
        "Sampled pollution and risk statistics geolocated at the real monitoring stations. Values are daily means "
        "over the measured window.",
        pills_html,
    )
    content += section_title(
        "Geospatial telemetry",
        "Debrecen — measured monitoring network",
        "Marker size scales with the Risk Score; colour follows the risk category. Hover for per-station measured values.",
    )
    content += chart_embed("charts/risk_map.html", 600, "Folium map built from the real station coordinates and risk report (output/visualizations/debrecen_risk_map.html).")
    content += section_title("Station catalogue", "All 16 stations, ranked by Risk Score", "Risk Score = 0.40·improvement + 0.30·pollution + 0.20·transit + 0.10·stability, min-max normalised across stations.")
    content += station_table(c)
    content += honesty_note()
    return content


def page_risk_matrix(c: SiteCatalog) -> str:
    content = hero(
        "Risk matrix — environmental shift vs. current pollution",
        "Bivariate view of the 16 stations: how fast the air is improving (Improvement Index) against the current "
        "risk score. Stations in the top-right combine momentum with exposure — the development-pressure set.",
        pill("measured window", "bg-surface-container-high text-on-surface", "schedule") + pill("16 stations", "bg-surface-container-low text-on-surface-variant"),
    )
    content += section_title("Bivariate model", "Risk quadrant", "Bubble colour follows the risk category; position follows current pollution and environmental improvement.")
    content += chart_embed("charts/risk_matrix.html", 520, "Real risk quadrant from output/visualizations/risk_matrix.html.")
    content += section_title("Justice × nature", "Is everyone sharing the recovery?", "Where gentrification risk meets biodiversity recovery — the displacement-watch tension.")
    content += chart_embed("charts/justice_quadrant.html", 520, "Real quadrant from output/visualizations/justice_quadrant.html.")
    content += honesty_note()
    return content


def page_trends(c: SiteCatalog) -> str:
    content = hero(
        "Environmental trends",
        "Daily aggregates across the whole network for the measured window. No projection — the traces are the "
        "measurements themselves.",
        pill("May 21 – Jun 19, 2026", "bg-surface-container-high text-on-surface", "schedule") + pill("daily means", "bg-surface-container-low text-on-surface-variant"),
    )
    content += section_title("Time series", "PM2.5 — the pollutant that matters most here", "All Debrecen stations sit well inside the WHO 24-hour/IT-3 (15 µg/m³) and EU-2030 (10 µg/m³) targets in this window.")
    content += chart_embed("charts/pm25_timeseries.html", 500, "PM2.5 daily means for the top five stations by record coverage.")
    content += section_title("Slopes", "Environmental improvement index", "Per-station linear improvement slope — negative days mean falling PM2.5.")
    content += chart_embed("charts/improvement_slopes.html", 440, "Improvement slopes for all stations.")
    content += section_title("Distribution", "Pollutant distribution overview", "Box/band view of the measured concentrations.")
    content += chart_embed("charts/pollutant_distributions.html", 440, "Measured distributions across pollutants and stations.")
    content += honesty_note()
    return content


def page_station_analysis(c: SiteCatalog) -> str:
    k = c.ker11()
    jus = c.justice().set_index("station")
    j = jus.loc["DEB-KER11"]
    content = hero(
        "Station deep-dive — DEB-KER11 Petőfi tér",
        "The fastest-cleaning station that is still under real exposure pressure: improving air, strong nature "
        "recovery and peak transit access combine into the highest Justice Score on the network.",
        pill("Emerging Green Zone", "font-semibold") + pill("High 79/100", "bg-error-container text-on-error-container") + pill("watch site", "bg-error-container text-on-error-container", "priority_high"),
    )
    month = f"{k['months']:.1f}" if k and k["months"] is not None else "—"
    cards = kpi_card("Justice Score", f"{j['environmental_justice_score']:.0f} / 100", str(j["justice_band"]), "Highest Justice Score on the network.", footer="Environmental Justice", icon="verified_user")
    cards += kpi_card("Current PM2.5", f"{k['pm25']:.1f} µg/m³", "daily mean", "Measured across the window.", footer=f"WHO 24h 15 · EU 2030 10 µg/m³ ({k['pm10']:.0f} µg/m³ PM10)", icon="air")
    cards += kpi_card("PM2.5 slope", f"{k['trend']:+.4f} µg/m³/day", "falling = improving", "Linear daily trend from the measured series.", footer=f"~{month} months to WHO-annual (5 µg/m³) · {k['target_date']}", icon="trending_down" if k["trend"] < 0 else "trending_up")
    cards += kpi_card("Biodiversity recovery", f"{j['biodiversity_recovery_index']:.0f} / 100", "monitored", f"{int(j['inat_species'])} iNaturalist species · {int(j['bird_rare'])} rare bird records · {j['habitat_area_ha']:.1f} ha habitat.", footer="diversity score", icon="forest")
    cards += kpi_card("Transit access", f"{k['bus_stops']} bus stops", "≤ 1 km", "DKV network within walking distance of the station.", footer=f"Transit component {j['transit_component']:.0f}/100", icon="directions_bus")
    cards += kpi_card("Legacy & watch", "watch site", "curated", f"1990s railway-industrial land use (Cívis GIStory 1999 map). Flagged for gentrification pressure.", footer="visual comparison only", icon="inventory_2")
    content += '<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-space-md mb-space-lg">' + cards + "</div>"

    details = data_card(
        "Measured identity",
        [
            ("Station", "DEB-KER11"),
            ("Location", k["location"]),
            ("Coordinates", f"{k['lat']:.5f}, {k['lon']:.5f}"),
            ("Risk band", f"{k['risk_band']} · {k['risk_score']:.0f}/100"),
            ("Timeline", f"{k['timeline']} → {k['target_date']}"),
            ("Nature data", "monitored — 10 of 16 stations have it"),
        ],
        "location_on",
    )
    content += '<div class="grid grid-cols-1 lg:grid-cols-2 gap-space-md mb-space-lg">' + details + "</div>"

    content += section_title("Context", "City-wide PM2.5 traces", "The station sits inside the full-network trend below.")
    content += chart_embed("charts/pm25_timeseries.html", 460, "PM2.5 daily means (top five stations by coverage).")
    content += chart_embed("charts/historical_then_now.html", 520, "Then & now overlay of the same Neighbourhood (1999/2020 Cívis GIStory base maps) with watch markers.")
    content += honesty_note()
    return content


def page_data_quality(c: SiteCatalog) -> str:
    s = c.stats
    content = hero(
        "Data engineering pipeline & telemetry quality",
        "Every number shipped downstream starts as a raw measurement. This page documents exactly what the 2026 "
        "dataset contains and how it was cleaned.",
        pill("real raw corpus", "bg-surface-container-high text-on-surface", "verified") + pill(s["window"], "bg-surface-container-low text-on-surface-variant", "schedule"),
    )
    kpis = (
        kpi_card("Raw records", f"{s['raw_rows']:,}", f"{s['raw_files']} files", "Green Sentinel measurements (air, water, noise) before cleaning.", footer=s["window"], icon="database")
        + kpi_card("Stations", str(s["n_stations"]), f"{s['n_monitored']} monitored", "16 sensing nodes · 18 measurement types.", footer="Moved to features", icon="sensors")
        + kpi_card("Negative anomalies", f"{s['negative_anomalies']:,} ({s['negative_anomaly_pct']:.2f}%)", "flagged", "Invalid negative values removed before analysis.", footer="replaced as NaN", icon="warning")
        + kpi_card("Outliers >3σ", f"{s['outliers_flagged']:,}", "retained", "Extreme values kept — they may be real pollution events.", footer="documented, not dropped", icon="tune")
        + kpi_card("Missing after imputation", "0", "ffill/bfill", "Per-station forward/backward fill by measurement type.", footer="no artificial interpolation", icon="check_circle")
        + kpi_card("DKV transit nodes", f"{s['bus_stops']:,}", "May 2026 stats", "Public-transport stops used for the transit accessibility component.", footer="DKV database", icon="directions_bus")
    )
    content += '<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-space-md mb-space-lg">' + kpis + "</div>"

    content += section_title(
        "Cleaning pipeline",
        "From raw sensor bytes to daily means",
        "Four honest steps — no 2023–2025 baseline, no AQI, no satellite estimates.",
    )
    steps = [
        ("1 · Ingest", "Import the 36 raw CSV files; parse timestamps across all stations."),
        ("2 · Clean", "Negative sensor readings flagged as anomalies and replaced with NaN."),
        ("3 · Impute", "Forward-fill then backward-fill within each station + measurement type."),
        ("4 · Aggregate", "Daily means per station per pollutant; outliers >3σ documented and retained."),
    ]
    step_html = "".join(
        f'<div class="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm flex flex-col gap-space-xs">'
        f'<span class="font-label-md text-label-md text-secondary font-bold uppercase tracking-wide">{t}</span>'
        f'<p class="font-body-sm text-body-sm text-on-surface-variant">{d}</p></div>'
        for t, d in steps
    )
    content += '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md mb-space-lg">' + step_html + "</div>"

    content += section_title("Per-station", "Record coverage by station", "Records counted after cleaning; coverage = rows present vs. expected.")
    content += quality_table(c)
    content += honesty_note()
    return content


def quality_table(c: SiteCatalog) -> str:
    g = c.per_station_quality()
    trs = []
    for r in g.to_dict("records"):
        trs.append(
            "<tr class=\"border-b border-surface-container last:border-0 hover:bg-surface-container-low/60\">"
            f"<td class=\"px-4 py-3 font-label-md text-label-md text-on-surface\">{r['station']}</td>"
            f"<td class=\"px-4 py-3 font-body-md text-body-md text-on-surface tabular-nums\">{int(r['Records']):,}</td>"
            f"<td class=\"px-4 py-3 font-body-md text-body-md text-on-surface tabular-nums\">{r['Measurement_Types']}</td>"
            f"<td class=\"px-4 py-3 font-body-md text-body-md text-on-surface tabular-nums\">{r['Missing_Pct']:.2f}%</td>"
            f"<td class=\"px-4 py-3\"><div class=\"w-40 h-2 rounded-full bg-surface-container-high overflow-hidden\">"
            f"<div class=\"h-full rounded-full bg-secondary\" style=\"width:{int(r['Coverage'])}%\"></div></div></td>"
            f"<td class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant\">{int(r['Coverage'])}% coverage</td>"
            "</tr>",
        )
    head = (
        "<tr class=\"text-left\">"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Station</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Records</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Types</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Missing %</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Coverage</th>"
        "<th class=\"px-4 py-3 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider\">Status</th>"
        "</tr>"
    )
    return (
        '<div class="rounded-3xl bg-surface-container-lowest shadow-sm overflow-hidden mb-space-lg">'
        '<div class="overflow-x-auto"><table class="w-full text-sm">' + head + "".join(trs) + "</table></div></div>"
    )


def page_loading() -> str:
    anim_css = """<style>
@keyframes pulseRing { 0% { transform: scale(0.96); opacity: 0.8; } 50% { transform: scale(1.04); opacity: 0.3; } 100% { transform: scale(0.96); opacity: 0.8; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
.shimmer-bar { background: linear-gradient(90deg, rgba(16,185,129,0.2), rgba(52,211,153,0.9), rgba(16,185,129,0.2)); background-size: 200% 100%; animation: shimmer 2s linear infinite; }
</style>"""
    return f"""
<div class="min-h-screen bg-primary-container text-on-primary flex items-center justify-center p-space-lg">
  <div class="flex flex-col items-center gap-space-lg max-w-lg text-center">
    <div class="relative w-28 h-28 flex items-center justify-center">
      <div class="absolute inset-0 rounded-full border-2 border-secondary/40" style="animation:pulseRing 3.5s ease-in-out infinite"></div>
      <div class="absolute inset-2 rounded-full border-2 border-secondary/30" style="border-top-color:#10B981;animation:spin 3s linear infinite"></div>
      <span class="material-symbols-outlined text-[34px] text-secondary-fixed">public</span>
    </div>
    <div>
      <div class="font-headline-xl text-headline-xl font-bold tracking-tight">GreenSense</div>
      <div class="font-label-md text-label-md text-secondary-fixed uppercase tracking-widest mt-1">Debrecen · DEIK.AI 2026 · Category B</div>
    </div>
    <p class="font-body-md text-body-md text-secondary-fixed/90">Civic environmental intelligence for Debrecen.</p>
    <div class="w-full h-2 rounded-full bg-on-primary/20 overflow-hidden"><div class="h-full w-2/3 rounded-full bg-secondary shimmer-bar"></div></div>
    <p class="font-body-sm text-body-sm text-secondary-fixed/80">
      Connecting 16 Green Sentinel nodes · 10 with validated records · DKV transit network (687 stops) ·
      measured window {WINDOW}.
    </p>
    <div class="flex flex-wrap justify-center gap-space-sm pt-space-md">
      <a href="index.html" class="inline-flex items-center gap-space-xs px-4 py-2 rounded-lg bg-secondary text-on-secondary font-label-md text-label-md hover:opacity-90">Executive overview</a>
      <a href="risk_map.html" class="inline-flex items-center gap-space-xs px-4 py-2 rounded-lg bg-on-primary/10 text-secondary-fixed border border-on-primary/20 font-label-md text-label-md hover:bg-on-primary/20">Risk map</a>
    </div>
  </div>
</div>
{anim_css}"""


def page_coat_of_arms() -> str:
    svg = (ASSETS / "coa_hungary_town_debrecen.svg").read_text(encoding="utf-8")
    svg = svg.replace('width="545"', 'width="120"').replace('width="545.1"', 'width="120"').replace('height="120"', '')
    return f"""
<div class="min-h-screen bg-surface flex items-center justify-center p-space-lg">
  <div class="flex flex-col items-center gap-space-md max-w-xl text-center">
    <div class="rounded-3xl bg-surface-container-lowest p-space-lg shadow-sm flex items-center justify-center w-64 h-64">
      <div class="w-40">{svg}</div>
    </div>
    <h1 class="font-headline-lg text-headline-lg text-on-surface tracking-tight">Debrecen — coat of arms</h1>
    <p class="font-body-md text-body-md text-on-surface-variant max-w-md">
      Official civic emblem of Debrecen, reproduced from the public civic brand assets bundled with the
      Stitch design.
    </p>
    <a href="index.html" class="inline-flex items-center gap-space-xs px-4 py-2 rounded-lg bg-primary text-secondary-fixed font-label-md text-label-md hover:bg-primary/90">Overview</a>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def build(c: SiteCatalog | None = None, out: Path | None = None) -> int:
    c = c or SiteCatalog()
    site = Path(out or SITE_DIR)
    charts = site / "charts"
    site.mkdir(parents=True, exist_ok=True)
    charts.mkdir(parents=True, exist_ok=True)

    # copy the real visualisations
    viz = OUTPUT_DIR / "visualizations"
    copied: list[str] = []
    for real_name, site_name in REAL_CHARTS.items():
        src = viz / real_name
        if src.exists():
            shutil.copy2(src, charts / site_name)
            copied.append(site_name)

    # build pages on the shared shell, wiring the active nav item per page
    shell_template = TEMPLATES / "overview.html"
    nav_active = {
        "index.html": "overview",
        "risk_map.html": "risk-map",
        "risk_matrix.html": "risk-analysis",
        "environmental_trends.html": "environmental-trends",
        "station_analysis.html": "station-analysis",
        "data_quality.html": "data-quality",
    }
    inner = {
        "index.html": page_overview(c),
        "risk_map.html": page_risk_map(c),
        "risk_matrix.html": page_risk_matrix(c),
        "environmental_trends.html": page_trends(c),
        "station_analysis.html": page_station_analysis(c),
        "data_quality.html": page_data_quality(c),
    }
    pages = {
        name: wrap_page(shell_template, active, inner[name])
        for name, active in nav_active.items()
    }

    # standalone splash pages
    pages["loading.html"] = finalize(page_loading())
    pages["coat_of_arms.html"] = finalize(page_coat_of_arms())

    for name, html in pages.items():
        (site / name).write_text(html, encoding="utf-8")
        print(f"WROTE {site / name} ({len(html):,} bytes)")

    print(f"COPIED charts: {len(copied)} — {', '.join(sorted(copied))}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(build())
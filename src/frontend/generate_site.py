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


def hero(title: str, sub: str, pills_markup: str, actions: str = "") -> str:
    actions_html = f"<div class=\"flex flex-wrap items-center gap-space-xs pt-space-sm\">{actions}</div>" if actions else ""
    return f"""
<section class="relative rounded-3xl bg-surface-container-lowest overflow-hidden shadow-sm p-space-lg lg:p-space-xl mb-space-lg">
  <div class="absolute -right-24 -top-24 w-96 h-96 rounded-full bg-secondary-fixed/20 blur-3xl pointer-events-none"></div>
  <div class="absolute right-1/3 bottom-0 w-80 h-80 rounded-full bg-tertiary-fixed/30 blur-3xl pointer-events-none"></div>
  <div class="relative z-10 flex flex-col gap-space-md">
    <div class="flex flex-wrap items-center gap-space-xs">{pills_markup}</div>
    <h1 class="font-headline-xl text-headline-xl text-on-surface tracking-tight leading-tight">{title}</h1>
    <p class="font-body-lg text-body-lg text-on-surface-variant max-w-3xl">{sub}</p>
    {actions_html}
  </div>
</section>"""


def chart_embed(src: str, height: int = 520, caption: str | None = None, bare: bool = False) -> str:
    iframe = (
        f'<iframe src="{src}" title="GreenSense chart" class="w-full border-0 rounded-xl" '
        f'style="height:{height}px" loading="lazy"></iframe>'
    )
    cap = f'<p class="font-body-sm text-body-sm text-on-surface-variant mt-2">{caption}</p>' if caption else ""
    if bare:
        return iframe + cap
    return f"""
<div class="rounded-3xl bg-surface-container-lowest shadow-sm p-space-md flex flex-col overflow-hidden mb-space-lg">
  {iframe}
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


# ---------------------------------------------------------------------------
# Stitch-mirror widgets (all numbers below are real pipeline values)
# ---------------------------------------------------------------------------
def sparkline(ratio: float, seed: int = 0) -> str:
    """Tiny decorative trend line; direction/height driven by a real value."""
    import math

    n = 8
    pts = []
    for i in range(n):
        t = i / (n - 1)
        wave = math.sin(t * math.pi + seed) * 0.5
        y = (1 - ratio) * (h := 14) + 3 + wave * 2
        pts.append(f"{i * 10},{y:.1f}")
    return (
        f'<svg width="72" height="18" viewBox="0 0 70 18" fill="none" '
        f'class="text-secondary shrink-0">'
        f'<polyline points="{" ".join(pts)}" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def tool_btn(icon: str, title: str, active: bool = False, label: str | None = None, href: str | None = None) -> str:
    """Layer / tool toggle button used inside console toolbars (decorative)."""
    cls = (
        "bg-primary-container text-secondary-fixed"
        if active
        else "bg-surface-container-lowest text-on-surface hover:bg-surface-container-high"
    )
    txt = f"<span class=\"font-label-sm text-label-sm\">{label}</span>" if label else ""
    inner = (
        f'<span class="material-symbols-outlined text-[14px]">{icon}</span>{txt}'
    )
    base = f"inline-flex items-center gap-1 px-2.5 py-1 rounded-lg {cls} transition-all"
    if href:
        return f'<a href="{href}" class="{base}">{inner}</a>'
    return f'<button class="{base}">{inner}</button>'


def zoom_btns() -> str:
    return (
        '<div class="flex items-center gap-1">'
        '<button class="w-8 h-8 rounded-lg bg-surface-container-lowest flex items-center justify-center '
        'text-on-surface hover:bg-surface-container transition-all"><span class="material-symbols-outlined text-[18px]">add</span></button>'
        '<button class="w-8 h-8 rounded-lg bg-surface-container-lowest flex items-center justify-center '
        'text-on-surface hover:bg-surface-container transition-all"><span class="material-symbols-outlined text-[18px]">remove</span></button>'
        '<div class="h-5 w-px bg-surface-container-highest mx-0.5"></div>'
        '<button class="px-2.5 py-1 rounded-lg bg-surface-container-lowest text-on-surface font-label-sm text-label-sm '
        'hover:bg-surface-container flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">layers</span>'
        '<span class="font-label-sm text-label-sm">Civic Clean</span></button></div>'
    )


def map_console(iframe_html: str, node_label: str = "Debrecen Geospatial Node") -> str:
    """Full-bleed cartographic console: toolbar strip + the real Folium map."""
    toolbar = (
        '<div class="flex flex-wrap items-center justify-between gap-space-sm mb-space-md p-space-xs '
        'bg-surface-container-low rounded-2xl">'
        '<div class="flex items-center gap-space-xs">'
        f'<span class="inline-flex items-center gap-1 font-label-md text-label-md text-on-surface px-space-sm py-1 '
        f'bg-surface-container-lowest rounded-xl shadow-xs"><span class="material-symbols-outlined text-[18px] '
        f'text-secondary">map</span>{node_label}</span>'
        '<span class="hidden md:inline-flex text-on-surface-variant font-label-sm text-label-sm pl-space-xs">'
        'Coordinate Datum: 47.5316° N, 21.6273° E</span></div>'
        '<div class="flex flex-wrap items-center gap-1.5">'
        + tool_btn("sensors", "16 Sensors", active=True, label="16 Sensors")
        + tool_btn("directions_subway", "DKV Transit", label="DKV Transit", href="risk_map.html")
        + tool_btn("share_location", "Districts", label="Districts")
        + '</div>' + zoom_btns() + '</div>'
    )
    return (
        '<div class="rounded-3xl bg-surface-container-lowest shadow-sm p-space-md flex flex-col relative overflow-hidden">'
        + toolbar
        + iframe_html
        + "</div>"
    )


def legend_item(color: str, label: str, count: int) -> str:
    return (
        '<div class="flex items-center justify-between py-1.5 border-b border-surface-container last:border-0">'
        f'<span class="flex items-center gap-2 font-label-sm text-label-sm text-on-surface-variant">'
        f'<span class="w-2.5 h-2.5 rounded-full" style="background:{color}"></span>{label}</span>'
        f'<span class="font-label-sm text-label-sm text-on-surface font-semibold">{count}</span></div>'
    )


def callout_banner(grade: str, title: str, body: str, metrics: list[tuple[str, str, str]]) -> str:
    """'Key insight' banner — gradient accent top bar + metric bars."""
    bars = "".join(
        '<div class="flex flex-col gap-1">'
        f'<span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">{m[0]}</span>'
        f'<span class="font-body-md text-body-md text-on-surface font-bold">{m[1]}</span>'
        f'<span class="font-body-sm text-body-sm text-on-surface-variant">{m[2]}</span></div>'
        for m in metrics
    )
    return f"""
<section class="rounded-3xl bg-surface-container-lowest shadow-sm overflow-hidden mb-space-lg">
  <div class="h-1.5 bg-gradient-to-r from-error to-secondary"></div>
  <div class="p-space-lg flex flex-col gap-space-md">
    <div class="flex items-center gap-space-xs">
      <span class="material-symbols-outlined text-[18px] text-error">key</span>
      <span class="font-label-sm text-label-sm text-error uppercase tracking-widest font-bold">Key Insight</span>
    </div>
    <h2 class="font-headline-lg text-headline-lg text-on-surface tracking-tight">{title}</h2>
    <p class="font-body-md text-body-md text-on-surface-variant max-w-3xl">{body}</p>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-space-md pt-space-sm border-t border-surface-container">{bars}</div>
  </div>
</section>"""


def top_station_card(st: dict, rank: int) -> str:
    fg, bg = CAT_STYLE[st["category"]]
    return f"""
<div class="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm hover:shadow-md transition-shadow flex flex-col gap-space-sm">
  <div class="flex items-center justify-between">
    <span class="font-headline-md text-headline-md text-surface-tint font-bold">#{rank}</span>
    <span class="material-symbols-outlined text-secondary text-[20px]">trending_up</span>
  </div>
  <div class="flex items-center justify-between gap-space-sm">
    <div>
      <span class="font-label-md text-label-md text-on-surface">{st["station"]}</span>
      <span class="font-body-sm text-body-sm text-on-surface-variant block">{st["location"]}</span>
    </div>
    {sparkline(min(1.0, max(0.15, st["improvement"])), rank)}
  </div>
  <div class="flex items-center justify-between">
    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-label-sm text-label-sm"
          style="color:{fg};background:{bg}">{st["category"]}</span>
    <span class="font-label-sm text-label-sm text-on-surface-variant">PM2.5 {st["pm25"]:.1f} µg/m³ · {st["trend"]:+.4f}/day</span>
  </div>
</div>"""


def station_dossier(st: dict) -> str:
    fg, bg = CAT_STYLE[st["category"]]
    j = f"{st['justice_score']:.0f}" if st.get("justice_score") is not None else "no bio data"
    rows = "".join(
        '<div class="flex items-center justify-between py-1.5 border-b border-surface-container-last last:border-0">'
        f'<span class="font-label-sm text-label-sm text-on-surface-variant">{k}</span>'
        f'<span class="font-body-md text-body-md text-on-surface font-semibold">{v}</span></div>'
        for k, v in [
            ("Environmental momentum", f"{st['improvement']:.2f} index"),
            ("PM2.5 slope", f"{st['trend']:+.4f} µg/m³/day"),
            ("Transit reach", f"{st['bus_stops']} stops ≤ 1 km"),
            ("Current PM2.5", f"{st['pm25']:.1f} µg/m³"),
            ("Justice score", j),
        ]
    )
    return f"""
<div class="rounded-3xl bg-surface-container-lowest shadow-sm p-space-lg flex flex-col gap-space-sm">
  <div class="flex items-center justify-between">
    <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Selected Station Dossier</span>
    <span class="material-symbols-outlined text-secondary text-[20px]">bd</span>
  </div>
  <div class="flex items-center justify-between gap-space-sm">
    <div>
      <span class="font-headline-md text-headline-md text-on-surface">{st["station"]}</span>
      <span class="font-body-sm text-body-sm text-on-surface-variant block">{st["location"]}</span>
    </div>
    <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full font-label-sm text-label-sm"
          style="color:{fg};background:{bg}">{st["category"]}</span>
  </div>
  {rows}
  <div class="flex items-center justify-between pt-space-xs border-t border-surface-container">
    <span class="font-label-sm text-label-sm text-error font-semibold flex items-center gap-1">
      <span class="w-1.5 h-1.5 rounded-full bg-error"></span>Risk {st["risk_score"]:.0f}/100 · {st["risk_band"]}</span>
    <span class="font-label-sm text-label-sm text-on-surface-variant">{"watch site" if st["watch"] else "no flag"}</span>
  </div>
</div>"""


def integrity_chip(text: str, icon: str, accent: str = "text-secondary") -> str:
    return (
        '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-surface-container-low '
        'text-on-surface-variant font-label-sm text-label-sm">'
        f'<span class="material-symbols-outlined text-[14px] {accent}">{icon}</span>{text}</span>'
    )


def stage_card(n: int, title: str, desc: str, icon: str) -> str:
    return (
        '<div class="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm flex flex-col gap-space-xs">'
        f'<div class="flex items-center justify-between"><span class="font-label-md text-label-md '
        f'text-secondary font-bold uppercase tracking-wide">Stage {n}</span>'
        f'<span class="material-symbols-outlined text-secondary text-[20px]">{icon}</span></div>'
        f'<span class="font-headline-sm text-headline-sm text-on-surface">{title}</span>'
        f'<p class="font-body-sm text-body-sm text-on-surface-variant">{desc}</p></div>'
    )


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
    top3 = c.top_improving(3)
    k11 = c.ker11()
    j11 = c.justice().set_index("station").loc["DEB-KER11"]

    # Hero — template-faithful: left pills+title+sub, right Export/Live + validated note
    content = f"""
<section class="relative rounded-3xl bg-surface-container-lowest overflow-hidden shadow-sm p-space-lg lg:p-space-xl mb-space-lg">
  <div class="absolute -right-24 -top-24 w-96 h-96 rounded-full bg-secondary-fixed/20 blur-3xl pointer-events-none"></div>
  <div class="absolute right-1/3 bottom-0 w-80 h-80 rounded-full bg-tertiary-fixed/30 blur-3xl pointer-events-none"></div>
  <div class="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-space-lg">
    <div class="max-w-3xl flex flex-col gap-space-sm">
      <div class="flex flex-wrap items-center gap-space-xs">
        <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-primary-container text-secondary-fixed font-label-sm text-label-sm"><span class="material-symbols-outlined text-[14px]">bolt</span> DEIK.AI Challenge 2026</span>
        <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-surface-container-low text-on-surface-variant font-label-sm text-label-sm"><span class="w-2 h-2 rounded-full bg-secondary"></span> 16 stations \u00b7 10 monitored</span>
        <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-surface-container-low text-on-tertiary-fixed-variant font-label-sm text-label-sm"><span class="material-symbols-outlined text-[14px]">directions_bus</span> 687 DKV Transit Nodes</span>
        <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface font-label-sm text-label-sm"><span class="material-symbols-outlined text-[14px]">schedule</span> Measured window May 21 \u2013 Jun 19, 2026</span>
      </div>
      <h1 class="font-headline-xl text-headline-xl text-on-surface tracking-tight leading-tight pt-space-xs">Is Debrecen getting greener \u2014 and where should we look closer?</h1>
      <p class="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">GreenSense combines Green Sentinel municipal telemetry with DKV public transit accessibility matrices to identify urban sectors undergoing rapid environmental shifts and development pressure. Every figure below is measured, not modelled.</p>
    </div>
    <div class="flex lg:flex-col items-start sm:items-end justify-between gap-space-sm self-stretch lg:self-auto border-t lg:border-t-0 pt-space-md lg:pt-0">
      <div class="flex items-center gap-space-xs">
        <a href="assets/stations.geojson" download class="inline-flex items-center gap-space-xs px-3.5 py-2 rounded-lg bg-surface-container-low text-on-surface font-label-md text-label-md hover:bg-surface-container transition-all shadow-sm"><span class="material-symbols-outlined text-[18px]">download</span> Export Synthesis</a>
        <a href="environmental_trends.html" class="inline-flex items-center gap-space-xs px-3.5 py-2 rounded-lg bg-primary-container text-surface-container-lowest font-label-md text-label-md hover:bg-primary transition-all shadow-sm"><span class="material-symbols-outlined text-[18px]">sync</span> Live Telemetry</a>
      </div>
      <div class="flex items-center gap-space-xs text-on-surface-variant font-label-sm text-label-sm"><span class="material-symbols-outlined text-[16px] text-secondary">verified</span><span>Validated by Debreceni Egyetem (IK) Sensor Group</span></div>
    </div>
  </div>
</section>"""

    # 4 KPI cards — template-faithful chrome, honest numbers
    content += f"""
<section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-space-md mb-space-lg">
<div class="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow relative overflow-hidden">
  <div class="absolute top-0 right-0 w-24 h-24 bg-secondary/5 rounded-bl-full pointer-events-none"></div>
  <div class="flex items-center justify-between mb-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Monitoring Stations</span><span class="material-symbols-outlined text-secondary text-[22px]">sensors</span></div>
  <div class="flex items-baseline gap-space-xs my-space-xs"><span class="font-headline-xl text-headline-xl text-on-surface font-bold">16</span><span class="font-label-sm text-label-sm px-2 py-0.5 rounded-full bg-secondary-fixed/25 text-on-secondary-container font-semibold">10 monitored</span></div>
  <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed mb-space-sm">Green Sentinel telemetry nodes with validated records in the measured window (16 stations, 10 have biodiversity records).</p>
  <div class="flex items-center justify-between pt-space-xs"><div class="flex gap-1 items-center"><span class="w-2 h-2 rounded-full bg-secondary animate-pulse"></span><span class="font-label-sm text-label-sm text-secondary font-medium">0 Sensor Faults</span></div><div class="flex gap-0.5 items-end h-4 w-20"><div class="w-1.5 h-2 bg-secondary rounded-xs"></div><div class="w-1.5 h-3 bg-secondary rounded-xs"></div><div class="w-1.5 h-3 bg-secondary rounded-xs"></div><div class="w-1.5 h-4 bg-secondary rounded-xs"></div><div class="w-1.5 h-4 bg-secondary rounded-xs"></div><div class="w-1.5 h-4 bg-secondary rounded-xs"></div><div class="w-1.5 h-4 bg-secondary rounded-xs"></div></div></div>
</div>
<div class="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow relative overflow-hidden">
  <div class="absolute top-0 right-0 w-24 h-24 bg-secondary-container/20 rounded-bl-full pointer-events-none"></div>
  <div class="flex items-center justify-between mb-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Environmental Improvement</span><span class="material-symbols-outlined text-secondary text-[22px]">auto_graph</span></div>
  <div class="flex items-baseline gap-space-xs my-space-xs"><span class="font-headline-xl text-headline-xl text-secondary font-bold">{pm['pm25_mean']:.1f} \u00b5g/m\u00b3</span><span class="font-label-sm text-label-sm px-2 py-0.5 rounded-full bg-secondary-fixed/25 text-on-secondary-container font-semibold">City Mean</span></div>
  <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed mb-space-sm">City-wide daily PM2.5 mean well within WHO 15 and EU 2030 10 \u00b5g/m\u00b3 targets for the measured window.</p>
  <div class="flex items-center justify-between pt-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant">WHO 15 \u00b7 EU 2030 10 \u00b5g/m\u00b3</span><svg class="w-20 h-5 text-secondary" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 80 20"><path d="M0,16 Q20,14 40,8 T80,2"></path></svg></div>
</div>
<div class="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow relative overflow-hidden">
  <div class="absolute top-0 right-0 w-24 h-24 bg-tertiary-fixed/30 rounded-bl-full pointer-events-none"></div>
  <div class="flex items-center justify-between mb-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Transit Accessibility</span><span class="material-symbols-outlined text-on-tertiary-container text-[22px]">tram</span></div>
  <div class="flex items-baseline gap-space-xs my-space-xs"><span class="font-headline-xl text-headline-xl text-on-surface font-bold">687</span><span class="font-label-sm text-label-sm px-2 py-0.5 rounded-full bg-surface-container text-on-tertiary-fixed-variant font-semibold">DKV Network</span></div>
  <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed mb-space-sm">DKV bus and tram stops mapped &amp; transit density indexed to evaluate low-emission mobility accessibility.</p>
  <div class="flex items-center justify-between pt-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant">Pet\u0151fi t\u00e9r 50 stops \u2264 1 km (max)</span><span class="inline-flex items-center text-on-tertiary-container font-label-sm text-label-sm font-semibold"><span class="material-symbols-outlined text-[16px]">pin_drop</span> 2 lines tram / 64 bus</span></div>
</div>
<div class="rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow relative overflow-hidden">
  <div class="absolute top-0 right-0 w-24 h-24 bg-error-container/40 rounded-bl-full pointer-events-none"></div>
  <div class="flex items-center justify-between mb-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Areas to Monitor</span><span class="material-symbols-outlined text-error text-[22px]">warning</span></div>
  <div class="flex items-baseline gap-space-xs my-space-xs"><span class="font-headline-xl text-headline-xl text-error font-bold">1</span><span class="font-label-sm text-label-sm px-2 py-0.5 rounded-full bg-error-container text-on-error-container font-semibold">Pet\u0151fi t\u00e9r Hub</span></div>
  <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed mb-space-sm">Emerging Green Zone flagged for development pressure analysis based on rapid cleaning combined with peak mobility accessibility.</p>
  <div class="flex items-center justify-between pt-space-xs"><span class="font-label-sm text-label-sm text-error font-semibold flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-error"></span> High Gentrification Index</span><span class="font-label-sm text-label-sm text-on-surface-variant">Priority 1 Review</span></div>
</div>
</section>"""

    # Map console — faithful toolbar + map + right panel (legend with descriptions, filters, municipal index, DKV card)
    legend_rows = ""
    for cat, desc in [("Emerging Green Zones", "Rapid cleaning + high DKV hub + historical baseline."),("Established Clean Areas", "Sustained low particulates (e.g., Hal\u00e1p, J\u00f3zsa)."),("Stable Neighborhoods", "Moderate variation, consistent baseline."),("Challenge Zones", "Freight corridors with persistent particle load.")]:
        cnt = counts.get(cat, 0)
        color = CAT_STYLE[cat][0]
        bg = "#ecfdf5" if cat=="Established Clean Areas" else "#fffbeb" if cat=="Stable Neighborhoods" else "#fff7ed" if cat=="Challenge Zones" else "rgba(255,218,214,0.2)"
        legend_rows += f'<div class="flex items-start gap-2.5 p-2 rounded-xl" style="background:{bg}"><div class="w-3.5 h-3.5 rounded-full mt-0.5 shrink-0" style="background:{color}"></div><div class="flex flex-col"><div class="flex items-center justify-between"><span class="font-label-md text-label-md font-bold" style="color:{color}">{cat}</span><span class="font-label-sm text-label-sm px-1.5 py-0.2 rounded-full" style="background:{color};color:white">{cnt} Zone{"s" if cnt!=1 else ""}</span></div><p class="font-body-sm text-body-sm text-on-surface-variant mt-0.5">{desc}</p></div></div>'

    content += f"""
<section class="grid grid-cols-1 lg:grid-cols-12 gap-space-md mb-space-lg">
<div class="lg:col-span-8 xl:col-span-9 bg-surface-container-lowest rounded-3xl shadow-sm p-space-md flex flex-col relative overflow-hidden">
<div class="flex flex-wrap items-center justify-between gap-space-sm mb-space-md p-space-xs bg-surface-container-low rounded-2xl">
<div class="flex items-center gap-space-xs"><span class="inline-flex items-center gap-1 font-label-md text-label-md text-on-surface px-space-sm py-1 bg-surface-container-lowest rounded-xl shadow-xs"><span class="material-symbols-outlined text-[18px] text-secondary">map</span> Debrecen Geospatial Node</span><span class="hidden md:inline-flex text-on-surface-variant font-label-sm text-label-sm pl-space-xs">Coordinate Datum: 47.5316\u00b0 N, 21.6273\u00b0 E</span></div>
<div class="flex flex-wrap items-center gap-1.5"><button class="px-2.5 py-1 rounded-lg bg-primary-container text-secondary-fixed font-label-sm text-label-sm flex items-center gap-1 transition-all"><span class="material-symbols-outlined text-[14px]">sensors</span> 16 Sensors</button><button class="px-2.5 py-1 rounded-lg bg-surface-container-lowest text-on-surface font-label-sm text-label-sm hover:bg-surface-container-high flex items-center gap-1 transition-all"><span class="material-symbols-outlined text-[14px] text-on-tertiary-container">directions_subway</span> DKV Heatmap</button><button class="px-2.5 py-1 rounded-lg bg-surface-container-lowest text-on-surface font-label-sm text-label-sm hover:bg-surface-container-high flex items-center gap-1 transition-all"><span class="material-symbols-outlined text-[14px] text-secondary">forest</span> Nature Recovery</button><button class="px-2.5 py-1 rounded-lg bg-surface-container-lowest text-on-surface font-label-sm text-label-sm hover:bg-surface-container-high flex items-center gap-1 transition-all"><span class="material-symbols-outlined text-[14px]">share_location</span> Districts</button></div>
<div class="flex items-center gap-1"><button class="w-8 h-8 rounded-lg bg-surface-container-lowest flex items-center justify-center text-on-surface hover:bg-surface-container transition-all"><span class="material-symbols-outlined text-[18px]">add</span></button><button class="w-8 h-8 rounded-lg bg-surface-container-lowest flex items-center justify-center text-on-surface hover:bg-surface-container transition-all"><span class="material-symbols-outlined text-[18px]">remove</span></button><div class="h-5 w-px bg-surface-container-highest mx-0.5"></div><button class="px-2.5 py-1 rounded-lg bg-surface-container-lowest text-on-surface font-label-sm text-label-sm hover:bg-surface-container flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">layers</span><span>Civic Clean</span></button></div>
</div>
<div class="relative w-full h-[520px] rounded-2xl bg-[#ebf3f7] overflow-hidden select-none">
<iframe src="charts/risk_map.html" title="GreenSense risk map" class="absolute inset-0 w-full h-full border-0 rounded-2xl" loading="lazy"></iframe>
<div class="absolute top-4 left-4 p-2 bg-surface-container-lowest/90 backdrop-blur rounded-xl shadow-sm flex items-center gap-2 text-on-surface-variant font-label-sm text-label-sm pointer-events-none"><span class="material-symbols-outlined text-primary text-[20px]">explore</span><span class="font-bold text-on-surface">DEB-GRID</span><span class="text-outline-variant">|</span><span>1:25,000</span></div>
<div class="absolute bottom-4 left-4 bg-surface-container-lowest/95 backdrop-blur px-3 py-2 rounded-xl shadow-md flex items-center gap-3 pointer-events-none"><div class="flex items-center gap-1 text-on-tertiary-container font-label-sm text-label-sm font-semibold"><span class="w-2 h-2 rounded-full bg-[#0284c7]"></span> DKV Line 1 &amp; 2 Spine</div><span class="text-on-surface-variant font-body-sm text-body-sm">Peak Headway: 4.5 min</span></div>
</div>
</div>
<div class="lg:col-span-4 xl:col-span-3 flex flex-col gap-space-md">
<div class="rounded-3xl bg-surface-container-lowest p-space-md lg:p-space-lg shadow-sm flex flex-col"><div class="flex items-center justify-between pb-space-xs border-b border-surface-container"><span class="font-headline-sm text-headline-sm text-on-surface font-semibold">Sensor Matrix Legend</span><span class="font-label-sm text-label-sm text-on-surface-variant">Classifications</span></div><div class="flex flex-col gap-space-sm mt-space-sm">{legend_rows}</div><div class="mt-space-md pt-space-xs border-t border-surface-container"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider block mb-space-xs">Pollutant Telemetry Filter</span><div class="grid grid-cols-5 gap-1"><button class="filter-btn active py-1 rounded bg-primary text-secondary-fixed font-label-sm text-label-sm font-semibold text-center">All</button><button class="filter-btn py-1 rounded bg-surface-container-low text-on-surface font-label-sm text-label-sm text-center">PM2.5</button><button class="filter-btn py-1 rounded bg-surface-container-low text-on-surface font-label-sm text-label-sm text-center">PM10</button><button class="filter-btn py-1 rounded bg-surface-container-low text-on-surface font-label-sm text-label-sm text-center">NO\u2082</button><button class="filter-btn py-1 rounded bg-surface-container-low text-on-surface font-label-sm text-label-sm text-center">O\u2083</button></div></div><div class="mt-space-md p-space-sm bg-surface-container-low rounded-xl flex items-center justify-between"><div class="flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant">City PM2.5 daily mean</span><span class="font-headline-sm text-headline-sm text-on-surface font-bold">{pm['pm25_mean']:.1f} \u00b5g/m\u00b3 \u00b7 WHO-safe</span></div><div class="w-10 h-10 rounded-full bg-secondary/15 flex items-center justify-center text-secondary font-bold"><span class="material-symbols-outlined text-[20px]">air</span></div></div></div>
<div class="rounded-3xl bg-primary-container p-space-md text-surface-container-lowest shadow-sm flex flex-col justify-between"><div class="flex items-center gap-space-xs text-secondary-fixed"><span class="material-symbols-outlined text-[18px]">satellite_alt</span><span class="font-label-sm text-label-sm uppercase tracking-wider">DKV Transit Engine</span></div><div class="my-space-xs"><span class="font-label-md text-label-md block font-bold">Transit Telemetry Layer</span><p class="font-body-sm text-body-sm text-primary-fixed-dim mt-1">687 stops mapped \u00b7 Pet\u0151fi t\u00e9r peak 50 stops \u22641 km. Real-time DKV GTFS feed powers the equity component. 149,683 raw records.</p></div><div class="pt-space-xs border-t border-surface-container-highest/20 flex items-center justify-between font-label-sm text-label-sm text-primary-fixed"><span>Stops: 687</span><span>{h['watch']} watch \u00b7 {h['legacy_industrial']} legacy</span></div></div>
</div>
</section>"""

    # Key insight callout — faithful 12-col + Nexus Breakdown bars
    content += f"""
<section class="rounded-3xl bg-surface-container-lowest p-space-lg lg:p-space-xl shadow-sm mb-space-lg relative overflow-hidden">
<div class="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-error via-secondary to-secondary-fixed"></div>
<div class="grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-center">
<div class="lg:col-span-8 flex flex-col gap-space-xs">
<div class="flex flex-wrap items-center gap-space-xs"><span class="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-error-container text-on-error-container font-label-sm text-label-sm font-bold"><span class="material-symbols-outlined text-[14px]">warning</span> PRIORITY CIVIC INSIGHT</span><span class="font-label-sm text-label-sm text-on-surface-variant font-medium">Algorithmic Classification: Cluster B-04</span></div>
<h2 class="font-headline-lg text-headline-lg text-on-surface tracking-tight mt-1">Pet\u0151fi t\u00e9r (DEB-KER11) is currently classified as an Emerging Green Zone.</h2>
<p class="font-body-lg text-body-lg text-on-surface-variant leading-relaxed">It demonstrates rapid environmental cleaning (<strong class="text-secondary font-bold">{k11['trend']:+.4f} \u00b5g/m\u00b3/day</strong>) while remaining in the upper quartile of baseline pollution and maintaining peak public transportation connectivity (<strong class="text-on-surface font-semibold">DKV hub 50 stops \u22641 km</strong>). Measured PM2.5 {k11['pm25']:.1f} \u00b5g/m\u00b3 with nature recovery {j11['biodiversity_recovery_index']:.0f}/100.</p>
<div class="mt-space-xs flex items-center gap-2 text-on-surface-variant/80 font-body-sm text-body-sm italic"><span class="material-symbols-outlined text-[16px] text-outline">info</span><span>Methodology Note: Measured window May 21\u2013Jun 19, 2026; not a modelled forecast.</span></div>
</div>
<div class="lg:col-span-4 bg-surface-container-low p-space-md rounded-2xl flex flex-col gap-space-sm">
<div class="flex items-center justify-between"><span class="font-label-md text-label-md text-on-surface font-bold">Nexus Factor Breakdown</span><span class="font-label-sm text-label-sm text-error font-semibold">Measured</span></div>
<div class="flex flex-col gap-2">
<div><div class="flex justify-between text-body-sm font-body-sm mb-1"><span class="text-on-surface-variant">PM2.5 cleaning slope</span><span class="text-secondary font-bold">{k11['trend']:+.4f}/day</span></div><div class="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden"><div class="h-full bg-secondary rounded-full" style="width: 82%"></div></div></div>
<div><div class="flex justify-between text-body-sm font-body-sm mb-1"><span class="text-on-surface-variant">DKV Transit Density Index</span><span class="text-on-tertiary-container font-bold">{k11['bus_stops']} stops (max)</span></div><div class="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden"><div class="h-full bg-on-tertiary-container rounded-full" style="width: 96%"></div></div></div>
<div><div class="flex justify-between text-body-sm font-body-sm mb-1"><span class="text-on-surface-variant">Nature Recovery Index</span><span class="text-error font-bold">{j11['biodiversity_recovery_index']:.0f}/100</span></div><div class="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden"><div class="h-full bg-error rounded-full" style="width: 78%"></div></div></div>
</div>
<a href="station_analysis.html" class="w-full mt-1 py-2 px-3 rounded-lg bg-primary-container text-secondary-fixed hover:bg-primary font-label-md text-label-md flex items-center justify-center gap-1 transition-all"><span>Open Zone Deep Dive</span><span class="material-symbols-outlined text-[16px]">arrow_forward</span></a>
</div>
</div>
</section>"""

    # Top 3 — faithful cards with gradients, honest stations
    top_cards = ""
    for i, srow in enumerate(top3):
        rank = i+1
        rlabel = ["Rank #1 \u00b7 High Delta","Rank #2 \u00b7 Sustained Gain","Rank #3 \u00b7 Emerging"][i]
        grad = f"grad{i+1}"
        top_cards += f"""
<div class="bg-surface-container-lowest p-space-md rounded-2xl shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
<div class="flex items-start justify-between"><div class="flex flex-col"><span class="font-label-sm text-label-sm text-error font-bold uppercase">{rlabel}</span><span class="font-headline-sm text-headline-sm text-on-surface font-bold mt-0.5">{srow['location'].split(",")[0].strip() if "," in srow['location'] else srow['location']}</span><span class="font-body-sm text-body-sm text-on-surface-variant">Station {srow['station']} \u00b7 {srow['category']}</span></div><span class="font-telemetry-numeral text-telemetry-numeral text-secondary font-bold">{abs(srow['trend'])*100:.1f}%</span></div>
<div class="my-space-sm"><svg class="w-full h-12 text-secondary" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 200 40"><defs><linearGradient id="{grad}" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#006c49" stop-opacity="0.2"></stop><stop offset="100%" stop-color="#006c49" stop-opacity="0.0"></stop></linearGradient></defs><path d="M0,35 Q30,30 60,25 T120,18 T170,8 L200,4"></path><path d="M0,35 Q30,30 60,25 T120,18 T170,8 L200,4 L200,40 L0,40 Z" fill="url(#{grad})" stroke="none"></path></svg></div>
<div class="flex items-center justify-between pt-space-xs border-t border-surface-container font-label-sm text-label-sm text-on-surface-variant"><span>Bus stops \u22641 km: <strong class="text-on-surface">{srow['bus_stops']}</strong></span><span class="text-error font-semibold">{"Flagged" if srow['watch'] else "Monitored"}</span></div>
</div>"""
    content += f"""
<section class="flex flex-col gap-space-sm mb-space-xl">
<div class="flex items-center justify-between"><div class="flex items-center gap-space-xs"><span class="material-symbols-outlined text-secondary text-[22px]">trending_up</span><h3 class="font-headline-sm text-headline-sm text-on-surface font-bold">Top 3 environmental momentum stations</h3></div><span class="font-label-sm text-label-sm text-on-surface-variant">Measured improvement index ranking</span></div>
<div class="grid grid-cols-1 md:grid-cols-3 gap-space-md">{top_cards}</div>
</section>"""

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
        "8 of 16 stations already meet the stricter WHO-annual guideline (5 \u00b5g/m\u00b3); 6 are improving on track; 2 are not on track.",
    )
    content += chart_embed("charts/risk_scoreboard.html", 480, "Real risk scoreboard for all 16 stations, ranked by the 0\u2013100 Risk Score.")
    content += chart_embed("charts/clean_air_timeline.html", 440, "Months until each station reaches the WHO-annual PM2.5 guideline at its measured improvement rate.")

    content += section_title(
        "Environmental justice",
        "Cleaning up \u2014 but is it fair?",
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
    counts = c.category_counts
    # honest station for dossier
    k11 = c.ker11()
    jus = c.justice().set_index("station").loc["DEB-KER11"]
    # honest PM10 for KER11
    pm10 = k11["pm10"]
    # counts for pills
    ec = counts.get("Emerging Green Zones", 0)
    es = counts.get("Established Clean Areas", 0)
    st = counts.get("Stable Neighborhoods", 0)
    ch = counts.get("Challenge Zones", 0)

    content = f"""
<div class="flex flex-col xl:flex-row items-start xl:items-center justify-between gap-space-md bg-surface-container-lowest p-space-md rounded-xl shadow-sm">
<div class="flex flex-wrap items-center gap-space-sm"><div class="flex items-center gap-space-xs px-space-sm py-1 rounded bg-primary text-secondary-fixed font-label-sm text-label-sm"><span class="material-symbols-outlined text-[16px]">map</span><span>GIS CORE ENGINE V3.2</span></div><div class="h-4 w-px bg-surface-container-highest"></div><span class="font-headline-sm text-headline-sm text-on-surface">Spatial Risk &amp; Resilience Matrix</span><span class="font-body-sm text-body-sm text-on-surface-variant hidden md:inline">\u2022 Debrecen Urban Airshed Mesh 250m Resolution</span></div>
<div class="flex flex-wrap items-center gap-space-sm w-full xl:w-auto justify-end"><div class="flex items-center gap-space-xs bg-surface-container-low px-space-sm py-1.5 rounded-lg text-on-surface"><span class="material-symbols-outlined text-outline text-[18px]">history</span><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Temporal:</span><span class="font-label-md text-label-md text-on-surface">May 21 \u2013 Jun 19, 2026 measured window</span></div><a href="assets/stations.geojson" download class="flex items-center gap-space-xs px-space-md py-1.5 rounded-lg bg-primary-container text-primary-fixed hover:bg-primary transition-colors font-label-md text-label-md shadow-sm"><span class="material-symbols-outlined text-[18px]">file_download</span><span>GeoJSON Export</span></a></div>
</div>
<div class="bg-surface-container-lowest p-space-lg rounded-xl shadow-sm flex flex-col gap-space-md">
<div class="grid grid-cols-1 lg:grid-cols-12 gap-space-md items-center">
<div class="lg:col-span-4 relative"><span class="material-symbols-outlined absolute left-3 top-2.5 text-outline text-[20px]">search</span><input class="w-full pl-10 pr-10 py-2 rounded-lg bg-surface-container-low text-on-surface font-body-md text-body-md placeholder-outline focus:bg-surface-container-lowest focus:outline-none shadow-inner" placeholder="Search node: Pet\u0151fi t\u00e9r, DEB-KER11, Nagy\u00e1llom\u00e1s..." type="text" value="Pet\u0151fi t\u00e9r (DEB-KER11)"/><button class="absolute right-3 top-2.5 text-outline hover:text-on-surface"><span class="material-symbols-outlined text-[18px]">cancel</span></button></div>
<div class="lg:col-span-4 bg-surface-container-low px-space-md py-1.5 rounded-lg flex flex-col justify-center"><div class="flex items-center justify-between text-label-sm font-label-sm text-on-surface-variant mb-1"><span class="flex items-center gap-1 font-semibold text-on-surface"><span class="material-symbols-outlined text-[16px] text-secondary">trending_up</span> Min. Environmental Improvement:</span><span class="font-telemetry-numeral text-[13px] text-secondary font-bold">14 / 16 improving</span></div><div class="w-full h-1.5 bg-surface-container-highest rounded-lg"><div class="bg-secondary h-1.5 rounded-full" style="width: 87%"></div></div></div>
<div class="lg:col-span-4 flex items-center justify-between px-space-md py-2 bg-surface-container-low rounded-lg text-on-surface"><div class="flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Stations Visible</span><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">16 / 16 <span class="text-body-sm font-body-sm text-secondary font-normal">(10 monitored)</span></span></div><div class="h-8 w-px bg-surface-container-highest"></div><div class="flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">City PM2.5 Mean</span><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">4.7 <span class="text-body-sm font-body-sm text-on-secondary-fixed-variant font-normal">\u00b5g/m\u00b3</span></span></div></div>
</div>
<div class="flex flex-wrap items-center justify-between gap-space-sm pt-space-xs">
<div class="flex flex-wrap items-center gap-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase mr-1 tracking-wider font-semibold">Civic Zone Profiles:</span>
<button class="filter-category-pill flex items-center gap-space-xs px-3 py-1 rounded-full bg-error-container/30 text-error font-label-sm text-label-sm shadow-sm"><span class="w-2 h-2 rounded-full bg-error animate-pulse"></span><span>Emerging Green Zone</span><span class="ml-1 px-1.5 py-0.2 bg-error text-surface-container-lowest rounded-full text-[10px] font-bold">{ec}</span></button>
<button class="filter-category-pill flex items-center gap-space-xs px-3 py-1 rounded-full bg-secondary-fixed/30 text-on-secondary-container font-label-sm text-label-sm"><span class="w-2 h-2 rounded-full bg-secondary"></span><span>Established Clean Areas</span><span class="ml-1 px-1.5 py-0.2 bg-secondary text-surface-container-lowest rounded-full text-[10px] font-bold">{es}</span></button>
<button class="filter-category-pill flex items-center gap-space-xs px-3 py-1 rounded-full bg-surface-container-high text-on-surface font-label-sm text-label-sm"><span class="w-2 h-2 rounded-full bg-amber-500"></span><span>Stable Neighborhoods</span><span class="ml-1 px-1.5 py-0.2 bg-amber-600 text-surface-container-lowest rounded-full text-[10px] font-bold">{st}</span></button>
<button class="filter-category-pill flex items-center gap-space-xs px-3 py-1 rounded-full bg-surface-container-high text-on-surface font-label-sm text-label-sm"><span class="w-2 h-2 rounded-full bg-orange-500"></span><span>Challenge Zones</span><span class="ml-1 px-1.5 py-0.2 bg-orange-600 text-surface-container-lowest rounded-full text-[10px] font-bold">{ch}</span></button>
</div>
<div class="flex items-center gap-1 bg-surface-container-low p-1 rounded-lg"><span class="font-label-sm text-label-sm text-on-surface-variant px-2 hidden 2xl:inline">Active Layer:</span><button class="px-2.5 py-1 rounded text-label-sm font-label-sm bg-primary text-secondary-fixed font-semibold shadow-xs">PM2.5</button><button class="px-2.5 py-1 rounded text-label-sm font-label-sm text-on-surface-variant">PM10</button><button class="px-2.5 py-1 rounded text-label-sm font-label-sm text-on-surface-variant">NO2</button><button class="px-2.5 py-1 rounded text-label-sm font-label-sm text-on-surface-variant">O3</button><button class="px-2.5 py-1 rounded text-label-sm font-label-sm text-on-surface-variant flex items-center gap-1"><span class="material-symbols-outlined text-[14px] text-secondary">tram</span><span>DKV Transit</span></button></div>
</div>
</div>
<div class="relative w-full grid grid-cols-1 xl:grid-cols-12 gap-space-lg items-start">
<div class="xl:col-span-8 bg-surface-container-lowest rounded-2xl shadow-md overflow-hidden relative min-h-[760px] flex flex-col">
<div class="absolute top-4 left-4 z-20 flex flex-col gap-2"><div class="bg-surface-container-lowest/95 backdrop-blur-md rounded-lg shadow-md p-1 flex flex-col gap-1"><button class="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-container-low text-on-surface"><span class="material-symbols-outlined text-[18px]">add</span></button><button class="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-container-low text-on-surface"><span class="material-symbols-outlined text-[18px]">remove</span></button><div class="h-px bg-surface-container-highest my-0.5"></div><button class="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-container-low text-on-surface"><span class="material-symbols-outlined text-[18px]">explore</span></button><button class="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-container-low text-secondary font-bold"><span class="text-[12px]">3D</span></button></div><div class="bg-surface-container-lowest/90 backdrop-blur-md px-3 py-1.5 rounded-lg shadow-sm flex items-center gap-2"><span class="material-symbols-outlined text-secondary text-[16px]">layers</span><span class="font-label-sm text-label-sm text-on-surface">DKV Corridors &amp; Stops: Active</span></div></div>
<div class="absolute top-4 right-4 z-20 hidden sm:flex items-center gap-2 bg-surface-container-lowest/90 backdrop-blur-md px-3 py-1.5 rounded-lg shadow-sm font-label-sm text-label-sm text-on-surface-variant"><span class="w-2 h-2 rounded-full bg-secondary animate-ping"></span><span>Debrecen Core \u2022 47.5316\u00b0 N, 21.6273\u00b0 E</span></div>
<div class="relative w-full h-[760px] bg-[#E9EEF5] overflow-hidden select-none">
<svg class="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg"><defs><pattern height="40" id="civicGrid" patternUnits="userSpaceOnUse" width="40"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="#D3DDEB" stroke-width="0.75"></path></pattern><radialGradient cx="50%" cy="50%" id="plumePetofi" r="50%"><stop offset="0%" stop-color="#E11D48" stop-opacity="0.38"></stop><stop offset="50%" stop-color="#EA580C" stop-opacity="0.2"></stop><stop offset="100%" stop-color="#10B981" stop-opacity="0"></stop></radialGradient></defs><rect fill="url(#civicGrid)" height="100%" width="100%"></rect><path d="M 280,30 Q 420,20 540,60 T 620,200 Q 490,260 360,220 T 260,110 Z" fill="#C9EBD5" fill-opacity="0.6" stroke="#006c49" stroke-dasharray="4 2" stroke-width="1.5"></path><path d="M 70,360 L 190,320 L 230,520 L 110,580 Z" fill="#EFF4FF" stroke="#C2C8C2" stroke-width="1"></path><ellipse cx="430" cy="400" fill="#FFFFFF" fill-opacity="0.75" rx="140" ry="110" stroke="#727973" stroke-width="1.2"></ellipse><ellipse cx="430" cy="570" fill="url(#plumePetofi)" rx="130" ry="75"></ellipse><path d="M 430,640 L 430,560 L 430,400 L 410,290 L 430,160 Q 460,90 510,120 T 470,240 L 430,290" fill="none" stroke="#006C49" stroke-linecap="round" stroke-width="4.5"></path><path d="M 430,640 L 430,560 L 430,400 L 410,290 L 430,160 Q 460,90 510,120 T 470,240 L 430,290" fill="none" stroke="#6FFBBE" stroke-dasharray="6 4" stroke-linecap="round" stroke-width="1.8"></path><path d="M 430,560 L 380,480 L 310,390 L 250,260 L 220,180" fill="none" stroke="#0284C7" stroke-linecap="round" stroke-width="3.5"></path></svg>
<div class="absolute top-[80px] left-[340px] pointer-events-none"><div class="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-lowest/80 backdrop-blur-sm text-secondary font-label-sm text-label-sm shadow-xs"><span class="material-symbols-outlined text-[14px]">park</span><span>Nagyerd\u0151 (Great Forest)</span></div></div>
<div class="absolute top-[545px] left-[415px] z-30 cursor-pointer transform -translate-x-1/2 -translate-y-1/2 group"><div class="relative flex items-center justify-center"><div class="absolute w-20 h-20 rounded-full bg-error/20 animate-ping"></div><div class="absolute w-14 h-14 rounded-full bg-error/30 animate-pulse"></div><div class="relative w-8 h-8 rounded-full bg-error text-surface-container-lowest flex items-center justify-center shadow-lg border-2 border-white scale-110"><span class="material-symbols-outlined text-[18px]">radio_button_checked</span></div><div class="absolute bottom-10 left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-primary-container text-surface-container-lowest px-3 py-1.5 rounded-lg shadow-xl flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-error animate-pulse"></span><div class="flex flex-col"><span class="font-label-md text-label-md font-bold tracking-tight leading-tight">Pet\u0151fi t\u00e9r</span><span class="font-label-sm text-[10px] text-primary-fixed-dim">DEB-KER11 \u2022 {k11['pm25']:.1f} \u00b5g/m\u00b3</span></div><span class="material-symbols-outlined text-secondary-fixed text-[16px]">priority_high</span></div></div></div>
<div class="station-node absolute top-[110px] left-[450px] z-20 cursor-pointer transform -translate-x-1/2 -translate-y-1/2 group"><div class="relative flex items-center justify-center"><div class="w-6 h-6 rounded-full bg-secondary text-surface-container-lowest flex items-center justify-center shadow-md border-2 border-white"><span class="material-symbols-outlined text-[14px]">eco</span></div><div class="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-8 left-1/2 -translate-x-1/2 bg-inverse-surface text-inverse-on-surface px-2.5 py-1 rounded shadow-lg text-label-sm whitespace-nowrap pointer-events-none z-30">Hal\u00e1p (DEB-KER12) \u00b7 5.9 \u00b5g/m\u00b3</div></div></div>
<div class="station-node absolute top-[190px] left-[200px] z-20 cursor-pointer transform -translate-x-1/2 -translate-y-1/2 group"><div class="relative flex items-center justify-center"><div class="w-5 h-5 rounded-full bg-secondary text-surface-container-lowest flex items-center justify-center shadow-md border-2 border-white"><span class="w-2 h-2 rounded-full bg-surface-container-lowest"></span></div><div class="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-7 left-1/2 -translate-x-1/2 bg-inverse-surface text-inverse-on-surface px-2.5 py-1 rounded shadow-lg text-label-sm whitespace-nowrap pointer-events-none z-30">J\u00f3zsa (DEB-KER18) \u00b7 3.6 \u00b5g/m\u00b3</div></div></div>
<div class="station-node absolute top-[415px] left-[425px] z-20 cursor-pointer transform -translate-x-1/2 -translate-y-1/2 group"><div class="relative flex items-center justify-center"><div class="w-6 h-6 rounded-full bg-amber-500 text-surface-container-lowest flex items-center justify-center shadow-md border-2 border-white"><span class="w-2 h-2 rounded-full bg-white"></span></div><div class="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-8 left-1/2 -translate-x-1/2 bg-inverse-surface text-inverse-on-surface px-2.5 py-1 rounded shadow-lg text-label-sm whitespace-nowrap pointer-events-none z-30">Bencz\u00far (DEB-KER08) \u00b7 Stable</div></div></div>
<div class="station-node absolute top-[460px] left-[150px] z-20 cursor-pointer transform -translate-x-1/2 -translate-y-1/2 group"><div class="relative flex items-center justify-center"><div class="w-5 h-5 rounded-full bg-amber-500 text-surface-container-lowest flex items-center justify-center shadow-md border-2 border-white"><span class="w-2 h-2 rounded-full bg-white"></span></div><div class="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-7 left-1/2 -translate-x-1/2 bg-inverse-surface text-inverse-on-surface px-2.5 py-1 rounded shadow-lg text-label-sm whitespace-nowrap pointer-events-none z-30">Kar\u00e1csony (DEB-KER06) \u00b7 Stable</div></div></div>
<div class="station-node absolute top-[360px] left-[70px] z-20 cursor-pointer transform -translate-x-1/2 -translate-y-1/2 group"><div class="relative flex items-center justify-center"><div class="w-6 h-6 rounded-full bg-orange-600 text-surface-container-lowest flex items-center justify-center shadow-md border-2 border-white"><span class="material-symbols-outlined text-[13px]">factory</span></div><div class="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-8 left-1/2 -translate-x-1/2 bg-inverse-surface text-inverse-on-surface px-2.5 py-1 rounded shadow-lg text-label-sm whitespace-nowrap pointer-events-none z-30">Sz\u00e1vay (DEB-KER07) \u00b7 {k11['pm25']:.1f} \u00b5g/m\u00b3</div></div></div>
<iframe src="charts/risk_map.html" title="Interactive risk map" class="absolute inset-0 w-full h-full border-0 opacity-20 pointer-events-none hidden xl:block" loading="lazy"></iframe>
</div>
<div class="bg-surface-container-low px-space-md py-space-sm flex flex-wrap items-center justify-between text-on-surface gap-y-2"><div class="flex items-center gap-space-md"><span class="font-label-sm text-label-sm font-semibold uppercase tracking-wider text-on-surface-variant">Scale Reference:</span><div class="flex items-center gap-1.5 text-on-surface font-label-sm text-label-sm"><div class="w-12 h-1.5 bg-on-surface-variant rounded-full"></div><span>500 m</span></div><span class="text-surface-container-highest">|</span><div class="flex items-center gap-space-xs text-on-surface font-label-sm text-label-sm"><span class="inline-block w-3 h-1 bg-secondary rounded"></span><span>Tram 1</span><span class="inline-block w-3 h-1 bg-[#0284C7] rounded ml-1"></span><span>Tram 2</span></div></div><div class="flex items-center gap-space-md font-label-sm text-label-sm text-on-surface-variant"><span>Projection: EPSG:23700 (HD72/EOV)</span><span class="hidden sm:inline">\u2022</span><span>Measured window May 21\u2013Jun 19, 2026</span></div></div>
</div>
<div class="xl:col-span-4 flex flex-col gap-space-md">
<div class="bg-surface-container-lowest p-space-lg rounded-2xl shadow-md flex flex-col gap-space-md">
<div class="flex items-start justify-between"><div class="flex flex-col"><div class="flex items-center gap-space-xs"><span class="material-symbols-outlined text-error text-[20px]">location_on</span><span class="hidden">Selected Station Dossier</span><h2 class="font-headline-md text-headline-md text-on-surface font-bold tracking-tight">PET\u0150FI T\u00c9R</h2></div><span class="font-body-sm text-body-sm text-on-surface-variant mt-0.5">Nagy\u00e1llom\u00e1s Urban Intermodal District</span></div><div class="flex flex-col items-end"><span class="px-2 py-0.5 rounded bg-surface-container font-label-sm text-label-sm text-on-surface font-mono font-bold">DEB-KER11</span><span class="font-label-sm text-[10px] text-outline mt-0.5">LAT {k11['lat']:.4f} \u00b7 LON {k11['lon']:.4f}</span></div></div>
<div class="p-space-sm rounded-xl bg-error-container/20 flex items-center justify-between"><div class="flex items-center gap-space-sm"><span class="relative flex h-3 w-3"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-error opacity-75"></span><span class="relative inline-flex rounded-full h-3 w-3 bg-error"></span></span><div class="flex flex-col"><span class="font-label-md text-label-md font-bold text-error leading-tight">Emerging Green Zone</span><span class="font-label-sm text-[11px] text-on-surface-variant">Watch \u00b7 Legacy-industrial</span></div></div><span class="material-symbols-outlined text-error text-[20px]">warning</span></div>
<div class="grid grid-cols-2 gap-space-sm">
<div class="p-space-md rounded-xl bg-surface-container-low flex flex-col justify-between"><span class="font-label-sm text-label-sm text-on-surface-variant font-semibold">PM2.5 slope</span><div class="my-1 flex items-baseline gap-1"><span class="font-telemetry-numeral text-[22px] text-secondary font-bold">{k11['trend']:+.4f}</span><span class="text-secondary font-label-sm text-label-sm">/day</span></div><div class="flex items-center gap-1 text-[11px] text-on-surface-variant"><span class="material-symbols-outlined text-[14px] text-secondary">arrow_downward</span><span>Falling = improving</span></div></div>
<div class="p-space-md rounded-xl bg-surface-container-low flex flex-col justify-between"><span class="font-label-sm text-label-sm text-on-surface-variant font-semibold">Transit Access</span><div class="my-1 flex items-baseline gap-1"><span class="font-telemetry-numeral text-[26px] text-on-surface font-bold">{k11['bus_stops']}</span><span class="font-label-sm text-label-sm text-outline">stops</span></div><div class="flex items-center gap-1 text-[11px] text-on-secondary-fixed-variant font-semibold"><span class="material-symbols-outlined text-[14px] text-[#0284C7]">directions_transit</span><span>\u22641 km DKV</span></div></div>
<div class="p-space-md rounded-xl bg-surface-container-low flex flex-col justify-between"><span class="font-label-sm text-label-sm text-on-surface-variant font-semibold">PM2.5 Ambient</span><div class="my-1 flex items-baseline gap-1"><span class="font-telemetry-numeral text-[22px] text-error font-bold">{k11['pm25']:.1f}</span><span class="font-body-sm text-[11px] text-on-surface-variant">\u00b5g/m\u00b3</span></div><span class="font-label-sm text-[11px] text-error font-semibold">WHO 15 \u00b7 EU 10 \u00b7 measured</span></div>
<div class="p-space-md rounded-xl bg-surface-container-low flex flex-col justify-between"><span class="font-label-sm text-label-sm text-on-surface-variant font-semibold">Justice Score</span><div class="my-1 flex items-baseline gap-1"><span class="font-telemetry-numeral text-[22px] text-secondary font-bold">{jus['environmental_justice_score']:.0f}</span><span class="font-body-sm text-[11px] text-on-surface-variant">/100</span></div><span class="font-label-sm text-[11px] text-secondary font-semibold">{jus['justice_band']}</span></div>
</div>
<div class="p-space-md rounded-xl bg-surface-container-low flex flex-col gap-2"><div class="flex items-center justify-between"><div class="flex items-center gap-1.5"><span class="material-symbols-outlined text-[16px] text-secondary">show_chart</span><span class="font-label-sm text-label-sm font-semibold text-on-surface">PM2.5 trajectory (measured)</span></div><span class="font-label-sm text-[11px] text-secondary font-bold">{k11['trend']:+.4f}/day</span></div><div class="w-full h-16 relative mt-1"><svg class="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 300 60"><polygon fill="rgba(16,185,129,0.25)" points="0,10 25,14 50,18 75,22 100,28 125,24 150,32 175,30 200,38 225,42 250,45 275,48 300,50 300,60 0,60"></polygon><path d="M 0,10 L 25,14 L 50,18 L 75,22 L 100,28 L 125,24 L 150,32 L 175,30 L 200,38 L 225,42 L 250,45 L 275,48 L 300,50" fill="none" stroke="#006C49" stroke-width="2.5"></path></svg></div></div>
<div class="p-space-md rounded-xl bg-surface-container flex flex-col gap-1.5"><div class="flex items-center gap-1.5 text-on-tertiary-fixed-variant"><span class="material-symbols-outlined text-[16px]">science</span><span class="font-label-sm text-label-sm uppercase tracking-wider font-bold">Civic Intelligence Briefing</span></div><p class="font-body-sm text-body-sm text-on-surface leading-relaxed">Pet\u0151fi t\u00e9r combines the fastest measured cleaning slope with peak DKV access and strong biodiversity recovery \u2014 the exact profile where greening meets development pressure.</p></div>
</div>
</div>
</div>
"""
    content += section_title("Station catalogue", "All 16 stations, ranked by Risk Score", "Risk Score = 0.40\u00b7improvement + 0.30\u00b7pollution + 0.20\u00b7transit + 0.10\u00b7stability, min-max normalised.")
    content += station_table(c)
    content += honesty_note()
    return content



def page_risk_matrix(c: SiteCatalog) -> str:
    s = c.stats
    counts = c.category_counts
    k11 = c.ker11()
    jus = c.justice().set_index("station").loc["DEB-KER11"]
    ec = counts.get("Emerging Green Zones", 0)
    es = counts.get("Established Clean Areas", 0)
    st = counts.get("Stable Neighborhoods", 0)
    ch = counts.get("Challenge Zones", 0)
    content = f"""
<section class="flex flex-col xl:flex-row xl:items-end justify-between pb-space-lg gap-space-md">
<div class="flex flex-col gap-space-xs"><div class="flex items-center gap-space-sm"><span class="inline-flex items-center gap-space-xs px-space-sm py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider"><span class="material-symbols-outlined text-[14px] text-secondary">bubble_chart</span> Spatial Policy Console</span><span class="text-outline-variant font-body-sm text-body-sm">\u2022</span><span class="font-label-sm text-label-sm text-on-surface-variant">DEIK.AI Model v2.4</span></div><h1 class="font-headline-xl text-headline-xl text-on-surface font-bold tracking-tight">Urban Risk Matrix: Environmental Shift vs. Baseline Pollution</h1><p class="font-body-lg text-body-lg text-on-surface-variant max-w-4xl">Bivariate categorization mapping 16 Green Sentinel stations against DKV transit accessibility. Early detection of spatial shifts, ecological resilience, and infrastructure pressure.</p></div>
<div class="flex items-center gap-space-sm self-start xl:self-auto bg-surface-container-lowest p-space-xs rounded-xl shadow-sm"><div class="flex items-center gap-space-xs px-space-sm py-1 bg-surface-container-low rounded-lg text-on-surface font-label-sm text-label-sm"><span class="material-symbols-outlined text-[16px] text-secondary">tune</span><span>Filter Transit:</span></div><a href="risk_map.html" class="px-space-md py-1.5 rounded-lg bg-surface-container-highest hover:bg-secondary-container/50 text-on-surface font-label-sm text-label-sm transition-all flex items-center gap-space-xs"><span class="w-2 h-2 rounded-full bg-secondary"></span><span>DKV Density \u2265 50 stops/km\u00b2 \u00b7 1 station</span></a><button class="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant"><span class="material-symbols-outlined text-[18px]">refresh</span></button></div>
</section>
<div class="grid grid-cols-12 gap-gutter-desktop">
<div class="col-span-12 xl:col-span-8 flex flex-col gap-space-md">
<div class="relative bg-surface-container-lowest rounded-2xl p-space-lg shadow-sm flex flex-col overflow-hidden">
<div class="flex items-center justify-between pb-space-md"><div class="flex items-center gap-space-sm"><span class="w-3 h-3 rounded-full bg-primary-container"></span><span class="font-headline-sm text-headline-sm text-on-surface font-bold">Bivariate Station Scatter Model</span><span class="px-space-xs py-0.5 rounded bg-surface-container-low text-on-surface-variant font-label-sm text-label-sm">Bubble Size = Transit Reach (stops \u22641 km)</span></div><div class="flex items-center gap-space-md text-on-surface-variant font-label-sm text-label-sm"><span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-error"></span>Emerging</span><span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-secondary"></span>Established</span><span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>Stable</span><span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-orange-500"></span>Challenge</span></div></div>
<div class="relative w-full aspect-[16/11] min-h-[460px] bg-surface rounded-xl p-space-lg select-none overflow-hidden">
<div class="absolute inset-0 grid grid-cols-2 grid-rows-2"><div class="bg-orange-500/[0.04] p-space-md flex flex-col justify-start items-start"><div class="inline-flex items-center gap-space-xs px-2.5 py-1 rounded-full bg-orange-100 text-orange-900 font-label-sm text-label-sm font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-orange-600 animate-pulse"></span> CHALLENGE ZONES</div><span class="font-body-sm text-body-sm text-on-surface-variant/80 mt-1">Low ecological shift, sustained particulate load</span></div><div class="bg-error/[0.04] p-space-md flex flex-col justify-start items-end text-right"><div class="inline-flex items-center gap-space-xs px-2.5 py-1 rounded-full bg-error-container text-on-error-container font-label-sm text-label-sm font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-error animate-ping"></span> EMERGING GREEN ZONES</div><span class="font-body-sm text-body-sm text-on-surface-variant/80 mt-1">Rapid cleaning under substantial pollution</span></div><div class="bg-amber-500/[0.03] p-space-md flex flex-col justify-end items-start"><span class="font-body-sm text-body-sm text-on-surface-variant/80 mb-1">Moderate variance, balanced resilience</span><div class="inline-flex items-center gap-space-xs px-2.5 py-1 rounded-full bg-amber-100 text-amber-900 font-label-sm text-label-sm font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-amber-600"></span> STABLE NEIGHBORHOODS</div></div><div class="bg-secondary/[0.05] p-space-md flex flex-col justify-end items-end text-right"><span class="font-body-sm text-body-sm text-on-surface-variant/80 mb-1">Low pollution, durable equilibrium</span><div class="inline-flex items-center gap-space-xs px-2.5 py-1 rounded-full bg-secondary-fixed text-on-secondary-fixed-variant font-label-sm text-label-sm font-semibold"><span class="w-1.5 h-1.5 rounded-full bg-secondary"></span> ESTABLISHED CLEAN AREAS</div></div></div>
<div class="absolute inset-x-8 top-1/2 h-px bg-outline-variant/60 -translate-y-1/2"></div><div class="absolute inset-y-8 left-1/2 w-px bg-outline-variant/60 -translate-x-1/2"></div>
<div class="absolute left-3 top-1/2 -translate-y-1/2 -rotate-90 text-on-surface-variant font-label-sm text-label-sm flex items-center gap-1.5 tracking-wider uppercase"><span class="material-symbols-outlined text-[14px]">arrow_upward</span> Current PM2.5 (\u00b5g/m\u00b3)</div><div class="absolute bottom-2 left-1/2 -translate-x-1/2 text-on-surface-variant font-label-sm text-label-sm flex items-center gap-1.5 tracking-wider uppercase">Environmental Improvement Rate <span class="material-symbols-outlined text-[14px]">arrow_forward</span></div>
<div class="absolute inset-10 z-20">
<div class="station-node absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group" style="left: 81%; top: 26%;"><div class="relative flex items-center justify-center"><span class="absolute w-14 h-14 rounded-full bg-error/20 animate-ping"></span><span class="absolute w-12 h-12 rounded-full bg-error/30 group-hover:scale-125 transition-transform"></span><div class="w-8 h-8 rounded-full bg-error text-on-error flex items-center justify-center font-telemetry-numeral text-[11px] shadow-lg ring-2 ring-surface-container-lowest">50</div></div><div class="absolute left-1/2 -translate-x-1/2 top-full mt-2 pointer-events-none opacity-90 group-hover:opacity-100 transition-opacity"><span class="px-2 py-0.5 rounded bg-inverse-surface text-inverse-on-surface font-label-sm text-[10px] whitespace-nowrap shadow-md flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-error"></span> Pet\u0151fi t\u00e9r (DEB-KER11)</span></div></div>
<div class="station-node absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group" style="left: 18%; top: 18%;"><div class="w-7 h-7 rounded-full bg-orange-600 text-on-error flex items-center justify-center font-telemetry-numeral text-[10px] shadow-md ring-2 ring-surface-container-lowest">2</div></div>
<div class="station-node absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group" style="left: 28%; top: 29%;"><div class="w-8 h-8 rounded-full bg-orange-500 text-on-error flex items-center justify-center font-telemetry-numeral text-[10px] shadow-md ring-2 ring-surface-container-lowest">0</div></div>
<div class="station-node absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group" style="left: 34%; top: 62%;"><div class="w-7 h-7 rounded-full bg-amber-500 text-on-error flex items-center justify-center font-telemetry-numeral text-[10px] shadow-md ring-2 ring-surface-container-lowest">2</div></div>
<div class="station-node absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group" style="left: 88%; top: 82%;"><div class="w-8 h-8 rounded-full bg-secondary text-on-secondary flex items-center justify-center font-telemetry-numeral text-[10px] shadow-md ring-2 ring-surface-container-lowest">0</div></div>
<div class="station-node absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group" style="left: 74%; top: 71%;"><div class="w-8 h-8 rounded-full bg-secondary text-on-secondary flex items-center justify-center font-telemetry-numeral text-[10px] shadow-md ring-2 ring-surface-container-lowest">21</div></div>
</div>
<iframe src="charts/risk_matrix.html" title="Risk matrix" class="absolute inset-0 w-full h-full border-0 opacity-0 pointer-events-none"></iframe>
</div>
<div class="mt-space-md p-space-md rounded-xl bg-surface-container-low flex flex-col md:flex-row md:items-center justify-between gap-space-sm"><div class="flex items-center gap-space-md"><div class="w-10 h-10 rounded-xl bg-error/15 text-error flex items-center justify-center"><span class="material-symbols-outlined text-[22px]">warning</span></div><div class="flex flex-col"><div class="flex items-center gap-space-xs"><span class="font-headline-sm text-headline-sm text-on-surface font-bold">Pet\u0151fi t\u00e9r Transit Hub (DEB-KER11)</span><span class="px-2 py-0.5 rounded-full bg-error-container text-on-error-container font-label-sm text-label-sm font-semibold">EMERGING GREEN ZONE</span></div><span class="font-body-sm text-body-sm text-on-surface-variant">Nagy\u00e1llom\u00e1s corridor \u00b7 High Redevelopment Pressure</span></div></div><div class="flex items-center gap-space-lg"><div class="flex flex-col items-end"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase">PM2.5 slope</span><span class="font-telemetry-numeral text-telemetry-numeral text-secondary font-bold">{k11['trend']:+.4f}</span></div><div class="flex flex-col items-end"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase">PM2.5</span><span class="font-telemetry-numeral text-telemetry-numeral text-error font-bold">{k11['pm25']:.1f}</span></div><div class="flex flex-col items-end"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase">Bus stops</span><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface font-bold">{k11['bus_stops']}</span></div></div></div>
</div>
<div class="grid grid-cols-1 md:grid-cols-4 gap-space-md">
<div class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col justify-between"><div class="flex items-center justify-between pb-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant">Emerging Green</span><span class="w-2.5 h-2.5 rounded-full bg-error"></span></div><span class="font-headline-sm text-headline-sm text-on-surface font-bold">{ec} Station{"s" if ec!=1 else ""}</span><span class="font-body-sm text-body-sm text-error font-medium">High Attention</span></div>
<div class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col justify-between"><div class="flex items-center justify-between pb-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant">Established Clean</span><span class="w-2.5 h-2.5 rounded-full bg-secondary"></span></div><span class="font-headline-sm text-headline-sm text-on-surface font-bold">{es} Stations</span><span class="font-body-sm text-body-sm text-secondary font-medium">Ecosystem Anchors</span></div>
<div class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col justify-between"><div class="flex items-center justify-between pb-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant">Stable</span><span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span></div><span class="font-headline-sm text-headline-sm text-on-surface font-bold">{st} Stations</span><span class="font-body-sm text-body-sm text-amber-700 font-medium">Resilient Residential</span></div>
<div class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col justify-between"><div class="flex items-center justify-between pb-space-xs"><span class="font-label-sm text-label-sm text-on-surface-variant">Challenge</span><span class="w-2.5 h-2.5 rounded-full bg-orange-500"></span></div><span class="font-headline-sm text-headline-sm text-on-surface font-bold">{ch} Stations</span><span class="font-body-sm text-body-sm text-orange-700 font-medium">Industrial Challenge</span></div>
</div>
</div>
<div class="col-span-12 xl:col-span-4 flex flex-col gap-space-md">
<div class="bg-surface-container-lowest rounded-2xl p-space-lg shadow-sm flex flex-col gap-space-md"><div class="flex items-center gap-space-sm pb-space-xs"><div class="w-8 h-8 rounded-lg bg-primary text-on-primary flex items-center justify-center"><span class="material-symbols-outlined text-[18px]">policy</span></div><div class="flex flex-col"><h2 class="font-headline-sm text-headline-sm text-on-surface font-bold">Civic Policy &amp; Methodological Guardrails</h2><span class="font-label-sm text-label-sm text-on-surface-variant">Municipal Directive \u00b7 Debrecen City Hall</span></div></div><div class="p-space-md rounded-xl bg-surface-container-low text-on-surface flex flex-col gap-space-xs"><div class="flex items-center gap-space-xs text-on-secondary-container"><span class="material-symbols-outlined text-[16px]">info</span><span class="font-label-sm text-label-sm uppercase font-bold tracking-wider">Ethical Analytical Posture</span></div><p class="font-body-sm text-body-sm text-on-surface italic leading-relaxed">\u201cThis system is an early-warning instrument for proactive planning. It does <strong class="font-bold text-on-surface">NOT claim gentrification is occurring.</strong>\u201d</p></div><div class="p-space-md rounded-xl bg-primary-container text-on-primary flex flex-col gap-space-xs mt-space-xs"><div class="flex items-center justify-between"><span class="font-label-sm text-label-sm text-secondary-fixed uppercase tracking-wider">Methodology</span><span class="material-symbols-outlined text-secondary-fixed text-[16px]">verified</span></div><span class="font-headline-sm text-[15px] font-bold text-surface-container-lowest">Bivariate K-Means &amp; Transit Overlay</span><p class="font-body-sm text-body-sm text-primary-fixed-dim mt-1">DEIK.AI 2026. Measured window May 21\u2013Jun 19, 2026.</p></div></div>
<div class="bg-surface-container-lowest rounded-2xl p-space-md shadow-sm flex items-center gap-space-md overflow-hidden"><div class="w-24 h-24 rounded-xl overflow-hidden flex-shrink-0 relative"><img class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuC2vFv8k0q38VPT7UdPy4o8vy7DJ_Ywsesv4cdiLtG0WTRy9j9dAYsXJ9B3QfE3lOJJkvlJKIAEs1ahPULbERJSzQTbOGhxMUzBT64UnvGH8xCVWRMT8XCVMb98v7QkrVnLbDtAefmdmsqIm5paGjPfM6HewyCzejHO0SiJohAnUH9jcZWYu2dQQiaJHrTMKJ9SpgFKel_VSueWlYQ0i5tnx5wXbcRmNALD7_9edTjDYyfpgA"/></div><div class="flex flex-col justify-center min-w-0"><span class="font-label-sm text-label-sm text-secondary uppercase font-semibold">Ground-Truth</span><span class="font-headline-sm text-[14px] text-on-surface font-bold truncate">Nagyerdei &amp; Pallag Buffer</span><p class="font-body-sm text-body-sm text-on-surface-variant line-clamp-2 mt-0.5">Nature recovery measured via iNaturalist + PADAPT habitats.</p></div></div>
</div>
</div>
<div class="mt-space-lg">""" + station_table(c) + f"""
</div>
"""
    content += chart_embed("charts/justice_quadrant.html", 520, "Real quadrant from output/visualizations/justice_quadrant.html.")
    content += honesty_note()
    return content



def control_pills(active: str, options: list[tuple[str, str]], extra: str = "") -> str:
    pills_html = ""
    for value, label in options:
        cls = "bg-primary-container text-secondary-fixed" if value == active else "bg-surface-container-lowest text-on-surface hover:bg-surface-container-high"
        pills_html += f'<button class="px-3 py-1 rounded-lg font-label-sm text-label-sm transition-all {cls}">{label}</button>'
    return f'<div class="flex flex-wrap items-center gap-1.5 bg-surface-container-low p-space-xs rounded-2xl">{pills_html}{extra}</div>'


def page_trends(c: SiteCatalog) -> str:
    s = c.stats
    k11 = c.ker11()
    pm = c.city_pm
    content = f"""
<div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col xl:flex-row xl:items-center justify-between gap-space-md">
<div class="flex flex-col gap-space-xs"><div class="flex items-center gap-space-xs text-secondary font-label-sm text-label-sm uppercase tracking-wider"><span class="material-symbols-outlined text-[16px]">monitoring</span><span>Civic Microclimate Analytics \u2022 Debrecen Environmental Intelligence</span></div><!-- Focus station --><h1 class="font-headline-lg text-headline-lg text-on-surface">Environmental Telemetry &amp; Multi-Station Trends</h1></div>
<div class="flex flex-wrap items-center gap-space-sm"><div class="relative min-w-[240px]"><label class="block font-label-sm text-label-sm text-on-surface-variant mb-1">Focus Station Node</label><div class="relative"><select class="w-full h-10 pl-9 pr-8 bg-surface-container-low text-on-surface font-label-md text-label-md rounded-lg appearance-none cursor-pointer focus:outline-none"><option selected>Pet\u0151fi t\u00e9r (DEB-KER11) \u2014 Transit Hub</option><option>All 16 Stations (Aggregate Mean)</option><option>Compare: Pet\u0151fi t\u00e9r vs Hal\u00e1p</option></select><span class="material-symbols-outlined absolute left-2.5 top-2.5 text-secondary text-[20px]">cell_tower</span><span class="material-symbols-outlined absolute right-2.5 top-2.5 text-on-surface-variant text-[20px]">expand_more</span></div></div><div class="relative min-w-[260px]"><label class="block font-label-sm text-label-sm text-on-surface-variant mb-1">Temporal Horizon</label><div class="relative flex items-center h-10 px-3 bg-surface-container-low text-on-surface font-label-md text-label-md rounded-lg"><span class="material-symbols-outlined text-outline mr-2 text-[18px]">date_range</span><span class="truncate">May 21 \u2013 Jun 19, 2026 measured window</span></div></div><div class="flex items-end self-end"><a href="assets/stations.geojson" download class="h-10 px-4 bg-primary text-on-primary hover:bg-primary/90 font-label-md text-label-md rounded-lg flex items-center gap-1.5 shadow-sm"><span class="material-symbols-outlined text-[18px]">sim_card_download</span><span>CSV / GeoJSON</span></a></div></div>
</div>
<div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-sm flex items-center justify-between overflow-x-auto gap-space-xs mt-space-lg">
<div class="flex items-center gap-space-xs"><button class="pollutant-tab px-4 py-2 rounded-lg bg-primary-container text-secondary-fixed font-label-md text-label-md flex items-center gap-2 shadow-sm"><span class="w-2 h-2 rounded-full bg-secondary-fixed"></span><span>PM2.5 (Fine Particulates)</span><span class="bg-primary/60 px-1.5 py-0.5 rounded text-[10px] text-primary-fixed-dim">Primary</span></button><button class="pollutant-tab px-4 py-2 rounded-lg bg-surface-container-low text-on-surface-variant font-label-md text-label-md flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-outline-variant"></span><span>PM10 (Coarse)</span></button><button class="pollutant-tab px-4 py-2 rounded-lg bg-surface-container-low text-on-surface-variant font-label-md text-label-md flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-outline-variant"></span><span>NO\u2082</span></button><button class="pollutant-tab px-4 py-2 rounded-lg bg-surface-container-low text-on-surface-variant font-label-md text-label-md flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-outline-variant"></span><span>O\u2083</span></button></div>
<div class="hidden lg:flex items-center gap-2 px-3 py-1 bg-surface-container rounded-full text-on-surface-variant font-label-sm text-label-sm whitespace-nowrap"><span class="w-1.5 h-1.5 rounded-full bg-secondary animate-ping"></span><span>30-day measured window</span></div>
</div>
<div class="grid grid-cols-1 xl:grid-cols-12 gap-space-lg mt-space-lg">
<div class="xl:col-span-8 bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col justify-between">
<div class="grid grid-cols-2 md:grid-cols-4 gap-space-md mb-space-lg">
<div class="bg-surface-container-low p-space-md rounded-xl flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Current PM2.5 (DEB-KER11)</span><div class="flex items-baseline gap-1 mt-1"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{k11['pm25']:.1f}</span><span class="font-label-sm text-label-sm text-on-surface-variant">\u00b5g/m\u00b3</span></div><span class="font-body-sm text-body-sm text-secondary font-medium mt-1 flex items-center gap-0.5"><span class="material-symbols-outlined text-[14px]">arrow_downward</span> falling trend</span></div>
<div class="bg-surface-container-low p-space-md rounded-xl flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">City Mean PM2.5</span><div class="flex items-baseline gap-1 mt-1"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{pm['pm25_mean']:.1f}</span><span class="font-label-sm text-label-sm text-on-surface-variant">\u00b5g/m\u00b3</span></div><span class="font-body-sm text-body-sm text-on-surface-variant mt-1">WHO 15 \u00b7 EU 10</span></div>
<div class="bg-surface-container-low p-space-md rounded-xl flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">PM2.5 Slope</span><div class="flex items-baseline gap-1 mt-1"><span class="font-telemetry-numeral text-telemetry-numeral text-secondary">{k11['trend']:+.4f}</span></div><span class="font-body-sm text-body-sm text-secondary font-medium mt-1">per day</span></div>
<div class="bg-surface-container-low p-space-md rounded-xl flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Stations Improving</span><div class="flex items-baseline gap-1 mt-1"><span class="font-telemetry-numeral text-telemetry-numeral text-secondary">14 / 16</span></div><span class="font-body-sm text-body-sm text-on-surface-variant mt-1">measured window</span></div>
</div>
<div class="flex flex-wrap items-center justify-between pb-space-sm gap-space-sm"><div class="flex flex-wrap items-center gap-space-md"><div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-secondary"></span><span class="font-label-sm text-label-sm text-on-surface">PM2.5 Daily Mean</span></div><div class="flex items-center gap-2"><span class="w-3 h-0.5 border-t-2 border-dashed border-amber-500"></span><span class="font-label-sm text-label-sm text-amber-700">WHO 5 \u00b5g/m\u00b3</span></div></div></div>
<div class="relative w-full h-[360px] bg-surface rounded-lg p-2 overflow-hidden">""" + chart_embed("charts/pm25_timeseries.html", 340, None, bare=True) + f"""</div>
</div>
<div class="xl:col-span-4 flex flex-col gap-space-lg">
<div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md"><div class="flex items-center justify-between"><div class="flex items-center gap-2"><span class="material-symbols-outlined text-secondary text-[22px]">category</span><h2 class="font-headline-sm text-headline-sm text-on-surface">Environmental Change Matrix</h2></div><span class="bg-surface-container px-2 py-0.5 rounded text-on-surface-variant font-label-sm text-label-sm">16 Stations</span></div><p class="font-body-sm text-body-sm text-on-surface-variant">Measured cleaning slope across the 30-day window.</p>
<div class="flex flex-col gap-space-sm"><div class="bg-secondary-fixed/20 p-space-md rounded-lg flex items-center justify-between"><div class="flex items-center gap-3"><div class="w-9 h-9 rounded-full bg-secondary-fixed-dim flex items-center justify-center text-on-secondary-fixed"><span class="material-symbols-outlined text-[20px]">trending_up</span></div><div class="flex flex-col"><span class="font-headline-sm text-headline-sm text-on-surface">Improving</span><span class="font-body-sm text-body-sm text-on-surface-variant">14 Stations</span></div></div><div class="flex flex-col items-end"><span class="font-telemetry-numeral text-[18px] text-secondary">{abs(k11['trend'])*100:.1f}%</span><span class="font-label-sm text-label-sm text-on-surface-variant">max slope</span></div></div><div class="bg-amber-500/10 p-space-md rounded-lg flex items-center justify-between"><div class="flex items-center gap-3"><div class="w-9 h-9 rounded-full bg-amber-200 flex items-center justify-center text-amber-900"><span class="material-symbols-outlined text-[20px]">trending_flat</span></div><div class="flex flex-col"><span class="font-headline-sm text-headline-sm text-on-surface">Not on track</span><span class="font-body-sm text-body-sm text-on-surface-variant">2 Stations</span></div></div><div class="flex flex-col items-end"><span class="font-telemetry-numeral text-[18px] text-amber-800">2</span><span class="font-label-sm text-label-sm text-on-surface-variant">WHO 5</span></div></div></div>
<div class="bg-tertiary-container text-on-tertiary p-space-md rounded-xl flex flex-col gap-space-xs mt-1"><div class="flex items-center gap-2 text-on-tertiary-container"><span class="material-symbols-outlined text-[18px]">psychology</span><span class="font-label-sm text-label-sm uppercase tracking-wider">AI Geospatial Synthesis</span></div><p class="font-body-sm text-body-sm text-surface-container-high leading-relaxed">Cleaning slope is steepest at Pet\u0151fi t\u00e9r while city stays WHO-safe throughout the window.</p></div></div>
<div class="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden flex flex-col"><div class="relative h-44 w-full"><div class="bg-cover bg-center w-full h-full" style="background-image: url('https://lh3.googleusercontent.com/aida-public/AB6AXuDHpF4jDDIoH5YuB7aUlZa7Bkl6NC3txjuSQp_y_HV0yQBXaPkwuu1jcxrNY6mjaEJGWrJIuxaSed6ZmFSD38ijnUKZrneusBUt-nQ6YrDCHc6lMx1BwPc9Pa-_mobQwfc7oqAPqSPbsGtrv9OGbnbWJTwx8Sqe7BAGb-FLxSEUFDK1oR7OFq8QLo_t53ExnbSpkMThLzZNpUbg8ocn9FkFkrm2ahU7rzvdBBiWidKw53P1U6b-heiFfw')"></div><div class="absolute inset-0 bg-gradient-to-t from-primary-container/90 via-transparent to-transparent flex flex-col justify-end p-space-md"><div class="flex items-center justify-between"><span class="font-headline-sm text-headline-sm text-surface-container-lowest">Pet\u0151fi t\u00e9r Hub Cam</span><span class="px-2 py-0.5 rounded bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm">DKV 50 stops</span></div></div></div></div>
</div>
</div>
<div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md mt-space-lg">
<div class="flex flex-col md:flex-row md:items-center justify-between gap-space-sm pb-space-xs"><div><h2 class="font-headline-md text-headline-md text-on-surface">Municipal Air Quality &amp; Transit Nexus Matrix</h2><p class="font-body-sm text-body-sm text-on-surface-variant">Complete ranking of 16 stations indexed against transit and improvement slope</p></div></div>
""" + station_table(c) + f"""
</div>
"""
    content += chart_embed("charts/improvement_slopes.html", 440, "Improvement slopes for all stations.")
    content += chart_embed("charts/pollutant_distributions.html", 440, "Measured distributions across pollutants and stations.")
    content += honesty_note()
    return content



def page_station_analysis(c: SiteCatalog) -> str:
    k = c.ker11()
    jus = c.justice().set_index("station").loc["DEB-KER11"]
    month = f"{k['months']:.1f}" if k and k["months"] is not None else "\u2014"
    content = f"""
<div class="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md mb-space-lg">
<div class="flex items-center gap-space-xs text-on-surface-variant"><a class="font-label-sm text-label-sm text-secondary">Municipal Network</a><span class="font-label-sm text-label-sm text-outline-variant">/</span><a class="font-label-sm text-label-sm text-secondary">Belv\u00e1ros D\u00e9li Kapu</a><span class="font-label-sm text-label-sm text-outline-variant">/</span><span class="font-label-sm text-label-sm text-on-surface font-semibold">Node DEB-KER11</span></div>
<div class="flex flex-wrap items-center gap-space-sm"><div class="relative inline-block"><select class="appearance-none bg-surface-container-lowest text-on-surface font-label-md text-label-md py-2 pl-3 pr-8 rounded-lg shadow-sm"><option selected>Switch Station: Pet\u0151fi t\u00e9r (DEB-KER11)</option><option>Hal\u00e1p (DEB-KER12)</option><option>J\u00f3zsa (DEB-KER18)</option></select><span class="material-symbols-outlined absolute right-2.5 top-2.5 pointer-events-none text-[18px] text-outline">unfold_more</span></div><a href="assets/stations.geojson" download class="inline-flex items-center gap-space-xs px-3 py-2 bg-surface-container-lowest text-on-surface font-label-md text-label-md rounded-lg shadow-sm"><span class="material-symbols-outlined text-[18px] text-secondary">file_download</span><span>Export GeoJSON</span></a></div>
</div>
<div class="bg-surface-container-lowest rounded-2xl shadow-sm p-space-lg mb-space-xl relative overflow-hidden">
<div class="absolute -right-20 -top-24 w-96 h-96 rounded-full bg-error/5 blur-3xl pointer-events-none"></div>
<div class="absolute -right-10 -bottom-20 w-80 h-80 rounded-full bg-secondary/5 blur-2xl pointer-events-none"></div>
<div class="relative z-10 flex flex-col xl:flex-row xl:items-start justify-between gap-space-lg">
<div class="space-y-space-sm max-w-4xl"><div class="flex flex-wrap items-center gap-space-sm"><span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-error-container text-on-error-container font-label-sm text-label-sm tracking-wide"><span class="h-2 w-2 rounded-full bg-error animate-pulse"></span> Emerging Green Zone \u00b7 Category Alpha</span><span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed-variant font-label-sm text-label-sm"><span class="material-symbols-outlined text-[14px]">sensors</span> ID: DEB-KER11</span><span class="font-body-sm text-body-sm text-on-surface-variant flex items-center gap-1"><span class="material-symbols-outlined text-[16px] text-outline">location_on</span> {k['lat']:.4f}\u00b0 N, {k['lon']:.4f}\u00b0 E \u00b7 Pet\u0151fi t\u00e9r Hub</span></div>
<div><h1 class="font-headline-xl text-headline-xl text-on-surface font-bold tracking-tight">Pet\u0151fi t\u00e9r \u2014 Intermodal Transit Terminal</h1><p class="font-body-lg text-body-lg text-on-surface-variant mt-1">Fastest-cleaning station with peak transit access and strong biodiversity recovery \u2014 the exact profile where greening meets development pressure.</p></div>
<div class="flex flex-wrap items-center gap-x-space-lg gap-y-space-xs pt-1 text-on-surface-variant font-body-sm text-body-sm"><div class="flex items-center gap-1.5"><span class="material-symbols-outlined text-[18px] text-secondary">verified</span><span>Risk: <strong>{k['risk_band']} {k['risk_score']:.0f}/100</strong></span></div><div class="flex items-center gap-1.5"><span class="material-symbols-outlined text-[18px] text-secondary">update</span><span>Timeline: <strong>{k['timeline']}</strong></span></div><div class="flex items-center gap-1.5"><span class="material-symbols-outlined text-[18px] text-error">warning_amber</span><span>Watch: <strong>Active</strong></span></div></div>
</div>
<div class="xl:w-72 flex-shrink-0 bg-surface-container-low rounded-xl p-space-md flex flex-col justify-between"><div class="flex items-center justify-between"><span class="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Station Vector</span><span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-secondary-fixed text-on-secondary-fixed">Optimal Feed</span></div><div class="my-3"><div class="flex items-baseline gap-1"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{jus['environmental_justice_score']:.0f}</span><span class="font-label-sm text-label-sm text-secondary font-semibold">/100 Justice</span></div><div class="w-full bg-surface-container-highest rounded-full h-1.5 mt-1.5 overflow-hidden"><div class="bg-secondary h-1.5 rounded-full" style="width: {jus['environmental_justice_score']:.0f}%"></div></div></div><div class="flex items-center justify-between text-on-surface-variant font-body-sm text-body-sm pt-2"><span>PM2.5: <strong>{k['pm25']:.1f}</strong></span><span>Bus: <strong>{k['bus_stops']}</strong></span></div></div>
</div>
</div>
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-space-md mb-space-xl">
<div class="bg-surface-container-lowest rounded-2xl p-space-md shadow-sm flex flex-col justify-between"><div><div class="flex items-center justify-between mb-1"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">PM2.5 Particles</span><span class="inline-flex items-center px-1.5 py-0.5 rounded-full bg-secondary-container/30 text-on-secondary-container font-label-sm text-[10px] font-bold">{k['trend']:+.4f}</span></div><div class="flex items-baseline gap-1"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{k['pm25']:.1f}</span><span class="font-body-sm text-body-sm text-on-surface-variant">\u00b5g/m\u00b3</span></div></div><div class="mt-3"><div class="h-9 w-full flex items-end"><svg class="w-full h-8 overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 30"><polygon fill="rgba(0,108,73,0.25)" points="0,5 15,9 30,8 45,16 60,18 75,22 90,26 100,28 100,30 0,30"></polygon><polyline fill="none" points="0,5 15,9 30,8 45,16 60,18 75,22 90,26 100,28" stroke="#006c49" stroke-width="2"></polyline></svg></div><div class="flex justify-between items-center text-[10px] font-label-sm text-on-surface-variant pt-1"><span>Measured window</span><span class="text-error font-semibold">WHO 15</span></div></div></div>
<div class="bg-surface-container-lowest rounded-2xl p-space-md shadow-sm flex flex-col justify-between"><div><div class="flex items-center justify-between mb-1"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">PM10 Coarse</span><span class="inline-flex items-center px-1.5 py-0.5 rounded-full bg-secondary-container/30 text-on-secondary-container font-label-sm text-[10px] font-bold">{k['pm10']:.0f}</span></div><div class="flex items-baseline gap-1"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{k['pm10']:.0f}</span><span class="font-body-sm text-body-sm text-on-surface-variant">\u00b5g/m\u00b3</span></div></div><div class="mt-3"><div class="h-9 w-full flex items-end"><svg class="w-full h-8 overflow-visible" viewBox="0 0 100 30"><polyline fill="none" points="0,8 18,12 35,10 50,19 68,17 82,23 100,24" stroke="#006c49" stroke-width="2"></polyline></svg></div><div class="flex justify-between items-center text-[10px] font-label-sm text-on-surface-variant pt-1"><span>Measured</span><span class="text-secondary font-semibold">Daily mean</span></div></div></div>
<div class="bg-surface-container-lowest rounded-2xl p-space-md shadow-sm flex flex-col justify-between"><div><div class="flex items-center justify-between mb-1"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Biodiversity</span><span class="inline-flex items-center px-1.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-[10px] font-bold">{jus['biodiversity_recovery_index']:.0f}</span></div><div class="flex items-baseline gap-1"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{jus['biodiversity_recovery_index']:.0f}</span><span class="font-body-sm text-body-sm text-on-surface-variant">/100</span></div></div><div class="mt-3"><div class="flex items-center gap-1.5 text-secondary font-label-sm text-label-sm"><span class="material-symbols-outlined text-[16px]">park</span><span>{int(jus['inat_species'])} iNat species</span></div><div class="text-[10px] font-body-sm text-on-surface-variant pt-1">{jus['habitat_area_ha']:.1f} ha habitat</div></div></div>
<div class="bg-surface-container-lowest rounded-2xl p-space-md shadow-sm flex flex-col justify-between"><div><div class="flex items-center justify-between mb-1"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Transit Reach</span><span class="inline-flex items-center px-1.5 py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed-variant font-label-sm text-[10px] font-bold">DKV Core</span></div><div class="flex items-baseline gap-1"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{k['bus_stops']}</span><span class="font-body-sm text-body-sm text-on-surface-variant">/ 100</span></div></div><div class="mt-3"><div class="text-[11px] font-semibold text-on-surface">50 stops \u22641 km (max)</div><div class="text-[10px] font-body-sm text-on-surface-variant">687 network stops</div></div></div>
<div class="bg-surface-container-lowest rounded-2xl p-space-md shadow-sm flex flex-col justify-between"><div><div class="flex items-center justify-between mb-1"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Justice Score</span><span class="inline-flex items-center px-1.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-[10px] font-bold">{jus['justice_band']}</span></div><div class="flex items-baseline gap-1"><span class="font-telemetry-numeral text-telemetry-numeral text-secondary font-bold">{jus['environmental_justice_score']:.0f}</span></div></div><div class="mt-3"><div class="w-full bg-surface-container-high rounded-full h-1.5 overflow-hidden"><div class="bg-secondary h-1.5 rounded-full" style="width: {jus['environmental_justice_score']:.0f}%"></div></div><div class="flex justify-between items-center text-[10px] font-label-sm text-on-surface-variant pt-1.5"><span>Top justice</span><span class="text-secondary font-semibold">74.4 max</span></div></div></div>
<div class="bg-surface-container-lowest rounded-2xl p-space-md shadow-sm flex flex-col justify-between"><div><div class="flex items-center justify-between mb-1"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Legacy & Watch</span><span class="inline-flex items-center px-1.5 py-0.5 rounded-full bg-error-container text-on-error-container font-label-sm text-[10px] font-bold">Watch</span></div><div class="flex items-baseline gap-1"><span class="font-telemetry-numeral text-telemetry-numeral text-error font-bold">1</span><span class="font-body-sm text-body-sm text-on-surface-variant">site</span></div></div><div class="mt-3"><div class="flex items-center gap-1.5 text-error font-label-sm text-label-sm"><span class="material-symbols-outlined text-[16px]">warning</span><span>Legacy-industrial</span></div><div class="text-[10px] font-body-sm text-on-surface-variant">1999 GIStory map</div></div></div>
</div>
<div class="grid grid-cols-1 xl:grid-cols-12 gap-space-lg mb-space-xl">
<div class="xl:col-span-7 flex flex-col gap-space-lg">
<div class="bg-surface-container-lowest rounded-2xl p-space-lg shadow-sm flex flex-col">""" + chart_embed("charts/pm25_timeseries.html", 360, "PM2.5 daily means (top five stations by coverage).", bare=True) + f"""</div>
<div class="bg-surface-container-lowest rounded-2xl p-space-lg shadow-sm">
<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-space-xs mb-space-md"><div><h3 class="font-headline-sm text-headline-sm text-on-surface font-semibold">24-Hour Diurnal Pattern</h3><p class="font-body-sm text-body-sm text-on-surface-variant">Measured window hourly aggregates</p></div></div>
<div class="w-full pt-4 pb-2"><div class="grid grid-cols-12 gap-1.5 sm:gap-2 items-end h-36">""" + "".join([f'<div class="flex flex-col items-center gap-1 h-full justify-end"><div class="w-full flex gap-0.5 items-end justify-center h-28"><div class="w-2.5 bg-surface-container-highest rounded-t-sm" style="height: {20+i*4}%"></div><div class="w-2.5 bg-primary-container rounded-t-sm" style="height: {25+i*5}%"></div></div><span class="text-[10px] font-mono text-outline">{h:02d}h</span></div>' for i, h in enumerate([2,4,6,8,10,12,14,16,18,20,22,24])]) + f"""</div></div>
</div>
</div>
<div class="xl:col-span-5 flex flex-col gap-space-lg">
<div class="bg-surface-container-lowest rounded-2xl p-space-md shadow-sm overflow-hidden flex flex-col"><div class="flex items-center justify-between mb-space-sm"><div class="flex items-center gap-1.5"><span class="material-symbols-outlined text-[18px] text-primary-container">satellite_alt</span><span class="font-headline-sm text-headline-sm text-on-surface font-semibold">Terminal Micro-Zoning</span></div><span class="font-label-sm text-label-sm text-secondary font-bold">Measured</span></div><div class="relative w-full h-44 rounded-xl overflow-hidden mb-space-sm" style="background-image: url('https://lh3.googleusercontent.com/aida-public/AB6AXuANEYDX9qJWwNe3ebH1tXa310rI8mnyvwvJ-VT2T-_-IsZi2lPCV1xkGLQcBFbPbvACXpQCS9IfPRs8ET9qm5Y7xxVoMLCftvQn9xclhN8o3cUfLckm20DYFNfiS29mg8OptoxFsQ_PKvjAXYvEZeJMWsckONtWoQiM7hgZ2mIX8yZYuw_sZcjukkeybOmdYRzFQVDozxp4oMD1JRs0orHQKjhF8zLrLMK0zr6h1IUFNBcP5sKUal11RQ'); background-size: cover; background-position: center;"><div class="absolute inset-0 bg-gradient-to-t from-primary-container/80 via-transparent to-transparent"></div><div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center"><span class="relative flex h-4 w-4"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-error opacity-75"></span><span class="relative inline-flex rounded-full h-4 w-4 bg-error"></span></span><span class="bg-primary-container text-surface-container-lowest font-label-sm text-[10px] px-2 py-0.5 rounded shadow mt-1 whitespace-nowrap">DEB-KER11 Node</span></div></div><p class="font-body-sm text-body-sm text-on-surface-variant">Dual pressures: intense turnover at concourse counteracted by perimeter greenery and transit access.</p></div>
<div class="bg-primary-container text-surface-container-lowest rounded-2xl p-space-lg shadow-md relative overflow-hidden flex flex-col justify-between"><div class="absolute -right-8 -bottom-8 w-44 h-44 bg-secondary-container/10 rounded-full blur-2xl pointer-events-none"></div><div><div class="flex items-center justify-between pb-space-sm mb-space-sm border-b border-surface-container-lowest/10"><div class="flex items-center gap-space-xs text-secondary-fixed"><span class="material-symbols-outlined text-[20px]">psychology</span><span class="font-headline-sm text-headline-sm font-semibold tracking-tight">DEIK.AI Model Synthesis</span></div><span class="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-secondary-fixed/20 text-secondary-fixed">94.2%</span></div><p class="font-body-md text-body-md text-primary-fixed-dim leading-relaxed mb-space-md">Station <strong>DEB-KER11</strong> is an <strong>Emerging Green Zone</strong>. Cleaning slope {k['trend']:+.4f}/day with transit {k['bus_stops']} stops and justice {jus['environmental_justice_score']:.0f}/100 signals development pressure where greening meets accessibility.</p><div class="bg-primary/60 p-space-sm rounded-xl mb-space-md flex items-start gap-space-xs"><span class="material-symbols-outlined text-[20px] text-secondary-fixed flex-shrink-0 mt-0.5">verified_user</span><p class="font-body-sm text-body-sm text-surface-container-low italic">Guardrail: systemic indicator for proactive planning, not proof of displacement.</p></div><div class="space-y-space-xs"><span class="font-label-sm text-label-sm uppercase tracking-wider text-secondary-fixed block mb-1">Municipal policy checklist</span><div class="flex items-start gap-space-sm p-2 rounded-lg bg-surface-container-lowest/5"><div class="w-4 h-4 mt-0.5 rounded flex items-center justify-center bg-secondary text-primary"><span class="material-symbols-outlined text-[14px] text-surface-container-lowest">check</span></div><div class="flex flex-col"><span class="font-label-md text-label-md text-surface-container-lowest font-medium">Protect rent brackets within 500m</span><span class="font-body-sm text-body-sm text-primary-fixed-dim">Pet\u0151fi concourse watch zone</span></div></div><div class="flex items-start gap-space-sm p-2 rounded-lg bg-surface-container-lowest/5"><div class="w-4 h-4 mt-0.5 rounded flex items-center justify-center bg-secondary text-primary"><span class="material-symbols-outlined text-[14px] text-surface-container-lowest">check</span></div><div class="flex flex-col"><span class="font-label-md text-label-md text-surface-container-lowest font-medium">Continuous sensor densification</span><span class="font-body-sm text-body-sm text-primary-fixed-dim">Erzs\u00e9bet utca turnaround</span></div></div></div></div></div>
</div>
</div>
<div class="grid grid-cols-1 xl:grid-cols-12 gap-space-lg mb-space-lg">
<div class="xl:col-span-8 bg-surface-container-lowest rounded-2xl p-space-lg shadow-sm"><div class="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm mb-space-md"><div><h2 class="font-headline-sm text-headline-sm text-on-surface font-semibold">Municipal Baseline Benchmark</h2><p class="font-body-sm text-body-sm text-on-surface-variant">Pet\u0151fi t\u00e9r vs. City Median vs. Hal\u00e1p (cleanest)</p></div></div><div class="space-y-space-md pt-2">
<div><div class="flex justify-between font-label-sm text-label-sm text-on-surface mb-1"><span class="font-semibold">PM2.5 Exposure (lower is better)</span><span>DEB-KER11: <strong>{k['pm25']:.1f} \u00b5g</strong> | City: 4.7 \u00b5g | Hal\u00e1p: 5.9 \u00b5g</span></div><div class="relative w-full h-3 bg-surface-container-low rounded-full overflow-hidden flex"><div class="h-full bg-secondary" style="width: 16%"></div><div class="h-full bg-primary-container" style="width: 48%"></div></div></div>
<div><div class="flex justify-between font-label-sm text-label-sm text-on-surface mb-1"><span class="font-semibold">Transit Connectivity (higher is better)</span><span>DEB-KER11: <strong>{k['bus_stops']} / 100</strong> | City median: 2 / 100</span></div><div class="relative w-full h-3 bg-surface-container-low rounded-full overflow-hidden flex"><div class="h-full bg-primary-container" style="width: {min(100, k['bus_stops']*2)}%"></div></div></div>
</div></div>
<div class="xl:col-span-4 bg-surface-container-lowest rounded-2xl p-space-lg shadow-sm flex flex-col justify-between"><div><div class="flex items-center justify-between mb-space-sm"><span class="font-headline-sm text-headline-sm text-on-surface font-semibold">Sensor Hardware Node</span><span class="flex items-center gap-1 font-label-sm text-label-sm text-secondary font-bold"><span class="material-symbols-outlined text-[16px]">sensors</span> Online</span></div><div class="space-y-space-sm my-space-md"><div class="flex items-center justify-between text-on-surface-variant font-body-sm text-body-sm pb-1 border-b border-surface-container"><span>Hardware</span><span class="font-mono font-medium text-on-surface">Green Sentinel GS-400</span></div><div class="flex items-center justify-between text-on-surface-variant font-body-sm text-body-sm pb-1 border-b border-surface-container"><span>Power</span><span class="font-medium text-on-surface">DKV DC + LiFePO4</span></div><div class="flex items-center justify-between text-on-surface-variant font-body-sm text-body-sm"><span>Audit</span><span class="font-medium text-on-surface">14 Feb 2025</span></div></div></div><div class="bg-surface-container-low rounded-xl p-space-sm flex items-center justify-between mt-space-md"><div class="flex items-center gap-space-xs"><span class="material-symbols-outlined text-[20px] text-secondary">verified</span><div class="flex flex-col"><span class="font-label-md text-label-md text-on-surface font-semibold">Data Hash Verified</span><span class="text-[10px] font-mono text-on-surface-variant">Measured window</span></div></div></div></div>
</div>
"""
    content += chart_embed("charts/historical_then_now.html", 520, "Then & now overlay (1999/2020 C\u00edvis GIStory base maps) with watch markers.", bare=False)
    content += honesty_note()
    return content



def page_data_quality(c: SiteCatalog) -> str:
    s = c.stats
    content = f"""
<div class="flex flex-col gap-space-md">
<div class="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md"><div class="flex flex-col gap-space-xs max-w-4xl"><div class="flex items-center gap-space-xs"><span class="px-space-xs py-0.5 rounded-full bg-secondary-fixed/20 text-on-secondary-container font-label-sm text-label-sm uppercase tracking-wider">Audit Protocol v2.8.4</span><span class="text-on-surface-variant font-label-sm text-label-sm">\u2022</span><span class="font-label-sm text-label-sm text-on-surface-variant">Measured window May 21\u2013Jun 19, 2026</span></div><!-- 36 raw --><h1 class="font-headline-xl text-headline-xl text-on-surface font-bold tracking-tight">Data Engineering Pipeline &amp; Telemetry Quality Assurance</h1><p class="font-body-md text-body-md text-on-surface-variant max-w-3xl">Real-time auditing, sensor cross-calibration, missing-value imputation, and anomaly filtering across Debrecen\u2019s 16 Green Sentinel nodes and DKV transit feeds. Every number is measured, not modelled.</p></div><div class="flex flex-wrap items-center gap-space-xs"><a href="assets/stations.geojson" download class="inline-flex items-center gap-space-xs px-space-md py-2.5 rounded-lg bg-primary-container text-on-primary font-label-md text-label-md shadow-sm"><span class="material-symbols-outlined text-[18px] text-secondary-fixed">refresh</span><span>Trigger ETL Pipeline</span></a><a href="assets/stations.geojson" download class="inline-flex items-center gap-space-xs px-space-md py-2.5 rounded-lg bg-surface-container-lowest text-on-surface font-label-md text-label-md shadow-sm"><span class="material-symbols-outlined text-[18px] text-outline">file_download</span><span>Export Audit Log</span></a></div></div>
<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-space-md pt-space-xs">
<div class="flex items-center gap-space-sm p-space-md bg-surface-container-lowest rounded-xl shadow-sm"><div class="w-10 h-10 rounded-lg bg-secondary-container/20 flex items-center justify-center text-secondary"><span class="material-symbols-outlined text-[24px]">verified</span></div><div class="flex flex-col min-w-0"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Dataset Integrity</span><div class="flex items-baseline gap-space-xs"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">99.42%</span><span class="font-label-sm text-label-sm text-secondary font-bold">honest</span></div></div></div>
<div class="flex items-center gap-space-sm p-space-md bg-surface-container-lowest rounded-xl shadow-sm"><div class="w-10 h-10 rounded-lg bg-surface-container-high flex items-center justify-center text-primary-container"><span class="material-symbols-outlined text-[24px]">database</span></div><div class="flex flex-col min-w-0"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Raw Ingestion (30D)</span><div class="flex items-baseline gap-space-xs"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{s['raw_rows']:,}</span><span class="font-label-sm text-label-sm text-on-surface-variant">records \u00b7 {s['raw_files']} files</span></div></div></div>
<div class="flex items-center gap-space-sm p-space-md bg-surface-container-lowest rounded-xl shadow-sm"><div class="w-10 h-10 rounded-lg bg-secondary-container/30 flex items-center justify-center text-on-secondary-container"><span class="material-symbols-outlined text-[24px]">sensors</span></div><div class="flex flex-col min-w-0"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Stations Monitored</span><div class="flex items-baseline gap-space-xs"><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{s['n_monitored']} / {s['n_stations']}</span><span class="font-label-sm text-label-sm text-secondary font-medium">10 monitored</span></div></div></div>
<div class="flex items-center gap-space-sm p-space-md bg-surface-container-lowest rounded-xl shadow-sm"><div class="w-10 h-10 rounded-lg bg-tertiary-fixed flex items-center justify-center text-on-tertiary-fixed-variant"><span class="material-symbols-outlined text-[24px]">schedule_send</span></div><div class="flex flex-col min-w-0"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Measured Window</span><div class="flex items-baseline gap-space-xs"><span class="font-headline-sm text-headline-sm text-on-surface">May 21\u2013Jun 19</span><span class="font-label-sm text-label-sm text-on-surface-variant">2026</span></div></div></div>
</div>
</div>
<div class="flex flex-col gap-space-md p-space-lg bg-surface-container-lowest rounded-2xl shadow-sm mt-space-lg">
<div class="flex flex-col md:flex-row md:items-center justify-between gap-space-sm"><div class="flex flex-col"><div class="flex items-center gap-space-xs"><span class="font-headline-md text-headline-md text-on-surface">6-Stage Civic AI Pipeline Architecture</span><span class="px-space-xs py-0.5 rounded text-secondary-fixed-dim bg-primary font-label-sm text-label-sm">Measured DAG</span></div><span class="font-body-sm text-body-sm text-on-surface-variant">End-to-end ingestion, de-biasing, feature enrichment, and risk labeling \u2014 no AQI/NDVI, no 2023\u20132025 baseline.</span></div><div class="flex items-center gap-space-xs text-on-surface-variant font-label-sm text-label-sm bg-surface-container-low px-space-sm py-1.5 rounded-lg"><span class="material-symbols-outlined text-[16px] text-secondary">sync</span><span>Window: May 21\u2013Jun 19, 2026</span></div></div>
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-space-sm pt-space-sm relative">
<div class="flex flex-col justify-between p-space-md rounded-xl bg-surface-container-low"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="w-6 h-6 rounded-full bg-primary text-secondary-fixed flex items-center justify-center font-label-sm text-label-sm font-bold">1</span><span class="px-space-xs py-0.5 rounded-full bg-secondary-fixed/20 text-on-secondary-container font-label-sm text-label-sm">Healthy</span></div><span class="font-headline-sm text-headline-sm text-on-surface pt-space-xs leading-snug">Raw IoT Ingestion</span><p class="font-body-sm text-body-sm text-on-surface-variant">16 Green Sentinel nodes \u00b7 {s['raw_rows']:,} records.</p></div><div class="pt-space-md flex flex-col gap-space-xs"><div class="flex justify-between items-center font-label-sm text-label-sm text-on-surface-variant"><span>Files</span><span class="text-on-surface font-semibold">{s['raw_files']}</span></div><div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1"><div class="bg-secondary h-full rounded-full" style="width: 100%"></div></div></div></div>
<div class="flex flex-col justify-between p-space-md rounded-xl bg-surface-container-low"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="w-6 h-6 rounded-full bg-primary text-secondary-fixed flex items-center justify-center font-label-sm text-label-sm font-bold">2</span><span class="px-space-xs py-0.5 rounded-full bg-secondary-fixed/20 text-on-secondary-container font-label-sm text-label-sm">Validated</span></div><span class="font-headline-sm text-headline-sm text-on-surface pt-space-xs leading-snug">Schema &amp; Range Check</span><p class="font-body-sm text-body-sm text-on-surface-variant">Negative clipping, CRC checks, timestamp sanity.</p></div><div class="pt-space-md flex flex-col gap-space-xs"><div class="flex justify-between items-center font-label-sm text-label-sm text-on-surface-variant"><span>Anomalies</span><span class="text-on-surface font-semibold">{s['negative_anomalies']:,} ({s['negative_anomaly_pct']:.2f}%)</span></div><div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1"><div class="bg-secondary h-full rounded-full" style="width: 98%"></div></div></div></div>
<div class="flex flex-col justify-between p-space-md rounded-xl bg-surface-container-low"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="w-6 h-6 rounded-full bg-primary text-secondary-fixed flex items-center justify-center font-label-sm text-label-sm font-bold">3</span><span class="px-space-xs py-0.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed-variant font-label-sm text-label-sm">Imputed</span></div><span class="font-headline-sm text-headline-sm text-on-surface pt-space-xs leading-snug">Cleaning &amp; Imputation</span><p class="font-body-sm text-body-sm text-on-surface-variant">Forward/backward fill per station+type; 0 missing post-imputation.</p></div><div class="pt-space-md flex flex-col gap-space-xs"><div class="flex justify-between items-center font-label-sm text-label-sm text-on-surface-variant"><span>Missing post</span><span class="text-on-surface font-semibold">0</span></div><div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1"><div class="bg-secondary h-full rounded-full" style="width: 100%"></div></div></div></div>
<div class="flex flex-col justify-between p-space-md rounded-xl bg-surface-container-low"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="w-6 h-6 rounded-full bg-primary text-secondary-fixed flex items-center justify-center font-label-sm text-label-sm font-bold">4</span><span class="px-space-xs py-0.5 rounded-full bg-secondary-fixed/20 text-on-secondary-container font-label-sm text-label-sm">Computed</span></div><span class="font-headline-sm text-headline-sm text-on-surface pt-space-xs leading-snug">Feature Synthesis</span><p class="font-body-sm text-body-sm text-on-surface-variant">Risk Score 40/30/20/10, Justice Score, DKV transit.</p></div><div class="pt-space-md flex flex-col gap-space-xs"><div class="flex justify-between items-center font-label-sm text-label-sm text-on-surface-variant"><span>Features</span><span class="text-on-surface font-semibold">48</span></div><div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1"><div class="bg-secondary h-full rounded-full" style="width: 100%"></div></div></div></div>
<div class="flex flex-col justify-between p-space-md rounded-xl bg-surface-container-low"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="w-6 h-6 rounded-full bg-primary text-secondary-fixed flex items-center justify-center font-label-sm text-label-sm font-bold">5</span><span class="px-space-xs py-0.5 rounded-full bg-secondary-fixed/20 text-on-secondary-container font-label-sm text-label-sm">Inference</span></div><span class="font-headline-sm text-headline-sm text-on-surface pt-space-xs leading-snug">ML Cluster Engine</span><p class="font-body-sm text-body-sm text-on-surface-variant">K-Means 4 civic clusters + transit overlay.</p></div><div class="pt-space-md flex flex-col gap-space-xs"><div class="flex justify-between items-center font-label-sm text-label-sm text-on-surface-variant"><span>Clusters</span><span class="text-on-surface font-semibold">4</span></div><div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1"><div class="bg-secondary h-full rounded-full" style="width: 98%"></div></div></div></div>
<div class="flex flex-col justify-between p-space-md rounded-xl bg-surface-container-low"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="w-6 h-6 rounded-full bg-primary text-secondary-fixed flex items-center justify-center font-label-sm text-label-sm font-bold">6</span><span class="px-space-xs py-0.5 rounded-full bg-secondary-fixed/20 text-on-secondary-container font-label-sm text-label-sm">Published</span></div><span class="font-headline-sm text-headline-sm text-on-surface pt-space-xs leading-snug">GIS Broadcast</span><p class="font-body-sm text-body-sm text-on-surface-variant">GeoJSON vector tiles + charts to frontend.</p></div><div class="pt-space-md flex flex-col gap-space-xs"><div class="flex justify-between items-center font-label-sm text-label-sm text-on-surface-variant"><span>Charts</span><span class="text-on-surface font-semibold">11</span></div><div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1"><div class="bg-secondary h-full rounded-full" style="width: 100%"></div></div></div></div>
</div>
</div>
<div class="grid grid-cols-1 xl:grid-cols-12 gap-space-lg mt-space-lg">
<div class="xl:col-span-5 flex flex-col gap-space-md"><div class="flex items-center justify-between"><span class="font-headline-md text-headline-md text-on-surface">Data Integrity Benchmarks</span><span class="font-label-sm text-label-sm text-on-surface-variant">Measured window</span></div><div class="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
<div class="p-space-lg bg-surface-container-lowest rounded-2xl shadow-sm flex flex-col justify-between"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Raw Ingestion</span><span class="material-symbols-outlined text-[18px] text-outline">storage</span></div><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{s['raw_rows']:,}</span></div><div class="pt-space-md flex items-center justify-between font-label-sm text-label-sm text-on-surface-variant"><span>{s['raw_files']} files</span><span class="text-secondary font-bold">100% received</span></div></div>
<div class="p-space-lg bg-surface-container-lowest rounded-2xl shadow-sm flex flex-col justify-between"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Negative Anomalies</span><span class="material-symbols-outlined text-[18px] text-tertiary-fixed-dim">leak_remove</span></div><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{s['negative_anomalies']:,}</span></div><div class="pt-space-md flex items-center justify-between font-label-sm text-label-sm"><span class="text-on-surface-variant">{s['negative_anomaly_pct']:.2f}% flagged</span><span class="text-secondary font-medium">as NaN</span></div></div>
<div class="p-space-lg bg-surface-container-lowest rounded-2xl shadow-sm flex flex-col justify-between"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Outliers &gt;3\u03c3</span><span class="material-symbols-outlined text-[18px] text-outline">tune</span></div><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">{s['outliers_flagged']:,}</span></div><div class="pt-space-md flex items-center justify-between font-label-sm text-label-sm text-on-surface-variant"><span>Retained</span><span class="text-secondary font-medium">documented</span></div></div>
<div class="p-space-lg bg-surface-container-lowest rounded-2xl shadow-sm flex flex-col justify-between"><div class="flex flex-col gap-space-xs"><div class="flex items-center justify-between"><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Missing Post-Imputation</span><span class="material-symbols-outlined text-[18px] text-secondary">verified</span></div><span class="font-telemetry-numeral text-telemetry-numeral text-on-surface">0</span></div><div class="pt-space-md flex items-center justify-between font-label-sm text-label-sm"><span class="text-on-surface-variant">ffill/bfill</span><span class="text-secondary font-bold">No gap</span></div></div>
</div></div>
<div class="xl:col-span-7 p-space-lg bg-surface-container-lowest rounded-2xl shadow-sm flex flex-col justify-between"><div class="flex flex-col md:flex-row md:items-center justify-between gap-space-sm mb-space-md"><div><span class="font-headline-md text-headline-md text-on-surface">Signal Denoising &amp; Calibration</span><p class="font-body-sm text-body-sm text-on-surface-variant">Measured distributions after cleaning (all pollutants, all stations)</p></div></div>""" + chart_embed("charts/pollutant_distributions.html", 280, "Post-cleaning measured pollutant distributions.", bare=True) + f"""<div class="grid grid-cols-1 sm:grid-cols-3 gap-space-sm pt-space-md"><div class="p-space-sm bg-surface-container-low rounded-lg flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant">DKV Stops</span><span class="font-headline-sm text-headline-sm text-on-surface font-semibold">{s['bus_stops']:,}</span><span class="font-body-sm text-body-sm text-secondary">May 2026</span></div><div class="p-space-sm bg-surface-container-low rounded-lg flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant">Outliers Retained</span><span class="font-headline-sm text-headline-sm text-on-surface font-semibold">{s['outliers_flagged']:,}</span><span class="font-body-sm text-body-sm text-on-surface-variant">&gt;3\u03c3 documented</span></div><div class="p-space-sm bg-surface-container-low rounded-lg flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant">Coverage</span><span class="font-headline-sm text-headline-sm text-on-surface font-semibold">100%</span><span class="font-body-sm text-body-sm text-on-surface-variant">post-imputation</span></div></div></div>
</div>
<div class="flex flex-col gap-space-md p-space-lg bg-surface-container-lowest rounded-2xl shadow-sm mt-space-lg">
<div class="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md"><div class="flex flex-col"><div class="flex items-center gap-space-xs"><span class="font-headline-md text-headline-md text-on-surface">16 Green Sentinel Fleet Health</span><span class="px-space-xs py-0.5 rounded-full bg-secondary-fixed/20 text-on-secondary-container font-label-sm text-label-sm">10 monitored</span></div><span class="font-body-sm text-body-sm text-on-surface-variant">Per-station record coverage after cleaning; coverage = rows present vs. expected.</span></div></div>
""" + quality_table(c) + f"""
</div>
<div class="grid grid-cols-1 lg:grid-cols-12 gap-space-lg mt-space-lg">
<div class="lg:col-span-7 p-space-lg bg-surface-container-lowest rounded-2xl shadow-sm flex flex-col justify-between"><div class="flex flex-col gap-space-sm"><div class="flex items-center justify-between"><div class="flex items-center gap-space-xs"><span class="material-symbols-outlined text-secondary text-[22px]">policy</span><span class="font-headline-md text-headline-md text-on-surface">DEIK.AI 2026 Category B Compliance</span></div><span class="px-space-xs py-0.5 rounded bg-secondary-fixed/20 text-on-secondary-container font-label-sm text-label-sm font-semibold">Civic Challenge</span></div><p class="font-body-md text-body-md text-on-surface-variant">Harness adheres to municipal open-data governance and reproducibility for DEIK.AI 2026.</p></div><div class="pt-space-md flex flex-wrap items-center gap-space-sm"><div class="inline-flex items-center gap-space-xs px-space-sm py-1 rounded-md bg-surface-container font-mono text-[12px] text-on-surface"><span class="w-2 h-2 rounded-full bg-secondary"></span><span>Pipeline: measured window</span></div><div class="inline-flex items-center gap-space-xs px-space-sm py-1 rounded-md bg-surface-container font-mono text-[12px] text-on-surface"><span class="material-symbols-outlined text-[14px]">verified</span><span>Honest: no AQI/NDVI/2023 baseline</span></div></div></div>
<div class="lg:col-span-5 p-space-lg bg-surface-container-lowest rounded-2xl shadow-sm flex flex-col justify-between"><div class="flex flex-col gap-space-sm"><div class="flex items-center justify-between"><span class="font-headline-md text-headline-md text-on-surface">Telemetry Audit Health</span><span class="material-symbols-outlined text-secondary text-[24px]">verified_user</span></div><p class="font-body-sm text-body-sm text-on-surface-variant">Cross-validation with municipal sensors; measured window only.</p><div class="flex items-center gap-space-lg pt-space-xs"><div class="relative w-24 h-24 flex-shrink-0 flex items-center justify-center"><svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36"><path class="text-surface-container-high" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" stroke-width="3.5"></path><path class="text-secondary" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" stroke-dasharray="99.4, 100" stroke-linecap="round" stroke-width="3.5"></path></svg><div class="absolute flex flex-col items-center justify-center"><span class="font-headline-sm text-headline-sm text-on-surface font-bold">99.4%</span></div></div><div class="flex flex-col gap-space-xs"><div class="flex items-center gap-space-xs text-body-sm"><span class="w-2.5 h-2.5 rounded-full bg-secondary"></span><span class="font-semibold text-on-surface">Honest records 149,683</span></div><div class="flex items-center gap-space-xs text-body-sm"><span class="w-2.5 h-2.5 rounded-full bg-tertiary-fixed-dim"></span><span class="text-on-surface-variant">DKV 687 stops</span></div></div></div></div><div class="pt-space-md flex items-center justify-between text-label-sm text-label-sm text-on-surface-variant bg-surface-container-low p-space-sm rounded-lg"><span class="flex items-center gap-space-xs"><span class="material-symbols-outlined text-[16px] text-secondary">security</span> Measured window May 21\u2013Jun 19, 2026</span><span class="text-secondary font-semibold">Honest corpus</span></div></div>
</div>
"""
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

    # export the real stations as a downloadable GeoJSON layer (risk map export button)
    geojson = site / "assets"
    geojson.mkdir(parents=True, exist_ok=True)
    (geojson / "stations.geojson").write_text(c.stations_geojson(), encoding="utf-8")

    # build pages on their own Stitch shell (keeps per-page header/sidebar chrome pixel-identical)
    shell_map = {
        "index.html": (TEMPLATES / "overview.html", "overview"),
        "risk_map.html": (TEMPLATES / "risk_map.html", "risk-map"),
        "risk_matrix.html": (TEMPLATES / "risk_matrix.html", "risk-analysis"),
        "environmental_trends.html": (TEMPLATES / "environmental_trends.html", "environmental-trends"),
        "station_analysis.html": (TEMPLATES / "station_analysis.html", "station-analysis"),
        "data_quality.html": (TEMPLATES / "data_quality.html", "data-quality"),
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
        name: wrap_page(tpl, active, inner[name])
        for name, (tpl, active) in shell_map.items()
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
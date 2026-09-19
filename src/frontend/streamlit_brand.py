"""GreenSense Debrecen streamlit branding (CSS + sidebar/hero markup).

Translates the Stitch design-system tokens from frontend/DESIGN.md onto the
Streamlit dashboard: Plus Jakarta Sans + Inter typography, deep-forest sidebar
shell, emerald accent and the civic semantic palette.
"""

from __future__ import annotations

BRAND_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700&display=swap');

    .stApp { font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif; background: #F8FAFC; }
    h1, h2, h3, .hero-title, .kpi-value { font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; }
    h1, h2, h3 { color: #0B1C30; letter-spacing: -0.02em; }

    /* ---------- Deep-forest sidebar shell (#0F2D1F) ---------- */
    [data-testid="stSidebar"] {
        background: #0F2D1F;
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    [data-testid="stSidebar"] * { color: #DDE9E0; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span { color: #DDE9E0; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.08); }
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-baseweb="multiselect"] { background: rgba(255,255,255,0.06); color: #FFFFFF; }
    [data-testid="stSidebar"] input { background: rgba(255,255,255,0.06); color: #FFFFFF; }

    .sb-brand { display: flex; align-items: center; gap: 12px; padding: 10px 2px 6px; }
    .sb-brand .sb-logo {
        width: 42px; height: 42px; border-radius: 12px; flex-shrink: 0;
        background: linear-gradient(135deg, #143D2B, #10B981);
        display: flex; align-items: center; justify-content: center; font-size: 22px;
    }
    .sb-brand .sb-name { font-weight: 800; font-size: 17px; color: #6ff1b4; line-height: 1.15; }
    .sb-brand .sb-sub { font-size: 11px; color: #b6ddc2; text-transform: uppercase; letter-spacing: 0.06em; }
    .sb-brand .sb-badge {
        display: inline-flex; margin-top: 4px; font-size: 10px; font-weight: 700;
        color: #6ffbbe; border: 1px solid rgba(111, 251, 190, 0.35);
        border-radius: 999px; padding: 1px 7px; text-transform: uppercase; letter-spacing: 0.05em;
    }

    /* ---------- side risk chips on dark shell ---------- */
    .risk-chip {
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14);
        color: #FFFFFF !important;
    }
    .risk-chip .dot { box-shadow: 0 0 6px rgba(0,0,0,0.35); }

    /* ---------- cards / hero ---------- */
    .hero {
        background: linear-gradient(120deg, #0F2D1F 0%, #143D2B 55%, #10B981 130%);
        box-shadow: 0 12px 28px rgba(15, 45, 31, 0.28);
    }
    .kpi-card { border: 1px solid #E2E8F0; border-radius: 16px; }
    .kpi-value { color: #0F2D1F; font-variant-numeric: tabular-nums; }
    .kpi-label { color: #64748B; }

    .footer { color: #64748B; }

    /* ---------- tabs ---------- */
    .stTabs [data-baseweb="tab"] { font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #0F2D1F !important; }

    /* ---------- buttons ---------- */
    .stButton button, [data-testid="stDownloadButton"] button {
        border-radius: 10px; font-weight: 600;
        border: 1px solid #0F2D1F; background: #0F2D1F; color: white;
    }
    .stButton button:hover, [data-testid="stDownloadButton"] button:hover {
        background: #143D2B; border-color: #143D2B; color: white;
    }
</style>
"""


def sidebar_brand() -> str:
    return """
    <div class="sb-brand">
        <div class="sb-logo">🌳</div>
        <div>
            <div class="sb-name">GreenSense</div>
            <div class="sb-sub">Debrecen · Debrecen</div>
            <span class="sb-badge">DEIK.AI 2026</span>
        </div>
    </div>
    """


def hero_html() -> str:
    return """
    <div class="hero">
        <div class="hero-emoji">🌳</div>
        <div>
            <div class="hero-title">GreenSense Debrecen — Environmental Intelligence</div>
            <div class="hero-sub">Civic Environmental Telemetry · DEIK.AI 2026</div>
            <div class="hero-tag">
                Analyzing the measured Green Sentinel monitoring window
                (May 21 – June 19, 2026) across 16 stations (10 with biodiversity
                records), combined with DKV transit connectivity, to spot
                environmental gentrification pressure before it displaces residents.
            </div>
        </div>
    </div>
    """
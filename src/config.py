import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
GREEN_SENTINEL_DIR = DATA_DIR / "green_sentinel" / "monitoring_2026-05-21_2026-06-19"
DKV_DIR = DATA_DIR / "dkv" / "databases" / "DKV databases"
BIODIVERSITY_DIR = DATA_DIR / "biodiversity"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"

DEBRECEN_CENTER = (47.53, 21.63)
MAP_ZOOM = 11

POLLUTANT_COLUMNS = ["PM2.5", "PM10", "NO2", "O3"]
AIR_POLLUTANTS = [
    "PM2.5", "PM10", "NO2", "O3", "TVOC",
    "CO", "CO2", "NO", "NOx",
    "Humidity", "Pressure", "Wind_Speed", "Wind_Direction",
]
GROUNDWATER_COLUMNS = ["Conductivity", "WaterLevel", "WaterTemp"]
NOISE_COLUMNS = ["LAEQ nappali", "LAEQ éjszakai"]

RISK_CATEGORY_COLORS = {
    "Emerging Green Zones": "#EF4444",
    "Established Clean Areas": "#10B981",
    "Stable Neighborhoods": "#FBBF24",
    "Challenge Zones": "#F97316",
}

RISK_BAND_COLORS = {
    "Critical": "#7F1D1D",
    "High": "#DC2626",
    "Moderate": "#F59E0B",
    "Low": "#10B981",
}

ANOMALY_THRESHOLD = 0
OUTLIER_SIGMA = 3
RANDOM_STATE = 42
N_CLUSTERS = 4

PM25_TARGETS = {
    "WHO Annual Guideline (5)": 5.0,
    "EU 2030 (10)": 10.0,
    "WHO 24h / IT-3 (15)": 15.0,
}
DEFAULT_PM25_TARGET = "WHO Annual Guideline (5)"
DAYS_PER_MONTH = 30.437

DATA_START = "2026-05-21"
DATA_END = "2026-06-19"

# ---------------------------------------------------------------------------
# Environmental Justice
# ---------------------------------------------------------------------------
BIODIVERSITY_FILES = {
    "inaturalist": "biodiversity_inaturalist.csv",
    "birds": "biodiversity_openbiomaps_birds.csv",
    "habitats": "biodiversity_padapt.csv",
}

# Documented competition Biodiversity Recovery Index weights (see
# BIODIVERSITY_DATASETS_README.md): species 40% / organisms 35% / birds 25%.
BIO_INDEX_WEIGHTS = {"species": 0.40, "organism": 0.35, "bird": 0.25}

# Documented competition Environmental Justice Score weights:
# 40% gentrification risk + 30% biodiversity + 20% transit + 10% pollution.
JUSTICE_WEIGHTS = {"risk": 0.40, "biodiversity": 0.30, "transit": 0.20, "pollution": 0.10}

CONSERVATION_QUALITY = {"excellent": 5, "good": 4, "moderate": 3, "poor": 2}
RESTORATION_LEVEL = {"very_high": 5, "high": 4, "medium": 3, "low": 2}

JUSTICE_BAND_COLORS = {
    "Excellent": "#065F46",
    "Good": "#10B981",
    "Moderate": "#F59E0B",
    "Needs Attention": "#EF4444",
}

# ---------------------------------------------------------------------------
# Historical maps (Cívis GIStory / Őrváros Közalapítvány) & gentrification watch
# ---------------------------------------------------------------------------
HISTORICAL_DIR = DATA_DIR / "historical"
HISTORICAL_YEARS = ["1999", "2020"]
HISTORICAL_MAINDIR = "/var/www/erda/html/projects/gistory/"
HISTORICAL_WMS_URL = "https://civisgistory.hu/common/php/ms_wms.php"
HISTORICAL_SESSION_URL = "https://civisgistory.hu/common/php/ms_session_keep.php"
HISTORICAL_LAYERS_URL = "https://civisgistory.hu/common/php/ms_layers_form.php"

# EOV (EPSG:23700) full-extent bounding box of the Cívis GIStory map area.
HISTORICAL_BBOX_EPSG23700 = (838718.8, 242859.1, 850279.7, 251053.4)
HISTORICAL_RASTER_WIDTH = 1600
HISTORICAL_RASTER_HEIGHT = 1130

# Curated "what was there in the 1990s" land-use labels, assigned from reading
# the 1999 Cívis GIStory base map plus known Debrecen geography. See
# data/historical/legacy_landuse.csv (source note in the file header).
LEGACY_CATEGORY_COLORS = {
    "industrial": "#EF4444",
    "railway_industrial": "#F97316",
    "old_town_core": "#8B5CF6",
    "socialist_estate": "#3B82F6",
    "research_campus": "#06B6D4",
    "forest": "#10B981",
    "agrarian_village": "#84CC16",
    "residential_edge": "#64748B",
}

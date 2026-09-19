# 🌍 Green Gentrification Index: Debrecen

Interactive dashboard for the **DEIK.AI Challenge 2026 — Category B (Urban Environmental Monitoring)**.
Identifies neighborhoods under **environmental gentrification pressure** in Debrecen by combining
30 days of real **Green Sentinel** air-quality monitoring (16 stations) with **DKV** transit connectivity data.

**Story:** neighborhoods that are cleaning up fastest *and* stay well-connected by public transport
are the most exposed to gentrification pressure — and need affordable-housing protection *before* developers arrive.

---

## 🚀 Quickstart

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the dashboard
streamlit run app.py
# Opens: http://localhost:8501
```

### One-shot pipeline (process everything + save outputs)

```bash
python run_pipeline.py
```

### Notebooks

```bash
jupyter notebook notebooks/01_data_exploration.ipynb
```

---

## 📁 Project Structure

```
green_gentrification_index/
├── app.py                  # Streamlit dashboard (5 tabs)
├── run_pipeline.py         # End-to-end data → model → outputs
├── smoke_test.py           # Headless dashboard smoke test
├── requirements.txt
├── README.md
├── METHODOLOGY.md          # How gentrification risk is computed
├── .streamlit/config.toml  # Dashboard theme
│
├── data/
│   ├── green_sentinel/     # Raw Excel files (16 stations × 3 sensor families)
│   ├── dkv/                # DKV bus stops, schedules, monthly statistics
│   └── processed/          # Cleaned parquet/csv intermediates
│
├── src/
│   ├── config.py           # Paths & constants
│   ├── pipeline.py         # DataPipeline (register/load datasets)
│   ├── loaders/
│   │   ├── base_loader.py          # Abstract loader contract
│   │   ├── green_sentinel_loader.py# 16-station environmental loader
│   │   └── dkv_loader.py           # Transit loader + accessibility features
│   ├── processors/
│   │   ├── data_cleaner.py         # Anomalies, imputation, outliers
│   │   └── feature_engineer.py     # Trends, improvement index, volatility
│   ├── models/
│   │   └── gentrification_model.py # K-means (k=4) + auto-labelling
│   └── visualizations/
│       ├── map_viz.py              # Folium map + Plotly scatter
│       ├── trend_charts.py         # Time series, bars, box plots
│       └── risk_matrix.py          # Improvement vs pollution quadrant
│
├── notebooks/              # 01 exploration · 02 EDA · 03 validation
└── output/
    ├── processed_data/     # Cleaned data & quality report
    ├── models/             # Clustering results + metrics
    ├── visualizations/     # Interactive HTML exports
    └── competition_submission/
```

---

## 🗺️ Dashboard Tabs

| Tab | What it shows |
|-----|---------------|
| 🗺️ **Risk Map** | Folium map of all 16 stations; marker size = improvement magnitude, colour = risk category |
| 📈 **Pollution Trends** | 30-day pollutant time series (multi-select stations), improvement-index bar chart |
| ⚠️ **Risk Matrix** | Improvement vs. current pollution quadrant plot (colour = risk, bubble = volatility) |
| 📊 **Detailed Analysis** | Per-station deep dive: all pollutants, weather context, summary stats |
| 🔍 **Data Quality** | Anomaly statistics, per-station quality table, methodology notes |

---

## 🎯 Key Results (monitoring period May 21 – Jun 19, 2026)

- **~149,700** raw measurements across 16 stations, cleanly standardised into a single long table.
- 30-day **linear-regression trends** per pollutant per station → composite **environmental improvement index**.
- **K-means clustering (k=4)** → 4 defensible risk categories:
  1. **Emerging Green Zones** 🔴 — fast improvement + still polluted = **gentrification risk**
  2. **Established Clean Areas** 🟢 — already clean/developed
  3. **Stable Neighborhoods** 🟡 — no major change
  4. **Challenge Zones** 🟠 — degrading + polluted, needs help first
- **Transit accessibility** (DKV): # bus stops within 1 km per station, surfaced as the connectivity signal.

---

## 🧪 Testing

```bash
# Headless dashboard smoke test (runs every widget through Streamlit AppTest)
python smoke_test.py

# Recompute everything and write outputs/
python run_pipeline.py
```

### Roadmap (post-competition)

- DKV service-schedule frequency layer (weekly departures per station).
- Biodiversity datasets (iNaturalist, OpenBioMaps, PADAPT).
- External air-quality validation (legszennyezettseg.met.hu).
- Monthly automated refresh + reports.

---

*Competition deadline: September 25, 2026*
# Methodology — Green Gentrification Index

This document explains exactly how the gentrification-risk score is computed so that
every claim on the dashboard can be audited and every cleaning decision is transparent.

## 1. Data Sources

| Source | Coverage | Content |
|--------|----------|---------|
| **Green Sentinel** | 16 stations, May 21 – Jun 19, 2026 | Hourly PM2.5, PM10, NO2, O3, TVOC, CO, CO2, NO, NOx, humidity, pressure, wind; groundwater; noise |
| **DKV** | 687 bus stops, May 2026 statistics | Stop coordinates, monthly boarding/alighting |

The Green Sentinel raw files are long-format Excel sheets with Hungarian column names
(`Mérőeszköz` = measurement type, `érték` = value, `mértékegység` = unit). They are
renamed, timestamp-parsed, and standardised into an 8-column schema.

## 2. Cleaning Decisions (documented anomalies)

1. **Negative measurements** (sensor drift / calibration errors) → flagged and replaced with `NaN`.
   In this monitoring window **0 negatives** were found.
2. **Missing values** → forward-fill then backward-fill **within each (station, measurement type)** group,
   with a maximum gap of 3 timestamps. This preserves temporal continuity without mixing neighbourhoods.
3. **Outliers** (>3σ from the measurement-type mean) → **flagged but retained**, because extremes can be
   real pollution episodes.
4. **Unit standardisation** → all concentrations kept in `µg/m³`; humidity `%`; pressure `mbar`;
   wind `km/h`; water `m` / `mS/cm` / `°C`; noise `dB`.

## 3. Feature Engineering

All features are computed **per station** from daily means (hourly → daily aggregation).

### 3.1 Environmental improvement index

For each key pollutant (`PM2.5`, `PM10`, `NO2`, `O3`) the **30-day linear-regression slope**
is computed with `scipy.stats.linregress`:

```
slope > 0  → pollution increasing (getting worse)
slope < 0  → pollution decreasing (improving)
```

The composite index is the negative mean of the four slopes:

```
env_improvement_index = -1 * mean(slope_pm25, slope_pm10, slope_no2, slope_o3)
```

> `index > 0` = conditions improving; `index < 0` = degrading. Magnitude = trend strength.

### 3.2 Current pollution level

Mean concentration over the **final 7 days** of the window per station (`current_PM2.5`, …).
High values + strong improvement signal = gentrification potential.

### 3.3 Volatility

Standard deviation of daily `PM2.5` over the 30-day window (`pm25_volatility`) — a reliability
and event-consistency signal.

### 3.4 Transit accessibility (DKV)

For each station, count of bus stops within **1 km** (`bus_stops_nearby`) and distance to the
nearest stop. Used as the **connectivity** component of gentrification pressure.

## 4. Risk Clustering (ML)

Features for the K-means model (per the competition spec):

| Feature | Meaning |
|---------|---------|
| `env_improvement_index` | 30-day improvement trend |
| `current_PM2.5` | Latest pollution level |
| `pm25_volatility` | Air-quality consistency |

- `StandardScaler` pre-processing.
- `KMeans(n_clusters=4, random_state=42, n_init=10)`.
- Fit on **16 rows** (one per station).

### Auto-labelling

Each cluster is labelled distinctly by ranking clusters on their centroids:

| Improvement rank | Pollution rank | Label |
|------------------|----------------|-------|
| High | High | **Emerging Green Zones** 🔴 (gentrification risk) |
| High | Low  | **Established Clean Areas** 🟢 |
| Low  | High | **Challenge Zones** 🟠 (needs help first) |
| Low  | Low  | **Stable Neighborhoods** 🟡 |

Because all 16 stations were improving during this window, labels are assigned **relatively**
(median-split), which is disclosed and documented rather than hiding the finding.

## 5. Gentrification Risk Score (0–100)

A quantified, weighted score per station — **not** the cluster label, but an actionable
ranking built from four normalized components:

```
Risk Score = 0.40 x improvement + 0.30 x pollution + 0.20 x transit + 0.10 x stability
```

Each component is **min-max normalized across the 16 monitored stations** (not against
fixed literature ranges), because the observed data lie well outside the brief's assumed
references (composite improvement index 0.47–1.01 vs. a ±0.5 slope range; daily PM2.5 means
2.1–6.3 µg/m³ vs. a 15–80 µg/m³ range). Min-max scaling guarantees a usable 0–100 spread and
stable, reproducible ranking.

| Component | Weight | Source feature | Higher score when… |
|-----------|--------|----------------|--------------------|
| Improvement | 40% | `env_improvement_index` | air is improving faster |
| Pollution   | 30% | `current_PM2.5`        | current level is higher |
| Transit     | 20% | `bus_stops_nearby`     | more bus stops within 1 km |
| Stability   | 10% | `pm25_volatility`      | volatility is lower (inverted score) |

### Interpretation bands

| Band       | Range | Meaning |
|------------|-------|---------|
| Low        | 0–30  | Low gentrification pressure (already good, stable) |
| Moderate   | 31–60 | Watch carefully |
| High       | 61–80 | **Priority for affordable housing** |
| Critical   | 81–100 | Act now |

### Notes on honesty

- A station can rank high on the pure risk score while being classed "Established Clean"
  by clustering (e.g. DEB-KER12 improves fastest and has high PM2.5 → 76/100, but 0 bus
  stops). The dashboard's recommendations flag such cases with "low transit access →
  monitor, not urgent action".
- Weights and per-metric min/max bounds are persisted in `output/models/model_metrics.json`.

## 5b. Clean-Air Timeline (months until target)

The intention of the brief was a "months to clean air" extrapolation per station. Because
the standard brief references (PM2.5 15–80 µg/m³) do not occur in this monitoring window
(daily means were 2–6 µg/m³), the dashboard implements the mechanism honestly:

**Inputs per station**
- `current_PM2.5` — mean over the final 7 days of the window.
- `pm25_trend` — the 30-day linear-regression slope of daily PM2.5 in **µg/m³ per day**
  (already computed during feature engineering).

**Formula** (linear extrapolation; calendar month = 30.437 days):

```
months_to_target = (current_PM2.5 - target) / (|slope| × 30.437)
target_date       = 2026-06-19 + months_to_target × 30.437 days
```

**Target standard (default):** WHO annual (2021) Air Quality Guideline **5 µg/m³** — the
only standard with a real gradient here, since every station already meets WHO 24h/IT-3
15 µg/m³ and the EU-2030 10 µg/m³ limit.

**Status**
| Status | Condition | Meaning |
|--------|-----------|---------|
| Already met | `current ≤ target` | 0 months |
| On track | `current > target`, slope < 0 | extrapolated months shown |
| Not on track | slope ≥ 0 | flat/rising — no date |

**Caveats disclosed on the dashboard**
- Linear extrapolation of a 30-day snapshot; no seasonality or policy effects modelled.
- Long horizons (e.g. 8 months at a near-zero slope) are less reliable than short ones.
- The brief's worked example (38–45 µg/m³, 18–40 months) is illustrative and does not
  match this dataset; it is reproduced nowhere as a result.

## 6. Validation

- Trend slopes verified against manual `linregress` on one station (see notebook 03).
- Clustering stability checked over 20 random seeds (Adjusted Rand Index).
- All coordinates validated within the Debrecen bounding box (~47.4–47.6°N, 21.5–21.9°E).
- No train/test split is used — the model is unsupervised and purely descriptive.

## 6. Reproducibility

```bash
python run_pipeline.py
# -> output/processed_data/        cleaned data + quality report
# -> output/models/                clustering_results.csv + model_metrics.json
# -> output/visualizations/        interactive HTML exports
```

Seeds are fixed (`random_state=42`) and all cleaning decisions are logged in the quality report.
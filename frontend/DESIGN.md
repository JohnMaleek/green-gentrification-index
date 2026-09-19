---
name: Urban Environmental Intelligence
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#424844'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#727973'
  outline-variant: '#c2c8c2'
  surface-tint: '#476554'
  primary: '#00170c'
  on-primary: '#ffffff'
  primary-container: '#0f2d1f'
  on-primary-container: '#769683'
  inverse-primary: '#adceb9'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#001524'
  on-tertiary: '#ffffff'
  tertiary-container: '#002a44'
  on-tertiary-container: '#2e95da'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c9ebd5'
  primary-fixed-dim: '#adceb9'
  on-primary-fixed: '#022113'
  on-primary-fixed-variant: '#2f4d3d'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#93ccff'
  on-tertiary-fixed: '#001d31'
  on-tertiary-fixed-variant: '#004b73'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  telemetry-numeral:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: -0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 1.5rem
  margin-desktop: 2.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system embodies an authoritative, scientific, and civic-forward posture tailored for municipal leaders, ecological researchers, and citizens. The visual narrative combines the structural discipline of high-density environmental monitoring with the modern polish of executive decision consoles.

The core aesthetic draws on **Modern Corporate Minimalism** infused with **Tonal Environmental Layering**. It avoids generic ecological clichés (such as literal leaf icons, pastel organic shapes, or raw paper textures) in favor of high-precision sensor telemetry, structured geospatial dashboards, and clinical data hierarchy.

### Core Principles
- **Scientific Exactitude:** Metrics, indices (AQI, NDVI, microclimate variance), and spatial records command visual priority through clear numerical scales and zero-fluff data framing.
- **Civic Trust & Gravitas:** Deep, institutional forest greens frame the viewport, providing an anchor of governance and permanence, while bright emerald highlights active metrics and vitality.
- **High-Density Clarity:** Information architecture supports rapid scanning across multiple sensor clusters, comparative temporal graphs, and municipal zone categorizations without cognitive friction.

## Colors

The palette establishes an immediate tension between the deep, authoritative structure of municipal governance and high-luminance environmental status markers.

### Palette Architecture
- **Primary Canvas & Chrome:**
  - Base App Background: `#F8FAFC` (Canvas Light) and `#F1F5F9` (Subtle Recessed Wells).
  - Primary Structural Anchors: `#0F2D1F` (Deep Forest Base) and `#143D2B` (Forest Container/Sidebar Elevation).
  - Primary Contrast Typography: `#0F172A` (Primary Dark Charcoal) and `#1E293B` (Secondary Deep Slate).
  - Secondary Demarcation & Supporting Copy: `#64748B` (Muted Slate) and `#94A3B8` (Border/Inactive Tone).

- **Ecological Action & Accents:**
  - Active Accent / Telemetry Vibrant: `#10B981` (Vibrant Emerald Green).
  - Interactive Hover / Focus Dark Emerald: `#059669`.

- **Semantic Zone & Telemetry Colors:**
  - **Established Clean Area:** `#10B981` (Emerald) with soft backing `#ECFDF5`.
  - **Stable Neighborhood:** `#F59E0B` (Warm Amber) with soft backing `#FFFBEB`.
  - **Challenge Zone:** `#F97316` (Energetic Coral/Orange) with soft backing `#FFF7ED`.
  - **Emerging Green Zone / Critical Alert:** `#E11D48` to `#BE123C` (Ruby Crimson) with soft backing `#FFF1F2`.
  - **Transit Integration (DKV Telemetry):** `#0284C7` (Municipal Transit Cyan/Blue) with soft backing `#F0F9FF`.

Maintain strict WCAG AAA contrast for body copy on `#F8FAFC` surfaces using `#0F172A`, and minimum AA for data visualization glyphs against their container baselines.

## Typography

The typographic system pairs the humanist, geometric precision of **Plus Jakarta Sans** for structural headers and municipal milestones with the neutral, hyper-legible neutrality of **Inter** for dense sensor feeds, data cards, and telemetry scales.

### Guidelines
- **Tabular Numerics:** All dynamic counters, sensor readings (PPM, µg/m³, °C, % humidity), and coordinates must enforce CSS `font-variant-numeric: tabular-nums` to eliminate layout jitter during real-time streaming updates.
- **Metric Micro-Labels:** Use `label-sm` with uppercase transforms and subtle letter-spacing (`0.04em`) when naming telemetry attributes (e.g., `PM2.5 SENSOR DELTA`, `NDVI CANOPY RATIO`).
- **Hierarchy Stacking:** Pair large tabular numerals directly with subordinate `label-sm` units below them to maintain maximum scan density without bloating component heights.

## Layout & Spacing

The platform is engineered around a 12-column fluid grid system with strict, uniform vertical rhythms designed for responsive analytics layouts.

### Screen Adaptations
- **Desktop (≥ 1280px):** 12 columns, `gutter-desktop` (1.5rem / 24px), outer canvas margins of 2.5rem (40px). Side rails for spatial filters and multi-chart telemetry sidebars lock into 3- or 4-column spans, while real-time map views or cluster matrices occupy the remaining 8 or 9 columns.
- **Tablet (768px – 1279px):** 8 columns, `gutter` (1rem / 16px), margins of 1.5rem (24px). Analytical sidebars collapse into sticky top summary ribbons or sliding slide-over drawers.
- **Mobile (< 768px):** 4 columns, `gutter` (1rem / 16px), margins of 1rem (16px). Cards reflow into single-column vertical stacks. Tabular telemetry shifts to compact, dual-metric split cards.

### Spacing Density Principles
Internal card padding maintains an efficient `space-lg` (1.5rem) on macro cards and `space-md` (1rem) on micro monitoring widgets. Gaps between related inline badges or sensor indicators strictly use `space-xs` (4px) or `space-sm` (8px) to reflect connected environmental dimensions.

## Elevation & Depth

Visual hierarchy relies on structural tonal separation rather than heavy, distracting drop shadows. The design achieves depth through crisp micro-borders and soft ambient diffusion.

### Depth Hierarchy
1. **Level 0 (App Canvas):** Flat `#F8FAFC` base layer.
2. **Level 1 (Card & Module Containers):** Surface fill `#FFFFFF` enclosed by a crisp, low-contrast border (`1px solid rgba(226, 232, 240, 0.8)` or `border-slate-200/80`). Shadow is minimal and cool-tinted: `0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.02)`.
3. **Level 2 (Active Cards, Hover States & Flyouts):** Surface fill `#FFFFFF`, border shifts to `rgba(203, 213, 225, 0.9)`, elevation lifts with an ambient spread: `0 10px 15px -3px rgba(15, 23, 42, 0.05), 0 4px 6px -4px rgba(15, 23, 42, 0.03)`.
4. **Level 3 (Modal Dialogs & Spatial Inspector Drawers):** `0 20px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04)`.
5. **Level 4 (Executive Forest Shell / Side Navigation):** Solid background of `#0F2D1F` with inner column division lines formed by `1px solid rgba(255, 255, 255, 0.08)`.

## Shapes

The interface balances welcoming civic aesthetics with data-dense technical geometry through a progressive corner-radius architecture:

- **Macro Containers & Analytical Cards:** Apply `rounded-2xl` (1rem / 16px) to major cards, telemetry clusters, and modal enclosures. This softens the high density of numerical data and charts.
- **Micro UI Controls (Buttons, Inputs, Pill Tabs):** Standardized to `0.5rem` (8px) or `rounded-lg` to retain tactile affordance and tight alignment with data grids.
- **Telemetry Chips & Sensor Indicators:** Fully rounded (`rounded-full` / pill) to instantly demarcate categorical state from rectangular data inputs.

## Components

### 1. Cards
- **Structure:** Surface `#FFFFFF`, border `1px solid rgba(226, 232, 240, 0.8)`, radius `rounded-2xl`, padding `1.5rem`.
- **Telemetry Card Pattern:** Features an upper meta header (`label-sm` in slate `#64748B`), a primary metric row with a prominent `telemetry-numeral` (`#0F172A`), an inline semantic trend badge, and a footer micro-sparkline or mini-bar comparison.

### 2. Buttons
- **Primary:** Background `#0F2D1F`, text `#FFFFFF`, radius `0.5rem`, padding `0.625rem 1.25rem`. Hover state transitions to `#143D2B` with a subtle elevation shift. Focus ring: `2px solid #10B981` offset by `2px`.
- **Secondary / Action Emerald:** Background `#10B981`, text `#FFFFFF`. Hover state `#059669`.
- **Subtle / Ghost:** Background `transparent`, text `#1E293B`, border `1px solid #E2E8F0`. Hover state backgrounds to `#F1F5F9`.

### 3. Status Badges & Chips
- **Geometry:** Height 24px, radius `9999px`, horizontal padding `8px`, typography `label-sm`.
- **Semantic Matrix:**
  - *Established Clean Area:* Emerald text `#059669`, background `#ECFDF5`, border `1px solid rgba(16, 185, 129, 0.2)`.
  - *Stable Neighborhood:* Amber text `#D97706`, background `#FFFBEB`, border `1px solid rgba(245, 158, 11, 0.2)`.
  - *Challenge Zone:* Coral text `#EA580C`, background `#FFF7ED`, border `1px solid rgba(249, 115, 22, 0.2)`.
  - *Emerging Green Zone / Urgent:* Ruby text `#BE123C`, background `#FFF1F2`, border `1px solid rgba(225, 29, 72, 0.2)`.
  - *Transit Telemetry (DKV):* Cyan text `#0284C7`, background `#F0F9FF`, border `1px solid rgba(2, 132, 199, 0.2)`.

### 4. Input Fields & Select Controls
- **Structure:** Height 40px, surface `#FFFFFF`, border `1px solid #CBD5E1`, radius `0.5rem`, text `#0F172A`, placeholder `#94A3B8`.
- **States:** Active/focus draws an immediate border highlight of `#10B981` and a soft ambient focus ring (`0 0 0 3px rgba(16, 185, 129, 0.15)`).

### 5. Selection Controls (Checkboxes & Radios)
- **Checkboxes:** 18px × 18px, radius `4px`, border `1.5px solid #94A3B8`. When checked: fill `#0F2D1F` with a crisp white check glyph.
- **Radio Buttons:** 18px × 18px circle, checked state displays an exterior ring `#0F2D1F` with an internal 6px dot `#10B981`.

### 6. Environmental Index Sparklines & Area Charts
- **Rules:** Stroke widths are set to exactly `2px`. Fill gradients transition from semantic source colors (e.g., `#10B981` or `#E11D48`) at `20%` opacity at the peak down to `0%` opacity at the X-axis baseline. Grid lines use dashed `1px solid #E2E8F0`.
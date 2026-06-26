# SciScore Journal Dashboard — Handover

## Live site

https://martijnroelandse.github.io/sciscore-dashboard/SciScore_journal_dashboard.html

Deployed via GitHub Pages from `main`.

## Original vision (three options)

| # | Approach | Status |
|---|----------|--------|
| 1 | Google Sheet + Apps Script → Slides | Skipped — PPTX export in dashboard covers meeting workflow |
| 2 | Self-contained HTML dashboard | **Built** |
| 3 | Live Cowork/BigQuery dashboard | Future prototype |

## Features

| Feature | Status |
|---------|--------|
| Publisher group filter (43 groups, sales-facing rollups) | Done |
| **Aggregated publisher/group dashboard** (portfolio RTI, trends, journal table) | Done |
| Publisher filter + journal search | Done |
| Hero RTI metric + collapsible detail panels | Done |
| RTI trend, study design radar, resource bars | Done |
| PPTX export (publisher or whole group) | Done |
| GitHub Pages hosting | Done |

## Aggregated publisher dashboard

When a **publisher** or **publisher group** is selected (and no journal is selected), the main panel shows a portfolio overview:

- Paper-weighted portfolio RTI and KPIs for the selected year
- RTI trend across years (all journals combined)
- Aggregated study design radar and resource findability bars
- Ranked journal table — click any row to drill down
- **← overview** breadcrumb when viewing a single journal

Metrics are weighted by paper count per journal per year.

## Publisher groups

`GROUP_MAP` in the HTML maps 537 publishers → 43 groups. Major rollups:

- Springer Nature, Elsevier, Wiley (+ Hindawi), Taylor & Francis, SAGE, Wolters Kluwer, Oxford, etc.
- US Society & Association Publishers (24 societies)
- Independent & Society Publishers (small publishers bucket)
- Publishers with ≥5 journals keep their own group name

To adjust groupings, edit `scripts/group_map.json` (see also `normalize_data.py` for Springer Nature sub-brand rules).

## PPTX export

- Select a **publisher** or **publisher group**, then click **Export Report**.
- Lazy-loads PptxGenJS from `pptxgen.bundle.js` (not `bundled.js` — that URL 404s).
- Uses **SciScore slide masters** (navy header, blue accent, footer logo) from `design/` branding assets.
- Deck structure: title → **portfolio overview** (RTI + trend) → **study design & resources** → **journal rankings** → per journal: **RTI timeline** + latest-year detail slide.
- Group export: all journals in the group, sorted by RTI.

### Branding (`design/` + template)

Place assets in the repo, then run:

```bash
python3 scripts/embed_brand_assets.py
```

| Path | Purpose |
|------|---------|
| `SciScore template.pptx` (repo root) or `design/*template*.pptx` | Source template — theme colours extracted |
| `Design/` or `design/logos/` | Logo PNG/SVG (SciScore white/black variants for slides) |
| `Design/PNGs for slides/` or `design/icons/` | Metric icons (matched by filename) |

The script writes `scripts/brand_config.json` and patches `BRAND_CONFIG` into the HTML (embedded base64 for small images). At export time, any remaining assets are fetched from `design/` on GitHub Pages.

**Note:** PptxGenJS cannot import an existing `.pptx` as-is; the template is used to extract colours/logos, and slide masters are defined to match SciScore branding.

## How to run locally

```bash
open SciScore_journal_dashboard.html
# or
python3 -m http.server 8080
```

## Regenerating after data update

Place `data/2026_sciscore_v3.csv` (export of the xlsx `by_journal_by_year` tab) or the full `2026_sciscore_v3.xlsx` in `data/`. Tracked in git: `2026_sciscore_v3.csv`, `2026_sciscore_v3 - by_year.csv`, and `ext_list_May_2026.csv`. The xlsx stays local (gitignored).

1. Embed journal metrics from CSV:

```bash
python3 scripts/embed_journal_data.py
python3 scripts/inspect_xlsx.py   # optional: audit columns and year range
```

2. Run `python3 scripts/normalize_data.py` to deduplicate journal names and split Springer Nature into BMC / Nature Portfolio / Springer Nature sub-publishers.

3. Place `2026_sciscore_v3.xlsx` in `data/` (must include a `by_year` sheet with all-journal averages). Install `openpyxl` if needed, then embed benchmarks:

```bash
pip install openpyxl
python3 scripts/embed_benchmarks.py
```

4. Apply UI patches for dynamic year range and open-science metrics:

```bash
python3 scripts/patch_extended_metrics_ui.py
```

The embed script verifies that `const GROUP_MAP` is still present after writing — if embed truncates the HTML, restore from git and re-run.

### Data normalization (`normalize_data.py`)

- **Journal deduplication:** merges case-insensitive duplicates (e.g. `Blood Research` / `Blood research`) into one entry; year data is kept from the row with more papers per year; canonical name prefers title case.
- **Springer Nature sub-brands:** journals formerly under publisher `Springer Nature` are reassigned by journal name prefix — `BMC …` → BMC, `Nature …` / `Nature` → Nature Portfolio, remainder → Springer Nature. All roll up to the **Springer Nature** publisher group via `scripts/group_map.json`.
- **Springer Publishing Company** is not part of Springer Nature (removed from that group).

To adjust groupings, edit `scripts/group_map.json` and re-run `normalize_data.py` or `patch_dashboard.py` as needed.

## Path to Option 3

1. Scheduled SQL from `2026_sciscore_v3` → BigQuery/API
2. Replace embedded JSON with `fetch()` on load
3. Add `publisher_grouped` column from Sheet as source of truth for GROUP_MAP
4. Cowork artifact: same UI, live data

## JMIR 2022 country & institution dashboards (separate platform)

These dashboards use the **2022 JMIR paper corpus** — intentionally **separate** from the journal dashboard while that is under external editor review. A new SciScore v3 dataset will replace this in a future release; do not merge the two data sources on one page yet.

| Dashboard | URL (GitHub Pages) | Data source |
|-----------|-------------------|-------------|
| Country | `SciScore_country_dashboard.html` | `data/jmir_*_by_country_by_year.csv` |
| Institution | `SciScore_institution_dashboard.html` | `data/jmir_*_by_institution_by_year.csv` + optional ROR |

### Regenerating JMIR dashboards

```bash
# Country (175 countries, 1997–2020)
python3 scripts/build_country_dashboard.py

# ROR matching (institutions) — local dump by default (fast, no rate limits)

```bash
# First run downloads ~34 MB ROR dump from Zenodo into data/ror_cache/
python3 scripts/match_ror.py

# Options
python3 scripts/match_ror.py --sample 100     # quick test
python3 scripts/match_ror.py --resume          # skip already-matched keys
python3 scripts/match_ror.py --api             # legacy: public API (rate-limited)
python3 scripts/match_ror.py --download        # force re-download ROR dump
```

# Institution dashboard (embeds ROR from data/ror_matches.json when present)
python3 scripts/build_institution_dashboard.py
```

Review unmatched institutions in `data/ror_match_review.csv`. ROR hierarchy (parent/child) is shown on institution profiles when relationships exist in the registry.

### JMIR pipeline files

```
scripts/entity_data_io.py           # JMIR CSV → shared metric keys
scripts/entity_benchmarks.py        # corpus-wide BY_YEAR_BENCHMARK
scripts/entity_dashboard_shell.py   # HTML/CSS/JS generator
scripts/build_country_dashboard.py
scripts/build_institution_dashboard.py
scripts/match_ror.py                # ROR matching (local dump default; --api for public API)
scripts/ror_local.py              # local ROR index builder + matcher
data/ror_matches.json               # generated ROR enrichments
data/ror_match_review.csv           # match audit for manual review
```

## Key files

```
SciScore_journal_dashboard.html   # app + embedded data (v3 — editor review)
SciScore_country_dashboard.html   # JMIR 2022 country dashboard
SciScore_institution_dashboard.html  # JMIR 2022 institution + ROR
design/                           # template PPTX, logos, icons
scripts/embed_brand_assets.py     # extract branding → HTML
scripts/brand_config.json         # generated brand manifest
scripts/normalize_data.py         # dedupe journals + SN sub-brands
scripts/group_map.json            # publisher → group mappings
scripts/patch_dashboard.py        # GROUP_MAP + UI patcher
scripts/patch_extended_metrics_ui.py  # dynamic years + open-science UI
scripts/embed_journal_data.py     # CSV → const DATA
scripts/journal_data_io.py        # read/parse 2026_sciscore_v3 export
scripts/inspect_xlsx.py           # audit source columns and year range
HANDOVER.md                       # this file
```

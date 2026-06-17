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
- Deck structure: title → **portfolio overview** (RTI, trend chart, study design & resources) → **journal rankings** → per journal: **RTI timeline** + latest-year detail slide.
- Group export: all journals in the group, sorted by RTI.

### Branding (`design/` + template)

Place assets in the repo, then run:

```bash
python3 scripts/embed_brand_assets.py
```

| Path | Purpose |
|------|---------|
| `design/*template*.pptx` | Source template — theme colours and embedded media are extracted |
| `design/logos/` | Logo PNG/SVG (white/reverse variant for title slide, colour for content footer) |
| `design/icons/` | Optional metric icons (matched by filename: sex, random, antibody, tool, …) |

The script writes `scripts/brand_config.json` and patches `BRAND_CONFIG` into the HTML (embedded base64 for small images). At export time, any remaining assets are fetched from `design/` on GitHub Pages.

**Note:** PptxGenJS cannot import an existing `.pptx` as-is; the template is used to extract colours/logos, and slide masters are defined to match SciScore branding.

## How to run locally

```bash
open SciScore_journal_dashboard.html
# or
python3 -m http.server 8080
```

## Regenerating after CSV update

1. Replace embedded `DATA` in the HTML (from `2026_sciscore_v3` enriched CSV).
2. Run `python3 scripts/normalize_data.py` to deduplicate journal names and split Springer Nature into BMC / Nature Portfolio / Springer Nature sub-publishers.
3. Run `python3 scripts/patch_dashboard.py` to re-apply GROUP_MAP and UI code.

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

## Key files

```
SciScore_journal_dashboard.html   # app + embedded data
design/                           # template PPTX, logos, icons
scripts/embed_brand_assets.py     # extract branding → HTML
scripts/brand_config.json         # generated brand manifest
scripts/normalize_data.py         # dedupe journals + SN sub-brands
scripts/group_map.json            # publisher → group mappings
scripts/patch_dashboard.py        # GROUP_MAP + UI patcher
HANDOVER.md                       # this file
```

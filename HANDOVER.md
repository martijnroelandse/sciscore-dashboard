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

To adjust groupings, edit `scripts/patch_dashboard.py` (`EXPLICIT` dict) and re-run the patch.

## PPTX export

- Select a **publisher** or **publisher group**, then click **Export Report**.
- Lazy-loads PptxGenJS from `pptxgen.bundle.js` (not `bundled.js` — that URL 404s).
- Group export: all journals in the group, one slide each, sorted by RTI.

## How to run locally

```bash
open SciScore_journal_dashboard.html
# or
python3 -m http.server 8080
```

## Regenerating after CSV update

1. Replace embedded `DATA` in the HTML (from `2026_sciscore_v3` enriched CSV).
2. Run `python3 scripts/patch_dashboard.py` to re-apply GROUP_MAP and UI code.

## Path to Option 3

1. Scheduled SQL from `2026_sciscore_v3` → BigQuery/API
2. Replace embedded JSON with `fetch()` on load
3. Add `publisher_grouped` column from Sheet as source of truth for GROUP_MAP
4. Cowork artifact: same UI, live data

## Key files

```
SciScore_journal_dashboard.html   # app + embedded data
scripts/patch_dashboard.py        # GROUP_MAP + UI patcher
HANDOVER.md                       # this file
```

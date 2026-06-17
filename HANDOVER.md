# SciScore Journal Dashboard — Handover

## Original vision (three options)

| # | Approach | Lift | Status |
|---|----------|------|--------|
| 1 | **Google Sheet** + publisher filter + Apps Script → Slides export | Lowest | Not built — PPTX export in the HTML dashboard covers the same meeting workflow |
| 2 | **Self-contained HTML dashboard** (openscience.works-style) | Medium | **Built** — this repo |
| 3 | **Live dashboard** (scheduled SQL → BigQuery/Cowork artifact) | Highest | Future — HTML dashboard is the prototype |

**Recommendation was Option 2.** That is what exists here: a single HTML file, no server, shareable for publisher meetings, and a prototype for what Option 3 would look like.

## What Option 2 specified vs what is built

| Requirement | Status |
|-------------|--------|
| Publisher dropdown → journal list → click journal | Done |
| Radar/spider chart of detection % | Done (Study Design radar) |
| RTI trend line (year on year) | Done |
| Resource findability bars | Done |
| One top metric (RTI) + detail panels | Partial — RTI is the primary KPI, but panels are always visible (not collapsible) |
| Load data client-side, no server | Done (embedded JSON, originally from enriched CSV) |
| Shareable as a file | Done |
| Presentation export per publisher | **Bonus** — PPTX export (automates the manual PNAS-style deck workflow from Option 1) |

## Project

Single-file interactive dashboard (`SciScore_journal_dashboard.html`) for exploring SciScore rigor metrics across **4,939 journals** and **537 publishers** (2015–2025). Data is embedded inline as a `DATA` JSON object (~5 MB), converted from the `2026_sciscore_v3` enriched CSV.

**Repo:** https://github.com/martijnroelandse/sciscore-dashboard

## How to run

```bash
open SciScore_journal_dashboard.html
# or
python3 -m http.server 8080
# → http://localhost:8080/SciScore_journal_dashboard.html
```

## Features

| Feature | Status |
|---------|--------|
| Publisher filter + journal search | Done |
| Per-journal KPIs, RTI trend chart, radar chart, resource bars | Done |
| White header + contrast fixes | Done |
| PPTX publisher report export | Done (lazy-loads PptxGenJS) |

## PPTX export (Option 1 workflow, in-browser)

- Button appears when a publisher is selected.
- Generates: title slide + one slide per journal (sorted by RTI, descending).
- Each journal slide: Study Design metrics (left) + Resource Findability (right).
- Filename: `SciScore_{Publisher}_Report.pptx`
- CDN fix (Jun 2026): `pptxgen.bundle.js` not `pptxgen.bundled.js` (old URL returned 404).

## Path to Option 3 (live dashboard)

1. **Data pipeline** — turn SQL in `2026_sciscore_v3` into a scheduled query (BigQuery or existing DB).
2. **Replace embedded JSON** — dashboard fetches from an API or JSON endpoint on load.
3. **Add `publisher_grouped`** — roll 537 publishers into sales-facing groups (as planned for the Sheet pivot).
4. **Cowork artifact** — persistent page that re-runs the query on open; publisher view for sales, journal drilldown for editorial.
5. **Keep the HTML prototype** — same UI/UX, swap data source from static embed to live fetch.

## Near-term improvements (still Option 2)

- [ ] **GitHub Pages** — host at `martijnroelandse.github.io/sciscore-dashboard/`
- [ ] **Split data from HTML** — `data.json` + fetch (enables easier CSV re-imports)
- [ ] **Publisher groups** — `publisher_grouped` filter for sales meetings
- [ ] **Collapsible detail panels** — closer to openscience.works signal-route layout
- [ ] **RTI trend chart in PPTX slides** — export currently shows bars only, not the line chart
- [ ] **README.md** — brief GitHub description

## Key files

```
SciScore_journal_dashboard.html   # entire app (HTML + CSS + JS + embedded data)
HANDOVER.md                       # this file
```

## Tech stack

- Vanilla HTML/CSS/JS
- [Chart.js 4.4.1](https://www.chartjs.org/) — line + radar charts
- [PptxGenJS 3.12.0](https://gitbrent.github.io/PptxGenJS/) — PowerPoint export (lazy-loaded)

## Data schema

```js
DATA = {
  p: { "Publisher Name": ["Journal A", "Journal B", ...] },
  j: {
    "Journal Name": {
      pub: "Publisher Name",
      y: {
        "2025": {
          n: 123,        // papers analysed
          r: 4.5,        // RTI score (0–10)
          sex, pwr, rand, blind, irb, iacuc,  // study design (0–1)
          ab, org, cl, tool,                  // resource findability (0–1)
          abn, orgn, cln, tooln               // detection counts
        }
      }
    }
  }
}
```

Source: enriched CSV (`2026_sciscore_v3`) with `publisher` column. `publisher_grouped` not yet in the data model.

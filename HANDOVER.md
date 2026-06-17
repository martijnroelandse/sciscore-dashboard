# SciScore Journal Dashboard — Handover

## Project

Single-file interactive dashboard (`SciScore_journal_dashboard.html`) for exploring SciScore rigor metrics across **4,939 journals** (2015–2025). Data is embedded inline as a `DATA` JSON object (~5 MB).

**Repo:** https://github.com/martijnroelandse/sciscore-dashboard

## How to run

Open the HTML file in a browser (no build step):

```bash
# macOS
open SciScore_journal_dashboard.html

# or serve locally
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

## Recent work (Jun 2026)

1. Added **Export Publisher Report** button (one PPTX slide per journal for selected publisher).
2. Fixed constructor: `new PptxGenJS()` (not `new pptxgen()`).
3. Lazy-load PptxGenJS on first export (keeps initial page load fast).
4. **Fixed CDN URLs:** `pptxgen.bundled.js` → `pptxgen.bundle.js` (both jsdelivr and unpkg returned 404 for the old filename).

## PPTX export behaviour

- Button appears when a publisher is selected in the sidebar.
- Generates: title slide + one slide per journal (sorted by RTI, descending).
- Each journal slide shows Study Design metrics (left) and Resource Findability (right).
- Filename: `SciScore_{Publisher}_Report.pptx`

## Known limitations / next steps

- [ ] **GitHub Pages hosting** — enable Pages on `main`, set source to root, access at `https://martijnroelandse.github.io/sciscore-dashboard/SciScore_journal_dashboard.html`
- [ ] **Split data from HTML** — move `DATA` to `data.json` and fetch on load (reduces HTML size, enables caching)
- [ ] **Add RTI trend chart to PPTX slides** — currently only bar metrics, not the line chart
- [ ] **README.md** — brief project description for GitHub
- [ ] **Publisher comparison view** — cross-publisher benchmarking (not started)

## Key files

```
SciScore_journal_dashboard.html   # entire app (HTML + CSS + JS + embedded data)
HANDOVER.md                       # this file
```

## Tech stack

- Vanilla HTML/CSS/JS (no framework)
- [Chart.js 4.4.1](https://www.chartjs.org/) — line + radar charts
- [PptxGenJS 3.12.0](https://gitbrent.github.io/PptxGenJS/) — PowerPoint export (lazy-loaded)

## Data schema (abbreviated)

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

## Testing PPTX export

1. Open dashboard in Chrome/Firefox.
2. Select a publisher (e.g. a small one for speed).
3. Click **▶ Export Publisher Report**.
4. Confirm `.pptx` downloads and opens in PowerPoint/Keynote.

If export fails with "Could not load PptxGenJS", check browser console — CDN must serve `pptxgen.bundle.js` (not `bundled`).

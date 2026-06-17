# Handover: PPTX Export Fix

## Problem
Export button throws `PptxGenJS is not defined` (and now `Could not load PptxGenJS from any CDN`).

## What's been done
- Removed the static `<script src>` tag for pptxgenjs (was failing silently at page load)
- Added lazy-loading in `generatePPTX()` via `ensurePptxGenJS()` with jsdelivr → unpkg fallback
- Both CDNs are failing — likely a network/CORS issue specific to the runtime environment

## What needs fixing
The CDN URLs need to be verified. Open the dashboard in a browser with DevTools → Network tab, click Export, and check which URL fails and why (CORS? 404? timeout?).

Candidate URLs to test:
- `https://cdn.jsdelivr.net/npm/pptxgenjs@3.12.0/dist/pptxgen.bundled.js`
- `https://unpkg.com/pptxgenjs@3.12.0/dist/pptxgen.bundled.js`
- `https://cdn.jsdelivr.net/npm/pptxgenjs/dist/pptxgen.bundled.js` (no pinned version)

If all CDNs fail, the fallback is to bundle pptxgenjs inline: `npm install pptxgenjs`, copy `node_modules/pptxgenjs/dist/pptxgen.bundled.js` into the repo, and reference it locally.

## File
`SciScore_journal_dashboard.html` — single file, all JS/CSS/data inline. Export logic starts at `function loadScript` (~line 524).

## Global name
The browser bundle exposes `window.PptxGenJS` (capital G, capital JS). The code at line 568 does `new PptxGenJS()` — this is correct assuming the bundle loads.

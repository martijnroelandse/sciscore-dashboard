# Client access & export — handover for sciscore.com developer

This document specifies work **not implemented in the public OA artifact**. The current maintainer delivers a **private source repo** + **public OA demo** on GitHub Pages. A developer with `sciscore.com` / `backoffice.sciscore.com` access should implement client auth, non-OA data, and gated export.

## Product tiers

| Tier | Corpus | Audience | Hosting (target) |
|------|--------|----------|------------------|
| **A — Public OA** | PMC open-access subset only | Everyone | GitHub Pages (`sciscore-dashboard` public artifact repo) |
| **B — Client licensed** | OA + publisher-licensed non-OA | Per-org login (e.g. AACR) | `sciscore.com/clients/{org}` |

**AACR on public OA:** All 8 AACR journals appear in the public dashboard with **OA-subset metrics only**. Full-corpus (non-OA) metrics are Tier B.

## Agreed business rules

- Public browsing (Tier A) includes AACR journals — supports awareness of reporting gaps.
- **CSV and PPTX export** require client login and org scope (Tier B).
- Export scope: **own org journals only** (no bulk “all publishers”).
- Benchmark columns in CSV: **`all`** and **`clients`** only (not per-discipline or competitor publishers).
- Click-through **SciScore Journal Metrics Data License** before first export (store `user_id`, `org_id`, `license_version`, `accepted_at`).
- CSV format only (no Excel required).

## Auth — minimum viable (v0)

SciScore today has **ORCID login for manuscript checking** but **no client portal**. Build a thin slice:

```
/clients/login              → “Sign in with ORCID”
/clients/auth/orcid/callback
/clients/aacr               → Journal Intelligence (gated UI)
/api/metrics/public         → OA metrics, no auth
/api/metrics/client         → OA + full corpus, requires session + org_id
/api/export/csv             → POST, auth + org + terms acceptance
/api/export/pptx            → optional; same gates as CSV
```

### Org binding (v1)

ORCID alone does not identify publisher org. Use:

1. **ORCID allowlist** per org (`allowed_orcids` in config/DB).
2. **Email domain verification** (`@aacr.org`) after ORCID login.
3. Optional: manual invite tokens for pilot.

### Session payload (example)

```json
{
  "orcid": "0000-0002-....",
  "org_id": "AACR",
  "tiers": ["full_corpus"],
  "export": true
}
```

### Client org mapping (existing)

`scripts/client_orgs.json` — extend with:

```json
"AACR": {
  "publishers": ["American Association for Cancer Research Inc."],
  "journals": [],
  "allowed_domains": ["aacr.org"],
  "allowed_orcids": []
}
```

AACR journals (resolved by publisher): Blood Cancer Discovery, Cancer Discovery, Cancer Immunology Research, Cancer Research, Cancer Research Communications, Clinical Cancer Research, Molecular Cancer Research, Molecular Cancer Therapeutics.

## Data model — OA vs full corpus

Store separately; never join client full-corpus rows without `org_id` check.

```
journal_metrics_oa          -- public Tier A (current 2026_sciscore_v3 OA pipeline)
journal_metrics_client      -- org_id, journal, year, metrics... (non-OA scoring)
```

Public API must return **only** `journal_metrics_oa`. Client API returns full corpus for journals in the authenticated org.

Future non-OA source files (private repo only):

```
data/client/aacr_full_corpus.csv   # not published to public artifact repo
```

## CSV export schema (long format)

| Column | Notes |
|--------|-------|
| `journal`, `publisher`, `publisher_group`, `year` | Identifiers |
| `corpus` | `oa` or `full` |
| `papers`, `rti` | Core |
| `sex`, `pwr`, `rand`, `blind`, `irb`, `iacuc` | Study design |
| `ab`, `org`, `cl`, `tool` | Resource findability |
| `data`, `code`, `prot`, `data_id`, `code_id` | Open science |
| `benchmark_rti`, `benchmark_*` | Optional; compare target (`all` or `clients`) |
| `delta_rti`, `delta_*` | Subject − benchmark |

Footer comment rows: export date, data version, license URL, `export_id`, user email.

## License (click-through)

Use a custom **SciScore Journal Metrics Data License** (proprietary), not Creative Commons.

Key clauses: internal use only, no redistribution/resale, SciScore retains IP, attribution required, no warranty, revocable.

Host at: `https://sciscore.com/legal/journal-metrics-data-license`

Methodology (`addendum.html`) may stay public under CC BY 4.0 separately from the numeric dataset.

## Public artifact repo (already set up)

- **Public:** `martijnroelandse/sciscore-dashboard` — built HTML only, GitHub Pages.
- **Private (target):** `sciscore-dashboard-private` — source, scripts, raw CSVs, client data.

See `docs/REPO_SPLIT_MIGRATION.md` for one-time GitHub setup.

Publish command (private repo):

```bash
python3 scripts/publish_oa_artifact.py
# or push to main → GitHub Action publishes automatically
```

## Migration to sciscore.com (timeline unknown)

Suggested order:

1. Deploy Tier A UI shell on `sciscore.com/journals` with **API-fetched OA data** (remove embedded `DATA` blob).
2. Implement ORCID + allowlist auth (reuse existing SciScore ORCID OAuth app if possible).
3. Add Tier B data pipeline for AACR non-OA scoring.
4. Enable `/api/export/csv` for authenticated AACR users.
5. Retire or redirect GitHub Pages URL to sciscore.com.

Until step 1 is live, GitHub Pages remains the public demo.

## Files to read first

| File | Purpose |
|------|---------|
| `HANDOVER.md` | Build pipeline, features |
| `docs/REPO_SPLIT_MIGRATION.md` | Two-repo setup |
| `scripts/journal_data_io.py` | Metric keys and CSV parsing |
| `scripts/client_orgs.json` | Client org definitions |
| `scripts/publish_oa_artifact.py` | OA public build |
| `addendum.html` | OA limitations (important for client conversations) |

## Explicit non-goals (maintainer phase)

- sciscore.com / backoffice integration
- ORCID auth implementation
- Non-OA scoring pipeline
- CSV/PPTX export (disabled on public artifact with “clients only” notice)

## Next step after repo split

Implement **ORCID integration + CSV export for AACR** on a staging environment (does not require immediate sciscore.com production access if a standalone auth stub is used). See `docs/ORCID_EXPORT_NEXT.md` for a suggested approach.

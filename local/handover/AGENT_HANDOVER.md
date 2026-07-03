# Agent handover — SciScore Journal Intelligence Dashboard

**Date:** 2026-07-03  
**Maintainer handing off:** Martijn Roelandse  
**Audience:** Next developer/agent with access to both GitHub repos (and eventually sciscore.com)

---

## Executive summary

This project is a **static web dashboard** for exploring SciScore rigor/transparency (RTI) metrics across biomedical journals. It was split into:

| Repo | URL | Role |
|------|-----|------|
| **Private (source)** | https://github.com/martijnroelandse/sciscore-dashboard-private | Edit code, data, scripts, CI |
| **Public (artifact)** | https://github.com/martijnroelandse/sciscore-dashboard | GitHub Pages OA demo only |

**Live demo:** https://martijnroelandse.github.io/sciscore-dashboard/SciScore_journal_dashboard.html

**Client context:** AACR wants (1) public OA metrics for awareness, (2) gated full-corpus + CSV/PPTX export via ORCID login, (3) no bulk export for competitors. See `docs/CLIENT_ACCESS_HANDOVER.md`.

**Immediate problems for next agent:**
1. **Sidebar fix not yet on public Pages** — layout/loading improvements exist on branch `cursor/repo-split-oa-publish-d550` but were not successfully republished.
2. **“Loading…” persists** on live site — ~13 MB embedded JSON blocks the UI until full script parse; needs a proper fix (not just copy).
3. **Git state on maintainer’s machine** — private `main` push was rejected (behind remote); may need reconcile.
4. **CI workflow location** — publish workflow was merged to public, then **deleted from public** by the first successful publish (`rsync --delete`). Future publishes must run from **private** repo.

---

## Architecture

```
┌─────────────────────────────────────┐
│  sciscore-dashboard-private         │
│  • SciScore_journal_dashboard.html  │  ← source shell + embedded DATA
│  • scripts/ (build, patch, publish) │
│  • data/ (2026_sciscore_v3.csv…)   │
│  • .github/workflows/publish-oa…  │
└──────────────┬──────────────────────┘
               │  publish_oa_artifact.py
               │  (or GitHub Action + deploy key)
               ▼
┌─────────────────────────────────────┐
│  sciscore-dashboard (public)        │
│  • SciScore_journal_dashboard.html  │  ← built artifact only
│  • addendum.html, design/, README   │
│  • NO scripts/, data/, .github/    │
└──────────────┬──────────────────────┘
               │  GitHub Pages
               ▼
         martijnroelandse.github.io/…
```

### Data tiers (product, not all built)

| Tier | Corpus | Access |
|------|--------|--------|
| **A — Public OA** | PMC open-access subset | Everyone (current Pages demo) |
| **B — Client licensed** | OA + non-OA full corpus | ORCID + org allowlist (AACR first) |

Public OA **includes AACR’s 8 journals** (OA metrics only). Full corpus is paid/gated.

---

## Verified state (2026-07-03)

### Public repo (`sciscore-dashboard`)

Root contains **only** (correct for artifact):

- `README.md`
- `SciScore_journal_dashboard.html` (~12.8 MB)
- `addendum.html`
- `design/`

Latest commit: `Publish OA artifact (2026-07-03)`.

**Does NOT contain:** `scripts/`, `data/`, `.github/workflows/`, `docs/`.

### Public HTML (live artifact) — feature flags

| Feature | On live public? |
|---------|-----------------|
| Embedded DATA (4909 journals) | ✅ |
| `corpusNotice` (OA disclaimer) | ✅ |
| `clientExportNotice` (export gated) | ✅ |
| `sidebar-footer` (layout fix) | ❌ not published yet |
| `earlySidebarBoot` (early journal count) | ❌ not published yet |
| Default compare `<option>All journals</option>` | ❌ not published yet |

### Private repo (`sciscore-dashboard-private`)

- Maintainer created repo and force-pushed full source (with PAT + `workflow` scope).
- Remotes on laptop: `origin` → private ✅; `public` → public (added as second remote).
- Local commit `328391c` “Sidebar layout fix…” — **push to `origin main` was rejected** (non-fast-forward). Remote private may differ from laptop.
- **Agent must:** clone private, inspect `main`, reconcile with branch `cursor/repo-split-oa-publish-d550` on public remote.

### GitHub Actions

| Repo | Workflow | Status |
|------|----------|--------|
| Public | `Publish OA artifact` | Ran successfully 2026-07-03, then workflow file removed from repo by publish |
| Private | Should have `publish-oa-artifact.yml` | Verify on private `main`; ensure `OA_ARTIFACT_DEPLOY_KEY` secret is on **private** |

### Secrets / deploy keys (maintainer configured)

- **Deploy key** (public key) on **public** repo — write access enabled.
- **`OA_ARTIFACT_DEPLOY_KEY`** — maintainer added; confirm it lives on **private** repo Actions secrets (not only public).
- Optional: `OA_ARTIFACT_REPO` = `martijnroelandse/sciscore-dashboard`

### sciscore.com

- **No access** for current maintainer. Do not depend on `backoffice.sciscore.com`.
- ORCID exists for manuscript checking but **no client portal** today.
- Long-term: API-backed hosting on sciscore.com (Option 3 in `HANDOVER.md`).

---

## Priority tasks (ordered)

### P0 — Reconcile git & republish sidebar fix

1. Clone both repos (or private + `public` remote).
2. On private `main`, ensure it contains:
   - Full source tree (`scripts/`, `data/`, `docs/`, `.github/workflows/publish-oa-artifact.yml`)
   - Sidebar fix from commit `2d3692e` on `cursor/repo-split-oa-publish-d550`:
     - `scripts/patch_oa_disclaimer.py`
     - `SciScore_journal_dashboard.html` with `sidebar-footer`, `earlySidebarBoot`
3. Resolve maintainer’s failed push (`git pull origin main --rebase` then push).
4. Run publish:
   ```bash
   python3 scripts/publish_oa_artifact.py --copy-only
   ```
   Or trigger **Publish OA artifact** workflow on **private** repo.
5. Verify public repo updates and hard-refresh Pages (Cmd+Shift+R).

### P1 — Fix “Loading…” properly

**Root cause:** `const DATA = {…}` (~12 MB JSON) is inline in `<script>`. Browser must parse entire blob before any UI init runs. User sees `Loading…` for many seconds (worse on slow devices).

**Partial mitigation already on branch (not live):** `earlySidebarBoot()` updates journal count right after `JOURNAL_COUNT_LABEL` — still blocked until DATA finishes parsing.

**Proper fixes (pick one):**

| Approach | Effort | Notes |
|----------|--------|-------|
| **A. External `data.json` + `fetch()`** | Medium | Best for Pages; removes data from HTML; enables loading spinner/progress |
| **B. Split DATA load via dynamic `import()` or second script file** | Medium | `data.js` generated at build time; HTML shell loads fast |
| **C. Web Worker parse** | Higher | Parse JSON off main thread; more complex |
| **D. Server API (sciscore.com)** | High | Option 3; correct long-term |

**Also fix:** `populateCompareSelect()` runs late — default `<option value="all">` in HTML helps until JS runs.

**Acceptance criteria:**
- Compare against shows “All journals” immediately or &lt;1s.
- Journal count and list appear without indefinite “Loading…”.
- No regression to embedded metrics accuracy.

### P2 — ORCID + AACR CSV export

See `docs/ORCID_EXPORT_NEXT.md` and `docs/CLIENT_ACCESS_HANDOVER.md`.

Summary:
- Thin auth layer (ORCID OAuth + `allowed_orcids` / `@aacr.org` email verify).
- `POST /api/export/csv` scoped to AACR’s 8 journals.
- Click-through **SciScore Journal Metrics Data License** (proprietary, not CC).
- Benchmark columns in export: `all` and `clients` only.
- Can pilot on staging without sciscore.com; production merges later.

AACR journals (via publisher `American Association for Cancer Research Inc.`):
Blood Cancer Discovery, Cancer Discovery, Cancer Immunology Research, Cancer Research, Cancer Research Communications, Clinical Cancer Research, Molecular Cancer Research, Molecular Cancer Therapeutics.

### P3 — Non-OA full corpus (revenue)

- Separate dataset `data/client/aacr_full_corpus.csv` (not in public artifact).
- Never embed in public HTML.
- Tier B API returns only when `org_id=AACR` in session.

---

## Key files

| Path | Purpose |
|------|---------|
| `SciScore_journal_dashboard.html` | App UI + embedded metrics (13 MB) |
| `scripts/publish_oa_artifact.py` | Build → `dist/oa-public/` |
| `scripts/patch_oa_disclaimer.py` | OA notice + client-only export UI |
| `scripts/embed_journal_data.py` | CSV → `DATA` |
| `scripts/embed_benchmarks.py` | Benchmarks + `BENCHMARK_CATALOG` |
| `scripts/client_orgs.json` | AACR, AHA, etc. |
| `scripts/journal_data_io.py` | Metric schema |
| `addendum.html` | Methodology; `#limitations` anchor |
| `.github/workflows/publish-oa-artifact.yml` | CI publish to public |
| `docs/CLIENT_ACCESS_HANDOVER.md` | Product/auth/license spec |
| `docs/REPO_SPLIT_MIGRATION.md` | Repo split setup |
| `docs/ORCID_EXPORT_NEXT.md` | ORCID phase plan |
| `HANDOVER.md` | Original build/run docs |

### Regenerate data locally

```bash
pip install openpyxl
python3 scripts/embed_journal_data.py
python3 scripts/embed_benchmarks.py
python3 scripts/embed_brand_assets.py
python3 scripts/patch_oa_disclaimer.py
python3 scripts/publish_oa_artifact.py
```

---

## Publish pipeline

```bash
# From private repo root
python3 scripts/publish_oa_artifact.py           # full rebuild
python3 scripts/publish_oa_artifact.py --copy-only  # patch + copy only
```

Output: `dist/oa-public/` → push to public `main` (via Action or manual).

**Important:** Public repo must stay artifact-only. Never commit `data/*.csv` to public.

---

## Maintainer git notes (for agent)

Events that happened:
1. PR #31 merged to **public** `main` (publish workflow + docs).
2. Publish workflow ran, stripped public to artifacts (removed `.github/`).
3. Private repo created; force-push required PAT with **`workflow`** scope.
4. Sidebar fix on branch `cursor/repo-split-oa-publish-d550` (commits `d0877ed`, `2d3692e`).
5. Maintainer fetched `public` remote on private clone, checked out 2 files, committed `328391c`, **push rejected** (behind remote).
6. GitHub Desktop showed “unrelated histories” when trying to pull — likely from mixing public artifact history with private; **do not pull public `main` into private**.

**Correct remotes on private clone:**
```
origin  → sciscore-dashboard-private.git
public  → sciscore-dashboard.git  (read-only, for fetching branches)
```

---

## What the maintainer may have missed

| Item | Status | Action |
|------|--------|--------|
| Republish after sidebar fix | ❌ | P0 |
| Move `OA_ARTIFACT_DEPLOY_KEY` to private repo | ⚠️ verify | Check private Actions secrets |
| Move/disable workflow on public | ⚠️ | Public no longer has workflow (OK by accident) |
| Confirm private `main` has full `data/` and `scripts/` | ⚠️ verify | Agent audit |
| `design/` assets mostly `.gitkeep` on public | ⚠️ | PPTX icons may 404; check `Design/` in private |
| JMIR country/institution dashboards | Not in public artifact | Intentional unless `--include-jmir` |
| PR #31 open/merged on private | Merged on public only | Ensure private has same commits |
| AACR non-OA scoring pipeline | Not started | P3 |
| License page URL (`sciscore.com/legal/…`) | Not created | Needed before ORCID export |
| Rate limits / export audit log | Not implemented | P2 hardening |

---

## Acceptance checklist for “repo split complete”

- [ ] Private `main` has full source + workflow + latest sidebar fix
- [ ] Public `main` has only artifact files
- [ ] Pages demo loads with sidebar footer layout
- [ ] Compare against populated; journal list loads reliably
- [ ] Export shows “clients only” (ORCID not yet required for message)
- [ ] `OA_ARTIFACT_DEPLOY_KEY` on private; publish Action runs green
- [ ] Maintainer can push to private without auth errors

---

## Acceptance checklist for “loading fix complete”

- [ ] First meaningful UI &lt; 2s on typical connection
- [ ] No stuck “Loading…” after 30s
- [ ] 4909 journals searchable after load
- [ ] Document new load pattern in `HANDOVER.md`

---

## Acceptance checklist for “AACR export MVP”

- [ ] ORCID login works on staging
- [ ] AACR allowlist grants export
- [ ] CSV downloads 8 journals, all years, long format
- [ ] License click-through recorded
- [ ] Non-AACR users cannot export

---

## Related docs

- `HANDOVER.md` — features, build pipeline, JMIR dashboards
- `docs/CLIENT_ACCESS_HANDOVER.md` — tiers, license, sciscore.com migration
- `docs/REPO_SPLIT_MIGRATION.md` — deploy key setup
- `docs/ORCID_EXPORT_NEXT.md` — ORCID staging architecture

---

## Contact / product decisions already made

1. Public OA includes AACR journals (OA metrics).
2. Export (CSV + PPTX) requires client login; no full-corpus public export.
3. CSV only (no Excel).
4. Export benchmarks: `all` and `clients` only.
5. Custom proprietary click-through license (not Creative Commons).
6. sciscore.com integration deferred; GitHub Pages is interim hosting.

**Open product question:** How long to stay on GitHub Pages vs migrate to sciscore.com API (Option 3)?

---

*Generated for agent continuity. Update this file when P0–P2 milestones complete.*

# Repository split — migration guide

Split the project into a **private source repo** and a **public OA artifact repo** so raw data and build scripts stay private while GitHub Pages demos remain public.

## Target layout

| Repo | Visibility | GitHub Pages | Contents |
|------|------------|--------------|----------|
| `sciscore-dashboard-private` | **Private** | No | Source HTML, `scripts/`, `data/`, docs, CI workflow |
| `sciscore-dashboard` | **Public** | Yes (existing URL) | Built HTML, `addendum.html`, `design/` only |

**Live demo URL (unchanged):**  
https://martijnroelandse.github.io/sciscore-dashboard/SciScore_journal_dashboard.html

## One-time GitHub setup

### Step 1 — Create the private source repo

1. On GitHub: **New repository** → `sciscore-dashboard-private` → **Private**.
2. Add the private repo as a second remote on your local clone (or make the current repo private and create a fresh public artifact repo — see Step 2).

**Recommended:** Rename workflow:

- Current `martijnroelandse/sciscore-dashboard` becomes **private** (after Step 2 populates the public artifact).
- Create new public repo `sciscore-dashboard-public` OR keep the name `sciscore-dashboard` as public and move source to private.

**Simplest path if `sciscore-dashboard` must stay the public Pages repo:**

1. Create `sciscore-dashboard-private` (private).
2. Push full current codebase to `sciscore-dashboard-private`.
3. Strip `sciscore-dashboard` (public) down to OA artifacts only (see Step 3).

### Step 2 — Deploy key for CI publish

1. Generate an SSH key pair (deploy key):

   ```bash
   ssh-keygen -t ed25519 -C "oa-artifact-publish" -f oa-artifact-deploy -N ""
   ```

2. Add **public** key (`oa-artifact-deploy.pub`) as a **Deploy key** on the **public** repo with **Write access**.
3. Add **private** key as a GitHub Actions secret on the **private** repo:
   - Name: `OA_ARTIFACT_DEPLOY_KEY`
4. Optional secrets:
   - `OA_ARTIFACT_REPO` — default `martijnroelandse/sciscore-dashboard`

### Step 3 — Strip the public repo

After first `publish_oa_artifact.py` run, the public repo should contain **only**:

```
SciScore_journal_dashboard.html
addendum.html
design/
README.md
```

**Remove from public repo** (keep in private):

- `scripts/`
- `data/` (raw CSVs)
- `SciScore_country_dashboard.html` / `SciScore_institution_dashboard.html` (unless explicitly published with `--include-jmir`)
- `SciScore template.pptx`, `jmir_*.xlsx`
- `HANDOVER.md`, `docs/` (optional: keep a minimal README only)
- `Design/` duplicate tree if `design/` is sufficient

### Step 4 — Enable GitHub Pages on public repo

Settings → Pages → Deploy from branch **main** → `/ (root)`.

### Step 5 — Verify

1. Push to `sciscore-dashboard-private` `main`.
2. GitHub Action `Publish OA artifact` runs.
3. Public repo updates; Pages site shows OA disclaimer and disabled client export button.

## Local publish (without CI)

From the **private** repo:

```bash
# Full rebuild + write to dist/oa-public/
python3 scripts/publish_oa_artifact.py

# Copy-only (skip rebuild if HTML already built)
python3 scripts/publish_oa_artifact.py --copy-only

# Include JMIR country/institution dashboards
python3 scripts/publish_oa_artifact.py --include-jmir
```

Manual push to public repo:

```bash
cd dist/oa-public
git init
git remote add origin git@github.com:martijnroelandse/sciscore-dashboard.git
git checkout -b main
git add .
git commit -m "Publish OA artifact"
git push -f origin main   # first time only; use with care
```

Prefer the GitHub Action for routine updates.

## Who can access what

| Audience | Access |
|----------|--------|
| Co-workers | Clone **private** repo; or use public Pages URL for OA demo |
| AACR / clients | Public Pages URL (OA metrics); full corpus after ORCID login (future) |
| World | Public Pages URL only |

Making the **source** repo private does **not** block demos — the **public artifact** repo serves Pages.

## Rollback

Keep a tagged release on the private repo before each publish:

```bash
git tag -a oa-publish-2026-07-03 -m "Before OA artifact publish"
git push origin oa-publish-2026-07-03
```

# Next phase: ORCID login + AACR CSV export

Implement after the repo split is live. Does **not** require immediate `sciscore.com` production access — can run on a staging host or GitHub Codespaces + simple auth backend.

## Goal

AACR editors sign in with ORCID → download CSV (and optionally PPTX) for **their 8 journals only**, including future **full-corpus (non-OA)** metrics when available.

## Suggested staging architecture

```
staging host (e.g. Fly.io, Railway, Cloudflare Workers + KV)
├── Static: OA dashboard shell (from publish_oa_artifact.py)
├── API: Node/Python lightweight server
│   ├── GET  /auth/orcid/login
│   ├── GET  /auth/orcid/callback
│   ├── GET  /api/session
│   ├── GET  /api/metrics/client?journal=...
│   └── POST /api/export/csv
└── Config: client_orgs.json + allowed_orcids / allowed_domains
```

## ORCID OAuth flow

1. User clicks **Sign in with ORCID** on disabled export button (or `/clients/login`).
2. Redirect to ORCID authorize URL (reuse SciScore’s existing ORCID client credentials if policy allows; otherwise register a separate “Journal Intelligence” app).
3. Callback exchanges code for access token; fetch ORCID record (`/oauth/userinfo` or ORCID API).
4. Match user to org:
   - ORCID in `allowed_orcids` → grant `org_id`
   - Else prompt for work email → if `@aacr.org`, send verification link → grant `org_id`
   - Else deny export (public OA view still works)
5. Issue HTTP-only session cookie (JWT or server session).

## CSV export endpoint

```http
POST /api/export/csv
Cookie: session=...
Content-Type: application/json

{
  "year": "2024",
  "format": "long",
  "benchmark": "all",
  "terms_accepted": true,
  "license_version": "1.0"
}
```

Response: `text/csv` attachment with license footer rows.

Server-side query (pseudocode):

```sql
SELECT * FROM journal_metrics_client
WHERE org_id = :session.org_id
  AND year = :year
```

Until non-OA data exists, `journal_metrics_client` can mirror OA metrics for AACR journals only (pilot).

## UI changes (minimal)

In `SciScore_journal_dashboard.html` (private source):

- Replace disabled export stub with:
  - Not logged in → “Sign in with ORCID to export”
  - Logged in, wrong org → “Export not available for your account”
  - Logged in, AACR → enable CSV button; PPTX optional
- Add `fetch()` to API instead of embedded full corpus for client tier (long-term).

## Effort estimate (for developer planning)

| Piece | Complexity |
|-------|------------|
| ORCID OAuth stub + session | Small–medium |
| Allowlist + email verify | Small |
| CSV generation server-side | Small (reuse `journal_data_io` column mapping) |
| Non-OA data ingest | Medium (depends on scoring pipeline) |
| sciscore.com integration | Medium–large (DNS, existing auth merge, backoffice) |

**Pilot without sciscore.com:** 1–2 weeks for a skilled developer with ORCID app access.  
**Production on sciscore.com:** depends on existing infra and who owns ORCID client credentials.

## Handoff checklist

- [ ] ORCID client ID/secret (new app or reuse SciScore)
- [ ] Staging URL agreed with AACR
- [ ] `allowed_orcids` / `allowed_domains` for AACR contacts
- [ ] License page URL or interim PDF
- [ ] Decision: pilot on OA-only data first, then add non-OA scores

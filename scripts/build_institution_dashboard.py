#!/usr/bin/env python3
"""Build SciScore institution dashboard HTML from JMIR 2022 CSV + ROR matches."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from entity_benchmarks import build_institution_benchmark  # noqa: E402
from entity_dashboard_shell import render_dashboard_html  # noqa: E402
from entity_data_io import (  # noqa: E402
    build_institution_data,
    find_institution_csv,
    load_ror_matches,
    read_csv_rows,
)

OUTPUT = ROOT / "SciScore_institution_dashboard.html"


def main() -> int:
    path = find_institution_csv()
    if not path:
        print("No institution CSV in data/", file=sys.stderr)
        return 1

    ror_matches = load_ror_matches()
    print(f"Reading {path}")
    if ror_matches:
        print(f"ROR matches loaded: {len(ror_matches):,}")
    else:
        print("No ROR matches (run: python3 scripts/match_ror.py)")

    rows = read_csv_rows(path)
    data, meta = build_institution_data(rows, ror_matches)
    benchmark = build_institution_benchmark(data)

    html = render_dashboard_html(
        entity_type="institution",
        title="SciScore Institution Intelligence (JMIR 2022)",
        subtitle="JMIR 2022 corpus · ROR-enriched where matched",
        data=data,
        benchmark=benchmark,
        meta=meta,
    )
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"Institutions: {meta['entity_count']:,}, countries: {meta['country_count']:,}")
    print(f"ROR matched in embed: {meta.get('ror_matched', 0):,}")
    years = sorted(meta["years"].keys(), key=int)
    if years:
        print(f"Years: {years[0]}–{years[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

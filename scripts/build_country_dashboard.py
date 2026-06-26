#!/usr/bin/env python3
"""Build SciScore country dashboard HTML from JMIR 2022 CSV data.

Keeps this dashboard separate from the journal platform (editor review).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from entity_benchmarks import build_country_benchmark  # noqa: E402
from entity_dashboard_shell import render_dashboard_html  # noqa: E402
from entity_data_io import build_country_data, find_country_csv, read_csv_rows  # noqa: E402

OUTPUT = ROOT / "SciScore_country_dashboard.html"


def main() -> int:
    path = find_country_csv()
    if not path:
        print("No country CSV in data/", file=sys.stderr)
        return 1

    print(f"Reading {path}")
    rows = read_csv_rows(path)
    data, meta = build_country_data(rows)
    benchmark = build_country_benchmark(data)

    html = render_dashboard_html(
        entity_type="country",
        title="SciScore Country Intelligence (JMIR 2022)",
        subtitle="JMIR 2022 corpus · open-access PMC subset",
        data=data,
        benchmark=benchmark,
        meta=meta,
    )
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"Countries: {meta['entity_count']:,}, rows: {meta['row_count']:,}")
    years = sorted(meta["years"].keys(), key=int)
    if years:
        print(f"Years: {years[0]}–{years[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

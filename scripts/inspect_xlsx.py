#!/usr/bin/env python3
"""Inspect by_journal_by_year source (CSV or xlsx).

    python3 scripts/inspect_xlsx.py
    python3 scripts/inspect_xlsx.py data/by_journal_by_year.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from embed_benchmarks import find_by_year_header_row, find_xlsx  # noqa: E402
from journal_data_io import (  # noqa: E402
    DEFAULT_CSV,
    DEFAULT_XLSX,
    find_journal_source,
    inspect_rows,
    map_all_headers,
    parse_row_metrics,
    read_rows,
)


def inspect_by_year_sheet(path: Path) -> dict | None:
    if path.suffix.lower() != ".xlsx":
        return None
    try:
        import openpyxl
    except ImportError:
        return None
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if "by_year" not in wb.sheetnames:
        return None
    rows = list(wb["by_year"].iter_rows(values_only=True))
    header_idx, headers, colmap = find_by_year_header_row(rows)
    colmap = map_all_headers(headers, rows[header_idx + 1 : header_idx + 21])
    years = []
    for row in rows[header_idx + 1 :]:
        if not row or "year" not in colmap:
            continue
        year_raw = row[colmap["year"]]
        if year_raw is None:
            continue
        year = str(int(float(year_raw)))
        metrics = parse_row_metrics(list(row), colmap)
        years.append((year, sorted(k for k in metrics if k != "_publisher")))
    return {
        "sheet": "by_year",
        "years": len(years),
        "year_range": f"{years[0][0]}–{years[-1][0]}" if years else None,
        "full_metrics_from": next((y for y, keys in years if len(keys) > 3), None),
        "columns_mapped": {k: headers[v] for k, v in sorted(colmap.items(), key=lambda x: x[1])},
    }


def main() -> int:
    explicit = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    path = find_journal_source(explicit)
    if not path:
        print("No journal source found.", file=sys.stderr)
        print(f"  CSV:  {DEFAULT_CSV}", file=sys.stderr)
        print(f"  XLSX: {DEFAULT_XLSX}", file=sys.stderr)
        return 1

    print(f"File: {path}\n")
    rows = read_rows(path)
    report = {
        "file": str(path),
        "by_journal_by_year": inspect_rows(rows),
    }
    by_year = inspect_by_year_sheet(path)
    if by_year:
        report["by_year"] = by_year

    print(json.dumps(report, indent=2, default=str))

    bj = report["by_journal_by_year"]
    y = bj["years"]
    print("\n--- Summary ---")
    print(f"Journals: {bj['journal_count']:,}  |  Rows: {bj['row_count']:,}")
    print(f"Year range: {y['min']}–{y['max']} ({y['count']} years)")
    new = bj["metrics"]["new_vs_dashboard"]
    if new:
        print(f"New metrics vs dashboard: {', '.join(new)}")
    if bj["columns"]["unmapped"]:
        print(f"Unmapped columns: {', '.join(str(c) for c in bj['columns']['unmapped'][:12])}")
        if len(bj["columns"]["unmapped"]) > 12:
            print(f"  … and {len(bj['columns']['unmapped']) - 12} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

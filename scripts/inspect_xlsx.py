#!/usr/bin/env python3
"""Inspect journal-year source (2026_sciscore_v3.csv or xlsx export).

    python3 scripts/inspect_xlsx.py
    python3 scripts/inspect_xlsx.py data/2026_sciscore_v3.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from journal_data_io import DEFAULT_CSV, find_journal_source, inspect_rows, read_rows  # noqa: E402


def main() -> int:
    explicit = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    path = find_journal_source(explicit)
    if not path:
        print("No journal source found.", file=sys.stderr)
        print(f"  Expected: {DEFAULT_CSV}", file=sys.stderr)
        return 1

    print(f"File: {path}\n")
    rows = read_rows(path)
    report = {"file": str(path), **inspect_rows(rows)}
    print(json.dumps(report, indent=2, default=str))

    bj = report
    y = bj["years"]
    print("\n--- Summary ---")
    print(f"Journals: {bj['journal_count']:,}  |  Rows: {bj['row_count']:,}")
    print(f"Year range: {y['min']}–{y['max']} ({y['count']} years)")
    new = bj["metrics"]["new_vs_dashboard"]
    if new:
        print(f"New metrics vs dashboard: {', '.join(new)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

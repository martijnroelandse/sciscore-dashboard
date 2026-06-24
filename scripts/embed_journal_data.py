#!/usr/bin/env python3
"""Embed journal metrics from data/by_journal_by_year.csv into the dashboard HTML.

Pipeline after updating the source file:

    python3 scripts/embed_journal_data.py
    python3 scripts/normalize_data.py
    python3 scripts/embed_benchmarks.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

HTML = ROOT / "SciScore_journal_dashboard.html"

from html_json import extract_json_block, replace_const_block  # noqa: E402
from journal_data_io import DEFAULT_CSV, build_data, find_journal_source, read_rows  # noqa: E402


def main() -> int:
    explicit = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    path = find_journal_source(explicit)
    if not path:
        print("No journal source found.", file=sys.stderr)
        print(f"  Place {DEFAULT_CSV.name} in data/ and re-run.", file=sys.stderr)
        return 1

    print(f"Reading {path}")
    rows = read_rows(path)
    data, meta = build_data(rows)

    before = extract_json_block(HTML.read_text(encoding="utf-8"), "DATA")
    before_journals = len(before.get("j", {}))
    before_years = sorted(
        {year for entry in before.get("j", {}).values() for year in entry.get("y", {})},
        key=int,
    )

    content = HTML.read_text(encoding="utf-8")
    content = replace_const_block(content, "DATA", data)
    if "\nconst GROUP_MAP" not in content:
        raise SystemExit(
            "ERROR: HTML looks truncated after DATA embed (const GROUP_MAP missing). "
            "Restore SciScore_journal_dashboard.html from git and re-run."
        )
    HTML.write_text(content, encoding="utf-8")

    after_years = sorted(
        {year for entry in data["j"].values() for year in entry["y"]},
        key=int,
    )
    print(f"Journals: {before_journals:,} -> {meta['journal_count']:,}")
    print(f"Rows embedded: {meta['row_count']:,}")
    if after_years:
        print(f"Year range: {after_years[0]}–{after_years[-1]}")
    if before_years and after_years and after_years[0] < before_years[0]:
        print(f"  Extended earliest year: {before_years[0]} -> {after_years[0]}")
    new_metrics = sorted(set(meta["metric_presence"]) - {"n", "r", "sex", "pwr", "rand", "blind", "irb", "iacuc", "ab", "org", "cl", "tool", "abn", "orgn", "cln", "tooln"})
    if new_metrics:
        print(f"New metric keys in embed: {', '.join(new_metrics)}")
    print("Next: python3 scripts/normalize_data.py && python3 scripts/embed_benchmarks.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read by_journal_by_year from CSV or xlsx and build dashboard DATA."""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from embed_benchmarks import (  # noqa: E402
    COUNT_KEYS,
    JOURNAL_NAME_ALIASES,
    RATE_KEYS,
    find_by_year_header_row,
    find_xlsx,
    map_headers,
    norm_header,
    parse_int,
    parse_rate,
    row_to_year_data,
)

DEFAULT_CSV = ROOT / "data" / "by_journal_by_year.csv"
DEFAULT_XLSX = ROOT / "data" / "2026_sciscore_v3.xlsx"

# SciScore v3 export columns beyond the original dashboard embed.
EXTRA_ALIASES: dict[str, list[str]] = {
    "data": ["data", "data availability", "data_avail", "data availability statement"],
    "code": ["code", "code availability", "code_avail", "code availability statement"],
    "prot": ["prot", "protocol", "protocol availability", "protocol identifier", "protocol identifiers"],
    "data_id": ["data identifier", "data identifiers", "data_id", "data id"],
    "code_id": ["code identifier", "code identifiers", "code_id", "code id"],
    "prot_id": ["protocol id", "protocol ids", "prot_id"],
    "datan": ["data detections", "data_n", "data count"],
    "coden": ["code detections", "code_n", "code count"],
    "protn": ["protocol detections", "protocol_n", "protocol count"],
    "stats": ["stats", "statistics", "statistical reporting", "statistics module"],
    "publisher": ["publisher", "pub", "publisher name"],
}

EMBEDDED_KEYS = set(RATE_KEYS + COUNT_KEYS + ["n"])
EXTRA_RATE_KEYS = [k for k in EXTRA_ALIASES if k not in ("publisher", "datan", "coden", "protn")]
EXTRA_COUNT_KEYS = [k for k in ("datan", "coden", "protn") if k in EXTRA_ALIASES]


def find_journal_csv() -> Path | None:
    data_dir = ROOT / "data"
    if not data_dir.is_dir():
        return None
    preferred = [
        data_dir / "by_journal_by_year.csv",
        *sorted(data_dir.glob("*by_journal*.csv")),
        *sorted(data_dir.glob("*journal*year*.csv")),
    ]
    seen: set[Path] = set()
    for path in preferred:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        return path
    matches = sorted(data_dir.glob("*.csv"))
    if len(matches) == 1:
        return matches[0]
    if matches:
        return matches[0]
    return None


def find_journal_source(explicit: Path | None = None) -> Path | None:
    if explicit and explicit.exists():
        return explicit
    return find_journal_csv() or find_xlsx(DEFAULT_XLSX)


def read_rows(path: Path) -> list[tuple]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return [tuple(row) for row in csv.reader(handle)]
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("openpyxl is required for xlsx: pip install openpyxl") from exc
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if "by_journal_by_year" not in wb.sheetnames:
        raise ValueError(
            f"Sheet 'by_journal_by_year' not found in {path}; sheets: {wb.sheetnames}"
        )
    return list(wb["by_journal_by_year"].iter_rows(values_only=True))


def map_all_headers(headers: list, data_rows: list) -> dict[str, int]:
    mapping = map_headers(headers, data_rows)
    normalized = [norm_header(h) for h in headers]
    for key, aliases in EXTRA_ALIASES.items():
        if key in mapping:
            continue
        for alias in aliases:
            alias_norm = norm_header(alias)
            for idx, header in enumerate(normalized):
                if header == alias_norm or (header and alias_norm in header):
                    mapping[key] = idx
                    break
            if key in mapping:
                break
    return mapping


def detect_journal_column(headers: list, data_rows: list) -> int | None:
    normalized = [norm_header(h) for h in headers]
    for alias in JOURNAL_NAME_ALIASES:
        alias_norm = norm_header(alias)
        for idx, header in enumerate(normalized):
            if header == alias_norm or (header and alias_norm in header):
                return idx
    for idx in range(min(8, len(headers))):
        values = [
            str(row[idx]).strip()
            for row in data_rows[:200]
            if row and idx < len(row) and row[idx] not in (None, "")
        ]
        if len(values) >= 20 and len(set(values)) >= 15:
            return idx
    return None


def parse_row_metrics(row: list, colmap: dict[str, int]) -> dict:
    out = row_to_year_data(list(row), colmap)
    for key in EXTRA_ALIASES:
        if key in colmap and key not in out:
            raw = row[colmap[key]] if colmap[key] < len(row) else None
            if key in EXTRA_COUNT_KEYS:
                out[key] = parse_int(raw)
            elif key == "publisher":
                out[key] = str(raw).strip() if raw not in (None, "") else None
            else:
                out[key] = parse_rate(raw)
    publisher = out.pop("publisher", None)
    if publisher:
        out["_publisher"] = publisher
    return out


def year_string(year_raw) -> str | None:
    if year_raw is None or str(year_raw).strip() == "":
        return None
    text = str(year_raw).strip()
    if text.replace(".", "", 1).isdigit():
        return str(int(float(text)))
    return text


def merge_year_metrics(existing: dict | None, incoming: dict) -> dict:
    if not existing:
        return incoming
    if int(incoming.get("n") or 0) >= int(existing.get("n") or 0):
        return incoming
    return existing


def build_data(rows: list[tuple]) -> tuple[dict, dict]:
    if not rows:
        raise ValueError("Input is empty")

    header_idx, headers, _ = find_by_year_header_row(rows)
    data_rows = rows[header_idx + 1 :]
    colmap = map_all_headers(headers, data_rows[:50])
    journal_col = detect_journal_column(headers, data_rows[:200])
    if journal_col is None:
        raise ValueError(f"Could not detect journal name column in headers: {headers}")
    if "year" not in colmap:
        raise ValueError(f"Could not detect year column in headers: {headers}")

    journals: dict[str, dict] = {}
    years = Counter()
    metric_presence: Counter[str] = Counter()

    for row in data_rows:
        if not row or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        year = year_string(row[colmap["year"]])
        if not year:
            continue
        metrics = parse_row_metrics(list(row), colmap)
        if not metrics.get("n") and metrics.get("r") is None:
            continue

        jname = str(row[journal_col]).strip() if journal_col < len(row) and row[journal_col] else ""
        if not jname:
            continue

        pub = metrics.pop("_publisher", None)
        if not pub and "publisher" in colmap and colmap["publisher"] < len(row):
            pub = row[colmap["publisher"]]
        pub = str(pub).strip() if pub not in (None, "") else None

        entry = journals.setdefault(jname, {"pub": pub or "", "y": {}})
        if pub and not entry["pub"]:
            entry["pub"] = pub
        entry["y"][year] = merge_year_metrics(entry["y"].get(year), metrics)
        years[year] += 1
        for key, val in metrics.items():
            if val is not None:
                metric_presence[key] += 1

    publishers: dict[str, list[str]] = defaultdict(list)
    for jname, entry in journals.items():
        publishers[entry.get("pub") or "Unknown"].append(jname)
    publisher_index = {pub: sorted(names) for pub, names in sorted(publishers.items())}

    meta = {
        "header_row": header_idx + 1,
        "headers": [str(h) if h is not None else "" for h in headers],
        "mapped_columns": {k: headers[v] for k, v in sorted(colmap.items(), key=lambda x: x[1])},
        "journal_column": headers[journal_col],
        "years": dict(sorted(years.items(), key=lambda x: int(x[0]))),
        "metric_presence": dict(sorted(metric_presence.items())),
        "journal_count": len(journals),
        "row_count": sum(years.values()),
    }
    return {"j": journals, "p": publisher_index}, meta


def inspect_rows(rows: list[tuple]) -> dict:
    header_idx, headers, _ = find_by_year_header_row(rows)
    data_rows = rows[header_idx + 1 :]
    colmap = map_all_headers(headers, data_rows[:50])
    journal_col = detect_journal_column(headers, data_rows[:200])

    years = Counter()
    journals: set[str] = set()
    publishers = Counter()
    metric_presence: Counter[str] = Counter()
    sample_by_year: dict[str, dict] = {}
    unmapped_headers = [
        headers[i]
        for i, h in enumerate(headers)
        if h not in (None, "")
        and i not in colmap.values()
        and norm_header(h) not in {"", "unnamed"}
    ]

    for row in data_rows:
        if not row or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        if "year" not in colmap:
            continue
        year = year_string(row[colmap["year"]])
        if not year:
            continue
        metrics = parse_row_metrics(list(row), colmap)
        if not metrics.get("n") and metrics.get("r") is None:
            continue

        years[year] += 1
        if journal_col is not None and journal_col < len(row) and row[journal_col]:
            journals.add(str(row[journal_col]).strip())
        pub = metrics.get("_publisher")
        if pub:
            publishers[str(pub).strip()] += 1
        for key, val in metrics.items():
            if key != "_publisher" and val is not None:
                metric_presence[key] += 1
        if year not in sample_by_year:
            sample_by_year[year] = {k: v for k, v in metrics.items() if k != "_publisher"}

    sorted_years = sorted(years.keys(), key=int)
    return {
        "header_row": header_idx + 1,
        "row_count": sum(years.values()),
        "journal_count": len(journals),
        "publisher_count": len(publishers),
        "years": {
            "min": sorted_years[0] if sorted_years else None,
            "max": sorted_years[-1] if sorted_years else None,
            "count": len(sorted_years),
            "rows_per_year": dict(sorted(years.items(), key=lambda x: int(x[0]))),
        },
        "columns": {
            "headers": [str(h) if h is not None else "" for h in headers],
            "mapped": {k: headers[v] for k, v in sorted(colmap.items(), key=lambda x: x[1])},
            "journal_column": headers[journal_col] if journal_col is not None else None,
            "unmapped": unmapped_headers,
        },
        "metrics": {
            "present_in_rows": dict(sorted(metric_presence.items())),
            "already_in_dashboard": sorted(EMBEDDED_KEYS),
            "new_vs_dashboard": sorted(set(metric_presence) - EMBEDDED_KEYS),
            "missing_from_sheet": sorted(EMBEDDED_KEYS - set(metric_presence)),
        },
        "samples": {
            "earliest_year": sample_by_year.get(sorted_years[0]) if sorted_years else None,
            "latest_year": sample_by_year.get(sorted_years[-1]) if sorted_years else None,
            "year_2015": sample_by_year.get("2015"),
            "year_2014": sample_by_year.get("2014"),
        },
    }

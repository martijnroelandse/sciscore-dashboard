#!/usr/bin/env python3
"""Embed benchmark data from 2026_sciscore_v3 (by_year tab) into the dashboard HTML."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"
CLIENT_ORGS_PATH = ROOT / "scripts" / "client_orgs.json"
DEFAULT_XLSX = ROOT / "data" / "2026_sciscore_v3.xlsx"

# Top-level discipline flags in the xlsx (columns V–AZ).
DISCIPLINE_COL_START = 22  # V (1-based)
DISCIPLINE_COL_END = 52    # AZ inclusive (1-based)

RATE_KEYS = ["r", "sex", "pwr", "rand", "blind", "irb", "iacuc", "ab", "org", "cl", "tool"]
COUNT_KEYS = ["abn", "orgn", "cln", "tooln"]

BY_YEAR_ALIASES: dict[str, list[str]] = {
    "year": ["year", "pub_year", "publication year"],
    "n": ["n", "papers", "paper_count", "papers analysed", "papers analyzed", "count"],
    "r": ["r", "rti", "rigor", "rigor & transparency index", "rigor and transparency index"],
    "sex": ["sex", "sex_balance", "sex of subjects", "sex reporting"],
    "pwr": ["pwr", "power", "power analysis"],
    "rand": ["rand", "randomization", "randomisation"],
    "blind": ["blind", "blinding"],
    "irb": ["irb", "irb / ethics", "ethics", "irb approval"],
    "iacuc": ["iacuc"],
    "ab": ["ab", "antibodies", "antibody rrid", "antibodies w/ rrid"],
    "org": ["org", "organisms", "organism rrid", "organisms/models"],
    "cl": ["cl", "cell lines", "cell line rrid", "cell lines w/ rrid"],
    "tool": ["tool", "software", "software tools", "tools"],
    "abn": ["abn", "antibody detections"],
    "orgn": ["orgn", "organism detections"],
    "cln": ["cln", "cell line detections"],
    "tooln": ["tooln", "tool detections"],
}

JOURNAL_NAME_ALIASES = [
    "journal",
    "journal name",
    "journal title",
    "title",
    "name",
]


def find_xlsx(path: Path) -> Path | None:
    if path.exists():
        return path
    data_dir = ROOT / "data"
    if not data_dir.is_dir():
        return None
    matches = sorted(data_dir.glob("*.xlsx"))
    if len(matches) == 1:
        return matches[0]
    preferred = [p for p in matches if "sciscore" in p.name.lower() or "2026" in p.name]
    if len(preferred) == 1:
        return preferred[0]
    if matches:
        print("Multiple .xlsx files in data/ — using the first match:", matches[0], file=sys.stderr)
        return matches[0]
    return None


def extract_json_block(content: str, marker: str) -> dict:
    pattern = rf"const {marker} = (\{{.*?\}});"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find const {marker} in HTML")
    return json.loads(match.group(1))


def replace_const_block(content: str, marker: str, data) -> str:
    serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    pattern = rf"const {marker} = .*?;"
    replacement = f"const {marker} = {serialized};"
    if re.search(pattern, content, flags=re.DOTALL):
        return re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    raise ValueError(f"Could not find const {marker} in HTML")


def insert_or_replace_const_block(content: str, marker: str, data, after_marker: str) -> str:
    serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    pattern = rf"const {marker} = .*?;"
    replacement = f"const {marker} = {serialized};"
    if re.search(pattern, content, flags=re.DOTALL):
        return re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    anchor = rf"(const {after_marker} = .*?;\n)"
    match = re.search(anchor, content, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not find anchor const {after_marker} for inserting {marker}")
    return content[: match.end()] + replacement + "\n" + content[match.end() :]


def norm_header(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def map_headers(headers: list) -> dict[str, int]:
    normalized = [norm_header(h) for h in headers]
    mapping: dict[str, int] = {}
    for key, aliases in BY_YEAR_ALIASES.items():
        for alias in aliases:
            alias_norm = norm_header(alias)
            for idx, header in enumerate(normalized):
                if header == alias_norm or alias_norm in header:
                    mapping[key] = idx
                    break
            if key in mapping:
                break
    if "year" not in mapping:
        raise ValueError(f"Could not find a year column in by_year headers: {headers}")
    return mapping


def parse_rate(value):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.strip().replace("%", "")
        if not value:
            return None
    num = float(value)
    if num > 1.5:
        return num / 100.0
    return num


def parse_int(value):
    if value is None or value == "":
        return None
    return int(float(value))


def row_to_year_data(row: list, colmap: dict[str, int]) -> dict:
    out: dict = {}
    for key in RATE_KEYS + COUNT_KEYS + ["n"]:
        if key not in colmap:
            continue
        raw = row[colmap[key]] if colmap[key] < len(row) else None
        if key in COUNT_KEYS or key == "n":
            out[key] = parse_int(raw)
        else:
            out[key] = parse_rate(raw)
    return out


def read_by_year_xlsx(path: Path) -> dict[str, dict]:
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("openpyxl is required: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if "by_year" not in wb.sheetnames:
        raise ValueError(f"Sheet 'by_year' not found in {path}; sheets: {wb.sheetnames}")
    ws = wb["by_year"]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("by_year sheet is empty")

    headers = [str(c) if c is not None else "" for c in rows[0]]
    colmap = map_headers(headers)
    print("by_year columns mapped:", {k: headers[v] for k, v in sorted(colmap.items(), key=lambda x: x[1])})
    out: dict[str, dict] = {}
    for row in rows[1:]:
        if not row or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        year_raw = row[colmap["year"]]
        if year_raw is None:
            continue
        year = str(int(float(year_raw))) if str(year_raw).replace(".", "", 1).isdigit() else str(year_raw).strip()
        out[year] = row_to_year_data(list(row), colmap)
    if not out:
        raise ValueError("No year rows parsed from by_year sheet")
    return out


def is_truthy_cell(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if not text:
        return False
    return text in {"1", "true", "yes", "y", "x", "✓", "✔"} or text not in {"0", "false", "no", "n"}


def normalize_journal_name(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def detect_journal_name_column(headers: list[str], rows: list[tuple], known_journals: set[str]) -> int | None:
    known_lower = {name.lower(): name for name in known_journals}
    best_idx = None
    best_score = 0
    search_cols = min(8, len(headers))
    for idx in range(search_cols):
        score = 0
        for row in rows[:500]:
            if idx >= len(row):
                continue
            name = normalize_journal_name(row[idx])
            if not name:
                continue
            if name in known_journals:
                score += 2
            elif name.lower() in known_lower:
                score += 2
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx if best_score >= 5 else None


def read_journal_disciplines(path: Path, known_journals: set[str]) -> dict[str, list[str]]:
    """Read top-level discipline flags from columns V–AZ on the journal metadata sheet."""
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("openpyxl is required: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    skip = {"by_year", "summary", "readme", "index"}
    best_sheet = None
    best_name_col = None
    best_rows: list[tuple] = []
    best_headers: list[str] = []

    for sheet_name in wb.sheetnames:
        if sheet_name.lower() in skip:
            continue
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            continue
        headers = [str(c).strip() if c is not None else "" for c in rows[0]]
        name_col = detect_journal_name_column(headers, rows[1:], known_journals)
        if name_col is None:
            continue
        score = sum(
            1
            for row in rows[1:501]
            if name_col < len(row)
            and normalize_journal_name(row[name_col]) in known_journals
        )
        if score > len(best_rows):
            best_sheet = sheet_name
            best_name_col = name_col
            best_rows = rows
            best_headers = headers

    if best_sheet is None or best_name_col is None:
        print("WARNING: could not locate a journal sheet with discipline columns V–AZ", file=sys.stderr)
        return {}

    disc_start = DISCIPLINE_COL_START - 1
    disc_end = DISCIPLINE_COL_END
    discipline_headers = []
    for idx in range(disc_start, min(disc_end, len(best_headers))):
        label = str(best_headers[idx] or "").strip()
        if label:
            discipline_headers.append((idx, label))

    if not discipline_headers:
        print(
            f"WARNING: no discipline headers found in columns V–AZ on sheet '{best_sheet}'",
            file=sys.stderr,
        )
        return {}

    known_lower = {name.lower(): name for name in known_journals}
    out: dict[str, list[str]] = {}
    matched = 0
    for row in best_rows[1:]:
        if best_name_col >= len(row):
            continue
        raw_name = normalize_journal_name(row[best_name_col])
        if not raw_name:
            continue
        journal = raw_name if raw_name in known_journals else known_lower.get(raw_name.lower())
        if not journal:
            continue
        disciplines = []
        for idx, label in discipline_headers:
            if idx < len(row) and is_truthy_cell(row[idx]):
                disciplines.append(label)
        if disciplines:
            out[journal] = disciplines
            matched += 1

    print(
        f"Disciplines from sheet '{best_sheet}' (columns V–AZ): "
        f"{matched} journals tagged, {len(discipline_headers)} discipline columns"
    )
    return out


def aggregate_year(journals: dict, journal_names: list[str], year: str) -> dict | None:
    total_n = 0
    journal_count = 0
    weights = {k: 0.0 for k in RATE_KEYS}
    denominators = {k: 0.0 for k in RATE_KEYS}
    counts = {k: 0 for k in COUNT_KEYS}

    for name in journal_names:
        yd = journals.get(name, {}).get("y", {}).get(year)
        if not yd or not yd.get("n"):
            continue
        journal_count += 1
        total_n += int(yd["n"])
        for key in RATE_KEYS:
            if yd.get(key) is not None:
                weights[key] += float(yd[key]) * int(yd["n"])
                denominators[key] += int(yd["n"])
        for key in COUNT_KEYS:
            if yd.get(key) is not None:
                counts[key] += int(yd[key])

    if not total_n:
        return None
    out = {"n": total_n, "journalCount": journal_count}
    for key in RATE_KEYS:
        out[key] = weights[key] / denominators[key] if denominators[key] else None
    out.update(counts)
    return out


def benchmarks_for_journals(journals: dict, journal_names: list[str]) -> dict[str, dict]:
    years = sorted({year for name in journal_names for year in journals.get(name, {}).get("y", {})})
    out: dict[str, dict] = {}
    for year in years:
        agg = aggregate_year(journals, journal_names, year)
        if agg:
            out[year] = agg
    return out


def resolve_client_journals(journals: dict, client_cfg: dict) -> tuple[list[str], dict[str, list[str]]]:
    resolved: list[str] = []
    per_org: dict[str, list[str]] = {}
    all_names = set(journals.keys())

    for org, spec in client_cfg["orgs"].items():
        org_journals: list[str] = []
        for pub in spec.get("publishers", []):
            org_journals.extend(
                sorted(j for j, entry in journals.items() if entry.get("pub") == pub)
            )
        for journal in spec.get("journals", []):
            if journal in all_names:
                org_journals.append(journal)
        deduped = []
        seen = set()
        for journal in org_journals:
            if journal not in seen:
                seen.add(journal)
                deduped.append(journal)
        per_org[org] = deduped
        resolved.extend(deduped)

    final = []
    seen = set()
    for journal in resolved:
        if journal not in seen:
            seen.add(journal)
            final.append(journal)
    return final, per_org


def build_discipline_index(journals: dict, journal_disciplines: dict[str, list[str]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for journal, disciplines in journal_disciplines.items():
        if journal not in journals:
            continue
        for discipline in disciplines:
            index.setdefault(discipline, []).append(journal)
    for discipline in index:
        index[discipline] = sorted(set(index[discipline]))
    return index


def apply_disciplines_to_data(journals: dict, journal_disciplines: dict[str, list[str]]) -> int:
    updated = 0
    for journal, disciplines in journal_disciplines.items():
        if journal not in journals:
            continue
        clean = sorted(set(d.strip() for d in disciplines if d and str(d).strip()))
        if clean:
            journals[journal]["disciplines"] = clean
            updated += 1
    return updated


def build_benchmark_catalog(
    client_cfg: dict,
    per_org: dict[str, list[str]],
    discipline_index: dict[str, list[str]],
) -> list[dict]:
    catalog = [
        {"id": "all", "label": "All journals", "group": "General"},
        {"id": "clients", "label": client_cfg.get("label", "SciScore clients"), "group": "General"},
    ]
    for org in sorted(per_org):
        if per_org[org]:
            catalog.append({"id": f"org:{org}", "label": org, "group": "Client orgs"})
    for discipline in sorted(discipline_index):
        if discipline_index[discipline]:
            catalog.append(
                {
                    "id": f"discipline:{discipline}",
                    "label": discipline,
                    "group": "Disciplines",
                }
            )
    return catalog


def build_benchmark_by_key(
    by_year: dict[str, dict],
    client_by_year: dict[str, dict],
    per_org: dict[str, list[str]],
    journals: dict,
    discipline_index: dict[str, list[str]],
) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {"all": by_year, "clients": client_by_year}
    for org, names in per_org.items():
        if names:
            series = benchmarks_for_journals(journals, names)
            if series:
                out[f"org:{org}"] = series
    for discipline, names in discipline_index.items():
        if names:
            series = benchmarks_for_journals(journals, names)
            if series:
                out[f"discipline:{discipline}"] = series
    return out


def compute_by_year_fallback(journals: dict) -> dict[str, dict]:
    years = sorted({year for entry in journals.values() for year in entry.get("y", {})})
    out = {}
    for year in years:
        agg = aggregate_year(journals, list(journals.keys()), year)
        if agg:
            out[year] = agg
    return out


def main() -> None:
    requested = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSX
    xlsx_path = find_xlsx(requested)
    content = HTML.read_text(encoding="utf-8")
    data = extract_json_block(content, "DATA")
    journals = data["j"]
    client_cfg = json.loads(CLIENT_ORGS_PATH.read_text(encoding="utf-8"))

    source = "2026_sciscore_v3.xlsx/by_year"
    if xlsx_path:
        by_year = read_by_year_xlsx(xlsx_path)
        source = f"{xlsx_path.name}/by_year"
        print(f"Loaded by_year benchmarks from {xlsx_path} ({len(by_year)} years)")
    else:
        by_year = compute_by_year_fallback(journals)
        source = "computed_fallback_from_DATA"
        print(
            f"WARNING: no .xlsx found at {requested} or in data/\n"
            "Place 2026_sciscore_v3.xlsx in data/ and re-run.\n"
            "Using paper-weighted all-journal averages from embedded DATA as fallback.",
            file=sys.stderr,
        )

    journal_disciplines: dict[str, list[str]] = {}
    if xlsx_path:
        journal_disciplines = read_journal_disciplines(xlsx_path, set(journals.keys()))
        tagged = apply_disciplines_to_data(journals, journal_disciplines)
        print(f"Applied discipline tags to {tagged} journals in embedded DATA")

    client_journal_names, per_org = resolve_client_journals(journals, client_cfg)
    client_by_year = benchmarks_for_journals(journals, client_journal_names)
    discipline_index = build_discipline_index(journals, journal_disciplines)
    benchmark_by_key = build_benchmark_by_key(
        by_year, client_by_year, per_org, journals, discipline_index
    )
    benchmark_catalog = build_benchmark_catalog(client_cfg, per_org, discipline_index)

    meta = {
        "source": source,
        "clientLabel": client_cfg.get("label", "SciScore clients"),
        "clientOrgs": list(client_cfg["orgs"].keys()),
        "clientJournalCount": len(client_journal_names),
        "clientJournalsByOrg": {org: len(items) for org, items in per_org.items()},
        "disciplineCount": len(discipline_index),
        "disciplinesTaggedJournalCount": len(journal_disciplines),
    }

    print("Client org journal counts:")
    for org, items in per_org.items():
        print(f"  {org}: {len(items)} journals")
    missing_orgs = [org for org, items in per_org.items() if not items]
    if missing_orgs:
        print(f"  (no journals matched: {', '.join(missing_orgs)})")
    if discipline_index:
        print(f"Discipline benchmarks: {len(discipline_index)} top-level fields")

    content = replace_const_block(content, "DATA", data)
    content = replace_const_block(content, "BY_YEAR_BENCHMARK", by_year)
    content = replace_const_block(content, "CLIENT_ORG_BENCHMARK", client_by_year)
    content = replace_const_block(content, "CLIENT_ORG_META", meta)
    content = replace_const_block(content, "CLIENT_ORG_JOURNALS", client_journal_names)
    content = insert_or_replace_const_block(
        content, "CLIENT_ORG_JOURNALS_BY_ORG", per_org, "CLIENT_ORG_JOURNALS"
    )
    content = insert_or_replace_const_block(
        content, "BENCHMARK_CATALOG", benchmark_catalog, "CLIENT_ORG_JOURNALS_BY_ORG"
    )
    content = insert_or_replace_const_block(
        content, "BENCHMARK_BY_KEY", benchmark_by_key, "BENCHMARK_CATALOG"
    )
    HTML.write_text(content, encoding="utf-8")
    print(
        f"Embedded {len(benchmark_catalog)} compare options "
        f"and {len(benchmark_by_key)} benchmark series"
    )


if __name__ == "__main__":
    main()

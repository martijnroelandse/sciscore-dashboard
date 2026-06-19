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

RATE_KEYS = ["r", "sex", "pwr", "rand", "blind", "irb", "iacuc", "ab", "org", "cl", "tool"]
COUNT_KEYS = ["abn", "orgn", "cln", "tooln"]

# Flexible header mapping for the by_year sheet (case-insensitive).
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
    return re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)


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


def compute_by_year_fallback(journals: dict) -> dict[str, dict]:
  """Fallback when xlsx is unavailable: paper-weighted all-journal averages."""
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

    client_journal_names, per_org = resolve_client_journals(journals, client_cfg)
    client_years = sorted({year for name in client_journal_names for year in journals[name].get("y", {})})
    client_by_year = {}
    for year in client_years:
        agg = aggregate_year(journals, client_journal_names, year)
        if agg:
            client_by_year[year] = agg

    meta = {
        "source": source,
        "clientLabel": client_cfg.get("label", "SciScore clients"),
        "clientOrgs": list(client_cfg["orgs"].keys()),
        "clientJournalCount": len(client_journal_names),
        "clientJournalsByOrg": {org: len(items) for org, items in per_org.items()},
    }

    print("Client org journal counts:")
    for org, items in per_org.items():
        print(f"  {org}: {len(items)} journals")
    missing_orgs = [org for org, items in per_org.items() if not items]
    if missing_orgs:
        print(f"  (no journals matched: {', '.join(missing_orgs)})")

    content = replace_const_block(content, "BY_YEAR_BENCHMARK", by_year)
    content = replace_const_block(content, "CLIENT_ORG_BENCHMARK", client_by_year)
    content = replace_const_block(content, "CLIENT_ORG_META", meta)
    content = replace_const_block(content, "CLIENT_ORG_JOURNALS", client_journal_names)
    HTML.write_text(content, encoding="utf-8")
    print(f"Embedded benchmarks for {len(by_year)} corpus years and {len(client_by_year)} client-org years")


if __name__ == "__main__":
    main()

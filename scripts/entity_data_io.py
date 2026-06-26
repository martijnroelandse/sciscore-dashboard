"""Read JMIR-style country/institution-year metrics and build dashboard DATA."""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

COUNTRY_CSV_NAMES = (
    "jmir_v24i6e37324_app5_by_country_by_year.csv",
    "*by_country_by_year*.csv",
)
INSTITUTION_CSV_NAMES = (
    "jmir_v24i6e37324_app5_by_institution_by_year.csv",
    "*by_institution_by_year*.csv",
)

EMBEDDED_KEYS = {
    "n", "r", "sex", "pwr", "rand", "blind", "irb", "iacuc",
    "ab", "org", "cl", "tool", "abn", "orgn", "cln", "tooln",
    "data", "code", "prot", "data_id", "code_id", "datan", "coden", "protn",
}


def _num(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace("%", "").replace(",", "")
    if not text or text.upper() == "NULL":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _int(value) -> int | None:
    num = _num(value)
    if num is None:
        return None
    return int(num)


def _rate(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den <= 0:
        return None
    return num / den


def _header_index(headers: list[str]) -> dict[str, int]:
    return {name: i for i, name in enumerate(headers)}


def is_jmir_entity_export(headers: list[str]) -> bool:
    joined = {h.strip() for h in headers if h}
    return "pub_year" in joined and "pmid_count" in joined and "RTI" in joined


def find_csv(candidates: tuple[str, ...]) -> Path | None:
    if not DATA_DIR.is_dir():
        return None
    seen: set[Path] = set()
    for name in candidates:
        if "*" in name:
            for path in sorted(DATA_DIR.glob(name)):
                if path.is_file() and path not in seen:
                    return path
        else:
            path = DATA_DIR / name
            if path.is_file():
                return path
    # fallback: repo root (legacy location)
    for name in candidates:
        if "*" not in name:
            path = ROOT / name
            if path.is_file():
                return path
    return None


def find_country_csv() -> Path | None:
    return find_csv(COUNTRY_CSV_NAMES)


def find_institution_csv() -> Path | None:
    return find_csv(INSTITUTION_CSV_NAMES)


def read_csv_rows(path: Path) -> list[tuple]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [tuple(row) for row in csv.reader(handle)]


def row_to_metrics(row: list, idx: dict[str, int]) -> dict | None:
    """Map JMIR entity export row to dashboard short metric keys."""
    n = _int(row[idx["pmid_count"]])
    r = _num(row[idx["RTI"]])
    if not n and r is None:
        return None

    metrics: dict = {}
    if n is not None:
        metrics["n"] = n
    if r is not None:
        metrics["r"] = round(r, 1)

    sex_detected = _num(row[idx["sex_detected"]])
    if n and sex_detected is not None:
        metrics["sex"] = sex_detected / n

    for key, col in (
        ("pwr", "avg(power)"),
        ("rand", "avg(randomization)"),
        ("blind", "avg(blinding)"),
    ):
        val = _num(row[idx[col]]) if col in idx else None
        if val is not None:
            metrics[key] = val

    for key, col in (("irb", "sum(irb)"), ("iacuc", "sum(iacuc)")):
        total = _int(row[idx[col]]) if col in idx else None
        if n and total is not None:
            metrics[key] = total / n

    resource_pairs = (
        ("ab", "antibody_findable", "sum(antibody_detected)", "abn"),
        ("org", "organism_findable", "sum(organism_detected)", "orgn"),
        ("cl", "cell_line_findable", "sum(cell_line_detected)", "cln"),
        ("tool", "tool_findable", "sum(tool_detected)", "tooln"),
    )
    for rate_key, findable_col, detected_col, count_key in resource_pairs:
        detected = _int(row[idx[detected_col]])
        findable = _int(row[idx[findable_col]])
        if detected is not None:
            metrics[count_key] = detected
        rate = _rate(float(findable or 0), float(detected or 0)) if detected else None
        if rate is not None:
            metrics[rate_key] = rate

    open_science = (
        ("data", "sum(data_availability)", "datan"),
        ("code", "sum(code_availability)", "coden"),
        ("prot", "sum(protocol_id_detected)", "protn"),
        ("data_id", "sum(data_id_detected)", None),
        ("code_id", "sum(code_id_detected)", None),
    )
    for rate_key, sum_col, count_key in open_science:
        if sum_col not in idx:
            continue
        total = _int(row[idx[sum_col]])
        if total is not None and count_key:
            metrics[count_key] = total
        if n and total is not None:
            metrics[rate_key] = total / n

    return metrics


def merge_year_metrics(existing: dict | None, incoming: dict) -> dict:
    if not existing:
        return incoming
    if int(incoming.get("n") or 0) >= int(existing.get("n") or 0):
        return incoming
    return existing


def entity_key(name: str, country: str = "") -> str:
    name = name.strip()
    country = country.strip()
    if country:
        return f"{name}|{country}"
    return name


def parse_entity_key(key: str) -> tuple[str, str]:
    if "|" in key:
        name, country = key.rsplit("|", 1)
        return name, country
    return key, ""


def _normalize_year(year_raw: str) -> str:
    year_raw = year_raw.strip()
    if year_raw.replace(".", "", 1).isdigit():
        return str(int(float(year_raw)))
    return year_raw


def build_country_data(rows: list[tuple]) -> tuple[dict, dict]:
    if not rows:
        raise ValueError("Input is empty")

    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    if not is_jmir_entity_export(headers):
        raise ValueError(f"Unrecognised country export headers: {headers[:8]}")

    idx = _header_index(headers)
    country_col = headers.index("country")
    countries: dict[str, dict] = {}
    years = Counter()
    metric_presence: Counter[str] = Counter()

    for row in rows[1:]:
        if not row or not row[country_col].strip():
            continue
        year = _normalize_year(row[idx["pub_year"]].strip() if idx["pub_year"] < len(row) else "")
        if not year:
            continue
        metrics = row_to_metrics(list(row), idx)
        if not metrics:
            continue

        cname = row[country_col].strip()
        entry = countries.setdefault(cname, {"y": {}})
        entry["y"][year] = merge_year_metrics(entry["y"].get(year), metrics)
        years[year] += 1
        for key, val in metrics.items():
            if val is not None:
                metric_presence[key] += 1

    meta = {
        "format": "jmir_by_country_by_year",
        "entity_count": len(countries),
        "row_count": sum(years.values()),
        "years": dict(sorted(years.items(), key=lambda x: int(x[0]))),
        "metric_presence": dict(sorted(metric_presence.items())),
    }
    return {"c": countries}, meta


def build_institution_data(
    rows: list[tuple],
    ror_matches: dict[str, dict] | None = None,
) -> tuple[dict, dict]:
    if not rows:
        raise ValueError("Input is empty")

    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    if not is_jmir_entity_export(headers):
        raise ValueError(f"Unrecognised institution export headers: {headers[:8]}")

    idx = _header_index(headers)
    name_col = headers.index("name")
    institutions: dict[str, dict] = {}
    by_country: dict[str, list[str]] = defaultdict(list)
    years = Counter()
    metric_presence: Counter[str] = Counter()
    ror_matches = ror_matches or {}

    for row in rows[1:]:
        if not row or not row[name_col].strip():
            continue
        year = _normalize_year(row[idx["pub_year"]].strip() if idx["pub_year"] < len(row) else "")
        if not year:
            continue
        metrics = row_to_metrics(list(row), idx)
        if not metrics:
            continue

        name = row[name_col].strip()
        country = row[idx["country"]].strip() if "country" in idx and idx["country"] < len(row) else ""
        state = row[idx["state"]].strip() if "state" in idx and idx["state"] < len(row) else ""
        established = _int(row[idx["established"]]) if "established" in idx else None

        key = entity_key(name, country)
        entry = institutions.setdefault(key, {
            "name": name,
            "country": country,
            "y": {},
        })
        if country and not entry.get("country"):
            entry["country"] = country
        if state and state.upper() != "NULL":
            entry["state"] = state
        if established and not entry.get("established"):
            entry["established"] = established

        ror = ror_matches.get(key) or ror_matches.get(name)
        if ror:
            entry["ror"] = ror

        entry["y"][year] = merge_year_metrics(entry["y"].get(year), metrics)
        years[year] += 1
        for key_name, val in metrics.items():
            if val is not None:
                metric_presence[key_name] += 1

    for key, entry in institutions.items():
        country = entry.get("country") or ""
        if country and key not in by_country[country]:
            by_country[country].append(key)

    for country in by_country:
        by_country[country] = sorted(by_country[country])

    meta = {
        "format": "jmir_by_institution_by_year",
        "entity_count": len(institutions),
        "row_count": sum(years.values()),
        "country_count": len(by_country),
        "years": dict(sorted(years.items(), key=lambda x: int(x[0]))),
        "metric_presence": dict(sorted(metric_presence.items())),
        "ror_matched": sum(1 for e in institutions.values() if e.get("ror")),
    }
    return {
        "i": institutions,
        "by_country": dict(sorted(by_country.items())),
    }, meta


def load_ror_matches(path: Path | None = None) -> dict[str, dict]:
    """Load ROR match results keyed by entity_key or institution name."""
    path = path or DATA_DIR / "ror_matches.json"
    if not path.is_file():
        return {}
    import json

    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for key, val in raw.items():
        if isinstance(val, dict):
            out[key] = val
    return out


def inspect_entity_rows(rows: list[tuple], entity_type: str) -> dict:
    if entity_type == "country":
        _, meta = build_country_data(rows)
    else:
        _, meta = build_institution_data(rows)
    return meta

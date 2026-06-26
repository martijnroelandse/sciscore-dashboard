#!/usr/bin/env python3
"""Match institution names to ROR IDs via the public ROR API.

Strategies (in order):
  1. Affiliation parameter with name + state + country
  2. Query parameter with country filter
  3. Query parameter without filter (name only)

Results are written to data/ror_matches.json keyed by entity_key (name|country).
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from entity_data_io import entity_key, find_institution_csv, read_csv_rows

ROR_API = "https://api.ror.org/v2/organizations"
OUTPUT = ROOT / "data" / "ror_matches.json"
REVIEW_CSV = ROOT / "data" / "ror_match_review.csv"

MIN_INTERVAL = 0.22
_last_request = 0.0


def _throttle() -> None:
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _last_request = time.time()


def _fetch_json(url: str) -> dict | None:
    _throttle()
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        print(f"  WARN: {exc}", file=sys.stderr)
        return None


def _normalize_name(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


def _primary_name(org: dict) -> str:
    names = org.get("names") or []
    for item in names:
        if item.get("types") and "ror_display" in item["types"]:
            return item.get("value", "")
    return names[0].get("value", "") if names else ""


def _country_name(org: dict) -> str:
    locs = org.get("locations") or []
    if not locs:
        return ""
    geo = locs[0].get("geonames_details") or {}
    return geo.get("country_name") or ""


def _extract_hierarchy(org: dict) -> dict:
    parents: list[dict] = []
    children: list[dict] = []
    related: list[dict] = []

    for rel in org.get("relationships") or []:
        entry = {
            "id": rel.get("id", ""),
            "label": rel.get("label", ""),
            "type": rel.get("type", ""),
        }
        rtype = (rel.get("type") or "").lower()
        if rtype == "parent":
            parents.append(entry)
        elif rtype == "child":
            children.append(entry)
        else:
            related.append(entry)

    return {"parents": parents, "children": children, "related": related}


def _org_to_match(org: dict, method: str, score: float = 1.0) -> dict:
    hierarchy = _extract_hierarchy(org)
    return {
        "id": org.get("id", ""),
        "name": _primary_name(org),
        "types": org.get("types") or [],
        "country": _country_name(org),
        "established": org.get("established"),
        "method": method,
        "score": round(score, 3),
        "chosen": method.startswith("affiliation"),
        "parents": hierarchy["parents"],
        "children": hierarchy["children"],
        "related": hierarchy["related"],
    }


def _affiliation_string(name: str, country: str, state: str = "") -> str:
    parts = [name]
    if state and state.upper() != "NULL":
        parts.append(state)
    if country:
        parts.append(country)
    return ", ".join(parts)


def match_affiliation(name: str, country: str, state: str = "") -> dict | None:
    aff = _affiliation_string(name, country, state)
    url = f"{ROR_API}?affiliation={urllib.parse.quote(aff)}"
    data = _fetch_json(url)
    if not data:
        return None
    for item in data.get("items") or []:
        if item.get("chosen") and item.get("organization"):
            return _org_to_match(item["organization"], "affiliation", 1.0)
    return None


def match_query(name: str, country: str = "") -> dict | None:
    query = urllib.parse.quote(name)
    if country:
        filt = urllib.parse.quote(f"country.country_name:{country}")
        url = f"{ROR_API}?query={query}&filter={filt}"
    else:
        url = f"{ROR_API}?query={query}"
    data = _fetch_json(url)
    if not data:
        return None

    items = data.get("items") or []
    if not items:
        return None

    best = None
    best_score = 0.0
    for org in items[:10]:
        ror_name = _primary_name(org)
        score = _similarity(name, ror_name)
        if country:
            org_country = _country_name(org)
            if org_country and _normalize_name(org_country) != _normalize_name(country):
                score *= 0.5
        if score > best_score:
            best_score = score
            best = org

    if best and best_score >= 0.55:
        return _org_to_match(best, f"query({best_score:.2f})", best_score)
    return None


def match_institution(name: str, country: str, state: str = "") -> dict | None:
    result = match_affiliation(name, country, state)
    if result:
        return result
    result = match_query(name, country)
    if result:
        return result
    return match_query(name)


def unique_institutions(rows: list[tuple]) -> list[dict]:
    headers = [str(h).strip() if h else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(headers)}
    name_col = headers.index("name")
    seen: set[str] = set()
    out: list[dict] = []

    for row in rows[1:]:
        if not row or not row[name_col].strip():
            continue
        name = row[name_col].strip()
        country = row[idx["country"]].strip() if "country" in idx else ""
        state = row[idx["state"]].strip() if "state" in idx else ""
        key = entity_key(name, country)
        if key in seen:
            continue
        seen.add(key)
        out.append({"key": key, "name": name, "country": country, "state": state})
    return out


def load_existing() -> dict[str, dict]:
    if OUTPUT.is_file():
        return json.loads(OUTPUT.read_text(encoding="utf-8"))
    return {}


def save_matches(matches: dict[str, dict]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(matches, indent=2, ensure_ascii=False), encoding="utf-8")


def write_review_csv(institutions: list[dict], matches: dict[str, dict]) -> None:
    import csv

    REVIEW_CSV.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "entity_key", "csv_name", "country", "ror_id", "ror_name",
            "method", "score", "parent_count", "child_count", "status",
        ])
        for inst in institutions:
            key = inst["key"]
            m = matches.get(key)
            if m:
                writer.writerow([
                    key, inst["name"], inst["country"],
                    m.get("id", ""), m.get("name", ""),
                    m.get("method", ""), m.get("score", ""),
                    len(m.get("parents") or []), len(m.get("children") or []),
                    "matched",
                ])
            else:
                writer.writerow([
                    key, inst["name"], inst["country"],
                    "", "", "", "", "", "", "unmatched",
                ])


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Match institutions to ROR IDs")
    parser.add_argument("--limit", type=int, default=0, help="Max institutions to match (0=all)")
    parser.add_argument("--resume", action="store_true", help="Skip already-matched keys")
    parser.add_argument("--sample", type=int, default=0, help="Match N institutions for testing")
    args = parser.parse_args()

    path = find_institution_csv()
    if not path:
        print("No institution CSV found in data/", file=sys.stderr)
        return 1

    print(f"Reading {path}")
    rows = read_csv_rows(path)
    institutions = unique_institutions(rows)
    print(f"Unique institutions: {len(institutions):,}")

    if args.sample:
        import random
        random.seed(42)
        institutions = random.sample(institutions, min(args.sample, len(institutions)))
        print(f"Sample mode: {len(institutions)} institutions")

    matches = load_existing() if args.resume else {}
    if not args.resume and OUTPUT.is_file():
        print(f"Overwriting {OUTPUT}")

    todo = [inst for inst in institutions if not (args.resume and inst["key"] in matches)]
    if args.limit:
        todo = todo[: args.limit]

    print(f"Matching {len(todo):,} institutions...")
    for i, inst in enumerate(todo, 1):
        if i % 25 == 0 or i == 1:
            print(f"  [{i}/{len(todo)}] {inst['name'][:50]}...")
        result = match_institution(inst["name"], inst["country"], inst.get("state", ""))
        if result:
            matches[inst["key"]] = result

    save_matches(matches)
    write_review_csv(institutions, matches)

    matched = sum(1 for inst in institutions if inst["key"] in matches)
    print(f"Matched: {matched:,} / {len(institutions):,} ({100 * matched / len(institutions):.1f}%)")
    print(f"Wrote {OUTPUT}")
    print(f"Wrote {REVIEW_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

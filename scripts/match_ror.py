#!/usr/bin/env python3
"""Match institution names to ROR IDs.

Default: local matching against the Zenodo ROR data dump (fast, no rate limits).
Use --api for the public ROR affiliation/query API (slow, rate-limited).

Results: data/ror_matches.json keyed by entity_key (name|country).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from entity_data_io import entity_key, find_institution_csv, read_csv_rows

OUTPUT = ROOT / "data" / "ror_matches.json"
REVIEW_CSV = ROOT / "data" / "ror_match_review.csv"


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


def match_local(institutions: list[dict], matches: dict, todo: list[dict]) -> None:
    from ror_local import RorLocalIndex

    index = RorLocalIndex.load()
    for i, inst in enumerate(todo, 1):
        if i % 500 == 0 or i == 1:
            print(f"  [{i}/{len(todo)}] {inst['name'][:50]}...")
        result = index.match(inst["name"], inst["country"], inst.get("state", ""))
        if result:
            matches[inst["key"]] = result


def match_api(institutions: list[dict], matches: dict, todo: list[dict]) -> None:
    """Legacy API matcher (rate-limited)."""
    import re
    import time
    import urllib.error
    import urllib.parse
    import urllib.request
    from difflib import SequenceMatcher

    ROR_API = "https://api.ror.org/v2/organizations"
    MIN_INTERVAL = 0.22
    last_request = 0.0

    def throttle() -> None:
        nonlocal last_request
        elapsed = time.time() - last_request
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        last_request = time.time()

    def fetch_json(url: str) -> dict | None:
        throttle()
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return None

    def normalize_name(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        return re.sub(r"\s+", " ", text)

    def primary_name(org: dict) -> str:
        for item in org.get("names") or []:
            if item.get("types") and "ror_display" in item["types"]:
                return item.get("value", "")
        names = org.get("names") or []
        return names[0].get("value", "") if names else ""

    def country_name(org: dict) -> str:
        locs = org.get("locations") or []
        if not locs:
            return ""
        return (locs[0].get("geonames_details") or {}).get("country_name") or ""

    def org_to_match(org: dict, method: str, score: float = 1.0) -> dict:
        parents, children, related = [], [], []
        for rel in org.get("relationships") or []:
            entry = {"id": rel.get("id", ""), "label": rel.get("label", ""), "type": rel.get("type", "")}
            rtype = (rel.get("type") or "").lower()
            if rtype == "parent":
                parents.append(entry)
            elif rtype == "child":
                children.append(entry)
            else:
                related.append(entry)
        return {
            "id": org.get("id", ""), "name": primary_name(org), "types": org.get("types") or [],
            "country": country_name(org), "established": org.get("established"),
            "method": method, "score": round(score, 3), "chosen": method.startswith("affiliation"),
            "parents": parents, "children": children, "related": related,
        }

    def match_one(name: str, country: str, state: str = "") -> dict | None:
        parts = [name]
        if state and state.upper() != "NULL":
            parts.append(state)
        if country:
            parts.append(country)
        aff = ", ".join(parts)
        url = f"{ROR_API}?affiliation={urllib.parse.quote(aff)}"
        data = fetch_json(url)
        if data:
            for item in data.get("items") or []:
                if item.get("chosen") and item.get("organization"):
                    return org_to_match(item["organization"], "affiliation", 1.0)
        query = urllib.parse.quote(name)
        if country:
            filt = urllib.parse.quote(f"country.country_name:{country}")
            url = f"{ROR_API}?query={query}&filter={filt}"
        else:
            url = f"{ROR_API}?query={query}"
        data = fetch_json(url)
        if not data:
            return None
        items = data.get("items") or []
        best, best_score = None, 0.0
        for org in items[:10]:
            score = SequenceMatcher(None, normalize_name(name), normalize_name(primary_name(org))).ratio()
            if country:
                oc = country_name(org)
                if oc and normalize_name(oc) != normalize_name(country):
                    score *= 0.5
            if score > best_score:
                best_score, best = score, org
        if best and best_score >= 0.55:
            return org_to_match(best, f"query({best_score:.2f})", best_score)
        return None

    for i, inst in enumerate(todo, 1):
        if i % 25 == 0 or i == 1:
            print(f"  [{i}/{len(todo)}] {inst['name'][:50]}...")
        result = match_one(inst["name"], inst["country"], inst.get("state", ""))
        if result:
            matches[inst["key"]] = result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Match institutions to ROR IDs")
    parser.add_argument("--api", action="store_true", help="Use ROR API instead of local dump")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild local ROR index cache")
    parser.add_argument("--download", action="store_true", help="Force re-download ROR data dump")
    parser.add_argument("--limit", type=int, default=0, help="Max institutions to match (0=all)")
    parser.add_argument("--resume", action="store_true", help="Skip already-matched keys")
    parser.add_argument("--sample", type=int, default=0, help="Match N institutions for testing")
    args = parser.parse_args()

    if args.download or args.rebuild_index:
        from ror_local import RorLocalIndex, ensure_ror_dump
        ensure_ror_dump(force=args.download)
        if args.rebuild_index:
            RorLocalIndex.load(force_rebuild=True)
            print("Index rebuilt.")
            if not args.limit and not args.sample:
                return 0

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

    mode = "API (rate-limited)" if args.api else "local ROR dump"
    print(f"Matching {len(todo):,} institutions via {mode}...")
    if args.api:
        match_api(institutions, matches, todo)
    else:
        match_local(institutions, matches, todo)

    save_matches(matches)
    write_review_csv(institutions, matches)

    matched = sum(1 for inst in institutions if inst["key"] in matches)
    print(f"Matched: {matched:,} / {len(institutions):,} ({100 * matched / len(institutions):.1f}%)")
    print(f"Wrote {OUTPUT}")
    print(f"Wrote {REVIEW_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

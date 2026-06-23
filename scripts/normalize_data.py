#!/usr/bin/env python3
"""Normalize embedded dashboard DATA: dedupe journals, split Springer Nature sub-brands."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"
GROUP_MAP_PATH = ROOT / "scripts" / "group_map.json"

SN_GROUP = "Springer Nature"
SN_SUB_BRANDS = ("BMC", "Nature Portfolio", "EMBO", "Springer Nature")
PUBLISHER_OVERRIDES = {
    "Journal of the American Heart Association: Cardiovascular and Cerebrovascular Disease": "American Heart Association",
    "The Journal of Cell Biology": "Rockefeller University Press",
    "The Journal of Experimental Medicine": "Rockefeller University Press",
    "The FASEB Journal": "Federation of American Societies for Experimental Biology",
}


def extract_json_block(content: str, marker: str) -> dict:
    pattern = rf"const {marker} = (\{{.*?\}});"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find const {marker} in HTML")
    return json.loads(match.group(1))


def replace_json_block(content: str, marker: str, data: dict) -> str:
    serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    pattern = rf"const {marker} = \{{.*?\}};"
    replacement = f"const {marker} = {serialized};"
    return re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)


def total_papers(journal: dict) -> int:
    return sum(int(yd.get("n") or 0) for yd in journal.get("y", {}).values())


def title_score(name: str) -> int:
    return sum(1 for word in name.split() if word and word[0].isupper())


def pick_canonical_name(names: list[str], journals: dict) -> str:
    def score(name: str) -> tuple[int, int, str]:
        return (title_score(name), total_papers(journals[name]), name)

    return max(names, key=score)


def merge_year_entries(a: dict, b: dict) -> dict:
    na, nb = int(a.get("n") or 0), int(b.get("n") or 0)
    return a if na >= nb else b


def dedupe_journals(journals: dict) -> tuple[dict, dict[str, str]]:
    by_lower: dict[str, list[str]] = defaultdict(list)
    for name in journals:
        by_lower[name.lower()].append(name)

    merged: dict = {}
    rename: dict[str, str] = {}

    for variants in by_lower.values():
        canonical = pick_canonical_name(variants, journals)
        entry = {"pub": journals[canonical]["pub"], "y": {}}
        for name in variants:
            for year, yd in journals[name]["y"].items():
                if year not in entry["y"]:
                    entry["y"][year] = dict(yd)
                else:
                    entry["y"][year] = merge_year_entries(entry["y"][year], yd)
            if name != canonical:
                rename[name] = canonical
        merged[canonical] = entry

    return merged, rename


def sn_sub_brand(journal_name: str) -> str:
    upper = journal_name.upper()
    if upper.startswith("EMBO ") or upper == "EMBO" or upper.startswith("THE EMBO "):
        return "EMBO"
    if journal_name.startswith("BMC ") or journal_name == "BMC":
        return "BMC"
    if journal_name.startswith("Nature ") or journal_name == "Nature":
        return "Nature Portfolio"
    return "Springer Nature"


def apply_sn_sub_brands(journals: dict) -> int:
    changed = 0
    for journal, entry in journals.items():
        brand = sn_sub_brand(journal)
        if brand == SN_GROUP:
            continue
        pub = entry.get("pub") or ""
        if brand == "EMBO":
            if pub != "EMBO":
                entry["pub"] = "EMBO"
                changed += 1
            continue
        if pub != "Springer Nature":
            continue
        if brand != pub:
            entry["pub"] = brand
            changed += 1
    return changed


def apply_publisher_overrides(journals: dict) -> int:
    changed = 0
    for journal, publisher in PUBLISHER_OVERRIDES.items():
        if journal not in journals:
            continue
        if journals[journal].get("pub") != publisher:
            journals[journal]["pub"] = publisher
            changed += 1
    return changed


def rebuild_publishers(journals: dict) -> dict[str, list[str]]:
    publishers: dict[str, list[str]] = defaultdict(list)
    for journal, entry in journals.items():
        publishers[entry.get("pub") or ""].append(journal)
    for pub in publishers:
        publishers[pub].sort(key=str.lower)
    return dict(publishers)


def update_group_map(group_map: dict, publishers: list[str]) -> dict:
    updated = dict(group_map)

    # Springer Publishing Company is unrelated to Springer Nature.
    updated.pop("Springer Publishing Company", None)

    for brand in SN_SUB_BRANDS:
        if brand in publishers:
            updated[brand] = SN_GROUP

    if "Springer Nature Korea" in publishers:
        updated["Springer Nature Korea"] = SN_GROUP

    return updated


def format_group_map_js(group_map: dict) -> str:
    lines = ["const GROUP_MAP = {"]
    for pub in sorted(group_map):
        grp = group_map[pub]
        lines.append(f'  {json.dumps(pub)}: {json.dumps(grp)},')
    lines.append("};")
    return "\n".join(lines)


def main() -> None:
    content = HTML.read_text(encoding="utf-8")
    data = extract_json_block(content, "DATA")
    group_map = json.loads(GROUP_MAP_PATH.read_text(encoding="utf-8"))

    journals_before = len(data["j"])
    journals, renamed = dedupe_journals(data["j"])
    override_updates = apply_publisher_overrides(journals)
    sn_split = apply_sn_sub_brands(journals)
    publishers = rebuild_publishers(journals)
    group_map = update_group_map(group_map, list(publishers.keys()))

    data = {"j": journals, "p": publishers}
    content = replace_json_block(content, "DATA", data)

    group_map_js = format_group_map_js(group_map)
    content = re.sub(
        r"const GROUP_MAP = \{.*?\};",
        group_map_js,
        content,
        count=1,
        flags=re.DOTALL,
    )

    HTML.write_text(content, encoding="utf-8")
    GROUP_MAP_PATH.write_text(
        json.dumps(group_map, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    sn_pubs = [p for p in publishers if p in SN_SUB_BRANDS or p == "Springer Nature Korea"]
    print(f"Journals: {journals_before} -> {len(journals)} ({len(renamed)} merged)")
    print(f"Publisher overrides applied: {override_updates}")
    print(f"Springer Nature sub-brand reassignment: {sn_split} journals")
    print(f"SN group publishers: {', '.join(f'{p} ({len(publishers[p])})' for p in sorted(sn_pubs))}")
    blood = [n for n in journals if n.lower() == "blood research"]
    print(f"Blood Research entries: {blood}")


if __name__ == "__main__":
    main()

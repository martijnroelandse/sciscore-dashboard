"""Compute corpus-wide BY_YEAR_BENCHMARK from embedded entity DATA."""
from __future__ import annotations

from collections import defaultdict

RATE_KEYS = [
    "r", "sex", "pwr", "rand", "blind", "irb", "iacuc",
    "ab", "org", "cl", "tool", "data", "code", "prot", "data_id", "code_id",
]
COUNT_KEYS = ["abn", "orgn", "cln", "tooln", "datan", "coden", "protn"]


def aggregate_year(entities: list[str], year: str, data_map: dict) -> dict | None:
    """Paper-weighted aggregate for a list of entity keys in a given year."""
    w: dict[str, float] = {k: 0.0 for k in RATE_KEYS}
    d: dict[str, float] = {k: 0.0 for k in RATE_KEYS}
    counts: dict[str, int] = {k: 0 for k in COUNT_KEYS}
    total_n = 0
    entity_count = 0

    for key in entities:
        yd = data_map.get(key, {}).get("y", {}).get(year)
        if not yd or not yd.get("n"):
            continue
        entity_count += 1
        n = yd["n"]
        total_n += n
        for k in RATE_KEYS:
            if yd.get(k) is not None:
                w[k] += yd[k] * n
                d[k] += n
        for k in COUNT_KEYS:
            if yd.get(k) is not None:
                counts[k] += yd[k]

    if not total_n:
        return None

    out: dict = {"n": total_n, "entityCount": entity_count}
    for k in RATE_KEYS:
        out[k] = w[k] / d[k] if d[k] else None
    for k in COUNT_KEYS:
        out[k] = counts[k]
    return out


def build_by_year_benchmark(data_map: dict) -> dict:
    """Build year -> benchmark metrics from all entities in data_map."""
    years: set[str] = set()
    for entry in data_map.values():
        years.update(entry.get("y", {}).keys())

    all_keys = list(data_map.keys())
    benchmark: dict[str, dict] = {}
    for year in sorted(years, key=int):
        agg = aggregate_year(all_keys, year, data_map)
        if agg:
            benchmark[year] = agg
    return benchmark


def build_country_benchmark(data: dict) -> dict:
    return build_by_year_benchmark(data.get("c", {}))


def build_institution_benchmark(data: dict) -> dict:
    return build_by_year_benchmark(data.get("i", {}))

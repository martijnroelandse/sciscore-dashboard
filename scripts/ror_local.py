"""Local ROR registry index and matching (no API rate limits).

Downloads the Zenodo ROR data dump and matches institution names against
~129k organizations using exact + fuzzy name matching with country filtering.
"""
from __future__ import annotations

import json
import pickle
import re
import zipfile
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "ror_cache"
ZIP_PATH = CACHE_DIR / "ror-data.zip"
INDEX_PATH = CACHE_DIR / "ror_index.pkl"
META_PATH = CACHE_DIR / "ror_meta.json"

ZENODO_LATEST = (
    "https://zenodo.org/api/communities/ror-data/records?q=&sort=newest&size=1"
)

COUNTRY_ALIASES = {
    "united states": "united states",
    "usa": "united states",
    "us": "united states",
    "u s a": "united states",
    "united kingdom": "united kingdom",
    "uk": "united kingdom",
    "u k": "united kingdom",
    "south korea": "south korea",
    "korea": "south korea",
    "republic of korea": "south korea",
    "russia": "russia",
    "russian federation": "russia",
    "iran": "iran",
    "islamic republic of iran": "iran",
    "vietnam": "vietnam",
    "viet nam": "vietnam",
    "taiwan": "taiwan",
    "republic of china": "taiwan",
}

STOPWORDS = frozenset({
    "of", "the", "and", "for", "in", "at", "de", "la", "du", "des", "van", "der",
    "university", "college", "institut", "institute", "hospital", "center", "centre",
})


def significant_tokens(text: str) -> set[str]:
    return {t for t in normalize_text(text).split() if len(t) > 2 and t not in STOPWORDS}


def token_recall(query: str, candidate: str) -> float:
    q = significant_tokens(query)
    if not q:
        return 1.0
    c = set(normalize_text(candidate).split())
    return len(q & c) / len(q)


def combined_score(query: str, candidate: str) -> float:
    sim = similarity(query, candidate)
    recall = token_recall(query, candidate)
    if recall < 0.5:
        return sim * recall
    return sim * 0.55 + recall * 0.45


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_country(country: str) -> str:
    if not country:
        return ""
    norm = normalize_text(country)
    return COUNTRY_ALIASES.get(norm, norm)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def primary_country(org: dict) -> str:
    locs = org.get("locations") or []
    if not locs:
        return ""
    geo = locs[0].get("geonames_details") or {}
    return geo.get("country_name") or ""


def all_names(org: dict) -> list[str]:
    names: list[str] = []
    for item in org.get("names") or []:
        val = (item.get("value") or "").strip()
        if val:
            names.append(val)
    return names


def primary_name(org: dict) -> str:
    for item in org.get("names") or []:
        types = item.get("types") or []
        if "ror_display" in types:
            return item.get("value", "")
    names = org.get("names") or []
    return names[0].get("value", "") if names else ""


def extract_hierarchy(org: dict) -> dict:
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


def org_to_match(org: dict, method: str, score: float) -> dict:
    hierarchy = extract_hierarchy(org)
    return {
        "id": org.get("id", ""),
        "name": primary_name(org),
        "types": org.get("types") or [],
        "country": primary_country(org),
        "established": org.get("established"),
        "method": method,
        "score": round(score, 3),
        "chosen": method.startswith("local:exact"),
        "parents": hierarchy["parents"],
        "children": hierarchy["children"],
        "related": hierarchy["related"],
    }


def zenodo_download_url() -> tuple[str, str]:
    with urlopen(ZENODO_LATEST, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    hit = data["hits"]["hits"][0]
    version = hit["metadata"].get("version", "unknown")
    url = hit["files"][0]["links"]["self"]
    return version, url


def ensure_ror_dump(force: bool = False) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.is_file() and not force:
        return ZIP_PATH

    print("Fetching latest ROR data dump from Zenodo...")
    version, url = zenodo_download_url()
    print(f"  Version: {version}")
    print(f"  Downloading {url}")
    with urlopen(url, timeout=600) as resp:
        ZIP_PATH.write_bytes(resp.read())
    META_PATH.write_text(json.dumps({"version": version, "url": url}, indent=2), encoding="utf-8")
    print(f"  Saved {ZIP_PATH} ({ZIP_PATH.stat().st_size / 1e6:.1f} MB)")
    return ZIP_PATH


def load_ror_orgs(zip_path: Path | None = None) -> list[dict]:
    zip_path = zip_path or ensure_ror_dump()
    with zipfile.ZipFile(zip_path) as zf:
        json_name = next(n for n in zf.namelist() if n.endswith(".json"))
        with zf.open(json_name) as handle:
            orgs = json.load(handle)
    active = [o for o in orgs if (o.get("status") or "active") == "active"]
    print(f"Loaded {len(active):,} active ROR organizations")
    return active


class RorLocalIndex:
    """In-memory name index over the ROR registry."""

    def __init__(self, orgs: list[dict]):
        self.orgs = orgs
        self.by_name_country: dict[tuple[str, str], list[int]] = defaultdict(list)
        self.by_name: dict[str, list[int]] = defaultdict(list)
        self.by_country: dict[str, list[int]] = defaultdict(list)
        self._build()

    def _build(self) -> None:
        seen_country: dict[str, set[int]] = defaultdict(set)
        for idx, org in enumerate(self.orgs):
            country = normalize_country(primary_country(org))
            if country:
                seen_country[country].add(idx)
            for name in all_names(org):
                norm = normalize_text(name)
                if not norm:
                    continue
                self.by_name_country[(norm, country)].append(idx)
                self.by_name[norm].append(idx)
        self.by_country = {c: sorted(ids) for c, ids in seen_country.items()}

    @classmethod
    def load(cls, force_rebuild: bool = False) -> RorLocalIndex:
        zip_path = ensure_ror_dump()
        zip_mtime = zip_path.stat().st_mtime

        if INDEX_PATH.is_file() and not force_rebuild:
            with INDEX_PATH.open("rb") as handle:
                cached = pickle.load(handle)
            if cached.get("zip_mtime") == zip_mtime:
                print(f"Using cached index ({INDEX_PATH})")
                return cls(cached["orgs"])

        orgs = load_ror_orgs(zip_path)
        print("Building local name index...")
        index = cls(orgs)
        with INDEX_PATH.open("wb") as handle:
            pickle.dump({"zip_mtime": zip_mtime, "orgs": orgs}, handle, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"Cached index to {INDEX_PATH}")
        return index

    def match(self, name: str, country: str = "", state: str = "") -> dict | None:
        norm_name = normalize_text(name)
        norm_country = normalize_country(country)
        if not norm_name:
            return None

        # 1. Exact name + country
        if norm_country:
            hits = self.by_name_country.get((norm_name, norm_country), [])
            if len(hits) == 1:
                return org_to_match(self.orgs[hits[0]], "local:exact", 1.0)
            if len(hits) > 1:
                best = self._best_fuzzy(name, [self.orgs[i] for i in hits], country)
                if best:
                    return org_to_match(best[0], "local:exact_multi", best[1])

        # 2. Exact name, any country
        hits = self.by_name.get(norm_name, [])
        if hits:
            candidates = [self.orgs[i] for i in hits]
            if norm_country:
                in_country = [o for o in candidates if normalize_country(primary_country(o)) == norm_country]
                if len(in_country) == 1:
                    return org_to_match(in_country[0], "local:exact_name", 0.98)
                if in_country:
                    candidates = in_country
            if len(candidates) == 1:
                return org_to_match(candidates[0], "local:exact_name", 0.95)
            best = self._best_fuzzy(name, candidates, country)
            if best and best[1] >= 0.9:
                return org_to_match(best[0], "local:exact_name_multi", best[1])

        # 3. Fuzzy match within country
        if norm_country:
            result = self._fuzzy_country_search(norm_name, norm_country, name, country)
            if result:
                return result

        # 4. Global fuzzy (lower threshold, country penalty)
        return self._global_fuzzy(name, country)

    def _best_fuzzy(self, query: str, candidates: list[dict], country: str) -> tuple[dict, float] | None:
        best: dict | None = None
        best_score = 0.0
        norm_country = normalize_country(country)
        for org in candidates:
            for org_name in all_names(org):
                score = combined_score(query, org_name)
                if norm_country:
                    org_c = normalize_country(primary_country(org))
                    if org_c and org_c != norm_country:
                        score *= 0.6
                if score > best_score:
                    best_score = score
                    best = org
        if best and best_score >= 0.82:
            return best, best_score
        return None

    def _fuzzy_country_search(self, norm_name: str, norm_country: str, raw_name: str, country: str) -> dict | None:
        country_indices = self.by_country.get(norm_country, [])
        best: dict | None = None
        best_score = 0.0
        for idx in country_indices:
            org = self.orgs[idx]
            for org_name in all_names(org):
                score = combined_score(raw_name, org_name)
                if token_recall(raw_name, org_name) >= 0.85 and similarity(raw_name, org_name) >= 0.75:
                    score = max(score, 0.92)
                if score > best_score:
                    best_score = score
                    best = org

        if best and best_score >= 0.78:
            return org_to_match(best, f"local:fuzzy({best_score:.2f})", best_score)
        return None

    def _global_fuzzy(self, name: str, country: str) -> dict | None:
        norm_name = normalize_text(name)
        norm_country = normalize_country(country)
        best: dict | None = None
        best_score = 0.0

        # Token-prefix filter: first 4 chars of first significant word
        tokens = [t for t in norm_name.split() if len(t) > 2]
        if not tokens:
            return None
        prefix = tokens[0][:4]

        for (n, c), indices in self.by_name_country.items():
            if not n.startswith(prefix) and prefix not in n:
                continue
            for idx in indices:
                org = self.orgs[idx]
                for org_name in all_names(org):
                    score = combined_score(name, org_name)
                    if norm_country:
                        org_c = normalize_country(primary_country(org))
                        if org_c and org_c != norm_country:
                            score *= 0.45
                    if score > best_score:
                        best_score = score
                        best = org

        if best and best_score >= 0.9:
            return org_to_match(best, f"local:global({best_score:.2f})", best_score)
        return None

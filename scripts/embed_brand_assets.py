#!/usr/bin/env python3
"""Extract SciScore branding from design/ + template PPTX, embed into dashboard HTML."""
from __future__ import annotations

import base64
import json
import mimetypes
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"
DESIGN = ROOT / "design"
BRAND_JSON = ROOT / "scripts" / "brand_config.json"

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

DEFAULT_BRAND = {
    "colors": {
        "blue": "29ABE2",
        "navy": "0D1B3E",
        "white": "FFFFFF",
        "light": "F0F5F8",
        "muted": "7A9BBF",
        "text": "333333",
    },
    "fonts": {"face": "Segoe UI"},
    "images": {},
    "icons": {},
    "template": None,
}


def _hex6(value: str) -> str:
    value = value.strip().upper().lstrip("#")
    return value[:6] if len(value) >= 6 else value


def _read_theme_colors(pptx_path: Path) -> dict[str, str]:
    colors: dict[str, str] = {}
    try:
        with zipfile.ZipFile(pptx_path) as zf:
            theme_names = [n for n in zf.namelist() if n.startswith("ppt/theme/theme") and n.endswith(".xml")]
            if not theme_names:
                return colors
            root = ET.fromstring(zf.read(theme_names[0]))
            scheme = root.find(".//a:clrScheme", NS)
            if scheme is None:
                return colors
            for child in scheme:
                tag = child.tag.rsplit("}", 1)[-1]
                srgb = child.find(".//a:srgbClr", NS)
                if srgb is not None and "val" in srgb.attrib:
                    colors[tag] = _hex6(srgb.attrib["val"])
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        pass
    return colors


def _extract_template_media(pptx_path: Path, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    with zipfile.ZipFile(pptx_path) as zf:
        for name in zf.namelist():
            if not name.startswith("ppt/media/"):
                continue
            data = zf.read(name)
            dest = out_dir / Path(name).name
            dest.write_bytes(data)
            saved.append(str(dest.relative_to(ROOT)))
    return saved


def _data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _pick_logo(files: list[Path], prefer_white: bool) -> Path | None:
    if not files:
        return None
    ranked = sorted(files, key=lambda p: p.name.lower())
    if prefer_white:
        for p in ranked:
            n = p.name.lower()
            if any(k in n for k in ("white", "light", "reverse", "inv")):
                return p
    for p in ranked:
        n = p.name.lower()
        if "logo" in n and not any(k in n for k in ("white", "light", "reverse", "inv", "icon")):
            return p
    return ranked[0]


def _icon_key(name: str) -> str:
    n = name.lower()
    rules = [
        ("sex", ("sex", "gender")),
        ("power", ("power", "pwr")),
        ("random", ("random", "rand")),
        ("blind", ("blind",)),
        ("irb", ("irb", "ethic")),
        ("iacuc", ("iacuc", "animal")),
        ("antibody", ("antibod", "ab", "rrid")),
        ("organism", ("organism", "model")),
        ("cell", ("cell",)),
        ("tool", ("tool", "software")),
    ]
    for key, parts in rules:
        if any(p in n for p in parts):
            return key
    return Path(name).stem.lower()


def find_template() -> Path | None:
    candidates: list[Path] = []
    for pattern in ("*template*.pptx", "*Template*.pptx", "sciscore*.pptx", "SciScore*.pptx"):
        candidates.extend(DESIGN.glob(pattern))
        candidates.extend(DESIGN.glob(f"templates/{pattern}"))
    candidates = sorted({p.resolve() for p in candidates if p.is_file()})
    return candidates[0] if candidates else None


def collect_brand() -> dict:
    brand = json.loads(json.dumps(DEFAULT_BRAND))
    template = find_template()
    if template:
        brand["template"] = str(template.relative_to(ROOT))
        theme = _read_theme_colors(template)
        if theme.get("accent1"):
            brand["colors"]["blue"] = theme["accent1"]
        if theme.get("dk1"):
            brand["colors"]["navy"] = theme["dk1"]
        if theme.get("lt1"):
            brand["colors"]["white"] = theme["lt1"]
        extracted = _extract_template_media(template, DESIGN / "_from_template")
        for rel in extracted:
            name = Path(rel).name.lower()
            if "logo" in name:
                key = "logoWhite" if any(k in name for k in ("white", "light", "reverse")) else "logoColor"
                if key not in brand["images"]:
                    brand["images"][key] = {"path": rel}

    logo_dir = DESIGN / "logos"
    if logo_dir.is_dir():
        logos = [p for p in logo_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".webp"}]
        white = _pick_logo(logos, prefer_white=True)
        color = _pick_logo(logos, prefer_white=False)
        if white:
            brand["images"]["logoWhite"] = {"path": str(white.relative_to(ROOT))}
        if color and (not white or color != white):
            brand["images"]["logoColor"] = {"path": str(color.relative_to(ROOT))}

    icons_dir = DESIGN / "icons"
    if icons_dir.is_dir():
        for icon in icons_dir.iterdir():
            if icon.suffix.lower() not in {".png", ".jpg", ".jpeg", ".svg", ".webp"}:
                continue
            brand["icons"][_icon_key(icon.name)] = {"path": str(icon.relative_to(ROOT))}

    # Embed small raster assets for reliable browser export (skip large files).
    for bucket in ("images", "icons"):
        for key, spec in list(brand[bucket].items()):
            path = ROOT / spec["path"]
            if not path.is_file():
                continue
            if path.suffix.lower() == ".svg" or path.stat().st_size > 400_000:
                continue
            spec["data"] = _data_uri(path)

    return brand


def patch_html(brand: dict) -> None:
    content = HTML.read_text(encoding="utf-8")
    block = "const BRAND_CONFIG = " + json.dumps(brand, indent=2, ensure_ascii=False) + ";"
    pattern = r"/\* BRAND_CONFIG_START \*/[\s\S]*?/\* BRAND_CONFIG_END \*/"
    replacement = "/* BRAND_CONFIG_START */\n" + block + "\n/* BRAND_CONFIG_END */"
    if not re.search(pattern, content):
        raise ValueError("BRAND_CONFIG markers not found in HTML")
    HTML.write_text(re.sub(pattern, replacement, content, count=1), encoding="utf-8")


def main() -> None:
    brand = collect_brand()
    BRAND_JSON.write_text(json.dumps(brand, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    patch_html(brand)
    print(f"Brand config written to {BRAND_JSON}")
    print(f"Patched {HTML.name}")
    print("Template:", brand.get("template") or "(none — using defaults)")
    print("Images:", ", ".join(brand["images"]) or "(none)")
    print("Icons:", ", ".join(brand["icons"]) or "(none)")


if __name__ == "__main__":
    main()

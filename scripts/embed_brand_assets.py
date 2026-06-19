#!/usr/bin/env python3
"""Extract SciScore branding from design/ + template PPTX, embed into dashboard HTML."""
from __future__ import annotations

import base64
import json
import mimetypes
import re
import struct
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"
DESIGN_DIRS = [ROOT / "design", ROOT / "Design"]
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


def _image_dims(path: Path) -> tuple[int, int] | None:
    try:
        if path.suffix.lower() == ".png":
            with path.open("rb") as f:
                f.read(16)
                return struct.unpack(">II", f.read(8))
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            with path.open("rb") as f:
                f.read(2)
                while True:
                    marker, size = struct.unpack(">HH", f.read(4))
                    if marker == 0xFFC0:
                        f.read(1)
                        return struct.unpack(">HH", f.read(4))[1::-1]
                    f.read(size - 2)
    except (OSError, struct.error):
        pass
    return None


def _pick_logo(files: list[Path], prefer_white: bool) -> Path | None:
    if not files:
        return None
    sciscore = [p for p in files if "sciscore" in p.name.lower()]
    pool = sciscore or files
    ranked = sorted(pool, key=lambda p: p.name.lower())
    if prefer_white:
        for p in ranked:
            n = p.name.lower()
            if any(k in n for k in ("white", "light", "reverse", "inv")):
                return p
    else:
        for p in ranked:
            n = p.name.lower()
            if "black" in n:
                return p
        for p in ranked:
            if "white" not in p.name.lower():
                return p
    for p in ranked:
        n = p.name.lower()
        if any(k in n for k in ("white", "light", "reverse", "inv")):
            continue
        return p
    return ranked[0]


def _icon_key(name: str) -> str:
    n = name.lower()
    explicit = {
        "preclinicalresearch": "iacuc",
        "protocolidentifierssvg": "antibody",
        "replicate": "random",
        "codeinformation": "tool",
        "review": "blind",
        "report": "power",
        "journalarticles": "organism",
        "globe": "organism",
        "casestudy": "irb",
        "copy": "cell",
        "clock": "power",
        "corrections": "sex",
        "submit": "irb",
    }
    stem = Path(name).stem.lower()
    if stem in explicit:
        return explicit[stem]
    rules = [
        ("sex", ("sex", "gender")),
        ("power", ("power", "pwr")),
        ("random", ("random", "rand", "replicate")),
        ("blind", ("blind", "review")),
        ("irb", ("irb", "ethic", "casestudy", "submit")),
        ("iacuc", ("iacuc", "animal", "preclinical")),
        ("antibody", ("antibod", "rrid", "protocol")),
        ("organism", ("organism", "model", "globe", "journal")),
        ("cell", ("cell", "copy")),
        ("tool", ("tool", "software", "code")),
    ]
    for key, parts in rules:
        if any(p in n for p in parts):
            return key
    return stem


def _design_roots() -> list[Path]:
    return [d for d in DESIGN_DIRS if d.is_dir()]


def _glob_design(pattern: str) -> list[Path]:
    found: list[Path] = []
    for root in [ROOT, *_design_roots()]:
        found.extend(root.glob(pattern))
        for d in _design_roots():
            found.extend(d.glob(pattern))
            found.extend(d.glob(f"**/{pattern}"))
    return sorted({p.resolve() for p in found if p.is_file()})


def find_template() -> Path | None:
    candidates = _glob_design("*template*.pptx") + _glob_design("*Template*.pptx")
    candidates += _glob_design("sciscore*.pptx") + _glob_design("SciScore*.pptx")
    # Prefer explicit template filename
    for p in candidates:
        if "template" in p.name.lower():
            return p
    return candidates[0] if candidates else None


def _find_logos() -> tuple[Path | None, Path | None]:
    # Prefer the current hexagon SciScore mark used in client decks.
    for name in ("New SciScore.png",):
        hits = sorted({p.resolve() for p in _glob_design(name)})
        if hits:
            return hits[0], hits[0]

    image_ext = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
    logos: list[Path] = []
    for d in _design_roots():
        for sub in ("logos", "New deck icons", ""):
            base = d / sub if sub else d
            if not base.is_dir():
                continue
            logos.extend(p for p in base.rglob("*") if p.suffix.lower() in image_ext)
    # Legacy SciScore brand marks
    for name in (
        "SciScore 6 years - white.png",
        "SciScore 6 years - black.png",
    ):
        for p in _glob_design(name):
            logos.append(p)
    logos = sorted({p.resolve() for p in logos})
    white = _pick_logo(logos, prefer_white=True)
    color = _pick_logo(logos, prefer_white=False)
    if white and color == white:
        for p in logos:
            if p != white and "sciscore" in p.name.lower():
                color = p
                break
    return white, color


def _collect_icons(brand: dict) -> None:
    image_ext = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
    icon_dirs = []
    for d in _design_roots():
        icon_dirs.extend([d / "icons", d / "PNGs for slides"])
    for base in icon_dirs:
        if not base.is_dir():
            continue
        for icon in base.rglob("*"):
            if icon.suffix.lower() not in image_ext:
                continue
            key = _icon_key(icon.name)
            if key not in brand["icons"]:
                brand["icons"][key] = {"path": str(icon.relative_to(ROOT))}


def collect_brand() -> dict:
    brand = json.loads(json.dumps(DEFAULT_BRAND))
    template = find_template()
    if template:
        brand["template"] = str(template.relative_to(ROOT))
        theme = _read_theme_colors(template)
        if theme.get("accent1"):
            brand["colors"]["blue"] = theme["accent1"]
        navy = theme.get("dk1")
        if navy and navy not in ("000000", "FFFFFF"):
            brand["colors"]["navy"] = navy
        if theme.get("lt1"):
            brand["colors"]["white"] = theme["lt1"]
        extracted = _extract_template_media(template, ROOT / "design" / "_from_template")
        for rel in extracted:
            name = Path(rel).name.lower()
            if "logo" in name:
                key = "logoWhite" if any(k in name for k in ("white", "light", "reverse")) else "logoColor"
                if key not in brand["images"]:
                    brand["images"][key] = {"path": rel}

    white, color = _find_logos()
    if white:
        brand["images"]["logoWhite"] = {"path": str(white.relative_to(ROOT))}
    if color and (not white or color != white):
        brand["images"]["logoColor"] = {"path": str(color.relative_to(ROOT))}

    _collect_icons(brand)

    # Embed small raster assets for reliable browser export (skip large files).
    for bucket in ("images", "icons"):
        for key, spec in list(brand[bucket].items()):
            path = ROOT / spec["path"]
            if not path.is_file():
                continue
            if path.suffix.lower() == ".svg" or path.stat().st_size > 250_000:
                continue
            spec["data"] = _data_uri(path)
            dims = _image_dims(path)
            if dims:
                spec["width"], spec["height"] = dims

    return brand


def patch_html(brand: dict) -> None:
    content = HTML.read_text(encoding="utf-8")
    block = "const BRAND_CONFIG = " + json.dumps(brand, indent=2, ensure_ascii=False) + ";"
    pattern = r"/\* BRAND_CONFIG_START \*/[\s\S]*?/\* BRAND_CONFIG_END \*/"
    replacement = "/* BRAND_CONFIG_START */\n" + block + "\n/* BRAND_CONFIG_END */"
    if not re.search(pattern, content):
        raise ValueError("BRAND_CONFIG markers not found in HTML")
    content = re.sub(pattern, replacement, content, count=1)
    logo_data = (
        brand.get("images", {}).get("logoColor", {}).get("data")
        or brand.get("images", {}).get("logoWhite", {}).get("data")
    )
    if logo_data:
        content = re.sub(
            r'(<img class="logo-img" src=")[^"]+(")',
            rf"\1{logo_data}\2",
            content,
            count=1,
        )
    HTML.write_text(content, encoding="utf-8")


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

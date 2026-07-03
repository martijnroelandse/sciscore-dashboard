#!/usr/bin/env python3
"""Build OA-safe dashboard artifacts for the public GitHub Pages repo.

Runs the embed pipeline (when source data is present), applies the OA disclaimer
patch, and copies only publishable files to dist/oa-public/.

Usage:
    python3 scripts/publish_oa_artifact.py
    python3 scripts/publish_oa_artifact.py --copy-only
    python3 scripts/publish_oa_artifact.py --include-jmir
    python3 scripts/publish_oa_artifact.py --skip-build
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "oa-public"
TEMPLATES = ROOT / "templates"

JOURNAL_HTML = ROOT / "SciScore_journal_dashboard.html"
COUNTRY_HTML = ROOT / "SciScore_country_dashboard.html"
INSTITUTION_HTML = ROOT / "SciScore_institution_dashboard.html"
ADDENDUM = ROOT / "addendum.html"

DESIGN_DIRS = [ROOT / "design", ROOT / "Design"]


def run(cmd: list[str], label: str) -> None:
    print(f"→ {label}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"{label} failed (exit {result.returncode})")


def build_dashboard(skip_build: bool) -> None:
    if skip_build:
        print("Skipping build pipeline (--skip-build)")
        return
    if not JOURNAL_HTML.is_file():
        raise SystemExit(f"Missing {JOURNAL_HTML}")

    data_csv = ROOT / "data" / "2026_sciscore_v3.csv"
    if data_csv.is_file():
        run([sys.executable, str(SCRIPTS / "embed_journal_data.py")], "embed_journal_data.py")
    else:
        print("No data/2026_sciscore_v3.csv — skipping embed (using existing HTML)")

    xlsx = ROOT / "data" / "2026_sciscore_v3.xlsx"
    if xlsx.is_file() or data_csv.is_file():
        run([sys.executable, str(SCRIPTS / "embed_benchmarks.py")], "embed_benchmarks.py")
    else:
        print("No benchmark source — skipping embed_benchmarks.py")

    brand_script = SCRIPTS / "embed_brand_assets.py"
    if brand_script.is_file():
        run([sys.executable, str(brand_script)], "embed_brand_assets.py")

    run([sys.executable, str(SCRIPTS / "patch_oa_disclaimer.py")], "patch_oa_disclaimer.py")


def resolve_design_dir() -> Path | None:
    for path in DESIGN_DIRS:
        if path.is_dir() and any(path.iterdir()):
            return path
    return None


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def write_readme(dest: Path) -> None:
    template = TEMPLATES / "public-artifact-README.md"
    if template.is_file():
        shutil.copy2(template, dest / "README.md")
    else:
        dest.joinpath("README.md").write_text(
            "# SciScore Journal Intelligence (public OA demo)\n\n"
            "Open-access metrics only. See addendum.html for methodology.\n",
            encoding="utf-8",
        )


def publish(include_jmir: bool, copy_only: bool, skip_build: bool) -> None:
    if not copy_only:
        build_dashboard(skip_build=skip_build)
    else:
        run([sys.executable, str(SCRIPTS / "patch_oa_disclaimer.py")], "patch_oa_disclaimer.py")

    if not JOURNAL_HTML.is_file():
        raise SystemExit(f"Missing built dashboard: {JOURNAL_HTML}")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    shutil.copy2(JOURNAL_HTML, DIST / JOURNAL_HTML.name)
    if ADDENDUM.is_file():
        shutil.copy2(ADDENDUM, DIST / ADDENDUM.name)

    design = resolve_design_dir()
    if design:
        copy_tree(design, DIST / "design")
        print(f"Copied {design.name}/ → dist/oa-public/design/")
    else:
        print("Warning: no design/ directory found — PPTX export may lack icons on Pages")

    if include_jmir:
        for path in (COUNTRY_HTML, INSTITUTION_HTML):
            if path.is_file():
                shutil.copy2(path, DIST / path.name)
                print(f"Included {path.name}")
            else:
                print(f"Warning: {path.name} not found — skipped")

    write_readme(DIST)

    print()
    print(f"OA artifact ready: {DIST}")
    print("Contents:")
    for p in sorted(DIST.rglob("*")):
        if p.is_file():
            rel = p.relative_to(DIST)
            size_kb = p.stat().st_size / 1024
            print(f"  {rel} ({size_kb:.0f} KB)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build public OA artifact for GitHub Pages")
    parser.add_argument(
        "--copy-only",
        action="store_true",
        help="Skip embed pipeline; patch disclaimer and copy existing HTML",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip embed/benchmark scripts; still runs disclaimer patch",
    )
    parser.add_argument(
        "--include-jmir",
        action="store_true",
        help="Also copy JMIR country/institution dashboards",
    )
    args = parser.parse_args()
    publish(
        include_jmir=args.include_jmir,
        copy_only=args.copy_only,
        skip_build=args.skip_build,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

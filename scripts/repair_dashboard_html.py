#!/usr/bin/env python3
"""Repair corrupted ``const DATA`` block and ensure dashboard init hooks."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from html_json import (
    _const_line_span,
    _data_blob,
    extract_json_block,
    has_merge_conflicts,
    recover_data_json,
    replace_const_block,
)

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"


def data_block_is_corrupt(content: str) -> bool:
    if has_merge_conflicts(content):
        return True
    _, line_end = _const_line_span(content, "DATA")
    line = content[content.index("const DATA = ") : line_end]
    if "\nconst GROUP_MAP" in line:
        return True
    try:
        recover_data_json(_data_blob(content))
        return False
    except (json.JSONDecodeError, ValueError):
        return True


def repair_data_block(content: str) -> str:
    data = extract_json_block(content, "DATA")
    return replace_const_block(content, "DATA", data)


def patch_init_hooks(content: str) -> str:
    if "populateCompareSelect();" not in content:
        content = content.replace(
            "populateGroups();\npopulatePublishers();\nrenderJournalList();\nrenderMain();",
            "populateGroups();\npopulatePublishers();\npopulateCompareSelect();\nshowExportBtn();\nrenderJournalList();\nrenderMain();",
        )

    if "compareTouched = false;" not in content.split("function selectJournal")[1][:200]:
        content = content.replace(
            "function selectJournal(name) {\n  selectedJournal = name;",
            "function selectJournal(name) {\n  selectedJournal = name;\n  compareTouched = false;",
        )
        content = content.replace(
            "function backToPublisher() {\n  selectedJournal = null;",
            "function backToPublisher() {\n  selectedJournal = null;\n  compareTouched = false;",
        )
        for old in (
            "groupSelect.addEventListener('change', () => {\n  selectedJournal = null;",
            "pubSelect.addEventListener('change', () => {\n  selectedJournal = null;",
        ):
            if "compareTouched = false;" not in content[content.index(old) : content.index(old) + 120]:
                content = content.replace(old, old + "\n  compareTouched = false;", 1)

    return content


def main() -> None:
    content = HTML.read_text(encoding="utf-8")
    if has_merge_conflicts(content):
        from html_json import _merge_conflict_help

        raise SystemExit(_merge_conflict_help())
    if data_block_is_corrupt(content):
        print("Repairing corrupted const DATA block…")
        content = repair_data_block(content)
    else:
        print("const DATA block looks healthy.")

    content = patch_init_hooks(content)
    HTML.write_text(content, encoding="utf-8")
    print(f"Updated {HTML.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

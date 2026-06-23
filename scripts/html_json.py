"""Robust extract/replace for large ``const NAME = {...};`` blocks in dashboard HTML."""
from __future__ import annotations

import json
import re


def _const_prefix(marker: str) -> str:
    return f"const {marker} = "


def _const_line_span(content: str, marker: str) -> tuple[int, int]:
    """Return ``(start, end)`` of the ``const MARKER = ...;`` line (end = before ``\\n``)."""
    prefix = _const_prefix(marker)
    pos = content.index(prefix)
    line_end = content.find("\n", pos)
    if line_end == -1:
        line_end = len(content)
    return pos, line_end


def _line_json_payload(content: str, marker: str) -> str:
    pos, line_end = _const_line_span(content, marker)
    blob = content[pos + len(_const_prefix(marker)) : line_end].strip()
    if blob.endswith(";"):
        blob = blob[:-1]
    return blob


def _data_blob(content: str) -> str:
    """Payload of ``const DATA = ...`` up to (but not including) ``const GROUP_MAP``."""
    prefix = _const_prefix("DATA")
    pos = content.index(prefix) + len(prefix)
    anchor = content.find("\nconst GROUP_MAP", pos)
    if anchor == -1:
        blob = content[pos : _const_line_span(content, "DATA")[1]]
    else:
        blob = content[pos:anchor]
    blob = blob.strip()
    if blob.endswith(";"):
        blob = blob[:-1]
    return blob


def _merge_conflict_help() -> str:
    return (
        "SciScore_journal_dashboard.html contains git merge conflict markers.\n"
        "Finish the merge by keeping the fix-branch version of the HTML, then re-run repair:\n\n"
        "  git checkout --theirs SciScore_journal_dashboard.html\n"
        "  git add SciScore_journal_dashboard.html\n"
        "  git commit -m \"Resolve merge: take fixed dashboard HTML\"\n"
        "  python3 scripts/repair_dashboard_html.py\n"
        "  python3 scripts/embed_benchmarks.py\n\n"
        "Or abort the merge and hard-reset to the fix branch:\n\n"
        "  git merge --abort\n"
        "  git fetch origin cursor/fix-dashboard-menus-5bad\n"
        "  git reset --hard origin/cursor/fix-dashboard-menus-5bad\n"
    )


def has_merge_conflicts(content: str) -> bool:
    return any(
        marker in content
        for marker in ("<<<<<<<", "=======", ">>>>>>>")
    )


def recover_data_json(blob: str) -> dict:
    """Parse DATA JSON, including recovery from regex-embed corruption."""
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        pass

    try:
        obj, rel = json.JSONDecoder().raw_decode(blob, 0)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse embedded DATA JSON ({exc}). "
            "The HTML file may be truncated or still contain merge conflicts."
        ) from exc

    trailing = blob[rel:].lstrip()
    if not trailing:
        return obj
    if trailing.startswith(";"):
        return obj
    # Leftover junk after a complete object (classic ``}};`` regex false match).
    if trailing.startswith("}};") or trailing.startswith("The Korean Society"):
        return obj
    if "The Korean Society for Neuro-Oncology" in trailing[:120]:
        return obj

    raise ValueError(
        "Embedded DATA JSON has unexpected trailing content after the parsed object. "
        f"First trailing chars: {trailing[:80]!r}"
    )


def extract_json_block(content: str, marker: str):
    if marker == "DATA":
        if has_merge_conflicts(content):
            raise SystemExit(_merge_conflict_help())
        return recover_data_json(_data_blob(content))
    return json.loads(_line_json_payload(content, marker))


def replace_const_block(content: str, marker: str, data) -> str:
    prefix = _const_prefix(marker)
    pos = content.index(prefix)
    serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    if marker == "DATA":
        anchor = content.find("\nconst GROUP_MAP", pos)
        end = anchor if anchor != -1 else _const_line_span(content, marker)[1]
    else:
        _, end = _const_line_span(content, marker)
    return content[:pos] + f"const {marker} = {serialized};" + content[end:]


def insert_or_replace_const_block(content: str, marker: str, data, after_marker: str) -> str:
    prefix = _const_prefix(marker)
    if prefix in content:
        return replace_const_block(content, marker, data)
    serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    replacement = f"const {marker} = {serialized};\n"
    after_pos, after_end = _const_line_span(content, after_marker)
    return content[:after_end] + "\n" + replacement + content[after_end:]

"""Robust extract/replace for large ``const NAME = {...};`` blocks in dashboard HTML."""
from __future__ import annotations

import json
import re


def _const_prefix(marker: str) -> str:
    return f"const {marker} = "


def _json_start(content: str, marker: str) -> int:
    return content.index(_const_prefix(marker)) + len(_const_prefix(marker))


def _data_line_span(content: str) -> tuple[int, int]:
    """Return ``(start, end)`` of the ``const DATA = ...;`` line only."""
    prefix = _const_prefix("DATA")
    pos = content.index(prefix)
    line_end = content.find("\n", pos)
    if line_end == -1:
        line_end = len(content)
    return pos, line_end


def _data_blob(content: str) -> str:
    """Payload of ``const DATA = ...`` up to (but not including) ``const GROUP_MAP``."""
    prefix = _const_prefix("DATA")
    pos = content.index(prefix) + len(prefix)
    anchor = content.find("\nconst GROUP_MAP", pos)
    if anchor == -1:
        _, line_end = _data_line_span(content)
        blob = content[pos:line_end]
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


def _span_after_json(content: str, json_end: int, marker: str) -> int:
    """End of the full const assignment, including corrupt trailing junk before the next const."""
    if marker == "DATA":
        next_const = content.find("\nconst GROUP_MAP", json_end)
        if next_const != -1:
            return next_const
    end = json_end
    while end < len(content) and content[end] in " \t\r\n":
        end += 1
    if end < len(content) and content[end] == ";":
        end += 1
    next_const = content.find("\nconst ", end)
    if next_const == -1:
        raise ValueError(f"Could not find next const declaration after {json_end}")
    return next_const


def extract_json_block(content: str, marker: str):
    if marker == "DATA":
        if has_merge_conflicts(content):
            raise SystemExit(_merge_conflict_help())
        return recover_data_json(_data_blob(content))
    start = _json_start(content, marker)
    obj, _rel = json.JSONDecoder().raw_decode(content, start)
    return obj


def replace_const_block(content: str, marker: str, data) -> str:
    prefix = _const_prefix(marker)
    pos = content.index(prefix)
    if marker == "DATA":
        anchor = content.find("\nconst GROUP_MAP", pos)
        end = anchor if anchor != -1 else _data_line_span(content)[1]
        serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return content[:pos] + f"const {marker} = {serialized};" + content[end:]
    json_start = pos + len(prefix)
    _, rel = json.JSONDecoder().raw_decode(content, json_start)
    end = _span_after_json(content, json_start + rel, marker)
    serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return content[:pos] + f"const {marker} = {serialized};" + content[end:]


def insert_or_replace_const_block(content: str, marker: str, data, after_marker: str) -> str:
    prefix = _const_prefix(marker)
    if prefix in content:
        return replace_const_block(content, marker, data)
    serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    replacement = f"const {marker} = {serialized};\n"
    anchor = rf"(const {after_marker} = .*?;\n)"
    match = re.search(anchor, content, flags=re.DOTALL)
    if not match:
        # Fall back to brace-safe anchor search.
        after_prefix = _const_prefix(after_marker)
        after_pos = content.index(after_prefix)
        after_start = after_pos + len(after_prefix)
        _, rel = json.JSONDecoder().raw_decode(content, after_start)
        anchor_end = _span_after_json(content, after_start + rel, after_marker)
        return content[:anchor_end] + replacement + content[anchor_end:]
    return content[: match.end()] + replacement + content[match.end() :]

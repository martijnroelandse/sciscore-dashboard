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
        pos, line_end = _data_line_span(content)
        line = content[pos:line_end]
        payload = line[len(_const_prefix(marker)) :]
        if payload.endswith(";"):
            payload = payload[:-1]
        return json.loads(payload)
    start = _json_start(content, marker)
    obj, _rel = json.JSONDecoder().raw_decode(content, start)
    return obj


def replace_const_block(content: str, marker: str, data) -> str:
    prefix = _const_prefix(marker)
    pos = content.index(prefix)
    if marker == "DATA":
        _, line_end = _data_line_span(content)
        serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return content[:pos] + f"const {marker} = {serialized};" + content[line_end:]
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

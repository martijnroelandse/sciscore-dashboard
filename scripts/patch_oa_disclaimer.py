#!/usr/bin/env python3
"""Patch journal dashboard: OA corpus disclaimer + client-only export notice."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"

CSS_MARKER = "  .export-btn:disabled { opacity: 0.5; cursor: default; }"
CSS_ADDITION = """
  .sidebar-footer {
    padding: 12px 16px 14px;
    border-top: 1px solid var(--blue-border);
    flex-shrink: 0;
    background: rgba(0,0,0,0.12);
  }
  .corpus-notice {
    margin: 0 0 10px;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid rgba(41,171,226,0.22);
    background: rgba(41,171,226,0.08);
    font-size: 0.72rem;
    line-height: 1.45;
    color: var(--muted);
  }
  .corpus-notice strong { color: var(--blue-light); font-weight: 600; }
  .corpus-notice a { color: var(--blue-light); }
  .export-btn.client-only {
    display: block;
    width: 100%;
    opacity: 1;
    background: rgba(41,171,226,0.22);
    border: 1px solid rgba(41,171,226,0.35);
    cursor: pointer;
  }
  .export-btn.client-only:hover { opacity: 0.9; background: rgba(41,171,226,0.32); }
  #compareSelect { min-height: 2rem; }"""

CORPUS_HTML = """      <div class="corpus-notice" id="corpusNotice">
        <strong>Open-access corpus.</strong>
        Metrics use the PubMed Central open-access subset only.
        <a href="addendum.html#limitations">Limitations</a>
        · Full-corpus metrics and CSV export:
        <a href="https://sciscore.com" target="_blank" rel="noopener">SciScore clients</a>
        (sign-in required).
      </div>
      <button class="export-btn client-only visible" id="exportBtn" type="button" onclick="clientExportNotice()" title="Client export requires sign-in">&#9654; Export (clients only)</button>"""

SIDEBAR_FOOTER = f"""
    <div class="sidebar-footer">
{CORPUS_HTML}
    </div>"""

CLIENT_EXPORT_NOTICE_JS = """function clientExportNotice() {
  alert(
    'Export (CSV and PowerPoint) is available to SciScore client organizations after sign-in.\\n\\n' +
    'Contact SciScore at sciscore.com to request access. AACR full-corpus metrics coming soon.'
  );
}

function showExportBtn() {
  const btn = document.getElementById('exportBtn');
  if (!btn) return;
  btn.classList.add('visible', 'client-only');
}"""

EARLY_BOOT = """
(function earlySidebarBoot() {
  const countEl = document.getElementById('journalCountLabel');
  if (countEl && typeof JOURNAL_COUNT_LABEL !== 'undefined') {
    countEl.textContent = `${JOURNAL_COUNT_LABEL} journals`;
  }
  const compare = document.getElementById('compareSelect');
  if (compare && !compare.options.length) {
    compare.innerHTML = '<option value="all">All journals</option>';
  }
})();
"""

MIDDLE_EXPORT_RE = re.compile(
    r'\s*<div class="sidebar-section">\s*'
    r'<div class="corpus-notice"[^>]*>.*?</div>\s*'
    r'<button class="export-btn[^"]*" id="exportBtn"[^>]*>.*?</button>\s*'
    r'</div>\s*'
    r'(<div class="sidebar-section">\s*'
    r'<div class="sidebar-label">Search journal</div>)',
    re.DOTALL,
)


def main() -> int:
    if not HTML.is_file():
        print(f"Missing {HTML}", file=sys.stderr)
        return 1

    content = HTML.read_text(encoding="utf-8")
    changed = False

    if ".sidebar-footer" not in content:
        if ".corpus-notice" in content and CSS_MARKER in content:
            content = content.replace(
                CSS_MARKER,
                CSS_MARKER + CSS_ADDITION,
                1,
            )
        elif CSS_MARKER in content:
            content = content.replace(CSS_MARKER, CSS_MARKER + CSS_ADDITION, 1)
        changed = True

    if MIDDLE_EXPORT_RE.search(content):
        content = MIDDLE_EXPORT_RE.sub(r"\n\1", content, count=1)
        changed = True

    if 'class="sidebar-footer"' not in content:
        content = content.replace(
            '    <div class="journal-list" id="journalList"></div>\n  </div>',
            '    <div class="journal-list" id="journalList"></div>' + SIDEBAR_FOOTER + "\n  </div>",
            1,
        )
        changed = True

    if 'id="compareSelect" onchange="onCompareChange()"></select>' in content:
        content = content.replace(
            'id="compareSelect" onchange="onCompareChange()"></select>',
            'id="compareSelect" onchange="onCompareChange()">'
            '<option value="all">All journals</option></select>',
            1,
        )
        changed = True

    if "function clientExportNotice()" not in content:
        content = re.sub(
            r"function showExportBtn\(\) \{.*?\n\}",
            CLIENT_EXPORT_NOTICE_JS,
            content,
            count=1,
            flags=re.DOTALL,
        )
        changed = True

    if "function earlySidebarBoot()" not in content and "const JOURNAL_COUNT_LABEL" in content:
        content = content.replace(
            "const JOURNAL_COUNT_LABEL = Object.keys(DATA.j).length.toLocaleString();",
            "const JOURNAL_COUNT_LABEL = Object.keys(DATA.j).length.toLocaleString();"
            + EARLY_BOOT,
            1,
        )
        changed = True

    if changed:
        HTML.write_text(content, encoding="utf-8")
        print("Patched sidebar layout, OA disclaimer footer, and early boot")
    else:
        print("Sidebar OA patch already applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

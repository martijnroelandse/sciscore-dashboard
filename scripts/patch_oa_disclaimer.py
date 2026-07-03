#!/usr/bin/env python3
"""Patch journal dashboard: OA corpus disclaimer + client-only export notice."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"

CORPUS_NOTICE_CSS = """
  .corpus-notice {
    margin: 0 16px 12px;
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
    opacity: 0.55;
    cursor: not-allowed;
  }
"""

CORPUS_NOTICE_HTML = """    <div class="corpus-notice" id="corpusNotice">
      <strong>Open-access corpus.</strong>
      Metrics are from the PubMed Central open-access subset only.
      Journals with paywalled content may be underrepresented.
      <a href="addendum.html#limitations">Limitations</a>
      · Full-corpus metrics and CSV export are available to
      <a href="https://sciscore.com" target="_blank" rel="noopener">SciScore clients</a>
      (sign-in required).
    </div>
      <button class="export-btn client-only" id="exportBtn" type="button" onclick="clientExportNotice()" title="Client export requires sign-in">&#9654; Export (clients only)</button>"""

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

OLD_EXPORT_BLOCK_RE = re.compile(
    r'<div class="sidebar-section">\s*'
    r'(?:<div class="corpus-notice"[^>]*>.*?</div>\s*)?'
    r'<button class="export-btn[^"]*" id="exportBtn"[^>]*>.*?</button>\s*'
    r'(?:&#9654; Export Report</button>\s*)?'
    r'</div>',
    re.DOTALL,
)

NEW_EXPORT_BLOCK = (
    '<div class="sidebar-section">\n'
    + CORPUS_NOTICE_HTML
    + "\n    </div>"
)


def main() -> int:
    if not HTML.is_file():
        print(f"Missing {HTML}", file=sys.stderr)
        return 1

    content = HTML.read_text(encoding="utf-8")
    changed = False

    if ".corpus-notice" not in content:
        content = content.replace(
            "  .export-btn:disabled { opacity: 0.5; cursor: default; }",
            "  .export-btn:disabled { opacity: 0.5; cursor: default; }"
            + CORPUS_NOTICE_CSS,
            1,
        )
        changed = True

    if 'id="corpusNotice"' not in content or "Export Report</button>" in content:
        if OLD_EXPORT_BLOCK_RE.search(content):
            content = OLD_EXPORT_BLOCK_RE.sub(NEW_EXPORT_BLOCK, content, count=1)
            changed = True
        elif 'onclick="generatePPTX()"' in content:
            content = content.replace(
                '    <div class="sidebar-section">\n'
                '      <button class="export-btn" id="exportBtn" onclick="generatePPTX()">'
                '&#9654; Export Report</button>\n'
                "    </div>",
                NEW_EXPORT_BLOCK,
                1,
            )
            changed = True

    if "function clientExportNotice()" not in content:
        if "function showExportBtn()" in content:
            content = re.sub(
                r"function showExportBtn\(\) \{.*?\n\}",
                CLIENT_EXPORT_NOTICE_JS,
                content,
                count=1,
                flags=re.DOTALL,
            )
            changed = True

    if changed:
        HTML.write_text(content, encoding="utf-8")
        print("Patched OA corpus disclaimer and client-only export notice")
    else:
        print("OA disclaimer patch already applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

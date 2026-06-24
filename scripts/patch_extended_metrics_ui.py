#!/usr/bin/env python3
"""Patch dashboard UI for dynamic year range and open-science metrics."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"


def patch_once(content: str, old: str, new: str, label: str) -> str:
    if new in content:
        return content
    if old not in content:
        raise SystemExit(f"patch_extended_metrics_ui: pattern not found for {label}")
    return content.replace(old, new, 1)


def main() -> int:
    content = HTML.read_text(encoding="utf-8")

    content = patch_once(
        content,
        '<div class="header-badge">2015 – 2025</div>',
        '<div class="header-badge" id="headerYearBadge"></div>',
        "header badge",
    )
    content = patch_once(
        content,
        '<div class="empty-sub">Filter by publisher or search above · 4,939 journals · 2015–2025</div>',
        '<div class="empty-sub" id="emptySubLabel"></div>',
        "empty sub (sidebar)",
    )

    content = patch_once(
        content,
        "const YEARS = ['2015','2016','2017','2018','2019','2020','2021','2022','2023','2024','2025'];",
        """const YEARS = (() => {
  const years = new Set();
  for (const entry of Object.values(DATA.j)) {
    for (const y of Object.keys(entry.y || {})) years.add(y);
  }
  return [...years].sort((a, b) => Number(a) - Number(b));
})();
const DATA_YEAR_LABEL = YEARS.length
  ? (YEARS[0] === YEARS[YEARS.length - 1] ? YEARS[0] : `${YEARS[0]} – ${YEARS[YEARS.length - 1]}`)
  : '';
const JOURNAL_COUNT_LABEL = Object.keys(DATA.j).length.toLocaleString();""",
        "YEARS",
    )

    content = patch_once(
        content,
        "const RATE_KEYS = ['r','sex','pwr','rand','blind','irb','iacuc','ab','org','cl','tool'];",
        "const RATE_KEYS = ['r','sex','pwr','rand','blind','irb','iacuc','ab','org','cl','tool','data','code','prot','data_id','code_id'];",
        "RATE_KEYS",
    )
    content = patch_once(
        content,
        "const COUNT_KEYS = ['abn','orgn','cln','tooln'];",
        "const COUNT_KEYS = ['abn','orgn','cln','tooln','datan','coden','protn'];",
        "COUNT_KEYS",
    )

    content = patch_once(
        content,
        """  { key: 'tool', label: 'Software tools' },
];""",
        """  { key: 'tool', label: 'Software tools' },
  { section: 'Open science & identifiers' },
  { key: 'data', label: 'Data availability' },
  { key: 'code', label: 'Code availability' },
  { key: 'prot', label: 'Protocol identifiers' },
  { key: 'data_id', label: 'Data identifiers' },
  { key: 'code_id', label: 'Code identifiers' },
];""",
        "BENCHMARK_TABLE_ROWS",
    )

    content = patch_once(
        content,
        """  { key: 'tool', label: 'Software tools', countKey: 'tooln' },
];""",
        """  { key: 'tool', label: 'Software tools', countKey: 'tooln' },
  { key: 'data', label: 'Data availability', countKey: 'datan' },
  { key: 'code', label: 'Code availability', countKey: 'coden' },
  { key: 'prot', label: 'Protocol identifiers', countKey: 'protn' },
];""",
        "METRIC_CARDS",
    )

    open_science_block = """
const OPEN_SCIENCE_ROWS = [
  { name: 'Data availability', key: 'data', countKey: 'datan' },
  { name: 'Code availability', key: 'code', countKey: 'coden' },
  { name: 'Protocol identifiers', key: 'prot', countKey: 'protn' },
  { name: 'Data identifiers', key: 'data_id' },
  { name: 'Code identifiers', key: 'code_id' },
];

function renderMetricBarGrid(rows, yd, year) {
  const bench = compareBenchmark(year);
  const benchLabel = compareLabel();
  return rows.map(r => {
    const val = yd[r.key];
    const p = val != null ? Math.round(val * 100) : null;
    const detected = r.countKey && yd[r.countKey] != null
      ? `<span class="res-detected">(${yd[r.countKey].toLocaleString()} detected)</span>`
      : '';
    const benchLine = bench?.[r.key] != null
      ? `<div class="res-bench">${benchLabel} ${pct(bench[r.key])}${val != null ? ' ' + deltaBadgePp(val, bench[r.key], benchLabel) : ''}</div>`
      : '';
    return `<div class="resource-item">
      <div class="resource-row">
        <div class="res-name">${r.name}${detected}</div>
        <div class="bar-bg"><div class="bar-fill${p != null && p >= 60 ? ' strong' : ''}" style="width:${p ?? 0}%"></div></div>
        <div class="res-pct">${p != null ? p + '%' : '—'}</div>
      </div>${benchLine}
    </div>`;
  }).join('');
}
"""

    if "const OPEN_SCIENCE_ROWS" not in content:
        content = patch_once(
            content,
            "function renderResourceGrid(yd, year) {\n  const bench = compareBenchmark(year);\n  const benchLabel = compareLabel();\n  return RESOURCE_ROWS.map(r => {",
            "function renderOpenScienceGrid(yd, year) {\n  return renderMetricBarGrid(OPEN_SCIENCE_ROWS, yd, year);\n}\n\nfunction renderResourceGrid(yd, year) {\n  return renderMetricBarGrid(RESOURCE_ROWS, yd, year);\n}\n\nfunction _renderResourceGridLegacy(yd, year) {\n  const bench = compareBenchmark(year);\n  const benchLabel = compareLabel();\n  return RESOURCE_ROWS.map(r => {",
            "renderResourceGrid refactor",
        )
        # Remove legacy function body - replace until closing of renderResourceGrid
        content = re.sub(
            r"function _renderResourceGridLegacy\(yd, year\) \{.*?\n\}\n\nfunction radarDatasets",
            open_science_block + "\nfunction radarDatasets",
            content,
            count=1,
            flags=re.DOTALL,
        )

    panel_html = """
    <div class="detail-panel" id="panelOpenScience">
      <button type="button" class="panel-toggle" onclick="togglePanel('panelOpenScience')">
        <span class="panel-toggle-title">Open Science & Identifiers · <span id="openScienceYear"></span></span>
        <span class="panel-chevron">▼</span>
      </button>
      <div class="panel-body">
        <div class="resource-grid" id="openScienceGrid"></div>
      </div>
    </div>
"""

    if 'id="panelOpenScience"' not in content:
        content = content.replace(
            """    <div class="detail-panel" id="panelJournals">""",
            panel_html + "\n    <div class=\"detail-panel\" id=\"panelJournals\">",
            1,
        )
        content = content.replace(
            """    <div class="detail-panel" id="panelRrid">""",
            panel_html + "\n    <div class=\"detail-panel\" id=\"panelRrid\">",
            1,
        )

    for old, new in (
        (
            "  document.getElementById('resYear').textContent = selectedYear;\n  document.getElementById('tableYear').textContent = selectedYear;",
            "  document.getElementById('resYear').textContent = selectedYear;\n  document.getElementById('openScienceYear').textContent = selectedYear;\n  document.getElementById('tableYear').textContent = selectedYear;",
        ),
        (
            "  document.getElementById('resourceGrid').innerHTML = renderResourceGrid(yd, selectedYear);\n  updateBenchmarkPanel(yd, selectedYear, scope.label);",
            "  document.getElementById('resourceGrid').innerHTML = renderResourceGrid(yd, selectedYear);\n  document.getElementById('openScienceGrid').innerHTML = renderOpenScienceGrid(yd, selectedYear);\n  updateBenchmarkPanel(yd, selectedYear, scope.label);",
        ),
        (
            "  document.getElementById('resYear').textContent = selectedYear;\n  const rridYearEl",
            "  document.getElementById('resYear').textContent = selectedYear;\n  document.getElementById('openScienceYear').textContent = selectedYear;\n  const rridYearEl",
        ),
        (
            "  document.getElementById('resourceGrid').innerHTML = renderResourceGrid(yd, selectedYear);\n  updateBenchmarkPanel(yd, selectedYear, selectedJournal);",
            "  document.getElementById('resourceGrid').innerHTML = renderResourceGrid(yd, selectedYear);\n  document.getElementById('openScienceGrid').innerHTML = renderOpenScienceGrid(yd, selectedYear);\n  updateBenchmarkPanel(yd, selectedYear, selectedJournal);",
        ),
    ):
        if new not in content:
            content = patch_once(content, old, new, "panel wiring")

    content = patch_once(
        content,
        """      <div class="empty-sub">Or pick a journal from the list · 4,939 journals · 2015–2025</div>""",
        """      <div class="empty-sub">Or pick a journal from the list · ${JOURNAL_COUNT_LABEL} journals · ${DATA_YEAR_LABEL}</div>""",
        "renderEmpty",
    )

    content = patch_once(
        content,
        """function pptxResourceRows(yd) {
  return [
    { label:'Antibody RRIDs', val:yd.ab, n:yd.abn, iconKey:'antibody' },
    { label:'Organism RRIDs', val:yd.org, n:yd.orgn, iconKey:'organism' },
    { label:'Cell Line RRIDs', val:yd.cl, n:yd.cln, iconKey:'cell' },
    { label:'Software Tools', val:yd.tool, n:yd.tooln, iconKey:'tool' },
  ];
}""",
        """function pptxResourceRows(yd) {
  return [
    { label:'Antibody RRIDs', val:yd.ab, n:yd.abn, iconKey:'antibody' },
    { label:'Organism RRIDs', val:yd.org, n:yd.orgn, iconKey:'organism' },
    { label:'Cell Line RRIDs', val:yd.cl, n:yd.cln, iconKey:'cell' },
    { label:'Software Tools', val:yd.tool, n:yd.tooln, iconKey:'tool' },
    { label:'Data availability', val:yd.data, n:yd.datan },
    { label:'Code availability', val:yd.code, n:yd.coden },
    { label:'Protocol IDs', val:yd.prot, n:yd.protn },
    { label:'Data identifiers', val:yd.data_id },
    { label:'Code identifiers', val:yd.code_id },
  ];
}""",
        "pptxResourceRows",
    )

    init_block = """populateGroups();
populatePublishers();
populateCompareSelect();
showExportBtn();
renderJournalList();
renderMain();"""

    init_with_labels = """const headerYearBadge = document.getElementById('headerYearBadge');
if (headerYearBadge && DATA_YEAR_LABEL) headerYearBadge.textContent = DATA_YEAR_LABEL;
const emptySubLabel = document.getElementById('emptySubLabel');
if (emptySubLabel) {
  emptySubLabel.textContent = `Filter by publisher or search above · ${JOURNAL_COUNT_LABEL} journals · ${DATA_YEAR_LABEL}`;
}

populateGroups();
populatePublishers();
populateCompareSelect();
showExportBtn();
renderJournalList();
renderMain();"""

    content = patch_once(content, init_block, init_with_labels, "init labels")

    HTML.write_text(content, encoding="utf-8")
    print(f"Patched {HTML.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

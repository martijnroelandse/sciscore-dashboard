#!/usr/bin/env python3
"""Patch dashboard HTML with Compare against UI and single-benchmark logic."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"

SIDEBAR_INSERT = """    <div class="sidebar-section">
      <div class="sidebar-label">Compare against</div>
      <select id="compareSelect" onchange="onCompareChange()"></select>
    </div>
    <div class="sidebar-section" id="journalDisciplineSection" style="display:none">
      <div class="sidebar-label">Journal discipline</div>
      <select id="journalDisciplineSelect" onchange="onJournalDisciplineChange()"></select>
    </div>
"""

COMPARE_JS = r'''
let selectedCompareKey = 'all';
let compareTouched = false;

function compareBenchmark(year) {
  return BENCHMARK_BY_KEY?.[selectedCompareKey]?.[year] ?? null;
}

function compareLabel() {
  return BENCHMARK_CATALOG?.find(c => c.id === selectedCompareKey)?.label || 'All journals';
}

function journalClientOrg(journal) {
  if (!CLIENT_ORG_JOURNALS_BY_ORG) return null;
  for (const [org, journals] of Object.entries(CLIENT_ORG_JOURNALS_BY_ORG)) {
    if (journals.includes(journal)) return org;
  }
  return null;
}

function publisherClientOrg() {
  const scope = publisherScope();
  if (!scope) return null;
  const orgs = [...new Set(scope.journals.map(j => journalClientOrg(j)).filter(Boolean))];
  return orgs.length === 1 ? orgs[0] : null;
}

function defaultCompareKey() {
  if (selectedJournal) {
    const org = journalClientOrg(selectedJournal);
    if (org) return `org:${org}`;
    const discs = DATA.j[selectedJournal]?.disciplines;
    if (discs?.length) return `discipline:${discs[0]}`;
  } else {
    const org = publisherClientOrg();
    if (org) return `org:${org}`;
  }
  return 'all';
}

function syncCompareSelect() {
  const sel = document.getElementById('compareSelect');
  if (sel && sel.value !== selectedCompareKey) sel.value = selectedCompareKey;
}

function refreshCompareDefault() {
  if (!compareTouched) {
    selectedCompareKey = defaultCompareKey();
    syncCompareSelect();
  }
  updateJournalDisciplineSelect();
}

function populateCompareSelect() {
  const sel = document.getElementById('compareSelect');
  if (!sel || !BENCHMARK_CATALOG?.length) return;
  sel.innerHTML = '';
  const groups = {};
  BENCHMARK_CATALOG.forEach(opt => {
    if (!groups[opt.group]) groups[opt.group] = [];
    groups[opt.group].push(opt);
  });
  Object.keys(groups).forEach(group => {
    const og = document.createElement('optgroup');
    og.label = group;
    groups[group].forEach(opt => {
      const o = document.createElement('option');
      o.value = opt.id;
      o.textContent = opt.label;
      og.appendChild(o);
    });
    sel.appendChild(og);
  });
  refreshCompareDefault();
}

function updateJournalDisciplineSelect() {
  const section = document.getElementById('journalDisciplineSection');
  const sel = document.getElementById('journalDisciplineSelect');
  if (!section || !sel) return;
  const discs = selectedJournal ? (DATA.j[selectedJournal]?.disciplines || []) : [];
  if (discs.length < 2) {
    section.style.display = 'none';
    sel.innerHTML = '';
    return;
  }
  section.style.display = '';
  sel.innerHTML = discs.map(d =>
    `<option value="discipline:${d.replace(/"/g, '&quot;')}">${d}</option>`
  ).join('');
  const current = selectedCompareKey.startsWith('discipline:') ? selectedCompareKey : `discipline:${discs[0]}`;
  if (discs.some(d => `discipline:${d}` === current)) sel.value = current;
}

function onCompareChange() {
  const sel = document.getElementById('compareSelect');
  selectedCompareKey = sel?.value || 'all';
  compareTouched = true;
  updateJournalDisciplineSelect();
  refreshBenchmarkViews();
}

function onJournalDisciplineChange() {
  const sel = document.getElementById('journalDisciplineSelect');
  if (!sel?.value) return;
  selectedCompareKey = sel.value;
  compareTouched = true;
  syncCompareSelect();
  refreshBenchmarkViews();
}

function refreshBenchmarkViews() {
  if (selectedJournal) renderYearContent();
  else if (publisherScope()) renderPublisherYearContent();
  refreshTrendChart();
}

function refreshTrendChart() {
  if (!charts.trend) return;
  const years = charts.trend.data.labels;
  const primary = charts.trend.data.datasets[0];
  if (!primary) return;
  charts.trend.data.datasets = rtiTrendDatasets(years, primary.data, primary.label);
  charts.trend.update();
}

'''

RENDER_BENCH_STRIP = r'''function renderBenchStrip(yd, year) {
  const bench = compareBenchmark(year);
  const label = compareLabel();
  if (!bench?.r || yd.r == null) return '';
  return `<div class="bench-strip"><span>vs <strong>${label}</strong> RTI ${bench.r.toFixed(1)} ${deltaBadgeRti(yd.r, bench.r, label)}</span></div>`;
}'''

RENDER_BENCHMARK_PANEL = r'''function renderBenchmarkPanel(yd, year, subjectLabel) {
  const compare = compareBenchmark(year);
  const compareName = compareLabel();
  const source = CLIENT_ORG_META.source || 'unknown';
  const sourceNote = source.includes('by_year')
    ? 'All-journal averages from <strong>2026_sciscore_v3 → by_year</strong>.'
    : 'All-journal averages computed from embedded DATA (run <code>scripts/embed_benchmarks.py</code> with the xlsx in <code>data/</code> for authoritative by_year values).';

  if (!compare) {
    return '<p class="bench-panel-intro">Benchmark data is not loaded.</p>';
  }

  const rows = BENCHMARK_TABLE_ROWS.map(row => {
    if (row.section) {
      return `<tr class="section-row"><td colspan="4">${row.section}</td></tr>`;
    }
    const val = yd[row.key];
    const compareVal = compare?.[row.key];
    const delta = row.format === 'rti'
      ? (val != null && compareVal != null ? deltaBadgeRti(val, compareVal, compareName) : '—')
      : (val != null && compareVal != null ? deltaBadgePp(val, compareVal, compareName) : '—');
    return `<tr>
      <td class="metric-name">${row.label}</td>
      <td class="current">${formatBenchmarkValue(val, row.format)}</td>
      <td>${formatBenchmarkValue(compareVal, row.format)}</td>
      <td>${delta}</td>
    </tr>`;
  }).join('');

  return `
    <p class="bench-panel-intro">
      <strong>${subjectLabel}</strong> compared with <strong>${compareName}</strong> for <strong>${year}</strong>.
      ${sourceNote}
    </p>
    <div class="bench-table-wrap">
      <table class="bench-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>${subjectLabel}</th>
            <th>${compareName}</th>
            <th>Delta</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}'''

RTI_TREND_DATASETS = r'''function rtiTrendDatasets(years, primaryValues, primaryLabel) {
  const compareName = compareLabel();
  const compareVals = years.map(y => compareBenchmark(y)?.r ?? null);
  const datasets = [{
    label: primaryLabel,
    data: primaryValues,
    borderColor: BLUE,
    backgroundColor: BLUE_DIM,
    tension: 0.35,
    pointRadius: 5,
    pointBackgroundColor: BLUE,
    pointBorderColor: '#0D1B3E',
    pointBorderWidth: 2,
    fill: true,
    order: 0,
  }];
  if (compareVals.some(v => v != null)) {
    datasets.push({
      label: compareName,
      data: compareVals,
      borderColor: 'rgba(168,200,224,0.85)',
      backgroundColor: 'transparent',
      tension: 0.35,
      pointRadius: 3,
      pointBackgroundColor: 'rgba(168,200,224,0.85)',
      borderDash: [6, 4],
      fill: false,
      order: 1,
    });
  }
  return datasets;
}'''

RENDER_METRIC_CARDS_BENCH = r'''function renderMetricCards(yd, year, prevYd, prevYear, getYdForYear, bench) {
  const benchLabel = compareLabel();
  const cards = METRIC_CARDS.map(card => {
    const val = yd[card.key];
    const benchLine = bench?.[card.key] != null && val != null
      ? `<div class="metric-card-bench">${benchLabel} ${pct(bench[card.key])} ${deltaBadgePp(val, bench[card.key], benchLabel)}</div>`
      : '';
'''

UPDATE_METRIC_SECTIONS = r'''function updateMetricSections(yd, year, getYdForYear) {
  const prevYear = prevYearWithData(year, y => getYdForYear(y)?.n);
  const prevYd = prevYear ? getYdForYear(prevYear) : null;
  const bench = compareBenchmark(year);
'''

RENDER_RESOURCE_GRID = r'''function renderResourceGrid(yd, year) {
  const bench = compareBenchmark(year);
  const benchLabel = compareLabel();
  return RESOURCE_ROWS.map(r => {
    const val = yd[r.key];
    const p = val != null ? Math.round(val * 100) : null;
    const detected = yd[r.countKey] != null ? `<span class="res-detected">(${yd[r.countKey].toLocaleString()} detected)</span>` : '';
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
}'''

RADAR_DATASETS = r'''function radarDatasets(year, vals, label) {
  const compare = compareBenchmark(year);
  const compareName = compareLabel();
  const datasets = [{
    label,
    data: vals,
    borderColor: BLUE,
    backgroundColor: BLUE_DIM,
    pointBackgroundColor: BLUE,
    pointBorderColor: '#0D1B3E',
    pointBorderWidth: 2,
    pointRadius: 4,
  }];
  if (compare) {
    const compareVals = ['sex','pwr','rand','blind','irb','iacuc']
      .map(k => compare[k] != null ? Math.round(compare[k] * 100) : 0);
    datasets.push({
      label: `${compareName} avg`,
      data: compareVals,
      borderColor: 'rgba(168,200,224,0.7)',
      backgroundColor: 'rgba(168,200,224,0.08)',
      pointBackgroundColor: 'rgba(168,200,224,0.7)',
      pointBorderColor: '#0D1B3E',
      pointBorderWidth: 1,
      pointRadius: 3,
      borderDash: [4, 4],
    });
  }
  return datasets;
}'''


def replace_function(content: str, name: str, new_body: str) -> str:
    pattern = rf"function {name}\([^)]*\) \{{"
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"function {name} not found")
    start = match.start()
    brace = 0
    i = match.end() - 1
    while i < len(content):
        if content[i] == '{':
            brace += 1
        elif content[i] == '}':
            brace -= 1
            if brace == 0:
                end = i + 1
                break
        i += 1
    else:
        raise ValueError(f"could not find end of function {name}")
    return content[:start] + new_body.strip() + content[end:]


def main() -> None:
    content = HTML.read_text(encoding="utf-8")

    if 'id="compareSelect"' not in content:
        anchor = '      <select id="publisherSelect"><option value="">All publishers</option></select>\n    </div>\n'
        if anchor not in content:
            raise ValueError("sidebar anchor not found")
        content = content.replace(anchor, anchor + SIDEBAR_INSERT, 1)

    if 'function compareBenchmark' not in content:
        anchor = "function clientOrgBenchmark(year) {\n  return CLIENT_ORG_BENCHMARK[year] || null;\n}\n"
        if anchor not in content:
            raise ValueError("clientOrgBenchmark anchor not found")
        content = content.replace(anchor, anchor + COMPARE_JS, 1)

    content = replace_function(content, "renderBenchStrip", RENDER_BENCH_STRIP)
    content = replace_function(content, "renderBenchmarkPanel", RENDER_BENCHMARK_PANEL)
    content = replace_function(content, "rtiTrendDatasets", RTI_TREND_DATASETS)
    content = replace_function(content, "renderResourceGrid", RENDER_RESOURCE_GRID)
    content = replace_function(content, "radarDatasets", RADAR_DATASETS)

    # renderMetricCards - partial replace for signature and bench line
    content = content.replace(
        "function renderMetricCards(yd, year, prevYd, prevYear, getYdForYear, benchAllJ) {",
        "function renderMetricCards(yd, year, prevYd, prevYear, getYdForYear, bench) {",
    )
    content = content.replace(
        "    const benchLine = benchAllJ?.[card.key] != null && val != null\n"
        "      ? `<div class=\"metric-card-bench\">All journals ${pct(benchAllJ[card.key])} ${deltaBadgePp(val, benchAllJ[card.key], 'all journals')}</div>`\n"
        "      : '';",
        "    const benchLabel = compareLabel();\n"
        "    const benchLine = bench?.[card.key] != null && val != null\n"
        "      ? `<div class=\"metric-card-bench\">${benchLabel} ${pct(bench[card.key])} ${deltaBadgePp(val, bench[card.key], benchLabel)}</div>`\n"
        "      : '';",
    )
    content = content.replace(
        "  const benchAllJ = byYearBenchmark(year);\n\n"
        "  const insightEl = document.getElementById('insightBanner');",
        "  const bench = compareBenchmark(year);\n\n"
        "  const insightEl = document.getElementById('insightBanner');",
    )
    content = content.replace(
        "  if (cardsEl) cardsEl.innerHTML = renderMetricCards(yd, year, prevYd, prevYear, getYdForYear, benchAllJ);",
        "  if (cardsEl) cardsEl.innerHTML = renderMetricCards(yd, year, prevYd, prevYear, getYdForYear, bench);",
    )

    # radar chart calls - remove 'clients' extra arg
    content = content.replace(
        "datasets: radarDatasets(selectedYear, radarVals, selectedYear, ['clients']),",
        "datasets: radarDatasets(selectedYear, radarVals, selectedYear),",
    )
    content = content.replace(
        "datasets: radarDatasets(selectedYear, radarVals, selectedJournal, ['clients']),",
        "datasets: radarDatasets(selectedYear, radarVals, selectedJournal),",
    )

    # selectJournal / navigation hooks
    if 'refreshCompareDefault();' not in content:
        content = content.replace(
            "function selectJournal(name) {\n  selectedJournal = name;",
            "function selectJournal(name) {\n  selectedJournal = name;\n  compareTouched = false;",
        )
        content = content.replace(
            "function backToPublisher() {\n  selectedJournal = null;",
            "function backToPublisher() {\n  selectedJournal = null;\n  compareTouched = false;",
        )
        for old in [
            "groupSelect.addEventListener('change', () => {\n  selectedJournal = null;",
            "pubSelect.addEventListener('change', () => {\n  selectedJournal = null;",
        ]:
            content = content.replace(
                old,
                old + "\n  compareTouched = false;",
            )

    if 'populateCompareSelect();' not in content:
        content = content.replace(
            "populateGroups();\npopulatePublishers();\nshowExportBtn();\nrenderMain();",
            "populateGroups();\npopulatePublishers();\npopulateCompareSelect();\nshowExportBtn();\nrenderMain();",
        )

    # RRID panel - use compare benchmark
    content = content.replace(
        "  const allJ = byYearBenchmark(year);\n  const clients = clientOrgBenchmark(year);",
        "  const allJ = byYearBenchmark(year);\n  const compare = compareBenchmark(year);\n  const compareName = compareLabel();",
        1,
    )
    content = content.replace(
        "  const clientLabel = CLIENT_ORG_META.clientLabel || 'SciScore clients';\n  const compareHtml = `<div class=\"rrid-compare\">",
        "  const compareHtml = `<div class=\"rrid-compare\">",
    )
    content = content.replace(
        "<thead><tr><th>Resource</th><th>Journal</th><th>${clientLabel}</th><th>All journals</th><th>Europe PMC sample</th></tr></thead>",
        "<thead><tr><th>Resource</th><th>Journal</th><th>${compareName}</th><th>All journals</th><th>Europe PMC sample</th></tr></thead>",
    )
    content = content.replace(
        "          <td>${clients ? pct(clients[row.key]) : '—'}</td>",
        "          <td>${compare ? pct(compare[row.key]) : '—'}</td>",
    )

    # PPTX benchmark line
    content = replace_function(
        content,
        "pptxBenchmarkLine",
        r'''function pptxBenchmarkLine(yd, year) {
  const compare = compareBenchmark(year);
  const compareName = compareLabel();
  if (compare?.r != null && yd?.r != null) {
    return `${compareName} RTI ${compare.r.toFixed(1)} (${fmtDeltaRti(deltaRti(yd.r, compare.r))})`;
  }
  return '';
}''',
    )

    HTML.write_text(content, encoding="utf-8")
    print("Patched Compare against UI and single-benchmark logic into dashboard HTML")


if __name__ == "__main__":
    main()

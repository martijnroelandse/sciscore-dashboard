"""Generate self-contained entity dashboard HTML (country / institution)."""
from __future__ import annotations

import json
from typing import Any

SHARED_CSS = """
  :root {
    --navy: #0D1B3E; --navy-card: #1A2E5A; --blue: #29ABE2; --blue-light: #5CC8F0;
    --blue-dim: rgba(41,171,226,0.15); --blue-border: rgba(41,171,226,0.25);
    --white: #FFFFFF; --text: #E8F0F8; --muted: #A8C8E0; --sidebar-w: 290px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--navy); color: var(--text);
    height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
  header { background: #fff; border-bottom: 2px solid var(--blue); padding: 0 24px; height: 58px;
    display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
  .header-title { font-size: 0.9rem; color: #1A6FA0; font-weight: 500; }
  .header-badge { background: var(--blue); color: var(--navy); font-size: 0.78rem; font-weight: 700;
    padding: 3px 10px; border-radius: 20px; }
  .header-link { font-size: 0.78rem; color: #1A6FA0; text-decoration: none; font-weight: 600;
    padding: 5px 12px; border-radius: 20px; border: 1px solid var(--blue-border); }
  .layout { display: flex; flex: 1; overflow: hidden; }
  .sidebar { width: var(--sidebar-w); background: linear-gradient(180deg, #0A1628, #132348);
    border-right: 1px solid var(--blue-border); display: flex; flex-direction: column; flex-shrink: 0; }
  .sidebar-section { padding: 13px 16px 11px; border-bottom: 1px solid var(--blue-border); }
  .sidebar-label { font-size: 0.72rem; font-weight: 700; color: var(--blue); text-transform: uppercase;
    letter-spacing: 0.1em; margin-bottom: 7px; }
  select, input[type=text] { width: 100%; background: rgba(41,171,226,0.08); border: 1px solid var(--blue-border);
    color: var(--text); padding: 7px 10px; border-radius: 6px; font-size: 0.82rem; outline: none; }
  .entity-list { flex: 1; overflow-y: auto; padding: 4px 0; }
  .entity-item { padding: 8px 16px; font-size: 0.78rem; cursor: pointer; border-left: 3px solid transparent;
    line-height: 1.4; color: var(--text); }
  .entity-item:hover { background: var(--blue-dim); }
  .entity-item.active { border-left-color: var(--blue); background: rgba(41,171,226,0.12); color: var(--blue-light); font-weight: 600; }
  .entity-item-sub { font-size: 0.68rem; color: var(--muted); }
  .main { flex: 1; overflow-y: auto; padding: 22px 26px; display: flex; flex-direction: column; gap: 18px; }
  .entity-header { background: linear-gradient(135deg, #132348, #1A3A6B); border-radius: 10px; padding: 18px 22px;
    border-left: 4px solid var(--blue); }
  .entity-title { font-size: 1.2rem; font-weight: 700; color: var(--white); margin-bottom: 4px; }
  .entity-meta { font-size: 0.82rem; color: var(--blue-light); }
  .year-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
  .year-tab { padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; cursor: pointer;
    border: 1px solid var(--blue-border); color: var(--muted); background: transparent; font-family: inherit; }
  .year-tab.active { background: var(--blue); color: var(--navy); border-color: var(--blue); font-weight: 700; }
  .hero-rti { background: linear-gradient(135deg, #132348, #1A3A6B); border-radius: 12px; padding: 24px 28px;
    border: 1px solid var(--blue-border); border-left: 5px solid var(--blue); display: flex; gap: 28px; align-items: center; }
  .hero-rti-value { font-size: 3.2rem; font-weight: 800; color: var(--blue); line-height: 1; }
  .hero-rti-label { font-size: 0.78rem; font-weight: 700; color: var(--blue); text-transform: uppercase; letter-spacing: 0.1em; }
  .hero-rti-title { font-size: 1.05rem; font-weight: 600; color: var(--white); }
  .hero-rti-sub { font-size: 0.82rem; color: var(--muted); }
  .detail-panel { background: var(--navy-card); border-radius: 10px; border: 1px solid var(--blue-border); }
  .panel-toggle { width: 100%; display: flex; justify-content: space-between; align-items: center; padding: 14px 18px;
    background: transparent; border: none; color: var(--text); cursor: pointer; font-family: inherit; }
  .panel-toggle-title { font-size: 0.78rem; font-weight: 700; color: var(--blue); text-transform: uppercase; letter-spacing: 0.08em; }
  .panel-body { padding: 0 18px 18px; }
  .detail-panel.collapsed .panel-body { display: none; }
  .chart-wrap { position: relative; height: 195px; }
  .resource-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 30px; }
  .resource-row { display: flex; align-items: center; gap: 10px; }
  .res-name { font-size: 0.78rem; width: 110px; color: var(--muted); flex-shrink: 0; }
  .bar-bg { flex: 1; height: 7px; background: rgba(41,171,226,0.12); border-radius: 4px; overflow: hidden; }
  .bar-fill { height: 100%; background: var(--blue); border-radius: 4px; }
  .res-pct { font-size: 0.78rem; width: 38px; text-align: right; font-weight: 600; }
  .metric-cards-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .metric-card { background: var(--navy-card); border-radius: 10px; padding: 14px 16px; border: 1px solid var(--blue-border); }
  .metric-card-label { font-size: 0.72rem; color: var(--muted); }
  .metric-card-value { font-size: 1.65rem; font-weight: 700; color: var(--white); }
  .entity-table { width: 100%; border-collapse: collapse; font-size: 0.78rem; }
  .entity-table th { text-align: left; padding: 8px 10px; color: var(--blue); font-size: 0.7rem; text-transform: uppercase; }
  .entity-table td { padding: 8px 10px; border-bottom: 1px solid rgba(41,171,226,0.08); }
  .entity-table tr { cursor: pointer; }
  .entity-table tr:hover td { background: var(--blue-dim); }
  .empty { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1;
    gap: 14px; text-align: center; color: var(--muted); padding: 40px; }
  .breadcrumb-btn { background: none; border: none; color: var(--blue-light); cursor: pointer; font-size: 0.82rem; margin-bottom: 8px; }
  .bench-strip { margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(41,171,226,0.15); font-size: 0.72rem; color: var(--muted); }
  .bench-delta { font-size: 0.68rem; font-weight: 600; padding: 1px 5px; border-radius: 4px; margin-left: 4px; }
  .bench-delta.pos { color: #6ee7b7; background: rgba(16,185,129,0.15); }
  .bench-delta.neg { color: #fca5a5; background: rgba(239,68,68,0.12); }
  .ror-badge { display: inline-block; font-size: 0.68rem; font-weight: 600; color: #c7d2fe;
    background: rgba(99,102,241,0.18); border: 1px solid rgba(99,102,241,0.35); padding: 2px 8px;
    border-radius: 999px; margin-left: 8px; text-decoration: none; }
  .ror-badge:hover { background: rgba(99,102,241,0.32); }
  .ror-panel { margin-top: 12px; padding: 12px 14px; background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.25); border-radius: 8px; font-size: 0.8rem; }
  .ror-hierarchy { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
  .ror-hierarchy a { color: var(--blue-light); text-decoration: none; font-size: 0.78rem; }
  .ror-hierarchy a:hover { text-decoration: underline; }
  .data-notice { font-size: 0.72rem; color: #fbbf24; background: rgba(251,191,36,0.1); padding: 6px 10px;
    border-radius: 6px; margin-top: 8px; }
  .jmir-badge { font-size: 0.68rem; color: var(--muted); background: rgba(255,255,255,0.06);
    padding: 2px 8px; border-radius: 4px; margin-left: 8px; }
"""


def _shared_metrics_js() -> str:
    return r"""
const pct = v => v == null ? '—' : (v * 100).toFixed(1) + '%';
const RATE_KEYS = ['r','sex','pwr','rand','blind','irb','iacuc','ab','org','cl','tool','data','code','prot','data_id','code_id'];
const BLUE = '#29ABE2', BLUE_DIM = 'rgba(41,171,226,0.15)', BLUE_GRID = 'rgba(41,171,226,0.1)', MUTED = '#7A9BBF';
const RTI_CHART_MIN = 3, RTI_CHART_MAX = 7;
let charts = {}, selectedYear = null;

function aggregateYear(keys, year, dataMap) {
  const w = {}, d = {}; let totalN = 0, entityCount = 0;
  RATE_KEYS.forEach(k => { w[k] = 0; d[k] = 0; });
  keys.forEach(k => {
    const yd = dataMap[k]?.y?.[year];
    if (!yd?.n) return;
    entityCount++;
    totalN += yd.n;
    RATE_KEYS.forEach(rk => {
      if (yd[rk] != null) { w[rk] += yd[rk] * yd.n; d[rk] += yd.n; }
    });
  });
  if (!totalN) return null;
  const out = { n: totalN, entityCount };
  RATE_KEYS.forEach(rk => { out[rk] = d[rk] ? w[rk] / d[rk] : null; });
  return out;
}

function compareBenchmark(year) { return BY_YEAR_BENCHMARK[year] || null; }

function deltaRti(val, bench) {
  if (val == null || bench == null) return null;
  return val - bench;
}

function deltaBadgeRti(val, bench) {
  const d = deltaRti(val, bench);
  if (d == null) return '';
  const cls = Math.abs(d) < 0.1 ? 'neutral' : d > 0 ? 'pos' : 'neg';
  const sign = d > 0 ? '+' : '';
  return `<span class="bench-delta ${cls}">${sign}${d.toFixed(1)}</span>`;
}

function renderBenchStrip(yd, year) {
  const bench = compareBenchmark(year);
  if (!bench?.r || yd.r == null) return '';
  return `<div class="bench-strip">vs <strong>corpus</strong> RTI ${bench.r.toFixed(1)} ${deltaBadgeRti(yd.r, bench.r)}</div>`;
}

function rtiTrendDatasets(years, primaryValues, primaryLabel) {
  const compareVals = years.map(y => compareBenchmark(y)?.r ?? null);
  const datasets = [{
    label: primaryLabel, data: primaryValues, borderColor: BLUE, backgroundColor: BLUE_DIM,
    tension: 0.35, pointRadius: 5, pointBackgroundColor: BLUE, fill: true,
  }];
  if (compareVals.some(v => v != null)) {
    datasets.push({
      label: 'Corpus average', data: compareVals, borderColor: 'rgba(168,200,224,0.85)',
      borderDash: [6,4], fill: false, pointRadius: 3, tension: 0.35,
    });
  }
  return datasets;
}

function rtiTrendChartOptions() {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: MUTED, font: { size: 10 } } } },
    scales: {
      x: { ticks: { color: MUTED }, grid: { color: BLUE_GRID } },
      y: { min: RTI_CHART_MIN, max: RTI_CHART_MAX, ticks: { color: MUTED }, grid: { color: BLUE_GRID } },
    },
  };
}

const RESOURCE_ROWS = [
  { key: 'ab', label: 'Antibodies w/ RRID' },
  { key: 'org', label: 'Organisms w/ RRID' },
  { key: 'cl', label: 'Cell lines w/ RRID' },
  { key: 'tool', label: 'Software tools' },
];
const OPEN_SCIENCE_ROWS = [
  { key: 'data', label: 'Data availability' },
  { key: 'code', label: 'Code availability' },
  { key: 'prot', label: 'Protocol IDs' },
  { key: 'data_id', label: 'Data identifiers' },
  { key: 'code_id', label: 'Code identifiers' },
];

function renderMetricBarGrid(rows, yd) {
  return rows.map(row => {
    const v = yd[row.key];
    const pctVal = v != null ? Math.round(v * 100) : 0;
    return `<div class="resource-row"><span class="res-name">${row.label}</span>
      <div class="bar-bg"><div class="bar-fill" style="width:${pctVal}%"></div></div>
      <span class="res-pct">${pct(v)}</span></div>`;
  }).join('');
}

const METRIC_CARDS = [
  { key: 'sex', label: 'Sex reporting' },
  { key: 'pwr', label: 'Power analysis' },
  { key: 'rand', label: 'Randomization' },
  { key: 'blind', label: 'Blinding' },
  { key: 'irb', label: 'IRB / ethics' },
  { key: 'ab', label: 'Antibody RRIDs' },
];

function renderMetricCards(yd, year) {
  const bench = compareBenchmark(year);
  return `<div class="metric-cards-grid">${METRIC_CARDS.map(card => {
    const val = yd[card.key];
    const b = bench?.[card.key];
    const display = card.key === 'r' ? (val?.toFixed(1) ?? '—') : pct(val);
  return `<div class="metric-card"><div class="metric-card-label">${card.label}</div>
    <div class="metric-card-value">${display}</div>
    ${b != null && val != null ? `<div style="font-size:0.68rem;color:var(--muted)">vs corpus ${pct(b)}</div>` : ''}
  </div>`; }).join('')}</div>`;
}

function destroyCharts() {
  Object.values(charts).forEach(c => { try { c.destroy(); } catch(e){} });
  charts = {};
}

function togglePanel(id) {
  document.getElementById(id)?.classList.toggle('collapsed');
}

const SORT_LABELS = {
  'papers-desc': 'papers (most)',
  'rti-desc': 'RTI (highest)',
  'rti-asc': 'RTI (lowest)',
  'name-asc': 'name (A–Z)',
};

function getSortMode() {
  return document.getElementById('entitySort')?.value || 'papers-desc';
}

function sortModeLabel(mode) {
  return SORT_LABELS[mode] || mode;
}

function sortEntityKeys(keys, mode, dataMap, year, getName) {
  const nameFn = getName || (k => k);
  return [...keys].sort((a, b) => {
    const ya = dataMap[a]?.y?.[year];
    const yb = dataMap[b]?.y?.[year];
    if (mode === 'rti-desc') {
      const ra = ya?.r ?? -Infinity, rb = yb?.r ?? -Infinity;
      return rb - ra || nameFn(a).localeCompare(nameFn(b));
    }
    if (mode === 'rti-asc') {
      const ra = ya?.r ?? Infinity, rb = yb?.r ?? Infinity;
      return ra - rb || nameFn(a).localeCompare(nameFn(b));
    }
    if (mode === 'name-asc') return nameFn(a).localeCompare(nameFn(b));
    const na = ya?.n || 0, nb = yb?.n || 0;
    return nb - na || nameFn(a).localeCompare(nameFn(b));
  });
}

function renderDetailPanels(prefix) {
  return `
    <div id="heroRti"></div>
    <div id="metricCards"></div>
    <div class="detail-panel" id="panelTrend">
      <button type="button" class="panel-toggle" onclick="togglePanel('panelTrend')">
        <span class="panel-toggle-title">RTI — Year on Year</span><span>▼</span>
      </button>
      <div class="panel-body"><div class="chart-wrap"><canvas id="trendChart"></canvas></div></div>
    </div>
    <div class="detail-panel" id="panelStudy">
      <button type="button" class="panel-toggle" onclick="togglePanel('panelStudy')">
        <span class="panel-toggle-title">Study Design · <span id="radarYear"></span></span><span>▼</span>
      </button>
      <div class="panel-body"><div class="chart-wrap"><canvas id="radarChart"></canvas></div></div>
    </div>
    <div class="detail-panel" id="panelResource">
      <button type="button" class="panel-toggle" onclick="togglePanel('panelResource')">
        <span class="panel-toggle-title">Resource Findability · <span id="resYear"></span></span><span>▼</span>
      </button>
      <div class="panel-body"><div class="resource-grid" id="resourceGrid"></div></div>
    </div>
    <div class="detail-panel" id="panelOpenScience">
      <button type="button" class="panel-toggle" onclick="togglePanel('panelOpenScience')">
        <span class="panel-toggle-title">Open Science · <span id="openYear"></span></span><span>▼</span>
      </button>
      <div class="panel-body"><div class="resource-grid" id="openScienceGrid"></div></div>
    </div>`;
}

function updateYearPanels(yd, year, trendYears, trendValues, radarLabel) {
  document.getElementById('heroRti').innerHTML = `
    <div class="hero-rti">
      <div><div class="hero-rti-value">${yd.r != null ? yd.r.toFixed(1) : '—'}</div><div style="color:var(--muted)">/ 10</div></div>
      <div>
        <div class="hero-rti-label">Rigor & Transparency Index</div>
        <div class="hero-rti-title">${year} · ${yd.n?.toLocaleString() || 0} papers</div>
        <div class="hero-rti-sub">JMIR 2022 open-access corpus</div>
        ${renderBenchStrip(yd, year)}
      </div>
    </div>`;
  document.getElementById('metricCards').innerHTML = renderMetricCards(yd, year);
  document.getElementById('radarYear').textContent = year;
  document.getElementById('resYear').textContent = year;
  document.getElementById('openYear').textContent = year;
  document.getElementById('resourceGrid').innerHTML = renderMetricBarGrid(RESOURCE_ROWS, yd);
  document.getElementById('openScienceGrid').innerHTML = renderMetricBarGrid(OPEN_SCIENCE_ROWS, yd);

  if (charts.radar) charts.radar.destroy();
  const radarLabels = ['Sex','Power','Randomization','Blinding','IRB','IACUC'];
  const radarVals = [yd.sex, yd.pwr, yd.rand, yd.blind, yd.irb, yd.iacuc].map(v => v != null ? Math.round(v*100) : 0);
  charts.radar = new Chart(document.getElementById('radarChart').getContext('2d'), {
    type: 'radar',
    data: { labels: radarLabels, datasets: [{ label: radarLabel, data: radarVals, borderColor: BLUE, backgroundColor: BLUE_DIM, pointBackgroundColor: BLUE }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: MUTED } } },
      scales: { r: { min: 0, max: 100, ticks: { color: MUTED, stepSize: 25 }, grid: { color: BLUE_GRID }, pointLabels: { color: MUTED } } }
    }
  });
}
"""


def _country_app_js() -> str:
    return r"""
let selectedCountry = null;
const ENTITY_MAP = DATA.c;
const LATEST_YEAR = String(Math.max(...Object.keys(BY_YEAR_BENCHMARK).map(y => +y)));
const ALL_KEYS = Object.keys(ENTITY_MAP);
const YEARS = [...new Set(ALL_KEYS.flatMap(k => Object.keys(ENTITY_MAP[k].y || {})))].sort((a,b) => +a - +b);

function latestYearFor(key) {
  const ys = Object.keys(ENTITY_MAP[key]?.y || {}).sort((a,b) => +a - +b);
  return ys[ys.length - 1];
}

function renderEntityList() {
  const q = (document.getElementById('entitySearch').value || '').toLowerCase();
  const list = document.getElementById('entityList');
  list.innerHTML = '';
  const matched = ALL_KEYS.filter(k => !q || k.toLowerCase().includes(q));
  const filtered = sortEntityKeys(matched, getSortMode(), ENTITY_MAP, LATEST_YEAR);
  document.getElementById('entityCountLabel').textContent =
    `${filtered.length.toLocaleString()} countries · sorted by ${sortModeLabel(getSortMode())}`;
  filtered.forEach(k => {
    const ly = latestYearFor(k);
    const yd = ENTITY_MAP[k]?.y?.[ly];
    const el = document.createElement('div');
    el.className = 'entity-item' + (k === selectedCountry ? ' active' : '');
    el.innerHTML = `<div>${k}</div><div class="entity-item-sub">${yd?.n ? yd.n.toLocaleString() + ' papers · RTI ' + (yd.r?.toFixed(1) || '—') : ''}</div>`;
    el.onclick = () => selectCountry(k);
    list.appendChild(el);
  });
}

function selectCountry(name) {
  selectedCountry = name;
  const years = YEARS.filter(y => ENTITY_MAP[name]?.y?.[y]);
  selectedYear = years[years.length - 1] || null;
  renderEntityList();
  renderMain();
}

function renderMain() {
  destroyCharts();
  if (!selectedCountry) {
    document.getElementById('main').innerHTML = `<div class="empty"><div style="font-size:2.5rem;opacity:0.3">🌍</div>
      <div>Select a country from the sidebar</div>
      <div style="font-size:0.82rem">${ALL_KEYS.length} countries · ${YEARS[0]}–${YEARS[YEARS.length-1]}</div></div>`;
    return;
  }
  const entry = ENTITY_MAP[selectedCountry];
  const years = YEARS.filter(y => entry.y?.[y]);
  const main = document.getElementById('main');
  main.innerHTML = `
    <div class="entity-header">
      <div class="entity-title">${selectedCountry}</div>
      <div class="entity-meta">Country · JMIR 2022 corpus <span class="jmir-badge">historical snapshot</span></div>
      <div class="data-notice">Data from the 2022 JMIR paper — not the current SciScore v3 journal dataset.</div>
    </div>
    <div class="year-tabs">${years.map(y => `<button class="year-tab${y===selectedYear?' active':''}" onclick="selectYear('${y}')">${y}</button>`).join('')}</div>
    ${renderDetailPanels('country')}
  `;
  const trendData = years.map(y => entry.y[y]?.r ?? null);
  charts.trend = new Chart(document.getElementById('trendChart').getContext('2d'), {
    type: 'line', data: { labels: years, datasets: rtiTrendDatasets(years, trendData, selectedCountry) },
    options: rtiTrendChartOptions(),
  });
  renderYearContent();
}

function selectYear(y) { selectedYear = y; renderYearContent(); }

function renderYearContent() {
  if (!selectedCountry || !selectedYear) return;
  const yd = ENTITY_MAP[selectedCountry].y[selectedYear];
  if (!yd) return;
  document.querySelectorAll('.year-tab').forEach(b => b.classList.toggle('active', b.textContent === selectedYear));
  const years = YEARS.filter(y => ENTITY_MAP[selectedCountry].y?.[y]);
  updateYearPanels(yd, selectedYear, years, years.map(y => ENTITY_MAP[selectedCountry].y[y]?.r), selectedCountry);
}

function initCountryDashboard() {
  document.getElementById('entitySearch').addEventListener('input', renderEntityList);
  document.getElementById('entitySort').addEventListener('change', renderEntityList);
  renderEntityList();
  const defaultCountry = ALL_KEYS.includes('United States') ? 'United States' : ALL_KEYS[0];
  if (defaultCountry) selectCountry(defaultCountry);
}

initCountryDashboard();
"""


def _institution_app_js() -> str:
    return r"""
let selectedCountry = 'United States';
let selectedInstitution = null;
const ENTITY_MAP = DATA.i;
const BY_COUNTRY = DATA.by_country || {};
const ALL_COUNTRIES = Object.keys(BY_COUNTRY).sort();
const LATEST_YEAR = String(Math.max(...Object.keys(BY_YEAR_BENCHMARK).map(y => +y)));
const ALL_KEYS = Object.keys(ENTITY_MAP).sort();
const YEARS = [...new Set(ALL_KEYS.flatMap(k => Object.keys(ENTITY_MAP[k].y || {})))].sort((a,b) => +a - +b);

function parseKey(key) { const i = key.lastIndexOf('|'); return i < 0 ? [key, ''] : [key.slice(0,i), key.slice(i+1)]; }
function displayName(key) { return parseKey(key)[0]; }

function rorLink(ror) {
  if (!ror?.id) return '';
  const shortId = ror.id.replace('https://ror.org/', '');
  return `<a class="ror-badge" href="https://ror.org/${shortId}" target="_blank" rel="noopener">ROR · ${shortId}</a>`;
}

function renderRorPanel(entry) {
  const ror = entry.ror;
  if (!ror) return '<div class="ror-panel">No ROR match — sub-units may not have a separate ROR record.</div>';
  const shortId = ror.id.replace('https://ror.org/', '');
  let html = `<div class="ror-panel"><strong>ROR:</strong> <a href="https://ror.org/${shortId}" target="_blank" style="color:var(--blue-light)">${ror.name || shortId}</a>`;
  if (ror.types?.length) html += ` · ${ror.types.join(', ')}`;
  if (ror.method) html += ` <span style="color:var(--muted);font-size:0.72rem">(${ror.method})</span>`;
  const parents = ror.parents || [];
  const children = ror.children || [];
  if (parents.length || children.length) {
    html += '<div class="ror-hierarchy">';
    parents.forEach(p => {
      const pid = (p.id || '').replace('https://ror.org/', '');
      html += `<div>↑ Parent: <a href="https://ror.org/${pid}" target="_blank">${p.label || pid}</a></div>`;
    });
    children.slice(0, 8).forEach(c => {
      const cid = (c.id || '').replace('https://ror.org/', '');
      html += `<div>↓ Child: <a href="https://ror.org/${cid}" target="_blank">${c.label || cid}</a></div>`;
    });
    if (children.length > 8) html += `<div style="color:var(--muted)">+ ${children.length - 8} more child orgs in ROR</div>`;
    html += '</div>';
  }
  return html + '</div>';
}

function sortedKeys(keys) {
  return sortEntityKeys(keys, getSortMode(), ENTITY_MAP, LATEST_YEAR, displayName);
}

function matchingKeys() {
  let keys = selectedCountry ? (BY_COUNTRY[selectedCountry] || []) : ALL_KEYS;
  const q = (document.getElementById('entitySearch').value || '').toLowerCase();
  if (q) keys = keys.filter(k => displayName(k).toLowerCase().includes(q) || k.toLowerCase().includes(q));
  return keys;
}

function filteredKeys() {
  return sortedKeys(matchingKeys()).slice(0, 500);
}

function populateCountries() {
  const sel = document.getElementById('countrySelect');
  if (!ALL_COUNTRIES.includes(selectedCountry) && ALL_COUNTRIES.length) {
    selectedCountry = ALL_COUNTRIES.includes('United States') ? 'United States' : ALL_COUNTRIES[0];
  }
  sel.innerHTML = '<option value="">All countries</option>' +
    ALL_COUNTRIES.map(c => `<option value="${c.replace(/"/g,'&quot;')}"${c===selectedCountry?' selected':''}>${c}</option>`).join('');
}

function renderEntityList() {
  const list = document.getElementById('entityList');
  list.innerHTML = '';
  const matched = matchingKeys();
  const keys = sortedKeys(matched).slice(0, 500);
  const suffix = keys.length < matched.length ? ` (top ${keys.length} of ${matched.length.toLocaleString()})` : '';
  document.getElementById('entityCountLabel').textContent =
    `${keys.length.toLocaleString()} institutions${suffix} · sorted by ${sortModeLabel(getSortMode())}`;
  keys.forEach(k => {
    const entry = ENTITY_MAP[k];
    const ly = LATEST_YEAR;
    const yd = entry?.y?.[ly];
    const el = document.createElement('div');
    el.className = 'entity-item' + (k === selectedInstitution ? ' active' : '');
    el.innerHTML = `<div>${displayName(k)}</div><div class="entity-item-sub">${entry.country || ''}${yd?.n ? ' · ' + yd.n.toLocaleString() + ' papers' : ''}${yd?.r != null ? ' · RTI ' + yd.r.toFixed(1) : ''}${entry.ror ? ' · ROR' : ''}</div>`;
    el.onclick = () => selectInstitution(k);
    list.appendChild(el);
  });
}

function selectInstitution(key) {
  selectedInstitution = key;
  const years = YEARS.filter(y => ENTITY_MAP[key]?.y?.[y]);
  selectedYear = years[years.length - 1] || null;
  if (!selectedCountry) {
    const c = ENTITY_MAP[key]?.country;
    if (c && BY_COUNTRY[c]) selectedCountry = c;
  }
  populateCountries();
  renderEntityList();
  renderMain();
}

function selectCountryFilter() {
  selectedCountry = document.getElementById('countrySelect').value;
  selectedInstitution = null;
  renderEntityList();
  renderMain();
}

function backToCountry() {
  selectedInstitution = null;
  renderEntityList();
  renderMain();
}

function renderMain() {
  destroyCharts();
  if (selectedInstitution) return renderInstitutionView();
  if (selectedCountry) return renderCountryPortfolio();
  document.getElementById('main').innerHTML = `<div class="empty"><div style="font-size:2.5rem;opacity:0.3">🏛</div>
    <div>Select a country or institution</div>
    <div style="font-size:0.82rem">${ALL_KEYS.length.toLocaleString()} institutions · ${ALL_COUNTRIES.length} countries</div></div>`;
}

function renderCountryPortfolio() {
  const keys = BY_COUNTRY[selectedCountry] || [];
  const years = YEARS.filter(y => keys.some(k => ENTITY_MAP[k]?.y?.[y]));
  if (!selectedYear || !years.includes(selectedYear)) selectedYear = years[years.length - 1];
  const main = document.getElementById('main');
  main.innerHTML = `
    <div class="entity-header">
      <div class="entity-title">${selectedCountry}</div>
      <div class="entity-meta">Country portfolio · ${keys.length.toLocaleString()} institutions</div>
      <div class="data-notice">JMIR 2022 historical data — separate from the journal dashboard.</div>
    </div>
    <div class="year-tabs">${years.map(y => `<button class="year-tab${y===selectedYear?' active':''}" onclick="selectYear('${y}')">${y}</button>`).join('')}</div>
    ${renderDetailPanels('portfolio')}
    <div class="detail-panel" id="panelTable">
      <button type="button" class="panel-toggle" onclick="togglePanel('panelTable')">
        <span class="panel-toggle-title">Institutions · <span id="tableYear"></span></span><span>▼</span>
      </button>
      <div class="panel-body"><table class="entity-table"><thead><tr>
        <th>Institution</th><th style="text-align:right">RTI</th><th style="text-align:right">Papers</th><th>ROR</th>
      </tr></thead><tbody id="instTableBody"></tbody></table></div>
    </div>`;
  const trendData = years.map(y => aggregateYear(keys, y, ENTITY_MAP)?.r ?? null);
  charts.trend = new Chart(document.getElementById('trendChart').getContext('2d'), {
    type: 'line', data: { labels: years, datasets: rtiTrendDatasets(years, trendData, selectedCountry + ' portfolio') },
    options: rtiTrendChartOptions(),
  });
  renderPortfolioYear();
}

function renderInstitutionView() {
  const entry = ENTITY_MAP[selectedInstitution];
  const name = displayName(selectedInstitution);
  const years = YEARS.filter(y => entry.y?.[y]);
  const main = document.getElementById('main');
  main.innerHTML = `
    ${selectedCountry ? `<button class="breadcrumb-btn" onclick="backToCountry()">← ${selectedCountry} overview</button>` : ''}
    <div class="entity-header">
      <div class="entity-title">${name} ${rorLink(entry.ror)}</div>
      <div class="entity-meta">${[entry.country, entry.state, entry.established ? 'est. ' + entry.established : ''].filter(Boolean).join(' · ')}</div>
      ${renderRorPanel(entry)}
      <div class="data-notice">JMIR 2022 historical data — separate from the journal dashboard.</div>
    </div>
    <div class="year-tabs">${years.map(y => `<button class="year-tab${y===selectedYear?' active':''}" onclick="selectYear('${y}')">${y}</button>`).join('')}</div>
    ${renderDetailPanels('inst')}
  `;
  const trendData = years.map(y => entry.y[y]?.r ?? null);
  charts.trend = new Chart(document.getElementById('trendChart').getContext('2d'), {
    type: 'line', data: { labels: years, datasets: rtiTrendDatasets(years, trendData, name) },
    options: rtiTrendChartOptions(),
  });
  renderInstitutionYear();
}

function selectYear(y) { selectedYear = y; if (selectedInstitution) renderInstitutionYear(); else renderPortfolioYear(); }

function renderPortfolioYear() {
  const keys = BY_COUNTRY[selectedCountry] || [];
  const yd = aggregateYear(keys, selectedYear, ENTITY_MAP);
  if (!yd) return;
  document.querySelectorAll('.year-tab').forEach(b => b.classList.toggle('active', b.textContent === selectedYear));
  document.getElementById('tableYear').textContent = selectedYear;
  const years = YEARS.filter(y => keys.some(k => ENTITY_MAP[k]?.y?.[y]));
  updateYearPanels(yd, selectedYear, years, years.map(y => aggregateYear(keys, y, ENTITY_MAP)?.r), selectedCountry);
  const ranked = sortedKeys(keys).map(k => ({ k, yd: ENTITY_MAP[k]?.y?.[selectedYear] })).filter(x => x.yd?.n);
  const tbody = document.getElementById('instTableBody');
  tbody.innerHTML = '';
  ranked.forEach(({ k, yd: jyd }) => {
    const ror = ENTITY_MAP[k].ror;
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${displayName(k)}</td>
      <td style="text-align:right;font-weight:700;color:var(--blue-light)">${jyd.r?.toFixed(1)||'—'}</td>
      <td style="text-align:right">${jyd.n}</td>
      <td>${ror ? '<span style="color:var(--blue-light);font-size:0.72rem">✓</span>' : '—'}</td>`;
    tr.onclick = () => selectInstitution(k);
    tbody.appendChild(tr);
  });
}

function renderInstitutionYear() {
  const yd = ENTITY_MAP[selectedInstitution].y[selectedYear];
  if (!yd) return;
  document.querySelectorAll('.year-tab').forEach(b => b.classList.toggle('active', b.textContent === selectedYear));
  const name = displayName(selectedInstitution);
  const years = YEARS.filter(y => ENTITY_MAP[selectedInstitution].y?.[y]);
  updateYearPanels(yd, selectedYear, years, years.map(y => ENTITY_MAP[selectedInstitution].y[y]?.r), name);
}

function initInstitutionDashboard() {
  document.getElementById('countrySelect').addEventListener('change', selectCountryFilter);
  document.getElementById('entitySearch').addEventListener('input', renderEntityList);
  document.getElementById('entitySort').addEventListener('change', () => {
    renderEntityList();
    if (selectedInstitution) renderMain();
    else if (selectedCountry) renderPortfolioYear();
  });
  if (!ALL_COUNTRIES.includes(selectedCountry)) {
    selectedCountry = ALL_COUNTRIES.includes('United States') ? 'United States' : (ALL_COUNTRIES[0] || '');
  }
  populateCountries();
  renderEntityList();
  renderMain();
}

initInstitutionDashboard();
"""


def render_dashboard_html(
    entity_type: str,
    title: str,
    subtitle: str,
    data: dict,
    benchmark: dict,
    meta: dict,
) -> str:
    years = sorted(meta.get("years", {}).keys(), key=int)
    year_label = f"{years[0]}–{years[-1]}" if years else ""
    data_json = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    bench_json = json.dumps(benchmark, separators=(",", ":"), ensure_ascii=False)

    sort_select = """
    <div class="sidebar-section"><div class="sidebar-label">Sort by</div>
      <select id="entitySort">
        <option value="papers-desc">Papers (most)</option>
        <option value="rti-desc">RTI (highest)</option>
        <option value="rti-asc">RTI (lowest)</option>
        <option value="name-asc">Name (A–Z)</option>
      </select></div>"""
    if entity_type == "country":
        sidebar = f"""
    <div class="sidebar-section"><div class="sidebar-label">Search country</div>
      <input type="text" id="entitySearch" placeholder="Type country name…"></div>
    {sort_select}
    <div class="sidebar-section"><span id="entityCountLabel" style="font-size:0.75rem;color:var(--muted)"></span></div>
    <div class="entity-list" id="entityList"></div>"""
        app_js = _country_app_js()
        sidebar_count_script = ""
    else:
        sidebar = f"""
    <div class="sidebar-section"><div class="sidebar-label">Country</div>
      <select id="countrySelect"><option value="">All countries</option></select></div>
    <div class="sidebar-section"><div class="sidebar-label">Search institution</div>
      <input type="text" id="entitySearch" placeholder="Type institution name…"></div>
    {sort_select}
    <div class="sidebar-section"><span id="entityCountLabel" style="font-size:0.75rem;color:var(--muted)"></span></div>
    <div class="entity-list" id="entityList"></div>"""
        app_js = _institution_app_js()
        sidebar_count_script = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>{SHARED_CSS}</style>
</head>
<body>
<header>
  <div class="header-title">{title}</div>
  <nav style="display:flex;gap:12px;align-items:center">
    <a class="header-link" href="addendum.html">Methods &amp; glossary</a>
    <div class="header-badge">{year_label} · JMIR 2022</div>
  </nav>
</header>
<div class="layout">
  <div class="sidebar">{sidebar}</div>
  <div class="main" id="main"></div>
</div>
<script>
const DATA = {data_json};
const BY_YEAR_BENCHMARK = {bench_json};
{_shared_metrics_js()}
{app_js}
{sidebar_count_script}
</script>
</body>
</html>
"""

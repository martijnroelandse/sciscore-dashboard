#!/usr/bin/env python3
"""Patch SciScore_journal_dashboard.html with groups, collapsible panels, PPTX fix."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"
GROUP_MAP_JS = Path("/tmp/group_map.js")

EXTRA_CSS = """
  /* HERO RTI */
  .hero-rti {
    background: linear-gradient(135deg, #132348 0%, #1A3A6B 100%);
    border-radius: 12px;
    padding: 24px 28px;
    border: 1px solid var(--blue-border);
    border-left: 5px solid var(--blue);
    display: flex;
    align-items: center;
    gap: 28px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
  }
  .hero-rti-score { flex-shrink: 0; text-align: center; min-width: 110px; }
  .hero-rti-value { font-size: 3.2rem; font-weight: 800; color: var(--blue); line-height: 1; }
  .hero-rti-max { font-size: 1rem; color: var(--muted); font-weight: 500; }
  .hero-rti-meta { flex: 1; }
  .hero-rti-label { font-size: 0.78rem; font-weight: 700; color: var(--blue); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }
  .hero-rti-title { font-size: 1.05rem; font-weight: 600; color: var(--white); margin-bottom: 4px; }
  .hero-rti-sub { font-size: 0.82rem; color: var(--muted); }
  .hero-kpis { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 12px; }
  .hero-kpi { font-size: 0.78rem; color: var(--muted); }
  .hero-kpi strong { color: var(--text); font-size: 0.95rem; display: block; }

  /* COLLAPSIBLE PANELS */
  .detail-panel {
    background: var(--navy-card);
    border-radius: 10px;
    border: 1px solid var(--blue-border);
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    overflow: hidden;
  }
  .panel-toggle {
    width: 100%; display: flex; align-items: center; justify-content: space-between;
    padding: 14px 18px; background: transparent; border: none; cursor: pointer;
    font-family: inherit; text-align: left;
  }
  .panel-toggle:hover { background: rgba(41,171,226,0.06); }
  .panel-toggle-title {
    font-size: 0.78rem; font-weight: 700; color: var(--blue);
    text-transform: uppercase; letter-spacing: 0.08em;
  }
  .panel-chevron { color: var(--blue); font-size: 0.7rem; transition: transform 0.2s; }
  .detail-panel.collapsed .panel-chevron { transform: rotate(-90deg); }
  .detail-panel.collapsed .panel-body { display: none; }
  .panel-body { padding: 0 18px 18px; }
  .panel-body .chart-wrap { height: 210px; }
"""

SIDEBAR_HTML = """    <div class="sidebar-section">
      <div class="sidebar-label">Publisher group</div>
      <select id="groupSelect"><option value="">All groups</option></select>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-label">Publisher</div>
      <select id="publisherSelect"><option value="">All publishers</option></select>
    </div>
    <div class="sidebar-section">
      <button class="export-btn" id="exportBtn" onclick="generatePPTX()">&#9654; Export Report</button>
    </div>"""

NEW_JS = r'''
const YEARS = ['2015','2016','2017','2018','2019','2020','2021','2022','2023','2024','2025'];
const BLUE       = '#29ABE2';
const BLUE_LIGHT = '#5CC8F0';
const BLUE_DIM   = 'rgba(41,171,226,0.15)';
const BLUE_GRID  = 'rgba(41,171,226,0.1)';
const MUTED      = '#7A9BBF';
const WHITE      = '#FFFFFF';

let charts = {};
let selectedJournal = null;
let selectedYear = null;

const pct = v => v == null ? '—' : (v * 100).toFixed(1) + '%';
const fmt = v => v == null ? '—' : v.toFixed(2);

function getPublisherGroup(pub) {
  return GROUP_MAP[pub] || pub || 'Unknown';
}

function buildGroupIndex() {
  const g = {};
  Object.keys(DATA.p).forEach(pub => {
    const grp = getPublisherGroup(pub);
    if (!g[grp]) g[grp] = [];
    g[grp].push(pub);
  });
  Object.values(g).forEach(arr => arr.sort((a, b) => a.localeCompare(b)));
  return g;
}

const GROUPS = buildGroupIndex();

const groupSelect = document.getElementById('groupSelect');
const pubSelect = document.getElementById('publisherSelect');

function groupJournalCount(grp) {
  return (GROUPS[grp] || []).reduce((n, pub) => n + (DATA.p[pub]?.length || 0), 0);
}

function populateGroups() {
  Object.keys(GROUPS)
    .sort((a, b) => groupJournalCount(b) - groupJournalCount(a) || a.localeCompare(b))
    .forEach(grp => {
      const opt = document.createElement('option');
      opt.value = grp;
      opt.textContent = `${grp} (${groupJournalCount(grp).toLocaleString()})`;
      groupSelect.appendChild(opt);
    });
}

function publishersForFilters() {
  const grp = groupSelect.value;
  let pubs = grp ? [...(GROUPS[grp] || [])] : Object.keys(DATA.p);
  pubs.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
  return pubs;
}

function populatePublishers() {
  const prev = pubSelect.value;
  const pubs = publishersForFilters();
  pubSelect.innerHTML = '<option value="">All publishers</option>';
  pubs.forEach(pub => {
    const opt = document.createElement('option');
    opt.value = pub;
    opt.textContent = `${pub} (${DATA.p[pub].length})`;
    pubSelect.appendChild(opt);
  });
  if (prev && pubs.includes(prev)) pubSelect.value = prev;
  else if (prev) pubSelect.value = '';
}

function getFilteredJournals() {
  const pubs = publishersForFilters();
  const pub = pubSelect.value;
  const q = document.getElementById('journalSearch').value.trim().toLowerCase();
  let list = pub ? (DATA.p[pub] || []) : pubs.flatMap(p => DATA.p[p] || []);
  list = [...new Set(list)];
  if (q) list = list.filter(j => j.toLowerCase().includes(q));
  list.sort((a, b) => a.localeCompare(b));
  return list;
}

function renderJournalList() {
  const list = getFilteredJournals();
  document.getElementById('journalCountLabel').textContent = `${list.length.toLocaleString()} journals`;
  const container = document.getElementById('journalList');
  container.innerHTML = '';
  list.forEach(j => {
    const el = document.createElement('div');
    el.className = 'journal-item' + (j === selectedJournal ? ' active' : '');
    el.textContent = j;
    el.onclick = () => selectJournal(j);
    container.appendChild(el);
  });
}

function selectJournal(name) {
  selectedJournal = name;
  const jdata = DATA.j[name];
  const years = YEARS.filter(y => jdata.y[y]);
  selectedYear = years[years.length - 1] || null;
  renderJournalList();
  renderDashboard();
}

function selectYear(y) {
  selectedYear = y;
  renderYearContent();
}

function togglePanel(id) {
  document.getElementById(id)?.classList.toggle('collapsed');
}

function destroyCharts() {
  Object.values(charts).forEach(c => { try { c.destroy(); } catch(e){} });
  charts = {};
}

function renderDashboard() {
  if (!selectedJournal) return;
  destroyCharts();
  const jdata = DATA.j[selectedJournal];
  const years = YEARS.filter(y => jdata.y[y]);
  const main = document.getElementById('main');

  main.innerHTML = `
    <div class="journal-header">
      <div class="journal-title">${selectedJournal}</div>
      <div class="journal-publisher">${jdata.pub || '<span style="opacity:0.5">Publisher not matched</span>'}${jdata.pub ? ' · ' + getPublisherGroup(jdata.pub) : ''}</div>
    </div>

    <div class="year-tabs" id="yearTabs">
      ${years.map(y => `<button class="year-tab${y===selectedYear?' active':''}" onclick="selectYear('${y}')">${y}</button>`).join('')}
    </div>

    <div id="heroRti"></div>

    <div class="detail-panel" id="panelTrend">
      <button type="button" class="panel-toggle" onclick="togglePanel('panelTrend')">
        <span class="panel-toggle-title">RTI Score — Year on Year</span>
        <span class="panel-chevron">▼</span>
      </button>
      <div class="panel-body">
        <div class="chart-wrap"><canvas id="trendChart"></canvas></div>
      </div>
    </div>

    <div class="detail-panel" id="panelStudy">
      <button type="button" class="panel-toggle" onclick="togglePanel('panelStudy')">
        <span class="panel-toggle-title">Study Design Reporting · <span id="radarYear"></span></span>
        <span class="panel-chevron">▼</span>
      </button>
      <div class="panel-body">
        <div class="chart-wrap"><canvas id="radarChart"></canvas></div>
      </div>
    </div>

    <div class="detail-panel" id="panelResource">
      <button type="button" class="panel-toggle" onclick="togglePanel('panelResource')">
        <span class="panel-toggle-title">Research Resource Findability · <span id="resYear"></span></span>
        <span class="panel-chevron">▼</span>
      </button>
      <div class="panel-body">
        <div class="resource-grid" id="resourceGrid"></div>
      </div>
    </div>
  `;

  const trendData = years.map(y => jdata.y[y]?.r ?? null);
  charts.trend = new Chart(document.getElementById('trendChart').getContext('2d'), {
    type: 'line',
    data: {
      labels: years,
      datasets: [{
        label: 'RTI',
        data: trendData,
        borderColor: BLUE,
        backgroundColor: BLUE_DIM,
        tension: 0.35,
        pointRadius: 5,
        pointBackgroundColor: BLUE,
        pointBorderColor: '#0D1B3E',
        pointBorderWidth: 2,
        fill: true,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#132348',
          borderColor: BLUE,
          borderWidth: 1,
          callbacks: { label: ctx => `RTI: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(2) : '—'}` }
        }
      },
      scales: {
        x: { ticks: { color: MUTED, font:{size:11} }, grid: { color: BLUE_GRID } },
        y: { min:0, max:10, ticks: { color: MUTED, font:{size:11} }, grid: { color: BLUE_GRID } }
      }
    }
  });

  renderYearContent();
}

function renderYearContent() {
  if (!selectedJournal || !selectedYear) return;
  const jdata = DATA.j[selectedJournal];
  const yd = jdata.y[selectedYear] || {};

  document.querySelectorAll('.year-tab').forEach(btn => {
    btn.classList.toggle('active', btn.textContent === selectedYear);
  });

  document.getElementById('heroRti').innerHTML = `
    <div class="hero-rti">
      <div class="hero-rti-score">
        <div class="hero-rti-value">${yd.r != null ? yd.r.toFixed(1) : '—'}</div>
        <div class="hero-rti-max">/ 10</div>
      </div>
      <div class="hero-rti-meta">
        <div class="hero-rti-label">Rigor &amp; Transparency Index</div>
        <div class="hero-rti-title">${selectedYear} · ${yd.n != null ? yd.n.toLocaleString() + ' papers analysed' : 'No papers'}</div>
        <div class="hero-rti-sub">Primary SciScore metric for editorial and sales conversations</div>
        <div class="hero-kpis">
          <div class="hero-kpi"><strong>${pct(yd.sex)}</strong>Sex of subjects</div>
          <div class="hero-kpi"><strong>${pct(yd.rand)}</strong>Randomization</div>
          <div class="hero-kpi"><strong>${pct(yd.ab)}</strong>Antibodies w/ RRID</div>
          <div class="hero-kpi"><strong>${pct(yd.tool)}</strong>Software tools</div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('radarYear').textContent = selectedYear;
  document.getElementById('resYear').textContent = selectedYear;

  if (charts.radar) { charts.radar.destroy(); }
  const radarLabels = ['Sex of subjects', 'Power analysis', 'Randomization', 'Blinding', 'IRB / Ethics', 'IACUC'];
  const radarVals = [yd.sex, yd.pwr, yd.rand, yd.blind, yd.irb, yd.iacuc]
    .map(v => v != null ? Math.round(v * 100) : 0);
  charts.radar = new Chart(document.getElementById('radarChart').getContext('2d'), {
    type: 'radar',
    data: {
      labels: radarLabels,
      datasets: [{
        label: selectedYear,
        data: radarVals,
        borderColor: BLUE,
        backgroundColor: BLUE_DIM,
        pointBackgroundColor: BLUE,
        pointBorderColor: '#0D1B3E',
        pointBorderWidth: 2,
        pointRadius: 4,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#132348',
          borderColor: BLUE,
          borderWidth: 1,
          callbacks: { label: ctx => `${ctx.label}: ${ctx.raw}%` }
        }
      },
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { color: MUTED, font:{size:10}, stepSize:25, backdropColor:'transparent' },
          grid: { color: BLUE_GRID },
          pointLabels: { color: MUTED, font:{size:11} },
          angleLines: { color: 'rgba(41,171,226,0.15)' }
        }
      }
    }
  });

  const resources = [
    { name: 'Antibodies',         val: yd.ab,   n: yd.abn },
    { name: 'Organisms / models', val: yd.org,  n: yd.orgn },
    { name: 'Cell lines',         val: yd.cl,   n: yd.cln },
    { name: 'Tools / Software',   val: yd.tool, n: yd.tooln },
  ];
  document.getElementById('resourceGrid').innerHTML = resources.map(r => {
    const p = r.val != null ? Math.round(r.val * 100) : null;
    return `<div class="resource-row">
      <div class="res-name">${r.name}</div>
      <div class="bar-bg"><div class="bar-fill${p != null && p >= 60 ? ' strong' : ''}" style="width:${p ?? 0}%"></div></div>
      <div class="res-pct">${p != null ? p + '%' : '—'}</div>
    </div>`;
  }).join('');
}

function exportScope() {
  const pub = pubSelect.value;
  const grp = groupSelect.value;
  if (pub) return { label: pub, journals: (DATA.p[pub] || []).filter(j => DATA.j[j]) };
  if (grp) {
    const journals = [...new Set((GROUPS[grp] || []).flatMap(p => DATA.p[p] || []))].filter(j => DATA.j[j]);
    return { label: grp, journals };
  }
  return null;
}

function showExportBtn() {
  const btn = document.getElementById('exportBtn');
  if (btn) btn.classList.toggle('visible', !!exportScope());
}

groupSelect.addEventListener('change', () => { populatePublishers(); renderJournalList(); showExportBtn(); });
pubSelect.addEventListener('change', () => { renderJournalList(); showExportBtn(); });
document.getElementById('journalSearch').addEventListener('input', renderJournalList);

populateGroups();
populatePublishers();
renderJournalList();

function loadScript(url) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = url;
    s.onload = resolve;
    s.onerror = () => reject(new Error('Failed to load ' + url));
    document.head.appendChild(s);
  });
}

async function ensurePptxGenJS() {
  if (window.PptxGenJS) return;
  const cdns = [
    'https://cdn.jsdelivr.net/npm/pptxgenjs@3.12.0/dist/pptxgen.bundle.js',
    'https://unpkg.com/pptxgenjs@3.12.0/dist/pptxgen.bundle.js'
  ];
  for (const url of cdns) {
    try {
      await loadScript(url);
      if (window.PptxGenJS) return;
    } catch (e) { /* try next CDN */ }
  }
  throw new Error('Could not load PptxGenJS. Check your network connection and try again.');
}

async function generatePPTX() {
  const scope = exportScope();
  if (!scope) return;
  const { label, journals } = scope;
  const btn = document.getElementById('exportBtn');
  const btnLabel = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Loading…';

  try {
    await ensurePptxGenJS();
  } catch (e) {
    alert('Export failed: ' + e.message);
    btn.disabled = false;
    btn.textContent = btnLabel;
    return;
  }

  btn.textContent = 'Generating…';

  try {
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';

    const BLUE_C = '29ABE2', NAVY = '0D1B3E', WHITE = 'FFFFFF';
    const W = 13.33, H = 7.5;

    const s0 = pptx.addSlide();
    s0.background = { color: NAVY };
    s0.addShape(pptx.ShapeType.rect, { x:0, y:H-0.15, w:W, h:0.15, fill:{color:BLUE_C}, line:{type:'none'} });
    s0.addText(label, { x:1, y:2.0, w:W-2, h:1.4, fontSize:34, bold:true, color:WHITE, fontFace:'Segoe UI' });
    s0.addText('SciScore Journal Intelligence Report', { x:1, y:3.3, w:W-2, h:0.6, fontSize:18, color:BLUE_C, fontFace:'Segoe UI' });
    s0.addText(`${journals.length} journal${journals.length!==1?'s':''} analysed  ·  ${new Date().getFullYear()}`, { x:1, y:3.95, w:W-2, h:0.4, fontSize:13, color:'A8C8E0', fontFace:'Segoe UI' });
    s0.addText('Powered by SciScore · sciscore.com', { x:W-4, y:H-0.6, w:3.5, h:0.35, fontSize:9, color:'5CC8F0', align:'right', fontFace:'Segoe UI' });

    const latestYr = j => Object.keys(DATA.j[j].y||{}).map(Number).sort((a,b)=>b-a)[0];
    const latestD  = j => { const y=latestYr(j); return y ? DATA.j[j].y[y] : null; };

    journals
      .sort((a,b) => (latestD(b)?.r||0) - (latestD(a)?.r||0))
      .forEach(jname => {
        const jdata = DATA.j[jname]; if(!jdata) return;
        const yr = latestYr(jname); if(!yr) return;
        const yd = jdata.y[yr]; if(!yd) return;

        const sl = pptx.addSlide();
        sl.background = { color: WHITE };

        sl.addShape(pptx.ShapeType.rect, { x:0,y:0,w:W,h:1.1, fill:{color:NAVY}, line:{type:'none'} });
        sl.addShape(pptx.ShapeType.rect, { x:0,y:1.1,w:W,h:0.06, fill:{color:BLUE_C}, line:{type:'none'} });
        sl.addText(jname, { x:0.35,y:0.12,w:W-2.5,h:0.86, fontSize:17, bold:true, color:WHITE, fontFace:'Segoe UI', valign:'middle' });

        const rti = yd.r!=null ? yd.r.toFixed(1) : '—';
        sl.addShape(pptx.ShapeType.rect, { x:W-2.15,y:0.16,w:1.8,h:0.78, fill:{color:BLUE_C}, line:{type:'none'}, rectRadius:0.07 });
        sl.addText(`RTI  ${rti}/10`, { x:W-2.15,y:0.16,w:1.8,h:0.78, fontSize:14, bold:true, color:NAVY, fontFace:'Segoe UI', align:'center', valign:'middle' });

        sl.addText(`${yd.n||0} papers · ${yr}`, { x:0.35,y:1.2,w:5,h:0.3, fontSize:9, color:'777777', fontFace:'Segoe UI' });

        sl.addText('STUDY DESIGN', { x:0.35,y:1.6,w:5.8,h:0.28, fontSize:8.5, bold:true, color:BLUE_C, fontFace:'Segoe UI', charSpacing:1.5 });

        const sdRows = [
          {label:'Sex Balance',  val:yd.sex},
          {label:'Power Analysis',val:yd.pwr},
          {label:'Randomization', val:yd.rand},
          {label:'Blinding',      val:yd.blind},
          {label:'IRB Approval',  val:yd.irb},
          {label:'IACUC',         val:yd.iacuc},
        ];
        sdRows.forEach((m,i) => {
          const col = i<3?0:1, row=i%3;
          const x=0.35+col*3.0, y=1.96+row*0.72;
          const pctV=m.val!=null ? Math.round(m.val*100) : null;
          const bw=2.1, fw=pctV!=null?bw*(pctV/100):0;
          sl.addText(m.label, {x,y,w:2.8,h:0.22,fontSize:9.5,color:'444444',fontFace:'Segoe UI'});
          sl.addShape(pptx.ShapeType.rect, {x,y:y+0.24,w:bw,h:0.18, fill:{color:'DFF0F7'}, line:{type:'none'}});
          if(fw>0) sl.addShape(pptx.ShapeType.rect, {x,y:y+0.24,w:fw,h:0.18, fill:{color:pctV>=60?'5CC8F0':BLUE_C}, line:{type:'none'}});
          sl.addText(pctV!=null?pctV+'%':'—', {x:x+bw+0.09,y:y+0.22,w:0.45,h:0.22,fontSize:9.5,bold:true,color:NAVY,fontFace:'Segoe UI'});
        });

        sl.addShape(pptx.ShapeType.rect, {x:6.4,y:1.55,w:0.03,h:4.1, fill:{color:'D0E4EE'}, line:{type:'none'}});

        sl.addText('RESOURCE FINDABILITY', {x:6.75,y:1.6,w:6,h:0.28,fontSize:8.5,bold:true,color:BLUE_C, fontFace:'Segoe UI',charSpacing:1.5});

        const resRows = [
          {label:'Antibody RRIDs', val:yd.ab,  n:yd.abn},
          {label:'Organism RRIDs', val:yd.org, n:yd.orgn},
          {label:'Cell Line RRIDs',val:yd.cl,  n:yd.cln},
          {label:'Software Tools', val:yd.tool,n:yd.tooln},
        ];
        resRows.forEach((m,i) => {
          const x=6.75, y=1.96+i*0.9;
          const pctV=m.val!=null?Math.round(m.val*100):null;
          const bw=5.2, fw=pctV!=null?bw*Math.min(pctV/100,1):0;
          const nLabel = m.n!=null ? ` (${m.n} detected)` : '';
          sl.addText(m.label+nLabel, {x,y,w:5.5,h:0.26,fontSize:10,color:'333333',fontFace:'Segoe UI',bold:true});
          sl.addShape(pptx.ShapeType.rect,{x,y:y+0.3,w:bw,h:0.26, fill:{color:'DFF0F7'},line:{type:'none'}});
          if(fw>0) sl.addShape(pptx.ShapeType.rect,{x,y:y+0.3,w:fw,h:0.26, fill:{color:pctV>=60?'5CC8F0':BLUE_C},line:{type:'none'}});
          sl.addText(pctV!=null?pctV+'%':'—',{x:x+bw+0.1,y:y+0.28,w:0.5,h:0.26,fontSize:11,bold:true,color:NAVY,fontFace:'Segoe UI'});
        });

        sl.addShape(pptx.ShapeType.rect,{x:0,y:H-0.32,w:W,h:0.32,fill:{color:'F0F5F8'},line:{type:'none'}});
        sl.addText('SciScore Journal Intelligence · sciscore.com',{x:0.35,y:H-0.29,w:6,h:0.24,fontSize:7.5,color:'999999',fontFace:'Segoe UI'});
        sl.addText(`${label}`,{x:W-5,y:H-0.29,w:4.6,h:0.24,fontSize:7.5,color:'999999',fontFace:'Segoe UI',align:'right'});
      });

    const fname = `SciScore_${label.replace(/[^a-z0-9]/gi,'_')}_Report.pptx`;
    await pptx.writeFile({ fileName: fname });
    btn.disabled = false;
    btn.textContent = btnLabel;
  } catch (e) {
    console.error(e);
    alert('Export failed: ' + e.message);
    btn.disabled = false;
    btn.textContent = btnLabel;
  }
}
'''


def main():
    content = HTML.read_text(encoding="utf-8")
    group_map = GROUP_MAP_JS.read_text(encoding="utf-8").strip()

    # CSS
    content = content.replace("  .export-btn:disabled { opacity: 0.5; cursor: default; }\n</style>",
                              "  .export-btn:disabled { opacity: 0.5; cursor: default; }\n" + EXTRA_CSS + "</style>")

    # Sidebar
    old_sidebar = """    <div class="sidebar-section">
      <div class="sidebar-label">Publisher</div>
      <select id="publisherSelect"><option value="">All publishers</option></select>
    </div>
    <div class="sidebar-section">
      <button class="export-btn" id="exportBtn" onclick="generatePPTX()">&#9654; Export Publisher Report</button>
    </div>"""
    content = content.replace(old_sidebar, SIDEBAR_HTML)

    # JS: replace from const YEARS through end of generatePPTX
    content = re.sub(
        r'\nconst YEARS = \[.*?</script>',
        '\n' + group_map + '\n\n' + NEW_JS.strip() + '\n\n</script>',
        content,
        count=1,
        flags=re.DOTALL,
    )

    HTML.write_text(content, encoding="utf-8")
    print(f"Patched {HTML} ({len(content)} bytes)")


if __name__ == "__main__":
    main()

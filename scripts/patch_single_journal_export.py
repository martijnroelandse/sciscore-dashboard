#!/usr/bin/env python3
"""Patch SciScore_journal_dashboard.html for single-journal PPTX export."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SciScore_journal_dashboard.html"

SELECT_JOURNAL = """function selectJournal(name) {
  selectedJournal = name;
  compareTouched = false;
  const jdata = DATA.j[name];
  const years = YEARS.filter(y => jdata.y[y]);
  selectedYear = years[years.length - 1] || null;
  renderJournalList();
  showExportBtn();
  renderMain();
}"""

BACK_TO_PUBLISHER = """function backToPublisher() {
  selectedJournal = null;
  compareTouched = false;
  const scope = publisherScope();
  selectedYear = scope ? latestYearForJournals(scope.journals) : null;
  renderJournalList();
  showExportBtn();
  renderMain();
}"""

EXPORT_SCOPE = """function exportScope() {
  if (selectedJournal && DATA.j[selectedJournal]) {
    const pub = pubSelect.value;
    const grp = groupSelect.value;
    const parentLabel = pub || grp || '';
    return { label: selectedJournal, journals: [selectedJournal], singleJournal: true, parentLabel };
  }
  const pub = pubSelect.value;
  const grp = groupSelect.value;
  if (pub) return { label: pub, journals: (DATA.p[pub] || []).filter(j => DATA.j[j]) };
  if (grp) {
    const journals = [...new Set((GROUPS[grp] || []).flatMap(p => DATA.p[p] || []))].filter(j => DATA.j[j]);
    return { label: grp, journals };
  }
  return null;
}"""

SHOW_EXPORT_BTN = """function showExportBtn() {
  const btn = document.getElementById('exportBtn');
  const scope = exportScope();
  if (!btn) return;
  btn.classList.toggle('visible', !!scope);
  if (scope) {
    btn.innerHTML = scope.singleJournal
      ? '&#9654; Export Journal Report'
      : '&#9654; Export Report';
  }
}"""

GENERATE_PPTX = r"""async function generatePPTX() {
  const scope = exportScope();
  if (!scope) return;
  const { label, journals, singleJournal, parentLabel } = scope;
  const btn = document.getElementById('exportBtn');
  const btnLabel = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Loading…';

  try {
    await ensureBrandAssets();
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
    const theme = setupPptxBranding(pptx);

    const { BLUE, NAVY, WHITE, W, H, face } = theme;
    const s0 = pptx.addSlide({ masterName: 'SCISCORE_TITLE' });
    const titleSize = label.length > 45 ? 26 : label.length > 30 ? 30 : 34;
    s0.addText(pptxTrunc(label, 70), { x:1, y:2.0, w:W-2, h:1.4, fontSize:titleSize, bold:true, color:WHITE, fontFace:face });
    s0.addText('SciScore Journal Intelligence Report', { x:1, y:3.3, w:W-2, h:0.6, fontSize:18, color:BLUE, fontFace:face });
    if (singleJournal) {
      const sub = parentLabel ? `${parentLabel}  ·  ${new Date().getFullYear()}` : `${new Date().getFullYear()}`;
      s0.addText(sub, { x:1, y:3.95, w:W-2, h:0.4, fontSize:13, color:'A8C8E0', fontFace:face });
    } else {
      s0.addText(`${journals.length} journal${journals.length!==1?'s':''} analysed  ·  ${new Date().getFullYear()}`, { x:1, y:3.95, w:W-2, h:0.4, fontSize:13, color:'A8C8E0', fontFace:face });
    }
    pptxFooterBranding(s0, theme, { onDark: true });

    if (!singleJournal) pptxAddOverviewSlides(pptx, label, journals, theme);

    const latestYr = j => Object.keys(DATA.j[j].y||{}).map(Number).sort((a,b)=>b-a)[0];
    const latestD  = j => { const y=latestYr(j); return y ? DATA.j[j].y[y] : null; };
    const detailYr = jname => (singleJournal && jname === selectedJournal && selectedYear) ? selectedYear : latestYr(jname);

    journals
      .sort((a,b) => (latestD(b)?.r||0) - (latestD(a)?.r||0))
      .forEach(jname => {
        const jdata = DATA.j[jname]; if(!jdata) return;
        const yr = detailYr(jname); if(!yr) return;
        const yd = jdata.y[yr]; if(!yd) return;
        pptxAddJournalTimelineSlide(pptx, jname, label, theme);
        pptxAddJournalDetailSlide(pptx, jname, label, yr, yd, theme);
      });

    const suffix = singleJournal ? '_Journal_Report' : '_Report';
    const fname = `SciScore_${label.replace(/[^a-z0-9]/gi,'_')}${suffix}.pptx`;
    await pptx.writeFile({ fileName: fname });
    btn.disabled = false;
    btn.textContent = btnLabel;
  } catch (e) {
    console.error(e);
    alert('Export failed: ' + e.message);
    btn.disabled = false;
    btn.textContent = btnLabel;
  }
}"""


def replace_function(content: str, name: str, new_body: str) -> str:
    pattern = rf"function {name}\([^)]*\) \{{.*?\n\}}"
    if name == "generatePPTX":
        pattern = r"async function generatePPTX\(\) \{.*?\n\}"
    result, n = re.subn(pattern, new_body, content, count=1, flags=re.DOTALL)
    if n != 1:
        raise RuntimeError(f"Failed to replace {name} (matched {n} times)")
    return result


def main():
    content = HTML.read_text(encoding="utf-8")
    content = replace_function(content, "selectJournal", SELECT_JOURNAL)
    content = replace_function(content, "backToPublisher", BACK_TO_PUBLISHER)
    content = replace_function(content, "exportScope", EXPORT_SCOPE)
    content = replace_function(content, "showExportBtn", SHOW_EXPORT_BTN)
    content = replace_function(content, "generatePPTX", GENERATE_PPTX)
    HTML.write_text(content, encoding="utf-8")
    print(f"Patched {HTML} for single-journal export")


if __name__ == "__main__":
    main()

// Token-path explorer: the three views (flow graph, swimlane timeline, die replay) for one design, on one shared
// replay clock, with the provenance banner and the per-stage shares.  Mount API: see README.md.
import { P, h, CSS, injectCSS, Clock, fmtCyc, fmtUs, fmtPct, GRADE, detail, CRIT, PHASE, HW } from './core.js';
import { mountFlow } from './flow.js';
import { mountGantt } from './gantt.js';
import { DieReplay } from './overlay.js';
import { attachCoverage, coverageVersion, COV, saveCov, GAPS, COL, covLevel } from '/explorer/coverage/gaps.js';

export const DESIGNS = [
  { id: 'qwen_rom', label: 'Qwen ROM', die: 'qwen_r21b' },
  { id: 'ds_rom', label: 'DeepSeek ROM (S81 array)', die: 's81_layer_r3' },
  { id: 'hbm_ds', label: 'HBM accelerator', die: 'hbm_r25' },
];

/** Default geometry sources, tried in order: the Chip Explorer die export (same instance names as /explorer's die
 *  map), then the snapshot the export tool writes beside the data. */
export function defaultGeometry(base) {
  return (design) => {
    const d = DESIGNS.find((x) => x.id === design);
    return [d && d.die ? `/api/explorer/geom?die=${encodeURIComponent(d.die)}` : null, `${base}geo_${design}.json`].filter(Boolean);
  };
}

const T_CSS = `
.tp-x{display:flex;flex-direction:column;gap:12px;min-width:0;overflow-wrap:anywhere}
.tp-x .bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.tp-x .tab{background:#0b1020;color:#c3cbe0;border:1px solid #1b2540;border-radius:999px;padding:5px 12px;font:600 12px Inter,system-ui,sans-serif;cursor:pointer}
.tp-x .tab[aria-pressed=true]{border-color:${CRIT};color:#e8eefc;background:#10204a}
.tp-x .panel{background:linear-gradient(180deg,#0f1629,#0b1020);border:1px solid #1b2540;border-radius:14px;padding:12px 14px;min-width:0}
.tp-x .pt{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap;color:#8a97b8;font-size:11px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
.tp-x .pt b{color:#e8eefc;text-transform:none;letter-spacing:.02em;font-size:12.5px}
.tp-x .hero{display:flex;gap:6px 22px;flex-wrap:wrap;align-items:baseline}
.tp-x .hero .big{font:800 30px Inter,system-ui,sans-serif;color:#e8eefc;font-variant-numeric:tabular-nums}
.tp-x .hero .u{color:#8a97b8;font-size:13px}
.tp-x .kv{font:12px ui-monospace,Menlo,monospace;color:#8a97b8}.tp-x .kv b{color:#e8eefc;font-weight:600}
.tp-x .grade{display:flex;height:12px;border-radius:4px;overflow:hidden;gap:2px;margin:8px 0 4px;max-width:640px}
.tp-x .gl{display:flex;flex-wrap:wrap;gap:4px 14px;font:11px ui-monospace,Menlo,monospace;color:#8a97b8}
.tp-x .gl i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.tp-x .ctl{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font:12px ui-monospace,Menlo,monospace;color:#8a97b8}
.tp-x .ctl button,.tp-x .ctl select{background:#0b1020;color:#e8eefc;border:1px solid #1b2540;border-radius:7px;padding:4px 9px;font:12px ui-monospace,Menlo,monospace;cursor:pointer}
.tp-x .ctl input[type=range]{flex:1 1 160px;min-width:120px;accent-color:${CRIT}}
.tp-x .crumb a{color:${CRIT};cursor:pointer;text-decoration:none}
.tp-x .two{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:12px}
@media (max-width:900px){.tp-x .two{grid-template-columns:1fr}}
.tp-x table{border-collapse:collapse;width:100%;font:12px ui-monospace,Menlo,monospace}
.tp-x td,.tp-x th{padding:3px 6px;border-bottom:1px solid #1b2540;text-align:left;color:#c3cbe0;font-weight:400}
.tp-x th{color:#8a97b8}.tp-x td.n{text-align:right;font-variant-numeric:tabular-nums}
.tp-x .sbar{height:8px;background:${CRIT};border-radius:2px;opacity:.75}
.tp-x .notes{font-size:12px;color:#8a97b8;line-height:1.45;margin:6px 0 0;padding-left:18px}
.tp-x .legend{display:flex;flex-wrap:wrap;gap:4px 14px;font:11.5px Inter,system-ui,sans-serif;color:#c3cbe0;margin-top:8px}
.tp-x .legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.tp-x .mode{display:inline-flex;border:1px solid #1b2540;border-radius:999px;overflow:hidden;margin-left:auto}
.tp-x .mode button{background:#0b1020;color:#c3cbe0;border:0;padding:5px 14px;font:700 12px Inter,system-ui,sans-serif;cursor:pointer}
.tp-x .mode button[aria-pressed=true]{background:#10204a;color:#e8eefc;box-shadow:inset 0 -2px 0 ${CRIT}}
.tp-x .mode button:disabled{color:#4a5678;cursor:not-allowed}
.tp-x .phb{display:flex;height:22px;border-radius:5px;overflow:hidden;gap:2px;margin:8px 0 4px}
.tp-x .phb div{display:flex;align-items:center;padding:0 6px;font:700 11px ui-monospace,Menlo,monospace;color:#05070d;white-space:nowrap;overflow:hidden;min-width:2px}
.tp-x .acc{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:8px}
.tp-x .acc div{background:#0b1020;border:1px solid #1b2540;border-radius:9px;padding:6px 9px;font:11px ui-monospace,Menlo,monospace;color:#8a97b8}
.tp-x .acc b{display:block;color:#e8eefc;font:700 15px Inter,system-ui,sans-serif;font-variant-numeric:tabular-nums}
.tp-x .arnote{border:1px dashed #2a3a63;border-radius:9px;padding:7px 10px;font-size:12px;color:#c3cbe0;margin-top:8px;line-height:1.4}
.tp-x .covctl{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;margin-top:8px;font:11.5px ui-monospace,Menlo,monospace;color:#8a97b8}
.tp-x .covctl button{background:#0b1020;color:#c3cbe0;border:1px solid #1b2540;border-radius:999px;padding:2px 8px;font:600 11px ui-monospace,Menlo,monospace;cursor:pointer}
.tp-x .covctl button[aria-pressed=true]{color:#e8eefc;background:#10204a}
.tp-x .covctl a{color:${CRIT}}
.tp-x .covsum{margin-top:6px;font:12px ui-monospace,Menlo,monospace;color:#8a97b8}.tp-x .covsum b{font-weight:700}
.tp-x .hatchsw{background:repeating-linear-gradient(45deg,#e66767 0 2px,#2a0f16 2px 5px)!important}
`;

const GRADE_COL = { measured: '#199e70', 'measured+vendor': '#3987e5', apportioned: '#9085e9', priced: '#c98500', modelled: '#e66767', lever: '#d55181', zero: '#4a5678' };

export async function loadRecord(url) { const r = await fetch(url); if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); }

/**
 * mountTokenExplorer(el, {base, design, group, geometryUrl, onState})
 *   base         URL prefix of the data directory (default './data/'): <base><design>.json
 *   design       'qwen_rom' | 'ds_rom' | 'hbm_ds'
 *   group        initial drill group id (null = whole token)
 *   geometryUrl  (design, record) => URL (or list of URLs, tried in order) of the die geometry, or null to hide the
 *                die replay (default: /api/explorer/geom?die=<die of the design>, then <base>geo_<design>.json)
 *   onState      called with {design, group} on every navigation (e.g. to update the URL hash)
 */
export async function mountTokenExplorer(el, opts = {}) {
  injectCSS('tp-css', CSS); injectCSS('tp-x-css', T_CSS);
  const o = Object.assign({ base: './data/', design: 'qwen_rom', group: null, onState: null,
    geometryUrl: defaultGeometry(opts.base || './data/') }, opts);
  const state = { design: o.design, group: o.group, mode: o.mode === 'mtp' ? 'mtp' : 'ar' };
  const cache = {}, gcache = {};
  const clock = new Clock({ seconds: 24 });
  const root = h('div', { class: 'tp-x tp-root' });
  el.replaceChildren(root);
  let views = [];

  let covV = null, covErr = null, covPending = false;
  async function render(keepT = null) {
    views.forEach((v) => v && v.destroy && v.destroy()); views = [];
    clock.pause();
    const arData = cache[state.design] ||= await loadRecord(o.base + state.design + '.json');
    const mtpInfo = arData.mtp || { available: false, reason: 'no MTP record' };
    if (state.mode === 'mtp' && !mtpInfo.available) state.mode = 'ar';
    const data = state.mode === 'mtp' ? (cache[state.design + '_mtp'] ||= await loadRecord(o.base + mtpInfo.file)) : arData;
    const mtp = state.mode === 'mtp';
    // coverage: map every operator onto the coverage rows of its target (live from the ledgers; /api/coverage/token)
    const covKey = state.design + (mtp ? '_mtp' : '');
    if (!data._cov || data._cov.v !== covV) {
      try { const c = await attachCoverage(data, covKey); covV = c.v; covErr = null; } catch (e) { covErr = e.message; }
    }
    const p = P(data);
    if (state.group && !p.groups[state.group]) state.group = null;
    o.onState && o.onState({ ...state });
    const g = state.group ? p.groups[state.group] : null;
    const t0 = g ? g.start : 0, t1 = g ? g.end : data.totals.cycles;
    clock.scope(t0, t1, g ? 12 : 24);
    // tabs
    const modeSw = h('div', { class: 'mode', role: 'group', 'aria-label': 'decode mode' },
      h('button', { 'aria-pressed': String(!mtp), onclick: () => { if (mtp) { state.mode = 'ar'; state.group = null; render(); } } }, 'AR'),
      h('button', { 'aria-pressed': String(mtp), title: mtpInfo.available ? 'MTP: one speculative verify step (draft → verify → accept)' : mtpInfo.reason,
        ...(mtpInfo.available ? {} : { disabled: '' }),
        onclick: () => { if (!mtp && mtpInfo.available) { state.mode = 'mtp'; state.group = null; render(); } } }, 'MTP'));
    const tabs = h('div', { class: 'bar', role: 'group', 'aria-label': 'design' },
      ...DESIGNS.map((d) => h('button', { class: 'tab', 'aria-pressed': String(d.id === state.design), onclick: () => { state.design = d.id; state.group = null; render(); } }, d.label)), modeSw);
    // provenance banner
    const hd = data.headline, tt = data.totals;
    const grades = Object.entries(tt.by_grade);
    const gpos = grades.filter(([, v]) => v > 0), gsum = gpos.reduce((a, [, v]) => a + v, 0);
    const banner = h('div', { class: 'panel' },
      h('div', { class: 'pt' }, h('b', {}, data.title), h('span', {}, mtp ? 'one MTP verify step · critical path' : 'one decode token · critical path')),
      h('div', { class: 'hero' },
        h('span', {}, h('span', { class: 'big' }, hd.tok_s.toLocaleString(undefined, { minimumFractionDigits: 1 })), h('span', { class: 'u' }, mtp ? ` tok/s per user (MTP, tau ${tt.tau})` : ' tok/s per user (AR)')),
        mtp ? h('span', { class: 'kv' }, 'step ', h('b', {}, fmtCyc(tt.cycles)), ' = ', h('b', {}, fmtUs(tt.cycles)), ' · per accepted token ', h('b', {}, fmtCyc(tt.per_accepted_cycles)))
          : h('span', { class: 'kv' }, 'token ', h('b', {}, fmtCyc(tt.cycles)), ' = ', h('b', {}, fmtUs(tt.cycles))),
        h('span', { class: 'kv' }, 'status ', h('b', {}, hd.status))),
      mtp ? mtpPanel(data) : (mtpInfo.available ? h('div', { class: 'kv', style: 'margin-top:6px' }, 'MTP: ', h('b', {}, `${mtpInfo.tok_s.toLocaleString(undefined, { minimumFractionDigits: 1 })} tok/s`), ` at tau ${mtpInfo.tau} (switch to MTP above for the speculative step)`)
        : h('div', { class: 'arnote' }, h('b', {}, 'AR only. '), mtpInfo.reason || '', mtpInfo.source ? h('div', { class: 'tp-src' }, mtpInfo.source) : null)),
      h('div', { class: 'kv', style: 'margin-top:6px' }, 'reproduces: ', h('b', {}, tt.reproduces)),
      h('div', { class: 'kv', style: 'margin-top:3px' }, 'basis: ', hd.basis),
      h('div', { class: 'kv', style: 'margin-top:3px' }, 'source: ', hd.source),
      h('div', { class: 'grade', role: 'img', 'aria-label': 'cycles by provenance' },
        ...gpos.map(([k, v]) => h('div', { style: `flex:${v / gsum};background:${GRADE_COL[k] || '#888'}`, title: `${GRADE[k] || k}: ${fmtCyc(v)}` }))),
      h('div', { class: 'gl' }, ...grades.map(([k, v]) => h('span', {}, h('i', { style: `background:${GRADE_COL[k] || '#888'}` }), `${GRADE[k] || k} ${fmtCyc(v)} (${fmtPct(Math.abs(v) / tt.cycles)})`))),
      covSummary(data, covErr));
    // controls
    const slider = h('input', { type: 'range', min: 0, max: 1000, value: 0, 'aria-label': 'replay position' });
    const tread = h('span', {});
    const playB = h('button', { onclick: () => clock.toggle() }, '▶ play');
    const speed = h('select', { 'aria-label': 'replay length', onchange: () => { clock.seconds = Number(speed.value); } },
      ...[6, 12, 24, 60, 120].map((s) => h('option', { value: s, ...(s === clock.seconds ? { selected: '' } : {}) }, `${s} s replay`)));
    slider.addEventListener('input', () => clock.seek(t0 + (t1 - t0) * slider.value / 1000));
    const crumb = h('span', { class: 'crumb' }, g ? [h('a', { onclick: () => { state.group = null; render(); } }, 'whole token'), ' ▸ ', h('b', {}, g.label)] : h('b', {}, 'whole token (click a stage to open it)'));
    const ctl = h('div', { class: 'ctl' }, playB, speed, slider, tread);
    clock.subs.clear();
    clock.on((t) => {
      slider.value = String(Math.round((t - t0) / Math.max(1, t1 - t0) * 1000));
      tread.textContent = `${Math.round(t).toLocaleString()} cyc · ${(t / 1.2e3).toFixed(2)} µs`;
      playB.textContent = clock.playing ? '❚❚ pause' : '▶ play';
    });
    // class legend
    const legend = h('div', { class: 'legend' }, ...data.classes.filter((c) => data.nodes.some((n) => n.cls === c.id)).map((c) => h('span', {}, h('i', { style: `background:${p.cls[c.id].color}` }), c.label)),
      h('span', {}, h('i', { style: `background:none;border:2px solid ${CRIT}` }), 'critical path'),
      ...(mtp ? [h('span', {}, h('i', { class: 'hatchsw' }), 'not built (no closed hardware)'), h('span', {}, h('i', { style: 'background:none;border:1.5px dashed #c3cbe0' }), 'block closed, not integrated'),
        ...Object.entries(PHASE).map(([k, v]) => h('span', {}, h('i', { style: `background:${v.color};height:4px;vertical-align:2px` }), v.label))] : []));
    const covCtl = h('div', { class: 'covctl', role: 'group', 'aria-label': 'coverage overlay' },
      h('label', {}, h('input', { type: 'checkbox', ...(COV.on ? { checked: '' } : {}), onchange: (e) => { COV.on = e.target.checked; saveCov(); rerender(); } }), ' coverage gaps'),
      h('span', {}, h('i', { style: `display:inline-block;width:10px;height:10px;border-radius:50%;border:2px solid ${COL.uncovered};vertical-align:-2px;margin-right:4px` }), 'no HW on a die'),
      h('span', {}, h('i', { style: `display:inline-block;width:10px;height:10px;border-radius:50%;border:2px dashed ${COL.gap};vertical-align:-2px;margin-right:4px` }), 'other gap'),
      ...Object.entries(GAPS).map(([k, g]) => h('button', { 'aria-pressed': String(COV.classes.has(k)), title: g.label, style: COV.classes.has(k) ? `border-color:${g.color}` : '',
        onclick: () => { COV.classes.has(k) ? COV.classes.delete(k) : COV.classes.add(k); saveCov(); rerender(); } }, g.tag)),
      data._cov ? h('a', { href: `/explorer/coverage/#t=${data._cov.target}` }, `${data._cov.target} matrix →`) : null);
    legend.append(covCtl);
    // panels
    const flowP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, g ? `Operators of ${g.label}` : mtp ? 'Flow graph of one MTP step: draft → verify → accept' : 'Flow graph by stage'), crumb), h('div', { class: 'fl' }), legend);
    const ganttP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Timeline by element class'), h('span', {}, 'critical chain = cyan line · dbl-click to seek')), h('div', { class: 'gn' }));
    const sel = h('div', { class: 'kv' }, 'Click an operator for its detail and element cards.');
    const dieBox = h('div', {});
    const dieP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Floorplan replay'), h('span', {}, 'lit = instances of the running operators · line = data moving')), dieBox);
    const selP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Selected operator')), sel);
    const shareP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, mtp ? 'Share of the MTP step' : 'Share of the token latency'), h('span', {}, 'by stage and by element class')), shareTables(data, p, (gid) => { state.group = gid; render(); }));
    const notes = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'How the numbers are built')), h('ul', { class: 'notes' }, ...data.notes.map((n) => h('li', {}, n))));
    const parts = [tabs, banner, h('div', { class: 'panel' }, ctl), flowP, ganttP, h('div', { class: 'two' }, dieP, selP)];
    if (mtp) parts.push(hwPanel(data, (n) => { state.group = n.group; render(); }));
    root.replaceChildren(...parts, shareP, notes);
    const onSelect = (n) => { sel.replaceChildren(detail(data, n)); views.forEach((v) => v && v.select && v.select(n.id)); };
    views.push(mountFlow(flowP.querySelector('.fl'), data, { clock, group: state.group, onSelect, onDrill: (gid) => { state.group = gid; render(); } }));
    views.push(mountGantt(ganttP.querySelector('.gn'), data, { clock, range: [t0, t1], onSelect, onZoom: (gid) => { state.group = gid; render(); } }));
    let gurls = o.geometryUrl && o.geometryUrl(state.design, data);
    gurls = gurls ? [].concat(gurls) : [];
    let geo = null, gsrc = null, gerr = [];
    for (const u of gurls) {
      try { geo = gcache[u] ||= await loadRecord(u); gsrc = u; break; } catch (e) { gerr.push(e.message); }
    }
    if (geo) {
      const rp = new DieReplay(dieBox, geo, data, { clock, group: state.group });
      views.push(rp);
      const dd = DESIGNS.find((x) => x.id === state.design);
      const off = data.classes.filter((c) => data.nodes.some((n) => n.cls === c.id) && !rp.classHits(c.id));
      dieBox.append(h('div', { class: 'kv', style: 'margin-top:4px' },
        gsrc.startsWith('/api/') ? ['die map: ', h('a', { class: 'tp-el', href: `/explorer#die=${dd.die}` }, geo.label || dd.die)] : `die map: ${geo.source || gsrc} (snapshot)`,
        off.length ? ` · not on this die: ${off.map((c) => c.label).join(', ')}` : ''));
    } else dieBox.replaceChildren(h('div', { class: 'kv' }, gurls.length ? 'no die geometry: ' + gerr.join('; ') : 'no die geometry mounted'));
    clock.seek(keepT != null && keepT >= t0 && keepT <= t1 ? keepT : t0);
  }
  function rerender() { return render(clock.t); }
  await render();
  // the ledgers change under the view: re-map when /api/coverage/version moves (deferred while the replay plays)
  clock.on(() => { if (covPending && !clock.playing) { covPending = false; rerender(); } });
  setInterval(async () => {
    try {
      const v = await coverageVersion();
      if (v && covV && v !== covV) { covV = v; for (const k in cache) if (cache[k]) cache[k]._cov = null; if (clock.playing) covPending = true; else rerender(); }
    } catch (e) { /* server restart */ }
  }, 30000);
  return { clock, show(design, group = null, mode = state.mode) { state.design = design; state.group = group; state.mode = mode; return render(); }, state };
}

/** banner line: critical cycles on operators whose coverage rows have gaps (under the current overlay filter) */
function covSummary(data, err) {
  if (err) return h('div', { class: 'covsum' }, 'coverage: ', err);
  if (!data._cov) return null;
  let u = 0, g = 0, t = 0;
  for (const n of data.nodes) { if (!n.critical) continue; t += n.cycles; const lv = covLevel(n); if (lv === 'uncovered') u += n.cycles; else if (lv === 'gap') g += n.cycles; }
  return h('div', { class: 'covsum' }, `coverage (${data._cov.target}, live from the ledgers): `,
    h('b', { style: `color:${COL.uncovered}` }, `${fmtPct(u / t)} no HW on a die`), ' · ', h('b', { style: `color:${COL.gap}` }, `${fmtPct(g / t)} other gaps`),
    ` of the critical cycles · ${COV.on ? 'overlay on' : 'overlay off'}`);
}

function shareTables(data, p, open) {
  const crit = data.groups.filter((g) => g.critical).sort((a, b) => b.share - a.share);
  const top = crit.slice(0, 12), mx = top[0]?.share || 1;
  const t1 = h('table', {}, h('tr', {}, h('th', {}, 'stage / layer'), h('th', {}, 'cycles'), h('th', {}, 'share'), h('th', { style: 'width:30%' }, '')),
    ...top.map((g) => h('tr', { style: 'cursor:pointer', onclick: () => open(g.id) }, h('td', {}, g.label), h('td', { class: 'n' }, fmtCyc(g.cycles)), h('td', { class: 'n' }, fmtPct(g.share)),
      h('td', {}, h('div', { class: 'sbar', style: `width:${(g.share / mx * 100).toFixed(1)}%` })))));
  const cls = data.totals.by_class;
  const t2 = h('table', {}, h('tr', {}, h('th', {}, 'element class'), h('th', {}, 'cycles'), h('th', {}, 'share')),
    ...cls.map((c) => h('tr', {}, h('td', {}, h('span', { class: 'tp-sw', style: `display:inline-block;margin-right:6px;background:${p.cls[c.cls]?.color}` }), p.cls[c.cls]?.label || c.cls),
      h('td', { class: 'n' }, fmtCyc(c.cycles)), h('td', { class: 'n' }, fmtPct(c.share)))));
  return h('div', { class: 'two' }, h('div', {}, t1, h('div', { class: 'kv', style: 'margin-top:4px' }, `${crit.length} critical stages; top 12 shown (click to open)`)), t2);
}

/** MTP banner block: the step split into draft / verify / accept, the accepted-token accounting, other BF cases */
function mtpPanel(data) {
  const a = data.accounting, tt = data.totals, ph = data.phases || [];
  const bar = h('div', { class: 'phb', role: 'img', 'aria-label': 'MTP step by phase' },
    ...ph.map((q) => h('div', { style: `flex:${Math.max(q.share, 0.004)};background:${PHASE[q.id]?.color || '#888'}`, title: `${q.label}: ${fmtCyc(q.cycles)} (${fmtPct(q.share)})` },
      q.share > 0.06 ? `${q.label} ${fmtPct(q.share)}` : '')));
  const cell = (big, small) => h('div', {}, h('b', {}, big), small);
  const pa = a.per_accepted_by_phase || {};
  const acc = h('div', { class: 'acc' },
    cell(String(a.tau), `tau: accepted tokens per step (${a.drafted_tokens} drafted, ${a.verified_positions} positions verified)`),
    cell(fmtCyc(tt.cycles), `one step = ${fmtUs(tt.cycles)}`),
    cell(fmtCyc(a.per_accepted_cycles), `per accepted token (step / tau) = ${a.per_accepted_us} µs`),
    cell(`${a.speedup_over_ar.toFixed(2)}×`, `over AR (${fmtCyc(a.ar_token_cycles)} a token)`),
    ...ph.map((q) => cell(fmtCyc(pa[q.id] ?? q.cycles / a.tau), `${q.label} per accepted token`)));
  const hs = data.hw_summary || {};
  const kids = [bar, acc,
    h('div', { class: 'kv', style: 'margin-top:6px' }, 'MTP-only operators: ',
      ...['built', 'partial', 'none'].filter((k) => hs[k]).map((k) => h('span', { class: 'tp-hw tp-hw-' + k, style: 'margin-right:6px' },
        `${k === 'none' ? 'not built' : k === 'partial' ? 'closed, not integrated' : 'built'}: ${hs[k].nodes} ops · ${fmtCyc(hs[k].cycles)}`))),
    h('div', { class: 'tp-src' }, 'tau: ' + a.tau_source)];
  const v = data.mtp_variants;
  if (v) {
    kids.push(h('table', { style: 'margin-top:8px' }, h('tr', {}, h('th', {}, 'BF case'), h('th', {}, 'AR tok/s'), h('th', {}, 'MTP tok/s'), h('th', {}, 'step µs'), h('th', {}, 'draft'), h('th', {}, 'verify: AR pass + 5 × II'), h('th', {}, 'seed/commit')),
      ...Object.values(v).map((x) => h('tr', { title: x.reproduces }, h('td', {}, x.label), h('td', { class: 'n' }, x.AR_tok_s.toLocaleString()), h('td', { class: 'n' }, h('b', {}, x.MTP_tok_s.toLocaleString())),
        h('td', { class: 'n' }, x.step_us), h('td', { class: 'n' }, x.draft_us), h('td', { class: 'n' }, `${x.verify_first_position_us} + 5 × ${x.II_us}`), h('td', { class: 'n' }, x.seed_commit_us)))));
  }
  return h('div', {}, ...kids);
}

/** MTP: every MTP-only operator group with its hardware status (flagged ones first) */
function hwPanel(data, open) {
  const rows = new Map();
  for (const n of data.nodes) {
    if (!n.hw || !n.critical) continue;
    const key = n.hw.status + '|' + n.group + '|' + n.hw.note;
    const r = rows.get(key) || { n, status: n.hw.status, note: n.hw.note, flag: n.flag, group: n.group, cycles: 0, count: 0, phase: n.phase };
    r.cycles += n.cycles; r.count++; rows.set(key, r);
  }
  const order = { none: 0, partial: 1, built: 2 };
  const list = [...rows.values()].sort((a, b) => order[a.status] - order[b.status] || b.cycles - a.cycles);
  const p = P(data);
  return h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Hardware status of the MTP operators'), h('span', {}, 'verify-pass operators are the AR path\'s')),
    h('table', {}, h('tr', {}, h('th', {}, 'status'), h('th', {}, 'phase'), h('th', {}, 'operators'), h('th', {}, 'cycles'), h('th', {}, 'why')),
      ...list.map((r) => h('tr', { style: 'cursor:pointer', onclick: () => open(r.n) },
        h('td', {}, h('span', { class: 'tp-hw tp-hw-' + r.status }, r.status === 'none' ? (r.flag || 'not built') : HW[r.status])),
        h('td', {}, PHASE[r.phase]?.label || r.phase || ''),
        h('td', {}, `${p.groups[r.group]?.label || r.group} (${r.count})`),
        h('td', { class: 'n' }, fmtCyc(r.cycles)),
        h('td', { style: 'font-family:Inter,system-ui,sans-serif;font-size:11.5px;color:#8a97b8' }, r.note)))));
}

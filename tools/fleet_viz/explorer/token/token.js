// Token-path explorer: the three views (flow graph, swimlane timeline, die replay) for one design, on one shared
// replay clock, with the provenance banner and the per-stage shares.  Mount API: see README.md.
import { P, h, CSS, injectCSS, Clock, fmtCyc, fmtUs, fmtPct, GRADE, detail, CRIT } from './core.js';
import { mountFlow } from './flow.js';
import { mountGantt } from './gantt.js';
import { DieReplay } from './overlay.js';

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
  const state = { design: o.design, group: o.group };
  const cache = {}, gcache = {};
  const clock = new Clock({ seconds: 24 });
  const root = h('div', { class: 'tp-x tp-root' });
  el.replaceChildren(root);
  let views = [];

  async function render() {
    views.forEach((v) => v && v.destroy && v.destroy()); views = [];
    clock.pause();
    const data = cache[state.design] ||= P(await loadRecord(o.base + state.design + '.json')) && cache[state.design] || await loadRecord(o.base + state.design + '.json');
    P(data);
    const p = P(data);
    if (state.group && !p.groups[state.group]) state.group = null;
    o.onState && o.onState({ ...state });
    const g = state.group ? p.groups[state.group] : null;
    const t0 = g ? g.start : 0, t1 = g ? g.end : data.totals.cycles;
    clock.scope(t0, t1, g ? 12 : 24);
    // tabs
    const tabs = h('div', { class: 'bar', role: 'group', 'aria-label': 'design' },
      ...DESIGNS.map((d) => h('button', { class: 'tab', 'aria-pressed': String(d.id === state.design), onclick: () => { state.design = d.id; state.group = null; render(); } }, d.label)));
    // provenance banner
    const hd = data.headline, tt = data.totals;
    const grades = Object.entries(tt.by_grade);
    const gpos = grades.filter(([, v]) => v > 0), gsum = gpos.reduce((a, [, v]) => a + v, 0);
    const banner = h('div', { class: 'panel' },
      h('div', { class: 'pt' }, h('b', {}, data.title), h('span', {}, 'one decode token · critical path')),
      h('div', { class: 'hero' },
        h('span', {}, h('span', { class: 'big' }, hd.tok_s.toLocaleString(undefined, { minimumFractionDigits: 1 })), h('span', { class: 'u' }, ' tok/s per user (AR)')),
        h('span', { class: 'kv' }, 'token ', h('b', {}, fmtCyc(tt.cycles)), ' = ', h('b', {}, fmtUs(tt.cycles))),
        h('span', { class: 'kv' }, 'status ', h('b', {}, hd.status))),
      h('div', { class: 'kv', style: 'margin-top:6px' }, 'reproduces: ', h('b', {}, tt.reproduces)),
      h('div', { class: 'kv', style: 'margin-top:3px' }, 'basis: ', hd.basis),
      h('div', { class: 'kv', style: 'margin-top:3px' }, 'source: ', hd.source),
      h('div', { class: 'grade', role: 'img', 'aria-label': 'cycles by provenance' },
        ...gpos.map(([k, v]) => h('div', { style: `flex:${v / gsum};background:${GRADE_COL[k] || '#888'}`, title: `${GRADE[k] || k}: ${fmtCyc(v)}` }))),
      h('div', { class: 'gl' }, ...grades.map(([k, v]) => h('span', {}, h('i', { style: `background:${GRADE_COL[k] || '#888'}` }), `${GRADE[k] || k} ${fmtCyc(v)} (${fmtPct(Math.abs(v) / tt.cycles)})`))));
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
      h('span', {}, h('i', { style: `background:none;border:2px solid ${CRIT}` }), 'critical path'));
    // panels
    const flowP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, g ? `Operators of ${g.label}` : 'Flow graph by stage'), crumb), h('div', { class: 'fl' }), legend);
    const ganttP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Timeline by element class'), h('span', {}, 'critical chain = cyan line · dbl-click to seek')), h('div', { class: 'gn' }));
    const sel = h('div', { class: 'kv' }, 'Click an operator for its detail and element cards.');
    const dieBox = h('div', {});
    const dieP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Floorplan replay'), h('span', {}, 'lit = instances of the running operators · line = data moving')), dieBox);
    const selP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Selected operator')), sel);
    const shareP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Share of the token latency'), h('span', {}, 'by stage and by element class')), shareTables(data, p, (gid) => { state.group = gid; render(); }));
    const notes = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'How the numbers are built')), h('ul', { class: 'notes' }, ...data.notes.map((n) => h('li', {}, n))));
    root.replaceChildren(tabs, banner, h('div', { class: 'panel' }, ctl), flowP, ganttP, h('div', { class: 'two' }, dieP, selP), shareP, notes);
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
    clock.seek(t0);
  }
  await render();
  return { clock, show(design, group = null) { state.design = design; state.group = group; return render(); }, state };
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

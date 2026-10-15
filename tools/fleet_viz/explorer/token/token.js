// Token-path explorer: the three views (flow graph, swimlane timeline, die replay) for one design, on one shared
// replay clock, with the provenance banner and the per-stage shares.  Mount API: see README.md.
import { P, h, CSS, injectCSS, Clock, fmtCyc, fmtUs, fmtPct, GRADE, detail, tip, CRIT, PHASE, HW } from './core.js';
import { mountFlow } from './flow.js';
import { mountGantt } from './gantt.js';
import { mountDataflow } from '/explorer/dataflow/dataflow.js';
import { attachCoverage, coverageVersion, COV, saveCov, GAPS, COL, covLevel } from '/explorer/coverage/gaps.js';

export const DESIGNS = [
  { id: 'qwen_rom', label: 'Qwen ROM', die: 'qwen_r21b' },
  { id: 'ds_rom', label: 'DeepSeek ROM (S81 array)', die: 's81_layer_r3' },
  { id: 'hbm_gen_qwen', label: 'HBM generic die · Qwen3-8B', die: 'hbm_r25gph' },
  { id: 'hbm_gen_ds', label: 'HBM generic die · DeepSeek', die: 'hbm_r25gph' },
];
/** retired design ids -> their replacement (old #design= links keep working) */
export const ALIASES = { hbm_ds: 'hbm_gen_ds', hbm_ds_mtp: 'hbm_gen_ds' };
export const canonDesign = (d) => ALIASES[d] || d;

/** Default geometry sources, tried in order: the Chip Explorer die export (same instance names as /explorer's die
 *  map), then the snapshot the export tool writes beside the data. */
const T_CSS = `
.tp-x{display:flex;flex-direction:column;gap:0;min-width:0;overflow-wrap:anywhere;height:100%;min-height:0}
.tp-x .workspace{display:grid;grid-template-columns:220px minmax(0,1fr);flex:1;min-height:0}
.tp-x .stage-nav{overflow:auto;border-right:1px solid #1b2540;background:#0b1020;padding:8px 0;scrollbar-width:thin}
.tp-x .nav-title{font:700 10px ui-monospace,Menlo,monospace;color:#8a97b8;letter-spacing:.12em;text-transform:uppercase;padding:4px 12px 8px}
.tp-x .stage-nav button{display:flex;align-items:center;gap:5px;width:100%;min-width:0;background:none;border:0;color:#c3cbe0;text-align:left;padding:3px 8px;min-height:24px;cursor:pointer;font:11.5px ui-monospace,Menlo,monospace}
.tp-x .stage-nav button:hover,.tp-x .stage-nav button:focus-visible{background:#16244a;outline:1px solid #2a3a63;outline-offset:-1px}
.tp-x .stage-nav button[aria-selected=true]{background:#16244a;color:#5ee7ff;box-shadow:inset 2px 0 #5ee7ff}
.tp-x .stage-nav .tree-label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.tp-x .stage-nav .tree-arrow{width:10px;flex:none;color:#8a97b8;font-size:9px}
.tp-x .stage-nav button small{margin-left:auto;color:#8a97b8;font:10px ui-monospace,Menlo,monospace;white-space:nowrap;padding-left:4px}
.tp-x .stage-nav .tree-folder{font-family:Inter,system-ui,sans-serif;font-weight:600;color:#8a97b8}
.tp-x .stage-nav [role=group]{margin-left:10px;border-left:1px solid #1b2540}
.tp-x .content{overflow:auto;min-width:0;padding:14px;display:flex;flex-direction:column;gap:14px;scrollbar-width:thin}
.tp-x .toolbar{padding:10px 14px;border-bottom:1px solid #1b2540;background:#070b16}
.tp-x .overview{background:#03050b!important}
.tp-x .scopebar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.tp-x .scopebar button,.tp-x .navback{background:#10204a;color:#5ee7ff;border:1px solid #2a3a63;border-radius:7px;padding:7px 12px;font:600 12px Inter,system-ui,sans-serif;cursor:pointer}
.tp-x .scopebar span{font:12px ui-monospace,Menlo,monospace;color:#8a97b8}
.tp-x .inspector{border-color:#2a3a63!important;scroll-margin-top:14px}
.tp-x .inspector .two{margin-top:12px}
.tp-x .loading-state{display:flex;align-items:center;justify-content:center;gap:12px;min-height:150px;color:#c3cbe0;font:13px Inter,system-ui,sans-serif}
.tp-x .loading-state .spinner{width:24px;height:24px;border:2px solid #253454;border-top-color:#5ee7ff;border-radius:50%;animation:tp-loading-spin .8s linear infinite;flex:none}
.tp-x .loading-state small{display:block;margin-top:5px;color:#8a97b8;font-size:12px}
.tp-x .load-error{color:#e8a0a0}
.tp-x .load-error button{margin-left:12px;background:#16244a;color:#e8eefc;border:1px solid #2a3a63;border-radius:6px;padding:6px 12px;cursor:pointer}
@keyframes tp-loading-spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.tp-x .loading-state .spinner{animation:none;border-top-color:#5ee7ff;border-right-color:#5ee7ff}}
.tp-x .native-audit>summary{cursor:pointer;color:#e8eefc;font:600 12.5px Inter,system-ui,sans-serif;line-height:1.7}
.tp-x .native-audit>summary span{color:#8a97b8;font:11px ui-monospace,Menlo,monospace;margin-left:12px}
.tp-x input:not([type=range]){background:#05070d;color:#e8eefc;border:1px solid #2a3a63;border-radius:6px;padding:8px;box-sizing:border-box}
.tp-x details>summary{cursor:pointer}
.tp-x .evidence>summary{color:#8a97b8;font:12px ui-monospace,Menlo,monospace;padding-top:10px;cursor:pointer}
.tp-x .metricline{display:flex;gap:8px 20px;align-items:baseline;flex-wrap:wrap;margin-bottom:12px}
.tp-x .metricline b{font:700 22px Inter,system-ui,sans-serif;color:#e8eefc}
.tp-x .metricline span{font:11px ui-monospace,Menlo,monospace;color:#8a97b8}
@media(max-width:760px){.tp-x .workspace{grid-template-columns:1fr;grid-template-rows:minmax(70px,135px) minmax(0,1fr)}.tp-x .stage-nav{max-height:135px;border-right:0;border-bottom:1px solid #1b2540;padding:4px 0}.tp-x .stage-nav .nav-title{padding:2px 10px 4px}.tp-x .stage-nav button{min-height:24px}.tp-x .content{padding:10px}.tp-x .overview .fl{max-height:55vh;overflow:auto}.tp-x .toolbar{padding:8px 10px}}


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
.tp-x .tp-rec{margin-top:8px}.tp-x .tp-rec pre{margin:4px 0 0;max-height:420px;overflow:auto;background:#05070d;border:1px solid #1b2540;border-radius:8px;padding:8px;font:11px/1.45 ui-monospace,Menlo,monospace;color:#c3cbe0;white-space:pre}
.tp-x .hatchsw{background:repeating-linear-gradient(45deg,#e66767 0 2px,#2a0f16 2px 5px)!important}
`;

const GRADE_COL = { measured: '#199e70', 'measured+vendor': '#3987e5', apportioned: '#9085e9', priced: '#c98500', modelled: '#e66767', lever: '#d55181', zero: '#4a5678' };

export async function loadRecord(url) { const r = await fetch(url); if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); }

/**
 * mountTokenExplorer(el, {base, design, group, onState})
 *   base         URL prefix of the data directory (default './data/'): <base><design>.json
 *   design       'qwen_rom' | 'ds_rom' | 'hbm_gen_qwen' | 'hbm_gen_ds' (retired ids map through ALIASES)
 *   group        initial drill group id (null = whole token)
 *   floorplan    false hides the data-flow floorplan replay (/explorer/dataflow/dataflow.js, link records per die revision)
 *   onState      called with {design, group} on every navigation (e.g. to update the URL hash)
 */
export async function mountTokenExplorer(el, opts = {}) {
  injectCSS('tp-css', CSS); injectCSS('tp-x-css', T_CSS);
  const o = Object.assign({ base: './data/', design: 'qwen_rom', group: null, onState: null, floorplan: true }, opts);
  const dfRecord = {};   // design -> die revision chosen in the data-flow panel (kept across re-renders)
  const state = { design: canonDesign(o.design), group: o.group, mode: o.mode === 'mtp' ? 'mtp' : 'ar' };
  const cache = {}, pcache = {};
  // generic HBM die: the decoded HGI-1 record behind an operator (tools/hgi_sim/listing.py), loaded on first click
  async function programRecord(data, n) {
    const f = data.program && data.program.file;
    if (!f || n.rec == null) return null;
    const pr = pcache[f] ||= loadRecord(o.base + f);
    const L = (await pr).listing[n.rec];
    return L ? L.text : null;
  }
  const clock = new Clock({ seconds: 24 });
  const root = h('div', { class: 'tp-x tp-root' });
  el.replaceChildren(root);
  let views = [];

  let covV = null, covErr = null, covPending = false;
  let renderRevision = 0;
  const expandedStages = new Set();
  function scrollContentTo(panel, inset = 0) {
    const content = panel?.closest('.content');
    if (content) content.scrollTop += panel.getBoundingClientRect().top - content.getBoundingClientRect().top - inset;
  }
  function navigateStage(gid) {
    tip(null); state.group = gid;
    return render(null, gid ? 'stage' : 'whole');
  }
  const loading = (label, hint = 'Fetching the flow graph and hardware details…') => h('div', { class: 'loading-state', role: 'status', 'aria-live': 'polite' },
    h('span', { class: 'spinner', 'aria-hidden': 'true' }), h('div', {}, label, h('small', {}, hint)));
  async function render(keepT = null, navigation = null) {
    const previousScroll = root.querySelector('.content')?.scrollTop || 0;
    const previousNavScroll = root.querySelector('.stage-nav')?.scrollTop || 0;
    const previousTreeFocus = root.contains(document.activeElement) ? document.activeElement?.dataset?.treeId : null;
    const revision = ++renderRevision;
    root.setAttribute('aria-busy', 'true');
    const current = cache[state.design];
    const group = current?.groups?.find(x => x.id === state.group);
    const label = state.group ? `Loading ${group?.label || 'layer'}…` : 'Loading token explorer…';
    let target = root.querySelector('.inspector');
    if (!target) {
      target = h('div', { class: 'panel loading-panel' });
      root.replaceChildren(target);
    }
    target.replaceChildren(loading(label));
    if (navigation === 'stage') { scrollContentTo(target); target.tabIndex = -1; target.focus({preventScroll:true}); }
    else if (navigation === 'whole') { const content = root.querySelector('.content'); if (content) content.scrollTop = 0; }
    try {
      await renderContent(keepT, revision, navigation, previousScroll, previousNavScroll, previousTreeFocus);
    } catch (e) {
      if (revision !== renderRevision) return;
      const destination = root.querySelector('.inspector') || target;
      destination.replaceChildren(h('div', { class: 'loading-state load-error', role: 'alert' },
        h('div', {}, 'Unable to load this view.', h('small', {}, e.message)),
        h('button', { onclick: () => render(keepT, navigation) }, 'Retry')));
    } finally {
      if (revision === renderRevision) root.setAttribute('aria-busy', 'false');
    }
  }
  async function renderContent(keepT, revision, navigation, previousScroll, previousNavScroll, previousTreeFocus) {
    clock.pause();
    const arData = cache[state.design] ||= await loadRecord(o.base + state.design + '.json');
    if (revision !== renderRevision) return;
    const mtpInfo = arData.mtp || { available: false, reason: 'no MTP record' };
    if (state.mode === 'mtp' && !mtpInfo.available) state.mode = 'ar';
    const data = state.mode === 'mtp' ? (cache[state.design + '_mtp'] ||= await loadRecord(o.base + mtpInfo.file)) : arData;
    if (revision !== renderRevision) return;
    const mtp = state.mode === 'mtp';
    // coverage: map every operator onto the coverage rows of its target (live from the ledgers; /api/coverage/token)
    const covKey = state.design + (mtp ? '_mtp' : '');
    if (!data._cov || data._cov.v !== covV) {
      try { const c = await attachCoverage(data, covKey); covV = c.v; covErr = null; } catch (e) { covErr = e.message; }
    }
    if (revision !== renderRevision) return;
    let native;
    try { native = await loadRecord('/api/native/coverage?design=' + encodeURIComponent(covKey)); }
    catch (e) { native = { native_qualified: false, nodes: {}, operations: [], defects: [{ edge: 'live_source', reason: e.message }] }; }
    if (revision !== renderRevision) return;
    for (const n of data.nodes) n.native = native.nodes?.[n.id] || { native_qualified: false, operations: [], defects: [{ edge: 'token_node->operation', reason: 'CURRENT_PROGRAM_MAPPING_UNAVAILABLE' }] };
    const nativePanel = nativeProvenancePanel(native);
    const p = P(data);
    if (state.group && !p.groups[state.group]) state.group = null;
    o.onState && o.onState({ ...state });
    const g = state.group ? p.groups[state.group] : null;
    const t0 = g ? g.start : 0, t1 = g ? g.end : data.totals.cycles;
    clock.scope(t0, t1, g ? 12 : 24);
    // tabs
    const modeSw = h('div', { class: 'mode', role: 'group', 'aria-label': 'decode mode' },
      h('button', { 'aria-pressed': String(!mtp), onclick: () => { if (mtp) { state.mode = 'ar'; state.group = null; render(null, 'whole'); } } }, 'AR'),
      h('button', { 'aria-pressed': String(mtp), title: mtpInfo.available ? 'MTP: one speculative verify step (draft → verify → accept)' : mtpInfo.reason,
        ...(mtpInfo.available ? {} : { disabled: '' }),
        onclick: () => { if (!mtp && mtpInfo.available) { state.mode = 'mtp'; state.group = null; render(null, 'whole'); } } }, 'MTP'));
    const tabs = h('div', { class: 'bar toolbar', role: 'group', 'aria-label': 'design' },
      ...DESIGNS.map((d) => h('button', { class: 'tab', 'aria-pressed': String(d.id === state.design), onclick: () => { state.design = d.id; state.group = null; render(null, 'whole'); } }, d.label)), modeSw);
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
        h('span', { class: 'kv' }, 'status ', h('b', {}, `${hd.status} · historical numerical/priced scope`))),
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
    const openStage = navigateStage;
    const crumb = h('div', { class: 'scopebar' },
      h('button', { onclick: () => openStage(null), 'aria-label': 'Back to whole token' }, g ? '← Back to whole token' : 'Whole token overview'),
      h('span', {}, g ? `Whole token / ${g.label}` : 'Select a stage to inspect its operators. The full path stays visible.'));
    const stageNav = stageTree(data, state, expandedStages, openStage);
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
    const flowP = h('section', { class: 'panel overview', 'aria-label': 'Whole token flow' },
      h('div', { class: 'pt' }, h('b', {}, mtp ? 'Flow graph of one MTP step: draft → verify → accept' : 'Flow graph by stage'), h('span', {}, 'Whole token · stage overview')),
      h('div', { class: 'metricline' }, h('b', {}, `${hd.tok_s.toLocaleString(undefined, { maximumFractionDigits: 1 })} tok/s`), h('span', {}, `${fmtCyc(tt.cycles)} · ${fmtUs(tt.cycles)} · ${mtp ? 'MTP step' : 'AR token'}`), h('span', {}, 'Historical numerical / priced scope · native ' + (native.native_qualified ? 'qualified' : 'incomplete'))),
      ctl, h('div', { class: 'fl', style: 'margin-top:12px' }), legend);
    const stageP = g ? h('div', { class: 'panel stage-flow' }, h('div', { class: 'pt' }, h('b', {}, `Operators of ${g.label}`), h('span', {}, `${fmtCyc(g.cycles)} · ${fmtPct(g.share)} of token`)), h('div', { class: 'fl' })) : null;
    const ganttP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Timeline by element class'), h('span', {}, 'critical chain = cyan line · dbl-click to seek')), h('div', { class: 'gn' }));
    const sel = h('div', { class: 'kv' }, 'Click an operator for its detail and element cards.');
    const dieBox = h('div', {}, loading('Loading the link model…', 'Fetching the die revision…'));
    const dieP = o.floorplan ? h('section', { class: 'panel df-host', 'aria-label': 'Data flow on the floorplan' }, h('div', { class: 'pt' }, h('b', {}, 'Data flow on the floorplan'),
      h('span', {}, 'links active in the schedule window · width ∝ log bits · colour = length vs reach · ', h('a', { href: `/explorer/dataflow/#design=${state.design}`, class: 'tp-el' }, 'full view →'))), dieBox) : null;
    const selP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'Selected operator')), sel);
    const shareP = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, mtp ? 'Share of the MTP step' : 'Share of the token latency'), h('span', {}, 'by stage and by element class')), shareTables(data, p, openStage));
    const notes = h('div', { class: 'panel' }, h('div', { class: 'pt' }, h('b', {}, 'How the numbers are built')), h('ul', { class: 'notes' }, ...data.notes.map((n) => h('li', {}, n))));
    const inspector = h('section', { class: 'panel inspector', 'aria-label': 'Stage inspector', tabindex: -1 }, crumb,
      ...(g ? [stageP] : [h('div', { class: 'kv' }, 'Inspect a stage from the flow graph or the stage list. Select an operator to see its timing, source and hardware mapping.')]),
      selP);
    const evidence = h('details', { class: 'evidence' }, h('summary', {}, 'Timing provenance, accounting and source records'), banner);
    const content = h('div', { class: 'content' }, flowP, ...(dieP ? [dieP] : []), inspector, ganttP);
    if (mtp) content.append(hwPanel(data, (n) => openStage(n.group)));
    content.append(shareP, evidence, notes, nativePanel);
    views.forEach((v) => v && v.destroy && v.destroy()); views = [];
    root.replaceChildren(tabs, h('div', { class: 'workspace' }, stageNav, content));
    const restoreView = () => {
      if (revision !== renderRevision) return;
      if (navigation === 'stage' && g) { scrollContentTo(inspector); inspector.focus({ preventScroll: true }); }
      else content.scrollTop = navigation === 'whole' ? 0 : previousScroll;
      stageNav.scrollTop = previousNavScroll;
      if (navigation === 'stage') {
        const selected = stageNav.querySelector('[aria-selected=true]');
        if (selected) { const r = selected.getBoundingClientRect(), v = stageNav.getBoundingClientRect(); if (r.top < v.top || r.bottom > v.bottom) stageNav.scrollTop += r.top - v.top - 30; }
      } else if (!navigation && previousTreeFocus) {
        [...stageNav.querySelectorAll('[role=treeitem]')].find(b => b.dataset.treeId === previousTreeFocus)?.focus({preventScroll:true});
      }
    };
    restoreView();
    requestAnimationFrame(restoreView);
    const onSelect = (n) => {
      sel.replaceChildren(detail(data, n));
      if (data.program && n.rec != null) {
        const box = h('div', { class: 'tp-rec' }, h('div', { class: 'tp-dm' }, `decoded HGI-1 record ${n.rec} of the image${n.iter != null ? ` (loop iteration L = ${n.iter})` : ''} · tools/hgi_sim/listing.py`), h('pre', {}, 'loading…'));
        sel.append(box);
        programRecord(data, n).then((t) => { box.querySelector('pre').textContent = t || 'record not in the listing'; }, (e) => { box.querySelector('pre').textContent = 'listing: ' + e.message; });
      }
      views.forEach((v) => v && v.select && v.select(n.id));
      const bounds = selP.getBoundingClientRect(), viewport = content.getBoundingClientRect();
      if (bounds.top < viewport.top || bounds.top + 80 > viewport.bottom) scrollContentTo(selP, 100);
    };
    views.push(mountFlow(flowP.querySelector('.fl'), data, { clock, group: null, onSelect, onDrill: openStage }));
    if (stageP) views.push(mountFlow(stageP.querySelector('.fl'), data, { clock, group: state.group, onSelect }));
    if (g) {
      const i = data.groups.filter(x => x.critical).findIndex(x => x.id === g.id);
      const box = flowP.querySelectorAll('.gbox')[i];
      if (box) { box.classList.add('inspected'); box.setAttribute('aria-current', 'step'); }
    }
    views.push(mountGantt(ganttP.querySelector('.gn'), data, { clock, range: [t0, t1], onSelect, onZoom: openStage }));
    if (dieP) {
      clock.seek(keepT != null && keepT >= t0 && keepT <= t1 ? keepT : t0);
      try {
        const df = await mountDataflow(dieBox, { data, clock, design: state.design, group: state.group, record: dfRecord[state.design] || null,
          onRecord: (id) => { dfRecord[state.design] = id; }, onNode: (n) => onSelect(n) });
        if (revision !== renderRevision) { df.destroy(); return; }
        views.push(df);
      } catch (e) { dieBox.replaceChildren(h('div', { class: 'kv' }, 'data-flow view unavailable: ' + e.message)); }
      if (revision !== renderRevision) return;
    }
    clock.seek(keepT != null && keepT >= t0 && keepT <= t1 ? keepT : t0);
  }
  function rerender() { return render(clock.t); }
  await render(null, state.group ? 'stage' : 'whole');
  // the ledgers change under the view: re-map when /api/coverage/version moves (deferred while the replay plays)
  clock.on(() => { if (covPending && !clock.playing) { covPending = false; rerender(); } });
  setInterval(async () => {
    try {
      const v = await coverageVersion();
      if (v && covV && v !== covV) { covV = v; for (const k in cache) if (cache[k]) cache[k]._cov = null; if (clock.playing) covPending = true; else rerender(); }
    } catch (e) { /* server restart */ }
  }, 30000);
  return { clock, show(design, group = null, mode = state.mode) { state.design = canonDesign(design); state.group = group; state.mode = mode; return render(null, group ? 'stage' : 'whole'); }, state };
}

/** Compact, keyboard navigable hierarchy of the actual program's stage groups. */
function stageTree(data, state, expanded, openStage) {
  const namespace = `${state.design}/${state.mode}/`;
  const groups = data.groups.filter(g => g.critical);
  const root = { id: 'path', label: 'Token path', children: [] };
  function folder(parent, id, label) {
    let item = parent.children.find(x => x.id === id);
    if (!item) { item = { id, label, children: [] }; parent.children.push(item); }
    return item;
  }
  for (const g of groups) {
    let parent = root;
    const phase = g.phase || (/^D[.0-9H]/.test(g.id) || /^Draft/i.test(g.label) ? 'draft' : /^V[.]/.test(g.id) || /^Verify/i.test(g.label) ? 'verify' : /^(A|acc)$/.test(g.id) ? 'accept' : null);
    if (phase) parent = folder(parent, phase, PHASE[phase]?.label || phase);
    const layer = g.label.match(/\blayer\s+(\d+)/i);
    const category = layer ? 'layers' : /head|argmax|accept|commit/i.test(g.label) ? 'decode' : /embed|prologue/i.test(g.label) ? 'input' : 'stages';
    parent = folder(parent, parent.id + '/' + category, { layers:'Layers', decode:'Head / output', input:'Input', stages:'Pipeline stages' }[category]);
    // HBM attention and FFN are distinct stage groups of the same real layer.
    if (layer && groups.some(x => x.id !== g.id && x.label.match(/\blayer\s+(\d+)/i)?.[1] === layer[1] && (x.phase || '') === (g.phase || '') && x.id.split('.')[0] === g.id.split('.')[0])) {
      parent = folder(parent, parent.id + '/L' + layer[1], 'Layer ' + layer[1]);
    }
    parent.children.push({ id: 'stage/' + g.id, label: g.label, stage: g });
  }
  // Expand selected ancestors when navigating from the canvas, timeline or table.
  // Visit every branch rather than stopping after the first selected descendant.
  function revealAll(item) { if (!item.children) return item.stage?.id === state.group; const hits = item.children.map(revealAll); if (hits.some(Boolean)) expanded.add(namespace + item.id); return hits.some(Boolean); }
  revealAll(root);
  if (!expanded.has(namespace + 'initialized')) { expanded.add(namespace + 'initialized'); expanded.add(namespace + 'path'); for (const child of root.children) expanded.add(namespace + child.id); }
  const nav = h('nav', { class: 'stage-nav', 'aria-label': 'Token stages' });
  const tree = h('div', { role: 'tree', 'aria-label': 'Token stage hierarchy' });
  nav.append(h('div', { class: 'nav-title' }, 'Token stages'), tree);
  function draw(focusId = null) {
    let selectedButton = null;
    function row(item, level, parentId = '') {
      const isFolder = !!item.children, isOpen = expanded.has(namespace + item.id);
      const childId = 'tp-tree-' + encodeURIComponent(namespace + item.id);
      const button = h('button', { role: 'treeitem', 'aria-level': level, 'data-tree-id': item.id, 'data-parent-id': parentId,
        ...(isFolder ? { class:'tree-folder', 'aria-expanded': String(isOpen), ...(isOpen ? { 'aria-owns': childId } : {}) } : { 'aria-selected': String((item.stage?.id || null) === state.group) }), tabindex: -1, title: item.label,
        onclick: () => { if (isFolder) { isOpen ? expanded.delete(namespace + item.id) : expanded.add(namespace + item.id); draw(item.id); } else openStage(item.stage?.id || null); } },
        h('span', { class:'tree-arrow', 'aria-hidden':'true' }, isFolder ? isOpen ? '▾' : '▸' : '·'),
        h('span', { class:'tree-label' }, item.label), h('small', {}, isFolder ? String(item.children.length) : item.stage ? fmtPct(item.stage.share) : `${groups.length}`));
      if (!isFolder && (item.stage?.id || null) === state.group) selectedButton = button;
      const branch = h('div', { role:'none' }, button);
      if (isFolder && isOpen) branch.append(h('div', { role:'group', id: childId }, ...item.children.map(x => row(x, level + 1, item.id))));
      return branch;
    }
    tree.replaceChildren(row({id:'whole', label:'Whole token'}, 1), row(root, 1));
    const buttons = [...tree.querySelectorAll('[role=treeitem]')];
    const focus = buttons.find(b => b.dataset.treeId === focusId) || selectedButton || buttons[0];
    focus.tabIndex = 0;
    if (focusId) focus.focus({preventScroll:true});
  }
  tree.addEventListener('focusin', e => { const item = e.target.closest('[role=treeitem]'); if (item) for (const button of tree.querySelectorAll('[role=treeitem]')) button.tabIndex = button === item ? 0 : -1; });
  tree.addEventListener('keydown', e => {
    const item = e.target.closest('[role=treeitem]'); if (!item) return;
    const buttons = [...tree.querySelectorAll('[role=treeitem]')], index = buttons.indexOf(item);
    let next;
    if (e.key === 'ArrowDown') next = buttons[Math.min(index + 1, buttons.length - 1)];
    else if (e.key === 'ArrowUp') next = buttons[Math.max(index - 1, 0)];
    else if (e.key === 'Home') next = buttons[0];
    else if (e.key === 'End') next = buttons.at(-1);
    else if (e.key === 'ArrowRight') { if (item.getAttribute('aria-expanded') === 'false') item.click(); else if (item.getAttribute('aria-expanded') === 'true') next = buttons[index + 1]; }
    else if (e.key === 'ArrowLeft') { if (item.getAttribute('aria-expanded') === 'true') item.click(); else next = buttons.find(b => b.dataset.treeId === item.dataset.parentId); }
    else return;
    e.preventDefault(); if (next) { next.focus({preventScroll:true}); next.scrollIntoView({block:'nearest'}); }
  });
  draw(); return nav;
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

// Authoritative operation/RTL/physical edges, independent of old coverage labels.
function nativeProvenancePanel(n) {
  const panel = h('details', { class: 'panel native-audit' },
    h('summary', {}, `Native lifecycle: ${n.native_qualified ? 'QUALIFIED' : 'INCOMPLETE'}`, h('span', {}, `${n.summary?.native_operations || 0} / ${n.summary?.operations || 0} operations · expand source-bound audit`)),
    h('div', { class: 'pt', style: 'margin-top:12px' }, h('b', {}, 'Native lifecycle evidence'),
      h('a', { href: '/api/native/coverage?design=' + encodeURIComponent(n.design || '') }, 'source-bound JSON →')),
    h('p', { class: 'kv' }, `${n.summary?.operations || 0} emitted operations · ${n.summary?.native_operations || 0} have the complete RTL → routed leaf → die chain. Historical numerical PASS and priced cycles remain separate.`));
  const missing = Object.entries(n.summary?.missing_edges || {});
  if (missing.length) panel.append(h('div', { class: 'kv' }, missing.map(([edge, count]) => `${edge}: ${count}`).join(' · ')));
  const input = h('input', { placeholder: 'Filter operation, instance, missing edge or reason', 'aria-label': 'native provenance filter', style: 'width:95%;margin:8px 0' });
  const list = h('div', {});
  const entries = [
    ...(n.defects || []).map(d => ({id: 'target inventory', instance: '', defects: [d]})),
    ...(n.operations || []),
    ...Object.entries(n.nodes || {}).filter(([,r]) => r.defects?.length && !r.operations?.length).map(([id,r]) => ({id, instance: '', defects:r.defects})),
  ];
  function draw() {
    const query = input.value.toLowerCase();
    const rows = entries.filter(r => JSON.stringify(r).toLowerCase().includes(query));
    list.replaceChildren(h('div', { class: 'kv' }, `${rows.length} matching records; first 50 shown. Select an operator for its exact token mapping.`),
      ...rows.slice(0, 50).map(r => h('details', { class: 'tp-cov' },
        h('summary', {}, `${r.id} · ${r.instance || 'no elaborated instance'} · ${r.native_qualified ? 'qualified' : (r.defects?.[0]?.reason || 'unproven')}`),
        h('div', { class: 'tp-src' }, r.instruction_sha256 ? `instruction SHA256 ${r.instruction_sha256}` : ''),
        ...r.defects.map(d => h('div', { class: 'tp-covr' }, `${d.edge}: ${d.reason}`)))));
  }
  input.addEventListener('input', draw); draw();
  panel.append(input, list);
  if (n.current_gap_groups?.length) panel.append(h('details', {}, h('summary', {}, 'Current die gaps and owners'),
    ...n.current_gap_groups.map(g => h('p', { class:'kv' }, `${g.die}: ${g.masters.join(', ')} · ${g.owner || 'UNASSIGNED'} · ${g.detail}`))));
  return panel;
}

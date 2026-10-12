/* Chip Explorer element page (/explorer/element/): one closed element (or a side-by-side pair), from its final routed
   DB (tools/explorer_elem_export.py: OpenROAD in the ORFS container with the closure loop's own sign-off STA setup) and
   its RTL at the closure's source commit (tools/explorer_elem/rtl_export.py: yosys elaboration of the exact synthesis
   inputs).  Tabs: Layout (landing) · Timing · Clock arrival · Clock tree · Density · RTL (structure diagram, reference
   model, source) · Facts (key numbers, throughput qualification, every fact with its record).
   URL: ?p=<page id> | ?e=<element id>; #tab=<tab>; ?safe=1 hides raw names. */
(function(){
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const fmt = (n, d = 1) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
const sgn = (n, d = 2) => n == null || isNaN(n) ? '—' : (n >= 0 ? '+' : '−') + fmt(Math.abs(n), d);
const QP = new URLSearchParams(location.search);
const SAFE = QP.get('safe') === '1';
const QS = SAFE ? '?safe=1' : '';
function lsGet(k, d){ try { const v = localStorage.getItem('otx.elem.' + k); return v == null ? d : v; } catch (e) { return d; } }
function lsSet(k, v){ try { localStorage.setItem('otx.elem.' + k, v); } catch (e) {} }
try { localStorage.removeItem('otx.elem.mode'); localStorage.removeItem('otx.elem.lens'); } catch (e) {}
function cssv(n){ return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
function hex2rgb(h){ h = h.replace('#', ''); if (h.length === 3) h = h.split('').map(x => x + x).join(''); return [0, 2, 4].map(i => parseInt(h.substr(i, 2), 16)); }

const F = {flop: 1, clk: 2, lvt: 4, hold: 8, repair: 16, infer: 32, slvt: 64, icg: 128};
const TABS = [
  ['layout', 'Layout', 'Every placed cell of the routed layout, coloured by the RTL block it implements.'],
  ['timing', 'Timing', 'The worst setup (TT) and hold (FF) paths, drawn through their placed pins, with per-stage delays.'],
  ['arrival', 'Clock arrival', 'When the clock edge reaches each flop, on one colour scale for every element shown.'],
  ['tree', 'Clock tree', 'How one clock pin feeds every flop: each buffer level and clock gate, on the layout and as a level diagram.'],
  ['density', 'Density', 'Cell density, pin density and routed-wire demand per bin.'],
  ['rtl', 'RTL', 'Structure from the elaborated RTL, the reference model the bench names, and the source at the closure\u2019s commit. Select a module to light its cells.'],
  ['facts', 'Facts', 'Key numbers, throughput qualification against the budget, and every sign-off and layout fact with its record.']];
const LAYOUT_TABS = new Set(['layout', 'timing', 'arrival', 'tree', 'density']);
const PAL = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#17becf', '#bcbd22', '#8c6bb1'];
const OTHER = '#7c86a6', UNATTR = '#4a5678';
const RAMP = ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'];
const HEAT = ['#0d0887', '#7e03a8', '#cc4778', '#f89540', '#f0f921'];
const LVL = ['#5e4fa2', '#3288bd', '#66c2a5', '#abdda4', '#e6f598', '#fee08b', '#fdae61', '#f46d43', '#d53e4f', '#9e0142'];
function rampAt(r, t){ t = Math.max(0, Math.min(1, t)); const k = t * (r.length - 1), i = Math.min(r.length - 2, Math.floor(k)), f = k - i;
  const a = hex2rgb(r[i]), b = hex2rgb(r[i + 1]); return [0, 1, 2].map(j => Math.round(a[j] + (b[j] - a[j]) * f)); }
const rgb = c => `rgb(${c[0]},${c[1]},${c[2]})`;

const S = {page: null, pages: null, els: [], tab: 'layout', depth: null, iso: {}, pcorner: lsGet('pcorner', 'setup'), ccorner: lsGet('ccorner', 'tt'),
  dmetric: lsGet('dmetric', 'density'), psel: {}, tview: lsGet('tview', 'wires'), tlevel: null, rtlEl: 0, rtlSel: null, rtlFile: null, rtlLines: null,
  diag: {}, tput: null, rows: false};

/* ------------------------------------------------------------------ theme */
function applyTheme(){ const t = lsGet('theme', ''); if (t) document.documentElement.setAttribute('data-theme', t); else document.documentElement.removeAttribute('data-theme'); }
applyTheme();
$('theme').onclick = () => { const dark = cssv('color-scheme') !== 'light'; lsSet('theme', dark ? 'light' : 'dark'); applyTheme(); S.els.forEach(E => E.raster = {}); render(); };

/* ------------------------------------------------------------------ load */
async function getJSON(u){ const r = await fetch(u, {cache: 'no-store'}); if (!r.ok) throw new Error(r.status + ' ' + u); return r.json(); }
async function getBin(u){ const r = await fetch(u, {cache: 'no-store'}); if (!r.ok) throw new Error(r.status + ' ' + u); return r.arrayBuffer(); }
function hashTab(){ const m = location.hash.match(/^#tab=(\w+)/); if (m && m[1] === 'overview') return 'layout'; return m && TABS.some(t => t[0] === m[1]) ? m[1] : null; }

async function init(){
  // the stepped story and the Overview tab are gone: their deep links land on the Layout
  if (/^#(story-|overview|tab=overview)/.test(location.hash)){ try { history.replaceState(null, '', location.pathname + location.search + '#tab=layout'); } catch (e) {} }
  let pages = {pages: [], elements: {}};
  try { pages = await getJSON('pages.json' + QS); } catch (e) {}
  S.pages = pages;
  let pid = QP.get('p'), eid = QP.get('e');
  let page = pages.pages.find(p => p.id === pid);
  if (!page && eid) page = pages.pages.find(p => p.elements.length === 1 && p.elements[0] === eid) || {id: eid, elements: [eid], title: null, summary: null, blocks: []};
  if (!page) page = pages.pages[0];
  if (!page){ $('sum').textContent = 'No element pages are installed yet.'; return; }
  S.page = page;
  document.title = (page.title || 'Element Layout').slice(0, 40);
  $('title').textContent = page.title || page.elements.join(' vs ');
  S.tab = hashTab() || 'layout';
  renderTabs();
  buildStage();
  const els = await Promise.all(page.elements.map(async (id, k) => {
    try {
      const d = await getJSON('data/' + encodeURIComponent(id) + '.json' + QS);
      if (!d.geom) return {id, d, k, pane: S.panes[k], nolayout: true, M: {status: (d.facts.find(f => f.k === 'status') || {}).v, recTT: factv(d, /setup WNS \(sign-off/), recFF: factv(d, /^FF hold WNS \(sign-off/), drc: factv(d, /^DRC$/)}};
      const [buf, cbuf] = await Promise.all([getBin('data/' + encodeURIComponent(d.geom.cells.file)),
        d.clock_wires ? getBin('data/' + encodeURIComponent(d.clock_wires.file)).catch(() => null) : null]);
      return prep(id, d, buf, cbuf, k);
    } catch (e) { return {id, err: String(e), k, pane: S.panes[k]}; }
  }));
  S.els = els;
  if (!page.title) $('title').textContent = els.map(E => E.d ? E.d.label + (E.d.target ? ' · ' + E.d.target : '') : E.id).join(' vs ');
  document.title = ($('title').textContent || 'Element').slice(0, 40);
  const sumtxt = page.summary || els.filter(E => E.d).map(E => [E.d.category, E.d.role && E.d.role !== E.d.category ? E.d.role : null, E.d.nosta && E.d.layout ? 'timing not re-run (sources released)' : null].filter(Boolean).join(' · ')).join(' | ');
  $('sum').textContent = sumtxt; $('sum').parentNode.hidden = !sumtxt;
  els.forEach(E => { const p = E.pane; p.busy.textContent = E.err ? 'Could not load ' + E.id + ': ' + E.err : E.nolayout ? 'Layout data released: the closure loop deleted this job\u2019s routed DB before the page existed. RTL and Facts remain.' : ''; p.busy.hidden = !(E.err || E.nolayout); });
  if (LAYOUT_TABS.has(S.tab) && els.every(E => E.nolayout || E.err)){ S.tab = 'facts'; renderTabs(); }
  chooseLayout();
  S.depth = +lsGet('depth.' + page.id, 0) || null;
  regroup();
  renderPills();
  render();
  // RTL (1 MB per element) and the throughput budget load behind the first paint
  els.forEach(E => { if (!E.err && E.d && E.d.rtl_file) getJSON('data/' + encodeURIComponent(E.d.rtl_file) + QS).then(r => { if (r && r.tree){ E.rtl = r; prepRtl(E); if (S.tab === 'rtl' || S.tab === 'layout') render(); } }).catch(() => {}); });
  loadTput(); setInterval(loadTput, 10 * 60 * 1000);
}
async function loadTput(){
  const blocks = (S.page.blocks || []).concat(S.els.filter(E => !E.err).map(E => E.d.block), S.els.filter(E => !E.err).map(E => E.d.job));
  try { S.tput = await getJSON('/api/explorer/elem_tput?blocks=' + encodeURIComponent(blocks.join(',')) + (SAFE ? '&safe=1' : '')); }
  catch (e) { S.tput = {status: 'unavailable', error: String(e)}; }
  if (S.tab === 'facts') renderSide();
}
function factv(d, re){ const f = (d.facts || []).find(x => re.test(x.k)); return f ? f.v : null; }

function prep(id, d, buf, cbuf, k){
  const g = d.geom, n = g.cells.n, q = g.quantum_dbu / g.dbu_per_um;
  const u16 = (o) => new Uint16Array(buf, o, n);
  const xq = u16(0), yq = u16(2 * n), wq = u16(4 * n), hq = u16(6 * n);
  const E = {id, d, k, n, mod: u16(8 * n), mas: u16(10 * n), fl: new Uint8Array(buf, 12 * n, n),
    x: new Float32Array(n), y: new Float32Array(n), w: new Float32Array(n), h: new Float32Array(n),
    W: g.die.x1 - g.die.x0, H: g.die.y1 - g.die.y0, raster: {}, view: null, pane: S.panes[k]};
  for (let i = 0; i < n; i++){ E.x[i] = xq[i] * q; E.y[i] = yq[i] * q; E.w[i] = wq[i] / 1000; E.h[i] = hq[i] / 1000; }
  if (cbuf && d.clock_wires){ const m = d.clock_wires.n, cq = d.clock_wires.quantum_dbu / g.dbu_per_um;
    E.cw = {n: m, q: cq, x1: new Uint16Array(cbuf, 0, m), y1: new Uint16Array(cbuf, 2 * m, m), x2: new Uint16Array(cbuf, 4 * m, m), y2: new Uint16Array(cbuf, 6 * m, m),
      layer: new Uint8Array(cbuf, 8 * m, m), lvl: new Uint8Array(cbuf, 9 * m, m)}; }
  buildIndex(E);
  const L = d.clock_tt.leaves; E.leafOf = new Int32Array(n).fill(-1);
  for (let j = 0; j < L.length; j++){ if (L[j][5]) continue; const c = hit(E, L[j][0], L[j][1], F.flop); if (c >= 0) E.leafOf[c] = j; }
  const byName = new Map(); L.forEach((l, j) => byName.set(l[4], j));
  const ffl = d.clock_ff_match ? d.clock_ff_leaves : null;
  const ck = (pin, ff) => { const j = byName.get(String(pin).replace(/\/[^/]*$/, '')); return j == null ? null : ff ? (ffl ? ffl[j] : null) : L[j][3]; };
  (d.setup_paths || []).forEach(p => { p.launch_clk_ps = ck(p.start, false); p.capture_clk_ps = ck(p.end, false); });
  (d.hold_paths || []).forEach(p => { p.launch_clk_ps = ck(p.start, true); p.capture_clk_ps = ck(p.end, true); });
  // inferred-cell count per module index
  E.inferByMod = new Uint32Array(g.modules.length); for (let i = 0; i < n; i++) if (E.fl[i] & F.infer) E.inferByMod[E.mod[i]]++;
  E.M = metrics(E);
  E.tree = treeStats(E);
  return E;
}
function buildIndex(E){
  const bs = Math.max(0.5, Math.max(E.W, E.H) / 600); const nx = Math.ceil(E.W / bs) + 1, ny = Math.ceil(E.H / bs) + 1;
  const cnt = new Uint32Array(nx * ny + 1), b = new Uint32Array(E.n);
  for (let i = 0; i < E.n; i++){ const bx = Math.min(nx - 1, Math.floor((E.x[i] + E.w[i] / 2) / bs)), by = Math.min(ny - 1, Math.floor((E.y[i] + E.h[i] / 2) / bs)); b[i] = by * nx + bx; cnt[b[i] + 1]++; }
  for (let i = 1; i <= nx * ny; i++) cnt[i] += cnt[i - 1];
  const pos = cnt.slice(0, nx * ny), idx = new Uint32Array(E.n);
  for (let i = 0; i < E.n; i++) idx[pos[b[i]]++] = i;
  E.bi = {bs, nx, ny, start: cnt, idx};
}
function hit(E, x, y, needFlag){
  const {bs, nx, ny, start, idx} = E.bi; const bx = Math.floor(x / bs), by = Math.floor(y / bs);
  let best = -1, bd = 1e18;
  for (let yy = by - 1; yy <= by + 1; yy++) for (let xx = bx - 1; xx <= bx + 1; xx++){
    if (xx < 0 || yy < 0 || xx >= nx || yy >= ny) continue;
    const bb = yy * nx + xx;
    for (let p = start[bb]; p < start[bb + 1]; p++){
      const i = idx[p]; if (needFlag && !(E.fl[i] & needFlag)) continue;
      const inside = x >= E.x[i] && x <= E.x[i] + E.w[i] && y >= E.y[i] && y <= E.y[i] + E.h[i];
      const dx = E.x[i] + E.w[i] / 2 - x, dy = E.y[i] + E.h[i] / 2 - y, dd = dx * dx + dy * dy - (inside ? 1e9 : 0);
      if (dd < bd){ bd = dd; best = i; }
    }
  }
  return best;
}
function pct(a, p){ if (!a.length) return null; const k = (a.length - 1) * p, i = Math.floor(k), f = k - i; return a[i] + ((a[Math.min(a.length - 1, i + 1)] - a[i]) * f); }
function latStats(vals){
  const a = vals.filter(v => v != null && isFinite(v)).sort((x, y) => x - y);
  if (!a.length) return null;
  return {n: a.length, min: a[0], max: a[a.length - 1], p1: pct(a, .01), p50: pct(a, .5), p99: pct(a, .99), spread: a[a.length - 1] - a[0], p9901: pct(a, .99) - pct(a, .01), sorted: a};
}
function metrics(E){
  const d = E.d, st = d.geom.stats, L = d.clock_tt.leaves, N = d.clock_tt.nodes;
  const flopIdx = []; L.forEach((l, j) => { if (!l[5]) flopIdx.push(j); });
  const tt = latStats(flopIdx.map(j => L[j][3]));
  const ff = d.clock_ff_match && d.clock_ff_leaves ? latStats(flopIdx.map(j => d.clock_ff_leaves[j])) : null;
  let hold = 0; for (let i = 0; i < E.n; i++) if (E.fl[i] & F.hold) hold++;
  const fact = k => { const f = d.facts.find(x => x.k === k); return f ? f.v : null; };
  const per = (d.clocks || [])[1];
  return {flops: st.flops, leaves: flopIdx.length, tt, ff, holdBuf: hold, holdPct: 100 * hold / E.n,
    clkNodes: N.filter(x => x[4] !== 'PORT').length, clkDepth: N.reduce((m, x) => Math.max(m, x[3]), 0),
    recTT: fact('TT setup WNS (sign-off record)'), recFF: fact('FF hold WNS (sign-off record)'), drc: fact('DRC'), util: fact('utilisation (std+macro)/core'),
    status: fact('status'), periodPs: per ? +per : null};
}
function treeStats(E){
  const N = E.d.clock_tt.nodes, L = E.d.clock_tt.leaves, D = N.reduce((m, x) => Math.max(m, x[3]), 0);
  const lv = Array.from({length: D + 2}, (_, i) => ({lvl: i, bufs: 0, icg: 0, kids: [], flops: 0, macros: 0}));
  const kids = new Uint32Array(N.length);
  N.forEach(n => { if (n[2] >= 0) kids[n[2]]++; });
  L.forEach(l => { if (l[2] >= 0) kids[l[2]]++; });
  N.forEach((n, i) => { const r = lv[n[3]]; if (n[4] === 'PORT') return; r.bufs++; if (/ICG/.test(n[4])) r.icg++; r.kids.push(kids[i]); });
  L.forEach(l => { const p = N[l[2]]; if (!p) return; const r = lv[p[3] + 1]; if (l[5]) r.macros++; else r.flops++; });
  lv.forEach(r => { r.fanAvg = r.kids.length ? r.kids.reduce((a, b) => a + b, 0) / r.kids.length : 0; r.fanMax = r.kids.length ? Math.max(...r.kids) : 0; delete r.kids; });
  const rootFan = N.filter(n => n[4] === 'PORT').map((n, i) => kids[N.indexOf(n)]);
  return {D, lv, rootFan: rootFan[0] || 0, icgNodes: N.map((n, i) => /ICG/.test(n[4]) ? i : -1).filter(i => i >= 0)};
}

/* ------------------------------------------------------------------ hierarchy groups (Layout tab colours) */
function regroup(){
  S.els.forEach(E => {
    if (E.err || E.nolayout) return;
    const mods = E.d.geom.modules, cnt = E.d.geom.module_cells;
    const comps = mods.map(m => m === '(unattributed)' ? null : m.split('.'));
    let pre = null; comps.forEach(c => { if (!c) return; if (pre == null) pre = c.slice(); else { let i = 0; while (i < pre.length && i < c.length && pre[i] === c[i]) i++; pre.length = i; } });
    pre = pre || [];
    E.prefix = pre.join('.');
    const keyAt = (c, dep) => c ? (c.slice(pre.length, pre.length + dep).join('.') || '(top)') : '(unattributed)';
    let depth = S.depth;
    if (!depth){ depth = 1;
      for (let dep = 1; dep <= 6; dep++){ const m = new Map(); comps.forEach((c, i) => { const k = keyAt(c, dep); m.set(k, (m.get(k) || 0) + cnt[i]); });
        const big = [...m.values()].filter(v => v >= E.n * 0.01).length; depth = dep; if (big >= 5) break; } }
    E.depth = depth;
    const tot = new Map(); comps.forEach((c, i) => { const k = keyAt(c, depth); tot.set(k, (tot.get(k) || 0) + cnt[i]); });
    const order = [...tot.entries()].filter(([k]) => k !== '(unattributed)').sort((a, b) => b[1] - a[1]);
    const top = order.slice(0, PAL.length).map(x => x[0]);
    const groups = top.map((k, i) => ({name: k, color: PAL[i], count: tot.get(k)}));
    const rest = order.slice(PAL.length).reduce((s, x) => s + x[1], 0);
    if (rest) groups.push({name: '(other ' + (order.length - PAL.length) + ' blocks)', color: OTHER, count: rest});
    if (tot.get('(unattributed)')) groups.push({name: '(unattributed)', color: UNATTR, count: tot.get('(unattributed)')});
    const gi = new Map(groups.map((g, i) => [g.name, i])), oth = groups.find(g => g.name.startsWith('(other'));
    E.modGroup = comps.map(c => { const k = keyAt(c, depth); return gi.has(k) ? gi.get(k) : (k === '(unattributed)' ? gi.get('(unattributed)') : gi.get(oth.name)); });
    E.groups = groups;
    E.grp = new Uint8Array(E.n); for (let i = 0; i < E.n; i++) E.grp[i] = E.modGroup[E.mod[i]];
    E.raster = {};
    if (!S.iso[E.id]) S.iso[E.id] = new Set();
  });
}

/* ------------------------------------------------------------------ RTL index: placed flop -> register declaration */
function prepRtl(E){
  const R = E.rtl;
  E.instOf = {}; for (const k in R.modules){ const m = R.modules[k]; const o = {}; (m.inst || []).forEach(x => o[x[0]] = x[1]); E.instOf[k] = o; }
  if (E.nolayout){ E.prefCount = () => [0, 0]; return; }
  const mods = E.d.geom.modules;
  E.prefCount = p => { let n = 0, inf = 0; const pp = p ? p + '.' : ''; for (let i = 0; i < mods.length; i++){ const m = mods[i]; if (!p ? m !== '(unattributed)' : (m === p || m.startsWith(pp))){ n += E.d.geom.module_cells[i]; inf += E.inferByMod[i]; } } return [n, inf]; };
}
function resolveReg(E, name){
  const R = E.rtl; if (!R) return null;
  let s = String(name).replace(/\$_.*$/, '').replace(/\//g, '.');
  const comps = s.match(/[^.\[]+(\[[^\]]*\])*/g) || [];
  let k = R.tree.k, pos = 0, path = [];
  for (;;){
    const inst = E.instOf[k] || {}; let hitJ = -1;
    for (let j = comps.length - 1; j > pos; j--){ const cand = comps.slice(pos, j).join('.'); if (inst[cand]){ hitJ = j; path.push(cand); k = inst[cand]; break; } }
    if (hitJ < 0) break; pos = hitJ;
  }
  const m = R.modules[k]; if (!m) return null;
  let rest = comps.slice(pos).join('.');
  for (let t = 0; t < 6 && rest; t++){
    const nn = m.nets[rest]; if (nn) return {module: m.name, inst: path.join('.'), reg: rest, file: nn[0], line: nn[1], width: nn[2]};
    const r2 = rest.replace(/\[[^\]]*\]$/, ''); if (r2 === rest) break; rest = r2;
  }
  return {module: m.name, inst: path.join('.'), reg: comps.slice(pos).join('.'), file: m.src && m.src[0], line: m.src && m.src[1], unresolved: true};
}

/* ------------------------------------------------------------------ tabs */
function renderTabs(){
  $('tabs').innerHTML = TABS.map(([k, t]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${S.tab === k}">${t}</button>`).join('');
  $('tabs').querySelectorAll('[data-tab]').forEach(b => b.onclick = () => setTab(b.dataset.tab));
  $('tabdesc').textContent = (TABS.find(t => t[0] === S.tab) || [])[2] || '';
}
function setTab(k){
  S.tab = k; renderTabs();
  try { history.replaceState(null, '', location.pathname + location.search + '#tab=' + k); } catch (e) {}
  render();
}
window.addEventListener('hashchange', () => { if (/^#(story-|overview)/.test(location.hash)){ setTab('layout'); return; } const t = hashTab(); if (t && t !== S.tab) setTab(t); });
function render(){
  document.body.className = 'tab-' + S.tab;
  S.els.forEach(E => { if (!E.err && !E.nolayout && (!E.view || E.view.auto)) fit(E); });
  renderSide(); redrawAll();
}

/* ------------------------------------------------------------------ stage, panes, view */
function buildStage(){
  const st = $('stage'); st.innerHTML = '';
  S.panes = S.page.elements.map((id, k) => {
    const div = document.createElement('div'); div.className = 'pane';
    div.innerHTML = `<canvas aria-label="Routed layout of ${esc(id)}"></canvas><div class="ph"><div class="lab" data-lab>${esc(id)}</div></div>
      <div class="busy" data-busy>Loading the routed layout&hellip;</div><div class="scale" data-scale></div>
      <div class="pz"><button class="btn" data-z="+" title="Zoom in" aria-label="Zoom in">+</button><button class="btn" data-z="-" title="Zoom out" aria-label="Zoom out">&minus;</button><button class="btn" data-z="fit" title="Fit" aria-label="Fit">&#9635;</button></div>`;
    st.appendChild(div);
    const P = {k, div, cv: div.querySelector('canvas'), busy: div.querySelector('[data-busy]'), lab: div.querySelector('[data-lab]'), scale: div.querySelector('[data-scale]')};
    bindPane(P);
    return P;
  });
  if (window.ResizeObserver){ const ro = new ResizeObserver(() => { if (S.els.length) chooseLayout(); S.els.forEach(E => { if (!E.err && !E.nolayout && E.view && E.view.auto) fit(E); }); redrawAll(); }); ro.observe(st); }
}
function chooseLayout(){
  const st = $('stage'), ok = S.els.filter(E => !E.err && !E.nolayout); if (ok.length < 2){ S.rows = false; return; }
  const r = st.getBoundingClientRect(), n = ok.length, phone = innerWidth <= 980;
  if (!r.width){ S.rows = true; st.classList.add('rows'); return; }
  const side = ok.reduce((a, E) => a + Math.min((r.width / n) / E.W, r.height / E.H), 0);
  const rows = ok.reduce((a, E) => a + Math.min(r.width / E.W, (r.height / n) / E.H), 0);
  S.rows = phone || rows > side; st.classList.toggle('rows', S.rows);
}
function elOfPane(P){ return S.els.find(E => E.k === P.k && !E.err && !E.nolayout); }
function fit(E){
  const r = E.pane.cv.getBoundingClientRect(); const pad = 16, top = 44;
  if (!r.width || !r.height){ E.view = null; return; }
  const s = Math.min((r.width - 2 * pad) / E.W, (r.height - pad - top - 30) / E.H);
  E.view = {s: Math.max(1e-3, s), ox: (r.width - E.W * s) / 2, oy: top + (r.height - top - 30 - E.H * s) / 2, auto: true};
}
const sx = (E, x) => E.view.ox + x * E.view.s;
const sy = (E, y) => E.view.oy + (E.H - y) * E.view.s;
const wx = (E, px) => (px - E.view.ox) / E.view.s;
const wy = (E, py) => E.H - (py - E.view.oy) / E.view.s;
function bindPane(P){
  const cv = P.cv; const pts = new Map(); let last = null, pinch = null, moved = false;
  cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); last = [e.clientX, e.clientY]; moved = false; if (pts.size === 2){ const [a, b] = [...pts.values()]; pinch = Math.hypot(a[0] - b[0], a[1] - b[1]); } cv.classList.add('drag'); });
  cv.addEventListener('pointermove', e => {
    const E = elOfPane(P); if (!E || !E.view) return;
    if (!pts.has(e.pointerId)){ hover(E, e); return; }
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2){ const [a, b] = [...pts.values()]; const d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (pinch){ const r = cv.getBoundingClientRect(); zoomAt(E, (a[0] + b[0]) / 2 - r.left, (a[1] + b[1]) / 2 - r.top, d / pinch); } pinch = d; moved = true; return; }
    if (last){ const dx = e.clientX - last[0], dy = e.clientY - last[1]; if (Math.abs(dx) + Math.abs(dy) > 2) moved = true; E.view.ox += dx; E.view.oy += dy; E.view.auto = false; last = [e.clientX, e.clientY]; draw(E); }
  });
  const up = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch = null; if (!pts.size){ last = null; cv.classList.remove('drag'); } };
  cv.addEventListener('pointerup', e => { const E = elOfPane(P); if (E && E.view && !moved && e.pointerType !== 'mouse') hover(E, e); up(e); });
  cv.addEventListener('pointercancel', up);
  cv.addEventListener('pointerleave', () => { $('tip').hidden = true; });
  cv.addEventListener('wheel', e => { const E = elOfPane(P); if (!E || !E.view) return; e.preventDefault(); const r = cv.getBoundingClientRect(); zoomAt(E, e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0015)); }, {passive: false});
  cv.addEventListener('dblclick', e => { const E = elOfPane(P); if (!E || !E.view) return; const r = cv.getBoundingClientRect(); zoomAt(E, e.clientX - r.left, e.clientY - r.top, 2); });
  P.div.querySelectorAll('[data-z]').forEach(b => b.onclick = () => { const E = elOfPane(P); if (!E) return; const r = cv.getBoundingClientRect();
    if (b.dataset.z === 'fit' || !E.view) fit(E); else zoomAt(E, r.width / 2, r.height / 2, b.dataset.z === '+' ? 2 : 0.5); draw(E); });
}
function zoomAt(E, px, py, f){
  const x = wx(E, px), y = wy(E, py); E.view.s = Math.max(1e-3, Math.min(2000, E.view.s * f));
  E.view.ox = px - x * E.view.s; E.view.oy = py - (E.H - y) * E.view.s; E.view.auto = false; draw(E);
}

/* ------------------------------------------------------------------ rasters */
function raster(E, key, colorOf){
  if (E.raster[key]) return E.raster[key];
  const ppu = Math.min(4, 1600 / Math.max(E.W, E.H)); const RW = Math.max(1, Math.ceil(E.W * ppu)), RH = Math.max(1, Math.ceil(E.H * ppu));
  const acc = new Float32Array(RW * RH * 4);
  for (let i = 0; i < E.n; i++){
    const c = colorOf(i); if (!c) continue;
    const x0 = E.x[i] * ppu, x1 = (E.x[i] + E.w[i]) * ppu, y0 = E.y[i] * ppu, y1 = (E.y[i] + E.h[i]) * ppu;
    const a = (x1 - x0) * (y1 - y0);
    if (x1 - x0 < 1 && y1 - y0 < 1){
      const px = Math.min(RW - 1, Math.floor((x0 + x1) / 2)), py = Math.min(RH - 1, Math.floor((y0 + y1) / 2)), o = ((RH - 1 - py) * RW + px) * 4;
      acc[o] += c[0] * a; acc[o + 1] += c[1] * a; acc[o + 2] += c[2] * a; acc[o + 3] += a;
    } else {
      for (let py = Math.floor(y0); py < Math.min(RH, Math.ceil(y1)); py++) for (let px = Math.floor(x0); px < Math.min(RW, Math.ceil(x1)); px++){
        const ov = (Math.min(x1, px + 1) - Math.max(x0, px)) * (Math.min(y1, py + 1) - Math.max(y0, py)); if (ov <= 0) continue;
        const o = ((RH - 1 - py) * RW + px) * 4; acc[o] += c[0] * ov; acc[o + 1] += c[1] * ov; acc[o + 2] += c[2] * ov; acc[o + 3] += ov;
      }
    }
  }
  const cv = document.createElement('canvas'); cv.width = RW; cv.height = RH;
  const cx = cv.getContext('2d'), im = cx.createImageData(RW, RH);
  for (let p = 0; p < RW * RH; p++){ const a = acc[p * 4 + 3]; if (!a) continue;
    im.data[p * 4] = acc[p * 4] / a; im.data[p * 4 + 1] = acc[p * 4 + 1] / a; im.data[p * 4 + 2] = acc[p * 4 + 2] / a; im.data[p * 4 + 3] = Math.min(255, 70 + 185 * Math.min(1, a)); }
  cx.putImageData(im, 0, 0);
  E.raster[key] = {cv, ppu};
  return E.raster[key];
}
function rtlMatch(E){
  // modules (by index) inside the selected RTL instance path
  const sel = S.rtlEl === E.k ? S.rtlSel : null; if (sel == null) return null;
  const key = 'm:' + sel; if (E._mm && E._mm.key === key) return E._mm.v;
  const mods = E.d.geom.modules, v = new Uint8Array(mods.length);
  for (let i = 0; i < mods.length; i++) if (sel === '' ? mods[i] !== '(unattributed)' : (mods[i] === sel || mods[i].startsWith(sel + '.'))) v[i] = 1;
  E._mm = {key, v}; return v;
}
function baseColorFn(E, mode){
  const grey = hex2rgb(cssv('--cellgrey'));
  if (mode === 'hier'){ const G = E.groups.map(g => hex2rgb(g.color)), iso = S.iso[E.id]; return i => (iso && iso.size && !iso.has(E.grp[i])) ? grey : G[E.grp[i]]; }
  if (mode === 'hold') return i => (E.fl[i] & F.hold) ? hex2rgb(cssv('--hold')) : grey;
  if (mode === 'rtl'){ const mm = rtlMatch(E), A = hex2rgb(cssv('--accent')), B = hex2rgb(cssv('--warn'));
    return i => (mm && mm[E.mod[i]]) ? ((E.fl[i] & F.infer) ? B : A) : grey; }
  return () => grey;
}
function baseKey(E, mode){ return mode + ':' + (mode === 'hier' ? E.depth + ':' + [...(S.iso[E.id] || [])].join(',') : mode === 'rtl' ? (S.rtlEl === E.k ? S.rtlSel : '-') : '') + ':' + cssv('--cellgrey') + cssv('--accent'); }

/* ------------------------------------------------------------------ drawing */
function redrawAll(){ S.els.forEach(E => { if (!E.err && !E.nolayout) draw(E); }); }
function lensState(){
  const T = S.tab;
  if (T === 'layout') return {base: 'hier', overlays: ['macros', 'root']};
  if (T === 'timing') return {base: 'grey', dim: .55, overlays: ['macros', 'paths']};
  if (T === 'arrival') return {base: 'grey', dim: .7, overlays: ['macros', 'flops', 'root']};
  if (T === 'tree') return {base: 'grey', dim: .8, overlays: ['macros', 'ctree', 'root']};
  if (T === 'density') return {base: 'none', overlays: ['heat', 'macros']};
  if (T === 'rtl') return {base: 'rtl', dim: 0, overlays: ['macros']};
  return {base: 'hier', dim: .45, overlays: ['macros']};
}
function draw(E){
  const P = E.pane, cv = P.cv, r = cv.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
  if (!r.width || !r.height) return;
  if (!E.view) fit(E); if (!E.view) return;
  if (cv.width !== Math.round(r.width * dpr) || cv.height !== Math.round(r.height * dpr)){ cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr); }
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.fillStyle = cssv('--canvas'); c.fillRect(0, 0, r.width, r.height);
  const spec = lensState(), s = E.view.s;
  c.strokeStyle = cssv('--die'); c.lineWidth = 1; c.strokeRect(sx(E, 0), sy(E, E.H), E.W * s, E.H * s);
  const co = E.d.geom.core; c.setLineDash([4, 3]); c.strokeStyle = cssv('--core'); c.strokeRect(sx(E, co.x0), sy(E, co.y1), (co.x1 - co.x0) * s, (co.y1 - co.y0) * s); c.setLineDash([]);
  if (spec.base !== 'none'){
    const R = raster(E, baseKey(E, spec.base), baseColorFn(E, spec.base));
    c.globalAlpha = 1 - (spec.dim || 0);
    if (s <= R.ppu * 2.2){ c.imageSmoothingEnabled = s < R.ppu; c.drawImage(R.cv, sx(E, 0), sy(E, E.H), E.W * s, E.H * s); }
    else drawCells(E, c, r, spec.base);
    c.globalAlpha = 1;
  }
  for (const o of spec.overlays || []) OVER[o] && OVER[o](E, c, r, spec);
  P.lab.innerHTML = `<b>${esc(E.d.label + (E.d.role ? ' · ' + E.d.role : ''))}</b><br>${esc(SAFE ? '' : E.d.block + ' · ')}${fmt(E.W, 1)} × ${fmt(E.H, 1)} µm · ${fmt(E.n, 0)} cells` +
    (S.tab === 'tree' ? `<br>${E.cw && S.tview === 'wires' ? `routed clock wires from the DB (${fmt(E.cw.n, 0)} segments)` : 'tree topology: straight lines driver → driven buffer'}` : '') +
    (S.tab === 'rtl' && S.rtlEl === E.k && S.rtlSel != null ? `<br>lit: ${esc(SAFE ? 'selected module' : (S.rtlSel || '(top)'))} · <span style="color:var(--accent)">&#9632;</span> named <span style="color:var(--warn)">&#9632;</span> inferred` : '');
  const bar = niceStep(80 / s); P.scale.textContent = `${bar >= 1 ? fmt(bar, 0) : fmt(bar, 2)} µm ≈ ${fmt(bar * s, 0)} px`;
}
function niceStep(v){ const m = Math.pow(10, Math.floor(Math.log10(v))), e = v / m; return (e >= 5 ? 5 : e >= 2 ? 2 : 1) * m; }
function drawCells(E, c, r, mode){
  const x0 = wx(E, 0) - 6, x1 = wx(E, r.width) + 6, y0 = wy(E, r.height) - 6, y1 = wy(E, 0) + 6, s = E.view.s;
  const fn = baseColorFn(E, mode); let lastC = null; const gap = s > 30 ? 0.6 : 0;
  for (let i = 0; i < E.n; i++){
    const x = E.x[i], y = E.y[i]; if (x > x1 || y > y1 || x + E.w[i] < x0 || y + E.h[i] < y0) continue;
    const col = fn(i); if (!col) continue; if (col !== lastC){ c.fillStyle = rgb(col); lastC = col; }
    c.fillRect(sx(E, x) + gap / 2, sy(E, y + E.h[i]) + gap / 2, Math.max(.6, E.w[i] * s - gap), Math.max(.6, E.h[i] * s - gap));
  }
}
function lvlColor(l, D){ return LVL[Math.min(LVL.length - 1, Math.floor(l / Math.max(1, D) * (LVL.length - 1) + 1e-9))]; }
const OVER = {
  macros(E, c){
    const s = E.view.s, mc = cssv('--macro');
    c.strokeStyle = mc; c.fillStyle = mc + '22'; c.lineWidth = 1;
    for (const m of E.d.geom.macros){ const X = sx(E, m.x0), Y = sy(E, m.y1), w = (m.x1 - m.x0) * s, h = (m.y1 - m.y0) * s; c.fillRect(X, Y, w, h); c.strokeRect(X, Y, w, h);
      if (w > 60 && h > 14 && !SAFE){ c.fillStyle = mc; c.font = '10px ' + cssv('--mono'); c.fillText(m.master.slice(0, Math.floor(w / 6.2)), X + 3, Y + 11); c.fillStyle = mc + '22'; } }
  },
  root(E, c, r){
    const N = E.d.clock_tt.nodes; c.fillStyle = cssv('--tree'); c.strokeStyle = cssv('--canvas');
    for (const n of N) if (n[4] === 'PORT'){ const X = sx(E, n[0]), Y = sy(E, n[1]); c.beginPath(); c.moveTo(X, Y - 7); c.lineTo(X + 7, Y); c.lineTo(X, Y + 7); c.lineTo(X - 7, Y); c.closePath(); c.fill(); c.stroke();
      c.font = '600 10.5px ' + cssv('--mono'); const tw = c.measureText('clock in').width; c.fillText('clock in', X + 9 + tw > r.width - 4 ? X - 9 - tw : X + 9, Y - 6); }
  },
  ctree(E, c){
    const N = E.d.clock_tt.nodes, L = E.d.clock_tt.leaves, D = E.tree.D, s = E.view.s, sel = S.tlevel;
    const on = l => sel == null || l === sel || (sel === 'flops' && false);
    if (E.cw && S.tview === 'wires'){
      const W = E.cw, q = W.q; c.lineWidth = Math.max(0.8, Math.min(2.2, s * 0.25));
      for (let l = 0; l <= D; l++){
        c.strokeStyle = lvlColor(l, D); c.globalAlpha = sel == null ? .85 : (sel === l ? 1 : .07); c.beginPath();
        for (let i = 0; i < W.n; i++){ if (W.lvl[i] !== l) continue; c.moveTo(sx(E, W.x1[i] * q), sy(E, W.y1[i] * q)); c.lineTo(sx(E, W.x2[i] * q), sy(E, W.y2[i] * q)); }
        c.stroke();
      }
    } else {
      c.lineWidth = 1;
      for (let l = 1; l <= D; l++){ c.strokeStyle = lvlColor(l - 1, D); c.globalAlpha = sel == null ? .7 : (sel === l - 1 ? 1 : .07); c.beginPath();
        for (const n of N){ if (n[3] !== l || n[2] < 0) continue; const p = N[n[2]]; c.moveTo(sx(E, p[0]), sy(E, p[1])); c.lineTo(sx(E, n[0]), sy(E, n[1])); } c.stroke(); }
      if (sel != null){ c.globalAlpha = .5; c.strokeStyle = lvlColor(sel, D); c.beginPath(); for (const lf of L){ const p = N[lf[2]]; if (!p || p[3] !== sel) continue; c.moveTo(sx(E, p[0]), sy(E, p[1])); c.lineTo(sx(E, lf[0]), sy(E, lf[1])); } c.stroke(); }
    }
    c.globalAlpha = 1;
    const rr = Math.max(2, Math.min(5, s * 0.6));
    for (const n of N){ if (n[4] === 'PORT') continue; if (sel != null && n[3] !== sel) continue;
      const X = sx(E, n[0]), Y = sy(E, n[1]);
      if (/ICG/.test(n[4])){ c.fillStyle = cssv('--hot'); c.beginPath(); c.moveTo(X, Y - rr - 2); c.lineTo(X + rr + 2, Y); c.lineTo(X, Y + rr + 2); c.lineTo(X - rr - 2, Y); c.closePath(); c.fill(); }
      else { c.fillStyle = lvlColor(n[3], D); c.fillRect(X - rr / 2, Y - rr / 2, rr, rr); } }
  },
  flops(E, c, r, spec){
    const corner = S.ccorner, L = E.d.clock_tt.leaves, ff = E.d.clock_ff_leaves, rng = clockRange(corner), s = E.view.s;
    const sz = Math.max(2, Math.min(6, s * 0.5));
    for (let j = 0; j < L.length; j++){ const l = L[j]; const v = corner === 'ff' ? (ff ? ff[j] : null) : l[3]; if (v == null) continue;
      c.fillStyle = rgb(rampAt(RAMP, (v - rng[0]) / Math.max(1e-6, rng[1] - rng[0]))); c.fillRect(sx(E, l[0]) - sz / 2, sy(E, l[1]) - sz / 2, sz, sz); }
  },
  paths(E, c){
    const which = S.pcorner, P = (which === 'hold' ? E.d.hold_paths : E.d.setup_paths) || [];
    const sel = S.psel[E.id + which] || 0, col = which === 'hold' ? cssv('--hold') : cssv('--path');
    c.strokeStyle = col; c.globalAlpha = .25; c.lineWidth = 1; for (let k = 0; k < P.length; k++) if (k !== sel) poly(E, c, P[k]);
    c.globalAlpha = 1; const p = P[sel]; if (!p) return;
    c.lineWidth = 3; c.strokeStyle = cssv('--canvas'); poly(E, c, p); c.lineWidth = 1.8; c.strokeStyle = col; poly(E, c, p);
    c.fillStyle = col; for (const pt of p.points) if (pt[5] != null){ c.beginPath(); c.arc(sx(E, pt[5]), sy(E, pt[6]), 2.4, 0, 7); c.fill(); }
    const a = p.points.find(q => q[5] != null), b = [...p.points].reverse().find(q => q[5] != null);
    if (a){ c.beginPath(); c.arc(sx(E, a[5]), sy(E, a[6]), 6, 0, 7); c.lineWidth = 2; c.stroke(); lbl(c, sx(E, a[5]) + 8, sy(E, a[6]) - 8, 'launch', col); }
    if (b){ c.strokeRect(sx(E, b[5]) - 6, sy(E, b[6]) - 6, 12, 12); lbl(c, sx(E, b[5]) + 9, sy(E, b[6]) + 14, 'capture  ' + sgn(p.slack, 2) + ' ps', col); }
  },
  heat(E, c){
    const g = E.d.geom.grid, m = S.dmetric, arr = g[m], mx = heatMax(m), s = E.view.s, key = 'heat:' + m + ':' + mx;
    if (!E.raster[key]){ const cv = document.createElement('canvas'); cv.width = g.nx; cv.height = g.ny; const cx = cv.getContext('2d'), im = cx.createImageData(g.nx, g.ny);
      for (let yy = 0; yy < g.ny; yy++) for (let xx = 0; xx < g.nx; xx++){ const v = arr[yy * g.nx + xx]; const o = ((g.ny - 1 - yy) * g.nx + xx) * 4; if (!v) continue;
        const col = rampAt(HEAT, Math.sqrt(Math.min(1, v / mx))); im.data[o] = col[0]; im.data[o + 1] = col[1]; im.data[o + 2] = col[2]; im.data[o + 3] = 235; }
      cx.putImageData(im, 0, 0); E.raster[key] = {cv}; }
    c.imageSmoothingEnabled = false; c.drawImage(E.raster[key].cv, sx(E, 0), sy(E, g.ny * g.bin_um), g.nx * g.bin_um * s, g.ny * g.bin_um * s);
  },
};
function poly(E, c, p){ c.beginPath(); let st = false; for (const pt of p.points){ if (pt[5] == null) continue; const X = sx(E, pt[5]), Y = sy(E, pt[6]); if (!st){ c.moveTo(X, Y); st = true; } else c.lineTo(X, Y); } c.stroke(); }
function lbl(c, x, y, t, col){ c.font = '600 11px ' + cssv('--mono'); const w = c.measureText(t).width; c.fillStyle = cssv('--tipbg'); c.fillRect(x - 3, y - 11, w + 6, 15); c.fillStyle = col; c.fillText(t, x, y); }
function clockRange(corner){
  let lo = Infinity, hi = -Infinity; S.els.forEach(E => { if (E.err || E.nolayout) return; const st = corner === 'ff' ? E.M.ff : E.M.tt; if (!st) return; lo = Math.min(lo, st.p1); hi = Math.max(hi, st.p99); });
  return isFinite(lo) ? [lo, hi] : [0, 1];
}
function heatMax(m){ let mx = 0; S.els.forEach(E => { if (E.err || E.nolayout) return; const a = E.d.geom.grid[m]; const s = a.slice().sort((x, y) => x - y); mx = Math.max(mx, s[Math.floor(s.length * 0.995)] || 0); }); return mx || 1; }

/* ------------------------------------------------------------------ hover */
function hover(E, e){
  const r = E.pane.cv.getBoundingClientRect(), x = wx(E, e.clientX - r.left), y = wy(E, e.clientY - r.top), tip = $('tip');
  if (x < 0 || y < 0 || x > E.W || y > E.H){ tip.hidden = true; return; }
  let html = '';
  if (S.tab === 'timing'){
    const P = (S.pcorner === 'hold' ? E.d.hold_paths : E.d.setup_paths) || [], p = P[S.psel[E.id + S.pcorner] || 0];
    if (p){ let best = null, bd = 64; for (const pt of p.points){ if (pt[5] == null) continue; const d = (sx(E, pt[5]) - (e.clientX - r.left)) ** 2 + (sy(E, pt[6]) - (e.clientY - r.top)) ** 2; if (d < bd){ bd = d; best = pt; } }
      if (best) html = `<div class="n">${esc(SAFE ? best[3] : best[0])}</div><div class="m">${esc(best[3])} · ${best[4] === 'o' ? 'cell delay' : best[4] === 'port' ? 'port' : 'wire delay'} +${fmt(best[2], 2)} ps · arrival ${fmt(best[1], 2)} ps</div>`; }
  }
  if (!html && S.tab === 'tree'){
    const N = E.d.clock_tt.nodes; let best = -1, bd = 100;
    N.forEach((n, i) => { const d = (sx(E, n[0]) - (e.clientX - r.left)) ** 2 + (sy(E, n[1]) - (e.clientY - r.top)) ** 2; if (d < bd){ bd = d; best = i; } });
    if (best >= 0){ const n = N[best]; html = `<div class="n">${esc(SAFE ? n[4] : n[6])}</div><div class="m">${esc(n[4])} · level ${n[3]}${/ICG/.test(n[4]) ? ' · clock gate' : ''} · clock arrival TT ${fmt(n[5], 1)} ps</div>`; }
  }
  if (!html && S.tab === 'density'){ const g = E.d.geom.grid, bx = Math.floor(x / g.bin_um), by = Math.floor(y / g.bin_um), k = by * g.nx + bx;
    html = `<div class="n">bin ${bx},${by} (${fmt(g.bin_um, 1)} µm)</div><div class="m">cell density ${fmt(100 * g.density[k], 1)} % · signal pins ${fmt(g.pins[k], 0)} · routed-wire RUDY ${fmt(g.rudy[k], 2)} µm/µm²</div>`; }
  if (!html){
    const m = E.d.geom.macros.find(q => x >= q.x0 && x <= q.x1 && y >= q.y0 && y <= q.y1);
    const i = hit(E, x, y, 0);
    if (i >= 0 && x >= E.x[i] - 0.5 && x <= E.x[i] + E.w[i] + 0.5 && y >= E.y[i] - 0.5 && y <= E.y[i] + E.h[i] + 0.5){
      const f = E.fl[i], mod = E.d.geom.modules[E.mod[i]], j = E.leafOf[i], L = E.d.clock_tt.leaves;
      const tags = [f & F.flop ? 'flop' : '', f & F.clk ? 'clock tree' : '', f & F.icg ? 'clock gate' : '', f & F.hold ? 'hold-fix buffer' : '', f & F.repair ? 'timing-repair buffer' : '', f & F.lvt ? 'LVT' : '', f & F.slvt ? 'SLVT' : ''].filter(Boolean);
      let rl = '';
      if (j >= 0 && !SAFE){ const R = resolveReg(E, L[j][4]); rl = !E.rtl ? '<br>RTL: loading…' : R ? `<br>register <b>${esc(R.reg)}</b> in ${esc(R.module)}<br>RTL ${esc(R.file)}:${R.line}${R.unresolved ? ' (module only; register line not resolved)' : ''}` : '<br>RTL: not resolved'; }
      html = `<div class="n">${esc(SAFE ? 'cell #' + i : (j >= 0 ? L[j][4] : 'cell #' + i + ' (synthesis-named)'))}</div>
        <div class="m">master ${esc(E.d.geom.masters[E.mas[i]])}${tags.length ? ' · ' + tags.join(' · ') : ''}<br>
        block <span style="color:${E.groups[E.grp[i]].color}">&#9632;</span> ${esc(SAFE ? 'block ' + (E.grp[i] + 1) : E.groups[E.grp[i]].name)}${SAFE ? '' : `<br>module ${esc(mod)}`}${f & F.infer ? ' <i>(inferred: from the flops it connects to)</i>' : ''}${rl}<br>
        at (${fmt(E.x[i], 2)}, ${fmt(E.y[i], 2)}) µm${j >= 0 ? ` · clock TT ${fmt(L[j][3], 1)} ps${E.d.clock_ff_match && E.d.clock_ff_leaves ? ` / FF ${fmt(E.d.clock_ff_leaves[j], 1)} ps` : ''}` : ''}</div>`;
    } else if (m) html = `<div class="n">${esc(SAFE ? 'macro' : m.name)}</div><div class="m">${esc(m.master)} · ${fmt(m.x1 - m.x0, 2)} × ${fmt(m.y1 - m.y0, 2)} µm</div>`;
  }
  if (!html){ tip.hidden = true; return; }
  tip.innerHTML = html; tip.hidden = false;
  const tw = tip.offsetWidth, th = tip.offsetHeight; let X = e.clientX + 14, Y = e.clientY + 14;
  if (X + tw > innerWidth - 6) X = e.clientX - tw - 14; if (Y + th > innerHeight - 6) Y = e.clientY - th - 14;
  tip.style.left = Math.max(4, X) + 'px'; tip.style.top = Math.max(4, Y) + 'px';
}

/* ------------------------------------------------------------------ pills */
function renderPills(){
  $('pills').innerHTML = S.els.map(E => {
    if (E.err) return `<span class="bd ng"><i></i>${esc(E.id)}: not loaded</span>`;
    const M = E.M, st = (M.status || '').toUpperCase();
    return `<span class="chip">${esc(E.d.label)}</span><span class="bd ${st === 'CLOSED' ? 'ok' : 'wn'}"><i></i>${esc(st || '?')}</span>
      <span class="bd ${M.recTT >= 0 ? 'ok' : 'ng'}" title="sign-off record">TT ${sgn(M.recTT)} ps</span><span class="bd ${M.recFF >= 0 ? 'ok' : 'ng'}" title="sign-off record">FF ${sgn(M.recFF)} ps</span>
      <span class="bd ${M.drc === 0 ? 'ok' : 'ng'}">DRC ${esc(M.drc)}</span>`;
  }).join('<span style="width:14px"></span>');
}

/* ------------------------------------------------------------------ syntax highlighting */
const SV_KW = new Set('module endmodule input output inout wire reg logic parameter localparam integer genvar generate endgenerate if else for begin end always always_ff always_comb assign case endcase default function endfunction automatic posedge negedge or and not initial signed unsigned'.split(' '));
const PY_KW = new Set('def return if elif else for in while import from as lambda None True False and or not is class with yield break continue pass raise try except'.split(' '));
function hl(line, py){
  let out = '', i = 0; const n = line.length;
  while (i < n){
    const r = line.slice(i);
    let m;
    if ((!py && r.startsWith('//')) || (py && r[0] === '#')){ out += `<span class="tk-c">${esc(r)}</span>`; break; }
    if ((m = r.match(/^("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/))){ out += `<span class="tk-s">${esc(m[0])}</span>`; i += m[0].length; continue; }
    if (!py && (m = r.match(/^`\w+/))){ out += `<span class="tk-d">${esc(m[0])}</span>`; i += m[0].length; continue; }
    if ((m = r.match(/^(\d+'[sS]?[bBhHdDoO][0-9a-fA-F_xXzZ?]+|'[bBhHdDoO][0-9a-fA-F_xXzZ?]+|0x[0-9a-fA-F]+|\d+(\.\d+)?)/))){ out += `<span class="tk-n">${esc(m[0])}</span>`; i += m[0].length; continue; }
    if ((m = r.match(/^[A-Za-z_$][A-Za-z0-9_$]*/))){ const w = m[0]; out += (py ? PY_KW : SV_KW).has(w) ? `<span class="tk-k">${w}</span>` : esc(w); i += w.length; continue; }
    out += esc(r[0]); i++;
  }
  return out;
}
function codeHtml(text, py, hlRange, id){
  const lines = text.replace(/\n$/, '').split('\n');
  return `<div class="code" ${id ? `id="${id}"` : ''}><table>${lines.map((l, k) => `<tr id="${id || 'c'}-L${k + 1}" class="${hlRange && k + 1 >= hlRange[0] && k + 1 <= hlRange[1] ? 'hl' : ''}"><td class="ln">${k + 1}</td><td class="lc">${hl(l, py)}</td></tr>`).join('')}</table></div>`;
}

/* ------------------------------------------------------------------ facts: key numbers + throughput */
function keyNumbersHtml(E){
  const d = E.d, f = re => factv(d, re), fx = (v, u, dg) => v == null ? '—' : (typeof v === 'number' ? fmt(v, dg == null ? (Number.isInteger(v) ? 0 : 2) : dg) : esc(v)) + (u ? ' ' + u : '');
  const cl = []; for (let i = 0; i + 1 < (d.clocks || []).length; i += 2){ const per = +d.clocks[i + 1]; cl.push(`${esc(d.clocks[i])} ${fmt(per, 3)} ps (${fmt(1e3 / per, 3)} GHz)`); }
  const setupK = (d.facts.find(x => /setup WNS \(sign-off/.test(x.k)) || {}).k || 'setup WNS';
  const rows = [
    ['clocks (sign-off SDC)', cl.length ? cl.join('<br>') : (d.layout ? 'not read (geometry-only export)' : '—')],
    [setupK.replace(' (sign-off record)', '') + ' / FF hold', `<span class="${f(/setup WNS \(sign-off/) >= 0 ? 'ok' : 'ng'}">${fx(f(/setup WNS \(sign-off/), '', 2)}</span> / <span class="${f(/^FF hold WNS \(sign-off/) >= 0 ? 'ok' : 'ng'}">${fx(f(/^FF hold WNS \(sign-off/), '', 2)}</span> ps · DRC ${fx(f(/^DRC$/))}`],
    ['cycles added', fx(f(/^cycles added/))],
    ['std-cell area', fx(f(/^std-cell area/), 'µm²', 0) + (f(/^macro area/) ? ' + macros ' + fx(f(/^macro area/), 'µm²', 0) : '')],
    ['die · utilisation', fx(f(/^die$/), 'µm') + ' · ' + fx(f(/^utilisation/), '%', 1)],
    ['cells · flops', fx(f(/^std cells$/)) + ' · ' + fx(f(/^flops$/))],
    ['LVT / SLVT cells', fx(f(/^LVT cells/), '%', 2) + ' / ' + fx(f(/^SLVT cells/), '%', 2)],
    ['power (vectorless, TT)', fx(f(/^power/), 'mW', 1)]];
  return `<table class="t"><tbody>${rows.map(r => `<tr><td>${r[0]}</td><td class="m">${r[1]}</td></tr>`).join('')}</tbody></table>
    <p class="note" style="margin-top:4px">From the closure record and the routed DB (each number's record is in "all facts" below).</p>`;
}
function tputHtml(E){
  const T = S.tput;
  if (!T) return '<p class="note">Reading the throughput budget&hellip;</p>';
  if (T.status === 'pending') return `<div class="vbox"><span class="lbl pend">pending</span> ${esc(T.path)} is not on origin/main yet${T.error ? ' (' + esc(T.error) + ')' : ''}. This box fills in automatically when it lands.</div>`;
  if (T.status !== 'present') return `<div class="vbox"><span class="lbl bad">${esc(T.status)}</span> ${esc(T.error || '')}</div>`;
  const b = E.d.block, el = (T.elements || {})[b], cls = (T.classes || {})[b] || [], qr = T.qualify_ratio;
  const src = `<p class="note" style="margin-top:6px">${esc(T.path)} @ origin/main ${esc(T.commit || '')}${T.generated_utc ? ' · generated ' + esc(T.generated_utc) : ''}. Rule: ${esc(T.rule || '')}</p>`;
  if (!el) return `<div class="vbox"><span class="lbl unv">not in the budget</span> ${esc(T.path)} has no <code>elements["${esc(b)}"]</code> entry: this block is not on a priced token path yet, so it has no budget and no production-shape throughput bench.${src}</div>`;
  const lab = st => st === 'QUALIFIED' ? 'ver' : st === 'UNQUALIFIED_NO_BENCH' ? 'unv' : 'bad';
  const txt = st => st === 'UNQUALIFIED_NO_BENCH' ? 'UNQUALIFIED · no production-shape bench' : st;
  const L = el.limiting || {};
  const ops = (el.ops || []).map(o => `<div class="fact"><div class="fr"><span><code>${esc(o.op)}</code> · ${esc(o.model)}</span><b><span class="lbl ${lab(o.status)}">${esc(txt(o.status))}</span> ${o.ratio == null ? '' : 'ratio ' + fmt(o.ratio, 3)}</b></div>${o.owner && o.owner !== '-' ? `<div class="note" style="margin:2px 0 0">owner ${esc(o.owner)}</div>` : ''}<div class="src">${esc(o.src || 'no source recorded')}</div></div>`).join('');
  const cl = cls.map(c => `<tr><td class="m">${esc(c.model)} · ${esc(c.cls)}</td><td><span class="lbl ${lab(c.status)}">${esc(txt(c.status))}</span></td><td class="n">${fmt(c.critical_cycles_per_token, 1)}</td><td class="n">${fmt(100 * c.share, 1)} %</td><td class="n">${fmt(100 * c.measured_fraction, 2)} % of ${fmt(c.nodes, 0)}</td></tr>
    ${c.n_unmeasured ? `<tr><td colspan="5" class="note">unmeasured nodes (${c.n_unmeasured}): ${esc((c.unmeasured_nodes || []).join(', '))}</td></tr>` : ''}`).join('');
  return `<div class="vbox"><p><span class="lbl ${lab(el.status)}">${esc(txt(el.status))}</span> ${el.ratio == null ? 'measured / budget ratio: <b>none recorded</b> (status from the token-path class below)' : `measured / budget = <b>${fmt(el.ratio, 3)}</b> (qualifies at ≤ ${fmt(qr, 2)})`}</p>
    <p class="note" style="margin-top:4px">limiting op ${esc(L.op || '—')} in ${esc(L.model || '—')}${L.owner && L.owner !== '-' ? ' · owner ' + esc(L.owner) : ''}</p>
    <div class="facts" style="margin-top:6px">${ops}</div>
    ${cl ? `<div class="tw"><table class="t" style="margin-top:8px"><thead><tr><th>token-path class</th><th>status</th><th class="n">cycles / token</th><th class="n">share</th><th class="n">measured</th></tr></thead><tbody>${cl}</tbody></table></div><p class="note">${esc(cls[0].basis || '')}</p>` : ''}
    ${src}</div>`;
}
/* ---- block diagram */
function diagScopes(E){
  const R = E.rtl, out = [];
  out.push({key: R.tree.k, path: '', label: R.modules[R.tree.k].name + ' (top)'});
  // instances one level down that hold >= 25 % of the placed cells and have sub-blocks of their own
  (R.tree.c || []).forEach(c => { if (R.diagrams[c.k] && !c.bb && ((R.modules[c.k] || {}).inst || []).length >= 3 && E.prefCount(c.p)[0] >= 0.25 * E.n) out.push({key: c.k, path: c.p, label: c.p + ' : ' + c.m}); });
  // generate scopes opened in place (first index only of a for-generate)
  Object.keys(R.diagrams).forEach(k => { const [mk, g] = k.split('|'); if (!g) return; const base = out.find(o => o.key === mk); if (base && !/\[[1-9]\d*\]$/.test(g) && E.prefCount((base.path ? base.path + '.' : '') + g)[0] >= 0.05 * E.n) out.push({key: k, path: (base.path ? base.path + '.' : '') + g, label: (base.path ? base.path + '.' : '') + g + ' (inside)'}); });
  return out;
}
function autoScope(E, scopes){
  // the top, unless it has fewer than 4 real blocks and one instance holds most of the cells: then that instance
  const top = scopes[0], d = E.rtl.diagrams[top.key];
  const real = (d.groups || []).filter(g => !g[0].startsWith('('));
  if (real.length >= 4) return top;
  let best = null; scopes.slice(1).forEach(s => { if (s.key.includes('|')) return; const n = E.prefCount(s.path)[0]; if (!best || n > best.n) best = {s, n}; });
  return best && best.n > 0.5 * E.n ? best.s : top;
}
function renderDiagram(E){
  const box = document.querySelector(`[data-diag="${E.k}"]`); if (!box || !E.rtl) return;
  const scopes = diagScopes(E);
  let sc = scopes.find(s => s.key === S.diag[E.id]) || autoScope(E, scopes);
  const d = E.rtl.diagrams[sc.key];
  if (!d || d.error){ box.innerHTML = `<p class="note">No diagram for this scope${d && d.error ? ': ' + esc(d.error) : ''}.</p>`; return; }
  const pre = sc.path ? sc.path + '.' : '';
  const rest = d.groups.map(g => g[0]).find(g => g.startsWith('(rest of'));
  // block sizes from the layout (cells under each block's instance path)
  const gs = d.groups.map(([g, n, lines]) => {
    const special = g.startsWith('(');
    const cnt = special ? (g === '(module logic)' ? glueCount(E, sc.path) : [0, 0]) : E.prefCount(pre + g);
    return {g, lines, n: cnt[0], inf: cnt[1], special, io: g === '(inputs)' || g === '(outputs)' || g === rest};
  });
  // clock / reset / gate-enable nets are control, not data: hidden from the arrows (counted in the note)
  const CTRL = /(^|\.)(clk|gclk\w*|\w*_clk|leaf_clk|eclk|pclk|\w*rst\w*|rst_n\w*|b_ze|ze_\w*|ze)(\[\d+\])?$/;
  let hidCtrl = 0;
  const dedges = d.edges.map(([a, b, names, bits]) => { const keep = names.filter(([n]) => !CTRL.test(n)); const kb = keep.reduce((t, x) => t + x[1], 0);
    hidCtrl += names.length - keep.length; return [a, b, keep, Math.min(bits, kb || 0) || (keep.length ? bits : 0)]; }).filter(e => e[3] >= 4);
  const thr = new Map(); dedges.forEach(([a, b, , bits]) => { thr.set(a, (thr.get(a) || 0) + bits); thr.set(b, (thr.get(b) || 0) + bits); });
  gs.forEach(x => x.bits = thr.get(x.g) || 0);
  // a for-generate's shared body (g_mac) next to its indexed copies (g_mac[0], g_mac[1]) is loop logic yosys could not
  // pin to one index: not a block of its own
  const loopBody = g => gs.some(y => y.g.startsWith(g + '['));
  const real = gs.filter(x => !x.io && x.bits > 0).sort((a, b) => b.bits - a.bits);
  // up to 8 sub-blocks; the module's own glue logic is drawn as well when it carries data (it is not a sub-block)
  const isGlue = x => x.g === '(module logic)' || (loopBody(x.g) && x.n === 0);
  const subs = real.filter(x => !isGlue(x)), glues = real.filter(isGlue), glue = glues.length;
  const shown = subs.slice(0, 8).concat(glues), shownSet = new Set(shown.map(x => x.g));
  glues.forEach(x => { if (x.g !== '(module logic)') x.loop = true; });
  const others = real.filter(x => !shownSet.has(x.g));
  const OTH = null;   // smaller blocks are listed in the note, not drawn (a merged hub hides the real data flow)
  const IN = rest ? rest : '(inputs)', OUT = rest ? rest + ' ' : '(outputs)';
  const map = g => g === '(inputs)' ? IN : g === '(outputs)' ? OUT : g === rest ? null : shownSet.has(g) ? g : OTH;
  const agg = new Map();
  dedges.forEach(([a, b, names, bits]) => {
    let A = map(a), B = map(b);
    if (a === rest) A = IN; if (b === rest) B = OUT;
    if (!A || !B || A === B) return;
    const k = A + '\u0000' + B; if (!agg.has(k)) agg.set(k, {a: A, b: B, bits: 0, names: new Map()});
    const o = agg.get(k); o.bits += bits; names.forEach(([nm, w]) => o.names.set(nm, (o.names.get(nm) || 0) + w));
  });
  const nodes = [IN, ...shown.map(x => x.g), ...(OTH ? [OTH] : []), OUT];
  const info = new Map(gs.map(x => [x.g, x])); if (OTH) info.set(OTH, {g: OTH, n: others.reduce((s, x) => s + x.n, 0), special: true});
  // layers: longest path from the inputs over forward edges (DFS back-edges dropped)
  const adj = new Map(nodes.map(n => [n, []])); agg.forEach(o => { if (adj.has(o.a) && adj.has(o.b)) adj.get(o.a).push(o.b); });
  const layer = new Map([[IN, 0]]), state = new Map(), back = new Set();
  (function dfs(u){ state.set(u, 1); for (const v of adj.get(u)){ if (state.get(v) === 1){ back.add(u + '\u0000' + v); continue; } if (!state.get(v)) dfs(v); } state.set(u, 2); })(IN);
  nodes.forEach(n => { if (!state.get(n)) (function dfs(u){ state.set(u, 1); for (const v of adj.get(u)){ if (state.get(v) === 1){ back.add(u + '\u0000' + v); continue; } if (!state.get(v)) dfs(v); } state.set(u, 2); })(n); });
  for (let it = 0; it < nodes.length + 2; it++) agg.forEach(o => { if (back.has(o.a + '\u0000' + o.b) || o.b === IN) return; const la = layer.get(o.a); if (la == null) return; if ((layer.get(o.b) ?? -1) < la + 1) layer.set(o.b, la + 1); });
  nodes.forEach(n => { if (!layer.has(n)) layer.set(n, 1); });
  const maxL = Math.max(...nodes.filter(n => n !== OUT).map(n => layer.get(n))) + 1; layer.set(OUT, maxL);
  const cols = []; nodes.forEach(n => { const l = layer.get(n); (cols[l] = cols[l] || []).push(n); });
  // top-to-bottom: one row per layer, so long chains fit a column and phone widths
  const BW = 168, BH = 46, GX = 22, GY = 66, PAD = 14, RB = 46;
  const maxRow = Math.max(...cols.filter(Boolean).map(c => c.length));
  const W = Math.max(maxRow * (BW + GX) - GX, BW) + PAD * 2 + RB, H = cols.length * (BH + GY) - GY + PAD * 2;
  const pos = new Map(); cols.forEach((c, l) => { if (!c) return; const w = c.length * (BW + GX) - GX; c.forEach((n, i) => pos.set(n, {x: PAD + (W - RB - 2 * PAD - w) / 2 + i * (BW + GX), y: PAD + l * (BH + GY)})); });
  const acc = cssv('--accent'), dim = cssv('--dim'), ink = cssv('--ink');
  const edges = [...agg.values()].sort((a, b) => b.bits - a.bits);
  const maxBits = Math.max(1, ...edges.map(e => e.bits));
  let svg = `<defs><marker id="ah${E.k}" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${dim}"/></marker></defs>`;
  const labels = [];
  edges.forEach((o, ei) => {
    const A = pos.get(o.a), B = pos.get(o.b); if (!A || !B) return;
    const fwd = B.y > A.y, sw = 1 + 3 * Math.sqrt(o.bits / maxBits);
    // spread several edges leaving / entering one block across its width
    const ax = A.x + BW / 2 + ((ei % 5) - 2) * 14, bx = B.x + BW / 2 + ((ei % 3) - 1) * 18;
    let path, lx, ly;
    if (fwd){ const y1 = A.y + BH, y2 = B.y - 2; path = `M${ax},${y1} C${ax},${y1 + GY * .55} ${bx},${y2 - GY * .55} ${bx},${y2}`; lx = (ax + bx) / 2 + 6; ly = (y1 + y2) / 2 + 3; }
    else { const xr = W - RB / 2 - (ei % 3) * 8, y1 = A.y + BH / 2, y2 = B.y + BH / 2; path = `M${A.x + BW},${y1} C${xr},${y1} ${xr},${y2} ${B.x + BW + 2},${y2}`; lx = xr - 4; ly = (y1 + y2) / 2; }
    const top = [...o.names.entries()].sort((a, b) => b[1] - a[1]);
    const lab = o.bits < 24 ? '' : SAFE ? `${o.bits} bit` : top.slice(0, 1).map(([n, w]) => `${n.replace(/^.*\./, '')}[${w}]`).join('') + (top.length > 1 ? ` +${top.length - 1}` : '');
    svg += `<g><title>${esc(o.a)} → ${esc(o.b)}: ${o.bits} bits\n${top.slice(0, 12).map(([n, w]) => `${n} [${w}]`).join('\n')}</title><path d="${path}" fill="none" stroke="${dim}" stroke-opacity=".7" stroke-width="${sw.toFixed(1)}" marker-end="url(#ah${E.k})"/></g>`;
    if (lab) labels.push(`<text x="${lx}" y="${ly}" font-size="10" text-anchor="${fwd ? 'start' : 'end'}" fill="${ink}" paint-order="stroke" stroke="${cssv('--panel2')}" stroke-width="3"><title>${esc(o.a)} → ${esc(o.b)}: ${o.bits} bits</title>${esc(lab.length > 38 ? lab.slice(0, 37) + '…' : lab)}</text>`);
  });
  nodes.forEach(n => {
    const p = pos.get(n), it = info.get(n) || {}, io = n === IN || n === OUT;
    const sub = io ? (rest ? 'rest of the module' : n === IN ? 'element pins' : 'element outputs') : it.loop ? 'loop logic shared by the copies' : it.special ? (n === OTH ? fmt(it.n, 0) + ' cells' : 'glue at this level · ' + fmt(it.n, 0) + ' cells') :
      `${instModule(E, sc, n)}${fmt(it.n, 0)} cells${it.inf ? ` (${fmt(100 * it.inf / Math.max(1, it.n), 0)} % inferred)` : ''}`;
    const sub2 = E.rtl.diagrams[sc.key.split('|')[0] + '|' + n] && !sc.key.includes('|') ? '▸ open inside' : '';
    svg += `<g class="blk" data-blk="${esc(n)}" style="cursor:${io ? 'default' : 'pointer'}"><rect x="${p.x}" y="${p.y}" width="${BW}" height="${BH}" rx="8" ${io ? `stroke-dasharray="4 3"` : `stroke="${acc}" stroke-opacity=".55"`}/>
      <text x="${p.x + 8}" y="${p.y + 17}" font-size="12" font-weight="700" fill="${ink}">${esc(SAFE && !io ? 'block' : (io ? (n === IN ? (rest ? 'outside' : 'inputs') : (rest ? 'outside' : 'outputs')) : n)).slice(0, 21)}</text>
      <text x="${p.x + 8}" y="${p.y + 31}" font-size="9.5" fill="${dim}">${esc(sub.slice(0, 27))}</text>${sub2 ? `<text x="${p.x + 8}" y="${p.y + 42}" font-size="9" fill="${acc}">${sub2}</text>` : ''}<title>${esc(n)}</title></g>`;
  });
  svg += labels.join('');
  box.innerHTML = `<div class="crumbs">${scopes.map(s => `<button type="button" data-scope="${esc(s.key)}" aria-pressed="${s.key === sc.key}">${esc(SAFE ? 'scope' : s.label)}</button>`).join('')}</div>
    <div class="tw" style="border:1px solid var(--line);border-radius:8px;background:var(--panel2)"><svg class="diag" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" style="width:${W}px;max-width:none" role="img" aria-label="Block diagram">${svg}</svg></div>
    <p class="note" style="margin-top:4px">${esc(d.module)}${d.prefix ? ' › ' + esc(d.prefix) : ''}: the ${Math.min(8, subs.length)} sub-blocks carrying the most data bits${glue ? ' plus glue logic (this module\'s own, and for-generate loop logic yosys does not pin to one copy)' : ''}${others.length ? `; not drawn: ${others.map(x => x.g).join(', ').slice(0, 200)}` : ''}; ${hidCtrl} clock / reset / enable nets and edges under 4 bits not drawn. Data flows top to bottom (feedback arrows on the right). Arrow width ∝ bits; labels name the widest RTL signal of an arrow of ≥ 24 bits (hover an arrow for all its signals). Click a block for its RTL; ▸ opens a block's inside.</p>`;
  box.querySelectorAll('[data-scope]').forEach(b => b.onclick = () => { S.diag[E.id] = b.dataset.scope; renderDiagram(E); });
  box.querySelectorAll('[data-blk]').forEach(g => g.onclick = () => {
    const n = g.dataset.blk; if (n === IN || n === OUT || n === OTH) return;
    const subKey = sc.key.split('|')[0] + '|' + n;
    if (E.rtl.diagrams[subKey] && !sc.key.includes('|')){ S.diag[E.id] = subKey; renderDiagram(E); return; }
    const it = info.get(n); openRtl(E, pre + n, it && it.lines && it.lines[0] ? it.lines : null);
  });
}
function instModule(E, sc, g){
  const mk = sc.key.split('|')[0], inst = (E.rtl.modules[mk] || {}).inst || [];
  const pre = sc.key.includes('|') ? sc.key.split('|')[1] + '.' : '';
  const hits = inst.filter(x => x[0] === pre + g || x[0].startsWith(pre + g + '.'));
  if (hits.length === 1) return (E.rtl.modules[hits[0][1]] || {}).name + ' · ';
  if (hits.length > 1) return hits.length + ' instances · ';
  return '';
}
function glueCount(E, path){ if (E.nolayout) return [0, 0]; const mods = E.d.geom.modules; let n = 0, inf = 0; for (let i = 0; i < mods.length; i++) if (mods[i] === path){ n += E.d.geom.module_cells[i]; inf += E.inferByMod[i]; } return [n, inf]; }

/* ------------------------------------------------------------------ RTL tab */
function openRtl(E, modPath, lines){
  S.rtlEl = E.k;
  if (modPath != null){ S.rtlSel = modPath; }
  if (lines){ S.rtlFile = lines[0] || S.rtlFile; S.rtlLines = [lines[1], lines[2]]; }
  else if (modPath != null && E.rtl){ const nd = findNode(E.rtl.tree, modPath); if (nd && nd.src){ S.rtlFile = nd.src[0]; S.rtlLines = [nd.src[1], nd.src[1]]; } }
  setTab('rtl');
}
function findNode(n, p){ if (n.p === p) return n; for (const c of n.c || []){ if (p === c.p || p.startsWith(c.p + '.')) { const r = findNode(c, p); if (r) return r; } } return null; }
function rtlSideHtml(){
  const ok = S.els.filter(E => !E.err);
  const E = ok.find(x => x.k === S.rtlEl) || ok[0]; if (!E) return '';
  if (SAFE) return sec('RTL', '<p class="note">The RTL source is not shown in the share-safe view.</p>');
  if (!E.d.rtl_file) return sec(esc(E.d.label) + ' · RTL', `<p class="note">No RTL export for this element: ${esc(E.d.rtl_error || 'the job\'s synthesis config was not found')}.</p><h4 class="sub">Reference model</h4>${refHtml(E)}`);
  if (!E.rtl) return sec('RTL', '<p class="note">Loading the RTL&hellip;</p>');
  S.rtlEl = E.k;
  const R = E.rtl;
  if (!S.rtlFile || !R.files[S.rtlFile]){ const top = R.modules[R.tree.k]; S.rtlFile = top.src[0]; S.rtlLines = [top.src[1], top.src[1]]; }
  const open = new Set(); if (S.rtlSel){ const parts = S.rtlSel.split('.'); } // expansion handled by data-open
  const H = [];
  if (ok.length > 1) H.push(`<div class="seg" role="group" style="margin-bottom:8px">${ok.map(x => `<button type="button" data-rel="${x.k}" aria-pressed="${x.k === E.k}">${esc(short(x))}</button>`).join('')}</div>`);
  H.push(`<h4 class="sub">Structure <span class="u">sub-blocks of the elaborated RTL and the signals between them, bit widths on the arrows</span></h4><div data-diag="${E.k}"></div>`);
  H.push(`<h4 class="sub">Reference model</h4>${refHtml(E)}`);
  H.push(`<h4 class="sub">Module tree and source</h4>`);
  H.push(`<p class="note">${esc(R.top)} elaborated by yosys from the route's own inputs (${R.files ? Object.keys(R.files).length : 0} files, ${esc((R.top_params || []).map(p => p.join('=')).join(' '))}) at <b>${esc((R.source_commit || '').slice(0, 12))}</b>. Counts are placed cells under each instance (inferred cells are those without an RTL name, assigned by their connections).</p>`);
  H.push(`<div class="mtree" id="mtree">${treeHtml(E, R.tree, 0)}</div>`);
  const files = Object.keys(R.files).sort();
  H.push(`<div class="ctl" style="margin-top:10px"><select id="rfile" aria-label="Source file">${files.map(f => `<option ${f === S.rtlFile ? 'selected' : ''}>${esc(f)}</option>`).join('')}</select>
    <span class="note" style="margin:0">${S.rtlLines ? `lines ${S.rtlLines[0]}–${S.rtlLines[1]}` : ''}</span></div>`);
  H.push(codeHtml(R.files[S.rtlFile], false, S.rtlLines, 'rsrc'));
  return sec(esc(E.d.label) + ' · RTL', H.join(''), '');
}
const TREE_OPEN = new Set(['']);
function treeHtml(E, n, depth, parent){
  const [cnt, inf] = E.prefCount(n.p);
  const has = (n.c || []).length, open = TREE_OPEN.has(n.p) || (S.rtlSel && (S.rtlSel === n.p || S.rtlSel.startsWith(n.p ? n.p + '.' : '')) && depth < 12);
  const name = n.p ? (parent ? n.p.slice(parent.length + 1) : n.p) : '(top)';
  let h = `<div class="nd ${S.rtlSel === n.p && S.rtlEl === E.k ? 'on' : ''}" style="padding-left:${8 + depth * 14}px" data-p="${esc(n.p)}"><span class="tw2" data-tog="${esc(n.p)}">${has ? (open ? '▾' : '▸') : ''}</span><span>${esc(name)}</span> <span class="mm">${esc(n.m)}</span><small>${cnt ? fmt(cnt, 0) + (inf ? ` · ${fmt(100 * inf / cnt, 0)}% inf` : '') : n.bb ? 'macro' : '—'}</small></div>`;
  if (has && open){
    // group sibling instances under generate prefixes so the tree reads like the RTL
    h += n.c.map(c => treeHtml(E, c, depth + 1, n.p)).join('');
  }
  return h;
}
function refHtml(E){
  const R = E.d.reference || {}, B = E.d.bench || {};
  const bspec = Object.entries(B.spec || {}).filter(([k, v]) => v != null && v !== '' && !(Array.isArray(v) && !v.length));
  const bst = Object.entries(B.state || {});
  const bench = (bspec.length || bst.length || (B.stages || []).length) ? `<div class="vbox" style="margin-top:6px"><p><b>Bench spec, from the job record</b></p>${bspec.map(([k, v]) => `<p class="note" style="margin:3px 0"><code>${esc(k)}</code>: ${esc(typeof v === 'string' ? v : JSON.stringify(v)).slice(0, 900)}</p>`).join('')}
    ${(B.stages || []).map(x => `<p class="note" style="margin:3px 0"><code>stages.bench</code>: ${esc(JSON.stringify(x)).slice(0, 600)}</p>`).join('')}
    ${bst.map(([k, v]) => `<p class="note" style="margin:3px 0">bench <code>${esc(k)}</code>: ${esc(typeof v === 'object' ? (v.status || v.state || JSON.stringify(v).slice(0, 200)) : v)}</p>`).join('')}</div>` : '';
  if (!R.found) return `<div class="vbox"><span class="lbl unv">no reference model recorded</span> The job's bench spec names no file recognisable as a reference model (oracle / golden / reference)${R.seeds && R.seeds.length ? '; files it names: ' + R.seeds.map(esc).join(', ') : ''}${R.note ? ' (' + esc(R.note) + ')' : ''}.</div>${bench}`;
  const direct = (R.chain || []).length <= 2;
  return `<div class="vbox"><p><span class="lbl ${direct ? 'ver' : 'unv'}">${direct ? 'reference model' : 'candidate reference'}</span> <b>${esc(R.path)}</b> @ ${esc((R.commit || '').slice(0, 10))} · sha256 ${esc((R.sha256 || '').slice(0, 12))}…</p>
    <p class="note" style="margin-top:4px">Located from the bench spec by following file references at the source commit: ${(R.chain || []).map(esc).join(' → ')}</p></div>${bench}
    ${SAFE ? '' : `<details style="margin-top:6px"><summary style="cursor:pointer;font:600 12.5px var(--sans);color:var(--dim)">${esc(R.path)} (${R.text.split('\n').length} lines, exact file at ${esc((R.commit || '').slice(0, 10))})</summary>${codeHtml(R.text, /\.py$/.test(R.path), null, 'ref' + E.k)}</details>`}`;
}
function bindRtlSide(){
  const side = $('side');
  S.els.filter(E => !E.err && E.rtl && document.querySelector(`[data-diag="${E.k}"]`)).forEach(E => renderDiagram(E));
  side.querySelectorAll('[data-rel]').forEach(b => b.onclick = () => { S.rtlEl = +b.dataset.rel; S.rtlFile = null; S.rtlSel = null; renderSide(); redrawAll(); });
  side.querySelectorAll('.mtree [data-tog]').forEach(t => t.onclick = e => { e.stopPropagation(); const p = t.dataset.tog; if (TREE_OPEN.has(p)) TREE_OPEN.delete(p); else TREE_OPEN.add(p); renderSide(); });
  side.querySelectorAll('.mtree .nd').forEach(d => d.onclick = () => {
    const E = S.els.find(x => x.k === S.rtlEl); S.rtlSel = d.dataset.p; TREE_OPEN.add(d.dataset.p);
    const nd = findNode(E.rtl.tree, d.dataset.p); if (nd && nd.src && E.rtl.files[nd.src[0]]){ S.rtlFile = nd.src[0]; S.rtlLines = [nd.src[1], nd.src[1]]; }
    renderSide(); redrawAll();
  });
  const rf = $('rfile'); if (rf) rf.onchange = () => { S.rtlFile = rf.value; S.rtlLines = null; renderSide(); };
  const src = $('rsrc'); if (src && S.rtlLines){ const row = document.getElementById('rsrc-L' + S.rtlLines[0]); if (row) src.scrollTop = Math.max(0, row.offsetTop - 60); }
  const mt = $('mtree'); const on = mt && mt.querySelector('.nd.on'); if (on) mt.scrollTop = Math.max(0, on.offsetTop - 80);
}

/* ------------------------------------------------------------------ side panel per tab */
function short(E){ return ((S.page.short || {})[E.id]) || E.d.label; }
function sec(t, body, sub){ return `<div class="sec"><h3>${t}${sub ? ` <span class="u">${sub}</span>` : ''}</h3>${body}</div>`; }
function renderSide(){
  const T = S.tab, H = [], ok = S.els.filter(E => !E.err && (!LAYOUT_TABS.has(T) || !E.nolayout));
  if (T === 'layout'){
    H.push(sec('Hierarchy', `<div class="ctl"><label for="dep">Depth</label><select id="dep">${[1, 2, 3, 4, 5, 6].map(d => `<option value="${d}" ${ok[0] && ok[0].depth === d ? 'selected' : ''}>${d}</option>`).join('')}</select>
      <span class="note" style="margin:0">Cells coloured by RTL block (module path below the common prefix). Click a block to isolate it.</span></div>`));
    ok.forEach(E => { const st = E.d.geom.stats;
      H.push(sec(esc(E.d.label), `<div class="lg">${E.groups.map((g, i) => `<button type="button" data-g="${i}" data-e="${esc(E.id)}" class="${S.iso[E.id].size ? (S.iso[E.id].has(i) ? 'on' : 'off') : ''}"><i class="sw" style="background:${g.color}"></i><span class="n" title="${esc(g.name)}">${esc(SAFE ? 'block ' + (i + 1) : g.name)}</span><small>${fmt(g.count, 0)} · ${fmt(100 * g.count / E.n, 1)}%</small></button>`).join('')}</div>
        <p class="note" style="margin-top:6px">${SAFE ? '' : `prefix <code>${esc(E.prefix || '(none)')}</code> · `}${fmt(st.named_cells, 0)} cells carry their RTL path in their name (flops); ${fmt(st.inferred_cells, 0)} synthesis-named cells are <b>inferred</b>: they take the block of the flops they connect to (nets ≤ 24 pins); ${fmt(st.unattributed_cells, 0)} unattributed. Filler / tap / decap (${fmt(st.filler_tap_decap, 0)}) not drawn.</p>`, `${fmt(E.n, 0)} cells`)); });
  } else if (T === 'timing'){
    H.push(sec('Worst paths', `<div class="seg" role="group"><button type="button" data-pc="setup" aria-pressed="${S.pcorner === 'setup'}">Setup · TT</button><button type="button" data-pc="hold" aria-pressed="${S.pcorner === 'hold'}">Hold · FF</button></div>
      <p class="note" style="margin-top:6px">Re-timed by the exporter with the closure loop's own sign-off setup (same odb, SPEF, 6_final.sdc and post-SDCs). One worst path per endpoint, worst first.</p>`));
    ok.forEach(E => {
      const P = (S.pcorner === 'hold' ? E.d.hold_paths : E.d.setup_paths) || [], key = E.id + S.pcorner, sel = S.psel[key] || 0, p = P[sel];
      const shortN = s => SAFE ? '' : s.replace(/^.*\.(?=[^.]+\.[^.]+$)/, '…');
      H.push(sec(esc(E.d.label), `<div class="tw"><table class="t"><thead><tr><th>#</th><th class="n">slack ps</th><th>endpoint</th><th class="n">stages</th></tr></thead><tbody>${P.slice(0, 15).map((q, k) =>
        `<tr class="cl ${k === sel ? 'on' : ''}" data-p="${k}" data-e="${esc(E.id)}"><td class="n">${k + 1}</td><td class="n ${q.slack >= 0 ? 'ok' : 'ng'}">${sgn(q.slack)}</td><td class="m">${esc(shortN(q.end))}</td><td class="n">${q.points.filter(t => t[4] === 'o').length}</td></tr>`).join('')}</tbody></table></div>`, `${P.length} paths`));
      if (p){
        const skew = p.capture_clk_ps != null && p.launch_clk_ps != null ? p.capture_clk_ps - p.launch_clk_ps : null;
        H.push(sec(`Path ${sel + 1} stages`, `<dl class="kv"><dt>slack</dt><dd class="${p.slack >= 0 ? 'ok' : 'ng'}">${sgn(p.slack)} ps</dd>${SAFE ? '' : `<dt>from</dt><dd>${esc(p.start)}</dd><dt>to</dt><dd>${esc(p.end)}</dd>`}<dt>clock</dt><dd>${esc(p.clock || '—')}</dd>
          <dt>launch clock pin</dt><dd>${fmt(p.launch_clk_ps, 1)} ps</dd><dt>capture clock pin</dt><dd>${fmt(p.capture_clk_ps, 1)} ps${skew != null ? ` (skew ${sgn(skew, 1)} ps)` : ''}</dd></dl>
          <div class="tw" style="margin-top:6px"><table class="t"><thead><tr><th>pin</th><th>cell</th><th class="n">incr</th><th class="n">arrival</th></tr></thead><tbody>${p.points.map(t =>
            `<tr><td class="m">${esc(SAFE ? (t[4] === 'port' ? 'port' : '') : t[0].replace(/^.*\.(?=[^.]+$)/, '…'))}</td><td class="m">${esc(t[3].replace(/_ASAP7_75t_/, ' '))}${t[4] === 'i' ? ' <span style="color:var(--faint)">in</span>' : ''}</td><td class="n">${fmt(t[2], 2)}</td><td class="n">${fmt(t[1], 2)}</td></tr>`).join('')}</tbody></table></div>
          <p class="note">incr on an output pin is the cell delay; on an input pin the wire delay from the driver. Clock-pin arrivals are the per-flop arrivals of the same corner.</p>`, esc(E.d.label)));
      }
    });
  } else if (T === 'arrival'){
    H.push(sec('Clock arrival', `<div class="seg" role="group"><button type="button" data-cc="tt" aria-pressed="${S.ccorner === 'tt'}">TT (setup corner)</button><button type="button" data-cc="ff" aria-pressed="${S.ccorner === 'ff'}">FF (hold corner)</button></div>
      <div class="ramp" style="background:linear-gradient(90deg,${RAMP.join(',')})"></div><div class="rampl"><span>${fmt(clockRange(S.ccorner)[0], 0)} ps</span><span>one scale for every element (1st–99th pct)</span><span>${fmt(clockRange(S.ccorner)[1], 0)} ps</span></div>
      <p class="note" style="margin-top:6px">Each flop is coloured by when the clock edge reaches its clock pin (propagated clock, extracted parasitics).</p>`));
    H.push(sec('Distribution', histSVG(), 'flops per arrival bin'));
    const st = E => S.ccorner === 'ff' ? E.M.ff : E.M.tt;
    H.push(sec('Arrival statistics', `<div class="tw"><table class="t"><thead><tr><th></th>${ok.map(E => `<th class="n" title="${esc(E.d.label)}">${esc(short(E))}</th>`).join('')}</tr></thead><tbody>${[
      ['flops reached', E => fmt(E.M.leaves, 0)], ['arrival min', E => fmt(st(E) && st(E).min, 1)], ['arrival median', E => fmt(st(E) && st(E).p50, 1)], ['arrival max', E => fmt(st(E) && st(E).max, 1)],
      ['spread max−min', E => fmt(st(E) && st(E).spread, 1)], ['spread p99−p1', E => fmt(st(E) && st(E).p9901, 1)], ['hold-fix buffers', E => fmt(E.M.holdBuf, 0) + ` (${fmt(E.M.holdPct, 1)}%)`]]
      .map(([k, f]) => `<tr><td>${k}</td>${ok.map(E => `<td class="n">${f(E)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
      <p class="note">ps at the ${S.ccorner.toUpperCase()} corner, including the source latency the sign-off SDC puts on the clock port.</p>`));
    ok.forEach(E => {
      const by = new Map(), ffl = E.d.clock_ff_match ? E.d.clock_ff_leaves : null;
      for (let i = 0; i < E.n; i++){ const j = E.leafOf[i]; if (j < 0) continue; const v = S.ccorner === 'ff' ? (ffl ? ffl[j] : null) : E.d.clock_tt.leaves[j][3]; if (v == null) continue; const g = E.grp[i]; if (!by.has(g)) by.set(g, []); by.get(g).push(v); }
      const rows = [...by.entries()].map(([g, a]) => [g, latStats(a)]).sort((x, y) => y[1].n - x[1].n);
      H.push(sec('Arrival by block', `<div class="tw"><table class="t"><thead><tr><th>block</th><th class="n">flops</th><th class="n">p1</th><th class="n">median</th><th class="n">p99</th></tr></thead><tbody>${rows.map(([g, t]) =>
        `<tr><td class="m"><i class="sw" style="background:${E.groups[g].color}"></i> ${esc(SAFE ? 'block ' + (g + 1) : E.groups[g].name)}</td><td class="n">${fmt(t.n, 0)}</td><td class="n">${fmt(t.p1, 0)}</td><td class="n">${fmt(t.p50, 0)}</td><td class="n">${fmt(t.p99, 0)}</td></tr>`).join('')}</tbody></table></div>`, esc(E.d.label) + ' · ' + S.ccorner.toUpperCase() + ' ps'));
    });
  } else if (T === 'tree'){
    const anyW = ok.some(E => E.cw);
    H.push(sec('Clock tree', `<div class="seg" role="group"><button type="button" data-tv="wires" aria-pressed="${S.tview === 'wires'}" ${anyW ? '' : 'disabled'}>Routed wires</button><button type="button" data-tv="topo" aria-pressed="${S.tview === 'topo'}">Topology</button></div>
      <p class="note" style="margin-top:6px"><b>Routed wires</b> are the clock nets' wire segments read from the final DB. <b>Topology</b> draws a straight line from each driver to each driven buffer (connectivity only, not geometry). Colour = buffer level from the clock pin (level 0 = the pin's net); red diamonds are clock gates (ICG). Click a level to light only it.</p>
      <div style="display:flex;height:10px;border-radius:3px;overflow:hidden;margin-top:6px">${LVL.map(c => `<i style="flex:1;background:${c}"></i>`).join('')}</div><div class="rampl"><span>level 0 (pin)</span><span>deepest level</span></div>`));
    ok.forEach(E => H.push(sec(esc(E.d.label), dendroHtml(E), `${fmt(E.tree.lv.reduce((a, r) => a + r.bufs, 0), 0)} buffers / gates · ${E.tree.D} levels · ${fmt(E.M.leaves, 0)} flops`)));
  } else if (T === 'density'){
    const mx = heatMax(S.dmetric);
    H.push(sec('Density / congestion', `<div class="seg" role="group"><button type="button" data-dm="density" aria-pressed="${S.dmetric === 'density'}">Cell density</button><button type="button" data-dm="pins" aria-pressed="${S.dmetric === 'pins'}">Pin density</button><button type="button" data-dm="rudy" aria-pressed="${S.dmetric === 'rudy'}">Routed-wire RUDY</button></div>
      <div class="ramp" style="background:linear-gradient(90deg,${HEAT.join(',')})"></div><div class="rampl"><span>0</span><span>sqrt scale, shared</span><span>${S.dmetric === 'density' ? fmt(100 * mx, 0) + ' %' : S.dmetric === 'pins' ? fmt(mx, 0) + ' pins' : fmt(mx, 2) + ' µm/µm²'}</span></div>
      <p class="note" style="margin-top:6px">${S.dmetric === 'density' ? 'Placed std-cell area per bin over bin area (macros excluded).' : S.dmetric === 'pins' ? 'Signal pins of placed cells per bin.' : 'Each net\'s final routed wire length spread evenly over its pin bounding box (RUDY with routed length): an estimate of routing demand, not global-route overflow; the routed DBs carry no GRT congestion map.'}</p>`));
    ok.forEach(E => { const a = E.d.geom.grid[S.dmetric], s = a.slice().sort((x, y) => x - y), f = v => S.dmetric === 'density' ? fmt(100 * v, 1) + ' %' : S.dmetric === 'pins' ? fmt(v, 0) : fmt(v, 2) + ' µm/µm²';
      H.push(sec(esc(E.d.label), `<dl class="kv"><dt>median bin</dt><dd>${f(pct(s, .5))}</dd><dt>99th pct bin</dt><dd>${f(pct(s, .99))}</dd><dt>max bin</dt><dd>${f(s[s.length - 1])}</dd><dt>bin</dt><dd>${fmt(E.d.geom.grid.bin_um, 1)} µm</dd></dl>`)); });
  } else if (T === 'rtl'){
    H.push(rtlSideHtml());
  } else if (T === 'facts'){
    ok.forEach(E => H.push(sec(esc(E.d.label) + ' · key numbers', keyNumbersHtml(E))));
    ok.forEach(E => H.push(sec(esc(E.d.label) + ' · throughput qualification', tputHtml(E), 'budget vs measured; QUALIFIED if measured / budget ≤ 1.10')));
    const fv = f => typeof f.v === 'number' ? (Number.isInteger(f.v) ? fmt(f.v, 0) : Math.abs(f.v) >= 1000 ? fmt(f.v, 0) : fmt(f.v, 2)) : esc(f.v);
    ok.forEach(E => H.push(sec(esc(E.d.label) + ' · all facts', `<div class="facts">${E.d.facts.map(f =>
      `<div class="fact"><div class="fr"><span>${esc(f.k)}</span><b>${fv(f)}${f.unit ? ' ' + esc(f.unit) : ''}</b></div>${f.note ? `<div class="note" style="margin:2px 0 0">${esc(f.note)}</div>` : ''}${SAFE || !f.src ? '' : `<div class="src">${esc(f.src)}</div>`}</div>`).join('')}</div>`, esc(SAFE ? '' : E.d.block || ''))));
  }
  if (!SAFE && T !== 'rtl') H.push(sec('Source', ok.map(E => `<dl class="kv"><dt>${esc(E.d.label)}</dt><dd>${esc(E.d.db)}<br>job ${esc(E.d.job)} on ${esc(E.d.host)} · exported ${esc((E.d.exported_at || '').slice(0, 16).replace('T', ' '))}${E.d.note ? '<br>' + esc(E.d.note) : ''}</dd></dl>`).join('') +
    `<p class="note" style="margin-top:6px">Exporters: tools/explorer_elem_export.py, tools/explorer_elem/or_export.py (OpenROAD, the job's own w18_sta_tt/ff.tcl setup), tools/explorer_elem/rtl_export.py (yosys, the route's config.mk).</p>`));
  $('side').innerHTML = H.join('');
  bindSide();
}
function dendroHtml(E){
  const T = E.tree, rows = T.lv.filter(r => r.bufs || r.flops || r.macros), maxB = Math.max(1, ...rows.map(r => r.bufs + r.flops));
  const W = 150, RH = 17, Hh = (rows.length + 1) * RH + 8, X0 = 30, BW = 110;
  let s = `<text x="0" y="12" font-size="10.5" font-family="var(--mono)" fill="${cssv('--ink')}">pin</text><text x="${X0}" y="12" font-size="10" font-family="var(--mono)" fill="${cssv('--dim')}">clock input · fanout ${T.rootFan}</text>`;
  rows.forEach((r, i) => {
    const y = (i + 1) * RH + 4, l = r.lvl, col = lvlColor(Math.min(l, T.D), T.D);
    const bw = r.bufs ? Math.max(2, BW * Math.log10(1 + r.bufs) / Math.log10(1 + maxB)) : 0, fw = r.flops ? Math.max(2, BW * Math.log10(1 + r.flops) / Math.log10(1 + maxB)) : 0;
    s += `<g data-lvl="${l}" style="cursor:pointer"><rect x="0" y="${y - 12}" width="${W}" height="${RH - 1}" fill="${S.tlevel === l ? cssv('--hover') : 'transparent'}"/>
      <text x="2" y="${y}" font-size="10.5" font-family="var(--mono)" fill="${cssv('--dim')}">L${l}</text>
      ${r.bufs ? `<rect x="${X0}" y="${y - 9}" width="${bw.toFixed(1)}" height="9" fill="${col}"/>` : ''}${r.flops ? `<rect x="${X0}" y="${y - 2}" width="${fw.toFixed(1)}" height="3" fill="${cssv('--ink')}" opacity=".55"/>` : ''}
      <text x="${X0 + BW + 6}" y="${y}" font-size="10" font-family="var(--mono)" fill="${cssv('--ink')}">${r.bufs ? `${r.bufs} buf` : ''}${r.icg ? ` · <tspan fill="${cssv('--hot')}">${r.icg} ICG</tspan>` : ''}${r.bufs ? ` · fo ${fmt(r.fanAvg, 1)}/${r.fanMax}` : ''}${r.flops ? ` → ${fmt(r.flops, 0)} flops` : ''}${r.macros ? ` · ${r.macros} macro` : ''}</text><title>level ${l}: ${r.bufs} buffers/gates (${r.icg} ICG), fanout avg ${fmt(r.fanAvg, 2)} max ${r.fanMax}; ${r.flops} flops and ${r.macros} macro clock pins driven from the level above</title></g>`;
  });
  return `<svg class="dendro" viewBox="0 0 ${W + 236} ${Hh}" role="img" aria-label="Clock tree levels">${s}</svg>
    <p class="note">Each row is one level below the clock pin: bar = buffers / gates at that level (log scale), thin bar = flops whose clock pin hangs off a buffer of the level above, fo = fanout avg/max of that level's buffers. ${T.icgNodes.length} clock gates in total.</p>`;
}
function bindSide(){
  const side = $('side');
  const dep = $('dep'); if (dep) dep.onchange = () => { S.depth = +dep.value; lsSet('depth.' + S.page.id, S.depth); S.iso = {}; regroup(); renderSide(); redrawAll(); };
  side.querySelectorAll('[data-g]').forEach(b => b.onclick = () => { const s = S.iso[b.dataset.e], i = +b.dataset.g; if (s.has(i)) s.delete(i); else s.add(i); renderSide(); redrawAll(); });
  side.querySelectorAll('[data-pc]').forEach(b => b.onclick = () => { S.pcorner = b.dataset.pc; lsSet('pcorner', S.pcorner); renderSide(); redrawAll(); });
  side.querySelectorAll('[data-cc]').forEach(b => b.onclick = () => { S.ccorner = b.dataset.cc; lsSet('ccorner', S.ccorner); renderSide(); redrawAll(); });
  side.querySelectorAll('[data-dm]').forEach(b => b.onclick = () => { S.dmetric = b.dataset.dm; lsSet('dmetric', S.dmetric); renderSide(); redrawAll(); });
  side.querySelectorAll('[data-tv]').forEach(b => b.onclick = () => { S.tview = b.dataset.tv; lsSet('tview', S.tview); renderSide(); redrawAll(); });
  side.querySelectorAll('[data-lvl]').forEach(g => g.onclick = () => { const l = +g.dataset.lvl; S.tlevel = S.tlevel === l ? null : l; renderSide(); redrawAll(); });
  side.querySelectorAll('tr[data-p]').forEach(tr => tr.onclick = () => { S.psel[tr.dataset.e + S.pcorner] = +tr.dataset.p; renderSide(); redrawAll(); });
  if (S.tab === 'rtl') bindRtlSide();
}
function histSVG(){
  const ok = S.els.filter(E => !E.err && (S.ccorner === 'ff' ? E.M.ff : E.M.tt));
  if (!ok.length) return '<p class="note">No clock arrivals exported for this corner.</p>';
  let lo = Infinity, hi = -Infinity, clip = 0; ok.forEach(E => { const s = S.ccorner === 'ff' ? E.M.ff : E.M.tt; lo = Math.min(lo, s.p1); hi = Math.max(hi, s.max); });
  lo = Math.floor(lo - 0.04 * (hi - lo)); ok.forEach(E => { const s = S.ccorner === 'ff' ? E.M.ff : E.M.tt; clip += s.sorted.filter(v => v < lo).length; });
  const NB = 48, W = 400, Hh = 64, bw = (hi - lo) / NB || 1;
  const rows = ok.map((E, k) => { const s = (S.ccorner === 'ff' ? E.M.ff : E.M.tt).sorted, h = new Array(NB).fill(0); s.forEach(v => h[Math.max(0, Math.min(NB - 1, Math.floor((v - lo) / bw)))]++); const m = Math.max(...h);
    const col = k === 0 ? cssv('--accent') : cssv('--story');
    return `<text x="0" y="${k * (Hh + 22) + 11}" font-size="11" font-family="var(--mono)" fill="${cssv('--ink')}">${esc(E.d.label)}  (${fmt(s.length, 0)} flops)</text>` +
      h.map((v, i) => v ? `<rect x="${(i / NB * W).toFixed(1)}" y="${(k * (Hh + 22) + 16 + Hh * (1 - v / m)).toFixed(1)}" width="${(W / NB - 1).toFixed(1)}" height="${(Hh * v / m).toFixed(1)}" fill="${col}"><title>${fmt(lo + i * bw, 0)}–${fmt(lo + (i + 1) * bw, 0)} ps: ${v} flops</title></rect>` : '').join(''); }).join('');
  const Ht = ok.length * (Hh + 22) + 18;
  const ticks = [lo, (lo + hi) / 2, hi].map((v, i) => `<text x="${[0, W / 2, W][i]}" y="${Ht - 2}" font-size="10.5" font-family="var(--mono)" fill="${cssv('--dim')}" text-anchor="${['start', 'middle', 'end'][i]}">${fmt(v, 0)} ps</text>`).join('');
  return `<svg class="hist" viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Clock arrival histogram">${rows}${ticks}</svg><p class="note">Shared x axis from the lowest 1st percentile; each row scaled to its own tallest bin.${clip ? ` ${fmt(clip, 0)} flop${clip > 1 ? 's' : ''} earlier than ${fmt(lo, 0)} ps counted in the first bin (min ${ok.map(E => fmt((S.ccorner === 'ff' ? E.M.ff : E.M.tt).min, 0)).join(' / ')} ps).` : ''}</p>`;
}

init().catch(e => { $('sum').textContent = 'Failed to load: ' + e; });
})();

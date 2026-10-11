/* Chip Explorer element page (/explorer/element/): the REAL routed layout of a closed element, exported from its final
   routed DB by tools/explorer_elem_export.py (OpenROAD in the ORFS container, the closure loop's own sign-off STA setup).
   Engineering lenses over one canvas per element (hierarchy, timing, clock, density, facts) and a stepped
   "How it works" story over the same canvas (explorer_story.js idiom: one event per step, plain caption, one
   "why it matters" fact, a link to the lens that shows the engineering detail).
   URL: ?p=<page id> | ?e=<element id>; #story-<page or element id> opens the story; ?safe=1 hides raw names. */
(function(){
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const fmt = (n, d = 1) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
const sgn = (n, d = 2) => n == null || isNaN(n) ? '—' : (n >= 0 ? '+' : '−') + fmt(Math.abs(n), d);
const QP = new URLSearchParams(location.search);
const SAFE = QP.get('safe') === '1';
const QS = SAFE ? '?safe=1' : '';
const reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
function lsGet(k, d){ try { const v = localStorage.getItem('otx.elem.' + k); return v == null ? d : v; } catch (e) { return d; } }
function lsSet(k, v){ try { localStorage.setItem('otx.elem.' + k, v); } catch (e) {} }
function cssv(n){ return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
function hex2rgb(h){ h = h.replace('#', ''); if (h.length === 3) h = h.split('').map(x => x + x).join(''); return [0, 2, 4].map(i => parseInt(h.substr(i, 2), 16)); }

const F = {flop: 1, clk: 2, lvt: 4, hold: 8, repair: 16, infer: 32, slvt: 64, icg: 128};
const LENSES = [['hier', 'Hierarchy'], ['timing', 'Timing'], ['clock', 'Clock'], ['density', 'Density'], ['facts', 'Facts']];
const PAL = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#17becf', '#bcbd22', '#8c6bb1'];
const OTHER = '#7c86a6', UNATTR = '#4a5678';
// sequential ramp (viridis-like, readable on both themes) for clock arrival and heat maps
const RAMP = ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'];
const HEAT = ['#0d0887', '#7e03a8', '#cc4778', '#f89540', '#f0f921'];
function rampAt(r, t){ t = Math.max(0, Math.min(1, t)); const k = t * (r.length - 1), i = Math.min(r.length - 2, Math.floor(k)), f = k - i;
  const a = hex2rgb(r[i]), b = hex2rgb(r[i + 1]); return [0, 1, 2].map(j => Math.round(a[j] + (b[j] - a[j]) * f)); }
const rgb = c => `rgb(${c[0]},${c[1]},${c[2]})`;

const S = {page: null, els: [], lens: lsGet('lens', 'hier'), mode: 'eng', step: 0, timer: null, depth: null, iso: {},
  pcorner: lsGet('pcorner', 'setup'), ccorner: lsGet('ccorner', 'tt'), dmetric: lsGet('dmetric', 'density'), psel: {}, hoverEl: null};
if (!LENSES.some(l => l[0] === S.lens)) S.lens = 'hier';

/* ------------------------------------------------------------------ theme */
function applyTheme(){ const t = lsGet('theme', ''); if (t) document.documentElement.setAttribute('data-theme', t); else document.documentElement.removeAttribute('data-theme'); }
applyTheme();
$('theme').onclick = () => {
  const dark = cssv('color-scheme') !== 'light';
  lsSet('theme', dark ? 'light' : 'dark'); applyTheme(); S.els.forEach(E => E.raster = {}); redrawAll(); renderSide();
};

/* ------------------------------------------------------------------ load */
async function getJSON(u){ const r = await fetch(u, {cache: 'no-store'}); if (!r.ok) throw new Error(r.status + ' ' + u); return r.json(); }
async function getBin(u){ const r = await fetch(u, {cache: 'no-store'}); if (!r.ok) throw new Error(r.status + ' ' + u); return r.arrayBuffer(); }

async function init(){
  let pages = {pages: [], elements: {}};
  try { pages = await getJSON('pages.json' + QS); } catch (e) {}
  const hashStory = (location.hash.match(/^#story-(.+)$/) || [])[1];
  let pid = QP.get('p'), eid = QP.get('e');
  if (!pid && !eid && hashStory){ if (pages.pages.some(p => p.id === hashStory)) pid = hashStory; else eid = hashStory; }
  let page = pages.pages.find(p => p.id === pid);
  if (!page && eid){
    page = pages.pages.find(p => p.elements.length === 1 && p.elements[0] === eid) ||
      {id: eid, elements: [eid], title: null, summary: null, story: null, alias: {a: eid}};
  }
  if (!page) page = pages.pages[0];
  if (!page){ $('sum').textContent = 'No element pages are installed yet.'; return; }
  S.page = page;
  document.title = page.title ? page.title.slice(0, 40) : 'Element Layout';
  $('title').textContent = page.title || page.elements.join(' vs ');
  buildStage();
  const els = await Promise.all(page.elements.map(async (id, k) => {
    try {
      const d = await getJSON('data/' + encodeURIComponent(id) + '.json' + QS);
      const buf = await getBin('data/' + encodeURIComponent(d.geom.cells.file));
      return prep(id, d, buf, k);
    } catch (e) { return {id, err: String(e), k}; }
  }));
  S.els = els;
  if (!page.title) $('title').textContent = els.map(E => E.d ? E.d.label : E.id).join(' vs ');
  $('sum').textContent = page.summary || (els[0].d && els[0].d.summary) || '';
  els.forEach(E => { const p = E.pane; p.busy.textContent = E.err ? 'Could not load ' + E.id + ': ' + E.err : ''; p.busy.hidden = !E.err; });
  chooseLayout();
  S.depth = +lsGet('depth.' + page.id, 0) || null;
  regroup();
  renderLensBar(); renderPills(); renderSide();
  els.forEach(E => { if (!E.err){ fit(E); } });
  redrawAll();
  const wantStory = hashStory && (hashStory === page.id || page.elements.includes(hashStory));
  if (page.story && page.story.length && (wantStory || lsGet('mode', 'eng') === 'story')) startStory(); else $('how').hidden = !(page.story && page.story.length);
  if (!(page.story && page.story.length)) $('how').hidden = true;
}

function prep(id, d, buf, k){
  const g = d.geom, n = g.cells.n, q = g.quantum_dbu / g.dbu_per_um;
  const u16 = (o) => new Uint16Array(buf, o, n);
  const xq = u16(0), yq = u16(2 * n), wq = u16(4 * n), hq = u16(6 * n);
  const E = {id, d, k, n, mod: u16(8 * n), mas: u16(10 * n), fl: new Uint8Array(buf, 12 * n, n),
    x: new Float32Array(n), y: new Float32Array(n), w: new Float32Array(n), h: new Float32Array(n),
    W: g.die.x1 - g.die.x0, H: g.die.y1 - g.die.y0, raster: {}, view: null};
  for (let i = 0; i < n; i++){ E.x[i] = xq[i] * q; E.y[i] = yq[i] * q; E.w[i] = wq[i] / 1000; E.h[i] = hq[i] / 1000; }
  E.pane = S.panes[k];
  buildIndex(E);
  // flop cell -> clock leaf (by centre), so hover and the clock lens can name a flop
  const L = d.clock_tt.leaves; E.leafOf = new Int32Array(n).fill(-1);
  for (let j = 0; j < L.length; j++){ if (L[j][5]) continue; const c = hit(E, L[j][0], L[j][1], F.flop); if (c >= 0) E.leafOf[c] = j; }
  // clock arrival at the launching / capturing flop's clock pin, from the per-flop arrivals of the path's own corner
  const byName = new Map(); L.forEach((l, j) => byName.set(l[4], j));
  const ffl = d.clock_ff_match ? d.clock_ff_leaves : null;
  const ck = (pin, ff) => { const j = byName.get(String(pin).replace(/\/[^/]*$/, '')); return j == null ? null : ff ? (ffl ? ffl[j] : null) : L[j][3]; };
  (d.setup_paths || []).forEach(p => { p.launch_clk_ps = ck(p.start, false); p.capture_clk_ps = ck(p.end, false); });
  (d.hold_paths || []).forEach(p => { p.launch_clk_ps = ck(p.start, true); p.capture_clk_ps = ck(p.end, true); });
  E.M = metrics(E);
  return E;
}

/* spatial index: CSR buckets of cell centres */
function buildIndex(E){
  const bs = Math.max(0.5, Math.max(E.W, E.H) / 600); const nx = Math.ceil(E.W / bs) + 1, ny = Math.ceil(E.H / bs) + 1;
  const cnt = new Uint32Array(nx * ny + 1);
  const b = new Uint32Array(E.n);
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
    const b = yy * nx + xx;
    for (let p = start[b]; p < start[b + 1]; p++){
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
  let hold = 0, repair = 0, clk = 0; for (let i = 0; i < E.n; i++){ const f = E.fl[i]; if (f & F.hold) hold++; if (f & F.repair) repair++; if (f & F.clk) clk++; }
  const fact = k => { const f = d.facts.find(x => x.k === k); return f ? f.v : null; };
  const h0 = d.hold_paths && d.hold_paths[0], hold0 = h0 ? {launch: h0.launch_clk_ps, capture: h0.capture_clk_ps, skew: h0.capture_clk_ps - h0.launch_clk_ps} : null;
  // clock arrival by top-level RTL block (first name component of the flop)
  const byTop = {}; flopIdx.forEach(j => { const k = L[j][4].split('.')[0]; (byTop[k] = byTop[k] || []).push(L[j][3]); });
  const clkByTop = {}; for (const k in byTop) clkByTop[k] = latStats(byTop[k]);
  return {label: d.label, n: E.n, flops: st.flops, leaves: flopIdx.length, macros: d.geom.macros.length, W: E.W, H: E.H,
    hold0, clkByTop, clkNodes: N.filter(x => x[4] !== 'PORT').length, clkDepth: N.reduce((m, x) => Math.max(m, x[3]), 0), tt, ff,
    holdBuf: hold, holdPct: 100 * hold / E.n, repair, setupWNS: d.setup_paths && d.setup_paths[0] ? d.setup_paths[0].slack : null,
    holdWNS: d.hold_paths && d.hold_paths[0] ? d.hold_paths[0].slack : null, recTT: fact('TT setup WNS (sign-off record)'),
    recFF: fact('FF hold WNS (sign-off record)'), drc: fact('DRC'), util: fact('utilisation (std+macro)/core'), lvt: fact('LVT cells'),
    area: st.std_cell_area_um2, core: st.core_area_um2, job: d.job, status: fact('status')};
}

/* ------------------------------------------------------------------ hierarchy groups */
function regroup(){
  S.els.forEach(E => {
    if (E.err) return;
    const mods = E.d.geom.modules, cnt = E.d.geom.module_cells;
    const comps = mods.map(m => m === '(unattributed)' ? null : m.split('.'));
    // common prefix of all attributed module paths
    let pre = null; comps.forEach(c => { if (!c) return; if (pre == null) pre = c.slice(); else { let i = 0; while (i < pre.length && i < c.length && pre[i] === c[i]) i++; pre.length = i; } });
    pre = pre || [];
    E.prefix = pre.join('.');
    const keyAt = (c, dep) => c ? (c.slice(pre.length, pre.length + dep).join('.') || '(top)') : '(unattributed)';
    let depth = S.depth;
    if (!depth){
      depth = 1;
      for (let dep = 1; dep <= 6; dep++){ const m = new Map(); comps.forEach((c, i) => { const k = keyAt(c, dep); m.set(k, (m.get(k) || 0) + cnt[i]); });
        const big = [...m.values()].filter(v => v >= E.n * 0.01).length; depth = dep; if (big >= 5) break; }
    }
    E.depth = depth;
    const tot = new Map(); comps.forEach((c, i) => { const k = keyAt(c, depth); tot.set(k, (tot.get(k) || 0) + cnt[i]); });
    const order = [...tot.entries()].filter(([k]) => k !== '(unattributed)').sort((a, b) => b[1] - a[1]);
    const top = order.slice(0, PAL.length).map(x => x[0]);
    const groups = top.map((k, i) => ({name: k, color: PAL[i], count: tot.get(k)}));
    const rest = order.slice(PAL.length).reduce((s, x) => s + x[1], 0);
    if (rest) groups.push({name: '(other ' + (order.length - PAL.length) + ' blocks)', color: OTHER, count: rest});
    if (tot.get('(unattributed)')) groups.push({name: '(unattributed)', color: UNATTR, count: tot.get('(unattributed)')});
    const gi = new Map(groups.map((g, i) => [g.name, i]));
    const modGroup = comps.map((c, i) => { const k = keyAt(c, depth); return gi.has(k) ? gi.get(k) : (k === '(unattributed)' ? gi.get('(unattributed)') : gi.get(groups.find(g => g.name.startsWith('(other')).name)); });
    E.groups = groups; E.modGroup = modGroup;
    E.grp = new Uint8Array(E.n); for (let i = 0; i < E.n; i++) E.grp[i] = modGroup[E.mod[i]];
    E.raster = {};
    if (!S.iso[E.id]) S.iso[E.id] = new Set();
  });
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
  if (window.ResizeObserver){ const ro = new ResizeObserver(() => { const was = S.rows; if (S.els.length) chooseLayout(); if (S.mode === 'story' && was !== S.rows) showStep(); S.els.forEach(E => { if (!E.err && E.view && E.view.auto) fit(E); }); redrawAll(); }); ro.observe(st); }
}
/* side by side or stacked: whichever draws the blocks larger (long thin blocks stack) */
function chooseLayout(){
  const st = $('stage'), ok = S.els.filter(E => !E.err); if (ok.length < 2){ S.rows = false; return; }
  const r = st.getBoundingClientRect(), n = ok.length, phone = innerWidth <= 980;
  const side = ok.reduce((a, E) => a + Math.min((r.width / n) / E.W, r.height / E.H), 0);
  const rows = ok.reduce((a, E) => a + Math.min(r.width / E.W, (r.height / n) / E.H), 0);
  S.rows = phone || rows > side; st.classList.toggle('rows', S.rows);
}
function elOfPane(P){ return S.els.find(E => E.k === P.k && !E.err); }
function fit(E){
  const r = E.pane.cv.getBoundingClientRect(); const pad = 16, top = 44;
  const s = Math.min((r.width - 2 * pad) / E.W, (r.height - pad - top - 30) / E.H);
  E.view = {s: Math.max(1e-3, s), ox: (r.width - E.W * s) / 2, oy: top + (r.height - top - 30 - E.H * s) / 2, auto: true};
}
function fitBox(E, x0, y0, x1, y1){
  const r = E.pane.cv.getBoundingClientRect(); const w = Math.max(5, x1 - x0), h = Math.max(5, y1 - y0);
  const s = Math.min((r.width - 40) / w, (r.height - 120) / h, 400);
  E.view = {s, ox: r.width / 2 - ((x0 + x1) / 2) * s, oy: (r.height - 70) / 2 - (E.H - (y0 + y1) / 2) * s + 20, auto: false};
}
const sx = (E, x) => E.view.ox + x * E.view.s;
const sy = (E, y) => E.view.oy + (E.H - y) * E.view.s;
const wx = (E, px) => (px - E.view.ox) / E.view.s;
const wy = (E, py) => E.H - (py - E.view.oy) / E.view.s;

function bindPane(P){
  const cv = P.cv; const pts = new Map(); let last = null, pinch = null, moved = false;
  cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); last = [e.clientX, e.clientY]; moved = false; if (pts.size === 2){ const [a, b] = [...pts.values()]; pinch = Math.hypot(a[0] - b[0], a[1] - b[1]); } cv.classList.add('drag'); });
  cv.addEventListener('pointermove', e => {
    const E = elOfPane(P); if (!E) return;
    if (!pts.has(e.pointerId)){ hover(E, e); return; }
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2){ const [a, b] = [...pts.values()]; const d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (pinch){ const r = cv.getBoundingClientRect(); zoomAt(E, (a[0] + b[0]) / 2 - r.left, (a[1] + b[1]) / 2 - r.top, d / pinch); } pinch = d; moved = true; return; }
    if (last){ const dx = e.clientX - last[0], dy = e.clientY - last[1]; if (Math.abs(dx) + Math.abs(dy) > 2) moved = true; E.view.ox += dx; E.view.oy += dy; E.view.auto = false; last = [e.clientX, e.clientY]; draw(E); }
  });
  const up = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch = null; if (!pts.size){ last = null; cv.classList.remove('drag'); } };
  cv.addEventListener('pointerup', e => { const E = elOfPane(P); if (E && !moved && e.pointerType !== 'mouse') hover(E, e); up(e); });
  cv.addEventListener('pointercancel', up);
  cv.addEventListener('pointerleave', () => { $('tip').hidden = true; });
  cv.addEventListener('wheel', e => { const E = elOfPane(P); if (!E) return; e.preventDefault(); const r = cv.getBoundingClientRect(); zoomAt(E, e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0015)); }, {passive: false});
  cv.addEventListener('dblclick', e => { const E = elOfPane(P); if (!E) return; const r = cv.getBoundingClientRect(); zoomAt(E, e.clientX - r.left, e.clientY - r.top, 2); });
  P.div.querySelectorAll('[data-z]').forEach(b => b.onclick = () => { const E = elOfPane(P); if (!E) return; const r = cv.getBoundingClientRect();
    if (b.dataset.z === 'fit') fit(E); else zoomAt(E, r.width / 2, r.height / 2, b.dataset.z === '+' ? 2 : 0.5); draw(E); });
}
function zoomAt(E, px, py, f){
  const x = wx(E, px), y = wy(E, py); E.view.s = Math.max(1e-3, Math.min(2000, E.view.s * f));
  E.view.ox = px - x * E.view.s; E.view.oy = py - (E.H - y) * E.view.s; E.view.auto = false; draw(E);
}

/* ------------------------------------------------------------------ rasters (zoomed-out view of every placed cell) */
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
function groupRGB(E){ return E.groups.map(g => hex2rgb(g.color)); }
function baseColorFn(E, mode){
  const grey = hex2rgb(cssv('--cellgrey'));
  if (mode === 'hier'){ const G = groupRGB(E), iso = S.iso[E.id]; const dim = grey.map(v => v);
    return i => (iso && iso.size && !iso.has(E.grp[i])) ? dim : G[E.grp[i]]; }
  if (mode === 'hold') return i => (E.fl[i] & F.hold) ? hex2rgb(cssv('--hold')) : grey;
  return () => grey;
}
function baseKey(E, mode){ return mode + ':' + (mode === 'hier' ? E.depth + ':' + [...(S.iso[E.id] || [])].join(',') : '') + ':' + cssv('--cellgrey'); }

/* ------------------------------------------------------------------ drawing */
function redrawAll(){ S.els.forEach(E => { if (!E.err) draw(E); }); }
function lensState(){
  // the story drives the same renderer through a "spec"; engineering mode derives it from the lens
  if (S.mode === 'story'){ const st = S.page.story[S.step]; return Object.assign({base: 'hier', dim: 0, overlays: []}, st.draw || {}); }
  const L = S.lens;
  if (L === 'hier') return {base: 'hier', dim: 0, overlays: ['macros', 'root']};
  if (L === 'timing') return {base: 'grey', dim: .55, overlays: ['macros', 'paths']};
  if (L === 'clock') return {base: 'grey', dim: .7, overlays: ['macros', 'tree', 'flops', 'root']};
  if (L === 'density') return {base: 'none', overlays: ['heat', 'macros']};
  return {base: 'hier', dim: .45, overlays: ['macros']};
}
function draw(E){
  const P = E.pane, cv = P.cv, r = cv.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
  if (!E.view) fit(E);
  if (cv.width !== Math.round(r.width * dpr) || cv.height !== Math.round(r.height * dpr)){ cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr); }
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.fillStyle = cssv('--canvas'); c.fillRect(0, 0, r.width, r.height);
  const spec = lensState(), s = E.view.s;
  // die + core
  c.strokeStyle = cssv('--die'); c.lineWidth = 1; c.strokeRect(sx(E, 0), sy(E, E.H), E.W * s, E.H * s);
  const co = E.d.geom.core; c.setLineDash([4, 3]); c.strokeStyle = cssv('--core'); c.strokeRect(sx(E, co.x0), sy(E, co.y1), (co.x1 - co.x0) * s, (co.y1 - co.y0) * s); c.setLineDash([]);
  // base layer
  if (spec.base !== 'none'){
    const mode = spec.base;
    const R = raster(E, baseKey(E, mode), baseColorFn(E, mode));
    c.globalAlpha = 1 - (spec.dim || 0);
    if (s <= R.ppu * 2.2){ c.imageSmoothingEnabled = s < R.ppu; c.drawImage(R.cv, sx(E, 0), sy(E, E.H), E.W * s, E.H * s); }
    else drawCells(E, c, r, mode);
    c.globalAlpha = 1;
  }
  for (const o of spec.overlays || []) OVER[o] && OVER[o](E, c, r, spec);
  // labels
  const lab = E.d.label + (E.d.role ? ' · ' + E.d.role : '');
  P.lab.innerHTML = `<b>${esc(lab)}</b><br>${esc(SAFE ? '' : E.d.block + ' · ')}${fmt(E.W, 1)} × ${fmt(E.H, 1)} µm · ${fmt(E.n, 0)} cells`;
  const bar = niceStep(80 / s); P.scale.textContent = `${bar >= 1 ? fmt(bar, 0) : fmt(bar, 2)} µm ≈ ${fmt(bar * s, 0)} px`;
}
function niceStep(v){ const m = Math.pow(10, Math.floor(Math.log10(v))), e = v / m; return (e >= 5 ? 5 : e >= 2 ? 2 : 1) * m; }
function drawCells(E, c, r, mode){
  const x0 = wx(E, 0) - 6, x1 = wx(E, r.width) + 6, y0 = wy(E, r.height) - 6, y1 = wy(E, 0) + 6, s = E.view.s;
  const fn = baseColorFn(E, mode); let lastC = null;
  const gap = s > 30 ? 0.6 : 0;
  for (let i = 0; i < E.n; i++){
    const x = E.x[i], y = E.y[i]; if (x > x1 || y > y1 || x + E.w[i] < x0 || y + E.h[i] < y0) continue;
    const col = fn(i); if (!col) continue; if (col !== lastC){ c.fillStyle = rgb(col); lastC = col; }
    c.fillRect(sx(E, x) + gap / 2, sy(E, y + E.h[i]) + gap / 2, Math.max(.6, E.w[i] * s - gap), Math.max(.6, E.h[i] * s - gap));
  }
}
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
  tree(E, c, r, spec){
    const N = E.d.clock_tt.nodes, s = E.view.s; c.strokeStyle = cssv('--tree'); c.globalAlpha = spec.treeAlpha || .55; c.lineWidth = 1;
    c.beginPath(); for (const n of N){ if (n[2] < 0) continue; const p = N[n[2]]; c.moveTo(sx(E, p[0]), sy(E, p[1])); c.lineTo(sx(E, n[0]), sy(E, n[1])); } c.stroke();
    c.globalAlpha = 1; c.fillStyle = cssv('--tree');
    const rr = Math.max(1.5, Math.min(4, s * 0.6)); for (const n of N) if (n[4] !== 'PORT') c.fillRect(sx(E, n[0]) - rr / 2, sy(E, n[1]) - rr / 2, rr, rr);
    if (spec.leafLines){ c.globalAlpha = .15; c.beginPath(); for (const l of E.d.clock_tt.leaves){ const p = N[l[2]]; if (!p) continue; c.moveTo(sx(E, p[0]), sy(E, p[1])); c.lineTo(sx(E, l[0]), sy(E, l[1])); } c.stroke(); c.globalAlpha = 1; }
  },
  flops(E, c, r, spec){
    const corner = spec.corner || S.ccorner, L = E.d.clock_tt.leaves, ff = E.d.clock_ff_leaves, rng = clockRange(corner), s = E.view.s;
    const sz = Math.max(2, Math.min(6, s * 0.5));
    for (let j = 0; j < L.length; j++){ const l = L[j]; const v = corner === 'ff' ? (ff ? ff[j] : null) : l[3]; if (v == null) continue;
      c.fillStyle = rgb(rampAt(RAMP, (v - rng[0]) / Math.max(1e-6, rng[1] - rng[0]))); c.fillRect(sx(E, l[0]) - sz / 2, sy(E, l[1]) - sz / 2, sz, sz); }
  },
  holdbuf(E, c){
    const s = E.view.s, sz = Math.max(2, Math.min(5, s * 0.4)); c.fillStyle = cssv('--hold');
    for (let i = 0; i < E.n; i++) if (E.fl[i] & F.hold) c.fillRect(sx(E, E.x[i] + E.w[i] / 2) - sz / 2, sy(E, E.y[i] + E.h[i] / 2) - sz / 2, sz, sz);
  },
  paths(E, c, r, spec){
    const which = spec.pcorner || S.pcorner, P = (which === 'hold' ? E.d.hold_paths : E.d.setup_paths) || [];
    const sel = spec.pathIdx != null ? spec.pathIdx : (S.psel[E.id + which] || 0);
    const col = which === 'hold' ? cssv('--hold') : cssv('--path');
    if (!spec.only){ c.strokeStyle = col; c.globalAlpha = .25; c.lineWidth = 1; for (let k = 0; k < P.length; k++) if (k !== sel) poly(E, c, P[k]); }
    c.globalAlpha = 1; const p = P[sel]; if (!p) return;
    c.lineWidth = 3; c.strokeStyle = cssv('--canvas'); poly(E, c, p); c.lineWidth = 1.8; c.strokeStyle = col; poly(E, c, p);
    c.fillStyle = col; for (const pt of p.points) if (pt[5] != null){ c.beginPath(); c.arc(sx(E, pt[5]), sy(E, pt[6]), 2.4, 0, 7); c.fill(); }
    const a = p.points.find(q => q[5] != null), b = [...p.points].reverse().find(q => q[5] != null);
    if (a){ c.beginPath(); c.arc(sx(E, a[5]), sy(E, a[6]), 6, 0, 7); c.lineWidth = 2; c.stroke(); lbl(c, sx(E, a[5]) + 8, sy(E, a[6]) - 8, 'launch', col); }
    if (b){ c.strokeRect(sx(E, b[5]) - 6, sy(E, b[6]) - 6, 12, 12); lbl(c, sx(E, b[5]) + 9, sy(E, b[6]) + 14, 'capture  ' + sgn(p.slack, 2) + ' ps', col); }
  },
  heat(E, c, r, spec){
    const g = E.d.geom.grid, m = spec.metric || S.dmetric, arr = g[m === 'pins' ? 'pins' : m === 'rudy' ? 'rudy' : 'density'], mx = heatMax(m), s = E.view.s;
    const key = 'heat:' + m + ':' + mx;
    if (!E.raster[key]){ const cv = document.createElement('canvas'); cv.width = g.nx; cv.height = g.ny; const cx = cv.getContext('2d'), im = cx.createImageData(g.nx, g.ny);
      for (let yy = 0; yy < g.ny; yy++) for (let xx = 0; xx < g.nx; xx++){ const v = arr[yy * g.nx + xx]; const o = ((g.ny - 1 - yy) * g.nx + xx) * 4; if (!v){ continue; }
        const col = rampAt(HEAT, Math.sqrt(Math.min(1, v / mx))); im.data[o] = col[0]; im.data[o + 1] = col[1]; im.data[o + 2] = col[2]; im.data[o + 3] = 235; }
      cx.putImageData(im, 0, 0); E.raster[key] = {cv}; }
    c.imageSmoothingEnabled = false; c.drawImage(E.raster[key].cv, sx(E, 0), sy(E, g.ny * g.bin_um), g.nx * g.bin_um * s, g.ny * g.bin_um * s);
  },
  outline(E, c){ c.strokeStyle = cssv('--story'); c.lineWidth = 2.5; c.strokeRect(sx(E, 0) - 3, sy(E, E.H) - 3, E.W * E.view.s + 6, E.H * E.view.s + 6); },
};
function poly(E, c, p){ c.beginPath(); let st = false; for (const pt of p.points){ if (pt[5] == null) continue; const X = sx(E, pt[5]), Y = sy(E, pt[6]); if (!st){ c.moveTo(X, Y); st = true; } else c.lineTo(X, Y); } c.stroke(); }
function lbl(c, x, y, t, col){ c.font = '600 11px ' + cssv('--mono'); const w = c.measureText(t).width; c.fillStyle = cssv('--tipbg'); c.fillRect(x - 3, y - 11, w + 6, 15); c.fillStyle = col; c.fillText(t, x, y); }
function clockRange(corner){
  // one colour scale across every element on the page so the spreads compare directly (1st..99th percentile; outliers saturate)
  let lo = Infinity, hi = -Infinity; S.els.forEach(E => { if (E.err) return; const st = corner === 'ff' ? E.M.ff : E.M.tt; if (!st) return; lo = Math.min(lo, st.p1); hi = Math.max(hi, st.p99); });
  return isFinite(lo) ? [lo, hi] : [0, 1];
}
function heatMax(m){ let mx = 0; S.els.forEach(E => { if (E.err) return; const g = E.d.geom.grid, a = g[m === 'pins' ? 'pins' : m === 'rudy' ? 'rudy' : 'density']; const s = a.slice().sort((x, y) => x - y); mx = Math.max(mx, s[Math.floor(s.length * 0.995)] || 0); }); return mx || 1; }

/* ------------------------------------------------------------------ hover */
function hover(E, e){
  const r = E.pane.cv.getBoundingClientRect(), x = wx(E, e.clientX - r.left), y = wy(E, e.clientY - r.top), tip = $('tip');
  if (x < 0 || y < 0 || x > E.W || y > E.H){ tip.hidden = true; return; }
  let html = '';
  const spec = lensState();
  if ((spec.overlays || []).includes('paths')){
    const which = spec.pcorner || S.pcorner, P = (which === 'hold' ? E.d.hold_paths : E.d.setup_paths) || [], p = P[spec.pathIdx != null ? spec.pathIdx : (S.psel[E.id + which] || 0)];
    if (p){ let best = null, bd = 64; for (const pt of p.points){ if (pt[5] == null) continue; const d = (sx(E, pt[5]) - (e.clientX - r.left)) ** 2 + (sy(E, pt[6]) - (e.clientY - r.top)) ** 2; if (d < bd){ bd = d; best = pt; } }
      if (best) html = `<div class="n">${esc(SAFE ? best[3] : best[0])}</div><div class="m">${esc(best[3])} · ${best[4] === 'o' ? 'cell delay' : best[4] === 'port' ? 'port' : 'wire delay'} +${fmt(best[2], 2)} ps · arrival ${fmt(best[1], 2)} ps</div>`; }
  }
  if (!html){
    const m = E.d.geom.macros.find(q => x >= q.x0 && x <= q.x1 && y >= q.y0 && y <= q.y1);
    const i = hit(E, x, y, 0);
    if (i >= 0 && x >= E.x[i] - 0.5 && x <= E.x[i] + E.w[i] + 0.5 && y >= E.y[i] - 0.5 && y <= E.y[i] + E.h[i] + 0.5){
      const f = E.fl[i], mod = E.d.geom.modules[E.mod[i]], j = E.leafOf[i], L = E.d.clock_tt.leaves;
      const tags = [f & F.flop ? 'flop' : '', f & F.clk ? 'clock tree' : '', f & F.icg ? 'clock gate' : '', f & F.hold ? 'hold-fix buffer' : '', f & F.repair ? 'timing-repair buffer' : '', f & F.lvt ? 'LVT' : '', f & F.slvt ? 'SLVT' : ''].filter(Boolean);
      html = `<div class="n">${esc(SAFE ? 'cell #' + i : (j >= 0 ? L[j][4] : 'cell #' + i + ' (synthesis-named)'))}</div>
        <div class="m">master ${esc(E.d.geom.masters[E.mas[i]])}${tags.length ? ' · ' + tags.join(' · ') : ''}<br>
        block <span style="color:${E.groups[E.grp[i]].color}">&#9632;</span> ${esc(SAFE ? E.groups[E.grp[i]].name.replace(/[^.]+/g, '·') : E.groups[E.grp[i]].name)}${SAFE ? '' : `<br>module ${esc(mod)}`}${f & F.infer ? ' <i>(inferred from connected flops)</i>' : ''}<br>
        at (${fmt(E.x[i], 2)}, ${fmt(E.y[i], 2)}) µm · ${fmt(E.w[i], 3)} × ${fmt(E.h[i], 3)} µm
        ${j >= 0 ? `<br>clock arrival TT ${fmt(L[j][3], 1)} ps${E.d.clock_ff_match && E.d.clock_ff_leaves ? ` · FF ${fmt(E.d.clock_ff_leaves[j], 1)} ps` : ''}` : ''}</div>`;
    } else if (m) html = `<div class="n">${esc(SAFE ? 'macro' : m.name)}</div><div class="m">${esc(m.master)} · ${fmt(m.x1 - m.x0, 2)} × ${fmt(m.y1 - m.y0, 2)} µm</div>`;
    else if ((spec.overlays || []).includes('heat')){ const g = E.d.geom.grid, bx = Math.floor(x / g.bin_um), by = Math.floor(y / g.bin_um), k = by * g.nx + bx;
      html = `<div class="n">bin ${bx},${by} (${fmt(g.bin_um, 1)} µm)</div><div class="m">cell density ${fmt(100 * g.density[k], 1)} % · signal pins ${fmt(g.pins[k], 0)} · routed-wire RUDY ${fmt(g.rudy[k], 2)} µm/µm²</div>`; }
  }
  if (!html){ tip.hidden = true; return; }
  tip.innerHTML = html; tip.hidden = false;
  const tw = tip.offsetWidth, th = tip.offsetHeight; let X = e.clientX + 14, Y = e.clientY + 14;
  if (X + tw > innerWidth - 6) X = e.clientX - tw - 14; if (Y + th > innerHeight - 6) Y = e.clientY - th - 14;
  tip.style.left = Math.max(4, X) + 'px'; tip.style.top = Math.max(4, Y) + 'px';
}

/* ------------------------------------------------------------------ header, pills, lens bar */
function renderLensBar(){
  $('lenses').innerHTML = LENSES.map(([k, t]) => `<button type="button" data-lens="${k}" aria-pressed="${S.lens === k && S.mode === 'eng'}">${t}</button>`).join('');
  $('lenses').querySelectorAll('[data-lens]').forEach(b => b.onclick = () => { if (S.mode === 'story') stopStory(); setLens(b.dataset.lens); });
}
function setLens(k){ S.lens = k; lsSet('lens', k); renderLensBar(); renderSide(); redrawAll(); }
function renderPills(){
  $('pills').innerHTML = S.els.map(E => {
    if (E.err) return `<span class="bd ng"><i></i>${esc(E.id)}: not loaded</span>`;
    const M = E.M; const st = (M.status || '').toUpperCase();
    return `<span class="chip">${esc(E.d.label)}</span><span class="bd ${st === 'CLOSED' ? 'ok' : 'wn'}"><i></i>${esc(st || '?')}</span>
      <span class="bd ${M.recTT >= 0 ? 'ok' : 'ng'}" title="sign-off record">TT ${sgn(M.recTT)} ps</span><span class="bd ${M.recFF >= 0 ? 'ok' : 'ng'}" title="sign-off record">FF ${sgn(M.recFF)} ps</span>
      <span class="bd ${M.drc === 0 ? 'ok' : 'ng'}">DRC ${esc(M.drc)}</span>`;
  }).join('<span style="width:14px"></span>');
}

/* ------------------------------------------------------------------ side panel per lens */
function short(E){ return ((S.page.short || {})[E.id]) || E.d.label; }
function sec(t, body, sub){ return `<div class="sec"><h3>${t}${sub ? ` <span class="u">${sub}</span>` : ''}</h3>${body}</div>`; }
function renderSide(){
  const H = [];
  const ok = S.els.filter(E => !E.err);
  if (S.lens === 'hier'){
    const maxD = 6;
    H.push(sec('Hierarchy', `<div class="ctl"><label for="dep">Depth</label><select id="dep">${[1, 2, 3, 4, 5, 6].slice(0, maxD).map(d => `<option value="${d}" ${ok[0] && ok[0].depth === d ? 'selected' : ''}>${d}</option>`).join('')}</select>
      <span class="note" style="margin:0">Cells coloured by RTL block (module path below the common prefix). Click a block to isolate it.</span></div>`));
    ok.forEach(E => {
      const st = E.d.geom.stats;
      H.push(sec(esc(E.d.label), `<div class="lg">${E.groups.map((g, i) => `<button type="button" data-g="${i}" data-e="${esc(E.id)}" class="${S.iso[E.id].size ? (S.iso[E.id].has(i) ? 'on' : 'off') : ''}"><i class="sw" style="background:${g.color}"></i><span class="n" title="${esc(g.name)}">${esc(SAFE ? 'block ' + (i + 1) : g.name)}</span><small>${fmt(g.count, 0)} · ${fmt(100 * g.count / E.n, 1)}%</small></button>`).join('')}</div>
        <p class="note" style="margin-top:6px">${SAFE ? '' : `prefix <code>${esc(E.prefix || '(none)')}</code> · `}${fmt(st.named_cells, 0)} cells carry their RTL path in their name (flops); ${fmt(st.inferred_cells, 0)} synthesis-named cells take the block of the flops they connect to (nets ≤ 24 pins); ${fmt(st.unattributed_cells, 0)} unattributed. Filler / tap / decap (${fmt(st.filler_tap_decap, 0)}) not drawn.</p>`, `${fmt(E.n, 0)} cells`));
    });
  } else if (S.lens === 'timing'){
    H.push(sec('Worst paths', `<div class="seg" role="group"><button type="button" data-pc="setup" aria-pressed="${S.pcorner === 'setup'}">Setup · TT</button><button type="button" data-pc="hold" aria-pressed="${S.pcorner === 'hold'}">Hold · FF</button></div>
      <p class="note" style="margin-top:6px">Re-timed by the exporter with the closure loop's own sign-off setup (same odb, SPEF, 6_final.sdc and post-SDCs). One worst path per endpoint, worst first. The line joins the placed pins in path order.</p>`));
    ok.forEach(E => {
      const P = (S.pcorner === 'hold' ? E.d.hold_paths : E.d.setup_paths) || [], key = E.id + S.pcorner, sel = S.psel[key] || 0, p = P[sel];
      const short = s => SAFE ? '' : s.replace(/^.*\.(?=[^.]+\.[^.]+$)/, '…');
      H.push(sec(esc(E.d.label), `<div class="tw"><table class="t"><thead><tr><th>#</th><th class="n">slack ps</th><th>endpoint</th><th class="n">stages</th></tr></thead><tbody>${P.slice(0, 15).map((q, k) =>
        `<tr class="cl ${k === sel ? 'on' : ''}" data-p="${k}" data-e="${esc(E.id)}"><td class="n">${k + 1}</td><td class="n ${q.slack >= 0 ? 'ok' : 'ng'}">${sgn(q.slack)}</td><td class="m">${esc(short(q.end))}</td><td class="n">${q.points.filter(t => t[4] === 'o').length}</td></tr>`).join('')}</tbody></table></div>`,
        `${P.length} paths`));
      if (p){
        const skew = p.capture_clk_ps != null && p.launch_clk_ps != null ? p.capture_clk_ps - p.launch_clk_ps : null;
        H.push(sec(`Path ${sel + 1} stages`, `<dl class="kv"><dt>slack</dt><dd class="${p.slack >= 0 ? 'ok' : 'ng'}">${sgn(p.slack)} ps</dd>${SAFE ? '' : `<dt>from</dt><dd>${esc(p.start)}</dd><dt>to</dt><dd>${esc(p.end)}</dd>`}<dt>clock</dt><dd>${esc(p.clock || '—')}</dd>
          <dt>launch clock</dt><dd>${fmt(p.launch_clk_ps, 1)} ps</dd><dt>capture clock</dt><dd>${fmt(p.capture_clk_ps, 1)} ps${skew != null ? ` (skew ${sgn(skew, 1)} ps)` : ''}</dd></dl>
          <div class="tw" style="margin-top:6px"><table class="t"><thead><tr><th>pin</th><th>cell</th><th class="n">incr</th><th class="n">arrival</th></tr></thead><tbody>${p.points.map(t =>
            `<tr><td class="m">${esc(SAFE ? (t[4] === 'port' ? 'port' : '') : t[0].replace(/^.*\.(?=[^.]+$)/, '…'))}</td><td class="m">${esc(t[3].replace(/_ASAP7_75t_/, ' '))}${t[4] === 'o' ? '' : t[4] === 'i' ? ' <span style="color:var(--faint)">in</span>' : ''}</td><td class="n">${fmt(t[2], 2)}</td><td class="n">${fmt(t[1], 2)}</td></tr>`).join('')}</tbody></table></div>
          <p class="note">incr on an output pin is the cell delay; on an input pin it is the wire (net) delay from the driver.</p>`, esc(E.d.label)));
      }
    });
  } else if (S.lens === 'clock'){
    H.push(sec('Clock arrival', `<div class="seg" role="group"><button type="button" data-cc="tt" aria-pressed="${S.ccorner === 'tt'}">TT (setup corner)</button><button type="button" data-cc="ff" aria-pressed="${S.ccorner === 'ff'}">FF (hold corner)</button></div>
      <div class="ramp" style="background:linear-gradient(90deg,${RAMP.join(',')})"></div><div class="rampl"><span>${fmt(clockRange(S.ccorner)[0], 0)} ps</span><span>one scale for every element (1st–99th pct)</span><span>${fmt(clockRange(S.ccorner)[1], 0)} ps</span></div>
      <p class="note" style="margin-top:6px">Each flop is coloured by when the clock edge reaches its clock pin (propagated clock, extracted parasitics). Lines are the buffer tree topology (driver to driven buffer), not the routed wires.</p>`));
    H.push(sec('Distribution', histSVG(), 'flops per arrival bin'));
    H.push(sec('Clock tree', `<div class="tw"><table class="t"><thead><tr><th></th>${ok.map(E => `<th class="n" title="${esc(E.d.label)}">${esc(short(E))}</th>`).join('')}</tr></thead><tbody>${[
      ['flops reached', E => fmt(E.M.leaves, 0)], ['tree buffers / gates', E => fmt(E.M.clkNodes, 0)], ['tree depth (levels)', E => fmt(E.M.clkDepth, 0)],
      ['arrival min', E => fmt(st(E).min, 1)], ['arrival median', E => fmt(st(E).p50, 1)], ['arrival max', E => fmt(st(E).max, 1)],
      ['spread max−min', E => fmt(st(E).spread, 1)], ['spread p99−p1', E => fmt(st(E).p9901, 1)], ['hold-fix buffers', E => fmt(E.M.holdBuf, 0) + ` (${fmt(E.M.holdPct, 1)}%)`]]
      .map(([k, f]) => `<tr><td>${k}</td>${ok.map(E => `<td class="n">${st(E) || k.startsWith('flops') || k.startsWith('tree') || k.startsWith('hold') ? f(E) : '—'}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
      <p class="note">ps at the ${S.ccorner.toUpperCase()} corner. Arrival includes the source latency the sign-off SDC puts on the clock port.</p>`));
    ok.forEach(E => {
      const by = new Map(), ffl = E.d.clock_ff_match ? E.d.clock_ff_leaves : null;
      for (let i = 0; i < E.n; i++){ const j = E.leafOf[i]; if (j < 0) continue; const v = S.ccorner === 'ff' ? (ffl ? ffl[j] : null) : E.d.clock_tt.leaves[j][3]; if (v == null) continue; const g = E.grp[i]; if (!by.has(g)) by.set(g, []); by.get(g).push(v); }
      const rows = [...by.entries()].map(([g, a]) => [g, latStats(a)]).sort((x, y) => y[1].n - x[1].n);
      H.push(sec('Arrival by block', `<div class="tw"><table class="t"><thead><tr><th>block</th><th class="n">flops</th><th class="n">p1</th><th class="n">median</th><th class="n">p99</th></tr></thead><tbody>${rows.map(([g, t]) =>
        `<tr><td class="m"><i class="sw" style="background:${E.groups[g].color}"></i> ${esc(SAFE ? 'block ' + (g + 1) : E.groups[g].name)}</td><td class="n">${fmt(t.n, 0)}</td><td class="n">${fmt(t.p1, 0)}</td><td class="n">${fmt(t.p50, 0)}</td><td class="n">${fmt(t.p99, 0)}</td></tr>`).join('')}</tbody></table></div>`, esc(E.d.label) + ' · ' + S.ccorner.toUpperCase() + ' ps, hierarchy depth ' + E.depth));
    });
  } else if (S.lens === 'density'){
    const g0 = ok[0] && ok[0].d.geom.grid, mx = heatMax(S.dmetric);
    H.push(sec('Density / congestion', `<div class="seg" role="group"><button type="button" data-dm="density" aria-pressed="${S.dmetric === 'density'}">Cell density</button><button type="button" data-dm="pins" aria-pressed="${S.dmetric === 'pins'}">Pin density</button><button type="button" data-dm="rudy" aria-pressed="${S.dmetric === 'rudy'}">Routed-wire RUDY</button></div>
      <div class="ramp" style="background:linear-gradient(90deg,${HEAT.join(',')})"></div><div class="rampl"><span>0</span><span>sqrt scale, shared</span><span>${S.dmetric === 'density' ? fmt(100 * mx, 0) + ' %' : S.dmetric === 'pins' ? fmt(mx, 0) + ' pins' : fmt(mx, 2) + ' µm/µm²'}</span></div>
      <p class="note" style="margin-top:6px">${S.dmetric === 'density' ? 'Placed std-cell area per bin over bin area (macros excluded).' : S.dmetric === 'pins' ? 'Signal pins of placed cells per bin.' : 'Each net\'s final routed wire length spread evenly over its pin bounding box (RUDY with routed length). An estimate of routing demand, not global-route overflow; the routed DBs carry no GRT congestion map.'}
      Bins ${ok.map(E => fmt(E.d.geom.grid.bin_um, 1) + ' µm').join(' / ')}.</p>`));
    ok.forEach(E => { const g = E.d.geom.grid, a = g[S.dmetric], s = a.slice().sort((x, y) => x - y);
      H.push(sec(esc(E.d.label), `<dl class="kv"><dt>median bin</dt><dd>${fmtD(pct(s, .5))}</dd><dt>99th pct bin</dt><dd>${fmtD(pct(s, .99))}</dd><dt>max bin</dt><dd>${fmtD(s[s.length - 1])}</dd><dt>utilisation</dt><dd>${fmt(E.M.util, 1)} %</dd></dl>`)); });
  } else {
    const fv = f => typeof f.v === 'number' ? (Number.isInteger(f.v) ? fmt(f.v, 0) : Math.abs(f.v) >= 1000 ? fmt(f.v, 0) : fmt(f.v, 2)) : esc(f.v);
    ok.forEach(E => H.push(sec(esc(E.d.label), `<div class="facts">${E.d.facts.map(f =>
      `<div class="fact"><div class="fr"><span>${esc(f.k)}</span><b>${fv(f)}${f.unit ? ' ' + esc(f.unit) : ''}</b></div>${f.note ? `<div class="note" style="margin:2px 0 0">${esc(f.note)}</div>` : ''}${SAFE || !f.src ? '' : `<div class="src">${esc(f.src)}</div>`}</div>`).join('')}</div>`, esc(SAFE ? '' : E.d.block || ''))));
  }
  // sources
  if (!SAFE) H.push(sec('Source', ok.map(E => `<dl class="kv"><dt>${esc(E.d.label)}</dt><dd>${esc(E.d.db)}<br>job ${esc(E.d.job)} on ${esc(E.d.host)} · exported ${esc((E.d.exported_at || '').slice(0, 16).replace('T', ' '))}${E.d.note ? '<br>' + esc(E.d.note) : ''}</dd></dl>`).join('') +
    `<p class="note" style="margin-top:6px">Exporter: tools/explorer_elem_export.py + tools/explorer_elem/or_export.py (OpenROAD, ORFS container, the job's w18_sta_tt/ff.tcl preamble).</p>`));
  $('side').innerHTML = H.join('');
  bindSide();
  function st(E){ return S.ccorner === 'ff' ? E.M.ff : E.M.tt; }
  function fmtD(v){ return S.dmetric === 'density' ? fmt(100 * v, 1) + ' %' : S.dmetric === 'pins' ? fmt(v, 0) : fmt(v, 2) + ' µm/µm²'; }
}
function bindSide(){
  const side = $('side');
  const dep = $('dep'); if (dep) dep.onchange = () => { S.depth = +dep.value; lsSet('depth.' + S.page.id, S.depth); S.iso = {}; regroup(); renderSide(); redrawAll(); };
  side.querySelectorAll('[data-g]').forEach(b => b.onclick = () => { const s = S.iso[b.dataset.e], i = +b.dataset.g; if (s.has(i)) s.delete(i); else s.add(i); renderSide(); redrawAll(); });
  side.querySelectorAll('[data-pc]').forEach(b => b.onclick = () => { S.pcorner = b.dataset.pc; lsSet('pcorner', S.pcorner); renderSide(); redrawAll(); });
  side.querySelectorAll('[data-cc]').forEach(b => b.onclick = () => { S.ccorner = b.dataset.cc; lsSet('ccorner', S.ccorner); renderSide(); redrawAll(); });
  side.querySelectorAll('[data-dm]').forEach(b => b.onclick = () => { S.dmetric = b.dataset.dm; lsSet('dmetric', S.dmetric); renderSide(); redrawAll(); });
  side.querySelectorAll('[data-p]').forEach(tr => tr.onclick = () => { S.psel[tr.dataset.e + S.pcorner] = +tr.dataset.p; renderSide(); redrawAll(); });
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

/* ------------------------------------------------------------------ story (explorer_story.js idiom: one event per step) */
function tpl(s){
  const posw = {a: S.rows ? 'top' : 'left', b: S.rows ? 'bottom' : 'right', A: S.rows ? 'Top' : 'Left', B: S.rows ? 'Bottom' : 'Right'};
  s = String(s || '').replace(/\{pos\.(\w)\}/g, (m, k) => posw[k] || m);
  return s.replace(/\{(\w+)\.([\w.]+)(?:\|(\d))?\}/g, (m, al, key, dg) => {
    const id = (S.page.alias || {})[al]; const E = S.els.find(x => x.id === id && !x.err); if (!E) return '—';
    let v = E.M; for (const k of key.split('.')) v = v == null ? null : v[k];
    if (typeof v === 'number') return key.endsWith('WNS') || key.startsWith('rec') ? sgn(v, dg == null ? 2 : +dg) : fmt(v, dg == null ? (Math.abs(v) >= 100 || Number.isInteger(v) ? 0 : 1) : +dg);
    return v == null ? '—' : esc(v);
  });
}
function startStory(){
  S.mode = 'story'; S.step = 0; lsSet('mode', 'story'); document.body.classList.add('story'); $('how').setAttribute('aria-pressed', 'true'); $('how').textContent = 'Exit story ✕';
  try { history.replaceState(null, '', location.pathname + location.search + '#story-' + S.page.id); } catch (e) {}
  renderLensBar(); showStep();
}
function stopStory(){
  clearInterval(S.timer); S.timer = null; S.mode = 'eng'; lsSet('mode', 'eng'); document.body.classList.remove('story'); $('storybar').hidden = true;
  $('how').setAttribute('aria-pressed', 'false'); $('how').innerHTML = 'How it works &#9654;';
  try { history.replaceState(null, '', location.pathname + location.search); } catch (e) {}
  S.els.forEach(E => { if (!E.err) fit(E); }); renderLensBar(); redrawAll();
}
$('how').onclick = () => S.mode === 'story' ? stopStory() : startStory();
function showStep(){
  const steps = S.page.story, n = steps.length, st = steps[S.step], bar = $('storybar');
  bar.hidden = false;
  bar.innerHTML = `<div class="row"><span class="ctr">step ${S.step + 1} / ${n}</span><span class="dots">${steps.map((_, i) => `<i class="${i === S.step ? 'on' : ''}"></i>`).join('')}</span><span class="sp" style="flex:1"></span>
      <button class="btn" data-sa="back" ${S.step ? '' : 'disabled'} aria-label="Previous step">&#9664; Back</button><button class="btn" data-sa="play" aria-pressed="${!!S.timer}">${S.timer ? 'Pause' : 'Play'}</button><button class="btn" data-sa="fwd" ${S.step < n - 1 ? '' : 'disabled'} aria-label="Next step">Next &#9654;</button></div>
    <h4>${tpl(st.title)}</h4><p class="cap" aria-live="polite">${tpl(st.cap)}</p>${st.why ? `<p class="why"><b>Why it matters:</b> ${tpl(st.why)}</p>` : ''}
    ${st.lens ? `<button class="lnk" data-sa="detail">Show the engineering detail (${esc((LENSES.find(l => l[0] === st.lens) || [])[1] || st.lens)} lens) &rarr;</button>` : ''}`;
  bar.querySelectorAll('[data-sa]').forEach(b => b.onclick = () => {
    const a = b.dataset.sa;
    if (a === 'back'){ halt(); S.step = Math.max(0, S.step - 1); showStep(); }
    else if (a === 'fwd'){ halt(); S.step = Math.min(n - 1, S.step + 1); showStep(); }
    else if (a === 'play'){ if (S.timer){ halt(); showStep(); return; } if (S.step >= n - 1) S.step = 0; S.timer = setInterval(() => { if (S.step >= n - 1){ halt(); showStep(); return; } S.step++; showStep(); }, 7000); showStep(); }
    else if (a === 'detail'){ const st2 = S.page.story[S.step]; stopStory(); if (st2.draw && st2.draw.corner) S.ccorner = st2.draw.corner; if (st2.draw && st2.draw.pcorner) S.pcorner = st2.draw.pcorner; setLens(st2.lens); }
  });
  // camera
  S.els.forEach(E => { if (E.err) return;
    const z = (st.draw || {}).zoom;
    if (z === 'path'){ const P = ((st.draw.pcorner === 'hold' ? E.d.hold_paths : E.d.setup_paths) || [])[0]; const pts = P ? P.points.filter(p => p[5] != null) : [];
      if (pts.length){ const xs = pts.map(p => p[5]), ys = pts.map(p => p[6]); fitBox(E, Math.min(...xs) - 10, Math.min(...ys) - 10, Math.max(...xs) + 10, Math.max(...ys) + 10); } else fit(E); }
    else if (z === 'root'){ const r = E.d.clock_tt.nodes.find(q => q[4] === 'PORT'); if (r) fitBox(E, r[0] - E.W * .2, r[1] - E.H * .2, r[0] + E.W * .2, r[1] + E.H * .2); else fit(E); }
    else fit(E); });
  redrawAll();
}
function halt(){ clearInterval(S.timer); S.timer = null; }
document.addEventListener('keydown', e => {
  if (S.mode !== 'story' || e.target.closest('input,select,textarea')) return;
  if (e.key === 'ArrowRight'){ halt(); S.step = Math.min(S.page.story.length - 1, S.step + 1); showStep(); }
  else if (e.key === 'ArrowLeft'){ halt(); S.step = Math.max(0, S.step - 1); showStep(); }
  else if (e.key === 'Escape') stopStory();
});
window.addEventListener('hashchange', () => { if (/^#story-/.test(location.hash) && S.mode !== 'story' && S.page && S.page.story) startStory(); });

init().catch(e => { $('sum').textContent = 'Failed to load: ' + e; });
})();

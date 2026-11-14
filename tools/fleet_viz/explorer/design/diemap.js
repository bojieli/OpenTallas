/* Die map (EXPLORER-P1): the die floorplan with the real routed wires of every signed type and of its hard cores, in place.
   Composition: /api/design/compose/<die> (die_compose.py) pins the die plan and one layout pack per unique master; every
   instance is a pack + offset + orient (R0 MX MY R180).  Packs are the element-page packs (tools/layout_viewer/lv_tile.py): coordinates
   stay PACK-LOCAL (integer DBU in float32, exact); the die offset is added in float64 on the CPU as an offset RELATIVE TO THE CAMERA
   (uRel), so a 32 mm die costs no precision.  World unit of the view is um.
   LOD: far = plan rectangles coloured by status + one level-0 density raster per type; closer = the finer raster levels of what is
   in view; closest (visible shape estimate within the budget) = the exact vector tiles, drawn with the same shader as the element page.
   Unsigned types are an outline placeholder, unless ?unsigned=1 (draws the newest as-routed pack, labelled UNSIGNED). */
(function(){
'use strict';
const S = window.LVShared;
if (!S) throw new Error('layout.js (window.LVShared) must load first');
let ROOT = document;
const $ = (q, r) => (r || ROOT).querySelector(q);
const esc = S.esc, fmt = S.fmt, hex = S.hex;
const cssv = n => getComputedStyle(ROOT === document ? document.documentElement : ROOT).getPropertyValue(n).trim();
const cssHex = n => cssv(n) || '#808080';   // tokens come from the host page / shell (tokens.css)
const cssRgb = (n, a) => [...hex(cssHex(n)), a == null ? 255 : a];
const SGN = {R0: [1, 1], MX: [1, -1], MY: [-1, 1], R180: [-1, -1]};
const STATE_VAR = {signed: '--s-signed', failed: '--s-failed', building: '--s-building', queued: '--s-queued', waiting: '--s-waiting', 'not built': '--s-notbuilt', 'hard ip': '--s-hardip'};
const OBJ = h => '/layout_store/objects/' + h.slice(0, 2) + '/' + h + '.br';
const M = {man: null, packs: new Map(), tiles: new Map(), rasters: new Map(), pending: new Map(), gpu: 0, showUnsigned: false, vis: null};
const PH = /[?&]phone=1/.test(location.search) || innerWidth <= 980;
let deckgl = null, RectLayer = null, workers = [], wnext = 0, upd = 0;

/* ---- shader: the element page's rect shader, with a die-level projection instead of deck's (offset relative to the camera, float64 on the CPU) */
function layerClass(){
  const {Layer} = window.deck, {Model, Geometry} = window.luma;
  const vs = S.VS.replace('uniform float uPx;', 'uniform float uPx; uniform vec2 uSgn; uniform vec2 uRel; uniform vec2 uScale;')
    .replace('gl_Position = project_position_to_clipspace(vec3(p, 0.0), vec3(0.0), vec3(0.0));', 'gl_Position = vec4((p * uSgn * 0.001 + uRel) * uScale, 0.0, 1.0);');
  if (vs === S.VS) throw new Error('layout.js shader changed: diemap projection patch did not apply');
  class DieRectLayer extends Layer {
    getShaders(){ return super.getShaders({vs, fs: S.FS, modules: []}); }
    initializeState(){ this.getAttributeManager().addInstanced({instanceRects: {size: 4, noAlloc: true}, instanceMeta: {size: 3, noAlloc: true}}); this.setState({model: this._model()}); }
    _model(){ return new Model(this.context.gl, Object.assign({}, this.getShaders(), {id: this.props.id, isInstanced: true,
      geometry: new Geometry({drawMode: 6, vertexCount: 4, attributes: {positions: {size: 3, value: new Float32Array([0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0])}}})})); }
    draw({uniforms}){ this.state.model.setUniforms(uniforms).setUniforms(this.props.lv).draw(); }
  }
  DieRectLayer.layerName = 'DieRectLayer'; DieRectLayer.defaultProps = {lv: {type: 'object', value: {}}};
  return DieRectLayer;
}

/* ---- composition: instances -> placed items (pack + float64 transform + um bbox) */
function xfOf(orient, X, Y, W, H){   // plan bbox (DBU) + orient -> {sx, sy, ox, oy} in um: world = o + S * local * 0.001
  const [sx, sy] = SGN[orient]; return {sx, sy, ox: (X + (sx < 0 ? W : 0)) / 1000, oy: (Y + (sy < 0 ? H : 0)) / 1000};
}
function compose(parent, c){   // core origin/orient (DBU, in the type's frame) under the type's transform
  const [sx, sy] = SGN[c.orient];
  return {sx: parent.sx * sx, sy: parent.sy * sy, ox: parent.ox + parent.sx * c.origin[0] / 1000, oy: parent.oy + parent.sy * c.origin[1] / 1000};
}
function bboxOf(xf, die){   // local pack die (DBU) -> world um bbox
  const a = [xf.ox + xf.sx * die[0] / 1000, xf.oy + xf.sy * die[1] / 1000], b = [xf.ox + xf.sx * die[2] / 1000, xf.oy + xf.sy * die[3] / 1000];
  return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
}
function buildItems(){
  const m = M.man, items = [];
  m.instances.forEach((r, ii) => {
    if (!r.ok) return;
    const p = m.packs[r.pack]; if (!p) return;
    if (p.state !== 'signed' && !M.showUnsigned) return;
    const xf = xfOf(r.orient, r.x, r.y, r.w, r.h);
    items.push({ii, pack: r.pack, level: 'type', xf, bb: bboxOf(xf, p.die), state: p.state, name: r.name});
    for (const c of p.cores){
      if (!c.core) continue;
      const cp = m.packs[c.core]; if (!cp) continue;
      const cx = compose(xf, c);
      items.push({ii, pack: c.core, level: 'core', xf: cx, bb: bboxOf(cx, cp.die), state: cp.state, name: r.name + '/' + c.name});
    }
  });
  M.items = items;
}

/* ---- packs: header, manifest (lazy), workers */
function packState(pid){
  let P = M.packs.get(pid);
  if (!P){ P = {pid, info: M.man.packs[pid], H: null, ob: null, loading: null, grid: null}; M.packs.set(pid, P); }
  return P;
}
async function getJSON(url){ const r = await fetch(url); if (!r.ok) throw new Error(r.status + ' ' + url); return r.json(); }
function needHeader(P){
  if (P.H || P.loading) return;
  P.loading = getJSON(OBJ(P.info.header)).then(H => {
    P.H = H; P.tidx = new Map((H.grid.tiles || []).map(t => [t.x + '_' + t.y, t]));
    workers.forEach(w => w.postMessage({op: 'init', pack: P.pid, header: H}));
    if (!M.L) initLayers(H);
    requestUpdate();
  }).catch(e => { P.err = String(e); console.warn('pack header', P.pid, e); });
}
function needManifest(P){
  if (P.ob || P.mloading) return;
  P.mloading = getJSON('/layout_store/elements/' + encodeURIComponent(P.pid) + '/' + encodeURIComponent(P.info.job) + '.json').then(m => { P.ob = m.objects; requestUpdate(); })
    .catch(e => { P.err = String(e); console.warn('pack manifest', P.pid, e); });
}
function objUrl(P, name){ const h = (P.ob && P.ob[name]) || (name.startsWith('r/0/') && P.info.r0[name.slice(4)]); return h ? location.origin + OBJ(h) : null; }

function initLayers(H){
  const nl = H.layers.length;
  M.L = H.layers.map((l, i) => ({i, name: l.name, type: l.type, n: 0, vis: true, op: l.type === 'CUT' ? 0.85 : 0.7}));
  M.L.push({i: nl, name: 'Cells', type: 'CELLS', vis: true, op: 0.55}, {i: nl + 1, name: 'Filler / tap', type: 'PHYS', vis: false, op: 0.35});
  const P = S.PAL.classic;
  M.L.forEach(l => { let c, pat; if (l.type === 'CELLS'){ c = cssHex('--cellgrey'); pat = 10; } else if (l.type === 'PHYS'){ c = cssHex('--faint'); pat = 10; } else { const s = P[l.name]; c = s ? s[0] : cssHex('--dim'); pat = s ? s[1] : 4; } l.color = c; l.pat = pat; });
  M.kindVis = Object.fromEntries(S.KINDS.map(k => [k[0], !!k[2]]));
  styleUniforms(); buildLayerPanel();
}
function styleUniforms(){
  const col = new Float32Array(48 * 4), al = new Float32Array(48), pat = new Float32Array(48), kd = new Float32Array(20);
  M.L.forEach(l => { const c = hex(l.color); col.set([c[0] / 255, c[1] / 255, c[2] / 255, 1], l.i * 4); al[l.i] = l.vis ? l.op : 0; pat[l.i] = l.pat; });
  S.KINDS.forEach(k => kd[k[0]] = M.kindVis[k[0]] ? 1 : 0);
  kd[14] = M.L[M.L.length - 1].vis ? 1 : 0; kd[15] = kd[16] = M.kindVis[10] ? 1 : 0;
  M.uni0 = {uColor: col, uAlpha: al, uPat: pat, uKind: kd, uHl: 0, uFill: 0.22};
  const st = {}; M.L.forEach(l => { const c = hex(l.color); st[l.i] = {r: c[0], g: c[1], b: c[2], a: l.vis ? l.op : 0}; });
  M.rstyle = st; workers.forEach(w => w.postMessage({op: 'restyle', style: st}));
}

/* ---- LOD / loading */
function viewBounds(){
  const vp = deckgl.getViewports()[0]; if (!vp) return null;
  const a = vp.unproject([0, 0]), b = vp.unproject([vp.width, vp.height]);
  return {x0: Math.min(a[0], b[0]), x1: Math.max(a[0], b[0]), y0: Math.min(a[1], b[1]), y1: Math.max(a[1], b[1]), w: vp.width, h: vp.height};
}
function requestUpdate(){ if (!upd) upd = requestAnimationFrame(() => { upd = 0; update(); }); }
const meets = (a, b) => a[0] < b.x1 && a[2] > b.x0 && a[1] < b.y1 && a[3] > b.y0;
// local DBU box (of a pack) -> world um bbox
function wbox(xf, x0, y0, x1, y1){
  const ax = xf.ox + xf.sx * x0 / 1000, bx = xf.ox + xf.sx * x1 / 1000, ay = xf.oy + xf.sy * y0 / 1000, by = xf.oy + xf.sy * y1 / 1000;
  return [Math.min(ax, bx), Math.min(ay, by), Math.max(ax, bx), Math.max(ay, by)];
}
function lbox(xf, b){   // world um view -> local DBU box of an item (clipped by the caller)
  const ax = (b.x0 - xf.ox) * 1000 * xf.sx, bx = (b.x1 - xf.ox) * 1000 * xf.sx, ay = (b.y0 - xf.oy) * 1000 * xf.sy, by = (b.y1 - xf.oy) * 1000 * xf.sy;
  return {x0: Math.min(ax, bx), x1: Math.max(ax, bx), y0: Math.min(ay, by), y1: Math.max(ay, by)};
}
function shapeCost(P, t){
  let n = 0; for (const l of M.L) if (l.vis && l.i < t.n.length) n += t.n[l.i];
  if (M.kindVis[9] || M.kindVis[10]) n += t.v * 3;
  n += t.c * 4;
  return n;
}
function tilesIn(P, lb){
  const G = P.H.grid, Sz = G.size, out = [];
  const tx0 = Math.max(0, Math.floor((lb.x0 - G.ox) / Sz)), tx1 = Math.min(G.nx - 1, Math.floor((lb.x1 - G.ox) / Sz));
  const ty0 = Math.max(0, Math.floor((lb.y0 - G.oy) / Sz)), ty1 = Math.min(G.ny - 1, Math.floor((lb.y1 - G.oy) / Sz));
  for (let y = ty0; y <= ty1; y++) for (let x = tx0; x <= tx1; x++){ const k = x + '_' + y; if (P.tidx.has(k)) out.push(k); }
  return out;
}
function secsOf(P, k){
  const t = P.tidx.get(k), nl = P.H.layers.length, out = [];
  for (const s of t.s || []){
    if (s[0] === 'L'){ const l = M.L[+s.slice(1)]; if (l && l.vis) out.push(s); }
    else if (s === 'v'){ if (M.kindVis[9] || M.kindVis[10]) out.push(s); }
    else if (s === 'c'){ if (M.L[nl].vis || M.L[nl + 1].vis) out.push(s); }
  }
  return out;
}
function reqTile(P, k){
  const key = P.pid + '|' + k, secs = secsOf(P, k);
  if (M.pending.has('t' + key)) return;
  if (!secs.length){ M.tiles.set(key, {n: 0, empty: true, bytes: 0, used: performance.now()}); return; }
  const parts = secs.map(s => ({name: s, url: objUrl(P, 't/' + k + '/' + s)}));
  if (parts.some(p => !p.url)) { M.tiles.set(key, {n: 0, empty: true, bytes: 0, used: performance.now()}); return; }
  M.pending.set('t' + key, 1);
  workers[wnext++ % workers.length].postMessage({op: 'tile', pack: P.pid, key: k, parts, phys: false, arrDetail: M.arrDetail});
}
function reqRaster(P, k){
  const key = P.pid + '|' + k; if (M.rasters.has(key) || M.pending.has('r' + key)) return;
  const u = objUrl(P, 'r/' + k); if (!u) return;
  M.pending.set('r' + key, 1);
  workers[wnext++ % workers.length].postMessage({op: 'raster', pack: P.pid, key: k, url: u, style: M.rstyle});
}
function onWorker(ev){
  const m = ev.data, key = m.pack + '|' + m.key;
  if (m.op === 'tile'){
    M.pending.delete('t' + key);
    const old = M.tiles.get(key); if (old) M.gpu -= old.bytes || 0;
    const bytes = m.n * 28;
    M.tiles.set(key, {n: m.n, rects: m.rects, meta: m.meta, bytes, used: performance.now()}); M.gpu += bytes;
    if (!M.firstGeo) M.firstGeo = performance.now() - M.t0;
    requestUpdate();
  } else if (m.op === 'raster'){
    M.pending.delete('r' + key);
    const prev = M.rasters.get(key);
    M.rasters.set(key, {im: new ImageData(new Uint8ClampedArray(m.rgba.buffer), m.size, m.size), v: (prev ? prev.v : 0) + 1});
    requestUpdate();
  } else if (m.op === 'error'){ M.pending.delete((m.what === 'tile' ? 't' : 'r') + key); console.warn('worker', m); }
}

function update(){
  if (!deckgl || !M.man) return;
  const b = viewBounds(); if (!b) return;
  const ppu = Math.pow(2, M.vs.zoom);   // css px per um
  M.ppu = ppu; M.arrDetail = ppu * 0.001 * Math.min(2, devicePixelRatio || 1) >= 0.2;
  const dpr = Math.min(2, devicePixelRatio || 1);
  // items in view, with their screen size
  const vis = [];
  for (const it of M.items){ if (!meets(it.bb, b)) continue; it.px = Math.min(it.bb[2] - it.bb[0], it.bb[3] - it.bb[1]) * ppu; if (it.px < 6) continue; vis.push(it); }
  const cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
  vis.sort((p, q) => ((p.bb[0] + p.bb[2]) / 2 - cx) ** 2 + ((p.bb[1] + p.bb[3]) / 2 - cy) ** 2 - (((q.bb[0] + q.bb[2]) / 2 - cx) ** 2 + ((q.bb[1] + q.bb[3]) / 2 - cy) ** 2));
  const budget = PH ? 1.2e6 : 3e6; let spent = 0, nGeo = 0;
  const want = new Set();
  for (const it of vis){
    const P = packState(it.pack); needHeader(P);
    it.P = P; it.geo = false; it.lb = null;
    if (!P.H || !M.L) continue;
    const lb = lbox(it.xf, b); it.lb = lb;
    const ppl = ppu * 0.001;   // css px per local DBU
    const ts = tilesIn(P, lb); it.ts = ts;
    // rasters: level 0 always (from the composition manifest, no manifest fetch); finer levels from the closure manifest
    const lv = P.H.raster.levels; let level = 0;
    for (const L of lv){ level = L.level; if (L.px_nm * ppl <= 1.5) break; }
    it.rlv = level;
    if (level > 0 || ppl * 1000 >= 0.25) needManifest(P);
    if (it.px >= 8) for (const n of lv[0].nodes) reqRaster(P, '0/' + n[0] + '_' + n[1]);
    if (level > 0 && P.ob){ const L = lv.find(q => q.level === level); if (L){ const have = new Set(L.nodes.map(n => n[0] + '_' + n[1])), node = L.node_nm;
      const nx0 = Math.max(0, Math.floor((lb.x0 - P.H.die[0]) / node)), nx1 = Math.floor((lb.x1 - P.H.die[0]) / node), ny0 = Math.max(0, Math.floor((lb.y0 - P.H.die[1]) / node)), ny1 = Math.floor((lb.y1 - P.H.die[1]) / node);
      for (let y = ny0; y <= ny1; y++) for (let x = nx0; x <= nx1; x++) if (have.has(x + '_' + y)) reqRaster(P, level + '/' + x + '_' + y); } }
    // geometry within the shape budget
    if (P.ob && ppu >= 0.25){
      let c = 0; for (const k of ts) c += shapeCost(P, P.tidx.get(k));
      if (spent + c <= budget){ spent += c; it.geo = true; nGeo++; for (const k of ts){ const key = P.pid + '|' + k; want.add(key); if (!M.tiles.has(key)) reqTile(P, k); } }
    }
  }
  M.stats = {items: vis.length, geo: nGeo, spent};
  if (M.gpu > (PH ? 150e6 : 300e6)){ const lru = [...M.tiles.entries()].filter(([k]) => !want.has(k)).sort((p, q) => p[1].used - q[1].used);
    for (const [k, t] of lru){ if (M.gpu <= (PH ? 150e6 : 300e6) * 0.8) break; M.gpu -= t.bytes; M.tiles.delete(k); } }
  const now = performance.now(); want.forEach(k => { const t = M.tiles.get(k); if (t) t.used = now; });
  M.vis = vis;
  render(b, vis, dpr);
  renderInfo();
}

/* ---- deck layers */
function render(b, vis, dpr){
  const C = deck.COORDINATE_SYSTEM.CARTESIAN, layers = [], man = M.man;
  const ppu = M.ppu, vs = M.vs, W = b.w, Hh = b.h;
  const rect = a => [[a[0], a[1]], [a[2], a[1]], [a[2], a[3]], [a[0], a[3]]];
  // plan rectangles (the placeholder for everything that has no routed pack in view)
  const covered = new Set(vis.filter(i => i.level === 'type' && i.geo).map(i => i.ii));
  const insts = M.insts.filter(r => r.bb[0] < b.x1 && r.bb[2] > b.x0 && r.bb[1] < b.y1 && r.bb[3] > b.y0);
  layers.push(new deck.PolygonLayer({id: 'plan', data: insts, getPolygon: r => rect(r.bb), getFillColor: r => [...r.col, r.drawn ? 28 : 80], getLineColor: r => [...r.col, 255],
    lineWidthUnits: 'pixels', getLineWidth: 1, coordinateSystem: C, updateTriggers: {getFillColor: [M.items.length, M.showUnsigned]}}));
  // rasters, then exact tiles
  for (const it of vis){
    const P = it.P; if (!P || !P.H) continue;
    const allIn = it.geo && it.ts.every(k => { const t = M.tiles.get(P.pid + '|' + k); return t && !t.pendingSecs; });
    if (!(it.geo && allIn)){
      const R = P.H.raster.levels;
      const rl = lvl => { const L = R.find(q => q.level === lvl); if (!L) return; const node = L.node_nm;
        for (const n of L.nodes){ const k = lvl + '/' + n[0] + '_' + n[1], r = M.rasters.get(P.pid + '|' + k); if (!r) continue;
          const x0 = P.H.die[0] + n[0] * node, y0 = P.H.die[1] + n[1] * node, wb = wbox(it.xf, x0, y0, x0 + node, y0 + node);
          if (!meets(wb, b)) continue;
          // mirrored instance: swap the bounds so the bitmap flips with it (image row 0 = top of the node)
          const bounds = [it.xf.sx < 0 ? wb[2] : wb[0], it.xf.sy < 0 ? wb[3] : wb[1], it.xf.sx < 0 ? wb[0] : wb[2], it.xf.sy < 0 ? wb[1] : wb[3]];
          layers.push(new deck.BitmapLayer({id: 'r' + it.ii + it.pack + k + ':' + r.v, image: r.im, bounds, coordinateSystem: C, textureParameters: {[10240]: 9729, [10241]: 9729}, opacity: 1})); } };
      rl(0); if (it.rlv > 0) rl(it.rlv);
    }
    if (it.geo){
      const uni = Object.assign({}, M.uni0, {uPx: ppu * 0.001 * dpr, uSgn: [it.xf.sx, it.xf.sy], uRel: [it.xf.ox - vs.target[0], it.xf.oy - vs.target[1]], uScale: [2 * ppu / W, 2 * ppu / Hh]});
      for (const k of it.ts){ const t = M.tiles.get(P.pid + '|' + k); if (!t || t.empty || !t.n) continue;
        layers.push(new RectLayer({id: 't' + it.ii + it.pack + k, data: {length: t.n, attributes: {instanceRects: {value: t.rects, size: 4}, instanceMeta: {value: t.meta, size: 3}}}, coordinateSystem: C, lv: uni})); }
    }
  }
  // outlines and labels: die, cores, names
  const D = man.outline, fg = hex(cssHex('--faint')), ink = hex(cssHex('--ink'));
  layers.push(new deck.PathLayer({id: 'die', data: [{p: [[0, 0], [D[0] / 1000, 0], [D[0] / 1000, D[1] / 1000], [0, D[1] / 1000], [0, 0]]}], getPath: d => d.p, getColor: [...fg, 255], widthUnits: 'pixels', getWidth: 1.5, coordinateSystem: C}));
  const cores = M.items.filter(i => i.level === 'core' && meets(i.bb, b) && Math.min(i.bb[2] - i.bb[0], i.bb[3] - i.bb[1]) * ppu >= 6);
  if (cores.length) layers.push(new deck.PolygonLayer({id: 'cores', data: cores, getPolygon: i => rect(i.bb), filled: false, getLineColor: [...hex(cssHex('--macro')), 220], lineWidthUnits: 'pixels', getLineWidth: 1, coordinateSystem: C}));
  const lab = insts.filter(r => Math.min(r.bb[2] - r.bb[0], r.bb[3] - r.bb[1]) * ppu >= 70);
  layers.push(new deck.TextLayer({id: 'names', data: lab, getPosition: r => [r.bb[0], r.bb[3]], getText: r => r.name + '  ' + r.stateLabel, getSize: 11, characterSet: 'auto', getColor: [...ink, 255], getTextAnchor: 'start',
    getAlignmentBaseline: 'top', getPixelOffset: [4, 4], background: true, getBackgroundColor: cssRgb('--canvas', 190), fontFamily: 'ui-monospace, Menlo, monospace', coordinateSystem: C}));
  if (M.flash) layers.push(new deck.PolygonLayer({id: 'flash', data: [M.flash], getPolygon: q => rect(q), filled: false, getLineColor: [...hex(cssHex('--accent')), 255], lineWidthUnits: 'pixels', getLineWidth: 3, coordinateSystem: C}));
  deckgl.setProps({layers});
}

/* ---- page */
function renderInfo(){
  const s = M.stats || {}, el = $('[data-info]'); if (!el) return;
  const ps = [...M.packs.values()].filter(p => p.H).length;
  el.textContent = `${M.vs.zoom.toFixed(2)} z · ${fmt(M.ppu, 3)} px/µm · ${s.items || 0} placed masters in view · ${s.geo || 0} exact · ${fmt(s.spent || 0, 0)} shapes est · ${fmt(M.gpu / 1e6, 0)} MB GPU · ${ps} packs open`;
}
function buildLayerPanel(){
  const el = $('[data-layers]'); if (!el) return;
  el.innerHTML = M.L.filter(l => l.type !== 'CUT' || /^V[1-6]$/.test(l.name)).filter(l => l.type !== 'PHYS' && l.type !== 'CELLS' || true).map(l => `<label class="lyr"><input type="checkbox" data-l="${l.i}" ${l.vis ? 'checked' : ''}><i style="background:${l.color}"></i>${esc(l.name)}</label>`).join('');
  el.querySelectorAll('input').forEach(i => i.onchange = () => { M.L[+i.dataset.l].vis = i.checked; styleUniforms(); refreshTiles(); requestUpdate(); });
}
function refreshTiles(){ M.tiles.clear(); M.gpu = 0; M.rasters.clear(); }
function colorOf(st){ return hex(cssHex(STATE_VAR[st] || '--s-notbuilt')); }
function prepInsts(){
  M.insts = M.man.instances.map(r => ({name: r.name, node: r.node, state: r.state, stateLabel: r.state, orient: r.orient, why: r.why, pack: r.pack, ok: r.ok, ii: 0,
    bb: [r.x / 1000, r.y / 1000, (r.x + r.w) / 1000, (r.y + r.h) / 1000], col: colorOf(r.state), drawn: false}));
  M.man.instances.forEach((r, i) => { M.insts[i].ii = i; });
}
function syncDrawn(){ const set = new Set(M.items.filter(i => i.level === 'type').map(i => i.ii)); M.insts.forEach((r, i) => { r.drawn = set.has(i); r.stateLabel = r.state + (r.drawn ? (r.state === 'signed' ? ' (routed wires)' : ' UNSIGNED as-routed') : (r.ok && r.state !== 'signed' ? ' (outline)' : r.ok ? '' : ' (no pack)')); }); }
function zoomTo(bb, pad){
  const r = $('[data-canvas]').getBoundingClientRect();
  const z = Math.log2(Math.min(r.width / ((bb[2] - bb[0]) / (pad || 0.9)), r.height / ((bb[3] - bb[1]) / (pad || 0.9))));
  M.vs = Object.assign({}, M.vs, {target: [(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, 0], zoom: z}); deckgl.setProps({initialViewState: M.vs}); requestUpdate(); saveUrl();
}
function urlState(){ const o = {}; location.hash.replace(/^#/, '').split('&').forEach(x => { const [k, v] = x.split('='); if (k) o[k] = decodeURIComponent(v || ''); }); return o; }
let urlT = 0;
function saveUrl(){ clearTimeout(urlT); urlT = setTimeout(() => { if (!M.live) return; const o = urlState(); delete o.die; o.n = M.node; o.v = [M.vs.target[0].toFixed(2), M.vs.target[1].toFixed(2), M.vs.zoom.toFixed(2)].join(','); if (M.showUnsigned) o.u = '1'; else delete o.u;
  try { history.replaceState(null, '', location.pathname + location.search + '#' + Object.entries(o).map(([k, v]) => k + '=' + encodeURIComponent(v).replace(/%2C/g, ',')).join('&')); } catch (e) {} }, 250); }
async function loadScript(src){ return new Promise((res, rej) => { const s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = () => rej(new Error('load ' + src)); document.head.appendChild(s); }); }

function hoverAt(e){
  const vp = deckgl.getViewports()[0], r = $('[data-canvas]').getBoundingClientRect(), w = vp.unproject([e.clientX - r.left, e.clientY - r.top]);
  $('[data-coord]').textContent = `x ${fmt(w[0], 2)}  y ${fmt(w[1], 2)} µm`;
  const tip = $('[data-tip]'), hit = M.insts.find(q => w[0] >= q.bb[0] && w[0] < q.bb[2] && w[1] >= q.bb[1] && w[1] < q.bb[3]);
  if (!hit){ tip.hidden = true; return; }
  const it = M.items.find(i => i.ii === hit.ii && i.level === 'type');
  let local = '';
  if (it){ const lx = (w[0] - it.xf.ox) * 1000 * it.xf.sx, ly = (w[1] - it.xf.oy) * 1000 * it.xf.sy; local = `<br>pack-local ${fmt(lx / 1000, 3)}, ${fmt(ly / 1000, 3)} µm`; }
  const p = M.man.packs[hit.pack];
  tip.innerHTML = `<b>${esc(hit.name)}</b><br>${esc(hit.node)}<br>${esc(hit.state)} · ${esc(hit.orient)}${p ? '<br>pack ' + esc(p.job) + ' · ' + fmt(p.bytes / 1e6, 1) + ' MB' : '<br>' + esc(hit.why || 'no routed pack')}${local}`;
  tip.hidden = false; tip.style.left = Math.min(r.width - 270, e.clientX - r.left + 14) + 'px'; tip.style.top = Math.min(r.height - 110, e.clientY - r.top + 14) + 'px';
}

const TEMPLATE = `<div class="dm-top"><span data-head>loading the composition&hellip;</span><span class="dm-sp"></span>
 <input type="search" placeholder="Go to partition / type" data-go aria-label="Go to partition"><button class="dm-btn" data-fit>Fit</button>
 <label><input type="checkbox" data-unsigned> show unsigned as-routed packs</label><span data-legend></span></div>
<div class="dm-main"><div class="dm-root" data-root><div data-canvas></div><div class="dm-ov" data-info></div><div class="dm-ov" data-coord></div><div class="dm-tip" data-tip hidden></div></div>
<div class="dm-side"><h4>Routing layers</h4><div data-layers></div>
<h4>Notes</h4><p>Zoom into a signed type for its exact routed wires; hard cores are drawn in place from their own packs. Far out: outline plus density raster. Unsigned types stay outlines. Die-top nets, PG and clock are not routed yet and are not drawn.</p></div></div>`;

/* mountDieLayout(el, {node, onSelect, unsigned}): node = design-index node id (die, type or core); selection and view live in #n= / #v= */
async function mountDieLayout(el, opts){
  opts = opts || {};
  if (!document.querySelector('link[data-dm-css]')){ const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = '/explorer/design/diemap.css'; l.dataset.dmCss = '1'; document.head.appendChild(l); }
  ROOT = el; M.live = true; M.opts = opts; el.classList.add('dm'); el.innerHTML = TEMPLATE;
  M.t0 = performance.now();
  const u = urlState(), node = (opts.node || u.n || u.die || 's81'), die = node.split('.')[0];
  M.showUnsigned = !!opts.unsigned || /[?&]unsigned=1/.test(location.search) || u.u === '1';
  const root = $('[data-root]');
  M.node = node;
  try {
    M.man = await getJSON('/api/design/compose/' + encodeURIComponent(die));
  } catch (e){ root.innerHTML = `<div class="busy"><b>Could not start.</b><br>${esc(String(e))}</div>`; return; }
  RectLayer = layerClass();
  const man = M.man;
  prepInsts(); buildItems(); syncDrawn();
  const NW = Math.max(2, Math.min(4, (navigator.hardwareConcurrency || 4) - 1));
  for (let i = 0; i < NW; i++){ const w = new Worker('/explorer/element/lv_worker.js'); w.onmessage = onWorker; workers.push(w); }
  const cv = $('[data-canvas]'), r = cv.getBoundingClientRect(), Wd = man.outline[0] / 1000, Ht = man.outline[1] / 1000;
  const fit = Math.log2(Math.min(r.width / Wd, r.height / Ht) * 0.94);
  M.fit = fit; M.vs = {target: [Wd / 2, Ht / 2, 0], zoom: fit, minZoom: fit - 1, maxZoom: 14};
  if (u.v){ const p = u.v.split(',').map(Number); if (p.length === 3 && p.every(isFinite)) M.vs = Object.assign(M.vs, {target: [p[0], p[1], 0], zoom: p[2]}); }
  deckgl = new deck.Deck({parent: cv, views: new deck.OrthographicView({id: 'o', flipY: false, controller: true}), initialViewState: M.vs,
    controller: {scrollZoom: {speed: 0.012, smooth: false}, inertia: 250, doubleClickZoom: true, keyboard: true, dragRotate: false},
    onViewStateChange: ({viewState}) => { M.vs = viewState; requestUpdate(); saveUrl(); return viewState; },
    useDevicePixels: Math.min(2, devicePixelRatio || 1), parameters: {clearColor: [0, 0, 0, 0], depthTest: false, blend: true}, layers: []});
  cv.addEventListener('pointermove', e => { M.hev = e; if (!M.hraf) M.hraf = requestAnimationFrame(() => { M.hraf = 0; hoverAt(M.hev); }); });
  cv.addEventListener('pointerleave', () => { $('[data-tip]').hidden = true; });
  const s = man.summary;
  $('[data-head]').innerHTML = `<b>${esc(man.label || man.die)}</b> die map · plan <code>${esc(man.plan.path.split('/').pop().replace('.json.gz', ''))}</code> · ${s.signed_with_pack} of ${s.signed_instances} signed placements have a routed pack · ${s.unique_packs} unique packs (${fmt(s.pack_bytes / 1e9, 2)} GB)`;
  $('[data-unsigned]').checked = M.showUnsigned;
  $('[data-unsigned]').onchange = e => { M.showUnsigned = e.target.checked; buildItems(); syncDrawn(); requestUpdate(); saveUrl(); };
  $('[data-fit]').onclick = () => zoomTo([0, 0, Wd, Ht], 0.94);
  $('[data-go]').onchange = e => { const q = e.target.value.trim().toLowerCase(); if (!q) return; const h = M.insts.find(x => x.name.toLowerCase() === q) || M.insts.find(x => x.name.toLowerCase().includes(q) || x.node.toLowerCase().includes(q)); if (h){ M.flash = h.bb; zoomTo(h.bb, 0.8); } };
  M.legend = ['signed', 'failed', 'building', 'waiting', 'not built'].map(k => `<i style="background:rgb(${colorOf(k)})"></i>${k}`).join(' ');
  $('[data-legend]').innerHTML = M.legend;
  window.DieMap = {state: () => M, zoomTo, update: () => update(), setUnsigned: v => { M.showUnsigned = v; buildItems(); syncDrawn(); requestUpdate(); }};
  cv.addEventListener('click', e => { const vp = deckgl.getViewports()[0], r = cv.getBoundingClientRect(), w = vp.unproject([e.clientX - r.left, e.clientY - r.top]);
    const hit = M.insts.find(q => w[0] >= q.bb[0] && w[0] < q.bb[2] && w[1] >= q.bb[1] && w[1] < q.bb[3]); if (hit && opts.onSelect) opts.onSelect(hit.node, hit.name); });
  if (node !== die){ const h = M.insts.find(x => x.node === node); if (h && !u.v){ M.flash = h.bb; zoomTo(h.bb, 0.8); } }
  requestUpdate();
  return {zoomTo, select: n => { const h = M.insts.find(x => x.node === n); if (h){ M.node = n; M.flash = h.bb; zoomTo(h.bb, 0.8); } }, destroy: () => { M.live = false; if (deckgl){ deckgl.finalize(); deckgl = null; } workers.forEach(w => w.terminate()); workers = []; el.innerHTML = ''; }};
}
window.mountDieLayout = mountDieLayout;
})();

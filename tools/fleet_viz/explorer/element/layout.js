/* Chip Explorer element page: the routed-geometry layout viewer ('Layout' tab).
   Data: /api/layout/<element>/... (tools/fleet_viz/layout_service.py), packs cut by tools/layout_viewer/lv_tile.py from a
   lossless OpenDB extraction (lv_extract.py).  Rendering: deck.gl 8.9.36 (vendored, WebGL2) with one instanced-rectangle
   layer per loaded tile (absolute DBU in float32: exact to 16.7 mm; deck's identity projection works relative to the camera); per-layer colour / stipple / opacity / visibility are shader uniforms, so toggles cost nothing.
   Zoomed out: per-layer density raster pyramid composited in a worker; zoomed in: exact geometry tiles (25.6 um).
   Overlays: hierarchy-contract findings, worst timing paths, clock tree with arrival colouring, per-layer routing
   congestion, module outlines.  View state lives in the URL hash (#tab=geo&v=x,y,zoom&h=hidden layers&n=net&o=overlays).
   Docs: tools/fleet_viz/LAYOUT_VIEWER.md */
(function(){
'use strict';
const $ = (id, r) => (r || document).querySelector(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const fmt = (n, d = 1) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const lsGet = (k, d) => { try { const v = localStorage.getItem('otx.lv.' + k); return v == null ? d : v; } catch (e) { return d; } };
const lsSet = (k, v) => { try { localStorage.setItem('otx.lv.' + k, v); } catch (e) {} };
const hex = h => { h = h.replace('#', ''); return [0, 2, 4].map(i => parseInt(h.substr(i, 2), 16)); };
const PHONE = () => innerWidth <= 980 || matchMedia('(pointer: coarse)').matches;

/* ------------------------------------------------------------------ palettes (per layer colour + stipple) */
// stipple ids (shader): 0 solid, 1 '/', 2 '\', 3 cross, 4 dots, 5 horizontal, 6 vertical, 7 dense '/', 8 sparse '\', 9 grid, 10 hollow
const PAL = {
  classic: {M1: ['#4f8dff', 1], M2: ['#ff5252', 2], M3: ['#3ddc84', 1], M4: ['#ffb300', 2], M5: ['#29d3f0', 7], M6: ['#e066ff', 8],
    M7: ['#ff8f3d', 3], M8: ['#ff7cc8', 9], M9: ['#a5e05a', 5], Pad: ['#b8b8b8', 6],
    V0: ['#9db6ff', 0], V1: ['#ffc0c0', 0], V2: ['#b6f5cf', 0], V3: ['#ffe08a', 0], V4: ['#b0f1fb', 0], V5: ['#f1c2ff', 0], V6: ['#ffd0b0', 0], V7: ['#ffd1ea', 0], V8: ['#d8f5b8', 0], V9: ['#e6e6e6', 0]},
  // colour-vision-deficiency safe (Okabe-Ito + Tol), stipples doubled up as the second cue
  cvd: {M1: ['#0072b2', 1], M2: ['#d55e00', 2], M3: ['#009e73', 5], M4: ['#e69f00', 6], M5: ['#56b4e9', 3], M6: ['#cc79a7', 7], M7: ['#f0e442', 8],
    M8: ['#882255', 9], M9: ['#44aa99', 4], Pad: ['#999999', 1],
    V0: ['#7fb8d8', 0], V1: ['#eaae7f', 0], V2: ['#7fcfb9', 0], V3: ['#f2cf7f', 0], V4: ['#aad9f4', 0], V5: ['#e5bcd3', 0], V6: ['#f7f1a0', 0], V7: ['#c390aa', 0], V8: ['#a1d4cc', 0], V9: ['#cccccc', 0]}};
const KINDS = [ // id, label, default visible
  [0, 'Signal wires', 1], [1, 'Power stripes', 1], [2, 'Follow-pin rails', 1], [3, 'Other special wires', 1], [4, 'Block pins', 1], [5, 'Routing obstructions', 1],
  [6, 'Metal fill', 1], [7, 'Macro pins', 1], [8, 'Macro OBS', 1], [9, 'Signal vias', 1], [10, 'Power vias', 1], [11, 'Cell pins', 1], [12, 'Cell OBS', 1], [13, 'Cell outlines', 1], [14, 'Filler / tap outlines', 0],
  [15, 'Via arrays (merged)', 1], [16, 'Via array cuts', 1]];
const KIND_NAME = Object.fromEntries(KINDS.map(k => [k[0], k[1].replace(/s$/, '')]));
const HEAT = ['#2c7bb6', '#7fbfdc', '#e6f5c9', '#fee08b', '#fc8d59', '#d7191c'];
const ARR = ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'];
function ramp(r, t){ t = Math.max(0, Math.min(1, t)); const k = t * (r.length - 1), i = Math.min(r.length - 2, Math.floor(k)), f = k - i, a = hex(r[i]), b = hex(r[i + 1]); return [0, 1, 2].map(j => Math.round(a[j] + (b[j] - a[j]) * f)); }

/* ------------------------------------------------------------------ the instanced rectangle layer */
const VS = `#define SHADER_NAME lv-rect-vs
attribute vec3 positions;
attribute vec4 instanceRects;
attribute vec3 instanceMeta;
uniform vec4 uColor[48];
uniform float uAlpha[48];
uniform float uPat[48];
uniform float uKind[20];
uniform float uHl;
uniform float uPx;
varying vec4 vColor; varying vec2 vPx; varying vec2 vSz; varying float vClip; varying float vPat;
void main(void){
  int li = int(instanceMeta.x + 0.5);
  float fl = instanceMeta.y;
  float clip = mod(fl, 16.0);
  int kind = int(floor(fl / 16.0) + 0.5);
  float a = uAlpha[li];
  if (a <= 0.0 || uKind[kind] < 0.5) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  vec2 lo = instanceRects.xy, hi = instanceRects.zw;
  vec2 sz = (hi - lo) * uPx;
  vec2 grow = max(vec2(0.0), (vec2(1.0) - sz) / uPx) * 0.5;
  lo -= grow; hi += grow;
  vec2 p = mix(lo, hi, positions.xy);
  vSz = max(sz, vec2(1.0));
  vPx = positions.xy * vSz;
  vClip = clip; vPat = uPat[li];
  vec3 col = uColor[li].rgb;
  if (uHl > 0.0) {
    if (abs(instanceMeta.z - uHl) < 0.5) { a = 1.0; col = mix(col, vec3(1.0), 0.35); vPat = 0.0; }
    else a *= 0.16;
  }
  vColor = vec4(col, a);
  gl_Position = project_position_to_clipspace(vec3(p, 0.0), vec3(0.0), vec3(0.0));
}`;
const FS = `#define SHADER_NAME lv-rect-fs
precision highp float;
uniform float uFill;
varying vec4 vColor; varying vec2 vPx; varying vec2 vSz; varying float vClip; varying float vPat;
float stip(float pat, vec2 f){
  float x = floor(f.x), y = floor(f.y);
  if (pat < 0.5) return 1.0;
  if (pat < 1.5) return step(mod(x + y, 6.0), 0.5);
  if (pat < 2.5) return step(mod(x - y, 6.0), 0.5);
  if (pat < 3.5) return max(step(mod(x + y, 6.0), 0.5), step(mod(x - y, 6.0), 0.5));
  if (pat < 4.5) return step(mod(x, 4.0), 0.5) * step(mod(y, 4.0), 0.5);
  if (pat < 5.5) return step(mod(y, 4.0), 0.5);
  if (pat < 6.5) return step(mod(x, 4.0), 0.5);
  if (pat < 7.5) return step(mod(x + y, 3.0), 0.5);
  if (pat < 8.5) return step(mod(x - y, 9.0), 0.5);
  if (pat < 9.5) return max(step(mod(x, 5.0), 0.5), step(mod(y, 5.0), 0.5));
  return 0.0;
}
void main(void){
  float l = mod(vClip, 2.0), r = mod(floor(vClip / 2.0), 2.0), b = mod(floor(vClip / 4.0), 2.0), t = mod(floor(vClip / 8.0), 2.0);
  bool edge = (l < 0.5 && vPx.x < 1.0) || (r < 0.5 && vSz.x - vPx.x < 1.0) || (b < 0.5 && vPx.y < 1.0) || (t < 0.5 && vSz.y - vPx.y < 1.0);
  float alpha;
  if (vPat > 9.5) alpha = (vSz.x < 6.0 || vSz.y < 6.0) ? 0.0 : (edge ? vColor.a : 0.0);   // hollow (cell outlines): only once legible
  else if (edge || vSz.x < 4.0 || vSz.y < 4.0) alpha = vColor.a;
  else alpha = vColor.a * (uFill + (1.0 - uFill) * 0.9 * stip(vPat, gl_FragCoord.xy));
  if (alpha < 0.004) discard;
  gl_FragColor = vec4(vColor.rgb, alpha);
}`;
let RectLayer = null;
function defineLayer(){
  const {Layer, project32} = window.deck; const {Model, Geometry} = window.luma;
  class LVRectLayer extends Layer {
    getShaders(){ return super.getShaders({vs: VS, fs: FS, modules: [project32]}); }
    initializeState(){
      this.getAttributeManager().addInstanced({instanceRects: {size: 4, noAlloc: true}, instanceMeta: {size: 3, noAlloc: true}});
      this.setState({model: this._model()});
    }
    _model(){
      return new Model(this.context.gl, Object.assign({}, this.getShaders(), {id: this.props.id, isInstanced: true,
        geometry: new Geometry({drawMode: 6, vertexCount: 4, attributes: {positions: {size: 3, value: new Float32Array([0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0])}}})}));
    }
    draw({uniforms}){ this.state.model.setUniforms(uniforms).setUniforms(this.props.lv).draw(); }
  }
  LVRectLayer.layerName = 'LVRectLayer';
  LVRectLayer.defaultProps = {lv: {type: 'object', value: {}}};
  RectLayer = LVRectLayer;
}

/* ------------------------------------------------------------------ viewer */
const V = {open: false};
let deckgl = null;

function urlState(){
  const m = location.hash.replace(/^#/, '').split('&').map(x => x.split('=')); const o = {}; m.forEach(([k, v]) => { if (k) o[k] = decodeURIComponent(v || ''); }); return o;
}
let urlTimer = 0;
function saveUrl(){
  clearTimeout(urlTimer);
  urlTimer = setTimeout(() => {
    if (!V.open || !V.vs) return;
    const o = urlState(); o.tab = 'geo';
    o.v = [Math.round(V.vs.target[0]), Math.round(V.vs.target[1]), V.vs.zoom.toFixed(2)].join(',');
    const hid = V.L.map((l, i) => l.vis ? '' : l.name).filter(Boolean); if (hid.length) o.h = hid.join('.'); else delete o.h;
    const kh = KINDS.filter(k => !V.kindVis[k[0]]).map(k => k[0]); if (kh.join(',') !== '14') o.k = kh.join('.'); else delete o.k;
    if (V.hl) o.n = String(V.hl); else delete o.n;
    const ov = Object.keys(V.ov).filter(k => V.ov[k]); if (ov.length) o.o = ov.join('.'); else delete o.o;
    if (V.lintSel != null) o.f = String(V.lintSel); else delete o.f;
    if (V.manifest && V.index && V.manifest.job !== V.index.latest) o.j = V.manifest.job; else delete o.j;
    try { history.replaceState(null, '', location.pathname + location.search + '#' + Object.entries(o).map(([k, v]) => k + '=' + encodeURIComponent(v).replace(/%2C/g, ',')).join('&')); } catch (e) {}
  }, 250);
}

async function api(path, opt){ const r = await fetch(V.base + path, opt); if (!r.ok) throw new Error(r.status + ' ' + path); return r; }
const blobUrl = name => {
  if (V.objects){ const h = V.objects[name]; return h ? '/layout_store/objects/' + h.slice(0, 2) + '/' + h + '.br' : null; }
  return V.base + 'b/' + name + '?v=' + V.ver;
};
async function blobJSON(name){ const u = blobUrl(name); if (!u) throw new Error('no ' + name); const r = await fetch(u); if (!r.ok) throw new Error(r.status + ' ' + name); return r.json(); }
async function blobBuf(name){ const u = blobUrl(name); if (!u) throw new Error('no ' + name); const r = await fetch(u); if (!r.ok) throw new Error(r.status + ' ' + name); return r.arrayBuffer(); }

function open(o){
  // o: {root, side, nav (optional: layers + overlay toggles go here, read-outs stay in side), el, d (element JSON), E (elem.js prepped element or null), safe, onFallback}
  Object.assign(V, {open: true, root: o.root, side: o.side, nav: o.nav || null, el: o.el, d: o.d, E: o.E, safe: o.safe, onFallback: o.onFallback, base: '/api/layout/' + encodeURIComponent(o.el) + '/'});
  if (V.loadedFor === o.el && deckgl){ V.root.hidden = false; V.side.hidden = false; if (V.nav) V.nav.hidden = false; renderSide(); requestUpdate(); return; }
  close(true);
  V.loadedFor = o.el;
  V.root.innerHTML = `<div class="lv-busy" data-busy><div class="lv-spin"></div><div data-msg>Checking the routed geometry&hellip;</div></div>`;
  V.side.innerHTML = ''; if (V.nav) V.nav.innerHTML = '';
  poll();
}
function close(keep){
  if (!keep) { V.open = false; return; }
  if (deckgl){ deckgl.finalize(); deckgl = null; }
  if (V.workers) V.workers.forEach(w => w.terminate());
  Object.assign(V, {workers: null, tiles: new Map(), rasters: new Map(), header: null, hl: 0, lintSel: null, rulers: [], rulerMode: false, pending: new Map(),
    objects: null, manifest: null, index: null, tidx: null, firstPaint: null, firstGeo: null, miniBg: null, congIm: null, stats: null});
}
async function poll(){
  const el = V.el;
  let st;
  try { st = await (await api('status?prepare=1')).json(); } catch (e) { st = {state: 'failed', error: String(e)}; }
  if (V.el !== el || !V.open) return;
  const msg = V.root.querySelector('[data-msg]');
  if (st.state === 'static' && !V.safe){
    try {
      V.index = await (await fetch(st.index)).json();
      const job = (urlState().j && V.index.history.includes(urlState().j)) ? urlState().j : V.index.latest;
      V.manifest = await (await fetch('/layout_store/elements/' + encodeURIComponent(V.el) + '/' + encodeURIComponent(job) + '.json')).json();
      V.objects = V.manifest.objects; V.ver = V.manifest.id;
      return start();
    } catch (e) { console.warn('static store', e); }
  }
  if (st.state === 'static'){ V.ver = st.id; return start(); }   // share-safe view: the same closure through /api/layout (redacted)
  if (st.state === 'ready'){ V.ver = st.version; return start(); }
  if (st.state === 'nodb'){
    V.root.innerHTML = `<div class="lv-busy"><div><b>No routed database for this element.</b><br>${esc(st.reason || '')}<br><br><button class="btn" data-fb>Open the placement view</button></div></div>`;
    V.root.querySelector('[data-fb]').onclick = () => V.onFallback && V.onFallback();
    return;
  }
  if (st.state === 'failed'){
    V.root.innerHTML = `<div class="lv-busy"><div><b>The geometry could not be cut.</b><br><span class="lv-dim">${esc(st.error || '')}</span><br><br>
      <button class="btn" data-fb>Open the placement view</button> <button class="btn" data-retry>Retry</button></div></div>`;
    V.root.querySelector('[data-fb]').onclick = () => V.onFallback && V.onFallback();
    V.root.querySelector('[data-retry]').onclick = () => { V.loadedFor = null; open(V); };
    return;
  }
  if (msg) msg.innerHTML = `Cutting the routed geometry from the final DB${st.host ? ' on <b>' + esc(V.safe ? 'a fleet host' : st.host) + '</b>' : ''}&hellip;<br><span class="lv-dim">${esc(st.stage || st.state)}</span>
    <br><br><button class="btn" data-fb>Open the placement view meanwhile</button>`;
  const fb = V.root.querySelector('[data-fb]'); if (fb) fb.onclick = () => V.onFallback && V.onFallback();
  setTimeout(poll, 2500);
}

async function loadScript(src){ return new Promise((res, rej) => { const s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = () => rej(new Error('load ' + src)); document.head.appendChild(s); }); }

async function start(){
  const t0 = performance.now();
  V.t0 = t0;
  try {
    if (!window.deck) await loadScript('/explorer/element/vendor/deck.gl-8.9.36.min.js');
    if (!RectLayer) defineLayer();
    const H = await blobJSON('header');
    V.header = H;
  } catch (e) {
    V.root.innerHTML = `<div class="lv-busy"><div><b>Viewer failed to start.</b><br><span class="lv-dim">${esc(String(e))}</span><br><br><button class="btn" data-fb>Open the placement view</button></div></div>`;
    V.root.querySelector('[data-fb]').onclick = () => V.onFallback && V.onFallback(); return;
  }
  const H = V.header, nl = H.layers.length;
  V.dbu = H.dbu; V.die = H.die;
  V.palette = lsGet('pal', 'classic');
  // layer table: real layers + synthetic (cell outlines, physical-only cell outlines) + macros (separate deck layer)
  V.L = H.layers.map((l, i) => ({i, name: l.name, type: l.type, dir: l.dir, n: H.counts.layer_rects[i] || 0, vis: true, op: l.type === 'CUT' ? 0.85 : 0.7}));
  V.L.push({i: nl, name: 'Cells', type: 'CELLS', vis: true, op: 0.55}, {i: nl + 1, name: 'Filler / tap', type: 'PHYS', vis: false, op: 0.35});
  V.kindVis = Object.fromEntries(KINDS.map(k => [k[0], !!k[2]]));
  V.ov = {macros: true};
  const u = urlState();
  if (u.h) { const hid = new Set(u.h.split('.')); V.L.forEach(l => { if (hid.has(l.name)) l.vis = false; }); }
  if (u.k != null) { const kh = new Set(u.k.split('.').filter(Boolean).map(Number)); KINDS.forEach(k => V.kindVis[k[0]] = !kh.has(k[0])); }
  if (u.o) u.o.split('.').forEach(k => V.ov[k] = true);
  V.hl = +u.n || 0; V.lintSel = u.f != null && u.f !== '' ? +u.f : null;
  V.phys = V.L[nl + 1].vis;
  // layers a via / a std cell can put shapes on (a solo metal layer still needs the vias' enclosures and the cells' pins)
  V.viaLayers = [...new Set(H.vias.flatMap(v => v.boxes.map(b => b[0])))];
  V.cellLayers = [...new Set(H.masters.filter(m => !m.block).flatMap(m => m.boxes.map(b => b[0])))];
  applyPalette();
  // workers
  const NW = Math.max(2, Math.min(4, (navigator.hardwareConcurrency || 4) - 1));
  V.workers = []; V.wnext = 0; V.tiles = new Map(); V.rasters = new Map(); V.pending = new Map(); V.rulers = []; V.gpuBytes = 0;
  for (let i = 0; i < NW; i++){ const w = new Worker('/explorer/element/lv_worker.js'); w.onmessage = onWorker; w.postMessage({op: 'init', header: H}); V.workers.push(w); }
  updateUniforms();   // pushes the raster style to the workers
  V.budget = PHONE() ? 1.2e6 : 3e6;
  V.gpuCap = PHONE() ? 150e6 : 300e6;
  // DOM
  if (SOLID){ V.root.style.background = '#000'; document.documentElement.classList.add('lv-solid'); }
  V.root.innerHTML = `
    <div class="lv-canvas" data-canvas></div>
    <div class="lv-top">
      <div class="lv-search"><input type="search" placeholder="${V.safe ? 'search hidden in the share-safe view' : 'Search net / instance…'}" ${V.safe ? 'disabled' : ''} data-q aria-label="Search nets and instances"><div class="lv-res" data-res hidden></div></div>
      <button class="btn" data-tool="fit" title="Fit (F)">Fit</button>
      <button class="btn" data-tool="ruler" title="Ruler (R): click two points">Ruler</button>
      <button class="btn" data-tool="clear" title="Clear highlight and rulers (Esc)">Clear</button>
    </div>
    <div class="lv-info" data-info></div>
    <canvas class="lv-mini" data-mini width="180" height="120" aria-label="Minimap"></canvas>
    <div class="lv-scale" data-scale><i></i><span></span></div>
    <div class="lv-coord" data-coord></div>
    <div class="lv-tip" data-tip hidden></div>`;
  const cvdiv = V.root.querySelector('[data-canvas]');
  const W = V.die[2] - V.die[0], Hh = V.die[3] - V.die[1];
  const r = cvdiv.getBoundingClientRect();
  const fitZoom = Math.log2(Math.min((r.width || 800) / W, (r.height || 600) / Hh) * 0.92);
  V.fitZoom = fitZoom;
  let vs = {target: [(V.die[0] + V.die[2]) / 2, (V.die[1] + V.die[3]) / 2, 0], zoom: fitZoom, minZoom: fitZoom - 3, maxZoom: 5};
  if (u.v){ const p = u.v.split(',').map(Number); if (p.length === 3 && p.every(isFinite)) vs = Object.assign(vs, {target: [p[0], p[1], 0], zoom: p[2]}); }
  V.vs = vs;
  deckgl = new deck.Deck({
    parent: cvdiv, views: new deck.OrthographicView({id: 'o', flipY: false, controller: true}),
    initialViewState: vs,
    controller: {scrollZoom: {speed: 0.012, smooth: false}, inertia: 250, doubleClickZoom: true, keyboard: true, dragRotate: false},
    onViewStateChange: ({viewState}) => { V.vs = viewState; requestUpdate(); saveUrl(); return viewState; },
    getCursor: ({isDragging}) => V.rulerMode ? 'crosshair' : isDragging ? 'grabbing' : 'default',
    onClick: onClick, onHover: onDeckHover,
    onAfterRender: () => { const t = performance.now(); const f = V.frames || (V.frames = []); f.push(t); while (f.length && t - f[0] > 2000) f.shift(); },
    useDevicePixels: Math.min(2, window.devicePixelRatio || 1),
    parameters: {clearColor: [0, 0, 0, 0], depthTest: false, blend: true},
    layers: []
  });
  V.deck = deckgl;
  V.tm = {deck: performance.now() - t0};
  cvdiv.addEventListener('pointermove', onMove);
  cvdiv.addEventListener('pointerleave', () => { V.root.querySelector('[data-tip]').hidden = true; V.root.querySelector('[data-coord]').textContent = ''; });
  bindTop();
  bindMini();
  renderSide();
  if (V.hl) netInfo(V.hl);
  loadOverview();
  loadOverlays();
  requestUpdate();
  V.tm.started = performance.now() - t0;
  V.root.addEventListener('keydown', onKey); V.root.tabIndex = 0;
}

/* ------------------------------------------------------------------ styles -> uniforms */
function themeBg(){ return cssv('color-scheme') === 'light' ? 'light' : 'dark'; }
const SOLID = /[?&]lvsolid=1/.test(location.search);   // regression mode: every layer solid white, no outline / stipple (tools/layout_viewer/lv_visual.py)
function applyPalette(){
  const P = PAL[V.palette] || PAL.classic, light = themeBg() === 'light';
  V.L.forEach(l => {
    let c, pat;
    if (l.type === 'CELLS'){ c = light ? '#6b7690' : '#8a97b8'; pat = 10; }
    else if (l.type === 'PHYS'){ c = light ? '#a7b0c4' : '#4a5678'; pat = 10; }
    else { const s = P[l.name] || ['#999999', 4]; c = s[0]; pat = s[1]; }
    if (light && l.type !== 'CELLS' && l.type !== 'PHYS'){ const a = hex(c); c = '#' + a.map(v => Math.round(v * 0.82).toString(16).padStart(2, '0')).join(''); }
    l.color = c; l.pat = pat;
    if (SOLID){ l.color = '#ffffff'; l.pat = 0; l.op = 1; }
  });
  updateUniforms();
}
function updateUniforms(){
  const col = new Float32Array(48 * 4), al = new Float32Array(48), pat = new Float32Array(48), kd = new Float32Array(20);
  V.L.forEach(l => { const c = hex(l.color); col.set([c[0] / 255, c[1] / 255, c[2] / 255, 1], l.i * 4); al[l.i] = l.vis ? l.op : 0; pat[l.i] = l.pat; });
  KINDS.forEach(k => kd[k[0]] = V.kindVis[k[0]] ? 1 : 0);
  kd[14] = V.L[V.L.length - 1].vis ? 1 : 0;   // physical-only outlines follow their layer row
  kd[15] = kd[16] = V.kindVis[10] ? 1 : 0;    // via arrays follow 'Power vias'
  V.uni = {uColor: col, uAlpha: al, uPat: pat, uKind: kd, uHl: V.hl || 0, uFill: SOLID ? 1 : themeBg() === 'light' ? 0.32 : 0.22, uPx: 1};
  V.styleVer = (V.styleVer || 0) + 1;
  if (V.workers){
    const st = {}; V.L.forEach(l => { const c = hex(l.color); st[l.i] = {r: c[0], g: c[1], b: c[2], a: l.vis ? l.op : 0}; });
    V.workers.forEach(w => w.postMessage({op: 'restyle', style: st}));
    V.rstyle = st;
  }
}

/* ------------------------------------------------------------------ LOD / tile management */
let upd = 0;
function requestUpdate(){ if (!upd) upd = requestAnimationFrame(() => { upd = 0; update(); }); }
function viewBounds(){
  const vp = deckgl && deckgl.getViewports()[0]; if (!vp) return null;
  const a = vp.unproject([0, 0]), b = vp.unproject([vp.width, vp.height]);
  return {x0: Math.min(a[0], b[0]), x1: Math.max(a[0], b[0]), y0: Math.min(a[1], b[1]), y1: Math.max(a[1], b[1]), w: vp.width, h: vp.height};
}
function tilesIn(b, margin){
  const G = V.header.grid, S = G.size, out = [];
  const tx0 = Math.max(0, Math.floor((b.x0 - G.ox) / S) - margin), tx1 = Math.min(G.nx - 1, Math.floor((b.x1 - G.ox) / S) + margin);
  const ty0 = Math.max(0, Math.floor((b.y0 - G.oy) / S) - margin), ty1 = Math.min(G.ny - 1, Math.floor((b.y1 - G.oy) / S) + margin);
  for (let y = ty0; y <= ty1; y++) for (let x = tx0; x <= tx1; x++) out.push([x, y]);
  return out;
}
function tileIndex(){
  if (!V.tidx){ V.tidx = new Map(); (V.header.grid.tiles || []).forEach(t => V.tidx.set(t.x + '_' + t.y, t)); }
  return V.tidx;
}
function shapeCost(t){
  let n = 0; for (const l of V.L) if (l.vis && l.i < t.n.length) n += t.n[l.i];
  if (V.kindVis[9] || V.kindVis[10]) n += t.v * 3;
  const cl = V.L[V.L.length - 2]; if (cl.vis) n += t.c * 4;   // std cells: outline + ~3 pin shapes
  if (V.phys) n += (t.cp || 0) * 3;
  return n;
}
function update(){
  if (!deckgl || !V.header) return;
  const b = viewBounds(); if (!b) return;
  const ppu = Math.pow(2, V.vs.zoom);               // css px per DBU
  const upx = ppu * Math.min(2, window.devicePixelRatio || 1); if (V.uni.uPx !== upx) V.uni = Object.assign({}, V.uni, {uPx: upx});
  const TI = tileIndex();
  const vis = tilesIn(b, 0).map(([x, y]) => x + '_' + y).filter(k => TI.has(k));
  // the header's per-tile counts estimate the instances a tile becomes; loaded tiles calibrate the estimate
  let est = 0, act = 0; for (const [k, t] of V.tiles){ if (t.n && TI.has(k)){ est += shapeCost(TI.get(k)); act += t.n; } }
  const scale = est > 0 ? Math.max(0.5, Math.min(20, act / est)) : 1;
  let cost = 0; vis.forEach(k => cost += shapeCost(TI.get(k)) * scale);
  const geo = cost <= V.budget && ppu * 1000 >= 0.25;   // >= 0.25 px per um and within the shape budget
  V.mode = geo ? 'geometry' : 'raster';
  const want = new Set();
  if (geo && V.lastArrDetail !== arrDetail()){ V.lastArrDetail = arrDetail(); refreshTiles(); }
  if (geo){
    // a one-tile prefetch ring, unless tiles are heavy (dense via arrays at full detail): then only what is on screen
    const perTile = vis.length ? cost / vis.length : 0;
    const heavy = perTile > 4e5 || (arrDetail() && [...V.tiles.values()].some(t => t.hasArr));   // via arrays cut by cut: on-screen only
    const near = tilesIn(b, heavy ? 0 : 1).map(([x, y]) => x + '_' + y).filter(k => TI.has(k));
    const cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2, G = V.header.grid;
    near.sort((p, q) => dist(p) - dist(q));
    function dist(k){ const [x, y] = k.split('_').map(Number); return (G.ox + (x + .5) * G.size - cx) ** 2 + (G.oy + (y + .5) * G.size - cy) ** 2; }
    near.forEach(k => want.add(k));
    for (const k of near) if (!V.tiles.has(k) && !V.pending.has('t/' + k)) requestTile(k);
  }
  // rasters: always the overview (level 0); in raster mode the level whose pixel ~ a screen pixel
  const R = V.header.raster; const lv = R.levels;
  let level = 0;
  for (const L of lv){ level = L.level; if (L.px_nm * ppu <= 1.5) break; }   // coarsest level with a raster pixel <= 1.5 screen px
  V.rlevel = level;
  if (!geo || vis.some(k => !V.tiles.has(k))){
    const L = lv.find(q => q.level === level);
    if (L){ const node = L.node_nm; const have = new Set(L.nodes.map(n => n[0] + '_' + n[1]));
      const nx0 = Math.max(0, Math.floor((b.x0 - V.die[0]) / node)), nx1 = Math.floor((b.x1 - V.die[0]) / node);
      const ny0 = Math.max(0, Math.floor((b.y0 - V.die[1]) / node)), ny1 = Math.floor((b.y1 - V.die[1]) / node);
      for (let y = ny0; y <= ny1; y++) for (let x = nx0; x <= nx1; x++){ const k = level + '/' + x + '_' + y; if (have.has(x + '_' + y) && !V.rasters.has(k) && !V.pending.has('r/' + k)) requestRaster(k); }
    }
  }
  V.want = want;
  // GPU memory: evict least-recently-wanted tiles beyond the cap
  if (V.gpuBytes > V.gpuCap){
    const lru = [...V.tiles.entries()].filter(([k]) => !want.has(k)).sort((a, b2) => a[1].used - b2[1].used);
    for (const [k, t] of lru){ if (V.gpuBytes <= V.gpuCap * 0.8) break; V.gpuBytes -= t.bytes; V.tiles.delete(k); }
  }
  const now = performance.now(); want.forEach(k => { const t = V.tiles.get(k); if (t) t.used = now; });
  render(b, geo, want, level);
  drawMini(); drawScale(ppu); renderInfo(cost, vis.length);
}
function neededSecs(k){
  const t = tileIndex().get(k); if (!t) return [];
  const nl = V.header.layers.length, L = V.L, out = [];
  const secs = t.s || [];
  for (const s of secs){
    if (s[0] === 'L'){ const li = +s.slice(1); if (L[li] && L[li].vis) out.push(s); }
    else if (s === 'v'){ if ((V.kindVis[9] || V.kindVis[10]) && V.viaLayers.some(li => L[li].vis)) out.push(s); }   // cut AND enclosure layers
    else if (s === 'c'){ if (L[nl].vis || L[nl + 1].vis || V.cellLayers.some(li => L[li].vis)) out.push(s); }
  }
  return out;
}
function requestTile(k){
  const secs = neededSecs(k);
  if (!secs.length){ V.tiles.set(k, {n: 0, empty: true, secs: [], bytes: 0, used: performance.now()}); return; }
  const w = V.workers[V.wnext++ % V.workers.length];
  V.pending.set('t/' + k, performance.now());
  w.postMessage({op: 'tile', key: k, parts: secs.map(s => ({name: s, url: location.origin + blobUrl('t/' + k + '/' + s)})), phys: V.phys, arrDetail: arrDetail()});
}
function refreshTiles(){   // a layer switched on: tiles that lack its section are fetched again (cached sections are reused)
  const ad = arrDetail();
  for (const [k, t] of V.tiles){ const need = neededSecs(k);
    if ((need.some(s => !(t.secs || []).includes(s)) || (t.hasArr && t.arrDetail !== ad)) && !V.pending.has('t/' + k)) requestTile(k); }
}
// via-array cuts become individual shapes once a cut is ~4 device pixels (ASAP7 power-via cuts are 18-24 nm)
function arrDetail(){ return Math.pow(2, V.vs.zoom) * Math.min(2, window.devicePixelRatio || 1) >= 0.2; }
function requestRaster(k){
  const w = V.workers[V.wnext++ % V.workers.length];
  V.pending.set('r/' + k, performance.now());
  const u = blobUrl('r/' + k); if (!u){ V.pending.delete('r/' + k); return; }
  w.postMessage({op: 'raster', key: k, url: location.origin + u, style: V.rstyle});
}
function onWorker(ev){
  const m = ev.data;
  if (m.op === 'tile'){
    V.pending.delete('t/' + m.key);
    if (!V.header) return;
    if (V.want && !V.want.has(m.key) && V.gpuBytes > V.gpuCap * 0.6){ requestUpdate(); return; }   // no longer needed: drop
    const bytes = m.n * 28, old = V.tiles.get(m.key);
    if (old) V.gpuBytes -= old.bytes || 0;
    V.tiles.set(m.key, {n: m.n, rects: m.rects, meta: m.meta, pick: m.pick, ox: m.ox, oy: m.oy, bytes, secs: m.secs, hasArr: m.hasArr, arrDetail: m.arrDetail, used: performance.now(), layer: null});
    V.gpuBytes += bytes;
    V.stats = V.stats || {tiles: 0, ms: 0, bytes: 0}; V.stats.tiles++; V.stats.ms += m.ms[1]; V.stats.bytes += m.bytes;
    if (!V.firstGeo){ V.firstGeo = performance.now() - V.t0; }
    requestUpdate();
  } else if (m.op === 'raster'){
    V.pending.delete('r/' + m.key);
    const im = new ImageData(new Uint8ClampedArray(m.rgba.buffer), m.size, m.size);
    const prev = V.rasters.get(m.key);
    V.rasters.set(m.key, {im, v: (prev ? prev.v : 0) + 1});
    if (m.key.startsWith('0/') && !V.firstPaint){ V.firstPaint = performance.now() - V.t0; }
    if (m.key.startsWith('0/')) V.miniDirty = true;
    requestUpdate();
  } else if (m.op === 'error'){
    V.pending.delete((m.what === 'tile' ? 't/' : 'r/') + m.key);
    console.warn('layout worker', m);
  }
}
function loadOverview(){
  const L0 = V.header.raster.levels.find(q => q.level === 0);
  if (L0) L0.nodes.forEach(n => requestRaster('0/' + n[0] + '_' + n[1]));
}

/* ------------------------------------------------------------------ deck layers */
function render(b, geo, want, level){
  const layers = [];
  const R = V.header.raster, C = deck.COORDINATE_SYSTEM.CARTESIAN;
  const rl = (lvl) => { const L = R.levels.find(q => q.level === lvl); if (!L) return; const node = L.node_nm;
    for (const n of L.nodes){ const k = lvl + '/' + n[0] + '_' + n[1], r = V.rasters.get(k); if (!r) continue;
      const x0 = V.die[0] + n[0] * node, y0 = V.die[1] + n[1] * node;
      if (x0 > b.x1 || y0 > b.y1 || x0 + node < b.x0 || y0 + node < b.y0) continue;
      layers.push(new deck.BitmapLayer({id: 'r' + k + ':' + r.v, image: r.im, bounds: [x0, y0, x0 + node, y0 + node], coordinateSystem: C,
        textureParameters: {[10240]: lvl === level && !geo ? 9728 : 9729, [10241]: 9729}, opacity: 1})); } };
  const allLoaded = geo && [...want].every(k => V.tiles.has(k) || !tileIndex().has(k));
  if (!allLoaded){ rl(0); if (level !== 0) rl(level); }
  if (geo){
    const vis = new Set(tilesIn(b, 0).map(([x, y]) => x + '_' + y));   // margin tiles stay loaded but are not drawn
    for (const k of want){ if (!vis.has(k)) continue; const t = V.tiles.get(k); if (!t || t.empty || !t.n) continue;
      layers.push(new RectLayer({id: 't' + k, data: {length: t.n, attributes: {instanceRects: {value: t.rects, size: 4}, instanceMeta: {value: t.meta, size: 3}}},
        coordinateSystem: C, lv: V.uni})); }
  }
  if (SOLID){ deckgl.setProps({layers}); return; }
  // die / core outline + macros
  const D = V.die, Co = V.header.core, fg = hex(cssv('--faint') || '#4a5678');
  layers.push(new deck.PathLayer({id: 'die', data: [{p: [[D[0], D[1]], [D[2], D[1]], [D[2], D[3]], [D[0], D[3]], [D[0], D[1]]], c: [...fg, 255]},
    {p: [[Co[0], Co[1]], [Co[2], Co[1]], [Co[2], Co[3]], [Co[0], Co[3]], [Co[0], Co[1]]], c: [...fg, 120]}], getPath: d => d.p, getColor: d => d.c,
    widthUnits: 'pixels', getWidth: 1, coordinateSystem: C}));
  if (V.ov.macros && V.header.macros.length){
    const mc = hex(cssv('--macro') || '#a78bfa');
    layers.push(new deck.PolygonLayer({id: 'macros', data: V.header.macros, getPolygon: m => { const q = m.bbox; return [[q[0], q[1]], [q[2], q[1]], [q[2], q[3]], [q[0], q[3]]]; },
      getFillColor: [...mc, geo ? 10 : 40], getLineColor: [...mc, 230], lineWidthUnits: 'pixels', getLineWidth: 1.5, coordinateSystem: C, pickable: true}));
  }
  overlayLayers(layers, b, geo);
  // rulers
  const rs = V.rulers.concat(V.rulerLive ? [V.rulerLive] : []);
  if (rs.length){
    const ac = hex(cssv('--story') || '#ffd23f');
    layers.push(new deck.LineLayer({id: 'rulers', data: rs, getSourcePosition: r => r.a, getTargetPosition: r => r.b, getColor: [...ac, 255], widthUnits: 'pixels', getWidth: 2, coordinateSystem: C}));
    layers.push(new deck.TextLayer({id: 'rulert', data: rs, getPosition: r => [(r.a[0] + r.b[0]) / 2, (r.a[1] + r.b[1]) / 2], getText: r => rulerText(r), getSize: 12, characterSet: 'auto',
      getColor: [...ac, 255], background: true, getBackgroundColor: themeBg() === 'light' ? [255, 255, 255, 220] : [5, 7, 13, 220], backgroundPadding: [4, 2],
      fontFamily: 'ui-monospace, Menlo, monospace', getTextAnchor: 'start', getAlignmentBaseline: 'bottom', getPixelOffset: [6, -6], coordinateSystem: C}));
  }
  if (V.flash){ const f = V.flash, ac = hex(cssv('--accent') || '#5ee7ff');
    layers.push(new deck.PolygonLayer({id: 'flash', data: [f], getPolygon: q => [[q[0], q[1]], [q[2], q[1]], [q[2], q[3]], [q[0], q[3]]], filled: false, stroked: true, getLineColor: [...ac, 255], lineWidthUnits: 'pixels', getLineWidth: 2.5, coordinateSystem: C})); }
  deckgl.setProps({layers});
}
function rulerText(r){ const dx = (r.b[0] - r.a[0]) / V.dbu, dy = (r.b[1] - r.a[1]) / V.dbu; return `${fmt(Math.hypot(dx, dy), 3)} \u00b5m  (dx ${fmt(dx, 3)}, dy ${fmt(dy, 3)})`; }

/* ------------------------------------------------------------------ overlays */
async function loadOverlays(){
  try { V.lint = await blobJSON('lint'); } catch (e) { V.lint = {error: String(e), findings: []}; }
  try { V.cong = LVDecode.decodeCong(await blobBuf('cong')); } catch (e) { V.cong = null; }
  V.congLayer = V.congLayer != null ? V.congLayer : 'max';
  prepClock(); prepModules();
  renderSide(); requestUpdate();
}
function um2dbu(v){ return v * V.dbu; }
function prepClock(){
  const d = V.d; if (!d || !d.clock_tt){ V.clk = null; return; }
  const N = d.clock_tt.nodes, L = d.clock_tt.leaves;
  const arr = L.map(l => l[3]).filter(v => v != null).sort((a, b) => a - b);
  const lo = arr.length ? arr[Math.floor(arr.length * 0.01)] : 0, hi = arr.length ? arr[Math.floor(arr.length * 0.99)] : 1;
  const edges = [];
  N.forEach(n => { if (n[2] >= 0){ const p = N[n[2]]; edges.push({a: [um2dbu(p[0]), um2dbu(p[1])], b: [um2dbu(n[0]), um2dbu(n[1])], t: n[5]}); } });
  L.forEach(l => { const p = N[l[2]]; if (p) edges.push({a: [um2dbu(p[0]), um2dbu(p[1])], b: [um2dbu(l[0]), um2dbu(l[1])], t: l[3], leaf: 1}); });
  V.clk = {lo, hi, edges, leaves: L.filter(l => l[3] != null).map(l => ({p: [um2dbu(l[0]), um2dbu(l[1])], t: l[3], name: l[4]})),
    bufs: N.map(n => ({p: [um2dbu(n[0]), um2dbu(n[1])], t: n[5], m: n[4], name: n[6], lvl: n[3]}))};
}
function prepModules(){
  const E = V.E; V.mods = null; if (!E || !E.groups) return;
  const g = E.groups.map(() => [Infinity, Infinity, -Infinity, -Infinity, 0]);
  for (let i = 0; i < E.n; i++){ const k = E.grp[i], q = g[k]; const x = E.x[i], y = E.y[i];
    if (x < q[0]) q[0] = x; if (y < q[1]) q[1] = y; if (x + E.w[i] > q[2]) q[2] = x + E.w[i]; if (y + E.h[i] > q[3]) q[3] = y + E.h[i]; q[4]++; }
  V.mods = E.groups.map((G, k) => ({name: G.name, color: G.color, n: g[k][4], bb: [V.die[0] + um2dbu(g[k][0]), V.die[1] + um2dbu(g[k][1]), V.die[0] + um2dbu(g[k][2]), V.die[1] + um2dbu(g[k][3])]}))
    .filter(m => m.n > 0 && !m.name.startsWith('(other') && m.name !== '(unattributed)');
}
function overlayLayers(layers, b, geo){
  const C = deck.COORDINATE_SYSTEM.CARTESIAN, light = themeBg() === 'light';
  if (V.ov.cong && V.cong){
    const c = V.cong, key = 'cong:' + V.congLayer + ':' + themeBg();
    if (!V.congIm || V.congIm.key !== key){
      const n = c.gx * c.gy, rgba = new Uint8ClampedArray(n * 4);
      const sel = V.congLayer === 'max' ? c.planes.map((_, i) => i) : [c.layers.indexOf(+V.congLayer)];
      for (let p = 0; p < n; p++){ let v = 0; for (const s of sel) if (s >= 0) v = Math.max(v, c.planes[s][p]);
        const y = c.gy - 1 - Math.floor(p / c.gx), x = p % c.gx, o = (y * c.gx + x) * 4;
        if (v < 3) continue; const col = ramp(HEAT, Math.min(1, v / 110)); rgba[o] = col[0]; rgba[o + 1] = col[1]; rgba[o + 2] = col[2]; rgba[o + 3] = 150 + Math.min(105, v); }
      V.congIm = {key, im: new ImageData(rgba, c.gx, c.gy)};
    }
    const bg = hex(cssv('--canvas') || '#03050b');
    layers.push(new deck.PolygonLayer({id: 'congdim', data: [V.die], getPolygon: q => [[q[0], q[1]], [q[2], q[1]], [q[2], q[3]], [q[0], q[3]]], getFillColor: [...bg, 200], stroked: false, coordinateSystem: C}));
    layers.push(new deck.BitmapLayer({id: 'cong:' + key, image: V.congIm.im, bounds: [V.die[0], V.die[1], V.die[0] + c.gx * c.bin, V.die[1] + c.gy * c.bin],
      coordinateSystem: C, textureParameters: {[10240]: 9728, [10241]: 9728}, opacity: 0.85}));
  }
  if (V.ov.mods && V.mods){
    layers.push(new deck.PolygonLayer({id: 'mods', data: V.mods, getPolygon: m => { const q = m.bb; return [[q[0], q[1]], [q[2], q[1]], [q[2], q[3]], [q[0], q[3]]]; },
      filled: false, getLineColor: m => [...hex(m.color), 230], lineWidthUnits: 'pixels', getLineWidth: 2, coordinateSystem: C}));
    layers.push(new deck.TextLayer({id: 'modt', data: V.mods, getPosition: m => [m.bb[0], m.bb[3]], getText: m => V.safe ? 'block' : m.name, getSize: 11, characterSet: 'auto', getColor: m => [...hex(m.color), 255],
      getTextAnchor: 'start', getAlignmentBaseline: 'top', getPixelOffset: [4, 4], fontFamily: 'ui-monospace, Menlo, monospace', background: true,
      getBackgroundColor: light ? [255, 255, 255, 200] : [5, 7, 13, 200], coordinateSystem: C}));
  }
  if (V.ov.clock && V.clk){
    const k = V.clk, col = t => [...ramp(ARR, (t - k.lo) / Math.max(1e-6, k.hi - k.lo)), 235];
    layers.push(new deck.LineLayer({id: 'clke', data: k.edges, getSourcePosition: e => e.a, getTargetPosition: e => e.b, getColor: e => e.t == null ? [128, 128, 128, 120] : col(e.t),
      widthUnits: 'pixels', getWidth: e => e.leaf ? 0.8 : 1.6, coordinateSystem: C}));
    layers.push(new deck.ScatterplotLayer({id: 'clkl', data: k.leaves, getPosition: l => l.p, getFillColor: l => col(l.t), radiusUnits: 'pixels', getRadius: 1.6,
      coordinateSystem: C, pickable: true}));
    layers.push(new deck.ScatterplotLayer({id: 'clkb', data: k.bufs, getPosition: l => l.p, getFillColor: l => l.t == null ? [200, 200, 200, 255] : col(l.t), stroked: true,
      getLineColor: light ? [0, 0, 0, 200] : [255, 255, 255, 200], lineWidthUnits: 'pixels', getLineWidth: 0.8, radiusUnits: 'pixels', getRadius: 3, coordinateSystem: C, pickable: true}));
  }
  if (V.ov.paths && V.d){
    const which = V.pcorner || 'setup', P = ((which === 'hold' ? V.d.hold_paths : V.d.setup_paths) || []).slice(0, 15), sel = V.psel || 0;
    const pc = hex(which === 'hold' ? (cssv('--hold') || '#fbbf24') : (cssv('--path') || '#ff5d73'));
    const data = P.map((p, i) => ({i, p, path: p.points.filter(q => q[5] != null).map(q => [um2dbu(q[5]), um2dbu(q[6])])}));
    layers.push(new deck.PathLayer({id: 'paths', data, getPath: d => d.path, getColor: d => [...pc, d.i === sel ? 255 : 70], widthUnits: 'pixels',
      getWidth: d => d.i === sel ? 3 : 1.2, coordinateSystem: C, pickable: true, updateTriggers: {getColor: sel, getWidth: sel}}));
    const cur = data[sel];
    if (cur) layers.push(new deck.ScatterplotLayer({id: 'pathpins', data: cur.p.points.filter(q => q[5] != null), getPosition: q => [um2dbu(q[5]), um2dbu(q[6])],
      getFillColor: q => q[4] === 'o' ? [...pc, 255] : [255, 255, 255, 230], getLineColor: [...pc, 255], stroked: true, lineWidthUnits: 'pixels', getLineWidth: 1.5,
      radiusUnits: 'pixels', getRadius: 3.5, coordinateSystem: C, pickable: true}));
  }
  if (V.ov.lint && V.lint && V.lint.findings && V.lint.findings.length){
    const F = V.lint.findings, sel = V.lintSel;
    const sh = []; F.forEach(f => (sel == null || sel === f.id) && f.shapes.forEach(s => sh.push({f, s})));
    const red = [255, 77, 99], amb = [255, 184, 0];
    layers.push(new deck.PolygonLayer({id: 'lints', data: sh, getPolygon: d => { const s = d.s; return [[s[1], s[2]], [s[3], s[2]], [s[3], s[4]], [s[1], s[4]]]; },
      getFillColor: d => [...(d.s[5] === 'obs' ? amb : red), 60], getLineColor: d => [...(d.s[5] === 'obs' ? amb : red), 255], lineWidthUnits: 'pixels', getLineWidth: 2,
      coordinateSystem: C, pickable: true}));
    const mk = F.filter(f => f.bbox).map(f => ({f, p: [(f.bbox[0] + f.bbox[2]) / 2, (f.bbox[1] + f.bbox[3]) / 2]}));
    layers.push(new deck.PolygonLayer({id: 'lintbb', data: F.filter(f => f.bbox && (sel == null || sel === f.id)), getPolygon: f => { const q = f.bbox; return [[q[0], q[1]], [q[2], q[1]], [q[2], q[3]], [q[0], q[3]]]; },
      filled: false, getLineColor: f => [...(f.sev === 'FAIL' ? red : amb), 200], lineWidthUnits: 'pixels', getLineWidth: 1, coordinateSystem: C}));
    layers.push(new deck.TextLayer({id: 'lintmk', data: mk, getPosition: d => d.p, getText: d => '\u26a0 ' + (d.f.id + 1), getSize: 13, getColor: d => [...(d.f.sev === 'FAIL' ? red : amb), 255],
      background: true, getBackgroundColor: light ? [255, 255, 255, 235] : [5, 7, 13, 235], backgroundPadding: [4, 2], fontWeight: 700, coordinateSystem: C, pickable: true, characterSet: 'auto',
      fontFamily: 'ui-sans-serif, system-ui, sans-serif'}));
  }
}

/* ------------------------------------------------------------------ hover / click */
let hoverEv = null, hoverRaf = 0;
function onMove(e){ hoverEv = e; if (!hoverRaf) hoverRaf = requestAnimationFrame(() => { hoverRaf = 0; doHover(hoverEv); }); }
function worldAt(e){
  const vp = deckgl.getViewports()[0], r = e.currentTarget ? e.currentTarget.getBoundingClientRect() : V.root.querySelector('[data-canvas]').getBoundingClientRect();
  return vp.unproject([e.clientX - r.left, e.clientY - r.top]);
}
function pickShape(x, y, tolDbu){
  const G = V.header.grid; const tx = Math.floor((x - G.ox) / G.size), ty = Math.floor((y - G.oy) / G.size);
  let best = null, bestOrder = -1;
  for (let yy = ty - 1; yy <= ty + 1; yy++) for (let xx = tx - 1; xx <= tx + 1; xx++){
    const t = V.tiles.get(xx + '_' + yy); if (!t) continue; const p = t.pick;
    for (let i = t.n - 1; i >= 0; i--){
      if (x < p.x0[i] - tolDbu || x > p.x1[i] + tolDbu || y < p.y0[i] - tolDbu || y > p.y1[i] + tolDbu) continue;
      const L = V.L[p.layer[i]]; if (!L || !L.vis || !(p.kind[i] === 14 ? V.L[V.L.length - 1].vis : V.kindVis[p.kind[i]])) continue;
      const order = p.layer[i] * 1e7 + i;
      // prefer real metal over cell outlines, top layer first
      const o2 = (p.kind[i] >= 13 ? -1e9 : 0) + order;
      if (o2 > bestOrder){ bestOrder = o2; best = {t, i}; }
    }
  }
  return best;
}
const nameCache = {net: new Map(), inst: new Map()};
async function names(kind, ids){
  const need = ids.filter(i => i > 0 || kind === 'inst').filter(i => !nameCache[kind].has(i));
  if (need.length && !V.safe){
    try { const r = await (await api('names?k=' + kind + '&ids=' + need.join(','))).json(); (r.items || []).forEach(it => nameCache[kind].set(it.id, it)); } catch (e) {}
  }
  return ids.map(i => nameCache[kind].get(i));
}
async function doHover(e){
  if (!V.header || !e) return;
  const w = worldAt(e), tip = V.root.querySelector('[data-tip]');
  V.root.querySelector('[data-coord]').textContent = `x ${fmt((w[0] - V.die[0]) / V.dbu, 3)}  y ${fmt((w[1] - V.die[1]) / V.dbu, 3)} \u00b5m`;
  if (V.rulerMode && V.rulerLive){ V.rulerLive.b = [w[0], w[1]]; requestUpdate(); }
  if (V.overlayHover){ return; }
  const ppu = Math.pow(2, V.vs.zoom), tol = 2 / ppu;
  const hit = V.mode === 'geometry' ? pickShape(w[0], w[1], tol) : null;
  if (!hit){ tip.hidden = true; V.hover = null; return; }
  const p = hit.t.pick, i = hit.i, li = p.layer[i], kind = p.kind[i], net = p.net[i];
  V.hover = {net, kind, aux: p.aux[i]};
  const L = V.L[li], W = (p.x1[i] - p.x0[i]) / V.dbu, Hh = (p.y1[i] - p.y0[i]) / V.dbu;
  let head = `${esc(L.name)} · ${esc(KIND_NAME[kind] || 'shape')}`, sub = '';
  if (kind === 9 || kind === 10){ const vt = V.header.vias[p.aux[i]]; sub = vt ? 'via ' + esc(vt.name) : ''; }
  let body = `<div class="m">${fmt(W, 3)} × ${fmt(Hh, 3)} \u00b5m at (${fmt((p.x0[i] - V.die[0]) / V.dbu, 3)}, ${fmt((p.y0[i] - V.die[1]) / V.dbu, 3)})${p.kind[i] < 9 && (p.layer[i] < V.header.layers.length) ? '' : ''}</div>`;
  const show = (nn, inst) => {
    const lines = [];
    if (inst){ const m = V.header.masters[inst.master]; lines.push(`instance <b>${esc(V.safe ? '#' + p.aux[i] : inst.name)}</b>`, `master ${esc(m ? m.name : inst.master)}${p.pin[i] >= 0 && m ? ' · pin ' + esc(m.pins[p.pin[i]].name) : ''}`); }
    if (net > 0) lines.push(`net <b>${esc(V.safe ? '#' + net : (nn ? nn.name : '#' + net))}</b>${nn && nn.sig && nn.sig !== 'SIGNAL' ? ' · ' + esc(nn.sig) : ''} <span class="lv-dim">(click to highlight)</span>`);
    tip.innerHTML = `<div class="n">${head}${sub ? ' · ' + sub : ''}</div>${body}${lines.length ? '<div class="m">' + lines.join('<br>') + '</div>' : ''}`;
    tip.hidden = false; placeTip(tip, e);
  };
  show(null, null);
  const isCell = kind >= 11;
  const [nn] = net > 0 ? await names('net', [net]) : [null];
  const [inst] = isCell ? await names('inst', [p.aux[i]]) : [null];
  if (V.hover && V.hover.net === net && V.hover.aux === p.aux[i]) show(nn, inst ? Object.assign({master: inst.master}, inst) : null);
}
function placeTip(tip, e){
  const r = V.root.getBoundingClientRect(); let X = e.clientX - r.left + 14, Y = e.clientY - r.top + 14;
  const tw = tip.offsetWidth, th = tip.offsetHeight; if (X + tw > r.width - 6) X = e.clientX - r.left - tw - 14; if (Y + th > r.height - 6) Y = e.clientY - r.top - th - 14;
  tip.style.left = Math.max(4, X) + 'px'; tip.style.top = Math.max(4, Y) + 'px';
}
function onDeckHover(info){
  V.overlayHover = !!(info && info.object);
  const tip = V.root && V.root.querySelector('[data-tip]'); if (!tip) return;
  if (!info || !info.object) return;
  const o = info.object, id = info.layer && info.layer.id;
  let html = '';
  if (id === 'lints' || id === 'lintmk'){ const f = o.f; html = `<div class="n">${esc(f.sev)} · ${esc(f.title)}</div><div class="m">${esc(f.reason).slice(0, 300)}</div><div class="m lv-dim">click for the reason and fix</div>`; }
  else if (id === 'clkl'){ html = `<div class="n">${esc(V.safe ? 'flop' : o.name)}</div><div class="m">clock arrival TT ${fmt(o.t, 1)} ps</div>`; }
  else if (id === 'clkb'){ html = `<div class="n">${esc(V.safe ? o.m : o.name)}</div><div class="m">${esc(o.m)} · level ${o.lvl} · arrival TT ${fmt(o.t, 1)} ps</div>`; }
  else if (id === 'paths'){ html = `<div class="n">path ${o.i + 1}: slack ${fmt(o.p.slack, 2)} ps</div><div class="m">${esc(V.safe ? '' : o.p.start + ' → ' + o.p.end)}</div><div class="m lv-dim">click to select</div>`; }
  else if (id === 'pathpins'){ html = `<div class="n">${esc(V.safe ? o[3] : o[0])}</div><div class="m">${esc(o[3])} · +${fmt(o[2], 2)} ps · arrival ${fmt(o[1], 2)} ps</div>`; }
  else if (id === 'macros'){ html = `<div class="n">${esc(V.safe ? 'macro' : o.name)}</div><div class="m">${esc(V.safe ? '' : o.master)} · ${fmt((o.bbox[2] - o.bbox[0]) / V.dbu, 2)} × ${fmt((o.bbox[3] - o.bbox[1]) / V.dbu, 2)} \u00b5m · ${esc(o.orient)}</div>`; V.overlayHover = false; return; }
  if (html){ tip.innerHTML = html; tip.hidden = false; placeTip(tip, info.srcEvent || {clientX: info.x + V.root.getBoundingClientRect().left, clientY: info.y + V.root.getBoundingClientRect().top}); }
}
function onClick(info, ev){
  const w = info.coordinate;
  if (V.rulerMode){
    if (!V.rulerLive) V.rulerLive = {a: [w[0], w[1]], b: [w[0], w[1]]};
    else { V.rulerLive.b = [w[0], w[1]]; V.rulers.push(V.rulerLive); V.rulerLive = null; }
    requestUpdate(); return;
  }
  const id = info.layer && info.layer.id, o = info.object;
  if (o && (id === 'lints' || id === 'lintmk')){ selectFinding(o.f.id, false); return; }
  if (o && id === 'paths'){ V.psel = o.i; renderSide(); requestUpdate(); return; }
  if (V.hover && V.hover.net > 0){ highlight(V.hover.net); return; }
  if (!o) { if (V.hl){ highlight(0); } }
}
function highlight(net){
  V.hl = net || 0; V.uni = Object.assign({}, V.uni, {uHl: V.hl});
  if (V.hl) netInfo(V.hl); else V.netSel = null;
  renderSide(); requestUpdate(); saveUrl();
}
async function netInfo(net){
  const [nn] = await names('net', [net]);
  V.netSel = nn || {id: net, name: '#' + net};
  renderSide();
}
function zoomTo(bb, pad){
  if (!bb) return;
  const r = V.root.querySelector('[data-canvas]').getBoundingClientRect();
  const w = Math.max(200, bb[2] - bb[0]), h = Math.max(200, bb[3] - bb[1]);
  const z = Math.log2(Math.min(r.width / w, r.height / h) * (pad || 0.7));
  const vs = Object.assign({}, V.vs, {target: [(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, 0], zoom: Math.min(4, z), transitionDuration: 400});
  V.vs = vs; deckgl.setProps({initialViewState: vs}); requestUpdate(); saveUrl();
}
function fit(){ zoomTo([V.die[0], V.die[1], V.die[2], V.die[3]], 0.92); }

/* ------------------------------------------------------------------ toolbar, search, keys */
function bindTop(){
  const R = V.root;
  R.querySelectorAll('[data-tool]').forEach(b => b.onclick = () => {
    const t = b.dataset.tool;
    if (t === 'fit') fit();
    if (t === 'ruler'){ V.rulerMode = !V.rulerMode; V.rulerLive = null; b.setAttribute('aria-pressed', V.rulerMode); requestUpdate(); }
    if (t === 'clear'){ V.rulers = []; V.rulerLive = null; V.flash = null; highlight(0); }
  });
  const q = R.querySelector('[data-q]'), res = R.querySelector('[data-res]'); let tm = 0;
  q.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(async () => {
    const s = q.value.trim(); if (s.length < 2){ res.hidden = true; return; }
    let out = [];
    try { out = (await (await api('search?q=' + encodeURIComponent(s) + '&k=all')).json()).results || []; } catch (e) {}
    res.innerHTML = out.length ? out.map((o, k) => `<button type="button" data-k="${k}"><span class="lv-tag">${o.k}</span> ${esc(o.name)}${o.sig && o.sig !== 'SIGNAL' ? ' <small>' + esc(o.sig) + '</small>' : ''}</button>`).join('') : '<div class="lv-dim" style="padding:6px 8px">no match</div>';
    res.hidden = false;
    res.querySelectorAll('[data-k]').forEach(b => b.onclick = () => { const o = out[+b.dataset.k]; res.hidden = true;
      if (o.k === 'net'){ nameCache.net.set(o.id, o); highlight(o.id); if (o.bbox && o.bbox[2] > o.bbox[0]) zoomTo(o.bbox); }
      else if (o.k === 'inst'){ V.flash = o.bbox; zoomTo(o.bbox, 0.2); }
      else if (o.k === 'pin'){ /* ports share their net name */ }
    });
  }, 220); });
  q.addEventListener('keydown', e => { if (e.key === 'Escape'){ res.hidden = true; q.blur(); } });
}
function onKey(e){
  if (e.target && e.target.tagName === 'INPUT') return;
  if (e.key === 'f' || e.key === 'F') fit();
  if (e.key === 'r' || e.key === 'R'){ V.rulerMode = !V.rulerMode; V.rulerLive = null; const b = V.root.querySelector('[data-tool="ruler"]'); if (b) b.setAttribute('aria-pressed', V.rulerMode); requestUpdate(); }
  if (e.key === 'Escape'){ V.rulerMode = false; V.rulerLive = null; V.rulers = []; V.flash = null; highlight(0); }
}

/* ------------------------------------------------------------------ minimap, scale, info */
function bindMini(){
  const cv = V.root.querySelector('[data-mini]'); let down = false;
  const go = e => { const r = cv.getBoundingClientRect(), m = V.miniGeom; if (!m) return; const x = m.x0 + (e.clientX - r.left - m.ox) / m.s, y = m.y0 + (m.h - (e.clientY - r.top - m.oy)) / m.s;
    const vs = Object.assign({}, V.vs, {target: [x, y, 0], transitionDuration: 0}); V.vs = vs; deckgl.setProps({initialViewState: vs}); requestUpdate(); saveUrl(); };
  cv.addEventListener('pointerdown', e => { down = true; cv.setPointerCapture(e.pointerId); go(e); });
  cv.addEventListener('pointermove', e => { if (down) go(e); });
  cv.addEventListener('pointerup', () => { down = false; });
}
function drawMini(){
  const cv = V.root.querySelector('[data-mini]'); if (!cv) return;
  const dpr = Math.min(2, window.devicePixelRatio || 1), CW = 180, CH = 120;
  if (cv.width !== CW * dpr){ cv.width = CW * dpr; cv.height = CH * dpr; }
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0);
  const W = V.die[2] - V.die[0], Hh = V.die[3] - V.die[1], s = Math.min((CW - 8) / W, (CH - 8) / Hh), ox = (CW - W * s) / 2, oy = (CH - Hh * s) / 2;
  V.miniGeom = {s, ox, oy, x0: V.die[0], y0: V.die[1], h: Hh * s};
  if (V.miniDirty || !V.miniBg){
    V.miniDirty = false; const bg = document.createElement('canvas'); bg.width = CW * dpr; bg.height = CH * dpr; const b = bg.getContext('2d'); b.setTransform(dpr, 0, 0, dpr, 0, 0);
    const L0 = V.header.raster.levels.find(q => q.level === 0);
    if (L0) for (const n of L0.nodes){ const r = V.rasters.get('0/' + n[0] + '_' + n[1]); if (!r) continue;
      const t = document.createElement('canvas'); t.width = r.im.width; t.height = r.im.height; t.getContext('2d').putImageData(r.im, 0, 0);
      const node = L0.node_nm; b.save(); b.translate(ox + n[0] * node * s, oy + Hh * s - (n[1] + 1) * node * s); b.scale(node * s / r.im.width, node * s / r.im.height);
      b.drawImage(t, 0, 0); b.restore(); }
    V.miniBg = bg;
  }
  c.clearRect(0, 0, CW, CH); c.fillStyle = cssv('--canvas'); c.fillRect(0, 0, CW, CH);
  c.drawImage(V.miniBg, 0, 0, CW, CH);
  c.strokeStyle = cssv('--faint'); c.strokeRect(ox, oy, W * s, Hh * s);
  const b = viewBounds(); if (!b) return;
  c.strokeStyle = cssv('--accent'); c.lineWidth = 1.5;
  const x0 = ox + (b.x0 - V.die[0]) * s, x1 = ox + (b.x1 - V.die[0]) * s, y0 = oy + Hh * s - (b.y1 - V.die[1]) * s, y1 = oy + Hh * s - (b.y0 - V.die[1]) * s;
  c.strokeRect(Math.max(-2, x0), Math.max(-2, y0), Math.min(CW + 4, x1) - Math.max(-2, x0), Math.min(CH + 4, y1) - Math.max(-2, y0));
}
function drawScale(ppu){
  const el = V.root.querySelector('[data-scale]'); if (!el) return;
  const um = 100 / (ppu * V.dbu), m = Math.pow(10, Math.floor(Math.log10(um))), e = um / m, step = (e >= 5 ? 5 : e >= 2 ? 2 : 1) * m;
  el.querySelector('i').style.width = (step * ppu * V.dbu) + 'px';
  el.querySelector('span').textContent = step >= 1 ? fmt(step, 0) + ' \u00b5m' : step >= 0.01 ? fmt(step * 1000, 0) + ' nm' : fmt(step * 1000, 1) + ' nm';
}
const PERF = /[?&#]perf=1/.test(location.href);
setInterval(() => { if (PERF && V.open && V.header) renderInfo(V.lastCost || 0); }, 500);
function fps(){ const f = V.frames || []; if (f.length < 2) return null; const dt = []; for (let i = 1; i < f.length; i++) dt.push(f[i] - f[i - 1]); dt.sort((a, b) => a - b);
  return {fps: 1000 * (f.length - 1) / (f[f.length - 1] - f[0]), p95: dt[Math.floor(dt.length * 0.95)]}; }
function renderInfo(cost, nvis){
  const el = V.root.querySelector('[data-info]'); if (!el) return;
  V.lastCost = cost;
  const loading = [...V.pending.keys()].length;
  if (PERF){ const p = fps(), inst = [...V.tiles.values()].reduce((s, t) => s + (t.n || 0), 0);
    el.innerHTML = `${V.mode} · ${p ? fmt(p.fps, 0) + ' fps (p95 ' + fmt(p.p95, 1) + ' ms)' : 'idle'} · ${fmt(inst, 0)} instances loaded · GPU ${fmt(V.gpuBytes / 1e6, 0)} MB · first paint ${fmt(V.firstPaint, 0)} ms · first geometry ${fmt(V.firstGeo, 0)} ms${loading ? ' · loading ' + loading : ''}`;
    return; }
  el.innerHTML = `${V.mode === 'geometry' ? '<b>exact geometry</b>' : '<b>density raster</b> L' + V.rlevel} · ${fmt(cost, 0)} shapes in view${loading ? ` · loading ${loading}` : ''} · GPU ${fmt(V.gpuBytes / 1e6, 0)} MB`;
}

/* ------------------------------------------------------------------ side panel */
function presets(name){
  const nl = V.header.layers.length;
  const setAll = (fn) => V.L.forEach(l => { l.vis = fn(l); });
  KINDS.forEach(k => V.kindVis[k[0]] = !!k[2]);
  if (name === 'all') setAll(l => l.type !== 'PHYS');
  if (name === 'signals'){ setAll(l => l.type !== 'PHYS'); [1, 2, 3, 10, 5, 6, 12].forEach(k => V.kindVis[k] = false); }
  if (name === 'power'){ setAll(l => l.type !== 'PHYS' && l.type !== 'CELLS'); KINDS.forEach(k => V.kindVis[k[0]] = [1, 2, 3, 10].includes(k[0])); }
  if (name === 'm6'){ setAll(l => { const m = /^[MV](\d+)$/.exec(l.name); return l.name === 'Pad' || (m && (l.name[0] === 'M' ? +m[1] >= 6 : +m[1] >= 5)); }); V.kindVis[4] = true; V.ov.macros = true; }
  V.phys = V.L[nl + 1].vis;
  updateUniforms(); refreshTiles(); renderSide(); requestUpdate(); saveUrl();
}
function renderSide(){
  if (!V.side || !V.header) return;
  const H = V.header, nl = H.layers.length;
  const sw = l => `<i class="lv-sw" style="--c:${l.color}" data-pat="${l.pat}"></i>`;
  const layersHtml = V.L.map(l => `<div class="lv-row ${l.vis ? '' : 'off'}" data-l="${l.i}">
      <label class="lv-vis"><input type="checkbox" ${l.vis ? 'checked' : ''} data-lv="${l.i}" aria-label="Show ${esc(l.name)}">${sw(l)}<span class="lv-ln">${esc(l.name)}</span></label>
      <small>${l.type === 'CUT' ? 'via' : l.type === 'ROUTING' ? (l.dir === 'HORIZONTAL' ? 'H' : 'V') : ''}</small>
      <input type="range" min="0" max="100" value="${Math.round(l.op * 100)}" data-lo="${l.i}" aria-label="${esc(l.name)} opacity">
      <button class="lv-solo" data-solo="${l.i}" title="Show only ${esc(l.name)}">solo</button></div>`).join('');
  const kinds = KINDS.filter(k => k[0] < 14).map(k => `<label class="lv-chk"><input type="checkbox" ${V.kindVis[k[0]] ? 'checked' : ''} data-kind="${k[0]}"> ${esc(k[1])}</label>`).join('');
  const lint = V.lint || {}, F = lint.findings || [];
  const fsel = V.lintSel != null ? F[V.lintSel] : null;
  const lintHtml = lint.error ? `<p class="note">Contract lint could not run: ${esc(lint.error)}</p>` : !F.length ? `<p class="note ok">No findings: this element passes the hierarchy-contract checks on its routed abstract${(lint.summary && lint.summary.macros && lint.summary.macros.length) ? ' and every placed macro is on grid' : ''}.</p>` :
    `<div class="lv-list">${F.map(f => `<button type="button" class="lv-f ${V.lintSel === f.id ? 'on' : ''}" data-f="${f.id}"><span class="lv-sev ${f.sev === 'FAIL' ? 'ng' : 'wn'}">${f.sev}</span> <b>${f.id + 1}.</b> ${esc(f.title)}<small>${f.n_shapes} shapes</small></button>`).join('')}</div>` +
    (fsel ? `<div class="lv-fd"><h4>${esc(fsel.title)}</h4><p><b>Why.</b> ${esc(fsel.reason)}</p><p><b>Fix.</b> ${esc(fsel.fix)}</p><p class="lv-dim">check (${esc(fsel.check)}) · ${esc(fsel.scope)}${fsel.inst ? ' · ' + esc(fsel.inst) : ''} · ${fsel.n_shapes} shapes${fsel.n_shapes > fsel.shapes.length ? ' (first ' + fsel.shapes.length + ' drawn)' : ''}</p></div>` : '');
  const cong = V.cong ? `<div class="ctl"><label>layer <select data-cong><option value="max" ${V.congLayer === 'max' ? 'selected' : ''}>max over layers</option>${V.cong.layers.map(li => `<option value="${li}" ${String(V.congLayer) === String(li) ? 'selected' : ''}>${esc(H.layers[li].name)}</option>`).join('')}</select></label></div>
    <div class="lv-ramp" style="background:linear-gradient(90deg,${HEAT.join(',')})"></div><div class="rampl"><span>0%</span><span>55%</span><span>&ge;110% of track capacity</span></div>
    <div class="tw"><table class="t"><thead><tr><th>layer</th><th class="n">p50</th><th class="n">p99</th><th class="n">max</th><th class="n">bins &gt;100%</th></tr></thead><tbody>${H.congestion.layers.map(c => `<tr><td>${esc(c.name)}</td><td class="n">${fmt(c.p50, 0)}%</td><td class="n">${fmt(c.p99, 0)}%</td><td class="n">${fmt(c.max, 0)}%</td><td class="n">${fmt(c.over100, 0)}</td></tr>`).join('')}</tbody></table></div>
    <p class="note">${esc(H.congestion.basis)}; ${fmt(H.congestion.bin_nm / 1000, 2)} \u00b5m bins.</p>` : '<p class="note">no congestion grid in this pack</p>';
  const P = V.d ? (((V.pcorner || 'setup') === 'hold' ? V.d.hold_paths : V.d.setup_paths) || []).slice(0, 15) : [];
  const paths = !P.length ? '<p class="note">No timing paths were exported for this element (timing not re-run).</p>' :
    `<div class="ctl"><select data-pc><option value="setup" ${(V.pcorner || 'setup') === 'setup' ? 'selected' : ''}>setup (TT)</option><option value="hold" ${V.pcorner === 'hold' ? 'selected' : ''}>hold (FF)</option></select></div>
     <div class="tw"><table class="t"><thead><tr><th>#</th><th class="n">slack ps</th><th>endpoint</th></tr></thead><tbody>${P.map((p, k) => `<tr class="cl ${k === (V.psel || 0) ? 'on' : ''}" data-p="${k}"><td class="n">${k + 1}</td><td class="n ${p.slack >= 0 ? 'ok' : 'ng'}">${fmt(p.slack, 2)}</td><td class="m">${esc(V.safe ? 'endpoint' : String(p.end).replace(/^.*\.(?=[^.]+$)/, '…'))}</td></tr>`).join('')}</tbody></table></div>`;
  const clk = V.clk ? `<div class="lv-ramp" style="background:linear-gradient(90deg,${ARR.join(',')})"></div><div class="rampl"><span>${fmt(V.clk.lo, 0)} ps</span><span>clock arrival (TT, p1..p99)</span><span>${fmt(V.clk.hi, 0)} ps</span></div>
    <p class="note">${fmt(V.clk.bufs.length, 0)} tree cells, ${fmt(V.clk.leaves.length, 0)} sinks; click a clock-tree wire on the layout to light its routed net.</p>` : '<p class="note">no clock tree exported</p>';
  const net = V.netSel ? `<div class="lv-net"><b>${esc(V.safe ? 'net #' + V.netSel.id : V.netSel.name)}</b>${V.netSel.sig && V.netSel.sig !== 'SIGNAL' ? ' · ' + esc(V.netSel.sig) : ''}
      ${V.netSel.bbox ? `<br><span class="lv-dim">extent ${fmt((V.netSel.bbox[2] - V.netSel.bbox[0]) / V.dbu, 2)} × ${fmt((V.netSel.bbox[3] - V.netSel.bbox[1]) / V.dbu, 2)} \u00b5m</span> <button class="rl" data-netzoom>zoom to net</button>` : ''} <button class="rl" data-netclear>clear</button></div>` : '';
  const T = H.truth ? H.truth.reduce((s, t) => s + t.n, 0) : null;
  const ovt = (k, t) => `<label class="lv-chk lv-ovt"><input type="checkbox" data-ov="${k}" ${V.ov[k] ? 'checked' : ''}> ${t}</label>`;
  const navHtml = `
    <div class="sec"><h3>Layers <span class="u">${fmt(H.counts.rects + H.counts.vias, 0)} shapes + ${fmt(H.counts.insts, 0)} instances</span></h3>
      <div class="lv-pre"><button class="btn" data-pre="all">All</button><button class="btn" data-pre="signals">Signals only</button><button class="btn" data-pre="power">Power grid</button><button class="btn" data-pre="m6">M6+ die contract</button></div>
      <div class="lv-layers">${layersHtml}</div>
      <details class="lv-kinds"><summary>Shape kinds</summary><div class="lv-kgrid">${kinds}</div></details>
      <div class="ctl" style="margin-top:8px"><label>palette <select data-pal><option value="classic" ${V.palette === 'classic' ? 'selected' : ''}>Classic layout</option><option value="cvd" ${V.palette === 'cvd' ? 'selected' : ''}>Colour-blind safe</option></select></label></div>
      </div>
    <div class="sec"><h3>Overlays</h3>${ovt('lint', 'contract findings' + (F.length ? ` <small class="lv-dim">(${F.length})</small>` : ''))}${ovt('paths', 'worst timing paths')}${ovt('clock', 'clock tree, arrival-coloured')}${ovt('cong', 'congestion heatmap')}${ovt('macros', 'macro outlines')}${ovt('mods', 'module outlines' + (V.mods ? ` (${V.mods.length} blocks)` : ' (placement data needed)'))}</div>`;
  const metaHtml = `${net ? `<div class="sec">${net}</div>` : ''}
    <div class="sec"><h3>Contract findings <span class="u">child_lint on this routed DB</span></h3>${lintHtml}</div>
    <div class="sec"><h3>Timing paths</h3>${paths}</div>
    <div class="sec"><h3>Clock tree</h3>${clk}</div>
    <div class="sec"><h3>Congestion</h3>${cong}</div>
    ${V.manifest ? (() => { const c = V.manifest.closure || {}, m = c.metrics || {};
      return `<div class="sec"><h3>Closure <span class="u">static export</span></h3><dl class="kv">
      <dt>job</dt><dd>${esc(c.job || V.manifest.job)}${c.status ? ' · ' + esc(c.status) : ''}</dd>
      ${c.commit ? `<dt>commit</dt><dd>${esc(String(c.commit).slice(0, 12))}</dd>` : ''}
      ${m.ss_ps != null ? `<dt>setup / hold</dt><dd>${esc((m.setup_corner || 'ss').toUpperCase())} ${fmt(+m.ss_ps, 2)} ps · FF ${fmt(+m.ff_ps, 2)} ps · DRC ${esc(m.drc != null ? m.drc : '\u2014')}</dd>` : ''}
      ${c.closed_at ? `<dt>closed</dt><dd>${esc(c.closed_at)}</dd>` : ''}
      ${c.record ? `<dt>record</dt><dd>${esc(c.record)}</dd>` : ''}
      <dt>export</dt><dd>${esc(V.manifest.made)} · ${fmt(V.manifest.bytes / 1e6, 1)} MB · round trip ${esc((V.manifest.verify || {}).verdict || '?')} (${fmt((V.manifest.verify || {}).shapes, 0)} shapes)</dd>
      </dl>${V.index && V.index.history.length > 1 ? `<div class="ctl" style="margin-top:6px"><label>history <select data-hist>${V.index.history.map((j, i) => `<option value="${esc(j)}" ${j === V.manifest.job ? 'selected' : ''}>${esc(j)}${i === 0 ? ' (latest)' : ''}</option>`).join('')}</select></label></div>` : ''}</div>`; })() : ''}
    <div class="sec"><h3>Data</h3><dl class="kv">
      <dt>source</dt><dd>${esc(V.safe ? 'final routed DB' : (H.db || ''))}</dd>
      <dt>die</dt><dd>${fmt((H.die[2] - H.die[0]) / H.dbu, 3)} × ${fmt((H.die[3] - H.die[1]) / H.dbu, 3)} \u00b5m · ${H.dbu} DBU/\u00b5m</dd>
      <dt>tiles</dt><dd>${H.grid.nx} × ${H.grid.ny} of ${fmt(H.grid.size / H.dbu, 1)} \u00b5m, ${H.grid.tiles ? H.grid.tiles.length : 0} non-empty</dd>
      <dt>DB truth</dt><dd>${T != null ? fmt(T, 0) + ' shapes; round-trip: tools/layout_viewer/lv_verify.js' : 'not recorded'}</dd>
      <dt>cut</dt><dd>${esc(H.made || '')}</dd>
      ${V.firstPaint ? `<dt>first paint</dt><dd>${fmt(V.firstPaint, 0)} ms${V.firstGeo ? ` · first geometry ${fmt(V.firstGeo, 0)} ms` : ''}</dd>` : ''}</dl></div>`;
  if (V.nav){ V.nav.innerHTML = navHtml; V.side.innerHTML = metaHtml; } else V.side.innerHTML = navHtml + metaHtml;
  bindSide();
}
function bindSide(){
  const both = [V.side, V.nav].filter(Boolean);
  const S = {querySelectorAll: q => both.flatMap(c => [...c.querySelectorAll(q)]), querySelector: q => { for (const c of both){ const e = c.querySelector(q); if (e) return e; } return null; }};
  const nl = V.header.layers.length;
  S.querySelectorAll('[data-lv]').forEach(c => c.onchange = () => { const l = V.L[+c.dataset.lv]; l.vis = c.checked; if (l.i === nl + 1){ V.phys = l.vis; V.tiles.clear(); V.gpuBytes = 0; }
    c.closest('.lv-row').classList.toggle('off', !l.vis); updateUniforms(); refreshTiles(); requestUpdate(); saveUrl(); });
  S.querySelectorAll('[data-lo]').forEach(c => c.oninput = () => { V.L[+c.dataset.lo].op = c.value / 100; updateUniforms(); requestUpdate(); });
  S.querySelectorAll('[data-solo]').forEach(b => b.onclick = () => { const i = +b.dataset.solo; const only = V.L.every(l => l.i === i ? l.vis : !l.vis);
    V.L.forEach(l => l.vis = only ? l.type !== 'PHYS' : l.i === i); V.phys = V.L[nl + 1].vis; updateUniforms(); refreshTiles(); renderSide(); requestUpdate(); saveUrl(); });
  S.querySelectorAll('[data-kind]').forEach(c => c.onchange = () => { V.kindVis[+c.dataset.kind] = c.checked; updateUniforms(); refreshTiles(); requestUpdate(); saveUrl(); });
  S.querySelectorAll('[data-pre]').forEach(b => b.onclick = () => presets(b.dataset.pre));
  const pal = S.querySelector('[data-pal]'); if (pal) pal.onchange = () => { V.palette = pal.value; lsSet('pal', pal.value); applyPalette(); renderSide(); V.miniDirty = true; requestUpdate(); };
  S.querySelectorAll('[data-ov]').forEach(c => c.onchange = () => { V.ov[c.dataset.ov] = c.checked; requestUpdate(); saveUrl(); });   // left column only
  S.querySelectorAll('[data-f]').forEach(b => b.onclick = () => selectFinding(+b.dataset.f, true));
  const cg = S.querySelector('[data-cong]'); if (cg) cg.onchange = () => { V.congLayer = cg.value; V.ov.cong = true; renderSide(); requestUpdate(); };
  const pc = S.querySelector('[data-pc]'); if (pc) pc.onchange = () => { V.pcorner = pc.value; V.psel = 0; V.ov.paths = true; renderSide(); requestUpdate(); };
  S.querySelectorAll('[data-p]').forEach(r => r.onclick = () => { V.psel = +r.dataset.p; V.ov.paths = true; const p = ((V.pcorner === 'hold' ? V.d.hold_paths : V.d.setup_paths) || [])[V.psel];
    if (p){ const pts = p.points.filter(q => q[5] != null); if (pts.length){ const xs = pts.map(q => um2dbu(q[5])), ys = pts.map(q => um2dbu(q[6])); zoomTo([Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], 0.8); } }
    renderSide(); requestUpdate(); });
  const hs = S.querySelector('[data-hist]'); if (hs) hs.onchange = () => { const o = urlState(); o.j = hs.value; o.tab = 'geo';
    try { history.replaceState(null, '', location.pathname + location.search + '#' + Object.entries(o).map(([k, v]) => k + '=' + encodeURIComponent(v)).join('&')); } catch (e) {}
    V.loadedFor = null; open(V); };
  const nz = S.querySelector('[data-netzoom]'); if (nz) nz.onclick = () => zoomTo(V.netSel.bbox);
  const nc = S.querySelector('[data-netclear]'); if (nc) nc.onclick = () => highlight(0);
}
function selectFinding(id, zoom){
  V.lintSel = V.lintSel === id && !zoom ? null : id; V.ov.lint = true;
  const f = V.lint.findings[id];
  if (zoom && f && f.bbox) zoomTo(f.bbox, 0.8);
  renderSide(); requestUpdate(); saveUrl();
  const el = V.side.querySelector('.lv-fd'); if (el && !zoom) el.scrollIntoView({block: 'nearest'});
}

/* ------------------------------------------------------------------ public */
window.LayoutViewer = {
  open, close: () => { V.open = false; if (V.root) V.root.hidden = true; if (V.side) V.side.hidden = true; if (V.nav) V.nav.hidden = true; },
  theme: () => { if (V.header){ applyPalette(); renderSide(); V.miniDirty = true; V.congIm = null; requestUpdate(); } },
  state: () => V,
  _update: () => update(),
  _restyle: () => { updateUniforms(); refreshTiles(); requestUpdate(); },
};
})();

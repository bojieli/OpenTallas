// Layout engine: one deck.gl renderer for routed geometry at die scope (many placed packs) and element scope (one pack).
//
// A scene is a list of placed items {key, pack, xf, level, name, state} over a set of packs.  A pack is one closure of
// one design in the layout store (tools/layout_viewer/lv_tile.py): 25.6 um vector tiles per layer, a density raster
// pyramid, name tables.  Tiles are fetched and decoded by the kept worker (/explorer/element/lv_worker.js, multi-pack).
// Coordinates: tile geometry stays PACK-LOCAL integer DBU in float32 (exact below 16.7 mm).  The camera is handed to the
// shader in the same local DBU frame per item (uCam), so (p - uCam) is exact and a 32 mm die costs no precision
// (EXPLORER-P1's method, here with the subtraction done in DBU).  World unit of the view: um, y up.
// LOD: plan rectangles + level-0 density rasters far out, finer raster levels closer, exact tiles inside the shape budget.
import { api } from '../core/api.js';
import { h, clear, cssv, hexRgb, fmt, raf } from '../core/dom.js';

const DECK_SRC = '/engine/vendor/deck.gl-8.9.36.min.js';
const WORKER_SRC = '/explorer/element/lv_worker.js';
// Routing-layer palettes: data of the engine, kept from the verified viewer (tools/fleet_viz/explorer/element/layout.js).
// stipple ids: 0 solid, 1 '/', 2 '\', 3 cross, 4 dots, 5 horizontal, 6 vertical, 7 dense '/', 8 sparse '\', 9 grid, 10 hollow
export const PAL = {
  classic: { M1: ['#4f8dff', 1], M2: ['#ff5252', 2], M3: ['#3ddc84', 1], M4: ['#ffb300', 2], M5: ['#29d3f0', 7], M6: ['#e066ff', 8], M7: ['#ff8f3d', 3], M8: ['#ff7cc8', 9], M9: ['#a5e05a', 5], Pad: ['#b8b8b8', 6],
    V0: ['#9db6ff', 0], V1: ['#ffc0c0', 0], V2: ['#b6f5cf', 0], V3: ['#ffe08a', 0], V4: ['#b0f1fb', 0], V5: ['#f1c2ff', 0], V6: ['#ffd0b0', 0], V7: ['#ffd1ea', 0], V8: ['#d8f5b8', 0], V9: ['#e6e6e6', 0] },
  cvd: { M1: ['#0072b2', 1], M2: ['#d55e00', 2], M3: ['#009e73', 5], M4: ['#e69f00', 6], M5: ['#56b4e9', 3], M6: ['#cc79a7', 7], M7: ['#f0e442', 8], M8: ['#882255', 9], M9: ['#44aa99', 4], Pad: ['#999999', 1],
    V0: ['#7fb8d8', 0], V1: ['#eaae7f', 0], V2: ['#7fcfb9', 0], V3: ['#f2cf7f', 0], V4: ['#aad9f4', 0], V5: ['#e5bcd3', 0], V6: ['#f7f1a0', 0], V7: ['#c390aa', 0], V8: ['#a1d4cc', 0], V9: ['#cccccc', 0] } };
export const KINDS = [[0, 'Signal wires', 1], [1, 'Power stripes', 1], [2, 'Follow-pin rails', 1], [3, 'Other special wires', 1], [4, 'Block pins', 1], [5, 'Routing obstructions', 1], [6, 'Metal fill', 1], [7, 'Macro pins', 1],
  [8, 'Macro OBS', 1], [9, 'Signal vias', 1], [10, 'Power vias', 1], [11, 'Cell pins', 1], [12, 'Cell OBS', 1], [13, 'Cell outlines', 1], [14, 'Filler / tap outlines', 0], [15, 'Via arrays (merged)', 1], [16, 'Via array cuts', 1]];
const KIND_NAME = Object.fromEntries(KINDS.map((k) => [k[0], k[1].replace(/s$/, '')]));
export const PRESETS = [['all', 'All'], ['signals', 'Signals'], ['power', 'Power'], ['upper', 'M6 and up'], ['cells', 'Cells only']];

const VS = `#define SHADER_NAME otx-rect-vs
attribute vec3 positions;
attribute vec4 instanceRects;
attribute vec3 instanceMeta;
uniform vec4 uColor[48];
uniform float uAlpha[48];
uniform float uPat[48];
uniform float uKind[20];
uniform float uHl;
uniform float uPx;
uniform vec2 uCam;
uniform vec2 uK;
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
  gl_Position = vec4((p - uCam) * uK, 0.0, 1.0);
}`;
const FS = `#define SHADER_NAME otx-rect-fs
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
  if (vPat > 9.5) alpha = (vSz.x < 6.0 || vSz.y < 6.0) ? 0.0 : (edge ? vColor.a : 0.0);
  else if (edge || vSz.x < 4.0 || vSz.y < 4.0) alpha = vColor.a;
  else alpha = vColor.a * (uFill + (1.0 - uFill) * 0.9 * stip(vPat, gl_FragCoord.xy));
  if (alpha < 0.004) discard;
  gl_FragColor = vec4(vColor.rgb, alpha);
}`;

let deckLoading = null;
export function loadDeck() {
  if (window.deck) return Promise.resolve();
  if (!deckLoading) deckLoading = new Promise((res, rej) => { const s = document.createElement('script'); s.src = DECK_SRC; s.onload = res; s.onerror = () => rej(new Error('deck.gl did not load')); document.head.append(s); });
  return deckLoading;
}
let RectLayer = null;
function rectLayer() {
  if (RectLayer) return RectLayer;
  const { Layer } = window.deck, { Model, Geometry } = window.luma;
  class OtxRectLayer extends Layer {
    getShaders() { return super.getShaders({ vs: VS, fs: FS, modules: [] }); }
    initializeState() { this.getAttributeManager().addInstanced({ instanceRects: { size: 4, noAlloc: true }, instanceMeta: { size: 3, noAlloc: true } }); this.setState({ model: this._model() }); }
    _model() { return new Model(this.context.gl, Object.assign({}, this.getShaders(), { id: this.props.id, isInstanced: true,
      geometry: new Geometry({ drawMode: 6, vertexCount: 4, attributes: { positions: { size: 3, value: new Float32Array([0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0]) } } }) })); }
    draw({ uniforms }) { this.state.model.setUniforms(uniforms).setUniforms(this.props.lv).draw(); }
  }
  OtxRectLayer.layerName = 'OtxRectLayer'; OtxRectLayer.defaultProps = { lv: { type: 'object', value: {} } };
  return (RectLayer = OtxRectLayer);
}

export const SGN = { R0: [1, 1], MX: [1, -1], MY: [-1, 1], R180: [-1, -1] };
/** plan bbox (DBU) + orient -> transform {sx, sy, ox, oy}: world um = o + s * local DBU / 1000 */
export const xfOf = (orient, X, Y, W, H) => { const [sx, sy] = SGN[orient]; return { sx, sy, ox: (X + (sx < 0 ? W : 0)) / 1000, oy: (Y + (sy < 0 ? H : 0)) / 1000 }; };
/** a macro (origin, orient in the parent's frame, DBU) under the parent's transform */
export const xfCompose = (parent, origin, orient) => { const [sx, sy] = SGN[orient]; return { sx: parent.sx * sx, sy: parent.sy * sy, ox: parent.ox + parent.sx * origin[0] / 1000, oy: parent.oy + parent.sy * origin[1] / 1000 }; };
/** a child placed by its bbox (um, in the parent's frame) + orient, under the parent's transform */
export const xfChild = (parent, orient, x, y, w, hh) => { const [sx, sy] = SGN[orient]; return xfCompose(parent, [(x + (sx < 0 ? w : 0)) * 1000, (y + (sy < 0 ? hh : 0)) * 1000], orient); };
export const XF0 = { sx: 1, sy: 1, ox: 0, oy: 0 };
export const xfBox = (xf, x0, y0, x1, y1) => { const ax = xf.ox + xf.sx * x0 / 1000, bx = xf.ox + xf.sx * x1 / 1000, ay = xf.oy + xf.sy * y0 / 1000, by = xf.oy + xf.sy * y1 / 1000; return [Math.min(ax, bx), Math.min(ay, by), Math.max(ax, bx), Math.max(ay, by)]; };
export const xfPoint = (xf, x, y) => [xf.ox + xf.sx * x / 1000, xf.oy + xf.sy * y / 1000];
const meets = (a, b) => a[0] < b.x1 && a[2] > b.x0 && a[1] < b.y1 && a[3] > b.y0;
const rectPoly = (a) => [[a[0], a[1]], [a[2], a[1]], [a[2], a[3]], [a[0], a[3]]];

/** the newest (or a named) closure of a node in the store -> pack info for the engine */
export async function packFromStore(node, job) {
  const ix = await (await fetch(api.storeIndex(node))).json();
  const j = job && ix.history.includes(job) ? job : ix.latest;
  const m = await (await fetch(api.storeManifest(node, j))).json();
  return { node, job: j, header: m.objects.header, objects: m.objects, id: m.id, verify: m.verify, bytes: m.bytes, history: ix.history, latest: ix.latest, updated: ix.updated };
}

export class LayoutEngine {
  /** opts: onView(cam), onStats(text), onPick({item, inst, net, shape, overlay}), onHoverInfo, tipExtra(hit) */
  constructor(host, opts = {}) {
    this.host = host; this.o = opts;
    this.packs = new Map(); this.tiles = new Map(); this.rasters = new Map(); this.pending = new Map();
    this.items = []; this.insts = []; this.gpu = 0; this.hl = null; this.rulers = []; this.rulerMode = false; this.flash = null; this.selBox = null;
    this.phone = innerWidth <= 980 || matchMedia('(pointer: coarse)').matches;
    this.budget = this.phone ? 1.2e6 : 3e6; this.gpuCap = this.phone ? 150e6 : 300e6;
    this.palette = 'classic'; this.L = null; this.kindVis = Object.fromEntries(KINDS.map((k) => [k[0], !!k[2]]));
    this.show = { plan: true, labels: true, cores: true, minimap: true };
    this.names = { net: new Map(), inst: new Map() };
    this.dom = {};
    const d = this.dom;
    d.canvas = h('div', { style: { position: 'absolute', inset: '0' }, dataset: { testid: 'layout-canvas' } });
    d.tip = h('div.tip', { hidden: true });
    d.info = h('div.hud.bl', { dataset: { testid: 'layout-info' } }); d.scale = h('div.scalebar', h('i'), h('span'));
    d.mini = h('canvas.minimap', { width: 180, height: 120, 'aria-label': 'Minimap: click to move', dataset: { testid: 'minimap' } });
    host.append(d.canvas, d.scale, d.info, d.mini, d.tip);
    this.requestUpdate = raf(() => this.update());
    this._theme = () => { this.applyPalette(); this.miniDirty = true; this.requestUpdate(); };
    window.addEventListener('otx:theme', this._theme);
    this.ro = new ResizeObserver(() => { if (this.deck) { this.requestUpdate(); } }); this.ro.observe(host);
  }

  async start() {
    await loadDeck(); rectLayer();
    const NW = Math.max(2, Math.min(4, (navigator.hardwareConcurrency || 4) - 1));
    this.workers = []; this.wnext = 0;
    for (let i = 0; i < NW; i++) { const w = new Worker(WORKER_SRC); w.onmessage = (ev) => this.onWorker(ev.data); this.workers.push(w); }
    const cv = this.dom.canvas;
    this.vs = { target: [0, 0, 0], zoom: 0, minZoom: -8, maxZoom: 13 };
    this.deck = new window.deck.Deck({
      parent: cv, views: new window.deck.OrthographicView({ id: 'o', flipY: false, controller: true }), initialViewState: this.vs,
      controller: { scrollZoom: { speed: 0.012, smooth: false }, inertia: 250, doubleClickZoom: true, keyboard: true, dragRotate: false },
      onViewStateChange: ({ viewState }) => { this.vs = viewState; this.requestUpdate(); if (this.o.onView) this.o.onView(this.cam()); return viewState; },
      getCursor: ({ isDragging }) => this.rulerMode ? 'crosshair' : isDragging ? 'grabbing' : this.hoverHit ? 'pointer' : 'default',
      onClick: (info, ev) => this.onClick(info, ev), onHover: (info) => this.onDeckHover(info),
      useDevicePixels: Math.min(2, devicePixelRatio || 1), parameters: { clearColor: [0, 0, 0, 0], depthTest: false, blend: true }, layers: [],
      onError: (e) => console.warn('deck', e),
    });
    const move = raf(() => this.doHover(this.hev));
    cv.addEventListener('pointermove', (e) => { this.hev = e; move(); });
    cv.addEventListener('pointerleave', () => { this.dom.tip.hidden = true; this.mouse = null; this.hoverHit = null; this.stats(); });
    this.bindMini();
    this.started = true;
  }

  /* ------------------------------------------------------------------ scene */
  /** scene: {outline: [x0, y0, x1, y1] um, items, insts (plan rectangles, optional), packs: {id: info}} */
  setScene(scene, keepView) {
    if (!this.deck) return;   // destroyed while the caller was loading
    this.scene = scene; this.items = scene.items || []; this.insts = scene.insts || [];
    for (const [id, info] of Object.entries(scene.packs || {})) { const P = this.packs.get(id); if (!P) this.packs.set(id, { id, info, H: null, ob: info.objects || null }); else if (P.info.job !== info.job) this.dropPack(id, info); }
    const o = scene.outline, r = this.dom.canvas.getBoundingClientRect();
    this.fitZoom = Math.log2(Math.min((r.width || 800) / (o[2] - o[0]), (r.height || 600) / (o[3] - o[1])) * 0.93);
    this.vs = Object.assign({}, this.vs, { minZoom: this.fitZoom - 2, maxZoom: 13 });
    if (!keepView) this.vs = Object.assign({}, this.vs, { target: [(o[0] + o[2]) / 2, (o[1] + o[3]) / 2, 0], zoom: this.fitZoom });
    this.deck.setProps({ initialViewState: Object.assign({}, this.vs) });
    this.miniDirty = true; this.requestUpdate();
  }
  dropPack(id, info) {
    for (const k of [...this.tiles.keys()]) if (k.startsWith(id + '|')) { this.gpu -= this.tiles.get(k).bytes || 0; this.tiles.delete(k); }
    for (const k of [...this.rasters.keys()]) if (k.startsWith(id + '|')) this.rasters.delete(k);
    this.packs.set(id, { id, info, H: null, ob: info.objects || null });
  }
  /** register a pack and wait for its header (element scope needs the pack's die box before the scene exists) */
  async addPack(id, info) {
    let P = this.packs.get(id);
    if (!P || P.info.job !== info.job) { if (P) this.dropPack(id, info); else this.packs.set(id, { id, info, H: null, ob: info.objects || null }); P = this.packs.get(id); }
    this.needHeader(P); await P.hl;
    if (!P.H) throw new Error(P.err || 'pack header did not load');
    return P;
  }
  setItems(items) { this.items = items; this.miniDirty = true; this.requestUpdate(); }
  cam() { return { x: this.vs.target[0], y: this.vs.target[1], z: this.vs.zoom }; }
  setCam(x, y, z, ms) { this.vs = Object.assign({}, this.vs, { target: [x, y, 0], zoom: Math.max(this.vs.minZoom, Math.min(this.vs.maxZoom, z)), transitionDuration: ms || 0 }); this.deck.setProps({ initialViewState: Object.assign({}, this.vs) }); this.requestUpdate(); if (this.o.onView) this.o.onView(this.cam()); }
  zoomTo(bb, pad = 0.8, ms = 350) {
    const r = this.dom.canvas.getBoundingClientRect(), w = Math.max(0.2, bb[2] - bb[0]), hh = Math.max(0.2, bb[3] - bb[1]);
    this.setCam((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, Math.log2(Math.min(r.width / w, r.height / hh) * pad), ms);
  }
  fit() { const o = this.scene.outline; this.zoomTo(o, 0.93); }

  /* ------------------------------------------------------------------ packs */
  needHeader(P) {
    if (P.H || P.hl) return;
    P.hl = fetch(api.storeObject(P.info.header)).then((r) => { if (!r.ok) throw new Error(r.status + ' pack header'); return r.json(); }).then((H) => {
      P.H = H; P.tidx = new Map((H.grid.tiles || []).map((t) => [t.x + '_' + t.y, t]));
      this.workers.forEach((w) => w.postMessage({ op: 'init', pack: P.id, header: H }));
      if (!this.L) this.initLayers(H);
      if (this.o.onPack) this.o.onPack(P);
      this.requestUpdate();
    }).catch((e) => { P.err = String(e.message || e); console.warn('pack header', P.id, e); this.requestUpdate(); });
  }
  needManifest(P) {
    if (P.ob || P.ml) return;
    P.ml = fetch(api.storeManifest(P.id, P.info.job)).then((r) => r.json()).then((m) => { P.ob = m.objects; this.requestUpdate(); }).catch((e) => { P.err = String(e.message || e); });
  }
  objUrl(P, name) { const hsh = (P.ob && P.ob[name]) || (name.startsWith('r/0/') && P.info.r0 && P.info.r0[name.slice(4)]); return hsh ? location.origin + api.storeObject(hsh) : null; }

  initLayers(H) {
    const nl = H.layers.length;
    this.L = H.layers.map((l, i) => ({ i, name: l.name, type: l.type, dir: l.dir, vis: true, op: l.type === 'CUT' ? 0.85 : 0.7 }));
    this.L.push({ i: nl, name: 'Cells', type: 'CELLS', vis: true, op: 0.55 }, { i: nl + 1, name: 'Filler / tap', type: 'PHYS', vis: false, op: 0.35 });
    this.nl = nl;
    if (this.pendingHidden) { for (const l of this.L) if (this.pendingHidden.has(l.name)) l.vis = false; this.pendingHidden = null; }
    this.applyPalette();
    if (this.o.onLayers) this.o.onLayers(this.L);
  }
  light() { return cssv('color-scheme') === 'light' || (document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')) === 'light'; }
  applyPalette() {
    if (!this.L) return;
    const P = PAL[this.palette] || PAL.classic, light = this.light();
    for (const l of this.L) {
      let c, pat;
      if (l.type === 'CELLS') { c = cssv('--cellgrey'); pat = 10; } else if (l.type === 'PHYS') { c = cssv('--faint'); pat = 10; } else { const s = P[l.name]; c = s ? s[0] : cssv('--ink-3'); pat = s ? s[1] : 4; }
      if (light && l.type !== 'CELLS' && l.type !== 'PHYS') { const a = hexRgb(c); c = '#' + a.map((v) => Math.round(v * 0.82).toString(16).padStart(2, '0')).join(''); }
      l.color = c; l.pat = pat;
    }
    this.styleUniforms();
  }
  styleUniforms() {
    const col = new Float32Array(48 * 4), al = new Float32Array(48), pat = new Float32Array(48), kd = new Float32Array(20);
    for (const l of this.L) { const c = hexRgb(l.color); col.set([c[0] / 255, c[1] / 255, c[2] / 255, 1], l.i * 4); al[l.i] = l.vis ? l.op : 0; pat[l.i] = l.pat; }
    for (const k of KINDS) kd[k[0]] = this.kindVis[k[0]] ? 1 : 0;
    kd[14] = this.L[this.L.length - 1].vis ? 1 : 0; kd[15] = kd[16] = this.kindVis[10] ? 1 : 0;
    this.uni = { uColor: col, uAlpha: al, uPat: pat, uKind: kd, uFill: this.light() ? 0.32 : 0.22 };
    const st = {}; for (const l of this.L) { const c = hexRgb(l.color); st[l.i] = { r: c[0], g: c[1], b: c[2], a: l.vis ? l.op : 0 }; }
    this.rstyle = st; if (this.workers) this.workers.forEach((w) => w.postMessage({ op: 'restyle', style: st }));
    this.requestUpdate();
  }
  /** visibility changed: tiles are re-requested with the sections they now need (the worker keeps decoded sections) */
  setLayerVis(fn) { for (const l of this.L) l.vis = !!fn(l); this.afterVis(); }
  afterVis() { this.clearTiles(); this.styleUniforms(); if (this.o.onLayers) this.o.onLayers(this.L); }
  setKind(k, on) { this.kindVis[k] = on; if (k === 9 || k === 10) this.clearTiles(); this.styleUniforms(); }
  setOpacity(i, v) { this.L[i].op = v; this.styleUniforms(); }
  setPalette(p) { this.palette = p; this.applyPalette(); }
  preset(name) {
    for (const k of KINDS) this.kindVis[k[0]] = !!k[2];
    const up = (l) => { const m = /^[MV](\d+)$/.exec(l.name); return l.name === 'Pad' || (m && (l.name[0] === 'M' ? +m[1] >= 6 : +m[1] >= 5)); };
    if (name === 'all') this.L.forEach((l) => { l.vis = l.type !== 'PHYS'; });
    if (name === 'signals') { this.L.forEach((l) => { l.vis = l.type !== 'PHYS'; }); [1, 2, 3, 10, 5, 6, 12].forEach((k) => { this.kindVis[k] = false; }); }
    if (name === 'power') { this.L.forEach((l) => { l.vis = l.type !== 'PHYS' && l.type !== 'CELLS'; }); for (const k of KINDS) this.kindVis[k[0]] = [1, 2, 3, 10].includes(k[0]); }
    if (name === 'upper') { this.L.forEach((l) => { l.vis = !!up(l); }); this.kindVis[4] = true; }
    if (name === 'cells') this.L.forEach((l) => { l.vis = l.type === 'CELLS' || l.name === 'M1'; });
    this.afterVis();
  }
  hiddenLayers() { return this.L ? this.L.filter((l) => !l.vis && l.type !== 'PHYS').map((l) => l.name) : []; }
  setHidden(names) { const s = new Set(names); if (!this.L) { this.pendingHidden = s; return; } for (const l of this.L) if (l.type !== 'PHYS') l.vis = !s.has(l.name); this.afterVis(); }
  clearTiles() { this.tiles.clear(); this.gpu = 0; this.failed = 0; for (const k of [...this.pending.keys()]) if (k[0] === 't') this.pending.delete(k); }

  /* ------------------------------------------------------------------ LOD */
  viewBounds() {
    const vp = this.deck.getViewports()[0]; if (!vp) return null;
    const a = vp.unproject([0, 0]), b = vp.unproject([vp.width, vp.height]);
    return { x0: Math.min(a[0], b[0]), x1: Math.max(a[0], b[0]), y0: Math.min(a[1], b[1]), y1: Math.max(a[1], b[1]), w: vp.width, h: vp.height };
  }
  localBox(xf, b) {
    const ax = (b.x0 - xf.ox) * 1000 * xf.sx, bx = (b.x1 - xf.ox) * 1000 * xf.sx, ay = (b.y0 - xf.oy) * 1000 * xf.sy, by = (b.y1 - xf.oy) * 1000 * xf.sy;
    return { x0: Math.min(ax, bx), x1: Math.max(ax, bx), y0: Math.min(ay, by), y1: Math.max(ay, by) };
  }
  shapeCost(t) { let n = 0; for (const l of this.L) if (l.vis && l.i < t.n.length) n += t.n[l.i]; if (this.kindVis[9] || this.kindVis[10]) n += t.v * 3; if (this.L[this.nl].vis) n += t.c * 4; return n; }
  tilesIn(P, lb) {
    const G = P.H.grid, S = G.size, out = [];
    const tx0 = Math.max(0, Math.floor((lb.x0 - G.ox) / S)), tx1 = Math.min(G.nx - 1, Math.floor((lb.x1 - G.ox) / S)), ty0 = Math.max(0, Math.floor((lb.y0 - G.oy) / S)), ty1 = Math.min(G.ny - 1, Math.floor((lb.y1 - G.oy) / S));
    for (let y = ty0; y <= ty1; y++) for (let x = tx0; x <= tx1; x++) { const k = x + '_' + y; if (P.tidx.has(k)) out.push(k); }
    return out;
  }
  secsOf(P, k) {
    const t = P.tidx.get(k), out = [], L = this.L, nl = this.nl;
    if (!this._vl || this._vlH !== P.H) { this._vlH = P.H; this._vl = [...new Set(P.H.vias.flatMap((v) => v.boxes.map((b) => b[0])))]; this._cl = [...new Set(P.H.masters.filter((m) => !m.block).flatMap((m) => m.boxes.map((b) => b[0])))]; }
    for (const s of t.s || []) {
      if (s[0] === 'L') { const l = L[+s.slice(1)]; if (l && l.vis) out.push(s); }
      else if (s === 'v') { if ((this.kindVis[9] || this.kindVis[10]) && this._vl.some((li) => L[li] && L[li].vis)) out.push(s); }
      else if (s === 'c') { if (L[nl].vis || L[nl + 1].vis || this._cl.some((li) => L[li] && L[li].vis)) out.push(s); }
    }
    return out;
  }
  reqTile(P, k) {
    const key = P.id + '|' + k; if (this.pending.has('t' + key)) return;
    const secs = this.secsOf(P, k), parts = secs.map((s) => ({ name: s, url: this.objUrl(P, 't/' + k + '/' + s) }));
    if (!secs.length || parts.some((p) => !p.url)) { this.tiles.set(key, { n: 0, empty: true, bytes: 0, used: performance.now() }); return; }
    this.pending.set('t' + key, 1);
    this.workers[this.wnext++ % this.workers.length].postMessage({ op: 'tile', pack: P.id, key: k, parts, phys: this.L[this.nl + 1].vis, arrDetail: this.arrDetail });
  }
  reqRaster(P, k) {
    const key = P.id + '|' + k; if (this.rasters.has(key) || this.pending.has('r' + key)) return;
    const u = this.objUrl(P, 'r/' + k); if (!u) return;
    this.pending.set('r' + key, 1);
    this.workers[this.wnext++ % this.workers.length].postMessage({ op: 'raster', pack: P.id, key: k, url: u, style: this.rstyle });
  }
  onWorker(m) {
    const key = m.pack + '|' + m.key;
    if (m.op === 'tile') {
      this.pending.delete('t' + key);
      const old = this.tiles.get(key); if (old) this.gpu -= old.bytes || 0;
      const bytes = m.n * 28;
      this.tiles.set(key, { n: m.n, rects: m.rects, meta: m.meta, pick: m.pick, bytes, used: performance.now(), hasArr: m.hasArr, arrDetail: m.arrDetail }); this.gpu += bytes;
      if (!this.firstGeo) this.firstGeo = performance.now();
      this.requestUpdate();
    } else if (m.op === 'raster') {
      this.pending.delete('r' + key);
      const prev = this.rasters.get(key);
      this.rasters.set(key, { im: new ImageData(new Uint8ClampedArray(m.rgba.buffer), m.size, m.size), v: (prev ? prev.v : 0) + 1 });
      if (m.key.startsWith('0/')) this.miniDirty = true;
      this.requestUpdate();
    } else if (m.op === 'error') {   // remember the failure: no retry storm, and the raster stays on screen for that tile
      this.pending.delete((m.what === 'tile' ? 't' : 'r') + key);
      if (m.what === 'tile') { this.tiles.set(key, { n: 0, empty: true, failed: true, bytes: 0, used: performance.now() }); this.failed = (this.failed || 0) + 1; this.lastError = m.error; this.requestUpdate(); }
      if (!this.warned) { this.warned = true; console.warn('layout worker', m); }
    }
  }

  update() {
    if (!this.deck || !this.scene) return;
    const b = this.viewBounds(); if (!b) return;
    const ppu = Math.pow(2, this.vs.zoom), dpr = Math.min(2, devicePixelRatio || 1), ppl = ppu * 0.001;
    this.ppu = ppu;
    const ad = ppl * dpr >= 0.2; if (ad !== this.arrDetail) { this.arrDetail = ad; for (const [k, t] of this.tiles) if (t.hasArr && t.arrDetail !== ad) this.tiles.delete(k); }
    const vis = [];
    for (const it of this.items) { if (!meets(it.bb, b)) continue; it.px = Math.sqrt((it.bb[2] - it.bb[0]) * (it.bb[3] - it.bb[1])) * ppu; if (it.px < 6) continue; vis.push(it); }
    if (vis.length > 500) { vis.sort((p, q) => q.px - p.px); vis.length = 500; }   // thousands of tiny cores: the largest carry the picture, the rest stay plan rectangles
    const cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
    const dist = (p) => { const dx = Math.max(p.bb[0] - cx, 0, cx - p.bb[2]), dy = Math.max(p.bb[1] - cy, 0, cy - p.bb[3]); return dx * dx + dy * dy; };
    vis.sort((p, q) => dist(p) - dist(q));
    // pass 1: headers, raster level and shape cost of everything in view
    let total = 0, known = true; const want = new Set();
    for (const it of vis) {
      const P = this.packs.get(it.pack); it.P = P; it.geo = false; it.ts = null; it.cost = 0;
      if (!P) continue; this.needHeader(P);
      if (!P.H || !this.L) { known = false; continue; }
      const lb = this.localBox(it.xf, b); it.lb = lb;
      const lv = P.H.raster.levels; let level = 0;
      for (const Lr of lv) { level = Lr.level; if (Lr.px_nm * ppl <= 1.5) break; }
      it.rlv = level;
      if (level > 0 || ppu >= 0.2) this.needManifest(P);
      if (!P.ob) known = false;
      if (lv[0]) for (const n of lv[0].nodes) this.reqRaster(P, '0/' + n[0] + '_' + n[1]);
      const ts = this.tilesIn(P, lb); it.ts = ts;
      let c = 0; for (const k of ts) c += this.shapeCost(P.tidx.get(k));
      it.cost = c; total += c;
    }
    // pass 2: exact geometry only when the WHOLE view fits the shape budget (one decision per view, as in the one-pack
    // viewer; a per-item decision would draw sub-pixel wires for whichever small cores happen to fit); else the rasters
    const geoAll = known && total > 0 && total <= this.budget && ppu >= 0.25;
    let spent = 0, nGeo = 0;
    for (const it of vis) {
      const P = it.P; if (!P || !P.H || !this.L || !it.ts) continue;
      if (geoAll && P.ob) {
        spent += it.cost; it.geo = true; nGeo++;
        for (const k of it.ts) { const key = P.id + '|' + k; want.add(key); if (!this.tiles.has(key)) this.reqTile(P, k); }
      } else if (it.rlv > 0 && P.ob) {
        const lv = P.H.raster.levels, level = it.rlv, lb = it.lb, Lr = lv.find((q) => q.level === level);
        if (Lr) { const have = new Set(Lr.nodes.map((n) => n[0] + '_' + n[1])), node = Lr.node_nm, D = P.H.die;
          const nx0 = Math.max(0, Math.floor((lb.x0 - D[0]) / node)), nx1 = Math.floor((lb.x1 - D[0]) / node), ny0 = Math.max(0, Math.floor((lb.y0 - D[1]) / node)), ny1 = Math.floor((lb.y1 - D[1]) / node);
          for (let y = ny0; y <= ny1; y++) for (let x = nx0; x <= nx1; x++) if (have.has(x + '_' + y)) this.reqRaster(P, level + '/' + x + '_' + y); }
      }
    }
    if (this.gpu > this.gpuCap) {
      const lru = [...this.tiles.entries()].filter(([k]) => !want.has(k)).sort((p, q) => p[1].used - q[1].used);
      for (const [k, t] of lru) { if (this.gpu <= this.gpuCap * 0.8) break; this.gpu -= t.bytes || 0; this.tiles.delete(k); }
    }
    const now = performance.now(); want.forEach((k) => { const t = this.tiles.get(k); if (t) t.used = now; });
    this.vis = vis; this.st = { items: vis.length, geo: nGeo, spent, cost: total };
    this.render(b, vis, dpr);
    this.drawMini(b); this.drawScale(ppu); this.stats();
  }

  /* ------------------------------------------------------------------ draw */
  render(b, vis, dpr) {
    const D = window.deck, C = D.COORDINATE_SYSTEM.CARTESIAN, layers = [], ppu = this.ppu, W = b.w, Hh = b.h, tgt = this.vs.target;
    const fg = hexRgb(cssv('--faint')), ink = hexRgb(cssv('--ink')), canvas = hexRgb(cssv('--canvas')), macro = hexRgb(cssv('--macro'));
    const o = this.scene.outline;
    if (this.show.plan && this.insts.length) {
      const insts = this.insts.filter((r) => meets(r.bb, b));
      layers.push(new D.PolygonLayer({ id: 'plan', data: insts, getPolygon: (r) => rectPoly(r.bb), getFillColor: (r) => [...r.col, r.drawn ? 26 : r.dim ? 30 : 84], getLineColor: (r) => [...r.col, 255], lineWidthUnits: 'pixels', getLineWidth: 1,
        coordinateSystem: C, updateTriggers: { getFillColor: this.instVer, getLineColor: this.instVer } }));
    }
    for (const it of vis) {
      const P = it.P; if (!P || !P.H) continue;
      const allIn = it.geo && it.ts.every((k) => { const t = this.tiles.get(P.id + '|' + k); return t && !t.failed; });
      if (!allIn) {
        const R = P.H.raster.levels;
        const rl = (lvl) => { const Lr = R.find((q) => q.level === lvl); if (!Lr) return; const node = Lr.node_nm;
          for (const n of Lr.nodes) { const k = lvl + '/' + n[0] + '_' + n[1], r = this.rasters.get(P.id + '|' + k); if (!r) continue;
            const x0 = P.H.die[0] + n[0] * node, y0 = P.H.die[1] + n[1] * node, wb = xfBox(it.xf, x0, y0, x0 + node, y0 + node);
            if (!meets(wb, b)) continue;
            const bounds = [it.xf.sx < 0 ? wb[2] : wb[0], it.xf.sy < 0 ? wb[3] : wb[1], it.xf.sx < 0 ? wb[0] : wb[2], it.xf.sy < 0 ? wb[1] : wb[3]];   // a mirrored instance flips its bitmap
            layers.push(new D.BitmapLayer({ id: 'r' + it.key + k + ':' + r.v, image: r.im, bounds, coordinateSystem: C, textureParameters: { [10240]: 9729, [10241]: 9729 }, opacity: 1 })); } };
        rl(0); if (it.rlv > 0) rl(it.rlv);
      }
      if (it.geo) {
        const camL = [(tgt[0] - it.xf.ox) * 1000 * it.xf.sx, (tgt[1] - it.xf.oy) * 1000 * it.xf.sy];
        const uni = Object.assign({}, this.uni, { uPx: ppu * 0.001 * dpr, uCam: camL, uK: [it.xf.sx * 0.002 * ppu / W, it.xf.sy * 0.002 * ppu / Hh], uHl: this.hl ? (this.hl.pack === it.pack ? this.hl.net : 1e9) : 0 });
        for (const k of it.ts) { const t = this.tiles.get(P.id + '|' + k); if (!t || t.empty || !t.n) continue;
          layers.push(new RectLayer({ id: 't' + it.key + '|' + k, data: { length: t.n, attributes: { instanceRects: { value: t.rects, size: 4 }, instanceMeta: { value: t.meta, size: 3 } } }, coordinateSystem: C, lv: uni })); }
      }
    }
    layers.push(new D.PathLayer({ id: 'outline', data: [{ p: [[o[0], o[1]], [o[2], o[1]], [o[2], o[3]], [o[0], o[3]], [o[0], o[1]]] }], getPath: (d) => d.p, getColor: [...fg, 255], widthUnits: 'pixels', getWidth: 1.5, coordinateSystem: C }));
    if (this.show.cores) {
      const cores = this.items.filter((i) => i.level === 'core' && meets(i.bb, b) && Math.sqrt((i.bb[2] - i.bb[0]) * (i.bb[3] - i.bb[1])) * ppu >= 5);
      if (cores.length) layers.push(new D.PolygonLayer({ id: 'cores', data: cores, getPolygon: (i) => rectPoly(i.bb), filled: false, getLineColor: [...macro, 220], lineWidthUnits: 'pixels', getLineWidth: 1, coordinateSystem: C }));
    }
    if (this.o.overlays) { try { for (const l of this.o.overlays(D, { b, ppu, C }) || []) layers.push(l); } catch (e) { console.warn('overlay', e); } }
    if (this.show.labels && this.insts.length) {
      const lab = this.insts.filter((r) => meets(r.bb, b) && Math.min(r.bb[2] - r.bb[0], r.bb[3] - r.bb[1]) * ppu >= 70);
      layers.push(new D.TextLayer({ id: 'names', data: lab, getPosition: (r) => [r.bb[0], r.bb[3]], getText: (r) => r.label || r.name, getSize: 11, characterSet: 'auto', getColor: [...ink, 255], getTextAnchor: 'start', getAlignmentBaseline: 'top',
        getPixelOffset: [4, 4], background: true, getBackgroundColor: [...canvas, 200], backgroundPadding: [3, 1], fontFamily: 'ui-monospace, Menlo, monospace', coordinateSystem: C, updateTriggers: { getText: this.instVer } }));
    }
    const rs = this.rulers.concat(this.rulerLive ? [this.rulerLive] : []);
    if (rs.length) {
      const ac = hexRgb(cssv('--ruler'));
      layers.push(new D.LineLayer({ id: 'rulers', data: rs, getSourcePosition: (r) => r.a, getTargetPosition: (r) => r.b, getColor: [...ac, 255], widthUnits: 'pixels', getWidth: 2, coordinateSystem: C }));
      layers.push(new D.TextLayer({ id: 'rulert', data: rs, getPosition: (r) => [(r.a[0] + r.b[0]) / 2, (r.a[1] + r.b[1]) / 2], getText: (r) => { const dx = r.b[0] - r.a[0], dy = r.b[1] - r.a[1]; return `${fmt(Math.hypot(dx, dy), 3)} µm  (dx ${fmt(dx, 3)}, dy ${fmt(dy, 3)})`; },
        getSize: 12, characterSet: 'auto', getColor: [...ac, 255], background: true, getBackgroundColor: [...canvas, 225], backgroundPadding: [4, 2], fontFamily: 'ui-monospace, Menlo, monospace', getTextAnchor: 'start', getAlignmentBaseline: 'bottom', getPixelOffset: [6, -6], coordinateSystem: C }));
    }
    const rings = [];
    if (this.selBox) for (const q of this.selBox) rings.push({ q: q.bb, c: hexRgb(cssv(q.strong ? '--accent' : '--select')), w: q.strong ? 3 : 1.5 });
    if (this.flash) rings.push({ q: this.flash, c: hexRgb(cssv('--accent')), w: 2.5 });
    if (rings.length) layers.push(new D.PolygonLayer({ id: 'rings', data: rings, getPolygon: (r) => rectPoly(r.q), filled: false, getLineColor: (r) => [...r.c, 255], lineWidthUnits: 'pixels', getLineWidth: (r) => r.w, coordinateSystem: C }));
    this.deck.setProps({ layers });
  }

  /* ------------------------------------------------------------------ hover / pick */
  worldAt(e) { const vp = this.deck.getViewports()[0], r = this.dom.canvas.getBoundingClientRect(); return vp.unproject([e.clientX - r.left, e.clientY - r.top]); }
  pickShape(P, x, y, tol) {
    const G = P.H.grid, tx = Math.floor((x - G.ox) / G.size), ty = Math.floor((y - G.oy) / G.size), L = this.L;
    let best = null, bo = -Infinity;
    for (let yy = ty - 1; yy <= ty + 1; yy++) for (let xx = tx - 1; xx <= tx + 1; xx++) {
      const t = this.tiles.get(P.id + '|' + xx + '_' + yy); if (!t || !t.pick) continue; const p = t.pick;
      for (let i = t.n - 1; i >= 0; i--) {
        if (x < p.x0[i] - tol || x > p.x1[i] + tol || y < p.y0[i] - tol || y > p.y1[i] + tol) continue;
        const l = L[p.layer[i]]; if (!l || !l.vis || !(p.kind[i] === 14 ? L[L.length - 1].vis : this.kindVis[p.kind[i]])) continue;
        const o2 = (p.kind[i] >= 13 ? -1e9 : 0) + p.layer[i] * 1e7 + i;
        if (o2 > bo) { bo = o2; best = { p, i }; }
      }
    }
    return best;
  }
  pickAt(w) {
    const inst = this.insts.find((q) => w[0] >= q.bb[0] && w[0] < q.bb[2] && w[1] >= q.bb[1] && w[1] < q.bb[3]) || null;
    const under = (this.vis || []).filter((it) => w[0] >= it.bb[0] && w[0] < it.bb[2] && w[1] >= it.bb[1] && w[1] < it.bb[3]).sort((a, c) => (c.level === 'core') - (a.level === 'core'));
    const tol = 2 / (this.ppu * 0.001);
    for (const it of under) {
      if (!it.geo || !it.P || !it.P.H) continue;
      const lx = (w[0] - it.xf.ox) * 1000 * it.xf.sx, ly = (w[1] - it.xf.oy) * 1000 * it.xf.sy, s = this.pickShape(it.P, lx, ly, tol);
      if (s) { const { p, i } = s; return { inst, item: it, local: [lx, ly], shape: { layer: p.layer[i], kind: p.kind[i], net: p.net[i], aux: p.aux[i], pin: p.pin[i], box: [p.x0[i], p.y0[i], p.x1[i], p.y1[i]] } }; }
    }
    const it = under[0] || null;
    return { inst, item: it, local: it ? [(w[0] - it.xf.ox) * 1000 * it.xf.sx, (w[1] - it.xf.oy) * 1000 * it.xf.sy] : null, shape: null };
  }
  async lookup(pack, kind, ids) {
    const m = this.names[kind], need = ids.filter((i) => !m.has(pack + '|' + i));
    if (need.length) { try { const r = await api.names(pack, kind, need); for (const it of r.items || []) m.set(pack + '|' + it.id, it); } catch (e) { /* names stay ids */ } }
    return ids.map((i) => m.get(pack + '|' + i));
  }
  async doHover(e) {
    if (!this.scene || !e || !this.deck.getViewports()[0]) return;
    const w = this.worldAt(e); this.mouse = w; this.stats();
    if (this.rulerMode && this.rulerLive) { this.rulerLive.b = [w[0], w[1]]; this.requestUpdate(); }
    if (this.overlayHover) return;
    const hit = this.pickAt(w), tip = this.dom.tip; this.hoverHit = hit.shape || hit.inst ? hit : null;
    if (!hit.inst && !hit.shape) { tip.hidden = true; return; }
    const draw = (nn, cell) => {
      clear(tip);
      if (hit.shape) {
        const s = hit.shape, H = hit.item.P.H, l = this.L[s.layer], dbu = 1000;
        tip.append(h('b', `${l.name} · ${KIND_NAME[s.kind] || 'shape'}`), h('div.m', `${fmt((s.box[2] - s.box[0]) / dbu, 3)} × ${fmt((s.box[3] - s.box[1]) / dbu, 3)} µm`));
        if (s.kind === 9 || s.kind === 10) { const vt = H.vias[s.aux]; if (vt) tip.append(h('div.m', 'via ' + vt.name)); }
        if (cell) { const m = H.masters[cell.master]; tip.append(h('div', 'instance ', h('b', cell.name)), h('div.m', `master ${m ? m.name : cell.master}` + (s.pin >= 0 && m && m.pins[s.pin] ? ` · pin ${m.pins[s.pin].name}` : ''))); }
        if (s.net > 0) tip.append(h('div', 'net ', h('b', nn ? nn.name : '#' + s.net), nn && nn.sig && nn.sig !== 'SIGNAL' ? ' · ' + nn.sig : ''), h('div.m', 'click to highlight the net'));
      }
      if (hit.inst) tip.append(h('div', { style: hit.shape ? { marginTop: '4px', paddingTop: '4px', borderTop: '1px solid var(--line)' } : null }, h('b', hit.inst.name), hit.item && hit.item.level === 'core' ? h('span.m', ' / ' + hit.item.cname) : null), h('div.m', hit.inst.sub || ''));
      if (this.o.tipExtra) { const x = this.o.tipExtra(hit); if (x) tip.append(x); }
      if (!tip.childNodes.length) { tip.hidden = true; return; }
      tip.hidden = false; const r = this.host.getBoundingClientRect(); let X = e.clientX - r.left + 14, Y = e.clientY - r.top + 14;
      if (X + tip.offsetWidth > r.width - 6) X = e.clientX - r.left - tip.offsetWidth - 14; if (Y + tip.offsetHeight > r.height - 6) Y = e.clientY - r.top - tip.offsetHeight - 14;
      tip.style.left = Math.max(4, X) + 'px'; tip.style.top = Math.max(4, Y) + 'px';
    };
    draw(null, null);
    if (hit.shape) {
      const s = hit.shape, pk = hit.item.pack;
      const [nn] = s.net > 0 ? await this.lookup(pk, 'net', [s.net]) : [null];
      const [cell] = s.kind >= 11 ? await this.lookup(pk, 'inst', [s.aux]) : [null];
      if (this.hoverHit === hit) draw(nn, cell);
    }
  }
  onDeckHover(info) {
    this.overlayHover = !!(info && info.object && info.layer && this.o.overlayTip && this.o.overlayTip(info, this.dom.tip, this.host));
  }
  onClick(info, ev) {
    const w = info.coordinate; if (!w) return;
    if (this.rulerMode) { if (!this.rulerLive) this.rulerLive = { a: [w[0], w[1]], b: [w[0], w[1]] }; else { this.rulerLive.b = [w[0], w[1]]; this.rulers.push(this.rulerLive); this.rulerLive = null; } this.requestUpdate(); return; }
    if (info.object && info.layer && this.o.overlayClick && this.o.overlayClick(info)) return;
    const hit = this.pickAt(w);
    if (this.o.onPick) this.o.onPick(hit, ev);
  }
  highlight(pack, net) { this.hl = net > 0 ? { pack, net } : null; this.requestUpdate(); }
  setRuler(on) { this.rulerMode = on; this.rulerLive = null; this.requestUpdate(); }
  clearMarks() { this.rulers = []; this.rulerLive = null; this.flash = null; this.requestUpdate(); }

  /* ------------------------------------------------------------------ minimap, scale, read-out */
  bindMini() {
    const cv = this.dom.mini; let down = false;
    const go = (e) => { const r = cv.getBoundingClientRect(), m = this.mg; if (!m) return; this.setCam(m.x0 + (e.clientX - r.left - m.ox) / m.s, m.y0 + (m.h - (e.clientY - r.top - m.oy)) / m.s, this.vs.zoom); };
    cv.addEventListener('pointerdown', (e) => { down = true; cv.setPointerCapture(e.pointerId); go(e); });
    cv.addEventListener('pointermove', (e) => { if (down) go(e); });
    cv.addEventListener('pointerup', () => { down = false; }); cv.addEventListener('pointercancel', () => { down = false; });
  }
  drawMini(b) {
    const cv = this.dom.mini; cv.hidden = !this.show.minimap; if (cv.hidden) return;
    const dpr = Math.min(2, devicePixelRatio || 1), CW = 180, CH = 120, o = this.scene.outline;
    if (cv.width !== CW * dpr) { cv.width = CW * dpr; cv.height = CH * dpr; cv.style.width = CW + 'px'; cv.style.height = CH + 'px'; this.miniDirty = true; }
    const W = o[2] - o[0], Hh = o[3] - o[1], s = Math.min((CW - 8) / W, (CH - 8) / Hh), ox = (CW - W * s) / 2, oy = (CH - Hh * s) / 2;
    this.mg = { s, ox, oy, x0: o[0], y0: o[1], h: Hh * s };
    if (this.miniDirty || !this.miniBg) {
      this.miniDirty = false; const bg = document.createElement('canvas'); bg.width = CW * dpr; bg.height = CH * dpr; const g = bg.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.fillStyle = cssv('--canvas'); g.fillRect(0, 0, CW, CH);
      const px = (x) => ox + (x - o[0]) * s, py = (y) => oy + Hh * s - (y - o[1]) * s;
      if (this.insts.length) for (const r of this.insts) { g.fillStyle = `rgba(${r.col[0]},${r.col[1]},${r.col[2]},${r.drawn ? 0.95 : 0.4})`; g.fillRect(px(r.bb[0]), py(r.bb[3]), Math.max(0.7, (r.bb[2] - r.bb[0]) * s - 0.3), Math.max(0.7, (r.bb[3] - r.bb[1]) * s - 0.3)); }
      else for (const it of this.items) { const P = this.packs.get(it.pack); if (!P || !P.H) continue; const L0 = P.H.raster.levels[0]; if (!L0) continue;
        for (const n of L0.nodes) { const r = this.rasters.get(P.id + '|0/' + n[0] + '_' + n[1]); if (!r) continue; const t = document.createElement('canvas'); t.width = r.im.width; t.height = r.im.height; t.getContext('2d').putImageData(r.im, 0, 0);
          const node = L0.node_nm, wb = xfBox(it.xf, P.H.die[0] + n[0] * node, P.H.die[1] + n[1] * node, P.H.die[0] + (n[0] + 1) * node, P.H.die[1] + (n[1] + 1) * node);
          g.save(); g.translate(px(wb[0]), py(wb[3])); g.scale((wb[2] - wb[0]) * s / r.im.width, (wb[3] - wb[1]) * s / r.im.height); g.drawImage(t, 0, 0); g.restore(); } }
      this.miniBg = bg;
    }
    const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, CW, CH); g.drawImage(this.miniBg, 0, 0, CW, CH);
    g.strokeStyle = cssv('--line-strong'); g.lineWidth = 1; g.strokeRect(ox, oy, W * s, Hh * s);
    g.strokeStyle = cssv('--accent'); g.lineWidth = 1.5;
    const x0 = Math.max(-2, ox + (b.x0 - o[0]) * s), x1 = Math.min(CW + 2, ox + (b.x1 - o[0]) * s), y0 = Math.max(-2, oy + Hh * s - (b.y1 - o[1]) * s), y1 = Math.min(CH + 2, oy + Hh * s - (b.y0 - o[1]) * s);
    if (x1 - x0 < 4 || y1 - y0 < 4) { g.beginPath(); g.arc((x0 + x1) / 2, (y0 + y1) / 2, 3.5, 0, 7); g.stroke(); } else g.strokeRect(x0, y0, x1 - x0, y1 - y0);
  }
  drawScale(ppu) {
    const um = 110 / ppu, m = Math.pow(10, Math.floor(Math.log10(um))), e = um / m, step = (e >= 5 ? 5 : e >= 2 ? 2 : 1) * m, el = this.dom.scale;
    el.querySelector('i').style.width = (step * ppu) + 'px';
    el.querySelector('span').textContent = step >= 1000 ? fmt(step / 1000, 0) + ' mm' : step >= 1 ? fmt(step, 0) + ' µm' : fmt(step * 1000, 0) + ' nm';
  }
  stats() {
    const s = this.st || {}, loading = this.pending.size, mode = s.geo ? 'exact geometry' : s.items ? 'density raster' : 'plan';
    this.mode = s.geo ? 'geometry' : s.items ? 'raster' : 'plan';
    this.dom.info.textContent = `${mode}${s.spent ? ' · ' + fmt(s.spent) + ' shapes' : s.cost ? ' · ' + fmt(s.cost) + ' shapes in view, zoom in for wires' : ''}${loading ? ' · loading ' + loading : ''}${this.failed ? ` · ${this.failed} tiles could not be decoded (raster shown)` : ''}`;
    this.dom.info.dataset.mode = this.mode; this.dom.info.dataset.loading = loading;
    if (this.o.onStats) this.o.onStats({ mouse: this.mouse, ppu: this.ppu, zoom: this.vs.zoom, mode: this.mode, gpu: this.gpu, loading, ...s });
  }
  destroy() {
    window.removeEventListener('otx:theme', this._theme); this.ro.disconnect();
    if (this.deck) { this.deck.finalize(); this.deck = null; }
    (this.workers || []).forEach((w) => w.terminate()); this.workers = [];
    clear(this.host);
  }
}

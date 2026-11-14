/* Layout viewer worker: fetches and decodes tiles / raster nodes off the main thread and builds the GPU instance
   buffers (layout.js draws them).  Messages in:
     {op:'init', header, base}                         header JSON, blob URL prefix
     {op:'tile', key, parts:[{name,url}], phys}         -> {op:'tile', key, secs, n, rects, meta, pick:{x0,y0,x1,y1,layer,kind,net,aux,pin}, ox, oy}
                                                          (parts: the tile's sections the view needs: L<layer>, v, c)
     {op:'raster', key, url, style}                    -> {op:'raster', key, rgba (256*256*4), layers}
     {op:'restyle', style}                             -> re-composite every cached raster node: {op:'raster', ...} each
   Instance buffers: rects Float32 [x0,y0,x1,y1] absolute DBU (exact in float32 below 2^24 = 16.7 mm; deck.gl's identity
   projection subtracts the camera position in the shader, so precision holds at any zoom); meta Float32 [layer, clip | kind << 4, net].
   Draw order = layer order (tech order), synthetic layers after: nl cell outlines, nl+1 physical-only cell outlines. */
'use strict';
importScripts('/explorer/element/lv_decode.js');
const D = self.LVDecode;
let H = null, NL = 0;
const HS = new Map();   // multi-pack (die viewer): pack id -> header; a message's `pack` field selects it (default '' = the single-pack element page)
function usePack(id){ const h = HS.get(id || ''); if (!h) throw new Error('no header for pack ' + id); H = h; NL = h.layers.length; return h; }
const planes = new Map();   // raster key -> {layers, planes}
let style = null;

// via arrays (power-grid vias with many cuts per layer): drawn as one merged box per (via, cut layer) until the cuts
// are at least a couple of pixels wide (arrDetail), then cut by cut.  Enclosures are always drawn exactly.
const ARRS = new Map();   // via type -> {layer: [cut box indices]} for layers with > 4 boxes
function viaArrays(){
  if (ARRS.has(H)) return ARRS.get(H);
  const arrInfo = H.vias.map(v => { const by = {}; v.boxes.forEach((b, j) => (by[b[0]] = by[b[0]] || []).push(j)); const o = {};
    for (const li in by) if (by[li].length > 4){ const bs = by[li].map(j => v.boxes[j]);
      // loop, not Math.min(...array): a power via with >100k cuts overflowed the call stack (hbm q_mca, every tile failed)
      const bb = [Infinity, Infinity, -Infinity, -Infinity];
      for (const q of bs){ if (q[1] < bb[0]) bb[0] = q[1]; if (q[2] < bb[1]) bb[1] = q[2]; if (q[3] > bb[2]) bb[2] = q[3]; if (q[4] > bb[3]) bb[3] = q[4]; }
      o[li] = bb; }
    return Object.keys(o).length ? o : null; });
  ARRS.set(H, arrInfo); return arrInfo;
}
const MAX_CUTS = 3e6;   // via-array cuts per tile build; above it the arrays are drawn merged (reported, not an error)
function CutLimit(){ this.cutLimit = true; }
function buildTile(T, phys, arrDetail, win){
  // win = [x0, y0, x1, y1] local DBU (optional): via-array cuts are emitted only inside it.  A power via can carry >100k cuts and a
  // tile hundreds of such vias; cut by cut for the whole tile that is tens of millions of shapes and the allocation fails in
  // the browser.  At the zoom where cuts are drawn the screen shows a few um, so the window bounds the work.
  // gather per layer (dense lists) so the output is in draw order
  const per = Array.from({length: NL + 2}, () => []);
  let hasArr = false, ncut = 0;
  // wire pieces (aux = shape id); cell shapes are built below so they carry their instance and pin
  D.forEachShape({rects: T.rects, vias: null, cells: null}, H, (li, x0, y0, x1, y1, net, kind, clip, id) => { per[li].push(x0, y0, x1, y1, net, kind, clip, id, -1, -1); });
  if (T.vias){ const v = T.vias, VT = H.vias, AI = viaArrays();
    for (let i = 0; i < v.n; i++){ const t = v.type[i], bx = VT[t].boxes, arr = AI[t], k = v.kind[i] ? 10 : 9, X = v.x[i], Y = v.y[i];
      if (arr) hasArr = true;
      for (let j = 0; j < bx.length; j++){ const q = bx[j];
        if (arr && arr[q[0]]){ if (!arrDetail) continue;
          if (win && (X + q[3] < win[0] || X + q[1] > win[2] || Y + q[4] < win[1] || Y + q[2] > win[3])) continue;
          if (++ncut > MAX_CUTS) throw new CutLimit();
          per[q[0]].push(X + q[1], Y + q[2], X + q[3], Y + q[4], v.net[i], 16, 0, t, -1, -1); continue; }
        per[q[0]].push(X + q[1], Y + q[2], X + q[3], Y + q[4], v.net[i], k, 0, t, -1, -1); }
      if (arr && !arrDetail) for (const li in arr){ const a = arr[li]; per[+li].push(X + a[0], Y + a[1], X + a[2], Y + a[3], v.net[i], 15, 0, t, -1, -1); } } }
  if (T.cells){ const c = T.cells, M = H.masters;
    for (let i = 0; i < c.n; i++){
      const isPhys = (c.flags[i] & 4) !== 0; if (isPhys && !phys) continue;
      const m = M[c.master[i]], bx = m.boxes, o = c.orient[i], X = c.x[i], Y = c.y[i];
      for (let j = 0; j < bx.length; j++){ const q = bx[j], a = D.orient(o, q[1], q[2]), b = D.orient(o, q[3], q[4]);
        const net = q[5] >= 0 ? c.nets[c.pinOff[i] + q[5]] : 0;
        per[q[0]].push(Math.min(a[0], b[0]) + X, Math.min(a[1], b[1]) + Y, Math.max(a[0], b[0]) + X, Math.max(a[1], b[1]) + Y, net, q[5] >= 0 ? 11 : 12, 0, -1, c.inst[i], q[5]); }
      // outline: the instance box = master box placed
      const a = D.orient(o, 0, 0), b = D.orient(o, m.w, m.h);
      per[isPhys ? NL + 1 : NL].push(Math.min(a[0], b[0]) + X, Math.min(a[1], b[1]) + Y, Math.max(a[0], b[0]) + X, Math.max(a[1], b[1]) + Y, 0, isPhys ? 14 : 13, 0, -1, c.inst[i], -1);
    } }
  let n = 0; for (const a of per) n += a.length / 10;
  const rects = new Float32Array(n * 4), meta = new Float32Array(n * 3);
  const px0 = new Int32Array(n), py0 = new Int32Array(n), px1 = new Int32Array(n), py1 = new Int32Array(n), lay = new Uint8Array(n), kind = new Uint8Array(n),
    net = new Int32Array(n), aux = new Int32Array(n), pin = new Int16Array(n);
  let k = 0;
  const ox = T.ox, oy = T.oy;
  for (let li = 0; li < per.length; li++){ const a = per[li];
    for (let i = 0; i < a.length; i += 10, k++){
      rects[4 * k] = a[i]; rects[4 * k + 1] = a[i + 1]; rects[4 * k + 2] = a[i + 2]; rects[4 * k + 3] = a[i + 3];   // absolute DBU: exact in float32 below 2^24 nm
      meta[3 * k] = li; meta[3 * k + 1] = a[i + 6] + 16 * a[i + 5]; meta[3 * k + 2] = a[i + 4];
      px0[k] = a[i]; py0[k] = a[i + 1]; px1[k] = a[i + 2]; py1[k] = a[i + 3]; lay[k] = li; kind[k] = a[i + 5]; net[k] = a[i + 4];
      aux[k] = a[i + 8] >= 0 ? a[i + 8] : a[i + 7]; pin[k] = a[i + 9];
    } }
  return {n, rects, meta, pick: {x0: px0, y0: py0, x1: px1, y1: py1, layer: lay, kind, net, aux, pin}, ox, oy, hasArr, arrDetail,
    vias: T.vias ? T.vias.n : 0, cells: T.cells ? T.cells.n : 0};
}

function composite(R){
  const S = R.size, out = new Uint8ClampedArray(S * S * 4);
  const acc = new Float32Array(S * S * 4);   // non-premultiplied over, done in float
  for (let k = 0; k < R.layers.length; k++){
    const li = R.layers[k], st = style && style[li]; if (!st || !(st.a > 0)) continue;
    const p = R.planes[k], cr = st.r, cg = st.g, cb = st.b, ka = Math.min(1, st.a * 1.6);
    for (let i = 0, j = 0; i < p.length; i++, j += 4){
      const c = p[i]; if (!c) continue;
      const a = (c / 255) * ka, A = acc[j + 3], na = a + A * (1 - a);
      acc[j] = (cr * a + acc[j] * A * (1 - a)) / na; acc[j + 1] = (cg * a + acc[j + 1] * A * (1 - a)) / na; acc[j + 2] = (cb * a + acc[j + 2] * A * (1 - a)) / na; acc[j + 3] = na;
    } }
  // image row 0 is the TOP of the node (BitmapLayer / canvas convention); raster row 0 is its bottom
  for (let y = 0; y < S; y++){ const src = (S - 1 - y) * S * 4, dst = y * S * 4;
    for (let x = 0; x < S * 4; x += 4){ out[dst + x] = acc[src + x]; out[dst + x + 1] = acc[src + x + 1]; out[dst + x + 2] = acc[src + x + 2]; out[dst + x + 3] = acc[src + x + 3] * 255; } }
  return out;
}

// every failure carries its class: "fetch: ..." (network / HTTP, retried), "decode: ..." (bad tile data), "build: ..." (memory)
async function get(url){
  let last = '';
  for (let k = 0; k < 4; k++){
    if (k) await new Promise(res => setTimeout(res, 250 * k * k));
    try {
      const r = await fetch(url);
      if (r.ok){ const b = new Uint8Array(await r.arrayBuffer()); if (!b.length) { last = 'empty object'; continue; } return b; }
      last = 'HTTP ' + r.status; if (r.status < 500 && r.status !== 429 && r.status !== 408) break;   // 4xx will not get better
    } catch (e) { last = String(e && e.message || e); }
  }
  throw new Error('fetch: ' + last + ' (' + String(url).split('/').pop().slice(0, 16) + ')');
}
// decoded tile sections, kept so a layer switched on later costs only its own section (LRU by count)
const secCache = new Map(); let secMem = 0; const SEC_CAP = 160e6;
function memOf(T){ let n = 0; const add = o => { for (const k in o){ const v = o[k]; if (v && v.byteLength != null) n += v.byteLength; } };
  for (const li in T.rects) add(T.rects[li]); if (T.vias) add(T.vias); if (T.cells) add(T.cells); return n + 256; }
async function section(p, Hd){
  let T = secCache.get(p.url);
  if (T){ secCache.delete(p.url); secCache.set(p.url, T); return T; }
  const buf = await get(p.url);
  try { T = D.decodeTile(buf, Hd); } catch (e) { throw new Error('decode: ' + String(e && e.message || e) + ' (section ' + p.name + ', ' + buf.length + ' bytes)'); }
  T.bytes = buf.length; T.mem = memOf(T);
  secCache.set(p.url, T); secMem += T.mem;
  // bounded by decoded bytes (was: 6000 sections, which on dense types is several GB per worker and ends in failed allocations)
  while (secMem > SEC_CAP && secCache.size > 1){ const k = secCache.keys().next().value; secMem -= secCache.get(k).mem; secCache.delete(k); }
  return T;
}

self.onmessage = async (ev) => {
  const m = ev.data;
  try {
    if (m.op === 'init'){ HS.set(m.pack || '', m.header); usePack(m.pack); return; }
    if (m.op === 'tile'){
      const t0 = performance.now();
      const Hp = usePack(m.pack);
      const parts = await Promise.all(m.parts.map(q => section(q, Hp)));
      const t1 = performance.now();
      const T = {ox: parts[0].ox, oy: parts[0].oy, size: parts[0].size, rects: {}, vias: null, cells: null};
      let bytes = 0;
      for (const P of parts){ Object.assign(T.rects, P.rects); if (P.vias) T.vias = P.vias; if (P.cells) T.cells = P.cells; bytes += P.bytes; }
      usePack(m.pack);
      let r, note = null;
      try { r = buildTile(T, m.phys, m.arrDetail, m.win || null); }
      catch (e) {
        if (e && e.cutLimit){ r = buildTile(T, m.phys, false, null); r.arrDetail = m.arrDetail; note = 'via arrays drawn merged: more than ' + MAX_CUTS + ' cuts in view'; }
        else throw new Error('build: ' + String(e && e.message || e));
      }
      r.note = note; r.win = m.win || null;
      r.op = 'tile'; r.key = m.key; r.pack = m.pack || ''; r.secs = m.parts.map(p => p.name); r.bytes = bytes; r.ms = [t1 - t0, performance.now() - t1];
      const p = r.pick;
      self.postMessage(r, [r.rects.buffer, r.meta.buffer, p.x0.buffer, p.y0.buffer, p.x1.buffer, p.y1.buffer, p.layer.buffer, p.kind.buffer, p.net.buffer, p.aux.buffer, p.pin.buffer]);
      return;
    }
    if (m.op === 'raster'){
      if (m.style) style = m.style;
      const pk = (m.pack || '') + '|' + m.key; let R = planes.get(pk);
      if (!R){ R = D.decodeRaster(await get(m.url)); planes.set(pk, R); if (planes.size > 400) planes.delete(planes.keys().next().value); }
      const rgba = composite(R);
      self.postMessage({op: 'raster', key: m.key, pack: m.pack || '', rgba, size: R.size, layers: R.layers}, [rgba.buffer]);
      return;
    }
    if (m.op === 'restyle'){
      style = m.style;
      for (const [pk2, R] of planes){ const i2 = pk2.indexOf('|'), key = pk2.slice(i2 + 1); const rgba = composite(R); self.postMessage({op: 'raster', key, pack: pk2.slice(0, i2), rgba, size: R.size, layers: R.layers, restyle: true}, [rgba.buffer]); }
      return;
    }
  } catch (e) {
    self.postMessage({op: 'error', key: m.key, pack: m.pack || '', what: m.op, error: String(e && e.message || e)});
  }
};

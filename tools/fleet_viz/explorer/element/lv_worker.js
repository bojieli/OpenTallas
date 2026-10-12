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
importScripts('lv_decode.js');
const D = self.LVDecode;
let H = null, NL = 0;
const planes = new Map();   // raster key -> {layers, planes}
let style = null;

function buildTile(T, phys){
  // gather per layer (dense lists) so the output is in draw order
  const per = Array.from({length: NL + 2}, () => []);
  // wire pieces and via boxes (aux = shape id / -1); cell shapes are built below so they carry their instance and pin
  D.forEachShape({rects: T.rects, vias: T.vias, cells: null}, H, (li, x0, y0, x1, y1, net, kind, clip, id) => { per[li].push(x0, y0, x1, y1, net, kind, clip, id, -1, -1); });
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
  return {n, rects, meta, pick: {x0: px0, y0: py0, x1: px1, y1: py1, layer: lay, kind, net, aux, pin}, ox, oy,
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

async function get(url){
  const r = await fetch(url); if (!r.ok) throw new Error(r.status + ' ' + url);
  return new Uint8Array(await r.arrayBuffer());
}
// decoded tile sections, kept so a layer switched on later costs only its own section (LRU by count)
const secCache = new Map();
async function section(p){
  let T = secCache.get(p.url);
  if (T){ secCache.delete(p.url); secCache.set(p.url, T); return T; }
  const buf = await get(p.url); T = D.decodeTile(buf, H); T.bytes = buf.length;
  secCache.set(p.url, T); if (secCache.size > 6000) secCache.delete(secCache.keys().next().value);
  return T;
}

self.onmessage = async (ev) => {
  const m = ev.data;
  try {
    if (m.op === 'init'){ H = m.header; NL = H.layers.length; return; }
    if (m.op === 'tile'){
      const t0 = performance.now();
      const parts = await Promise.all(m.parts.map(section));
      const t1 = performance.now();
      const T = {ox: parts[0].ox, oy: parts[0].oy, size: parts[0].size, rects: {}, vias: null, cells: null};
      let bytes = 0;
      for (const P of parts){ Object.assign(T.rects, P.rects); if (P.vias) T.vias = P.vias; if (P.cells) T.cells = P.cells; bytes += P.bytes; }
      const r = buildTile(T, m.phys);
      r.op = 'tile'; r.key = m.key; r.secs = m.parts.map(p => p.name); r.bytes = bytes; r.ms = [t1 - t0, performance.now() - t1];
      const p = r.pick;
      self.postMessage(r, [r.rects.buffer, r.meta.buffer, p.x0.buffer, p.y0.buffer, p.x1.buffer, p.y1.buffer, p.layer.buffer, p.kind.buffer, p.net.buffer, p.aux.buffer, p.pin.buffer]);
      return;
    }
    if (m.op === 'raster'){
      if (m.style) style = m.style;
      let R = planes.get(m.key);
      if (!R){ R = D.decodeRaster(await get(m.url)); planes.set(m.key, R); if (planes.size > 400) planes.delete(planes.keys().next().value); }
      const rgba = composite(R);
      self.postMessage({op: 'raster', key: m.key, rgba, size: R.size, layers: R.layers}, [rgba.buffer]);
      return;
    }
    if (m.op === 'restyle'){
      style = m.style;
      for (const [key, R] of planes){ const rgba = composite(R); self.postMessage({op: 'raster', key, rgba, size: R.size, layers: R.layers, restyle: true}, [rgba.buffer]); }
      return;
    }
  } catch (e) {
    self.postMessage({op: 'error', key: m.key, what: m.op, error: String(e && e.message || e)});
  }
};

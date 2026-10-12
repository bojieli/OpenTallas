/* Layout viewer tile decoder (schema opentallas.layout_viewer.pack.v1; encoder tools/layout_viewer/lv_tile.py).
   One file for the browser (window.LVDecode) and node (module.exports): the round-trip check
   (tools/layout_viewer/lv_verify.mjs) decodes tiles with exactly the code the viewer runs. */
(function(root){
'use strict';

function Reader(u8, pos, end){ this.u = u8; this.p = pos; this.end = end; }
Reader.prototype.vu = function(){   // LEB128 -> Number (exact to 2^53)
  const u = this.u; let r = 0, m = 1, b;
  do { b = u[this.p++]; r += (b & 0x7f) * m; m *= 128; } while (b & 0x80);
  return r;
};
Reader.prototype.col = function(n, zig){
  const a = new Float64Array(n);
  if (zig) for (let i = 0; i < n; i++){ const v = this.vu(); a[i] = (v % 2) ? -(v + 1) / 2 : v / 2; }
  else for (let i = 0; i < n; i++) a[i] = this.vu();
  return a;
};

/* tile -> {ox, oy, size, rects: {li: {...}}, vias, cells} ; coordinates absolute DBU (Int32 exact) */
function decodeTile(buf, header){
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const magic = String.fromCharCode(u8[0], u8[1], u8[2], u8[3]);
  if (magic !== 'OTT1') throw new Error('bad tile magic ' + magic);
  const ox = dv.getInt32(4, true), oy = dv.getInt32(8, true), size = dv.getUint32(12, true), nsec = dv.getUint16(16, true);
  let p = 20;
  const T = {ox, oy, size, rects: {}, vias: null, cells: null};
  for (let s = 0; s < nsec; s++){
    const type = u8[p], li = u8[p + 1], flags = dv.getUint16(p + 2, true), n = dv.getUint32(p + 4, true), nb = dv.getUint32(p + 8, true);
    p += 12;
    const R = new Reader(u8, p, p + nb);
    if (type === 1){
      const vert = flags & 1;
      const dmaj = R.col(n, 1), dmnr = R.col(n, 1), w = R.col(n, 0), h = R.col(n, 0), dnet = R.col(n, 1), kind = R.col(n, 0), clip = R.col(n, 0);
      const x0 = new Int32Array(n), y0 = new Int32Array(n), x1 = new Int32Array(n), y1 = new Int32Array(n), net = new Int32Array(n),
        K = new Uint8Array(n), C = new Uint8Array(n), id = new Int32Array(n).fill(-1);
      let maj = 0, mnr = 0, nt = 0;
      for (let i = 0; i < n; i++){
        maj += dmaj[i]; mnr = (i > 0 && dmaj[i] === 0) ? mnr + dmnr[i] : dmnr[i]; nt += dnet[i];
        const X = (vert ? maj : mnr) + ox, Y = (vert ? mnr : maj) + oy;
        x0[i] = X; y0[i] = Y; x1[i] = X + w[i]; y1[i] = Y + h[i]; net[i] = nt; K[i] = kind[i]; C[i] = clip[i];
      }
      for (let i = 0; i < n; i++) if (C[i]) id[i] = R.vu();
      T.rects[li] = {n, x0, y0, x1, y1, net, kind: K, clip: C, id};
    } else if (type === 2){
      const dy = R.col(n, 1), dx = R.col(n, 1), ty = R.col(n, 0), dnet = R.col(n, 1), kind = R.col(n, 0);
      const x = new Int32Array(n), y = new Int32Array(n), t = new Uint16Array(n), net = new Int32Array(n), K = new Uint8Array(n);
      let Y = 0, X = 0, nt = 0;
      for (let i = 0; i < n; i++){ Y += dy[i]; X = (i > 0 && dy[i] === 0) ? X + dx[i] : dx[i]; nt += dnet[i];
        x[i] = X + ox; y[i] = Y + oy; t[i] = ty[i]; net[i] = nt; K[i] = kind[i]; }
      T.vias = {n, x, y, type: t, net, kind: K};
    } else if (type === 3){
      const dy = R.col(n, 1), dx = R.col(n, 1), orient = R.col(n, 0), master = R.col(n, 0), dinst = R.col(n, 1), fl = R.col(n, 0);
      const x = new Int32Array(n), y = new Int32Array(n), o = new Uint8Array(n), m = new Uint16Array(n), inst = new Int32Array(n), F = new Uint8Array(n);
      let Y = 0, X = 0, I = 0, npin = 0;
      for (let i = 0; i < n; i++){ Y += dy[i]; X = (i > 0 && dy[i] === 0) ? X + dx[i] : dx[i]; I += dinst[i];
        x[i] = X + ox; y[i] = Y + oy; o[i] = orient[i]; m[i] = master[i]; inst[i] = I; F[i] = fl[i]; npin += header.masters[m[i]].pins.length; }
      const pinOff = new Int32Array(n + 1); for (let i = 0; i < n; i++) pinOff[i + 1] = pinOff[i] + header.masters[m[i]].pins.length;
      const dn = R.col(npin, 1), nets = new Int32Array(npin); let nt = 0; for (let i = 0; i < npin; i++){ nt += dn[i]; nets[i] = nt; }
      T.cells = {n, x, y, orient: o, master: m, inst, flags: F, pinOff, nets};
    }
    p += nb;
  }
  return T;
}

/* odb dbTransform orientation (R0 R90 R180 R270 MY MYR90 MX MXR90) */
function orient(code, x, y){
  switch (code){
    case 0: return [x, y]; case 1: return [-y, x]; case 2: return [-x, -y]; case 3: return [y, -x];
    case 4: return [-x, y]; case 5: return [-y, -x]; case 6: return [x, -y]; default: return [y, x];
  }
}

/* every shape of a tile, per layer, as flat lists: emit(li, x0, y0, x1, y1, net, kind, clip, id, src)
   (id: shape id of a clipped piece, the via type for a via box, -1 otherwise)
   src: 0 rect piece, 1 via box, 2 cell shape.  kinds: 0 wire 1 stripe 2 followpin 3 special 4 bterm pin 5 obstruction
   6 fill 7 macro pin 8 macro OBS 9 via (signal) 10 via (special) 11 cell pin 12 cell OBS */
function forEachShape(T, header, emit){
  for (const li in T.rects){ const r = T.rects[li], L = +li;
    for (let i = 0; i < r.n; i++) emit(L, r.x0[i], r.y0[i], r.x1[i], r.y1[i], r.net[i], r.kind[i], r.clip[i], r.id[i], 0); }
  if (T.vias){ const v = T.vias, VT = header.vias;
    for (let i = 0; i < v.n; i++){ const b = VT[v.type[i]].boxes, k = v.kind[i] ? 10 : 9;
      for (let j = 0; j < b.length; j++){ const q = b[j]; emit(q[0], v.x[i] + q[1], v.y[i] + q[2], v.x[i] + q[3], v.y[i] + q[4], v.net[i], k, 0, v.type[i], 1); } } }
  if (T.cells){ const c = T.cells, M = header.masters;
    for (let i = 0; i < c.n; i++){ const m = M[c.master[i]], bx = m.boxes, o = c.orient[i], X = c.x[i], Y = c.y[i];
      for (let j = 0; j < bx.length; j++){ const q = bx[j], a = orient(o, q[1], q[2]), b = orient(o, q[3], q[4]);
        const net = q[5] >= 0 ? c.nets[c.pinOff[i] + q[5]] : 0;
        emit(q[0], Math.min(a[0], b[0]) + X, Math.min(a[1], b[1]) + Y, Math.max(a[0], b[0]) + X, Math.max(a[1], b[1]) + Y, net, q[5] >= 0 ? 11 : 12, 0, -1, 2); } } }
}

/* order-independent rect hash, identical to lv_tile.rect_hash */
function hashAcc(){ return {h1: 0, h2: 0, n: 0}; }
function hashAdd(acc, l, x0, y0, x1, y1){
  let h1 = 0x9747b28c, h2 = 0x1b873593; const v = [l, x0, y0, x1, y1];
  for (let k = 0; k < 5; k++){ h1 = Math.imul((h1 ^ v[k]) >>> 0, 0x5bd1e995) >>> 0; h1 = (h1 ^ (h1 >>> 15)) >>> 0;
    h2 = Math.imul((h2 ^ v[k]) >>> 0, 0x85ebca6b) >>> 0; h2 = (h2 ^ (h2 >>> 13)) >>> 0; }
  h1 = (h1 ^ (h1 >>> 16)) >>> 0; h1 = Math.imul(h1, 0x85ebca6b) >>> 0; h1 = (h1 ^ (h1 >>> 13)) >>> 0;
  h2 = (h2 ^ (h2 >>> 16)) >>> 0; h2 = Math.imul(h2, 0xc2b2ae35) >>> 0; h2 = (h2 ^ (h2 >>> 16)) >>> 0;
  acc.h1 = (acc.h1 + h1) >>> 0; acc.h2 = (acc.h2 + h2) >>> 0; acc.n++;
}

/* raster node: {layers: [li...], size, planes: [Uint8Array]} (horizontal delta filter undone) */
function decodeRaster(buf){
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const nl = dv.getUint16(4, true), R = dv.getUint16(6, true);
  const layers = Array.from(u8.subarray(8, 8 + nl));
  let p = 8 + nl; const planes = [];
  for (let k = 0; k < nl; k++){
    const a = new Uint8Array(u8.subarray(p, p + R * R)); p += R * R;
    for (let y = 0; y < R; y++){ const o = y * R; for (let x = 1; x < R; x++) a[o + x] = (a[o + x] + a[o + x - 1]) & 0xff; }
    planes.push(a);
  }
  return {layers, size: R, planes};
}
function decodeCong(buf){
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const n = dv.getUint16(4, true), gx = dv.getUint16(6, true), gy = dv.getUint16(8, true), bin = dv.getUint32(10, true);
  const layers = Array.from(u8.subarray(14, 14 + n)); let p = 14 + n; const planes = [];
  for (let k = 0; k < n; k++){ planes.push(u8.subarray(p, p + gx * gy)); p += gx * gy; }
  return {layers, gx, gy, bin, planes};
}

const API = {decodeTile, forEachShape, orient, hashAcc, hashAdd, decodeRaster, decodeCong};
if (typeof module !== 'undefined' && module.exports) module.exports = API; else root.LVDecode = API;
})(typeof self !== 'undefined' ? self : this);

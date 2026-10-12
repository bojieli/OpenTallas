#!/usr/bin/env node
/* Geometry round-trip check of a layout-viewer pack: decode EVERY tile with the viewer's own decoder
   (tools/fleet_viz/explorer/element/lv_decode.js), re-join clipped pieces by shape id, expand vias and cells exactly as
   the viewer draws them, and compare per layer against the DB truth summary in the pack header (count, bbox,
   order-independent 2 x 32-bit hash of the canonical shape set written by lv_extract.py from OpenDB).
     node lv_verify.js <pack.lvp | store manifest .json> [--dump out.bin]     exit 0 = every layer identical
   --dump writes the decoded shape set (int32 layer,x0,y0,x1,y1 per rect, unsorted) for an exact list comparison. */
'use strict';
const fs = require('fs'), path = require('path'), zlib = require('zlib');
const D = require(process.env.LV_DECODE || path.join(__dirname, '../fleet_viz/explorer/element/lv_decode.js'));

const file = process.argv[2];
const dumpAt = process.argv.indexOf('--dump');
let index, blob;
if (file.endsWith('.json')){   // a published closure: manifest in <store>/elements/<el>/<job>.json, objects in <store>/objects
  const man = JSON.parse(fs.readFileSync(file)), store = path.resolve(path.dirname(file), '../..');
  index = man.objects;
  blob = k => zlib.brotliDecompressSync(fs.readFileSync(path.join(store, 'objects', index[k].slice(0, 2), index[k] + '.br')));
} else {
  const fd = fs.openSync(file, 'r');
  const readAt = (off, len) => { const b = Buffer.alloc(len); fs.readSync(fd, b, 0, len, off); return b; };
  const hd = readAt(0, 24);
  if (hd.toString('latin1', 0, 8) !== 'OTLVPK01') throw new Error('not a pack');
  const io = Number(hd.readBigUInt64LE(8)), il = Number(hd.readBigUInt64LE(16));
  index = JSON.parse(zlib.brotliDecompressSync(readAt(io, il)).toString());
  blob = k => zlib.brotliDecompressSync(readAt(index[k][0], index[k][1]));
}
const t0 = Date.now();
const header = JSON.parse(blob('header').toString());
const nl = header.layers.length;
const acc = Array.from({length: nl}, () => Object.assign(D.hashAcc(), {bb: [Infinity, Infinity, -Infinity, -Infinity]}));
const pieces = new Map();   // (li, id) -> [x0, y0, x1, y1]
let ntile = 0, npiece = 0;
const dump = dumpAt > 0 ? {chunks: [], cur: new Int32Array(5 << 20), n: 0} : null;   // chunked: tens of millions of shapes
function add(li, x0, y0, x1, y1){
  const a = acc[li]; D.hashAdd(a, li, x0, y0, x1, y1);
  if (x0 < a.bb[0]) a.bb[0] = x0; if (y0 < a.bb[1]) a.bb[1] = y0; if (x1 > a.bb[2]) a.bb[2] = x1; if (y1 > a.bb[3]) a.bb[3] = y1;
  if (dump){ if (dump.n === dump.cur.length){ dump.chunks.push(dump.cur); dump.cur = new Int32Array(5 << 20); dump.n = 0; }
    const c = dump.cur, k = dump.n; c[k] = li; c[k + 1] = x0; c[k + 2] = y0; c[k + 3] = x1; c[k + 4] = y1; dump.n += 5; }
}
for (const k of Object.keys(index)){
  if (!k.startsWith('t/')) continue;
  const T = D.decodeTile(blob(k), header); ntile++;   // one section per blob
  D.forEachShape(T, header, (li, x0, y0, x1, y1, net, kind, clip, id) => {
    if (clip){ npiece++; const key = li * 2 ** 32 + id, p = pieces.get(key);
      if (p){ p[0] = Math.min(p[0], x0); p[1] = Math.min(p[1], y0); p[2] = Math.max(p[2], x1); p[3] = Math.max(p[3], y1); }
      else pieces.set(key, [x0, y0, x1, y1, li]); }
    else add(li, x0, y0, x1, y1);
  });
}
for (const p of pieces.values()) add(p[4], p[0], p[1], p[2], p[3]);
let ok = true; const rows = [];
for (let li = 0; li < nl; li++){
  const t = (header.truth || [])[li] || {n: 0, bbox: null, h: [0, 0]}, a = acc[li];
  const bb = a.n ? a.bb : null;
  const same = a.n === t.n && a.h1 === t.h[0] && a.h2 === t.h[1] && JSON.stringify(bb) === JSON.stringify(t.bbox);
  if (!same) ok = false;
  if (a.n || t.n) rows.push({layer: header.layers[li].name, decoded: a.n, db: t.n, hash: [a.h1, a.h2].map(v => v.toString(16)).join(':'), match: same});
}
const out = {schema: 'opentallas.layout_viewer.roundtrip.v1', element: header.element, db: header.db, tiles: ntile, clipped_pieces: npiece,
  joined_shapes: pieces.size, shapes: acc.reduce((s, a) => s + a.n, 0), db_shapes: (header.truth || []).reduce((s, t) => s + t.n, 0),
  layers: rows, verdict: ok ? 'IDENTICAL' : 'MISMATCH', seconds: (Date.now() - t0) / 1000};
console.log(JSON.stringify(out, null, 1));
if (dump){ const fd2 = fs.openSync(process.argv[dumpAt + 1], 'w');
  for (const c of dump.chunks) fs.writeSync(fd2, Buffer.from(c.buffer));
  fs.writeSync(fd2, Buffer.from(dump.cur.buffer, 0, dump.n * 4)); fs.closeSync(fd2); }
process.exit(ok ? 0 : 1);

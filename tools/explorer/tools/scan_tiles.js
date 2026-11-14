#!/usr/bin/env node
/* Tile decode scan: runs the viewer's own tile worker (tools/fleet_viz/explorer/element/lv_worker.js + lv_decode.js)
   over EVERY tile of a layout pack, at both via-array detail levels (the two "zoom levels" of exact geometry), straight
   from the store on disk.  A tile counts as failed when the worker reports an error, an object is missing or empty,
   or the decoded shape count is zero where the header says the tile has shapes.

     node scan_tiles.js <LV_STORE> <node id> [<node id> ...]        one JSON line per pack on stdout
*/
'use strict';
const fs = require('fs'), path = require('path'), zlib = require('zlib'), vm = require('vm');
const ENG = process.env.SCAN_ENGINE || path.resolve(__dirname, '..', '..', 'fleet_viz', 'explorer', 'element');
const STORE = process.argv[2], NODES = process.argv.slice(3);
const obj = (h) => path.join(STORE, 'objects', h.slice(0, 2), h + '.br');
const readObj = (h) => zlib.brotliDecompressSync(fs.readFileSync(obj(h)));

function makeWorker() {
  const out = [];
  const self = { postMessage: (m) => out.push(m), performance: { now: () => Date.now() } };
  self.self = self;
  self.importScripts = (u) => vm.runInContext(fs.readFileSync(path.join(ENG, path.basename(u)), 'utf8'), ctx, { filename: path.basename(u) });
  self.fetch = async (url) => {   // url = "obj:<hash>"
    const h = String(url).slice(4);
    if (!h || !fs.existsSync(obj(h))) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
    const b = readObj(h);
    return { ok: true, status: 200, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) };
  };
  for (const k of ['Uint8Array', 'Uint16Array', 'Int16Array', 'Int32Array', 'Uint32Array', 'Float32Array', 'Float64Array', 'Uint8ClampedArray', 'DataView', 'ArrayBuffer', 'Map', 'Set', 'Math', 'JSON', 'Promise', 'Array', 'Object', 'String', 'Number', 'Error', 'console']) self[k] = global[k];
  const ctx = vm.createContext(self);
  vm.runInContext(fs.readFileSync(path.join(ENG, 'lv_worker.js'), 'utf8'), ctx, { filename: 'lv_worker.js' });
  return { self, out, ctx };
}

async function scan(node) {
  const res = { node, tiles: 0, runs: 0, failed: 0, errors: {}, missing_objects: 0, shapes: 0, examples: [] };
  const fail = (k, why) => { res.failed++; const key = why.replace(/[0-9a-f]{16,}/g, '<hash>').slice(0, 120); res.errors[key] = (res.errors[key] || 0) + 1; if (res.examples.length < 5) res.examples.push(k + ': ' + why.slice(0, 160)); };
  let ix, man, H;
  try {
    ix = JSON.parse(fs.readFileSync(path.join(STORE, 'elements', node, 'index.json'), 'utf8'));
    man = JSON.parse(fs.readFileSync(path.join(STORE, 'elements', node, ix.latest + '.json'), 'utf8'));
    H = JSON.parse(readObj(man.objects.header).toString('utf8'));
  } catch (e) { res.error = 'pack not readable: ' + e.message; return res; }
  res.job = ix.latest; res.overview_only = !!H.overview_only;
  if (H.overview_only) return res;
  const W = makeWorker();
  await W.self.onmessage({ data: { op: 'init', pack: node, header: H } });
  for (const t of H.grid.tiles || []) {
    const k = t.x + '_' + t.y; res.tiles++;
    const parts = (t.s || []).map((s) => ({ name: s, url: 'obj:' + (man.objects['t/' + k + '/' + s] || '') }));
    const miss = parts.filter((p) => p.url === 'obj:' || !fs.existsSync(obj(p.url.slice(4))));
    if (miss.length) { res.missing_objects += miss.length; res.runs++; fail(k, 'tile section missing in the store: ' + miss.map((p) => p.name).join(',')); continue; }
    if (!parts.length) continue;
    const expect = (t.n || []).reduce((a, b) => a + b, 0) + (t.v || 0) + (t.c || 0);
    for (const arrDetail of [false, true]) {
      W.out.length = 0; res.runs++;
      try { await W.self.onmessage({ data: { op: 'tile', pack: node, key: k, parts, phys: true, arrDetail } }); } catch (e) { fail(k, 'worker threw: ' + (e && e.message || e)); continue; }
      const m = W.out[W.out.length - 1];
      if (!m) fail(k, 'worker gave no answer');
      else if (m.op === 'error') fail(k, 'decode error: ' + m.error);
      else if (expect > 0 && !(m.n > 0)) fail(k, 'decoded 0 shapes, header counts ' + expect);
      else if (arrDetail) res.shapes += m.n;
    }
  }
  return res;
}
(async () => { for (const n of NODES) { let r; try { r = await scan(n); } catch (e) { r = { node: n, error: String(e && e.stack || e) }; } console.log(JSON.stringify(r)); } })();

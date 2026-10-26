// Data-flow link model (opentallas.dataflow.links.v1, written by tools/fleet_viz/dataflow_links.py).
// One record per die revision: blocks (rectangles) + links (driver/sinks, bits, hops, stages, length, crossings).
// Everything here is derived from the record; a field the record does not carry stays unknown (NaN / -1 / null).

export const STATUS = [
  { id: 'ok', label: 'within reach', color: '#3ccf7e' },
  { id: 'relay', label: 'relayed / needs relay', color: '#f2b134' },
  { id: 'over', label: 'hop beyond reach', color: '#ff5c5c' },
  { id: 'unknown', label: 'unplaced', color: '#6b7894' },
];
export const BYPASS_COLOR = '#c58cff';
export const DATA_BASE = '/explorer/dataflow/data/';

export const fmtBits = (b) => !Number.isFinite(b) ? 'width unknown' : b >= 1e6 ? (b / 1e6).toFixed(2) + ' Mbit' : b >= 1e4 ? (b / 1e3).toFixed(1) + ' kbit' : Math.round(b).toLocaleString() + ' bit';
export const fmtUm = (u) => !Number.isFinite(u) ? 'unknown' : u >= 1e4 ? (u / 1e3).toFixed(2) + ' mm' : Math.round(u).toLocaleString() + ' µm';
export const fmtBitUm = (v) => !Number.isFinite(v) ? 'unknown' : v >= 1e9 ? (v / 1e9).toFixed(2) + ' Gbit·µm' : v >= 1e6 ? (v / 1e6).toFixed(2) + ' Mbit·µm' : v >= 1e3 ? (v / 1e3).toFixed(1) + ' kbit·µm' : Math.round(v) + ' bit·µm';
export const widthPx = (bits) => 0.7 + Math.log2(Math.max(1, Number.isFinite(bits) ? bits : 1)) * 0.42;

const jsonCache = new Map();
export async function fetchJSON(url) {
  if (!jsonCache.has(url)) jsonCache.set(url, fetch(url, { cache: 'no-store' }).then((r) => { if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`); return r.json(); }));
  try { return await jsonCache.get(url); } catch (e) { jsonCache.delete(url); throw e; }
}
export const loadIndex = (base = DATA_BASE) => fetchJSON(base + 'index.json');
const modelCache = new Map();
export function loadModel(row, base = DATA_BASE) {
  const url = base + row.file;
  if (!modelCache.has(url)) modelCache.set(url, fetchJSON(url).then(buildModel).catch((e) => { modelCache.delete(url); throw e; }));
  return modelCache.get(url);
}

/** Columnar, typed view of a links record plus derived per-link status and a segment list. */
export function buildModel(rec) {
  const B = rec.blocks, nb = B.name.length, L = rec.links, nl = L.length;
  const reach = rec.reach_um || 500;
  const m = {
    rec, reach, nb, nl, W: rec.outline[0], H: rec.outline[1], explicit: !!rec.stages_explicit,
    bx: Float64Array.from(B.x), by: Float64Array.from(B.y), bw: Float64Array.from(B.w), bh: Float64Array.from(B.h),
    reg: Uint8Array.from(B.reg), bname: B.name, bmaster: B.master, bkind: B.kind, bgroup: B.group,
    bits: new Float64Array(nl), len: new Float64Array(nl), mh: new Float64Array(nl), stages: new Int32Array(nl),
    bitum: new Float64Array(nl), cross: new Int32Array(nl), directed: new Uint8Array(nl), status: new Uint8Array(nl),
    ends: new Array(nl), bbox: new Float32Array(nl * 4), segStart: new Int32Array(nl + 1),
  };
  const segs = [];
  for (let i = 0; i < nl; i++) {
    const l = L[i];
    m.bits[i] = l.b > 0 ? l.b : NaN; m.len[i] = l.L ?? NaN; m.mh[i] = l.mh ?? NaN;
    m.stages[i] = l.s ?? -1; m.bitum[i] = l.bu ?? NaN; m.cross[i] = l.x || 0; m.directed[i] = l.d;
    m.ends[i] = l.e.map((e) => e[0]);
    m.segStart[i] = segs.length / 5;
    if (l.h) for (const h of l.h) segs.push(h[0], h[1], h[2], h[3], h[4] || 0);
    else {
      const d = l.e[0];
      if (d && d[2] != null) for (const e of l.e.slice(1)) if (e[2] != null) segs.push(d[2], d[3], e[2], e[3], l.b || 0);
    }
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (let k = m.segStart[i] * 5; k < segs.length; k += 5) {
      x0 = Math.min(x0, segs[k], segs[k + 2]); x1 = Math.max(x1, segs[k], segs[k + 2]);
      y0 = Math.min(y0, segs[k + 1], segs[k + 3]); y1 = Math.max(y1, segs[k + 1], segs[k + 3]);
    }
    m.bbox.set([x0, y0, x1, y1], i * 4);
    m.status[i] = classify(m, i, l);
  }
  m.segStart[nl] = segs.length / 5;
  // flight lines (driver end -> every sink end): the zoomed-out, aggregated picture of where data goes
  const fl = [], fStart = new Int32Array(nl + 1);
  for (let i = 0; i < nl; i++) {
    fStart[i] = fl.length / 5;
    const e = L[i].e, d = e[0];
    if (d && d[2] != null) for (const x of e.slice(1)) if (x[2] != null) fl.push(d[2], d[3], x[2], x[3], L[i].b || 0);
  }
  fStart[nl] = fl.length / 5; m.fseg = Float32Array.from(fl); m.fStart = fStart;
  m.seg = Float32Array.from(segs);
  m.segLink = new Int32Array(m.seg.length / 5);
  for (let i = 0; i < nl; i++) for (let s = m.segStart[i]; s < m.segStart[i + 1]; s++) m.segLink[s] = i;
  m.link = (i) => L[i];
  m.blockIndex = new Map(B.name.map((n, i) => [n, i]));
  m.incident = null;   // block -> links, built lazily
  return m;
}

/** Reach verdict. Explicit register plans: a hop > reach is red; relayed chains amber; direct within reach green.
 *  Records without placed registers: length > reach means relays are needed (amber, count unknown). */
function classify(m, i, l) {
  if (!Number.isFinite(m.len[i]) && !Number.isFinite(m.mh[i])) return 3;
  const hop = Number.isFinite(m.mh[i]) ? m.mh[i] : m.len[i];
  if (m.explicit) { if (hop > m.reach) return 2; return m.stages[i] > 0 ? 1 : 0; }
  return (Number.isFinite(m.len[i]) ? m.len[i] : hop) > m.reach ? 1 : 0;
}

export function statusText(m, i) {
  const s = m.status[i], L = m.len[i], hop = m.mh[i];
  if (s === 3) return 'unplaced: at least one end has no placement in this revision';
  if (m.explicit) {
    if (s === 2) return `a single hop of ${fmtUm(hop)} exceeds the ${m.reach} µm reach`;
    if (s === 1) return `relayed through ${m.stages[i]} register stage${m.stages[i] === 1 ? '' : 's'}; longest hop ${fmtUm(hop)}`;
    return `direct, ${fmtUm(L)} ≤ ${m.reach} µm`;
  }
  if (s === 1) return `${fmtUm(L)} > ${m.reach} µm: needs ≥ ${Math.ceil(L / m.reach) - 1} relay stage(s); stages not in this source`;
  return `${fmtUm(L)} ≤ ${m.reach} µm (lower bound where pins are unknown)`;
}

export function incident(m, b) {
  if (!m.incident) {
    m.incident = new Map();
    for (let i = 0; i < m.nl; i++) for (const e of m.ends[i]) if (e >= 0) { let a = m.incident.get(e); if (!a) m.incident.set(e, a = []); a.push(i); }
  }
  return m.incident.get(b) || [];
}

export function linkLabel(m, i) {
  const l = m.rec.links[i], nm = (b) => b >= 0 ? m.bname[b] : '?';
  const d = l.e[0], rest = l.e.slice(1);
  const arrow = m.directed[i] ? ' → ' : ' — ';
  return `${nm(d[0])}${d[1] ? '.' + d[1] : ''}${arrow}${rest.length > 2 ? `${rest.length} ends` : rest.map((e) => nm(e[0]) + (e[1] ? '.' + e[1] : '')).join(', ')}`;
}

// ------------------------------------------------------------------------------------------------ spatial index
export function segmentGrid(m, cell = 0) {
  if (m._sgrid) return m._sgrid;
  cell = cell || Math.max(100, Math.max(m.W, m.H) / 160);
  const nx = Math.ceil(m.W / cell) + 1, ny = Math.ceil(m.H / cell) + 1, cells = new Map();
  const S = m.seg;
  for (let s = 0; s < m.segLink.length; s++) {
    const x0 = Math.min(S[s * 5], S[s * 5 + 2]), x1 = Math.max(S[s * 5], S[s * 5 + 2]);
    const y0 = Math.min(S[s * 5 + 1], S[s * 5 + 3]), y1 = Math.max(S[s * 5 + 1], S[s * 5 + 3]);
    const gx0 = Math.max(0, Math.floor(x0 / cell)), gx1 = Math.min(nx - 1, Math.floor(x1 / cell));
    const gy0 = Math.max(0, Math.floor(y0 / cell)), gy1 = Math.min(ny - 1, Math.floor(y1 / cell));
    if ((gx1 - gx0 + 1) * (gy1 - gy0 + 1) > 400) {   // long diagonal: walk it
      const n = Math.ceil(Math.hypot(x1 - x0, y1 - y0) / (cell / 2)) + 1;
      const seen = new Set();
      for (let k = 0; k <= n; k++) {
        const t = k / n, gx = Math.floor((S[s * 5] + (S[s * 5 + 2] - S[s * 5]) * t) / cell), gy = Math.floor((S[s * 5 + 1] + (S[s * 5 + 3] - S[s * 5 + 1]) * t) / cell);
        const key = gy * nx + gx; if (seen.has(key)) continue; seen.add(key);
        let a = cells.get(key); if (!a) cells.set(key, a = []); a.push(s);
      }
      continue;
    }
    for (let gx = gx0; gx <= gx1; gx++) for (let gy = gy0; gy <= gy1; gy++) {
      const key = gy * nx + gx; let a = cells.get(key); if (!a) cells.set(key, a = []); a.push(s);
    }
  }
  return (m._sgrid = { cell, nx, ny, cells });
}

export function blockGrid(m) {
  if (m._bgrid) return m._bgrid;
  const cell = Math.max(100, Math.max(m.W, m.H) / 120), nx = Math.ceil(m.W / cell) + 1, cells = new Map();
  for (let b = 0; b < m.nb; b++) {
    const gx0 = Math.floor(m.bx[b] / cell), gx1 = Math.floor((m.bx[b] + m.bw[b]) / cell);
    const gy0 = Math.floor(m.by[b] / cell), gy1 = Math.floor((m.by[b] + m.bh[b]) / cell);
    for (let gx = gx0; gx <= gx1; gx++) for (let gy = gy0; gy <= gy1; gy++) {
      const key = gy * nx + gx; let a = cells.get(key); if (!a) cells.set(key, a = []); a.push(b);
    }
  }
  return (m._bgrid = { cell, nx, cells });
}

export function blockAt(m, x, y) {
  const g = blockGrid(m), a = g.cells.get(Math.floor(y / g.cell) * g.nx + Math.floor(x / g.cell)) || [];
  let best = -1, area = Infinity;
  for (const b of a) {
    if (x < m.bx[b] || x > m.bx[b] + m.bw[b] || y < m.by[b] || y > m.by[b] + m.bh[b]) continue;
    const ar = m.bw[b] * m.bh[b] * (m.reg[b] ? 50 : 1);
    if (ar < area) { area = ar; best = b; }
  }
  return best;
}

// ------------------------------------------------------------------------------------------------ cut congestion
/** Bits crossing every cut window for a set of links: L-shaped route per segment (x first, then y), each link counted
 *  once per window (as tools/s81/chain_guide_cut_unique.py counts each chain once). ratio = bits / tracks per window. */
export function cutMap(m, links) {
  const C = m.rec.cut, Wn = C.window_um, nx = Math.ceil(m.W / Wn), ny = Math.ceil(m.H / Wn);
  const v = new Float64Array((nx + 1) * ny), hz = new Float64Array((ny + 1) * nx);  // v: cut x=k*W, window j; hz: cut y=k*W, window i
  const S = m.seg, seen = new Set(), contrib = new Map();
  const list = links || Array.from({ length: m.nl }, (_, i) => i);
  for (const i of list) {
    const bits = m.bits[i]; if (!Number.isFinite(bits)) continue;
    seen.clear();
    for (let s = m.segStart[i]; s < m.segStart[i + 1]; s++) {
      const x1 = S[s * 5], y1 = S[s * 5 + 1], x2 = S[s * 5 + 2], y2 = S[s * 5 + 3], b = S[s * 5 + 4] || bits;
      const j = Math.min(ny - 1, Math.max(0, Math.floor(y1 / Wn)));
      for (let k = Math.floor(Math.min(x1, x2) / Wn) + 1; k * Wn < Math.max(x1, x2); k++) {
        const key = k * ny + j; if (seen.has(key)) continue; seen.add(key); v[key] += b;
      }
      const ii = Math.min(nx - 1, Math.max(0, Math.floor(x2 / Wn)));
      for (let k = Math.floor(Math.min(y1, y2) / Wn) + 1; k * Wn < Math.max(y1, y2); k++) {
        const key = -1 - (k * nx + ii); if (seen.has(key)) continue; seen.add(key); hz[k * nx + ii] += b;
      }
    }
  }
  const cap = C.tracks_per_window;
  let max = 0, over = 0, top = [];
  for (let k = 0; k < v.length; k++) if (v[k]) { const r = v[k] / cap; if (r > max) max = r; if (r > C.limit) over++; top.push([r, 'x', Math.floor(k / ny), k % ny]); }
  for (let k = 0; k < hz.length; k++) if (hz[k]) { const r = hz[k] / cap; if (r > max) max = r; if (r > C.limit) over++; top.push([r, 'y', Math.floor(k / nx), k % nx]); }
  top.sort((a, b) => b[0] - a[0]); top = top.slice(0, 8);
  return { Wn, nx, ny, v, hz, cap, limit: C.limit, max, over, top, n: list.length };
}

/** Largest cut ratio among the windows each link crosses (static map of all links). */
export function linkCutRatio(m, cm) {
  if (m._lcut) return m._lcut;
  const out = new Float32Array(m.nl), S = m.seg, { Wn, nx, ny, v, hz, cap } = cm;
  for (let i = 0; i < m.nl; i++) {
    let mx = 0;
    for (let s = m.segStart[i]; s < m.segStart[i + 1]; s++) {
      const x1 = S[s * 5], y1 = S[s * 5 + 1], x2 = S[s * 5 + 2], y2 = S[s * 5 + 3];
      const j = Math.min(ny - 1, Math.max(0, Math.floor(y1 / Wn)));
      for (let k = Math.floor(Math.min(x1, x2) / Wn) + 1; k * Wn < Math.max(x1, x2); k++) mx = Math.max(mx, v[k * ny + j] / cap);
      const ii = Math.min(nx - 1, Math.max(0, Math.floor(x2 / Wn)));
      for (let k = Math.floor(Math.min(y1, y2) / Wn) + 1; k * Wn < Math.max(y1, y2); k++) mx = Math.max(mx, hz[k * nx + ii] / cap);
    }
    out[i] = mx;
  }
  return (m._lcut = out);
}

export function cutLabel(c, Wn) {
  const mm = (k) => (k * Wn / 1000).toFixed(2);
  return c[1] === 'x' ? `cut x = ${mm(c[2])} mm, y ${mm(c[3])}–${mm(c[3] + 1)} mm` : `cut y = ${mm(c[2])} mm, x ${mm(c[3])}–${mm(c[3] + 1)} mm`;
}

// ------------------------------------------------------------------------------------------------ token mapping
const globs = new Map();
function glob(p) { if (!globs.has(p)) globs.set(p, new RegExp('^' + p.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$')); return globs.get(p); }

/** Token operators -> die blocks. A node maps through its own instance globs / element masters when it lists any,
 *  else through its class. Each distinct mapping is one key (bit); blocks carry the OR of the keys that claim them. */
export function tokenMapping(m, data) {
  const classes = new Map(data.classes.map((c) => [c.id, c]));
  const keyOf = new Map(), keys = [], nodeKey = new Map();
  for (const n of data.nodes) {
    const c = classes.get(n.cls) || {};
    const ins = n.instances?.length ? n.instances : c.instances || [], els = n.elements?.length ? n.elements : c.elements || [];
    const k = (n.instances?.length || n.elements?.length) ? `${n.cls}|${ins.join(',')}|${els.join(',')}` : `cls:${n.cls}`;
    if (!keyOf.has(k)) { keyOf.set(k, keys.length); keys.push({ key: k, cls: n.cls, ins, els, blocks: 0 }); }
    nodeKey.set(n.id, keyOf.get(k));
  }
  const nk = Math.min(keys.length, 31), bmask = new Int32Array(m.nb);
  keys.forEach((k, ki) => {
    if (ki >= 31) return;
    const re = k.ins.map(glob), els = new Set(k.els);
    for (let b = 0; b < m.nb; b++) if ((m.bmaster[b] && els.has(m.bmaster[b])) || re.some((r) => r.test(m.bname[b]))) { bmask[b] |= 1 << ki; k.blocks++; }
  });
  // per link: driver mask, union of sink masks, per-end masks for undirected links
  const dmask = new Int32Array(m.nl), smask = new Int32Array(m.nl);
  for (let i = 0; i < m.nl; i++) {
    const e = m.ends[i];
    dmask[i] = e[0] >= 0 ? bmask[e[0]] : 0;
    let s = 0; for (let k = 1; k < e.length; k++) if (e[k] >= 0) s |= bmask[e[k]];
    smask[i] = s;
  }
  const clsCycles = {};
  for (const n of data.nodes) clsCycles[n.cls] = (clsCycles[n.cls] || 0) + (n.cycles || 0);
  const covered = keys.filter((k) => k.blocks > 0);
  const tot = Object.values(clsCycles).reduce((a, b) => a + b, 0) || 1;
  const coveredCycles = data.nodes.reduce((a, n) => a + (keys[nodeKey.get(n.id)].blocks > 0 ? n.cycles || 0 : 0), 0);
  return { keys, nk, nodeKey, bmask, dmask, smask, coverage: coveredCycles / tot, unmapped: keys.filter((k) => !k.blocks).map((k) => k.cls),
    mappedLinks: (() => { let c = 0; for (let i = 0; i < m.nl; i++) if (dmask[i] && smask[i]) c++; return c; })() };
}

export function linkActive(m, map, i, A) {
  const d = map.dmask[i] & A, s = map.smask[i] & A;
  if (m.directed[i]) return d !== 0 && s !== 0;
  if (!d && !s) return false;
  const e = m.ends[i]; let n = 0;
  for (const b of e) if (b >= 0 && (map.bmask[b] & A)) if (++n >= 2) return true;
  return false;
}

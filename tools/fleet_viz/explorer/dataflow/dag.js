// Logical view: the operators of one stage as a left-to-right DAG in execution order (layered, barycentre-ordered to
// cut crossings). Edge thickness ∝ log2 of the physical bits between the two operators' blocks on this die; colour =
// worst reach verdict of those links; parallel physical links are bundled into the one edge with a count.
import { STATUS, fmtBits, widthPx } from './model.js';

const NS = 'http://www.w3.org/2000/svg';
const el = (tag, a = {}, parent) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(a)) e.setAttribute(k, v); if (parent) parent.append(e); return e; };

/** physical links between two token mapping keys (driver key -> sink key; undirected links count both ways) */
export function pairIndex(m, map) {
  if (map._pairs) return map._pairs;
  const pairs = new Map();
  const add = (a, b, i) => { const k = a * 32 + b; let p = pairs.get(k); if (!p) pairs.set(k, p = []); p.push(i); };
  for (let i = 0; i < m.nl; i++) {
    const d = map.dmask[i], s = map.smask[i]; if (!d || !s) continue;
    for (let a = 0; a < map.nk; a++) if (d & (1 << a)) for (let b = 0; b < map.nk; b++) if (s & (1 << b)) { add(a, b, i); if (!m.directed[i] && a !== b) add(b, a, i); }
  }
  return (map._pairs = pairs);
}

export function mountDag(host, { onEdge = () => {}, onNode = () => {}, colorOf = () => '#8a97b8' } = {}) {
  host.classList.add('df-dag');
  let state = null, selKey = null;
  function render(data, groupId, m, map) {
    state = { data, groupId, m, map };
    host.replaceChildren();
    const g = data.groups.find((x) => x.id === groupId);
    if (!g || !m || !map) { host.textContent = 'Select a stage to see its operators.'; return; }
    let nodes = data.nodes.filter((n) => n.group === groupId).sort((a, b) => a.start - b.start || a.end - b.end);
    const truncated = nodes.length > 160; if (truncated) nodes = nodes.slice(0, 160);
    const ids = new Set(nodes.map((n) => n.id)), byId = new Map(nodes.map((n) => [n.id, n]));
    const seen = new Set(), edges = [];
    for (const e of data.edges) {
      if (!ids.has(e.src) || !ids.has(e.dst) || e.src === e.dst) continue;
      const k = e.src + '>' + e.dst; if (seen.has(k)) continue; seen.add(k); edges.push(e);
    }
    // layers: longest path in start order (edges always go forward in time in these records)
    const layer = new Map(), succ = new Map(), pred = new Map();
    for (const n of nodes) { layer.set(n.id, 0); succ.set(n.id, []); pred.set(n.id, []); }
    for (const e of edges) { succ.get(e.src).push(e.dst); pred.get(e.dst).push(e.src); }
    for (const n of nodes) for (const p of pred.get(n.id)) layer.set(n.id, Math.max(layer.get(n.id), layer.get(p) + 1));
    const L = Math.max(0, ...layer.values()) + 1, cols = Array.from({ length: L }, () => []);
    for (const n of nodes) cols[layer.get(n.id)].push(n.id);
    const pos = new Map(); const idx = () => cols.forEach((c) => c.forEach((id, k) => pos.set(id, k)));
    idx();
    for (let sweep = 0; sweep < 6; sweep++) {   // barycentre sweeps, forward then backward
      const fwd = sweep % 2 === 0, order = fwd ? cols.map((_, k) => k) : cols.map((_, k) => L - 1 - k);
      for (const k of order) {
        const nb = fwd ? pred : succ;
        const bc = (id) => { const a = nb.get(id); return a.length ? a.reduce((s, x) => s + pos.get(x), 0) / a.length : pos.get(id); };
        cols[k].sort((a, b) => bc(a) - bc(b)); cols[k].forEach((id, j) => pos.set(id, j));
      }
    }
    const NW = 148, NH = 30, CG = 64, RG = 14, maxRows = Math.max(...cols.map((c) => c.length));
    const W = L * (NW + CG) + 20, H = maxRows * (NH + RG) + 20;
    const svg = el('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `Operators of ${g.label} as a data-flow graph` });
    const xy = (id) => { const c = layer.get(id), r = pos.get(id), off = (maxRows - cols[c].length) * (NH + RG) / 2; return [10 + c * (NW + CG), 10 + off + r * (NH + RG)]; };
    const pairs = pairIndex(m, map), eg = el('g', {}, svg), ng = el('g', {}, svg);
    const info = [];
    for (const e of edges) {
      const a = byId.get(e.src), b = byId.get(e.dst), ka = map.nodeKey.get(a.id), kb = map.nodeKey.get(b.id);
      const ids2 = (ka < 31 && kb < 31 ? pairs.get(ka * 32 + kb) : null) || [];
      let bits = 0, worst = -1, widest = 0;
      for (const i of ids2) { const bt = m.bits[i]; if (Number.isFinite(bt)) { bits += bt; widest = Math.max(widest, bt); } if (m.status[i] !== 3) worst = Math.max(worst, m.status[i]); }
      const [x1, y1] = xy(e.src), [x2, y2] = xy(e.dst), sx = x1 + NW, sy = y1 + NH / 2, tx = x2, ty = y2 + NH / 2, mx = (sx + tx) / 2;
      const d = `M${sx},${sy} C${mx},${sy} ${mx},${ty} ${tx},${ty}`;
      const w = ids2.length ? Math.min(12, widthPx(bits)) : 1;
      const col = ids2.length ? STATUS[Math.max(0, worst)].color : '#4a5678';
      const hit = el('path', { d, fill: 'none', stroke: 'transparent', 'stroke-width': Math.max(10, w + 6), class: 'hit', tabindex: 0, role: 'button' }, eg);
      const p = el('path', { d, fill: 'none', stroke: col, 'stroke-width': w, 'stroke-opacity': 0.85, ...(ids2.length ? {} : { 'stroke-dasharray': '4 4' }) }, eg);
      const text = ids2.length
        ? `${a.label} → ${b.label}\n${ids2.length.toLocaleString()} physical link${ids2.length === 1 ? '' : 's'} between their blocks · ${fmtBits(bits)} total, widest ${fmtBits(widest)} · worst: ${STATUS[Math.max(0, worst)].label}${e.bytes ? `\ntoken edge: ${e.bytes.toLocaleString()} bytes` : ''}${e.link ? ` · ${e.link}` : ''}`
        : `${a.label} → ${b.label}\nno physical link between the blocks these operators map to on this die${e.link ? `\ntoken edge: ${e.link}` : ''}`;
      el('title', {}, hit).textContent = text;
      const key = e.src + '>' + e.dst;
      const pick = () => { selKey = key; mark(); onEdge({ ids: ids2, label: `${a.label} → ${b.label}`, text }); };
      hit.addEventListener('click', pick); hit.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(); } });
      info.push({ key, p, w });
      if (ids2.length > 1) { const t = el('text', { x: mx, y: (sy + ty) / 2 - 4, 'text-anchor': 'middle', class: 'cnt' }, eg); t.textContent = '×' + (ids2.length > 999 ? Math.round(ids2.length / 1000) + 'k' : ids2.length); }
    }
    for (const n of nodes) {
      const [x, y] = xy(n.id), gg = el('g', { transform: `translate(${x},${y})`, class: 'node', tabindex: 0, role: 'button' }, ng);
      el('rect', { width: NW, height: NH, rx: 6, fill: '#0b1020', stroke: colorOf(n.cls), 'stroke-width': n.critical ? 2 : 1 }, gg);
      el('rect', { width: 5, height: NH, rx: 2, fill: colorOf(n.cls) }, gg);
      const t = el('text', { x: 10, y: 13 }, gg); t.textContent = n.label.length > 22 ? n.label.slice(0, 21) + '…' : n.label;
      const t2 = el('text', { x: 10, y: 25, class: 'sub' }, gg); t2.textContent = `${n.cls} · ${Math.round(n.cycles).toLocaleString()} cyc`;
      el('title', {}, gg).textContent = `${n.label} (${n.cls})\n${Math.round(n.start).toLocaleString()}–${Math.round(n.end).toLocaleString()} cyc`;
      const pick = () => onNode(n);
      gg.addEventListener('click', pick); gg.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(); } });
    }
    function mark() { for (const e of info) { e.p.setAttribute('stroke-width', e.key === selKey ? e.w + 3 : e.w); e.p.setAttribute('stroke-opacity', selKey && e.key !== selKey ? 0.35 : 0.9); } }
    mark();
    const cap = document.createElement('div'); cap.className = 'df-dagcap';
    cap.textContent = `${g.label}: ${nodes.length} operators${truncated ? ' (first 160)' : ''}, ${edges.length} dependencies. Edge width = physical bits between the operators' blocks on this die (log scale); dashed = no physical link there.`;
    const scroll = document.createElement('div'); scroll.className = 'df-dagscroll'; scroll.append(svg);
    host.append(cap, scroll);
  }
  return { render, clear() { selKey = null; if (state) render(state.data, state.groupId, state.m, state.map); }, get group() { return state?.groupId; } };
}

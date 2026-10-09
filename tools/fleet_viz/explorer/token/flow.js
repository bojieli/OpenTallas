// (a) Flow graph: left -> right layered DAG of one token's path, critical path highlighted, node size ∝ cycles,
// and an animated token pulse driven by a shared Clock.
//   token scope: one box per stage/layer group (width ∝ cycles, filled by the element-class split), serpentine rows;
//   group scope: the group's operators as a layered DAG (circle area ∝ cycles), critical chain on the centre row.
import { P, svg, h, tip, detail, fmtCyc, fmtPct, CRIT, critAt, injectCSS, CSS, reducedMotion } from './core.js';

const FLOW_CSS = `
.tp-flow{position:relative;overflow-x:auto;overflow-y:hidden;border-radius:10px}
.tp-flow svg{display:block}
.tp-flow .gbox{cursor:pointer}
.tp-flow .gbox .frame{fill:none;stroke:#2a3a63;stroke-width:1}
.tp-flow .gbox.crit .frame{stroke:${CRIT};stroke-opacity:.55}
.tp-flow .gbox.on .frame{stroke:${CRIT};stroke-width:2.5;stroke-opacity:1}
.tp-flow .gbox:hover .frame{stroke:#e8eefc}
.tp-flow .glab{fill:#e8eefc!important;font-weight:600}
.tp-flow .gshare{fill:#8a97b8!important}
.tp-flow .link{fill:none;stroke:#2a3a63;stroke-width:1.5}
.tp-flow .link.crit{stroke:${CRIT};stroke-opacity:.5;stroke-width:2}
.tp-flow .link.on{stroke-opacity:1;stroke-width:3}
.tp-flow .nd{cursor:pointer}
.tp-flow .nd circle{stroke:#05070d;stroke-width:2}
.tp-flow .nd.crit circle.ring{fill:none;stroke:${CRIT};stroke-width:2}
.tp-flow .nd.par circle.body{fill-opacity:.45}
.tp-flow .nd.on circle.body{fill-opacity:1;filter:drop-shadow(0 0 6px ${CRIT})}
.tp-flow .nd:hover circle.ring,.tp-flow .nd.sel circle.ring{stroke:#e8eefc;stroke-width:3}
.tp-flow .pulse{fill:#fff;filter:drop-shadow(0 0 8px ${CRIT}) drop-shadow(0 0 3px #fff)}
.tp-flow .rowlab{fill:#4a5678!important}
`;

export function mountFlow(el, data, { clock, group = null, onDrill, onSelect } = {}) {
  injectCSS('tp-css', CSS); injectCSS('tp-flow-css', FLOW_CSS);
  const p = P(data);
  const root = h('div', { class: 'tp-flow' });
  el.replaceChildren(root);
  let api;
  const width = Math.max(320, el.clientWidth || 900);
  api = group ? drill(root, data, p, group, width, onSelect) : tokenLevel(root, data, p, width, onDrill);
  let off = null;
  if (clock) { off = clock.on((t) => api.at(t)); api.at(clock.t); }
  return { destroy() { off && off(); root.remove(); }, select: (id) => api.select && api.select(id) };
}

// ---------------------------------------------------------------- token scope: groups, serpentine
function tokenLevel(root, data, p, W, onDrill) {
  const G = data.groups.filter((g) => g.critical);
  const total = G.reduce((a, g) => a + g.cycles, 0);
  const pad = 14, gap = 10, BH = 38, rowGap = 40, minW = 26;
  let rows, k;
  for (let R = 1; R <= 12; R++) {
    k = (R * (W - 2 * pad) - G.length * gap) / total;
    rows = [[]]; let x = 0;
    for (const g of G) {
      const w = Math.max(minW, g.cycles * k);
      if (x + w > W - 2 * pad + 0.5 && rows[rows.length - 1].length) { rows.push([]); x = 0; }
      rows[rows.length - 1].push([g, w]); x += w + gap;
    }
    if (rows.length <= R) break;
  }
  const H = pad * 2 + rows.length * BH + (rows.length - 1) * rowGap + 18;
  const s = svg('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `${data.title}: token path by stage` }, root);
  const linkL = svg('g', {}, s), boxL = svg('g', {}, s), top = svg('g', {}, s);
  const pos = {};
  rows.forEach((row, ri) => {
    const y = pad + ri * (BH + rowGap);
    const ltr = ri % 2 === 0;
    let x = ltr ? pad : W - pad;
    for (const [g, w] of row) {
      const x0 = ltr ? x : x - w;
      pos[g.id] = { x0, y, w, ltr };
      x = ltr ? x + w + gap : x - w - gap;
    }
  });
  // links between consecutive groups (U-turn at row ends)
  const links = {};
  for (let i = 1; i < G.length; i++) {
    const a = pos[G[i - 1].id], b = pos[G[i].id];
    let d;
    const ay = a.y + BH / 2, by = b.y + BH / 2;
    if (a.y === b.y) {
      const ax = a.ltr ? a.x0 + a.w : a.x0, bx = b.ltr ? b.x0 : b.x0 + b.w;
      d = `M${ax},${ay}L${bx},${by}`;
    } else {
      const ax = a.ltr ? a.x0 + a.w : a.x0, bx = b.ltr ? b.x0 : b.x0 + b.w;
      const ex = a.ltr ? Math.max(ax, bx) + 8 : Math.min(ax, bx) - 8;
      d = `M${ax},${ay}C${ex},${ay} ${ex},${by} ${bx},${by}`;
    }
    links[G[i].id] = svg('path', { d, class: 'link crit' }, linkL);
  }
  const boxes = {};
  for (const g of G) {
    const { x0, y, w } = pos[g.id];
    const gg = svg('g', { class: 'gbox crit', tabindex: 0 }, boxL);
    let cx = x0;
    const parts = Object.entries(g.cls_cycles);
    const sum = parts.reduce((a, [, c]) => a + c, 0) || 1;
    for (const [c, cy] of parts) {
      const ww = Math.max(0, (cy / sum) * w - 1);
      if (ww > 0.2) svg('rect', { x: cx, y, width: ww, height: BH, fill: p.cls[c]?.color || '#555', rx: 2 }, gg);
      cx += (cy / sum) * w;
    }
    svg('rect', { x: x0 - 1, y: y - 1, width: w + 2, height: BH + 2, rx: 4, class: 'frame' }, gg);
    const lab = shortLabel(g);
    if (w > 46) {
      const t = svg('text', { x: x0 + 4, y: y + BH + 13, class: 'glab' }, gg); t.textContent = clip(lab, Math.floor((w + gap) / 6.6));
    }
    if (w > 54) { const t2 = svg('text', { x: x0 + 4, y: y + BH + 25, class: 'gshare' }, gg); t2.textContent = fmtPct(g.share); }
    gg.addEventListener('mousemove', (ev) => tip(groupTip(data, g), ev));
    gg.addEventListener('mouseleave', () => tip(null));
    gg.addEventListener('click', () => onDrill && onDrill(g.id));
    gg.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') onDrill && onDrill(g.id); });
    boxes[g.id] = gg;
  }
  const pulse = svg('circle', { r: 6, class: 'pulse' }, top);
  let cur = null;
  return {
    at(t) {
      const n = critAt(data, t);
      const g = p.groups[n.group];
      if (!g || !pos[g.id]) return;
      if (cur !== g.id) {
        if (cur) { boxes[cur]?.classList.remove('on'); links[cur]?.classList.remove('on'); }
        boxes[g.id].classList.add('on'); links[g.id]?.classList.add('on'); cur = g.id;
      }
      const { x0, y, w, ltr } = pos[g.id];
      const f = Math.min(1, Math.max(0, (t - g.start) / Math.max(1, g.end - g.start)));
      pulse.setAttribute('cx', ltr ? x0 + f * w : x0 + w - f * w);
      pulse.setAttribute('cy', y + BH / 2);
      pulse.style.display = reducedMotion() && !cur ? 'none' : '';
    },
  };
}

function shortLabel(g) { return g.label.replace(/^Stage (\d+): /, 'S$1 ').replace(/^Layer /, 'L'); }
function clip(s, n) { return s.length > n ? s.slice(0, Math.max(1, n - 1)) + '…' : s; }

function groupTip(data, g) {
  const p = P(data);
  const d = h('div', {}, h('div', { class: 'tp-dt' }, h('b', {}, g.label)),
    h('div', { class: 'tp-kv' }, h('span', {}, 'cycles'), h('b', {}, fmtCyc(g.cycles)), h('span', {}, 'share'), h('b', {}, fmtPct(g.share)),
      h('span', {}, 'operators'), h('b', {}, String(g.n_nodes))));
  const t = h('div', { class: 'tp-add' });
  for (const [c, cy] of Object.entries(g.cls_cycles)) t.append(h('div', {}, h('span', { class: 'tp-sw', style: `display:inline-block;margin-right:6px;background:${p.cls[c]?.color}` }), `${p.cls[c]?.label || c}: ${fmtCyc(cy)}`));
  d.append(t, h('div', { class: 'tp-dm' }, 'click to open the operators'));
  return d;
}

// ---------------------------------------------------------------- group scope: layered DAG of operators
function drill(root, data, p, gid, W, onSelect) {
  const nodes = (p.byGroup[gid] || []).slice().sort((a, b) => a.start - b.start || a.end - b.end);
  const inG = new Set(nodes.map((n) => n.id));
  const edges = data.edges.filter((e) => inG.has(e.src) && inG.has(e.dst));
  // rank: longest path from the group's sources; critical chain fixes the spine
  const rank = {};
  const ins = {};
  for (const e of edges) (ins[e.dst] ||= []).push(e.src);
  for (const n of nodes) rank[n.id] = Math.max(0, ...(ins[n.id] || []).map((s) => (rank[s] ?? 0) + 1));
  // nodes sorted by start are mostly topological; one relaxation pass for any stragglers
  for (let it = 0; it < 3; it++) for (const n of nodes) rank[n.id] = Math.max(0, ...(ins[n.id] || []).map((s) => (rank[s] ?? 0) + 1));
  // operators with no in-group input (e.g. a prefetch feeding the next layer) sit in the column of the critical
  // operator running when they start
  const critN = nodes.filter((n) => n.critical);
  for (const n of nodes) {
    if (n.critical || (ins[n.id] || []).length) continue;
    const c = critN.filter((m) => m.start <= n.start + 1e-9).pop() || critN[0];
    if (c) rank[n.id] = rank[c.id];
  }
  const cols = {};
  for (const n of nodes) (cols[rank[n.id]] ||= []).push(n);
  const maxR = Math.max(0, ...Object.keys(cols).map(Number));
  const maxC = Math.max(...nodes.map((n) => n.cycles), 1);
  const R = 24, colW = 64, pad = 30;
  const rad = (n) => Math.max(3.5, Math.sqrt(n.cycles / maxC) * R);
  const slots = Math.max(1, ...Object.values(cols).map((c) => c.filter((n) => !n.critical).length));
  const rowH = 2 * R + 26;
  const half = Math.ceil(slots / 2);
  const H = pad * 2 + (2 * half + 1) * rowH;
  const Wd = Math.max(W, pad * 2 + (maxR + 1) * colW);
  const s = svg('svg', { width: Wd, height: H, viewBox: `0 0 ${Wd} ${H}`, role: 'img', 'aria-label': `${p.groups[gid]?.label}: operator graph` }, root);
  const cy0 = pad + half * rowH + rowH / 2;
  const pos = {};
  for (const [r, list] of Object.entries(cols)) {
    const x = pad + Number(r) * colW + colW / 2;
    let k = 0;
    for (const n of list) {
      if (n.critical) pos[n.id] = { x, y: cy0 };
      else { const j = k++; const side = j % 2 === 0 ? -1 : 1; const lvl = Math.floor(j / 2) + 1; pos[n.id] = { x, y: cy0 + side * lvl * rowH }; }
    }
  }
  svg('text', { x: 6, y: cy0 - R - 8, class: 'rowlab' }, s).textContent = 'critical path';
  const eL = svg('g', {}, s), nL = svg('g', {}, s), top = svg('g', {}, s);
  const eEls = [];
  for (const e of edges) {
    const a = pos[e.src], b = pos[e.dst];
    if (!a || !b) continue;
    const mx = (a.x + b.x) / 2;
    const path = svg('path', { d: `M${a.x},${a.y}C${mx},${a.y} ${mx},${b.y} ${b.x},${b.y}`, class: 'link' + (e.critical ? ' crit' : '') }, eL);
    eEls.push([e, path]);
  }
  const els = {};
  let selected = null;
  for (const n of nodes) {
    const { x, y } = pos[n.id];
    const g = svg('g', { class: 'nd ' + (n.critical ? 'crit' : 'par'), tabindex: 0 }, nL);
    const r = rad(n);
    svg('circle', { cx: x, cy: y, r, fill: p.cls[n.cls]?.color || '#888', class: 'body' }, g);
    svg('circle', { cx: x, cy: y, r: r + 2.5, class: 'ring', fill: 'none', stroke: n.critical ? CRIT : 'none' }, g);
    if (n.critical) {
      const t = svg('text', { x, y: y + (Number(rank[n.id]) % 2 ? -R - 8 : R + 16), 'text-anchor': 'middle' }, g);
      t.textContent = clip(n.op.replace(/^attn\.|^ffn\./, ''), 12);
    }
    g.addEventListener('mousemove', (ev) => tip(detail(data, n, { links: false }), ev));
    g.addEventListener('mouseleave', () => tip(null));
    const pick = () => { sel(n.id); onSelect && onSelect(n); };
    g.addEventListener('click', pick);
    g.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') pick(); });
    els[n.id] = g;
  }
  function sel(id) { if (selected) els[selected]?.classList.remove('sel'); selected = id; els[id]?.classList.add('sel'); }
  const pulse = svg('circle', { r: 6, class: 'pulse' }, top);
  const crit = nodes.filter((n) => n.critical);
  let on = new Set();
  return {
    select: sel,
    at(t) {
      const now = new Set(nodes.filter((n) => n.start <= t && t < n.end + 1e-9).map((n) => n.id));
      for (const id of on) if (!now.has(id)) els[id]?.classList.remove('on');
      for (const id of now) if (!on.has(id)) els[id]?.classList.add('on');
      on = now;
      if (!crit.length) return;
      let i = crit.findIndex((n) => n.start <= t && t < n.end);
      if (i < 0) { pulse.style.display = 'none'; return; }
      pulse.style.display = '';
      const n = crit[i], nx = crit[i + 1] || n;
      const f = Math.min(1, Math.max(0, (t - n.start) / Math.max(1e-9, n.end - n.start)));
      const a = pos[n.id], b = pos[nx.id];
      pulse.setAttribute('cx', a.x + (b.x - a.x) * f); pulse.setAttribute('cy', a.y + (b.y - a.y) * f);
      for (const [e, path] of eEls) path.classList.toggle('on', e.src === n.id && e.dst === nx.id);
    },
  };
}

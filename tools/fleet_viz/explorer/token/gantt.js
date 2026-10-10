// (b) Swimlane timeline (Gantt) for one token: one lane per element class, a bar per operator, the critical chain
// drawn through the lanes, a group strip on top (click a group to zoom), a cursor for the shared Clock.
import { P, svg, h, tip, detail, fmtCyc, fmtUs, CRIT, injectCSS, CSS, CLK, PHASE, hatch } from './core.js';

const G_CSS = `
.tp-gantt{position:relative}
.tp-gantt svg{display:block;width:100%}
.tp-gantt .bar{cursor:pointer}
.tp-gantt .bar.par{fill-opacity:.42}
.tp-gantt .bar.crit{stroke:${CRIT};stroke-width:0}
.tp-gantt .bar.hl{stroke:#fff;stroke-width:1.5}
.tp-gantt .chain{fill:none;stroke:${CRIT};stroke-width:1.2;stroke-opacity:.8}
.tp-gantt .lane{fill:#0b1020}
.tp-gantt .lane.alt{fill:#0d1326}
.tp-gantt .lanelab{fill:#c3cbe0!important}
.tp-gantt .grp{cursor:pointer;fill:#111a33}
.tp-gantt .grp.alt{fill:#16213f}
.tp-gantt .grp:hover{fill:#24345e}
.tp-gantt .grplab{fill:#8a97b8!important;pointer-events:none}
.tp-gantt .cursor{stroke:#fff;stroke-width:1.5}
.tp-gantt .tick{stroke:#1b2540}
.tp-gantt .bar.hwp{stroke:#e8eefc;stroke-width:1;stroke-dasharray:3 2}
.tp-gantt .phlab{fill:#05070d!important;font-weight:700!important}
`;

export function mountGantt(el, data, { clock, range = null, onZoom, onSelect } = {}) {
  injectCSS('tp-css', CSS); injectCSS('tp-gantt-css', G_CSS);
  const p = P(data);
  const t0 = range ? range[0] : 0, t1 = range ? range[1] : data.totals.cycles;
  const W = Math.max(320, el.clientWidth || 900);
  const narrow = W < 640;
  const phases = (data.phases || []).filter((q) => q.end >= t0 && q.start <= t1);
  const pH = phases.length ? 18 : 0;
  const labW = narrow ? 0 : 190, padR = 12, laneH = 24, gH = 22 + pH, axH = 30;
  const used = data.classes.filter((c) => data.nodes.some((n) => n.cls === c.id && n.end >= t0 && n.start <= t1));
  const laneY = {};
  const lanePitch = laneH + (narrow ? 14 : 4);
  used.forEach((c, i) => { laneY[c.id] = gH + 6 + i * lanePitch + (narrow ? 14 : 0); });
  const H = gH + 6 + used.length * lanePitch + axH + (narrow ? 14 : 0);
  const x0 = labW + 4, x1 = W - padR;
  const k = (x1 - x0) / Math.max(1, t1 - t0);
  const X = (t) => x0 + (t - t0) * k;
  const root = h('div', { class: 'tp-gantt' });
  el.replaceChildren(root);
  const s = svg('svg', { viewBox: `0 0 ${W} ${H}`, height: H, role: 'img', 'aria-label': `${data.title}: one-token timeline by element class` }, root);
  // lanes
  used.forEach((c, i) => {
    const y = laneY[c.id];
    svg('rect', { x: x0, y: y - 2, width: x1 - x0, height: laneH + 4, class: 'lane' + (i % 2 ? ' alt' : '') }, s);
    const t = svg('text', narrow ? { x: x0 + 12, y: y - 4, class: 'lanelab' } : { x: 16, y: y + laneH / 2 + 4, class: 'lanelab' }, s);
    t.textContent = c.label.length > 26 && !narrow ? c.label.slice(0, 25) + '…' : c.label;
    svg('title', {}, t).textContent = c.label;
    svg('rect', { x: narrow ? x0 : 4, y: narrow ? y - 12 : y + laneH / 2 - 4, width: 8, height: 8, rx: 2, fill: p.cls[c.id].color }, s);
  });
  const hatchUrl = hatch(s, '#ff9a9a');
  // phase strip (MTP): draft / verify / accept
  for (const q of phases) {
    const a = Math.max(x0, X(q.start)), b = Math.min(x1, X(q.end));
    if (b - a < 0.3) continue;
    const r = svg('rect', { x: a, y: 0, width: Math.max(0.6, b - a - 1), height: pH - 3, rx: 3, fill: PHASE[q.id]?.color || '#888' }, s);
    if (b - a > 40) { const t = svg('text', { x: a + 4, y: pH - 6, class: 'phlab' }, s); t.textContent = clipTo(`${q.label} · ${fmtCyc(q.cycles)}`, (b - a - 6) / 6.6); }
    r.addEventListener('mousemove', (ev) => tip(h('div', {}, h('b', {}, q.label), h('div', { class: 'tp-dm' }, `${fmtCyc(q.cycles)} (${fmtUs(q.cycles)}) · ${(q.share * 100).toFixed(1)} % of the step`)), ev));
    r.addEventListener('mouseleave', () => tip(null));
  }
  // group strip
  const gs = data.groups.filter((g) => g.end >= t0 && g.start <= t1);
  gs.forEach((g, i) => {
    const a = Math.max(x0, X(g.start)), b = Math.min(x1, X(g.end));
    if (b - a < 0.5) return;
    const r = svg('rect', { x: a, y: pH, width: Math.max(0.5, b - a - 1), height: gH - pH, rx: 3, class: 'grp' + (i % 2 ? ' alt' : '') }, s);
    if (b - a > 34) { const t = svg('text', { x: a + 4, y: pH + 15, class: 'grplab' }, s); t.textContent = clipTo(g.label.replace(/^Stage (\d+): /, 'S$1 ').replace(/^Layer /, 'L'), (b - a - 6) / 6.6); }
    r.addEventListener('mousemove', (ev) => tip(h('div', {}, h('b', {}, g.label), h('div', { class: 'tp-dm' }, `${fmtCyc(g.cycles)} · ${(g.share * 100).toFixed(2)} % of the token · click to zoom`)), ev));
    r.addEventListener('mouseleave', () => tip(null));
    r.addEventListener('click', () => onZoom && onZoom(g.id));
  });
  // bars
  const bars = {};
  const vis = data.nodes.filter((n) => n.end >= t0 && n.start <= t1 && laneY[n.cls] !== undefined);
  vis.sort((a, b) => (a.critical - b.critical));
  for (const n of vis) {
    const a = Math.max(x0, X(n.start)), b = Math.min(x1, X(n.end));
    const w = Math.max(1, b - a);
    const y = laneY[n.cls] + (n.critical ? 0 : laneH * 0.55);
    const hh = n.critical ? laneH : laneH * 0.45;
    const r = svg('rect', { x: a, y, width: w, height: hh, rx: Math.min(3, w / 3), fill: p.cls[n.cls].color, class: 'bar ' + (n.critical ? 'crit' : 'par') + (n.hw?.status === 'partial' ? ' hwp' : '') }, s);
    if (n.hw?.status === 'none') svg('rect', { x: a, y, width: w, height: hh, fill: hatchUrl, 'pointer-events': 'none' }, s);
    r.addEventListener('mousemove', (ev) => tip(detail(data, n, { links: false }), ev));
    r.addEventListener('mouseleave', () => tip(null));
    r.addEventListener('click', () => { hl(n.id); onSelect && onSelect(n); });
    bars[n.id] = r;
  }
  // critical chain through the lanes (step line at bar mid-height)
  const cp = data.critical_path.map((id) => p.nodes[id]).filter((n) => n.end >= t0 && n.start <= t1 && laneY[n.cls] !== undefined);
  if (cp.length) {
    let d = '', prevY = null;
    for (const n of cp) {
      const y = laneY[n.cls] + laneH / 2, a = Math.max(x0, X(n.start)), b = Math.min(x1, X(n.end));
      d += prevY === null ? `M${a},${y}` : `L${a},${prevY}L${a},${y}`;
      d += `L${b},${y}`; prevY = y;
    }
    svg('path', { d, class: 'chain' }, s);
  }
  // axis
  const ay = H - axH + 8;
  const span = t1 - t0, step = nice(span / Math.max(2, Math.floor((x1 - x0) / (narrow ? 70 : 170))));
  for (let t = Math.ceil(t0 / step) * step; t <= t1; t += step) {
    svg('line', { x1: X(t), x2: X(t), y1: gH + 2, y2: ay - 4, class: 'tick' }, s);
    const tx = svg('text', { x: X(t), y: ay + 6, 'text-anchor': 'middle' }, s);
    tx.textContent = (t >= 1e4 ? (t / 1e3).toFixed(t % 1e3 ? 1 : 0) + 'k' : Math.round(t)) + (narrow ? '' : ` · ${(t / CLK * 1e6).toFixed(1)}µs`);
  }
  const cap = svg('text', { x: x1, y: ay + 20, 'text-anchor': 'end' }, s);
  cap.textContent = `cycles @ 1.2 GHz · window ${fmtCyc(span)} (${fmtUs(span)})`;
  const cursor = svg('line', { y1: gH + 2, y2: ay - 4, class: 'cursor' }, s);
  let hlId = null;
  function hl(id) { if (hlId) bars[hlId]?.classList.remove('hl'); hlId = id; bars[id]?.classList.add('hl'); }
  let off = null;
  const at = (t) => { const x = X(Math.min(t1, Math.max(t0, t))); cursor.setAttribute('x1', x); cursor.setAttribute('x2', x); };
  if (clock) { off = clock.on(at); at(clock.t); }
  s.addEventListener('dblclick', (ev) => { if (!clock) return; const r = s.getBoundingClientRect(); const t = t0 + ((ev.clientX - r.left) * W / r.width - x0) / k; clock.seek(t); });
  return { destroy() { off && off(); root.remove(); }, select: hl };
}

function nice(x) {
  const e = Math.pow(10, Math.floor(Math.log10(x))), f = x / e;
  return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * e;
}
function clipTo(s, n) { n = Math.floor(n); return s.length > n ? s.slice(0, Math.max(1, n - 1)) + '…' : s; }

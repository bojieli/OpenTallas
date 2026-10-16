// Token-path views: shared helpers (data access, palette, formatting, tooltip, element links, replay clock).
// Data: opentallas.token_path.v1 records written by tools/token_path_export.py (main).

import { GAPS, COL, covClasses, covLevel } from '/explorer/coverage/gaps.js';

export const CLK = 1.2e9;

// Categorical slots (dataviz reference palette, dark steps) in fixed order; classes past eight fall to neutral greys
// (they are always labelled: Gantt lanes and legends carry the class name).
export const SLOTS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'];
export const NEUTRAL = ['#8a97b8', '#5b6684'];
export const CRIT = '#5ee7ff';          // critical-path accent (fleet-viz --accent)

export const SVGNS = 'http://www.w3.org/2000/svg';

// MTP: phases of one verify step and the hardware status of MTP-only operators (hw.status from the export).
export const PHASE = {
  draft: { label: 'Draft', color: '#f2b84b' },
  verify: { label: 'Verify', color: CRIT },
  accept: { label: 'Accept / commit', color: '#7ee08a' },
};
export const HW = {
  built: 'built (closed elements / the AR path\'s hardware)',
  partial: 'block closed, not integrated / adopted',
  none: 'not built — no closed hardware element',
};
/** hardware status of a group: none when every critical operator is unbuilt, partial when any is unbuilt / partial */
export function groupHw(data, gid) {
  const ns = (P(data).byGroup[gid] || []).filter((n) => n.critical && n.hw);
  if (!ns.length) return null;
  if (ns.every((n) => n.hw.status === 'none')) return 'none';
  if (ns.some((n) => n.hw.status !== 'built')) return 'partial';
  return 'built';
}
let hatchN = 0;
/** add a diagonal-hatch pattern to an svg; returns its url(#id) */
export function hatch(s, color = '#ffffff') {
  const id = 'tp-hatch-' + (++hatchN);
  const defs = svg('defs', {}, s);
  const p = svg('pattern', { id, width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' }, defs);
  svg('rect', { width: 6, height: 6, fill: '#05070d', 'fill-opacity': 0.55 }, p);
  svg('line', { x1: 0, y1: 0, x2: 0, y2: 6, stroke: color, 'stroke-width': 2.2, 'stroke-opacity': 0.75 }, p);
  return `url(#${id})`;
}

export function svg(tag, attrs = {}, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

export function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k === 'style') e.style.cssText = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null) e.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined) e.append(k instanceof Node ? k : document.createTextNode(String(k)));
  return e;
}

/** Index one record: node map, class map + colours, group map, edges by node. */
export function prepare(data) {
  if (data._prep) return data;
  const cls = {};
  data.classes.forEach((c, i) => { cls[c.id] = Object.assign({ color: i < SLOTS.length ? SLOTS[i] : NEUTRAL[(i - SLOTS.length) % 2], idx: i }, c); });
  const nodes = {};
  for (const n of data.nodes) nodes[n.id] = n;
  const groups = {};
  data.groups.forEach((g, i) => { groups[g.id] = Object.assign(g, { idx: i }); });
  const byGroup = {};
  for (const n of data.nodes) (byGroup[n.group] ||= []).push(n);
  const out = {}, inn = {};
  for (const e of data.edges) { (out[e.src] ||= []).push(e); (inn[e.dst] ||= []).push(e); }
  const critIdx = {};
  data.critical_path.forEach((id, i) => { critIdx[id] = i; });
  data._prep = { cls, nodes, groups, byGroup, out, inn, critIdx, total: data.totals.cycles };
  return data;
}

export const P = (data) => prepare(data)._prep;

export function elementsOf(data, n) { return n.elements || (P(data).cls[n.cls] || {}).elements || []; }
export function instancesOf(data, n) { return n.instances || (P(data).cls[n.cls] || {}).instances || []; }

export function elementHref(name) { return '/explorer#element=' + encodeURIComponent(name); }

export function fmtCyc(c) {
  const a = Math.abs(c);
  if (a >= 1e6) return (c / 1e6).toFixed(2) + ' M cyc';
  if (a >= 1e4) return (c / 1e3).toFixed(1) + ' k cyc';
  return (Math.round(c * 10) / 10).toLocaleString() + ' cyc';
}
export function fmtUs(c) { return (c / CLK * 1e6).toFixed(c / CLK * 1e6 < 10 ? 3 : 2) + ' µs'; }
export function fmtPct(x) { return (x * 100).toFixed(x < 0.001 ? 3 : x < 0.01 ? 2 : 1) + ' %'; }
export function fmtBytes(b) {
  if (b == null) return '';
  if (b >= 1 << 20) return (b / (1 << 20)).toFixed(2) + ' MiB';
  if (b >= 1024) return (b / 1024).toFixed(1) + ' KiB';
  return b + ' B';
}

export const GRADE = {
  measured: 'measured RTL', 'measured+vendor': 'measured RTL + vendor PHY budget', apportioned: 'measured total, op split by trace',
  priced: 'priced (closure / wire cost)', lever: 'exact lever credit', modelled: 'modelled', zero: 'zero',
};

/** Node detail as a DOM fragment (tooltip body / selection panel). */
export function detail(data, n, { links = true } = {}) {
  const p = P(data);
  const c = p.cls[n.cls] || {};
  const rows = [];
  rows.push(h('div', { class: 'tp-dt' }, h('span', { class: 'tp-sw', style: `background:${c.color}` }), h('b', {}, n.label)));
  rows.push(h('div', { class: 'tp-dm' }, `${c.label || n.cls} · group ${p.groups[n.group]?.label || n.group}`));
  rows.push(h('div', { class: 'tp-kv' },
    h('span', {}, 'cycles'), h('b', {}, fmtCyc(n.cycles) + ' (' + fmtUs(n.cycles) + ')'),
    h('span', {}, 'window'), h('b', {}, `${Math.round(n.start).toLocaleString()} → ${Math.round(n.end).toLocaleString()}`),
    h('span', {}, 'critical'), h('b', { style: n.critical ? `color:${CRIT}` : '' }, n.critical ? `yes · ${fmtPct(n.share)} of the token` : `no · slack ${fmtCyc(n.slack || 0)}`),
    h('span', {}, 'source'), h('b', {}, GRADE[n.src.grade] || n.src.grade)));
  if (n.phase) rows.push(h('div', { class: 'tp-dm' }, 'MTP phase: ', h('b', { style: `color:${PHASE[n.phase]?.color}` }, PHASE[n.phase]?.label || n.phase)));
  if (n.hw) {
    rows.push(h('div', { class: 'tp-hw tp-hw-' + n.hw.status }, n.hw.status === 'none' ? '▨ ' + (n.flag || 'NOT BUILT') : n.hw.status === 'partial' ? '◌ block closed, not integrated' : '■ built'));
    rows.push(h('div', { class: 'tp-note' }, n.hw.note + (n.hw.evidence ? ' [' + n.hw.evidence + ']' : '')));
  }
  if (n.cov && n.cov.rows.length) {
    const lv = covLevel(n);
    const box = h('div', { class: 'tp-cov' + (lv ? ' tp-cov-' + lv : '') },
      h('div', { class: 'tp-dm' }, lv === 'uncovered' ? 'COVERAGE: no hardware on a die for ' : lv === 'gap' ? 'COVERAGE: gaps in ' : 'coverage: ', `${n.cov.target} rows`));
    for (const r of n.cov.rows) {
      box.append(h('div', { class: 'tp-covr' }, h('a', { class: 'tp-el', href: `/explorer/coverage/#t=${n.cov.target}&q=${encodeURIComponent(r.fid)}&cell=${encodeURIComponent(r.fid + '@' + n.cov.target)}` }, r.fid), ' ',
        r.gaps.length ? [...new Map(r.gaps.map((g) => [g.cls, g])).values()].map((g) => h('span', { class: 'tp-gc', style: `background:${GAPS[g.cls]?.color || '#888'}`, title: `${GAPS[g.cls]?.label || g.cls} · owner ${g.owner || 'NONE'}` }, GAPS[g.cls]?.tag || g.cls))
          : h('span', { class: 'tp-dm' }, 'covered'),
        r.owner ? h('span', { class: 'tp-dm' }, ' · ' + r.owner) : null));
    }
    rows.push(box);
  }
  if (n.adders && n.adders.length) {
    const t = h('div', { class: 'tp-add' }, h('div', { class: 'tp-dm' }, `base ${fmtCyc(n.base_cycles)} + priced adders:`));
    for (const [it, cy] of n.adders) t.append(h('div', {}, `${cy >= 0 ? '+' : ''}${cy} ${it}`));
    rows.push(t);
  }
  if (n.reprice_10_08) rows.push(h('div', { class: 'tp-dm' }, 'includes re-price 10-08: ' + n.reprice_10_08.join('; ')));
  rows.push(h('div', { class: 'tp-src' }, n.src.record + (n.src.pointer ? ' · ' + n.src.pointer : '')));
  if (n.src.note) rows.push(h('div', { class: 'tp-note' }, n.src.note));
  if (links) {
    const els = elementsOf(data, n);
    if (els.length) {
      const l = h('div', { class: 'tp-els' }, h('span', { class: 'tp-dm' }, 'elements: '));
      els.slice(0, 12).forEach((e) => l.append(h('a', { href: elementHref(e), class: 'tp-el' }, e)));
      if (els.length > 12) l.append(h('span', { class: 'tp-dm' }, ` +${els.length - 12}`));
      rows.push(l);
    }
  }
  return h('div', {}, rows);
}

let tipEl = null;
export function tip(content, ev) {
  if (!tipEl) { tipEl = h('div', { class: 'tp-tip' }); document.body.appendChild(tipEl); }
  if (!content) { tipEl.style.display = 'none'; return; }
  tipEl.replaceChildren(content);
  tipEl.style.display = 'block';
  const w = tipEl.offsetWidth, hh = tipEl.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + w > innerWidth - 8) x = Math.max(8, ev.clientX - w - 14);
  if (y + hh > innerHeight - 8) y = Math.max(8, innerHeight - hh - 8);
  tipEl.style.left = x + 'px'; tipEl.style.top = y + 'px';
}

/**
 * Replay clock shared by the views: token time in cycles over a scope [t0, t1], played in `seconds` of wall time.
 * Subscribers get (t, clock) every frame and on seek.
 */
export class Clock {
  constructor({ t0 = 0, t1 = 1, seconds = 20 } = {}) {
    this.t0 = t0; this.t1 = t1; this.seconds = seconds; this.t = t0; this.playing = false; this.subs = new Set(); this.loop = true;
    this._raf = null; this._last = 0;
  }
  on(fn) { this.subs.add(fn); return () => this.subs.delete(fn); }
  emit() { for (const f of this.subs) f(this.t, this); }
  scope(t0, t1, seconds) { this.t0 = t0; this.t1 = Math.max(t1, t0 + 1); if (seconds) this.seconds = seconds; this.t = t0; this.emit(); }
  seek(t) { this.t = Math.min(this.t1, Math.max(this.t0, t)); this.emit(); }
  play() {
    if (this.playing) return; this.playing = true; this._last = performance.now();
    const step = (now) => {
      if (!this.playing) return;
      const dt = (now - this._last) / 1000; this._last = now;
      this.t += dt * (this.t1 - this.t0) / this.seconds;
      if (this.t >= this.t1) { if (this.loop) this.t = this.t0; else { this.t = this.t1; this.playing = false; } }
      this.emit();
      this._raf = requestAnimationFrame(step);
    };
    this._raf = requestAnimationFrame(step);
    this.emit();
  }
  pause() { this.playing = false; if (this._raf) cancelAnimationFrame(this._raf); this.emit(); }
  toggle() { this.playing ? this.pause() : this.play(); }
}

/** Critical node active at time t (binary search on the critical chain). */
export function critAt(data, t) {
  const cp = data.critical_path, N = P(data).nodes;
  let lo = 0, hi = cp.length - 1;
  while (lo < hi) {
    const m = (lo + hi + 1) >> 1;
    if (N[cp[m]].start <= t) lo = m; else hi = m - 1;
  }
  return N[cp[lo]];
}

export const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

export const CSS = `
.tp-root{--tp-bg:#05070d;--tp-panel:#0b1020;--tp-line:#1b2540;--tp-ink:#e8eefc;--tp-dim:#8a97b8;--tp-faint:#4a5678;--tp-crit:${CRIT};
  color:var(--tp-ink);font:13px Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.tp-root svg text{fill:var(--tp-dim);font:11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.tp-tip{position:fixed;z-index:1000;max-width:440px;background:#0b1020f2;border:1px solid #2a3a63;border-radius:10px;padding:9px 11px;
  color:#e8eefc;font:12px Inter,ui-sans-serif,system-ui,sans-serif;pointer-events:none;box-shadow:0 8px 30px #000a;display:none}
.tp-dt{display:flex;gap:7px;align-items:center;font-size:13px}.tp-sw{width:10px;height:10px;border-radius:3px;flex:none}
.tp-dm{color:#8a97b8;font-size:11.5px;margin-top:3px}
.tp-kv{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin-top:6px;font:11.5px ui-monospace,Menlo,monospace;color:#8a97b8}
.tp-kv b{color:#e8eefc;font-weight:600;font-variant-numeric:tabular-nums}
.tp-add{margin-top:6px;font:11px ui-monospace,Menlo,monospace;color:#c3cbe0}
.tp-src{margin-top:6px;font:11px ui-monospace,Menlo,monospace;color:#8a97b8;word-break:break-all}
.tp-note{margin-top:3px;font-size:11px;color:#8a97b8;line-height:1.35}
.tp-els{margin-top:6px;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.tp-el{font:11px ui-monospace,Menlo,monospace;color:#5ee7ff;text-decoration:none;border:1px solid #1b2540;border-radius:5px;padding:1px 5px}
.tp-el:hover{border-color:#5ee7ff}
.tp-hw{margin-top:6px;font:600 11px ui-monospace,Menlo,monospace;display:inline-block;border-radius:5px;padding:1px 6px}
.tp-hw-none{color:#ffd0d0;background:repeating-linear-gradient(45deg,#5a1f2a 0 4px,#2a0f16 4px 8px);border:1px solid #e66767}
.tp-hw-partial{color:#e8eefc;border:1px dashed #c3cbe0}
.tp-hw-built{color:#7ee08a;border:1px solid #1b2540}
.tp-cov{margin-top:6px;border:1px solid #1b2540;border-radius:7px;padding:4px 7px}
.tp-cov-uncovered{border-color:#ff4fa3}.tp-cov-gap{border-color:#ffc857}
.tp-covr{margin-top:3px;font:11px ui-monospace,Menlo,monospace;color:#c3cbe0;display:flex;flex-wrap:wrap;gap:3px;align-items:center}
.tp-gc{font:700 9.5px ui-monospace,Menlo,monospace;color:#05070d;border-radius:4px;padding:0 4px}
.tp-badge{font:700 9.5px ui-monospace,Menlo,monospace;fill:#ffd0d0!important;letter-spacing:.04em}
`;

export { GAPS, COL, covClasses, covLevel };

export function injectCSS(id, text) {
  if (document.getElementById(id)) return;
  const s = document.createElement('style'); s.id = id; s.textContent = text; document.head.appendChild(s);
}

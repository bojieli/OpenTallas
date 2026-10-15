// (c) Floorplan overlay driver: turn a token-path record + a die geometry into time-indexed highlight events
// (which instances are active, which links carry data), and a small canvas player (DieReplay) that replays them.
// The events are independent of the renderer: a die map that draws its own geometry only needs overlayEvents()
// and activeAt(); DieReplay is the reference renderer used by the standalone harness.
import { P, instancesOf, elementsOf, CRIT, h, tip, detail, injectCSS, CSS, fmtCyc , COL, covLevel, covClasses, GAPS } from './core.js';
import { normalizeDataflow, filterConnections, connectionSegments, connectionLabel, connectionDescription, sourceText } from '../dataflow.js';

/**
 * Normalise a die geometry to {w, h, inst: [{name, kind, x, y, w, h, master}]} (DEF microns, y up). Accepts
 *  - the token-path snapshot {w, h, instances: [[name, kind, x, y, w, h, master]]} (data/geo_<design>.json);
 *  - the chip-explorer geo.json entry {w, h, kinds, rects: [[kindIdx, x, y, w, h, name]], meta: {masters}};
 *  - the Chip Explorer die export /api/explorer/geom?die=<id> {W, H, inst: {name[], x[], y[], w[], h[], m[], k[]}, masters, kinds};
 *  - an object list {w|die_w, h|die_h, instances|blocks: [{name|inst, master|cell, kind, x, y, w, h}]}.
 */
export function normalizeGeometry(g) {
  if (g._norm) return g._norm;
  const W = g.w ?? g.W ?? g.die_w ?? g.die?.w_um, H = g.h ?? g.H ?? g.die_h ?? g.die?.h_um;
  let inst = [];
  if (g.inst && Array.isArray(g.inst.name)) {
    // Chip Explorer die export (/api/explorer/geom?die=<id>): columnar {W, H, inst: {name, x, y, w, h, m, k}, masters, kinds}
    const I = g.inst, ms = g.masters || [], ks = g.kinds || [];
    inst = I.name.map((name, i) => ({ name, kind: ks[I.k[i]]?.name ?? ks[I.k[i]] ?? '', x: I.x[i], y: I.y[i], w: I.w[i], h: I.h[i], master: ms[I.m[i]]?.name ?? '' }));
  } else if (Array.isArray(g.rects)) {
    const ms = (g.meta && g.meta.masters) || {};
    inst = g.rects.map((r) => ({ name: r[5], kind: g.kinds[r[0]], x: r[1], y: r[2], w: r[3], h: r[4], master: ms[r[5]] || '' }));
  } else {
    const list = g.instances || g.blocks || [];
    inst = list.map((r) => Array.isArray(r)
      ? { name: r[0], kind: r[1], x: r[2], y: r[3], w: r[4], h: r[5], master: r[6] || '' }
      : { name: r.name ?? r.inst, kind: r.kind ?? '', x: r.x, y: r.y, w: r.w, h: r.h, master: r.master ?? r.cell ?? '' });
  }
  g._norm = { w: W || Math.max(...inst.map((i) => i.x + i.w)), h: H || Math.max(...inst.map((i) => i.y + i.h)), inst };
  return g._norm;
}

const globRe = new Map();
function glob(p) {
  if (!globRe.has(p)) globRe.set(p, new RegExp('^' + p.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$'));
  return globRe.get(p);
}

/** Instance indices of a node: name globs (node / class `instances`) or masters among the node's `elements`. */
export function resolveInstances(data, geom, n, cache = new Map()) {
  const pats = instancesOf(data, n), els = new Set(elementsOf(data, n));
  const key = pats.join('|') + '#' + [...els].join('|');
  if (cache.has(key)) return cache.get(key);
  const res = [];
  const G = normalizeGeometry(geom);
  const re = pats.map(glob);
  G.inst.forEach((it, i) => { if (re.some((r) => r.test(it.name)) || (it.master && els.has(it.master))) res.push(i); });
  cache.set(key, res);
  return res;
}

/**
 * Time-indexed highlight events for the die map.
 *   overlayEvents(data, geometry, {range: [t0, t1] | null, group: id | null})
 * -> {t0, t1, events: [{t0, t1, node, label, cls, color, critical, instances: [names]}],
 *     links: [{t0, t1, src, dst, from: [x, y], to: [x, y], critical, bytes, link}]}   (times in cycles)
 */
export function overlayEvents(data, geometry, { range = null, group = null } = {}) {
  const p = P(data), G = normalizeGeometry(geometry), cache = new Map();
  let t0 = 0, t1 = data.totals.cycles;
  if (group) { const g = p.groups[group]; t0 = g.start; t1 = g.end; }
  if (range) [t0, t1] = range;
  const span = t1 - t0;
  const nodes = data.nodes.filter((n) => n.end >= t0 && n.start <= t1);
  const idxOf = {};
  const events = nodes.map((n) => {
    // an operator with no closed hardware lights nothing: the die it would run on does not exist (notBuilt)
    const notBuilt = n.hw?.status === 'none';
    const idx = notBuilt ? [] : resolveInstances(data, geometry, n, cache);
    idxOf[n.id] = idx;
    return { t0: n.start, t1: Math.max(n.end, n.start + span * 0.002), node: n.id, label: n.label, cls: n.cls,
             color: p.cls[n.cls]?.color, critical: n.critical, idx, instances: idx.map((i) => G.inst[i].name),
             phase: n.phase || null, hw: n.hw?.status || null, notBuilt,
             cov: covLevel(n), covCls: covClasses(n), covRows: n.cov ? n.cov.rows : [] };
  });
  // Schedule dependencies are not physical transfer paths. Only explicit dataflow metadata is drawn.
  const links = [];
  events.sort((a, b) => a.t0 - b.t0);
  return { t0, t1, events, links };
}

/** Events / links active at time t (linear scan over the time-sorted list; fine for a few thousand events). */
export function activeAt(ev, t) {
  return { events: ev.events.filter((e) => e.t0 <= t && t < e.t1), links: ev.links.filter((l) => l.t0 <= t && t < l.t1) };
}

const R_CSS = `.tp-die{position:relative}.tp-die canvas{display:block;width:100%;border-radius:10px;background:#070a14}
.tp-die .cap{font:11px ui-monospace,Menlo,monospace;color:#8a97b8;margin-top:4px;min-height:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}`;

/** Reference die renderer: draws the geometry once, then the active instances / links for the Clock's time. */
export class DieReplay {
  constructor(el, geometry, data, { clock, group = null, range = null, maxH = 520, dataflow = null } = {}) {
    injectCSS('tp-css', CSS); injectCSS('tp-die-css', R_CSS);
    this.G = normalizeGeometry(geometry); this.data = data;
    this.ev = overlayEvents(data, geometry, { group, range });
    this.df = normalizeDataflow(dataflow || {}); this.flowMode = 'all'; this.flowOn = false; this.showLabels = true;
    this.selected = null; this.minimumWidth = 0; this.search = '';
    const instanceMap = new Map(this.G.inst.map(i => [i.name, i]));
    this.segments = this.df.edges.flatMap(edge => connectionSegments(edge, instanceMap).map(segment => ({ ...segment, edge })));

    const W = Math.max(280, el.clientWidth || 600);
    const s = Math.min(W / this.G.w, maxH / this.G.h);
    this.s = s; this.cw = Math.round(this.G.w * s); this.ch = Math.round(this.G.h * s);
    const dpr = window.devicePixelRatio || 1;
    this.root = h('div', { class: 'tp-die' });
    this.cv = h('canvas', { width: this.cw * dpr, height: this.ch * dpr, style: `max-width:${this.cw}px`, role: 'img', 'aria-label': 'die floorplan replay' });
    this.cap = h('div', { class: 'cap' });
    const toggle = h('input', { type: 'checkbox', 'aria-label': 'dataflow overlay', onchange: e => { this.flowOn = e.target.checked; this.draw(this.t); } });
    const mode = h('select', { 'aria-label': 'dataflow scope', onchange: e => { this.flowMode = e.target.value; this.draw(this.t); } },
      ...[['all', 'All physical connections'], ['current', 'Current operators'], ['selected', 'Selected operator'], ['critical', 'Critical connections']].map(([value, label]) => h('option', { value }, label)));
    const labels = h('input', { type: 'checkbox', checked: '', 'aria-label': 'connection width labels', onchange: e => { this.showLabels = e.target.checked; this.draw(this.t); } });
    const width = h('input', { type: 'number', min: 0, value: 0, style: 'width:68px', 'aria-label': 'minimum connection width', onchange: e => { this.minimumWidth = Math.max(0, Number(e.target.value) || 0); this.draw(this.t); } });
    const search = h('input', { type: 'search', placeholder: 'Connection or instance', 'aria-label': 'connection search', oninput: e => { this.search = e.target.value.toLowerCase(); this.draw(this.t); } });
    this.flowStatus = h('div', { class: 'kv', role: 'status' });
    this.root.append(h('div', { class: 'ctl', style: 'margin-bottom:8px' }, h('label', {}, toggle, ' Dataflow'), mode, h('label', {}, labels, ' Width labels'), h('label', {}, 'Minimum bits ', width), search), this.cv, this.flowStatus,
      h('div', { class: 'kv' }, 'Lines are schematic connections, not routed wires. Arrows require a known source and destination. Width is bits per connection; bandwidth requires clock and activity evidence.'), this.cap);
    el.replaceChildren(this.root);
    this.ctx = this.cv.getContext('2d'); this.ctx.scale(dpr, dpr);
    this.base = document.createElement('canvas'); this.base.width = this.cv.width; this.base.height = this.cv.height;
    const b = this.base.getContext('2d'); b.scale(dpr, dpr);
    for (const r of this.G.inst) {
      b.fillStyle = r.kind === 'waypoint' || /^(w|wh|wv)_/.test(r.name) ? '#141c33' : '#1b2540';
      const [x, y, w, hh] = this.rect(r);
      b.fillRect(x, y, Math.max(0.6, w), Math.max(0.6, hh));
    }
    this.cv.addEventListener('mousemove', (e) => this.hover(e));
    this.cv.addEventListener('mouseleave', () => tip(null));
    this.t = clock ? clock.t : this.ev.t0;
    if (clock) this.off = clock.on((t) => this.draw(t));
    this.draw(this.t);
  }
  /** true when some operator of class `cls` lights at least one instance of this die */
  classHits(cls) { return this.ev.events.some((e) => e.cls === cls && e.idx.length); }
  rect(r) { return [r.x * this.s, (this.G.h - r.y - r.h) * this.s, r.w * this.s, r.h * this.s]; }
  pt([x, y]) { return [x * this.s, (this.G.h - y) * this.s]; }
  draw(t) {
    this.t = t;
    const c = this.ctx;
    c.clearRect(0, 0, this.cw, this.ch);
    c.drawImage(this.base, 0, 0, this.cw, this.ch);
    const { events, links } = activeAt(this.ev, t);
    const visible = new Set(filterConnections(this.df.edges, { mode: this.flowMode, selected: this.selected, activeNodes: events.map(e => e.node) })
      .filter(e => (!this.minimumWidth || (e.width_bits !== null && e.width_bits >= this.minimumWidth)) && (!this.search || [e.id, e.label, e.src, e.dst, ...e.endpoints.map(p => p.instance)].join(' ').toLowerCase().includes(this.search))).map(e => e.id));
    const candidates = this.flowOn ? this.segments.filter(s => visible.has(s.edge.id)) : [];
    const segments = candidates.slice(0, 600);
    this.drawnSegments = segments;
    const mapped = this.df.coverage.token_mapped;
    this.flowStatus.textContent = `${this.flowOn ? `${segments.length} segments shown${candidates.length > 600 ? ` / ${candidates.length}; narrow the filter` : ''}${this.showLabels && segments.length > 50 ? ' · first 50 width labels shown; narrow the filter or hover a line' : ''}` : 'Dataflow overlay off'} · ${this.df.coverage.total} source connections · ${this.df.coverage.widths_known} widths known · ${this.df.coverage.rates_known} required rates known · ${mapped} explicit token mappings` +
      (!mapped ? ' · Current/selected operator filtering unavailable: no token-to-connection mapping.' : '') +
      (this.df.error ? ` · ${this.df.error}` : '');
    events.sort((a, b) => a.critical - b.critical);
    for (const e of events) {
      c.fillStyle = e.color; c.globalAlpha = e.critical ? 0.9 : 0.5;
      for (const i of e.idx) { const [x, y, w, hh] = this.rect(this.G.inst[i]); c.fillRect(x, y, Math.max(1, w), Math.max(1, hh)); }
      if (e.critical) {
        c.globalAlpha = 1; c.strokeStyle = CRIT; c.lineWidth = 1;
        if (e.idx.length <= 64) for (const i of e.idx) { const [x, y, w, hh] = this.rect(this.G.inst[i]); c.strokeRect(x - 0.5, y - 0.5, w + 1, hh + 1); }
      }
    }
    c.globalAlpha = 1;
    for (const l of links) {
      const [ax, ay] = this.pt(l.from), [bx, by] = this.pt(l.to);
      c.strokeStyle = l.critical ? CRIT : '#c3cbe0'; c.lineWidth = l.critical ? 2 : 1; c.setLineDash(l.critical ? [] : [4, 3]);
      c.beginPath(); c.moveTo(ax, ay); c.lineTo(bx, by); c.stroke(); c.setLineDash([]);
      const f = Math.min(1, Math.max(0, (t - l.t0) / Math.max(1e-9, l.t1 - l.t0)));
      c.fillStyle = '#fff'; c.beginPath(); c.arc(ax + (bx - ax) * f, ay + (by - ay) * f, 3.5, 0, 6.3); c.fill();
    }
    for (const [index, segment] of segments.entries()) {
      const [ax, ay] = this.pt(segment.from), [bx, by] = this.pt(segment.to), e = segment.edge;
      c.strokeStyle = e.critical ? CRIT : '#efb971'; c.lineWidth = e.critical ? 2 : 1.2;
      c.setLineDash(segment.directed ? [] : [4, 3]); c.beginPath(); c.moveTo(ax, ay); c.lineTo(bx, by); c.stroke(); c.setLineDash([]);
      if (segment.directed) {
        const angle = Math.atan2(by - ay, bx - ax); c.fillStyle = c.strokeStyle;
        c.beginPath(); c.moveTo(bx, by); c.lineTo(bx - 8 * Math.cos(angle - .4), by - 8 * Math.sin(angle - .4)); c.lineTo(bx - 8 * Math.cos(angle + .4), by - 8 * Math.sin(angle + .4)); c.closePath(); c.fill();
      }
      if (this.showLabels && index < 50) {
        const label = connectionLabel(e); c.font = '10px ui-monospace,monospace';
        const x = (ax + bx) / 2, y = (ay + by) / 2, w = c.measureText(label).width;
        c.fillStyle = '#070a14ee'; c.fillRect(x - w / 2 - 2, y - 10, w + 4, 13); c.fillStyle = '#ffe0a8'; c.fillText(label, x - w / 2, y);
      }
    }
    // coverage: outline the instances of gap operators (pink = no hardware on a die, amber = other gaps)
    for (const e of events) {
      if (!e.cov || !e.idx.length) continue;
      c.strokeStyle = e.cov === 'uncovered' ? COL.uncovered : COL.gap; c.lineWidth = e.critical ? 2 : 1; c.setLineDash(e.cov === 'uncovered' ? [] : [3, 2]);
      for (const i of e.idx.slice(0, 400)) { const [x, y, w, hh] = this.rect(this.G.inst[i]); c.strokeRect(x - 1, y - 1, w + 2, hh + 2); }
      c.setLineDash([]);
    }
    const cur = events.filter((e) => e.critical).pop();
    if (cur && cur.notBuilt) {
      // not built: hatch the die and badge it (the operator runs on hardware that does not exist yet)
      c.save(); c.globalAlpha = 0.5; c.strokeStyle = '#e66767'; c.lineWidth = 3;
      for (let x = -this.ch; x < this.cw; x += 14) { c.beginPath(); c.moveTo(x, this.ch); c.lineTo(x + this.ch, 0); c.stroke(); }
      c.restore();
      const msg = 'NOT BUILT: ' + cur.label;
      c.font = '700 13px ui-monospace,Menlo,monospace';
      const tw = Math.min(this.cw - 16, c.measureText(msg).width + 16);
      c.fillStyle = '#2a0f16'; c.strokeStyle = '#e66767'; c.lineWidth = 1.5;
      c.fillRect(8, 8, tw, 24); c.strokeRect(8, 8, tw, 24);
      c.fillStyle = '#ffd0d0'; c.fillText(msg.length > 60 ? msg.slice(0, 59) + '…' : msg, 16, 25);
    }
    if (cur && cur.cov) {
      // coverage badge (beside NOT BUILT when both apply): the running operator's rows have gaps on this target
      const col = cur.cov === 'uncovered' ? COL.uncovered : COL.gap;
      const fns = [...new Set(cur.covRows.filter((r) => r.gaps.some((g) => cur.covCls.includes(g.cls))).map((r) => r.fid))];
      const msg = (cur.cov === 'uncovered' ? 'NO HW ON DIE: ' : 'GAP: ') + cur.covCls.map((k) => GAPS[k].tag).join(' ') + ' · ' + fns.join(', ');
      c.font = '700 12px ui-monospace,Menlo,monospace';
      const tw = Math.min(this.cw - 16, c.measureText(msg).width + 16), y0 = cur.notBuilt ? 38 : 8;
      c.fillStyle = '#05070dee'; c.strokeStyle = col; c.lineWidth = 1.5;
      c.fillRect(8, y0, tw, 22); c.strokeRect(8, y0, tw, 22);
      c.fillStyle = col; c.fillText(msg.length > 70 ? msg.slice(0, 69) + '…' : msg, 16, y0 + 15);
      if (!cur.idx.length && !cur.notBuilt) {
        c.save(); c.globalAlpha = 0.35; c.strokeStyle = col; c.lineWidth = 2;
        for (let x = -this.ch; x < this.cw; x += 18) { c.beginPath(); c.moveTo(x, this.ch); c.lineTo(x + this.ch, 0); c.stroke(); }
        c.restore();
      }
    }
    this.cap.textContent = cur ? `${Math.round(t).toLocaleString()} cyc · ${cur.phase ? cur.phase.toUpperCase() + ' · ' : ''}${cur.label} · ` +
      (cur.notBuilt ? 'not built (no die / closed element)' : `${cur.idx.length} instances lit${cur.hw === 'partial' ? ' (block closed, not integrated)' : ''}`) +
      (events.length > 1 ? ` · ${events.length - 1} more active` : '') : `${Math.round(t).toLocaleString()} cyc`;
    this.active = events;
  }
  select(id) { this.selected = id; this.draw(this.t); }
  hover(ev) {
    const r = this.cv.getBoundingClientRect();
    const x = (ev.clientX - r.left) / r.width * this.cw / this.s, y = this.G.h - (ev.clientY - r.top) / r.height * this.ch / this.s;
    const px = x * this.s, py = (this.G.h - y) * this.s;
    const segment = (this.drawnSegments || []).find(s => {
      const a = this.pt(s.from), b = this.pt(s.to), dx = b[0] - a[0], dy = b[1] - a[1], d = dx * dx + dy * dy;
      const t = d ? Math.max(0, Math.min(1, ((px - a[0]) * dx + (py - a[1]) * dy) / d)) : 0;
      return Math.hypot(px - a[0] - t * dx, py - a[1] - t * dy) < 5;
    });
    if (segment) return tip(h('div', {}, h('b', {}, connectionDescription(segment.edge)),
      h('div', {}, segment.pin_located ? 'Explicit endpoint coordinates; schematic straight connection.' : 'Instance-centre schematic; exact pin locations/routed path unknown.'),
      h('div', {}, `Source: ${sourceText(segment.edge.source)}`)), ev);
    const hit = this.G.inst.find((i) => x >= i.x && x <= i.x + i.w && y >= i.y && y <= i.y + i.h);
    if (!hit) return tip(null);
    const act = (this.active || []).filter((e) => e.idx.some((i) => this.G.inst[i] === hit));
    tip(h('div', {}, h('b', {}, hit.name), h('div', { class: 'tp-dm' }, `${hit.master || hit.kind} · ${hit.w.toFixed(0)} x ${hit.h.toFixed(0)} µm`),
      ...act.map((e) => h('div', { class: 'tp-add' }, `${e.critical ? '● ' : '○ '}${e.label}`))), ev);
  }
  destroy() { this.off && this.off(); this.root.remove(); }
}

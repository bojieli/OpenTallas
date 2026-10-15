// Canvas floorplan of one die revision with its data-flow links. Blocks to scale (DEF µm, y up), links pin to pin
// (or along their register hops), width ∝ log2(bits) (capped, user scale), colour = reach verdict, dashed = bypasses.
// Level of detail is geometry preserving: every stroke follows a real hop segment. When many links are in view,
// segments whose ends snap to the same pair of 6 px screen cells are merged into one stroke whose ends are the
// bit-weighted means of the members' real ends (so a bundle is never longer than its longest member). Segments shorter
// than a cell, and links shorter than the reach when zoomed out ('auto' local mode), are shown as a local density fill
// instead of strokes.
import { STATUS, BYPASS_COLOR, segmentGrid, blockAt, fmtBits, fmtUm } from './model.js';

const DPR = () => Math.min(2, window.devicePixelRatio || 1);
const RANK = [0, 1, 2, -1];   // worst-status ordering for bundles (unknown lowest)
const CELL_PX = 6;            // bundle snap / density cell, screen px
const SUB_PX = 3;             // segments shorter than this on screen go to the density fill
const LOCAL_PX = 40;          // 'auto': links shorter than the reach become density while reach < LOCAL_PX on screen
const DENS_COLOR = '#7aa7ff';
/** stroke width (px) of a link or bundle of `bits`: log, capped, times the user scale */
export const strokePx = (bits, scale = 1) => scale * Math.min(5, 0.45 + 0.32 * Math.log2(Math.max(1, Number.isFinite(bits) ? bits : 1)));

export class Floor {
  constructor(el, { onPick = () => {}, onHover = () => {}, onPaint = () => {} } = {}) {
    this.el = el; this.onPick = onPick; this.onHover = onHover; this.onPaint = onPaint;
    el.classList.add('df-floor');
    this.cv = document.createElement('canvas'); this.cv.setAttribute('role', 'img');
    this.cv.setAttribute('aria-label', 'Die floorplan with data-flow links');
    this.cv.tabIndex = 0;
    el.append(this.cv);
    this.base = document.createElement('canvas');   // blocks, re-rendered when the view settles
    this.m = null; this.view = { s: 1, ox: 0, oy: 0 }; this.baseView = null; this.baseDirty = true;
    this.st = { mode: 'all', active: null, trail: [], highlight: null, lit: null, litColor: null, selBlock: -1,
      manhattan: false, cut: null, bypassOnly: false, filter: null, flow: false, phase: 0, minBits: 0, minLen: 'auto', wscale: 0.7 };
    this._bind(); this._ro = new ResizeObserver(() => this.resize()); this._ro.observe(el);
  }
  destroy() { this._ro.disconnect(); cancelAnimationFrame(this._raf); this.el.replaceChildren(); }
  setModel(m) { this.m = m; this.baseDirty = true; this._bundleCache = null; this.fit(); }
  set(patch) {
    Object.assign(this.st, patch);
    if ('lit' in patch || 'selBlock' in patch) this._litDirty = true;
    if (['active', 'filter', 'bypassOnly', 'minBits', 'minLen', 'mode'].some((k) => k in patch)) this._bundleCache = null;
    this.draw();
  }
  resize() {
    const r = this.el.getBoundingClientRect(), d = DPR();
    const w = Math.max(50, Math.round(r.width)), h = Math.max(50, Math.round(r.height));
    if (this.cv.width === w * d && this.cv.height === h * d) return;
    this.cv.width = w * d; this.cv.height = h * d; this.cv.style.width = w + 'px'; this.cv.style.height = h + 'px';
    this.base.width = w * d; this.base.height = h * d; this.cw = w; this.ch = h;
    if (!this._fitted) this.fit(); else { this.baseDirty = true; this.draw(); }
  }
  fit() {
    if (!this.m || !this.cw) return;
    const pad = 12, s = Math.min((this.cw - 2 * pad) / this.m.W, (this.ch - 2 * pad) / this.m.H);
    this.view = { s, ox: (this.cw - this.m.W * s) / 2, oy: (this.ch - this.m.H * s) / 2 };
    this._fitted = true; this.baseDirty = true; this._bundleCache = null; this.draw();
  }
  zoomTo(x0, y0, x1, y1, margin = 0.25) {
    if (!this.m) return;
    const w = Math.max(x1 - x0, 200), h = Math.max(y1 - y0, 200), cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    const s = Math.min(this.cw / (w * (1 + 2 * margin)), this.ch / (h * (1 + 2 * margin)), 40);
    this.view = { s, ox: this.cw / 2 - cx * s, oy: this.ch / 2 - (this.m.H - cy) * s };
    this.baseDirty = true; this._bundleCache = null; this.draw();
  }
  X(x) { return this.view.ox + x * this.view.s; }
  Y(y) { return this.view.oy + (this.m.H - y) * this.view.s; }
  inv(px, py) { return [(px - this.view.ox) / this.view.s, this.m.H - (py - this.view.oy) / this.view.s]; }

  // -------------------------------------------------------------------------------------------- interaction
  _bind() {
    const cv = this.cv, ptrs = new Map();
    let drag = null, pinch = null, moved = false;
    cv.addEventListener('wheel', (e) => {
      if (!this.m) return; e.preventDefault();
      const r = cv.getBoundingClientRect(); this._zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0015));
    }, { passive: false });
    cv.addEventListener('pointerdown', (e) => {
      cv.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]); moved = false;
      if (ptrs.size === 1) drag = { x: e.clientX, y: e.clientY, ox: this.view.ox, oy: this.view.oy };
      if (ptrs.size === 2) { const [a, b] = [...ptrs.values()]; pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), s: this.view.s }; drag = null; }
    });
    cv.addEventListener('pointermove', (e) => {
      const r = cv.getBoundingClientRect();
      if (ptrs.has(e.pointerId)) ptrs.set(e.pointerId, [e.clientX, e.clientY]);
      if (pinch && ptrs.size === 2) {
        const [a, b] = [...ptrs.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
        this._zoomAt((a[0] + b[0]) / 2 - r.left, (a[1] + b[1]) / 2 - r.top, (pinch.s * d / pinch.d) / this.view.s); moved = true; return;
      }
      if (drag) {
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
        if (moved) { this.view.ox = drag.ox + dx; this.view.oy = drag.oy + dy; this._interact(); }
        return;
      }
      this._hover(e.clientX - r.left, e.clientY - r.top, e);
    });
    const up = (e) => {
      ptrs.delete(e.pointerId);
      if (ptrs.size < 2) pinch = null;
      if (drag && !moved && e.type === 'pointerup') { const r = cv.getBoundingClientRect(); this._click(e.clientX - r.left, e.clientY - r.top); }
      if (!ptrs.size) drag = null;
    };
    cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
    cv.addEventListener('pointerleave', () => this.onHover(null));
    cv.addEventListener('dblclick', (e) => { const r = cv.getBoundingClientRect(); this._zoomAt(e.clientX - r.left, e.clientY - r.top, 2); });
    cv.addEventListener('keydown', (e) => {
      const k = { '+': 1.4, '=': 1.4, '-': 1 / 1.4 }[e.key];
      if (k) { this._zoomAt(this.cw / 2, this.ch / 2, k); e.preventDefault(); }
      if (e.key === '0') { this.fit(); e.preventDefault(); }
      const pan = { ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40] }[e.key];
      if (pan) { this.view.ox += pan[0]; this.view.oy += pan[1]; this._interact(); e.preventDefault(); }
    });
  }
  _zoomAt(px, py, k) {
    const s = Math.max(1e-4, Math.min(80, this.view.s * k)); k = s / this.view.s;
    this.view.ox = px - (px - this.view.ox) * k; this.view.oy = py - (py - this.view.oy) * k; this.view.s = s;
    this._interact();
  }
  _interact() {   // cheap frames while moving; full base re-render once settled
    this._moving = true; this.draw();   // keep the cached level of detail (µm coordinates) while moving
    clearTimeout(this._settle); this._settle = setTimeout(() => { this._moving = false; this.baseDirty = true; this._bundleCache = null; this.draw(); }, 140);
  }

  // -------------------------------------------------------------------------------------------- visible link set
  visibleLinks() {
    const m = this.m, st = this.st;
    let list = st.mode === 'replay' ? (st.active || new Int32Array(0)) : null;
    let [vx0, vy1] = this.inv(0, 0), [vx1, vy0] = this.inv(this.cw, this.ch); const bb = m.bbox;
    const px = (vx1 - vx0) * 0.25, py = (vy1 - vy0) * 0.25; vx0 -= px; vx1 += px; vy0 -= py; vy1 += py;   // pan margin
    const minLen = typeof st.minLen === 'number' ? st.minLen : 0;
    const inView = (i) => !(bb[i * 4] > vx1 || bb[i * 4 + 2] < vx0 || bb[i * 4 + 1] > vy1 || bb[i * 4 + 3] < vy0);
    const keep = (i) => inView(i) && (!st.bypassOnly || m.cross[i] > 0) && (!st.minBits || m.bits[i] >= st.minBits)
      && (!minLen || !(m.len[i] < minLen)) && (!st.filter || st.filter(i));
    if (!list) { const a = []; for (let i = 0; i < m.nl; i++) if (m.segStart[i + 1] > m.segStart[i] && keep(i)) a.push(i); return a; }
    return Array.from(list).filter(keep);
  }
  _segCount(list) { let n = 0; for (const i of list) n += this.m.segStart[i + 1] - this.m.segStart[i]; return n; }

  /** 'auto' local mode is on: links shorter than the reach collapse into the density fill at this zoom */
  localMode() { return this.st.minLen === 'auto' && this.m.reach * this.view.s < LOCAL_PX; }

  /** Level of detail for `list` at the current zoom: direct links, merged bundles and the local density fill. */
  lodFor(list) {
    const m = this.m, S = m.seg, s = this.view.s, cell = CELL_PX / s, sub = SUB_PX / s, local = this.localMode();
    const dens = new Map(), strokeLinks = [];
    const addDens = (x, y, i, bits) => {
      const key = Math.floor(x / cell) + ',' + Math.floor(y / cell);
      let d = dens.get(key); if (!d) dens.set(key, d = { gx: Math.floor(x / cell), gy: Math.floor(y / cell), n: 0, bits: 0, links: [], last: -1, maxL: 0 });
      if (d.last !== i) { d.n++; d.bits += bits; d.last = i; if (d.links.length < 400) d.links.push(i); if (m.len[i] > d.maxL) d.maxL = m.len[i]; }
    };
    let nseg = 0;
    for (const i of list) {
      const bits = m.bits[i] || 1, a = m.segStart[i], z = m.segStart[i + 1];
      const diag = Math.max(m.bbox[i * 4 + 2] - m.bbox[i * 4], m.bbox[i * 4 + 3] - m.bbox[i * 4 + 1]);
      if ((local && m.len[i] < m.reach) || diag < sub) { addDens((m.bbox[i * 4] + m.bbox[i * 4 + 2]) / 2, (m.bbox[i * 4 + 1] + m.bbox[i * 4 + 3]) / 2, i, bits); continue; }
      strokeLinks.push(i); nseg += z - a;
    }
    const out = { s, cell, dens: [...dens.values()], links: null, bundles: null, nLocal: 0, list };
    for (const d of out.dens) out.nLocal += d.n;
    if (strokeLinks.length <= 2500 && nseg <= 24000) { out.links = strokeLinks; return out; }
    // merge parallel segments that snap to the same pair of screen cells
    const map = new Map();
    for (const i of strokeLinks) {
      const bitsL = m.bits[i] || 1;
      for (let k = m.segStart[i]; k < m.segStart[i + 1]; k++) {
        const x1 = S[k * 5], y1 = S[k * 5 + 1], x2 = S[k * 5 + 2], y2 = S[k * 5 + 3], bt = S[k * 5 + 4] || bitsL;
        if (Math.abs(x2 - x1) + Math.abs(y2 - y1) < sub) continue;   // sub-pixel piece of a longer chain: its neighbours carry the shape
        const key = Math.floor(x1 / cell) + ',' + Math.floor(y1 / cell) + '>' + Math.floor(x2 / cell) + ',' + Math.floor(y2 / cell);
        let b = map.get(key);
        if (!b) map.set(key, b = { x1: 0, y1: 0, x2: 0, y2: 0, w: 0, bits: 0, n: 0, links: [], st: 3, by: 0, maxSeg: 0, last: -1 });
        b.x1 += x1 * bt; b.y1 += y1 * bt; b.x2 += x2 * bt; b.y2 += y2 * bt; b.w += bt;
        b.maxSeg = Math.max(b.maxSeg, Math.abs(x2 - x1) + Math.abs(y2 - y1));
        if (b.last !== i) {   // count each link once per bundle (a link contributes one segment per cell pair)
          b.last = i; b.bits += bt; b.n++; if (b.links.length < 400) b.links.push(i);
          if (RANK[m.status[i]] > RANK[b.st]) b.st = m.status[i];
          if (m.cross[i] > 0) b.by++;
        }
      }
    }
    const bundles = [];
    for (const b of map.values()) { b.x1 /= b.w; b.y1 /= b.w; b.x2 /= b.w; b.y2 /= b.w; bundles.push(b); }
    bundles.sort((p, q) => p.bits - q.bits);
    out.bundles = bundles;
    return out;
  }

  // -------------------------------------------------------------------------------------------- drawing
  draw() { if (!this._pending) { this._pending = true; this._raf = requestAnimationFrame(() => { this._pending = false; this._paint(); }); } }

  _paintBase() {
    const m = this.m, c = this.base.getContext('2d'), d = DPR();
    c.setTransform(d, 0, 0, d, 0, 0); c.clearRect(0, 0, this.cw, this.ch);
    c.fillStyle = '#070b16'; c.fillRect(this.X(0), this.Y(m.H), m.W * this.view.s, m.H * this.view.s);
    c.strokeStyle = '#2a3558'; c.lineWidth = 1; c.strokeRect(this.X(0), this.Y(m.H), m.W * this.view.s, m.H * this.view.s);
    const s = this.view.s, x0 = -this.view.ox / s, x1 = (this.cw - this.view.ox) / s, yTop = m.H + this.view.oy / s, yBot = m.H - (this.ch - this.view.oy) / s;
    c.fillStyle = '#131c30'; c.strokeStyle = '#26324f'; c.lineWidth = 0.6;
    const showReg = s * 20 > 2;
    c.beginPath();
    const big = [];
    for (let b = 0; b < m.nb; b++) {
      if (m.bx[b] > x1 || m.bx[b] + m.bw[b] < x0 || m.by[b] > yTop || m.by[b] + m.bh[b] < yBot) continue;
      if (m.reg[b] && !showReg) continue;
      const w = m.bw[b] * s, h = m.bh[b] * s;
      if (w < 0.4 && h < 0.4) continue;
      c.rect(this.X(m.bx[b]), this.Y(m.by[b] + m.bh[b]), Math.max(w, 0.6), Math.max(h, 0.6));
      if (w > 60 && h > 14) big.push(b);
    }
    c.fill(); if (s > 0.004) c.stroke();
    // names of big blocks only (no overlap: one per block, clipped to the block)
    c.font = '10px ui-monospace,Menlo,monospace'; c.fillStyle = '#5d6a8c'; c.textBaseline = 'top';
    for (const b of big.slice(0, 400)) {
      const x = this.X(m.bx[b]) + 3, y = this.Y(m.by[b] + m.bh[b]) + 2, w = m.bw[b] * s - 6;
      const t = m.bname[b]; if (c.measureText(t).width > w) continue;
      c.fillText(t, x, y);
    }
    this.baseView = { ...this.view }; this.baseDirty = false;
  }

  _paint() {
    const m = this.m; if (!m || !this.cw) return;
    const c = this.cv.getContext('2d'), d = DPR(), st = this.st;
    if (this.baseDirty && !this._moving) this._paintBase();
    c.setTransform(1, 0, 0, 1, 0, 0); c.fillStyle = '#05070d'; c.fillRect(0, 0, this.cv.width, this.cv.height);
    if (this.baseView) {   // reuse the settled bitmap while panning / zooming
      const k = this.view.s / this.baseView.s;
      c.setTransform(d, 0, 0, d, 0, 0);
      c.drawImage(this.base, 0, 0, this.base.width, this.base.height, this.view.ox - this.baseView.ox * k, this.view.oy - this.baseView.oy * k, this.cw * k, this.ch * k);
    }
    c.setTransform(d, 0, 0, d, 0, 0);
    // lit blocks (replay activity) and the selected block
    if (st.lit) {
      const s = this.view.s;
      for (const [color, blocks] of st.lit) {
        c.fillStyle = color; c.beginPath();
        for (const b of blocks) { const w = m.bw[b] * s, h = m.bh[b] * s; if (m.reg[b] && w < 1.5) continue; c.rect(this.X(m.bx[b]), this.Y(m.by[b] + m.bh[b]), Math.max(w, 0.8), Math.max(h, 0.8)); }
        c.fill();
      }
    }
    if (st.selBlock >= 0) {
      const b = st.selBlock; c.strokeStyle = '#ffffff'; c.lineWidth = 2;
      c.strokeRect(this.X(m.bx[b]) - 1, this.Y(m.by[b] + m.bh[b]) - 1, Math.max(3, m.bw[b] * this.view.s) + 2, Math.max(3, m.bh[b] * this.view.s) + 2);
    }
    if (st.cut) this._paintCut(c, st.cut);
    const hl = st.highlight && st.highlight.size ? st.highlight : null;
    // trail of recently used links (replay)
    if (st.mode === 'replay' && st.trail.length) {
      for (const [list, alpha] of st.trail) { c.globalAlpha = alpha * (hl ? 0.4 : 1); this._paintLinks(c, list, { thin: true }); }
      c.globalAlpha = 1;
    }
    if (!this._bundleCache || (!this._moving && this._bundleCache.s !== this.view.s)) this._bundleCache = this.lodFor(this.visibleLinks());
    const L = this._bundleCache;
    this.visibleCount = L.list.length; this.localCount = L.nLocal;
    c.globalAlpha = hl ? 0.28 : 1;
    this._paintDensity(c, L);
    if (L.bundles) { this._paintBundles(c, L.bundles); this.lod = 'bundled'; this.bundleCount = L.bundles.length; }
    else { const segs = this._segCount(L.links); this._paintLinks(c, L.links, { arrows: segs < 2500, flow: st.flow && segs < 4000 }); this.lod = 'links'; this.bundleCount = 0; }
    c.globalAlpha = 1;
    if (hl) this._paintLinks(c, [...hl], { arrows: true, halo: true, flow: st.flow });
    if (this._hoverLink != null && this._hoverLink >= 0) this._paintLinks(c, [this._hoverLink], { arrows: true, halo: true });
    if (this._hoverBundle && this._hoverBundle.dens) this._paintDensity(c, { cell: this._bundleCache.cell, dens: [this._hoverBundle] }, true);
    else if (this._hoverBundle) this._paintBundles(c, [this._hoverBundle], true);
    // scale bar
    const um = [100, 200, 500, 1000, 2000, 5000, 10000].find((u) => u * this.view.s > 70) || 10000;
    c.fillStyle = '#8a97b8'; c.fillRect(this.cw - 16 - um * this.view.s, this.ch - 14, um * this.view.s, 2);
    c.font = '10px ui-monospace,Menlo,monospace'; c.textAlign = 'right'; c.fillText(um >= 1000 ? um / 1000 + ' mm' : um + ' µm', this.cw - 16, this.ch - 18); c.textAlign = 'left';
    this.onPaint(this);
    if (st.flow && !matchMedia('(prefers-reduced-motion: reduce)').matches) { this.st.phase = (this.st.phase + 0.6) % 24; this.draw(); }
  }

  _path(c, x1, y1, x2, y2) {
    c.moveTo(this.X(x1), this.Y(y1));
    if (this.st.manhattan) c.lineTo(this.X(x2), this.Y(y1));
    c.lineTo(this.X(x2), this.Y(y2));
  }

  _paintLinks(c, list, { arrows = false, halo = false, thin = false, flow = false } = {}) {
    const m = this.m, S = m.seg, groups = new Map();
    for (const i of list) {
      const bits = m.bits[i], w = thin ? Math.max(0.6, strokePx(bits, this.st.wscale) * 0.5) : Math.max(0.6, strokePx(bits, this.st.wscale));
      const key = m.status[i] + '|' + (m.cross[i] > 0 ? 1 : 0) + '|' + (Math.round(w * 2) / 2);
      let g = groups.get(key); if (!g) groups.set(key, g = []); g.push(i);
    }
    c.lineCap = 'round'; c.lineJoin = 'round';
    for (const [key, ids] of groups) {
      const [stv, byp, w] = key.split('|'), color = STATUS[+stv].color;
      if (halo) { c.strokeStyle = '#ffffff'; c.lineWidth = +w + 3; c.setLineDash([]); c.beginPath(); for (const i of ids) for (let s = m.segStart[i]; s < m.segStart[i + 1]; s++) this._path(c, S[s * 5], S[s * 5 + 1], S[s * 5 + 2], S[s * 5 + 3]); c.stroke(); }
      c.strokeStyle = color; c.lineWidth = +w; c.setLineDash(byp === '1' && !thin ? [Math.max(4, 3 * w), Math.max(3, 2 * w)] : []);
      c.beginPath();
      for (const i of ids) for (let s = m.segStart[i]; s < m.segStart[i + 1]; s++) this._path(c, S[s * 5], S[s * 5 + 1], S[s * 5 + 2], S[s * 5 + 3]);
      c.stroke();
      if (flow) {   // moving dashes driver -> sink show direction during replay
        c.strokeStyle = '#ffffffb0'; c.lineWidth = Math.max(1, +w * 0.45); c.setLineDash([3, 9]); c.lineDashOffset = -this.st.phase;
        c.beginPath(); for (const i of ids) if (m.directed[i]) for (let s = m.segStart[i]; s < m.segStart[i + 1]; s++) this._path(c, S[s * 5], S[s * 5 + 1], S[s * 5 + 2], S[s * 5 + 3]); c.stroke();
        c.lineDashOffset = 0;
      }
      c.setLineDash([]);
      if (arrows) {
        c.fillStyle = color;
        for (const i of ids) {
          if (!m.directed[i]) continue;
          for (let s = m.segStart[i]; s < m.segStart[i + 1]; s++) {
            const ax = this.st.manhattan ? this.X(S[s * 5 + 2]) : this.X(S[s * 5]), ay = this.st.manhattan ? this.Y(S[s * 5 + 1]) : this.Y(S[s * 5 + 1]);
            const bx = this.X(S[s * 5 + 2]), by = this.Y(S[s * 5 + 3]), len = Math.hypot(bx - ax, by - ay);
            if (len < 14) continue;
            const ang = Math.atan2(by - ay, bx - ax), a = 4 + +w, mx = bx - Math.cos(ang) * 2, my = by - Math.sin(ang) * 2;
            c.beginPath(); c.moveTo(mx, my); c.lineTo(mx - a * Math.cos(ang - 0.45), my - a * Math.sin(ang - 0.45)); c.lineTo(mx - a * Math.cos(ang + 0.45), my - a * Math.sin(ang + 0.45)); c.closePath(); c.fill();
          }
        }
      }
    }
  }

  _paintBundles(c, bundles, hover = false) {
    c.lineCap = 'round';
    const groups = new Map(), ws = this.st.wscale;
    for (const b of bundles) {
      const w = Math.max(0.6, strokePx(b.bits, ws));
      const key = b.st + '|' + (b.by * 2 > b.n ? 1 : 0) + '|' + Math.round(w * 2) / 2;
      let g = groups.get(key); if (!g) groups.set(key, g = []); g.push(b);
    }
    for (const [key, bs] of groups) {
      const [stv, byp, w] = key.split('|');
      if (hover) { c.strokeStyle = '#ffffff'; c.lineWidth = +w + 3; }
      else { c.strokeStyle = STATUS[+stv].color; c.lineWidth = +w; }
      c.setLineDash(byp === '1' && !hover ? [6, 4] : []);
      c.beginPath(); for (const b of bs) this._path(c, b.x1, b.y1, b.x2, b.y2); c.stroke();
      if (hover) { c.strokeStyle = STATUS[+stv].color; c.lineWidth = +w; c.beginPath(); for (const b of bs) this._path(c, b.x1, b.y1, b.x2, b.y2); c.stroke(); }
    }
    c.setLineDash([]);
  }

  /** local links as a density fill: one translucent cell per CELL_PX screen cell, alpha ∝ log2 of the bits in it */
  _paintDensity(c, L, hover = false) {
    if (!L.dens || !L.dens.length) return;
    const cell = L.cell, s = this.view.s, px = cell * s, levels = new Map();
    for (const d of L.dens) {
      const a = hover ? 1 : Math.min(0.55, 0.08 + 0.04 * Math.log2(1 + d.bits));
      const q = Math.round(a * 20) / 20; let g = levels.get(q); if (!g) levels.set(q, g = []); g.push(d);
    }
    const ga = c.globalAlpha;
    for (const [a, ds] of levels) {
      c.globalAlpha = ga * a; c.fillStyle = hover ? '#ffffff' : DENS_COLOR; c.beginPath();
      for (const d of ds) c.rect(this.X(d.gx * cell), this.Y((d.gy + 1) * cell), px, px);
      c.fill();
    }
    c.globalAlpha = ga;
  }

  _paintCut(c, cm) {
    const m = this.m, W = cm.Wn;
    c.lineCap = 'butt';
    const col = (r) => r > cm.limit ? '#ff3b3b' : r > cm.limit * 0.66 ? '#f2b134' : '#2fb3a8';
    for (let k = 0; k < cm.v.length; k++) {
      const bits = cm.v[k]; if (!bits) continue;
      const r = bits / cm.cap; if (r < 0.04) continue;
      const kx = Math.floor(k / cm.ny), j = k % cm.ny;
      c.strokeStyle = col(r); c.globalAlpha = Math.min(1, 0.35 + r); c.lineWidth = Math.max(2, Math.min(9, 2 + r * 6));
      c.beginPath(); c.moveTo(this.X(kx * W), this.Y(j * W)); c.lineTo(this.X(kx * W), this.Y(Math.min(m.H, (j + 1) * W))); c.stroke();
    }
    for (let k = 0; k < cm.hz.length; k++) {
      const bits = cm.hz[k]; if (!bits) continue;
      const r = bits / cm.cap; if (r < 0.04) continue;
      const ky = Math.floor(k / cm.nx), i = k % cm.nx;
      c.strokeStyle = col(r); c.globalAlpha = Math.min(1, 0.35 + r); c.lineWidth = Math.max(2, Math.min(9, 2 + r * 6));
      c.beginPath(); c.moveTo(this.X(i * W), this.Y(ky * W)); c.lineTo(this.X(Math.min(m.W, (i + 1) * W)), this.Y(ky * W)); c.stroke();
    }
    c.globalAlpha = 1;
  }

  // -------------------------------------------------------------------------------------------- picking
  _pickAt(px, py) {
    const m = this.m; if (!m) return null;
    const [x, y] = this.inv(px, py), tol = 6;
    const dist = (ax, ay, bx, by) => {   // screen distance from the cursor to a (possibly L-shaped) segment
      const seg = (x1, y1, x2, y2) => { const dx = x2 - x1, dy = y2 - y1, v = dx * dx + dy * dy, t = v ? Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / v)) : 0; return Math.hypot(px - x1 - t * dx, py - y1 - t * dy); };
      return this.st.manhattan ? Math.min(seg(this.X(ax), this.Y(ay), this.X(bx), this.Y(ay)), seg(this.X(bx), this.Y(ay), this.X(bx), this.Y(by))) : seg(this.X(ax), this.Y(ay), this.X(bx), this.Y(by));
    };
    const L = this._bundleCache;
    if (L?.bundles) {
      let best = null, bd = tol;
      for (const b of L.bundles) { const d = dist(b.x1, b.y1, b.x2, b.y2); if (d <= bd) { bd = d; best = b; } }
      if (best) return best.n === 1 ? { link: best.links[0] } : { bundle: best };
    } else {
      const vis = new Set(L?.links || this.visibleLinks());
      if (this.st.highlight) for (const i of this.st.highlight) vis.add(i);
      const g = segmentGrid(m), S = m.seg, r = Math.ceil((tol / this.view.s) / g.cell);
      let best = -1, bd = tol;
      const gx = Math.floor(x / g.cell), gy = Math.floor(y / g.cell);
      for (let ix = gx - r; ix <= gx + r; ix++) for (let iy = gy - r; iy <= gy + r; iy++) {
        for (const s of g.cells.get(iy * g.nx + ix) || []) {
          const i = m.segLink[s]; if (!vis.has(i)) continue;
          const d = dist(S[s * 5], S[s * 5 + 1], S[s * 5 + 2], S[s * 5 + 3]); if (d < bd) { bd = d; best = i; }
        }
      }
      if (best >= 0) return { link: best };
    }
    if (L?.dens?.length) {
      const gx = Math.floor(x / L.cell), gy = Math.floor(y / L.cell);
      const d = L.dens.find((q) => q.gx === gx && q.gy === gy);
      if (d) return d.n === 1 ? { link: d.links[0] } : { bundle: Object.assign(d, { dens: true }) };
    }
    const b = blockAt(m, x, y);
    return b >= 0 ? { block: b } : null;
  }
  _hover(px, py, e) {
    const p = this._pickAt(px, py);
    const hl = p?.link ?? -1, hb = p?.bundle || null;
    if (hl !== this._hoverLink || hb !== this._hoverBundle) { this._hoverLink = hl; this._hoverBundle = hb; this.draw(); }
    this.cv.style.cursor = p ? 'pointer' : 'grab';
    this.onHover(p, e);
  }
  _click(px, py) { this.onPick(this._pickAt(px, py)); }
}

/** top driver master / link class of a member list, e.g. 'ot_x_w10 cfg ×512' */
export function membersSummary(m, ids, k = 3) {
  const c = new Map();
  for (const i of ids) { const d = m.ends[i][0], key = `${d >= 0 ? (m.bmaster[d] || m.bname[d]) : '?'} ${m.rec.links[i].c}`; c.set(key, (c.get(key) || 0) + 1); }
  return [...c.entries()].sort((a, b) => b[1] - a[1]).slice(0, k).map(([t, n]) => `${t} ×${n}`).join(', ');
}

export function bundleText(m, b) {
  const head = b.dens ? `${b.n.toLocaleString()} local link${b.n === 1 ? '' : 's'} in this cell (density fill, not drawn as strokes)`
    : `bundle of ${b.n.toLocaleString()} parallel link${b.n === 1 ? '' : 's'} (ends = bit-weighted mean of the members' real ends; longest member hop ${fmtUm(b.maxSeg)})`;
  return `${head} · ${fmtBits(b.bits)} total${b.by ? ` · ${b.by} bypass` : ''}${b.dens ? ` · longest ${fmtUm(b.maxL)}` : ''} · ${membersSummary(m, b.links)}${b.links.length < b.n ? ` (of first ${b.links.length})` : ''}`;
}

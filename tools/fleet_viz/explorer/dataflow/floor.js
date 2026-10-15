// Canvas floorplan of one die revision with its data-flow links. Blocks to scale (DEF µm, y up), links pin to pin
// (or along their register hops), width ∝ log2(bits), colour = reach verdict, dashed = bypasses unrelated blocks.
// Zoomed out, links are aggregated into spatial bundles (one stroke per pair of screen bins) so 100k+ links stay smooth.
import { STATUS, BYPASS_COLOR, widthPx, segmentGrid, blockAt, fmtBits } from './model.js';

const DPR = () => Math.min(2, window.devicePixelRatio || 1);
const RANK = [0, 1, 2, -1];   // worst-status ordering for bundles (unknown lowest)

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
      manhattan: false, cut: null, bypassOnly: false, filter: null, flow: false, phase: 0, minBits: 0 };
    this._bind(); this._ro = new ResizeObserver(() => this.resize()); this._ro.observe(el);
  }
  destroy() { this._ro.disconnect(); cancelAnimationFrame(this._raf); this.el.replaceChildren(); }
  setModel(m) { this.m = m; this.baseDirty = true; this._bundleCache = null; this.fit(); }
  set(patch) {
    Object.assign(this.st, patch);
    if ('lit' in patch || 'selBlock' in patch) this._litDirty = true;
    if ('active' in patch || 'filter' in patch || 'bypassOnly' in patch || 'minBits' in patch || 'mode' in patch) this._bundleCache = null;
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
    this._moving = true; this._bundleCache = null; this.draw();
    clearTimeout(this._settle); this._settle = setTimeout(() => { this._moving = false; this.baseDirty = true; this.draw(); }, 140);
  }

  // -------------------------------------------------------------------------------------------- visible link set
  visibleLinks() {
    const m = this.m, st = this.st;
    let list = st.mode === 'replay' ? (st.active || new Int32Array(0)) : null;
    const [vx0, vy1] = this.inv(0, 0), [vx1, vy0] = this.inv(this.cw, this.ch), bb = m.bbox;
    const inView = (i) => !(bb[i * 4] > vx1 || bb[i * 4 + 2] < vx0 || bb[i * 4 + 1] > vy1 || bb[i * 4 + 3] < vy0);
    const keep = (i) => inView(i) && (!st.bypassOnly || m.cross[i] > 0) && (!st.minBits || m.bits[i] >= st.minBits) && (!st.filter || st.filter(i));
    if (!list) { const a = []; for (let i = 0; i < m.nl; i++) if (m.segStart[i + 1] > m.segStart[i] && keep(i)) a.push(i); return a; }
    return Array.from(list).filter(keep);
  }
  _segCount(list) { let n = 0; for (const i of list) n += this.m.segStart[i + 1] - this.m.segStart[i]; return n; }

  bundles(list) {
    const bin = 34 / this.view.s, m = this.m, S = m.fseg, map = new Map();
    for (const i of list) {
      for (let s = m.fStart[i]; s < m.fStart[i + 1]; s++) {
        const ax = Math.floor(S[s * 5] / bin), ay = Math.floor(S[s * 5 + 1] / bin), bx = Math.floor(S[s * 5 + 2] / bin), by = Math.floor(S[s * 5 + 3] / bin);
        if (ax === bx && ay === by) continue;
        const key = ax + ',' + ay + '>' + bx + ',' + by;
        let b = map.get(key);
        if (!b) map.set(key, b = { x1: 0, y1: 0, x2: 0, y2: 0, w: 0, bits: 0, n: 0, links: [], st: 3, by: 0 });
        const bt = S[s * 5 + 4] || m.bits[i] || 1;
        b.x1 += S[s * 5] * bt; b.y1 += S[s * 5 + 1] * bt; b.x2 += S[s * 5 + 2] * bt; b.y2 += S[s * 5 + 3] * bt; b.w += bt;
        b.bits += bt; b.n++; if (b.links.length < 400) b.links.push(i);
        if (RANK[m.status[i]] > RANK[b.st]) b.st = m.status[i];
        if (m.cross[i] > 0) b.by++;
      }
    }
    const out = [];
    for (const b of map.values()) { b.x1 /= b.w; b.y1 /= b.w; b.x2 /= b.w; b.y2 /= b.w; out.push(b); }
    out.sort((a, b) => a.bits - b.bits);
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
    const list = this._bundleCache?.list || this.visibleLinks();
    const segs = this._segCount(list);
    this.visibleCount = list.length; this.visibleSegs = segs;
    c.globalAlpha = hl ? 0.28 : 1;
    if (list.length > 2500 || segs > 24000) {
      if (!this._bundleCache || this._bundleCache.s !== this.view.s) this._bundleCache = { s: this.view.s, list, b: this.bundles(list) };
      this._paintBundles(c, this._bundleCache.b); this.lod = 'bundled';
    } else {
      this._bundleCache = { s: this.view.s, list, b: null };
      this._paintLinks(c, list, { arrows: segs < 2500, flow: st.flow && segs < 4000 }); this.lod = 'links';
    }
    c.globalAlpha = 1;
    if (hl) this._paintLinks(c, [...hl], { arrows: true, halo: true, flow: st.flow });
    if (this._hoverLink != null && this._hoverLink >= 0) this._paintLinks(c, [this._hoverLink], { arrows: true, halo: true });
    if (this._hoverBundle) this._paintBundles(c, [this._hoverBundle], true);
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
      const bits = m.bits[i], w = thin ? Math.max(0.6, widthPx(bits) * 0.5) : widthPx(bits);
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
    const groups = new Map();
    for (const b of bundles) {
      const w = hover ? 0 : Math.min(14, widthPx(b.bits) * (b.n > 1 ? 1.08 : 1));
      const key = b.st + '|' + (b.by ? 1 : 0) + '|' + Math.round(w * 2) / 2;
      let g = groups.get(key); if (!g) groups.set(key, g = []); g.push(b);
    }
    for (const [key, bs] of groups) {
      const [stv, byp, w] = key.split('|');
      if (hover) { c.strokeStyle = '#ffffff'; c.lineWidth = Math.min(16, widthPx(bs[0].bits)) + 3; }
      else { c.strokeStyle = STATUS[+stv].color; c.lineWidth = +w; }
      c.setLineDash(byp === '1' && !hover ? [6, 4] : []);
      c.beginPath(); for (const b of bs) this._path(c, b.x1, b.y1, b.x2, b.y2); c.stroke();
    }
    c.setLineDash([]);
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
    if (this.lod === 'bundled' && this._bundleCache?.b) {
      let best = null, bd = tol;
      for (const b of this._bundleCache.b) { const d = dist(b.x1, b.y1, b.x2, b.y2); if (d < bd) { bd = d; best = b; } }
      if (best) return { bundle: best };
    } else {
      const vis = new Set(this._bundleCache?.list || this.visibleLinks());
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

export function bundleText(m, b) {
  return `${b.n.toLocaleString()} link${b.n === 1 ? '' : 's'} bundled at this zoom (driver → sink flight lines) · ${fmtBits(b.bits)} total${b.by ? ` · ${b.by} bypass` : ''}`;
}

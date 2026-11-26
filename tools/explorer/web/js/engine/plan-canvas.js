// 2-D floorplan canvas: pan / zoom camera (world um, y up) and the two plan drawings (die plan, type plan).
// The drawings are pure functions of (context, transform, data, options), so the Overview thumbnails reuse them.
import { cssv, STATE_VAR, displayState } from '../core/dom.js';

export class PlanCanvas {
  constructor(host, { draw, onHover, onClick, onDblClick, onView }) {
    this.host = host; this.drawFn = draw; this.onHover = onHover || (() => {}); this.onClick = onClick || (() => {}); this.onDblClick = onDblClick || (() => {}); this.onView = onView || (() => {});
    this.cv = document.createElement('canvas'); this.cv.tabIndex = 0; this.cv.setAttribute('role', 'img'); this.cv.dataset.testid = 'plan-canvas';
    host.append(this.cv); this.g = this.cv.getContext('2d');
    this.world = [1, 1]; this.cam = null; this.raf = 0;
    const cv = this.cv; let drag = null;
    cv.addEventListener('pointerdown', (e) => { if (e.button !== 0) return; drag = { x: e.clientX, y: e.clientY, cx: this.cam.x, cy: this.cam.y, moved: false }; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove', (e) => {
      const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
      if (drag) { const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true; if (drag.moved) { this.cam.x = drag.cx + dx; this.cam.y = drag.cy + dy; cv.style.cursor = 'grabbing'; this.redraw(); this.onView(); } return; }
      this.onHover(...this.toWorld(mx, my), mx, my, e);
    });
    cv.addEventListener('pointerup', (e) => { const d = drag; drag = null; cv.style.cursor = ''; if (d && !d.moved) { const r = cv.getBoundingClientRect(); this.onClick(...this.toWorld(e.clientX - r.left, e.clientY - r.top), e); } });
    cv.addEventListener('pointercancel', () => { drag = null; cv.style.cursor = ''; });
    cv.addEventListener('pointerleave', () => this.onHover(null, null));
    cv.addEventListener('dblclick', (e) => { const r = cv.getBoundingClientRect(); this.onDblClick(...this.toWorld(e.clientX - r.left, e.clientY - r.top), e); });
    cv.addEventListener('wheel', (e) => {
      e.preventDefault(); const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
      this.zoomAt(mx, my, Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0016)));
    }, { passive: false });
    cv.addEventListener('keydown', (e) => {
      const step = 60;
      if (e.key === 'f' || e.key === 'F' || e.key === '0') this.fit();
      else if (e.key === '+' || e.key === '=') this.zoomAt(this.w / 2, this.h / 2, 1.4);
      else if (e.key === '-') this.zoomAt(this.w / 2, this.h / 2, 1 / 1.4);
      else if (e.key === 'ArrowLeft') { this.cam.x += step; this.redraw(); this.onView(); } else if (e.key === 'ArrowRight') { this.cam.x -= step; this.redraw(); this.onView(); }
      else if (e.key === 'ArrowUp') { this.cam.y += step; this.redraw(); this.onView(); } else if (e.key === 'ArrowDown') { this.cam.y -= step; this.redraw(); this.onView(); }
      else return;
      e.preventDefault();
    });
    this.ro = new ResizeObserver(() => { const had = this.cam && this.w; const c = had ? this.center() : null; this.measure(); if (c) this.setCenter(c[0], c[1], c[2]); else if (this.world) this.fit(true); this.redraw(); });
    this.ro.observe(host);
    this.measure();
  }
  measure() { const r = this.host.getBoundingClientRect(); this.w = Math.max(10, r.width); this.h = Math.max(10, r.height); }
  setWorld(w, keep) { this.world = w; if (!keep || !this.cam) this.fit(true); this.redraw(); }
  fit(silent) { const [W, H] = this.world, k = Math.min(this.w / W, this.h / H) * 0.93; this.cam = { k, x: (this.w - W * k) / 2, y: (this.h + H * k) / 2 }; this.minK = k / 4; this.redraw(); if (!silent) this.onView(); }
  zoomAt(mx, my, f) {
    const k = Math.max(this.minK || 1e-6, Math.min(400, this.cam.k * f)), r = k / this.cam.k;
    this.cam.x = mx - (mx - this.cam.x) * r; this.cam.y = my - (my - this.cam.y) * r; this.cam.k = k; this.redraw(); this.onView();
  }
  zoomTo(bb, pad = 0.6) { const w = Math.max(1, bb[2] - bb[0]), hh = Math.max(1, bb[3] - bb[1]); this.setCenter((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, Math.min(this.w / w, this.h / hh) * pad); this.onView(); }
  center() { return [(this.w / 2 - this.cam.x) / this.cam.k, (this.cam.y - this.h / 2) / this.cam.k, this.cam.k]; }
  setCenter(cx, cy, k) { this.cam = { k, x: this.w / 2 - cx * k, y: this.h / 2 + cy * k }; this.redraw(); }
  toWorld(mx, my) { return [(mx - this.cam.x) / this.cam.k, (this.cam.y - my) / this.cam.k]; }
  redraw() { if (!this.raf) this.raf = requestAnimationFrame(() => { this.raf = 0; this.paint(); }); }
  paint() {
    if (!this.cam) return;
    const dpr = Math.min(2, devicePixelRatio || 1), cv = this.cv;
    if (cv.width !== Math.round(this.w * dpr) || cv.height !== Math.round(this.h * dpr)) { cv.width = Math.round(this.w * dpr); cv.height = Math.round(this.h * dpr); cv.style.width = this.w + 'px'; cv.style.height = this.h + 'px'; }
    const g = this.g; g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, this.w, this.h);
    this.drawFn(g, transform(this.cam), { w: this.w, h: this.h });
  }
  destroy() { this.ro.disconnect(); cancelAnimationFrame(this.raf); this.cv.remove(); }
}
export const transform = (cam) => ({ k: cam.k, X: (x) => cam.x + x * cam.k, Y: (y) => cam.y - y * cam.k });
export const fitTransform = (W, H, w, h, pad = 0.94) => { const k = Math.min(w / W, h / H) * pad; return transform({ k, x: (w - W * k) / 2, y: (h + H * k) / 2 }); };

export function placeChild(ox, oy, o, W, H, x, y, w, h) {
  if (o === 'MY') x = W - x - w; else if (o === 'MX') y = H - y - h; else if (o === 'R180') { x = W - x - w; y = H - y - h; }
  return [ox + x, oy + y];
}
export function sharedEdge(A, B) {
  const e = 1.0, [ax, ay, aw, ah] = A.slice(2, 6), [bx, by, bw, bh] = B.slice(2, 6);
  const ox0 = Math.max(ax, bx), ox1 = Math.min(ax + aw, bx + bw), oy0 = Math.max(ay, by), oy1 = Math.min(ay + ah, by + bh);
  if (Math.abs(ax + aw - bx) < e || Math.abs(bx + bw - ax) < e) { const x = Math.abs(ax + aw - bx) < e ? bx : ax; if (oy1 > oy0) return [x, oy0, x, oy1]; }
  if (Math.abs(ay + ah - by) < e || Math.abs(by + bh - ay) < e) { const y = Math.abs(ay + ah - by) < e ? by : ay; if (ox1 > ox0) return [ox0, y, ox1, y]; }
  return null;
}
const SWAP = new Set(['R90', 'R270', 'MXR90', 'MYR90']);
export const coreSize = (hc) => SWAP.has(hc[7]) ? [hc[6], hc[5]] : [hc[5], hc[6]];
function star(g, x, y, r, c) { g.fillStyle = c; g.beginPath(); for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * 0.45 : r; g.lineTo(x + rr * Math.cos(a), y + rr * Math.sin(a)); } g.closePath(); g.fill(); }
function palette() {
  const P = {}; for (const [s, v] of Object.entries(STATE_VAR)) P[s] = cssv(v);
  for (const k of ['--surface', '--surface-2', '--line', '--line-strong', '--ink', '--ink-2', '--ink-3', '--accent', '--seam', '--tree', '--pg', '--macro', '--core-fill', '--pin-in', '--pin-out', '--faint', '--select', '--canvas', '--ok', '--bad', '--warn', '--s-notbuilt']) P[k] = cssv(k);
  P.mono = cssv('--mono');
  return P;
}

/** die plan: partitions coloured by `colorOf(typeNode)`; opts: {ov:{seams,cores,clock,pg,names}, hide:Set(state), selType, selInst, hover, thumb} */
export function drawDiePlan(g, T, die, nodes, opts = {}) {
  const P = palette(), p = die.plan, ov = opts.ov || {}, { X, Y, k } = T;
  const rect = (x, y, w, h) => g.rect(X(x), Y(y + h), w * k, h * k);
  g.fillStyle = P['--surface']; g.strokeStyle = P['--line-strong']; g.lineWidth = 1;
  g.beginPath(); rect(0, 0, p.outline[0], p.outline[1]); g.fill(); g.stroke();
  const colorBy = opts.colorBy || 'state';
  const col = (t) => {
    if (colorBy === 'pack') return t && t.layout && t.layout.store ? P['--accent'] : P['--s-notbuilt'];
    if (colorBy === 'vis') { const v = t && t.vis && t.vis.verdict; return !v ? P['--s-notbuilt'] : /GOOD|PASS|OK/i.test(v) ? P['--ok'] : /BAD|FAIL/i.test(v) ? P['--bad'] : P['--warn']; }
    return P[displayState(t)] || P['not built'];
  };
  const hide = opts.hide || new Set(), sel = opts.selType, landing = opts.landing;
  for (const q of p.partitions) {
    const t = nodes[q[1]], st = displayState(t);
    let dim = hide.has(st) || (landing && (!t || t.plan.landing_base !== landing));
    const isSel = sel && (sel instanceof Set ? sel.has(q[1]) : q[1] === sel);
    g.globalAlpha = dim ? 0.1 : sel && !isSel ? 0.38 : 0.82; g.fillStyle = col(t);
    g.beginPath(); rect(q[2], q[3], q[4], q[5]); g.fill();
    g.globalAlpha = 1; g.strokeStyle = P['--surface']; g.lineWidth = opts.thumb ? 0.4 : 0.8; g.stroke();
  }
  if (ov.cores && k > 0.02 && !opts.thumb) {
    g.fillStyle = P['--core-fill']; g.globalAlpha = 0.22;
    const vx0 = -X(0) / k, vx1 = (opts.w - X(0)) / k, vy1 = Y(0) / k, vy0 = (Y(0) - opts.h) / k;
    for (const q of p.partitions) {
      if (q[2] > vx1 || q[2] + q[4] < vx0 || q[3] > vy1 || q[3] + q[5] < vy0) continue;
      const t = nodes[q[1]]; if (!t || !t.plan.hard_cores.length) continue;
      const [W, H] = t.plan.outline;
      for (const hc of t.plan.hard_cores) { const [w, hh] = coreSize(hc), [x, y] = placeChild(q[2], q[3], q[6], W, H, hc[3], hc[4], w, hh); g.fillRect(X(x), Y(y + hh), Math.max(0.6, w * k), Math.max(0.6, hh * k)); }
    }
    g.globalAlpha = 1;
  }
  if (ov.pg && p.pg_domains) { g.setLineDash([5, 4]); g.strokeStyle = P['--pg']; g.lineWidth = 1.2; for (const d of p.pg_domains) { const q = d.rect; g.beginPath(); rect(q[0], q[1], q[2] - q[0], q[3] - q[1]); g.stroke(); } g.setLineDash([]); }
  if (ov.seams && p.seams) {
    const idx = opts.partIndex || (opts.partIndex = Object.fromEntries(p.partitions.map((q) => [q[0], q])));
    g.strokeStyle = P['--seam'];
    for (const [a, b, bits] of p.seams) {
      const A = idx[a], B = idx[b]; if (!A || !B) continue;
      const s = sharedEdge(A, B); if (!s) continue;
      g.lineWidth = Math.min(4, 0.5 + 0.2 * Math.log2(1 + bits)); g.globalAlpha = 0.7;
      g.beginPath(); g.moveTo(X(s[0]), Y(s[1])); g.lineTo(X(s[2]), Y(s[3])); g.stroke();
    }
    g.globalAlpha = 1;
  }
  if (ov.clock && p.clock && p.clock.root) {
    const [cx, cy] = p.clock.root, W = p.outline[0], H = p.outline[1];
    if (p.clock.topology === 'htree') {   // topology sketch (first two H levels); the trunks are not routed yet
      g.strokeStyle = P['--tree']; g.globalAlpha = 0.75; g.lineWidth = 1.6; g.setLineDash([8, 4]);
      for (const [a, b] of [[[W / 4, cy], [3 * W / 4, cy]], [[W / 4, H / 4], [W / 4, 3 * H / 4]], [[3 * W / 4, H / 4], [3 * W / 4, 3 * H / 4]]]) { g.beginPath(); g.moveTo(X(a[0]), Y(a[1])); g.lineTo(X(b[0]), Y(b[1])); g.stroke(); }
      g.setLineDash([]); g.globalAlpha = 1;
    }
    star(g, X(cx), Y(cy), opts.thumb ? 5 : 9, P['--tree']);
  }
  // selection and hover rings on top
  const ring = (q, c, w) => { g.strokeStyle = c; g.lineWidth = w; g.beginPath(); rect(q[2], q[3], q[4], q[5]); g.stroke(); };
  if (sel) for (const q of p.partitions) if (sel instanceof Set ? sel.has(q[1]) : q[1] === sel) ring(q, P['--select'], q[0] === opts.selInst ? 3 : 1.4);
  if (opts.selInst) { const q = p.partitions.find((x) => x[0] === opts.selInst); if (q) { ring(q, P['--accent'], 3); } }
  if (opts.hover) ring(opts.hover, P['--ink'], 2);
  if (ov.names && !opts.thumb) {
    g.fillStyle = P['--ink']; g.font = '10px ' + P.mono; g.textBaseline = 'top';
    for (const q of p.partitions) { const w = q[4] * k; if (w > 54 && q[5] * k > 16) g.fillText(q[0].length * 6.1 > w - 6 ? q[0].slice(0, Math.max(1, Math.floor((w - 10) / 6.1))) + '…' : q[0], X(q[2]) + 3, Y(q[3] + q[5]) + 3); }
  }
}

const faceSeg = (face, win, W, H, inset = 0) => { const [a, b] = win; return face === 'N' ? [a, H - inset, b, H - inset] : face === 'S' ? [a, inset, b, inset] : face === 'E' ? [W - inset, a, W - inset, b] : [inset, a, inset, b]; };

/** type (or core) plan: outline, hard cores coloured by their own state, face buses, ft slots + stations, clock taps */
export function drawTypePlan(g, T, n, kids, opts = {}) {
  const P = palette(), { X, Y, k } = T, pl = n.plan, [W, H] = pl.outline || [10, 10], ov = opts.ov || {};
  const rect = (x, y, w, h) => g.rect(X(x), Y(y + h), w * k, h * k);
  g.fillStyle = P['--surface']; g.strokeStyle = P[displayState(n)] || P['--line-strong']; g.lineWidth = 2;
  g.beginPath(); rect(0, 0, W, H); g.fill(); g.stroke();
  if (ov.ft !== false) for (const s of pl.ft_slots || []) {
    g.strokeStyle = P['--faint']; g.lineWidth = 6; g.globalAlpha = 0.6;
    for (const [f, w] of [[s.in_face, s.in_window], [s.out_face, s.out_window]]) { if (!f || !w) continue; const q = faceSeg(f, w, W, H, 4 / k); g.beginPath(); g.moveTo(X(q[0]), Y(q[1])); g.lineTo(X(q[2]), Y(q[3])); g.stroke(); }
    g.globalAlpha = 1; g.fillStyle = P['--ink-2'];
    for (const r of s.regs || []) if (Array.isArray(r) && typeof r[0] === 'number') g.fillRect(X(r[0]) - 2.5, Y(r[1]) - 2.5, 5, 5);
  }
  for (const hc of pl.hard_cores || []) {
    const c = kids[hc[1]], st = c ? displayState(c) : null, [w, hh] = coreSize(hc);
    g.globalAlpha = 0.78; g.fillStyle = st ? P[st] : P['--s-notbuilt'];
    g.beginPath(); rect(hc[3], hc[4], w, hh); g.fill(); g.globalAlpha = 1;
    const hot = opts.hover === hc || (opts.selCore && hc[1] === opts.selCore);
    g.strokeStyle = hot ? P['--select'] : P['--macro']; g.lineWidth = hot ? 2.2 : 1; g.stroke();
    if (ov.names !== false && w * k > 64 && hh * k > 14) { g.fillStyle = P['--ink']; g.font = '10px ' + P.mono; g.textBaseline = 'top'; g.fillText(hc[2].slice(0, Math.floor(w * k / 6.2)), X(hc[3]) + 3, Y(hc[4] + hh) + 3); }
  }
  if (ov.buses !== false) for (const b of pl.buses || []) {
    if (!b[3] || !b[4]) continue; const q = faceSeg(b[3], b[4], W, H, 0);
    g.strokeStyle = P[b[1] === 'out' ? '--pin-out' : '--pin-in']; g.lineWidth = Math.min(7, 1.5 + 0.45 * Math.log2(1 + (b[2] || 1)));
    g.beginPath(); g.moveTo(X(q[0]), Y(q[1])); g.lineTo(X(q[2]), Y(q[3])); g.stroke();
  }
  if (ov.stations !== false) {
    g.strokeStyle = P['--accent']; g.globalAlpha = 0.55; g.lineWidth = 1;
    for (const s of pl.stations || []) { const [, a, b, regs] = s; if (!a || !b) continue; const pts = [a].concat((regs || []).filter(Array.isArray)).concat([b]); g.beginPath(); pts.forEach((q, i) => i ? g.lineTo(X(q[0]), Y(q[1])) : g.moveTo(X(q[0]), Y(q[1]))); g.stroke(); }
    g.globalAlpha = 1;
  }
  if (ov.clock !== false && pl.clock) {
    g.strokeStyle = P['--tree']; g.lineWidth = 1.2;
    for (const t of pl.clock.taps || []) if (t[2]) { const x = X(t[2][0]), y = Y(t[2][1]); g.beginPath(); g.moveTo(x - 3, y - 3); g.lineTo(x + 3, y + 3); g.moveTo(x + 3, y - 3); g.lineTo(x - 3, y + 3); g.stroke(); }
    if (pl.clock.tap) star(g, X(pl.clock.tap[0]), Y(pl.clock.tap[1]), 8, P['--tree']);
  }
}

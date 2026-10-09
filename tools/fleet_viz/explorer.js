/* OpenTallas Chip Explorer (fleet-viz /explorer).
   Die maps drawn from the exact placement the die recipes generate (explorer_geom.py -> /api/explorer/geom), every
   instance coloured by its element's closure status (/api/explorer/meta), a card for every element
   (/api/explorer/card) and the curated stories (/api/explorer/story, rendered by explorer_story.js).
   Rendering: one canvas; world units are um, y up.  Zoomed out, a pre-rendered overview bitmap of every instance is
   scaled; once fewer than LIMIT instances are in view they are drawn one by one (outlines, master labels, then
   instance names as they grow), found through a uniform grid index.  Hover and click hit-test through the same grid. */
(function(){
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt = (n, d = 1) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
const sgn = (n, d = 1) => n == null ? '—' : (n >= 0 ? '+' : '−') + fmt(Math.abs(n), d);
const SAFE = new URLSearchParams(location.search).get('safe') === '1';
const QS = SAFE ? 'safe=1&' : '';
const reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
const LIMIT = 30000;                 // most instances drawn one by one per frame
const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const ST_KEYS = ['closed', 'below', 'running', 'failing', 'revoked', 'superseded', 'placeholder', 'macro', 'relay'];
const ST_COL = {}; ST_KEYS.forEach(k => ST_COL[k] = cssv('--st-' + k));
const ST_SHORT = {closed: 'closed', below: 'closed < margin', running: 'running', failing: 'failing', revoked: 'revoked', superseded: 'superseded',
  placeholder: 'placeholder', macro: 'hard macro', relay: 'relay / wire stage'};
const JOB_COL = s => s === 'CLOSED' ? ST_COL.closed : ['RUNNING', 'QUEUED', 'READY', 'SYNC', 'ECO', 'MIGRATING'].includes(s) ? ST_COL.running
  : s === 'CANCELLED' ? ST_COL.superseded : /NEEDS|INVALID|REFUSED|FAIL/.test(s || '') ? ST_COL.failing : ST_COL.revoked;
const S = { meta: null, die: null, geo: {}, colour: 'status', sel: null, hover: -1, bus: true, view: null, focus: null, card: null, loading: {} };
const cv = $('map'), ctx = cv.getContext('2d');
let CW = 0, CH = 0, DPR = 1;

async function getJSON(u){ const r = await fetch(u, {cache: 'no-store'}); if (!r.ok) throw new Error(r.status + ' ' + u); return r.json(); }
function hash(){ const o = {}; (location.hash || '').replace(/^#/, '').split('&').forEach(p => { const i = p.indexOf('='); if (i > 0) o[decodeURIComponent(p.slice(0, i))] = decodeURIComponent(p.slice(i + 1)); }); return o; }
function setHash(o){ const s = Object.entries(o).filter(([k, v]) => v != null && v !== '').map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v)).join('&');
  try { history.replaceState(null, '', location.pathname + location.search + (s ? '#' + s : '')); } catch (e) {} }
function hue(s){ let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h % 360; }
function kindCol(k){ return `hsl(${hue(k || 'x')} 62% 58%)`; }
function dot(s){ return `<span class="dot" style="background:${ST_COL[s] || ST_COL.placeholder}"></span>`; }
function badge(s, label){ return `<span class="bd" style="color:${ST_COL[s] || ST_COL.placeholder}"><i></i>${esc(label || ST_SHORT[s] || s)}</span>`; }
function when(t){ if (!t) return '—'; const d = new Date(t * 1000); return d.toLocaleString('en-US', {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false}); }
function ago(t){ if (!t) return ''; const s = Date.now() / 1000 - t; return s < 90 ? Math.round(s) + ' s ago' : s < 5400 ? Math.round(s / 60) + ' min ago' : s < 172800 ? (s / 3600).toFixed(1) + ' h ago' : Math.round(s / 86400) + ' d ago'; }

/* ------------------------------------------------------------------ meta */
async function loadMeta(){
  const m = await getJSON('/api/explorer/meta?' + QS);
  if (m.warming){ $('busy').textContent = 'Explorer is warming up (first element scan)…'; setTimeout(loadMeta, 3000); return; }
  const first = !S.meta; S.meta = m;
  S.elByName = new Map(m.elements.map(e => [e.element, e]));
  S.dieById = new Map(m.dies.map(d => [d.id, d]));
  renderDies(); renderTree(); buildSearch();
  if (first){
    const h = hash();
    let die = h.die && S.dieById.has(h.die) ? h.die : null;
    if (!die && h.element){ const e = S.elByName.get(h.element); if (e && Object.keys(e.dies).length) die = Object.keys(e.dies)[0]; else if (!e) die = dieOfMaster(h.element); }
    if (!die && h.master){ for (const d of m.dies){ if ((m.masters[d.id] || {})[h.master]){ die = d.id; break; } } }
    await setDie(die || (m.dies.find(d => d.insts) || m.dies[0]).id, false);
    if (h.element) selectElement(h.element, {zoom: true});
    else if (h.master) selectMaster(S.die, h.master, {zoom: true});
    if (h.story) openStory(h.story);
  } else if (S.die){
    const g = S.geo[S.die];
    if (g && g.key !== (S.dieById.get(S.die) || {}).key){ delete S.geo[S.die]; await setDie(S.die, true); }
    else if (g){ recolour(g); draw(); }
  }
}
function renderDies(){
  $('dies').innerHTML = S.meta.dies.map(d => {
    const t = S.meta.tree.find(x => x.id === d.id) || {};
    return `<button type="button" data-die="${esc(d.id)}" aria-pressed="${d.id === S.die}" title="${esc(d.tool || d.label)}">${esc(d.label)}<small>${t.total ? `${t.closed}/${t.total}` : (d.exporting ? 'exporting' : '')}</small></button>`;
  }).join('');
  $('dies').querySelectorAll('button').forEach(b => b.onclick = () => setDie(b.dataset.die, true));
}

/* ------------------------------------------------------------------ geometry */
async function setDie(id, keepSel){
  S.die = id; renderDies(); renderTree();
  const d = S.dieById.get(id);
  $('busy').hidden = false;
  $('busy').textContent = d && d.exporting ? `Exporting ${d.label} from its recipe (a few minutes)…` : `Loading ${d ? d.label : id}…`;
  let g = S.geo[id];
  if (!g){
    try {
      const rec = await getJSON(`/api/explorer/geom?${QS}die=${encodeURIComponent(id)}`);
      g = S.geo[id] = prep(rec);
    } catch (e){
      $('busy').textContent = (d && d.exporting) ? `Exporting ${d.label} from its recipe; the map appears when it is done.` : `No geometry for ${id} yet (${e.message}).` + (d && d.error ? ' Last export error: ' + d.error : '');
      draw(); return;
    }
  }
  if (S.die !== id) return;
  $('busy').hidden = true;
  recolour(g); S.view = fitView(g); S.moved = false; S.hover = -1;
  if (S.sel && keepSel !== false){ const s = S.sel; S.sel = null; if (s.element) selectElement(s.element, {zoom: false, keepCard: true}); else if (s.master && s.die === id) selectMaster(id, s.master, {zoom: false}); }
  else if (keepSel === false){ /* initial */ }
  dieInfo(); legend(); draw();
  if (!S.sel) setHash({die: id});
}
function prep(rec){
  const n = rec.inst.name.length, I = rec.inst;
  const g = {rec, n, W: rec.W, H: rec.H, key: rec.key, x: Float64Array.from(I.x), y: Float64Array.from(I.y), w: Float64Array.from(I.w), h: Float64Array.from(I.h),
    m: Int32Array.from(I.m), k: Int32Array.from(I.k), r: Int32Array.from(I.r), names: I.name, masters: rec.masters, kinds: rec.kinds};
  let W = g.W, H = g.H;
  for (let i = 0; i < n; i++){ W = Math.max(W, g.x[i] + g.w[i]); H = Math.max(H, g.y[i] + g.h[i]); }
  g.W = W; g.H = H;
  g.mIndex = new Map(); rec.masters.forEach((m, i) => { if (!g.mIndex.has(m.name)) g.mIndex.set(m.name, i); });
  g.byMaster = rec.masters.map(() => []); for (let i = 0; i < n; i++) g.byMaster[g.m[i]].push(i);
  // uniform grid
  const G = 110, cs = Math.max(W, H) / G, gw = Math.ceil(W / cs) + 1, gh = Math.ceil(H / cs) + 1;
  const cells = new Array(gw * gh); for (let c = 0; c < cells.length; c++) cells[c] = [];
  const big = [];
  for (let i = 0; i < n; i++){
    const x0 = Math.max(0, Math.floor(g.x[i] / cs)), x1 = Math.min(gw - 1, Math.floor((g.x[i] + g.w[i]) / cs));
    const y0 = Math.max(0, Math.floor(g.y[i] / cs)), y1 = Math.min(gh - 1, Math.floor((g.y[i] + g.h[i]) / cs));
    if ((x1 - x0 + 1) * (y1 - y0 + 1) > 64){ big.push(i); continue; }
    for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) cells[cy * gw + cx].push(i);
  }
  Object.assign(g, {cs, gw, gh, cells, big, stamp: new Uint32Array(n), sv: 0});
  // draw order: big first so small instances inside a big one stay visible
  g.area = new Float64Array(n); for (let i = 0; i < n; i++) g.area[i] = g.w[i] * g.h[i];
  // bus adjacency
  const nb = rec.buses.length, cnt = new Int32Array(n + 1);
  for (let j = 0; j < nb; j++) for (const id of rec.buses[j][2]) if (id >= 0) cnt[id + 1]++;
  for (let i = 0; i < n; i++) cnt[i + 1] += cnt[i];
  const adj = new Int32Array(cnt[n]), fill = cnt.slice(0, n);
  for (let j = 0; j < nb; j++) for (const id of rec.buses[j][2]) if (id >= 0) adj[fill[id]++] = j;
  g.adjS = cnt; g.adj = adj;
  g.col = new Uint8Array(n); g.st = new Uint8Array(n); g.mst = [];
  return g;
}
function recolour(g){
  const ms = (S.meta.masters || {})[S.die] || {};
  g.mst = g.masters.map(m => (ms[m.name] || {}).s || 'placeholder');
  const kinds = g.kinds;
  if (S.colour === 'status'){ g.pal = ST_KEYS.map(k => ST_COL[k]); for (let i = 0; i < g.n; i++) g.col[i] = ST_KEYS.indexOf(g.mst[g.m[i]]); }
  else { g.pal = kinds.map(kindCol); for (let i = 0; i < g.n; i++) g.col[i] = g.k[i]; }
  for (let i = 0; i < g.n; i++) g.st[i] = ST_KEYS.indexOf(g.mst[g.m[i]]);
  buildBitmap(g);
}
function buildBitmap(g){
  const maxPx = 3200, sc = maxPx / Math.max(g.W, g.H);
  const c = document.createElement('canvas'); c.width = Math.ceil(g.W * sc); c.height = Math.ceil(g.H * sc);
  const x = c.getContext('2d'); x.fillStyle = '#0a0f1d'; x.fillRect(0, 0, c.width, c.height);
  const all = []; for (let i = 0; i < g.n; i++) all.push(i);
  rects(x, g, all, sc, 0, g.H, 0.9, false);
  g.bmp = {c, sc};
}
function fitView(g){ if (!CW || !CH) measure(); const s = Math.min(CW / g.W, CH / g.H) * 0.93; return {s, vx: g.W / 2 - CW / 2 / s, vy: g.H / 2 + CH / 2 / s}; }

/* ------------------------------------------------------------------ drawing */
function measure(){
  DPR = Math.min(2, window.devicePixelRatio || 1); const r = cv.getBoundingClientRect();
  CW = Math.max(50, r.width); CH = Math.max(50, r.height);
  cv.width = Math.round(CW * DPR); cv.height = Math.round(CH * DPR);
}
function resize(){
  const old = {CW, CH}; measure();
  const g = S.geo[S.die];
  if (g && (!S.view || !S.moved || !(S.view.s > 0))) S.view = fitView(g);     // untouched view: keep the die fitted
  else if (S.view && old.CW){ S.view.vx += (old.CW - CW) / 2 / S.view.s; S.view.vy -= (old.CH - CH) / 2 / S.view.s; }
  draw();
}
function visible(g, v, pad = 0){
  const x0 = v.vx - pad, x1 = v.vx + CW / v.s + pad, y1 = v.vy + pad, y0 = v.vy - CH / v.s - pad;
  const out = []; const sv = ++g.sv;
  const inter = i => g.x[i] <= x1 && g.x[i] + g.w[i] >= x0 && g.y[i] <= y1 && g.y[i] + g.h[i] >= y0;
  for (const i of g.big) if (inter(i)){ out.push(i); g.stamp[i] = sv; }
  const cx0 = Math.max(0, Math.floor(x0 / g.cs)), cx1 = Math.min(g.gw - 1, Math.floor(x1 / g.cs));
  const cy0 = Math.max(0, Math.floor(y0 / g.cs)), cy1 = Math.min(g.gh - 1, Math.floor(y1 / g.cs));
  for (let cy = cy0; cy <= cy1; cy++) for (let cx = cx0; cx <= cx1; cx++){
    for (const i of g.cells[cy * g.gw + cx]){ if (g.stamp[i] === sv) continue; g.stamp[i] = sv; if (inter(i)) out.push(i); }
  }
  return out;
}
/* fill (and optionally outline) rects batched by colour; s = px per um, (vx, vy) the world top-left */
function rects(c, g, list, s, vx, vy, minPx, outline, palOverride){
  const pal = palOverride || g.pal, by = pal.map(() => []);
  for (const i of list){ const k = g.col[i]; (by[k] || by[0]).push(i); }
  for (let k = 0; k < by.length; k++){
    if (!by[k].length) continue;
    c.fillStyle = pal[k]; c.beginPath();
    for (const i of by[k]){
      const w = Math.max(minPx, g.w[i] * s), h = Math.max(minPx, g.h[i] * s);
      c.rect((g.x[i] - vx) * s, (vy - g.y[i] - g.h[i]) * s, w, h);
    }
    c.fill();
  }
  if (outline){
    c.strokeStyle = 'rgba(2,4,10,.75)'; c.lineWidth = 1; c.beginPath();
    for (const i of list){ const w = g.w[i] * s, h = g.h[i] * s; if (w < 7 || h < 7) continue; c.rect((g.x[i] - vx) * s + .5, (vy - g.y[i] - g.h[i]) * s + .5, w - 1, h - 1); }
    c.stroke();
  }
}
let raf = 0;
function draw(){ if (!raf) raf = requestAnimationFrame(() => { raf = 0; paint(); }); }
function lod(g){ const s = S.view.s; const dieW = g.W * s; return dieW < 1.6 * Math.max(CW, CH) ? 0 : s < 0.12 ? 1 : s < 0.6 ? 2 : 3; }
function paint(){
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  ctx.fillStyle = '#03050b'; ctx.fillRect(0, 0, CW, CH);
  const g = S.geo[S.die]; if (!g || !S.view){ hud(null); return; }
  const v = S.view, s = v.s;
  const X = x => (x - v.vx) * s, Y = y => (v.vy - y) * s;
  // die outline
  ctx.fillStyle = '#0a0f1d'; ctx.fillRect(X(0), Y(g.H), g.W * s, g.H * s);
  let list = null, nvis = 0;
  if (g.W * s > g.bmp.c.width * 0.8){ list = visible(g, v); nvis = list.length; if (list.length > LIMIT) list = null; }
  const dim = !!(S.sel || S.focus);
  if (!list){
    ctx.imageSmoothingEnabled = g.W * s < g.bmp.c.width;
    ctx.drawImage(g.bmp.c, X(0), Y(g.H), g.W * s, g.H * s);
  } else {
    list.sort((a, b) => g.area[b] - g.area[a]);
    rects(ctx, g, list, s, v.vx, v.vy, 0.8, true);
  }
  regions(g, X, Y);
  if (dim){
    ctx.fillStyle = 'rgba(3,5,11,.68)'; ctx.fillRect(0, 0, CW, CH);
    const pick = [];
    const src = list || (S.sel ? S.sel.insts : null);
    if (S.sel){ for (const i of (list || S.sel.insts)) if (S.sel.mask[i]) pick.push(i); }
    else if (S.focus != null){ const fk = ST_KEYS.indexOf(S.focus); const L = list || [...Array(g.n).keys()]; for (const i of L) if (g.st[i] === fk) pick.push(i); }
    rects(ctx, g, pick, s, v.vx, v.vy, S.sel ? 2.5 : 1.2, true);
    if (S.sel && S.bus) buses(g, X, Y);
    if (S.sel){ ctx.strokeStyle = cssv('--accent'); ctx.lineWidth = 1.4; ctx.beginPath();
      for (const i of pick){ const w = g.w[i] * s, h = g.h[i] * s; if (w < 3 && h < 3) continue; ctx.rect(X(g.x[i]) - 1, Y(g.y[i] + g.h[i]) - 1, w + 2, h + 2); } ctx.stroke(); }
  }
  if (list) labels(g, list, X, Y);
  if (S.hover >= 0){
    const i = S.hover; ctx.strokeStyle = '#fff'; ctx.lineWidth = 2;
    ctx.strokeRect(X(g.x[i]) - 1.5, Y(g.y[i] + g.h[i]) - 1.5, Math.max(3, g.w[i] * s) + 3, Math.max(3, g.h[i] * s) + 3);
  }
  scalebar(s);
  hud(g, nvis || g.n, list ? 'individual' : 'overview');
}
function regions(g, X, Y){
  const L = lod(g); const rs = g.rec.regions || [];
  ctx.save(); ctx.setLineDash([5, 4]); ctx.lineWidth = 1; ctx.strokeStyle = 'rgba(160,180,230,.22)';
  ctx.font = '600 11px ' + cssv('--mono'); ctx.fillStyle = 'rgba(200,214,245,.55)';
  for (const r of rs){
    const [x0, y0, x1, y1] = r.rect; const w = (x1 - x0) * S.view.s, h = (y1 - y0) * S.view.s;
    if (w < 24 || h < 24 || w > CW * 6) continue;
    ctx.strokeRect(X(x0), Y(y1), w, h);
    if (L >= 1 && w > 110 && h > 26){ const t = r.name || r.kind; if (t) ctx.fillText(clip(t, w - 8, 6.6), X(x0) + 4, Y(y1) + 13); }
  }
  ctx.restore();
}
function clip(t, px, cw){ const n = Math.floor(px / cw); return t.length <= n ? t : (n > 3 ? t.slice(0, n - 1) + '…' : ''); }
function mlabel(g, mi){ const n = g.masters[mi].name; return SAFE ? n : n.replace(/^(hfd|qfd|dsfd)_/, ''); }
function labels(g, list, X, Y){
  const s = S.view.s; const cand = [];
  for (const i of list){ const w = g.w[i] * s, h = g.h[i] * s; if (w >= 52 && h >= 13) cand.push(i); }
  cand.sort((a, b) => g.area[b] - g.area[a]);
  ctx.save(); ctx.textBaseline = 'top';
  let n = 0;
  for (const i of cand){
    if (n++ > 700) break;
    const w = g.w[i] * s, h = g.h[i] * s, x0 = X(g.x[i]), y0 = Y(g.y[i] + g.h[i]);
    if (x0 > CW || y0 > CH || x0 + w < 0 || y0 + h < 0) continue;
    // keep the label of a partly off-screen instance on screen (top-left of its visible part)
    const x = Math.max(x0, 0) + 3, y = Math.max(y0, 0) + 2; if (x0 + w - x < 40 || y0 + h - y < 13) continue;
    const big = w >= 150 && h >= 30;
    ctx.font = (big ? '600 12px ' : '600 10.5px ') + cssv('--mono');
    ctx.fillStyle = 'rgba(3,5,11,.9)';
    const t1 = clip(mlabel(g, g.m[i]), w - 6, big ? 7.3 : 6.4);
    if (!t1) continue;
    ctx.fillText(t1, x + .7, y + .7); ctx.fillStyle = '#f4f7ff'; ctx.fillText(t1, x, y);
    if (big && !SAFE && g.names[i]){ ctx.font = '10.5px ' + cssv('--mono'); const t2 = clip(g.names[i], w - 6, 6.4); ctx.fillStyle = 'rgba(3,5,11,.9)'; ctx.fillText(t2, x + .7, y + 15.7); ctx.fillStyle = '#c9d3ee'; ctx.fillText(t2, x, y + 15); }
  }
  ctx.restore();
}
function buses(g, X, Y){
  const sel = S.sel; if (!sel || !sel.insts.length) return;
  const B = g.rec.buses, cls = g.rec.bus_classes; let lines = 0;
  ctx.save(); ctx.globalAlpha = .85; ctx.lineCap = 'round';
  const cx = i => X(g.x[i] + g.w[i] / 2), cy = i => Y(g.y[i] + g.h[i] / 2);
  for (const i of sel.insts){
    for (let a = g.adjS[i]; a < g.adjS[i + 1]; a++){
      const b = B[g.adj[a]]; const ids = b[2]; if (ids.some(x => x < 0)) continue;
      ctx.strokeStyle = kindCol(cls[b[0]]); ctx.lineWidth = Math.min(5, .8 + Math.log2(b[1] + 1) / 3);
      ctx.beginPath();
      for (const k of ids){ if (k === i || sel.mask[k]) continue; ctx.moveTo(cx(i), cy(i)); ctx.lineTo(cx(k), cy(k)); lines++; }
      ctx.stroke();
      if (lines > 6000) { ctx.restore(); return; }
    }
  }
  ctx.restore();
}
function scalebar(s){
  const target = 120 / s; const p = Math.pow(10, Math.floor(Math.log10(target))); const L = [1, 2, 5, 10].map(k => k * p).filter(x => x <= target).pop() || p;
  const px = L * s, x = CW - 24 - px, y = CH - 66;
  ctx.fillStyle = 'rgba(232,238,252,.85)'; ctx.fillRect(x, y, px, 2); ctx.fillRect(x, y - 4, 1.5, 8); ctx.fillRect(x + px - 1.5, y - 4, 1.5, 8);
  ctx.font = '11px ' + cssv('--mono'); ctx.textAlign = 'center'; ctx.fillText(L >= 1000 ? (L / 1000) + ' mm' : L + ' µm', x + px / 2, y - 7); ctx.textAlign = 'left';
}
const LODN = ['die', 'regions / columns', 'masters', 'instances'];
function hud(g, nvis, mode){
  if (!g){ $('hud').textContent = ''; return; }
  const c = S.cursor;
  $('hud').innerHTML = `LOD ${lod(g)} · ${LODN[lod(g)]} · ${mode}<br>${fmt(1 / S.view.s, S.view.s > 1 ? 2 : 1)} µm/px · ${fmt(nvis, 0)} of ${fmt(g.n, 0)} in view` +
    (c ? `<br>x ${fmt(c[0], 1)} · y ${fmt(c[1], 1)} µm` : '');
}
function dieInfo(){
  const g = S.geo[S.die], d = S.dieById.get(S.die); if (!g || !d) { $('dinfo').innerHTML = ''; return; }
  const r = g.rec;
  $('dinfo').innerHTML = `<b>${esc(d.label)}</b> · ${fmt(g.W / 1000, 2)} × ${fmt(g.H / 1000, 2)} mm · ${fmt(g.n, 0)} instances · ${fmt(r.masters.length, 0)} masters · ${fmt(r.buses.length, 0)} buses` +
    (SAFE ? '' : `<br>recipe ${esc((r.recipe || {}).recipe || (r.recipe || {}).variant || '')} @ <span title="${esc(d.tool || '')}">${esc((r.commit || '').slice(0, 10))}</span> · exported ${esc((r.generated || '').slice(0, 16).replace('T', ' '))}` +
     (d.want && d.key && d.want !== d.key ? ' · <span style="color:var(--warn)">recipe changed, re-exporting</span>' : ''));
}
function legend(){
  const g = S.geo[S.die]; if (!g){ $('legend').innerHTML = ''; return; }
  if (S.colour === 'kind'){
    const c = new Map(); for (let i = 0; i < g.n; i++) c.set(g.k[i], (c.get(g.k[i]) || 0) + 1);
    $('legend').innerHTML = [...c.entries()].sort((a, b) => b[1] - a[1]).slice(0, 24).map(([k, n]) => `<span><i class="dot" style="background:${kindCol(g.kinds[k])}"></i>${esc(g.kinds[k] || '(none)')}<b>${fmt(n, 0)}</b></span>`).join('');
    return;
  }
  const ci = new Map(), cm = new Map();
  for (let i = 0; i < g.n; i++){ const s = ST_KEYS[g.st[i]]; ci.set(s, (ci.get(s) || 0) + 1); }
  g.mst.forEach(s => cm.set(s, (cm.get(s) || 0) + 1));
  $('legend').innerHTML = `<span style="color:var(--faint)">status<b style="color:var(--faint)">masters / insts</b></span>` + ST_KEYS.filter(k => ci.get(k)).map(k =>
    `<span data-st="${k}" title="${esc((S.meta.status_label || {})[k] || k)}; click to emphasise" style="cursor:pointer;${S.focus === k ? 'color:var(--ink)' : ''}"><i class="dot" style="background:${ST_COL[k]}"></i>${esc(ST_SHORT[k])}<b>${fmt(cm.get(k) || 0, 0)} / ${fmt(ci.get(k), 0)}</b></span>`).join('');
  $('legend').querySelectorAll('[data-st]').forEach(e => e.onclick = () => { S.focus = S.focus === e.dataset.st ? null : e.dataset.st; legend(); draw(); });
}

/* ------------------------------------------------------------------ interaction */
function toWorld(px, py){ return [S.view.vx + px / S.view.s, S.view.vy - py / S.view.s]; }
function zoomAt(px, py, f){
  const g = S.geo[S.die]; if (!g || !S.view) return;
  const [wx, wy] = toWorld(px, py); const smin = Math.min(CW / g.W, CH / g.H) * 0.4, smax = 40;
  const s = Math.max(smin, Math.min(smax, S.view.s * f));
  S.view = {s, vx: wx - px / s, vy: wy + py / s}; S.moved = true; draw();
}
function hit(px, py){
  const g = S.geo[S.die]; if (!g) return -1;
  const [wx, wy] = toWorld(px, py); const tol = 3 / S.view.s;
  const cx = Math.floor(wx / g.cs), cy = Math.floor(wy / g.cs);
  let best = -1, ba = Infinity;
  const test = i => { if (wx >= g.x[i] - tol && wx <= g.x[i] + g.w[i] + tol && wy >= g.y[i] - tol && wy <= g.y[i] + g.h[i] + tol && g.area[i] < ba){ best = i; ba = g.area[i]; } };
  for (let yy = cy - 1; yy <= cy + 1; yy++) for (let xx = cx - 1; xx <= cx + 1; xx++){ if (xx < 0 || yy < 0 || xx >= g.gw || yy >= g.gh) continue; for (const i of g.cells[yy * g.gw + xx]) test(i); }
  for (const i of g.big) test(i);
  return best;
}
let drag = null; const ptrs = new Map();
cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.offsetX, e.offsetY]); drag = {x: e.offsetX, y: e.offsetY, vx: S.view && S.view.vx, vy: S.view && S.view.vy, moved: false}; if (ptrs.size === 2) drag.pinch = pinchState(); });
cv.addEventListener('pointermove', e => {
  if (ptrs.has(e.pointerId)) ptrs.set(e.pointerId, [e.offsetX, e.offsetY]);
  if (drag && S.view){
    if (ptrs.size === 2 && drag.pinch){ const p = pinchState(); zoomAt(p.cx, p.cy, p.d / drag.pinch.d); drag.pinch = p; drag.moved = true; return; }
    const dx = e.offsetX - drag.x, dy = e.offsetY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
    if (drag.moved){ S.moved = true; cv.classList.add('drag'); S.view.vx = drag.vx - dx / S.view.s; S.view.vy = drag.vy + dy / S.view.s; hideTip(); draw(); return; }
  }
  if (!S.view) return;
  S.cursor = toWorld(e.offsetX, e.offsetY);
  const i = hit(e.offsetX, e.offsetY);
  if (i !== S.hover){ S.hover = i; draw(); }
  if (i >= 0) showTip(i, e); else { hideTip(); draw(); }
});
function pinchState(){ const p = [...ptrs.values()]; return {cx: (p[0][0] + p[1][0]) / 2, cy: (p[0][1] + p[1][1]) / 2, d: Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]) || 1}; }
cv.addEventListener('pointerup', e => {
  ptrs.delete(e.pointerId); cv.classList.remove('drag');
  if (drag && !drag.moved && ptrs.size === 0){ const i = hit(e.offsetX, e.offsetY); if (i >= 0) clickInst(i); }
  if (ptrs.size === 0) drag = null;
});
cv.addEventListener('pointerleave', () => { S.hover = -1; S.cursor = null; hideTip(); draw(); });
cv.addEventListener('wheel', e => { e.preventDefault(); const f = Math.exp(-Math.max(-60, Math.min(60, e.deltaY * (e.deltaMode ? 30 : 1))) * 0.0028); zoomAt(e.offsetX, e.offsetY, f); }, {passive: false});
cv.addEventListener('dblclick', e => zoomAt(e.offsetX, e.offsetY, 2.5));
$('zin').onclick = () => zoomAt(CW / 2, CH / 2, 1.8);
$('zout').onclick = () => zoomAt(CW / 2, CH / 2, 1 / 1.8);
$('zfit').onclick = () => { const g = S.geo[S.die]; if (g) animateTo(fitView(g)); };
$('bus').onclick = () => { S.bus = !S.bus; $('bus').setAttribute('aria-pressed', String(S.bus)); draw(); };
$('clr').onclick = () => clearSel();
document.querySelectorAll('[data-col]').forEach(b => b.onclick = () => { S.colour = b.dataset.col; document.querySelectorAll('[data-col]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); const g = S.geo[S.die]; if (g){ recolour(g); legend(); draw(); } });
window.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === '+' || e.key === '=') zoomAt(CW / 2, CH / 2, 1.5); else if (e.key === '-') zoomAt(CW / 2, CH / 2, 1 / 1.5);
  else if (e.key === '0'){ const g = S.geo[S.die]; if (g) animateTo(fitView(g)); } else if (e.key === 'Escape'){ if (!$('story').hidden) closeStory(); else clearSel(); }
});
function animateTo(t){
  if (reduceMotion || !S.view){ S.view = t; draw(); return; }
  const a = Object.assign({}, S.view), t0 = performance.now(), D = 380;
  const la = Math.log(a.s), lb = Math.log(t.s);
  // interpolate the world point at the canvas centre and the log scale
  const ca = [a.vx + CW / 2 / a.s, a.vy - CH / 2 / a.s], cb = [t.vx + CW / 2 / t.s, t.vy - CH / 2 / t.s];
  const step = now => { const f = Math.min(1, (now - t0) / D), e = f < .5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2;
    const s = Math.exp(la + (lb - la) * e), cx = ca[0] + (cb[0] - ca[0]) * e, cy = ca[1] + (cb[1] - ca[1]) * e;
    S.view = {s, vx: cx - CW / 2 / s, vy: cy + CH / 2 / s}; paint(); if (f < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
function zoomToInsts(g, ids){
  if (!ids.length) return; S.moved = true;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const i of ids){ x0 = Math.min(x0, g.x[i]); y0 = Math.min(y0, g.y[i]); x1 = Math.max(x1, g.x[i] + g.w[i]); y1 = Math.max(y1, g.y[i] + g.h[i]); }
  const w = Math.max(x1 - x0, 60), h = Math.max(y1 - y0, 60);
  const s = Math.min(40, Math.min(CW / w, CH / h) * 0.6, Math.max(Math.min(CW / g.W, CH / g.H) * 0.93, Math.min(CW / w, CH / h) * 0.6));
  animateTo({s, vx: (x0 + x1) / 2 - CW / 2 / s, vy: (y0 + y1) / 2 + CH / 2 / s});
}
const tip = $('tip');
function showTip(i, e){
  const g = S.geo[S.die], mi = g.m[i], m = g.masters[mi], ms = ((S.meta.masters || {})[S.die] || {})[m.name] || {};
  const st = g.mst[mi];
  tip.innerHTML = `<div class="n">${esc(SAFE ? m.name : g.names[i])}</div><div class="m">${esc(SAFE ? '' : m.name)}${m.n > 1 ? ` · ×${fmt(m.n, 0)}` : ''}</div>` +
    `<div class="r">${badge(st)}${ms.el && ms.el !== m.name ? `<span class="m">element ${esc(ms.el)}</span>` : ms.els && ms.els.length > 1 ? `<span class="m">${ms.els.length} elements</span>` : ''}</div>` +
    `<div class="m">${esc(g.kinds[g.k[i]] || '')}${g.rec.regions_names && g.rec.regions_names[g.r[i]] ? ' · ' + esc(g.rec.regions_names[g.r[i]]) : ''} · ${fmt(g.w[i], 1)} × ${fmt(g.h[i], 1)} µm @ (${fmt(g.x[i], 1)}, ${fmt(g.y[i], 1)})</div>`;
  tip.hidden = false; const pad = 14; let x = e.clientX + pad, y = e.clientY + pad; const r = tip.getBoundingClientRect();
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - pad; if (y + r.height > innerHeight - 8) y = e.clientY - r.height - pad;
  tip.style.left = Math.max(4, x) + 'px'; tip.style.top = Math.max(4, y) + 'px';
}
function hideTip(){ tip.hidden = true; }

/* ------------------------------------------------------------------ selection */
function setSel(die, masters, info){
  const g = S.geo[die]; if (!g) return;
  const mask = new Uint8Array(g.n), insts = [];
  for (const mi of masters) for (const i of g.byMaster[mi]){ if (!mask[i]){ mask[i] = 1; insts.push(i); } }
  S.sel = Object.assign({die, masters, mask, insts}, info);
  $('clr').hidden = false; renderTree(); draw();
}
function clearSel(){ S.sel = null; $('clr').hidden = true; S.card = null; $('card').innerHTML = '<div class="empty">Selection cleared. Click an instance or a hierarchy row.</div>'; renderTree(); setHash({die: S.die}); draw(); }
function clickInst(i){
  const g = S.geo[S.die], mi = g.m[i];
  selectMaster(S.die, g.masters[mi].name, {zoom: false, inst: i});
}
async function selectMaster(die, mname, o = {}){
  if (die !== S.die) await setDie(die, false);
  const g = S.geo[die]; if (!g) return;
  const mi = g.mIndex.get(mname); if (mi == null) return;
  const ms = ((S.meta.masters || {})[die] || {})[mname] || {};
  setSel(die, [mi], {master: mname, element: ms.el || null, inst: o.inst});
  if (o.zoom) zoomToInsts(g, S.sel.insts);
  setHash({die, master: ms.el ? null : mname, element: ms.el || null});
  loadCard(SAFE ? {die, mi} : {die, master: mname});
}
function dieOfMaster(name){ for (const d of S.meta.dies){ if (((S.meta.masters || {})[d.id] || {})[name]) return d.id; } return null; }
async function selectElement(el, o = {}){
  const e = S.elByName.get(el);
  if (!e){ const d = (S.geo[S.die] && ((S.meta.masters || {})[S.die] || {})[el]) ? S.die : dieOfMaster(el); if (d) return selectMaster(d, el, o); }
  const dies = e ? Object.keys(e.dies) : [];
  let die = dies.includes(S.die) ? S.die : dies[0];
  if (die && die !== S.die) await setDie(die, false);
  if (die){
    const g = S.geo[die];
    if (g){ const ms = e.dies[die].map(m => g.mIndex.get(m)).filter(x => x != null); setSel(die, ms, {element: el}); if (o.zoom) zoomToInsts(g, S.sel.insts); }
  } else { S.sel = null; $('clr').hidden = false; renderTree(); draw(); }
  setHash({die: S.die, element: el});
  if (!o.keepCard) loadCard(SAFE ? null : {element: el});
}

/* ------------------------------------------------------------------ card */
async function loadCard(q){
  if (!q){ $('card').innerHTML = '<div class="empty">In the share-safe view, cards open from the die map.</div>'; return; }
  const u = '/api/explorer/card?' + QS + Object.entries(q).map(([k, v]) => k + '=' + encodeURIComponent(v)).join('&');
  $('card').innerHTML = '<div class="empty">Loading card…</div>';
  try { const c = await getJSON(u); S.card = c; renderCard(c); $('right').scrollTop = 0; }
  catch (e){ $('card').innerHTML = `<div class="empty">Card failed: ${esc(e.message)}</div>`; }
}
function interfaces(g, insts, mask){
  const B = g.rec.buses, cls = g.rec.bus_classes, peers = new Map(), seen = new Set();
  let total = 0;
  for (const i of insts){
    for (let a = g.adjS[i]; a < g.adjS[i + 1]; a++){
      const j = g.adj[a]; const b = B[j]; const ids = b[2];
      if (ids.some(x => x < 0)) continue;
      for (const k of ids){
        if (k === i || mask[k]) continue;
        const pm = g.masters[g.m[k]].name; let p = peers.get(pm);
        if (!p){ p = {m: pm, mi: g.m[k], bits: 0, n: 0, cls: new Set(), maxL: 0, minL: Infinity, buses: new Set()}; peers.set(pm, p); }
        const L = Math.abs(g.x[i] + g.w[i] / 2 - g.x[k] - g.w[k] / 2) + Math.abs(g.y[i] + g.h[i] / 2 - g.y[k] - g.h[k] / 2);
        if (!p.buses.has(j)){ p.buses.add(j); p.bits += b[1]; p.n++; }
        p.cls.add(cls[b[0]]); p.maxL = Math.max(p.maxL, L); p.minL = Math.min(p.minL, L);
      }
      if (!seen.has(j)){ seen.add(j); total += b[1]; }
    }
  }
  return {peers: [...peers.values()].sort((a, b) => b.bits - a.bits), total, nbus: seen.size};
}
function contained(g, i){
  // hard macros / other instances fully inside instance i (e.g. ROM macros of a field slot)
  const out = new Map(); const x0 = g.x[i], y0 = g.y[i], x1 = x0 + g.w[i], y1 = y0 + g.h[i];
  const v = {vx: x0, vy: y1, s: 1}; const save = [CW, CH]; CW = g.w[i]; CH = g.h[i];
  const L = visible(g, v); CW = save[0]; CH = save[1];
  for (const k of L){ if (k === i) continue; if (g.x[k] >= x0 - .01 && g.x[k] + g.w[k] <= x1 + .01 && g.y[k] >= y0 - .01 && g.y[k] + g.h[k] <= y1 + .01){ const n = g.masters[g.m[k]].name; out.set(n, (out.get(n) || 0) + 1); } }
  return [...out.entries()];
}
function renderCard(c){
  if (c.error || c.warming){ $('card').innerHTML = `<div class="empty">${esc(c.error || 'warming up')}</div>`; return; }
  const g = S.geo[S.die]; const sel = S.sel && S.sel.die === S.die ? S.sel : null;
  const st = c.s || (sel && g ? g.mst[sel.masters[0]] : 'placeholder');
  const d = S.dieById.get(S.die) || {};
  const H = [];
  H.push(`<div><h2>${esc(c.name)}</h2><div class="dec">${esc(c.decoded || '')}</div></div>`);
  H.push(`<div class="badges">${badge(st, c.category || ST_SHORT[st])}${c.target ? `<span class="chip">${esc(c.target)}</span>` : ''}${c.live ? `<span class="chip" style="color:var(--accent)">${c.live} live job${c.live > 1 ? 's' : ''}</span>` : ''}${c.owner ? `<span class="chip">${esc(c.owner)}</span>` : ''}</div>`);
  if (c.stories && c.stories.length) H.push(`<div class="sec storyl">${c.stories.map(s => `<button type="button" data-story="${esc(s.id)}"><b>${s.status === 'planned' ? 'Story planned: ' : 'Story: '}${esc(s.title || s.id)}</b><small>${esc((s.summary || '').slice(0, 160))}${(s.summary || '').length > 160 ? '…' : ''}</small></button>`).join('')}</div>`);
  if (c.purpose || c.role) H.push(`<div class="sec"><h3>What it is</h3>${c.purpose ? `<p>${esc(c.purpose)}</p>` : ''}${c.role ? `<p style="margin-top:6px"><b style="color:var(--dim);font-weight:600">Token path:</b> ${esc(c.role)}</p>` : ''}</div>`);
  // where
  const places = c.places || {};
  const pl = Object.entries(places).map(([die, ms]) => {
    const gg = S.geo[die]; const lab = (S.dieById.get(die) || {}).label || die;
    const rows = ms.map(p => { const mi = gg ? gg.mIndex.get(p.master) : null; const n = gg && mi != null ? gg.byMaster[mi].length : null;
      return `<tr class="cl" data-die="${esc(die)}" data-m="${esc(p.master)}"><td class="m">${dot(p.s)} ${esc(p.master)}</td><td class="n">${n == null ? '' : '×' + fmt(n, 0)}</td><td>${esc(p.src || '')}${p.view ? ' · view ' + esc(p.view) : ''}</td></tr>`; }).join('');
    return `<div style="margin-bottom:6px"><div style="font-size:12.5px;margin-bottom:3px"><button class="lnk" data-showdie="${esc(die)}">${esc(lab)}</button></div><table class="t"><tbody>${rows}</tbody></table></div>`;
  }).join('');
  H.push(`<div class="sec"><h3>Where it sits</h3>${pl || '<p class="note">Not placed on an exported die map: a sub-block hardened inside a die master, or not used by the current dies.</p>'}</div>`);
  if (sel && g && sel.insts.length){
    const ids = sel.insts.slice(0, 14);
    H.push(`<div class="sec"><h3>Instances on this die (${fmt(sel.insts.length, 0)})</h3><table class="t"><thead><tr><th>instance</th><th class="n">x µm</th><th class="n">y µm</th><th>region</th></tr></thead><tbody>${ids.map(i =>
      `<tr class="cl" data-inst="${i}"><td class="m">${esc(SAFE ? '#' + i : g.names[i])}</td><td class="n">${fmt(g.x[i], 1)}</td><td class="n">${fmt(g.y[i], 1)}</td><td class="m">${esc((g.rec.regions_names || [])[g.r[i]] || '')}</td></tr>`).join('')}</tbody></table>${sel.insts.length > ids.length ? `<p class="note">and ${fmt(sel.insts.length - ids.length, 0)} more, all highlighted on the map.</p>` : ''}</div>`);
    // physical
    const m0 = g.masters[sel.masters[0]]; const i0 = sel.insts[0];
    const totA = sel.insts.reduce((a, i) => a + g.area[i], 0);
    const inside = contained(g, i0).sort((a, b) => b[1] - a[1]).slice(0, 6);
    const a = c.area || {};
    H.push(`<div class="sec"><h3>Physical</h3><dl class="kv">
      <dt>outline</dt><dd>${fmt(g.w[i0], 2)} × ${fmt(g.h[i0], 2)} µm (${fmt(g.area[i0] / 1e6, 4)} mm²)</dd>
      <dt>on this die</dt><dd>${fmt(sel.insts.length, 0)} instance${sel.insts.length > 1 ? 's' : ''}, ${fmt(totA / 1e6, 3)} mm² (${fmt(100 * totA / (g.W * g.H), 2)} % of the die)</dd>
      ${a.die ? `<dt>routed block</dt><dd>die ${fmt(a.die, 0)} µm²${a.core ? ` · core ${fmt(a.core, 0)} µm²` : ''}${a.util != null ? ` · util ${fmt(100 * a.util, 1)} %` : ''}</dd>` : ''}
      ${inside.length ? `<dt>contains</dt><dd>${inside.map(([n, k]) => `${esc(n)} ×${k}`).join(', ')}</dd>` : ''}
      <dt>kind</dt><dd>${esc(m0.kind || g.kinds[g.k[i0]] || '—')}</dd>
      ${c.cycles_added != null ? `<dt>cycles added</dt><dd>${esc(String(c.cycles_added).slice(0, 320))}${String(c.cycles_added).length > 320 ? '…' : ''} (latest job spec)</dd>` : ''}
    </dl></div>`);
    // interfaces
    const itf = interfaces(g, sel.insts, sel.mask);
    if (itf.peers.length){
      const R = d.reach_um;
      H.push(`<div class="sec"><h3>Interfaces: ${fmt(itf.nbus, 0)} buses, ${fmt(itf.total, 0)} bits, ${itf.peers.length} peer masters</h3>
      <table class="t"><thead><tr><th>peer</th><th class="n">bits</th><th class="n">buses</th><th class="n">max µm</th><th class="n" title="cycles a wire of that length needs at the die reach ${R || '?'} µm (geometric, centre to centre)">cyc @${R || '?'}</th></tr></thead><tbody>${itf.peers.slice(0, 24).map(p =>
        `<tr class="cl" data-die="${esc(S.die)}" data-m="${esc(p.m)}" title="${esc([...p.cls].join(', '))}"><td class="m">${dot(g.mst[p.mi])} ${esc(p.m)}</td><td class="n">${fmt(p.bits, 0)}</td><td class="n">${fmt(p.n, 0)}</td><td class="n">${fmt(p.maxL, 0)}</td><td class="n" style="${R && p.maxL > R ? 'color:var(--warn)' : ''}">${R ? Math.max(1, Math.ceil(p.maxL / R)) : '—'}</td></tr>`).join('')}</tbody></table>
      <p class="note">Bus widths from the die netlist the recipe builds; lengths are Manhattan, centre to centre. Peers on relay / station masters are the register hops of the link; a cycle count above 1 at the die reach (${R || '?'} µm, ${esc(d.reach_note || '')}) needs that many register stages.</p></div>`);
    }
  }
  if (c.children && c.children.length) H.push(`<div class="sec"><h3>Hardened inside (${c.children.length})</h3><div>${c.children.map(k => `<button class="lnk m" data-el="${esc(k)}">${dot((c.child_status || {})[k] || 'placeholder')} ${esc(k)}</button>`).join('<br>')}</div></div>`);
  if (c.parents && c.parents.length) H.push(`<div class="sec"><h3>Part of</h3><div>${c.parents.map(k => `<button class="lnk m" data-pm="${esc(k)}">${esc(k)}</button>`).join('<br>')}</div></div>`);
  // closure
  const b = c.best || {};
  if (c.element && !SAFE){
    const ad = c.adopted || {};
    H.push(`<div class="sec"><h3>Closure</h3><dl class="kv">
      <dt>status</dt><dd>${esc(c.category || '')}${c.via ? ' (' + esc(c.via) + ')' : ''}</dd>
      <dt>best route</dt><dd>${b.job ? `${b.corner === 'TT' ? `TT <span class="${b.tt >= 0 ? 'p' : 'ng'}">${sgn(b.tt, 2)}</span>` : `SS <span class="${b.ss >= 0 ? 'p' : 'ng'}">${sgn(b.ss, 2)}</span>`} / FF <span class="${b.ff >= 0 ? 'p' : 'ng'}">${sgn(b.ff, 2)}</span> ps${b.corner === 'TT' && b.ss != null ? ` · SS sens ${sgn(b.ss, 1)}` : ''} · DRC ${b.drc == null ? '—' : b.drc}` : '—'}</dd>
      ${b.job ? `<dt>job</dt><dd>${esc(b.job)}</dd>` : ''}
      ${ad.commit ? `<dt>adopted</dt><dd>${esc(ad.commit)} on ${esc(ad.branch || '?')}${ad.record_to && ad.record_to.length ? `<br>view → ${ad.record_to.map(esc).join(', ')}` : ''}</dd>` : ''}
      ${c.closed_t ? `<dt>closed</dt><dd>${when(c.closed_t)} (${ago(c.closed_t)})</dd>` : ''}
      ${c.revoked ? `<dt>revoked</dt><dd>${esc(c.revoked.reason || c.revoked.verdict || '')}${c.revoked.ff != null ? ` (re-timed FF ${sgn(c.revoked.ff, 1)} ps)` : ''}</dd>` : ''}
      ${c.superseded ? `<dt>superseded</dt><dd>by ${esc(c.superseded.by)}: ${esc(c.superseded.reason || '')}</dd>` : ''}
      ${c.variants && c.variants.length ? `<dt>variants</dt><dd>${c.variants.map(esc).join(', ')}</dd>` : ''}
      ${c.latest ? `<dt>latest</dt><dd>${when(c.latest.t)} ${esc(c.latest.status)}: ${esc(c.latest.text)}</dd>` : ''}
    </dl></div>`);
  }
  const vw = c.views || {};
  const vrows = Object.entries(vw).flatMap(([die, ms]) => Object.entries(ms).map(([m, v]) => `<tr><td class="m">${esc(m)}</td><td>${esc(v.status || '')}${v.verdict ? ' · ' + esc(v.verdict) : ''}</td><td class="m">${esc(v.dir || (v.tiles || []).join(', '))}</td></tr>`));
  if (vrows.length && !SAFE) H.push(`<div class="sec"><h3>Die view</h3><table class="t"><tbody>${vrows.join('')}</tbody></table></div>`);
  if (c.history && c.history.length) H.push(historyHtml(c));
  if (!SAFE) H.push(`<p class="note">Card: closure from the fleet element table (elements.py) and the closure-loop job files; placement from the ${esc(d.label || S.die)} recipe export. <a href="#element=${encodeURIComponent(c.element || '')}" data-copy="1">link to this card</a></p>`);
  $('card').innerHTML = `<div class="card">${H.join('')}</div>`;
  bindCard();
}
function historyHtml(c){
  const js = c.history; const now = Date.now() / 1000;
  const t0 = Math.min(...js.map(j => j.created || now)), t1 = Math.max(now, ...js.map(j => j.updated || 0));
  const W = 420, rh = 9, H = js.length * rh + 22;
  const X = t => 4 + (W - 8) * (t - t0) / Math.max(1, t1 - t0);
  let svg = `<svg class="tl" viewBox="0 0 ${W} ${H}" role="img" aria-label="job timeline">`;
  js.forEach((j, k) => { const x = X(j.created || t0), x2 = Math.max(x + 2, X(['RUNNING', 'QUEUED', 'READY', 'SYNC', 'ECO'].includes(j.status) ? now : (j.updated || j.created || t0)));
    svg += `<rect x="${x.toFixed(1)}" y="${2 + k * rh}" width="${(x2 - x).toFixed(1)}" height="${rh - 3}" rx="1.5" fill="${JOB_COL(j.status)}"><title>${esc((j.name || '') + ' ' + j.status)}</title></rect>`;
    if (j.closed_t) svg += `<circle cx="${X(j.closed_t).toFixed(1)}" cy="${2 + k * rh + (rh - 3) / 2}" r="3" fill="#fff"/>`; });
  svg += `<text x="4" y="${H - 4}" fill="#8a97b8" font-size="10" font-family="ui-monospace,monospace">${esc(when(t0))}</text><text x="${W - 4}" y="${H - 4}" fill="#8a97b8" font-size="10" text-anchor="end" font-family="ui-monospace,monospace">now</text></svg>`;
  const rows = js.slice().reverse().map(j => {
    const sl = j.tt != null ? `TT ${sgn(j.tt, 1)}` : j.ss != null ? `SS ${sgn(j.ss, 1)}` : '';
    return SAFE ? `<li>${badge(j.status === 'CLOSED' ? 'closed' : 'placeholder', j.status)} ${when(j.created)}</li>`
      : `<li><span class="bd" style="color:${JOB_COL(j.status)}"><i></i>${esc(j.status)}</span> <b style="font:600 12px var(--mono)">${esc(j.name)}</b> <span class="note">${when(j.created)} → ${when(j.updated)}${j.host ? ' · ' + esc(j.host) : ''}${j.commit ? ' · ' + esc(j.commit) : ''}</span>
        ${sl || j.ff != null ? `<div style="font:12px var(--mono)">${sl}${j.ff != null ? ` / FF ${sgn(j.ff, 1)}` : ''} ps${j.drc != null ? ` · DRC ${j.drc}` : ''} · ${esc(j.corner)}</div>` : ''}
        ${j.reason ? `<div class="why">${esc(j.reason)}</div>` : ''}${j.failed_checks && j.failed_checks.length ? `<div class="why">checks failed: ${esc(j.failed_checks.join(', '))}</div>` : ''}
        ${j.purpose ? `<details><summary class="note" style="cursor:pointer">purpose${j.owner ? ' · ' + esc(j.owner) : ''}</summary><div class="why">${esc(j.purpose)}</div></details>` : ''}</li>`;
  }).join('');
  const live = js.filter(j => ['RUNNING', 'QUEUED', 'READY', 'SYNC', 'ECO', 'MIGRATING'].includes(j.status));
  return `<div class="sec"><h3>Closure history: ${js.length} job${js.length > 1 ? 's' : ''}${live.length ? `, ${live.length} live` : ''}</h3>${svg}<ul class="hist" style="margin-top:8px">${rows}</ul></div>`;
}
function bindCard(){
  const C = $('card');
  C.querySelectorAll('tr[data-m]').forEach(r => r.onclick = () => selectMaster(r.dataset.die, r.dataset.m, {zoom: true}));
  C.querySelectorAll('[data-showdie]').forEach(b => b.onclick = () => { const s = S.card; if (s && s.element) selectElement(s.element, {zoom: true, keepCard: true}); });
  C.querySelectorAll('tr[data-inst]').forEach(r => r.onclick = () => { const g = S.geo[S.die]; zoomToInsts(g, [+r.dataset.inst]); S.hover = +r.dataset.inst; });
  C.querySelectorAll('[data-el]').forEach(b => b.onclick = () => selectElement(b.dataset.el, {zoom: true}));
  C.querySelectorAll('[data-pm]').forEach(b => b.onclick = () => { for (const d of S.meta.dies){ if (((S.meta.masters || {})[d.id] || {})[b.dataset.pm]){ selectMaster(d.id, b.dataset.pm, {zoom: true}); return; } } });
  C.querySelectorAll('[data-story]').forEach(b => b.onclick = () => openStory(b.dataset.story));
  C.querySelectorAll('[data-copy]').forEach(a => a.onclick = e => { e.preventDefault(); const u = location.origin + location.pathname + location.search + '#' + (S.card.element ? 'element=' + encodeURIComponent(S.card.element) : 'die=' + S.die + '&master=' + encodeURIComponent(S.card.master || '')); try { navigator.clipboard.writeText(u); a.textContent = 'link copied'; } catch (err) {} });
}

/* ------------------------------------------------------------------ stories */
async function openStory(id){
  try {
    const c = await getJSON('/api/explorer/story?' + QS + 'id=' + encodeURIComponent(id));
    $('story').hidden = false;
    const sm = S.meta.story_meta || {};
    window.OTStory.render($('storyC'), c, sm.legend, sm.loop_src);
    const att = (c.attach || []).filter(a => S.elByName.has(a));
    if (att.length){ const p = document.createElement('p'); p.className = 'note'; p.style.marginTop = '12px';
      p.innerHTML = 'Elements: ' + att.map(a => `<button class="lnk m" data-el="${esc(a)}">${esc(a)}</button>`).join(', ');
      $('storyC').appendChild(p); p.querySelectorAll('[data-el]').forEach(b => b.onclick = () => { closeStory(); selectElement(b.dataset.el, {zoom: true}); }); }
    const h = hash(); h.story = id; setHash(h);
  } catch (e){ alert('story: ' + e.message); }
}
function closeStory(){ $('story').hidden = true; $('storyC').innerHTML = ''; const h = hash(); delete h.story; setHash(h); }
$('storyX').onclick = closeStory;
$('story').addEventListener('click', e => { if (e.target === $('story')) closeStory(); });

/* ------------------------------------------------------------------ tree */
const OPEN = new Set();
function renderTree(){
  const m = S.meta; if (!m) return;
  const selM = S.sel ? new Set(S.sel.masters.map(mi => (S.geo[S.sel.die] || {masters: []}).masters[mi].name)) : new Set();
  const H = m.tree.map(t => {
    const cur = t.id === S.die; const open = cur || OPEN.has(t.id);
    const c = t.counts || {}; const tot = Object.values(c).reduce((a, b) => a + b, 0) || 1;
    const bar = ST_KEYS.filter(k => c[k]).map(k => `<i style="width:${100 * c[k] / tot}%;background:${ST_COL[k]}" title="${esc(ST_SHORT[k])}: ${c[k]}"></i>`).join('');
    let body = '';
    if (open){
      body = t.groups.map(gp => {
        const gk = t.id + '/' + gp.name, go = OPEN.has(gk) || (cur && S.sel && gp.items.some(i => selM.has(i.m)));
        const cc = gp.counts || {}; const closed = (cc.closed || 0) + (cc.below || 0), all = gp.items.reduce((a, i) => a + (i.group ? 0 : 1), 0);
        const items = go ? gp.items.map(i => {
          if (i.group) return `<div class="item" style="cursor:default">${dot('relay')}<span class="n">${esc(i.m)}</span><small>${fmt(i.n, 0)} insts</small></div>`;
          const kids = i.kids && i.kids.length && (selM.has(i.m)) ? i.kids.map(k => { const e = S.elByName.get(k); return `<div class="item kid" data-el="${esc(k)}">${dot(e ? e.s : 'placeholder')}<span class="n">${esc(k)}</span></div>`; }).join('') : '';
          return `<div class="item${selM.has(i.m) && cur ? ' sel' : ''}" data-die="${esc(t.id)}" data-m="${esc(i.m)}" title="${esc(i.m)}">${dot(i.s)}<span class="n">${esc(SAFE ? i.m : i.m.replace(/^(hfd|qfd|dsfd)_/, ''))}</span><small>${i.kids && i.kids.length ? `+${i.kids.length} ` : ''}×${fmt(i.n, 0)}</small></div>` + kids;
        }).join('') : '';
        return `<div class="grp${go ? ' open' : ''}"><div class="gh" data-g="${esc(gk)}"><span class="car">▶</span>${esc(gp.name)}<span class="c">${all ? `${closed}/${all}` : fmt(gp.items[0] ? gp.items[0].n : 0, 0)}</span></div>${items}</div>`;
      }).join('');
    }
    return `<div class="die${cur ? ' cur' : ''}${open ? ' open' : ''}"><div class="dh" data-die="${esc(t.id)}"><span class="car">▶</span><b>${esc(t.label)}</b><span class="cnt">${t.total ? `${t.closed}/${t.total} closed` : '—'}</span><div class="bar">${bar}</div></div>${body}</div>`;
  }).join('');
  $('tree').innerHTML = H;
  const cur = m.tree.find(t => t.id === S.die);
  $('treeT').textContent = cur && cur.total ? `${cur.closed}/${cur.total}` : '';
  $('tree').querySelectorAll('.dh').forEach(e => e.onclick = () => { const id = e.dataset.die; if (id !== S.die) setDie(id, false); else { OPEN.has(id) ? OPEN.delete(id) : OPEN.add(id); renderTree(); } });
  $('tree').querySelectorAll('.gh').forEach(e => e.onclick = () => { const k = e.dataset.g; OPEN.has(k) ? OPEN.delete(k) : OPEN.add(k); renderTree(); });
  $('tree').querySelectorAll('.item[data-m]').forEach(e => e.onclick = () => selectMaster(e.dataset.die, e.dataset.m, {zoom: true}));
  $('tree').querySelectorAll('.item[data-el]').forEach(e => e.onclick = ev => { ev.stopPropagation(); selectElement(e.dataset.el, {zoom: true}); });
  // elements with no die master on any exported die
  const un = m.elements.filter(e => !Object.keys(e.dies).length);
  const byT = {}; un.forEach(e => (byT[e.target] = byT[e.target] || []).push(e));
  $('unplaced').innerHTML = un.length ? `<div class="ptitle" style="padding-left:0">Elements not on a die map (${un.length})</div>` + Object.entries(byT).map(([t, es]) =>
    `<details><summary>${esc(t)} (${es.length})</summary>${es.map(e => `<div class="item" style="padding-left:12px" data-uel="${esc(e.element)}" title="${esc(e.decoded)}">${dot(e.s)}<span class="n">${esc(e.element)}</span></div>`).join('')}</details>`).join('') : '';
  $('unplaced').querySelectorAll('[data-uel]').forEach(e => e.onclick = () => selectElement(e.dataset.uel, {zoom: false}));
}

/* ------------------------------------------------------------------ search */
let SIDX = [];
function buildSearch(){
  const m = S.meta; SIDX = [];
  for (const e of m.elements) SIDX.push({t: 'element', name: e.element, dec: e.decoded, s: e.s, key: (e.element + ' ' + e.decoded).toLowerCase()});
  const names = m.names || {};
  for (const d of m.dies){ const ms = m.masters[d.id] || {}; for (const [n, v] of Object.entries(ms)){ if (v.s === 'relay' && /rly|relay/.test(n)) continue; SIDX.push({t: 'master', die: d.id, name: n, dec: d.label, s: v.s, key: n.toLowerCase()}); } }
}
let sOn = 0, sRes = [];
$('q').addEventListener('input', () => search($('q').value));
$('q').addEventListener('focus', () => { if ($('q').value) search($('q').value); });
$('q').addEventListener('keydown', e => {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp'){ e.preventDefault(); sOn = Math.max(0, Math.min(sRes.length - 1, sOn + (e.key === 'ArrowDown' ? 1 : -1))); paintRes(); }
  else if (e.key === 'Enter'){ if (sRes[sOn]) pickRes(sRes[sOn]); } else if (e.key === 'Escape'){ $('sres').hidden = true; }
});
document.addEventListener('click', e => { if (!e.target.closest('.search')) $('sres').hidden = true; });
function search(q){
  q = q.trim().toLowerCase(); if (!q){ $('sres').hidden = true; return; }
  const words = q.split(/\s+/);
  const ok = k => words.every(w => k.includes(w));
  const el = SIDX.filter(x => x.t === 'element' && ok(x.key)).slice(0, 12);
  const ms = SIDX.filter(x => x.t === 'master' && ok(x.key)).slice(0, 10);
  const ins = [];
  const g = S.geo[S.die];
  if (g && !SAFE && q.length >= 3){ for (let i = 0; i < g.n && ins.length < 10; i++) if (ok(g.names[i].toLowerCase())) ins.push({t: 'inst', i, name: g.names[i], dec: g.masters[g.m[i]].name, s: g.mst[g.m[i]]}); }
  sRes = [...el, ...ms, ...ins]; sOn = 0; paintRes();
}
function paintRes(){
  if (!sRes.length){ $('sres').innerHTML = '<div class="h">no match</div>'; $('sres').hidden = false; return; }
  let last = '', H = '';
  sRes.forEach((r, k) => { if (r.t !== last){ H += `<div class="h">${r.t === 'element' ? 'elements' : r.t === 'master' ? 'die masters' : 'instances on this die'}</div>`; last = r.t; }
    H += `<button type="button" data-k="${k}" class="${k === sOn ? 'on' : ''}">${dot(r.s)}<span class="n">${esc(r.name)}</span><span class="d">${esc(r.dec || '')}</span></button>`; });
  $('sres').innerHTML = H; $('sres').hidden = false;
  $('sres').querySelectorAll('button').forEach(b => b.onclick = () => pickRes(sRes[+b.dataset.k]));
}
function pickRes(r){
  $('sres').hidden = true;
  if (r.t === 'element') selectElement(r.name, {zoom: true});
  else if (r.t === 'master') selectMaster(r.die, r.name, {zoom: true});
  else { const g = S.geo[S.die]; selectMaster(S.die, g.masters[g.m[r.i]].name, {zoom: false, inst: r.i}); zoomToInsts(g, [r.i]); S.hover = r.i; }
}

/* ------------------------------------------------------------------ boot */
if (SAFE){ $('safeb').hidden = false; $('back').href = '/?safe=1'; }
new ResizeObserver(resize).observe($('center'));
window.addEventListener('hashchange', () => { const h = hash();
  if (h.die && h.die !== S.die && !h.element && !h.master && S.dieById && S.dieById.has(h.die)){ setDie(h.die, false); return; }
  if (h.master && h.die && (!S.sel || S.sel.master !== h.master)){ selectMaster(h.die, h.master, {zoom: true}); return; }
  if (h.element && (!S.sel || S.sel.element !== h.element)) selectElement(h.element, {zoom: true}); else if (h.story && $('story').hidden) openStory(h.story); });
measure();
loadMeta().catch(e => { $('busy').textContent = 'Explorer failed to load: ' + e.message; });
setInterval(() => { if (!document.hidden) loadMeta().catch(() => {}); }, 60000);
})();

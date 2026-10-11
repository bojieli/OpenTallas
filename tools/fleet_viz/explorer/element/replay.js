/* Chip Explorer element page, Replay tab (anim-1011): the exact state of every placed flop, cycle by cycle, from a
   gate-level simulation of the routed netlist under the element's own exactness bench (tools/explorer_elem/trace_bench.py).
   Data: data/<element>.trace.json (opentallas.elem_trace.v1: window, exactness, register lanes, handshakes, chunk index)
   and data/<element>.trace/c*.bin (flop-xor-rle chunks of 256 cycles, zlib).  WebGL draws one rectangle per flop at
   its placed cell, coloured by its bit (value view) or by whether it changed this cycle (toggle view). */
(function(){
'use strict';
const X = () => window.OTX;
const R = {els: {}, mode: 'toggle', play: false, speed: 8, pos: 0, lane: null, fps: 0, frames: 0, fpsT: 0, last: 0, acc: 0, filter: ''};
window.OTXReplay = R;

/* ------------------------------------------------------------------ data */
async function load(E){
  if (R.els[E.id]) return R.els[E.id];
  const T = R.els[E.id] = {state: 'loading'};
  try {
    const r = await fetch('data/' + encodeURIComponent(E.id) + '.trace.json' + X().QS, {cache: 'no-store'});
    if (!r.ok){ T.state = r.status === 404 ? 'none' : 'error'; T.err = r.status; X().renderSide(); return T; }
    T.d = await r.json(); T.state = 'ok';
    const d = T.d;
    T.cycles = []; T.jumpAt = new Set();
    d.window.segments.forEach((s, k) => { if (k) T.jumpAt.add(T.cycles.length); for (let c = s[0]; c <= s[1]; c++) T.cycles.push(c); });
    T.chunks = d.state.chunks.slice().sort((a, b) => a.c0 - b.c0);
    T.cache = new Map(); T.N = d.state.n;
    T.flags = new Uint8Array(T.N);
    // placed rectangles: flop i -> its cell (leaf -> cell through the layout's hit index), ICGs from the clock tree nodes
    const cellOfLeaf = new Map(); for (let c = 0; c < E.n; c++){ const j = E.leafOf[c]; if (j >= 0) cellOfLeaf.set(j, c); }
    const rect = new Float32Array(T.N * 4); const L = E.d.clock_tt.leaves; let miss = 0;
    d.flops.forEach((f, i) => { const c = cellOfLeaf.get(f[0]);
      if (c != null){ rect.set([E.x[c], E.y[c], E.w[c], E.h[c]], i * 4); }
      else { const l = L[f[0]]; if (l){ rect.set([l[0] - .3, l[1] - .27, .6, .54], i * 4); } miss++; } });
    const nodes = E.d.clock_tt.nodes || []; const byName = new Map(nodes.map(n => [n[6], n]));
    (d.icgs || []).forEach((g, k) => { const n = byName.get(g.name); const i = d.flops.length + k; if (n) rect.set([n[0] - .6, n[1] - .5, 1.2, 1.0], i * 4); });
    T.rect = rect; T.rectMiss = miss;
    T.laneOf = new Int32Array(T.N).fill(-1); d.lanes.forEach((ln, k) => ln.flops.forEach(i => { T.laneOf[i] = k; }));
    R.pos = 0; await frameData(T, 0);
  } catch (e) { T.state = 'error'; T.err = String(e); }
  X().renderSide(); X().redrawAll();
  return T;
}
async function inflate(buf){
  const ds = new DecompressionStream('deflate');
  return new Response(new Blob([buf]).stream().pipeThrough(ds)).arrayBuffer();
}
async function chunk(T, k){
  if (T.cache.has(k)) return T.cache.get(k);
  const p = (async () => {
    const meta = T.chunks[k];
    const r = await fetch('data/' + encodeURIComponent(T.d.state.dir) + '/' + meta.file, {cache: 'force-cache'});
    const b = new Uint8Array(await inflate(await r.arrayBuffer()));
    const dv = new DataView(b.buffer); const N = dv.getUint32(4, true), c0 = dv.getUint32(8, true), n = dv.getUint32(12, true);
    const W = (N + 31) >>> 5; let o = 16;
    const snaps = [], chg = [];
    let cur = new Uint32Array(W); const nb = (N + 7) >>> 3;
    for (let i = 0; i < nb; i++) cur[i >>> 2] |= b[o + i] << (8 * (i & 3));
    o += nb; snaps.push(cur); chg.push(new Uint32Array(0));
    const vint = () => { let v = 0, s = 0, x; do { x = b[o++]; v += (x & 127) * Math.pow(2, s); s += 7; } while (x & 128); return v; };
    for (let t = 1; t < n; t++){
      const cnt = vint(); const idx = new Uint32Array(cnt); let p_ = -1;
      const nx = cur.slice();
      for (let j = 0; j < cnt; j++){ const g = vint(); const i = j === 0 ? g : p_ + 1 + g; idx[j] = i; p_ = i; nx[i >>> 5] ^= (1 << (i & 31)); }
      snaps.push(nx); chg.push(idx); cur = nx;
    }
    if (T.cache.size > 12) T.cache.delete(T.cache.keys().next().value);
    return {c0, n, snaps, chg};
  })();
  T.cache.set(k, p);
  return p;
}
function chunkIndex(T, cyc){ let lo = 0, hi = T.chunks.length - 1;
  while (lo < hi){ const m = (lo + hi + 1) >> 1; if (T.chunks[m].c0 <= cyc) lo = m; else hi = m - 1; } return lo; }
async function frameData(T, pos){
  const cyc = T.cycles[Math.max(0, Math.min(T.cycles.length - 1, pos))];
  const k = chunkIndex(T, cyc); const C = await chunk(T, k);
  const t = cyc - C.c0; if (t < 0 || t >= C.n) return;
  const s = C.snaps[t], ch = C.chg[t], f = T.flags, N = T.N, hl = R.lane;
  for (let i = 0; i < N; i++) f[i] = (s[i >>> 5] >>> (i & 31)) & 1;
  for (let j = 0; j < ch.length; j++) f[ch[j]] |= 2;
  if (hl != null) T.d.lanes[hl].flops.forEach(i => { f[i] |= 4; });
  T.cyc = cyc; T.snap = s; T.chg = ch; T.dirty = true;
  if (k + 1 < T.chunks.length && t > C.n - 64) chunk(T, k + 1);   // prefetch
}

/* ------------------------------------------------------------------ WebGL */
const VS = `#version 300 es
in vec2 a_c; in vec4 a_r; in float a_f;
uniform vec4 u_v; uniform vec2 u_sz; uniform float u_min;
flat out int v_f;
void main(){
  vec2 c = a_r.xy + a_r.zw * 0.5; vec2 hw = max(a_r.zw * 0.5 * u_v.z, vec2(u_min));
  vec2 p = vec2(u_v.x + c.x * u_v.z, u_v.y + (u_v.w - c.y) * u_v.z) + (a_c - 0.5) * 2.0 * hw;
  gl_Position = vec4(p.x / u_sz.x * 2.0 - 1.0, 1.0 - p.y / u_sz.y * 2.0, 0.0, 1.0); v_f = int(a_f);
}`;
const FS = `#version 300 es
precision mediump float; flat in int v_f; uniform int u_mode; uniform vec3 u_c1; uniform vec3 u_c0; uniform vec3 u_hot; uniform vec3 u_hl; out vec4 o;
void main(){
  bool v = (v_f & 1) != 0, t = (v_f & 2) != 0, h = (v_f & 4) != 0;
  vec3 c = u_mode == 0 ? (v ? u_c1 : u_c0) : (t ? u_hot : (v ? u_c1 * 0.35 + u_c0 * 0.65 : u_c0));
  if (h) c = t || v ? u_hl : mix(u_hl, u_c0, 0.55);
  o = vec4(c, 1.0);
}`;
function glFor(E, T){
  const P = E.pane;
  if (!P.gl){
    const cv = document.createElement('canvas'); cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none';
    P.div.insertBefore(cv, P.div.children[1]);
    const gl = cv.getContext('webgl2', {antialias: false, premultipliedAlpha: false, alpha: true});
    if (!gl){ P.gl = {err: 'WebGL2 is not available in this browser'}; return P.gl; }
    const sh = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o); if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o)); return o; };
    const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(pr);
    const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
    const q = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, q); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]), gl.STATIC_DRAW);
    const la = gl.getAttribLocation(pr, 'a_c'); gl.enableVertexAttribArray(la); gl.vertexAttribPointer(la, 2, gl.FLOAT, false, 0, 0);
    P.gl = {cv, gl, pr, vao, u: n => gl.getUniformLocation(pr, n), rb: gl.createBuffer(), fb: gl.createBuffer(), T: null};
  }
  const G = P.gl; if (G.err) return G;
  const gl = G.gl;
  if (G.T !== T){
    gl.bindVertexArray(G.vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, G.rb); gl.bufferData(gl.ARRAY_BUFFER, T.rect, gl.STATIC_DRAW);
    const ra = gl.getAttribLocation(G.pr, 'a_r'); gl.enableVertexAttribArray(ra); gl.vertexAttribPointer(ra, 4, gl.FLOAT, false, 0, 0); gl.vertexAttribDivisor(ra, 1);
    gl.bindBuffer(gl.ARRAY_BUFFER, G.fb); gl.bufferData(gl.ARRAY_BUFFER, T.flags, gl.DYNAMIC_DRAW);
    const fa = gl.getAttribLocation(G.pr, 'a_f'); gl.enableVertexAttribArray(fa); gl.vertexAttribPointer(fa, 1, gl.UNSIGNED_BYTE, false, 0, 0); gl.vertexAttribDivisor(fa, 1);
    G.T = T;
  }
  return G;
}
const rgbf = h => { h = h.replace('#', ''); if (h.length === 3) h = h.split('').map(x => x + x).join(''); return [0, 2, 4].map(i => parseInt(h.substr(i, 2), 16) / 255); };
R.draw = function(E){
  const T = R.els[E.id]; const P = E.pane;
  if (!T || T.state !== 'ok' || !E.view){ if (P.gl && P.gl.cv) P.gl.cv.hidden = true; if (!T) load(E); return; }
  const G = glFor(E, T); if (G.err) return;
  const gl = G.gl, cv = G.cv; cv.hidden = false;
  const r = P.cv.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
  if (cv.width !== Math.round(r.width * dpr) || cv.height !== Math.round(r.height * dpr)){ cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr); }
  gl.viewport(0, 0, cv.width, cv.height); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
  gl.useProgram(G.pr); gl.bindVertexArray(G.vao);
  if (T.dirty){ gl.bindBuffer(gl.ARRAY_BUFFER, G.fb); gl.bufferSubData(gl.ARRAY_BUFFER, 0, T.flags); T.dirty = false; }
  gl.uniform4f(G.u('u_v'), E.view.ox, E.view.oy, E.view.s, E.H); gl.uniform2f(G.u('u_sz'), r.width, r.height); gl.uniform1f(G.u('u_min'), 0.6);
  gl.uniform1i(G.u('u_mode'), R.mode === 'value' ? 0 : 1);
  const cs = X().cssv;
  gl.uniform3fv(G.u('u_c1'), rgbf(cs('--accent') || '#4e79a7')); gl.uniform3fv(G.u('u_c0'), rgbf(cs('--cellgrey') || '#555b6e'));
  gl.uniform3fv(G.u('u_hot'), rgbf('#f28e2b')); gl.uniform3fv(G.u('u_hl'), rgbf('#e15759'));
  gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, T.N);
  R.frames++;
};
R.hide = function(){ Object.values(X().S.els || []).forEach(E => { if (E.pane && E.pane.gl && E.pane.gl.cv) E.pane.gl.cv.hidden = true; }); };

/* ------------------------------------------------------------------ playback */
function primary(){ const S = X().S; const E = S.els.find(e => !e.err && !e.nolayout && R.els[e.id] && R.els[e.id].state === 'ok'); return E ? [E, R.els[E.id]] : [null, null]; }
async function seek(pos){
  const S = X().S; R.pos = pos;
  await Promise.all(S.els.filter(E => R.els[E.id] && R.els[E.id].state === 'ok').map(E => { const T = R.els[E.id]; return frameData(T, Math.min(pos, T.cycles.length - 1)); }));
  S.els.forEach(E => { if (!E.err && !E.nolayout) R.draw(E); });
  updateSide();
}
function tick(now){
  if (X().S.tab !== 'replay'){ R.play = false; return; }
  if (now - R.fpsT >= 1000){ R.fps = Math.round(R.frames * 1000 / Math.max(1, now - R.fpsT)); R.frames = 0; R.fpsT = now; window.__otxReplayFps = R.fps; const f = document.getElementById('rp-fps'); if (f) f.textContent = R.fps + ' fps'; }
  if (R.play){
    const [, T] = primary();
    if (T){ R.acc += (now - (R.last || now)) / 1000 * R.speed; const step = Math.floor(R.acc);
      if (step >= 1 && !R.busy){ R.acc -= step; R.busy = true; const np = R.pos + step >= T.cycles.length ? 0 : R.pos + step; seek(np).finally(() => { R.busy = false; }); } }
    else if (!R.busy) { const S = X().S; S.els.forEach(E => { if (!E.err && !E.nolayout) R.draw(E); }); }
  }
  R.last = now;
  requestAnimationFrame(tick);
}
R.bench = function(seconds){   // headless fps measurement: play at max speed for <seconds>, return mean fps
  R.speed = 60; R.play = true; R.frames = 0; R.fpsT = performance.now(); requestAnimationFrame(tick);
  return new Promise(res => setTimeout(() => { const f = R.fps; res(f); }, seconds * 1000));
};

/* ------------------------------------------------------------------ side panel */
const hexOf = (T, ln) => { if (ln.flops.length > 256) return null; let v = 0n;
  ln.flops.forEach((i, k) => { if ((T.snap[i >>> 5] >>> (i & 31)) & 1) v |= 1n << BigInt(ln.bits[k]); }); return v.toString(16); };
R.side = function(){
  const {esc, fmt, sec, S, SAFE} = X();
  const H = [];
  const ok = S.els.filter(E => !E.err && !E.nolayout);
  ok.forEach(E => { if (!R.els[E.id]) load(E); });
  for (const E of ok){
    const T = R.els[E.id];
    if (!T || T.state === 'loading'){ H.push(sec(esc(E.d.label), '<p class="note">Loading the replay&hellip;</p>')); continue; }
    if (T.state !== 'ok'){ H.push(sec(esc(E.d.label), `<p class="note">${T.state === 'none' ? 'No replay for this element yet: the gate-level replay runs after the element export (explorer_elem_export.py trace).' : 'Replay data could not be loaded (' + esc(T.err) + ').'}</p>`)); continue; }
    const d = T.d, w = d.window, x = d.exactness, st = d.state;
    const segs = w.segments.map(s => s[0] + '–' + s[1]).join(', ');
    H.push(sec(esc(E.d.label), `
      <p class="note" style="margin-top:0"><b>Source: gate-level simulation</b> of the routed netlist (zero delay, cycle-based; cells modelled from the liberty functions, macros by the bench's own model), driven by the element's exactness bench.
        ${x.pass ? '<span class="ok">Reproduces the RTL run</span> (same output transactions and bench verdict lines).' : '<span class="ng">Does NOT reproduce the RTL run</span>: ' + esc(JSON.stringify({payloads: x.output_payloads_equal, transactions: x.transactions_equal, verdict: x.bench_markers_equal}))}</p>
      <table class="t"><tbody>
        <tr><td>flops / ICGs traced</td><td class="n">${fmt(st.flops, 0)} / ${fmt(st.icgs, 0)}</td></tr>
        <tr><td>flops mapped to placed cells</td><td class="n">${fmt(d.mapping.mapped, 0)} of ${fmt(d.mapping.flops_db_leaves, 0)}</td></tr>
        <tr><td>latency L (first input → first output)</td><td class="n">${w.L == null ? '—' : fmt(w.L, 0) + ' cyc'}</td></tr>
        <tr><td>input spacing II</td><td class="n">${w.II == null ? '—' : fmt(w.II, 0) + ' cyc'}</td></tr>
        <tr><td>work unit</td><td class="n">${w.work_unit ? w.work_unit[0] + '–' + w.work_unit[1] + ' (' + fmt(w.work_unit_cycles, 0) + ' cyc)' : '—'}</td></tr>
        <tr><td>window</td><td class="n">${esc(segs)} (${fmt(w.cycles, 0)} cyc)</td></tr>
        <tr><td>trace size</td><td class="n">${fmt(st.bytes / 1e6, 2)} MB · ${fmt(st.bytes_per_1000_cycles / 1e3, 0)} kB per 1,000 cycles</td></tr>
      </tbody></table>
      <p class="note">${esc(w.choice || '')}${w.jumps && w.jumps.length ? ' · jumps after ' + w.jumps.map(j => j[0] + '→' + j[1]).join(', ') : ''}. ${esc(w.rule || '')}</p>`,
      SAFE ? '' : esc(d.bench || '')));
  }
  const [E0, T0] = primary();
  if (T0){
    H.push(sec('Playback', `
      <div class="ctl" style="flex-wrap:wrap;gap:6px">
        <button class="btn" id="rp-play" type="button">${R.play ? 'Pause' : 'Play'}</button>
        <button class="btn" id="rp-prev" type="button" aria-label="Previous cycle">&lsaquo;</button>
        <button class="btn" id="rp-next" type="button" aria-label="Next cycle">&rsaquo;</button>
        <select id="rp-speed" aria-label="Speed">${[1, 4, 8, 30, 60].map(v => `<option value="${v}" ${R.speed === v ? 'selected' : ''}>${v} cyc/s</option>`).join('')}</select>
        <select id="rp-mode" aria-label="View"><option value="toggle" ${R.mode === 'toggle' ? 'selected' : ''}>toggle view</option><option value="value" ${R.mode === 'value' ? 'selected' : ''}>value view</option></select>
        <span class="note" id="rp-fps" style="margin:0">${R.fps ? R.fps + ' fps' : ''}</span>
      </div>
      <input type="range" id="rp-pos" min="0" max="${T0.cycles.length - 1}" value="${R.pos}" style="width:100%;margin-top:8px" aria-label="Cycle">
      <div class="note" id="rp-cyc" style="margin:2px 0 6px"></div>
      <canvas id="rp-strip" style="width:100%;height:${Math.min(220, 18 * (T0.d.handshakes.length + 1) + 8)}px;display:block;background:var(--canvas);border-radius:6px;cursor:pointer" aria-label="Handshake lanes"></canvas>
      <p class="note">Toggle view: orange = the flop changed at this cycle's clock edge. Value view: lit = the flop holds 1. Lanes: handshake signals of the block's ports (valid / ready / level), ticks = accepted transactions.</p>`));
    H.push(sec('Register lanes', `<div class="ctl"><input id="rp-filter" type="search" placeholder="filter registers" value="${esc(R.filter)}" style="flex:1;min-width:0"></div>
      <div class="tw" style="max-height:380px;overflow:auto"><table class="t"><thead><tr><th>register</th><th class="n">bits</th><th class="n">changed</th><th>value</th></tr></thead><tbody id="rp-lanes"></tbody></table></div>
      <p class="note">${fmt(T0.d.lanes.length, 0)} lanes: placed flops grouped by their synthesis register name. Click one to light its flops.</p>`));
  }
  return H.join('');
};
R.bindSide = function(){
  const $ = id => document.getElementById(id);
  const [, T] = primary(); if (!T) return;
  $('rp-play').onclick = () => { R.play = !R.play; $('rp-play').textContent = R.play ? 'Pause' : 'Play'; R.last = 0; if (R.play) requestAnimationFrame(tick); };
  $('rp-prev').onclick = () => seek(Math.max(0, R.pos - 1));
  $('rp-next').onclick = () => seek(Math.min(T.cycles.length - 1, R.pos + 1));
  $('rp-speed').onchange = e => { R.speed = +e.target.value; };
  $('rp-mode').onchange = e => { R.mode = e.target.value; seek(R.pos); };
  $('rp-pos').oninput = e => seek(+e.target.value);
  $('rp-filter').oninput = e => { R.filter = e.target.value; updateSide(); };
  const st = $('rp-strip'); st.onclick = e => { const r = st.getBoundingClientRect(); seek(Math.round((e.clientX - r.left) / r.width * (T.cycles.length - 1))); };
  $('rp-lanes').onclick = e => { const tr = e.target.closest('tr[data-l]'); if (!tr) return; const k = +tr.dataset.l; R.lane = R.lane === k ? null : k; seek(R.pos); };
  updateSide();
  if (!R.loop){ R.loop = true; requestAnimationFrame(function l(t){ if (X().S.tab !== 'replay'){ R.loop = false; return; } tick(t); }); }
};
function updateSide(){
  const $ = id => document.getElementById(id); const {esc, fmt, SAFE} = X();
  const [, T] = primary(); if (!T || !T.snap) return;
  if ($('rp-pos')) $('rp-pos').value = R.pos;
  const nch = T.chg ? T.chg.length : 0;
  if ($('rp-cyc')) $('rp-cyc').innerHTML = `cycle <b>${T.cyc}</b> (${R.pos + 1} of ${T.cycles.length}${T.jumpAt.has(R.pos) ? ', <span class="ng">jump</span>' : ''}) · ${fmt(nch, 0)} flops changed`;
  // lanes table: the lanes that changed this cycle first, then by name
  const tb = $('rp-lanes');
  if (tb){
    const d = T.d, cnt = new Map();
    for (let j = 0; j < nch; j++){ const l = T.laneOf[T.chg[j]]; if (l >= 0) cnt.set(l, (cnt.get(l) || 0) + 1); }
    const f = R.filter.toLowerCase();
    let ks = d.lanes.map((_, k) => k).filter(k => !f || (d.lanes[k].name || '').toLowerCase().includes(f));
    ks.sort((a, b) => (cnt.get(b) || 0) - (cnt.get(a) || 0) || a - b); ks = ks.slice(0, 60);
    tb.innerHTML = ks.map(k => { const ln = d.lanes[k], h = hexOf(T, ln);
      return `<tr class="cl ${R.lane === k ? 'on' : ''}" data-l="${k}"><td class="m">${esc(SAFE ? 'register ' + (k + 1) : ln.name)}</td><td class="n">${ln.flops.length}</td><td class="n">${cnt.get(k) || ''}</td><td class="m">${h == null ? '(wide)' : esc(h.length > 18 ? h.slice(0, 16) + '…' : h)}</td></tr>`; }).join('');
  }
  strip(T);
}
function strip(T){
  const cv = document.getElementById('rp-strip'); if (!cv) return;
  const {cssv, SAFE} = X(); const r = cv.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
  cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr);
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, r.width, r.height);
  const n = T.cycles.length, x = p => 4 + p / Math.max(1, n - 1) * (r.width - 8);
  const posOf = new Map(T.cycles.map((cy, p) => [cy, p]));
  const hs = T.d.handshakes, rowH = 18;
  c.font = '10px ' + (cssv('--mono') || 'monospace');
  hs.forEach((h, k) => {
    const y = 4 + k * rowH;
    c.fillStyle = cssv('--faint') || '#888'; c.fillText(SAFE ? h.kind : h.name, 4, y + 9);
    c.fillStyle = h.kind === 'valid' ? '#4e79a7' : h.kind === 'ready' ? '#59a14f' : h.kind === 'credit' ? '#b07aa1' : '#9c755f';
    const ev = h.events; for (let i = 0; i < ev.length; i++){ if (!ev[i][1]) continue; const a = posOf.get(ev[i][0]); if (a == null) continue;
      const b = i + 1 < ev.length ? (posOf.get(ev[i + 1][0]) ?? n - 1) : n - 1; c.fillRect(x(a), y + 11, Math.max(1, x(b) - x(a)), 5); }
  });
  const ty = 4 + hs.length * rowH; c.fillStyle = '#f28e2b';
  T.d.transactions.forEach(t => { const p = posOf.get(t[0]); if (p != null) c.fillRect(x(p), ty, 1, 8); });
  c.fillStyle = cssv('--ng') || '#e15759'; T.jumpAt.forEach(p => c.fillRect(x(p), 0, 1, r.height));
  c.fillStyle = cssv('--ink') || '#fff'; c.fillRect(x(R.pos) - 1, 0, 2, r.height);
}
})();

'use strict';
/* OpenTallas landing: replays recorded sessions at per-user rates read from /api/landing/numbers. */
(() => {
const $ = (id) => document.getElementById(id);
const RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmt = (v, d = 0) => (v == null || isNaN(v)) ? '—' : Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtS = (s) => s < 10 ? s.toFixed(2) : s < 100 ? s.toFixed(1) : s.toFixed(0);
const clamp01 = (x) => x < 0 ? 0 : x > 1 ? 1 : x;
const shortSrc = (p) => String(p || '').replace(/^results\//, '');
async function J(u) { const r = await fetch(u, { cache: 'no-store' }); if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); }
function el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

/* theme */
$('themeBtn').addEventListener('click', () => {
  const root = document.documentElement;
  const cur = root.dataset.theme || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  root.dataset.theme = cur === 'light' ? 'dark' : 'light';
  try { localStorage.setItem('ot-landing-theme', root.dataset.theme); } catch (e) {}
  die.palette();
});

/* ---------- hero die sketch ---------- */
const die = (() => {
  const cv = $('dieCanvas'), ctx = cv.getContext('2d'); let W = 0, H = 0, C = {}, t0 = performance.now();
  const N = 6, layers = 36, sub = 4;
  function palette() { const cs = getComputedStyle(document.documentElement); C = { chip: cs.getPropertyValue('--chip').trim(), line: cs.getPropertyValue('--line2').trim(), fg3: cs.getPropertyValue('--fg3').trim(), bg: cs.getPropertyValue('--bg2').trim(), prefill: cs.getPropertyValue('--prefill').trim() }; draw(performance.now()); }
  function size() { const r = cv.getBoundingClientRect(), d = Math.min(2, window.devicePixelRatio || 1); W = r.width; H = r.height; cv.width = Math.round(W * d); cv.height = Math.round(H * d); ctx.setTransform(d, 0, 0, d, 0, 0); }
  function order(i) { const row = Math.floor(i / N), col = i % N; return [row % 2 ? N - 1 - col : col, row]; }  // serpentine, like a pipelined layer chain
  function draw(now) {
    if (!W) return;
    ctx.clearRect(0, 0, W, H);
    const padT = W * 0.07, padB = Math.max(40, W * 0.11), g = (Math.min(W, H) - padT - padB) / N, gap = g * 0.1, cell = (g - gap) / sub, pad = (W - g * N) / 2;
    const period = 2.6, ph = RM ? 0.42 : ((now - t0) / 1000 / period) % 1, head = ph * (layers + 6);
    for (let i = 0; i < layers; i++) {
      const [cx, cy] = order(i), x = pad + cx * g, y = padT + cy * g, d = head - i, a = d >= 0 && d < 6 ? Math.exp(-d / 1.6) : 0;
      ctx.strokeStyle = C.line; ctx.lineWidth = 1; ctx.strokeRect(x + .5, y + .5, g - gap, g - gap);
      for (let u = 0; u < sub; u++) for (let v = 0; v < sub; v++) {
        const lit = a * (0.55 + 0.45 * Math.sin((u * 3 + v * 5 + i) * 1.7) ** 2);
        ctx.globalAlpha = 0.13 + 0.87 * lit; ctx.fillStyle = (u + v) % 3 === 0 ? C.prefill : C.chip;
        ctx.fillRect(x + u * cell + 2, y + v * cell + 2, cell - 3, cell - 3);
      }
      ctx.globalAlpha = 1;
      if (i < layers - 1) {  // the hop to the next layer
        const [nx, ny] = order(i + 1), x2 = pad + nx * g, y2 = padT + ny * g, mid = (g - gap) / 2;
        ctx.strokeStyle = a > 0.05 ? C.chip : C.line; ctx.globalAlpha = a > 0.05 ? 0.4 + 0.6 * a : 0.6; ctx.lineWidth = a > 0.05 ? 2 : 1;
        ctx.beginPath(); ctx.moveTo(x + mid, y + mid); ctx.lineTo(x2 + mid, y2 + mid); ctx.stroke(); ctx.globalAlpha = 1;
      }
    }
    const L = Math.min(layers - 1, Math.max(0, Math.floor(head)));
    const lab = $('dieLayer'); const s = head >= layers ? 'lm_head → token' : 'L' + String(L).padStart(2, '0') + ' · ROM macros read in place';
    if (lab.textContent !== s) lab.textContent = s;
  }
  const ro = new ResizeObserver(() => { size(); draw(performance.now()); }); ro.observe(cv);
  let vis = true; new IntersectionObserver((e) => { vis = e[0].isIntersecting; }).observe(cv);
  return { palette, tick(now) { if (vis && !RM) draw(now); } };
})();
die.palette();

/* ---------- shared timeline maths ---------- */
function segments(steps, decodeRate, prefillRate) {
  const segs = []; let t = 0;
  steps.forEach((s, i) => {
    const p = s.prefill_tokens / prefillRate, d = s.output_tokens / decodeRate, u = (s.tools_ms || 0) / 1000;
    segs.push({ k: 'prefill', i, t0: t, t1: t + p }); t += p;
    segs.push({ k: 'decode', i, t0: t, t1: t + d }); t += d;
    if (u > 0) { segs.push({ k: 'tools', i, t0: t, t1: t + u }); t += u; }
  });
  const sum = (k) => segs.filter((x) => x.k === k).reduce((a, x) => a + x.t1 - x.t0, 0);
  return { segs, total: t, prefill: sum('prefill'), decode: sum('decode'), tools: sum('tools') };
}
function stepWindow(tl, i) { const w = {}; tl.segs.forEach((s) => { if (s.i === i) w[s.k] = s; }); return w; }

function tlRows(host, rows, opts = {}) {
  host.innerHTML = ''; const max = Math.max(...rows.map((r) => r.tl.total), opts.min || 0) || 1; const out = [];
  rows.forEach((r) => {
    const row = el('div', 'tlrow ' + r.cls), bar = el('div', 'bar');
    row.append(el('div', 'nm', esc(r.name)), bar, el('div', 'tot num', fmtS(r.tl.total) + ' s'));
    r.tl.segs.forEach((s) => { if (s.t1 - s.t0 <= 0) return; const i = el('i', s.k); i.style.left = (100 * s.t0 / max) + '%'; i.style.width = Math.max(0.15, 100 * (s.t1 - s.t0) / max) + '%'; i.title = `${s.k} ${fmtS(s.t1 - s.t0)} s (step ${s.i + 1})`; bar.append(i); });
    if (opts.thresh && opts.thresh < max) { const th = el('div', 'thresh', '<span>1 s</span>'); th.style.left = (100 * opts.thresh / max) + '%'; bar.append(th); }
    const veil = el('div', 'veil'), ph = el('div', 'ph'); bar.append(veil, ph); host.append(row);
    out.push({ veil, ph, max, tl: r.tl });
  });
  return { set(t) { out.forEach((o) => { const x = Math.min(t, o.tl.total) / o.max * 100; o.ph.style.left = x + '%'; o.veil.style.left = x + '%'; }); } };
}

function splitBars(host, rows) {
  host.innerHTML = ''; const max = Math.max(...rows.map((r) => r.tl.total)) || 1;
  rows.forEach((r) => {
    const row = el('div', 'row'), bar = el('div', 'bar'); let x = 0;
    row.append(el('div', 'nm', `<span style="font:600 13px var(--f-display);color:var(--${r.cls})">${esc(r.name)}</span>`), bar);
    [['prefill', r.tl.prefill], ['decode', r.tl.decode], ['tools', r.tl.tools]].forEach(([k, v]) => {
      if (v <= 0) return; const w = 100 * v / max, i = el('i', k); i.style.left = x + '%'; i.style.width = w + '%'; x += w;
      i.title = `${k}: ${fmtS(v)} s`; if (w > 9) i.append(el('span', '', `${k} ${fmtS(v)} s`)); bar.append(i);
    });
    host.append(row);
  });
}

/* ---------- a playback controller ---------- */
function player(playBtn, resetBtn, speedSeg, onFrame, opts = {}) {
  const P = { t: 0, playing: false, speed: Number(speedSeg.querySelector('[aria-pressed="true"]').dataset.s), total: 1, auto: !RM, frame: onFrame };
  const label = playBtn.querySelector('span');
  P.set = (playing) => { P.playing = playing; label.textContent = playing ? 'Pause' : (P.t >= P.total ? 'Replay' : 'Play'); playBtn.querySelector('path').setAttribute('d', playing ? 'M3 1.5h3v11H3zM8 1.5h3v11H8z' : 'M3 1.5v11l9-5.5z'); };
  playBtn.addEventListener('click', () => { if (P.t >= P.total) { P.t = 0; P.frame(0, true); } P.auto = false; P.set(!P.playing); });
  resetBtn.addEventListener('click', () => { P.t = 0; P.auto = false; P.frame(0, true); P.set(true); });
  speedSeg.addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; speedSeg.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', x === b)); P.speed = Number(b.dataset.s); });
  P.step = (dt) => { if (!P.playing) return; P.t = Math.min(P.total, P.t + dt * P.speed); P.frame(P.t, false); if (P.t >= P.total) P.set(false); };
  P.restart = () => { P.t = 0; P.frame(0, true); P.set(false); };
  new IntersectionObserver((e) => { if (e[0].isIntersecting && P.auto && P.ready) { P.auto = false; P.t = 0; P.set(true); } }, { threshold: 0.35 }).observe(opts.observe || playBtn);
  return P;
}
function tabs(host, items, onPick) {
  host.innerHTML = ''; items.forEach((it, i) => { const b = el('button', '', esc(it.title)); b.type = 'button'; b.setAttribute('aria-pressed', i === 0); b.onclick = () => { host.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', x === b)); onPick(it); }; host.append(b); });
}
function stick(box) { return box.scrollTop + box.clientHeight >= box.scrollHeight - 40; }

/* ---------- Demo A: agent terminals ---------- */
function agentPane(term, rec, tl, sideName) {
  const S = rec.steps, nodes = [];
  function reset() {
    term.innerHTML = ''; nodes.length = 0;
    term.append(el('div', 'ln sys', `${esc(sideName)} · ${S.length} model calls · ${fmt(S.reduce((a, s) => a + s.output_tokens, 0))} generated tokens\n<span style="color:#f0b78c">▶ press Play to replay the session</span>`));
  }
  function ensure(i) {
    if (nodes[i]) return nodes[i];
    const s = S[i], w = stepWindow(tl, i), box = el('div');
    const head = el('div', 'ln step', ''), think = el('div', 'ln think'), say = el('div', 'ln say'), calls = el('div');
    box.append(head, think, say, calls); term.append(box);
    const tc = s.tool_calls.map((c) => { const d = el('div'); const line = el('div', 'ln tc', ''); const res = el('div'); d.append(line, res); calls.append(d); return { c, line, res, shown: -1, state: '' }; });
    let cum = 0; tc.forEach((x) => { cum += (x.c.ms || 0) / 1000; x.done = cum; });
    const scale = tc.length && cum > 0 && w.tools ? (w.tools.t1 - w.tools.t0) / cum : 1;
    tc.forEach((x) => { x.done *= scale; });
    const labels = tc.map((x) => '→ ' + (x.c.label || x.c.name));
    const visChars = s.text.length + labels.reduce((a, l) => a + l.length, 0);
    return (nodes[i] = { s, w, head, think, say, tc, labels, visChars, last: {} });
  }
  function render(t) {
    const st = stick(term); let changed = false;
    for (let i = 0; i < S.length; i++) {
      const w0 = stepWindow(tl, i); if (t < w0.prefill.t0 || (t === 0)) break;
      const n = ensure(i), s = n.s, w = n.w;
      const pf = clamp01((t - w.prefill.t0) / Math.max(1e-9, w.prefill.t1 - w.prefill.t0));
      const head = `── call ${i + 1}/${S.length} · prefill ${fmt(s.prefill_tokens)} new tokens` + (s.cached_tokens ? ` (+${fmt(s.cached_tokens)} cached)` : '') + (pf < 1 ? ` · ${Math.round(pf * 100)}%` : ` · ${fmtS((w.prefill.t1 - w.prefill.t0) * 1000)} ms`);
      if (n.last.head !== head) { n.head.textContent = head; n.last.head = head; changed = true; }
      const df = clamp01((t - w.decode.t0) / Math.max(1e-9, w.decode.t1 - w.decode.t0)); const e = df * s.output_tokens, r = s.reasoning_tokens;
      const thinkF = t < w.decode.t0 ? 0 : (r > 0 ? clamp01(e / r) : (s.thinking ? 1 : 0));
      const restF = t < w.decode.t0 ? 0 : clamp01((e - r) / Math.max(1, s.output_tokens - r));
      const tk = Math.round(s.thinking.length * thinkF);
      if (n.last.tk !== tk) { n.think.textContent = tk ? '✻ ' + s.thinking.slice(0, tk) : ''; n.think.classList.toggle('cursor', thinkF > 0 && thinkF < 1); n.last.tk = tk; changed = true; }
      let budget = Math.round(n.visChars * restF);
      const sk = Math.min(s.text.length, budget); budget -= sk;
      if (n.last.sk !== sk) { n.say.textContent = s.text.slice(0, sk); n.say.classList.toggle('cursor', restF > 0 && restF < 1 && budget <= 0); n.last.sk = sk; changed = true; }
      n.tc.forEach((x, j) => {
        const L = n.labels[j], show = Math.min(L.length, Math.max(0, budget)); budget -= L.length;
        let state = '';
        if (show >= L.length && w.tools) { const tu = t - w.tools.t0; state = tu < 0 ? 'queued' : tu >= x.done ? 'done' : 'run'; }
        const key = show + state + (state === 'run' ? Math.floor((t - w.tools.t0) * 10) : '');
        if (x.shown === key) return; x.shown = key; changed = true;
        if (!show) { x.line.textContent = ''; x.res.innerHTML = ''; return; }
        const st2 = state === 'done' ? `<span class="st">✓ ${fmtS(x.c.ms / 1000)} s</span>` : state === 'run' ? `<span class="st">… running ${fmtS(Math.max(0, t - w.tools.t0))} s</span>` : '';
        x.line.className = 'ln tc' + (state === 'done' ? ' ok' : ''); x.line.innerHTML = esc(L.slice(0, show)) + ' ' + st2;
        if (state === 'done' && !x.res.childElementCount) {
          if (x.c.diff) { const d = el('div', 'diff'); if (x.c.diff.old) d.append(el('div', 'd', esc(x.c.diff.old.split('\n').map((l) => '- ' + l).join('\n')))); d.append(el('div', 'a', esc(x.c.diff.new.split('\n').map((l) => '+ ' + l).join('\n')))); x.res.append(d); }
          else if (x.c.result) x.res.append(el('div', 'ln res', esc(x.c.result.replace(/<\/?(path|type|content)>/g, '').trim().split('\n').slice(0, 7).join('\n'))));
        } else if (state !== 'done' && x.res.childElementCount) x.res.innerHTML = '';
      });
    }
    if (changed && st) term.scrollTop = term.scrollHeight;
  }
  reset();
  return { reset, render };
}

const A = { recs: {}, cur: null };
function setupA(N, idx) {
  const gpuR = N.gpu.ds.per_user.value, chipR = N.designs.find((d) => d.id === 'ds_rom').per_user_mtp.value, preR = N.gpu.ds.prefill.value;
  $('aGpuRate').textContent = `${fmt(gpuR, 1)} tok/s per user · third-party · ${N.gpu.ds.per_user.label}`;
  $('aChipRate').textContent = `${fmt(chipR, 1)} tok/s per user · analytical · MTP τ 4.159 · ${shortSrc(N.designs.find((d) => d.id === 'ds_rom').per_user_mtp.source)} · ${N.designs.find((d) => d.id === 'ds_rom').per_user_mtp.date}`;
  const P = player($('aPlay'), $('aReset'), $('aSpeed'), (t) => frameA(t), { observe: $('aGpu') });
  A.P = P;
  async function pick(it) {
    const rec = A.recs[it.id] || (A.recs[it.id] = await J('recordings/' + it.file));
    const tg = segments(rec.steps, gpuR, preR), tc = segments(rec.steps, chipR, preR);
    A.cur = { rec, tg, tc, gp: agentPane($('aGpuTerm'), rec, tg, 'GPU'), cp: agentPane($('aChipTerm'), rec, tc, 'DS ROM') };
    A.bars = tlRows($('aTl'), [{ name: 'Best GPU', cls: 'gpu', tl: tg }, { name: 'DS ROM', cls: 'chip', tl: tc }]);
    $('aTask').innerHTML = `<b>${esc(rec.title)}.</b> ${esc(rec.blurb)} Task given to the agent: “${esc(rec.task)}” <span class="src">recorded ${new Date(rec.recorded * 1000).toISOString().slice(0, 16).replace('T', ' ')} UTC · ${esc(rec.harness)} · API served <b>${esc(rec.model_served.join(', '))}</b> · ${rec.steps.length} model calls, ${rec.steps.reduce((a, s) => a + s.tool_calls.length, 0)} tool calls</span>`;
    $('aBig').innerHTML = `${fmtS(tc.total)} s <small>vs ${fmtS(tg.total)} s on the GPU</small>`;
    $('aBigSub').textContent = `The session finishes ${(tg.total / tc.total).toFixed(1)}× sooner end to end. ${fmt(rec.steps.reduce((a, s) => a + s.output_tokens, 0))} generated tokens (${fmt(rec.steps.reduce((a, s) => a + s.reasoning_tokens, 0))} of them reasoning), ${fmt(rec.steps.reduce((a, s) => a + s.prefill_tokens, 0))} prefilled prompt tokens.`;
    splitBars($('aSplit'), [{ name: 'GPU', cls: 'gpu', tl: tg }, { name: 'DS ROM', cls: 'chip', tl: tc }]);
    $('aAmdahl').textContent = `Decode drops from ${fmtS(tg.decode)} s to ${fmtS(tc.decode)} s (${(tg.decode / tc.decode).toFixed(1)}×). Prefill (${fmtS(tg.prefill)} s) and tools (${fmtS(tg.tools)} s) are the same on both sides, so the end-to-end gain is ${(tg.total / tc.total).toFixed(1)}×. This is Amdahl's law: the faster decode gets, the more the measured tool time dominates.`;
    P.total = Math.max(tg.total, tc.total); P.ready = true; P.restart();
  }
  tabs($('aTabs'), idx.agent, (it) => { pick(it).then(() => { A.P.auto = false; A.P.set(true); }); });
  $('aNote').innerHTML = `GPU decode: ${fmt(gpuR, 1)} tok/s, <span class="mono">${esc(N.gpu.ds.per_user.field)}</span> in <span class="mono">results/external/registry.json</span> (${esc(N.gpu.ds.per_user.title)}). This is the best published per-user DeepSeek-V4-family figure in the registry. It is measured on the larger V4-Pro, and no batch-1 V4.1-Flash GPU figure is published (V4-Flash on 4 × H200: ${fmt(N.gpu.ds.per_user_flash.value)} tok/s). Chip decode: ${fmt(chipR, 1)} tok/s, <span class="mono">${esc(N.designs.find((d) => d.id === 'ds_rom').per_user_mtp.source)}</span> · <span class="mono">headline.tok_s</span>, i.e. τ 4.159 accepted tokens per 955.7 µs MTP step at 1M context (${esc(N.designs.find((d) => d.id === 'ds_rom').per_user_mtp.status)}). Prefill on both sides: ${fmt(preR)} tok/s, <span class="mono">${esc(N.gpu.ds.prefill.source)} · ${esc(N.gpu.ds.prefill.field)}</span> (${esc(N.gpu.ds.prefill.label)}).`;
  return pick(idx.agent[0]);
}
function frameA(t) { if (!A.cur) return; const c = A.cur; if (t === 0) { c.gp.reset(); c.cp.reset(); } c.gp.render(t); c.cp.render(t); A.bars.set(t);
  clockSet($('aGpuClock'), $('aGpu'), t, c.tg.total, 'wall clock'); clockSet($('aChipClock'), $('aChip'), t, c.tc.total, 'wall clock'); }
function clockSet(clock, lane, t, total, word) {
  const v = Math.min(t, total), done = t >= total - 1e-9 && t > 0; const s = `${v.toFixed(1)} s<small>${done ? 'done' : word}</small>`;
  if (clock._s !== s) { clock.innerHTML = s; clock._s = s; } lane.classList.toggle('done', done);
}

/* ---------- Demo B: long answer ---------- */
function mdLine(raw) {
  const t = esc(raw).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\*\*(.*)$/, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>');
  let m;
  if ((m = raw.match(/^(#{1,6})\s/))) return { tag: 'h4', cls: m[1].length <= 1 ? 'h1' : '', html: t.replace(/^#{1,6}\s/, '') };
  if (/^\s*([-*]|\d+\.)\s/.test(raw)) return { tag: 'div', cls: 'li', html: t.replace(/^\s*([-*]|\d+\.)\s/, '') };
  if (/^\s*-{3,}\s*$/.test(raw)) return { tag: 'div', cls: '', html: '' };
  return { tag: 'p', cls: '', html: t };
}
function streamPane(box, text) {
  const lines = []; let off = 0; text.split('\n').forEach((l) => { lines.push({ s: off, e: off + l.length, text: l }); off += l.length + 1; });
  let full = 0, partial = null, lastC = -1;
  function reset() { box.innerHTML = ''; full = 0; partial = null; lastC = -1; }
  function render(c) {
    if (c === lastC) return; if (c < lastC) reset(); lastC = c; const st = stick(box);
    while (full < lines.length && lines[full].e < c) { if (partial) { partial.remove(); partial = null; } const L = lines[full]; if (L.text.trim()) { const m = mdLine(L.text); box.append(el(m.tag, m.cls, m.html)); } full++; }
    if (full < lines.length && c > lines[full].s) { const L = lines[full], m = mdLine(L.text.slice(0, c - L.s)); if (!partial || partial.tagName.toLowerCase() !== m.tag) { if (partial) partial.remove(); partial = el(m.tag, m.cls); box.append(partial); } partial.className = (m.cls ? m.cls + ' ' : '') + 'cursor'; partial.innerHTML = m.html; }
    else if (partial) { partial.remove(); partial = null; }
    if (st) box.scrollTop = box.scrollHeight;
  }
  return { reset, render };
}
const B = {};
function setupB(N, q) {
  const gpuR = N.gpu.qwen.per_user.value, chipR = N.designs.find((d) => d.id === 'qwen_rom').per_user.value, preR = N.gpu.qwen.prefill.value;
  const pre = q.prompt_tokens / preR, n = q.output_tokens, tg = pre + n / gpuR, tc = pre + n / chipR;
  const cum = []; let o = 0; q.pieces.forEach((p) => { o += p.length; cum.push(o); });
  const gp = streamPane($('bGpuText'), q.text), cp = streamPane($('bChipText'), q.text);
  $('bGpuRate').textContent = `${fmt(gpuR)} tok/s per user · third-party`; $('bChipRate').textContent = `${fmt(chipR, 1)} tok/s per user · analytical`;
  $('bTask').innerHTML = `<b>Prompt:</b> “${esc(q.prompt)}” <span class="src">${fmt(q.prompt_tokens)} prompt tokens → ${fmt(n)} output tokens · generated by ${esc(q.model)} (${esc(q.dtype)}, thinking off) on our own machine, ${esc(q.recorded)}; the text is real model output, only the pacing is modelled</span>`;
  $('bBig').innerHTML = `${tc.toFixed(2)} s <small>vs ${tg.toFixed(2)} s on the GPU</small>`;
  $('bBigSub').textContent = `${(tg / tc).toFixed(1)}× sooner. Both sides start streaming after the same ${(pre * 1000).toFixed(1)} ms prefill.`;
  splitBars($('bSplit'), [{ name: 'GPU', cls: 'gpu', tl: { prefill: pre, decode: n / gpuR, tools: 0, total: tg } }, { name: 'Qwen ROM', cls: 'chip', tl: { prefill: pre, decode: n / chipR, tools: 0, total: tc } }]);
  $('bNoteIn').textContent = `Decode: ${fmt(n)} tokens at ${fmt(gpuR)} vs ${fmt(chipR, 1)} tok/s. Without speculative decoding the same B200 runs ${fmt(N.gpu.qwen.per_user_ar.value)} tok/s, which would take ${(pre + n / N.gpu.qwen.per_user_ar.value).toFixed(1)} s.`;
  const qr = N.designs.find((d) => d.id === 'qwen_rom').per_user;
  $('bNote').innerHTML = `GPU: ${fmt(gpuR)} tok/s, <span class="mono">${esc(N.gpu.qwen.per_user.field)}</span> in <span class="mono">results/external/registry.json</span> (${esc(N.gpu.qwen.per_user.label)}). This is the best published Qwen3-8B per-user figure in the registry; its MATH-500 acceptance (τ 8.01) is favourable to the GPU. Qwen ROM: ${fmt(chipR, 1)} tok/s, <span class="mono">${esc(qr.source)} · ${esc(qr.field)}</span> (${esc(qr.mode)}, ${esc(qr.status)}, ${esc(qr.date)}). Prefill: ${fmt(preR)} tok/s, <span class="mono">${esc(N.gpu.qwen.prefill.source)} · ${esc(N.gpu.qwen.prefill.field)}</span>. Recording note: the local GPU was unavailable, so the text was generated on CPU with the same weights. Generation speed plays no part in the replay.`;
  const P = player($('bPlay'), $('bReset'), $('bSpeed'), (t) => {
    const side = (pane, T, rate, lane, tEl, pEl) => {
      const k = t <= pre ? 0 : Math.min(n, Math.floor((t - pre) * rate)); pane.render(k ? cum[k - 1] : 0);
      const v = Math.min(t, T), s = v.toFixed(3); if (tEl._s !== s) { tEl.textContent = s; tEl._s = s; }
      pEl.style.transform = `scaleX(${clamp01(t / T)})`; lane.classList.toggle('done', t >= T && t > 0);
    };
    side(gp, tg, gpuR, $('bGpu'), $('bGpuT'), $('bGpuP')); side(cp, tc, chipR, $('bChip'), $('bChipT'), $('bChipP'));
  }, { observe: $('bGpu') });
  P.total = tg; P.ready = true; P.restart(); B.P = P;
  [$('bGpuText'), $('bChipText')].forEach((b) => { if (!b.childElementCount) b.append(el('p', '', '<span style="color:var(--fg3)">▶ Play to stream the answer.</span>')); });
}

/* ---------- Demo C: home hub ---------- */
const PLAN = {
  rooms: { kitchen: [10, 10, 130, 110], living_room: [140, 10, 160, 130], office: [300, 10, 110, 110], garage: [10, 120, 130, 140], hallway: [140, 140, 160, 50], bedroom: [300, 120, 110, 140], porch: [140, 190, 160, 70] },
  names: { kitchen: 'Kitchen', living_room: 'Living room', office: 'Office', garage: 'Garage', hallway: 'Hall', bedroom: 'Bedroom', porch: 'Porch' },
  locks: { front_door: [220, 190], back_door: [75, 10], garage_entry: [140, 165] },
  wins: { kitchen: [10, 40, 10, 90], living_room: [180, 10, 260, 10], office: [330, 10, 380, 10], bedroom: [410, 160, 410, 220] },
  dev: { thermostat: [190, 165], oven: [36, 98], dishwasher: [104, 98], tv: [220, 118], alarm: [355, 240], calendar: [355, 200] },
};
function planSvg(svg) {
  const NS = 'http://www.w3.org/2000/svg', mk = (t, a, p = svg) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); p.append(e); return e; };
  svg.innerHTML = ''; const R = {};
  for (const [k, [x, y, w, h]] of Object.entries(PLAN.rooms)) {
    mk('rect', { class: 'room', x, y, width: w, height: h, ...(k === 'porch' ? { 'stroke-dasharray': '4 4', fill: 'none' } : {}) });
    R['glow_' + k] = mk('rect', { class: 'glow', x: x + 2, y: y + 2, width: w - 4, height: h - 4, style: 'fill:var(--warn)', opacity: 0 });
    R['bulb_' + k] = mk('circle', { class: 'bulb', cx: x + w / 2, cy: y + h / 2 - 6, r: 4, style: 'fill:var(--line2)' });
    const t = mk('text', { class: 'rl', x: x + 7, y: y + 15 }); t.textContent = PLAN.names[k];
  }
  mk('rect', { class: 'wall', x: 10, y: 10, width: 400, height: 180 }); mk('path', { class: 'wall', d: 'M10 190V260H140' });
  for (const [k, [x1, y1, x2, y2]] of Object.entries(PLAN.wins)) R['win_' + k] = mk('line', { class: 'win closed', x1, y1, x2, y2 });
  mk('line', { x1: 30, y1: 260, x2: 120, y2: 260, style: 'stroke:var(--fg3);stroke-width:5' });  // garage door
  for (const [k, [x, y]] of Object.entries(PLAN.locks)) {
    const g = mk('g', { transform: `translate(${x - 7},${y - 9})` });
    mk('path', { d: 'M3 8V5a4 4 0 0 1 8 0v3', style: 'fill:none;stroke:var(--fg2);stroke-width:1.6' }, g);
    R['lock_' + k] = mk('rect', { class: 'lock', x: 1, y: 8, width: 12, height: 9, rx: 2, style: 'fill:var(--bad)' }, g);
  }
  const lbl = (k, x, y) => { R['lbl_' + k] = mk('text', { class: 'lbl', x, y, 'text-anchor': 'middle' }); };
  lbl('thermostat', ...PLAN.dev.thermostat); lbl('oven', ...PLAN.dev.oven); lbl('dishwasher', ...PLAN.dev.dishwasher); lbl('tv', ...PLAN.dev.tv); lbl('alarm', ...PLAN.dev.alarm); lbl('calendar', ...PLAN.dev.calendar);
  R.pulses = mk('g', {});
  R.mk = mk;
  return R;
}
const PULSE_AT = { get_home_state: [210, 100], set_lights: [210, 60], lock_door: null, set_thermostat: PLAN.dev.thermostat, get_calendar: PLAN.dev.calendar, set_alarm: PLAN.dev.alarm, turn_off_appliance: null };
function pulsePos(c) {
  if (c.name === 'lock_door') return PLAN.locks[c.args.door] || [210, 100];
  if (c.name === 'turn_off_appliance') return PLAN.dev[c.args.appliance] || [210, 100];
  if (c.name === 'set_lights' && PLAN.rooms[c.args.room]) { const [x, y, w, h] = PLAN.rooms[c.args.room]; return [x + w / 2, y + h / 2]; }
  return PULSE_AT[c.name] || [210, 100];
}
function applyEffect(st, c) {
  const r = c.effect || {}; if (r.error) return;
  if (c.name === 'set_lights' && r.lights) Object.assign(st.lights, r.lights);
  if (c.name === 'lock_door' && r.door) st.locks[r.door] = r.state;
  if (c.name === 'set_thermostat' && r.thermostat) st.thermostat = r.thermostat;
  if (c.name === 'set_alarm' && r.alarm) st.alarms = [...st.alarms, r.alarm];
  if (c.name === 'turn_off_appliance' && r.appliance) st.appliances[r.appliance] = r.state;
  if (c.name === 'get_calendar') st.cal = (r.events || []).length;
}
function homePane(svg, tick, say, rec, tl) {
  const R = planSvg(svg), S = rec.steps, events = [];
  S.forEach((s, i) => { const w = stepWindow(tl, i); if (!w.tools) return; const sc = (w.tools.t1 - w.tools.t0) / Math.max(1e-9, Math.max(...s.tool_calls.map((c) => c.ms)) / 1000);
    s.tool_calls.forEach((c) => events.push({ c, t0: w.tools.t0, t1: w.tools.t0 + c.ms / 1000 * sc })); });
  let lastKey = '', lastSay = '', lastTick = '';
  function state(t) { const st = JSON.parse(JSON.stringify(rec.initial_state)); events.forEach((e) => { if (t >= e.t1) applyEffect(st, e.c); }); return st; }
  function render(t) {
    const st = state(t), key = JSON.stringify(st);
    if (key !== lastKey) {
      lastKey = key;
      for (const k in PLAN.rooms) { const on = st.lights[k] === 'on'; R['glow_' + k].setAttribute('opacity', on ? 0.11 : 0); R['bulb_' + k].style.fill = on ? 'var(--warn)' : 'var(--line2)'; }
      for (const k in PLAN.locks) R['lock_' + k].style.fill = st.locks[k] === 'locked' ? 'var(--good)' : 'var(--bad)';
      for (const k in PLAN.wins) R['win_' + k].setAttribute('class', 'win ' + (st.windows[k] === 'open' ? 'open' : 'closed'));
      const th = st.thermostat; R.lbl_thermostat.textContent = `${th.target_c}°C`; R.lbl_thermostat.setAttribute('class', 'lbl' + (th.target_c !== rec.initial_state.thermostat.target_c ? ' hi' : ''));
      const ap = (k, n) => { R['lbl_' + k].textContent = `${n} ${st.appliances[k]}`; R['lbl_' + k].setAttribute('class', 'lbl' + (st.appliances[k] !== rec.initial_state.appliances[k] ? ' hi' : '')); };
      ap('oven', 'oven'); ap('dishwasher', 'dw'); ap('tv', 'tv');
      R.lbl_alarm.textContent = st.alarms.length ? `alarm ${st.alarms[st.alarms.length - 1].time}` : 'no alarm'; R.lbl_alarm.setAttribute('class', 'lbl' + (st.alarms.length ? ' hi' : ''));
      R.lbl_calendar.textContent = st.cal != null ? `${st.cal} events read` : '';
    }
    const running = events.filter((e) => t >= e.t0 && t < e.t1);
    const pk = running.map((e) => e.c.label).join('|');
    if (R.pulses._k !== pk) { R.pulses._k = pk; R.pulses.innerHTML = ''; running.forEach((e) => { const [x, y] = pulsePos(e.c); R.mk('circle', { class: 'pulse', cx: x, cy: y, r: 9, style: 'fill:none;stroke:var(--chip);stroke-width:2' }, R.pulses); }); }
    const lines = events.filter((e) => t >= e.t0).slice(-4).map((e) => t >= e.t1 ? `<div class="${e.c.effect && e.c.effect.error ? 'er' : 'ok'}">${e.c.effect && e.c.effect.error ? '✗' : '✓'} ${esc(e.c.label)} · ${fmtS(e.c.ms / 1000)} s</div>` : `<div class="run">… ${esc(e.c.label)}</div>`).join('');
    if (lines !== lastTick) { tick.innerHTML = lines || '<div>waiting for the first tool call…</div>'; lastTick = lines; }
    let html = '<span class="who">assistant</span>';
    for (let i = S.length - 1; i >= 0; i--) {
      const w = stepWindow(tl, i); if (t < w.decode.t0) continue; const s = S[i];
      const f = clamp01((t - w.decode.t0) / Math.max(1e-9, w.decode.t1 - w.decode.t0)), e = f * s.output_tokens, r = s.reasoning_tokens;
      if (e < r && s.thinking) { const k = Math.round(s.thinking.length * e / r); html += `<span class="thinking">thinking… ${esc(s.thinking.slice(Math.max(0, k - 180), k))}</span>`; }
      else if (s.text) { const k = Math.round(s.text.length * clamp01((e - r) / Math.max(1, s.output_tokens - r))); html += esc(s.text.slice(0, k)).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>'); }
      else html += `<span class="thinking">calling ${s.tool_calls.length} device tool${s.tool_calls.length === 1 ? '' : 's'}…</span>`;
      break;
    }
    if (html === '<span class="who">assistant</span>') html += '<span class="thinking">listening…</span>';
    if (html !== lastSay) { say.innerHTML = html; lastSay = html; }
  }
  return { render, firstAction: events.length ? Math.min(...events.map((e) => e.t1)) : null };
}
const C = { recs: {} };
function setupC(N, idx) {
  if (!idx.home.length) { $('cTask').textContent = 'No home recording installed yet.'; return; }
  const P = player($('cPlay'), $('cReset'), $('cSpeed'), (t) => frameC(t), { observe: $('cGpu') }); C.P = P;
  async function pick(it) {
    const rec = C.recs[it.id] || (C.recs[it.id] = await J('recordings/' + it.file));
    const qwen = it.design === 'qwen', d = N.designs.find((x) => x.id === (qwen ? 'qwen_rom' : 'ds_rom'));
    const chipR = qwen ? d.per_user.value : d.per_user_mtp.value, gpuR = qwen ? N.gpu.qwen.per_user.value : N.gpu.ds.per_user.value, preR = qwen ? N.gpu.qwen.prefill.value : N.gpu.ds.prefill.value;
    const tg = segments(rec.steps, gpuR, preR), tc = segments(rec.steps, chipR, preR);
    $('cChipName').textContent = qwen ? 'Qwen ROM hub' : 'DS ROM array';
    $('cGpuRate').textContent = `${fmt(gpuR, 1)} tok/s per user · third-party`; $('cChipRate').textContent = `${fmt(chipR, 1)} tok/s per user · analytical${qwen ? '' : ' · MTP'}`;
    C.cur = { rec, tg, tc, g: homePane($('cGpuPlan'), $('cGpuTick'), $('cGpuSay'), rec, tg), c: homePane($('cChipPlan'), $('cChipTick'), $('cChipSay'), rec, tc) };
    C.bars = tlRows($('cTl'), [{ name: 'GPU hub', cls: 'gpu', tl: tg }, { name: qwen ? 'Qwen ROM' : 'DS ROM', cls: 'chip', tl: tc }], { thresh: 1, min: 1.2 });
    const nTools = rec.steps.reduce((a, s) => a + s.tool_calls.length, 0), out = rec.steps.reduce((a, s) => a + s.output_tokens, 0), rs = rec.steps.reduce((a, s) => a + s.reasoning_tokens, 0);
    $('cTask').innerHTML = `<b>“${esc(rec.request)}”</b> <span class="src">${esc(rec.model_note)}${rec.served_models && rec.served_models.length ? ' (served: ' + esc(rec.served_models.join(', ')) + ')' : ''} · recorded ${esc(rec.recorded)} · ${rec.steps.length} model calls, ${nTools} device calls, ${fmt(out)} generated tokens (${fmt(rs)} thinking)</span>`;
    $('cBig').innerHTML = `${fmtS(tc.total)} s <small>vs ${fmtS(tg.total)} s on the GPU</small>`;
    $('cBigSub').textContent = `First device moves at ${fmtS(C.cur.c.firstAction)} s vs ${fmtS(C.cur.g.firstAction)} s. Device calls take ${fmtS(tg.tools)} s on both sides. They are measured and run in parallel where the model asked for it.`;
    $('cWhy').textContent = `In this trace decode is ${Math.round(100 * tg.decode / tg.total)}% of the GPU's time to done and ${Math.round(100 * tc.decode / tc.total)}% of the chip's.`;
    $('cNote').innerHTML = `The mock home answers each device call after a latency drawn from a typical range per device class (lock motor with confirmation 1.0–1.5 s, cloud thermostat 0.55–0.85 s, Zigbee lights 0.2–0.3 s). These latencies are modelled, and the replay uses the wall times we measured. ${qwen ? 'The Qwen trace ran on CPU with the released Qwen3-8B weights (BF16), because the local GPU was unavailable. Only token counts and text are used.' : 'The DeepSeek trace ran through the DeepSeek API (OpenAI-compatible tool calling); the API reported the reasoning-token counts.'} Rates as in the demos above.`;
    P.total = Math.max(tg.total, tc.total); P.ready = true; P.restart();
  }
  tabs($('cTabs'), idx.home, (it) => pick(it).then(() => { C.P.auto = false; C.P.set(true); }));
  return pick(idx.home[0]);
}
function frameC(t) { if (!C.cur) return; C.cur.g.render(t); C.cur.c.render(t); C.bars.set(t); clockSet($('cGpuClock'), $('cGpu'), t, C.cur.tg.total, 'time to done'); clockSet($('cChipClock'), $('cChip'), t, C.cur.tc.total, 'time to done'); }

/* ---------- numbers table + hero ---------- */
function numbers(N) {
  const D = Object.fromEntries(N.designs.map((d) => [d.id, d])), G = N.gpu;
  const ref = (o) => o ? `<div class="src">${o.stale ? '' : (o.source === 'results/external/registry.json' ? 'third-party · ' : 'analytical · ')}${esc(shortSrc(o.source))} · ${esc(o.field)}${o.date ? ' · ' + esc(o.date) : ''}</div>` : '';
  const v = (o, d = 1) => o ? `${fmt(o.value, o.value > 10000 ? 0 : d)}${o.stale ? '<span class="stale" title="' + esc(o.note) + '">STALE</span>' : ''}${ref(o)}${o.stale ? `<div class="src">${esc(o.note)}</div>` : ''}` : '<span style="color:var(--fg3)">not in the registry</span>';
  const pair = (a, b) => `${fmt(a.value, 1)} / ${fmt(b.value, 1)}${ref(a)}${ref(b)}`;
  const rows = [
    ['ours', 'Qwen ROM', 'Qwen3-8B · 8K · AR', v(D.qwen_rom.per_user), v(D.qwen_rom.aggregate), D.qwen_rom.per_user.status],
    ['ours', 'DS ROM array', 'DeepSeek-V4.1 Flash · 1M · AR / MTP', pair(D.ds_rom.per_user, D.ds_rom.per_user_mtp), v(D.ds_rom.aggregate) + '<br>' + v(D.ds_rom.aggregate_mtp), D.ds_rom.per_user_mtp.status],
    ['ours', 'HBM accelerator', 'DeepSeek-V4.1 Flash · 1M · AR / MTP', pair(D.hbm_ds.per_user, D.hbm_ds.per_user_mtp), v(D.hbm_ds.aggregate) + '<br>' + v(D.hbm_ds.aggregate_mtp), D.hbm_ds.per_user_mtp.status],
    ['gpu', 'Best GPU · Qwen3-8B', esc(G.qwen.per_user.label), v(G.qwen.per_user, 0) + `<div class="src">no speculation: ${fmt(G.qwen.per_user_ar.value)} tok/s</div>`, v(null), 'published, third-party'],
    ['gpu', 'Best GPU · DeepSeek', esc(G.ds.per_user.label), v(G.ds.per_user) + `<div class="src">V4-Flash, 4 × H200: ${fmt(G.ds.per_user_flash.value)} tok/s</div>`, v(G.ds.aggregate, 0) + `<div class="src">${esc(G.ds.aggregate.label)}</div>`, 'published, third-party'],
  ];
  $('numsTable').tBodies[0].innerHTML = rows.map(([c, m, mm, pu, ag, st]) => `<tr class="${c}"><td><b>${esc(m)}</b><div style="margin-top:4px">${c === 'ours' ? '<span class="tag-a">analytical</span>' : '<span class="tag-g">third-party</span>'}</div></td><td>${mm}</td><td class="v">${pu}</td><td class="v${/STALE|not in/.test(ag) ? ' dim' : ''}">${ag}</td><td style="font-size:13px;color:var(--fg2)">${esc(st)}</td></tr>`).join('');
  $('numsNote').innerHTML = `Read from <span class="mono">${esc(N.generated_from.token_path)}</span> and <span class="mono">${esc(N.generated_from.reprice)}</span> (repriced ${esc(N.generated_from.reprice_date)}), and <span class="mono">results/external/registry.json</span> (${esc(N.generated_from.registry_date)}). Aggregates have not been recomputed for the 2026-10-08 design points. The newest committed aggregates belong to earlier designs and are marked STALE.`;
  const hs = (id, ours, gpu, src) => { $(id).innerHTML = `${fmt(ours.value, 0)}<small>tok/s</small>`; $(id + '-s').innerHTML = `${(ours.value / gpu.value).toFixed(1)}× the best published GPU (${fmt(gpu.value, gpu.value < 1000 ? 1 : 0)})<br>analytical · ${esc(shortSrc(ours.source))} · ${esc(ours.date)}`; };
  hs('hs-qwen', D.qwen_rom.per_user, G.qwen.per_user); hs('hs-ds', D.ds_rom.per_user_mtp, G.ds.per_user); hs('hs-hbm', D.hbm_ds.per_user_mtp, G.ds.per_user);
}

/* ---------- boot ---------- */
let last = performance.now();
function loop(now) { const dt = Math.min(0.1, (now - last) / 1000); last = now; die.tick(now); [A.P, B.P, C.P].forEach((p) => p && p.step(dt)); requestAnimationFrame(loop); }
requestAnimationFrame(loop);
(async () => {
  try {
    const [N, idx] = await Promise.all([J('/api/landing/numbers'), J('recordings/index.json')]);
    if (N.error) throw new Error(N.error);
    numbers(N);
    const q = idx.long ? await J('recordings/' + idx.long) : null;
    await Promise.all([setupA(N, idx), q ? setupB(N, q) : null, setupC(N, idx)]);
    $('recInfo').textContent = `${idx.agent.length} dsh coding sessions, ${idx.home.length} home-hub traces, 1 long Qwen3-8B answer, all recorded 2026-10-09`;
  } catch (e) {
    console.warn('landing:', e); $('aTask').textContent = 'Could not load the numbers or recordings: ' + e.message;
  }
})();
})();

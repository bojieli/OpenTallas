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
  function size() { const r = cv.getBoundingClientRect(), d = Math.min(2, window.devicePixelRatio || 1), w = Math.round(r.width * d), h = Math.round(r.height * d); W = r.width; H = r.height; if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; } ctx.setTransform(d, 0, 0, d, 0, 0); }
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

/* the three lanes: our chip, best published GPU at batch 1, OpenRouter median served speed */
function sides(N, model) {
  const ds = model === 'ds', D = N.designs.find((d) => d.id === (ds ? 'ds_rom' : 'qwen_rom')), G = ds ? N.gpu.ds : N.gpu.qwen;
  const chip = ds ? D.per_user_mtp : D.per_user;
  return [
    { k: 'Chip', cls: 'chip', name: ds ? 'DS ROM array' : 'Qwen ROM', short: ds ? 'DS ROM' : 'Qwen ROM', rate: chip.value,
      label: `${fmt(chip.value, 1)} tok/s per user · analytical${ds ? ' · MTP τ 4.159' : ''} · ${shortSrc(chip.source)} · ${chip.date}` },
    { k: 'Gpu', cls: 'gpu', name: 'Best GPU, batch 1', short: 'Best GPU', rate: G.per_user.value,
      label: `${fmt(G.per_user.value, G.per_user.value < 1000 ? 1 : 0)} tok/s per user · third-party · ${G.per_user.label}` },
    { k: 'Or', cls: 'or', name: 'OpenRouter today', short: 'OpenRouter', rate: G.served.value,
      label: `${fmt(G.served.value, 1)} tok/s · ${G.served.label} · snapshot ${G.served.date}, includes network and load` },
  ];
}
const A = { recs: {}, cur: null };
function setupA(N, idx) {
  const S = sides(N, 'ds'), preR = N.gpu.ds.prefill.value;
  S.forEach((x) => { $('a' + x.k + 'Rate').textContent = x.label; });
  const P = player($('aPlay'), $('aReset'), $('aSpeed'), (t) => frameA(t), { observe: $('aChip') });
  A.P = P;
  async function pick(it) {
    const rec = A.recs[it.id] || (A.recs[it.id] = await J('recordings/' + it.file));
    const L = S.map((x) => { const tl = segments(rec.steps, x.rate, preR); return { ...x, tl, pane: agentPane($('a' + x.k + 'Term'), rec, tl, x.short) }; });
    A.cur = { rec, L };
    A.bars = tlRows($('aTl'), L.map((x) => ({ name: x.short, cls: x.cls, tl: x.tl })));
    $('aTask').innerHTML = `<b>${esc(rec.title)}.</b> ${esc(rec.blurb)} Task given to the agent: “${esc(rec.task)}” <span class="src">recorded ${new Date(rec.recorded * 1000).toISOString().slice(0, 16).replace('T', ' ')} UTC · ${esc(rec.harness)} · API served <b>${esc(rec.model_served.join(', '))}</b> · ${rec.steps.length} model calls, ${rec.steps.reduce((a, s) => a + s.tool_calls.length, 0)} tool calls</span>`;
    const [c, g, o] = L.map((x) => x.tl);
    $('aBig').innerHTML = `${fmtS(c.total)} s <small>vs ${fmtS(g.total)} s best GPU · ${fmtS(o.total)} s OpenRouter</small>`;
    $('aBigSub').textContent = `The session finishes ${(g.total / c.total).toFixed(1)}× sooner than on the best published GPU and ${(o.total / c.total).toFixed(1)}× sooner than at today's median OpenRouter speed. ${fmt(rec.steps.reduce((a, s) => a + s.output_tokens, 0))} generated tokens (${fmt(rec.steps.reduce((a, s) => a + s.reasoning_tokens, 0))} of them reasoning), ${fmt(rec.steps.reduce((a, s) => a + s.prefill_tokens, 0))} prefilled prompt tokens.`;
    splitBars($('aSplit'), L.map((x) => ({ name: x.short, cls: x.cls, tl: x.tl })));
    $('aAmdahl').textContent = `Decode takes ${fmtS(c.decode)} s on our chip, ${fmtS(g.decode)} s on the best GPU and ${fmtS(o.decode)} s at OpenRouter speed. Prefill (${fmtS(c.prefill)} s) and tools (${fmtS(c.tools)} s) are the same in every lane, so the end-to-end gain over the best GPU is ${(g.total / c.total).toFixed(1)}× while decode alone is ${(g.decode / c.decode).toFixed(1)}×. This is Amdahl's law: the faster decode gets, the more the measured tool time dominates.`;
    P.total = Math.max(...L.map((x) => x.tl.total)); P.ready = true; P.restart();
  }
  tabs($('aTabs'), idx.agent, (it) => { pick(it).then(() => { A.P.auto = false; A.P.set(true); }); });
  const G = N.gpu.ds, D = N.designs.find((d) => d.id === 'ds_rom').per_user_mtp;
  $('aNote').innerHTML = `<b>Best GPU</b>: ${fmt(G.per_user.value, 2)} tok/s, <span class="mono">${esc(G.per_user.field)}</span> in <span class="mono">results/external/registry.json</span> (${esc(G.per_user.title)}). It is the best published batch-1 DeepSeek-V4.1 Flash figure we found. Its accept length is simulated at 5.5, above the τ 4.159 our chip is priced at, so it favours the GPU. Other published per-user points: V4.1 Flash on B200 TP4 at concurrency 1, ${fmt(G.per_user_b200.value, 1)} tok/s; V4-Flash on 4 × H200, ${fmt(G.per_user_flash.value)} tok/s. <b>OpenRouter</b>: median P50 of 30 providers, ${fmt(G.served.value, 1)} tok/s (best standard-routed ${fmt(G.served_best.value)} tok/s), <span class="mono">${esc(G.served.field)}</span>. It is a 2026-10-09 snapshot that includes network, queueing and provider load. <b>Our chip</b>: ${fmt(D.value, 1)} tok/s, <span class="mono">${esc(D.source)} · headline.tok_s</span>, i.e. τ 4.159 accepted tokens per 955.7 µs MTP step at 1M context (${esc(D.status)}). <b>Prefill</b> in every lane: ${fmt(preR)} tok/s, <span class="mono">${esc(N.gpu.ds.prefill.source)} · ${esc(N.gpu.ds.prefill.field)}</span> (${esc(N.gpu.ds.prefill.label)}).`;
  return pick(idx.agent[0]);
}
function frameA(t) { if (!A.cur) return; A.cur.L.forEach((x) => { if (t === 0) x.pane.reset(); x.pane.render(t); clockSet($('a' + x.k + 'Clock'), $('a' + x.k), t, x.tl.total, 'wall clock'); }); A.bars.set(t); }
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
    if (c === lastC) return; if (c < lastC) reset(); lastC = c; const st = stick(box); if (c > 0) { const ph = box.querySelector('.ph'); if (ph) ph.remove(); }
    while (full < lines.length && lines[full].e < c) { if (partial) { partial.remove(); partial = null; } const L = lines[full]; if (L.text.trim()) { const m = mdLine(L.text); box.append(el(m.tag, m.cls, m.html)); } full++; }
    if (full < lines.length && c > lines[full].s) { const L = lines[full], m = mdLine(L.text.slice(0, c - L.s)); if (!partial || partial.tagName.toLowerCase() !== m.tag) { if (partial) partial.remove(); partial = el(m.tag, m.cls); box.append(partial); } partial.className = (m.cls ? m.cls + ' ' : '') + 'cursor'; partial.innerHTML = m.html; }
    else if (partial) { partial.remove(); partial = null; }
    if (st) box.scrollTop = box.scrollHeight;
  }
  return { reset, render };
}
const B = {};
function setupB(N, q) {
  const S = sides(N, 'qwen'), preR = N.gpu.qwen.prefill.value, pre = q.prompt_tokens / preR, n = q.output_tokens;
  const cum = []; let o = 0; q.pieces.forEach((p) => { o += p.length; cum.push(o); });
  const L = S.map((x) => ({ ...x, T: pre + n / x.rate, pane: streamPane($('b' + x.k + 'Text'), q.text) }));
  L.forEach((x) => { $('b' + x.k + 'Rate').textContent = x.label; });
  $('bTask').innerHTML = `<b>Prompt:</b> “${esc(q.prompt)}” <span class="src">${fmt(q.prompt_tokens)} prompt tokens → ${fmt(n)} output tokens · ${q.source === 'openrouter' ? `text generated by ${esc(q.model)} via OpenRouter ${esc((q.provider || []).join(', '))} (quantisation reported: ${esc((q.quantization || ['not stated']).join(', '))}), thinking off, ${esc(q.recorded)}; rates from published sources` : `text generated by ${esc(q.model)} (${esc(q.dtype)}, thinking off) on our own machine's CPU, ${esc(q.recorded)}; rates from published sources`}. The text is real model output; only the pacing is modelled.</span>`;
  const [c, g, r] = L;
  $('bBig').innerHTML = `${c.T.toFixed(2)} s <small>vs ${g.T.toFixed(2)} s best GPU · ${r.T.toFixed(1)} s OpenRouter</small>`;
  $('bBigSub').textContent = `${(g.T / c.T).toFixed(1)}× sooner than the best published GPU and ${(r.T / c.T).toFixed(0)}× sooner than today's OpenRouter speed. Every lane starts streaming after the same ${(pre * 1000).toFixed(1)} ms prefill.`;
  splitBars($('bSplit'), L.map((x) => ({ name: x.short, cls: x.cls, tl: { prefill: pre, decode: n / x.rate, tools: 0, total: x.T } })));
  $('bNoteIn').textContent = `Decode: ${fmt(n)} tokens at ${fmt(c.rate, 1)}, ${fmt(g.rate)} and ${fmt(r.rate)} tok/s. Without speculative decoding the same B200 runs ${fmt(N.gpu.qwen.per_user_ar.value)} tok/s, which would take ${(pre + n / N.gpu.qwen.per_user_ar.value).toFixed(1)} s.`;
  const qr = N.designs.find((d) => d.id === 'qwen_rom').per_user, G = N.gpu.qwen;
  $('bNote').innerHTML = `<b>Best GPU</b>: ${fmt(G.per_user.value)} tok/s, <span class="mono">${esc(G.per_user.field)}</span> in <span class="mono">results/external/registry.json</span> (${esc(G.per_user.label)}). It is the best published Qwen3-8B per-user figure in the registry; its MATH-500 acceptance (τ 8.01) favours the GPU. <b>OpenRouter</b>: ${fmt(G.served.value)} tok/s, ${esc(G.served.label)}, snapshot ${esc(G.served.date)}, including network and load. <b>Qwen ROM</b>: ${fmt(qr.value, 1)} tok/s, <span class="mono">${esc(qr.source)} · ${esc(qr.field)}</span> (${esc(qr.mode)}, ${esc(qr.status)}, ${esc(qr.date)}). <b>Prefill</b>: ${fmt(preR)} tok/s, <span class="mono">${esc(G.prefill.source)} · ${esc(G.prefill.field)}</span>. ${q.source === 'openrouter' ? 'The local GPU needs a reset, so the text was generated through OpenRouter.' : 'The local GPU needs a reset, so the text was generated on CPU with the same released weights.'} Generation speed plays no part in the replay.`;
  const P = player($('bPlay'), $('bReset'), $('bSpeed'), (t) => {
    L.forEach((x) => {
      const k = t <= pre ? 0 : Math.min(n, Math.floor((t - pre) * x.rate)); x.pane.render(k ? cum[k - 1] : 0);
      const tEl = $('b' + x.k + 'T'), v = Math.min(t, x.T), s2 = v.toFixed(v < 100 ? 3 : 1); if (tEl._s !== s2) { tEl.textContent = s2; tEl._s = s2; }
      $('b' + x.k + 'P').style.transform = `scaleX(${clamp01(t / x.T)})`; $('b' + x.k).classList.toggle('done', t >= x.T && t > 0);
    });
  }, { observe: $('bChip') });
  P.total = Math.max(...L.map((x) => x.T)); P.ready = true; P.restart(); B.P = P;
  L.forEach((x) => { const b = $('b' + x.k + 'Text'); if (!b.childElementCount) b.append(el('p', 'ph', '<span style="color:var(--fg3)">▶ Play to stream the answer.</span>')); });
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
  const P = player($('cPlay'), $('cReset'), $('cSpeed'), (t) => frameC(t), { observe: $('cChip') }); C.P = P;
  async function pick(it) {
    const rec = C.recs[it.id] || (C.recs[it.id] = await J('recordings/' + it.file));
    const qwen = it.design === 'qwen', S = sides(N, qwen ? 'qwen' : 'ds'), preR = qwen ? N.gpu.qwen.prefill.value : N.gpu.ds.prefill.value;
    const L = S.map((x) => { const tl = segments(rec.steps, x.rate, preR); return { ...x, tl, pane: homePane($('c' + x.k + 'Plan'), $('c' + x.k + 'Tick'), $('c' + x.k + 'Say'), rec, tl) }; });
    L.forEach((x) => { $('c' + x.k + 'Rate').textContent = x.label; $('c' + x.k + 'Name').textContent = x.k === 'Chip' ? (qwen ? 'Qwen ROM hub' : 'DS ROM array') : x.name; });
    C.cur = { rec, L };
    C.bars = tlRows($('cTl'), L.map((x) => ({ name: x.short, cls: x.cls, tl: x.tl })), { thresh: 1, min: 1.2 });
    const nTools = rec.steps.reduce((a, s) => a + s.tool_calls.length, 0), out = rec.steps.reduce((a, s) => a + s.output_tokens, 0), rs = rec.steps.reduce((a, s) => a + s.reasoning_tokens, 0);
    $('cTask').innerHTML = `<b>“${esc(rec.request)}”</b> <span class="src">${esc(rec.model_note)}${rec.served_models && rec.served_models.length ? ' (served: ' + esc(rec.served_models.join(', ')) + ')' : ''} · recorded ${esc(rec.recorded)} · ${rec.steps.length} model calls, ${nTools} device calls, ${fmt(out)} generated tokens (${fmt(rs)} thinking)</span>`;
    const [c, g, o] = L;
    $('cBig').innerHTML = `${fmtS(c.tl.total)} s <small>vs ${fmtS(g.tl.total)} s best GPU · ${fmtS(o.tl.total)} s OpenRouter</small>`;
    $('cBigSub').textContent = `First device moves at ${fmtS(c.pane.firstAction)} s on our chip, ${fmtS(g.pane.firstAction)} s on the best GPU and ${fmtS(o.pane.firstAction)} s at OpenRouter speed. Device calls take ${fmtS(c.tl.tools)} s in every lane; they are measured, and run in parallel where the model asked for it.`;
    $('cWhy').textContent = `In this trace decode is ${Math.round(100 * c.tl.decode / c.tl.total)}% of the chip's time to done, ${Math.round(100 * g.tl.decode / g.tl.total)}% of the best GPU's and ${Math.round(100 * o.tl.decode / o.tl.total)}% at OpenRouter speed.`;
    const alarms = (rec.final_state.alarms || []).map((a) => a.time), wrong = qwen && !alarms.includes('07:30');
    const capped = rec.steps.filter((s) => s.think_capped).length, rejected = rec.steps.reduce((a, s) => a + s.tool_calls.filter((t) => / rejected by the harness$/.test(t.label)).length, 0);
    const qnote = !qwen ? '' : rec.thinking_mode
      ? `The Qwen trace ran in thinking mode${rec.think_budget ? ` with a thinking budget of ${fmt(rec.think_budget)} tokens per turn` : ''}${capped ? ` (${capped} of ${rec.steps.length} turns hit the budget and ${capped === 1 ? 'was' : 'were'} told to answer)` : ' (no turn hit the budget)'}. ${rec.backend === 'openrouter' ? `It ran through OpenRouter (${esc((rec.provider || []).join(', '))}, quantisation reported: ${esc((rec.quantization || ['not stated']).join(', '))}).` : 'It ran on our own machine\'s CPU with the released Qwen3-8B weights (BF16), because the local GPU needs a reset.'} Tools go through Qwen3's native tool-calling format, the system prompt states the tool contract, and the harness validates every call's arguments before it reaches the home${rejected ? ` (${rejected} call${rejected === 1 ? ' was' : 's were'} rejected and returned to the model)` : ''}. An earlier harness without these let thinking runs deliberate for 1,024 and 3,000 tokens without a tool call, and its non-thinking run set the alarm for 22:41. Only token counts and text are used.`
      : 'The Qwen trace ran in non-thinking mode. Only token counts and text are used.';
    $('cNote').innerHTML = (wrong ? `<b>This trace gets the alarm wrong.</b> Qwen3-8B set ${alarms.length ? 'the alarm for ' + esc(alarms.join(', ')) : 'no alarm'} instead of 07:30 (45 minutes before the 08:15 standup). We show the run as recorded. ` : (qwen ? '<b>Correct result:</b> the alarm is set for 07:30, 45 minutes before the 08:15 standup (the calendar lists it second, after the 09:30 dentist). ' : '')) +
      `The mock home answers each device call after a latency drawn from a typical range per device class (lock motor with confirmation 1.0–1.5 s, cloud thermostat 0.55–0.85 s, Zigbee lights 0.2–0.3 s). These latencies are modelled, and the replay uses the wall times we measured. ${qwen ? qnote : 'The DeepSeek trace ran through the DeepSeek API (OpenAI-compatible tool calling); the API reported the reasoning-token counts.'} Rates as in the demos above.`;
    P.total = Math.max(...L.map((x) => x.tl.total)); P.ready = true; P.restart();
  }
  tabs($('cTabs'), idx.home, (it) => pick(it).then(() => { C.P.auto = false; C.P.set(true); }));
  return pick(idx.home[0]);
}
function frameC(t) { if (!C.cur) return; C.cur.L.forEach((x) => { x.pane.render(t); clockSet($('c' + x.k + 'Clock'), $('c' + x.k), t, x.tl.total, 'time to done'); }); C.bars.set(t); }

/* ---------- Demo D: generative UI ---------- */
/* one interaction = the model calls dsh made for one user action; each call: prefill of the new tokens ->
   (chip lanes) KV transfer -> decode of every generated token -> the call's tools at their measured wall time */
function gSegments(calls, rate, kv) {
  const segs = []; let t = 0;
  calls.forEach((c, i) => {
    const add = (k, d) => { if (d > 0) { segs.push({ k, i, t0: t, t1: t + d }); t += d; } };
    add('prefill', c.prefill_s); if (kv) add('kv', c.kv_s); add('decode', c.output_tokens / rate); add('tools', c.tool_s);
  });
  const sum = (k) => segs.filter((x) => x.k === k).reduce((a, x) => a + x.t1 - x.t0, 0);
  return { segs, total: t, prefill: sum('prefill'), kv: sum('kv'), decode: sum('decode'), tools: sum('tools') };
}
const gSum = (it, k) => it.calls.reduce((a, c) => a + c[k], 0);
const gTools = (it) => it.calls.reduce((a, c) => a + c.tool_calls.length, 0);
function gMark(prev, html) {  // put a marker at the first changed tag boundary (not inside <style>), so the patch can be outlined
  let i = 0; const n = Math.min(prev.length, html.length); while (i < n && prev[i] === html[i]) i++;
  let p = html.lastIndexOf('<', i); if (p < 0) return html;
  const so = html.lastIndexOf('<style', p), sc = html.lastIndexOf('</style', p); if (so > sc) return html;
  const vo = html.lastIndexOf('<svg', p), vc = html.lastIndexOf('</svg', p); if (vo > vc) p = vo;      // outline the whole chart, never split an SVG
  const tb = html.search(/<body[\s>]/i); if (tb < 0 || p < tb) return html;
  return html.slice(0, p) + '<span id="ot-edit"></span>' + html.slice(p);
}
function gPane(frame, stat, rec, it, tl) {
  const ev = it.event, before = it.page_before == null ? null : rec.pages[it.page_before];
  const cssq = (v) => String(v).replace(/["\\]/g, '\\$&');
  const hl = ev.kind === 'click' ? `<style>[data-action="${cssq(ev.action)}"]${ev.arg != null ? `[data-arg="${cssq(ev.arg)}"]` : ''}{outline:3px solid #e8925a!important;outline-offset:2px;box-shadow:0 0 0 7px rgba(232,146,90,.3)!important}</style>` : '';
  const blank = `<!doctype html><body style="margin:0;font:14px/1.5 system-ui,sans-serif;color:#6f7889;display:grid;place-items:center;height:100vh;background:#f7f8fa"><div style="max-width:80%;text-align:center">No screen yet.</div></body>`;
  // the page each call leaves on screen, and where in the call's output its HTML / patch tokens sit
  const plan = it.calls.map((c) => { const last = [...c.tool_calls].reverse().find((x) => x.page != null); return { page: last ? last.page : null, kind: last ? last.kind : null }; });
  let cur = { key: null, written: 0 }, lastStat = '';
  const doc = () => { try { return frame.contentDocument; } catch (e) { return null; } };
  const at = (d, m) => { const se = d.scrollingElement; if (m && se) se.scrollTop = Math.max(0, m.getBoundingClientRect().top + se.scrollTop - frame.clientHeight / 2); };
  function show(html, key, mode) {
    if (cur.key === key) return; const d = doc(); if (!d) return;
    d.open(); d.write(html); d.close(); cur = { key, written: html.length };
    if (mode === 'edit') { const m = d.getElementById('ot-edit'); const tg = m && (m.nextElementSibling || m.parentElement); if (tg && tg.style) { tg.style.outline = '3px solid #2f8a68'; tg.style.outlineOffset = '2px'; } at(d, tg); }
    else if (mode === 'click' && ev.kind === 'click') at(d, d.querySelector(`[data-action="${cssq(ev.action)}"]`));
  }
  function stream(html, n, key) {  // incremental document.write of the HTML generated so far
    if (cur.key === key + ':done' && n >= html.length) return;
    const d = doc(); if (!d) return;
    if (cur.key !== key || n < cur.written) { d.open(); cur = { key, written: 0 }; }
    if (n > cur.written) { d.write(html.slice(cur.written, n)); cur.written = n; const se = d.scrollingElement; if (se) se.scrollTop = se.scrollHeight; }
    if (n >= html.length) { d.close(); cur.key = key + ':done'; const se = d.scrollingElement; if (se) se.scrollTop = 0; }
  }
  function render(t) {
    let shown = false, prevPage = before;
    for (let i = it.calls.length - 1; i >= 0 && !shown; i--) {
      const c = it.calls[i], P = plan[i]; if (P.page == null) continue;
      const w = tl.segs.find((s) => s.i === i && s.k === 'decode'); if (!w || t < w.t0) continue;
      const e = clamp01((t - w.t0) / Math.max(1e-9, w.t1 - w.t0)) * c.output_tokens;
      if (P.kind === 'html') {
        const html = rec.pages[P.page], hf = clamp01((e - c.reasoning_tokens - c.tool_tokens) / Math.max(1, c.html_tokens));
        if (hf > 0) { stream(html, Math.round(html.length * hf), 'p' + P.page); shown = true; }
      } else if (t >= w.t1) {
        let pv = before; for (let j = i - 1; j >= 0; j--) if (plan[j].page != null) { pv = rec.pages[plan[j].page]; break; }
        show(gMark(pv || '', rec.pages[P.page]), 'e' + P.page, 'edit'); shown = true;
      }
    }
    if (!shown) {
      show(before ? before + hl : blank, 'b' + it.i, 'click');
    }
    let st = '';
    const wNow = tl.segs.find((s) => t >= s.t0 && t < s.t1);
    if (t >= tl.total && t > 0) st = `<span class="ok">✓ ${it.kind === 'full' ? 'new screen' : it.kind === 'patch' ? 'screen patched' : 'no change'} · ${fmtS(tl.total)} s</span> · ${fmt(gSum(it, 'output_tokens'))} tokens · ${gTools(it)} tool calls`;
    else if (t > 0 && wNow) {
      const c = it.calls[wNow.i], cn = `turn ${wNow.i + 1}/${it.calls.length}`;
      if (wNow.k === 'prefill') st = `<span class="ph">prefill</span> · ${cn} · ${fmt(c.new_tokens)} new tokens`;
      else if (wNow.k === 'kv') st = `<span class="ph">KV → chip</span> · ${cn} · ${fmt(c.kv_bytes / 1e6, 2)} MB`;
      else if (wNow.k === 'tools') st = `<span class="ph">tools</span> · ${cn} · ${c.tool_calls.length} call${c.tool_calls.length === 1 ? '' : 's'}, ${fmtS(c.tool_s)} s measured` + c.tool_calls.slice(0, 3).map((x) => `<span class="tc">→ ${esc(x.label.slice(0, 100))}</span>`).join('') + (c.tool_calls.length > 3 ? `<span class="tc">… +${c.tool_calls.length - 3} more</span>` : '');
      else {
        const e = clamp01((t - wNow.t0) / Math.max(1e-9, wNow.t1 - wNow.t0)) * c.output_tokens, r = c.reasoning_tokens;
        if (e < r) { const k = Math.round(c.thinking.length * e / r); st = `<span class="ph">thinking</span> · ${cn} · ${fmt(e)} / ${fmt(r)} tokens<span class="th">${esc(c.thinking.slice(Math.max(0, k - 150), k))}</span>`; }
        else if (c.html_tokens && e >= r + c.tool_tokens) st = `<span class="ph">writing HTML</span> · ${cn} · ${fmt(e - r - c.tool_tokens)} / ${fmt(c.html_tokens)} tokens`;
        else if (c.patch_tokens && e >= r + c.tool_tokens) st = `<span class="ph">writing a patch</span> · ${cn} · ${fmt(c.patch_tokens)} tokens of find/replace`;
        else if (c.tool_calls.length) st = `<span class="ph">calling tools</span> · ${cn}` + c.tool_calls.filter((x) => x.kind === 'tool').slice(0, 3).map((x) => `<span class="tc">→ ${esc(x.label.slice(0, 100))}</span>`).join('');
        else st = `<span class="ph">replying</span> · ${cn} · “${esc(c.text.slice(0, 60))}”`;
      }
    } else st = ev.kind === 'click' ? `<span class="ph">click</span> · “${esc(ev.label)}”` : `<span class="ph">request</span> · “${esc(ev.text.slice(0, 90))}”`;
    if (st !== lastStat) { stat.innerHTML = st; lastStat = st; }
  }
  return { render, reset() { cur = { key: null, written: 0 }; lastStat = ''; } };
}
const D = { recs: {}, kind: 'full' };
function gLanes(N) {
  const sys = N.systems || {}, hb = ((sys.hbm || {}).targets || []).find((x) => x.id === 'hbm_ds');
  const dsm = (sys.ds_rom && sys.ds_rom.per_user && sys.ds_rom.per_user.MTP) || null, hbm = (hb && hb.per_user && hb.per_user.MTP) || null;
  const Dd = Object.fromEntries(N.designs.map((d) => [d.id, d])), G = N.gpu.ds;
  const dv = dsm ? dsm.value : Dd.ds_rom.per_user_mtp.value, hv = hbm ? hbm.value : Dd.hbm_ds.per_user_mtp.value;
  const src = shortSrc(N.generated_from.systems || N.generated_from.token_path);
  return [
    { k: 'Chip', cls: 'chip', short: 'DS ROM', rate: dv, kv: true, lab: `${fmt(dv, 1)} tok/s · analytical, MTP`, label: `${fmt(dv, 1)} tok/s per user · analytical · MTP τ 4.159 · ${src} ds_rom.per_user.MTP` },
    { k: 'Hbm', cls: 'chip', short: 'HBM', rate: hv, kv: true, lab: `${fmt(hv, 1)} tok/s · analytical, MTP`, label: `${fmt(hv, 1)} tok/s per user · analytical · MTP τ 4.159 · generic die · ${src} hbm.targets[hbm_ds].per_user.MTP` },
    { k: 'Gpu', cls: 'gpu', short: 'Best GPU', rate: G.per_user.value, kv: false, lab: `${fmt(G.per_user.value, 1)} tok/s · 4 × GB300, published`, label: `${fmt(G.per_user.value, 2)} tok/s per user · third-party · ${G.per_user.label}` },
    { k: 'Or', cls: 'or', short: 'OpenRouter', rate: G.served.value, kv: false, lab: `${fmt(G.served.value, 1)} tok/s · median served`, label: `${fmt(G.served.value, 1)} tok/s · ${G.served.label} · snapshot ${G.served.date}` },
  ];
}
function setupD(N, idx) {
  if (!idx.genui || !idx.genui.length) { $('genui').hidden = true; const a = document.querySelector('.nav a[href="#genui"]'); if (a) a.hidden = true; return; }
  const L = gLanes(N); D.L = L; L.forEach((x) => { const e = $('g' + x.k + 'Rate'); e.textContent = x.lab; e.title = x.label; });
  D.P = player($('gPlay'), $('gReset'), $('gSpeed'), (t) => frameD(t), { observe: $('gChip') });
  $('gKind').addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; D.kind = b.dataset.k; $('gKind').querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', x === b)); pickCase(D.case, true); });
  return Promise.all(idx.genui.map((g) => J('recordings/' + g.file))).then((recs) => {
    D.recs = recs; tabs($('gCases'), recs.map((r, i) => ({ title: r.title, i })), (it) => pickCase(it.i, true));
    gSummary(N, recs, L); gMethod(N, recs);
    pickCase(0, false);
  });
}
function pickCase(ci, play) {
  D.case = ci; const rec = D.recs[ci], list = rec.interactions.filter((x) => x.kind === D.kind);
  $('gCases').querySelectorAll('button').forEach((b, j) => b.setAttribute('aria-pressed', j === ci));
  $('gCaseNote').innerHTML = `<b>${esc(rec.title)}.</b> ${esc(rec.blurb)}`;
  const host = $('gInter'); host.innerHTML = '';
  list.forEach((it, j) => { const b = el('button', '', '#' + it.i); b.type = 'button'; b.title = it.event.kind === 'click' ? 'click: ' + it.event.label : it.event.text; b.onclick = () => { pickD(rec, list, j); D.P.auto = false; D.P.set(true); }; host.append(b); });
  gDetail(rec);
  if (list.length) { pickD(rec, list, 0); if (play) { D.P.auto = false; D.P.set(true); } }
}
function pickD(rec, list, j) {
  const it = list[j]; D.list = list; D.j = j; D.rec = rec; D.chained = false;
  $('gInter').querySelectorAll('button').forEach((b, k) => b.setAttribute('aria-pressed', k === j));
  D.cur = D.L.map((x) => { const tl = gSegments(it.calls, x.rate, x.kv); return { ...x, tl, pane: gPane($('g' + x.k + 'Frame'), $('g' + x.k + 'Stat'), rec, it, tl) }; });
  D.bars = tlRows($('gTl'), D.cur.map((x) => ({ name: x.short, cls: x.cls, tl: x.tl })));
  const ev = it.event, S = (k) => gSum(it, k);
  const kinds = {}; it.calls.forEach((c) => c.tool_calls.forEach((x) => { const n = x.kind === 'html' ? 'write screen' : x.kind === 'patch' ? 'edit screen' : x.name; kinds[n] = (kinds[n] || 0) + 1; }));
  $('gTask').innerHTML = (ev.kind === 'click' ? `<b>#${it.i} · The user clicks</b> “${esc(ev.label)}” <span class="mono" style="font-size:12px">data-action="${esc(ev.action)}"</span>` : `<b>#${it.i} · The user asks:</b> “${esc(ev.text)}”`) +
    ` <span class="src">${it.kind === 'full' ? 'The model writes a new screen.' : 'The model patches the screen in place.'} ${it.calls.length} model turns · ${gTools(it)} tool calls (${Object.entries(kinds).map(([k, v]) => `${v} ${k}`).join(', ')}) · ${fmt(S('output_tokens'))} generated tokens: ${fmt(S('reasoning_tokens'))} reasoning, ${fmt(S('tool_tokens'))} tool-call arguments, ${fmt(S('html_tokens'))} HTML, ${fmt(S('patch_tokens'))} patch, ${fmt(S('text_tokens'))} text · ${fmt(S('tool_result_tokens'))} tool-result tokens · ${fmt(S('new_tokens'))} new tokens prefilled · tools ${fmtS(S('tool_s'))} s measured</span>`;
  D.P.total = Math.max(...D.cur.map((x) => x.tl.total)); D.P.ready = true; D.P.restart();
}
function frameD(t) {
  if (!D.cur) return;
  D.cur.forEach((x) => { if (t === 0) x.pane.reset(); x.pane.render(t); clockSet($('g' + x.k + 'Clock'), $('g' + x.k), t, x.tl.total, 'this action'); }); D.bars.set(t);
  if (t >= D.P.total && t > 0 && !D.chained && D.j < D.list.length - 1) {
    D.chained = true; const nx = D.j + 1, list = D.list; setTimeout(() => { if (D.list === list && D.j === nx - 1 && D.chained) { pickD(D.rec, list, nx); D.P.set(true); } }, 1800);
  }
}
function gq(a, q) { const s = [...a].sort((x, y) => x - y); if (!s.length) return NaN; const p = (s.length - 1) * q, lo = Math.floor(p), hi = Math.ceil(p); return s[lo] + (s[hi] - s[lo]) * (p - lo); }
function gStats(list, L) {
  const col = (f) => list.map(f);
  return {
    n: list.length, turns: col((it) => it.calls.length), tools: col(gTools), reasoning: col((it) => gSum(it, 'reasoning_tokens')),
    out: col((it) => gSum(it, 'output_tokens')), html: col((it) => gSum(it, 'html_tokens')), patch: col((it) => gSum(it, 'patch_tokens')), targs: col((it) => gSum(it, 'tool_tokens')),
    res: col((it) => gSum(it, 'tool_result_tokens')), tool_s: col((it) => gSum(it, 'tool_s')), api: col((it) => gSum(it, 'api_s')),
    lanes: L.map((x) => col((it) => gSegments(it.calls, x.rate, x.kv).total)), decode: L.map((x) => col((it) => gSegments(it.calls, x.rate, x.kv).decode)),
  };
}
const gMP = (a, d = 0, s = '') => `${fmt(gq(a, 0.5), d)}${s}<div class="src">p90 ${fmt(gq(a, 0.9), d)}${s}</div>`;
const gMPs = (a) => `${fmtS(gq(a, 0.5))} s<div class="src">p90 ${fmtS(gq(a, 0.9))} s</div>`;
function gSummary(N, recs, L) {
  const rows = [];
  recs.forEach((rec) => ['full', 'patch'].forEach((k) => {
    const list = rec.interactions.filter((x) => x.kind === k); if (!list.length) return; const s = gStats(list, L);
    rows.push(`<tr><td><b>${esc(rec.title)}</b><div class="src">${k === 'full' ? 'full generation' : 'patch'} · ${s.n} interactions</div></td><td class="num">${gMP(s.turns)}</td><td class="num">${gMP(s.tools)}</td><td class="num">${gMP(s.reasoning)}</td><td class="num">${gMP(k === 'full' ? s.html : s.patch)}</td><td class="num">${gMP(s.targs)}</td><td class="num">${gMP(s.res)}</td><td class="num">${gMPs(s.tool_s)}</td>` +
      s.lanes.map((a, j) => `<td class="v ${['lc', 'lc', 'lg', 'lo'][j]}">${fmtS(gq(a, 0.5))} s<div class="src">p90 ${fmtS(gq(a, 0.9))} s · decode ${fmtS(gq(s.decode[j], 0.5))} s</div></td>`).join('') + `<td class="v">${gMPs(s.api)}</td></tr>`);
  }));
  $('gSum').tBodies[0].innerHTML = rows.join('');
  const none = recs.reduce((a, r) => a + r.interactions.filter((x) => x.kind === 'none').length, 0);
  $('gSumNote').innerHTML = `Median, with the 90th percentile under it. “HTML / patch” is the tokens of the new screen (full) or of the find/replace edits (patch). Tool-call arguments are the SQL and shell commands. Tool results are what the tools returned; they are most of the new tokens prefilled. Wall time per lane = prefill + KV transfer (chip lanes) + decode + measured tool time, summed over the model's turns; the median decode time alone is under it. Tool time is the same in every lane, so it sets a floor. It is measured from the end of the model's response to the last tool result, so it includes the harness's own per-call overhead: on our shared test host (load about 25 on 32 cores) even a file read took 1–2 s and an edit about 4 s. It is an upper bound for a tuned harness. In these sessions it is often longer than the chip's decode.${none ? ` ${none} recorded interaction${none === 1 ? '' : 's'} left the screen unchanged (the model found the request already satisfied) and ${none === 1 ? 'is' : 'are'} not counted as patches.` : ''}`;
}
function gDetail(rec) {
  const L = D.L, rows = rec.interactions.map((it) => {
    const tls = L.map((x) => gSegments(it.calls, x.rate, x.kv)), S = (k) => gSum(it, k);
    return `<tr class="${it.kind === D.kind ? '' : 'dim'}"><td><b>#${it.i} ${it.kind === 'full' ? 'full' : it.kind === 'patch' ? 'patch' : 'no change'}</b><div class="src">${esc(it.event.kind === 'click' ? 'click: ' + it.event.label : it.event.text).slice(0, 110)}</div></td><td class="num">${it.calls.length} / ${gTools(it)}</td>` +
      `<td class="num">${fmt(S('output_tokens'))}<div class="src">reasoning ${fmt(S('reasoning_tokens'))} · args ${fmt(S('tool_tokens'))} · HTML ${fmt(S('html_tokens'))} · patch ${fmt(S('patch_tokens'))}</div></td><td class="num">${fmt(S('tool_result_tokens'))}<div class="src">${fmt(S('new_tokens'))} new prefilled</div></td><td class="num">${fmtS(S('tool_s'))} s</td>` +
      tls.map((tl, j) => `<td class="v ${['lc', 'lc', 'lg', 'lo'][j]}">${fmtS(tl.total)} s</td>`).join('') + `<td class="v">${fmtS(S('api_s'))} s</td></tr>`;
  });
  $('gTable').tBodies[0].innerHTML = rows.join('');
}
function gMethod(N, recs) {
  const A = recs[0].assumptions, G = N.gpu.ds, all = recs.flatMap((r) => r.interactions.flatMap((it) => it.calls));
  const lo = Math.min(...all.map((c) => c.prefill_s_low)), hi = Math.max(...all.map((c) => c.prefill_s_low));
  const kvlo = Math.min(...all.map((c) => c.kv_s)), kvhi = Math.max(...all.map((c) => c.kv_s));
  $('gMethod').innerHTML = `
  <p><b>The recordings are real.</b> Every token of reasoning, every SQL query and shell command, and every byte of HTML here is DeepSeek-V4.1 Flash output from the DeepSeek API (served model <span class="mono">${esc(recs[0].model_served.join(', '))}</span>), run by the DeepSeek Harness (${esc(recs[0].harness)}) in a sandbox. The SQL ran against a real 1M-order SQLite database and the shell commands against a real directory tree. Each case is one session; every user action resumes it, so the conversation stays in the prefix cache. Token counts come from the API; the split into reasoning, tool arguments, HTML and patch re-tokenises each part with the DeepSeek-V4.1 tokenizer and scales it to the API's output count. Only the replay rate differs between lanes.</p>
  <p><b>Wall time per action.</b> It is the sum over the model's turns of four parts. <b>Prefill</b> covers only the new tokens since the previous turn (the user's event, or the tool results); the cached prefix is free. <b>KV transfer</b> applies in the chip lanes only. <b>Decode</b> is every generated token (reasoning, tool-call arguments, HTML or patch, text) at the lane's per-user rate. <b>Tools</b> run at their measured wall time, the same in every lane. That time runs from the end of the model's response to the last tool result and includes the harness's per-call overhead on a loaded host. The harness's further gap before its next request (typically 2–3 s) is not counted, and neither is user think time.</p>
  <p><b>Prefill</b> runs on 8 B200 GPUs in every lane, so the comparison isolates decode. It uses the repository's turn model (<span class="mono">${esc(A.prefill_model)}</span>). The FLOP rate is calibrated from ${esc(A.prefill_cite)}. At these sizes the ${fmt(A.layers)}-layer expert-parallel floor dominates: ${fmt(A.ep_layer_floor_s * 1000, 1)} ms per layer (<b>assumed</b>, DeepEP low-latency dispatch + combine class), so ${fmt(A.ep_floor_s * 1000, 1)} ms per turn. Compute alone would take ${fmt(lo * 1000, 2)}–${fmt(hi * 1000, 1)} ms. We found no published batch-1 time to first token for a DeepSeek-V3/V4-class model with a cached prefix, so this is a bound, not a measurement.</p>
  <p><b>KV transfer to the chip</b>: ${esc(A.kv_model)}, over ${fmt(A.link_Bps / 1e9, 1)} GB/s (${esc(A.link_note)}). That is ${fmt(kvlo * 1e6, 0)}–${fmt(kvhi * 1e6, 0)} µs per turn. The HBM lane is charged the same link, because its own ingest path has not been composed. The GPU lanes prefill and decode on one node and pay no transfer.</p>
  <p><b>Not modelled.</b> The network between the user and the server, the browser's render time, and the harness's own time between turns are not modelled. They would add the same amount to every lane. The OpenRouter lane uses the median served decode rate (${fmt(G.served.value, 1)} tok/s), not OpenRouter's real time to first token, so it is optimistic for OpenRouter. The last column is what the DeepSeek API actually took for the model calls, measured from our client.</p>
  <p><b>Rates.</b> The chip rates are analytical per-user MTP rates at 1M context (τ 4.159), read live from <span class="mono">${esc(shortSrc(N.generated_from.systems || ''))}</span>. These sessions run at 10K–150K context, so the chip rates are conservative. Best GPU: ${fmt(G.per_user.value, 2)} tok/s, ${esc(G.per_user.title)}. Its accept length is simulated at 5.5, which favours the GPU. OpenRouter: ${esc(G.served.label)}, snapshot ${esc(G.served.date)}.</p>`;
}

/* ---------- numbers table + hero ---------- */
function numbers(N) {
  const D = Object.fromEntries(N.designs.map((d) => [d.id, d])), G = N.gpu;
  const ref = (o) => o ? `<div class="src">${o.stale ? '' : (o.source === 'results/external/registry.json' ? 'third-party · ' : 'analytical · ')}${esc(shortSrc(o.source))} · ${esc(o.field)}${o.date ? ' · ' + esc(o.date) : ''}</div>` : '';
  const v = (o, d = 1) => o ? `${fmt(o.value, o.value > 10000 ? 0 : d)}${o.stale ? '<span class="stale" title="' + esc(o.note) + '">STALE</span>' : ''}${ref(o)}${o.note ? `<div class="src">${esc(o.note)}</div>` : ''}` : '<span style="color:var(--fg3)">not in the registry</span>';
  const pair = (a, b) => `${fmt(a.value, 1)} / ${fmt(b.value, 1)}${ref(a)}${ref(b)}`;
  const cap = D.ds_rom.capacity;
  const capCell = `≤ ${fmt(cap.ar_agg_bound, 0)} / ≤ ${fmt(cap.mtp_agg_bound, 0)}<span class="stale" style="color:var(--fg2);border-color:var(--line2)" title="${esc(cap.rule)}">DERIVED</span><div class="src">per instance: 1/II and τ/(6·II), II ${cap.II_us} µs · ${esc(shortSrc(cap.source))} · ${esc(cap.field)} · ${esc(cap.date)}</div><div class="src">full per-user rate up to about ${cap.ar_users} users (AR) or ${cap.mtp_users} (MTP) per instance; an upper bound, not a committed aggregate</div><div style="margin-top:8px">${v(D.ds_rom.aggregate_mtp)}</div>`;
  const rows = [
    ['ours', 'Qwen ROM', 'Qwen3-8B · 8K · AR', v(D.qwen_rom.per_user), v(D.qwen_rom.aggregate, 0), D.qwen_rom.per_user.status],
    ['ours', 'DS ROM array', 'DeepSeek-V4.1 Flash · 1M · AR / MTP', pair(D.ds_rom.per_user, D.ds_rom.per_user_mtp), capCell, D.ds_rom.per_user_mtp.status],
    ['ours', 'HBM accelerator', 'DeepSeek-V4.1 Flash · 1M · AR / MTP', pair(D.hbm_ds.per_user, D.hbm_ds.per_user_mtp), v(D.hbm_ds.aggregate) + '<br>' + v(D.hbm_ds.aggregate_mtp), D.hbm_ds.per_user_mtp.status],
    ['gpu', 'Best GPU · Qwen3-8B', esc(G.qwen.per_user.label), v(G.qwen.per_user, 0) + `<div class="src">no speculation: ${fmt(G.qwen.per_user_ar.value)} tok/s</div>`, v(null), 'published, third-party'],
    ['gpu', 'Best GPU · DeepSeek-V4.1 Flash', esc(G.ds.per_user.label), v(G.ds.per_user, 2) + `<div class="src">B200 TP4, concurrency 1: ${fmt(G.ds.per_user_b200.value, 1)} · V4-Pro on 8 × B300: ${fmt(G.ds.per_user_pro.value, 1)} · V4-Flash on 4 × H200: ${fmt(G.ds.per_user_flash.value)}</div>`, v(G.ds.aggregate, 0) + `<div class="src">${esc(G.ds.aggregate.label)}</div>`, 'published, third-party'],
    ['or', 'OpenRouter · Qwen3-8B', 'served today, one provider', v(G.qwen.served, 0), v(null), 'snapshot 2026-10-09, includes network and load'],
    ['or', 'OpenRouter · DeepSeek-V4.1 Flash', 'served today, median of 30 providers', v(G.ds.served, 1) + `<div class="src">best standard-routed provider: ${fmt(G.ds.served_best.value)}</div>`, v(null), 'snapshot 2026-10-09, includes network and load'],
  ];
  $('numsTable').tBodies[0].innerHTML = rows.map(([c, m, mm, pu, ag, st]) => `<tr class="${c}"><td><b>${esc(m)}</b><div style="margin-top:4px">${c === 'ours' ? '<span class="tag-a">analytical</span>' : c === 'gpu' ? '<span class="tag-g">third-party</span>' : '<span class="tag-g">served snapshot</span>'}</div></td><td>${mm}</td><td class="v">${pu}</td><td class="v${/^(<span|≤)/.test(ag) || /STALE/.test(ag.slice(0, 200)) ? ' dim' : ''}">${ag}</td><td style="font-size:13px;color:var(--fg2)">${esc(st)}</td></tr>`).join('');
  $('numsNote').innerHTML = `Read from <span class="mono">${esc(N.generated_from.token_path)}</span> and <span class="mono">${esc(N.generated_from.reprice)}</span> (repriced ${esc(N.generated_from.reprice_date)}), <span class="mono">${esc(D.qwen_rom.aggregate.source)}</span>, and <span class="mono">results/external/registry.json</span>. The DS ROM and HBM aggregates have not been recomputed for the 2026-10-08 design points. The DS ROM bound is derived on this page from the committed pipeline interval. The HBM figures are the newest committed aggregates, from earlier designs, and are marked STALE.`;
  const hs = (id, ours, gpu) => { $(id).innerHTML = `${fmt(ours.value, 0)}<small>tok/s</small>`; $(id + '-s').innerHTML = `${(ours.value / gpu.value).toFixed(1)}× the best published GPU at batch 1 (${fmt(gpu.value, 0)})<br>analytical · ${esc(shortSrc(ours.source))} · ${esc(ours.date)}`; };
  hs('hs-qwen', D.qwen_rom.per_user, G.qwen.per_user); hs('hs-ds', D.ds_rom.per_user_mtp, G.ds.per_user); hs('hs-hbm', D.hbm_ds.per_user_mtp, G.ds.per_user);
  chart(N, 'ds');
  $('chTabs').addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; $('chTabs').querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', x === b)); chart(N, b.dataset.m); });
}

/* per-user tok/s vs concurrent users, log-log */
function chart(N, m) {
  const svg = $('chart'), tip = $('chTip'), NS = 'http://www.w3.org/2000/svg';
  const mk = (t, a, p = svg) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); p.append(e); return e; };
  svg.innerHTML = ''; tip.hidden = true;
  const W = 760, H = 360, l = 64, r = 150, t = 18, b = 46, X0 = 1, X1 = 128, Y0 = 30, Y1 = 10000;
  const x = (u) => l + (Math.log(u / X0) / Math.log(X1 / X0)) * (W - l - r), y = (v) => t + (1 - Math.log(v / Y0) / Math.log(Y1 / Y0)) * (H - t - b);
  [100, 1000, 10000].forEach((v) => { mk('line', { class: 'grid', x1: l, x2: W - r, y1: y(v), y2: y(v) }); const tx = mk('text', { class: 'ax', x: l - 8, y: y(v) + 4, 'text-anchor': 'end' }); tx.textContent = fmt(v); });
  [1, 2, 4, 8, 16, 32, 64, 128].forEach((u) => { const tx = mk('text', { class: 'ax', x: x(u), y: H - b + 18, 'text-anchor': 'middle' }); tx.textContent = u; });
  const xt = mk('text', { class: 'axt', x: (l + W - r) / 2, y: H - 8, 'text-anchor': 'middle' }); xt.textContent = 'concurrent users on one machine instance (log)';
  const yt = mk('text', { class: 'axt', x: 14, y: (t + H - b) / 2, 'text-anchor': 'middle', transform: `rotate(-90 14 ${(t + H - b) / 2})` }); yt.textContent = 'tok/s per user (log)';
  const pts = []; // hover targets
  const path = (arr, stroke, dash) => mk('path', { d: arr.map((p, i) => (i ? 'L' : 'M') + x(p[0]).toFixed(1) + ' ' + y(p[1]).toFixed(1)).join(' '), fill: 'none', style: `stroke:${stroke};stroke-width:2${dash ? ';stroke-dasharray:' + dash : ''}`, 'stroke-linejoin': 'round' });
  const dot = (u, v, fill, txt, hollow) => { mk('circle', { cx: x(u), cy: y(v), r: 4.5, style: hollow ? `fill:var(--panel);stroke:${fill};stroke-width:2` : `fill:${fill};stroke:var(--panel);stroke-width:2` }); pts.push({ u, v, txt }); };
  const lab = (u, v, txt, sub, color, dy = 0) => { const a = mk('text', { class: 'lab', x: x(u) + 8, y: y(v) + dy, style: `fill:var(--fg)` }); a.textContent = txt; if (sub) { const c = mk('text', { class: 'labs', x: x(u) + 8, y: y(v) + dy + 14 }); c.textContent = sub; } };
  const ds = m === 'ds', D = N.designs.find((d) => d.id === (ds ? 'ds_rom' : 'qwen_rom')), G = ds ? N.gpu.ds : N.gpu.qwen;
  const R = ds ? D.per_user_mtp.value : D.per_user.value, Agg = ds ? D.capacity.mtp_agg_bound : D.aggregate.value, sat = Agg / R;
  // our chip, one instance
  const one = []; for (let u = 1; u <= X1; u *= 1.08) one.push([u, Math.min(R, Agg / u)]); one.push([X1, Math.min(R, Agg / X1)]);
  path(one.filter((p) => p[0] <= sat + 1e-9).concat([[sat, R]]), 'var(--s-chip)');
  path(one.filter((p) => p[0] >= sat), 'var(--s-chip)', '6 5');
  path([[sat, R], [X1, R]], 'var(--s-chip)', '2 4');
  dot(1, R, 'var(--s-chip)', `${ds ? 'DS ROM array (MTP)' : 'Qwen ROM'}: ${fmt(R, 1)} tok/s per user, analytical`);
  dot(sat, R, 'var(--s-chip)', `one instance saturates near ${sat.toFixed(1)} users (${fmt(Agg, 0)} tok/s aggregate${ds ? ', derived upper bound' : ', modelled ceiling'})`, true);
  lab(X1, R, ds ? 'DS ROM, more instances' : 'Qwen ROM, more instances', `one per ~${sat.toFixed(1)} users`, 'var(--s-chip)', -14);
  lab(X1, Agg / X1, 'one instance', 'past its capacity', 'var(--s-chip)', 4);
  // GPU
  if (ds && G.curve) {
    const c = G.curve.points.filter((p) => p.c <= X1);
    path(c.map((p) => [p.c, p.per_user]), 'var(--s-gpu)');
    c.forEach((p) => dot(p.c, p.per_user, 'var(--s-gpu)', `B200 TP4, ${p.c} concurrent: ${fmt(p.per_user, 1)} tok/s per user (p90), ${fmt(p.per_gpu, 0)} tok/s per GPU`));
    lab(1, c[0].per_user, 'GPU, B200 × 4, by concurrency', 'V4.1 Flash, InferenceX, p90', 'var(--s-gpu)', 30);
    dot(1, G.per_user.value, 'var(--s-gpu)', `GB300 × 4, batch 1: ${fmt(G.per_user.value, 2)} tok/s (SGLang + DSpark, simulated accept 5.5)`, true);
    lab(1, G.per_user.value, 'GB300 × 4, batch 1', '', 'var(--s-gpu)', -8);
  } else {
    dot(1, G.per_user.value, 'var(--s-gpu)', `B200 + DFlash, concurrency 1: ${fmt(G.per_user.value)} tok/s (MATH-500)`);
    dot(1, G.per_user_ar.value, 'var(--s-gpu)', `B200, concurrency 1, no speculation: ${fmt(G.per_user_ar.value)} tok/s`, true);
    lab(1, G.per_user.value, 'B200 + DFlash', '', 'var(--s-gpu)', 4); lab(1, G.per_user_ar.value, 'B200, plain', '', 'var(--s-gpu)', 4);
  }
  // OpenRouter reference
  mk('line', { x1: l, x2: W - r, y1: y(G.served.value), y2: y(G.served.value), style: 'stroke:var(--or);stroke-width:1.5;stroke-dasharray:4 4' });
  { const a = mk('text', { class: 'labs', x: l + 6, y: y(G.served.value) - 6 }); a.textContent = `OpenRouter today, median served ${fmt(G.served.value, ds ? 1 : 0)} tok/s (concurrency unknown)`; }
  $('chTitle').textContent = ds ? 'DeepSeek-V4.1 Flash' : 'Qwen3-8B';
  $('chLegend').innerHTML = `<span style="--c:var(--s-chip)">${ds ? 'DS ROM array, MTP' : 'Qwen ROM'} (analytical)</span><span style="--c:var(--s-gpu)">GPU (third-party)</span><span style="--c:var(--or)">OpenRouter median served speed (snapshot)</span>`;
  $('chNote').innerHTML = ds
    ? `Our chip keeps its per-user rate until one instance's pipeline is full, then you add instances. The capacity is <b>derived on this page</b> from the committed stage interval (II ${D.capacity.II_us} µs, <span class="mono">${esc(D.capacity.source)} · ${esc(D.capacity.field)}</span>): at most τ/(6·II) = ${fmt(D.capacity.mtp_agg_bound, 0)} tok/s per instance. That is an upper bound that ignores draft-die and collective contention. GPU curve: <span class="mono">${esc(G.curve.field)}</span> (${esc(G.curve.label)}, ${esc(G.curve.date)}). The GPU instance is 4 B200s; ours is the full ROM array.`
    : `Qwen ROM: ${fmt(D.aggregate.value, 0)} tok/s per instance (${esc(D.aggregate.label)}), bound by ${esc(D.aggregate.binding)}, so full per-user rate up to about ${D.aggregate.users_to_saturate} users, <span class="mono">${esc(D.aggregate.source)} · ${esc(D.aggregate.field)}</span> (${esc(D.aggregate.date)}). The registry has no published Qwen3-8B per-user-versus-concurrency curve for a GPU, so only the concurrency-1 points are shown.`;
  svg.onpointermove = (e) => {
    const bb = svg.getBoundingClientRect(), sx = (e.clientX - bb.left) * W / bb.width, sy = (e.clientY - bb.top) * H / bb.height;
    let best = null, bd = 1e9; pts.forEach((p) => { const d = Math.hypot(x(p.u) - sx, y(p.v) - sy); if (d < bd) { bd = d; best = p; } });
    if (!best || bd > 24) { tip.hidden = true; return; }
    tip.hidden = false; tip.innerHTML = esc(best.txt); const box = svg.parentElement.getBoundingClientRect();
    tip.style.left = Math.min(box.width - 270, Math.max(0, e.clientX - box.left + 12 + svg.parentElement.scrollLeft)) + 'px'; tip.style.top = (e.clientY - box.top + 12) + 'px';
  };
  svg.onpointerleave = () => { tip.hidden = true; };
}

/* ---------- boot ---------- */
let last = performance.now();
function loop(now) { const dt = Math.min(0.1, (now - last) / 1000); last = now; die.tick(now); [A.P, B.P, C.P, D.P].forEach((p) => p && p.step(dt)); requestAnimationFrame(loop); }
requestAnimationFrame(loop);
(async () => {
  try {
    const [N, idx] = await Promise.all([J('/api/landing/numbers'), J('recordings/index.json')]);
    if (N.error) throw new Error(N.error);
    numbers(N);
    const q = idx.long ? await J('recordings/' + idx.long) : null;
    await Promise.all([setupA(N, idx), q ? setupB(N, q) : null, setupC(N, idx), setupD(N, idx)]);
    $('recInfo').textContent = `${idx.agent.length} dsh coding sessions, ${idx.home.length} home-hub traces, 1 long Qwen3-8B answer, ${(idx.genui || []).length} generative-UI sessions, all recorded 2026-10-09`;
  } catch (e) {
    console.warn('landing:', e); $('aTask').textContent = 'Could not load the numbers or recordings: ' + e.message;
  }
})();
})();

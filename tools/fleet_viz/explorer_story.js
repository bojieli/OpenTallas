/* Chip Explorer element stories for the fleet-viz /explorer page: the story renderer of the Chip Explorer site
   (site/chip_explorer/src/app.js, section 7), ported unchanged (helpers + stBodyHtml / stDiaHtml / stBind / stDraw /
   dg* diagrams).  OTStory.render(container, card, legend) shows one card open. */
(function(){
'use strict';
const $ = id => document.getElementById(id);
const st = x => (x && typeof x === 'object' && 'status' in x) ? x.status : 'measured';
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt = (n, d = 1) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
const fmt0 = n => fmt(n, 0);
const SVGNS = 'http://www.w3.org/2000/svg';
const reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
function css(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function pill(s){ return `<span class="pill p-${esc(s)}"><i></i>${esc(s)}</span>`; }
function cpill(c){ return `<span class="pill c-${esc(c)}"><i></i>${esc(CLOSURE_LABEL[c] || c)}</span>`; }
function svgEl(tag, attrs, parent){ const e = document.createElementNS(SVGNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function clear(n){ while (n.firstChild) n.removeChild(n.firstChild); }
function hideTip(){ tip.hidden = true; }
function lsGet(k, d){ try { const v = localStorage.getItem('otx.' + k); return v == null ? d : v; } catch (e) { return d; } }
function lsSet(k, v){ try { localStorage.setItem('otx.' + k, v); } catch (e) {} }
function sizeSvg(svg, W, H){ svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', Math.ceil(H)); }
function txt(parent, x, y, s, o = {}){ const t = svgEl('text', Object.assign({x, y, 'font-size': o.fs || 12, 'font-family': o.mono === false ? 'var(--f-body)' : 'var(--f-mono)', fill: o.fill || css('--muted')}, o.anchor ? {'text-anchor': o.anchor} : {}, o.weight ? {'font-weight': o.weight} : {}), parent); t.textContent = s; return t; }
/* wrap a string into lines that fit `maxW` px at a mono font of size fs (0.6 em per glyph) */
function wrapLines(s, maxW, fs){ const per = Math.max(8, Math.floor(maxW / (fs * 0.6))); const out = []; let cur = ''; for (const w of s.split(' ')){ if ((cur + ' ' + w).trim().length > per && cur){ out.push(cur); cur = w; } else cur = (cur + ' ' + w).trim(); } if (cur) out.push(cur); return out; }
function txtWrap(parent, x, y, s, maxW, o = {}){ const fs = o.fs || 12, lh = o.lh || fs * 1.35; const ls = wrapLines(s, maxW, fs); ls.forEach((l, i) => txt(parent, x, y + i * lh, l, o)); return ls.length * lh; }
function mix(c1, c2, t){ // hex mix for shading
  const p = c => { c = c.replace('#', ''); if (c.length === 3) c = c.split('').map(x => x + x).join(''); return [0, 2, 4].map(i => parseInt(c.substr(i, 2), 16)); };
  try { const a = p(c1), b = p(c2); return '#' + a.map((v, i) => Math.round(v + (b[i] - v) * t).toString(16).padStart(2, '0')).join(''); } catch (e) { return c1; }
}
function niceTicks(a, b, n){ const span = b - a; const step0 = span / n; const mag = Math.pow(10, Math.floor(Math.log10(step0))); const err = step0 / mag; const step = (err >= 5 ? 10 : err >= 2 ? 5 : err >= 1 ? 2 : 1) * mag; const out = []; for (let v = Math.ceil(a / step) * step; v <= b + 1e-9; v += step) out.push(+v.toFixed(6)); return out; }
/* ================================================================ element stories (section 7)
   Cards come from DATA.stories (tools/chip_explorer_stories.py). Every number in a card's prose is a fact listed
   in its reviewer table with the record it came from. Diagrams are schematic and step one event at a time; bar
   charts plot recorded values only. */
const ST = { target: lsGet('stTarget', 'all'), status: lsGet('stStatus', 'all'), open: new Set(), mode: {}, step: {}, timers: {} };
const ST_TARGET = { ds: 'DeepSeek ROM array', hbm: 'HBM accelerator', qwen: 'Qwen ROM', x: 'Cross-cutting' };
const ST_ORDER = ['ds', 'hbm', 'qwen', 'x'];
const ST_STATUS = ['closed', 'in progress', 'gated', 'reference'];
const DGK = { bad: '--s-open', good: '--s-closed', field: '--k-field', su: '--k-su', ctrl: '--k-ctrl', hbm: '--k-hbm', wire: '--k-wire', idle: '--k-res',
  op0: '--k-field', op1: '--k-attn', op2: '--k-hc', op3: '--k-ctrl' };
function sbadge(s){ return `<span class="sb sb-${esc(s.replace(' ', '-'))}"><i></i>${esc(s)}</span>`; }
function stCards(){ return (DATA.stories && DATA.stories.cards) || []; }
function stFiltered(){ return stCards().filter(c => (ST.target === 'all' || c.target === ST.target) && (ST.status === 'all' || c.status === ST.status)); }
function stFmt(f){ const v = f.v; if (typeof v !== 'number') return esc(v); const d = Number.isInteger(v) && Math.abs(v) >= 1 ? 0 : (Math.abs(v) < 10 ? 3 : 2); return fmt(v, d).replace('-', '−'); }

function renderStories(){
  const cards = stCards();
  if (!cards.length){ $('stCount').textContent = 'No story data in this build.'; return; }
  const cnt = (key, val) => cards.filter(c => c[key] === val).length;
  const chip = (grp, val, label, n) => `<button type="button" class="chip" data-st-${grp}="${esc(val)}" aria-pressed="${ST[grp] === val}">${esc(label)} <span class="muted">${n}</span></button>`;
  $('stFilters').innerHTML =
    `<span class="lab">Target</span><div class="chips" role="group" aria-label="Filter by target">${chip('target', 'all', 'All', cards.length)}${ST_ORDER.map(t => chip('target', t, ST_TARGET[t], cnt('target', t))).join('')}</div>` +
    `<span class="lab">Status</span><div class="chips" role="group" aria-label="Filter by status">${chip('status', 'all', 'All', cards.length)}${ST_STATUS.map(s => chip('status', s, s, cnt('status', s))).join('')}</div>`;
  $('stFilters').querySelectorAll('[data-st-target]').forEach(b => b.onclick = () => { ST.target = b.dataset.stTarget; lsSet('stTarget', ST.target); renderStories(); });
  $('stFilters').querySelectorAll('[data-st-status]').forEach(b => b.onclick = () => { ST.status = b.dataset.stStatus; lsSet('stStatus', ST.status); renderStories(); });
  const shown = stFiltered();
  $('stCount').textContent = `${shown.length} of ${cards.length} stories` + (ST.target !== 'all' || ST.status !== 'all' ? ' match the filter.' : '.');
  $('stGroups').innerHTML = ST_ORDER.map(t => {
    const cs = shown.filter(c => c.target === t); if (!cs.length) return '';
    return `<div class="st-group"><h3>${esc(ST_TARGET[t])} <small>${cs.length} ${cs.length === 1 ? 'story' : 'stories'}</small></h3><div class="st-grid">${cs.map(stCardHtml).join('')}</div></div>`;
  }).join('') || '<p class="muted">No story matches this filter.</p>';
  $('stGroups').querySelectorAll('[data-st-open]').forEach(b => b.onclick = () => stToggle(b.dataset.stOpen));
  $('stSrc').textContent = `Status is recomputed at build time from committed closure-loop verdicts (results/closure_loop/*/verdict.json); routes not yet closed are shown from the ${DATA.stories.loop_src}. Diagrams are schematic; bar charts plot recorded values.`;
  shown.filter(c => ST.open.has(c.id)).forEach(stBind);
}
function stCardHtml(c){
  const open = ST.open.has(c.id);
  return `<article class="st-card" id="story-${esc(c.id)}" data-open="${open}">
    <div class="top"><div class="el">${esc(ST_TARGET[c.target])} · ${esc(c.element)}</div>${sbadge(c.status)}</div>
    <h4>${esc(c.title)}</h4>
    <p class="sum">${esc(c.summary)}</p>
    ${open ? stBodyHtml(c) : ''}
    <button type="button" class="btn small open" data-st-open="${esc(c.id)}" aria-expanded="${open}" aria-controls="story-${esc(c.id)}">${open ? 'Close story' : 'Open story'}</button>
  </article>`;
}
function stToggle(id){
  if (ST.open.has(id)){ ST.open.delete(id); stStop(id + '/main'); stStop(id + '/extra'); } else ST.open.add(id);
  renderStories();
  const el = $('story-' + id); if (el && ST.open.has(id)) el.scrollIntoView({behavior: reduceMotion ? 'auto' : 'smooth', block: 'start'});
  try { history.replaceState(null, '', ST.open.has(id) ? '#story-' + id : location.pathname + location.search); } catch (e) {}
}
function stDiaHtml(c, which, title){
  const key = c.id + '/' + which;
  return `<div class="st-dia" data-dia="${esc(key)}">
    <div class="tools">
      ${which === 'main' ? `<div class="seg" role="group" aria-label="Design shown"><button type="button" data-mode="naive" aria-pressed="${(ST.mode[c.id] || 'trick') === 'naive'}">Naive design</button><button type="button" data-mode="trick" aria-pressed="${(ST.mode[c.id] || 'trick') === 'trick'}">The trick</button></div>` : `<span class="eyebrow">${esc(title || '')}</span>`}
      <button type="button" class="btn small" data-act="back" aria-label="Previous step">&#9664; Step</button>
      <button type="button" class="btn small" data-act="play" aria-pressed="false">Play</button>
      <button type="button" class="btn small" data-act="fwd" aria-label="Next step">Step &#9654;</button>
      <span class="ctr" data-ctr></span>
    </div>
    ${which === 'main' ? '<div class="txt"><h6 data-ttl></h6><p data-txt></p></div>' : ''}
    <div class="scroll"><svg role="img" data-svg></svg></div>
    <p class="cap" data-cap aria-live="polite"></p>
    <p class="schem" data-schem></p>
  </div>`;
}
function stBodyHtml(c){
  const facts = c.facts.map(f => `<tr><td>${esc(f.label)}</td><td class="n">${stFmt(f)}</td><td>${esc(f.unit)}</td><td>${pill(f.status)}</td><td class="src">${esc(f.src)}</td></tr>`).join('');
  const blocks = (c.blocks || []).map(b => `<tr><td class="mono" style="font-size:12px">${esc(b.block)}</td><td>${b.closed ? sbadge('closed') + ` SS ${fmt(b.closed.ss, 2)} / FF ${fmt(b.closed.ff, 2)} ps` : (b.best_fail ? `best so far SS ${fmt(b.best_fail.ss_ps, 2)} / FF ${fmt(b.best_fail.ff_ps, 2)} ps (${esc(b.best_fail.status)})` : 'no measured route yet')}${b.live ? `; ${b.live} route${b.live > 1 ? 's' : ''} queued or running` : ''}</td><td class="src">${b.closed ? esc(b.closed.src) : esc(b.best_fail ? b.best_fail.job : (b.live_jobs || []).join(', '))}</td></tr>`).join('');
  const tried = c.tried.length ? `<ul>${c.tried.map(t => `<li><b>${esc(t.name)}</b>: ${esc(t.result)}. ${esc(t.why)} <span class="recs">[${esc(t.src)}]</span></li>`).join('')}</ul>` : `<p class="muted">No failed variant of this element was routed. The naive design above is the one the model or the first measurement rejected.</p>`;
  return `<div class="st-body">
    <div><h5>The problem</h5><p>${esc(c.problem)}</p></div>
    ${stDiaHtml(c, 'main')}
    ${c.diagram && c.diagram.extra ? stDiaHtml(c, 'extra', c.diagram.extra.title) : ''}
    <div class="st-pair"><div><h5>Evidence</h5><p>${esc(c.evidence)}</p></div><div><h5>Price paid</h5><p>${esc(c.price)}</p></div></div>
    <details><summary>Reviewer depth: every number, its status and its record</summary>
      <p class="muted" style="font-size:13px;margin:4px 0 8px">Status: ${sbadge(c.status)} ${esc(c.status_basis || DATA.stories.legend[c.status] || '')}</p>
      <div class="scroll"><table><thead><tr><th>Fact</th><th class="n">Value</th><th>Unit</th><th>Status</th><th>Record</th></tr></thead><tbody>${facts}</tbody></table></div>
      ${blocks ? `<h5 style="margin-top:12px">Closure blocks</h5><div class="scroll"><table><thead><tr><th>Block</th><th>State</th><th>Record</th></tr></thead><tbody>${blocks}</tbody></table></div>` : ''}
      <h5 style="margin-top:12px">Records</h5><p class="recs">${c.records.map(esc).join('<br>')}</p>
    </details>
    <details><summary>What we tried first (${c.tried.length})</summary>${tried}</details>
  </div>`;
}
function stSpec(c, which){ const d = c.diagram || {}; return which === 'extra' ? d.extra : (ST.mode[c.id] || 'trick') === 'naive' ? d.naive : d.trick; }
function stNSteps(sp){ if (!sp) return 1; if (sp.steps && sp.steps.length) return sp.steps.length; if (sp.kind === 'pipe' || sp.kind === 'ring') return sp.cycles; return 1; }
function stBind(c){
  const card = $('story-' + c.id); if (!card) return;
  card.querySelectorAll('[data-dia]').forEach(box => {
    const key = box.dataset.dia, which = key.split('/')[1];
    box.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => { ST.mode[c.id] = b.dataset.mode; ST.step[key] = 0; stStop(key); box.querySelectorAll('[data-mode]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); stDraw(c, which); });
    box.querySelector('[data-act="back"]').onclick = () => { stStop(key); ST.step[key] = Math.max(0, (ST.step[key] || 0) - 1); stDraw(c, which); };
    box.querySelector('[data-act="fwd"]').onclick = () => { stStop(key); ST.step[key] = Math.min(stNSteps(stSpec(c, which)) - 1, (ST.step[key] || 0) + 1); stDraw(c, which); };
    box.querySelector('[data-act="play"]').onclick = e => {
      if (ST.timers[key]){ stStop(key); return; }
      const n = stNSteps(stSpec(c, which)); if ((ST.step[key] || 0) >= n - 1) ST.step[key] = 0;
      e.currentTarget.setAttribute('aria-pressed', 'true'); e.currentTarget.textContent = 'Pause'; stDraw(c, which);
      ST.timers[key] = setInterval(() => { const m = stNSteps(stSpec(c, which)); if ((ST.step[key] || 0) >= m - 1){ stStop(key); return; } ST.step[key] = (ST.step[key] || 0) + 1; stDraw(c, which); }, 1100);
    };
    if (ST.step[key] == null) ST.step[key] = which === 'main' ? 0 : 0;
    stDraw(c, which);
  });
}
function stStop(key){ if (ST.timers[key]){ clearInterval(ST.timers[key]); delete ST.timers[key]; } const box = document.querySelector(`[data-dia="${key}"]`); if (box){ const p = box.querySelector('[data-act="play"]'); if (p){ p.setAttribute('aria-pressed', 'false'); p.textContent = 'Play'; } } }
function stDraw(c, which){
  const key = c.id + '/' + which, box = document.querySelector(`[data-dia="${key}"]`); if (!box) return;
  const sp = stSpec(c, which); const n = stNSteps(sp); const i = Math.min(ST.step[key] || 0, n - 1);
  if (which === 'main'){
    const naive = (ST.mode[c.id] || 'trick') === 'naive', t = naive ? c.naive : c.trick;
    box.querySelector('[data-ttl]').textContent = (naive ? 'Naive: ' : 'Trick: ') + (t ? t.title : '');
    box.querySelector('[data-txt]').textContent = t ? t.text : '';
  }
  const svg = box.querySelector('[data-svg]'), wrap = svg.parentNode;
  const W = Math.max(300, Math.floor(wrap.clientWidth - 16 || 600));
  clear(svg);
  const cap = stDiagram(svg, sp, i, W);
  box.querySelector('[data-ctr]').textContent = `step ${i + 1} / ${n}`;
  box.querySelector('[data-cap]').textContent = cap || '';
  box.querySelector('[data-schem]').textContent = sp && (sp.kind === 'bars') ? 'Bars plot recorded values (reviewer table).' : (sp && sp.note ? sp.note : 'Schematic: positions illustrate the mechanism; measured cycles and slacks are in the reviewer table.');
}
function dgc(k){ return css(DGK[k] || '--k-wire'); }
function stDiagram(svg, sp, i, W){
  if (!sp) { sizeSvg(svg, W, 40); txt(svg, 8, 24, 'No diagram for this view.'); return ''; }
  const f = { flow: dgFlow, pipe: dgPipe, gantt: dgGantt, bars: dgBars, ring: dgRing, timeline: dgTimeline, fanout: dgFanout }[sp.kind];
  return f ? f(svg, sp, i, W) : '';
}
function dgBox(svg, x, y, w, h, label, k, hot, bad){
  const g = svgEl('g', {class: 'dg-node' + (hot ? ' hot' : '')}, svg);
  const col = dgc(k);
  svgEl('rect', {x, y, width: w, height: h, rx: 3, fill: mix(css('--surface'), col, hot ? .32 : .14), stroke: hot ? (bad ? css('--s-open') : css('--accent')) : col}, g);
  const fs = w < 110 ? 10.5 : 12; const ls = wrapLines(label, w - 10, fs); const lh = fs * 1.25; const y0 = y + h / 2 - (ls.length - 1) * lh / 2 + fs * .35;
  ls.forEach((l, j) => txt(g, x + w / 2, y0 + j * lh, l, {fs, anchor: 'middle', fill: css('--ink'), mono: false}));
  return g;
}
function dgFlow(svg, sp, i, W){
  const st = (sp.steps || [])[i] || {}; const hot = new Set(st.hot || []); const pk = new Set(st.pk || []);
  const cols = sp.cols, rows = sp.rows, colW = W / cols, bw = Math.max(70, colW - 18);
  const lines = n => wrapLines(n.label, bw - 10, bw < 110 ? 10.5 : 12).length;
  const bh = Math.max(42, Math.max(...sp.nodes.map(lines)) * 15 + 16), rowH = bh + 50, H = rows * rowH + 6;
  sizeSvg(svg, W, H);
  const pos = {}; sp.nodes.forEach(n => { pos[n.id] = {x: n.c * colW + (colW - bw) / 2, y: n.r * rowH + 22, w: bw, h: bh}; });
  const defs = svgEl('defs', {}, svg); const mk = svgEl('marker', {id: 'dgArr', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse'}, defs);
  svgEl('path', {d: 'M0,0 L10,5 L0,10 z', fill: css('--muted')}, mk);
  const mk2 = svgEl('marker', {id: 'dgArrBad', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse'}, defs);
  svgEl('path', {d: 'M0,0 L10,5 L0,10 z', fill: css('--s-open')}, mk2);
  const edge = (a, b) => { const A = pos[a], B = pos[b]; const ac = [A.x + A.w / 2, A.y + A.h / 2], bc = [B.x + B.w / 2, B.y + B.h / 2];
    const clip = (P, c, d) => { const dx = d[0] - c[0], dy = d[1] - c[1]; const tx = dx ? (P.w / 2) / Math.abs(dx) : 1e9, ty = dy ? (P.h / 2) / Math.abs(dy) : 1e9; const t = Math.min(tx, ty); return [c[0] + dx * t, c[1] + dy * t]; };
    const back = (B.x < A.x && Math.abs(B.y - A.y) < 1) || (B.x === A.x && B.y === A.y);
    if (back){ const s = [A.x + A.w / 2, A.y], e = [B.x + B.w / 2, B.y]; const cy = A.y - 20; return {d: `M${s[0]},${s[1]} C${s[0]},${cy} ${e[0]},${cy} ${e[0]},${e[1] - 1}`, mid: [(s[0] + e[0]) / 2, cy + 5]}; }
    const s = clip(A, ac, bc), e = clip(B, bc, ac); return {d: `M${s[0]},${s[1]} L${e[0]},${e[1]}`, mid: [(s[0] + e[0]) / 2, (s[1] + e[1]) / 2]}; };
  const paths = sp.edges.map((e, j) => { const g = edge(e.a, e.b); const on = pk.has(j); const bad = e.bad && (on || st.bad);
    svgEl('path', {d: g.d, class: 'dg-edge', stroke: bad ? css('--s-open') : (on ? css('--accent') : css('--muted')), 'stroke-width': on ? 2.6 : 1.4, 'stroke-dasharray': e.bad && !on ? '4 4' : '', 'marker-end': bad ? 'url(#dgArrBad)' : 'url(#dgArr)', opacity: on || !pk.size ? 1 : .55}, svg);
    g.el = svg.lastChild; g.lab = e.l; g.bad = bad;
    return g; });
  sp.nodes.forEach(n => { const p = pos[n.id]; dgBox(svg, p.x, p.y, p.w, p.h, n.label, n.k, hot.has(n.id), st.bad); });
  paths.forEach(g => { if (!g.lab) return; const tw = g.lab.length * 6.3; const x = Math.max(2, Math.min(W - tw - 2, g.mid[0] + 4));
    const bg = svgEl('rect', {x: x - 2, y: g.mid[1] - 15, width: tw + 4, height: 13, fill: css('--surface-2'), opacity: .85}, svg); txt(svg, x, g.mid[1] - 5, g.lab, {fs: 10.5, fill: g.bad ? css('--s-open') : css('--muted')}); });
  pk.forEach(j => { const g = paths[j]; if (!g || !g.el) return; const dot = svgEl('circle', {r: 5.5, fill: st.bad && sp.edges[j].bad ? css('--s-open') : css('--packet'), class: 'dg-pk', cx: g.mid[0], cy: g.mid[1]}, svg);
    let L = 0; try { L = g.el.getTotalLength(); } catch (e) {} if (!L) return;
    const put = f => { const q = g.el.getPointAtLength(L * f); dot.setAttribute('cx', q.x); dot.setAttribute('cy', q.y); };
    if (reduceMotion){ put(.6); return; }
    const t0 = performance.now(); put(0); const step = now => { if (!dot.isConnected) return; const f = Math.min(1, (now - t0) / 900); put(f); if (f < 1) requestAnimationFrame(step); }; requestAnimationFrame(step); });
  return st.note || '';
}
function dgAxis(svg, x0, x1, y, span, unit, ticks){
  svgEl('line', {x1: x0, x2: x1, y1: y, y2: y, stroke: css('--line')}, svg);
  niceTicks(0, span, ticks || 5).forEach(v => { const x = x0 + (x1 - x0) * v / span; svgEl('line', {x1: x, x2: x, y1: y, y2: y + 4, stroke: css('--muted')}, svg); txt(svg, x, y + 15, fmt(v, span < 5 ? 1 : 0), {fs: 10, anchor: 'middle'}); });
  txt(svg, x1, y + 28, unit, {fs: 10, anchor: 'end'});
}
function dgGantt(svg, sp, i, W){
  const st = (sp.steps || [])[i] || {t: sp.span}; const t = st.t == null ? sp.span : st.t;
  const lab = W < 480 ? 74 : 110, x0 = lab, x1 = W - 10, rh = 30, H = sp.rows.length * rh + 46; sizeSvg(svg, W, H);
  const X = v => x0 + (x1 - x0) * v / sp.span;
  sp.rows.forEach((r, j) => txtWrap(svg, 4, 12 + j * rh + 8, r, lab - 8, {fs: 11, fill: css('--ink'), mono: false}));
  sp.bars.forEach(b => { const on = b.start < t; const x = X(b.start), w = Math.max(1.2, X(b.start + b.len) - x); const y = 6 + b.row * rh;
    svgEl('rect', {x, y, width: w, height: rh - 8, fill: dgc(b.k), opacity: on ? .9 : .18, stroke: css('--surface'), 'stroke-width': .6}, svg);
    if (b.label && w > b.label.length * 6.2 + 6) txt(svg, x + 4, y + (rh - 8) / 2 + 4, b.label, {fs: 10.5, fill: on ? css('--bg') : css('--muted')}); });
  const xc = X(Math.min(t, sp.span)); svgEl('line', {x1: xc, x2: xc, y1: 2, y2: sp.rows.length * rh + 2, stroke: css('--accent'), 'stroke-width': 2}, svg);
  dgAxis(svg, x0, x1, sp.rows.length * rh + 6, sp.span, sp.unit || '');
  return st.note || '';
}
function dgBars(svg, sp, i, W){
  const st = (sp.steps || [])[i] || {show: sp.bars.length}; const show = st.show == null ? sp.bars.length : st.show;
  const lab = W < 480 ? 120 : 190, x0 = lab, x1 = W - 70, bh = 24, gap = 10, H = sp.bars.length * (bh + gap) + 40; sizeSvg(svg, W, H);
  const mx = sp.max || Math.max(...sp.bars.map(b => b.v), sp.limit ? sp.limit.v : 0) * 1.05; const X = v => x0 + (x1 - x0) * v / mx;
  sp.bars.forEach((b, j) => { const y = 6 + j * (bh + gap), on = j < show;
    txtWrap(svg, 4, y + 10, b.label, lab - 10, {fs: 11, fill: css('--ink'), mono: false, lh: 12});
    svgEl('rect', {x: x0, y, width: Math.max(1.5, X(b.v) - x0), height: bh, fill: dgc(b.k), opacity: on ? .9 : .18}, svg);
    if (on) txt(svg, X(b.v) + 5, y + bh / 2 + 4, fmt(b.v, b.v < 10 && b.v % 1 ? 3 : (b.v % 1 ? 1 : 0)), {fs: 11, fill: css('--ink')}); });
  if (sp.limit){ const x = X(sp.limit.v); svgEl('line', {x1: x, x2: x, y1: 0, y2: sp.bars.length * (bh + gap), stroke: css('--accent'), 'stroke-width': 2, 'stroke-dasharray': '5 3'}, svg); txt(svg, Math.min(x, x1) - 2, sp.bars.length * (bh + gap) + 12, sp.limit.label + ' ' + fmt(sp.limit.v, 2), {fs: 10.5, anchor: 'end', fill: css('--accent')}); }
  dgAxis(svg, x0, x1, sp.bars.length * (bh + gap) + (sp.limit ? 16 : 2), mx, sp.unit || '', 4);
  return (st.note || '') + (sp.marker && i === (sp.steps || []).length - 1 ? ' ' + sp.marker.label + '.' : '');
}
function dgPipe(svg, sp, i, W){
  const lab = 60, cw = Math.max(26, Math.min(48, (W - lab - 8) / sp.cycles)), rh = 26; const Wd = Math.max(W, lab + cw * sp.cycles + 8), H = sp.stages * rh + 40; sizeSvg(svg, Wd, H);
  for (let s = 0; s < sp.stages; s++) txt(svg, 4, 16 + s * rh + 4, 'stage ' + (s + 1), {fs: 10.5});
  for (let cyc = 0; cyc < sp.cycles; cyc++){ const x = lab + cyc * cw; if (cyc === i) svgEl('rect', {x, y: 2, width: cw, height: sp.stages * rh, fill: mix(css('--surface-2'), css('--accent'), .18)}, svg); txt(svg, x + cw / 2, sp.stages * rh + 16, String(cyc), {fs: 10, anchor: 'middle'}); }
  let busy = 0;
  sp.lanes.forEach((ln, li) => { for (let k = 0; ; k++){ const st = ln.start + k * (ln.every || 1e9); if (st > i || st >= sp.cycles) break;
    for (let s = 0; s < sp.stages; s++){ const cyc = st + s; if (cyc > i || cyc >= sp.cycles) break; const x = lab + cyc * cw, y = 2 + s * rh;
      svgEl('rect', {x: x + 1, y: y + 1, width: cw - 2, height: rh - 2, rx: 2, fill: css(['--k-field', '--k-attn', '--k-hc', '--k-ctrl', '--k-su', '--k-hbm'][li % 6]), opacity: cyc === i ? .95 : .55}, svg);
      if (cw >= 30) txt(svg, x + cw / 2, y + rh / 2 + 4, ln.label.replace('slot ', 's'), {fs: 10, anchor: 'middle', fill: css('--bg')}); if (cyc === i) busy++; } } });
  txt(svg, Wd - 4, H - 6, 'cycle', {fs: 10, anchor: 'end'});
  return `Cycle ${i}: ${busy} of ${sp.stages} adder stages busy.`;
}
function dgRing(svg, sp, i, W){
  const N = sp.slots, cw = Math.min(70, (W - 20) / N), H = 118; sizeSvg(svg, W, H); const x0 = (W - cw * N) / 2;
  const rd = i - sp.offset;
  for (let s = 0; s < N; s++){ const x = x0 + s * cw; const age = (i - s) >= 0 ? ((i - s) % N) : null; const written = s <= i || i >= N;
    const isW = s === i % N, isR = rd >= 0 && s === rd % N, isG = rd >= 0 && s === (rd + sp.guard) % N;
    svgEl('rect', {x: x + 2, y: 34, width: cw - 4, height: 34, rx: 2, fill: written ? mix(css('--surface'), css('--k-field'), .2 + .5 * (1 - ((i - s + N * 4) % N) / N)) : css('--surface'), stroke: isR ? css('--s-closed') : isG ? css('--s-enc') : css('--line'), 'stroke-width': isR || isG ? 2.4 : 1}, svg);
    txt(svg, x + cw / 2, 56, 'slot ' + s, {fs: 10, anchor: 'middle', fill: css('--ink')});
    if (isW) txt(svg, x + cw / 2, 26, 'write', {fs: 10.5, anchor: 'middle', fill: css('--k-field'), weight: 600});
    if (isR) txt(svg, x + cw / 2, 84, 'read', {fs: 10.5, anchor: 'middle', fill: css('--s-closed'), weight: 600});
    if (isG) txt(svg, x + cw / 2, 98, 'guard', {fs: 10.5, anchor: 'middle', fill: css('--s-enc'), weight: 600}); }
  txt(svg, W / 2, 14, `cycle ${i}`, {fs: 11, anchor: 'middle'});
  return rd < 0 ? `Cycle ${i}: the writer fills slot ${i % N}; the reader was placed ${sp.offset} periods behind and has not started.` : `Cycle ${i}: write slot ${i % N}, read slot ${rd % N} (written ${sp.offset} cycles ago), guard on slot ${(rd + sp.guard) % N}.`;
}
function dgTimeline(svg, sp, i, W){
  const st = (sp.steps || [])[i] || {t: sp.span}; const lab = W < 480 ? 96 : 140, x0 = lab, x1 = W - 10, rh = 28, H = sp.lanes.length * rh + 50; sizeSvg(svg, W, H);
  const X = v => x0 + (x1 - x0) * v / sp.span;
  sp.lanes.forEach((ln, j) => { const y = 6 + j * rh; txtWrap(svg, 4, y + 12, ln.label, lab - 8, {fs: 11, fill: css('--ink'), mono: false});
    svgEl('rect', {x: X(Math.max(0, ln.start)), y, width: Math.max(2, X(ln.start + ln.len) - X(Math.max(0, ln.start))), height: rh - 8, fill: dgc(ln.k), opacity: ln.start < st.t ? .9 : .2}, svg); });
  const xp = X(sp.period); svgEl('line', {x1: xp, x2: xp, y1: 0, y2: sp.lanes.length * rh + 6, stroke: css('--s-open'), 'stroke-width': 2, 'stroke-dasharray': '5 3'}, svg);
  txt(svg, xp - 3, sp.lanes.length * rh + 2, 'next edge ' + sp.period + ' ps', {fs: 10, anchor: 'end', fill: css('--s-open')});
  dgAxis(svg, x0, x1, sp.lanes.length * rh + 12, sp.span, 'ps (schematic)', 4);
  return st.note || '';
}
function dgFanout(svg, sp, i, W){
  const H = 190; sizeSvg(svg, W, H); const n = sp.loads, cps = sp.copies; const lx = Math.min(W - 30, W * .8), dx = Math.max(60, W * .18);
  const ly = j => 14 + j * ((H - 28) / (n - 1));
  for (let c = 0; c < cps; c++){ const cy = cps === 1 ? H / 2 : 30 + c * ((H - 60) / (cps - 1));
    for (let j = c * n / cps; j < (c + 1) * n / cps; j++) svgEl('line', {x1: dx + 40, y1: cy, x2: lx, y2: ly(j), stroke: cps === 1 ? css('--s-open') : css('--s-closed'), 'stroke-width': .9, opacity: .7}, svg);
    svgEl('rect', {x: dx, y: cy - 12, width: 40, height: 24, rx: 2, fill: mix(css('--surface'), cps === 1 ? css('--s-open') : css('--s-closed'), .25), stroke: cps === 1 ? css('--s-open') : css('--s-closed')}, svg);
    txt(svg, dx + 20, cy + 4, cps === 1 ? 'reg' : 'kreg', {fs: 10, anchor: 'middle', fill: css('--ink')}); }
  for (let j = 0; j < n; j++) svgEl('circle', {cx: lx + 6, cy: ly(j), r: 3, fill: css('--k-field')}, svg);
  txt(svg, lx + 14, H / 2 + 4, n + ' loads', {fs: 10.5});
  return sp.note || '';
}
function stRedraw(){ stCards().filter(c => ST.open.has(c.id)).forEach(c => { stDraw(c, 'main'); if (c.diagram && c.diagram.extra) stDraw(c, 'extra'); }); }

const DATA = { stories: { legend: {}, loop_src: '' } };
function render(container, c, legend, loopSrc){
  DATA.stories.legend = legend || {}; DATA.stories.loop_src = loopSrc || '';
  ['main', 'extra'].forEach(w => stStop(c.id + '/' + w));
  ST.open = new Set([c.id]);
  const planned = c.status === 'planned' || !c.problem;
  container.innerHTML = `<article class="st-card" id="story-${esc(c.id)}" data-open="true">
    <div class="top"><div class="el">${esc(ST_TARGET[c.target] || c.target || '')} · ${esc(c.element || '')}</div>${sbadge(c.status || 'planned')}</div>
    <h4>${esc(c.title || c.id)}</h4><p class="sum">${esc(c.summary || '')}</p>
    ${planned ? '<p class="muted">This story is planned; its card is not written yet.</p>' : stBodyHtml(Object.assign({facts: [], tried: [], records: [], blocks: []}, c))}</article>`;
  if (!planned) stBind(c);
}
window.OTStory = { render, sbadge };
})();

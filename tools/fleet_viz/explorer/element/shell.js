/* Element page shell (/explorer/element/<name>): header, breadcrumb, tab availability and the two views that do not need
   the routed database (How it works, and the registry facts of an element whose routed data is not archived).
   Data: /api/explorer/elem_shell?e=<name> (tools/fleet_viz/elem_shell.py).  elem.js calls:
     ElemShell.load(name)          -> shell record (or null); also fills the header and breadcrumb
     ElemShell.tab(id, S)          -> {ok, why}: whether a tab has data, with a one-line reason when it does not
     ElemShell.render(S)           -> true when the shell drew the current tab itself (elem.js then skips its stage) */
(function(){
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const fmt = (n, d = 1) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
const sgn = (n, d = 1) => n == null || isNaN(n) ? '—' : (n >= 0 ? '+' : '−') + fmt(Math.abs(n), d);
const SAFE = new URLSearchParams(location.search).get('safe') === '1';
const QS = SAFE ? '&safe=1' : '';
let SH = null;
function when(t){ if (!t) return ''; return new Date(t * 1000).toLocaleString('en-US', {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false}); }
function ago(t){ if (!t) return ''; const s = Date.now() / 1000 - t; return s < 5400 ? Math.max(1, Math.round(s / 60)) + ' min ago' : s < 172800 ? (s / 3600).toFixed(1) + ' h ago' : Math.round(s / 86400) + ' d ago'; }

/* ------------------------------------------------------------------ header + breadcrumb */
function statusOf(s){
  const c = String(s.category || '');
  if (!s.registry && !s.data) return ['super', 'Not tracked'];
  if (s.revoked) return ['revoked', 'Revoked'];
  if (/^closed/.test(c)) return ['closed', 'Closed'];
  if (s.superseded || c === 'superseded') return ['super', 'Superseded'];
  if (c === 'exported') return ['closed', 'Exported'];
  return ['open', 'Open'];
}
function tputChip(t){
  if (!t || !t.status) return '<span class="eh-chip eh-mute" title="no throughput budget entry for this element">Throughput —</span>';
  const ok = /^QUALIFIED|ACCEPTED|EXEMPT/.test(t.status);
  const lab = t.status.replace(/_/g, ' ').toLowerCase();
  return `<span class="eh-chip ${ok ? 'eh-ok' : 'eh-warn'}" title="throughput qualification against the budget (measured / budget ≤ 1.10)">Throughput ${esc(lab)}${t.ratio != null ? ' · ' + fmt(t.ratio, 2) + '×' : ''}</span>`;
}
function metric(lab, v, unit, ok, title){
  return `<span class="eh-m" title="${esc(title || '')}"><small>${lab}</small><b class="${v == null ? '' : ok ? 'eh-okt' : 'eh-ngt'}">${v == null ? '—' : esc(v)}${v != null && unit ? `<i>${unit}</i>` : ''}</b></span>`;
}
function header(s){
  const [cls, lab] = statusOf(s), b = s.best || {};
  const tt = b.corner === 'SS' ? null : b.tt, ff = b.ff;
  const exq = '/explorer' + (SAFE ? '?safe=1' : '') + '#' + (s.crumbs[0] ? 'die=' + encodeURIComponent(s.crumbs[0].die) + '&' : '') + 'element=' + encodeURIComponent(s.registry || s.element);
  $('crumbs').innerHTML = `<a href="/explorer${SAFE ? '?safe=1' : ''}">Chip Explorer</a>` +
    (s.crumbs[0] ? `<span aria-hidden="true">›</span><a href="/explorer${SAFE ? '?safe=1' : ''}#die=${encodeURIComponent(s.crumbs[0].die)}">${esc(s.crumbs[0].label)}</a>` +
      (s.crumbs[0].region ? `<span aria-hidden="true">›</span><a href="${esc(exq)}" title="show it on the die map">${esc(s.crumbs[0].region)}</a>` : '')
     : s.target ? `<span aria-hidden="true">›</span><span>${esc(s.target)}</span>` : '') +
    `<span aria-hidden="true">›</span><span aria-current="page" class="eh-cur">${esc(s.element)}</span>`;
  $('title').textContent = s.element;
  document.title = (s.element || 'Element').slice(0, 40);
  const sub = [s.decoded, s.registry && s.registry !== s.element ? 'counted as ' + s.registry : null, s.data && s.data !== s.element && s.data !== s.registry ? 'routed data from ' + s.data : null].filter(Boolean);
  $('ehsub').innerHTML = sub.map(esc).join(' · ');
  const D = s.desc || {};
  $('ehdesc').innerHTML = (D.summary ? `<p class="${D.src === 'manual' ? 'eh-sum' : 'eh-about'}">${esc(D.summary)}</p>` : '') + (D.about && D.src === 'manual' && D.about !== D.summary ? `<p class="eh-about">${esc(D.about)}</p>` : '');
  $('ehdesc').hidden = !(D.summary || D.about);
  $('ehchips').innerHTML = [
    `<span class="eh-st eh-${cls}">${lab}</span>`,
    D.family ? `<span class="eh-chip eh-fam" title="element family">${esc(D.family)}</span>` : '',
    s.target ? `<span class="eh-chip" title="target die">${esc(s.target)}</span>` : '',
    metric('TT setup', tt == null ? null : sgn(tt, 1), ' ps', tt >= 0, 'worst setup slack at TT, sign-off at 833.333 ps'),
    metric('FF hold', ff == null ? null : sgn(ff, 1), ' ps', ff >= 0, 'worst hold slack at FF'),
    metric('DRC', b.drc == null ? null : String(b.drc), '', b.drc === 0, 'routed DRC violations'),
    tputChip(s.throughput),
    s.owner ? `<span class="eh-chip" title="owner">${esc(s.owner.replace(/^Claude:/, ''))}</span>` : '',
    s.closed_t ? `<span class="eh-chip" title="${esc(when(s.closed_t))}">closed ${esc(ago(s.closed_t))}</span>` : '',
    s.live ? `<span class="eh-chip eh-acc">${s.live} live job${s.live > 1 ? 's' : ''}</span>` : '',
    `<a class="eh-chip eh-link" href="${esc(exq)}">Show on die map</a>`].join('');
  $('ehead').hidden = false;
}

/* ------------------------------------------------------------------ tab availability */
const ROUTED = new Set(['geo', 'layout', 'timing', 'arrival', 'tree', 'density', 'replay']);
function tab(id, S){
  const els = (S && S.els) || [];
  const ok = els.filter(E => E.d && !E.err);
  if (id === 'how') return SH && (SH.stories.some(x => x.status !== 'planned') || SH.prose || (SH.desc && SH.desc.src === 'manual' && SH.desc.about)) ? {ok: true} : {ok: false, why: 'no How-it-works story written for this element yet'};
  if (id === 'facts') return {ok: true};
  if (!els.length) return {ok: true};   // still loading: do not grey anything out yet
  if (!ok.length) return {ok: false, why: SH && SH.missing ? SH.missing : 'no routed data for this element'};
  if (ROUTED.has(id)){
    const lay = ok.filter(E => !E.nolayout);
    if (!lay.length) return {ok: false, why: 'routed DB released before the export ran: no placement archived'};
    if (id === 'timing' && lay.every(E => !((E.d.setup_paths || []).length || (E.d.hold_paths || []).length)))
      return {ok: false, why: 'timing not re-run: the closing job’s sign-off sources were released'};
    if ((id === 'arrival' || id === 'tree') && lay.every(E => !E.d.clock_tt || !(E.d.clock_tt.leaves || []).length))
      return {ok: false, why: 'no clock tree in the exported data'};
    return {ok: true};
  }
  if (id === 'rtl') return ok.some(E => E.d.rtl_file) ? {ok: true} : {ok: false, why: 'no RTL export at the closure’s source commit'};
  return {ok: true};
}

/* ------------------------------------------------------------------ views drawn by the shell */
function render(S){
  const v = $('shellview');
  const noData = S.els.length && S.els.every(E => !E.d || E.err);
  const mine = S.tab === 'how' || (S.tab === 'facts' && noData && SH);
  v.hidden = !mine;
  if ($('pills')) $('pills').hidden = !!noData;
  document.querySelector('.main').hidden = !!mine;
  if (!mine) return false;
  if (S.tab === 'how') v.innerHTML = howHtml(S);
  else v.innerHTML = registryFactsHtml();
  v.querySelectorAll('[data-story]').forEach(b => b.onclick = () => openStory(b.dataset.story, b));
  return true;
}
function howHtml(S){
  const P = (S.pages && S.pages.elements) || {};
  const pr = P[SH.data] || P[SH.element] || null;
  const H = [];
  if (pr && pr.function) H.push(`<section class="sv-sec"><h2>What it does</h2><p>${esc(pr.function)}</p>${pr.summary ? `<p>${esc(typeof pr.summary === 'string' ? pr.summary : '')}</p>` : ''}</section>`);
  const D = SH.desc || {};
  if (D.src === 'manual' && (D.about || D.summary)) H.push(`<section class="sv-sec"><h2>About${D.family ? ' \u00b7 ' + esc(D.family) : ''}</h2>${D.summary ? `<p><b>${esc(D.summary)}</b></p>` : ''}${D.about ? `<p>${esc(D.about)}</p>` : ''}</section>`);
  else if (SH.purpose && !pr) H.push(`<section class="sv-sec"><h2>Purpose</h2><p>${esc(SH.purpose)}</p></section>`);
  if (SH.stories.length) H.push(`<section class="sv-sec"><h2>Stories</h2><div class="sv-stories">${SH.stories.map(s =>
    `<div class="sv-story"><button type="button" class="sv-open" data-story="${esc(s.id)}" aria-expanded="false"><b>${esc(s.title || s.id)}</b>${s.status === 'planned' ? ' <small>(planned)</small>' : ''}<span>${esc(s.summary || '')}</span></button><div class="sv-body" hidden></div></div>`).join('')}</div></section>`);
  if (!H.length) H.push(`<section class="sv-sec"><p class="sv-why">No How-it-works story written for this element yet.</p></section>`);
  return H.join('');
}
let storyLib = null;
function loadStoryLib(){
  if (window.OTStory) return Promise.resolve();
  if (!storyLib) storyLib = new Promise((res, rej) => { const s = document.createElement('script'); s.src = '/explorer_story.js'; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
  return storyLib;
}
async function openStory(id, btn){
  const body = btn.nextElementSibling, open = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', String(!open)); body.hidden = open;
  if (open || body.dataset.done) return;
  body.innerHTML = '<p class="sv-why">Loading the story…</p>';
  try {
    const [c] = await Promise.all([fetch('/api/explorer/story?id=' + encodeURIComponent(id) + QS, {cache: 'no-store'}).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }), loadStoryLib()]);
    let sm = {};
    try { sm = (await fetch('/api/explorer/meta?' + (SAFE ? 'safe=1' : ''), {cache: 'no-store'}).then(r => r.json())).story_meta || {}; } catch (e) {}
    body.innerHTML = ''; window.OTStory.render(body, c, sm.legend, sm.loop_src); body.dataset.done = '1';
  } catch (e){ body.innerHTML = `<p class="sv-why">Story failed to load: ${esc(e.message || e)}</p>`; }
}
function registryFactsHtml(){
  const b = SH.best || {};
  const row = (k, v) => v == null || v === '' ? '' : `<dt>${esc(k)}</dt><dd>${v}</dd>`;
  return `<section class="sv-sec"><h2>No routed data for this element</h2><p class="sv-why">${esc(SH.missing || '')}</p>
    <p>The header numbers come from the closure registry. Layout, placement, timing, clock and density views appear here once the routed database is exported (tools/explorer_elem_export.py) or archived.</p></section>
    <section class="sv-sec"><h2>Registry facts</h2><dl class="sv-kv">
      ${row('status', esc(SH.category))}${row('target', esc(SH.target))}
      ${row('TT setup', b.tt == null ? null : sgn(b.tt, 2) + ' ps')}${row('FF hold', b.ff == null ? null : sgn(b.ff, 2) + ' ps')}${row('SS sensitivity', b.ss == null ? null : sgn(b.ss, 1) + ' ps')}
      ${row('DRC', b.drc == null ? null : String(b.drc))}
      ${row('throughput', SH.throughput && SH.throughput.status ? esc(SH.throughput.status) + (SH.throughput.ratio != null ? ' (' + fmt(SH.throughput.ratio, 3) + '× budget)' : '') : null)}
      ${row('closing job', b.job ? esc(b.job) : null)}${row('source commit', b.commit ? esc(b.commit) : null)}
      ${row('closed', SH.closed_t ? esc(when(SH.closed_t)) + ' (' + esc(ago(SH.closed_t)) + ')' : null)}${row('owner', SH.owner ? esc(SH.owner) : null)}
      ${row('purpose', SH.purpose ? esc(SH.purpose) : null)}
    </dl></section>`;
}

async function load(name){
  if (!name) return null;
  try {
    const r = await fetch('/api/explorer/elem_shell?e=' + encodeURIComponent(name) + QS, {cache: 'no-store'});
    if (!r.ok) throw new Error(r.status);
    SH = await r.json();
  } catch (e){ SH = null; return null; }
  header(SH);
  return SH;
}
window.ElemShell = {load, tab, render, get: () => SH};
})();

/* Design Explorer (EXPLORER-2, 2026-11-11): die -> type -> core.
   Data: /api/design/* (design_service.py over design_index.json, one node index for every explorer page).
   Die page: the plan of record drawn to scale, type slots coloured by sign-off status, seams (port windows between
   abutting partitions), clock root, PG domains, hard cores inside each slot.  Click a slot -> the type.
   Type / core page: Plan view (outline, hard cores coloured by their own status, face windows, ft slots, stations, clock
   taps) and the Routed layout view: the lossless layout viewer (explorer/element/layout.js) on the node's store pack.
   A hard-core macro clicked in a type's routed layout opens that core.  URL: #n=<node id>&v=plan|layout */
(function(){
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = (n, d = 0) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
const STC = {signed: '--s-signed', failed: '--s-failed', building: '--s-building', queued: '--s-queued', waiting: '--s-waiting', 'not built': '--s-notbuilt'};
const STL = {signed: 'signed off', failed: 'failed', building: 'building', queued: 'queued', waiting: 'waiting', 'not built': 'not built'};
const stcls = s => 'st-' + String(s || 'not built').replace(' ', '');
const badge = st => `<span class="st ${stcls(st.state)}"><i></i>${esc(STL[st.state] || st.state)}</span>`;
const ORS = new Set(['R90', 'R270', 'MXR90', 'MYR90']);
const S = {hash: {}, idx: null, die: null, dieId: null, node: null, view: 'plan', hide: new Set(), hover: null, cam: null, filter: ''};
try { const t = localStorage.getItem('otx.design.theme'); if (t) document.documentElement.dataset.theme = t; } catch (e) {}

function parseHash(){ const o = {}; location.hash.replace(/^#/, '').split('&').forEach(kv => { const [k, v] = kv.split('='); if (k) o[k] = decodeURIComponent(v || ''); }); return o; }
function setHash(o, push){ const h = '#' + Object.entries(o).filter(([, v]) => v != null && v !== '').map(([k, v]) => k + '=' + encodeURIComponent(v)).join('&');
  if (push) location.hash = h; else history.replaceState(null, '', location.pathname + location.search + h); }
const nodeHref = (id, v) => '#n=' + encodeURIComponent(id) + (v ? '&v=' + v : '');
async function J(u){ const r = await fetch(u); if (!r.ok) throw new Error(r.status + ' ' + u); return r.json(); }

/* ------------------------------------------------------------------ routing */
async function route(){
  S.hash = parseHash();
  if (!S.idx) S.idx = await J('/api/design/index');
  if (S.hash.q){   // a name from another page (token step element, coverage cell, old element id) -> its node(s)
    const r = (await J('/api/design/resolve?q=' + encodeURIComponent(S.hash.q)))[S.hash.q] || [];
    const pref = S.hash.die ? r.filter(x => x.split('.')[0] === S.hash.die) : r, hits = pref.length ? pref : r;
    if (hits.length === 1){ setHash({n: hits[0]}); return route(); }
    S.resolve = {q: S.hash.q, hits};
  } else S.resolve = null;
  let id = S.hash.n || (S.idx.dies[0] && S.idx.dies[0].id);
  const die = id.split('.')[0];
  if (S.dieId !== die){ S.die = await J('/api/design/die/' + encodeURIComponent(die)); S.dieId = die; S.cam = null; }
  if (id === die){ S.node = null; S.view = 'plan'; }
  else {
    const r = await J('/api/design/node/' + encodeURIComponent(id));
    if (!S.node || S.node.node.id !== id) S.cam = null;
    S.node = r;
    const has = !!((r.node.layout || {}).store);
    S.view = S.hash.v === 'plan' ? 'plan' : S.hash.v === 'layout' ? 'layout' : (has ? 'layout' : 'plan');
  }
  render();
}
window.addEventListener('hashchange', () => route().catch(err));
function err(e){ console.error(e); $('facts').innerHTML = `<div class="sec"><div class="warnbox">${esc(String(e))}</div></div>`; }

/* ------------------------------------------------------------------ chrome */
function render(){
  const d = S.die.die, n = S.node && S.node.node;
  document.title = n ? n.name + ' · ' + d.id : d.label;
  const cr = [`<a href="${nodeHref(d.id)}">${esc(d.id.toUpperCase())}</a>`];
  if (n){
    if (n.level === 'core'){
      const from = S.hash.from && S.die.nodes[S.hash.from];
      if (from) cr.push('<i>&rsaquo;</i>', `<a href="${nodeHref(from.id)}">${esc(from.name)}</a>`);
      else cr.push('<i>&rsaquo;</i>', `<span class="lv-dim" style="font:600 11px var(--mono)">core of ${n.plan.used_by.length} type${n.plan.used_by.length === 1 ? '' : 's'}</span>`);
    }
    cr.push('<i>&rsaquo;</i>', `<b>${esc(n.name)}</b>`);
  }
  $('crumbs').innerHTML = cr.join('');
  $('dflink').href = '/explorer/dataflow/#design=' + ({s81: 'ds_rom', s81_head: 'ds_rom', qwen_compute: 'qwen_rom', qwen_kvsys: 'qwen_rom', hbm: 'hbm_gen_ds'}[d.id] || 'ds_rom') + '&die=plan_' + d.id;
  const has = n && (n.layout || {}).store;
  $('views').innerHTML = n ? `<button type="button" data-v="plan" aria-pressed="${S.view === 'plan'}">Plan</button><button type="button" data-v="layout" aria-pressed="${S.view === 'layout'}" ${has ? '' : 'disabled title="no routed layout exported for this design yet"'}>Routed layout</button>` : '';
  $('views').querySelectorAll('button').forEach(b => b.onclick = () => { setHash(Object.assign(parseHash(), {v: b.dataset.v}), true); });
  renderNav(); renderFacts();
  const lay = n && S.view === 'layout' && has;
  $('plan').hidden = !!lay; $('geo').hidden = !lay; $('geoside').hidden = !lay; $('geonav').hidden = !lay; $('hint').hidden = !!lay;
  if (lay) openLayout(n);
  else { if (window.LayoutViewer) LayoutViewer.close(); drawSoon(); }
}

function counts(c){ return S.idx.states.map(s => `<label><span class="sw" style="background:var(${STC[s]})"></span>${esc(STL[s])}<small>${c ? c[s] || 0 : 0}</small></label>`).join(''); }

function renderNav(){
  const d = S.die.die, n = S.node && S.node.node;
  const dies = S.idx.dies.map(x => `<a href="${nodeHref(x.id)}" class="${x.id === d.id ? 'on' : ''}"><span class="sw" style="background:var(--accent)"></span>${esc(x.label)}<small>${x.counts.type.signed}/${x.types} types</small></a>`).join('');
  let h = `<div class="sec"><h3>Dies</h3><div class="list">${dies}</div></div>`;
  if (!n){
    h += `<div class="sec"><h3>Types by status (click to hide)</h3><div class="legend" id="leg">${S.idx.states.map(s => `<label><input type="checkbox" data-s="${esc(s)}" ${S.hide.has(s) ? '' : 'checked'}><span class="sw" style="background:var(${STC[s]})"></span>${esc(STL[s])}<small>${d.counts.type[s] || 0}</small></label>`).join('')}</div>
      <p class="note">Cores: ${S.idx.states.filter(s => d.counts.core[s]).map(s => `${d.counts.core[s]} ${STL[s]}`).join(', ')}</p></div>
      <div class="sec"><h3>Overlays</h3>
        <label class="chk"><input type="checkbox" data-o="seams" ${S.ov.seams ? 'checked' : ''}> seams (port windows between partitions)</label>
        <label class="chk"><input type="checkbox" data-o="cores" ${S.ov.cores ? 'checked' : ''}> hard cores inside slots</label>
        <label class="chk"><input type="checkbox" data-o="clock" ${S.ov.clock ? 'checked' : ''}> clock root / spine</label>
        <label class="chk"><input type="checkbox" data-o="pg" ${S.ov.pg ? 'checked' : ''}> PG domains</label>
        <label class="chk"><input type="checkbox" data-o="landing" ${S.ov.landing ? 'checked' : ''}> landing cohort of the hovered type</label>
        <label class="chk"><input type="checkbox" data-o="names" ${S.ov.names ? 'checked' : ''}> partition names</label></div>`;
  }
  const types = Object.values(S.die.nodes).filter(x => x.level === 'type');
  const q = S.filter.toLowerCase();
  const rows = types.filter(t => !q || t.name.toLowerCase().includes(q)).sort((a, b) => S.idx.states.indexOf(a.status.state) - S.idx.states.indexOf(b.status.state) || a.name.localeCompare(b.name))
    .map(t => `<a href="${nodeHref(t.id)}" class="${n && n.id === t.id ? 'on' : ''}" title="${esc(t.status.label)}"><span class="sw" style="background:var(${STC[t.status.state]})"></span>${esc(t.name)}<small>${(t.layout || {}).store ? 'layout ' : ''}${t.plan.instances}&times;</small></a>`).join('');
  h += `<div class="sec"><h3>Types of ${esc(d.id)} (${types.length})</h3><input type="search" id="tq" placeholder="filter types…" value="${esc(S.filter)}" aria-label="Filter types"><div class="list" style="margin-top:6px">${rows}</div></div>`;
  $('nav').innerHTML = h;
  const tq = $('tq'); tq.oninput = () => { S.filter = tq.value; const p = tq.selectionStart; renderNav(); const t2 = $('tq'); t2.focus(); t2.setSelectionRange(p, p); };
  $('nav').querySelectorAll('[data-s]').forEach(c => c.onchange = () => { c.checked ? S.hide.delete(c.dataset.s) : S.hide.add(c.dataset.s); drawSoon(); });
  $('nav').querySelectorAll('[data-o]').forEach(c => c.onchange = () => { S.ov[c.dataset.o] = c.checked; drawSoon(); });
}
S.ov = {seams: true, cores: true, clock: true, pg: true, landing: true, names: false};

function layoutFacts(l){
  if (!l) return '<p class="note">No routed DB yet (not built, or the newest attempt stopped before global route).</p>';
  const s = l.store;
  const db = l.db || l.kit || '—';
  return `<dl class="kv"><dt>source</dt><dd>${esc(l.source || '')}${l.legacy ? ' (legacy view)' : ''}</dd><dt>stage</dt><dd>${esc(l.stage || '?')}</dd><dt>DB</dt><dd>${esc(db)}</dd>
    ${l.record ? `<dt>signed record</dt><dd>${esc(l.record.slice(0, 16))}…</dd>` : ''}${l.archive_odb ? `<dt>archive</dt><dd>AGIdock ${esc(l.archive_odb)}</dd>` : ''}
    ${l.odb_bytes ? `<dt>DB size</dt><dd>${fmt(l.odb_bytes / 1e6, 0)} MB</dd>` : ''}
    <dt>exported</dt><dd>${s ? `${esc(s.verify || '?')} · ${fmt(s.shapes)} shapes · ${fmt(s.bytes / 1e6, 1)} MB · ${esc((s.made || '').slice(0, 16))}` : 'not yet (design_export.py backfill)'}</dd></dl>`;
}
function statusFacts(st){
  const m = st.metrics || {};
  const mm = [['TT setup WNS', m.tt_wns, ' ps'], ['FF hold WNS', m.ff_wns, ' ps'], ['DRC', m.drt_drc != null ? m.drt_drc : m.drc, ''], ['GRT overflow', m.grt_overflow, ''], ['LEC', m.lec, ''], ['cells', m.cells, '']]
    .filter(x => x[1] != null).map(x => `<dt>${x[0]}</dt><dd>${typeof x[1] === 'number' ? fmt(x[1], x[0].includes('WNS') ? 2 : 0) : esc(x[1])}${x[2]}</dd>`).join('');
  return `<div style="margin:6px 0">${badge(st)} <span class="lv-dim" style="font-size:12px">${esc(st.label)}${st.cls ? ' · class ' + esc(st.cls) : ''}${st.stage ? ' · stage ' + esc(st.stage) : ''}${st.attempt ? ' · attempt ' + esc(st.attempt) : ''}</span></div>
    ${st.reason ? `<p class="note">${esc(st.reason)}</p>` : ''}${mm ? `<dl class="kv" style="margin-top:6px">${mm}</dl>` : ''}`;
}

function renderFacts(){
  const d = S.die.die, n = S.node && S.node.node;
  let h;
  if (!n){
    const p = d.plan;
    h = `<div class="sec"><h1>${esc(d.label)}</h1><p class="sub">${esc(d.target || '')} · plan of record drawn to scale. Click a slot to open its type.</p></div>
      <div class="sec"><h3>Plan</h3><dl class="kv"><dt>file</dt><dd>${esc(p.path)}</dd><dt>commit</dt><dd>${esc((p.commit || '').slice(0, 10))} ${esc((p.date || '').slice(0, 10))}</dd>
        <dt>subject</dt><dd>${esc(p.subject || '')}</dd><dt>outline</dt><dd>${fmt(p.outline[0], 1)} × ${fmt(p.outline[1], 1)} µm</dd><dt>period</dt><dd>${esc(p.period_ps)} ps</dd>
        <dt>reach</dt><dd>${esc(p.reach_um)} µm/cycle</dd><dt>partitions</dt><dd>${p.partitions.length} (${d.children.length} types)</dd><dt>seams</dt><dd>${p.seams.length} abutting pairs with ports</dd>
        <dt>clock</dt><dd>${esc(p.clock.topology || '?')} on ${esc((p.clock.layers || []).join('/'))}, root ${p.clock.root ? fmt(p.clock.root[0], 0) + ', ' + fmt(p.clock.root[1], 0) : '?'}</dd>
        <dt>PG domains</dt><dd>${p.pg_domains.length}</dd></dl>${p.release_header ? `<p class="note">${esc(p.release_header)}</p>` : ''}</div>
      <div class="sec"><h3>Sign-off</h3><p class="note">Types: ${S.idx.states.filter(s => d.counts.type[s]).map(s => `<b>${d.counts.type[s]}</b> ${STL[s]}`).join(' · ')}<br>Cores: ${S.idx.states.filter(s => d.counts.core[s]).map(s => `<b>${d.counts.core[s]}</b> ${STL[s]}`).join(' · ')}</p>
        <p class="note">Die-level route has not run yet: this page shows the plan placement, not a routed die.</p></div>
      <div class="sec" id="hov"><h3>Hover</h3><p class="note">Point at a slot.</p></div>`;
  } else if (n.level === 'type'){
    const R = S.node, cores = Object.values(R.children);
    const cl = cores.sort((a, b) => a.name.localeCompare(b.name)).map(c => {
      const k = n.plan.hard_cores.filter(h => h[1] === c.id).length;
      return `<a href="${nodeHref(c.id)}&from=${encodeURIComponent(n.id)}"><span class="sw" style="background:var(${STC[c.status.state]})"></span>${esc(c.name)}<small>${k}&times; ${(c.layout || {}).store ? '· layout' : ''}</small></a>`; }).join('');
    const unk = n.plan.hard_cores.filter(h => !R.children[h[1]]).length;
    h = `<div class="sec"><h1>${esc(n.name)}</h1><p class="sub">type of ${esc(d.id)} · ${n.plan.instances} instance${n.plan.instances === 1 ? '' : 's'} in the die · ${fmt(n.plan.outline[0], 2)} × ${fmt(n.plan.outline[1], 2)} µm${n.plan.landing_base ? ' · landing cohort ' + esc(n.plan.landing_base) : ''}</p>${statusFacts(n.status)}</div>
      <div class="sec"><h3>Routed layout</h3>${layoutFacts(n.layout)}</div>
      <div class="sec"><h3>Hard cores (${n.plan.hard_cores.length} instances, ${cores.length} designs)</h3>${cores.length ? `<div class="list">${cl}</div>` : '<p class="note">None: this type is flat (standard cells and generated macros only).</p>'}
        ${unk ? `<p class="note">${unk} instance(s) are generated memory macros (SRAM/ROM), not signed designs.</p>` : ''}<div id="macrocard"></div></div>
      <div class="sec"><h3>Plan contents</h3><dl class="kv"><dt>face buses</dt><dd>${n.plan.buses.length}</dd><dt>ft slots</dt><dd>${n.plan.ft_slots.length} (${n.plan.ft_slots.reduce((a, s) => a + (s.stations || 1), 0)} stations)</dd>
        <dt>internal stations</dt><dd>${n.plan.stations.length}</dd><dt>clock taps</dt><dd>${n.plan.clock.taps.length}${n.plan.clock.layer ? ' (' + esc(n.plan.clock.layer) + ')' : ''}</dd>
        <dt>placements</dt><dd>${R.placements.slice(0, 6).map(p => esc(p[0]) + ' ' + esc(p[5])).join(', ')}${R.placements.length > 6 ? ' …' : ''}</dd></dl></div>
      ${n.vis ? `<div class="sec"><h3>Visual review (VIS-SWEEP)</h3><p class="note"><b>${esc(n.vis.verdict)}</b> ${esc(n.vis.cls)} · attempt ${esc(n.vis.attempt)} ${esc(n.vis.stage)}<br>${esc(n.vis.cause)}</p></div>` : ''}`;
  } else {
    const users = Object.values(S.node.users).map(u => `<a href="${nodeHref(u.id)}"><span class="sw" style="background:var(${STC[u.status.state]})"></span>${esc(u.name)}</a>`).join('');
    h = `<div class="sec"><h1>${esc(n.name)}</h1><p class="sub">hard core of ${esc(d.id)} · ${n.plan.outline ? fmt(n.plan.outline[0], 2) + ' × ' + fmt(n.plan.outline[1], 2) + ' µm' : ''} · placed ${n.plan.placements} time(s)</p>${statusFacts(n.status)}</div>
      <div class="sec"><h3>Routed layout</h3>${layoutFacts(n.layout)}</div>
      <div class="sec"><h3>Used by ${n.plan.used_by.length} type(s)</h3><div class="list">${users}</div></div>`;
  }
  if (S.resolve) h = `<div class="sec"><div class="warnbox">${S.resolve.hits.length ? `<b>${esc(S.resolve.q)}</b> is ${S.resolve.hits.length} designs:<br>` + S.resolve.hits.map(x => `<a href="${nodeHref(x)}">${esc(x)}</a>`).join('<br>')
    : `<b>${esc(S.resolve.q)}</b> is not a type or core of any current die plan (an October element, a retired design, or a generated macro).`}</div></div>` + h;
  $('facts').innerHTML = h;
}

/* ------------------------------------------------------------------ routed layout (lossless viewer) */
function openLayout(n){
  LayoutViewer.open({root: $('geo'), side: $('geoside'), nav: $('geonav'), el: n.id, d: null, E: null, safe: false,
    onFallback: () => setHash(Object.assign(parseHash(), {v: 'plan'}), true),
    onMacro: m => macroPick(n, m)});
}
function macroCore(n, m){
  // the macro instance of the routed type -> the plan's hard core (instance name first, then master ~ module)
  const hc = n.plan.hard_cores;
  let h = hc.find(x => x[0] === m.name) || hc.find(x => m.name.endsWith(x[0]) || x[0].endsWith(m.name));
  if (!h) h = hc.find(x => m.master === x[2]) || hc.find(x => m.master.includes(x[2]));
  return h;
}
function macroPick(n, m){
  const h = macroCore(n, m), box = $('macrocard'); if (!box) return;
  const c = h && S.node.children[h[1]];
  box.innerHTML = `<div class="macrocard"><b style="font-family:var(--mono)">${esc(m.name)}</b><br><span class="lv-dim">${esc(m.master)}</span><br>` +
    (c ? `${badge(c.status)} <a class="btn" href="${nodeHref(c.id)}&from=${encodeURIComponent(n.id)}">Open core ${esc(c.name)} &rsaquo;</a>` : 'generated memory macro (no signed design of its own)') + '</div>';
  box.scrollIntoView({block: 'nearest'});
}

/* ------------------------------------------------------------------ plan canvas */
let raf = 0; function drawSoon(){ if (!raf) raf = requestAnimationFrame(() => { raf = 0; draw(); }); }
const cv = $('plan'), ctx = cv.getContext('2d');
function world(){ // drawing extent (um)
  if (!S.node) return S.die.die.plan.outline;
  return S.node.node.plan.outline || [10, 10];
}
function fit(){
  const r = cv.getBoundingClientRect(), [W, H] = world();
  const k = Math.min(r.width / W, r.height / H) * 0.92;
  S.cam = {k, x: (r.width - W * k) / 2, y: (r.height + H * k) / 2};
}
const X = x => S.cam.x + x * S.cam.k, Y = y => S.cam.y - y * S.cam.k;
function rect(x, y, w, h){ ctx.rect(X(x), Y(y + h), w * S.cam.k, h * S.cam.k); }
function placeChild(ox, oy, o, W, H, x, y, w, h){
  if (o === 'MY') x = W - x - w; else if (o === 'MX') y = H - y - h; else if (o === 'R180'){ x = W - x - w; y = H - y - h; }
  return [ox + x, oy + y];
}
function draw(){
  const r = cv.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
  cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (!S.cam) fit();
  ctx.clearRect(0, 0, r.width, r.height);
  if (!S.node) drawDie(); else drawType();
}
function col(s){ return cssv(STC[s] || '--s-notbuilt'); }
function drawDie(){
  const d = S.die.die, p = d.plan, N = S.die.nodes;
  ctx.fillStyle = cssv('--panel2'); ctx.strokeStyle = cssv('--line'); ctx.lineWidth = 1;
  ctx.beginPath(); rect(0, 0, p.outline[0], p.outline[1]); ctx.fill(); ctx.stroke();
  if (S.ov.pg){ ctx.setLineDash([4, 3]); ctx.strokeStyle = cssv('--warn'); p.pg_domains.forEach(g => { const q = g.rect; ctx.beginPath(); rect(q[0], q[1], q[2] - q[0], q[3] - q[1]); ctx.stroke(); }); ctx.setLineDash([]); }
  const hovT = S.hover && S.hover.type, landing = S.ov.landing && hovT && N[hovT] ? N[hovT].plan.landing_base : null;
  for (const q of p.partitions){
    const t = N[q[1]], st = t ? t.status.state : 'not built';
    const dim = S.hide.has(st) || (landing && (!t || t.plan.landing_base !== landing));
    ctx.globalAlpha = dim ? 0.12 : 0.85; ctx.fillStyle = col(st);
    ctx.beginPath(); rect(q[2], q[3], q[4], q[5]); ctx.fill();
    ctx.globalAlpha = 1; ctx.strokeStyle = hovT === q[1] ? cssv('--ink') : cssv('--panel'); ctx.lineWidth = hovT === q[1] ? 2.5 : 0.8; ctx.stroke();
  }
  if (S.ov.cores && S.cam.k > 0.02){
    ctx.fillStyle = cssv('--ink'); ctx.globalAlpha = 0.16;
    for (const q of p.partitions){
      const t = N[q[1]]; if (!t || !t.plan.hard_cores.length) continue;
      const [W, H] = t.plan.outline;
      for (const h of t.plan.hard_cores){ const [x, y] = placeChild(q[2], q[3], q[6], W, H, h[3], h[4], h[5], h[6]); ctx.fillRect(X(x), Y(y + h[6]), Math.max(0.6, h[5] * S.cam.k), Math.max(0.6, h[6] * S.cam.k)); }
    }
    ctx.globalAlpha = 1;
  }
  if (S.ov.seams){
    const P = Object.fromEntries(p.partitions.map(q => [q[0], q]));
    ctx.strokeStyle = cssv('--accent');
    for (const [a, b, bits] of p.seams){
      const A = P[a], B = P[b]; if (!A || !B) continue;
      const seg = sharedEdge(A, B); if (!seg) continue;
      ctx.lineWidth = Math.min(3.5, 0.4 + 0.18 * Math.log2(1 + bits)); ctx.globalAlpha = 0.55;
      ctx.beginPath(); ctx.moveTo(X(seg[0]), Y(seg[1])); ctx.lineTo(X(seg[2]), Y(seg[3])); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
  if (S.ov.clock && p.clock.root){
    const [cx, cy] = p.clock.root; star(X(cx), Y(cy), 9, cssv('--tree'));
    if (p.clock.topology === 'htree'){ // H-tree first two levels, drawn from the root over the die (topology sketch, not routed geometry)
      ctx.strokeStyle = cssv('--tree'); ctx.globalAlpha = 0.6; ctx.lineWidth = 1.5;
      const W = p.outline[0], H = p.outline[1];
      const h1 = [[W / 4, cy], [3 * W / 4, cy]], lines = [[h1[0], h1[1]], [[W / 4, H / 4], [W / 4, 3 * H / 4]], [[3 * W / 4, H / 4], [3 * W / 4, 3 * H / 4]]];
      lines.forEach(([a, b]) => { ctx.beginPath(); ctx.moveTo(X(a[0]), Y(a[1])); ctx.lineTo(X(b[0]), Y(b[1])); ctx.stroke(); });
      ctx.globalAlpha = 1;
    }
  }
  if (S.ov.names && S.cam.k > 0.05){
    ctx.fillStyle = cssv('--ink'); ctx.font = '10px ' + cssv('--mono');
    for (const q of p.partitions) if (q[4] * S.cam.k > 60) ctx.fillText(q[0], X(q[2]) + 3, Y(q[3] + q[5]) + 11);
  }
  $('hint').textContent = 'scroll: zoom · drag: pan · click a slot: open its type · F: fit';
}
function sharedEdge(A, B){
  const e = 1.0, [ax, ay, aw, ah] = A.slice(2, 6), [bx, by, bw, bh] = B.slice(2, 6);
  const ox0 = Math.max(ax, bx), ox1 = Math.min(ax + aw, bx + bw), oy0 = Math.max(ay, by), oy1 = Math.min(ay + ah, by + bh);
  if (Math.abs(ax + aw - bx) < e || Math.abs(bx + bw - ax) < e){ const x = Math.abs(ax + aw - bx) < e ? bx : ax; if (oy1 > oy0) return [x, oy0, x, oy1]; }
  if (Math.abs(ay + ah - by) < e || Math.abs(by + bh - ay) < e){ const y = Math.abs(ay + ah - by) < e ? by : ay; if (ox1 > ox0) return [ox0, y, ox1, y]; }
  return null;   // not abutting: ports that cross through ft slots of the partitions between them
}
function star(x, y, r, c){ ctx.fillStyle = c; ctx.beginPath(); for (let i = 0; i < 10; i++){ const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * 0.45 : r; ctx.lineTo(x + rr * Math.cos(a), y + rr * Math.sin(a)); } ctx.closePath(); ctx.fill(); }
function faceSeg(face, win, W, H, inset){
  const a = win[0], b = win[1], k = inset || 0;
  if (face === 'N') return [a, H - k, b, H - k]; if (face === 'S') return [a, k, b, k];
  if (face === 'E') return [W - k, a, W - k, b]; return [k, a, k, b];
}
function drawType(){
  const n = S.node.node, [W, H] = n.plan.outline, K = S.node.children;
  ctx.fillStyle = cssv('--panel2'); ctx.strokeStyle = col(n.status.state); ctx.lineWidth = 2;
  ctx.beginPath(); rect(0, 0, W, H); ctx.fill(); ctx.stroke();
  for (const s of n.plan.ft_slots){
    ctx.strokeStyle = cssv('--faint'); ctx.lineWidth = 6; ctx.globalAlpha = 0.5;
    [[s.in_face, s.in_window], [s.out_face, s.out_window]].forEach(([f, w]) => { if (!f || !w) return; const g = faceSeg(f, w, W, H, 4); ctx.beginPath(); ctx.moveTo(X(g[0]), Y(g[1])); ctx.lineTo(X(g[2]), Y(g[3])); ctx.stroke(); });
    ctx.globalAlpha = 1; ctx.fillStyle = cssv('--ink');
    (s.regs || []).forEach(r => { if (Array.isArray(r) && r.length >= 2 && typeof r[0] === 'number') ctx.fillRect(X(r[0]) - 2.5, Y(r[1]) - 2.5, 5, 5); });
  }
  for (const b of n.plan.buses){
    if (!b[3] || !b[4]) continue; const g = faceSeg(b[3], b[4], W, H, 0);
    ctx.strokeStyle = cssv(b[1] === 'out' ? '--pin-out' : '--pin-in'); ctx.lineWidth = Math.min(6, 1 + 0.4 * Math.log2(1 + (b[2] || 1)));
    ctx.beginPath(); ctx.moveTo(X(g[0]), Y(g[1])); ctx.lineTo(X(g[2]), Y(g[3])); ctx.stroke();
  }
  for (const h of n.plan.hard_cores){
    const c = K[h[1]], st = c ? c.status.state : null;
    const [w, hh] = ORS.has(h[7]) ? [h[6], h[5]] : [h[5], h[6]];
    ctx.globalAlpha = 0.8; ctx.fillStyle = st ? col(st) : cssv('--core');
    ctx.beginPath(); rect(h[3], h[4], w, hh); ctx.fill(); ctx.globalAlpha = 1;
    ctx.strokeStyle = S.hover && S.hover.core === h ? cssv('--ink') : cssv('--macro'); ctx.lineWidth = S.hover && S.hover.core === h ? 2 : 1; ctx.stroke();
    if (w * S.cam.k > 70){ ctx.fillStyle = cssv('--ink'); ctx.font = '10px ' + cssv('--mono'); ctx.fillText(h[2].slice(0, Math.floor(w * S.cam.k / 6)), X(h[3]) + 3, Y(h[4] + hh) + 11); }
  }
  ctx.strokeStyle = cssv('--accent'); ctx.globalAlpha = 0.5; ctx.lineWidth = 1;
  for (const s of n.plan.stations){ const [, a, b, regs] = s; if (!a || !b) continue; const pts = [a].concat((regs || []).filter(r => Array.isArray(r))).concat([b]);
    ctx.beginPath(); pts.forEach((q, i) => i ? ctx.lineTo(X(q[0]), Y(q[1])) : ctx.moveTo(X(q[0]), Y(q[1]))); ctx.stroke(); }
  ctx.globalAlpha = 1;
  const ck = n.plan.clock;
  (ck.taps || []).forEach(t => { if (t[2]) { ctx.strokeStyle = cssv('--tree'); ctx.lineWidth = 1; const x = X(t[2][0]), y = Y(t[2][1]); ctx.beginPath(); ctx.moveTo(x - 3, y - 3); ctx.lineTo(x + 3, y + 3); ctx.moveTo(x + 3, y - 3); ctx.lineTo(x - 3, y + 3); ctx.stroke(); } });
  if (ck.tap) star(X(ck.tap[0]), Y(ck.tap[1]), 8, cssv('--tree'));
  $('hint').textContent = n.level === 'type' ? 'plan view: hard cores coloured by their own status (click one to open it) · face windows cyan in / orange out · grey: ft slots · squares: stations · star: clock tap' :
    'plan view of a hard core: its outline in the type. The routed layout tab shows its real geometry.';
}

/* ------------------------------------------------------------------ interaction */
function pickAt(mx, my){
  const wx = (mx - S.cam.x) / S.cam.k, wy = (S.cam.y - my) / S.cam.k;
  if (!S.node){
    const p = S.die.die.plan;
    for (let i = p.partitions.length - 1; i >= 0; i--){ const q = p.partitions[i]; if (wx >= q[2] && wx <= q[2] + q[4] && wy >= q[3] && wy <= q[3] + q[5]) return {part: q, type: q[1]}; }
    return null;
  }
  const n = S.node.node;
  for (const h of n.plan.hard_cores){ const [w, hh] = ORS.has(h[7]) ? [h[6], h[5]] : [h[5], h[6]]; if (wx >= h[3] && wx <= h[3] + w && wy >= h[4] && wy <= h[4] + hh) return {core: h}; }
  return null;
}
let drag = null;
cv.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY, cx: S.cam.x, cy: S.cam.y, moved: false}; cv.setPointerCapture(e.pointerId); });
cv.addEventListener('pointermove', e => {
  const r = cv.getBoundingClientRect();
  if (drag){ const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true; S.cam.x = drag.cx + dx; S.cam.y = drag.cy + dy; drawSoon(); return; }
  const h = pickAt(e.clientX - r.left, e.clientY - r.top); const key = h ? (h.type || '') + (h.part ? h.part[0] : '') + (h.core ? h.core[0] : '') : '';
  const tip = $('tip');
  if (!h){ tip.hidden = true; if (S.hover){ S.hover = null; drawSoon(); } return; }
  if (!S.hover || S.hover.key !== key){ S.hover = Object.assign({key}, h); drawSoon(); hoverFacts(h); }
  let html;
  if (h.type){ const t = S.die.nodes[h.type]; html = `<b>${esc(h.part[0])}</b><div class="m">type ${esc(t ? t.name : h.type)} · ${esc(h.part[6])}</div>${t ? `<div class="m">${badge(t.status)} ${esc(t.status.label)}${t.plan.hard_cores.length ? ' · ' + t.plan.hard_cores.length + ' hard cores' : ''}${(t.layout || {}).store ? ' · routed layout' : ''}</div>` : ''}`; }
  else { const c = S.node.children[h.core[1]]; html = `<b>${esc(h.core[0])}</b><div class="m">${esc(h.core[2])} · ${esc(h.core[7])} · ${h.core[5]} × ${h.core[6]} µm</div><div class="m">${c ? badge(c.status) + ' ' + esc(c.status.label) : 'generated memory macro'}</div>`; }
  tip.innerHTML = html; tip.hidden = false;
  tip.style.left = Math.min(r.width - 300, e.clientX - r.left + 14) + 'px'; tip.style.top = (e.clientY - r.top + 14) + 'px';
});
cv.addEventListener('pointerup', e => {
  const d0 = drag; drag = null; if (!d0 || d0.moved) return;
  const r = cv.getBoundingClientRect(), h = pickAt(e.clientX - r.left, e.clientY - r.top); if (!h) return;
  if (h.type) location.hash = nodeHref(h.type);
  else if (h.core && S.node.children[h.core[1]]) location.hash = nodeHref(h.core[1]) + '&from=' + encodeURIComponent(S.node.node.id);
});
cv.addEventListener('pointerleave', () => { $('tip').hidden = true; });
cv.addEventListener('wheel', e => { e.preventDefault(); const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top, f = Math.exp(-e.deltaY * 0.0015);
  S.cam.x = mx - (mx - S.cam.x) * f; S.cam.y = my - (my - S.cam.y) * f; S.cam.k *= f; drawSoon(); }, {passive: false});
addEventListener('keydown', e => { if (e.target.tagName === 'INPUT') return; if (e.key === 'f' || e.key === 'F'){ if ($('plan').hidden) return; fit(); drawSoon(); } });
addEventListener('resize', () => { S.cam = null; drawSoon(); });
function hoverFacts(h){
  const box = $('hov'); if (!box || !h.type) return;
  const t = S.die.nodes[h.type]; if (!t) return;
  box.innerHTML = `<h3>Hover</h3><p style="margin:0;font:700 12.5px var(--mono)">${esc(h.part[0])}</p><p class="note">type <a href="${nodeHref(t.id)}">${esc(t.name)}</a> · ${t.plan.instances} instance(s)</p>${statusFacts(t.status)}`;
}
$('theme').onclick = () => { const dark = cssv('color-scheme') !== 'light'; document.documentElement.dataset.theme = dark ? 'light' : 'dark';
  try { localStorage.setItem('otx.design.theme', document.documentElement.dataset.theme); } catch (e) {}
  if (window.LayoutViewer) LayoutViewer.theme(); drawSoon(); };
route().catch(err);
})();

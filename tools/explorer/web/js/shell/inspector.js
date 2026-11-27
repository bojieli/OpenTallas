// Inspector: details of the current selection (the same in every view) plus the tabs a view adds.
import { h, clear, fmt, fmtBytes, fmtCount, STATES, STATE_LABEL, stateCls, badge, dieShort, levelOf, fmtTime, displayState } from '../core/dom.js';
import { store } from '../core/store.js';
import { api } from '../core/api.js';

const sec = (title, n, ...body) => h('section.sec', h('h3', title, n != null ? h('span.n', n) : null), ...body);
const kv = (pairs) => h('dl.kv', pairs.filter((p) => p && p[1] != null && p[1] !== '').map(([k, v]) => [h('dt', k), h('dd', v)]));
export function stateBar(counts, total) {
  const tot = total || STATES.reduce((a, s) => a + (counts[s] || 0), 0) || 1;
  return h('div.bar', { role: 'img', 'aria-label': STATES.filter((s) => counts[s]).map((s) => `${counts[s]} ${s}`).join(', ') },
    STATES.filter((s) => counts[s]).map((s) => h('i.' + stateCls(s), { style: { width: (100 * counts[s] / tot) + '%' }, title: `${counts[s]} ${STATE_LABEL[s]}` })));
}
export const stateLegend = (counts) => h('div.legend', STATES.filter((s) => counts[s]).map((s) => h('span.' + stateCls(s), h('i.dot'), `${counts[s]} ${STATE_LABEL[s].toLowerCase()}`)));

function metricTiles(m) {
  if (!m) return null;
  const drc = m.drt_drc != null ? m.drt_drc : m.drc;
  const T = [['Setup TT', m.tt_wns, 'ps', (v) => v >= -42], ['Hold FF', m.ff_wns, 'ps', (v) => v >= 0], ['DRC', drc, '', (v) => v === 0], ['GRT ovf', m.grt_overflow, '', (v) => v === 0],
    ['LEC', m.lec, '', (v) => /pass|equiv|ok/i.test(String(v))], ['Cells', m.cells, '', null]].filter((t) => t[1] != null);
  if (!T.length) return null;
  return h('div.metrics', T.map(([k, v, u, good]) => h('div.metric' + (good ? (good(v) ? '.good' : '.bad') : ''), h('small', k), h('b', typeof v === 'number' ? (k === 'Cells' ? fmtCount(v) : fmt(v, /Setup|Hold/.test(k) ? 1 : 0)) : String(v), u ? ' ' + u : ''))));
}
function actions(n, view) {
  const A = [];
  const lvl = n.level, pack = n.layout && n.layout.store;
  if (lvl !== 'die' && view !== 'element') A.push(h('a.btn.sm', { href: store.href({ view: 'element', node: n.id }), dataset: { testid: 'act-element' } }, pack ? 'Open routed layout' : 'Open element'));
  if (view !== 'plan') A.push(h('a.btn.sm', { href: store.href({ view: 'plan', node: n.id }), dataset: { testid: 'act-plan' } }, 'Plan'));
  if (lvl === 'type' && view !== 'layout') A.push(h('a.btn.sm', { href: store.href({ view: 'layout', node: n.id }), dataset: { testid: 'act-layout' } }, 'Show on die'));
  if (lvl === 'die' && view !== 'layout') A.push(h('a.btn.sm', { href: store.href({ view: 'layout', node: n.id }), dataset: { testid: 'act-layout' } }, 'Routed die map'));
  if (view !== 'closure') A.push(h('a.btn.sm', { href: store.href({ view: 'closure', node: n.id }), dataset: { testid: 'act-closure' } }, 'Closure'));
  return h('div', { style: { display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '10px' } }, A);
}
function layoutFacts(l, src) {
  if (!l && !(src && src.resolved)) return h('p.note', 'No routed database yet: not built, or the newest attempt stopped before routing.');
  l = l || {};
  const s = l.store, rs = src && src.resolved, rec = src && src.recorded;
  const recCls = rec ? { fleet: 'build host, not the copy of record', 'off-limits': 'host is off limits, never read', archive: 'archive', none: '' }[rec.cls] : '';
  return [kv([['source', (l.source || '') + (l.legacy ? ' (legacy view)' : '')], ['stage', l.stage],
    ['signed database', rs ? [h('span.pos', { dataset: { testid: 'db-archive' } }, `${rs.where} ${rs.kind}`), h('br'), h('span.mono', rs.path)] : h('span.neg', { dataset: { testid: 'db-no-archive' } }, rec ? 'no archive copy found' : 'none')],
    src && src.archives.length > 1 ? ['other copies', src.archives.filter((a) => a !== rs).map((a) => h('div', h('span.muted', `${a.where} ${a.kind} `), h('span.mono', a.path)))] : null,
    rec ? ['built at', [h('span.mono.muted', (rec.host ? rec.host + ':' : '') + rec.path), recCls ? h('div.muted', { dataset: { testid: 'db-recorded-' + rec.cls } }, `(${recCls})`) : null]] : null,
    l.record ? ['signed record', h('span.mono', l.record.slice(0, 16) + '…')] : null, l.odb_bytes ? ['DB size', fmtBytes(l.odb_bytes)] : null,
    ['pack', s ? `${s.verify || 'unverified'} against OpenDB · ${fmtCount(s.shapes)} shapes · ${fmtBytes(s.bytes)}` : 'not cut yet'],
    s && s.made ? ['cut', String(s.made).slice(0, 16).replace('T', ' ')] : null,
    s && s.timing ? ['timing data', s.timing.sta ? `${s.timing.setup} setup + ${s.timing.hold} hold paths (${(s.timing.corners || []).join(', ').toUpperCase()}), clock tree ${fmtCount(s.timing.clock_leaves)} sinks` : `clock tree ${fmtCount(s.timing.clock_leaves)} sinks (topology only)`] : null]),
    h('p.note', 'The routed view draws the layout pack (cut once from the signed database and kept in the explorer store); it does not open the database, on any host.')];
}
const nodeRow = (n, extra, patch) => h('a.row.' + stateCls(displayState(n)), { href: store.href(Object.assign({ node: n.id }, patch || {})), title: n.id }, h('i.dot'), h('span.nm', n.name), extra ? h('small', extra) : null);

function dieDetails(D, view) {
  const d = D.die, p = d.plan, counts = d.counts_any_plan || d.counts;
  return [
    h('section.sec', h('h1', d.label), h('p.sub', `${d.target || ''} · ${fmt(p.outline[0] / 1000, 2)} × ${fmt(p.outline[1] / 1000, 2)} mm`), actions(d, view)),
    sec('Sign-off on any plan', null, h('p.note', { style: { margin: '0 0 4px' }, testid: 'insp-signoff-types' }, h('b', counts.type.signed || 0), ` of ${d.type_count} partition types signed off`), stateBar(counts.type), h('div', { style: { height: '6px' } }), stateLegend(counts.type),
      h('p.note', h('b', counts.core.signed || 0), ` of ${STATES.reduce((a, s) => a + (counts.core[s] || 0), 0)} hard cores signed off`), stateBar(counts.core)),
    sec(D.plan.wave ? 'Plan (kit wave, as counted)' : 'Plan of record', null, D.plan.wave ? h('p.note', { style: { margin: '0 0 6px' }, dataset: { testid: 'plan-wave-note' } }, `This is the plan the kit wave builds and the sign-off count counts (${D.plan.wave.host}:${D.plan.wave.path}). It is not on main yet; the pinned plan of record is ${D.plan.wave.pinned}.`) : null, kv([['plan', h('b.mono', D.plan.sha)], ['file', h('span.mono', p.path)], ['commit', h('span.mono', (p.commit || '').slice(0, 10) + ' · ' + String(p.date || '').slice(0, 10))],
      ['subject', p.subject], ['clock period', p.period_ps + ' ps'], ['reach', p.reach_um + ' µm per cycle'], ['partitions', `${p.partitions.length} placed, ${d.type_count} partition types` + ((d.hard_ip || []).length ? `, ${d.hard_ip.length} hard IP` : '')],
      ['clock', `${p.clock.topology || '?'} on ${(p.clock.layers || []).join('/')}` + (p.clock.insertion_ps ? `, ${p.clock.insertion_ps} ps insertion` : '')], ['PG domains', p.pg_domains.length], ['seams', (p.seams || []).length + ' abutting pairs with ports']]),
      p.release_header ? h('p.note', h('b', 'Historical release note. '), p.release_header) : null),
    sec('What is real here', null, h('p.note', { style: { margin: 0 } }, 'Inside a signed partition type or hard core the routed wires are exact. The die-level route has not run: die-top nets, the M8/M9 power grid and the clock trunks are plan data, shown as plan overlays.')),
  ];
}
function nodeDetails(R, view, inst) {
  const n = R.node, st = n.status, p = n.plan || {}, isType = n.level === 'type';
  const out = [h('section.sec', h('h1.mono', n.name), h('p.sub', n.superseded ? n.plan_label : isType && p.outline ? `Partition type of ${dieShort(n.die)} · ${p.instances} placement${p.instances === 1 ? '' : 's'} · ${fmt(p.outline[0], 1)} × ${fmt(p.outline[1], 1)} µm` + (p.hard ? ' · hard IP' : '')
    : `Hard core of ${dieShort(n.die)}${p.outline ? ' · ' + fmt(p.outline[0], 1) + ' × ' + fmt(p.outline[1], 1) + ' µm' : ''} · placed ${p.placements || 0}×`),
    h('div', { style: { display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' } }, R.signoff_basis ? h('span.st.st-signed', h('i.dot'), 'Signed off', h('span.muted', R.signoff_basis === 'current' ? ' · current plan' : R.signoff_basis === 'deferred' ? ' · earlier plan' : ' · retired plan')) :
        R.signoff_display_state === 'uncredited' ? h('span.st.muted', 'Uncredited') : badge(st.state, null, st.basis),
      h('span.muted', [!n.superseded && R.signoff_basis && st.state !== 'signed' && 'Current build', st.label, st.cls && 'class ' + st.cls, st.stage && 'stage ' + st.stage, st.attempt && 'attempt ' + st.attempt, st.metrics?.verdict && st.metrics.verdict !== 'SIGNED' && st.metrics.verdict].filter(Boolean).join(' · '))),
    st.reason ? h('p.note', st.reason) : null,
    st.state === 'pending archive' ? h('div.banner', { dataset: { testid: 'pending-archive' } }, h('div', h('b', R.signoff_basis === 'deferred' ? 'Current archive pending. ' : 'Current archive status. '), `The count credits this design, but the AGIdock archive does not hold all of it: missing ${((st.pending || {}).missing || []).join(', ')}${(st.pending || {}).path ? ' in ' + st.pending.path : ''}. The current-plan archive requires its database, view files and signoff.json.`)) : null,
    st.archive && !n.superseded ? h('p.note', { dataset: { testid: 'archived-at' } }, `Counted from the AGIdock archive: ${st.archive.path || st.archive.basis}`) : null, actions(n, view))];
  const mt = metricTiles(st.metrics); if (mt) out.push(sec('Sign-off metrics', null, mt));
  out.push(sec('Routed layout', null, layoutFacts(n.layout, R.sources), R.packs && R.packs.history.length > 1 ? h('p.note', `${R.packs.history.length} closures in the store; newest ${R.packs.latest}.`) : null));
  if (isType) {
    const places = R.placements || [];
    if (places.length) out.push(sec('Placements in the die', places.length, h('div.list', places.slice(0, 60).map((q) => h('a.row' + (q[0] === inst ? '.on' : ''), { href: store.href({ view: view === 'plan' ? 'plan' : 'layout', node: n.id, inst: q[0] }), title: 'Show this placement on the die', dataset: { inst: q[0] } },
      h('span.nm', q[0]), h('small', `${q[5]} · ${fmt(q[1], 0)}, ${fmt(q[2], 0)}`)))), places.length > 60 ? h('p.note', `${places.length - 60} more placements.`) : null));
    const kids = Object.values(R.children || {}).sort((a, b) => a.name.localeCompare(b.name));
    const gen = (p.hard_cores || []).filter((x) => !R.children[x[1]]).length;
    out.push(sec('Hard cores', `${(p.hard_cores || []).length} placed`, kids.length ? h('div.list', kids.map((c) => nodeRow(c, (p.hard_cores.filter((x) => x[1] === c.id).length) + '×' + ((c.layout || {}).store ? ' · routed' : '')))) : h('p.note', { style: { margin: 0 } }, 'None: this type is flat (standard cells and generated macros only).'),
      gen ? h('p.note', `${gen} generated memory macro${gen === 1 ? '' : 's'} (SRAM/ROM), not signed designs.`) : null));
    out.push(sec('Plan contents', null, kv([['module', h('span.mono', p.module)], ['face buses', (p.buses || []).length], ['feed-through slots', `${(p.ft_slots || []).length} (${(p.ft_slots || []).reduce((a, s) => a + (s.stations || 1), 0)} stations)`],
      ['internal stations', (p.stations || []).length], ['clock taps', ((p.clock || {}).taps || []).length + ((p.clock || {}).layer ? ` on ${p.clock.layer}` : '')], p.landing_base ? ['landing cohort', p.landing_base] : null])));
  } else {
    const uses = R.uses || [];
    out.push(sec('Used by', uses.length + ' types', h('div.list', uses.map((u) => nodeRow({ id: u.type, name: u.name, state: u.state, signoff_display_state: u.signoff_display_state }, `${u.count}× · ${u.placements || 0} placements`)))));
  }
  if (R.archive && R.archive.length) out.push(sec('Signed-layout archive', 'SIGNED-DB-AUDIT', R.archive.map((a) => kv(Object.entries(a).filter(([, v]) => v).slice(0, 12).map(([k, v]) => [k, h('span.mono', String(v))]))),
    h('p.note', 'Where the signed routed database lives after it left the fleet hosts. The routed view itself reads the layout pack cut from that database, so it keeps working when the fleet path is gone.')));
  if (n.vis) out.push(sec('Visual review', null, kv([['verdict', h('b', n.vis.verdict)], ['class', n.vis.cls], ['attempt', `${n.vis.attempt || ''} ${n.vis.stage || ''}`], ['cause', n.vis.cause]])));
  out.push(sec('Identity', null, kv([['node id', h('span.mono', n.id)], ['plan', h('span.mono', R.plan.sha)], ['index built', fmtTime(R.generated)]])));
  return out;
}

export function mountInspector(tabsEl, body) {
  const S = { tabs: [], cur: 'details', seq: 0, st: null, cleanup: null };
  function paintTabs() {
    clear(tabsEl);
    const all = [{ id: 'details', label: 'Details' }, ...S.tabs];
    if (!all.some((t) => t.id === S.cur)) S.cur = 'details';
    tabsEl.hidden = all.length < 2;
    for (const t of all) tabsEl.append(h('button', { type: 'button', role: 'tab', 'aria-selected': String(t.id === S.cur), dataset: { testid: 'insp-tab-' + t.id }, onclick: () => show(t.id) }, t.label));
  }
  function show(id) { S.cur = id; paintTabs(); paintBody(); }
  async function paintBody() {
    if (S.cleanup) { try { S.cleanup(); } catch (e) { /* view gone */ } S.cleanup = null; }
    const t = S.tabs.find((x) => x.id === S.cur);
    if (t) { clear(body); const c = t.render(body); if (typeof c === 'function') S.cleanup = c; return; }
    const st = S.st; if (!st) return;
    const my = ++S.seq, { die, node, inst } = st.sel;
    if (!die) { clear(body).append(h('section.sec', h('h1', 'Five dies, one chip'), h('p.sub', 'Pick a die in the top bar or a card on the Overview. The selection follows you through every view.'))); return; }
    try {
      const out = levelOf(node) === 'die' ? dieDetails(await api.die(die), st.view) : nodeDetails(await api.node(node), st.view, inst);
      if (my === S.seq && S.cur === 'details') { const y = body.dataset.for === node ? body.scrollTop : 0; clear(body).append(...out); body.dataset.for = node; body.scrollTop = y; }
    } catch (e) {
      if (my === S.seq) clear(body).append(h('section.sec', h('div.banner.bad', h('div', h('b', e.status === 404 ? 'Not in the current plan. ' : 'Could not load. '), e.status === 404 ? `${node} is not a die, partition type or hard core of any plan of record.` : e.message))));
    }
  }
  return {
    update(st) { S.st = st; if (S.cur === 'details') paintBody(); },
    /** a view's extra tabs: [{id, label, render(el) -> optional cleanup}] */
    setTabs(tabs, opts = {}) { S.tabs = tabs || []; if (opts.show) S.cur = opts.show; paintTabs(); paintBody(); },
    show, current: () => S.cur,
  };
}

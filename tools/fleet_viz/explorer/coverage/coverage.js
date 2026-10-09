// /explorer/coverage: the coverage matrix (one row per function, a cell per target), filters, ownerless gaps, owner
// streams, live closure status of each cell's elements.  Data: /api/coverage (re-derived from the ledgers on origin/main
// whenever they change; element status joined live).  Polls /api/coverage/version every 20 s and the full matrix every
// 60 s (element status moves without a ledger change).
import { GAPS, UNCOVERED, COL } from './gaps.js';

const $ = (id) => document.getElementById(id);
function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v; else if (k === 'style') e.style.cssText = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v); else if (v !== undefined && v !== null && v !== false) e.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined && k !== false) e.append(k instanceof Node ? k : document.createTextNode(String(k)));
  return e;
}
const TARGETS = ['T1', 'T2', 'T3', 'T4'];
const TOKEN = { T1: [['qwen_rom', 'AR']], T2: [['ds_rom', 'AR'], ['ds_rom&mode=mtp', 'MTP']], T3: [['hbm_ds', 'AR'], ['hbm_ds&mode=mtp', 'MTP']], T4: [] };
const GROUPS = { host: 'Host / prefill', boot: 'Boot', control: 'Decode control', sampler: 'Sampler', data: 'Decode data', deepseek: 'Decode data: DeepSeek only', mtp: 'MTP', fault: 'Fault', unmapped: 'Not yet normalised' };
const COLS = [['H', 'hw', 'hardware exists (RTL)'], ['D', 'on_die', 'on a die (master in a recipe)'], ['R', 'rtl', 'RTL path'], ['E', 'exact', 'exact bench'], ['C', 'closure', 'closure (worst element)'], ['P', 'priced', 'priced in a token path']];

let M = null, V = null, sel = null;
const F = { t: new Set(TARGETS), phase: '', plane: '', group: '', gap: new Set(), owner: '', q: '', only: false, beyond: false };

function readHash() {
  const q = Object.fromEntries(location.hash.slice(1).split('&').filter(Boolean).map((kv) => kv.split('=').map(decodeURIComponent)));
  if (q.t) F.t = new Set(q.t.split(',').filter((x) => TARGETS.includes(x)));
  for (const k of ['phase', 'plane', 'group', 'owner', 'q']) F[k] = q[k] || '';
  F.gap = new Set((q.gap || '').split(',').filter((x) => GAPS[x]));
  F.only = q.only === '1'; F.beyond = q.beyond === '1';
  sel = q.cell || null;
}
function writeHash() {
  const p = [];
  if (F.t.size !== 4) p.push('t=' + [...F.t].join(','));
  for (const k of ['phase', 'plane', 'group', 'owner', 'q']) if (F[k]) p.push(k + '=' + encodeURIComponent(F[k]));
  if (F.gap.size) p.push('gap=' + [...F.gap].join(','));
  if (F.only) p.push('only=1'); if (F.beyond) p.push('beyond=1');
  if (sel) p.push('cell=' + encodeURIComponent(sel));
  const want = p.length ? '#' + p.join('&') : ' ';
  if (location.hash !== want.trim()) history.replaceState(null, '', want.trim() || location.pathname);
}

function gapsOf(c) { return (c && c.gaps) || []; }
function level(c) {
  if (!c || c.state === 'na' || c.state === 'missing_ledger') return 'na';
  if (c.state === 'covered') return 'ok';
  const g = gapsOf(c);
  if (g.some((x) => UNCOVERED.has(x.cls))) return 'unc';
  if (g.some((x) => x.cls !== 'NOT_CLOSED')) return 'gp';
  return 'cl';
}
function cellMatches(c, r) {
  if (!c) return false;
  if (F.only && !(c.state === 'gap')) return false;
  if (F.beyond && !gapsOf(c).some((g) => g.cls !== 'NOT_CLOSED')) return false;
  if (F.gap.size && !gapsOf(c).some((g) => F.gap.has(g.cls))) return false;
  if (F.owner && !gapsOf(c).some((g) => (g.owner || 'OWNERLESS') === F.owner)) return false;
  return true;
}
function rowVisible(r) {
  if (F.phase && r.phase !== F.phase) return false;
  if (F.plane && r.plane !== F.plane) return false;
  if (F.group && r.group !== F.group) return false;
  if (F.q) {
    const s = F.q.toLowerCase();
    const hay = [r.fid, r.function, ...TARGETS.flatMap((t) => [...(r.cells[t].nodes || []), ...(r.cells[t].elements || []), ...(r.cells[t].hw_element || [])])].join(' ').toLowerCase();
    if (!hay.includes(s)) return false;
  }
  const ts = [...F.t];
  if (!(F.only || F.beyond || F.gap.size || F.owner)) return ts.some((t) => r.cells[t] && r.cells[t].state !== 'na');
  return ts.some((t) => cellMatches(r.cells[t], r));
}

// ------------------------------------------------------------------ summary cards
function cards() {
  const el = $('cards'); el.replaceChildren();
  for (const t of TARGETS) {
    const s = M.summary[t], info = M.targets[t];
    const na = M.rows.length - s.rows_applicable;
    const cl = s.with_gap - s.uncovered;
    const tp = Object.entries(M.token_paths || {}).filter(([, x]) => x.target === t);
    const card = h('div', { class: 'card', role: 'button', tabindex: 0, 'aria-pressed': String(F.t.has(t)), title: 'click to show / hide this target in the matrix',
      onclick: () => { F.t.has(t) ? F.t.delete(t) : F.t.add(t); if (!F.t.size) F.t.add(t); render(); },
      onkeydown: (e) => { if (e.key === 'Enter') e.currentTarget.click(); } },
      h('h2', {}, h('span', { class: 't' }, t), `${info.model} on ${info.machine.split(' (')[0]}`),
      h('div', { class: 'm' }, info.machine + ' · ' + info.modes),
      h('div', { class: 'big' },
        h('div', { class: 'ok' }, h('b', {}, s.covered), 'covered'),
        h('div', {}, h('b', {}, s.with_gap), 'with a gap'),
        h('div', { class: 'u' }, h('b', {}, s.uncovered), 'no HW on a die')),
      h('div', { class: 'sbar', role: 'img', 'aria-label': `${s.covered} covered, ${s.uncovered} uncovered, ${cl} other gaps of ${s.rows_applicable} applicable rows` },
        h('i', { style: `flex:${s.covered || 0.0001};background:${COL.ok}` }), h('i', { style: `flex:${s.uncovered};background:${COL.uncovered}` }),
        h('i', { style: `flex:${cl};background:${COL.gap}` })),
      h('div', { class: 'chips' }, ...Object.entries(s.by_class).filter(([, v]) => v).map(([k, v]) =>
        h('span', { class: 'chip k', style: `background:${GAPS[k].color}`, title: `${GAPS[k].label}: ${v} rows` }, `${GAPS[k].tag} ${v}`))),
      h('div', { class: 'tk' }, `${s.nodes} ledger nodes · ${s.rows_applicable} of ${M.rows.length} rows apply (${na} n/a)`),
      h('div', { class: 'tk' }, TOKEN[t].length ? ['token path: ', ...TOKEN[t].map(([d, l]) => h('a', { href: `/explorer/token/#design=${d}`, onclick: (e) => e.stopPropagation(), style: 'margin-right:8px' }, l))]
        : 'token path: none (no qwen_hbm view exists)'),
      ...tp.map(([d, x]) => h('div', { class: 'tk' }, `${d}: ${(100 * x.cycles_on_uncovered_rows / x.critical_cycles).toFixed(1)} % of critical cycles on uncovered rows`)));
    el.append(card);
  }
}

// ------------------------------------------------------------------ ownerless + streams
function ownerless() {
  const el = $('ownerless');
  const seen = new Map();
  for (const o of M.ownerless) for (const n of o.nodes) {
    const k = o.target + '|' + n;
    const x = seen.get(k) || { target: o.target, node: n, cls: new Set(), fids: new Set(), why: o.why, proposed: o.proposed };
    x.cls.add(o.cls); x.fids.add(o.fid); seen.set(k, x);
  }
  // one row per reason: the nodes that share a why / proposed owner
  const byWhy = new Map();
  for (const x of seen.values()) {
    const k = (x.why || '') + '|' + (x.proposed || '');
    const y = byWhy.get(k) || { why: x.why, proposed: x.proposed, items: [], cls: new Set(), fids: new Set() };
    y.items.push(x.target + ' ' + x.node); x.cls.forEach((c) => y.cls.add(c)); x.fids.forEach((f) => y.fids.add(f)); byWhy.set(k, y);
  }
  const list = [...byWhy.values()];
  const struct = M.ownerless_structural || [];
  el.replaceChildren(h('div', { class: 'pt' }, h('b', {}, `Ownerless gaps: ${seen.size} ledger nodes in ${list.length} groups` + (struct.length ? ` + ${struct.length} structural` : '')),
      h('span', {}, 'every other gap has an owner stream · plan: ' + (M.plan || ''))),
    h('div', { class: 'tw' }, h('table', { class: 'ol' }, h('tr', {}, h('th', {}, 'nodes'), h('th', {}, 'rows'), h('th', {}, 'gap'), h('th', {}, 'why no owner'), h('th', {}, 'proposed owner')),
      ...struct.map((x) => h('tr', {}, h('td', {}, h('b', { style: 'color:#ff4fa3' }, x.id), ' ', x.scope), h('td', {}, x.rows || ''),
        h('td', {}, h('span', { class: 'chips' }, ...(x.classes || []).map((k) => h('span', { class: 'chip k', style: `background:${GAPS[k].color}` }, GAPS[k].tag)))),
        h('td', { class: 'why' }, x.why), h('td', { class: 'why' }, x.proposed))),
      ...list.map((x) => h('tr', {}, h('td', {}, x.items.join(', ')), h('td', {}, [...x.fids].join(', ')),
        h('td', {}, h('span', { class: 'chips' }, ...[...x.cls].map((k) => h('span', { class: 'chip k', style: `background:${GAPS[k].color}` }, GAPS[k].tag)))),
        h('td', { class: 'why' }, x.why || ''), h('td', { class: 'why' }, x.proposed || ''))))));
}
function streams() {
  const el = $('streams');
  const live = M.streams_live || {};
  const counts = {};
  for (const r of M.rows) for (const t of TARGETS) for (const g of gapsOf(r.cells[t])) { const o = g.owner || 'OWNERLESS'; counts[o] = (counts[o] || 0) + 1; }
  el.replaceChildren(h('div', { class: 'pt' }, h('b', {}, 'Owner streams'), h('span', {}, 'log state from claude-takeover-20261007/*.log · click to filter')),
    h('div', { class: 'sg' }, ...Object.entries(M.streams).map(([s, info]) => {
      const L = live[s] || {};
      const st = !L.log ? (s === 'owner-decision' ? 'scope' : 'NO LOG') : L.status === 'started only' ? 'started ' + (L.mtime || '').slice(11) : 'active ' + (L.mtime || '').slice(11);
      return h('span', { class: !L.log && s !== 'owner-decision' ? 'no' : L.status === 'started only' ? 'st1' : '', title: info.scope + (L.last ? '\nlast: ' + L.last : ''), style: 'cursor:pointer',
        onclick: () => { F.owner = F.owner === s ? '' : s; render(); } }, h('b', {}, s), ` · ${st} · ${counts[s] || 0} gaps`);
    }), h('span', { class: 'no', style: 'cursor:pointer', onclick: () => { F.owner = F.owner === 'OWNERLESS' ? '' : 'OWNERLESS'; render(); } }, h('b', {}, 'OWNERLESS'), ` · ${counts.OWNERLESS || 0} gaps`)));
}

// ------------------------------------------------------------------ filters
function filters() {
  const el = $('filters');
  const opt = (v, l, cur) => h('option', { value: v, ...(v === cur ? { selected: '' } : {}) }, l);
  const phases = [...new Set(M.rows.map((r) => r.phase))].filter(Boolean);
  const planes = [...new Set(M.rows.map((r) => r.plane))].filter(Boolean);
  const owners = [...new Set(M.rows.flatMap((r) => TARGETS.flatMap((t) => gapsOf(r.cells[t]).map((g) => g.owner || 'OWNERLESS'))))].sort();
  const sel = (k, list, all) => h('select', { 'aria-label': k, onchange: (e) => { F[k] = e.target.value; render(); } }, opt('', all, F[k]), ...list.map((x) => opt(x[0] ?? x, x[1] ?? x, F[k])));
  const search = h('input', { type: 'search', placeholder: 'function, node, element', value: F.q, 'aria-label': 'search' });
  search.addEventListener('input', () => { F.q = search.value.trim(); renderTable(); writeHash(); });
  el.replaceChildren(
    h('span', { class: 'chips', role: 'group', 'aria-label': 'targets' }, ...TARGETS.map((t) => h('button', { class: 'tg', 'aria-pressed': String(F.t.has(t)),
      onclick: () => { F.t.has(t) ? F.t.delete(t) : F.t.add(t); if (!F.t.size) F.t.add(t); render(); } }, t))),
    h('label', {}, 'phase', sel('phase', phases, 'all')),
    h('label', {}, 'plane', sel('plane', planes, 'all')),
    h('label', {}, 'group', sel('group', Object.entries(GROUPS), 'all')),
    h('label', {}, 'owner', sel('owner', owners, 'any')),
    h('span', { class: 'chips', role: 'group', 'aria-label': 'gap classes' }, ...Object.entries(GAPS).map(([k, g]) => h('button', { class: 'tg', 'aria-pressed': String(F.gap.has(k)), title: g.label,
      style: F.gap.has(k) ? `border-color:${g.color}` : '', onclick: () => { F.gap.has(k) ? F.gap.delete(k) : F.gap.add(k); render(); } }, h('i', { style: `display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px;background:${g.color}` }), g.tag))),
    h('label', {}, h('input', { type: 'checkbox', ...(F.only ? { checked: '' } : {}), onchange: (e) => { F.only = e.target.checked; render(); } }), 'gaps only'),
    h('label', { title: 'hide cells whose only gap is NOT_CLOSED (the closure drive owns those)' }, h('input', { type: 'checkbox', ...(F.beyond ? { checked: '' } : {}), onchange: (e) => { F.beyond = e.target.checked; render(); } }), 'beyond closure'),
    search);
  $('legend').replaceChildren(
    ...Object.entries(GAPS).map(([k, g]) => h('span', {}, h('i', { style: `background:${g.color}` }), `${g.tag} ${g.label}`)),
    h('span', {}, h('i', { style: `background:${COL.uncovered}` }), 'left bar: no HW on a die'),
    h('span', {}, h('i', { style: `background:${COL.gap}` }), 'gap beyond closure'),
    h('span', {}, h('i', { style: 'background:#8a97b8' }), 'closure only'),
    h('span', {}, 'H D R E C P = hardware · on die · RTL · exact · closed · priced (green yes, red no, amber partial)'));
}

// ------------------------------------------------------------------ table
function colState(c, k) {
  if (k === 'closure') return c.closure === 'CLOSED' || c.closure === 'n/a' && !gapsOf(c).some((g) => g.cls === 'NOT_CLOSED') ? 'y' : c.closure === 'RUNNING' || c.closure === 'PARTIAL' ? 'p' : c.closure === 'n/a' ? 'u' : 'n';
  if (k === 'priced') return c.priced == null ? 'u' : c.priced === 'no' ? 'n' : c.priced === 'modelled' ? 'p' : 'y';
  return c[k] == null ? 'u' : c[k] ? 'y' : 'n';
}
function cellTd(r, t) {
  const c = r.cells[t];
  if (!c || c.state === 'na' || c.state === 'missing_ledger') return h('td', { class: 'c na', title: c && c.why || '' }, 'n/a');
  const lv = level(c);
  const g = gapsOf(c);
  const tags = [...new Map(g.map((x) => [x.cls, x])).values()];
  const owners = [...new Set(g.filter((x) => x.cls !== 'NOT_CLOSED' || g.length === 1).map((x) => x.owner || 'OWNERLESS'))];
  const ls = c.live_summary;
  const td = h('td', { class: 'c ' + lv, tabindex: 0, role: 'button', 'aria-label': `${r.function} on ${t}: ${lv === 'ok' ? 'covered' : g.map((x) => x.cls).join(', ')}`,
    onclick: () => openCell(r.fid, t), onkeydown: (e) => { if (e.key === 'Enter') openCell(r.fid, t); } },
    h('div', {}, h('span', { class: 'st ' + lv }, lv === 'ok' ? 'OK' : lv === 'unc' ? 'NO HW' : lv === 'gp' ? 'GAP' : 'OPEN'),
      ...owners.map((o) => h('span', { class: 'ow' + (o === 'OWNERLESS' ? ' none' : ''), style: 'margin-right:6px' }, o))),
    h('div', { class: 'cols' }, ...COLS.map(([l, k, d]) => h('span', { class: colState(c, k), title: d + ': ' + (k === 'closure' ? c.closure : k === 'priced' ? c.priced : String(c[k])) }, l))),
    tags.length ? h('div', { class: 'chips' }, ...tags.map((x) => h('span', { class: 'chip k', style: `background:${GAPS[x.cls].color}`, title: `${GAPS[x.cls].label} · ${x.owner || 'OWNERLESS'} · ${x.nodes.join(', ')}` }, GAPS[x.cls].tag))) : null,
    ls ? h('div', { class: 'lv' }, 'live: ', h('b', {}, `${ls.closed}/${ls.total}`), ' closed', ls.inflight ? ` · ${ls.inflight} in flight` : '') : null);
  return td;
}
function renderTable() {
  const ts = TARGETS.filter((t) => F.t.has(t));
  const tb = $('matrix');
  const rows = M.rows.filter(rowVisible);
  const head = h('tr', {}, h('th', {}, 'function'), ...ts.map((t) => h('th', {}, `${t} · ${M.targets[t].model} / ${M.targets[t].machine.split(' (')[0]}`)));
  const body = [];
  let grp = null;
  for (const r of rows) {
    if (r.group !== grp) { grp = r.group; body.push(h('tr', { class: 'grp' }, h('td', { colspan: ts.length + 1 }, GROUPS[grp] || grp))); }
    body.push(h('tr', {}, h('td', { class: 'fn' }, r.function, h('small', {}, `${r.fid} · ${r.phase} · ${r.plane}`)), ...ts.map((t) => cellTd(r, t))));
  }
  tb.replaceChildren(h('thead', {}, head), h('tbody', {}, ...body));
  $('count').textContent = `${rows.length} of ${M.rows.length} functions`;
}

// ------------------------------------------------------------------ drawer
function openCell(fid, t) { sel = fid + '@' + t; writeHash(); drawer(); }
function drawer() {
  const d = $('drawer');
  if (!sel || !M) { d.hidden = true; return; }
  const [fid, t] = sel.split('@');
  const r = M.rows.find((x) => x.fid === fid);
  if (!r || !r.cells[t]) { d.hidden = true; return; }
  const c = r.cells[t];
  const kids = [h('h3', {}, r.function), h('div', { class: 'kv' }, h('span', {}, 'row'), h('b', {}, `${r.fid} · ${r.group} · ${r.phase} · ${r.plane}`),
    h('span', {}, 'target'), h('b', {}, `${t}: ${M.targets[t].model} on ${M.targets[t].machine}`),
    h('span', {}, 'state'), h('b', {}, c.state === 'na' ? 'n/a: ' + (c.why || '') : c.state),
    ...(c.state !== 'na' ? [h('span', {}, 'closure'), h('b', {}, c.closure || ''), h('span', {}, 'priced'), h('b', {}, String(c.priced)), h('span', {}, 'cycles'), h('b', {}, c.cycles == null ? '—' : Math.round(c.cycles).toLocaleString())] : []))];
  for (const g of gapsOf(c)) kids.push(h('div', { class: 'chips', style: 'margin:3px 0' }, h('span', { class: 'chip k', style: `background:${GAPS[g.cls].color}` }, g.cls),
    h('span', { class: 'chip' + (g.owner ? '' : ' dim'), style: g.owner ? '' : 'color:#e66767;border-color:#6a2238' }, g.owner || 'OWNERLESS'), h('span', { class: 'chip dim' }, g.nodes.join(', ') || g.note || ''),
    g.why ? h('span', { class: 'chip dim', style: 'white-space:normal' }, g.why + (g.proposed ? ' → ' + g.proposed : '')) : null));
  if (c.live && c.live.length) {
    kids.push(h('div', { class: 'node' }, h('b', {}, 'Elements (live closure status)'),
      ...c.live.map((e) => h('div', { style: 'font:11px ui-monospace,Menlo,monospace;color:#c3cbe0;margin:3px 0' }, h('a', { class: 'el', href: '/explorer#element=' + encodeURIComponent(e.element) }, e.element),
        ` ${e.category}`, e.tt != null ? ` · TT ${e.tt >= 0 ? '+' : ''}${e.tt}` : '', e.ff != null ? ` FF ${e.ff >= 0 ? '+' : ''}${e.ff}` : '', e.live ? ` · ${e.live} live` : '', e.latest ? ` · latest ${e.latest}` : ''))));
  } else if ((c.elements || []).length) kids.push(h('div', { class: 'node' }, h('b', {}, 'Elements'), ...c.elements.map((e) => h('a', { class: 'el', href: '/explorer#element=' + encodeURIComponent(e) }, e))));
  (c.nodes || []).forEach((id, i) => kids.push(h('div', { class: 'node' }, h('b', {}, id + ': '), (c.function || [])[i] || '',
    h('div', { class: 'kv' }, h('span', {}, 'element'), h('b', {}, (c.hw_element || [])[i] || '—'), h('span', {}, 'die'), h('b', {}, (c.die || [])[i] || '—'),
      h('span', {}, 'closure'), h('b', {}, (c.closure_text || [])[i] || '—'), h('span', {}, 'token path'), h('b', {}, String((c.in_token_path || [])[i] ?? '—'))),
    h('p', {}, (c.notes || [])[i] || ''))));
  $('dbody').replaceChildren(...kids);
  d.hidden = false;
}

// ------------------------------------------------------------------ load / refresh
function render() { writeHash(); cards(); streams(); filters(); renderTable(); drawer(); }
// staleness guard (fv_stale.js): a failed / timed-out fetch, or a flagged source, raises the red banner and hatches the panels
const FV = window.FVStale || null;
let covOK = null, visibleAt = Date.now() / 1000;
const getCov = async (u, ms) => {
  if (FV) return FV.getJSON(u, ms);
  const r = await fetch(u, { cache: 'no-store' }); const m = await r.json(); if (!r.ok) throw new Error(m.error || r.status); return m;
};
function fresh(m) {
  if (!FV) return;
  FV.payload(m, ['elements', 'coverage'], 'src'); covOK = Date.now() / 1000; FV.synced(covOK);
}
if (FV) {
  FV.anchor($('covLinks'));   // one small 'stale · last sync' label; the matrix keeps its last good data untouched
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { visibleAt = Date.now() / 1000; load(); } });
  setInterval(() => {   // the 20 s version poll went quiet
    const n = Date.now() / 1000;
    if (document.hidden || n - visibleAt < 25 || covOK == null) return;
    if (n - covOK > 2 * 20 + 10) FV.issue('cov-late', `coverage data: no successful refresh for ${Math.round(n - covOK)}s`, covOK); else FV.clear('cov-late');
  }, 5000);
}
async function load(force) {
  try {
    let m;
    try { m = await getCov('/api/coverage', 30000); }
    catch (e) { if (FV) FV.fail('cov', 'coverage data: ' + e.message + (covOK ? ` (last good ${FV.hms(covOK)})` : ''), covOK); throw e; }
    if (m.error && !m.rows) { if (FV) FV.fail('cov', 'coverage data: ' + m.error, covOK); throw new Error(m.error); }
    if (FV) FV.ok('cov');
    fresh(m);
    const first = !M;
    M = m; V = m.v;
    if (first) ownerless();
    else ownerless();
    render();
    $('status').replaceChildren('source ', h('b', {}, m.source), ` · matrix v ${m.v} loaded ${m.loaded} · element status ${new Date(m.live_t * 1000).toLocaleTimeString()} · `,
      `${m.rows.length} rows, ${Object.values(m.targets).reduce((a, x) => a + x.nodes, 0)} ledger nodes · refreshes on every ledger change`,
      m.error ? h('span', { class: 'err' }, ' · ' + m.error) : '');
  } catch (e) {
    if (M) setTimeout(load, 15000);   // retry sooner: the label clears on the next good sync
    if (!M || !FV) $('status').replaceChildren(h('span', { class: 'err' }, 'coverage: ' + e.message));   // loaded data stays as it was; the stale label says why
  }
}
readHash();
$('dx').addEventListener('click', () => { sel = null; writeHash(); drawer(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && sel) { sel = null; writeHash(); drawer(); } });
window.addEventListener('hashchange', () => { readHash(); if (M) render(); });
await load();
let tick = 0;
setInterval(async () => {
  tick++;
  try {
    const d = await getCov('/api/coverage/version', 10000);
    const was = FV && (FV.has('cov') || FV.has('cov-ver'));
    if (FV) FV.ok('cov-ver');
    if (was) return load();   // recovered: resync the matrix now
    fresh(d);
    const v = d.v;
    if (v && v !== V) return load();
  } catch (e) { if (FV) FV.fail('cov-ver', 'coverage feed: ' + e.message + (covOK ? ` (last good ${FV.hms(covOK)})` : ''), covOK); }
  if (tick % 3 === 0) load();
}, 20000);

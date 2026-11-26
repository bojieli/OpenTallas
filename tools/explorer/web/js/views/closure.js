// Closure: sign-off status of every type and core (table with the academic gates), the die x state matrix, failure
// groups, and the architecture coverage ledger.
import { h, clear, fmt, fmtCount, STATES, STATE_LABEL, stateCls, dieShort, levelOf, debounce } from '../core/dom.js';
import { stateBar } from '../shell/inspector.js';

// academic profile (owner 11-13): the only blocking gates
const GATE = { tt_wns: (v) => v >= -42, ff_wns: (v) => v >= 0, drc: (v) => v === 0 };
const displayState = (r) => r.signoff_basis ? 'signed' : r.display_state || r.state;
const label = (s) => STATE_LABEL[s] || s;
const COLS = [
  ['state', 'State', (r) => STATES.indexOf(displayState(r)), null], ['name', 'Design', (r) => r.name, null], ['level', 'Level', (r) => r.level, null], ['stage', 'Stage', (r) => r.stage || '', null],
  ['attempt', 'Att.', (r) => r.attempt ?? -1, 'r'], ['tt_wns', 'Setup TT ps', (r) => r.tt_wns ?? -1e9, 'r'], ['ff_wns', 'Hold FF ps', (r) => r.ff_wns ?? -1e9, 'r'], ['drc', 'DRC', (r) => r.drc ?? 1e9, 'r'],
  ['grt_overflow', 'GRT ovf', (r) => r.grt_overflow ?? 1e9, 'r'], ['lec', 'LEC', (r) => r.lec || '', null], ['cells', 'Cells', (r) => r.cells ?? -1, 'r'], ['instances', 'Placed', (r) => r.instances ?? 0, 'r'],
  ['pack', 'Routed pack', (r) => (r.pack ? 1 : 0), null], ['db_cls', 'Signed DB', (r) => r.db_cls || '', null], ['vis', 'Visual', (r) => r.vis || '', null], ['reason', 'Class / reason', (r) => (r.cls || '') + (r.reason || ''), null]];
const TABS = [['table', 'Status table'], ['matrix', 'Die matrix'], ['failures', 'Failure groups'], ['ledger', 'Coverage ledger']];

export default {
  id: 'closure', title: 'Closure', icon: 'closure', datasets: ['design_index', 'plan_now', 'coverage'],
  async mount(ctx) {
    const { host, tools, store, api } = ctx;
    host.classList.add('scroll');
    const S = { die: null, data: null, tab: 'table', sort: 'state', dir: 1, level: 'all', states: new Set(), q: '', gate: false, seq: 0 };
    const ctl = h('div.ctlrow', { testid: 'closure-controls' }), body = h('div', { testid: 'closure-body' }); host.append(ctl, body);
    const tabSeg = h('div.seg', { role: 'tablist', 'aria-label': 'Closure section' }, TABS.map(([id, label]) => h('button', { type: 'button', dataset: { tab: id, testid: 'closure-tab-' + id }, onclick: () => ctx.setParams({ tab: id === 'table' ? null : id }, { notify: true }) }, label)));
    const lvlSeg = h('div.seg', { role: 'group', 'aria-label': 'Level' }, [['all', 'All'], ['type', 'Types'], ['core', 'Cores']].map(([id, label]) => h('button', { type: 'button', dataset: { lvl: id, testid: 'closure-level-' + id }, onclick: () => { S.level = id; paint(); } }, label)));
    const q = h('input.field', { type: 'search', placeholder: 'Filter by name, stage, reason', 'aria-label': 'Filter rows', style: { width: '210px' }, testid: 'closure-filter', spellcheck: false });
    q.addEventListener('input', debounce(() => { S.q = q.value.trim().toLowerCase(); paint(); }, 120));
    const gateBtn = h('button.btn', { type: 'button', 'aria-pressed': 'false', title: 'Only rows that miss a blocking gate: DRC 0, setup at least -42 ps, hold at least 0', testid: 'closure-gates', onclick: () => { S.gate = !S.gate; gateBtn.setAttribute('aria-pressed', String(S.gate)); paint(); } }, 'Gate misses');
    const tsvBtn = h('button.btn.ghost', { type: 'button', title: 'Copy the visible rows as TSV', testid: 'closure-tsv', onclick: copyTsv }, 'Copy TSV');
    const chipsEl = h('div', { style: { display: 'contents' } }), countEl = h('span.muted', { style: { marginLeft: 'auto', fontSize: 'var(--fs-s)', whiteSpace: 'nowrap' }, dataset: { testid: 'closure-count' } });
    tools.append(tabSeg); ctl.append(lvlSeg, q, gateBtn, chipsEl, countEl, tsvBtn);

    const gateMiss = (r) => (r.tt_wns != null && !GATE.tt_wns(r.tt_wns)) || (r.ff_wns != null && !GATE.ff_wns(r.ff_wns)) || (r.drc != null && !GATE.drc(r.drc));
    function rows() {
      const col = COLS.find((c) => c[0] === S.sort) || COLS[0];
      return S.data.rows.filter((r) => (S.level === 'all' || r.level === S.level) && (!S.states.size || S.states.has(displayState(r))) && (!S.gate || gateMiss(r)) &&
        (!S.q || (r.name + ' ' + (r.stage || '') + ' ' + (r.label || '') + ' ' + (r.cls || '') + ' ' + (r.reason || '') + ' ' + (r.vis || '')).toLowerCase().includes(S.q)))
        .sort((a, b) => { const x = col[2](a), y = col[2](b); return (x < y ? -1 : x > y ? 1 : a.name.localeCompare(b.name, 'en', { numeric: true })) * S.dir; });
    }
    async function copyTsv() {
      const R = rows(), keys = ['id', 'signoff_basis', 'state', 'label', 'cls', 'stage', 'attempt', 'tt_wns', 'ff_wns', 'drc', 'grt_overflow', 'lec', 'cells', 'instances', 'pack', 'vis', 'reason'];
      const t = [keys.join('\t')].concat(R.map((r) => keys.map((k) => String(r[k] ?? '').replace(/\s+/g, ' ')).join('\t'))).join('\n');
      try { await navigator.clipboard.writeText(t); ctx.toast(`${R.length} rows copied as TSV`); } catch (e) { ctx.toast('The browser refused clipboard access'); }
    }
    const num = (v, d, ok) => v == null ? h('td.r.muted', '–') : h('td.r' + (ok == null ? '' : ok ? '.pos' : '.neg'), fmt(v, d));
    function tableTab() {
      const d = S.data, R = rows(), sel = store.get().sel.node;
      const byState = {};
      for (const r of d.rows) {
        if (S.level !== 'all' && r.level !== S.level) continue;
        const state = displayState(r);
        byState[state] = (byState[state] || 0) + 1;
      }
      clear(chipsEl).append(...STATES.filter((s) => byState[s]).map((s) => {
        const n = byState[s];
        return h('button.chip.' + stateCls(s), { type: 'button', 'aria-pressed': String(S.states.has(s)), style: S.states.size && !S.states.has(s) ? { opacity: 0.5 } : null, dataset: { testid: 'closure-state-' + s.replace(/\s/g, '') }, title: 'Show only this state (click again to clear)',
          onclick: () => { if (S.states.has(s)) S.states.delete(s); else S.states.add(s); paint(); } }, h('i.dot'), `${label(s)} ${n}`);
      }));
      countEl.textContent = `${R.length} of ${d.rows.length} designs`;
      const head = h('tr', COLS.map((c) => h('th' + (c[3] ? '.r' : ''), { 'aria-sort': S.sort === c[0] ? (S.dir > 0 ? 'ascending' : 'descending') : null, dataset: { testid: 'closure-sort-' + c[0] }, onclick: () => { if (S.sort === c[0]) S.dir = -S.dir; else { S.sort = c[0]; S.dir = 1; } paint(); } }, c[1], S.sort === c[0] ? h('span.arr', S.dir > 0 ? '▲' : '▼') : null)));
      const tb = h('tbody');
      for (const r of R) tb.append(h('tr', { 'aria-selected': r.id === sel ? 'true' : null, dataset: { node: r.id }, title: r.label || '' },
        h('td', h('span.st.' + stateCls(displayState(r)), h('i.dot'), label(displayState(r))),
          r.signoff_basis === 'retired' ? h('div.muted', 'Retired plan') :
          r.signoff_basis === 'deferred' ? h('div.muted', r.state ? 'Earlier plan · Current: ' + label(r.state) : 'Earlier plan · Re-sign pending') :
          r.state && displayState(r) !== r.state ? h('div.muted', 'Current build: ' + label(r.state)) :
          r.basis ? h('div.muted', r.basis) : null,
          r.verdict && r.verdict !== 'SIGNED' ? h('div.muted', r.verdict) : null), h('td', h('a.mono', { href: store.href({ view: 'element', node: r.id }), title: 'Open the element' }, r.name)), h('td.muted', r.level), h('td', r.stage || ''), h('td.r', r.attempt ?? ''),
        num(r.tt_wns, 1, r.tt_wns == null ? null : GATE.tt_wns(r.tt_wns)), num(r.ff_wns, 1, r.ff_wns == null ? null : GATE.ff_wns(r.ff_wns)), num(r.drc, 0, r.drc == null ? null : GATE.drc(r.drc)), num(r.grt_overflow, 0, null),
        h('td' + (r.lec ? (/EQUIV|PASS/i.test(r.lec) ? '.pos' : '.neg') : '.muted'), r.lec || '–'), h('td.r', r.cells == null ? '–' : fmtCount(r.cells)), h('td.r', r.instances ?? ''),
        h('td', r.pack ? (r.state === 'signed' || r.state === 'pending archive' || (!r.state && r.signoff_basis) ? h('span.pos', r.pack_verify === 'IDENTICAL' ? 'identical' : 'cut') : h('span.muted', { title: 'view of an unsigned build (' + (r.layout_stage || 'stage unknown') + '): not a signed record, not counted' }, 'unsigned view')) : h('span.muted', r.layout_stage ? 'not cut' : '–')), h('td', { title: r.db_host || '' }, r.db_cls === 'archive' ? h('span.pos', 'archive') : r.db_cls === 'off-limits' ? h('span.neg', 'off-limits host') : r.db_cls === 'fleet' ? h('span' + (r.state === 'signed' ? '.neg' : '.muted'), 'fleet host') : h('span.muted', '–')), h('td' + (r.vis === 'BAD' ? '.neg' : ''), r.vis || ''), h('td.muted', { title: r.reason || '' }, [r.cls, r.reason].filter(Boolean).join(' · '))));
      tb.addEventListener('click', (e) => { if (e.target.closest('a')) return; const tr = e.target.closest('tr'); if (tr) store.go({ node: tr.dataset.node }); });
      return h('div.page', { style: { maxWidth: 'none', padding: '0 14px 30px' } },
        h('p.note', { style: { margin: '8px 0' } }, 'Blocking gates of the academic profile are coloured: routed DRC 0, setup TT at least -42 ps, hold FF at least 0. Everything else is advisory. Signed off includes qualifying sign-offs from any plan. Build metrics and release verdicts describe the current plan where available.'),
        h('div.card.sticky-head', { style: { padding: 0 } }, h('table.grid', { testid: 'closure-table' }, h('thead', head), tb)), R.length ? null : h('p.note', 'No design matches the filters.'));
    }
    async function matrixTab() {
      const r = await api.dies();
      const block = (lvl, title) => h('div.card', { style: { padding: 0, overflow: 'auto', marginBottom: '14px' } }, h('table.grid', { testid: 'closure-matrix-' + lvl }, h('thead', h('tr', { style: { cursor: 'default' } }, h('th', title), STATES.map((s) => h('th.r.' + stateCls(s), h('i.dot'), ' ', STATE_LABEL[s])), h('th.r', 'Total'), h('th', { style: { width: '30%' } }, 'Share'))),
        h('tbody', r.dies.map((d) => { const c = (d.counts_any_plan || d.counts)[lvl], tot = STATES.reduce((a, s) => a + (c[s] || 0), 0);
          return h('tr', { 'aria-selected': d.id === S.die ? 'true' : null, onclick: () => store.go({ node: d.id, params: { tab: null } }) }, h('td', h('b', d.label)), STATES.map((s) => h('td.r' + (c[s] ? '' : '.muted'), c[s] || 0)), h('td.r', tot), h('td', tot ? stateBar(c) : '')); }))));
      const area = h('div.card', { style: { padding: 0, overflow: 'auto' } }, h('table.grid', { testid: 'closure-matrix-area' }, h('thead', h('tr', { style: { cursor: 'default' } }, h('th', 'Share of die area by state of the placed type'), STATES.map((s) => h('th.r', STATE_LABEL[s])), h('th.r', 'Uncovered'))),
        h('tbody', r.dies.map((d) => { const a = d.area_um2, states = a.by_state_any_plan || a.by_state, cov = Object.values(states).reduce((x, y) => x + y, 0);
          return h('tr', { style: { cursor: 'default' } }, h('td', h('b', d.label)), STATES.map((s) => h('td.r' + (states[s] ? '' : '.muted'), states[s] ? fmt(100 * states[s] / a.die, 1) + ' %' : '–')), h('td.r', fmt(100 * (1 - cov / a.die), 1) + ' %')); }))));
      return h('div.page', { style: { maxWidth: 'none', padding: '12px 14px 30px' } }, h('h2.sect', { style: { marginTop: '4px' } }, 'Current partition types with sign-offs from any plan'), block('type', 'Die'), h('h2.sect', 'Hard cores'), block('core', 'Die'), h('h2.sect', 'Die area'), area);
    }
    function failuresTab() {
      const G = new Map();
      for (const r of S.data.rows) { if (r.state !== 'failed' && !gateMiss(r) && r.vis !== 'BAD') continue; const k = r.state === 'failed' ? `${r.label}${r.cls ? ' · ' + r.cls : ''}` : gateMiss(r) ? 'signed or building, but a blocking gate is missed' : 'visual verdict BAD (advisory)'; if (!G.has(k)) G.set(k, []); G.get(k).push(r); }
      const groups = [...G.entries()].sort((a, b) => b[1].length - a[1].length);
      return h('div.page', { style: { maxWidth: '1300px', padding: '12px 14px 30px' } }, h('p.lead', `${groups.reduce((a, g) => a + g[1].length, 0)} of ${S.data.rows.length} designs of ${S.data.label} are failed, miss a blocking gate, or carry a BAD visual verdict. One group is one class of problem: fix the class, not the row.`),
        groups.length ? groups.map(([k, R]) => h('div.card', { style: { marginBottom: '12px' }, dataset: { testid: 'failure-group' } }, h('h3', k, h('small', `${R.length} design${R.length === 1 ? '' : 's'}`)),
          h('div.list', R.slice(0, 40).map((r) => h('a.row.' + stateCls(r.state), { href: store.href({ node: r.id }), title: r.reason || '' }, h('i.dot'), h('span.nm', { style: { flex: '0 0 300px' } }, r.name), h('small', { style: { flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', textAlign: 'left' } }, r.reason || [r.tt_wns != null ? `setup ${fmt(r.tt_wns, 1)} ps` : '', r.ff_wns != null ? `hold ${fmt(r.ff_wns, 1)} ps` : '', r.drc != null ? `DRC ${r.drc}` : '', r.vis_cause || ''].filter(Boolean).join(' · ')))),
          R.length > 40 ? h('div.more', `${R.length - 40} more in the status table.`) : null))) : h('div.banner.info', h('div', 'No failed design, gate miss or BAD verdict on this die.')));
    }
    async function ledgerTab() {
      let c; try { c = await api.coverage(); } catch (e) { return h('div.page', h('div.banner.bad', h('div', h('b', 'The coverage ledger did not load. '), e.message))); }
      if (c.error) return h('div.page', h('div.banner.bad', h('div', h('b', 'The coverage ledger is not available. '), String(c.error))));
      const T = Object.keys(c.targets), cell = (x) => !x ? h('td.muted', 'n/a') : h('td', { title: (x.gaps || []).map((g) => `${g.cls} (${g.owner})`).join('\n') }, x.state === 'covered' ? h('span.pos', 'covered') : x.state === 'gap' ? h('span', (x.gaps || []).length + ' gap' + ((x.gaps || []).length === 1 ? '' : 's'), h('span.muted', ' · ' + [...new Set((x.gaps || []).map((g) => g.cls))].join(', ').toLowerCase().replace(/_/g, ' '))) : h('span.neg', x.state || '?'));
      return h('div.page', { style: { maxWidth: 'none', padding: '12px 14px 30px' } }, h('p.lead', `Architecture coverage ledger: which model functions each target machine covers with built, closed and priced hardware. Source ${c.source || c.generator}; generated ${c.generated}. This ledger describes the October target definitions; it is not the sign-off count.`),
        h('div.cards', { style: { marginBottom: '14px' } }, T.map((t) => { const s = c.summary[t] || {}, g = c.targets[t]; return h('div.card', h('h3', t, h('small', g.model)), h('p.note', { style: { margin: 0 } }, g.machine + ' · ' + g.modes), h('div.pair', h('div', h('div.big', s.covered ?? '–', h('small', `/ ${s.rows_applicable ?? '?'} functions covered`))), h('div', h('div.big', s.uncovered ?? '–', h('small', 'uncovered')))),
          h('div.legend', Object.entries(s.by_class || {}).filter(([, n]) => n).map(([k, n]) => h('span', `${n} ${k.toLowerCase().replace(/_/g, ' ')}`)))); })),
        h('div.card', { style: { padding: 0, overflow: 'auto' } }, h('table.grid', { testid: 'ledger-table' }, h('thead', h('tr', { style: { cursor: 'default' } }, h('th', 'Function'), h('th', 'Group'), T.map((t) => h('th', t)))),
          h('tbody', c.rows.map((r) => h('tr', { style: { cursor: 'default' } }, h('td', { style: { whiteSpace: 'normal', minWidth: '260px' } }, r.function), h('td.muted', r.group), T.map((t) => cell(r.cells[t]))))))));
    }
    async function paint() {
      const my = ++S.seq2 || (S.seq2 = 1);
      tabSeg.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.tab === S.tab)));
      lvlSeg.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.lvl === S.level)));
      ctl.hidden = S.tab !== 'table';
      const y = host.scrollTop;
      const out = S.tab === 'matrix' ? await matrixTab() : S.tab === 'failures' ? failuresTab() : S.tab === 'ledger' ? await ledgerTab() : tableTab();
      if (my !== S.seq2) return;
      clear(body).append(out); host.scrollTop = S.keepScroll ? y : 0; S.keepScroll = true;
      const cur = body.querySelector('tr[aria-selected="true"]'); if (cur && S.reveal) { cur.scrollIntoView({ block: 'center' }); S.reveal = false; }
    }
    return {
      async update(st, prev) {
        const { die, node } = st.sel, my = ++S.seq, tab = TABS.some((t) => t[0] === st.params.tab) ? st.params.tab : 'table';
        if (die !== S.die) { S.data = await api.closure(die); if (my !== S.seq) return; S.die = die; S.keepScroll = false; }
        if (tab !== S.tab) { S.tab = tab; S.keepScroll = false; }
        if (!prev || prev.sel.node !== node) S.reveal = levelOf(node) !== 'die';
        const census = S.data.signoff_census;
        ctx.setScope(`${dieShort(die)} · ${census ? census.any + ' signed off on any plan · ' + census.current + ' current · ' : ''}plan ${S.data.plan.sha}`);
        await paint();
      },
      destroy() {},
    };
  },
};

// Token: where one token spends its cycles.  Records are opentallas.token_path.v1 exports of the token simulator
// (tools/token_path_export.py); the flow graph and swimlane renderers are the kept modules (explorer/token/flow.js,
// gantt.js, core.js Clock), mounted here on one replay clock.  "Runs on" maps token classes to current design nodes
// (token_design_map.py) with the confidence grade of each mapping.
import { h, clear, fmt, fmtCount, icon, stateCls, STATE_LABEL, dieShort, fmtTime, fmtAge, debounce } from '../core/dom.js';
import { showBusy } from '../shell/shell.js';

const DIE_DESIGN = { s81: 'ds_rom', s81_head: 'ds_rom', qwen_compute: 'qwen_rom', qwen_kvsys: 'qwen_rom', hbm: 'hbm_gen_ds' };
const SERIES = ['--c1', '--c2', '--c3', '--c4', '--c5', '--c6', '--c7', '--c8'];
let lib = null;
const loadLib = () => lib || (lib = Promise.all([import('/explorer/token/core.js'), import('/explorer/token/flow.js'), import('/explorer/token/gantt.js')]).then(([core, flow, gantt]) => ({ core, flow, gantt })));
const pct = (x) => (x * 100).toFixed(x < 0.01 ? 2 : 1) + ' %';

export default {
  id: 'token', title: 'Token', icon: 'token', datasets: ['token', 'token_map'],
  async mount(ctx) {
    const { host, tools, store, api } = ctx;
    host.classList.add('scroll');
    const S = { design: null, mode: 'ar', data: null, map: null, group: null, op: null, clock: null, flow: null, gantt: null, seq: 0, index: null };
    const page = h('div.page.tokpage', { testid: 'token-page' }); host.append(page);
    const designSel = h('select.field', { 'aria-label': 'Token design', title: 'Model and machine', style: { maxWidth: '300px' }, testid: 'tok-design', onchange: (e) => store.go({ tok: e.target.value }) });
    const modeSeg = h('div.seg', { role: 'group', 'aria-label': 'Decoding mode' }, ['ar', 'mtp'].map((m) => h('button', { type: 'button', dataset: { mode: m, testid: 'tok-mode-' + m }, onclick: () => ctx.setParams({ mode: m === 'ar' ? null : 'mtp' }, { notify: true }) }, m.toUpperCase())));
    const playBtn = h('button.btn', { type: 'button', title: 'Play or pause the replay', testid: 'tok-play', onclick: () => S.clock && S.clock.toggle() }, icon('play'), 'Replay');
    const speedSel = h('select.field', { 'aria-label': 'Replay length', title: 'Replay length', testid: 'tok-speed', onchange: (e) => { if (S.clock) S.clock.seconds = +e.target.value; } }, [[12, '12 s'], [24, '24 s'], [60, '60 s']].map(([v, l]) => h('option', { value: v, selected: v === 24 }, l)));
    const upBtn = h('button.btn', { type: 'button', title: 'Back to the whole token', testid: 'tok-up', onclick: () => selectGroup(null) }, 'Whole token');
    tools.append(designSel, modeSeg, playBtn, speedSel, upBtn);

    const selectGroup = (g) => store.go({ tok: S.design + (g ? ':' + g : '') });
    function runsOnTab(el) {
      const M = S.map;
      if (!M || M.error) { el.append(h('section.sec', h('div.banner', h('div', h('b', 'No node map for this design. '), (M && M.error) || 'token_design_map.py has not mapped it.')))); return; }
      el.append(h('section.sec', h('h3', 'Runs on'), h('p.note', { style: { margin: 0 } }, `Token classes mapped to today's partition types and hard cores. ${pct(M.coverage.named)} of token cycles map by name, ${pct(M.coverage.inferred)} by inference; the grade is shown per class. Map built ${fmtTime(M.generated && Date.parse(M.generated) / 1000 || S.index.map_generated)}.`)));
      for (const [cid, c] of Object.entries(M.classes).sort((a, b) => (b[1].cycle_share || 0) - (a[1].cycle_share || 0))) {
        const nodes = c.nodes.map((id) => Object.assign({ id }, M.nodes[id])).filter((n) => n.name), signed = nodes.filter((n) => n.state === 'signed').length;
        const open = S.openCls === cid;
        el.append(h('section.sec', h('h3', c.label, h('span.n', pct(c.cycle_share || 0))),
          h('div', { style: { display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', fontSize: 'var(--fs-s)' } }, h('span.chip', { title: c.why }, c.confidence === 'named' ? 'mapped by name' : 'inferred'), h('span.muted', `${c.types} partition types · ${c.cores} hard cores · ${signed} of ${nodes.length} signed off · ${c.exported} routed packs`)),
          h('p.note', c.why),
          h('button.btn.sm', { type: 'button', style: { marginTop: '6px' }, dataset: { testid: 'tok-cls-' + cid }, onclick: () => { S.openCls = open ? null : cid; ctx.inspector.show('runs'); } }, open ? 'Hide the designs' : `Show the ${nodes.length} designs`),
          open ? h('div.list', { style: { marginTop: '6px' } }, nodes.sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true })).map((n) => h('a.row.' + stateCls(n.state), { href: store.href({ view: n.layout ? 'element' : 'plan', node: n.id }), title: n.id }, h('i.dot'), h('span.nm', n.name), h('small', `${dieShort(n.die)} · ${n.level}${n.layout ? ' · routed' : ''}`)))) : null));
      }
    }
    function opTab(el) {
      const n = S.op;
      if (!n) { el.append(h('section.sec', h('p.note', { style: { margin: 0 } }, 'Open a stage in the flow graph, then click an operator (a circle, or a bar in the timeline).'))); return; }
      const src = n.src || {};
      el.append(h('section.sec', h('h1.mono', n.label || n.id), h('p.sub', `${n.group} · class ${n.cls}${n.critical ? ' · on the critical path' : ''}`),
        h('dl.kv', h('dt', 'cycles'), h('dd', fmt(n.cycles, 1)), h('dt', 'base cycles'), h('dd', fmt(n.base_cycles, 1)), h('dt', 'start – end'), h('dd', `${fmt(n.start, 0)} – ${fmt(n.end, 0)}`), h('dt', 'grade'), h('dd', h('b', src.grade || '?')),
          src.record ? [h('dt', 'record'), h('dd', h('span.mono', src.record))] : null, src.pointer ? [h('dt', 'pointer'), h('dd', h('span.mono', src.pointer))] : null, src.note ? [h('dt', 'note'), h('dd', src.note)] : null,
          n.hw ? [h('dt', 'hardware'), h('dd', `${n.hw.status}${n.hw.note ? ' · ' + n.hw.note : ''}`)] : null)),
      (n.adders || []).length ? h('section.sec', h('h3', 'Adders'), h('dl.kv', n.adders.map((a) => [h('dt', a.name || a.id || 'adder'), h('dd', fmt(a.cycles, 1) + ' cycles')]))) : null);
    }
    ctx.inspector.setTabs([{ id: 'runs', label: 'Runs on', render: runsOnTab }, { id: 'op', label: 'Operator', render: opTab }]);

    function headline() {
      const d = S.data, hl = d.headline || {}, c = d.composition_1018, row = S.index.index.designs.find((x) => x.design === S.design) || {}, date = S.index.dates[S.design], age = date ? Date.now() / 1000 - date : null;
      const grades = c && c.available && c.by_grade ? Object.entries(c.by_grade) : Object.entries((d.totals || {}).by_grade || {}), gt = grades.reduce((a, g) => a + g[1], 0) || 1;
      return [
        h('div.banner' + (age != null && age > 7 * 86400 ? '' : '.info'), { testid: 'tok-banner' }, h('div', h('b', age != null && age > 7 * 86400 ? 'Older than the plans of record. ' : 'Token record. '),
          `Exported by ${d.tool || 'token_path_export.py'} at repo head ${d.repo_head || '?'}, committed ${date ? fmtTime(date) + ' (' + fmtAge(age) + ')' : 'at an unknown date'}. It describes ${(d.geometry && d.geometry.die) || 'the die revision of that date'}, not today's plans. Rates are analytic records (measured, composed or priced as graded), not a token pass on the release dies.`)),
        h('div.card', h('h3', d.title || row.title || S.design, h('small', hl.mode || (S.mode === 'mtp' ? 'MTP' : 'AR'))),
          h('div.pair', { style: { gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' } },
            h('div', h('div.big', fmt(hl.tok_s ?? d.totals.tok_s, 1), h('small', 'tok/s (record headline)'))), h('div', h('div.big', fmtCount(d.totals.cycles), h('small', 'cycles per token'))),
            h('div', h('div.big', fmt(d.totals.us, 1), h('small', 'µs per token'))), c && c.available ? h('div', h('div.big', fmt(c.tok_s, 1), h('small', `tok/s composed 10-18 · ${fmt(c.pct_measured_current_rtl, 1)} % on current RTL`))) : null),
          h('div.bar', { style: { height: '10px' }, role: 'img', 'aria-label': 'cycles by provenance grade' }, grades.map(([g, v], i) => h('i', { style: { '--c': `var(${SERIES[i % 8]})`, width: (100 * v / gt) + '%' }, title: `${g}: ${fmtCount(v)} cycles` }))),
          h('div.legend', grades.map(([g, v], i) => h('span', h('i.sq', { style: { '--c': `var(${SERIES[i % 8]})` } }), `${g} ${pct(v / gt)}`))),
          hl.status ? h('p.note', { style: { margin: 0 } }, `${hl.status}. ${hl.basis || ''}`) : null, (d.totals || {}).reproduces ? h('p.note.mono', { style: { margin: 0 } }, d.totals.reproduces) : null),
      ];
    }
    function stages() {
      const d = S.data, G = d.groups.slice().sort((a, b) => (b.share || 0) - (a.share || 0)).slice(0, 14), mx = Math.max(...G.map((g) => g.share || 0), 1e-9);
      return h('div.card', h('h3', 'Largest stages', h('small', `${d.groups.length} stages · click to open one`)), h('div.list', { testid: 'tok-stages' }, G.map((g) => h('button.row' + (g.id === S.group ? '.on' : ''), { type: 'button', title: g.label, dataset: { group: g.id }, onclick: () => selectGroup(g.id) },
        h('span.nm', { style: { flex: '0 0 44%' } }, g.label || g.id), h('span', { style: { flex: 1, height: '8px', background: 'var(--surface-3)', borderRadius: '4px', overflow: 'hidden' } }, h('i', { style: { display: 'block', height: '100%', width: (100 * (g.share || 0) / mx) + '%', background: g.critical ? 'var(--c1)' : 'var(--c-other)' } })), h('small.num', { style: { width: '54px', textAlign: 'right' } }, pct(g.share || 0))))));
    }
    async function render() {
      const d = S.data, L = await loadLib();
      if (S.flow) { S.flow.destroy(); S.flow = null; } if (S.gantt) { S.gantt.destroy(); S.gantt = null; }
      const g = S.group && L.core.P(d).groups[S.group] ? L.core.P(d).groups[S.group] : null;
      if (!S.clock) { S.clock = new L.core.Clock({ t0: 0, t1: d.totals.cycles, seconds: +speedSel.value }); S.clock.on(() => { const on = S.clock.playing; if (playBtn.dataset.on !== String(on)) { playBtn.dataset.on = String(on); clear(playBtn).append(icon(on ? 'pause' : 'play'), on ? 'Pause' : 'Replay'); } }); }
      S.clock.pause(); S.clock.scope(g ? g.start : 0, g ? g.end : d.totals.cycles, +speedSel.value);
      const flowEl = h('div.tokdark', { testid: 'tok-flow' }), ganttEl = h('div.tokdark', { testid: 'tok-gantt' });
      clear(page).append(...headline(), h('div.tokgrid', stages(),
        h('div.card', h('h3', g ? `Stage ${g.label || g.id}` : 'Flow by stage', h('small', g ? `${fmtCount(g.cycles)} cycles · ${pct(g.share || 0)} of the token · operators as a DAG, critical chain on the centre row` : 'each box is one stage, width by cycles, colours by element class; click a stage to open it')), flowEl)),
        h('div.card', h('h3', 'Timeline by element class', h('small', g ? 'the selected stage' : 'the whole token · click a stage in the strip to zoom')), ganttEl));
      upBtn.disabled = !g;
      S.flow = L.flow.mountFlow(flowEl, d, { clock: S.clock, group: g ? g.id : null, onDrill: (id) => selectGroup(id), onSelect: (n) => { S.op = n; ctx.inspector.show('op'); } });
      S.gantt = L.gantt.mountGantt(ganttEl, d, { clock: S.clock, range: g ? [g.start, g.end] : null, onZoom: (id) => selectGroup(id), onSelect: (n) => { S.op = n; ctx.inspector.show('op'); } });
    }
    const onResize = debounce(() => { if (S.data) render(); }, 250); window.addEventListener('resize', onResize);

    return {
      async update(st) {
        const my = ++S.seq;
        if (!S.index) { S.index = await api.tokenIndex(); clear(designSel); for (const x of S.index.index.designs) designSel.append(h('option', { value: x.design }, x.title ? x.title.split(',')[0] : x.design)); }
        const [dz, grp] = String(st.sel.tok || '').split(':'), known = S.index.index.designs.map((x) => x.design);
        const design = known.includes(dz) ? dz : (known.includes(DIE_DESIGN[st.sel.die]) ? DIE_DESIGN[st.sel.die] : known[0]);
        const row = S.index.index.designs.find((x) => x.design === design), mtpOk = !!(row && row.mtp && row.mtp.available && row.mtp.file), mode = st.params.mode === 'mtp' && mtpOk ? 'mtp' : 'ar';
        designSel.value = design;
        modeSeg.querySelectorAll('button').forEach((b) => { b.setAttribute('aria-pressed', String(b.dataset.mode === mode)); if (b.dataset.mode === 'mtp') { b.disabled = !mtpOk; b.title = mtpOk ? 'One multi-token-prediction verify step' : (row && row.mtp && row.mtp.reason) || 'No MTP record for this design'; } });
        if (design !== S.design || mode !== S.mode) {
          const busy = showBusy(host, 'Loading the token record…'); busy.classList.add('clear');
          try {
            const rec = mode === 'mtp' ? row.mtp.file.replace(/\.json$/, '') : design;
            const [data, map] = await Promise.all([api.tokenRecord(rec), api.tokenMap(design).catch((e) => ({ error: e.message }))]);
            if (my !== S.seq) return;
            S.data = data; S.map = map; S.design = design; S.mode = mode; S.op = null; S.clock = null;
          } finally { busy.remove(); }
        }
        S.group = grp || null;
        ctx.setScope(`${design}${mode === 'mtp' ? ' · MTP' : ''}${S.group ? ' · ' + S.group : ''}`);
        await render();
        if (ctx.inspector.current() !== 'details') ctx.inspector.show(ctx.inspector.current());
      },
      destroy() { window.removeEventListener('resize', onResize); if (S.clock) S.clock.pause(); if (S.flow) S.flow.destroy(); if (S.gantt) S.gantt.destroy(); document.querySelectorAll('.tp-tip').forEach((t) => t.remove()); },
    };
  },
};

// Dataflow: which blocks talk, how wide, how far.
//   Plan of record (current): partition-to-partition port bundles of the die plan (plan seams: bits and port windows per
//   pair), abutting or passing through feed-through slots of the partitions between them.
//   Link records (kept engine, tools/fleet_viz/dataflow_links.py + explorer/dataflow/model.js): pin-to-pin links of one
//   die revision with reach verdicts.  These records carry their own revision and date; they are not the plan of record.
import { h, clear, fmt, fmtUm, icon, cssv, levelOf, dieShort, shortName, debounce, stateCls, fmtTime, fmtAge } from '../core/dom.js';
import { PlanCanvas, sharedEdge } from '../engine/plan-canvas.js';
import { showBusy } from '../shell/shell.js';

const DESIGNS = { s81: ['ds_rom'], s81_head: ['ds_rom'], qwen_compute: ['qwen_rom'], qwen_kvsys: ['qwen_rom'], hbm: ['hbm', 'hbm_gen_ds', 'hbm_gen_qwen', 'hbm_ds'] };
const VERDICT = [['ok', 'within reach', '--ok'], ['relay', 'relayed / needs relay', '--warn'], ['over', 'hop beyond reach', '--bad'], ['unknown', 'unplaced', '--s-notbuilt']];
const KIND = [['abut', 'abutting partitions', '--ok'], ['through', 'through feed-through slots', '--warn']];
const fmtBits = (b) => !Number.isFinite(b) ? 'width unknown' : b >= 1e6 ? fmt(b / 1e6, 2) + ' Mbit' : b >= 1e4 ? fmt(b / 1e3, 1) + ' kbit' : fmt(b) + ' bit';
const wpx = (bits, k = 1) => k * Math.min(6, 0.6 + 0.36 * Math.log2(Math.max(1, Number.isFinite(bits) ? bits : 1)));
let modelLib = null;
const loadModelLib = () => modelLib || (modelLib = import('/explorer/dataflow/model.js'));

export default {
  id: 'dataflow', title: 'Dataflow', icon: 'dataflow', datasets: ['design_index'],
  async mount(ctx) {
    const { host, tools, store, api } = ctx;
    const S = { die: null, D: null, mode: 'plan', links: [], rec: null, m: null, recId: null, minBits: 0, hide: new Set(), hover: null, seq: 0, moving: false, index: null, sort: 'bits' };
    const wrap = h('div.canvas-host'); host.append(wrap);
    const tip = h('div.tip', { hidden: true }), legend = h('div.hud.tl.act', { testid: 'df-legend', style: { whiteSpace: 'normal', right: '8px' } }), banner = h('div', { hidden: true, style: { position: 'absolute', left: '8px', right: '8px', bottom: '8px', zIndex: 6 }, testid: 'df-banner' });
    wrap.append(tip, legend, banner);
    const modeSeg = h('div.seg', { role: 'group', 'aria-label': 'Source' }, h('button', { type: 'button', dataset: { mode: 'plan', testid: 'df-mode-plan' }, title: 'Port bundles between partitions of the current plan of record' }, 'Plan of record'),
      h('button', { type: 'button', dataset: { mode: 'record', testid: 'df-mode-record' }, title: 'Pin-to-pin link records of earlier die revisions' }, 'Link records'));
    modeSeg.querySelectorAll('button').forEach((b) => { b.onclick = () => ctx.setParams({ src: b.dataset.mode === 'plan' ? null : 'record', cam: null }, { notify: true }); });
    const recSel = h('select.field', { hidden: true, 'aria-label': 'Link record', title: 'Die revision of the link record', style: { maxWidth: '300px' }, testid: 'df-record', onchange: (e) => ctx.setParams({ rec: e.target.value, cam: null }, { notify: true }) });
    const bitsSel = h('select.field', { 'aria-label': 'Minimum width', title: 'Hide links narrower than this', testid: 'df-minbits', onchange: (e) => { S.minBits = +e.target.value; ctx.setParams({ min: S.minBits || null }); repaint(); } },
      [[0, 'All widths'], [8, '≥ 8 bit'], [64, '≥ 64 bit'], [512, '≥ 512 bit'], [4096, '≥ 4 kbit']].map(([v, l]) => h('option', { value: v }, l)));
    const fitBtn = h('button.btn', { type: 'button', title: 'Fit (F)', testid: 'df-fit', onclick: () => pc.fit() }, icon('fit'), 'Fit');
    tools.append(modeSeg, recSel, bitsSel, fitBtn);

    const settle = debounce(() => { S.moving = false; pc.redraw(); }, 160);
    const pc = new PlanCanvas(wrap, {
      draw, onView() { S.moving = true; settle(); saveCam(); readout(); },
      onHover(wx, wy, mx, my) {
        S.mouse = wx == null ? null : [wx, wy]; readout();
        const hit = wx == null ? null : pick(wx, wy);
        if ((hit && hit.key) !== (S.hover && S.hover.key)) { S.hover = hit; pc.redraw(); }
        if (!hit) { tip.hidden = true; pc.cv.style.cursor = ''; return; }
        clear(tip).append(h('b', hit.name), h('div.m', hit.sub), hit.links != null ? h('div.m', `${hit.links} link${hit.links === 1 ? '' : 's'} · ${fmtBits(hit.bits)}`) : null, hit.node ? h('div.m', 'click to select') : null);
        tip.hidden = false; pc.cv.style.cursor = hit.node ? 'pointer' : ''; const r = wrap.getBoundingClientRect(); tip.style.left = Math.min(r.width - tip.offsetWidth - 8, mx + 14) + 'px'; tip.style.top = Math.min(r.height - tip.offsetHeight - 8, my + 14) + 'px';
      },
      onClick(wx, wy) { const hit = pick(wx, wy); if (hit && hit.node) store.go({ node: hit.node, inst: hit.inst }); else if (hit && S.mode === 'record') { S.selBlock = S.selBlock === hit.b ? null : hit.b; pc.redraw(); refreshLinks(); } },
    });
    const saveCam = debounce(() => { const c = pc.center(); ctx.setParams({ cam: [c[0].toFixed(1), c[1].toFixed(1), Math.log2(c[2]).toFixed(2)].join(',') }); }, 300);
    const repaint = () => { pc.redraw(); paintLegend(); refreshLinks(); };
    const refreshLinks = () => { if (ctx.inspector.current() === 'links') ctx.inspector.show('links'); };
    function readout() { const c = pc.cam; if (c) ctx.setReadout((S.mouse ? `x ${fmt(S.mouse[0], 1)}  y ${fmt(S.mouse[1], 1)} µm   ` : '') + `${fmt(c.k, c.k < 1 ? 4 : 2)} px/µm`); }

    /* ---------------- plan-of-record links */
    function buildPlan() {
      const p = S.D.die.plan, idx = Object.fromEntries(p.partitions.map((q) => [q[0], q])), reach = p.reach_um || 405, L = [];
      for (const [a, b, bits, nwin, wins] of p.seams || []) {
        const A = idx[a], B = idx[b]; if (!A || !B) continue;
        const e = sharedEdge(A, B), ca = [A[2] + A[4] / 2, A[3] + A[5] / 2], cb = [B[2] + B[4] / 2, B[3] + B[5] / 2];
        const dist = Math.abs(ca[0] - cb[0]) + Math.abs(ca[1] - cb[1]);
        L.push({ a, b, A, B, bits, nwin, wins, kind: e ? 'abut' : 'through', edge: e, ca, cb, dist, reach });
      }
      S.links = L; S.partIdx = idx;
      S.per = new Map(); for (const l of L) for (const n of [l.a, l.b]) { const x = S.per.get(n) || { links: 0, bits: 0 }; x.links++; x.bits += l.bits; S.per.set(n, x); }
    }
    const planShown = () => S.links.filter((l) => l.bits >= S.minBits && !S.hide.has(l.kind));
    function drawPlan(g, T) {
      const p = S.D.die.plan, { X, Y, k } = T, st = store.get().sel, selType = levelOf(st.node) === 'type' ? st.node : null, selInst = st.inst;
      const C = { surface: cssv('--surface'), line: cssv('--line-strong'), fill: cssv('--surface-3'), ink: cssv('--ink'), ink3: cssv('--ink-3'), accent: cssv('--accent'), abut: cssv('--ok'), through: cssv('--warn'), sel: cssv('--select') };
      g.fillStyle = C.surface; g.strokeStyle = C.line; g.lineWidth = 1; g.beginPath(); g.rect(X(0), Y(p.outline[1]), p.outline[0] * k, p.outline[1] * k); g.fill(); g.stroke();
      for (const q of p.partitions) { const on = q[1] === selType || q[0] === selInst, hov = S.hover && S.hover.key === q[0];
        g.fillStyle = on ? cssv('--accent-soft') : C.fill; g.strokeStyle = hov || q[0] === selInst ? C.sel : C.surface; g.lineWidth = hov || q[0] === selInst ? 2 : 0.8;
        g.beginPath(); g.rect(X(q[2]), Y(q[3] + q[5]), q[4] * k, q[5] * k); g.fill(); g.stroke(); }
      const focus = selInst || (S.hover && S.hover.key), shown = planShown();
      for (const kind of ['through', 'abut']) for (const l of shown) {
        if (l.kind !== kind) continue;
        const hot = focus && (l.a === focus || l.b === focus);
        g.globalAlpha = focus ? (hot ? 1 : 0.1) : kind === 'abut' ? 0.85 : 0.55; g.strokeStyle = C[kind]; g.lineWidth = wpx(l.bits);
        g.beginPath();
        if (l.edge) { const e = l.edge, mx = (e[0] + e[2]) / 2, my = (e[1] + e[3]) / 2, len = Math.max(6 / k, Math.min(l.A[4], l.A[5], l.B[4], l.B[5]) * 0.28), vert = e[0] === e[2];   // a tick across the shared edge
          g.moveTo(X(mx - (vert ? len : 0)), Y(my - (vert ? 0 : len))); g.lineTo(X(mx + (vert ? len : 0)), Y(my + (vert ? 0 : len))); }
        else { g.moveTo(X(l.ca[0]), Y(l.ca[1])); g.lineTo(X(l.cb[0]), Y(l.ca[1])); g.lineTo(X(l.cb[0]), Y(l.cb[1])); }   // Manhattan sketch between the partition centres
        g.stroke();
      }
      g.globalAlpha = 1;
      if (k > 0.03) { g.fillStyle = C.ink3; g.font = '10px ' + cssv('--mono'); g.textBaseline = 'top'; for (const q of p.partitions) { const w = q[4] * k; if (w > 60 && q[5] * k > 16) g.fillText(q[0].slice(0, Math.floor((w - 8) / 6.1)), X(q[2]) + 3, Y(q[3] + q[5]) + 3); } }
    }

    /* ---------------- link records */
    async function loadRecord(id) {
      const lib = await loadModelLib(), rec = await api.dataflowRecord(id);
      S.rec = rec; S.m = lib.buildModel(rec); S.lib = lib; S.recId = id; S.selBlock = null;
      const m = S.m, n = m.segLink.length, order = new Int32Array(n); for (let i = 0; i < n; i++) order[i] = i;
      S.order = Array.from(order).sort((a, b) => (m.seg[b * 5 + 4] || 0) - (m.seg[a * 5 + 4] || 0));
      S.counts = [0, 0, 0, 0]; for (let i = 0; i < m.nl; i++) S.counts[m.status[i]]++;
    }
    function drawRecord(g, T, size) {
      const m = S.m, { X, Y, k } = T, C = { surface: cssv('--surface'), line: cssv('--line-strong'), fill: cssv('--surface-3'), ink3: cssv('--ink-3'), sel: cssv('--select') };
      const col = VERDICT.map((v) => cssv(v[2]));
      g.fillStyle = C.surface; g.strokeStyle = C.line; g.lineWidth = 1; g.beginPath(); g.rect(X(0), Y(m.H), m.W * k, m.H * k); g.fill(); g.stroke();
      const vx0 = -X(0) / k, vx1 = (size.w - X(0)) / k, vy1 = Y(0) / k, vy0 = (Y(0) - size.h) / k;
      g.fillStyle = C.fill;
      for (let b = 0; b < m.nb; b++) { const w = m.bw[b] * k, hh = m.bh[b] * k; if (w < 1.2 && hh < 1.2) continue; if (m.bx[b] > vx1 || m.bx[b] + m.bw[b] < vx0 || m.by[b] > vy1 || m.by[b] + m.bh[b] < vy0) continue; g.fillRect(X(m.bx[b]), Y(m.by[b] + m.bh[b]), Math.max(1, w - 0.5), Math.max(1, hh - 0.5)); }
      if (S.selBlock != null) { const b = S.selBlock; g.strokeStyle = C.sel; g.lineWidth = 2; g.strokeRect(X(m.bx[b]), Y(m.by[b] + m.bh[b]), m.bw[b] * k, m.bh[b] * k); }
      const seg = m.seg, lim = S.moving ? 30000 : 400000, sel = S.selBlock != null ? new Set(S.lib.incident(m, S.selBlock)) : null, lane = store.get().sel.lane != null ? +String(store.get().sel.lane).replace(/^L/, '') : null;
      const paths = {}; let drawn = 0;
      for (const s of S.order) {
        const li = m.segLink[s], st = m.status[li], bits = seg[s * 5 + 4] || m.bits[li] || 1;
        if (S.hide.has(VERDICT[st][0]) || (Number.isFinite(m.bits[li]) ? m.bits[li] : 0) < S.minBits) continue;
        if (sel && !sel.has(li)) continue;
        const x0 = seg[s * 5], y0 = seg[s * 5 + 1], x1 = seg[s * 5 + 2], y1 = seg[s * 5 + 3];
        if ((x0 < vx0 && x1 < vx0) || (x0 > vx1 && x1 > vx1) || (y0 < vy0 && y1 < vy0) || (y0 > vy1 && y1 > vy1)) continue;
        if ((Math.abs(x1 - x0) + Math.abs(y1 - y0)) * k < 1.5) continue;
        const wb = bits >= 512 ? 2 : bits >= 16 ? 1 : 0, key = st * 3 + wb; (paths[key] || (paths[key] = [])).push(s);
        if (++drawn >= lim) break;
      }
      for (const key of Object.keys(paths)) { const st = Math.floor(key / 3), wb = key % 3; g.strokeStyle = col[st]; g.lineWidth = [0.6, 1.2, 2.4][wb]; g.globalAlpha = st === 0 ? 0.5 : 0.85; g.beginPath();
        for (const s of paths[key]) { g.moveTo(X(seg[s * 5]), Y(seg[s * 5 + 1])); g.lineTo(X(seg[s * 5 + 2]), Y(seg[s * 5 + 3])); } g.stroke(); }
      g.globalAlpha = 1;
      if (lane != null && lane < m.nl) { g.strokeStyle = C.sel; g.lineWidth = 3; g.beginPath(); for (let s = m.segStart[lane]; s < m.segStart[lane + 1]; s++) { g.moveTo(X(seg[s * 5]), Y(seg[s * 5 + 1])); g.lineTo(X(seg[s * 5 + 2]), Y(seg[s * 5 + 3])); } g.stroke(); }
      S.drawn = drawn;
    }
    function draw(g, T, size) { if (S.mode === 'plan' && S.D) drawPlan(g, T); else if (S.mode === 'record' && S.m) drawRecord(g, T, size); }
    function pick(wx, wy) {
      if (S.mode === 'plan' && S.D) { const P = S.D.die.plan.partitions; for (let i = P.length - 1; i >= 0; i--) { const q = P[i]; if (wx >= q[2] && wx <= q[2] + q[4] && wy >= q[3] && wy <= q[3] + q[5]) { const x = S.per.get(q[0]) || { links: 0, bits: 0 }; return { key: q[0], name: q[0], sub: shortName(q[1]), node: q[1], inst: q[0], links: x.links, bits: x.bits }; } } return null; }
      if (S.mode === 'record' && S.m) { const m = S.m; let best = null, ba = Infinity; for (let b = 0; b < m.nb; b++) if (wx >= m.bx[b] && wx <= m.bx[b] + m.bw[b] && wy >= m.by[b] && wy <= m.by[b] + m.bh[b]) { const a = m.bw[b] * m.bh[b]; if (a < ba) { ba = a; best = b; } }
        if (best == null) return null; const inc = S.lib.incident(m, best); return { key: 'b' + best, b: best, name: m.bname[best], sub: [m.bmaster[best], m.bkind[best], m.bgroup[best]].filter(Boolean).join(' · '), links: inc.length, bits: inc.reduce((a, i) => a + (Number.isFinite(m.bits[i]) ? m.bits[i] : 0), 0) }; }
      return null;
    }
    function paintLegend() {
      clear(legend);
      const item = (id, label, v, n) => h('label', { style: { display: 'inline-flex', gap: '5px', alignItems: 'center', cursor: 'pointer', opacity: S.hide.has(id) ? 0.45 : 1, marginRight: '12px' }, title: 'Click to hide or show' },
        h('input', { type: 'checkbox', checked: !S.hide.has(id), style: { display: 'none' }, dataset: { testid: 'df-show-' + id }, onchange: (e) => { if (e.target.checked) S.hide.delete(id); else S.hide.add(id); repaint(); } }), h('i.sq', { style: { '--c': `var(${v})` } }), `${label} ${fmt(n)}`);
      if (S.mode === 'plan') { const L = S.links, tot = L.reduce((a, l) => a + l.bits, 0);
        legend.append(h('b', `${fmt(L.length)} partition pairs exchange ports · ${fmtBits(tot)} in total`), h('div', KIND.map(([id, label, v]) => item(id, label, v, L.filter((l) => l.kind === id).length))), h('div.muted', 'Line width grows with the bit count. A tick sits on the edge two abutting partitions share; an angled line joins partitions whose ports cross other partitions.'));
      } else if (S.m) { const m = S.m, cov = (S.rec.coverage || {});
        legend.append(h('b', `${fmt(m.nl)} links · ${fmt(m.nb)} blocks · reach ${m.reach} µm`), h('div', VERDICT.map(([id, label, v], i) => S.counts[i] ? item(id, label, v, S.counts[i]) : null)), h('div.muted', (S.drawn >= 400000 ? 'Drawing the 400,000 widest segments in view. ' : '') + 'Click a block to see only its links.' + (cov.unplaced ? ` ${fmt(cov.unplaced)} links have an unplaced end.` : '')));
      }
    }
    function linksTab(el) {
      if (S.mode === 'plan') {
        const focus = store.get().sel.inst, L = planShown().filter((l) => !focus || l.a === focus || l.b === focus).sort((a, b) => S.sort === 'dist' ? b.dist - a.dist : b.bits - a.bits).slice(0, 200);
        el.append(h('section.sec', h('h3', focus ? `Links of ${focus}` : 'Widest links', h('span.n', `${L.length} shown`)), focus ? h('p.note', { style: { margin: '0 0 6px' } }, h('a', { href: store.href({ inst: null }) }, 'Show the links of the whole die')) : null,
          h('table.grid', { testid: 'df-links' }, h('thead', h('tr', h('th', { onclick: () => {} }, 'Between'), h('th.r', { dataset: { testid: 'df-sort-bits' }, onclick: () => { S.sort = 'bits'; refreshLinks(); } }, 'Bits'), h('th.r', { dataset: { testid: 'df-sort-dist' }, onclick: () => { S.sort = 'dist'; refreshLinks(); } }, 'Centre distance'), h('th', 'Kind'))),
            h('tbody', L.map((l) => h('tr', { title: `${l.nwin} port window${l.nwin === 1 ? '' : 's'}`, onclick: () => { const o = l.a === focus ? l.B : l.A; store.go({ node: o[1], inst: o[0] }); const bb = [Math.min(l.A[2], l.B[2]), Math.min(l.A[3], l.B[3]), Math.max(l.A[2] + l.A[4], l.B[2] + l.B[4]), Math.max(l.A[3] + l.A[5], l.B[3] + l.B[5])]; pc.zoomTo(bb, 0.7); } },
              h('td.mono', { style: { whiteSpace: 'normal' } }, `${l.a} ↔ ${l.b}`), h('td.r', fmt(l.bits)), h('td.r', fmtUm(l.dist)), h('td', h('span' + (l.kind === 'abut' ? '.pos' : ''), l.kind === 'abut' ? 'abutting' : 'through')))))),
          h('p.note', 'Source: the port windows of the die plan of record. Bits are bundle widths of the plan, not routed wires; the die-level route has not run.')));
        return;
      }
      if (!S.m) { el.append(h('section.sec', h('p.note', { style: { margin: 0 } }, 'Pick a link record.'))); return; }
      const m = S.m, pool = S.selBlock != null ? S.lib.incident(m, S.selBlock) : Array.from({ length: m.nl }, (_, i) => i);
      const L = pool.filter((i) => !S.hide.has(VERDICT[m.status[i]][0]) && (Number.isFinite(m.bits[i]) ? m.bits[i] : 0) >= S.minBits).sort((a, b) => (m.bitum[b] || 0) - (m.bitum[a] || 0)).slice(0, 120), lane = store.get().sel.lane;
      el.append(h('section.sec', h('h3', S.selBlock != null ? `Links of ${m.bname[S.selBlock]}` : 'Worst links by bits × length', h('span.n', `${L.length} shown`)),
        h('div.list', { testid: 'df-links' }, L.map((i) => h('button.row' + (lane === 'L' + i ? '.on' : ''), { type: 'button', title: S.lib.statusText(m, i), onclick: () => { const bb = Array.from(m.bbox.subarray(i * 4, i * 4 + 4)); if (Number.isFinite(bb[0])) pc.zoomTo(bb, 0.6); store.go({ lane: 'L' + i }); } },
          h('i.sq', { style: { '--c': `var(${VERDICT[m.status[i]][2]})` } }), h('span.nm', S.lib.linkLabel(m, i)), h('small', `${fmtBits(m.bits[i])} · ${fmtUm(m.len[i])}`)))),
        h('p.note', `Reach verdicts use ${m.reach} µm per cycle${m.explicit ? ' and the register stages of the record' : '; the record carries no register placement, so amber means relays are needed'}.`)));
    }
    ctx.inspector.setTabs([{ id: 'links', label: 'Links', render: linksTab }]);
    const onKey = (e) => { if (!/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) && (e.key === 'f' || e.key === 'F') && !e.metaKey && !e.ctrlKey) pc.fit(); };
    document.addEventListener('keydown', onKey);
    const onTheme = () => pc.redraw(); window.addEventListener('otx:theme', onTheme);

    return {
      async update(st, prev) {
        const { die } = st.sel, my = ++S.seq, mode = st.params.src === 'record' ? 'record' : 'plan';
        S.minBits = +st.params.min || 0; bitsSel.value = String(S.minBits);
        if (!S.index) { try { S.index = await api.dataflowIndex(); } catch (e) { S.index = { records: [] }; } }
        const dieChanged = die !== S.die;
        if (dieChanged) { const busy = showBusy(wrap, 'Loading the plan…'); try { S.D = await api.die(die); } finally { busy.remove(); } if (my !== S.seq) return; S.die = die; buildPlan(); }
        const recs = S.index.records.filter((r) => (DESIGNS[die] || []).includes(r.design) || (r.token_designs || []).some((t) => (DESIGNS[die] || []).includes(t)));
        modeSeg.querySelectorAll('button').forEach((b) => { b.setAttribute('aria-pressed', String(b.dataset.mode === mode)); if (b.dataset.mode === 'record') { b.disabled = !recs.length; if (!recs.length) b.title = 'No link record exists for this die'; } });
        const modeChanged = mode !== S.mode || dieChanged; S.mode = mode; S.hover = null; tip.hidden = true;
        if (modeChanged) S.hide.clear();
        recSel.hidden = mode !== 'record'; banner.hidden = true;
        if (mode === 'record' && recs.length) {
          const id = recs.some((r) => r.id === st.params.rec) ? st.params.rec : (recs.find((r) => r.role === 'canonical') || recs[0]).id;
          clear(recSel); for (const r of recs) recSel.append(h('option', { value: r.id, selected: r.id === id }, `${r.label}${r.role === 'canonical' ? '' : ' · ' + r.role}`));
          if (id !== S.recId) { const busy = showBusy(wrap, 'Loading the link record…'); try { await loadRecord(id); } catch (e) { busy.remove(); throw e; } busy.remove(); if (my !== S.seq) return; pc.setWorld([S.m.W, S.m.H]); }
          else if (modeChanged) pc.setWorld([S.m.W, S.m.H]);
          const r = recs.find((x) => x.id === id), gen = Date.parse(r.generated) / 1000, plan = S.D.plan;
          banner.hidden = false; clear(banner).append(h('div.banner', h('div', h('b', 'Not the plan of record. '), `This link record describes die revision “${r.revision || r.label}”, generated ${fmtTime(gen)} (${fmtAge(Date.now() / 1000 - gen)}). The plan of record of ${dieShort(die)} is ${plan.sha} (${String(plan.date || '').slice(0, 10)}). Block names and positions differ; use “Plan of record” for today's partition links.`)));
          ctx.setScope(`${dieShort(die)} · link record ${id}`);
        } else {
          if (modeChanged) pc.setWorld(S.D.die.plan.outline);
          ctx.setScope(`${dieShort(die)} · port bundles of plan ${S.D.plan.sha}`);
        }
        if (modeChanged) { const cam = (st.params.cam || '').split(',').map(Number); if (cam.length === 3 && cam.every(Number.isFinite)) pc.setCenter(cam[0], cam[1], Math.pow(2, cam[2])); }
        paintLegend(); pc.redraw(); refreshLinks(); readout();
      },
      destroy() { document.removeEventListener('keydown', onKey); window.removeEventListener('otx:theme', onTheme); pc.destroy(); },
    };
  },
};

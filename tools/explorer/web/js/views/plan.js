// Plan: the die plan of record drawn to scale (partitions by sign-off state, seams, clock, PG, hard cores), and the
// plan contents of one type (hard cores, face buses, feed-through slots, stations, clock taps).
import { h, clear, fmt, icon, STATES, STATE_LABEL, stateCls, levelOf, dieShort, shortName, debounce, ls, displayState, displayStateLabel } from '../core/dom.js';
import { PlanCanvas, drawDiePlan, drawTypePlan, placeChild, coreSize } from '../engine/plan-canvas.js';
import { showBusy } from '../shell/shell.js';

const OV_DIE = [['seams', 'Seams (port windows between abutting partitions)'], ['cores', 'Hard cores inside partitions'], ['clock', 'Clock root and trunk sketch'], ['pg', 'Power domains'], ['names', 'Partition names']];
const OV_TYPE = [['buses', 'Face buses (in / out)'], ['ft', 'Feed-through slots and stations'], ['stations', 'Internal station chains'], ['clock', 'Clock tap points'], ['names', 'Core names']];

export default {
  id: 'plan', title: 'Plan', icon: 'plan', datasets: ['design_index'],
  async mount(ctx) {
    const { host, tools, store, api } = ctx;
    const S = { die: null, D: null, node: null, R: null, scope: 'die', ov: Object.assign({ seams: true, cores: true, clock: true, pg: false, names: true, buses: true, ft: true, stations: true }, ls.get('plan.ov', {})), hide: new Set(), colorBy: 'state', hover: null, seq: 0 };
    const wrap = h('div.canvas-host'); host.append(wrap);
    const tip = h('div.tip', { hidden: true }); const legend = h('div.hud.tl.act', { testid: 'plan-legend' });
    wrap.append(tip, legend);
    const scopeSeg = h('div.seg', { role: 'group', 'aria-label': 'Scope' },
      h('button', { type: 'button', dataset: { scope: 'die', testid: 'plan-scope-die' }, title: 'The whole die' }, 'Die'), h('button', { type: 'button', dataset: { scope: 'type', testid: 'plan-scope-type' }, title: 'The plan contents of the selected type' }, 'Type'));
    const colorSel = h('select.field', { 'aria-label': 'Colour partitions by', title: 'Colour partitions by', testid: 'plan-colorby' }, h('option', { value: 'state' }, 'Colour: sign-off on any plan'), h('option', { value: 'pack' }, 'Colour: routed pack'), h('option', { value: 'vis' }, 'Colour: visual verdict'));
    const fitBtn = h('button.btn', { type: 'button', title: 'Fit (F)', testid: 'plan-fit' }, icon('fit'), 'Fit');
    tools.append(scopeSeg, colorSel, fitBtn);
    scopeSeg.querySelectorAll('button').forEach((b) => b.onclick = () => ctx.setParams({ scope: b.dataset.scope === 'die' ? null : 'type' }, { notify: true }));
    colorSel.onchange = () => { S.colorBy = colorSel.value; ctx.setParams({ color: S.colorBy === 'state' ? null : S.colorBy }); paintLegend(); pc.redraw(); };
    fitBtn.onclick = () => pc.fit();

    const saveCam = debounce(() => { if (!pc.cam) return; const c = pc.center(); ctx.setParams({ cam: [c[0].toFixed(1), c[1].toFixed(1), Math.log2(c[2]).toFixed(2)].join(',') }); }, 300);
    const pc = new PlanCanvas(wrap, {
      draw(g, T, size) {
        if (!S.D) return;
        if (S.scope === 'type' && S.R) drawTypePlan(g, T, S.R.node, S.R.children || {}, { ov: S.ov, hover: S.hover && S.hover.core, selCore: null });
        else drawDiePlan(g, T, S.D.die, S.D.nodes, { ov: S.ov, hide: S.hide, colorBy: S.colorBy, selType: levelOf(S.node) === 'type' ? S.node : S.coreUsers, selInst: store.get().sel.inst, hover: S.hover && S.hover.part, w: size.w, h: size.h, partIndex: S.partIndex });
      },
      onView() { saveCam(); readout(); },
      onHover(wx, wy, mx, my) {
        S.mouse = wx == null ? null : [wx, wy];
        const hit = wx == null ? null : pick(wx, wy);
        if ((hit && (hit.part || hit.core)) !== (S.hover && (S.hover.part || S.hover.core))) { S.hover = hit; pc.redraw(); }
        readout();
        if (!hit) { tip.hidden = true; pc.cv.style.cursor = ''; return; }
        pc.cv.style.cursor = 'pointer';
        clear(tip);
        if (hit.part) { const q = hit.part, t = S.D.nodes[q[1]];
          tip.append(h('b', q[0]), h('div.m', shortName(q[1])), h('div', t ? h('span.st.' + stateCls(displayState(t)), h('i.dot'), displayStateLabel(t)) : 'not in the index'),
            h('div.m', `${fmt(q[4], 1)} × ${fmt(q[5], 1)} µm at ${fmt(q[2], 0)}, ${fmt(q[3], 0)} · ${q[6]}`), h('div.m', 'click: select · double-click: open the element'));
        } else { const c = hit.core, cn = S.R.children[c[1]];
          tip.append(h('b', c[0]), h('div.m', c[2]), h('div', cn ? h('span.st.' + stateCls(displayState(cn)), h('i.dot'), displayStateLabel(cn)) : 'generated memory macro (no design of its own)'),
            h('div.m', `${fmt(coreSize(c)[0], 1)} × ${fmt(coreSize(c)[1], 1)} µm · ${c[7]}`), cn ? h('div.m', 'click: select this core') : null); }
        tip.hidden = false; const r = wrap.getBoundingClientRect(); tip.style.left = Math.min(r.width - tip.offsetWidth - 8, mx + 14) + 'px'; tip.style.top = Math.min(r.height - tip.offsetHeight - 8, my + 14) + 'px';
      },
      onClick(wx, wy) {
        const hit = pick(wx, wy);
        if (hit && hit.part) store.go({ node: hit.part[1], inst: hit.part[0] });
        else if (hit && hit.core && S.R.children[hit.core[1]]) store.go({ node: hit.core[1], params: { scope: null } });
      },
      onDblClick(wx, wy) { const hit = pick(wx, wy); if (hit && hit.part) store.go({ view: 'element', node: hit.part[1], inst: hit.part[0] }); },
    });
    function pick(wx, wy) {
      if (!S.D) return null;
      if (S.scope === 'type' && S.R) { for (const c of S.R.node.plan.hard_cores || []) { const [w, hh] = coreSize(c); if (wx >= c[3] && wx <= c[3] + w && wy >= c[4] && wy <= c[4] + hh) return { core: c }; } return null; }
      const P = S.D.die.plan.partitions;
      for (let i = P.length - 1; i >= 0; i--) { const q = P[i]; if (wx >= q[2] && wx <= q[2] + q[4] && wy >= q[3] && wy <= q[3] + q[5]) return { part: q }; }
      return null;
    }
    function readout() { const c = pc.cam; if (!c) return; ctx.setReadout((S.mouse ? `x ${fmt(S.mouse[0], 1)}  y ${fmt(S.mouse[1], 1)} µm   ` : '') + `${fmt(c.k, c.k < 1 ? 4 : 2)} px/µm`); }
    function paintLegend() {
      clear(legend);
      if (S.scope === 'type') { legend.append(h('div.legend', h('span', h('i.sq', { style: { '--c': 'var(--pin-in)' } }), 'bus in'), h('span', h('i.sq', { style: { '--c': 'var(--pin-out)' } }), 'bus out'), h('span', h('i.sq', { style: { '--c': 'var(--faint)' } }), 'feed-through'), h('span', h('i.sq', { style: { '--c': 'var(--tree)' } }), 'clock tap'), h('span', h('i.sq', { style: { '--c': 'var(--macro)' } }), 'hard core (fill = its state)'))); return; }
      if (S.colorBy === 'pack') { legend.append(h('div.legend', h('span', h('i.sq', { style: { '--c': 'var(--accent)' } }), 'routed pack in the store'), h('span', h('i.sq', { style: { '--c': 'var(--s-notbuilt)' } }), 'no pack'))); return; }
      if (S.colorBy === 'vis') { legend.append(h('div.legend', h('span', h('i.sq', { style: { '--c': 'var(--ok)' } }), 'good'), h('span', h('i.sq', { style: { '--c': 'var(--warn)' } }), 'other verdict'), h('span', h('i.sq', { style: { '--c': 'var(--bad)' } }), 'bad'), h('span', h('i.sq', { style: { '--c': 'var(--s-notbuilt)' } }), 'not reviewed'))); return; }
      const c = S.D ? (S.D.die.counts_any_plan || S.D.die.counts).type : {};
      legend.append(h('div.legend', STATES.filter((s) => c[s]).map((s) => h('label.' + stateCls(s), { style: { display: 'inline-flex', gap: '5px', alignItems: 'center', cursor: 'pointer', opacity: S.hide.has(s) ? 0.45 : 1 }, title: 'Click to hide or show' },
        h('input', { type: 'checkbox', checked: !S.hide.has(s), style: { display: 'none' }, dataset: { testid: 'plan-state-' + s.replace(/\s/g, '') }, onchange: (e) => { if (e.target.checked) S.hide.delete(s); else S.hide.add(s); paintLegend(); pc.redraw(); } }),
        h('i.sq'), `${STATE_LABEL[s]} ${c[s]}`))));
    }
    function overlaysTab(el) {
      const list = S.scope === 'type' ? OV_TYPE : OV_DIE;
      el.append(h('section.sec', h('h3', 'Overlays'), list.map(([k, label]) => h('label.chk', h('input', { type: 'checkbox', checked: !!S.ov[k], dataset: { testid: 'plan-ov-' + k }, onchange: (e) => { S.ov[k] = e.target.checked; ls.set('plan.ov', S.ov); pc.redraw(); } }), label))),
        h('section.sec', h('h3', 'Reading the plan'), h('p.note', { style: { margin: 0 } }, S.scope === 'type' ? 'Hard cores are filled by their sign-off status across all plans. Thick lines on the faces are buses (width grows with the bit count); grey bars are feed-through windows with their register stations; crosses are clock taps and the star is the type clock entry.'
          : 'Partitions use the geometry of the plan of record and sign-offs from any plan. Blue seam lines mark abutting partition pairs that exchange ports (thicker = more bits). The dashed clock tree is the planned topology, not routed metal.')));
    }
    ctx.inspector.setTabs([{ id: 'overlays', label: 'Overlays', render: overlaysTab }]);
    const onTheme = () => pc.redraw(); window.addEventListener('otx:theme', onTheme);
    const onKey = (e) => { if (!/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) && e.target !== pc.cv && (e.key === 'f' || e.key === 'F') && !e.metaKey && !e.ctrlKey && !e.altKey) pc.fit(); };   // F fits wherever the focus is
    document.addEventListener('keydown', onKey);

    return {
      async update(st) {
        const { die, node, inst } = st.sel, my = ++S.seq;
        if (die !== S.die) { const busy = showBusy(wrap, 'Loading the plan…'); try { S.D = await api.die(die); } finally { busy.remove(); } if (my !== S.seq) return; S.die = die; S.partIndex = null; S.cam0 = false; }
        const lvl = levelOf(node), wantType = st.params.scope === 'type' && lvl !== 'die';
        S.colorBy = st.params.color || 'state'; colorSel.value = S.colorBy;
        const nodeChanged = node !== S.node; S.node = node; S.coreUsers = null;
        if (lvl !== 'die') { try { S.R = await api.node(node); } catch (e) { S.R = null; } if (my !== S.seq) return; if (lvl === 'core' && S.R) S.coreUsers = new Set(S.R.node.plan.used_by || []); } else S.R = null;
        const scope = wantType && S.R && S.R.node.plan.outline ? 'type' : 'die';
        const scopeChanged = scope !== S.scope || (scope === 'type' && nodeChanged); S.scope = scope; S.hover = null; tip.hidden = true;
        scopeSeg.querySelectorAll('button').forEach((b) => { b.setAttribute('aria-pressed', String(b.dataset.scope === scope)); if (b.dataset.scope === 'type') b.disabled = lvl === 'die'; });
        colorSel.hidden = scope === 'type';
        const world = scope === 'type' ? S.R.node.plan.outline : S.D.die.plan.outline;
        if (scopeChanged || !S.cam0) {
          pc.setWorld(world); S.cam0 = true;
          const cam = (st.params.cam || '').split(',').map(Number);
          if (cam.length === 3 && cam.every(Number.isFinite)) pc.setCenter(cam[0], cam[1], Math.pow(2, cam[2]));
        }
        if (scope === 'die' && inst && nodeChanged === false && S.lastInst !== inst) { /* keep the camera: the ring shows the placement */ }
        S.lastInst = inst;
        ctx.setScope(scope === 'type' ? `${shortName(node)} · plan contents` : `${dieShort(die)} · ${S.D.die.plan.partitions.length} partitions · plan ${S.D.plan.sha}`);
        paintLegend(); if (ctx.inspector.current() === 'overlays') ctx.inspector.show('overlays');
        pc.redraw(); readout();
      },
      destroy() { document.removeEventListener('keydown', onKey); window.removeEventListener('otx:theme', onTheme); pc.destroy(); },
    };
  },
};

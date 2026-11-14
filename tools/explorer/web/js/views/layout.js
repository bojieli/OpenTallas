// Layout: the die with the real routed wires of every signed type and of its hard cores, in place (composition
// manifest of EXPLORER-P1, /api/v1/compose/<die>).  Far out: plan rectangles + density rasters; zoom in: exact wires.
import { h, clear, fmt, fmtCount, icon, stateColor, hexRgb, levelOf, dieShort, shortName, debounce, STATE_LABEL, stateCls, fmtBytes } from '../core/dom.js';
import { LayoutEngine, xfOf, xfCompose, xfChild, xfBox, SGN } from '../engine/layout-engine.js';
import { layersTab } from './layers-panel.js';
import { showBusy } from '../shell/shell.js';

export default {
  id: 'layout', title: 'Layout', short: 'Layout', icon: 'layout', datasets: ['design_index', 'compose', 'store'],
  async mount(ctx) {
    const { host, tools, store, api } = ctx;
    const S = { die: null, man: null, unsigned: false, seq: 0, selfPick: false };
    const wrap = h('div.canvas-host'); host.append(wrap);
    const head = h('div.hud.tl', { testid: 'layout-summary', style: { right: '204px', whiteSpace: 'normal' } });
    const eng = new LayoutEngine(wrap, {
      onView: debounce((c) => ctx.setParams({ cam: [c.x.toFixed(2), c.y.toFixed(2), c.z.toFixed(2)].join(',') }), 300),
      onStats: (s) => ctx.setReadout((s.mouse ? `x ${fmt(s.mouse[0], 2)}  y ${fmt(s.mouse[1], 2)} µm   ` : '') + `${fmt(s.ppu, s.ppu < 1 ? 4 : 2)} px/µm · ${s.mode}${s.gpu ? ' · GPU ' + fmt(s.gpu / 1e6, 0) + ' MB' : ''}`),
      onPick: async (hit) => {
        if (hit.shape && hit.shape.net > 0) {
          const pk = hit.item.pack, [nn] = await eng.lookup(pk, 'net', [hit.shape.net]);
          eng.highlight(pk, hit.shape.net); S.selfPick = true;
          store.go({ node: hit.inst ? hit.inst.node : store.get().sel.node, inst: hit.inst ? hit.inst.name : null, net: nn ? nn.name : '#' + hit.shape.net });
        } else if (hit.inst) { eng.highlight(null, 0); S.selfPick = true; store.go({ node: hit.inst.node, inst: hit.inst.name, net: null }); }
        else { eng.highlight(null, 0); if (store.get().sel.net) store.go({ net: null }); }
      },
    });
    wrap.append(head);
    await eng.start(); if (window.otx) window.otx.eng = eng;

    const fitBtn = h('button.btn', { type: 'button', title: 'Fit the die (F)', testid: 'layout-fit', onclick: () => eng.fit() }, icon('fit'), 'Fit');
    const selBtn = h('button.btn', { type: 'button', title: 'Zoom to the selected placement', testid: 'layout-zoomsel', onclick: () => zoomSel(true) }, 'To selection');
    const unsBtn = h('button.btn', { type: 'button', 'aria-pressed': 'false', title: 'Also draw the newest as-routed pack of types that are not signed off (labelled UNSIGNED)', testid: 'layout-unsigned',
      onclick: () => ctx.setParams({ unsigned: S.unsigned ? null : '1' }, { notify: true }) }, 'Unsigned');
    const rulerBtn = h('button.btn', { type: 'button', 'aria-pressed': 'false', title: 'Ruler (R): click two points', testid: 'layout-ruler', onclick: () => setRuler(!eng.rulerMode) }, icon('ruler'), 'Ruler');
    const clearBtn = h('button.btn.ghost', { type: 'button', title: 'Clear rulers and the net highlight (Esc)', testid: 'layout-clear', onclick: clearAll }, 'Clear');
    tools.append(fitBtn, selBtn, unsBtn, rulerBtn, clearBtn);
    function setRuler(on) { eng.setRuler(on); rulerBtn.setAttribute('aria-pressed', String(on)); }
    function clearAll() { eng.clearMarks(); setRuler(false); eng.highlight(null, 0); if (store.get().sel.net) store.go({ net: null }); }
    const onKey = (e) => {
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 'f' || e.key === 'F') eng.fit(); else if (e.key === 'r' || e.key === 'R') setRuler(!eng.rulerMode); else if (e.key === 'Escape') clearAll();
    };
    document.addEventListener('keydown', onKey);
    ctx.inspector.setTabs([{ id: 'layers', label: 'Layers', render: layersTab(() => eng, { onChange: () => ctx.setParams({ hide: eng.hiddenLayers().join('.') || null }) }) }]);

    function build() {
      const m = S.man, insts = [], items = [];
      m.instances.forEach((r, ii) => {
        const p = r.pack ? m.packs[r.pack] : null, drawn = !!(r.ok && p && (p.state === 'signed' || S.unsigned));
        const what = drawn ? (r.state === 'signed' ? 'routed wires' : 'UNSIGNED, as routed') : r.ok ? 'outline only (not signed off)' : (r.why || 'no routed pack');
        insts.push({ ii, name: r.name, node: r.node, state: r.state, orient: r.orient, bb: [r.x / 1000, r.y / 1000, (r.x + r.w) / 1000, (r.y + r.h) / 1000], col: hexRgb(stateColor(r.state)), drawn,
          label: r.name + (drawn && r.state !== 'signed' ? '  UNSIGNED' : ''), sub: `${shortName(r.node)} · ${STATE_LABEL[r.state] || r.state} · ${r.orient} · ${what}` });
        const xf = SGN[r.orient] ? xfOf(r.orient, r.x, r.y, r.w, r.h) : null;
        if (!drawn) {   // no type pack to draw: its hard cores still have packs; draw them at their PLAN placement
          const t = S.D.nodes[r.node]; let nc = 0;
          if (xf && t) (t.plan.hard_cores || []).forEach((hc, j) => {
            const cp = m.packs[hc[1]]; if (!cp || !SGN[hc[7]] || !(cp.state === 'signed' || S.unsigned)) return;
            if (Math.abs((cp.die[2] - cp.die[0]) - hc[5] * 1000) > 2 || Math.abs((cp.die[3] - cp.die[1]) - hc[6] * 1000) > 2) return;   // the pack is not this plan outline
            const cx = xfChild(xf, hc[7], hc[3], hc[4], hc[5], hc[6]);
            items.push({ key: 'i' + ii + 'p' + j, ii, pack: hc[1], level: 'core', xf: cx, bb: xfBox(cx, ...cp.die), name: r.name, cname: hc[0], state: cp.state, plan: true }); nc++;
          });
          if (nc) { const q = insts[insts.length - 1]; q.cores = nc; q.sub += ` · ${nc} hard cores drawn at plan placement`; }
          return;
        }
        items.push({ key: 'i' + ii, ii, pack: r.pack, level: 'type', xf, bb: xfBox(xf, ...p.die), name: r.name, state: p.state });
        p.cores.forEach((c, j) => { if (!c.core || !m.packs[c.core]) return; const cx = xfCompose(xf, c.origin, c.orient); items.push({ key: 'i' + ii + 'c' + j, ii, pack: c.core, level: 'core', xf: cx, bb: xfBox(cx, ...m.packs[c.core].die), name: r.name, cname: c.name, state: m.packs[c.core].state }); });
      });
      S.insts = insts; S.items = items; eng.instVer = (eng.instVer || 0) + 1;
      return { outline: [0, 0, m.outline[0] / 1000, m.outline[1] / 1000], insts, items, packs: m.packs };
    }
    function paintHead() {
      const s = S.man.summary, drawn = S.insts.filter((r) => r.drawn).length;
      const st = store.get(), sel = levelOf(st.sel.node) === 'type' ? S.insts.filter((r) => r.node === st.sel.node) : [];
      const pc = S.items.filter((i) => i.plan).length;
      clear(head).append(h('b', `${drawn} of ${s.partitions} placements drawn with their routed wires`), ` (${s.signed_with_pack} of ${s.signed_instances} signed placements have a pack)`, pc ? h('span', ' · ', h('b', `${fmtCount(pc)} hard cores`), ' of the other placements drawn at plan placement') : '', ` · ${Object.keys(S.man.packs).length} packs, ${fmtBytes(s.pack_bytes)}`,
        h('div.muted', 'Die-top nets, the M8/M9 power grid and clock trunks are not routed yet and are not drawn.'));
      if (sel.length && !sel.some((r) => r.drawn)) {
        const r = S.man.instances[sel[0].ii], canShow = r.ok && !S.unsigned;
        head.append(h('div', { style: { marginTop: '4px', color: 'var(--ink)' }, dataset: { testid: 'layout-hint' } }, h('b', shortName(st.sel.node)), canShow ? (sel[0].cores ? ' is not signed off: its signed hard cores are drawn at their plan placement.' : ' is not signed off, so only its outline is drawn.') + ' The Unsigned switch draws its newest as-routed pack.' : r.ok ? '' : ` has no usable routed pack (${r.why || 'none cut'}).`));
      }
    }
    function rings(st) {
      const { node, inst } = st.sel, lvl = levelOf(node), out = [];
      if (lvl === 'type') for (const r of S.insts) if (r.node === node) out.push({ bb: r.bb, strong: r.name === inst });
      if (lvl === 'core') for (const it of S.items) if (it.level === 'core' && it.pack === node) out.push({ bb: it.bb, strong: false });
      eng.selBox = out.length ? out : null; eng.requestUpdate();
      selBtn.disabled = !out.length;
      return out;
    }
    function zoomSel(force) {
      const st = store.get(), out = rings(st); if (!out.length) return;
      const strong = out.filter((q) => q.strong), set = strong.length ? strong : out.length === 1 || force ? out : null;
      if (!set) return;
      const bb = set.reduce((a, q) => [Math.min(a[0], q.bb[0]), Math.min(a[1], q.bb[1]), Math.max(a[2], q.bb[2]), Math.max(a[3], q.bb[3])], [Infinity, Infinity, -Infinity, -Infinity]);
      eng.zoomTo(bb, 0.8);
    }
    return {
      async update(st, prev) {
        const { die, node, inst, net } = st.sel, my = ++S.seq;
        const uns = st.params.unsigned === '1';
        let fresh = false;
        if (die !== S.die) {
          const busy = showBusy(wrap, 'Composing the die…');
          try { [S.man, S.D] = await Promise.all([api.compose(die), api.die(die)]); } catch (e) { busy.remove(); throw e; }
          busy.remove(); if (my !== S.seq) return;
          S.die = die; S.unsigned = uns; fresh = true;
          eng.setScene(build());
          if (st.params.hide) eng.setHidden(st.params.hide.split('.'));
          const cam = (st.params.cam || '').split(',').map(Number);
          if (cam.length === 3 && cam.every(Number.isFinite)) eng.setCam(cam[0], cam[1], cam[2]);
          else if (inst || levelOf(node) === 'type') { rings(st); zoomSel(false); }
        } else if (uns !== S.unsigned) { S.unsigned = uns; const sc = build(); eng.insts = sc.insts; eng.setItems(sc.items); }
        unsBtn.setAttribute('aria-pressed', String(S.unsigned));
        paintHead(); rings(st);
        if (!fresh && prev && (prev.sel.node !== node || prev.sel.inst !== inst) && !S.selfPick) zoomSel(false);
        S.selfPick = false;
        if (!net) eng.highlight(null, 0);
        ctx.setScope(`${dieShort(die)} · routed die map · plan ${S.man.plan.sha || ''}`);
      },
      destroy() { document.removeEventListener('keydown', onKey); eng.destroy(); },
    };
  },
};

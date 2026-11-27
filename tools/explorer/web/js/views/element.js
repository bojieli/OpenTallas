// Element: one type or core in full.  Routed layout of its pack (one-pack scene on the shared engine) with timing
// paths, clock tree, congestion, macros and net / instance search; or its plan contents when no pack exists.
import { h, clear, fmt, fmtCount, fmtBytes, icon, cssv, hexRgb, levelOf, dieShort, shortName, debounce, stateCls, STATE_LABEL, STATES } from '../core/dom.js';
import { LayoutEngine, packFromStore, xfCompose, xfChild, xfBox, XF0, SGN } from '../engine/layout-engine.js';
import { PlanCanvas, drawTypePlan, coreSize } from '../engine/plan-canvas.js';
import { layersTab } from './layers-panel.js';
import { colourSlots, legendHud, macrosTab } from './macros.js';
import { showBusy } from '../shell/shell.js';

const ramp = (prefix, n, t) => { t = Math.max(0, Math.min(1, t)); const k = t * (n - 1), i = Math.min(n - 2, Math.floor(k)), f = k - i, a = hexRgb(cssv(prefix + (i + 1))), b = hexRgb(cssv(prefix + (i + 2))); return [0, 1, 2].map((j) => Math.round(a[j] + (b[j] - a[j]) * f)); };
const rectPoly = (q) => [[q[0], q[1]], [q[2], q[1]], [q[2], q[3]], [q[0], q[3]]];
function decodeCong(buf) {
  const u8 = new Uint8Array(buf), dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const n = dv.getUint16(4, true), gx = dv.getUint16(6, true), gy = dv.getUint16(8, true), bin = dv.getUint32(10, true);
  const layers = Array.from(u8.subarray(14, 14 + n)), planes = []; let p = 14 + n;
  for (let k = 0; k < n; k++) { planes.push(u8.subarray(p, p + gx * gy)); p += gx * gy; }
  return { layers, gx, gy, bin, planes };
}

export default {
  id: 'element', title: 'Element', icon: 'element', datasets: ['design_index', 'store'],
  async mount(ctx) {
    const { host, tools, store, api } = ctx;
    const S = { node: null, R: null, mode: null, job: null, info: null, P: null, T: null, ov: { macros: true }, corner: 'setup', psel: 0, congLayer: 'max', seq: 0, eng: null, pc: null, hlName: null };
    const geo = h('div.canvas-host', { hidden: true }), planHost = h('div.canvas-host', { hidden: true }), msg = h('div.stage-body.scroll', { hidden: true, style: { position: 'absolute', inset: '0' } });
    const planTip = h('div.tip', { hidden: true }); planHost.append(planTip);
    host.append(geo, planHost, msg);

    /* ---------------- toolbar */
    const modeSeg = h('div.seg', { role: 'group', 'aria-label': 'View' }, h('button', { type: 'button', dataset: { mode: 'routed', testid: 'el-mode-routed' } }, 'Routed'), h('button', { type: 'button', dataset: { mode: 'plan', testid: 'el-mode-plan' } }, 'Plan'));
    modeSeg.querySelectorAll('button').forEach((b) => { b.onclick = () => ctx.setParams({ mode: b.dataset.mode, cam: null }, { notify: true }); });
    const jobSel = h('select.field', { hidden: true, 'aria-label': 'Closure', title: 'Closure (older packs of this design)', testid: 'el-job', onchange: (e) => ctx.setParams({ job: e.target.value === S.info.latest ? null : e.target.value, cam: null }, { notify: true }) });
    const q = h('input.field', { type: 'search', placeholder: 'Find net or instance', 'aria-label': 'Find a net or an instance in this design', style: { width: '190px' }, spellcheck: false, testid: 'el-search' });
    const qres = h('div.results', { hidden: true, style: { right: 'auto', left: '0', width: '460px' }, testid: 'el-search-results' });
    const qbox = h('div', { style: { position: 'relative', flex: 'none' } }, q, qres);
    const fitBtn = h('button.btn', { type: 'button', title: 'Fit (F)', testid: 'el-fit', onclick: () => (S.mode === 'routed' ? S.eng && S.eng.scene && S.eng.fit() : S.pc && S.pc.fit()) }, icon('fit'), 'Fit');
    const rulerBtn = h('button.btn', { type: 'button', 'aria-pressed': 'false', title: 'Ruler (R): click two points', testid: 'el-ruler', onclick: () => setRuler(!(S.eng && S.eng.rulerMode)) }, icon('ruler'), 'Ruler');
    const clearBtn = h('button.btn.ghost', { type: 'button', title: 'Clear rulers and the net highlight (Esc)', testid: 'el-clear', onclick: clearAll }, 'Clear');
    const labBtn = h('button.btn', { type: 'button', 'aria-pressed': 'true', title: 'Macro name labels on the canvas', testid: 'el-labels', onclick: () => { if (!S.eng) return; S.eng.show.macroLabels = !S.eng.show.macroLabels; labBtn.setAttribute('aria-pressed', String(S.eng.show.macroLabels)); ctx.setParams({ labels: S.eng.show.macroLabels ? null : '0' }); S.eng.requestUpdate(); } }, 'Labels');
    const macroHud = h('div.hud.tl.act', { hidden: true, testid: 'macro-legend', style: { whiteSpace: 'normal', right: '204px' } }); geo.append(macroHud);
    const unsTag = h('span.uns-tag', { hidden: true, testid: 'el-unsigned', title: 'This pack was cut from a build that is not signed off (a wave run, possibly before routing). It is shown for inspection only and is not part of the signed count.' });
    tools.append(modeSeg, jobSel, unsTag, qbox, fitBtn, labBtn, rulerBtn, clearBtn);
    S.macros = []; S.masters = [];
    const selectMacro = (key, zoom) => { S.selfMacro = !zoom; store.go({ inst: key }); if (zoom) { const m = S.macros.find((x) => x.key === key); if (m && S.eng) S.eng.zoomTo(m.bb, 0.45); } };
    const onHoverInst = (e) => { if (S.eng) S.eng.hoverMark(e.detail || null); }; window.addEventListener('otx:hover-inst', onHoverInst);
    /** macros of the open design: from the pack header (exact placement) or, without a pack, from the plan */
    function buildMacros(n, P, comp) {
      const plan = (n.plan && n.plan.hard_cores) || [], out = [];
      const core = (id) => (id && S.R.children[id]) || null;
      if (P) {
        const used = new Set();
        P.H.macros.forEach((m) => {
          const bb = m.bbox.map((v) => v / 1000), cx = (bb[0] + bb[2]) / 2, cy = (bb[1] + bb[3]) / 2;
          let best = null, bd = 2.5;   // the plan instance at this place (the routed DB uses flattened names)
          plan.forEach((c, i) => { if (used.has(i)) return; const [w, hh] = coreSize(c), d = Math.hypot(c[3] + w / 2 - cx, c[4] + hh / 2 - cy); if (d < bd && Math.abs(w - (bb[2] - bb[0])) < 1 && Math.abs(hh - (bb[3] - bb[1])) < 1) { bd = d; best = i; } });
          const pc = best != null ? plan[best] : (plan.find((c) => c[0] === m.name) || null); if (best != null) used.add(best);
          const cn = pc ? core(pc[1]) : macroCore(m);
          out.push({ key: pc ? pc[0] : m.name, packName: m.name, master: pc ? pc[2] : m.master, coreId: cn ? cn.id : null, state: cn ? cn.status.state : null, bb, orient: m.orient, where: 'exact, from the routed database of this partition type' });
        });
      } else plan.forEach((c) => { const [w, hh] = coreSize(c), cn = core(c[1]); out.push({ key: c[0], master: c[2], coreId: cn ? cn.id : null, state: cn ? cn.status.state : null, bb: [c[3], c[4], c[3] + w, c[4] + hh], orient: c[7], where: 'plan placement (this partition type has no routed database yet)' }); });
      S.macros = out; S.masters = colourSlots(out);
      S.eng.setMarks(out.map((m) => ({ key: m.key, bb: m.bb, label: m.key, sub: shortName(m.master), ci: m.ci,
        tip: [`master ${m.master}`, `${fmt(m.bb[2] - m.bb[0], 2)} × ${fmt(m.bb[3] - m.bb[1], 2)} µm · ${m.orient}`, m.coreId ? `hard core · ${STATE_LABEL[m.state] || m.state}` : 'generated memory macro (no design of its own)', 'click to select'] })));
      legendHud(macroHud, S.masters, 'Macros');
    }
    const pinsOf = (master) => { const H = S.P && S.P.H; if (!H) return null; const mm = H.masters.find((x) => x.name === master && x.block) || H.masters.find((x) => x.block && (x.name.includes(master) || master.includes(x.name))); return mm ? mm.pins.map((q) => q.name) : null; };
    const macroTab = (el) => macrosTab(el, { macros: S.macros, masters: S.masters, sel: store.get().sel.inst, store, hover: (k) => S.eng && S.eng.hoverMark(k), select: selectMacro, pinsOf });
    function setRuler(on) { if (!S.eng) return; S.eng.setRuler(on); rulerBtn.setAttribute('aria-pressed', String(on)); }
    function clearAll() { if (S.eng) { S.eng.clearMarks(); setRuler(false); S.eng.highlight(null, 0); } S.hlName = null; if (store.get().sel.net) store.go({ net: null }); }
    const onKey = (e) => {
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 'f' || e.key === 'F') fitBtn.click(); else if ((e.key === 'r' || e.key === 'R') && S.mode === 'routed') setRuler(!S.eng.rulerMode); else if (e.key === 'Escape') clearAll();
    };
    document.addEventListener('keydown', onKey);

    /* ---------------- pack search */
    let hits = [];
    const runSearch = debounce(async () => {
      const s = q.value.trim(); if (s.length < 2 || !S.info || S.info.coresOnly) { qres.hidden = true; return; }
      let out = []; try { out = (await api.packSearch(S.node, s)).results || []; } catch (e) { out = []; }
      hits = out; clear(qres);
      if (!out.length) qres.append(h('div.none', `No net or instance matches “${s}” in this design.`));
      out.forEach((o, i) => qres.append(h('button', { type: 'button', dataset: { i }, onclick: () => pickHit(o) }, h('span.kind', o.k), h('span.nm', o.name, o.sig && o.sig !== 'SIGNAL' ? h('small', o.sig) : null), h('span'))));
      qres.hidden = false;
    }, 200);
    function pickHit(o) {
      qres.hidden = true;
      const bb = o.bbox && o.bbox[2] > o.bbox[0] ? o.bbox.map((v) => v / 1000) : null;
      if (o.k === 'net') { S.eng.names.net.set(S.node + '|' + o.id, o); S.eng.highlight(S.node, o.id); S.hlName = o.name; if (bb) S.eng.zoomTo(bb, 0.7); store.go({ net: o.name }); }
      else if (bb) { S.eng.flash = bb; S.eng.zoomTo(bb, 0.25); }
    }
    q.addEventListener('input', runSearch);
    q.addEventListener('keydown', (e) => { if (e.key === 'Escape') { qres.hidden = true; q.blur(); } else if (e.key === 'Enter' && hits[0]) pickHit(hits[0]); });
    const offSearch = (e) => { if (!qbox.contains(e.target)) qres.hidden = true; };
    document.addEventListener('pointerdown', offSearch);

    /* ---------------- engine (created on first routed view) */
    async function engine() {
      if (S.eng) return S.eng;
      const eng = new LayoutEngine(geo, {
        tipExtra: (hit) => hit.item && hit.item.level === 'core' ? h('div', h('b', hit.item.cname), h('div.m', `hard core ${shortName(hit.item.pack)}${hit.item.plan ? ' · at plan placement' : ''}${hit.shape ? '' : ' · click to open'}`)) : null,
        onView: debounce((c) => { if (S.mode === 'routed') ctx.setParams({ cam: [c.x.toFixed(3), c.y.toFixed(3), c.z.toFixed(2)].join(',') }); }, 300),
        onStats: (s) => ctx.setReadout((s.mouse ? `x ${fmt(s.mouse[0], 3)}  y ${fmt(s.mouse[1], 3)} µm   ` : '') + `${fmt(s.ppu, s.ppu < 1 ? 4 : 2)} px/µm · ${s.mode}${s.gpu ? ' · GPU ' + fmt(s.gpu / 1e6, 0) + ' MB' : ''}`),
        onPick: async (hit) => {
          if (hit.shape && hit.shape.net > 0) {
            const pk = hit.item.pack, [nn] = await eng.lookup(pk, 'net', [hit.shape.net]); eng.highlight(pk, hit.shape.net);
            S.hlName = pk === S.node ? (nn ? nn.name : '#' + hit.shape.net) : null; store.go({ net: S.hlName });
          } else if (hit.mark) selectMacro(hit.mark.key, false);
          else { eng.highlight(null, 0); S.hlName = null; if (store.get().sel.net) store.go({ net: null }); }
        },
        overlays, overlayTip, overlayClick,
      });
      eng.show.plan = false; eng.show.labels = false; eng.show.cores = false;
      await eng.start(); S.eng = eng; if (window.otx) window.otx.eng = eng; return eng;
    }
    function overlays(D, { C }) {
      const L = [], H = S.P && S.P.H; if (!H) return L;
      const canvas = hexRgb(cssv('--canvas'));
      if (S.ov.cong && S.cong) {
        const c = S.cong, key = 'cong:' + S.congLayer + ':' + cssv('--canvas');
        if (!S.congIm || S.congIm.key !== key) {
          const n = c.gx * c.gy, rgba = new Uint8ClampedArray(n * 4), sel = S.congLayer === 'max' ? c.planes.map((_, i) => i) : [c.layers.indexOf(+S.congLayer)];
          for (let p = 0; p < n; p++) { let v = 0; for (const s of sel) if (s >= 0) v = Math.max(v, c.planes[s][p]); if (v < 3) continue;
            const y = c.gy - 1 - Math.floor(p / c.gx), x = p % c.gx, o = (y * c.gx + x) * 4, col = ramp('--heat-', 6, Math.min(1, v / 110)); rgba[o] = col[0]; rgba[o + 1] = col[1]; rgba[o + 2] = col[2]; rgba[o + 3] = 150 + Math.min(105, v); }
          S.congIm = { key, im: new ImageData(rgba, c.gx, c.gy) };
        }
        const d = H.die.map((v) => v / 1000);
        L.push(new D.PolygonLayer({ id: 'congdim', data: [d], getPolygon: rectPoly, getFillColor: [...canvas, 205], stroked: false, coordinateSystem: C }));
        L.push(new D.BitmapLayer({ id: key, image: S.congIm.im, bounds: [d[0], d[1], d[0] + c.gx * c.bin / 1000, d[1] + c.gy * c.bin / 1000], coordinateSystem: C, textureParameters: { [10240]: 9728, [10241]: 9728 }, opacity: 0.88 }));
      }
      if (S.ov.clock && S.clk) {
        const k = S.clk, col = (t) => [...ramp('--arr-', 5, (t - k.lo) / Math.max(1e-6, k.hi - k.lo)), 235], ink = hexRgb(cssv('--ink'));
        L.push(new D.LineLayer({ id: 'clke', data: k.edges, getSourcePosition: (e) => e.a, getTargetPosition: (e) => e.b, getColor: (e) => e.t == null ? [128, 128, 128, 120] : col(e.t), widthUnits: 'pixels', getWidth: (e) => e.leaf ? 0.8 : 1.6, coordinateSystem: C }));
        L.push(new D.ScatterplotLayer({ id: 'clkl', data: k.leaves, getPosition: (l) => l.p, getFillColor: (l) => col(l.t), radiusUnits: 'pixels', getRadius: 1.6, coordinateSystem: C, pickable: true }));
        L.push(new D.ScatterplotLayer({ id: 'clkb', data: k.bufs, getPosition: (l) => l.p, getFillColor: (l) => l.t == null ? [200, 200, 200, 255] : col(l.t), stroked: true, getLineColor: [...ink, 200], lineWidthUnits: 'pixels', getLineWidth: 0.8, radiusUnits: 'pixels', getRadius: 3, coordinateSystem: C, pickable: true }));
      }
      if (S.ov.paths && S.T) {
        const P = paths(), sel = S.psel, pc = hexRgb(cssv(S.corner === 'hold' ? '--hold' : '--path'));
        const data = P.map((p, i) => ({ i, p, path: p.points.filter((x) => x[5] != null).map((x) => [x[5], x[6]]) }));
        L.push(new D.PathLayer({ id: 'paths', data, getPath: (d) => d.path, getColor: (d) => [...pc, d.i === sel ? 255 : 80], widthUnits: 'pixels', getWidth: (d) => d.i === sel ? 3 : 1.2, coordinateSystem: C, pickable: true, updateTriggers: { getColor: [sel, S.corner], getWidth: sel } }));
        const cur = data[sel];
        if (cur) L.push(new D.ScatterplotLayer({ id: 'pathpins', data: cur.p.points.filter((x) => x[5] != null), getPosition: (x) => [x[5], x[6]], getFillColor: (x) => x[4] === 'o' ? [...pc, 255] : [255, 255, 255, 235], getLineColor: [...pc, 255], stroked: true,
          lineWidthUnits: 'pixels', getLineWidth: 1.5, radiusUnits: 'pixels', getRadius: 3.5, coordinateSystem: C, pickable: true }));
      }
      if (S.ov.lint && S.lint && (S.lint.findings || []).length) {
        const bad = hexRgb(cssv('--bad')), warn = hexRgb(cssv('--warn')), sh = [];
        for (const f of S.lint.findings) for (const s of f.shapes || []) sh.push({ f, s });
        L.push(new D.PolygonLayer({ id: 'lints', data: sh, getPolygon: (d) => rectPoly([d.s[1] / 1000, d.s[2] / 1000, d.s[3] / 1000, d.s[4] / 1000]), getFillColor: (d) => [...(d.f.sev === 'FAIL' ? bad : warn), 60], getLineColor: (d) => [...(d.f.sev === 'FAIL' ? bad : warn), 255], lineWidthUnits: 'pixels', getLineWidth: 2, coordinateSystem: C, pickable: true }));
      }
      return L;
    }
    function overlayTip(info, tip, hostEl) {
      const o = info.object, id = info.layer.id; clear(tip);
      if (id === 'clkl') tip.append(h('b', o.name || 'sink'), h('div.m', `clock arrival TT ${fmt(o.t, 1)} ps`));
      else if (id === 'clkb') tip.append(h('b', o.name || o.m), h('div.m', `${o.m} · level ${o.lvl} · arrival TT ${fmt(o.t, 1)} ps`));
      else if (id === 'paths') tip.append(h('b', `path ${o.i + 1}: slack ${fmt(o.p.slack, 2)} ps`), h('div.m', `${o.p.start} → ${o.p.end}`), h('div.m', 'click to select'));
      else if (id === 'pathpins') tip.append(h('b', o[0]), h('div.m', `${o[3] || ''} · +${fmt(o[2], 2)} ps · arrival ${fmt(o[1], 2)} ps`));
      else if (id === 'lints') tip.append(h('b', `${o.f.sev} · ${o.f.title}`), h('div.m', String(o.f.reason || '').slice(0, 300)));
      else return false;
      tip.hidden = false; const r = hostEl.getBoundingClientRect(); tip.style.left = Math.min(r.width - tip.offsetWidth - 8, info.x + 14) + 'px'; tip.style.top = Math.min(r.height - tip.offsetHeight - 8, info.y + 14) + 'px';
      return true;
    }
    function overlayClick(info) {
      const o = info.object, id = info.layer.id;
      if (id === 'paths') { S.psel = o.i; ctx.setParams({ path: o.i || null }); S.eng.requestUpdate(); refreshTab('timing'); return true; }
      return false;
    }
    function macroCore(m) {
      const hc = (S.R.node.plan && S.R.node.plan.hard_cores) || [];
      let x = hc.find((c) => c[0] === m.name) || hc.find((c) => m.name.endsWith(c[0]) || c[0].endsWith(m.name));
      if (!x) x = hc.find((c) => m.master === c[2]) || hc.find((c) => m.master.includes(c[2]));
      return x ? S.R.children[x[1]] || null : null;
    }
    const paths = () => ((S.corner === 'hold' ? S.T.hold_paths : S.T.setup_paths) || []).slice(0, 40);
    function prepClock() {
      const d = S.T; S.clk = null; if (!d || !d.clock_tt) return;
      const N = d.clock_tt.nodes, Lv = d.clock_tt.leaves, arr = Lv.map((l) => l[3]).filter((v) => v != null).sort((a, b) => a - b);
      const lo = arr.length ? arr[Math.floor(arr.length * 0.01)] : 0, hi = arr.length ? arr[Math.floor(arr.length * 0.99)] : 1, edges = [];
      N.forEach((n) => { if (n[2] >= 0) { const p = N[n[2]]; if (p) edges.push({ a: [p[0], p[1]], b: [n[0], n[1]], t: n[5] }); } });
      Lv.forEach((l) => { const p = N[l[2]]; if (p) edges.push({ a: [p[0], p[1]], b: [l[0], l[1]], t: l[3], leaf: 1 }); });
      S.clk = { lo, hi, edges, min: arr[0], max: arr[arr.length - 1], leaves: Lv.filter((l) => l[3] != null).map((l) => ({ p: [l[0], l[1]], t: l[3], name: l[4] })), bufs: N.map((n) => ({ p: [n[0], n[1]], t: n[5], m: n[4], name: n[6], lvl: n[3] })) };
    }

    /* ---------------- inspector tabs */
    const tabEls = {};
    const refreshTab = (id) => { if (ctx.inspector.current() === id) ctx.inspector.show(id); };
    const saveOv = () => { ctx.setParams({ ov: Object.keys(S.ov).filter((k) => S.ov[k] && k !== 'macros').join('.') || null, corner: S.corner === 'hold' ? 'hold' : null }); if (S.eng) S.eng.requestUpdate(); };
    const sw = (key, label, id) => h('label.chk', h('input', { type: 'checkbox', checked: !!S.ov[key], dataset: { testid: 'el-ov-' + key }, onchange: (e) => { S.ov[key] = e.target.checked; saveOv(); if (key === 'cong' && e.target.checked) loadCong(); refreshTab(id); } }), label);
    function timingTab(el) {
      if (S.mode !== 'routed' || !S.info || S.info.coresOnly) { el.append(h('section.sec', h('p.note', { style: { margin: 0 } }, 'Timing overlays need a routed layout pack of this design. Open one of its hard cores to see that core\'s paths and clock tree.'))); return; }
      const T = S.T;
      if (!T) { el.append(h('section.sec', h('p.note', { style: { margin: 0 } }, S.timingErr || 'This pack carries no timing data (it was cut before the timing export, or the sign-off session was gone).'))); return; }
      const P = T.sta ? paths() : [];
      el.append(h('section.sec', h('h3', 'Worst paths', h('span.n', T.sta ? `${(T.setup_paths || []).length} setup · ${(T.hold_paths || []).length} hold` : 'not re-timed')),
        T.sta ? [h('div', { style: { display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' } }, sw('paths', 'Draw on the layout', 'timing'),
          h('div.seg', { style: { marginLeft: 'auto' } }, ['setup', 'hold'].map((c) => h('button', { type: 'button', 'aria-pressed': String(S.corner === c), dataset: { testid: 'el-corner-' + c }, onclick: () => { S.corner = c; S.psel = 0; saveOv(); refreshTab('timing'); } }, c === 'setup' ? 'Setup (TT)' : 'Hold (FF)')))),
          h('div.list', { testid: 'el-paths' }, P.map((p, i) => h('button.row' + (i === S.psel ? '.on' : ''), { type: 'button', title: `${p.start} → ${p.end}`, onclick: () => selectPath(i) }, h('small.num', { style: { width: '22px' } }, i + 1), h('span.num.' + (p.slack < 0 ? 'neg' : 'pos'), { style: { width: '74px', fontFamily: 'var(--mono)', fontSize: 'var(--fs-s)' } }, fmt(p.slack, 1) + ' ps'), h('span.nm', p.end))))]
          : h('p.note', { style: { margin: 0 } }, 'The sign-off STA session was not available when this pack was cut, so only the clock topology was exported.')),
      h('section.sec', h('h3', 'Clock tree', h('span.n', T.clock_tt ? `${fmtCount(T.clock_tt.leaves.length)} sinks · ${fmt(T.clock_tt.nodes.length)} buffers` : 'none')),
        T.clock_tt ? [sw('clock', 'Draw the tree, coloured by arrival (TT)', 'timing'),
          S.clk ? h('div', { style: { marginTop: '8px' } }, h('div', { style: { height: '8px', borderRadius: '4px', background: 'linear-gradient(90deg, var(--arr-1), var(--arr-2), var(--arr-3), var(--arr-4), var(--arr-5))' } }),
            h('div', { style: { display: 'flex', justifyContent: 'space-between', font: 'var(--fs-xs) var(--mono)', color: 'var(--ink-2)', marginTop: '2px' } }, h('span', fmt(S.clk.lo, 0) + ' ps'), h('span', `spread ${fmt(S.clk.max - S.clk.min, 1)} ps`), h('span', fmt(S.clk.hi, 0) + ' ps'))) : null,
          h('p.note', `Clocks: ${(T.clocks || []).slice(0, 6).join(', ')}${(T.clocks || []).length > 6 ? ` and ${T.clocks.length - 6} more` : ''}.`)] : h('p.note', { style: { margin: 0 } }, 'No clock tree in this pack.')),
      h('section.sec', h('h3', 'Source'), h('p.note', { style: { margin: 0 } }, T.source || 'timing export of the pack')));
    }
    function selectPath(i) {
      S.psel = i; S.ov.paths = true; saveOv(); ctx.setParams({ path: i || null });
      const p = paths()[i], pts = p ? p.points.filter((x) => x[5] != null) : [];
      if (pts.length) { const bb = pts.reduce((a, x) => [Math.min(a[0], x[5]), Math.min(a[1], x[6]), Math.max(a[2], x[5]), Math.max(a[3], x[6])], [Infinity, Infinity, -Infinity, -Infinity]); const pad = Math.max(2, (bb[2] - bb[0]) * 0.15, (bb[3] - bb[1]) * 0.15); S.eng.zoomTo([bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad], 0.85); }
      refreshTab('timing');
    }
    function checksTab(el) {
      if (S.mode !== 'routed' || !S.info || S.info.coresOnly) { el.append(h('section.sec', h('p.note', { style: { margin: 0 } }, 'Checks need a routed layout pack of this design.'))); return; }
      const H = S.P.H, v = S.info.verify || {}, cg = H.congestion;
      el.append(h('section.sec', h('h3', 'Pack against OpenDB', h('span.n', v.verdict || 'not verified')), h('p.note', { style: { margin: '0 0 6px' } }, v.verdict === 'IDENTICAL' ? `Every one of the ${fmtCount(v.shapes)} shapes decoded from the pack matches the routed database, layer by layer.` : 'This pack has no round-trip verdict.'),
        v.layers ? h('table.grid', h('thead', h('tr', h('th', 'Layer'), h('th.r', 'Shapes'), h('th', 'Match'))), h('tbody', v.layers.map((l) => h('tr', { style: { cursor: 'default' } }, h('td.mono', l.layer), h('td.r', fmt(l.decoded)), h('td', l.match ? h('span.pos', 'identical') : h('span.neg', 'differs')))))) : null),
      h('section.sec', h('h3', 'Routing congestion'), cg ? [sw('cong', 'Heat map of signal-track use', 'checks'),
        h('label.chk', 'Layer ', h('select.field', { style: { height: '24px', marginLeft: 'auto' }, dataset: { testid: 'el-cong-layer' }, onchange: (e) => { S.congLayer = e.target.value; S.congIm = null; S.eng.requestUpdate(); } }, h('option', { value: 'max', selected: S.congLayer === 'max' }, 'max over layers'), cg.layers.map((l) => h('option', { value: l.layer, selected: String(S.congLayer) === String(l.layer) }, l.name)))),
        h('table.grid', { style: { marginTop: '6px' } }, h('thead', h('tr', h('th', 'Layer'), h('th.r', 'p50 %'), h('th.r', 'p99 %'), h('th.r', 'max %'), h('th.r', '>100 %'))), h('tbody', cg.layers.map((l) => h('tr', { style: { cursor: 'default' } }, h('td.mono', l.name), h('td.r', fmt(l.p50)), h('td.r', fmt(l.p99)), h('td.r' + (l.max > 100 ? '.neg' : ''), fmt(l.max)), h('td.r', fmt(l.over100)))))),
        h('p.note', cg.basis || '')] : h('p.note', { style: { margin: 0 } }, 'No congestion map in this pack.')),
      h('section.sec', h('h3', 'Hierarchy-contract lint'), lintBody()),
      h('section.sec', h('h3', 'Macros'), h('p.note', { style: { margin: 0 } }, `${H.macros.length} macros in this design: see the Macros tab.`)));
    }
    function lintBody() {
      const ls = S.P.H.lint_summary || {}, L = S.lint;
      if (ls.error || (L && L.error)) return h('div.banner', h('div', h('b', 'Lint did not run for this pack. '), String(ls.error || L.error).slice(0, 200)));
      if (!ls.n) return h('p.note', { style: { margin: 0 } }, 'No findings: the routed abstract passes the hierarchy-contract checks.');
      return [sw('lint', `Draw ${ls.n} finding${ls.n === 1 ? '' : 's'} (${ls.fail || 0} failing)`, 'checks'), L ? h('div.list', (L.findings || []).map((f) => h('button.row', { type: 'button', title: f.reason, onclick: () => { if (f.bbox) S.eng.zoomTo(f.bbox.map((x) => x / 1000), 0.5); } }, h('span.' + (f.sev === 'FAIL' ? 'neg' : 'muted'), f.sev), h('span.nm', f.title), h('small', f.n_shapes + ' shapes')))) : h('p.note', 'Loading findings…')];
    }
    async function loadCong() {
      if (S.cong || !S.info.objects.cong) return;
      try { const r = await fetch(api.storeObject(S.info.objects.cong)); S.cong = decodeCong(await r.arrayBuffer()); S.eng.requestUpdate(); } catch (e) { ctx.toast('The congestion map did not load'); }
    }
    function setTabs() {
      const t = [];
      if (S.mode === 'routed' && S.info) t.push({ id: 'layers', label: 'Layers', render: layersTab(() => S.eng, { onChange: () => ctx.setParams({ hide: S.eng.hiddenLayers().join('.') || null }) }) }, { id: 'macros', label: 'Macros', render: macroTab }, { id: 'timing', label: 'Timing', render: timingTab }, { id: 'checks', label: 'Checks', render: checksTab });
      ctx.inspector.setTabs(t);
    }

    /* ---------------- plan canvas */
    function planCanvas() {
      if (S.pc) return S.pc;
      S.pc = new PlanCanvas(planHost, {
        draw: (g, T) => { if (S.R && S.R.node.plan.outline) drawTypePlan(g, T, S.R.node, S.R.children || {}, { hover: S.hoverCore }); },
        onView: () => { const c = S.pc.cam; if (c) ctx.setReadout(`${fmt(c.k, c.k < 1 ? 4 : 2)} px/µm · plan`); },
        onHover: (wx, wy, mx, my) => {
          const c = wx == null ? null : (S.R.node.plan.hard_cores || []).find((x) => { const [w, hh] = coreSize(x); return wx >= x[3] && wx <= x[3] + w && wy >= x[4] && wy <= x[4] + hh; });
          if (c !== S.hoverCore) { S.hoverCore = c; S.pc.redraw(); }
          if (!c) { planTip.hidden = true; S.pc.cv.style.cursor = ''; return; }
          const cn = S.R.children[c[1]]; clear(planTip).append(h('b', c[0]), h('div.m', c[2]), h('div', cn ? h('span.st.' + stateCls(cn.status.state), h('i.dot'), cn.status.label || cn.status.state) : 'generated memory macro'), cn ? h('div.m', 'click to open this core') : null);
          planTip.hidden = false; S.pc.cv.style.cursor = cn ? 'pointer' : ''; planTip.style.left = (mx + 14) + 'px'; planTip.style.top = (my + 14) + 'px';
        },
        onClick: () => { const c = S.hoverCore; if (c && S.R.children[c[1]]) store.go({ node: c[1] }); },
      });
      return S.pc;
    }
    const onTheme = () => { if (S.pc) S.pc.redraw(); S.congIm = null; }; window.addEventListener('otx:theme', onTheme);

    function show(which) { geo.hidden = which !== 'geo'; planHost.hidden = which !== 'plan'; msg.hidden = which !== 'msg'; }
    async function picker(die) {
      show('msg'); clear(msg); setTabs(); modeSeg.hidden = true; jobSel.hidden = true; unsTag.hidden = true; qbox.hidden = true; fitBtn.hidden = rulerBtn.hidden = clearBtn.hidden = true;
      ctx.setScope(`${dieShort(die)} · pick a partition type or hard core`);
      const D = await api.die(die), all = Object.values(D.nodes).filter((n) => n.layout && n.layout.store);
      all.sort((a, b) => STATES.indexOf(a.status.state) - STATES.indexOf(b.status.state) || a.level.localeCompare(b.level) * -1 || a.name.localeCompare(b.name, 'en', { numeric: true }));
      const row = (n) => h('a.row.' + stateCls(n.status.state), { href: store.href({ node: n.id }) }, h('i.dot'), h('span.nm', n.name), h('small', `${n.level} · ${STATE_LABEL[n.status.state]} · ${fmtCount(n.layout.store.shapes)} shapes`));
      msg.append(h('div.page', { testid: 'element-picker' }, h('h1', `Elements of ${D.die.label}`), h('p.lead', `Pick a partition type or hard core in the navigator, on the plan, or below. ${all.length} of ${Object.keys(D.nodes).length} designs of this die have a routed layout pack; the others open with their plan contents.`),
        h('div.card', { style: { padding: '6px' } }, h('div.list', all.slice(0, 400).map(row)))));
    }

    return {
      async update(st) {
        const { die, node, net } = st.sel, my = ++S.seq;
        if (levelOf(node) === 'die') { S.node = node; S.R = null; S.info = null; return picker(die); }
        modeSeg.hidden = false; fitBtn.hidden = false;
        let R; try { R = await api.node(node); } catch (e) { if (my !== S.seq) return; show('msg'); clear(msg).append(h('div.empty', h('div', h('h3', e.status === 404 ? 'Not in the current plan' : 'Could not load this design'), h('p', e.status === 404 ? `${node} is not a partition type or hard core of any plan of record.` : e.message)))); setTabs(); return; }
        if (my !== S.seq) return;
        const n = R.node, has = !!(n.layout && n.layout.store), hasPlan = !!(n.plan && n.plan.outline);
        let comp = null; try { comp = await api.compose(die); } catch (e) { comp = { packs: {} }; } if (my !== S.seq) return;
        const planCores = hasPlan ? (n.plan.hard_cores || []).filter((c) => comp.packs[c[1]] && SGN[c[7]]) : [], hasCores = !has && planCores.length > 0;
        const mode = st.params.mode === 'plan' && hasPlan ? 'plan' : has || hasCores ? 'routed' : 'plan';
        const nodeChanged = node !== S.node; S.R = R; S.node = node; S.mode = mode;
        modeSeg.querySelectorAll('button').forEach((b) => { b.setAttribute('aria-pressed', String(b.dataset.mode === mode)); if (b.dataset.mode === 'routed') { b.disabled = !(has || hasCores); b.title = has ? 'Routed geometry of the newest closure' : hasCores ? 'No pack for the type itself yet: its hard cores are drawn with their routed wires at their plan placement' : 'No routed layout pack for this design yet'; } if (b.dataset.mode === 'plan') b.disabled = !hasPlan; });
        rulerBtn.hidden = clearBtn.hidden = labBtn.hidden = mode !== 'routed'; qbox.hidden = mode !== 'routed' || !has;
        S.ov = Object.assign({ macros: true }, Object.fromEntries((st.params.ov || '').split('.').filter(Boolean).map((k) => [k, true]))); S.corner = st.params.corner === 'hold' ? 'hold' : 'setup'; S.psel = +st.params.path || 0;
        if (mode === 'plan') {
          show(hasPlan ? 'plan' : 'msg'); jobSel.hidden = true; S.info = null; setTabs(); unsTag.hidden = true;
          if (!hasPlan) { clear(msg).append(h('div.empty', h('div', h('h3', 'Nothing to draw yet'), h('p', 'This design has no routed layout pack and no plan outline. Its state and history are in the inspector.')))); ctx.setScope(shortName(node)); return; }
          const pc = planCanvas(); pc.setWorld(n.plan.outline, !nodeChanged && S.planFor === node); S.planFor = node;
          ctx.setScope(`${shortName(node)} · plan contents${has ? '' : ' · no routed pack yet'}`);
          return;
        }
        show('geo');
        const eng = await engine(); if (my !== S.seq || !eng.deck) return;
        const job = st.params.job || null;
        if (nodeChanged || !S.info || S.info.node !== node || (has && (job || S.info.latest) !== S.info.job)) {
          const busy = showBusy(geo, 'Opening the routed layout…'); busy.classList.add('clear');
          try {
            const info = has ? await packFromStore(node, job) : { node, job: 'plan', latest: 'plan', history: [], objects: {}, coresOnly: true }; if (my !== S.seq) return;
            const P = has ? await eng.addPack(node, info) : null; if (my !== S.seq) return;
            S.info = info; S.P = P; S.T = null; S.clk = null; S.cong = null; S.congIm = null; S.lint = null; S.timingErr = null; S.hlName = null; eng.highlight(null, 0); eng.clearMarks();
            const d = P ? P.H.die.map((v) => v / 1000) : [0, 0, n.plan.outline[0], n.plan.outline[1]];
            const items = P ? [{ key: 'e', pack: node, level: 'type', xf: XF0, bb: d, name: n.name }] : [], packs = P ? { [node]: info } : {};
            const addCore = (key, id, xf, cname, plan) => { const cp = comp.packs[id]; if (!cp) return; packs[id] = cp; items.push({ key, pack: id, level: 'core', xf, bb: xfBox(xf, ...cp.die), name: n.name, cname, plan }); };
            if (P) P.H.macros.forEach((m, j) => { const c = macroCore(m); if (c && SGN[m.orient]) addCore('m' + j, c.id, xfCompose(XF0, m.origin, m.orient), m.name, false); });   // the type's own macros: exact placement from its pack
            else planCores.forEach((c, j) => addCore('p' + j, c[1], xfChild(XF0, c[7], c[3], c[4], c[5], c[6]), c[0], true));
            S.nCores = items.filter((i) => i.level === 'core').length; eng.show.cores = true;
            eng.setScene({ outline: d, items, insts: [], packs }); buildMacros(n, P, comp);
            if (st.params.hide) eng.setHidden(st.params.hide.split('.'));
            const cam = (st.params.cam || '').split(',').map(Number); if (cam.length === 3 && cam.every(Number.isFinite)) eng.setCam(cam[0], cam[1], cam[2]);
            clear(jobSel); for (const j of info.history.slice().reverse()) jobSel.append(h('option', { value: j, selected: j === info.job }, j === info.latest ? `${j} (newest)` : j)); jobSel.hidden = info.history.length < 2; unsTag.hidden = !has || ['signed', 'pending archive'].includes((n.status || {}).state); unsTag.textContent = `Unsigned build view${info.stage ? ' · ' + info.stage : ''} · not counted`;
            const t = has ? ((n.layout.store || {}).timing || {}).object : null;
            if (t && info.job === info.latest) fetch(api.storeObject(t)).then((r) => r.ok ? r.json() : null).then((T) => { if (S.info !== info) return; S.T = T; prepClock(); eng.requestUpdate(); refreshTab('timing'); }).catch(() => { S.timingErr = 'The timing data of this pack did not load.'; });
            if (has && info.objects.lint) fetch(api.storeObject(info.objects.lint)).then((r) => r.ok ? r.json() : null).then((L) => { if (S.info === info) { S.lint = L; refreshTab('checks'); } }).catch(() => {});
            if (S.ov.cong) loadCong();
          } catch (e) { busy.remove(); show('msg'); clear(msg).append(h('div.empty', h('div', h('h3', 'The routed layout could not be opened'), h('p', e.message), hasPlan ? h('button.btn', { type: 'button', onclick: () => ctx.setParams({ mode: 'plan' }, { notify: true }) }, 'Show the plan instead') : null))); setTabs(); return; }
          busy.remove(); setTabs();
        }
        // macro selection lives in the URL (inst=); zoom to it unless the click came from the canvas
        const inst = st.sel.inst, mk = inst && S.macros.find((x) => x.key === inst || x.packName === inst);
        eng.selectMark(mk ? mk.key : null);
        if (st.params.labels === '0') { eng.show.macroLabels = false; labBtn.setAttribute('aria-pressed', 'false'); }
        if (mk && S.lastMacro !== mk.key && !S.selfMacro && !st.params.cam) eng.zoomTo(mk.bb, 0.45);
        if ((mk ? mk.key : null) !== S.lastMacro) { S.lastMacro = mk ? mk.key : null; if (mk) ctx.inspector.show('macros'); else if (ctx.inspector.current() === 'macros') ctx.inspector.show('macros'); }
        S.selfMacro = false;
        if (net && net !== S.hlName) { try { const r = await api.packSearch(node, net, 'net'); const o = (r.results || []).find((x) => x.k === 'net' && x.name === net); if (o && my === S.seq) { eng.names.net.set(node + '|' + o.id, o); eng.highlight(node, o.id); S.hlName = net; } } catch (e) { /* the name stays in the URL */ } }
        if (!net && S.hlName) { eng.highlight(null, 0); S.hlName = null; }
        const s = has ? n.layout.store : null;
        if (!has) ctx.setScope(`${shortName(node)} · no pack of its own yet · ${S.nCores} hard cores with routed wires at plan placement`);
        else ctx.setScope(`${shortName(node)} · ${S.info.job}${S.info.job !== S.info.latest ? ' (older closure)' : ''} · ${S.info.verify && S.info.verify.verdict ? S.info.verify.verdict : s.verify || 'unverified'} · ${fmtCount(s.shapes)} shapes`);
        eng.requestUpdate();
      },
      destroy() { window.removeEventListener('otx:hover-inst', onHoverInst); document.removeEventListener('keydown', onKey); document.removeEventListener('pointerdown', offSearch); window.removeEventListener('otx:theme', onTheme); if (S.eng) S.eng.destroy(); if (S.pc) S.pc.destroy(); },
    };
  },
};

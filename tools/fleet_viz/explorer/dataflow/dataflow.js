// Data-flow view of one token on one die revision: floorplan replay (links active in the current schedule window),
// the whole-die link map with cut congestion, the stage's logical DAG and the worst-links table, all on ONE link model.
//   mountDataflow(el, {data, clock, design, group, onNode})   data = token-path record, clock = token core Clock
import { STATUS, BYPASS_COLOR, DATA_BASE, loadIndex, loadModel, fmtBits, fmtUm, fmtBitUm, widthPx, statusText, linkLabel, incident,
  cutMap, linkCutRatio, cutLabel, tokenMapping, linkActive } from './model.js';
import { Floor, bundleText, strokePx } from './floor.js';
import { LinkTable } from './table.js';
import { mountDag, pairIndex } from './dag.js';

const SLOTS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#36a2a8', '#9085e9', '#e66767', '#7fbf3f', '#c06bd6', '#e0a458'];
const fmtCyc = (c) => Math.round(c).toLocaleString() + ' cyc';
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const H = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k.startsWith('on')) e.addEventListener(k.slice(2), v); else if (v != null && v !== false) e.setAttribute(k, v === true ? '' : v); }
  for (const k of kids.flat()) if (k != null) e.append(k.nodeType ? k : document.createTextNode(String(k)));
  return e;
};

/** default record for a design: the canonical revision when it maps the token about as well as the best one */
export function pickRecord(rows, design, data, models) {
  const mine = rows.filter((r) => (r.token_designs || []).includes(design));
  return mine.find((r) => r.role === 'canonical') || mine[0] || null;
}

export async function mountDataflow(root, opts) {
  const { data, clock, design } = opts;
  root.classList.add('df-root');
  root.replaceChildren(H('div', { class: 'df-loading', role: 'status' }, 'Loading the link model…'));
  const index = await loadIndex(opts.base || DATA_BASE);
  const rows = index.records.filter((r) => (r.token_designs || []).includes(design));
  if (!rows.length) { root.replaceChildren(H('div', { class: 'df-empty' }, `No link model for ${design} yet.`)); return { destroy() {} }; }
  const S = { row: rows.find((r) => r.id === opts.record) || pickRecord(rows, design), mode: data ? 'replay' : 'all', cong: false, man: false,
    trail: true, bypass: false, minBits: 0, sel: null, group: opts.group || null, mult: 1, chosen: !!opts.record, tried: new Set(), note: '' };
  const clsColor = {}; (data?.classes || []).forEach((c, k) => { clsColor[c.id] = SLOTS[k % SLOTS.length]; });

  // ---------------------------------------------------------------------------------------------- DOM
  const dieSel = H('select', { 'aria-label': 'Die revision', class: 'df-die' }, ...rows.map((r) => H('option', { value: r.id, ...(r.id === S.row.id ? { selected: true } : {}) }, r.label)));
  const modeBtns = data ? ['replay', 'all'].map((k) => H('button', { type: 'button', 'aria-pressed': String(S.mode === k), 'data-mode': k }, k === 'replay' ? 'Replay token' : 'All links')) : [];
  const tog = (key, label, title) => H('label', { class: 'df-tog', title }, H('input', { type: 'checkbox', 'data-k': key, ...(S[key] ? { checked: true } : {}) }), ' ' + label);
  const minSel = H('select', { 'aria-label': 'Minimum link width' }, ...[[0, 'all widths'], [8, '≥ 8 bit'], [64, '≥ 64 bit'], [256, '≥ 256 bit'], [1024, '≥ 1 kbit']].map(([v, t]) => H('option', { value: v }, t)));
  const lenSel = H('select', { 'aria-label': 'Minimum link length', title: 'auto: links shorter than the reach are shown as a local density fill while zoomed out' },
    ...[['auto', 'local → density'], ['0', 'all lengths'], ['100', '≥ 100 µm'], ['reach', '≥ reach'], ['2000', '≥ 2 mm']].map(([v, t]) => H('option', { value: v }, t)));
  const wIn = H('input', { type: 'range', min: 0.3, max: 2.5, step: 0.1, value: 0.7, 'aria-label': 'Link width scale', class: 'df-w' });
  const wLab = H('label', { class: 'df-tog', title: 'Stroke width scale (width ∝ log₂ bits, capped)' }, 'width ', wIn);
  const fitB = H('button', { type: 'button', title: 'Fit the die (key 0)' }, 'Fit');
  const top = H('div', { class: 'df-top' }, dieSel, H('div', { class: 'df-seg', role: 'group', 'aria-label': 'View' }, ...modeBtns),
    tog('cong', 'cut congestion', 'Bits crossing each 260 µm cut window ÷ routing tracks; red above the 0.60 limit'),
    tog('man', 'Manhattan', 'Draw links as L-shaped (x then y) routes'), data ? tog('trail', 'trail', 'Fade recently used links') : null,
    tog('bypass', 'bypass only', 'Only links whose flight line crosses unrelated blocks'), minSel, lenSel, wLab, fitB);
  const cov = H('div', { class: 'df-cov' });
  const cmp = H('details', { class: 'df-cmp', ...(rows.some((r) => r.role === 'candidate') ? { open: true } : {}) });
  const strip = H('canvas', { class: 'df-strip', role: 'slider', tabindex: 0, 'aria-label': 'Token stages; click to jump' });
  const stripBox = H('div', { class: 'df-stripbox' }, strip, H('div', { class: 'df-stripcap' }));
  const b = (label, title, fn) => H('button', { type: 'button', title, 'aria-label': title, onclick: fn }, label);
  const playB = b('▶', 'Play / pause', () => clock.toggle());
  const multSel = H('select', { 'aria-label': 'Step size' }, ...[1, 4, 16].map((k) => H('option', { value: k }, `step ${k} window${k > 1 ? 's' : ''}`)));
  const speedSel = H('select', { 'aria-label': 'Replay length' }, ...[6, 12, 24, 60, 120].map((s) => H('option', { value: s, ...(clock && s === clock.seconds ? { selected: true } : {}) }, `${s} s replay`)));
  const slider = H('input', { type: 'range', min: 0, max: 10000, value: 0, 'aria-label': 'Replay position' });
  const tread = H('span', { class: 'df-tread', 'aria-live': 'off' });
  const ctl = data ? H('div', { class: 'df-ctl' }, b('⏮', 'Previous stage', () => stepStage(-1)), b('◀', 'Step back', () => stepWin(-1)), playB,
    b('▶|', 'Step forward', () => stepWin(1)), b('⏭', 'Next stage', () => stepStage(1)), multSel, speedSel, slider, tread) : null;
  const floorEl = H('div', { class: 'df-floorbox' });
  const legend = H('div', { class: 'df-legend' });
  const lod = H('div', { class: 'df-lod', 'aria-live': 'polite' });
  const side = H('aside', { class: 'df-side', 'aria-label': 'Current window and selection' });
  const tipEl = H('div', { class: 'df-tip', role: 'tooltip' });
  const dagEl = H('div', {}); const tableEl = H('div', {});
  const dagP = data ? H('section', { class: 'df-panel' }, H('h3', {}, 'Logical flow of the current stage'), dagEl) : null;
  const tableP = H('section', { class: 'df-panel' }, H('h3', {}, 'Worst links'), tableEl);
  const prov = H('details', { class: 'df-prov' });
  root.replaceChildren(top, cov, cmp, ...(data ? [stripBox, ctl] : []), H('div', { class: 'df-main' }, H('div', { class: 'df-floorwrap' }, floorEl, legend, lod), side),
    ...(dagP ? [dagP] : []), tableP, prov, tipEl);

  let lodText = '';
  const floor = new Floor(floorEl, { onPick: pick, onHover: hover, onPaint: (f) => {
    const n = f.visibleCount || 0, loc = f.localCount || 0;
    const t = `${n.toLocaleString()} link${n === 1 ? '' : 's'} in view · ${f.lod === 'bundled' ? `${(f.bundleCount || 0).toLocaleString()} strokes (parallel hops merged)` : 'each link along its hops'}${loc ? ` · ${loc.toLocaleString()} local as density` : ''}`;
    if (t !== lodText) { lodText = t; lod.textContent = t; } } });
  const table = new LinkTable(tableEl, { onSelect: (i) => selectLink(i, true) });
  const dag = data ? mountDag(dagEl, { colorOf: (c) => clsColor[c] || '#8a97b8', onEdge: (e) => { if (clock) clock.pause(); select({ kind: 'dag', ids: e.ids, label: e.label, text: e.text }, true); },
    onNode: (n) => { if (clock) { clock.pause(); clock.seek(Math.max(clock.t0, Math.min(clock.t1, n.start))); } opts.onNode && opts.onNode(n); } }) : null;

  let m = null, map = null, cmAll = null, lcut = null, win = null, wholeWin = null, cur = -1, activeCache = new Map(), stageId = null;

  // ---------------------------------------------------------------------------------------------- loading
  async function load(row) {
    S.row = row; floorEl.classList.add('busy'); side.replaceChildren(H('div', { class: 'df-loading' }, `Loading ${row.label}…`));
    m = await loadModel(row, opts.base || DATA_BASE);
    if (S.row !== row) return;
    floorEl.classList.remove('busy');
    map = data ? tokenMapping(m, data) : null;
    if (data && !S.chosen && map.mappedLinks === 0) {   // canonical revision carries none of this token's links: use the next one
      const alt = rows.find((r) => r !== row && !S.tried.has(r.id));
      S.tried.add(row.id);
      if (alt) { S.note = `${row.label}: no link joins two blocks the token's operators map to; showing ${alt.label}.`; dieSel.value = alt.id; return load(alt); }
    }
    cmAll = cutMap(m); lcut = linkCutRatio(m, cmAll); activeCache = new Map(); wholeWin = null; win = null; cur = -1;
    floor.setModel(m); table.setModel(m, lcut);
    renderProv(); renderLegend(); renderCoverage();
    if (data) { computeWindows(); onTime(clock.t, true); } else { floor.set({ mode: 'all', cut: S.cong ? cmAll : null }); renderSide(); }
  }

  function renderCompare() {
    const num = (v, f) => v == null ? H('span', { class: 'dim' }, 'n/a') : f(v);
    const gb = (v) => fmtBitUm(v), bits = (v) => fmtBits(v);
    const head = ['revision / candidate', 'Σ width·length', 'Σ bit·µm (hops)', 'Σ traffic·length', 'over-reach bits', 'relay bit·stages', 'needed relay bit·stages ≥', 'worst cut'];
    const body = rows.map((r) => {
      const x = r.coverage?.metrics || {};
      const tr = H('tr', { tabindex: 0, 'aria-selected': String(r.id === S.row.id), onclick: () => { dieSel.value = r.id; dieSel.dispatchEvent(new Event('change')); },
        onkeydown: (e) => { if (e.key === 'Enter') { dieSel.value = r.id; dieSel.dispatchEvent(new Event('change')); } } },
        H('td', { title: r.scope || '' }, r.label, H('span', { class: 'dim' }, ` · ${r.role === 'candidate' ? `candidate of ${r.candidate?.of} (${r.candidate?.agent || '?'})` : r.role}`)),
        H('td', {}, num(x.sum_width_length_bit_um, gb)), H('td', {}, num(x.sum_bit_um_hops, gb)), H('td', {}, num(x.sum_traffic_length, (v) => fmtBitUm(v).replace('bit·µm', 'bit/token·µm'))),
        H('td', {}, num(x.over_reach_bits, bits)), H('td', {}, num(x.relay_bit_stages, (v) => v.toLocaleString())), H('td', {}, num(x.needed_relay_bit_stages_lower_bound, (v) => v.toLocaleString())),
        H('td', { class: x.worst_cut > (0.6) ? 'hot' : '' }, num(x.worst_cut, (v) => `${v.toFixed(2)} (${x.cut_windows_over_limit} > 0.6)`)));
      return tr;
    });
    cmp.replaceChildren(H('summary', {}, `Revisions and floorplan candidates (${rows.length}) · same metrics, click to switch`),
      H('div', { class: 'df-cmpscroll' }, H('table', {}, H('thead', {}, H('tr', {}, ...head.map((x) => H('th', {}, x)))), H('tbody', {}, ...body))),
      H('div', { class: 'df-kv dim' }, 'Σ width·length = bits × longest driver→sink length; traffic·length needs per-link traffic (t) from the source, else n/a; relay bit·stages only where registers are placed; cut = L-route per hop in 260 µm windows (limit 0.60). Pin-less records measure to block outlines (lower bounds).'));
  }

  function renderCoverage() {
    renderCompare();
    const c = m.rec.coverage;
    const parts = [`${c.links.toLocaleString()} links · ${c.blocks.toLocaleString()} blocks · ${c.pin_ends ? 'pin centroids' : 'block outlines (pins not published)'}${c.unplaced ? ` · ${c.unplaced} unplaced` : ''}`,
      `cut max ${cmAll.max.toFixed(2)} (${cmAll.over} window${cmAll.over === 1 ? '' : 's'} > ${cmAll.limit})`];
    if (map) parts.push(`token mapping: ${(map.coverage * 100).toFixed(1)} % of operator cycles land on blocks of this die${map.unmapped.length ? `; not on this die: ${[...new Set(map.unmapped)].join(', ')}` : ''}; ${map.mappedLinks.toLocaleString()} links join mapped blocks`);
    cov.textContent = (S.note ? S.note + ' ' : '') + parts.join(' · ');
  }

  function renderLegend() {
    const sw = (color, dash) => H('i', { style: `border-top:3px ${dash ? 'dashed' : 'solid'} ${color}` });
    legend.replaceChildren(
      ...STATUS.slice(0, 3).map((s, k) => H('span', {}, sw(s.color), k === 0 ? `≤ ${m.reach} µm` : k === 1 ? (m.explicit ? 'relayed' : 'needs relay') : 'hop > reach')),
      H('span', {}, sw('#c3cbe0', true), 'crosses unrelated blocks'),
      H('span', {}, H('i', { style: `border-top:${Math.max(1, strokePx(8, floor.st.wscale)).toFixed(1)}px solid #c3cbe0;width:10px` }), H('i', { style: `border-top:${strokePx(4096, floor.st.wscale).toFixed(1)}px solid #c3cbe0;width:14px` }), 'width ∝ log₂ bits, capped; thick = bundle of N links (hover)'),
      H('span', {}, H('i', { style: 'height:8px;width:10px;background:#7aa7ff80' }), 'local links (density)'),
      ...(S.cong ? [H('span', {}, sw('#ff3b3b'), `cut > ${m.rec.cut.limit}`)] : []));
  }

  function renderProv() {
    const r = m.rec, p = r.provenance;
    prov.replaceChildren(H('summary', {}, `Source: ${r.label}`),
      H('div', { class: 'df-provb' },
        H('div', {}, H('b', {}, 'Scope '), r.scope || 'unknown'),
        H('div', {}, H('b', {}, 'Pins '), r.pins || 'unknown'),
        H('div', {}, H('b', {}, 'Registers '), r.registers || 'unknown'),
        H('div', {}, H('b', {}, 'Direction '), r.direction || 'unknown'),
        H('div', {}, H('b', {}, 'Reach '), `${r.reach_um} µm · ${r.reach_source || ''}`),
        H('div', {}, H('b', {}, 'Cut '), r.cut.source),
        H('div', {}, H('b', {}, 'Bypass '), 'flight-line crossings of blocks that are neither an end of the link nor in an end\'s region/group, nor contain an end'),
        H('div', {}, H('b', {}, 'Activity '), 'a link is lit when operators mapped to its driver block and to one of its sink blocks run in the same window (undirected: two ends). Width is the port width; per-cycle transfer volume is not in these sources.'),
        H('div', {}, H('b', {}, 'Extractor '), `${p.tool} sha256 ${p.tool_sha256.slice(0, 12)} · repo ${String(p.repo_head || '').slice(0, 12)} · ${p.generated}`),
        H('ul', {}, ...p.inputs.map((i) => H('li', {}, `${i.role}: ${i.path} · sha256 ${i.sha256.slice(0, 16)}${i.commit ? ' · commit ' + String(i.commit).slice(0, 12) : ''}`)))));
  }

  // ---------------------------------------------------------------------------------------------- windows
  function windowsFor(t0, t1, n) {
    const W = Math.max(1, (t1 - t0) / n), N = Math.max(1, Math.ceil((t1 - t0) / W)), mask = new Int32Array(N);
    for (const nd of data.nodes) {
      const k = map.nodeKey.get(nd.id); if (k >= 31) continue;
      if (nd.end < t0 || nd.start > t1) continue;
      const a = Math.max(0, Math.floor((nd.start - t0) / W)), z = Math.min(N - 1, Math.floor((Math.max(nd.start, nd.end - 1e-6) - t0) / W));
      for (let w = a; w <= z; w++) mask[w] |= 1 << k;
    }
    return { t0, t1, W, N, mask };
  }
  function computeWindows() { win = windowsFor(clock.t0, clock.t1, 240); }
  function activeFor(mask) {
    let a = activeCache.get(mask);
    if (!a) {
      const out = [];
      for (let i = 0; i < m.nl; i++) if (linkActive(m, map, i, mask)) out.push(i);
      out.sort((x, y) => (m.bitum[y] || 0) - (m.bitum[x] || 0));
      a = { list: Int32Array.from(out), set: null, cut: null, lit: null };
      activeCache.set(mask, a);
    }
    return a;
  }
  function litFor(mask, entry) {
    if (!entry.lit) {
      const groups = new Map();
      map.keys.forEach((k, ki) => {
        if (ki >= 31 || !(mask & (1 << ki))) return;
        const color = (clsColor[k.cls] || '#8a97b8') + 'b0';
        let g = groups.get(color); if (!g) groups.set(color, g = []);
        for (let bk = 0; bk < m.nb; bk++) if (map.bmask[bk] & (1 << ki)) g.push(bk);
      });
      entry.lit = [...groups.entries()];
    }
    return entry.lit;
  }
  const winAt = (t) => Math.max(0, Math.min(win.N - 1, Math.floor((t - win.t0) / win.W)));
  const groupAt = (t) => data.groups.find((g) => g.critical !== false && t >= g.start && t < g.end) || data.groups.find((g) => t >= g.start && t < g.end) || null;

  function onTime(t, force) {
    if (!m || !win) return;
    if (clock.t0 !== win.t0 || clock.t1 !== win.t1) { computeWindows(); force = true; }
    slider.value = String(Math.round((t - clock.t0) / Math.max(1, clock.t1 - clock.t0) * 10000));
    tread.textContent = `${fmtCyc(t)} · ${(t / 1.2e3).toFixed(2)} µs`;
    playB.textContent = clock.playing ? '❚❚' : '▶';
    drawStrip(t);
    const w = winAt(t);
    if (w === cur && !force) return;
    cur = w;
    const g = groupAt(t);
    if (g && g.id !== stageId) { stageId = g.id; if (dag && S.mode === 'replay') dag.render(data, g.id, m, map); }
    if (S.mode !== 'replay') return;
    const mask = win.mask[w], e = activeFor(mask);
    const trail = [];
    if (S.trail) {
      const curSet = e.set ||= new Set(e.list);
      let alpha = 0.42;
      for (let k = 1; k <= 5 && w - k >= 0; k++, alpha *= 0.66) {
        const pm = win.mask[w - k]; if (pm === mask) continue;
        const pe = activeFor(pm); trail.push([Array.from(pe.list).filter((i) => !curSet.has(i)), alpha]);
      }
    }
    if (S.cong && !e.cut) e.cut = cutMap(m, e.list);
    floor.set({ mode: 'replay', active: e.list, trail, lit: litFor(mask, e), cut: S.cong ? e.cut : null, flow: clock.playing });
    table.setActive(e.list);
    if (!S.sel) renderSide();
    else if (S.sel.kind === 'link') renderSel();
  }

  function drawStrip(t) {
    const r = strip.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1), w = Math.max(50, Math.round(r.width)), h = 30;
    if (strip.width !== w * d) { strip.width = w * d; strip.height = h * d; }
    const c = strip.getContext('2d'); c.setTransform(d, 0, 0, d, 0, 0); c.clearRect(0, 0, w, h);
    const T0 = clock.t0, T1 = clock.t1, X = (v) => (v - T0) / Math.max(1, T1 - T0) * w;
    const gs = data.groups.filter((g) => g.end > T0 && g.start < T1 && g.critical !== false);
    gs.forEach((g, k) => {
      const x0 = Math.max(0, X(g.start)), x1 = Math.min(w, X(g.end));
      c.fillStyle = g.id === stageId ? '#1d3a6e' : k % 2 ? '#121a2e' : '#0f1626'; c.fillRect(x0, 0, Math.max(1, x1 - x0), 18);
      c.font = '10px ui-monospace,Menlo,monospace';
      const fit = [g.label, g.label.split(':')[0], g.id].find((s) => c.measureText(s).width < x1 - x0 - 6);
      if (fit) { c.fillStyle = g.id === stageId ? '#e8eefc' : '#7d8aa8'; c.fillText(fit, x0 + 3, 13); }
    });
    // activity density: active links per window
    if (win && S.mode === 'replay') {
      let mx = 1; const counts = new Float32Array(win.N);
      for (let k = 0; k < win.N; k++) { const a = activeCache.get(win.mask[k]); counts[k] = a ? a.list.length : -1; if (counts[k] > mx) mx = counts[k]; }
      c.fillStyle = '#2fb3a8';
      for (let k = 0; k < win.N; k++) if (counts[k] > 0) { const hh = 9 * counts[k] / mx; c.fillRect(X(win.t0 + k * win.W), h - hh, Math.max(1, w / win.N), hh); }
    }
    c.fillStyle = '#5ee7ff'; c.fillRect(Math.round(X(t)) - 1, 0, 2, h);
    const g = groupAt(t);
    stripBox.querySelector('.df-stripcap').textContent = g ? `${g.label} · ${fmtCyc(g.start)}–${fmtCyc(g.end)}` : '';
  }

  function stepWin(k) { clock.pause(); const n = +multSel.value * k; clock.seek(win.t0 + (winAt(clock.t) + n + 0.5) * win.W); }
  function stepStage(k) {
    clock.pause();
    const gs = data.groups.filter((g) => g.critical !== false && g.end > clock.t0 && g.start < clock.t1).sort((a, b) => a.start - b.start);
    const i = gs.findIndex((g) => clock.t >= g.start && clock.t < g.end);
    const nx = gs[Math.max(0, Math.min(gs.length - 1, (i < 0 ? 0 : i) + k))];
    if (nx) clock.seek(Math.max(clock.t0, nx.start + 0.01));
  }

  // ---------------------------------------------------------------------------------------------- side panel
  function linkRow(i, extra) {
    const st = STATUS[m.status[i]];
    return H('button', { type: 'button', class: 'df-lrow', onclick: () => selectLink(i, true), title: m.rec.links[i].i },
      H('i', { style: `background:${st.color}` }), H('span', { class: 'df-ln' }, linkLabel(m, i)),
      H('span', { class: 'df-lv' }, extra ?? `${fmtBits(m.bits[i])} · ${fmtUm(m.len[i])}`));
  }
  function cutBox(cm, title) {
    const bar = H('div', { class: 'df-cutbar' }, H('i', { style: `width:${Math.min(100, cm.max / 1.2 * 100)}%;background:${cm.max > cm.limit ? '#ff3b3b' : cm.max > cm.limit * 0.66 ? '#f2b134' : '#2fb3a8'}` }), H('b', { style: `left:${cm.limit / 1.2 * 100}%` }));
    return H('div', { class: 'df-sec' }, H('h4', {}, title),
      H('div', { class: 'df-kv' }, `worst cut ${cm.max.toFixed(2)} of ${cm.limit} · ${cm.over} window${cm.over === 1 ? '' : 's'} over the limit`), bar,
      ...cm.top.slice(0, 3).map((c) => H('div', { class: 'df-kv dim' }, `${c[0].toFixed(2)} · ${cutLabel(c, cm.Wn)}`)));
  }
  function renderSide() {
    if (!m) return;
    if (S.mode !== 'replay' || !win) {
      const worst = Array.from({ length: m.nl }, (_, i) => i).filter((i) => Number.isFinite(m.bitum[i])).sort((a, b) => m.bitum[b] - m.bitum[a]).slice(0, 8);
      const over = []; const byp = [];
      for (let i = 0; i < m.nl; i++) { if (m.status[i] === 2) over.push(i); if (m.cross[i]) byp.push(i); }
      byp.sort((a, b) => m.cross[b] - m.cross[a]);
      side.replaceChildren(H('div', { class: 'df-sec' }, H('h4', {}, 'Whole die'), H('div', { class: 'df-kv' }, `${m.nl.toLocaleString()} links · ${fmtBits(m.rec.coverage.bits_total)} · ${fmtBitUm(m.rec.coverage.bit_um_total)}`)),
        H('div', { class: 'df-sec' }, H('h4', {}, 'Largest bit·µm'), ...worst.map((i) => linkRow(i, fmtBitUm(m.bitum[i])))),
        H('div', { class: 'df-sec' }, H('h4', {}, `Bypass links (${byp.length})`), ...byp.slice(0, 6).map((i) => linkRow(i, `${m.cross[i]} crossed`))),
        H('div', { class: 'df-sec' }, H('h4', {}, `Hop beyond reach (${over.length})`), ...over.slice(0, 6).map((i) => linkRow(i, fmtUm(m.mh[i])))),
        cutBox(cmAll, 'Cut congestion, all links'));
      return;
    }
    const w = cur, mask = win.mask[w], e = activeFor(mask), t0 = win.t0 + w * win.W, t1 = t0 + win.W;
    const ops = data.nodes.filter((n) => n.start < t1 && n.end > t0).sort((a, b) => b.cycles - a.cycles);
    let bits = 0, bu = 0; const over = [], byp = [];
    for (const i of e.list) { if (Number.isFinite(m.bits[i])) bits += m.bits[i]; if (Number.isFinite(m.bitum[i])) bu += m.bitum[i]; if (m.status[i] === 2) over.push(i); if (m.cross[i]) byp.push(i); }
    if (!e.cut) e.cut = cutMap(m, e.list);
    const g = groupAt(t0);
    side.replaceChildren(
      H('div', { class: 'df-sec' }, H('h4', {}, `Window ${fmtCyc(t0)}–${fmtCyc(t1)}`), H('div', { class: 'df-kv' }, g ? g.label : ''),
        H('div', { class: 'df-ops' }, ...ops.slice(0, 6).map((n) => H('span', { title: n.label }, H('i', { style: `background:${clsColor[n.cls] || '#888'}` }), n.label)), ops.length > 6 ? H('span', { class: 'dim' }, `+${ops.length - 6} more`) : null),
        H('div', { class: 'df-kv' }, `${e.list.length.toLocaleString()} active links · ${fmtBits(bits)} of port width · ${fmtBitUm(bu)}`)),
      H('div', { class: 'df-sec' }, H('h4', {}, 'Top active links by bit·µm'), ...(e.list.length ? Array.from(e.list.slice(0, 7)).map((i) => linkRow(i, fmtBitUm(m.bitum[i]))) : [H('div', { class: 'df-kv dim' }, 'No link joins two blocks that are active in this window.')])),
      ...(over.length || byp.length ? [H('div', { class: 'df-sec warn' }, H('h4', {}, `Flags now: ${over.length} over reach · ${byp.length} bypass`),
        ...over.slice(0, 3).map((i) => linkRow(i, 'hop ' + fmtUm(m.mh[i]))), ...byp.sort((a, b) => m.cross[b] - m.cross[a]).slice(0, 3).map((i) => linkRow(i, `${m.cross[i]} crossed`)))] : []),
      cutBox(e.cut, 'Cut congestion, active links only'));
  }

  function usage(i) {   // every window of the whole token in which link i is active, merged into runs
    wholeWin ||= windowsFor(0, data.totals.cycles, 800);
    const runs = []; let start = -1;
    for (let k = 0; k <= wholeWin.N; k++) {
      const on = k < wholeWin.N && linkActive(m, map, i, wholeWin.mask[k]);
      if (on && start < 0) start = k;
      if (!on && start >= 0) { runs.push([wholeWin.t0 + start * wholeWin.W, wholeWin.t0 + k * wholeWin.W]); start = -1; }
    }
    return runs;
  }

  function renderSel() {
    const s = S.sel; if (!s) return renderSide();
    const close = H('button', { type: 'button', class: 'df-x', 'aria-label': 'Clear selection', onclick: () => select(null) }, '×');
    if (s.kind === 'link') {
      const i = s.i, l = m.rec.links[i], ends = l.e.map((e) => `${e[0] >= 0 ? m.bname[e[0]] : '(unplaced)'}${e[1] ? '.' + e[1] : ''}`);
      const kv = (k, v) => H('div', { class: 'df-kv' }, H('b', {}, k + ' '), v);
      const runs = data && map ? usage(i) : [];
      side.replaceChildren(H('div', { class: 'df-sec sel' }, close, H('h4', {}, l.i),
        kv('class', l.c), kv(m.directed[i] ? 'driver' : 'ends', m.directed[i] ? ends[0] : ends.join(' — ')),
        m.directed[i] ? kv('sinks', ends.slice(1).join(', ')) : null,
        kv('width', fmtBits(m.bits[i])), kv('length', `${fmtUm(m.len[i])}${l.h ? ' along its hops' : ''}`), kv('longest hop', fmtUm(m.mh[i])),
        kv('register stages', m.stages[i] < 0 ? 'unknown in this source' : String(m.stages[i])), kv('bit·µm', fmtBitUm(m.bitum[i])),
        kv('verdict', H('span', { style: `color:${STATUS[m.status[i]].color}` }, statusText(m, i))),
        kv('crosses', m.cross[i] ? `${m.cross[i]} unrelated block${m.cross[i] === 1 ? '' : 's'}: ${l.xb.slice(0, 6).map((b) => m.bname[b]).join(', ')}${m.cross[i] > 6 ? '…' : ''}` : 'no unrelated block'),
        kv('cut', `largest window it crosses: ${lcut[i].toFixed(2)} (limit ${m.rec.cut.limit})`),
        l.n ? kv('source note', l.n) : null),
        data ? H('div', { class: 'df-sec' }, H('h4', {}, runs.length ? `Used in ${runs.length} span${runs.length === 1 ? '' : 's'} of the token` : 'Never active in this token mapping'),
          H('div', { class: 'df-runs' }, ...runs.slice(0, 40).map(([a, z]) => { const g = groupAt(a); return H('button', { type: 'button', onclick: () => { clock.pause(); clock.seek(Math.max(clock.t0, Math.min(clock.t1, a + 0.01))); }, title: g ? g.label : '' }, `${g ? g.label.split(':')[0] + ' · ' : ''}${fmtCyc(a)}`); }),
            runs.length > 40 ? H('span', { class: 'dim' }, `+${runs.length - 40}`) : null),
          runs.some(([a]) => a < clock.t0 || a > clock.t1) ? H('div', { class: 'df-kv dim' }, 'Spans outside the current stage scope are listed; seeking stays within the scope.') : null) : null);
      return;
    }
    if (s.kind === 'block') {
      const bk = s.b, inc = incident(m, bk).slice().sort((a, b2) => (m.bitum[b2] || 0) - (m.bitum[a] || 0));
      const peer = (i) => { const e = m.ends[i].filter((x) => x !== bk); return e.length === 1 ? (e[0] >= 0 ? m.bname[e[0]] : '?') : `${e.length} ends`; };
      const keys = map ? map.keys.filter((k, ki) => ki < 31 && (map.bmask[bk] & (1 << ki))).map((k) => k.cls) : [];
      const tb = H('table', { class: 'df-inc' }, H('thead', {}, H('tr', {}, ...['peer', 'bits', 'length', 'bit·µm', 'stg', 'crossed'].map((x) => H('th', {}, x)))),
        H('tbody', {}, ...inc.slice(0, 60).map((i) => H('tr', { tabindex: 0, onclick: () => selectLink(i, true), onkeydown: (ev) => { if (ev.key === 'Enter') selectLink(i, true); } },
          H('td', {}, H('i', { style: `background:${STATUS[m.status[i]].color}` }), (m.ends[i][0] === bk ? '→ ' : m.directed[i] ? '← ' : '— ') + peer(i)),
          H('td', {}, fmtBits(m.bits[i])), H('td', {}, fmtUm(m.len[i])), H('td', {}, fmtBitUm(m.bitum[i])), H('td', {}, m.stages[i] < 0 ? '?' : m.stages[i]), H('td', {}, m.cross[i] || '')))));
      side.replaceChildren(H('div', { class: 'df-sec sel' }, close, H('h4', {}, m.bname[bk]),
        H('div', { class: 'df-kv' }, `${m.bmaster[bk] || 'master unknown'} · ${m.bkind[bk] || ''}${m.bgroup[bk] ? ' · ' + m.bgroup[bk] : ''}`),
        H('div', { class: 'df-kv' }, `${(m.bw[bk]).toFixed(1)} × ${(m.bh[bk]).toFixed(1)} µm at (${m.bx[bk].toFixed(0)}, ${m.by[bk].toFixed(0)})${keys.length ? ' · token classes: ' + keys.join(', ') : ''}`),
        H('div', { class: 'df-kv' }, `${inc.length} incident link${inc.length === 1 ? '' : 's'}${inc.length > 60 ? ' (60 largest shown)' : ''}`), tb,
        H('a', { href: '/explorer#element=' + encodeURIComponent(m.bmaster[bk] || m.bname[bk]), class: 'df-a' }, 'element card →')));
      return;
    }
    if (s.kind === 'dag' || s.kind === 'bundle') {
      const ids = s.ids || [];
      let bits = 0; for (const i of ids) if (Number.isFinite(m.bits[i])) bits += m.bits[i];
      side.replaceChildren(H('div', { class: 'df-sec sel' }, close, H('h4', {}, s.label),
        H('div', { class: 'df-kv pre' }, s.text || ''),
        H('div', { class: 'df-kv' }, `${ids.length.toLocaleString()} physical link${ids.length === 1 ? '' : 's'} · ${fmtBits(bits)}`),
        ...ids.slice().sort((a, b) => (m.bitum[b] || 0) - (m.bitum[a] || 0)).slice(0, 12).map((i) => linkRow(i))));
    }
  }

  // ---------------------------------------------------------------------------------------------- selection
  function select(s, zoom) {
    S.sel = s;
    let hl = null, sb = -1;
    if (s?.kind === 'link') hl = new Set([s.i]);
    else if (s?.kind === 'block') { hl = new Set(incident(m, s.b)); sb = s.b; }
    else if (s?.ids) hl = new Set(s.ids);
    floor.set({ highlight: hl, selBlock: sb });
    if (s?.kind === 'link') table.select(s.i);
    if (s?.kind === 'dag' || s?.kind === 'bundle') table.restrict(s.ids, s.label); else if (!s) table.restrict(null);
    if (!s && dag) dag.clear();
    if (zoom && hl && hl.size) {
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const i of hl) { const bb = m.bbox; if (!Number.isFinite(bb[i * 4])) continue; x0 = Math.min(x0, bb[i * 4]); y0 = Math.min(y0, bb[i * 4 + 1]); x1 = Math.max(x1, bb[i * 4 + 2]); y1 = Math.max(y1, bb[i * 4 + 3]); }
      if (sb >= 0) { x0 = Math.min(x0, m.bx[sb]); y0 = Math.min(y0, m.by[sb]); x1 = Math.max(x1, m.bx[sb] + m.bw[sb]); y1 = Math.max(y1, m.by[sb] + m.bh[sb]); }
      if (Number.isFinite(x0)) floor.zoomTo(x0, y0, x1, y1);
    }
    renderSel();
  }
  function selectLink(i, zoom) { if (clock) clock.pause(); select({ kind: 'link', i }, zoom); }
  function pick(p) {
    if (!p) return select(null);
    if (clock) clock.pause();
    if (p.link != null) select({ kind: 'link', i: p.link });
    else if (p.block != null) select({ kind: 'block', b: p.block });
    else if (p.bundle) select({ kind: 'bundle', ids: p.bundle.links, label: p.bundle.dens ? 'Local links' : 'Bundled links', text: bundleText(m, p.bundle) + (p.bundle.links.length < p.bundle.n ? ` (first ${p.bundle.links.length} listed)` : '') });
  }
  function hover(p, ev) {
    if (!p || !ev) { tipEl.style.display = 'none'; return; }
    let html = '';
    if (p.link != null) { const i = p.link, e = m.ends[i], ms = (b) => b >= 0 ? `${m.bmaster[b] || m.bname[b]}${m.bkind[b] ? ' [' + m.bkind[b] + ']' : ''}` : '?';
      const sinks = [...new Set(e.slice(1).map(ms))];
      html = `<b>${esc(linkLabel(m, i))}</b><br><span class="dim">${esc(ms(e[0]))} → ${esc(sinks.slice(0, 2).join(', '))}${sinks.length > 2 ? ` +${sinks.length - 2}` : ''}</span><br>${esc(m.rec.links[i].c)} · ${fmtBits(m.bits[i])} · ${fmtUm(m.len[i])}${m.stages[i] >= 0 ? ` · ${m.stages[i]} stages` : ''}<br><span style="color:${STATUS[m.status[i]].color}">${esc(statusText(m, i))}</span>${m.cross[i] ? `<br><span style="color:${BYPASS_COLOR}">crosses ${m.cross[i]} unrelated block${m.cross[i] === 1 ? '' : 's'}</span>` : ''}`; }
    else if (p.bundle) html = `<b>${p.bundle.dens ? 'Local links' : `Bundle of ${p.bundle.n.toLocaleString()} links`}</b><br>` + esc(bundleText(m, p.bundle)) + '<br><span class="dim">click to list; zoom in to separate</span>';
    else if (p.block != null) html = `<b>${esc(m.bname[p.block])}</b><br>${esc(m.bmaster[p.block] || '')}${m.bkind[p.block] ? ` [${esc(m.bkind[p.block])}]` : ''} · ${incident(m, p.block).length} links`;
    tipEl.innerHTML = html; tipEl.style.display = 'block';
    const x = Math.min(innerWidth - 300, ev.clientX + 14), y = Math.min(innerHeight - 90, ev.clientY + 14);
    tipEl.style.left = x + 'px'; tipEl.style.top = y + 'px';
  }

  // ---------------------------------------------------------------------------------------------- controls
  dieSel.addEventListener('change', () => { S.sel = null; S.chosen = true; S.note = ''; floor.set({ highlight: null, selBlock: -1 }); load(rows.find((r) => r.id === dieSel.value)); opts.onRecord && opts.onRecord(dieSel.value); });
  for (const btn of modeBtns) btn.addEventListener('click', () => {
    S.mode = btn.dataset.mode; modeBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === btn)));
    if (S.mode === 'all') { floor.set({ mode: 'all', active: null, trail: [], lit: null, cut: S.cong ? cmAll : null, flow: false }); table.setActive(null); if (!S.sel) renderSide(); }
    else { cur = -1; onTime(clock.t, true); }
  });
  top.addEventListener('change', (e) => {
    const k = e.target.dataset?.k; if (!k) return;
    S[k] = e.target.checked;
    if (k === 'man') floor.set({ manhattan: S.man });
    if (k === 'bypass') floor.set({ bypassOnly: S.bypass });
    if (k === 'cong') { renderLegend(); if (S.mode === 'all' || !data) floor.set({ cut: S.cong ? cmAll : null }); else { cur = -1; onTime(clock.t, true); } }
    if (k === 'trail') { cur = -1; onTime(clock.t, true); }
  });
  minSel.addEventListener('change', () => floor.set({ minBits: +minSel.value }));
  lenSel.addEventListener('change', () => floor.set({ minLen: lenSel.value === 'auto' ? 'auto' : lenSel.value === 'reach' ? m.reach : +lenSel.value }));
  wIn.addEventListener('input', () => { floor.set({ wscale: +wIn.value }); renderLegend(); });
  fitB.addEventListener('click', () => floor.fit());
  let unsub = null;
  if (data) {
    speedSel.addEventListener('change', () => { clock.seconds = +speedSel.value; });
    slider.addEventListener('input', () => clock.seek(clock.t0 + (clock.t1 - clock.t0) * slider.value / 10000));
    const stripSeek = (ev) => { const r = strip.getBoundingClientRect(); clock.pause(); clock.seek(clock.t0 + (clock.t1 - clock.t0) * Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width))); };
    strip.addEventListener('pointerdown', (ev) => { stripSeek(ev); strip.setPointerCapture(ev.pointerId); });
    strip.addEventListener('pointermove', (ev) => { if (ev.buttons) stripSeek(ev); });
    strip.addEventListener('keydown', (ev) => { if (ev.key === 'ArrowRight') { stepWin(1); ev.preventDefault(); } if (ev.key === 'ArrowLeft') { stepWin(-1); ev.preventDefault(); } if (ev.key === 'PageDown') { stepStage(1); ev.preventDefault(); } if (ev.key === 'PageUp') { stepStage(-1); ev.preventDefault(); } });
    let wasPlaying = false;
    unsub = clock.on((t) => { onTime(t); if (clock.playing !== wasPlaying) { wasPlaying = clock.playing; floor.set({ flow: clock.playing }); } });
  }
  const ro = new ResizeObserver(() => { if (data && m) drawStrip(clock.t); }); ro.observe(root);
  await load(S.row);
  return {
    destroy() { unsub && unsub(); ro.disconnect(); floor.destroy(); },
    get model() { return m; }, floor, table, selectLink,
  };
}

(function(){
'use strict';
/* ==========================================================================
   OpenTallas Chip Explorer. Rendering code only reads DATA through val()/the
   {v,unit,status,src} leaves, so replacing a value with a measured one is a
   data edit, never a code edit.
   ========================================================================== */
const $ = id => document.getElementById(id);
const val = x => (x && typeof x === 'object' && 'v' in x && 'status' in x) ? x.v : x;
const st = x => (x && typeof x === 'object' && 'status' in x) ? x.status : 'measured';
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt = (n, d = 1) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
const fmt0 = n => fmt(n, 0);
const SVGNS = 'http://www.w3.org/2000/svg';
const reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
function css(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function pill(s){ return `<span class="pill p-${esc(s)}"><i></i>${esc(s)}</span>`; }
const CLOSURE_LABEL = {'closed':'closed at 1.2 GHz','exact-not-closed':'exact, not closed','open':'open','no-rtl':'no RTL top','reservation':'reservation'};
function cpill(c){ return `<span class="pill c-${esc(c)}"><i></i>${esc(CLOSURE_LABEL[c] || c)}</span>`; }
function svgEl(tag, attrs, parent){ const e = document.createElementNS(SVGNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function clear(n){ while (n.firstChild) n.removeChild(n.firstChild); }
function vs(x, d = 1){ if (x == null) return '—'; const v = val(x); if (v == null) return '—'; return typeof v === 'number' ? fmt(v, d) : esc(v); }
function srcLine(x){ return x && x.src ? `<div class="src">${pill(x.status)} ${esc(x.src)}${x.note ? ' — ' + esc(x.note) : ''}</div>` : ''; }
const tip = $('tip');
function showTip(html, ev){ tip.innerHTML = html; tip.hidden = false; const pad = 14; let x = ev.clientX + pad, y = ev.clientY + pad; const r = tip.getBoundingClientRect(); if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - pad; if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - pad; tip.style.left = Math.max(4, x) + 'px'; tip.style.top = Math.max(4, y) + 'px'; }
function hideTip(){ tip.hidden = true; }
function lsGet(k, d){ try { const v = localStorage.getItem('otx.' + k); return v == null ? d : v; } catch (e) { return d; } }
function lsSet(k, v){ try { localStorage.setItem('otx.' + k, v); } catch (e) {} }

/* ---------------------------------------------------------------- designs */
const DESIGNS = {
  qwen: { short: 'Qwen ROM', title: ['Qwen3-8B', 'ROM accelerator'], ctx: '8K context, position 8,191',
    lede: 'Weights are hard-wired in ROM beside the multipliers, so a decode step never fetches a weight. The per-user KV cache streams from four attached HBM3E stacks (STREAM4). The design runs plain decoding: speculation measured below plain decoding on this compute-balanced datapath.',
    dies: ['qwen_rom'] },
  ds: { short: 'DeepSeek ROM array', title: ['DeepSeek-V4.1', 'ROM array'], ctx: '1M context, position 1,048,575',
    lede: `An ${val(DATA.ds_system.stages)}-stage pipeline of ROM dies. Each layer is spread over a TP4 group of rank dies whose fields of ROM element pairs hold the weights; the token walks the pipeline over die-to-die links and its KV comes from HBM beside every die. MTP speculation fills idle stages with a wavefront of draft positions.`,
    dies: ['ds_s81_layer'] },
  hbm: { short: 'HBM accelerator', title: ['HBM', 'accelerator'], ctx: 'matched comparator, same contexts',
    lede: 'The comparator is a GPU-like die: 32 SM compute elements fed by four HBM3E stacks on the long edges, a hub band of serial vector, special-function, hyper-connection and index units, 64 attention tiles and a centre spine. Weights stream from HBM every token; speculation shares that weight stream across the verified positions.',
    dies: ['hbm_ds', 'hbm_qwen'] },
};
const state = { design: lsGet('design', 'ds'), compare: false, hbmModel: lsGet('hbmModel', 'ds'), colorBy: 'kind', zoom: 1,
  hidden: new Set(), dieCtx: null, showWire: true, showClock: false, showIR: false, sel: null, arraySel: null, arrayZoom: 'system', cbFilter: 'all' };
if (!DESIGNS[state.design]) state.design = 'ds';
function dieKey(){ return state.design === 'hbm' ? (state.hbmModel === 'qwen' ? 'hbm_qwen' : 'hbm_ds') : DESIGNS[state.design].dies[0]; }

/* ---------------------------------------------------------------- block grouping and colour */
function groupOf(dk, kind, name){
  if (dk === 'hbm_ds'){
    if (kind === 'hub' || kind === 'spine'){ return name.replace(/^hb_/, '').split('_')[0]; }
    return ({attn_tile:'attn', serdes_slab:'serdes', host_slab:'host'})[kind] || kind;
  }
  return kind;
}
function catOf(dk, g, name){
  if (dk === 'ds_s81_layer' && g === 'hub'){
    if (/su_/.test(name)) return 'su'; if (/hc/.test(name)) return 'hc'; if (/gather/.test(name)) return 'attn'; if (/collective/.test(name)) return 'link'; return 'ctrl';
  }
  if (dk === 'qwen_rom' && g === 'spine'){
    if (/su64/.test(name)) return 'su'; if (/tree/.test(name)) return 'tree'; return 'ctrl';
  }
  const M = { sm:'field', tile:'field', q:'field', bf:'field', node:'tree', col_head:'tree', head:'tree',
    su:'su', sfu:'sfu', hc:'hc', attn:'attn', row_engine:'attn', band_blk:'attn', index:'index',
    cmdproc:'ctrl', vm:'ctrl', barrier:'ctrl', router:'ctrl', quant:'ctrl', loader:'ctrl', spine:'ctrl', band_slab:'ctrl',
    phy:'hbm', svc: dk === 'ds_s81_layer' ? 'attn' : 'hbmsvc', ctrl:'hbmsvc', hbm_ctrl:'hbmsvc', cdc:'hbmsvc',
    coll:'link', link:'link', serdes:'link', host:'link', io:'link', link_fifo:'link', serdes_slab:'link', host_slab:'link',
    hub: dk === 'qwen_rom' ? 'ctrl' : 'link',
    waypoint:'wire', station:'wire', link_station:'wire', fifo_blk:'wire', hub_fifo:'wire' };
  return M[g] || 'res';
}
const CATS = [
  ['field','Matrix field / ROM tiles','--k-field'], ['tree','Reduction tree / heads','--k-tree'], ['su','Serial vector unit','--k-su'], ['sfu','Special functions','--k-sfu'],
  ['hc','Hyper-connection mix','--k-hc'], ['attn','Attention / scan','--k-attn'], ['index','Indexer','--k-index'], ['ctrl','Control, spine, VM','--k-ctrl'],
  ['hbm','HBM PHY','--k-hbm'], ['hbmsvc','HBM controller / stream service','--k-hbmsvc'], ['link','Links, SerDes, collective','--k-link'], ['wire','Wire stations, FIFOs','--k-wire'], ['res','Other','--k-res'] ];
const CATVAR = Object.fromEntries(CATS.map(c => [c[0], c[2]]));
const CLOSVAR = {'closed':'--s-closed','exact-not-closed':'--s-enc','open':'--s-open','no-rtl':'--s-nortl','reservation':'--s-res'};

/* geometry index (built once per die) */
const GEO = {};
function geo(dk){
  if (GEO[dk]) return GEO[dk];
  const g = val(DATA.dies[dk].geo);
  const items = g.rects.map((r, i) => { const kind = g.kinds[r[0]]; const grp = groupOf(dk, kind, r[5]); return { i, kind, g: grp, cat: catOf(dk, grp, r[5]), x: r[1], y: r[2], w: r[3], h: r[4], name: r[5] }; });
  const groups = {};
  items.forEach(it => { (groups[it.g] = groups[it.g] || []).push(it); });
  const byName = {}; items.forEach(it => { byName[it.name] = it; });
  return (GEO[dk] = { W: g.w, H: g.h, items, groups, byName, meta: g.meta || {} });
}
function blockInfo(dk, g){ return (DATA.blocks[dk] || {})[g] || null; }
function closureOf(dk, g){ const b = blockInfo(dk, g); return b ? b.closure : 'open'; }

/* ---------------------------------------------------------------- top bar, banner, hero */
function statusCounts(){
  const c = {measured:0, analytical:0, estimate:0, placeholder:0};
  walk(DATA, '', (p, leaf) => { c[leaf.status] = (c[leaf.status] || 0) + 1; });
  return c;
}
function walk(o, p, f){
  if (o && typeof o === 'object' && 'v' in o && 'status' in o && 'src' in o){ f(p, o); return; }
  if (Array.isArray(o)) return;
  if (o && typeof o === 'object') for (const k in o) walk(o[k], p ? p + '.' + k : k, f);
}
function renderNotice(){
  const c = statusCounts();
  $('notice').innerHTML = `<span>Values marked <b>analytical</b>, <b>estimate</b> or <b>placeholder</b> will be replaced with measured ones as records land.</span>` +
    ['measured','analytical','estimate','placeholder'].map(s => `<span class="p-${s}"><span class="dot" style="background:currentColor"></span>${c[s] || 0} ${s}</span>`).join('');
}
function kpi(label, x, unit, d, digits = 1){
  return `<div class="kpi"><div class="k"><span>${esc(label)}</span>${pill(st(x))}</div><div class="v num">${vs(x, digits)}<small>${esc(unit || (x && x.unit) || '')}</small></div>${d ? `<div class="d">${d}</div>` : ''}</div>`;
}
function renderHero(){
  const D = DESIGNS[state.design], R = DATA.rates;
  let k = '';
  if (state.design === 'qwen'){
    k = kpi('Plain decoding, per user', R.qwen.AR, 'tok/s', 'speculation off: DSpark measured ' + fmt(val(R.qwen.dspark_ratio), 3) + '× of plain') +
        kpi('Token at P8191', R.qwen.cycles, 'cycles', fmt(val(R.qwen.AR_us), 1) + ' µs at 1.2 GHz', 0) +
        kpi('Die (r17b)', DATA.dies.qwen_rom.area, 'mm²', 'reticle 858 mm²', 1) +
        kpi('TP4 group', {v: 4, unit: 'dies', status: 'measured', src: 'results/rtl/qwen_plain_ar_stream4_P8191_20261005/measured_composition.json ranks'}, 'dies', '4 HBM3E stacks per die', 0);
  } else if (state.design === 'ds'){
    k = kpi('Plain decoding (AR)', R.ds.AR, 'tok/s', fmt(val(R.ds.AR_us), 1) + ' µs per token') +
        kpi('MTP speculation', R.ds.MTP, 'tok/s', 'τ ' + fmt(val(R.ds.tau), 3) + '; step ' + fmt(val(R.ds.MTP_step_us), 1) + ' µs') +
        kpi('With pending levers', R.ds.AR_cond, 'tok/s AR', fmt(val(R.ds.MTP_cond), 1) + ' MTP if every PENDING_SSFF lever closes') +
        kpi('Pipeline', DATA.ds_system.stages, 'stages', fmt0(val(DATA.ds_system.layer_dies)) + ' layer dies + ' + val(DATA.ds_system.head_dies) + ' head + ' + val(DATA.ds_system.draft_added) + ' draft', 0);
  } else {
    k = kpi('DeepSeek 1M, AR (candidate)', R.hbm_ds.AR_unified, 'tok/s', 'with die closure costs; ' + fmt(val(R.hbm_ds.AR_no_lever)) + ' without lever credit; pre-closure ' + fmt(val(R.hbm_ds.AR))) +
        kpi('DeepSeek 1M, MTP (candidate)', R.hbm_ds.MTP_unified, 'tok/s', 'τ 4.159, same as the ROM') +
        kpi('Qwen 8K, TP4', R.hbm_qwen.AR, 'tok/s', 'TP2 ' + fmt(val(R.hbm_qwen.AR_tp2)) + ' tok/s (wire median)') +
        kpi('DS die (r14b)', DATA.dies.hbm_ds.area, 'mm²', 'Qwen tile die ' + fmt(val(DATA.dies.hbm_qwen.area)) + ' mm²');
  }
  $('hero').innerHTML = `<div><div class="eyebrow">${esc(D.ctx)}</div><h1>${esc(D.title[0])}<br><em>${esc(D.title[1])}</em></h1><p class="lede">${esc(D.lede)}</p></div><div class="kpis">${k}</div>`;
  document.querySelectorAll('[data-design]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.design === state.design)));
  renderCompareStrip();
}
function renderCompareStrip(){
  const s = $('cmpStrip');
  if (!state.compare){ s.innerHTML = ''; return; }
  const R = DATA.rates;
  const card = (name, rows) => `<div class="card"><h3>${esc(name)}</h3><dl style="display:grid;grid-template-columns:auto 1fr;gap:4px 10px;margin:8px 0 0">${rows.map(r => `<dt class="eyebrow" style="align-self:center">${esc(r[0])}</dt><dd class="num" style="margin:0">${vs(r[1], r[2] == null ? 1 : r[2])} ${esc(r[1] && r[1].unit || '')} ${pill(st(r[1]))}</dd>`).join('')}</dl></div>`;
  s.innerHTML = `<div class="cmp3">${card('Qwen ROM, 8K', [['AR', R.qwen.AR], ['MTP', R.qwen.MTP], ['Die', DATA.dies.qwen_rom.area]])}${card('DeepSeek ROM array, 1M', [['AR', R.ds.AR], ['MTP', R.ds.MTP], ['Die', DATA.ds_system.die_mm2]])}${card('HBM accelerator', [['DS AR', R.hbm_ds.AR_unified], ['DS MTP', R.hbm_ds.MTP_unified], ['Qwen TP4', R.hbm_qwen.AR], ['DS die', DATA.dies.hbm_ds.area]])}</div>`;
}

/* ================================================================ 1. ARRAY */
/* Every array view lays itself out in CSS pixels at the panel's own width (arrW), so it fits the panel
   at any width and text stays at its design size. A ResizeObserver on the panel redraws on resize. */
function arrW(){ const s = $('arrayScroll'); return Math.max(280, Math.floor((s && s.clientWidth) || 900)); }
function sizeSvg(svg, W, H){ svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', Math.ceil(H)); }
function txt(parent, x, y, s, o = {}){ const t = svgEl('text', Object.assign({x, y, 'font-size': o.fs || 12, 'font-family': o.mono === false ? 'var(--f-body)' : 'var(--f-mono)', fill: o.fill || css('--muted')}, o.anchor ? {'text-anchor': o.anchor} : {}, o.weight ? {'font-weight': o.weight} : {}), parent); t.textContent = s; return t; }
/* wrap a string into lines that fit `maxW` px at a mono font of size fs (0.6 em per glyph) */
function wrapLines(s, maxW, fs){ const per = Math.max(8, Math.floor(maxW / (fs * 0.6))); const out = []; let cur = ''; for (const w of s.split(' ')){ if ((cur + ' ' + w).trim().length > per && cur){ out.push(cur); cur = w; } else cur = (cur + ' ' + w).trim(); } if (cur) out.push(cur); return out; }
function txtWrap(parent, x, y, s, maxW, o = {}){ const fs = o.fs || 12, lh = o.lh || fs * 1.35; const ls = wrapLines(s, maxW, fs); ls.forEach((l, i) => txt(parent, x, y + i * lh, l, o)); return ls.length * lh; }
/* link stroke width from bandwidth: 2 px at <= 50 GB/s, +1.15 px per doubling, capped at 7 px */
function lw(x){ const g = val(x); if (!g) return 2.5; return Math.max(2, Math.min(7, 2 + 1.15 * Math.log2(Math.max(1, g / 50)))); }
/* a link: wide transparent hit stroke + visible stroke + optional flow dashes (direction of traffic).
   Hovering it lights it and its endpoints (elements whose data-id is in a/b). */
function hotIds(root, ids, on){ for (const id of ids) if (id) root.querySelectorAll(`[data-id="${id}"]`).forEach(n => n.classList.toggle('hot', on)); }
function link(parent, d, o = {}){
  const g = svgEl('g', {class: 'lk' + (o.cls ? ' ' + o.cls : '')}, parent);
  const w = o.w || 2.5;
  svgEl('path', {d, class: 'lk-hit', 'stroke-width': o.hit || Math.max(12, w + 8)}, g);
  const ln = svgEl('path', {d, class: 'lk-line', 'stroke-width': w}, g);
  if (o.dash) ln.setAttribute('stroke-dasharray', o.dash);
  if (o.arrow) ln.setAttribute('marker-end', 'url(#lkArrow)');
  if (o.flow) svgEl('path', {d, class: 'lk-flow', 'stroke-width': Math.max(1.2, w * 0.5)}, g);
  const ends = [].concat(o.ends || []);
  const root = parent.ownerSVGElement || parent;
  g.addEventListener('mouseenter', () => { g.classList.add('hot'); hotIds(root, ends, true); });
  g.addEventListener('mouseleave', () => { g.classList.remove('hot'); hotIds(root, ends, false); hideTip(); });
  if (o.tip) g.addEventListener('mousemove', ev => showTip(o.tip, ev));
  return g;
}
function linkDefs(svg){
  const defs = svgEl('defs', {}, svg);
  const m = svgEl('marker', {id: 'lkArrow', viewBox: '0 0 10 10', refX: 7, refY: 5, markerWidth: 3.2, markerHeight: 3.2, orient: 'auto-start-reverse', markerUnits: 'strokeWidth'}, defs);
  svgEl('path', {d: 'M0,1 L9,5 L0,9 z', class: 'lk-head'}, m);
  const p = svgEl('pattern', {id: 'hatchArr', width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)'}, defs); svgEl('rect', {width: 2.2, height: 6, fill: css('--k-res')}, p);
  return defs;
}
function linkTip(name, x, extra){ return `<b>${esc(name)}</b>${x ? `<br>${vs(x, 0)} ${esc(x.unit || '')} · ${esc(st(x))}` : ''}${extra ? '<br>' + extra : ''}`; }

function renderArray(){
  const svg = $('arraySvg'); clear(svg);
  const tools = $('arrayTools'); const leg = $('arrayLegend');
  const d = state.design;
  const linkLeg = (label, x) => `<span><i class="sw lk-sw" style="height:${Math.round(lw(x))}px"></i>${label}${x ? ' · ' + vs(x, 0) + ' ' + esc(x.unit || '') + ' ' + pill(st(x)) : ''}</span>`;
  if (d === 'ds'){
    $('arrayLede').textContent = 'The token walks the ' + val(DATA.ds_system.stages) + '-stage pipeline (q-element frame) as a serpentine: left to right, then back. Each cell is one stretch of the critical path between two measured stage hops; its four squares are the TP4 rank dies that hold the layer slice, each with HBM beside it. Shade shows how long the stretch keeps the token. Click a cell for its breakdown; double-click (or Stage) to zoom in.';
    tools.innerHTML = `<div class="seg" role="group" aria-label="Zoom level"><button type="button" data-az="system" aria-pressed="${state.arrayZoom === 'system'}">System</button><button type="button" data-az="stage" aria-pressed="${state.arrayZoom === 'stage'}">Stage</button></div><span class="muted" style="font-size:12px">${state.arrayZoom === 'stage' ? 'Stage ' + (state.arraySel == null ? 0 : state.arraySel) + ': four rank dies and their links' : 'packages → dies → stages → links'}</span>`;
    tools.querySelectorAll('[data-az]').forEach(b => b.onclick = () => { state.arrayZoom = b.dataset.az; if (state.arraySel == null) state.arraySel = 20; renderArray(); });
    if (state.arrayZoom === 'stage') drawDsStage(svg); else drawDsRibbon(svg);
    const L = DATA.links || {};
    leg.innerHTML = `<span><i class="sw" style="background:var(--k-field)"></i>ROM rank die (shade: busy time)</span><span><i class="sw" style="background:var(--k-hbm)"></i>HBM stack</span>${linkLeg('stage hop ' + vs(DATA.ds_hop, 4) + ' µs', L.ds_stage)}${linkLeg('draft replica link', L.ds_draft)}<span><i class="sw" style="background:repeating-linear-gradient(45deg,var(--k-res) 0 2px,transparent 2px 5px)"></i>hop-only stage, position not in the record</span><span><i class="sw" style="background:var(--k-attn)"></i>draft dies (DP1-EP5)</span><span class="muted">Line width scales with link bandwidth; hover a link to light it and its ends.</span>`;
  } else if (d === 'qwen'){
    $('arrayLede').textContent = 'One user’s token runs on a TP4 group: four identical ROM dies, each holding a quarter of every weight matrix and streaming its share of the KV cache from four HBM3E stacks on its east and west edges. The dies meet only at the all-reduce after each attention and MLP block.';
    tools.innerHTML = '<span class="muted" style="font-size:12px">system: 4 dies · 16 HBM3E stacks · TP4 all-reduce</span>';
    drawQwenSystem(svg);
    leg.innerHTML = `<span><i class="sw" style="background:var(--k-field)"></i>ROM die</span><span><i class="sw" style="background:var(--k-hbm)"></i>HBM3E stack</span>${linkLeg('all-reduce link', (DATA.links || {}).qwen_ar)}`;
  } else {
    $('arrayLede').textContent = state.hbmModel === 'qwen' ? 'Qwen3-8B on the HBM accelerator: a TP4 group of tile dies (iso-silicon with the ROM group) or a TP2 group on the same silicon. Every die streams its weight share from its four stacks every token.' : 'DeepSeek-V4.1 at 1M on the HBM accelerator: 96 dies in tensor parallel (TP-96), each with four HBM3E stacks, joined through a Tomahawk-Ultra switch tier. Every die stripes its ports across all the switch chips; collectives cross the switch, and about a third of the AR token is the vendor budget for that crossing.';
    tools.innerHTML = `<div class="seg" role="group" aria-label="Model"><button type="button" data-hm="ds" aria-pressed="${state.hbmModel === 'ds'}">DeepSeek die</button><button type="button" data-hm="qwen" aria-pressed="${state.hbmModel === 'qwen'}">Qwen tile die</button></div>`;
    tools.querySelectorAll('[data-hm]').forEach(b => b.onclick = () => { state.hbmModel = b.dataset.hm; lsSet('hbmModel', state.hbmModel); state.sel = null; renderAll(); });
    drawHbmSystem(svg);
    leg.innerHTML = `<span><i class="sw" style="background:var(--k-field)"></i>compute die</span><span><i class="sw" style="background:var(--k-hbm)"></i>HBM3E stack</span><span><i class="sw" style="background:var(--k-link)"></i>switch chip</span>${linkLeg('die uplink', (DATA.links || {}).hbm_uplink)}<span class="muted">Hover a die or a switch chip to see its fan-out.</span>`;
  }
}
function arrayRead(html){ $('arrayRead').innerHTML = html; }
function dieGlyph(svg, x, y, w, h, fill, stacks, opts = {}){
  const g = svgEl('g', opts.id ? {class: 'nd', 'data-id': opts.id} : {}, svg);
  svgEl('rect', {x, y, width: w, height: h, fill, stroke: css('--die-edge'), 'stroke-width': 0.8, rx: 1}, g);
  const sw = Math.max(3, w * 0.22), sh = Math.max(2.5, Math.min(h * 0.26, 10));
  if (stacks === 'ns'){ for (let i = 0; i < 2; i++){ svgEl('rect', {x: x + w * (0.12 + 0.5 * i), y: y - sh - 1.5, width: sw * 1.2, height: sh, fill: css('--k-hbm')}, g); svgEl('rect', {x: x + w * (0.12 + 0.5 * i), y: y + h + 1.5, width: sw * 1.2, height: sh, fill: css('--k-hbm')}, g); } }
  if (stacks === 'ew'){ const sw2 = Math.max(3, h * 0.22), sh2 = Math.max(2.5, Math.min(w * 0.26, 10)); for (let i = 0; i < 2; i++){ svgEl('rect', {x: x - sh2 - 1.5, y: y + h * (0.12 + 0.5 * i), width: sh2, height: sw2 * 1.2, fill: css('--k-hbm')}, g); svgEl('rect', {x: x + w + 1.5, y: y + h * (0.12 + 0.5 * i), width: sh2, height: sw2 * 1.2, fill: css('--k-hbm')}, g); } }
  if (opts.label) { const t = svgEl('text', {x: x + w / 2, y: y + h / 2 + 4, 'text-anchor': 'middle', 'font-size': opts.fs || 11, 'font-family': 'var(--f-mono)'}, g); t.textContent = opts.label; }
  return g;
}
function mix(c1, c2, t){ // hex mix for shading
  const p = c => { c = c.replace('#', ''); if (c.length === 3) c = c.split('').map(x => x + x).join(''); return [0, 2, 4].map(i => parseInt(c.substr(i, 2), 16)); };
  try { const a = p(c1), b = p(c2); return '#' + a.map((v, i) => Math.round(v + (b[i] - v) * t).toString(16).padStart(2, '0')).join(''); } catch (e) { return c1; }
}
function segBusy(s){ let t = 0; for (const k in s.cats) t += s.cats[k]; return t; }
function keyActivate(g, f){ g.addEventListener('click', f); g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); f(e); } }); }
function drawDsRibbon(svg){
  const W = arrW(); const narrow = W < 560;
  const segs = val(DATA.ds_stages); const extra = val(DATA.ds_extra_hops); const S = DATA.ds_system; const L = DATA.links || {};
  const total = segs.length + extra.count;
  const cw = narrow ? 30 : 40, ch = narrow ? 34 : 44, gx = narrow ? 11 : 16, gy = narrow ? 30 : 34, turn = narrow ? 14 : 22;
  const perRow = Math.max(4, Math.floor((W - 2 * turn - 8 + gx) / (cw + gx)));
  const rows = Math.ceil(total / perRow);
  const gridW = perRow * (cw + gx) - gx, xs = Math.round((W - gridW) / 2);
  linkDefs(svg);
  const lay = svgEl('g', {}, svg);
  const head = narrow ? [`token → ${segs.length} stretches + ${extra.count} hop-only stages`, `= ${segs.length + extra.count - 1} stage hops, serpentine`] : [`token → ${segs.length} critical-path stretches + ${extra.count} hop-only stages (${extra.s81} S81 + ${extra.qelem} q-element frame) = ${segs.length + extra.count - 1} stage hops · serpentine: left to right, then right to left`];
  head.forEach((l, i) => txt(lay, xs, 16 + i * 15, l));
  const y0 = 16 + head.length * 15 + 12;
  const pos = k => { const r = Math.floor(k / perRow), c = k % perRow, cc = r % 2 ? perRow - 1 - c : c; return {r, c, x: xs + cc * (cw + gx), y: y0 + r * (ch + gy)}; };
  const maxB = Math.max(...segs.map(segBusy));
  const bg = css('--die'), fc = css('--k-field');
  const linkG = svgEl('g', {}, svg), cellG = svgEl('g', {}, svg);
  const lwStage = lw(L.ds_stage);
  for (let k = 0; k < total; k++){
    const {r, c, x, y} = pos(k);
    const id = 'c' + k;
    const g = svgEl('g', {tabindex: 0, role: 'button', class: 'nd cell', 'data-id': id, 'aria-label': k < segs.length ? `Stretch ${k}: ${segs[k].layers.join(', ')}` : 'Hop-only stage', style: 'cursor:pointer'}, cellG);
    svgEl('rect', {x: x - 3, y: y - 5, width: cw + 6, height: ch + 8, fill: 'transparent', stroke: state.arraySel === k ? css('--accent') : 'none', 'stroke-width': 2, rx: 2, class: 'cell-frame'}, g);
    if (k < segs.length){
      const s = segs[k], b = segBusy(s), shade = b ? mix(bg, fc, 0.25 + 0.75 * b / maxB) : bg;
      const qw = (cw - 4) / 2, qh = (ch - 8) / 2 - 3;
      for (let q = 0; q < 4; q++){
        const dx = x + (q % 2) * (qw + 4), dy = y + 4 + Math.floor(q / 2) * (qh + 7);
        svgEl('rect', {x: dx, y: dy, width: qw, height: qh, fill: shade, stroke: css('--die-edge'), 'stroke-width': 0.7}, g);
        svgEl('rect', {x: dx, y: dy - 3.5, width: qw, height: 2.5, fill: css('--k-hbm')}, g);
      }
      let lab = s.layers.filter(l => l !== 'token').join('·').replace(/L(\d+)/g, '$1').replace('embed', narrow ? 'E' : 'emb') || 'pass';
      if (lab.length * 5.4 > cw + gx - 2) lab = lab.split('·')[0] + '…';
      txt(g, x + cw / 2, y + ch + 12, lab, {fs: 9.5, anchor: 'middle'});
      g.addEventListener('mousemove', ev => showTip(`<b>Stretch ${k}</b> · ${esc(s.layers.join(', ') || 'no critical-path work')}<br>busy ${fmt(b, 3)} µs · ${s.n} nodes<br>hop ${fmt(s.hop, 4)} µs ${esc(s.hop_node)}`, ev));
      g.addEventListener('mouseleave', hideTip);
      keyActivate(g, () => { state.arraySel = k; renderArray(); const n = $('arraySvg').querySelector(`[data-id="c${k}"]`); if (n) n.focus(); });
      g.addEventListener('dblclick', () => { state.arraySel = k; state.arrayZoom = 'stage'; renderArray(); });
    } else {
      svgEl('rect', {x: x + 1, y: y + 2, width: cw - 2, height: ch - 4, fill: 'url(#hatchArr)', stroke: css('--die-edge'), 'stroke-width': 0.6, 'stroke-dasharray': '3 2'}, g);
      g.addEventListener('mousemove', ev => showTip(`<b>Hop-only stage</b><br>one of ${extra.count} extra stage hops (${extra.s81} S81 + ${extra.qelem} q-element frame) (${fmt(extra.us_each, 4)} µs each, ${fmt(extra.total, 3)} µs total).<br>Its position in the pipeline is not in the composition record.`, ev));
      g.addEventListener('mouseleave', hideTip);
    }
    if (k < total - 1){
      const n = pos(k + 1), ym = y + ch / 2, yn = n.y + ch / 2;
      let dpath, turnHere = false;
      if (n.r === r){ const dir = n.x > x ? 1 : -1; const xa = dir > 0 ? x + cw + 1 : x - 1, xb = dir > 0 ? n.x - 2 : n.x + cw + 2; dpath = `M${xa} ${ym} L${xb} ${ym}`; }
      else { turnHere = true; const right = r % 2 === 0; const xe = right ? x + cw + 1 : x - 1, xo = right ? x + cw + turn : x - turn; dpath = `M${xe} ${ym} C${xo} ${ym} ${xo} ${yn} ${right ? xe + 1 : xe - 1} ${yn}`; }
      link(linkG, dpath, {w: lwStage, arrow: true, flow: true, ends: [id, 'c' + (k + 1)], cls: turnHere ? 'turn' : '',
        tip: linkTip(`Stage hop ${k} → ${k + 1}${turnHere ? ' (row turn)' : ''}`, L.ds_stage, `${vs(DATA.ds_hop, 4)} µs measured: link RTL + full RS(544,514) PHY budget (209 ns) + UCIe + wire stages; cable flight per hop class in the rack view`)});
      if (turnHere){ const right = r % 2 === 0; txt(lay, right ? x + cw + turn + 1 : x - turn - 1, (ym + yn) / 2 + 3, '↩', {fs: 11, anchor: right ? 'start' : 'end', fill: css('--muted')}).setAttribute('aria-hidden', 'true'); }
    }
  }
  // head dies + draft group, reflowed to the width
  let yb = y0 + rows * (ch + gy) + 6;
  const textW = W - 2 * xs;
  yb += txtWrap(lay, xs, yb + 10, `head dies ×${val(S.head_dies)}: embed, LM head, norm, DSpark drafter`, textW, {fs: 11.5}) + 6;
  const hd = val(S.head_dies), hs = narrow ? 16 : 20, hp = hs + 7;
  const hPer = Math.max(4, Math.floor((textW + 7) / hp));
  for (let i = 0; i < hd; i++) dieGlyph(svg, xs + (i % hPer) * hp, yb + Math.floor(i / hPer) * hp, hs, hs, mix(bg, css('--k-tree'), .6), null, {id: 'h' + i});
  yb += Math.ceil(hd / hPer) * hp + 14;
  yb += txtWrap(lay, xs, yb + 10, `draft placement DP1-EP5: ${val(S.draft_primary)} primary dies + ${val(S.draft_replicas)} expert-replica dies (+${val(S.draft_added)} vs baseline). Rows are the 3 DSpark blocks; each holds 5 expert TP4 groups. ${fmt0(val(S.layer_dies))} layer dies = ${val(S.stages)} × TP4.`, textW, {fs: 11.5}) + 10;
  // primary TP4 group (left), replica groups in a 5-wide grid (right), joined by a trunk and one link per group
  const ps = narrow ? 13 : 17, pg = 3;
  const primX = xs, primY = yb + 6;
  for (let i = 0; i < val(S.draft_primary); i++) dieGlyph(svg, primX + (i % 2) * (ps + pg), primY + Math.floor(i / 2) * (ps + pg), ps, ps, css('--k-attn'), null, {id: 'dp'});
  txt(lay, primX, primY + 2 * (ps + pg) + 12, 'primary', {fs: 10});
  const reps = val(S.draft_replicas), groups = Math.round(reps / 4), perG = 5, gRows = Math.ceil(groups / perG);
  const gs = narrow ? 9 : 12, gW = 2 * gs + 3;
  const trunkX = primX + 2 * (ps + pg) + (narrow ? 14 : 24);
  const gx0 = trunkX + (narrow ? 16 : 26), pitch = Math.min(narrow ? 60 : 90, (xs + textW - gx0 - gW) / (perG - 1));
  const rowH = 2 * gs + 3 + (narrow ? 16 : 20);
  const lwD = lw(L.ds_draft);
  const rmid = r => primY + r * rowH + gs + 1;
  link(linkG, `M${primX + 2 * (ps + pg) - pg + 1} ${primY + ps} L${trunkX} ${primY + ps} L${trunkX} ${rmid(gRows - 1)}`, {w: lwD + 1, ends: ['dp'], tip: linkTip('Draft trunk (15 replica links per primary die, bundled)', L.ds_draft, `draft x-row link ${vs(S.draft_hop, 4)} µs measured (ot_dsrom_link_rt, full FEC)`)});
  for (let gi = 0; gi < groups; gi++){
    const r = Math.floor(gi / perG), c = gi % perG; const gx1 = gx0 + c * pitch, gy1 = primY + r * rowH;
    const id = 'dr' + gi;
    for (let q = 0; q < 4; q++) dieGlyph(svg, gx1 + (q % 2) * (gs + 3), gy1 + Math.floor(q / 2) * (gs + 3), gs, gs, mix(bg, css('--k-attn'), .45), null, {id});
    const xPrev = c === 0 ? trunkX : gx0 + (c - 1) * pitch + gW;
    link(linkG, `M${xPrev} ${rmid(r)} L${gx1 - 1} ${rmid(r)}`, {w: lwD, flow: true, ends: ['dp', id], tip: linkTip(`Replica group ${gi}: DSpark block ${r}, expert group ${c}`, L.ds_draft, `4 dies, one link per primary rank die (board + UCIe class, full RS(544,514) FEC)`)});
  }
  for (let r = 0; r < 3 && r < gRows; r++) txt(lay, gx0 + (perG - 1) * pitch + gW + 4, rmid(r) + 3, narrow ? '' : `block ${r}`, {fs: 10});
  yb = primY + gRows * rowH + 4;
  sizeSvg(svg, W, yb);
  if (state.arraySel == null) state.arraySel = 0;
  renderDsArrayRead(state.arraySel);
}
function drawSelOutline(){ if (state.design === 'ds' && state.arrayZoom === 'system') renderArray(); }
function renderDsArrayRead(k){
  const segs = val(DATA.ds_stages); const s = segs[k]; if (!s){ arrayRead(''); return; }
  const b = segBusy(s);
  const cats = Object.entries(s.cats).sort((a, b) => b[1] - a[1]);
  const top = s.nodes.slice().sort((a, b) => b[1] - a[1]).slice(0, 6);
  arrayRead(`<div class="eyebrow">Critical-path stretch ${k} of ${segs.length}</div><h3>${esc(s.layers.join(' · ') || 'Pass-through stage')}</h3>
    <dl><dt>Busy</dt><dd>${fmt(b, 3)} µs</dd><dt>Leaves on</dt><dd>${esc(s.hop_node || 'token return')} · ${fmt(s.hop, 4)} µs</dd><dt>Nodes</dt><dd>${s.n}</dd>
    ${cats.map(c => `<dt>${esc(c[0])}</dt><dd>${fmt(c[1], 3)} µs</dd>`).join('')}</dl>
    ${top.length ? `<div class="eyebrow" style="margin-top:12px">Longest nodes</div><dl>${top.map(n => `<dt style="text-transform:none">${esc(n[0])}</dt><dd>${fmt(n[1], 4)} µs</dd>`).join('')}</dl>` : '<p class="muted" style="margin-top:8px">No critical-path work in this stage: the token crosses it hop to hop.</p>'}
    ${srcLine(DATA.ds_stages)}`);
}
function drawDsStage(svg){
  const k = state.arraySel == null ? 20 : state.arraySel; const s = val(DATA.ds_stages)[k];
  const W = arrW(), wide = W >= 680; const L = DATA.links || {};
  linkDefs(svg);
  const bg = css('--die');
  const lay = svgEl('g', {}, svg), lk = svgEl('g', {}, svg);
  let y = 18 + txtWrap(lay, 14, 18, `Stage view · stretch ${k}: ${s ? s.layers.join(', ') : ''} · TP4 rank dies (four HBM3E stacks on the 32 scan dies, one on the others)`, W - 28, {fs: 12.5});
  const stubW = wide ? 56 : Math.min(160, W * 0.4), stubH = wide ? 120 : 34;
  let dies = [], prev, next, H;
  if (wide){
    const gap = 40, inner = W - 2 * (14 + stubW + 40); const dw = Math.min(150, (inner - 3 * gap) / 4), dh = dw * 0.79;
    const x0 = (W - (4 * dw + 3 * gap)) / 2, dy = y + 50;
    for (let r = 0; r < 4; r++) dies.push({x: x0 + r * (dw + gap), y: dy, w: dw, h: dh});
    prev = {x: 14, y: dy + dh / 2 - stubH / 2, w: stubW, h: stubH}; next = {x: W - 14 - stubW, y: prev.y, w: stubW, h: stubH};
    H = dy + dh + 70;
  } else {
    prev = {x: (W - stubW) / 2, y: y + 6, w: stubW, h: stubH};
    const gap = 34, dw = Math.min(140, (W - 28 - gap) / 2), dh = dw * 0.79, x0 = (W - (2 * dw + gap)) / 2, dy = prev.y + stubH + 46;
    for (let r = 0; r < 4; r++) dies.push({x: x0 + (r % 2) * (dw + gap), y: dy + Math.floor(r / 2) * (dh + gap + 14), w: dw, h: dh});
    next = {x: prev.x, y: dies[3].y + dh + 40, w: stubW, h: stubH};
    H = next.y + stubH + 16;
  }
  for (const [b, lab, id] of [[prev, 'stage k−1', 'sp'], [next, 'stage k+1', 'sn']]){
    const g = svgEl('g', {class: 'nd', 'data-id': id}, svg);
    svgEl('rect', {x: b.x, y: b.y, width: b.w, height: b.h, fill: 'none', stroke: css('--die-edge'), 'stroke-dasharray': '4 3'}, g);
    txt(g, b.x + b.w / 2, b.y + b.h / 2 + 4, lab, {fs: 11, anchor: 'middle'});
  }
  dies.forEach((d, r) => { dieGlyph(svg, d.x, d.y, d.w, d.h, mix(bg, css('--k-field'), .35), 'ns', {label: 'rank ' + r, fs: 13, id: 'r' + r}); });
  // stage hops in and out of every rank die (solid), TP4 collectives between ranks (dashed)
  const lwS = lw(L.ds_stage), lwT = lw(L.ds_tp);
  dies.forEach((d, r) => {
    let din, dout;
    if (wide){ din = `M${prev.x + prev.w} ${prev.y + prev.h / 2} C${prev.x + prev.w + 30} ${prev.y + prev.h / 2} ${d.x - 30} ${d.y + d.h * 0.8} ${d.x - 2} ${d.y + d.h * 0.8}`; dout = `M${d.x + d.w + 1} ${d.y + d.h * 0.2} C${d.x + d.w + 30} ${d.y + d.h * 0.2} ${next.x - 30} ${next.y + next.h / 2} ${next.x - 3} ${next.y + next.h / 2}`; }
    else { din = `M${prev.x + prev.w / 2} ${prev.y + prev.h} C${prev.x + prev.w / 2} ${d.y - 30} ${d.x + d.w * 0.3} ${prev.y + prev.h + 10} ${d.x + d.w * 0.3} ${d.y - 13}`; dout = `M${d.x + d.w * 0.7} ${d.y + d.h + 13} C${d.x + d.w * 0.7} ${next.y - 10} ${next.x + next.w / 2} ${d.y + d.h + 30} ${next.x + next.w / 2} ${next.y - 3}`; }
    if (!wide && r < 2) din = `M${prev.x + prev.w / 2} ${prev.y + prev.h} L${d.x + d.w * 0.3} ${d.y - 13}`;
    if (!wide && r >= 2) dout = `M${d.x + d.w * 0.7} ${d.y + d.h + 13} L${next.x + next.w / 2} ${next.y - 3}`;
    if (!wide && r >= 2) din = `M${prev.x + prev.w / 2} ${prev.y + prev.h} L${prev.x + prev.w / 2} ${prev.y + prev.h + 4} L${r === 2 ? 6 : W - 6} ${prev.y + prev.h + 18} L${r === 2 ? 6 : W - 6} ${d.y + d.h / 2} L${r === 2 ? d.x - 2 : d.x + d.w + 2} ${d.y + d.h / 2}`;
    if (!wide && r < 2) dout = `M${r === 0 ? d.x - 2 : d.x + d.w + 2} ${d.y + d.h / 2} L${r === 0 ? 14 : W - 14} ${d.y + d.h / 2} L${r === 0 ? 14 : W - 14} ${next.y + next.h / 2} L${r === 0 ? next.x - 2 : next.x + next.w + 2} ${next.y + next.h / 2}`;
    link(lk, din, {w: lwS, arrow: true, flow: true, ends: ['sp', 'r' + r], tip: linkTip(`Stage hop in → rank ${r}`, L.ds_stage, `${vs(DATA.ds_hop, 4)} µs measured`)});
    link(lk, dout, {w: lwS, arrow: true, flow: true, ends: ['r' + r, 'sn'], tip: linkTip(`Stage hop out of rank ${r}`, L.ds_stage, `${vs(DATA.ds_hop, 4)} µs measured`)});
  });
  const pairs = wide ? [[0, 1], [1, 2], [2, 3]] : [[0, 1], [2, 3], [0, 2], [1, 3]];
  for (const [a, b] of pairs){
    const A = dies[a], B = dies[b]; let d;
    if (A.y === B.y) d = `M${A.x + A.w + 2} ${A.y + A.h / 2} L${B.x - 2} ${B.y + B.h / 2}`; else d = `M${A.x + A.w / 2} ${A.y + A.h + 13} L${B.x + B.w / 2} ${B.y - 13}`;
    link(lk, d, {w: lwT, dash: '6 4', ends: ['r' + a, 'r' + b], tip: linkTip(`TP4 collective link, rank ${a} ↔ rank ${b}`, L.ds_tp, 'all-gather and all-reduce inside the stage')});
  }
  H += 8 + txtWrap(lay, 14, H, `Dashed: TP4 collectives inside the stage (all-gather, all-reduce). Solid with arrows: stage hops over the board or cable link (full RS(544,514) FEC) + UCIe fan-out. The die floorplan below is the scan die (four stacks; ${val(DATA.ds_system.scan_dies)} of the ${fmt0(val(DATA.ds_system.layer_dies))} layer dies); the other layer dies carry one stack.`, W - 28, {fs: 11.5, fill: css('--ink')});
  sizeSvg(svg, W, H + 4);
  renderDsArrayRead(k);
}
function drawQwenSystem(svg){
  const W = arrW(), wide = W >= 640; const L = DATA.links || {};
  linkDefs(svg);
  const g = geo('qwen_rom'); const ar = g.W / g.H;
  const lay = svgEl('g', {}, svg), lk = svgEl('g', {}, svg);
  const y0 = 16 + txtWrap(lay, 14, 18, 'TP4 group · each die streams KV for its heads from its own 4 stacks · all-reduce after attention and after the MLP', W - 28, {fs: 12}) + 14;
  const cols = wide ? 4 : 2, gap = wide ? 54 : 40;
  const w = Math.min(150, (W - 28 - (cols - 1) * gap - 30) / cols), h = w / ar;
  const x0 = (W - (cols * w + (cols - 1) * gap)) / 2;
  const P = [];
  for (let r = 0; r < 4; r++){
    const x = x0 + (r % cols) * (w + gap), y = y0 + Math.floor(r / cols) * (h + 50);
    P.push({x, y});
    const gg = dieGlyph(svg, x, y, w, h, mix(css('--die'), css('--k-field'), .35), 'ew', {label: 'rank ' + r, fs: 13, id: 'q' + r});
    gg.setAttribute('tabindex', 0); gg.setAttribute('role', 'img'); gg.setAttribute('aria-label', `Qwen ROM die, rank ${r}`);
    gg.addEventListener('mousemove', ev => showTip(`<b>Qwen ROM die, rank ${r}</b><br>${fmt(val(DATA.dies.qwen_rom.area), 2)} mm² · 1,536 ROM tiles · 4 HBM3E stacks`, ev));
    gg.addEventListener('mouseleave', hideTip);
  }
  const ring = [[0, 1], [1, 2], [2, 3], [3, 0]];
  const yBus = Math.max(...P.map(p => p.y)) + h + 30;
  for (const [a, b] of ring){
    const A = P[a], B = P[b]; let d;
    if (A.y === B.y && Math.abs(A.x - B.x) < w + gap + 1) d = `M${Math.min(A.x, B.x) + w + 12} ${A.y + h / 2} L${Math.max(A.x, B.x) - 12} ${A.y + h / 2}`;
    else if (A.x === B.x) d = `M${A.x + w / 2} ${Math.min(A.y, B.y) + h + 4} L${A.x + w / 2} ${Math.max(A.y, B.y) - 4}`;
    else d = `M${A.x + w / 2} ${A.y + h + 4} L${A.x + w / 2} ${yBus} L${B.x + w / 2} ${yBus} L${B.x + w / 2} ${B.y + h + 4}`;
    link(lk, d, {w: lw(L.qwen_ar), ends: ['q' + a, 'q' + b], tip: linkTip(`All-reduce link, rank ${a} ↔ rank ${b}`, L.qwen_ar, '')});
  }
  sizeSvg(svg, W, yBus + 22);
  arrayRead(`<div class="eyebrow">System</div><h3>Four ROM dies, sixteen stacks</h3><dl><dt>Dies</dt><dd>4 (TP4 ranks)</dd><dt>Die area</dt><dd>${vs(DATA.dies.qwen_rom.area, 2)} mm²</dd><dt>KV fill</dt><dd>3.734 TB/s, 93.4 % of 4-stack peak</dd><dt>Token</dt><dd>${fmt0(val(DATA.rates.qwen.cycles))} cycles</dd></dl><div class="src">${pill('measured')} results/rtl/qwen_plain_ar_stream4_P8191_20261005/measured_composition.json (ranks 4); STREAM4 fill from results/arch/measured_scoreboard/README.md</div>`);
}
function drawHbmSystem(svg){
  const W = arrW(), narrow = W < 560; const L = DATA.links || {};
  linkDefs(svg);
  const lay = svgEl('g', {}, svg), lk = svgEl('g', {}, svg);
  if (state.hbmModel === 'qwen'){
    const y0 = 16 + txtWrap(lay, 14, 18, 'Qwen3-8B 8K: TP4 iso-silicon (4 tile dies) or TP2 same silicon (2 dies)', W - 28, {fs: 12}) + 20;
    const g = geo('hbm_qwen'); const cols = W >= 640 ? 4 : 2, gap = 40; const w = Math.min(150, (W - 28 - (cols - 1) * gap) / cols), h = w / (g.W / g.H);
    const x0 = (W - (cols * w + (cols - 1) * gap)) / 2;
    const rowsN = Math.ceil(4 / cols), swY = y0 + rowsN * (h + 34) + 20, swW = Math.min(220, W - 40), swX = (W - swW) / 2;
    const sw = svgEl('g', {class: 'nd', 'data-id': 'qs'}, svg);
    svgEl('rect', {x: swX, y: swY, width: swW, height: 26, fill: css('--k-link'), rx: 2}, sw);
    txt(sw, W / 2, swY + 17, 'switch / direct links', {fs: 11, anchor: 'middle', fill: css('--bg')});
    for (let r = 0; r < 4; r++){
      const x = x0 + (r % cols) * (w + gap), y = y0 + Math.floor(r / cols) * (h + 34);
      dieGlyph(svg, x, y, w, h, mix(css('--die'), css('--k-field'), .35), 'ns', {label: 'TP4 rank ' + r, id: 'qh' + r});
      const xs = x + w / 2, xe = swX + swW * (0.2 + 0.2 * r);
      const below = Math.floor(r / cols) === rowsN - 1;
      const d = below ? `M${xs} ${y + h + 12} L${xs} ${swY - 8} L${xe} ${swY - 8} L${xe} ${swY - 2}` : `M${x - 6} ${y + h / 2} L${r % cols ? x + w + 14 : x - 14} ${y + h / 2} L${r % cols ? x + w + 14 : x - 14} ${swY - 14} L${xe} ${swY - 14} L${xe} ${swY - 2}`;
      link(lk, below ? d : (r % cols ? `M${x + w + 2} ${y + h / 2} L${x + w + 14} ${y + h / 2} L${x + w + 14} ${swY - 14} L${xe} ${swY - 14} L${xe} ${swY - 2}` : d), {w: lw(L.hbm_qwen), flow: true, ends: ['qh' + r, 'qs'], tip: linkTip(`Rank ${r} link to the switch`, L.hbm_qwen, '')});
    }
    sizeSvg(svg, W, swY + 40);
    arrayRead(`<div class="eyebrow">System</div><h3>Qwen tile dies</h3><dl><dt>TP4 AR</dt><dd>${vs(DATA.rates.hbm_qwen.AR)} tok/s</dd><dt>TP2 AR</dt><dd>${vs(DATA.rates.hbm_qwen.AR_tp2)} tok/s</dd><dt>Unpriced TP4</dt><dd>${vs(DATA.rates.hbm_qwen.AR_unpriced)} tok/s</dd><dt>Die</dt><dd>${vs(DATA.dies.hbm_qwen.area, 2)} mm²</dd></dl>${srcLine(DATA.rates.hbm_qwen.AR)}`);
    return;
  }
  const n = val(DATA.hbm_system.dies), nSw = val(DATA.hbm_system.switch_chips) || 8;
  const y0 = 16 + txtWrap(lay, 14, 18, `${n} dies · TP-${n} · ${4 * n} HBM3E stacks · Tomahawk-Ultra switch tier (${nSw} chips; count is an estimate) · each die stripes its ports over every switch chip`, W - 28, {fs: 12}) + 22;
  const cols = narrow ? 12 : 16, rowsN = Math.ceil(n / cols), half = Math.ceil(rowsN / 2);
  const pitch = (W - 24) / cols, gutter = Math.max(9, pitch * 0.32), dw = pitch - gutter, dh = dw / (24401.52 / 19722.96);
  const rowP = dh + (narrow ? 16 : 22);
  const swH = narrow ? 18 : 22, swY = y0 + half * rowP + 14;
  const yBot = swY + swH + 28;
  const x0 = 12;
  // switch tier: a band with nSw chips
  const band = svgEl('rect', {x: x0, y: swY - 6, width: W - 2 * x0, height: swH + 12, fill: 'none', stroke: css('--line'), 'stroke-dasharray': '3 3', rx: 3}, svg);
  const chipW = (W - 2 * x0 - 8) / nSw;
  const chipG = [];
  for (let s = 0; s < nSw; s++){
    const g = svgEl('g', {class: 'nd sw-chip', 'data-id': 's' + s, tabindex: 0, role: 'img', 'aria-label': `Switch chip ${s}`}, svg);
    svgEl('rect', {x: x0 + 4 + s * chipW + 3, y: swY, width: chipW - 6, height: swH, fill: css('--k-link'), rx: 2}, g);
    if (chipW > 50) txt(g, x0 + 4 + s * chipW + chipW / 2, swY + swH / 2 + 4, 'TU ' + s, {fs: 10.5, anchor: 'middle', fill: css('--bg')});
    chipG.push(g);
  }
  // fan layer (shown on hover): die column foot -> every switch chip
  const fan = svgEl('g', {class: 'fan'}, svg);
  const lwU = lw(L.hbm_uplink);
  const dieEnds = [];
  const allIds = Array.from({length: nSw}, (_, s) => 's' + s);
  for (let i = 0; i < n; i++){
    const r = Math.floor(i / cols), c = i % cols, top = r < half;
    const x = x0 + c * pitch + gutter / 2, y = top ? y0 + r * rowP : yBot + (r - half) * rowP;
    const id = 'hd' + i; dieEnds.push(id);
    const gg = dieGlyph(svg, x, y, dw, dh, mix(css('--die'), css('--k-field'), .35), 'ns', {id});
    gg.setAttribute('tabindex', 0); gg.setAttribute('role', 'img'); gg.setAttribute('aria-label', `HBM accelerator die ${i}`);
    // uplink: a short stub into the right-hand gutter, then down (or up) the gutter to the switch band. Each row uses its own lane in the gutter.
    const nLane = half, lane = top ? (half - 1 - r) : (r - half);
    const gxL = x + dw + 2 + (gutter - 4) * (lane + 0.5) / nLane;
    const ym = y + dh / 2;
    const yEnd = top ? swY - 1 : swY + swH + 1;
    const d = `M${x + dw + 1} ${ym} L${gxL} ${ym} L${gxL} ${yEnd}`;
    const sC = Math.min(nSw - 1, Math.floor((gxL - x0 - 4) / chipW));
    const lkG = link(lk, d, {w: Math.max(1.6, Math.min(lwU, (gutter - 4) / nLane - 0.6)), flow: true, ends: [id].concat(allIds), tip: linkTip(`Die ${i} uplink`, L.hbm_uplink, `striped over all ${nSw} switch chips; lands on TU ${sC} here`)});
    const showFan = on => { clear(fan); if (!on) return; for (let s = 0; s < nSw; s++){ const cx = x0 + 4 + s * chipW + chipW / 2; svgEl('path', {d: `M${gxL} ${yEnd} L${cx} ${top ? swY + 3 : swY + swH - 3}`, class: 'fan-line'}, fan); } };
    lkG.addEventListener('mouseenter', () => showFan(true)); lkG.addEventListener('mouseleave', () => showFan(false));
    gg.addEventListener('mouseenter', () => { showFan(true); lkG.classList.add('hot'); hotIds(svg, allIds, true); });
    gg.addEventListener('mouseleave', () => { showFan(false); lkG.classList.remove('hot'); hotIds(svg, allIds, false); hideTip(); });
    gg.addEventListener('mousemove', ev => showTip(`<b>Die ${i}</b> · TP-${n} rank ${i}<br>${fmt(val(DATA.dies.hbm_ds.area), 1)} mm² · 4 HBM3E stacks<br>uplink striped over ${nSw} switch chips`, ev));
    gg.addEventListener('focus', () => { lkG.classList.add('hot'); hotIds(svg, allIds, true); }); gg.addEventListener('blur', () => { lkG.classList.remove('hot'); hotIds(svg, allIds, false); });
  }
  chipG.forEach((g, s) => {
    g.addEventListener('mouseenter', () => { svg.querySelectorAll('.lk').forEach(l => l.classList.add('hot')); hotIds(svg, dieEnds.concat(['s' + s]), true); });
    g.addEventListener('mouseleave', () => { svg.querySelectorAll('.lk').forEach(l => l.classList.remove('hot')); hotIds(svg, dieEnds.concat(['s' + s]), false); hideTip(); });
    g.addEventListener('mousemove', ev => showTip(`<b>Switch chip ${s}</b> · Tomahawk-Ultra class<br>every die has a port here (striped crossing)<br>${vs(DATA.hbm_system.switch)}`, ev));
  });
  const H = yBot + (rowsN - half) * rowP + 4;
  sizeSvg(svg, W, H);
  arrayRead(`<div class="eyebrow">System</div><h3>${n} dies around a switch tier</h3><dl><dt>Dies</dt><dd>${vs(DATA.hbm_system.dies, 0)}</dd><dt>Switch</dt><dd>${vs(DATA.hbm_system.switch)}</dd><dt>Uplink</dt><dd>${L.hbm_uplink ? vs(L.hbm_uplink, 0) + ' ' + esc(L.hbm_uplink.unit) : '—'}</dd><dt>TU share of AR</dt><dd>${vs(DATA.hbm_system.tu_budget_share, 4)}</dd><dt>Die wire added</dt><dd>${vs(DATA.rates.hbm_ds.wire_us, 3)} µs</dd></dl>${srcLine(DATA.hbm_system.dies)}${srcLine(DATA.hbm_system.switch)}${L.hbm_uplink ? srcLine(L.hbm_uplink) : ''}`);
}

/* ================================================================ 2. RACK */
/* Elevation drawn to scale (ORv3 OpenU = 48 mm, 44 OU, 600 mm frame) with the deployment's racks side by side;
   packages inside a tray are drawn schematically on the elevation and to scale in the tray plan. */
const RK_KIND = { power: ['Power shelf', '--busbar'], stage: ['Stage tray (2 stages × TP4)', '--k-field'], head: ['Head tray', '--k-tree'], table: ['Engram table tray', '--k-index'],
  draft: ['Draft tray (DP1-EP5)', '--k-attn'], compute: ['Compute tray', '--k-field'], qtray: ['Qwen TP4 tray', '--k-field'], switch: ['Switch tray', '--k-link'], host: ['Host', '--k-ctrl'], mgmt: ['Management', '--k-res'] };
const rackState = { tray: null, rack: 0 };
function rackW(){ const s = $('rackScroll'); return Math.max(280, Math.floor((s && s.clientWidth) || 900)); }
function rkData(){ return state.design === 'ds' ? DATA.racks.ds : state.design === 'hbm' ? DATA.racks.hbm : DATA.racks.qwen; }
function trayList(){ const out = []; val(rkData().racks).forEach((rk, ri) => rk.rows.forEach(r => { if (r.pk) out.push({ri, row: r, rk}); })); return out; }
function dieRole(p, id){
  if (p.r === 'stage'){ const m = /s(\d+)r(\d+)/.exec(id); return `stage ${m[1]} rank ${m[2]}`; }
  return ({head: 'head die ', table: 'Engram table die ', draft: 'draft die ', hbm: 'HBM accelerator die ', qwen: 'Qwen ROM rank '})[p.r] + id.replace(/^[a-z]/, '');
}
function trayDies(row){ return row.pk.map(p => p.d.map(id => dieRole(p, id)).join(', ')).join('; '); }
function stageSpan(rk){ const ss = []; rk.rows.forEach(r => (r.pk || []).forEach(p => { if (p.s != null) ss.push(p.s); })); return ss.length ? `S${Math.min(...ss)}–S${Math.max(...ss)}` : ''; }
function renderRack(){
  const d = state.design, RD = rkData(), F = DATA.racks.frame, R = DATA.rates;
  const racks = val(RD.racks), C = val(RD.counts);
  const sum = k => racks.reduce((a, r) => a + r[k], 0);
  const lede = { ds: `The ${C.stages}-stage pipeline (q-element frame) packed into Open Rack v3 racks with liquid-cooled 1 OU trays of four two-die packages, two pipeline stages a tray. ${racks.length} racks hold ${fmt0(C.dies)} dies. Two stages share a tray; the chain runs down R1 and up R2 with one rack crossing, the head trays sit beside stage 0 and the draft trays beside the head. Every off-package link runs full RS(544,514) FEC. Packing from the committed rack record on the legacy rack study's tray, power and cable template.`,
    hbm: `The HBM accelerator's ${fmt0(C.dies)} dies in ${C.packages} two-die packages, four packages a liquid-cooled 1 OU tray, around one Tomahawk-Ultra tier of ${C.switch_chips} switch chips. Every package stripes ${C.ports_per_package} ports of 800G over the switch chips, so each collective is one or two switch crossings.`,
    qwen: 'The Qwen ROM TP4 group is two two-die packages on one tray: a rack holds many independent groups, and one is drawn. Shown for scale beside the two array machines.' }[d];
  $('rackLede').textContent = lede;
  // KPI row
  const kv = (label, v, unit, x) => `<div class="kpi"><div class="k"><span>${esc(label)}</span>${pill(st(x))}</div><div class="v num">${v}<small>${esc(unit)}</small></div></div>`;
  const rateX = d === 'ds' ? R.ds.MTP : d === 'hbm' ? R.hbm_ds.AR : R.qwen.AR;
  $('rackKpis').innerHTML = kv('Racks', racks.length, d === 'qwen' ? ' (one group)' : '', RD.racks) + kv('Dies', fmt0(C.dies), '', RD.counts) + kv('Packages', fmt0(C.packages), '', RD.counts) +
    kv('Provisioned', fmt(sum('prov_kw'), 1), 'kW', RD.racks) + kv('Per user', vs(rateX, 0), d === 'ds' ? 'tok/s MTP' : 'tok/s AR', rateX);
  // tools: tray kinds legend and selection hint
  $('rackTools').innerHTML = `<span class="muted" style="font-size:12px">${racks.length > 1 ? racks.length + ' racks side by side · ' : ''}to scale: ${vs(F.ou_mm, 0)} mm OpenU, ${vs(F.usable_ou, 0)} OU · hover a tray for its dies, click it for its plan, click a die to open it below</span>`;
  const kinds = [...new Set(racks.flatMap(r => r.rows.map(x => x.kind)))];
  $('rackLegend').innerHTML = kinds.map(k => `<span><i class="sw" style="background:var(${RK_KIND[k][1]})"></i>${esc(RK_KIND[k][0])}</span>`).join('') +
    `<span><i class="sw" style="background:var(--cool-sup)"></i>coolant supply</span><span><i class="sw" style="background:var(--cool-ret)"></i>coolant return</span><span><i class="sw lk-sw" style="height:3px"></i>${d === 'ds' ? 'token path (stage hops)' : d === 'hbm' ? 'switch uplinks' : 'all-reduce'}</span>`;
  drawRack();
  rackTables();
}
function drawRack(){
  const svg = $('rackSvg'); clear(svg); linkDefs(svg);
  const d = state.design, RD = rkData(), F = DATA.racks.frame; const racks = val(RD.racks);
  const W = rackW(), narrow = W < 640;
  const OU = val(F.ou_mm), NOU = d === 'qwen' ? racks[0].used_ou + 1 : val(F.usable_ou), frameW = 600, bayW = val(F.width_mm);
  // scale: the elevation height is fixed in px; width follows the real 600 mm frame
  const plan = W >= 820; // tray plan beside the racks when wide, below when narrow
  const availW0 = (W >= 820) ? W * 0.6 : W, nR = racks.length, gap0 = narrow ? 34 : 56;
  const k = Math.min((d === 'qwen' ? Math.min(220, NOU * 26) : (narrow ? 520 : 600)) / (NOU * OU), (availW0 - 28 - 30 - (nR - 1) * gap0) / (nR * frameW)); // px per mm
  const elevH = k * NOU * OU;
  let rw = frameW * k; const gap = narrow ? 34 : 56, sideL = 28;
  const availW = plan ? W * 0.6 : W;
  let n = racks.length; let rackX0 = sideL + (availW - sideL - (n * rw + (n - 1) * gap)) / 2;
  if (rackX0 < sideL){ rackX0 = sideL; }
  const y0 = 30;
  const lay = svgEl('g', {}, svg), body = svgEl('g', {}, svg), lk = svgEl('g', {}, svg);
  txt(lay, 8, 16, d === 'qwen' ? 'Elevation (to scale): one TP4 tray' : `Elevation (to scale) · ${racks.length} rack${racks.length > 1 ? 's' : ''}, ORv3 ${val(F.usable_ou)} OU`, {fs: 12});
  const centers = {}; // stage -> [x,y]
  const trayPos = [];
  racks.forEach((rk, ri) => {
    const x = rackX0 + ri * (rw + gap), y = y0;
    svgEl('rect', {x: x - 4, y: y - 4, width: rw + 8, height: elevH + 8, fill: 'none', stroke: css('--rk-frame'), 'stroke-width': 2.5, rx: 2}, body);
    const bx = x + (frameW - bayW) / 2 * k, bw = bayW * k;
    svgEl('rect', {x: bx, y, width: bw, height: elevH, fill: css('--rk-slot')}, body);
    txt(lay, x + rw / 2, y + elevH + 18, rk.name + (stageSpan(rk) ? ' · ' + stageSpan(rk) : ''), {fs: 11.5, anchor: 'middle', fill: css('--ink'), weight: 600});
    txt(lay, x + rw / 2, y + elevH + 32, `${rk.used_ou}/${val(F.usable_ou)} OU · ${fmt(rk.prov_kw, 1)} kW`, {fs: 10, anchor: 'middle'});
    // busbar (left rail) and liquid manifolds (right rails)
    svgEl('rect', {x: x - 3, y, width: 2.5, height: elevH, fill: css('--busbar')}, body);
    const ms = x + rw + 3, mr = x + rw + 8;
    svgEl('line', {x1: ms, y1: y - 2, x2: ms, y2: y + elevH, class: 'cool-sup', 'stroke-width': 2.5}, body);
    svgEl('line', {x1: mr, y1: y - 2, x2: mr, y2: y + elevH, class: 'cool-ret', 'stroke-width': 2.5}, body);
    rk.rows.forEach(row => {
      const ry = y + elevH - (row.ou - 1 + row.h) * OU * k, rh = row.h * OU * k;
      const col = css(RK_KIND[row.kind][1]);
      const g = svgEl('g', row.pk ? {class: 'nd rk-tray' + (rackState.tray && rackState.tray.ri === ri && rackState.tray.ou === row.ou ? ' sel' : ''), 'data-id': `t${ri}_${row.ou}`, tabindex: 0, role: 'button', 'aria-label': `${rk.name} OU ${row.ou}: ${row.label}`} : {class: 'nd', 'data-id': `s${ri}_${row.ou}`}, body);
      svgEl('rect', {x: bx + 0.5, y: ry + 0.5, width: bw - 1, height: Math.max(1, rh - 1), fill: mix(css('--die'), col, row.pk ? .22 : .55), stroke: col, 'stroke-width': 0.8}, g);
      if (row.pk){
        // packages drawn schematically along the tray front: dies in field colour, HBM ticks
        const np = row.pk.length, pw = (bw - 8) / 4;
        row.pk.forEach((p, i) => {
          const px = bx + 4 + i * pw + 1, ph = Math.max(2, rh - 3);
          const dw = (pw - 4) / p.d.length;
          p.d.forEach((id, j) => svgEl('rect', {x: px + 1 + j * dw, y: ry + 1.5, width: dw - 1, height: ph - 0.5, fill: col, opacity: .85}, g));
        });
        if (row.kind !== 'power'){ svgEl('line', {x1: bx + bw, y1: ry + rh * 0.35, x2: ms, y2: ry + rh * 0.35, class: 'cool-sup', 'stroke-width': 1}, body); svgEl('line', {x1: bx + bw, y1: ry + rh * 0.7, x2: mr, y2: ry + rh * 0.7, class: 'cool-ret', 'stroke-width': 1}, body); }
        row.pk.forEach(p => { if (p.s != null) centers[p.s] = [bx + 6, ry + rh / 2]; });
        trayPos.push({ri, row, x: bx, y: ry, w: bw, h: rh});
        g.addEventListener('mousemove', ev => showTip(`<b>${esc(rk.name)} · OU ${row.ou}</b> · ${esc(row.label)}<br>${row.pk.length} packages · ${row.pk.reduce((a, p) => a + p.d.length, 0)} dies · ${fmt(row.w, 0)} W chips<br>${esc(trayDies(row)).slice(0, 420)}`, ev));
        g.addEventListener('mouseleave', hideTip);
        keyActivate(g, () => { rackState.tray = {ri, ou: row.ou}; drawRack(); const n2 = $('rackSvg').querySelector(`[data-id="t${ri}_${row.ou}"]`); if (n2) n2.focus(); });
      } else {
        if (rh >= 9 && bw > 70) txt(g, bx + 4, ry + rh / 2 + 3.5, row.label.split(' (')[0].slice(0, Math.floor(bw / 5.4)), {fs: 8.5, fill: css('--ink')});
        g.addEventListener('mousemove', ev => showTip(`<b>${esc(rk.name)} · OU ${row.ou}${row.h > 1 ? '–' + (row.ou + row.h - 1) : ''}</b><br>${esc(row.label)}`, ev));
        g.addEventListener('mouseleave', hideTip);
      }
    });
    // OU ruler every 10 OU
    for (let u = 0; u <= NOU; u += 10) txt(lay, x + rw + 12, y + elevH - u * OU * k + 3, String(u), {fs: 8.5});
  });
  // overlays: the token path through the stage trays (DS), switch uplinks (HBM), the all-reduce (Qwen)
  const L = DATA.links || {};
  if (d === 'ds'){
    const C = val(RD.counts); let path = '';
    for (let s = 0; s < C.stages; s++){ const c = centers[s]; if (!c) continue; path += (path ? ' L' : 'M') + c[0] + ' ' + c[1]; }
    link(lk, path, {w: lw(L.ds_stage), hit: 6, flow: true, tip: linkTip('Token path through the stage trays', L.ds_stage, `${val(RD.hops).tray} hops inside a tray, ${val(RD.hops).rack} tray to tray, ${val(RD.hops).cross} rack to rack`)});
    // token return: last stage back to the head tray
    const head = trayPos.find(t => t.row.kind === 'head'); const last = centers[C.stages - 1];
    if (head && last){ const hx = head.x + head.w / 2, hy = head.y + head.h / 2; const ym = y0 + elevH + 44; link(lk, `M${last[0]} ${last[1]} L${last[0]} ${ym} L${hx} ${ym} L${hx} ${hy}`, {w: 2, dash: '5 4', tip: linkTip('Head hop: last stage to the head dies (rack to rack)', null, `head hop ${esc(val(DATA.ds_system.head_hop))}; token return (head → S0, beside it in R1) ${vs(DATA.ds_system.token_return_us, 3)} µs measured, full FEC`)}); }
  } else if (d === 'hbm'){
    const sw = racks[0].rows.filter(r => r.kind === 'switch');
    const rk = racks[0], x = rackX0, bx = x + (frameW - bayW) / 2 * k;
    const trunkX = rackX0 + rw + 18;
    const swY = sw.map(r => y0 + elevH - (r.ou - 1 + r.h / 2) * OU * k);
    trayPos.forEach((t, i) => {
      const yy = t.y + t.h / 2;
      link(lk, `M${t.x + t.w * 0.15} ${yy} L${t.x - 10 - (i % 3) * 3} ${yy} L${t.x - 10 - (i % 3) * 3} ${swY[i % swY.length]} L${t.x + 2} ${swY[i % swY.length]}`,
        {w: Math.min(3.2, lw(L.hbm_uplink) * 0.7), ends: [`t0_${t.row.ou}`].concat(sw.map(r => `s0_${r.ou}`)), tip: linkTip(`Compute tray at OU ${t.row.ou}: ${t.row.pk.length * 8} ports of 800G`, L.hbm_uplink, 'each package stripes 8 ports over all switch chips; drawn as one bundle per tray')});
    });
  } else {
    const t = trayPos[0]; if (t){ link(lk, `M${t.x + t.w * 0.3} ${t.y + t.h / 2} L${t.x + t.w * 0.7} ${t.y + t.h / 2}`, {w: lw(L.qwen_ar), tip: linkTip('TP4 all-reduce between the two packages', L.qwen_ar, '406.6 ns per all-reduce, 72 a token')}); }
  }
  let H = y0 + elevH + (d === 'ds' ? 56 : 42);
  // tray plan to scale (top view): 533 x depth mm, packages 85 x 85 mm with two dies and eight stacks, cold-plate loop
  const tl = trayList(); if (!rackState.tray && tl.length){ const t0 = tl.find(t => t.row.kind === 'stage' || t.row.kind === 'compute' || t.row.kind === 'qtray') || tl[0]; rackState.tray = {ri: t0.ri, ou: t0.row.ou}; }
  const sel = tl.find(t => rackState.tray && t.ri === rackState.tray.ri && t.row.ou === rackState.tray.ou);
  if (sel){
    const px0 = plan ? availW + 10 : 10, pyy = plan ? y0 : H + 10, pW = plan ? W - availW - 20 : W - 20;
    const depth = val(F.depth_mm), bay = val(F.width_mm); const kk = Math.min(pW / bay, (plan ? elevH * 0.85 : 360) / depth);
    const tw = bay * kk, th = depth * kk, tx = px0 + (pW - tw) / 2, ty = pyy + 34;
    txt(lay, px0, pyy + 12, `Tray plan (to scale): ${val(rkData().racks)[sel.ri].name} OU ${sel.row.ou}`, {fs: 12, fill: css('--ink'), weight: 600});
    txt(lay, px0, pyy + 26, `${fmt0(bay)} × ${fmt0(depth)} mm · front at the bottom · click a die`, {fs: 10.5});
    svgEl('rect', {x: tx, y: ty, width: tw, height: th, fill: css('--surface-2'), stroke: css('--rk-frame'), 'stroke-width': 1.5, rx: 3}, svg);
    const pk = val(F.package_mm)[0], dm = val(F.die_mm), hm = val(F.hbm_mm)[0];
    const np = sel.row.pk.length, cols = 2, rowsP = Math.ceil(np / cols);
    const col = css(RK_KIND[sel.row.kind][1]);
    // cold-plate loop
    const loop = [];
    sel.row.pk.forEach((p, i) => {
      const cx = tx + tw * (i % cols === 0 ? 0.3 : 0.7), cy = ty + th * (0.28 + 0.36 * Math.floor(i / cols)) ;
      loop.push([cx, cy]);
    });
    if (loop.length){ // supply and return manifolds along the rear (right) edge, one branch pair per package cold plate
      const xs = tx + tw - 10, xr = tx + tw - 18, half = pk * kk / 2;
      svgEl('line', {x1: xs, y1: ty + 6, x2: xs, y2: ty + th - 6, class: 'cool-sup', 'stroke-width': 3}, svg);
      svgEl('line', {x1: xr, y1: ty + 6, x2: xr, y2: ty + th - 6, class: 'cool-ret', 'stroke-width': 3}, svg);
      loop.forEach(c => { svgEl('path', {d: `M${xs} ${c[1] - half * 0.5} H${c[0] - half - 3} V${c[1]}`, class: 'cool-sup', fill: 'none', 'stroke-width': 1.6, 'stroke-dasharray': '4 2'}, svg); svgEl('path', {d: `M${xr} ${c[1] + half * 0.5} H${c[0] + half + 3}`, class: 'cool-ret', fill: 'none', 'stroke-width': 1.6, 'stroke-dasharray': '4 2'}, svg); }); }
    sel.row.pk.forEach((p, i) => {
      const [cx, cy] = loop[i]; const s = pk * kk; const x = cx - s / 2, y = cy - s / 2;
      svgEl('rect', {x, y, width: s, height: s, fill: css('--die'), stroke: css('--die-edge'), 'stroke-width': 1, rx: 2}, svg);
      // two dies side by side (rotated to portrait), the die's HBM stacks (p.k, default four) on its outer edge
      const dW = dm[0] * kk, dH = dm[1] * kk, gapD = 1.5 * kk;
      p.d.forEach((id, j) => {
        const dx = cx - (p.d.length * dW + (p.d.length - 1) * gapD) / 2 + j * (dW + gapD), dy = cy - dH / 2;
        const g = svgEl('g', {class: 'rk-die', tabindex: 0, role: 'button', 'aria-label': `Open ${dieRole(p, id)} in The die`}, svg);
        svgEl('rect', {x: dx, y: dy, width: dW, height: dH, fill: mix(css('--die'), col, .6), stroke: css('--die-edge'), 'stroke-width': .8}, g);
        if (dW > 26) txt(g, dx + dW / 2, dy + dH / 2 + 3, id, {fs: Math.min(10, dW / 4), anchor: 'middle', fill: css('--ink')});
        g.addEventListener('mousemove', ev => showTip(`<b>${esc(dieRole(p, id))}</b><br>package ${p.id} · ${esc(val(rkData().racks)[sel.ri].name)} OU ${sel.row.ou}<br>click to open this die in The die`, ev));
        g.addEventListener('mouseleave', hideTip);
        keyActivate(g, () => jumpToDie(`${dieRole(p, id)} · ${val(rkData().racks)[sel.ri].name}, OU ${sel.row.ou}, package ${p.id}`));
        for (let q = 0; q < (p.k ?? 4); q++){ const hx = j === 0 ? dx - hm * kk - 1 : dx + dW + 1; svgEl('rect', {x: hx, y: dy + q * (dH / 4) + 0.5, width: hm * kk, height: Math.min(hm * kk, dH / 4 - 1), fill: css('--k-hbm')}, svg); }
      });
    });
    txt(lay, tx, ty + th + 14, `${np} packages · ${fmt0(pk)} mm · ${fmt(sel.row.w, 0)} W of chips`, {fs: 10.5});
    H = Math.max(H, ty + th + 24);
    renderRackRead(sel);
  }
  sizeSvg(svg, W, H);
}
function renderRackRead(sel){
  const RD = rkData(), F = DATA.racks.frame, rk = val(RD.racks)[sel.ri];
  const dies = sel.row.pk.reduce((a, p) => a + p.d.length, 0);
  const lim = val(F.cooling_limit_w);
  $('rackRead').innerHTML = `<div class="eyebrow">${esc(rk.name)} · OU ${sel.row.ou} · ${esc(RK_KIND[sel.row.kind][0])}</div><h3>${esc(sel.row.label)}</h3>
    <dl><dt>Packages</dt><dd>${sel.row.pk.length}</dd><dt>Dies</dt><dd>${dies}</dd>${sel.row.stacks != null ? `<dt>HBM3E stacks</dt><dd>${sel.row.stacks} (${esc(sel.row.pk.map(p => p.k).join('/'))} a die)</dd>` : ''}<dt>Chip power</dt><dd>${fmt(sel.row.w, 0)} W</dd>
    <dt>Per die</dt><dd>${fmt(sel.row.w / dies, 1)} W of ${fmt0(lim)} W liquid limit</dd><dt>At the wall</dt><dd>${fmt(sel.row.w * val(F.wall_factor), 0)} W</dd></dl>
    <div class="eyebrow" style="margin-top:12px">Dies on this tray</div><p style="font-size:12.5px;margin-top:4px">${esc(trayDies(sel.row))}</p>
    <div class="eyebrow" style="margin-top:12px">Rack ${esc(rk.name)}</div>
    <dl><dt>Used</dt><dd>${rk.used_ou} OU · ${rk.trays} trays</dd><dt>Dies</dt><dd>${fmt0(rk.dies)} in ${rk.packages} packages</dd><dt>Power</dt><dd>${fmt(rk.chips_kw, 1)} kW chips · ${fmt(rk.prov_kw, 1)} kW provisioned</dd><dt>Shelves</dt><dd>${rk.shelves} (2N)</dd><dt>Mass</dt><dd>~${fmt0(rk.kg)} kg</dd></dl>
    ${srcLine(RD.racks)}${RD.die_w ? srcLine(RD.die_w) : ''}`;
}
function rackTables(){
  const d = state.design, RD = rkData(), racks = val(RD.racks), R = DATA.rates;
  const rows = racks.map(r => `<tr><td class="mono">${esc(r.name)}</td><td>${esc(stageSpan(r) || r.rows.filter(x => x.pk).map(x => RK_KIND[x.kind][0]).filter((v, i, a) => a.indexOf(v) === i).join(', '))}</td><td class="n">${r.used_ou}</td><td class="n">${r.packages}</td><td class="n">${fmt0(r.dies)}</td><td class="n">${fmt(r.chips_kw, 1)}</td><td class="n">${fmt(r.prov_kw, 1)}</td><td class="n">${fmt0(r.kg)}</td></tr>`).join('');
  const tot = k => racks.reduce((a, r) => a + r[k], 0);
  const linkBW = d === 'ds' ? `stage hop ${vs(DATA.links.ds_stage, 0)} GB/s ${pill(st(DATA.links.ds_stage))}` : d === 'hbm' ? `switch fabric ${vs(RD.fabric_tbps, 1)} Tb/s ${pill(st(RD.fabric_tbps))}` : `all-reduce link ${vs(DATA.links.qwen_ar, 0)} GB/s ${pill(st(DATA.links.qwen_ar))}`;
  const ctx = d === 'ds' ? `One user's token crosses all ${racks.length} racks: ${vs(R.ds.AR, 0)} tok/s AR, ${vs(R.ds.MTP, 0)} tok/s MTP per user; all users together saturate at ~${vs(RD.sat_tok_s, 0)} tok/s ${pill(st(RD.sat_tok_s))}. Model system power ${val(RD.system_kw).ar} kW AR, ${val(RD.system_kw).mtp} kW MTP ${pill(st(RD.system_kw))} (the rack sums charge every layer die at the busiest die's saturated power).`
    : d === 'hbm' ? `${vs(R.hbm_ds.AR_unified, 0)} tok/s AR, ${vs(R.hbm_ds.MTP_unified, 0)} tok/s MTP per user at 1M (candidate, with die closure costs). Model system power ${val(RD.system_kw).ar} kW at AR ${pill(st(RD.system_kw))}; the rack sum charges every die its in-phase peak.`
    : `${vs(R.qwen.AR, 0)} tok/s per user at 8K on ${val(RD.system_kw).ar} kW ${pill(st(RD.system_kw))}.`;
  const nv = val(DATA.racks.nvl72);
  $('rackTable').innerHTML = `<thead><tr><th>Rack</th><th>Holds</th><th class="n">OU</th><th class="n">Pkgs</th><th class="n">Dies</th><th class="n">Chips kW</th><th class="n">Prov. kW</th><th class="n">kg</th></tr></thead><tbody>${rows}${racks.length > 1 ? `<tr><td><b>Total</b></td><td></td><td class="n">${tot('used_ou')}</td><td class="n">${tot('packages')}</td><td class="n">${fmt0(tot('dies'))}</td><td class="n">${fmt(tot('chips_kw'), 1)}</td><td class="n">${fmt(tot('prov_kw'), 1)}</td><td class="n">${fmt0(tot('kg'))}</td></tr>` : ''}
    <tr><td class="muted">NVL72</td><td class="muted">GB200 rack, published ${pill(st(DATA.racks.nvl72))}</td><td class="n muted">—</td><td class="n muted">${nv.gpus}</td><td class="n muted">${nv.gpus * 2}</td><td class="n muted">—</td><td class="n muted">${nv.kw}</td><td class="n muted">${fmt0(nv.kg)}</td></tr></tbody>`;
  $('rackSrc').innerHTML = `${linkBW}. ${ctx}<br>${esc(RD.racks.note || '')} ${pill(st(RD.racks))} ${esc(RD.racks.src)}`;
  const lc = val(RD.links);
  $('linkTable').innerHTML = `<thead><tr><th>Class</th><th>Carries</th><th>Medium</th><th class="n">ns / hop</th><th class="n">GB/s</th><th>Status</th></tr></thead><tbody>${lc.map(l => `<tr title="${esc(l.src)}"><td class="mono" style="white-space:nowrap">${esc(l.cls)}</td><td>${esc(l.what)}</td><td>${esc(l.medium)}</td><td class="n">${l.ns == null ? '—' : fmt(l.ns, 1) + (l.ns_hi ? '–' + fmt(l.ns_hi, 0) : '')}</td><td class="n">${l.GBps == null ? '—' : fmt0(l.GBps)}</td><td>${pill(l.st)}</td></tr>`).join('')}</tbody>`;
  if (d === 'ds'){ const h = val(RD.hops); const f = val(RD.fec); $('linkNote').innerHTML = `Stage hops in this packing: <b>${h.tray}</b> inside a tray, <b>${h.rack}</b> tray to tray, <b>${h.cross}</b> rack to rack (the minimum for ${val(RD.counts).stages} stages at two a tray), plus the head hop and the token return ${pill(st(RD.hops))}. Owner baseline (2026-10-06): every off-package link runs full RS(544,514) FEC, board and cable alike; no light FEC anywhere. Each hop is the measured ${fmt(f.hop_us, 4)} µs full-FEC hop (was ${fmt(f.hop_light_us_was, 4)} µs on light FEC), every TP4 collective +${f.coll_delta_cycles} cycles, and the cable flight beyond 0.3 m adds ${fmt(f.cable_flight_us, 3)} µs a token. Against the superseded light-FEC row: DS ROM ${fmt(f.d_AR_tok_s, 1)} tok/s AR (+${fmt(f.d_AR_us, 2)} µs), ${fmt(f.d_MTP_tok_s, 1)} tok/s MTP; the HBM accelerator pays +${fmt(f.hbm_d_us, 2)} µs over ${f.hbm_crossings} switch crossings ${pill(st(RD.fec))}.`; }
  else $('linkNote').innerHTML = esc(RD.links.src);
}
function jumpToDie(label){
  state.dieCtx = label;
  if (state.design === 'hbm' && state.hbmModel !== 'ds'){ state.hbmModel = 'ds'; lsSet('hbmModel', 'ds'); dieTools(); }
  state.sel = null; drawDie();
  $('die').scrollIntoView({behavior: reduceMotion ? 'auto' : 'smooth', block: 'start'});
  $('dieCanvas').focus({preventScroll: true});
}

/* ================================================================ 2. DIE (canvas) */
const dieView = { s: 1, ox: 0, oy: 0, W: 0, H: 0 };
function dieTools(){
  const dk = dieKey(); const G = geo(dk); const D = DATA.dies[dk];
  const cats = [...new Set(G.items.map(i => i.cat))];
  const hasClock = dk === 'hbm_ds'; const hasIR = dk === 'hbm_ds' || dk === 'qwen_rom';
  const dieSel = state.design === 'hbm' ? `<div class="seg" role="group" aria-label="Die"><button type="button" data-hm="ds" aria-pressed="${state.hbmModel === 'ds'}">DS die</button><button type="button" data-hm="qwen" aria-pressed="${state.hbmModel === 'qwen'}">Qwen tile die</button></div>` : '';
  $('dieTools').innerHTML = `${dieSel}<div class="seg" role="group" aria-label="Colour by"><button type="button" data-cb="kind" aria-pressed="${state.colorBy === 'kind'}">Block kind</button><button type="button" data-cb="closure" aria-pressed="${state.colorBy === 'closure'}">Closure</button></div>
    <button type="button" class="chip" data-ly="wire" aria-pressed="${state.showWire}">Wire stations</button>
    ${hasClock ? `<button type="button" class="chip" data-ly="clock" aria-pressed="${state.showClock}">Clock regions</button>` : ''}
    ${hasIR ? `<button type="button" class="chip" data-ly="ir" aria-pressed="${state.showIR}">IR drop windows</button>` : ''}
    <div class="seg" role="group" aria-label="Zoom" style="margin-left:auto"><button type="button" data-z="1" aria-pressed="${state.zoom === 1}">1×</button><button type="button" data-z="2" aria-pressed="${state.zoom === 2}">2×</button><button type="button" data-z="4" aria-pressed="${state.zoom === 4}">4×</button></div>`;
  $('dieTools').querySelectorAll('[data-hm]').forEach(b => b.onclick = () => { state.hbmModel = b.dataset.hm; lsSet('hbmModel', state.hbmModel); state.sel = null; renderAll(); });
  $('dieTools').querySelectorAll('[data-cb]').forEach(b => b.onclick = () => { state.colorBy = b.dataset.cb; dieTools(); drawDie(); });
  $('dieTools').querySelectorAll('[data-z]').forEach(b => b.onclick = () => { state.zoom = +b.dataset.z; dieTools(); drawDie(); });
  $('dieTools').querySelectorAll('[data-ly]').forEach(b => b.onclick = () => { const k = b.dataset.ly; if (k === 'wire') state.showWire = !state.showWire; if (k === 'clock') state.showClock = !state.showClock; if (k === 'ir') state.showIR = !state.showIR; dieTools(); drawDie(); });
  // legend
  if (state.colorBy === 'kind'){
    $('dieLegend').innerHTML = CATS.filter(c => cats.includes(c[0])).map(c => `<button type="button" class="chip" data-cat="${c[0]}" aria-pressed="${!state.hidden.has(c[0])}"><i class="sw" style="background:var(${c[2]})"></i>${esc(c[1])}</button>`).join('') + '<span class="muted">Click a kind to hide it.</span>';
    $('dieLegend').querySelectorAll('[data-cat]').forEach(b => b.onclick = () => { const c = b.dataset.cat; state.hidden.has(c) ? state.hidden.delete(c) : state.hidden.add(c); dieTools(); drawDie(); });
  } else {
    $('dieLegend').innerHTML = Object.keys(CLOSVAR).map(c => `<span><i class="sw" style="background:${c === 'reservation' ? 'transparent' : 'var(' + CLOSVAR[c] + ')'};${c === 'reservation' ? 'border:1.5px dashed var(--s-res)' : ''}"></i>${esc(CLOSURE_LABEL[c])}</span>`).join('');
  }
  const lede = { qwen_rom: 'The r17b Qwen ROM die drawn from its placement: 1,536 ROM tiles in four quadrants with a corridor station beside each, a centre spine of vector, sequencing and band slabs, HBM3E PHYs on the east and west edges with their controller bands and the 128-frame CDC column.',
    ds_s81_layer: 'One S81 layer die drawn from the generator: 128 column frames of ROM element pairs (blue; each pair sits over its row of seven configuration ROMs, drawn as texture) with their ragged return trees, a 2.6 mm centre spine, and HBM3E bands on the north and south edges.',
    hbm_ds: 'The r14b HBM accelerator die: four stacks on the long edges, each feeding a group of eight SMs; the hub band carries the SU, SFU, HC and index quarters and four quadrants of 16 attention tiles; the centre spine carries control, collectives and the multicast root. SerDes sit at the north and south edge centres.',
    hbm_qwen: 'The Qwen3-8B tile die of the HBM accelerator: 96 columns × 16 rows of W12 matrix tiles with column heads, a centre spine of core, scale and port slices, and four HBM3E PHYs.' }[dk];
  $('dieLede').innerHTML = esc(lede) + ` ${pill(st(D.geo))}`;
}
function sizeCanvas(cv, W, H, maxW){
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const scroll = cv.parentElement; const avail = Math.max(320, scroll.clientWidth - 2);
  let cssW = Math.min(maxW || 99999, avail) * state.zoom; cssW = Math.min(cssW, 6000);
  const s = cssW / W; const cssH = H * s;
  const px = Math.min(dpr, 8192 / Math.max(cssW, cssH));
  cv.width = Math.round(cssW * px); cv.height = Math.round(cssH * px); cv.style.width = cssW + 'px'; cv.style.height = cssH + 'px';
  const ctx = cv.getContext('2d'); ctx.setTransform(px, 0, 0, px, 0, 0);
  return { ctx, s, cssW, cssH };
}
function heat(mv){ const t = Math.max(0, Math.min(1, mv / 35)); return t < .5 ? mix(css('--heat-lo'), css('--heat-mid'), t * 2) : mix(css('--heat-mid'), css('--heat-hi'), (t - .5) * 2); }
function drawDie(){
  const dk = dieKey(); const G = geo(dk); const cv = $('dieCanvas');
  const { ctx, s } = sizeCanvas(cv, G.W, G.H, 980);
  dieView.s = s; dieView.H = G.H; dieView.dk = dk;
  const C = Object.fromEntries(CATS.map(c => [c[0], css(c[2])]));
  const CL = Object.fromEntries(Object.keys(CLOSVAR).map(k => [k, css(CLOSVAR[k])]));
  ctx.fillStyle = css('--die'); ctx.fillRect(0, 0, G.W * s, G.H * s);
  // 1 mm grid
  ctx.strokeStyle = css('--grid'); ctx.lineWidth = 1; ctx.beginPath();
  for (let x = 1000; x < G.W; x += 1000){ ctx.moveTo(x * s, 0); ctx.lineTo(x * s, G.H * s); }
  for (let y = 1000; y < G.H; y += 1000){ ctx.moveTo(0, (G.H - y) * s); ctx.lineTo(G.W * s, (G.H - y) * s); }
  ctx.stroke();
  const ink = css('--ink');
  for (const it of G.items){
    if (state.hidden.has(it.cat)) continue;
    if (!state.showWire && it.cat === 'wire') continue;
    const x = it.x * s, y = (G.H - it.y - it.h) * s, w = Math.max(it.w * s, .6), h = Math.max(it.h * s, .6);
    const clo = closureOf(dk, it.g);
    let fill;
    if (state.colorBy === 'closure') fill = clo === 'reservation' ? null : CL[clo];
    else fill = C[it.cat] || C.res;
    if (fill){ ctx.globalAlpha = (it.cat === 'field' && state.colorBy === 'kind') ? .78 : .9; ctx.fillStyle = fill; ctx.fillRect(x, y, w, h); ctx.globalAlpha = 1; }
    else { ctx.save(); ctx.setLineDash([3, 2]); ctx.strokeStyle = CL.reservation; ctx.lineWidth = 1; ctx.strokeRect(x + .5, y + .5, w - 1, h - 1); ctx.restore(); }
    // die-shot texture: ROM bit lines in tiles / pairs, cfg ROM row under DS pairs
    if ((it.cat === 'field') && h > 10 && w > 6){
      ctx.globalAlpha = .22; ctx.fillStyle = ink; const step = Math.max(2, h / 24);
      for (let yy = y + step; yy < y + h - 1; yy += step) ctx.fillRect(x + 1, yy, w - 2, .6);
      ctx.globalAlpha = 1;
    }
    if (dk === 'ds_s81_layer' && (it.g === 'q' || it.g === 'bf') && h > 2){
      ctx.globalAlpha = .35; ctx.fillStyle = C.res; ctx.fillRect(x, y + h, w, Math.max(1, 62.9 * s)); ctx.globalAlpha = 1;
    }
    if (w > 4 && h > 4){ ctx.strokeStyle = 'rgba(0,0,0,.18)'; ctx.lineWidth = .5; ctx.strokeRect(x, y, w, h); }
  }
  // labels for large blocks
  ctx.fillStyle = ink; ctx.font = `600 ${Math.max(9, Math.min(13, s * 380))}px ${css('--f-mono').split(',')[0]}`; ctx.textBaseline = 'top';
  const seen = new Set();
  for (const it of G.items){
    const w = it.w * s, h = it.h * s; if (w < 60 || h < 14) continue;
    if (state.hidden.has(it.cat)) continue;
    const key = it.g + (it.g === 'sm' || it.g === 'tile' ? '' : it.name);
    if (seen.has(key) && (it.g === 'sm' || it.g === 'tile')) continue; seen.add(key);
    ctx.globalAlpha = .85; ctx.fillText(it.name.replace(/^hb_|^sp_|^qfd_/, ''), it.x * s + 3, (G.H - it.y - it.h) * s + 3); ctx.globalAlpha = 1;
  }
  // clock regions
  if (state.showClock && dk === 'hbm_ds'){
    const regs = val(DATA.dies.hbm_ds.clock_regions); ctx.save(); ctx.setLineDash([6, 4]); ctx.strokeStyle = css('--accent'); ctx.lineWidth = 1.4; ctx.fillStyle = css('--accent'); ctx.font = `600 11px ${css('--f-mono').split(',')[0]}`;
    for (const r of regs){ const [a, b, c, e] = r.rect; ctx.strokeRect(a * s, (G.H - e) * s, (c - a) * s, (e - b) * s); ctx.fillText(r.name + ' · ' + r.clock.replace('clk_', ''), a * s + 3, (G.H - e) * s + 3); }
    ctx.restore();
  }
  // IR windows
  if (state.showIR){
    ctx.save(); ctx.font = `600 10px ${css('--f-mono').split(',')[0]}`; ctx.textBaseline = 'middle'; ctx.textAlign = 'center';
    if (dk === 'hbm_ds'){
      for (const w of val(DATA.dies.hbm_ds.ir_windows)){ const [, a, b, c, e, mv] = w; if (mv == null || mv === 0) continue; const x = a * s, y = (G.H - e) * s, ww = (c - a) * s, hh = (e - b) * s; ctx.globalAlpha = .42; ctx.fillStyle = heat(mv); ctx.fillRect(x + 1, y + 1, ww - 2, hh - 2); ctx.globalAlpha = 1; if (ww > 30){ ctx.fillStyle = ink; ctx.fillText(fmt(mv, 1), x + ww / 2, y + hh / 2); } }
    } else if (dk === 'qwen_rom'){
      const ir = val(DATA.dies.qwen_rom.ir);
      for (const k in ir){ const [a, b, c, e] = ir[k].win; const mv = ir[k].mv; const x = a * s, y = (G.H - e) * s, ww = (c - a) * s, hh = (e - b) * s; ctx.globalAlpha = .5; ctx.fillStyle = heat(mv); ctx.fillRect(x, y, ww, hh); ctx.globalAlpha = 1; ctx.strokeStyle = ink; ctx.strokeRect(x, y, ww, hh); ctx.fillStyle = ink; ctx.fillText(fmt(mv, 1) + ' mV' + (ir[k].ok ? '' : ' FAIL'), x + ww / 2, y + hh / 2); }
    }
    ctx.restore();
  }
  // selection
  if (state.sel && state.sel.dk === dk){
    ctx.save(); ctx.strokeStyle = css('--accent'); ctx.lineWidth = 2;
    for (const it of G.groups[state.sel.g] || []){ ctx.strokeRect(it.x * s - 1, (G.H - it.y - it.h) * s - 1, it.w * s + 2, it.h * s + 2); }
    const it = G.byName[state.sel.name]; if (it){ ctx.lineWidth = 3; ctx.strokeStyle = ink; ctx.strokeRect(it.x * s - 2, (G.H - it.y - it.h) * s - 2, it.w * s + 4, it.h * s + 4); }
    ctx.restore();
  }
  // scale bar
  const bar = 5000 * s; ctx.fillStyle = ink; ctx.fillRect(10, G.H * s - 16, bar, 3); ctx.font = `600 11px ${css('--f-mono').split(',')[0]}`; ctx.textBaseline = 'bottom'; ctx.textAlign = 'left'; ctx.fillText('5 mm', 10, G.H * s - 19);
  if (!state.sel) dieReadSummary();
}
function hitDie(ev){
  const dk = dieView.dk; const G = geo(dk); const r = $('dieCanvas').getBoundingClientRect(); const s = dieView.s;
  const ux = (ev.clientX - r.left) / s, uy = G.H - (ev.clientY - r.top) / s;
  let best = null;
  for (let i = G.items.length - 1; i >= 0; i--){ const it = G.items[i]; if (state.hidden.has(it.cat) || (!state.showWire && it.cat === 'wire')) continue; if (ux >= it.x && ux <= it.x + it.w && uy >= it.y && uy <= it.y + it.h){ if (!best || it.w * it.h < best.w * best.h) best = it; } }
  return best;
}
function dieReadSummary(){
  const dk = dieKey(); const D = DATA.dies[dk]; const G = geo(dk);
  const counts = {}; G.items.forEach(i => { counts[i.g] = (counts[i.g] || 0) + 1; });
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([g, n]) => { const b = blockInfo(dk, g); return `<dt>${esc(b ? b.label : g)}</dt><dd>${fmt0(n)} ${b ? cpill(b.closure) : ''}</dd>`; }).join('');
  const ctxLine = state.dieCtx ? `<div class="pill" style="color:var(--accent);margin-bottom:8px;white-space:normal">From the rack: ${esc(state.dieCtx)}</div>` : '';
  $('dieRead').innerHTML = `${ctxLine}<div class="eyebrow">${esc(D.title)}</div><h3>${fmt(G.W / 1000, 2)} × ${fmt(G.H / 1000, 2)} mm</h3>
   <dl><dt>Area</dt><dd>${vs(D.area, 2)} mm² ${pill(st(D.area))}</dd>${D.placed ? `<dt>Placed</dt><dd>${vs(D.placed, 1)} mm²</dd>` : ''}${D.grt ? `<dt>Route</dt><dd>${vs(D.grt)}</dd>` : ''}${D.ir_worst ? `<dt>IR worst</dt><dd>${vs(D.ir_worst, 2)} mV</dd>` : ''}${D.path ? `<dt>Wire stages</dt><dd>block word ${val(D.path).bword_worst}, link ${val(D.path).link_worst} @ ${val(D.path).pitch} µm</dd>` : ''}</dl>
   <div class="eyebrow" style="margin-top:12px">Instances (hover or click a block)</div><dl class="inst">${rows}</dl>${srcLine(D.geo)}`;
}
function dieRead(it){
  const dk = dieKey(); const b = blockInfo(dk, it.g) || {};
  const sl = (x) => x ? `${fmt(val(x), 2)} ps ${pill(st(x))}` : '—';
  $('dieRead').innerHTML = `<div class="eyebrow">${esc(it.name)} · ${esc(it.kind)}</div><h3>${esc(b.label || it.g)}</h3>
   <div style="margin-top:6px">${cpill(b.closure || 'open')}</div>
   <dl><dt>This instance</dt><dd>${fmt(it.w, 1)} × ${fmt(it.h, 1)} µm = ${fmt(it.w * it.h / 1e6, 4)} mm²</dd>
   <dt>Block area</dt><dd>${b.area && val(b.area) != null ? fmt(val(b.area), 4) + ' mm² ' + pill(st(b.area)) : 'see instance'}</dd>
   <dt>Instances</dt><dd>${b.inst != null ? fmt0(b.inst) : (geo(dk).groups[it.g] || []).length}</dd>
   <dt>RTL top</dt><dd>${esc(b.rtl || '—')}</dd>
   <dt>SS slack</dt><dd>${sl(b.ss)}</dd><dt>FF slack</dt><dd>${sl(b.ff)}</dd>
   <dt>Position</dt><dd>(${fmt0(it.x)}, ${fmt0(it.y)}) µm</dd></dl>
   ${b.note ? `<p style="margin-top:10px;font-size:13px">${esc(b.note)}</p>` : ''}
   ${b.area ? srcLine(b.area) : ''}${b.ss ? srcLine(b.ss) : ''}${b.src ? `<div class="src">${esc(b.src)}</div>` : ''}
   <button type="button" class="btn small" style="margin-top:10px" id="dieClr">Back to die summary</button>`;
  const c = $('dieClr'); if (c) c.onclick = () => { state.sel = null; drawDie(); };
}
function bindDie(){
  const cv = $('dieCanvas');
  cv.addEventListener('mousemove', ev => { const it = hitDie(ev); if (!it){ hideTip(); cv.style.cursor = 'default'; return; } cv.style.cursor = 'pointer'; const b = blockInfo(dieKey(), it.g) || {}; showTip(`<b>${esc(it.name)}</b> · ${esc(b.label || it.g)}<br>${fmt(it.w, 0)} × ${fmt(it.h, 0)} µm · ${esc(CLOSURE_LABEL[b.closure] || 'open')}`, ev); });
  cv.addEventListener('mouseleave', hideTip);
  cv.addEventListener('click', ev => { const it = hitDie(ev); if (!it) return; state.sel = { dk: dieKey(), g: it.g, name: it.name }; drawDie(); dieRead(it); });
  cv.tabIndex = 0;
  cv.addEventListener('keydown', ev => { // keyboard: cycle through block groups
    if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return; ev.preventDefault();
    const G = geo(dieKey()); const gs = Object.keys(G.groups); let i = state.sel ? gs.indexOf(state.sel.g) : -1; i = (i + (ev.key === 'ArrowRight' ? 1 : -1) + gs.length) % gs.length;
    const it = G.groups[gs[i]][0]; state.sel = { dk: dieKey(), g: it.g, name: it.name }; drawDie(); dieRead(it);
  });
}

/* ================================================================ 3. TOKEN */
const TK = { steps: [], i: 0, t: 0, playing: false, last: 0, speed: 1, spec: false, unit: 'us', total: 0 };
function centers(dk, sel, n){
  const G = geo(dk); let its = [];
  for (const s of [].concat(sel)){ if (G.groups[s]) its = its.concat(G.groups[s]); else if (G.byName[s]) its.push(G.byName[s]); else its = its.concat(G.items.filter(i => i.name.indexOf(s) === 0)); }
  if (!its.length) return [];
  if (n && its.length > n){ const k = its.length / n; its = Array.from({length: n}, (_, j) => its[Math.floor(j * k + k / 2)]); }
  return its.map(i => ({ x: i.x + i.w / 2, y: i.y + i.h / 2, it: i }));
}
function itemsOf(dk, sel){ const G = geo(dk); let its = []; for (const s of [].concat(sel || [])){ if (G.groups[s]) its = its.concat(G.groups[s]); else if (G.byName[s]) its.push(G.byName[s]); else its = its.concat(G.items.filter(i => i.name.indexOf(s) === 0)); } return its; }
function S(label, dur, busy, from, to, kind, extra){ return Object.assign({ label, dur, busy: [].concat(busy || []), from: from ? [].concat(from) : null, to: to ? [].concat(to) : null, kind: kind || 'compute' }, extra || {}); }

function buildDsSteps(){
  const segs = val(DATA.ds_stages); const nodes = [];
  for (const s of segs){ for (const n of s.nodes) if (/^L20\./.test(n[0])) nodes.push(n); if (/^L20\./.test(s.hop_node)) nodes.push([s.hop_node, s.hop, 'measured+vendor_phy']); }
  const SU = ['sp_su_s', 'sp_su_n'];
  return nodes.map(([name, us, cls]) => {
    const s = name.replace(/^L20\./, '');
    const label = s.replace(/^attn\./, 'attention · ').replace(/^ffn\./, 'MoE FFN · ');
    let st;
    if (/hc_pre|hc_post/.test(s)) st = S(label, us, ['sp_hc'], 'sp_vm', 'sp_hc', 'compute');
    else if (/substage_hop/.test(s)) st = S(label + ' (to next stage)', us, ['link'], 'sp_collective', ['lk_E1', 'lk_E2', 'lk_E3'], 'link');
    else if (/allgather|allreduce/.test(s)) st = S(label + ' (TP4 collective)', us, ['sp_collective', 'link'], 'sp_collective', ['lk_W1', 'lk_W2', 'lk_E1', 'lk_E2'], 'link', { back: true });
    else if (/a_proj|wo_a|wo_b|experts_gu|\.down|\.router$|wq_b|idx\.q/.test(s)) st = S(label + ' (ROM field)', us, ['q', 'bf', 'node'], 'sp_vm', ['q', 'bf'], 'field', { back: true, n: 18 });
    else if (/own_row_write/.test(s)) st = S(label + ' (new KV row to HBM)', us, ['svc', 'phy'], 'sp_vm', ['phy_SW', 'phy_SE', 'phy_NW', 'phy_NE'], 'hbm');
    else if (/window_load/.test(s)) st = S(label + ' (KV window from HBM)', us, ['svc', 'phy'], ['phy_SW', 'phy_SE', 'phy_NW', 'phy_NE'], 'svc', 'hbm');
    else if (/scores|idx\.score|idx\.topk/.test(s)) st = S(label + ' (scan service)', us, ['svc'], null, null, 'attn');
    else if (/gather/.test(s)) st = S(label, us, ['band_blk', 'sp_gather'], 'band_blk', 'sp_gather', 'attn');
    else st = S(label + ' (SU)', us, SU, null, null, 'su');
    st.cls = cls; st.src = 'composition node ' + name; return st;
  });
}
function buildHbmSteps(){
  if (state.hbmModel === 'qwen') return null;
  return val(DATA.hbm_l20).map(([name, us, cls, dom]) => {
    let st; const L = name;
    if (/^xload/.test(name)) st = S(L + ' (activation multicast)', us, ['vm'], 'vm', 'sm', 'move', { n: 16 });
    else if (/^sm:/.test(name)) st = S(L + ' (weights stream from HBM)', us, ['sm', 'svc', 'phy'], ['svc'], 'sm', 'stream', { n: 32 });
    else if (/^barrier/.test(name)) st = S('barrier (arrive + release)', us, ['barrier', 'cmdproc'], 'sm', 'barrier', 'move', { n: 12, back: true });
    else if (dom === 'coll') st = S(L + ' (TU collective)', us, ['coll', 'link'], 'coll', ['lk_S0', 'lk_S2', 'lk_N1', 'lk_N3'], 'link', { back: true });
    else if (dom === 'tail') st = S(L + ' (switch striping tail, modelled)', us, ['serdes'], null, null, 'link');
    else if (dom === 'su') st = S(L, us, /attend/.test(name) ? ['su', 'sfu'] : ['su'], null, null, 'su');
    else if (/router_top6/.test(name)) st = S(L, us, ['router'], 'su', 'router', 'move');
    else if (dom === 'du' || dom === 'du_fast') st = S(L, us, /hcp/.test(name) ? ['hc'] : ['index'], null, null, 'attn');
    else if (/expert_fetch/.test(name)) st = S(L, us, ['svc', 'phy'], 'router', 'svc', 'hbm');
    else if (dom === 'hbm') st = S(L + ' (KV rows)', us, ['svc', 'phy', 'attn'], 'svc', 'attn', 'hbm', { n: 16 });
    else if (dom === 'attn') st = S(L, us, ['attn'], null, null, 'attn');
    else st = S(L, us, [], null, null, 'compute');
    st.cls = cls; return st;
  }).filter(s => s.dur > 0);
}
function buildQwenSteps(){
  const ps = val(DATA.qwen_phase_split); const L = 5282; const f = L / ps.total;
  const A = ps.attention * f, M = ps.mlp * f, Rz = ps.residual * f, meA = ps.me_busy_attn * f, meM = ps.me_busy_mlp * f;
  const nA = A - meA, nM = M - meM;
  const SU = ['sp_su64_sfu'], T = 'tile';
  return [
    S('Attention RMSNorm on the SU64 + SFU slab', nA * .10, SU, null, null, 'su'),
    S('Broadcast x down the corridors to 1,536 tiles', meA * .06, ['sp_tree_top', 'station'], 'sp_tree_top', T, 'move', { n: 20 }),
    S('Q, K, V projections: weights read in place from code ROM', meA * .58, [T], null, null, 'field', { rom: true }),
    S('RoPE on q and k', nA * .08, SU, null, null, 'su'),
    S('New K/V row out to HBM through the CDC column', nA * .10, ['cdc', 'hbm_ctrl', 'phy'], 'row_engine', ['phy'], 'hbm'),
    S('Past K/V streams in from 4 stacks (prefetched a layer ahead)', nA * .04, ['phy', 'hbm_ctrl', 'cdc', 'row_engine'], ['phy'], 'row_engine', 'hbm', { n: 8 }),
    S('Scores, softmax and value on the row engines and SU', nA * .48, ['row_engine', 'sp_su64_sfu'], null, null, 'attn'),
    S('Output projection in the ROM tiles', meA * .36, [T], 'sp_tree_top', T, 'field', { rom: true, n: 20 }),
    S('All-reduce across the TP4 group', nA * .20, ['io', 'hub'], 'hub', ['io_collective'], 'link', { back: true }),
    S('MLP RMSNorm', nM * .2, SU, null, null, 'su'),
    S('Gate and up projections in ROM', meM * .62, [T], 'sp_tree_top', T, 'field', { rom: true, n: 20 }),
    S('SwiGLU on the SFU', nM * .3, SU, null, null, 'su'),
    S('Down projection in ROM', meM * .38, [T], 'sp_tree_top', T, 'field', { rom: true, n: 20 }),
    S('All-reduce across the TP4 group', nM * .5, ['io', 'hub'], 'hub', ['io_collective'], 'link', { back: true }),
    S('Residual add and hand-off to the next layer', Rz, SU, null, null, 'su'),
  ].map(s => (s.cls = 'analytical split of measured block', s));
}
function tokenDie(){ return state.design === 'hbm' ? 'hbm_ds' : DESIGNS[state.design].dies[0]; }
function buildSteps(){
  const d = state.design;
  if (d === 'ds'){ TK.steps = buildDsSteps(); TK.unit = 'us'; }
  else if (d === 'hbm'){ TK.steps = buildHbmSteps() || []; TK.unit = 'us'; }
  else { TK.steps = buildQwenSteps(); TK.unit = 'cyc'; }
  TK.total = TK.steps.reduce((a, s) => a + s.dur, 0); TK.i = 0; TK.t = 0;
  let acc = 0; TK.steps.forEach(s => { s.t0 = acc; acc += s.dur; });
  const lede = { ds: `Layer 20 of DeepSeek-V4.1 at position 1,048,575 on one S81 rank die, node by node from the measured composition. The weights never move: the activation x leaves the spine, visits the ROM pairs that hold the weights, and comes back up the return trees. KV rows are the only HBM traffic.`,
    qwen: `One steady decoder layer of Qwen3-8B (5,282 measured cycles) on one rank die. Weights stay in the code ROM inside each tile; only the 4,096-wide activation and the KV stream move. The split of the measured attention, MLP and residual blocks into finer steps is analytical.`,
    hbm: state.hbmModel === 'qwen' ? 'The token animation for the Qwen tile die is not built yet: its per-node layer record is not part of this page. Switch to the DeepSeek die to see the HBM accelerator data path.' : `Layer 20 of DeepSeek-V4.1 on one HBM accelerator die, node by node from the matched-reference composition. Every matrix operation pulls its weights from the four stacks through the stream services (magenta flow) before the SMs can use them.` }[d];
  $('tokenLede').textContent = lede;
  $('tSpec').disabled = d === 'qwen' || (d === 'hbm' && state.hbmModel === 'qwen');
  if ($('tSpec').disabled){ TK.spec = false; $('tSpec').setAttribute('aria-pressed', 'false'); }
  $('tSpec').title = d === 'qwen' ? 'Off on the Qwen ROM: DSpark measured 0.705x of plain decoding (r21 relays charged)' : 'Show the speculative wavefront';
  const ul = $('tSteps'); ul.innerHTML = TK.steps.map((s, i) => `<li data-i="${i}" tabindex="0"><span class="sw" style="background:var(${CATVAR[{field:'field', su:'su', link:'link', hbm:'hbm', attn:'attn', move:'ctrl', stream:'hbm', compute:'res'}[s.kind]] || '--k-res'})"></span><span>${esc(s.label)}</span><span class="t">${TK.unit === 'cyc' ? fmt0(s.dur) : fmt(s.dur, 3)}</span></li>`).join('');
  ul.querySelectorAll('li').forEach(li => { const go = () => { TK.i = +li.dataset.i; TK.t = 0; drawToken(); }; li.onclick = go; li.onkeydown = e => { if (e.key === 'Enter'){ go(); } }; });
  const srcs = { ds: DATA.ds_stages, hbm: DATA.hbm_l20, qwen: DATA.qwen_phase_split };
  $('tSrc').innerHTML = srcLine(srcs[d]) + (d === 'qwen' ? srcLine(DATA.qwen_layers) : '');
  $('tokLegend').innerHTML = `<span><i class="sw" style="background:var(--packet)"></i>activation packet</span>${d === 'hbm' ? '<span><i class="sw" style="background:var(--k-hbm)"></i>weight stream from HBM</span>' : '<span><i class="sw" style="background:var(--k-field)"></i>weights stay put (ROM)</span>'}<span><i class="sw" style="background:var(--packet-2)"></i>KV / collective traffic</span><span class="muted">Arrow keys step when the canvas has focus.</span>`;
}
function drawToken(){
  const dk = tokenDie(); const G = geo(dk); const cv = $('tokCanvas');
  const { ctx, s } = sizeCanvas(cv, G.W, G.H, 980);
  const C = Object.fromEntries(CATS.map(c => [c[0], css(c[2])]));
  ctx.fillStyle = css('--die'); ctx.fillRect(0, 0, G.W * s, G.H * s);
  const step = TK.steps[TK.i]; const busy = new Set(step ? itemsOf(dk, step.busy).map(i => i.i) : []);
  const ph = step ? Math.min(1, TK.t / Math.max(step.dur, 1e-9)) : 0;
  const pulse = .55 + .45 * Math.sin(ph * Math.PI);
  for (const it of G.items){
    const x = it.x * s, y = (G.H - it.y - it.h) * s, w = Math.max(it.w * s, .6), h = Math.max(it.h * s, .6);
    const on = busy.has(it.i);
    ctx.globalAlpha = on ? (.55 + .45 * pulse) : .16; ctx.fillStyle = C[it.cat] || C.res; ctx.fillRect(x, y, w, h);
    if (on && w > 3 && h > 3){ ctx.globalAlpha = 1; ctx.strokeStyle = css('--ink'); ctx.lineWidth = .6; ctx.strokeRect(x, y, w, h); }
  }
  ctx.globalAlpha = 1;
  const P = (pt) => [pt.x * s, (G.H - pt.y) * s];
  function packet(a, b, t, col, r){ const [x1, y1] = P(a), [x2, y2] = P(b); const x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t; ctx.strokeStyle = col; ctx.globalAlpha = .35; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); ctx.globalAlpha = 1; ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, r || 3.2, 0, Math.PI * 2); ctx.fill(); }
  if (step){
    const pk = css('--packet'), pk2 = css('--packet-2'), hb = css('--k-hbm');
    const waves = TK.spec ? 6 : 1;
    for (let wv = 0; wv < waves; wv++){
      const lag = wv * 0.11; const t = Math.max(0, Math.min(1, ph * (1 + lag * 1.2) - lag));
      if (TK.spec && t <= 0) continue;
      if (step.kind === 'stream' || (state.design === 'hbm' && step.kind === 'field')){
        // weight stream: PHY -> stream service -> SMs, shared by all waves in spec mode
        if (wv === 0){ const ph4 = centers(dk, 'phy'); const sms = centers(dk, 'sm', 32); const svc = centers(dk, 'svc');
          sms.forEach((m, j) => { const src = svc.reduce((b, c) => (Math.hypot(c.x - m.x, c.y - m.y) < Math.hypot(b.x - m.x, b.y - m.y) ? c : b), svc[0]); const tt = (ph * 3 + j * 0.13) % 1; packet(src, m, tt, hb, 2.4); });
          ph4.forEach(p => { const sv = svc.reduce((b, c) => (Math.hypot(c.x - p.x, c.y - p.y) < Math.hypot(b.x - p.x, b.y - p.y) ? c : b), svc[0]); packet(p, sv, (ph * 4) % 1, hb, 2.4); }); }
        const vm = centers(dk, 'vm')[0]; if (vm && TK.spec){ const m = centers(dk, 'sm', 6)[wv % 6]; if (m) packet(vm, m, t, pk, 3); }
        continue;
      }
      if (!step.from || !step.to) continue;
      const fr = centers(dk, step.from, 4); const to = centers(dk, step.to, step.n || 8);
      if (!fr.length || !to.length) continue;
      const col = (step.kind === 'link' || step.kind === 'hbm') ? pk2 : pk;
      to.forEach((d, j) => { const a = fr[j % fr.length]; const tt = step.back ? (t < .5 ? t * 2 : 2 - t * 2) : t; packet(a, d, tt, col, wv ? 2.6 : 3.4); });
    }
    if (step.rom){ ctx.fillStyle = css('--ink'); ctx.font = `600 12px ${css('--f-mono').split(',')[0]}`; ctx.textAlign = 'left'; ctx.textBaseline = 'top'; ctx.fillText('weights stationary: no weight traffic', 8, 8); }
  }
  // readouts
  const elapsed = step ? step.t0 + Math.min(TK.t, step.dur) : 0;
  const cyc = TK.unit === 'cyc' ? elapsed : elapsed * 1200;
  $('tCount').innerHTML = TK.unit === 'cyc' ? `${fmt0(elapsed)}<small>cycles of ${fmt0(TK.total)}</small>` : `${fmt(elapsed, 3)}<small>µs of ${fmt(TK.total, 3)} · ${fmt0(cyc)} cycles</small>`;
  $('tProg').style.width = (TK.total ? 100 * elapsed / TK.total : 0) + '%';
  let busyTxt = step ? `<b>Busy:</b> ${esc(step.label)}${step.cls ? ` · <span class="muted">${esc(step.cls)}</span>` : ''}` : '';
  if (TK.spec && state.design === 'ds'){ const m = val(DATA.ds_mtp); busyTxt += `<br><b>Speculation:</b> a wavefront of 6 positions (1 verified + 5 drafts) enters the pipeline ${fmt(m.II, 3)} µs apart; the step costs ${fmt(m.step, 1)} µs and commits τ = ${fmt(val(DATA.rates.ds.tau), 3)} tokens on average.`; }
  if (TK.spec && state.design === 'hbm'){ busyTxt += `<br><b>Speculation:</b> the 6 positions share each weight stream; MTP step ${vs(DATA.rates.hbm_ds.MTP_step_us, 1)} µs at τ 4.159 (wire median).`; }
  $('tBusy').innerHTML = busyTxt;
  $('tSteps').querySelectorAll('li').forEach((li, i) => li.setAttribute('aria-current', String(i === TK.i)));
  const cur = $('tSteps').querySelector('[aria-current="true"]'); if (cur && TK.playing){ const ul = $('tSteps'); const top = cur.offsetTop - ul.offsetTop; if (top < ul.scrollTop || top > ul.scrollTop + ul.clientHeight - 30) ul.scrollTop = top - 60; }
}
function tick(ts){
  if (!TK.playing) return;
  const dt = TK.last ? (ts - TK.last) / 1000 : 0; TK.last = ts;
  // pace: the whole layer plays in ~14 s at 1x, but no step shorter than 0.35 s
  const step = TK.steps[TK.i]; if (!step){ TK.playing = false; return; }
  const secPerUnit = 14 / TK.total; const stepSec = Math.max(.35, step.dur * secPerUnit);
  TK.t += dt * TK.speed * step.dur / stepSec;
  if (TK.t >= step.dur){ TK.t = 0; TK.i++; if (TK.i >= TK.steps.length){ TK.i = 0; } }
  drawToken(); requestAnimationFrame(tick);
}
function bindToken(){
  $('tPlay').onclick = () => { TK.playing = !TK.playing; $('tPlay').setAttribute('aria-pressed', String(TK.playing)); $('tPlay').textContent = TK.playing ? 'Pause' : 'Play'; TK.last = 0; if (TK.playing) requestAnimationFrame(tick); };
  const stepBy = d => { TK.playing = false; $('tPlay').setAttribute('aria-pressed', 'false'); $('tPlay').textContent = 'Play'; TK.i = (TK.i + d + TK.steps.length) % TK.steps.length; TK.t = TK.steps[TK.i] ? TK.steps[TK.i].dur * .5 : 0; drawToken(); };
  $('tBack').onclick = () => stepBy(-1); $('tFwd').onclick = () => stepBy(1);
  $('tSpeed').onchange = e => { TK.speed = +e.target.value; };
  $('tSpec').onclick = () => { TK.spec = !TK.spec; $('tSpec').setAttribute('aria-pressed', String(TK.spec)); drawToken(); };
  const cv = $('tokCanvas'); cv.tabIndex = 0; cv.addEventListener('keydown', e => { if (e.key === 'ArrowRight'){ e.preventDefault(); stepBy(1); } if (e.key === 'ArrowLeft'){ e.preventDefault(); stepBy(-1); } if (e.key === ' '){ e.preventDefault(); $('tPlay').click(); } });
}

/* ================================================================ 4. TIMING */
const WFCAT = { field: ['ROM field matvec', '--k-field'], su: ['SU / vector chains', '--k-su'], hop: ['Hops and collectives', '--k-link'], attn: ['Attention and index', '--k-attn'], head: ['Embed and LM head', '--k-tree'],
  sm: ['SM matrix ops (weights from HBM)', '--k-field'], coll: ['TU collectives', '--k-link'], tail: ['Switch striping tail (modelled)', '--k-res'], hbm: ['HBM rows', '--k-hbm'], du: ['Index / select', '--k-index'], du_fast: ['Index / select', '--k-index'],
  attention: ['Attention block', '--k-attn'], mlp: ['MLP block', '--k-field'], residual: ['Residual', '--k-su'], layer: ['Layer (measured)', '--k-field'], headq: ['RTL head', '--k-tree'], lever: ['Exact levers (removed)', '--s-closed'], wire: ['Die wire stages (added)', '--k-wire'], ctx: ['Adopted lever cycles', '--k-ctrl'] };
function hatchDefs(svg){
  const defs = svgEl('defs', {}, svg);
  const mk = (id, col) => { const p = svgEl('pattern', {id, width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)'}, defs); svgEl('rect', {width: 6, height: 6, fill: col, opacity: .25}, p); svgEl('rect', {width: 2.4, height: 6, fill: col}, p); };
  return mk;
}
function renderWaterfall(){
  const svg = $('wfSvg'); clear(svg); const d = state.design;
  const W = 1100, lab = 70, x0 = lab + 10, x1 = W - 20, rowH = 9, gap = 2;
  let rows = [], total = 0, unit = 'µs', legendKeys = [];
  if (d === 'ds'){
    const segs = val(DATA.ds_stages); let t = 0;
    segs.forEach((s, k) => { const parts = []; for (const n of s.nodes){ parts.push({ t0: t, d: n[1], c: catDs(n[0]), name: n[0] }); t += n[1]; } parts.push({ t0: t, d: s.hop, c: 'hop', name: s.hop_node || 'token return' }); t += s.hop; rows.push({ label: (s.layers.join(' ') || 'pass').replace(/L(\d+)/g, 'L$1'), parts }); });
    const ex = val(DATA.ds_extra_hops); rows.push({ label: `+${ex.count} hops`, parts: [{ t0: t, d: ex.total, c: 'hop', name: `${ex.count} extra stage hops (${ex.s81} S81 + ${ex.qelem} q-element frame)` }] }); t += ex.total; total = t; legendKeys = ['field', 'su', 'attn', 'hop', 'head'];
    $('wfLede').innerHTML = `Every node on the DeepSeek ROM token's critical path at 1M, one row per stretch between stage hops. Total ${fmt(total, 3)} µs = ${fmt(val(DATA.rates.ds.AR), 1)} tok/s. ${pill(st(DATA.ds_stages))}`;
  } else if (d === 'qwen'){
    const L = val(DATA.qwen_layers); const ps = val(DATA.qwen_phase_split); unit = 'cycles';
    L.forEach(s => { if (s.name === 'HEAD' || /head/i.test(s.name)){ rows.push({ label: 'head', parts: [{ t0: s.start, d: s.cycles, c: 'headq', name: 'RTL head' }] }); return; } const f = s.cycles / ps.total; rows.push({ label: s.name, parts: [{ t0: s.start, d: ps.attention * f, c: 'attention', name: 'attention (split analytical)' }, { t0: s.start + ps.attention * f, d: ps.mlp * f, c: 'mlp', name: 'MLP (split analytical)' }, { t0: s.start + (ps.attention + ps.mlp) * f, d: ps.residual * f, c: 'residual', name: 'residual (split analytical)' }], tot: s.cycles }); });
    const last = L[L.length - 1]; let t = last.start + last.cycles; for (const lv of val(DATA.rates.qwen.levers)){ if (!lv.cycles) continue; rows.push({ label: '+' + lv.name, parts: [{ t0: t, d: lv.cycles, c: 'ctx', name: `adopted lever ${lv.name} (${lv.variant || lv.verdict}): +${lv.cycles} cycles` }] }); t += lv.cycles; } total = val(DATA.rates.qwen.cycles); legendKeys = ['attention', 'mlp', 'residual', 'headq', 'ctx'];
    $('wfLede').innerHTML = `Each decoder layer of the measured P8191 token (L0 includes the first KV fill; L1-L35 are 5,282 cycles each, at their compute-only bound). The attention/MLP/residual split inside a layer applies the measured isolated-L0 proportions and is analytical. Total ${fmt0(total)} cycles. ${pill('measured')}`;
  } else {
    const L = val(DATA.hbm_layers); let t = 0;
    L.forEach(r => { const parts = []; for (const k of ['hbm', 'su', 'sm', 'du', 'du_fast', 'attn', 'coll', 'tail']){ if (r.doms[k]){ parts.push({ t0: t, d: r.doms[k], c: k, name: k }); t += r.doms[k]; } } rows.push({ label: r.name, parts }); });
    const lv = val(DATA.rates.hbm_ds.levers_us), wi = val(DATA.rates.hbm_ds.wire_us);
    rows.push({ label: 'levers', parts: [{ t0: t - lv, d: lv, c: 'lever', name: 'exact levers −' + fmt(lv, 3) + ' µs' }] }); t -= lv;
    rows.push({ label: 'die wire', parts: [{ t0: t, d: wi, c: 'wire', name: 'die wire stages +' + fmt(wi, 3) + ' µs (median bundle)' }] }); t += wi; total = t;
    legendKeys = ['sm', 'su', 'attn', 'du', 'hbm', 'coll', 'tail', 'lever', 'wire'];
    $('wfLede').innerHTML = `The HBM accelerator's DeepSeek token at 1M by layer, split by unit in path order (the matched-reference gate), then the exact levers removed and the die wire added. Total ${fmt(total, 3)} µs = ${fmt(val(DATA.rates.hbm_ds.AR), 1)} tok/s before die closure; the die closure costs add ${fmt(val(DATA.rates.hbm_ds.closure_us), 3)} µs (${fmt(val(DATA.rates.hbm_ds.AR_unified), 1)} tok/s candidate). ${pill('analytical')}`;
  }
  const H = 30 + rows.length * (rowH + gap) + 30;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
  const sx = v => x0 + (x1 - x0) * v / total;
  // axis
  const ticks = niceTicks(0, total, 8);
  for (const tv of ticks){ const x = sx(tv); svgEl('line', {x1: x, y1: 22, x2: x, y2: H - 22, stroke: css('--line'), 'stroke-width': .6}, svg); const tx = svgEl('text', {x, y: 16, 'text-anchor': 'middle', 'font-size': 10, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); tx.textContent = fmt0(tv) + (tv === ticks[ticks.length - 1] ? ' ' + unit : ''); }
  const mk = hatchDefs(svg); mk('hlever', css('--s-closed'));
  rows.forEach((r, k) => {
    const y = 26 + k * (rowH + gap);
    if (k % 2 === 0 || rows.length < 50){ const lt = svgEl('text', {x: lab, y: y + rowH - 1, 'text-anchor': 'end', 'font-size': 8.5, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); lt.textContent = r.label.length > 12 ? r.label.slice(0, 12) + '…' : r.label; }
    for (const p of r.parts){ if (p.d <= 0) continue; const x = sx(p.t0), w = Math.max(.5, sx(p.t0 + p.d) - x); const col = css((WFCAT[p.c] || WFCAT.field)[1]); const rect = svgEl('rect', {x, y, width: w, height: rowH, fill: p.c === 'lever' ? 'url(#hlever)' : col}, svg); rect.addEventListener('mousemove', ev => showTip(`<b>${esc(r.label)}</b> · ${esc(p.name)}<br>${unit === 'cycles' ? fmt0(p.d) + ' cycles' : fmt(p.d, 4) + ' µs'} · starts at ${unit === 'cycles' ? fmt0(p.t0) : fmt(p.t0, 3)}`, ev)); rect.addEventListener('mouseleave', hideTip); }
  });
  $('wfLegend').innerHTML = legendKeys.map(k => `<span><i class="sw" style="background:var(${WFCAT[k][1]})"></i>${esc(WFCAT[k][0])}</span>`).join('');
}
function catDs(node){
  const s = node.replace(/^L\d+\./, '');
  if (/^head|^embed|^token/.test(node)) return /hop|return/.test(s) ? 'hop' : 'head';
  if (/hop|allgather|allreduce/.test(s)) return 'hop';
  if (/a_proj|wo_a|wo_b|experts_gu|ffn\.down|ffn\.router$|wq_b|idx\.q$|eng\.dot/.test(s)) return 'field';
  if (/scores|\.max|\.exp|\.den|\.sink|normalize|own_row_write|window_load|idx\.score|idx\.topk|attn\.gather/.test(s)) return 'attn';
  return 'su';
}
function niceTicks(a, b, n){ const span = b - a; const step0 = span / n; const mag = Math.pow(10, Math.floor(Math.log10(step0))); const err = step0 / mag; const step = (err >= 5 ? 10 : err >= 2 ? 5 : err >= 1 ? 2 : 1) * mag; const out = []; for (let v = Math.ceil(a / step) * step; v <= b + 1e-9; v += step) out.push(+v.toFixed(6)); return out; }

function renderClosure(){
  const svg = $('cbSvg'); clear(svg);
  const all = val(DATA.closure_board);
  const f = state.cbFilter === 'all' ? (state.design === 'hbm' ? 'hbm' : state.design) : state.cbFilter;
  $('cbTools').innerHTML = `<div class="seg" role="group" aria-label="Design filter">${[['qwen', 'Qwen ROM'], ['ds', 'DeepSeek ROM'], ['hbm', 'HBM accelerator'], ['every', 'All']].map(([k, l]) => `<button type="button" data-cf="${k}" aria-pressed="${f === k}">${l}</button>`).join('')}</div>`;
  $('cbTools').querySelectorAll('[data-cf]').forEach(b => b.onclick = () => { state.cbFilter = b.dataset.cf; renderClosure(); });
  const rows = all.filter(r => f === 'every' || r.design === f).sort((a, b) => (a.ss == null ? -1e9 : a.ss) - (b.ss == null ? -1e9 : b.ss));
  const W = 1000, lab = 330, x0 = lab + 10, x1 = W - 70, rh = 20, lo = -800, hi = 420;
  const H = 40 + rows.length * rh + 20;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
  const sx = v => x0 + (x1 - x0) * (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo);
  for (const tv of [-800, -600, -400, -200, 0, 200, 400]){ const x = sx(tv); svgEl('line', {x1: x, y1: 24, x2: x, y2: H - 14, stroke: tv === 0 ? css('--ink') : css('--line'), 'stroke-width': tv === 0 ? 1.4 : .6}, svg); const t = svgEl('text', {x, y: 16, 'text-anchor': 'middle', 'font-size': 10, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); t.textContent = (tv > 0 ? '+' : '') + tv + (tv === 400 ? ' ps' : ''); }
  rows.forEach((r, k) => {
    const y = 34 + k * rh;
    if (k % 2 === 0) svgEl('rect', {x: 0, y: y - rh / 2, width: W, height: rh, fill: css('--grid')}, svg);
    const t = svgEl('text', {x: lab, y: y + 4, 'text-anchor': 'end', 'font-size': 11.5, fill: css('--ink')}, svg); t.textContent = (f === 'every' ? '[' + r.design + '] ' : '') + (r.block.length > 46 ? r.block.slice(0, 46) + '…' : r.block);
    const g = svgEl('g', {}, svg);
    const mark = (v, shape) => { if (v == null) return; const x = sx(v); const ok = v >= 0; const col = ok ? css('--s-closed') : css('--s-open');
      if (shape === 'ss') svgEl('circle', {cx: x, cy: y, r: 5.5, fill: col}, g); else svgEl('path', {d: `M${x} ${y - 6} L${x + 6} ${y} L${x} ${y + 6} L${x - 6} ${y} Z`, fill: 'none', stroke: col, 'stroke-width': 2}, g);
      if (v < lo || v > hi){ const a = v < lo ? x - 12 : x + 12; svgEl('path', {d: v < lo ? `M${a} ${y} l6 -4 v8 Z` : `M${a} ${y} l-6 -4 v8 Z`, fill: col}, g); } };
    if (r.ss != null && r.ff != null) svgEl('line', {x1: sx(r.ss), y1: y, x2: sx(r.ff), y2: y, stroke: css('--line'), 'stroke-width': 1}, g);
    mark(r.ss, 'ss'); mark(r.ff, 'ff');
    const vt = svgEl('text', {x: x1 + 8, y: y + 4, 'font-size': 10.5, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); vt.textContent = (r.ss == null ? '—' : (r.ss > 0 ? '+' : '') + fmt(r.ss, 1)) + ' / ' + (r.ff == null ? '—' : (r.ff > 0 ? '+' : '') + fmt(r.ff, 1));
    const hit = svgEl('rect', {x: 0, y: y - rh / 2, width: W, height: rh, fill: 'transparent'}, svg);
    hit.addEventListener('mousemove', ev => showTip(`<b>${esc(r.block)}</b><br>SS ${r.ss == null ? '—' : fmt(r.ss, 2) + ' ps'} · FF ${r.ff == null ? '—' : fmt(r.ff, 2) + ' ps'}<br>${esc(CLOSURE_LABEL[r.closure] || r.closure)} · ${esc(r.basis)}<br><span style="opacity:.8">${esc(r.src)}</span>`, ev)); hit.addEventListener('mouseleave', hideTip);
  });
  $('cbLegend').innerHTML = `<span><svg width="14" height="14"><circle cx="7" cy="7" r="5" fill="var(--s-closed)"/></svg>SS setup slack</span><span><svg width="14" height="14"><path d="M7 1 L13 7 L7 13 L1 7 Z" fill="none" stroke="var(--s-closed)" stroke-width="2"/></svg>FF hold slack</span><span><i class="sw" style="background:var(--s-open)"></i>negative: fails at 1.2 GHz</span><span>${pill(st(DATA.closure_board))} ${esc(DATA.closure_board.src)}</span>`;
}

function renderLevers(){
  const svg = $('lvSvg'); clear(svg); const d = state.design;
  const W = 1000; let H;
  const mk = hatchDefs(svg); mk('hc1', css('--k-field')); mk('hc2', css('--k-attn'));
  if (d === 'ds'){
    const L = val(DATA.ds_levers);
    const order = L.slice().sort((a, b) => ({adopted: 0, conditional: 1, excluded: 2})[a.cls] - ({adopted: 0, conditional: 1, excluded: 2})[b.cls] || (b.dMTP_tok_s || 0) - (a.dMTP_tok_s || 0));
    const lab = 250, colW = (W - lab - 40) / 2, rh = 30; H = 50 + order.length * rh + 70;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
    const maxAR = 400, maxMTP = 2300;
    [['AR tok/s per user', lab + 10, maxAR], ['MTP tok/s per user', lab + 20 + colW, maxMTP]].forEach(([t, x, m]) => { const e = svgEl('text', {x, y: 18, 'font-size': 11, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); e.textContent = t + ' (Δ, 0 → ' + fmt0(m) + ')'; });
    order.forEach((r, k) => {
      const y = 36 + k * rh;
      const tl = svgEl('text', {x: lab, y: y + 12, 'text-anchor': 'end', 'font-size': 12.5, 'font-weight': 600, fill: css('--ink')}, svg); tl.textContent = r.name;
      const sub = svgEl('text', {x: lab, y: y + 24, 'text-anchor': 'end', 'font-size': 9.5, 'font-family': 'var(--f-mono)', fill: r.cls === 'adopted' ? css('--s-closed') : r.cls === 'conditional' ? css('--s-enc') : css('--s-open')}, svg); sub.textContent = r.verdict;
      if (r.cls === 'excluded'){ const n = svgEl('text', {x: lab + 10, y: y + 16, 'font-size': 11.5, fill: css('--muted')}, svg); n.textContent = 'rejected: ' + (r.what || '') ; return; }
      [[r.dAR_tok_s, lab + 10, maxAR, 'hc1', '--k-field'], [r.dMTP_tok_s, lab + 20 + colW, maxMTP, 'hc2', '--k-attn']].forEach(([v, x, m, h, c]) => {
        const w = Math.max(1, (colW - 70) * (v || 0) / m);
        const rc = svgEl('rect', {x, y: y + 2, width: w, height: 18, fill: r.cls === 'adopted' ? css(c) : `url(#${h})`}, svg);
        const vt = svgEl('text', {x: x + w + 6, y: y + 15, 'font-size': 11, 'font-family': 'var(--f-mono)', fill: css('--ink')}, svg); vt.textContent = '+' + fmt(v, 1);
        rc.addEventListener('mousemove', ev => showTip(`<b>${esc(r.name)}</b> · ${esc(r.verdict)}<br>${esc(r.what)}<br>ΔAR ${fmt(r.dAR_us, 3)} µs, ΔMTP step ${fmt(r.dMTP_step_us, 3)} µs<br><span style="opacity:.8">${esc(r.record)}</span>`, ev)); rc.addEventListener('mouseleave', hideTip);
      });
    });
    const yb = 40 + order.length * rh + 16; const R = DATA.rates.ds;
    const s1 = svgEl('text', {x: lab + 10, y: yb + 10, 'font-size': 12.5, fill: css('--ink')}, svg); s1.textContent = `Headline with adopted levers: ${fmt(val(R.AR))} AR / ${fmt(val(R.MTP))} MTP tok/s (measured).`;
    const s2 = svgEl('text', {x: lab + 10, y: yb + 30, 'font-size': 12.5, fill: css('--muted')}, svg); s2.textContent = `All pending levers together (field_spine_pq, su_norm, su_softmax, su_swiglu): ${fmt(val(R.AR_cond))} AR / ${fmt(val(R.MTP_cond))} MTP tok/s (analytical until SS/FF closes).`;
    $('lvLede').innerHTML = `Each bar is one DeepSeek ROM lever's own effect: for adopted levers, the headline minus the headline without it; for pending ones, the gain if it alone were adopted. The bars do not add up, because levers share critical-path nodes. ${pill(st(DATA.ds_levers))}`;
    $('lvLegend').innerHTML = `<span><i class="sw" style="background:var(--k-field)"></i>adopted (in the headline)</span><span><i class="sw" style="background:repeating-linear-gradient(45deg,var(--k-field) 0 2px,transparent 2px 5px)"></i>conditional: exact, waiting for SS/FF closure</span><span>excluded: fails 1.2 GHz</span>`;
  } else if (d === 'hbm'){
    const L = val(DATA.hbm_levers); H = 140; svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
    L.forEach((r, k) => { const y = 24 + k * 50; const t = svgEl('text', {x: 240, y: y + 14, 'text-anchor': 'end', 'font-size': 12.5, 'font-weight': 600, fill: css('--ink')}, svg); t.textContent = r.name;
      [[r.dAR_us, 250, 'AR'], [r.dMTP_step_us, 620, 'MTP step']].forEach(([v, x, l]) => { const w = Math.abs(v) * 4; svgEl('rect', {x, y, width: Math.max(1, w), height: 18, fill: 'url(#hc1)'}, svg); const vt = svgEl('text', {x: x + w + 6, y: y + 14, 'font-size': 11, 'font-family': 'var(--f-mono)', fill: css('--ink')}, svg); vt.textContent = `${l} ${fmt(v, 3)} µs`; });
      const n = svgEl('text', {x: 250, y: y + 34, 'font-size': 10.5, fill: css('--muted')}, svg); n.textContent = r.scope.slice(0, 120); });
    $('lvLede').innerHTML = `HBM accelerator levers credited in the comparator: both are exact on minimum components; their SS/FF closure is not admitted. ${pill('analytical')}`;
    $('lvLegend').innerHTML = '<span>bar length: µs removed from the token (AR) or the speculative step (MTP)</span>';
  } else {
    const QL = val(DATA.rates.qwen.levers), Q = DATA.rates.qwen, m = val(Q.cycles_measured), sn = val(Q.sens);
    H = 136 + QL.length * 26; svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
    const t = svgEl('text', {x: 20, y: 30, 'font-size': 13, fill: css('--ink')}, svg); t.textContent = `Measured token ${fmt0(m)} cycles (${fmt(1.2e9 / m, 1)} tok/s) + adopted levers = ${fmt0(val(Q.cycles))} cycles: ${fmt(val(Q.AR), 1)} tok/s.`;
    QL.forEach((lv, k) => { const tl = svgEl('text', {x: 36, y: 56 + k * 26, 'font-size': 12.5, fill: css('--ink')}, svg); tl.textContent = `${lv.name} (${lv.variant || 'adopted'}): +${lv.cycles} cycles, ${fmt(lv.dAR_tok_s, 1)} tok/s, ${lv.verdict.split(',')[0].split(' (')[0]}`; });
    const y0 = 56 + QL.length * 26;
    const t1 = svgEl('text', {x: 20, y: y0, 'font-size': 13, fill: css('--muted')}, svg); t1.textContent = `Modelled sensitivity (not RTL, not a headline): +${sn.cycles} cycles of die crossbar on the cold first layer, ${fmt(sn.AR, 1)} tok/s.`;
    const t2 = svgEl('text', {x: 20, y: y0 + 26, 'font-size': 13, fill: css('--muted')}, svg); t2.textContent = `DSpark speculation: built and exact, switched off; it measures ${fmt(val(Q.dspark_ratio), 3)}× of plain decoding (${fmt(val(Q.dspark))} tok/s).`;
    const t3 = svgEl('text', {x: 20, y: y0 + 52, 'font-size': 13, fill: css('--muted')}, svg); t3.textContent = 'Reason: a 4-position verify layer costs 3.26× an AR layer, because the ROM reads exactly as fast as the lanes multiply.';
    $('lvLede').innerHTML = `The Qwen ROM's adopted levers since the measured token, and one decision. ${pill('measured')}`;
    $('lvLegend').innerHTML = '';
  }
}

/* ================================================================ 5. COMPARE */
function renderCompare(){
  const svg = $('cmpSvg'); clear(svg); const R = DATA.rates;
  const rows = [
    ['Qwen3-8B · ROM, 8K', R.qwen.AR, R.qwen.MTP, null, 'MTP mode is plain decoding (DSpark off)'],
    ['Qwen3-8B · HBM accel. TP4, 8K', R.hbm_qwen.AR, R.hbm_qwen.MTP, null, 'MTP not composed on this basis'],
    ['DeepSeek-V4.1 · ROM array, 1M', R.ds.AR, R.ds.MTP, [R.ds.AR_cond, R.ds.MTP_cond], 'outline: with every pending lever'],
    ['DeepSeek-V4.1 · HBM accel., 1M', R.hbm_ds.AR_unified, R.hbm_ds.MTP_unified, null, 'candidate with die closure costs; same τ'],
  ];
  const W = 1000, lab = 250, x0 = lab + 10, x1 = W - 90, rh = 70; const H = 30 + rows.length * rh + 10;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
  const mk = hatchDefs(svg); mk('cAR', css('--k-field')); mk('cMTP', css('--k-attn'));
  const max = 7000; const sx = v => x0 + (x1 - x0) * v / max;
  for (const tv of [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000]){ const x = sx(tv); svgEl('line', {x1: x, y1: 20, x2: x, y2: H - 6, stroke: css('--line'), 'stroke-width': .6}, svg); const t = svgEl('text', {x, y: 14, 'text-anchor': 'middle', 'font-size': 10, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); t.textContent = fmt0(tv) + (tv === 7000 ? ' tok/s' : ''); }
  rows.forEach(([name, ar, mtp, cond, note], k) => {
    const y = 28 + k * rh;
    const t = svgEl('text', {x: lab, y: y + 16, 'text-anchor': 'end', 'font-size': 13, 'font-weight': 600, fill: css('--ink')}, svg); t.textContent = name;
    const n = svgEl('text', {x: lab, y: y + 32, 'text-anchor': 'end', 'font-size': 10, fill: css('--muted')}, svg); n.textContent = note;
    [[ar, 'AR', 0, 'cAR', '--k-field'], [mtp, 'MTP', 24, 'cMTP', '--k-attn']].forEach(([v, l, dy, h, c]) => {
      const vv = val(v);
      if (vv == null){ const e = svgEl('text', {x: x0 + 4, y: y + dy + 15, 'font-size': 11, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); e.textContent = l + ': not composed (' + st(v) + ')'; return; }
      const w = sx(vv) - x0; const rc = svgEl('rect', {x: x0, y: y + dy + 2, width: w, height: 18, fill: st(v) === 'measured' ? css(c) : `url(#${h})`}, svg);
      const e = svgEl('text', {x: x0 + w + 6, y: y + dy + 16, 'font-size': 11.5, 'font-family': 'var(--f-mono)', fill: css('--ink')}, svg); e.textContent = `${l} ${fmt(vv, 1)}`;
      rc.addEventListener('mousemove', ev => showTip(`<b>${esc(name)} · ${l}</b><br>${fmt(vv, 1)} tok/s · ${esc(st(v))}<br><span style="opacity:.8">${esc(v.src)}</span>`, ev)); rc.addEventListener('mouseleave', hideTip);
    });
    if (cond){ [[cond[0], 0], [cond[1], 24]].forEach(([v, dy]) => { svgEl('rect', {x: x0, y: y + dy + 2, width: sx(val(v)) - x0, height: 18, fill: 'none', stroke: css('--ink'), 'stroke-dasharray': '3 2', 'stroke-width': 1}, svg); }); }
  });
  $('cmpLegend').innerHTML = `<span><i class="sw" style="background:var(--k-field)"></i>AR, measured composition</span><span><i class="sw" style="background:var(--k-attn)"></i>MTP, measured composition</span><span><i class="sw" style="background:repeating-linear-gradient(45deg,var(--k-field) 0 2px,transparent 2px 5px)"></i>analytical (priced wire or unadmitted levers)</span><span>DeepSeek ROM / HBM: AR ${vs(DATA.ratios.ds_ar, 3)}×, MTP ${vs(DATA.ratios.ds_mtp, 3)}× ${pill(st(DATA.ratios.ds_ar))}</span>`;
  // spec table
  const sp = val(DATA.spec_table);
  $('specTable').innerHTML = `<thead><tr><th>Machine</th><th>Shared cost of a step</th><th class="n">AR layer</th><th class="n">Verify (positions)</th><th class="n">Verify ÷ AR</th><th class="n">Spec ÷ AR</th></tr></thead><tbody>${sp.map(r => `<tr><td>${esc(r[0])}</td><td>${esc(r[1])}</td><td class="n">${typeof r[2] === 'number' ? fmt0(r[2]) : esc(r[2])}</td><td class="n">${esc(r[3])}</td><td class="n">${fmt(r[4], 2)}×</td><td class="n">${fmt(r[5], 2)}×</td></tr>`).join('')}</tbody>`;
  $('specSrc').innerHTML = `${pill(st(DATA.spec_table))} ${esc(DATA.spec_table.src)} — ${esc(DATA.spec_table.note)}`;
  const ch = val(DATA.fused_chains);
  $('chainTable').innerHTML = `<thead><tr><th>Chain</th><th class="n">Before µs</th><th class="n">After µs</th><th class="n">Cycles</th><th>Status</th></tr></thead><tbody>${ch.map(r => `<tr><td>${esc(r[0])}</td><td class="n">${fmt(r[1], 3)}</td><td class="n">${fmt(r[2], 3)}</td><td class="n">${fmt0(r[3])}</td><td>${esc(r[4])}</td></tr>`).join('')}</tbody>`;
  $('chainSrc').innerHTML = `${pill(st(DATA.fused_chains))} ${esc(DATA.fused_chains.src)}`;
  $('principles').innerHTML = val(DATA.principles).map(p => `<article class="pcard"><h3>${esc(p[0])}</h3><p>${esc(p[1])}</p><p class="cons">${esc(p[2])}</p></article>`).join('') + `<p class="src muted" style="font:11px var(--f-mono);grid-column:1/-1">${pill(st(DATA.principles))} ${esc(DATA.principles.src)}</p>`;
}

/* ================================================================ element stories (section 7)
   Cards come from DATA.stories (tools/chip_explorer_stories.py). Every number in a card's prose is a fact listed
   in its reviewer table with the record it came from. Diagrams are schematic and step one event at a time; bar
   charts plot recorded values only. */
const ST = { target: lsGet('stTarget', 'all'), status: lsGet('stStatus', 'all'), open: new Set(), mode: {}, step: {}, timers: {} };
const ST_TARGET = { ds: 'DeepSeek ROM array', hbm: 'HBM accelerator', qwen: 'Qwen ROM', x: 'Cross-cutting' };
const ST_ORDER = ['ds', 'hbm', 'qwen', 'x'];
const ST_STATUS = ['closed', 'in progress', 'gated', 'reference'];
const DGK = { bad: '--s-open', good: '--s-closed', field: '--k-field', su: '--k-su', ctrl: '--k-ctrl', hbm: '--k-hbm', wire: '--k-wire', idle: '--k-res',
  op0: '--k-field', op1: '--k-attn', op2: '--k-hc', op3: '--k-ctrl' };
function sbadge(s){ return `<span class="sb sb-${esc(s.replace(' ', '-'))}"><i></i>${esc(s)}</span>`; }
function stCards(){ return (DATA.stories && DATA.stories.cards) || []; }
function stFiltered(){ return stCards().filter(c => (ST.target === 'all' || c.target === ST.target) && (ST.status === 'all' || c.status === ST.status)); }
function stFmt(f){ const v = f.v; if (typeof v !== 'number') return esc(v); const d = Number.isInteger(v) && Math.abs(v) >= 1 ? 0 : (Math.abs(v) < 10 ? 3 : 2); return fmt(v, d).replace('-', '−'); }

function renderStories(){
  const cards = stCards();
  if (!cards.length){ $('stCount').textContent = 'No story data in this build.'; return; }
  const cnt = (key, val) => cards.filter(c => c[key] === val).length;
  const chip = (grp, val, label, n) => `<button type="button" class="chip" data-st-${grp}="${esc(val)}" aria-pressed="${ST[grp] === val}">${esc(label)} <span class="muted">${n}</span></button>`;
  $('stFilters').innerHTML =
    `<span class="lab">Target</span><div class="chips" role="group" aria-label="Filter by target">${chip('target', 'all', 'All', cards.length)}${ST_ORDER.map(t => chip('target', t, ST_TARGET[t], cnt('target', t))).join('')}</div>` +
    `<span class="lab">Status</span><div class="chips" role="group" aria-label="Filter by status">${chip('status', 'all', 'All', cards.length)}${ST_STATUS.map(s => chip('status', s, s, cnt('status', s))).join('')}</div>`;
  $('stFilters').querySelectorAll('[data-st-target]').forEach(b => b.onclick = () => { ST.target = b.dataset.stTarget; lsSet('stTarget', ST.target); renderStories(); });
  $('stFilters').querySelectorAll('[data-st-status]').forEach(b => b.onclick = () => { ST.status = b.dataset.stStatus; lsSet('stStatus', ST.status); renderStories(); });
  const shown = stFiltered();
  $('stCount').textContent = `${shown.length} of ${cards.length} stories` + (ST.target !== 'all' || ST.status !== 'all' ? ' match the filter.' : '.');
  $('stGroups').innerHTML = ST_ORDER.map(t => {
    const cs = shown.filter(c => c.target === t); if (!cs.length) return '';
    return `<div class="st-group"><h3>${esc(ST_TARGET[t])} <small>${cs.length} ${cs.length === 1 ? 'story' : 'stories'}</small></h3><div class="st-grid">${cs.map(stCardHtml).join('')}</div></div>`;
  }).join('') || '<p class="muted">No story matches this filter.</p>';
  $('stGroups').querySelectorAll('[data-st-open]').forEach(b => b.onclick = () => stToggle(b.dataset.stOpen));
  $('stSrc').textContent = `Status is recomputed at build time from committed closure-loop verdicts (results/closure_loop/*/verdict.json); routes not yet closed are shown from the ${DATA.stories.loop_src}. Diagrams are schematic; bar charts plot recorded values.`;
  shown.filter(c => ST.open.has(c.id)).forEach(stBind);
}
function stCardHtml(c){
  const open = ST.open.has(c.id);
  return `<article class="st-card" id="story-${esc(c.id)}" data-open="${open}">
    <div class="top"><div class="el">${esc(ST_TARGET[c.target])} · ${esc(c.element)}</div>${sbadge(c.status)}</div>
    <h4>${esc(c.title)}</h4>
    <p class="sum">${esc(c.summary)}</p>
    ${open ? stBodyHtml(c) : ''}
    <button type="button" class="btn small open" data-st-open="${esc(c.id)}" aria-expanded="${open}" aria-controls="story-${esc(c.id)}">${open ? 'Close story' : 'Open story'}</button>
  </article>`;
}
function stToggle(id){
  if (ST.open.has(id)){ ST.open.delete(id); stStop(id + '/main'); stStop(id + '/extra'); } else ST.open.add(id);
  renderStories();
  const el = $('story-' + id); if (el && ST.open.has(id)) el.scrollIntoView({behavior: reduceMotion ? 'auto' : 'smooth', block: 'start'});
  try { history.replaceState(null, '', ST.open.has(id) ? '#story-' + id : location.pathname + location.search); } catch (e) {}
}
function stDiaHtml(c, which, title){
  const key = c.id + '/' + which;
  return `<div class="st-dia" data-dia="${esc(key)}">
    <div class="tools">
      ${which === 'main' ? `<div class="seg" role="group" aria-label="Design shown"><button type="button" data-mode="naive" aria-pressed="${(ST.mode[c.id] || 'trick') === 'naive'}">Naive design</button><button type="button" data-mode="trick" aria-pressed="${(ST.mode[c.id] || 'trick') === 'trick'}">The trick</button></div>` : `<span class="eyebrow">${esc(title || '')}</span>`}
      <button type="button" class="btn small" data-act="back" aria-label="Previous step">&#9664; Step</button>
      <button type="button" class="btn small" data-act="play" aria-pressed="false">Play</button>
      <button type="button" class="btn small" data-act="fwd" aria-label="Next step">Step &#9654;</button>
      <span class="ctr" data-ctr></span>
    </div>
    ${which === 'main' ? '<div class="txt"><h6 data-ttl></h6><p data-txt></p></div>' : ''}
    <div class="scroll"><svg role="img" data-svg></svg></div>
    <p class="cap" data-cap aria-live="polite"></p>
    <p class="schem" data-schem></p>
  </div>`;
}
function stBodyHtml(c){
  const facts = c.facts.map(f => `<tr><td>${esc(f.label)}</td><td class="n">${stFmt(f)}</td><td>${esc(f.unit)}</td><td>${pill(f.status)}</td><td class="src">${esc(f.src)}</td></tr>`).join('');
  const blocks = (c.blocks || []).map(b => `<tr><td class="mono" style="font-size:12px">${esc(b.block)}</td><td>${b.closed ? sbadge('closed') + ` SS ${fmt(b.closed.ss, 2)} / FF ${fmt(b.closed.ff, 2)} ps` : (b.best_fail ? `best so far SS ${fmt(b.best_fail.ss_ps, 2)} / FF ${fmt(b.best_fail.ff_ps, 2)} ps (${esc(b.best_fail.status)})` : 'no measured route yet')}${b.live ? `; ${b.live} route${b.live > 1 ? 's' : ''} queued or running` : ''}</td><td class="src">${b.closed ? esc(b.closed.src) : esc(b.best_fail ? b.best_fail.job : (b.live_jobs || []).join(', '))}</td></tr>`).join('');
  const tried = c.tried.length ? `<ul>${c.tried.map(t => `<li><b>${esc(t.name)}</b>: ${esc(t.result)}. ${esc(t.why)} <span class="recs">[${esc(t.src)}]</span></li>`).join('')}</ul>` : `<p class="muted">No failed variant of this element was routed. The naive design above is the one the model or the first measurement rejected.</p>`;
  return `<div class="st-body">
    <div><h5>The problem</h5><p>${esc(c.problem)}</p></div>
    ${stDiaHtml(c, 'main')}
    ${c.diagram && c.diagram.extra ? stDiaHtml(c, 'extra', c.diagram.extra.title) : ''}
    <div class="st-pair"><div><h5>Evidence</h5><p>${esc(c.evidence)}</p></div><div><h5>Price paid</h5><p>${esc(c.price)}</p></div></div>
    <details><summary>Reviewer depth: every number, its status and its record</summary>
      <p class="muted" style="font-size:13px;margin:4px 0 8px">Status: ${sbadge(c.status)} ${esc(c.status_basis || DATA.stories.legend[c.status] || '')}</p>
      <div class="scroll"><table><thead><tr><th>Fact</th><th class="n">Value</th><th>Unit</th><th>Status</th><th>Record</th></tr></thead><tbody>${facts}</tbody></table></div>
      ${blocks ? `<h5 style="margin-top:12px">Closure blocks</h5><div class="scroll"><table><thead><tr><th>Block</th><th>State</th><th>Record</th></tr></thead><tbody>${blocks}</tbody></table></div>` : ''}
      <h5 style="margin-top:12px">Records</h5><p class="recs">${c.records.map(esc).join('<br>')}</p>
    </details>
    <details><summary>What we tried first (${c.tried.length})</summary>${tried}</details>
  </div>`;
}
function stSpec(c, which){ const d = c.diagram || {}; return which === 'extra' ? d.extra : (ST.mode[c.id] || 'trick') === 'naive' ? d.naive : d.trick; }
function stNSteps(sp){ if (!sp) return 1; if (sp.steps && sp.steps.length) return sp.steps.length; if (sp.kind === 'pipe' || sp.kind === 'ring') return sp.cycles; return 1; }
function stBind(c){
  const card = $('story-' + c.id); if (!card) return;
  card.querySelectorAll('[data-dia]').forEach(box => {
    const key = box.dataset.dia, which = key.split('/')[1];
    box.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => { ST.mode[c.id] = b.dataset.mode; ST.step[key] = 0; stStop(key); box.querySelectorAll('[data-mode]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); stDraw(c, which); });
    box.querySelector('[data-act="back"]').onclick = () => { stStop(key); ST.step[key] = Math.max(0, (ST.step[key] || 0) - 1); stDraw(c, which); };
    box.querySelector('[data-act="fwd"]').onclick = () => { stStop(key); ST.step[key] = Math.min(stNSteps(stSpec(c, which)) - 1, (ST.step[key] || 0) + 1); stDraw(c, which); };
    box.querySelector('[data-act="play"]').onclick = e => {
      if (ST.timers[key]){ stStop(key); return; }
      const n = stNSteps(stSpec(c, which)); if ((ST.step[key] || 0) >= n - 1) ST.step[key] = 0;
      e.currentTarget.setAttribute('aria-pressed', 'true'); e.currentTarget.textContent = 'Pause'; stDraw(c, which);
      ST.timers[key] = setInterval(() => { const m = stNSteps(stSpec(c, which)); if ((ST.step[key] || 0) >= m - 1){ stStop(key); return; } ST.step[key] = (ST.step[key] || 0) + 1; stDraw(c, which); }, 1100);
    };
    if (ST.step[key] == null) ST.step[key] = which === 'main' ? 0 : 0;
    stDraw(c, which);
  });
}
function stStop(key){ if (ST.timers[key]){ clearInterval(ST.timers[key]); delete ST.timers[key]; } const box = document.querySelector(`[data-dia="${key}"]`); if (box){ const p = box.querySelector('[data-act="play"]'); if (p){ p.setAttribute('aria-pressed', 'false'); p.textContent = 'Play'; } } }
function stDraw(c, which){
  const key = c.id + '/' + which, box = document.querySelector(`[data-dia="${key}"]`); if (!box) return;
  const sp = stSpec(c, which); const n = stNSteps(sp); const i = Math.min(ST.step[key] || 0, n - 1);
  if (which === 'main'){
    const naive = (ST.mode[c.id] || 'trick') === 'naive', t = naive ? c.naive : c.trick;
    box.querySelector('[data-ttl]').textContent = (naive ? 'Naive: ' : 'Trick: ') + (t ? t.title : '');
    box.querySelector('[data-txt]').textContent = t ? t.text : '';
  }
  const svg = box.querySelector('[data-svg]'), wrap = svg.parentNode;
  const W = Math.max(300, Math.floor(wrap.clientWidth - 16 || 600));
  clear(svg);
  const cap = stDiagram(svg, sp, i, W);
  box.querySelector('[data-ctr]').textContent = `step ${i + 1} / ${n}`;
  box.querySelector('[data-cap]').textContent = cap || '';
  box.querySelector('[data-schem]').textContent = sp && (sp.kind === 'bars') ? 'Bars plot recorded values (reviewer table).' : (sp && sp.note ? sp.note : 'Schematic: positions illustrate the mechanism; measured cycles and slacks are in the reviewer table.');
}
function dgc(k){ return css(DGK[k] || '--k-wire'); }
function stDiagram(svg, sp, i, W){
  if (!sp) { sizeSvg(svg, W, 40); txt(svg, 8, 24, 'No diagram for this view.'); return ''; }
  const f = { flow: dgFlow, pipe: dgPipe, gantt: dgGantt, bars: dgBars, ring: dgRing, timeline: dgTimeline, fanout: dgFanout }[sp.kind];
  return f ? f(svg, sp, i, W) : '';
}
function dgBox(svg, x, y, w, h, label, k, hot, bad){
  const g = svgEl('g', {class: 'dg-node' + (hot ? ' hot' : '')}, svg);
  const col = dgc(k);
  svgEl('rect', {x, y, width: w, height: h, rx: 3, fill: mix(css('--surface'), col, hot ? .32 : .14), stroke: hot ? (bad ? css('--s-open') : css('--accent')) : col}, g);
  const fs = w < 110 ? 10.5 : 12; const ls = wrapLines(label, w - 10, fs); const lh = fs * 1.25; const y0 = y + h / 2 - (ls.length - 1) * lh / 2 + fs * .35;
  ls.forEach((l, j) => txt(g, x + w / 2, y0 + j * lh, l, {fs, anchor: 'middle', fill: css('--ink'), mono: false}));
  return g;
}
function dgFlow(svg, sp, i, W){
  const st = (sp.steps || [])[i] || {}; const hot = new Set(st.hot || []); const pk = new Set(st.pk || []);
  const cols = sp.cols, rows = sp.rows, colW = W / cols, bw = Math.max(70, colW - 18);
  const lines = n => wrapLines(n.label, bw - 10, bw < 110 ? 10.5 : 12).length;
  const bh = Math.max(42, Math.max(...sp.nodes.map(lines)) * 15 + 16), rowH = bh + 50, H = rows * rowH + 6;
  sizeSvg(svg, W, H);
  const pos = {}; sp.nodes.forEach(n => { pos[n.id] = {x: n.c * colW + (colW - bw) / 2, y: n.r * rowH + 22, w: bw, h: bh}; });
  const defs = svgEl('defs', {}, svg); const mk = svgEl('marker', {id: 'dgArr', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse'}, defs);
  svgEl('path', {d: 'M0,0 L10,5 L0,10 z', fill: css('--muted')}, mk);
  const mk2 = svgEl('marker', {id: 'dgArrBad', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse'}, defs);
  svgEl('path', {d: 'M0,0 L10,5 L0,10 z', fill: css('--s-open')}, mk2);
  const edge = (a, b) => { const A = pos[a], B = pos[b]; const ac = [A.x + A.w / 2, A.y + A.h / 2], bc = [B.x + B.w / 2, B.y + B.h / 2];
    const clip = (P, c, d) => { const dx = d[0] - c[0], dy = d[1] - c[1]; const tx = dx ? (P.w / 2) / Math.abs(dx) : 1e9, ty = dy ? (P.h / 2) / Math.abs(dy) : 1e9; const t = Math.min(tx, ty); return [c[0] + dx * t, c[1] + dy * t]; };
    const back = (B.x < A.x && Math.abs(B.y - A.y) < 1) || (B.x === A.x && B.y === A.y);
    if (back){ const s = [A.x + A.w / 2, A.y], e = [B.x + B.w / 2, B.y]; const cy = A.y - 20; return {d: `M${s[0]},${s[1]} C${s[0]},${cy} ${e[0]},${cy} ${e[0]},${e[1] - 1}`, mid: [(s[0] + e[0]) / 2, cy + 5]}; }
    const s = clip(A, ac, bc), e = clip(B, bc, ac); return {d: `M${s[0]},${s[1]} L${e[0]},${e[1]}`, mid: [(s[0] + e[0]) / 2, (s[1] + e[1]) / 2]}; };
  const paths = sp.edges.map((e, j) => { const g = edge(e.a, e.b); const on = pk.has(j); const bad = e.bad && (on || st.bad);
    svgEl('path', {d: g.d, class: 'dg-edge', stroke: bad ? css('--s-open') : (on ? css('--accent') : css('--muted')), 'stroke-width': on ? 2.6 : 1.4, 'stroke-dasharray': e.bad && !on ? '4 4' : '', 'marker-end': bad ? 'url(#dgArrBad)' : 'url(#dgArr)', opacity: on || !pk.size ? 1 : .55}, svg);
    g.el = svg.lastChild; g.lab = e.l; g.bad = bad;
    return g; });
  sp.nodes.forEach(n => { const p = pos[n.id]; dgBox(svg, p.x, p.y, p.w, p.h, n.label, n.k, hot.has(n.id), st.bad); });
  paths.forEach(g => { if (!g.lab) return; const tw = g.lab.length * 6.3; const x = Math.max(2, Math.min(W - tw - 2, g.mid[0] + 4));
    const bg = svgEl('rect', {x: x - 2, y: g.mid[1] - 15, width: tw + 4, height: 13, fill: css('--surface-2'), opacity: .85}, svg); txt(svg, x, g.mid[1] - 5, g.lab, {fs: 10.5, fill: g.bad ? css('--s-open') : css('--muted')}); });
  pk.forEach(j => { const g = paths[j]; if (!g || !g.el) return; const dot = svgEl('circle', {r: 5.5, fill: st.bad && sp.edges[j].bad ? css('--s-open') : css('--packet'), class: 'dg-pk', cx: g.mid[0], cy: g.mid[1]}, svg);
    let L = 0; try { L = g.el.getTotalLength(); } catch (e) {} if (!L) return;
    const put = f => { const q = g.el.getPointAtLength(L * f); dot.setAttribute('cx', q.x); dot.setAttribute('cy', q.y); };
    if (reduceMotion){ put(.6); return; }
    const t0 = performance.now(); put(0); const step = now => { if (!dot.isConnected) return; const f = Math.min(1, (now - t0) / 900); put(f); if (f < 1) requestAnimationFrame(step); }; requestAnimationFrame(step); });
  return st.note || '';
}
function dgAxis(svg, x0, x1, y, span, unit, ticks){
  svgEl('line', {x1: x0, x2: x1, y1: y, y2: y, stroke: css('--line')}, svg);
  niceTicks(0, span, ticks || 5).forEach(v => { const x = x0 + (x1 - x0) * v / span; svgEl('line', {x1: x, x2: x, y1: y, y2: y + 4, stroke: css('--muted')}, svg); txt(svg, x, y + 15, fmt(v, span < 5 ? 1 : 0), {fs: 10, anchor: 'middle'}); });
  txt(svg, x1, y + 28, unit, {fs: 10, anchor: 'end'});
}
function dgGantt(svg, sp, i, W){
  const st = (sp.steps || [])[i] || {t: sp.span}; const t = st.t == null ? sp.span : st.t;
  const lab = W < 480 ? 74 : 110, x0 = lab, x1 = W - 10, rh = 30, H = sp.rows.length * rh + 46; sizeSvg(svg, W, H);
  const X = v => x0 + (x1 - x0) * v / sp.span;
  sp.rows.forEach((r, j) => txtWrap(svg, 4, 12 + j * rh + 8, r, lab - 8, {fs: 11, fill: css('--ink'), mono: false}));
  sp.bars.forEach(b => { const on = b.start < t; const x = X(b.start), w = Math.max(1.2, X(b.start + b.len) - x); const y = 6 + b.row * rh;
    svgEl('rect', {x, y, width: w, height: rh - 8, fill: dgc(b.k), opacity: on ? .9 : .18, stroke: css('--surface'), 'stroke-width': .6}, svg);
    if (b.label && w > b.label.length * 6.2 + 6) txt(svg, x + 4, y + (rh - 8) / 2 + 4, b.label, {fs: 10.5, fill: on ? css('--bg') : css('--muted')}); });
  const xc = X(Math.min(t, sp.span)); svgEl('line', {x1: xc, x2: xc, y1: 2, y2: sp.rows.length * rh + 2, stroke: css('--accent'), 'stroke-width': 2}, svg);
  dgAxis(svg, x0, x1, sp.rows.length * rh + 6, sp.span, sp.unit || '');
  return st.note || '';
}
function dgBars(svg, sp, i, W){
  const st = (sp.steps || [])[i] || {show: sp.bars.length}; const show = st.show == null ? sp.bars.length : st.show;
  const lab = W < 480 ? 120 : 190, x0 = lab, x1 = W - 70, bh = 24, gap = 10, H = sp.bars.length * (bh + gap) + 40; sizeSvg(svg, W, H);
  const mx = sp.max || Math.max(...sp.bars.map(b => b.v), sp.limit ? sp.limit.v : 0) * 1.05; const X = v => x0 + (x1 - x0) * v / mx;
  sp.bars.forEach((b, j) => { const y = 6 + j * (bh + gap), on = j < show;
    txtWrap(svg, 4, y + 10, b.label, lab - 10, {fs: 11, fill: css('--ink'), mono: false, lh: 12});
    svgEl('rect', {x: x0, y, width: Math.max(1.5, X(b.v) - x0), height: bh, fill: dgc(b.k), opacity: on ? .9 : .18}, svg);
    if (on) txt(svg, X(b.v) + 5, y + bh / 2 + 4, fmt(b.v, b.v < 10 && b.v % 1 ? 3 : (b.v % 1 ? 1 : 0)), {fs: 11, fill: css('--ink')}); });
  if (sp.limit){ const x = X(sp.limit.v); svgEl('line', {x1: x, x2: x, y1: 0, y2: sp.bars.length * (bh + gap), stroke: css('--accent'), 'stroke-width': 2, 'stroke-dasharray': '5 3'}, svg); txt(svg, Math.min(x, x1) - 2, sp.bars.length * (bh + gap) + 12, sp.limit.label + ' ' + fmt(sp.limit.v, 2), {fs: 10.5, anchor: 'end', fill: css('--accent')}); }
  dgAxis(svg, x0, x1, sp.bars.length * (bh + gap) + (sp.limit ? 16 : 2), mx, sp.unit || '', 4);
  return (st.note || '') + (sp.marker && i === (sp.steps || []).length - 1 ? ' ' + sp.marker.label + '.' : '');
}
function dgPipe(svg, sp, i, W){
  const lab = 60, cw = Math.max(26, Math.min(48, (W - lab - 8) / sp.cycles)), rh = 26; const Wd = Math.max(W, lab + cw * sp.cycles + 8), H = sp.stages * rh + 40; sizeSvg(svg, Wd, H);
  for (let s = 0; s < sp.stages; s++) txt(svg, 4, 16 + s * rh + 4, 'stage ' + (s + 1), {fs: 10.5});
  for (let cyc = 0; cyc < sp.cycles; cyc++){ const x = lab + cyc * cw; if (cyc === i) svgEl('rect', {x, y: 2, width: cw, height: sp.stages * rh, fill: mix(css('--surface-2'), css('--accent'), .18)}, svg); txt(svg, x + cw / 2, sp.stages * rh + 16, String(cyc), {fs: 10, anchor: 'middle'}); }
  let busy = 0;
  sp.lanes.forEach((ln, li) => { for (let k = 0; ; k++){ const st = ln.start + k * (ln.every || 1e9); if (st > i || st >= sp.cycles) break;
    for (let s = 0; s < sp.stages; s++){ const cyc = st + s; if (cyc > i || cyc >= sp.cycles) break; const x = lab + cyc * cw, y = 2 + s * rh;
      svgEl('rect', {x: x + 1, y: y + 1, width: cw - 2, height: rh - 2, rx: 2, fill: css(['--k-field', '--k-attn', '--k-hc', '--k-ctrl', '--k-su', '--k-hbm'][li % 6]), opacity: cyc === i ? .95 : .55}, svg);
      if (cw >= 30) txt(svg, x + cw / 2, y + rh / 2 + 4, ln.label.replace('slot ', 's'), {fs: 10, anchor: 'middle', fill: css('--bg')}); if (cyc === i) busy++; } } });
  txt(svg, Wd - 4, H - 6, 'cycle', {fs: 10, anchor: 'end'});
  return `Cycle ${i}: ${busy} of ${sp.stages} adder stages busy.`;
}
function dgRing(svg, sp, i, W){
  const N = sp.slots, cw = Math.min(70, (W - 20) / N), H = 118; sizeSvg(svg, W, H); const x0 = (W - cw * N) / 2;
  const rd = i - sp.offset;
  for (let s = 0; s < N; s++){ const x = x0 + s * cw; const age = (i - s) >= 0 ? ((i - s) % N) : null; const written = s <= i || i >= N;
    const isW = s === i % N, isR = rd >= 0 && s === rd % N, isG = rd >= 0 && s === (rd + sp.guard) % N;
    svgEl('rect', {x: x + 2, y: 34, width: cw - 4, height: 34, rx: 2, fill: written ? mix(css('--surface'), css('--k-field'), .2 + .5 * (1 - ((i - s + N * 4) % N) / N)) : css('--surface'), stroke: isR ? css('--s-closed') : isG ? css('--s-enc') : css('--line'), 'stroke-width': isR || isG ? 2.4 : 1}, svg);
    txt(svg, x + cw / 2, 56, 'slot ' + s, {fs: 10, anchor: 'middle', fill: css('--ink')});
    if (isW) txt(svg, x + cw / 2, 26, 'write', {fs: 10.5, anchor: 'middle', fill: css('--k-field'), weight: 600});
    if (isR) txt(svg, x + cw / 2, 84, 'read', {fs: 10.5, anchor: 'middle', fill: css('--s-closed'), weight: 600});
    if (isG) txt(svg, x + cw / 2, 98, 'guard', {fs: 10.5, anchor: 'middle', fill: css('--s-enc'), weight: 600}); }
  txt(svg, W / 2, 14, `cycle ${i}`, {fs: 11, anchor: 'middle'});
  return rd < 0 ? `Cycle ${i}: the writer fills slot ${i % N}; the reader was placed ${sp.offset} periods behind and has not started.` : `Cycle ${i}: write slot ${i % N}, read slot ${rd % N} (written ${sp.offset} cycles ago), guard on slot ${(rd + sp.guard) % N}.`;
}
function dgTimeline(svg, sp, i, W){
  const st = (sp.steps || [])[i] || {t: sp.span}; const lab = W < 480 ? 96 : 140, x0 = lab, x1 = W - 10, rh = 28, H = sp.lanes.length * rh + 50; sizeSvg(svg, W, H);
  const X = v => x0 + (x1 - x0) * v / sp.span;
  sp.lanes.forEach((ln, j) => { const y = 6 + j * rh; txtWrap(svg, 4, y + 12, ln.label, lab - 8, {fs: 11, fill: css('--ink'), mono: false});
    svgEl('rect', {x: X(Math.max(0, ln.start)), y, width: Math.max(2, X(ln.start + ln.len) - X(Math.max(0, ln.start))), height: rh - 8, fill: dgc(ln.k), opacity: ln.start < st.t ? .9 : .2}, svg); });
  const xp = X(sp.period); svgEl('line', {x1: xp, x2: xp, y1: 0, y2: sp.lanes.length * rh + 6, stroke: css('--s-open'), 'stroke-width': 2, 'stroke-dasharray': '5 3'}, svg);
  txt(svg, xp - 3, sp.lanes.length * rh + 2, 'next edge ' + sp.period + ' ps', {fs: 10, anchor: 'end', fill: css('--s-open')});
  dgAxis(svg, x0, x1, sp.lanes.length * rh + 12, sp.span, 'ps (schematic)', 4);
  return st.note || '';
}
function dgFanout(svg, sp, i, W){
  const H = 190; sizeSvg(svg, W, H); const n = sp.loads, cps = sp.copies; const lx = Math.min(W - 30, W * .8), dx = Math.max(60, W * .18);
  const ly = j => 14 + j * ((H - 28) / (n - 1));
  for (let c = 0; c < cps; c++){ const cy = cps === 1 ? H / 2 : 30 + c * ((H - 60) / (cps - 1));
    for (let j = c * n / cps; j < (c + 1) * n / cps; j++) svgEl('line', {x1: dx + 40, y1: cy, x2: lx, y2: ly(j), stroke: cps === 1 ? css('--s-open') : css('--s-closed'), 'stroke-width': .9, opacity: .7}, svg);
    svgEl('rect', {x: dx, y: cy - 12, width: 40, height: 24, rx: 2, fill: mix(css('--surface'), cps === 1 ? css('--s-open') : css('--s-closed'), .25), stroke: cps === 1 ? css('--s-open') : css('--s-closed')}, svg);
    txt(svg, dx + 20, cy + 4, cps === 1 ? 'reg' : 'kreg', {fs: 10, anchor: 'middle', fill: css('--ink')}); }
  for (let j = 0; j < n; j++) svgEl('circle', {cx: lx + 6, cy: ly(j), r: 3, fill: css('--k-field')}, svg);
  txt(svg, lx + 14, H / 2 + 4, n + ' loads', {fs: 10.5});
  return sp.note || '';
}
function stRedraw(){ stCards().filter(c => ST.open.has(c.id)).forEach(c => { stDraw(c, 'main'); if (c.diagram && c.diagram.extra) stDraw(c, 'extra'); }); }
function stFromHash(){ const h = decodeURIComponent(location.hash || ''); if (h.indexOf('#story-') === 0){ const id = h.slice(7); if (stCards().some(c => c.id === id)){ ST.open.add(id); ST.target = 'all'; ST.status = 'all'; renderStories(); const el = $('story-' + id); if (el) el.scrollIntoView({block: 'start'}); return true; } } return false; }

/* ================================================================ provenance drawer */
let provFilter = 'all';
function renderProv(){
  const leaves = []; walk(DATA, '', (p, l) => leaves.push([p, l]));
  const c = {}; leaves.forEach(([, l]) => { c[l.status] = (c[l.status] || 0) + 1; });
  $('provFilter').innerHTML = ['all', 'measured', 'analytical', 'estimate', 'placeholder'].map(s => `<button type="button" class="chip" data-pf="${s}" aria-pressed="${provFilter === s}">${s} ${s === 'all' ? leaves.length : (c[s] || 0)}</button>`).join('');
  $('provFilter').querySelectorAll('[data-pf]').forEach(b => b.onclick = () => { provFilter = b.dataset.pf; renderProv(); });
  $('provSummary').textContent = `${leaves.length} values. Each carries its status and the record it came from. Geometry and node lists are summarised by size.`;
  const show = v => { if (v == null) return '—'; if (Array.isArray(v)) return `[${v.length} entries]`; if (typeof v === 'object') return v.rects ? `[${v.rects.length} rectangles]` : `{${Object.keys(v).length} fields}`; if (typeof v === 'number') return fmt(v, Math.abs(v) < 10 && v % 1 ? 3 : (v % 1 ? 1 : 0)); return esc(v); };
  $('provTable').innerHTML = `<thead><tr><th>Value</th><th class="n">v</th><th>Unit</th><th>Status</th><th>Source</th></tr></thead><tbody>${leaves.filter(([, l]) => provFilter === 'all' || l.status === provFilter).map(([p, l]) => `<tr><td class="mono" style="font-size:11.5px">${esc(p)}</td><td class="n">${show(l.v)}</td><td>${esc(l.unit)}</td><td>${pill(l.status)}</td><td class="src">${esc(l.src)}${l.note ? '<br>' + esc(l.note) : ''}</td></tr>`).join('')}</tbody>`;
}
function openDrawer(){ renderProv(); $('drawer').hidden = false; $('scrim').hidden = false; $('drawerClose').focus(); }
function closeDrawer(){ $('drawer').hidden = true; $('scrim').hidden = true; $('provBtn').focus(); }

/* ================================================================ wiring */
function renderAll(){
  renderNotice(); renderHero(); renderArray(); renderRack(); dieTools(); drawDie();
  const wasPlaying = TK.playing; TK.playing = false; buildSteps(); drawToken(); if (wasPlaying && !reduceMotion){ TK.playing = true; requestAnimationFrame(tick); }
  renderWaterfall(); renderClosure(); renderLevers(); renderCompare();
}
document.querySelectorAll('[data-design]').forEach(b => b.addEventListener('click', () => { state.design = b.dataset.design; lsSet('design', state.design); state.sel = null; state.hidden.clear(); state.cbFilter = 'all'; state.arraySel = null; state.arrayZoom = 'system'; rackState.tray = null; state.dieCtx = null; renderAll(); }));
$('cmpBtn').onclick = () => { state.compare = !state.compare; $('cmpBtn').setAttribute('aria-pressed', String(state.compare)); renderCompareStrip(); if (state.compare) $('cmpStrip').scrollIntoView({behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest'}); };
$('provBtn').onclick = openDrawer; $('drawerClose').onclick = closeDrawer; $('scrim').onclick = closeDrawer;
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('drawer').hidden) closeDrawer(); });
bindDie(); bindToken();
let rz; window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { drawDie(); drawToken(); }, 150); });
// the array and rack views lay out at their panel's width: redraw them when that width changes
if (window.ResizeObserver){ const lastW = {}; const ro = new ResizeObserver(es => { for (const e of es){ const id = e.target.id, w = Math.floor(e.contentRect.width); if (lastW[id] === w) continue; const first = lastW[id] == null; lastW[id] = w; if (first) continue; requestAnimationFrame(() => { if (id === 'arrayScroll') renderArray(); else if (id === 'stGroups') stRedraw(); else drawRack(); }); } }); ro.observe($('arrayScroll')); ro.observe($('rackScroll')); ro.observe($('stGroups')); }
else window.addEventListener('resize', () => { renderArray(); drawRack(); stRedraw(); });
const themeRedraw = () => { renderArray(); renderRack(); drawDie(); drawToken(); renderWaterfall(); renderClosure(); renderLevers(); renderCompare(); stRedraw(); };
if (window.matchMedia) matchMedia('(prefers-color-scheme: dark)').addEventListener('change', themeRedraw);
new MutationObserver(themeRedraw).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
renderAll();
renderStories(); stFromHash(); window.addEventListener('hashchange', stFromHash);
// complete at rest: park the token mid-way through a representative step
(function park(){ const k = TK.steps.findIndex(s => s.kind === 'field' || s.kind === 'stream'); TK.i = k >= 0 ? k : 0; TK.t = TK.steps[TK.i] ? TK.steps[TK.i].dur * .45 : 0; drawToken(); })();
})();

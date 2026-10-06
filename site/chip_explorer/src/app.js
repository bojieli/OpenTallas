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
    lede: 'An 81-stage pipeline of ROM dies. Each layer is spread over a TP4 group of rank dies whose fields of ROM element pairs hold the weights; the token walks the pipeline over die-to-die links and its KV comes from HBM beside every die. MTP speculation fills idle stages with a wavefront of draft positions.',
    dies: ['ds_s81_layer'] },
  hbm: { short: 'HBM accelerator', title: ['HBM', 'accelerator'], ctx: 'matched comparator, same contexts',
    lede: 'The comparator is a GPU-like die: 32 SM compute elements fed by four HBM3E stacks on the long edges, a hub band of serial vector, special-function, hyper-connection and index units, 64 attention tiles and a centre spine. Weights stream from HBM every token; speculation shares that weight stream across the verified positions.',
    dies: ['hbm_ds', 'hbm_qwen'] },
};
const state = { design: lsGet('design', 'ds'), compare: false, hbmModel: lsGet('hbmModel', 'ds'), colorBy: 'kind', zoom: 1,
  hidden: new Set(), showWire: true, showClock: false, showIR: false, sel: null, arraySel: null, arrayZoom: 'system', cbFilter: 'all' };
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
    k = kpi('DeepSeek 1M, AR', R.hbm_ds.AR, 'tok/s', 'wire median; floor ' + fmt(val(R.hbm_ds.AR_floor)) + ', bound ' + fmt(val(R.hbm_ds.AR_bound))) +
        kpi('DeepSeek 1M, MTP', R.hbm_ds.MTP, 'tok/s', 'τ 4.159, same as the ROM') +
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
  s.innerHTML = `<div class="cmp3">${card('Qwen ROM, 8K', [['AR', R.qwen.AR], ['MTP', R.qwen.MTP], ['Die', DATA.dies.qwen_rom.area]])}${card('DeepSeek ROM array, 1M', [['AR', R.ds.AR], ['MTP', R.ds.MTP], ['Die', DATA.ds_system.die_mm2]])}${card('HBM accelerator', [['DS AR', R.hbm_ds.AR], ['DS MTP', R.hbm_ds.MTP], ['Qwen TP4', R.hbm_qwen.AR], ['DS die', DATA.dies.hbm_ds.area]])}</div>`;
}

/* ================================================================ 1. ARRAY */
function renderArray(){
  const svg = $('arraySvg'); clear(svg);
  const tools = $('arrayTools'); const leg = $('arrayLegend');
  const d = state.design;
  if (d === 'ds'){
    $('arrayLede').textContent = 'The token walks the S81 pipeline. Each cell is one stretch of the critical path between two measured stage hops; its four squares are the TP4 rank dies that hold the layer slice, each with HBM beside it. Shade shows how long the stretch keeps the token. Click a cell to zoom into the stage.';
    tools.innerHTML = `<div class="seg" role="group" aria-label="Zoom level"><button type="button" data-az="system" aria-pressed="${state.arrayZoom === 'system'}">System</button><button type="button" data-az="stage" aria-pressed="${state.arrayZoom === 'stage'}">Stage</button></div><span class="muted" style="font-size:12px">${state.arrayZoom === 'stage' ? 'Stage ' + (state.arraySel == null ? 0 : state.arraySel) + ': four rank dies and their links' : 'packages → dies → stages → links'}</span>`;
    tools.querySelectorAll('[data-az]').forEach(b => b.onclick = () => { state.arrayZoom = b.dataset.az; if (state.arraySel == null) state.arraySel = 20; renderArray(); });
    if (state.arrayZoom === 'stage') drawDsStage(svg); else drawDsRibbon(svg);
    leg.innerHTML = `<span><i class="sw" style="background:var(--k-field)"></i>ROM rank die (shade: busy time)</span><span><i class="sw" style="background:var(--k-hbm)"></i>HBM stack</span><span><i class="sw" style="background:var(--k-link)"></i>stage hop ${vs(DATA.ds_hop, 4)} µs ${pill(st(DATA.ds_hop))}</span><span><i class="sw" style="background:repeating-linear-gradient(45deg,var(--k-res) 0 2px,transparent 2px 5px)"></i>S81 hop-only stage, position not in the record</span><span><i class="sw" style="background:var(--k-attn)"></i>draft dies (DP1-EP5)</span>`;
  } else if (d === 'qwen'){
    $('arrayLede').textContent = 'One user’s token runs on a TP4 group: four identical ROM dies, each holding a quarter of every weight matrix and streaming its share of the KV cache from four HBM3E stacks on its east and west edges. The dies meet only at the all-reduce after each attention and MLP block.';
    tools.innerHTML = '<span class="muted" style="font-size:12px">system: 4 dies · 16 HBM3E stacks · TP4 all-reduce</span>';
    drawQwenSystem(svg);
    leg.innerHTML = `<span><i class="sw" style="background:var(--k-field)"></i>ROM die</span><span><i class="sw" style="background:var(--k-hbm)"></i>HBM3E stack</span><span><i class="sw" style="background:var(--k-link)"></i>all-reduce link</span>`;
  } else {
    $('arrayLede').textContent = state.hbmModel === 'qwen' ? 'Qwen3-8B on the HBM accelerator: a TP4 group of tile dies (iso-silicon with the ROM group) or a TP2 group on the same silicon. Every die streams its weight share from its four stacks every token.' : 'DeepSeek-V4.1 at 1M on the HBM accelerator: 96 dies in tensor parallel (TP-96), each with four HBM3E stacks, joined through a Tomahawk-Ultra switch tier. Collectives cross the switch; about a third of the AR token is the vendor budget for that crossing.';
    tools.innerHTML = `<div class="seg" role="group" aria-label="Model"><button type="button" data-hm="ds" aria-pressed="${state.hbmModel === 'ds'}">DeepSeek die</button><button type="button" data-hm="qwen" aria-pressed="${state.hbmModel === 'qwen'}">Qwen tile die</button></div>`;
    tools.querySelectorAll('[data-hm]').forEach(b => b.onclick = () => { state.hbmModel = b.dataset.hm; lsSet('hbmModel', state.hbmModel); state.sel = null; renderAll(); });
    drawHbmSystem(svg);
    leg.innerHTML = `<span><i class="sw" style="background:var(--k-field)"></i>compute die</span><span><i class="sw" style="background:var(--k-hbm)"></i>HBM3E stack</span><span><i class="sw" style="background:var(--k-link)"></i>switch chip / link</span>`;
  }
}
function arrayRead(html){ $('arrayRead').innerHTML = html; }
function dieGlyph(svg, x, y, w, h, fill, stacks, opts = {}){
  const g = svgEl('g', {}, svg);
  svgEl('rect', {x, y, width: w, height: h, fill, stroke: css('--die-edge'), 'stroke-width': 0.8, rx: 1}, g);
  const sw = Math.max(3, w * 0.22), sh = Math.max(3, h * 0.26);
  if (stacks === 'ns'){ for (let i = 0; i < 2; i++){ svgEl('rect', {x: x + w * (0.12 + 0.5 * i), y: y - sh - 1.5, width: sw * 1.2, height: sh, fill: css('--k-hbm')}, g); svgEl('rect', {x: x + w * (0.12 + 0.5 * i), y: y + h + 1.5, width: sw * 1.2, height: sh, fill: css('--k-hbm')}, g); } }
  if (stacks === 'ew'){ for (let i = 0; i < 2; i++){ svgEl('rect', {x: x - sh - 1.5, y: y + h * (0.12 + 0.5 * i), width: sh, height: sw * 1.2, fill: css('--k-hbm')}, g); svgEl('rect', {x: x + w + 1.5, y: y + h * (0.12 + 0.5 * i), width: sh, height: sw * 1.2, fill: css('--k-hbm')}, g); } }
  if (opts.label) { const t = svgEl('text', {x: x + w / 2, y: y + h / 2 + 4, 'text-anchor': 'middle', 'font-size': opts.fs || 11, 'font-family': 'var(--f-mono)'}, g); t.textContent = opts.label; }
  return g;
}
function mix(c1, c2, t){ // hex mix for shading
  const p = c => { c = c.replace('#', ''); if (c.length === 3) c = c.split('').map(x => x + x).join(''); return [0, 2, 4].map(i => parseInt(c.substr(i, 2), 16)); };
  try { const a = p(c1), b = p(c2); return '#' + a.map((v, i) => Math.round(v + (b[i] - v) * t).toString(16).padStart(2, '0')).join(''); } catch (e) { return c1; }
}
function segBusy(s){ let t = 0; for (const k in s.cats) t += s.cats[k]; return t; }
function drawDsRibbon(svg){
  const segs = val(DATA.ds_stages); const extra = val(DATA.ds_extra_hops);
  const perRow = 20, cw = 50, ch = 64, gx = 10, gy = 30, x0 = 20, y0 = 34;
  const total = segs.length + extra.count;
  const rows = Math.ceil(total / perRow);
  const W = x0 * 2 + perRow * (cw + gx), Hrib = y0 + rows * (ch + gy);
  const H = Hrib + 190;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
  const maxB = Math.max(...segs.map(segBusy));
  const bg = css('--die'), fc = css('--k-field');
  const t = svgEl('text', {x: x0, y: 18, 'font-size': 12, 'font-family': 'var(--f-mono)', fill: css('--muted')}); t.textContent = `token → ${segs.length} critical-path stretches + ${extra.count} S81 hop-only stages = ${segs.length + extra.count - 1} stage hops · scroll inside this panel →`; svg.appendChild(t);
  for (let k = 0; k < total; k++){
    const r = Math.floor(k / perRow), c = k % perRow;
    const x = x0 + c * (cw + gx), y = y0 + r * (ch + gy);
    const g = svgEl('g', {tabindex: 0, role: 'button', 'aria-label': k < segs.length ? `Stretch ${k}` : 'Hop-only stage', style: 'cursor:pointer'}, svg);
    if (k < segs.length){
      const s = segs[k], b = segBusy(s), shade = b ? mix(bg, fc, 0.25 + 0.75 * b / maxB) : bg;
      for (let q = 0; q < 4; q++){
        const dx = x + (q % 2) * (cw / 2), dy = y + 10 + Math.floor(q / 2) * (ch / 2 - 6);
        svgEl('rect', {x: dx + 2, y: dy, width: cw / 2 - 6, height: ch / 2 - 12, fill: shade, stroke: state.arraySel === k ? css('--accent') : css('--die-edge'), 'stroke-width': state.arraySel === k ? 2 : 0.7}, g);
        svgEl('rect', {x: dx + 2, y: dy - 4, width: cw / 2 - 6, height: 2.5, fill: css('--k-hbm')}, g);
      }
      const lab = svgEl('text', {x: x + cw / 2 - 2, y: y + ch + 4, 'text-anchor': 'middle', 'font-size': 9.5, 'font-family': 'var(--f-mono)', fill: css('--muted')}, g);
      lab.textContent = s.layers.filter(l => l !== 'token').join('·').replace(/L(\d+)/g, '$1') || 'pass';
      g.addEventListener('mousemove', ev => showTip(`<b>Stretch ${k}</b> · ${esc(s.layers.join(', ') || 'no critical-path work')}<br>busy ${fmt(b, 3)} µs · ${s.n} nodes<br>hop ${fmt(s.hop, 4)} µs ${esc(s.hop_node)}`, ev));
      g.addEventListener('mouseleave', hideTip);
      const pick = () => { state.arraySel = k; renderDsArrayRead(k); drawSelOutline(); };
      g.addEventListener('click', pick); g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); pick(); } });
      g.addEventListener('dblclick', () => { state.arraySel = k; state.arrayZoom = 'stage'; renderArray(); renderDsArrayRead(k); });
    } else {
      const pid = 'hatchArr';
      if (!svg.querySelector('#' + pid)){ const defs = svgEl('defs', {}, svg); const p = svgEl('pattern', {id: pid, width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)'}, defs); svgEl('rect', {width: 2.2, height: 6, fill: css('--k-res')}, p); }
      svgEl('rect', {x: x + 2, y: y + 6, width: cw - 8, height: ch - 18, fill: `url(#${pid})`, stroke: css('--die-edge'), 'stroke-width': 0.6, 'stroke-dasharray': '3 2'}, g);
      g.addEventListener('mousemove', ev => showTip(`<b>S81 hop-only stage</b><br>one of ${extra.count} extra stage hops (${fmt(extra.us_each, 4)} µs each, ${fmt(extra.total, 3)} µs total).<br>Its position in the pipeline is not in the composition record.`, ev));
      g.addEventListener('mouseleave', hideTip);
    }
    if (k < total - 1 && c < perRow - 1) svgEl('line', {x1: x + cw - 3, y1: y + ch / 2, x2: x + cw + gx + 1, y2: y + ch / 2, stroke: css('--k-link'), 'stroke-width': 2}, svg);
  }
  // head dies + draft group
  const yb = Hrib + 12; const S = DATA.ds_system;
  const tt = svgEl('text', {x: x0, y: yb + 4, 'font-size': 12, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg);
  tt.textContent = `head dies ×${val(S.head_dies)} (embed, LM head, norm, DSpark drafter) · draft placement DP1-EP5: ${val(S.draft_primary)} primary + ${val(S.draft_replicas)} expert-replica dies (+${val(S.draft_added)} vs baseline) · ${fmt0(val(S.layer_dies))} layer dies = 81 × TP4`;
  for (let i = 0; i < val(S.head_dies); i++) dieGlyph(svg, x0 + i * 24, yb + 22, 18, 18, mix(bg, css('--k-tree'), .6), null);
  const px = x0 + 330, py = yb + 70;
  for (let i = 0; i < val(S.draft_primary); i++) dieGlyph(svg, px + i * 26, py, 20, 20, css('--k-attn'), null);
  const reps = val(S.draft_replicas);
  for (let i = 0; i < reps; i++){
    const cx = px + 330 + (i % 20) * 22, cy = yb + 34 + Math.floor(i / 20) * 26;
    svgEl('line', {x1: px + 50, y1: py + 10, x2: cx + 8, y2: cy + 8, stroke: css('--k-link'), 'stroke-width': 0.4, opacity: .6}, svg);
    dieGlyph(svg, cx, cy, 16, 16, mix(bg, css('--k-attn'), .45), null);
  }
  const lt = svgEl('text', {x: px, y: py + 40, 'font-size': 10.5, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg);
  lt.textContent = `primary TP4 group · 15 replica links per primary die · draft hop ${vs(S.draft_hop, 3)} µs`;
  svg._outline = true;
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
  const W = 980, H = 420; svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
  const bg = css('--die');
  const t = svgEl('text', {x: 20, y: 24, 'font-size': 13, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg);
  t.textContent = `Stage view · stretch ${k}: ${s ? s.layers.join(', ') : ''} · TP4 rank dies with four HBM3E stacks each`;
  // previous stage stub, four rank dies, next stage stub
  svgEl('rect', {x: 20, y: 150, width: 60, height: 120, fill: 'none', stroke: css('--die-edge'), 'stroke-dasharray': '4 3'}, svg);
  svgEl('rect', {x: W - 80, y: 150, width: 60, height: 120, fill: 'none', stroke: css('--die-edge'), 'stroke-dasharray': '4 3'}, svg);
  const lp = svgEl('text', {x: 50, y: 290, 'text-anchor': 'middle', 'font-size': 11, fill: css('--muted')}, svg); lp.textContent = 'stage k−1';
  const ln = svgEl('text', {x: W - 50, y: 290, 'text-anchor': 'middle', 'font-size': 11, fill: css('--muted')}, svg); ln.textContent = 'stage k+1';
  for (let r = 0; r < 4; r++){
    const x = 150 + r * 180, y = 120, w = 140, h = 110;
    dieGlyph(svg, x, y, w, h, mix(bg, css('--k-field'), .35), 'ns', {label: 'rank ' + r, fs: 13});
    const sub = svgEl('text', {x: x + w / 2, y: y + h + 46, 'text-anchor': 'middle', 'font-size': 10.5, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); sub.textContent = '33 × 26 mm layer die';
    if (r < 3) svgEl('line', {x1: x + w + 4, y1: y + h / 2, x2: x + 176, y2: y + h / 2, stroke: css('--k-link'), 'stroke-width': 2, 'stroke-dasharray': '5 3'}, svg);
    svgEl('line', {x1: 80, y1: 210, x2: x, y2: y + h * 0.8, stroke: css('--k-link'), 'stroke-width': 1.2, opacity: .7}, svg);
    svgEl('line', {x1: x + w, y1: y + h * 0.2, x2: W - 80, y2: 210, stroke: css('--k-link'), 'stroke-width': 1.2, opacity: .7}, svg);
  }
  const n1 = svgEl('text', {x: 150, y: 350, 'font-size': 11.5, fill: css('--ink')}, svg); n1.textContent = 'dashed: TP4 collectives inside the stage (all-gather, all-reduce); solid: stage hop over light-FEC board link + UCIe fan-out.';
  const n2 = svgEl('text', {x: 150, y: 370, 'font-size': 11.5, fill: css('--muted')}, svg); n2.textContent = 'Double-click any cell in the System view to open it here; the die floorplan below is one of these rank dies.';
  renderDsArrayRead(k);
}
function drawQwenSystem(svg){
  const W = 900, H = 330; svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
  const g = geo('qwen_rom'); const ar = g.W / g.H; const h = 190, w = h * ar;
  for (let r = 0; r < 4; r++){
    const x = 60 + r * 210, y = 60;
    const gg = dieGlyph(svg, x, y, w, h, mix(css('--die'), css('--k-field'), .35), 'ew', {label: 'rank ' + r, fs: 13});
    gg.setAttribute('tabindex', 0);
    gg.addEventListener('mousemove', ev => showTip(`<b>Qwen ROM die, rank ${r}</b><br>${fmt(val(DATA.dies.qwen_rom.area), 2)} mm² · 1,536 ROM tiles · 4 HBM3E stacks`, ev));
    gg.addEventListener('mouseleave', hideTip);
    if (r < 3) svgEl('path', {d: `M${x + w + 22} ${y + h + 26} H ${x + 210 - 22}`, stroke: css('--k-link'), 'stroke-width': 2.4, fill: 'none'}, svg);
  }
  svgEl('path', {d: `M${60 + w / 2} ${60 + h + 26} V ${60 + h + 50} H ${60 + 3 * 210 + w / 2} V ${60 + h + 26}`, stroke: css('--k-link'), 'stroke-width': 1.4, fill: 'none', 'stroke-dasharray': '5 4'}, svg);
  const t = svgEl('text', {x: 60, y: 40, 'font-size': 12, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); t.textContent = 'TP4 group · each die streams KV for its heads from its own 4 stacks · all-reduce after attention and after the MLP';
  arrayRead(`<div class="eyebrow">System</div><h3>Four ROM dies, sixteen stacks</h3><dl><dt>Dies</dt><dd>4 (TP4 ranks)</dd><dt>Die area</dt><dd>${vs(DATA.dies.qwen_rom.area, 2)} mm²</dd><dt>KV fill</dt><dd>3.734 TB/s, 93.4 % of 4-stack peak</dd><dt>Token</dt><dd>${fmt0(val(DATA.rates.qwen.cycles))} cycles</dd></dl><div class="src">${pill('measured')} results/rtl/qwen_plain_ar_stream4_P8191_20261005/measured_composition.json (ranks 4); STREAM4 fill from results/arch/measured_scoreboard/README.md</div>`);
}
function drawHbmSystem(svg){
  if (state.hbmModel === 'qwen'){
    const W = 900, H = 320; svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
    const g = geo('hbm_qwen'); const w = 150, h = w / (g.W / g.H);
    for (let r = 0; r < 4; r++){ const x = 60 + r * 205, y = 80; dieGlyph(svg, x, y, w, h, mix(css('--die'), css('--k-field'), .35), 'ns', {label: 'TP4 rank ' + r}); svgEl('line', {x1: x + w / 2, y1: y + h + 22, x2: 450, y2: 270, stroke: css('--k-link'), 'stroke-width': 1.4}, svg); }
    svgEl('rect', {x: 390, y: 268, width: 120, height: 26, fill: css('--k-link'), rx: 2}, svg);
    const tl = svgEl('text', {x: 450, y: 285, 'text-anchor': 'middle', 'font-size': 11, fill: css('--bg')}, svg); tl.textContent = 'switch / direct links';
    const t = svgEl('text', {x: 60, y: 40, 'font-size': 12, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); t.textContent = 'Qwen3-8B 8K: TP4 iso-silicon (4 tile dies) or TP2 same silicon (2 dies)';
    arrayRead(`<div class="eyebrow">System</div><h3>Qwen tile dies</h3><dl><dt>TP4 AR</dt><dd>${vs(DATA.rates.hbm_qwen.AR)} tok/s</dd><dt>TP2 AR</dt><dd>${vs(DATA.rates.hbm_qwen.AR_tp2)} tok/s</dd><dt>Unpriced TP4</dt><dd>${vs(DATA.rates.hbm_qwen.AR_unpriced)} tok/s</dd><dt>Die</dt><dd>${vs(DATA.dies.hbm_qwen.area, 2)} mm²</dd></dl>${srcLine(DATA.rates.hbm_qwen.AR)}`);
    return;
  }
  const cols = 16, rows = 6, dw = 34, dh = dw / (24401.52 / 19722.96), gx = 18, gy = 34, x0 = 30, y0 = 54;
  const W = x0 * 2 + cols * (dw + gx), H = y0 + rows * (dh + gy) + 110;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
  const swY = y0 + 3 * (dh + gy) - gy / 2 - 8;
  for (let i = 0; i < 96; i++){
    const r = Math.floor(i / cols), c = i % cols; const x = x0 + c * (dw + gx), y = y0 + r * (dh + gy) + (r >= 3 ? 30 : 0);
    svgEl('line', {x1: x + dw / 2, y1: r < 3 ? y + dh + 7 : y - 7, x2: x0 + ((i * 7) % 8 + 0.5) * (W - 2 * x0) / 8, y2: swY + 10, stroke: css('--k-link'), 'stroke-width': 0.35, opacity: .55}, svg);
    dieGlyph(svg, x, y, dw, dh, mix(css('--die'), css('--k-field'), .35), 'ns');
  }
  for (let s = 0; s < 8; s++){ const x = x0 + s * (W - 2 * x0) / 8 + 8; svgEl('rect', {x, y: swY, width: (W - 2 * x0) / 8 - 16, height: 20, fill: css('--k-link'), rx: 2}, svg); }
  const t = svgEl('text', {x: x0, y: 26, 'font-size': 12, 'font-family': 'var(--f-mono)', fill: css('--muted')}, svg); t.textContent = '96 dies · TP-96 · 384 HBM3E stacks · Tomahawk-Ultra switch tier (8 chips drawn; count is an estimate)';
  arrayRead(`<div class="eyebrow">System</div><h3>96 dies around a switch tier</h3><dl><dt>Dies</dt><dd>${vs(DATA.hbm_system.dies, 0)}</dd><dt>Switch</dt><dd>${vs(DATA.hbm_system.switch)}</dd><dt>TU share of AR</dt><dd>${vs(DATA.hbm_system.tu_budget_share, 4)}</dd><dt>Die wire added</dt><dd>${vs(DATA.rates.hbm_ds.wire_us, 3)} µs</dd></dl>${srcLine(DATA.hbm_system.dies)}${srcLine(DATA.hbm_system.switch)}`);
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
  $('dieRead').innerHTML = `<div class="eyebrow">${esc(D.title)}</div><h3>${fmt(G.W / 1000, 2)} × ${fmt(G.H / 1000, 2)} mm</h3>
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
  $('tSpec').title = d === 'qwen' ? 'Off on the Qwen ROM: DSpark measured 0.704x of plain decoding' : 'Show the speculative wavefront';
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
  attention: ['Attention block', '--k-attn'], mlp: ['MLP block', '--k-field'], residual: ['Residual', '--k-su'], layer: ['Layer (measured)', '--k-field'], headq: ['RTL head', '--k-tree'], lever: ['Exact levers (removed)', '--s-closed'], wire: ['Die wire stages (added)', '--k-wire'], ctx: ['Adopted core-context cycles', '--k-ctrl'] };
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
    const ex = val(DATA.ds_extra_hops); rows.push({ label: '+23 hops', parts: [{ t0: t, d: ex.total, c: 'hop', name: '23 extra S81 stage hops' }] }); t += ex.total; total = t; legendKeys = ['field', 'su', 'attn', 'hop', 'head'];
    $('wfLede').innerHTML = `Every node on the DeepSeek ROM token's critical path at 1M, one row per stretch between stage hops. Total ${fmt(total, 3)} µs = ${fmt(val(DATA.rates.ds.AR), 1)} tok/s. ${pill(st(DATA.ds_stages))}`;
  } else if (d === 'qwen'){
    const L = val(DATA.qwen_layers); const ps = val(DATA.qwen_phase_split); unit = 'cycles';
    L.forEach(s => { if (s.name === 'HEAD' || /head/i.test(s.name)){ rows.push({ label: 'head', parts: [{ t0: s.start, d: s.cycles, c: 'headq', name: 'RTL head' }] }); return; } const f = s.cycles / ps.total; rows.push({ label: s.name, parts: [{ t0: s.start, d: ps.attention * f, c: 'attention', name: 'attention (split analytical)' }, { t0: s.start + ps.attention * f, d: ps.mlp * f, c: 'mlp', name: 'MLP (split analytical)' }, { t0: s.start + (ps.attention + ps.mlp) * f, d: ps.residual * f, c: 'residual', name: 'residual (split analytical)' }], tot: s.cycles }); });
    const last = L[L.length - 1]; let t = last.start + last.cycles; rows.push({ label: '+core ctx', parts: [{ t0: t, d: 112, c: 'ctx', name: 'adopted core-context cycles' }] }); total = val(DATA.rates.qwen.cycles); legendKeys = ['attention', 'mlp', 'residual', 'headq', 'ctx'];
    $('wfLede').innerHTML = `Each decoder layer of the measured P8191 token (L0 includes the first KV fill; L1-L35 are 5,282 cycles each, at their compute-only bound). The attention/MLP/residual split inside a layer applies the measured isolated-L0 proportions and is analytical. Total ${fmt0(total)} cycles. ${pill('measured')}`;
  } else {
    const L = val(DATA.hbm_layers); let t = 0;
    L.forEach(r => { const parts = []; for (const k of ['hbm', 'su', 'sm', 'du', 'du_fast', 'attn', 'coll', 'tail']){ if (r.doms[k]){ parts.push({ t0: t, d: r.doms[k], c: k, name: k }); t += r.doms[k]; } } rows.push({ label: r.name, parts }); });
    const lv = val(DATA.rates.hbm_ds.levers_us), wi = val(DATA.rates.hbm_ds.wire_us);
    rows.push({ label: 'levers', parts: [{ t0: t - lv, d: lv, c: 'lever', name: 'exact levers −' + fmt(lv, 3) + ' µs' }] }); t -= lv;
    rows.push({ label: 'die wire', parts: [{ t0: t, d: wi, c: 'wire', name: 'die wire stages +' + fmt(wi, 3) + ' µs (median bundle)' }] }); t += wi; total = t;
    legendKeys = ['sm', 'su', 'attn', 'du', 'hbm', 'coll', 'tail', 'lever', 'wire'];
    $('wfLede').innerHTML = `The HBM accelerator's DeepSeek token at 1M by layer, split by unit in path order (the matched-reference gate), then the exact levers removed and the die wire added. Total ${fmt(total, 3)} µs = ${fmt(val(DATA.rates.hbm_ds.AR), 1)} tok/s. ${pill('analytical')}`;
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
    H = 110; svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
    const t = svgEl('text', {x: 20, y: 30, 'font-size': 13, fill: css('--ink')}, svg); t.textContent = `core_context (adopted): the in-context core decode closure adds ${val(DATA.rates.qwen.core_ctx)} cycles to the 193,955-cycle measured token: 6,187.0 → ${fmt(val(DATA.rates.qwen.AR))} tok/s.`;
    const t2 = svgEl('text', {x: 20, y: 56, 'font-size': 13, fill: css('--muted')}, svg); t2.textContent = `DSpark speculation: built and exact, switched off; it measures ${fmt(val(DATA.rates.qwen.dspark_ratio), 3)}× of plain decoding (${fmt(val(DATA.rates.qwen.dspark))} tok/s).`;
    const t3 = svgEl('text', {x: 20, y: 82, 'font-size': 13, fill: css('--muted')}, svg); t3.textContent = 'Reason: a 4-position verify layer costs 3.26× an AR layer, because the ROM reads exactly as fast as the lanes multiply.';
    $('lvLede').innerHTML = `The Qwen ROM has one adopted lever since the measured token, and one decision. ${pill('measured')}`;
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
    ['DeepSeek-V4.1 · HBM accel., 1M', R.hbm_ds.AR, R.hbm_ds.MTP, null, 'wire median; same τ'],
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
  renderNotice(); renderHero(); renderArray(); dieTools(); drawDie();
  const wasPlaying = TK.playing; TK.playing = false; buildSteps(); drawToken(); if (wasPlaying && !reduceMotion){ TK.playing = true; requestAnimationFrame(tick); }
  renderWaterfall(); renderClosure(); renderLevers(); renderCompare();
}
document.querySelectorAll('[data-design]').forEach(b => b.addEventListener('click', () => { state.design = b.dataset.design; lsSet('design', state.design); state.sel = null; state.hidden.clear(); state.cbFilter = 'all'; state.arraySel = null; state.arrayZoom = 'system'; renderAll(); }));
$('cmpBtn').onclick = () => { state.compare = !state.compare; $('cmpBtn').setAttribute('aria-pressed', String(state.compare)); renderCompareStrip(); if (state.compare) $('cmpStrip').scrollIntoView({behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest'}); };
$('provBtn').onclick = openDrawer; $('drawerClose').onclick = closeDrawer; $('scrim').onclick = closeDrawer;
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('drawer').hidden) closeDrawer(); });
bindDie(); bindToken();
let rz; window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { drawDie(); drawToken(); }, 150); });
const themeRedraw = () => { renderArray(); drawDie(); drawToken(); renderWaterfall(); renderClosure(); renderLevers(); renderCompare(); };
if (window.matchMedia) matchMedia('(prefers-color-scheme: dark)').addEventListener('change', themeRedraw);
new MutationObserver(themeRedraw).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
renderAll();
// complete at rest: park the token mid-way through a representative step
(function park(){ const k = TK.steps.findIndex(s => s.kind === 'field' || s.kind === 'stream'); TK.i = k >= 0 ? k : 0; TK.t = TK.steps[TK.i] ? TK.steps[TK.i].dur * .45 : 0; drawToken(); })();
})();

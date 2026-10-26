// Debug table: worst links of a die revision, sortable and filterable; a row selects the link in every view.
import { STATUS, fmtBits, fmtUm, fmtBitUm, linkLabel } from './model.js';

const COLS = [
  { id: 'bitum', label: 'bit·µm', get: (m, i) => m.bitum[i], fmt: fmtBitUm, num: true },
  { id: 'len', label: 'length', get: (m, i) => m.len[i], fmt: fmtUm, num: true },
  { id: 'mh', label: 'max hop', get: (m, i) => m.mh[i], fmt: fmtUm, num: true },
  { id: 'bits', label: 'bits', get: (m, i) => m.bits[i], fmt: fmtBits, num: true },
  { id: 'stages', label: 'stages', get: (m, i) => m.stages[i], fmt: (v) => v < 0 ? '?' : String(v), num: true },
  { id: 'cross', label: 'crossed', get: (m, i) => m.cross[i], fmt: (v) => v ? String(v) : '', num: true },
  { id: 'cut', label: 'cut ratio', get: (m, i, t) => t.lcut ? t.lcut[i] : NaN, fmt: (v) => Number.isFinite(v) && v > 0 ? v.toFixed(2) : '', num: true },
];

export class LinkTable {
  constructor(el, { onSelect = () => {} } = {}) {
    this.el = el; this.onSelect = onSelect; this.m = null; this.sort = 'bitum'; this.dir = -1; this.only = null; this.sel = -1;
    el.classList.add('df-table');
    el.innerHTML = `<div class="df-tfilters" role="group" aria-label="Link filters">
      <input type="search" placeholder="filter by block, port or class" aria-label="Filter links">
      <label>min width <select aria-label="Minimum width"><option value="0">any</option><option value="8">≥ 8 bit</option><option value="64">≥ 64 bit</option><option value="256">≥ 256 bit</option><option value="1024">≥ 1 kbit</option></select></label>
      <label><input type="checkbox" data-f="over"> over reach</label>
      <label><input type="checkbox" data-f="bypass"> bypass</label>
      <label><input type="checkbox" data-f="active"> active now</label>
    </div><div class="df-tcount" role="status"></div><div class="df-tscroll"><table><thead><tr></tr></thead><tbody></tbody></table></div>`;
    this.q = el.querySelector('input[type=search]'); this.min = el.querySelector('select');
    this.f = Object.fromEntries([...el.querySelectorAll('[data-f]')].map((x) => [x.dataset.f, x]));
    const head = el.querySelector('thead tr');
    head.append(Object.assign(document.createElement('th'), { textContent: 'link' }), Object.assign(document.createElement('th'), { textContent: 'class' }));
    for (const c of COLS) {
      const th = document.createElement('th'), b = document.createElement('button');
      b.type = 'button'; b.textContent = c.label; b.onclick = () => { if (this.sort === c.id) this.dir = -this.dir; else { this.sort = c.id; this.dir = -1; } this.render(); };
      th.append(b); th.dataset.col = c.id; head.append(th);
    }
    this.tbody = el.querySelector('tbody'); this.count = el.querySelector('.df-tcount');
    let t; this.q.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => this.render(), 150); });
    for (const x of [this.min, ...Object.values(this.f)]) x.addEventListener('change', () => this.render());
    this.tbody.addEventListener('click', (e) => { const tr = e.target.closest('tr[data-i]'); if (tr) this.onSelect(+tr.dataset.i); });
    this.tbody.addEventListener('keydown', (e) => { const tr = e.target.closest('tr[data-i]'); if (tr && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); this.onSelect(+tr.dataset.i); } });
  }
  setModel(m, lcut) { this.m = m; this.lcut = lcut; this.only = null; this.render(); }
  setActive(list) { this.active = list ? new Set(list) : null; if (this.f.active.checked) this.render(); }
  restrict(ids, label) { this.only = ids ? new Set(ids) : null; this.onlyLabel = label; this.render(); }
  select(i) { this.sel = i; for (const tr of this.tbody.querySelectorAll('tr[aria-selected=true]')) tr.setAttribute('aria-selected', 'false'); const tr = this.tbody.querySelector(`tr[data-i="${i}"]`); if (tr) tr.setAttribute('aria-selected', 'true'); }
  render() {
    const m = this.m; if (!m) return;
    const q = this.q.value.trim().toLowerCase(), min = +this.min.value, over = this.f.over.checked, byp = this.f.bypass.checked, act = this.f.active.checked;
    const col = COLS.find((c) => c.id === this.sort), rows = [];
    for (let i = 0; i < m.nl; i++) {
      if (this.only && !this.only.has(i)) continue;
      if (min && !(m.bits[i] >= min)) continue;
      if (over && !(m.status[i] === 1 || m.status[i] === 2)) continue;
      if (byp && !m.cross[i]) continue;
      if (act && !(this.active && this.active.has(i))) continue;
      if (q) { const l = m.rec.links[i]; const hay = (l.i + ' ' + l.c + ' ' + l.e.map((e) => (e[0] >= 0 ? m.bname[e[0]] : '') + '.' + (e[1] || '')).join(' ')).toLowerCase(); if (!hay.includes(q)) continue; }
      rows.push(i);
    }
    const key = (i) => { const v = col.get(m, i, this); return Number.isFinite(v) ? v : -Infinity; };
    rows.sort((a, b) => this.dir * (key(a) - key(b)) || a - b);
    if (this.dir === -1) { /* unknown last */ }
    this.count.textContent = `${rows.length.toLocaleString()} of ${m.nl.toLocaleString()} links${this.only ? ` · ${this.onlyLabel || 'selection'}` : ''} · sorted by ${col.label}${rows.length > 300 ? ' · first 300 shown' : ''}`;
    for (const th of this.el.querySelectorAll('th[data-col]')) th.setAttribute('aria-sort', th.dataset.col === this.sort ? (this.dir < 0 ? 'descending' : 'ascending') : 'none');
    const frag = document.createDocumentFragment();
    for (const i of rows.slice(0, 300)) {
      const tr = document.createElement('tr'); tr.dataset.i = i; tr.tabIndex = 0; tr.setAttribute('aria-selected', String(i === this.sel));
      const l = m.rec.links[i], st = STATUS[m.status[i]];
      const td0 = document.createElement('td'); td0.className = 'df-tl';
      td0.innerHTML = `<i style="background:${st.color}" title="${st.label}"></i>`; td0.append(document.createTextNode(linkLabel(m, i)));
      td0.title = l.i;
      const td1 = document.createElement('td'); td1.textContent = l.c;
      tr.append(td0, td1);
      for (const c of COLS) { const td = document.createElement('td'); td.className = 'n'; td.textContent = c.fmt(c.get(m, i, this)); if (c.id === 'cut' && this.lcut && this.lcut[i] > m.rec.cut.limit) td.className = 'n hot'; tr.append(td); }
      frag.append(tr);
    }
    this.tbody.replaceChildren(frag);
  }
}

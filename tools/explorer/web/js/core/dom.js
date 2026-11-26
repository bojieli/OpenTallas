// DOM, formatting and small shared helpers.  The one copy for the whole app.
export const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/** h('div.cls#id', {attrs, onclick, dataset:{}}, ...children) -> element.  Strings become text nodes; null is skipped. */
export function h(spec, attrs, ...kids) {
  if (attrs != null && (typeof attrs !== 'object' || attrs.nodeType || Array.isArray(attrs))) { kids.unshift(attrs); attrs = null; }
  const m = spec.match(/^([a-z0-9]+)?((?:[.#][\w-]+)*)$/i) || [];
  const e = document.createElement(m[1] || 'div');
  (m[2] || '').replace(/([.#])([\w-]+)/g, (_, k, v) => { if (k === '.') e.classList.add(v); else e.id = v; });
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2), v);
    else if (k === 'dataset') Object.assign(e.dataset, v);
    else if (k === 'style' && typeof v === 'object') { for (const [sk, sv] of Object.entries(v)) { if (sk.startsWith('--')) e.style.setProperty(sk, sv); else e.style[sk] = sv; } }
    else if (k === 'html') e.innerHTML = v;
    else if (k === 'testid') e.dataset.testid = v;
    else if (k in e && k !== 'list' && typeof v !== 'string') e[k] = v;
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat(Infinity)) if (k != null && k !== false) e.append(k.nodeType ? k : document.createTextNode(String(k)));
  return e;
}
export const clear = (el) => { el.replaceChildren(); return el; };
export const cssv = (name, el) => getComputedStyle(el || document.documentElement).getPropertyValue(name).trim();
export const hexRgb = (hex) => { const s = hex.replace('#', ''); const f = s.length === 3 ? s.split('').map((c) => c + c).join('') : s; return [0, 2, 4].map((i) => parseInt(f.substr(i, 2), 16)); };
export const cssRgb = (name, a) => { const v = cssv(name), c = v ? hexRgb(v) : [128, 128, 128]; return a == null ? c : [...c, a]; };

export const fmt = (n, d = 0) => (n == null || Number.isNaN(+n)) ? '–' : Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmtUm = (u) => u == null ? '–' : u >= 1000 ? fmt(u / 1000, 2) + ' mm' : fmt(u, u < 10 ? 2 : 1) + ' µm';
export const fmtBytes = (b) => b == null ? '–' : b >= 1e9 ? fmt(b / 1e9, 2) + ' GB' : b >= 1e6 ? fmt(b / 1e6, 1) + ' MB' : fmt(b / 1e3, 0) + ' kB';
export const fmtCount = (n) => n == null ? '–' : n >= 1e9 ? fmt(n / 1e9, 2) + ' B' : n >= 1e6 ? fmt(n / 1e6, 1) + ' M' : n >= 1e4 ? fmt(n / 1e3, 0) + ' k' : fmt(n);
export function fmtAge(s) {
  if (s == null) return 'unknown';
  if (s < 90) return 'just now';
  if (s < 3600 * 1.5) return Math.round(s / 60) + ' min ago';
  if (s < 86400 * 2) return Math.round(s / 3600) + ' h ago';
  return Math.round(s / 86400) + ' d ago';
}
export function fmtTime(epoch) {
  if (epoch == null) return 'unknown';
  const d = new Date(epoch * 1000), p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export const STATES = ['signed', 'pending archive', 'failed', 'building', 'queued', 'waiting', 'not built', 'hard ip', 'uncredited'];
export const STATE_LABEL = { 'pending archive': 'Signed, pending archive', signed: 'Signed off', failed: 'Failed', building: 'Building', queued: 'Queued', waiting: 'Waiting', 'not built': 'Not built', 'hard ip': 'Hard IP', uncredited: 'Uncredited' };
export const STATE_VAR = { 'pending archive': '--s-pending', signed: '--s-signed', failed: '--s-failed', building: '--s-building', queued: '--s-queued', waiting: '--s-waiting', 'not built': '--s-notbuilt', 'hard ip': '--s-hardip', uncredited: '--s-notbuilt' };
export const stateCls = (s) => 'st-' + String(s || 'not built').replace(/\s/g, '');
export const displayState = (n) => n?.signoff_display_state || n?.status?.state || n?.state || 'not built';
export const displayStateLabel = (n) => {
  const state = displayState(n);
  if (state === 'signed' && n.signoff_basis && n.signoff_basis !== 'current') return 'Signed off on an earlier plan';
  if (n.signoff_basis || state === 'uncredited') return STATE_LABEL[state];
  return n.status?.label || STATE_LABEL[state] || state;
};
export const stateColor = (s) => cssv(STATE_VAR[s] || '--s-notbuilt');
export const badge = (state, label, basis) => h('span.st.' + stateCls(state), { title: label || (basis ? 'counted on the ' + basis + ' gates; the kit sign-off record used the older full gate set' : '') }, h('i.dot'), (STATE_LABEL[state] || state || 'unknown') + (basis ? ` (${basis})` : ''));
export const DIE_SHORT = { s81: 'S81', s81_head: 'HEAD', qwen_compute: 'QC', qwen_kvsys: 'KV', hbm: 'HBM' };
export const dieShort = (d) => DIE_SHORT[d] || String(d || '').toUpperCase();
export const dieOf = (node) => String(node || '').split('.')[0];
export const levelOf = (node) => !node ? null : node.includes('.t.') ? 'type' : node.includes('.c.') ? 'core' : 'die';
export const shortName = (node) => { const m = /\.[tc]\.(.+)$/.exec(node || ''); return m ? m[1] : node; };

const I = (d, extra = '') => `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${d}</svg>`;
export const ICON = {
  logo: I('<rect x="3" y="3" width="14" height="14" rx="2"/><path d="M3 8h14M8 3v14M12 8v9M8 12h4"/>'),
  overview: I('<rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/><rect x="3" y="11" width="6" height="6" rx="1"/><rect x="11" y="11" width="6" height="6" rx="1"/>'),
  plan: I('<rect x="3" y="3" width="14" height="14" rx="1"/><path d="M3 9h8M11 3v14M11 13h6"/>'),
  layout: I('<path d="M3 5h9v4h5M3 10h5v5h9M7 15v2M14 5V3"/><circle cx="12" cy="9" r=".6" fill="currentColor"/><circle cx="8" cy="15" r=".6" fill="currentColor"/>'),
  element: I('<rect x="4" y="4" width="12" height="12" rx="1.5"/><path d="M8 4V2M12 4V2M8 18v-2M12 18v-2M4 8H2M4 12H2M18 8h-2M18 12h-2"/><rect x="8" y="8" width="4" height="4"/>'),
  dataflow: I('<circle cx="4.5" cy="5" r="2"/><circle cx="15.5" cy="10" r="2"/><circle cx="4.5" cy="15" r="2"/><path d="M6.5 5c4 0 3 5 7 5M6.5 15c4 0 3-5 7-5"/>'),
  token: I('<path d="M3 16V8M7.5 16V4M12 16v-6M16.5 16V7"/><path d="M2 16h16"/>'),
  fleet: I('<rect x="3" y="3" width="14" height="5" rx="1"/><rect x="3" y="12" width="14" height="5" rx="1"/><path d="M6 5.5h.01M6 14.5h.01M10 8v4"/>'),
  closure: I('<path d="M4 4h12v12H4z"/><path d="M7 10l2.2 2.2L13.5 8"/>'),
  search: I('<circle cx="9" cy="9" r="5"/><path d="M13 13l4 4"/>'),
  chevL: I('<path d="M12 5l-5 5 5 5"/>'), chevR: I('<path d="M8 5l5 5-5 5"/>'), chevD: I('<path d="M5 8l5 5 5-5"/>'),
  focus: I('<path d="M3 7V3h4M13 3h4v4M17 13v4h-4M7 17H3v-4"/>'),
  full: I('<rect x="3" y="4" width="14" height="12" rx="1"/><path d="M7 8l-2 2 2 2M13 8l2 2-2 2"/>'),
  exit: I('<path d="M5 5l10 10M15 5L5 15"/>'),
  sun: I('<circle cx="10" cy="10" r="3.2"/><path d="M10 2.5v2M10 15.5v2M2.5 10h2M15.5 10h2M4.7 4.7l1.4 1.4M13.9 13.9l1.4 1.4M4.7 15.3l1.4-1.4M13.9 6.1l1.4-1.4"/>'),
  moon: I('<path d="M16 11.5A6.5 6.5 0 018.5 4a6.5 6.5 0 107.5 7.5z"/>'),
  fit: I('<path d="M3 8V3h5M12 3h5v5M17 12v5h-5M8 17H3v-5"/><rect x="7" y="7" width="6" height="6"/>'),
  ruler: I('<path d="M3 13L13 3l4 4L7 17z"/><path d="M6.5 10.5l1.5 1.5M9 8l1.5 1.5M11.5 5.5L13 7"/>'),
  link: I('<path d="M8.5 11.5a3 3 0 004.2 0l2.8-2.8a3 3 0 00-4.2-4.2l-1 1M11.5 8.5a3 3 0 00-4.2 0l-2.8 2.8a3 3 0 004.2 4.2l1-1"/>'),
  panelL: I('<rect x="3" y="4" width="14" height="12" rx="1.5"/><path d="M8 4v12"/>'),
  panelR: I('<rect x="3" y="4" width="14" height="12" rx="1.5"/><path d="M12 4v12"/>'),
  help: I('<circle cx="10" cy="10" r="7"/><path d="M8 8a2 2 0 113 1.7c-.7.4-1 .8-1 1.6M10 14v.2"/>'),
  open: I('<path d="M8 4H4v12h12v-4M11 3h6v6M17 3l-8 8"/>'),
  clock: I('<circle cx="10" cy="10" r="7"/><path d="M10 6v4l2.5 2"/>'),
  play: I('<path d="M6 4l10 6-10 6z" fill="currentColor"/>'), pause: I('<path d="M6 4v12M14 4v12"/>'),
};
export const icon = (name) => { const s = document.createElement('span'); s.style.display = 'contents'; s.innerHTML = ICON[name] || ''; return s.firstChild; };

export function toast(msg, ms = 2200) {
  document.querySelectorAll('.toast').forEach((t) => t.remove());
  const t = h('div.toast', { role: 'status' }, msg); document.body.append(t); setTimeout(() => t.remove(), ms);
}
export const debounce = (fn, ms) => { let t = 0; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
export const raf = (fn) => { let id = 0; return (...a) => { if (!id) id = requestAnimationFrame(() => { id = 0; fn(...a); }); }; };
export const ls = {
  get(k, d) { try { const v = localStorage.getItem('otx.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('otx.' + k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
};

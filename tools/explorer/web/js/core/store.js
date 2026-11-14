// The one selection and the one URL scheme (DESIGN.md section 3).
//   #/<view>/<node id>?inst=..&net=..&lane=..&tok=..&<view params>
// Selection keys survive a view change; view params are remembered per view for the session.
import { dieOf } from './dom.js';

export const VIEWS = ['overview', 'plan', 'layout', 'element', 'dataflow', 'token', 'closure', 'fleet'];
const SEL_KEYS = ['inst', 'net', 'lane', 'tok'];
const subs = new Set();
const memory = {};   // view -> params (session)
let state = { view: 'overview', sel: { die: null, node: null, inst: null, net: null, lane: null, tok: null }, params: {} };
let defaultDie = null;

const enc = (v) => encodeURIComponent(v).replace(/%2C/g, ',').replace(/%2F/g, '/').replace(/%3A/g, ':');

export function parse(hash) {
  const s = String(hash || '').replace(/^#/, '');
  const [path, query = ''] = s.split('?');
  const seg = path.split('/').filter(Boolean);
  const view = VIEWS.includes(seg[0]) ? seg[0] : 'overview';
  const node = seg[1] ? decodeURIComponent(seg[1]) : null;
  const params = {}, sel = { die: node ? dieOf(node) : null, node, inst: null, net: null, lane: null, tok: null };
  for (const kv of query.split('&')) {
    if (!kv) continue;
    const i = kv.indexOf('='), k = decodeURIComponent(i < 0 ? kv : kv.slice(0, i)), v = i < 0 ? '' : decodeURIComponent(kv.slice(i + 1));
    if (SEL_KEYS.includes(k)) sel[k] = v || null; else params[k] = v;
  }
  return { view, sel, params };
}

export function format(st) {
  const q = [];
  for (const k of SEL_KEYS) if (st.sel[k]) q.push(k + '=' + enc(st.sel[k]));
  for (const [k, v] of Object.entries(st.params || {})) if (v != null && v !== '') q.push(enc(k) + '=' + enc(String(v)));
  return '#/' + st.view + (st.sel.node ? '/' + enc(st.sel.node) : '') + (q.length ? '?' + q.join('&') : '');
}

/** next state from a patch: {view, node, die, inst, net, lane, tok, params} */
function apply(patch) {
  const next = { view: patch.view || state.view, sel: { ...state.sel }, params: {} };
  const viewChanged = next.view !== state.view;
  if ('node' in patch || 'die' in patch) {
    const node = 'node' in patch ? patch.node : patch.die;
    const changed = node !== state.sel.node;
    next.sel.node = node || null; next.sel.die = node ? dieOf(node) : null;
    if (changed) { next.sel.inst = null; next.sel.net = null; if (next.sel.die !== state.sel.die) next.sel.lane = null; }
  }
  for (const k of SEL_KEYS) if (k in patch) next.sel[k] = patch[k] || null;
  if (!next.sel.node && defaultDie && next.view !== 'overview') { next.sel.node = defaultDie; next.sel.die = defaultDie; }
  const nodeChanged = next.sel.node !== state.sel.node;
  next.params = viewChanged ? { ...(memory[next.view + '|' + (next.sel.node || '')] || {}) } : nodeChanged ? {} : { ...state.params };
  if (patch.params) for (const [k, v] of Object.entries(patch.params)) { if (v == null || v === '') delete next.params[k]; else next.params[k] = String(v); }
  return next;
}

function commit(next, replace) {
  const url = format(next);
  const same = url === format(state);
  state = next; memory[state.view + '|' + (state.sel.node || '')] = { ...state.params };
  if (location.hash !== url) { if (replace || same) history.replaceState(null, '', location.pathname + location.search + url); else history.pushState(null, '', location.pathname + location.search + url); }
  return !same;
}

export const store = {
  get: () => state,
  setDefaultDie(d) { defaultDie = d; },
  subscribe(fn) { subs.add(fn); return () => subs.delete(fn); },
  /** navigate: a new history entry unless opts.replace */
  go(patch, opts = {}) {
    const prev = state;
    if (commit(apply(patch), opts.replace)) notify(prev);
  },
  /** view-local state (camera, toggles): replaces the URL, tells nobody unless opts.notify */
  setParams(params, opts = {}) {
    const prev = state;
    const changed = commit(apply({ params }), true);
    if (changed && opts.notify) notify(prev);
  },
  href: (patch) => format(apply(patch)),
  /** read the URL (boot, Back/Forward) */
  sync() {
    const prev = state; const p = parse(location.hash);
    if (!p.sel.node && defaultDie && p.view !== 'overview') { p.sel.node = defaultDie; p.sel.die = defaultDie; }
    state = p; memory[state.view + '|' + (state.sel.node || '')] = { ...state.params };
    notify(prev);
  },
};
function notify(prev) { for (const fn of [...subs]) { try { fn(state, prev); } catch (e) { console.error('store subscriber', e); } } }
window.addEventListener('popstate', () => store.sync());
let legacyHandler = null;
export const onLegacy = (fn) => { legacyHandler = fn; };
window.addEventListener('hashchange', () => {
  if (location.hash.length > 1 && !location.hash.startsWith('#/') && legacyHandler) return legacyHandler();   // an old-scheme link pasted into the open app
  if (format(state) !== location.hash) store.sync();
});

/** old explorer URL schemes -> the canonical one.  Returns a patch or null; names that need the resolver come back as {q}. */
export function legacy(loc) {
  const sp = new URLSearchParams(loc.search), view = sp.get('legacy');
  const raw = loc.hash.replace(/^#/, '');
  if (raw.startsWith('/')) return null;
  if (!raw && !view) return null;
  const o = {}; raw.split('&').forEach((kv) => { const [k, v] = kv.split('='); if (k) o[k] = decodeURIComponent(v || ''); });
  const p = { view: view || 'plan', params: {} };
  if (o.n && /^[a-z0-9_]+(\.[tc]\..+)?$/i.test(o.n)) { p.node = o.n; if (o.n.includes('.') && !view) p.view = o.v === 'plan' ? 'plan' : 'element'; }
  if (o.v === 'layout' && p.node && p.node.includes('.')) p.view = 'element';
  if (o.net) p.net = o.net;
  if (o.q) p.q = o.q;
  if (!p.node && !p.q && sp.get('q')) { const nm = sp.get('q'); if (/^[a-z0-9_]+(\.[tc]\..+)?$/i.test(nm) && (nm.includes('.t.') || nm.includes('.c.'))) p.node = nm; else p.q = nm; }
  if (o.element) { p.q = o.element; p.view = 'element'; }
  if (o.design) { const g = o.group || o.t; p.tok = o.design + (g ? ':' + g : ''); if (!view) p.view = 'token'; }
  if (o.die && !p.node) { const d = o.die.replace(/^plan_/, ''); p.dieHint = d; }
  return p;
}

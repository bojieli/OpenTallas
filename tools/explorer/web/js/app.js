// Boot: load the meta, rewrite old URLs, build the shell, register the views.
import { h, clear } from './core/dom.js';
import { store, legacy, onLegacy } from './core/store.js';
import { api } from './core/api.js';
import { createShell } from './shell/shell.js';
import overview from './views/overview.js';
import plan from './views/plan.js';
import layout from './views/layout.js';
import element from './views/element.js';
import dataflow from './views/dataflow.js';
import token from './views/token.js';
import closure from './views/closure.js';
import fleet from './views/fleet.js';

const VIEWS = [overview, plan, layout, element, dataflow, token, closure, fleet];

async function boot() {
  const root = document.getElementById('root');
  let meta;
  try { meta = await api.meta(); } catch (e) {
    clear(root).append(h('div.empty', h('div', h('h3', 'The explorer service did not answer'), h('p', e.message), e.detail ? h('p.muted.mono', e.detail) : null, h('button.btn', { type: 'button', onclick: () => location.reload() }, 'Retry'))));
    return;
  }
  if (meta.dies.length) store.setDefaultDie(meta.dies[0].id);
  // old explorer links (#n=, #q=, #element=, #design=, ?legacy=<view>) -> the canonical scheme
  async function fromLegacy() {
    const old = legacy(location); if (!old) return false;
    let node = old.node || null;
    if (!node && old.q) { try { const r = await api.resolve([old.q]); const hits = r[old.q] || []; node = (old.dieHint && hits.find((x) => x.split('.')[0] === old.dieHint)) || hits[0] || null; } catch (e) { /* unresolved: land on the view */ } }
    if (!node && old.dieHint && meta.dies.some((d) => d.id === old.dieHint)) node = old.dieHint;
    history.replaceState(null, '', location.pathname);
    store.go({ view: old.view, node: node || meta.dies[0].id, net: old.net || null, tok: old.tok || null }, { replace: true });
    return true;
  }
  await fromLegacy(); onLegacy(fromLegacy);
  clear(root);
  const shell = createShell(root, { views: VIEWS, meta });
  window.otx = { store, api, shell };   // for tests and the console
  store.sync();
}
boot();

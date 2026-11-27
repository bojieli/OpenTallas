// Navigator: die > status group > type > core tree with a filter.  Rows are plain links to the current view.
import { h, clear, STATES, STATE_LABEL, stateCls, dieShort, ls, debounce, levelOf, displayState, displayStateLabel } from '../core/dom.js';
import { store } from '../core/store.js';
import { api } from '../core/api.js';

export function mountNavigator(host) {
  const S = { die: null, data: null, filter: '', packOnly: false, closed: new Set(ls.get('nav.closed', ['cores'])), node: null, view: null, seq: 0 };
  const q = h('input.field', { type: 'search', placeholder: 'Filter partition types and hard cores', 'aria-label': 'Filter the navigator', testid: 'nav-filter', spellcheck: false });
  const packBtn = h('button.btn.sm', { type: 'button', 'aria-pressed': 'false', title: 'Only designs with a routed layout pack', testid: 'nav-packonly' }, 'Routed');
  const tree = h('div.tree', { testid: 'nav-tree' });
  host.append(h('div.nav-tools', q, packBtn), tree);
  q.addEventListener('input', debounce(() => { S.filter = q.value.trim().toLowerCase(); paint(); }, 100));
  packBtn.onclick = () => { S.packOnly = !S.packOnly; packBtn.setAttribute('aria-pressed', String(S.packOnly)); paint(); };

  const href = (id) => store.href({ view: S.view === 'overview' ? 'plan' : S.view, node: id });
  function row(n, cls) {
    const pack = !!(n.layout && n.layout.store);
    return h('a.row' + (cls || '') + '.' + stateCls(displayState(n)), { href: href(n.id), 'aria-current': n.id === S.node ? 'true' : null, title: `${n.name} · ${displayStateLabel(n)}${pack ? ' · routed layout available' : ''}`, dataset: { node: n.id } },
      h('i.dot'), h('span.nm', n.name), pack ? h('i.pk', { title: 'routed layout pack' }) : null,
      h('small', n.level === 'type' ? (n.plan.instances || 0) + '×' : ''));
  }
  function group(key, label, n, body, state) {
    const open = !S.closed.has(key) || !!S.filter || (key === 'cores' && S.node && S.node.includes('.c.') && !S.nodeParent);
    const b = h('button.grp' + (state ? '.' + stateCls(state) : ''), { type: 'button', 'aria-expanded': String(open), dataset: { testid: 'nav-group-' + key.replace(/\s/g, '') },
      onclick: () => { if (S.closed.has(key)) S.closed.delete(key); else S.closed.add(key); ls.set('nav.closed', [...S.closed]); paint(); } },
      h('span.car', '▾'), state ? h('i.dot') : null, label, h('span.n', n));
    return [b, open ? body : null];
  }
  function paint() {
    clear(tree);
    if (!S.die) {
      tree.append(h('div.grp', 'Dies'));
      for (const d of S.dies || []) tree.append(h('a.row', { href: store.href({ view: 'plan', node: d.id }), dataset: { node: d.id } }, h('span.nm', d.label), h('small', `${d.any_plan?.any ?? '–'} signed`)));
      return;
    }
    if (!S.data) { tree.append(h('div.more', 'Loading ' + dieShort(S.die) + '…')); return; }
    const all = Object.values(S.data.nodes), f = S.filter;
    const ok = (n) => (!f || n.name.toLowerCase().includes(f)) && (!S.packOnly || (n.layout && n.layout.store));
    const types = all.filter((n) => n.level === 'type' && ok(n)).sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true }));
    const cores = all.filter((n) => n.level === 'core' && ok(n)).sort((a, b) => a.name.localeCompare(b.name));
    const die = S.data.die;
    tree.append(h('a.row', { href: href(die.id), 'aria-current': S.node === die.id ? 'true' : null, dataset: { node: die.id } }, h('span.nm', { style: { fontFamily: 'var(--sans)', fontWeight: 600 } }, die.label), h('small', 'die')));
    for (const st of STATES) {
      const rows = types.filter((n) => displayState(n) === st); if (!rows.length) continue;
      const body = rows.map((n) => {
        const out = [row(n)];
        if (n.id === S.node) {   // the macros placed inside the selected type: hover highlights on the canvas, click selects and zooms
          const hc = (n.plan.hard_cores || []).slice().sort((a, b) => a[0].localeCompare(b[0], 'en', { numeric: true }));
          if (hc.length) out.push(h('div.more', { dataset: { testid: 'nav-macros-head' } }, `${hc.length} macros in this partition type`));
          for (const c of hc.slice(0, 300)) { const cn = S.data.nodes[c[1]];
            out.push(h('a.row.core.' + stateCls(cn ? displayState(cn) : 'not built'), { href: store.href({ view: S.view === 'overview' || S.view === 'closure' || S.view === 'token' || S.view === 'dataflow' ? 'element' : S.view, node: n.id, inst: c[0] }), 'aria-current': S.inst === c[0] ? 'true' : null,
              title: `${c[0]} · ${c[2]}${cn ? ' · hard core, ' + displayStateLabel(cn) : ' · generated memory macro'}`, dataset: { macro: c[0] },
              onmouseenter: () => window.dispatchEvent(new CustomEvent('otx:hover-inst', { detail: c[0] })), onmouseleave: () => window.dispatchEvent(new CustomEvent('otx:hover-inst', { detail: null })) },
              h('i.dot'), h('span.nm', c[0]), h('small', c[2].length > 16 ? '…' + c[2].slice(-14) : c[2]))); }
          if (hc.length > 300) out.push(h('div.more', `${hc.length - 300} more: see the Macros tab of the inspector.`));
        } else if (S.nodeParent === n.id) for (const c of n.children || []) { const cn = S.data.nodes[c]; if (cn) out.push(row(cn, '.core')); }
        return out;
      });
      tree.append(...group(st, (STATE_LABEL[st] || 'Uncredited') + ' partition types in plan', rows.length, body, st).flat(3).filter(Boolean));
    }
    if (cores.length) tree.append(...group('cores', 'Hard cores', cores.length, cores.map((n) => row(n))).flat(3).filter(Boolean));
    if (!types.length && !cores.length) tree.append(h('div.more', f ? `Nothing matches “${f}”.` : 'No designs.'));
    const cur = tree.querySelector('[aria-current="true"]'); if (cur && S.scroll) { cur.scrollIntoView({ block: S.node && S.node.includes('.t.') && cur.dataset.node === S.node ? 'start' : 'nearest' }); S.scroll = false; }   // a selected type goes to the top so its macros are in view
  }
  async function update(st) {
    const { die, node } = st.sel;
    S.view = st.view; S.inst = st.sel.inst;
    if (node !== S.node) S.scroll = true;
    S.node = node;
    if (die !== S.die) {
      S.die = die; S.data = null; paint();
      if (!die) { try { S.dies = (await api.dies()).dies; } catch (e) { S.dies = []; } if (!S.die) paint(); return; }
      const my = ++S.seq;
      try { const d = await api.die(die); if (my === S.seq) S.data = d; } catch (e) { if (my === S.seq) { clear(tree).append(h('div.more', 'Could not load the die: ' + e.message)); return; } }
    }
    // a selected core opens under the type it was reached from (the last selected type that uses it)
    if (S.data && levelOf(node) === 'type') S.lastType = node;
    S.nodeParent = null;
    if (S.data && levelOf(node) === 'core') { const t = S.data.nodes[S.lastType]; if (t && (t.children || []).includes(node)) S.nodeParent = S.lastType; }
    paint();
  }
  return { update };
}

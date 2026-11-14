// Macro identity, shared by the Element and Layout views: colour slots by master, the canvas legend, the inspector
// card of one macro and the instance list.  A macro = one placed hard core or generated memory macro inside a type.
import { h, fmt, stateCls, STATE_LABEL, shortName } from '../core/dom.js';
import { MARK_VARS } from '../engine/layout-engine.js';

/** masters by placement count, the eight most frequent get a colour slot (fixed order), the rest share "other" */
export function colourSlots(macros) {
  const n = new Map(); for (const m of macros) n.set(m.master, (n.get(m.master) || 0) + 1);
  const order = [...n.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const slot = new Map(order.map(([k], i) => [k, i < MARK_VARS.length ? i : -1]));
  for (const m of macros) m.ci = slot.get(m.master);
  return order.map(([master, count]) => ({ master, count, ci: slot.get(master) }));
}
const sw = (ci) => h('i.sq', { style: { '--c': `var(${ci >= 0 ? MARK_VARS[ci] : '--c-other'})` } });

/** canvas legend: one swatch per coloured master */
export function legendHud(el, masters, what) {
  el.replaceChildren();
  if (!masters.length) { el.hidden = true; return; }
  el.hidden = false;
  const top = masters.filter((m) => m.ci >= 0), rest = masters.length - top.length;
  el.append(h('b', `${what} by master`), h('div.legend', { style: { marginTop: '3px' } }, top.map((m) => h('span', { title: `${m.master}: ${m.count} placed` }, sw(m.ci), `${shortName(m.master)} ×${m.count}`)), rest > 0 ? h('span', sw(-1), `${rest} other master${rest === 1 ? '' : 's'}`) : null));
}

/** inspector: the selected macro, the master legend and every instance.  o: {macros, masters, sel, store, hover(key|null), select(key), pinsOf(master), note} */
export function macrosTab(el, o) {
  const m = o.macros.find((x) => x.key === o.sel);
  if (m) {
    const pins = o.pinsOf ? o.pinsOf(m.master) : null;
    el.append(h('section.sec', { dataset: { testid: 'macro-card' } }, h('h3', 'Selected macro'), h('h1.mono', m.key),
      h('dl.kv', h('dt', 'master'), h('dd', sw(m.ci), ' ', h('span.mono', m.master)), m.packName && m.packName !== m.key ? [h('dt', 'name in the routed DB'), h('dd', h('span.mono', m.packName))] : null,
        h('dt', 'kind'), h('dd', m.coreId ? h('span.st.' + stateCls(m.state), h('i.dot'), `hard core · ${STATE_LABEL[m.state] || m.state || 'unknown'}`) : 'generated memory macro (no signed design of its own)'),
        h('dt', 'size'), h('dd', `${fmt(m.bb[2] - m.bb[0], 2)} × ${fmt(m.bb[3] - m.bb[1], 2)} µm`), h('dt', 'position'), h('dd', `${fmt(m.bb[0], 2)}, ${fmt(m.bb[1], 2)} µm · ${m.orient || '?'}`),
        m.where ? [h('dt', 'placement'), h('dd', m.where)] : null, m.partition ? [h('dt', 'in partition'), h('dd', h('span.mono', m.partition))] : null,
        pins ? [h('dt', 'pins'), h('dd', `${fmt(pins.length)}` + (pins.length ? ': ' : ''), h('span.mono', { style: { fontSize: 'var(--fs-xs)' } }, pins.slice(0, 14).join(' ') + (pins.length > 14 ? ' …' : '')))] : null),
      h('div', { style: { display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '10px' } },
        m.coreId ? h('a.btn.sm.primary', { href: o.store.href({ view: 'element', node: m.coreId, inst: null }), dataset: { testid: 'macro-open-core' } }, `Open core ${shortName(m.coreId)}`) : null,
        h('button.btn.sm', { type: 'button', dataset: { testid: 'macro-zoom' }, onclick: () => o.select(m.key, true) }, 'Zoom to it'),
        h('a.btn.sm', { href: o.store.href({ inst: null }), dataset: { testid: 'macro-clear' } }, 'Clear'))));
  } else el.append(h('section.sec', h('p.note', { style: { margin: 0 } }, o.macros.length ? 'Click a macro outline on the canvas, or a row below, to select it. Outlines are coloured by master; names appear on the canvas when a macro is large enough.' : (o.note || 'This design has no macros: it is flat (standard cells only).'))));
  if (!o.macros.length) return;
  el.append(h('section.sec', h('h3', 'Masters', h('span.n', `${o.masters.length} masters · ${o.macros.length} placed`)), h('div.list', { dataset: { testid: 'macro-masters' } }, o.masters.map((x) => { const first = o.macros.find((q) => q.master === x.master);
    return h('button.row', { type: 'button', title: `${x.master}: select the first of ${x.count}`, onclick: () => o.select(first.key, true) }, sw(x.ci), h('span.nm', x.master), h('small', `${x.count}× · ${first.coreId ? (STATE_LABEL[first.state] || 'core') : 'memory macro'}`)); }))));
  const rows = o.macros.slice().sort((a, b) => a.key.localeCompare(b.key, 'en', { numeric: true })).slice(0, 600);
  el.append(h('section.sec', h('h3', 'Instances', h('span.n', o.macros.length > 600 ? `first 600 of ${o.macros.length}` : o.macros.length)), h('div.list', { dataset: { testid: 'macro-list' } }, rows.map((x) => h('button.row' + (x.key === o.sel ? '.on' : ''), { type: 'button', title: `${x.key} · ${x.master}`, dataset: { macro: x.key },
    onmouseenter: () => o.hover(x.key), onmouseleave: () => o.hover(null), onclick: () => o.select(x.key, true) }, sw(x.ci), h('span.nm', x.key), h('small', shortName(x.master)))))));
}

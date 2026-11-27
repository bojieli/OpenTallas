// Inspector tab shared by the Layout and Element views: routing layers (visibility, opacity, solo), presets, shape
// kinds, palette and canvas display switches of one LayoutEngine.
import { h, clear } from '../core/dom.js';
import { KINDS, PRESETS } from '../engine/layout-engine.js';

export function layersTab(getEngine, { onChange, extra } = {}) {
  return (el) => {
    const eng = getEngine();
    const paint = () => {
      clear(el);
      if (!eng || !eng.L) { el.append(h('section.sec', h('p.note', { style: { margin: 0 } }, 'Layers appear when the first routed pack has loaded. Zoom into a signed partition type, or open a design with a routed layout.'))); return; }
      const changed = () => { if (onChange) onChange(); };
      const rows = eng.L.map((l) => h('div.lyr' + (l.vis ? '' : '.off'), { style: { '--c': l.color } },
        h('input', { type: 'checkbox', checked: l.vis, 'aria-label': 'Show ' + l.name, dataset: { testid: 'layer-' + l.name.replace(/\W+/g, '') }, onchange: (e) => { l.vis = e.target.checked; eng.afterVis(); changed(); paint(); } }),
        h('i.sw'), h('span.ln', l.name), h('small', l.type === 'CUT' ? 'via' : l.type === 'ROUTING' ? (l.dir === 'HORIZONTAL' ? 'H' : 'V') : ''),
        h('input', { type: 'range', min: 5, max: 100, value: Math.round(l.op * 100), 'aria-label': l.name + ' opacity', oninput: (e) => eng.setOpacity(l.i, +e.target.value / 100) }),
        h('button.solo', { type: 'button', title: 'Show only ' + l.name, dataset: { testid: 'solo-' + l.name.replace(/\W+/g, '') }, onclick: () => { eng.setLayerVis((x) => x === l); changed(); paint(); } }, 'solo')));
      el.append(
        h('section.sec', h('h3', 'Presets'), h('div.presets', PRESETS.map(([id, label]) => h('button.btn.sm', { type: 'button', dataset: { testid: 'preset-' + id }, onclick: () => { eng.preset(id); changed(); paint(); } }, label)))),
        h('section.sec', h('h3', 'Layers', h('span.n', 'visible · opacity')), rows),
        h('section.sec', h('h3', 'Shape kinds'), h('div.cols2', KINDS.filter((k) => k[0] < 14).map((k) => h('label.chk', h('input', { type: 'checkbox', checked: !!eng.kindVis[k[0]], dataset: { testid: 'kind-' + k[0] }, onchange: (e) => eng.setKind(k[0], e.target.checked) }), k[1])))),
        h('section.sec', h('h3', 'Display'),
          h('label.chk', 'Palette ', h('select.field', { style: { height: '24px', marginLeft: 'auto' }, 'aria-label': 'Layer palette', dataset: { testid: 'palette' }, onchange: (e) => { eng.setPalette(e.target.value); paint(); } },
            h('option', { value: 'classic', selected: eng.palette === 'classic' }, 'Classic'), h('option', { value: 'cvd', selected: eng.palette === 'cvd' }, 'Colour-vision safe'))),
          [['plan', 'Plan rectangles under the wires'], ['labels', 'Partition labels'], ['cores', 'Macro and hard-core outlines'], ['macroLabels', 'Macro name labels'], ['minimap', 'Minimap']].map(([k, label]) => h('label.chk', h('input', { type: 'checkbox', checked: !!eng.show[k], dataset: { testid: 'show-' + k }, onchange: (e) => { eng.show[k] = e.target.checked; eng.requestUpdate(); } }), label)),
          extra ? extra() : null));
    };
    paint();
    const prev = eng && eng.o.onLayers; if (eng) eng.o.onLayers = () => { paint(); };
    return () => { if (eng) eng.o.onLayers = prev; };
  };
}

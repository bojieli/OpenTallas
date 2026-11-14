// Element view: placeholder until milestone 2.
import { h } from '../core/dom.js';
export default {
  id: 'element', title: 'Element', icon: 'element', datasets: ['design_index'],
  async mount(ctx) {
    ctx.host.append(h('div.empty', { testid: 'soon-element' }, h('div', h('h3', 'Element arrives with milestone 2'), h('p', 'The selection and the URL already carry over; this view is being built.'))));
    return { update() {}, destroy() {} };
  },
};

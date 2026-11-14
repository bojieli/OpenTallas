// Closure view: placeholder until milestone 4.
import { h } from '../core/dom.js';
export default {
  id: 'closure', title: 'Closure', icon: 'closure', datasets: ['design_index'],
  async mount(ctx) {
    ctx.host.append(h('div.empty', { testid: 'soon-closure' }, h('div', h('h3', 'Closure arrives with milestone 4'), h('p', 'The selection and the URL already carry over; this view is being built.'))));
    return { update() {}, destroy() {} };
  },
};

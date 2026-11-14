// Token view: placeholder until milestone 3.
import { h } from '../core/dom.js';
export default {
  id: 'token', title: 'Token', icon: 'token', datasets: ['design_index'],
  async mount(ctx) {
    ctx.host.append(h('div.empty', { testid: 'soon-token' }, h('div', h('h3', 'Token arrives with milestone 3'), h('p', 'The selection and the URL already carry over; this view is being built.'))));
    return { update() {}, destroy() {} };
  },
};

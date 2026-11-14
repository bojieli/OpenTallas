// Dataflow view: placeholder until milestone 3.
import { h } from '../core/dom.js';
export default {
  id: 'dataflow', title: 'Dataflow', icon: 'dataflow', datasets: ['design_index'],
  async mount(ctx) {
    ctx.host.append(h('div.empty', { testid: 'soon-dataflow' }, h('div', h('h3', 'Dataflow arrives with milestone 3'), h('p', 'The selection and the URL already carry over; this view is being built.'))));
    return { update() {}, destroy() {} };
  },
};

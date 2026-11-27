// Overview: the five dies side by side: sign-off state, plan of record, routed coverage, data freshness.
import { h, fmt, fmtAge, fmtTime, STATES } from '../core/dom.js';
import { stateBar, stateLegend } from '../shell/inspector.js';
import { drawDiePlan, fitTransform } from '../engine/plan-canvas.js';

const displayCounts = (d) => d.counts_any_plan || d.counts;
const unsignedPacks = (d) => d.packs_unsigned_any_plan || d.packs_unsigned || {};
const signedPacks = (d) => d.packs_signed_any_plan || {
  type: d.packs.type - (unsignedPacks(d).type || 0),
  core: d.packs.core - (unsignedPacks(d).core || 0),
};
const packTotal = (p) => (p.type || 0) + (p.core || 0);

function signoffChip(census, testid) {
  return h('div', { testid },
    h('div.big', census ? fmt(census.any) : '–', h('small', 'Signed off on any plan')),
    census ? h('div.muted', `${fmt(census.by_level.type)} partition types · ${fmt(census.by_level.core)} hard cores`) : null,
    census ? h('div.muted', `${fmt(census.current)} current plan · ${fmt(census.deferred)} deferred re-sign · ${fmt(census.retired)} retired`)
      : h('div.muted', 'Sign-off census unavailable'));
}

export default {
  id: 'overview', title: 'Overview', icon: 'overview', datasets: ['design_index', 'plan_now', 'store'],
  async mount(ctx) {
    const { host, api, store } = ctx;
    host.classList.add('scroll');
    const page = h('div.page', { testid: 'overview-page' }); host.append(page);
    const r = await api.dies(), meta = ctx.meta();
    const tot = (lvl, s) => r.dies.reduce((a, d) => a + (displayCounts(d)[lvl][s] || 0), 0);
    const nTypes = r.dies.reduce((a, d) => a + d.types, 0), nCores = r.dies.reduce((a, d) => a + d.cores, 0);
    const census = r.signoff_census;
    const signedPackTotal = r.dies.reduce((a, d) => a + packTotal(signedPacks(d)), 0);
    const unsignedPackTotal = r.dies.reduce((a, d) => a + packTotal(unsignedPacks(d)), 0);
    const allT = Object.fromEntries(STATES.map((s) => [s, tot('type', s)]));
    page.append(h('h1', 'Chip overview'), h('p.lead', `Five dies, ${fmt(nTypes)} current partition types and ${fmt(nCores)} current hard cores. The design index was built ${fmtAge(meta.service.now - r.generated)}.`),
      h('div.card', { style: { marginBottom: '14px' } }, h('div.pair', { style: { gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' } },
        signoffChip(census, 'ov-signoff-any'),
        h('div', { testid: 'ov-packs' }, h('div.big', fmt(signedPackTotal)), h('small', `signed-off layout packs from any plan (+${fmt(unsignedPackTotal)} unsigned build views)`)),
        h('div', h('div.big', fmt(allT.failed), h('small', 'current partition types failed')))), h('p.note', 'Current partition types with sign-offs from any plan'), stateBar(allT), stateLegend(allT)));
    const cards = h('div.cards'); page.append(cards);
    const thumbs = [];
    for (const d of r.dies) {
      const cv = h('canvas', { 'aria-label': `${d.label} floorplan, partitions coloured by sign-off from any plan` });
      const thumb = h('a.thumb', { href: store.href({ view: 'plan', node: d.id }), title: 'Open the plan', dataset: { testid: 'thumb-' + d.id } }, cv);
      const counts = displayCounts(d), packs = signedPacks(d), unsigned = packTotal(unsignedPacks(d));
      const area = d.area_um2.by_state_any_plan || d.area_um2.by_state;
      const signedArea = (area.signed || 0) / d.area_um2.die;
      cards.append(h('article.card', { dataset: { die: d.id, testid: 'card-' + d.id } },
        h('h3', d.label, h('small', d.target || '')), thumb,
        h('div.pair', signoffChip(d.any_plan, 'ov-signoff-any-' + d.id), h('div', { testid: 'ov-signed-area-' + d.id }, h('div.big', fmt(100 * signedArea, 0) + '%', h('small', 'of current die area signed on any plan')))),
        stateBar(counts.type), stateLegend(counts.type),
        h('dl.kv', h('dt', 'plan'), h('dd', h('b.mono', d.plan.sha), ' · ', String(d.plan.date || '').slice(0, 10)), h('dt', 'outline'), h('dd', `${fmt(d.outline[0] / 1000, 2)} × ${fmt(d.outline[1] / 1000, 2)} mm · ${d.partitions} partitions`),
          h('dt', 'current designs signed on any plan'),
          h('dd', { testid: 'ov-current-designs-' + d.id }, `${counts.type.signed || 0} of ${d.types} partition types, ${counts.core.signed || 0} of ${d.cores} hard cores`),
          h('dt', 'routed packs on any plan'),
          h('dd', { title: 'Stored packs of signed-off designs from any plan' }, `${packs.type || 0} partition types, ${packs.core || 0} hard cores signed off`,
            unsigned ? h('span.muted', ` + ${unsigned} unsigned views`) : '')),
        h('div.acts', h('a.btn.sm', { href: store.href({ view: 'plan', node: d.id }), dataset: { testid: 'open-plan-' + d.id } }, 'Plan'), h('a.btn.sm', { href: store.href({ view: 'layout', node: d.id }), dataset: { testid: 'open-layout-' + d.id } }, 'Routed die map'),
          h('a.btn.sm', { href: store.href({ view: 'closure', node: d.id }), dataset: { testid: 'open-closure-' + d.id } }, 'Closure'), h('a.btn.sm', { href: store.href({ view: 'dataflow', node: d.id }) }, 'Dataflow'))));
      thumbs.push({ d, cv });
    }
    page.append(h('h2.sect', 'Data freshness'));
    const tb = h('tbody');
    for (const x of meta.datasets) tb.append(h('tr', { style: { cursor: 'default' } }, h('td', h('span.st.fresh-' + x.state, h('i.dot'), x.state)), h('td', x.label), h('td.r', x.id === 'coverage' && x.state === 'fresh' ? 'live' : x.generated ? `${fmtTime(x.generated)} (${fmtAge(x.age_s)})` : 'n/a'), h('td.muted', x.source), h('td.muted', { style: { whiteSpace: 'normal' } }, x.note || '')));
    page.append(h('div.card', { style: { padding: 0, overflow: 'auto' } }, h('table.grid', { testid: 'fresh-table' }, h('thead', h('tr', h('th', 'State'), h('th', 'Dataset'), h('th.r', 'As of'), h('th', 'Built by'), h('th', 'Note'))), tb)));

    let dead = false;
    async function paintThumb({ d, cv }) {
      let D; try { D = await api.die(d.id); } catch (e) { return; }
      if (dead) return;
      const draw = () => { const r2 = cv.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1); cv.width = r2.width * dpr; cv.height = r2.height * dpr; const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0);
        drawDiePlan(g, fitTransform(D.die.plan.outline[0], D.die.plan.outline[1], r2.width, r2.height, 0.92), D.die, D.nodes, { thumb: true, ov: { clock: true }, w: r2.width, h: r2.height }); };
      draw(); thumbs.find((t) => t.d === d).draw = draw;
    }
    (async () => { for (const t of thumbs) await paintThumb(t); })();
    const repaint = () => thumbs.forEach((t) => t.draw && t.draw());
    window.addEventListener('otx:theme', repaint); window.addEventListener('resize', repaint);
    return {
      update(st) { cards.querySelectorAll('.card').forEach((c) => c.classList.toggle('on', c.dataset.die === st.sel.die)); ctx.setScope('all dies'); },
      destroy() { dead = true; window.removeEventListener('otx:theme', repaint); window.removeEventListener('resize', repaint); },
    };
  },
};

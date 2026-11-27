// The shell: top bar, view rail, navigator, stage, inspector, status bar; panel resize / collapse; focus and full screen;
// search; freshness.  Views mount into the stage and never touch anything outside the slots they are given.
import { h, clear, icon, esc, fmtAge, fmtTime, dieShort, levelOf, shortName, ls, toast, debounce, stateCls } from '../core/dom.js';
import { store, VIEWS } from '../core/store.js';
import { api } from '../core/api.js';
import { mountNavigator } from './navigator.js';
import { mountInspector } from './inspector.js';

const NAV = { min: 180, max: 520, def: 280 }, INSP = { min: 260, max: 720, def: 348 };
const KEYS = [['/', 'Search'], ['1 – 8', 'Switch view'], ['[', 'Hide or show the navigator'], [']', 'Hide or show the inspector'], ['\\', 'Focus mode: canvas only'],
  ['Shift + \\', 'Browser full screen'], ['F', 'Fit the canvas'], ['R', 'Ruler (layout)'], ['Esc', 'Leave focus mode, clear highlight'], ['?', 'This list']];

export function createShell(root, { views, meta }) {
  const S = { meta, view: null, pop: null };
  const narrow = innerWidth < 900;   // panels are drawers on a narrow screen: closed until asked for
  const app = h('div.app', { dataset: { nav: !narrow && ls.get('nav.open', true) ? 'open' : 'closed', insp: !narrow && ls.get('insp.open', true) ? 'open' : 'closed', focus: '0' } });
  app.style.setProperty('--nav-w', ls.get('nav.w', NAV.def) + 'px'); app.style.setProperty('--insp-w', ls.get('insp.w', INSP.def) + 'px');

  /* ---------------- top bar */
  const dies = h('div.dies', { role: 'group', 'aria-label': 'Die', testid: 'die-switch' });
  const crumbs = h('nav.crumbs', { 'aria-label': 'Selection', testid: 'crumbs' });
  const q = h('input', { type: 'search', placeholder: 'Search types, cores, instances', 'aria-label': 'Search', autocomplete: 'off', spellcheck: false, testid: 'search' });
  const results = h('div.results', { hidden: true, role: 'listbox', testid: 'search-results' });
  const fresh = h('button.chip', { type: 'button', title: 'Data freshness', testid: 'fresh-chip', onclick: (e) => freshPop(e.currentTarget) });
  const theme = h('button.btn.icon.ghost', { type: 'button', title: 'Light / dark theme', 'aria-label': 'Toggle theme', testid: 'theme', onclick: toggleTheme });
  const help = h('button.btn.icon.ghost', { type: 'button', title: 'Keyboard shortcuts (?)', 'aria-label': 'Keyboard shortcuts', testid: 'help', onclick: (e) => helpPop(e.currentTarget) }, icon('help'));
  const top = h('header.top', h('a.brand', { href: '#/overview', title: 'OpenTallas Explorer', 'aria-label': 'Overview' }, icon('logo')),
    h('span.brand-name', 'OpenTallas', h('small', 'Explorer')), dies, crumbs,
    h('div.searchbox', icon('search'), q, h('kbd', '/'), results), fresh, theme, help);
  top.querySelector('.searchbox svg').classList.add('ico');

  /* ---------------- rail */
  const rail = h('nav.rail', { 'aria-label': 'Views' });
  const railLinks = {};
  views.forEach((v, i) => { railLinks[v.id] = h('a', { href: '#/' + v.id, title: `${v.title} (${i + 1})`, dataset: { testid: 'view-' + v.id } }, icon(v.icon), v.short || v.title); rail.append(railLinks[v.id]); });

  /* ---------------- panels */
  const navBody = h('div.panel-body');
  const navPanel = h('aside.panel.nav', { 'aria-label': 'Navigator', testid: 'navigator' },
    h('div.panel-head', h('h2', 'Navigator'), h('button.btn.icon.ghost.sm', { type: 'button', title: 'Hide navigator ([)', 'aria-label': 'Hide navigator', testid: 'nav-hide', onclick: () => setPanel('nav', false) }, icon('chevL'))),
    navBody, h('div.split', { dataset: { split: 'nav' }, title: 'Drag to resize, double-click to reset', testid: 'split-nav' }));
  const inspTabs = h('div.tabs', { role: 'tablist', testid: 'insp-tabs' });
  const inspBody = h('div.panel-body', { testid: 'insp-body' });
  const inspPanel = h('aside.panel.insp', { 'aria-label': 'Inspector', testid: 'inspector' },
    h('div.split', { dataset: { split: 'insp' }, title: 'Drag to resize, double-click to reset', testid: 'split-insp' }),
    h('div.panel-head', h('h2', 'Inspector'), h('button.btn.icon.ghost.sm', { type: 'button', title: 'Hide inspector (])', 'aria-label': 'Hide inspector', testid: 'insp-hide', onclick: () => setPanel('insp', false) }, icon('chevR'))),
    inspTabs, inspBody);

  /* ---------------- stage */
  const title = h('span.title', { testid: 'view-title' }), scope = h('span.scope', { testid: 'view-scope' }), tools = h('div.tools', { testid: 'view-tools' });
  const navShow = h('button.btn.icon.ghost.only-normal', { type: 'button', title: 'Show navigator ([)', 'aria-label': 'Show navigator', testid: 'nav-show', onclick: () => setPanel('nav', true) }, icon('panelL'));
  const inspShow = h('button.btn.icon.ghost.only-normal', { type: 'button', title: 'Show inspector (])', 'aria-label': 'Show inspector', testid: 'insp-show', onclick: () => setPanel('insp', true) }, icon('panelR'));
  const focusBtn = h('button.btn.icon.ghost', { type: 'button', title: 'Focus mode: canvas only (\\)', 'aria-label': 'Focus mode', 'aria-pressed': 'false', testid: 'focus', onclick: () => setFocus(app.dataset.focus !== '1') }, icon('focus'));
  const fullBtn = h('button.btn.icon.ghost', { type: 'button', title: 'Browser full screen (Shift+\\)', 'aria-label': 'Full screen', testid: 'fullscreen', onclick: toggleFull }, icon('full'));
  const linkBtn = h('button.btn.icon.ghost.only-normal', { type: 'button', title: 'Copy a link to this view', 'aria-label': 'Copy link', testid: 'copy-link', onclick: copyLink }, icon('link'));
  const stageBody = h('div.stage-body', { testid: 'stage' });
  const stage = h('main.stage', h('div.stage-bar', navShow, title, tools, scope, linkBtn, focusBtn, fullBtn, inspShow), stageBody);

  /* ---------------- status bar */
  const readout = h('span.readout', { testid: 'readout' }), asof = h('span.fresh', { testid: 'asof' }), plan = h('span', { testid: 'plan-sha' }), svc = h('span.muted', { testid: 'service-sha' });
  const status = h('footer.status', readout, asof, plan, svc);

  app.append(top, rail, navPanel, stage, inspPanel, status);
  root.append(app);

  const nav = mountNavigator(navBody);
  const insp = mountInspector(inspTabs, inspBody);

  /* ---------------- panels: collapse, resize */
  function setPanel(which, open) {
    app.dataset[which] = open ? 'open' : 'closed'; if (innerWidth >= 900) ls.set(which + '.open', open); else if (open) app.dataset[which === 'nav' ? 'insp' : 'nav'] = 'closed'; syncPanelButtons();
    window.dispatchEvent(new Event('resize'));
  }
  function syncPanelButtons() {
    navShow.hidden = app.dataset.nav === 'open'; inspShow.hidden = app.dataset.insp === 'open';
  }
  function setWidth(which, w) {
    const lim = which === 'nav' ? NAV : INSP; w = Math.round(Math.max(lim.min, Math.min(lim.max, w)));
    app.style.setProperty('--' + which + '-w', w + 'px'); ls.set(which + '.w', w); return w;
  }
  for (const sp of app.querySelectorAll('.split')) {
    const which = sp.dataset.split, lim = which === 'nav' ? NAV : INSP;
    sp.addEventListener('pointerdown', (e) => {
      e.preventDefault(); sp.setPointerCapture(e.pointerId); sp.classList.add('on'); app.classList.add('dragging');
      const x0 = e.clientX, w0 = (which === 'nav' ? navPanel : inspPanel).getBoundingClientRect().width;
      const move = (ev) => { setWidth(which, w0 + (which === 'nav' ? ev.clientX - x0 : x0 - ev.clientX)); window.dispatchEvent(new Event('resize')); };
      const up = () => { sp.classList.remove('on'); app.classList.remove('dragging'); sp.removeEventListener('pointermove', move); sp.removeEventListener('pointerup', up); sp.removeEventListener('pointercancel', up); };
      sp.addEventListener('pointermove', move); sp.addEventListener('pointerup', up); sp.addEventListener('pointercancel', up);
    });
    sp.addEventListener('dblclick', () => { setWidth(which, lim.def); window.dispatchEvent(new Event('resize')); });
    sp.tabIndex = 0; sp.setAttribute('role', 'separator'); sp.setAttribute('aria-orientation', 'vertical');
    sp.addEventListener('keydown', (e) => {
      const cur = (which === 'nav' ? navPanel : inspPanel).getBoundingClientRect().width, d = (e.key === 'ArrowLeft' ? -24 : e.key === 'ArrowRight' ? 24 : 0) * (which === 'nav' ? 1 : -1);
      if (d) { e.preventDefault(); setWidth(which, cur + d); window.dispatchEvent(new Event('resize')); }
    });
  }
  syncPanelButtons();

  /* ---------------- focus / full screen */
  function setFocus(on) {
    app.dataset.focus = on ? '1' : '0'; focusBtn.setAttribute('aria-pressed', String(on));
    focusBtn.title = on ? 'Leave focus mode (\\ or Esc)' : 'Focus mode: canvas only (\\)';
    clear(focusBtn).append(icon(on ? 'exit' : 'focus'));
    window.dispatchEvent(new Event('resize'));
  }
  function toggleFull() {
    if (document.fullscreenElement) document.exitFullscreen();
    else { setFocus(true); const p = app.requestFullscreen && app.requestFullscreen(); if (p && p.catch) p.catch(() => toast('The browser refused full screen; focus mode is on')); }
  }
  document.addEventListener('fullscreenchange', () => { if (!document.fullscreenElement) setFocus(false); });
  async function copyLink() {
    try { await navigator.clipboard.writeText(location.href); toast('Link copied'); } catch (e) { toast(location.href, 5000); }
  }

  /* ---------------- theme */
  const curTheme = () => document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  function paintTheme() { clear(theme).append(icon(curTheme() === 'dark' ? 'sun' : 'moon')); }
  function toggleTheme() {
    const t = curTheme() === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = t; ls.set('theme', t); paintTheme();
    window.dispatchEvent(new CustomEvent('otx:theme', { detail: t }));
  }
  paintTheme();

  /* ---------------- popovers */
  function pop(anchor, content) {
    closePop();
    const p = h('div.pop', { role: 'dialog', testid: 'popover' }, content); document.body.append(p);
    const r = anchor.getBoundingClientRect(), w = p.offsetWidth;
    p.style.top = (r.bottom + 6) + 'px'; p.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.right - w)) + 'px';
    S.pop = p; S.popAnchor = anchor;
    setTimeout(() => document.addEventListener('pointerdown', outside, true), 0);
  }
  function outside(e) { if (S.pop && !S.pop.contains(e.target) && e.target !== S.popAnchor && !S.popAnchor.contains(e.target)) closePop(); }
  function closePop() { if (S.pop) { S.pop.remove(); S.pop = null; document.removeEventListener('pointerdown', outside, true); return true; } return false; }
  function helpPop(a) {
    if (S.pop && S.popAnchor === a) return closePop();
    pop(a, [h('h4', 'Keyboard shortcuts'), h('dl.kv', KEYS.map(([k, v]) => [h('dt', h('kbd', k)), h('dd', v)]))]);
  }
  function freshPop(a) {
    if (S.pop && S.popAnchor === a) return closePop();
    const used = new Set((S.view && S.view.datasets) || []);
    const rows = S.meta.datasets.map((d) => h('tr', { 'aria-selected': used.has(d.id) ? 'true' : null },
      h('td', h('span.st.fresh-' + d.state, h('i.dot'), d.state)), h('td', d.label, d.note ? h('div.muted', d.note) : null),
      h('td.r', { title: d.generated ? fmtTime(d.generated) : '' }, d.id === 'coverage' && d.state === 'fresh' ? 'live' : fmtAge(d.age_s)), h('td.muted', d.source)));
    const t = h('table.grid', h('thead', h('tr', h('th', 'State'), h('th', 'Dataset'), h('th.r', 'As of'), h('th', 'Built by'))), h('tbody', rows));
    t.querySelectorAll('td').forEach((td) => { td.style.whiteSpace = 'normal'; });
    pop(a, [h('h4', 'Data freshness'), h('p.note', { style: { margin: '0 0 8px' } }, 'Highlighted rows feed the current view. Layout packs are cut once per sign-off and never go stale.'), t,
      h('div', { style: { marginTop: '10px', display: 'flex', gap: '8px' } }, h('button.btn.sm', { type: 'button', testid: 'reload-data', onclick: reload }, 'Reload data'))]);
  }
  async function reload() {
    closePop(); api.clear();
    try { S.meta = await api.meta(true); toast('Data reloaded'); } catch (e) { toast('Reload failed: ' + e.message); }
    paintDies(); render(store.get(), null, true);
  }
  setInterval(async () => { try { const m = await api.meta(true); const was = dsOf('design_index'); S.meta = m; paintFresh(); const now = dsOf('design_index'); if (was && now && was.generated !== now.generated) toast('Newer data is available: open the freshness chip and reload', 6000); } catch (e) { /* offline: the chip keeps its last state */ } }, 300000);
  const dsOf = (id) => S.meta.datasets.find((d) => d.id === id);

  /* ---------------- search */
  let hits = [], cur = -1, seq = 0;
  const runSearch = debounce(async () => {
    const s = q.value.trim(); const my = ++seq;
    if (s.length < 2) { results.hidden = true; return; }
    let r; try { r = await api.search(s, store.get().sel.die); } catch (e) { r = { results: [], error: e.message }; }
    if (my !== seq) return;
    hits = r.results; cur = hits.length ? 0 : -1;
    clear(results);
    if (!hits.length) results.append(h('div.none', r.error ? 'Search failed: ' + r.error : `No partition type, hard core or instance matches “${s}”.`));
    hits.forEach((o, i) => results.append(h('button', { type: 'button', role: 'option', 'aria-selected': String(i === cur), dataset: { i }, onclick: () => pick(i) },
      h('span.kind', o.kind), h('span.nm', o.name, h('small', o.kind === 'instance' ? `${dieShort(o.die)} · instance of ${o.of || '?'}` : dieShort(o.die))),
      h('span.st.' + stateCls(o.state), h('i.dot'), o.state || ''))));
    if (r.total > hits.length) results.append(h('div.none', `${r.total - hits.length} more: type more letters.`));
    results.hidden = false;
  }, 160);
  function pick(i) {
    const o = hits[i]; if (!o) return;
    results.hidden = true; q.value = ''; q.blur();
    const v = store.get().view;
    store.go({ view: v === 'overview' ? (o.kind === 'die' ? 'plan' : 'element') : v, node: o.id, inst: o.inst || null });
  }
  q.addEventListener('input', runSearch);
  q.addEventListener('focus', () => { if (hits.length && q.value.trim().length >= 2) results.hidden = false; });
  q.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); if (!hits.length) return; cur = (cur + (e.key === 'ArrowDown' ? 1 : hits.length - 1)) % hits.length;
      results.querySelectorAll('button').forEach((b, i) => { b.setAttribute('aria-selected', String(i === cur)); if (i === cur) b.scrollIntoView({ block: 'nearest' }); }); }
    else if (e.key === 'Enter') { e.preventDefault(); pick(cur); }
    else if (e.key === 'Escape') { results.hidden = true; q.blur(); }
  });
  document.addEventListener('pointerdown', (e) => { if (!e.target.closest('.searchbox')) results.hidden = true; });

  /* ---------------- keys */
  document.addEventListener('keydown', (e) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable;
    if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || (e.key === '/' && !typing)) { e.preventDefault(); q.focus(); q.select(); return; }
    if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'Escape') { if (closePop()) return; if (app.dataset.focus === '1') { if (document.fullscreenElement) document.exitFullscreen(); setFocus(false); return; } }
    if (e.key === '[') setPanel('nav', app.dataset.nav !== 'open');
    else if (e.key === ']') setPanel('insp', app.dataset.insp !== 'open');
    else if (e.key === '\\') setFocus(app.dataset.focus !== '1');
    else if (e.key === '|') toggleFull();
    else if (e.key === '?') helpPop(help);
    else if (/^[1-8]$/.test(e.key)) { const v = views[+e.key - 1]; if (v) store.go({ view: v.id }); }
    else return;
    e.preventDefault();
  });

  /* ---------------- paint on state */
  function paintDies() {
    const cur = store.get().sel.die;
    clear(dies);
    for (const d of S.meta.dies) {
      const c = (S.dies && S.dies[d.id]) || null, tot = c ? c.types : 0, done = c ? c.counts.type.signed : 0;
      dies.append(h('button', { type: 'button', 'aria-pressed': String(d.id === cur), title: `${d.label}${c ? ` · ${done} of ${tot} partition types signed off` : ''} · plan ${d.plan.sha}`, dataset: { testid: 'die-' + d.id },
        onclick: () => store.go({ view: store.get().view === 'overview' ? 'plan' : store.get().view, node: d.id }) },
        h('span', dieShort(d.id)), c ? h('span.meter', h('i', { style: { width: (tot ? 100 * done / tot : 0) + '%' } })) : null));
    }
  }
  function paintCrumbs(st) {
    clear(crumbs);
    const { die, node, inst, net } = st.sel;
    if (!die) { crumbs.append(h('b', 'All dies')); return; }
    const d = S.meta.dies.find((x) => x.id === die);
    const lvl = levelOf(node);
    crumbs.append(lvl === 'die' ? h('b', d ? d.label : die) : h('a', { href: store.href({ node: die }) }, d ? d.label : die));
    if (d) crumbs.append(h('span.chip', { title: (d.plan.wave ? 'kit wave plan, as counted: ' + d.plan.wave.host + ':' + d.plan.wave.path : 'plan of record on main: ' + d.plan.path), dataset: { testid: 'plan-chip' }, style: { flex: 'none' } }, (d.plan.wave ? 'wave plan ' : 'plan ') + d.plan.sha));
    if (lvl !== 'die') crumbs.append(h('span.sep', '›'), h('span.muted', lvl), h('b.mono', shortName(node)));
    if (inst) crumbs.append(h('span.sep', '@'), h('span.mono', inst));
    if (net) crumbs.append(h('span.sep', '·'), h('span.muted', 'net'), h('span.mono', net));
  }
  function paintFresh() {
    const used = (S.view && S.view.datasets) || [], rows = S.meta.datasets.filter((d) => used.includes(d.id));
    const worst = rows.some((d) => d.state === 'missing') ? 'missing' : rows.some((d) => d.state === 'stale') ? 'stale' : 'fresh';
    const gens = rows.filter((d) => d.generated && d.id !== 'store' && d.id !== 'coverage').map((d) => d.generated), oldest = gens.length ? Math.min(...gens) : null;
    clear(fresh).append(h('span.st.fresh-' + worst, h('i.dot')), worst === 'fresh' ? 'Data fresh' : worst === 'stale' ? 'Stale data' : 'Data missing');
    fresh.dataset.state = worst;
    const now = S.meta.service.now;
    clear(asof).append(h('span.st.fresh-' + worst, h('i.dot')), 'data as of ', h('b', oldest ? fmtTime(oldest) : 'n/a'), oldest ? ` (${fmtAge(now - oldest)})` : '');
    const die = store.get().sel.die, d = S.meta.dies.find((x) => x.id === die);
    clear(plan); if (d) plan.append(d.plan.wave ? 'wave plan ' : 'plan ', h('b.mono', { title: `${d.plan.path}\ncommit ${d.plan.commit || '?'} · ${d.plan.date || ''}` }, d.plan.sha), d.plan.date ? ` (${String(d.plan.date).slice(0, 10)})` : '');
    svc.textContent = 'service ' + (S.meta.service.sha || 'dev');
  }

  let mounted = null, mountedId = null;
  async function render(st, prev, force) {
    for (const id of VIEWS) if (railLinks[id]) { railLinks[id].href = store.href({ view: id }); if (id === st.view) railLinks[id].setAttribute('aria-current', 'page'); else railLinks[id].removeAttribute('aria-current'); }
    const v = views.find((x) => x.id === st.view) || views[0];
    S.view = v;
    paintDies(); paintCrumbs(st); paintFresh();
    document.title = (st.sel.node ? shortName(st.sel.node) + ' · ' : '') + v.title + ' · OpenTallas Explorer';
    nav.update(st); insp.update(st);
    if (mountedId !== v.id || force) {
      if (mounted && mounted.destroy) { try { mounted.destroy(); } catch (e) { console.error(e); } }
      clear(stageBody); clear(tools); stageBody.className = 'stage-body'; readout.textContent = ''; insp.setTabs([]);
      title.textContent = v.title; scope.textContent = '';
      mountedId = v.id; mounted = null;
      const ctx = { host: stageBody, tools, store, api, meta: () => S.meta, setScope: (t) => { scope.textContent = t || ''; scope.title = t || ''; }, setReadout: (t) => { readout.textContent = t || ''; },
        inspector: insp, toast, select: (p, o) => store.go(p, o), setParams: (p, o) => store.setParams(p, o) };
      try { mounted = await v.mount(ctx); } catch (e) { console.error(e); showError(stageBody, e); return; }
      if (mountedId !== v.id) { if (mounted && mounted.destroy) mounted.destroy(); return; }
    }
    if (mounted && mounted.update) { try { await mounted.update(store.get(), prev); } catch (e) { console.error(e); showError(stageBody, e); mountedId = null; } }
  }
  store.subscribe((st, prev) => render(st, prev));
  api.dies().then((r) => { S.dies = Object.fromEntries(r.dies.map((d) => [d.id, d])); paintDies(); }).catch(() => {});
  return { render: () => render(store.get(), null), app, setFocus, setPanel };
}

export function showError(host, e) {
  clear(host).append(h('div.empty', { testid: 'view-error' }, h('div', h('h3', 'This view could not load'), h('p', e && e.message ? e.message : String(e)),
    e && e.detail ? h('p.muted.mono', e.detail) : null, h('button.btn', { type: 'button', onclick: () => location.reload() }, 'Reload'))));
}
export function showBusy(host, msg) { const b = h('div.busy', h('div', h('div.spinner'), msg || 'Loading…')); host.append(b); return b; }

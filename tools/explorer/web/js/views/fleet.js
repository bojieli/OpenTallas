// Fleet: the build hosts and their jobs.  Data: the fleet-viz collectors (/api/fleet, /api/fleetjobs, /api/jobs,
// /api/verdicts, proxied by /api/v1/fleet/*) plus a light probe of RAM admission and disks (/api/v1/fleet/probe).
import { h, clear, fmt, fmtAge, fmtTime, cssv, debounce, dieShort } from '../core/dom.js';

const HOSTS = ['EPYC2', 'EPYC7', 'EPYC8', 'EPYC9', 'EPYC10', 'INTEL1', 'INTEL2', 'localhost'];   // the fleet today; others are listed as retired when down
const COLS = [['host', 'Host'], ['kind', 'Kind'], ['die', 'Die'], ['item', 'Item'], ['stage', 'Stage'], ['attempt', 'Att.', 'r'], ['elapsed', 'Elapsed', 'r'], ['mem', 'RAM GB', 'r'], ['peak', 'Peak', 'r'], ['max', 'Limit', 'r'], ['cpu', 'CPU', 'r'], ['n', 'Procs', 'r']];
const dur = (s) => s == null ? '–' : s < 90 ? Math.round(s) + ' s' : s < 5400 ? Math.round(s / 60) + ' min' : s < 172800 ? fmt(s / 3600, 1) + ' h' : fmt(s / 86400, 1) + ' d';
const gb = (v) => v == null ? '–' : fmt(v, v < 10 ? 1 : 0);
const meter = (frac, cls, title) => h('div.meter2' + (cls ? '.' + cls : ''), { title: title || '' }, h('i', { style: { width: Math.max(0, Math.min(100, 100 * frac)) + '%' } }));
const level = (f) => f >= 1.0 ? 'bad' : f >= 0.9 ? 'warn' : '';

export default {
  id: 'fleet', title: 'Fleet', icon: 'fleet', datasets: ['fleet'],
  async mount(ctx) {
    const { host, tools, store, api } = ctx;
    host.classList.add('scroll');
    const S = { fleet: null, jobs: null, loop: null, verdicts: null, probe: null, err: null, hostSel: null, kind: 'all', q: '', sort: 'elapsed', dir: -1, job: null, timers: [], dead: false, now: Date.now() / 1000 };
    const page = h('div.page.fleetpage', { testid: 'fleet-page' }); host.append(page);
    const banner = h('div', { testid: 'fleet-banner' }), tiles = h('div.card', { testid: 'fleet-totals' }), cards = h('div.cards.hostcards', { testid: 'fleet-hosts' }), ctl = h('div.ctlrow', { testid: 'fleet-controls', style: { top: '0', margin: '0 -16px', padding: '8px 16px' } });
    const jobsBox = h('div', { testid: 'fleet-jobs-box' }), loopBox = h('div', { testid: 'fleet-loop' });
    page.append(banner, tiles, h('h2.sect', 'Hosts'), cards, h('h2.sect', 'Jobs'), ctl, jobsBox, h('h2.sect', 'Closure loop and recent sign-offs'), loopBox);
    const kindSeg = h('div.seg', { role: 'group', 'aria-label': 'Job kind' }, [['all', 'All'], ['run', 'Running'], ['wait', 'Waiting']].map(([id, l]) => h('button', { type: 'button', dataset: { k: id, testid: 'fleet-kind-' + id }, onclick: () => { S.kind = id; ctx.setParams({ kind: id === 'all' ? null : id }); paintJobs(); } }, l)));
    const q = h('input.field', { type: 'search', placeholder: 'Filter: die, item, stage, host, command', 'aria-label': 'Filter jobs', style: { width: '260px' }, spellcheck: false, testid: 'fleet-filter' });
    q.addEventListener('input', debounce(() => { S.q = q.value.trim().toLowerCase(); paintJobs(); }, 120));
    const hostChip = h('button.chip', { type: 'button', hidden: true, title: 'Clear the host filter', testid: 'fleet-host-clear', onclick: () => selectHost(null) });
    const count = h('span.muted', { style: { marginLeft: 'auto', fontSize: 'var(--fs-s)' }, dataset: { testid: 'fleet-count' } });
    ctl.append(kindSeg, q, hostChip, count);
    const refreshBtn = h('button.btn', { type: 'button', title: 'Reload now (the view polls every 5 s)', testid: 'fleet-refresh', onclick: () => { pollFleet(); pollJobs(); pollProbe(); } }, 'Refresh');
    const live = h('span.chip', { testid: 'fleet-live' });
    tools.append(refreshBtn, live);

    const selectHost = (label) => { S.hostSel = label; ctx.setParams({ host: label }); paintHosts(); paintJobs(); if (label) ctx.inspector.show('host'); else if (ctx.inspector.current() === 'host') ctx.inspector.show('host'); };
    const probeOf = (label) => (S.probe && S.probe.hosts && S.probe.hosts[String(label).toUpperCase()]) || null;

    function paintTotals() {
      const f = S.fleet; if (!f) return;
      const t = f.totals || {}, jh = (S.jobs && S.jobs.hosts) || {}, run = Object.values(jh).reduce((a, x) => a + (x.other || 0) + (x.loop || 0), 0), wait = Object.values(jh).reduce((a, x) => a + (x.waiters || 0), 0), held = Object.values(jh).reduce((a, x) => a + (x.held || 0), 0);
      const up = f.hosts.filter((x) => x.state === 'up').length, cur = f.hosts.filter((x) => HOSTS.includes(x.label)).length;
      const cv = h('canvas', { width: 520, height: 46, style: { width: '100%', height: '46px' }, 'aria-label': 'busy cores over the last hour' });
      clear(tiles).append(h('div.pair', { style: { gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' } },
        h('div', h('div.big', `${up}`, h('small', `of ${cur} hosts up`))), h('div', h('div.big', fmt(t.busy, 0), h('small', `of ${fmt(t.cores)} cores busy`))),
        h('div', h('div.big', fmt(t.mem_used, 0), h('small', `of ${fmt(t.mem_total, 0)} GB RAM used`))), h('div', h('div.big', fmt(run), h('small', 'jobs running'))),
        h('div', h('div.big' + (wait ? '' : ''), fmt(wait), h('small', `waiting for RAM${held ? ' · ' + held + ' held' : ''}`))), h('div', h('div.big', fmt(t.docker), h('small', 'containers')))),
        h('div', h('div.muted', { style: { fontSize: 'var(--fs-xs)', marginBottom: '2px' } }, 'Busy cores, last hour'), cv));
      const H = f.history || []; if (H.length > 2) {
        const g = cv.getContext('2d'), W = cv.width, Hh = cv.height, t0 = H[0][0], t1 = H[H.length - 1][0], mx = Math.max(...H.map((r) => r[2])) || 1;
        g.strokeStyle = cssv('--line'); g.lineWidth = 1; g.beginPath(); g.moveTo(0, Hh - 0.5); g.lineTo(W, Hh - 0.5); g.stroke();
        g.strokeStyle = cssv('--c1'); g.lineWidth = 2; g.beginPath(); H.forEach((r, i) => { const x = (r[0] - t0) / Math.max(1, t1 - t0) * W, y = Hh - 2 - (r[1] / mx) * (Hh - 6); i ? g.lineTo(x, y) : g.moveTo(x, y); }); g.stroke();
      }
    }
    function hostCard(x) {
      const jh = (S.jobs && S.jobs.hosts && S.jobs.hosts[x.label]) || x.jobs || {}, p = probeOf(x.label), a = p && p.admit, up = x.state === 'up', ncpu = (x.cores || []).length || (a && a.ncpu) || 0;
      const src = S.fleet.fresh && S.fleet.fresh.sources && S.fleet.fresh.sources['host:' + (x.alias || x.label).toLowerCase()];
      const card = h('article.card.hostcard' + (S.hostSel === x.label ? '.on' : '') + (up ? '' : '.down'), { tabIndex: 0, role: 'button', 'aria-pressed': String(S.hostSel === x.label), title: 'Click to filter the jobs to this host', dataset: { host: x.label, testid: 'host-' + x.label },
        onclick: () => selectHost(S.hostSel === x.label ? null : x.label), onkeydown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectHost(S.hostSel === x.label ? null : x.label); } } },
        h('h3', x.label, h('small', up ? `${ncpu} threads · ${fmt(x.mem_total, 0)} GB` : 'down'), h('span.st.fresh-' + (up ? 'fresh' : 'missing'), { style: { marginLeft: 'auto' } }, h('i.dot'), up ? 'up' : 'down')));
      if (!up) { card.append(h('p.note', { style: { margin: 0 } }, (src && src.error) || x.error || 'no answer from the probe')); return card; }
      const lf = ncpu ? x.load / ncpu : 0, mf = x.mem_total ? x.mem_used / x.mem_total : 0;
      // load is drawn against twice the thread count: this fleet runs oversubscribed on purpose; amber above 2x, red above 3x
      card.append(h('div.hrow', h('span', { title: 'load average (1 min) against the thread count; the bar is full at 2x' }, 'Load'), meter(lf / 2, lf > 3 ? 'bad' : lf > 2 ? 'warn' : ''), h('b.num', `${fmt(x.load, 0)} / ${ncpu}`)),
        h('div.hrow', h('span', 'RAM'), meter(mf, level(mf / 0.97)), h('b.num', `${fmt(x.mem_used, 0)} / ${fmt(x.mem_total, 0)} GB`)),
        h('div.hrow', h('span', 'Admit'), a ? meter(a.total_gb ? a.admit_gb / a.total_gb : 0, a.admit_gb < 48 ? 'warn' : 'ok', 'RAM that ot-run would admit for a new job now') : h('span.muted', { style: { gridColumn: '2 / 4' } }, p ? (p.error || 'no admission data') : 'not probed from the service host'), a ? h('b.num', `${fmt(a.admit_gb, 0)} GB free`) : null),
        h('div.hrow', h('span', 'Jobs'), h('span', { style: { gridColumn: '2 / 4' } }, h('b', fmt((jh.other || 0) + (jh.loop || 0))), ' running · ', h('b' + (jh.waiters ? '.neg' : ''), fmt(jh.waiters || 0)), ' waiting', jh.held ? [' · ', h('b', jh.held), ' held'] : '', ` · ${fmt(x.docker || 0)} containers`)));
      for (const d of (p && p.disks) || []) { if (d.same_as) continue; const f = d.pct / 100; card.append(h('div.hrow', h('span', { title: d.mount }, d.mount === '/' ? 'Root' : d.mount.replace('/srv/opentallas-', '')), meter(f, f >= 0.92 ? 'bad' : f >= 0.8 ? 'warn' : ''), h('b.num', `${fmt(d.avail_gb)} GB free`))); }
      if (x.cores && x.cores.length) { const cv = h('canvas.corestrip', { width: x.cores.length, height: 1, title: 'per-thread utilisation' }); card.append(cv);
        const g = cv.getContext('2d'), c = cssv('--c1'); x.cores.forEach((v, i) => { g.globalAlpha = Math.max(0.06, v / 100); g.fillStyle = c; g.fillRect(i, 0, 1, 1); }); }
      return card;
    }
    function paintHosts() {
      const f = S.fleet; if (!f) return;
      const order = f.hosts.slice().sort((a, b) => (HOSTS.indexOf(a.label) < 0 ? 99 : HOSTS.indexOf(a.label)) - (HOSTS.indexOf(b.label) < 0 ? 99 : HOSTS.indexOf(b.label)));
      const cur = order.filter((x) => HOSTS.includes(x.label)), old = order.filter((x) => !HOSTS.includes(x.label));
      clear(cards).append(...cur.map(hostCard));
      if (old.length) cards.append(h('p.note', { style: { gridColumn: '1 / -1', margin: 0 } }, `Not in the fleet any more (still in the collector's host list): ${old.map((x) => `${x.label} (${x.state})`).join(', ')}.`));
      hostChip.hidden = !S.hostSel; hostChip.textContent = S.hostSel ? `Host ${S.hostSel} ×` : '';
    }
    const elapsed = (r) => r.start ? S.now - r.start : null;
    function jobRows() {
      const R = (S.jobs && S.jobs.rows) || [];
      const key = { host: (r) => r.host, kind: (r) => r.kind, die: (r) => r.die || '~', item: (r) => r.item || '~', stage: (r) => r.stage || '~', attempt: (r) => r.attempt ?? -1, elapsed: (r) => elapsed(r) ?? -1, mem: (r) => r.mem ?? -1, peak: (r) => r.peak ?? -1, max: (r) => r.max ?? r.req ?? -1, cpu: (r) => r.cpu ?? -1, n: (r) => r.n ?? -1 }[S.sort];
      return R.filter((r) => (!S.hostSel || r.host === S.hostSel) && (S.kind === 'all' || (S.kind === 'wait') === (r.kind === 'waiter')) && (!S.q || (`${r.host} ${r.kind} ${r.die || ''} ${r.item || ''} ${r.stage || ''} ${r.job || ''} ${r.name} ${r.cwd || ''}`).toLowerCase().includes(S.q)))
        .sort((a, b) => { const x = key(a), y = key(b); return (x < y ? -1 : x > y ? 1 : 0) * S.dir; });
    }
    function paintJobs() {
      kindSeg.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.k === S.kind)));
      if (!S.jobs) { clear(jobsBox).append(h('p.note', S.jobsErr ? 'The job list did not load: ' + S.jobsErr : 'Loading the job list…')); return; }
      const R = jobRows(), show = R.slice(0, 400);
      count.textContent = `${fmt(R.length)} of ${fmt(S.jobs.rows.length)} jobs${R.length > 400 ? ' · first 400 shown' : ''}`;
      const head = h('tr', COLS.map(([id, label, cls]) => h('th' + (cls ? '.r' : ''), { 'aria-sort': S.sort === id ? (S.dir > 0 ? 'ascending' : 'descending') : null, dataset: { testid: 'fleet-sort-' + id }, onclick: () => { if (S.sort === id) S.dir = -S.dir; else { S.sort = id; S.dir = id === 'elapsed' || id === 'mem' || id === 'peak' || id === 'cpu' ? -1 : 1; } paintJobs(); } }, label, S.sort === id ? h('span.arr', S.dir > 0 ? '▲' : '▼') : null)));
      const tb = h('tbody');
      show.forEach((r, i) => tb.append(h('tr', { dataset: { i }, 'aria-selected': S.job && S.job.unit === r.unit && S.job.start === r.start && S.job.host === r.host ? 'true' : null, title: r.job || r.name },
        h('td', r.host), h('td' + (r.kind === 'waiter' ? '.neg' : '.muted'), r.kind === 'waiter' ? 'waiting' : r.kind.replace(' job', '')), h('td', r.die ? dieShort(r.die) : h('span.muted', '–')),
        h('td', r.item ? h('a.mono', { href: '/element?name=' + encodeURIComponent(r.item.replace(/__pv[0-9a-f]+$/, '')), title: 'Open this design in the Element view' }, r.item) : h('span.muted.mono', (r.job || r.name || '').slice(0, 46))),
        h('td', r.stage || h('span.muted', '–')), h('td.r', r.attempt ?? ''), h('td.r', dur(elapsed(r))), h('td.r', gb(r.mem)), h('td.r', gb(r.peak)), h('td.r' + (r.max != null && r.peak != null && r.peak > 0.9 * r.max ? '.neg' : ''), gb(r.max ?? r.req)), h('td.r', r.cpu == null ? '–' : fmt(r.cpu, 2)), h('td.r', r.n ?? ''))));
      tb.addEventListener('click', (e) => { if (e.target.closest('a')) return; const tr = e.target.closest('tr'); if (!tr) return; S.job = show[+tr.dataset.i]; ctx.inspector.show('job'); paintJobs(); });
      clear(jobsBox).append(h('div.card.sticky-head', { style: { padding: 0 } }, h('table.grid', { testid: 'fleet-jobs' }, h('thead', head), tb)), R.length ? null : h('p.note', 'No job matches the filters.'));
    }
    function paintLoop() {
      const f = S.fleet, L = S.loop; if (!f) return;
      const lp = f.loop || {}, rec = f.recent || [];
      clear(loopBox).append(h('div.pair', { style: { gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', alignItems: 'start' } },
        h('div.card', h('h3', 'Closure loop', h('small', `${fmt(lp.running)} running · ${fmt(lp.queued)} queued · ${fmt(lp.closed_today)} closed today · ${fmt(lp.closed_total)} in total`)),
          L && L.jobs && L.jobs.length ? h('table.grid', { testid: 'fleet-loop-jobs' }, h('thead', h('tr', { style: { cursor: 'default' } }, h('th', 'Job'), h('th', 'Status'), h('th', 'Host'), h('th', 'Stage'), h('th', 'Owner'))),
            h('tbody', L.jobs.slice(0, 40).map((j) => h('tr', { style: { cursor: 'default' }, title: j.event || j.reason || '' }, h('td.mono', j.block || j.name), h('td', j.status), h('td', j.label || j.host), h('td', j.stage || ''), h('td.muted', j.owner || ''))))) : h('p.note', { style: { margin: 0 } }, 'No closure-loop job is listed.'),
          Object.keys(lp.running_by_cat || {}).length ? h('p.note', 'Running by target: ' + Object.entries(lp.running_by_cat).map(([k, v]) => `${k} ${v}`).join(' · ')) : null),
        h('div.card', h('h3', 'Recent sign-offs', h('small', `${rec.length} newest`)), rec.length ? h('table.grid', { testid: 'fleet-recent' }, h('thead', h('tr', { style: { cursor: 'default' } }, h('th', 'Design'), h('th', 'Host'), h('th.r', 'Setup ps'), h('th.r', 'Hold ps'), h('th.r', 'DRC'), h('th.r', 'When'))),
          h('tbody', rec.slice(0, 30).map((r) => h('tr', { style: { cursor: 'default' } }, h('td', h('a.mono', { href: '/element?name=' + encodeURIComponent(r.block), title: 'Open in the Element view' }, r.name || r.block)), h('td', r.host), h('td.r' + (r.setup == null ? '.muted' : r.setup >= -42 ? '.pos' : '.neg'), r.setup == null ? '–' : fmt(r.setup, 1)),
            h('td.r' + (r.hold == null ? '.muted' : r.hold >= 0 ? '.pos' : '.neg'), r.hold == null ? '–' : fmt(r.hold, 1)), h('td.r' + (r.drc == null ? '.muted' : r.drc === 0 ? '.pos' : '.neg'), r.drc ?? '–'), h('td.r.muted', fmtAge(S.now - r.t)))))) : h('p.note', { style: { margin: 0 } }, 'Nothing closed recently.'))));
    }
    function paintLive() {
      const f = S.fleet, age = f ? Date.now() / 1000 - (f.generated_at || f.t) : null, ok = f && age < 60 && !S.err;
      clear(live).append(h('span.st.fresh-' + (ok ? 'fresh' : S.err ? 'missing' : 'stale'), h('i.dot')), S.err ? 'collector unreachable' : f ? `live · ${age < 8 ? 'now' : fmtAge(age)}` : 'loading');
      clear(banner);
      if (S.err) banner.append(h('div.banner.bad', { style: { marginBottom: '12px' } }, h('div', h('b', 'The fleet collector does not answer. '), `${S.err}. The numbers below are the last ones received${f ? ' (' + fmtTime(f.generated_at || f.t) + ')' : ''}.`)));
      const flagged = f && f.fresh && (f.fresh.flagged || []).filter((k) => HOSTS.map((x) => 'host:' + x.toLowerCase()).includes(k));
      if (flagged && flagged.length) banner.append(h('div.banner', { style: { marginBottom: '12px' } }, h('div', h('b', 'Stale sources: '), flagged.join(', '))));
    }
    function hostTab(el) {
      const x = S.fleet && S.fleet.hosts.find((y) => y.label === S.hostSel);
      if (!x) { el.append(h('section.sec', h('p.note', { style: { margin: 0 } }, 'Click a host card to filter the jobs to it and see its details here.'))); return; }
      const p = probeOf(x.label), a = p && p.admit, jh = (S.jobs && S.jobs.hosts && S.jobs.hosts[x.label]) || {};
      el.append(h('section.sec', h('h1', x.label), h('p.sub', x.kind || ''), h('dl.kv', h('dt', 'state'), h('dd', x.state + (x.error ? ' · ' + x.error : '')), h('dt', 'alias'), h('dd', h('span.mono', x.alias || '')), h('dt', 'load'), h('dd', `${fmt(x.load, 1)} on ${(x.cores || []).length} threads`),
        h('dt', 'RAM'), h('dd', `${fmt(x.mem_used, 1)} of ${fmt(x.mem_total, 1)} GB used`), h('dt', 'jobs'), h('dd', `${fmt((jh.other || 0) + (jh.loop || 0))} running, ${fmt(jh.waiters || 0)} waiting, ${fmt(jh.held || 0)} held, ${gb(jh.jobs_mem)} GB in jobs`), h('dt', 'containers'), h('dd', fmt(x.docker || 0)), (x.gpu || []).length ? [h('dt', 'GPU'), h('dd', JSON.stringify(x.gpu).slice(0, 200))] : null)),
      h('section.sec', h('h3', 'RAM admission (ot-run)'), a ? h('dl.kv', Object.entries({ 'admit now': a.admit_gb + ' GB', 'free': a.free_gb + ' GB', 'available': a.avail_gb + ' GB', 'used': a.used_gb + ' GB', 'reserved': a.reserved_gb + ' GB', 'floor': a.floor_gb + ' GB', 'headroom': a.headroom_gb + ' GB', 'running': a.running, 'waiting': `${a.waiting} (${a.waiting_gb} GB)` }).map(([k, v]) => [h('dt', k), h('dd', String(v))]), h('dt', 'probed'), h('dd', fmtAge(S.now - p.t))) : h('p.note', { style: { margin: 0 } }, p ? (p.error || 'no admission data') : 'This host is not probed from the service host.')),
      h('section.sec', h('h3', 'Disks'), p && p.disks.length ? h('dl.kv', p.disks.map((d) => [h('dt', h('span.mono', d.mount)), h('dd', `${fmt(d.avail_gb)} of ${fmt(d.size_gb)} GB free · ${d.pct} % used${d.same_as ? ' (same file system)' : ''}`)])) : h('p.note', { style: { margin: 0 } }, 'No disk data for this host.')));
    }
    function jobTab(el) {
      const r = S.job;
      if (!r) { el.append(h('section.sec', h('p.note', { style: { margin: 0 } }, 'Click a row of the job table to see the whole job here.'))); return; }
      el.append(h('section.sec', { dataset: { testid: 'fleet-job-card' } }, h('h1.mono', r.item || r.job || r.name), h('p.sub', `${r.kind} on ${r.host}`),
        h('dl.kv', h('dt', 'die'), h('dd', r.die ? dieShort(r.die) : 'unknown'), h('dt', 'item'), h('dd', r.item || 'unknown'), h('dt', 'stage'), h('dd', r.stage || 'unknown'), h('dt', 'attempt'), h('dd', r.attempt ?? '–'), h('dt', 'started'), h('dd', r.start ? `${fmtTime(r.start)} (${dur(elapsed(r))})` : '–'),
          h('dt', 'RAM'), h('dd', r.kind === 'waiter' ? `asks for ${gb(r.req)} GB` : `${gb(r.mem)} GB now · peak ${gb(r.peak)} · limit ${gb(r.max)}`), h('dt', 'CPU'), h('dd', r.cpu == null ? '–' : fmt(r.cpu, 2)), h('dt', 'unit'), h('dd', h('span.mono', r.unit || '–')), h('dt', 'directory'), h('dd', h('span.mono', r.cwd || '–'))),
        r.item ? h('div', { style: { marginTop: '10px' } }, h('a.btn.sm', { href: '/element?name=' + encodeURIComponent(r.item.replace(/__pv[0-9a-f]+$/, '')), dataset: { testid: 'fleet-job-open' } }, 'Open this design')) : null),
      h('section.sec', h('h3', 'Command'), h('pre.cmd', r.detail || r.name || '')));
    }
    function verdictTab(el) {
      const V = (S.verdicts && S.verdicts.verdicts) || [];
      el.append(h('section.sec', h('h3', 'Verdict feed', h('span.n', `${V.length} newest`)), V.length ? h('div.list', V.slice(0, 80).map((v) => h('div.row', { style: { cursor: 'default', alignItems: 'baseline' }, title: v.detail || v.why || '' }, h('span.' + (/PASS|SIGNED|READY|OK/i.test(v.status) ? 'pos' : /FAIL|BAD/i.test(v.status) ? 'neg' : 'muted'), { style: { flex: '0 0 74px', fontSize: 'var(--fs-xs)', fontWeight: 600 } }, String(v.status).slice(0, 12)), h('span.nm', v.block || v.name), h('small', fmtAge(S.now - v.t))))) : h('p.note', { style: { margin: 0 } }, S.verdicts ? 'No verdict in the feed.' : 'Loading…')));
    }
    ctx.inspector.setTabs([{ id: 'host', label: 'Host', render: hostTab }, { id: 'job', label: 'Job', render: jobTab }, { id: 'verdicts', label: 'Verdicts', render: verdictTab }]);

    const visible = () => !S.dead && document.visibilityState !== 'hidden';
    async function pollFleet() { if (!visible()) return; try { S.fleet = await api.fleet('fleet'); S.err = null; } catch (e) { S.err = e.detail || e.message; } S.now = Date.now() / 1000; if (S.dead) return; paintLive(); paintTotals(); paintHosts(); paintLoop(); if (ctx.inspector.current() === 'host') ctx.inspector.show('host'); }
    async function pollJobs() { if (!visible()) return; try { S.jobs = await api.fleet('fleetjobs'); S.jobsErr = null; } catch (e) { S.jobsErr = e.detail || e.message; } try { S.loop = await api.fleet('jobs'); } catch (e) { /* the loop table stays */ } S.now = Date.now() / 1000; if (S.dead) return; paintTotals(); paintHosts(); paintJobs(); paintLoop(); }
    async function pollProbe() { if (!visible()) return; try { S.probe = await api.get('fleet/probe', { fresh: true }); } catch (e) { /* cards say so */ } if (!S.dead) paintHosts(); }
    async function pollVerdicts() { if (!visible()) return; try { S.verdicts = await api.fleet('verdicts'); } catch (e) { /* tab says so */ } if (!S.dead && ctx.inspector.current() === 'verdicts') ctx.inspector.show('verdicts'); }
    S.timers.push(setInterval(pollFleet, 5000), setInterval(pollJobs, 20000), setInterval(pollProbe, 30000), setInterval(pollVerdicts, 60000));
    paintLive();
    await pollFleet(); pollJobs(); pollProbe().then(() => setTimeout(pollProbe, 6000)); pollVerdicts();
    return {
      update(st) {
        S.hostSel = st.params.host || null; S.kind = ['run', 'wait'].includes(st.params.kind) ? st.params.kind : 'all';
        ctx.setScope('build hosts and jobs · polled every 5 s'); paintHosts(); paintJobs();
      },
      destroy() { S.dead = true; S.timers.forEach(clearInterval); },
    };
  },
};

/* Flow / version state of the elements (flow_state.py -> /api/explorer/flow): a badge per element ("closed · ref_tile M5
   (current)", "closed · legacy flow", "re-route in flight (M5)", ...), the M5 re-route comparison (tools/ref_tile/
   reroute_batch.py compare), and a per-target progress tracker of the die-used elements on the current flow.
   Superseded / fallback rows are hidden from the default counts; the toggle (remembered per viewer) shows them. */
(function(){
  const SAFE = new URLSearchParams(location.search).get('safe') === '1';
  const COL = {closed_m5: '#34d399', inflight: '#38bdf8', closed_m6: '#fbbf24', closed_legacy: '#a78bfa', open: '#fb7185',
               superseded: '#64748b', fallback: '#475569'};
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const css = `.fvf{font:12px/1.45 var(--sans,system-ui,sans-serif);color:var(--ink,#e8eefc)}
.fvf h3{font:700 10.5px var(--mono,ui-monospace,monospace);letter-spacing:.14em;text-transform:uppercase;color:var(--faint,#7c89aa);margin:0 0 6px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.fvf .t{margin:0 0 9px}.fvf .tn{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}.fvf .tn b{font-weight:600}
.fvf .tn span{color:var(--dim,#8a97b8);font:11.5px var(--mono,ui-monospace,monospace)}.fvf .tn span em{font-style:normal;color:#34d399}
.fvf .bar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--line,#1b2540);margin-top:3px}
.fvf .bar i{display:block;height:100%}.fvf .t.on .tn b{color:var(--accent,#5ee7ff)}
.fvf .lg{display:flex;flex-wrap:wrap;gap:4px 10px;margin:4px 0 6px;color:var(--dim,#8a97b8);font-size:11px}
.fvf .lg i,.fvf-b i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px;vertical-align:0}
.fvf label{display:inline-flex;align-items:center;gap:6px;color:var(--dim,#8a97b8);font-size:11.5px;cursor:pointer;min-height:24px}
.fvf-b{display:inline-flex;align-items:center;border:1px solid var(--line,#1b2540);border-radius:999px;padding:2px 9px;font:600 11.5px var(--sans,system-ui,sans-serif);color:var(--ink,#e8eefc);white-space:normal;max-width:100%}
.fvf-c{margin:6px 0 2px;color:var(--dim,#8a97b8);font-size:11.5px;overflow-wrap:anywhere}
.fvf table{border-collapse:collapse;width:100%;font:11.5px var(--mono,ui-monospace,monospace);margin-top:4px}
.fvf td,.fvf th{padding:2px 4px;text-align:right;border-bottom:1px solid var(--line,#1b2540)}.fvf td:first-child,.fvf th:first-child{text-align:left}
.fvf th{color:var(--faint,#7c89aa);font-weight:600}.fvf .bad{color:#fb7185}.fvf .good{color:#34d399}
.fvf-box{padding:10px 12px;border-bottom:1px solid var(--line,#1b2540)}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  let D = null, P = null; const subs = [];
  const hid = () => { try { return localStorage.getItem('fvflow.hidden') === '1'; } catch (e) { return false; } };
  const setHid = v => { try { localStorage.setItem('fvflow.hidden', v ? '1' : '0'); } catch (e) {} };
  function load(){
    if (P) return P;
    P = fetch('/api/explorer/flow' + (SAFE ? '?safe=1' : ''), {cache: 'no-store'}).then(r => r.ok ? r.json() : null)
      .then(j => { D = j; subs.forEach(f => { try { f(); } catch (e) {} }); return j; }).catch(() => null);
    return P;
  }
  const F = () => (D && D.flow) || {};
  const label = k => (F().labels || {})[k] || k;
  function get(el){ return el && D && D.elements ? D.elements[el] || null : null; }
  function badge(el){
    const e = get(el); if (!e) return '';
    return `<span class="fvf-b" title="flow / version state${e.detail ? ': ' + esc(e.detail) : ''}"><i style="background:${COL[e.flow] || '#888'}"></i>${esc(e.label)}</span>`;
  }
  const num = (v, d) => v == null ? '—' : (typeof v === 'number' ? (d ? (v >= 0 ? '+' : '') + v.toFixed(1) : String(v)) : esc(v));
  function compare(el){
    const e = get(el), m = e && e.m5; if (!m) return '';
    const SN = {kit: 'kit generated, pre-route gate pending', gate_fail: 'pre-route gate failed', skip: 'not re-routed',
                error: 'kit generation error', submitted: 'submitted to the closure loop'};
    let h = `<div class="fvf-c">M5 re-route: <b>${esc(SN[m.state] || m.state)}</b>${m.job ? ' · ' + esc(m.job) : ''}${m.reason && m.state !== 'submitted' ? ' · ' + esc(String(m.reason).slice(0, 160)) : ''}</div>`;
    const c = m.compare;
    if (c && c.m5){
      const a = c.m5, b = c.prev || {};
      const row = (n, k, s) => `<tr><td>${n}</td><td>${num(a[k], s)}</td><td>${num(b[k], s)}</td></tr>`;
      h += `<table><thead><tr><th></th><th>M5</th><th>previous</th></tr></thead><tbody>${row('TT setup ps', 'tt_ps', 1)}${row('FF hold ps', 'ff_ps', 1)}${row('GRT overflow', 'grt_overflow')}${row('DRT iterations', 'drt_iters')}${row('route min', 'route_min')}</tbody></table>`;
      h += (c.flags && c.flags.length) ? `<div class="fvf-c bad">WORSE: ${esc(c.flags.join('; '))}${c.grant_proposed ? ' · M6 grant proposed (' + esc(c.grant_proposed) + ')' : ''}</div>` : `<div class="fvf-c good">not worse than the previous closure</div>`;
    }
    return h;
  }
  function tracker(focus){
    const s = F().summary || {}, order = F().order || Object.keys(COL), hidden = new Set(F().hidden || ['superseded', 'fallback']);
    const show = hid(), keys = order.filter(k => show || !hidden.has(k));
    const T = Object.keys(s).filter(t => t !== 'Other');
    if (!T.length) return '<div class="fvf-c">Flow state not available yet.</div>';
    let h = `<h3><span>Flow progress · die-used elements</span></h3>`;
    for (const t of T){
      const c = s[t].die_used, tot = keys.reduce((a, k) => a + (c[k] || 0), 0), cur = c.closed_m5 || 0;
      h += `<div class="t${focus === t ? ' on' : ''}"><div class="tn"><b>${esc(t)}</b><span><em>${cur}</em> of ${tot} on the current flow${c.inflight ? ' · ' + c.inflight + ' in flight' : ''}</span></div>
        <div class="bar" role="img" aria-label="${esc(t)}: ${keys.map(k => (c[k] || 0) + ' ' + label(k)).join(', ')}">${keys.filter(k => c[k]).map(k => `<i style="width:${100 * c[k] / Math.max(1, tot)}%;background:${COL[k]}" title="${esc(label(k))}: ${c[k]}"></i>`).join('')}</div></div>`;
    }
    const all = {}; for (const t of T) for (const k of keys) all[k] = (all[k] || 0) + (s[t].die_used[k] || 0);
    h += `<div class="lg">${keys.map(k => `<span><i style="background:${COL[k]}"></i>${esc(label(k))} ${all[k] || 0}</span>`).join('')}</div>`;
    h += `<label><input type="checkbox" class="fvf-tog" ${show ? 'checked' : ''}> Show superseded / fallback</label>`;
    return h;
  }
  function mount(id, opts){
    opts = opts || {};
    const draw = () => {
      const el = document.getElementById(id); if (!el) return;
      const e = get(opts.element);
      let h = '';
      if (e) h += `<h3><span>Flow / version</span></h3><div>${badge(opts.element)}</div>${e.detail ? `<div class="fvf-c">${esc(e.detail)}</div>` : ''}${compare(opts.element)}<div style="height:10px"></div>`;
      h += tracker(e && e.target);
      el.classList.add('fvf');
      el.innerHTML = h;
      const tg = el.querySelector('.fvf-tog');
      if (tg) tg.onchange = () => { setHid(tg.checked); subs.forEach(f => { try { f(); } catch (x) {} }); };
    };
    subs.push(draw); draw(); load();
  }
  window.FVFlow = {load, get, badge, compare, tracker, mount, on: f => subs.push(f), label};
  load();
})();

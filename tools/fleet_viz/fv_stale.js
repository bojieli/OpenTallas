/* fv_stale.js: shared staleness guard for the fleet, explorer and coverage pages.
 *
 * Every API payload carries generated_at, sent_at and fresh = {sources: {key: {label, t, age, limit, ok, error}}, flagged: [keys]}.
 * Server times are mapped onto this browser's clock through sent_at (offset = receive time - sent_at), so a skewed
 * clock on either side cannot hide old data. A failed or timed-out fetch, a payload older than its limit, or a flagged
 * source raises an issue; any open issue shows a red banner ("Data stale since HH:MM:SS: <reason>"), affected panels are
 * dimmed and hatched, and per-panel age stamps ("updated 12s ago") turn amber, then red. Issues clear on recovery.
 */
(function () {
  'use strict';
  const css = `
#fvStale{position:sticky;top:0;z-index:1000;display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 16px;
  background:repeating-linear-gradient(135deg,#b3122e 0 14px,#c8173a 14px 28px);color:#fff;font:700 14px/1.35 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  box-shadow:0 6px 30px #ff1f4b66;border-bottom:2px solid #ff8a9b;overflow-wrap:anywhere}
#fvStale b{font-weight:800;letter-spacing:.04em}
#fvStale .fvr{font-weight:600;flex:1 1 280px;min-width:0}
#fvStale small{font-weight:500;opacity:.85}
#fvStale .fvm{font:700 12px ui-monospace,Menlo,monospace;color:#fff;background:#0004;border:1px solid #fff8;border-radius:999px;padding:3px 10px;cursor:pointer}
#fvStale .fvl{flex-basis:100%;margin:2px 0 0;padding-left:18px;font-weight:500;font-size:12px;max-height:40vh;overflow:auto}
@media (max-width:640px){#fvStale{font-size:12.5px;padding:8px 12px;gap:6px 8px}#fvStale .fvn{display:none}}
.fv-stale{position:relative!important;border-color:#ff5d73aa!important}
.fv-stale>*{opacity:.38;filter:grayscale(.85)}
.fv-stale::after{content:attr(data-fv-why);position:absolute;inset:0;border-radius:inherit;pointer-events:none;z-index:5;
  background:repeating-linear-gradient(135deg,rgba(255,93,115,.20) 0 7px,transparent 7px 16px);
  display:flex;align-items:flex-end;justify-content:flex-end;padding:6px 10px;color:#ff8a9b;font:800 11px ui-monospace,Menlo,monospace;letter-spacing:.1em}
.fv-age{font:600 11px ui-monospace,SFMono-Regular,Menlo,monospace;color:#8a97b8;white-space:nowrap;text-transform:none;letter-spacing:0}
.fv-age.amber{color:#fbbf24}
.fv-age.red{color:#ff5d73;font-weight:800}
`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  const now = () => Date.now() / 1000;
  const hms = t => new Date(t * 1000).toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false});
  const span = s => s < 90 ? Math.round(s) + 's' : s < 5400 ? Math.round(s / 60) + 'm' : s < 172800 ? (s / 3600).toFixed(1) + 'h' : Math.round(s / 86400) + 'd';
  const issues = new Map();   // key -> {reason, since (client epoch)}
  const stamps = [];          // {el, get, warn, bad, prefix}
  const panels = new Map();   // name -> {els: [elements], keys: Set(issue keys that dim them)}
  let banner = null, offset = 0;

  function ensureBanner() {
    if (banner) return banner;
    banner = document.createElement('div'); banner.id = 'fvStale'; banner.setAttribute('role', 'alert'); banner.hidden = true;
    banner.addEventListener('click', e => { if (e.target.closest('.fvm')) { open = !open; render(); } });
    document.body.insertBefore(banner, document.body.firstChild);
    return banner;
  }
  const short = r => r.length > 110 ? r.slice(0, 107) + '…' : r;
  let open = false;
  function render() {
    const b = ensureBanner();
    if (!issues.size) { if (!b.hidden) b.hidden = true; refreshPanels(); return; }
    // the live feed, then connection-level issues (keys without a scope, e.g. 'feed', 'jobs-fetch') first, then flagged sources, oldest first
    const list = [...issues.entries()].sort(([ka, x], [kb, y]) => ((kb === 'feed') - (ka === 'feed')) || (ka.includes(':') - kb.includes(':')) || x.since - y.since).map(e => e[1]);
    const since = Math.min(...list.map(i => i.since)), more = list.length - 1;
    const txt = `<b>DATA STALE</b><span class="fvr">since ${hms(since)}: ${esc(short(list[0].reason))}</span>` +
      (more ? `<button type="button" class="fvm" aria-expanded="${open}">${open ? 'hide' : '+' + more + ' more'}</button>` : '') +
      `<small class="fvn">numbers marked STALE are frozen at their last good time · clears on recovery</small>` +
      (more && open ? `<ul class="fvl">${list.map(i => `<li>${esc(i.reason)}</li>`).join('')}</ul>` : '');
    if (b._h !== txt) { b._h = txt; b.innerHTML = txt; }
    b.title = list.map(i => i.reason).join('\n');
    if (b.hidden) b.hidden = false;
    refreshPanels();
  }
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'})[c]);
  function refreshPanels() {
    for (const [, p] of panels) {
      const hit = [...p.keys].map(k => issues.get(k) || [...issues.entries()].find(([ik]) => k.endsWith('*') && ik.startsWith(k.slice(0, -1)))?.[1]).find(Boolean);
      for (const el of p.els) {
        if (!el) continue;
        el.classList.toggle('fv-stale', !!hit);
        if (hit) el.setAttribute('data-fv-why', 'STALE since ' + hms(hit.since)); else el.removeAttribute('data-fv-why');
      }
    }
  }

  const FV = {
    hms, span,
    /** raise (or keep) an issue; since defaults to the first time it was raised */
    issue(key, reason, since) {
      const o = issues.get(key);
      const s = since != null ? since : o ? o.since : now();
      if (!o || o.reason !== reason || o.since !== s) { issues.set(key, {reason, since: s}); render(); }
    },
    clear(key) { if (issues.delete(key)) render(); },
    clearPrefix(p, keep) { let ch = false; for (const k of [...issues.keys()]) if (k.startsWith(p) && !(keep && keep.has(k))) { issues.delete(k); ch = true; } if (ch) render(); },
    has(key) { return issues.has(key); },
    active() { return issues.size > 0; },
    /** server epoch -> client epoch, through the latest payload's sent_at */
    toClient(t) { return t == null ? null : t + offset; },
    /** dim/hatch els while any of keys (exact, or 'prefix*') has an open issue */
    panel(name, els, keys) { panels.set(name, {els: [].concat(els), keys: new Set(keys)}); refreshPanels(); },
    /** age stamp: get() -> client epoch of the data shown (null = never); amber after warn s, red after bad s */
    stamp(el, get, warn, bad, prefix) { if (el) { stamps.push({el, get, warn, bad, prefix: prefix == null ? 'updated ' : prefix}); tickStamps(); } },
    /** read a payload: clock offset, and flagged sources (only those matching want, a list of key prefixes) */
    payload(d, want, scope) {
      const recv = now();
      if (d && d.sent_at) offset = recv - d.sent_at;
      const gen = d && d.generated_at ? d.generated_at + offset : recv;
      const f = d && d.fresh, open = new Set();
      if (f && f.sources) {
        for (const [k, s] of Object.entries(f.sources)) {
          if (s.ok || (want && !want.some(w => k.startsWith(w)))) continue;
          if (s.pending) continue;
          const key = (scope || 'src') + ':' + k; open.add(key);
          const since = s.t != null ? s.t + offset : null;
          FV.issue(key, `${s.label || k}: ${s.error || 'stale'}` + (s.t != null ? ` (last good ${hms(s.t + offset)})` : ''), since);
        }
      }
      FV.clearPrefix((scope || 'src') + ':', open);
      return gen;
    },
    /** fetch JSON with a timeout; rejects on network error, timeout or HTTP error */
    async getJSON(url, ms, opts) {
      const ac = new AbortController(), tm = setTimeout(() => ac.abort(), ms || 10000);
      try {
        const r = await fetch(url, Object.assign({cache: 'no-store', signal: ac.signal}, opts || {}));
        if (!r.ok) { let m = ''; try { const j = await r.json(); m = j.error || (j.warming ? 'server warming up' : ''); } catch (e) {} throw new Error('HTTP ' + r.status + (m ? ' ' + m : '')); }
        return await r.json();
      } catch (e) {
        if (e.name === 'AbortError') throw new Error('timed out after ' + Math.round((ms || 10000) / 1000) + 's');
        if (e instanceof TypeError) throw new Error('network error (server unreachable)');
        throw e;
      } finally { clearTimeout(tm); }
    },
  };
  function tickStamps() {
    const n = now();
    for (const s of stamps) {
      const t = s.get(), a = t == null ? null : Math.max(0, n - t);
      const txt = a == null ? 'no data yet' : s.prefix + span(a) + ' ago';
      if (s.el.textContent !== txt) s.el.textContent = txt;
      const red = a == null ? false : a > s.bad, amber = !red && a != null && a > s.warn;
      s.el.classList.toggle('red', red); s.el.classList.toggle('amber', amber);
      s.el.title = t == null ? '' : 'data as of ' + hms(t);
    }
  }
  setInterval(tickStamps, 1000);
  window.FVStale = FV;
})();

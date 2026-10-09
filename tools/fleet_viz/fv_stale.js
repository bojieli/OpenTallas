/* fv_stale.js: shared staleness indicator for the fleet, explorer and coverage pages.
 *
 * Every API payload carries generated_at, sent_at and fresh = {sources: {key: {label, t, age, limit, ok, error}}, flagged: [keys]}.
 * Server times are mapped onto this browser's clock through sent_at (offset = receive time - sent_at).
 *
 * Owner rule (10-09): displayed data is NEVER replaced, blanked, dimmed or hatched when a fetch fails or a source goes stale;
 * the last good values stay on screen. The only signal is ONE small label beside the page's live indicator:
 * "stale · last sync HH:MM:SS (Ns ago)", reason in its tooltip. Hysteresis so it does not flicker: a failure (fetch error,
 * flagged source) shows only after 2 consecutive occurrences; an age condition is raised by the page only past ~2x its poll;
 * any success clears it at once.
 */
(function () {
  'use strict';
  const css = `
.fv-tag{display:inline-flex;align-items:center;gap:6px;font:600 11.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#fbbf24;
  border:1px solid #fbbf2466;background:#fbbf2414;border-radius:999px;padding:4px 9px;white-space:nowrap;cursor:help}
.fv-tag::before{content:'';width:6px;height:6px;border-radius:50%;background:#fbbf24}
.fv-tag[hidden]{display:none!important}
`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  const now = () => Date.now() / 1000;
  const hms = t => new Date(t * 1000).toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false});
  const span = s => s < 90 ? Math.round(s) + 's' : s < 5400 ? Math.round(s / 60) + 'm' : s < 172800 ? (s / 3600).toFixed(1) + 'h' : Math.round(s / 86400) + 'd';
  const issues = new Map();   // active: key -> {reason, since (client epoch of the last good data, or null)}
  const fails = new Map();    // key -> consecutive failure count
  let tag = null, lastSync = null, offset = 0;

  function render() {
    if (!tag) return;
    if (!issues.size) { if (!tag.hidden) tag.hidden = true; return; }
    const list = [...issues.values()];
    const ts = list.map(i => i.since).filter(t => t != null);
    const t = lastSync != null ? lastSync : ts.length ? Math.min(...ts) : null;   // the page's last good sync of its main feed
    const txt = t != null ? `stale · last sync ${hms(t)} (${span(Math.max(0, now() - t))} ago)` : 'stale · no sync yet';
    if (tag.textContent !== txt) tag.textContent = txt;
    const tip = list.map(i => i.reason).join('\n');
    if (tag.title !== tip) tag.title = tip;
    if (tag.hidden) tag.hidden = false;
  }

  const FV = {
    hms, span,
    /** place the label right after el (the page's live indicator / top-bar end) */
    anchor(el) {
      if (!el || tag) return;
      tag = document.createElement('span'); tag.className = 'fv-tag'; tag.hidden = true; tag.setAttribute('role', 'status');
      el.insertAdjacentElement('afterend', tag); render();
    },
    /** a successful sync: remember when */
    synced(t) { lastSync = t == null ? now() : t; },
    /** raise a condition that is already past its own threshold (e.g. data age > 2x poll) */
    issue(key, reason, since) {
      const o = issues.get(key);
      if (!o || o.reason !== reason || o.since !== since) { issues.set(key, {reason, since: since == null ? (o ? o.since : lastSync) : since}); render(); }
    },
    clear(key) { fails.delete(key); if (issues.delete(key)) render(); },
    has(key) { return issues.has(key); },
    /** one failure; the label shows only from the 2nd consecutive failure of the same key */
    fail(key, reason, since) {
      const n = (fails.get(key) || 0) + 1; fails.set(key, n);
      if (n >= 2) FV.issue(key, reason, since);
    },
    ok(key) { FV.clear(key); },
    /** server epoch -> client epoch, through the latest payload's sent_at */
    toClient(t) { return t == null ? null : t + offset; },
    /** read a payload: clock offset, and flagged sources (only those matching want, a list of key prefixes) */
    payload(d, want, scope) {
      const recv = now();
      if (d && d.sent_at) offset = recv - d.sent_at;
      const gen = d && d.generated_at ? d.generated_at + offset : recv;
      const f = d && d.fresh, sc = (scope || 'src') + ':', bad = new Set();
      if (f && f.sources) {
        for (const [k, s] of Object.entries(f.sources)) {
          if (s.ok || s.pending || (want && !want.some(w => k.startsWith(w)))) continue;
          bad.add(sc + k);
          FV.fail(sc + k, `${s.label || k}: ${s.error || 'stale'}` + (s.t != null ? ` (last good ${hms(s.t + offset)})` : ''), s.t != null ? s.t + offset : null);
        }
      }
      for (const k of new Set([...fails.keys(), ...issues.keys()])) if (k.startsWith(sc) && !bad.has(k)) FV.clear(k);
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
  setInterval(render, 1000);   // the "(Ns ago)" count only; show/hide changes only on issue changes
  window.FVStale = FV;
})();

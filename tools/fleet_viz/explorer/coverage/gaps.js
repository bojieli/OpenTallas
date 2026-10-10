// Coverage gap classes: colours, short tags and the live feed (shared by /explorer/coverage and the token-path views).
export const GAPS = {
  MISSING_HW: { tag: 'MH', label: 'missing HW (no RTL)', color: '#ff4fa3' },
  NOT_ON_DIE: { tag: 'OD', label: 'not on a die (no master)', color: '#c86bfa' },
  NOT_CLOSED: { tag: 'NC', label: 'not closed', color: '#8a97b8' },
  NOT_EXACT: { tag: 'NE', label: 'no exact bench', color: '#ffc857' },
  NOT_PRICED: { tag: 'NP', label: 'not in a token path', color: '#3987e5' },
  MODELLED_ONLY: { tag: 'MO', label: 'modelled / vendor only', color: '#d95926' },
  UNENUMERATED: { tag: 'UE', label: 'not enumerated in the ledger', color: '#e8eefc' },
};
export const UNCOVERED = new Set(['MISSING_HW', 'NOT_ON_DIE']);
export const COL = { uncovered: '#ff4fa3', gap: '#ffc857', ok: '#7ee08a' };

/** Shared overlay state for the token views: which gap classes light a node (NOT_CLOSED off by default: it is everywhere). */
export const COV = {
  on: true,
  classes: new Set(['MISSING_HW', 'NOT_ON_DIE', 'NOT_EXACT', 'NOT_PRICED', 'MODELLED_ONLY', 'UNENUMERATED']),
};
try {
  const s = JSON.parse(localStorage.getItem('tp-cov') || 'null');
  if (s) { COV.on = !!s.on; if (Array.isArray(s.classes)) COV.classes = new Set(s.classes); }
} catch (e) { /* storage unavailable: defaults */ }
export function saveCov() { try { localStorage.setItem('tp-cov', JSON.stringify({ on: COV.on, classes: [...COV.classes] })); } catch (e) { /* ignore */ } }

/** classes of a node's rows (n.cov from attachCoverage) that the overlay currently shows */
export function covClasses(n) {
  if (!COV.on || !n || !n.cov) return [];
  const s = new Set();
  for (const r of n.cov.rows) for (const g of r.gaps) if (COV.classes.has(g.cls)) s.add(g.cls);
  return [...s];
}
/** 'uncovered' | 'gap' | null */
export function covLevel(n) {
  const c = covClasses(n);
  if (!c.length) return null;
  return c.some((k) => UNCOVERED.has(k)) ? 'uncovered' : 'gap';
}

/** fetch /api/coverage/token for a design and set n.cov = {rows:[{fid, function, owner, gaps}]} on every operator */
export async function attachCoverage(data, design) {
  const r = await fetch('/api/coverage/token?design=' + encodeURIComponent(design));
  if (!r.ok) throw new Error('coverage ' + r.status);
  const c = await r.json();
  if (c.error) throw new Error(c.error);
  for (const n of data.nodes) {
    const fids = c.nodes[n.id] || [];
    n.cov = { target: c.target, rows: fids.map((f) => ({ fid: f, ...(c.rows[f] || { function: f, gaps: [] }) })) };
  }
  data._cov = { v: c.v, target: c.target, design };
  return c;
}
export async function coverageVersion() {
  const r = await fetch('/api/coverage/version');
  if (!r.ok) return null;
  return (await r.json()).v;
}

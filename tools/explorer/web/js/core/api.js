// /api/v1 client: one fetch path, promise cache per URL, plain errors.
const BASE = '/api/v1/';
const cache = new Map();

export class ApiError extends Error {
  constructor(status, msg, detail, url) { super(msg); this.status = status; this.detail = detail; this.url = url; }
}
async function fetchJSON(url) {
  let r;
  try { r = await fetch(url, { headers: { Accept: 'application/json' } }); } catch (e) { throw new ApiError(0, 'The server did not answer', String(e), url); }
  if (!r.ok) {
    let o = null; try { o = await r.json(); } catch (e) { /* not JSON */ }
    throw new ApiError(r.status, (o && o.error) || ('HTTP ' + r.status), o && o.detail, url);
  }
  return r.json();
}
/** cached GET; pass {fresh: true} to bypass */
export function get(path, opts = {}) {
  const url = BASE + path;
  if (opts.fresh) cache.delete(url);
  if (!cache.has(url)) cache.set(url, fetchJSON(url).catch((e) => { cache.delete(url); throw e; }));
  return cache.get(url);
}
const e = encodeURIComponent;
export const api = {
  get, base: BASE,
  meta: (fresh) => get('meta', { fresh }),
  dies: () => get('dies'),
  die: (d) => get('die/' + e(d)),
  node: (id) => get('node/' + e(id)),
  compose: (d) => get('compose/' + e(d)),
  closure: (d) => get('closure/' + e(d)),
  resolve: (names) => fetchJSON(BASE + 'resolve?q=' + names.map(e).join(',')),
  search: (q, die) => fetchJSON(BASE + 'search?q=' + e(q) + (die ? '&die=' + e(die) : '')),
  names: (node, kind, ids) => fetchJSON(BASE + 'layout/' + e(node) + '/names?k=' + kind + '&ids=' + ids.join(',')),
  packSearch: (node, q, kind = 'all') => fetchJSON(BASE + 'layout/' + e(node) + '/search?q=' + e(q) + '&k=' + kind),
  storeObject: (hash) => BASE + 'store/objects/' + hash.slice(0, 2) + '/' + hash + '.br',
  storeManifest: (node, job) => BASE + 'store/elements/' + e(node) + '/' + e(job) + '.json',
  storeIndex: (node) => BASE + 'store/elements/' + e(node) + '/index.json',
  dataflowIndex: () => get('dataflow/index'),
  dataflowRecord: (id) => get('dataflow/record/' + e(id)),
  tokenIndex: () => get('token/index'),
  tokenRecord: (id) => get('token/record/' + e(id)),
  tokenMap: (design) => get('token/map/' + e(design)),
  coverage: () => get('coverage'),
  clear: () => cache.clear(),
};

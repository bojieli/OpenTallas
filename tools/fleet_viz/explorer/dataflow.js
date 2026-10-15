// Source-backed connection metadata shared by both explorers. Width is never a rate.
const number = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null;
const point = p => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite) ? p : null;
export function normalizeDataflow(payload = {}) {
  const raw = payload.edges || payload.connections || [];
  const edges = raw.map((e, i) => ({
    ...e, id: String(e.id ?? `connection-${i}`), label: e.label || e.name || e.id || `Connection ${i + 1}`,
    src: e.src ?? null, dst: e.dst ?? null,
    direction: e.direction || (e.directed === true ? 'forward' : 'unknown'),
    width_bits: Number.isInteger(e.width_bits) && e.width_bits > 0 ? e.width_bits : null, required_bps: number(e.required_bps), capacity_bps: number(e.capacity_bps),
    bytes: number(e.bytes), start: number(e.start), end: number(e.end),
    from: point(e.from), to: point(e.to), source: typeof e.source === 'string' && payload.provenance ? { kind: e.source, provenance: payload.provenance } : e.source || payload.provenance || null,
    endpoints: (e.endpoints || []).map(p => ({ ...p, point: point(p.point) })),
  }));
  return { ...payload, edges, coverage: { ...payload.coverage, total: edges.length,
    widths_known: edges.filter(e => e.width_bits !== null).length,
    rates_known: edges.filter(e => e.required_bps !== null).length,
    token_mapped: edges.filter(e => e.src_node && e.dst_node).length } };
}
export function formatRate(v) {
  if (number(v) === null) return 'unknown';
  for (const [u, n] of [['Tb/s', 1e12], ['Gb/s', 1e9], ['Mb/s', 1e6], ['kb/s', 1e3]]) if (v >= n) return `${(v / n).toLocaleString(undefined, { maximumFractionDigits: 2 })} ${u}`;
  return `${v} b/s`;
}
export function connectionLabel(e) { return e.width_bits === null ? 'width unknown' : `${e.width_bits.toLocaleString()} bits`; }
export function connectionDescription(e) {
  return `${e.label || e.id}: ${connectionLabel(e)}; required ${formatRate(e.required_bps)}; capacity ${formatRate(e.capacity_bps)}; direction ${e.direction || 'unknown'}; ${e.bytes == null ? 'transfer size unknown' : `${e.bytes} bytes/transfer`}`;
}
export function sourceText(source) { return source == null ? 'unknown' : typeof source === 'string' ? source : JSON.stringify(source); }
// Node mapping must be explicit. Instance proximity and schedule dependencies do not establish it.
export function filterConnections(edges, { mode = 'all', selected = null, activeNodes = [] } = {}) {
  const ids = new Set(activeNodes);
  return edges.filter(e => mode === 'all' || (mode === 'critical' && e.critical === true) ||
    (mode === 'selected' && selected && (e.src_node === selected || e.dst_node === selected)) ||
    (mode === 'current' && (ids.has(e.src_node) || ids.has(e.dst_node))));
}
// Pin coordinates where available, otherwise explicit instance-centre schematics.
export function connectionSegments(edge, instances = []) {
  const byName = instances instanceof Map ? instances : new Map(instances.map(i => [i.name, i]));
  const locate = (p, name) => { if (p) return p; const i = byName.get(name); return i ? [i.x + i.w / 2, i.y + i.h / 2] : null; };
  if (edge.endpoints.length > 2) {
    const ps = edge.endpoints.map(p => locate(p.point, p.instance)).filter(Boolean);
    return ps.slice(1).map(p => ({ from: ps[0], to: p, directed: false, pin_located: false }));
  }
  const a = locate(edge.from, edge.src), b = locate(edge.to, edge.dst);
  if (a && b) return [{ from: a, to: b, directed: edge.direction === 'forward', pin_located: !!(edge.from && edge.to) && edge.geometry_kind !== 'instance_center_not_route' }];
  const ps = edge.endpoints.map(p => locate(p.point, p.instance)).filter(Boolean);
  // Unordered hypernet: star display only; no producer/destination is inferred.
  return ps.slice(1).map(p => ({ from: ps[0], to: p, directed: false, pin_located: false }));
}

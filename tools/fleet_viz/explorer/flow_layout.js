// Display bundling preserves endpoint coordinates. It never invents a physical route or bandwidth.
export function bundleSegments(segments) {
  const groups = new Map();
  for (const s of segments) {
    const a = s.from.join(','), b = s.to.join(',');
    const key = s.directed ? `${a}>${b}` : [a, b].sort().join('|');
    let g = groups.get(key);
    if (!g) { g = { ...s, edges: [], count: 0 }; groups.set(key, g); }
    g.count++;
    if (!g.edges.includes(s.edge)) g.edges.push(s.edge);
  }
  return [...groups.values()];
}

// Round-robin across spatial cells: a source-ordered prefix must not crowd out the rest of the die.
export function spatialOverview(segments, { width, height, limit = 160, columns = 8 } = {}) {
  if (segments.length <= limit) return segments;
  const cells = new Map();
  for (const s of segments) {
    const x = (s.from[0] + s.to[0]) / 2, y = (s.from[1] + s.to[1]) / 2;
    const ix = Math.max(0, Math.min(columns - 1, Math.floor(x / width * columns)));
    const iy = Math.max(0, Math.min(columns - 1, Math.floor(y / height * columns)));
    const key = iy * columns + ix;
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(s);
  }
  const length = s => Math.hypot(s.to[0] - s.from[0], s.to[1] - s.from[1]);
  const buckets = [...cells.entries()].sort((a, b) => a[0] - b[0])
    .map(([, v]) => v.sort((a, b) => length(b) - length(a) || (b.edge.width_bits || 0) - (a.edge.width_bits || 0)));
  const out = [];
  for (let i = 0; out.length < limit; i++) {
    let found = false;
    for (const b of buckets) if (b[i]) { out.push(b[i]); found = true; if (out.length === limit) break; }
    if (!found) break;
  }
  return out;
}

export function bundleLabel(s) {
  const widths = [...new Set(s.edges.map(e => e.width_bits).filter(Number.isFinite))].sort((a, b) => a - b);
  const width = !widths.length ? 'width unknown' : widths.length === 1 ? `${widths[0].toLocaleString()} bits` : `${widths[0].toLocaleString()}–${widths.at(-1).toLocaleString()} bits`;
  return s.edges.length > 1 ? `${s.edges.length} connections · ${width} each` : width;
}

export function placeLabel(box, occupied, width, height) {
  if (box.x < 0 || box.y < 0 || box.x + box.w > width || box.y + box.h > height) return false;
  if (occupied.some(r => box.x < r.x + r.w + 4 && box.x + box.w + 4 > r.x && box.y < r.y + r.h + 3 && box.y + box.h + 3 > r.y)) return false;
  occupied.push(box);
  return true;
}

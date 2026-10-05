"""Deterministic GDSII structural reader used by the IHP bitcell measurements.

The reader is intentionally small and dependency-free so that a bitcell pitch
taken from a vendor GDS can be audited from this file alone.  It resolves
SREF/AREF placement, mirroring, rotation and magnification, which is what the
pitch measurement depends on; it does not resolve path widths, and no result
that depends on a path width may be taken from it.
"""
import struct, sys
from collections import defaultdict

def _real8(b):
    e = b[0]; sign = -1 if e & 0x80 else 1; exp = (e & 0x7f) - 64
    m = int.from_bytes(b[1:8], 'big')
    return sign * m * (16.0 ** exp) / (1 << 56)

def read_records(path):
    data = open(path, 'rb').read()
    i = 0
    out = []
    while i + 4 <= len(data):
        ln, rt, dt = struct.unpack('>HBB', data[i:i+4])
        if ln < 4:
            break
        out.append((rt, dt, data[i+4:i+ln]))
        i += ln
    return out

def parse(path):
    recs = read_records(path)
    cells = {}
    unit = None
    cur = None
    el = None
    st = {}
    for rt, dtp, body in recs:
        if rt == 0x03:
            unit = (_real8(body[0:8]), _real8(body[8:16]))
        elif rt == 0x05:
            cur = {'shapes': [], 'refs': []}
        elif rt == 0x06:
            cells[body.decode('latin1').rstrip('\x00')] = cur
        elif rt == 0x07:
            cur = None
        elif rt in (0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x2d):
            el = rt
            st = {'strans': 0, 'angle': 0.0, 'mag': 1.0}
        elif rt == 0x0d:
            st['layer'] = struct.unpack('>h', body[:2])[0]
        elif rt == 0x0e or rt == 0x16:
            st['dt'] = struct.unpack('>h', body[:2])[0]
        elif rt == 0x12:
            st['sname'] = body.decode('latin1').rstrip('\x00')
        elif rt == 0x1a:
            st['strans'] = struct.unpack('>H', body[:2])[0]
        elif rt == 0x1b:
            st['mag'] = _real8(body[:8])
        elif rt == 0x1c:
            st['angle'] = _real8(body[:8])
        elif rt == 0x10:
            n = len(body) // 4
            st['xy'] = struct.unpack('>%di' % n, body[:n*4])
        elif rt == 0x13:
            st['colrow'] = struct.unpack('>hh', body[:4])
        elif rt == 0x11:
            if el in (0x08, 0x09, 0x2d) and 'xy' in st:
                xy = st['xy']
                cur['shapes'].append((st.get('layer', -1), st.get('dt', 0),
                                      list(zip(xy[0::2], xy[1::2])), el))
            elif el == 0x0a and 'sname' in st:
                x, y = st['xy'][0], st['xy'][1]
                cur['refs'].append({'name': st['sname'], 'x': x, 'y': y,
                                    'mirror': bool(st['strans'] & 0x8000),
                                    'angle': st['angle'], 'mag': st['mag'],
                                    'aref': None})
            elif el == 0x0b and 'sname' in st:
                nc, nr = st['colrow']
                xy = st['xy']
                x0, y0, x1, y1, x2, y2 = xy[:6]
                cur['refs'].append({'name': st['sname'], 'x': x0, 'y': y0,
                                    'mirror': bool(st['strans'] & 0x8000),
                                    'angle': st['angle'], 'mag': st['mag'],
                                    'aref': (nc, nr, (x1-x0)/nc, (y1-y0)/nc,
                                             (x2-x0)/nr, (y2-y0)/nr)})
            el = None
    return cells, unit

def xform(ref):
    """Return (a,b,c,d) 2x2 matrix for point mapping plus translation."""
    import math
    ang = math.radians(ref['angle'] or 0.0)
    m = ref['mag'] or 1.0
    ca, sa = math.cos(ang), math.sin(ang)
    # GDS: mirror about x-axis first (y -> -y), then rotate, then translate
    if ref['mirror']:
        # (x, -y) then rotate
        return (m*ca, m*sa, m*sa, -m*ca)
    return (m*ca, -m*sa, m*sa, m*ca)

def apply(mat, x, y):
    a, b, c, d = mat
    return (a*x + b*y, c*x + d*y)

def instances(cells, top, target):
    """All placements of `target` under `top` as (x, y) origins in top coords."""
    out = []
    def walk(name, ox, oy, mat, depth):
        if depth > 30:
            return
        c = cells.get(name)
        if c is None:
            return
        for r in c['refs']:
            rm = xform(r)
            nm = (mat[0]*rm[0] + mat[1]*rm[2], mat[0]*rm[1] + mat[1]*rm[3],
                  mat[2]*rm[0] + mat[3]*rm[2], mat[2]*rm[1] + mat[3]*rm[3])
            dx, dy = apply(mat, r['x'], r['y'])
            steps = [(0.0, 0.0)]
            if r['aref']:
                nc, nr, cx, cy, rx, ry = r['aref']
                steps = [(i*cx + j*rx, i*cy + j*ry)
                         for j in range(nr) for i in range(nc)]
            for sx, sy in steps:
                tx, ty = apply(mat, sx, sy)
                px, py = ox + dx + tx, oy + dy + ty
                if r['name'] == target:
                    out.append((px, py))
                else:
                    walk(r['name'], px, py, nm, depth + 1)
    walk(top, 0.0, 0.0, (1.0, 0.0, 0.0, 1.0), 0)
    return out

_bb = {}
def bbox(cells, name, stack=()):
    if name in _bb:
        return _bb[name]
    if name in stack:
        return None
    c = cells.get(name)
    if c is None:
        return None
    pts = []
    for (l, d, poly, el) in c['shapes']:
        for (x, y) in poly:
            pts.append((x, y))
    for r in c['refs']:
        b = bbox(cells, r['name'], stack + (name,))
        if b is None:
            continue
        mat = xform(r)
        corners = [(b[0], b[1]), (b[2], b[1]), (b[0], b[3]), (b[2], b[3])]
        tc = [apply(mat, cx, cy) for cx, cy in corners]
        steps = [(0.0, 0.0)]
        if r['aref']:
            nc, nr, cx, cy, rx, ry = r['aref']
            steps = [(i*cx + j*rx, i*cy + j*ry)
                     for j in (0, nr-1) for i in (0, nc-1)]
        for sx, sy in steps:
            for (tx, ty) in tc:
                pts.append((r['x'] + tx + sx, r['y'] + ty + sy))
    if not pts:
        _bb[name] = None
        return None
    res = (min(p[0] for p in pts), min(p[1] for p in pts),
           max(p[0] for p in pts), max(p[1] for p in pts))
    _bb[name] = res
    return res


def structure_spans(path):
    """Byte spans of every BGNSTR..ENDSTR record group, keyed by structure name."""
    data = open(path, 'rb').read()
    i = 0
    spans = {}
    start = None
    name = None
    while i + 4 <= len(data):
        ln, rt, dt = struct.unpack('>HBB', data[i:i+4])
        if ln < 4:
            break
        if rt == 0x05:
            start = i
        elif rt == 0x06 and start is not None:
            name = data[i+4:i+ln].decode('latin1').rstrip('\x00')
        elif rt == 0x07 and start is not None:
            spans[name] = (start, i + ln)
            start = None
            name = None
        i += ln
    return data, spans


def subset_gds(path, out, roots):
    """Write a GDS containing only `roots` and everything they reference.

    Records are copied verbatim, so path widths, properties and every other
    element attribute survive even though this module does not interpret them.
    """
    cells, unit = parse(path)
    data, spans = structure_spans(path)
    if not spans:
        raise ValueError(f"{path} contains no structures")
    header = data[:min(start for start, _ in spans.values())]
    need = set()

    def walk(name):
        if name in need or name not in cells:
            return
        need.add(name)
        for ref in cells[name]['refs']:
            walk(ref['name'])

    for root in roots:
        if root not in cells:
            raise ValueError(f"{path} has no structure named {root}")
        walk(root)
    with open(out, 'wb') as handle:
        handle.write(header)
        for name in sorted(need):
            start, end = spans[name]
            handle.write(data[start:end])
        handle.write(struct.pack('>HBB', 4, 0x04, 0x00))
    return sorted(need)

"""Planning-only multi-rank relay rows and exact point-endpoint reach costs.

No GEN geometry, RTL, stage count, calendar, or release binding is changed here.
Endpoint coordinates must be actual pin locations; absent pins fail closed.
"""
import math
from case_reach import xf


def _number(x, positive=False, nonnegative=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError('nonfinite or nonnumeric geometry')
    if (positive and x <= 0) or (nonnegative and x < 0):
        raise ValueError('invalid geometry sign')
    return x


def _integer(x, positive=False):
    if isinstance(x, bool) or not isinstance(x, int) or x < (1 if positive else 0):
        raise ValueError('invalid integer bit range or count')
    return x


def _view(v):
    _number(v['w'], positive=True); _number(v['h'], positive=True)


def _placement(p):
    _number(p['x']); _number(p['y'])
    if p['orient'] not in ('R0', 'R90', 'R180', 'R270', 'MX', 'MY', 'MXR90', 'MYR90'):
        raise ValueError('unknown orientation')


class Reservations:
    """Deterministic atomic reservations of actual oriented tile rectangles."""
    def __init__(self, die_wh, occupied=()):
        for n in die_wh:
            _number(n, positive=True)
        self.die_wh = die_wh
        self.boxes = list(occupied)
        for _, x0, y0, x1, y1 in self.boxes:
            for n in (x0, y0, x1, y1):
                _number(n)
            if x0 >= x1 or y0 >= y1:
                raise ValueError('invalid occupied rectangle')

    def reserve(self, placements, views, masters, halo=0.0):
        _number(halo, nonnegative=True)
        staged = []
        for n in sorted(placements):
            p, v = placements[n], views[masters[n]]
            _view(v); _placement(p)
            w, h = v['w'], v['h']
            if p['orient'] in ('R90', 'R270', 'MXR90', 'MYR90'):
                w, h = h, w
            x0, y0 = p['x'] - halo, p['y'] - halo
            x1, y1 = p['x'] + w + halo, p['y'] + h + halo
            for c in (x0, y0, x1, y1):
                _number(c)
            if x0 < 0 or y0 < 0 or x1 > self.die_wh[0] or y1 > self.die_wh[1]:
                return False, (n, 'outside_die')
            for other, a, b, c, d in self.boxes + staged:
                if n == other or (x0 < c and x1 > a and y0 < d and y1 > b):
                    return False, (n, other)
            staged.append((n, x0, y0, x1, y1))
        self.boxes.extend(staged)
        return True, None


def exact_contract_cost(edges, placements, masters, views, port_widths, reach=405.0, escape_um=None):
    """Bit-exact cost, including reset/clock; no bus centroid or rectangle fallback.

    Endpoint shape is production [instance, port, low_bit, high_bit_exclusive]. Every
    expanded bit must have a real LEF pin and explicit port width. escape_um
    optionally adds measured local escape detours by (instance, pin) key.
    Missing authority raises ValueError; this helper never qualifies timing.
    """
    _number(reach, positive=True)
    for detour in (escape_um or {}).values():
        _number(detour, nonnegative=True)
    def pin(endpoint, bit, expected_direction):
        n, port, lo, hi = endpoint
        _integer(lo); _integer(hi, positive=True)
        width = hi - lo
        if bit >= width or (n, port) not in port_widths:
            raise ValueError(f'missing width or endpoint bit: {endpoint}')
        index = lo + bit
        _integer(port_widths[n, port], positive=True)
        if index >= port_widths[n, port] or index < 0:
            raise ValueError(f'bit outside actual port: {endpoint}')
        name = port if port_widths[n, port] == 1 else f'{port}[{index}]'
        v = views[masters[n]]
        _view(v); _placement(placements[n])
        if name not in v['pins']:
            raise ValueError(f'missing actual LEF pin: {n}.{name}')
        if v.get('directions', {}).get(name) != expected_direction:
            raise ValueError(f'actual LEF direction is not {expected_direction}: {n}.{name}')
        for c in v['pins'][name]:
            _number(c)
        p = xf(placements[n], v['w'], v['h'], *v['pins'][name])
        for c in p:
            _number(c)
        detour = (escape_um or {}).get((n, name), 0.0)
        if detour < 0:
            raise ValueError('negative escape distance')
        return p, detour, (n, name)
    costs = []
    for e in edges:
        s, t = e['source'], e['sink']
        for endpoint in (s, t):
            if len(endpoint) != 4:
                raise ValueError('invalid endpoint schema')
            _integer(endpoint[2]); _integer(endpoint[3], positive=True)
        width = s[3] - s[2]
        _integer(e.get('bits', width), positive=True)
        if width <= 0 or width != t[3] - t[2] or e.get('bits', width) != width:
            raise ValueError('source/sink bit widths differ')
        for bit in range(width):
            a, ae, ak = pin(s, bit, 'OUTPUT')
            b, be, bk = pin(t, bit, 'INPUT')
            span = abs(a[0]-b[0])+abs(a[1]-b[1])+ae+be
            _number(span, nonnegative=True)
            costs.append(dict(source=ak, sink=bk, span_um=span))
    if not costs:
        raise ValueError('no contract edges')
    over = [c for c in costs if c['span_um'] > reach]
    return dict(bits_checked=len(costs), max_span_um=max(c['span_um'] for c in costs),
                over_reach=over, feasible=not over)


def layout(names, tile_wh, columns, gap=0.0):
    """R0 bank ranks, preserving tile identity and logical stage count."""
    _integer(columns, positive=True); _number(gap, nonnegative=True)
    for n in tile_wh:
        _number(n, positive=True)
    if len(set(names)) != len(names):
        raise ValueError('duplicate tile')
    w, h = tile_wh
    offsets = {n: ((i % columns) * (w + gap), (i // columns) * (h + gap))
               for i, n in enumerate(names)}
    nx, ny = min(columns, len(names)), math.ceil(len(names) / columns)
    return dict(offsets=offsets, width=max(0, nx * (w + gap) - gap),
                height=max(0, ny * (h + gap) - gap))


def evaluate(row, origin, pins, edges, reach=405.0, reserved=(), tile_wh=None):
    """Cost EVERY supplied data/forwarded-clock edge, with no centroid fallback.

    pins maps (tile,port) to local LEF offsets. Each edge is ((tile,port),
    actual external endpoint), or ((tile,port),(other_tile,port)). Caller must
    supply the complete relevant contract edge set; a coupon is not closure.
    """
    _number(reach, positive=True)
    for c in origin:
        _number(c)
    for v in row['offsets'].values():
        for c in v:
            _number(c)
    if tile_wh is not None:
        for c in tile_wh:
            _number(c, positive=True)
    for _, x0, y0, x1, y1 in reserved:
        for c in (x0, y0, x1, y1):
            _number(c)
        if x0 >= x1 or y0 >= y1:
            raise ValueError('invalid reservation rectangle')
    def xy(key):
        if key not in pins or key[0] not in row['offsets']:
            raise ValueError(f'missing exact pin or tile: {key}')
        ox, oy = row['offsets'][key[0]]
        px, py = pins[key]
        _number(px); _number(py)
        return origin[0] + ox + px, origin[1] + oy + py
    costs = []
    for own, endpoint in edges:
        a = xy(own)
        b = xy(endpoint) if isinstance(endpoint[0], str) else endpoint
        for c in (*a, *b):
            _number(c)
        cost = abs(a[0] - b[0]) + abs(a[1] - b[1])
        _number(cost, nonnegative=True)
        costs.append(cost)
    if not costs:
        raise ValueError('no contract edges supplied')
    conflicts = []
    if reserved and tile_wh is None:
        raise ValueError('reservation checks require actual tile footprint')
    for n, (dx, dy) in row['offsets'].items():
        if tile_wh is None:
            break
        x, y = origin[0] + dx, origin[1] + dy
        w, h = tile_wh
        for label, x0, y0, x1, y1 in reserved:
            if x < x1 and x + w > x0 and y < y1 and y + h > y0:
                conflicts.append((n, label))
    return dict(max_span_um=max(costs), over_reach=sum(x > reach for x in costs),
                edges_checked=len(costs), footprint_conflicts=conflicts,
                feasible=not conflicts and max(costs) <= reach)

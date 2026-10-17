#!/usr/bin/env python3
"""Cluster boundary: bodies never straddle, ports pinned ON the outline, repair confined, fail-closed bounds check.

ROOT CLUSTER-FLOW 2026-10-16.  Generic for every die (HBM cluster_case, S81 column/hub clusters, Qwen).  Root causes it
removes (HBM pilot_SW / pilot_SW2, d4b SW quadrant):
  1. a relay straddling the cluster rectangle put 1,024 pins outside the cluster die -> GRT-0028;
  2. `place_pins` laid 65,354 ports in arbitrary outline slots (IO HPWL 111 M um, ~1.7 mm per port), so repair_design
     -max_wire 450 inserted 5.77 M buffers on 1.33 M nets, never legalised: wire buffers sat on / over the die edge ->
     GRT-0035 "pin outside die area" -> nets left with no pin inside -> STT-0009 empty Steiner tree.

Contract (spec schema opentallas.die_cluster.spec.v1, all coordinates in the PARENT frame, um):
  {"name": str, "outline": [x0, y0, x1, y1],
   "bodies": [{"name", "master", "x", "y", "w", "h", "orient", "kind"?}],        # every placed parent body near the cluster
   "ports":  [{"name", "direction", "inside": [[x, y], ...], "outside": [[x, y], ...],
               "at"?: [x, y], "layer"?: "M5", "edge"?: "N|S|E|W"}],              # 'at' = top-down pin already assigned
   "allowed_edges"?: ["N", "E", "S", "W"],
   "pin"?: {...PIN_DEFAULTS}, "snap"?: {...SNAP_DEFAULTS}}
resolve_bodies(): every body fully inside or fully outside (policy snap | grow | fail; snap moves the body the least
distance to the side holding its centre, on the placement grid, refusing any overlap -- the moves go back to the parent).
assign_pins(): each port goes to the point where the straight line from its inside pin(s) to its outside pin(s) leaves the
outline (nearest allowed edge if none), then 1-D legalised per edge onto the layer's tracks at `spacing_tracks`, away
from corners and from bodies that touch the edge (pin access), and FIXED (place_pin).  Density per edge is reported and
fails above `max_density_per_um` (owner pin-density rule <= 6/um per face).
flow fragments: floorplan with the core inset (repair buffers legalise inside), detailed_placement after repair, and
bounds_check.tcl before global_route (fail closed: cells / pins outside the die, ports off the outline, unplaced ports).
"""
import argparse, bisect, collections, json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN_DEFAULTS = dict(hor_layer='M4', ver_layer='M5', hor_layers=('M4', 'M6'), ver_layers=('M5', 'M7'), spacing_tracks=2, corner_margin_um=2.0, edge_halo_um=1.0,
                    access_clear_um=0.5, max_density_per_um=6.0, pin_len_um=0.192, pin_w_um=0.024)
SNAP_DEFAULTS = dict(policy='cut', grid_um=0.216, halo_um=0.0, search_um=60.0, flip_penalty_um=20.0, max_move_um=100.0)
# ASAP7 1x routing tracks as cluster_case / die_case_v16 make them (die-local coordinates): layer -> (offset, pitch)
# along the coordinate a pin on that layer is indexed by (x for a vertical layer, y for a horizontal one).
TRACKS = {'M4': (0.012, 0.048), 'M5': (0.012, 0.048), 'M6': (0.016, 0.064), 'M7': (0.016, 0.064),
          'M8': (0.116, 0.080), 'M9': (0.116, 0.080)}
VERTICAL = {'M1', 'M3', 'M5', 'M7', 'M9'}
# ASAP7 tech LEF WIDTH per layer (PPL-0034 rejects a pin narrower than the layer's min width)
WIDTH = {'M4': 0.024, 'M5': 0.024, 'M6': 0.032, 'M7': 0.032, 'M8': 0.040, 'M9': 0.040}
EPS = 1e-6


# ---------------------------------------------------------------------------------------------------------------- LEF
def parse_lef_pins(text):
    """{macro: {'w', 'h', 'pins': {pin: (cx, cy)}}} -- centre of each pin's first RECT, macro frame."""
    out = {}
    for m in re.finditer(r'(?m)^\s*MACRO (\S+)(.*?)^\s*END \1\s*$', text, re.S):
        body = m.group(2)
        sz = re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)', body)
        w, h = (float(sz.group(1)), float(sz.group(2))) if sz else (0.0, 0.0)
        pins = {}
        for pm in re.finditer(r'(?m)^\s*PIN (\S+)(.*?)^\s*END \1\s*$', body, re.S):
            r = re.search(r'RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', pm.group(2))
            if r:
                a, b, c, d = (float(v) for v in r.groups())
                pins[pm.group(1)] = ((a + c) / 2, (b + d) / 2)
        out[m.group(1)] = dict(w=w, h=h, pins=pins)
    return out


def oriented_point(px, py, w, h, orient):
    """Macro-frame point -> offset from the placed bbox lower-left (OpenROAD/DEF orientation semantics)."""
    o = orient or 'R0'
    return {'R0': (px, py), 'MX': (px, h - py), 'MY': (w - px, py), 'R180': (w - px, h - py),
            'R90': (h - py, px), 'R270': (py, w - px), 'MXR90': (py, px), 'MYR90': (h - py, w - px)}[o]


def pin_xy(body, pin, lef):
    """Parent-frame location of `pin` on placed `body` (centre of the body when the LEF lacks the pin)."""
    info = lef.get(body['master'])
    if info and pin in info['pins']:
        dx, dy = oriented_point(*info['pins'][pin], info['w'], info['h'], body.get('orient', 'R0'))
        return (body['x'] + dx, body['y'] + dy)
    return (body['x'] + body['w'] / 2, body['y'] + body['h'] / 2)


# ------------------------------------------------------------------------------------------------------------ bodies
def _rel(b, ol):
    x0, y0, x1, y1 = ol
    bx0, by0, bx1, by1 = b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']
    if bx0 >= x0 - EPS and by0 >= y0 - EPS and bx1 <= x1 + EPS and by1 <= y1 + EPS:
        return 'inside'
    if bx1 <= x0 + EPS or bx0 >= x1 - EPS or by1 <= y0 + EPS or by0 >= y1 - EPS:
        return 'outside'
    return 'straddle'


def _centre_in(b, ol):
    cx, cy = b['x'] + b['w'] / 2, b['y'] + b['h'] / 2
    return ol[0] <= cx < ol[2] and ol[1] <= cy < ol[3]


class _Bins:
    """Uniform bucket index of rectangles for overlap queries."""
    def __init__(self, rects, cell=200.0):
        self.cell, self.b, self.r = cell, collections.defaultdict(list), {}
        for k, r in rects.items():
            self.add(k, r)

    def _keys(self, r):
        c = self.cell
        for i in range(int(math.floor(r[0] / c)), int(math.floor((r[2] - EPS) / c)) + 1):
            for j in range(int(math.floor(r[1] / c)), int(math.floor((r[3] - EPS) / c)) + 1):
                yield i, j

    def add(self, k, r):
        self.r[k] = r
        for key in self._keys(r):
            self.b[key].append(k)

    def remove(self, k):
        r = self.r.pop(k)
        for key in self._keys(r):
            self.b[key].remove(k)

    def hits(self, r, skip=None):
        seen = set()
        for key in self._keys(r):
            for k in self.b.get(key, ()):
                if k == skip or k in seen:
                    continue
                seen.add(k)
                q = self.r[k]
                if q[0] < r[2] - EPS and r[0] < q[2] - EPS and q[1] < r[3] - EPS and r[1] < q[3] - EPS:
                    yield k


def clean_cut(outline, bodies, search_um=60.0, passes=3):
    """Move each outline edge to the nearest line (within search_um) that no body crosses inside the edge's span.
    Returns (outline, [{'edge', 'from', 'to'}], [edges left dirty]).  A cut line through a relay row or a block is the
    root of a straddle; moving the line is cheaper and keeps the parent placement untouched."""
    ol = list(map(float, outline))
    shifts, dirty = [], []
    for _ in range(passes):
        changed = False
        dirty = []
        for e in 'NESW':
            vert = e in 'EW'                        # E/W edges are vertical lines x = c
            k = {'W': 0, 'S': 1, 'E': 2, 'N': 3}[e]
            c0 = ol[k]
            span = (ol[1], ol[3]) if vert else (ol[0], ol[2])
            iv = []
            for b in bodies:
                lo, hi = (b['x'], b['x'] + b['w']) if vert else (b['y'], b['y'] + b['h'])
                plo, phi = (b['y'], b['y'] + b['h']) if vert else (b['x'], b['x'] + b['w'])
                if phi <= span[0] + EPS or plo >= span[1] - EPS or hi < c0 - search_um or lo > c0 + search_um:
                    continue
                iv.append((lo, hi))
            def crossed(c):
                return any(lo + EPS < c < hi - EPS for lo, hi in iv)
            if not crossed(c0):
                continue
            cands = sorted({v for lo, hi in iv for v in (lo, hi) if abs(v - c0) <= search_um}, key=lambda v: (abs(v - c0), v))
            best = next((c for c in cands if not crossed(c)), None)
            if best is None:
                dirty.append(e)
                continue
            # keep the outline non-degenerate
            ol[k] = best
            shifts.append(dict(edge=e, frm=round(c0, 6), to=round(best, 6)))
            changed = True
        if not changed:
            break
    return ol, shifts, dirty


def resolve_bodies(outline, bodies, policy='cut', grid_um=0.216, halo_um=0.0, search_um=60.0, search_step_um=None,
                   flip_penalty_um=20.0, max_move_um=100.0):
    """Every body fully inside or fully outside the outline.  Returns dict(outline, inside, outside, moved, errors).

    cut:  (default) each outline edge first moves to the nearest line within search_um that no body crosses
          (clean_cut; the parent placement stays untouched, the outline change is reported), then snap the rest.

    snap: a straddling body moves the least distance to the side holding its centre (inside: clamped into the outline
          less halo; outside: out through the nearest edge), on the placement grid, never onto another body; when the
          plain move is blocked it slides (+-search_um) and finally may flip side (cost +flip_penalty_um); a move
          longer than max_move_um is refused (snap_blocked: the parent plan must re-home that body).
    grow: (legacy cluster_case 2ce1497cf) the outline grows to hold every body whose centre is inside.
    fail: any straddle is an error."""
    ol = list(map(float, outline))
    bodies = [dict(b) for b in bodies]
    errors, moved, cut = [], [], []
    if policy == 'cut':                          # clean cut lines first, then snap what is left
        ol, cut, _ = clean_cut(ol, bodies, search_um)
        policy = 'snap'
    if policy == 'grow':
        inn = [b for b in bodies if _centre_in(b, ol)]
        if inn:
            ol = [min([ol[0]] + [b['x'] for b in inn]), min([ol[1]] + [b['y'] for b in inn]),
                  max([ol[2]] + [b['x'] + b['w'] for b in inn]), max([ol[3]] + [b['y'] + b['h'] for b in inn])]
    rects = {b['name']: (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']) for b in bodies}
    bins = _Bins(rects)
    g = grid_um or 0.0
    up = (lambda v: math.ceil(v / g - 1e-9) * g) if g else (lambda v: v)
    dn = (lambda v: math.floor(v / g + 1e-9) * g) if g else (lambda v: v)
    for b in bodies:
        rel = _rel(b, ol)
        if rel != 'straddle':
            continue
        side = 'inside' if _centre_in(b, ol) else 'outside'
        if policy == 'fail' or policy == 'grow':
            errors.append(dict(kind='straddle', name=b['name'], side=side, rect=rects[b['name']]))
            continue
        base = {}
        lo_x, hi_x = up(ol[0] + halo_um), dn(ol[2] - halo_um - b['w'])
        lo_y, hi_y = up(ol[1] + halo_um), dn(ol[3] - halo_um - b['h'])
        if lo_x <= hi_x + EPS and lo_y <= hi_y + EPS:
            base['inside'] = [(min(max(b['x'], lo_x), hi_x), min(max(b['y'], lo_y), hi_y))]
        elif side == 'inside':
            errors.append(dict(kind='body_larger_than_outline', name=b['name'], rect=rects[b['name']]))
            continue
        base['outside'] = [(dn(ol[0] - halo_um - b['w']), b['y']), (up(ol[2] + halo_um), b['y']),
                           (b['x'], dn(ol[1] - halo_um - b['h'])), (b['x'], up(ol[3] + halo_um))]
        # least move first: the side holding the centre, then the slide / deeper offsets around each base position
        # (a neighbour can block the plain clamp), then the other side (flip costs flip_penalty_um)
        st = search_step_um or (g * 10 if g else 2.0)
        offs = [k * st for k in range(-int(search_um / st), int(search_um / st) + 1)]
        cands = []
        for sd, pts in base.items():
            pen = 0.0 if sd == side else flip_penalty_um
            for bx, by in pts:
                for ox in offs:
                    for oy in offs:
                        nx, ny = bx + ox, by + oy
                        dist = abs(nx - b['x']) + abs(ny - b['y'])
                        if dist <= max_move_um:
                            cands.append((dist + pen, nx, ny, sd))
        cands.sort()
        done = False
        # bodies it already overlaps in the parent (an illegal parent, e.g. d4b relays over SM tiles) do not block the
        # move -- the move must not make the parent worse; they are reported per move
        pre = set(bins.hits(rects[b['name']], skip=b['name']))
        for _, nx, ny, sd in cands:
            r = (nx, ny, nx + b['w'], ny + b['h'])
            nb = dict(b, x=nx, y=ny)
            if _rel(nb, ol) != sd:
                continue
            hit = next((h for h in bins.hits(r, skip=b['name']) if h not in pre), None)
            if hit is None:
                bins.remove(b['name']); bins.add(b['name'], r)
                moved.append(dict(name=b['name'], master=b.get('master'), side=sd, centre_side=side,
                                  frm=[b['x'], b['y']], to=[round(nx, 6), round(ny, 6)],
                                  dist_um=round(abs(nx - b['x']) + abs(ny - b['y']), 6),
                                  **({'preexisting_overlap': sorted(pre)} if pre else {})))
                b['x'], b['y'] = nx, ny
                done = True
                break
        if not done:
            errors.append(dict(kind='snap_blocked', name=b['name'], side=side, rect=rects[b['name']]))
    inside = [b for b in bodies if _rel(b, ol) == 'inside']
    outside = [b for b in bodies if _rel(b, ol) == 'outside']
    left = [b['name'] for b in bodies if _rel(b, ol) == 'straddle']
    if left and not errors:
        errors.append(dict(kind='straddle_left', names=left[:20], count=len(left)))
    return dict(outline=ol, inside=inside, outside=outside, moved=moved, errors=errors, cut_shifts=cut,
                straddling_after=len(left))


# -------------------------------------------------------------------------------------------------------------- pins
def _exit_point(p, q, ol):
    """Point where segment p->q (p inside) leaves rect ol, and its edge; None when q is inside too."""
    x0, y0, x1, y1 = ol
    dx, dy = q[0] - p[0], q[1] - p[1]
    best = None
    for edge, t in (('W', (x0 - p[0]) / dx if dx < 0 else None), ('E', (x1 - p[0]) / dx if dx > 0 else None),
                    ('S', (y0 - p[1]) / dy if dy < 0 else None), ('N', (y1 - p[1]) / dy if dy > 0 else None)):
        if t is not None and 0 <= t <= 1 and (best is None or t < best[1]):
            best = (edge, t)
    if best is None:
        return None
    e, t = best
    return e, (p[0] + t * dx, p[1] + t * dy)


def _nearest_edge(p, ol, allowed):
    x0, y0, x1, y1 = ol
    d = {'W': p[0] - x0, 'E': x1 - p[0], 'S': p[1] - y0, 'N': y1 - p[1]}
    e = min(allowed, key=lambda k: (d[k], 'NESW'.index(k)))
    return e


def _along(edge, pt):
    return pt[0] if edge in 'NS' else pt[1]


def _edge_span(edge, ol):
    return (ol[0], ol[2]) if edge in 'NS' else (ol[1], ol[3])


def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _blocked(edge, ol, inside, halo, clear):
    """Intervals along `edge` (local coords) covered by bodies within `halo` of that edge (no pin access there)."""
    x0, y0, x1, y1 = ol
    iv = []
    for b in inside:
        bx0, by0, bx1, by1 = b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']
        near = {'S': by0 - y0 <= halo, 'N': y1 - by1 <= halo, 'W': bx0 - x0 <= halo, 'E': x1 - bx1 <= halo}[edge]
        if near:
            iv.append((bx0 - clear, bx1 + clear) if edge in 'NS' else (by0 - clear, by1 + clear))
    iv.sort()
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def assign_pins(outline, ports, inside_bodies=(), allowed_edges='NESW', **cfg):
    """Pins ON the outline.  Returns dict(pins=[...], report={...}, errors=[...]); pin x/y are cluster-LOCAL
    (outline origin = (0, 0)), exactly what place_pin needs in the cluster run."""
    c = dict(PIN_DEFAULTS); c.update({k: v for k, v in cfg.items() if v is not None})
    ol = list(map(float, outline))
    W, H = ol[2] - ol[0], ol[3] - ol[1]
    allowed = [e for e in 'NESW' if e in allowed_edges]
    errors, want = [], collections.defaultdict(list)
    fixed = []
    for p in ports:
        if p.get('at') is not None:
            fixed.append(p)
            continue
        ins = [tuple(v) for v in p.get('inside') or []]
        outs = [tuple(v) for v in p.get('outside') or []]
        P = _centroid(ins) if ins else ((ol[0] + ol[2]) / 2, (ol[1] + ol[3]) / 2)
        P = (min(max(P[0], ol[0]), ol[2]), min(max(P[1], ol[1]), ol[3]))
        hit = None
        if p.get('edge'):
            e = p['edge']; pt = P
        else:
            if outs:
                hit = _exit_point(P, _centroid(outs), ol)
            if hit and hit[0] in allowed:
                e, pt = hit
            else:
                pt = hit[1] if hit else P
                e = _nearest_edge(pt, ol, allowed)
        want[e].append((_along(e, pt), p['name'], p.get('layer')))
    out, rep = [], dict(edges={})
    for e in 'NESW':
        lst = sorted(want.get(e, []))
        if not lst:
            continue
        lo, hi = _edge_span(e, ol)
        layers = list(c['ver_layers'] if e in 'NS' else c['hor_layers'])
        # candidate slots on every pin layer's tracks (die-local), corner margin, none inside a blocked interval;
        # two layers double the edge capacity and halve the displacement at hot spots
        blocked = _blocked(e, ol, inside_bodies, c['edge_halo_um'], c['access_clear_um'])
        slots = []
        for layer in layers:
            off, pitch = TRACKS[layer]
            step = pitch * c['spacing_tracks']
            k0 = math.ceil((c['corner_margin_um'] - off) / step - 1e-9)
            k1 = math.floor((hi - lo - c['corner_margin_um'] - off) / step + 1e-9)
            bi = 0
            for k in range(k0, k1 + 1):
                s_ = lo + off + k * step            # parent frame (outline origin is on the track origin)
                while bi < len(blocked) and blocked[bi][1] < s_:
                    bi += 1
                if bi < len(blocked) and blocked[bi][0] <= s_ <= blocked[bi][1]:
                    continue
                slots.append((s_, layers.index(layer), layer))
        slots.sort()
        slot_layer = [x[2] for x in slots]
        slots = [x[0] for x in slots]
        n = len(lst)
        if n > len(slots):
            errors.append(dict(kind='edge_capacity', edge=e, ports=n, slots=len(slots)))
            continue
        idx = []
        for d, _, _ in lst:
            j = bisect.bisect_left(slots, d)
            if j > 0 and (j == len(slots) or d - slots[j - 1] <= slots[j] - d):
                j -= 1
            idx.append(max(j, idx[-1] + 1) if idx else j)
        for i in range(n - 1, -1, -1):        # push back from the far end when the forward pass overflowed
            cap = len(slots) - (n - i)
            idx[i] = min(idx[i], cap if i == n - 1 else min(cap, idx[i + 1] - 1))
        disp = []
        for (d, name, _), j in zip(lst, idx):
            s = slots[j]
            disp.append(abs(s - d))
            if e in 'NS':
                x, y = s - ol[0], (H if e == 'N' else 0.0)
            else:
                x, y = (W if e == 'E' else 0.0), s - ol[1]
            out.append(dict(name=name, edge=e, layer=slot_layer[j], x=round(x, 6), y=round(y, 6),
                            disp_um=round(abs(s - d), 3)))
        length = hi - lo
        dens = n / length if length > 0 else float('inf')
        used = collections.Counter(slot_layer[j] for j in idx)
        rep['edges'][e] = dict(ports=n, layers=dict(used), length_um=round(length, 3), density_per_um=round(dens, 3),
                               blocked_intervals=len(blocked), slots=len(slots),
                               disp_max_um=round(max(disp), 3), disp_mean_um=round(sum(disp) / n, 3))
        if dens > c['max_density_per_um']:
            errors.append(dict(kind='pin_density', edge=e, density_per_um=round(dens, 3), max=c['max_density_per_um']))
    for p in fixed:                            # top-down pins: validate, never move
        x, y = p['at'][0] - ol[0], p['at'][1] - ol[1]
        layer = p.get('layer') or (c['ver_layer'] if abs(y) < EPS or abs(y - H) < EPS else c['hor_layer'])
        on = (abs(y) < EPS or abs(y - H) < EPS) and -EPS <= x <= W + EPS if layer in VERTICAL else \
             (abs(x) < EPS or abs(x - W) < EPS) and -EPS <= y <= H + EPS
        off, pitch = TRACKS.get(layer, (0.0, 0.0))
        v = x if layer in VERTICAL else y
        on_track = pitch == 0 or abs(((v - off) / pitch) - round((v - off) / pitch)) < 1e-3
        if not on or not on_track:
            errors.append(dict(kind='fixed_pin_illegal', name=p['name'], at=p['at'], layer=layer, on_outline=on,
                               on_track=on_track))
        e = ('S' if abs(y) < EPS else 'N') if layer in VERTICAL else ('W' if abs(x) < EPS else 'E')
        out.append(dict(name=p['name'], edge=e, layer=layer, x=round(x, 6), y=round(y, 6), disp_um=0.0, fixed=True))
    names = [q['name'] for q in out]
    dup = [k for k, v in collections.Counter(names).items() if v > 1]
    if dup:
        errors.append(dict(kind='duplicate_port', names=dup[:20]))
    seen = collections.Counter((q['layer'], q['x'], q['y']) for q in out)
    clash = [k for k, v in seen.items() if v > 1]
    if clash:
        errors.append(dict(kind='pin_location_clash', count=len(clash), first=clash[:5]))
    rep['ports'] = len(out)
    rep['outline_local'] = [0.0, 0.0, round(W, 6), round(H, 6)]
    return dict(pins=out, report=rep, errors=errors)


def pins_tcl(pins, pin_len=PIN_DEFAULTS['pin_len_um'], pin_w=None):
    """place_pin per port, FIXED (OpenROAD's place_pin default), long side into the die, layer min width."""
    L = ['# cluster boundary pins (tools/die_cluster/boundary.py): on the outline, on track, FIXED']
    for p in pins:
        pin_w_ = pin_w or WIDTH.get(p['layer'], PIN_DEFAULTS['pin_w_um'])
        sz = f'{pin_w_} {pin_len}' if p['edge'] in 'NS' else f'{pin_len} {pin_w_}'
        L.append(f"place_pin -pin_name {{{p['name']}}} -layer {p['layer']} -location {{{p['x']:.6f} {p['y']:.6f}}} "
                 f"-pin_size {{{sz}}} -force_to_die_boundary")
    return '\n'.join(L) + '\n'


# -------------------------------------------------------------------------------------------------------- flow tcl
def floorplan_tcl(W, H, site='asap7sc7p5t', inset_x=1.08, inset_y=1.08):
    """Die = outline; core inset so every std cell (repair buffers, CTS buffers) legalises strictly inside."""
    return (f'initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} '
            f'-core_area {{{inset_x:.3f} {inset_y:.3f} {W - inset_x:.3f} {H - inset_y:.3f}}} -site {site}')


def legalize_tcl(tag='repair'):
    """After repair_design / CTS: legalise every inserted std cell inside the core; fail closed on DPL failure."""
    return (f'if {{[catch {{detailed_placement}} e]}} {{ puts "OT_CLUSTER_DPL_FAIL {tag} $e"; exit 4 }}\n'
            f'if {{[catch {{check_placement}} e]}} {{ puts "OT_CLUSTER_CHECK_PLACEMENT_FAIL {tag} $e"; exit 4 }}\n'
            f'puts "OT_CLUSTER_LEGAL {tag}"')


def bounds_check_tcl(report='/work/out/cluster_bounds.json', tag='pre_grt', fail=True):
    """source boundary_check.tcl + call: fail closed before global_route."""
    return (f'source /work/cluster_bounds.tcl\n'
            f'set ot_cb [ot_cluster_bounds {report} {tag}]\n'
            + (f'if {{$ot_cb != 0}} {{ puts "OT_CLUSTER_BOUNDS_FAIL {tag} $ot_cb"; exit 3 }}\n' if fail else ''))


def bounds_tcl_path():
    return HERE / 'cluster_bounds.tcl'


# ------------------------------------------------------------------------------------------------------------- CLI
def run_spec(spec):
    snap = dict(SNAP_DEFAULTS); snap.update(spec.get('snap') or {})
    rb = resolve_bodies(spec['outline'], spec.get('bodies', []), snap['policy'], snap['grid_um'], snap['halo_um'],
                        snap['search_um'], snap.get('search_step_um'), snap['flip_penalty_um'],
                        snap['max_move_um'])
    ap = assign_pins(rb['outline'], spec.get('ports', []), rb['inside'], ''.join(spec.get('allowed_edges', 'NESW')),
                     **(spec.get('pin') or {}))
    return rb, ap


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec', type=Path, help='opentallas.die_cluster.spec.v1 JSON')
    ap.add_argument('--out', type=Path, required=True, help='directory: pins.tcl, boundary.json, cluster_bounds.tcl')
    a = ap.parse_args()
    spec = json.loads(a.spec.read_text())
    rb, pa = run_spec(spec)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'pins.tcl').write_text(pins_tcl(pa['pins']))
    (a.out / 'cluster_bounds.tcl').write_text(bounds_tcl_path().read_text())
    rep = dict(schema='opentallas.die_cluster.boundary.v1', name=spec.get('name'), outline=rb['outline'],
               inside=len(rb['inside']), outside=len(rb['outside']), moved=rb['moved'], pins=pa['report'],
               errors=rb['errors'] + pa['errors'])
    (a.out / 'boundary.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(name=rep['name'], inside=rep['inside'], moved=len(rep['moved']), ports=pa['report']['ports'],
                          errors=len(rep['errors']))))
    return 1 if rep['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())

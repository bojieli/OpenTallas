#!/usr/bin/env python3
"""Face-aware obstacle-avoiding hub router for the S81 VM-centred (vmc) hub (S-DIE 2026-10-15 22:40).

The C5 side-by-side hub drew hub polylines from heuristic face points that ignored the real port faces (capture
t_vm on S, SU VM bits on N), so the preflight saw L=0 abutments where the real wires had to U-turn.  In vmc mode every
hub polyline is derived here instead:

  * the endpoint face is the port's ASSIGNED face (die pin record, orientation applied) when the master has one,
    otherwise the face of the block that looks at the peer (generator-laid faces follow the same rule at finalize);
  * the endpoint is the port's real pin-span centre on that face when the record carries positions, otherwise the
    point of the face nearest the peer;
  * the route is the straight / single-L path when it crosses no macro, else a turn-penalised A* on a 43.2-um raster
    of every non-station macro (margin 8.64 um), compressed to its corners.

Pure geometry: no RTL, no pins written.  The caller keeps station placement, reach and the preflight audit.
"""
from __future__ import annotations

import heapq
from collections import Counter

PITCH = 43.2
MARGIN = 8.64
STUB = 30.0          # first / last leg leaves the face perpendicular by this much before turning
TURN = 12            # turn penalty in raster steps
WINDOW = 2600.0      # raster window around the endpoints' bounding box
PIN_PITCH = 0.048


def _flip(face, orient):
    if orient in ('MY', 'R180'):
        face = {'E': 'W', 'W': 'E'}.get(face, face)
    if orient in ('MX', 'R180'):
        face = {'N': 'S', 'S': 'N'}.get(face, face)
    return face


def assigned_face(rec, port):
    """(face, along-face centre in master coordinates or None) of an assigned port record, before orientation"""
    if not rec:
        return None
    base = port.split('[')[0]
    spec = rec.get('ports', {}).get(base)
    if not spec:
        return None
    if spec.get('per_bit'):
        faces = Counter(r[0] for r in spec['per_bit'])
        f = faces.most_common(1)[0][0]
        pos = [r[2] for r in spec['per_bit'] if r[0] == f]
        return f, (min(pos) + max(pos)) / 2
    if 'face' in spec:
        at = spec.get('at') or [None]
        return spec['face'], (at[0] + spec.get('bits', 1) * PIN_PITCH / 2) if at[0] is not None else None
    return None


def face_toward(it, other):
    cx, cy = it.x + it.w / 2, it.y + it.h / 2
    ox = min(max(cx, other.x), other.x + other.w)
    oy = min(max(cy, other.y), other.y + other.h)
    dx, dy = ox - cx, oy - cy
    return ('E' if dx > 0 else 'W') if abs(dx) * it.h > abs(dy) * it.w else ('N' if dy > 0 else 'S')


def face_point(it, face, along=None, toward=None):
    """die point on `face` of `it`; along = master-coordinate offset along the face (orientation applied by caller)"""
    if face in 'NS':
        lo, hi = it.x + 20.0, it.x + it.w - 20.0
        if along is not None:
            v = it.x + along
        else:
            v = min(max((toward.x + toward.w / 2) if toward else it.x + it.w / 2, lo), hi)
        v = min(max(v, lo), hi)
        return (v, it.y + it.h if face == 'N' else it.y)
    lo, hi = it.y + 20.0, it.y + it.h - 20.0
    if along is not None:
        v = it.y + along
    else:
        v = min(max((toward.y + toward.h / 2) if toward else it.y + it.h / 2, lo), hi)
    v = min(max(v, lo), hi)
    return (it.x + it.w if face == 'E' else it.x, v)


def endpoint(it, port, rec, other):
    """(face, point) of (it, port) for a bus to `other`"""
    af = assigned_face(rec, port)
    if af:
        f0, along = af
        f = _flip(f0, it.orient)
        if along is not None:
            if f in 'NS' and it.orient in ('MY', 'R180'):
                along = it.w - along
            if f in 'EW' and it.orient in ('MX', 'R180'):
                along = it.h - along
        return f, face_point(it, f, along, other)
    f = face_toward(it, other)
    return f, face_point(it, f, None, other)


def _stub(p, face, d=STUB):
    return {'N': (p[0], p[1] + d), 'S': (p[0], p[1] - d), 'E': (p[0] + d, p[1]), 'W': (p[0] - d, p[1])}[face]


def seg_hits(p, q, boxes, skip=()):
    """names of boxes whose interior the orthogonal segment p-q crosses (same test as hub_path_preflight.audit)"""
    out = []
    if abs(p[0] - q[0]) < 1e-6:
        axis, fixed = 1, p[0]
    else:
        axis, fixed = 0, p[1]
    lo, hi = sorted((p[axis], q[axis]))
    if hi - lo < .001:
        return out
    for b in boxes:
        name, x, y, w, h = b
        if name in skip:
            continue
        r = (x, y, x + w, y + h)
        if not r[1 - axis] + .001 < fixed < r[3 - axis] - .001:
            continue
        if min(hi, r[axis + 2]) - max(lo, r[axis]) > .001:
            out.append(name)
    return out


def path_hits(path, boxes, skip=()):
    return [n for p, q in zip(path, path[1:]) for n in seg_hits(p, q, boxes, skip)]


def _dedup(path):
    out = []
    for p in path:
        p = (round(p[0], 3), round(p[1], 3))
        if not out or abs(out[-1][0] - p[0]) + abs(out[-1][1] - p[1]) > 1e-6:
            out.append(p)
    # drop collinear middle points
    k = 1
    while k < len(out) - 1:
        a, b, c = out[k - 1], out[k], out[k + 1]
        if (abs(a[0] - b[0]) < 1e-6 and abs(b[0] - c[0]) < 1e-6) or (abs(a[1] - b[1]) < 1e-6 and abs(b[1] - c[1]) < 1e-6):
            out.pop(k)
        else:
            k += 1
    return out


def _astar(a, b, boxes, die):
    """turn-penalised A* between a and b on a PITCH raster; returns corner list or None"""
    x0 = max(die[0], min(a[0], b[0]) - WINDOW); x1 = min(die[2], max(a[0], b[0]) + WINDOW)
    y0 = max(die[1], min(a[1], b[1]) - WINDOW); y1 = min(die[3], max(a[1], b[1]) + WINDOW)
    nx, ny = int((x1 - x0) / PITCH) + 1, int((y1 - y0) / PITCH) + 1
    blocked = bytearray(nx * ny)
    for _, x, y, w, h in boxes:
        if x + w < x0 or x > x1 or y + h < y0 or y > y1:
            continue
        i0 = max(0, int((x - MARGIN - x0) // PITCH)); i1 = min(nx - 1, int((x + w + MARGIN - x0) // PITCH) + 1)
        j0 = max(0, int((y - MARGIN - y0) // PITCH)); j1 = min(ny - 1, int((y + h + MARGIN - y0) // PITCH) + 1)
        # a cell is blocked when its centre lies inside the margin-expanded box
        for i in range(i0, i1 + 1):
            cx = x0 + i * PITCH
            if not (x - MARGIN < cx < x + w + MARGIN):
                continue
            base = i * ny
            for j in range(j0, j1 + 1):
                cy = y0 + j * PITCH
                if y - MARGIN < cy < y + h + MARGIN:
                    blocked[base + j] = 1
    def cell(p):
        return (min(max(int(round((p[0] - x0) / PITCH)), 0), nx - 1), min(max(int(round((p[1] - y0) / PITCH)), 0), ny - 1))
    def anchor(p):
        i0, j0 = cell(p)
        choices = sorted(((abs(di)+abs(dj), i0+di, j0+dj)
                          for di in range(-4, 5) for dj in range(-4, 5)))
        for _, i, j in choices:
            if not (0 <= i < nx and 0 <= j < ny) or blocked[i * ny + j]:
                continue
            q = (x0 + i * PITCH, y0 + j * PITCH)
            for link in ([p, (p[0], q[1]), q], [p, (q[0], p[1]), q]):
                if not path_hits(link, boxes):
                    return (i, j), _dedup(link)
        return None
    aa, bb = anchor(a), anchor(b)
    if aa is None or bb is None:
        return None
    sa, ac = aa
    sb, bc = bb
    D = ((1, 0), (-1, 0), (0, 1), (0, -1))
    INF = 1 << 60
    dist = {}
    q = []
    for d in range(4):
        dist[(sa[0], sa[1], d)] = 0
        heapq.heappush(q, (abs(sa[0] - sb[0]) + abs(sa[1] - sb[1]), 0, sa[0], sa[1], d))
    prev = {}
    end = None
    while q:
        f, g, i, j, d = heapq.heappop(q)
        if g != dist.get((i, j, d), INF):
            continue
        if (i, j) == sb:
            end = (i, j, d)
            break
        for nd, (di, dj) in enumerate(D):
            ii, jj = i + di, j + dj
            if not (0 <= ii < nx and 0 <= jj < ny) or blocked[ii * ny + jj]:
                continue
            ng = g + 1 + (TURN if nd != d else 0)
            k = (ii, jj, nd)
            if ng < dist.get(k, INF):
                dist[k] = ng
                prev[k] = (i, j, d)
                heapq.heappush(q, (ng + abs(ii - sb[0]) + abs(jj - sb[1]), ng, ii, jj, nd))
    if end is None:
        return None
    cells = []
    k = end
    while k is not None:
        cells.append((x0 + k[0] * PITCH, y0 + k[1] * PITCH))
        k = prev.get(k)
    cells.reverse()
    return _dedup(ac + cells[1:] + list(reversed(bc))[1:])


def route(a, fa, b, fb, boxes, die, skip=(), narrow=True):
    """orthogonal polyline from face point a (face fa) to face point b (face fb) avoiding boxes"""
    def inside(p):
        return any(x < p[0] < x + w and y < p[1] < y + h for n, x, y, w, h in boxes if n not in skip)
    def stub(p, f):
        for d in (STUB, 10.0, 4.0, 1.0):
            q = _stub(p, f, d)
            if not inside(q):
                return q
        return _stub(p, f, 1.0)
    sa, sb = stub(a, fa), stub(b, fb)
    cands = []
    if abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6:
        cands.append([a, b])
    cands += [[a, sa, (sa[0], sb[1]), sb, b], [a, sa, (sb[0], sa[1]), sb, b]]
    if fa in 'NS':
        cands.append([a, (a[0], b[1]), b])
    else:
        cands.append([a, (b[0], a[1]), b])
    for c in cands:
        c = _dedup(c)
        if not path_hits(c, boxes, skip):
            return c
    mid = _astar(sa, sb, [bx for bx in boxes if bx[0] not in skip], die)
    if mid is not None:
        # Anchor connectors were checked before A*: never move a raster endpoint
        # through the source macro while stitching its exact physical face.
        out = _dedup([a] + mid + [b])
        if not path_hits(out, boxes, skip):
            return out
    # S-DIE 0030 10-16 (pf17: sseq E-face pins 5.6 um from a station column, VM->collective seam behind link landings):
    # the 43.2-um raster cannot see slits; route on the exact Hanan grid of the obstacle edges (+- CLR) instead
    return hanan_route(a, fa, b, fb, [bx for bx in boxes if bx[0] not in skip], die, narrow=narrow)


CLR = 2.16           # Hanan-grid clearance from every obstacle edge, end blocks included (um)


def hanan_route(a, fa, b, fb, boxes, die, clr=CLR, narrow=True):
    """exact orthogonal route on the Hanan grid of obstacle edges +- clr (turn-penalised Dijkstra), windows grown
    300 / 900 / WINDOW um around the endpoints; the first leg leaves a along fa and the last enters b against fb.
    None when no legal path exists in the largest window."""
    import numpy as np
    for c_ in ((WIDE_CLR, clr) if narrow else (WIDE_CLR,)):         # a real channel first (wide buses), the slit-level clearance only when none exists
        out = _hanan_once(a, fa, b, fb, boxes, die, c_)
        if out is not None:
            return out
    return None


WIDE_CLR = 21.6     # a channel that also holds 17-um relay stations (>= 43.2 um); slits (CLR) only when none exists


def _hanan_once(a, fa, b, fb, boxes, die, clr):
    import numpy as np
    a0, b0 = a, b
    a, b = _stub(a0, fa, clr + 0.5), _stub(b0, fb, clr + 0.5)
    if any(x < p[0] < x + w and y < p[1] < y + h for p in (a, b) for _, x, y, w, h in boxes):
        return None
    for win in (300.0, 900.0, WINDOW):
        x0 = max(die[0], min(a[0], b[0]) - win); x1 = min(die[2], max(a[0], b[0]) + win)
        y0 = max(die[1], min(a[1], b[1]) - win); y1 = min(die[3], max(a[1], b[1]) + win)
        bx = [(x - clr, y - clr, x + w + clr, y + h + clr) for _, x, y, w, h in boxes
              if x + w > x0 and x < x1 and y + h > y0 and y < y1]
        xs = sorted({round(v, 3) for v in [a[0], b[0], x0, x1] + [r[0] for r in bx] + [r[2] for r in bx] if x0 <= v <= x1})
        ys = sorted({round(v, 3) for v in [a[1], b[1], y0, y1] + [r[1] for r in bx] + [r[3] for r in bx] if y0 <= v <= y1})
        X, Y = np.array(xs), np.array(ys)
        nx, ny = len(xs), len(ys)
        node = np.zeros((nx, ny), bool)      # node strictly inside an expanded box
        eh = np.zeros((max(nx - 1, 1), ny), bool)   # edge (i,j)-(i+1,j) crosses an expanded box interior
        ev = np.zeros((nx, max(ny - 1, 1)), bool)
        mx, my = (X[:-1] + X[1:]) / 2, (Y[:-1] + Y[1:]) / 2
        for r in bx:
            ix = (X > r[0] + 1e-4) & (X < r[2] - 1e-4); iy = (Y > r[1] + 1e-4) & (Y < r[3] - 1e-4)
            jx = (mx > r[0]) & (mx < r[2]); jy = (my > r[1]) & (my < r[3])
            node[np.ix_(ix, iy)] = True
            eh[np.ix_(jx, iy)] = True
            ev[np.ix_(ix, jy)] = True
        ia, ja = xs.index(round(a[0], 3)), ys.index(round(a[1], 3))
        ib, jb = xs.index(round(b[0], 3)), ys.index(round(b[1], 3))
        D = {'E': (1, 0), 'W': (-1, 0), 'N': (0, 1), 'S': (0, -1)}
        dl = list(D.values())
        d0 = dl.index(D[fa])
        dend = dl.index({'E': (-1, 0), 'W': (1, 0), 'N': (0, -1), 'S': (0, 1)}[fb])
        tc = 4 * PITCH                        # one turn costs ~170 um of wire
        INF = float('inf')
        dist = {(ia, ja, d0): 0.0}
        prev = {}
        q = [(0.0, ia, ja, d0)]
        end = None
        while q:
            g, i, j, d = heapq.heappop(q)
            if g > dist.get((i, j, d), INF):
                continue
            if (i, j) == (ib, jb) and d == dend:
                end = (i, j, d)
                break
            for nd, (di, dj) in enumerate(dl):
                if (di, dj) == (-dl[d][0], -dl[d][1]):
                    continue
                ii, jj = i + di, j + dj
                if not (0 <= ii < nx and 0 <= jj < ny):
                    continue
                if di:
                    if eh[min(i, ii), j]:
                        continue
                    ln = abs(xs[ii] - xs[i])
                else:
                    if ev[i, min(j, jj)]:
                        continue
                    ln = abs(ys[jj] - ys[j])
                if node[ii, jj] and (ii, jj) != (ib, jb):
                    continue
                ng = g + ln + (tc if nd != d else 0.0)
                k = (ii, jj, nd)
                if ng < dist.get(k, INF):
                    dist[k] = ng
                    prev[k] = (i, j, d)
                    heapq.heappush(q, (ng, ii, jj, nd))
        if end is None:
            continue
        pts = []
        k = end
        while k is not None:
            pts.append((xs[k[0]], ys[k[1]]))
            k = prev.get(k)
        out = _dedup([a0] + pts[::-1] + [b0])
        if not path_hits(out, boxes):
            return out
    return None

"""Geometry helpers: instance orientation, pin points, Manhattan L-routes and their block crossings (um)."""
import math

OPP = dict(N="S", S="N", E="W", W="E")


def xform(px, py, W, H, orient, x0=0.0, y0=0.0):
    """master-frame point (px, py) of a W x H master -> die point for an instance at bbox origin (x0, y0)."""
    o = orient or "R0"
    if o == "R0":
        X, Y = px, py
    elif o == "R180":
        X, Y = W - px, H - py
    elif o == "MX":
        X, Y = px, H - py
    elif o == "MY":
        X, Y = W - px, py
    elif o == "R90":
        X, Y = H - py, px
    elif o == "R270":
        X, Y = py, W - px
    elif o == "MXR90":
        X, Y = py, px
    elif o == "MYR90":
        X, Y = H - py, W - px
    else:
        raise ValueError(f"orient {o}")
    return x0 + X, y0 + Y


def face_point(face, lo, hi, W, H):
    """centre of a bus's pin range on a master face, master frame."""
    off = (lo + hi) / 2.0
    if face == "N":
        return off, H
    if face == "S":
        return off, 0.0
    if face == "W":
        return 0.0, off
    if face == "E":
        return W, off
    return W / 2.0, H / 2.0


def nearest_face(x, y, rx, ry, rw, rh):
    d = dict(W=x - rx, E=rx + rw - x, S=y - ry, N=ry + rh - y)
    return min(d, key=d.get)


def manhattan(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def polyline_len(pts):
    return sum(manhattan(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def l_route(p, q, order="HV"):
    """Manhattan L between p and q: HV = horizontal first, VH = vertical first. Returns the corner list."""
    if order == "HV":
        return [p, (q[0], p[1]), q]
    return [p, (p[0], q[1]), q]


def seg_crossings(a, b, rects, skip=()):
    """Axis-parallel segment a->b vs rects [(id, x, y, w, h)] -> [(id, length, face_in, face_out, t_in, t_out)].
    t_in/t_out are distances from a along the segment; face_in None when a lies inside the rect (likewise face_out)."""
    out = []
    (x1, y1), (x2, y2) = a, b
    if x1 == x2 and y1 == y2:
        return out
    horiz = y1 == y2
    for rid, rx, ry, rw, rh in rects:
        if rid in skip:
            continue
        if horiz:
            if not (ry < y1 < ry + rh):
                continue
            lo, hi = min(x1, x2), max(x1, x2)
            s, e = max(lo, rx), min(hi, rx + rw)
            if e <= s:
                continue
            fwd = x2 > x1
            if fwd:
                fin = "W" if x1 < rx else None
                fout = "E" if x2 > rx + rw else None
                t_in, t_out = s - x1, e - x1
            else:
                fin = "E" if x1 > rx + rw else None
                fout = "W" if x2 < rx else None
                t_in, t_out = x1 - e, x1 - s
        else:
            if not (rx < x1 < rx + rw):
                continue
            lo, hi = min(y1, y2), max(y1, y2)
            s, e = max(lo, ry), min(hi, ry + rh)
            if e <= s:
                continue
            fwd = y2 > y1
            if fwd:
                fin = "S" if y1 < ry else None
                fout = "N" if y2 > ry + rh else None
                t_in, t_out = s - y1, e - y1
            else:
                fin = "N" if y1 > ry + rh else None
                fout = "S" if y2 < ry else None
                t_in, t_out = y1 - e, y1 - s
        out.append((rid, e - s, fin, fout, t_in, t_out))
    return out


def path_crossings(pts, rects, skip=()):
    """Crossings along a Manhattan polyline; t measured from pts[0] along the path. Consecutive pieces of the same
    rect (a corner inside a block) are merged."""
    res = []
    t0 = 0.0
    for i in range(len(pts) - 1):
        for rid, ln, fi, fo, ti, to in sorted(seg_crossings(pts[i], pts[i + 1], rects, skip), key=lambda c: c[4]):
            if res and res[-1][0] == rid and abs(res[-1][5] - (t0 + ti)) < 1e-6:
                r = res[-1]
                res[-1] = (rid, r[1] + ln, r[2], fo, r[4], t0 + to)
            else:
                res.append((rid, ln, fi, fo, t0 + ti, t0 + to))
        t0 += manhattan(pts[i], pts[i + 1])
    return res


def ideal_stages(length_um, reach_um):
    """register stages strictly between two registered endpoints for a wire of length_um at reach_um per cycle."""
    if length_um <= reach_um:
        return 0
    return int(math.ceil(length_um / reach_um)) - 1


def stage_positions(length_um, n):
    """evenly spaced stage positions (distance from source) for n stages: j * L / (n + 1)."""
    return [length_um * (j + 1) / (n + 1) for j in range(n)]


def point_at(pts, t):
    """point at distance t along a Manhattan polyline."""
    for i in range(len(pts) - 1):
        d = manhattan(pts[i], pts[i + 1])
        if t <= d or i == len(pts) - 2:
            f = 0.0 if d == 0 else min(1.0, t / d)
            return (pts[i][0] + f * (pts[i + 1][0] - pts[i][0]), pts[i][1] + f * (pts[i + 1][1] - pts[i][1]))
        t -= d
    return pts[-1]

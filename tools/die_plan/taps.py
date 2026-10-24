"""Sink-anchored clock taps (COORD 10-23 R4, GEOM-REVIEW6 17:09, KV-P6).

A partition whose clock sinks are FIRM-planned (face registers at their pins, ft stations on their planned routes, the
per-tap reset synchronisers) may ADD clock taps at those sinks to its ceil(w/pitch) x ceil(h/pitch) grid (KV-P6
motivation: a coarse grid left 6/12 (400 um) and 11/20 (280 um) io_cor_v1 taps without a sink (dead spine drops, unloaded
per-tap reset synchronisers) while the loaded taps held 2.7k sinks / 349-ps trees.

    clock.tap_mode      "grid+sinks" / "sinks" (default "grid": schema.tap_grid's pitch grid).  CP1 r8 RULING (COORD
                        10-23 21:26): these taps are ADDED to the R4 grid (schema.tap_grid), never replace it -- as a
                        replacement the frame's interior logic (4.5-5.7k sinks) piled on one tap (spread 133 ps)
    clock.tap_radius_um max Manhattan distance tap -> planned sink (default 250: the 280-um grid's 205-222 ps trees)
    clock.tap_max_sinks max planned sinks per sink tap (clustering default 1500); clock_taps.tcl caps the real
                        netlist per tap (grid or added) at OT_TAP_MAX_SINKS = this value, else 3000

Method: the planned sinks (planned_sinks) are clustered by capacity- and radius-bounded Manhattan k-medians: k grows
from ceil(N / cap) until every cluster fits the radius and the cap; a tap sits at its cluster's coordinate-wise median
(the L1 centre), clamped TAP_MARGIN_UM inside the outline; empty clusters are dropped, so every tap carries planned
sinks.  Deterministic (farthest-point seeding from the sink nearest the outline centre).  Tap 0 = 'clk' is the tap
nearest the plan's clock.tap_um (the die spine's partition root), the rest 'clk_t<i>' in (y, x) order.
"""
import math

TAP_MARGIN_UM = 17.28          # keep the interior tap pins off the face pin bands
FACE_INSET_UM = 2.0            # a face register sits just inside its pin
SEP_UM = 8.64                  # two taps closer than one lattice step merge (one spine drop)

_CACHE = {}


def _zroute(a, b, fin, fout):
    """face_flops.tcl ff_zroute: the slot's planned route as a polyline."""
    (ax, ay), (bx, by) = a, b
    if abs(ax - bx) < 1 or abs(ay - by) < 1:
        return [a, b]
    if (fin in "EW") != (fout in "EW"):
        return [a, (bx, ay), b] if fin in "EW" else [a, (ax, by), b]
    if fin in "EW":
        xm = (ax + bx) / 2
        return [a, (xm, ay), (xm, by), b]
    ym = (ay + by) / 2
    return [a, (ax, ym), (bx, ym), b]


def _point_at(pts, t):
    for (px, py), (qx, qy) in zip(pts, pts[1:]):
        d = abs(px - qx) + abs(py - qy)
        if t <= d:
            f = 0.0 if d == 0 else t / d
            return (px + f * (qx - px), py + f * (qy - py))
        t -= d
    return pts[-1]


def _inset(x, y, face, w, h):
    return {"E": (x - FACE_INSET_UM, y), "W": (x + FACE_INSET_UM, y), "N": (x, y - FACE_INSET_UM),
            "S": (x, y + FACE_INSET_UM)}.get(face, (x, y))


def planned_sinks(P, tn):
    """[(x, y, kind)] type-frame sites of the type's FIRM-planned clock sinks: one face register per bus pin (in and
    out ports register at the face, R2), ft slot station 0 at each in pin and stations j = 1..k-1 at L*j/k along the
    slot route (or at regs_um), as face_flops.tcl places them.  ft out pins carry no sink (the neighbour's station 0)."""
    import gen_phys
    t = P.types[tn]
    w, h = t["outline_um"]
    slots = {s["name"]: s for s in t.get("ft_slots", [])}
    pins = gen_phys.type_pins(P, tn)
    at = {(p[0], p[1]): (p[3], p[4], p[5]) for p in pins}
    out = []
    for name, bit, _ln, x, y, face in pins:
        base, sfx = (name[:-2], name[-2:]) if name[-2:] in ("_i", "_o") else (name, "")
        if base in slots and sfx:
            if sfx == "_o":
                continue
            s = slots[base]
            out.append(_inset(x, y, face, w, h) + ("ft_s0",))
            k = int(s.get("stations", 1))
            o = at.get((base + "_o", bit))
            if k < 2 or o is None:
                continue
            regs = s.get("regs_um", [])
            pts = _zroute((x, y), (o[0], o[1]), s["in_face"], s["out_face"])
            L = sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))
            for j in range(1, k):
                xy = tuple(regs[j]) if len(regs) >= k else _point_at(pts, L * j / k)
                out.append((xy[0], xy[1], f"ft_s{j}"))
        else:
            out.append(_inset(x, y, face, w, h) + ("face",))
    return out


def _median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def _kmedians(pts, k, iters=25):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    seed = min(pts, key=lambda p: (abs(p[0] - cx) + abs(p[1] - cy), p))
    cen = [seed]
    dmin = [abs(p[0] - seed[0]) + abs(p[1] - seed[1]) for p in pts]
    while len(cen) < k:
        i = max(range(len(pts)), key=lambda j: (dmin[j], -j))
        c = pts[i]
        cen.append(c)
        dmin = [min(d, abs(p[0] - c[0]) + abs(p[1] - c[1])) for d, p in zip(dmin, pts)]
    asg = None
    for _ in range(iters):
        new = [min(range(len(cen)), key=lambda c: (abs(p[0] - cen[c][0]) + abs(p[1] - cen[c][1]), c)) for p in pts]
        if new == asg:
            break
        asg = new
        groups = [[] for _ in cen]
        for p, a in zip(pts, asg):
            groups[a].append(p)
        cen = [(_median([p[0] for p in g]), _median([p[1] for p in g])) if g else c for g, c in zip(groups, cen)]
    groups = [[] for _ in cen]
    for p, a in zip(pts, asg):
        groups[a].append(p)
    return cen, groups


def sink_taps(P, tn):
    """[(port, x, y, n_sinks, radius_um)] sink-anchored taps of type tn (cached per plan object and type)."""
    key = (id(P), tn)
    if key in _CACHE:
        return _CACHE[key]
    t = P.types[tn]
    ck = t.get("clock", {})
    w, h = t["outline_um"]
    R = float(ck.get("tap_radius_um", 250.0))
    cap = int(ck.get("tap_max_sinks", 1500))
    pts = [(x, y) for x, y, _ in planned_sinks(P, tn)]
    if not pts:
        raise ValueError(f"type {tn}: clock.tap_mode 'sinks' but no planned sinks (no pins / ft slots)")
    k = max(1, math.ceil(len(pts) / cap))
    while True:
        cen, groups = _kmedians(pts, k)
        taps = []
        for (x, y), g in zip(cen, groups):
            if not g:
                continue
            x = min(max(x, TAP_MARGIN_UM), w - TAP_MARGIN_UM)
            y = min(max(y, TAP_MARGIN_UM), h - TAP_MARGIN_UM)
            r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
            taps.append([x, y, len(g), r])
        if all(tp[3] <= R and tp[2] <= cap for tp in taps) or k >= len(pts) or k >= 256:
            break
        k += 1
    # one spine drop per lattice step: merge near-coincident taps
    merged = []
    for tp in sorted(taps, key=lambda q: (round(q[1], 3), round(q[0], 3))):
        m = next((q for q in merged if abs(q[0] - tp[0]) + abs(q[1] - tp[1]) < SEP_UM), None)
        if m:
            m[2] += tp[2]
            m[3] = max(m[3], tp[3])
        else:
            merged.append(tp)
    root = ck.get("tap_um", [w / 2, h / 2])
    i0 = min(range(len(merged)), key=lambda i: (abs(merged[i][0] - root[0]) + abs(merged[i][1] - root[1]), i))
    order = [merged[i0]] + [q for i, q in enumerate(merged) if i != i0]
    out = [("clk" if i == 0 else f"clk_t{i}", round(q[0], 4), round(q[1], 4), q[2], round(q[3], 1))
           for i, q in enumerate(order)]
    _CACHE[key] = out
    return out


def report(P, tn):
    """kit / G0 summary of the sink-anchored taps."""
    taps = sink_taps(P, tn)
    ck = P.types[tn].get("clock", {})
    return dict(mode="sinks", radius_um=float(ck.get("tap_radius_um", 250.0)),
                max_sinks=int(ck.get("tap_max_sinks", 1500)), n=len(taps), empty=sum(1 for t in taps if t[3] == 0),
                taps=[dict(name=n, xy=[x, y], planned_sinks=s, radius_um=r) for n, x, y, s, r in taps])

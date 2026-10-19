"""Pin-access windows for generated (placeholder / stand-in / die-model) block abstracts (Q-DIE11 10-18, coordinator 0ea
item 2 + follow-up: "obstruct only the layers actually used, with pin-access windows on every face pin").

Measured failure class: a generated abstract that obstructs a layer over (nearly) its whole footprint makes the GRT
gcells along its pin faces capacity 0 on that layer, so the face pins are unreachable:
  * dv2f12 die: qfd_dv_slice2 OBS M1-M8 full -> GRT overflow 72,022, all in the bottom 240 um of the slice row;
  * Q-CLUSTER4 c_b16 gates: A0 stand-in OBS M1-M6 (0.5-um inset) + M7 stripes -> GRT overflow 585k-747k, mostly M6,
    in strips along the A0 W/E pin faces.

Rule: along every face that carries pins, each cluster of pins (pins closer than 2 x depth merge) gets a window
`depth` um deep from the face, spanning the cluster +- depth along the face, free of OBS on the router's signal layers
from `lo` up to the abstract's top OBS layer.  Layers below `lo` stay obstructed (the block's cells and pin registers sit
under the window).  The hardened block must keep the windows free on those layers (generators record it).

    windows(w, h, pins, depth, lo, top) -> {layer index: [rect]}      pins: [(name, layer, (x0, y0, x1, y1))]
    minus(w, h, holes) / minus_rect(rect, holes) -> exact cover of a rectangle minus holes (x-slabs)
"""


def faces_of(w, h, pins, edge=0.5):
    out = {}
    for _nm, _layer, (a, b, c, d) in pins:
        if b < edge:
            f, lo, hi = 'S', a, c
        elif d > h - edge:
            f, lo, hi = 'N', a, c
        elif a < edge:
            f, lo, hi = 'W', b, d
        elif c > w - edge:
            f, lo, hi = 'E', b, d
        else:
            continue
        out.setdefault(f, []).append((lo, hi))
    return out


def window_rects(w, h, pins, depth):
    if depth <= 0:
        return []
    rects = []
    for f, iv in sorted(faces_of(w, h, pins).items()):
        iv.sort()
        spans = [list(iv[0])]
        for lo, hi in iv[1:]:
            if lo - spans[-1][1] <= 2 * depth:
                spans[-1][1] = max(spans[-1][1], hi)
            else:
                spans.append([lo, hi])
        along = w if f in 'NS' else h
        for lo, hi in spans:
            lo, hi = max(0.0, lo - depth), min(along, hi + depth)
            rects.append({'S': (lo, 0.0, hi, depth), 'N': (lo, h - depth, hi, h),
                          'W': (0.0, lo, depth, hi), 'E': (w - depth, lo, w, hi)}[f])
    return rects


def windows(w, h, pins, depth, lo, top):
    r = window_rects(w, h, pins, depth)
    return {i: list(r) for i in range(lo, top + 1)} if r else {}


def minus_rect(rect, holes):
    """rect (x0, y0, x1, y1) minus the hole rectangles, as x-slabs of y-intervals (exact cover, no overlap)"""
    X0, Y0, X1, Y1 = rect
    hs = [(max(X0, a), max(Y0, b), min(X1, c), min(Y1, d)) for a, b, c, d in holes]
    hs = [q for q in hs if q[2] > q[0] + 1e-9 and q[3] > q[1] + 1e-9]
    if not hs:
        return [rect]
    xs = sorted({X0, X1} | {q for hl in hs for q in (hl[0], hl[2])})
    out = []
    for x0, x1 in zip(xs, xs[1:]):
        if x1 - x0 < 1e-6:
            continue
        ys = sorted((hl[1], hl[3]) for hl in hs if hl[0] < x1 - 1e-9 and hl[2] > x0 + 1e-9)
        y = Y0
        for a, b in ys:
            if a > y + 1e-6:
                out.append((x0, y, x1, a))
            y = max(y, b)
        if Y1 > y + 1e-6:
            out.append((x0, y, x1, Y1))
    return out


def minus(w, h, holes):
    return minus_rect((0.0, 0.0, w, h), holes)

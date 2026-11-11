"""RELAY-SITES macro clearance (TYPE-SAFE-5 2026-11-10).

type_relay_sites.py spaces the sites of a chain evenly on the straight line between its two ends.  When the line
crosses a hard macro, a site can fall inside it.  The placer cannot put a flop there, so it legalises the flop to the
nearest free row instead.  On leaf__t35 p3 that was the macro's top edge, 68 um from the site.  That turned the
following hop into 397-408 um (15 bits over 405) and the stages into collapsed chains.

clear_sites moves every site that lies inside a macro (grown by `halo`) to a free point on that grown rectangle's
boundary.  It takes the point that minimises the larger of its two hops: to the previous site (or, for the first site,
the farthest launch) and to the next site (or, for the last site, the farthest capture).  It works site by site in
chain order, so a moved site is the neighbour the next one sees.  Ties go to the point nearest the original site.
Sites outside every macro are left exactly as they are.
"""

L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def inside(p, r, halo):
    return r[0] - halo < p[0] < r[2] + halo and r[1] - halo < p[1] < r[3] + halo


def ring(r, halo, step):
    """points on the boundary of rectangle r grown by halo, about `step` apart (corners included)"""
    x0, y0, x1, y1 = r[0] - halo, r[1] - halo, r[2] + halo, r[3] + halo
    nx, ny = max(1, int((x1 - x0) / step)), max(1, int((y1 - y0) / step))
    pts = []
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx
        pts += [(x, y0), (x, y1)]
    for j in range(1, ny):
        y = y0 + (y1 - y0) * j / ny
        pts += [(x0, y), (x1, y)]
    return pts


def clear_sites(path, pa, pb, rects, die, halo=6.0, step=2.0):
    """path: [(x, y)] sites in chain order; pa / pb: launch / capture end points; rects: [(x0, y0, x1, y1)] macros;
    die: (x0, y0, x1, y1).  -> (new path, number of sites moved)"""
    out, moved = list(path), 0
    free = lambda p: (die[0] <= p[0] <= die[2] and die[1] <= p[1] <= die[3]
                      and not any(inside(p, r, halo) for r in rects))
    for j, s in enumerate(out):
        hit = [r for r in rects if inside(s, r, halo)]
        if not hit:
            continue
        prev = [out[j - 1]] if j else pa
        nxt = [out[j + 1]] if j + 1 < len(out) else pb
        cand = [p for r in hit for p in ring(r, halo, step) if free(p)]
        if not cand:
            continue                      # no free point on the ring: keep the site, the report still shows the hop
        cost = lambda p: (max(max(L1(p, q) for q in prev), max(L1(p, q) for q in nxt)), L1(p, s))
        best = min(cand, key=cost)
        out[j] = (round(best[0], 3), round(best[1], 3))
        moved += 1
    return out, moved

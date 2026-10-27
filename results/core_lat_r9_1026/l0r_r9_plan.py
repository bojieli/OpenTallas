#!/usr/bin/env python3
"""S81-CORE-LAT-R9: gunit_l0r plan with STRAIGHT legs (COORD 18:5x ruling: maze-meander length equalisation = padding,
banned; GEOM edge check routed <= 1.10 x Manhattan unless a jog is needed for legality).

Same R8 structure (2,2,8,8 equal-count H partition + dedicated W-strip branch, 9 stages, repeaters per level from
geometry) but every edge segment is the SHORTEST legal maze path between its own endpoints: H.exact_points is called
with T = the edge's own shortest legal length (waypoints evenly on that path) instead of the level maximum.
Remaining imbalance is left to 12.8 d1 plan-computed sizing (l0r_r9_d1.py).  Optional --recluster: the L3 groups that
hold the long main leaves are re-partitioned into the same number of equal-count leaves by an equal-count maze power
diagram (H.balanced) seeded at the H.split centroids (compact clusters, same leaf count per island, no padding).
usage: as l0r_r8_model.py + [--recluster T107,T0072,...]  PLAN MODEL, UNCHECKED."""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'core_lat_r8_1026'))
import l0r_r8_model as M8   # noqa: E402
H = M8.H
_exact = H.exact_points
STRAIGHT = []


def exact_straight(mz, a, b, T, k):
    t = mz.md(a, b)
    STRAIGHT.append((round(T, 2), round(t, 2)))
    return _exact(mz, a, b, t, k)


H.exact_points = exact_straight
M8.H.exact_points = exact_straight

_split = H.split
RECL = set()


def _spread(mz, g):
    c = mz.cell((sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g))); x, y = mz.xy(c)
    return max(abs(p[0] - x) + abs(p[1] - y) for p in g), c


def _partitions(pts, k):
    """deterministic candidate equal-count partitions: H.split seeded on x, on y, and on 2-D grids (rows x cols)."""
    out = [H.split(pts, k, axis=0), H.split(pts, k, axis=1)]
    for r_ in [d for d in range(1, k + 1) if k % d == 0]:
        c_ = k // r_
        xs = sorted(p[0] for p in pts); ys = sorted(p[1] for p in pts); n = len(pts)
        cs = [(xs[int((j + .5) * n / c_)], ys[int((i + .5) * n / r_)]) for i in range(r_) for j in range(c_)]
        for _ in range(8):
            grp = H.balanced(pts, list(range(k)), lambda s_, c: abs(s_[0] - cs[c][0]) + abs(s_[1] - cs[c][1]), iters=300)
            cs = [(sorted(p[0] for p in g)[len(g) // 2], sorted(p[1] for p in g)[len(g) // 2]) for g in grp]
        out.append(grp)
    return out


def recluster(P, l3_names):
    """GEOM-7/COORD R8 (b): re-cluster the leaves of the named L3 groups -- same leaf count, equal sink count, leaf
    driver at the cluster centroid, partition chosen = min of max leaf spread over deterministic candidates (structure,
    not a trim; no wire added; L4 edge = shortest legal path from the unchanged branch cell)."""
    mz = P['mz']; node = {n[0]: n for n in P['nodes']}; rep = []
    for g3 in l3_names:
        leaves = sorted(u for u in P['leafsinks'] if u.startswith(g3) and len(u) == len(g3) + 1 and node[u][4] == 'leaf')
        pts = [s for u in leaves for s in P['leafsinks'][u]]; k = len(leaves)
        before = max(_spread(mz, P['leafsinks'][u])[0] for u in leaves)
        best = None
        for grp in _partitions(pts, k):
            sc = [_spread(mz, g) for g in grp]; v = (max(x[0] for x in sc), sum(x[0] for x in sc))
            if best is None or v < best[0]: best = (v, grp, [x[1] for x in sc])
        (mx, _), grp, cells = best
        # match new clusters to the existing leaf names/branch cells by min total branch->centroid distance (greedy)
        bcell = {u: node[u + '_br'][2] for u in leaves}; free = list(range(k)); assign = {}
        for u in leaves:
            j = min(free, key=lambda j: mz.md(bcell[u], cells[j])); assign[u] = j; free.remove(j)
        for u in leaves:
            j = assign[u]; P['leafsinks'][u] = grp[j]
            P['nodes'] = [(n[0], n[1], cells[j] if n[0] == u else n[2], n[3], n[4]) for n in P['nodes']]
            P['wires'] = [w for w in P['wires'] if w['edge'] != u]
            P['wires'].append(dict(level=4, edge=u, segs=[mz.md(bcell[u], cells[j])], cells=[mz.path(bcell[u], cells[j])]))
        rep.append(dict(l3=g3, leaves=k, sinks=[len(g) for g in grp], max_spread_before=round(before, 2), max_spread_after=round(mx, 2)))
        print('RECLUSTER', rep[-1], flush=True)
    return rep


_graft = M8.graft_strip


def graft_with_recluster(P, strip, n_l3=2, n_l4=4):
    rc = recluster(P, sorted(RECL)) if RECL else []
    r = _graft(P, strip, n_l3, n_l4); r['recluster'] = rc
    return r


M8.graft_strip = graft_with_recluster


def main():
    if '--recluster' in sys.argv:
        i = sys.argv.index('--recluster'); RECL.update(sys.argv[i + 1].split(',')); del sys.argv[i:i + 2]
    M8.main()
    print('STRAIGHT edges', len(STRAIGHT), 'level-max length would have been', sum(1 for T, t in STRAIGHT if T > t + 1e-6), 'padded edges (now 0)')


if __name__ == '__main__':
    main()

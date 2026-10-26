#!/usr/bin/env python3
"""HBM-CORE-LAT-R3: per-type 12.8b inputs for the shared slice-driven core generator (MASTER-PLAN-R2).

For each REBUILD type: centre clock entry (4.32 lattice), leaf islands on the MEASURED sink clusters with EQUAL
load (recursive median bisection along the longer side = H-tree topology, 2^k leaves), island = group median
snapped to 4.32 and pushed out of macro+halo, internal tree nodes = midpoint of their two children (snapped), and
trunk repeater stages (one driver per tree node + extra stages so no unbuffered trunk segment exceeds SEG_MAX).
Sink coordinates come from the type's last 3_place.odb (dump_sinks.tcl).  When that placement used an outline
other than the plan outline, coordinates are scaled to the plan outline and the type is marked PROVISIONAL-SCALED
(re-derive from the first placement on the plan outline before CTS).  No latency value here is a sign-off number.
"""
import json, math, os, sys
import numpy as np

LAT = 4.32
HALF = 4.32          # island rect = centre +- 4.32 (8.64 square, as the master-plan slices)
HALO = 4.32
R_LEAF = 100.0       # target p95 Manhattan leaf->sink radius (um)
K_MAX = 4            # at most 16 leaves (programme_store: 32)
SEG_MAX = 150.0      # max unbuffered clock trunk segment (um); plan value, sizing per 12.8 d1 by MASTER-PLAN


def snap(v):
    return round(v / LAT) * LAT


def load(path):
    die, sinks, macros, pins = None, [], [], []
    for ln in open(path):
        p = ln.split()
        if not p:
            continue
        if p[0] == 'DIE':
            die = [float(x) for x in p[1:5]]
        elif p[0] == 'SINK':
            sinks.append((float(p[2]), float(p[3]), p[1].startswith('DFF') or p[1].startswith('SDF') or 'DFF' in p[1]))
        elif p[0] == 'MACRO':
            macros.append([float(x) for x in p[3:7]])
        elif p[0] == 'CLKPIN':
            pins.append((p[1], float(p[2]), float(p[3])))
    return die, sinks, macros, pins


def bisect(idx, pts, k):
    """equal-count recursive bisection; returns tree: leaf = index array, node = (a, b)."""
    if k == 0:
        return idx
    sub = pts[idx]
    w = sub[:, 0].max() - sub[:, 0].min()
    h = sub[:, 1].max() - sub[:, 1].min()
    ax = 0 if w >= h else 1
    order = idx[np.argsort(sub[:, ax], kind='stable')]
    half = len(order) // 2
    return (bisect(order[:half], pts, k - 1), bisect(order[half:], pts, k - 1))


def leaves_of(t):
    return [t] if isinstance(t, np.ndarray) else leaves_of(t[0]) + leaves_of(t[1])


def legal(x, y, W, H, macros):
    x = min(max(x, HALF + LAT), W - HALF - LAT)
    y = min(max(y, HALF + LAT), H - HALF - LAT)
    x, y = snap(x), snap(y)

    def bad(x, y):
        for m in macros:
            if x + HALF > m[0] - HALO and x - HALF < m[2] + HALO and y + HALF > m[1] - HALO and y - HALF < m[3] + HALO:
                return True
        return False
    if not bad(x, y):
        return x, y, 0.0
    best = None
    for r in range(1, 60):
        for dx in range(-r, r + 1):
            for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                cx, cy = x + dx * LAT, y + dy * LAT
                if HALF + LAT <= cx <= W - HALF - LAT and HALF + LAT <= cy <= H - HALF - LAT and not bad(cx, cy):
                    d = abs(dx * LAT) + abs(dy * LAT)
                    if best is None or d < best[2]:
                        best = (round(cx, 2), round(cy, 2), d)
        if best:
            return best
    return x, y, -1.0


def tree_score(c, ex, ey, W, H, macros):
    k, t, lv, isl, rad = c
    pos = {id(g): (isl[i][0], isl[i][1]) for i, g in enumerate(lv)}
    worst = [0.0]

    def walk(tt):
        if isinstance(tt, np.ndarray):
            return [(pos[id(tt)], 0.0, lv.index(tt) if False else None, tt)]
        a, b = walk(tt[0]), walk(tt[1])
        pa, pb = a[0][0], b[0][0]
        return [(((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2), 0.0, None, (a, b))]
    # simple: entry -> leaf Manhattan along bisection midpoints
    def lengths(tt, px, py, acc):
        if isinstance(tt, np.ndarray):
            x, y = pos[id(tt)]
            return [acc + abs(x - px) + abs(y - py)]
        ca = centre(tt)
        L = acc + abs(ca[0] - px) + abs(ca[1] - py)
        return lengths(tt[0], ca[0], ca[1], L) + lengths(tt[1], ca[0], ca[1], L)

    def centre(tt):
        if isinstance(tt, np.ndarray):
            return pos[id(tt)]
        a, b = centre(tt[0]), centre(tt[1])
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    Ls = lengths(t, ex, ey, 0.0) if not isinstance(t, np.ndarray) else [0.0]
    return max(max(Ls), 0) + max(r[0] for r in rad)


def balanced_kmeans(pts, n, init_tree, iters=12):
    """capacity-constrained k-means (Manhattan): every leaf gets floor/ceil(N/n) sinks = equal load."""
    cen = np.array([[np.median(pts[g, 0]), np.median(pts[g, 1])] for g in leaves_of(init_tree)])
    N = len(pts)
    cap = np.full(n, N // n) + (np.arange(n) < N % n)
    for _ in range(iters):
        D = np.abs(pts[:, None, 0] - cen[None, :, 0]) + np.abs(pts[:, None, 1] - cen[None, :, 1])
        # regret-ordered greedy: points with the largest gap between best and 2nd best choose first
        srt = np.sort(D, axis=1)
        order = np.argsort(-(srt[:, 1] - srt[:, 0]) if n > 1 else np.zeros(N), kind='stable')
        pref = np.argsort(D, axis=1)
        lab = np.full(N, -1)
        left = cap.copy()
        for p in order:
            for c in pref[p]:
                if left[c] > 0:
                    lab[p] = c
                    left[c] -= 1
                    break
        new = np.array([[np.median(pts[lab == c, 0]), np.median(pts[lab == c, 1])] for c in range(n)])
        if np.allclose(new, cen):
            break
        cen = new
    return [np.where(lab == c)[0] for c in range(n)]


def remap(t, lv):
    if isinstance(t, np.ndarray):
        return lv[int(t[0])]
    return (remap(t[0], lv), remap(t[1], lv))


def plan_type(name, path, outline, inst, measured_tt, cls):
    die, sinks, macros, pins = load(path)
    pts = np.array([(s[0], s[1]) for s in sinks])
    W, H = outline
    sx, sy = W / (die[2] - die[0]), H / (die[3] - die[1])
    scaled = abs(sx - 1) > 1e-3 or abs(sy - 1) > 1e-3
    pts = np.column_stack(((pts[:, 0] - die[0]) * sx, (pts[:, 1] - die[1]) * sy))
    macros = [[(m[0] - die[0]) * sx, (m[1] - die[1]) * sy, (m[2] - die[0]) * sx, (m[3] - die[1]) * sy] for m in macros]
    ex, ey, ed = legal(W / 2, H / 2, W, H, macros)
    idx = np.arange(len(pts))
    cand, summary = [], []
    for k in range(1, (5 if W * H > 300000 else K_MAX) + 1):
        groups = leaves_of(bisect(idx, pts, k))   # MMM (means-and-medians) equal-count bisection; balanced k-means was tried and is worse (INFO)
        isl, rad = [], []
        for g in groups:
            gx, gy = float(np.median(pts[g, 0])), float(np.median(pts[g, 1]))
            x, y, d = legal(gx, gy, W, H, macros)
            dist = np.abs(pts[g, 0] - x) + np.abs(pts[g, 1] - y)
            isl.append((x, y, d, len(g)))
            rad.append((float(np.percentile(dist, 95)), float(dist.max())))
        ipts = np.array([(x[0], x[1]) for x in isl])
        t = bisect(np.arange(len(isl)), ipts, k)       # H-tree topology over the islands
        lv = [np.array([i]) for i in range(len(isl))]
        t = remap(t, lv)
        cand.append((k, t, lv, isl, rad))
    # pick the smallest k (>= 2 levels = 4 leaves) whose leaf p95 radius is <= R_LEAF for >= 90 % of the leaves
    best = None
    for c in cand:
        p95s = sorted(r[0] for r in c[4])
        q90 = p95s[min(len(p95s) - 1, int(math.ceil(0.9 * len(p95s))) - 1)]
        summary.append({'leaves': 2 ** c[0], 'q90_leaf_p95_radius_um': round(q90, 1), 'max_leaf_p95_radius_um': round(p95s[-1], 1),
                        'worst_trunk_plus_p95_um_INFO': round(tree_score(c, ex, ey, W, H, macros), 1),
                        'islands_xy_um': [[x[0], x[1], x[3]] for x in c[3]]})
        if c[0] >= 2 and best is None and q90 <= R_LEAF:
            best = c
    radius_limited = best is None
    k, t, lv, isl, rad = best if best else cand[-1]
    # tree nodes: bottom-up midpoint of children, root = entry
    leaf_id = {id(g): i for i, g in enumerate(lv)}
    nodes = []

    def build(tt, depth):
        if isinstance(tt, np.ndarray):
            i = leaf_id[id(tt)]
            return ('leaf%d' % i, isl[i][0], isl[i][1])
        a = build(tt[0], depth + 1)
        b = build(tt[1], depth + 1)
        x, y, _ = legal((a[1] + b[1]) / 2, (a[2] + b[2]) / 2, W, H, macros)
        nm = 'n%d_%d' % (depth, len(nodes))
        nodes.append({'name': nm, 'depth': depth, 'xy_um': [x, y], 'children': [a[0], b[0]],
                      'seg_um': [round(abs(a[1] - x) + abs(a[2] - y), 2), round(abs(b[1] - x) + abs(b[2] - y), 2)]})
        return (nm, x, y)
    top = build(t, 1)
    root_seg = abs(top[1] - ex) + abs(top[2] - ey)
    # entry -> each leaf trunk length + stage count
    par = {}
    for n in nodes:
        for c, s in zip(n['children'], n['seg_um']):
            par[c] = (n['name'], s)
    par[top[0]] = ('entry', root_seg)
    trunks = []
    for i in range(len(lv)):
        c, L, st = 'leaf%d' % i, 0.0, 0
        while c != 'entry':
            p, s = par[c]
            L += s
            st += 1 + max(0, math.ceil(s / SEG_MAX) - 1)
            c = p
        trunks.append((round(L, 2), st))
    Ls = [x[0] for x in trunks]
    loads = [x[3] for x in isl]
    corner = max(math.hypot(W / 2, H / 2), 0)
    return {
        'module': name, 'inst': inst, 'measured_natural_tt_ps': measured_tt, 'cls_12_8': cls,
        'plan_outline_um': [W, H], 'sink_source_outline_um': [die[2] - die[0], die[3] - die[1]],
        'coords': 'PROVISIONAL-SCALED (re-derive from first placement on plan outline)' if scaled else 'MEASURED (placement on the plan outline)',
        'sinks': len(pts), 'macros': len(macros),
        'clock_entry': {'xy_um': [ex, ey], 'moved_um': ed, 'island_rect_um': [ex - HALF, ey - HALF, ex + HALF, ey + HALF],
                        'ft_ports': ['mp_isl0_ck_i', 'mp_isl0_ck_o', 'mp_isl0_rst_i', 'mp_isl0_rst_o']},
        'tree': {'levels': k, 'leaves': len(lv), 'topology': 'equal-count recursive bisection (longer side first) = H-tree',
                 'nodes': nodes, 'root_node': top[0], 'entry_to_root_um': round(root_seg, 2)},
        'leaf_islands': [{'name': 'tree_leaf%d' % i, 'xy_um': [x[0], x[1]], 'rect_um': [x[0] - HALF, x[1] - HALF, x[0] + HALF, x[1] + HALF],
                          'moved_from_median_um': x[2], 'sinks': x[3], 'p95_radius_um': round(rad[i][0], 1),
                          'max_radius_um': round(rad[i][1], 1), 'trunk_um': trunks[i][0], 'trunk_stages': trunks[i][1]}
                         for i, x in enumerate(isl)],
        'balance': {'load_min': min(loads), 'load_max': max(loads), 'trunk_min_um': min(Ls), 'trunk_max_um': max(Ls),
                    'trunk_imbalance_um': round(max(Ls) - min(Ls), 2),
                    'note': 'equal-length legs = generator routes each leg to trunk_max (plan-computed, 12.8 d1); imbalance is input, not a trim'},
        'k_candidates': summary,
        'radius_limited': radius_limited,
        'leaf_radius_target_um': R_LEAF, 'seg_max_um': SEG_MAX,
        'max_entry_to_sink_um_via_tree': round(max(Ls) + max(r[1] for r in rad), 1),
        'centre_to_corner_um': round(W / 2 + H / 2, 1),
    }


def main():
    rc, sinkdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    d = json.load(open(rc))
    res = []
    for t in sorted(d['types'], key=lambda t: -t['tt_ps']):
        f = os.path.join(sinkdir, t['module'] + '.txt')
        if not os.path.exists(f):
            res.append({'module': t['module'], 'inst': t['inst'], 'measured_natural_tt_ps': t['tt_ps'], 'cls_12_8': t['cls_12_8'],
                        'plan_outline_um': t['plan_outline_um'], 'coords': 'NO PLACED DB on the fleet (epyc3 retired / pruned)',
                        'method': 'generator places once on the plan outline (GOAL=place), then this tool computes the leaves before CTS'})
            continue
        res.append(plan_type(t['module'], f, t['plan_outline_um'], t['inst'], t['tt_ps'], t['cls_12_8']))
    json.dump({'schema': 'opentallas.hbm.core_tree_inputs.v1', 'lane': 'HBM-CORE-LAT-R3', 'status': 'UNCHECKED',
               'rule': 'METHODOLOGY 12.8a/b/d1 + 12.2a1; COORD 07:18 one shared generator (MASTER-PLAN-R2)',
               'params': {'lattice_um': LAT, 'island_half_um': HALF, 'halo_um': HALO, 'leaf_p95_radius_target_um': R_LEAF,
                          'seg_max_um': SEG_MAX, 'k_max': K_MAX},
               'types': res}, open(out, 'w'), indent=1)
    for r in res:
        if 'tree' in r:
            b = r['balance']
            print('%-44s %5s inst%-3d %-9s leaves%-3d load %5d-%-5d p95r<=%5.1f trunk %6.1f-%6.1f stages<=%d E->S %6.1f %s' % (
                r['module'], r['measured_natural_tt_ps'], r['inst'], 'x'.join('%g' % v for v in r['plan_outline_um']), r['tree']['leaves'],
                b['load_min'], b['load_max'], max(l['p95_radius_um'] for l in r['leaf_islands']), b['trunk_min_um'], b['trunk_max_um'],
                max(l['trunk_stages'] for l in r['leaf_islands']), r['max_entry_to_sink_um_via_tree'], r['coords'][:12]))
        else:
            print('%-44s %5s inst%-3d %s' % (r['module'], r['measured_natural_tt_ps'], r['inst'], r['coords']))


if __name__ == '__main__':
    main()

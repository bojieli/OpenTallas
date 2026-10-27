#!/usr/bin/env python3
"""S81-CORE-LAT-R8: gunit_l0r core clock plan = R7 F1 (equal-structure 2,2,8,8 H-tree, NDR2W trunk, 12.8 d1 sizing)
+ a DEDICATED equal-structure branch for the W-face pin-register strip (GEOM-REVIEW-7 R6/R7 condition 1).

PLAN MODEL ONLY: deterministic, plan geometry (R6 GPL placement) + liberty, no measured timing input.

Strip branch (structure, not a trim): the strip sinks (placed in the first site column, x < STRIP_X) are removed from the
equal-count H partition and get their own L3 edges: STRIP_L3 extra L3 children of the two W L2 nodes (T00 south, T01
north), each an ordinary L3 edge (same length T3 by detour + same repeater count as every L3 edge), each with
STRIP_L4 ordinary L4 leaf edges to leaves that cover <= ~15 um of the strip.  Every root->sink path still has the same
stage count (9) and the same per-level edge lengths; the strip leaves are short (no 114-um leaf MST).
Other long leaves of the main tree (> LEAF_SPLIT_UM) are reported; they are not split here unless --split-long.

GEOM-7 (3): d1 sizing restricted to the BUFx8..x24 gating envelope (BUFx4f/5/6f removed from the plan search).
"""
import argparse, collections, copy, gzip, json, math, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'core_lat_r7_1026'))
sys.path.insert(0, str(HERE.parents[1] / 'tools' / 'die_plan'))
import l0r_r7_model as M7          # noqa: E402  (R7 predictor chain, unchanged)
import core_infra_htree as H       # noqa: E402

STRIP_X = 5.0          # um: W-face first site column (754 face/pin registers at x = 4.414 in the R6 GPL geometry)
GATING_BUFS = ['BUFx24_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx12_ASAP7_75t_R',
               'BUFx10_ASAP7_75t_R', 'BUFx8_ASAP7_75t_R']


def read_sinks(geo):
    op = gzip.open if str(geo).endswith('.gz') else open
    lines = list(op(geo, 'rt'))
    return lines, [l for l in lines if l.startswith('SINK')]


def equal_y_groups(sinks, k):
    s = sorted(sinks, key=lambda p: (p[1], p[0], p[2]))
    n = len(s)
    return [s[(i * n) // k:((i + 1) * n) // k] for i in range(k)]


def reach_minimax(mz, hub, reach, children):
    """Legal node site with maze distance <= reach from the parent hub (so the edge can be padded to exactly the level
    length) minimising the max (then sum) maze distance to its children.  Deterministic full-grid search."""
    Dh = mz.bfs(hub); Dc = [mz.bfs(c) for c in children]; lim = int(reach / mz.G + 1e-9); best = None
    for i in range(mz.NX + 1):
        for j in range(mz.NY + 1):
            if Dh[i][j] < 0 or Dh[i][j] > lim or not mz.site_ok(i, j): continue
            ds = [D[i][j] for D in Dc]
            if min(ds) < 0: continue
            v = (max(ds), sum(ds), i, j)
            if best is None or v < best[0]: best = (v, (i, j))
    return best[1]


def graft_strip(P, strip, n_l3=2, n_l4=4):
    """Add the dedicated strip branch to plan P in place.  n_l3 L3 edges per W L2 node (south half -> T00, north half
    -> T01), n_l4 L4 leaves per strip L3 node.  Returns a report dict."""
    mz, T, K = P['mz'], P['T'], P['K']
    halves = equal_y_groups(strip, 2)
    rep = dict(l3_edges=[], l4_edges=[], leaves={})
    folded_driver = {}
    for n in P['nodes']:
        if n[4] == 'rep' or n[4] == 'branch':
            pass
    # driver of a folded L2 node = the last cell of its L2 edge (T00_r<K-2> or T00_br when K==1)
    def last_driver(edge, k):
        return edge + ('_r%d' % (k - 2) if k > 1 else '_br')
    for side, (l2, half) in enumerate(zip(('T00', 'T01'), halves)):
        par_drv = last_driver(l2, K[1])
        g2 = (0, side)
        hub = P['site'][g2]
        nsib = P['splits'][2]
        for a, grp in enumerate(equal_y_groups(half, n_l3)):
            idx = nsib + a
            e3 = l2 + 'abcdefgh'[a]          # letter suffix: never collides with the digit-named main nodes
            leaves = equal_y_groups(grp, n_l4)
            lsite = [mz.cell((sum(p[0] for p in L) / len(L), sum(p[1] for p in L) / len(L))) for L in leaves]
            cx = round(sum(c[0] for c in lsite) / len(lsite)); cy = round(sum(c[1] for c in lsite) / len(lsite))
            off = mz.cell((mz.xy(hub)[0], mz.xy(hub)[1] + (idx - (nsib - 1) / 2) * 1.08))
            site3 = reach_minimax(mz, off, T[2], lsite)     # reach from the branch buffer cell (edge start)
            d = mz.md(off, site3)
            if d > T[2] + 1e-6:
                raise SystemExit('strip L3 node %s at %s is %.2f um from %s > T3 %.2f: no equal-length edge' %
                                 (e3, mz.xy(site3), d, l2, T[2]))
            P['nodes'].append((e3 + '_br', par_drv, off, H.BIG, 'branch'))
            pts = H.exact_points(mz, off, site3, T[2], K[2]); prev = e3 + '_br'; chain = [off] + pts + [site3]
            for i, c in enumerate(pts):
                nm = e3 + '_r%d' % i; P['nodes'].append((nm, prev, c, H.REP, 'rep')); prev = nm
            segs = [mz.md(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]
            P['wires'].append(dict(level=3, edge=e3, segs=segs, cells=[mz.path(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]))
            P['land'][prev] = (segs[-1], e3)
            rep['l3_edges'].append(dict(edge=e3, parent=l2, node_xy=mz.xy(site3), straight_um=round(d, 2), len_um=round(sum(segs), 2)))
            for j, (L, lc) in enumerate(zip(leaves, lsite)):
                e4 = e3 + str(j)
                off4 = mz.cell((mz.xy(site3)[0], mz.xy(site3)[1] + (j - (n_l4 - 1) / 2) * 1.08))
                P['nodes'].append((e4 + '_br', prev, off4, H.BIG, 'branch'))
                pts4 = H.exact_points(mz, off4, lc, T[3], K[3]); p4 = e4 + '_br'; ch4 = [off4] + pts4 + [lc]
                for i, c in enumerate(pts4):
                    nm = e4 + '_r%d' % i; P['nodes'].append((nm, p4, c, H.REP, 'rep')); p4 = nm
                segs4 = [mz.md(ch4[i], ch4[i + 1]) for i in range(len(ch4) - 1)]
                if sum(segs4) > T[3] + 1e-6:
                    print('NOTE strip L4 edge %s %.2f > main T4 max %.2f (L4 is natural length on every edge)' % (e4, sum(segs4), T[3]), flush=True)
                P['wires'].append(dict(level=4, edge=e4, segs=segs4, cells=[mz.path(ch4[i], ch4[i + 1]) for i in range(len(ch4) - 1)]))
                P['nodes'].append((e4, p4, lc, H.BIG, 'leaf'))
                P['leafsinks'][e4] = L
                rep['l4_edges'].append(dict(edge=e4, len_um=round(sum(segs4), 2)))
    return rep


def split_long_leaves(P, limit_um, skip=()):
    """GEOM-7 (1): every main leaf whose driver->farthest-sink spread exceeds limit_um is split (equal-count k-means,
    H.split) into k sibling leaves on the SAME L3 driver (same level, same stage count, natural L4 length like every L4
    edge); the leaf driver of each part sits at its part's centroid.  k grows until every part is within the limit."""
    mz = P['mz']; out = []
    sp = leaf_spread(P)
    node = {n[0]: n for n in P['nodes']}
    for u in sorted(sp):
        if u in skip or sp[u] <= limit_um:
            continue
        sinks = P['leafsinks'][u]; br = node[u][1]; drv = node[br][1]
        for k in range(2, 6):
            parts = H.split(sinks, k)
            cells = [mz.cell((sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g))) for g in parts]
            spr = [max(abs(s_[0] - mz.xy(c)[0]) + abs(s_[1] - mz.xy(c)[1]) for s_ in g) for g, c in zip(parts, cells)]
            if max(spr) <= limit_um:
                break
        nsib = sum(1 for n in P['nodes'] if n[4] == 'branch' and n[1] == drv)
        hub = node[br][2]
        taken = {n[0] for n in P['nodes']}
        free = [u[:-1] + ch for ch in 'pqrstuvwxyz' if u[:-1] + ch not in taken]
        names = [u] + free[:k - 1]
        for i, (nm, g, c) in enumerate(zip(names, parts, cells)):
            if i == 0:
                bcell = node[br][2]
                P['nodes'] = [(n[0], n[1], c if n[0] == u else n[2], n[3], n[4]) for n in P['nodes']]
                P['wires'] = [w for w in P['wires'] if w['edge'] != u]
            else:
                bcell = mz.cell((mz.xy(hub)[0], mz.xy(hub)[1] + (nsib + i - 1) * 1.08))
                P['nodes'].append((nm + '_br', drv, bcell, H.BIG, 'branch'))
                P['nodes'].append((nm, nm + '_br', c, H.BIG, 'leaf'))
            P['wires'].append(dict(level=4, edge=nm, segs=[mz.md(bcell, c)], cells=[mz.path(bcell, c)]))
            P['leafsinks'][nm] = g
        out.append(dict(leaf=u, spread_um=sp[u], parts=names, part_spread_um=[round(x, 2) for x in spr],
                        part_sinks=[len(g) for g in parts]))
    # parents must precede children in nodes order (converter / core_infra requirement)
    order, seen, rest = [], set(), list(P['nodes'])
    while rest:
        nxt = [n for n in rest if n[1] is None or n[1] in seen]
        if not nxt:
            raise SystemExit('cycle in plan nodes')
        for n in nxt:
            order.append(n); seen.add(n[0])
        rest = [n for n in rest if n[0] not in seen]
    P['nodes'] = order
    return out


def leaf_spread(P):
    mz = P['mz']; pos = {n[0]: mz.xy(n[2]) for n in P['nodes']}
    return {u: round(max(abs(s[0] - pos[u][0]) + abs(s[1] - pos[u][1]) for s in v), 2) for u, v in P['leafsinks'].items()}


def leaf_mst(P):
    mz = P['mz']; pos = {n[0]: mz.xy(n[2]) for n in P['nodes']}; out = {}
    for u, v in P['leafsinks'].items():
        pts = [pos[u]] + [s[:2] for s in v]; par, order = H.mst_edges(pts)
        out[u] = round(sum(abs(pts[i][0] - pts[par[i]][0]) + abs(pts[i][1] - pts[par[i]][1]) for i in order[1:]), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('geo'); ap.add_argument('--libtt', required=True); ap.add_argument('--libff', required=True)
    ap.add_argument('--config', required=True, help='R7 config json (list); the named entry is used')
    ap.add_argument('--name', default='F1_s70_ndr_buf_d1')
    ap.add_argument('--splits', default='2,2,8,8'); ap.add_argument('--smax', type=float, default=70.0)
    ap.add_argument('--strip-l3', type=int, default=2); ap.add_argument('--strip-l4', type=int, default=4)
    ap.add_argument('--bufs', choices=('gating', 'r7'), default='gating')
    ap.add_argument('--leaf-limit', type=float, default=35.0, help='split main leaves with spread > this (um); 0 = off')
    ap.add_argument('--rc', default='0.8,0.9'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.bufs == 'gating':
        M7.BUFS = list(GATING_BUFS)
    lines, sl = read_sinks(a.geo)
    strip_lines = [l for l in sl if float(l.split()[1]) < STRIP_X]
    main_geo = tempfile.NamedTemporaryFile('w', suffix='.geo', delete=False)
    main_geo.write(''.join(l for l in lines if not (l.startswith('SINK') and float(l.split()[1]) < STRIP_X))); main_geo.close()
    strip = []
    for l in strip_lines:
        f = l.split(); strip.append((float(f[1]), float(f[2]), f[4], f[5], f[3]))
    cf = [x for x in json.loads(Path(a.config).read_text()) if x['name'] == a.name][0]
    P = H.plan(main_geo.name, [int(x) for x in a.splits.split(',')], a.smax, [])
    graft = graft_strip(P, strip, a.strip_l3, a.strip_l4)
    strip_names = {e['edge'] for e in graft['l4_edges']}
    graft['split_leaves'] = split_long_leaves(P, a.leaf_limit, skip=strip_names) if a.leaf_limit > 0 else []
    kr, kc = map(float, a.rc.split(','))
    r = 0.5 * (1.80365e-2 + 1.89935e-2) * kr; c = 0.5 * (1.78475e-1 + 1.64264e-1) * kc
    cells = sorted(set(M7.BUFS + M7.INVS + GATING_BUFS + [H.REP, H.BIG]))
    libs = {'TT': H.lib_cells(a.libtt, cells), 'FF': H.lib_cells(a.libff, cells)}
    inv = M7.apply_masters(P, cf.get('masters', {}))
    if any(k % 2 for k in inv):
        raise SystemExit('odd inverter count %s' % inv)
    wc = {int(k): v for k, v in cf.get('wire', {}).items()}
    sized = M7.size_d1(P, libs, r, c, wc)
    res, st = M7.model_x(P, libs, r, c, wc)
    g = vars(M7); keep = (g['NDR_C'], g['NDR_R'], g['LEAF_NDR']); variants = []
    for v in cf.get('variants', []):
        g['NDR_C'], g['NDR_R'], g['LEAF_NDR'] = v.get('ndr_c', keep[0]), v.get('ndr_r', keep[1]), v.get('leaf_ndr', keep[2])
        vkr, vkc = map(float, v.get('rc', a.rc).split(','))
        vres, _ = M7.model_x(P, libs, 0.5 * (1.80365e-2 + 1.89935e-2) * vkr, 0.5 * (1.78475e-1 + 1.64264e-1) * vkc, wc)
        variants.append(dict(v, TT={k: vres['TT'][k] for k in ('mean', 'window', 'sink_min', 'sink_max', 'leaf_out_slew_max')},
                             FF={k: vres['FF'][k] for k in ('mean', 'window', 'sink_min', 'sink_max', 'leaf_out_slew_max')}))
        print('  variant', v['name'], 'TT', vres['TT']['mean'], 'w', vres['TT']['window'], 'FF', vres['FF']['mean'], 'w', vres['FF']['window'], flush=True)
    g['NDR_C'], g['NDR_R'], g['LEAF_NDR'] = keep
    # strip-leaf arrivals (TT) vs the rest, from the same model run
    par = {n[0]: n[1] for n in P['nodes']}; depths = set()
    for n in P['nodes']:
        if n[4] == 'leaf':
            d = 1; u = n[0]
            while par[u]: u = par[u]; d += 1
            depths.add(d)
    mz = P['mz']
    def corners(cs):
        pts = [mz.xy(x) for x in cs]; kp = [pts[0]]
        for i in range(1, len(pts) - 1):
            if (pts[i][0] - kp[-1][0]) * (pts[i + 1][1] - pts[i][1]) != (pts[i][1] - kp[-1][1]) * (pts[i + 1][0] - pts[i][0]): kp.append(pts[i])
        return kp + [pts[-1]]
    spread = leaf_spread(P); mst = leaf_mst(P)
    strip_leaves = sorted(e['edge'] for e in graft['l4_edges'])
    lvl_len = collections.defaultdict(list)
    for w in P['wires']: lvl_len[w['level']].append(round(sum(w['segs']), 2))
    rec = dict(name=a.name + '_strip', base_config=a.name, splits=a.splits, smax=a.smax, bufs=a.bufs, wire=cf.get('wire'),
               strip=dict(x_lt_um=STRIP_X, sinks=len(strip), l3_per_w_l2=a.strip_l3, l4_per_l3=a.strip_l4, **graft),
               level_len_um=[round(x, 2) for x in P['T']], level_len_range={l: [min(v), max(v), len(v)] for l, v in sorted(lvl_len.items())},
               repeaters_per_edge=[k - 1 for k in P['K']], stages=sorted(depths), inv_per_path=inv, n_cells=len(P['nodes']),
               sized_masters={'%s:%s' % k: v for k, v in sorted(sized.items())},
               frozen_masters={n[0]: n[3] for n in P['nodes']}, TT=res['TT'], FF=res['FF'], stage_TT=st['TT'], variants=variants,
               entry=mz.xy(P['ent']), core=list(mz.core), maze_g_um=mz.G,
               nodes_xy=[(n[0], n[1], mz.xy(n[2]), n[3], n[4]) for n in P['nodes']],
               wire_paths=[dict(level=w['level'], edge=w['edge'], segs=[round(x, 2) for x in w['segs']], paths=[corners(cs) for cs in w['cells']]) for w in P['wires']],
               leaf_members={u: len(v) for u, v in P['leafsinks'].items()},
               leaf_sinks={u: ['%s/%s' % (s[2], s[3]) for s in v] for u, v in P['leafsinks'].items()},
               leaf_spread_um=spread, leaf_mst_um=mst,
               leaf_spread_max=dict(all=max(spread.values()), strip=max(spread[u] for u in strip_leaves),
                                    main=max(v for u, v in spread.items() if u not in strip_leaves),
                                    n_gt_40=sum(v > 40 for v in spread.values()), n_gt_30=sum(v > 30 for v in spread.values()),
                                    top=sorted(spread.items(), key=lambda kv: -kv[1])[:8]),
               model='R7 predictor chain (l0r_r7_model.model_x): ASAP7 NLDM + Elmore, setRC M4/M5 x rc_cal, NDR2W R x0.5 C x1.25; PLAN MODEL, UNCHECKED')
    # per-leaf TT mean for the strip vs main
    M7.model_x(P, {'TT': libs['TT']}, r, c, wc)
    Path(a.out).write_text(json.dumps([rec], indent=1))
    print(rec['name'], 'stages', rec['stages'], 'TT', res['TT']['mean'], 'w', res['TT']['window'], 'FF', res['FF']['mean'], 'w', res['FF']['window'],
          'slew', res['TT']['leaf_slew_in_max'], res['TT']['leaf_out_slew_max'], 'spread', rec['leaf_spread_max'], 'sized', rec['sized_masters'],
          'lvl', rec['level_len_range'], flush=True)


if __name__ == '__main__':
    main()

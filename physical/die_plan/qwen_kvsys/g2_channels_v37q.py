#!/usr/bin/env python3
"""KV-P7-V38 10-23: per-gap channel-demand table (GEOM-REVIEW7 MACRO-BOUND rule) for partition types with hard cores.

Model (read-only estimate, no P&R):
  flows   the bound partition netlist (binder3 rtl/<type>_part.sv): every net bit, with ot_dp_st / ot_dp_dly station
          chains passed through (d[i] == q[i]), so ft slots and pin-register stations become one in->out net.  Ends:
          hard-core pins (the core's pins_file pin of that bit, after the core orient), partition buses (the bit's
          slot inside its type-frame face window), glue leaves (bits-weighted centroid of their non-glue partners, the
          place a std-cell placer puts them).  A net with k ends is cut into its Manhattan MST edges.
  routing 8.64-um grid; channel cells carry one horizontal + one vertical layer pair (M4+M6 H / M5+M7 V = 36.4 tracks
          per um each way), core cells only M6 / M7 (15.6 tracks per um; closed / planned cores obstruct M1-M5, e.g. the
          pv_join LEF OBS M1-M5).  Negotiated congestion: 4 rounds of rip-up / re-route of every edge (scipy
          Dijkstra, cost = 1 + history + 8 * max(0, use / cap - 0.5)^2 per cell).
  gaps    every rectangle between two facing cores (channel / row gap) and between a core and a type face (band);
          demand = the worst cross-section across the gap's length (bits on the cut line through the gap), capacity =
          gap width x 36.4 tracks / um; ratio <= 0.6 is the rule.  Over-core M6/M7: worst cell use / cap is reported.
usage: g2_channels_v37q.py PLAN_DIR RTL_DIR OUT.json [type,type... | all (default: every hg/hgi/pc/pv type)]"""
import collections
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

QD = Path(__file__).resolve().parent
sys.path.insert(0, str(QD))
sys.path.insert(0, str(QD.parents[2] / 'tools/die_plan'))
import core_pins_v37p as CP   # noqa: E402
import check as C             # noqa: E402
import schema as S            # noqa: E402
from rtlnet import Net        # noqa: E402

CELL = 8.64
TR_CH = 36.4      # tracks / um, one direction, channel (M4+M6 or M5+M7)
TR_CORE = 15.6    # tracks / um, one direction, over a core (M6 or M7)
RULE = 0.6
PIECE = 64       # bits per routed piece


def windows(P, tn):
    """{bus: (face, lo, hi)} type-frame windows (die port windows mapped through the instance orient)."""
    out = {}
    insts = sorted(n for n, p in P.parts.items() if p['type'] == tn)
    for pr in P.ports.values():
        if 'window_um' not in pr or 'face' not in pr:
            continue
        for side in ('src', 'dst'):
            inst = pr[side]['part']
            if inst not in insts or pr[side]['bus'] in out:
                continue
            df = pr['face'] if side == 'src' or pr['src']['part'] == C.DIE_PART else C.OPP[pr['face']]
            x0, y0, x1, y1 = P.rect(inst)
            a, b = pr['window_um']
            if df in 'EW':
                p1, p2 = P.to_type(inst, (x0 if df == 'W' else x1, a)), P.to_type(inst, (x0 if df == 'W' else x1, b))
            else:
                p1, p2 = P.to_type(inst, (a, y0 if df == 'S' else y1)), P.to_type(inst, (b, y0 if df == 'S' else y1))
            f = P.type_face(inst, df)
            lo, hi = sorted([p1[1], p2[1]] if f in 'EW' else [p1[0], p2[0]])
            out[pr[side]['bus']] = (f, lo, hi)
    return out


def endpoints(P, raw, rtl, tn, plan_dir):
    t = raw['partition_types'][tn]
    W, H = t['outline_um']
    net = Net(CP.rtl_file(rtl, tn))
    g = net.graph()
    wins = windows(P, tn)
    r2c, pinpos, ccent = {}, {}, {}
    for h in t.get('hard_cores', []):
        ms, pre = CP.members(t, h)
        cw, ch = h['outline_um']
        dx, dy = h.get('track_offset_um', [0, 0])
        X0, Y0 = h['origin_um'][0] + dx, h['origin_um'][1] + dy
        ccent[h['inst']] = (X0 + cw / 2, Y0 + ch / 2)
        pp = {}
        try:
            for nm, _ln, x, y in C.core_pins(h, plan_dir):
                tx, ty = C._orient_pt(h.get('orient', 'R0'), cw, ch, x, y)
                fc = min([(tx, 'W'), (cw - tx, 'E'), (ty, 'S'), (ch - ty, 'N')])[1]
                ox, oy = dict(W=(-0.75, 0), E=(0.75, 0), S=(0, -0.75), N=(0, 0.75))[fc]   # the cell outside the face
                pp[nm] = (X0 + tx + ox * CELL, Y0 + ty + oy * CELL)
        except (OSError, KeyError, ValueError):
            pass
        pinpos[h['inst']] = pp
        for i in ms:
            r2c['u_' + i.replace('__', '_')] = (h['inst'], CP.rel(i, pre, h))
    par = {}

    def f(x):
        while par.get(x, x) != x:
            x = par[x]
        return x
    st = {i for i, (m, _) in net.insts.items() if m.startswith('ot_dp_st') or m.startswith('ot_dp_dly')}
    for i in st:
        _m, pm = net.insts[i]
        if 'd' in pm and 'q' in pm:
            for a, b in zip(net.bits(pm['d'])[::-1], net.bits(pm['q'])[::-1]):
                if a and b:
                    par[f(net.find(a))] = f(net.find(b))
    groups = collections.defaultdict(set)
    for nb, ends in g.items():
        for e in ends:
            if e[0] in st:
                continue
            if CP.CLKRST.match(e[1]) and e[0] != '<port>':
                continue
            groups[f(nb)].add(e)
    # glue centroids (2 passes)
    glue_pts = collections.defaultdict(list)
    nets = []
    for k, ends in groups.items():
        pts, glue = [], []
        for inst, port, bit in ends:
            if inst == '<port>':
                if port in wins:
                    fc, lo, hi = wins[port]
                    wd = max(1, net.width.get(port, 1))
                    u = lo + (bit + 0.5) / wd * (hi - lo)
                    pts.append(('b', dict(N=(u, H), S=(u, 0.0), E=(W, u), W=(0.0, u))[fc]))
            elif inst in r2c:
                ci, rn = r2c[inst]
                nm = f'{rn}__{port}[{bit}]' if rn else f'{port}[{bit}]'
                pts.append(('c' + ci, pinpos[ci].get(nm, ccent[ci])))
            else:
                glue.append(inst)
        # one point per core: a pin hit when the core has one (internal member ports carry no pin)
        best = {}
        for kk, q in pts:
            if kk == 'b':
                best[('b', q)] = (q, True)
            else:
                hit = q != ccent[kk[1:]]
                if kk not in best or (hit and not best[kk][1]):
                    best[kk] = (q, hit)
        pp = [q for q, _h in best.values()]
        if len(pp) + len(set(glue)) < 2:
            continue
        nets.append((pp, sorted(set(glue))))
        for gl in set(glue):
            glue_pts[gl] += pp
    gpos = {gl: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) if v else (W / 2, H / 2)
            for gl, v in glue_pts.items()}
    for gl in [g_ for g_ in set(x for _, gls in nets for x in gls) if g_ not in gpos]:
        gpos[gl] = (W / 2, H / 2)
    # glue with no fixed partner: centroid of glue partners
    for _ in range(2):
        acc = collections.defaultdict(list)
        for pp, gls in nets:
            if not pp:
                for gl in gls:
                    acc[gl] += [gpos[o] for o in gls if o != gl]
        for gl, v in acc.items():
            if v and not glue_pts.get(gl):
                gpos[gl] = (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
    edges = collections.Counter()
    nx, ny = int(math.ceil(W / CELL)), int(math.ceil(H / CELL))
    boxes = [(h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0],
              h['origin_um'][1] + h['outline_um'][1]) for h in t.get('hard_cores', [])]
    for gl, (x, y) in list(gpos.items()):      # glue is std-cell logic: snap it out of a core to the nearest face
        for x0, y0, x1, y1 in boxes:
            if x0 < x < x1 and y0 < y < y1:
                d = min((x - x0, 'W'), (x1 - x, 'E'), (y - y0, 'S'), (y1 - y, 'N'))[1]
                gpos[gl] = dict(W=(x0 - CELL, y), E=(x1 + CELL, y), S=(x, y0 - CELL), N=(x, y1 + CELL))[d]

    def cell(p):
        return (min(nx - 1, max(0, int(p[0] / CELL))), min(ny - 1, max(0, int(p[1] / CELL))))
    for pp, gls in nets:
        cs = sorted({cell(p) for p in pp} | {cell(gpos[gl]) for gl in gls})
        if len(cs) < 2:
            continue
        # Prim MST, Manhattan
        inn, rest = [cs[0]], set(cs[1:])
        while rest:
            best = min(((abs(a[0] - b[0]) + abs(a[1] - b[1]), a, b) for a in inn for b in rest))
            edges[(best[1], best[2])] += 1
            inn.append(best[2])
            rest.discard(best[2])
    return edges, (nx, ny), gpos, nets


def route(t, edges, dims, rounds=3, chunk=16):
    """sequential negotiated routing: each round rips up and re-routes every source chunk against the live usage."""
    nx, ny = dims
    N = nx * ny
    core = np.zeros((nx, ny), bool)
    for h in t.get('hard_cores', []):
        dx, dy = h.get('track_offset_um', [0, 0])
        x0, y0 = h['origin_um'][0] + dx, h['origin_um'][1] + dy
        x1, y1 = x0 + h['outline_um'][0], y0 + h['outline_um'][1]
        i0, i1 = int(math.ceil(x0 / CELL - 1e-6)), int(math.floor(x1 / CELL + 1e-6))
        j0, j1 = int(math.ceil(y0 / CELL - 1e-6)), int(math.floor(y1 / CELL + 1e-6))
        core[i0:i1, j0:j1] = True
    cap = (np.where(core, TR_CORE, TR_CH) * CELL).ravel()
    I, J = np.meshgrid(np.arange(nx), np.arange(ny), indexing='ij')
    idx = lambda i, j: i * ny + j   # noqa: E731
    ha, hb = idx(I[:-1], J[:-1]).ravel(), idx(I[1:], J[1:]).ravel()
    va, vb = idx(I[:, :-1], J[:, :-1]).ravel(), idx(I[:, 1:], J[:, 1:]).ravel()
    rows = np.concatenate([ha, hb, va, vb])
    cols = np.concatenate([hb, ha, vb, va])
    nh = len(ha)
    use = np.zeros((2, N))        # 0 = H, 1 = V
    hist = np.zeros((2, N))
    coref = core.ravel() * 0.3
    items = []                    # 64-bit pieces, round-robin over the bundles so a wide bundle spreads
    for (a_, b_), n in edges.items():
        k = int(math.ceil(n / PIECE))
        for i in range(k):
            items.append((i, -n, idx(*a_), idx(*b_), n / k))
    items.sort()
    paths = {}

    def lay(path, n, sgn):
        for u, v in path:
            d = 0 if abs(u - v) == ny else 1
            use[d, u] += sgn * n / 2
            use[d, v] += sgn * n / 2
    for rnd in range(rounds):
        for k in range(0, len(items), chunk):
            ch_ = items[k:k + chunk]
            for it in ch_:
                if it in paths:
                    lay(paths[it], it[4], -1)
            cst = 1 + hist + 8 * np.maximum(0, use / cap - 0.5) ** 2 + coref
            data = np.concatenate([cst[0][hb], cst[0][ha], cst[1][vb], cst[1][va]])
            Gm = csr_matrix((data, (rows, cols)), shape=(N, N))
            us = sorted({it[2] for it in ch_})
            _d, pred = dijkstra(Gm, indices=us, return_predecessors=True)
            for it in ch_:
                r, s_, b_ = us.index(it[2]), it[2], it[3]
                v, path = b_, []
                while v != s_ and v >= 0:
                    u = pred[r, v]
                    path.append((u, v))
                    v = u
                paths[it] = path
                lay(path, it[4], +1)
        hist += 0.3 * np.maximum(0, use / cap - RULE)
    return use[0].reshape(nx, ny), use[1].reshape(nx, ny), core, cap.reshape(nx, ny)


def gaps(t):
    """rectangles between facing cores and between a core and a type face: (name, x0, y0, x1, y1, axis), axis
    'V' = a vertical channel (cut lines horizontal, demand = V bits), 'H' = a horizontal gap."""
    W, H = t['outline_um']
    bx = []
    for h in t.get('hard_cores', []):
        dx, dy = h.get('track_offset_um', [0, 0])
        x0, y0 = h['origin_um'][0] + dx, h['origin_um'][1] + dy
        bx.append((h['inst'], x0, y0, x0 + h['outline_um'][0], y0 + h['outline_um'][1]))
    out = {}
    for n, x0, y0, x1, y1 in bx:
        # east neighbour / face
        cand = [(b[1], b[0]) for b in bx if b[1] >= x1 - 1e-6 and min(y1, b[4]) - max(y0, b[2]) > 1]
        xe, ne = min(cand) if cand else (W, 'face E')
        out[('V', round(x1, 2), round(xe, 2), n, ne)] = ('V', x1, y0, xe, y1)
        if not any(b[3] <= x0 + 1e-6 and min(y1, b[4]) - max(y0, b[2]) > 1 for b in bx):
            out[('V', 0, round(x0, 2), 'face W', n)] = ('V', 0.0, y0, x0, y1)
        cand = [(b[2], b[0]) for b in bx if b[2] >= y1 - 1e-6 and min(x1, b[3]) - max(x0, b[1]) > 1]
        yn, nn = min(cand) if cand else (H, 'face N')
        out[('H', round(y1, 2), round(yn, 2), n, nn)] = ('H', x0, y1, x1, yn)
        if not any(b[4] <= y0 + 1e-6 and min(x1, b[3]) - max(x0, b[1]) > 1 for b in bx):
            out[('H', 0, round(y0, 2), 'face S', n)] = ('H', x0, 0.0, x1, y0)
    res = []
    for k, (ax, x0, y0, x1, y1) in out.items():
        res.append((f'{k[3]} | {k[4]}', x0, y0, x1, y1, ax))
    return res


def table(t, use_h, use_v, core):
    rows = []
    for nm, x0, y0, x1, y1, ax in gaps(t):
        i0, i1 = int(round(x0 / CELL)), int(round(x1 / CELL))
        j0, j1 = int(round(y0 / CELL)), int(round(y1 / CELL))
        if i1 <= i0 or j1 <= j0:
            continue
        if ax == 'V':
            wd = x1 - x0
            sl = use_v[i0:i1, j0:j1].sum(axis=0)
        else:
            wd = y1 - y0
            sl = use_h[i0:i1, j0:j1].sum(axis=1)
        dem = float(sl.max()) if sl.size else 0.0
        trk = wd * TR_CH
        rows.append(dict(gap=nm, axis=ax, box=[round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                         width_um=round(wd, 2), bits=round(dem), tracks=round(trk), ratio=round(dem / trk, 3)))
    rows.sort(key=lambda r: -r['ratio'])
    capc = TR_CORE * CELL
    oc = max(float((use_h[core] / capc).max(initial=0)), float((use_v[core] / capc).max(initial=0)))
    return rows, round(oc, 3)


def one(args):
    pdir, rtl, outf, tn = args
    raw = json.load(open(pdir / 'die_plan.json'))
    P = S.Plan(raw)
    t = raw['partition_types'][tn]
    edges, dims, _g, _n = endpoints(P, raw, rtl, tn, pdir)
    uh, uv, core, _cap = route(t, edges, dims)
    rows, oc = table(t, uh, uv, core)
    np.savez_compressed(Path(outf).with_suffix('').as_posix() + f'_{tn}.npz', h=uh, v=uv, core=core)
    nbad = sum(r['ratio'] > RULE for r in rows)
    sys.stderr.write(f'{tn}: {len(rows)} gaps, worst {rows[0]["gap"]} {rows[0]["bits"]} b / {rows[0]["tracks"]} tr = '
                     f'{rows[0]["ratio"]}; over rule {nbad}; over-core M6/M7 max {oc}\n')
    return tn, dict(gaps=rows, over_core_m6m7_max=oc, gaps_over_rule=nbad, edges=len(edges),
                    bits_routed=int(sum(edges.values())))


def main():
    from multiprocessing import Pool
    pdir, rtl, outf = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    raw = json.load(open(pdir / 'die_plan.json'))
    want = sys.argv[4] if len(sys.argv) > 4 else 'all'
    tns = [tn for tn, t in raw['partition_types'].items() if t.get('hard_cores') and
           re.match(r'kv3_(hgi?|pc|pv)(_|$)', tn)] if want == 'all' else want.split(',')
    with Pool(min(12, len(tns))) as pool:
        res = dict(pool.map(one, [(pdir, rtl, outf, tn) for tn in tns]))
    json.dump(dict(schema='opentallas.kv.g2_channels.v1', model=__doc__.split('usage')[0].strip(), rule=RULE,
                   types=res), open(outf, 'w'), indent=1)


if __name__ == '__main__':
    main()

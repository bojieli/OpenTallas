#!/usr/bin/env python3
"""S81-CORE-LAT-R7: plan-computed driver sizing (METHODOLOGY 12.8 d1) + wire class per level on the R6 equal-structure
core H-tree (tools/die_plan/core_infra_htree.plan).  PLAN MODEL ONLY, deterministic, no measured timing input.

Same predictor chain as R6 (ASAP7 NLDM + Elmore, setRC stock M4/M5 mean x rc_cal 0.8/0.9, leaf nets as MST), extended with:
  * per-kind/level cell master (BUF or INV pairs) chosen BY THE PLAN from geometry + loads (sweep below is the plan search;
    the frozen choice is written to the plan json), polarity checked: every root->sink path must have an even INV count;
  * per-level wire class: 'std' (setRC x cal) or 'ndr2w' (2x width M4/M5: R x 0.5, C x NDR_C) for trunk edges;
  * repeaters per level from geometry (ceil(T/smax_l)), >=1 waypoint wherever the level needs a detour (equal length).
"""
import argparse, collections, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools' / 'die_plan'))
import core_infra_htree as H

NDR_C = 1.25   # 2W/2S clock NDR unit C vs default (plate x2 with 2S coupling relief); conservative for M4/M5
NDR_R = 0.5    # 2W unit R vs default
LEAF_NDR = False  # True: the leaf (driver->sinks) nets carry the NDR too (core_infra ot_ci_clock_ndr applies it to every tree net)


def lvl_of(name):
    if name == 'root': return 0
    return len(name[1:].split('_')[0])


def model_x(P, libs, r, c, wire_cls, ffc=H.FFC):
    """R6 model() with per-wire (r,c) by edge level and arbitrary masters.  wire_cls[l] in {'std','ndr2w'} for l=1..depth."""
    mz = P['mz']; nodes = P['nodes']; ch = collections.defaultdict(list)
    for n in nodes:
        if n[1]: ch[n[1]].append(n)
    pos = {n[0]: mz.xy(n[2]) for n in nodes}; mst = {n[0]: n[3] for n in nodes}
    wirelen = {}
    for w in P['wires']:
        e = w['edge']; segs = w['segs']
        names = [e + '_br'] + [e + '_r%d' % i for i in range(len(segs) - 1)] + [e]
        for i in range(len(segs)): wirelen[names[i + 1]] = segs[i]
    pos_hub = {w['edge']: mz.xy(w['cells'][-1][-1]) for w in P['wires']}
    def rc(l):
        return (r * NDR_R, c * NDR_C) if wire_cls.get(l, 'std') == 'ndr2w' else (r, c)
    res = {}; stage = {}; P['_int'] = {}
    for corner, L in libs.items():
        arr = {'root': 0.0}; slew = {'root': 0.0}; leafarr = {}; cd = {}; drv = {}
        stack = ['root']
        while stack:
            u = stack.pop(); kids = ch.get(u, []); lib = L[mst[u]]
            if kids and u in P['land']:
                seg, hub = P['land'][u]; hp = pos_hub[hub]; rr, cc = rc(lvl_of(hub))
                stub = [abs(pos[k[0]][0] - hp[0]) + abs(pos[k[0]][1] - hp[1]) for k in kids]
                Cl = sum(L[k[3]]['cin'] for k in kids) + cc * sum(stub); Ct = cc * seg + Cl
                d = 0.5 * (H.interp(lib['rise'], slew[u], Ct) + H.interp(lib['fall'], slew[u], Ct))
                so = 0.5 * (H.interp(lib['trise'], slew[u], Ct) + H.interp(lib['tfall'], slew[u], Ct))
                el = rr * seg * (cc * seg / 2 + Cl)
                drv[u] = (Ct, [(k[0], el + rr * sl_ * L[k[3]]['cin']) for k, sl_ in zip(kids, stub)])
                for k, sl_ in zip(kids, stub):
                    e2 = el + rr * sl_ * L[k[3]]['cin']
                    arr[k[0]] = arr[u] + d + e2; slew[k[0]] = math.hypot(so, 2.2 * e2); stack.append(k[0])
                    cd[k[0]] = (round(d, 2), round(e2, 2), round(so, 1))
                kids = []
            if kids:
                br = []
                for k in kids:
                    w = wirelen.get(k[0], abs(pos[k[0]][0] - pos[u][0]) + abs(pos[k[0]][1] - pos[u][1]))
                    br.append((w, L[k[3]]['cin'], rc(lvl_of(k[0]))))
                far = [b for b in br if b[0] >= 3.0]
                if len(far) > 1: raise ValueError('shared wire at ' + u)
                Ct = sum(b[2][1] * b[0] + b[1] for b in br)
                d = 0.5 * (H.interp(lib['rise'], slew[u], Ct) + H.interp(lib['fall'], slew[u], Ct))
                so = 0.5 * (H.interp(lib['trise'], slew[u], Ct) + H.interp(lib['tfall'], slew[u], Ct))
                drv[u] = (Ct, [(k[0], rr * w * (cc * w / 2 + cp)) for (w, cp, (rr, cc)), k in zip(br, kids)])
                for (w, cp, (rr, cc)), k in zip(br, kids):
                    el = rr * w * (cc * w / 2 + cp)
                    arr[k[0]] = arr[u] + d + el; slew[k[0]] = math.hypot(so, 2.2 * el); stack.append(k[0])
                    cd[k[0]] = (round(d, 2), round(el, 2), round(so, 1))
            if u in P['leafsinks']:
                ls = P['leafsinks'][u]; pts = [pos[u]] + [s[:2] for s in ls]
                par, order = H.mst_edges(pts); sub = [0.0] + [ffc[corner] for _ in ls]; ec = [0.0] * len(pts); er = [0.0] * len(pts)
                lr, lc = (r * NDR_R, c * NDR_C) if LEAF_NDR else (r, c)
                for v in order[1:]:
                    e = abs(pts[v][0] - pts[par[v]][0]) + abs(pts[v][1] - pts[par[v]][1]); ec[v] = lc * e; er[v] = lr * e
                for v in reversed(order[1:]): sub[par[v]] += sub[v] + ec[v]
                Ct = sub[0]
                d = 0.5 * (H.interp(lib['rise'], slew[u], Ct) + H.interp(lib['fall'], slew[u], Ct))
                so = 0.5 * (H.interp(lib['trise'], slew[u], Ct) + H.interp(lib['tfall'], slew[u], Ct))
                t = [0.0] * len(pts)
                for v in order[1:]: t[v] = t[par[v]] + er[v] * (sub[v] - ec[v] / 2)
                vals = [arr[u] + d + x for x in t[1:]]
                drv[u] = (Ct, [('#sinks', sum(t[1:]) / len(ls))])
                leafarr[u] = (sum(vals) / len(vals), min(vals), max(vals), Ct, d, so, slew[u])
        P['_int'][corner] = dict(arr=dict(arr), slew=dict(slew), drv=drv)
        means = [v[0] for v in leafarr.values()]; allv = []
        for u, v in leafarr.items(): allv += [v[1], v[2]]
        n_s = sum(len(P['leafsinks'][u]) for u in leafarr)
        mean = sum(leafarr[u][0] * len(P['leafsinks'][u]) for u in leafarr) / n_s
        res[corner] = dict(mean=round(mean, 2), leaf_mean_min=round(min(means), 2), leaf_mean_max=round(max(means), 2),
                           window=round(max(means) - min(means), 2), sink_min=round(min(allv), 2), sink_max=round(max(allv), 2),
                           leaf_slew_in_max=round(max(v[6] for v in leafarr.values()), 1),
                           leaf_ct_ff=[round(min(v[3] for v in leafarr.values()), 1), round(max(v[3] for v in leafarr.values()), 1)],
                           leaf_out_slew_max=round(max(v[5] for v in leafarr.values()), 1))
        # stage breakdown along the worst (latest) leaf path
        worst = max(leafarr, key=lambda u: leafarr[u][0]); path = []; par_ = {n[0]: n[1] for n in nodes}; u = worst
        while par_[u]: path.append((u, mst[par_[u]]) + cd.get(u, ())); u = par_[u]
        stage[corner] = dict(leaf=worst, leaf_drv=[round(leafarr[worst][4], 2), round(leafarr[worst][0] - arr[worst] - leafarr[worst][4], 2)],
                             path=list(reversed(path)))
    return res, stage


BUFS = ['BUFx24_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx12_ASAP7_75t_R', 'BUFx10_ASAP7_75t_R',
        'BUFx8_ASAP7_75t_R', 'BUFx6f_ASAP7_75t_R', 'BUFx5_ASAP7_75t_R', 'BUFx4f_ASAP7_75t_R']
INVS = ['INVx13_ASAP7_75t_R', 'INVx11_ASAP7_75t_R', 'INVx8_ASAP7_75t_R', 'INVx6_ASAP7_75t_R', 'INVx5_ASAP7_75t_R', 'INVx4_ASAP7_75t_R']
SLEW_MAX = 60.0   # ps, plan clock-slew ceiling for any sized driver output (TT)


def size_d1(P, libs, r, c, wc, corner='TT', passes=2):
    """12.8 d1 plan-computed per-driver sizing: level by level (top-down), every driver of an edge at level l picks the
    master of ITS family (BUF stays BUF, INV stays INV -> polarity unchanged) whose predicted child arrival is closest to
    the level target = latest arrival any edge of that level can reach with its strongest master; the leaf drivers
    then pick the master that puts their own sink mean closest to the latest leaf's.  Inputs: plan geometry + liberty +
    loads only (no measurement); deterministic; the chosen masters are frozen in the plan json."""
    L = libs[corner]; mst = {n[0]: n for n in P['nodes']}
    kind_lv = collections.defaultdict(list)
    for n in P['nodes']:
        if n[4] in ('branch', 'rep', 'leaf'):
            pos_in_edge = 0 if n[4] == 'branch' else (1 + int(n[0].rsplit('_r', 1)[1]) if n[4] == 'rep' else 0)
            kind_lv[(1 if n[4] == 'leaf' else 0, lvl_of(n[0]), pos_in_edge)].append(n[0])
    order = sorted(kind_lv)
    for _ in range(passes):
        for key in order:
            model_x(P, {corner: L}, r, c, wc); I = P['_int'][corner]
            names = kind_lv[key]; opts = {}
            for u in names:
                fam = INVS if mst[u][3].startswith('INV') else BUFS
                Ct, ch_ = I['drv'][u]; sl = I['slew'][u]; a0 = I['arr'][u]; o = []
                for m in fam:
                    lib = L[m]
                    d = 0.5 * (H.interp(lib['rise'], sl, Ct) + H.interp(lib['fall'], sl, Ct))
                    so = 0.5 * (H.interp(lib['trise'], sl, Ct) + H.interp(lib['tfall'], sl, Ct))
                    if so > SLEW_MAX: continue
                    o.append((a0 + d + max(e for _, e in ch_), m))
                opts[u] = o
            tgt = max(min(a for a, _ in o) for o in opts.values())
            for u, o in opts.items():
                a, m = min(o, key=lambda x: (abs(x[0] - tgt), x[0]))
                n = mst[u]; mst[u] = (n[0], n[1], n[2], m, n[4])
            P['nodes'] = [mst[n[0]] for n in P['nodes']]
    return collections.Counter((n[4], n[3]) for n in P['nodes'])


def apply_masters(P, mm):
    """mm: kind->master, optional 'leaf','branch','rep','entry'; 'branchL<l>' per level overrides."""
    out = []
    for n in P['nodes']:
        k = n[4]; l = lvl_of(n[0]); m = mm.get('%sL%d' % (k, l), mm.get(k, n[3]))
        out.append((n[0], n[1], n[2], m, k))
    P['nodes'] = out
    inv = {}
    par = {n[0]: n[1] for n in out}; mst = {n[0]: n[3] for n in out}
    for n in out:
        if n[4] != 'leaf': continue
        u = n[0]; ninv = 0
        while u: ninv += mst[u].startswith('INV'); u = par[u]
        inv[ninv] = inv.get(ninv, 0) + 1
    return inv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('geo'); ap.add_argument('--libtt', required=True); ap.add_argument('--libff', required=True)
    ap.add_argument('--splits', default='2,2,8,8'); ap.add_argument('--smax', type=float, default=70.0)
    ap.add_argument('--rc', default='0.8,0.9'); ap.add_argument('--configs', required=True, help='json list of {name,masters,wire,smax?}')
    ap.add_argument('--out', required=True); ap.add_argument('--tcl', default=None, help='write the frozen plan (first d1 config) as R6 ot_ms spec Tcl')
    a = ap.parse_args()
    kr, kc = map(float, a.rc.split(','))
    r = 0.5 * (1.80365e-2 + 1.89935e-2) * kr; c = 0.5 * (1.78475e-1 + 1.64264e-1) * kc
    cells = BUFS + INVS
    libs = {'TT': H.lib_cells(a.libtt, cells), 'FF': H.lib_cells(a.libff, cells)}
    cfgs = json.loads(Path(a.configs).read_text()); out = []
    plans = {}
    for cf in cfgs:
        key = (cf.get('splits', a.splits), cf.get('smax', a.smax))
        if key not in plans:
            plans[key] = H.plan(a.geo, [int(x) for x in key[0].split(',')], key[1], [])
        import copy
        P = dict(plans[key]); P['nodes'] = list(plans[key]['nodes'])
        inv = apply_masters(P, cf.get('masters', {}))
        if any(k % 2 for k in inv): rec = dict(name=cf['name'], error='odd inverter count per path %s' % inv); out.append(rec); print(rec); continue
        wc = {int(k): v for k, v in cf.get('wire', {}).items()}
        globals()['LEAF_NDR'] = bool(cf.get('leaf_ndr', False))
        sized = size_d1(P, libs, r, c, wc) if cf.get('d1') else None
        res, st = model_x(P, libs, r, c, wc)
        variants = []
        g = globals(); keep = (g['NDR_C'], g['NDR_R'], g['LEAF_NDR'])
        for v in cf.get('variants', []):
            g['NDR_C'], g['NDR_R'], g['LEAF_NDR'] = v.get('ndr_c', keep[0]), v.get('ndr_r', keep[1]), v.get('leaf_ndr', keep[2])
            vkr, vkc = map(float, v.get('rc', a.rc).split(','))
            vr = 0.5 * (1.80365e-2 + 1.89935e-2) * vkr; vc = 0.5 * (1.78475e-1 + 1.64264e-1) * vkc
            vres, _ = model_x(P, libs, vr, vc, wc)
            variants.append(dict(v, TT={k: vres['TT'][k] for k in ('mean', 'window', 'sink_min', 'sink_max', 'leaf_out_slew_max')},
                                 FF={k: vres['FF'][k] for k in ('mean', 'window', 'sink_min', 'sink_max', 'leaf_out_slew_max')}))
            print('  variant', v, 'TT', vres['TT']['mean'], 'w', vres['TT']['window'], 'FF', vres['FF']['mean'], 'w', vres['FF']['window'], flush=True)
        g['NDR_C'], g['NDR_R'], g['LEAF_NDR'] = keep
        depths = set(); par = {n[0]: n[1] for n in P['nodes']}
        for n in P['nodes']:
            if n[4] == 'leaf':
                d = 1; u = n[0]
                while par[u]: u = par[u]; d += 1
                depths.add(d)
        rec = dict(name=cf['name'], splits=key[0], smax=key[1], masters=cf.get('masters', {}), wire=cf.get('wire', {}),
                   level_len_um=[round(x, 2) for x in P['T']], repeaters_per_edge=[k - 1 for k in P['K']], stages=sorted(depths),
                   inv_per_path=inv, n_cells=len(P['nodes']), d1=bool(cf.get('d1')),
                   sized_masters={'%s:%s' % k: v for k, v in sized.items()} if sized else None,
                   frozen_masters={n[0]: n[3] for n in P['nodes']} if cf.get('d1') else None, TT=res['TT'], FF=res['FF'], stage_TT=st['TT'], frozen_masters_variants=variants)
        if cf.get('d1'):
            mz = P['mz']
            def corners(cells):
                pts = [mz.xy(x) for x in cells]; keep = [pts[0]]
                for i in range(1, len(pts) - 1):
                    if (pts[i][0] - keep[-1][0]) * (pts[i + 1][1] - pts[i][1]) != (pts[i][1] - keep[-1][1]) * (pts[i + 1][0] - pts[i][0]): keep.append(pts[i])
                return keep + [pts[-1]]
            rec['entry'] = mz.xy(P['ent'])
            rec['nodes_xy'] = [(n[0], n[1], mz.xy(n[2]), n[3], n[4]) for n in P['nodes']]
            rec['wire_paths'] = [dict(level=w['level'], edge=w['edge'], segs=[round(x, 2) for x in w['segs']], paths=[corners(cs) for cs in w['cells']]) for w in P['wires']]
            rec['leaf_members'] = {u: len(v) for u, v in P['leafsinks'].items()}
            rec['leaf_spread_um'] = {u: round(max(abs(s_[0] - mz.xy([n for n in P['nodes'] if n[0] == u][0][2])[0]) + abs(s_[1] - mz.xy([n for n in P['nodes'] if n[0] == u][0][2])[1]) for s_ in v), 2) for u, v in P['leafsinks'].items()}
        out.append(rec)
        print(cf['name'], key, 'stages', sorted(depths), 'TT', res['TT']['mean'], 'w', res['TT']['window'], 'FF', res['FF']['mean'], 'w', res['FF']['window'],
              'slew', res['TT']['leaf_slew_in_max'], res['TT']['leaf_out_slew_max'], flush=True)
    Path(a.out).write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()

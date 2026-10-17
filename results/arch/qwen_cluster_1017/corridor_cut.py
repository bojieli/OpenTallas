#!/usr/bin/env python3
"""Q-CLUSTER corridor cut estimate for qfd_c_b16 / qfd_c_b16_dv (planning model, GRT decides).

Uses the CB generator's own geometry, tree host map and leg router (q3h_cb16_gen.py), so the legs are the ones the
RTL would build.  Adds the four bc->bco column runs, the reset run, the rs exit and (dv) the 514-b rs_i->rs_o
far-band feedthrough, then reports peak bits per corridor (vertical wires, horizontal cut) and per row-gap channel
(horizontal wires, vertical cut) against two capacity rules:

  proj : the project's die cut rule for channels (results/arch/qwen_tp8_1012/cuts.py): vertical wires M5 @ 50 % +
         M7 @ 75 %; horizontal wires M4 @ 50 % + M6 @ 75 %.  M2/M3 left to the corridor's relay/repeater cells,
         M8/M9 left to the cluster PDN + die over-flight.
  m3   : proj + M3 (36 nm) @ 50 % for verticals / M2 @ 50 % horizontals (sensitivity only).

usage: corridor_cut.py GEN.py HOSTS.json [--dv CORR[,CORR]] [--corr-w A=64.8,T=129.6,...] [--anneal N] [--json OUT]
"""
import argparse
import importlib.util
import json
import math
import random
import sys

P = argparse.ArgumentParser()
P.add_argument('gen')
P.add_argument('hosts')
P.add_argument('--dv', default='', help='corridor(s) carrying rs_i->rs_o; "T" or "A,B" (split 257+257) or "L,R"')
P.add_argument('--corr-w', default='', help='override corridor widths, e.g. T=129.6')
P.add_argument('--anneal', type=int, default=0, help='re-host the tree minimising the worst corridor util (seeds)')
P.add_argument('--iters', type=int, default=30000)
P.add_argument('--json', default='')
P.add_argument('--lat-first', action='store_true')
P.add_argument('--lat-cap', type=int, default=0)
a = P.parse_args()

spec = importlib.util.spec_from_file_location('g', a.gen)
g = importlib.util.module_from_spec(spec)
sys.argv = [a.gen]
spec.loader.exec_module(g)

# optional corridor widening: rebuild CORR / COLX / WIDTH in the generator's own order
if a.corr_w:
    over = {k: float(v) for k, v in (t.split('=') for t in a.corr_w.split(','))}
    x = 0.0
    for n in ["L", 0, "A", 1, "T", 2, "B", 3, "R"]:
        if isinstance(n, str):
            w = over.get(n, g.WIDE.get(n, g.CW))
            g.CORR[n] = (x, x + w)
            x += w
        else:
            g.COLX[n] = (x, x + g.TW)
            x += g.TW
    g.WIDTH = round(x, 4)

hosts, spare = g.load_hosts(a.hosts)
BW, DW = g.BW, g.DW
TP = {'M2': 0.036, 'M3': 0.036, 'M4': 0.048, 'M5': 0.048, 'M6': 0.064, 'M7': 0.064}


def cap(width, vertical, rule):
    if vertical:
        c = width / TP['M5'] * .5 + width / TP['M7'] * .75
        if rule == 'm3':
            c += width / TP['M3'] * .5
    else:
        c = width / TP['M4'] * .5 + width / TP['M6'] * .75
        if rule == 'm3':
            c += width / TP['M2'] * .5
    return c


def loads(host, dv):
    rs_t, bits, legs, rsx, _ = g.evaluate(host, True)
    segs = [(x['poly'], BW, 'tree') for x in legs] + [(rsx['poly'], BW, 'rs')]
    # bc -> bco column runs: full height in the column's tap corridor (two lanes in T)
    for c in range(4):
        x = g.run_x(c)
        segs.append(([(x, 0.0), (x, g.HEIGHT)], DW, 'bc'))
    # reset run (1 b) in L / T / R
    for cor in 'LTR':
        segs.append(([(g.ccx(cor), 0.0), (g.ccx(cor), g.HEIGHT)], 1, 'rst'))
    # dv feedthrough: N face -> S face, full height, split evenly over the named corridors
    if dv:
        cs = dv.split(',')
        for k, cor in enumerate(cs):
            n = BW // len(cs) + (1 if k < BW % len(cs) else 0)
            segs.append(([(g.ccx(cor), 0.0), (g.ccx(cor), g.HEIGHT)], n, 'rs_ft'))
    V = {c: {} for c in g.CORR}         # corridor -> 20-um y bin -> bits
    Vf = {c: {} for c in g.CORR}
    H = {i: {} for i in range(len(g.CHANNELS))}
    Hf = {i: {} for i in range(len(g.CHANNELS))}
    for p, n, fam in segs:
        for s, t in zip(p, p[1:]):
            if abs(s[0] - t[0]) < 1e-6 and abs(s[1] - t[1]) > 1e-6:      # vertical
                cor = next((c for c, (lo, hi) in g.CORR.items() if lo - 1e-6 <= s[0] <= hi + 1e-6), None)
                if cor is None:
                    raise SystemExit(f'vertical segment outside every corridor at x={s[0]}')
                for k in range(int(min(s[1], t[1]) // 20), int(max(s[1], t[1]) // 20)):
                    V[cor][k] = V[cor].get(k, 0) + n
                    Vf[cor].setdefault(k, {}).setdefault(fam, 0)
                    Vf[cor][k][fam] += n
            elif abs(s[1] - t[1]) < 1e-6 and abs(s[0] - t[0]) > 1e-6:    # horizontal
                ch = next((i for i, (lo, hi) in enumerate(g.CHANNELS) if lo - 1e-6 <= s[1] <= hi + 1e-6), None)
                if ch is None:
                    continue   # pin stubs inside a tile row (face to corridor), not channel load
                for k in range(int(min(s[0], t[0]) // 20), int(max(s[0], t[0]) // 20)):
                    H[ch][k] = H[ch].get(k, 0) + n
                    Hf[ch].setdefault(k, {}).setdefault(fam, 0)
                    Hf[ch][k][fam] += n
    out = {}
    for c, (lo, hi) in g.CORR.items():
        pk = max(V[c].values(), default=0)
        kk = max(V[c], key=V[c].get) if V[c] else None
        out[f'corr_{c}'] = dict(width_um=round(hi - lo, 2), peak_bits=pk, at_y=None if kk is None else kk * 20,
                                fam=Vf[c].get(kk, {}),
                                util_proj=round(pk / cap(hi - lo, True, 'proj'), 3),
                                util_m3=round(pk / cap(hi - lo, True, 'm3'), 3),
                                cap_proj=round(cap(hi - lo, True, 'proj')))
    for i, (lo, hi) in enumerate(g.CHANNELS):
        pk = max(H[i].values(), default=0)
        kk = max(H[i], key=H[i].get) if H[i] else None
        out[f'chan_{i}_y{lo:.0f}'] = dict(height_um=round(hi - lo, 2), peak_bits=pk, at_x=None if kk is None else kk * 20,
                                         fam=Hf[i].get(kk, {}),
                                         util_proj=round(pk / cap(hi - lo, False, 'proj'), 3),
                                         util_m3=round(pk / cap(hi - lo, False, 'm3'), 3),
                                         cap_proj=round(cap(hi - lo, False, 'proj')))
    worst = max(v['util_proj'] for v in out.values())
    return dict(rs_latency=rs_t, relay_bits=bits, worst_util_proj=worst, cuts=out)


def anneal(seed, dv, iters):
    rnd = random.Random(seed)
    nodes = g.NODES
    host = dict(hosts)
    sp = spare

    def cost(h):
        r = loads(h, dv)
        if a.lat_cap:
            return r['worst_util_proj'] * 1e4 + max(0, r['rs_latency'] - a.lat_cap) * 1e5 + r['rs_latency'] * 10 + r['relay_bits'] / 1e5, r
        if a.lat_first:
            return r['rs_latency'] * 1e4 + r['worst_util_proj'] * 1e3 + r['relay_bits'] / 1e5, r
        return r['worst_util_proj'] * 1e4 + r['rs_latency'] * 10 + r['relay_bits'] / 1e5, r
    cur, cr = cost(host)
    best = (cur, dict(host), sp, cr)
    for it in range(iters):
        T = 200 * (1 - it / iters) + .01
        h, s2 = dict(host), sp
        n1 = rnd.choice(nodes)
        if rnd.random() < .2:
            h[n1], s2 = s2, h[n1]
        else:
            n2 = rnd.choice(nodes)
            h[n1], h[n2] = h[n2], h[n1]
        c, r = cost(h)
        if c < cur or rnd.random() < math.exp(-(c - cur) / T):
            host, sp, cur = h, s2, c
            if c < best[0]:
                best = (c, dict(h), s2, r)
    return best


res = dict(gen=a.gen, hosts=a.hosts, dv=a.dv, corr_w=a.corr_w, width_um=g.WIDTH, height_um=g.HEIGHT,
           base=loads(hosts, a.dv))
assert g.ordered_ast(hosts) == g.ordered_ast(hosts)
if a.anneal:
    bs = [anneal(s, a.dv, a.iters) for s in range(1, a.anneal + 1)]
    b = min(bs, key=lambda t: t[0])
    res['annealed'] = dict(host={f'{l}_{i}': list(v) for (l, i), v in sorted(b[1].items())}, spare=list(b[2]), **b[3])
for k in ('base', 'annealed'):
    if k in res:
        r = res[k]
        print(f"== {k}: rs_latency {r['rs_latency']}  relay_bits {r['relay_bits']}  worst util(proj) {r['worst_util_proj']}")
        for n, v in r['cuts'].items():
            print(f"   {n:14s} peak {v['peak_bits']:5d}  proj {v['util_proj']:.3f}  m3 {v['util_m3']:.3f}  cap {v['cap_proj']:5d}  {v['fam']}")
if a.json:
    json.dump(res, open(a.json, 'w'), indent=1)

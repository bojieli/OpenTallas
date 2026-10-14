#!/usr/bin/env python3
"""el1013-s81-vmfe/B8: E-W NECESSARY CONDITION of the dsfd_vm_fe_h floorplan (slot sp_vm/u_fe 1,520.064 x 695.52).

  python3 tools/s81_ph/s81_ph_vm_fe_h_ew_bound.py [--out results/arch/s81_vm_fe_h_ew_bound_1013.json]

For every vertical cut x (10.8-um columns):
  demand(x) = the bits whose two ends lie on opposite sides of x (source leaf pin / sink leaf pin; relays lie between
              them, so a chain crosses the cut once): a LOWER bound of the wires that cross it, whatever the routing
  supply(x) = the usable H tracks of the WHOLE FE height at x (s81_ph_vm_fe_h_floorplan.py track model, 80 % usable):
              free area M2/2 + M4 + M6 = 39.5 / um, over an M5-capped leaf M6 only = 12.5 / um (the clt row's M6 included,
              although only a detour over the row reaches it), over dsfd_vm_fsr 0: an UPPER bound
  bound(x)  = demand / supply <= the cut ratio of ANY routing of that placement.  bound > 0.60 = no plan can pass.
Placement family searched (hill climb, 4 restarts x 2,500 moves a case): the 10 landing lanes anywhere on a 108-um x
lattice (<= 2 lane rows under the clt row, <= 4 beside it; pin access, reach and overlaps are NOT checked: optimistic),
return face towards the drain, fld / fcn / fcc / fcw centres free.  Pin x of fxs / fsr from the real pin tables.
Result (2026-10-13): frozen structure (one drain dsfd_vm_fld) best bound found 0.65 (clt row at x 0) / 0.74 - 0.82 (centred);
with NO lane in the slot 0.533."""
import argparse, importlib.util, json, random, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sp = importlib.util.spec_from_file_location('fp', ROOT / 'tools/s81_ph/s81_ph_vm_fe_h_floorplan.py')
fp = importlib.util.module_from_spec(sp); sp.loader.exec_module(fp)
MP, v = fp.MP, fp.LS.v
W, H = 1520.064, 695.52
LW, LH = 216.0, 129.6
M8 = 0.0
HF, HL = fp.H_FREE * fp.USABLE, fp.H_LEAF * fp.USABLE          # usable H tracks / um: free 39.5, over an M5 leaf 12.5
XS = np.arange(5.4, W, 10.8)
fs = MP['dsfd_vm_fsr'][2]; fx = MP['dsfd_vm_fxs'][2]
_FD = {P: (float(np.mean([fs[f'i_d[{128*P+i}]'][0] for i in range(128)])), fs[f'i_row[{14*P}]'][0]) for P in range(28)}
_SX = {(j, s): float(np.mean([fx[f's_o[{(4*j+s)*147+i}]'][0] for i in range(147)])) for j in range(4) for s in range(4)}
def fsr_x(s, P):
    """x of port P of slice s: data, ctl"""
    return 388.8 * s + _FD[P][0], 388.8 * s + _FD[P][1]
_CAP = {}
def cap_demand(cx):
    if cx not in _CAP:
        d = np.zeros(len(XS))
        for g in range(16):
            b, j = divmod(g, 4)
            for s in range(4):
                xa = cx + 322.56 * b + _SX[(j, s)]
                for xb, bits in zip(fsr_x(s, 12 + g), (128, 19)):
                    d[(XS > min(xa, xb)) & (XS < max(xa, xb))] += bits
        _CAP[cx] = d
    return _CAP[cx].copy()
def demand(cx, lanes, cen, R=3, premux=None):
    """lanes: [(x0, mirrored?)] 10; cen: {'fld','fcn','fcc','fcw': x centre} -> demand(x) array, components"""
    D = {k: np.zeros(len(XS)) for k in ('capture', 'b4b5', 'returns', 'k')}
    def add(k, xa, xb, bits):
        lo, hi = min(xa, xb), max(xa, xb); D[k][(XS > lo) & (XS < hi)] += bits
    D['capture'] = cap_demand(cx)
    for g in range(16):
        b, j = divmod(g, 4)
        add('k', cx + 322.56 * b + fx[f'k_o[{32*j}]'][0], cen['fcn'], 32)
    for s in range(4):
        for P, src, dat in ((0, 'fcw', 1), (1, 'fcw', 0), (3, 'fcc', 1), (4, 'fcc', 1), (2, 'fcn', 0), (5, 'fcn', 0), (6, 'fcn', 0), (7, 'fcn', 0),
                            (8, 'fcn', 0), (9, 'fcn', 0), (10, 'fld', 1), (11, 'fld', 1)):
            xd, xc = fsr_x(s, P)
            if dat: add('b4b5', cen[src], xd, 128)
            add('b4b5', cen[src], xc, 15 + dat)
    add('b4b5', cen['fcn'], fsr_x(0, 5)[0], 112)
    for i, (x0, mir) in enumerate(lanes):
        xf = x0 + (LW if mir else 0.0)
        if premux:      # two-level drain: lanes of a side -> its pre-mux (5 x 546), pre-mux -> fld 2 x 530
            add('returns', xf, premux[i], 546 + 16)
        else:
            add('returns', xf, cen['fld'], 546 + 16)
    if premux:
        for xp in sorted(set(premux)): add('returns', xp, cen['fld'], 2 * 530 + 2 * 16)
    return D
def supply(rects):
    """rects [(x0, x1, height, kind)] kind 'leaf' (M6 above) | 'fsr' (nothing above) -> usable H tracks per cut"""
    S = np.full(len(XS), H * (HF + M8))
    for x0, x1, h, kind in rects:
        m = (XS > x0) & (XS < x1); S[m] -= h * (HF - (HL if kind == 'leaf' else 0.0))
    return S
def base_rects(cx, R=3):
    r = [(cx, cx + 16 * 80.64, 267.84, 'leaf'), (cx, cx + 4 * 322.56, 19.44, 'leaf')]
    for s in range(4):
        r.append((388.8 * s, 388.8 * s + 345.6, 25.92, 'fsr'))
        r.append((388.8 * s, 388.8 * s + 86.4, 25.92, 'leaf')); r.append((388.8 * s + 127.44, 388.8 * s + 300.24, 32.4, 'leaf'))   # last relay row
    return r
def report(name, cx, lanes, cen, cen_rects, extra_relay_h=64.8, premux=None, show=True):
    D = demand(cx, lanes, cen, premux=premux); tot = sum(D.values())
    r = base_rects(cx) + [(x0, x0 + LW, LH, "leaf") for x0, _ in lanes] + cen_rects
    # the 2 x 24 other bundle relay tiles lie somewhere on every cut between a source and its slice: >= extra_relay_h of
    # tile height on an average central cut (2 tiles of 32.4)
    r.append((350.0, 1170.0, extra_relay_h, 'leaf'))
    S = supply(r); ratio = tot / S; i = int(ratio.argmax())
    if show:
        print(f'{name}: worst E-W cut x {XS[i]:.0f}: demand >= {tot[i]:.0f} b (capture {D["capture"][i]:.0f}, clients {D["b4b5"][i]:.0f}, lane returns {D["returns"][i]:.0f}, k {D["k"][i]:.0f}) / usable H tracks <= {S[i]:.0f} = {ratio[i]:.3f}'
              f' | cuts over 0.60: {int((ratio > 0.6).sum())} of {len(XS)} ({XS[ratio > 0.6].min() if (ratio > 0.6).any() else 0:.0f} .. {XS[ratio > 0.6].max() if (ratio > 0.6).any() else 0:.0f})')
    return float(ratio.max()), ratio


SL = [round(108.0 * i, 3) for i in range(0, 13)] + [1304.064]          # lane x0 candidates
def capok(xs, cx):
    cov = np.zeros(len(XS))
    for x in xs: cov[(XS > x) & (XS < x + LW)] += 1
    lim = np.where((XS > cx) & (XS < cx + 1290.24), 2, 4)     # <= 2 lane rows under the clt row (generous), 4 beside it
    return bool((cov <= lim).all())
def score(xs, cen, cx, premux):
    lanes = [(x, (x + 108 < cen['fld']) if not premux else (x + 108 < (premux[0] if x < 760 else premux[1]))) for x in xs]
    pm = None
    if premux: pm = [premux[0] if x < 760 else premux[1] for x in xs]
    cr = [(cen['fld'] - 86.4, cen['fld'] + 86.4, 69.12, 'leaf'), (cen['fcn'] - 120, cen['fcn'] + 120, 51.84, 'leaf'),
          (cen['fcc'] - 90.7, cen['fcc'] + 90.7, 112.32, 'leaf'), (cen['fcw'] - 75.6, cen['fcw'] + 75.6, 38.88, 'leaf')]
    return report('', cx, lanes, cen, cr, premux=pm, show=False)[0], lanes, cr, pm
def search(cx, use_pm, iters=2500):
    best = None
    for rs in range(4):
        xs = [random.choice(SL) for _ in range(10)]
        while not capok(xs, cx): xs = [random.choice(SL) for _ in range(10)]
        cen = {'fld': 760.0, 'fcn': 806.0, 'fcc': 560.0, 'fcw': 980.0}; pm = [430.0, 1090.0] if use_pm else None
        cur = score(xs, cen, cx, pm)[0]
        for it in range(iters):
            xs2, cen2, pm2 = list(xs), dict(cen), list(pm) if pm else None
            r = random.random()
            if r < 0.6: xs2[random.randrange(10)] = random.choice(SL)
            elif r < 0.9: k = random.choice(list(cen2)); cen2[k] = min(1400.0, max(120.0, cen2[k] + random.choice((-108, -54, 54, 108))))
            elif pm2: k = random.randrange(2); pm2[k] = min(1450.0, max(60.0, pm2[k] + random.choice((-108, -54, 54, 108))))
            if not capok(xs2, cx): continue
            s = score(xs2, cen2, cx, pm2)[0]
            if s <= cur: xs, cen, pm, cur = xs2, cen2, pm2, s
        if best is None or cur < best[0]: best = (cur, sorted(xs), cen, pm)
    return best


def case(tag, cx=0.0, pm=False, lane=(216.0, 129.6), m8=0.0, dh=0.0, seed=11):
    global LW, LH, M8, H
    LW, LH = lane; M8 = m8; H = 695.52 + dh; random.seed(seed)
    b = search(cx, pm); s, lanes, cr, p = score(b[1], b[2], cx, b[3])
    D = demand(cx, lanes, b[2], premux=p); tot = sum(D.values())
    r = base_rects(cx) + [(x0, x0 + LW, LH, 'leaf') for x0, _ in lanes] + cr + [(350.0, 1170.0, 64.8, 'leaf')]
    S = supply(r); ratio = tot / S; i = int(ratio.argmax())
    rec = {'case': tag, 'clt_row_x0': cx, 'two_level_drain': pm, 'lane_um': list(lane), 'm8_tracks_per_um': m8, 'height_um': H,
           'bound': round(float(ratio[i]), 3), 'worst_cut_x': float(XS[i]), 'demand_bits': {k: int(v[i]) for k, v in D.items()},
           'supply_tracks': int(S[i]), 'cuts_over_0p60': int((ratio > 0.6).sum()), 'lanes_x0': b[1], 'centres': b[2], 'premux_x': b[3]}
    print(f"{tag}: bound {rec['bound']:.3f} at x {rec['worst_cut_x']:.0f} (demand {int(tot[i])} = {rec['demand_bits']} / supply {rec['supply_tracks']}), cuts over 0.60: {rec['cuts_over_0p60']} of {len(XS)}")
    return rec


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=None); a = ap.parse_args()
    cen = {'fld': 760.0, 'fcn': 806.0, 'fcc': 560.0, 'fcw': 980.0}
    cr = [(cen['fld'] - 86.4, cen['fld'] + 86.4, 69.12, 'leaf'), (cen['fcn'] - 120, cen['fcn'] + 120, 51.84, 'leaf'),
          (cen['fcc'] - 90.7, cen['fcc'] + 90.7, 112.32, 'leaf'), (cen['fcw'] - 75.6, cen['fcw'] + 75.6, 38.88, 'leaf')]
    nol = report('no landing lane in the slot (returns enter above fld)', 0.0, [], cen, cr)[0]
    R = [case('frozen structure, clt row at x 0'), case('frozen structure, clt row centred (+115.2)', cx=115.2),
         case('two-level drain (5 lanes -> pre-mux -> fld)', pm=True),
         case('lane tile 190.08 x 103.68 (cluster free-area rule)', lane=(190.08, 103.68)),
         case('lane tile 190.08 x 103.68 + two-level drain', pm=True, lane=(190.08, 103.68)),
         case('M8 H grant over the slot (75 % of 12.5 / um)', m8=0.75 / 0.080),
         case('slot height +64.8 um', dh=64.8), case('slot height +129.6 um', dh=129.6), case('slot height +194.4 um', dh=194.4)]
    res = {'schema': 'opentallas.s81_vm_fe_h.ew_bound.v1', 'agent': 'el1013-s81-vmfe/B8', 'outline': [W, 695.52], 'limit': 0.60,
           'tracks_per_um_usable': {'free': round(HF, 2), 'over_m5_leaf': round(HL, 2), 'over_fsr': 0.0},
           'no_lane_in_slot_bound': round(nol, 3), 'cases': R,
           'reading': 'bound = demand lower bound / supply upper bound of the worst vertical cut for the best placement found; > 0.60: this searched candidate cannot pass; the finite hill-climb search does not prove global impossibility. <= 0.60: NOT a pass (pin access, reach, local windows and the detour onto the clt-row M6 are not in it)'}
    if a.out: (ROOT / a.out).write_text(json.dumps(res, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())

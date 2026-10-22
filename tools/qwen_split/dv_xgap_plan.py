#!/usr/bin/env python3
"""QW-G5STA 10-20: slice LANDING CHANNELS for the Qwen compute die's dv array (data only, no GEN code change).

g5 (dv2f20g5) abutted the 12 dv_slice2 instances face to face (dvs_W5..W0 | seam | E0..E5, pitch = slice width 2462.4),
so the 182 slice <-> slice cross-REGION buses (50,267 b; every slice has its own region root) had no die site for a
landing station and the GEN recorded them as OT_SPLIT_LAND_LIST_IN_FACE "owed" (regional verdict landed=FAIL, the FF
hold -64 ps slice -> slice paths).  This writes a dv plan with a full-height channel of G um at EVERY abutted slice
column boundary (the W0|E0 seam already has its 129.6-um channel): every instance whose x is at or east of a boundary
moves E by G (cumulative), so the c16 cluster columns stay aligned with their slices (the cw / rs words keep their
vertical G-free geometry) and the inter-column gaps grow from 17.28 to 17.28 + G.  With OT_SPLIT_LAND_LIST_IN_FACE=''
the GEN then lands those rows like every other cross-region link (one-frame forwarded lane at the receiver: ring
written on the sender's root, read on the receiver's root, fixed E, no backpressure).  G is on the 43.2 lattice.

usage: dv_xgap_plan.py --plan in.json --gap-um 129.6 --skip dvs_E1 --out out.json [--die-w-max 33000]
G 86.4 (one 64.8-um station column) was too narrow: dv2f20g5l tries 2-3 stacked ~1 mm of landings per boundary in one
column beside a ~1-mm pin window (779-838 / 658-um hops); G 129.6 holds two 64.8-um columns.
"""
import argparse, json
from pathlib import Path

LAT = 43.2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', required=True, type=Path)
    ap.add_argument('--gap-um', required=True, type=float)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--die-w-max', type=float, default=33000.0, help='reticle width (um): refuse a plan wider than this')
    ap.add_argument('--die-w', type=float, default=31730.376, help='current die width (um) the plan builds')
    ap.add_argument('--skip', default='', help='slices whose W-side boundary gets no channel (same region root as the W neighbour, '
                                               'no cross-region slice bus there: dvs_E1 on g5 = E0 | E1 share pll_r95)')
    a = ap.parse_args()
    G = a.gap_um
    if abs(G / LAT - round(G / LAT)) > 1e-6 or G <= 0:
        raise SystemExit(f'gap {G} is not a positive multiple of the {LAT} lattice')
    D = json.loads(a.plan.read_text())
    sl = sorted((i for i in D['insts'] if i['n'].startswith('dvs_')), key=lambda i: i['x'])
    bounds = []
    for p, q in zip(sl, sl[1:]):
        if abs(p['x'] + p['w'] - q['x']) < 1e-3 and q['n'] not in set(filter(None, a.skip.split(','))):
            bounds.append(q['x'])                       # abutted pair (the W0|E0 seam has its own channel)
    if not bounds:
        raise SystemExit('no abutted slice boundary in the plan')
    moved = {}
    for i in D['insts']:
        k = sum(1 for b in bounds if i['x'] >= b - 1e-3)
        if k:
            i['x'] = round(i['x'] + k * G, 3)
            moved[i['n']] = k * G
    grow = len(bounds) * G
    if a.die_w + grow > a.die_w_max:
        raise SystemExit(f'die width {a.die_w + grow:.1f} > reticle {a.die_w_max}')
    D['slice_abut'] = False
    D['slice_xgap_um'] = G
    D['source'] = D.get('source', '') + f' | QW-G5STA 10-20: slice landing channels {G} um at {len(bounds)} abutted slice boundaries (dv_xgap_plan.py)'
    a.out.write_text(json.dumps(D, indent=1) + '\n')
    print(json.dumps(dict(out=str(a.out), gap_um=G, boundaries=[round(b, 3) for b in bounds], moved=len(moved),
                          die_w_growth_um=round(grow, 3), die_w_est_um=round(a.die_w + grow, 3))))


if __name__ == '__main__':
    main()

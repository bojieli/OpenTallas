#!/usr/bin/env python3
"""S81.CLK2 (10-22): land plan rows for x-chain HEAD lanes that have none.

cap18 (528fc3c9f) routes 96 x_frame lanes (24 frames f_<c><L|R>02 / f_<c><L|R>12, 4 lanes each) as chain HEADS from a
slice LEP endpoint root (ck_ep_*/ck_sl_*/ck_b_s_*) straight to the frame (30-80 relay stations).  Their land plan rows
were never produced (the p4l/G7 row sets know these lanes only as short frame->frame forwards; G7's model scope excludes
x_), so: (a) gen_safety C1 counts them as region crossings WITHOUT a landing ring, and (b) dv_bind derives the frame lk
strap from "no row" -> K 1 for every lane of those 24 frames, below the minimum measured x_frame E (2) -> the receiving
crs4 ring would be read before the forwarded data is in its window.

The landing hardware exists (dsfd_cfifo_crs4 inside the receiving frame: ot_s81_land W276 D4 per lane, 3-bit K strap,
read on the frame root).  This tool adds a MODEL row per missing x_frame lane whose K is the LARGEST die-STA-measured E
of the measured x_frame rows within +-WIN stations (forwarded clock travels with the data, so E does not grow with N:
measured E over 364 rows, 0-80 stations, is 2..5); every lane of one receiving frame takes the bundle max (the frame
has one strap per lane but dv_bind straps the frame max).  K <= 7 (3-bit strap) is asserted.  The die STA re-derives
E/K like every other model row.  Extra latency (K - 1 edges vs the old K 1 strap) is accepted (owner: cycles OK).

Usage: land_xhead_clk2.py PLAN LAND_IN LAND_OUT [--win 8] [--uniform K]
"""
import argparse, collections, json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan'); ap.add_argument('land_in'); ap.add_argument('land_out')
    ap.add_argument('--win', type=int, default=8)
    ap.add_argument('--uniform', type=int, default=None, help='FALLBACK policy: one K for every added lane')
    a = ap.parse_args()
    p = json.load(open(a.plan)); d = json.load(open(a.land_in))
    rows = {r['link']: r for r in d['links']}
    B = p['blocks']
    meas = [r for r in d['links'] if r.get('cls') == 'x_frame' and not r.get('model')
            and (r.get('s1') or {}).get('tt') is not None and r.get('E')]
    assert meas, 'no measured x_frame rows to model from'
    gmax = max(r['E'] for r in meas)
    added, by_dst = [], collections.defaultdict(list)
    for l in p['links']:
        nm = l['i'].replace('-', '_')
        if l['c'] != 'x_frame' or nm in rows:
            continue
        dst = B[l['e'][1][0]]
        if dst.get('kind') != 'frame':
            continue
        N = l.get('s', 0)
        near = [r['E'] for r in meas if abs(r['stages'] - N) <= a.win]
        E = a.uniform if a.uniform else (max(near) if near else gmax)
        assert 1 <= E <= 7, (nm, E)
        r = dict(link=nm, cls='x_frame', dst=dst['name'], bits=l['b'], stages=N, s1={'tt': None, 'ff': None},
                 h0={'tt': None, 'ff': None}, E=E, K=E, D=4, master='dsfd_dvland_276', window_ok=None, model=True,
                 bundle=dst['name'],
                 K_source=(f'CLK2 x-head MODEL: uniform K {E} (fallback policy)' if a.uniform else
                           f'CLK2 x-head MODEL: max die-STA E of {len(near)} measured x_frame rows within +-{a.win} '
                           f'stations of N {N} (global max {gmax}); lands in the receiving frame crs4 (D4, 3-bit K); '
                           f'die STA re-derives'))
        rows[nm] = r; added.append(nm); by_dst[dst['name']].append(r)
    # one strap value per frame: every lane row of an affected frame carries the frame max (what dv_bind straps)
    for f, rs in by_dst.items():
        allr = [r for r in rows.values() if r.get('cls') == 'x_frame' and r.get('dst') == f]
        k = max(r.get('K', r['E']) for r in allr)
        for r in rs:
            r['K'] = k
    d['links'] = list(rows.values())
    d['clk2_xhead'] = dict(added=added, frames=sorted(by_dst), win=a.win, uniform=a.uniform, global_max_E=gmax,
                           K_hist=dict(collections.Counter(r['K'] for rs in by_dst.values() for r in rs)),
                           rule='x_frame lanes without a row -> model row (crs4 in-frame landing), K = max measured E '
                                'within +-win stations, frame bundle max; old strap K 1 (no row) replaced')
    json.dump(d, open(a.land_out, 'w'), indent=1)
    print('CLK2_XHEAD', json.dumps(d['clk2_xhead']['K_hist']), 'added', len(added), 'frames', len(by_dst))


if __name__ == '__main__':
    main()

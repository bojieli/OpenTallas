#!/usr/bin/env python3
"""HBM-P5 GEOM condition (GEOM-REVIEW 10-23 14:25 note on hbm_plan @432b1f283): per-column worst cut and total
bit-mm of a die plan, on the PLAN-TOOL lane geometry (check.lane_geometry: Z routes between port windows).

Bands (die frame, um):  edge_W  x 300-2500        edge_E  x W-2717.6 .. W-417.6 (mirror of edge_W; 17.5-19.8 mm)
                         cross_V x CX +- 1100     (centre column)     cross_H y CY +- 1100 (centre row)
For each band the cut lines run ACROSS the band every 250 um (horizontal lines for a column, vertical lines for the
row); a lane segment counts when it runs along the band (its crossing point lies inside the band).  Capacity =
band width x (partition ft track density on M4/M6 or M5/M7 x ft_track_frac + die M8/M9 cut_avail density), the
same densities check.check_cuts uses.  Total bit-mm = sum over lanes of width x route length.

    python3 column_cuts.py PLAN.json [PLAN.json ...] [--labels a,b,...] [--json OUT]
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'die_plan'))
import check  # noqa: E402
import schema as S  # noqa: E402


def analyse(path):
    raw = S.load(path)
    P = S.Plan(raw)
    geo = {lid: check.lane_geometry(P, lid) for lid in P.lanes}
    W, H = P.W, P.H
    CX, CY = W / 2, H / 2
    avail = P.layer_budget.get('cut_avail', {})
    die_l = [n for n in P.layer_budget['die_layers'] if n in P.layers]

    def den(wire_dir):
        d = sum(avail.get(n, 0.0) / P.layers[n]['pitch_um'] for n in die_l if P.layers[n]['dir'] == wire_dir)
        return d + check.track_density(P, check.PART_FT_LAYERS[wire_dir], check.FT_TRACK_FRAC)
    segs, bitmm = [], 0.0
    for lid, (pts, _, _) in geo.items():
        w = P.ports[P.lanes[lid]['ports'][0]]['width']
        bitmm += w * check.plen(pts) / 1000.0
        segs += [(p, q, w) for p, q in zip(pts, pts[1:])]
    bands = dict(edge_W=('col', 300.0, 2500.0), edge_E=('col', W - 2717.6, W - 417.6),
                 cross_V=('col', CX - 1100, CX + 1100), cross_H=('row', CY - 1100, CY + 1100))
    out = dict(plan=path, lanes=len(geo), bit_mm=round(bitmm), bands={})
    for name, (kind, lo, hi) in bands.items():
        wire = 'V' if kind == 'col' else 'H'
        cap = (hi - lo) * den(wire)
        L = H if kind == 'col' else W
        worst = (0.0, None, 0)
        for k in range(1, int(L // 250)):
            c = k * 250.0
            bits = 0
            for p, q, w in segs:
                a, b = (p[1], q[1]) if kind == 'col' else (p[0], q[0])      # coordinate the cut line crosses
                o = p[0] if kind == 'col' else p[1]                           # position across the band
                if min(a, b) < c - 1e-6 and max(a, b) > c + 1e-6 and lo <= o <= hi:
                    bits += w
            r = bits / cap
            if r > worst[0]:
                worst = (r, c, bits)
        out['bands'][name] = dict(range_um=[round(lo, 1), round(hi, 1)], worst_ratio=round(worst[0], 4),
                                  at_um=worst[1], bits=worst[2], tracks=round(cap))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('plans', nargs='+')
    ap.add_argument('--labels')
    ap.add_argument('--json')
    a = ap.parse_args()
    labels = a.labels.split(',') if a.labels else a.plans
    res = {lb: analyse(p) for lb, p in zip(labels, a.plans)}
    for lb, r in res.items():
        b = r['bands']
        print(f"{lb:8s} lanes {r['lanes']:5d} bit-mm {r['bit_mm']:>9,d}  " +
              '  '.join(f"{k} {v['worst_ratio']:.3f}@{v['at_um']}" for k, v in b.items()))
    if a.json:
        json.dump(res, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""DIE-CLOCK: regional clock-root sites for an HBM half/full-die compact plan (compact.P.json), legalised outside every block.

  root_sites.py --plan compact.P.json --die-w W --die-h H --bands SW:8797:12097,SE:12597:15897,... \\
      --band-split 3 --ecol-x 17860 --out root_sites.json [--die NAME]

Sites (each a 60 x 60 um station-free keepout; one root buffer per clock family present in the region):
- sm_<q><i>: one per SM column cluster, in the channel E of the column, 400 um from its band-side end. The cluster's
  own CTS goes from there; F108 puts clk/rst on the front E face.
- band_<q><k>: --band-split equal x slices of each band (x 0 .. the band hub's W edge). The site is the slice centroid.
- ecol_<q>: one per band row in the E column (x >= ecol_x), at the row's y centre.
- pc_<q>a/b: the two halves of each PC row (the hbm family).
Each point is moved to the nearest location whose 60 um keepout clears every block (by 10 um steps out to 1.5 mm). The
move is recorded, and a site that cannot be legalised is reported, never dropped.
"""
import argparse, json, re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--die-w', type=float, required=True)
    ap.add_argument('--die-h', type=float, required=True)
    ap.add_argument('--bands', required=True, help='name:y0:y1,... (S to N)')
    ap.add_argument('--band-split', type=int, default=3)
    ap.add_argument('--ecol-x', type=float, required=True)
    ap.add_argument('--die', default='hbm')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    P = json.load(open(a.plan))
    boxes = [(k, v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h']) for k, v in P.items()]
    H = 30.0

    def clear(x, y):
        if not (H <= x <= a.die_w - H and H <= y <= a.die_h - H):
            return False
        return all(x + H <= b[1] or x - H >= b[3] or y + H <= b[2] or y - H >= b[4] for b in boxes)

    def legal(x, y):
        if clear(x, y):
            return x, y, 0.0
        for r in range(1, 151):
            d = 10.0 * r
            best = None
            for i in range(-r, r + 1):
                for (dx, dy) in ((i * 10.0, -d), (i * 10.0, d), (-d, i * 10.0), (d, i * 10.0)):
                    if clear(x + dx, y + dy):
                        m = abs(dx) + abs(dy)
                        if best is None or m < best[2]:
                            best = (x + dx, y + dy, m)
            if best:
                return best
        return None

    sites, failed = [], []

    def add(name, x, y, note):
        L = legal(x, y)
        if L is None:
            failed.append(name)
            return
        sites.append(dict(region=name, x=round(L[0], 1), y=round(L[1], 1), moved_um=round(L[2], 1), planned=[round(x, 1), round(y, 1)],
                          keepout=[round(L[0] - H, 1), round(L[1] - H, 1), round(L[0] + H, 1), round(L[1] + H, 1)], note=note))

    bands = [(b.split(':')[0], float(b.split(':')[1]), float(b.split(':')[2])) for b in a.bands.split(',')]
    for k, v in sorted(P.items()):
        m = re.match(r'^sm_([A-Z]+)(\d+)$', k)
        if not m:
            continue
        q = m.group(1)
        band = next((b for b in bands if b[0] == q), None)
        mid = (band[1] + band[2]) / 2 if band else a.die_h / 2
        top = v['y'] + v['h'] <= mid           # column below its band: band-side end is the top
        y = v['y'] + v['h'] - 400 if top else v['y'] + 400
        add(k, v['x'] + v['w'] + 50, y, 'SM column cluster root, E channel by the front clk/rst pins (F108)')
    for q, y0, y1 in bands:
        hub = [v for k, v in P.items() if k in (f'vmh_{q}',)]
        xe = min(v['x'] for v in hub) if hub else a.ecol_x
        for i in range(a.band_split):
            x0, x1 = xe * i / a.band_split, xe * (i + 1) / a.band_split
            add(f'band_{q}{i}', (x0 + x1) / 2, (y0 + y1) / 2, 'band region root; trees of every family present in the slice')
        add(f'ecol_{q}', a.ecol_x + 300, (y0 + y1) / 2, 'E column row root (hc_eng / ep / lk / hub side of this band)')
    for k in sorted({re.sub(r'\d+$', '', k) for k in P if k.startswith('pc_')}):
        pcs = [v for kk, v in P.items() if re.sub(r'\d+$', '', kk) == k]
        x0 = min(v['x'] for v in pcs); x1 = max(v['x'] + v['w'] for v in pcs); y = max(v['y'] + v['h'] for v in pcs) + 50
        add(f'{k}a', x0 + (x1 - x0) / 4, y, 'PC row W half (hbm family)')
        add(f'{k}b', x0 + 3 * (x1 - x0) / 4, y, 'PC row E half (hbm family)')
    json.dump(dict(schema='opentallas.die_clock.root_sites.v1', die=a.die, plan=a.plan,
                   rule='60x60 um station-free keepout per site (wires may cross); one regional root buffer per clock family '
                        'present in the region; positions already legalised outside every plan block',
                   sites=sites, failed=failed), open(a.out, 'w'), indent=1)
    print(len(sites), 'sites; moved >150 um:', [s['region'] for s in sites if s['moved_um'] > 150], 'failed:', failed)


if __name__ == '__main__':
    main()

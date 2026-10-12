#!/usr/bin/env python3
"""qwendie-1012: localise a die GRT's 3D layer overflow from its route.guide (no OpenROAD session needed).

    guide_layer_map.py route.guide --die-model die.json.gz --layers M6 M8 --bin 48 --out map.json

Per layer, every guide box adds one track of demand to each gcell it covers (a horizontal-layer guide is one gcell
row tall).  Demand is binned to --bin um squares (mean tracks per gcell row / column through the bin) and compared
with the free-channel track count (bin / pitch) and with the macro footprint share of the bin (die-model insts with
a master, i.e. blocks whose own routing owns the layer).  Output: the top bins by demand / capacity with the net
classes (name prefix) that cross them."""
import argparse
import collections
import gzip
import json
import re
import numpy as np

PITCH = dict(M2=0.036, M3=0.036, M4=0.048, M5=0.048, M6=0.064, M7=0.064, M8=0.080, M9=0.080)
HORIZ = {'M2', 'M4', 'M6', 'M8'}


def ncls(n):
    n = re.sub(r'\[\d+\]$', '', n)
    n = re.sub(r'_\d+(__r\d+)?$', '', n)
    return re.sub(r'__r\d+$', '', n)[:40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('guide')
    ap.add_argument('--die-model', required=True)
    ap.add_argument('--layers', nargs='+', default=['M6', 'M8'])
    ap.add_argument('--bin', type=float, default=48.0)
    ap.add_argument('--top', type=int, default=40)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    d = json.load(gzip.open(a.die_model))
    W, H = d['outline_um']
    nx, ny = int(W // a.bin) + 1, int(H // a.bin) + 1
    dem = {l: np.zeros((ny, nx), np.float64) for l in a.layers}
    cls = {l: collections.defaultdict(collections.Counter) for l in a.layers}
    net = None
    with open(a.guide) as f:
        for line in f:
            t = line.split()
            if len(t) == 1:
                if t[0] not in ('(', ')'):
                    net = t[0]
                continue
            if len(t) != 5 or t[4] not in dem:
                continue
            x0, y0, x1, y1 = (float(v) / 1000.0 for v in t[:4])   # DBU 1000 / um
            l = t[4]
            if l in HORIZ:   # track-um of demand: length along x, one track per gcell row covered
                rows = max(1.0, (y1 - y0) / 4.8)
                bx0, bx1, by_ = int(x0 // a.bin), int(min(x1, W - 1e-3) // a.bin), int(((y0 + y1) / 2) // a.bin)
                for bx in range(bx0, bx1 + 1):
                    seg = min(x1, (bx + 1) * a.bin) - max(x0, bx * a.bin)
                    if seg > 0:
                        dem[l][by_, bx] += seg * rows
                        cls[l][(by_, bx)][ncls(net)] += 1
            else:
                cols = max(1.0, (x1 - x0) / 4.8)
                by0, by1, bx_ = int(y0 // a.bin), int(min(y1, H - 1e-3) // a.bin), int(((x0 + x1) / 2) // a.bin)
                for by in range(by0, by1 + 1):
                    seg = min(y1, (by + 1) * a.bin) - max(y0, by * a.bin)
                    if seg > 0:
                        dem[l][by, bx_] += seg * cols
                        cls[l][(by, bx_)][ncls(net)] += 1
    # macro share per bin
    occ = np.zeros((ny, nx), np.float64)
    for i in d['insts']:
        x, y, w, h = i[5:9]
        if i[0].startswith('rly'):
            continue
        for by in range(int(y // a.bin), int(min(y + h, H - 1e-3) // a.bin) + 1):
            for bx in range(int(x // a.bin), int(min(x + w, W - 1e-3) // a.bin) + 1):
                ox = min(x + w, (bx + 1) * a.bin) - max(x, bx * a.bin)
                oy = min(y + h, (by + 1) * a.bin) - max(y, by * a.bin)
                if ox > 0 and oy > 0:
                    occ[by, bx] += ox * oy
    occ = np.minimum(occ / (a.bin * a.bin), 1.0)
    out = dict(guide=a.guide, bin_um=a.bin, layers={})
    for l in a.layers:
        cap_free = a.bin / PITCH[l] * a.bin      # track-um per bin if no blockage
        u = dem[l] / cap_free                     # utilisation vs an empty bin
        u_ch = dem[l] / np.maximum(cap_free * (1 - occ), 1e-9)   # vs the channel share (macro owns the layer)
        idx = np.dstack(np.unravel_index(np.argsort(-u_ch, axis=None), u_ch.shape))[0][:a.top]
        rows = []
        for by, bx in idx:
            rows.append(dict(x=round(bx * a.bin, 1), y=round(by * a.bin, 1), util_empty=round(float(u[by, bx]), 3),
                             util_channel=round(float(u_ch[by, bx]), 3), macro_share=round(float(occ[by, bx]), 3),
                             nets=cls[l][(by, bx)].most_common(5)))
        over = u_ch > 1.0
        out['layers'][l] = dict(bins_over_channel_cap=int(over.sum()), bins_over_empty_cap=int((u > 1.0).sum()),
                                demand_track_um=float(dem[l].sum()),
                                over_rows_y=collections.Counter(int(by * a.bin) for by, bx in zip(*np.nonzero(over))).most_common(15),
                                over_cols_x=collections.Counter(int(bx * a.bin) for by, bx in zip(*np.nonzero(over))).most_common(15),
                                top=rows)
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    for l, r in out['layers'].items():
        print(l, r['bins_over_channel_cap'], r['bins_over_empty_cap'], r['over_rows_y'][:5], r['over_cols_x'][:5])


if __name__ == '__main__':
    main()

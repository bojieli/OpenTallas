#!/usr/bin/env python3
"""DIE-HBM-22 re-plan estimate (12.14b estimate before build): row permutations of the HBM die rows A (y 4510, h 1555.2)
and C (y 10385, h 1572.48) per half, scored on ALL pair connectivity (existing plan lanes end-to-end + the 92 UNPLANNED
far/failed rows of HBM-BIND-8 after h8b).  Plan arithmetic only (UNCHECKED until built + G0/G0C).

Per pair: ADJ = the two rectangles share an edge >= MIN_EDGE um; else gap = rectangle edge-to-edge distance
(Manhattan); FAR = gap > NEAR.  Edge window demand: per shared edge, bits of all ADJ pairs on it vs edge_len x 6 pins/um x
0.6 (pin_track_max) -> window over-subscription flag.
"""
import json, sys, itertools, random
from collections import defaultdict

NEAR = 1200.0
MIN_EDGE = 50.0
PPU = 6.0

D = json.load(open(sys.argv[1]))           # lanes.json (die-hbm-21 d21h extraction)
R = json.load(open(sys.argv[2]))['rows']   # rows103.json
H = json.load(open(sys.argv[3]))['rows']   # rows_h8b.json (already laned in d21h)
hs = {(x['src'], x['dst']) for x in H}
far92 = [x for x in R if (x['src'], x['dst']) not in hs]

rect0 = {p['name']: (p['o'][0], p['o'][1], p['sz'][0], p['sz'][1]) for p in D['parts']}

pairs = defaultdict(lambda: [0, 0])  # (a,b) sorted -> [plan bits, new bits]
for l in D['lanes']:
    if l['src'] == l['dst']:
        continue
    k = tuple(sorted((l['src'], l['dst'])))
    pairs[k][0] += l['w']
for x in far92:
    k = tuple(sorted((x['src'], x['dst'])))
    pairs[k][1] += x['unplanned_bits']


def rel(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    dx = max(bx - (ax + aw), ax - (bx + bw), 0.0)
    dy = max(by - (ay + ah), ay - (by + bh), 0.0)
    if dx < 1e-6 and dy < 1e-6:
        ox = min(ax + aw, bx + bw) - max(ax, bx)
        oy = min(ay + ah, by + bh) - max(ay, by)
        edge = max(ox, oy)
        return edge, 0.0
    return 0.0, dx + dy


def score(rect, verbose=False, only=None):
    far_b = far_n = 0
    near_b = 0
    bitmm = 0.0
    edge_dem = defaultdict(int)
    edge_len = {}
    rows = []
    for (a, b), (pb, nb) in pairs.items():
        w = pb + nb
        edge, gap = rel(rect[a], rect[b])
        if edge >= MIN_EDGE:
            edge_dem[(a, b)] += w
            edge_len[(a, b)] = edge
            cls = 'ADJ'
        elif gap <= NEAR:
            near_b += w
            bitmm += w * max(gap, 1.0) / 1000
            cls = 'NEAR'
        else:
            far_b += w
            far_n += 1
            bitmm += w * gap / 1000
            cls = 'FAR'
        rows.append((a, b, pb, nb, cls, round(edge, 1), round(gap, 1)))
    over = [(k, edge_dem[k], round(edge_len[k] * PPU)) for k in edge_dem if edge_dem[k] > edge_len[k] * PPU]
    if verbose:
        for r in sorted(rows, key=lambda r: (r[4], -(r[2] + r[3]))):
            if only is None or r[4] in only:
                print('  %-10s %-10s plan %6d new %6d %-4s edge %8.1f gap %8.1f' % r)
    return dict(far_pairs=far_n, far_bits=far_b, near_bits=near_b, bit_mm=round(bitmm, 1), edge_over=over,
                new_far=sum(nb for (a, b), (pb, nb) in pairs.items() if nb and rel(rect[a], rect[b])[0] < MIN_EDGE and rel(rect[a], rect[b])[1] > NEAR),
                new_unadj=sum(nb for (a, b), (pb, nb) in pairs.items() if nb and rel(rect[a], rect[b])[0] < MIN_EDGE))


def mirror(name):
    return 'NE' + name[2:] if name.startswith('NW') else name


DIEW = D['die'][0]


SIZE = {}


def apply_rows(rowspec):
    """rowspec: {'A': [names west->east], 'C': [...]} for NW; NE mirrored (MY)."""
    rect = dict(rect0)
    for row, order in rowspec.items():
        y = 4510.08 if row == 'A' else 10385.28
        x = 0.0
        for n in order:
            if n is None:
                continue
            if isinstance(n, tuple):  # (name, explicit width gap after)
                n, gapw = n
            else:
                gapw = 0.0
            w = SIZE.get(n, rect0[n][2])
            h = 1555.2 if row == 'A' else 1572.48
            rect[n] = (round(x, 2), y, w, h)
            ne = mirror(n)
            rect[ne] = (round(DIEW - x - w, 2), y, w, h)
            x += w + gapw
        assert x <= 13357.44 + 0.01, (row, x)
    return rect


A0 = ['NW_b102', 'NW_b103', 'NW_b111', 'NW_su20', 'NW_su21', 'NW_spu1', 'NW_su30', 'NW_b100', 'NW_b110', 'NW_su31', 'NW_b101']
C0 = ['NW_b113', 'NW_su00', 'NW_su01', 'NW_spu0', 'NW_su10', 'NW_su11', 'NW_b112']

if __name__ == '__main__':
    base = apply_rows({'A': A0, 'C': C0})
    assert all(abs(base[k][0] - rect0[k][0]) < 0.02 for k in base), 'baseline reproduce'
    s = score(base)
    print('BASE', {k: v for k, v in s.items() if k != 'edge_over'}, 'edge_over', len(s['edge_over']))

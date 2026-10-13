#!/usr/bin/env python3
"""Cut and hop analysis of the qkd_seq cluster floorplan (owner rule 10-12: bits per cut against tracks <= 0.60;
every parent hop register -> wire -> register <= 500 um), from the cluster spec and the leaf specs.

    seq_cluster_cut.py [tools/ref_tile/specs_qkvcentre/qkd_seq.json] [--json OUT]

Tracks of a cut = the parent's routing tracks that cross it and are free of hard children: M6 (horizontal) / M7
(vertical) over the whole cut (the leaves are capped at M5), plus M4 / M5 where the cut line does not cross a leaf.
ASAP7 pitches: M4 0.048, M5 0.048, M6 0.064, M7 0.064 um; 20 % of every layer is taken off for power.  A hop is the gap between the two facing edges plus the worst lateral offset (see main).  Cut lines are taken
THROUGH the leaves (the narrowest sections), where M4 / M5 are free only in the channels."""
import json, sys
PITCH = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064)
PG = 0.20
ROOT = __file__.rsplit('/physical/', 1)[0]


def load(p):
    return json.load(open(p if p.startswith('/') else f'{ROOT}/{p}'))


def main(argv):
    spec = load(argv[1] if len(argv) > 1 and not argv[1].startswith('--') else 'tools/ref_tile/specs_qkvcentre/qkd_seq.json')
    W, H = spec['outline']['w'], spec['outline']['h']
    fp = spec['floorplan']
    box = {}
    for n, (m, x, y, o) in fp['leaves'].items():
        ol = load(f'tools/ref_tile/specs_qkvcentre/{m}.json')['outline']
        box[n] = (x, y, x + ol['w'], y + ol['h'])
    for n, (face, a, b) in fp['pins'].items():               # parent pin spans along a face
        box[n] = dict(N=(a, H, b, H), S=(a, 0, b, 0), W=(0, a, 0, b), E=(W, a, W, b))[face]
    nets = fp['nets']                                        # [name, bits, from, to]
    hops, worst = [], 0.0
    for name, bits, a, b in nets:
        A, B = box[a], box[b]
        # the two facing edges: gap + lateral offset.  Leaf <-> leaf: any pin of one edge to any pin of the other (a
        # slice's bits land anywhere on a fan's edge).  Slot pin span <-> leaf: both are placed in bus order
        # (pin_ranges), so the lateral offset is the larger end-to-end misalignment of the two spans.
        dx = max(0.0, max(A[0], B[0]) - min(A[2], B[2]))
        dy = max(0.0, max(A[1], B[1]) - min(A[3], B[3]))
        ordered = a in fp['pins'] or b in fp['pins']
        def lat(lo1, hi1, lo2, hi2):
            return max(abs(lo1 - lo2), abs(hi1 - hi2)) if ordered else max(abs(hi1 - lo2), abs(hi2 - lo1))
        if dx > 0 and dy == 0:
            d = dx + lat(A[1], A[3], B[1], B[3])
        elif dy > 0 and dx == 0:
            d = dy + lat(A[0], A[2], B[0], B[2])
        else:
            d = dx + dy + (min(A[2] - A[0], B[2] - B[0]) if dx > 0 else 0.0)
        hops.append(dict(net=name, bits=bits, frm=a, to=b, hop_um=round(d, 1)))
        worst = max(worst, d)
    cuts = []
    for kind, pos in [('V', x) for x in fp['cuts_x']] + [('H', y) for y in fp['cuts_y']]:
        n = 0
        for name, bits, a, b in nets:
            A, B = box[a], box[b]
            lo, hi = (min(A[0], B[0]), max(A[2], B[2])) if kind == 'V' else (min(A[1], B[1]), max(A[3], B[3]))
            ca = (A[0] + A[2]) / 2 if kind == 'V' else (A[1] + A[3]) / 2
            cb = (B[0] + B[2]) / 2 if kind == 'V' else (B[1] + B[3]) / 2
            if (ca - pos) * (cb - pos) < 0:
                n += bits
        L = H if kind == 'V' else W
        blocked = 0.0
        for nme, bx in box.items():
            if nme in fp['leaves']:
                if kind == 'V' and bx[0] < pos < bx[2]:
                    blocked += bx[3] - bx[1]
                if kind == 'H' and bx[1] < pos < bx[3]:
                    blocked += bx[2] - bx[0]
        up, lo_ = ('M6', 'M4') if kind == 'V' else ('M7', 'M5')
        tracks = (L / PITCH[up] + (L - blocked) / PITCH[lo_]) * (1 - PG)
        cuts.append(dict(cut=f'{kind}@{pos}', bits=n, tracks=int(tracks), tracks_top_layer_only=int(L / PITCH[up] * (1 - PG)),
                         ratio=round(n / tracks, 3), ratio_top_layer_only=round(n / (L / PITCH[up] * (1 - PG)), 3)))
    out = dict(cluster=spec['name'], outline=[W, H], worst_hop_um=round(worst, 1), hop_limit_um=500, cut_limit=0.60,
               worst_cut=max(c['ratio'] for c in cuts), worst_cut_top_layer_only=max(c['ratio_top_layer_only'] for c in cuts),
               cuts=cuts, hops=sorted(hops, key=lambda h: -h['hop_um']))
    ok = worst <= 500 and out['worst_cut_top_layer_only'] <= 0.60
    out['verdict'] = 'PASS' if ok else 'FAIL'
    if '--json' in argv:
        json.dump(out, open(argv[argv.index('--json') + 1], 'w'), indent=1)
    print(json.dumps({k: out[k] for k in ('cluster', 'outline', 'worst_hop_um', 'worst_cut', 'worst_cut_top_layer_only', 'verdict')}))
    for c in cuts:
        print(' cut', c)
    for h in out['hops'][:6]:
        print(' hop', h)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))

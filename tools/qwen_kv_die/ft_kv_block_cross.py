#!/usr/bin/env python3
"""FT-KV 10-23 (FT-PLAN): which big KV die blocks the die lanes cross, and whether any crossing needs an IN-BLOCK relay.

ESTIMATE pre FT-TOOL census.py: every die bus of a GEN's relay_stages.json whose two ends are single instances in the
coordinator dump (insts.tsv) is routed as the cheaper of its two L paths (centre to centre); per crossed block (>= 0.02
mm2, not an endpoint, not a relay) it sums bits, buses and the longest stretch inside one block.  A stretch longer than
the relay reach (KV 1.2 mm on M8/M9) needs a feedthrough relay inside the block; a shorter one only needs the layers
above the block's contract (route-over).  Output JSON: per master {crossing_bits, buses, max_stretch_um, ft_relay_bits}.
"""
import argparse
import collections
import json
from pathlib import Path

C = 500.0


def load(path):
    I = {}
    for ln in Path(path).read_text().splitlines():
        n, m, x, y, w, h, o = ln.split('\t')
        I[n] = (float(x), float(y), float(w), float(h), m)
    return I


def cross(I, buses, reach=1200.0, min_area=20000.0):
    big = [n for n, v in I.items() if v[2] * v[3] >= min_area and not v[4].startswith('qkd_rly')]
    G = collections.defaultdict(list)
    for n in big:
        x, y, w, h, _ = I[n]
        for gx in range(int(x // C), int((x + w) // C) + 1):
            for gy in range(int(y // C), int((y + h) // C) + 1):
                G[(gx, gy)].append(n)

    def seg(x0, y0, x1, y1):
        out = {}
        if y0 == y1:
            a, b = sorted((x0, x1))
            cand = {n for gx in range(int(a // C), int(b // C) + 1) for n in G.get((gx, int(y0 // C)), [])}
            for n in cand:
                x, y, w, h, _ = I[n]
                if y < y0 < y + h and min(b, x + w) - max(a, x) > 0:
                    out[n] = min(b, x + w) - max(a, x)
        else:
            a, b = sorted((y0, y1))
            cand = {n for gy in range(int(a // C), int(b // C) + 1) for n in G.get((int(x0 // C), gy), [])}
            for n in cand:
                x, y, w, h, _ = I[n]
                if x < x0 < x + w and min(b, y + h) - max(a, y) > 0:
                    out[n] = min(b, y + h) - max(a, y)
        return out

    res = collections.defaultdict(lambda: dict(crossing_bits=0, buses=0, max_stretch_um=0.0, ft_relay_bits=0))
    skipped = 0
    for b in buses:
        s, d = b['src']['inst'], b['dst']['inst']
        if s not in I or d not in I:
            skipped += 1
            continue
        xs, ys = I[s][0] + I[s][2] / 2, I[s][1] + I[s][3] / 2
        xd, yd = I[d][0] + I[d][2] / 2, I[d][1] + I[d][3] / 2
        best = None
        for path in ([(xs, ys, xd, ys), (xd, ys, xd, yd)], [(xs, ys, xs, yd), (xs, yd, xd, yd)]):
            cr = {}
            for sg in path:
                for n, L in seg(*sg).items():
                    if n not in (s, d):
                        cr[n] = cr.get(n, 0.0) + L
            if best is None or sum(cr.values()) < sum(best.values()):
                best = cr
        for n, L in best.items():
            r = res[I[n][4]]
            r['crossing_bits'] += b['width']
            r['buses'] += 1
            r['max_stretch_um'] = round(max(r['max_stretch_um'], L), 1)
            if L > reach:
                r['ft_relay_bits'] += b['width']
    return dict(sorted(res.items(), key=lambda t: -t[1]['crossing_bits'])), skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--relay-stages', required=True)
    ap.add_argument('--insts', required=True)
    ap.add_argument('--reach', type=float, default=1200.0)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    I = load(a.insts)
    res, skipped = cross(I, json.loads(Path(a.relay_stages).read_text())['buses'], a.reach)
    cnt = collections.Counter(v[4] for v in I.values())
    doc = dict(schema='opentallas.ft_kv_block_cross.v0', status='ESTIMATE (L paths centre to centre, pre FT-TOOL census)',
               reach_um=a.reach, buses_skipped_cluster_ends=skipped,
               blocks={m: dict(v, instances=cnt[m]) for m, v in res.items()},
               in_block_ft_relays_needed=sorted(m for m, v in res.items() if v['ft_relay_bits']))
    Path(a.out).write_text(json.dumps(doc, indent=1) + '\n')
    print(json.dumps(doc, indent=1)[:3000])


if __name__ == '__main__':
    main()

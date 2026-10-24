#!/usr/bin/env python3
"""KV plan v3.7t (KV-P7-V38 10-23, GEOM-REVIEW8 FIX (1) + COORD 22:40 (3): die re-window of the hg/hgi N/S stack
edges).  Every port between two vertically stacked hg*/hgi* partitions (astk strip chain, kvs/fch/idhg legs, the N/S
feedthroughs ft2/17/19/24...) had its window in type-frame x 2..520, so all of it rode the head0 / head2 column.  Here
the windows are stretched across the type width in the type frame: x' = 2.16 + (x - 2.16) * S, S = 2.4 (x <= 520 ->
<= 1240), the same in every stacked type, so the columns still abut and pin density drops 2.4x.  Window positions only
(lanes, stations and widths unchanged -> 0 changed-cycle lanes).
usage: post_v37t.py die_plan_v37s.json > die_plan.json"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g2_channels_v37q as G  # noqa: E402
from post_v37s import tmap, to_die  # noqa: E402

S, X0 = 2.4, 2.16


def main():
    raw = json.load(open(sys.argv[1]))
    P = G.S.Plan(raw)
    typ = {n: p['type'] for n, p in P.parts.items()}
    hg = lambda p: typ.get(p, '').startswith('kv3_hg')
    n = 0
    for pr in raw['ports']:
        a, b = pr['src']['part'], pr['dst']['part']
        if not (hg(a) and hg(b)) or pr['face'] not in 'NS' or 'window_um' not in pr:
            continue
        df = pr['face']
        t = sorted(tmap(P, a, df, w)[0] for w in pr['window_um'])
        nt = [X0 + (v - X0) * S for v in t]
        pr['window_um'] = sorted(round(to_die(P, a, df, v), 3) for v in nt)
        pr['note'] = (pr.get('note', '') + ' | v3.7t window stretched x2.4 (hg/hgi N/S re-window)').strip(' |')
        n += 1
    raw['note'] += f' | v3.7t (KV-P7-V38 10-23): {n} hg/hgi N/S stack-edge windows stretched x2.4 across the type'
    sys.stderr.write(f'post_v37t: {n} windows stretched\n')
    json.dump(raw, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()

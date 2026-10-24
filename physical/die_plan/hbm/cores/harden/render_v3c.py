#!/usr/bin/env python3
"""CORE-HBM-REPIN: render a v3c pin file next to the partition it sits in (visual check of the connectivity faces).

Left: the core (R0) with every pin as a tick coloured by its bus (pins of one bus share a colour), per-face count and
pins/um.  Right: the partition type frame: contents (grey), hard cores (blue), the rendered instance (red), and the
partition port windows of the lanes that end on this partition (green ticks).

    python3 render_v3c.py --plan ../../die_plan.json --pins pins_v3c/X.json --part q_sfuc --inst u7_lane0 --out X.png
"""
import argparse
import collections
import json
import re
import zlib

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

import repin_v3c as rv  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--pins', required=True)
    ap.add_argument('--part', required=True)
    ap.add_argument('--inst', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='')
    a = ap.parse_args()
    P = rv.Plan(a.plan)
    ctx = P.part_ctx(a.part)
    t = ctx['t']
    hc = next(h for h in t['hard_cores'] if h['inst'] == a.inst)
    pins = json.load(open(a.pins))
    w = max(p['x'] for p in pins) + rv.INSET
    h = max(p['y'] for p in pins) + rv.INSET
    w, h = (hc['outline_um'] if abs(w - hc['outline_um'][0]) < 1 and abs(h - hc['outline_um'][1]) < 1 else (w, h))
    fig, (A, B) = plt.subplots(1, 2, figsize=(18, 9))
    A.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
    cnt = collections.Counter()
    tick = 0.03 * max(w, h)
    for p in pins:
        f = rv.v2_face(p['x'], p['y'], w, h)
        cnt[f] += 1
        col = plt.cm.tab20((zlib.crc32(rv.base(p['name']).encode()) % 20) / 20)
        if f == 'W':
            A.plot([0, -tick], [p['y']] * 2, color=col, lw=0.4)
        elif f == 'E':
            A.plot([w, w + tick], [p['y']] * 2, color=col, lw=0.4)
        elif f == 'S':
            A.plot([p['x']] * 2, [0, -tick], color=col, lw=0.4)
        else:
            A.plot([p['x']] * 2, [h, h + tick], color=col, lw=0.4)
    for f, (x, y) in dict(N=(w / 2, h + 2 * tick), S=(w / 2, -2.5 * tick), E=(w + 1.3 * tick, h / 2),
                          W=(-1.3 * tick, h / 2)).items():
        L = w if f in 'NS' else h
        A.text(x, y, f'{f}: {cnt[f]} ({cnt[f] / L:.2f}/um)', ha='center', va='center', fontsize=9,
               rotation=90 if f in 'EW' else 0)
    buses = collections.Counter(rv.base(p['name']) for p in pins)
    A.set_title(f'{a.title or a.pins.split("/")[-1]}\n{len(pins)} pins, {len(buses)} buses (colour = bus)', fontsize=9)
    A.set_aspect('equal')
    A.set_xlim(-4 * tick, w + 4 * tick)
    A.set_ylim(-4 * tick, h + 4 * tick)
    W_, H_ = t['outline_um']
    B.add_patch(Rectangle((0, 0), W_, H_, fill=False, lw=1.5))
    for c in t['contents']:
        if 'origin_um' in c:
            B.add_patch(Rectangle(c['origin_um'], *c['outline_um'], fc='0.85', ec='0.6', lw=0.5))
    for x in t.get('hard_cores', []):
        me = x['inst'] == a.inst
        B.add_patch(Rectangle(x['origin_um'], *x['outline_um'], fc='#f4a3a3' if me else '#a9c4eb',
                              ec='r' if me else 'b', lw=1.2 if me else 0.5))
        B.text(x['origin_um'][0] + x['outline_um'][0] / 2, x['origin_um'][1] + x['outline_um'][1] / 2,
               x['inst'], fontsize=5, ha='center', va='center')
    for pt in P.p['ports']:
        for end in ('src', 'dst'):
            if pt[end]['part'] == ctx['pn']:
                x, y = ctx['port_pt'](pt, end)
                B.plot([x], [y], marker='|' if (x in (0, W_)) is False else '_', color='g', ms=4)
    B.set_title(f'partition type {a.part} (rep. instance {ctx["pn"]}, type frame); red = {a.inst}, '
                f'green = lane port windows', fontsize=9)
    B.set_aspect('equal')
    B.set_xlim(-0.03 * W_, 1.03 * W_)
    B.set_ylim(-0.03 * H_, 1.03 * H_)
    fig.tight_layout()
    fig.savefig(a.out, dpi=110)


if __name__ == '__main__':
    main()

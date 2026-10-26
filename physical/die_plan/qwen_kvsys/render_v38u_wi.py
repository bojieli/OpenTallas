#!/usr/bin/env python3
"""KVG3-WI 10-24: render the kv3_hub_Wi host-root cores with their top-down pins (core_pins_hr.py) and partners.

Core boxes (orient label), pins as face ticks coloured by layer (M4/M5 dark, M6/M7 light), purple diamonds = partition
bus windows (check._bus_targets), lines = pin-group -> partner (other core centre / bus window) from the pin-group
centroid, width ~ log(bits); the TOP largest partners per core.  usage: render_v38u_wi.py die_plan.json OUT.png"""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                 # noqa: E402
from matplotlib.patches import Rectangle        # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools/die_plan'))
import check as C                               # noqa: E402
import schema as S                              # noqa: E402

TN = 'kv3_hub_Wi'
TOP = 6          # partners drawn per core (largest bit counts)


def main():
    pp, png = Path(sys.argv[1]), sys.argv[2]
    raw = json.load(open(pp))
    P = S.Plan(raw)
    t = raw['partition_types'][TN]
    W, H = t['outline_um']
    conns = json.load(open(pp.parent / 'core_conns.json')).get(TN, {})
    bt = C._bus_targets(P, TN)
    fig, ax = plt.subplots(figsize=(13, 16))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
    cent = {}
    used = set()
    cmap = plt.get_cmap('tab20')
    for k, hc in enumerate(t['hard_cores']):
        ci, (cw, ch), (ox, oy) = hc['inst'], hc['outline_um'], hc['origin_um']
        o = hc.get('orient', 'R0')
        cent[ci] = (ox + cw / 2, oy + ch / 2)
        ax.add_patch(Rectangle((ox, oy), cw, ch, fc='#e0f4f8', ec='k', lw=0.8))
        ax.text(ox + cw / 2, oy + ch / 2, ci.replace('host__qkd_hr_', '') + f'\n{o}', ha='center', va='center',
                fontsize=7)
    for k, hc in enumerate(t['hard_cores']):
        ci, (cw, ch), (ox, oy) = hc['inst'], hc['outline_um'], hc['origin_um']
        o = hc.get('orient', 'R0')
        if not hc.get('pins_file'):
            continue
        pins = C.core_pins(hc, pp.parent)
        grp = {}
        xs = {'M4': [], 'M5': [], 'M6': [], 'M7': []}
        for nm, ln, x, y in pins:
            tx, ty = C._orient_pt(o, cw, ch, x, y)
            tx, ty = ox + tx, oy + ty
            xs.setdefault(ln, []).append((tx, ty))
            grp.setdefault(nm.rsplit('[', 1)[0], []).append((tx, ty))
        for ln, pts in xs.items():
            if pts:
                ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=0.3,
                           c={'M4': '#c03030', 'M5': '#3050c0', 'M6': '#f0a0a0', 'M7': '#a0b0f0'}[ln], zorder=3)
        col = cmap(k % 20)
        agg = {}
        for base, tags in conns.get(ci, {}).items():
            pts = grp.get(base)
            if not pts:
                continue
            for v in tags:
                kind, _, nm = v.partition(':')
                q = bt.get(nm, (None, None))[1] if kind == 'bus' else cent.get(nm)
                if q is None:
                    continue
                if kind == 'bus':
                    used.add(nm)
                a = agg.setdefault(v, [0, 0.0, 0.0, q])
                a[0] += len(pts)
                a[1] += sum(p[0] for p in pts)
                a[2] += sum(p[1] for p in pts)
        for v, (n, sx, sy, q) in sorted(agg.items(), key=lambda kv: -kv[1][0])[:TOP]:
            ax.plot([sx / n, q[0]], [sy / n, q[1]], color=col, lw=0.4 + 0.5 * math.log10(1 + n), alpha=0.8, zorder=2)
    for nm in sorted(used):
        x, y = bt[nm][1]
        ax.plot([x], [y], 'D', color='#8040a0', ms=4, zorder=4)
        ax.text(x, y, ' ' + nm, fontsize=4, color='#8040a0', rotation=90 if y in (0.0, H) else 0)
    ax.set_xlim(-60, W + 60)
    ax.set_ylim(-60, H + 60)
    ax.set_aspect('equal')
    ax.set_title(f'{TN} {W} x {H} um v3.8u: 22 host-root cores + top-down pins (red M4/M6 E-W faces, blue M5/M7 N-S);\n'
                 f'lines = pin groups -> partner (core centre / purple bus window), {TOP} largest per core, width ~ log bits', fontsize=10)
    fig.savefig(png, dpi=100, bbox_inches='tight')
    print(png)


if __name__ == '__main__':
    main()

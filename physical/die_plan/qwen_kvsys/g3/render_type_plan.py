#!/usr/bin/env python3
"""KV-G3 10-24 (review before route): plan-level picture of one partition type.

Bus windows (check._bus_targets) by face as dots sized by width (blue in / red out), ft slots as in->out legs with
their stations at L*j/k (grey; red if a hop > 675 um), internal_stations paths + regs (green), plan cells with a site
(magenta squares) and their bus-window partners (dotted), hard cores (boxes), R4 clock taps (black +).
usage: render_type_plan.py die_plan.json TYPE OUT.png [OUT.json]"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                 # noqa: E402
from matplotlib.patches import Rectangle        # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / 'tools/die_plan'))
import check as C                               # noqa: E402
import schema as S                              # noqa: E402

HOP = 675.0


def zpath(a, b, fin):
    """the leg as face_flops.ff_zroute does it, roughly: straight across, one jog in the middle"""
    if fin in ('E', 'W'):
        xm = (a[0] + b[0]) / 2
        return [a, (xm, a[1]), (xm, b[1]), b]
    ym = (a[1] + b[1]) / 2
    return [a, (a[0], ym), (b[0], ym), b]


def plen(p):
    return sum(abs(x[0] - y[0]) + abs(x[1] - y[1]) for x, y in zip(p, p[1:]))


def at(p, t):
    for a, b in zip(p, p[1:]):
        d = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if t <= d:
            f = t / d if d else 0
            return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
        t -= d
    return p[-1]


def main():
    pp, tn, png = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    raw = json.load(open(pp))
    P = S.Plan(raw)
    t = raw['partition_types'][tn]
    W, H = t['outline_um']
    bt = C._bus_targets(P, tn)
    bw = {b['name']: (b['width'], b['dir']) for b in t['buses']}
    fig, ax = plt.subplots(figsize=(12, 12 * H / W + 1))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
    for hc in t.get('hard_cores', []):
        (ox, oy), (cw, ch) = hc['origin_um'], hc['outline_um']
        ax.add_patch(Rectangle((ox, oy), cw, ch, fc='#ddd', ec='k', lw=0.8))
        ax.text(ox + cw / 2, oy + ch / 2, hc['inst'], fontsize=5, ha='center')
    st = dict(slots=0, hops=0, hop_max=0.0, hops_gt=0)
    for s in t.get('ft_slots', []):
        a, b = bt.get(s['name'] + '_i'), bt.get(s['name'] + '_o')
        if not a or not b:
            continue
        p = zpath(a[1], b[1], a[0])
        k = int(s.get('stations', 1))
        L = plen(p)
        regs = [tuple(r) for r in s.get('regs_um', [])] or [at(p, L * j / k) for j in range(1, k)]
        pts = [a[1]] + regs + [b[1]]
        hops = [abs(x[0] - y[0]) + abs(x[1] - y[1]) for x, y in zip(pts, pts[1:])]
        st['slots'] += 1
        st['hops'] += len(hops)
        st['hop_max'] = max(st['hop_max'], max(hops))
        st['hops_gt'] += sum(h > HOP for h in hops)
        bad = max(hops) > HOP
        ax.plot([q[0] for q in p], [q[1] for q in p], color='r' if bad else '#bbb', lw=0.3 if not bad else 0.8)
        ax.plot([q[0] for q in regs], [q[1] for q in regs], 's', ms=1.2, color='#666')
    for n, (f, (x, y)) in bt.items():
        if n.startswith('ft'):
            continue
        w, d = bw.get(n, (1, 'in'))
        ax.plot(x, y, 'o', ms=1.5 + min(w, 2048) ** 0.4, color='tab:blue' if d == 'in' else 'tab:red', alpha=0.6)
        if w >= 64:
            ax.text(x, y, f"{n} {w}", fontsize=4)
    for e in t.get('internal_stations', []):
        pts = [e['from_um']] + e['regs_um'] + [e['to_um']]
        ax.plot([q[0] for q in pts], [q[1] for q in pts], '--', color='green', lw=1.0)  # station order (wire is Manhattan)
        ax.plot([q[0] for q in e['regs_um']], [q[1] for q in e['regs_um']], 'D', color='green', ms=4)
        ax.text(*e['regs_um'][0], e.get('conn', ''), fontsize=5, color='green')
    cells = []
    for c in t.get('contents', []):
        if 'origin_um' in c and not c.get('lef'):
            x, y = c['origin_um']
            ax.plot(x, y, 's', color='m', ms=5)
            cells.append(c['inst'])
    for c in t.get('contents', []):
        for lp, v in c.get('bind', {}).items():
            if v.startswith('bus:') and v[4:] in bt and 'origin_um' in c:
                q = bt[v[4:]][1]
                ax.plot([c['origin_um'][0], q[0]], [c['origin_um'][1], q[1]], ':', color='m', lw=0.6)
    for tap in S.tap_grid(P, tn):
        ax.plot(tap[1], tap[2], 'k+', ms=6)
    ax.set_xlim(-30, W + 30)
    ax.set_ylim(-30, H + 30)
    ax.set_aspect('equal')
    ax.set_title(f"{tn} plan {raw.get('version', '')}: windows (blue in / red out), ft legs (red: hop > {HOP:g}), "
                 f"internal stations (green, dashed = order), plan cells (magenta), taps (+)", fontsize=8)
    fig.tight_layout()
    fig.savefig(png, dpi=150)
    st.update(type=tn, plan_cells_sited=cells, internal_stations=len(t.get('internal_stations', [])),
              taps=len(S.tap_grid(P, tn)))
    if len(sys.argv) > 4:
        Path(sys.argv[4]).write_text(json.dumps(st, indent=1))
    print(json.dumps(st))


if __name__ == '__main__':
    main()

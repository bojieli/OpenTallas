#!/usr/bin/env python3
"""Standard die-trial readout (coordinator/owner 10-16) for a die_case_v16.py run.

    die_readout_gcell.py CASE_DIR [--top 20] [--hot 12]

Reads CASE_DIR/out/gcell_usage.txt (sampled GCell capacity/usage per layer, written by run.tcl after global_route),
CASE_DIR/out/layout_dump.json (tools/ref_tile/layout_dump.tcl, OT_LAYOUT_LINKS=1) and CASE_DIR/manifest.json, and writes
  out/die_congestion_flows.png  GRT congestion heat map (max over M4..M9 of usage/capacity per sampled GCell) with every
                                block outline and the top-N data flows (bits) as lines
  out/hotspots.json             the hottest windows (1 mm), each with its measured numbers and a class:
                                pin-face/density | partner placement | channel/metal margin | clock/relay structure
Classification rule (measured, per window): clock/relay structure when die clock/relay cells own >= 30 % of the cells
in the window; pin-face/density when a block face with >= 1 pin/um faces the window and lies within 50 um;
partner placement when >= 50 % of the crossing bits connect blocks whose centres are > 3 mm apart; otherwise
channel/metal margin (the window is a plain channel short of tracks).
"""
import argparse, json, math, re
from collections import defaultdict
from pathlib import Path


def gcells(p):
    gx = gy = None; sx = sy = 1; L = defaultdict(dict)
    for line in Path(p).read_text().splitlines():
        a = line.split()
        if a[0] == 'GRIDX':
            gx = [int(v) for v in a[1].split(',')]
        elif a[0] == 'GRIDY':
            gy = [int(v) for v in a[1].split(',')]
        elif a[0] == 'STRIDE':
            sx, sy = int(a[1]), int(a[2])
        elif a[0] == 'L':
            L[a[1]][int(a[2])] = [tuple(int(x) for x in c.split('/')) for c in a[3:]]
    return gx, gy, sx, sy, L


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('case', type=Path); ap.add_argument('--top', type=int, default=20); ap.add_argument('--hot', type=int, default=12)
    ap.add_argument('--dbu', type=float, default=1000.0)
    a = ap.parse_args()
    out = a.case / 'out'
    man = json.loads((a.case / 'manifest.json').read_text())
    D = json.loads((out / 'layout_dump.json').read_text())
    gx, gy, sx, sy, L = gcells(out / 'gcell_usage.txt')
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    rows = sorted(next(iter(L.values())).keys())
    ncol = len(next(iter(next(iter(L.values())).values())))
    R = np.zeros((len(rows), ncol)); per = {}
    for ln, rr in L.items():
        m = np.array([[u / c if c else (2.0 if u else 0.0) for c, u in rr[j]] for j in rows])
        per[ln] = m
        R = np.maximum(R, m)
    xs = [gx[i] / a.dbu for i in range(0, len(gx), sx)][:ncol]
    ys = [gy[j] / a.dbu for j in rows]
    W, H = man['die_um']
    blocks = D.get('blocks', [])
    cen = {b[0]: ((b[2] + b[4]) / 2, (b[3] + b[5]) / 2) for b in blocks}
    links = sorted(D.get('links', []), key=lambda t: -t[2])
    fig, ax = plt.subplots(figsize=(18, 13.5))
    im = ax.imshow(np.clip(R, 0, 1.5), origin='lower', extent=(0, W, 0, H), cmap='inferno', vmin=0, vmax=1.5, aspect='equal')
    plt.colorbar(im, ax=ax, fraction=0.025, label='max layer usage / capacity (M4..M9), sampled GCells')
    for b in blocks:
        ax.add_patch(Rectangle((b[2], b[3]), b[4] - b[2], b[5] - b[3], fill=False, lw=0.25, color='cyan'))
    bmax = max([l[2] for l in links[:a.top]] or [1])
    for k, (s, t, n) in enumerate(links[:a.top]):
        if s in cen and t in cen:
            (x0, y0), (x1, y1) = cen[s], cen[t]
            ax.plot([x0, x1], [y0, y1], color='lime', lw=0.6 + 3.5 * n / bmax, alpha=0.8)
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, f'{k + 1}:{n}', color='lime', fontsize=5)
    ax.set_title(f"{D.get('top', 'die')}: GRT congestion + block outlines + top-{a.top} data flows (bits); "
                 f"{man.get('label', '')[:60]}", fontsize=8)
    fig.savefig(out / 'die_congestion_flows.png', dpi=120, bbox_inches='tight')
    # hot windows (1 mm)
    win = 1000.0
    nwx, nwy = int(math.ceil(W / win)), int(math.ceil(H / win))
    acc = defaultdict(list)
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            acc[(int(x // win), int(y // win))].append(R[j, i])
    hot = sorted(((max(v), float(np.mean(v)), k) for k, v in acc.items() if v), reverse=True)[:a.hot]
    pl = man['placement']
    face = man.get('face_bits', {})
    res = []
    for mx, mean, (wi, wj) in hot:
        x0, y0, x1, y1 = wi * win, wj * win, (wi + 1) * win, (wj + 1) * win
        inside = [n for n, v in pl.items() if v['x'] < x1 and v['x'] + v['w'] > x0 and v['y'] < y1 and v['y'] + v['h'] > y0]
        rly = [n for n in inside if v_m(pl[n]).startswith('hbfd_rly')]
        near = [n for n in inside if not v_m(pl[n]).startswith('hbfd_rly')]
        # densest block face within the window: bits / face length
        dens = []
        for n in near:
            v = pl[n]; fb = face.get(v['m'], {})
            for f, bits in fb.items():
                Lf = v['w'] if f in 'NS' else v['h']
                dens.append((bits / max(Lf, 1e-3), n, f, bits))
        dens.sort(reverse=True)
        cross = [(s, t, n) for s, t, n in links if s in cen and t in cen and
                 _seg_hits(cen[s], cen[t], (x0, y0, x1, y1))]
        cb = sum(n for _, _, n in cross) or 1
        far = sum(n for s, t, n in cross if abs(cen[s][0] - cen[t][0]) + abs(cen[s][1] - cen[t][1]) > 3000)
        ck = man.get('clock_buffers_in_window', {}).get(f'{wi},{wj}', 0)
        if len(rly) + ck >= 0.3 * max(1, len(inside) + ck) and (rly or ck):
            cls_, fix = 'clock/relay structure', 'spread relay/clock cells over the channel width; carve or widen the channel they share'
        elif dens and dens[0][0] >= 1.0:
            cls_, fix = 'pin-face/density', f'spread {dens[0][1]} {dens[0][2]}-face pins ({dens[0][3]} b) over more face / move to its peer face'
        elif far >= 0.5 * cb:
            cls_, fix = 'partner placement', 'move the far partners together (the bits cross this window only because they are far apart)'
        else:
            cls_, fix = 'channel/metal margin', 'widen the channel or grant more upper metal (M6-M9) over it'
        res.append(dict(window_um=[x0, y0, x1, y1], max_usage=round(float(mx), 3), mean_usage=round(mean, 3),
                        layer_max={ln: round(float(per[ln][[k for k, y in enumerate(ys) if y0 <= y < y1]][:, [k for k, x in enumerate(xs) if x0 <= x < x1]].max()), 3)
                                   for ln in per},
                        blocks=near[:12], relays=len(rly), densest_face=dens[0][1:] + (round(dens[0][0], 2),) if dens else None,
                        crossing_bits=cb, far_partner_bits=far, cls=cls_, fix=fix,
                        top_crossing=[f'{s}->{t}:{n}' for s, t, n in sorted(cross, key=lambda c: -c[2])[:5]]))
    (out / 'hotspots.json').write_text(json.dumps(res, indent=1))
    for r in res:
        print(r['window_um'], r['max_usage'], r['cls'], r['densest_face'], r['top_crossing'][:2])
    print('PNG', out / 'die_congestion_flows.png')


def v_m(v):
    return v['m']


def _seg_hits(p, q, box):
    """L-shaped (x then y) route from p to q crosses box"""
    (x0, y0), (x1, y1) = p, q
    bx0, by0, bx1, by1 = box
    h = min(x0, x1) <= bx1 and max(x0, x1) >= bx0 and by0 <= y0 <= by1
    v = min(y0, y1) <= by1 and max(y0, y1) >= by0 and bx0 <= x1 <= bx1
    return h or v


if __name__ == '__main__':
    main()

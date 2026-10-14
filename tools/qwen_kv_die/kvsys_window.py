#!/usr/bin/env python3
"""qwen-split/kvsys 2026-10-14: 2-D WINDOW routing-demand check of a KV / KV-system die plan (the HBM v12 lesson: a hot
corner that no straight cut line sees).  Every relay-staged die bus segment is routed as an L between its drawn pins
(half the bits H-then-V, half V-then-H); each window of FINE um (and COARSE um) accumulates the bits that cross it
horizontally (H demand: tracks on M4 / M6 / M8) and vertically (V demand: M5 / M7 / M9).

Capacity per window and direction (the TP8 SPEC cut rule, results/arch/qwen_tp8_1012/cuts.py): over a hard block only the
die layer (M8 H / M9 V) at 75 % after the die PDN = 9.375 tracks/um; in a channel add M6/M7 at 75 % and M4/M5 at 50 % =
31.5 tracks/um; a window mixes the two by its block-covered fraction across the direction of travel.
Target <= 0.55 (owner: 0.55-0.60). Clock / reset / constant nets are CTS / reset-tree routed.
Every nonzero signal segment is counted, including classes intended to abut.

    python3 tools/qwen_kv_die/kvsys_window.py [--split] [--fine 260] [--coarse 1040] --out OUT.json
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_die as K  # noqa: E402

BLOCK_TPU = 0.75 / 0.080                     # die layer over a block
CHAN_TPU = 0.75 / 0.080 + 0.75 / 0.064 + 0.5 / 0.048


def scan(m, M, win):
    W, H = m['die']['w'], m['die']['h']
    nx, ny = int(np.ceil(W / win)), int(np.ceil(H / win))
    by = {i.name: i for i in m['insts']}
    # block coverage per window (relays excluded: they are die-top logic in the channels)
    cov = np.zeros((nx, ny))
    sub = 8
    for it in m['insts']:
        if it.master.startswith('qkd_rly') or it.w * it.h < 0.04e6 * 0 + 1.0:
            continue
        x0, x1, y0, y1 = it.x, it.x + it.w, it.y, it.y + it.h
        for gx in range(max(0, int(x0 // win)), min(nx, int(x1 // win) + 1)):
            for gy in range(max(0, int(y0 // win)), min(ny, int(y1 // win) + 1)):
                ox = max(0.0, min(x1, (gx + 1) * win) - max(x0, gx * win))
                oy = max(0.0, min(y1, (gy + 1) * win) - max(y0, gy * win))
                cov[gx, gy] += ox * oy / (win * win)
    cov = np.clip(cov, 0.0, 1.0)
    cap = win * (cov * BLOCK_TPU + (1.0 - cov) * CHAN_TPU)
    dh, dv = np.zeros((nx, ny)), np.zeros((nx, ny))
    who_h, who_v = defaultdict(Counter), defaultdict(Counter)

    def pt(inst, port):
        it = by[inst]
        try:
            return K.pin_xy(it, M[it.master], port.lstrip('*'))
        except Exception:
            return (it.x + it.w / 2, it.y + it.h / 2)

    def hseg(x0, x1, y, bits, bid):
        if abs(x1 - x0) < 1e-6:
            return
        if x1 < x0:
            x0, x1 = x1, x0
        gy = min(ny - 1, max(0, int(y // win)))
        for gx in range(max(0, int(x0 // win)), min(nx, int(x1 // win) + 1)):
            dh[gx, gy] += bits
            who_h[(gx, gy)][bid] += bits

    def vseg(y0, y1, x, bits, bid):
        if abs(y1 - y0) < 1e-6:
            return
        if y1 < y0:
            y0, y1 = y1, y0
        gx = min(nx - 1, max(0, int(x // win)))
        for gy in range(max(0, int(y0 // win)), min(ny, int(y1 // win) + 1)):
            dv[gx, gy] += bits
            who_v[(gx, gy)][bid] += bits
    for bid, cl, bits, eps in m['buses']:
        if cl in ('clock_trunk', 'reset', 'constant') or len(eps) < 2:
            continue
        base = bid.split('__')[0]
        a = pt(*eps[0])
        for e in eps[1:]:
            b = pt(*e)
            h1, h2 = bits / 2.0, bits - bits / 2.0
            hseg(a[0], b[0], a[1], h1, base); vseg(a[1], b[1], b[0], h1, base)      # H then V
            vseg(a[1], b[1], a[0], h2, base); hseg(a[0], b[0], b[1], h2, base)      # V then H
    uh, uv = dh / cap, dv / cap
    rows = []
    for (u, d, who, dirn) in ((uh, dh, who_h, 'H'), (uv, dv, who_v, 'V')):
        for gx, gy in zip(*np.unravel_index(np.argsort(-u, axis=None)[:12], u.shape)):
            rows.append(dict(dir=dirn, util=round(float(u[gx, gy]), 3), bits=round(float(d[gx, gy])), cap=round(float(cap[gx, gy])),
                             window_um=[round(gx * win, 1), round(gy * win, 1), round((gx + 1) * win, 1), round((gy + 1) * win, 1)],
                             block_cover=round(float(cov[gx, gy]), 2), top=who[(gx, gy)].most_common(4)))
    rows.sort(key=lambda r: -r['util'])
    return dict(window_um=win, grid=[nx, ny], max_util_h=round(float(uh.max()), 3), max_util_v=round(float(uv.max()), 3),
                over_055=int(((uh > 0.55) | (uv > 0.55)).sum()), over_060=int(((uh > 0.60) | (uv > 0.60)).sum()),
                windows=int(nx * ny), hot=rows[:16])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--split', action='store_true')
    ap.add_argument('--fine', type=float, default=260.0)
    ap.add_argument('--coarse', type=float, default=1040.0)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    m = K.build(kv_wq_leaves=True, kv_wq_binary=True, kv_wq_leaf_s=True, kv_wq_wide=True, kv_wq_mirror=True, split=a.split)
    M = K.masters(m, 1)
    rec = dict(schema='opentallas.qwen_kvsys_window.v1', split=a.split, die_um=[m['die']['w'], m['die']['h']],
               rule='L-routes between drawn pins, 50/50 H-V / V-H; capacity 9.375 tr/um over blocks, 31.5 in channels',
               fine=scan(m, M, a.fine), coarse=scan(m, M, a.coarse))
    a.out.write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(json.dumps({k: (dict(max_h=v['max_util_h'], max_v=v['max_util_v'], over_055=v['over_055'], over_060=v['over_060'])
                          if isinstance(v, dict) and 'max_util_h' in v else v) for k, v in rec.items() if k != 'rule'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())

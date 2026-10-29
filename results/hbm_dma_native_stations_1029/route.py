#!/usr/bin/env python3
"""Count/geometry preparation using actual per-bit endpoints and station_resite.

Two legal endpoint banks cover every native bit pin. The shared exact-count
solver connects those banks. This does not claim body placement or capacity.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
import multiprocessing as mp
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import station_resite as SR
import hub_repack as HR

FREE = None
RECTS = None
REACH = 364.5


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def endpoint_home(points, target):
    """Minimax legal site over all exact bit pins, with target-distance tiebreak."""
    p = np.asarray(points)
    x = np.arange(FREE.shape[0])[:, None] * HR.G
    y = np.arange(FREE.shape[1])[None, :] * HR.G
    u, v = p[:, 0] + p[:, 1], p[:, 0] - p[:, 1]
    d = np.maximum.reduce(np.broadcast_arrays(x+y-u.min(), u.max()-x-y,
                                              x-y-v.min(), v.max()-x+y))
    legal = FREE & (d <= REACH + 1e-6)
    if not legal.any():
        raise ValueError('no free endpoint bank reaches every native bit within canonical reach')
    score = d + 0.001 * (abs(x-target[0]) + abs(y-target[1]))
    i, j = np.unravel_index(np.where(legal, score, np.inf).argmin(), FREE.shape)
    return [round(float(i*HR.G), 6), round(float(j*HR.G), 6)]


def solve(group):
    src = [p['src']['xy_um'] for p in group['pairs']]
    dst = [p['dst']['xy_um'] for p in group['pairs']]
    a = endpoint_home(src, np.mean(dst, axis=0))
    b = endpoint_home(dst, np.mean(src, axis=0))
    regs = None
    lower = max(0, math.ceil(man(a, b) / REACH - 1e-9) - 1)
    if man(a, b) <= REACH:
        regs = [a] if a == b else [a, b]
    else:
        for n in range(max(1, lower), max(1, lower) + 12):
            middle = SR.route(FREE, a, b, n, REACH)
            if middle is not None:
                regs = [a] + [list(p) for p in middle] + [b]
                break
    if regs is None:
        return dict(bank=group['bank'], kind=group['kind'], verdict='FAIL',
                    reason='no exact-count shared station_resite route after lower bound +11 attempts')
    hops = [man(p, q) for p, q in zip(regs, regs[1:])]
    hops += [man(p, regs[0]) for p in src] + [man(regs[-1], p) for p in dst]
    blocked = [r for r in regs if SR.blocked(RECTS, r)]
    if blocked or max(hops) > REACH + 1e-5:
        raise ValueError(f'invalid solver result blocked={blocked[:1]} maxhop={max(hops)}')
    # Request and response are native source buses, including their own valid bit.
    # No epoch, serial narrowing, or unconstrained phantom bits are introduced.
    return dict(bank=group['bank'], kind=group['kind'], verdict='PASS', width=group['width'],
                stations=len(regs), registered_bits=len(regs)*group['width'], regs_um=regs,
                max_bit_hop_um=round(max(hops), 6), source_escape_um=a, sink_escape_um=b,
                source_pin_hop_max_um=round(max(man(p, regs[0]) for p in src), 6),
                sink_pin_hop_max_um=round(max(man(regs[-1], p) for p in dst), 6),
                source=group['source'], sink=group['sink'], valid_src_bit=group['valid_src_bit'],
                valid_dst_bit=group['valid_dst_bit'], endpoint_pin_pairs=group['pairs'],
                qualification='station-center geometry/count preparation; actual per-bit FF packing/capacity and RTL adoption not run')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prepared', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    prepared = Path(a.prepared)
    t = json.loads((prepared/'type.json').read_text())
    proj = json.loads((prepared/'pin_projection.json').read_text())
    global FREE, RECTS
    RECTS = SR.core_rects(t)
    FREE = HR.Raster(*t['outline_um'], [r[1:] for r in RECTS]).f
    FREE[0, :] = FREE[-1, :] = FREE[:, 0] = FREE[:, -1] = False
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with ProcessPoolExecutor(a.jobs, mp_context=mp.get_context('fork')) as pool:
        fs = [pool.submit(solve, g) for g in proj['groups']]
        for f in as_completed(fs):
            row = f.result()
            (out/f"bank{row['bank']}_{row['kind']}.json").write_text(json.dumps(row, indent=1)+'\n')
            rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k not in ('endpoint_pin_pairs', 'regs_um')}), flush=True)
    rows.sort(key=lambda r: (r['bank'], r['kind']))
    budget = []
    for bank in range(8):
        by = {r['kind']: r for r in rows if r['bank'] == bank}
        if all(by[k]['verdict'] == 'PASS' for k in ('request', 'return')):
            q, r = by['request']['stations'], by['return']['stations']
            budget.append(dict(bank=bank, request_stages=q, return_stages=r,
                               producer_rr_rt=80, intrinsic_bank_launch_cycles=7,
                               request_padding_candidate=80-7-q-r, padding_adopted=False,
                               request_padding_bits=17*max(0, 80-7-q-r),
                               response_padding_bits=257*max(0, 80-7-q-r),
                               request_option='moves bank read sample date; compiler write/version window proof required',
                               response_option='preserves bank read sample date; >2kb storage requires priced SRAM design'))
    summary = dict(schema='hbm.native_dma.station_count_prep.v1', reach_um=REACH, halo_um=HR.HALO,
                   groups=len(rows), failures=sum(r['verdict'] != 'PASS' for r in rows),
                   physical_cores=len(RECTS), budget=budget,
                   registered_bits=sum(r.get('registered_bits', 0) for r in rows),
                   max_bit_hop_um=max(r.get('max_bit_hop_um', 0) for r in rows),
                   qualification='plan geometry/count preparation only; no per-bit FF body packing, routability, timing, exactness, or token-pass claim')
    (out/'summary.json').write_text(json.dumps(summary, indent=1)+'\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()

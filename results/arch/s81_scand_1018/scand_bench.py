#!/usr/bin/env python3
"""S81-SCAND (10-18): the S81 index-scan reader at p4l's ONE HBM3E stack a die, with option D's distributed key layout.

Bench = the 10-04 W11 quarter-per-stack reader (tools/w11_idx_reader_rate.py layout "quarter_stack":
ot_hdc_v41x_idx_kstream_range per stack + the refresh-aware per-PC HBM model ot_hdc_v41x_idx_hbm, NPC 32 = one HBM3E
stack, every key / lane mask / last flag / refusal bit checked).  Its four stacks are independent (one kstream + one HBM
model each, the join never back-pressures: o_ready 1), so bench stack s = ONE p4l die reading its own share:
NKEYS = 4 x M measures one die scanning M keys from its one stack.

Option D spreads a full-scan layer's rank keys (L20 ratio 1: 262,144; L2/L8/L14 ratio 2: 131,072) over k adjacent TP4
stages, so each die scans M = ceil(K / k) keys (k = 1 is today's p4l: the whole rank on one stack).  The bench's quarter
partition gives stack 3 the remainder; the cycle count is the slowest stack (M or a few keys more, never fewer).

Two ring placements bound the super-block head offsets (as 10-04): default (BASE 0, BSTEP 1000, OSTEP 136) and
placement2 (BASE 123, BSTEP 777, OSTEP 8).  CLK_PS 833 (1.2 GHz), WB 128, GA 120 (the 10-04 S81 configuration).

  python3 results/arch/s81_scand_1018/scand_bench.py --out DIR [--jobs N] [--only name,...]
writes DIR/reader_1stack.json.  Run on the fleet with Verilator 5.050 first on PATH.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import w11_idx_reader_rate as W  # noqa: E402

RANK_KEYS = {'L20': 262144, 'L2': 131072}
CFG = dict(CLK_PS=833, WB=128, GA=120)
PLACEMENTS = {'p1': {}, 'p2': dict(BASE=123, BSTEP=777, OSTEP=8)}


def per_die(K, k):
    return math.ceil(K / k)


def runs():
    seen, out = {}, []
    for lay, K in RANK_KEYS.items():
        for k in (1, 2, 3, 4):
            M = per_die(K, k)
            seen.setdefault(M, []).append(f'{lay}_k{k}')
    for M, uses in sorted(seen.items(), reverse=True):
        for p, extra in PLACEMENTS.items():
            out.append((f'die_keys_{M}_{p}', 4 * M, dict(CFG, **extra), M, uses))
    return out


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    out = a.out.resolve()
    (out / 'build').mkdir(parents=True, exist_ok=True)
    only = set(filter(None, a.only.split(',')))

    def one(r):
        name, n, params, M, uses = r
        t0 = time.time()
        row = W.build_and_run((name, 'quarter_stack', n, params, 's81_scand'), out / 'build')
        row.update(wall_s=round(time.time() - t0, 1), die_keys=M, used_for=uses,
                   per_stack_keys=[(n // 32) * 8] * 3 + [n - 3 * (n // 32) * 8],
                   one_stack_peak_sectors_per_cycle=round(W.NPC * params['CLK_PS'] / W.BURST_PS, 3))
        row['one_stack_efficiency'] = round(row['sectors'] / 4 / row['cycles'] / row['one_stack_peak_sectors_per_cycle'], 4)
        print(f"{name:28s} M={M:7d} cycles={row['cycles']:6d} eff={row['one_stack_efficiency']:.4f}", flush=True)
        return row

    todo = [r for r in runs() if not only or r[0] in only]
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(one, todo))
    ver = subprocess.run(['verilator', '--version'], capture_output=True, text=True).stdout.strip()
    srcs = {p: sha(p) for p in sorted(set(W.QS_SOURCES + [W.QS_CPP, 'tools/w11_idx_reader_rate.py',
                                                          'results/arch/s81_scand_1018/scand_bench.py']))}
    rec = dict(schema='opentallas.s81_scand.reader_1stack.v1', lane='S81-SCAND', simulator=ver, source_sha256=srcs,
               method=__doc__.split('\n\n')[1], rank_keys=RANK_KEYS, runs=rows,
               status='pass' if rows and all(r['checked_keys'] == r['keys'] for r in rows) else 'fail')
    (out / 'reader_1stack.json').write_text(json.dumps(rec, indent=1) + '\n')
    print('STATUS', rec['status'], ver)


if __name__ == '__main__':
    main()

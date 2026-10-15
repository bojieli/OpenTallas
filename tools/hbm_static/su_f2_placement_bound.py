#!/usr/bin/env python3
"""SU.VOP F2 (four-quarter) VM transport bound per canonical record, before and after quarter-balanced placement.

Model before RTL (owner 10-14 21:35 decision: (c) F2 four-quarter composition + operand reuse, and (a1) VM slices at
833 ps).  Input: the actual canonical tensor plans written by su_tensor_plan.py (224c1359b), which keep the compiler's
current VM word identity: sector s lives in slice SID = s[14:13], bank = s[2:0] (SID-major, 2^13 sectors = 64 Ki words a
slice).  Each of the 32 static VM banks (4 slices x 8, ot_vms_bank_static, all on pll_stream 833.333 ps in the v15 source
contract) serves one read sector and one write sector per engine edge, compiler slotted, no queues.

  L0  current placement: stage edges = max per-bank read sectors, drain edges = max per-bank write sectors.
  L1  F2 quarter-balanced placement (compiler allocates quarter q's partition of every tensor in slice q, spread over its
      8 banks): stage = ceil(read sectors / 32), drain = ceil(write sectors / 32).
A record's transport bound is max(stage, drain) (separate read and write ports).  Arithmetic, reduction carry, SRAM
dispatch network and pipeline fill are NOT included: these are lower bounds, never a service measurement.
"""
import argparse
import gzip
import json
import math
from pathlib import Path


def bound(plan):
    rows = []
    for r in plan['records']:
        stage = sum(len(s) for s in r['stage_sector_slots'])
        drain = len(r['drain_masks'])
        dbank = [0] * 32
        for v in r['drain_native'].values():
            dbank[v['SID'] * 8 + v['bank']] += 1
        sids = sorted({i // 8 for i, n in enumerate(r['stage_bank_counts']) if n})
        l0 = max(r['stage_minimum_edges'], max(dbank))
        l1 = max(math.ceil(stage / 32), math.ceil(drain / 32))
        rows.append(dict(tag=r['tag'], priced=r['priced_cycles'], stage_sectors=stage, drain_sectors=drain,
                         stage_sids=sids, stage_banks_used=sum(1 for n in r['stage_bank_counts'] if n),
                         L0_edges=l0, L1_edges=l1, L0_over_price=l0 > r['priced_cycles'],
                         L1_over_price=l1 > r['priced_cycles']))
    tot = dict(priced=sum(x['priced'] for x in rows), L0=sum(x['L0_edges'] for x in rows),
               L1=sum(x['L1_edges'] for x in rows))
    tot['L0_ratio'] = round(tot['L0'] / tot['priced'], 3)
    tot['L1_ratio'] = round(tot['L1'] / tot['priced'], 3)
    return dict(records=rows, total=tot,
                L0_over=[(x['tag'], x['L0_edges'], x['priced']) for x in rows if x['L0_over_price']],
                L1_over=[(x['tag'], x['L1_edges'], x['priced']) for x in rows if x['L1_over_price']])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plans', type=Path, default=Path(__file__).resolve().parents[2] /
                    'results/arch/hbm_su_f2_static_1014/tensor_plan')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    res = dict(schema='opentallas.hbm.su_f2_placement_bound.v1', tool='tools/hbm_static/su_f2_placement_bound.py',
               qualification=False, kind='transport lower bound (model before RTL), not a service measurement',
               designs={})
    for name in ('deepseek', 'qwen'):
        p = a.plans / f'{name}.json.gz'
        res['designs'][name] = bound(json.loads(gzip.decompress(p.read_bytes())))
        t = res['designs'][name]['total']
        print(name, t, 'L1 over price:', res['designs'][name]['L1_over'])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + '\n')


if __name__ == '__main__':
    main()

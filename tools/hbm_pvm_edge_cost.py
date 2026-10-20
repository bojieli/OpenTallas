#!/usr/bin/env python3
"""e2e price of the PVM distributed-source +N edge (L2H-SMATT/PVMD 2026-10-19, H.STA.BLK.14.3.1).

ot_hbm_sm_pv_merge_distributed registers every input twice at the source (2 input edges, was 1 automatic pin register)
and keeps one output edge, so every PV-merge result (pv_v / pub_v) leaves the tile N = 1 edge later; the II-1 merge
stream, the 8-edge barrel and the fold/publication calendar are unchanged (bench: candidate == SAFE2 reference at +1
age, every output bit every edge).  The +1 cold reset-release edge is paid once at reset, not per token.
Method = tools/throughput/accepted_cost.py hbm_schedule (as tools/hbm_coll_static/injlat_cost.py --issue-edges): S2
schedule of the exact per-die program, +N cycles on every record of the ops whose result passes the PV merge leaf
(default ATT.PV; edges counted 1:1 as schedule cycles, conservative).
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'tools/throughput')); sys.path.insert(0, str(ROOT / 'src'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edges', type=int, nargs='*', default=[1])
    ap.add_argument('--ops', nargs='*', default=['ATT.PV'])
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    import accepted_cost as A
    out = {'schema': 'opentallas.hbm.pvm_edge_cost.v1', 'mechanism': __doc__, 'ops': a.ops, 'workloads': {}}
    for model in ('ds', 'qwen'):
        run, count = A.hbm_schedule(model)
        base = run()
        ops = [o for o in a.ops if count.get(o)]
        rows = []
        for n in a.edges:
            per_op = {}
            for op in ops:
                one = run(op, 1.0, float(n))
                per_op[op] = {'records': count[op], 'cycles_per_record': n, 'added_cycles': round(one - base, 1)}
            new = run(ops[0], 1.0, float(n)) if len(ops) == 1 else None
            if new is None:
                new = base + sum(v['added_cycles'] for v in per_op.values())    # several ops: additive (conservative)
            rows.append({'edges': n, 'base_cycles': round(base, 1), 'cycles': round(new, 1), 'added_cycles': round(new - base, 1),
                         'e2e_loss_pct': round(100 * (1 - base / new), 4), 'per_op': per_op})
            print(model, 'edges', n, 'base', round(base, 1), 'added', round(new - base, 1), 'loss%', rows[-1]['e2e_loss_pct'])
        out['workloads'][model] = {'records': {o: count.get(o, 0) for o in a.ops},
                                   'att_ops': {k: v for k, v in count.items() if k.startswith('ATT.')}, 'rows': rows}
    if a.out:
        a.out.write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()

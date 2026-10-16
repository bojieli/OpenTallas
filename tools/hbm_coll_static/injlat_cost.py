#!/usr/bin/env python3
"""e2e cost of raising the COLL SU-inject latency INJLAT (H-NETLIST/coll 2026-10-16).

Mechanism (ot_hfd_coll_q_static_v4 INJLAT, request P -> qslots capture P+INJLAT; SU 3:4 phase rule of
H-NETLIST/suport: no SU-bound stream event at (P+1+Rq) mod 4 == 2):
  * every COLL op whose sources are SU inject words pays dINJLAT = INJLAT-12 once a record (pipelined requests);
  * COLL.GROUP_REDUCE_MCAST: measured delta of the production compiler tools/hbm_coll_static/g96_calendar.py
    (--injlat I --su-rq 0) against INJLAT 12 (passed in with --g96 I:cycles ...);
  * COLL.ALL_GATHER injects 96 flits a quadrant at 2 a cycle = 48 beats; the phase rule allows 3 of 4 edges, so the
    inject stream takes 64 edges: +16 a record on top of dINJLAT (the rails take 1 flit/cycle each, so the inject is
    the pace setter);
  * COLL.ALL_REDUCE_SUM (qwen): dINJLAT + ceil(beats/3) with beats = its inject beats (charged as 16, conservative);
  * COLL.TOPK_MERGE (IDX frames through cij_SW, no SU phase rule) and COLL.ARGMAX_MERGE: dINJLAT;
  * COLL.ROW_GATHER sources VM words (vm_rq, no SU inject): 0.
Method = tools/throughput/accepted_cost.py hbm_schedule: S2 schedule of the exact per-die program, fixed cycles
added to every record of each op (edges counted 1:1 as schedule cycles, conservative).
"""
import argparse, collections, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'tools/throughput')); sys.path.insert(0, str(ROOT / 'src'))


def schedule(model):
    from hgi_sim import timing as T
    import accepted_cost as A
    # reuse accepted_cost's loader, then schedule with a per-op delta table
    run, count = A.hbm_schedule(model)
    cf_holder = {}
    # accepted_cost.run only supports one op; rebuild the same recs/cost to apply several deltas
    if model == 'ds':
        from hgi_sim import ds_native_timing as DT
        res = ROOT / 'results/arch/hgi_sim_20261010/g25_proof'
        d, recs = DT.load(res / 'ds_rank0_program.json'); recs = T.rebuild_waits(recs)
        rg = {}
        for x in json.loads((res / 'ds_full.json').read_text())['results']:
            for s_ in x.get('row_gather') or []: rg[x['layer']] = s_
        DT.apply_dyn_counts(recs, rg); cf, pos = DT.NativeCost(d['ops'], recs, row_gather=rg), DT.POS
    else:
        from hgi_sim import qwen_compiler as QC
        cfg = json.loads((ROOT / 'compiler/models/qwen3-8b/config.json').read_text())
        recs = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), cfg['num_hidden_layers']); cf, pos = T.cost, 8191

    def run_d(delta):
        def g(r, dyn, L):
            c = cf(r, dyn, L)
            return c[0] + delta.get(f'{r.unit}.{r.op}', 0.0), c[1], c[2]
        return T.schedule(recs, pos, 'S2', cost_fn=g)['total_cycles']
    return run_d, count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--injlat', type=int, nargs='+', default=[12, 14, 16, 20, 24, 30, 36, 48])
    ap.add_argument('--g96', nargs='*', default=[], help='I:cycles of g96_calendar --injlat I --su-rq 0')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    g96 = {int(k): float(v) for k, v in (x.split(':') for x in a.g96)}
    base_g96 = g96.get(12)
    out = {'schema': 'opentallas.hcoll.injlat_cost.v1', 'method': __doc__.strip().splitlines()[0], 'mechanism': __doc__,
           'g96_cycles': g96, 'workloads': {}}
    for model in ('ds', 'qwen'):
        run, count = schedule(model)
        base = run({})
        rows = []
        for I in a.injlat:
            dI = I - 12
            dg = (g96[I] - base_g96) if (I in g96 and base_g96) else dI
            delta = {'COLL.ALL_GATHER': dI + 16, 'COLL.GROUP_REDUCE_MCAST': dg, 'COLL.ALL_REDUCE_SUM': dI + 16 / 3 + 1,
                     'COLL.TOPK_MERGE': dI, 'COLL.ARGMAX_MERGE': dI, 'COLL.ROW_GATHER': 0}
            new = run(delta)
            per_op = {}
            for op, dv in delta.items():
                if count.get(op) and dv:
                    one = run({op: dv})
                    per_op[op] = {'records': count[op], 'cycles_per_record': round(dv, 2), 'added_cycles': round(one - base, 1),
                                  'e2e_loss_pct': round(100 * (1 - base / one), 3)}
            rows.append({'injlat': I, 'base_cycles': round(base, 1), 'cycles': round(new, 1), 'added_cycles': round(new - base, 1),
                         'e2e_loss_pct': round(100 * (1 - base / new), 3), 'per_op': per_op})
        out['workloads'][model] = {'coll_records': {k: v for k, v in count.items() if k.startswith('COLL')}, 'rows': rows}
    s = json.dumps(out, indent=1)
    if a.out: a.out.write_text(s + '\n')
    for m, w in out['workloads'].items():
        for r in w['rows']: print(m, r['injlat'], r['added_cycles'], r['e2e_loss_pct'], {k: v['e2e_loss_pct'] for k, v in r['per_op'].items()})


if __name__ == '__main__':
    main()

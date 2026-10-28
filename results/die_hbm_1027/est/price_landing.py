#!/usr/bin/env python3
"""DIE-HBM-2 12.14b: price count-aligned landing latency per region map on the HBM ds_ar / qwen_ar S2 schedule.

Model = the TOK-HBM price chain (b1_lane_traversal ledger -> op_deltas -> accepted_cost.hbm_schedule, as combine.py),
applied as a MARGINAL delta on one plan: lane total += sum over the lane's crossing ports of the added landing cycles.
  mode 'k1'   : every crossing adds its physical latency ceil(lat + d/T) = K+1 (write -> read incl. RDREG), on top of
                the lane's existing boundary/face/station cycles (conservative: nothing is credited back).
  mode 'k1m1' : the crossing replaces one existing boundary hop (adds phys - 1).
Absolute tok/s = CLK / (planU3f upper cycles + delta) (planU3f upper 1905.97 tok/s = the OWNER-accepted 1906 floor).
usage: price_landing.py SRC_ROOT PLAN_DIR OUT.json TAG=crossings.tsv [TAG=crossings.tsv ...]
"""
import copy, csv, json, sys
from pathlib import Path
ROOT, PDIR, OUT = sys.argv[1:4]
sys.path[:0] = [ROOT + '/tools', ROOT + '/tools/die_plan', ROOT + '/tools/throughput', ROOT + '/src', ROOT + '/tools/hbm_b2']
import importlib.util
spec = importlib.util.spec_from_file_location('T', ROOT + '/tools/hbm_b2/b1_lane_traversal.py')
T = importlib.util.module_from_spec(spec); sa = sys.argv; sys.argv = ['x']; spec.loader.exec_module(T); sys.argv = sa
import accepted_cost as A
CLK = 1.2e9
U3F = {'ds_ar': CLK / 1905.97}
FAILPH = 8   # crossing failing even at DEPTH 8: priced as a D8 slot + 1 hop (lower bound of a hop chain)
def ph(r): return FAILPH if r['phys_cycles'] in ('-', '') else int(r['phys_cycles'])
led = T.ledger(PDIR)
plan = json.load(open(Path(PDIR) / 'die_plan.json'))
port_lane = {p: ln['id'] for ln in plan['lanes'] for p in ln['ports']}
sched = {}
for wl, name in A.DESIGNS['r25gq']['workloads'].items():
    run, count = A.hbm_schedule(name); sched[wl] = (run, count, run())
res = dict(plan=str(Path(PDIR) / 'die_plan.json'), plan_sha256=led['plan_sha256'], u3f_upper_cycles=U3F, maps={})
for arg in sys.argv[4:]:
    tag, tsv = arg.split('=', 1)
    rows = list(csv.DictReader(open(tsv), delimiter='\t'))
    for mode, sub in (('k1', 0), ('k1m1', 1)):
        add, miss = {}, []
        for r in rows:
            lid = port_lane.get(r['id'])
            if lid is None: miss.append(r['id']); continue
            add[lid] = add.get(lid, 0) + max(0, ph(r) - sub)
        led2 = copy.deepcopy(led)
        for lid, a in add.items():
            led2['lanes'][lid]['total'] += a
        ops, _ = T.op_deltas(led, led2)
        byop = {o['op']: o for o in ops}
        bit_cyc = sum(int(r['width']) * max(0, ph(r) - sub) for r in rows)
        out = dict(crossings=len(rows), unmapped=miss, lanes_touched=len(add), bit_cycles=bit_cyc,
                   op_delta={o['op']: o['delta_cycles'] for o in ops if o['delta_cycles']}, workloads={})
        for wl, (run, count, b) in sched.items():
            first = {}
            for k in count:
                for op in byop:
                    if A.op_match(k, op): first[k] = op; break
            w = dict(base_cycles=round(b, 1))
            for m, f in (('lower', lambda o: o['delta_cycles'] if not o['parallel'] else 0),
                         ('upper', lambda o: o['delta_cycles'])):
                ex = tuple((k, None, float(f(byop[op]))) for k, op in sorted(first.items()) if f(byop[op]))
                n = run(extra=ex); d = n - b
                e = dict(added_cycles=round(d, 1), loss_pct_vs_base=round(A.loss_pct(b, n), 3))
                if wl in U3F:
                    e['tok_s_on_u3f'] = round(CLK / (U3F[wl] + d), 2)
                w[m] = e
            out['workloads'][wl] = w
        res['maps'][f'{tag}/{mode}'] = out
        print(tag, mode, json.dumps({wl: {m: v[m] for m in ('lower', 'upper')} for wl, v in out['workloads'].items()}))
json.dump(res, open(OUT, 'w'), indent=1)

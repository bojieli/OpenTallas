"""PATH-HBM-R13 price decomposition: marginal ds_ar loss of each op's extra cycles (lane part / cc part) alone,
lower mode (R12 combine.py semantics), r25gq basis."""
import json, sys
W, lane, ccj = sys.argv[1:4]
sys.path.insert(0, W + '/tools/throughput'); sys.path.insert(0, W + '/tools')
import accepted_cost as A
L = json.load(open(lane)); C = json.load(open(ccj))['ops']
rows = {r['op']: r for r in L['op_deltas']}
out = {}
for wl, name in A.DESIGNS['r25gq']['workloads'].items():
    run, count = A.hbm_schedule(name); b = run()
    first = {}
    for k in count:
        for op, r in rows.items():
            if A.op_match(k, op): first[k] = op; break
    def loss(f):
        ex = tuple((k, None, float(f(op))) for k, op in sorted(first.items()) if f(op))
        return round(A.loss_pct(b, run(extra=ex)), 3)
    lo = lambda op: 0 if rows[op]['parallel'] else rows[op]['delta_cycles'] + C[op]['lower']
    w = dict(total_lower=loss(lo), ops={})
    for o in rows:
        ln = lambda op, o=o: (rows[op]['delta_cycles'] if op == o and not rows[op]['parallel'] else 0)
        cc = lambda op, o=o: (C[op]['lower'] if op == o and not rows[op]['parallel'] else 0)
        w['ops'][o] = dict(lane_cyc=rows[o]['delta_cycles'], cc_cyc=C[o]['lower'], parallel=rows[o]['parallel'],
                           n_kernels=sum(1 for k, op in first.items() if op == o),
                           lane_loss=loss(ln), cc_loss=loss(cc), both=loss(lambda op, o=o: lo(op) if op == o else 0))
    # each changed-lane leg on COLL/DMA ops
    out[wl] = w
print(json.dumps(out, indent=1))

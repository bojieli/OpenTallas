#!/usr/bin/env python3
"""combine lane deltas (b1_lane_traversal price json) + cc deltas (cc_price.json) -> S2 schedule tok/s (r25gq basis)."""
import json, sys
W, lane, ccj, out = sys.argv[1:5]
sys.path.insert(0, W + '/tools/throughput'); sys.path.insert(0, W + '/tools')
import accepted_cost as A
L = json.load(open(lane)); C = json.load(open(ccj))['ops']
rows = {r['op']: r for r in L['op_deltas']}
CLK = 1.2e9; res = {}
modes = {'lower': lambda r, c: (r['delta_cycles'] + c['lower']) if not r['parallel'] else 0,
         'mid_sm_serial': lambda r, c: r['delta_cycles'] + c['lower'],
         'upper': lambda r, c: r['delta_cycles'] + c['upper'],
         'cc_only_lower': lambda r, c: c['lower'] if not r['parallel'] else 0,
         'cc_only_upper': lambda r, c: c['upper']}
for wl, name in A.DESIGNS['r25gq']['workloads'].items():
    run, count = A.hbm_schedule(name); b = run()
    first = {}
    for k in count:
        for op, r in rows.items():
            if A.op_match(k, op): first[k] = op; break
    w = dict(base_cycles=round(b, 1), base_tok_s=round(CLK / b, 2))
    for m, f in modes.items():
        ex = tuple((k, None, float(f(rows[op], C[op]))) for k, op in sorted(first.items()) if f(rows[op], C[op]))
        n = run(extra=ex)
        w[m] = dict(cycles=round(n, 1), added=round(n - b, 1), tok_s=round(CLK / n, 2), loss_pct=round(A.loss_pct(b, n), 3))
    res[wl] = w
json.dump(res, open(out, 'w'), indent=1); print(json.dumps(res, indent=1))

#!/usr/bin/env python3
"""Co-located IR: per load instance VDD drop (0.7 - V) + VSS bounce (V), worst instance; + inherited below-M7 6.05 mV (Codex kv_c39_w13 basis)."""
import csv, json, sys, collections
d = sys.argv[1]
V = {r["Instance"]: (float(r["X location"]), float(r["Y location"]), 0.7 - float(r["Voltage"])) for r in csv.DictReader(open(d + "/psm/ir_VDD.csv"))}
S = {r["Instance"]: float(r["Voltage"]) for r in csv.DictReader(open(d + "/psm/ir_VSS.csv"))}
assert set(V) == set(S), "load sets differ"
L = sorted(((V[k][2] + S[k], V[k][2], S[k], k, V[k][0], V[k][1]) for k in V), reverse=True)
s, vd, vs, k, x, y = L[0]
row = collections.defaultdict(float)
for a, _, _, kk, _, _ in L:
    j = int(kk.split("_")[2]); row[j] = max(row[j], a)
m = json.load(open(d + "/irwin.json"))
out = dict(kit=d, grid=m["grid"], window_um=m["window_um"], power_w=m["power_w"], bumps=m["bumps"], matched_loads=len(V),
           co_located_worst=dict(instance=k, vdd_drop_mv=round(vd * 1e3, 3), vss_bounce_mv=round(vs * 1e3, 3), sum_mv=round(s * 1e3, 3), local_xy_um=[x, y]),
           above_m7_mv=round(s * 1e3, 3), below_m7_mv=6.05, total_mv=round(s * 1e3 + 6.05, 3), budget_mv=35.0,
           verdict="PASS" if s * 1e3 + 6.05 <= 35.0 else "FAIL",
           worst_by_row_mv={j: round(row[j] * 1e3, 2) for j in sorted(row)[:6]},
           vdd_separate_worst_mv=round(max(v[2] for v in V.values()) * 1e3, 3), vss_separate_worst_mv=round(max(S.values()) * 1e3, 3),
           review="UNCHECKED: own evaluator; NUMBER-CHECK required")
json.dump(out, open(d + "/result_d5.json", "w"), indent=1); print(json.dumps({k: out[k] for k in ("verdict", "total_mv", "above_m7_mv", "co_located_worst", "worst_by_row_mv")}))

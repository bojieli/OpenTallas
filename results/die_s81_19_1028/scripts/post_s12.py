#!/usr/bin/env python3
"""DIE-S81-19 plan_s12 post-compose deltas (exact, listed):
 (a) dead_inputs proof paths -> results/token_pass/s81_dead_inputs_2148/proof_closing_1028.json (TOK-S81-1 re-proof, 36/36
     declarations identical; same edit as its plan_s11b);
 (b) TOK-S81-2 / COORD 22:45: the 30 abutted svc ring hops (dn/up/pr/sg/ss) carry 3 as-built in-instance stages but the plan
     lane prices 2 -> every lane of those links gets fixed_cycles += (as-built stages - current plan cycles) so the plan
     matches the as-built (bind lands fixed_cycles as face pad stages; no other lane changes).
usage: post_s12.py PLAN_IN SVC_JSON OUT"""
import json, sys
sys.path.insert(0, "tools/die_plan")
import schema as S
pin, svcj, out = sys.argv[1:4]
raw = json.load(open(pin))
OLD = "results/token_pass/s81_dead_inputs_2148/proof_closing.json"
NEW = "results/token_pass/s81_dead_inputs_2148/proof_closing_1028.json"
n = 0
for t in raw["partition_types"].values():
    for d in t.get("dead_inputs", []):
        if d.get("proof") == OLD:
            d["proof"] = NEW; n += 1
P = S.Plan(raw)
svc = json.load(open(svcj))
L = {l["id"]: l for l in raw["lanes"]}
changed = {}
for link, v in svc.items():
    need = max(v["asbuilt_stages"])
    for lid in v["lanes"]:
        cur = P.lane_latency(lid)["cycles"]
        if cur < need:
            L[lid]["fixed_cycles"] = int(L[lid].get("fixed_cycles", 0)) + (need - cur)
            changed[lid] = dict(link=link, before=cur, after=need, fixed_cycles=L[lid]["fixed_cycles"])
raw["note"] += (f"; DIE-S81-19 post: {n} dead_inputs proofs -> proof_closing_1028.json; {len(changed)} svc ring lanes of the 30 abutted "
                f"dn/up/pr/sg/ss hops set to the as-built 3 stages via fixed_cycles (TOK-S81-2/COORD 22:45)")
json.dump(raw, open(out, "w"), indent=1)
P2 = S.Plan(raw)
bad = {lid: P2.lane_latency(lid)["cycles"] for lid in changed if P2.lane_latency(lid)["cycles"] != changed[lid]["after"]}
print(json.dumps(dict(proofs_repointed=n, svc_lanes_changed=len(changed), mismatch=bad, sample=dict(list(changed.items())[:3]))))
json.dump(changed, open(out + ".svc_lanes.json", "w"), indent=1)

"""DIE-S81-87: copy ONLY the collector_tree relay xy of the types path_respace re-sited (svc_lo__t7, svc_lo_rs_w__t1) from ready8 into IN. IN OUT REPORT."""
import json, sys
inp, out, rep = sys.argv[1:4]
SRC = "/srv/opentallas-scratch2/claude/die-s81-85/compose1111/out/s87_ready8/plan.json"
P = json.load(open(inp)); S = json.load(open(SRC))["partition_types"]
done = {}
for t in ("svc_lo_dsdv_svc_rs__t7", "svc_lo_dsdv_svc_rs_w__t1"):
    a = P["partition_types"][t]["clock"]["landing_contract"]["collector_tree"]["relays"]
    b = S[t]["clock"]["landing_contract"]["collector_tree"]["relays"]
    assert len(a) == len(b) and all(x.get("id") == y.get("id") for x, y in zip(a, b)), t
    n = 0
    for x, y in zip(a, b):
        if x["xy"] != y["xy"]: x["xy"] = y["xy"]; n += 1
    done[t] = n
json.dump(P, open(out, "w"), indent=1); json.dump(done, open(rep, "w"))
print(done)

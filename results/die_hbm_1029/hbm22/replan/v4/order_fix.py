#!/usr/bin/env python3
"""DIE-HBM-22: fix-up of bit order on re-routed hops: where src/dst die-frame orders of a port differ, flip the order of
the side declared on a NON-shared type (a declaration this event wrote; shared NW/NE types keep the NW declaration)."""
import sys, json
from collections import Counter
sys.path.insert(0, sys.argv[1])
import schema as S
plan = sys.argv[2]
raw = json.load(open(plan))
cnt = Counter(p["type"] for p in raw["partitions"])
P = S.Plan(raw)
nfix, bad = 0, []
FL = {"lsb_low": "lsb_high", "lsb_high": "lsb_low"}
for pid, pr in P.ports.items():
    if pr["src"]["part"] == S.DIE_PART or pr["dst"]["part"] == S.DIE_PART:
        continue
    gs, gd = P.port_geom_from(pr, "src"), P.port_geom_from(pr, "dst")
    if not gs or not gd:
        continue
    rp = next(x for x in raw["ports"] if x["id"] == pid)
    if "order" in rp and gs[3] == gd[3] and gs[3] != rp["order"]:
        rp["order"] = gs[3]; nfix += 1; continue
    if gs[3] == gd[3]:
        continue
    for side in ("dst", "src"):
        part, bus = pr[side]["part"], pr[side]["bus"]
        tn = P.parts[part]["type"]
        if cnt[tn] > 1 or ("order" in rp and (gs if side == "src" else gd)[3] == rp["order"]):
            continue
        t = raw["partition_types"][tn]
        done = False
        for b in t.get("buses", []):
            if b["name"] == bus:
                b["order"] = FL[b.get("order", "lsb_low")]; done = True
        for s_ in t.get("ft_slots", []):
            if bus == s_["name"] + "_i":
                s_["in_order"] = FL[s_.get("in_order", "lsb_low")]; done = True
            if bus == s_["name"] + "_o":
                s_["out_order"] = FL[s_.get("out_order", "lsb_low")]; done = True
        if done:
            nfix += 1
            break
    else:
        bad.append(pid)
json.dump(raw, open(plan, "w"), indent=1)
print("order fixes", nfix, "unfixable", bad)

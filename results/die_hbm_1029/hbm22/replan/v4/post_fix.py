#!/usr/bin/env python3
"""DIE-HBM-22 post-fix on the VB2 event output: (a) explicit-order kept ports into re-created boundary slots: slot side
order = the port's explicit order; (b) a NE mirror lane whose NW lane failed on a NW/NE-shared type is dropped too
(else the shared bus is unbound in the NW instance)."""
import sys, json
from collections import Counter
raw = json.load(open(sys.argv[1])); rep = json.load(open(sys.argv[2]))
T = raw["partition_types"]; pt = {p["name"]: p["type"] for p in raw["partitions"]}
cnt = Counter(pt.values())
n_a = 0
for p in raw["ports"]:
    if "order" not in p:
        continue
    for side, suf, key in (("dst", "_i", "in_order"), ("src", "_o", "out_order")):
        part, bus = p[side]["part"], p[side]["bus"]
        if part not in pt:
            continue
        for s_ in T[pt[part]].get("ft_slots", []):
            if bus == s_["name"] + suf and s_.get(key, "lsb_low") != p["order"] and cnt[pt[part]] == 1:
                s_[key] = p["order"]; n_a += 1
lanes = {l["id"]: l for l in raw["lanes"]}
failed = {x["id"] for x in rep["phase1"]["failed"] if "id" in x}
drop = {l + "m" for l in failed if l + "m" in lanes} | {l[:-1] for l in failed if l.endswith("m") and l[:-1] in lanes}
ports = {p["id"]: p for p in raw["ports"]}
used = Counter()
for p in raw["ports"]:
    for side in ("src", "dst"):
        used[(pt.get(p[side]["part"]), p[side]["bus"])] += 1
for lid in drop:
    for q in lanes[lid]["ports"]:
        p = ports[q]
        for side in ("src", "dst"):
            tn, bus = pt.get(p[side]["part"]), p[side]["bus"]
            used[(tn, bus)] -= 1
    raw["ports"] = [p for p in raw["ports"] if p["id"] not in set(lanes[lid]["ports"])]
for (tn, bus), c in used.items():
    if tn and c <= 0:
        T[tn]["buses"] = [b for b in T[tn].get("buses", []) if b["name"] != bus]
        if not any(used[(tn, s_["name"] + "_i")] > 0 or used[(tn, s_["name"] + "_o")] > 0
                   for s_ in T[tn].get("ft_slots", []) if s_["name"] == bus[:-2]):
            T[tn]["ft_slots"] = [s_ for s_ in T[tn].get("ft_slots", []) if s_["name"] != bus[:-2]]
raw["lanes"] = [l for l in raw["lanes"] if l["id"] not in drop]
for l in drop:
    raw["latency"]["lanes"].pop(l, None)
json.dump(raw, open(sys.argv[1], "w"), indent=1)
print("slot order fixes", n_a, "mirror lanes dropped", sorted(drop))

# DIE-KV-36 KV-021b: event28b plan (from DIE-KV-35 mk_plan28.py) = event27f + eA2 count-aligned landing cycles (clock.landing_network.count_aligned_cycles)
# and the latency table recomputed with the plan schema.Plan.lane_latency (no new rule). Reports every lane delta.
import json, sys, copy
sys.path.insert(0, "tools/die_plan")
import schema
src = "results/die_kv_29_1029/event27f/plan.json"
raw = json.load(open(src)); old = copy.deepcopy(raw)
B = json.load(open(sys.argv[1]))   # eA2 bind.json (count_align ports sched_lat)
net = raw["clock"]["landing_network"]; cac = net["count_aligned_cycles"]
chg = {}
for pid, c in B["ports"].items():
    if pid in cac and int(cac[pid]) != int(c["sched_lat"]):
        chg[pid] = (cac[pid], c["sched_lat"]); cac[pid] = int(c["sched_lat"])
missing = [p for p in B["ports"] if p not in cac]
P = schema.Plan(raw)
P0 = schema.Plan(old)
lat = raw["latency"]["lanes"]; dl = {}; ctl = []
for lid in lat:
    new = P.lane_latency(lid); o = P0.lane_latency(lid)
    if any(k in o and old["latency"]["lanes"][lid].get(k) != o[k] for k in ("cycles", "natural", "clock_landing")):
        ctl.append(lid)
    for k in ("cycles", "natural", "clock_landing"):
        if k in new and lat[lid].get(k) != new[k]:
            dl.setdefault(lid, {})[k] = (lat[lid].get(k), new[k]); lat[lid][k] = new[k]
raw["note"] = (raw.get("note", "") + " | DIE-KV-36 event28b: eA2 count-aligned K+1 on 122 ports (both-cal hull) + ECTL round trip equalised on all 32 frames (29 krq pads), latency table recomputed").strip(" |")
json.dump(raw, open("kv36/event28b/plan.json", "w"), indent=1)
json.dump(dict(ports_changed=chg, missing_in_plan=missing, lanes_changed=dl, control_lanes_not_reproduced=ctl),
          open("kv36/event28b/plan_delta.json", "w"), indent=1)
print("ports", len(chg), "missing", len(missing), "lanes", len(dl), "control_mismatch", len(ctl), ctl[:5],
      "sum dcycles", sum(v["cycles"][1] - v["cycles"][0] for v in dl.values() if "cycles" in v))

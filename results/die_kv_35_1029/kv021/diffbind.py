import json, sys
from collections import Counter
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
ex = set(json.load(open(sys.argv[3]))) if len(sys.argv) > 3 else None
dK = {}; dS = {}; tags = Counter()
for p, v in a["ports"].items():
    w = b["ports"][p]
    if v["K"] != w["K"] or v["sched_lat"] != w["sched_lat"] or v["depth"] != w["depth"]:
        dK[p] = (w["K"], v["K"], w["sched_lat"], v["sched_lat"], w["depth"], v["depth"])
        tags[(v["src_part"], v["dst_part"], v["K"] - w["K"], v["sched_lat"] - w["sched_lat"])] += 1
np = [x for x in a["parts"] if a["parts"][x].get("n_nominal") != b["parts"].get(x, {}).get("n_nominal")]
print("ports K/sched/depth changed:", len(dK))
print("by (src,dst,dK,dSched):")
for k, n in sorted(tags.items()): print("  ", k, n)
print("parts n_nominal changed:", len(np), [(x, b["parts"][x].get("n_nominal"), a["parts"][x].get("n_nominal")) for x in np[:40]])
ra = {k: v.get("n_nominal") for k, v in a["regions"].items()}; rb = {k: v.get("n_nominal") for k, v in b["regions"].items()}
rc = [k for k in ra if ra[k] != rb.get(k)]
print("regions n_nominal changed:", len(rc), "edge_fall changed:", sum(a["regions"][k].get("edge_fall") != b["regions"].get(k, {}).get("edge_fall") for k in a["regions"]))
print("sched total", sum(v["sched_lat"] for v in b["ports"].values()), "->", sum(v["sched_lat"] for v in a["ports"].values()))
if ex is not None:
    s = set(dK); print("expected86:", len(ex), "changed&expected", len(s & ex), "changed-not-expected", len(s - ex), "expected-not-changed", len(ex - s))
json.dump(dK, open(sys.argv[1] + ".diff.json", "w"), indent=0)

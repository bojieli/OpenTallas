"""lat_plan.json = regenerated composed-plan latency table (gen.py latency) + 3 x legacy-core landings per lane"""
import json, sys
P = json.load(open(sys.argv[1]))["latency"]["lanes"]
for core in ("land", "rebuild"):
    f = f"results/fallback_s81_2_1026/regions/class_g2_{core}/"
    L = json.load(open(f + "lat_face.json"))
    for k, v in L["lanes"].items():
        c = P[k]["cycles"] + 3 * v.get("fallback_core_landings", 0)
        v["natural"] += c - v["cycles"]; v["cycles"] = c
    L["fallback"]["ft"] = "plan-table (gen.py latency of the composed plan)"
    json.dump(L, open(f + "lat_plan.json", "w"), indent=1)

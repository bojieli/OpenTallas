#!/usr/bin/env python3
"""DIE-KV-39 V2 kit plan: plan_sd39c + the existing SD kit-plan forms already used by every sys_SD kit since DIE-KV-33/35
(no new form): count_straps sites_um + clock.die_islands_um from DIE-KV-33 die_plan_sd33s, clk_clk_phy edge clock from
DIE-KV-35 die_plan_sd35_delta (results/die_kv_35_1029/kv022).  Only kv3_sys_SD/_v1 change.
usage: kitplan_sd39.py PLAN_SD39C SD33S SD35_DELTA OUT"""
import json, sys
p, a, d = (json.load(open(x)) for x in sys.argv[1:4])
for tn in ("kv3_sys_SD", "kv3_sys_SD_v1"):
    t, s = p["partition_types"][tn], a["partition_types"][tn]
    assert [x["name"] for x in t["count_straps"]] == [x["name"] for x in s["count_straps"]], tn
    t["count_straps"] = s["count_straps"]
    t["clock"]["die_islands_um"] = s["clock"]["die_islands_um"]
    for op in d["patch"]:
        if op["path"] == f"/partition_types/{tn}/clock/edge_clocks/-" and op["value"]["port"] not in [e["port"] for e in t["clock"]["edge_clocks"]]:
            t["clock"]["edge_clocks"].append(op["value"])
json.dump(p, open(sys.argv[4], "w"), indent=1)
print("kit plan", sys.argv[4])

#!/usr/bin/env python3
"""DIE-HBM-66 d44v part 14: ot_hnx_fused_host_program clk pin to the signed-off location. mk_p14.py PLAN_DIR (plain die_plan.json, clock_entries.json)
Signed core whose clk pin alone differs from the plan (1/562): the kit was generated without --clock-pin-entry on, so the plan centre entry
went to the N face. The signed DB stays; the plan follows it. clk M5 (103.704, 64.8) -> (103.704, 129.36), N face. Parent tap and clock entry follow."""
import json, sys
from pathlib import Path
pd = Path(sys.argv[1])
Q = "cores/ot_hnx_fused_host_program__276.48x129.6__c25b__centry__p10"; NF = Q + "__p14.json"; MOD = "ot_hnx_fused_host_program"; NEW = (103.704, 129.36); DY = 129.36 - 64.8; H = 129.6
T = json.loads((pd / (Q + ".json")).read_text()); ck = [p for p in T if p["name"] == "clk"]
if len(T) != 562 or len(ck) != 1 or (ck[0]["x"], ck[0]["y"]) != (103.704, 64.8): raise SystemExit("fhp table not as read")
ck[0]["x"], ck[0]["y"] = NEW
(pd / NF).write_text(json.dumps(T))
D = json.loads((pd / "die_plan.json").read_text()); ty = D["partition_types"]["root"]
cs = [c for c in ty["hard_cores"] if c.get("module") == MOD]
if len(cs) != 1 or cs[0].get("pins_file") != Q + ".json": raise SystemExit("rows")
cs[0]["pins_file"] = NF
tp = [t for t in ty["clock"]["taps"] if t["name"].split(".")[0] == cs[0]["inst"]]
if len(tp) != 1: raise SystemExit(f"tap {tp}")
old = list(tp[0]["xy"]); tp[0]["xy"] = [old[0], round(old[1] + DY, 3)]; tp[0]["note"] = (tp[0].get("note") or "") + " | d44v part 14: at the signed N-face clk pin"
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
ce = json.loads((pd / "clock_entries.json").read_text()); ents = []
for part, es in ce.items():
    for k, e in es.items():
        if isinstance(e, dict) and e.get("module") == MOD:
            e["xy_um"] = [e["xy_um"][0], 129.36]; a = e["island_um"]; e["island_um"] = [a[0], round(H - (a[3] - a[1]), 3), a[2], H]
            e["source"] += " | d44v part 14: signed N-face clk pin"; ents.append(part + "/" + k)
if len(ents) != 1: raise SystemExit(f"clock entries {ents}")
(pd / "clock_entries.json").write_text(json.dumps(ce, indent=1) + "\n")
(pd / "part14_event.json").write_text(json.dumps({"schema": "opentallas.hbm_plan_event.part14", "core": MOD, "pins_file": NF, "rows": 1,
    "clk": {"from": [103.704, 64.8], "to": list(NEW), "layer": "M5"}, "tap": [old, tp[0]["xy"]], "clock_entries": ents, "cycles": 0}, indent=1) + "\n")
print("part 14", tp[0]["name"], old, tp[0]["xy"], ents)

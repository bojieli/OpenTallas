#!/usr/bin/env python3
"""DIE-HBM-66 d44v part 12: ot_hgi_qw_dec clk pin to the signed-off location. mk_p12.py PLAN_DIR (plain die_plan.json, clock_entries.json)
Class COORD 15:56: signed core whose clk pin alone differs from the plan (1/1670). The signed DB stays; the plan follows it. clk M5
(129.624, 86.4) -> (129.624, 0.24), S face. The two parent taps move with it, x kept on the same 4.32 lattice line; clock entry rows follow."""
import json, sys
from pathlib import Path
pd = Path(sys.argv[1])
Q = "cores/ot_hgi_qw_dec__260x173.6__c25c__codex_g21__centry"; NF = Q + "__p12.json"; MOD = "ot_hgi_qw_dec"; NEW = (129.624, 0.24); DY = 0.24 - 86.4
T = json.loads((pd / (Q + ".json")).read_text()); ck = [p for p in T if p["name"] == "clk"]
if len(T) != 1670 or len(ck) != 1 or (ck[0]["x"], ck[0]["y"]) != (129.624, 86.4): raise SystemExit("qw_dec table not as read")
ck[0]["x"], ck[0]["y"] = NEW
(pd / NF).write_text(json.dumps(T))
D = json.loads((pd / "die_plan.json").read_text()); rows = 0; taps = {}
ty = D["partition_types"]["q_hub_nw"]
for c in ty["hard_cores"]:
    if c.get("module") != MOD: continue
    if c.get("pins_file") != Q + ".json": raise SystemExit("pins_file " + c["inst"])
    c["pins_file"] = NF; rows += 1
    tap = [t for t in ty["clock"]["taps"] if t["name"] == c["inst"]]
    if len(tap) != 1: raise SystemExit("tap " + c["inst"])
    old = list(tap[0]["xy"]); tap[0]["xy"] = [old[0], round(old[1] + DY, 3)]; taps[c["inst"]] = [old, tap[0]["xy"]]
    tap[0]["note"] = (tap[0].get("note") or "") + " | d44v part 12: at the signed S-face clk pin"
if rows != 2: raise SystemExit(f"rows {rows} != 2")
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
ce = json.loads((pd / "clock_entries.json").read_text()); ents = []
for part, es in ce.items():
    for k, e in es.items():
        if isinstance(e, dict) and e.get("module") == MOD:
            e["xy_um"] = [e["xy_um"][0], 0.24]; a = e["island_um"]; e["island_um"] = [a[0], 0.0, a[2], round(a[3] - a[1], 3)]
            e["source"] += " | d44v part 12: signed S-face clk pin"; ents.append(part + "/" + k)
if len(ents) != 2: raise SystemExit(f"clock entries {ents}")
(pd / "clock_entries.json").write_text(json.dumps(ce, indent=1) + "\n")
(pd / "part12_event.json").write_text(json.dumps({"schema": "opentallas.hbm_plan_event.part12", "core": MOD, "pins_file": NF, "rows": rows,
    "clk": {"from": [129.624, 86.4], "to": list(NEW), "layer": "M5"}, "taps": taps, "clock_entries": ents, "cycles": 0}, indent=1) + "\n")
print("part 12", rows, "rows", taps, ents)

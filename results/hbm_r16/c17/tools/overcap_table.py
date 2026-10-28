#!/usr/bin/env python3
"""HBM-R16/C17: remaining pin6 over-capacity table from respread.py reports. usage: overcap_table.py before.json after.json"""
import json, sys
r0 = json.load(open(sys.argv[1])); r = json.load(open(sys.argv[2]))
print("# C17g pin6 face capacity (<= 5.5 pins/um over L-2*8.64) after (a) re-pin/orient + (b-i) re-spread. CHECKED: tools/respread.py on c17g")
print("# module | instances | face | pins | usable L um | pins/um | (ii) grow side by um (4.32 grid) | lot check (grown rect vs type outline + other cores, either growth direction)")
n = 0
for f, v in r.items():
    for F, x in v["faces"].items():
        n += 1
        lots = x["lots"]; ok = sum(1 for k, o in lots.items() if any(s == "ok" for d, s in o))
        bad = [k.split(".", 1)[1] + ": " + " / ".join(s[:40] for d, s in o) for k, o in lots.items() if not any(s == "ok" for d, s in o)]
        print(f"{v['module'][:62]} | {v['instances']} | {F} | {x['after_respread']} | {x['L']} | {x['dens_after']} | +{x['grow_um']} | lot ok {ok}/{len(lots)} {'; '.join(bad[:2])}")
print(f"# {len(r)} tables / {n} faces still over cap")
print()
print("# (b-i) re-spread APPLIED in c17g (whole groups moved to a face with cos > 0 for EVERY instance; destination <= cap):")
for f, v in r0.items():
    if v["moves"]:
        print(v["module"][:62], {F: (x["dens"], x["dens_after"]) for F, x in v["faces"].items()}, "groups", len(v["moves"]), "pins", sum(m["pins"] for m in v["moves"]))

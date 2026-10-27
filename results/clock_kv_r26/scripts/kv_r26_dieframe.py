#!/usr/bin/env python3
"""CLOCK-KV-R26 die-frame check: every kv3_head_eighth_e1/e5 instance (all partitions), r25 vs r26 die xy per pin.
   - non-moved pins: identical die xy (TR(A) instances included: fMX@MX -> canonical@R0)
   - moved clock pins: in the die-frame 8.64-um entry square around the core centre, y == core-centre row
   - e5 resets: on the core-centre row inside the entry square
   Also counts, per module, distinct core-frame pin sets (should be 1 = one GDS) and orients.
   kv_r26_dieframe.py PD hm_r25.json hm_r26.json OUT.json"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
import schema
from die_clock_mesh import core_frame

pd = Path(sys.argv[1])
P5 = schema.Plan(schema.load(pd / sys.argv[2]))
P6 = schema.Plan(schema.load(pd / sys.argv[3]))


def pins(pf):
    return {p["name"]: p for p in json.loads((pd / pf).read_text())["pins"]}


MODS = ("kv3_head_eighth_e1", "kv3_head_eighth_e5")
rep = dict(instances=Counter(), pins_checked=0, bad=[], views=Counter(), moved_ok=0, entry_bad=[])
for pn, part in P6.parts.items():
    t6, t5 = P6.ptype(pn), P5.ptype(pn)
    c5 = {c["inst"]: c for c in t5.get("hard_cores", []) or []}
    for c in t6.get("hard_cores", []) or []:
        if c["module"] not in MODS:
            continue
        o = c5[c["inst"]]
        rep["instances"][c["module"]] += 1
        rep["views"][f"{c['module']}|{c['pins_file']}|{c['orient']}|part {part.get('orient','R0')}"] += 1
        a, b = pins(o["pins_file"]), pins(c["pins_file"])
        cx, cy = core_frame(P6, pn, c, (108.0, 108.0), inverse=True)
        for n, q in b.items():
            d6 = core_frame(P6, pn, c, (q["x"], q["y"]), inverse=True)
            p = a[n]
            d5 = core_frame(P5, pn, o, (p["x"], p["y"]), inverse=True)
            rep["pins_checked"] += 1
            moved = (p["x"], p["y"]) != (q["x"], q["y"]) if o["pins_file"].replace("_fMX", "") == o["pins_file"] else None
            if abs(q["y"] - 108.0) < 1e-6 and q["layer"] == "M5" and ("clk" in n or "rst_n" in n):
                # entry pin: die xy within the entry square on the core-centre line
                if not (abs(d6[0] - cx) <= 4.32 and abs(d6[1] - cy) <= 4.32 and (abs(d6[1] - cy) < 1e-4 or abs(d6[0] - cx) < 4.32)):
                    rep["entry_bad"].append((pn, c["inst"], n, d6, (cx, cy)))
                if abs(d6[1] - cy) > 1e-4:
                    rep["entry_bad"].append((pn, c["inst"], n, "not on centre row", d6, (cx, cy)))
                if (round(d5[0], 4), round(d5[1], 4)) != (round(d6[0], 4), round(d6[1], 4)):
                    rep["moved_ok"] += 1
                continue
            if (round(d5[0], 4), round(d5[1], 4), p["layer"]) != (round(d6[0], 4), round(d6[1], 4), q["layer"]):
                rep["bad"].append((pn, c["inst"], n, d5, d6))
rep["instances"] = dict(rep["instances"])
rep["views"] = dict(rep["views"])
rep["n_bad"], rep["n_entry_bad"] = len(rep["bad"]), len(rep["entry_bad"])
rep["bad"], rep["entry_bad"] = rep["bad"][:20], rep["entry_bad"][:20]
Path(sys.argv[4]).write_text(json.dumps(rep, indent=1, default=str) + "\n")
print(json.dumps({k: rep[k] for k in ("instances", "pins_checked", "n_bad", "n_entry_bad", "moved_ok")}))
for k, v in sorted(rep["views"].items()):
    print(v, k)
for x in rep["bad"][:5] + rep["entry_bad"][:5]:
    print("BAD", x)

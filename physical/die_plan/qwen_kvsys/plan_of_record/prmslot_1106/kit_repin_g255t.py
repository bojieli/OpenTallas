#!/usr/bin/env python3
"""KV-PRMSLOT-1 11-06: re-pin a qkd_hr_core_prompt 254.88 kit (KV-PRM-B4 vB form) to the on-track plan table g255t.

The vB grow_outline.py snap (k*0.048) puts 4745 of 5124 pins between the kit's own M4/M5/M7 tracks
(make_tracks offset = pitch/2), which also fails the plan G0C track rule. This keeps the kit's face coordinate
(edge form) and takes the along-face coordinate (and both coordinates for interior pins) from the plan table.
Rewrites KIT/pins.json and the place_pin -location values in KIT/io.tcl. Pin names, layers, faces and order are unchanged.
usage: kit_repin_g255t.py KIT PLAN_PINS_JSON
"""
import json
import re
import sys
from pathlib import Path

K, P = Path(sys.argv[1]), Path(sys.argv[2])
plan = {p["name"]: p for p in json.loads(P.read_text())["pins"]}
pj = json.loads((K / "pins.json").read_text())
loc = {}
for r in pj:
    q = plan[f'{r["bus"]}[{r["bit"]}]']
    assert q["layer"] == r["layer"], (r, q)
    if r["face"] in ("N", "S"):
        r["x"] = q["x"]
    elif r["face"] in ("E", "W"):
        r["y"] = q["y"]
    else:
        r["x"], r["y"] = q["x"], q["y"]
    loc[f'{r["bus"]}[{r["bit"]}]'] = (r["face"], r["x"], r["y"])
(K / "pins.json").write_text(json.dumps(pj, indent=1))
io = K / "io.tcl"
n = 0


def rep(mo):
    global n
    face, x, y = loc[mo.group(1)]
    ox, oy = (float(v) for v in mo.group(2)[1:-1].split())
    if face in ("N", "S"):
        y = oy          # io.tcl keeps its own pin-centre face coordinate
    elif face in ("E", "W"):
        x = ox
    n += 1
    return mo.group(0)[: mo.start(2) - mo.start(0)] + "{%.4f %.4f}" % (x, y)


t = re.sub(r"place_pin -pin_name \{([^}]+)\}.*?-location (\{[0-9.]+ [0-9.]+\})", rep, io.read_text())
io.write_text(t)
print("pins.json", len(pj), "io.tcl place_pin", n)

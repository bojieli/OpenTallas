#!/usr/bin/env python3
"""HEAD-96 rp18 item 3: move the ot_s81hd_lep_pair rst_n core pin from the core centre to the S (K) face.

    python3 -I lep_rst_edge.py IN_PLAN OUT_PLAN

Why: the centre rst_n (388.824, 246.24) is 250.56 um from the nearest legal relay site (push-off out of a 777.6 x 492.48
core); one relay stage cannot drive that wire (RESET-SLEW 16:19: L_safe 130 um) and no partition cell can sit over
the core.  Rule (fixed, no hand placement): rst_n goes on the S face, same layer (M5) and same centre-form inset as
the K-side M5 pins, on the first M5 plan track at least EDGE_UM east of the K-side band (S-face pins end x 395.424),
i.e. as close as possible to the old centre x.  Every instance's die relay then sits just outside its own S face
(R0) / N face (MX, R180) in the central shelf channel.  Writes PLANDIR/core_pins/lep_pair_pins_777r.json and points
the 4 hd_lep0N pairs at it.  The core view (results/head_lep_pair_views_vE_1106) is re-pinned by a core rebuild.
"""
import copy, json, math, sys
from pathlib import Path

SRC, DST = "core_pins/lep_pair_pins_777.json", "core_pins/lep_pair_pins_777r.json"
EDGE_UM, M5_PITCH, M5_OFF = 2.0, 0.048, 0.024
inp, outp = Path(sys.argv[1]), Path(sys.argv[2])
pd = inp.resolve().parent
plan = json.loads(inp.read_text())
doc = json.loads((pd / SRC).read_text())
w, h = doc["outline_um"]
s_pins = [q for q in doc["pins"] if q["name"] != "rst_n" and q["y"] < 0.5]
inset = sorted({q["y"] for q in s_pins})
assert inset == [0.042], inset
band_hi = max(q["x"] for q in s_pins)
x = M5_OFF + math.ceil((band_hi + EDGE_UM - M5_OFF) / M5_PITCH) * M5_PITCH
x = round(x, 6)
new = copy.deepcopy(doc)
rst = [q for q in new["pins"] if q["name"] == "rst_n"]
assert len(rst) == 1, rst
old = dict(rst[0])
rst[0].update(layer="M5", x=x, y=inset[0])
new["source"] = doc["source"] + f"; HEAD-96 rp18: rst_n centre ({old['x']}, {old['y']}) -> S face ({x}, {inset[0]}) M5"
new["faces"] = dict(doc["faces"], S=doc["faces"]["S"] + f"; rst_n M5 x {x}")
(pd / DST).write_text(json.dumps(new, indent=1) + "\n")
n = 0
for hc in plan["partition_types"]["hd_lep0N"]["hard_cores"]:
    if hc.get("module") == "ot_s81hd_lep_pair":
        assert hc["pins_file"] == SRC, hc["pins_file"]
        hc["pins_file"] = DST
        n += 1
assert n == 4, n
outp.write_text(json.dumps(plan, indent=1) + "\n")
print(json.dumps(dict(old=[old["x"], old["y"]], new=[x, inset[0]], band_hi=band_hi, pairs=n, pins_file=DST)))

#!/usr/bin/env python3
"""QK-CORES-5 (COORD ruling 10-27 15:4x, pins_canonical edge-vs-centre): ONE canonical pin form = the pin CENTRE as the
kit io.tcl places it.  The kit generators place every face pin with a 0.192 um deep shape flush with the outline, so
the centre sits 0.096 um inside the face.  Plan pin files that carry another face depth (closed-LEF access points,
e.g. pv_join_t M3 S/N pins at y 0.072 = 0.144 um shapes) are rewritten to that centre form; interior pins (12.8a
entry islands) and pins already in centre form are untouched.  Same physical edge, no pin moves along the face.
    pins_centre_form.py IN.json OUT.json W H      -> prints per-face counts of moved pins"""
import json, sys
from collections import Counter
INSET = 0.096          # half of the generator's 0.192 um face pin depth
NEAR = 0.2             # a pin closer than this to a face is a face pin
src, dst, W, H = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
doc = json.load(open(src))
rows = doc["pins"] if isinstance(doc, dict) else doc
moved = Counter()
for p in rows:
    x, y = p["x"], p["y"]
    d = {"W": x, "E": W - x, "S": y, "N": H - y}
    f = min(d, key=d.get)
    if d[f] > NEAR or abs(d[f] - INSET) < 1e-6:
        continue
    if f == "W": p["x"] = INSET
    elif f == "E": p["x"] = round(W - INSET, 6)
    elif f == "S": p["y"] = INSET
    else: p["y"] = round(H - INSET, 6)
    moved[f] += 1
if isinstance(doc, dict):
    doc["source"] = (doc.get("source", "") + " | QK-CORES-5 10-27: face pins in io.tcl centre form (0.096 um inset, "
                     "COORD one-canonical-form ruling)")
json.dump(doc, open(dst, "w"), indent=1)
print(json.dumps({"in": src, "out": dst, "moved": dict(moved), "pins": len(rows)}))

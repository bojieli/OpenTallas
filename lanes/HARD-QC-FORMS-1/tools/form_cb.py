#!/usr/bin/env python3
"""HARD-QC-FORMS-1 candidate form F-CB (cbn_q00 family; plan-check only, not built): column-0 tiles 17.28 um east (8.64 lattice)
(W strip 86.4 -> 103.68 for u_t00's 2,056 pins + 1,545 transit bits; centre street 147.4 -> 130.1), top-row tiles 51.84 um
south and the N landing rings 17.28 um south (ring 30.24 um behind the N face, 38.9 um between ring and tile).
usage: form_cb.py PLAN FORM_OUT.json"""
import json, sys
P = json.load(open(sys.argv[1])); pt = P["partition_types"]; ops = []
for t in sorted(pt):
    if not t.startswith("cbn_q00"): continue
    T = pt[t]; assert T["outline_um"] == [1235.52, 2566.08], (t, T["outline_um"])
    for h in T["hard_cores"]:
        x, y = h["origin_um"]; nx, ny = x, y
        if h["inst"] in ("u_t00", "u_t01"): nx = round(x + 17.28, 6)
        if h["inst"] in ("u_t01", "u_t11"): ny = round(y - 51.84, 6)
        if h["inst"].startswith("cl_") and y > 2000: ny = round(y - 17.28, 6)
        if (nx, ny) != (x, y): ops.append({"op": "move_core", "type": t, "inst": h["inst"], "from": [x, y], "to": [nx, ny]})
    for f in T.get("ft_slots", []):
        if f["name"] == "rsf" and f.get("regs_um") and any(h["inst"] == "cl_rsf_i" for h in T["hard_cores"]):
            # the rsf chain column stood 8.64 um east of column 0; it keeps that distance (x 552.96 -> 570.24), south of the ring
            ops.append({"op": "shift_ft", "type": t, "slot": "rsf", "box": [548.0, 0.0, 560.0, 2480.0], "d": [17.28, 0.0], "from_regs": f["regs_um"]})
ops.sort(key=lambda o: (o["type"], o["op"] != "shift_ft"))   # station shift first: the ring core move carries its own station
json.dump({"name": "F-CB cbn_q00 strips (HARD-QC-FORMS-1 11-13, candidate)", "ops": ops}, open(sys.argv[2], "w"), indent=1); print("ops", len(ops))

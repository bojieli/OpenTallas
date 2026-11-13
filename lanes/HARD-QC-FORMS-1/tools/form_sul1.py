#!/usr/bin/env python3
"""HARD-QC-FORMS-1 form F-SUL1W (slw_su_l1 x2): the four lane cores re-pitched to 43.2 um streets with u_lane4 129.6 um
off the S face (the closed S wall becomes three two-ended ring walls), E rings 25.92 um west (43.2 um behind the E pins),
N ring cl_cws0_i 30.24 um south.  usage: form_sul1.py PLAN FORM_OUT.json"""
import json, sys
P = json.load(open(sys.argv[1])); pt = P["partition_types"]; ops = []
TO = {"u_lane4": (None, 129.6), "u_lane5": (None, 440.64), "u_lane6": (None, 751.68), "u_lane7": (None, 1062.72),
      "cl_x_su_c_i": (-25.92, None), "cl_x_su_c_p1_i": (-25.92, None), "cl_cws0_i": (None, -30.24)}
for t in sorted(pt):
    if not t.startswith("slw_su_l1"): continue
    for h in pt[t]["hard_cores"]:
        if h["inst"] not in TO: continue
        x, y = h["origin_um"]; a, b = TO[h["inst"]]
        if h["inst"].startswith("u_lane"): to = [x, b]
        else: to = [round(x + (a or 0), 6), round(y + (b or 0), 6)]
        ops.append({"op": "move_core", "type": t, "inst": h["inst"], "from": [x, y], "to": to})
    # order: top lane first when moving down, bottom lane last when moving up, so no transient overlap matters (the check is final-state)
json.dump({"name": "F-SUL1W slw_su_l1 lane re-pitch (HARD-QC-FORMS-1 11-13)", "ops": ops}, open(sys.argv[2], "w"), indent=1); print("ops", len(ops))

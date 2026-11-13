#!/usr/bin/env python3
"""QC-FORMS-2 form F-SUC2 (on top of F-SUC, su_c x3): u_va and u_vb +17.28 um east, so u_va stands 43.2 um behind the
W pin face (slw: 735 pins of x_su_l1_o in its span) and the u_va|u_vb gap stays 25.92.  u_va physical_ft pins are the
tied ft_ck/ft_rst pushdown pins (unconsumed), not the cws1 data ft, so the move needs no seam change.
usage: form_suc2.py PLAN FORM_OUT.json"""
import json, sys
P = json.load(open(sys.argv[1])); pt = P["partition_types"]; ops = []
for t in sorted(pt):
    if "su_c" not in t.split("__")[0]: continue
    for h in pt[t]["hard_cores"]:
        if h["inst"] in ("u_suvm_u_vm8q_u_va", "u_suvm_u_vm8q_u_vb"):
            x, y = h["origin_um"]; ops.append({"op": "move_core", "type": t, "inst": h["inst"], "from": [x, y], "to": [round(x + 17.28, 6), y]})
json.dump({"name": "F-SUC2 su_c u_va/u_vb +17.28 (QC-FORMS-2 11-13)", "ops": ops}, open(sys.argv[2], "w"), indent=1); print("ops", len(ops))

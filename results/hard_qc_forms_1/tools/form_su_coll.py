#!/usr/bin/env python3
"""HARD-QC-FORMS-1 forms F-SUC (su_c x3: middle core row +25.92 um east so u_pg stands 43.2 um behind the W pin face;
u_cl 8.64 um west for a 43.2 um E street) and F-COLLCORE (face_1 codec bank[0] SRAM from 17.28 to 60.48 um behind the
1,959-pin W face, in line with the other bank columns).  usage: form_su_coll.py PLAN FORM_OUT.json"""
import json, sys
P = json.load(open(sys.argv[1])); pt = P["partition_types"]; ops = []
DX = {"u_suvm_u_vm8q_u_pg": 25.92, "u_suvm_u_su8": 25.92, "u_suvm_u_vm8q_u_ch": 25.92, "u_suvm_u_vm8q_u_bt": 25.92, "u_suvm_u_vm8q_u_cl": -8.64}
for t in sorted(pt):
    if "su_c" in t.split("__")[0]:
        for h in pt[t]["hard_cores"]:
            if h["inst"] in DX:
                ops.append({"op": "move_core", "type": t, "inst": h["inst"], "from": h["origin_um"], "to": [round(h["origin_um"][0] + DX[h["inst"]], 6), h["origin_um"][1]]})
for h in pt["coll_core"]["hard_cores"]:
    if h["inst"].endswith("g_face_1_u_face.g_codec.u_codec.g_bank[0].u_store.u_sram"):
        ops.append({"op": "move_core", "type": "coll_core", "inst": h["inst"], "from": h["origin_um"], "to": [60.48, h["origin_um"][1]], "rigid": False})
json.dump({"name": "F-SUC + F-COLLCORE (HARD-QC-FORMS-1 11-13)", "ops": ops}, open(sys.argv[2], "w"), indent=1); print("ops", len(ops))

#!/usr/bin/env python3
"""HARD-QC-FORMS-1 family form F-STM (11 QC stm types): the 4 tload ROMs as one 2 x 2 block (two stacked pairs,
N/S faces abutted, a 46.6 um street between the columns for the W/E pin faces), 166 um below the N face, under the
b_tw_data_ctl_o window; plus verilog define OT_QC_TLOADCAP (ROM capture stage, RTL branch).  usage: form_stm.py PLAN FORM_OUT.json"""
import json, sys
P = json.load(open(sys.argv[1])); pt = P["partition_types"]
SITE = {"m0": [77.76, 1537.92], "m1": [77.76, 1602.72], "m2": [246.24, 1537.92], "m3": [246.24, 1602.72]}
ops = []
for t in sorted(pt):
    T = pt[t]
    if "_stm_" not in t: continue
    assert T["outline_um"] == [613.44, 1831.68], t
    for h in T["hard_cores"]:
        k = h["inst"].rsplit(".", 1)[-1]; assert h["module"] == "ot_rom_4096x266_m8" and k in SITE, h["inst"]
        ops.append({"op": "move_core", "type": t, "inst": h["inst"], "from": h["origin_um"], "to": SITE[k], "from_orient": h["orient"], "to_orient": h["orient"], "rigid": False})
    ops.append({"op": "add_define", "type": t, "define": "OT_QC_TLOADCAP"})
json.dump({"name": "F-STM rom block + tload capture stage (HARD-QC-FORMS-1 11-13)", "ops": ops}, open(sys.argv[2], "w"), indent=1)
print("ops", len(ops))

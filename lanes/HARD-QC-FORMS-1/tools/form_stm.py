#!/usr/bin/env python3
"""HARD-QC-FORMS-1 family form F-STM (11 QC stm types): the 4 tload ROMs as one 2 x 2 block on the 8.64 um lattice
(50.9 um street between the columns for the W/E pin faces, 49.4 um between the rows), 170 um below the N face, under the
b_tw_data_ctl_o window; plus verilog define OT_QC_TLOADCAP (ROM capture stage, RTL branch).  usage: form_stm.py PLAN FORM_OUT.json"""
import json, sys
P = json.load(open(sys.argv[1])); pt = P["partition_types"]
# 8.64-um core lattice (G0C hard_cores): columns x 77.76 / 250.56 (50.9 um street between the W/E pin faces), rows y 1486.08 /
# 1598.4 (49.4 um street between the rows; top of the block 1661.4, below the N landing bands at y 1669, 170 um under the N face)
SITE = {"m0": [77.76, 1486.08], "m1": [77.76, 1598.4], "m2": [250.56, 1486.08], "m3": [250.56, 1598.4]}
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

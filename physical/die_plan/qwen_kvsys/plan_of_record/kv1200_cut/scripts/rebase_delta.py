#!/usr/bin/env python3
"""DIE-KV-97: rebase a positions/orients delta written on plan A onto plan B (same types/insts/modules).
A target that is a slot (origin, module) of plan A becomes the same slot inst's origin in plan B; a pure translation
keeps its (dx, dy) relative to the core's own origin.  Orient is carried as given.
usage: rebase_delta.py PLAN_A PLAN_B DELTA_IN DELTA_OUT"""
import json, sys
A, B, din, dout = sys.argv[1:5]
pa = json.load(open(A))["partition_types"]; pb = json.load(open(B))["partition_types"]
D = json.load(open(din)); out = {}; nslot = ntr = 0
for tn, d in D.items():
    ha = {h["inst"]: h for h in pa[tn]["hard_cores"]}; hb = {h["inst"]: h for h in pb[tn]["hard_cores"]}
    assert set(ha) == set(hb) and all(ha[i]["module"] == hb[i]["module"] for i in ha), tn
    slot = {(round(h["origin_um"][0], 3), round(h["origin_um"][1], 3), h["module"]): i for i, h in ha.items()}
    out[tn] = {}
    for k, (x, y, o) in d.items():
        key = (round(x, 3), round(y, 3), ha[k]["module"])
        if key in slot:
            s = slot[key]; out[tn][k] = [hb[s]["origin_um"][0], hb[s]["origin_um"][1], o]; nslot += 1
        else:
            dx, dy = x - ha[k]["origin_um"][0], y - ha[k]["origin_um"][1]
            out[tn][k] = [round(hb[k]["origin_um"][0] + dx, 4), round(hb[k]["origin_um"][1] + dy, 4), o]; ntr += 1
json.dump(out, open(dout, "w"), indent=1)
print("rebased", sum(len(v) for v in out.values()), "moves:", nslot, "slot,", ntr, "translate")

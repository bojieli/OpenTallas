#!/usr/bin/env python3
"""HBM-HUBMESH-5: add grid.early sub-tree taps (rec_grt.json 'early_taps', routed GRT-RC OpenSTA arrival at the leaf
load A pin; the <=~100 um entry stub is not modelled) to a hub-only proof made by mk_hubproof.py.  FF = TT x ff-scale
(same UNCHECKED ratio as the mesh taps).   addearly.py PROOF_DIR REC.json PART ORIGIN_X ORIGIN_Y [FF_SCALE]"""
import json, re, sys
d, rec, part, ox, oy = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
ffs = float(sys.argv[6]) if len(sys.argv) > 6 else 0.8666
E = rec.get("early_taps") or []
if not E:
    raise SystemExit("rec has no early_taps")
for corner, f in (("TT", 1.0), ("FF", ffs)):
    p = f"{d}/tap_arrivals_{corner}.json"
    J = json.load(open(p))
    have = {t["port"] for t in J["taps"]}
    for e in E:
        m = re.fullmatch(r"K_clk_(c\d+)", e["port"])
        port = f"t_{part}__clk_{m.group(1)}"
        if port in have:
            raise SystemExit(f"{port} is both a mesh tap and an early tap")
        v = float(e["arr"]["TT"]["late"]) * f
        J["taps"].append(dict(port=port, part=part, late_ps=v, early_ps=v, slew_ps=20.0, cppr_node=part,
                              stages_from_root=0, xy_um=[ox + e["xy"][0], oy + e["xy"][1]], mesh_load=e["leaf"],
                              kind="native_core_clock", early_subtree=True))
    J["basis"] += f" + {len(E)} grid.early sub-tree taps (GRT-RC OpenSTA leaf arrival)"
    json.dump(J, open(p, "w"), indent=0)
print(len(E), "early taps added ->", d)

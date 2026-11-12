#!/usr/bin/env python3
"""seed_h10r1.py PLAN TYPE OUT_SEED.json VAR : VISLAYOUT2-S81/H10R1 hand seed for col_h10_r1 (positions only)."""
import json, sys, re
P = json.load(open(sys.argv[1])); tn = sys.argv[2]; out = sys.argv[3]; var = sys.argv[4]
t = P["partition_types"][tn]; seed = {}
H = {c["inst"]: c for c in t["hard_cores"]}
def put(n, x, y, o=None):
    h = H["u_r1." + n]
    seed[h["inst"]] = {"origin_um": [round(x, 3), round(y, 3)], "orient": o or h.get("orient", "R0")}
def at(n): return H["u_r1." + n]["origin_um"]
if var == "base":
    pass
else:
    # c-row x pitch W of each pair junction: compact c*_0..4 (47.52 um pitch) to free the junction slot
    for row in ("c6", "c8", "c10"):
        y = at("u_" + row + "_0")[1]
        for i, x in enumerate([34.56, 77.76, 120.96, 164.16, 207.36]):
            put("u_%s_%d" % (row, i), x, y)
    # row 1 band (c6/c7 y 241.92; e6/e7 S face 336.96): banks in the junction slot 34.56 below the ROM S face
    put("u_bs6", 276.48, 276.48)
    put("u_bs7", 838.08, 276.48)
    put("u_t4", 371.52, 259.2)
    put("u_c6_5", 466.56, 241.92); put("u_c6_6", 509.76, 241.92)
    put("u_t4__payload", 552.96, 250.56)          # over the e5 root N face, under the e6|e7 street
    put("u_n13", 648.0, 233.28); put("u_n12", 699.84, 233.28)
    for i, x in zip((0, 1), (751.68, 794.88)):
        put("u_c7_%d" % i, x, 241.92)
    put("u_s7", 907.2, 241.92)
    for i, x in zip((2, 3, 4, 5, 6), (933.12, 984.96, 1036.8, 1088.64, 1140.48)):
        put("u_c7_%d" % i, x, 241.92)
    # row 2 band (c8/c9 y 578.88; e8/e9 S face 691.2)
    put("u_bs8", 276.48, 630.72); put("u_bn6", 276.48, 604.8)
    put("u_t5", 371.52, 578.88)
    put("u_c8_5", 466.56, 578.88); put("u_c8_6", 509.76, 578.88)
    put("u_t5__payload", 552.96, 604.8)           # e6|e7 street -> e8|e9 street column
    put("u_n24", 1313.28, 812.16)
    put("u_bs9", 838.08, 630.72); put("u_bn7", 838.08, 604.8)
    put("u_s9", 907.2, 578.88)
    for i, x in zip((3, 4, 5, 6), (933.12, 984.96, 1036.8, 1088.64)):
        put("u_c9_%d" % i, x, 578.88)
    # top band (c10 y 933.12; e8/e9 N face 912.6)
    put("u_bn8", 267.84, 933.12); put("u_s10", 345.6, 933.12)
    put("u_bn9", 838.08, 933.12)
json.dump({tn: seed}, open(out, "w"), indent=1)
bad = [(k, v["origin_um"]) for k, v in seed.items() if any(abs(c / 8.64 - round(c / 8.64)) > 1e-6 for c in v["origin_um"])]
print(len(seed), "seeded; off-8.64-lattice:", bad)

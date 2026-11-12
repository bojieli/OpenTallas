#!/usr/bin/env python3
"""seed_h9r1.py PLAN TYPE OUT_SEED.json : VISLAYOUT2-S81 COL-H9R1 "R2-APRON" port.
col_h9_r1 = the col_h9_r2 floorplan at the same y with names e5/e6 (row 1), e7/e9 (row 2), e8 (bf group), c5/c6, c7/c9, c8,
s5/s6/s7/s9/s8, bs5/bs6/bs7/bs9, bn5/bn6/bn7/bn9, t3/t4/t5, plus n12/n13 between ROM row 1 and band 2, rg0 on the S band,
an E node column n14-n21 and n22/n19 in the N band.  Same defect: bs6 (e6 bank, 2 x 549 b) 200 um E of its junction,
t3/t4 payloads in the E corner, S window frame_int_i1 bits run E under the c5 row, no channel under the ROM S faces.
Same form as col_h9_r2 (row 1 + band 2 +77.76, row 2 + band 3 + bf group +120.96, banks under junctions, t3/t3p over the S
window, c5 row E of the window with s5 mid-row, c6 row/s6 +34.56), plus: n12/n13 ride with band 2, n17 rides with row 2,
n22 leaves the bf group's path (to the free NE strip), rg0 into the c5|c6 gap."""
import json, sys, re
P = json.load(open(sys.argv[1])); tn = sys.argv[2]; out = sys.argv[3]
t = P["partition_types"][tn]; seed = {}
def put(n, x, y, o=None):
    h = next(c for c in t["hard_cores"] if c["inst"] == "u_r1." + n)
    seed[h["inst"]] = {"origin_um": [round(x, 3), round(y, 3)], "orient": o or h.get("orient", "R0")}
A, B = 77.76, 120.96
for h in t["hard_cores"]:
    n = h["inst"].split(".", 1)[1]; x, y = h["origin_um"]
    if re.match(r"u_(e5|e6)\.|u_(c7|c9)_|u_s[79]$|u_bs[79]$|u_t4$|u_n1[23]$", n): put(n, x, y + A)
    elif re.match(r"u_e[79]\.|u_c8_|u_s8$|u_t5$|u_bn[79]$|u_t5__payload$|u_e8|u_n17$", n): put(n, x, y + B)
    elif re.match(r"u_c6_|u_s6$", n): put(n, x + 34.56, y)
put("u_bs5", 380.16, 120.96)
put("u_bs6", 838.08, 120.96)          # under the e6 u_w|u_e junction (882.36)
put("u_bn5", 198.72, 440.64)
put("u_bn6", 777.6, 440.64)
put("u_t3", 60.48, 43.2)
put("u_t3__payload", 181.44, 43.2)
put("u_t4__payload", 501.12, 552.96)
put("u_s5", 440.64, 43.2)
for i, x in enumerate([285.12, 336.96, 388.8, 475.2, 527.04, 578.88, 630.72]):
    put("u_c5_%d" % i, x, 25.92)
put("u_rg0", 673.92, 77.76)
put("u_n22", 1218.24, 1097.28)
bad = [(k, v["origin_um"]) for k, v in seed.items() if any(abs(c / 8.64 - round(c / 8.64)) > 1e-6 for c in v["origin_um"])]
json.dump({tn: seed}, open(out, "w"), indent=1)
print(len(seed), "seeded; off-8.64-lattice:", [b for b in bad if not re.search(r"u_e[5-9]", b[0])])

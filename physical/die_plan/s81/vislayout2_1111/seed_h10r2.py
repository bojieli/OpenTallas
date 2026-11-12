#!/usr/bin/env python3
"""seed_h10r2.py PLAN TYPE OUT_SEED.json : VISLAYOUT2-S81 COL-H10R2 hand form "R2-APRON" (port of col_h9_r2 R2-APRON).

col_h10_r2 is the col_h9_r2 floorplan shifted ~147 um N (names +1: e11/e12 row 1, e13/e14 row 2, e15 bf group, c11..c15,
s11..s15, bs11..bs14, bn11..bn14, t7..t9, n25..n30), with the same defect: bs12 (bank of the e12 pair, 2 x 549 b) and the
t8 payload in the E corner, the t7 payload along the S edge, the window bits running E under the c rows, and only 40 / 58 um
between each c row and the ROM S faces (xs_q pins).
Form (positions only): bands go to the R2-APRON y of col_h9_r2 (c11/c12 row y 25.92, ROM row 1 y 207.36, band 2 c13/c14
y 475.2, ROM row 2 y 639.36, band 3 y -25.92, bf group -25.92): aprons 118 / 101 um under the ROM rows; bs11/bs12 under
their junctions; t7/t7p over the S window; c11 row E of the window with s11 mid-row; c12 row/s12 +34.56; n25 into the E
corner; bn11/bn12 above ROM row 1 on the N pin groups; t8p beside t8 at the row-2 street mouth."""
import json, sys, re
P = json.load(open(sys.argv[1])); tn = sys.argv[2]; out = sys.argv[3]
t = P["partition_types"][tn]
seed = {}
def h_of(n): return next(c for c in t["hard_cores"] if c["inst"] == "u_r2." + n)
def put(n, x, y, o=None):
    h = h_of(n); seed[h["inst"]] = {"origin_um": [round(x, 3), round(y, 3)], "orient": o or h.get("orient", "R0")}
D1, DR1, D2, DR2, D3 = -146.88, -69.12, -69.12, -25.92, -25.92
for h in t["hard_cores"]:
    n = h["inst"].split(".", 1)[1]; x, y = h["origin_um"]
    if re.match(r"u_e1[12]\.", n): put(n, x, y + DR1)
    elif re.match(r"u_(c13|c14)_|u_s1[34]$|u_bs1[34]$|u_t8$|u_bn13$", n): put(n, x, y + D2)
    elif re.match(r"u_e1[34]\.", n): put(n, x, y + DR2)
    elif re.match(r"u_c15_|u_s15$|u_t9$|u_t9__payload$|u_bn14$|u_e15", n): put(n, x, y + D3)
    elif re.match(r"u_c12_|u_s12$", n): put(n, x + 34.56, y + D1)
put("u_bs11", 380.16, 120.96)
put("u_bs12", 846.72, 120.96)
put("u_bn11", 198.72 + 23.76, 440.64)
put("u_bn12", 790.56, 440.64)
put("u_t7", 60.48, 43.2)
put("u_t7__payload", 181.44, 43.2)
put("u_t8__payload", 501.12, 552.96)
put("u_s11", 440.64, 43.2)
for i, x in enumerate([285.12, 336.96, 388.8, 475.2, 527.04, 578.88, 630.72]):
    put("u_c11_%d" % i, x, 25.92)
put("u_n25", 1123.2, 43.2)
put("u_n27", 1166.4, 172.8)
bad = [(k, v["origin_um"]) for k, v in seed.items() if any(abs(c / 8.64 - round(c / 8.64)) > 1e-6 for c in v["origin_um"])]
json.dump({tn: seed}, open(out, "w"), indent=1)
print(len(seed), "seeded; off-8.64-lattice:", bad)

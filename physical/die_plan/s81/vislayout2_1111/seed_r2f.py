#!/usr/bin/env python3
"""seed_r2f.py PLAN TYPE OUT_SEED.json : VISLAYOUT2-S81 COL-H9R2 hand form "R2-APRON" (all origins on the 8.64 lattice).

Defect (real GRT, ce45 attempt_27, ov 57k, 98% M6 H): an H hot column x 1070-1120, y 0-320 = bs11 sitting at the E
corner (1131.84,155.52), feeding both e11 halves (2 x 549 b) and fed from the W (549 b), squeezed between n23 / the
c11 row and the e11.u_e S face, plus the t6p 536-b payload run along the S edge to the E corner and back up.
route_supply (edge_outline) base p99 1.50, worst face_H at the S window: all 1167+321 window bits run E under the c10 row.

Form (positions/orients only; same cores, same stations, same cycles):
 1. APRONS: row-1 ROM pairs (e10/e11) +77.76, the band above them (c12/c14 row, s12/s14, bs12/bs14, t7) +77.76,
    row-2 pairs (e12/e14), c13 row, s13, t8, t8p, bn12/bn14 and the bf group (e13*) +120.96: the empty 164-um N band
    becomes an 84-um apron under ROM row 1 and a 52-um apron under ROM row 2 (bank -> ROM S-face pin fan-out room).
 2. BANKS UNDER THEIR JUNCTIONS: bs10 (380.16,120.96) under e10's u_w|u_e junction, bs11 (829.44,120.96) under e11's
    (was at the E corner); bn10 (198.72,440.64) / bn11 (768.96,440.64) in the street right above ROM row 1, centred on
    the two halves' N pin groups.
 3. WINDOW CONSUMERS OVER THE WINDOW: t6 (60.48,43.2) and t6p (181.44,43.2) sit directly over the S window
    (x 6-330), so frame_int_i0 goes up into them instead of E under the c10 row; t7p (501.12,544.32) beside t7 at the
    row-2 street mouth; the c10 row E of the window (x 285-669) with s10 in its middle (440.64), the c11 row +34.56, n23 into the freed E corner.
"""
import json, sys, re
P = json.load(open(sys.argv[1])); tn = sys.argv[2]; out = sys.argv[3]
t = P["partition_types"][tn]
seed = {}
def put(n, x, y, o=None):
    h = next(c for c in t["hard_cores"] if c["inst"] == "u_r2." + n)
    seed[h["inst"]] = {"origin_um": [round(x, 3), round(y, 3)], "orient": o or h.get("orient", "R0")}
A, B = 77.76, 120.96
for h in t["hard_cores"]:
    n = h["inst"].split(".", 1)[1]
    x, y = h["origin_um"]
    if re.match(r"u_(e10|e11)\.|u_(c12|c14)_|u_s1[24]$|u_bs1[24]$|u_t7$", n):
        put(n, x, y + A)
    elif re.match(r"u_e1[24]\.|u_c13_|u_s13$|u_t8$|u_bn1[24]$|u_t8__payload$|u_e13", n):
        put(n, x, y + B)
    elif re.match(r"u_c11_|u_s11$", n):
        put(n, x + 34.56, y)
put("u_bs10", 380.16, 120.96)
put("u_bs11", 829.44, 120.96)
put("u_bn10", 198.72, 440.64)
put("u_bn11", 768.96, 440.64)
put("u_t6", 60.48, 43.2)
put("u_t6__payload", 181.44, 43.2)
put("u_t7__payload", 501.12, 544.32)
# s10 (cfg/go_tag sequencer of e10 + the c10 ROMs) right E of the window, next to t6 and under e10.u_w; c10 row E of it
put("u_s10", 440.64, 43.2)
for i, x in enumerate([285.12, 336.96, 388.8, 475.2, 527.04, 578.88, 630.72]):
    put("u_c10_%d" % i, x, 25.92)
put("u_n23", 1123.2, 43.2)
bad = [(k, v["origin_um"]) for k, v in seed.items() if any(abs(c / 8.64 - round(c / 8.64)) > 1e-6 for c in v["origin_um"])]
json.dump({tn: seed}, open(out, "w"), indent=1)
print(len(seed), "seeded; off-8.64-lattice:", bad)

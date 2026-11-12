#!/usr/bin/env python3
"""repack_lep.py BASE OUT : HEAD-95 fallback form v1, hd_lep0N re-pack inside 1892.16 x 1226.88 (no growth, no die move).
Pairs (4 x 777.6 x 492.48) stay.  Centre band (y 509.76-665.28): TWO macro rows abutting the pair rows (2.16 um) with a
~92-um logic street between them (was 3 rows ~5 um apart): each row 10 tx abutted (x 69.12-1762.8).  Vertical centre street (x 846.72-967.68): rx column abutting the W pair
column, 10 rx per half, 67-um street to the E pair column.  E strip (x 1745.28-1892.16) outside the E-face landing bands
(y 265-820): 3 srams stacked at y >= 830, 2 tx rotated R90 at y 20-190.  Orientation of moved tx/rx/sram unchanged
except the 2 E-strip tx (R90).  Grid 0.001 um (street_rule / gen legalize to their own grid)."""
import copy, json, sys
B = json.load(open(sys.argv[1])); P = copy.deepcopy(B)
t = P["partition_types"]["hd_lep0N"]
hc = t["hard_cores"]
tx = sorted([h for h in hc if ".g_tx" in h["inst"]], key=lambda h: h["inst"])
rx = sorted([h for h in hc if ".g_rx" in h["inst"]], key=lambda h: h["inst"])
sr = sorted([h for h in hc if "g_sram" in h["inst"]], key=lambda h: h["inst"])
TXW, TXH = 169.368, 29.16; RXW, RXH = 51.432, 20.808; SW, SH = 91.8, 39.432
AB = 2.16; X0 = 69.12; YB = 509.76 + AB; YT = 665.28 - AB - TXH
log = []
def put(h, x, y, orient=None):
    old = (h["origin_um"], h["orient"]); h["origin_um"] = [round(x, 3), round(y, 3)]
    if orient: h["orient"] = orient
    log.append(f"{h['inst']} {old[0]} {old[1]} -> {h['origin_um']} {h['orient']}")
for row, y in ((0, YB), (1, YT)):
    for i in range(10):
        put(tx[row * 10 + i], X0 + i * TXW, y)
# srams in the E strip outside the E-face landing bands (y 265-820): 2 at the bottom, 3 at the top, abutting the pairs
for i in range(2):
    put(sr[i], 1745.28 + AB, AB + i * SH)
for i in range(3):
    put(sr[2 + i], 1745.28 + AB, 830.0 + i * SH)
# rx column in the vertical street, abutting the W pair column
for i in range(20):
    half = i // 10; k = i % 10
    y0 = (17.28 + 60.0) if half == 0 else (665.28 + 60.0)
    put(rx[i], 846.72 + AB, y0 + k * RXH)
json.dump(P, open(sys.argv[2], "w"), indent=1)
print("\n".join(log)); print("moved", len(log))

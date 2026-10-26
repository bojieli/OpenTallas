#!/usr/bin/env python3
"""COORD 10-23 request: 'rpi' (interleaved) plan -- LSL rows between ROM row pairs, hub at the tile centre.  Same
outline (457.92 x 1157.76), faces, 20-um channel rule.  Rows bottom->top: R(b0) R(b1) L R(b2) R(b4) L R(b3) L (the same
5 ROM + 3 LSL rows as rpm/rpf, re-ordered), ROM rows as rpm (back to back, pins into the W/E channels), LSL rows as
rpm/rpf.  NL only: the NK node (47.5 x 432) spans 3 rows at the W face and would overlap ROM col 0 in the interleaved
ROM rows (ROM pair 345.6 + node 47.5 + three 20-um channels + 2 x 22.2 edges = 473 > 457.92) -> NK rpi infeasible."""
import json, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_repack as G, flyline_model as FM
CH, CM = 20.0, 2.16
order = ["R0", "R1", "L", "R2", "R4", "L", "R3", "L"]
y = G.up(CM + CH, 0.048); ys = []
prev = None
for r in order:
    if prev is not None:
        y = G.up(y + CH, 0.192 if r == "L" else 0.048)
    ys.append(y); y = y + (G.LSL_H if r == "L" else G.ROM_H); prev = r
H = G.up(y + CH + CM, 8.64)
rx = G.rom_x("m")
ch = {}; lrow = [v for r, v in zip(order, ys) if r == "L"]; rrow = {int(r[1]): v for r, v in zip(order, ys) if r != "L"}
for b, yy in rrow.items():
    ch[f"ROM0{b}"] = [rx[0][0], yy, "R0"]; ch[f"ROM1{b}"] = [rx[1][0], yy, "MY"]
for g, (x, r, o) in G.LSL_AT.items():
    ch[f"LSL{g}"] = [x, lrow[r], o]
mid = lrow[1]
W = G.W
fx = {}
for g, (x, r, o) in G.LSL_AT.items():
    xx = x - 13 if o == "MY" else x + G.LSL_W + 13
    fx[f"TX{g}"] = [xx, lrow[r] + 70]
wpin, epin = rx[0][0], rx[1][0] + G.ROM_W
fx.update({"RW_sw": [wpin - 12, (rrow[0] + rrow[2]) / 2 + 55], "RW_se": [epin + 12, (rrow[0] + rrow[2]) / 2 + 55],
           "RW_nw": [wpin - 12, (rrow[3] + rrow[4]) / 2 + 55], "RW_ne": [epin + 12, (rrow[3] + rrow[4]) / 2 + 55],
           "DW": [25, mid + 70], "DE": [W - 25, mid + 70], "HUB": [G.X_B + 50, lrow[0] + 70]})
for g in range(8):
    fx[f"TWW{g}"] = [40, mid + 20]; fx[f"TWE{g}"] = [W - 40, mid + 20]
ports = {"P_t_out": [0, mid + 100], "P_tap": [W, lrow[0] + 40], "P_tile_id": [W, lrow[0] + 60], "P_rst_n": [W, lrow[0] + 62]}
plan = {"name": "rpi_nl", "outline": [W, H], "children": ch, "ports": ports, "fixed": fx}
cen = json.load(open(sys.argv[1]))
r = FM.solve(cen, plan)
print("rpi_nl H", H, "rows", [round(v, 2) for v in ys], "bit-mm", r["bit_mm"])
for c, v in list(r["classes"].items())[:8]: print("  ", c, v)
json.dump({"plan": plan, "fly": r}, open(sys.argv[2], "w"))

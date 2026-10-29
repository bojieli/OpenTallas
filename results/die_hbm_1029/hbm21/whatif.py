#!/usr/bin/env python3
"""DIE-HBM-21 ESTIMATE: AUTO-GEOM demand_metrics what-if on an existing geom.tsv dump (placement held, geometry edited).
usage: whatif.py TOOLSDIR GEOM.TSV [ops...]
  ins_y:Y:DY   insert DY um of empty rows at y=Y (everything with centre/lower edge >= Y moves up, die grows)
  ins_x:X:DX   same in x
  mv:SUB:DX:DY move the macro(s) whose instance name contains SUB (std cells untouched)
Estimate only: std cells keep their placed xy, so the real place may differ (build decides)."""
import sys
sys.path.insert(0, sys.argv[1])
import geom_rules as G
D = G.Design(sys.argv[2])
for op in sys.argv[3:]:
    f = op.split(":")
    if f[0] in ("ins_y", "ins_x"):
        a, d = float(f[1]), float(f[2]); iy = f[0] == "ins_y"
        for k, c in list(D.cells.items()):
            lo = c[3] if iy else c[2]
            if lo >= a:
                c = list(c)
                if iy: c[3] += d; c[5] += d
                else: c[2] += d; c[4] += d
                D.cells[k] = tuple(c)
        for p in D.pins:
            if iy and p["y"] >= a: p["y"] += d
            if not iy and p["x"] >= a: p["x"] += d
        X0, Y0, X1, Y1 = D.die
        D.die = (X0, Y0, X1 + (0 if iy else d), Y1 + (d if iy else 0))
    elif f[0] == "mv":
        dx, dy = float(f[2]), float(f[3])
        for k, c in list(D.cells.items()):
            if c[0] == "M" and f[1] in c[6]:
                c = list(c); c[2] += dx; c[4] += dx; c[3] += dy; c[5] += dy; D.cells[k] = tuple(c)
for k, c in D.cells.items():
    if c[0] == "M": print("macro", c[6][-40:], [round(v, 3) for v in c[2:6]])
m = G.demand_metrics(D, "M5")
print("die", D.die, " ".join(f"{k}={m.get(k)}@{m.get(k.replace('_max','_at'))}" for k in ("channel_h_max", "channel_v_max", "col_v_max")))

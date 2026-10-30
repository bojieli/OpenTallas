#!/usr/bin/env python3
"""DIE-S81-29 WS3IR (COORD [DIE-S81-28-PARK](3)): PG-only fix-only variants of the WS3 V2 plan copy
(claude/die-s81-27-ws3-1029@74340c6433 plan_s13r2_ws3v2.json); only die.pg.domains[phy_lk_WS3] changes.

    python3 ws3_pg_variants_1029.py PLAN_V2.json OUT.json VARIANT
VARIANT: a45 = the plan's 45-um VDDPHY/VSS array re-laid as an axis-aligned checkerboard anchored to bumps.rect_um
              (bumps.anchor=rect; same pitch, same 175+175 count) so every macro edge row/column carries both rails;
         a75 = COORD literal: 75-um anchored checkerboard (sparser than the plan's 45-um array);
         b   = plan bumps kept, domain M8/M9 straps 1.92 um at 5.92-um pitch (spacing 1.04 >= the 1.0-um wide-metal
               rule; M8/M9 MAXWIDTH 2.0 forbids wider straps) = 64.9 % PG metal vs 44.4 % (1.92/8.64);
         ab  = a45 + b.
"""
import json
import sys

src, dst, var = sys.argv[1:4]
plan = json.load(open(src))
dm = next(d for d in plan["die"]["pg"]["domains"] if d["name"] == "phy_lk_WS3")
if var in ("a45", "ab"):
    dm["bumps"]["anchor"] = "rect"
if var == "a75":
    dm["bumps"].update(anchor="rect", pitch_um=75.0)
if var in ("b", "ab"):
    dm["grid"] = [dict(st, width_um=1.92, pitch_um=5.92, offset_um=2.96) for st in dm["grid"]]
dm["note"] += f"; DIE-S81-29 WS3IR PG variant {var} (ws3_pg_variants_1029.py)"
json.dump(plan, open(dst, "w"))
print(var, json.dumps({k: dm[k] for k in ("bumps", "grid")}))

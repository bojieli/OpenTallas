#!/usr/bin/env python3
"""S81 die-local plan delta (DIE-S81-51/RF-D 11-03, OWNER 18:57 conservative form): dsdv_gunit_l4 outline 345.6x64.8 ->
302.4x108 (fill <= 0.45, aspect 2.8; pins / LEF = the RF-C rfc_1103 set already on main). The old slot (1270.08, 336.96)
cannot grow (l5 below ends at 319.68, l0 above starts at 423.36), so the core moves to the free gunit__t1 field between
l3 (top 190.08) and l1 (bottom 380.16), left of l5 (x 1270.08): origin (950.4, 233.28) (4.32-um grid), orient MX kept;
its early core tap moves to the clk pin, now on the core S edge (155.052, 0.24; MX: the die-side top edge).  L0 / L5 / L4r faces are all registered both sides (the moved wires are
<= ~450 um, one repeated M5/M6 leg each).  Writes a plan COPY (plan_h2_2249.json is not edited):
    python3 delta_gl4.py <plan_h2_2249.json> <out plan json>
"""
import json, sys
src, out = sys.argv[1], sys.argv[2]
plan = json.load(open(src))
pt = plan["partition_types"]["gunit__t1"]
X0, Y0, W, H = 950.4, 233.28, 302.4, 108.0
rect = (X0, Y0, X0 + W, Y0 + H)
for hc in pt["hard_cores"]:
    if hc["module"] == "dsdv_gunit_l4":
        hc.update(origin_um=[X0, Y0], outline_um=[W, H], pins_file="inputs/core_pins/rfc_1103/dsdv_gunit_l4.json",
                  lef="physical/die_plan/s81/cores/legacy/lef/rfc_1103/dsdv_gunit_l4.lef")
        hc["note"] = (hc.get("note", "") + " | RF-D 11-03: 302.4x108 at (950.4, 233.28), conservative form OLAT 2").strip(" |")
    else:   # overlap check against every other core (2.16-um halo)
        ox, oy = hc["origin_um"]; ow, oh = hc["outline_um"]
        assert ox >= rect[2] + 2.16 or ox + ow <= rect[0] - 2.16 or oy >= rect[3] + 2.16 or oy + oh <= rect[1] - 2.16, hc["module"]
for t in pt["clock"]["taps"]:
    if t["name"] == "u_gunit.u_l4.clk":
        t["xy"] = [round(X0 + 155.052, 3), round(Y0 + H - 0.24, 3)]   # clk on the core S edge (MX: top in the die)
        t["note"] = t.get("note", "") + " | RF-D 11-03: moved with the core (clk S-edge pin 155.052, 0.24)"
# the grid+explicit light tap clk_t50 (1049.32, 289.32) sat in the free field the core now covers: move it into the
# l4 / l1 street (core top 341.28, l1 bottom 380.16), same x (schema added-tap outline / halo / spacing check)
for t in pt["clock"]["added_taps"]:
    if t["name"] == "clk_t50":
        t["xy"] = [1049.32, 360.72]
json.dump(plan, open(out, "w"), indent=1)
print("delta_gl4 OK", rect)

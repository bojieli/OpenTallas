# KV PHY interface fit, 2026-10-29 08:44 PDT

Picture: results/kv_phy_wrapper_0822/fit/geometry.png. Personally viewed by Codex and independent /root/coverage/review. Verdict: G1 PASS-COND for MODELED interface proposal only. No P&R, PHY silicon or SIGNED claim.

The E pin stripe sits immediately beside the E boundary FFs. All2500 native bit legs preserve actual bound concatenations, y and M4/M6 layer, with34.56um distance; no crossing or long wide buses. Clock354.252um and reset354.2919/56.532um pin-centre distances stay below405um. Macro leaves every existing clock island, reset collector and utility corridor clear. Existing full1.31383296mm2 PHY window remains reserved: analog body/power1.152605802mm2, digital interface0.0653184mm2, existing utility/edge channels0.095908758mm2. The decomposition is no area reduction.

Analog/digital separation follows tools/hbm_phy_bb.py. Upper-metal permeability must be explicitly MODELED, using tools/mem_compiler/hbm_phy_gen.py's licensed-PHY access-stack assumption (analog M1-M4 obstruction and M5 body; M6/M7 overhead access). Pin macro is M1-M3 obstructed, retaining real M4/M6 E pins. Gray analog reserve is never a free place/route area: materialize its physical cell blockages and routing OBS plus utility holes in actual ODB. Keep the separate PHY supply, PG access pins and gross PG footprint; measured IR remains required under existing rules.

Independent review recomputed2500 unique native legs and agreed PASS-COND. Before wrapper P&R: materialize the complete reserve/PG in actual LEF/ODB; currentevent27f bind must keep forwarded-clock grouping; inspect actual placed wrapper; measure local clock latency/duty, TT setup and FF hold. These are existing gates, not new checks.

Rejected before route: one near-full-slot macro covers existing dieclock/collector cells. Four PC row macros put high-number command groups >405um from the E-face ABI. Digital pin macro plus reserved analog body avoids both without added cycles or changed parent pins.

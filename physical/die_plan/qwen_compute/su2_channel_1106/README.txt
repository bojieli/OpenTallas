DIE-QC-85 11-06: SU2 south-channel form (slw_su_l1__cla2a78701 + slw_su_l1__clcc9d0155), candidate event, data_cycles 0.
Cause (measured on a2 4_1_cts.odb): the rsn landing macro sle_cland_w515_s_201 (184.9-413.9, 4.3-30.2) puts 517 M5
output pins on its north edge 4.3 um below lane4 (y 34.57); rsn_i pins enter at x 13.5-101 on the S face, so 517 nets
run east in the 0-4.3 um strip and back west to ft station 1 -> GRT-0116 (296 ov, M6 274) in x 150-250, y 0-150.
Estimate: ~133 derated tracks in that gap vs 517 nets.
Form: lane4 origin y 34.56 -> 60.48 (+25.92); rsn landing moved west over its own pins to (4.32, 25.92);
monitor_0 ring rect to x0 250.56; collector relays u_rrl_30/68 +30.24 y, u_rrl_73 beside the landing; ft rsn station
regs/bit sites +30.24 y. Channel ~930 derated tracks (~56% use). plan_geom (advisory): pin_reg max 175.7 -> 82.1,
p90 96.65 -> 32.5, r2r 694.7 -> 522.7; no plan sinks under cores. Image su2_geom.png (viewed).
apply_event.py: hash-guarded plan patch (base_guards.json = sha256 of each base type, qc53v2 base).
su2_build.py: kit-local overlay used for the vA/vB builds (Codex SU2 kits, synth + RTL reused, floorplan to route;
geometry files from gen.py phys of the patched plan; reset relays moved to the patched tree's own positions;
vB = same form + PLACE_DENSITY 0.40).

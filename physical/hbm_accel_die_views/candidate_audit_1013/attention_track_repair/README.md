Attention half contact repair, 2026-10-13

Original v13 placement and GRT STA both failed before timing: run_sta_place.tcl line119, at_SW_00_lo x has no legal origin. No SS/TT/FF verdict exists. Original clocks completed successfully and are preserved.

The unpublished half_v10 lo IO source mixed M5 centres 0 and12nm modulo48nm.1105 of5655 M5 contacts were offtrack and no origin existed in any orientation. The source contact plan now puts those1105 centres at12nm modulo48nm, moving them12nm while preserving pin names, widths, layers, faces, outlines and bank placement. Future source generation applies the same alignment in Pins.tcl/record; real bank-to-parent stubs still require routing.

The pathfinding abstract previously put full-outline M1..M7 OBS over every contact. Only the attention placeholders reserve a240nm peripheral access corridor on M4..M7 (192nm contact depth plus48nm clearance). Real views are untouched. This reserved corridor is not routed metal or signoff proof.

Both14043 named contacts across lo/hi pass width/area and same-layerOBS-clearance preflight, with legal origins in all4 orientations. M4 MX/R180 legitimately requires24nm origin residue, realized on the row lattice at1080nm modulo2160nm. The snap/assert remains enabled.

Run from repository root: python3 physical/hbm_accel_die_views/candidate_audit_1013/attention_track_repair/verify.py. This checks actual original-source rejected mutant and exact pin-name/use identity, plus repaired absolutetrack/access geometry. This is a geometry gate, not a behavioral qualification bench or full die timing result. Original and repairedLEF, raw audits and verifier are retained.

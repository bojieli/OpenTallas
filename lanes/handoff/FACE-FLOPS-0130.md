# FACE-FLOPS-0130 handoff (from FLOW-FIX-0100 item "COORD extra")

Lane clone: epyc9 /srv/opentallas-scratch/claude/lanes/face-flops-0130 (sparse, tools rtl common_flow tests). Profile rig: epyc9 .../lanes/ffrun.sh LABEL TOOLS_DIR (docker orfs, kit dsdv_slice_c1x_C__t9 3_2_place_iop.odb, hooks overlay-mounted; IST=<istations.tcl> overrides), outputs .../lanes/ff0130-out/<label>/.

| Item | State |
|---|---|
| Profile (t9, old-gen kit) | base face_flops about 1221 s (kit log). Pre-fix OT_FF_TIME: istations dominant (915 is_place calls each scanning every inst, >15 min). After fix: istations 7-8 s, reset_tree 199 s (old-gen kit; current generator already has RTR-SCAN), reset_taps 8 s, relay_mid 4 s, rest under 1 s, total about 222 s |
| Fix | kit_istations.py TCL_HEAD is_place: DFF list built once, per-literal index; is_dff_reset after clone creation. Test test_istation_scan_index.py (full scan vs indexed, same cells/order/miss) |
| Equality check | DONE: ot_face_flops, chain, relay_mid, post.def byte-identical (base2 vs opt2) |
| Pushed | main fbc23d5034. Next: regen kit on current generator, time reset_tree (RTR-SCAN) |

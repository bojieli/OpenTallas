# FACE-FLOPS-0130 handoff (from FLOW-FIX-0100 item "COORD extra")

Lane clone: epyc9 /srv/opentallas-scratch/claude/lanes/face-flops-0130 (sparse, tools rtl common_flow tests). Profile rig: epyc9 .../lanes/ffrun.sh LABEL TOOLS_DIR (docker orfs, kit dsdv_slice_c1x_C__t9 3_2_place_iop.odb, hooks overlay-mounted; IST=<istations.tcl> overrides), outputs .../lanes/ff0130-out/<label>/.

| Item | State |
|---|---|
| Profile (t9, old-gen kit) | base face_flops about 1221 s (kit log). Pre-fix OT_FF_TIME: istations dominant (915 is_place calls each scanning every inst, >15 min). After fix: istations 7-8 s, reset_tree 199 s (old-gen kit; current generator already has RTR-SCAN), reset_taps 8 s, relay_mid 4 s, rest under 1 s, total about 222 s |
| Fix | kit_istations.py TCL_HEAD is_place: DFF list built once, per-literal index; is_dff_reset after clone creation. Test test_istation_scan_index.py (full scan vs indexed, same cells/order/miss) |
| Equality check | DONE: ot_face_flops, chain, relay_mid, post.def byte-identical (base2 vs opt2) |
| Pushed | main fbc23d5034. Next: regen kit on current generator, time reset_tree (RTR-SCAN) |

## CODEX notes 11-21 02:22 PST

- Current RTR-SCAN result on the same t9 3_2 checkpoint as opt2, using a read-only hook overlay. Reset tree 189.4 to 6.6 seconds, timed hook sum 213.5 to 27.4 seconds. Post DEF and four face/station seating files byte-identical. E9 unit oth-ubuntu-1910442-1795256398 exit 0, scratch2/claude/lanes/ff0130-rtr-replay/rtr_scan2. Read-only review of the parent t9 placement showed the west macro column feeding the southern core and a long E-facing memory bank row. No route requested for this hook measurement. First launcher supplied a nonexistent IST file (Docker exit 125) and its prior script masked it with a successful grep. Replacement used the real opt2 IST file and propagated the Docker status.

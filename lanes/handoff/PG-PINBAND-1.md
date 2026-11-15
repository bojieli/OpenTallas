# PG-PINBAND-1 handoff (11-15, FABLE-ROUTE lever 2, takes over PG-AWARE-1 scope)
Branch claude/pg-pinband-1-1114 (off PG-AWARE-1 240cf2612f; localhost /home/ubuntu/wt-pg-aware-1), tests test_pg_pin_check.py + test_pg_aware.py pass.
## Proof (cheap, minutes, no route)
Original PG-AWARE-1 route proofs never produced a RESULT (summary.tsv RUNNING/exit 2). Replaced by a 3-minute check on the failed kits' own 3_place.odb:
keepout (OT_PG_CELL_KEEPOUT mechanism) applied + detailed_placement, then re-check of cells in the 80 um band under an M5xM6 PG crossing:
coll_n 1773 -> 0, hd_spn 2183 -> 0, kv3_io_cor 3713 -> 0, sle_stm_v3 3993 -> 0, leaf t21f 2352 -> 0 (movable cells; FIXED under crossing 44-1669 stay, not routed cells). leaf t69 before keepout: 2034 band cells under crossings.
Pin check (2_floorplan, signal pins M5-M7 within 80 um, gap to PG < 0.072): t69 and t49 floorplan DBs 0 bad pins (VSS/VDD pins excluded; M7 phase kits).
Not proven: a route with DRT-0255 gone (no 2 h route run); t49 post-keepout row not returned.
## Install
pg_pin_check.tcl + gen hook (gen env OT_PG_PIN_CHECK=1 fail, =warn print; last POST_PDN step; FAIL_PREFLOOR error + PGPIN-0255 lines + pg_pin_check.tsv). Default OFF.
Cell side = PG-AWARE-1 OT_PG_CELL_KEEPOUT=1 + OT_PG_DIE_PHASE=1 (face tracks phase). Probe dirs intel2 ~/pg-pinband-1 (mk.sh remote.sh rerun.sh), scratch2 pg-pinband-1.
Standalone: ODB=x.odb CELLS=1 APPLY_KEEPOUT=1 openroad -exit pg_pin_check.tcl.
## Kits to key (KIT-OPS-5): DRT-0255 kits whose DB shows band cells under crossings: leaf t69/t25/t21f/t40f, slw_hc2, coll_n, hd_spn, kv3_io_cor, sle_stm_v3, ss t49: relaunch with OT_PG_CELL_KEEPOUT=1 + OT_PG_DIE_PHASE=1 + OT_PG_TRACK_TRUTH=1 (key = kit hash + failing net). Rollout to main/hosts (copy+mv) waits for ROOT-MERGE; I did not install on hosts.

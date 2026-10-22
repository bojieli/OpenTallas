## SAFE review, PC_H sr10f (QE3-PC2 FALLBACK, 2026-10-21)

sr10e (i_grp / i_grp_h face registers, +1 edge each, priced) plus:
- SAFE checklist 8, define OT_KVPC_CAL_DNR: calendar wait_q (16 x 16 b) and active_row (19 b) are reset-free DATA. wait_q[k] is read only while entry k is live (left_q != 0, still reset) and every go load (gk) rewrites both bytes; active_row is read only in a fired (live) event and is loaded by ga[1] on that go. While rn is low gk / fe / le / ga are 0, so both hold. Removes 275 async RESETN pins on the calendar rn copies (the sr10b wait_q / active_row reset-removal hold endpoints).
- Frame widened 267.84 -> 280.8 um (+12.96 um, parent slot adoption required, as sr10d); CTS 8 / 20 um; macro-edge guard 2.4 / 1.2 um; hold margin 50 ps.
1 Pins FIXED (sr10e). 2 Reach PASS. 3 Fanout PASS (census in gate). 4 Depth FIXED (sr10e). 5 Storage PASS (23 SRAM). 6 Floorplan: wider frame, lower util. 7 Clock: as sr10e. 8 Reset FIXED for the calendar data class; control / valid bits keep the landed reset.
Benches with --define OT_KVPC_CAL_DNR (V5.050): kvpc_cal m0 PASS (1014 gos, 169 fault rounds), m3 FAIL as required; kvpc_path m0 PASS; kvpc_tile_pc_h m0 PASS; the gate job runs every bench with the define.

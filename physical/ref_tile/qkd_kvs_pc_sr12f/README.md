# qkd_kvs_pc_sr12f (SQ-PCH-P FALLBACK, 2026-10-21) -- KV PC tile (TOP qkd_kvs_pc)

sr12e (i_grp / i_grp_h kept face registers, sink CTS 8 / 20 um, SRAM-edge guard 2.4 / 1.2 um, 50 ps hold margin) plus,
as PC_H sr10f (f8763a3e1):
- SAFE checklist 8, define OT_KVPC_CAL_DNR: calendar wait_q (16 x 16 b) and active_row (19 b) are reset-free DATA
  (wait_q[k] read only while entry k is live -- left_q, still reset -- and every go load rewrites it; active_row read only
  in a fired event and loaded by ga[1] on that go).  Removes ~275 async RESETN pins on the calendar rn copies.
- Frame widened 267.84 -> 280.8 um (+12.96 um, E face moves out; parent slot adoption required); lower utilisation.

## SAFE 8-point review
1 Pins FIXED (sr12e face registers). 2 Reach PASS (same macro lattice, +12.96 um width). 3 Fanout PASS (census in gate).
4 Depth FIXED (sr12e). 5 Storage PASS (23 SRAM). 6 Floorplan: wider frame, lower util, channels unchanged or wider.
7 Clock: as sr12e (sink CTS 8 / 20). 8 Reset FIXED for the calendar data class; control / valid bits keep the landed reset.
Benches with --define OT_KVPC_CAL_DNR (V5.050): see lanes/SQ-PCH-P.md (kvpc_cal m0 PASS / m3 FAIL, kvpc_path m0, kvpc_tile_pc m0).

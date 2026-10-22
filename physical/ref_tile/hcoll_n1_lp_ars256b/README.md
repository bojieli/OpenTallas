# ROWS256 landed COLL parent: hcoll_n1_lp_ars256b

This is the actual five-region parent with the closed ROWS256 issuer and FJ children. Its functional source is fd453c43a; both Q3/n1s0 positive tests and MUT1/2/4 ran on Verilator 5.050 and produced the required outcomes. Actual logs and source-pinned receipts are under results/rtl/hbm_coll_lp256_1021/takeover_2000. The sticky comparator correction preserves the existing 12-cycle status bound across repeated reset epochs. These functional results do not establish physical closure.

The outline is 1287.36 x 1261.44um. Existing child_lattice_um=8.64 preserves common M1-M7 track alignment for tiny 25.92/34.56um closed children and actual 20 um channels. HBM lead approved this existing option; the encapsulated SRAMs retain their43.2 um macro grid and the normal physical flow retains all PG/access checks. The old43.2 um child snap collapsed channels to8.64um. The explicit placements in spec.json are authoritative. Link0 uses its LEF's allowed R0 orientation; MY cannot simultaneously align its M3/M5 pins. The highest instruction slice sits centrally beside the reduce lanes.

SAFE review before the physical gate:

1. FIXED: long external buses have the declared input/output registers; every regional crossing uses a fixed-latency landing ring. Same-region direct paths follow the current owner policy. Reset enters one root and regional/child runs.
2. FIXED: bit-level child-pin planning has no direct child group above 500 um after legal placement. The405um planning target remains guidance; actual placed reach and STA must qualify. Long delivery/injection ports use two registered stages; their placement and resulting segment lengths remain to be measured.
3. PENDING NATIVE ADMISSION: hard children have closed views; new landing/pad/reset glue must pass the mapped<=32 census before floorplan. No census waiver or layout PASS is claimed.
4. PASS BY STRUCTURE: the parent adds wires, fixed-latency landing rings and register pads, without new arithmetic/mux depth. Actual mapped timing remains required.
5. PASS BY STRUCTURE: no new parent SRAM or runtime-indexed general storage; the standard fixed-slot landing rings are explicit. Existing issuer/link/FJ SRAMs stay inside their closed children.
6. FIXED: explicit legal channels and core-edge clearance; enlarged outlines with no fill squeezing. Actual synthesis area, native PG and pin access remain gate obligations.
7. PENDING MEASUREMENT: ck_sw/ck_wr/ck_rg/ck_hd/ck_lk are independent local roots, and every regional data crossing lands. Measure within-region TT/FF spread using the standard gate; no relaxed clock or timing constraints.
8. PASS FUNCTIONAL / PRICE RECORDED: static schedule, no credits/backpressure, all extra pin/landing cycles are in the exact compiler record. ISA command/data output ages differ and must be compensated individually by the die calendar; chain and token pricing were notified.

NEXT: mapped native admission, CTS and layout review for MAIN and fallback; then submit_exact on exact source. Preserve all predecessor failures.

# SYSFACE n32o/n32oa PG "unbound" root cause (QW-ORPHANS2 10-20)

Run read-only on the gate run dirs (ot-epyc9 ref_gate/qfd_sys_face_{n32o,n32oa}-20261020-053946), ORFS image asap7lock.
pg_stage.py, n32o, unbound native PG ITerms per stage ODB (DB global-connect rules present at every stage: .* VDD/VDDPE/VDDCE/VSS/VSSE):
  2_4_floorplan_pdn 0 / 121344; 3_2_place_iop 0; 3_4_place_resized 9020 / 122636 (placeN 2170 insts, inputN 885, wireN 98,
  u_N 317 + u_ot_pr_core 1040 resized); 3_place 9020; 4_cts 11028 / 137738 (+hold/rebuffer/clone); 5_1_grt 11028.
  dont_touch instances among the unbound: 0 at every stage (1594 dont_touch insts, all bound).
pg_gc.tcl on 5_1_grt.odb (in memory, nothing written): n32o 11028 -> 0, n32oa 10692 -> 0 after `global_connect`.
Cause: OpenROAD resizer/CTS create or swap cells without applying the DB global-connect rules; ORFS binds them in
final_connect.tcl (6_final: "Ensure all OR created (rsz/cts) instances are connected"). global_connect skips only
dont_touch instances, which main 67cb1acc7 binds before protection. The gate stops at GRT, so its ODB is pre-final_connect.
Conclusion: not a tile, kit or flow defect; the PG0 qualification belongs on the final routed ODB (pg_receipt on 6_final),
as for the closed BTAB (PG0). No cosmetic mid-flow connect was added.

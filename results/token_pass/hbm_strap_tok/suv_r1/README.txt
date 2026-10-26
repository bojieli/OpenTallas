TOK-HBM-SUV 2026-10-26 receipt (run dir epyc2:/srv/opentallas-scratch2/claude/tok-hbm-suv/suv_r2, ot-run unit oth-ubuntu-983072-1793003369 exit 0, source_commit 4b878a37ec8c21e2847160fe83f9cd95c3b09a67).
Runner tools/hbm_b2/strap_tok/run_su_slice.sh OUT 1500 3 (refuses dirty tree; all inputs repo-relative at source_commit; sources.sha256).
Vehicle: SU Q0 slice = B2n q_su00 + q_su01 hard cores (22 of 23: lane_exp0 FULL, lane_exp1..14 + lane_exp_l (15 x ot_hbm_su_pg_lane_exp_core_strap),
 4 x ot_hbm_su_pg_lanes4_core_strap, pretree, side_softplus) composed into the yosys-extracted glue of the unsplit twin ot_hbm_su_static_pgslice_lg_s
 #(QID 0,G 0,MLAT 4,ALAT 3,LEAF 1,MULTIRATE 1,COLLPORT 1,RF_LOCAL 1,PIN_REG 1,RSYNC 1,PRETREE 1) (66 member cells replaced, 0 left).
 side_rest is not a member-set core (remainder of u_side) and stays in the glue. No plan stations/face shells (function + strap check only).
Strap ties: 31 strap_* port ties on 19 plan instances, tied to the die_plan.json values; every value equals the master constant (su_report.json).
Results (every output bit incl. sticky fault and tree_o compared !== at every serial and stream edge, 3 power-on resets x 1500 serial edges):
 canon (canonical cores, master lane ids)   PASS checks 9000, 4500 serial cycles, 0 errors
 strap (plan modules, strap pins = plan)    PASS checks 9000, 4500 serial cycles, 0 errors
 old   (TR3 old constant variants)          PASS checks 9000, 4500 serial cycles, 0 errors  => strap == old == unsplit twin every edge
 mut   (strap values of lane_exp3/5 swapped) FAIL 390 mismatching edges (CAUGHT)
Activity: nonzero outputs 8997/9000 edges, tree_o nonzero 6629 edges; caveat: random-traffic stimulus (tb_hbm_su_pgslice_lg_s style), the sticky slice
 fault is high 8993 edges -- this is a lock-step vehicle, not a native SU.VOP programme/token-record run.
Superseded: an earlier run at d087ca7ae8 failed canon/strap/old alike (765 tree_o mismatches): the core port parser dropped side_softplus x/rst_n/r
 (comment after a port); fixed at 4b878a37ec (fail-closed port count). Its data was deleted.

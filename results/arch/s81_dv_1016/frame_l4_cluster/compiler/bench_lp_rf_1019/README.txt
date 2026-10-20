S81-FRAME4 10-19 variant rf: landed frame LP RTL with the kept-copy same-age reset forest (lp landing_reset_forest +
landing_reset_forest_children, 3-level ot_pl_land_reset_forest3), claude/s81-frame4-rf-1019 @b850173cf staged on
ot-epyc5, Verilator 5.050 (frame_bench.sh FRAME_LP=1).  col_h9 / col_h10: MUT0 plan (KK 2048) PASS, each PASS;
unland / landread / reset FAIL (NEGATIVE_CONTROL_FAILED_AS_EXPECTED).  Reset age unchanged (h9 depth 7, h10 depth 8).

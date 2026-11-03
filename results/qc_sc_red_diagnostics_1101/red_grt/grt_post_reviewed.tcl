source /work/grt_post_core.tcl
source /work/core_final_repair.tcl
source /work/grt_final_full.tcl
ot_clk_freeze_assert red_final_full_grt
ot_clk_dump $::env(RESULTS_DIR)/red_clock_freeze/clk_freeze_post.tsv post $::env(RESULTS_DIR)/red_clock_freeze/clk_freeze_nets.txt
exec python3 -I /work/clk_geom_diff.py $::env(RESULTS_DIR)/red_clock_freeze/clk_freeze_pre.tsv $::env(RESULTS_DIR)/red_clock_freeze/clk_freeze_post.tsv --json $::env(RESULTS_DIR)/red_clock_freeze/clock_diff.json
ot_pg_require_bound red_final_full_grt

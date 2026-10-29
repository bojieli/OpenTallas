source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 4_cts.sdc
set_propagated_clock [all_clocks]
if {![grt::have_routes]} {error "PHY delay requires actual restored GRT routes"}
source /work/clk_freeze.tcl
set phy_d $::env(RESULTS_DIR)/phy_delay_clock
file mkdir $phy_d
ot_clk_freeze $phy_d
global_route -start_incremental
source /work/phy_delay_apply.tcl
source /work/pg_connect.tcl
ot_pg_connect_all phy_delay
ot_pg_require_bound phy_delay
foreach rec $phy_delay_records {foreach c [lindex $rec 3] {[$phy_b findInst [lindex $c 0]] setDoNotTouch 1}}
check_placement -verbose
global_route -end_incremental -congestion_iterations 50
estimate_parasitics -global_routing
ot_clk_freeze_assert phy_delay
ot_clk_dump $phy_d/clk_freeze_post.tsv post $phy_d/clk_freeze_nets.txt
if {[catch {exec python3 -I /work/clk_geom_diff.py $phy_d/clk_freeze_pre.tsv $phy_d/clk_freeze_post.tsv --json $phy_d/clock_diff.json} msg]} {error "PHY delay clock diff: $msg"}
source /work/final_ff_hold.tcl
ot_final_ff_converge
ot_pg_connect_all phy_delay_final
ot_pg_require_bound phy_delay_final
write_db $::env(RESULTS_DIR)/5_1_phy_delay.odb
write_sdc -no_timestamp $::env(RESULTS_DIR)/5_1_phy_delay.sdc
write_verilog $::env(RESULTS_DIR)/5_1_phy_delay.v
write_guides $::env(RESULTS_DIR)/5_1_phy_delay.guide
puts "PHY_DELAY_GRT_DONE_NO_DRT"

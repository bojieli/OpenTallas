# Local data-net near miss. TT322.12ps slew vs320; logic/cycles unchanged.
read_spef $::env(RESULTS_DIR)/6_final.spef
source /work/clk_freeze.tcl
ot_clk_freeze
set b [ord::get_db_block]
set i [$b findInst _26200_]
if {$i eq "NULL" || [[$i getMaster] getName] ne "INVx1_ASAP7_75t_R"} {error "E0 local ECO: expected actual INVx1 driver _26200_"}
set old [$i getLocation]
global_route -start_incremental
replace_cell _26200_ INVx2_ASAP7_75t_R
if {[[$i getMaster] getName] ne "INVx2_ASAP7_75t_R"} {error "E0 local ECO replacement failed"}
puts "E0_LOCAL_RESIZE _26200_ INVx1->INVx2 location $old"
detailed_placement
check_placement -verbose
global_route -end_incremental
ot_clk_freeze_assert post_grt
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide

read_db /base/3_2_place_iop.odb
set ::env(RESULTS_DIR) /diag
set blk [ord::get_db_block]
set before [list [llength [$blk getInsts]] [llength [$blk getNets]] [llength [$blk getBTerms]]]
source /diag/hook.tcl
set after [list [llength [$blk getInsts]] [llength [$blk getNets]] [llength [$blk getBTerms]]]
if {$before ne $after} {error "driver strip changed netlist counts"}
source /src/physical/qwen_die_masters/out_flop_release.tcl
foreach n $pd_fixed {if {[[$blk findInst $n] getPlacementStatus] ne "PLACED"} {error "driver not released: $n"}}
puts "PAD_STRIP_VERIFY counts $before == $after; all driver cells released; output ports [llength $pd_candidates]"
write_db /diag/placement_only.odb
exit

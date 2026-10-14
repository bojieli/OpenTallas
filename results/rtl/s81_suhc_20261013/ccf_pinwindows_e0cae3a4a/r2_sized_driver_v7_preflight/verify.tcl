read_db /base/3_2_place_iop.odb
set ::env(RESULTS_DIR) /diag
set blk [ord::get_db_block]
proc pad_verify_links {blk} {
 set rows {}
 foreach inst [$blk getInsts] {foreach it [$inst getITerms] {
 if {![$it isInputSignal] && ![$it isOutputSignal]} continue
 set net [$it getNet]
 if {$net ne "NULL"} {lappend rows [list [$inst getName] [[$it getMTerm] getName] [$net getName]]}
 }}
 foreach bt [$blk getBTerms] {set net [$bt getNet];if {$net ne "NULL"} {lappend rows [list PORT [$bt getName] [$net getName]]}}
 return [lsort $rows]
}
set before_links [pad_verify_links $blk]
set before [list [llength [$blk getInsts]] [llength [$blk getNets]] [llength [$blk getBTerms]]]
source /diag/hook.tcl
set after_links [pad_verify_links $blk]
if {$before_links ne $after_links} {error "driver sizing changed connectivity"}
puts "PAD_STRIP_CONNECTIVITY [llength $before_links] signal connections identical"
set after [list [llength [$blk getInsts]] [llength [$blk getNets]] [llength [$blk getBTerms]]]
if {$before ne $after} {error "driver strip changed netlist counts"}
source /src/physical/qwen_die_masters/out_flop_release.tcl
foreach n $pd_fixed {if {[[$blk findInst $n] getPlacementStatus] ne "PLACED"} {error "driver not released: $n"}}
puts "PAD_STRIP_VERIFY counts $before == $after; all driver cells released; output ports [llength $pd_candidates]"
write_db /diag/placement_only.odb
exit

read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /work/probe.v
link_design pair_probe
initialize_floorplan -die_area {0 0 317.034000 127.440000} -core_area {4.32 4.32 312.714000 123.120000} -site asap7sc7p5t
source /work/reset_pair_place.tcl
set ::ot_reset_pair_plan_only [expr {$::env(OT_PAIR_MODE) eq "plan"}]
ot_reset_pair_place [ord::get_db_block] {{{pr_reset_u_rrl_639} {pr_reset_u_rrl_639_drive} 301.032000 111.300000} {{pr_reset_u_rrl_640} {pr_reset_u_rrl_640_drive} 16.032000 16.300000}} {} 8
if {!$::ot_reset_pair_plan_only} {
 detailed_placement
 check_placement -verbose
 ot_reset_pair_check [ord::get_db_block]
 set stat [ot_reset_pair_verify_hops [ord::get_db_block] 405]
 if {[dict get $stat count] != 1} {error "expected exact one registered relay arc"}
 write_db /work/paired.odb
}
set f [open /work/$::env(OT_PAIR_MODE)_cells.tsv w]
puts $f "inst\tx_um\ty_um\tw_um\th_um"
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
dict for {name xy} $::ot_reset_pair_locs {
 set i [$b findInst $name];set m [$i getMaster]
 puts $f "$name\t[expr {[lindex $xy 0]/double($u)}]\t[expr {[lindex $xy 1]/double($u)}]\t[expr {[$m getWidth]/double($u)}]\t[expr {[$m getHeight]/double($u)}]"
}
close $f
puts PAIR_CASE_DONE

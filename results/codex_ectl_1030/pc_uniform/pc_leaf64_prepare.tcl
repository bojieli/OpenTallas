foreach l $::env(OT_LIBS) {read_liberty $l}
read_db /work/run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base/3_place.odb
read_sdc /work/constraint.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
set ::env(RESULTS_DIR) /out
source /work/clk_freeze.tcl
ot_clk_freeze
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
set sqpin {}
foreach p [all_registers -data_pins] {
 set n [string map {\\ {}} [get_full_name $p]]
 if {[string first {u_ctl.core.on.sq_n[1]} $n]>=0 && [string match */D $n]} {lappend sqpin $p}
}
if {[llength $sqpin]!=1} {error "PC_DRIVE expected oneSQN1capture, got[llength $sqpin]"}
set sqpin [lindex $sqpin 0]
proc pc_measure {tag sqpin} {
 estimate_parasitics -placement
 set w [worst_slack -max]
 set ps [find_timing_paths -to [list $sqpin] -path_delay max -group_path_count 1]
 if {![llength $ps]} {error "PC_DRIVE missingtimedcounterpath"}
 set ss [get_property [lindex $ps 0] slack]
 puts "PC_DRIVE $tag worstTT $w sq1TT $ss slew [sta::max_slew_violation_count]"
 report_checks -to [list $sqpin] -path_delay max -format full_clock_expanded -fields {capacitance slew fanout} -group_path_count 1
}
pc_measure baseline $sqpin
set fa [$b findInst _327937_]
if {$fa eq "NULL" || [[$fa getMaster] getName] ne "FAx1_ASAP7_75t_R"} {error "PC_DRIVE originalFAidentitymissing"}
lassign [$fa getLocation] fx fy
insert_buffer -buffer_cell BUFx6f_ASAP7_75t_R -load_pins [list $sqpin] -location [list [expr {double($fx)/$u+2.16}] [expr {double($fy)/$u}]] -buffer_name codex_sq1_drive
set_dont_touch [get_cells codex_sq1_drive]
detailed_placement
check_placement -verbose
ot_clk_freeze_assert pc_sq1_buffer_placed
pc_measure sq1buffer $sqpin
write_db /work/run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base/3_place.odb
puts "PC_LEAF64_SN_PREPARED 0RTLcycles"
exit

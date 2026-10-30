foreach l $::env(OT_LIBS) {read_liberty $l}
read_db /work/run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base/4_cts.odb
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
write_db /out/pc_sq1_buffer_placed.odb
foreach nm {fanout38161 fanout38159} {
 set i [$b findInst $nm]
 if {$i eq "NULL" || [[$i getMaster] getName] ni {BUFx2_ASAP7_75t_R BUFx3_ASAP7_75t_R}} {puts "PC_DRIVE skipmodifiedfanout $nm";continue}
 replace_cell [get_cells $nm] [lindex [get_lib_cells */BUFx10_ASAP7_75t_R] 0]
 puts "PC_DRIVE dataonlyupsized $nm BUFx10"
}
detailed_placement
check_placement -verbose
ot_clk_freeze_assert pc_driver2_placed
pc_measure sq1buffer_and_po_drivers $sqpin
write_db /out/pc_drivers_placed.odb
puts "PC_DRIVE PLACEMENTRC coupononly;0RTLcycles; no GRT/DRT/signoff claim"
exit

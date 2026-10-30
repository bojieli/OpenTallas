foreach l $::env(OT_LIBS) {read_liberty $l}
read_db /work/run/results/asap7/hc_qkd_ectlk_q1__233_28x172_8/base/5_1_grt.odb
read_sdc /work/constraint.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
set ::env(RESULTS_DIR) /work
source /work/clk_freeze.tcl
ot_clk_freeze
set_dont_use [get_lib_cells -quiet */DFF*]
set k 0
foreach nm {_09551_ _09560_ _09540_ _09614_} {
 set load [get_pins $nm/A]
 if {[llength $load]!=1} {error "Q1B2 missing $nm/A"}
 set y [expr {119.0-0.81*$k}]
 set last [expr {$k<3?232.0:194.0}]
 set j 0
 foreach x [list 13.0 121.0 $last] {
  set bn codex_q1relay_${k}_${j}
  insert_buffer -buffer_cell BUFx12f_ASAP7_75t_R -load_pins $load -location [list $x $y] -buffer_name $bn
  set_dont_touch [get_cells $bn]
  incr j
 }
 incr k
}
detailed_placement
check_placement -verbose
ot_clk_freeze_assert Q1B2placed
write_db /work/q1B2_placed.odb
puts "Q1B2_PLACED 12noninvertingdatarelays;0FFclockpinscycleschanges"
exit

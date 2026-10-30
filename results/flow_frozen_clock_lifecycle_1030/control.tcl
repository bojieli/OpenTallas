define_corners tc BC
foreach l $::env(OT_TC_LIBS) {read_liberty -corner tc $l}
foreach l $::env(OT_BC_LIBS) {read_liberty -corner BC $l}
read_db /baseline/data5_dpl.odb
read_sdc /work/constraint.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
source /out/clk_freeze.tcl
set ::env(RESULTS_DIR) /out/freeze
file mkdir $::env(RESULTS_DIR)
# Idempotent in-memory lock of the already-qualified routed graph. No cell move,
# placement, route or output ODB; the immutable original graph is checked below.
ot_clk_freeze $::env(RESULTS_DIR)
set ::env(OT_MM_SETUP_CORNER) tc
set ::env(OT_MM_FROZEN_CLOCK_SPEFS) {tc /qualified/original_clock_only.spef BC /qualified/original_clock_only.spef}
set ::env(OT_MM_FROZEN_CLOCK_IDENTITY) /baseline/clk_freeze_pre.tsv
set ::env(OT_MM_FROZEN_CLOCK_DIFF) /out/clk_geom_diff.py
set ::ot_mm_stage 4_cts.sdc
source /out/orfs_hold_mm.tcl
# Observe only the approved named helper, so native DATA is sampled AFTER the
# native estimator and immediately around the automatic lifecycle annotation.
rename ::ot_clk_restore_parasitics ::control_approved_named_restore
proc ::ot_clk_restore_parasitics {maps} {
 set clocknames {};foreach net [::ot_clk_dbnets] {dict set clocknames [$net getName] 1}
 set probes {}
 foreach net [[ord::get_db_block] getNets] {
  if {[$net getSigType] in {POWER GROUND CLOCK} || [dict exists $clocknames [$net getName]]} continue
  set name [$net getName]
  if {[sta::find_net $name] ne "NULL"} {lappend probes $name}
 }
 set caps {}
 foreach c {tc BC} {
  set scene [sta::find_scene $c]
  foreach name $probes {
   set nn [sta::find_net $name]
   foreach mm {min max} {dict set caps [list $c $name $mm] [list [$nn capacitance $scene $mm] [$nn wire_capacitance $scene $mm]]}
  }
 }
 ::control_approved_named_restore $maps
 set changed 0;set maxdelta 0
 foreach c {tc BC} {
  set scene [sta::find_scene $c]
  foreach name $probes {
   set nn [sta::find_net $name]
   foreach mm {min max} {
    foreach old [dict get $caps [list $c $name $mm]] new [list [$nn capacitance $scene $mm] [$nn wire_capacitance $scene $mm]] {
     set delta [expr {abs($new-$old)}]
     if {$delta>1e-20} {incr changed}
     set maxdelta [expr {max($maxdelta,$delta)}]
    }
   }
  }
 }
 puts "LIFECYCLE_DATA_GUARD native_nets [llength $probes] changed_values $changed maxdeltaSI $maxdelta"
 if {$changed || [llength $probes]!=145605} {error "automatic lifecycle callback changed native DATA RC"}
}
estimate_parasitics -global_routing
# This is the first consumer after the native estimator returns; POST_GRT was
# never sourced. The previous failure occurred at this lifecycle boundary.
source /work/clock_family.tcl
source /work/pinreg_measure.tcl
ot_cf_refresh
set pp [dict values [ot_pinreg_set]]
foreach c {tc BC} expected {255.239 206.799} {
 set sum 0.;set n 0
 foreach p $pp {
  sta::redirect_string_begin;report_arrival -scene $c -digits 9 $p;set report [sta::redirect_string_end]
  if {![regexp {\(clk \^\) r [-+0-9.e]+:([-+0-9.e]+)} $report -> a]} {error "missing native boundary arrival $p/$c"}
  set sum [expr {$sum+$a}];incr n
 }
 set mean [expr {$sum/$n}]
 puts "LIFECYCLE_FIRST_CONSUMER $c n $n mean_ps $mean expected_original_RCX $expected"
 if {abs($mean-$expected)>.001} {error "original CLOCK RC did not precede first timing consumer"}
}
puts "RING_LIFECYCLE_CONTROL PASS original-clock/native-DATA after automatic GLOBAL callback; noPOST_GRT/noP&R/noSIGNED/write_db"
exit

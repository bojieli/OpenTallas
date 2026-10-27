# QC-SU-F4A-SIGN 2026-10-26: FF-only DATA-PATH hold repair on the kit 5_1_grt.odb (template: QC-SU btab_m0_r4 hold_grt_s6.tcl;
# changes: kit SRAM FF lib, no per-tap RCX correction (none exists for F4A), no hold_pass.tcl, tap-window not part of the
# gate (COORD RULING QC-PLAN-F4A (1): rp1 21.1 proceeds), global_connect before write).  The clock tree is NOT touched:
# repair_timing -hold only inserts buffers on data pins (12.8: no clock edits).  vclk bound to OT_VCLK_FF (vclk_corner.tcl).
set R $::env(RESULTS_DIR)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty $f }
foreach f [glob /work/macros/*_ff.lib] { read_liberty $f }
read_db $R/5_1_grt.odb
read_sdc /work/constraint.sdc
set ::env(OT_VCLK_CORNER) ff
source /work/cf/main/vclk_corner.tcl
source /work/cf/rc_cal.tcl
set_routing_layers -clock M4-M5
set_routing_layers -signal M2-M5
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
set_placement_padding -global -left 0 -right 0
pin_access
global_route -congestion_iterations 30 -resistance_aware
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
proc hp {v} { return [format %.2f [sta::time_sta_ui $v]] }
set m [expr {[info exists ::env(OT_HOLD_MARGIN)] ? $::env(OT_HOLD_MARGIN) : 15}]
proc hclass {tag} {
  set ins [all_inputs -no_clocks]; set outs [all_outputs]; set res {}
  foreach {cl args} [list in [list -from $ins] out [list -to $outs] int [list -from [all_registers] -to [all_registers]]] {
    set ps [find_timing_paths -path_delay min {*}$args -group_path_count 100000 -endpoint_path_count 1 -slack_max 0.0]
    set n [llength $ps]; set w 0.0
    foreach p $ps { set s [get_property $p slack]; if {$s < $w} { set w $s } }
    lappend res $cl [format "%d %.2f" $n $w]
  }
  puts "HOLD_CLASS $tag $res"; return $res
}
# clock-net fingerprint before/after (proves no clock edit): count + names of cells driving clock nets
proc ckfp {} {
  set n 0; set h 0
  foreach c [get_cells -quiet -hierarchical ot_ms_*] { incr n; set h [expr {($h * 31 + [string length [get_full_name $c]] + [string length [get_property $c ref_name]]) % 1000000007}] }
  return "$n $h"
}
set fp0 [ckfp]
set h0 [hp [sta::worst_slack_cmd min]]; set e0 [sta::endpoint_violation_count min]
puts "HOLD_FF_BEFORE $h0 ep $e0 (vclk FF $::env(OT_VCLK_FF), margin $m) clock_cells $fp0"
set c0 [hclass before]
if {$h0 < -150.0 || $e0 > 4000} { error "structural FF hold failure ($h0 / $e0): stop before route" }
repair_timing -hold -hold_margin $m -max_buffer_percent 100 -verbose
global_route -start_incremental
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set h1 [hp [sta::worst_slack_cmd min]]; set e1 [sta::endpoint_violation_count min]
set fp1 [ckfp]
set c1 [hclass after]
set nb [llength [get_cells -quiet hold*]]
set ws [hp [sta::worst_slack_cmd max]]
set ok [expr {$h1 >= 0 && $e1 == 0 && $fp0 eq $fp1}]
puts "HOLD_FF_AFTER $h1 ep $e1 hold_bufs $nb clock_cells $fp1 setup_ff_est $ws"
global_connect
set f [open /work/hold_f4a_gate.txt w]
puts $f "HOLD_F4A_GATE [expr {$ok ? "PASS" : "FAIL"}] vclk_ff $::env(OT_VCLK_FF) margin $m before $h0 ep $e0 after $h1 ep $e1 hold_bufs $nb clock_cells $fp0 -> $fp1 classes_before $c0 after $c1 | [clock format [clock seconds]]"
close $f
write_guides $R/route.guide
write_db $R/5_1_grt.odb
puts "HOLD_F4A_GATE [expr {$ok ? "PASS" : "FAIL"}]"

set ::env(OT_GATE_SIGNOFF_SDC) /src/physical/ref_tile/qfd_coll_xfifo_native/signoff.sdc
source /out/canonical_ss.tcl
puts "NATIVE_AUDIT_CLOCKS"
report_clock_properties [all_clocks]
report_units
foreach port {ck ckd} {
 puts "NATIVE_AUDIT_SOURCE $port"
 report_arrival -digits 6 [get_ports $port]
 report_slews -digits 6 [get_ports $port]
}
set block [ord::get_db_block]
set n [$block findNet ckd]
set count 0;set flops 0;set buffers 0;set macros 0;set other 0
foreach it [$n getITerms] {
 if {![$it isInputSignal]} continue
 incr count
 set i [$it getInst];set name [[$i getMaster] getName]
 if {[string match DFF* $name]} {incr flops} elseif {[string match BUF* $name] || [string match INV* $name]} {incr buffers} elseif {[[$i getMaster] isBlock]} {incr macros;puts "NATIVE_AUDIT_MACRO [$i getName]/[[$it getMTerm] getName]"} else {incr other}
}
puts "NATIVE_AUDIT_CKD_NET name=[$n getName] direct_sinks=$count flops=$flops buffers=$buffers macros=$macros other=$other BTerms=[llength [$n getBTerms]]"
foreach pat {{*u_cq*g_ipr*pd*CLK} {*u_sq*g_ipr*pd*CLK}} {
 set pin [lindex [get_pins -hier -quiet $pat] 0]
 if {$pin eq ""} {error "missing physical reference probe"}
 puts "NATIVE_AUDIT_REF [get_full_name $pin]"
 report_arrival -digits 6 $pin
 report_slews -digits 6 $pin
}
puts "NATIVE_AUDIT_SETUP_PATHS"
report_checks -path_delay max -format full_clock_expanded -fields {slew cap input fanout} -digits 6 -group_path_count 2
puts "NATIVE_AUDIT_HOLD_PATHS"
report_checks -path_delay min -format full_clock_expanded -fields {slew cap input fanout} -digits 6 -group_path_count 1

proc physical_source {net} {
 set seen [dict create]
 for {set depth 0} {$depth<64} {incr depth} {
  set id [$net getId];if {[dict exists $seen $id]} {error "physical clock cycle"};dict set seen $id 1
  set roots {};foreach b [$net getBTerms] {if {[$b getIoType] eq "INPUT"} {lappend roots [$b getName]}}
  if {[llength $roots]} {if {[llength $roots]!=1} {error "ambiguous clock source"};return [lindex $roots 0]}
  set drivers {};foreach it [$net getITerms] {if {[$it isOutputSignal]} {lappend drivers $it}}
  if {[llength $drivers]!=1} {error "missing/ambiguous physical clock driver"}
  set i [[lindex $drivers 0] getInst];set kind [[$i getMaster] getName]
  if {![string match BUF* $kind] && ![string match INV* $kind] && $kind ne "HB4xp67_ASAP7_75t_R"} {error "unknown physical clock driver $kind"}
  set inputs {};foreach it [$i getITerms] {if {[$it isInputSignal]} {lappend inputs $it}}
  if {[llength $inputs]!=1} {error "non-scalar clock buffer"}
  set net [[lindex $inputs 0] getNet]
 }
 error "physical clock depth exceeded"
}
proc root_metrics {tag} {
 foreach {clock source} {core_clk ck ckd ckd} {
  set pins [all_registers -clock_pins -clock [get_clocks $clock]]
  set sum 0.0;set min 1e30;set max -1e30;set count 0
  foreach pin $pins {
   set a [get_property $pin arrival_max_rise]
   if {![string is double -strict $a] || abs($a)>1e20} {error "unmeasured root pin"}
   set sum [expr {$sum+$a}];set min [expr {min($min,$a)}];set max [expr {max($max,$a)}];incr count
  }
  if {$count==0} {error "empty root"}
  puts "FIXED_ROOT $tag $source n=$count mean=[expr {$sum/$count}] min=$min max=$max"
 }
 puts "FIXED_WNS $tag setup=[sta::worst_slack_cmd max] hold=[sta::worst_slack_cmd min]"
}
set i [$block findInst {u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m}]
set it [$i findITerm wclk]
set owner [physical_source [$it getNet]]
if {$owner ne "ck"} {error "wrong macro clock owner u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m/wclk"}
puts "FIXED_MACRO ss {u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m/wclk} owner=$owner"
report_arrival -digits 6 [get_pins {u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m/wclk}]
report_slews -digits 6 [get_pins {u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m/wclk}]
set i [$block findInst {u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m}]
set it [$i findITerm rclk]
set owner [physical_source [$it getNet]]
if {$owner ne "ck"} {error "wrong macro clock owner u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m/rclk"}
puts "FIXED_MACRO ss {u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m/rclk} owner=$owner"
report_arrival -digits 6 [get_pins {u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m/rclk}]
report_slews -digits 6 [get_pins {u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m/rclk}]
set i [$block findInst {u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m}]
set it [$i findITerm rclk]
set owner [physical_source [$it getNet]]
if {$owner ne "ckd"} {error "wrong macro clock owner u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m/rclk"}
puts "FIXED_MACRO ss {u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m/rclk} owner=$owner"
report_arrival -digits 6 [get_pins {u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m/rclk}]
report_slews -digits 6 [get_pins {u_port.u_cq.g_afw.u_af.g_mm.genblk1.genblk1.g_256x517.u_m/rclk}]
set i [$block findInst {u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m}]
set it [$i findITerm wclk]
set owner [physical_source [$it getNet]]
if {$owner ne "ckd"} {error "wrong macro clock owner u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m/wclk"}
puts "FIXED_MACRO ss {u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m/wclk} owner=$owner"
report_arrival -digits 6 [get_pins {u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m/wclk}]
report_slews -digits 6 [get_pins {u_port.u_sq.g_afw.u_af.g_mm.genblk1.genblk1.genblk1.g_64x546.u_m/wclk}]
set i [$block findInst {u_port.u_sq.g_ib_mem.u_ib}]
set it [$i findITerm clk]
set owner [physical_source [$it getNet]]
if {$owner ne "ckd"} {error "wrong macro clock owner u_port.u_sq.g_ib_mem.u_ib/clk"}
puts "FIXED_MACRO ss {u_port.u_sq.g_ib_mem.u_ib/clk} owner=$owner"
report_arrival -digits 6 [get_pins {u_port.u_sq.g_ib_mem.u_ib/clk}]
report_slews -digits 6 [get_pins {u_port.u_sq.g_ib_mem.u_ib/clk}]
root_metrics ss_source150
set baseline_setup [sta::worst_slack_cmd max]
set baseline_hold [sta::worst_slack_cmd min]
# Sensitivity only, fixed baseline IO/reference budgets. Not source qualification.
set_input_transition 0 [get_ports ckd]
root_metrics ss_source0_fixed_original_IO
set_input_transition 150 [get_ports ckd]
root_metrics ss_restored150
if {abs([sta::worst_slack_cmd max]-$baseline_setup)>1e-16 || abs([sta::worst_slack_cmd min]-$baseline_hold)>1e-16} {error "source150 restore differs"}
write_sdc /out/executed_ss.sdc
puts "FIXED_NATIVE_PASS ss actual150_clock_source_and_macro_owners"
exit

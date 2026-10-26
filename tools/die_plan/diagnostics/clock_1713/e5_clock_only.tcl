# PARTIAL routing diagnostic. All data wires are omitted, not qualified.
source /scripts/timing_libs.tcl
ot_lib_load TT /out/libraries_route_TT.json /work/config.mk
read_db /work/checkpoint/4_cts.odb
read_sdc /work/checkpoint/4_cts.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
set block [ord::get_db_block]
set port [$block findBTerm ck]
if {$port eq "NULL"} {error "E5 partial clock diagnostic requires actual ck source"}
set pending [list [$port getNet]]
set selected {}
while {[llength $pending]} {
  set net [lindex $pending end]; set pending [lrange $pending 0 end-1]
  set name [$net getName]
  if {[dict exists $selected $name]} continue
  dict set selected $name $net
  foreach term [$net getITerms] {
    if {![$term isInputSignal]} continue
    set inst [$term getInst]
    if {[[$inst getMaster] isBlock]} continue
    if {![regexp {^(BUF|INV|HB|CKBUF|CKINV)} [[$inst getMaster] getName]]} continue
    foreach output [$inst getITerms] {
      if {[$output isOutputSignal] && [$output getNet] ne "NULL"} {lappend pending [$output getNet]}
    }
  }
}
if {[dict size $selected] != 2002} {error "Clock ownership incomplete: [dict size $selected] nets vs native 2002"}
set omitted 0
foreach net [$block getNets] {
  if {[$net getSigType] ni {POWER GROUND} && ![dict exists $selected [$net getName]]} {incr omitted}
}
set fp [open /out/partial_scope.json w]
puts $fp "{\"partial_routing\":true,\"clock_nets\":[dict size $selected],\"omitted_nonclock_signal_nets\":$omitted,\"data_competition\":false,\"g2_or_signoff\":false}"
close $fp
set_routing_layers -signal M2-M5 -clock M6-M7
set_global_routing_layer_adjustment M2-M7 0.0
set_nets_to_route [dict keys $selected]
puts "PARTIAL_CLOCK_ONLY nets=[dict size $selected] omitted_nonclock_signals=$omitted no_data_competition=1 NO_G2_OR_SIGNOFF"
pin_access
if {[catch {global_route -congestion_report_file /out/congestion.rpt -congestion_iterations 30 -verbose -resistance_aware} err]} {
  catch {write_guides /out/failed_clock.guide}
  write_db /out/failed_clock.odb
  error $err
}
write_guides /out/clock.guide
write_db /out/clock.odb
estimate_parasitics -global_routing
write_spef /out/clock.spef
puts "PARTIAL_CLOCK_RC_READY: omitted data demand and all-net competition remain untested"

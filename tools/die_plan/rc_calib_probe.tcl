# rc_calib_probe.tcl: clock-sink arrivals + hold WNS + long-net delays under (a) routed RCX SPEF or (b) GRT-stage estimate
# for each RC file in OT_RC_FILES. env: OT_MODE est|rcx, OT_LIBS (tcl file of read_liberty), OT_ODB, OT_SPEF, OT_SDC,
# OT_LAYERS (e.g. M2-M5), OT_RC_FILES, OT_NETS (net-name list), OT_OUT (prefix)
source $::env(OT_LIBS)
read_db $::env(OT_ODB)
read_sdc $::env(OT_SDC)
set_propagated_clock [all_clocks]
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
set nets {}
if {[info exists ::env(OT_NETS)] && [file exists $::env(OT_NETS)]} {
  set f [open $::env(OT_NETS)]; while {[gets $f l] >= 0} { if {$l ne ""} { lappend nets $l } }; close $f
}
proc dump {tag} {
  set f [open $::env(OT_OUT)_${tag}.tsv w]
  puts $f "HOLD\t[format %.3f [sta::time_sta_ui [sta::worst_slack_cmd min]]]\t[sta::endpoint_violation_count min]"
  puts $f "SETUP\t[format %.3f [sta::time_sta_ui [sta::worst_slack_cmd max]]]\t[sta::endpoint_violation_count max]"
  foreach p [all_registers -clock_pins] { set a ""; catch {set a [get_property $p arrival_max_rise]}; puts $f "CK\t[get_full_name $p]\t$a" }
  foreach n $::nets {
    set net [get_nets -quiet $n]; if {![llength $net]} continue
    set drv [get_pins -quiet -of_objects $net -filter "direction==output"]; if {[llength $drv] != 1} continue
    set da ""; catch {set da [get_property $drv arrival_max_rise]}
    if {$da eq ""} continue
    foreach s [get_pins -quiet -of_objects $net -filter "direction==input"] {
      set sa ""; catch {set sa [get_property $s arrival_max_rise]}
      if {$sa ne ""} { puts $f "NET\t$n\t[get_full_name $s]\t[format %.3f [expr {$sa-$da}]]" }
    }
  }
  close $f
}
if {$::env(OT_MODE) eq "rcx"} {
  read_spef $::env(OT_SPEF)
  dump rcx
} else {
  set L $::env(OT_LAYERS)
  source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
  set_routing_layers -signal $L -clock $L
  set have 0
  if {![catch {estimate_parasitics -global_routing} e]} { set have 1 }
  puts "RC_PROBE stored_routes=$have"
  if {!$have} {
    set_global_routing_layer_adjustment $L 0.5
    global_route -allow_congestion
  }
  foreach rc [split $::env(OT_RC_FILES)] {
    if {$rc eq ""} continue
    source $rc
    estimate_parasitics -global_routing
    dump [file rootname [file tail $rc]]
    puts "RC_PROBE done $rc"
  }
}
puts RC_PROBE_DONE
exit

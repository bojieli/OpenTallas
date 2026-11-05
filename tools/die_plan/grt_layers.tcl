# KW-FIX-16 11-05 (COORD 12:15 class, HBM-GAPS-1 finding): ORFS sets the GRT routing layers only in floorplan.tcl and
# stores them in the odb, so a GRT resumed from 4_cts.odb keeps the floorplan ceiling even after config.mk moves
# MIN/MAX_ROUTING_LAYER ("M6" resumes ran GRT at Max routing layer: M5).  Sourced first by the PRE_GLOBAL_ROUTE hook:
# when the odb signal range differs from MIN/MAX_ROUTING_LAYER, re-apply set_routing_layers -signal from the config.
# A fresh run (floorplan in the same config) has equal ranges: no command runs, the kit behaves as before.
# OT_GRT_LAYERS_SYNC=0 turns it off.  The clock range (MIN_CLK_ROUTING_LAYER, kit hooks) is not touched.
proc ot_grt_layers_sync {} {
  if {[info exists ::env(OT_GRT_LAYERS_SYNC)] && $::env(OT_GRT_LAYERS_SYNC) eq "0"} { return }
  if {![info exists ::env(MIN_ROUTING_LAYER)] || ![info exists ::env(MAX_ROUTING_LAYER)]} { return }
  set lo $::env(MIN_ROUTING_LAYER); set hi $::env(MAX_ROUTING_LAYER)
  if {$lo eq "" || $hi eq ""} { return }
  # a kit with its own FASTROUTE_TCL set the floorplan layers on purpose: leave its odb range alone
  if {[info exists ::env(FASTROUTE_TCL)] && $::env(FASTROUTE_TCL) ne ""
      && [file tail [file dirname $::env(FASTROUTE_TCL)]] ne "asap7"} {
    puts "OT_GRT_LAYERS: kit FASTROUTE_TCL $::env(FASTROUTE_TCL), odb range kept"; return
  }
  set tech [ord::get_db_tech]; set blk [ord::get_db_block]
  if {$tech eq "NULL" || $blk eq "NULL"} { return }
  set llo [$tech findLayer $lo]; set lhi [$tech findLayer $hi]
  if {$llo eq "NULL" || $lhi eq "NULL"} { puts "OT_GRT_LAYERS: WARNING unknown layer $lo/$hi, odb range kept"; return }
  set want_lo [$llo getRoutingLevel]; set want_hi [$lhi getRoutingLevel]
  set have_lo [$blk getMinRoutingLayer]; set have_hi [$blk getMaxRoutingLayer]
  if {$have_lo == $want_lo && $have_hi == $want_hi} {
    puts "OT_GRT_LAYERS: odb signal range = config $lo-$hi (no change)"
    return
  }
  puts "OT_GRT_LAYERS: odb signal range levels $have_lo-$have_hi != config $lo-$hi ($want_lo-$want_hi): set_routing_layers -signal $lo-$hi"
  set_routing_layers -signal $lo-$hi
}
ot_grt_layers_sync

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

# QC-DRT-LAYERS 11-25 (Fable flow review 02:4x): GRT layer-adjustment calibration, sourced first by grt_pre.tcl, so it
# reaches fresh and resumed GRT alike.  ORFS sets the asap7 default ROUTING_LAYER_ADJUSTMENT 0.25 on EVERY layer M2-M8
# at floorplan (stored in the odb tech layers).  With it GRT saw M2/M3 at 21-31 % use and 0 overflow, put 18 of 24 M
# demand units on M2+M3 (M4-M8 0.5-16 %), and DRT then opened at 129k-510k iteration-0 violations, ~80 % M2/M3
# shorts / EOL in the pin-access-dense rows that a 0.25 derate does not model.  OT_GRT_LAYER_ADJ = "L A L A ..." sets
# set_global_routing_layer_adjustment per layer (inside MIN..MAX_ROUTING_LAYER only) before global_route; the GRT
# model only -- no layer range, NDR, constraint, margin or gate changes.  Default below = M2/M3 0.40 (M4-M8 keep 0.25):
# same 5_1_grt.odb, fresh GRT + DRT, iteration-0 violations sle_fw_v2 137086 -> 110751 (-19 %), sle_sc_v1 145772 -> 118578
# (-19 %); M2+M3 demand share 80 -> 71 % / 70 -> 60 %, GRT WL +1.9 %, GRT setup TNS 0 both, hold TNS within 0.1 %.
# M2/M3 0.50 + M4-M7 0.15 measured -21 % / -14 %.  OT_GRT_LAYER_ADJ=0 (or off) keeps the odb values (old behaviour).  A kit with its own
# FASTROUTE_TCL chose its adjustments on purpose and is left alone; cons_grt_pre.tcl pin-layer cuts run after this.
set ::ot_grt_layer_adj_default "M2 0.40 M3 0.40"
proc ot_grt_layer_adjust {} {
  set spec [expr {[info exists ::env(OT_GRT_LAYER_ADJ)] ? [string trim $::env(OT_GRT_LAYER_ADJ)] : $::ot_grt_layer_adj_default}]
  if {$spec eq "" || $spec eq "0" || $spec eq "off"} { puts "OT_GRT_LAYER_ADJ off: odb layer adjustments kept"; return }
  if {[info exists ::env(FASTROUTE_TCL)] && $::env(FASTROUTE_TCL) ne ""
      && [file tail [file dirname $::env(FASTROUTE_TCL)]] ne "asap7"} {
    puts "OT_GRT_LAYER_ADJ: kit FASTROUTE_TCL $::env(FASTROUTE_TCL), odb layer adjustments kept"; return
  }
  if {[llength $spec] % 2} { error "OT_GRT_LAYER_ADJ '$spec': want layer/adjustment pairs" }
  set tech [ord::get_db_tech]; set blk [ord::get_db_block]
  if {$tech eq "NULL" || $blk eq "NULL"} { return }
  set lo [$blk getMinRoutingLayer]; set hi [$blk getMaxRoutingLayer]
  set done {}
  foreach {ln a} $spec {
    if {![string is double -strict $a] || $a < 0 || $a >= 1} { error "OT_GRT_LAYER_ADJ $ln '$a': want 0 <= a < 1" }
    set l [$tech findLayer $ln]
    if {$l eq "NULL"} { error "OT_GRT_LAYER_ADJ unknown layer $ln" }
    set lv [$l getRoutingLevel]
    if {$lv < $lo || $lv > $hi} continue
    set_global_routing_layer_adjustment $ln $a
    lappend done "$ln=$a"
  }
  puts "OT_GRT_LAYER_ADJ per-layer GRT adjustment: [join $done { }]"
}
ot_grt_layer_adjust

# Preserve routed clock metal while representing all existing clock layers in
# GRT's resource vector. The signal routing range is never raised. Staged only
# for explicitly opted-in route/final PRD seeds, before the first global_route.
proc ot_prd_inventory_layer {layer} {
  if {$layer eq "" || $layer eq "NULL"} { error "OT_PRD_CLOCK_INVENTORY missing decoded routing layer" }
  set level [$layer getRoutingLevel]
  if {$level <= 0} { error "OT_PRD_CLOCK_INVENTORY decoded non-routing layer [$layer getName]" }
  return $level
}
proc ot_prd_inventory_wire_top {wire} {
  set top 0
  set decoder [odb::dbWireDecoder]
  try {
    $decoder begin $wire
    while {1} {
      set op [$decoder next]
      if {$op == $::odb::dbWireDecoder_END_DECODE} break
      set layers {}
      switch $op {
        0 - 2 - 3 { set layers [list [$decoder getLayer]] }
        6 - 7 {
          set via [expr {$op == 6 ? [$decoder getVia] : [$decoder getTechVia]}]
          if {$via eq "" || $via eq "NULL"} { error "OT_PRD_CLOCK_INVENTORY missing decoded via" }
          set layers [list [$via getBottomLayer] [$via getTopLayer]]
        }
      }
      foreach layer $layers { set top [expr {max($top,[ot_prd_inventory_layer $layer])}] }
    }
  } finally {
    $decoder -delete
  }
  return $top
}
proc ot_prd_clock_inventory {} {
  set block [ord::get_db_block]
  set signal_lo [$block getMinRoutingLayer]
  set signal_hi [$block getMaxRoutingLayer]
  set clock_lo [$block getMinLayerForClock]
  set clock_hi [$block getMaxLayerForClock]
  if {$signal_lo <= 0 || $signal_hi < $signal_lo} { error "OT_PRD_CLOCK_INVENTORY signal range is not initialized" }
  set clock_top 0; set data_top 0; set clocks 0; set data 0; set above 0; set bad {}
  foreach net [$block getNets] {
    set type [$net getSigType]
    if {$type in {POWER GROUND}} continue
    set wire [$net getWire]
    if {$wire eq "" || $wire eq "NULL"} continue
    set top [ot_prd_inventory_wire_top $wire]
    if {$type eq "CLOCK"} {
      incr clocks
      set clock_top [expr {max($clock_top,$top)}]
      if {$top > $signal_hi} { incr above }
    } else {
      incr data
      set data_top [expr {max($data_top,$top)}]
      if {$top > $signal_hi} { lappend bad [list [$net getName] $type $top] }
    }
  }
  # A larger clock resource inventory must not disguise pre-existing data metal
  # outside its unchanged contract. Refuse before changing either range.
  if {[llength $bad]} {
    error "OT_PRD_CLOCK_INVENTORY data above unchanged signal ceiling $signal_hi: [lrange $bad 0 9]"
  }
  set effective_hi [expr {max($signal_hi,$clock_hi)}]
  if {$clock_top > $effective_hi} {
    set min_level [expr {$clock_lo > 0 ? $clock_lo : $signal_lo}]
    set names [dict create]
    foreach layer [[ord::get_db_tech] getLayers] {
      set level [$layer getRoutingLevel]
      if {$level > 0} { dict set names $level [$layer getName] }
    }
    if {![dict exists $names $min_level] || ![dict exists $names $clock_top]} {
      error "OT_PRD_CLOCK_INVENTORY clock range lacks declared technology layers"
    }
    set_routing_layers -clock "[dict get $names $min_level]-[dict get $names $clock_top]"
  }
  if {[$block getMinRoutingLayer] != $signal_lo || [$block getMaxRoutingLayer] != $signal_hi ||
      max($signal_hi,[$block getMaxLayerForClock]) < $clock_top} {
    error "OT_PRD_CLOCK_INVENTORY failed to retain signal range/register clock inventory"
  }
  set registered [$block getMaxLayerForClock]
  puts "OT_PRD_CLOCK_INVENTORY signal $signal_lo-$signal_hi unchanged; clock_max $clock_hi -> $registered; routed_clock_nets $clocks above_signal $above observed_clock_max $clock_top data_max $data_top"
  if {[info exists ::env(RESULTS_DIR)]} {
    set fp [open [file join $::env(RESULTS_DIR) prd_clock_inventory.json] w]
    puts $fp "{\"schema\":\"opentallas.prd_clock_inventory.v1\",\"status\":\"CLOCK_RESOURCE_INVENTORY_REGISTERED\",\"signal_min\":$signal_lo,\"signal_max\":$signal_hi,\"clock_max_before\":$clock_hi,\"clock_max_after\":$registered,\"clock_wire_max\":$clock_top,\"routed_clock_nets\":$clocks,\"clock_nets_above_signal\":$above,\"data_wire_max\":$data_top,\"routed_data_nets\":$data,\"signal_range_unchanged\":true}"
    close $fp
  }
}
ot_prd_clock_inventory

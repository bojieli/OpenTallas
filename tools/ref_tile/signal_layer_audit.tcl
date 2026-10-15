# Audit the ACTUAL final routed OpenDB by net type. A lower signal ceiling
# never lowers the PG ceiling and never exempts clock nets or contact vias.
# The exporter re-runs this on final6_final.odb after any hold ECO.
proc ot_ref_json_layers {counts} {
  set out {}
  foreach layer [lsort [dict keys $counts]] { lappend out "\"$layer\":[dict get $counts $layer]" }
  return "{[join $out ,]}"
}
proc ot_ref_audit_signal_layers {signal_cap pg_cap output} {
  set tech [ord::get_db_tech]
  set sl [$tech findLayer $signal_cap]; set pl [$tech findLayer $pg_cap]
  if {$sl eq "NULL" || $pl eq "NULL"} { error "SIGNAL_LAYER_AUDIT: unknown layer" }
  set sigmax [$sl getRoutingLevel];set pgmax [$pl getRoutingLevel]
  if {$sigmax < 2 || $sigmax > $pgmax} {error "SIGNAL_LAYER_AUDIT: invalid signal/PG contract"}
  set signal [dict create];set power [dict create];set violations [dict create]
  set block [ord::get_db_block]
  foreach net [$block getNets] {
    set pg [expr {[$net getSigType] in {POWER GROUND}}]
    set limit [expr {$pg ? $pgmax : $sigmax}]
    set wire [$net getWire]
    if {$wire ne "NULL"} {
      set dec [odb::dbWireDecoder];$dec begin $wire
      while {[set op [$dec next]] != $odb::dbWireDecoder_END_DECODE} {
        set layers {}
        if {$op == $odb::dbWireDecoder_POINT || $op == $odb::dbWireDecoder_POINT_EXT} {
          lappend layers [$dec getLayer]
        } elseif {$op == $odb::dbWireDecoder_TECH_VIA || $op == $odb::dbWireDecoder_VIA} {
          if {$op == $odb::dbWireDecoder_TECH_VIA} {set via [$dec getTechVia]} else {set via [$dec getVia]}
          foreach box [$via getBoxes] {lappend layers [$box getTechLayer]}
        }
        foreach layer $layers {
          if {$layer eq "NULL" || [$layer getRoutingLevel] <= 0} continue
          set name [$layer getName]
          if {$pg} {dict incr power $name} else {dict incr signal $name}
          if {[$layer getRoutingLevel] > $limit} {dict incr violations "[$net getSigType]:$name"}
        }
      }
    }
    # PG lives primarily in special wires; retain their real layer evidence.
    foreach sw [$net getSWires] {
      foreach box [$sw getWires] {
        set layers {}
        if {[$box isVia]} {
          if {[$box getTechVia] ne "NULL"} {set via [$box getTechVia]} else {set via [$box getBlockVia]}
          foreach vb [$via getBoxes] {lappend layers [$vb getTechLayer]}
        } else {lappend layers [$box getTechLayer]}
        foreach layer $layers {
          if {$layer eq "NULL" || [$layer getRoutingLevel] <= 0} continue
          set name [$layer getName]
          if {$pg} {dict incr power $name} else {dict incr signal $name}
          if {[$layer getRoutingLevel] > $limit} {dict incr violations "[$net getSigType]:$name"}
        }
      }
    }
  }
  foreach term [$block getBTerms] {
    if {[$term getSigType] in {POWER GROUND}} continue
    foreach pin [$term getBPins] {foreach box [$pin getBoxes] {
      set layer [$box getTechLayer]
      if {$layer ne "NULL" && [$layer getRoutingLevel] > $sigmax} {dict incr violations "PIN:[$layer getName]"}
    }}
  }
  set fd [open $output w]
  puts $fd "{\"schema\":\"opentallas.ref_tile.routed-signal-cap.v1\",\"signal_cap\":\"$signal_cap\",\"pg_cap\":\"$pg_cap\",\"non_pg_layers\":[ot_ref_json_layers $signal],\"pg_layers\":[ot_ref_json_layers $power],\"violations\":[ot_ref_json_layers $violations]}"
  close $fd
  puts "SIGNAL_LAYER_AUDIT signal=$signal_cap PG=$pg_cap nonPG=$signal PGmetal=$power violations=$violations"
  if {[dict size $violations]} {error "SIGNAL_LAYER_AUDIT: actual routed metal violates its net-type ceiling"}
}

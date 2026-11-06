# Native final-wire gate for the explicit clock-only M6 resource event.
# Decoder API is shared with clk_freeze.tcl; no wire or timing input is changed.
proc ot_clock_overpass_layer_level {layer} {
  if {$layer eq "" || $layer eq "NULL"} {error "OT_CLOCK_OVERPASS_AUDIT missing native wire layer"}
  set name [$layer getName]
  if {![regexp {^M([0-9]+)$} $name -> level]} {error "OT_CLOCK_OVERPASS_AUDIT unknown routing layer $name"}
  return $level
}
set ot_co_bad {}; set ot_co_clock6 0; set ot_co_routed 0
foreach net [[ord::get_db_block] getNets] {
  set type [$net getSigType]
  if {$type in {POWER GROUND}} continue
  set wire [$net getWire]
  if {$wire eq "" || $wire eq "NULL"} continue
  incr ot_co_routed
  set decoder [odb::dbWireDecoder]; $decoder begin $wire
  set top 0
  while {1} {
    set op [$decoder next]
    if {$op == $odb::dbWireDecoder_END_DECODE} break
    set layers {}
    switch $op {
      0 - 2 - 3 {set layers [list [$decoder getLayer]]}
      6 - 7 {
        set via [expr {$op == 6 ? [$decoder getVia] : [$decoder getTechVia]}]
        if {$via eq "" || $via eq "NULL"} {error "OT_CLOCK_OVERPASS_AUDIT missing native via"}
        set layers [list [$via getBottomLayer] [$via getTopLayer]]
      }
    }
    foreach layer $layers {set top [expr {max($top,[ot_clock_overpass_layer_level $layer])}]}
  }
  $decoder -delete
  if {$type eq "CLOCK" && $top == 6} {incr ot_co_clock6}
  set ceiling [expr {$type eq "CLOCK" ? 6 : 5}]
  if {$top > $ceiling} {dict set ot_co_bad [$net getName] [list $type M$top M$ceiling]}
}
puts "OT_CLOCK_OVERPASS_AUDIT routed $ot_co_routed CLOCK_M6 $ot_co_clock6 bad [dict size $ot_co_bad] (data<=M5, CLOCK<=M6; PG separate)"
if {[dict size $ot_co_bad]} {
  dict for {net detail} $ot_co_bad {puts "OT_CLOCK_OVERPASS_AUDIT BAD $net $detail"}
  write_db /work/clock_overpass_failed.odb
  error "OT_CLOCK_OVERPASS_AUDIT final native wire exceeds its declared clock/data ceiling"
}

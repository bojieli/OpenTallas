# Actual M5 routing corridor around a face pin lifted from M4 to clear a fixed M5 PG pad.
# Keep every neighboring M4 pin's above-layer band; remove only these temporary rectangles after DRT.
set cb [ord::get_db_block]
set dbu [$cb getDbUnitsPerMicron]
set cp [$cb findBTerm $::ot_smpub_corridor_pin]
if {$cp eq "NULL"} { error "SMPUB_CORRIDOR missing pin $::ot_smpub_corridor_pin" }
set die [$cb getDieArea];set ex [$die xMax]
set ph [expr {round($::env(OT_PK_HALO)*$dbu)}]
set half [expr {round($::ot_smpub_corridor_half*$dbu)}]
set cy "";set minx "";set miny "";set maxy ""
foreach bp [$cp getBPins] {foreach bx [$bp getBoxes] {set cy [expr {([$bx yMin]+[$bx yMax])/2}]}}
foreach bt [$cb getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} continue
 foreach bp [$bt getBPins] {foreach bx [$bp getBoxes] {
  if {[[$bx getTechLayer] getName] ne "M4" || [$bx xMax]<$ex} continue
  if {$minx eq ""} {set minx [$bx xMin];set miny [$bx yMin];set maxy [$bx yMax]} else {
   set minx [expr {min($minx,[$bx xMin])}];set miny [expr {min($miny,[$bx yMin])}];set maxy [expr {max($maxy,[$bx yMax])}]
  }
 }}
}
if {$minx eq "" || $cy eq ""} {error "SMPUB_CORRIDOR missing E-face group or pin box"}
set full [list [expr {$minx-$ph}] [expr {$miny-$ph}] $ex [expr {$maxy+$ph}]]
lassign $full x0 y0 x1 y1
set lo [expr {max($y0,$cy-$half)}];set hi [expr {min($y1,$cy+$half)}]
set pieces {}
if {$lo<$hi} {
 if {$lo>$y0} {lappend pieces [list $x0 $y0 $x1 $lo]}
 if {$hi<$y1} {lappend pieces [list $x0 $hi $x1 $y1]}
 set count 0
 foreach ob [$cb getObstructions] {
  set bx [$ob getBBox]
  if {[[$bx getTechLayer] getName] ne "M5"} continue
  set coords [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]
  if {(!$::ot_smpub_corridor_post && $coords eq $full) || ($::ot_smpub_corridor_post && [lsearch -exact $pieces $coords]>=0)} {
   odb::dbObstruction_destroy $ob;incr count
  }
 }
 if {!$::ot_smpub_corridor_post} {
  if {$count!=1} {error "SMPUB_CORRIDOR expected one actual E M5 band, found $count at $full"}
  set ml [[[ord::get_db] getTech] findLayer M5]
  foreach rc $pieces {lassign $rc a b c d;odb::dbObstruction_create $cb $ml $a $b $c $d}
 }
 puts "SMPUB_CORRIDOR pin=$::ot_smpub_corridor_pin post=$::ot_smpub_corridor_post removed=$count corridor_y=$lo,$hi pieces=$pieces"
} else {puts "SMPUB_CORRIDOR pin=$::ot_smpub_corridor_pin no band intersects lifted M5 pin"}

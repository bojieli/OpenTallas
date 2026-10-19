set b [ord::get_db_block]
set die [$b getDieArea];set u [$b getDbUnitsPerMicron]
set byface [dict create N {} S {} W {} E {}]
set count 0;set shapes {}
foreach net [$b getNets] {
 if {[$net getSigType] ni {POWER GROUND}} continue
 foreach sw [$net getSWires] {
  foreach sb [$sw getWires] {
   set lname *
   if {![$sb isVia] && [$sb getTechLayer] ne "NULL"} {set lname [[$sb getTechLayer] getName]}
   lappend shapes [list $lname [$sb xMin] [$sb yMin] [$sb xMax] [$sb yMax]]
  }
 }
}
foreach bt [$b getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} continue
 if {[llength [$bt getBPins]]!=1} {error "PIN_AUDIT missing/multiple pin [$bt getName]"}
 set boxes [[lindex [$bt getBPins] 0] getBoxes]
 if {[llength $boxes]!=1} {error "PIN_AUDIT nonrect pin"}
 set box [lindex $boxes 0];set layer [[$box getTechLayer] getName]
 set x0 [$box xMin];set y0 [$box yMin];set x1 [$box xMax];set y1 [$box yMax]
 if {$x0==[$die xMin]} {set face W;set v [expr {($y0+$y1)/2.0}]} elseif {$x1==[$die xMax]} {set face E;set v [expr {($y0+$y1)/2.0}]} elseif {$y0==[$die yMin]} {set face S;set v [expr {($x0+$x1)/2.0}]} elseif {$y1==[$die yMax]} {set face N;set v [expr {($x0+$x1)/2.0}]} else {error "PIN_AUDIT interior pin [$bt getName]"}
 dict lappend byface $face $v
 foreach shape $shapes {
  lassign $shape pl px0 py0 px1 py1
  if {$pl ne "*" && $pl ne $layer} continue
  if {$x0<$px1 && $x1>$px0 && $y0<$py1 && $y1>$py0} {error "PIN_AUDIT PG/via overlap [$bt getName]"}
 }
 incr count
}
foreach {face coords} $byface {
 set coords [lsort -real $coords];set gap Inf
 foreach a [lrange $coords 0 end-1] c [lrange $coords 1 end] {set g [expr {($c-$a)/double($u)}];if {$g<$gap} {set gap $g}}
 if {$gap<0.192-0.000001} {error "PIN_AUDIT pitch below0.192 on $face: $gap"}
 puts "PIN_AUDIT face=$face count=[llength $coords] min_pitch_um=$gap"
}
if {$count!=3668} {error "PIN_AUDIT scalar coverage$count !=3668"}
puts "PIN_AUDIT PASS actual_scalar_pins=$count PG_and_via_bbox_overlap=0 actual_pitch_ge0.192=PASS"

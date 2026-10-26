# Source-bound requested geometry is snapped only to the ACTUAL database grid.
# No timing exceptions or admission bypasses. PG validation runs after pdngen.
namespace eval hbm_assigned_pins {
 proc die {} {
  set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set d [$b getDieArea]
  lassign $::hbm_geometry_requested_outline w h
  if {abs([$d dx]-round($w*$u))>1 || abs([$d dy]-round($h*$u))>1} {error "HBM_PIN_AUDIT actual outline differs from assigned outline"}
  return [list $b $u $d]
 }
 proc snap {b l pos axis} {
  set g [$b findTrackGrid $l]
  if {$g eq "NULL"} {error "HBM_PIN_AUDIT missing actual track grid"}
  set best {};set delta Inf;set half 0
  set count [$g getNumGridPatterns$axis]
  for {set k 0} {$k<$count} {incr k} {
   lassign [$g getGridPattern$axis $k] start n pitch
   if {$n<=0 || $pitch<=0} continue
   set ix [expr {max(0,min($n-1,round(double($pos-$start)/$pitch)))}]
   set candidate [expr {$start+$ix*$pitch}];set diff [expr {abs($pos-$candidate)}]
   if {$diff<$delta} {set best $candidate;set delta $diff;set half [expr {$pitch/2.0}]}
  }
  if {$best eq "" || $delta>$half+1} {error "HBM_PIN_AUDIT no actual track within half pitch"}
  return $best
 }
 proc place {} {
  lassign [die] b u d;set tech [ord::get_db_tech]
  foreach req $::hbm_geometry_pin_requests {
   lassign $req name face layer x y
   set l [$tech findLayer $layer];if {$l eq "NULL"} {error "HBM_PIN_AUDIT missing requested layer"}
   if {[$l getDirection] eq "VERTICAL"} {set x [expr {[snap $b $l [expr {round($x*$u)}] X]/double($u)}]} else {set y [expr {[snap $b $l [expr {round($y*$u)}] Y]/double($u)}]}
   place_pin -pin_name $name -layer $layer -location [list $x $y] -force_to_die_boundary
  }
 }
 proc intersects {a b spacing} {
  lassign $a ax0 ay0 ax1 ay1;lassign $b bx0 by0 bx1 by1
  expr {min($ax1+$spacing,$bx1)>max($ax0-$spacing,$bx0) && min($ay1+$spacing,$by1)>max($ay0-$spacing,$by0)}
 }
 proc audit_pg {} {
  lassign [die] b u d;set tech [ord::get_db_tech];set pg {};set wires 0
  foreach net [$b getNets] {
   if {[$net getSigType] ni {POWER GROUND}} continue
   foreach sw [$net getSWires] {foreach box [$sw getWires] {
    incr wires
    if {[$box isVia]} {
     lassign [$box getViaXY] vx vy;set via [$box getTechVia];if {$via eq "NULL"} {set via [$box getBlockVia]}
     foreach metal [$via getBoxes] {
      set l [$metal getTechLayer];if {$l eq "NULL" || [$l getRoutingLevel]<=0} continue
      dict lappend pg [$l getName] [list [expr {[$metal xMin]+$vx}] [expr {[$metal yMin]+$vy}] [expr {[$metal xMax]+$vx}] [expr {[$metal yMax]+$vy}]]
     }
    } else {
     set l [$box getTechLayer];dict lappend pg [$l getName] [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
    }
   }}
  }
  if {$wires==0} {error "HBM_PIN_AUDIT requires actual generated PG before CTS"}
  set output [open $::env(RESULTS_DIR)/hbm_pin_pg_readback.tsv w]
  puts $output "port\tface\tlayer\trequested_x_um\trequested_y_um\tactual_x_um\tactual_y_um\tPG_clear"
  set count 0;set signals {}
  foreach req $::hbm_geometry_pin_requests {
   lassign $req name face layer rx ry;set bt [$b findBTerm $name]
   if {$bt eq "NULL"} {error "HBM_PIN_AUDIT missing requested port $name"}
   set boxes {};foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend boxes $box}}
   if {[llength $boxes]!=1} {error "HBM_PIN_AUDIT expected one actual pin rectangle for $name"}
   set box [lindex $boxes 0];set l [$box getTechLayer]
   if {[$l getName] ne $layer} {error "HBM_PIN_AUDIT wrong actual layer $name"}
   set x [expr {([$box xMin]+[$box xMax])/2.0}];set y [expr {([$box yMin]+[$box yMax])/2.0}]
   set preferred [expr {[$l getDirection] eq "VERTICAL"}]
   set target [expr {round(($preferred?$rx:$ry)*$u)}];set actual [expr {$preferred?$x:$y}]
   set grid [snap $b $l $target [expr {$preferred?"X":"Y"}]]
   if {abs($actual-$grid)>1} {error "HBM_PIN_AUDIT actual pin not on assigned nearest track: $name"}
   set onface [expr {$face eq "W"?abs([$box xMin]-[$d xMin]):$face eq "E"?abs([$box xMax]-[$d xMax]):$face eq "N"?abs([$box yMax]-[$d yMax]):abs([$box yMin]-[$d yMin])}]
   if {$onface>1} {error "HBM_PIN_AUDIT actual pin on wrong face: $name"}
   set rect [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
   if {[dict exists $pg $layer]} {foreach pr [dict get $pg $layer] {if {[intersects $rect $pr [$l getSpacing]]} {error "HBM_PIN_AUDIT signal/PG clearance conflict $name"}}}
   foreach ob [$b getObstructions] {
    set obox [$ob getBBox];set ol [$obox getTechLayer]
    if {[$ol getRoutingLevel] != [$l getRoutingLevel]+1} continue
    if {[intersects $rect [list [$obox xMin] [$obox yMin] [$obox xMax] [$obox yMax]] 0]} {error "HBM_PIN_AUDIT above-pin obstruction $name"}
   }
   foreach prev $signals {lassign $prev pl pr pn;if {$pl eq $layer && [intersects $rect $pr [$l getSpacing]]} {error "HBM_PIN_AUDIT signal pin clearance conflict $name/$pn"}}
   lappend signals [list $layer $rect $name]
   puts $output "$name\t$face\t$layer\t$rx\t$ry\t[expr {$x/$u}]\t[expr {$y/$u}]\tPASS"
   incr count
  }
  close $output
  set actualcount 0;foreach bt [$b getBTerms] {if {[$bt getSigType] ni {POWER GROUND}} {incr actualcount}}
  if {$actualcount!=$count} {error "HBM_PIN_AUDIT requested/actual signal coverage mismatch"}
  puts "HBM_PIN_AUDIT PASS pins=$count actual_PG_shapes=$wires tracks_and_faces=actual_readback"
 }
}

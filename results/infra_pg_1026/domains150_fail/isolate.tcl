set ot_phy_boxes {
 {0.000000 207.360000 777.600000 984.960000}
}
set ot_pg_gap 0.144

proc ot_intersect {a b} {
 lassign $a x0 y0 x1 y1;lassign $b u0 v0 u1 v1
 set r [list [expr {max($x0,$u0)}] [expr {max($y0,$v0)}] [expr {min($x1,$u1)}] [expr {min($y1,$v1)}]]
 lassign $r a b c d;if {$a >= $c || $b >= $d} {return {}};return $r
}
proc ot_subtract {a b} {
 if {![llength [ot_intersect $a $b]]} {return [list $a]}
 lassign $a x0 y0 x1 y1;lassign $b u0 v0 u1 v1
 set out {};set aa [expr {max($x0,$u0)}];set cc [expr {min($x1,$u1)}]
 foreach r [list [list $x0 $y0 [expr {min($x1,$u0)}] $y1] [list [expr {max($x0,$u1)}] $y0 $x1 $y1] [list $aa $y0 $cc [expr {min($y1,$v0)}]] [list $aa [expr {max($y0,$v1)}] $cc $y1]] {
  lassign $r a b c d;if {$a < $c && $b < $d} {lappend out $r}
 };return $out
}
set ot_iso_block [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set outer {};set inner {}
foreach r $ot_phy_boxes {
 lassign $r a b c d
 lappend outer [list [expr {round(($a-$ot_pg_gap)*$dbu)}] [expr {round(($b-$ot_pg_gap)*$dbu)}] [expr {round(($c+$ot_pg_gap)*$dbu)}] [expr {round(($d+$ot_pg_gap)*$dbu)}]]
 lappend inner [list [expr {round(($a+$ot_pg_gap)*$dbu)}] [expr {round(($b+$ot_pg_gap)*$dbu)}] [expr {round(($c-$ot_pg_gap)*$dbu)}] [expr {round(($d-$ot_pg_gap)*$dbu)}]]
}
set clipped 0
foreach netname {VDD VDDPHY} {
 set net [$ot_iso_block findNet $netname]
 foreach sw [$net getSWires] {
  foreach s [$sw getWires] {
   set r [list [$s xMin] [$s yMin] [$s xMax] [$s yMax]];set rs {}
   if {$netname eq "VDDPHY"} {
    foreach q $inner {set rr [ot_intersect $r $q];if {[llength $rr]} {lappend rs $rr}}
   } else {
    set rs [list $r]
    foreach q $outer {set out {};foreach rr $rs {set out [concat $out [ot_subtract $rr $q]]};set rs $out}
   }
   if {[llength $rs] == 1 && [lindex $rs 0] eq $r} continue
   if {[$s isVia]} {
    # A via is retained only if its entire metal enclosure stays in its supply region.
    odb::dbSBox_destroy $s;incr clipped;continue
   }
   set layer [$s getTechLayer]
   foreach rr $rs {lassign $rr a b c d;if {$c-$a >= .04*$dbu && $d-$b >= .04*$dbu} {odb::dbSBox_create $sw $layer $a $b $c $d STRIPE}}
   odb::dbSBox_destroy $s;incr clipped
  }
 }
}
puts "OT_PG_POWER_ISOLATION_CLIPPED $clipped"


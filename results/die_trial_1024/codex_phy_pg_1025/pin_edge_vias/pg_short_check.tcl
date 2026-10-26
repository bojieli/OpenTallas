set pg_shapes {}
foreach netname {VDD VDDPHY VSS} {
  set boxes {}
  foreach wire [[[ord::get_db_block] findNet $netname] getSWires] {
    foreach s [$wire getWires] {
      if {[$s isVia]} continue
      set layer [[$s getTechLayer] getName]
      if {$layer ni {M8 M9}} continue
      lappend boxes [list $layer [$s xMin] [$s yMin] [$s xMax] [$s yMax]]
    }
  }
  dict set pg_shapes $netname $boxes
}
set bad 0
foreach pair {{VDD VDDPHY} {VDD VSS} {VDDPHY VSS}} {
  lassign $pair na nb
  foreach a [dict get $pg_shapes $na] {
    lassign $a la ax0 ay0 ax1 ay1
    foreach b [dict get $pg_shapes $nb] {
      lassign $b lb bx0 by0 bx1 by1
      if {$la ne $lb} continue
      if {max($ax0,$bx0) <= min($ax1,$bx1) && max($ay0,$by0) <= min($ay1,$by1)} {
        incr bad
        if {$bad<=10} {puts "OT_PG_SHORT $na $a VS $nb $b"}
      }
    }
  }
}
puts "OT_PG_SHORT_COUNT $bad"
if {$bad} { error "cross-supply M8/M9 metal overlap ($bad)" }

# pg_rail_check.tcl (PG-RAIL-CHECK-1, FABLE-FIX-S81-SERDES2 2026-11-17): after PDN every std-cell row has its two followpin rails.
# Class: serdes__t13 passed every kit gate with 2108 rows (about 16k cells, 56 flops) that had no VDD/VSS M1/M2 rail at all: the rows
# beside the PHY supply region overlapped the region, so pdngen gave them no CORE followpins.  Nothing in the flow looked.
# Check (POST_PDN, design in memory; or standalone with ODB set): for every dbRow, on its lower and its upper edge there must be a
# PG special-wire rail on the lowest routing layer that covers the row span (gaps <= OT_PG_RAIL_CHECK_GAP_UM, default 0.6), one edge
# POWER and the other GROUND, and each of the two rails must carry at least one PG via with a top layer above the rail's own via
# pair inside the row span (the stack up to a strap).  Prints one OT_PG_RAIL_CHECK line with counts and the first failing rows.
# OT_PG_RAIL_CHECK_FAIL=1: a bad row raises an error (FAIL).  =0: advisory, the line says ADVISORY_FAIL and the kit goes on (R-MINIMAL:
# blocking only where the generator sets it, i.e. kits with a PHY supply region).  Either way pg_rail_check.json records the verdict.
# OT_PG_RAIL_CHECK=0 turns the check off.
namespace eval prc {}
proc prc::env {n d} { if {[info exists ::env($n)] && $::env($n) ne ""} { return $::env($n) }; return $d }
# does the sorted interval list cover [a, b] with no gap larger than g ?
proc prc::covers {ivs a b g} {
  set pos $a
  foreach iv [lsort -integer -index 0 $ivs] { lassign $iv lo hi
    if {$hi <= $pos} continue
    if {$lo - $pos > $g} { return 0 }
    set pos $hi; if {$pos >= $b} { return 1 } }
  return [expr {$b - $pos <= $g}]
}
proc prc::run {} {
  if {[prc::env OT_PG_RAIL_CHECK 1] eq "0"} { puts "OT_PG_RAIL_CHECK off"; return }
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]; set dbu [$blk getDbUnitsPerMicron]
  set gap [expr {int(round([prc::env OT_PG_RAIL_CHECK_GAP_UM 0.6] * $dbu))}]
  set L1 [$tech findRoutingLayer 1]; set l1 [$L1 getName]
  # rails by y centre: rail(y) = list of {x0 x1 type}; stack vias by y centre: via(y) = list of {x0 x1}
  foreach net [$blk getNets] {
    if {![$net isSpecial]} continue
    set st [$net getSigType]; if {$st ne "POWER" && $st ne "GROUND"} continue
    foreach sw [$net getSWires] { foreach sb [$sw getWires] {
      set yc [expr {([$sb yMin] + [$sb yMax]) / 2}]
      if {[$sb isVia]} {
        set o [$sb getTechVia]; if {$o eq "NULL"} { set o [$sb getBlockVia] }; if {$o eq "NULL"} continue
        if {[catch {[$o getBottomLayer] getRoutingLevel} lv] || $lv < 2} continue
        lappend via($st,$yc) [list [$sb xMin] [$sb xMax]]
      } elseif {[[$sb getTechLayer] getName] eq $l1 && ([$sb xMax] - [$sb xMin]) > ([$sb yMax] - [$sb yMin])} {
        lappend rail($st,$yc) [list [$sb xMin] [$sb xMax]]
      } } }
  }
  set n 0; set norail 0; set nostack 0; set samepol 0; set bad {}
  foreach r [$blk getRows] {
    set b [$r getBBox]; set x0 [$b xMin]; set x1 [$b xMax]; if {$x1 <= $x0} continue
    incr n; set got {}; set why ""
    foreach y [list [$b yMin] [$b yMax]] {
      set t ""
      foreach st {POWER GROUND} { if {[info exists rail($st,$y)] && [prc::covers $rail($st,$y) $x0 $x1 $gap]} { set t $st } }
      if {$t eq ""} { set why norail; break }
      set ok 0
      if {[info exists via($t,$y)]} { foreach v $via($t,$y) { lassign $v a c; if {$c > $x0 && $a < $x1} { set ok 1; break } } }
      if {!$ok} { set why nostack; break }
      lappend got $t
    }
    if {$why eq "" && [lindex $got 0] eq [lindex $got 1]} { set why samepol }
    if {$why eq ""} continue
    incr $why
    if {[llength $bad] < 5} { lappend bad [format "%s(%s %.3f..%.3f y %.3f)" [$r getName] $why [expr {$x0/double($dbu)}] [expr {$x1/double($dbu)}] [expr {[$b yMin]/double($dbu)}]] }
  }
  set nbad [expr {$norail + $nostack + $samepol}]
  set blocking [expr {[prc::env OT_PG_RAIL_CHECK_FAIL 1] ne "0"}]
  set verdict [expr {!$nbad ? "PASS" : ($blocking ? "FAIL" : "ADVISORY_FAIL")}]
  puts "OT_PG_RAIL_CHECK rows $n bad $nbad (no rail $norail, rail without stack via $nostack, both edges same polarity $samepol) $verdict $bad"
  # one record per kit for the failure census (advisory kits keep building; R-MINIMAL: not a blocking gate there)
  if {![catch {open [prc::env OT_PG_RAIL_CHECK_JSON /work/pg_rail_check.json] w} fh]} {
    puts $fh "{\"schema\": \"opentallas.pg_rail_check.v1\", \"rows\": $n, \"bad\": $nbad, \"no_rail\": $norail, \"no_stack_via\": $nostack, \"same_polarity\": $samepol, \"blocking\": $blocking, \"verdict\": \"$verdict\"}"
    close $fh
  }
  if {$nbad && $blocking} { error "OT_PG_RAIL_CHECK FAIL: $nbad of $n rows without connected VDD/VSS rails" }
}
if {[info exists ::env(OT_PG_RAIL_CHECK_ODB)]} { read_db $::env(OT_PG_RAIL_CHECK_ODB) }
if {![info exists ::env(OT_PG_RAIL_CHECK_NO_RUN)]} { prc::run }

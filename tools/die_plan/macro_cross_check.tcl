# MACRO-CROSS (QC-CB-GEN-1115, FABLE-PD-QC-1115 L3, 11-15): advisory placement check.  Counts 2-pin signal nets longer than
# ::ot_mcross_min_um (300) whose straight L-route bounding box passes over the interior of a hard macro (a net like the cbn_q11
# t22 t_out pipe hop: BUFx16 at x 80 -> BUFx16 at x 546 across a 463 um tile on rows with zero horizontal capacity).  Target 0.
# Reads only; never changes the design and never fails.  Log (one line + up to 5 worst):
#   OT_MACRO_CROSS nets N (2-pin, > X um, over a macro; target 0) worst W um over <macro>
uplevel #0 {
proc mc_main {} {
  set blk [ord::get_db_block]
  set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set min [expr {round(([info exists ::ot_mcross_min_um] ? $::ot_mcross_min_um : 300.0) * $dbu)}]
  set e [expr {round(2.0 * $dbu)}]
  set mac {}
  foreach i [$blk getInsts] { if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend mac [list [$i getName] [expr {[$b xMin]+$e}] [expr {[$b yMin]+$e}] [expr {[$b xMax]-$e}] [expr {[$b yMax]-$e}]] } }
  if {![llength $mac]} { puts "OT_MACRO_CROSS nets 0 (no macros)"; return }
  set n 0; set worst 0; set wm ""; set rows {}
  foreach net [$blk getNets] {
    if {[$net getSigType] ne "SIGNAL"} continue
    set its [$net getITerms]
    if {[llength $its] != 2 || [llength [$net getBTerms]] != 0} continue
    set pts {}
    foreach it $its { set ii [$it getInst]; if {[[$ii getMaster] isBlock]} { set bb [$it getBBox] } else { set bb [$ii getBBox] }; if {$bb eq "NULL"} { set pts {}; break }; lappend pts [list [expr {([$bb xMin]+[$bb xMax])/2}] [expr {([$bb yMin]+[$bb yMax])/2}]] }
    if {[llength $pts] != 2} continue
    lassign [lindex $pts 0] x1 y1; lassign [lindex $pts 1] x2 y2
    set len [expr {abs($x1-$x2)+abs($y1-$y2)}]
    if {$len <= $min} continue
    set xl [expr {min($x1,$x2)}]; set xh [expr {max($x1,$x2)}]; set yl [expr {min($y1,$y2)}]; set yh [expr {max($y1,$y2)}]
    foreach m $mac {
      lassign $m nm a b c d
      # the net's horizontal / vertical leg (either L orientation) passes over the macro interior: the leg is longer than the reach
      set hx [expr {min($xh,$c) - max($xl,$a)}]; set hy [expr {min($yh,$d) - max($yl,$b)}]
      if {$hx > 0 && $hy > 0 && ($hx > $min || $hy > $min)} { incr n; if {$len > $worst} { set worst $len; set wm $nm }; if {[llength $rows] < 5} { lappend rows "[$net getName] [format %.0f [expr {$len/double($dbu)}]]um over $nm" }; break }
    }
  }
  puts "OT_MACRO_CROSS nets $n (2-pin, > [format %.0f [expr {$min/double($dbu)}]] um, over a macro; target 0) worst [format %.0f [expr {$worst/double($dbu)}]] um over $wm"
  foreach r $rows { puts "OT_MACRO_CROSS NET $r" }
}
mc_main
}

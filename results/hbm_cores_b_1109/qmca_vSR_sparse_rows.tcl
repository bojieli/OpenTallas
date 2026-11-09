# sparse_rows.tcl -- HBM-CORES-B 2026-11-09, q_mca conservative form "rows only where cells sit" (PRE_TAPCELL_TCL).
# WHY (measured, q_mca a2 epyc5): the type holds 1,680 logic cells (reset relay tree + hop latches, 326.5 um2) on a
# 4898.88 x 2073.6 um outline; floorplan made full rows and tapcell inserted 749,700 tapcells + 15,296 endcaps, so
# 766,772 instances, and DRT pin access peaked at 75.4 GB and died (Error 247).  The logic is FIRM-placed by
# reset_tree.tcl at known sites.  Same idea as tools/qwen_split/die_tie_rows.tcl (QC die r8: rows only around die-top
# cells): keep row segments only (a) in a band of +-OT_SR_HALF_Y um around every firm site, OT_SR_HALF_X um either side
# in x, and (b) around every placed block pin (+-OT_SR_HALF_X, +-2 x OT_SR_HALF_Y), optional edge ring OT_SR_EDGE um (default 0 = off).  Every kept
# segment is a normal row on the original site grid, so tapcell, PDN followpins, placement and fill work unchanged
# there.  RTL, pins, outline, layers and the reset tree are unchanged.
set sr_half_y [expr {[info exists ::env(OT_SR_HALF_Y)] ? $::env(OT_SR_HALF_Y) : 10.8}]
set sr_half_x [expr {[info exists ::env(OT_SR_HALF_X)] ? $::env(OT_SR_HALF_X) : 60.0}]
set sr_edge   [expr {[info exists ::env(OT_SR_EDGE)]   ? $::env(OT_SR_EDGE)   : 0.0}]
set sr_src    [expr {[info exists ::env(OT_SR_SITES)]  ? $::env(OT_SR_SITES)  : "/work/rtl/reset_tree.tcl"}]

set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set core [$block getCoreArea]
set cx0 [$core xMin]; set cy0 [$core yMin]; set cx1 [$core xMax]; set cy1 [$core yMax]

# boxes in dbu: {x0 y0 x1 y1}
set boxes {}
set nsite 0
set fh [open $sr_src r]
while {[gets $fh line] >= 0} {
  if {[regexp {^\s*rtr_place(_opt|_lk)?\s+(\S+)\s+\{[^\}]*\}\s+([0-9.]+)\s+([0-9.]+)\s} $line -> _ key x y]} {
    incr nsite
    lappend boxes [list [expr {round(($x - $sr_half_x) * $dbu)}] [expr {round(($y - $sr_half_y) * $dbu)}] \
                        [expr {round(($x + $sr_half_x) * $dbu)}] [expr {round(($y + $sr_half_y) * $dbu)}]]
  }
}
close $fh
if {$nsite == 0} { error "OT_SPARSE_ROWS: no firm sites read from $sr_src" }
# every placed block pin (q_mca: 78 of 82 are internal clock-tap / reset pins on the relay lines)
set npin 0
foreach bt [$block getBTerms] {
  set bb [$bt getBBox]
  if {[$bb xMax] <= [$bb xMin] && [$bb yMax] <= [$bb yMin]} continue
  if {[$bb xMin] == 0 && [$bb yMin] == 0 && [$bb xMax] == 0} continue
  incr npin
  set px [expr {([$bb xMin] + [$bb xMax]) / 2}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2}]
  lappend boxes [list [expr {$px - round($sr_half_x * $dbu)}] [expr {$py - round(2 * $sr_half_y * $dbu)}]                       [expr {$px + round($sr_half_x * $dbu)}] [expr {$py + round(2 * $sr_half_y * $dbu)}]]
}
puts "OT_SPARSE_ROWS: $npin placed pins boxed"
set e [expr {round($sr_edge * $dbu)}]
if {$e > 0} {
lappend boxes [list $cx0 $cy0 $cx1 [expr {$cy0 + $e}]] [list $cx0 [expr {$cy1 - $e}] $cx1 $cy1] \
              [list $cx0 $cy0 [expr {$cx0 + $e}] $cy1] [list [expr {$cx1 - $e}] $cy0 $cx1 $cy1]
}

set n_old 0; set n_new 0; set sites_old 0; set sites_new 0
foreach row [$block getRows] {
  incr n_old
  set site [$row getSite]; set sw [$site getWidth]; set sh [$site getHeight]
  set orient [$row getOrient]; set name [$row getName]
  set bb [$row getBBox]
  set rx0 [$bb xMin]; set ry0 [$bb yMin]; set rx1 [$bb xMax]; set ry1 [$bb yMax]
  incr sites_old [$row getSiteCount]
  # intervals of this row covered by boxes
  set iv {}
  foreach b $boxes {
    lassign $b bx0 by0 bx1 by1
    if {$by1 <= $ry0 || $by0 >= $ry1} continue
    set a [expr {max($bx0, $rx0)}]; set z [expr {min($bx1, $rx1)}]
    if {$z <= $a} continue
    # snap to the row's site grid
    set a [expr {$rx0 + (($a - $rx0) / $sw) * $sw}]
    set z [expr {$rx0 + (($z - $rx0 + $sw - 1) / $sw) * $sw}]
    if {$z > $rx1} { set z $rx1 }
    lappend iv [list $a $z]
  }
  odb::dbRow_destroy $row
  if {![llength $iv]} continue
  set iv [lsort -integer -index 0 $iv]
  set merged {}
  foreach p $iv {
    if {[llength $merged] && [lindex $p 0] <= [lindex $merged end 1]} {
      lset merged end 1 [expr {max([lindex $merged end 1], [lindex $p 1])}]
    } else { lappend merged $p }
  }
  set k 0
  foreach p $merged {
    lassign $p a z
    set cnt [expr {($z - $a) / $sw}]
    if {$cnt < 8} continue
    odb::dbRow_create $block "${name}_sr$k" $site $a $ry0 $orient "HORIZONTAL" $cnt $sw
    incr k; incr n_new; incr sites_new $cnt
  }
}
puts "OT_SPARSE_ROWS: firm sites $nsite (from $sr_src), half_y $sr_half_y half_x $sr_half_x edge $sr_edge um: rows $n_old -> segments $n_new, sites $sites_old -> $sites_new ([format %.2f [expr {100.0 * $sites_new / max(1, $sites_old)}]] %)"

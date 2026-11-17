# phy_region_rows.tcl (PHY-REGION-ROWS-1, FABLE-FIX-S81-SERDES2 11-17): no core row overlaps a PHY supply region.
# Class: the rows beside the region were cut by the macro halo only (x 317.25 on serdes__t13) while the region starts at 314.928, and
# the rows just under the PHY macros ran through it; pdngen gives a row that overlaps another voltage domain region no CORE followpin
# rails: 2046 of 6664 rows (about 16k cells, 56 flops) had no VDD/VSS rail and nothing in the flow looked.
# Form (PRE_TAPCELL, before tap / endcap insertion): every row that overlaps a region rect is replaced by its pieces left and right of
# the rect, on the row site grid; a piece narrower than OT_PHY_REGION_ROWS_MIN_SITES (default 20) is dropped.  Rects: prr_rects (um).
set prr_b [ord::get_db_block]; set prr_dbu [$prr_b getDbUnitsPerMicron]
set prr_min [expr {[info exists ::env(OT_PHY_REGION_ROWS_MIN_SITES)] ? $::env(OT_PHY_REGION_ROWS_MIN_SITES) : 20}]
set prr_cut 0; set prr_new 0
foreach prr_r $prr_rects {
  lassign $prr_r a b c d
  set X0 [expr {round($a*$prr_dbu)}]; set Y0 [expr {round($b*$prr_dbu)}]; set X1 [expr {round($c*$prr_dbu)}]; set Y1 [expr {round($d*$prr_dbu)}]
  foreach row [$prr_b getRows] {
    set bb [$row getBBox]
    if {[$bb xMin] >= $X1 || [$bb xMax] <= $X0 || [$bb yMin] >= $Y1 || [$bb yMax] <= $Y0} continue
    set site [$row getSite]; set w [$site getWidth]; lassign [$row getOrigin] ox oy
    set nm [$row getName]; set ori [$row getOrient]; set dir [$row getDirection]; set sp [$row getSpacing]; set ns [$row getSiteCount]
    set k1 [expr {($X0 - $ox) / $w}]; if {$k1 > $ns} { set k1 $ns }
    set k2 [expr {($X1 - $ox + $w - 1) / $w}]
    odb::dbRow_destroy $row; incr prr_cut
    if {$k1 >= $prr_min} { odb::dbRow_create $prr_b ${nm}_rw $site $ox $oy $ori $dir $k1 $sp; incr prr_new }
    if {$ns - $k2 >= $prr_min} { odb::dbRow_create $prr_b ${nm}_re $site [expr {$ox + $k2 * $w}] $oy $ori $dir [expr {$ns - $k2}] $sp; incr prr_new }
  }
}
puts "OT_PHY_REGION_ROWS [llength $prr_rects] region(s): $prr_cut overlapping rows replaced by $prr_new pieces outside the region"

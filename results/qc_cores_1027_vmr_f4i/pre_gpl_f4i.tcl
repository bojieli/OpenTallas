# QC-CORES-2 F4I PRE_GLOBAL_PLACE: the unchanged MIF0 hook (pushdown fixes the plan clock-node / ft cells), then the PG
# stripe-pair M3 escape-gap keep-out bands (pa_bands_f4i.tcl = band x list from pa_bands.py on the floorplan PDN), each cut
# in y around every std cell that STAYS fixed through DPL (LOCKED boundary/well tapcells at macro edges; FIRM plan clock / island
# cells ot_ms_* / ot_isl*): those sites are taken by plan cells anyway, and DPL check_placement rejects a fixed cell under a
# blockage (F4I try 1: 1106 tap + 3 ot_ms_TR*_nd).  Face / macro-pin flops (FIRM now, released to PLACED before DPL by
# face_flops_release / macro_pin_flops_release) are NOT cut around, so DPL legalises them out of the bands (try 2: 997 left in cuts).
source /work/pre_gpl_m0.tcl
source /work/pa_bands_f4i.tcl
set ot_pab_blk [ord::get_db_block]
set ot_pab_fix {}
foreach i [$ot_pab_blk getInsts] {
  if {[[$i getMaster] isBlock]} continue
  set ps [$i getPlacementStatus]; set nm [$i getName]
  if {!($ps eq "LOCKED" || $ps eq "COVER" || ($ps eq "FIRM" && ([string match ot_ms_* $nm] || [string match ot_isl* $nm])))} continue
  set bb [$i getBBox]; lappend ot_pab_fix [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
}
set ot_pab_n 0; set ot_pab_cut 0
foreach band $ot_pab_bands {
  lassign $band x0 x1 y0 y1
  set ys {}
  foreach f $ot_pab_fix { lassign $f fx0 fy0 fx1 fy1; if {$fx1 > $x0 && $fx0 < $x1} { lappend ys [list $fy0 $fy1] } }
  set ys [lsort -integer -index 0 $ys]; set cur $y0
  foreach s $ys {
    lassign $s a b
    if {$a > $cur} { odb::dbBlockage_create $ot_pab_blk $x0 $cur $x1 $a; incr ot_pab_n }
    if {$b > $cur} { set cur $b }; incr ot_pab_cut
  }
  if {$cur < $y1} { odb::dbBlockage_create $ot_pab_blk $x0 $cur $x1 $y1; incr ot_pab_n }
}
puts "F4I_PA_BANDS [llength $ot_pab_bands] bands -> $ot_pab_n hard placement blockages, $ot_pab_cut fixed-cell cuts ([llength $ot_pab_fix] std cells fixed through DPL)"

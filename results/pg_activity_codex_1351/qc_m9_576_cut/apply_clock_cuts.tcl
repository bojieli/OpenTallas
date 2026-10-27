# Exact R28 net_holes translated to canonical2972.16um interior window. Whole stripes only.
set ot_cut_count 0
set ot_cut_vias 0
set ot_cut_net [[ord::get_db_block] findNet VSS]
set ot_cut_del {}
set ot_cut_rects {
{M8 0.0 25.68 2972.16 26.16}
{M8 0.0 172.56 2972.16 173.04}
{M8 0.0 319.44 2972.16 319.92}
{M8 0.0 457.68 2972.16 458.16}
{M8 0.0 803.28 2972.16 803.76}
{M8 0.0 941.52 2972.16 942.0}
{M8 0.0 1088.4 2972.16 1088.88}
{M8 0.0 1235.28 2972.16 1235.76}
{M8 0.0 1408.08 2972.16 1408.56}
{M8 0.0 1554.96 2972.16 1555.44}
{M8 0.0 1701.84 2972.16 1702.32}
{M8 0.0 1840.08 2972.16 1840.56}
{M8 0.0 1986.96 2972.16 1987.44}
{M8 0.0 2133.84 2972.16 2134.32}
{M8 0.0 2272.08 2972.16 2272.56}
{M8 0.0 2418.96 2972.16 2419.44}
{M8 0.0 2565.84 2972.16 2566.32}
{M8 0.0 2738.64 2972.16 2739.12}
{M8 0.0 2885.52 2972.16 2886.0}
{M9 535.392 0.0 535.968 2972.16}
{M9 1157.472 0.0 1158.048 2972.16}
{M9 1770.912 0.0 1771.488 2972.16}
{M9 2401.632 0.0 2402.208 2972.16}
}
foreach sw [$ot_cut_net getSWires] {
 foreach sb [$sw getWires] {
  set rm 0
  foreach cut $ot_cut_rects {
   lassign $cut ly x0 y0 x1 y1
   set hx0 [expr {round($x0*$dbu)}];set hy0 [expr {round($y0*$dbu)}];set hx1 [expr {round($x1*$dbu)}];set hy1 [expr {round($y1*$dbu)}]
   if {[$sb xMin] >= $hx1 || [$sb xMax] <= $hx0 || [$sb yMin] >= $hy1 || [$sb yMax] <= $hy0} {continue}
   if {[$sb isVia]} {set rm 1} elseif {[[$sb getTechLayer] getName] eq $ly} {set rm 1}
  }
  if {$rm} {lappend ot_cut_del $sb}
 }
}
foreach sb $ot_cut_del {if {[$sb isVia]} {incr ot_cut_vias} else {incr ot_cut_count};odb::dbSBox_destroy $sb}
puts "OT_QC_CUT stripes=$ot_cut_count vias=$ot_cut_vias"
if {$ot_cut_count==0} {error "Exact R28 cuts removed zero stripes"}

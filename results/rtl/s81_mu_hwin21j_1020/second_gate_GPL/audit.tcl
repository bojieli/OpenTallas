read_db /work/3_3_place_gp-failed.odb
source /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /out/bbox_violations.tsv w]
set count 0;set worst 0
foreach row [$b getRows] {puts "SITE width=[[$row getSite] getWidth] height=[[$row getSite] getHeight] dbu=$u";break}
dict for {owner box} $::ot_hj_boxes {
 lassign $box x0 y0 x1 y1
 foreach i [[$b findGroup ot_hj_$owner] getInsts] {
  set bb [$i getBBox]
  set delta [expr {max(round($x0*$u)-[$bb xMin],round($y0*$u)-[$bb yMin],[$bb xMax]-round($x1*$u),[$bb yMax]-round($y1*$u))}]
  if {$delta>0} {
   incr count;set worst [expr {max($worst,$delta)}]
   puts $f "$owner\t[$i getName]\t[[$i getMaster] getName]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]\t$delta"
  }
 }
}
close $f
puts "HWIN_GPL_BBOX_AUDIT outside=$count worst_dbu=$worst dbu_per_um=$u"

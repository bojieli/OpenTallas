read_db /data/routes/gate/work/orfs/results/asap7/opentallas_ot_s81_hc_ctfx_reset_native_asap7_ref_gate/base/3_3_place_gp-failed.odb
set b [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /data/cell_density.tsv w]
puts $f "#dbu_per_um\t$u"
foreach i [$b getInsts] {
 set m [$i getMaster];set bb [$i getBBox]
 puts $f "[$i getName]\t[$m getName]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]\t[$i getPlacementStatus]"
}
close $f
set f [open /data/row_density.tsv w]
foreach row [$b getRows] {set bb [$row getBBox];puts $f "[$row getName]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]"}
close $f

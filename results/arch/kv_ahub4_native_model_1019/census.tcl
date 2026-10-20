read_db /native/routes/gate/work/orfs/results/asap7/opentallas_qkd_ahub_static_dw_g2_lp_asap7_ref_gate/base/4_1_cts.odb
set b [ord::get_db_block]
set f [open /out/native_cells.tsv w]
puts $f "name\tmaster\tx0\ty0\tx1\ty1\tstatus"
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach i [$b getInsts] {
 set r [$i getBBox]
 puts $f "[$i getName]\t[[$i getMaster] getName]\t[expr {[$r xMin]/double($dbu)}]\t[expr {[$r yMin]/double($dbu)}]\t[expr {[$r xMax]/double($dbu)}]\t[expr {[$r yMax]/double($dbu)}]\t[$i getPlacementStatus]"
}
close $f
puts "AHUB_NATIVE_CELLS [llength [$b getInsts]]"

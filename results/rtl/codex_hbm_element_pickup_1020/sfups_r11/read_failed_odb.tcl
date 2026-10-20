read_db /old/routes/gate/work/orfs/results/asap7/opentallas_ot_hgi_sfu_programme_store_r11_asap7_ref_gate/base/3_3_place_gp-failed.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set f [open /out/r11_cl_fixed.tsv w]
puts $f "kind\tname\tmaster\tstatus\tx0\ty0\tx1\ty1"
set n 0
foreach i [$b getInsts] {
 set m [$i getMaster]
 set st [$i getPlacementStatus]
 if {![$m isBlock] && $st ne "FIRM" && ![$i isFixed]} {continue}
 set bb [$i getBBox]
 set kind [expr {[$m isBlock]?"macro":"std"}]
 puts $f "$kind\t[$i getName]\t[$m getName]\t$st\t[expr {[$bb xMin]/double($u)}]\t[expr {[$bb yMin]/double($u)}]\t[expr {[$bb xMax]/double($u)}]\t[expr {[$bb yMax]/double($u)}]"
 incr n
}
close $f
puts "SFUPS_FIXED_DUMP count=$n dbu=$u"

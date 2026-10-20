set ::env(RESULTS_DIR) /work
read_db /work/3_3_place_gp-failed.odb
source /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl
ot_hj_fences_install
set births [ot_hj_assign_births 1]
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /out/post_gpl_birth_area.tsv w]
dict for {owner box} $::ot_hj_boxes {
 set area 0.0;set group [$b findGroup ot_hj_$owner]
 foreach i [$group getInsts] {set m [$i getMaster];set area [expr {$area+double([$m getWidth])*[$m getHeight]/$u/$u}]}
 lassign $box x0 y0 x1 y1;puts $f "$owner\t[llength [$group getInsts]]\t$area\t[expr {$area/(($x1-$x0)*($y1-$y0))}]"
}
close $f
::ot_hj_detailed_placement_orig
write_db /out/post_gpl_native_dp.odb
ot_hj_fences_check POST_GPL_NATIVE_DP
check_placement -verbose
puts "HWIN_POST_GPL_NATIVE_DP_PASS"

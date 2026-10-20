set ::env(RESULTS_DIR) /work
read_db /work/3_3_place_gp-failed.odb
source /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl
ot_hj_fences_install
ot_hj_assign_births 0
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /out/group_area.tsv w];set total 0.0
foreach i [$b getInsts] {
 set m [$i getMaster]
 if {[$m isBlock] || [regexp {TAPCELL|FILL|DECAP|ENDCAP|tapcell} [$m getName]]} {continue}
 if {[$i getGroup] eq "NULL"} {error "HWIN_STAGE unassigned functionalcell [$i getName]"}
 set total [expr {$total+double([$m getWidth])*[$m getHeight]/$u/$u}]
}
dict for {owner box} $::ot_hj_boxes {
 set g [$b findGroup ot_hj_$owner];set area 0.0
 foreach i [$g getInsts] {set m [$i getMaster];set area [expr {$area+double([$m getWidth])*[$m getHeight]/$u/$u}]}
 lassign $box x0 y0 x1 y1;set density [expr {$area/(($x1-$x0)*($y1-$y0))}]
 puts $f "$owner\t[llength [$g getInsts]]\t$area\t$density"
 if {$density>0.60} {error "HWIN_STAGE group density $owner $density"}
}
close $f
set legal 0.0
foreach r [$b getRows] {set bb [$r getBBox];set legal [expr {$legal+double([$bb xMax]-[$bb xMin])*([$bb yMax]-[$bb yMin])/$u/$u}]}
set density [expr {$total/$legal}]
if {$density<.40 || $density>.60} {error "HWIN_STAGE legalrow density $density"}
puts "HWIN_STAGE_AREA_PASS std_area=$total legal_row_area=$legal density=$density"
write_db /out/stage_assigned.odb

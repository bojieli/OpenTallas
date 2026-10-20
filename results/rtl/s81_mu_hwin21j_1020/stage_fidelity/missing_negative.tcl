set ::env(RESULTS_DIR) /work
read_db /work/3_3_place_gp-failed.odb
source /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl
set b [ord::get_db_block];set selected NULL
foreach i [$b getInsts] {
 set master [[$i getMaster] getName]
 if {($::env(NEG_KIND) eq "ff" && [regexp {^DFF} $master]) || ($::env(NEG_KIND) eq "comb" && [regexp {^AND} $master])} {set selected $i;break}
}
if {$selected eq "NULL"} {error "HWIN_MISSING_NEG no candidate"}
set name [$selected getName]
odb::dbInst_destroy $selected
set rc [catch {ot_hj_fences_install} message]
if {!$rc || ![string match {HWIN_NATIVE missing mapped cell*} $message]} {error "HWIN_MISSING_NEG expectedmissing $::env(NEG_KIND) got $rc/$message"}
foreach group [dict keys $::ot_hj_boxes] {if {[$b findGroup ot_hj_$group] ne "NULL"} {error "HWIN_MISSING_NEG partial mutation $group"}}
puts "HWIN_MISSING_NEG_PASS kind=$::env(NEG_KIND) removed=$name rejected=$message no_group_mutation"

set original [lindex [glob /work/results/asap7/*/base/3_4_place_resized.odb] 0]
read_db $original
set ::env(RESULTS_DIR) [file dirname $original]
set kit [lindex [glob /src/physical/ref_tile/qfd_tile_n*_rp2_45_a2/pre_dpl.tcl] 0]
# Each invocation receives the actual kit path; no selection fallback.
source $::env(R5_KIT_PRE_DPL)
set_placement_padding -global -left 0 -right 0
proc record_cells {stage} {
 set b [ord::get_db_block]
 set f [open /out/viol_names.txt r];set out [open /out/${stage}_cells.tsv w]
 while {[gets $f n] >= 0} {set i [$b findInst [string trim $n]];if {$i eq "NULL"} continue;set r [$i getBBox];set g [$i getGroup];if {$g ne "NULL"} {set g [$g getName]};puts $out "[$i getName]\t[$r xMin]\t[$r yMin]\t$g"}
 close $f;close $out
}
puts "R5_SEQUENCE_INITIAL_ORDINARY_DPL"
detailed_placement
check_placement -verbose
write_db /out/before_dpo.odb
record_cells before_dpo
puts "R5_SEQUENCE_BEFORE_DPO_CHECK_PASS"
improve_placement -max_displacement {5 1}
optimize_mirroring
write_db /out/after_dpo.odb
record_cells after_dpo
set rc [catch {check_placement -verbose} msg]
puts "R5_SEQUENCE_AFTER_DPO_CHECK_RC=$rc $msg"
puts "OT_FINAL_DPL: ordinary legalization after final optimizer/mirroring"
detailed_placement
check_placement -verbose
write_db /out/canonical_final.odb
record_cells canonical_final
puts "R5_SEQUENCE_CANONICAL_FINAL_CHECK_PASS"
exit

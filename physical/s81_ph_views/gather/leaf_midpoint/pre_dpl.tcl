source /src/physical/dsrom_window_source/leaf_inhold_release.tcl
source /src/physical/qwen_die_masters/out_flop_release.tcl
# Every forwarding FF was already assigned a legal native site/row satisfying
# both actual D/Q windows. Keep those bounded legal sites through DPL.
set mp_block [ord::get_db_block]
set mp_file [open $::env(RESULTS_DIR)/s81_midpoint_used_cells.txt r]
while {[gets $mp_file mp_name]>=0} {
  set mp_inst [$mp_block findInst $mp_name]
  if {$mp_inst eq "NULL"} {error "S81_DQ_SITE lost used forwarding FF $mp_name"}
  $mp_inst setPlacementStatus FIRM
}
close $mp_file

# PRE_DETAIL_PLACE hook (el1011-q-seq 2026-10-12): release the pin flops (out_flop_release.tcl) and the FIRM input /
# output hold stages of ctlm_hold_stages.tcl to PLACED so detailed_placement legalises them next to their pins.
source /src/physical/qwen_die_masters/out_flop_release.tcl
set hr_blk [ord::get_db_block]
set hr_f $::env(RESULTS_DIR)/ot_hold_stage_firm.txt
set hr_n 0
if {[file exists $hr_f]} {
  set fh [open $hr_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$hr_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr hr_n
  }
  close $fh
}
puts "HOLDSTAGE released $hr_n FIRM hold-stage cells for DPL"

# Existing CTS checkpoint; data-only existing hold pad, no CTS rerun.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_cts.odb 4_cts.sdc
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
estimate_parasitics -placement
# This is CTS placement RC, with a separate output directory. The shared helper
# infers GRT only from a 4_1_cts file in RESULTS_DIR; no such file belongs here.
set old_results $::env(RESULTS_DIR)
set ::env(RESULTS_DIR) /work/cts_input_pad
file mkdir $::env(RESULTS_DIR)
set ::ot_mm_stage 3_place.sdc
ot_mm_sync
# Freeze the actual CTS ancestors by placement status, retain exact connectivity.
set saved {}
foreach c [get_fanin -flat -to [all_registers -clock_pins] -only_cells] {
  set inst [sta::sta_to_db_inst $c]
  if {$inst eq "" || $inst eq "NULL"} {continue}
  lappend saved [list $inst [$inst getPlacementStatus] [$inst getLocation] [[$inst getMaster] getName]]
  $inst setPlacementStatus FIRM
}
puts "HNX_CLOCK_FREEZE [llength $saved] original clock ancestors"
puts "HNX_PAD_BEFORE [ot_hold_stats]"
ot_io_hold_pad
foreach rec $saved {
  lassign $rec inst status xy master
  if {[$inst getLocation] ne $xy || [[$inst getMaster] getName] ne $master} {error "HNX input-data pad moved or resized existing clock ancestor"}
  $inst setPlacementStatus $status
}
puts "HNX_PAD_AFTER [ot_hold_stats]"
ot_mm_unsync
write_db /work/cts_input_pad/4_cts.odb
write_sdc -no_timestamp /work/cts_input_pad/4_cts.sdc
puts "HNX_INPUT_PAD_CHECKPOINT_DONE"

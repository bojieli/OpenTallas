source /src/physical/dsrom_window_source/leaf_inhold_release.tcl
source /src/physical/qwen_die_masters/out_flop_release.tcl
# Release the functional FF-local drivers/converters for normal legalization.
set fd_file [open $::env(RESULTS_DIR)/s81_forward_drive_firm.txt r]
while {[gets $fd_file fd_name]>=0} {
 set fd_inst [[ord::get_db_block] findInst $fd_name]
 if {$fd_inst ne "NULL"} {$fd_inst setPlacementStatus PLACED}
}
close $fd_file
# Re-evaluate actual D/Q centers after GPL/resizing, before DPL and CTS.
# Reserve only legal FIRM row/site positions; reset buffering stays repairable.
source /src/physical/s81_ph_views/gather/leaf_midpoint/anchor.tcl
set ::env(S81_FORWARD_DRIVE_MOVABLE) 1
source /src/physical/s81_ph_views/gather/leaf_midpoint/forward_drive.tcl

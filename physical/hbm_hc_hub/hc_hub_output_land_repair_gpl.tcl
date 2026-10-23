# Keep physical landing buffers at face pins, with ordinary sizing / wire repair.
# c9 MAIN / fallback failed RSZ-3006 because an inserted buffer's A load was dont_touch.
# These are non-stateful physical buffers; clear only their cell / output-net protection.
# FIRM placement still excludes them from the compact GPL band. All normal checks remain.
source /src/physical/common_flow/out_pin_driver.tcl
set ol_b [ord::get_db_block]
set ol_cells 0
set ol_nets 0
foreach ol_i [$ol_b getInsts] {
    if {[string match "ot_outdrv_*" [$ol_i getName]]} {
        $ol_i setDoNotTouch 0
        incr ol_cells
    }
}
foreach ol_n [$ol_b getNets] {
    if {[string match "ot_outdrv_p*" [$ol_n getName]]} {
        $ol_n setDoNotTouch 0
        incr ol_nets
    }
}
puts "HC_OUTPUT_LANDING repairable cells=$ol_cells output_nets=$ol_nets; FIRM pin placement retained"
source /src/physical/hbm_hc_hub/hc_hub_band_native_gpl.tcl

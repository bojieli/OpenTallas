# Load the retained exact constrained state. No make stage/prior-stage dependency.
proc log_cmd {args} {uplevel 1 $args}
set ::env(OT_MM_SETUP_CORNER) tc
set ::env(OT_HOLD_MM) 1
set ::env(OT_MM_FF_SDC) /work/vclk_ff.sdc
set ::env(OT_MM_MEASURED_HOLD) 1
set ::env(RESULTS_DIR) /work/run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base
set fh [open /work/selected_library_receipt.json];set raw [read $fh];close $fh
# Exact TT/FF paths, not inferred corner substitutions.
set lists [exec python3 -c {import json;d=json.load(open('/work/selected_library_receipt.json'));print(' '.join('{'+x+'}'for x in d['TT']));print(' '.join('{'+x+'}'for x in d['FF']))}]
lassign [split $lists \n] ::env(TC_LIB_FILES) ::env(BC_LIB_FILES)
source /work/orfs_hold_mm.tcl
ot_mm_read_libs
read_db /work/snapshot/5_1_grt.odb
ot_mm_read_sdc /work/snapshot/4_cts.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
source /work/apply_candidate.tcl

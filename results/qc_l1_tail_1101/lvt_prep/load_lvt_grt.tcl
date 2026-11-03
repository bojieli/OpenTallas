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
lappend ::env(TC_LIB_FILES) /work/asap7sc7p5t_SIMPLE_LVT_TT_nldm_211120.lib.gz
lappend ::env(BC_LIB_FILES) /work/asap7sc7p5t_SIMPLE_LVT_FF_nldm_211120.lib.gz
ot_mm_read_libs
read_db /work/input.odb
read_lef /work/asap7sc7p5t_28_L_1x_220121a.lef
ot_mm_read_sdc /work/snapshot/4_cts.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
source /work/apply_lvt_grt.tcl

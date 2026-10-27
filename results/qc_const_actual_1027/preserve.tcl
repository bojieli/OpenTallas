yosys read_rtlil /work/front/upstream2.il
set ::env(RESULTS_DIR) /work/front
set ::env(OT_CONST_DFF_SPEC) /work/capture_spec.json
source /work/tools/ot_const_dff_keep.tcl
yosys write_rtlil /work/front/preserved_before_synth.il
yosys synth -top qfd_qc_su_lane_w_l0
yosys write_json /work/front/preserved_synth.json
yosys write_verilog -noattr /work/front/preserved_synth.v
yosys stat

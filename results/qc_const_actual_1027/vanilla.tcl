yosys read_rtlil /work/front/upstream2.il
yosys synth -top qfd_qc_su_lane_w_l0
yosys write_json /work/front/vanilla_synth.json
yosys write_verilog -noattr /work/front/vanilla_synth.v
yosys stat

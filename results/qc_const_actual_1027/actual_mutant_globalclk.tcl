yosys read_json /work/front/vanilla_synth.json
yosys rename qfd_qc_su_lane_w_l0 gold
yosys design -stash goldstash
yosys read_json /work/front/mutant_synth.json
yosys rename qfd_qc_su_lane_w_l0 gate
yosys read_verilog -overwrite /work/ff_model.v
yosys proc
yosys flatten gate
yosys opt_expr
yosys opt_dff
yosys opt_clean
yosys design -copy-from goldstash -as gold gold
yosys clk2fflogic
yosys opt_clean
yosys equiv_make gold gate miter
yosys hierarchy -top miter
yosys equiv_simple
yosys equiv_induct -undef -seq 5
yosys equiv_status -assert

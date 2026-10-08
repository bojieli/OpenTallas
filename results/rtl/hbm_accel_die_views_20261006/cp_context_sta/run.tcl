set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
define_corners ss ff
read_liberty -corner ss $P/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty -corner ff $P/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty -corner ss /work/ot_hbm_integrated_su_cp_context_ss.lib
read_liberty -corner ff /work/ot_hbm_integrated_su_cp_context_ff.lib
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/ot_hbm_integrated_su_cp_context.lef
read_verilog /work/cpctx.v
link_design cpctx
set_cmd_units -time ns -capacitance fF
create_clock -name c_cp -period 0.833333 [get_ports clk_cp]
create_clock -name c_nb -period 0.833333 [get_ports clk_nb]
set_propagated_clock [all_clocks]
set_load 6.0 [get_nets w_*]
foreach skew {0.150 0.050 0.0 -0.050 -0.150} {
  set_clock_latency -source $skew [get_clocks c_nb]
  set_clock_uncertainty -setup 0.060 [all_clocks]
  set_clock_uncertainty -hold 0.025 [all_clocks]
  puts "OT_CP skew_nb=$skew"
  report_worst_slack -max -digits 3
  report_worst_slack -min -digits 3
}

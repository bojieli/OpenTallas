read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNH2V2X_RVT_FF_nldm_FAKE.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNV2X_RVT_FF_nldm_FAKE.lib
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /work/results/asap7/scr_ot_dsrom_s81_wl_screen/base/1_2_yosys.v
link_design ot_dsrom_s81_wl_screen
create_clock -name clk -period 833 [get_ports clk]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [all_inputs]
set_false_path -to [all_outputs]
puts "OTC hold [sta::worst_slack_cmd min]"
report_checks -path_delay min -digits 1 > /work/ff_worst.rpt

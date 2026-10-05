read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNH2V2X_RVT_FF_nldm_FAKE.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNV2X_RVT_FF_nldm_FAKE.lib
read_verilog /work/results/asap7/dsrom_baseline_clock1/base/6_final.v
link_design ot_dsrom_link_rt_clock_core
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
read_spef /work/results/asap7/dsrom_baseline_clock1/base/6_final.spef
report_checks -path_delay min -digits 3
puts "WNS [sta::worst_slack_cmd min]"

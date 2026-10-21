read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_FF_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_hgi_sm_xload_cl2_bdring_asap7_ref_hgi_sm_xl2_bdring_cl2d_COMMIT_b0d45974d/base/6_final.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_ot_hgi_sm_xload_cl2_bdring_asap7_ref_hgi_sm_xl2_bdring_cl2d_COMMIT_b0d45974d/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hgi_sm_xload_cl2_bdring_asap7_ref_hgi_sm_xl2_bdring_cl2d_COMMIT_b0d45974d/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/hgi_sm_xl2_bdring/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc

report_checks -to [get_ports {bq_d[420]}] -path_delay max -fields {slew cap fanout input_pin nets} -format full_clock_expanded -digits 3
report_checks -to [get_ports {bq_d[420]}] -path_delay min -fields {slew cap fanout input_pin nets} -format full_clock_expanded -digits 3
set b [ord::get_db_block]
foreach n {\bq_d[420]$_DFF_P_ _135173_ wire22480 wire22481} { set i [$b findInst $n]; if {$i != "NULL"} {puts "INSTANCE $n [$i getMaster] [$i getLocation]"} }
exit

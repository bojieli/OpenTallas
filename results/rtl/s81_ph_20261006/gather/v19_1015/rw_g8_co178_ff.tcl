read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_128x66_m1_r2c2.lef
read_lef /mv1/ot_sram_1r1w_256x34_m2_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_128x66_m1_r2c2_ff.lib
read_liberty /mv1/ot_sram_1r1w_256x34_m2_r2c2_ff.lib
read_db /work/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_dsfd_gth_rw_v19_g8_996350cb8/base/6_final.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_dsfd_gth_rw_v19_g8_996350cb8/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_dsfd_gth_rw_v19_g8_996350cb8/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/dsfd_gth_rw_v19/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
report_checks -to [get_ports {co[178]}] -path_delay min -format full_clock_expanded -digits 4 -group_path_count 1
set b [ord::get_db_block];set ff [$b findInst ot_prs_00083_ff]
puts "CO178_FF_POS [$ff getLocation]"
set clock [[$ff findITerm CLK] getNet]
puts "CO178_CLOCK [$clock getName]"
foreach it [$clock getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {set drv [$it getInst];puts "CO178_CLKDRV [$drv getName] [$drv getLocation]";foreach t [$drv getITerms] {if {[$t getNet] ne "NULL"} {puts "CO178_DRIVER_PIN [[$t getMTerm] getName] [[$t getNet] getName]"}}}}
exit

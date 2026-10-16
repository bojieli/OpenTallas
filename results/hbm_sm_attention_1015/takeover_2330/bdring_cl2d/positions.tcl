read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_TT_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_hgi_sm_xload_cl2_bdring_asap7_ref_hgi_sm_xl2_bdring_cl2d_COMMIT_b0d45974d/base/6_final.odb
set ::ot_ce_corner tt
read_sdc /work/results/asap7/opentallas_ot_hgi_sm_xload_cl2_bdring_asap7_ref_hgi_sm_xl2_bdring_cl2d_COMMIT_b0d45974d/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hgi_sm_xload_cl2_bdring_asap7_ref_hgi_sm_xl2_bdring_cl2d_COMMIT_b0d45974d/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/hgi_sm_xl2_bdring/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc

set b [ord::get_db_block]
foreach n {{bq_d[420]$_DFF_P_} {bq_d[419]$_DFF_P_} _135173_ wire22480 wire22481 wire22416 wire22415 ot_ohdrv_01404_0 ot_outhold_01404_1 ot_ohdrv_01404_2 output1405} {
 set i [$b findInst $n]; if {$i ne "NULL"} {puts "INSTPOS $n [[$i getMaster] getName] [$i getLocation] [$i getPlacementStatus]"}
}
foreach n {{bq_d[420]} {bq_d[419]}} {set bt [$b findBTerm $n];foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {puts "PINPOS $n [$box xMin] [$box yMin] [$box xMax] [$box yMax]"}}}
exit

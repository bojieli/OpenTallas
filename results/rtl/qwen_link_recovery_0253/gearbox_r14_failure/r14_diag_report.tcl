read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_qfd_ucie_six_five_asap7_ref_gate/base/4_1_cts.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_qfd_ucie_six_five_asap7_ref_gate/base/4_cts.sdc
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/qfd_ucie_gearbox_r10/signoff.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
puts {DIAGNOSTIC ONLY: frozen r14 CTS, repair disabled, not a closure verdict}
report_checks -path_delay min -to [get_pins {padbad$_DFF_PN0_/D}] -group_path_count 5 -format full_clock_expanded
report_checks -path_delay max -to [get_pins {padbad$_DFF_PN0_/D}] -group_path_count 5 -format full_clock_expanded
exit

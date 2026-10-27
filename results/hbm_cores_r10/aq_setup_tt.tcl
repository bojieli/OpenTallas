set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach l {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib} { read_liberty $L/$l }
read_db /work/run/results/asap7/hbc_ot_hbm_xp_aq_tree13_fmt/base/5_1_grt.odb
read_sdc /work/run/results/asap7/hbc_ot_hbm_xp_aq_tree13_fmt/base/5_1_grt.sdc
set_propagated_clock [get_clocks clk]
source /work/vclk_corner.tcl
ot_vclk_bind tt
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
report_checks -path_delay max -format full_clock_expanded -digits 2; report_checks -path_delay max -group_path_count 5 -format end
array set n {rr 0 in 0 out 0}

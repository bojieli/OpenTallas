set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach l {asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib} { read_liberty $L/$l }
read_db /work/run/results/asap7/hbc_ot_hbm_xp_aq_tree13_fmt/base/5_1_grt.odb
read_sdc /work/run/results/asap7/hbc_ot_hbm_xp_aq_tree13_fmt/base/5_1_grt.sdc
set_propagated_clock [get_clocks clk]
source /work/vclk_corner.tcl
ot_vclk_bind ff
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
report_checks -path_delay min -to [get_pins {u_bin_x/q[109]$_DFF_P_/D}] -format full_clock_expanded -fields {fanout cap slew} -digits 2
report_checks -path_delay min -group_path_count 3 -format end
array set n {rr 0 in 0 out 0}
foreach p [find_timing_paths -path_delay min -group_path_count 20000 -endpoint_path_count 1 -slack_max 0] {
 if {[get_property [get_property $p startpoint] is_port]} {incr n(in)} elseif {[get_property [get_property $p endpoint] is_port]} {incr n(out)} else {incr n(rr)} }
puts "VIOL rr $n(rr) in $n(in) out $n(out)"

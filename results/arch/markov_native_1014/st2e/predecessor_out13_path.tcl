read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_s81_markov_ctl_static_asap7_ref_s81_markov_ctl_static_st1_b314866a0/base/6_final.odb
set ::ot_ce_corner ss
read_sdc /work/results/asap7/opentallas_ot_s81_markov_ctl_static_asap7_ref_s81_markov_ctl_static_st1_b314866a0/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_s81_markov_ctl_static_asap7_ref_s81_markov_ctl_static_st1_b314866a0/base/6_final.spef
set_propagated_clock [all_clocks]
report_checks -to [get_ports {out_bits[13]}] -path_delay max -format full_clock_expanded -fields {slew cap fanout input net} -digits 4
set b [ord::get_db_block]
set bt [$b findBTerm {out_bits[13]}]
set n [$bt getNet]
for {set k 0} {$k < 10} {incr k} {
 foreach i [$n getITerms] {if {[$i isOutputSignal]} {set c [$i getInst];puts "CHAIN [$c getName] [[$c getMaster] getName] [$c getLocation]";set a [$c findITerm A];if {$a ne "NULL"} {set n [$a getNet]} else {set k 10};break}}
}
exit

read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_dsfd_xstg_515_asap7_ref_s81net_xstg_515_n3_61a4164c1/base/6_final.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_dsfd_xstg_515_asap7_ref_s81net_xstg_515_n3_61a4164c1/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_xstg_515_asap7_ref_s81net_xstg_515_n3_61a4164c1/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
# Diagnostic correction: use the existing explicit wclk insertion-reference clock.
unset_input_delay -clock [get_clocks vw] [get_ports {i*}]
set_input_delay 166.667 -clock [get_clocks ot_lb_v_wclk] [get_ports {i*}]
set_input_delay -min 0 -clock [get_clocks ot_lb_v_wclk] [get_ports {i*}]
read_sdc /cl/io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"

set f [open /diag/input_min_corrected.tsv w]
puts $f "port\tendpoint\tslack_ps"
set ni 0;set np 0;set missing 0
foreach ip [get_ports {i*}] {
 incr ni
 set ps [find_timing_paths -path_delay min -from $ip -to [all_registers -data_pins] -group_path_count 1000000 -endpoint_path_count 1]
 if {![llength $ps]} {incr missing;puts $f "[get_full_name $ip]\tNONE\tNONE"}
 foreach p $ps {
  incr np
  puts $f "[get_full_name $ip]\t[get_full_name [get_property $p endpoint]]\t[get_property $p slack]"
 }
}
close $f
puts "XSTG_MIN_INPUTS $ni PATHS $np MISSING $missing"
report_checks -path_delay min -from [get_ports {i*}] -to [all_registers -data_pins] -group_path_count 3 -format full_clock_expanded
exit

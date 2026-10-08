
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_dsfd_capt_x_asap7_s81ph_s81ph_dsfd_capt_x_6fe9f807d/base/6_final.odb
read_sdc /work/results/asap7/opentallas_dsfd_capt_x_asap7_s81ph_s81ph_dsfd_capt_x_6fe9f807d/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_capt_x_asap7_s81ph_s81ph_dsfd_capt_x_6fe9f807d/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/s81_ph_views/common/signoff_unc60.sdc
set count 0
foreach p [get_pins -hierarchical */D] {
 set name [get_full_name $p]
 if {[string first "w_st_r" $name] >= 0 || [string first "r_st_w" $name] >= 0} {
 incr count
 puts "STARTUP_ENDPOINT $name"
 report_checks -to $p -path_delay max -group_path_count 1 -format full_clock_expanded -fields {slew cap input_pin fanout}
 }
}
puts "STARTUP_COUNT $count"
exit

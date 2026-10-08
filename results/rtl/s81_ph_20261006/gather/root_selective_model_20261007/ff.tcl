
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_s81ph_root_tile_asap7_s81ph_s81ph_root_tile_77bcb3f3c/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_s81ph_root_tile_asap7_s81ph_s81ph_root_tile_77bcb3f3c/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_s81ph_root_tile_asap7_s81ph_s81ph_root_tile_77bcb3f3c/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/s81_ph_views/common/signoff_unc60.sdc
set_thread_count 1
puts "ROOT_ORIGINAL_WS [sta::worst_slack_cmd min]"
set targets {}
set f [open /case/targets.txt w]
foreach pin [get_pins -hierarchical */D] {
 set s [get_property $pin slack_min]
 if {$s ne "INF" && $s < 15} {set n [get_full_name $pin]; lappend targets $n; puts $f $n; puts "ROOT_LOW endpoint=$n slack=$s"}
}
close $f
puts "ROOT_TARGET_COUNT [llength $targets]"
foreach pin [get_pins -hierarchical */D] {
 set n [get_full_name $pin]
 if {[lsearch -exact $targets $n] < 0} continue
 foreach edge {rise fall} {
 puts "ROOT_EDGE $n $edge"
 report_checks -path_delay min -${edge}_to $pin -group_path_count 1 -format full_clock_expanded -fields {slew cap input_pin fanout}
 }
}
exit

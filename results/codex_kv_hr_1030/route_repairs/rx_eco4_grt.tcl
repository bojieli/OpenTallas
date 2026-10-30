define_corners tc bc
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz}
read_db /work/eco4/3_place.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_core_rx__259_2x259_2/base/6_final.sdc
foreach c [get_clocks *] {if {[get_property $c period] != 833} {error "non833period"}}
source /work/setRC_rcx.tcl
set ::env(RESULTS_DIR) /work/eco4_grt
source /work/clk_freeze_supported.tcl
ot_clk_freeze
set cknames {};foreach n [ot_clk_dbnets] {dict set cknames [$n getName] 1;$n setSpecial}
set cleared 0
foreach n [[ord::get_db_block] getNets] {
 if {[$n getSigType] in {POWER GROUND CLOCK} || [dict exists $cknames [$n getName]]} continue
 set w [$n getWire];if {$w ne "NULL" && $w ne ""} {odb::dbWire_destroy $w;incr cleared}
}
puts "RX_ECO4_CLEARED_DATA_WIRES $cleared"
set_routing_layers -signal M2-M5
set_global_routing_layer_adjustment M2-M5 0.25
global_route -congestion_iterations 50 -congestion_report_file /work/eco4_grt/congestion.rpt -allow_congestion -verbose
ot_clk_freeze_assert post_rx_eco4_grt
write_db /work/eco4_grt/5_1_grt.odb
write_def /work/eco4_grt/5_1_grt.def
write_guides /work/eco4_grt/route.guide
write_global_route_segments /work/eco4_grt/global_segments.tcl
write_sdc /work/eco4_grt/5_1_grt.sdc
estimate_parasitics -global_routing
ot_clk_restore_parasitics {tc /work/eco4_grt/original_clock_only.spef bc /work/eco4_grt/original_clock_only.spef}
set_propagated_clock [get_clocks clk]
foreach {tag c kind lat} {TT tc max 250.0 FF bc min 202.5} {
 set_clock_latency -source $lat [get_clocks vclk]
 set_output_delay -min 0 -clock [get_clocks vclk] [all_outputs]
 set inputs {};foreach ip [all_inputs] {if {![string match {ck*} [get_full_name $ip]]} {lappend inputs $ip}}
 set_input_delay -min -40 -clock [get_clocks vclk] $inputs
 set paths [find_timing_paths -corner $c -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
 if {![llength $paths]} {error "CDC $tag no path"}
 set worst Inf;foreach path $paths {set worst [expr {min($worst,[get_property $path slack])}]}
 puts "RX_ECO4_GRT $tag worst_slack_ps $worst groups [llength $paths]"
 report_checks -corner $c -path_delay $kind -format full_clock_expanded -digits 3
 report_check_types -corner $c -max_slew -max_capacitance -violators
}
puts RX_ECO4_GRT_DIAGNOSTIC_DONE_NO_DRT_CLOCK_CONTEXT_NOT_QUALIFIED

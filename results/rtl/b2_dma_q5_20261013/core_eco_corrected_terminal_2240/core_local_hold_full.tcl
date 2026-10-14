read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_256x256_m2_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_FF_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_256x256_m2_r2c2_ff.lib
read_db /in/results/asap7/tile/base/6_final.odb
read_sdc /in/results/asap7/tile/base/6_final.sdc
read_spef /in/results/asap7/tile/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/hbm_accel_die_views/common/signoff_unc60.sdc
read_sdc /src/physical/hbm_accel_die_views/common/vclk_corner_true.sdc
read_sdc /src/physical/common_flow/link_budget_consistent.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /cl/io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"

set_thread_count 8
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set original [dict create]
foreach i [$block getInsts] {
 if {[string match FILLER* [[$i getMaster] getName]]} { odb::dbInst_destroy $i; continue }
 dict set original [$i getName] [list {*}[$i getLocation] [$i getOrient] [[$i getMaster] getName]]
 $i setPlacementStatus FIRM
}
set_routing_layers -signal M2-M7 -clock M4-M7
set_global_routing_layer_adjustment M2-M7 0.25
global_route -start_incremental
set target_pins {{u_b1/wd_in[139]} {u_b1/wd_in[182]} {u_b1/wd_in[177]} {u_b1/wd_in[142]} {u_b1/wd_in[174]} {u_b1/wd_in[150]} {u_b1/wd_in[140]} {u_b1/wd_in[178]} {u_b1/wd_in[173]} {u_b1/wd_in[180]} {u_b1/wd_in[145]} {u_b1/wd_in[148]} {u_b1/wd_in[176]} {u_b1/wd_in[183]} {u_b1/wd_in[175]} {u_b1/wd_in[147]} {u_b1/wd_in[159]} {u_b1/wd_in[179]} {u_b1/wd_in[181]} {u_b1/wd_in[152]} {u_b1/wd_in[171]} {u_b1/wd_in[157]}}
set dirty [dict create]
set k 0
foreach pn $target_pins {
 set obj [get_pins -quiet $pn]
 if {[llength $obj] != 1} {error "target missing $pn"}
 set it [$block findITerm $pn]
 set nt [$it getNet]
 dict set dirty [$nt getName] 1
 set driver NULL
 foreach q [$nt getITerms] { if {[$q isOutputSignal]} {set driver [$q getInst]} }
 if {$driver eq "NULL"} {error "driver missing $pn"}
 lassign [$driver getLocation] x y
 set x [expr {double($x)/$dbu}];set y [expr {double($y)/$dbu}]
 insert_buffer -buffer_cell HB1xp67_ASAP7_75t_R -load_pins $obj -location [list $x $y] -buffer_name core_local_hold_$k -net_name core_local_hold_net_$k
 dict set dirty core_local_hold_net_$k 1
 incr k
}
detailed_placement
check_placement -verbose
foreach i [$block getInsts] {
 if {[dict exists $original [$i getName]] && [dict get $original [$i getName]] ne [list {*}[$i getLocation] [$i getOrient] [[$i getMaster] getName]]} { error "original instance moved [$i getName]" }
}
set stripped 0
foreach nt [$block getNets] {
 if {[$nt getSigType] in {POWER GROUND}} continue
 set w [$nt getWire]
 if {$w ne "NULL"} {odb::dbWire_destroy $w;incr stripped}
}
puts "CORE_LOCAL_ECO added $k cells stripped $stripped wires; original cell placements and clock cells preserved; full wire reroute on original guides because frozen-wire DRT produced connectivity/DRC conflicts"
global_route -end_incremental -allow_congestion -resistance_aware
detailed_route -output_drc /work/core_local_hold_full_drc.rpt -verbose 1
filler_placement {FILLERxp5_ASAP7_75t_R FILLER_ASAP7_75t_R FILLERxp5_ASAP7_75t_L FILLER_ASAP7_75t_L}
check_placement -verbose
extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules
write_spef /work/core_local_hold_full.spef
write_db /work/core_local_hold_full.odb
write_verilog /work/core_local_hold_full.v
puts "CORE_LOCAL_ECO_DONE"
exit

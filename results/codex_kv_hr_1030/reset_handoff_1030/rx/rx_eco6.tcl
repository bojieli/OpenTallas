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
read_db /work/eco5_grt/5_1_grt.odb
read_sdc /work/eco5_grt/5_1_grt.sdc
source /work/setRC_rcx.tcl
set ::env(RESULTS_DIR) /work/eco6
source /work/clk_freeze_supported.tcl
foreach n [ot_clk_dbnets] {$n clearSpecial}
ot_clk_freeze
if {![grt::have_routes]} {error "persisted actualroutes missing"}
estimate_parasitics -global_routing
ot_clk_restore_parasitics {tc /work/eco5_grt/original_clock_only.spef bc /work/eco5_grt/original_clock_only.spef}
set_propagated_clock [get_clocks clk]
set_clock_latency -source 250 [get_clocks vclk]
set_output_delay -min 0 -clock [get_clocks vclk] [all_outputs]
set ins {};foreach p [all_inputs] {if {![string match ck* [get_full_name $p]]} {lappend ins $p}}
set_input_delay -min -40 -clock [get_clocks vclk] $ins
set_dont_use [get_lib_cells *DFF*]
# Two master-only localDATA changes on actual−1.862ps path. Samepositivebuffer/AO21function.
resize_cell place9118 BUFx6f_ASAP7_75t_R
resize_cell _091148_ AO21x2_ASAP7_75t_R
detailed_placement -max_displacement {20 4}
check_placement -verbose
ot_clk_freeze_assert post_rx_eco6
write_db /work/eco6/3_place.odb
write_def /work/eco6/3_place.def
write_verilog /work/eco6/3_place.v
foreach {tag c kind lat} {TT tc max 250.0 FF bc min 202.5} {
 set_clock_latency -source $lat [get_clocks vclk]
 set paths [find_timing_paths -corner $c -path_delay $kind -group_path_count 1]
 set worst Inf;foreach path $paths {set worst [expr {min($worst,[get_property $path slack])}]}
 puts "RX_ECO6_MASTER_ONLY_DIAGNOSTIC $tag $worst"
 report_checks -corner $c -path_delay $kind -format full_clock_expanded -digits 3
 report_check_types -corner $c -max_slew -max_capacitance -violators
}
puts RX_ECO6_ROUTE_AWARE_DATA_REPAIR_DONE_NO_GRT_NO_DRT

define_corners tc bc
foreach {c suf} {tc TT bc FF} {foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_${suf}*.lib*] {read_liberty -corner $c $l}}
read_db /work/hb100/3_place.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_phy_pad__86_4x95_04/base/6_final.sdc
source /work/setRC_rcx.tcl
set ::env(RESULTS_DIR) /work/hb100
source /work/clk_freeze.tcl
ot_clk_freeze
foreach n [ot_clk_dbnets] {$n setSpecial}
set_routing_layers -signal M2-M5
set_global_routing_layer_adjustment M2-M5 0.25
global_route -congestion_iterations 50 -congestion_report_file /work/hb100/congestion.rpt -allow_congestion -verbose
ot_clk_freeze_assert post_grt
write_db /work/hb100/5_1_grt.odb
write_guides /work/hb100/route.guide
write_sdc /work/hb100/5_1_grt.sdc
estimate_parasitics -global_routing
foreach c {tc bc} {read_spef -corner $c /work/proto/clock_only.spef}
set_propagated_clock [get_clocks clk]
foreach {tag c kind lat} {TT tc max 250.0 FF bc min 202.5} {
 set_clock_latency -source $lat [get_clocks vclk]
 set paths [find_timing_paths -corner $c -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
 if {![llength $paths]} {error "HB100 $tag no path"}
 set worst Inf
 foreach path $paths {set worst [expr {min($worst,[get_property $path slack])}]}
 puts "PHY_HB100_PROTO $tag worst_slack_ps $worst groups [llength $paths]"
 report_checks -corner $c -path_delay $kind -format full_clock_expanded -digits 3
 report_check_types -corner $c -max_slew -max_capacitance -violators
}
puts PHY_HB100_PROTO_DONE

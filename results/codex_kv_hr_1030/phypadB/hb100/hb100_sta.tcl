define_corners tc bc
foreach {c suf} {tc TT bc FF} {foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_${suf}*.lib*] {read_liberty -corner $c $l}}
read_db /work/hb100/5_1_grt.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_phy_pad__86_4x95_04/base/6_final.sdc
source /work/setRC_rcx.tcl
set ::env(RESULTS_DIR) /work/hb100
source /work/clk_freeze.tcl
ot_clk_freeze
set_routing_layers -signal M2-M5
read_guides /work/hb100/route.guide
estimate_parasitics -global_routing
write_spef /work/hb100/grt_data.spef
foreach c {tc bc} {read_spef -corner $c /work/proto/clock_only.spef}
set_propagated_clock [get_clocks clk]
foreach {tag c kind lat} {TT tc max 250.0 FF bc min 202.5} {
 set_clock_latency -source $lat [get_clocks vclk]
 set_output_delay -min 0 -clock [get_clocks vclk] [all_outputs]
 set inputs {};foreach ip [all_inputs] {if {![string match {ck*} [get_full_name $ip]]} {lappend inputs $ip}}
 set_input_delay -min -40 -clock [get_clocks vclk] $inputs
 set paths [find_timing_paths -corner $c -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
 if {![llength $paths]} {error "HB100 $tag no path"}
 set worst Inf
 foreach path $paths {set worst [expr {min($worst,[get_property $path slack])}]}
 puts "PHY_HB100_PROTO $tag worst_slack_ps $worst groups [llength $paths]"
 report_checks -corner $c -path_delay $kind -format full_clock_expanded -digits 3
 report_check_types -corner $c -max_slew -max_capacitance -violators
}
puts PHY_HB100_PROTO_DONE

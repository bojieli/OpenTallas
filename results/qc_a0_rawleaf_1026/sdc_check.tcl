foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF_nldm*.lib*] { read_liberty $l }
read_db /work/run_ffpg/results/asap7/lsl_rawfault_m3/base/4_cts.odb
read_sdc /work/constraint.sdc
set_propagated_clock [get_clocks core_clk]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set ::env(OT_VCLK_FF) 143.9
source /work/vclk_corner.tcl
ot_vclk_bind ff
puts "SDCCHK hold_viol [sta::endpoint_violation_count min] setup_viol [sta::endpoint_violation_count max]"
report_worst_slack -min -digits 2
foreach p [find_timing_paths -path_delay min -group_path_count 50 -endpoint_path_count 1 -slack_max 0] { puts "EP [format %.2f [get_property $p slack]] [get_full_name [get_property $p startpoint]] -> [get_full_name [get_property $p endpoint]]" }

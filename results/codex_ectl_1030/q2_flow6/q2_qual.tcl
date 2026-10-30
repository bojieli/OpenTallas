foreach l $::env(OT_LIBS) {read_liberty $l}
read_db /work/run/results/asap7/hc_qkd_ectlk_q2__233_28x172_8/base/5_1_grt.odb
read_sdc /work/constraint.sdc
if {$::env(OT_C) eq "FF"} {read_sdc /work/vclk_ff.sdc}
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
# Include the actual clock graph; unlike generic geometry probes, never mark clock nets special.
set b [ord::get_db_block];set ns 0
foreach n [$b getNets] {if {[$n getSigType] eq "CLOCK" && [$n isSpecial] && [$n getWire] eq "NULL"} {incr ns}}
if {$ns} {error "Q2_QUAL $ns unrouted clock nets would be skipped as special"}
set_routing_layers -signal $::env(OT_DMIN)-$::env(OT_DMAX)
set_global_routing_layer_adjustment $::env(OT_DMIN)-$::env(OT_DMAX) $::env(OT_ADJ)
puts "Q2_QUAL_DECK $::env(OT_C) signals $::env(OT_DMIN)-$::env(OT_DMAX) clock_range native_floorplan_inherited adj $::env(OT_ADJ) max_iterations50 includesclock"
global_route -congestion_iterations 50 -congestion_report_file /out/congestion.rpt -allow_congestion -verbose -resistance_aware
write_guides /out/route.guide
estimate_parasitics -global_routing
set w [worst_slack -max];set h [worst_slack -min]
set sv [sta::max_slew_violation_count];set cv [sta::max_capacitance_violation_count]
puts "Q2_QUAL_STA $::env(OT_C) setup $w hold $h slew $sv cap $cv"
report_checks -path_delay min -format full_clock_expanded -group_path_count 1
report_checks -path_delay max -format full_clock_expanded -group_path_count 1
source /deck/clock_family.tcl
set ::env(CORNER) $::env(OT_C)
set ::env(OT_PS_OUT) /out/pair_skew.tsv
source /deck/pair_skew.tcl
puts "Q2_QUAL_DONE $::env(OT_C)"
exit

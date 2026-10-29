# Read-only GRT timing coupon. Stored routes and exact kit RC required; never reroutes.
set C $::env(CORNER)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_[string tolower $C].lib] { read_liberty $f }
set B /work/run/results/asap7/kq_qfd_dv_s8x_btab_turntree/base
read_db $B/5_1_grt.odb
read_sdc $B/5_1_grt.sdc
if {$C eq "FF"} { source /work/vclk_ff.sdc }
source /work/setRC_rcx.tcl
set_routing_layers -signal M2-M5 -clock M2-M5
set_propagated_clock [get_clocks clk]
# Deliberately fatal if no stored route; a measurement never substitutes a new route.
estimate_parasitics -global_routing
report_checks -path_delay max -group_path_count 3 -format full_clock_expanded -fields {slew cap fanout} > /out/${C}_max.rpt
report_checks -path_delay min -group_path_count 3 -format full_clock_expanded -fields {slew cap fanout} > /out/${C}_min.rpt
puts "BTAB_GRT_STA $C setup_ps [expr {[sta::worst_slack_cmd max]*1e12}] setup_bad [sta::endpoint_violation_count max] hold_ps [expr {[sta::worst_slack_cmd min]*1e12}] hold_bad [sta::endpoint_violation_count min]"
report_check_types -max_slew -max_capacitance -max_fanout -violators > /out/${C}_drv.rpt
set f [open /out/${C}_clock_pins.tsv w]
foreach p [all_registers -clock_pins] { puts $f "[get_full_name $p]\t[get_property $p arrival_max_rise]\t[get_property $p arrival_min_rise]" }
close $f
# Exhaustive pair skew is last: it zeros uncertainty for skew after slack is recorded.
set ::env(OT_PS_OUT) /out/${C}_pairs.tsv
source /work/pair_skew.tcl
puts "BTAB_GRT_STA_DONE $C"

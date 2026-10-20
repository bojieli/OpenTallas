# r7a (HBM-SMATT9): 5_1_grt at the SIGN-OFF period 833.333 (route SDC over-constrains to 770), propagated clock,
# GRT parasitics; TT setup and FF hold (owner option B). Diagnostic: the route SDC IO delays are kept.
set C $::env(R7_CORNER); set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $P/lib/NLDM/*RVT_${C}*] { read_liberty $l }
read_liberty $::env(R7_MACRO_LIB)
read_db $::env(R7_ODB)
read_sdc $::env(R7_SDC)
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]; set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [all_clocks]
source $P/setRC.tcl
if {[catch {estimate_parasitics -global_routing} e]} {puts "R7_PAR placement ($e)"; estimate_parasitics -placement} else {puts "R7_PAR global_routing"}
set m [expr {$C eq "TT" ? "max" : "min"}]
puts "R7_STA $C $m"; report_worst_slack -$m; report_tns -$m
set p [find_timing_paths -path_delay $m -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1]
if {[llength $p]} {puts "R7_STA $C $m reg2reg [get_property [lindex $p 0] slack] [get_full_name [get_property [lindex $p 0] startpoint]] -> [get_full_name [get_property [lindex $p 0] endpoint]]"}
report_checks -path_delay $m -group_path_count 3 -format end

# CLAUDE WFC src hold ECO: region sign-off IO at the FF corner (r13 measured FF insertion 270.13/323.21 ps)
# 150 ps on the stage link in_*/out_*, 90 ps intra-region elsewhere, 50 ps hold IO uncertainty (driver REGION_TCL)
set per 833; set io 166.6; set lmin 270.130798; set lmax 323.211700
set ins [lsearch -all -inline -not [all_inputs] [get_ports clk]]
catch {unset_input_delay -clock [get_clocks io_clk] $ins}
catch {unset_output_delay -clock [get_clocks io_clk] [all_outputs]}
create_clock -name vclk -period $per
create_clock -name vlk -period $per
set_clock_latency -min [expr $lmin - 150] [get_clocks vclk]
set_clock_latency -max [expr $lmax + 150] [get_clocks vclk]
set_clock_latency -min [expr $lmin - 150] [get_clocks vlk]
set_clock_latency -max [expr $lmax + 150] [get_clocks vlk]
set_clock_uncertainty -setup 60 [get_clocks {vclk vlk}]
set_clock_uncertainty -hold 50 [get_clocks {vclk vlk}]
set lk_in [get_ports {in_*}]; set lk_out [get_ports {out_*}]
set_input_delay $io -clock vclk [lsearch -all -inline -not $ins [get_ports {in_*}]]
set_output_delay $io -clock vclk [lsearch -all -inline -not [all_outputs] [get_ports {out_*}]]
set_input_delay $io -clock vlk $lk_in
set_output_delay $io -clock vlk $lk_out
set_output_delay -max $io -clock vlk $lk_out
set_output_delay -min [expr {$io - 60}] -clock vlk $lk_out

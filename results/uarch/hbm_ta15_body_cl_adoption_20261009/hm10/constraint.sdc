set clk_period 833
create_clock -name core_clk -period $clk_period [get_ports clk_stream]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {core_clk vclk}]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_clock_latency 770 [get_clocks {core_clk vclk}]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk $ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk [all_outputs]
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -min 0 -clock vclk [all_outputs]
set ot_rst {}
foreach ot_c [get_cells *] { if {[string match {rst_s\[1\]*} [get_full_name $ot_c]]} { lappend ot_rst $ot_c } }
if {[llength $ot_rst]} { set_multicycle_path -setup 2 -from $ot_rst; set_multicycle_path -hold 1 -from $ot_rst }
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
delete_clock [all_clocks]
create_clock -name aon -period 3000 [get_ports aon_clk]
create_clock -name stream -period 833.333333 [get_ports clk_stream]
create_clock -name serial -period 1111.111111 [get_ports clk_serial]
create_clock -name hbm -period 1024 [get_ports clk_hbm]
create_clock -name link -period 833.333333 [get_ports clk_link]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -min 25 -clock aon [get_ports {por_n power_good pll_lock phy_ready* links_ready* bist_done bist_pass fatal_error requalify}]
set_input_delay -max 100 -clock aon [get_ports {por_n power_good pll_lock phy_ready* links_ready* bist_done bist_pass fatal_error requalify}]
set_output_delay -min 25 -clock aon [get_ports {pll_reset_n ready state*}]
set_output_delay -max 100 -clock aon [get_ports {pll_reset_n ready state*}]
set_output_delay -min 25 -clock hbm [get_ports phy_reset_n*]
set_output_delay -max 100 -clock hbm [get_ports phy_reset_n*]
set_output_delay -min 25 -clock link [get_ports link_reset_n*]
set_output_delay -max 100 -clock link [get_ports link_reset_n*]
set_output_delay -min 25 -clock stream [get_ports {coll_reset_stream_n cmd_reset_stream_n}]
set_output_delay -max 100 -clock stream [get_ports {coll_reset_stream_n cmd_reset_stream_n}]
set_output_delay -min 25 -clock serial [get_ports {coll_reset_serial_n cmd_reset_serial_n}]
set_output_delay -max 100 -clock serial [get_ports {coll_reset_serial_n cmd_reset_serial_n}]
set ot_cs {}; set ot_r0 {}; set ot_sm {}
foreach c [get_cells -hierarchical -quiet *sync_q*] {
  set n [get_full_name $c]
  if {[string match *rel_sync_q0* $n]} { lappend ot_r0 $c } elseif {![string match *rel_sync_q1* $n]} { lappend ot_cs $c }
}
set ot_sm [get_cells -hierarchical -quiet *status_meta*]
puts "OT_TA15_CL: collar sync [llength $ot_cs], ready stage-1 [llength $ot_r0], status stage-1 [llength $ot_sm]"
if {![llength $ot_cs] || ![llength $ot_r0] || ![llength $ot_sm]} { error "OT_TA15_CL: synchroniser cells not found" }
set ot_ain [get_ports {por_n power_good pll_lock phy_ready* links_ready* bist_done bist_pass}]
set_max_delay 500 -ignore_clock_latency -from [get_clocks aon] -to $ot_cs
set_min_delay 0   -ignore_clock_latency -from [get_clocks aon] -to $ot_cs
set_max_delay 500 -ignore_clock_latency -from $ot_ain -to $ot_cs
set_min_delay 0   -ignore_clock_latency -from $ot_ain -to $ot_cs
set_max_delay 500 -ignore_clock_latency -from [get_clocks {stream serial hbm link}] -to $ot_r0
set_min_delay 0   -ignore_clock_latency -from [get_clocks {stream serial hbm link}] -to $ot_r0
set_max_delay 500 -ignore_clock_latency -from $ot_ain -to $ot_sm
set_min_delay 0   -ignore_clock_latency -from $ot_ain -to $ot_sm

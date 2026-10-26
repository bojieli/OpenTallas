# s81-suhc-hier-1011: second clock of the SU root tile dsfd_su_t_root: cck = the dsfd_sp_ctrl controller clock (engine
# adapter c-side: c_cmd / c_done pins and the c-side of the adapter's CDC FIFOs).  Timed at the slab clock's period (the
# stricter of the controller domains), asynchronous to core_clk = sk (ot_s81_engine_adapter crosses through async FIFOs).
# c-side IO budgeted as the margin-first IO (0.2 T + 150 ps) against vclk_c at the measured insertion.
create_clock -name ctrl_clk -period [get_property [get_clocks core_clk] period] [get_ports {cck}]
catch {unset_input_delay -clock vclk [get_ports {cck}]}
create_clock -name vclk_c -period [get_property [get_clocks ctrl_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {ctrl_clk vclk_c}]
set_clock_uncertainty -hold 25 [get_clocks {ctrl_clk vclk_c}]
set_clock_latency 770 [get_clocks {ctrl_clk vclk_c}]
set ot_co [get_ports -quiet {c_done*}]
if {[llength $ot_co]} { unset_output_delay -clock vclk $ot_co
set_output_delay [expr {[get_property [get_clocks ctrl_clk] period] * 0.2 + 150}] -clock vclk_c $ot_co
set_output_delay -min 0 -clock vclk_c $ot_co }
set ot_ci [get_ports -quiet {c_cmd*}]
if {[llength $ot_ci]} { unset_input_delay -clock vclk $ot_ci
set_input_delay [expr {[get_property [get_clocks ctrl_clk] period] * 0.2 + 150}] -clock vclk_c $ot_ci
set_input_delay -min 0 -clock vclk_c $ot_ci }
set_clock_groups -asynchronous -group [get_clocks {ctrl_clk vclk_c}] -group [get_clocks {core_clk vclk}]
set_false_path -from [get_ports {crs srs}]

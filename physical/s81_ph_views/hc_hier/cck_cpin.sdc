# s81-suhc-hier-1011: controller clock (cck, dsfd_sp_ctrl domain, serial 0.9 GHz) of the HC centre pin tile ot_s81_hc_cpin:
# command pins -> relay flops -> combine seam, combine done -> relay flops -> done pins; asynchronous to sk (core_clk).
create_clock -name c_clk -period [expr {[get_property [get_clocks core_clk] period] * 4.0 / 3.0}] [get_ports {cck}]
catch {unset_input_delay -clock vclk [get_ports {cck}]}
create_clock -name vclk_c -period [get_property [get_clocks c_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {c_clk vclk_c}]
set_clock_uncertainty -hold 25 [get_clocks {c_clk vclk_c}]
set_clock_latency 770 [get_clocks {c_clk vclk_c}]
set ot_ci [get_ports {c_cmd_v c_cmd_d[*] n_done_v n_done_tag[*] crs}]
unset_input_delay -clock vclk $ot_ci
set_input_delay [expr {[get_property [get_clocks c_clk] period] * 0.2 + 150}] -clock vclk_c $ot_ci
set_input_delay -min 0 -clock vclk_c $ot_ci
set ot_co [get_ports {c_done_v c_done_tag[*] n_cmd_v n_cmd_d[*]}]
unset_output_delay -clock vclk $ot_co
set_output_delay [expr {[get_property [get_clocks c_clk] period] * 0.2 + 150}] -clock vclk_c $ot_co
set_output_delay -min 0 -clock vclk_c $ot_co
set_clock_groups -asynchronous -group {c_clk vclk_c} -group [get_clocks -filter {name != c_clk && name != vclk_c}]

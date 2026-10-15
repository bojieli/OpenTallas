create_clock -name core_clk -period 833.3330 
set_clock_uncertainty -setup 60.0000 core_clk
set_clock_uncertainty -hold 25.0000 core_clk
create_clock -name ot_io_response -period 833.3330 
set_clock_uncertainty -setup 60.0000 ot_io_response
set_clock_uncertainty -hold 25.0000 ot_io_response
create_clock -name ot_entry_0 -period 833.3330 [get_ports {ck_req}]
set_clock_uncertainty -setup 60.0000 ot_entry_0
set_clock_uncertainty -hold 25.0000 ot_entry_0
create_clock -name ot_entry_1 -period 833.3330 [get_ports {ck_rsp}]
set_clock_uncertainty -setup 60.0000 ot_entry_1
set_clock_uncertainty -hold 25.0000 ot_entry_1
set_clock_latency -source 0.0000 [get_clocks {ot_entry_0}]
set_clock_latency -source 49.1576 [get_clocks {ot_entry_1}]
set_clock_uncertainty -rise_from [get_clocks {ot_entry_0}] -rise_to [get_clocks {ot_entry_0}]  -hold 100.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_0}] -rise_to [get_clocks {ot_entry_0}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_0}] -fall_to [get_clocks {ot_entry_0}]  -hold 100.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_0}] -fall_to [get_clocks {ot_entry_0}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_0}] -rise_to [get_clocks {ot_entry_0}]  -hold 100.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_0}] -rise_to [get_clocks {ot_entry_0}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_0}] -fall_to [get_clocks {ot_entry_0}]  -hold 100.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_0}] -fall_to [get_clocks {ot_entry_0}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_0}] -rise_to [get_clocks {ot_entry_1}]  -hold 100.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_0}] -rise_to [get_clocks {ot_entry_1}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_0}] -fall_to [get_clocks {ot_entry_1}]  -hold 100.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_0}] -fall_to [get_clocks {ot_entry_1}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_0}] -rise_to [get_clocks {ot_entry_1}]  -hold 100.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_0}] -rise_to [get_clocks {ot_entry_1}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_0}] -fall_to [get_clocks {ot_entry_1}]  -hold 100.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_0}] -fall_to [get_clocks {ot_entry_1}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_1}] -rise_to [get_clocks {ot_entry_0}]  -hold 100.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_1}] -rise_to [get_clocks {ot_entry_0}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_1}] -fall_to [get_clocks {ot_entry_0}]  -hold 100.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_1}] -fall_to [get_clocks {ot_entry_0}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_1}] -rise_to [get_clocks {ot_entry_0}]  -hold 100.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_1}] -rise_to [get_clocks {ot_entry_0}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_1}] -fall_to [get_clocks {ot_entry_0}]  -hold 100.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_1}] -fall_to [get_clocks {ot_entry_0}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_1}] -rise_to [get_clocks {ot_entry_1}]  -hold 100.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_1}] -rise_to [get_clocks {ot_entry_1}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_1}] -fall_to [get_clocks {ot_entry_1}]  -hold 100.0000
set_clock_uncertainty -rise_from [get_clocks {ot_entry_1}] -fall_to [get_clocks {ot_entry_1}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_1}] -rise_to [get_clocks {ot_entry_1}]  -hold 100.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_1}] -rise_to [get_clocks {ot_entry_1}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_1}] -fall_to [get_clocks {ot_entry_1}]  -hold 100.0000
set_clock_uncertainty -fall_from [get_clocks {ot_entry_1}] -fall_to [get_clocks {ot_entry_1}]  -setup 210.0000
set_output_delay -168.7627 -clock [get_clocks {ot_io_response}] -min -add_delay [get_ports {o_sd[321]}]
set_output_delay 130.1904 -clock [get_clocks {ot_io_response}] -max -add_delay [get_ports {o_sd[321]}]

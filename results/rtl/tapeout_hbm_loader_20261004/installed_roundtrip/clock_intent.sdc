# ASAP7 time unit ps. Targets only: host 1ns, memory service 0.833ns.
create_clock -name mem_clk -period 833 [get_ports clk_mem]
set_clock_uncertainty -setup 60 [get_clocks mem_clk]
set_clock_uncertainty -hold 25 [get_clocks mem_clk]
unset_input_delay [get_ports clk_mem]
set mem_inputs [get_ports {req_rdy* rsp_v* rsp_we* rsp_tag* rsp_data*}]
set mem_outputs [get_ports {req_v* req_we* req_addr* req_wdata* req_wstrb* req_tag* rsp_rdy*}]
unset_input_delay $mem_inputs
unset_output_delay $mem_outputs
set_input_delay 166.6 -clock mem_clk $mem_inputs
set_output_delay 166.6 -clock mem_clk $mem_outputs
# Only host/memory traffic crosses the retained asynchronous FIFOs. This
# controller domain check does not certify Gray-bus physical skew/CDC placement.
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks mem_clk]

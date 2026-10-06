# Real selected existing HBM-service domain: clk_mem binds clk_hbm1024ps.
# External budgets remain conditional; internal receiver clocks/caps come from source.
create_clock -name mem_clk -period 1024 [get_ports clk_mem]
set_clock_uncertainty -setup 60 [get_clocks mem_clk]
set_clock_uncertainty -hold 25 [get_clocks mem_clk]
set_clock_latency -source 0 [get_clocks {core_clk mem_clk}]
unset_input_delay [get_ports clk_mem]
set ot_mem_inputs [get_ports {rst_mem_n m_req_rdy m_rsp_v m_rsp_we m_rsp_tag* m_rsp_data*}]
set ot_mem_outputs [get_ports {m_req_v m_req_we m_req_addr* m_req_wdata* m_req_wstrb* m_req_tag* m_rsp_rdy}]
unset_input_delay $ot_mem_inputs
unset_output_delay $ot_mem_outputs
set_input_delay -min 0 -clock mem_clk $ot_mem_inputs
set_input_delay -max 204.8 -clock mem_clk $ot_mem_inputs
set_output_delay -min 0 -clock mem_clk $ot_mem_outputs
set_output_delay -max 204.8 -clock mem_clk $ot_mem_outputs
# No broad clock groups, IO false paths or invented CDC phase.
# First map exposes actual kept synchronizer/capture pins for scoped CDC constraints.

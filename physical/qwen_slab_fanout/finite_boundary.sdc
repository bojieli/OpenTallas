# ot_qwen_slab_port_group (rtl/physical/ot_qwen_slab_port_group.sv): one Qwen3-8B ROM die slab port group.
# clk = the spine band clock (1.2 GHz); bw_clk = the block's forwarded clock (decision C, same frequency, unknown
# static phase).  Sign-off policy (AGENTS.md): 60 ps setup / 25 ps hold uncertainty, never relaxed.
create_clock -name clk -period 833.333 [get_ports clk]
create_clock -name bw_clk -period 833.333 [get_ports bw_clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# ot_meso_fifo phase-window budget (physical/rom_clock/meso_ring_w512_d4.sdc, unchanged): every cross-clock arc
# settles within T/2 - 60 ps; hold needs only a non-negative datapath delay (the slot is rewritten DEPTH periods on).
set_max_delay -ignore_clock_latency 356.667 -from [get_clocks bw_clk] -to [get_clocks clk]
set_max_delay -ignore_clock_latency 356.667 -from [get_clocks clk] -to [get_clocks bw_clk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks bw_clk] -to [get_clocks clk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks clk] -to [get_clocks bw_clk]
# Boundary: every port is a register stage of the die's spine wiring; 0.2 T of the cycle is spent outside.
set_input_delay 166.667 -clock bw_clk [get_ports {bw_rst_n bw_v bw_d*}]
set_input_delay 166.667 -clock clk [get_ports {rst_n tw_rdy p_* res_in*}]
set_output_delay 166.667 -clock bw_clk [get_ports {bw_rdy bw_w_fault bw_w_live}]
set_output_delay 166.667 -clock clk [get_ports {tw_v tw_d* o_we o_addr* o_mask* o_data* ov am_tv am_top* am_rmax fault bw_r_fault bw_r_live}]
set_max_fanout 32 [current_design]

# Explicit finite SS sequential-pin envelope; parent arrival contract remains unqualified.
set_load 5.55848 [all_outputs]

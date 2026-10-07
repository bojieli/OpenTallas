###############################################################################
# Created by write_sdc
###############################################################################
current_design ot_v41_rom_elem_q_qx_w10
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clk -period 833.0000 [get_ports {clk}]
set_clock_uncertainty -setup 60.0000 core_clk
set_clock_uncertainty -hold 25.0000 core_clk
set_propagated_clock [get_clocks {core_clk}]
set_multicycle_path -hold\
    -from [list [get_cells {u_e.g_mac[0].g_pp.u_rom0}]\
           [get_cells {u_e.g_mac[0].g_pp.u_rom1}]\
           [get_cells {u_e.g_mac[1].g_pp.u_rom0}]\
           [get_cells {u_e.g_mac[1].g_pp.u_rom1}]] 1
set_multicycle_path -setup\
    -from [list [get_cells {u_e.g_mac[0].g_pp.u_rom0}]\
           [get_cells {u_e.g_mac[0].g_pp.u_rom1}]\
           [get_cells {u_e.g_mac[1].g_pp.u_rom0}]\
           [get_cells {u_e.g_mac[1].g_pp.u_rom1}]] 2
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################
set_max_transition 320.0000 [current_design]
set_max_fanout 32.0000 [current_design]

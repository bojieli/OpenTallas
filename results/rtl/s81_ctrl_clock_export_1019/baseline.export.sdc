###############################################################################
# Created by write_sdc
# Mon Oct 19 19:44:50 2026
###############################################################################
current_design top
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clk -period 770.0000 [get_ports {clk}]
set_propagated_clock [get_clocks {core_clk}]
create_clock -name hclk -period 900.0000 [get_ports {ckh}]
set_propagated_clock [get_clocks {hclk}]
create_generated_clock -name ck_o_fwd -source [get_ports {clk}] -divide_by 1 [get_ports {ck_o}]
set_propagated_clock [get_clocks {ck_o_fwd}]
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################

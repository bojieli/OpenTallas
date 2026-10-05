# ot_ratio_cdc_fifo (f2s): writer clock wclk = fast, reader clock rclk = slow.
# Both clocks divide one 3.6 GHz VCO (277.777 ps tick): fast = 3 ticks, slow = 4 ticks, rising edges aligned at
# t = 0.  The periods are exact tick multiples (833.331 / 1111.108 ps, 3 fs and 4 fs FASTER than 1.2 / 0.9 GHz,
# never slower), so STA sees one commensurate 3333.324 ps pattern and times every fast/slow edge pair: the
# tightest launch->capture setup window is one tick (277.777 ps) and hold is checked at the coincident edge.
# For any divider phase the set of edge spacings is identical (gcd(3,4) = 1), so phase 0 covers all phases.
# Related clocks, one PLL: NO clock groups, NO false or multicycle paths, NO max-delay exceptions.
create_clock -name fast -period 833.331 [get_ports wclk]
create_clock -name slow -period 1111.108 [get_ports rclk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.666 -clock fast [get_ports {w_v w_d* wrst_n}]
set_input_delay 222.222 -clock slow [get_ports {r_rdy rrst_n}]
set_output_delay 166.666 -clock fast [get_ports {w_rdy w_live}]
set_output_delay 222.222 -clock slow [get_ports {r_v r_d* r_live}]
set_max_fanout 32 [current_design]

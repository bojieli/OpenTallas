# qfd_tile / qfd_tile_e = ot_qwen_rom_tile_w12 margin route: over-constrained 770 ps (sign-off 833.333 = slack + 63.333).
# 60 / 25 ps uncertainty never relaxed.  Boundary 0.2 x 833.333 = 166.667 ps; after CTS the hooks switch to
# io_ref_skew.sdc.  tile_id is a static per-tile strap (die tie-off), not a timed path.
create_clock -name core_clk -period 770 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.667 -clock core_clk [all_inputs -no_clocks]
set_output_delay 166.667 -clock core_clk [all_outputs]
set_false_path -from [get_ports tile_id*]
set_max_fanout 32 [current_design]
set_load 3.898 [all_outputs]
set_max_transition 260 [current_design]

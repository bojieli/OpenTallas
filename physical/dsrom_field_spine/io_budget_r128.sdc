# DS-ROM field spine v13 (margin-first) ROUTING boundary for the R = 128 screen (--sdc-append of phys13.sh; units ps).
# Die-integration IO budget (owner rule 2026-10-06 + clarification): the neighbour (die station, another clock region)
# launches / captures on a clock arriving at the block's measured insertion +/- 150 ps, with 100 ps wire + station
# clk-q on the late side.  Measured insertion (v11 routed R = 128, SS): 850 ps.
#  * The neighbour clock is a VIRTUAL clock io_clk with SOURCE latency 850 (kept when the flow propagates clocks).
#  * The core clock gets the same insertion as IDEAL network latency, so the pre-CTS stages time the boundary
#    consistently; from CTS on it is propagated (the ideal latency is then ignored) and the real tree replaces it.
#  * Setup: input max = 150 + 100, output max = 150 + 100 (relative to io_clk).
#  * Hold (clarification: sign-off at FF with each corner's insertion and 50 ps hold IO uncertainty, signoff_r128.sdc):
#    the flow repairs hold at WC and BC with one number, so it asks 125 ps at WC (150 ps with the 25 ps uncertainty),
#    whose buffers keep ~90 ps at FF (~0.6 FF/WC buffer delay) over the FF need of 75 ps.
set_clock_latency 850 [get_clocks core_clk]
create_clock -name io_clk -period [get_property [get_clocks core_clk] period]
set_clock_latency -source 850 [get_clocks io_clk]
set_clock_uncertainty -setup 60 [get_clocks io_clk]
set_clock_uncertainty -hold 25 [get_clocks io_clk]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set fs_in [get_ports {go i_ph* i_np* i_xbase* i_xps* i_obase* i_ops* i_fmt* x_q* r_v* r_row* r_pos* r_fp32* r_bf16* r_e* f_fault}]
set_input_delay  250 -max -clock io_clk $fs_in
set_input_delay  -125 -min -clock io_clk $fs_in
set_output_delay 250 -max -clock io_clk [all_outputs]
set_output_delay -125 -min -clock io_clk [all_outputs]
# screen-fixture ROM write ports (the die's ROMs are macros, not written) and the reset (the die's synchronised tree)
set_false_path -from [get_ports {rw_ph rw_st rw_a* rw_d* rst_n}]

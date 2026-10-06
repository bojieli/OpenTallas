# DS-ROM field spine v13 (margin-first) ROUTING boundary for the R = 128 screen (--sdc-append of phys13.sh; units ps).
# Die-integration IO budget (owner rule 2026-10-06): the neighbour (die station) clock arrives at the block's measured
# insertion +/- 150 ps; 100 ps wire + station clk-q allowance on the late side.  Measured insertion (v11 routed R = 128,
# SS): 850 ps.  The core clock is given that insertion as its IDEAL network latency, so the pre-CTS stages time the
# boundary consistently; from CTS on the clock is propagated (OpenSTA then ignores the ideal latency) and the real tree
# replaces it.  Sign-off re-times the boundary against the propagated arrival per corner (signoff_r128.sdc).
set_clock_latency 850 [get_clocks core_clk]
set fs_in [get_ports {go i_ph* i_np* i_xbase* i_xps* i_obase* i_ops* i_fmt* x_q* r_v* r_row* r_pos* r_fp32* r_bf16* r_e* f_fault}]
set_input_delay  1100 -max -clock core_clk $fs_in
set_input_delay  700 -min -clock core_clk $fs_in
set_output_delay -600 -max -clock core_clk [all_outputs]
set_output_delay -1000 -min -clock core_clk [all_outputs]
# screen-fixture ROM write ports (the die's ROMs are macros, not written) and the reset (the die's synchronised tree)
set_false_path -from [get_ports {rw_ph rw_st rw_a* rw_d* rst_n}]

# CP pin-margin route constraints (Claude:tk-hbm-cp, OWNER MARGIN-FIRST 2026-10-06), appended after the driver SDC.
# Same convention as the HBM die views (physical/hbm_accel_die_views/common/make_io_vclk_margin.sh on
# claude/hbm-abstracts-20261006): route over-constrained to an effective 770 ps (setup uncertainty 123 ps on the
# 833.333 ps clock, set by the driver), IO budget 0.2 T + 150 ps die clock-arrival allowance against a virtual clock at
# the block's insertion L (planning value 120 ps = the measured CTS insertion of the r1_terminal CP route,
# clkbuf_0 -> leaf ~120 ps SS). Sign-off re-times at 60 ps with vclk at the measured insertion (signoff_post.sdc).
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {core_clk vclk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk vclk}]
set_clock_latency 120 [get_clocks {core_clk vclk}]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk $ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk [all_outputs]
# Route-time hold over-constraint only: inputs repaired as if launched 60 ps early (the FF insertion is ~40 ps
# below the SS planning L); sign-off times them at -min 0 against vclk at the measured insertion.
set_input_delay -min -60 -clock vclk $ot_in
set_output_delay -min 0 -clock vclk [all_outputs]
set_load 9.673192000 [all_outputs]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ot_in

# SU-side CP block route constraints (Claude:hbm-su-cpin, OWNER MARGIN-FIRST 2026-10-06), appended after the driver
# SDC. Route over-constrained to an effective 770 ps (setup uncertainty 123 ps on 833.333 ps, set by the driver);
# vclk at the planning insertion 120 ps (measured CTS insertion of the CP pin-margin route). Port classes: io_classes.tcl.
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {core_clk vclk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk vclk}]
set_clock_latency 120 [get_clocks {core_clk vclk}]
unset_input_delay -clock core_clk [all_inputs -no_clocks]
unset_output_delay -clock core_clk [all_outputs]
source /src/physical/hbm_su_cp_side_20261006/io_classes.tcl
# Route-time hold over-constraint only (inputs repaired as if launched 60 ps early); sign-off uses -min 0.
ot_apply_io -60
set_load 9.673192000 [all_outputs]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y [all_inputs -no_clocks]

# S81-PINREG4 2026-10-19 (SAFE item 1, die hold budget T-OUT): signoff_col.sdc with ONE change, the output min delay.
# Why: the CLOSED prepabs route (bfh_compact199_col_pinreg_prepabs_1019) has every one of the 64 PQ outputs registered at
# its pin (pinflop_band.tcl: flop within ~10 um of the S-face pin) but then 10 x BUFx2 + 1 INV hold pad between that flop
# and the pin (6_final.v), = native launch 263-281 ps at TT (physical/s81_die_views/bf_compact199_prepabs/ot_v41_bf_col).
# The pad is the rule-H1 sender hold term: output min -(L + 50) + U 25 + route HM 30 = launch >= L + 105 at FF, while
# the PQ flops sit on the ordinary tree (~25-30 ps before the bf_pinclk reference group L) with clk->Q ~32 ps.
# Fix = the owner-approved die-wide boundary hold budget (results/arch/boundary_hold_budget_1016/RULE.md, 10-16, T-OUT,
# the ref_tile "hold_budget": "die" contract): output min = U - (L_min + C), C = 25 ps guaranteed sender launch, i.e. every
# output proves launch >= L_min + 25 at FF sign-off (a pin flop meets it with ~2-3 pad cells under the route HM).
# Inputs, setup, clocks and uncertainties unchanged.  Die obligation: die/frame FF STA checks every bf_col output link
# against the receiver's exported hold need (ETM), as the RULE's die check.
# BF native pair (PINREG=1, HITFIX=1) closure-loop SIGN-OFF constraints, read by tools/w18/corner_sta.py --post-sdc after
# the routed 6_final.sdc: clock 833.333 ps, 60 / 25 ps uncertainty, the m2 die IO model (die clock arrival = boundary
# insertion +/- 150 ps, 100 ps wire/station on the max side, 50 ps hold IO) with the insertion MEASURED in this STA run:
# L = mean propagated clock arrival at the PINREG boundary registers' CLK pins (corner_sta runs one corner per STA, so
# L is the SS insertion in the setup run and the FF insertion in the hold run; OpenROAD 26Q3 crashes on -reference_pin,
# so the reference is applied numerically, as physical/qwen_core_ctx/io_ref.sdc).
#   input  max = L + 250, min = L             output max = 250 - L, min = -(L + 50)
# rule H1 (flow-hold 2026-10-07; bf-hold 2026-10-08): the die-link hold term is carried ONCE, by the sender's output
# min -(L + 50); the receiver's input min is L (it was L - 50: the 50 ps counted on both sides of every die link).
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_load 3.898 [all_outputs]
set_false_path -from [get_ports rst_n_pin]
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]
# build the timing graph before querying arrivals (a cold get_property arrival segfaults OpenROAD 26Q3)
set bf_w [sta::worst_slack_cmd max]
set bf_n 0; set bf_amax 0.0; set bf_amin 0.0
foreach bf_c [get_cells -quiet -hierarchical {g_pin.r_*}] {
  set bf_p [get_pins -quiet "[get_full_name $bf_c]/CLK"]
  if {[llength $bf_p] == 0} continue
  set bf_x [get_property $bf_p arrival_max_rise]; set bf_y [get_property $bf_p arrival_min_rise]
  if {$bf_x eq "INF" || $bf_y eq "INF"} continue
  incr bf_n; set bf_amax [expr {$bf_amax + $bf_x}]; set bf_amin [expr {$bf_amin + $bf_y}]
}
if {$bf_n == 0} {
  foreach bf_p [all_registers -clock_pins] {
    set bf_x [get_property $bf_p arrival_max_rise]; set bf_y [get_property $bf_p arrival_min_rise]
    if {$bf_x eq "INF" || $bf_y eq "INF"} continue
    incr bf_n; set bf_amax [expr {$bf_amax + $bf_x}]; set bf_amin [expr {$bf_amin + $bf_y}]
  }
}
set bf_lmax [expr {$bf_amax / $bf_n}]; set bf_lmin [expr {$bf_amin / $bf_n}]
puts "BF_IO boundary registers $bf_n insertion mean max $bf_lmax min $bf_lmin"
set bf_ins [all_inputs -no_clocks]
set_input_delay -max [expr {$bf_lmax + 250}] -clock core_clk $bf_ins
set_input_delay -min $bf_lmin -clock core_clk $bf_ins
set_output_delay -max [expr {250 - $bf_lmax}] -clock core_clk [all_outputs]
# T-OUT (die hold budget): output min = U - (L_min + C), U = 25 ps, C = 25 ps (was -(L_min + 50), rule H1)
set bf_hb_c 25.0; set bf_hb_u 25.0
set_output_delay -min [expr {$bf_hb_u - ($bf_lmin + $bf_hb_c)}] -clock core_clk [all_outputs]
puts "BF_IO_HB output min [expr {$bf_hb_u - ($bf_lmin + $bf_hb_c)}] (T-OUT C $bf_hb_c U $bf_hb_u, L_min $bf_lmin)"

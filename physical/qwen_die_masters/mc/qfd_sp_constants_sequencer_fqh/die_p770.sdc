# Qwen die master margin route (die-context IO, template station_die_p770.sdc of the die-top a9bf510a0): 770 ps over-constrained (sign-off 833.333 = slack + 63.333),
# 60 / 25 ps uncertainty, boundary 0.2 x 833.333; after CTS the hooks switch to io_ref_skew.sdc.
create_clock -name core_clk -period 770 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.667 -clock core_clk [all_inputs -no_clocks]
set_output_delay 166.667 -clock core_clk [all_outputs]
set_max_fanout 32 [current_design]
# die-wire context (r21 die STA): an output drives one die hop of <= 430.56 um on M8/M9 (~0.17 fF/um) plus the
# receiving pin: 80 fF; an input arrives through that wire: 150 ps transition
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_max_transition 260 [current_design]

# safe-qwen S-A6 (2026-10-08): po_me_clk is the engine gated clock (ICG output), a clock pin of the spine master, not
# data: clk -> po_me_clk was timed against the output budget (-381.6, the core_kv u_me.clk artefact class, 77d93ac50).
set_false_path -to [get_ports -quiet {po_me_clk}]

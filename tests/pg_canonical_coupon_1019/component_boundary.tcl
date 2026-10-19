# Fixed source-owned diagnostic budgets, identical before/after CTS.
# Preserve propagated clock state; no invented neighbour reference or source latency.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay 100 -clock core_clk [all_inputs -no_clocks]
set_output_delay 100 -clock core_clk [all_outputs]
set_load 80 [all_outputs]

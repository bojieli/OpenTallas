# Restore the agreed 60/25 ps sign-off policy after the 123 ps setup
# uncertainty used only to route with margin. Keep both real clock periods.
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
source /src/physical/qwen_stream4_cdc/io_skew90.sdc
# Real die-wire boundary from the 2026-10-07 element contract.
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]

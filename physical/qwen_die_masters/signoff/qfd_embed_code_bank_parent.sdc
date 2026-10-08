create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
source /src/physical/qwen_embedding_parent/code/io_ref_skew.sdc
source /src/physical/qwen_die_masters/embed_bank_capture.sdc

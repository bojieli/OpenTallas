# B4 confirmed review0242: SAME generic250ps and sender hold50ps rule.
# P1 source38f22c6d8 routed_ioref.a1.json actual boundary TTmean561/FFmean462.
# Old calibration TT657/FF546 gave input907/546 output-407/-596.
# Regenerate same formula from actual routed insertion: maxin561+250=811;
# minin462; maxout250-561=-311; minout-(462+50)=-512.
# No period/uncertainty/protocol/latency change; no generic budget term removed.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -max 811 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 462 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max -311 -clock core_clk [all_outputs]
set_output_delay -min -512 -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_false_path -from [get_ports rst_n]

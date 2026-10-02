read_liberty {/tmp/opentallas-qwen-rom-abstract-20261002/physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2_ss.lib}
read_liberty {/tmp/qwen-rom-macro-capture-20261002/seq_ss.lib}
read_verilog {/tmp/qwen-rom-macro-capture-sta-local-r1/ot_sram_1r1w_512x128_m4_r2c2_ss.v}
link_design macro_capture
create_clock -name clk -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_clock_transition 20 [get_clocks clk]
set_load 2.88 [get_ports raw]
report_units
report_checks -to [get_pins capture/D] -path_delay max -format full_clock_expanded -digits 6 -fields {slew cap input net fanout}
exit

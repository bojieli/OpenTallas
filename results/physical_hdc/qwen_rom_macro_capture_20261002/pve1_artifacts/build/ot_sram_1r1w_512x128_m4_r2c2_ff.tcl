read_liberty {/home/ubuntu/w12/qwen_macro_capture_20261002_d0e5/source/physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2_ff.lib}
read_liberty {/home/ubuntu/w12/qwen_macro_capture_20261002_d0e5/capture_libs/seq_ff.lib}
read_verilog {/home/ubuntu/w12/qwen_macro_capture_20261002_d0e5/build/ot_sram_1r1w_512x128_m4_r2c2_ff.v}
link_design macro_capture
create_clock -name clk -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_clock_transition 20 [get_clocks clk]
set_load 2.88 [get_ports raw]
report_units
report_checks -to [get_pins capture/D] -path_delay min -format full_clock_expanded -digits 6 -fields {slew cap input net fanout}
exit

read_liberty /tmp/opentallas-qwen-rom-abstract-20261002/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_ss.lib
read_liberty /tmp/qwen-enabled-capture-map-r2/mapped_lib_ss.lib
read_verilog /tmp/qwen-enabled-capture-map-r2/mapped.v
link_design qwen_current_enabled_capture
create_clock -name clk -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_clock_transition 20 [get_clocks clk]
report_units
report_checks -path_delay max -format full_clock_expanded -digits 6 -fields {slew cap input net fanout}
report_check_types -max_capacitance -max_slew -max_fanout
exit

read_liberty /tmp/dsrom-s81-minimum-w6-leaves-20261004-r3/ao_ss.lib
read_liberty /tmp/dsrom-s81-minimum-w6-leaves-20261004-r3/invbuf_ss.lib
read_liberty /tmp/dsrom-s81-minimum-w6-leaves-20261004-r3/oa_ss.lib
read_liberty /tmp/dsrom-s81-minimum-w6-leaves-20261004-r3/simple_ss.lib
read_liberty /tmp/dsrom-s81-minimum-w6-leaves-20261004-r3/seq_ss.lib
read_verilog /tmp/dsrom-s81-minimum-w6-fanout8-capture-20261004-r2/decode/buffered.v
link_design leaf
create_clock -name core -period 1111.111111 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core]
set_clock_uncertainty -hold 25 [get_clocks core]
set_input_transition 20 [get_ports din*]
report_units
report_checks -from [all_registers -output_pins] -to [all_registers -data_pins] -path_delay max -group_count 1 -digits 6 -fields {slew capacitance input_pin net}
report_checks -from [all_registers -output_pins] -to [all_registers -data_pins] -path_delay min -group_count 1 -digits 6 -fields {slew capacitance input_pin net}
report_check_types -max_slew -max_capacitance
exit

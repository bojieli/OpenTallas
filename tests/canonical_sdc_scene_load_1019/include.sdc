incr ::include_reads([sta::cmd_mode_name])
set_units -capacitance pF
set_load -pin_load 0.051 [get_ports {y[6]}]
set_load -wire_load 0.019 [get_ports {y[6]}]
set_units -capacitance fF

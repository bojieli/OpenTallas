###############################################################################
# Created by write_sdc
###############################################################################
current_design tiny
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name clk -period 833.0000 [get_ports {clk}]
set_clock_uncertainty -setup 60.0000 clk
set_clock_uncertainty -hold 25.0000 clk
create_clock -name vclk -period 833.0000 
set_clock_uncertainty -setup 60.0000 vclk
set_clock_uncertainty -hold 25.0000 vclk
set_input_delay -40.0000 -clock [get_clocks {vclk}] -min -add_delay [get_ports {d}]
set_input_delay 150.0000 -clock [get_clocks {vclk}] -max -add_delay [get_ports {d}]
set_input_delay -40.0000 -clock [get_clocks {vclk}] -min -add_delay [get_ports {t}]
set_input_delay 150.0000 -clock [get_clocks {vclk}] -max -add_delay [get_ports {t}]
set_output_delay 0.0000 -clock [get_clocks {vclk}] -min -add_delay [get_ports {o}]
set_output_delay 150.0000 -clock [get_clocks {vclk}] -max -add_delay [get_ports {o}]
set_path_margin -hold\
    -from [get_ports {d}]\
    -to [get_pins {ff0/D}] 5.0000
set_multicycle_path -hold\
    -from [get_ports {d}]\
    -to [get_pins {ff1/D}] 3
set_min_delay\
    -from [get_pins {ff0/CLK}]\
    -to [get_ports {o}] 50.0000
set_max_delay\
    -from [get_ports {d}]\
    -to [get_pins {ff1/D}] 700.0000
set_false_path\
    -from [get_ports {t}]\
    -to [get_pins {ff0/D}]
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################

# Native ASAP7 ps/fF; exact Kant isolated boundary, no relaxation.
create_clock -name core -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core]
set_clock_uncertainty -hold 25 [get_clocks core]
set code_inputs {}
foreach p [all_inputs] {if {[get_full_name $p] ni {clk por_n}} {lappend code_inputs $p}}
set_input_delay -clock core -max 120 $code_inputs
set_input_delay -clock core -min 0 $code_inputs
set_driving_cell -lib_cell BUFx2_ASAP7_75t_R -pin Y $code_inputs
set_output_delay -clock core -max 120 [all_outputs]
set_output_delay -clock core -min 0 [all_outputs]
set_load 0.558822 [all_outputs]
set_false_path -from [get_ports por_n]

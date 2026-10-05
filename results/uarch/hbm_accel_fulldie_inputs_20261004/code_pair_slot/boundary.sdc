# ISOLATED interface contract ONLY; not actual production-parent delays/load.
set_units -time ns -capacitance pF
create_clock -name core -period 0.833333333 [get_ports clk]
set_clock_uncertainty -setup 0.060 [get_clocks core]
set_clock_uncertainty -hold 0.025 [get_clocks core]
set code_inputs [remove_from_collection [all_inputs] [get_ports {clk por_n}]]
set_input_delay -clock core -max 0.120 $code_inputs
set_input_delay -clock core -min 0.000 $code_inputs
set_driving_cell -lib_cell BUFx2_ASAP7_75t_R -pin Y $code_inputs
set_output_delay -clock core -max 0.120 [all_outputs]
set_output_delay -clock core -min 0.000 [all_outputs]
set_load 0.000558822 [all_outputs]
# Cold-reset boundary only. Release before clock; no warm-reset claim.
set_false_path -from [get_ports por_n]

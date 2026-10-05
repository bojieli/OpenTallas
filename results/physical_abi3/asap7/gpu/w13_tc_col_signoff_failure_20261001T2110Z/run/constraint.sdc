# Budgeted boundary constraints for ot_gpu_tc_col from gpu_sm_qwen
# (tools/chip_assembly/budgets.py); period 833 ps; the external
# flops are clocked 356.58 ps late, as the parent balances this block's insertion delay.
set clk_period 833
create_clock -name clk -period $clk_period [get_ports clk]
set_clock_uncertainty 60 [get_clocks clk]
set_max_fanout 32 [current_design]
set_max_transition 320 [current_design]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y [all_inputs -no_clocks]
set_false_path -from [get_ports rst_n]
set_output_delay -33.6 -clock clk [get_ports {fault}]
set_load 4.0 [get_ports {fault}]
set_input_delay 829.6 -clock clk [get_ports {first}]
set_input_delay 829.6 -clock clk [get_ports {last}]
set_output_delay -33.6 -clock clk [get_ports {otag[*]}]
set_load 4.0 [get_ports {otag[*]}]
set_output_delay -33.6 -clock clk [get_ports {ov}]
set_load 4.0 [get_ports {ov}]
set_input_delay 829.6 -clock clk [get_ports {tag[*]}]
set_input_delay 829.6 -clock clk [get_ports {v}]
set_input_delay 829.6 -clock clk [get_ports {w[*]}]
set_input_delay 829.6 -clock clk [get_ports {x[*]}]
set_output_delay -33.6 -clock clk [get_ports {y[*]}]
set_load 4.0 [get_ports {y[*]}]

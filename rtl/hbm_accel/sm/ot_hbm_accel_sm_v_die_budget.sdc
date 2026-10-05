# ot_hbm_accel_sm_v ENABLE=1 in its die: the W13 die budget of the SM's ports
# (results/physical_abi3/asap7/chip/budgets/gpu_hbm_die_v41.json, 1.2 GHz, 60 ps uncertainty): every input lands in a
# flop within 300 ps of the pin (external 473 ps), every output leaves a flop within 450 ps including the element's
# clock insertion (external 323 ps).  Setup (max) budgets; the min (hold) delays stay at the flow's 20 % of the period.
set_input_delay -max 473 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max 323 -clock core_clk [all_outputs]
set_false_path -from [get_ports rst_n]

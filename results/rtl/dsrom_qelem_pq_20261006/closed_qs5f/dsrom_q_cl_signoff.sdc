# PQ q-element sign-off post-SDC (cl_signoff_sdc.sh): CK_SS_MEAN 520.0 ps, CK_FF_MEAN 414.0 ps
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_input_delay -max 727 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max -160.0 -clock core_clk [all_outputs]
set_output_delay -min -414.0 -clock core_clk [all_outputs]

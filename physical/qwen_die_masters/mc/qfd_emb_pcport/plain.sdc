# qfd_emb_pcport: multi-clock kit (jobs/mk_mc_kit.py); route over-constrained at 960 ps
create_clock -name clk -period 960 [get_ports {clk}]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# unrelated-clock crossings: one period minus the setup uncertainty, both directions; hold: non-negative
set_input_delay 204.8 -clock clk [get_ports {col_v col_we col_sr r_v r_d[*] w_v w_d[*]}]
set_output_delay 204.8 -clock clk [get_ports {wd[*] kv_v kv_d[*] em_v em_d[*] fault}]
set_false_path -from [get_ports {rst_n}]
set_max_fanout 32 [current_design]
# die-wire context (r21 die STA): one <= 430.56 um hop + receiver pin
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_max_transition 260 [current_design]

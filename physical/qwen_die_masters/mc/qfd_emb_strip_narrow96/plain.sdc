# qfd_emb_strip_w600: multi-clock kit (jobs/mk_mc_kit.py); route over-constrained at 770 ps
create_clock -name clk -period 770 [get_ports {clk}]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# unrelated-clock crossings: one period minus the setup uncertainty, both directions; hold: non-negative
set_input_delay 166.667 -clock clk [get_ports {i_v i_d[*] o_cr s_cr[*] e_v[*] e_d[*]}]
set_output_delay 166.667 -clock clk [get_ports {i_cr o_v o_d[*] s_m[*] s_we s_bank[*] s_col[*] s_row[*] w_m[*] w_d[*] fault fault_code[*] ce_cnt[*] ue_info[*]}]
set_false_path -from [get_ports {rst_n}]
set_max_fanout 32 [current_design]
# die-wire context (r21 die STA): one <= 430.56 um hop + receiver pin
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_max_transition 260 [current_design]

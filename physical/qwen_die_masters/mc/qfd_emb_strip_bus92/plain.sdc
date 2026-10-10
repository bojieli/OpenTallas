# qfd_emb_strip_bus92: multi-clock kit (jobs/mk_mc_kit.py); route over-constrained at 770 ps
create_clock -name clk -period 770 [get_ports {clk}]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# unrelated-clock crossings: one period minus the setup uncertainty, both directions; hold: non-negative
set_input_delay 166.667 -clock clk [get_ports {link_i[*] ret0[*] ret1[*] ret2[*] ret3[*] ret4[*] ret5[*] ret6[*] ret7[*] ret8[*] ret9[*] ret10[*] ret11[*] ret12[*] ret13[*] ret14[*] ret15[*] ret16[*] ret17[*] ret18[*] ret19[*] ret20[*] ret21[*] ret22[*] ret23[*] ret24[*] ret25[*] ret26[*] ret27[*] ret28[*] ret29[*] ret30[*] ret31[*]}]
set_output_delay 166.667 -clock clk [get_ports {link_o[*] cmd0[*] cmd1[*] cmd2[*] cmd3[*] cmd4[*] cmd5[*] cmd6[*] cmd7[*] cmd8[*] cmd9[*] cmd10[*] cmd11[*] cmd12[*] cmd13[*] cmd14[*] cmd15[*] cmd16[*] cmd17[*] cmd18[*] cmd19[*] cmd20[*] cmd21[*] cmd22[*] cmd23[*] cmd24[*] cmd25[*] cmd26[*] cmd27[*] cmd28[*] cmd29[*] cmd30[*] cmd31[*] fault fault_code[*] ce_cnt[*] ue_info[*]}]
set_false_path -from [get_ports {rst_n}]
set_max_fanout 32 [current_design]
# die-wire context (r21 die STA): one <= 430.56 um hop + receiver pin
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_max_transition 260 [current_design]

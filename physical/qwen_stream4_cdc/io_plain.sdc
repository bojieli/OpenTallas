# plain boundary (cdc_pc_slew.sdc lines), restored after each stage so the written stage SDC reloads
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay  166.667 -clock clk  [get_ports {c_arst_n l_pop w_v w_sec* w_data* w_tag*}]
set_output_delay 166.667 -clock clk  [get_ports {l_v l_sec* l_row* l_data* w_room wd_v wd_tag* c_fault}]
set_input_delay  204.800 -clock hclk [get_ports {h_arst_n h_lv h_lsec* h_lrow* h_ldata* h_hand h_wcon h_av h_atag*}]
set_output_delay 204.800 -clock hclk [get_ports {h_cred* h_wv h_wsec* h_cv h_csec* h_cdata* h_ctag* h_fault}]

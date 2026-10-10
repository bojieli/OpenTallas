# drive-0849: io_plain.sdc was missing from this kit (post_plain.tcl reads it after CTS: STA-0340 on both -pb routes); IO lines of plain.sdc
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay 166.667 -clock ck [get_ports {o_seq_coll_cr i_coll_seq_v i_coll_seq[*]}]
set_output_delay 166.667 -clock ck [get_ports {o_seq_coll_v o_seq_coll[*] fault_ck}]
set_input_delay 166.667 -clock ckd [get_ports {i_seq_coll_v i_seq_coll[*] o_coll_seq_cr}]
set_output_delay 166.667 -clock ckd [get_ports {i_seq_coll_cr o_coll_seq_v o_coll_seq[*] fault_ckd}]
set_false_path -from [get_ports rst_n]

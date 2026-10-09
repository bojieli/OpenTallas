# sys-takeover 2026-10-09: io_plain.sdc for the qfd_coll_xfifo kit (post_plain.tcl reads it after CTS / GRT / DRT / fill;
# qfd_coll_xfifo_l8_a-c177e6af6 crashed STA-0340 at 4_1_cts without it).  Plain boundary = 0.2 x 833.333 each side,
# per clock domain as plain.sdc.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay 166.667 -clock ck [get_ports {o_seq_coll_cr i_coll_seq_v i_coll_seq[*]}]
set_output_delay 166.667 -clock ck [get_ports {o_seq_coll_v o_seq_coll[*] fault_ck}]
set_input_delay 166.667 -clock ckd [get_ports {i_seq_coll_v i_seq_coll[*] o_coll_seq_cr}]
set_output_delay 166.667 -clock ckd [get_ports {i_seq_coll_cr o_coll_seq_v o_coll_seq[*] fault_ckd}]
set_false_path -from [get_ports {rst_n}]

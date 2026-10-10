# sys-takeover 2026-10-09: qfd_coll_xfifo (ot_qwen_die_coll_xfifo, the native collective local port): two
# unrelated clocks ck (collective) / ckd (sequencer), written from the qfd_io_xfifo kit pattern.
# route over-constrained at 770 ps
create_clock -name ck -period 770 [get_ports ck]
create_clock -name ckd -period 770 [get_ports ckd]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# crossings: Gray pointer -> first synchroniser flop, and the read mux -> capture register: one period minus
# the setup uncertainty in both directions (no static phase relation); hold only non-negative
set_max_delay -ignore_clock_latency 710.000 -from [get_clocks ck] -to [get_clocks ckd]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ck] -to [get_clocks ckd]
set_max_delay -ignore_clock_latency 710.000 -from [get_clocks ckd] -to [get_clocks ck]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ckd] -to [get_clocks ck]
set_input_delay 166.667 -clock ck [get_ports {o_seq_coll_cr i_coll_seq_v i_coll_seq[*]}]
set_output_delay 166.667 -clock ck [get_ports {o_seq_coll_v o_seq_coll[*] fault_ck}]
set_input_delay 166.667 -clock ckd [get_ports {i_seq_coll_v i_seq_coll[*] o_coll_seq_cr}]
set_output_delay 166.667 -clock ckd [get_ports {i_seq_coll_cr o_coll_seq_v o_coll_seq[*] fault_ckd}]
set_false_path -from [get_ports rst_n]
set_max_fanout 32 [current_design]
# die-wire context (r21 die STA): one <= 430.56 um hop + receiver pin
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_max_transition 260 [current_design]

# qfd_emb_far92: multi-clock kit (jobs/mk_mc_kit.py); route over-constrained at 770 ps
create_clock -name ck -period 770 [get_ports {ck}]
create_clock -name lclk -period 770 [get_ports {lclk}]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# unrelated-clock crossings: one period minus the setup uncertainty, both directions; hold: non-negative
set_max_delay -ignore_clock_latency 710.000 -from [get_clocks ck] -to [get_clocks lclk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ck] -to [get_clocks lclk]
set_max_delay -ignore_clock_latency 710.000 -from [get_clocks lclk] -to [get_clocks ck]
set_min_delay -ignore_clock_latency 0 -from [get_clocks lclk] -to [get_clocks ck]
set_input_delay 166.667 -clock ck [get_ports {hub_i[*]}]
set_input_delay 166.667 -clock lclk [get_ports {emb_i[*] kv_i[*]}]
set_output_delay 166.667 -clock lclk [get_ports {hub_o[*] emb_o[*] kv_o[*] fault}]
set_false_path -from [get_ports {rst_n}]
set_max_fanout 32 [current_design]
# die-wire context (r21 die STA): one <= 430.56 um hop + receiver pin
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_max_transition 260 [current_design]

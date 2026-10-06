# hfd_stn_r2: forwarded clocks (one per 512 b slice and direction), the local clock ck, the meso
# crossings (max 356.667 / min 0 ps ignoring latency, the closed ot_meso_fifo W512 D4 contract), io budget 0.2 T.
set_max_fanout 32 [current_design]
create_clock -name ck -period 833.333 [get_ports {ck[0]}]
create_generated_clock -name o_b44 -source [get_ports {ck[0]}] -master_clock ck -divide_by 1 [get_ports {b[44]}]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.666 -clock ck [get_ports {a[0] a[10] a[11] a[12] a[13] a[14] a[15] a[16] a[17] a[18] a[19] a[1] a[20] a[21] a[22] a[23] a[24] a[25] a[26] a[27] a[28] a[29] a[2] a[30] a[31] a[32] a[33] a[34] a[35] a[36] a[37] a[38] a[39] a[3] a[40] a[41] a[42] a[4] a[5] a[6] a[7] a[8] a[9]}]
set_output_delay 166.666 -clock ck [get_ports {a[43]}]
set_output_delay 166.666 -clock o_b44 -clock_fall [get_ports {b[0] b[10] b[11] b[12] b[13] b[14] b[15] b[16] b[17] b[18] b[19] b[1] b[20] b[21] b[22] b[23] b[24] b[25] b[26] b[27] b[28] b[29] b[2] b[30] b[31] b[32] b[33] b[34] b[35] b[36] b[37] b[38] b[39] b[3] b[40] b[41] b[42] b[43] b[4] b[5] b[6] b[7] b[8] b[9]}]
set_load 2.0 [all_outputs]
set_input_delay 166.666 -clock ck -add_delay [get_ports {rst[0]}]

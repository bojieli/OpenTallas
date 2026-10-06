# Native caller diagnostic only. Actual arrays/dispatch/receiver cones internal.
# Facing pin groups, not guessed top-level delays or installed terminal caps.
set_io_pin_constraint -group -region bottom:* -pin_names {inj_data[*] inj_idx[*] inj_rd[*]}
set_io_pin_constraint -group -region top:* -pin_names {w2_v[*] w2_d[*]}
set_io_pin_constraint -group -region right:* -pin_names {qr_heads[*] qr_counts[*] qr_empty[*] qr_ovf[*] delivery_words[*] delivery_v[*] r_v r_m[*] r_d[*]}
set_io_pin_constraint -group -region left:* -pin_names {clk rst_n go endpoint_rearm_ready rank[*] pf[*] context_operation[*] context_phase[*] qr_pop[*] rb_pop[*] dq_own_pop dupe issue_o owner_quiet context_fault_o}

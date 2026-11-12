# Form D (OT_KSH_PFREE) out_data audit while out_v = 0 (HBM-CORES-B 11-11, v700685__wcnt2pf)

D changes u_a, u_b, u_e out_data only while out_v = 0 (head loads on !head_valid || out_r, tail on !tail_valid, no reset gate). Valid-masked EQ proven.

Internal consumers (all valid-qualified):
- u_a.out_data -> a_d -> b_in_d: used only when a_v (b_in_v = ... st==NORM && a_v); u_b data register is loaded but only meaningful with b_in_v.
- u_e.out_data -> e_d: e_bad and w_addr only under w_push = wb_st && b_in_v && b_in_r; e_r = w_more && b_in_r.
- u_b.out_data -> b_d: rd_beats / b_pop_grp need b_v (b_pop = b_v && c_k_rdy); drained/wdrained use b_v.

Pin groups:
- g_kr_* (u_d): not changed (u_d is the SRDL skid, EQ).  fill_*, fault, w_k_*, g_k_*: not changed.
- **c_k_we, c_k_addr, c_k_len, c_k_tag, c_k_wstrb, c_k_wdata (u_b.out_data, 340 bits x 4 lanes): CHANGED while c_k_v = 0.**
  The pin value can differ from the previous kit in every cycle in which c_k_v = 0.  Sole consumer: ot_hbm_svc_pc_ctrl_leaf_cfg_h9b
  (and the KREG skid variant): data lands in unconditional pin flops, accepted only when kp_v = kv_q && k_rdy_seen, so function is unchanged.
  The visible difference is at the pins only (pin-level EQ/LEC against the previous core, parent bind contract).
Conclusion: one pin group (c_k_* data) is unmasked while invalid.  ASK DIE-HBM-100 before building.

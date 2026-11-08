# S81 RCK t16 vJ (S81-RCK-10, 2026-11-07)

One form for the four classes left open by the vI PLACE probe (epyc4 scratch3/claude/s81-rck-9/vi_probe):
RM write side (rp_g2 -> we_q -133), CLAND ring (tc -> s_d -710), DSYN (S_q -> RiBM units -663), LPL (rq -> b -538).
All changes are opt-in defines (default elaboration unchanged):

| define | file | change | cycles |
|---|---|---|---|
| OT_S81_RM_WFULL8 | rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv | full/ge6 = rp_g2 == registered gray targets; 8 kept group copies | +1 wclk at RM input |
| OT_S81_CLAND_WCHK | rtl/common/ot_dp_clk_landing.sv | ring WCHK=1 + local training-reset flop | ready/fault +1 clk, data 0 |
| OT_S81_KP4_SYN_LOCAL | ot_s81_kp4_dsyn.sv, ot_s81_kp4_bm.sv, ot_s81_kp4_ddly.sv | per-unit S copy + load copies, NG 8, registered k_*; DD 57 | +2 rck decoder |
| OT_S81_LPL_CHUNK | rtl/common/landed_parent/ot_pl_land.sv | <=24-bit local rings (ot_pl_land_local_w/r) | 0 |

ot_pdie_serdes.sv also carries Codex RM_LOCAL4 (codex/rck-rm-local-1551@1de2d3e0898, opt-in, used by the vI kit).
Proofs (Verilator 5.032, vrun.sh): rm/ lock-step vs RM_LOCAL4 fed one wclk later + 4 mutants; cland/ lock-step vs the
vI landing at 6 phases + 3 mutants; dec/ lock-step of ot_s81_kp4_dec_native_flat_lp with the real KP4 encoder vs vI
(outputs 2 ck later) + 3 mutants.  Kit-only change (not here, bound.sv is generated): u_bin_coll_i0 reset from tap t33.

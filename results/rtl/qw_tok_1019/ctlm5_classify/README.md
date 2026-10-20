# QW-CTLM5 10-19: classification of the qfd_tt_ctlm_dv safe3/safe4 regressions and gate FAILs (Verilator 5.050, fleet)

1. **prog_m0_landed LANDED_LOCKSTEP 1254/18068** (REFILL-1725, safe3/4 RTL): stale bench offsets, not RTL. tb_qfd_tt_ctlm_prog /
   tb_mu_opseg_dv (TB_LANDED) hard-coded the MU-DQ-CTLMCLK offsets (outputs +6, inputs +6, tl +3); QW-CTLM3's D2/K1 rings made
   them +4 / +4 / +2 (lp record compiler block). The benches now read the record (fd44e2a46): c5a_ctlm_rest_and_mut36 -> 18070/0.
2. **opseg MUT0 'd2d_ctx C1 mu faulted' (opf 80546)**: the ctlm fresh-context guard qfd_mu_context_guard (c22e7e793) is right.
   d2d_ctx_guard_trace: runtime record for filler 1 loaded at 68136 (GLD) after the in-flight token's last consumer (SEG 64705);
   its result write at 80544 (GRW, pending=0010) overwrote the fresh tok/pos before any EMB/SEG consumed it (GCN 80545) -> the
   context would be lost. Guard-off mutant 36 PASSes. Fix: the bench's compiler placement rule (rt_records): a record lands so a
   same-filler consumer reads it before that filler's next result (cc2a4097a). RTL unchanged; run_mu_opseg pass+mut PASS.
3. **kvctx**: tb_mu_kvctx.f lacked qfd_mu_context_guard.sv (fixed 0f9f2896d, builds); the positive still FAILs C10/C8 because
   tb_mu_kvctx instantiates the ctlm without FCTX / CTX_SRC (bench vintage; QW-TOK3's CAL-mode kvctx bench is the current one).
4. **clock_rule 'per-root measurement coverage differs from clock_ports'** (all four gates): ck_insertion.py aborted on the h16c
   raw clock pin u_hr/ck_pm0 (no ETM arcs, 609270c0a rule) -> no GATE_CK_DOMAIN. Tool fix (claude/qw-ctlm5-tools-1019 83c224733).
   Re-measured on the safe4 CTS db (safe4_ck_insertion_fixed_tool): ck_core boundary TT 844.8-1036.4 / FF 698.3-864.6, ck_hr
   boundary TT 311.1-558.8 / FF 255.1-459.8 -> the hidden verdict is a pin-flop spread FAIL. safe4_pin_flop_arrivals_tt: the
   1,088 tl pin flops alone span 886.6-1036.4 (rst_n root flop 844.8, N face); hr pin bands N 455-498, S cmd/hr 515-559.
5. **cross_clock hr->core -158.1 ps** (safe4_xclk_worst_path): ck_hr launch 1010.8 vs ck_core capture 803 (+207 ps: ck_hr is
   co-timed with the h16c ck_head reference), plus a 346 ps buffered wire inside u_lpl_5_r (ss5), on D2/K1's 1T window with the
   210 ps inter-clock reserve. safe5 takes D4 / K2 + the LANDING-CONTRACT L5 multicycle.
Scripts: xpath.tcl / pinflops.tcl (OpenROAD in openroad/orfs on the safe4 gate's 4_1_cts.odb).

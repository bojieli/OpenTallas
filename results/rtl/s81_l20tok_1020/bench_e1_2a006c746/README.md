# S81-L20TOK bench receipts, source claude/s81-l20tok-1020 @2a006c746 (dsdv_idx_rg ENG=1, SQD=256), Verilator 5.050 on ot-epyc6
- e1_base IDXRD_CAMPAIGN PASS: pass_small/l2/l20/g2048/p3/open6 PASS, fail_late FAIL as required; T0 sweep 250/300/350 PASS
  (pass_l20 hdr_to_last as e0_reg 16,895 at T0 400 -> no READER_T0 re-price needed).
- e0_reg (ENG=0 record) IDXRD_CAMPAIGN PASS.
- mutants m1..m6: each IDXRD_CAMPAIGN FAIL (nerr / slice_err / negative latency) = caught; fail witnesses e1_m*.client.log.
- Behaviour only: ENG1 native census still FAILS (276 nets > 32, max 3892) -> reader native32 successor owed before any gate.

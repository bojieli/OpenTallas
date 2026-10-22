# QW-KVCTX 10-19: mu_kvctx_cal_e2e 0/108 filler native contexts = STALE BENCH (no RTL regression)

Fleet ot-epyc6, Verilator 5.050, `run_mu_kvctx.sh WORK pass|mut`.

- main_repro/ (origin/main ab0c6fada): mu_image OK; positive FAILS C10 (filler native contexts 0 vs 108; user-0 contexts
  mu 0 vs solo 1) + C8 (CTXU None). Cause: tb_mu_kvctx.sv built qfd_tt_ctlm_dv with CTX_SRC 0 / FCTX 0, forced
  dut.c_ctx / c_ctxld and logged neither LCV nor CTXU; the shared mu_opseg_bench.check_case gained C10 (b97041178,
  MU-DQ-BOOTCTX FCTX) and C8 (MU-DQ-D2DUSER) after the bench was written. The earlier PASSes (QW-TOK3 dedf4c794,
  KV-TXDP c903d60e1) sit on bases without b97041178.
- fix/ (claude/qw-kvctx-1019 fa5162b97): the ctlm runs CTX_SRC 1 FCTX 1 (die_params) with the leaf on the
  REAL ctx_x port (pin register + same-filler load rule, no force), LCV + C8 probe as tb_mu_opseg_dv; the image's
  DW5 / DW6 carry a valid EMPTY-mask record (the seal check faults on plain 0, which the force used to hide), so the
  fillers' contexts still come only from the KV die. Positive MU_KVCTX_PASS (C10 108 = 60 / 30 / 18 per filler, C8
  0 bad); mutants k1 k2 k3 r1 c1 all MU_KVCTX_FAIL. MU_KVCTX BENCHES: PASS.

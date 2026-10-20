# Qwen MU combined-commit regression

Source `0e6795834` (merged as `3fd57606f`); Verilator 5.050. Snapshot 2026-10-19T10:49:43-07:00.

41 / 44 legs have terminal results as expected; 1 unexpected; 2 remain pending. This snapshot is not a full regression PASS.

Outer shell exit 0 alone does not validate a mutant. The table checks the behavioral output for nested amix/adopt_slice runs. SIGTERM/143 is infrastructure failure, never expected mutant failure. FACES mutant r3 supersedes r0; collective r2 supersedes the hollow cases=0 r0. Pending output is excluded because the generic collector can otherwise prefer an old completed copy.

Scope excludes OPSEG full2 steady-state rate and the real MU.TOK.QW run gated on B3-B5. DHUSER mutants report FAIL in their text while exiting 0 by design. ctlm_rest records its existing lp_m4 observability waiver.

| Leg | Expect | Actual | Status |
|---|---|---|---|
| [amix_F0](evidence/runs/amix/runs/F0_nu1_ag.out) | PASS | F0_nu1_ag.out: bench2 (j) MUT=0: PASS 3/3; # exit 0 | AS EXPECTED |
| [amix_F1](evidence/runs/amix/runs/F1_nu1_ag.out) | PASS | F1_nu1_ag.out: bench2 (j) MUT=0: PASS 3/3; # exit 0 | AS EXPECTED |
| [amix_F2](evidence/runs/amix/runs/F2_nu1_ag.out) | PASS | F2_nu1_ag.out: bench2 (j) MUT=0: PASS 3/3; # exit 0 | AS EXPECTED |
| [amix_FACES1](evidence/runs/amix/runs/FACES_mut0_nu1.out) | PASS | FACES_mut0_nu1.out: FACES MUT=0: PASS; # exit 0 | AS EXPECTED |
| [amix_FACES4](evidence/runs/amix/runs/FACES_mut0_nu4.out) | PASS | FACES_mut0_nu4.out: FACES MUT=0: PASS; # exit 0 | AS EXPECTED |
| [amix_G0](evidence/runs/amix/runs/F0_nu4_ag.out) | PASS | F0_nu4_ag.out: bench2 (j) MUT=0: PASS 3/3; # exit 0; F0_nu4_m_s21.out: bench2 (m) MUT=0: PASS 8/8; # exit 0; F0_nu4_m_s22.out: bench2 (m) MUT=0: PASS 8/8; # exit 0; F0_nu4_n.out: bench2 (n) MUT=0: PASS 2/2; # exit 0 | AS EXPECTED |
| [amix_G1](evidence/runs/amix/runs/F1_nu4_ag.out) | PASS | F1_nu4_ag.out: bench2 (j) MUT=0: PASS 3/3; # exit 0; F1_nu4_m_s21.out: bench2 (m) MUT=0: PASS 8/8; # exit 0; F1_nu4_m_s22.out: bench2 (m) MUT=0: PASS 8/8; # exit 0; F1_nu4_n.out: bench2 (n) MUT=0: PASS 2/2; # exit 0 | AS EXPECTED |
| [amix_G2](evidence/runs/amix/runs/F2_nu4_ag.out) | PASS | F2_nu4_ag.out: bench2 (j) MUT=0: PASS 3/3; # exit 0; F2_nu4_m_s21.out: bench2 (m) MUT=0: PASS 8/8; # exit 0; F2_nu4_m_s22.out: bench2 (m) MUT=0: PASS 8/8; # exit 0; F2_nu4_n.out: bench2 (n) MUT=0: PASS 2/2; # exit 0 | AS EXPECTED |
| [amix_H1](evidence/runs/amix/runs/F0_nu1_h.out) | PASS | F0_nu1_h.out: bench2 (h) MUT=0: PASS 12/12; # exit 0 | AS EXPECTED |
| [amix_H4](evidence/runs/amix/runs/F0_nu4_h.out) | PASS | F0_nu4_h.out: bench2 (h) MUT=0: PASS 12/12; # exit 0 | AS EXPECTED |
| [amix_N0](evidence/runs/amix/runs/NEG_n_am7_f0.out) | FAIL with behavioral witness | NEG_n_am7_f0.out: bench2 (n) MUT=0: FAIL 1/2; # exit 1 | AS EXPECTED |
| [amix_N1](evidence/runs/amix/runs/NEG_n_am7_f1.out) | FAIL with behavioral witness | NEG_n_am7_f1.out: bench2 (n) MUT=0: FAIL 1/2; # exit 1 | AS EXPECTED |
| [amix_N2](evidence/runs/amix/runs/NEG_n_am7_f2.out) | FAIL with behavioral witness | NEG_n_am7_f2.out: bench2 (n) MUT=0: FAIL 1/2; # exit 1 | AS EXPECTED |
| [coll_mu_bi](evidence/out/coll_mu_bi.out) | PASS, cases>0 | coll_mu_bi.out: case mu_window_ref_user0 kind=pos latu=53 lats=378 phi=0 xu=0 xs=0 mutant=- FAIL mismatches=22512 extra=0 out_err=0 cmd_bad=0 coll_fault=11111111 issuer_fault=00000000 die_fault=11111111 words_out=22528 meas_lu=53 meas_ls=378 pr_overlap=0 compiled_span=35227; COLL_TP8SL FAIL failed=mu_window,mu_window_ref_user0 | UNEXPECTED job exit 1 |
| [coll_mu_bi_mut_rank](evidence/out/coll_mu_bi_mut_rank.out) | negative-control PASS, cases>0, expected FAIL witnessed | coll_mu_bi_mut_rank.out: case mu_window kind=pos latu=53 lats=378 phi=0 xu=0 xs=0 mutant=OT_TP8S_MUT_RANK FAIL (expected FAIL) mismatches=61432 extra=0 out_err=0 cmd_bad=0 coll_fault=11111111 issuer_fault=00000000 die_fault=11111111 words_out=61440 meas_lu=53 meas_ls=378 pr_overlap=0 compiled_span=38138; COLL_TP8SL NEGATIVE-CONTROL PASS cases=1 latu=53 lats=378 | AS EXPECTED |
| [coll_mu_bi_mut_rlat](evidence/out/coll_mu_bi_mut_rlat.out) | negative-control PASS, cases>0, expected FAIL witnessed | coll_mu_bi_mut_rlat.out: case mu_window kind=pos latu=53 lats=378 phi=0 xu=0 xs=0 mutant=OT_TP8S_MUT_RLAT FAIL (expected FAIL) mismatches=61432 extra=0 out_err=0 cmd_bad=0 coll_fault=11111111 issuer_fault=00000000 die_fault=11111111 words_out=61440 meas_lu=53 meas_ls=378 pr_overlap=0 compiled_span=38138; COLL_TP8SL NEGATIVE-CONTROL PASS cases=1 latu=53 lats=378 | AS EXPECTED |
| [coll_mu_bi_neg_overlap](evidence/out/coll_mu_bi_neg_overlap.out) | negative-control PASS, cases>0, expected FAIL witnessed | coll_mu_bi_neg_overlap.out: case mu_window_neg_overlap kind=pos latu=53 lats=378 phi=0 xu=0 xs=0 mutant=- FAIL (expected FAIL) mismatches=59384 extra=0 out_err=0 cmd_bad=0 coll_fault=11111111 issuer_fault=11111111 die_fault=11111111 words_out=59392 meas_lu=53 meas_ls=378 pr_overlap=0 compiled_span=38138; COLL_TP8SL NEGATIVE-CONTROL PASS cases=1 latu=53 lats=378 | AS EXPECTED |
| [ctlm_mu](evidence/out/ctlm_mu.out) | positives PASS; defined mutants FAIL; suite succeeds | ctlm_mu.out: MU_CTLM BENCHES: PASS; # exit 0 | AS EXPECTED |
| [ctlm_nsl12](evidence/out/ctlm_nsl12.out) | positives PASS; defined mutants FAIL; suite succeeds | ctlm_nsl12.out: MU_CTLM BENCHES: PASS; # exit 0 | AS EXPECTED |
| [ctlm_rest](evidence/out/ctlm_rest.out) | positives PASS; defined mutants FAIL; suite succeeds | ctlm_rest.out: MU_CTLM BENCHES: PASS; # exit 0 | AS EXPECTED |
| [head](evidence/out/head.out) | positives PASS; defined mutants FAIL; suite succeeds | head.out: user_pass_s2 want=PASS OK :: TB_USER_EVENT PASS MUT=0 seed=2; overall rc=0 | AS EXPECTED |
| [host](evidence/out/host.out) | MU1 PASS; cm1-4/hm1-4/rm1-2 FAIL; 13 MU0 benches identical | host.out:   tb_qkd_host_prompt_ue identical; # exit 0 | AS EXPECTED |
| [hroot](evidence/out/hroot.out) | positives PASS; defined mutants FAIL; suite succeeds | hroot.out: MU_HROOT tb_mu_lprg_lockstep_s2 rc=0: PASS MU_LPRG_LOCKSTEP seed=1234 mu0_cmp=5102 mu1_cmp=5098 events=807 (MU0 == original; MU1 user 0 gap 0 == original); # exit 0 | AS EXPECTED |
| [kv](evidence/out/kv.out) | positives PASS; defined mutants FAIL; suite succeeds | kv.out: MU_KV tb_mu_kv_writer_rows rc=0: PASS MU_KV_WRITE_ROWS users4 x layers36 x positions8192 (stage-interleaved) words4718592 sectors9437184 unique alias0 inverse{user,layer,pos,kind,dim}+raw exact; MU1 == plain writer outside row[9:8]; MU0 wrapper == plain writer; # exit 0 | AS EXPECTED |
| [opseg_mut](evidence/out/opseg_mut.out) | positives PASS; defined mutants FAIL; suite succeeds | opseg_mut.out: MU_OPSEG BENCHES: PASS; # exit 0 | AS EXPECTED |
| [opseg_pass](evidence/out/opseg_pass.out) | PASS | opseg_pass.out: MU_OPSEG BENCHES: PASS; # exit 0 | AS EXPECTED |
| [sl_DHUSER](evidence/runs/adopt_slice/runs/dhuser_fieldmap.out) | positives PASS; defined mutants FAIL; suite succeeds | dhuser_fieldmap.out: seq_dh field map OK (h_start [42], stage [41:36]); dhuser_mut1.out: TB_DHUSER FAIL MUT=1 3494 mismatches; # exit 0; dhuser_mut2_slip.out: TB_DHUSER FAIL slip not detected (det -1); # exit 0; dhuser_mut3.out: TB_DHUSER FAIL MUT=3 349 mismatches; # exit 0; dhuser_pass_s11.out: TB_DHUSER PASS MUT=0; # exit 0; dhuser_pass_s7.out: TB_DHUSER PASS MUT=0; # exit 0; dhuser_slip_pass.out: TB_DHUSER PASS slip detected 2 h_starts after the slip (NU1 err 0); # exit 0 | AS EXPECTED |
| [sl_F0_nu4_m_gap16](evidence/runs/adopt_slice/runs/F0_nu4_m_gap16.out) | PASS | F0_nu4_m_gap16.out: bench2 (m) MUT=0: PASS 8/8; # exit 0 | AS EXPECTED |
| [sl_F0_nu4_m_gap20](evidence/runs/adopt_slice/runs/F0_nu4_m_gap20.out) | PASS | F0_nu4_m_gap20.out: bench2 (m) MUT=0: PASS 8/8; # exit 0 | AS EXPECTED |
| [sl_F0_nu4_m_gap24](evidence/runs/adopt_slice/runs/F0_nu4_m_gap24.out) | PASS | F0_nu4_m_gap24.out: bench2 (m) MUT=0: PASS 8/8; # exit 0 | AS EXPECTED |
| [sl_F0_nu4_m_gap30](evidence/runs/adopt_slice/runs/F0_nu4_m_gap30.out) | PASS | F0_nu4_m_gap30.out: bench2 (m) MUT=0: PASS 8/8; # exit 0 | AS EXPECTED |
| [sl_FACES_mut11_nu4](clients/legs_r3/sl_FACES_mut11_nu4.log) | FAIL with behavioral witness | Existing fleet job still active; no terminal behavioral verdict | PENDING |
| [sl_FACES_mut12_nu4](clients/legs_r3/sl_FACES_mut12_nu4.log) | FAIL with behavioral witness | Existing fleet job still active; no terminal behavioral verdict | PENDING |
| [sl_NEG_i_mut11_nu4](evidence/runs/adopt_slice/runs/NEG_i_mut11_nu4.out) | FAIL with behavioral witness | NEG_i_mut11_nu4.out: bench2 (i) MUT=11: FAIL 1/3; # exit 1 | AS EXPECTED |
| [sl_NEG_j_mut12_nu4](evidence/runs/adopt_slice/runs/NEG_j_mut12_nu4.out) | FAIL with behavioral witness | NEG_j_mut12_nu4.out: bench2 (j) MUT=12: FAIL 1/3; # exit 1 | AS EXPECTED |
| [sl_NEG_m_am1](evidence/runs/adopt_slice/runs/NEG_m_am1.out) | FAIL with behavioral witness | NEG_m_am1.out: bench2 (m) MUT=0: FAIL 7/8; # exit 1 | AS EXPECTED |
| [sl_NEG_m_am2](evidence/runs/adopt_slice/runs/NEG_m_am2.out) | FAIL with behavioral witness | NEG_m_am2.out: bench2 (m) MUT=0: FAIL 2/8; # exit 1 | AS EXPECTED |
| [sl_NEG_m_am2_e](evidence/runs/adopt_slice/runs/NEG_m_am2_e.out) | FAIL with behavioral witness | NEG_m_am2_e.out: bench2 (m) MUT=0: FAIL 2/8; # exit 1 | AS EXPECTED |
| [sl_NEG_m_am3](evidence/runs/adopt_slice/runs/NEG_m_am3.out) | FAIL with behavioral witness | NEG_m_am3.out: bench2 (m) MUT=0: FAIL 6/8; # exit 1 | AS EXPECTED |
| [sl_NEG_m_am4](evidence/runs/adopt_slice/runs/NEG_m_am4.out) | FAIL with behavioral witness | NEG_m_am4.out: bench2 (m) MUT=0: FAIL 2/8; # exit 1 | AS EXPECTED |
| [sl_NEG_m_am6_rootnoclr](evidence/runs/adopt_slice/runs/NEG_m_am6_rootnoclr.out) | FAIL with behavioral witness | NEG_m_am6_rootnoclr.out: bench2 (m) MUT=0: FAIL 2/8; # exit 1 | AS EXPECTED |
| [sl_NEG_m_gap12_stnpend](evidence/runs/adopt_slice/runs/NEG_m_gap12_stnpend.out) | FAIL with behavioral witness | NEG_m_gap12_stnpend.out: bench2 (m) MUT=0: FAIL 1/8; # exit 1 | AS EXPECTED |
| [sl_NEG_m_nu1_w](evidence/runs/adopt_slice/runs/NEG_m_nu1_w.out) | FAIL with behavioral witness | NEG_m_nu1_w.out: bench2 (m) MUT=0: FAIL 2/8; # exit 1 | AS EXPECTED |
| [tok](evidence/out/tok.out) | positives PASS; defined mutants FAIL; suite succeeds | tok.out: MU_TOK_SMOKE BENCHES: PASS; # exit 0 | AS EXPECTED |

## Resolution 10-19 11:45 (QW-MUREG)

- coll_mu_bi: STALE RECIPE. The old dv2f14bi fixture fails bit-identically (61424/22512 mismatches, coll+die faults 11111111) on current
  SAFE source too; the release-die dv2f18dh2 + SAFE hard fixture PASSES (codex/qwen-mu-current-1019 e6b9c55f2). Re-pointed in
  claude/qw-mureg-cur-1019 (cases.py mu_bi + negatives share _MUC; old fixture kept as *_dv2f14bi_diagnostic).
- coll_mu_bi_mut_rank / _mut_rlat / _neg_overlap above are HOLLOW witnesses (same all-die fault signature as the failing positive).
  Re-witnessed on the current fixture: rank 42288 / rlat 30720 mismatches with zero faults, neg_overlap issuer_fault 11111111;
  results/rtl/mu_qwen_current_1019/qw_mureg_negatives on claude/qw-mureg-cur-1019 5f5080c86.
- Still pending: sl_FACES_mut11_nu4 / sl_FACES_mut12_nu4 (r3, ot-pve1, single cc1plus each >1h40 CPU, progressing; not restarted).

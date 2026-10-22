# ROOT4-S81MERGE receipts (10-19), branch claude/root4-s81smwire-main-1019
Fleet ot-epyc7, Verilator 5.050. Source: git archive of 2a362ccf0, ot_s81sl_xr.sv then updated to 4fa702e19 (HB 0 only:
sos_c not generated on C1; e2e_base and GEN ran before that copy -- HB 1 logic identical).
- e2e SMWIRE: base route 1 / 2 PASS, SMW_MUT 1-5 FAIL, TARGET_MUT 1-5 CAUGHT (E2E_DONE bad=0); RTL mutants ORDER, CIXB FAIL as required.
- regress (run_regress.sh): xr HB0/HB1 PASS + hops/row/porder/nocol/bwide FAIL, rstop PASS + tiercol FAIL, pvrd PASS + 2 mutants FAIL,
  svc_rs / svc_rs_entry die lint 0 errors (REGRESS_DONE bad=0); XR_FOREG=1 xr HB0/HB1 PASS, bwide FAIL.
- MU_HWIN_GATE PASS (base, BADRT, mut3/4 detected) + LEP_MU_DIE_LINT PASS.
- GEN mu5 strict die_port_bind PASS 42 masters / 9,868 inst, unread 0, output open 0, all counters 0 (gen_mu5m/bind/port_bind.log).
- pytest tools/s81_dv: identical failure set on this branch and origin/main 34428d840 (test_dv_layer_compile 2 FAIL,
  layer_prog/test_final_ffn_transport 8 ERROR): no regression from the merge.

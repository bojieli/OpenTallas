# PRECHECK-DERIVED-DROP handoff (Opus 5.5; COORD split 11-23 21:36 PST)
Job: PRE FAIL classes for derived plan sections a re-floor / grow / tap rewrite leaves stale. ONE job.
## Landed (main): e5b0faacef (RSTREACH + DERIVEDNAME), 728cc0176d (die_relays parent check; bind-repaired refs WARN), ea2c017401 (rr_t + collector nodes WARN)
- tools/die_plan/derived_drop.py + test_derived_drop.py (16 tests); plan_gate_pre hook (CLASSES, base = remap base, bind RTL = --elab-dir else <plan dir>/bind_of_record).
- DERIVEDNAME b oracle = landing_remap --resets rstnode (COORD ruling). Die relays vs reset_tree.wf_solve (COORD 4th case).
- Lane clones: intel2 (push clone); epyc10/epyc9/epyc7 = main + files copied from localhost scratchpad.
## Proofs (runs/<TAG>.log; dd_run.sh TAG PLAN TREE BASE [ELAB])
- KV epyc10: A3g b258e3e34f22 FAIL 15 pv (13 bound + pv/v8 plan) + hroot 27 finals + io_ft_v1 5 chains; 3d130f381902 pv PASS; R1 e186567f8dd6 DERIVEDNAME PASS.
- S81 epyc9: c7a tail 90698b2ec067 FAIL svc_lo t1 30/t6 4/t7 43/rs_w 6; LOSTART a39888d9ebe1 svc_lo PASS; c8 24_tgr5 ba9b277a852b FAIL die_relays 3/38; 25_strip 11f93cb045e9 PASS.
- HEAD epyc7 r18g: 1 FAIL hd_lep0N_w reader_start coll_i0:0 <- rst_rl_283 410 um.
- QC epyc7 C1b 62ce8aba0292: v3 had su_c rr_t FAILs (false: strict bind clean) -> ea2c017401 WARN; v4 rerun pending.
## Findings posted (22:05, 22:27): KV hub_C/hub_Wi/sys_SD FSTART reach; hroot/hub_Wo/pv_v1n START raw; hg/hgi/pc/hub raw-branch base legs; S81 c8 ~27 leaf/kv_leaf/c1x_C/serdes START raw.
## Cost: PRE adds ~0.5 min KV, ~10 min S81, ~5 min QC (tree solves; OT_DERIVED_BUDGET_S default 900).

# S81-SVC-TIED handoff (Opus 5.5; fresh lane 11-24 08:2x PST). Brief: localhost scratchpad resume_1124b.txt + s81_open_brief.txt + rules.txt.
Job: clear the S81 svc strict-bind class (TIED 486,192 bits on 16 svc types + OT_SVC_ATTCUT 10 NOEFFECT / 1 CONFLICT); one row PRE + scoped strict on c9 -> ROW-REBASED to S81-ALLFIX-INT.
Work dir: E9 /srv/opentallas-scratch2/claude/s81-svc-tied (row/, pre/, c8fix/, abi_scan_c8.json).
## 08:5x findings
- TIED = bind ELAB defect: slang empty-blackbox import reuses the first instance port ABI. ENGINE row (SRX=7/ENG_XS/BCAST) adds ot_hdc_v41x_kreg (W 1..1040) + ot_hdc_v41x_dly (W 7..1040) in svc; c8 elab: 848/1072 kreg + 64/80 dly cells at the wrong width (kreg W=576 connected 1 bit) -> hcore.ib 575/576 const0 etc. B1 (SRX 0) tied 0. Die-wide census abi_scan_c8.json: only these 2 unlisted leaves mismatch (ot_pl_land_chunk_* listed; their 'vld' hits are scanner range-parse noise).
- FIX: asbuilt slang_parameterized_blackboxes += ot_hdc_v41x_kreg, ot_hdc_v41x_dly (row/asbuilt_run_c9_svctied.json f0b6dd61e18b = c9 a048b32bba7e + 2).
- ATTCUT: drop on the last 10 svc_hi (adopted INT draft rows/c8_attcut_drop10.DRAFT; row/svctied_attcut_drop10.ops.json 13da27e41f30). ON = functional break (S81-SVC-J9-CUT-ENG-reconcile bench: one-slice cut FAIL, uniform needs +2K dates). c9 plan + row = row/plan_c9_svctied.json 99f7d3042489 (verilog_defines only, 10 types).
- Running: E9 pre.sh (PRE base c9 vs c9+row, tree amd1_tree, rt 515889f6ef75); E9 c8fix.sh (c8 plan+drop, c8 asbuilt+2, fresh strict elab + scoped strict bind on all svc_* types). Note: c8fix installs 2 new files in INT amd1_tree (plan_svctied_c8_<sha>.json, native_bind/asbuilt_run_allfix2_svctied.json); ot-delete after.
- Next: c9 scoped strict on E11 c9seal_tree once sealed (or INT folds row into the c9 gate elab), then ROW-REBASED.
## 15:2x PST results
- c8fix elab ELAB_RC=0: every kreg/dly cell at its own width; type_defines NONE_NEEDED; in-elab PRE = 26 ANCHORDRY (base-identical, serdes, not mine). Standalone PRE base vs row: identical (only path-label diffs).
- c8fix scoped strict v1 (E9 c8fix_v1/, asbuilt +2 bb): TIED 486,192 -> 41,584, UNDRIVEN 0, n_errors 201 = TIED only. First bind run OOM-killed at EMIT j=8 (240G); reruns use OT_BIND_EMIT_J=2..3, --mem 220.
- Residue declared (gen_ties.py, 41 declared_ties rows, bit-exact vs srx_fused formula): tr_x.w_g 41,472 non-fused fill bits =0; kreg.d=1 112 bits = W1 reset relays u_rn/u_rn_a/u_rn_e/u_rs0.
- ROW v2: plan c9 99f7d3042489 + asbuilt c9 b23d94ffcd6e (row/asbuilt_run_c9_svctied2.json); c8 twin fbd98e560cd9. INT c9s gate runs f0b6 (v1): expect the same 201 TIED; swap v2 in (bind-only).
- Running: E9 c8fix_bind2.sh (v2 recheck, unit oth-ubuntu-3514937). Then: ROW-REBASED post, svc kit probes (svc_lo rs t3, svc_hi pvso_entry t1), ot-delete my 3 files in INT amd1_tree (plan_svctied_c8_*, native_bind/asbuilt_run_allfix2_svctied{,2}.json).
## 17:5x PST state
- DONE: scoped strict c8 v2 (24 svc types): BIND_RC=0 n_errors 0 (E9 c8fix_out/bind_report.json 5b2bf2c71a42). ROW-REBASED posted 17:21: plan c9 99f7d3042489 + asbuilt c9 b23d94ffcd6e. INT to swap b23d into c9s bind (bind-only); c9s runs f0b6 at EMIT_J=8 (OOM risk; my svc-only j=8 OOMed at 240G).
- FINDINGS 17:26: svc_width_gate checks only listed modules (blind to kreg/dly) -> PRECHECK-R3; c8s svc_hi 10 ATTCUT kits build the bench-FAIL cut form -> asked INT to cancel; c8s svc_lo kits adopted as probes.
- PROBE: intel2 unit svctied-svc-hi-dsdv-svc-pvso-entry--t1 (goal grt), launcher intel2 ~/tmp/s81-svc-tied/launch_probe.sh (+probe_types.txt), specs ~/tmp/s81-svc-tied/probe/. Tree E9 s81-svc-tied/trees/c8svctied (fork of c8seal_tree) + bind trees/c8svctied_bind. Uses --allow-bind-stale + INT specfix.py (KITWAVE-BINDOUT); bind_matches verified True with v2 asbuilt.
- Cleanup done: ot-deleted my 3 files in INT amd1_tree.
- Next: watch probe; when c9s bind with b23d lands, launch/adopt c9 svc kits (svc_hi route once L0-FIXTURES clears).

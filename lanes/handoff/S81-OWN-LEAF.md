# S81-SVC-TIED handoff (Opus 5.5; fresh lane 11-24 08:2x PST). Brief: localhost scratchpad resume_1124b.txt + s81_open_brief.txt + rules.txt.
Job: clear the S81 svc strict-bind class (TIED 486,192 bits on 16 svc types + OT_SVC_ATTCUT 10 NOEFFECT / 1 CONFLICT); one row PRE + scoped strict on c9 -> ROW-REBASED to S81-ALLFIX-INT.
Work dir: E9 /srv/opentallas-scratch2/claude/s81-svc-tied (row/, pre/, c8fix/, abi_scan_c8.json).
## 08:5x findings
- TIED = bind ELAB defect: slang empty-blackbox import reuses the first instance port ABI. ENGINE row (SRX=7/ENG_XS/BCAST) adds ot_hdc_v41x_kreg (W 1..1040) + ot_hdc_v41x_dly (W 7..1040) in svc; c8 elab: 848/1072 kreg + 64/80 dly cells at the wrong width (kreg W=576 connected 1 bit) -> hcore.ib 575/576 const0 etc. B1 (SRX 0) tied 0. Die-wide census abi_scan_c8.json: only these 2 unlisted leaves mismatch (ot_pl_land_chunk_* listed; their 'vld' hits are scanner range-parse noise).
- FIX: asbuilt slang_parameterized_blackboxes += ot_hdc_v41x_kreg, ot_hdc_v41x_dly (row/asbuilt_run_c9_svctied.json f0b6dd61e18b = c9 a048b32bba7e + 2).
- ATTCUT: drop on the last 10 svc_hi (adopted INT draft rows/c8_attcut_drop10.DRAFT; row/svctied_attcut_drop10.ops.json 13da27e41f30). ON = functional break (S81-SVC-J9-CUT-ENG-reconcile bench: one-slice cut FAIL, uniform needs +2K dates). c9 plan + row = row/plan_c9_svctied.json 99f7d3042489 (verilog_defines only, 10 types).
- Running: E9 pre.sh (PRE base c9 vs c9+row, tree amd1_tree, rt 515889f6ef75); E9 c8fix.sh (c8 plan+drop, c8 asbuilt+2, fresh strict elab + scoped strict bind on all svc_* types). Note: c8fix installs 2 new files in INT amd1_tree (plan_svctied_c8_<sha>.json, native_bind/asbuilt_run_allfix2_svctied.json); ot-delete after.
- Next: c9 scoped strict on E11 c9seal_tree once sealed (or INT folds row into the c9 gate elab), then ROW-REBASED.
11:4x PST:
- c9 already fixes t35/t50 (reset.in_sites y 10.272). All 20 leaf G0 errors covered by c9. 16 my types wait for c9 (t2 t22 t3 t35 t38 t43 t47 t50 t61 t65 t68 t70 t71 t72 t73 t9); 55 c8 (= INT probe-safe list exactly).
- C10-RTL-SYNC kv_leaf: row 6ef2516770b9 (E9 s81-own-leaf/rows/c10kv) carries fbcbcd14cf ca915a5022 c3ea0d5e30 (bug fix -> c9 suffix); a64d7d7813 d97edba9f3 opt-in -> next event. Posted to INT.
- c8 bind EMIT done 11:1x; raw allfix_c8_out is BIND_STALE for kits (asbuilt sha + types differ) until INT postbind+reseal. INT c8_post died (ot-run --priority plan refused). INT launcher stdin bug reported.
- My launcher: intel2 ~/tmp/s81-own-leaf/launch_leaf_c8.sh <list> (rt 69de849b3da1, lane S81-OWN-LEAF, host epyc9); list launch1.txt (55). Logs ~/tmp/s81-own-leaf/c8/. Use the re-sealed bind dir INT names (BINDOUT=...).
- Waiters: t26 J7 ot-wait; KITS GO poll (case-insensitive).

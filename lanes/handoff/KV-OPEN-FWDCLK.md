# KV-OPEN-FWDCLK handoff (Opus 5.5; family lane under KV-ALLFIX; started 2026-11-23 19:30 PST)
GOAL: FABLE-RC-KV 331a59eb item 2: KV forwarded landing clock (fclk) <= 330 ps on 16 types; ONE family row; ROW-REBASED to KV-ALLFIX with before/after per type. Due 22:30.
## Finding (19:35)
- Depth = landing master's own fclk insertion (clock_contract.json fclk pin, read by plan_timing_audit via core_clock_contract.load), not a tap.
- Exactly the 4 masters signed 11-14 are bad: kv_cland_w1057_ew_94a44 637.7 (hgi, hgi_v3/5/6/7/8, pv_v1n/v3n/v7/v1e), w1045_ns_ddbeb 617.6 (hgi_v6/7/8 ft8/ft4), w781_ns_9f2d9 604.9 (pv_v5/5n/5e/5ne), w288_ns_ad575 555.9 (pv_v6e/6ne). All 24 masters re-signed 11-15 = 96-208 ps.
## Fix = re-harden the 4 with the 11-15 recipe (tools/die_plan/cland_ring_master.py prep: related_clocks fclk), exact params, SAME module name/outline/pins (plan_of_record pins file, asserted equal).
- Work dir epyc11 L=/srv/opentallas-scratch2/claude/kv-open-fwdclk: wt (ot-lane-clone main f2156bb449), fwd_prep2.py + fwd_params.py, rk/<m>/kits/<m>_synth0, ck_contract.py (copy of kv-ringmac-r1).
- Then: ck_contract run tt/ff -> write clock_contract; export_view -> L/views/<m>; row ROWS_KV-OPEN-FWDCLK.py swaps lef/lib/budget_owner to physical/die_plan/qwen_kvsys/kvfwd_views_1123/<m> + clk tap insertion; overlay into tree; PRE + earlytap audit on base A2g (KV-ALLFIX: A2g = A2f + ISTPRICE).
## State 20:5x PST
- All 4 masters SIGNED on epyc11 (TT setup +160..+164, DRC 0, routed LEC EQUIVALENT; FF hold negatives are port->reg on rst_n/rst_xn only = parent-owned boundary). pins_sha256 + outline identical to the bound views.
- New fclk TT: w1057_ew 637.7->168.2, w1045_ns 617.6->149.1, w781_ns 604.9->138.0, w288_ns 555.9->119.7.
- Views: epyc11 + epyc8 L/views/<m>; overlay epyc8 L/overlay (72 files, overlay.sha256 sha 462b2b2b604e) -> tree path physical/die_plan/qwen_kvsys/kvfwd_views_1123/<m>.
- Row: epyc8 L/ROWS_KV-OPEN-FWDCLK.py sha 562aebc897e6 (frozen from L/mkrow.py + template); on A2g 3857747ea992 -> L/tmp/a2g_fwd.json 73acf583a2ee (28 cores on 16 types, 28 clk taps).
- Probe: epyc8 L/probe.sh TAG PLAN (PRE + plan_timing_audit on kv-allfix/launch_70b6f, view paths pointed at L/views); probe_base / probe_fwd; table L/table.py -> L/before_after.tsv.
- Killed my queued ot-tree-fork (epyc11 copy slots busy); epyc11 L/tree.forking-301399 (216 MB partial) needs ot-delete.
## State 20:1x PST: ROW-REBASED posted (hub f3220652)
- PRE PASS 0 on A2g+row (73acf583a2ee); audit over-330 rows 19 -> 0, failing types 22 -> 12, worst over 387.7 -> 25.0. Table lanes/handoff/KV-OPEN-FWDCLK-before_after.tsv.
- 4 sign-offs enqueued to AUTO-EXPORT spool on epyc11 (b21f134c, 85099792, 3a5b50de, fa3ffcdb).
- Open offer to FABLE-RC-KV: w1560_ew (208.4, < 330 but audit 200 rule FAIL on 11 hgi rows) re-harden with same recipe on request.
- Next: answer KV-ALLFIX compose questions; re-run row on A2h/newer base if asked (order-independent).
## State 20:2x PST: v2 posted (hub c270adbf)
- FABLE-RC-KV accepted FWDCLK (833b29ed). w1560_ew rebuild cancelled (COORD 20:1x: 200 ps fclk rule wrong, FLOW-OPS -> 330).
- v2 = ROWS_KV-OPEN-FWDCLK-HUBCTAP.py 98de46da0ec2 (hub_C core_taps early, 61 rows re-measured, 8 unmeasured to type tree). On A2g+FWDCLK+HUBCTAP dac02dd8ae1f: PRE PASS 0, audit FAIL rows 11 (w1560 200-rule only).
- Partial fork dir deleted (ot-delete). Lane done unless KV-ALLFIX asks for a re-run on a newer base.

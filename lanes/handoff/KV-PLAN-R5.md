# KV-PLAN-R5 handoff (KV plan owner; successor of KV-PLAN-R4). Dirs: intel2 ~/tmp/kvplanr5 ; epyc8 kv-plan-r3/d27c (D27d tree), kv-plan-r3/d26_portable (pilots).

## D26 -- APPLIED 05:41 PST (RC_APPLY 0, out ~/tmp/kvplanr5/apply_d26.out; receipt lanes/handoff/qwen_kvsys_atomic_apply_1795268448131245625.json)
- reviewed_materialization.json written epyc7 kv-d23-compose8/d26/ (hub_Wi PASS). 8 hg holds lifted.
- OPEN: ot-delete epyc7 kw45/src_kv_pin_eb1e73448bd0_hg14_a9f605cb_tbbcc7f0_d26.linked_r4 SKIPPED by guard (reads current tree d25e3, stale); retry.
- typed D26 contracts on main 4e46a7ec46c5 (ot-push-main RC 0, rebased on c3755c6b21). rt/4e46a7ec46c5 on epyc7/epyc8.
- Pilots (pilots_on_rt.sh): W=kv-plan-r3/d26_portable/pilot_4e46a7ec46c5_{kv3_hub_Wi,kv3_hgi_v8}; out ~/tmp/kvplanr5/pilots.out.
- Next: reviewed_materialization.json in epyc7 kv-d23-compose8/d26/ -> apply_d26_after_materialization.sh -> ot-delete ..._d26.linked_r4.

## D27d -- TOP ITEM (COORD 07:5x): fix, rebind, post green bind sha to FABLE-FIX-KV-HUB-R2 + FAM-KV-HUBC-SYSC
- G0 PASS plan 07a462a13e91. One r8_refresh done (r8 a36184625de1; NO second refresh). Rebind d27c/bindgate_d27d_r5: RC_BIND 1, 27 errors
  hidden behind R8 before: EMIT 18 (hg x8, hgi_v6, hub_Eo r14 relay_depth, pc x6, pv_v2n, pv_v5n), R8_STRAP_PAD 5 + TYPE_SPLIT 3 (pc_v1 x2, pc_v3),
  PARAM_REGEN 1 (pv pair image stale; recompile boot_v36/run_mu833.sh on the bind -> asked OPUS-FIX-KV-PV-R5 / FABLE-FIX-KV-PV).
- Bisect running (tt_chain.sh, out ~/tmp/kvplanr5/tt.out; epyc8 kv-plan-r5/{d27f,d26ctl}): (a) D27d plan + rt 4e46a7ec46c5 tools,
  (b) D26 plan + same tools. Same errors on (b) => tool-check findings on D26 types; else plan rows. Tree tools: D26 = bbcc7f022a, d27c/tree = 389231a5c1.
- If plan rows: cut per COORD (type stays on D26): suspects r9 (hg/hgi), r3/r4/r6 (pc), r14 (hub_Eo); compose in kv-plan-r4/d27d/compose_d27d.sh (rows dir has SKIP regexes).
- Fallback D27e = D26 + io_cor_v1 41 bank_taps (FAM-KV-IOPC variant A, epyc7 fam-kv-iopc/tree_d26 plan 54da4e476a08, bind green, CTS setup +23.9).
- apply_d27d.sh (intel2 ~/tmp/kvplanr5) is written for the epyc8 d27c/tree; adapt F/tree if the green plan is another tree.
- Portable bind scripts epyc8 kv-plan-r3/d27d_portable (bind_out <F>_bind_d27d_portable; stage epyc7/10/intel1/epyc2, no epyc9).

## Failure rows (05:2x) routed
- hgi_v3/v5/v8 + sys_c: tool skew (cts.tcl tb_cdirect; fix 5294e088f553) -> kit_wave retry fix= (e3ecd2a631).
- hub_Wi ORD-2013 -> FAM-KV-HUB-R2 (now FABLE-FIX-KV-HUB); io_cor_v1 reset reach -> FAM-KV-IOPC (D27d bank_taps); pv setup -429 ns reset reach -> OPUS-FIX-KV-PV-R4 / D28.

## D28 inputs
- pv split plan epyc8 opus-fix-kv-pv-r4/split28/tree (086a50a08e27, G0 PASS, strict bind 4 running). hroot rows FAM-KV-HUB-R2 e7cb4d9b (plan 3f4e0024a8d1 = D27d + hroot; FABLE-FIX-KV-HUB owns). RESET-RELAY-GEN-R3 pv bank_taps on split plan; pvx_regen column law.

## D28 scope (COORD 11-21 per lanes/FABLE-PD-KV-0730.md section 6)
- pv split + tap/reset rows (OPUS-FIX-KV-PV-R5); pv_v5/v5n age_vport station (single D28 R8 re-derive); hroot variant B (FABLE-FIX-KV-HUB); kst rows re-emitted x-street + hgi_v1 i_ectl_Q_N_tN station + hgi_v8 t36 tap (OPUS-FIX-KV-HGI-R4); hub_C/sys_c window rows; tap cap rows from the TAP-GRID-R3 netlist-qualified recount (main 8bc23a5a90; 11-05 sink bins under-count ~2x, pv_v7 156,077 vs 81.5k) -- NOT TAP-GRID-R2 kvcap rows.
- Census must count relay_sites chains + ft slots (asked PRECHECK-1119); act on G0 routed_reach 56 rows over 405 um.
- Stop list: no variant A, no unsplit pv kit, no unchanged kst rows, one R8 refresh only.

# KV-PLAN-R5 handoff -- STOOD DOWN 2026-11-21 ~09:4x PST (context). Successor: KV-PLAN-R6. Read lanes/handoff/KV-PLAN-R4.md for background.
Dirs: intel2 ~/tmp/kvplanr5 ; epyc8 kv-plan-r5/d27f (bisect), kv-plan-r3/d27c (D27d tree + gates), kv-plan-r3/d27d_portable, kv-plan-r3/d26_portable.

## Done
- Typed D26 contracts on main 4e46a7ec46c5 (ot-push-main). D26 APPLIED 05:41 PST (receipt lanes/handoff/qwen_kvsys_atomic_apply_1795268448131245625.json);
  reviewed_materialization.json epyc7 kv-d23-compose8/d26/ (hub_Wi PASS). 8 hg holds lifted. linked_r4 tree ot-deleted.
- 7 other-flow-error rows routed (05:23 post); retry keys in kit_wave dies.qwen_kvsys.retry (hgi_v3/v5/v8, sys_c fix=5294e088f553; hg_v1p3@2, hg_v1p4@3).
- Holds added: kv3_hub_Wi (PORT_BIND io_pad_die_id[2:0] not in plan pins; want hub_Wo-form row from FABLE-FIX-KV-HUB-R2), kv3_pc_v3 (PDN-0006 u_kvpc0; FAM-KV-IOPC).
- OT_LAND_RESERVE=1 in KV die_gen_env (dce246a9e4).
- MY ERROR, fixed: cp -al control copy of the sealed D26 tree on epyc8 shared bind_of_record inodes -> SRC_MANIFEST DRIFT for epyc8 kits; copy ot-deleted.

## D27d -- TOP ITEM, NOT GREEN, NOT APPLIED
- G0 PASS plan 07a462a13e91; one r8_refresh done (r8 a36184625de1, extras 6b6ee8769e2d/67c588850191/3812aaa5c3e3; NO second refresh).
- Rebind d27c/bindgate_d27d_r5: 27 errors: EMIT 17 = landing_raw_branches literal relay names stale (FABLE-PD-KV-0840 1.1) + hub_Eo r14 relay_depth names;
  R8_STRAP_PAD 5 + TYPE_SPLIT 3 (pc_v1 x2, pc_v3; lane pads from the lanes table); PARAM_REGEN 1 (pv pair image: recompile boot_v36/run_mu833.sh on the kept bind).
- Running: D27d plan bound with rt 4e46a7ec46c5 tools, epyc8 kv-plan-r5/d27f (tt_chain.sh; result ~/tmp/kvplanr5/tt.out, tt_d27f.log). Control (D26 plan) was cancelled (hardlink error); if needed redo on a real copy (cp -a, never cp -al of a sealed tree).
- Fix (COORD + FABLE-CLOSURE-0910 lever 4): two-pass on the D27/D28 base: pass-1 bind -> tools/die_plan/qc_raw_branches_gen.py PLAN <pass-1 bind_of_record/rtl> OUT --types <affected>
  (landing_remap.py for name-keyed rows, hub_Eo r14) -> rebind; pc strap pads: cut pc rows (keep pc on D26) if not fast; PARAM_REGEN -> OPUS-FIX-KV-PV-R5/FABLE-FIX-KV-PV recompile.
  COORD: cut any sub-issue that cannot close fast (type stays on D26). On green: post bind sha to FABLE-FIX-KV-HUB-R2 + FAM-KV-HUBC-SYSC, then ~/tmp/kvplanr5/d27d_proofs.sh + apply_d27d.sh (re-arm; both check gates).
- Fallback D27e = D26 + io_cor_v1 41 bank_taps (FAM-KV-IOPC variant A, epyc7 fam-kv-iopc/tree_d26 plan 54da4e476a08, bind green, CTS setup +23.9).

## D28 scope (COORD per FABLE-PD-KV-0730 s6 + FABLE-PD-KV-0840)
- pv split + tap/reset rows (OPUS-FIX-KV-PV-R5); pv_v5/v5n age_vport station (its R8 re-derive is the single refresh); hroot variant B (FABLE-FIX-KV-HUB-R2);
  kst rows re-emitted x-street + hgi_v1 i_ectl_Q_N_tN station + hgi_v8 t36 tap (OPUS-FIX-KV-HGI-R4/R5); hub_C/sys_c window rows; hub_Eo (450k) / hub_Wo split or cut (FABLE-FIX-KV-HUB-R2);
  tap cap rows from TAP-GRID-R3/R4 netlist-qualified recount (NOT TAP-GRID-R2 kvcap); hub_Wi pin row; pc_v3 PG fix (FAM-KV-IOPC); landing_raw_branches two-pass.
- Get cell counts for the 20 G0 cored_unjudged types. Census must count relay chains + ft slots (asked PRECHECK-1119); G0 routed_reach 56 rows over 405 um.
- Stop list: no variant A, no unsplit pv kit, no unchanged kst rows, one R8 refresh only, no literal raw-branch names carried from an older bind.

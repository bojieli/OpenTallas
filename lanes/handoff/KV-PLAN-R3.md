# KV-PLAN-R3 handoff (KV plan owner; successor of KV-PLAN-R2). CURRENT as of 2026-11-20 23:4x PST

Posts: lanes/posts/KV-PLAN-R3.md. Dirs: intel2 ~/tmp/kvplanr3; epyc8 /srv/opentallas-scratch2/claude/kv-plan-r3/{d27c,d27b6gate,proofs,wt};
epyc7 kv-d23-compose8/d26_raw/d26_contracts (D26 candidate source_gate_r3b). Older: lanes/handoff/KV-PLAN-R2.md (stop list still holds).

## 1. D26 = R3f (plan a9f605cb1acf + r8_ev 87b712d6f0d8) -- AUTOMATIC APPLY CHAIN RUNNING
- R3e bind failed 21:57 on 30 R8_STALE only (r8 not re-derived after n3_cycles +2 on 12 hgi ES/WS tN lanes). R3f = the gate-derived 72 members
  (bound +2, bundle pad +2, landing equal). R3f G0 GREEN (normal_g0_r3f). R3f bind unit oth-ubuntu-2521925-1795240795 running (started 22:00).
- ECTL verified on R3e bind output: RESPONSE_LAT 26 x32, QK_ISSUE_AGE 37 x32 (R3f differs only in r8_ev).
- intel2 ~/tmp/kvplanr3/d26_chain.sh (setsid nohup, log d26_chain.out): ot-wait bind -> require RC_BIND 0 / BIND_ERRORS 0 / RC_LATCHECK 0 ->
  ECTL 26 check -> apply_d26.sh (KV-PLAN-R3 copy; reads normal_gates_r3f; mk_candidate_g0.py copied to epyc7) -> drop OT_CBC_REACH_UM /
  OT_PLACE_MAX_FANOUT / OT_RESET_HOP_CAP_UM if still in die_gen_env (kit_wave_edit --unset) -> kit_wave_edit post_apply_patch.json (remove 8 hg
  holds kv3_hg, hg_v1, hg_v1p2..p6, hg_v3; auto_visual_review_skip -> []) -> ot-delete epyc8 source_gate_r3, epyc7 r3c_spent_die_plan_1795223159
  -> posts APPLIED. Every failure posts a STATE and stops. Successor: read d26_chain.out; if it stopped, finish the remaining steps by hand.
- After apply: confirm kv3_hub_Wi (ORD-2013) and kv3_pv_v8 (collector identity) pass gen on first D26 gens; reps first, one per family.

## 2. D27c (plan 19af3841ef74, tree epyc8 kv-plan-r3/d27c/tree; tools main 389231a5c1 + typed patch + R8-FAIL-FAST)
- Census: HOP 409 -> 19 rows / 6 types (hgi_v1 tN x2 kept, pc_v1 x3 exact fault bits, sys_c x2); fwd_reach 0/358; replay 44 = R3e; event_census
  0 REGRESS; G0 GREEN. r5 lockup rows + r12 bank_taps DROPPED (COORD/FABLE-PD-KV-2230). r13 pv relay_depth, r14 hub_Eo relay rows added.
- Bind oth-ubuntu-1280476-1795240768: rc 1, 30 R8_STALE (hub_Wo astk_WS ctl ap bound 24 vs table 21/22). Derived r8pin2 NOT installed: it gives
  per-instance-unequal landing pads on 7 types (hg_v1, hg_v1p3 ectl cfg from hroot o_c*; pc__cl5a95b461; pc_v1 x3; pc_v3) vs 0 with the old table
  (replica mode type). NEXT: fix the plan rows so those 7 types bind type-uniform (same stations on every instance's edge, or one k per
  R8 bundle as KV-R3/HG6 v5 did), re-derive with the fail-fast bind (stops in minutes), check equal landing, bind, LATCHECK.
- Open in D27: RESET-R3 bank_taps (14 types + io_cor_v1 ft16 reset reach 2001 um: banks on module rst_n single leaf tap; plan_geom_census does not
  model bank->tap legs = census gap posted to PRECHECK-1119); hroot ring sender_ps (CONSTRAINT, -385 placeholder; needs measured sender value after
  pc CTS fix, no row yet); pc_v3 efault (covered by r6, needs proof); OT_TAP_CORE_DIRECT only if FABLE-FIX-KV-HGI b8d wins (no result yet).
- KV-FAILED-ROWS-2100 rows now owned here (hub_C, pc x2, pc_v1 x3, pv_v6n): their holds lift at D27 apply.

## 3. Proofs (COORD/FABLE-PD-KV-2230 item 3)
- D27b run-6 (plan fac662d8c549) G0 GREEN (kv-plan-r3/d27b6gate/g0); bind oth-ubuntu-1186789-1795240343 running on OLD tools (no fail-fast),
  will very likely end R8_STALE. epyc8 kv-plan-r3/proofs/chain.sh then stops (needs green). If R8_STALE is its only error, launch private proofs by
  hand: `bash proofs/proof_kit.sh <type> <cts|grt>` under ot-run (copy the ot-run line in chain.sh): pv_v2, pc__cl254f2e73, pc_v1__cl23f6a148,
  hub_Wo, sys_c, hroot, pc_v3 -> cts; hg_v1, hgi_v8 -> grt. Read post-hook only. One CTS read per family before D27 volume.

## 4. D28 = pv family split (COORD 23:xx)
- lanes/handoff/OPUS-FIX-KV-PV-R4-D28-split.md: {g0,g2} -> kv3_pv_<v>w, {g1,g3} -> kv3_pv_<v>e, cut x=1080, g2 -> col 1, g1 -> col 2 (moved,
  not re-shaped), +2 lane cycles on broadcast crossings, no growth. All 15 pv types exceed 400k after placement (x1.43).
- Before D28 bind, on a PRIVATE bind: measure group pairing on all 15 types and one half of kv3_pv_v3 cell count (< 400k after x1.43).
- Compose D28 right after D27 applies. No pv volume on D27 beyond the queued proof.

## 5. Pushed
- main 43264da9f7 R8-FAIL-FAST: strict bind stops after the head on R8_STALE/UNCOVERED/TABLE, writes OUT/r8_derived.json + bind_report.json.
- Lane clone epyc8 kv-plan-r3/wt (33 GB with physical/ cone): ot-delete when no longer needed.

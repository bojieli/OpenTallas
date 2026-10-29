# TOK-HBM-5 (HBM whole-die token pass, 8 SM; successor of TOK-HBM-4)

## 2026-10-28 22:15 PDT START: base claude/tok-hbm-4-1028@b7c2fe3607, worktree intel2:/srv/opentallas-scratch2/claude/wt/tok-hbm-2. No live jobs inherited. C25b RESULT + bindfull S-role (q0-half) map not posted yet (c25b dir newest 21:59). Polling queue/PATH-HBM; nothing heavy meanwhile.

## 2026-10-28 23:02 PDT PROGRESS (claude/tok-hbm-5-1028@226d7a7346)
- Bench check per COORD FYI (Verilator 5.050 `x <= #d ck`): no intra-assignment delays in any TOK-HBM bench/RTL (results/tok_hbm_*_1028, tools/hbm_next, tools/hbm_b2, rtl/hbm_next) [CHECKED grep]; the whole-die vehicle bench will use none.
- bound_from_plan.py opt-in --side <c25b_side.json> (plan_sha256 must match, fail closed; plan tables win; 8 tests PASS).
- C25b 6b3a80cd + side (22:43): legs down/up NW 40/33 NE 40/34, reset SW/SE/NW/NE 50, root 17 (C25a reset_tree basis, UNCHECKED on C25b), provider<->root 0/0.
  Calendar on real MTP6 jobs: MISSING 10 -> 3: host_to_provider cycles, host_write_interval, plan commit [CHECKED own].

## 2026-10-28 23:26 PDT RESULT / PARKED (claude/tok-hbm-5-1028@a6cb3a86fd, on TOK-HBM-4 b7c2fe3607; opt-in/new files)
- Calendar on real MTP6 jobs with C25b side data: MISSING 10 -> 3 (host_to_provider, host_write_interval, plan commit) [CHECKED own].
  COORD 23:23: host_to_provider 4 cyc as DECLARED static boot path (multicycle in die STA), DIE-HBM-10 owns the calendar entry.
- Strict bind on C25b (DIE-HBM-10 c25b_after 23:19, instance map q0/q1 halves + PHY split) = 463 errors -> no vehicle possible yet.
  Census results/tok_hbm_5_1028/strict_blockers_c25b.json [CHECKED own from bind_report/bind_tied]:
  - UNMAPPED 32,810 cells = the 4 idx scorer quarters hb_idx__s_NE/NW/SE/SW (ot_hnx_idxn_quarter_with_keybuf): no plan core (plan has idx op/q/qctl per half, no scorer).
  - TIED 10,656 b undeclared: sm_NW0..7 attn_tile.gin 6400 b + attn_be.qin 2208 b (= SM attention inputs tied 0 in the composed top), selector in_line[2367:1184] 1184 b (S-half lines), 520 sm mux B, stl dn_i 164, hc_eng gathered_mix 64+...
  - 60 S-role nets need plan q0 copies (hcollks 8, hcollrs 2, hleaf 18, su 16, vmdel 16), UNPLANNED 30 (hub<->hub 2775/2730 b vs 2838 planned), TYPE_SPLIT 28, NW/NE_mca EMIT/EMPTY.
- Bench: no `<= #d` delays in any TOK-HBM bench [CHECKED grep].
- NEXT (successor TOK-HBM-6, when DIE-HBM-10 posts C25c + strict 0, likely >2 h): bound_from_plan.py --side on the C25c side/plan
  -> four_role_calendar.py --jobs results/tok_hbm_4_1028/jobs_mtp6_f0b93231.json --service results/tok_hbm_2_1028/service_segments.json
  -> fold_s_roles.py --map on the binder instance_map_c25b.json -> strict 0 -> fused_job217_emit --calendar -> programme -> epyc2 ot-run vehicle
  (no `<= #d` in the bench) -> nominal bit-exact + tok/s vs composer + must-fail mutant; svg_S*/selector S-half ties only if bit-exact. No live jobs.

## CODEX correction 2026-10-29
Inherited463-error verdict retained; several original diagnoses above were wrong. Actual32810unmapped decomposition frombindowner:8existingNorthSUsubtrees29198cells,2SFU200cells,4scorers3412cells; missing mapping isnot32810scorerlogic. SM gin/qin8608zero bits are intentional first/last-stage seeds, not missing producers. Selector paddingzero is intentional, but real8-entry lists were compressed into wrongquarters; corrected sparse-expansion adapter preserves quarterorder. No R7tieexemption. Oldhost4 isnot safequalifiedcontract: actual30FFtransport/LOADcapture31+unknownregionalK. C25csourceabe1936f3/typedside53ed20461 stillfailsqualifiedcalendarwhileKmissing; RAWsourceonlyrgap24/+9720FUSEDserviceedges, notoldrgap18. SouthSVGkey_lines remain active sourceobligation (actualMTPimage8INDEXN6records), cannotzero-specialize. Currentwork/optionalcomponentproofs recordedTOK-HBM-6; wholevehiclehelduntilactualsourceclosure/clockbound.

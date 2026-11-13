# RULES-REACH-1 handoff (Fable expert lane, rule R-REACH; COORD coordinates)

## Scope
Set rule R-REACH once (fanout + reach locality, face-net buffering): numbers, ONE family change in the die_plan
generator + G0, proof on KV kv3_hub_Eo + one S81 leaf, affected-type count per die, section in lanes/RULEBOOK-1113.md,
READY with branch + tests, stop.

## Where
- worktree epyc7 /srv/opentallas-scratch2/claude/rules-reach-1/wt, branch claude/rules-reach-1-1113 off origin/main.
- logs intel2 ~/rr1log/.

## Log
- 2026-11-13 03:30 lane started; evidence read (EXPERT-REVIEW-1, 11-13 verdicts, RELAY-PLACE-1, CLAND-RELAY-3,
  HBM-FORMS-1, REACH-FIX-2); worktree being cloned.
- 2026-11-13 03:57 worktree ready (branch claude/rules-reach-1-1113 off origin/main 055e36edab). Census (scan/census0.py on
  the wave plans): START origin -> ring > 405 um with NO reader START chain: KV 27 types, HEAD 2, QC 6, S81 0 (no START
  pin form). hub_Eo before-kit r2r classes (scratch rr/r2r_class.py): 3236/3869 = origin fan. Design: R-REACH-1 trunk
  sharing (clock.landing_reader_start.share_trunk; patched clock_landings/_verify/landing_place/schema, uncommitted),
  tool tools/die_plan/reach_rules.py (being written): start fan fix, fclk source, macro barrier, window census + G0 hook.
- 2026-11-13 04:13 code in wt (uncommitted): reach_rules.py (rules 1-4 check/fix/census CLI), share_trunk in
  clock_landings (reader+writer) / clock_landing_verify / landing_place / schema (+ reach_homes, budgets.r_reach), G0 hook
  in check.py (check "r_reach"), reach_fix classes 7/8, test_reach_rules.py (10 pass). KV proof: private plan
  epyc7 rules-reach-1/kv/por/plan_c.json = main plan_c + fix on kv3_hub_Eo/Wo (reader depth 9/8, writer 9/10, origin
  loads 3/11); strict bind running: ot-run epyc7 kv/bind_rr.sh a1 (log intel2 ~/rr1log/kv_bind_a1.log, out kv/bind_a1).
  Die checks: epyc7 rules-reach-1/scan/{kv,head,qc,s81}_check.{log,json,tsv} (scan/run_check.sh). Related pytest via
  ot-run: scan/pyt.sh -> scan/pyt.log.
- 2026-11-13 04:23 R-REACH-5 added (chain_even.tcl default: bin -> lane pad chains re-spaced when a hop > 405; gen_phys
  REACH_EVEN_CHAINS, budgets.r_reach_even). S81 proof: epyc9 rules-reach-1/s81/t21 = copy of wave kit ot_s81sl_leaf__t21
  a3 (7073a6b4a59), 3_*/4_* removed, face_flops.tcl + main FT-LANE delta (ov/ftlane_main.patch), chain_even hook
  appended; place via ot-run epyc9 (log intel2 ~/rr1log/s81_t21_place.log). Before geom: s81/t21/before/.
  KV bind a2 running (kv/bind_a2; a1 failed: private plan must sit in the tree plan_of_record -> untracked
  wt/physical/die_plan/qwen_kvsys/plan_of_record/plan_rr1.json, NEVER stage it).
  Census (wave plans; types): KV start_reach 32 / writer 27 / fanout 28 / barrier 2 / fwd_source 42 (1338 pins);
  QC 18 / 26 / 1 / 0 / 99 (534 pins, +2 no tap); HEAD 1 / 3 / 0 / 0 / 2; S81 0 / 0 / 0 / 24 / 14; window_far (warn)
  KV 6, QC 28, HEAD 5, S81 34.
- 2026-11-13 04:44 branch commits 86d4155aff, e6bfa65802, 2ad9de19a9 (local on epyc7 wt, not pushed yet). KV strict bind a2
  RC 0 / 0 errors (kv/bind_a2/out): hub_Eo bound RTL = 149 reader + 118 writer START relays, cland_start drives 3,
  start_d 12, 0 rings direct. run-item hub_Eo launched: intel2 /srv/opentallas-scratch2/claude/rules-reach-1/jobs/
  rr1_kv3_hub_Eo (unit.log there; work epyc7 rules-reach-1/kv/pilots_rr1/items/kv3_hub_Eo).
  S81 t21 placed (epyc9 rules-reach-1/s81/t21): OT_FT_LANE 0 hops > 405; OT_CHAIN_EVEN 105 chains moved; r2r > 405
  1134 -> 1034 (bin->lpad 104 -> 12, max 587 -> 434); rest = vp glue hops 410-563 um (driver -> cf/yrow, driver_lo_d ->
  leafup ist0 536). AUTO-GEOM after: s81/t21/after (geom_after.sh via ot-run). Renders viewed (place density).
  Full-die fix runs: fix/{kv,qc,head,s81}_fix.log on epyc7 (scan/run_fix.sh).
- 2026-11-13 04:54 RULEBOOK section R-REACH posted (coord commit 0e2498bdbdd, on origin/coord/state). Branch pushed to hub:
  claude/rules-reach-1-1113 @ 1376d26613 (4 commits; merge-tree vs origin/main 87b85b86bd clean). Tests: test_reach_rules.py
  11 + related suites pass; test_gen_phys_bump_ports::test_refuse_mismatch is the known base failure.
  S81 t21 a1 AUTO-GEOM (s81/t21/a1_geom): r2r_count 1134 -> 1034, relay_collapse 380 -> 327, r2r max 700 -> 827 (ONE
  fan-out pad bit pushed out) -> guard added (1376d26613) and DPL re-run a2 (s81/t21/after; logs ~/rr1log/s81_t21_place2.log,
  s81_t21_geom2.log). KV hub_Eo run-item in kit_rtl/gen -> place expected ~05:00-06:30.
  NEXT: (1) read a2 AUTO-GEOM; (2) hub_Eo place: classify r2r with scratch rr/r2r_class.py (copy on epyc8 /tmp/rr1_r2r_class.py,
  epyc9 rules-reach-1/s81/ov/), view run/layout_review/place/{density,layout}.png; route if place is clean;
  (3) update the Proof kits paragraph of the R-REACH section (intel2 ~/rr1log/put_section.py + rulebook_reach_post.md),
  coord-commit; (4) READY in lanes/COORD-REVIEW-QUEUE.md (branch, tests, census, proofs); stop.
- 2026-11-13 07:25 REACH-FIN-2 (Opus successor) finished the lane. Hub tip was 9c98f405bd = epyc7 wt HEAD (nothing unpushed;
  untracked plan_rr1.json + composed_rtl/ are proof inputs, NOT staged). Commit 3144527add (pushed): G0 r_reach default
  "warn" (budgets.r_reach "error" opts in) and R-REACH-5 chain_even only with budgets.r_reach_even true (defaults preserved).
  merge-tree vs origin/main 9ebef751ca clean. Tests on merged tree: 802 pass / 2 fail (both fail on origin/main alone:
  band_reserve steps_down_to_fit_reach, bump_ports refuse_mismatch). Proofs read: S81 t21 after AUTO-GEOM r2r>405 1134 -> 1039,
  max 701, GRT 0 ov; KV hub_Eo placed, AUTO-GEOM FAIL, GRT 0 ov, r2r>405 721 (worst u_rrl_150 -> cland_fstart_ft12_o 2376 um),
  run-item stopped at geom. RULEBOOK text (rows 1/2/4/5, item 7) still says ERROR / every kit: COORD to change to opt-in.
  READY posted in lanes/COORD-REVIEW-QUEUE.md. Lane STOPPED; nothing running from this lane.
- 2026-11-13 07:35 RESUMED after REACH-FIN-2 handback. Branch tip ce0e50e4e7 (adds the reach_homes schema/G0 test; pushed; merge-tree
  vs origin/main 5eefdbe2fa clean). hub_Eo placed: r2r>405 3869 -> 721, START fan 3236 -> 0; leftovers classified in the
  RULEBOOK proof table. RULEBOOK R-REACH updated (opt-in wording, final proof numbers). Renders viewed (scratch rr/img).
- 2026-11-13 08:11 branch tip ec64b8339b: rule 1 takes cland_rstart_in (relay piece of an R-CAP split) as START origin; RULING + new train-47 sha posted to DIE-KV-100 / ROOT-MERGE. Lane stopped again.

CODEX2026-11-13 follow-up READY79d58ec6f0 hub branchclaude/rules-reach-1-1113 (E7existingwt). clock_landings.py signed hard DSREP/RSTREP/PLACEREP preservation +test,10focusedPASS E4unit3328160; QC ctl4d blocked1/6 vs signed8/34. Exact START34copies/K unchanged/strict mismatch gate retained. QC/shared own adoption, no plan/re-sign/P&R, untrackedKVartifacts untouched. Code committed/pushed.
CODEX READYab145f3072 after79d58ec6f0: fixed-phase reuse relay writer siting, actualpinnedRX/depth/reuse retained,physicaldepth-1;17testsPASS E4unit3453566. ActualQC privateevent adoption/results ownedQC, no ownplan/P&R. Allsourcecommitted/pushed.
CODEX sharedlateECOsource READY21f727475c +doc96b3321801 hub existingreachbranch. eco_loop.py/prd_hook.tcl+tests only;111testsPASS E4unit2031904, sharedCONCUR. Defaultlatecore-owned repair, actualscopeexpected/pinned, MMguardfailclosed, post-RCcalruntimepostconditionandreceiptbeforeacceptance; pregrt/explicitoverridesunchanged. Root/shared/residualnotified, no P&R/deploy, T51actualcauseUNPROVEN. Allsourcecommitted/pushed.

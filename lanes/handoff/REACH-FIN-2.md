# REACH-FIN-2 handoff (Opus successor to RULES-REACH-1, rule R-REACH; COORD coordinates)

## State at handback (2026-11-13 07:28 PST)
- Branch: hub claude/rules-reach-1-1113 @ 3144527add (worktree epyc7 /srv/opentallas-scratch2/claude/rules-reach-1/wt).
  Hub tip before this lane was 9c98f405bd = wt HEAD (nothing was unpushed). Untracked in wt, proof inputs only, NEVER stage:
  physical/die_plan/qwen_kvsys/plan_of_record/plan_rr1.json and .../inputs/composed_rtl/.
- Commit 3144527add (this lane): defaults preserved. G0 check r_reach WARNs by default (budgets.r_reach "error" opts in);
  R-REACH-5 chain_even hook only with budgets.r_reach_even true. share_trunk, reach_fix classes 7/8 and reach_homes were already
  opt-in. Current plans' kits and G0 verdicts do not change when this merges.
- git merge-tree vs origin/main 9ebef751ca (contains 24b08535da): clean (tree 035f8f58bd).
- Tests on the merged tree (epyc7, 94 tools/die_plan files): 802 pass, 4 skip, 2 fail. Both failures also fail on origin/main
  alone: test_clock_landing_band_reserve::test_band_spread_steps_down_to_fit_reach, test_gen_phys_bump_ports::test_refuse_mismatch.
  Logs: epyc7 rules-reach-1/rf2_pyt_full.log (merged), rf2_pyt_wt.log (branch head).
- Proofs (finished, private, DO_NOT_COUNT):
  S81 t21 (epyc9 /srv/opentallas-scratch/claude/rules-reach-1/s81/t21, after/): r2r>405 1134 -> 1039, max 699.8 -> 701.1,
  relay_collapse 380 -> 327, GRT 0 overflow. FAIL on non-rule-5 classes.
  KV kv3_hub_Eo (epyc7 rules-reach-1/kv/pilots_rr1/items/kv3_hub_Eo/geom): placed, FT_LANE 0 hops >405, AUTO-GEOM FAIL,
  GRT 0 overflow, r2r>405 721 (pre-kit count 3869), worst 2376 um u_rrl_150 -> u_cland_fstart_ft12_o (reset relay -> FSTART
  face flop). The run-item stopped at geom (RC 1). No route was launched.
- READY posted to lanes/COORD-REVIEW-QUEUE.md: [REACH-FIN-2 -> ROOT-MERGE, COORD]. COORD 07:2x: approved as train 47 if
  defaults are preserved (they are).

## Open for RULES-REACH-1
1. The RULEBOOK R-REACH text still says G0 ERROR for rows 1/2/4, "every kit" for row 5, and item 7 says 'error (default)'.
   It should say opt-in (COORD's call; I did not edit the rule text).
2. QC s29 tree uses 9c98f405bd, where rule 5 was ON by default. On main, QC plans need budgets.r_reach_even true.
3. hub_Eo: classify the remaining 721 r2r (rr/r2r_class.py). The worst hop is the reset relay -> FSTART path, not the START
   trunk. Route only if COORD wants it.
4. Proof kits paragraph in the R-REACH section is not updated with these numbers.

HANDBACK 2026-11-13 07:28 to RULES-REACH-1

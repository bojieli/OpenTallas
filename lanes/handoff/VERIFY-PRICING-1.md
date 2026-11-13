# VERIFY-PRICING-1 handoff (tool-fix lane; COORD ruling S81 ready12b-A 19:02)

Job: prove/refute that bind verify depth mismatches (3966 on S81 out_r12bA_dst) are source-kit stations not added back under
kit_source_station_pricing ON; fix verify to use the LATCHECK-1 station source; proof 0 in place; one READY; stop.

## State (updated 19:2x PST 11-12)
- Worktree: epyc8 /srv/opentallas-scratch2/claude/wt/verify-pricing-1, branch claude/verify-pricing-1-1112 off origin/main 8fc4972f54.
- Fix commit 3da2fdfc5f (not pushed yet): bind_verify.KitSourceCredit + kit_source_cuts; lane_asbuilt_latency.source_cut /
  source_cuts (check() uses the same helper); test_bind_verify_kit_pricing.py (7 tests). 48 pass with the LATCHECK + verify tests.
- Cause confirmed in code: bind.py bind_sinks want = full lane (bound formula includes internal_kit_source_cycles); bind_verify
  compared the traced bound RTL count only. Credit = sum of priced u_bout_<o> faces on the driving transport chain.
- Proof run: epyc8 /srv/opentallas-scratch2/claude/verify-pricing-1/bin/run_verify_vp1.sh under ot-heavy --mem 230 (started
  03:15 UTC), tree bsrc_vp1 (hardlinks of s81-r12ba-fin/bsrc_r12bA_dst + tools copy of 3da2fdfc5f). Merged verify outputs moved
  aside in OUT as verify_merged/, verify_report.json_merged, lint_merged/. Log verify_vp1.log, run_vp1.out (VERIFY_VP1_RC).
- Pass criteria: kit_source_credit.raw_mismatched_credited_match == 3966, raw_matched_credited_mismatch == 0, mismatched 0;
  only the 2 leaf__t3 CLOCK_LANDING reset rows remain (ruled functional, separate).
- Run 1 OOM-killed 04:15 UTC in lint (memcg 230 GiB, peak 230). Fix 376cb98e4b frees bind_sinks + credit cache before lint.
  Run 2: bin/run_verify_vp1b.sh under ot-heavy --mem 260 (started 11:1x UTC 11-13), log verify_vp1b.log, run_vp1b.out.
  Session restarted 11-13; no READY posted yet.
- Next: on result -> push branch, READY to COORD, stop.

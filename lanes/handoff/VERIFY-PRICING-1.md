# VERIFY-PRICING-1 handoff (tool-fix lane; COORD ruling S81 ready12b-A 19:02) -- STOPPED after READY

Job: prove/refute that bind verify depth mismatches (3966 on S81 out_r12bA_dst) are source-kit stations not added back under
kit_source_station_pricing ON; fix verify to use the LATCHECK-1 station source; proof 0 in place; one READY; stop.

## Result (11-13 04:3x PST)
- READY posted: origin claude/verify-pricing-1-1112@376cb98e4b (3da2fdfc5f fix + tests, 376cb98e4b frees sinks before lint).
- Claim PROVEN: in-place verify on out_r12bA_dst: mismatched 0 (was 3966); raw_mismatched_credited_match 3966,
  raw_matched_credited_mismatch 0; 80 priced lanes / 97 stations, all credited, 0 faces unmatched. Only the 2 leaf__t3
  CLOCK_LANDING reset rows remain (ruled functional, separate). verify_report.json sha256 1f1d87f6decb.
- Run 1 (--mem 230) memcg-OOM in lint; run 2 (--mem 260, tools 376cb98e4b) completed.
- Files: epyc8 /srv/opentallas-scratch2/claude/verify-pricing-1 (bin/, bsrc_vp1 = hardlink tree + tools copy, logs).
  OUT keeps the predecessor's merged-tools outputs as verify_merged/, verify_report.json_merged, lint_merged/.
- Worktree epyc8 /srv/opentallas-scratch2/claude/wt/verify-pricing-1 (remove after merge; bsrc_vp1 removable then).
- Known unrelated: test_bind_structural_bridge_event x2 KeyError 'partitions' (bind.py untouched here).

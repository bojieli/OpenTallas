# FABLE-FIX-QC-PLAN handoff (QC S4q9m plan chain -> CB16-qualifying bind)

## 2026-11-17 03:3x start
- Scope: M4 (zz_s29_qc103_s4q9m4.json 32bba5467a18, side 5787a70f3b01) to a bind meeting CB16: 0 errors, extra e2f94854 468/468, R8 pinned PASS, column pads <= 9, LATCHECK 1921/1921, hcparam 0, G0 0 latency.
- Decision (1): 5 new st_a masters (COORD + FABLE-CLOSURE-STRATEGY-0320); no restore in M. From N: st_a/st_b QFT params = equality constraint at compose time.
- Live work of others, not duplicated: QC-PLAN-M4 replay E2 oth-ubuntu-1550993 (knee-hc/gates/m4_prebind_1117), G0 m4_1117/gates/g0; QC-TYPES-R builds the 5 masters; QC-CLK-R2 recuts 3 sle_st_b_v1 rows.
- My dir: E2 /srv/opentallas-scratch3/claude/fable-fix-qc-plan/ (replay v3 copy + runs).
- Next: review replay coverage holes; add chain-manifest, kit-rtl/cm/kp/latcheck-CLI and CB16-criteria stages; launch M4BR/BQ via ot-run --priority plan only on a clean replay with the rows folded.

## 2026-11-17 04:06 M4 bind launched
- M4 replay (QC-PLAN-M4, knee-hc/gates/m4_prebind_1117): pass 2 = 0 real errors. Its 36 BIND_GROUP_MASTER + 1 HCPARAM are replay-tool artifacts (replay links only asbuilt.json, not asbuilt_sources.json; SUM line counted). Proof: bind_strict_src.check with the seed's 39 lib files on the 8 su_lane products = 0.
- My tool: E2 /srv/opentallas-scratch3/claude/fable-fix-qc-plan/bin/prebind_post.py (c74f76a1d84a). Runs on a replay OUT, or on a real bind with --bind-dir (the CB16 record). Stages S1 receipt integrity (+strict recheck), S2 manifest == chain-composed, S3 the six CB16 criteria, S4 st_a/st_b param equality (plan rows vs QFT; moves vs a reference bind must be covered by --declared-masters = the event-N equality constraint), S5 kit-rtl on clock-merge + param_wrap types + cm/kp check, S6 latency CLI. First run: fable-fix-qc-plan/m4_post_1/post_receipt.json; S1-S4 clean except rows_check absent in the v1 receipt.
- BIND RUNNING: E2 unit oth-ubuntu-2337006-1794917117 (ot-run --priority plan, 128 GB), chain fable-fix-qc-plan/bin/chain_s4q9m4_ffqp.sh, tag s29q103S4Q9M4BR, plan 32bba5467a18, side 5787a70f3b01, first R8 = replay-derived c66ea4c01d38 (fable-fix-qc-plan/m4bind/r8_m4_replay_derived_c66ea4c0.json), log fable-fix-qc-plan/m4bind/chain_M4.log, bind log knee-hc/bind/bind_s29q103S4Q9M4BR.log. Expected: BR rc 0 = final (no BQ); then R8 pinned check, LATCHECK CLI, hcparam, G0 (~45 min), CB16 record knee-hc/gates/cb16_qual_s29q103S4Q9M4BR/.
- Bind does not read clock.tap_offset rows; the QC-CLK-R2 M4 row delta (~07:00) folds as a rows-only plan delta, then one more single-pass bind under a NEW tag on the folded plan (same R8 seed) = the final bind CB16 is read on. Do not reuse tag M4BR/M4BQ.
- If the chain stops: read chain_M4.log; BIND_RC 11 = cm/kp inject refused, 17 = isolation, non-R8 errors = assert in the chain. No same-input retry; new tag for any new candidate.

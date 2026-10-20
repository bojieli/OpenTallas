# A0 r4 terminal collection (2026-10-20 04:00 PT)

Source branch claude/qw-a0-rc4-1020 RTL 3fe36bf2e, receipt commit 109c8e741. Original worktree and live NL gates untouched.
NK rc8 and rc8b: FAIL. Actual remote cts.log proves clock geometry failure, not density/placement: TT ck_dw spread 232.2 ps / 191.3 ps, all_internal_only 1056 sinks. CTS exits before FF/GRT/path-classes. Generic gate cts_run does not describe actual reason.
Native census PASS max32, 54478 roots, zero violations. Pin geometry PASS2622, textbook depth468.4ps, total fill45.2%, std density3.0%, outline820.8x907.2.
Safe checklist: 1 pins/reset preflight PASS; 2 reach inherited preflight <=405um, measured complete path analysis unavailable; 3 census PASS; 4 depth PASS; 5 inherited u_xm delay-line waiver PENDING; 6 preflight lattice/aspect/full-face pins PASS, PNG floorplan preserved; 7 FAIL ck_dw TT spread (no FF signoff); 8 static/zero added data cycles.
No REVIEW.json or submission. Remote exact cts.log, gate JSON/source-bound gate_result, shipping snapshots/stdout, README and original layout are preserved beside this file.
Diagnosis: g_operand_rr s2_w is clocked on ck_dw/de but absent from dw/de fence regexes; it is caught by hub. 512 variable s2_w bits per half +512 mq_wrom+32csel=1056 sinks per root. Successor must co-locate complete regional mass and retain TT+FF<=80; zero source behavior change.
CB16 fullk/fullkb and A0 NL rc8/rc8b are live and remain in pending_results. No progression claim based on empty buffered logs.

Mapped-name correction: s2_w is optimized/aliased into g_hier.g_sl[*].g_hd.g_tx.g_r[0].di. Actual audit confirms old fences put512 ck_dw and512 ck_de source flops in hub; rc9 matches surviving di aliases and restores1056/1056 to their own region. Internal-only spread scope is applicable because these roots carry internal operand clocks without a boundary subset. Original-fence causal negative:1024 wrong memberships and AssertionError.

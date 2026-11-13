# SVC-MACRO-2 handoff (Opus successor of HARD-S81-SVC-1; S81 svc family, 16 items held SVC-MACRO-1113; COORD) -- started 2026-11-13 07:00 PST

## Read first
- lanes/handoff/HARD-S81-SVC-1.md (findings 1-4: memory is already MEM v2 macros on main; wave lost the closure when s81 kit_rtl
  moved to mode "bind"; R-CAP needs provider hard cores + Y cut).

## Worktree / files
- epyc7 /srv/opentallas-scratch2/claude/wt/svc-macro-2, branch claude/svc-macro-2-1113 off origin/main 24b08535da
  (worktree of the hard-s81-svc-1 clone). fe4468028e (flow fix) cherry-picked here.
- predecessor work dirs still used: epyc2 /srv/opentallas-scratch2/claude/hard-s81-svc-1/{kr,gp,fitgate}.

## State / next
- 07:00 took over. genproof svc_hi_dsdv_svc_rs__t1 (epyc2, GEN_LINT) still running from HARD-S81-SVC-1.
- 07:0x flow fix carried: claude/svc-macro-2-1113@3856aafc01 (= fe4468028e on origin main 24b08535da), pushed, on origin.
  test_kit_wave_kit_rtl_post.py 6/6 pass (epyc2, archive of the branch incl. the closure inputs). Full test_kit_wave*.py:
  600 pass / 10 fail on the branch; baseline main run in progress to show the 10 are pre-existing.
- COORD 07:1x: Codex (mistaken 06:59-07:04 takeover) left untracked in wt/hard-s81-svc-1:
  physical/die_plan/s81/delta_svc_provider_recover_1113.py (44 lines; uses main svc_prov_event_1109.split_type/validate) and a
  donor copy of tools/die_plan/type_split.py (KV-SPLIT-1, not on origin). Outputs epyc7 hard-s81-svc-1/v5/plan_provider_recover.json
  + provider_recover_report.json. REVIEW: correct as step 1 (R-CAP-3.3 provider hardening) on ready12b-A 18c864518844: outlines
  unchanged (core-shape freeze), lo growth not repeated, 14 rs types 26 (hi) / 58 (lo) boxes, 0 legacy validation fails, 31 new
  SRAM sites. Open in it: pvso_entry t1/t2 not covered; reset contract not re-solved; provider views = S81-SVCRS-4 rows
  (12 SIGNED, 9 LOCAL_PASS_NEEDS_PARENT, epyc9). DECISION: USE it (step 1). type_split.py not usable for svc: the whole soft
  parent is ONE content (u_rsv dsdv_svc_rs), type_split moves contents by regex, so a split needs an RTL cut first.
- R-CAP projection (cap_estimate.project, soft = v5 measured 228,760 hi / 381,961 lo, pins = plan bus bits):
  ready12b-A (no boxes): hi rs 524-583k, lo 655-741k (and the real soft there is the 4.1 M flat form).
  provider-recovered: hi rs 555-614k (142 macros), lo 732-819k (195 macros), pvso_entry 732k. ALL OVER 400k.
  Terms (hi t1): soft 229k + port 16.6k + pin repeaters 137k + macro repeaters 175k. Split still required (3 parts hi, 4 lo).
- 07:2x GEN + GEN_LINT svc_hi_dsdv_svc_rs__t1 from the closed kit (epyc2 hard-s81-svc-1/gp, wave bind ready12b-A): GEN_LINT PASS,
  0 issues (pins_vs_plan, clock_export_form, macro_tcl, rtl_check, memory_bits all PASS). Memory part of the brief is proven.
- 07:24 posted to COORD-REVIEW-QUEUE: READY claude/svc-macro-2-1113@3856aafc01 (flow fix) + PLAN (svc R-CAP form, options A/B,
  orphan VL3-SVCSTN builds on epyc2). The coord-commit of those lines was queued behind the hub lock at 07:3x (two
  coord-commit.sh processes of mine, PIDs 1994201 and the nohup one, log ~/tmp/svc_macro_2_commit.log) -- check they landed
  on origin coord/state (grep "SVC-MACRO-2 -> COORD" = 2).

## HANDBACK state (2026-11-13 07:26)
Running jobs: none of mine (genproof hi t1 finished; the epyc2 vl3-svcstn builds are NOT mine, orphaned, cancel proposed to COORD,
  not touched).
Worktrees (epyc7, both worktrees of the hard-s81-svc-1 clone, clean, no uncommitted edits):
- /srv/opentallas-scratch2/claude/wt/svc-macro-2 = claude/svc-macro-2-1113@3856aafc01 on origin (READY, flow fix + 6 tests).
- /srv/opentallas-scratch2/claude/wt/svc-macro-2-form = claude/svc-macro-2-form-1113@ff8154806c on origin (Codex recover
  script only; created with --no-checkout, so the working tree is empty by design: use git -C, or delete this worktree).
- wt/hard-s81-svc-1 still holds Codex untracked files (delta_svc_provider_recover_1113.py, type_split.py donor); left as is.
Test scratch: epyc2 /srv/opentallas-scratch2/claude/svc-macro-2/{t0,t1} (archives of main / branch, deletable).
Codex recover script: KEEP as step 1 (see 07:1x note above); type_split.py not usable for svc until the soft parent u_rsv is cut
  in RTL.
Decisions: memory = done by the flow fix (no new macro needed; MEM v2 already generated macros). R-CAP: provider form alone is
  still OVER (hi 555-614k, lo 732-819k, pvso 732k projected), so a cut is required. Recommended A = 4 band partitions in Y
  (one per lane band g_t/g_m/g_tr + 2 SML + SMD; top part also takes SRAM rows, sx, SMC/SMR, PC, job, trees), +1 cycle per cut
  lane; ~120k hi / ~165k lo per part. B = same band wrapper as a hard core reused 4x and across the 14 rs types, parent ~350k NEAR.
Next steps (not started): (1) COORD decision A/B; (2) RTL dsdv_svc_band wrapper + cut of dsdv_svc_rs_c / ot_hdc_v41x_attn_s
  per band, sim (tb_svc_h8_protocol, svc mem benches) + LEC vs uncut slice with boundary flops mapped, latency rows;
  (3) plan event on top of the provider-recover output (pvso_entry t1/t2 + reset contract still open); (4) private kit of one
  part through place + GRT, renders viewed; (5) READY after the 11-15 04:00 freeze. Hold SVC-MACRO-1113 stays until then.
HANDBACK 2026-11-13 07:26 to HARD-S81-SVC-1

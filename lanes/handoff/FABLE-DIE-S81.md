# FABLE-DIE-S81 handoff (2026-11-16 08:3x PST)
Report: lanes/FABLE-DIE-S81.md. Work dir epyc9 /srv/opentallas-scratch2/claude/fable-die-s81 (run_base.sh TAG PLAN, dieana.py,
dierender.py needs user-site matplotlib so run without -I; plan/ holds B6gF2s2 + B6gF2sv; s81/F2s2 = baseline run).
Lane clone epyc9 fable-die-s81/repo, branch claude/fable-die-s81-1116 @f222855b650 (pushed). Gate: intel2
~/fable-die-s81/gate_f222855.log (ot-gate-remote exists on epyc9, not epyc7); post READY when it prints GATE pass.
Launch form: intel2 `ot-run --mem 100 --threads 24 --hosts epyc9 --dir W --priority die -- bash W/run_base.sh TAG PLAN`.
Delivered: col reset rows + overlay on epyc10 fable-die-s81/rst (post 3775dcfb1c3). DIE-S81-92 folds them into F2s3.
Next, in order:
1. R3: find the die_trial type keep-out switch (test_die_trial_type_keepouts.py), add bands / ft stations / tap rows and
   --rep-reach-max 405 to the yaml, rerun run_base.sh, re-count band hits (target 0) and legs over 405 (target 0).
2. R2 rows from that kit (clksite_reserve.py --tree), then R4 with DIE-S81-92's chain_ca tools (ca_swm form).
3. Read the COLTAP r2 pilot for u_d*_Y* endpoints (accept >= -42 TT); if a chain hop is still long, add sites.
4. R5 station rows; R6 per-port seam windows from s81/F2s2/kitwin.json.
Incident: the session scratchpad is shared; a helper named r.sh there was another lane's script and I ran it twice
locally by mistake (every step failed: no such dir, permission denied, no post). Use a private subdirectory.
Commit trailer used: Claude Fable 5.2 (session attribution rule), not Opus 5.5.

## CODEX R3 takeover 2026-11-16 10:4x PST
- Existing epyc2 F2s2ke completed GRT TT/FF EXIT0 (~18.7GB RSS each); taps21687/21687 present. TT intra+396.61 / seam+308.05. FF raw seam-353.23 and landed-phase margins-3255.33TT/-2871.11FF use stale K/phase; measured boundary-hold views0, so no full hold signoff claim.
- R3 failure diagnosed on minimum18-leg vehicle:16 missing placement regions are already-declared svc/jumper channels with between[] but no rect_um. Explicit exact gap rectangles (28 channels) at reach_codex/plan_gap_rects.json + gap_rect_rows.json resolve16/18 without area/cycles. Use current-plan channel_rect derivation when rebasing to F2s3/F2s4; never transplant stale coordinates after re-floor.
- Two in-part paths: SerDes__t2 wide PHY wall needs existing adaptive site-legal helper; node19 cap/xr clock path needs parity/minimum-count stages on legal sides of an unsplittable macro overflight. Shared tools pushed on existing claude/fable-die-s81-1116: cda5a7251117e78fdf815f49563fe707c69b52ff (adaptive helper fallback, normal gate51/51 GREEN) then4aa3ebbc21fe6585bea681511bfc8b3fdcba6159 (largest SPLITTABLE span for extra stages, targeted12/12 PASS; normal gate owned MERGE-QUEUE).
- Whole-body census: original ke point sites93528/93528 legal, but native1.62x0.27um bodies overlap3083 core halos,506 band exclusions,245 outside,7 PHY keepouts. Existing body_sites option was absent. New template s81_tpl_reach1_codex.yaml enables body_sites:true +detour:adaptive, with existing reach405/type_keepouts.
- Body-aware component evidence:17/18 PASS with cda; node19 PASS after4aa (7repeaters,max343.43um,+13.2um wire). Combined18 mechanisms at reach_codex/replay_body_composed.json, max343.43um. No new RTL cycles. Earlier failed logs preserved. A sparse-corner prototype was unnecessary once the padding bug was identified; retained as corner_uncommitted_codex.patch in epyc9 lane dir, never adopted.
- Fresh pinned candidate source epyc2 src_reach3_codex = real tools copy with cda+4aa +inherited private band patch; physical symlink points to same immutable src_v2/physical inputs. No report-all exception catch: it fails closed. Do not edit candidate after launch.
- Visual body-path review LOOKED/PASS-COND at reach_codex/results/geom_review/reach18_body_{paths.png,review.txt}. Launcher run_reach3_codex.sh -> F2s2kr3 is prepared, not yet launched pending4aa normal GREEN. Follow fulltree body/band/reach census, then R2 site rows +R4 K/strap regeneration. Inherited private band patch still needs source/test integration before release; no R2 adoption or R3 PASS yet.

## CODEX START/reset data-plane successor (2026-11-16)
- Owner child start_reset covers the two data-dominated C failures: t1clfe origin/s2 -> reader_start ft1_i copy6 (2104.28ps data), t15cla3d relay115 -> fstart ft0_o reset (2009.46ps data). Both require actual staged/local transport; clock cohorts alone cannot fix them.
- Canonical typed rows/report: lanes/handoff/S81-START-RESET-{rows,report}.json (coord78cd5973). Source input exact F2s3 plan012db35daaea, existing lane ep9 start_reset/{derive_rows.py,types.json,start_reset_rows.json,start_reset_report.json}. Two types use existing reader9/writer9 config plus equal-depth writer reset leaves, no new hardware mechanism. 144 added FF (54/90); no payload or FT cycles. Reader boot+8 relative default1, writer boot+9; current binder automatically prices K+W-R (affected-pair K+1 relative current). Cross-type straps/start-tree receipts must regenerate in next full bind.
- Geometry image start_reset/start_reset_review.png LOOKED: macro walls avoided, staged South corridors, local reset leaves outside storage bands. Data hops<=317.625um; local raw feeds<=197.001um; writer reset leaves<=213.468um. No macro/pin/outline changes. Physical bank/tap assignment still requires new GEN/CTS.
- Source bug fixed/pushed inherited branch d5bd6d74eede3dfbb00c8e01863bd31d99698739: clock_landings local-reset depth checker omitted production ot_dp_rrelay_nl. One regex and production positive/wrong-depth mutant,29 focused testsPASS. Actual C t15 bound wrapper5/5 local leavesPASS/wrong-depth mutantreject. Normal source gate owned MERGE-QUEUE, client3268762 logmq1/tmp/rg/s81-reset-parser-d5bd6d7-1116.out.
- Native RTL515-bit ring+relay miter baseline W0/R1/K1 vs candidateW9/R9/K2 PASS3576 exact comparisons across8 warmresets; staleK mutant3576 differences. Repro ep9 start_reset/{start_tb.sv,tb.vvp,rtl_proof.log,component.py,component.log}. Initial missing dependency/pytest import errors resolved, no timing failures overwritten.
- Next: parent DIE-S81-92 composes as separate successor after progressing F2s4strip event, binds/LATCHECK, fresh actualtwo typeGEN then reviewed fullshape CTS pilot. Do not modify current C/F2s3/strip jobs. No signoff or plan-adopt claim.

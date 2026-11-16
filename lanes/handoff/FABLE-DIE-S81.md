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

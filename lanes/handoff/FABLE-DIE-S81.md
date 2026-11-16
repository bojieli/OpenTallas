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

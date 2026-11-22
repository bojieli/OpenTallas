# QC-PLAN-R12 handoff (from 11-21 12:5x PST; succeeds QC-PLAN-R11). Read QC-PLAN-R11.md (V3 inventory, gate recipe) and QC-PLAN-R10.md (V2 apply recipe).
Work dir epyc7 /srv/opentallas-scratch2/claude/qc-plan-r11 (kept; R12 files go to /srv/opentallas-scratch2/claude/qc-plan-r12).
Intake ledger: lanes/handoff/QC-PLAN-R12-V3-INTAKE.md (cut 11-22 06:00, apply >= 11:16).
## Units / waiters
- v3t control (chain_v3t.sh pid 1857369): post-bind G0 + census; wait: until grep -q CHAIN_DONE qc-plan-r11/chain_v3t.log.
- sites helper (R11-SITES files, now R12): compose_sites.py ot-run unit oth-ubuntu-3018773-1795293987 (bash pid 3017469); ctl G0 run_g0.sh ctl (pid 2875631). Then run run_g0.sh on the sites plan + g0diff_all.py.
- tt_ctlm: taken by R12 (COORD 13:0x, OWNERS-SWEEP UNOWNED). Helper QC-PLAN-R12-TTCTLM (Claude subagent; dies with R12 session) work dir epyc7 /srv/opentallas-scratch2/claude/qc-plan-r12/ttctlm. Fix TTCTLM-R1 (lanes/handoff/FABLE-FIX-QC-rows-ttctlm.json).

## RESUMED 11-21 18:3x PST (after the weekly limit; Codex 14:23-18:1x)
- RECONCILED with J7eL6 (sealed plan a6771d121e95, intel2 kw45/src_s81_pin_3c913dbdfb23_d8j7_1117_work): all 72 START keys of the 25 slice_station types
  are IDENTICAL to my plan_l6s (recon: intel2 fable-fix-s81-strobe/tmp/recon.py). Slice rows = adopted in J7eL6 / enL6; nothing more to hand over.
- NOT in J7eL6: my 7 serdes ops (t3 reader+writer depth 11, t16 reader+writer depth 11, t4 / t13 / t15 cla2127225 writer depth 3):
  lanes/handoff/FABLE-FIX-S81-STROBE-serdes-start-rows.json (made on J6r1; must be regenerated on J7eL6: reach_rules.py fix --rules 1 --types '^serdes__').
  FAM-S81-SERDES-R6 (Codex) has a private W1 writer START for t16 (7 stages, <= 378 um, K 1->8 / -2->5) = same mechanism, shallower. One form must be chosen
  for J8: theirs for the t16 writer if its exact-width proof passes; the t16 READER START (ft1_i, 2.84 mm, the measured -1252 path) and t3 still need rows.
- My jobs: both run-items stopped by me 13:1x BEFORE any kit dir was filled (epyc10 was DRAINING; no build ever started). epyc7 tree copy job oth-ubuntu-3817542 DIED
  13:40 (client lost at the limit): epyc7 kw45/src_s81_pin_3c913dbdfb23_d8j6r1_1117_fxstrobe_l6s (+_bind copy) has the right manifest sha file but publish/verify
  was not confirmed: run src_manifest.py verify before use, or ot-delete. epyc10 copy is published + verified (3aa2196d96b1).
- NO PROOF KIT BUILT. 18:3x every build host is DRAINING (new job dirs refused). Next: when a host admits, private-spec slice_station__t18 on the J7eL6 tree
  (not my J6r1 tree) -> place stop read (expect path_um/stages on the line, main b9735df11e) -> route chain -> sign-off; then serdes__t16 with the chosen form.

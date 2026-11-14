# ROOT-MERGE-62 handoff (2026-11-13, after Codex ROOT-MERGE-61 park)

## State
origin/main = hub ~/OpenTallas = 4702c3c43a6f0f3123f69d383ad6437cc7ac0075, clean. No jobs running.
Landed (all with MERGED lines in lanes/COORD-REVIEW-QUEUE.md and 5 tags each, read back):
- A a4da49b846d2 (tags flow-20261113-aa-*): Codex batch78 2fc6f2700a (reset root copies b6a8=b3c776, READ_CHUNK 4877=0c02, tracer c2613d=955741 patch-identical, GF5 F/A0 unused overlay) + test_ts_relay fixture fix (tracer needs LEF directions).
- B 30f4ab558f77 (ab): native mapper 9615a697f7, LEC f9b72b0b1d, paired RESET/START d20d68e762 (cherry-picked).
- C e5d142bf7fcd (ac): KV-KITFIX-1 437795b7dd. kv-kitfix-1-plan-1113 NOT merged (post-freeze plan).
- D 4702c3c43a6f (ad): HARD-QC CBF corridor 4ad3e1b02c+b869e17362.
Already in main before me: TOK-VERIFY-3 67b97a7613, HARD-QC d2506256e2, CBF deps fe86e6ab12/6d5f095842.
955741b20a must never be merged directly (carries 6 FRAME-SPINE plan/event ancestors).

## Recipe
- epyc8 /srv/opentallas-scratch2/claude/wt: rm60 (at D2), rm60c (at D pre-fix ae5fcf9e68), rm60-main (28cf baseline). venv60. Runner wt/run62.sh (59-style die_plan+autopilot + wt/t66.list), outputs wt/t66-{main,tipA..D}.{raw,fails,xml}.
- Baseline main 28cf: 10571 tests 61F+2E (incl. ImportError test_tap_chain_affinity / test_postcts_real_clock_profile).
- Landing: intel2 bash /srv/opentallas-scratch2/claude/rm62-land3.sh <tip> <old-main> <receipt> <shas...> (hardened copy with receipt latch; the old rm60-land3.sh on intel2 has NO latch, do not use). Receipt ~/tmp/rm62_<train>.receipt = "HEAD=<tip>\nALL_CHECKS=0" written only after the gate passes. Push tip to hub branch claude/rm62-trainX first.
- Posts: intel2 bash /srv/opentallas-scratch2/claude/rm62-post.sh "<line>" (appends to queue + lanes/ROOT-MERGE-62.md via coord-commit).
- Next free tags: flow-20261113-ae-*.

## Open notes
- Tracer c2613d now fails closed (ports -> unresolved) for hard cores without a lef path; old QC plans (qc99_s23 and earlier: 166/666) affected, current s25-s27 only 6/666. Flagged in the A MERGED line for the tracer owner.
- Codex-listed but NOT in my brief, not merged: PVFIN 4675ca42cc donor, SVC chain aa7281/1d60ef/b26960/9d2710.

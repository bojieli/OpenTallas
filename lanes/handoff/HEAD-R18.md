# HEAD-R18 (Opus 5.5) handoff - replaces OPUS-FIX-HEAD-LEP0N-R9, FABLE-UNC-HEAD, HEAD-CTL-R1
Deadline: plan to FABLE-RC-ALL (was FABLE-RC-KVHEAD) by 10:30, HEAD r18 gate 11:00 PST.
Lane dirs: epyc9 + intel1 /srv/opentallas-scratch2/claude/head-r18 (clone/ = lane clone tools cone, tmp/). R9 lane dir epyc7 /srv/opentallas-scratch2/claude/fable-fix-head-lep0n-1122 (L).
Plan of record r18z2 23e33a4497865202: epyc7 L/trees/s81_head_r18w_ecol/physical/die_plan/s81_head/prep/NF15f/prep/source_plan.json

## Live units
- wp3 W probe: epyc7 oth-ubuntu-3722763-1795439402 kit .../private/OPUS-FIX-HEAD-LEP0N-R9/hd_lep0N_w_1123035958 (GRT from 05:26). log intel2 ~/fable-fix-head-lep0n-1122/runitem_r9_wp3.log
- ep3 E probe: place on intel1 (job dir /srv/opentallas-scratch2/claude/ot-jobs/hd_lep0N-place-key-cardinal-569295-1795436170), hub service kwp-ace3f525e5181078913e; kit .../hd_lep0N_1123035944. log runitem_r9_ep3.log
- hd_ctl LEC proof: epyc9 oth-ubuntu-928356-1795443707, script head-r18/tmp/lec_ctl1_fsm.sh, out head-r18/lec_ctl1_fsm, log tmp/lec_ctl1_fsm.otrun.log
- old e1 kit intel1 oth-ubuntu-1532240-1795405774: UNSIGNABLE posted 06:05 -> cancel at 06:35 via ot-run --cancel

## hd_ctl LEC = LEC-SETUP (posted 06:3x)
yosys FSM_RECODE st[2:0] (7 states) -> one-hot st[0..6]; OT_LEC_SUPERSET_VEC=1 name-paired st[0..2] -> fsm_proposals skipped. Patch in epyc9 clone tools/die_plan/lec.py (superset_fsm / fsm_shape) + test_lec_superset_fsm.py (11 tests pass). Push via ot-push-main after EQUIVALENT. WRCAP REASONED (ctl1 no-WRCAP signed TT +4.35).

## TODO
- West LEP-WPLACE-1 (w1-w4 FABLE-RC-ALL causes), tree re-fork vs main + ADV-TREE-DRIFT + re-gate, ep3 census (PROBE-PASS fe8a2a5: total <10% of 45,948 baseline, no cluster >=50), wp3 hold vs 17,932, rc138.

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

## CODEX notes 11-23 07:30 PST
- LEP-CLKWALL-1 standalone epyc7 cw1 plan 9b79a291e87cb006. PRE 0, strict bind 0 (7668), cohort 27/27, LATCHECK 334/334. The raw placed A/B both hit GRT-0228 on (796,2404) usage 65535 and both hit the 20k marker cap. Recorded local horizontal overflow at x800–850 y640–705 fell 53→3. This supports the geometry row, with full GRT still open.
- r18z2 W wp3 epyc7 1123035958: FAIL clock GRT-0273 on clk, clk_t1, clk_t7, clk_t37. Clock-first iteration 10 reports 0/1 vertical capacity within the 0.57 µm cell immediately below each BPin. Later signal GRT overflow 0 was after clock NDR drop. FF pre-GRT hold: cross-tap 810 before (−68.96 ps), 0 after (+45.009 ps), same-tap 6→0, port-in 5818 at −81.34 ps, 12834 hold buffers, TT +0.675 ps. E ep3 CTS remains in progress.
- Private r18wplace1 combines CLKWALL plus five staggered W banks (lower pair to SRAM 8.65→35.65 µm), eight nearest existing forwarded taps (max 1248.7→70.6 µm), and the exact four W M7 ingress pin heights 0.768→3.24 µm, using existing per-port plan support. The tap centres, interfaces and latency are unchanged. Actual BPin collision sweep 0. The floorplan and tap escapes were rendered and looked at. Review assets are at epyc7/9 head-r18/results/geom_review/head_r18wplace_preview.md. Verdict private generate and place only. Actual placement, phase pairing, PDN, route and no NDR drop still needed.
- r18r cold tree epyc9 fork is copying roughly 47.6 GB over the network at about 2 MB/s. Existing client oth-ubuntu-1343343-1795444932 retained. Only Codex's dependent wait service on epyc9 was stopped. Faster local epyc7 fork and gate started through ot-run under head-r18-wplace1-gate.service PID 2050612, waiting on host load admission. Work under /srv/opentallas-scratch2/claude/head-r18, log tmp/r18wplace1.otrun.log. Candidate uses current pinned runtime c84f72ee2c9e.
- hd_st_n4 sealed 1123001323 signed TT +75.74, FF-int 0/0, DRC 0, LEC 28870/28870. AGIdock index latest __ax_93d39da9d0 ODB size matches. hd_ctl exact 6_final FSM-corrected LEC epyc9 oth-ubuntu-928356-1795443707 progressing; original failure kept. Independent Fable sign-off review on exact final plan pending.


# S81-ALLFIX-COL handoff (Opus, family lane REBASE, started 11-23 16:29 PST; LIVE MEMORY)
Brief: scratchpad allfix_brief.txt (+ resume_1123b/e, rules.txt). Integrator = S81-ALLFIX-INT. Original owners: S81-COL-J9, FABLE-OPEN-S81-B.
Lane dir: epyc10 /srv/opentallas-scratch2/claude/s81-allfix-col (ops/ row files copied, tmp/ scripts+outputs, hf/ hopfix).
Base B1 ae3101241d6b = E10 s81-j9-r6/b1_tree/physical/die_plan/s81/plan_j9_b1_exact_1123_ae3101241d6b.json (b1_tree used READ-ONLY for PRE; plan_gate_pre check writes only --json).

## Results (posted 17:3x ROW-REBASED x15, hub 7504d8c3)
- IN-BASE (op-by-op vs B1/J8, tmp/inb1.out inb1b.out): rc72 UCF-MX 96/96; rc78 GROW (outlines +25.92/+60.48); rc80 SEAMBLK 6/6; rc84 TAPSPLIT 24/24; rc79/82/85 TAPGRT 24/24 + REACH v2 59/59; rc88 SSTRIP 300/300; rc87 porous data == rt 70b6 (11e80a73410f); rc89 s3 by tap count (+4035 vs probe +4038; asked TAP-GRID-R6 confirm); hop rows = REACH + kit_wave item_env col_h* OT_KEEP_WIRES.
- COL-FRAME-HOPFIX-1: hf/plan_hf.json c71de97d3e91 (rt 70b6), scope -6/+0, PRE tree-tools PASS 0; main-tools vs J8: 12 ANCHORDRY col_h9_r0_p5 (inherited B1: Codex step02 depth-8 FSTART reseat vs J8 depth 7). Re-running main PRE vs base B1 (hf/pre_main_vsB1) and B1 vs J8 (hf/pre_main_B1_vsJ8).
- col774 52aebeb23d: RTL only, carried by overlay + re-ELAB.
## Open
- rc72 probe: intel1 s81-col-j9/ew1_place_1438 (S81-COL-J9/Codex; bind b_f9a1db3e37dd at 17:23 still in bind) -> p5 GRT read ~20:00 -> post to INT + PRECHECK-LEDGER-R3.
## 17:5x
- HOPFIX PRE main tools vs base B1: PASS 0 adv 197 (hf/pre_main_vsB1.log). Posted ROW-REBASED ae218970. 12 p5 ANCHORDRY = J8-baseline artifact of B1 depth-8 reseat; B1 strict bind re-picks rst_rl_22->24 depth 7.
- pre_main_B1_vsJ8 (confirm inherited) still running E10 unit oth-ubuntu-3225270 -> hf/pre_main_B1_vsJ8.log.
- NEXT: read ew1_place_1438 p5 GRT (~20:00): final 5_1_grt overflow at x1133-1413 y607-675 + census; post to S81-ALLFIX-INT/PRECHECK-LEDGER-R3 (rc72 GATED if 0 stuck shorts/overflow there).

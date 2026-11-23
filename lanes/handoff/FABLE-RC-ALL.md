# FABLE-RC-ALL handoff (Fable 5.2; independent root-cause reviewer, S81 + QC + KV + HEAD; started 11-23 05:50 PST)
Replaces FABLE-RC-S81, FABLE-RC-QC, FABLE-RC-KVHEAD (read their handoffs for history). Briefs: localhost scratchpad resume_1123b.txt, fable_review_brief.txt, rules.txt. Local notes: scratchpad/fablercall.
Die lanes for rejections / no-row gaps: S81-J9-ASSEMBLY-R6, S81-LEAF-J9, S81-SLICE-J9, S81-SVC-J9, S81-MISC-SERDES-J9, S81-COL-J9, HEAD-R18, QC-V4, KV-D29. Ledger owner now PRECHECK-LEDGER-R3.
## Schedule (PST)
- REASONED packets: S81 svc/leaf 09:30; HEAD 10:30; KV 12:30; QC 12:30.
- Re-review before cuts: HEAD 11:00; KV + QC 13:00; S81 16:30 (cut 18:00). Report to COORD at each cut, < 200 words.
## Log
- 05:53 TAKING posted (54a98250).
- 06:1x u_hold reset-relay verdict ACCEPT (e1346347): legs land on CLR pins of rst_sync/lock_sync 2-flop synchronisers (read in epyc10 s81-j6-r5/j8_cut_tree). Conditions for 16:30: CLR-only fan-out on J9-bound netlist; core_rst_n -> u_boot_release/rs_r recovery >= 0 at post-hook CTS (stays in RHI-RST).
- 06:1x S81 uncovered list posted (aeea97bd): SVC rc16/rc15/rc18/x1; SLICE rc37/rc35/x13/REPAIR-CAP violator/rc36; MISC-SERDES x14/x6/u_rrl eq legs/rc67 scans/iqf; COL rc72/CLOCK-SKEW col/p5 GRT-0116; LEAF CLOCK-SKEW leaf/t15/REACH; ASSEMBLY x9 + RHI rows.
- 06:1x QC re-check posted (293b26c1): rc97 unmeasured (btab_s4r harden4 running intel1); rc96 btw0g PRE FAIL 46 LANDREMAP (asked QC-V4 to show inherited); rc104 bind running; x5 ACCEPT REASONED with condition (0 DPL-0033 on first c4 st_a kit).
## Carried conditions (from predecessors, check at re-review)
- S81 16:30: SVC engine timing row (SRX=7+BAND+TILE_STAGE) and SVC-CUT-DEPTH present; residual hop lengths; SRX sized for 2748 um; serdes x14; CORETAP/FACETAP per-tap insertion spread; 0 GRT-0273 in probes.
- HEAD 11:00: r18z2 23e33a4497865202 static OK; cut accept needs ep3/wp3 census (E GRT vs 45,948; W hold vs 17,932; per-tap hold split on W clk_t56..t63 and 18 E ports at window 200; tx|tx 14 um slit; rc138 stripe; NDR: no GRT-0273, ov <10%). Codex: west spec 1123040001 manual placement FAIL (pin congestion, 8 opposite-face pins, clock entry 912 um).
- KV 13:00: D29 cut conditions R1-R6 (epyc8 kv-plan-r6/d29/D29_CUT_CONDITIONS.txt); rc118/119/121 pc; hroot placement FAIL (23 opposite-face pins, root entry 1647 um); x10 tapoff 30 UNEVALUATED; x15.
- QC 13:00: rc97 release number; rc96 probe; rc104; rc98 SEAT-1c; cb rows; coll_core + CBF q00 placement FAIL records.
- 06:1x HEAD W wp3 own view posted to HEAD-R18 (451e2844): tx SRAM row 6 um off u_rg2 N face (no row), W strip x0-65 conduit, rstart/run/rst broadcasts 650-1045 um, clk_t45 -> fclk_out_coll_o1 1.1 mm. Check each at 11:00.
- 06:2x COORD order: KV pre-review before the 11:30 D29 tools cut; causes without a row to KV-D29 + FABLE-OPEN-KV by 10:30; waiter through 18:00. DONE 06:2x: posts 48143c45 (hroot h1-h4, hgi g1-g3, hg: no HGFORM placed probe) + c41dac50 (pc p1 inner slits persist, p2 centre seam ring buses cap 0; manifest rows.json 29 rows lacks rc118, rc119, rc121 PCST, rc120, rc122, x15, rc117 TGR5 sysc, rc128 beyond pv_v3; RHI-KV is row 29 but the hroot RHI probe kit has no OT_TAP_RESET_SPLIT and OT_HOLD_IN_MIN -75 = RST/IO unproven on KV).
- Local renders read: scratchpad/fablercall/{head_wp3,kv/*}. Waiter: scratchpad/fablercall/wait_posts.sh <HH:MM> (background; exits on a post addressed to this lane; re-arm each time; lastline file holds the queue line number).
- KV 13:00 re-review checklist: h1 E-strip column < 0.7 on D29 placement; h3 o_next ring 616 um vs 330 ps; g1 hst2_t1 4-way fan-out; HGFORM placed probe; pc p1/p2 rows; manifest gaps above; RHI keys reaching a kit.

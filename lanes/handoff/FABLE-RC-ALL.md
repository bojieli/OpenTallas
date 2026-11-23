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

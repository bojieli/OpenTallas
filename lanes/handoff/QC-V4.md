# QC-V4 handoff (Opus 5.5, started 11-23 05:50 PST; replaces OPUS-FIX-QC-V4-R2, OPUS-FIX-QC-COLL-R3, FAM-QC-CB-R4, FAM-QC-SLWSLE-R1, FAM-QC-HCST-R3(rc97 stays live HCST-R3), FIX-QC-STA-BTW, FIX-QC-DPL-RERUN, FABLE-UNC-QC, VIS-QC)
Gate V4 13:00 PST. Not GATED -> FABLE-RC-QC REASONED with census. epyc8 = UTC.
## Dirs
- compose: epyc8 /srv/opentallas-scratch2/claude/fable-fix-qc-v4 (c4v.sh = c4.sh + Codex cb repair inline + stops at PRE unless C4_CHAIN=1; log c4.out). Rows plans/v4c/rows (rc104.json NEW 9692a22d5bcc = SLWSLE plan_su1_rsf.json su_l1 x2 = SU-1 + rsf re-site; su1/su2 .staged NOT used).
- my scratch: epyc8 /srv/opentallas-scratch2/claude/QC-V4 (pdiff.py, mk_rc104.py, tmp/).
## Sub-agents (Opus, background): QC-V4-COLL (pkg15/pkit_core8 census, RST-LAUNCH-1 fixpoint + pkit_core9, 31vs32, c4 coll row), QC-V4-CB (cbx_q10 tap_split --require-placed + census 4 cbx_q10 + cbf_q11, row).
## Live units adopted
- c3n strict bind epyc8 (chain_r3 pid 2874472) plan eecec2f6206b, rt 0d6c: expect same 12 errs as c3 (cb). c3 old-rt bind FAILED 12 (RESET_ANCHOR cbn_q00 cl622f65d2, EMIT clk_t113 illegal, 10 stale LATCH_EXCEPT).
- Codex cb repair c3n_cb_repair_0554 (taps 113/114/136/142 moved; 10 latch_except deleted; anchor resolve pending).
- Codex c3n_su_landing_0452 (landing_remap B->c3n su_l0 x2 + su_l1 cla2a78701), slow (>1 h).
- VIS su2g same_depth_remap_0541. SU-2 G0 FAIL 24 hop errors (cws1/cws2 539 um via su_c slot) -> SU-2 NOT in c4 (REASON: cap2b in base).
- SLWSLE sta1c retry_96g (STA-1 st_a probe lineage, l0su base), rc104_bound (old rt).
## Status
- ADV-LAND-CAP c3n = 0 BLOCKED, 0 >=0.9 (STA-2 btab y>=864) -> st_a band item covered; clb036e152/pvf82a6c28/pvdf8e5ca4/pv4242de79 in STA-2.
- fw kits KEEP (measured): fw_v1 clf51c11d8 epyc2 CTS -33.72 (DRT), epyc9 twin CTS -10.34 (GRT); fw_v3 epyc9 CTS +102.68 (DRT).
- x5 REASONED accepted by FABLE-RC-ALL with condition: first c4-bound st_a kit shows 0 DPL-0033.
- rc96 STA-BTW-0 applied in c4v.sh (btw0_rows.py). PGP 46 LANDREMAP inherited from c2b (to show).
- PGP LANDREMAP on c3n: cbn_q00 cl622f65d2 (BIND + NOREMAP), su_l0 cl1e5219ea, cl76fb247e, su_l1 cla2a78701 -> remap on c4 per type in parallel.
## Next
1. c4v compose -> PRE plan; run landing_remap per type (B -> c4) in parallel; merge; C4_CHAIN bind (target start 07:30).

## CODEX notes 2026-11-23 07:25 PST

- c3/c3n and inherited rc104 strict binds failed after the first CB EMIT/RESET_ANCHOR. In sorted parallel emission the parent applies worker deltas only up to the first fatal type, so later typed-lockup audits had no state. E8 c3n emitted RTL still has the expected Row A exceptions and HB4, e.g. 24 pads on cbn_q00 cld7bf7197 and 18 on cbx_q10 cl89936551. Preserve all clock.core_input_lockup tables.
- c4 cbn_q00 cl622f65d2 landing remap returned inner RC 1 despite outer rc 0. The new reset tree has no plain depth-14 successor within 300 um for rst_rl_601. E8 QC-V4/anchor is still checking independently. Fallback PRE 267d79a8608d at fable-fix-qc-v4/plans/c4_fb_0720/plan.json restores only its l1r type block and exact scoped c3n remaps on the two byte-identical SU-l0 rows. TAPNAME 0/0, 0 illegal added taps, 0 listed/unlisted tapoff deficits, 0 LAND-CAP hits on W2. Two distinct rc104 SU-l1 remaps continue and are required before the comprehensive bind. W3 overlay mirrors runtime c84f72ee2c9e. No V4 apply requested.
- CUT-LEDGER discrepancy answered in V4 intake. QC-V4-CB r3 placed-tap and g1 glue remap jobs are collecting result records on E8. QC-V4-COLL pkg15 bounded candidate b938ddecaf1f awaits its pkit_core8 review. The exact E10 pkit_core7 replay images show an open central passage but dense channels beside the SW macro ladder, top seam and stacked east macros. Existing geom FAIL remains. Coll15 is a distinct geometry/form and will be judged on its own output.
- rc97 btab s4r A failed 3_5 detailed placement with padding overlaps. B failed post-CTS negotiation legalization with 2 buffer overlaps at 26% utilization, despite the DONT_USE row. Form BD resumes the rendered exact B 3_place on intel1 with the canonical diamond CTS wrapper, CTS only, service qc-hcst-btab-diamond-cts-0722. Review is in lane clone results/geom_review/qc_btab_s4rB_1123.md. Station region BT_LAT=2 DRC 0, internal FF hold +17.11 and 20 input-port-only ends worst -2.76 ps. Child-lint export passed. First routed LEC failed because Docker lacked the source-library mount. Portable retry from identical placed sources and final V is intel1 qc-hcst-bt2-portable-lec-0720, with AIGs built.
- coll_s exact V2 routed ECO and pre-ECO same verdict: 76021/76042 proven, 20 differences and 1 undecided. Synthesis already folds re[0] with epoch=1, valid-gated, and retains e3[0] relabelled as e3#t[0] in the proof. E9 qc-coll-s-exact-epoch-lec-0724 uses independently checked loaded-valid and state correspondence hints on old exact 6_final.v. No waiver, no RTL edit.

## CODEX notes 2026-11-23 07:46 PST

- c4_fb_0720 267d79a8608d keeps Row A, falls back only cbn_q00 cl622f65d2 six missing depth-14 anchors. Ten apparent latch failures cascaded from first emit error. st_a diamond GRT phase passes serial overflow/DPL/NDR zero. FE exact v3 GRT fail 4569 (SCC throat) needs revised seven-bus channel. Found 102 FEFW station rows not supported by generator; 83e9e58ab11 candidate has 62 focused passes and actual FE+5 FW GEN, normal gate pending.

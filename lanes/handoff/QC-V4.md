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

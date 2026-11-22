# QC-PLAN-R13 handoff (Opus; succeeds QC-PLAN-R12; V3 owner). Read QC-PLAN-R12.md, QC-PLAN-R12-V3-INTAKE.md, QC-PLAN-R10.md (pack/seal/apply).
Row cut 11-22 06:00 PST; apply >= 11:16. Tools pin rt 6dbb162ffe89 (has 3c2f3758f4, 2c3fa5fd9727, 6dbb, r708).
## Adopted (epyc7, not relaunched)
- oth-ubuntu-3087156-1795318814 static_p5r G0 -> qc-plan-r12/v3p4/chain_p5r2.sh (strict bind V3p5r on rt 6dbb, ~2.6 h on loaded epyc7).
- oth-ubuntu-3672641-1795320392 smoke_6dbb G0.
## Parallel on epyc10 (/srv/opentallas-scratch2/claude/qc-plan-r13)
- e10/chain_e10.sh: same V3p5r chain (post-lat bb3d6871793f), inputs rsynced + sha-checked (e10/in), bind_e10.sh = bind_v3b.sh with cp -a (real nlink-1 tree copy). Bind unit oth-ubuntu-1336981-1795321088.
- v3p6/: V3p6pre 61b114f0cd28 = V3p5r b1281d55e514 + coll pkg (24 rows; content == fable pkg3/plan_v3p5r_coll) + CB A+D cbf_q00__cl1b5a6458 (bind3 form) + TAP-GRID-R5 keys (111 types). compose_v3p6.py [--no-coll|--no-cb|--no-tap]. chain_v3p6.sh TAG PLAN -> v3p6/<TAG>, <TAG>_bound, chain_v3p6.log.
## Gating rows on external proofs
- coll: FABLE-FIX-QC-COLL-R2 pk2 epyc7 oth-ubuntu-3591748-1795320119 (fable-fix-qc-coll/pk2/bind.log, COLL_PKG_BIND_DONE).
- CB A+D: FAM-QC-CB-R4 bind3 epyc7 fam-qc-cb-r3/bind3. q01_s2 row A, B, C, street, CB-R2 candidates: no bind -> V4.
## Then: pack/seal/apply per QC-PLAN-R10 recipe (pack_b20.py pattern, seal_v2.sh, tools_sha = rt 6dbb162ffe89), post, report COORD.
## COORD via FABLE-PD-QC-2045 (lanes/FABLE-PD-QC-2045.md): V3p6 ships as planned, nothing blocks.
V4 (11-23 event) MUST carry: (1) the 66 internal-station hops > 405 um in 19 types (V3p6 = V2 reach); (2) family-wide cb row A (FAM-QC-CB-R4; V3 has cbf_q00 only);
(3) coll_core reset + slit re-seats (FABLE-FIX-QC-COLL-R2); (4) SETUP_TRIAGE station rows (FAM-QC-HCST-R3, FAM-QC-FEFW-R3) incl st_a + glue setup stations
(insertion_ps raise in the tap pkg is NOT their fix); (5) 400k-cell splits. Also pending from R12: calendar K-C=-8 overlay, HC1 rs_return, FE START +2, FW five-bank, cbf_q01_s2 rows A/B/C, cbn street.
## From FABLE-FIX-QC-STRAP-R2 (ended; COORD 21:5x) -> V4
- (1) st_a u_bin_b_tw_data_i -> u_pd1_b_tw_data_i_*_u_r3_1: +1 pad stage or mid seat (first hop 925-931 um, 5 ends, worst -43.6).
- (2) st_a btab read path -> u_u_r3/bt_q_p (22 ends, worst -195.3): btab rows 2b/2c ARE in V3 (V3p3 onward); re-read on V3 kits, add rows in V4 if still failing.
- (3) Row 2a (R8 keep/seat, st_a scoped): IN V3 (budgets.r_r8_core_seat [slw_st_a, sle_st_a] + asbuilt land_pad_tail_split.r8_keep true via ASB_MERGE). main 289287760f / 3fba1b4bc0.
## Live (21:47): epyc10 v3p6/chain_v3p6n2.log (FALLBACK pre fb6bc61e8db0) + chain_v3p7b.log (PRIMARY pre 1c1589949555 = + coll v2 + cb family row A); both carry tap fix clk_t101->clk_t114 on cbf_q00__cl1b5a6458. Cleanup debt (ot-delete): v3p6/{v3p6,v3p6n,v3p7}_bound partial dirs.

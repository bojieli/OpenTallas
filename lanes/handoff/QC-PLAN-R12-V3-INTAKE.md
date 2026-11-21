# QC V3 intake ledger (QC-PLAN-R12)
Base V2 s29q103S4Q9N46R6V2 plan 7f9f8260349f. Row cut 11-22 06:00 PST; apply >= 11-22 11:16. Bind rt 31c7ccbd1b93 (v3t tools-only control: strict 0, LATCHECK 1921/1921; post-bind G0 + census running).
Gate: compose -> gen.py latency -> static G0 vs control -> strict bind 0 (bind_v3b.sh) + LATCHECK -> post-bind G0 vs b20 -> census -> pack/seal/apply.
Stop list: FABLE-PD-QC-1230 sec 3 (10 items). Packages: lanes/handoff/<LANE>-V3-*.json, posted to QC-PLAN-R12.

| # | package | lane | state | evidence / what is missing |
|---|---|---|---|---|
| 1 | sle_ctl x_su_l0_i pad = parent-tied count strap (before any su-path station) | QC-SLE-R5 | STAGED | QC-SLE-R5-V3-lane-count.json. Source merged 46590841483, exact asymmetric strict 0/LATCHECK 1921, E6/W5 equivalence and wrong-count mutant, M5 kit GEN pass. V2 composition preserves W cycles. |
| 2a | r8_keep=true + budgets.r_r8_core_seat [slw_st_a, sle_st_a] (R8S-1) | FABLE-FIX-QC-STRAP-R2 | STAGED | FABLE-FIX-QC-STRAP-R2-V3-sta-seat.json. Exact p1 cl9f post-hook TT −12.25 ps, seats 332/528, need_stage 0. Scoped to ST_A and paired with 2b. |
| 2b | st_a btab SRAM column ~250 um N (window 149-370) + per-type shifts clearing x_fw_ctl sites on g_btb[3] | FAM-QC-HCST-R2 | STAGED | Ranked 11 types in plan_v3p3. Old 3 fatal x_fw_ctl collisions have explicit per-bit sites. Same-count clf436 x_fe_o 259-bit banks max 269.19 µm. Current-runtime G0 running. |
| 2c | slw_st_a_v2__clf4365a62 face-home (5 core moves) be330101a1cf | FAM-QC-HCST-R2 | STAGED with 2b | lanes/handoff/FAM-QC-HCST-R2-row-clf4365a62.json |
| 3 | reach rows WITH sites (site-less multi-station ft slots, unchanged counts) | QC-PLAN-R12 sites helper | STAGED (289 FT rows) | Unchanged counts. Omits 2 ST_B and 6 ST_A cws0 proposals with new modeled core crossings. |
| 4 | st_b/hc splits, measured synth counts, shared split order | FLOW-STRIPBODY-1121 | HELD | Exact HC/ST_B census and feasible cuts available. Shared splitter still fails on QC landing metadata; no discarded clock/reset/param constraints. |
| 5 | cb taps stay t24/t25/t93/t100 (in V2); stations bc_i00/10/30, nb_i12, y_o00 after CTS | FAM-QC-CB-R2 | PENDING | p1 CTS reads |
| 6 | stm reset inst_taps cl7b3062fa tap79 / cl55be2264 tap51 (0 cycles) | OPUS-FIX-QC-SLE-R4 -> QC-SLE-R5 | IN | opus-fix-qc-sle-r4-rows/stm/stm_rows.json 2b2dfe128b06 |
| 6c | coll: 29 name-refresh rows only | FAM-QC-COLL-R2/R3 | IN | lanes/handoff/FAM-QC-COLL-R2-rows_reset_v3.json d312dd10fe2f |
| 7 | sle_ctl -440.70: relay sites at rp mux (0 cycles) + cws2_i variant C or reg-stage fallback | QC-SLE-R5 | HELD | Same-count variant C exact 3_place and independent CTS in progress; tap caps and TT/FF pending. |
| 8 | fw x_sc_i +1 station WITH sites (W su_c/sc E/W pad rule) | FAM-QC-FEFW-R2 | RECONCILE | V2 exact FW variants already instantiate five x_sc_i path banks, and FW V3 old tail is x_fe_p1_i. No duplicate station from V1 ECO. |
| 9 | taps over the sink cap: automatic tap split | TAP-GRID-R4 | PENDING | tool not landed |
| 11 | coll_core six defines + 2 face-codec stations 57bf4be9d132 | FAM-QC-COLL-R3 | HELD | Exact pkit8 still has 4.33 µm macro wall; pkit10 widened placement after fresh strict+LATCHECK and normal GEN. |
| T | tt_ctlm TTCTLM-R1: +1 register rank in u_75259 cone (cycles pre-approved) + lane latency row | QC-PLAN-R12 helper | PRIVATE | RAE CTS TT −36.34 ps, FF −121.93 ps. Zero-cycle native_cmd seam move into receiver corridor placing. Keep +1 fallback separate. |

Current trial: epyc7 `/srv/opentallas-scratch2/claude/qc-plan-r12/ctl_strap/v3p3_static/plan.json`, normalized SHA f5d51696a2eb, pinned runtime 55344f311cde. Unit in `v3p3_static/g0.log`. Contains 1, scoped 2a/2b/2c, 3, 6, 6c. Apply remains gated on static and post-bind G0, strict/LATCHECK, census and event-specific required geometry review.

## REJECTED (stop list / measured)
| package | reason |
|---|---|
| 23 hop300 station bumps | stop 2 (327-361 um, inside cap; sites on macros) |
| btab shift 345.6 um | stop 5 (window 149-370) |
| coll reset stations; re-point to rr_t<j> | COORD item 6; FAM-QC-COLL-R2 12:41: 27/27 hops <= 405 um |
| sle_ctl reset stations | R11 census: 3,656 reset nets, 0 hops > 250 um |
| any station without a site; su-path station before row 1; r_r8_core_seat beyond st_a | stops 3, 4, 6 |

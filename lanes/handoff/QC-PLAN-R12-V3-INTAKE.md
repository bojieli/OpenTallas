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

### 17:14 PST successor candidates and route holds

- HC3 four West types across twelve instances, exact R6V2 bound forms. The original four type names and base-type references are retained. The supported param_set explicitly records N_PAD 1/3/3/1 and S_PAD 0. This corrects the projection that previously gave the R6V1 and R6V2 forms the same scheduler keys. The signed R6V1 pvfd488b8f archive carries S_PAD 1 and different delivered cycles. An isolated strict and LATCHECK run is active on E7 unit 3623057 under qc-plan-r12/ctl_strap/hc3_projection. The native receipt has the exact four affected forms and compiled member sets.
- HC1 e3b3a82fceac. The original GRT path on clk is u_bin_rs_n1/q[443] to u_bout_x_st_b_o/q[383], −901.46 ps. Actual placement has 393 of 516 beyond 405 µm, worst 595.728 µm. Same lane latency retime moves one of six stations from each of two unique ST_B receivers to the common HC1 source. Explicit 517-site source bank models 298.89 µm on data and 274.536 µm on epoch. Two five-bank receiver plans model 176.31 and 179.28 µm. The native run is E7 unit 3671493 under qc-plan-r12/ctl_strap/hc1_rs_return. It must verify both delivered 16-cycle lanes and the emitted stage counts before intake. Current geometry remains held.
- Collective FTC E9 exact private wide_r3 placement and image reviewed. Old DRT 7-µm tile has zero cells and the 50-µm halo has 336 cells and zero ring FFs. Peak 20-µm bin rises from original 1,608/376 cells/FFs to 1,900/556. The narrow L-shaped concentration remains. Actual 66 register captures exceed 405 µm, max 881.04. Detailed-place WNS is −166.03 ps on tl_st_wi_i[63] to its ring capture (r2 −183.39, same bus bit 1023). Route hold remains. Actual image and counts in E9 fam-qc-coll/pkit9_spread/wide_r3/read. A pin-span aligned west band is being modeled, with exact measured pin y spans 806.176–1031.968 µm.
- SU cap candidate E7 unit 3366960 is native binding only. 43 additional taps corrected exact West SU C retained in-memory reach from peak sinks 10,877 to all at or below 1,000 without moving existing sites. Continue with the separate reset-locality candidate after native tap and reset identities are available.

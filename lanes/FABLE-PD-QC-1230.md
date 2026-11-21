# FABLE-PD-QC-1230 2026-11-21 12:30 PST: structural review of QC plan event V2 (s29q103S4Q9N46R6V2, live tree qwen_compute_v2r10)

Reviewer: FABLE-PD-QC-1230 (Fable). Read-only: nothing launched, cancelled, deleted or patched; no ot-run job. Technical PD only.
The 2026-11-19 review that had this file name is kept unchanged below the line "PREVIOUS REVIEW".
Marking: **V** = read or computed by me this round from the named file. **R** = reported by the named lane. **I** = my inference. **P** = proposal.
Sources (V), all on epyc7 `/srv/opentallas-scratch2/claude/qc-plan-r9/`: `b20/tree/.../plan_of_record/zz_s29_qc103_s4q9n46r4_final_preview.json`
(the b20 plan, 7f9f8260349f, 130 types / 377 partitions / 637 ft slots), `b20/post_bind/g0/g0_report.json` (PASS, 0 errors, 543 warnings),
`b20/post_bind/event/EVENT-CENSUS.tsv`, `b20/proof_gen/*/gen/*` (8 GEN kits), `cells_census.tsv`, `v3rows/r8_straps_rows.md`;
intel2 receipt `qwen_compute_atomic_apply_1795288459577088225.json`, `failure_breakdown.py` 11:55.
Fix rules applied: 833 ps fixed; hold structural; setup by stations or pipeline stages; no die or outline growth; cores move or rotate only.

## 0. Headline

1. **The pin-in-reserved-clock-site class found on KV does not exist on QC (V).** The V2 plan has 0 `clock.reserved_sites_um` rows in 130 types
   and no `die_islands_um`; no QC kit has a `reserved_sites.tcl` (8 of 8 V2 proof GEN kits, and the V1 and V2 wave run dirs on epyc7).
   `kit_pin_site_check.py` (rt a13768301176) therefore reports `ERR ... reserved_sites.tcl` on every kit and can find nothing. QC forwards its
   clock partition to partition (`clock.spine.feed.form = fwd`, `landing_network`), so there is no die clock cell inside a type. No action.
2. **V2 is V1 plus rows; the reach debt is unchanged (V).** 43 ft slots in 40 types have span / stations over 405 um, 66 internal-station hops
   are over 405 um, and 300 slots with 2 or more stations have no site at all. The 23 hop300 slots went back to V1 station counts.
3. **One sle_ctl type serves 12 E and W slices only because a derived pad happens to be equal (V).** Three binds split the type before b20;
   b20 fixed it by adding a 33rd station to a W chain. Every V3 station row on a su_l0 / su_l1 path can split it again.
4. **st_a cannot sign on V2: neither the strap seat nor the btab fix is in the plan (V).** `budgets` has no `r_r8_core_seat` key. The btab read
   needs the SRAM group 150 to 370 um north by the lanes' own slacks (I); the 345.6 um shift that collided was larger than needed.
5. **9 of 19 types measured after GRT are over 400k cells, and the G0 estimate is about 56k low on the two hc types it can be compared on (V).**

## 1. Structural risks in V2, with evidence

### 1.1 sle_ctl E/W: one type held together by a coincidence
- V: partitions `sl_E0..5_ctl` and `sl_W0..5_ctl` are all `sle_ctl__cla4f6f12f` (12 instances, 224,926 plan cells, G0 estimate 360,311 after resize).
- V, plan `latency.lanes`: E `x_su_l0_ctl` lanes 30 to 31 cycles, 9 to 11 stations, landing 6 to 8, pad 3. W lanes 58 to 59 cycles, 37 to 38 stations,
  landing 8, pad 4. E `x_su_l1_ctl` fixed 10, W fixed 9.
- R (QC-PLAN-R10): b17 strict bind TYPE_SPLIT into 4 variants, b18r and b19 E vs W on `x_su_l0_i`. b20 passed after `slw_su_c` `x_su_l1_ctl`
  went 32 -> 33 stations, the new stage "at the midpoint of a 40 um hop".
- Risk (I): the bind pad on `x_su_l0_i` is (su_l1 group arrival - su_l0 stations and landing). It is equal on E and W by arithmetic, not by design.
  The 12 ENDPOINT_REACH slots and the 23 reverted slots all sit on these paths, so V3 will move it.
- Fix (P): carry the `x_su_l0_i` pad as a parent-tied count strap. The type already has 23 `count_straps` (for example `strap_ca_k_b_tw_data_i`,
  6 bits), and the pad bank is the same `ot_dp_dly_cnt` form. E and W then differ only in a tied value, and su-path station rows are free.

### 1.2 W-side lanes are 28 cycles longer than E, carried by dense station chains
- V: `slw_su_c__cl19bb38ef` / `cl92142dac` (6 instances) `x_su_l1_ctl`: 33 stations x 456 bits = 15,048 flops, sited hops 20 um minimum, 38 um median.
  `sle_su_c` on the same outline (1226.88 x 1399.68) and faces has 4 stations.
- V: `slw_fe_v1` (3 types) and `slw_fe_v2` (2 types) `x_su_l0_ctl`: 34 to 35 stations, 15,504 to 15,960 flops, no `regs_um` (placer-free). `sle_fe` has 6.
- V, G0 `xtap_latency`: 22 hops in `slw_su_c__cl19bb38ef` (at least 9 on `x_su_l1_ctl`, the rest on cws1, cws2, x_su_l0_stm) go between different tap ports,
  window 235 ps against 50, no `clock.ft_hop_lockup`.
- Risk (I): 32 zero-logic hops of 20 to 40 um, some across taps, are a hold class by construction, and one of these chains is now the E/W equaliser.
- Not determined: what the 28 extra W cycles align to. Lane `natural` equals `cycles` (pad 0), so the stations themselves set the 58.
- Fix (P), after 1.1: stations by distance only (3 to 4 on about 800 um, as on E), the remaining cycles as one same-tap `ot_dp_dly` at the landing.
  Same lane cycles, no cross-tap zero-logic hop.

### 1.3 Station and hop lengths against the 405 um cap
- V, ft slots, span / stations (G0's own estimate: width, height or their mean by faces):
  - over 405: 43 slots, 40 types, 12,657 bits (46,393 with instance counts). `x_fw_ctl_p2` 490 um, 2 stations, all 12 st_b types; `x_hc3_ctl` 665, 1 station,
    7 hc2 types; `x_su_l1_stm` 657, 3 su_c types; `x_st_a_fe` 505 on 4 su_l0 / su_l1 types and 409 on 4 fw types; `x_fw_st_b` 409 on 5 fe types;
    coll_ftm 4 slots 1,128 with 1 station; cbx_q10 `a22` 1,884 to 1,901 with 1 station; sle_ctl `x_hc1_st_b` 428.
  - 300 to 405: 67 slots, 47 types, 31,521 bits. Inside the close-by-construction cap; they need sites, not stations.
- V, sited `regs_um` hops: 0 over 405, 212 between 300 and 405 (st_a_v2 cws0 361, x_fw_ctl 370, b_hw_ctl_hc0 336; slw_sc_v1 311 on 7 slots; cbn_q01 320).
- V, internal stations (5,592 hops): 66 over 405, 207 between 300 and 405. Over 405: cb `bc_i00` / `bc_i10` / `bc_i30` 611 to 637, `nb_i12` 411 to 418,
  `y_o00` 413 (17 cb types); slw_stm (4 types) `flt_o` 548; sle_ctl `x_fw_p2_i` 432. G0 `routed_reach` has the same 60 rows; G0C marks 28 rows incomplete.
- V: 300 slots in 62 types (107,171 bits) have 2 or more stations and neither `regs_um` nor bit sites. Largest: coll_ftc 26, sle_stm_v1 22, native59 21,
  slw_stm_v2 20, sle_stm_v2 20, coll_ftm 18.

### 1.4 The 23 hop300 slots reverted to V1
- V, their state in V2:
  - st_b `x_su_l0_ctl`: 3 stations, no sites, 327 um per hop, on 11 of 12 st_b types (`sle_st_b_v1__pvc5a85fd4__pv7b7fafb4` kept 5 sited stations at 196 um).
  - `slw_st_b_v2` (3 types) `b_hw_ctl_hc3`: 4 stations, no sites, 1,574 bits. The other 9 st_b types have 5 stations with bit sites at 262 to 265 um.
  - st_a_v1 (6 types) cws0: 5 stations, no sites. st_a_v2 (5 types) cws0: 4 sited stations at 361 um.
  - `sle_fe_v1__cl8210183c` `x_su_l0_ctl`: 6 stations, no sites. native59: 21 site-less slots of 3 to 4 stations.
- R (QC-PLAN-R9 / R10): the bumps failed G0 because `ft_spread` put the new sites on macros and the per-slice pads became 2 / 4 / 3 / 4 / 1 / 4.
- Reading (I): the reverted slots are at 327 to 361 um, inside the 405 cap. They were short of sites, not of stations. Three of the 12 st_b types
  (slw_st_b_v2) now differ from their 9 siblings on `b_hw_ctl_hc3`, which works against the family merge G0 asks for (29 near-duplicate groups, 91 types).

### 1.5 Clock tap placement
- V, G0 `tap_sink_cap`: 393 taps over the 1,000-sink cap in 106 types, largest 2,501 (`slw_st_a_v2__clf4365a62` clk_t129). coll_ft clk_t4 / t5: 2,264 / 2,182
  sinks at radius 262 um against 200.
- V, failure_breakdown 11:55: 3,251 measured taps in 34 types, 77 over 1,650 sinks, insertion max 493 ps (p50 268, p90 285), skew max 137.
- V, G0 `timing_audit`: the early core tap declares 250 ps and measures 290.7 to 301.7 on 4 st_a types (over the 40 ps tolerance by 0.7 to 11.7).
  219 core rows in 74 types have no measured clock depth; the LIB fallback would fail 93.
- V, G0 R-REACH-4: 16 types have forwarded-clock outputs on a tap more than 405 um from the pin while another tap is 12 to 120 um away
  (sle_ctl `fclk_out_b_hw_hc2_o` on clk_t255, nearest clk_t265 at 47 um; coll_core 11 outputs; slw_hc2 4 on the far root).

### 1.6 Reset reach
- V, G0 R-REACH-5 `edge_reach`: 66 raw reset hops over 405 um in 5 types: coll_ftc 52 (worst 1,190 um), sle_ctl 10 (1,422), coll_core 2 (1,217),
  `cbn_q11__cl5cc92dfe` 1 (437), `slw_hc0__cl4f54b7a3__pvde134a90` 1 (424). `start_raw_net`: coll_ftc 7, sle_ctl 7, slw_hc0 3, coll_core 2 nets
  are not in the plan's reset tree.
- V, G0 R-REACH-6: 39 types have a ring reset whose loads span 486 to 1,259 um with one same-cycle copy; 4 of them (2 sle_hc2, 2 slw_hc2, 486 to 525 um) get none.
- R: sle_stm_v2 `u_core.rst_n` on tap 0, leg 699 um; row 2b2dfe128b06 (tap 79, 190 um) is not in V2. cbf_q00 `inst_taps` t93 / t100 measure 525 / 506 um;
  V2 carries those old rows (re-pick t77 / t76 gives 75 / 135).

### 1.7 Pin faces and seams
- Reserved-site class: none, see headline 1.
- V, G0 R-REACH-3 `window_far`: 28 types have face buses more than 200 um from their consumer. cb `nb_i00` 514 bits x 1,938 to 1,964 um; sle_ctl 22 buses,
  8,530 bits, about 28,585 face-net buffers by G0's estimate; glue 21 buses.
- V, G0 `core_faces`: coll_core 8 core ports face away from their partner (`wd_in` 546 pins, 279 on the far side), sle_su_c 11, glue 7.
  The face rule is unchecked on all st_b types (20 of 20 cores without connectivity), st_a_v2 (14 of 14), tt_ctlm, coll_n. sle_su_c and both slw_su_c have cores without a LEF.
- V, G0 `street_die_leg`: 41 die-level lane stations (`rsn` / `rsf`) lie inside hard cores of su_l0 / su_l1 and cbn.

### 1.8 Types over 400k cells
- V, `cells_census.tsv`: 19 types have a post-GRT count, 9 are over 400k:

| type | synth | post-GRT | growth |
|---|---|---|---|
| slw_st_b_v2__pvc2ec5bfb | 364,445 | 506,723 | 1.39 |
| slw_sc_v1__cl63e5a7a2 | 273,484 | 486,060 | 1.78 |
| slw_hc1__cl68f9248e__cl144ee7b3 | 365,110 | 482,222 | 1.32 |
| slw_hc0__cl1bc59e1c | 343,544 | 459,853 | 1.34 |
| slw_fw_v2__cl8f84514c | 254,839 | 453,801 | 1.78 |
| sle_hc0__cl05696ed1 | 334,366 | 447,140 | 1.34 |
| sle_stm_v1__cl27746664 | 262,717 | 424,813 | 1.62 |
| sle_fe_v1__cl1cbb7497 | 242,816 | 408,932 | 1.68 |
| slw_stm_v2__cl1ca9c415 | 273,205 | 405,251 | 1.48 |

- V: 24 types are flagged NEAR_350K at synth (353k to 394k: 12 st_b, 12 hc); only 2 of them have a GRT number. At the measured 1.32 to 1.39 the other
  22 land at 465k to 548k (I).
- V: the G0 cell estimate gives hc0 `cl05696ed1` 390,617 and hc1 `cl144ee7b3` 426,323 at GRT; measured 447,140 and 482,222. It is about 56k low on both.
- I: two different causes. fw / sc / stm / fe grow 1.48 to 1.78 from buffers (far windows, hold pads), so the cure is structural hold and window moves.
  st_b and hc start at 365k to 394k and exceed the cap on normal growth, so they need a split or a type cut.
- Not read: whether these 9 runs signed, died or were stopped.

### 1.9 btab -> u_u_r3 at -124 ps (st_a, 11 types)
- R (FABLE-FIX-QC-STRAP, a3 kit final `5_1_grt.odb`): `g_read[*].q -> u_u_r3/bt_q_p` -124.3 on 22 ends, 668 ps of wire over about 800 um.
  Other slacks: g_read -> r0 +377, r1 +417, r2 +148; r0 `bt_word` -> SRAM +309; SRAM -> g_read +58 to +225.
- V, V2 plan `slw_st_a_v2__cl9f076a5c` (622.08 x 1339.2): cores `u_r0` y 78 to 240, `u_r1` 406 to 568, `u_r2` 752 to 914, `u_r3` 1,089 to 1,251, x 233 to 430,
  one master `sta_region_nb0_h15_n9_s11`. The four btab SRAMs (95 x 41) sit at y 285 to 490: two at x 449 to 544, two at x 207 to 371 under `u_r1`.
  V2 did not move them.
- I, from the lane's slacks at 0.835 ps/um (668 ps / 800 um): moving the SRAM group and `g_read` north by X um gives r3 -124 + 0.835 X, `bt_word` +309 - 0.835 X,
  r0 +377 - 0.835 X. All three are at or above 0 for X between 149 and 370 um, and above the -42 gate from 99 um. The 345.6 um shift that collided was near the top
  of that window.
- Fix (P): a 1 x 4 SRAM column at x 449 to 544, y about 580 to 750 (X about 250), beside the r1 / r2 corridor. The corridor itself (reset tap 311,674; cws0
  station 376,669.6) stays. The stations now in that column (ist 0 at 506,622; ist 4 / 5 at 438 to 455,727; about 165 relay sites) move into the vacated
  y 285 to 490 block or the strip x 410 to 445. Fallback: +1 cycle on the bt read (BT_LAT is a core parameter, so every region-core master is re-hardened).
- Not checked: the fit of the column against `cl_x_ctl_fw_i` (x 553 to 600, y 467 to 575, a 9 um slit today) and the re-sited hop lengths.

### 1.10 R8 strap seats (main 289287760f)
- R: 289287760f and 3fba1b4bc0 are on main (11:26). MERGE-QUEUE flagged 3 schema-key tests red on 289287760f at 11:23; 3fba1b4bc0 regenerates the schema.
  I did not read whether main is green now.
- V: the V2 plan `budgets` has no `r_r8_core_seat` key, so no V2 kit runs the seat pass. The a3 numbers (4 ends at -333.6, one merged flop driving
  4 cores over 1,067 um; `rs_n_hi_p` -33.7 with a last stage 439 um from the pin) stand for every V2 st_a kit (I).
- R: dry run 404 of 528 pins seated, 124 tails kept, chain hop max 250.6 um, 0 need a stage. No timing result. Private strict bind b1 ended rc 0 at 11:51; result not read by me.
- Open (R): sle_ctl a5 -440.70 has not been read from the placed DB; sle_su_c has the same latent chain merge. The opt-in list covers st_a only.

## 2. Ranked fix list for V3

| # | Fix | Evidence | Types | Owner |
|---|---|---|---|---|
| 1 | sle_ctl: `x_su_l0_i` pad as a parent-tied count strap, so E and W can never split the type. Do it before any su-path station row | 1.1: 3 TYPE_SPLIT binds, fixed by a 33rd station | sle_ctl (12 instances); unblocks rows 2 and 3 | QC-SLE-R5 (RTL + bind proof), QC-PLAN-R11 (rows) |
| 2 | st_a: `r8_keep` + `r_r8_core_seat` rows after the b1 proof reads, and the btab SRAM column 250 um north (1.9). Both are needed | -333.6 on 4 ends, -124.3 on 22 ends | st_a 11 | FABLE-FIX-QC-STRAP-R2 (seat proof on cl9f076a5c), FAM-QC-HCST-R2 (btab floorplan row + private kit), QC-PLAN-R11 |
| 3 | Reach rows with sites: +1 station and `regs_um` on `x_fw_ctl_p2` (12 st_b), `x_hc3_ctl` (7 hc2), `x_su_l1_stm` (3 su_c), `x_st_a_fe` (8), `x_fw_st_b` (5), coll_ftm 4 slots, cbx `a22`. Every new station gets a site off the macros in the same row | 1.3: 43 slots over 405 | 40 | QC-PLAN-R11; FAM-QC-HCST-R2 (st_b, hc2), FAM-QC-FEFW-R2 (fe, fw), FAM-QC-COLL-R2 (coll_ftm), FAM-QC-CB-R2 (cbx) |
| 4 | Cells: read the outcome of the 9 over-cap runs; split or cut st_b and hc (strip / body schema); for fw / sc / stm / fe remove the buffer causes (rows 6, 8) first. Correct the G0 estimate by the measured growth | 1.8: 9 of 19 over, 22 more projected 465k to 548k | st_b 12, hc 14, 5 others | QC-PLAN-R11 (census, split rows), FAM-QC-HCST-R2 (st_b, hc), FAM-QC-FEFW-R2, QC-SLE-R5 |
| 5 | cb: re-picked `inst_taps` (cbf_q00 t24 / t25 / t77 / t76; same re-pick for cbn_q01 and siblings on placed positions), then +1 internal station on `bc_i00` / `bc_i10` / `bc_i30` (611 to 637) and `nb_i12`, `y_o00` (411 to 426) | 1.3, 1.6: 60 routed-reach rows; 525 / 506 um reset legs | cb 17 | FAM-QC-CB-R2 -> QC-PLAN-R11 |
| 6 | Reset: `reach_rules.py fix --rules 1` on the 19 START nets outside the tree, relay rows for the 66 raw hops (coll_ftc 52, sle_ctl 10), stm `inst_taps` row 2b2dfe128b06, a second same-cycle copy where a ring reset spans over 810 um | 1.6 | coll_ftc, coll_core, sle_ctl, stm 2, about 20 ring types | FAM-QC-COLL-R2 (coll), QC-SLE-R5 (sle_ctl, stm), QC-PLAN-R11 (ring copies) |
| 7 | Clock: `reach_rules.py fix --rules 4` (forwarded outputs onto the nearest tap, 0 cycles); split the taps over 1,650 sinks; early core tap declared at its measured depth (291 to 302) instead of 250 | 1.5: 16 types, 77 taps, 4 st_a types | 16 + 34 | QC-PLAN-R11; FAM-QC-HCST-R2 (st_a taps), FAM-QC-COLL-R2 (coll_ft t4 / t5) |
| 8 | fw: +1 station on `x_sc_i` (rows already written); face windows of sle_ctl and cb moved toward their consumers where the bus keeps its seam partner | -49 to -84 routed (R); 1.7 window_far 28 types | fw 4; sle_ctl, cb | FAM-QC-FEFW-R2, QC-SLE-R5, FAM-QC-CB-R2 |
| 9 | Sites for the reverted slots at V1 station counts: `regs_um` / bit sites for st_b `x_su_l0_ctl` (11 types), slw_st_b_v2 `b_hw_ctl_hc3` (copy the 9 siblings' 5 sited stations, +1 cycle on 3 types), st_a_v1 cws0, native59 | 1.4 | st_b 12, st_a_v1 6, native59 | QC-PLAN-R11, FAM-QC-HCST-R2 |
| 10 | W chains: stations by distance, the rest of the cycles in one same-tap delay at the landing (after row 1); until then `ft_hop_lockup` on the 22 cross-tap hops of slw_su_c | 1.2 | slw_su_c 2, slw_fe 5 | QC-SLE-R5 (su_c), FAM-QC-FEFW-R2 (fe), QC-PLAN-R11 |
| 11 | coll_core: the six defines as one row set after the pkit4 read; re-pin `wd_in` of `u_pring` / `u_rring` `g_b[1]` to face W | pkw4 -255 (R); 279 of 546 pins on the far side | coll_core, coll_ftc | FAM-QC-COLL-R2 |

## 3. Stop list

| # | Do not | Why |
|---|---|---|
| 1 | Run `kit_pin_site_check.py` as a QC gate, or add `reserved_sites_um` rows to QC | No reserved site exists on QC (headline 1) |
| 2 | Re-add the 23 hop300 station bumps per slice | They are at 327 to 361 um, inside the cap; the bumps put sites on macros and split sle_ctl |
| 3 | Add a su_l0 / su_l1 / su_c / sc / st_b station row before fix 1 lands, or fix the next E/W split with another station | 1.1, 1.2: the last one cost a 33rd station at a 20 um pitch |
| 4 | Add a station without a site | 300 site-less slots already; b17 failed G0 on exactly this |
| 5 | Shift the btab SRAMs by a full 345.6 um, or relaunch st_a with only one of the two fixes | Window is 149 to 370 um; -333.6 and -124.3 are separate paths |
| 6 | Extend `r_r8_core_seat` beyond st_a before the cl9f076a5c proof has a routed timing result | The seat is a dry run only |
| 7 | Relaunch st_b or hc types unchanged and expect them under the cap | Measured 447k to 507k; the estimate is 56k low |
| 8 | Hold-buffer repair as the cure for the cross-tap station hops, or the general lockup form on QC | 22 hops at a 235 ps window; QC general lockup moved TT -1.82 -> -133.98 (R) |
| 9 | More repair passes on straps or on cb reset legs of 500 um | Structural: merged chain, far tap |
| 10 | Treat G0 PASS as reach closure | PASS is 0 errors with 60 routed-reach, 43 geometry and 92 reach warnings |

## 4. Not checked

- No placed or routed DB was opened this round. Every timing number is the named lane's (R).
- Span / stations is G0's face-based estimate, not a pin-to-pin length; `die_hop_scan.py` was not run on V2.
- Why W lanes carry 28 more cycles than E; whether the slw_fe chains were the same in the plan slw_fe_v1 cldb4efe33 signed on.
- Which 6 st_a types R9 counted as reverted (st_a_v1 has 6 site-less cws0 slots, st_a_v2 has 5 sited ones).
- Outcome of the 9 over-cap runs; the b1 strict bind result; whether main is green after 3fba1b4bc0.
- The 41 `street_die_leg` warnings were counted, not interpreted.
- The V2 wave: KIT-WAVE posted at 11:50 that TOOL-SKEW refused QC launches on the v2r10 tree (229 modules differ from main). Not a PD item; QC-PLAN-R11 has it.
- Slips of mine: one temp file written to `/tmp` on intel2 (failure_breakdown output), removed with ot-delete; read-only `git log` on two files in `~/coord`.

---
PREVIOUS REVIEW (2026-11-19, unchanged)

# FABLE-PD-QC-1230 2026-11-19 12:50 PST: QC coll_core wall, cbn_q11 stretch, st_a detours, N4.6f3 / N4.6e structure

Reviewer: FABLE-PD-QC-1230 (Fable). Read-only: no job launched, killed or patched. Technical PD only.
Marking: **V** = I opened the report, LEF, plan or render this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Sources (V): epyc9 `qc-coll-core-1118/c5,c20.rpt` (attempt_7), `qc-plan-r3-n41p/pkits/pk45_coll/gen/coll_core` (congestion-5.rpt,
tt_setup_repair.log, smells.json, density.png, macros/*.lef), `n46/plan_n46_g3.json` (carries f3), `n46g.py`, `n46f2.py`, `n46f3.py`.
Levers of FABLE-CLOSURE-STRATEGY 11:45, QC-PLAN-R3, SONNET-FIX-QC and QC-OWN-1119 are not repeated here.

## 0. Headline

1. **coll_core does not fail on bus bundles crossing a wall. It fails on macro pin faces that have no channel (V).** 75 % (attempt_7
   round 20) to 90 % (pk45_coll round 5) of the overflow sits inside the bodies of g_xf_1 / g_xf_2 and the two u_rring SRAMs, where the
   router has 5 H + 6 V tracks per gcell against 26 to 27 on open floor. Each fold slice has 512 `src` pins on its west face, and those
   faces look into slots of 4.3, 13.0 and 4.3 um. Fix = move cores (no re-shape), section 1.
2. **pk45_coll (the N4.5 form) repeats attempt_7, worse (V).** Round 5 sum 75,675 (attempt_7 round 5: 46,172); placement TT after repair
   -997.94 ps, tns -691,971. It will not give a usable GRT TT. Stop list item 1.
3. **cbn_q11: two 516-bit register groups share the same six column anchors (V).** The N4.4 row put `u_x_3_3.u_st.b_d` on the sites of
   `u_d6_u_fab_u_x_3_2_a_d.q`. Both cbn_q11 types carry it. Section 2.
4. **N4.6e moves the x_fw_ctl station into a channel that already holds two ft stations, and the bin site leaves two consumer legs over
   405 um (V from plan geometry).** Section 3 and 4.
5. **N4.6f3 has no proof kit on its own type, and cbf_q00 keeps four 625 to 637 um legs (V).** Section 4.

## 1. coll_core congestion

### Evidence
- V, overlay of every overflow row on the plan hard-core boxes (reports are capped at 10,000 H + 10,000 V rows, so sums are floors):

| report | sum | inside a core body | within 8 um of a core edge | open floor |
|---|---|---|---|---|
| attempt_7 round 20 (c20) | 33,087 | 24,795 (75 %) | 7,364 (22 %) | 811 (2.5 %) |
| pk45_coll round 5 | 75,675 | g_xf_1 + g_xf_2 alone 67,775 (90 %) | about 3,400 | under 1 % |

- V, c20 by core: g_xf_2 H 5,554 + V 2,274; g_xf_1 V 3,335 + H 2,065; u_rring g_b[0] H 4,864 + V 1,308; u_rring g_b[1] H 2,623 + V 1,361;
  u_pring 1,411. **g_sring has no row in the top 24**: the SRAM column at x 449 is not a hotspot (correction to the 12:04 post).
- V, capacity printed in the rows: inside a fold slice H 5 (4 to 6), V 6, and V 0 on 574 + 471 gcells (pk45); inside the 32x546 SRAM
  H 8, V 10; open floor 26 to 27. Gcell 0.57 um. The fold-slice LEF obstructs M1 to M5 over the full body, so only M6 / M7 pass.
- V, LEF pin faces: `ot_coll_fold_slice` 190.08 x 211.68: `src[512]` + `red_in` on the **W face, M4**, y 32 to 179; `sum[128]`, `e_out`,
  `v_out` on the E face, M4; clk / rst_n on S, M5. `ot_sram_1r1w_32x546`: 826 pins W (rd_out 546, wd_in 267), 825 pins E (w_mask 546,
  wd_in 279), all M4.
- V, plan geometry (plan_n46_g3 coll_core, 786.24 x 1589.76):

| pin face | pins | channel in front of it |
|---|---|---|
| g_xf_0 W (x 8.6) | 513 | 4.3 um of core to the die edge |
| g_xf_0 E / g_xf_1 W (x 198.7 to 203.0) | 130 + 513 | 4.3 um slot |
| g_xf_1 E / g_xf_2 W (x 393.1 to 406.1) | 130 + 513 | 13.0 um slot |
| u_rring g_b[0] E / g_b[1] W (x 221.0 to 241.9), same on u_pring | 825 + 826 | 20.9 um, and its north end meets g_xf_1 after 5.4 um |
| u_rring top (y 1100.5) to wall bottom (y 1105.9) | - | 5.4 um E-W |

- V, the overflow follows the faces, not the bundle paths: V overflow inside g_xf_2 is 2,012 of 2,274 in x 400 to 420 (its W face);
  inside g_xf_1 it is at x 200 to 240 and 360 to 400 (both edges); open-floor V overflow is 3,175 at x 220 to 240 (the SRAM gap) and 3,348
  at x 380 to 420. H overflow inside g_xf_1 / g_xf_2 is at y 1120 to 1220.
- V, pk45 placement density (smells.json): 0.87 to 0.88 in six bins at x 399, y 1109 to 1289, i.e. the 13 um slot is full of cells.
- V, named nets in the overflow rows of g_xf_1 / g_xf_2: `u_cland_io_collective__in_data/u_ring.dch[*].u_dsel` 14 to 21 %,
  `u_bout_rec_tx_s0` 4 to 16 %. in_data is 512 bits and `src` is 512 bits (I: the in_data read side is the `src` driver of the four
  x-fold slices, so every bit must reach four W faces).
- V, density.png: the east strip x 600 to 786 above y 900 and the band x 40 to 450, y 717 to 907 are empty. Room exists.
- V, pk45 `tt_setup_repair.log`: before -1100.83, after -997.94, tns -691,971, 926 cells added, 406,163 instances.

### Root cause
A 4.3 um slot holds about 7 gcells x 27 = 190 V tracks; a 13 um slot about 620. Each must serve 643 M4 pins. The nets therefore arrive
over the slice on M6 at 5 tracks per gcell and drop to M4 at the face, and the SRAM gap (1,651 pins in 20.9 um) has no north exit. The
N4.5 / N4.6 station rows ("wires cross cores on M6/M7") add demand on the same two layers. No GRT setting fixes a pin face without a channel.

### Fix, ranked (P; core moves only, r-core-shape respected; coordinates to be snapped by the plan tool)
1. **Wall respace (plan row, QC-PLAN-R3 composes, rows by QC-COLL-CORE-1118 or a new lane QC-COLL-WALL).** 48 um channel in front of
   every `src` face: g_xf_0 x 8.6 -> 51.8, g_xf_1 203.0 -> 289.9, g_xf_2 406.1 -> 528.0; g_pf_3 follows g_xf_0, g_xf_3 follows g_xf_2.
   3 x 190.1 + 3 x 48 = 714 um of 777 um core. The open channel above g_xf_1 keeps both N4.6 tx station sites clear.
   Expected: 48 um = 84 gcells x 27 = about 2,270 V tracks for 643 pins (28 % use, was over 100 %); removes the cause of 75 to 90 % of
   the overflow. Pass mark for the proof kit: round-5 sum under 5,000 and inside-core share under 30 %.
2. **SRAM field (same row).** u_pring / u_rring g_b[1] x 241.9 -> 300 (gap 79 um for 1,651 pins), g_sring column x 449.3 -> 530 (gap
   52 um, y unchanged: moving it south would hit g_pf_0). u_pring + u_rring rows 60 um south into the empty band (u_rring top
   1100.5 -> 1040.5): a 65 um E-W channel under the wall, about 2,960 H tracks where there are 5.4 um today.
   Expected: removes the u_rring / u_pring share (13.2k of 33.1k in c20).
3. **in_data bin site (plan row).** coll_core relay_sites cover rec_rx_s0 / s1 / s2 and fltv_s only (V); `u_bin_io_collective__in_data`,
   in_tag and cmd have none. With the channels of fix 1, site the in_data bin north of the wall (x 242 to 528, y 1330 to 1560) so one
   registered 512-bit bus enters the three channels. 0 cycles. Do this after fix 1, not instead of it.
4. **Timing is a separate item.** -998 ps at placement is not a congestion number. No path print exists in the kit logs (not checked:
   which ends). SONNET-FIX-QC or the coll owner prints the worst 20 ends from `4_cts.odb.tt` before any new coll_core timing row.
Owner: QC-PLAN-R3 (compose, bind, G0 KITFIT); rows QC-COLL-CORE-1118 if alive, else new lane. One private proof kit to GRT round 5 (r712).

## 2. cbn_q11__cl49ae4555 OT_XSTN_STRETCH (132 / 2712)

### Evidence
- V (plan_n46_g3 relay_sites, both `cbn_q11__cl49ae4555` and `cbn_q11__cl5cc92dfe`): `u_u_fab_u_x_3_3.u_st.b_d` (516 bits) and
  `u_d6_u_fab_u_x_3_2_a_d.q` (516 bits) have the **same 6 unique sites**: x 1159.92 to 1181.52, y 2309.04. `u_st.cnt` and `u_st.run` sit
  there too. That is 1,037 flops on six anchors (86 + 86 per anchor).
- V (type note): N4.4 moved the x_3_3 b_d / cnt / run sites to "the tap_d row +60.48 um (y 2309.04), x mirrored from x_3_2". The mirror
  landed on the last d6 stage of x_3_2.
- V: in the same 86 um east margin (x 1149 to 1235): x_3_3 tap_d 444 + cap 64 at y 2249, and the bc_o33 station 517 bits at
  (1192.3, 2272.3), 37 um from the b_d anchors.
- R (QC-OWN-1119): 64 / 2832 on N43R, 132 / 2712 on N45F and N46C. The count doubled after the N4.4 move.
- Not opened: the kit resize log (no kit directory for this type was found on epyc8 today), so which b_d instances fail is I.

### Root cause (I, on V geometry)
One of the two groups is displaced by the legaliser by one or two column heights (86 flops x 0.27 = 23 um each). b_d sinks are close,
so a 25 to 50 um displacement is over 3x the direct distance. The N43R 64 were the old north-face site (600 to 1001 um, per the note);
N4.4 fixed that and created the collision.

### Fix, ranked (P)
1. **Plan row (QC-PLAN-R3, next N4.6 compose):** x_3_3 `u_st.b_d` / `cnt` / `run` anchors to x 1194.48 to 1216.08 (+34.56, same y), or
   keep x and move +48.6 um in y; then check the bc_o33 station at (1192.3, 2272.3) is at least 25 um away. Both cbn_q11 types.
   Expected: 132 -> 0 at place; no cycle change (same registers).
2. **Tool (QC-PLAN-R3, `ft_site_dedupe`):** extend the dedupe from FT bit sites to relay_sites groups: two groups of different instances
   on one anchor is an error. PRECHECK-1119 gets the same check as an estimator.
3. `cbn_q11__cl5cc92dfe` is running on epyc9 (dpkit, 44 min at 12:40) with the same sites: expect the same stop; it is the free test.

## 3. sle_st_a_v2 b_tw_data_i / x_fw_ctl (-108 ps), A/B pk46_ctl2 vs pk46_e3

State (V 12:49): `pkits/` holds no pk46 directory; both G0s end "4 errors" (the known KITFIT 4, R). The A/B has not started, so the
points below can still be taken into the test form.

### Evidence (V, plan_n46_g3 `sle_st_a_v2__pv30dda31f__pvd2ec7769`, 622.08 x 1339.2)
- b_tw_data_i: 1080 bits, E face y 277.5 to 464.4, landing box cl_b_tw_data_i x 561.6 to 607.0. Consumer relay sites
  `u_pd1_b_tw_data_i_*` are on the E faces of the four cores: u_r0 (430, 157 to 165), u_r1 (404, 486 to 494), u_r2 (395, 831 to 839),
  u_r3 (395, 1168 to 1176).
- N4.6e bin: 1080 flops, 40 x 27, bbox x 479 to 521, y 533 to 547 (42 x 14 um), x pitch 1.08 = one flop width.
- Legs from the bin centre (500, 540): to u_r1 146 um, u_r2 400 um, **u_r0 449 um, u_r3 737 um**. Landing to bin 254 um. The u_r0 share
  goes north 170 um to the bin and comes back south 379 um; direct landing to u_r0 is 363 um.
- x_fw_ctl new stations (522.1, 1.0) (450, 120) (300, 257) (220, 512) (420, 640). Other ft stations in the plan: x_ctl_fw 631 bits at
  (330.2, 271.0), **33 um** from (300, 257); b_hw_ctl_hc0 1,573 bits at (385.4, 240.9), 86 um away; cws0 at (376.1, 669.6), 74 um from
  (420, 640). The u_r0-top channel (x 268 to 430, y 240 to 406) then holds three ft stations = 2,740 flops, and x_fw_ctl (S to E) crosses
  x_ctl_fw (E to S) there.
- V (`n46g.py`): the station check tests the station **centre point** against core boxes; the bin check tests bbox corners. Station
  centres are 10.9 to 15.6 um from a core (n46g3_report), less than half a 536-bit station footprint.
- R (SONNET-FIX-QC 08:02): the box x 450 to 615, y 320 to 645 is 64 % same-bus + bin demand after x_fw_ctl leaves.

### Root cause
The detours are the 1080-bit bus funnelling to one point beside its own landing, with two ft buses in the same box (R). N4.6e removes
23 % of the box demand (R) but (a) puts a 14 um tall funnel mouth for 1080 + 1080 nets in the box, (b) leaves two consumer legs over
405 um if the bin drives all four cores (I: fan-out per core not read from the netlist), and (c) relocates x_fw_ctl onto x_ctl_fw.

### Fix, ranked (P), owner QC-PLAN-R3 with SONNET-FIX-QC for the netlist read
1. Read the A/B on **two boxes**: B1 x 450 to 615, y 320 to 645 (the b_tw nets) and B2 x 268 to 430, y 240 to 406 (the new x_fw_ctl
   crossing). A pass on B1 with new overflow in B2 is a move, not a fix.
2. SONNET-FIX-QC: one netlist read, does `u_bin_b_tw_data_i/q` drive all four cores or 270 bits per core. If per core: four bin slices
   sited on the landing-to-core lines (u_r0 slice near (470, 250), u_r1 (470, 480), u_r2 (450, 700), u_r3 (450, 800) + its existing
   pd1), 0 cycles, no funnel. If broadcast: keep one bin but as a bit-ordered strip of the landing height (x 500, y 300 to 560), and the
   u_r3 leg needs a second stage.
3. x_fw_ctl station 3: at least 80 um from the x_ctl_fw station (330.2, 271.0), and `n46g.py` checks the station bbox, not the centre.
Expected: b_tw detour nets back to under 1.3x direct; value to be read at GRT TT in the kit frame (the -108 is stock RC, R).

## 4. Structural review of the in-flight events

### N4.6f3 (plan_n46_f3r.json; cbf_q00_s2 u_t01 / u_t10 swap, reset remap)
- V: tiles u_t00 (86.4, 77.8), u_t10 (691.2, 77.8), u_t01 (86.4, 1304.6) MY, u_t11 (691.2, 1304.6) MY: family arrangement, equal to
  cbf_q00__cl1b5a6458. Reset anchor: 39 relays, 10 local resets (family 29 / 5). `n46f3.py` copies s2's own START / local resets /
  anchor from N4.6d-b: structurally the right form (names stay in s2's own tree; the f2 rename needed a same-depth relay that s2 lacks).
- **Finding 1 (V): internal_stations `bus:bc_i00` legs 633.6 / 636.7 um and `bus:bc_i10` 625.0 / 628.1 um, 517 bits, 1 station each,
  in cbf_q00_s2 and in the family.** Both are over the r713 405 um rule and are not listed in the event notes. P: +2 stations each
  (4 legs of about 318 um, +2 cycles on the two lanes via sync_fixed_cycles), or state why the leg is covered (landing bin not read).
- **Finding 2 (V): the d6 chain `u_d6_u_fab_u_x_0_0_a_d.r[0..5]` is sited at 240 um steps** ((546, 931) (546, 1171) (372, 1238)
  (130, 1238) (84, 1434) (84, 1674)). The six stages end at y 1674; the 653 um leg QC-PLAN-R3 reports follows. P: re-space the same six
  stages evenly over the full route (the 354 um form of QC-PLAN-R3-x01-site.json); 0 cycles, removes the 653 um leg.
- **Finding 3: no proof kit on cbf_q00_s2.** Both N4.6 proofs are on sle_st_a_v2. r712 asks one private kit on the worst type of the
  event: cbf_q00_s2 to CTS TT on n46j before apply.
- Not checked: the offline resolve "39 kept, 0 remaps" (R) against a bound reset tree.

### N4.6e (plan_n46_g3.json)
Section 3 items. In addition (V): `sync` reports +2 cycles on sl_E1 / E3 / E5 x_fw_ctl (15 -> 17), bus_deltas empty, rule_broken empty:
latency side is consistent. The x_fw_ctl route is now 1,372 um in 5 hops for an S-to-E feed-through whose direct path is about 770 um.

## 5. Owners

| item | action | owner |
|---|---|---|
| coll_core wall respace + SRAM field + in_data bin | plan row, proof kit to GRT round 5 | rows QC-COLL-CORE-1118 or new QC-COLL-WALL; compose QC-PLAN-R3 |
| coll_core -998 ps ends | print worst 20 ends of 4_cts.odb.tt | SONNET-FIX-QC |
| cbn_q11 x_3_3 b_d anchors + group dedupe | plan row + ft_site_dedupe | QC-PLAN-R3; QC-OWN-1119 keeps the row and reads cl5cc92dfe |
| st_a bin fan-out read, two-box A/B read | netlist read, congestion read | SONNET-FIX-QC, QC-PLAN-R3 |
| cbf_q00 bc_i00 / bc_i10 legs, d6 re-space, s2 proof kit | plan row, kit | QC-PLAN-R3 |

## 6. Stop list
1. Do not wait on pk45_coll GRT and do not read it as a timing result: round 5 is 75,675 on the same slices, placement TT -998. Its
   owner (QC-PLAN-R3) decides the cancel; I am read-only.
2. No coll_core relaunch, GRT iteration change or allow-congestion variant before the wall respace.
3. No further station or relay row that routes a coll_core bus "over cores on M6/M7". The srr_cone region does not touch this cause.
4. Do not name the g_sring column as the hotspot.
5. No relaunch of either cbn_q11 type on a plan that keeps the shared anchors; a rerun repeats 132.
6. Do not apply N4.6e on the b_tw nets alone (box B2), and do not apply N4.6f3 without a cbf_q00_s2 kit at CTS TT.

## 7. Not checked
- Cell positions of the in_data ring, dsel muxes and bins in coll_core (no DB opened; the in_data-to-src link is from net names).
- The cbn_q11 resize log; the failing b_d instance names.
- b_tw_data_i fan-out per core; station footprint shape of ft stations.
- Whether a landing bin already splits the cbf_q00 bc_i00 / bc_i10 legs.
- Hold: nothing here changes the die intra hold -268 or the per-type hold window pilot.

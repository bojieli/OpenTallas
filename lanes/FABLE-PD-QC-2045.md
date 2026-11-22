# FABLE-PD-QC-2045 2026-11-21 20:50 PST: QC plan event V3p6 (QC-PLAN-R13) structural review and today's failure events

Reviewer: FABLE-PD-QC-2045 (Fable). Read-only: nothing launched, cancelled, patched or deleted; no ot-run job; no git outside ~/coord.
Marking: **V** = read or computed by me this round from the named file. **R** = reported by the named lane. **I** = my inference. **P** = proposal.
Read first: FABLE-CLOSURE-STRATEGY 20:30, FABLE-PD-QC-1230. Their levers stand unless a line below changes them. Nothing here is a new gate.

Sources (V): epyc10 `qc-plan-r13/v3p6/v3p6/plan.json` (V3p6 post-latency b9e748038f4e, 130 types) and `v3p6_bound/tree/.../sink_bins/coll_core.json`;
epyc7 `fable-fix-qc-coll/an/{cfg3.json,s3/residual.json,s3/solve.log}`; intel2 `fam-qc-coll/reflow3/coll_core/run/{logs,reports}`;
intel2 `rt/current/tools/die_plan/postcts_gate.tcl`; `hub-coord/autopilot/log.txt`; epyc9 private kits under
`.../s29q103S4Q9N46R6V2/private/{FAM-QC-HCST-R3,QC-RELAUNCH-R1,FAM-QC-FEFW-R3}/*/geom/{auto_geom.json,placed_scan.json,auto_geom.png}`;
the four handoff files named in the brief; `lanes/COUNT-REVOKED.tsv`; RELEASE_TREE breakdown (QC types 57 of 127 signed, 50 rows running).

## 0. Headline

1. **The st_a and glue stops are setup stops, not tap-bound stops (V). This corrects the 20:30 strategy, lever 4.** `postcts_gate.tcl` lines 248 to 262:
   the pin-register band (`dev > tol`) is ADVISORY since 11-03; the only stop is `SETUP_TRIAGE`, TT `setup_est < -150 ps`. All of today's stops carry
   that marker: slw_st_a_v2 cl9f076a5c -239.51, sle_st_a_v1 cled3c1d7b -218.27, sle_st_a_v1 cl18eece69 -225.07 (19:18), slw_st_a_v1 pvf82a6c28 -154.27, glue -161.47.
   Raising `insertion_ps` to 280 / 285 / 300 on four types moves the advisory band only.
2. **V3p6 leaves the internal-station reach class exactly where V2 had it (V).** 66 hops over 405 um in 19 types, the same count and the same rows as the 12:30 review
   (cb `bc_i00` / `bc_i10` / `bc_i30` 611 to 637 um, `nb_i12`, `y_o00`, slw_stm `flt_o`, sle_ctl `x_fw_p2_i`). cbf_q00_s2's 687 / 697 um and cbx_q10 are in that list.
3. **The coll_core package closes the modelled data reach but its model skips resets (V).** `cfg3.json` `skip_launch_re` excludes `u_rrl_*`, `reset_pipe`, `rst_n`.
   reflow3 (six defines, wall form) measured recovery -193.82 ps on `u_rrl_221 -> g_face_0 ... u_codec.u_ctl.es[4]`. In V3p6 the relay is still at (445, 1041)
   and the 4,664 codec control flops are now fixed at x 6 to 312, y 46 to 641. The delta has no reset row.
4. **The cbx_q10 -659.86 ps place stop is CB row A's class on the same bit (V).** Start `u_lk_nk_u_t_2_0_n_b/q[372]` (lockup latch), end core `u_t20`. V3p6 carries row A for one
   type (cbf_q00__cl1b5a6458, 7 bits). Bit `n_b[372]` now fails on three types.
5. **Four of the LEC-revoke rebuilds died at placed geometry on V2 debts that V3p6 does not carry rows for (V).** slw_hc3 pvcca9ff41: 515-bit bus, 465 bits over 405 um, 202 over the cycle.

## 1. Part A: does V3p6 close the measured classes?

| Class (measured) | In V3p6 | Verdict |
|---|---|---|
| Site-less multi-station ft slots (300 on V2) | 8 of 623 left, all st_a cws0 (V) | Closed |
| sle_ctl E/W type split | count strap (R, row 1) | Closed at bind |
| st_a strap -333.6 and btab -124.3 | rows 2a / 2b / 2c on 11 types; proof on cl9f076a5c only, post-hook TT -12.25 (R) | Closed on 1 type, 10 unproven |
| Taps over the sink cap (387 over, 104 types) | split rows on 104 types, 9 partial (R); `tap_balance_to slowest` on 112 types (V) | Mostly closed; 9 types open |
| Internal-station hops over 405 um | 66 in 19 types, unchanged (V) | **Open** |
| cb lockup latch to core pin | 1 type of at least 3 measured (V) | **Open** |
| cb internal cross-tap hold (cbf_q00 -110.88 on 1,224 ends) | row D on cbf_q00__cl1b5a6458 only: affinity 64 / 150 um, radius 150 (V) | Open on 16 types, unproven on 1 |
| coll_core data reach | 24 rows, 49,748 seats, 13 lanes (V) | Closed in the model; no kit yet |
| coll_core reset reach | none (V) | **Open** |
| coll_ftc west band DRT-0255 | none; old placement resumed 20:09 (R) | **Open** |
| Types over 400k cells (9 measured, 22 projected) | row 4 HELD (R) | **Open** |
| slw_hc3 `cw_n3` bus, slw_fe_v2 `arv_ei` / `arm_ei` | 0 internal stations on the 4 slw_hc3 types; no `ar[vm]_ei` row (V) | **Open** |
| tt_ctlm | private trial only (R) | Open |

### 1.1 coll_core package, checked on the V3p6 plan (V)

- Geometry: 29 cores, no overlap, none outside 786.24 x 1589.76. The two N-S aisles are 48 um each (x 241.9 to 289.9 and 480 to 528); the west margin is 51.8 um.
- Station legs (Manhattan, from the rows): rec_tx_s0 200 / 286 / 248 / 310; rec_tx_s1 340 / 370 / 313; rec_tx_s2 275 / **383** / 246; flt_o 157 / 310 / 310 / 323;
  fltv_o per-bit seats 360 / 350 max; fault 377 / 338 / 361. All under 405. Three are over the lane's own 370.
- Seats, 49,748 keys, none outside the outline:
  - 97 lie inside a hard-core box (g_pf_3 48, g_xf_2 30, g_pf_0 11, g_sring[4] 6, g_pf_1 2); 562 more are within 2 um of one.
  - **599 sit in two 5.4 um slits between macros**: 458 (`hi_q`, `lo_q`, `pf_q`, 128 bits each, plus `g_wd[3]`) between `u_pring/u_rring g_b[1].u_m` (halo 4.32) and `g_xf_1`
    at y 1100.5 to 1105.9; 141 (`gq_q` 128) between `g_b[0].u_m` and `g_xf_0`. After the SRAM halo, 1.08 um (4 rows) is left. This is the lane's own caveat
    ("macro box distance, not pin faces") made concrete: the flops are at distance 0 from both boxes and have no legal row.
  - 1,243 flops share 318 coordinates; 254 (`hi_q` / `lo_q` 256..383) are on one point (341.07, 722.16) and 60 on (277.64, 633.73). 2,319 same-row neighbours are closer than one flop width.
  - Peak 20 um bin 490 seats (260, 620), below coll_ftc's 556-FF DRT bin. Seat fill by flop area is under 0.05 in every aisle.
  - The east strip x 718 to 786 holds 246 seats. The package did not use it; the macro column moved east instead (g_xf_2 / g_xf_3 to x 528).
- Residual (`residual.json`, 20 rows, V): matches the package (`hi_q` / `lo_q` -> g_pf fold 254 bits at 411 um from that single point; `shr_p_rx_i` pin -> ring 467 bits at 441).
- **Not in the model**:
  - Reset relays (headline 3). `u_rrl_221` (445, 1041) to face_0 `u_ctl.es` seats at (214, 195) is 1,077 um; to the 128 `written` flops (x 27 to 54, y 260 to 590) 840 to 1,200 um.
    Whether the V3p6 bind keeps this parentage was not read (I). The pk2 bind re-anchored only the `fstart` local resets (R).
  - reflow3's worst setup path, -402.98 ps (V, third path of `3_detailed_place.rpt`): `g_wd[3].u_tcv/q` -> select tree -> `g_sxo[1].u_face/qdata[510]`, 1,466 ps arrival.
    It is absent from `residual.json`. In V3p6 `g_wd[3].u_tcv` is seated at (345.2, 1105.5), inside the slit, and `g_sxo[1]` qdata at y 306 to 784, so every bit is 320 to 800 um away.
    `g_sxo[0]` qdata spans y 632 to 1323, `g_sxo[2]` y 306 to 883: banks 480 to 690 um tall under one select flop.
  - reflow3 totals: WNS -402.98, TNS -78,415 ps, 1,939 setup ends. The -250 ps in the brief is the global-place timing-driven estimate (log line 522), not the placed result.
- Clock: coll_core's tap grid comes from `sink_bins/coll_core.json`, source "L2 attempt_2 3_place.odb", 11-18, 65,949 sinks. Against V3p6: 1,634 of those sinks are under the moved macro boxes,
  and 9,643 of the 49,748 seats (19 %) are in bins that had no sink. The tap package gives coll_core one added tap and no measurement (`measured: null`).

### 1.2 Tap package (TAP-GRID-R5)

- V: the pin-register mean does not follow the tap split. slw_st_a_v2 cl9f076a5c has max tap 214 ps and a pin-register mean of 275.87; slw_st_a_v1 pvf82a6c28 250 and 281.47.
- V: three st_a types and glue are raised (280, 280, 285, 300); the other seven st_a types stay at 250 with `tap_slowest_max_ps` 265. sle_st_a_v1 cl18eece69 printed 281.77 at 19:18 and is not raised. Harmless, since the band is advisory.
- I: the raise changes the IO reference of those four kits by 30 to 50 ps against neighbours still at 250. Ring crossings absorb it; direct pin-register crossings do not. Not checked on the die clock tool.
- Since 11-19 the same `SETUP_TRIAGE` line stopped 18 distinct QC types (V, autopilot log): st_a 4, glue, tt_ctlm (4 times, -266 to -361), sle_fw_v1 2 (-552 to -595), slw_fw_v2, sle_stm 3, cbf_q00 cl870de686 (-3,332), cbf_q11 (-908), cbf_q01_s2, cbn_q00, sle_su_l1, slw_st_b_v1, slw_fe_v2 cle312294d. Every one is a data path to read, not a tap to raise.

### 1.3 CB rows

- V: V3p6 `latch_except_by_type` = cbf_q00__cl1b5a6458 only: `n_b[347/372/399/445/475/500]`, `n_a[471]`, 3 HB4 pads each.
- R (rows file): the latch needs clock latency under about 114 ps; balanced taps give 250 to 271. q01_s2 has 24 such bits (-184.47), again with 347 and 372.
- I: the bit list is a property of the shared core `qfd_tile_nk_rp2_romleaf_rr` (pins with about 392 ps setup), not of the type. Cutting it per type from each type's first kit costs one kit per type for 17 types.
- Row D raises the tap count on one type. Its 36 of 101 taps over 300 um span are measured on V2 (R); no kit has the row.

## 2. Part B: today's events, by root cause

| Event | Evidence | Root cause | In V3p6 |
|---|---|---|---|
| coll_core 926 bits over 370; `hi_q` / `lo_q` -> g_pf 411 | 1.1 | 254 flops on one seat point; resets and the select fan-out unmodelled | partly |
| coll_ftc DRT-0255 | V: box (166.44, 912.57) to (170.43, 916.56), net `u_cland_tl_st_wi_i/u_ring.dch[10].u_dsel`; 6 failed attempts on V1 | landing-ring dsel cells in the 4,455-sink west band; the 20:09 resume reuses synth, floorplan and place (R) | no |
| cbx_q10 cl89936551_h -659.86 at place | V, autopilot 14:20 | lockup latch `n_b[372]` -> `u_t20`, row A class | no |
| cbf_q00_s2 bc 687 / 697 um | V: plan hops `bc_i00` 634 / 637, 517 bits, one station | station count | no |
| slw_fe_v2 clf110fab2 NEED-STATION | V: `arv_ei` 695, `arm_ei` 593 (1 bit each); **also `col_v` 3.598 against hard 1.0 at (310, 657), 40 of 67 grid taps over cap, largest 7,017** | render viewed: 622 x 1832 tile, fill 0.048, logic and about 25 taps in one patch x 200 to 380, y 650 to 1050 | split rows only |
| st_a / glue 276 to 295 | headline 1 | setup estimate under -150 | rows 2a / 2b / 2c |
| 9 partial-split types | R only | sinks banked beside macros | no |
| tt_ctlm +1 retime: TT -36.34, FF -121.93 | R; geom died 14:29 | TT is inside the gate; the hold path was not read by anyone | no |
| reflow3 | 1.1 | select fan-out and reset relay | no |
| Count 60 -> 54 | V: 18 QC `PENDING-LEC` rows dated 11-21 | routed LEC never ran on the R-MINIMAL chain | n/a |

Rebuilds launched for the revoked records (V, `auto_geom.json` on epyc9; all `AUTO-GEOM FAIL`, run-item rc 1):
- slw_hc3 clccfc3e6b pvcca9ff41: `u_u_xh3.n_d -> u_bout_cw_n3` 515 bits, 465 over 405 um, 202 over the 580 um cycle, max 733, estimate 908 ps, row "none"; relay collapse 8.
- sle_st_b_v2 cl14c98df5 pvcd986c42: 419,374 cells at place; `u_lpad_x_st_a_i.q -> u_u_r7.g_pin.r` 8 bits to 467 um; largest tap 4,097.
- sle_st_b_v1 pv0e7b1dcc: one bit at 415 um; largest tap 3,115.
- slw_hc3 cld86a7ad4 pvfd488b8f (intel1): geom rc 1, file not read.
A rebuild makes a new view, so it restores the count only by a full new sign-off. slw_hc3 cannot sign on V2 or V3p6 without a `cw_n3` station.

## 3. Ranked levers

| # | Lever | Evidence | Types | Owner |
|---|---|---|---|---|
| 1 | coll_core before the proof kit reaches CTS: (a) move the 599 slit seats and the 97 in-core seats into the 48 um aisles, with the solver measuring to pin faces; (b) read the reset parentage of the codec control flops in the pk2 bind and add relay rows near x 6 to 312, y 46 to 641 if `u_rrl_221` still feeds them; (c) replicate `g_wd[*].u_tcv` / `u_gd` per `g_sxo` face, seated at each qdata bank (0 cycles), or shorten the banks | 1.1 | coll_core, then coll_ftc / ftm | FABLE-FIX-QC-COLL-R2, QC-PLAN-R13 |
| 2 | cb row A for the whole family from one static read: list the `n_a` / `n_b` pins of `qfd_tile_nk_rp2_romleaf_rr` whose LIB setup leaves no room for a T/2 latch at 250 ps, then emit `latch_except_by_type` + HB4 for every cb type, cbx_q10 `_h` and q01_s2 first | headline 4, 1.3 | cb 17 | FAM-QC-CB-R4, QC-PLAN-R13 |
| 3 | Read the worst post-CTS path of each `SETUP_TRIAGE` stop before anything else is changed on that type; keep the kit CTS ODB or the gate json for stopped rows. Start with sle_st_a_v1 cl18eece69 (-225.07) on V3p6 rows 2a / 2b | headline 1, 1.2 | st_a 10, glue, tt_ctlm, fw 3, stm 3 | FAM-QC-HCST-R3, FAM-QC-FEFW-R3, QC-PLAN-R13 |
| 4 | cb internal stations: +1 station with sites on `bc_i00` / `bc_i10` / `bc_i30` (2 hops of 611 to 637 become 3 of about 320), `nb_i12`, `y_o00`; +1 cycle on those lanes | headline 2 | cb 17 | FAM-QC-CB-R4 |
| 5 | Count: run routed LEC on every kept signed view first. Rebuild only where the kit is gone, and for slw_hc3 only with a `cw_n3` row | section 2 | 18 records | FAM-QC-HCST-R3, FAM-QC-FEFW-R3, QC-RELAUNCH-R1 |
| 6 | coll_core clock: regenerate `sink_bins/coll_core.json` from the 49,748 seats (deterministic, no placement run) and re-run `tap_split` on it | 1.1 | coll_core | TAP-GRID-R5 |
| 7 | slw_fe_v2 clf110fab2: treat the centre patch (col_v 3.6, taps to 7,017) together with the two station rows; compare with sibling cle312294d, which routed DRC 0 | section 2 | 1 | FAM-QC-FEFW-R3 |
| 8 | coll_ftc: the spread form (pkit9 axis_r4 / pin-span west band), not the resumed V2 placement | section 2 | coll_ftc | FABLE-FIX-QC-COLL-R2 |

## 4. Levers for V4 (11-22 event)

1. cb package as one event: row A family-wide (lever 2), row D on all cb types after the cbf_q00 proof reads `OT_TAP_SPAN 0`, station rows (lever 4), q01_s2 rows B / C. Owner FAM-QC-CB-R4.
2. coll_core delta 2: slit seats, reset rows, select replication, the `hi_q` / `lo_q` -> g_pf station, new sink bins. coll_ftc spread rows in the same event. Owner FABLE-FIX-QC-COLL-R2, TAP-GRID-R5.
3. Station rows with sites from placed scans already on disk: slw_hc3 `cw_n3` (4 types, 515 bits, +1 or +2 cycles), slw_fe_v2 `arv_ei` / `arm_ei`, sle_ctl's three groups (R, FAM-QC-SLWSLE-R1), slw_stm `flt_o` 548. Owner FAM-QC-HCST-R3, FAM-QC-FEFW-R3, FAM-QC-SLWSLE-R1.
4. st_b / hc split rows (intake row 4, HELD on the splitter's landing metadata). sle_st_b_v2 pvcd986c42 is at 419k cells at place. Owner FAM-QC-HCST-R3 with FLOW-STRIPBODY.
5. The 9 partial-split types: assign taps by bank name for sinks banked beside macros, or spread the bank along the macro edge (P; which sinks fill the 2,080 bins was not read). Owner TAP-GRID-R5.
6. Drop the four `insertion_ps` raises unless a die-side pair check shows a need; they do not release any stop. Owner TAP-GRID-R5, QC-PLAN-R13.

## 5. Stop list (new; earlier lists stand)

| # | Stop | Why |
|---|---|---|
| 1 | Calling the st_a / glue stops a tap-bound failure, or raising `insertion_ps` to release them | Band is advisory; the stop is `setup_est < -150` (V) |
| 2 | Reading "926 bits left" as coll_core's whole residue | Resets and the select fan-out are outside the model; reflow3 has -193.82 and -402.98 on them (V) |
| 3 | Routing the coll_core proof kit with 599 seats in 5.4 um macro slits | 4 rows of site left after the halo (V) |
| 4 | Cutting cb row A bits per type from each type's first kit | Same bit on three types; one LIB read covers the family (V, I) |
| 5 | Relaunching cb types on V3p6 and expecting bc paths to close | 66 hops over 405 um unchanged (V) |
| 6 | Rebuilding slw_hc3 on V2 or V3p6 for the count | 465 bits over 405 um, no row (V) |
| 7 | Waiting on the 20:09 coll_ftc route as a test | Same placement as six DRT-0255 failures (V, R) |
| 8 | Quoting reflow3 as -250 ps | Placed WNS is -402.98, TNS -78,415 (V) |
| 9 | Only two 1-bit stations for clf110fab2 | col_v 3.6 and 40 over-cap taps in the same read (V) |

## 6. Not checked

- No V3p6 G0 report: static G0 and the strict bind were still running at 20:49. The 66-hop count is my Manhattan read of the plan rows; it reproduces the 12:30 number.
- The paths behind the st_a / glue / tt_ctlm stops: the kit CTS logs and ODBs are gone from the kit dirs on epyc7 and epyc8.
- Reset parentage in the V3p6 or pk2 bind; whether seats inside core boxes are intended over-core sites.
- The coll_ftc 20:09 route result; the cbf_q00 / q01_s2 V2 routes; the tt_ctlm hold path; the 2,080-sink bins of the 9 partial types.
- Seat model on a real kit: none has run with the 49,748 seats.
- The LIB setup values of the NK core pins (lever 2 rests on the lane's 391.7 ps for `n_b[372]`).
- failure_breakdown gives only row states for QC types today (57 of 127 signed, 50 running), so the classes above come from the logs, not from it.

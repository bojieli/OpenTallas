# FABLE-CLOSURE-STRATEGY 2026-11-21 20:30 PST (lane FABLE-CLOSURE-2000): QC coll_core's "3,481 unregistered pins" is a read artefact (13 real); its 4,805 long captures are not touched by the wall or the fault pipe; QC st_a stops on the 250 ps tap bound, not on data

Supersedes the 18:30 round (FABLE-CLOSURE-1320; `git log -2 -- lanes/FABLE-CLOSURE-STRATEGY.md`). Its levers and stop list stand unless a line below changes them. The 19:10 die reviews (FABLE-PD-S81-2000, FABLE-PD-KV-2000, FABLE-PD-HEAD-2000) are re-ranked here, not repeated.

Reviewer: FABLE-CLOSURE-2000 (Fable). Read-only: nothing launched, cancelled, signalled, patched or deleted; no ot-run job; no git outside ~/coord.
Scope: S81, HEAD, QC, KV physical design only. Gate: DRC 0, TT setup >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. No die or outline growth; cores move or rotate. Nothing below is a new gate.
Marking: **V** = read or computed by me this round (19:10 to 20:20) from the named file. **R** = reported by the named lane. **I** = my inference. **P** = proposal.
New measurements this round are on QC (no PD review since 12:30). S81, KV and HEAD numbers are from the 19:10 reviews and the owners' posts up to 19:20.

## 0. QC measurements (V unless marked)

### 0.1 coll_core: what the three numbers are

Sources: epyc8 `/srv/opentallas-scratch2/claude/fam-qc-coll/pkit8/geom/` (V2 plan, 4.33 um wall), `pkit10_wall/kit_place/geom/` (wall respace + reset rebind), `pkit10_wall/faultpipe_private/read/` (wall + 11-cycle fault pipe; the source of the three numbers), each with `auto_geom.json`, `placed_scan.tsv`, `placed_scan_rows.json`; intel2 `fam-qc-coll/reflow2/coll_core` place log; epyc7 `qc-plan-r12/ctl_strap/v3p3_static/plan.json`.

| Number | pkit8 (V2) | pkit10 wall | wall + fault pipe | Reading |
|---|---|---|---|---|
| Unregistered pins | 13 | 18 | **3,481** | **Artefact.** The fault-pipe read ran the geom rules without the kit pin contract (`land_ring: null`, `pins_land_ring 0`; the kit reads have 3,468 to 3,473). 3,481 - 3,468 = 13. Its samples are `cland_dn_*`, `fclk_out_*`: landing-ring pins. Same on coll_ftc axis_r4 (5,133 with `pins_land_ring 0`) |
| Captures over 405 um | 5,187 | 4,631 | **4,805** | Real. On the wall kit: 3,020 bits in 160 groups, 92 groups need a station, 896 bits over the 580 um cycle. Before the wall: 3,067 bits, 98 groups, 812 over cycle. **The wall respace did not move this class** |
| Collapsed relay chains | 195 | 321 | **222** | Real, of 8,071 to 8,492 chains. Cause below |
| Vertical channel estimate | 2.71 | 1.76 | 1.81 | Still over the hard 1.0 at x 242..252, y 1107 (aisle between `g_pf_3` and `g_xf_1`). The geom GRT did not finish in 600 s, so there is no overflow number for the wall form |

What the 3,020 bits are (wall kit `placed_scan.tsv`):

| Class | Bits over 405 (over cycle) | Longest | Plan row today |
|---|---|---|---|
| Record TX: `u_coll.g_sxo.u_face/qdata` -> `u_ist_rec_tx_s0_0`, `u_bout_rec_tx_s1`, `_s2` (S face, y 6) | 705 (384) | 1,483 um | s0 has 1 station at 310 um; **s1 and s2 have none** (legs 959 and 996 um: 2 stations each) |
| Inside `u_coll`, register to SRAM or register: `g_sring.s_wd` -> `g_sring.u_m` 171, `ir` -> `u_pring` mem 138, `ir_n` -> `ir` 135, `ir` -> `up_rec` 122, `ur_rec` -> `u_rring` mem 98, `ur_rec` -> d5 49, `xr` -> `ur_rec` 24 | 737 (about 190) | 807 um | none |
| Record RX landing chain s1 / s2 (cland -> bin -> lpad.r -> lpad.q), 6 groups | 760 (0) | 457 um | none; 427 to 457 um, sites only |
| Reset relay `u_rrl_221` -> codec `g_original_control.written`, faces 0 and 1 | 128 (128) | 936 um | none; the 508 -> 477 rebind does not cover it |
| Face 0 TX / RX memory legs (`up_rec.q` -> `u_tx.wd`, `u_rx.o_data` -> d5, `rd_stage` -> `o_data`) | 174 (14) | 675 um | none |

- `s_wd` -> `g_sring.u_m` got worse with the wall: 64 bits at 658 um before, 171 bits at 683 um after. The wall rows move the five `g_sring[*].u_m` macros from x 449 to x 530; their write registers stayed at x 427, y 671.
- Collapse mechanism: the kit carries `OT_RELAY_MID_RE = ^(.*[._]u_y_[A-Za-z0-9_]+)[.]`, the S81 chain naming. On coll_core the hook prints `OT_RELAY_MID placed 0 relay flops of 0 stations (0 relay groups)`. Only the 4,457 `relay_sites` flops and 1,062 internal-station flops are sited; every other chain is placer-free. Worst chain: `u_cland_io_collective__in_data` dsel -> `g_face_0.u_tx.wd`, 10 hops over 704 um with one hop of 447.
- V3p3 (f5d51696a2eb) coll_core block: old wall geometry (`g_xf_0` at 8.64, sring at 449.28), 2 `internal_stations` rows, 4,462 `relay_sites`. The package QC-PLAN-R12 asked for at 18:26 (wall + reset rebind + fault pipe) has no row for the 92 groups.
- Fault pipe (R + V `fault_stage_reflow.json`): the three-stage return fits (first legs 378 / 302 / 238 um). Before stages the path read -671.05 over 1,453 um. reflow2 is at global place.
- Render viewed (`auto_geom.png`, `actual_place.png`): the east strip x 720..786 is empty over the full 1,590 um height (no E pins, macros end at x 680 to 720); the west column x 0..50 and the two N-S aisles carry everything.

### 0.2 st_a and glue: five post-CTS stops this afternoon on the pin-register tap bound

- autopilot/log.txt 16:57 to 19:07: `slw_st_a_v2__cl9f076a5c` (mean 275.87, setup_est -239.51, hold_est -175.36), `sle_st_a_v1__cl989804f6__cled3c1d7b` (279.34, -218.27, -191.36), `slw_st_a_v1__clfc5867a6__pvf82a6c28` (281.47, -154.27, -174.42), `glue` (295.17, -161.47, -190.74). All four: `pinreg n 3,442 to 5,516 ... bound 250.00 ... tol 20.0`. The kit CTS logs are no longer in the kit dirs, so I did not read the paths.
- Same family, other stops: three `sle_st_a_v2` kits died at GRT with `RSZ-0060 Max buffer count reached` (18:02 to 18:12); `sle_st_a_v1__cl67389ecd` and `slw_st_a_v1__clb036e152` carry GRT-0273 (clock NDR dropped) with overflow 504 and 153 at round 10.
- G0 on V3p3 (2,038 warnings, 0 errors): `timing_audit` 5 rows, `tap_sink_cap` 22 findings on 13 types, `geometry` 43 on 40 types, `routed_reach` 60 on 19 types. The reach rows are the V2 numbers unchanged.
- R (TAP-GRID-R5 19:13, main 3c2f3758f4): `tap_split.py` and opt-in `clock.tap_balance_to: slowest` landed. Neither is in V3p3.

### 0.3 slw_hc1__cl68f9248e__cle683a076: two taps at 2.06 ns

- epyc7 V2 kit `4_1_cts.log`: `OT_TAP_BALANCE it0 ... clk_t11=2062(1874-2143,40)`, `clk_t18` 27 sinks at 2,143 max; unchanged through it2 (balance only adds delay). `done: 589 delay cells; tap mean insertion 231..2062 ps (spread 1831)`; 11 empty taps; `clk_t102` 2,060 sinks against the 1,000 cap. The `OT_STB before` lines of these two taps print values of 1e11 scale. The kit ended `TT global-routing insertion gate failed`.
- This type has at least 16 kits over the plan events. The 67 sinks were not read (needs the CTS ODB).

### 0.4 cb, su_c, fe

- `cbf_q00__cl1b5a6458` V2 post-CTS (intel2 `fam-qc-cb-r2/v2/.../cts_r3.log`, done 19:10): `OT_HOLD_GATE PASS FF wns_ps -110.88 endpoints 1224 (true negative slack)` against a structural limit of -145.0 (forwarded ring inputs 2,068 on 4 clocks, `in_min -85`, tap window 41.5). The gate passes; the hold is not closed.
- cb station rows for `bc_i00` / `bc_i10` / `bc_i30` (611 to 637 um), `nb_i12`, `y_o00` are still "to do" in the lane handoff; `routed_reach` in V3p3 has the same 60 rows.
- su_c: `sle_su_c` GRT flat at 38,588 -> 37,924; `slw_su_c` 11,725 and 9,472 at round 10. Site rows exist (R: two at 0 cycles, cl19bb38ef +1 cycle on 3 lanes). The private proof died `KIT_TOPOLOGY_BIND_STALE` at 19:09: a rows delta needs its own bind.
- `slw_fe_v2__cle312294d`: routed, DRC 0, TT -35.59 (inside the gate), FF hold -36.39 on 164 ends -> **-3.78 on 8 ends**, then "late-ECO exhausted".
- R: `sle_fe_v1__cl8210183c` signed with LEC 103,598 / 103,598; q01 S2 TT +18.75, FF -31.03 not routed; sle_ctl variant C TT -375.29 at place, route launched 18:19.

## 1. Levers, ranked by types unblocked

### Lever 1. S81 col: three proofs are finally running; read them in this order (216 types)
- Evidence (R, 19:03 to 19:18): lever-1 kit col_h10_r0_p4 pvcc166a6d on epyc7 (view daea3c41, `halo_um` 0.27 on `u_cf` + `u_t0`; the edge OBS is signed metal, so no regen); ROM-input rep col_h10_r1 cld01bb4ae on epyc9 from the sealed J7 tree; `rq` keep A/B and STAGGER on epyc8. Proof A's GRT-0116 is 11 vertical gcells at x 498..523, y 11..13 on the south face: a face-pad stack, not a macro corner.
- Fix (P): decide col's J8 entry from three numbers only: violations against `u_cf` / `u_t0` (target 0), xo recovery ends with the `rq` keep (was 552), ROM-input ends with the stage pair (was 427). For proof A, spread the `frame_int` face-pad stack over two rows before any channel change. xo depth D3 before STAGGER, as in the 18:30 lever 4.
- Owner: FAM-S81-COL-H10-R4, FAM-S81-COL-H9R0-R4, FABLE-FIX-S81-COLROM-R5, S81-J6-ASSEMBLY-R5.

### Lever 2. S81 START and reset reach rows as J8 GEN steps (writer 104 types, reader 38, raw reset 73)
- Evidence (FABLE-PD-S81-2000 section 2): J7eL6 covers slice_station only (44 of 45; t46 writer 1,957 um). Serdes has 7 open ops up to 3,328 um; svc 16 types to 4,087; leaf 50 types on the `fstart_k <- rst_rl_*` falling-edge relay; col writer 59.
- Fix: rule 1 and rule 5 per family into J8; one placed proof per family on the J7eL6 form. QC has the same class: coll_ftc's 66 remaining hops end at `u_rrl_90_r -> u_cland_writer_start_ss_wo_ss5_o_4` (V, 881 um), so its residue is START reach, not data.
- Owner: each S81 family lane, S81-J6-ASSEMBLY-R5; FAM-QC-COLL-R3 for coll_ftc.

### Lever 3. KV: reset rows on 19 hg / hgi, stable type blocks, pv split in one event (50 unsigned of 56)
- Evidence (FABLE-PD-KV-2000): 0 sign-offs in 22 events; D27d3 re-keys 52 of 56 blocks and can close 8 types (pc 6, io_cor 2). R: R6c strict bind ETA 20:45 with hgi_v2 as the proof type; hub_Ei row A removes 93,887 synth cells (placed at most 301k) and changes only its own block; hroot's -532 ps appears at GRT because 10 of 41 taps span over 300 um.
- Fix: as KV-2000 section 3. Add to it: hroot variant B must cap the tap sink box (300 um), since variant A moves relays, not sinks.
- Owner: KV-PLAN-R6, OPUS-FIX-KV-HGI-R6, OPUS-FIX-KV-PV-R5, FABLE-FIX-KV-HUB-R5, FAM-KV-HROOT-R1.

### Lever 4. QC tap rows in the V3 cut: balance to the slowest tap, split over-cap taps (st_a 11 types + glue now; 13 types with over-cap taps) NEW
- Evidence: section 0.2. Four of four st_a / glue kits that reached CTS today stopped on `pinreg mean 276..295` against a fixed 250 with tolerance 20. G0 already measured the early core tap at 290.7 to 301.7 on 4 st_a types.
- Root cause (I): the 250 ps target is below what the st_a and glue pin-register taps reach, and balance can only add delay. The kit then fails its own bound before any data path is judged.
- Fix (P): V3p4 carries `clock.tap_balance_to: slowest` on the st_a types and glue, and the `tap_split` rows for the 13 types. Both are 0-cycle and append-only (R). The die-side pair slack for those types then uses the same target; check the st_a boundary pairs on the die clock tool once. Read the `RSZ-0060` GRT deaths on sle_st_a_v2 after the btab and seat rows are in (V3p3 has them); do not retry them on V2.
- Owner: TAP-GRID-R5 (rows by 04:00), QC-PLAN-R12, FAM-QC-HCST-R3.

### Lever 5. QC coll_core: the V3 package needs the data rows, a QC chain regex and the sring seat (coll_core, coll_ftc, coll_ftm) CHANGED
- Evidence: section 0.1.
- Root cause: N-S data flow through a 1,590 um type whose collective logic sits mid-height between macro blocks. Three long buses have no station, the `u_coll` registers sit 400 to 800 um from the SRAMs they write, and the chain-siting hook does not recognise QC chain names.
- Fix (P), in this order, all in the one package FAM-QC-COLL-R3 hands over:
  1. `rec_tx_s1` and `rec_tx_s2`: 2 stations each from `placed_scan_rows.json` (sites (320, 645) / (320, 325) and (436, 670) / (436, 338) on the wall geometry), +2 cycles on those two lanes. Pre-approved.
  2. `u_coll` internals at 0 cycles first: FIRM sites for `g_sring.s_wd`, `ir`, `ur_rec`, `up_rec` at the pin face of the macro they feed. If a leg still exceeds 405 um after that, one RTL stage on that write path. Re-check the sring move to x 530: it bought the overlap fix and cost 107 more long bits.
  3. `OT_RELAY_MID_RE` for qwen_compute in `die_gen_env`, matching the QC chain names (the `u_d5_*` and `ot_dp_dly` / `ot_dp_st` chains). Accept on `OT_RELAY_MID placed N > 0` and collapsed chains falling from 222.
  4. Reset: a row for `u_rrl_221 -> codec written` (128 bits, all over cycle) in the rebind.
  5. Channel: the vertical estimate is still 1.8 at the `g_pf_3` / `g_xf_1` aisle. The east strip x 720..786 is unused and has no pins; moving the east macro column (`g_xf_2`, `g_xf_3`, sring, the three large blocks) east by 40 to 60 um widens the middle N-S channel at no cost. Decide on the GRT round-5 number of the one build, not on the estimate.
  6. Private geom reads: pass the kit pin contract (`--all-kits` with `land_slots`), or `pin_unreg` is meaningless.
- Owner: FAM-QC-COLL-R3 (rows, build), QC-PLAN-R12 (intake), FLOW-OPS-1300 (regex in die env).

### Lever 6. QC cb and su_c: rows must ride in the V3 bind; cb hold is open behind a passing gate (cb 17 types, su_c 3)
- Evidence: section 0.4.
- Fix (P):
  1. su_c rows (3 types) and the cb site-only forms plus the five bus station rows go into V3p4 with the V3 bind; a private proof without its own bind cannot run.
  2. cbf_q00: 1,224 FF hold ends at -110.88 must reach 0 at sign-off. Split them by start (forwarded ring input against internal) on the kept `4_cts.odb` before route; ring-input ends take the lockup or same-tap capture, not buffers. Same reading for q01 S2 (-31.03).
  3. cbx_q10: `a22` at 1,884 to 1,901 um with 1 station is 4 hops short; rows before its relaunch reaches GRT (it was flat at 25,215).
- Owner: FAM-QC-CB-R3, FAM-QC-SLWSLE-R1, QC-PLAN-R12.

### Lever 7. Cell cap by strip / body split (S81 c1x_C 9, svc hi4, lepe_mu_C; QC 4 measured + 17 projected hc / st_b; KV hub 5; HEAD hd_lep0N)
- Evidence: S81-2000 section 3 (cut at y 60.48 with 3 to 15 macro moves; t9 needs the xring strip too); QC split table delivered 18:59 (R: 21 types, pieces 233k to 285k); KV hub_Ei row A (R); HEAD shelf at 98.9 % of the cap with two located walls (HEAD-2000 section 2).
- Fix: FLOW-STRIPBODY-R2's bind path is the common dependency; first proof lepe_mu_C t1 on the sealed J7. svc hi4: re-order the cut windows by endpoint y and drop the 4,663 dead `Q_p` bits before any fourth place run.
- Owner: FLOW-STRIPBODY-R2, FAM-S81-SLICE-R5, OPUS-FIX-S81-SVC-R9, FAM-QC-HCST-R3, FABLE-FIX-KV-HUB-R5, FABLE-FIX-HEAD-LEP0N-R4.

### Lever 8. Near sign-off types that need one targeted step (3 types now)
- `slw_fe_v2__cle312294d`: 8 ends at -3.78 ps FF hold on a routed DRC-0 DB with TT -35.59. One local hold ECO on those 8 ends (owner rule: small ECO for an understood local near miss). No rebuild.
- HEAD hd_ctl: the wave-env WRCAP kit (launched 19:04, strip rows 3, PGCAP) is the signing form; the rows-1 DRT is a read only (HEAD-2000 section 1).
- `slw_hc1__cl68f9248e__cle683a076`: list the 67 sinks of `clk_t11` / `clk_t18` from the kept CTS ODB before kit 17. A 2.06 ns raw tap is either sinks far over 1 mm from the tap or a non-buffer cell on the tap net (I).
- Owner: FAM-QC-FEFW-R3, HEAD-CTL-R1, FAM-QC-HCST-R3 with TAP-GRID-R5.

## 2. Stop list (new or changed; earlier lists stand)

| # | Dead end | Why |
|---|---|---|
| 1 | Adding pin registers on coll_core or coll_ftc for "3,481 / 5,133 unregistered pins" | Read without the landing-ring contract; 13 real on coll_core (V) |
| 2 | Routing coll_core on wall + reset rebind + fault pipe alone | 3,020 bits in 92 groups still need stations; vertical channel estimate 1.8 (V) |
| 3 | Expecting the relay-mid line fit to fix QC chain collapse as configured | S81 regex, 0 groups matched on coll_core (V) |
| 4 | More wall respace on coll_core as the answer to long captures | 3,067 -> 3,020 bits; `s_wd` -> sring worse (V) |
| 5 | Relaunching st_a or glue on V2 unchanged | 4 of 4 stopped on the 250 ps pin-register bound today (V) |
| 6 | Reading `OT_HOLD_GATE PASS` on cbf_q00 as hold closed | -110.88 on 1,224 ends under a -145 structural limit (V) |
| 7 | Private su_c or cb rows proofs without their own bind | `KIT_TOPOLOGY_BIND_STALE` (R) |
| 8 | Another full build of slw_fe_v2 cle312294d | 8 ends at -3.78 ps on a routed DB (V) |
| 9 | Kit 17 of slw_hc1 cle683a076 before the two taps are read | 2,062 ps raw insertion on 67 sinks, spread 1,831 (V) |
| 10 | KV hg / hgi / pv volume on D27d3; die-wide regeneration in D28 | KV-2000 section 6 |
| 11 | svc hi4 fourth place run on the present cut list; ECO rounds on col_h9 r1 / r2 at -230 to -290 | S81-2000 section 6 |
| 12 | hd_ctl rows-1 or rows-2 private sign-off as the signing form; unsplit hd_lep0N shelf | HEAD-2000 |

## 3. Not checked
- The st_a and glue post-CTS paths (logs gone from the kit dirs); the `setup_est` values are the gate's own estimate.
- The cause of `RSZ-0060` on the three sle_st_a_v2 kits; where the su_c overflow sits.
- The exact QC chain instance names for the relay-mid regex; whether reflow2's env carries the reset keep-wires proven on pkit8.
- GRT overflow of any coll_core wall form (the geom GRT did not finish).
- S81, KV and HEAD numbers were not re-measured this round.

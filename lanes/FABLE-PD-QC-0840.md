# FABLE-PD-QC-0840: QC failure classes since 04:53, half-cycle landing inputs, V2 (b18/b19) structural review (2026-11-21 09:00 PST)

Read-only. Nothing launched (two plan-read scripts through ot-run on epyc7), cancelled, patched or signalled.
V = read by me today from the named file. R = reported by a lane. I = inference.
Sources: epyc7 `qc-plan-r9/b19in/plan.json` (sha e6246deed98f) against V1 (`kw45/snap_qwen_compute/qwen_compute_v1r6`); wave kits
`kw43-wave-1109n/.../s29q103S4Q9N46R6V1/items/<type>/attempt_N/gen/<type>` on epyc2 / epyc7 / epyc8 (`postplace_setup.log`, `place_setup_stop.json`,
`FAIL_POSTCTS`, `run/reports/.../{3_detailed_place,4_cts_post_hook,5_global_route}.rpt`, `tt_setup_repair_grt.log`, `macros/*.lib`, `constraint.sdc`);
epyc2 `FAM-QC-HCST-R2/tmp/{rp.log,rp4.log}`. 4_cts_final.rpt not used. My scripts and outputs: rtx-pro scratchpad `qc0840/`, epyc7 `FABLE-PD-QC-0840/tmp/`.

## 0. Headline

1. **The half-cycle landing-input "floor" (-75.8 / -113) is a measurement artifact, not a design limit.** The post-place stop now times every clock as
   ideal. On an ideal clock OpenSTA subtracts the landing macro's `min_clock_tree_path` (162 ps) from the capture edge. The same bus on the same
   type with propagated clocks (post-hook CTS) is +39 to +44 ps. No full-cycle capture, face register or station is needed.
2. **slw_st_a_v2__clf4365a62 is really about -140 ps pre-repair, not -301.73**, and only because its landing band is the off-face `_n_s26` variant.
   It is the only one of 11 st_a types with that variant. The face-home floorplan row (FAM-QC-HCST-R2) is the right fix and is enough.
3. **The real post-CTS blocker on the st_a representative is a strap register driving a hard-core pin over about 1 mm:** -169 ps post-hook, 43 endpoints,
   repair stalls. The R8 pad registers are also the worst start on sle_ctl attempt 5 (-440.70). Neither is owned as a class.
4. **Giant-negative place stops are false** (reset relay starts, old measurement). Not plan items.
5. **V2 b19 is still not safe by construction**: the hop, tap and reset-leg results of FABLE-PD-QC-0440 section 3 are unchanged apart from two cb reset
   rows. It should still apply as soon as it binds. b19 static G0 and strict bind were still running at 08:50 (R8 loop 1).

## 1. Half-cycle landing inputs (COORD question)

### 1.1 What was measured (V)

slw_st_a_v2__cl9f076a5c attempt_3, bus `b_hw_ctl_hc0_i[*]` into `u_cland_b_hw_ctl_hc0_i` (`sta_cland_w1574_e_s26`, face-home), TT:

| view | arrival | capture edge at `fclk` pin | macro tree term | lib setup | slack |
|---|---|---|---|---|---|
| post-place, ideal clocks (`rp4.log`, d[17]) | 245.0 + 45.1 = 290.05 | 416.50 | **-162.40** | -76.95 | **-112.90** |
| post-hook CTS, propagated (`4_cts_post_hook.rpt`, worst 4 bits) | same port | 418.65 | none | same arc | **+39.12 to +43.84** |
| same, start flag `cland_fstart_in_*` -> `t_rst_n` | 188.87 | 418.65 | none | -242.00 | -12.22 (CTS), +55.86 (GRT report) |

- Lib (`sta_cland_w1574_e_s26_tt.lib`): pin `fclk` carries `min_clock_tree_path` fall 162.40 and `max_clock_tree_path` fall 194.61; `d[17]` setup_falling 76.95, hold_falling -64.09. The setup and hold arcs are at the pin and already contain the tree.
- `tt_setup_repair.tcl` line 42-45: with `OT_POSTPLACE_WORST=1` no clock is set propagated ("ideal, as in detailed place"). This came with the fix for the false reset stops (eda19506a55).
- `fclk_in_*` is created on an input port and wired straight to the macro pin (1.24 to 2.15 ps). It cannot reach the pin 162 ps before it reaches the port, so the ideal-clock number is the wrong one. Sign-off and every post-CTS gate use propagated clocks.
- The same term appears on all seven landing groups of the type: -95.3 to -162.4 (`rp.log`). On sle_ctl attempt_5 the post-place landing groups read -181 to -265 (`3_detailed_place.rpt`) and carry it too.

### 1.2 clf4365a62 (V)

`rp.log`: arrival 245.0 + 225.9 = 470.92 (four buffers, two segments of 67.9 and 81.7 ps, placement RC before repair, hop 140.5 um);
required 416.50 - 161.70 - 85.61 = 169.19; slack -301.73. Without the artifact: **-140.0**. It crossed the -300 stop by 1.73 ps only because of the artifact.
Plan b19: its band is `sta_cland_w1574_n_s26` at (328.3, 60.5), 272 x 45. All other 10 st_a types have `sta_cland_w1574_e_s26` at (561.6, 17.3) on the E face.

### 1.3 Is the class sound, and what would improve it

Budget on a face-home band: T/2 416.5 = 245 external + 45 port buffer and wire + 77 setup + about 40 to 50 left. Hold on the same groups: +340 to +349 (GRT report).
So the capture point sits about 150 ps early in the data eye: setup margin about +40, hold margin about +340 (I, from the two arcs: the macro samples what was on the pin about 70 ps before the `fclk` pin edge).

| option | result | verdict |
|---|---|---|
| Full-cycle capture (next rising edge) | setup +466; hold = (833 - 85 + 35) - (833 + 2 - 64) = about +14 TT, negative at FF and with any clock / data mismatch | **No.** `in_min -85` makes it a hold failure by construction |
| Extra face register in front of the macro | the macro's first flop already is the face register; a second one has the same window and costs a cycle | **No** |
| Station on the port -> band hop | the path has 0 cycles to give inside a half cycle | **No** (row correctly withdrawn) |
| Face-home band (copy cl9f076a5c floorplan) | -140 -> about +39 (sibling, measured) | **Yes**, clf4365a62 only |
| Re-centre the eye inside the landing macro (less data-side padding or 150 ps more on `fclk`; 0 cycles, macro re-sign) | about +190 setup / +190 hold (I) | **Hold in reserve.** Only if a routed sign-off shows a landing group under 0 |

Open: no routed sign-off of a V1 st_a kit was read for the `fclk_in_*` groups. The +39 is post-hook CTS, global-route RC.

### 1.4 The "-177 on x_fe_o" on clb036e152 and cl9f076a5c (V)

`postplace_setup.log` attempt_3: start `u_rrl_128` / `u_rrl_435` (reset relay), end `u_bout_x_fe_o/eq` reset pin, hop 1,087 / 1,487 um. It is reset recovery on an
unbuffered net at place, not the output data path. After CTS the worst recovery slack on cl9f076a5c is +551.17 (`4_cts_post_hook.rpt`). Not a plan item.

What actually fails after CTS:

- **cl9f076a5c** (`FAIL_POSTCTS` SETUP_TRIAGE -333.62): `u_r8b_strap_r8pad_u_r0_rs_n_c_p_f.q[2]` -> hard core `u_u_r0/rs_n_c_p[2]`. Launch clock 255.73, 787 ps through nine wire buffers and one OA21 (segments 75 to 133 ps), core `ck` at -3.29 (early core tap), lib setup 106.81: -169.05 post-hook. 43 endpoints at GRT RC, -322.66 before repair, `OT_REPAIR_STALL` at -230.30.
- **clb036e152**: `u_cland_origin/s2` -> `u_cland_rstart_tx/q` -85.49 post-hook: the rstart_tx class (rows `l2_rows.json`, 40 types, 0 cycles, unbound).

## 2. Other classes since 04:53

| class | root cause | evidence |
|---|---|---|
| Giant-negative place stops (sle_hc0 pvcaa93304 -146,651; sle_hc2 pvcf529cc9 -131,708; slw_hc3 a4 -56,163; slw_fw_v1 cl592e3d37 a2 -226,252; sle_ctl a4 -359,026; coll_core a4 -241,057) | every start is a reset relay or local reset flop (`u_rl.rst_n[*]`, `u_rrl_*`, `r_rst_n`) into async pins: unbuffered reset net timed before CTS | V: 5 `postplace_setup.log` (sle_hc0 pvcaa93304 not opened: no log left in its attempt dirs, R only). R: same DB with ideal clocks +21.56 (Codex); rep a5 passes place on new tools |
| R8 pad / strap registers unsited | strap register far from the core pin it feeds and on a normal tap while the core is on an early tap (section 1.4); sle_ctl a5 worst -440.70 starts at `u_r8b_strap_r8pad_u_rp_chd_q_1/r[4][473]` -> `u_ist_x_su_c_p1_o_0` | V: 2 of the 3 post-tool-fix failures I opened |
| sle_ctl core in the data path | `u_lpad_x_fw_p2_i.q[116]` -> core `u_u_tap` -598.68 at place (a5); plan first leg 432 um; b19 per-bit row still [432, 240, 276] | V |
| sle_ctl auto-geom FAIL (a5) | fill 0.039, r2r 1,125 um on 2,542 captures, pin_reg_max 442.7, clock_tap_sinks 9,194 against cap 1,000, 2 clock cells on macros | V `auto_geom.json`. R: proof k_a2 (core-slit stations) GRT overflow 0 |
| slw_fw_v1 cl592e3d37 -74 routed; sle_fw_v2 -49 / -61; slw_fw_v3 -84 | zero-logic hop `u_bin_x_sc_i` -> `u_bout_flt_wo` / `sc_eo`: 17 buffers, 846 ps | V (0440). b19 adds a station on `sc_wo` (4 -> 5) and `x_sc_o` (1 -> 2) but no `x_sc_i` / `flt_wo` row |
| coll_core pkw4 -255 after 55,013 HB4 | GRT hold repair on input-register paths bought pads on setup paths | R only. pkw4 kit not found on epyc9; I could not check that it ran with `OT_GRT_NONPORT_HOLD=1` and `OT_HOLD_IN_MIN` as the wave kit does. If it did not, the pad count is partly an env effect (I) |
| b16 G0 59 errors | non-uniform hop300 station bumps per slice gave pads 2/4/3/4/1/4 at one shared sle_ctl site; ft_spread sites on macros | R. b18 static G0 0 errors. 23 slots reverted to V1 station counts |

## 3. V2 b19 as gated (V unless marked)

| test | b19 | change from b14 |
|---|---|---|
| hop <= 405 | **fails**: 27 routed internal rows (cb `bc_i00` / `bc_i10` / `bc_i30` legs 611 to 637, `nb_i12` 418, slw_stm `flt_o` 548) + sle_ctl `x_fw_p2_i` 432. ft slots 0 over 405. `ft_station_max_um` and `reset.hop_um` still 405 | 28 -> 27 |
| hop <= 300 | routed internal rows 87 of 188 over; per-bit chains 9 of 923; sited ft slots 212 of 323 with a leg of 301 to 400 (slw_sc_v1 51, sle_sc_v1 32, sc_v2 / v3 59, st_a 19, su_c 14, su_l1 12); 75 last legs over 300 (max 363); 314 slots on 72 types have stations and no sites | same; 23 slots went back to V1 counts |
| stations added vs V1 | internal: 529 rows +1 to +7; ft: 194 slots +1 / +2 | - |
| taps | no change: radius 200 / cap 1,000 / density on 120 types; plan tap count differs from V1 on 0 types | same |
| <= 400k cells | `cells` present on 42 of 130 types, max 366,499 (five st_b types), none over 400k. 88 types carry no number. st_b plus the 1.4 to 20 % hold cells measured in 0440 can pass the cap (I) | not checked before |
| reset leaf legs | 17 of 17 cb types have `inst_taps` (was 15). cbf_q00 still carries taps 93 / 100, which FAM-QC-CB-R2 measured at 525 / 506 um; the re-pick 77 / 76 (75 / 135 um) bound clean in its private bind (LATCHECK 1921 / 1921, R) and is not in b19 | +2 types |
| hold structure | nothing in V2 changes it. coll_core carries `OT_TP8S_SRDREG` only | same |
| G0 / bind | b18 static G0 0 errors, 0 new vs V1 (R). b19 = b18 + 6 E su_l0 lanes fixed 7 -> 8; bind in R8 loop 1 at 08:50 | - |

Verdict: apply V2 when it binds. It is a station-count event, not a 300 um plan and not close-by-construction.

## 4. Ranked fixes

| # | fix | measured evidence | owner |
|---|---|---|---|
| 1 | Post-place measurement: keep `clk` ideal, set `fclk_in_*` propagated (or drop the macro tree term on port-born clocks) in `tt_setup_repair.tcl`. Then re-read clf4365a62 and the sle_ctl landing groups | -112.90 ideal vs +39.12 propagated, same bus; stop crossed by 1.73 ps | FLOW-NOADV-R3 (flow) |
| 2 | R8 pad / strap registers: site `u_r8b_strap_*_f` at the core pin face on that core's early tap, or tie the strap at the parent under the ID-strap rule (the port is already a false path); sites for the `r8pad` chain stages. Census all types for `u_r8b_*` starts first | -169.05 / 43 endpoints (st_a), -440.70 (sle_ctl a5) | QC-PLAN-R10; FAM-QC-HCST-R2 and OPUS-FIX-QC-SLE-R4 for the proofs |
| 3 | +1 station on `x_sc_i` -> `flt_wo` / `sc_eo` (4 fw types) | -74.03, -49.46, -60.55, -84.28 routed | FAM-QC-FEFW-R2 -> QC-PLAN-R10 (V3) |
| 4 | Bind `l2_rows.json` (rstart_tx, 40 types, 0 cycles) and `l7_rows.json` (slw_su_l1 rsf / rsn) | -85.49 post-hook on clb036e152; su_l1 -43.05 routed (0440) | OPUS-FIX-QC-SLE-R4 -> QC-PLAN-R10 (V3) |
| 5 | cb: re-picked `inst_taps` for cbf_q00 and the same re-pick on placed positions for cbn_q01 and siblings; then stations on the 27 rows over 405 | 525 / 506 um vs 75 / 135 um; -393.97 (0440) | FAM-QC-CB-R2 -> QC-PLAN-R10 (V3) |
| 6 | clf4365a62 face-home floorplan row | -140 -> about +39 | FAM-QC-HCST-R2 -> QC-PLAN-R10 (V3; needs bind + LATCHECK + G0) |
| 7 | sle_ctl: carry the k_a2 rows (in V2), then move `u_tap` or add a station on the 432 um first leg; tap rows for the 9,194-sink tap; stations by length on `b_tw_data` | -598.68 place; overflow 40.2k -> 0 (R) | OPUS-FIX-QC-SLE-R4 |
| 8 | coll_core: b + c + d as one row set after the wave-env kit read; first confirm the pkw4 hold env | -255 / 916 ends, 55,013 pads (R) | FAM-QC-COLL-R2 |
| 9 | Taps by region and core tap insertion (0440 fixes 1 and 2), still not in any plan | 0440 section 1.2 | QC-PLAN-R10 (V3) |
| 10 | Census: fill `cells` for the 88 types; flag st_b at 366k | section 3 | QC-PLAN-R10 / census |
| 11 | Landing eye re-centre in the `sta_cland_*` macros, only if a routed sign-off shows a landing group under 0 | section 1.3 | FAM-QC-HCST-R2 (reserve) |

## 5. Stop list (not into V2 / V3)

- No full-cycle capture, extra face register or station row on landing inputs. No band moves on the 10 face-home st_a types.
- No stop, cancel, triage or plan row from a post-place number on an `fclk_in_*` group or on a path that starts at a reset relay, until fix 1 lands. Subtract the macro tree term (95 to 162 ps) when reading one.
- Do not hold V2 or start a b20 to take in any row of section 4; they are V3 rows.
- No cb volume on taps 93 / 100; no relaunch of clf4365a62 unchanged after fix 1 without the floorplan row (it would run at -140 pre-repair).
- coll_core: not ODPRE alone, and not INLOCK before the kit shows the half-cycle setup and the pad count. No private proof without the wave env.
- Do not call V2 a 300 um or close-by-construction plan. Do not re-add the 23 reverted hop300 slots per slice: they must be uniform across the 12 sle_ctl instances.

## 6. Not checked

- b19 bind result, LATCHECK, post-bind G0, census, the 8 proof GENs (running).
- Routed sign-off slack of the `fclk_in_*` groups on any V1 st_a kit; the landing macro's own build SDC (why its data side is padded).
- Placed positions of the strap registers and the core pins they feed (path length taken from the buffer chain); whether the V2 R8 link sites cover them.
- coll_core pkw4 logs (kit not found); the sle_ctl a5 -440.70 path cell by cell; slw_fw_v1 routed report (taken from 0440).
- Cell counts from kits (plan field only). Hard-core reset pins on sle_ctl.

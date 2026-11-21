# FABLE-PD-QC-0440: QC hold pattern, reset-relay class, V2 (b14/b15) structural review (2026-11-21 05:05 PST)

Read-only. Nothing launched, cancelled, patched or signalled. V = read by me today from the named log / report / plan. R = reported by a lane. I = inference.
Sources: 66 QC route jobs live in the last 20 h on epyc2/7/9/10, intel1/2 (`ot-jobs/*-route-*/work`: `pregrt_ff_hold.log`, `hold_gate.log`,
`run_route.log`, `postcts_gate_{TT,FF}.log`, `4_1_cts.log` post-hook lines, `signoff/signoff.json`, `signoff/{tt,ff}/sta.log`);
fp3 = epyc9 `fable-fix-qc-cb/proof/fp3` (`3_detailed_place.rpt`, `bound_native_reset.json`, render `fp3_pre_route.png`, viewed);
V2 = epyc8 `qc-plan-r9/b14in/b14_plan.json` (c3f5b1eb9c1e; b15 = this plan + 2 clone types) against V1 (`kw45/snap_qwen_compute/qwen_compute_v1r6`), `b14/bind/bind_reset.json`, `b14.out`, `chain_b15.log`.
My collectors and tables: rtx-pro scratchpad `qc0440/` (fleet.sh, cts.sh, an*.py). 4_cts_final.rpt was not used.

## 0. Headline

1. **The fleet-wide pre-route hold number is not flop-to-flop hold.** On all 66 builds the worst hold endpoint is class `port_in`: an input port
   timed against the ideal `vclk`, captured by a flop on a propagated tap. It is the seam contract (`in_min -85 ps`), not skew inside the type.
   The kit excludes it from repair by design and sign-off lists it as advisory (`io_hold_parent: NEEDS_PARENT`).
2. **Internal hold closes.** Pre-GRT repair takes same-tap and cross-tap to 0 violators on every build that ran it. 5 routed builds read: internal FF hold 0 violators on 4, 1 endpoint at -8.50 on 1.
3. **What stops the routed builds is TT setup, -43 to -84 ps, on long zero-logic station hops.** 6 of 8 routed builds. V2 leaves the same hops in the plan.
4. **The reset path is one leaf relay driving sinks 1,850 um away.** Fix = `reset.inst_taps` (same depth, 0 cycles). V2 carries it for 15 of 17 cb types.
5. **V2 is not safe by construction on three of the four tests** (hops, taps, reset leaf legs). List in section 3.
6. **b15 is not binding.** The chain stopped at 04:49 PST: non-strict bind rc 0 but no `rtl/qwen_compute_bound_top.sv` (EMIT error remains). QC-PLAN-R9 wrote `chain_b15b.sh` at 04:50.

## 1. Fleet-wide hold

### 1.1 What the number is (V)

`pregrt_ff_hold.log` classes, 66 builds (post-hook CTS database, FF):

| class | endpoints per build | worst slack | after pre-GRT repair |
|---|---|---|---|
| port_in | 2 to 4,361 | -79 to -135 | unchanged (not repaired) |
| cross_tap | 16 to 7,640 | -23 to -224 (median about -55) | 0 violators, wns +45 |
| same_tap | 0 to 366 | -3 to -88 | 0 violators |
| port_out | 0 (210 on one st_b) | -6.5 | 0 |

- port_in = 2 on su_l / sle_ctl / cb (`start_i`, `arst_n` into `u_run_in`, `u_rst_in`); 519 st_b; 1,036 st_a; 1,576 hc0; 2,288 to 2,803 sc; 2,881 to 4,361 fe / fw / stm (`u_bin_x_*_i`). Buses through a forwarded-clock landing (`fclk_in_*`) are +338 to +360.
- `slw_su_l1__clcc9d0155` (epyc2), FF, global-route RC: `vclk` ideal 240.1, input delay -85.0, port buffer 13.8 = arrival 169.0; capture `clk_t42` 229.3 + uncertainty 12.5 + hold 13.1 = 254.9; slack -85.9.
- So: slack = in_min (-85) + (vclk latency - capture insertion) - 25.6 + port buffer. The reported -62 to -178 moves with the second term only.
- Second term: TT pin-flop insertion mean at GRT is 277 to 316 ps against the 250 bound (+27 to +66) on every build that printed it. That is why the TT "hold_est" (-122 to -216) is worse than FF (-108 to -192).
- `OT_HOLD_GATE` calls it PASS under a structural limit (-150 to -301). `OT_GRT_NONPORT` removes input-port starts from GRT hold repair.

### 1.2 Internal hold: cause and cost (V)

Post-hook CTS lines, same 66 builds:

| measure | range |
|---|---|
| zero-logic pairs under 64 um on two taps (`OT_TAP_PAIR ... cross-tap short pairs`) | 15 to 14,398 |
| clock pins the pairing pass moved | 0 on 24 builds, at most 566 |
| taps over the 1,000-sink cap | 0 to 31 per type, largest tap 13,264 sinks; each warns `no tap with room within 200 um` |
| taps with sink box W+H over 300 um (`OT_TAP_SPAN`) | 2 to 107 per type, max 306 to 683 um |
| tap mean insertion after balance (target 250) | spread 28 to 147 ps on slices, 205 and 409 on two cb |
| core clock pins outside target +/-20 | su_l1 3 of 10 (329 / 351 / 373 ps), sle_ctl 8 of 16, st_a 4 to 7 of 15, cb 4 of 4 |
| worst skew inside one tap | 32 to 157 ps |
| related-pair skew at sign-off, TT (7 routed) | 115 to 196 ps; sle_sc_v1 433 |

Cause: the plan gives each type one tap rule (`tap_radius_um` 200, cap 1,000, density mode) and V2 does not change it. Where sinks are dense the nearest
tap is full, the sinks stay on a far or over-full tap, and the pairing pass has nowhere to move a launch / capture pair. Core taps arrive 80 to 120 ps late.

Cost of closing it by padding (pre-GRT pass, margin 40 + cross-tap guard 45):

- 3,053 to 94,307 hold cells = 1.4 to 20 % of instances; 0.1 to 6.9 h.
- Setup WNS in the same session falls 0 to 120 ps (typical 45 to 60: 123 -> 63, 136 -> 79, 92 -> -1, 84 -> 23, 120 -> 0).

### 1.3 Can route-stage repair close it? (V)

- **Internal: yes.** At GRT 0 to 277 endpoints reappear at -2 to -76 and close to +19 to +40 in at most 3 chunks. After detail route, 5 sign-offs read: internal hold violators 0 / 0 / 0 / 0 / 1 (-8.50, slw_fw_v1__clf51c11d8__cl592e3d37); sle_fw_v2__cl69f5e854 -1.67 (log line). R: one late ECO took slw_fe_v1 from -60.89 / 126 endpoints to -3.63 / 1.
- **port_in: no, and it should not try.** It is outside the repair set; only a parent run on real views decides it.
- **It has a price.** su_l1: `OT_HOLD_SETUP_GUARD stop: worst setup -201.60` after one hold chunk; `OT_REPAIR_STALL` on 32 of the 66 builds.
- Routed setup, the real blocker: sle_su_l1__cl5ea486db -43.05 (`u_ft_rsf_o_1 -> u_ft_rsf_o_2`), sle_fw_v2 -49.46 (`u_bin_x_sc_i -> u_ist_sc_eo_0`) and -47.52, slw_hc1 -49.73, slw_fw_v1 -74.03 (`u_bin_x_sc_i -> u_bout_flt_wo`, 17 buffers, 846 ps of data path, 1 endpoint), slw_hc0 -75.63, slw_fw_v3 -84.28. Violators 1 to 49 per build.

### 1.4 Ranked fixes

| # | fix | evidence | owner |
|---|---|---|---|
| 1 | Plan tap rows by region: sink box W+H <= 300 um, add taps where a tap is over cap (start: sle_ctl, fe_v2, fw, stm, su_l1, cb). Same finding as FABLE-PD-QC-0407 sec 2; still not in the plan. | 1.2 table | QC-PLAN-R9 (V3) |
| 2 | Core tap rows: raise `insertion_ps` / parent budget for core clock pins measured late (su_l1 lanes 4 to 6: 329 / 351 / 373; sle_ctl 8 pins; st_a; cb tiles) | `OT_TAP_CORE ... still late` | QC-PLAN-R9; FAM-QC-HCST and FAM-QC-CB supply the measured values |
| 3 | Launch-side lockup on the cross-tap pairs left after 1 and 2, only under 200 um, no seam latches | S81 proof6 cross-tap 14,251 -> 9,161 (R); seams cost -57.7k TNS (R) | LOCKUP-STATION-R3, after the QC2 proof |
| 4 | Final ECO, up to 3 passes, for the 1 to 5 residual internal endpoints | -8.50 / 1, -1.67, -3.63 / 1, -4.69 / 5 | FAM-QC-FEFW, FAM-QC-HCST |
| 5 | port_in: one parent `io_hold` run per seam class on real views; until then report it UNMEASURED | `parent_qualification NEEDS_PARENT` on every sign-off | QC-PLAN-R9 |
| 6 | Reporting: print internal hold (`class after`, `internal_hold`) in the pre-route and autopilot lines, port_in separately. Late ECO: allow passes 2 and 3; one pass took 13.2 h and 19.9 h (R, wave rows) | 1.1; wave `q_reason ... no second ECO` | new lane (flow) |

### 1.5 Stop list

- Stop quoting `hold_est` or the -62 to -178 figure as a build's hold, and stop triaging or cancelling on it.
- No extra hold margin, guard or GRT hold pass aimed at it. No hold buffers on input ports in kits.
- No seam latches. No lockup rows before the QC2 proof.
- Do not lower a tap cap without adding taps: cap 1,000 leaves taps of 2,000 to 13,264 sinks.
- Do not read slw_su_l1 as hold-limited: its two builds are setup -29 to -46 at GRT with 1 to 8 internal hold endpoints.

## 2. One-cycle reset relay (cbf_q00__cl1b5a6458 fp3, -393.97)

**Root cause (V).** `u_rrl_482` is the leaf relay of reset tap 45, sited at (670, 1257), the centre cross of the four tiles. Its output is the type's
`u_bound.rst_n`. The four fabric column stations `u_u_fab_u_x_{0_0,1_0,0_1,1_1}` take that net. `x_0_1` sits at the top-left corner near tap 93
(64, 2501): 606 + 1,244 = 1,850 um Manhattan round tile `u_t01`. The path is 22 buffers plus one unbuffered segment (80 fF, 365 ps wire, slew 1,158 ps)
where the net cuts a tile macro that has no buffer site. Arrival 1,245 ps after launch against 851 ps allowed. The relay tree itself is fine:
depth 14, 108 leaves all at depth 14, planned hop 275 um.

| # | fix | evidence | owner |
|---|---|---|---|
| 1 | `reset.inst_taps`: station instance -> nearest leaf relay (taps 24 / 25 / 93 / 100). All leaves are depth 14, so 0 cycles and the same release edge. | above; plan rows present in b14 for this type | RESET-RELAY-GEN-R3 (rows), FAM-QC-CB (fp4 proof), QC-PLAN-R9 (carry) |
| 2 | `reset.local_taps_um` where no leaf relay is within 300 um (cbn_q11__cl5cc92dfe, 379 um) | row present in b14 | same |
| 3 | Rows for cbf_q01 and cbf_q01_s2: none in b14 | 15 of 17 cb types have `inst_taps` | RESET-RELAY-GEN-R3 |
| 4 | Checker: leaf relay -> sink leg <= 300 um per type in the event census. The bind proves relay hops only (`long_hops` 0, max 298.6) | fp3 passed every bind check | QC-PLAN-R9 / census |

- Relay depth: no change needed. More depth does not shorten a leaf leg.
- Multi-cycle release: no. Near sinks of the same net would leave reset one edge before far sinks. It is also a constraint fix, not a structural one.
- fp3 also printed `placed max hop 307.8 um, 2 hops > 300` on the relay tree: re-site those two in fp4.

Stop: no route of fp3 (FAM-QC-CB already held it); no relaunch of a cb kit without `inst_taps` applied to the kit RTL (`apply_inst_taps`; the kit binds resets
only at strict bind); no reading of the -299 latch path or the -215 hold as failures (pre-CTS ideal clock).

## 3. V2 (b14 plan, b15 = + 2 hc0 clones)

**State (V).** b13 and b14 strict: 3 errors, TYPE_SPLIT x 2 and EMIT. No latency, QFT or reset error. b15 chain stopped at the non-strict bind (headline 6).
The non-strict bind still reports `EMIT clock landing: emitted module/type inventory changed after cohort composition`, so EMIT may not only follow the splits (I).

| test | result on b14 (V) |
|---|---|
| hop <= 405 | **Fails on 28 station rows + 1 ft slot.** `budgets.ft_station_max_um` and `reset.hop_um` are still 405. |
| hop <= 300 | internal stations over 300: 351 -> 96. ft slots with plan sites: 212 of 319 have a station-to-station leg of 301 to 400 um; V2 changed none of them. 75 have last station -> out pin over 300 (max 363). |
| tap <= 300 | **Not addressed.** No tap rule changed on any type (radius 200, cap 1,000, same sink bins). Today's kits on that rule: 1.2 table. |
| depth | 876 lanes +1 to +8 cycles, no negative pad, bind clean on latency. LATCHECK has not run on b14 or b15. |
| reset reach | relay hops <= 298.6 um, die hop max 368.2, unreachable 0, wavefront release max 205. Leaf legs: section 2. |

Rows over 405 (V): cb `bc_i00` / `bc_i10` / `bc_i30` with one station on 1,225 to 1,271 um (legs 611 to 637; cbf_q00 x3, cbn_q00 x3, cbx_q10 x3), `nb_i12` 411 to 418
(cbf_q01 x2, cbn_q01 x3), slw_stm `flt_o` 536 to 548 (1 bit, 4 types), sle_ctl `x_fw_p2_i` first leg 432 (537 bits), ft slot sle_ctl `cws2` 577 (check against its per-bit sites).

**What V2 still leaves to fail**

1. cb family, 17 types: station rows are identical to V1 (the b10 note holds them "pending joint tree alignment"). Only reset taps changed. Class A of FABLE-PD-QC-1840 (-1.3 to -8.6 ns at place) is untouched. Owner FAM-QC-CB.
2. The routed setup class of 1.3: e.g. sle_su_l1 `rsf` legs 347 / 400 / 374 / 387 / 385 are unchanged, and the routed worst path of that type is `u_ft_rsf_o_1 -> u_ft_rsf_o_2` at -43.05. Owner QC-PLAN-R9 (V3: +1 station on the 212 slots), FAM-QC-HCST.
3. 312 ft slots on 72 types carry stations but no plan sites (183 of them gained +1 / +2 in V2). Their hops are decided at gen. 12 are known to need more hops (R). Owner QC-PLAN-R9 + FAM-QC-FEFW.
4. Taps (1.4 fix 1 and 2).
5. Reset rows for cbf_q01, cbf_q01_s2.
6. coll_core / coll_ftc: ODPRE and write-register rows are staged, not in V2 (R). Owner FAM-QC-COLL.
7. sle_ctl / su_c core-slit class: rows are in V2, no GRT number yet (R). Owner OPUS-FIX-QC-SLE-R4.

Stop list: do not call V2 a 300 um plan or "safe by construction"; do not launch cb volume on V2; do not add a third TYPE_SPLIT loop without diffing the bind
against the green V1 bind (R9 already plans this); do not hold V2 for any item here: it removes 255 station rows over 300 and should apply once it binds.

## 4. Not checked

- Die-level seam hold (no parent run exists). Whether `in_min -85` is tight or loose is unmeasured.
- Which sign-off session the pre-GRT `setup_wns` figures use (TT or FF); the routed worst paths I opened carry no hold cell.
- Placed positions of the `x_0_1` sinks (taken from the tap 93 row, not from the database); hard-core reset pins on sle_ctl.
- Whether gen sites the 312 site-less ft slots at 300 um or less; sle_ctl `cws2` per-bit sites.
- b15 itself (no plan file existed when I read); LATCHECK, G0, census on V2.

# FABLE-PD-S81-1100 (2026-11-21 11:05 PST): col_h9_r0 detail-route result and lepe_mu_LP proof9 hold / setup

Reviewer: FABLE-PD-S81-1100 (Fable). Read-only. Nothing built, cancelled, patched or signalled. Four light odb reads via ot-run on epyc10 (units 1309131, 1446778, 1577818 and one failed 1385970), about 2 min each.
Marking: **V** = I read or computed it this round. **R** = reported by the named lane. **I** = inferred.
Earlier reviews stand: FABLE-PD-S81-0830, FABLE-CLOSURE-STRATEGY b9ecdd6c8e2. Scripts and logs: `epyc10 /srv/opentallas-scratch2/claude/fable-pd-s81-1100/tmp/` (drcbin.py, probe.py, probe2.py, probe3.py, probe4.py and their logs).

## 0. Verdict

1. **The col_h9_r0 rep was not congested. The watchdog cancelled a run that was converging (V).** Job 0d6487d7a8c6 finished DRT iteration 0 at 151,954 after 3 h 46 min, and iteration 1 had fallen to 60,258 at 70 % when it was stopped. The watchdog reads only the end-of-iteration count, so it saw one number.
2. **Two different things are left on the four kits, and neither is a global-route capacity problem (V).** Global route ends with 0 overflow at 14.5 % usage on all of them.
   - **Hard-core pin shorts on M5, on every kit that converged.** p2 class cl9f71e63d ends DRT with 20 (17 M5 + 3 M3, all against `u_r0_u_cf`). p3 is at 15 at 10:52 PST (M5 against `u_cf` and `u_t0` at iteration 15). This blocks DRC 0 on every col type that carries `dsfd_cfifo_crs4`, in both orientations.
   - **One class, cl0045af7b, is stuck at 28,640** (iterations 5 to 8: 30,561, 29,838, 29,440, 28,640). 27,106 of its violations sit in one strip 130 um x 15 um under the south face of ROM pair `e2`.
3. **Same mechanism as the 216-type J7 risk? In part (I).** The M5 pin shorts are type-wide and will be on J7 kits unless the cfifo view changes. The stuck strip is a class-specific crowding of xo relay stations, not the reach problem; but the reach fix (more stations per chain) feeds the same corridors, so it needs one check per class. The J7 xo D3 rep is no worse than the class that routed.
4. **lepe proof9 is the wrong kit to judge.** proof10 reads -64.5 post-hook (R). The 11,314 hold endpoints are a tap problem: tap means span 236 to 380 ps against a 250 target, 7,954 short pairs stay across taps, and `OT_TAP_RESET_AFFINITY` is not set. The single worst endpoint (`rov_r[41]`) has its clock pin on a non-clock net.

## 1. Event 1: col_h9_r0 detail route

### 1.1 DRT trends (V, from each job's `5_2_route` log)

| Job | Kit | Host | Iteration ends | State 10:55 PST |
|---|---|---|---|---|
| 0d6487d7a8c6 | p2 cl9f71e63d pva4376595 (rep) | intel1 | 151,954; iter 1 at 70 %: 60,258 | cancelled 09:15 |
| 64e24c10ad78 | p2 cl9f71e63d pv11b73b67 | epyc10 | ... 26, 24, 22, 20 at iteration 64 | DRT done, 7 h 07 min. Sign-off: DRC 20, TT -205.74, hold -12.48. In ECO |
| 4e4323c4d5b1 | p3 cl8ce97bcb pvd2159f4a | epyc10 | 196,822; 37,186; 25,984; 1,234; 207; 135; ... 34; 15 | still iterating, 15 left at 10:52 |
| 3283f16cae2b | p2 cl0045af7b pva2793873 | epyc10 | 211,425; 69,258; 54,269; 33,830; 31,406; 30,561; 29,838; 29,440; 28,640 | iteration 9, flat |

- The rep's iteration 0 took 3 h 46 min on intel1 (load 140 on 112 cores) against 2 h 04 min for the same design size on epyc10. It was slow, not stuck.
- The rep's iteration-0 table: 136k of 152k violations on M1 to M4 and V2 to V4 (M2 short 19,239, M4 eolKeepOut 16,720). That is the normal first-pass shape; the two siblings start at 197k and 211k and one of them ends at 20.
- Global route on the rep: resources 191.5M, demand 27.8M, 14.53 %, congestion 0 / 0 / 0 after 14 extra iterations. The band y 1220 to 1260 reported at 09:56 is in `congestion-5.rpt`, an intermediate report; it is gone at the end. Of the 27,106 located violations of the stuck sibling, 26,999 are in the strip of 1.2 and 79 at y 870; none is near y 1220.

### 1.2 The stuck class: xo stations and the bus repeater row in one face strip (V)

Kit pva2793873, DRC report at iteration 5 (27,106 records):

- 26,999 records lie in y 620 to 635, x 210 to 345. Types: M2 short 5,447, M4 eolKeepOut 4,244, M4 short 3,068, M2 eolKeepOut 2,385.
- Nets named in them: `u_bout_xo_o*/net*` 16,392, `u_r0_u_y_xo*_*.o[*]` 11,684.
- The strip is the first three cell rows under `u_e2_u_w` / `u_e2_u_e` (ROM pair, south face y 635.05). `u_bs2` is below at y 566 to 592.
- Cells in x 200 to 350, y 615 to 640 (3,750 um2): 1,585 BUFx12f of the `u_bout_xo_o` wire chain, 873 INVx4, 636 DFFASRHQN of the xo relays with 635 TIEHI, 600 BUFx10, 303 BUFx12.
- Row y 625: utilisation 85 to 96 % over about 100 um, 240 to 300 signal pins per 25 um2 bin.
- All four last-stage xo stations sit side by side in that strip: xo3_1 x 257 to 301, xo2_1 296 to 341, xo1_1 337 to 382, xo0_1 375 to 421, all y 622 to 631. All four first-stage stations sit side by side under `e3` at x 855 to 962, y 622 to 634.

The class that routed (pv11b73b67, cl9f71e63d), same box: 872 BUFx12f, no INVx4, no relay flops; row y 625 at 0 to 44 %. Its xo chains split two and two: xo0 / xo1 last stage at x 407 to 485 in the same strip, xo2 / xo3 along the north (y 1141 to 1147).

Macro placement differs between the two classes on `e3` (y 648 against 635), `bn3`, `s4`, `t2` and `t2_payload` (V, diff of `macro_place.tcl`). That is what sends all four slices down one corridor in cl0045af7b.

Cause: `OT_RELAY_MID` places each station as a compact cluster on its source-sink line. Four parallel chains share one line, so four clusters land in the same three rows, on top of the bus's own repeater chain. `OT_RELAY_MID_FIT` is on but fitted 12 of 105 stations and none of the xo ones (V, `3_3_place_gp.log`). It is a pin-density failure in a three-row strip, not a track-capacity one.

Not the cause here (V): obstruction-adjacent sliver gcells (GRT uses no capacity it lacks; `obs_gcell_cap` f56d99cf55 would change nothing, as R3 also found), reserved strips, clock-landing bands (p3 has 280 dense bins in its `u_cland_xo_i` rings and still converged to 15).

### 1.3 The residue on every converged kit: M5 shorts at hard-core pins (V)

- pv11b73b67 final: 17 M5 shorts at x 1157 to 1296, y 659 to 670 and 3 M3 shorts at y 606.8, all `inst:u_r0_u_cf` against a signal net. `u_cf` is MX at (1131.9, 604.8), 280.8 x 69.1, so the M5 shorts are 4 to 14 um inside its north edge and the M3 ones 2 um inside its south edge.
- pvd2159f4a at iteration 15 (42 records): 31 M5 shorts on `u_cf` (R0 here, y 608 to 620, plus two at y 656 and 664) and 8 records at (1188.9, 253.6 / 259.7) where one net shorts `u_t0`, an obstruction and VSS on M4 / M5.
- The cfifo LEF has its `xl*` and `rd` pins on M5 at the R0 south edge (24 nm x 84 nm) and M5 OBS over the body.
- This is the class FAM-S81-COL-H10-R2 counted as 26 M5 shorts and OPUS-FIX-QC-SLE-R4-SC's via shadow (1980f8126c) is reported to cover (R). That commit was not on main at 07:36 and I found no later post that it landed. b49b697c40 (PG crossing preflight) is on main and gates it (R).

So a col kit that routes cleanly still ends at 15 to 20 violations. ECO passes cannot remove a short against a macro body.

### 1.4 J7 exposure (V unless marked)

Dense-bin count on placed DBs (5 um bins with utilisation >= 0.85 and >= 240 signal pins; `probe2.py`, `4_cts.odb`):

| Kit | Bins | xo stations in dense clusters |
|---|---|---|
| pva2793873 (stuck) | 77 | 28 bins in four clusters at y 600 to 635 |
| pv11b73b67 (routed to 20) | 76 | 6 bins at (950, 500), 3 at (1150, 1100) |
| J7-form rep, xo D3, private kit pva4376595 | 69 | 5 bins at (1200, 550) |
| p3 pvd2159f4a (routed to 15) | 280 | none; all in clock-landing rings |

- The D3 rep's last xo stations are at x 93 to 181 under `e2_u_w` (two) and y 1142 (two): the same two-and-two split as the class that routed. Its GRT ends at 14.63 %, 0 overflow.
- My probe matched only the first and last station of each chain by name, so the three middle D3 stations per chain are not located.
- The total count does not separate the stuck kit from the routed one (77 against 76); what does is four stations of parallel chains plus the repeater row in one strip.
- Not measured: how many of the 216 types take the cl0045af7b corridor on the J7 plan.
- The reach recount (685k legs over 405 by detour length, R) is a length measure. Its fix adds stations, and each added station of a 276-bit chain is one more cluster on the same line. That is the coupling to watch; it is not the cause of today's stall.

## 2. Event 2: lepe_mu_LP t2 proof9

### 2.1 Setup (V for proof9, R for proof10)

- proof9 post-hook: -292.10, TNS -32.8 ns. The five worst paths start at `g_rx[*]` RX memory banks or `pair_b` and end at `f_host[*]`.
- After the pre-GRT hold repair the kit reads setup -423.28 (`pregrt_ff_hold.log`). That number is what the UNSIGNABLE watchdog listed at 10:30.
- proof10 (+1 relay stage on `unit_o0`, lane 87 to 88 cycles) reads -64.5 / TNS -0.87 ns post-hook (R, 10:43). The stage is the right fix and is pre-approved.

### 2.2 Hold (V)

`pregrt_ff_hold.log`: 12,840 endpoints, worst -166.91. By class: cross-tap 8,350 (worst -166.91), input ports 3,726 (-159.57), same-tap 251 (-26.96), output ports 513 (-14.10). `repair_timing` found 11,314 and inserted 11,074 buffers, then 78 more.

- **Tap spread.** `OT_TAP_BALANCE done: tap mean insertion 236..380 ps (spread 144, target 250)`. Balance only adds delay, so the three late taps stay late: root tap `clk` mean 349 (max 394, exactly 1,000 sinks), `clk_t65` 352 (skew 94), `clk_t8` 380 (max 421). The other 68 register taps are at 252 to 313.
- **Pairs across taps.** `OT_TAP_PAIR` ends with 7,954 cross-tap short pairs after moving 114 clock pins; 27 taps were over the 1,000 cap at start and 54 components were frozen as oversized.
- **Reset last stage.** 1,012 `g_reset_balanced.u_rstr.g_local[*].local_r` flops on 54 taps drive 7,368 async pins; 2,194 of those (30 %) are on a different tap than their `local_r` (`probe3.py`). Median distance 7 um, 90th percentile 112 um, maximum 684 um. `OT_TAP_RESET_AFFINITY` is not in `config.mk`; `tap_reset_affinity.tcl` in the kit does exactly this move.
- **The worst endpoint is a one-off.** `g_frame_local.g_slice[41].rov_r` has its CLK pin on a plain `net*` net, the only register in the design that does (`probe4.py`). Its capture clock is 360.06 against a launch of 198.53 on `clk_t28`, which with removal 42.42 and uncertainty 25 gives -163.86. The other `rov_r` flops are on ordinary taps (t69 22, t44 14, t46 11).
- The next removal paths (-123, `g_tx[2].g_safe_write` slice 47) also capture at 359; I did not identify their tap.

Padding 11,074 buffers into paths is what moved setup from -292 to -423. The cause is clock structure, so the fix is on the clock side.

## 3. Ranked fixes

| # | Fix | Owner | Evidence |
|---|---|---|---|
| 1 | Re-export `dsfd_cfifo_crs4` (and check the `u_t0` master) with the via-shadow OBS, and put the view into the J7 kit inputs before col kits route. It changes no row, so the 20:00 row cut does not bind it; the 04:15 apply does. Accept on one routed col kit ending at 0 against `u_cf` | OPUS-FIX-QC-SLE-R4-SC (land 1980f8126c on b49b697c40), FAM-S81-COL-H10-R3 (view + proof), S81-J6-ASSEMBLY-R4 (pick-up) | 1.3 |
| 2 | Watchdog: count progress inside an iteration (`Completing N% with V`) and require two finished iterations inside the window before a no-progress cancel | COORD to assign (autopilot watchdog) | 1.1 |
| 3 | xo stations: stagger the stations of parallel chains along the shared line by one cluster length plus 20 um, keep them off the row that carries the bus repeaters, and put the xo groups through `OT_RELAY_MID_FIT`. Prove on a cl0045af7b kit | FAM-S81-COL-H9R0-R3 | 1.2 |
| 4 | Before the J7 col wave: one placed read per col class with `probe2.py`; flag any strip where three or more stations of different chains sit within 150 um in the same three rows. List which J7 types take the cl0045af7b macro positions (`e3` y 648) | FAM-S81-COL-R4 (h9_r1 / r2 and the census), FAM-S81-COL-H10-R3 (h10), S81-J6-ASSEMBLY-R4 | 1.4 |
| 5 | Relay-branch and depth rows for J7: keep them, but count stations per corridor in the row generator's report, since each is a 276-bit cluster | FAM-S81-COL-R4, S81-J6-ASSEMBLY-R4 | 1.4 |
| 6 | lepe: proof10 is the lead. Add to it, as one A/B overlay on the wave env: `OT_TAP_RESET_AFFINITY=1`; find why `rov_r[41]` CLK is on `net*` and put it back on its tap | FAM-S81-LEPE-3 | 2.2 |
| 7 | lepe late taps: split or re-seat root tap `clk` (1,000 sinks at the cap, mean 349), `clk_t8` and `clk_t65` so every tap reaches the 250 target, or raise the target to the slowest tap. Then re-read the cross-tap class before any hold repair | FAM-S81-LEPE-3 | 2.2 |
| 8 | lepe J7 / J8 rows: the `unit_o0` relay row after proof10's routed read, as the lane plans | FAM-S81-LEPE-3, S81-J6-ASSEMBLY-R4 | 2.1 |

## 4. Stop list

1. No relaunch of the J5 rep pva4376595: it would not sign (TT -74, R) and its class result is already known from pv11b73b67.
2. No plan change to the ft0 pin band or the `frame_int` rank for the y 1220 to 1260 band: it is an intermediate GRT report, not a DRT result.
3. No `obs_gcell_cap` or GRT adjustment as the col_h9_r0 fix.
4. 3283f16cae2b (pva2793873): stop at the next check rather than at iteration 12. Four iterations gained 6 % and the cause is placement. Its DRC report and placed DB are the evidence for fix 3; keep the kit dir. Owner call: FAM-S81-COL-H9R0-R3.
5. No further ECO passes on pv11b73b67 for DRC: the 20 are macro-body shorts, and TT is -205.74.
6. No KEEP for proof9 against the UNSIGNABLE notice of 10:30: proof10 supersedes it. Copy `pregrt_ff_hold.log` and the post-hook report first.
7. No hold-buffer repair on lepe as the fix for the cross-tap class, and no post-CTS setup repair on top of it.
8. No J7 col volume routing before the cfifo view of fix 1 is in the kit inputs.

## 5. Not checked

- Where the rep's own violations were: its DRC reports went with the job dir. The location evidence is from the two siblings.
- Whether via shadow removes all 17 to 31 shorts on these kits: reported by the view lane, not run by me.
- The three middle D3 xo stations per chain, and any class other than the four kits above.
- Which tap captures the -123 `g_tx[2]` removal paths, and why the launch insertion reads 198 in the hold scene against 252 to 313 in the tap table (I assume corner scaling).
- proof10's own hold classes: epyc7 is in a disk stall and I read only the lane's post.

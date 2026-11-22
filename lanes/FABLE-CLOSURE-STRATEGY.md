# FABLE-CLOSURE-STRATEGY 2026-11-21 18:30 PST (lane FABLE-CLOSURE-1320): S81 col still has no proven macro view and is held out of J7; the largest open timing classes on S81 col, KV hg and QC cb are reset or clock distribution, not data logic

Supersedes the 11:35 round (FABLE-CLOSURE-1120, coord/state 7a88fa0048; `git log -2 -- lanes/FABLE-CLOSURE-STRATEGY.md`). Its stop list stands except lines 9 and 14, which this round withdraws (section 2).

Reviewer: FABLE-CLOSURE-1320 (Fable). Read-only: nothing launched, cancelled, signalled, patched or deleted; no ot-run job; no git outside ~/coord.
Scope: S81, HEAD, QC, KV physical design only. Gate: DRC 0, TT setup >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. No die or outline growth. Nothing below is a new gate.
Marking: **V** = read by me this round from the named log, DB-derived report or kit file. **R** = reported by the named lane. **C** = reported by Codex in CODEX-LOG.md lines 14146 to 14220 (takeover 14:23 to 18:11); none of the C numbers were re-read by me. **I** = my inference. **P** = proposal.
Timing of this round: my own reads are from 13:10 to 13:35. The lanes were limited from about 14:2x; section 0b and the C lines were folded in at 18:15.

## 0. Last round's levers and the COORD 13:2x facts, re-measured

| Item | State now |
|---|---|
| Lever 1, col `u_cf` view inset + halo ("31c7ccbd1b") | **Not proven, not in J7.** Via shadow 1980f8126c is REJECTED in the J7 ledger (R, S81-J6-ASSEMBLY-R4 12:03); col volume is held until a view exists. A re-exported view sits in the lane's private tree only (V: epyc10 `fam-s81-col-h10-r3/srcJ7L1/physical/ref_tile/s81coll_cfifo_crs4/views/dsfd_cfifo_crs4/dsfd_cfifo_crs4.lef`, written 12:20, sha daea3c415efd). No kit runs on it: no private-spec dir for FAM-S81-COL-H10-R3 on the hub and no `pvcc166a6d` / `srcJ7L1` process on any build host (V 13:20). 31c7ccbd1b93 was an rt snapshot (the QC V3 bind tools); I found no col proof tied to it. See lever 1 |
| Lever 2 item 1, `OT_RELAY_MID_FIT` selects 0 | **Landed**, main ae660e1299 (R): polyline chains never wrote `rm_seg`. Replay on placed DBs: proof C 0 -> 155 of 157, col_h9_r0_p5 0 -> 67 of 71. No fresh place + GRT yet |
| `OT_RELAY_MID_STAGGER` (c54a7596fc) | **Landed, but its proof kit does not move the chains it was written for (V).** See lever 4 |
| Lever 3, pipeline stages | Serdes encoder SIGNED without a split (R: enchp_j6b TT +25.72, hold 0, DRC 0). Col ROM-input stage waits on the guard gate candJ7cG (19:00 cut). lepe proof10 post-hook CTS -64.47 / hold -180.74 (V), in GRT. QC btab row not built |
| Lever 4, clock-first + resistance-aware GRT (79210da191) | **Numbers confirmed (V)**, epyc8 `flow-clkgrt-1121/out`: base TT -659.87, TNS -23,480.7, hold -473.58; combined arm TT -609.14, TNS -27,519.5 (17.2 % worse), hold -232.20, FF internal hold -59.96 on 332 ends. Base arm lost the NDR on 29 clock nets (GRT-0273), the clock-first arms on 0. Real kit kv3_hg_v1p2: clock-first arm at place since 12:57, combined arm at gen 13:21; no GRT result |
| Lever 4 item 3, `OT_TAP_RESET_AFFINITY` | **Lost at CTS (V).** lepe proof11 post-hook -121.27 / -196.81 against proof10 -64.47 / -180.74 |
| Lever 5, S81 start-strobe | **Root cause measured by FABLE-FIX-S81-STROBE (R); my 11:35 inference was wrong.** It is distance: one START broadcast crosses 1.7 to 2.8 mm in one cycle. See lever 3 |
| KV face pins inside clock-site OBS | Confirmed as a plan class (R, KV-PLAN-R6): 920 face-pin hits on 42 types under D27d2; `clksite_pinclear` (main 114851a275) moves 62 die clock rows by 0.05 to 2.16 um, 0 hits left. D27d3 apply about 17:00 |
| Merged-register class | Confirmed on three families and it is the largest col timing class. See lever 2 |
| QC sle_ctl siting | R (QC-PLAN-R11 path read): -440.7, about 1,550 um of wire for a 380 um Manhattan distance. Variant B (+1 station) is dead: 671 ends at -85 to -94, all `u_cland_cws2_i/d`. Variant C has no flow log yet (V) |
| HEAD hd_lep0N shelf form | V, epyc10 `fable-fix-head-lep0n-env/shelf_we`: post-hook CTS TT +22.00, TNS 0, hold -117.55 (TNS -442,399), 357,856 non-tap cells = 89.5 % of the cap. No GRT log yet on either kit |

## 0b. Codex results 14:23 to 18:11, and what they change

| Result (C) | Effect on this report |
|---|---|
| S81 J7 preferred package a6771d121e95 sealed (strict bind, LATCHECK 873, PRE pass; G0 nine known findings). J7eL6 / enL6 replace 25 physically violating START forms at unchanged data cycles. Apply is conditional for 11-22 04:15 with an explicit col hold | Lever 3 rows are in J7 for slice_station. Lever 1 outcome is decided for J7: no col volume |
| The guarded ROM-input pair stays in the J7 package. lepe proof10 is out of J7 after a real GRT-0116 with 2,991 overflow | Lever 5 items 1 and 2 change |
| col_h9_r0_p2: 5,401 GRT overflow, from the xo fallback. col p4 DRT 15 = 11 dense relay M2 defects + 4 true FIFO OBS shorts; H10's seven are same-net EOL at the LEF | Confirms lever 4 (xo NOFIT). Splits lever 1 into two classes |
| Serdes decoder dec_j6c: DRC 0, TT +14.15, internal FF hold 0. First routed LEC receipt NOT EQUIVALENT on 33 points; export held | Serdes cores need no pipeline stage. The open item is LEC |
| Serdes t16 west run 3,168.6 um with 812 captures over 405 um; t14 private placement clears 3,417 over-405 captures (max 404.57) | Lever 3: serdes rows are not yet physically proven |
| KV D26 hg -559.80 is a 23-level, 1,730 um reset chain. hgi 993295117977: about -450 ps recovery, stopped at -738.66. hgi_v3: 3,353 over-cycle captures, 944 um reset-to-lockup, 8 clock entries on macros | Corrects my lever 8, which listed kv3_hg as a possible measurement artefact. It is real. New lever 7 item |
| KV D27d3 48b92c30c8f6: strict bind, LATCHECK, 9 gen proofs and G0 pass; the apply script was paused before seal | Lever 7 item 1 is ready to apply |
| QC coll_core prefers 48 um aisles against 4.33 um, needing a reset rebind (508 -> 477 relays). Fault return: farthest source 1,453 um from the return register = 4 legs at 405 um, 8 -> 11 cycles. coll_ftc r4: -166.03 -> +55.28 with 66 hops still over 405 | New lever 8 |
| QC cb q01 repeated cut: 514 over-cycle paths, 765 / 846 um; worst 679.94 um -> DLL + 333.99 um -> capture with +453.92 ps clock skew; true TT -321.75. Preferred q01 S2 form: TT +18.75, internal FF -31.03, not routed. cf0b endpoint corrected from -659.86 to -380.66 on the stage SDC (observer fix 9bf23638b0f) | Lever 6 and lever 9 |
| HEAD START tr12 with 32 separated measured clocks still fails 219 of 329. p6 tr23: START 1 / fault 0, 329 of 329 raw measures, 202 stable differences, priced replay pending | Withdraws line 16 of the 11:35 stop list (section 2) |
| HEAD hd_ctl a8: DRC 0, hold 0, NOT SIGNED on TT -164.14, `wd2[876] -> xb1/wd_in[364]` through HB4 / HB2 hold cells. WRCAP form: TT +0.11 at GRT, 0 overflow, south ring density 0.945. hd_mesh r16 cancelled: north pin access under blanket clock-site OBS | HEAD is no longer "one type open": see the HEAD paragraph |
| LANE-STATUS 18:16 (V): FAM-S81-COL-H10-R3 stood down to FAM-S81-COL-H10-R4 with "lever-1 kit not launched (epyc7 tree ready); proof A GRT-0116" | Lever 1 is still unproven five hours on; H10-R4 owns the launch |

## 1. Levers, ranked by types unblocked

### Lever 1. S81 col macro view: launch the one fresh kit now, or col misses J7 (216 col types)

- Evidence:
  - R: every converged col kit ends with 15 to 31 shorts against `u_cf` / `u_t0`; the ECO form died DRT-1231 twice.
  - V: the new LEF is 280.8 x 69.12. Its OBS bounding boxes still reach the west and south edges: M2 0.103 / 1.152, M3 0.108 / 0.043, M4 0.060 / 0.048, M5 0.144 / 0.016 um from the W / S edge; the east side is 1.95 to 1.99 um clear. So it is not a uniform 0.30 um inset. I could not tell from the LEF alone whether the edge shapes are shadow or signed metal.
  - V: the halo mechanism already exists (`hard_cores[].halo_um` -> `ot_macro_halo` placement blockage, gen_phys HALO-1 of 11-18). It needs a plan row, not new tool code.
  - C: the 15 leftover violations on col p4 are two classes: 11 dense relay-flop M2 defects and 4 true FIFO OBS shorts. H10's seven are same-net EOL at the LEF. Col is explicitly held at the J7 apply.
- Root cause (I, refined by C): three mechanisms at the same macro edge. Relay flops packed against the macro (M2 density), a few routes that via up at M5 pins inside the body (true OBS shorts), and same-net EOL stubs at the pin LEF shapes.
- Fix (P):
  1. Today, before 19:00: one fresh col_h10_r0_p4 pvcc166a6d kit on candJ7c with the srcJ7L1 view and a `halo_um` row (one cell row, 0.27 um, is the minimum; 1.08 um gives relay flops a clear access track) on `u_cf` and the `u_t0` master. Accept on 0 violations against both macros.
  2. If the west / south edge shapes are shadow, pull them 0.30 um in before the launch; if they are signed metal, leave them and rely on the halo.
  3. J7 applies without col volume (C). The kit above is therefore the J8 entry condition. The halo addresses the 11 relay M2 defects, the view the 4 OBS shorts, the EOL-stub exporter half (proven on QC sle_sc) the H10 seven: the proof kit should carry all three so one run separates them.
- Owner: FAM-S81-COL-H10-R3 (view, row, kit), S81-J6-ASSEMBLY-R4 (row intake).

### Lever 2. Replica reset and pad registers merged by yosys: extend the automatic keep list (S81 col 216, c1x_C 10, p6; QC st_a 11) NEW

- Evidence:
  - R, measured on a final `5_1_grt.odb` (FAM-S81-COL-H9R0-R3 11:49, col rep with xo D3): 980 TT ends below -42. 552 are xo reset recovery, worst -169.27: one flop `u_y_xo0_0.g_rsreg.rq` drives RESETN of 2,210 relay flops in all 8 xo stations. 427 are ROM element inputs (worst -96). 1 other.
  - R (FAM-S81-SLICE-R5 12:32, t9 synth netlist): `xg.u_s.gs1` absorbed every `ot_rst_relay` `sync_q`; it drives 124 pins instead of 1.
  - R (FABLE-FIX-QC-STRAP-R2): four `rs_n_c` pad chains merged into one flop at y 1284 with a 1,067 um last hop, -333.6. With `r8_keep` the proof kit reads `shared_roots 0`, tail max 446.7 -> 14.6 um, hop max 254.0 um, `need_stage 0` (V, place log `OT_R8_CORE_SEAT`; timing still pending).
  - V: gen_phys `replica_keep_wires` (MERGE-CENSUS 11-15) keeps only the port-staging registers of modules instantiated more than once, plus plan stations. `g_rsreg.rq` and `sync_q` are internal registers, so they are outside it.
- Root cause: `opt_merge` folds registers with identical D, clock and reset. Every per-station reset register and every equal-source pad chain is identical by construction. Adding stations (xo D3) makes it worse because one flop then fans farther.
- Fix (P), one flow change and no plan or RTL row:
  1. `replica_keep.derive`: for a module instantiated more than once, keep every register whose D cone is module inputs or constants only (this covers `ot_s81_rly:rq`, `ot_rst_relay:sync_q`, R8 pad chains). Function is unchanged; LEC pairs by name.
  2. Advisory line at synth: registers present per replica in RTL against flops left in `1_2_yosys.v`; a shortfall names the merged register.
  3. Until it lands: `OT_KEEP_WIRES += ot_s81_rly:rq` in the col item env (the H9R0 A/B on the candJ7c rep is running) and `ot_rst_relay:sync_q` for c1x_C.
- Owner: FLOW-OPS-1300 (derive + advisory), FAM-S81-COL-H9R0-R4 (col proof), FAM-S81-SLICE-R5 (t9), FABLE-FIX-QC-STRAP-R2 (QC seat timing).

### Lever 3. START and reset broadcast reach rows on every family (S81: 105 types `start_reach`, 181 `start_writer_reach`; QC: 19 START nets)

- Evidence:
  - R (FABLE-FIX-S81-STROBE 11:53, `report_checks` on three kept `3_place.odb`): serdes t16 origin (2839, 474) -> reader bank (55, 527) = 2.84 mm in one cycle, 27 repeaters, -1,252. slice t18 2.28 mm, 19 repeaters, -857. slice t29 reset relay -> FSTART face flop 1.73 mm, -381. Recovery is reported apart at +572 to +618, so it is not the reset or clock class.
  - V (autopilot/log.txt 12:47): t18 stop line now reads `hop_um=141.9 path_um=2280.1`. `hop_um` was only the longest single cell hop.
  - R: rows = `reach_rules.py fix --rules 1` (reader / writer START relays, K adjusted at bind, 0 data cycles). Private gate on J6r1 green: strict bind 0, LATCHECK 873 / 873. slice t37 with rows: post-place +10.22 (was -111.5).
  - V: proof kits slice_station__t18 and serdes__t16 were at kit_rtl at 12:59, not placed.
  - Same class on QC (V log): slw_fw_v1 `cland_rstart_in[0] -> u_cland_writer_start_x_st_a_o_0/q` -303.90. S81 serdes t14 -533.02 `u_dec.u_lpr_syn.q -> u_lpl_5_w.g_ck[2].u_local/rq` is the reset form (not read by me).
  - C: J7eL6 / enL6 carry the corrected forms for 25 slice_station types at unchanged data cycles; t36 / t37 are at DRT 0 with pin audit pass. Serdes is not there yet: t16's west run is 3,168.6 um with 812 captures over 405 um and needs a fresh physical proof; t14 has a private placement at max 404.57 um.
- Root cause: count-aligned START and its reset are generated once per type and broadcast unregistered. No reach rule covered them until rule 1.
- Fix (P): rule 1 as a GEN step in J7 for slice_station and serdes (rows are ready), and for leaf (47 / 49), col (59), c1x_C (9), svc (15 / 16), kv_leaf in J8 from each family lane. QC: FABLE-PD-QC-1230 row 6 (19 START nets) in V3. No station row from a place stop without `path_um`.
- Owner: FABLE-FIX-S81-STROBE, S81-J6-ASSEMBLY-R4, each S81 family lane; QC-PLAN-R12 with FAM-QC-COLL-R3, QC-SLE-R5.

### Lever 4. S81 col stations: depth before stagger; the xo chains are under-staged (col_h9_r0 53 types with e3 at y 648, h10_r0_p1 6)

- Evidence (V, epyc8 kit `.../s81/a9ed808a98d/private/FAM-S81-COL-H9R0-R3/col_h9_r0_p2__t1__cl0045af7b__pva2793873_1121120240`, `3_3_place_gp.log`, placed 13:15, FIT_POLY code present in the kit's `relay_mid.tcl`):
  - `OT_RELAY_MID_STAGGER sets 12 chains moved 19 (halved 0) kept 5`. The 5 kept are xo0, xo1, xo2, xo3 and lpl_8_w: "offset would cross a halo / the core edge / the hop cap".
  - `OT_RELAY_MID_FIT fitted 84 stations, 21 on the old fallback`. All 8 xo chains are NOFIT: line 1,624 to 1,792 um with 2 stages, even hop 541.4 to 597.3 um. Also over 405: lpl_8_w 458.4, rr_2_0 478.5, so_1_0 433.3.
  - So this proof cannot show whether stagger clears the 130 x 15 um strip under ROM e2: the four chains that fill it did not move.
  - C: the same class routed: col_h9_r0_p2 ends GRT at 5,401 overflow, attributed to the xo fallback.
- Root cause: two stages on a 1.6 to 1.8 mm polyline leave 541 to 597 um hops. The hop cap that stagger and FIT respect is already broken, so both refuse and the stations fall back to nearest-free, next to each other.
- Fix (P):
  1. xo depth first. On these line lengths D3 gives 406 to 448 um and D4 325 to 358 um; the J7 `mkxo` D3 form reports about 324 um on the J7 geometry (R), which is enough there. Rows for lpl_8_w, rr_2_0, so_1_0 (+1 stage each).
  2. Then one place + GRT kit of cl0045af7b on the J7 tree with FIT_POLY + STAGGER + lever 2's keep. Accept on the strip: xo stations in separate rows, GRT 0 overflow in the bin, DRT falling below 1,000 by iteration 5.
  3. STAGGER should print which of the three conditions refused the move; one line of tcl, it saves the next read.
  4. The 30 um hard-core corner keep-off and the `t0_payload_i` station on the payload pin face (11:35 lever 2 items 2, 3) are still open.
- Owner: FAM-S81-COL-H9R0-R4 (proof, rows), FAM-S81-COL-H10-R3 (FIT / STAGGER code), FAM-S81-COL-R5 (per-class placed read: 13 classes have no placed DB).

### Lever 5. Setup where placement cannot help: a stage, or a seat at the pin (S81 col 216, lepe 4, c1x_C; QC st_a 11, sle_ctl, fw 4, tt_ctlm)

- Evidence:
  - Col ROM inputs: 427 ends below -42, worst -96 (R, lever 2 kit). The stage rows are in J7 but on the no-guard RTL; they ship with the guard package or not at all (R).
  - lepe_mu_LP t2 (V): proof10 post-hook CTS setup -64.47, TNS -869.8; hold -180.74, TNS -299,508.
  - c1x_C t9 with WREG (R): 512k non-tap at CTS, post-hook -850.6, after TT repair -832.5. The write stage alone does not close it.
  - QC st_a btab (R): -124.33 on 22 ends, all `u_u_r3/bt_q_p`; r0 +377, r1 +417, r2 +148.
  - QC sle_ctl (R): strap 7:1 mux at (618, 614), 19 buffers over a detour through (691, 908) and (828, 458) to the station at (909, 526). Port -> `u_cland_cws2_i/d` is a half-cycle capture with no flop.
  - QC tt_ctlm (R): one start flop, 24 to 28 logic levels inside core `qfd_hp13_cpub39_rp_alt`, -266 to -360 on 6 attempts.
- Fix (P), all +cycles pre-approved:
  1. Col: the guarded ROM-input pair is in the J7 preferred package (C). Its timing proof still waits for a col kit (lever 1).
  2. lepe: proof10 is out of J7 (C: GRT-0116, 2,991 overflow). The +1 relay stage fixed setup at CTS (-64.47, V) and the placement then failed routing, so the next proof needs the overflow location read first (which bin, which bus) before any more rows; treat it as lever 4's class until shown otherwise.
  3. t9 and the c1x_C family: split (J8), then WREG with lever 2's keep.
  4. btab: r3-side `g_read` copy plus the SRAM column about 250 um north (window 149 to 370), built as one private kit with the seat.
  5. sle_ctl: relay sites at the rp mux (row R8S-3) for the strap leg; for cws2 wait for variant C at GRT, fallback is the per-bus face register (`freg_buses`, +1 cycle on that bus only).
  6. tt_ctlm: +1 register rank in the core and a lane latency row.
  7. HEAD hd_ctl (C): a8 fails only TT -164.14 on `wd2[876] -> xb1/wd_in[364]`, long routed data through hold cells. The WRCAP write-stage form holds TT +0.11 at GRT; it is the path. Its open issue is the south landing strip at 0.945 density (`u_cland_b_i` + `u_cland_h_rx_i` = 97.1 % of the strip), which the two-row strip candidate addresses.
  8. Serdes cores need no stage: encoder +25.72 (R), decoder +14.15 (C). Decoder LEC (33 points) is the open item.
- Owner: FABLE-FIX-S81-COLROM-R4, FAM-S81-LEPE-4, FAM-S81-SLICE-R5, FAM-QC-HCST-R2 + FABLE-FIX-QC-STRAP-R2, QC-SLE-R5, QC-PLAN-R12.

### Lever 6. Clock: clock-first GRT is ready for a default; tap size and tap target are the open half (all four dies)

- Evidence:
  - V: A/B numbers in section 0. The hroot test DB itself is at -609 to -660 setup, so it proves the clock effect, not sign-off.
  - V (lepe proof11, post-hook): pitch 300 + max sinks 600 + reset affinity gave -121.27 / -196.81, worse than proof10. R: `OT_TAP_MAX_SINKS` is not enforced on explicit-tap types (8 taps over 1,000 sinks, largest 2,804), and affinity moved sinks onto fewer taps. So the tap-size lever is still untested.
  - R (TAP-GRID-R4, KV CTS 11:31): 215 taps or core pins off the 250 target after 8 passes; tap means 263 to 331.
  - V (failure_breakdown 13:11): S81 123 taps over 1,650 sinks, insertion max 838, skew max 328. QC 69 over, 493 / 137. HEAD 2 over, 504 / 82.
  - V: HEAD shelf post-hook hold TNS -442,399 at 89.5 % of the cell cap.
  - C: QC cb q01: +453.92 ps clock skew on the worst of 514 over-cycle paths (679.94 um -> DLL, 333.99 um -> capture); true TT -321.75. The S2 reset-inclusive form reads TT +18.75, internal FF -31.03 before route.
  - C: QC su_c tap cap 10,877 -> 1,000 sinks binds clean; S81 PHY centre clock seats moved worst FF hold -539.49 -> -165.85, leaving a DFI4 clock / data imbalance.
- Root cause (I): a fixed 250 ps target below what large or far taps reach, and explicit taps exempt from the sink cap. The spread is then paid in hold buffers.
- Fix (P):
  1. `OT_GRT_CLOCK_FIRST=1` default after the kv3_hg_v1p2 clock-first arm reads no worse than the wave control on TT, FF hold and overflow at the final `5_1_grt.odb`. Keep `RES_AWARE` opt-in until the combined arm shows TNS no worse; on hroot it cost 17 %.
  2. Enforce the sink cap on explicit-tap types by splitting the tap (lepe `clk_t30` 1,856 sinks first). Then repeat proof11 without affinity.
  3. Balance target = the slowest tap mean of the kit, per kit, and the post-CTS triage bound from the same number.
  4. QC cb q01: the S2 form is the path (C); its -31.03 hold is a small structural item (same-tap capture or one lockup), not a repair pass. The 453.92 ps skew on the old cut is a cross-tap DLL path: keep launch, DLL and capture on one tap in the row.
- Owner: FLOW-CLKGRT-R2 (1), TAP-GRID-R4 (2, 3), FAM-S81-LEPE-4 (proof), FABLE-FIX-HEAD-LEP0N-R2 (shelf hold read).

### Lever 7. KV: D27d3 is the only signable base; three geometry classes ride on it (hg 8, hub 5, pc, io_cor, sys_c, pv 15; 6 of 56 signed)

- Evidence:
  - R: D27d2 strict bind green, not applied because its kits carry the 920 pin / clock-site shorts.
  - V (hub `~/tmp/kvplanr6/d27d2_proofs.out`): 6 gen proofs GEN_OK (hg_v1, hgi_v8, hroot, hub_Wo, pc, pc_v1), 3 failed: io_cor_v1 (R: `snap_slots`, ft11 bank 3 on ft23 cells; row r10c), pc_v3 (R: R8 strap count tool bug, main 0b660fcf93), sys_c exit 2 (cause not in the log I read).
  - R (FLOW-OBS-GCELL-R2): `qkd_ahub` `ck[3..5]` lie under real core M6 signal wires; no LEF-only fix.
  - V (autopilot/log.txt): kv3_pv_v1 -1,199.24, `u_vport_E.sel_q -> u_vport_E.fault`, path 2,805 um over a 670 um span, 31 stages. kv3_hg_v3 -486.94, landing ring `dsel/y[8] -> u_bin_i_hst.../q[8]`, hop 257 um.
- Fix (P):
  1. D27d3 = D27d2 + pinclear + r10c on a runtime >= 0b660fcf93. The 62 moved clock rows change die clock cell positions: the die clock tool reruns on the D27d3 ledger before any die STA is read.
  2. ahub: route-only ECO that clears M6 over the three pin windows, then re-sign and a view sha swap (in progress).
  3. pv: no unsplit build. The `vport` select -> fault path needs a register at the cut face in the D28 split rows; 2.8 mm does not fit a cycle on either half otherwise.
  4. hg / hgi reset (C): the D26 hg stop is a 23-level, 1,730 um reset chain ending at the fallback latch group; hgi reads about -450 ps recovery into an async tail. Fix = split the single fallback latch group by its 8 destination cores at the fixed five release stages (proven in local opt-in RTL), with the regional reset placed per region (5,460 guided moves, +49 taps; first DPL had 140 row errors, retry running). The hgi synchronous-tail form is an owner question in CODEX-LOG; the rule "hold structural, reset >= 64 clocks" suggests yes, but it is the owner's call.
  5. hg: relaunch only on D27d3. Read hg_v3's ring -> bin path with `path_um` first; 257 um is one cell hop.
  6. HEAD has the same pin-under-clock-site class (C: hd_mesh north access under blanket clock-site OBS; private north split opens 25.434 um). Run `kit_pin_site_check.py` on HEAD kits as a read, not a gate.
- Owner: KV-PLAN-R6, FAM-KV-IOPC-R3, FABLE-FIX-KV-HUB-R4, OPUS-FIX-KV-PV-R5, OPUS-FIX-KV-HGI-R6, FAM-KV-HUBC-SYSC (sys_c exit 2).

### Lever 8. QC collective: aisles and a registered fault return (coll_core, coll_ftc, coll_ftm) NEW from C

- Evidence (C): coll_core macro aisles are 4.33 um; the preferred form is 48 um, which needs the reset rebound (508 -> 477 relays). The fault return's farthest source is 1,453 um from its register: 4 legs at 405 um, so 8 -> 11 cycles on the fault return only. coll_ftc r4 moved its target path -166.03 -> +55.28 and still has 66 hops over 405 um and a dense local stripe. V (log 08:22): coll_core place stop -1,114.13 inside `u_coll.g_sring[4]`.
- Root cause: macros abutted at 4.33 um leave no routing or station sites between them, so every crossing detours and the ring and fault nets run over a millimetre unregistered.
- Fix (P): the 48 um aisle floorplan row (cores move, none re-shaped, outline unchanged) with the reset rebind; +3 registered stages on the fault return. Extra cycles are pre-approved by the owner rule; the 8 -> 11 question sits in CODEX-LOG as OWNER? and only needs confirming that fault reporting has no deadline. coll_ftc: sites for the 66 hops before any route.
- Owner: FAM-QC-COLL-R3, QC-PLAN-R12.

### Lever 9. Place-stage measurement: lockup latch -> hard-core pin is stopped as structural (QC cb / cbx 17+)

- Evidence (V, autopilot/log.txt):
  - 13:27 qwen_compute/cbx_q10__cl94a12200_h: STRUCTURAL place-setup-stop, -620.08, `u_lk_nk_u_t_2_0_n_b/q[372]$_DLATCH_N_ -> u_t20`, `hop_um=0.0 path_um=0.0 stages=1`.
  - C: cf0b's same endpoint corrected from -659.86 to -380.66 once read on the stage SDC; observer fix 9bf23638b0f landed. Whether the wave place stop uses it is not checked.
  - Correction: I listed kv3_hg -559.80 here at 13:40. C measured it as a real 1,730 um reset chain (lever 7 item 4). It is not this class.
  - R (FAM-QC-CB-R2): cbf_q00 and cbn_q01 both read exactly -380.83 on the same latch -> core-pin term: 65 ps latch + 1.5 ps wire against an ideal launch / capture offset.
- Root cause: with ideal clocks the latch opens at one edge and the core pin is constrained with its real insertion, so a zero-length path reads hundreds of ps negative. It is the same kind of artefact as the reset-recovery class that 3ed87c352a took out of the stop.
- Fix (P): exclude paths that start at a `u_lk_*` lockup latch and end on a hard-core pin from PLACE-SETUP-STOP, and judge them post-hook at CTS. This removes a false stop; it adds no gate. cbx_q10 relaunches after it.
- Owner: FLOW-OPS-1300 (stop filter, after checking 9bf23638b0f), FAM-QC-CB-R2 (CTS read on the two p1 kits).

HEAD: hd_lep0N shelf form removes the -679 late-meta path by placement (R), holds TT +22.00 after CTS (V) and passed its pre-GRT internal hold guard (C). Other open HEAD items from C: hd_ctl (lever 5 item 7), hd_mesh pin access (lever 7 item 6), hd_host_e `he_epc` M7 edge DRC awaiting a fresh placement on the LEF override, and START: tr12 with 32 separated measured clocks still fails 219 of 329, so it is not only the ideal-clock bench; p6 tr23 reads START 1 / fault 0 with a priced replay pending. North host is signed (TT +8.98, LEC 7,877 / 7,877).

Cell cap, unchanged from lever 8 of 11:35: the splitter step 1 (FLOW-STRIPBODY-1121) is still not on main, and S81 svc hi4, KV pv, S81 c1x_C / lepe_mu_C and 9 measured + 22 projected QC st_b / hc types wait on it (V 13:13: sle_st_b_v1 408,077 at floorplan).

## 2. Stop list (new or changed; earlier lists stand)

| # | Dead end | Why |
|---|---|---|
| 1 | J7 col volume routing before one fresh kit ends at 0 against `u_cf` / `u_t0` | No view is proven; none is even in a kit (V) |
| 2 | Reading the cl0045af7b STAGGER kit as a verdict on the e2 strip | xo0..3 were "kept on the line" and NOFIT at 541 to 597 um hops (V) |
| 3 | More xo stations (D3) on col without the `rq` keep | One merged flop already resets 2,210 flops in 8 stations; more stations lengthen it (R) |
| 4 | TT repair on xo reset-recovery ends or on ROM-pin ends | 552 + 427 of 980 ends; both are structural |
| 5 | Station rows from a place stop that has no `path_um` | `hop_um` is one cell hop; the START class is 1.7 to 2.8 mm |
| 6 | `OT_TAP_RESET_AFFINITY` + pitch 300 as the lepe tap fix in its present form | proof11 worse on setup, hold and spread (V); sink cap not enforced |
| 7 | `OT_GRT_CLOCK_FIRST_RES_AWARE` as a default before a real kit | TNS 17 % worse on hroot (V) |
| 8 | WREG alone on c1x_C t9 | 512k cells, -832 after TT repair (R) |
| 9 | sle_ctl +1 station on hc1 / hc3 (variant B) | 671 ends flat at -85 to -94, all cws2 port -> landing (R) |
| 10 | QC cb tap re-pick t77 / t76 | Legs 455 / 640 um against 100 / 90 for t24 / t25 on the V2 geometry (R, lane's own correction) |
| 11 | Applying or building KV on D27d2 | 920 pin / clock-site shorts (R) |
| 12 | LEF-only access fix for `qkd_ahub` ck[3..5], or a core re-export for `dsdv_idx_tx_n32` rst | M6 signal over the pins; idx_tx pin is on track at the planned y 475.188 (R) |
| 13 | Unsplit kv3_pv builds; relaunch of cbx_q10 before the stop filter | 2.8 mm path at -1,199 (V); the cbx stop is a measurement artefact (V) |
| 15 | Unchanged retry of HEAD hd_ctl a8, or of lepe proof10 | TT -164.14 through hold cells after DRC 0 (C); GRT-0116 at 2,991 overflow (C) |
| 16 | Routing coll_core at 4.33 um aisles, or coll_ftc with 66 hops over 405 | C |
| 17 | Old cb q01 cut (cldd6) | 514 over-cycle paths, skew +453.92, TT -321.75 (C) |
| 18 | KV hg / hgi relaunch with the single fallback latch group | 23 levels over 1,730 um (C) |
| 14 | Hold-buffer passes as the answer to HEAD shelf hold if pass 2 leaves it open | TNS -442 k at 89.5 % of the cap; the next step is tap grouping (`tap_grt_pre`, shelf_tg), not pass 3 |

Withdrawn from the 11:35 list:
- Line 9 ("route over-constraint as the serdes encoder fix"): wrong. enchp_j6b with the 740 ps over-constraint signed at +25.72 (R). The CRC split is not needed for the encoder.
- Line 14 ("no station rows for the start-strobe class before the path read"): the read is done; the rows are the fix (lever 3).
- Line 16 ("HEAD START change from the ideal-clock bench"): with measured clocks tr12 still fails 219 of 329 (C), so START is a real open item with HEAD-START / the token lane.

## 3. Not checked

- All C lines: taken from CODEX-LOG.md as written; none re-read on a host. My own reads predate 13:35, so kit states marked V may have moved (the STAGGER kit, lepe p10 / p11, the clock-first A/B kits, STRAP p1).
- Read by me: failure_breakdown 13:11; autopilot/log.txt place stops 06:00 to 13:28; the cfifo view LEF in srcJ7L1; the STAGGER kit place log; lepe p10 / p11 and HEAD shelf_we / shelf_tg post-hook CTS lines; the STRAP p1 seat line; the clock GRT A/B arm logs; the D27d2 proof summary; `replica_keep_wires` and the halo code in rt/current. Everything marked R is the lane's number.
- Whether the west / south edge OBS shapes of the new cfifo view are shadow or signed metal, and whether the view still covers all 17 to 31 short spots.
- The merged `rq` netlist itself, the t9 netlist and the QC strap / sle_ctl path reports: lane reads, not re-read.
- No final-GRT timing exists yet for: lepe proof10 / 11, HEAD shelf_we / shelf_tg, STRAP p1, sle_ctl variant C, kv3_hg_v1p2 (both arms), strobe proofs t18 / t16, leaf t39 lockup proof.
- kv3_sys_c exit 2 on D27d2, kv3_hg_v3 and serdes t14 paths, the other GRT-0116 col kits, the corner keep-off.
- rt snapshot 31c7ccbd1b93 was readable on the hub at about 13:22 and absent at 13:32 (also absent on epyc7); QC-PLAN-R12 named it at 13:15 as the V3 bind tools to keep. I deleted nothing. COORD / QC-PLAN-R12 should check before the V3 bind.

## 4. failure_breakdown (13:11, technical lines only)

- TAP-INSERTION qwen_compute: 3,265 taps in 33 types, 69 over 1,650 sinks; insertion max 493 (p50 269, p90 285), skew max 137.
- TAP-INSERTION s81: 2,738 taps in 47 types, 123 over 1,650; insertion max 838 (p50 461, p90 495), skew max 328.
- TAP-INSERTION s81_head: 196 taps in 9 types, 2 over; insertion max 504 (p50 465, p90 482), skew max 82.
- Kit rows by technical class: KV "CLAND ring band" 5, "over 400k cells" 2, "place error" 2; QC "place error" 1 (slw_fw_v3; R: never started, disk hold). S81 274 rows held for the plan event.

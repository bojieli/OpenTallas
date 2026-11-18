# FABLE-CLOSURE-STRATEGY 2026-11-18 05:10 PST (0510): delta on 03:20

Reviewer: FABLE-CLOSURE-STRATEGY-0510 (Fable). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK. r708: clock pin cap nominal at sign-off.
Marking: **V** = I opened the file or log this round (05:10 to 05:50 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

Signed types by family (V, plan cache 05:10): S81 42/394 (slice_station 41/46, col_h9_r2 1/60, everything else 0: leaf 75, col 215, dsdv_slice 20, svc 16, serdes 11, kv_leaf 5, bk_sel, eng, gunit, iqf, seqhost). HEAD 24/26 (open: hd_mesh, hd_lep0N). QC 24/130 (hc 7/18, fe 4/9, su 4/9, stm 2/11, fw 1/11; 0 of st_b 12, st_a 11, sc 9, cbn/cbf/cbx 18, ctl 7). KV 6/56 (0 of pv 16, hgi 11, hg 8, pc 6, hub 5).

## 0. Headline

1. **The D8e plan now in bind carries 1,140 relay rows that break the col config sequencer (V).** epyc8 `s81-colgen-1/ev/d8e_rd.json` (sha1 c24b3f8b72b8, the plan S81-DIE-R3 took at 05:08): 2,058 `relay_depth` rows; 480 `u_c*_*.addr_in` + 480 `ce_in` + 180 `u_s*.q*` = 1,140 rows on 168 col types, identical to `d8d_rd.json`. FABLE-FIX-S81-BANKLEAF measured at 04:56 (R, verilator on `ot_s81_cfg7_seq`): one stage on one ROM of the fixed-latency read loop captures the wrong word; bind and LATCHECK accept it. The S81-DIE-R3 post does not mention the alert (V, 0 matches). These rows span 420 to 640 um, just over the 405 um reach.
2. **Col is 215 of the 352 unsigned S81 types and its one routed member is ECO-sized (V).** epyc10 `col_h9_r2__t1__cl774acf45__pv11b6518d/attempt_2` sign-off: DRC 2, TT -46.87 / 131 ends, internal FF hold 5 ends at -5.07, 102 unconstrained. The worst TT path is core to core (`u_u_e*_u_w` -> `u_u_bn*`), the bank-leaf class. No relay rows are in that kit.
3. **`5_global_route.rpt` is not a TT number (V).** Leaf t11 reads -5.30 there and -288.97 at the TT gate of the same DB; t15 -17.59 / -350.29; kv_leaf t4 -4.71 / -259.65. The GRT repair session is FF-only (`tt_setup_repair.tcl` header); the TT repair on t11 moved -353.00 -> -288.97 with 404 cells. This answers the 03:20 open item: the 14 strip stops are real at TT.
4. **QC kits with clean GRT die on the measured-hold bind when pin registers sit on more than one clock (V).** `vclk_measured_hold.tcl` line 131 errors unless `ncl == 1`. Five kits: N3 sle_sc_v3 (04:4x today, CTS wns -59.25, GRT overflow 0, `clocks 3`), N1B slw_fw_v3 (CTS 0.00, `clocks 4`), sle_sc_v1__cl7479a5ec (-5.29), sle_su_l1__cl5ea486db (-33.43), slw_fe_v2__cle312294d (-88.40). The wave row for sle_sc_v3 reads `_LAYOUT_RENDER ... local_density`, so the class is hidden. No QC lane post names it.
5. **S81 leaf GRT overflow has a second class that row stride 2 does not address (V).** t25__cl431c660f (fixed by the pilot) is the south face. t24: 566 congested gcells in one window x 850-950, y 300-450, M6 6,368 + M8 11,182 of 18,328. t68: 524 gcells at x 500-550, y 200-250, M6 5,616 + M8 6,253. t25__cl55642d17: 5,122 gcells at x 200-300, y 350-450, M6 69,907 + M8 21,090. All interior, all on the horizontal layers M6 and M8 only.
6. **KV has no CTS number on the current plan family (V).** 27 KV-HG6 kits have `3_5_place_dp` as their last log (1.3 to 4.8 h old) and none has a `4_1_cts` log. D22 applied at 05:0x with the tail split on 1 of 16 PV types (R, KV-D23-REACH: `re.fullmatch("^kv3_pv")`).
7. Closed since 03:20 (R): hd_serdes sd9he signed (TT -27.16, hold 0); svc hslice signed twice (mm3r at 30 ps with r692; mm4 by r708 re-sign, TT +184.88); lep_pair vE28 signed and in HEAD r2; t25 stride-2 pilot GRT 1,022 -> 0.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Take the 1,140 ROM-loop rows out of D8e before publish; close those hops by core placement; ECO the routed col_h9_r2 as the family pilot | col 215 | S81-DIE-R3, FABLE-FIX-S81-BANKLEAF, S81-COLGEN-1 |
| 2 | S81 | D8e leaf rows (XR, core reset relays, face stride): judge the first kits at the TT gate; open a lane item for the interior M6/M8 window class | leaf 75, kv_leaf 5 | FABLE-FIX-S81-STRIP, S81-DIE-R3 |
| 3 | QC | Measured-hold bind per clock root instead of an error at `ncl != 1` | sc 9, su 5, fe 5, fw 10 as an upper bound; 5 kits proven | WAVE-FLOW-R2, QC-TYPES-R3 |
| 4 | KV | D23 with `kv3_pv.*`, bands sized by `band_capacity`, reset hops; read hg/hgi at CTS now | pv 16; first evidence for hg/hgi 19 | FABLE-FIX-KV-HG |
| 5 | QC | N4 then N4.1 on one measured st_a kit; cbn/cbf/cbx place errors | st_a 11; cb 18 | QC-PLAN-R3, FABLE-FIX-QC-N, QC-TYPES-R3 |
| 6 | S81 | Serdes: H18 is the first rail-clean kit; the die pad-clock trunk to the moved `io_pma_rck` pin has no plan field | serdes 11 | FABLE-FIX-S81-SERDES2, S81-DIE-R3 |
| 7 | HEAD | hd_mesh: balance the 5 short taps before hold padding; first hd_lep0N build on r2 | 2 types, then the die | FABLE-DIE-HEAD, FABLE-FIX-HEAD-LEP0N |
| 8 | S81 | svc mergex at 30 ps + r692 (the hslice recipe); r708 re-sign of mergex_mm3b | 1 core, then svc 16 | FABLE-FIX-S81-SVC2, NOMCAP-1118 |

### Lever 1. S81 col: remove the ROM-loop relay rows, close col_h9_r2 by ECO

**Evidence (V).** `d8e_rd.json` rows by class: ROM `addr_in` 480 and `ce_in` 480 (168 types, 420 to 640 um), `u_s*.q*` 180 (144 types, 420 to 692 um), `u_t*.c*` 288, `u_n*.fi` 180, `u_n*.a` 96, `u_e*.xb_data` 72, y_cc / y_x links 126 (920 to 1,244 um). The die bind on this plan is running on epyc8 (`bind.py elab ... --strict`). Routed col_h9_r2 numbers as in headline 2; its `config.mk` has `OT_HOLD_FF_MARGIN = 0` and the SDC hold uncertainty is 25 ps.

**Root cause.** The relay generator treats every hop over 405 um as a schedulable link. The cfg7 sequencer loop is not a link: its read latency is fixed in RTL. The frame tracer models the sequencer as a 0-edge pass-through, so the only signal is `RELAY_DEPTH_UNSCHEDULED`, which D8e plans to name in the ack record and pass.

**Fix.**
1. S81-DIE-R3: do not publish D8e with the 1,140 rows. Filter `inst ~ u_c<b>_<k>` with port `addr_in` / `ce_in` and `inst ~ u_s<n>` with port `q<k>` out of `relay_depth` and rebind as the delta; the other 918 rows stay only where the tracer can schedule them (R: BANKLEAF is adding that).
2. FABLE-FIX-S81-BANKLEAF: the ROM hops are 15 to 235 um over reach, so move the ROM cores toward the sequencer (0 cycles), as already started. Deliver as one col row set for all 168 types.
3. S81-TYPES-R3 + CAPSKEW-ECO: col_h9_r2 pv11b6518d is 4.87 ps and 5 hold ends from the gate. Name the 2 DRCs and the 102 unconstrained ends, then run the capture-skew / hold-pad ECO on the routed DB (the sd9he form: 15 flops, 113 pads). A signed r2 proves the family without relay rows; 50 placed col kits are waiting on the same answer.
4. P: the macro-to-macro worst path means the r2 TT miss is set by core pin timing plus distance, so core placement also closes TT; do not add a cycle there before the placement rows are measured.

### Lever 2. S81 leaf: D8e rows, TT-gate reads, interior congestion class

**Evidence (V).** TT gate estimate against the FF-session report, same DB:

| type | CTS wns | TT gate | `5_global_route.rpt` |
|---|---|---|---|
| t11 | -304.64 | -288.97 | -5.30 |
| t15 | -401.81 | -350.29 | -17.59 |
| t30 | -283.77 | -315.26 | -29.06 |
| t44 | -160.55 | -288.41 | -11.32 |
| t54 | -575.04 | -470.52 | -30.37 |
| t55 | -384.19 | -449.57 | -30.27 |
| kv_leaf t4 | -273.55 | -259.65 | -4.71 |
| kv_leaf t5 | -403.50 | -297.36 | -34.49 |
| t50 | -684.45 | -445.36 | -94.32 |
| t27 | -610.56 | -515.04 | -202.02 |
| t38 | -488.12 | -462.95 | -248.26 |
| t16 | -734.41 | -733.84 | -384.76 |
| t53 | -1,085.45 | -891.61 | -666.38 |

All these kits: `VERILOG_DEFINES = -DSYNTHESIS` (no XR), plan before D8e. GRT overflow rows: t24 18,328, t25__cl55642d17 99,680 (still running), t68 15,143, t40__clf8bbdae1 10,497, t4 2,283, t41 1,620, t25__cl431c660f 1,022, t29 547, t35 4 (GRT-0232). Seven more leaf kits stop at place on `OT_VPW_BANK distance exceeds 100um` (t1 t10 t13 t14 t75 class); kv_leaf t1 and t3 on PLACE-HPWL 1.48 x and 1.32 x.

**Root cause.** Unchanged from 03:20 for timing (VS core clk-to-`x_wa` 383 ps, reset relay far from the core pin). For the interior class: one window of 50 to 150 um carrying only horizontal-layer overflow is a bundle crossing one channel, not pin access. P: the FIRM bank placement pulls the write bus of one VPW bank through a single gap between hard cores. Not shown; the stage DBs were cleaned.

**Fix.**
1. S81-DIE-R3: D8e keeps XR 16/16, the 1,967 reset relay sites and `face_flop_ns_types` stride 2 (R, all in). These do not depend on the col rows; if the col delta costs a rebind, publish the leaf rows first.
2. FABLE-FIX-S81-STRIP: read the first XR kits at `postcts_gate_tt.json` and `tt_setup_repair_grt.log` only. Expected (P): the `wdo_q` class gains one cycle of 833 ps against misses of 260 to 734, so t16 and t53 (-734, -892) may keep a residue; take their class table first.
3. FABLE-FIX-S81-STRIP: keep `5_1_grt.odb` on t24, t68, t25__cl55642d17 and t40 and image the window. If it is a core gap, the fix is a bank or core move in the type rows, not stride.
4. The `OT_VPW_BANK distance exceeds 100um` stop is a placement check on a path that XR re-times; with XR in, it should be measured again before any site work.

### Lever 3. QC measured-hold bind with forwarded clocks

**Evidence (V).** epyc9 `s29q103S4Q9N3/items/sle_sc_v3/attempt_2`, `5_1_grt.log` line 727 after `OT_HOLD_BUDGET added 0 ... hold_ws -21.86 ... OK`: `OT_VCLK_MEASURED_HOLD: pin-register mean unavailable (samples 8205 missing 0 clocks 3)`. `vclk_measured_hold.tcl`: `ot_vmh_pinreg_mean` maps a clock to its root only when `fwd_roots` is non-empty and `ot_cf_root` exists; the bind then requires exactly one clock name. The col sign-off record shows the working form: `samples 1496 missing 0 clocks 1 forwarded_excluded 8`.

**Root cause.** In these QC kits the pin registers are clocked by forwarded cland clocks that are not in the kit's forwarded-root table, so they count as separate clocks and the step aborts. All samples have arrivals (`missing 0`); only the clock count fails.

**Fix (WAVE-FLOW-R2 with QC-TYPES-R3).** Bind the IO virtual clock from the pin registers of the primary clock and exclude forwarded-clock registers, as sign-off already does (`forwarded_excluded`), or fill `fwd_roots` from the plan cland rows at gen. Then relaunch the five kits from GRT; three of them are at CTS wns 0.00, -5.29 and -33.43. The same error stopped HEAD sd9c on 11-16 (R), so the fix is die-agnostic.

### Lever 4. KV D23

**Evidence.** V: 4 PV kits stop at `OT_CLAND no legal nonoverlapping row/site in reserved band` (pv_v2 and pv_v4 `u_cland_raw_fs_o_pvw...`, pv_v6 `..._valid_d1_0`, pv_v2n `u_cland_fstart_ft26_o`); hub_C 773,818 and hub_Wo 406,241 cells; no KV kit past placement. R: D22 gate of record passed (strict bind 0 errors, R8 recheck 0, LATCHECK 2,404 / 2,404); not in D22: rider (29 routed hops over 405 um), reset relay rule, `u_d` pipes, pc taps, hub splits; hub_Wi shell 299,999 cells with 14 hard `qkd_hr` masters; hub_C split gate A failed 16 EMIT (reset_net on ring rows, `landing_ring_wreg`), gate B running, 1 collision with a reserved die clock rect open.

**Fix (FABLE-FIX-KV-HG).**
1. D23 in one event: `types ["kv3_pv.*"]`, writer-start and raw-reset bands grown from `band_capacity.py measure` on all 16 PV types, rider, reset hops, hub_Wi rows. hub_C follows when gate B and the clock-rect collision are clean; do not hold D23 for it.
2. hg / hgi / pc / hroot / io_cor (25 kits placed on HG6) are not touched by the PV rows; under r710 they survive the apply. Their first CTS tap-balance and wns lines are the first KV evidence; read them before composing D24.
3. D24 (lighter rings) should be decided from the 186,960 ring cells in the hub_Wi shell and a measured ring kit, not before.

### Lever 5. QC N4 / N4.1 and the cb types

**Evidence (R unless marked).** N4 chain running (group A stations, coll_core 43 taps, clk_t115 split, relay_sites for 11 st_a types). N4.1 by FABLE-FIX-QC-N: u_btab bank moves tested (0 halo hits, lane latency equal), rs_s per-row copies, nb_od / nb_oc station (+1 on x_fe_o), cland forwarded-clock insertion target 485 instead of 419 ps for three masters with setup over 80 ps; one kit to routed sign-off, first CTS in about 3 h. V: cbx_q10__cl94a12200 stops at `global_place.tcl ... can't read "nka_blk": no such variable`; cbf_q01_s2 and cbn_q11__cl5cc92dfe at `GRTM mode edge_outline`; st_b refused at 486,894 to 501,829 cells; tt_ctlm TT gate -258.47.

**Fix.**
1. QC-PLAN-R3: apply N4 as composed. FABLE-FIX-QC-N: no N4.1 rows before the single kit is read at CTS.
2. QC-TYPES-R3: the `nka_blk` Tcl error is an unset variable in the generated `global_place.tcl` (V: the error line; P: a gen branch for the nk_a hard-core form that this type does not take). Fix in gen; P: it stops every cb type built with that core form, so check cbn / cbf kits for the same line.
3. The +66 ps forwarded-clock target is a contract change on the sender; check the three cland masters in the signed fe / hc kits before it becomes a gen default.
4. tt_ctlm still needs the RTL stage (flat `u_core`, 253 ps wire + 700 ps logic, R).

### Lever 6. S81 serdes

**Evidence (R, SERDES2 / DIE-R3).** H18 (H17 recipe + `OT_S81_LPL_CHUNK`, PHY row cut): rail check 6,726 rows 0 bad (H17: 2,046 of 6,664 bad), in placement at 04:41. H17 with nominal clock cap: TT -69.66, internal hold -15.88 / 20 ends. D8e: u_cmem read register at 0 cycles, TAP-GROUP-CAP-1 back (cap 1,700; t13 clk_t42 split in 4), `io_pma_rck` pin moved x 332.704 -> 1,448.032 on 5 shore types (insertion 1,695 against 2,217 ps). Open: the die pad-clock trunk (about 1,115 um, 3 hops) has no plan schema field, and `serdes_shore_delta.py` would move the pin back.

**Fix.**
1. S81-DIE-R3: add the trunk as explicit die clock rows (three stations <= 405 um on M8/M9) in the clock event, and make `serdes_shore_delta.py` read the pin from the plan. Without it the type closes against a pin the die cannot feed.
2. FABLE-FIX-S81-SERDES2: sign H18 under r708 if routed TT >= -42; otherwise the sd9he ECO form (capture skew + hold pads) on the routed DB. The six non-shore types wait for the H18 result, not for a new H form.

### Lever 7. HEAD

**Evidence (R, FABLE-DIE-HEAD 04:18).** hd_mesh mesh_w1 with the credit counter on one tap: TT at CTS -0.96 (was -50.56). Hold before repair: cross-tap 10,190 ends at -185.30, same-tap 1,408 at -84.24; five taps short of the 450 ps target (clk_t45 322, clk_t54 330, clk 332, clk_t42 360, clk_t43 384). The earlier attempt lost TT -49.56 -> -68.34 after 37,912 hold cells. V: no hd_lep0N kit directory exists on epyc9 / epyc10 / intel1 under event `..._r2` at 05:45; hd_tile on NF15f a4 reads TT gate -354.59 (it is signed from nf15c_tp2_land1).

**Fix.**
1. FABLE-DIE-HEAD: the 128 ps tap spread is the hold demand. Fix the five short taps (delay cells at the tap root, or the tap group rule) and re-run CTS before pre-GRT padding; padding 10 k ends by 185 ps repeats the 37,912-cell run.
2. FABLE-FIX-HEAD-LEP0N: first r2 synth, band and CTS read; nothing technical can be said before it.
3. M8 grant: 1,723 die-track conflicts on signed types (hd_tile 1,069) stay a die clock leg move (R). It blocks die assembly, not the type count.

### Lever 8. S81 svc mergex

**Evidence (R).** hslice: 15 ps finished at FF r2r -0.00 (not signed), 30 ps + r692 signed (+12.14 routed), 50 ps failed on utilisation. mergex mm6 in GRT, mm3r and mm15r in CTS hold repair; mergex_mm3b routed r2r -6.93, r708 re-sign running (hslice_mm3b re-sign: FF -2.85, not signed).

**Fix.** FABLE-FIX-S81-SVC2: mergex_mm3r is the form of record; stop mm15r (hslice proved 15 ps leaves no room). If the mm3b re-sign lands within 3 ps as hslice_mm3b did, close it with the r583 internal hold ECO instead of waiting for the rebuild.

## 2. Die floorplan or type-internal, per die

| die | unsigned families | where the blocker sits | one die-level change |
|---|---|---|---|
| S81 | leaf 75 + kv_leaf 5 | Type structure, fixed by die-plan rows (XR stage, reset relay sites, face stride). A second, type-internal class: interior M6/M8 windows on 4 types | D8e |
| S81 | col 215 | Type-internal and close (routed -46.87, 5 hold ends). Held by plan rows: relay hops over 405 um and bank-leaf core distance | D8e col delta without the ROM-loop rows, with core moves |
| S81 | serdes 11 | Type-internal (rck tree, PG rails) plus one die item: pad-clock trunk to the moved pin | D8e rows + die clock rows |
| S81 | svc 16, dsdv_slice 20, slice_station 5, singles 5 | Type-internal (mergex core hold; kit preflight / `edge_outline`; slice_station t6 TT gate -229). Not opened this round beyond the wave rows | none |
| HEAD | hd_mesh | Type-internal (tap balance, cross-tap hold) | none |
| HEAD | hd_lep0N | Die plan (bands, pair views, tap offsets): delivered in r2, unbuilt | r2, already applied |
| QC | sc, su, fe, fw (29 unsigned) | Flow: measured-hold bind; no floorplan cause found | none; lever 3 |
| QC | st_a 11 | Die plan rows inside the type (stations, tail copies, bank sites) | N4 + N4.1 |
| QC | st_b 12, hc 11 | Type size (350 to 502 k cells) and routed hold; not floorplan | none |
| QC | cbn / cbf / cbx 18, ctl 7, tt_ctlm | Generator and RTL (place Tcl error, `edge_outline`, missing stage) | none |
| KV | pv 16, pc 6 | Die plan rows (tail split, bands, taps) | D23 |
| KV | hub 5 | Partition size: split on signed ring and host masters | D23 (Wi), later hub_C |
| KV | hg 8, hgi 11, others 4 | Unknown: no CTS number exists | none known |

No die has a die-floorplan routing problem: die GRT overflow is 0 on S81 (M4 to M7 use under 5 %), QC (worst cut 0.237) and HEAD combo (0.37 %) (R, FABLE-DIE-* 11-17). The die-level open items are clock structure (S81 K table from B6gsh, 93,626 unreserved clock cell sites, 21 legs over 405 um; HEAD M8 grant) and they gate die STA, not type sign-off.

Answer: S81 yes, one event. D8e plus a corrected col delta reaches 306 of the 352 unsigned types (leaf 80, col 215, serdes 11). KV yes for 22 of 50 (D23: pv, pc), unknown for hg / hgi. QC no: N4 covers 11 of 106; the widest single change is the flow fix of lever 3. HEAD no: one type each.

## 3. Stop list (the 03:20 list stands, plus these)

1. Do not publish D8e with `relay_depth` rows on `u_c*_*.addr_in / ce_in` or `u_s*.q*`. Do not record `RELAY_DEPTH_UNSCHEDULED` as an accepted finding for those rows.
2. Do not read `5_global_route.rpt` / `6_finish.rpt` wns as the TT result; it is the FF session. TT is `postcts_gate_tt.json`, `tt_setup_repair*.log` and sign-off.
3. No relaunch of pre-D8e leaf kits; no SETUP_TRIAGE threshold change (the 8 kits that look closed at GRT are at -260 to -470 TT).
4. No row stride as the answer to t24 / t68 / t25__cl55642d17 / t40; no S81-wide stride default (fires on 387 of 395 types, R).
5. QC: no relaunch of sc / su / fe / fw kits with forwarded-clock pin registers before the bind fix; no N4.1 plan rows before its one kit is measured.
6. KV: no judgement of PV on HG6 or D22 kits (split covers 1 type); no D24 compose before one KV CTS number; no hold of D23 for hub_C.
7. hd_mesh: no hold padding against a 128 ps tap spread.
8. svc: no 15 ps and no 50 ps margin builds.
9. Serdes: no `serdes_shore_delta.py` rerun on D8e; no export of H17 (rail defect).

## 4. Not checked

- The D8e bind output itself (still running); whether S81-DIE-R3 acted on the BANKLEAF alert after 05:08.
- The BANKLEAF verilator result, the 515 bank-leaf paths and the core-move rows (R).
- What the interior congestion windows contain (no stage DB; the cause in lever 2 is a proposal).
- Whether the five QC kits pass sign-off once the bind is fixed; how many of the 29 sc / su / fe / fw types carry forwarded-clock pin registers.
- Any KV timing. Any hd_lep0N r2 result. H18 beyond the 04:41 post. mergex results.
- dsdv_slice (20), svc shell types and bk_sel / eng / gunit / iqf / seqhost: wave rows only.
- QC N4 bind result; the cland +66 ps effect on port hold.
- Die STA on the real clock for S81 and HEAD (0 measured hold pairs, R).

---

# FABLE-CLOSURE-STRATEGY 2026-11-18 03:20 PST (0320): delta on 23:20

Reviewer: FABLE-CLOSURE-STRATEGY-0320 (Fable). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round (03:14 to 03:40 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.
All lanes were stopped 00:30 to 03:10; most "running" items below are builds that kept going with no reader.

## 0. Headline

1. **S81 strip leaves: 14 of the first 21 route verdicts are a pre-route setup stop of -244 to -734 ps, and it is structure, not settings (V).** Worst classes in the kits: VS core `x_wa` -> `u_vp_g_wr1_u_w.wdo_q` (t16 -715 / 1,025 ends; t50 -684 at CTS), and reset into hard-core `rst_n` pins (`u_vsw/rst_n` -298 to -425 on t15 t26 t38 t50). The XR stage that was decided for this family on 11-17 is not in any of these kits (t50: 0 `ot_s81sl_xr` instances, `VERILOG_DEFINES = -DSYNTHESIS`). The other 7 verdicts are GRT congestion (t25 class).
2. **The GRT optimism is a serdes rck-tree problem on both dies, not a fleet problem (V).** hd_serdes, three forms routed overnight: sd9h GRT TT -0.24 -> routed -45.34; sd9pa -10.89 -> -49.62; sd9pb2 -0.89 -> -92.27. Over 85 other kits with both a `grt_policy.json` and a later `signoff.json` (epyc7/9/10), TT moves mostly within +-25 ps and FF hold within +-10 ps; the bad outliers are QC sle_fe_v3 (+39 -> -29), S81 col_h9_r2 (-19 -> -47) and QC slw_hc1 (-14 -> -41).
3. **hd_serdes sd9h is 3.3 ps from the gate (V):** DRC 0, TT -45.34 / 119 ends, FF hold -31.02 / 169 ends. sd9pa: DRC 0, TT -49.62 / 8 ends. Both are ECO-sized on setup.
4. **lep_pair vE28 is 12 flops from sign-off (V):** DRC 0, TT -0.66, internal FF hold -9.7 on 12 ends (the other 2,739 hold ends start at ports). No ECO has been started on it. It is the only thing hd_lep0N waits for.
5. **KV D22s failed its strict bind at 23:58 (V); this is the third D22 plan.** `R8_STRAP_PAD kv3_pc_v1__cl7f648944 slg.vreq: pad 18 > strap capacity 15`, `TYPE_SPLIT` 12 instances -> 7 variants, `EMIT clock landing`; R8 recheck 64 unequal groups, 2 inversions. Rider gate3: 30 `R8_STALE`, LATCHECK 2,404 / 2,404. Meanwhile the wave ran PV kits on KV-HG6 with no tail copies (pv_v6: 0 `ot_dp_dly_keep`), and 4 of them tripped the CLAND band breaker.
6. **The svc hold misses are not ECO-sized (R, SVC2 03:14).** hslice_mm4 ECO failed (1,092 negative ends, incremental route failed); mergex_mm3b refused (1,567 ends); hslice_mm7 at 50 ps died at CTS (53,294 hold buffers, utilisation over 100 %). My 23:20 lever 4 item 1 was wrong for these two cores. V: hslice_mm6 is in detailed route (471 violations in the current iteration), mergex_mm6 in CTS hold repair at 30.9 k buffers.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Strip leaf: XR stage on the VS -> VPW write, registered reset at the core `rst_n` pins, in one plan/RTL event | 14 stopped strip types now; the same class sits in all 75 leaves | FABLE-FIX-S81-STRIP, S81-DIE-R3 |
| 2 | HEAD | lep_pair vE28 hold ECO (12 ends) -> sign -> view pack -> hd_lep0N | hd_lep0N, then the HEAD die | FABLE-FIX-HEAD-LEP0N, HEAD-PLAN-R4 |
| 3 | HEAD, S81 | Serdes rck: close sd9h / sd9pa by post-route clock ECO; size rck pads on extracted arrivals; never decide these types at GRT | hd_serdes; 11 S81 serdes types | FABLE-FIX-HEAD-SD9F, FABLE-FIX-S81-SERDES2, CAPSKEW-ECO |
| 4 | KV | D22: fix the `slg.vreq` pad (18 > 15) before a fourth bind; regenerate the rider R8 table from that bind; PV bands by `band_capacity`; hold PV kits | PV 16, pc 6, the die event | FABLE-FIX-KV-HG, KV-R3 |
| 5 | S81 | Strip south-face pin-row congestion (t25 class, 7 types) and col relay reach, as generator rules | 7 strip types; col 216 | FABLE-FIX-S81-STRIP, S81-TYPES-R3 |
| 6 | QC | N4 with flt_bank stations + sited tail copies; own tt_ctlm | st_a 11 types; tt_ctlm types | QC-PLAN-R3, TAIL-REPL |
| 7 | S81 | svc hslice / mergex: sign mm6 if it passes; if not, cut the hold demand at its source instead of adding buffers | 2 cores, then the svc shell | FABLE-FIX-S81-SVC2 |
| 8 | KV | Hub types over the size OpenROAD closes: split hub_C and hub_Wi on signed ring cores; waive hub_Wo | 3 hub types | KV-HUBWO-SPLIT rows, FABLE-FIX-KV-HG |

### Lever 1. S81 strip leaf: the stops are two structural paths

**Evidence (V).**
- `kit_wave_stages.tsv`, current plan, strip route rows: 14 `FAIL_POSTCTS SETUP_TRIAGE` (iqf__t1 -537, kv_leaf t4 -260, t11 -289, t15 -350, t16 -734, t26 -483, t27 -515, t30 -315, t38 -463, t44 -288, t50 -445, t54 -471, t55 -450; last one t55 at 02:55), 7 GRT congestion (t25 t29 t35 t4 t40 t41 t68), t51 DPL-0033.
- epyc8 `.../items/ot_s81sl_leaf__t50/attempt_7`, `4_cts_final.rpt`: wns -684.45, tns -336,321. Path `u_bound.u_u_vs/clk` -> `x_wa[0]` leaves the core at 401.7 ps, then 38 cells (31 buffers, 7 gates) in three long hops (401 -> 911, 951 -> 1,288, 1,351 -> 1,576) to `wdo_q[0][82]`, arrival 1,603 against 919 required.
- Same kit: `OT_VPW_BANK placed 317 FFs FIRM, nearest-bank max 11.328um`. So the bank placement works and does not close the path: the capture flops sit at the bank, the source core and the arbiter logic do not.
- Same kit: asynchronous group, `u_lpad_leafdn_i0.q[0]` -> 22 buffers -> recovery at a `_DFF_PN0_`, -41.42.
- `tt_setup_repair_grt.log` last line per kit: t16 -714.4 `wdo_q`; t15 -297.8, t26 -329.4, t38 -420.2, t50 -424.7 all `u_*vsw/rst_n`; kv_leaf t4 -243.4 `u_vp_g_ln_7_u_l/rst_n`; t55 -291.1 `g_u_lf4_u_vp_cf.native_memory`. t16 then crashes: `[ERROR RSZ-0074] Failed to build tree from global routes`.
- All these kits: `OT_HOLD_FF_MARGIN = 0` (plan 30c40fae, before the D8d key).

**Root cause.** The VS core spends 383 ps clk-to-`x_wa` inside the core (R, 11-16 review; V 401.7 at the pin). The five-writer arbiter then has about 430 ps for 400 to 1,000 um of wire plus 7 gates. No placement can close that. The reset class is the same shape: a relay flop far from the core pin it drives. The repair cannot help either path and spends its time (and crashes) trying.

**Fix.**
1. S81-DIE-R3 + FABLE-FIX-S81-STRIP: put the XR form (r432 `ot_s81sl_xr`, +1 cycle on `x_w` and `x_wd` together, pre-approved) into the next S81 event for every leaf type, with bank placement kept. I did not find XR in D8d (P: it is not there; the 03:13 D8d result does not name it). If D8d is already bound, make it D8e, not a per-type patch.
2. Reset: one `ot_dp_rrelay` stage sited within 50 um of each hard-core `rst_n` pin (vsw, vp_g_ln), from the existing relay-site rows; the 64-cycle reset hold makes the cycle free.
3. FABLE-FIX-S81-STRIP: class table of the 14 kits from `4_cts_final.rpt` (not from the gate estimate) before anything is relaunched. t15 shows kit GRT -17.6 against an estimate of -350 (R); find what the estimate adds, but that question does not change t16 / t50, which are real at CTS.
4. WAVE-FLOW-R2: `tt_setup_repair.tcl` must catch RSZ-0074 and keep the pre-repair DB; today the crash hides the real number.

### Lever 2. HEAD: sign lep_pair vE28 by ECO

**Evidence (V).** epyc9 `head-lep0n-opus/lep_ve28/kit/ot_s81hd_lep_pair_kit/signoff/signoff.json` (23:27): NOT SIGNED, DRC 0, antenna and PG PASS, `setup_tt -0.66 / 1`, `hold_ff -177.0 / 2751` of which `std_min_start.port 2739`, `nonport_n 12`, `nonport_wns -9.7`. TT insertion 517 to 528 ps; pair skew min 87.3. No ECO directory exists in the kit. hd_lep0N p2 (diagnostic, old windows) is at CTS wns -379.62, tns -97,009: not a verdict.

**Fix.**
1. FABLE-FIX-HEAD-LEP0N: `hold_eco_internal_run.py` (r583) with the top-layer route fix b6e97307 on the routed vE28 DB now; hei3 closed 7 -> 0 pads in three rounds the same way. Sign, export.
2. HEAD-PLAN-R4: one pack = vE28 views (`bb.v` KCRED 28) + plan_grown2 bands + related-pair windows; take the four pair tap offsets from the signed core's `clock_contract.json` (insertion about 527, not the 450 target).
3. M8 grant (R): track-level lock 4,321 -> 3,178; hd_tile (signed) 1,069. Types do not re-sign; if the shape test shows real overlap the die clock legs move. Still open with FABLE-DIE-HEAD.
4. hd_mesh `mesh_w1` (related windows) is in CTS (V 03:20); read its cross-tap hold class against 11,732 ends / -125.74.

### Lever 3. Serdes rck trees: decide on extraction, close by clock ECO

**Evidence.**
- S81 H17 (R census; V the eight census files exist, epyc9 `fable-fix-s81-serdes2/drtx/census/`): GRT -27.17 / +0.12, routed -117.47 / -55.85; data nets median -14 ps; rck sinks spread 1,848 to 2,051 routed; lpl_r.rc -> o 144 ps, lpl_2_w.wc -> b 179 ps.
- HEAD hd_serdes (V, epyc10 `fable-fix-head-sd9h/<form>/hd_serdes/{grt_policy.json,signoff_fable/signoff.json}`):

| form | GRT TT / ends | routed TT / ends | GRT FF hold | routed FF hold / ends | DRC |
|---|---|---|---|---|---|
| sd9h (PW16 + PW8) | -0.24 / 1 | -45.34 / 119 | -24.34 | -31.02 / 169 | 0 |
| sd9pa (PPCYC) | -10.89 / 1 | -49.62 / 8 | -17.77 | -33.68 / 432 | 0 |
| sd9pb2 (SPCYC) | -0.89 / 2 | -92.27 / 228 | -35.12 | -46.66 / 107 | 0 |
| sd9pc2 (both) | +0.67 / 0 | none: `DRT-0255` | -21.12 | none | - |

- sd9h vclk reference latency 488.8 at GRT, 446.4 routed: the tree is 42 ps faster under extraction, as on H17 (74 to 94).
- Fleet (V, 85 kit pairs): the effect is small elsewhere. HEAD types (insertion 478 to 521) move TT by -9 to +11 typically; S81 slice_station (280 to 350) by -44 to +90; QC by -68 to +61.

**Root cause.** The rck balance pads are sized on placement RC and confirmed on GRT RC. A 2 ns, 63-stage tree turns a few percent of clock RC error into 50 to 180 ps between branches (R, SERDES2). Ordinary CTS trees of 300 to 520 ps do not show it.

**Fix.**
1. FABLE-FIX-HEAD-SD9F: sd9h needs 3.3 ps on 119 ends; sd9pa needs 7.6 ps on 8 ends. Run `capskew_eco_run.py` on both routed DBs, then the internal hold ECO. The 100-pad hold limit will refuse 169 / 432 ends: split by rck branch and run two rounds rather than raise the limit blind. First to pass signs. sd9pb2 is out.
2. I withdraw my 23:20 line "stop PPCYC/SPCYC once sd9h shows TT >= -42 at GRT". No rck-tree type is decided at GRT.
3. CAPSKEW-ECO + WAVE-FLOW-R2: for kits with `OT_S81_RCK_BALANCE` (S81 serdes 11, hd_serdes), make the flow: route -> extract -> rck pad re-size on SPEF sink arrivals -> incremental route -> hold ECO. The GRT policy stays as a triage only.
4. FABLE-FIX-S81-SERDES2 / S81-DIE-R3 (R, agreed): cmem read register, centre-root trunk, t42 four-tap split in the S81 event; pilot t13 only after that.
5. sd9pc2: `DRT-0255` is the M6 pair-row class; hd_serdes kits need the `pg_row_guides.tcl` hook (r598) that S81 serdes has. Do not rerun unchanged.
6. Triage margin elsewhere (P): a type with GRT TT between -42 and +30 is not safe; plan the CAPSKEW ECO for it rather than a rebuild (col_h9_r2, slw_hc1, sle_fe_v3 are this case).

### Lever 4. KV D22

**Evidence (V).** epyc7 `kv-hg-opus/d22s/gate/gate.out` (07:58Z): PRE PASS, G0 PASS (0 errors, 2,403 warnings), `RC_BIND 1` with 3 errors as in headline 5, `RC_R8CHECK 1`, LATCHECK not run (no `*_bound_top.sv`). `kv-pv-rider/gate3/gate.out`: `BIND_ERRORS 30 {'R8_STALE': 30}` (`pvw_0__u_T0Q0_45_r0.b as-built 2 bound 9, table ... bound 5`), LATCHECK PASS. Wave 01:37 to 01:48: `OT_CLAND no legal nonoverlapping row/site in reserved band` for `u_cland_fstart_ft0_o` (pv_v6), `ft26_o` (pv_v2, pv_v2n), `u_cland_raw_fs_o_pvw...` (pv_v4, literal-local-reset). Sited proof epyc9 `kv-hg-opus-site/proof/kv3_pv_v12`: placed; `OT_TAIL_SITE copies 7009 of 7040 sited ... max_hop 441.3 um over_380 1205 core_crossing 0 in_halo 0`; no timing number yet.

**Root cause.** The pc `slg.vreq` pad needs depth 18 and the R8 strap carries 15, so instances of one type bind differently and the emit inventory changes. The rider's R8 table was built from an older bind. The PV writer-start bands are sized for the pre-split flop count.

**Fix (FABLE-FIX-KV-HG).**
1. One plan station on `slg.vreq` for pc_EN / pc_ES so no pad exceeds 15 (or a 5-bit strap for that bus only). Then the bind; G0 cannot see this class, so do not compose again before it.
2. Rebuild the rider R8 table from the passing bind; R8_STALE is a stale input, not a design error.
3. Run `band_capacity.py measure` (r681, all dies) on the 16 PV types and grow the writer-start and raw-reset bands in the same plan (HEAD needed 11 rects).
4. Hold all `^kv3_pv` items on KV-HG6: they have no tail copies, so their timing is the unsplit -1,197 class and 4 already fail the band.
5. Sited proof: read CTS reg-to-core on pv_v12. The 1,205 copies over 380 um need one more stage (K+1) in D22; decide that from the CTS number, not before.

### Lever 5. S81 generator rules: face pin row and relay reach

**Evidence.** Strip (R, STRIP 03:4x; V the 7 GRT rows): t25 has 595 `leafdn_i0` input regs in 12 full rows at y 4.32 to 7.29 on 598 pins in 124 um; 101 congested gcells at x 360 to 480, y 0 to 7; M6 568 + M8 347. Pilot `t25_ns2` (row stride 2) is running. Col (R, S81-TYPES-R3 23:21): poly relay hops 446 to 746 um in every col family (limit 405); col_h9_r0_p2 stops on 2 unfitted groups (252 / 206 um). 22 direct wires of 412 to 640 um (R, COORD brief; I found no generator post). Col after the marker fix (V): 10 rows running, none past place yet, 87 old place FAIL rows; col_h9_r2 reached sign-off with DRC 2, TT -46.87, hold_ff -62.46, `unconstrained` FAIL.

**Fix.**
1. FABLE-FIX-S81-STRIP: if `t25_ns2` gives GRT 0, make the stride a generator default from pins/um on the face window (no per-type plan rows), and apply to the 6 other types in one relaunch. t29 is the landing-ring variant (`cland_strip_rows`).
2. S81-TYPES-R3: gate `OT_RELAY_POLY` max hop over 405 um at generation, and insert stations so every poly hop is <= 405 um (+1 cycle each). The 22 direct wires get the same rule. Otherwise all 216 col types pass place and stop at CTS.
3. col_h9_r2: name the 2 DRCs and the unconstrained endpoints first; the 4.9 ps of TT is a CAPSKEW case.

### Lever 6. QC N4

**Evidence.** (R, TAIL-REPL 23:19; V the keep kit exists on epyc9) st_a split + keep + sited: CTS wns -901.4 -> -580.7, tns -160,939 -> -123,092; `rs_n_c_p` gone; new worst `u_r2.flt_bank_o -> u_r0.flt_bank_i` (819 to 1,000 um, R). (R, QC-PLAN-R3 03:15) N4: flt_bank 2 + 2 stations need `claude/qc-intra-stations-1118` (proof bind running, READY about 05:00); coll_core 43 taps + t115 split composing; tt_ctlm stage unowned.

**Fix.**
1. QC-PLAN-R3: N4 carries tail split + keep + sites, flt_bank stations and the tap rows in one event, as planned. Before the apply, place ONE st_a kit to CTS from the N4 bind and read wns; the acceptance is better than -250 with no path over 380 um unregistered.
2. COORD: tt_ctlm (31 cells in `u_core`, about 253 ps wire + 700 ps logic, R) needs an RTL stage and has no lane; without it those types fail N4 as they failed N3.
3. Routed QC rows already inside TT (V: sle_st_b_v1 +7.0 and -32.3, slw_st_b_v1 -25.4 and +9.5, slw_stm_v3 -4.8, slw_hc1 -41.1): their open item is internal hold; give them the r692 hold repair and the r583 ECO, not a rebuild.

### Lever 7. S81 svc hslice / mergex

**Evidence.** Headline 6. mergex_mm6 CTS hold repair: 36,993 endpoints under margin (R), 30.9 k buffers at +10.6 % area and still running (V).

**Root cause (P).** Tens of thousands of short paths cannot be a skew accident; the cores are built with a 30 ps margin on top of the 25 ps hold uncertainty in the SDC, so the repair is asked for 55 ps on every zero-logic stage.

**Fix (FABLE-FIX-S81-SVC2).**
1. Read hslice_mm6 at route end; sign it if DRC 0 and internal hold >= 0.
2. If mm6 fails: do not go to 50 ps (mm7 proved it does not fit). Check whether sign-off measures internal hold with the 25 ps uncertainty; if it does, build at margin 0 to 10 with r692 (worst + 1 ps floor, bounded re-repair), which removes most of the 30 k buffers and the route pressure that broke the mm4 ECO.
3. Count the endpoints per launch-capture clock-leaf pair in mm4; if a few leaf pairs carry most of the 1,092, a leaf-level clock pad is the ECO, not 1,092 data pads.

### Lever 8. KV hub types

**Evidence (V, wave).** kv3_hub_Wo 406,241 cells, kv3_hub_C 773,818: `OT_NATIVE_CELL_CAP SPLIT-NEEDED`. kv3_hub_Wi: `FAIL_PREFLOOR kit_preflight PROVISIONAL[qkd_hr_core_order, _peer, _prompt, qkd_hr_ingest_eng :routed]` and 1.155 M cells (R).

**Fix.** Waive hub_Wo (1.5 % over; QC signed 351 k and r696 waived 500 k). hub_C and hub_Wi are in the range where every past run failed (0.53 to 1.31 M): split on signed ring masters plus dly cores as KV-HUBWO-SPLIT measured for hub_Wo (rows exist for D23; 419,971 -> 199,876 synth cells). hub_Wi also needs its four qkd_hr cores signed, not routed-provisional. These belong in D23, not in D22.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| failure_breakdown 03:14 | intel2 | S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 (unchanged since 23:10) |
| strip route verdicts | intel2 `autopilot/kit_wave_stages.tsv`; epyc8 / epyc10 / intel1 / epyc2 kits `FAIL_POSTCTS`, `tt_setup_repair_grt.log`, t50 `4_cts_final.rpt`, `config.mk`, `1_synth_odb.v` | lever 1 |
| hd_serdes four forms | epyc10 `fable-fix-head-sd9h/*/hd_serdes/{grt_policy.json,signoff_fable/signoff.json,run_route.log}` | lever 3 table |
| GRT vs routed, 85 kit pairs | epyc7 / epyc9 / epyc10 wave kits, `grt_policy.json` + later `signoff.json` | headline 2 |
| lep_pair vE28 | epyc9 `head-lep0n-opus/lep_ve28/kit/.../signoff/signoff.json` | lever 2 |
| hd_lep0N p2, hd_mesh mesh_w1 | epyc9 `4_cts_final.rpt`; `4_1_cts.tmp.log` | -379.62 at CTS; in CTS |
| KV D22s, rider | epyc7 `kv-hg-opus/d22s/gate/gate.out`, `kv-pv-rider/gate3/gate.out` | lever 4 |
| KV PV kit | epyc7 KV-HG6 `kv3_pv_v6/attempt_5` bound RTL | 0 keep copies |
| KV sited proof | epyc9 `kv-hg-opus-site/proof/kv3_pv_v12/run_place.log` | OT_TAIL_SITE line; placed |
| svc reruns | epyc10 `fable-fix-s81-svc2/svc/build/{hslice_mm6,mergex_mm6}` | DRT; CTS hold repair |
| H17 census | epyc9 `fable-fix-s81-serdes2/drtx/census/` | 8 files present, not re-aggregated |
| VPW marker | intel2 `tree_switch_s81.json` | key gone; last VPW fail 00:32 |

## 3. Stop list (the 23:20 list stands, plus these)

1. S81 strip: no relaunch of the 14 SETUP_TRIAGE types on a plan without the XR stage and the core-pin reset relay. No gate-threshold change for them.
2. Serdes (both dies): no go / no-go from `grt_policy.json`. No new H-form or sd9 route before the clock ECO on the routed DBs in hand.
3. hd_serdes: no sd9pb2 follow-up (-92). No unchanged sd9pc2 route.
4. lep_pair vE28: no rebuild; ECO the routed DB. No hd_lep0N judgement from p2.
5. KV: no fourth D22 compose before the `slg.vreq` pad is 15 or less. No PV kit on KV-HG6. No cell waiver for hub_C or hub_Wi.
6. svc: no hslice or mergex run above 30 ps margin; no post-route data-pad ECO on a DB with more than about 100 negative ends.
7. Col: no mass launch before the 405 um hop rule is in the generator; the first col past place must be read at CTS.

## 4. Not checked

- Whether D8d (plan e291d6a8) carries the XR form or a reset relay at the core pins; lever 1 item 1 assumes not.
- The cause of the t15 estimate gap (-17.6 kit GRT against -350 gate estimate); the endpoint classes of 9 of the 14 strip kits (only last repair lines read).
- Whether sign-off internal hold includes the 25 ps SDC uncertainty (lever 7 rests on it).
- The 2 DRCs and the unconstrained endpoints of col_h9_r2. Any col kit past place. The col direct-wire generator (no post found).
- `t25_ns2` result. hslice_mm6 / mergex_mm6 final results.
- KV: the CLAND band logs themselves (wave lines only); pv_v12 timing after place; band fill numbers for PV.
- QC: every N3 route result beyond the six rows in the GRT/routed table; the N3 clock-chain proof; the intra-station proof bind.
- HEAD: hd_host_e route FAIL (GRT-0116 at 01:48 on NF15f) was not opened; the M8 per-instance shape test; die hold on real views (0 measured pairs on HEAD and S81).
- The H17 census numbers are FABLE-FIX-S81-SERDES2's; I confirmed the files, not the aggregation.

---

# FABLE-CLOSURE-STRATEGY 2026-11-17 23:20 PST (2320): delta on 21:20

Reviewer: FABLE-CLOSURE-STRATEGY-2320 (Fable). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round (23:08 to 23:16 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.
Signed (failure_breakdown 23:10): S81 42/394, HEAD 23/26, QC 24/130, KV 6/56. No type signed on S81, QC or KV in the last 4 h (wave stages).

## 0. Headline

1. **S81 col still dies at GPL because the D7w tree-switch marker re-adds the key every tick (V).** `lanes/handoff/tree_switch_s81.json` still holds `OT_S81_VPW_BANK: "1"` at 23:10. Wave stages, last 4 h: 58 col rows FAIL `OT_VPW_BANK needs exactly two real VP SRAM macros, got 0`. The item_env move (6b15cc83) is correct but is overwritten in memory. Until the marker is edited, no col type (216, the largest family on any die) can show a real result.
2. **The S81 die GRT is now real and clean on the clock of record; the landed check still has no result (V).** epyc10 `s81-die-r3-proto/s81/d7w_eco`: ECOv3 clock, taps 21,687, missing 0, overflow 0 / 0 / 0 (M4 2.73 %, M5 4.04, M6 4.42, M7 2.15, M8 0.92, M9 0.79). Then `CHAIN_FAIL CA_CHAIN`: `count_align_plan.py: error: unrecognized arguments: --strap-window --min-lat-cycles 1` (the D7w tree tools predate the r4 recipe). The retry with newer tools (`ca_r4_noparts`) stops at `partition START origins require actual src_part/dst_part on every crossing`. `ca_r4/phase_ocv.log` is empty.
3. **No sited tail-copy result exists yet on either die (V).** KV: the keep + anchor proof (epyc9 scratch3 `kv-hg-opus-site/proof/kv3_pv_v12`) sources `tail_copy_anchor.tcl` at `face_flops.tcl:975`, 7,040 rows in `tail_copies.tsv`, but is still in 3_1 GPL (overflow 0.39); no `OT_TAIL_SITE` line yet. QC: `tail-repl-qc-kit/splitk` stops at 1_synth; nobody has placed a sited st_a.
4. **The tail split pushes KV PV over the cell limit (V).** Wave row kv3_pv_v3: `REFUSED: SPLIT-NEEDED: cells 467307 > 400000`. The split adds 19 to 27 k flops per PV type. S81 kv_leaf__t2 is refused the same way (estimate 462,435).
5. **hd_serdes: the structural fix is building (V).** epyc10 `fable-fix-head-sd9h`: `KP4_PW_BENCH PASS`; sd9h `config.mk` carries `ENC_PW16` + `SYN_PW8`, sd9pa carries `ENC_PPCYC`; both are in 3_1 GPL. sd9pb2 and sd9pc2 have a kit and no log yet.
6. **KV D22 is on its third plan (V).** try 2 (`d22gate/gate.out`): PRE FAIL, bind FAIL `pvw_0 column 5 ... flags [(88, 31), (88, 32)]`. Composer plan d22s 957d81e49c52: PRE PASS, G0 0 errors; first bind stopped on a manifest path, second bind started 06:52Z and has not reported.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Remove `OT_S81_VPW_BANK` from the tree-switch marker; land r676 (skip, nearest bank, FT snap); then read the next col stop classes | col 216 types; leaf t1 t7 t10 t13 t31 t45 t53 t74 t75 | S81-DIE-R3 (marker), FIX-S81-VPW, S81-TYPES-R3 |
| 2 | QC, KV | Sited tail copies, proven at CTS on st_a and pv_v12; PV cell waiver | QC st_a 11 types; KV PV 16 types | TAIL-REPL, FABLE-FIX-KV-HG |
| 3 | HEAD | hd_serdes PW16/PW8; lep_pair vE28 then hd_lep0N with related-pair windows; die clock off the granted M8 tracks | last 3 HEAD types = the die | FABLE-FIX-HEAD-SD9F, FABLE-FIX-HEAD-LEP0N, FABLE-DIE-HEAD, HEAD-PLAN-R4 |
| 4 | all | Close small routed hold misses with the post-route internal hold ECO, not with rebuilds | S81 svc hslice + mergex (then the svc shell, 2 svc families), hd_mesh, QC L2 | CAPSKEW-ECO, FABLE-FIX-S81-SVC2 |
| 5 | KV | D22s bind, with rider + siting folded in; pc 68 taps in D23 | PV 16, pc 6, hroot/pv_v2 band 5 | FABLE-FIX-KV-HG, KV-R3 |
| 6 | S81 | Serdes: H17 routed TT / hold read, then t13 + 10 on D8d | 11 serdes types | FABLE-FIX-S81-SERDES2 |
| 7 | S81 | Die landed check on ECOv3 with the r4 recipe; K refresh + clock site reservation as one clock event | die clock verdict; hold windows of every seam type | S81-DIE-R3, FABLE-DIE-S81 |
| 8 | S81 | Leaf and svc place/kit stops: HPWL (t37, kv_leaf t3), landing collectors missing, svc kit_rtl closure, relay_mid coverage | about 25 types | FABLE-FIX-S81-STRIP, S81-TYPES-R3, FABLE-FIX-S81-SVC2 |

QC N4 content (lever 7 of 21:20) is decided and TAKEN by QC-PLAN-R3 (R, 22:51); no new technical finding. QC has produced no N3 kit, so r650, the halo fix and the 40 ps margin are all still unmeasured.

### Lever 1. S81 col: the marker, then the next classes

**Evidence (V).**
- `tree_switch_s81.json`: `OT_S81_VPW_BANK": "1"` present at 23:10.
- Wave stages, last 4 h, S81 place FAIL 81: 58 `VPW_BANK ... got 0` (col), 9 `distance exceeds 100um` (leaf t1 t10 t13 t31 t45 t74 t75), 2 FT off-grid (t7 `82.9376 176.8544`, t53clb `9.3393 1032.3389`).
- Behind it, already visible on col: `OT_HOOK_COVERAGE relay_mid: 2 of 15 stations on the old fallback; unfitted group:even_hop_um u_bound.u_u_r0_u_y_rt_4a_0:252 u_bound.u_u_r0_u_y_rt_4b_0:206` on 4 col_h9_r0_p2 rows (22:45).

**Root cause.** A type-scoped opt-in sits in a die-scoped marker that `apply_tree_switches` re-applies each tick (R, FIX-S81-VPW 23:10; consistent with what I read). The relay_mid stop is a real design class: two relay groups in u_r0 have hops of 252 and 206 um that the even-hop fitter cannot place.

**Fix.**
1. S81-DIE-R3: re-write the marker without the key (`apply_reviewed_tree_marker`). Release hold `s81-col-vpw-1117` only after one regenerated col spec shows no key.
2. FIX-S81-VPW: r676 (`claude/fix-s81-vpw-ftsnap` @0d4134418d4, gate 67/67) reaches kits only through the S81 tools refresh, which r685 unblocks. Then relaunch t7, t10, t45, t53, t74, t75. Do not wait for the B4 plan row; the gen snap covers t7 and t53.
3. S81-TYPES-R3: for col_h9_r0_p2, add one relay station to each of `y_rt_4a` and `y_rt_4b` (252 -> 2 x 126, 206 -> 2 x 103; +1 cycle, pre-approved) or place the two groups by explicit sites. Do not disable the coverage check.
4. First col kit past GPL: confirm `OT_HOLD_FF_MARGIN = 25` in `config.mk` and read the CTS hold class line before 200 more launch.

### Lever 2. Sited tail copies (QC st_a, KV PV)

**Evidence.** Headline 3 and 4 (V). Unsited result stands: -901.39 -> -912.09 (V, 21:20). Yosys folds unkept copies: 3,155 of 7,040 flops on pv_v12, 35 of 140 on st_a (R). Keep module `ot_dp_dly_keep` READY @6fc8c4a3 with `types.<t>.sites` anchor rows (R).

**Fix.**
1. TAIL-REPL: place `splitk` to CTS now with the bind `sites` rows loaded FIRM by the r650 anchor path. This is the only QC proof and it is not running. Acceptance: `rs_n_c_p` wire under 150 ps, CTS wns better than -250.
2. FABLE-FIX-KV-HG: on the pv_v12 proof read the `OT_TAIL_SITE` line first (`copies N of 7040 sited`, `over_380`, `core_crossing`, `in_halo`). Any `core_crossing` > 0 is the same defect as the 29 detour hops: the anchor must use the routed path around kv3_pv_pair (M1 to M7 OBS). Then reg-to-core against -1,197.
3. COORD/KV: PV types cross 400 k only because of the pad flops (pv_v3 467,307). Waive as in r682; a partition split of a PV column is not wanted. If GPL then stalls for size, cut K: tail copies only on pads with spread over 380 um.
4. The 1,822 short chains on pv_v12 and the pad < K buses need plan stages regardless (R, CHAIN 22:28); they belong in D22s/D23, not in the split.

### Lever 3. HEAD: three types

**Evidence.**
- hd_serdes (R, SD9F 23:20; V on the build state): one stage holds an 8-level XOR rank; sd9f -105.6, sd9g3 -184.09 TT and hold -44.59 on the same family. PPCYC removes one level only.
- lep_pair vE28 (V, epyc9 `lep_ve28/kit/.../run_finish.log`, `postcts_gate_TT.log`): at 6_report (RCX 124,229 nets, IR 1.32 %); GRT-stage gate `pinreg mean 555.05 bound 450.00 ... setup_est 11.75 hold_est -203.93 PASS`. No sign-off file yet.
- hd_lep0N p2 diagnostic (V): 3_3 GPL iteration 210, overflow 0.42, past the band stage.
- Die (V, epyc10 `fable-die-head/base/head/nf15f_t2/CHAIN.log`): combo GRT TT/FF 0 / 0 / 0 at 0.37 %; TT intra +572.03, seam +656.04; seam contract +9.08 (W 90, need 80.92); intra kit-contract -76.07 (W 22, need 98.07, 44,945 pairs). Hold measured on 0 of 585,476 pairs.
- M8 lock (V `m8/lock.log`, R for the totals): tree2 clock legs sit on granted type tracks, e.g. hd_turn_a 150, hd_turn_b 175; 4,321 in 14 types.

**Fix.**
1. FABLE-FIX-HEAD-SD9F: sd9h (PW16 + PW8) is the build of record. At GRT read `tt_setup_repair_grt.log`; expect 5 to 6 levels in the window stage. Stop PPCYC/SPCYC forms once sd9h shows TT >= -42 at GRT; they cost a cycle and fix less.
2. FABLE-FIX-HEAD-LEP0N: the vE28 core has 555 ps mean insertion against a 450 bound. Take the four pair tap offsets from its `clock_contract.json` when it signs, not from the 450 target. Its -204 hold estimate is port-side; close internal hold with r583 as on hei3.
3. HEAD-PLAN-R4: one pack = plan_grown2 + vE28 views with `bb.v` default KCRED 28 + related-pair `per_port_ps` for hd_lep0N and hd_mesh (file in `lanes/handoff/`). The routed window need of lep0N is 163 ps whole-set; the 63 ps figure was placement RC and must not size anything.
4. FABLE-DIE-HEAD: t2g (die clock with granted tracks as M8 obstructions). Types do not re-sign.

### Lever 4. Small routed hold misses: ECO the routed DB

**Evidence.**
- (R, SVC2 22:5x; V that mm6, mm7 are at CTS and mergex_mm6 at floorplan at 23:11) hslice mm4, HM 30, guards off: +2.83 before route, -3.27 routed, -6.15 at sign-off, TT +175.5, DRC 0. mergex mm3b -6.93, TT +97.83.
- Precedent (R): lep_pair hei3 closed 7 -> 2 -> 1 -> 0 pads with r583; sd9f ECO2 kept DRC 0 with 0 cells moved; QC L2 hold closes with the post-route ECO (6 signed).

**Root cause.** Pre-route margin does not predict the routed result on these cores (loss 6 to 9 ps on hslice, 20 to 40 ps on QC). Each margin step costs a full rebuild.

**Fix.**
1. FABLE-FIX-S81-SVC2 (P): run `hold_eco_internal_run.py` (r583) on the routed hslice_mm4 and mergex_mm3b DBs now. Both have large TT room, so a handful of pads closes them. Keep mm6/mm7 running as the second form; sign whichever passes first.
2. CAPSKEW-ECO: make that ECO the default last step of every kit that ends DRC 0, TT >= -42, internal hold between -50 and 0. This is the flow form of what three lanes do by hand.
3. Still open from 21:20: the chunk cap (2,000 buffers x 3) that stopped hslice at 11.7 k endpoints; `OT_HOLD_CHUNK_BUF_PCT=0` is under test in mm6.

### Lever 5. KV D22s and D23

**Evidence (V).** Headline 6. Rider gate (epyc7 `kv-pv-rider/gate2`): G0 PASS twice, LATCHECK `no *_bound_top.sv (the bind did not finish emitting)`; gate3 started 07:00Z. Wave: KV has 8 kit_rtl and 5 gen RUNNING, 0 at place or route.

**Fix (FABLE-FIX-KV-HG).**
1. Gate d22s on strict bind before anything else; the two try-2 errors were both invisible to G0.
2. Fold the rider (29 detour hops, 11 keepout stations) into the same plan if its bind passes this hour; else a separate event. No PV kit before keep + siting + rider.
3. D23 pc: 32 added taps, 68 total, max load 1,200 on measured sinks (R, KV-R3). Add the three forwarded pc clocks over 1,200 (3,347 / 1,303 / 1,271) to the same event. Drop tap_spill.

### Lever 6. S81 serdes

**Evidence (V).** epyc9 H17 `6_report.tmp.log`: RCX `411739 nets finished` at 22:18; unit 476135 still alive at 23:13 in final STA; no numbers yet. 204 `STA-1652 ... pin cland_fwd_fclk_out_ft{0,1,2}_o:N not found` SPEF warnings (98 / 60 / 33, plus 13 on `cland_up`).

**Fix (FABLE-FIX-S81-SERDES2).**
1. When STA ends: routed TT and internal FF hold by class; that read decides whether TAP-GROUP-CAP-1 (6,502 flops on clk_t42) returns.
2. Check the four forwarded-clock nets for missing parasitics before trusting their arrival (P: the SPEF refers to nodes the netlist no longer has after the pad strip).
3. t13 + 10 build on D8d with r678 once h-form PASS is posted.

### Lever 7. S81 die clock event

**Evidence (V).** Headline 2. `sta_droop.log` (legacy margins, not the gate form): TT intra +173.41 (0 negative), seam -0.46 (6 negative), skew 409 / 623; kit contract needs 341 intra / 548 seam against W 40; 0 measured hold pairs.

**Fix (S81-DIE-R3).**
1. Run the landed check with the tools and inputs of the r4j run: `fable-die-s81/reach_codex/run_current_r4_ca_phase.sh` end to end on the d7w_eco proof. Do not pass its arguments to the D7w tree tools, and do not drop `--start-partition-origins`; give the crossings their `src_part/dst_part`.
2. Name the 6 negative seam pairs in the legacy read and show them in the nominal form.
3. D8d (plan e291d6a8) proceeds to bind/G0; the route does not need more cut moves. Then one clock event: in-place K refresh + `clock.reserved_sites_um` after a census of the 42 signed DBs.

### Lever 8. S81 leaf and svc stops

**Evidence (V, wave stages).**
- PLACE-HPWL: t37 `7.8347e6 = 1.40 x 5.5789e6`; kv_leaf__t3 `1.0557e7 = 1.32 x` (new).
- svc: 11 rows (svc_hi pvso_entry t1 t2, rs t1, svc_lo rs_w t1 ...) FAIL kit_rtl `RuntimeError: closure failed for .../items/<item>/`.
- t56: `native module must declare exactly one memory array`. gunit__t1 KIT_PREFLIGHT 5 issues; serdes__t14 4 issues.
- (R, S81-FIX-OPUS 22:22) t22 died at GPL: `OT_CLAND no mapped cells under u_cland_collect_rst_rl_188`, because `build_rebase.sh` drops `--clock-landing` for non-col types.

**Fix.**
1. FABLE-FIX-S81-STRIP: t37 and kv_leaf t3 are one class (timing-driven repair grows area by 78 % on t37 and the placer re-spreads). Image the attempt_8 3_3 DB; if the growth is in the re-slotted ft bundles, cap the TD repair (r496 0.25/0.30) for the family. No ratio change.
2. S81-TYPES-R3: `--clock-landing` for every type with landing rows, then t22 (the GRT calibration over the M5 cores is still unmeasured).
3. FABLE-FIX-S81-SVC2: the svc kit_rtl closure failures are the old soft svc types; they end only with the shell rows (4 of 6 cores signed). Keep them held rather than relaunched.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| failure_breakdown 23:10 | intel2 | S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 |
| wave stages, last 4 h | intel2 `autopilot/kit_wave_stages.tsv` | S81 place FAIL 81 (58 VPW got 0, 9 VPW distance, 4 relay_mid coverage, 2 FT off-grid, 2 HPWL); S81 route RUNNING 41, QC 8, HEAD 10; KV 0 at place/route; SPLIT-NEEDED kv3_pv_v3 467,307 and S81 kv_leaf__t2 462,435 |
| VPW marker | intel2 `lanes/handoff/tree_switch_s81.json` | key still present 23:10 |
| S81 die proto | epyc10 `s81-die-r3-proto/s81/d7w_eco/{CHAIN.log,grt_st_TT/combo_TT.log,ca/ca_plan.log,ca_r4_noparts/ca_plan.log,sta_droop.log}` | GRT 0 overflow; CA_PLAN rc 2 (unrecognized arguments), retry ValueError; legacy STA numbers above |
| svc reruns | epyc10 `fable-fix-s81-svc2/svc/build/{hslice_mm6,hslice_mm7,mergex_mm6}` | 4_1_cts, 4_1_cts, 2_1_floorplan; no exit files |
| hd_serdes | epyc10 `fable-fix-head-sd9h/{bench_b.log,sd9h_gen,sd9pa_gen}` | bench PASS; defines as stated; both in 3_1 GPL |
| HEAD die | epyc10 `fable-die-head/base/head/nf15f_t2/{CHAIN.log,m8/lock.log}` | numbers in lever 3 |
| lep_pair vE28, hd_lep0N p2 | epyc9 `head-lep0n-opus/lep_ve28/kit/...`, `fable-fix-head-lep0n/p2/hd_lep0N/run_cts.log` | 6_report; GPL it 210 |
| H17 | epyc9 `fable-fix-s81-serdes2/H17/.../6_report.tmp.log` | RCX done, STA running, 204 SPEF warnings |
| KV sited proof | epyc9 scratch3 `kv-hg-opus-site/proof/kv3_pv_v12/{face_flops.tcl,tail_copies.tsv,run_place.log}` | anchor sourced; 3_1 GPL; no OT_TAIL_SITE yet |
| QC keep proof | epyc9 `/srv/opentallas-scratch/claude/tail-repl-qc-kit/splitk` | last log 1_synth; no place |
| KV D22 | epyc7 `kv-hg-opus/{d22gate,d22s/gate,d22s/gate_try1}/gate.out`, `kv-pv-rider/gate2/gate.out` | as headline 6 |

## 3. Stop list (the 21:20 list stands, plus these)

1. S81 col: no relaunch while `tree_switch_s81.json` carries the key. 58 fails in 4 h prove each one is wasted.
2. S81 die: do not read `STA_DROOP` (legacy margins) or `STA_LEGACY` as the landed verdict, and do not pass r4 CA arguments to the D7w tree tools.
3. S81 serdes: do not re-add TAP-GROUP-CAP-1 before the H17 routed timing. No new H17 route.
4. S81 svc: no further 30 ps margin rebuild of hslice (mm4 at HM 30, guards off, is -6.15 at sign-off). No relaunch of the soft svc types that fail kit_rtl closure.
5. S81 t37 / kv_leaf t3: no HPWL ratio change (branch 4eeee568 withdrawn; the real log is still 1.38 x). No t22 rebuild without `--clock-landing`.
6. HEAD: no CAPSKEW on sd9g3 (deficit 184 against about 130 per flop). Do not judge the die on `run_grt.sh` (signal-only runner over real views; the combo GRT is 0 / 0 / 0). Do not size lep0N windows from the 63 ps placement span.
7. QC: no partition split of st_a, st_b or hc (st_a is 54 k cells on the current event; 8 types waived by r682). No tt_ctlm region-only fix.
8. KV: no PV kit before keep + siting + rider. No pc judgement on tap_spill. No partition split of a PV column for the cell limit. Do not read the unsited pv_v12 run.
9. Tail split anywhere: no kit without the keep module; unkept copies fold back in synthesis.

## 4. Not checked

- H17 routed TT and hold (STA still running). The cause of the STA-1652 warnings (P).
- Any S81 route result of the 41 running rows; none finished in the window.
- hd_mesh route state and its numbers (R only). The t2g result. hd_lep0N CTS.
- sd9h past GPL; whether PW16/PW8 reach -42.
- KV d22s bind, rider gate3, the `OT_TAIL_SITE` line, the kv3_hg_v1 pilot.
- QC: N3 gate (blocked on a host disk, out of scope), the N3 clock-chain proof (queued), every N3 kit read.
- Whether r583 was already tried on hslice_mm4 or mergex_mm3b (lever 4 item 1 is P).
- The col_h9_r0_p3 place stop (`unclassified`, last GPL line only) and the gunit__t1 / serdes__t14 preflight issues.
- The relay_mid hop arithmetic in lever 1 item 3 is from the error text only; I did not open the plan rows.

---

# FABLE-CLOSURE-STRATEGY 2026-11-17 21:20 PST (2120): delta on 19:20

Reviewer: CLOSURE-STRATEGY-2120 (Opus, standing in for Fable, out of quota until 11-24). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

## 0. Headline

1. **Splitting the pad tails does not help unless the copies are also sited (V).** QC st_a proof `sle_st_a_v1__cl67389ecd` (epyc9 `/srv/opentallas-scratch/claude/tail-repl-qc-kit/{base,split}`, `4_cts_final.rpt`): wns -901.39 -> -912.09, tns -160,939 -> -159,509. The new copy `u_pd2_x_hc1_i_0_u_r0_5` drives one load, `u_u_r0/rs_n_c_p[0]`, but still has 1,585 ps of wire at 5,017 ps slew. The KV pv_v12 split kit (epyc7 `fable-fix-kv-hg-chain/tailsplit/kit_split/kv3_pv_v12`, still in GPL) has no anchor or relay-site knob for the `u_pd*_c*` copies in `config.mk`, and its GPL already added 153,615 buffers on 40,945 nets. It will show the same result. This is now the largest lever: about 27 QC and KV types depend on it.
2. **S81 has no die GRT result, although both proto arms "RAN exit 0" (V).** On epyc10, in `s81-die-r3-proto/s81/{d7w,d8c}`, the kit built, then all three GRT arms died in under 1 s at `mk_combo_kv.py: ModuleNotFoundError: No module named 'die_sta'`, because `OT_DIE_PLAN_TOOLS` is unset. TTA_TT and TTA_FF have no `arr_*.txt`, and CHAIN_DONE still ran. The s_4N_L1 congestion question is unanswered.
3. **HEAD hd_lep0N p2 is dead at global place since 20:19 PST, and no lane has posted it (V).** `fable-fix-head-lep0n/p2/hd_lep0N/run_cts.log` stops with `OT_CLAND no mapped cells found under u_core.u.g_plw.g_s\[0\][/.].*`. The cells do exist in `1_synth_odb.v` (`\u_core.u.g_plw.g_s[0].u_st.q[0]$_DFF_PN0_`), so the CTS read HEAD-LEP0N-OPUS is waiting for will never come.
4. **H17 serdes reached DRC 0, fill and fillcell, then stopped at `6_report` (V):** `[ERROR ODB-0420] tmg_conn::detachTilePins: tilepin inside iterm` (final_report.tcl:13). The r644 in-pin segment ends inside the pin shape, and RCX/tmg_conn refuses it.
5. **Other technical place-stop classes in the last 12 h (V, `kit_wave_state.json`):**
   - S81 `OT_VPW_BANK distance exceeds 100um` on leaf t10, t45 and t74 (+1), up to attempt a9;
   - S81 `explicit FT site is not on a row/site` on t7 and t53;
   - `PLACE-HPWL` divergence on hd_tile (2.26x) and S81 leaf t37 (1.40x);
   - QC GPL-0305 on slw_st_b_v1__cle6023ec2;
   - `SPLIT-NEEDED` over 400 k cells on 7 QC types (hc0, hc2, st_b, 453 k to 487 k) and on kv3_hub_Wo (528 k).

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | QC, KV | Site the split tail copies at their consumer pins | QC st_a 11 types (44 hard rows); KV PV 16 types; PC bin-to-core | KV-HG-OPUS (r657 code), TAIL-REPL (st_a proof) |
| 2 | S81 | Get a real die GRT (fix the proto env), then D8d = re-sited stations + lattice snap + reset write-back + ist_rows | die route verdict; 8 G0 geometry ERRORs; col_h9_r1; t1/t15 serdes reset | S81-DIE-R3 |
| 3 | HEAD | hd_lep0N CLAND stage-row stop; lep_pair vE28 contract; related-pair windows | hd_lep0N, then hd_mesh and the last 3 HEAD types | HEAD-LEP0N-OPUS, HEAD-PLAN-R4 |
| 4 | all | Hold repair must reach the asked margin: no area-guard cut below the target, repair last, in the gate RC frame | S81 svc smc/hslice, S81 col family (236 items), QC N3 at 40 ps | CAPSKEW-ECO, S81-TYPES-R3 |
| 5 | S81 | Pad abut segment ends at the pin edge, not inside it (ODB-0420) | H17 sign-off, then 11 serdes types | S81-SERDES-GEN, S81-FIX-OPUS |
| 6 | S81 | Leaf place stops: VPW_BANK distance, FT site off row, CLAND band | about 8 to 10 leaf types | S81-TYPES-R3 |
| 7 | QC | N4 content: st_a flt_bank 2 stations, clk_t115 split, tt_ctlm pipe stage, coll_core offsets measured before apply, plus the >400 k splits | st_a, cbn_q00, tt_ctlm, coll family, 7 split types | QC-PLAN-R3, QC-N-OPUS, QC-TYPES-R3 |
| 8 | KV | D22 = 612 stations + facegrow + tap spill + tail split **with siting** | PV family, kv3_hroot/pv_v2/v2n band (5), pc pilot4 caps | KV-HG-OPUS, KV-R3 |

### Lever 1. Site the split tail copies (QC st_a, KV PV)

**Evidence (V).**
- In the st_a split kit, every `rs_n_c_p` end keeps its wire and slew: base 1,589 ps / 5,030 ps, split 1,585 ps / 5,017 ps.
- The bind and LEC are correct: 35 of 803 pads were split, giving 140 copies and +123 flops (R, TAIL-REPL 20:33).
- KV pv_v12: the split bind gives 7,044 copies and +19,382 flops (R). The kit has `PRE_DETAIL_PLACE_TCL = face_flops_release.tcl` only, with no anchor for the copies (V).

**Root cause.** r657 `land_pad_tail_split` changes the netlist only. GPL places each copy flop at the timing/wirelength optimum of its fan-in, which is the shared D-K trunk near the clock tap region (clk_t386 in st_a). The copy-to-pin hop stays at the full spread.

**Fix.**
1. KV-HG-OPUS: bind writes a sites record for every copy, at most 20 um from its consumer-core pin centroid (for QC st_a, the soft-leaf centroid from TAIL-REPL's 617dd4d9). The shared trunk stage goes at the pin-spread centroid.
2. The kit loads that record FIRM at 3_3, using the same anchor path as r650 `core_input_anchor.tcl`, so that both dies use one mechanism. A two-pass `type_relay_sites.py` regeneration is the slower fallback.
3. K from the r657 formula keeps each hop at or under `hop_um` 380.

**Acceptance.** On the st_a proof DB, `rs_n_c_p` wire under 150 ps and CTS wns better than -250. Then the same test on pv_v12 (before: reg-to-core -1,197).
4. TAIL-REPL runs the st_a proof as soon as the anchor exists. Do not wait for N4.

### Lever 2. S81 die GRT and D8d

**Evidence.**
- Lever-2 proto chain (V): `CHAIN.log` shows KIT 0, three GRT arms, each `mk.log` with `ModuleNotFoundError die_sta`, TTA 1 FileNotFoundError, CA_CHAIN 1, STA_DROOP 1, then `CHAIN_DONE`. `ot-run` reports exit 0. The same applies to d8c.
- D8c (R, FABLE-PD-S81-2100):
  - moved macros cover 2,296 ft station bits in 8 slots;
  - t1 `rst_rl_170` is gone and t15 `rst_rl_244` is 690 um away;
  - `ist_rows.py` and `cut_census.py` are not in the tree;
  - the 12 moved origins are off the 8.64 um lattice.

**Fix.**
1. S81-DIE-R3: in `proto_die.sh`, export `OT_DIE_PLAN_TOOLS=<tree>/tools/die_plan`. Make the chain exit non-zero when any GRT arm has no `arr_*.txt`. Rerun the D7w arm now; it is the applied plan and needs no D8.
2. Read three things from that run:
   - total overflow;
   - the gcell map over s_4N_L1 (y 19.77 to 21.0 mm), and over s_5S_L0, where the new worst cut segment (0.577) sits;
   - routed clock skew on related pairs.
3. D8d:
   - choose each core's dy so that it clears both the cut line and the station rows of that slot, as a multiple of 8.64 um;
   - otherwise re-site the 8 slots' stations with the generator;
   - build with r666 + gen4 (bind, then `local_reset_writeback.py`, then G0);
   - carry r652 `ist_rows` and r645 `cut_census`;
   - expect G0 with 0 geometry ERRORs, bind rc 0 and LATCHECK 873/873.
4. Run the D8d die GRT A/B against D7w before D8d applies. If the D7w die GRT shows s_4N_L1 below 100 % with no overflow, D8 is not needed for the route, and only the station and reset fixes matter.

### Lever 3. HEAD hd_lep0N

**Evidence (V).**
- p2 failed at 3_3 with the `OT_CLAND` error above. `landing_placement.tcl` lines 323 to 325 hold three `stage:plw_s0..s2` rows. The error is raised when `hit` stays 0 (line 2492).
- The cell names exist in the netlist, so either the escaped regex does not match the ODB names, or every flop was already in `cland_done` from an earlier entry (P: in that case the `continue` leaves `hit` at 0). Both are tool defects on a placement hint, not a plan fault.
- lep_pair vE28 (epyc9 `head-lep0n-opus/lep_ve28`) is in 5_1 GRT hold repair: `OT_HOLD_MM` SS setup -8.44 / FF hold -177.03 at margin 10. Insertion is 586 ps against a 450 target (R).
- tree2 die GRT is at extra iteration 11/50 with a 75 % derate on M4 to M7, so it is congested. Result not yet available.
- tree2 placement-RC clock STA: 195 lep0N taps span 62.9 ps TT (R, 20:22); the kit SDC gives each port a 89 to 96 ps window.

**Fix.**
1. HEAD-LEP0N-OPUS: in `landing_placement.tcl`, count already-placed members as a hit, or test the regex on the 3_2 ODB with `get_cells`. Relaunch p2 from 3_2, not from synth.
2. Replace the stale rp21x per-port windows with related-pair windows from tree2 (`die_sta_related --kit-window-related`). That is the only cure for the cross-tap hold class; more margin is not.
3. HEAD-PLAN-R4: re-derive the four pair-clock tap offsets from the vE28 `clock_contract.json` (about 586 ps) when it signs.
4. When tree2 GRT ends, post the overflow and the gcells for x 880 to 1160 and 1230 to 1472.
5. hd_tile PLACE-HPWL (2.26x) is the same divergence class as S81 t37 and QC cle6023ec2 (lever 6, item 3).

### Lever 4. Hold repair that reaches its target

**Evidence.**
- (R, S81-FIX-OPUS 20:30) smc mm3b r2r FF -10.62 and hslice -5.92. The ORFS hold guard cut HM from 30 to 19 (a projected +8.9 util points over the 8-point limit), then MET-FIRST repaired at HM 0 and stopped.
- (V, 19:2x) The same order problem exists on QC: on slw_sc_v2 the GRT hold repair ends at +0.15, then TT setup repair runs after it.
- (R) Col item_env `OT_HOLD_FF_MARGIN_PS` 10 replaces the die key (25) and the family floor (`_fam = None if _hm`).

**Fix.**
1. CAPSKEW-ECO:
   - when the area guard trips, lower the margin no further than the gate target (0 plus the 20 to 40 ps routed loss already measured), and log it;
   - never fall back to HM 0;
   - run the final hold pass after the setup repair, in the gate RC frame.
2. The mm4 runs (guards off) are the A/B for this. If they sign, make guards-off the svc default.
3. S81-TYPES-R3: the 10 -> 25 change on all col item_env rows. Confirm `OT_HOLD_FF_MARGIN = 25` in the first col `config.mk`.

### Lever 5. Serdes: ODB-0420 at finish

**Evidence (V).** H17 `6_report.log:27` shows ODB-0420 after `5_3_fillcell` and `6_1_fill` passed. Route was DRC 0 at iteration 5, with 1,089 pad nets carrying the r644 segment (R).

**Root cause.** The hook draws a wire whose endpoint lies inside the macro iterm's pin shape. tmg_conn, which RCX and `estimate_parasitics` use, rejects a tile pin inside an iterm.

**Fix (S81-SERDES-GEN).**
- Preferred: end the segment exactly on the pin boundary (the pin-edge point on the access layer), so tmg_conn sees a normal connection.
- Alternative: the strip-before-RCX hook in test, but it must not leave these nets "unrouted" for RCX.
- Prove it on the H17 `6_1_fill.odb` copy; do not route again.
- Then run t13 from the D6z generator (running, epyc10 unit 306723) with the fix, and the TAP-CAP-CENSUS on the first CTS of each of the 11 types.

### Lever 6. S81 leaf place stops

**Evidence (V).** In `autopilot/kit_wave/s81_ot_s81sl_leaf__t10_*/a9` the error is `OT_VPW_BANK distance exceeds100um at u_bound.u_u_lf4_u_vp_g_wr1_u_w.wa0[0]`. The same error appears on t45 and t74 at attempts a4 to a9. Leaf t7 and t53 stop on an FT site off a row (`ft3,1,0 82.9376 176.8544`).

**Root cause (P).**
- OT_S81_VPW_BANK (r-strip, opt-in) clusters the VPW flops beside "both real SRAMs" and fails hard when the bank is over 100 um away. In lf4 sub-leaves the SRAM it chooses is not in the same sub-leaf.
- The FT site x is not snapped to the 0.054 um site grid (82.9376 is off-grid).

**Fix (S81-TYPES-R3).**
1. VPW_BANK chooses the SRAM of the same `u_u_lfN` instance. Under R-MINIMAL, a bank over 100 um gives a WARN and the flops are left to GPL.
2. The generator snaps the FT station xy to the row/site grid.
3. The PLACE-HPWL stops (t37 1.40x, hd_tile 2.26x, QC cle6023ec2 GPL-0305) get one retry of the converged DB without region guides and with the r496 td 0.25/0.30 GPL setting, not another unchanged relaunch.

### Lever 7. QC N4 content

**Evidence (R, QC-N-OPUS 19:5x).**
- st_a `flt_bank` r2 -> r0 runs about 1,000 um. The r1 -> r0 (482 um) and r2 -> r1 / r3 -> r2 (516 um) pairs are also over 405 um.
- clk_t115 has two clusters 200 um apart (W 330 to 359 ps, E 321 to 326 ps). clk_t50 is one hop latch: no split.
- tt_ctlm: 949 ps of data over 31 cells, about 700 ps of it logic. The period is 833 ps.
- The coll_core and cbn_q00__cldbcda913 clock-chain inputs are gone from every host (R, QC-PLAN-R3 19:48).

**Fix.**
1. QC-PLAN-R3, in N4:
   - 2 stations on r2 -> r0;
   - check the three other flt_bank pairs for live nets and add stations where they are live;
   - split clk_t115 at about (600, 2390) and (820, 2470);
   - add 1 pipeline stage in tt_ctlm `u_core`. A region alone removes at most about 250 ps of wire against a 760 ps budget for 700 ps of logic, so it cannot close.
2. QC-N-OPUS: regenerate the clock-chain inputs from the N3 plan before N4 applies. coll_core is `clock.source`, so all 43 new taps start unmeasured.
3. QC-TYPES-R3 with QC-PLAN-R3: the 7 types over 400 k cells need a partition split in N4. The +1,032 head-pad flops on hc in N3 make them larger, not smaller.
4. Carry the halo fix `claude/qc-pad-chain-halo-1117` into N3 by a tools refresh before the cb kits generate. Without it the third HB4 and the pipe register sit inside the r648 strip.

### Lever 8. KV D22

**State (R, KV-HG-OPUS 20:48 to 21:07).** D22 is composed on plan f9eeac833487 with:
- 189 PV stage rows and 612 stations (+99.5 k flops, +612 cycles on 187 lanes);
- `tap_spill_um 600` on 3 kv3_pc_v1 (this answers pc pilot4: 10 taps over the 1,200 cap, clk_t4 at 9,664);
- 6 raw-branch band rows;
- tail split `^kv3_pv`.

The tools refresh is applied (src `_t2509079`, with r641 and r657). Facegrow fix b917b3be is READY for the writer-face band class (kv3_hroot, pv_v2, pv_v2n, pv_v6: 5 rows). The build is moving to epyc7 because epyc10 scratch is full.

**Fix.**
1. Add lever 1 siting before the D22 kits generate. Without it, D22 PV kits repeat the st_a -912 result.
2. Merge b917b3be into the D22 tools.
3. On the first pc kit, run `tap_cap_census.py` on its CTS log and expect no tap over 1,200.
4. kv3_hub_Wo (528 k) needs a split row in D22, or it stays REFUSED.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| QC st_a tail split | epyc9 `tail-repl-qc-kit/{base,split}/run/reports/.../4_cts_final.rpt` | wns -901.39 / -912.09; tns -160,939 / -159,509; copy `u_pd2_x_hc1_i_0_u_r0_5` -> `u_u_r0/rs_n_c_p[0]`, slew 5,017.47, wire 1,585.02 |
| KV split kit | epyc7 `fable-fix-kv-hg-chain/tailsplit/kit_split/kv3_pv_v12/{config.mk,3_3_place_gp.tmp.log}` | no copy anchor; RSZ-0038 153,615 buffers in 40,945 nets; still in GPL (unit 229217 active) |
| S81 die GRT proto | epyc10 `s81-die-r3-proto/s81/d7w/{CHAIN.log,grt_*/mk.log,tta_TT.log}` | `ModuleNotFoundError die_sta` in all 3 arms; no `arr_TT.txt`; chain reported done; d8c the same |
| hd_lep0N p2 | epyc9 `fable-fix-head-lep0n/p2/hd_lep0N/{run_cts.log,landing_placement.tcl,1_synth_odb.v}` | GPL stop at 04:19 UTC (20:19 PST), OT_CLAND `g_plw.g_s[0]`; flop `\u_core.u.g_plw.g_s[0].u_st.q[0]$_DFF_PN0_` present |
| lep_pair vE28 | epyc9 `head-lep0n-opus/lep_ve28/.../5_1_grt.tmp.log` | `OT_HOLD_MM` SS setup -8.44 / FF hold -177.03, margin 10, repair in progress |
| tree2 die GRT | epyc9 `head-die-r/nf15e_e10/hr4/clock_rs8/tree2/kit/grt/grt.log` | derate 75 % on M4 to M7, extra iteration 11/50 at 05:10 UTC |
| H17 | epyc9 `fable-fix-s81-serdes2/H17/.../6_report.log` | ODB-0420 tilepin inside iterm, after fill |
| wave FAIL rows, last 12 h | intel2 `autopilot/kit_wave_state.json` | technical: VPW_BANK 4 (S81), FT off-row 2, PLACE-HPWL 2, MPL-0041 2 (kv_leaf t1/t3), GRTM edge_outline 3 (c1x_C t7/t9, slw_sc_v2), MPL-0034 2 (st_a), GPL-0305 1, SPLIT-NEEDED 8, KV CLAND band 5 |
| failure_breakdown 21:10 | intel2 | signed S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 |

## 3. Stop list (the 19:20 list stands, plus these items)

1. Do not relaunch any tail-split kit (QC st_a, KV PV, D22) without copy siting. It is proven a no-op: -901 -> -912.
2. Do not read an `ot-run ... exit 0` from `proto_die.sh` as a die GRT result. Check that `arr_*.txt` exists.
3. Do not change region-guide box size or registers per region for GPL-0305. It was proven not to be the lever (QC-TYPES-R3 19:44).
4. tt_ctlm: a region-only fix cannot close 700 ps of logic. No clk_t50 split (one hop latch).
5. HEAD: no tree re-cut for lep0N (63 ps whole-set spread). No hd_lep0N relaunch from synth. No hold margin increase.
6. H17: no new route attempt. The defect is at finish (ODB-0420); test the fix on the routed/fill ODB copy.
7. S81: no D8d apply without a die GRT number on D7w. No hand edit of `rst_rl_N`. No VPW_BANK relaunch unchanged (t10 is at a9).
8. QC N3 cb kits: no generation before the halo fix is in the tree.
9. svc: do not raise the hold margin again while the area guard still cuts it. Fix the guard first (lever 4).

## 4. Not checked

- The S81 D8d build. I found no d8d directory on epyc8 or on the hub.
- smc/hslice mm4 results.
- The N3 bind result.
- The kv3_pv_v12 split kit past GPL.
- The tree2 GRT overflow numbers.
- Whether the hd_lep0N CLAND miss is the regex or `cland_done` (both are P).
- The VPW_BANK root cause beyond the error text (P).
- The 4 KIT_PREFLIGHT issues on dsdv_slice_c1x_C (14 rows; the class may be technical).

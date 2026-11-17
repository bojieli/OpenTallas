# FABLE-CLOSURE-STRATEGY 2026-11-17 11:20 PST (1120): delta on 09:20

Reviewer: FABLE-CLOSURE-STRATEGY-1120 (Fable). Read-only, no jobs launched. Technical PD only. HBM parked.
Blocking gates: DRC 0, routed TT setup >= -42 ps, internal reg-to-reg FF hold >= 0 (port hold advisory), die bind + LATCHECK.

Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal, not measured.

## 0. Headline

1. **The S81 col fix (r579, r584) is in no S81 tree, so no col kit carries it (V).** The live tree D5e, the D6 work tree and the D7-strip work tree each have 0 occurrences of `OT_HOLD_FF_MARGIN_PS`, `OT_PREGRT_HOLD_PORT_MARGIN_PS`, `OT_S81_SSTN_M5_BLOCK`, `OT_GRT_PORT_HOLD_INCLUDE` and `prd_obs_check`. A col kit generated at 10:28 with all three knobs in its `item_env` has `OT_HOLD_FF_MARGIN = 0`, no port margin and no M5 block in `config.mk`. The knobs are silently ignored. 203 types.
2. **KV D19 (HG6 v5) passes its gate of record (V):** PRE PASS, G0 0 errors, strict bind 0, LATCHECK 2404 / 2404, `R8_RECHECK changed 0`, `R8_VS_D16_DIFF_LINES 0`. It is ready to publish. 50 types.
3. **HEAD sd9f routes clean, and fails timing (V + R).** Plain detailed route on the eco4 DB ends with 0 violations and an empty `unrouted.txt` in both xa and xb (V). The first sign-off-frame STA reads TT setup -105.88 on 287 ends and internal FF hold -15.48 on 15 ends, against a GRT estimate of -16.30 (R). The problem was never the route.
4. **PG region mode is withdrawn as a default.** H15 and H16 both died with DRT-0255 in iteration 1 (R). The guide-move proof routes G1 / G2 are at 70 % / 60 % of iteration 0 with no verdict yet (V).
5. **The wave has not yet produced a technical result.** No kit launched since 10:00 has reached CTS, GRT or route. Two new technical failures only (section 3).

## 1. Evidence I opened

| item | host, path | result |
|---|---|---|
| Col knobs in trees | epyc10 `kw45/src_s81_pin_3c913dbdfb23_{f2s4_cohort_d5e, d6_1117_work, d7strip_1117_work}/tools`, `physical/common_flow` | 0 files name any of the five r579 / r584 strings. Only the old `OT_PREGRT_HOLD_PORT_MARGIN` (no `_PS`) exists, in 3 files |
| Col kit as generated | epyc10 `kw43-wave-1109n/runs/s81/kit-wave/s81/3fa87b84b18/items/col_h9_r2__t1__cl774acf45__pv11b6518d/attempt_2/gen/.../config.mk` (10:28) | `OT_HOLD_FF_MARGIN = 0`, `HOLD_SLACK_MARGIN = 5`, `OT_GRT_NONPORT_HOLD = 1`; no port margin, no sstn block. Hub `kit_wave.json` `item_env` for this item: FF margin 10, port margin 25, sstn block 1 (67 items carry the set). Row is ROUTE-HELD |
| KV D19 gate | epyc10 `fable-fix-kv-hg2/d19gate/{gate.out, pre.log, g0.log, bind.log, latcheck.log, r8check.log}` (10:26) | PRE PASS 0 findings; G0 PASS 0 errors / 2,396 warnings; bind `errors 0, unbound 0`, 2,545 crossings; LATCHECK 2404 / 2404; `R8_RECHECK changed 0`; `R8_VS_D16_DIFF_LINES 0`; r8 check 64 / 2 / 6 = the D16 baseline |
| S81 serdes H17 | epyc9 `fable-fix-s81-serdes2/H17/serdes__t13/gen/serdes__t13/run_route.log` | `OT_TT_SETUP_REPAIR cells 29; wns -100.23 -> -27.17, tns -11979.65 -> -224.13`. Gate line at global route: TT setup_est -27.17, FF hold_est -25.58. No `5_2` log yet |
| S81 serdes G1 / G2 | epyc9 `fable-fix-s81-serdes2/drtx/G{1,2}/drt.log` | Both in the 0th iteration: G1 70 % with 68,082 violations, G2 60 % with 59,207. No iteration-1 line |
| HEAD sd9f route proof | epyc7 `fable-fix-head-sd9f/{xa,xb}/drt.log`, `unrouted.txt` | Both: 3rd iteration 0 violations, `Complete detail routing`, `unrouted.txt` 0 bytes |
| HEAD corridor columns | epyc9 `fable-fix-head-corridor/{c1,c2,c3}/alloc*.log`, `access*.log`, `c2/place.log`, `gates_pc1`, `gates_pc2` | Unassigned of 59,089 nets: c1 5,028, c2 2,867, c3 367; reach-bad 0 in all. c2: 27 columns, 0 infeasible, 0 keepout overlaps. c3 over the vertical limit at 3 anchors (pin_r4, txi0_r0, txi2_r0; txi2_r0 holds 56 of the unassigned). pc1: G0 PASS 0 errors, nested port bind PASS, but `HEAD_DIE_PORTBIND FAIL port_bind_rc=1`. pc2 compose: `hd_st_n3_turn: bootstrap GEN failed rc=1` |
| QC st_a place | intel2 `autopilot/kit_wave/qwen_compute_slw_st_a_v1__clfc5867a6__pvf82a6c28_bcdaeca55ced5/a4/place_probe.log` (10:50) | `[ERROR MPL-0034] Cannot place u_bound.u_cland_b_hw_ctl_hc0_i at (570.252, 17.292) (617.772, 276.492), outside of the core (4.32, 4.32) (617.76, 1334.88)`. 12 nm over the east core edge |
| KV hub_Wi views | intel2 `autopilot/kit_wave/qwen_kvsys_kv3_hub_Wi_b472b53e5b10a/a2/prov_views.log` (10:25) | `qkd_hr_phy_adp: configured detailed abstract not accepted, blanket fallback refused` (detailed abstract layers differ from the layers above the PG pins) |
| S81 gunit__t1 | epyc10 `.../items/gunit__t1/attempt_7/gen/gunit__t1/preflight.json` (09:29) | 5 `module_closure` issues: `dsdv_seln_cx_c`, `dsdv_seln_fold_c`, `dsdv_seln_x2g`, `dsdv_seln_x2s`, `ot_rst_relay` have no definition in the kit file list |
| Wave rows | intel2 `autopilot/kit_wave_state.json` (11:09), `tools/failure_breakdown.py` (11:10) | Section 3 |

Not opened: the QC N1 bind, the pg3 re-sign, the D6 gate rerun, the HEAD credit benches, the r579 / r584 branch source, the sd9f sign-off STA report.

## 2. Levers, ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col: put r579 + r584 into the tree that generates kits, prove it on one `config.mk` | 203 col types | S81-DIE-R3 (tree), S81-TYPES-R3 |
| 2 | KV | publish and apply D19; stop the flat hub_C | 50 unsigned types | FABLE-FIX-KV-HG, KV-HUBC-SPLIT |
| 3 | QC | N1 with the rows on `qfd_tile_nk_rp2_romleaf_rr`; st_a core edge fix in N2 | 18 cb types, then 11 st_a types | QC-PLAN-R3, QC-TYPES-R3 |
| 4 | S81 | strip: D7 re-slot, calibrated by the leaf kits already running | 20 flagged types | S81-DIE-R3, FABLE-FIX-S81-STRIP, S81-TYPES-R3 |
| 5 | S81 | serdes: G1 / G2 verdict, then H17 to route; pair-row blockage in GRT as the family form | 11 serdes types | FABLE-FIX-S81-SERDES2 |
| 6 | HEAD | sd9f: timing form on the routed DB, not another route | hd_serdes | FABLE-FIX-HEAD-SD9F |
| 7 | HEAD | NF15f corridor: last 367 nets, 3 anchors | hd_lep0N, hd_mesh | FABLE-FIX-HEAD-CORRIDOR, HEAD-PLAN-R4 |
| 8 | all | GRT timing read in the sign-off frame | every type whose GRT estimate passes and sign-off fails | new lane GRT-FRAME (or TOOLS-CONVERGE) |

### Lever 1. S81 col (203 types)

Evidence: section 1 rows 1 and 2 (V). pg3: 110 input-port ends (advisory) and 2 internal ends at -0.44 / -0.29; TT setup -39.36; route-only ECO DRC 0 (R, FABLE-PD-S81-1100).
Root cause: the wave generates kits with the tools of the die source tree. r579 and r584 are approved on main, but D5e, D6 and D7-strip were cut before them. `item_env` exports names the tree's `gen_phys.py` does not read, and nothing reports an unread knob.
Fix.
1. S81-DIE-R3: the D6 tree (or D7, whichever applies first) takes main tools at or after r584. Do not apply D6 without them: every col kit generated from it repeats pg3 (internal -7.61 on 57 ends, port -13.66).
2. S81-TYPES-R3: acceptance on the first col kit from the new tree, read from `config.mk` before place: FF margin 10, pre-GRT port margin 25, `OT_GRT_PORT_HOLD_INCLUDE = 1` with margin 10, sstn M5 block on. Add to gen: an `item_env` name that no generator reads is an error.
3. The ROUTE-HELD kit `col_h9_r2__t1__cl774acf45__pv11b6518d` and the 70 `kit_snap` rows regenerate from the new tree. Do not release the held kit to route as generated.
4. pg3: pad the 2 internal ends, take `hei_drc.rpt`, sign off. The 110 port ends are advisory and need no cell.

### Lever 2. KV D19 (50 types)

Evidence: gate PASS on all six checks (V). Bundle k per R8 group and rq unstationed removed both D18 error classes (R, FABLE-FIX-KV-HG).
Fix.
1. FABLE-FIX-KV-HG: publish D19, PC dry GEN of `kv3_pc_v1__cl23f6a148`, apply, pilot `kv3_hg_v1` to sign-off.
2. 12 KV kits are running place on HG5 (V, wave state). Those whose block sha is unchanged by D19 carry over; the hg / hgi rows restart on D19. Decide by block sha, not by name.
3. `kv3_hub_C` is one of the 12 and is running flat at 773,818 cells (V row, R count). Stop it at place: no flat run of it has closed. KV-HUBC-SPLIT: 15 ring cores + 2 pvfin cores leave about 275k (R); the 6 ring masters are building.
4. `kv3_hub_Wi`: the `qkd_hr_phy_adp` detailed abstract is refused. Regenerate that abstract from the signed ODB with the M6 / M7 detail over its PG pins (one core view, one type). Owner: KV-R3.
5. HG7 (rq ring -> bin over 405 um) stays a separate event.

### Lever 3. QC (18 cb types, then 11 st_a types)

Evidence (R, FABLE-PLAN-QC-N): 68 of 68 tiles kept the W(508) tap latch because the rows were keyed on `qfd_tile_nk_a0c`. r572 fixes the pad hook and adds the unmatched-key bind error. N failed on 44 `HI_PAD` wraps on 11 st_a types and 30 `R8_STALE` bits, both from N START / SC reset. New (V): the st_a place failure of section 1.
Fix.
1. QC-PLAN-R3: N1 = M5 + the two rows on `qfd_tile_nk_rp2_romleaf_rr`. Bind check: 68 `u_hdly_lk_*`, 68 x W(507), 0 x W(508).
2. QC-TYPES-R3: three routed pilots, not one: `cbn_q01__clab6e67f2`, plus `cbn_q11__cl49ae4555` (TT setup estimate about +10) and `cbn_q00__cl622f65d2` (FF hold estimate about +15). Acceptance on the routed DB at the four `tap[0]` pins. If either edge type is negative, the pad count becomes per type (2 or 4 HB4), not a new clock.
3. QC-PLAN-R3, in N2: the cland core `u_cland_b_hw_ctl_hc0_i` in `slw_st_a_v1__clfc5867a6__pvf82a6c28` ends at x 617.772 against a core edge of 617.760. Move the origin west to the next lattice point (the 0.012 is the track offset added to an origin already flush with the edge). Add to G0: hard-core box including `track_offset_um` inside the core area. Check the other 10 st_a types with the same rule before N2 binds; they share the `HI_PAD` rows.

### Lever 4. S81 strip (20 types)

Evidence (R, FABLE-FIX-S81-STRIP, r581): re-slot with cores fixed puts 20 of 20 types at or under 0.70 (worst 0.695), strict bind 0, LATCHECK 873 / 873, +1 cycle on one lane. V: three leaf kits are running place on the old slots (t28, t47, t8) and t43 is route-held.
Fix.
1. S81-DIE-R3: D7 = D6 + `rows_d7_strip.json`, with lever 1 item 1 in the same tree.
2. S81-TYPES-R3: the running leaf kits are the calibration the 0.70 to 1.0 band lacks: t28 is at 0.97, t43 at 0.79, t8 at 0.76 on the old slots. Run them to GRT with no early stop, read per-layer overflow, then stop them (D7 moves their ft pins). This needs no new kit and does not wait for D7.
3. After D7: t22 first to GRT (2.175 -> 0.457). It tests the one unmeasured assumption of the re-slot: bundles crossing M5-ceiling cores on 0.6 of M7.
4. The 45.6 tracks / um model stands (region mode withdrawn).

### Lever 5. S81 serdes (11 types)

Evidence. R: M6 guide segments of 5 um or more in pair rows: H5 obstruction form 216, H15 region 286, H16 region 306; GRT reports 0 overflow in all. `pg_row_guides.tcl` on the H15 DB: 236 bad rows, 105 guides on 98 nets moved, 353 connectors. V: H17 GRT TT -27.17; G1 / G2 in iteration 0.
Root cause: the capacity cut leaves one track in a pair row, so the row is legal to FastRoute and it fills it; detail route cannot reach that track past the via stacks.
Fix (FABLE-FIX-S81-SERDES2).
1. G1 / G2 pass iteration 1: the hook becomes the serdes default with `OT_STB_ROUNDS=16` and the rck balance. Fleet default only after one QC and one HEAD DB with a logged DRT-0255 also pass (QC holds 9 of the 17 position-matched kits).
2. Family form (P): make the GRT blockage match the hook's set. M6 capacity 0 in every row with 1 or fewer legal M6 tracks, so GRT detours and its timing repair sees the detour. The hook then moves 0 guides and stays as a check.
3. H17 before detail route: the gate line reads FF hold_est -25.58 at global route. Confirm the GRT hold repair closed it (H16 needed 80 buffers for -24.27).
4. G1 / G2 fail: one single-worker debug dump on the failing box. No further region or obstruction forms.

### Lever 6. HEAD sd9f (hd_serdes)

Evidence: route proof clean (V). TT setup -105.88 / 287 ends; worst `u_enc.ch_q[404]` (tap clk_t9) -> `u_enc.pp1[237]` (tap clk_t3): data 880 ps with two transport buffers of 113 to 126 ps and a -50 cross-tap window; pma_rck group -73.14; internal FF hold -15.48 / 15 ends (R, estimate with 2 nets unrouted).
Root cause: the encoder XOR plate launches and captures on different taps and is crossed by transport buffers. The kit never reached sign-off STA (pin audit stop, then the read-only mount error), so four ECO rounds optimised a route that could not sign off.
Fix (FABLE-FIX-HEAD-SD9F).
1. Re-run sign-off STA on the xa routed DB. Census the 287 ends by tap pair.
2. If cross-tap pairs carry most of them: put the `u_enc` launch and capture flops on one tap group and remove the transport buffers from that path (tap schedule and placement, 0 cycles).
3. If same-tap paths are still under -42: one register stage in the encoder plate, +1 cycle on the TX lane, priced in LATCHECK (pre-approved).
4. Hold -15.48 on 15 ends is inside the lever 8 limits of 09:20: post-route HB4 after the setup form.
5. `CLKSITE-TAP-ESCAPE-1117` goes to READY now: the routed proof it waited for exists.

### Lever 7. HEAD NF15f corridor (hd_lep0N, hd_mesh)

Evidence (V): column anchors cut unassigned 5,028 -> 2,867 -> 367 with reach-bad 0; 3 anchors over the vertical limit.
Fix.
1. FABLE-FIX-HEAD-CORRIDOR: split `txi2_r0`, `txi0_r0` and `pin_r4` per source column (two half-height columns each). Acceptance unchanged: unassigned 0, reach-bad 0, vertical ratio 0.9 or less, overlaps 0.
2. Resolve `HEAD_DIE_PORTBIND FAIL` on pc1 and the `hd_st_n3_turn` bootstrap GEN on pc2 before calling a candidate.
3. HEAD-PLAN-R4: `KCRED` 28 at both ends in the same event (R: pair core rebuild).
4. The wave enqueued 11 HEAD kits on `head_rp21z20NF15d2r1` at 10:02, `hd_mesh` among them (V). NF15f changes that geometry: hold `hd_mesh` and `hd_lep0N` until the corridor candidate binds.

### Lever 8. GRT timing read in the sign-off frame (all dies)

Evidence: sd9f GRT estimate -16.30 against sign-off -105.88 (R). Col pg3 port hold +4.90 at placement RC against -13.66 at sign-off (R). H16 "TNS 0" at GRT was a stage metric while the class read was -92 (R).
Root cause: the GRT read uses the flow SDC; sign-off adds the cross-tap window, the vclk in / out overlay and the uncertainty. A type can pass every pre-route read and be 90 ps short.
Fix (P): `grt_policy` runs the sign-off STA script (same SDC, overlay, derates, corners) on the GRT DB and prints the same split as sign-off: setup WNS / ends by class, internal hold, port hold. Advisory, no new gate. First users: H17 and the first col kit of lever 1.

## 3. First wave failures since 10:00, by technical class

Rows started since 10:00 (V, wave state 11:09): S81 68 FAIL + 3 running + 2 route-held; KV 12 running + 1 FAIL; QC 2 running + 1 FAIL; HEAD 11 enqueued.

| class | count | example | note |
|---|---|---|---|
| Kit input missing (flow) | 68 S81 col | `ot_s81_cfg7_seq_bfp/xbase` | Input restored 10:15 (R); rows not relaunched by 11:09. Not technical |
| Hard core outside the core area | 1 QC | `slw_st_a_v1__clfc5867a6__pvf82a6c28`, 12 nm | Lever 3 item 3 |
| Child view abstract refused | 1 KV | `kv3_hub_Wi`, `qkd_hr_phy_adp` | Lever 2 item 4 |
| Kit module closure | 1 S81 (09:29) | `gunit__t1`, 5 modules | Kit file list, S81-TYPES-R3 |
| CTS, hold, GRT, DRT | 0 | | No kit launched since 10:00 is past place |

Standing technical rows (failure_breakdown 11:10): S81 congestion 1 (phy__t1), place error 1 (serdes__t3), hold after CTS 1 (serdes__t4); QC macro placement 1. Everything else in the breakdown is flow or superseded.

## 4. Stop list (changes; the 09:20 list otherwise stands)

1. S81 col: applying D6 or D7 without r579 + r584 in its tools; routing any col kit whose `config.mk` shows FF margin 0; another pg3 round for port ends; raising `--max-ends`.
2. S81 serdes: region-mode or obstruction-mode route forms (H12 to H16); region mode as a fleet default; reading H16 as a timing candidate.
3. S81 strip: routing t28 / t43 / t47 / t8 past GRT on the old slots; any kit for the 20 flagged types before D7.
4. KV: the flat `kv3_hub_C` run; another HG6 composer round (v5 passes); treating r8 check 64 / 2 / 6 as a failure.
5. QC: any cb kit on plan 175b9337614e or the out3 / out4 pilot bind; one cb pilot type only; quoting +90.6 / +93.9 as a bound result.
6. HEAD: sd9f route ECOs (the route is clean); `hd_mesh` / `hd_lep0N` kits on NF15d2r1; decisions from `edges_g1.py`.
7. All: accepting a form on a GRT stage metric (TNS, hold line) without the class read.

## 5. Corrections to my 09:20 claims

1. **Lever 4, region mode as fleet default: withdrawn.** I said yes after one DRT proof. The proof failed twice (H15, H16), and pair-row M6 guides rose from 216 to 286 / 306. The plan-model capacity check I asked for is moot.
2. **"H16 is clean at GRT" was wrong.** Setup TNS 0 and hold +0.12 were the CTS and GRT-hold lines. H16 GRT TT is -136.92 -> -92.05 because its post-CTS repair was skipped. The -77.35 I left unexplained was the real pre-repair TT setup. Lever 6 item 1 (resume H16 to route) produced a second DRT-0255 and nothing usable.
3. **KV: 64 unequal groups and 6 conflicting types are the D16 baseline, not an HG6 effect** (KV-R3, confirmed V on D19). The R8 gate of record is table = derivation. My "one k per group" form was right and is v5; my reading of the -22 / -24 pads as a stale table was not checked and is dropped.
4. **Col: "57 ends at -7.61" was the internal-only count.** 107 port ends were in the first sign-off too. My margins (pre-GRT 15, GRT 10) left port hold about -3.7; 25 or the GRT port include is needed. And the fix I ranked first never reached a tree (headline 1).
5. **QC: the cb numbers I quoted (+90.6 / +93.9) were an in-memory ECO.** No bound kit carried the row. My "one bind for N" and stop item "a separate event for the cb row" are reversed: N1 / N2.
6. **Strip: D6 does not carry the ft check as a warn; it has no such check.** The +1 register widening I proposed is not needed: re-slot alone closes 20 of 20.
7. **HEAD sd9f: I said wait for the verification DRT.** The route was never the limit; routed timing is -105.88.
8. **Lever 8 limit "about 100 ends" counts internal ends only** (r583).

## 6. Not checked

- Whether main at r584 reads the `_PS` names end to end; I read trees and one kit, not the branch.
- The sd9f sign-off report and the per-tap-pair split.
- Whether the H17 GRT hold repair ran after the -25.58 gate line.
- The QC N1 bind and whether the other 10 st_a types share the core-edge overshoot.
- Which of the 12 KV HG5 kits keep their block sha under D19.
- The pair-row GRT blockage of lever 5 item 2 and the frame read of lever 8 are proposals.

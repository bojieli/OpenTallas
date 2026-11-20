# FABLE-PD-QC-1600: QC A4 global-place stops (2026-11-20 15:50 PST)

Read-only review. Nothing launched, cancelled or edited. V = verified by me on the kit / plan files today, R = reported by another lane.
Event s29q103S4Q9N46R4A4 (A4). Source: intel2 `~/coord/autopilot/kit_wave_state.json`, `autopilot/kit_wave/*/a*/place.log`, each kit's `istations.tcl` + `pins.json` (hosts epyc2, intel1, epyc8, epyc9, epyc10).
`tools/failure_breakdown.py` is not in rt/current or the owner checkout; I grouped kit_wave_state directly.

## 1. The 15 rows are two classes, not one (V)

| class | rows | error at 3_3_place_gp |
|---|---|---|
| A packed bank | 11 | `exact packed bank overlaps existing explicit reservation: u_lpad_rs_s1 <x> <y>` |
| B station knee | 4 | `internal station knee needs a plan depth change: worst ideal hop N >403um` |

Both stop 20 to 110 s into global place, before any placement. Both are deterministic on unchanged inputs.

## 2. Class A: st_a rs_s0 / rs_s1 (11 types = every st_a type)

**Evidence (V, from each failed kit's `istations.tcl`).** Each bank: 514 payload + 1 epoch site, 1 stage, cell 1.404 x 0.27 um. Footprint overlaps of `u_lpad_rs_s0` against `u_lpad_rs_s1`:

| types | overlapping pairs | of which identical site |
|---|---|---|
| sle_st_a_v2 pv30dda31f__pv88773f93, pv30dda31f__pvd2ec7769, pv4242de79; slw_st_a_v2 cl9f076a5c, clf4365a62 | 51 | 51 |
| sle_st_a_v1 cl67389ecd, cl989804f6__cl18eece69 | 65 | 53 |
| sle_st_a_v1 cl989804f6__cled3c1d7b | 63 | 51 |
| slw_st_a_v1 clb036e152, clfc5867a6__pvf82a6c28, clfc5867a6__pvdf8e5ca4 | 77 | 51 |

First colliding site: v2 (241.92, 293.76), v1 (267.84, 73.44), as in the logs. `u_lpad_rs_s0` passes ("514 payload bits x 1 stages verified"), then `u_lpad_rs_s1` hits its reservations.

**Root cause: wrong plan rows, not geometry and not the check.**
- Not geometry: 1,030 sites in a box of about 300 x 680 um. R (Codex 10:52, epyc10 `.../r4_direct/analysis_all/st_a_packed_r5`): moving 51 S1 sites by at most 29.4 um clears all overlaps, one placed pass.
- Not the check: 51 to 53 pairs per type are the same site for two FIRM flops. The Tcl test is a footprint test with no padding.
- The rows: `bit_sites_um` of `bus:rs_s0` and `bus:rs_s1` are generated one row at a time (each bit at the midpoint of its own leg). `kit_istations.packed_exact_geometry` rejects overlaps inside one row only (its line 133); nothing tests across rows of a type before the kit reaches place.
- Side finding (V): 7 to 9 `u_bin_rs_s0` relay_sites keys sit on packed sites too. Not fatal (spiral placement moves them), but the same missing cross-row test.

**Does V1 fix it? No, not as drafted (V).** Both V1 drafts carry the A4 rows unchanged, depth 1, same overlap counts on all 11 types: epyc9 `v1_cbc/r5/v1a_r5_fabric_a_raw2_plan.json` and `unify-tools-r3-work/ph6/plan_rs.json` (51 / 63 / 65 / 77). Fabric balance, pad hoist and reset reach do not touch these rows. The R5 handoff lists the st_a rows as "not started"; no file in `v1_cbc/r5` changed after 11:01 PST.

## 3. Class B: station knee (4 types)

**Evidence (V, recomputed from `is_bits` rows + `pins.json`).**

| type | bus | stations | legs (first / second) | worst hop |
|---|---|---|---|---|
| sle_su_c, slw_su_c__cl19bb38ef | x_sc_o | 2 | 9.6 / 809.5 | 404.76 |
| sle_ctl__cl503337ff | b_hw_hc2_o | 4 | 807.2 / 1010.8 | 403.61 |
| sle_ctl__cl67434795 | b_hw_hc2_o | 4 | 806.2 / 1010.8 | 403.12 |

**Root cause: plan depth.** The limit is 403 against a plan reach of 405, so the check is 2 um tight, but these chains need more stations under the 300 um cap anyway. The sle_ctl pair fails on `leaf_um` x 305.7 / 306.7; siblings at 307.3 / 307.5 pass by under 0.5 um.

**Does V1 fix it? Partly (V).**
- su_c: the R5 draft has 3 stations on x_sc_o (269.8 um). `ph6/plan_rs.json` still has 2. The compose must keep 3 on all three su_c types (incl. slw_su_c__cl92142dac).
- sle_ctl: the ph6 merge (7 types to 1, leaf x 307.521) passes at about 402.7 um, a 0.3 um margin, by accident. b_hw_hc2_o still has 4 stations in both drafts.

## 4. The other two items

- **Unclassified place error (V):** slw_st_b_v2__pva66d0f22__pvb80e2003 attempt 2 on epyc2: `bwrap: Can't bind mount /oldroot/ on /newroot/ ... /tmp/containerd-mount185193941: Invalid argument`, exit 1 before OpenROAD started. Sandbox set-up race with a transient containerd mount. Infra, not design. Only this item shows it today (2 logs). Sister st_b types are placed.
- **macro_place.tcl MPL (V):** no QC row. kit_wave_state has no QC MPL failure. The six `MPL-0020` rows today are S81 `svc_hi/svc_lo_dsdv_svc_rs` (t1, t2, t4, t5), owner S81-DIE-R4.

## 5. Fixes for QC-PLAN-R5, ranked

| # | row | evidence | check |
|---|---|---|---|
| 1 | Plan, 11 st_a types: `internal_stations` `bus:rs_s0` and `bus:rs_s1` depth 1 to 2 (W514 + epoch slot 514 per stage, +1 cycle on the lanes). Stage 1 beside `u_r1`, stage 2 beside `u_r2`, every leg <= 300. Site both buses and both stages on ONE occupancy map per type. | sec 2; FABLE-PD-QC-0945 sec 6 (794 um to `u_r3` needs three legs) | cross-row overlap 0 on 11 types; one v1 + one v2 place-only |
| 2 | Tool, `tools/die_plan/kit_istations.py`: extend the line-133 overlap test to all exact rows of a type (internal_stations `bit_sites_um`, exact banks, relay_sites), raised at gen and reported by the plan check. Same condition the kit already stops on, two stages earlier. | sec 2: 11 types reached place with 51 to 77 overlaps | scan on A4 plan reports the 11 types; 0 on V1 |
| 3 | Plan, 3 su_c types: `bus:x_sc_o` 3 stations (269.8 um). Keep the R5 row through the ph6 compose. | sec 3 | `istation_knee.py` on the composed plan: 0 over 403 |
| 4 | Plan, sle_ctl (merged type): `bus:b_hw_hc2_o` 4 to 6 stations (269 um, +2 cycles); 5 gives 337. Re-run the knee tool after the `u_ctl` move, since `leaf_um` moves. | sec 3 | worst hop <= 300, not a 0.3 um pass |
| 5 | Ops: `unblock slw_st_b_v2__pva66d0f22__pvb80e2003 place`; classify the bwrap bind-mount line as INFRA auto-retry (owner FAIL-ROUTE / KIT-OPS). | sec 4 | row leaves UNCLASSIFIED |
| 6 | For the 300 pass (0945 fix 7), chains over 300 in these same kits (V): st_a x_fe_o 375.8 (2 -> 3 stations) on all 11; slw_st_a_v2 x_st_b_o 353.3; sle_ctl b_tw_data_st_a_o 330.0, b_hw_hc1_o 313.1, b_hw_hc3_o 337.0, x_su_c_p2_o 337.0; su_c x_su_l0_o 358.6 (2 -> 4), x_su_l0_p1_o 311.0, x_su_l1_p1_o 332.6, x_ctl_o 354.5 / 336.3. | analyzer output | knee tool at limit 300 |

Fallback for row 1 only if the two-stage rows are not composed by the cut AND V1 keeps data reach at 405 on st_a: Codex `apply_st_a_r5_rows.py` S1 reseat. It is proven for the 5 v2 types (hard-pin ends; one placed pass); the 6 v1 types have 11 moved edges each ending at x_st_b_o seats without current evidence. Legs 391 / 405 um, so it cannot ship in a 300 um event.

## 6. Stop list

- No relaunch or `unblock` of the 11 st_a rows or the 4 knee rows on A4 inputs. They stop at the same line.
- No loosening of either check: no 403 -> 405, no skip of the reservation test, no spiral fallback for packed sites.
- No 1 to 2 um `leaf_um` nudge on sle_ctl to pass 403.
- No V1 post while the composed plan still has cross-row overlaps on st_a or 2 stations on su_c x_sc_o. Scan the final composed plan, not the R5 draft alone.
- No 405-form reseat as the V1 form if V1 sets reach 300.
- No die, outline or core-shape change for any of this. None is needed.
- Do not cancel the placed st_b / sle_ctl / su siblings; they are unaffected.

# FABLE-PD-S81-2250 2026-11-14 22:55 PST: col_h10_r1 hold mechanism, B6f structural review, S81 clock budget verdict

Reviewer: Fable, read only. Three small STA reads of my own through ot-run on epyc10 (kit mounted read-only, 4_cts.odb of form fa,
FF and TT, placement RC, about 1 min each); outputs in epyc10 `/srv/opentallas-scratch2/claude/fable-pd-s81-2250/`.
MEASURED = read from a log, report, plan, liberty or my STA read. INFERENCE = fits the numbers, not proven.
Scope note: fa/fd carry the pre-B6 wave plan (kit of 11-14 12:08), so no C1, C2 or C4 content is in these numbers.

## 0. Verdict

1. col_h10_r1 hold is the cross-tap internal class (same as KV kv3_pc), not a forwarded-ring or lockup problem. The ring flops are a
   plain 5-stage pipeline whose ranks sit on different grid taps, and the tap trees are 218-519 ps deep (single sinks to 731)
   against a 250 ps target. Hold repair cannot close it. Density, layer and max-wire forms cannot change it.
2. B6f as assembled does not touch that cause. Step b6f1 goes the wrong way: it replaces measured boundary-register means by the
   liberty maximum over all sinks. Correction to my 22:20 report: "gap b" of lever 2 (435 -> 476, 303 -> 336) is WITHDRAWN.
3. Budget question: (a) 450 ps for the S81 col and leaf families, by the per-type override B6e already uses for serdes, plus
   (c) re-sign of 4 modules. (b) stays only for the residual. The audit's 689 rows are about 11 modules, and 432 of the new FAIL
   rows are judged against a number that is not a measurement.

## 1. Item 1: col_h10_r1 hold (forms fa / fd, epyc10 `type-colh10r1/fa`)

End of the runs (MEASURED): `run_route.log` stops at 22:29 (fa) and 22:26 (fd) inside `repair_timing -hold`, iteration 10. The
containers are gone; STOPLIST-2120 names "TYPE-COLH10R1 fa-fd". INFERENCE: stopped from outside, not a tool exit.
State at the stop: hold WNS -328.49, TNS -1,333,743 ps, 12,263 endpoints (input-port starts excluded by OT_GRT_NONPORT);
setup repair before it ran 7,516 s and left WNS -222.8 on 3,375 endpoints (`u_e8_u_w/go_tag[1]`), RSZ-0062.

### 1.1 The worst path (my FF read on 4_cts.odb; the kit's own hold gate gives the same -374.28 / 12,948)

`u_lpad_frame_int_i1.r[1][476]` -> `r[2][476]`, slack -361.6:

| term | launch r[1], tap clk_t1 | capture r[2], tap clk_t6 |
|---|---|---|
| source latency (plan tap window) | -186.0 | 0.0 |
| tree, FF | 262.2 (13 stages) | 596.8 (22 stages, 2 repeaters of 78.5 and 80.5 ps over macros) |
| data: QN 56.7 + buffer 38.9 + INV 88.0 + wire 6.5 | 190.1 | |
| uncertainty + library hold | | 25.0 + 6.0 |

Split of -361.6: real tree skew 334.6, tap window 186.0, margin 31.0, data credit 190.1.

### 1.2 Three causes, counted over all 12,948 endpoints

| cause | evidence (MEASURED) | endpoints |
|---|---|---|
| A. tap trees not at target | `4_1_cts.log:1986`: TT tap means clk 519, clk_t6 503, clk_t2 440, clk_t12 426, clk_t1 380 ... clk_t15 218, target 250; `:2163` "106 delay cells; tap mean 218..519 (spread 301)"; `:2164` trees to 738, "re-pitch taps to <= 208 um". FF sink latency in my read: t11 112, t10 170-183, t9 180, t5 204, t1 262-333, t3 269-360, t2 323-480, t6 372-605, clk 428-494 (FF target 202.5). `ot_clock_taps.json`: 16 grid taps for 21,664 flops; clk_t1, t2, t6 at the 3,000 cap, clk 2,928 | 5,667 remain with the window removed (worst -309.1); internal ones to -188 |
| B. plan tap window | `constraint.sdc`: early source latency -179 to -208 on every grid tap, late 0, no CPPR between taps. Re-run with early = late: 12,948 -> 5,667 | 7,281 are window only |
| C. seam (port) hold | `frame_int_i1[*]` -> `u_bin_frame_int_i1/q`: vclk 202.5 - 40 against tap `clk` at 428-460 FF; -309.1 | 1,648, all input ports of that bus; not in the 12,263 |

Worst pairs in the 1,200 worst paths: clk_t1 -> clk_t6 290, clk_t10 -> clk_t6 243, clk_t3 -> clk_t2 84, clk_t1 -> clk_t2 59.
Largest classes: lpad rank to rank 1,268 (-374), lpad r -> q 642, lpad q -> lpl_r 621, lpl_r write 754, lpl_w -> bout 725,
core `u_t*` -> station registers about 2,600 (-90 to -264), reset removal `g_rsreg.rq -> o[]` about 850 (-278 to -332).

### 1.3 Can hold repair fix it? No (MEASURED numbers, INFERENCE on cell count)

- TNS -1.33 us on 12,263 endpoints, mean 109 ps each. At 25-35 ps per HB4xp67 that is 38-53 k delay cells, 17-23 % of the
  227,490 instances, in a type whose GRT only converged with `-allow_congestion`.
- First 10 iterations: 26 buffers, WNS -328.5 -> -322.1.
- 3,375 endpoints still fail setup; the resizer does not pad those. r2 siblings ended RSZ-0060 at -245 to -287 on 6-8 k.
- Cause C is outside the repair by construction, and it is real at die level: there are no die cells to fix it later.

### 1.4 Structural fix, ranked (owner DIE-S81-92 unless named)

1. Tap trees at the budget. Split every grid tap over 1,500 sinks (plan `tap_max_sinks`; 186 col types have none, 30 have
   100000) and re-pitch to the 208 um the kit asks for; with the 450 ps budget of section 3 the trees fit without re-CTS tricks.
   Removes cause A and most of C (-309 + about 240).
2. Lane-pad buses on planned taps: one explicit tap per rank of `frame_int_i1` (bin, r[0..4], q; 1,264 flops each, compact at
   the C4 sites) under one `clock.tap_group`, so consecutive ranks are a related pair fed by one die branch. Same for `lpl_*_r/w`.
   Owner S81-COLGEN-1 (sites) + DIE-S81-92 (taps).
3. Related-pair window for col types as well as leaf (cause B). B6f plans it for the 79 leaf types only.
4. `clock.seam_hold` in the plan (KIT-OPS-5 ask, seam_ps 60-90) for what is left of C.
Not a lockup latch: the hops are 189-377 um, a half-cycle stage cannot be paid there. Not `seam_hold` alone: 11,300 of the
endpoints are internal.
Proof (one build, col_h10_r1 to CTS on the fixed plan): tap mean spread under 80 ps, no tree over budget + 40, FF hold before
repair under 1,500 endpoints and above -120 ps, port hold above -90.

## 2. Item 2: B6f (epyc7 `s81-b3-clk/b6f1.py`; `ev/B6f1.json` not written yet at 22:47; base read: `ev/B6e0.json`)

| # | gap | evidence (MEASURED) | effect | fix, owner |
|---|---|---|---|---|
| 1 | b6f1 replaces a measurement by a bound | Plan rows: `u_view.u_c.clk` 434.57 / FF 333.92, `u_ha` 303.17 / 238.36, budget_owner "pin_register_mean .../insertion.json". That file: 1,461 boundary flops, TT min 412.96, mean 434.57, max 464.13; FF mean 333.92. Liberty `max_clock_tree_path` 475.56 is the latest of all sinks (min 375.70). b6f1 raises to 475.56 and scales FF to 365.4 | boundary flops 41 ps early at TT and 31 ps at FF; trips the audit rule on 216 rows (\|d\| 41.0 > 40) | do not raise rows whose owner is pin_register_mean. DIE-S81-92 |
| 2 | element halves: max is the wrong number | Liberty hw 532.99 max / 341.83 min, he 553.18 / 398.92 (spread 191 / 154 ps inside the core). Early is capped at 250. A/B on the fa DB, halves at the cap (-250) against the midpoint (-187.4 / -226.1): TT setup TNS -1,673,856 -> -1,535,772 ps (8 % better), TT hold TNS -53 ps, FF hold TNS -0.1 % | max costs setup and buys no hold | keep 465.39 (io reference) or the midpoint until a boundary mean is harvested from the half sign-off; DIE-S81-92 + PLAN-READERS-1 (harvest) |
| 3 | FF by ratio | FF / TT of the liberty maxima: hw 0.809, he 0.814, col3_c 0.742, bf16_half 0.777 | up to 31 ps FF error per tap | read `_ff.lib` or `insertion.json` ff; never scale. DIE-S81-92 |
| 4 | FF overlay keeps the TT window on core taps | `core_taps_ff.sdc` sets -202.5 without the -early line; my FF read shows the half pin at -364.4 (TT -429 + tree) where -381.5 + tree is meant | 47.5 ps false hold on core-launched paths | emit FF -early lines. KIT-OPS-5 |
| 5 | no col tap window | `clock.tap_window` is null on all 216 col types; kit takes the die per-port 179-208 | 7,281 extra hold endpoints per col kit | section 1.4 item 3. Needs the S81 die proof (DIE-S81-GRT0, not landed) and one DB per type |
| 6 | grid taps unchanged | no key in B6f changes tap count or cap | post-CTS: `OT_TAP_CHECK`, insertion band, and the SETUP_TRIAGE stop that KIT-OPS-5 installed at 22:25 (TT estimate below -150): this kit's TT estimate is -948.8 before C1 / C2 | section 1.4 item 1 in the same event |
| 7 | reset copies only on col_h9_r2 | `reset_replicate` is absent on col_h10_r1; FF setup list of fa: `u_d*_*_Y.q` -> rt / node registers 211 endpoints at -520 to -545 (estimate). INFERENCE: same relay driver class | next worst setup after C1 in r1 families | extend `driver_re` to col_h9_r1 / col_h10_r1. S81-COLGEN-1 |
| 8 | bind overlay on hard-linked trees | the B6 trees are hard-link copies (DIE-S81-92 23:5x); B6c, B6d, B6e binds are running | an in-place write of `reset_replicate.py` changes the source of the running binds | `cp --remove-destination`, as bind_prove26.sh does |
| 9 | G0 | B6c4 G0: 5 new against the 274 control (4 seam hops 454-540 um, 1 cut 0.63) | B6f repeats them unless the S81-LEAF-PLAN re-site delta is in | S81-LEAF-PLAN |

Sound: colgen-1b per-region copies (0 new G0 errors on B6c4_cg); the 26-define re-proof (B6f adds no define); leaf block shift.
Answer to the method question: the liberty maximum decides whether a core needs an early tap; it is not the insertion. The
insertion is the mean latency of the core's boundary registers at each corner, measured at the core sign-off.

## 3. Budget verdict (COORD added scope) and audit check

Audit read: epyc7 `s81-b3-clk/ev/audit_B6e0.json` (22:46): PASS 3,894, UNMEASURED 1,033, FAIL 256. I did not find the 689 run.

Audit sanity (arithmetic MEASURED, cause INFERENCE):
- UNMEASURED by module: hw 216, he 216, ve_s 79 (these three are the only early-tapped LIB-fallback modules), front_roots 216,
  rom 216, sram 75, others 15. 216 + 216 + 79 = 511 = 1,033 - 522 exactly. So the drop is those three modules being judged, one
  row per type; one harvested file cannot produce it. Either the fallback depth is now treated as measured, or one file is
  applied by module name across all types. PLAN-READERS-1 should say which.
- 689 - 256 = 433 = the 432 half rows + 1. Their depth is "LIB fallback 566.7 / 588.4 ps (library arc, not a measurement)",
  which is even 34-35 ps above the liberty maximum (533.0 / 553.2). The rule (declared within 40 ps of measured) is applied to
  a mean-based declaration against a maximum-based depth. For col3_c the same two bases differ by 41 ps on a core that is fine.
- The 256 are 9 modules: dsfd_rstg 132 rows (236 ps on a grid tap), su_t_rxsb 79 (declared 269, measured 207), svc_sx_hrow 16,
  capc5r 14, kp4_dchn 11, 4 single rows. Scale is modules, not rows.

Options:

| | die STA | hold | lane latency | work |
|---|---|---|---|---|
| (a) budget 450 for col + leaf (per-type `insertion_target_override`, as B6e does for serdes) | seam contract is relative: 250-types keep their views if the die tree delivers their taps 200 ps later (`clock.tap_offset`); no S81 die clock is signed yet, so nothing is redone. Corner split of the 200 ps die delay against cell delay: 10-20 ps seam skew (INFERENCE) | cores of 236-301 ps go back on grid taps; col3_c 435 and halves 465 need no early offset (inside +/- 40); the -429 early ends disappear. Deeper trees add local skew, bounded by the tap split | none: no cycle changes | plan keys + kit regen of col / leaf; none of them is signed |
| (b) per-core early taps | 7,796 extra die landings, each with its own window; not in any die proof | every core IO becomes a cross-tap pair; cap 250 cannot serve the halves by the maximum | none | large die clock load |
| (c) re-sign deep cores | none | removes the cause for that core | none | per core |

Verdict: (a) for the col and leaf families in B6f, together with the tap split of 1.4. (c) for four modules only: the two
element halves (internal spread 191 / 154 ps and a `go_tag` pin window of 557 ps at FF, setup_falling 263 + hold_falling 294;
no tap value fixes a spread) and `dsdv_bksel_q` / `dsdv_idx_tx_n32` (clk->q 869 / 1,014 ps, over the period). (b) only where a
core still exceeds 450 + 40 after that, which in col is none. The die-wide common latency stays 250 until the S81 die clock is
built; move it to 450 there if more than half the types carry the override.

## 4. Stop list

- b6f1 as written (raise to liberty maximum, FF by ratio).
- Any further col_h10_r1 form that changes density, top layer, max wire or congestion allowance; hold repair runs on this plan.
- Reading the 689 count as 689 problems, and fixing half rows against the LIB fallback depth.
- Lockup latches or hold padding as the lpad answer.
- Col kit launches on B6f before grid taps are split and a col window exists: they stop at the post-CTS gate.
- Unchanged: the 22:20 stop list, except its lever 2 gap b, which is withdrawn.

## 5. Not done

- No routed data: all STA here is placement RC on the post-CTS DB; GRT numbers are from the kit logs.
- fb / fc (epyc8) not read; they share the plan and the tap set, so the cause is the same (INFERENCE).
- TT -948.8 path not dumped; the A/B path-group report came back empty, so the A/B is whole-design TNS only.
- The 689-row audit run itself; a 450 ps trial build; the rank-tap proof.

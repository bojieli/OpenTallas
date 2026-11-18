# FABLE-PD-S81-0855 2026-11-18 08:55 PST: D8e (bind r4/r5) and serdes H18 clock, structural PD review

Reviewer: FABLE-PD-S81. Read-only. Technical PD only.
Marking: **V** = opened the file / ran the check myself. **I** = inferred from V data. **R** = reported by a lane. **P** = prediction, not built.

Evidence (V): epyc8 `s81-die-r3-e8/d8e/{r3,r4}/bind.log`, `plan_d8e_rd2.json` (d396b7d6), tree plan `7d70fb1ed773` (= rd2 + face-clear),
`fable-fix-s81-strip/rows_face_clear_d8e.json`, tree `tools/die_plan/{taps.py,s81_vpw_bank.tcl,s81_vp_xr_overlay.py,rck_*.{tcl,py}}`,
`physical/common_flow/clock_split_km.tcl`, `d8e/serdes/all_sinks_serdes__t13_H17_4_1_cts.tsv`.
epyc9 H18 kit `fable-fix-s81-serdes2/H18/serdes__t13/gen/serdes__t13`: `4_1_cts.log`, `config.mk`, `pad_clock.json`, `io.tcl`, `budget.json`,
`phy_region_rows.tcl`, `north_rows.tcl`, `cell_census.jsonl`, `pregrt_ff_hold.log`, `run_route.log`.
epyc10 wave items `ot_s81sl_leaf__*/attempt_*/gen/*/postcts_gate_tt.json` (10 leaf kits). `failure_breakdown.py` 08:40: S81 types 42/394, cores 64/64.

## Answers

**(A) D8e does not close all 15 leaf stops, and it does not close the serdes clock.**
- The reset class (hard-core `rst_n`, -298 to -425) should close: 1,967 relay sites on 79 leaf / kv_leaf types are in the plan (V count; closure R/P).
- The `wdo_q` class lands near the gate, without margin, on the types I measured, and stays open on the far types (fix 2).
- Serdes: D8e carries the clk_t42 split, the pin move on 5 types and `OT_S81_LPL_CHUNK` on 11 types (V). It carries no rck structure and no die trunk: `pma_rck` occurs 0 times in `partitions`, `ports` and die `clock` (V). The rck tree stays a single 2 ns root (fix 3).
- State: r4 crashed at 08:37 (fix 1). r5 (t40 reverted, plan a30d6c6f, R) was still waiting on the epyc8 admission lock at 08:50; the tree plan was still 7d70 (V).

**(B) H18 has two separate clock root causes.** rck: one 27,027-flop tree, 34 to 40 levels, 1.66 to 2.06 ns of insertion, balanced only by padding (fix 3). Taps: six north taps sit south of a 285 um region that has no rows since H18, with their sinks north of it (fix 4). The cell count follows from both (fix 6).

## Ranked fixes

| # | finding | owner |
|---|---|---|
| 1 | D8e r4 bind crash: 8 added taps of leaf t40 lie inside moved cores | S81-GEOM-OPUS, S81-DIE-R3 |
| 2 | Leaf XR stage is placed at the bank end; 9 types are too far, the rest have no margin | S81-GEOM-OPUS (rows via S81-DIE-R3) |
| 3 | Serdes rck: single-root 2 ns tree; replace padding by regional roots | S81-CORES-OPUS (pilot), S81-DIE-R3 (generator key) |
| 4 | Serdes north taps and the PTX macro pin cross the row-less PHY region | S81-CORES-OPUS (row spec), S81-DIE-R3 (apply) |
| 5 | H18 is not the D8e form of serdes__t13; die trunk rows absent | S81-CORES-OPUS, S81-DIE-R3 |
| 6 | H18 non-tap cells are at 415k in GRT, over the 400k advisory cap | S81-CORES-OPUS |

FABLE-FIX-S81-COL-1118: no item from this review (col was not in scope; the 918 kept relay rows bind on tools 8efd33fb, R).

### 1. D8e r4: the face-clear rows moved cores under the added taps (BLOCKER, handled in part)

**Evidence (V).** `r4/bind.log`: `ValueError: ot_s81sl_leaf__t40__clf8bbdae1: added tap clk_t20 violates outline/halo/tap spacing`, raised from `reset_anchor.resolve_plan`, 6 min after a 63 min elaboration. I re-ran the `taps.grid_explicit_sites` rule on every type of plan 7d70: one type fails, with **8** illegal taps, not one:

| tap | xy | inside (core box + 8.64 halo) | depth um |
|---|---|---|---|
| clk_t20 | 1064.88, 246.16 | u_ve.u_m | 23.9 |
| clk_t22 | 319.68, 686.90 | u_vp.g_ln[7] | 2.3 |
| clk_t23 | 280.76, 289.44 | u_vp.g_ln[5] | 11.0 |
| clk_t26 | 691.20, 250.44 | u_vn.u_b | 28.2 |
| clk_t27 | 1118.47, 658.80 | u_vsw | 35.1 |
| clk_t29 | 704.16, 868.28 | u_rxsf | 17.2 |
| clk_t34 | 410.36, 394.20 | u_vp.u_b0 | 9.7 |
| clk_t36 | 883.17, 51.21 | u_ve.u_s | 15.5 |

**Root cause (V).** The face-clear row moves 20 hard cores of t40 (22 of t29). Its `clock` entry changes `landing_contract`, `tap_um` and `taps`, but `added_taps` is byte-identical to rd2. `--taps-movable` did not re-site the added taps. The rows had no strict bind proof (R, S81-GEOM-OPUS 06:2x: "not handed as a plan row yet").

**Change.**
1. S81-GEOM-OPUS: re-site all 8 taps of t40 (the bind stops at the first one, so fixing clk_t20 alone costs another bind). Run `taps.grid_explicit_sites` on the row file before hand-off; it takes seconds.
2. S81-DIE-R3: t29 face-clear is still in r5 and is equally unproven (it has no added taps, so this check cannot fail on it). If r5 fails on t29, put t29 back on rd2 at once; do not debug it inside the event.
3. S81-DIE-R3: run `reset_anchor.resolve_plan` (it calls the tap check) before elaboration, not after. Two of four D8e binds died on a plan-content error after the full elaboration.

### 2. Leaf setup stops: XR sits at the bank end, so the whole VS-to-bank wire is in the first cycle

**Evidence.**
- V: the XR flops are generated inside `ot_s81sl_vpw` (`g_xr`, `<writer>_q`), instance path `vp.g_wr1.u_w.g_xr.*`. `s81_vpw_bank.tcl` takes every DFF matching `vp[._/]g_wr1[._/]u_w[._/]` and places it FIRM on the sites nearest a bank. So XR is at the bank; the first cycle is VS `clk -> x_wa` plus the full core-to-bank wire.
- V (0710 review, t50 kit): `x_wa` leaves the VS core at 401.7 ps; required 919. R (FABLE-PD-S81-STRIP, t34): 0.77 ps/um, and 1,541 um of path for 751 um of distance.
- V, D8e plan, VS centre to far bank centre, 75 leaf types: over 500 um 65, over 670 um 42, over 800 um 9 (t3 1,245; t31 998; t10 / t74 995; t13 / t65 920; t14 900; t1 834; t32 805).
- V, the stopped kits I could open (TT gate, no XR): t53 -892 (707 um), t16 -734 (773), t27 -515 (753), t42 -499 (787), t26 -483 (647), t54 -471 (722), t36 -461 (656), t15 -350 (696), t69 -349 (713), t11 -289 (643).

**Root cause (I).** Budget for the wire is 919 - 402 = 517 ps, about 670 um of straight route. A bank-end stage closes types up to about 650 um and nothing beyond.

**Prediction (P).** With XR at the bank and a straight route: 640 um gives about +25 ps, 700 um about -20, 790 um about -90. All ten kits above sit in that band, so they land within ECO range of the -42 gate at best and none has margin; any detour like t34's puts them back at -200 or worse. t16 and t53 were far worse than their distance explains, so they carry a detour or a second class: read their class table first. The 9 types over 800 um stay at -100 to -440.

**Change (0 cycles, no RTL).** S81-GEOM-OPUS: in `s81_vpw_bank.tcl`, when VS-to-bank exceeds 600 um, take the `g_xr.` cohort (902 FF per type, R) out of the bank set and place it FIRM in free rows on the VS-to-bank line at d = min(500 um, W/2) from the VS write pins. Check: 402 + 0.77 d <= 790 for the first cycle; 0.77 (W - d) + 214 (5 gates, R) + setup <= 833 for the second. That holds up to W of about 1,230 um, i.e. every type except t3, which also needs the VS move already named for the far types. Deliver as one per-type plan key through S81-DIE-R3 in the delta after D8e; prove it on t3 and t16.
On the first D8e XR kits read `OT_VPW_BANK placed N FFs`: N = 317 means XR is not in the netlist, about 1,219 means XR is at the bank.

### 3. Serdes rck: the root cause is the tree form, not the root position

**Evidence (V, H18 `4_1_cts.log`).**
- `io_pma_rck[0]_regs`: 27,027 sinks in one TritonCTS H-tree, 1,458 leaf buffers, path depth 34 to 40, average sink wire 1,622 um. Pin at (332.7, 1063.8) beside the PRX macro; decoder macros at x 1,259 to 1,449.
- Before balance: sink insertion 1,656 to 2,060 ps, spread 405. `OT_STB`: 13 rounds, 1,012 INVx4 pads, span 109.5 of 110, by raising the early sinks to 1,948.
- R: H17 routed span 175 against 89 at GRT; routed arrivals of related registers differ by 144 to 179 ps (`rck_rebalance.py` header). Pin at x 1,448 gives 1,695 instead of 2,217 ps (S81-DIE-R3).
- V: no serdes type in D8e has `rck_island`; the plan pin of the 6 non-shore types stays at x 77 to 258 with `u_chn` 540 to 1,080 um away.

**Root cause (I).** Two related rck flops share almost none of a 2 ns tree. A 5 to 8 % error between placement RC and extraction is then 100 to 170 ps of skew, which is what H17 shows. Padding sets the mean, not the error; it also holds 1,012 pads and the hold cells that follow. Moving the root to the centre removes 24 % of the insertion, so Row A alone leaves the same mechanism at about 1.7 ns.

**Change (P, not built).** S81-CORES-OPUS, one pilot kit of serdes__t13 on the D8e form:
1. Regional rck roots with the existing hook `physical/common_flow/clock_split_km.tcl` (`OT_CKKM_PORT=io_pma_rck[0]`, `OT_CKKM_K=16`, i.e. <= 1,700 flops per root). Each root then carries a 4 to 6 level tree; the clk taps of the same kit with 1,146 to 1,650 sinks measure 171 to 328 ps (V). The top tree has 16 loads. Expected rck insertion 550 to 700 ps, and related flops mostly inside one cluster.
2. Opt in the existing plan key `rck_island` so the rck cloud is compact before the split.
3. Keep `OT_STB` only for the 16 roots; do not raise `OT_STB_ROUNDS`. Accept on routed pair skew (`pair_skew.tcl`), not on the sink span.
S81-DIE-R3: generator key on `clock.pad_clock.pins[]` that exports `OT_CKKM_*`, so the 11 types get it from the plan and not from a private `config.mk`.

### 4. Serdes clk taps: the 477 ps spread is a PHY-region crossing

**Evidence (V).**
- `OT_TAP_BALANCE it2`: clk_t17 404-409, t18 382-399, t27 384-400, t28 383-399, t29 412-423, t30 410-416 ps, with 66 to 90 sinks each. Their minimum is above the 250 target, so a delay-only balance cannot fix them.
- These taps are at y 671.76 (`budget.json`); their sinks are the `u_txl.q` strip flops at y 1,206 to 1,207 (sink table). `phy_region_rows.tcl` (new in H18) removes every row in x 314.9 to 2,575.7, y 921.24 to 1,205.82. The tap-to-sink run is 535 um, 285 um of it without a buffer site. The H2 pilot, with rows there, measured 184 to 276 ps on strip-only taps (`north_rows.tcl` header).
- clk_t36 364-495: it also drives the `u_ptx` macro clock pin 450 um into the same region. clk_t22 381-477: sinks up to y 1,068.
- clk_t42 810: 6,627 sinks, cap 100000 in H18. The D8e split is sound: on the H17 sink table the four sites take 1,756 / 1,504 / 1,421 / 1,821 sinks by nearest site, p90 distance 85 um (V).
- `OT_NORTH_TAPS` exists only in the kit `config.mk`; `gen_phys.py` does not emit it (V grep), so the other 10 types do not get even the present form.

**Root cause.** Tap sites south of a row-less region for sinks north of it. The rail fix (rows cut) removed the buffer sites the north trees had used.

**Change.** Plan rows on all serdes types with a north PHY keepout:
1. Six to seven added taps on the north strip itself (y about 1,215), at the x centroids of the present groups (about 587, 905, 1,265, 1,620, 1,981, 2,299, plus the east group of t22). This needs `clock.keepouts_um` cut back to the PHY region top (1,205.82 instead of 1,226.88) and `tap_clear_um` 4.32 on these types: the strip is 21 um tall, and 8.64 leaves a 3.8 um window.
2. One tap at the `u_ptx` clock pin for the macro sink alone, so clk_t36 keeps only local sinks.
3. Do not act on the `OT_TAP_CHECK` advice "re-pitch taps to <= 169 um"; the pitch is not the cause.
S81-CORES-OPUS writes the rows from the H18 sink dump; S81-DIE-R3 applies them with fix 3 in one serdes delta.

### 5. H18 is a recipe pilot, not the D8e serdes__t13

**Evidence (V).** H18 `io.tcl`: `io_pma_rck` at (332.704, 1063.8). D8e plan: (1448.032, 1063.8). H18 has 44 tap ports with clk_t42 unsplit; D8e has 32 grid + 15 added taps. The die plan has no trunk to either pin.
**Change.** S81-CORES-OPUS: use the H18 routed result as evidence for the rail fix and `OT_S81_LPL_CHUNK` only. The countable kit is generated from the applied D8e plan. S81-DIE-R3: die clock rows for `lk_*_pma_rck` in the delta after the D8e apply; decide the pin of the 6 non-shore types after the fix 3 pilot (with regional roots the pin position matters much less).

### 6. Cell count

**Evidence (V / I).** Non-tap cells: floorplan 327,314; place 363,682; CTS 373,784; after the pre-GRT hold pass 390,907 (16,652 hold cells); in GRT hold repair 415,292 (635,149 instances minus 219,857 tap / endcap). GRT hold starts at -30.22 on 501 ends.
**Root cause (I).** About 41k of the 88k added cells are hold cells and pads that pay for clock skew (rck tree, north taps). The cap is advisory; the count is a symptom.
**Change.** None of its own: fixes 3 and 4. Report the non-tap count of the pilot at the same four stages.

## Stop list

1. Do not export H18 as the serdes__t13 sign-off of D8e, and do not judge it at GRT (H17: GRT span 89, routed 175).
2. No further `OT_STB` rounds, larger pad budgets or a per-register capture ECO as the rck answer.
3. No face-clear, relay-site or tap row into a plan event without `taps.grid_explicit_sites` and a private strict bind; do not fix clk_t20 alone on t40.
4. Do not relaunch the 15 leaf rows on d8t; they fail the same way until D8e is applied (R, S81-COL-FLOW-1118).
5. Do not move the XR stage to the VS output end (R: -30 to -130 on far types), and do not add a second XR cycle before the mid-site form is measured.
6. No re-pitch of the serdes tap grid, and no rows put back into the PHY supply region to carry clock buffers (that was the 2,046-row rail fault).
7. No core re-shape for any of the above; moves and sites only.

## Not checked

- The rck sink locations of H18 (no sink dump in the kit); the cluster count 16 is from the sink count alone.
- t29 face-clear geometry beyond the tap rule; the r5 bind result.
- The class tables of t16 and t53 (the kits keep no path report at the TT gate).
- Whether a north-strip tap site clears the pads of the PHY face.

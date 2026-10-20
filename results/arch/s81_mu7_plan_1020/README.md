# S81 mu7 die plan + 116/124-stage array plan (S81-MU7PLAN, 10-20) -- PREPARED, NOT BOUND, NO RELEASE CHAIN LAUNCHED

Inputs: mu5k die GRT (854,368, ot-epyc7 case_mu5k, real PHY view) and its class table
(`results/arch/s81_die10_1020/grt_class_table.md`, claude/s81-die10-1020 @04a5c1233); ROM capacity
(claude/s81-romopt-1020 @5ed4c2ea0, `b/README.md`, `b/min_stages_model.json`, exact runs map97/map116 on ep9).
The mu6n chain belongs to S81-DIE10 and was not touched. Its mu6n_pre stopped at CHAIN_RC 3 (OT_DIE_REP FAIL, fclk_mismatch_hops=1) before GRT.

## Summary table

| variant | GRT overflow (mu5k demand) | die-size effect | work | time |
|---|---:|---|---|---|
| mu5k as is (M2-M7) | **854,368 measured** | 31.97 x 25.00 mm | - | - |
| M8 open, nothing else changed | **82,594 MEASURED** (trial GRT, -90 %) | none | 1 line in the die flow | done (8 min GRT) |
| **mu7 M8-open** (M8 + the M7-cap fixes below, minus the height growth) | forecast **~0-20k** (the residual is all vertical) | ~+1-2 lattice columns (43.2 um each) at x 13-19 mm; height unchanged | layer contract + flow change, CTRL seam (mu6), widen V channels at x 13-19 mm, svc_rs placefix, TOPK 648 repack | ~0.5 d plan + ~6-8 h chain |
| **mu7 M7-cap** (lane-channel sizing + landed M6/M7 hops + CTRL seam + slice side channels + svc_rs placefix) | forecast **~0** only if the die grows **+0.35-0.79 mm in height and +0.72-0.98 mm in width** (32.7-32.95 x 25.35-25.8 mm, 818-850 mm2); **~250-325k** if the height stays at 25.0 mm | +8-19 lattice rows, +17-23 lattice columns | full re-floorplan of the channel lattice, TOPK repack, svc_rs placefix | ~1-1.5 d plan + ~8-10 h chain |

**Recommendation for the owner's decision (a): open M8.** M9 stays PG/clock. The measurement is clean: the same post-repeater mu5k netlist and
placement (grt.odb) were routed again with only `set_routing_layers -signal M2-M8`, and wirelength is unchanged
(453.77 vs 453.71 m).

## Trial GRT (measured, ot-epyc7 /srv/opentallas-scratch/claude/s81-mu5/trial_m8_mu7plan, tools/trial_m8_run.*)

| layer | mu5k M2-M7 | trial M2-M8 | derated resource mu5k -> trial |
|---|---:|---:|---|
| M2 | 31,574 | 0 | |
| M3 | 81,322 | 7,685 | |
| M4 | 332,457 | 13 | |
| M5 | 227,272 | 23,800 | |
| M6 | 155,182 | 52 | |
| M7 | 26,561 | 50,992 | **258.2M -> 650.4M** |
| M8 | 0 (69 demand) | 52 | 0 -> 831.8M (demand 0.87M) |
| total | 854,368 (max H 353 / V 357) | **82,594 (max H 27 / V 307)** | GRT 1 h 26 min -> 8 min |

- **Two effects.**
  - M8 carries the horizontal long lanes, so H overflow falls 519k -> 130.
  - As the top signal layer, M7 was derated over the macro footprints exactly like M6 (258M = the M6 number). Once M7 is
    no longer the top layer, GRT gives it 650M. M7 gains vertical capacity over the macros, and that is the only reason
    V overflow fell too (335k -> 82.5k).
- **Residual, all vertical.** Class method on the trial grt.odb (`grt_class_trialm8.json`, calibrated per layer):
  - CTRL 28k (74 % over the block, M7)
  - frame 28k (82 % open channel)
  - slice_col 14k
  - svc_rs 10k
  - PHY face zone 29k, rest of die 54k
  - Hot 1 mm tiles form a vertical spine at x 13-19 mm, y 1-10 mm: the PHY/CTRL/svc_rs face, then frame/bk_topk at
    y ~7-10 mm. The nets are a_phy, w_hrq/r_hrd, w_x, r_jw, r_mu.
  - CAVEAT: grt_class.py still models M7 as blocked like M6 (cov6), so the M7 split between CTRL and channel is
    approximate. The totals are GRT's own.
- **Owed before binding.**
  - RC/STA of the M8 hops: set_wire_rc and the repeater step use M6. The ASAP7 setRC has M8.
  - M8 vias/pin access stay at the tiles' M4/M5 pins. The tiles keep their layer contract: no tile pin layers are
    added (owner ban); M8 is die-level only.
  - Clock stays -clock M5-M9 (it shares M8 with signals; die clock check).

## Calibrated model (tools/mu7_forecast.py, `mu7_forecast_mu5k.json`; for the M7-cap variant, which cannot be trial-routed without a new floorplan)

- **Method.** The model uses grt_class.py's demand/capacity rasters (mu5k guide dump), pooled per direction (H = M2/M4/M6[/M8],
  V = M3/M5/M7). These are smoothed over a w = 3/5/9 gcell detour window and calibrated per direction to the GRT of
  record (k_H 0.65-1.65, k_V 0.69-3.0).
- **Channel sizing.** The die must grow by height = sum over rows of the worst calibrated H excess, divided by 27.9
  tracks/um (M2+M4+M6 in an open channel at GRT adjustment). Width is the same calculation for V.
- **Area to reach zero overflow.**
  - **Whole die:** +0.46-0.90 mm in height and +1.25-1.55 mm in width.
  - **With the CTRL seam credit** (n32s registered pin order, 1,244 -> 476 wires/pair applied to the PHY-zone
    excess): **+0.35-0.79 mm H, +0.72-0.98 mm W.**
  - Fixed at 25.0 mm height (the height the c4045d687 TOPK refusal used): residual H ~250-325k.
- **The model underestimates M8.** It forecast M8-only at 340-424k because it cannot see the M7 top-layer derate, and it
  missed the V gain. The trial is the number of record. So the M7-cap forecast is the model's best and carries about
  2x uncertainty.
- **Open question (cheap, for the M7-cap variant only).** The M7 derate over macros appears only when M7 is the top
  signal layer. One more trial GRT would settle it: keep signals M2-M7 but remove the top-layer macro derate (GRT macro
  extension / obstruction setting), on the same grt.odb (~10-90 min).

## mu7 die plan (both variants share 1-5; the M8-open variant adds 6 and drops the height growth)

1. CTRL/PHY seam: mu6's real n32s CTRL 388.8x324 centred per 531.25 um pair, 142 um seam channels, array +86.4 um north,
   registered south-face pin order (476 wires/pair), 86.4 um M6/M7 PHY escape band, one landed hop on the full-U upper
   leg (408.4 > 405). Take the measurement from mu6n (S81-DIE10) first.
2. Frame-row lane channels: channel width = ceil(bits x 1.82 / tracks/um) (55 % rule), 276-bit stations staggered
   (never two in one gcell column), long xring/jw/mu/hf lanes split into landed regions with forwarded half-cycle hops
   on M6/M7 (M7-cap) or M8 (M8-open). Owner 08:50 ring rule: every region crossing lands in a fixed-latency ring.
3. svc_rs: owner-approved feedthrough channel (COORD 09:28 (d)) for the gi/go/si/so/dn/r chain buses, plus a merge of
   the svc_rs column pairs. Codex --placefix (+70 um, 6e3559855) is re-derived jointly with the +86.4 CTRL shift.
   No two-layer tile pins (owner ban).
4. Slice columns: widen the side channel by one 43.2 um pitch where a column pair carries > 2 lanes; relays go on the
   column face band.
5. TOPK quarter slot 648x648 (hk2/hk2l, LEAD7-S81 decision) with a coherent TOPK/SVC row repack (no rigid shift).
   idx3 readers (L20RD3 69e03df35) are bound only on PASS.
6. M8-open only:
   - `tools/s81_dv/dv_rvcase.py:794` and `dv_diecase.py:383`: `-signal M2-M8`, `set_global_routing_layer_adjustment
     M6-M8 0.20`.
   - The repeater step and set_wire_rc take M8 for the landed long lanes.
   - Widen the vertical channel(s) at x 13-19 mm (the residual V spine) by 1-2 lattice pitches. M7-cap needs ~17-23
     columns plus 8-19 rows instead.

## Array / chain plan for decision (b) (contents and compiler only; the layer die itself is unchanged)

| plan | layer dies | total dies* | worst ROM pair | static-safe? | compiler | status |
|---|---:|---:|---:|---|---|---|
| release 97 stages | 388 | 520 | 119.24 % | - | - | DOES NOT FIT (exact, 44/44 FAIL) |
| **116 stages** | 464 | **596** (612 if copy-B scales) | 99.61 % (margin 32 words) | **NO**: O2 rotation gives even/odd experts different pair layouts | stage_map_116.json exists; **needs a new chunk/pair policy so every expert shares one layout at <= 60 words/expert** (not built) | exact 46/46 PASS as built (rotating) |
| **124 stages (pinned layout)** | 496 | **628** (650 if copy-B scales) | 99.22 % (model) | YES: one layout for every expert (64/expert) | stage map at slope 64 + exact all-stage runs (~2 h fleet) only | ready to generate |
| floor 108 (reference) | 432 | 564 | 99.8 % (model) | yes | new chunk/pair policy at 56 (not built) | - |

\*Total = layer dies + 52 head/other + 80 copy-B, as in the chain of record. Copy-B is the 10 heaviest groups x2 (B4
knee). If copy-B scales with the layer dies, it becomes 96/102.

- **Recommendation.** 124 stages is the only static-safe fit with the current compiler, because the owner rule bans
  credits and dynamic stalls. 116 is static-safe only after the pinned-layout chunk policy is reworked to <= 60 words.
  That rework is a compiler task with no die change, about 1 day plus the exact re-run, and it saves 32 dies.
- **Calendar and compiler.**
  - The per-layer calendar is unchanged: 1,868-2,006 rows per layer, 3,874 max of 4,096 at 116.
  - cfg7 is 816/1,024 at 116.
  - The per-stage expert count falls from ~158 to <= 136 (116) / ~124 (124).
  - The token-pass per-layer sims are unchanged (per-layer).
  - What must be redone: the chain plan, the MU cal1 group map (copy B = round(layer_dies/40) per group), the token
    path hop list, and the expert map.
- **Rate (model, unmeasured).**
  - Per-user AR loses one die crossing per extra stage: +19 / +27 crossings x 377.6 ns = +7.2 / +10.2 us on a ~960 us
    token, i.e. -0.7 % / -1.0 %.
  - Users (47) and multi-user throughput need the B4 balance model re-run.
- **Calendar time.** 124 takes ~0.5 d: map + exact runs + chain/token-path update. 116 takes ~1.5 d: chunk policy +
  exact runs + chain.
- **Die-plan change:** none. The ROM macros are unchanged, so mu7 is unaffected. The array package/SerDes link count
  grows with the die count: package plan update only.

## Files

- `tools/mu7_forecast.py`: calibrated pooled model.
- `mu7_forecast_mu5k.json`: model outputs for w = 3/5/9.
- `tools/trial_m8_run.{tcl,sh}`: trial GRT recipe.
- `grt_class_trialm8.json`: class table of the trial grt.odb. The dump is on ep7 at die10_ana/trialm8.

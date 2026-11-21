# FABLE-PD-S81-1430 (2026-11-21 13:30 PST): structural review of the S81 J7 plan event before the 20:00 row cut

Reviewer: FABLE-PD-S81-1430 (Fable). Read-only: nothing built, cancelled, patched or deleted; no git in an owner checkout.
Marking: **V** = read or computed by me this round. **R** = reported by the named lane. **I** = inferred.
Inputs read: candJ7c gate (G0 report, logs), candJ7d gate log, plans v9 / v9n, J6 plan candC1n, 22 candJ7c lint kits, lane posts to 13:15 PST.
Scripts: `epyc10 /srv/opentallas-scratch2/claude/fable-pd-s81-1430/tmp/` (tapst.py, col2.py, bk.py, sc.py, v9n.py, svc.py, g0b.py).
Earlier reviews stand: FABLE-PD-S81-1100, FABLE-CLOSURE-STRATEGY 7a88fa0048.

## 0. Verdict

1. **J7 has no green candidate that holds its final content.** candJ7d died in strict bind at 13:0x on bk_sel R6 (V). candJ7c is green but lacks t5, lepe10, bk_sel R6 and the col reset resite. A gate takes about 2 h 45 min (candJ7c: 16:40 to 19:24 UTC), so from the 19:00 decision only two gate cycles fit before 04:15.
2. **The 184 cores beyond street reach are one module on eight types, and the number is a metric effect.** The same types do carry a real, smaller problem: feed-through register sites inside hard cores.
3. **Tap overload is inherited, not a J7 change** (J5 349 taps on 66 types, J6 362 on 71, J7 360 on 70). It does not separate the types that fail hold from those that pass.
4. **ROM e3 at y 648 is not the stuck-strip signature.** 48 of the 53 types have e2 and e3 both at 648. Only the five cl0045af7b types have e2 at 635.04 and e3 at 648.
5. **The ROM-input stage puts 4,832 new flops per col type directly under the ROM south faces**, the rows where the cl0045af7b strip stalled. No J7-form col kit has been placed.
6. **No J7 row guarantees a new short or DRC class.** The clock-site pin class does not exist in S81 kits. The `u_cf` / `u_t0` M5 shorts stay guaranteed on every col kit until the view is proven.

## 1. Ranked risks and rulings

| # | Risk | Measured evidence | Ruling | Owner |
|---|---|---|---|---|
| 1 | Final J7 content never gated | V: `gate_candJ7d.log` BIND_RC=1, `bk_sel__t2: explicit tap clk_t9 violates outline/halo/tap spacing`. v10 (fix) still composing at 13:18. Fallback v9n never gated | Gate both finals as early as possible, not at 19:00: v10 + guard package, and v10n | S81-J6-ASSEMBLY-R4 |
| 2 | ROM-input stage and go guard, 216 col types | Functional: no-guard RTL has the stale-ef window (R). candJ7cG at 13:1x: ELAB 0, strict bind 0, LATCHECK 873/873, G0 pending (V). Physical: section 2.4 | **go**, both together, if candJ7cG G0 and PRE are green by 19:00; else both to J8. No col volume before one placed J7-form read | FABLE-FIX-S81-COLROM-R4, FAM-S81-COL-H9R0-R4 |
| 3 | xo D3 rows, 144 rows on 36 types (p1, p2, p4, p5) | R (H9R0-R3, rep final `5_1_grt.odb`): TT -169.27; 552 of 980 ends below -42 are xo reset recovery, one merged `g_rsreg.rq` drives 2,210 RESETN pins. D3 adds stations to the same merged flop. V: J7 tools rt 8d1cff9b1bb6 has no `OT_RELAY_MID_FIT_POLY` (0 matches; rt current 5) | **go** for the rows (gated in candJ7c). Hold the 36 types until the keep A/B reads at GRT and the wave tools_sha is at or above ae660e1299 | FAM-S81-COL-H9R0-R4, S81-J6-ASSEMBLY-R4 |
| 4 | bk_sel R6 | V: candJ7d red on it. R: v10 copies the 22 re-sited R6 taps; `landing_writer_start` is dropped; R6 kit try 5 is at geom, not routed | **go** only if candJ7e is green on bind, LATCHECK and G0 with no new bk_sel error; else pull `bksel_r6` + `bksel_taps` to **J8** | S81-BKSEL-R7 |
| 5 | cl0045af7b strip, 5 types | R (FABLE-PD-S81-1100): DRT flat at 28,640. V: unique macro set (2.3). STAGGER proof placed 13:17, now at geom, not routed | **go** in the plan, items held. **J8** row if STAGGER fails: adopt the cl9f71e63d macro set (core move, no reshape) | FAM-S81-COL-H9R0-R4 |
| 6 | svc_lo feed-through sites inside hard cores, 8 types | V: section 2.1 | **go** in the plan (no row to pull). svc_lo items held. **J8**: ft slot re-site (`ft_nudge`) and `core_conns` for the idx h-slice cores | OPUS-FIX-S81-SVC-R8 |
| 7 | lepe proof10 row | R: post-hook CTS setup -292.1 to -64.5, TNS -0.87 ns; not routed. V: one type, one sink-side D1 row on 604 bits plus li D1; lane 87 to 88. candJ7d never reached LATCHECK, so the lane is not yet gate-proven | **go** for the unit_o0 row on a green candJ7e LATCHECK. Full package (rx2 bank move) only with its own green private gate by 19:00, else **J8** | FAM-S81-LEPE-4 |
| 8 | COL-R4 reset resite, 78 types | V: one die-level flag, 317 types on the skip list; tree tools know the key. R: dry run on v4, detour hops over 405: 464 to 146, depth unchanged, max hop 275 um. Not gated yet | **go** on a green candJ7e bind. The 146 left are J8 | FAM-S81-COL-R5 |
| 9 | t5 rows | V: 42 ops on `ot_s81sl_kv_leaf__t5` only (32 hard_cores, 8 clock, 2 ft_slots) plus `landing_reader_start`. misc3 gate: bind 0, LATCHECK 0, G0 0 new. An earlier variant (MISC1b) had 277 station cells inside macros | **go** if candJ7e G0 shows 0 new on kv_leaf__t5 | FAM-S81-MISC-R3 |
| 10 | Tap sinks over cap, 70 types | V: section 2.2 | **J8** stands (TAP-GRID-R4). Nothing to pull from J7 | TAP-GRID-R4 |
| 11 | Fallback v9n tree side | V: plan side is consistent (0 rom_in rows, 0 cfg7 rows, 864 seq cores back on `signed_1101`). Not checked: the manifest define, RD_EXTRA sidecars and reproof must flip with it | Covered by ruling 1 | S81-J6-ASSEMBLY-R4 |

Pending offers: eng__t1 view row (1 op, lib key only): go. COL-H10-R3 scan A (re-sites, 0 cycles): go only with its gate folded into the final candidate. Scan X (xo D3 on h10_r0_p1): J8, same reset-merge class as risk 3. svc_s1 GEN, svc hi4, misc5, serdes: J8 as ruled.

## 2. Answers

### 2.1 The 184 cores beyond street reach

- V (recount with `streets.analyze`, demand mode, reproduces 184): all 184 are `ot_s81_svc_idx_hslice_fp`, 23 on each of the eight svc_lo instances (svc_0, 2, 4, 6, 8, 10, 12, 14). Worst 535.68 um.
- These cores are new in J7: svc_lo goes from 72 to 98 hard cores (58 new, 32 removed). J6 had 0 over reach, worst 328 um.
- They sit in four bands of eight, 77.76 x 276.48 um, 8.64 um apart, between the `attn_hcore` rows. Neighbours face each other with 1,146 pins across the alley. Data is by abutment, so distance to a street does not measure it.
- The metric is mode-sensitive: the flat 34.56 um mode gives 489 cores, including 176 `attn_hcore` that J6 already had.
- So: no stations, no core move, no reach rows for this number.
- Real finding on the same types (V, type frame): ft slot register sites inside hard cores. `svc_lo_dsdv_svc_rs_w__t1` 5 of 10 (4 in the new idx h-slice cores, for example ft0 at (654.4, 2412.6) in `u_irg.g_ch[3].u_c.g_s[3].u_s`), `svc_lo_dsdv_svc_rs__t1` 3 of 9, `__t7` 10 of 38. Die level: 49 lane stations in cores against 42 in J6.
- G0 cannot judge these cores: 90 of 98 have no declared connectivity. No svc kit generates today (signoff / liberty mismatch on `xoff0`, also on J6), so there is no placed read.

### 2.2 Tap-sink overload

- V (`tap_sink_loads` on candJ7c): 360 taps over cap on 70 types: 61 leaf, kv_leaf t1 / t2 / t4, c1x_C t5 / t6 / t8 / t9, iq_C t1, slice_station t45. Plan counts are lower bounds (103 types have face and ft sinks only).
- Worst by excess sinks: leaf t28 (19 taps, 5,516), t31 (8 taps, max 2,765, 4,588), t8 (16, 3,851), t72 (17, 3,550), t62, t66, t3, t70, t46.
- Expected to stop at CTS (tap spread, post-CTS triage bound): the 19 types with seven or more taps over, or one tap at 1,700 or more: leaf t1, t3, t4, t8, t10, t28, t31, t44 clf4ea6d4b, t45, t46, t52, t61, t62, t66, t70, t72, t74, t75 and slice_station t45 (I).
- Hold: the cap does not separate. `lanes/S81-TAPSKEW.tsv` (11-19, 22 leaf kits): FF hold -104 to -319 ps on every one, 68 to 88 % cross-tap where split, including t11, t17 and t42, which are not over cap. lepe LP t2 is not on the plan list, yet its kit starts with 27 taps over 1,000 (R).

### 2.3 ROM e3 at y 648 and station crowding

- V (plan v9 and v9n, identical): 60 col_h9_r0 types. e3 at 648.0 on 53, at 635.04 on 7.
- Three macro sets:
  - 48 types (p1 6, p3 12, p4 6, p5 12, p6 12): e2 and e3 both at 648.
  - 5 types (p2 cl0045af7b): e2 at 635.04, e3 at 648, with different `bn3`, `s4`, `t2`.
  - 7 types (p2 cl9f71e63d, the routed form): both at 635.04.
- p3 and p6 (24 types) have no xo relays; two of their classes were read with no four-wide strip (R, FAM-S81-COL-R5). p1, p4 and p5 (24 types) carry xo D3 and are unmeasured.
- Cross-check with the crowding diagnosis: both causes are confirmed and neither fix is in J7.
  - Polyline chains skip FIT: fixed on main ae660e1299 (R). J7 tree and wave tools are 8d1cff9b1bb6, which lacks it (V).
  - xo reset registers merge: the keep A/B has been at kit_rtl since 12:16 (V), no result.
- J7 adds about 150 relay rows per col type (cl0045af7b: 11 rows in J6, 161 in J7; 104 of them are the ROM-input stage) (V).

### 2.4 ROM-input stage geometry

- V (ROM half LEF): the 13 input ports are 604 pins on M5 at 96 nm pitch, all on the south face in x 142.8 to 201.2 (58.4 um).
- The stage is one sink-side D1 row per port and half: 104 rows and 4,832 flops per type, in eight clusters at those pin runs.
- In cl0045af7b the e2 clusters land under y 635 at x 164 to 223 and 432 to 491. The stuck strip is y 620 to 635, x 210 to 345, already at 85 to 96 % row use.
- Benefit (R): 427 rep ends below -42 are ROM inputs, worst -96. Without the stage no col type reaches -42.

### 2.5 Short and DRC classes

- Pins inside reserved clock-site OBS: `kit_pin_site_check.py` does not apply. No S81 kit has `reserved_sites.tcl` (V, 22 lint kits). My equivalent read: 0 of the face pins of the 22 kits lie in a plan tap site or a hard-core rectangle.
- `u_cf` / `u_t0` M5 shorts: unchanged by J7. View and halo proof due 19:00 (R). Col items stay held.
- `dsdv_idx_tx_n32` rst: on track in v9. `track_offset_um` y -0.012 puts the M4 pin at residue 24 nm of the 48 nm pitch (V). Not a guaranteed failure; the try-5 GRT confirms.
- bk_sel `ck` DRT-0073: the lef_override is in 8d1cff9b1bb6 (R).

## 3. Stop list

1. No apply of a J7 candidate that differs from its gated plan sha by even one GEN step.
2. No ROM-input stage without the guard, and no guard gate result taken from candJ7cG for a v10 tree: the final candidate needs its own gate.
3. No col volume on J7 before three reads: one fresh col kit at 0 against `u_cf` / `u_t0`; one placed J7-form col kit with the ROM-input stage; the xo keep A/B at GRT.
4. No J7 col kit generated from tools below ae660e1299.
5. No relaunch of the five cl0045af7b types before the STAGGER proof routes.
6. No stations, core moves or reach rows for the 184 svc_lo cores. No svc_lo kit before the ft slot sites are off the hard cores.
7. No further bk_sel fix cycle after candJ7e: if it is red, bk_sel goes to J8.
8. No tap row in J7. No hold-buffer repair as the answer to an over-cap tap.
9. No scan X or other new xo depth rows until the reset merge is fixed.

## 4. Not checked

- candJ7e, candJ7cG G0 and the lepe private gate were still running at 13:20 PST.
- Whether the kit moves the svc ft registers off the cores at generate (the 11-09 note names `ft_nudge`); no svc kit generates.
- Where the xo stations land on p1, p4 and p5; the placed effect of the ROM-input clusters.
- Whether the reset merge also folds the 104 ROM-input relay registers of a type.
- v9n tree side (define, sidecars, reproof).
- Disclosure: epyc10 was draining and held my ot-run request for the recount. I stopped my own queued client (two PIDs, cmdline checked) and ran the single-thread read with output to stdout only. It wrote nothing to disk.

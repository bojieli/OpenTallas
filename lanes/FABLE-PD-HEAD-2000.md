# FABLE-PD-HEAD-2000: HEAD physical-design review (2026-11-21 18:40-19:10 PST)

Read-and-analyse only. No build, kit, DB, plan or job touched. Previous review: FABLE-PD-HEAD-0700 (its levers are not
repeated). Marks: V = read by me from the file named, R = the owning lane's number, not re-measured.

One slip to record: I copied `density.png` / `congestion.png` of the WRCAP GRT into the local scratchpad directory `ctl/`,
which is HEAD-CTL-R1's. Same source files as its own copies (epyc9 `wrcap_grt_1415/grt_geom`), nothing else written there.

## 0. Summary

| Event | Verdict | Root cause |
|---|---|---|
| 3. hd_ctl WRCAP south strip 0.945 | Not a property of the write-capture form. It is an env delta of the private kit | Private kit config.mk lacks `OT_CLAND_STRIP_DENS=1` (also `OT_PGCAP`, `OT_PLACE_MAX_FANOUT=64`, `OT_PG_CELL_KEEPOUT=0`). The wave kit a8 gets strip rows 3; WRCAP has rows 1 |
| 2. hd_lep0N shelf | GRT flat is two located walls plus the cell cap, not a general density problem | 64 % of the listed overflow sits in gcells with under 10 tracks of capacity (over macros): the RX bank row at y 637.7 and the west `coll_i1` channel |
| 1. START tr12 219 / 329 | Bench artefact, not distance, depth or K settings | tr12 `tb.sv` is `timescale 1ns/1ps` with fractional intra-assignment delays; Verilator 5.050 rounds them to whole ns = T/2 of the 2 ns bench clock (R17's test) |
| 4. r17a v2 561a1f11cf15 | Sound as a package; its payload is overtaken by its own proof | Its only effective row (hd_lep0N shelf) has a measured flat GRT at 98.9 % of the cell cap |

## 1. Event 3: hd_ctl WRCAP (owner HEAD-CTL-R1)

Kit: epyc9 `/srv/opentallas-scratch3/claude/head-crossing-1119/wrcap_grt_1415/active/hd_ctl`. Die 587.52 x 518.4 um.

### 1.1 Where the 0.945 comes from (V)

- `diff` of the `export` lines of the wave kit a8 (epyc9 `kw43-wave-1109n/.../items/hd_ctl/attempt_8/gen/hd_ctl/config.mk`)
  against the WRCAP kit: WRCAP lacks `OT_CLAND_STRIP_DENS = 1`, `OT_PGCAP = 1`, `OT_PG_CELL_KEEPOUT = 0`,
  `OT_PLACE_MAX_FANOUT = 64`, and has `POST_PDN_TCL = pg_rail_check_hook.tcl` instead of `post_pdn.tcl`. `grt_pre.tcl` holds
  0 `pg_pair_cap` lines (a8: 4). These are all in `kit_wave.json` `dies.s81_head.die_gen_env`.
- Effect on the strip. a8 place log: `OT_CLAND strip density ring:b_i ... 2.57 flops/um2 at rows 1, target 1 -> rows 3`
  for all four south / east rings (a_rx_i, b7_rx_i, b_i 3,334 flops, h_rx_i 1,673 flops). The WRCAP kit prints no strip line:
  rows 1. Codex's fallback `south_rows2_place` (epyc10) asks rows 2 by hand and also lacks the four env lines.
- Density result. a8 routed DB: no south bin in the 20 worst (max 0.878, in the west column), 71 bins over 0.70.
  WRCAP final GRT: 10 south bins at 0.927 to 0.945 (x 189 to 379, y 19.3), 91 bins over 0.70.
- Strip content (`south_ring_grt_cells.tsv`, x 170-400, y 8-35, 28,259 cells, 3,704 um2): rows y 15.0 to 26.3 (43 rows)
  run at 0.77 to 0.90 row utilisation over 228 um; the rows below (y 8.2 to 13.4) are at 0.20 to 0.39 and above
  (y 28 to 35) at 0.12 to 0.62. By area: FIRM ring flops 39 %, ring logic of `u_cland_b_i` / `u_cland_h_rx_i` 36 %,
  HB4xp67 hold pads 14 % (4,967 cells, 507 um2, almost all `u_cland_*/holdN`), clock 3 %.

This is the same class as the 11-21 lep0N finding (private kit with a hand env subset). The form itself is not what made the
strip dense.

### 1.2 DRT / DRC prediction

- For: GRT usage is lower than a8 (85 gcells over 90 % against a8's 428, 0 overflow, total usage 11.9 %). a8, same die and
  rings, went 55,830 -> 8,078 -> 5,218 -> ... -> 0 in 5,261 s with bins at 0.86 to 0.88.
- Against: no HEAD kit has routed bins above 0.88. Ten adjacent bins at 0.93 to 0.945 made of DFFHQNx1, OA21x2, NAND2x1,
  INVx1 and HB4xp67 leave under 6 % free sites, so M1 / M2 pin access is the limit, not track supply. `OT_PGCAP` is off, so
  GRT did not reserve the PG pair rows / columns (the DRT-0255 class C3b guard).
- Prediction: DRT converges everywhere except the south strip. I expect a residual of tens to low hundreds of M1-M3
  short / spacing / EOL markers inside x 185-390, y 15-26, flat after about iteration 10. Probability of DRC 0 on this DB:
  roughly 40 %. A marker cluster anywhere else is a different cause (check PGCAP rows first).
- Live note. The route resume re-ran the CTS- and GRT-stage TT steps and rewrote `4_cts.odb` (18:32), `route.guide` (18:36) and
  `5_1_grt.odb` (18:37 PST). The DB under DRT is sha `8b1c58975305`, not the reviewed `8a8cd9c5d06c` (the GRT-stage repair
  added 5 cells, slack kept at +0.11, then "RESTORE before"). DRT pin access started about 18:50 PST. Compare the instance
  count with the reviewed 263,261 at sign-off; same mechanism as FABLE-PD-HEAD-0700 section 0.

### 1.3 Pre-planned response if DRC fails

Ranked. Do (A) now in parallel; it does not depend on the DRT result.

- A. Generate the WRCAP plan `28819946547a` with the exact wave env (the lep0N `lep_gen_waveenv.sh` recipe:
  `die_gen_env` + `item_env.hd_ctl`). That gives rows 3 by `OT_CLAND_STRIP_DENS`, PGCAP, fanout 64. This is also the only
  form the wave will ever build, so a rows-1 or rows-2 private sign-off is not the signing form (private proof, src_manifest
  off). Read first: placed `local_density` (expect under 0.70 as a8), then the wd2 -> xb1 / xa1 write-capture reach and TT.
- B. If markers are under about 50 and all in the strip: one local ECO on the routed DB. Unplace the non-FIRM HB4xp67 pads of
  the failing bins only, re-legalise them into the rows y 8.2-13.4 directly below (free area at 0.80 fill is about 590 um2
  against 507 um2 of pads, moves under 12 um), then ECO-route the touched nets. Hold pads tolerate the move (FF internal
  margin +10.9 at GRT, pre-GRT cross-tap +45). Re-check TT (only +0.11 at GRT) and FF internal hold.
- C. If markers are over about 50, or outside the strip: no ECO loop on this DB. Go to (A).
- Drop `south_rows2_place` as the fallback: it is a hand copy of half of what the wave env does (rows 2 against rows 3) and
  still lacks PGCAP.

Risk to carry into (A): rows 3 moves the last ring flop about 18 um further from its pin. a8 had rows 3 and its only failure
was the wd2 write path that WRCAP removes, so I expect no new setup path; confirm on the placed DB.

## 2. Event 2: hd_lep0N shelf form (owner FABLE-FIX-HEAD-LEP0N-R3)

Kit: epyc10 `fable-fix-head-lep0n-env/shelf_we/gen/gen/hd_lep0N` (cancelled 18:42 by R3 on the flat-GRT rule; reports kept).
Die 1,892.16 x 1,408.32. Four `ot_s81hd_lep_pair` macros (777.6 x 492.48, OBS M1-M7) in a 2 x 2 grid leave one central band
y 510 to 847, which holds 45 SRAMs in shelves.

### 2.1 What the flat overflow is made of (V, `congestion-5.rpt` / `congestion-10.rpt`, each capped at 20,000 gcells)

- Listed sum 89,584 -> 90,077 (R3's numbers confirmed). Direction moved (H 37.0k -> 45.4k, V 52.6k -> 44.7k), total did not.
- Capacity class at iteration 10: 57.5k of the 90.1k (64 %) is in gcells whose total capacity is under 10 tracks, against
  about 30 for a free gcell (gcell 0.57 um). Those are gcells over macros. `reserved_sites.tcl` is not the cause: 336 clock
  sites, 7,915 um2 in total.
- Wall 1, RX bank row. `g_rx[0]` + `g_rx[3]` banks: ten 51.4 x 20.8 SRAMs in one row at y 637.7, x 1,008 to 1,620, slits of
  4 to 24 um. V overflow inside x 1,000-1,625, y 635-662: 12,045 on 3,209 gcells. Top source family: top-level `netN`
  (resizer-inserted buffer nets) 21.6k mentions, six times the next (`g_inpipe.rop` 3.5k, `u_rx_mem.raw` 2.2k).
- Wall 2, TX bank rows y 555-606 (x 970-1,700): H 7,819 on 780 gcells, about 10 per gcell, on M6 / M8 over the SRAMs.
- West channel. `u_cland_coll_i1`: 3,043 FIRM ring flops "stretched over pin y 640.39..845.59" in the 65-um channel between
  the die edge and the SRAM / pair-macro column at x 69.2; 10,075 ring logic cells left to global place. H 11,179 at
  x 55-105, y 840-925 (the pair macro's lower-left edge, capacity 0-9) plus V 7,393 in the channel. 95 % of the source nets
  are `u_cland_coll_i1` / `u_bin_coll_i1` internals. It grew 18.1k -> 21.9k between the two reports (R).
- Cell cap: pre-GRT hold `pass rr margin 40` took instances 462,410 -> 492,241 (+29.8k) for the 40 ps R2R margin; the
  5 ps pass before it already had 0 violating endpoints. 37,757 hold cells in total, non-tap 395,746 (98.9 %).

### 2.2 Consequence for the type split (R3's next lever)

The split is right for the cap. It does not by itself remove either wall: both are macro geometry inside the central band
and the west channel. Rows the split plan must carry, with the measurement that decides each:

1. Break the RX bank row: no SRAM row longer than about 250 um without a gap of at least 40 um, or put `g_rx[0]` and
   `g_rx[3]` banks in two columns beside their consumers, so `rop` / `raw` and the buffered nets do not cross the row.
   Measure: V overflow in x 1,000-1,625, y 635-662 at GRT iteration 5.
2. Give `coll_i1` (and its twin `coll_i2`, same "stretched" form at y 120-326) to the io part with its ring logic, and
   do not seat the ring in a 65-um channel that ends at a macro corner. Measure: listed overflow at x under 200.
3. Run the split parts with `OT_PREGRT_HOLD_R2R_MARGIN` as measured need, not 40. The 5 ps pass closed all endpoints; 40 ps
   cost 29.8k cells and the buffered nets are the top family on wall 1.
4. Macro sites move, shapes do not (owner rule): all three are moves.

## 3. Event 1: START tr12 219 / 329 (owner HEAD-START-R17)

- V: epyc7 `head-start-r17/tr12/tb.sv` line 1 is `timescale 1ns/1ps`, the bench clock is `always #1` (2 ns), and all 1,758
  region clocks are `always @(clk) clk_region_X <= #(8.6713) clk;` with fractional ns delays.
- R (R17, 18:40): on Verilator 5.050 `#(0.4)` delays by 0 and `#(6.6)` by 7 ns under 1ns/1ps; integer ps under 1ps/1ps is
  exact (`dlytest/t.sv`, `t2.sv`). In tr13 the START origin minus nominal is 151 for every phase from 0.9 T to 7.2 T.
- So tr11 to tr24 put every region clock on a T/2 grid. The 219 / 215 / 202 counts and the 53 re-chosen K of tr21 / tr22
  measure the bench. Root cause is neither hop distance nor stage depth nor K settings. tr10 (ideal clock) had already shown
  all 358 parts reach their origin within 1 count and the 9 relays keep half-hops at 286 um or less.
- Structural fix: none in the plan today. tr25 (1ps/1ps, integer ps; 427 / 427 crossings inside their window, R) is the
  functional gate for e1b; it was still running at 18:55 PST.
- If tr25 still fails: look only at the 19 tile-chain lanes with origin +-1 from tr10 (24 parts at -1, 18 at +1, 2 at +2).
  That is the plan's J model (2 per stage for d in (0, T)) and the fix is the START sidecar origin, not K on the rings.

## 4. Event 4: r17a v2 561a1f11cf15

- Package: plan 00b2abf6e7a6 on applied r16 p5, sidecar 6fcd1d3dfc43 and START p5 unchanged, tools 745c8f11; static schema,
  PRE / G0, containment, 31 view hashes pass (C / R). Nothing in it touches the other 25 types' pins. Sound as a container.
- Payload: (a) hd_lep0N shelf type row, (b) hd_serdes `tap_grt_pre` + two tap groups. hd_serdes is a deferred re-sign with
  no new builds. So the only consumer is the wave hd_lep0N row, and that row is the form measured in section 2: flat GRT
  at 98.9 % of the cap in the wave env.
- Verdict: applying it is harmless and moves the wave row off the 2x2 form (-679), but it cannot produce a sign-off. Since
  it is disk-held anyway, the better event is r17a + the split rows (section 2.2) + the hd_ctl WRCAP row in one reseal,
  which also keeps the one-event-per-24-h rule. If the marker lands first, the wave shelf build should stop at the placed
  review and not spend about 10 h reaching the same GRT.

## 5. Ranked levers

| # | Lever | Evidence | Owner |
|---|---|---|---|
| 1 | hd_ctl: generate WRCAP with the exact wave env now (rows 3, PGCAP, fanout 64); it is the signing form | config diff; a8 rows 3 with no south bin over 0.84 against rows 1 at 0.945 | HEAD-CTL-R1 |
| 2 | hd_lep0N: split plan carries the RX-row break, the `coll_i1` / `coll_i2` re-seat and measured hold margin | 64 % of overflow under 10-track gcells; 12.0k on the RX row; 18.6k in the west channel; +29.8k cells for margin 40 | FABLE-FIX-HEAD-LEP0N-R3 (plan), Codex split1121 (RTL) |
| 3 | START: tr25 exact-ps bench is the gate; discard tr11-tr24 counts and the 53 K candidates | tb.sv 1ns/1ps fractional delays; origins constant over phase | HEAD-START-R17 |
| 4 | hd_ctl DRC fail: strip-only HB4 pad ECO if under about 50 markers, else lever 1 | 507 um2 of pads against about 590 um2 free in the rows below | HEAD-CTL-R1 |
| 5 | r17a: fold split + WRCAP rows into the reseal while it is disk-held | sole payload is the shelf row | FABLE-FIX-HEAD-LEP0N-R3 |

## 6. Stop list

1. Private HEAD kits generated with a hand env subset. Third case in two days (lep0N shelf_bf / col_bf, hd_ctl WRCAP and
   rows2). Diff `config.mk` against the wave kit of the same type before the first place.
2. `south_rows2_place` as the hd_ctl fallback.
3. ECO loops on the WRCAP rows-1 DB beyond one strip-local pass.
4. Any unchanged hd_lep0N shelf relaunch, private or wave, past the placed review.
5. Treating the type split as a cell-count fix only.
6. Carrying tr21 / tr22 K candidates, or any tr11-tr24 count, into a plan or a status line.
7. Quoting the reviewed GRT sha for a resumed kit without re-hashing after the resume gates ran.

## 7. Not verified

- I did not re-run the Verilator delay test (the build dir is R17's); the tb.sv form is mine, the rounding is R17's.
- The DRC prediction is a judgement from a8 and the density data; no HEAD kit has routed above 0.88.
- `netN` on the RX row is resizer-inserted nets; I did not separate hold buffers from repair buffers in the DB.
- Whether the WRCAP DB 8b1c58975305 differs from 8a8cd9c5d06c in content or only in bytes.
- The true total GRT overflow of shelf_we (reports are capped at 20,000 gcells).

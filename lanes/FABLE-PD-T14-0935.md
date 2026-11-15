# FABLE-PD-T14-0935: S81 leaf t14 GRT residue 139, ft5 forms A/B, class (2026-11-15 10:15 PST)

Read-only review. Tool runs: two OpenROAD read-only dumps of the r2 `4_cts.odb` (ro mount, ot-run on epyc10, outputs in epyc10 `/srv/opentallas-scratch2/claude/fable-pd-t14-0935/`). Nothing launched, stopped or changed.
MEASURED = r2 / p1 reports, DBs, kits, plans. INFERENCE is marked. "p1" is the run COORD calls r3: epyc7 `s81-leaf-t14/kit/p1` (E2 t14 row).

## 0. Verdict

1. **Layer budget is the first cause on the B6gE base, and it is a class regression.** `B6gsl_or13_rp` carries `die.layer_budget.type_m8_grant.types` = 24 col_h9_r0 types. `m8_grant.grant_config` reads `OT_GEN_M8_GRANT=1` only when the plan key is absent, so since B6b (11-14) every other type lost M8. r2 (kit generated 11-14 13:57) has the grant (M2-M8); p1 has `MAX_ROUTING_LAYER = M7`, no `m8_grant.json`. Wave check: 8 of 8 leaf kits of 11-14 (src 7073a6b4) have the grant; the current wave tree 3fa87b84 has it on 12 of 86 kits, all col_h9 (leaf t27, t30, t42 are M7).
2. **The 139 in r2 is a repeater pit at the ve_s / ve_m slot, not slot width for the stations themselves.** The slot holds 1,667 station flops and 3,616 buffers. 2,125 nets cross the ve_m west edge and 1,925 the ve_s east edge on the only over-core H layers (M6 + M8). Peak 233 nets per 20 um against about 280 tracks (83 %).
3. **r2 never tested the ft5 move.** `ft_stations.txt` was edited, `ft_bit_sites.tcl` was not: 536 ft5 last-station flops are still in the slot (MEASURED, placed DB).
4. **p1 fails for two reasons of its own:** no M8, and the ft5 S2 band placed in the mouth of the 34.56-um gap between ve_m top and vq bottom. It says nothing about the slot fix.
5. Forms A and B both close on track supply but cost +1 cycle on ft5. The cheaper arrangement is form R (section 4): three stations, S2 east of ve_m, with the M8 row. Build A/B/R with M8 or the comparison repeats p1.

## 1. Track supply (MEASURED from the congestion reports, per 0.57-um gcell)

| where | H | V |
|---|---|---|
| free rows, all layers to M7 | 24-26 (44 per um) | 26-28 (47 per um) |
| over a hard core, M8 granted (r2) | 5-9, mode 8 (14 per um) | 6 (M7 only, 10.5 per um) |
| over a hard core, no M8 (p1) | 0-3, mode 3 (5.3 per um) | 6 |

Core OBS is M1-M5; pins on M4 / M5. M8 grant = 13,616 of 15,984 tracks. Caps are read on overflow cells only (selection bias possible; the r2 and p1 modes are 986 and 4,304 cells).

Bus pitch: ft0 (1,104 bits, E to W, y 6-246) and ft5 (1,104 bits, W pins y 247-487) are 4.6 bits per um. Both must cross 172.8-um cores to reach the W face. Against over-core H: 33 % with M8, **87 % on M6 alone** before any other net. M9 is vertical and does not help.

## 2. r2 residue (congestion-15.rpt, pass 3)

135 cells, 139 over, all +1 or +2:
- 68 H cells, x 216-228 (first 12 um over the ve_m west edge), y 113-176 and 245-293; 7 more over the ve_s east edge.
- 50 V cells in one gcell row y 1208.97, x 175-241: ft2 input landing (`u_cland_ft2_i`), cap 26-28, +1. Marginal, pin landing row.
- 17 V cells in the slot at y 93-98 and 225.

Slot content (r2 placed DB, x 207.47-216.11, y 43.2-380.2, util 0.44): flops ft0 S5 904, ft5 S3 536, ft2 S4/S5 227; buffers ft2 1,376, ft0 1,283, ft5 643, ft4 233.

Nets crossing the ve_m west edge, per 20-um band of y (capacity about 280 at 8 per gcell, 175-210 where cap is 5-6):

| y band | ft0 | ft2 | ft4 | ft5 | total |
|---|---|---|---|---|---|
| 120 | 94 | 0 | 68 | 0 | 163 |
| 140 | 90 | 20 | 44 | 0 | 154 |
| 160 | 93 | 140 | 0 | 0 | 233 |
| 180-220 | 91 | 0 | 0 | 0 | 92 |
| 240 | 36 | 0 | 82 | 50 | 168 |
| 260 | 0 | 50 | 43 | 93 | 186 |
| 280 | 0 | 115 | 0 | 94 | 211 |
| 300-340 | 0 | 0 | 0 | 91 | 94-108 |

- ft0 and ft5 are the bus baseline, 91-94 per band (33 %).
- The peaks are ft2 and ft4: their S-to-N hops run 345.6 um over ve_m on M7 (ft2 x 222-274, 228 bits; ft4 x 275-401), the resizer needs repeaters at 1/3 and 2/3 of the hop (y about 150-170 and 260-280), and the slot is the only row area in reach. Median far-end offset of those nets: 120 um in y. The overflow sits exactly in those two bands.
- Not pin access (no overflow inside the slot on H; V in slot 18-27 cap, 17 cells +1). Not slot V supply after iteration 10 (iteration 5: 22,206, of which V over ve_s 13,306 and over ve_m 7,592; gone by iteration 10).

## 3. p1 (E2 t14 row, M7)

12,804 at iteration 5, 13,747 at iteration 10 (r2: 22,206, 461). The slot is clear (20 over). Overflow: 4,830 in x 340-440, y 380-445 (ve_m top / vq bottom gap; 2,345 of the 3,830 cells there are free-row cells with cap 17-26, the rest are cap 0-3 over cores) and 4,198 in x 300-360, y 440-620 (u_vs east edge and the 8.66-um u_vs / vq slot: ft4 S2 to S3, 220 um over cores, same repeater pattern).
Gap arithmetic: ve_m now ends at x 423.5, vq starts at 354.4, so the 34.56-um gap is 69 um long (34.5 in r2). H supply 34.56 x 44 = 1,516 tracks; ft5 alone is 1,104 = 73 %, with the 1,105-flop S2 band (x 417-460, y 393-407) and the ft4 S2 band (y 388-394) inside it, and nothing can spill over the cores at 5.3 per um. With M8: 1,820 in the gap (61 %), plus 14 per um over the ve_m top rows (46 % with a 40-um strip). INFERENCE: r2 passed this gap with all 1,104 bits (0 overflow cells there at iterations 10 and 15) with M8, the short overlap and S2 east at (499.66, 368.96).

## 4. ft5 forms (E2 geometry: ve_m 250.67-423.47, u_vs y 440.68-613.48, vq 354.37-527.17 x 423.4-553.0)

| form | path | worst cross-section | use, M7 only | use, with M8 | stations |
|---|---|---|---|---|---|
| p1 | all bits through the gap, S2 in the mouth | 34.56 um gap, 1,516 H | 73 % + station bands: fails (measured) | 61 % | 3 |
| A | S2 north of u_vs, y > 613 | vq-to-vn_a channel 69 um: 3,240 V; vq top to rxsf 82 um: 3,600 H; u_vs top to vsw 60.5 um: 2,660 H | 34 / 31 / 42 % | lower | path 1,449 um against 893 direct: 3 stations leave 388-um hops (limit 405, no slack), so 4 stations, +1 cycle |
| B | split, half through the gap, half north | gap 552 of 1,516 | 36 % | 30 % | bus latency is one number: both halves take the 4th station, +1 cycle |
| R | all through the gap, S2 east of ve_m at about (470, 372), band x 450-490, y 300-388; S3 (147.56, 425.92) as E2 | gap | 73 %: not allowed | 61 % gap alone, about 46 % with the ve_m top rows | 3; hops 141 and 376 um |

- A: supply is fine even on M7, but it crosses the ft2 S3 and ft4 S3 station rows (y 590-635) and adds 556 um and one cycle. Use only if R fails.
- B: lowest peak, most rows, same +1 cycle as A. Right fallback if the M8 row is refused.
- R: no latency change; it is the r2 arrangement that already passed this gap, with S3 moved out of the slot for real. Needs the M8 row.
- All forms: 612 of the 1,104 W pins (y 247-380) sit behind ve_s. They are reached over ve_s (H at the pin edge 33 % with M8, 87 % without) or down the 30.3-um W strip (1,426 V tracks; 612 + ft1 276 = 62 %). This alone needs M8 for t14.

## 5. Fix rows on `B6gsl_or13_rp` (apply with the E2 rows; one compose last)

1. Die row (DIE-S81-92, `die_rows`): `die.layer_budget.type_m8_grant.types` = `null` (every placed type gets the leftover M8, as all kits had under the env switch until 11-14). Minimum form if the full list is refused: the 24 current types + `ot_s81sl_leaf__t14` + the x-slot class of section 6 (t58, t65, t22, t2, t9, t73, t32). Key is a whole list: later setters list it in `overrides`.
2. t14 partition row = the E2 row as posted (`u_lf.u_ve.u_m` origin 250.56, 43.2; `u_lf.u_vs` 172.8, 440.64; ft5 S3 at 147.56, 425.92; five stages out of u_vsw / vn_b), with one change: `ft_slots[ft5].regs_um[2]` = (470.0, 372.0) and its `bit_sites_um` re-banded in x 450-490, y 300-388 (was (440, 400), band x 417-460, y 393-407). Expected slot-edge peak after the row: 93 + about 65 (ft2 105 of 228 bits left over ve_m) = about 160 per 20 um = 57 %; ft5 bands 0. INFERENCE until built.
3. Proof before bind counts it: one place + GRT of that row with the grant in the plan copy (not the env), pass = 0 overflow inside pass 1. Check that `ft_bit_sites.tcl` moved, not only `ft_stations.txt`.
4. Owner lane: p1 cannot pass (M7); cancel it. Forms A and B built on the same tree are M7 too.

Not needed: more slot width than 43.2 (ft2 668 bits in 43.2 um = 33 % of V), M9, moving ft0 S5 (its 4.6 per um is the bus pitch; it crosses both cores wherever the station sits).

## 6. Same pattern in other leaf types (screen on `e2/rp/E2rp.json`, script epyc7 `/srv/opentallas-scratch2/claude/fable-pd-t14-0935-screen.py`)

Screen: station flops (at least 100) in a slot of at most 45 um between two cores at least 100 um deep, whose previous or next point lies across a core. Demand = flops per um of slot at the peak 20-um band, against 14 per um (x-slot, H, M6+M8), 5.3 (H, M6 only) or 10.5 (y-slot, V, M7 only; M8 does not help). Calibration is t14 only: baseline 34 % became 83 % with repeaters and left 139. 20 types flagged; all are M7 on the B6gE base.

| type | slot | gap um | flops | per um | use |
|---|---|---|---|---|---|
| t65 | vsw / vs (y) | 25.92 | 1,105 | 21.6 | 206 % of M7 |
| t56 | vs / ve_m (y) | 25.92 | 554 | 21.2 | 202 % |
| t34 | ve_s / vsw (y) | 43.2 | 669 | 20.6 | 196 % |
| t32 | vn_a / vn_b (y) | 17.28 | 598 | 20.1 | 191 % |
| t61 | vsw / ve_s (y) | 17.28 | 1,267 | 15.5 | 148 % |
| t23, t62, t67 | ve_s / vsw or vs (y) | 17.28-25.92 | 598 | 13.9 | 132 % |
| t1 | ln7 / ln3 (y) | 23.76 | 568 | 11.5 | 110 % |
| t58 | ve_m / vsw (y) | 17.28 | 574 | 10.2 | 97 % |
| t68, t24__cl2456157b | ve_s / vsw, ve_s / vq (y) | 25.92 | 550, 510 | 10.0 | 95 % |
| t38 | vs / ve_m, vsw / vs (y) | 17.28, 8.64 | 425, 175 | 9.2, 8.8 | 88 %, 84 % |
| t58 | ve_m / ve_s (x) | 43.2 | 929 | 7.6 | 54 % with M8, 142 % without |
| t65 | ve_m / ve_s (x) | 43.2 | 138 | 6.3 | 45 %, 119 % |
| t14 | ve_s / ve_m (x) | 43.2 | 891 | 4.7 | 34 %, 89 % |
| t2, t35, t59, t37, t16, t41 | lane-core slots | 15-32 | 154-439 | 4.5-7.5 | 43-71 % of M7 |

The y-slot rows above 100 % have station bands packed denser than M7 over the core can feed: spread each band along the slot to at most 6 flops per um (60 % of M7) or put the stage at the core corner. Bands in a slot whose bus runs along it (t22 3,026, t2 2,915, t9 2,362, t73 1,693 flops in the ve slot) cross no core edge and are not flagged, but any S-N bus over ve_m or ve_s next to them will drop repeaters there as in t14.

Station rule for the family: no hop longer than about 170 um over a core (one core depth, unbuffered); a bus that must run 345 um beside the ve pair goes in a slot sized bits / (47 x 0.6) um plus repeater columns; cross-slot stations at most 6 flops per um of slot (V) or 8 (H, with M8).

## 7. GRT extra-iteration form: stop list

r2: 5 passes in 4 h 40 min (10:29-15:09 UTC), ended at iteration 15, 11, 15, 11, 14 of 30. Each pass stops early, GRT-0273 drops the NDR of one clock net (9,022 clock nets) and routing restarts from zero; every pass repeats about 22,000 / 460 / 140. Clock nets are in 6 of the 135 residue cells.
- Stop after pass 1: a GRT-0273 line = design verdict, kill the job. Never run pass 2 or later.
- Early stop inside pass 1: overflow at iteration 10 above about 1,000, or rising from iteration 5 to 10 (p1), = fail now.
- A residue under about 200 at iteration 15 is still a structural verdict (one cut at 80-85 %), not a retry case.

## Not verified
The E2 row + R + M8 has no build. Over-core caps are from overflow cells. The class screen is geometric (no placed DB per type). Whether DIE-S81-92 restricted the grant list on purpose in B6b (plan note names only the col_h9 grant).

# FABLE-PD-S81-0720 2026-11-17 07:20 PST: S81 strip t34 GRT-0116 and col pg3 DRT-1231

Reviewer: FABLE-PD-S81-0720 (Fable). Read-only on builds. Technical PD only.
Marking: **V** = I opened the DB / log / report myself. **I** = inferred from V data, not directly observed. **R** = reported by a lane.
Probe outputs: intel1 `/srv/opentallas-scratch/claude/fable-pd-s81-0720/probeA_t34.txt`; epyc8 `/srv/opentallas-scratch2/claude/fable-pd-s81-0720/probeB_*.txt, probeC_*.txt` (ot-run, DBs mounted read-only).

## Summary

- **Strip t34: the overflow is one place, the 30.4-um west seam between the core edge and VE_m, and it is feedthrough bits, not clock NDR and not relay columns.** Five ft slots (1,766 station flops) share 1,952 raw vertical tracks. Form-B does not touch this geometry, so form-B t34 will fail the same way unless the plan moves VE_m / VE_s east by 25.92 um or more. Form-B t62 is not exposed (its VE_m sits at x 181.6).
- **Col pg3 DRT-1231: not a blocked pin and not HB4 density.** The hold-repair path wrote its GRT DB with the 3,967 temporary PG-track GRT obstructions still in it. Detail route then saw 15,736 static M5 / M6 / M7 spacing violations, opened every box on the die each pass, and hit a box-edge case on a flop M2 pin bar 234 um from the nearest hold buffer.
- The route-only retry on E8 does not have that defect and is converging: 686 -> 601 -> 600 -> 52 -> 46. The 49 left are M5 shorts made by the temporary M5 block over t6, not by the hold cells.
- For the 63 members the clean fix is to close both items before the first route (hold margin at pre-GRT / GRT, M5 block over the sstn core from floorplan), so no member needs a post-route ECO.

## A. Strip t34 (tapfix1, GRT-0116, overflow 3,516)

### Evidence (V)

Kit: intel1 `fable-fix-s81-cong/countable_F2s4tapfix1_eight/gen/ot_s81sl_leaf__t34`; `5_1_grt.log`, `congestion.rpt`, `congestion-10.rpt`, `grt/congestion.png`, guides of `5_1_grt-failed.odb` (184,471 nets, 2,430,856 guides).

| item | value |
|---|---|
| Final per-layer overflow | M6 2,199, M8 1,254, all other layers 63 |
| Final overflow gcells (2D report) | 222; 194 of them at x 30-45, y 100-200 and 275-350; 19 at x 885-950, y 325-350; 11 at x 625-640 |
| Nets in those gcells | ft2 stations 5 / 6: 966; cland_ft3 ring: 393; ft1 station 4: 320; ft0 station 4: 301; clock nets: 12 (10 distinct of 2,735); reset: 3 |
| Seam | x 4.32 to 34.692 (VE_m west edge), y 77.8 to 423.4: 30.37 x 345.6 um |
| Seam tracks, raw | M3 844 + M5 633 + M7 475 = 1,952. GRT capacity after PG derate: 26 per 0.57-um gcell = 1,385 |
| Station flops inside the seam | 1,766: ft2 669, ft0 277, ft1 277, ft4 277, ft3 266. Reset relays: 2. Cell use 15.7 % |
| Vertical guides crossing a cut inside the seam | y 120: 1,541; y 160: 1,569; y 250: 1,471; y 330: 1,605; y 400: 1,451 (M3 703-772, M5 455-511, M7 290-327) |
| Vertical guides spilled over VE_m on M7 at the same cuts | 447, 396, 558, 417, 465 |
| Horizontal guides crossing the VE_m west edge (345.6 um) | M6 2,032 + M8 1,838 (M2 / M4 are blocked by the macro) |
| Edge capacity where it overflows | 5 to 8 tracks per gcell (M6 + M8 after PG), usage 7 to 9 |
| NDR | GRT dropped it on one net, `clknet_0_clk_t31` |

The kit already flagged it: `ft_track_use.json` has ft0 / ft1 / ft4 at 0.827, ft2 at 0.894, ft3 at 0.68 against a 0.5 target, per slot and advisory.

### Root cause

The five slots ft0 to ft4 all turn down the same 30-um seam. Demand at every cut is 1,900 to 2,030 vertical wires (seam + spill) on 1,952 raw tracks, which is 98 to 104 % of raw and about 140 % of what GRT can use. The quarter that does not fit rides M7 over VE_m. To get there each wire crosses the macro edge on M6 or M8, the only horizontal layers over the macro, and that edge holds 5 to 8 tracks per gcell. The M6 / M8 overflow is that edge, peaking at the station rows (y 100-175 and 275-350, 10 to 11.5 crossings per gcell). Low die-wide use (7.4 %) is consistent: the rest of the die is empty.

Second place, minor (V): at iteration 10 the worst gcells were the east mouth of the VN_a / VN_b channel (x 920-935, y 330-355, usage 15 on capacity 6; `cst_vni_gd` and `vn hq_d` buses in a 21.6-um channel). By iteration 30 it was down to 19 gcells. Not a fix item yet.

### Will form-B remove it? No (I)

Form-B is XR on the vpw inputs, the vpw bank placement and the GPL setting. None of them moves VE_m, the ft stations or the ft bit count. I did not open the C4 plan; if `macro_place.tcl` of the new t34 kit still has `u_ve_u_m` at x 34.692 and ft0 to ft4 stations at x 19.7 to 34.6, the GRT result is known before it runs.

### Fixes, ranked

| # | fix | numbers | owner |
|---|---|---|---|
| A1 | Plan row for t34: move VE_m and VE_s east together, shape unchanged | +25.92 um gives a 56.3-um seam: 1,766 bits on 2,567 usable tracks = 69 %. +34.56 um gives 64.9 um = 60 %. VE_s east edge lands at 414.9 or 423.5; VN starts at 570.4, so the channel stays over 145 um. VSW (x from 259.3) and VS (y from 440.7) are clear. 0 flops, 0 cycles, hop lengths unchanged | S81-DIE-R3 |
| A2 | Spread each station over the seam width as columns, not one stack at x 19.7-34.6 | With A1: 669 ft2 bits over 56 um is 12 per um of height instead of 22 | S81-DIE-R3 (bit sites), S81-TYPES-R-STRIP (kit) |
| A3 | Make the ft track check a blocking pre-GRT read per channel, summed over all slots in the same channel | Fail above 0.70 of GRT-usable vertical tracks (45.6 per um of width at this PG derate). t34 today: 1,766 / 1,385 = 1.28 | S81-TYPES-R-STRIP |
| A4 | Run A3 over the 74 strip leaves from the plan before C4 seals | t75 is the next candidate (VE_m at x 43.3, ft2 and ft4 stations at x 17-22). t62 / t72 / t47 / t28 have VE_m at x 181 or more and are not in this class | S81-DIE-R3 |
| A5 | Form-B t62 goes ahead as the pilot. Form-B t34 waits for A1 or runs only as a known GRT failure | none | S81-DIE-R3 |

## B. Col pg3 (col_h9_r2, 63 members released)

### Evidence (V)

| item | host, path | result |
|---|---|---|
| Repair run log | epyc8 `fable-fix-s81-col/pg3_hold_m5_mm2_1117/run_prd.log` | Line 73: `OT_PG_TRACK_TRUTH add 3967 temporary GRT obstructions M5=2896 M6=740 M7=331`. No `removed` line before `write_db 5_1_grt.odb`. The first-route log of the same kit has `removed 3967 ... before 5_1_grt.odb is written` (run_route.log line 4255) |
| Obstructions in the DBs | probeB | First route `5_2_route.odb`: M8 2,268 only. Repair `5_1_grt.odb`: M8 2,268 + M5 2,897 + M6 740 + M7 331. Route-only retry `hei_grt.odb`: M8 2,268 + M5 1 |
| Repair detail route | run_prd.log | Pass 0: 15,889 violations, of which Metal Spacing M5 9,992 / M6 4,670 / M7 1,073. Pass 1: 15,801, the same three counts (9,991 / 4,672 / 1,073). Pass 2: DRT-1231 |
| The pin | probeC, all three DBs identical | `o[16]` is DFFASRHQNx1 at (399.492, 820.26). RESETN is the functional reset, net104226, 43 pins, driver `place104227`. SETN is the tied pin, on a private TIEHIx1 (net2953, 2 pins). RESETN has 2 M1 and about 24 M2 access points; the pin is an M2 bar at x 400.124 to 400.559 |
| The wire on the pin | probeC | The kept M2 wire enters the bar from the west, is split at (400.140, 820.413) and ends at (400.149, 820.413). 400.140 = 702 x 0.57, a gcell line |
| Access-point catalog | probeC | Same in all three DBs (63,318 block points, per-master digests equal). 0 pins without a preferred point in 256,194 checked |
| Hold buffers | probeB | 0 overlaps, 0 off-row. Nearest hold buffer to the pin: 233.6 um |
| DRT source | OpenROAD `FlexDR_init.cpp`, `initNet_term_helper` | DRT-1231 is raised when a pin is pulled into a worker box by a wire end lying on its shape and none of the pin's access points is inside that box |
| Route-only retry | epyc8 `pg3_hei_route1117/route.log` | 686 (M1 spacing 170, M2 spacing 370, M5 short 50) -> 601 -> 600 -> 52 (M5 short 49, 3 other) -> 46 at 90 % of pass 4 |
| Original 2 shorts | `5_route_drc.rpt` | Both M5, `net155735` against `u_u_t6` at (741.5, 49.1) and (741.6, 54.9). net155735 does not connect to t6 |
| t6 abstract | `macros/ot_s81_sstn_base566.lef` | 84.24 x 30.24 um, obstruction as 817 separate M5 rectangles (754 on M4, 642 on M3), not a full block |
| Hold ends | `internal_hold.tsv`, run_route.log 2787-2790, 4158-4172 | 57 ends, worst -7.61. 50 start at hard-core `u_s13` outputs (cfg 33, f_prog 17) into the adjacent boundary flops. Pre-GRT pass closed at +4.90 with a 5-ps same-tap margin; GRT repair ran at margin 0 and closed at +0.29; routed -7.61. Setup room on these ends is 690 ps or more |

### Root causes

1. **DRT-1231 (V for each step, I for the link between them).** The repair path adds the PG-track GRT obstructions and never removes them. The kept wires that sit next to PG stripes then violate spacing against obstructions on M5 / M6 / M7: 15,736 violations that no pass can clear. Every worker box is dirty, so every box is rebuilt each pass. In pass 2 the box grid put an edge on gcell line x 400.140, exactly where a kept wire is split on the RESETN M2 bar. The pin came into the box through that wire end with its access points on the other side. The pin is not blocked, the catalog is not stale, and no hold buffer is near it.
2. **686 early violations in the retry.** 540 of them (M1 / M2 spacing) cleared by pass 3: local re-access around the 78 new cells. The 49 to 52 that stay are M5 shorts, and they appear in both runs from pass 0. The original DB had 2. The only M5 change is the 76 x 26 um temporary block over t6, so these are kept M5 wires that were legal before the block (I).
3. **Why every member needs a hold repair.** The flow closes internal hold to +5 ps on placement RC and to 0 on GRT RC, then loses 8 to 12.5 ps in detail route. 50 of 57 ends are one class: a hard-core output into its first flop.
4. **Why the 2 M5 shorts exist.** GRT sees free M5 tracks between the 817 obstruction rectangles of the sstn core; detail route cannot use two of them.

Not causes: tied RESETN pins blocked on M1 (RESETN is driven; SETN is tied and reaches its TIEHI on M2 / M3 cleanly), HB4 density near the reset pack, pin-access settings.

### Fixes, ranked

| # | fix | numbers | owner |
|---|---|---|---|
| B1 | Repair path: remove the PG-track obstructions before `5_1_grt.odb` is written, as the first-route path does. Add a check before detail route: obstruction count per layer equals the seed's | pg3: M5 / M6 / M7 must be 0 (seed has M8 2,268 only). Removes 15,736 static violations | S81-TYPES-R3 (flow change with TOOLS-CONVERGE) |
| B2 | Members not yet at GRT: close internal hold before the first route. Same-tap margin 5 -> 15 ps in the pre-GRT pass, GRT repair margin 0 -> 10 ps (`OT_HOLD_FF_MARGIN`), and price hard-core output starts with the cross-tap guard | Measured loss placement -> routed 12.5 ps, GRT -> routed 7.9 ps. Setup room 690 ps. Cell count not measured; the pre-GRT pass already places 2,485 | S81-TYPES-R3 |
| B3 | Members not yet at floorplan / GRT: M5 routing block over every `ot_s81_sstn_*` core interior from floorplan on, the same inset the lane used (4.0 um in x, 2.0 um in y) | From-scratch route: 0 kept wires to collide. Check the pin audit still passes 1,490 / 1,490 | S81-TYPES-R3 |
| B4 | pg3 now: let the E8 route-only retry run. If it stalls above 0 on M5 shorts, drop the blanket block and re-route only `net155735` with a block over the two marker boxes | 49 shorts today, falling 52 -> 46 | S81-TYPES-R3 |
| B5 | Members already routed with the same two defects: route-only hold insert (the E8 form) with B1 in place; no full re-route | 78 cells, 56 nets per member on pg3 | S81-TYPES-R3 |
| B6 | Report DRT-1231 upstream as a box-edge case on a planar M2 pin bar; no local work-round needed once B1 is in | 1 pin in 256,194 | TOOLS-CONVERGE |

## Stop list

- Do not route form-B t34 on the current floor expecting a different GRT result; the seam is unchanged.
- Do not tune GRT (more iterations, layer adjustments, NDR off) for t34; 30 iterations already ran and the limit is geometric.
- Do not remove reset from the tied flops in RTL, add hold-buffer keepouts, or change pin-access settings for col; none of them is the cause.
- Do not wipe or recompute the access-point catalog for the pg3 retry; it is identical to the first route's.
- Do not rerun the `pg3_hold_m5_mm2` form (prd path) on any member until B1 is in; it fails the same way on every kit with PG-track truth on.
- Do not add a blanket M5 block to a routed DB; put it in before the first route (B3).
- Do not launch per-member post-route hold repair on members that have not reached GRT; apply B2 instead.

## Not checked

- The C4 plan itself (t34 VE_m site and ft stations in form-B).
- Which worker box raised DRT-1231; the box edge at x 400.140 is derived from the wire split point and the DRT source.
- How many cells B2 adds, and whether the 50 hard-core starts are priced as same-tap today.
- Whether the 63 members share the two t6 shorts; pg3 is the only routed h9_r2 DB I opened.
- t75 seam load (flagged from station coordinates only).

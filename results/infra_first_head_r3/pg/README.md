# INFRA-FIRST-HEAD-3 PG (task 4): s81_head worst-case power from the head netlists + PDNSim wider-M9 sweep

Plan physical/die_plan/s81_head/die_plan.json sha256 674a8ac9 (read-only; the plan is not edited).
Tools: `tools/s81_head/head_pg_power.tcl` (OpenSTA report_power), `tools/s81_head/head_pg_sweep.py`
(power / sweep / psm; it wraps `tools/die_plan/infra_pg.py` estimate + window_kit). Run dir:
intel2:/srv/opentallas-scratch2/claude/infra-head3-1027/pg. Power probes ran in docker (16 GB cap) at
epyc2/intel1:/srv/opentallas-scratch2/claude/infra-head3-1027/pg/elem{B,A}. PDNSim ran via ot-run on intel2 at 8 GB / 8 threads.
The PSM kits are in pg/psm/<cand>_tf. Evidence is in data/.

## 1. Head worst-case power from the head netlists
**Inputs:**
- Netlists: the hold2 GRT views 5_1_grt.odb of ot_s81hd_elemA_cv / elemB_cv (head-core-r10/elem{A,B}_hold2, copied read-only). Their sha256: A 30ee676a..., B 5511e3d2....
- Analysis: TT RVT NLDM + ot_rom_4096x274_m8_tt.lib, estimate_parasitics -global_routing with rc_cal 0.8/0.9, and propagated clock at 833 ps.
- Activity: `set_power_activity -global/-input -activity A -duty 0.5`.
- Assumption: the ROM is clocked every cycle, with no CE credit.

| core | cells / regs | area mm2 | P @0.5 W | P @0.2 W | W/mm2 @0.5 |
|---|---|---|---|---|---|
| elemA (319.68^2) | 134524 / 28723 | 0.1022 | 0.1487 | 0.1049 | 1.455 |
| elemB (285.12^2) | 120273 / 25983 | 0.0813 | 0.1370 | 0.0977 | 1.686 |

**Breakdown at 0.5:**
- elemB: seq 60.1, comb 37.7, clock 20.5, ROM 18.8 mW.
- elemA: seq 66.1, comb 42.5, clock 21.3, ROM 18.7 mW.

About 80 % of the 0.2-activity power does not depend on activity: the flop clock pins, the clock tree and the ROM internal power. So even a low data activity leaves the head at about 0.85 W/mm2 or more.

**hd_tile = 4 x elemA + 1 x elemB:**
- Cores: 0.7318 W on 0.4901 mm2 (1.493 W/mm2).
- Glue (0.2445 mm2) has no glue netlist, so it is bounded:
  - upper bound = glue at the 5-core average density (S81-HEAD gives ~1.07M cells/tile against 0.658M in the cores);
  - lower bound = 0 W.
- Tile: **1.493 W/mm2 upper (1.097 W/tile) / 0.996 W/mm2 lower**. At activity 0.2 it is 1.055 / 0.704 W/mm2.
- 264 tiles therefore draw 289.6 W at the upper bound.

The other head types (spine, stations, serdes strip, ctl/host/mesh/lep0N) have no netlist. They are charged at the tile upper bound (ASSUMPTION, conservative). The SerDes PHY windows are 4.37 W/macro on their own VDDPHY domain, which is not re-verified here.

**This is 4.6x the R1 borrowed basis** (S81 84.1 W/die -> 0.3257 W/mm2). The R1 conclusion that 0.48@4.32 / 0.48@1.728 gives 34.34 mV is void at the head's own power: the same model gives 157.4 mV, and 157.37 / 34.34 = 4.58 = 1.4933 / 0.3257, so the model is linear.

## 2. PG sweep (gate = core VDD drop <= 35 mV = 5 % of 0.7 V; activity 0.5, upper bound 1.4933 W/mm2)
- The analytic sweep is `infra_pg.estimate`, die-wide, core region (data/sweep_*.json).
- Grid notation is width@pitch per net (VDD at pitch/2, VSS at pitch).
- Track share uses `infra_pg.track_frac` (ASAP7 SPACINGTABLE: 0.5 um for width >= 0.5, 1.0 um for width >= 1.0).

Clock lane (VSS-locked, QC R14 form):
- A 16W trunk (0.64 um) or a 2x16W trunk (1.28 um) sits in a VSS-adjacent half-gap, at 0.5 um wide spacing to both stripes.
- max_jog is the distance from an island coordinate to the nearest legal lane centre. The island x mod 8.64 is {0, 4.32} (column pitch 177.12 = 20.5 x 8.64) and the island y mod 8.64 is {4.32}.

| grid M8 / M9 | bumps um | M8 % | M9 % | IR model mV | M9 16W lane | M8 16W lane |
|---|---|---|---|---|---|---|
| plan-R1 0.48@4.32 / 0.48@1.728 | 150 | 29.4 | 70.1 | 157.4 FAIL | NO (gap 0.384) | yes, jog 1.06 |
| best at 150: 0.48@4.32 / 12.96@34.56 | 150 | 29.4 | 85.7 | 75.4 FAIL | yes, jog 4.32 | yes, jog 1.06 |
| 1.92@8.64 / 3.84@8.64 (metal-max) | 150 | 91.1 | 99.0 | 69.4 FAIL | NO | NO |
| 0.48@4.32 / 4.32@17.28 | 100 | 29.4 | 72.9 | 45.8 FAIL | yes | yes |
| 0.48@8.64 / 6.48@34.56 | 75 | 14.6 | 48.3 | 27.3 | yes, jog 4.32 (gap 10.8) | yes, jog 2.16 |
| **0.48@4.32 / 6.48@34.56** | **75** | **29.4** | **48.3** | **20.4** | yes, jog 4.32 (gap 10.8; 2x16W also fits) | yes, jog 1.06 |
| 0.48@4.32 / 0.48@1.728 | 75 | 29.4 | 70.1 | 33.3 | NO | yes |

Two findings:
- **No M8/M9 grid meets 35 mV with 150-um C4 power bumps at the measured head power.** The best case is 69.4 mV with M8/M9 about 100 % metal. Above ~3.8 um the drop is bump-spreading limited: the coarse term is about 2/3 of it.
- **Fewer, wider M9 stripes beat the 0.48 fine grid.** At 75-um bumps, 6.48@34.56 gives 20.4 mV at 48 % of M9, against 0.48@1.728 at 33.3 mV and 70 % of M9. They also open 10.8-um gaps, so the 16W and 2x16W clock lanes fit. The fine grid's 0.384-um gaps cannot hold a 16W trunk.

The 16W clock lanes themselves take about 0.7 % of M9 (~70 island/turn/spine columns x 1.64 um / 17.52 mm) and about 0.4 % of M8 (~38 rows).

## 3. PDNSim (OpenROAD analyze_power_grid)
Setup:
- Tile-field window [3801.6, 6704.64, 5287.68(5296.32), 8190.72(8199.36)], about 1.49 x 1.49 mm (snapped to the grid pitch).
- 1.4933 W/mm2 uniform, about 3.30 W in 86.4-um load blocks.
- Window-local C4 at 150 or 75 um; open window edges (no feed from outside), as in the infra_pg window form.
- Clock lanes are not drawn; they take no PG metal in this grid.

| cand | grid M8 / M9 | bumps | PDNSim worst mV | interior (>= 300 um from edge) | model (same window) | check_power_grid | verdict |
|---|---|---|---|---|---|---|---|
| C0b150 | 0.48@4.32 / 0.48@1.728 (R1) | 150 (50 VDD) | 170.0 | 138.0 | 176.8 | VDD+VSS OK | FAIL |
| C1b150 | 0.48@8.64 / 6.48@34.56 | 150 | 145.0 | 109.9 | 176.5 | OK | FAIL |
| C2b75 | 0.48@8.64 / 6.48@34.56 | 75 (200 VDD) | 34.2 | 31.9 | 32.9 | OK | PASS (0.8 mV margin) |
| **C3b75** | **0.48@4.32 / 6.48@34.56** | **75** | **24.5** | **22.4** | 25.2 | OK | **PASS (10.5 mV margin)** |

The model agrees with PDNSim to 4 % (C0, C2, C3) and is pessimistic on C1.

## Recommended grid (candidate; needs a package decision)
**M8 0.48 @ 4.32 (29.4 % of tracks) + M9 6.48 @ 34.56 (48.3 %), with core power C4 at 75 um.**
- PDNSim gives 24.5 mV against the 35-mV budget at worst-case (activity 0.5, glue upper bound) head power.
- The M9 VSS-locked lanes have 10.8-um gaps, so 16W and 2x16W trunks fit (max jog 4.32 um). The M8 lanes give a 1.06-um jog, as in QC R14.
- About 22 % of M9 and 70 % of M8 tracks are left for the 12.1c leftover die signals.

The plan's 150-um bump lattice cannot deliver the head's power at 35 mV with any M8/M9 grid. Possible ways forward:
- (a) 75-um core power bumps over the head (a package/bump-map change);
- (b) a lower worst-case activity basis (an owner call: even 0.2 activity with zero glue power is 0.70 W/mm2, which is still about 74 mV at the R1 grid / 150 um);
- (c) a design-side power cut (clock gating of idle head tiles or the ROM CE).

OWNER?/COORD.

## Numbers
| number | value | status |
|---|---|---|
| elemA / elemB power @0.5 | 0.1487 / 0.1370 W | UNCHECKED (own OpenSTA run; report files data/rpt) |
| elemA / elemB power @0.2 | 0.1049 / 0.0977 W | UNCHECKED |
| hd_tile density @0.5, upper / lower | 1.493 / 0.996 W/mm2 | CHECKED (arithmetic from the two reports; glue bound is an ASSUMPTION) |
| 264 tiles, upper | 289.6 W | CHECKED (arithmetic) |
| R1 grid at head power (model) | 157.4 mV FAIL | UNCHECKED (tool); linear scaling CHECKED |
| best M8/M9 grid at 150-um bumps (model) | 69.4 mV FAIL | UNCHECKED |
| PDNSim C0 / C1 (150 um) | 170.0 / 145.0 mV FAIL | UNCHECKED (PSM log) |
| PDNSim C2 / C3 (75 um) | 34.2 / 24.5 mV PASS | UNCHECKED (PSM log) |
| C3 track share M8 / M9 | 29.4 / 48.3 % | UNCHECKED (infra_pg.track_frac) |
| 16W lane fit C3, M9 / M8 jog | 4.32 / 1.06 um | UNCHECKED (own lane model) |

Not done:
- the PHY VDDPHY windows at head power (not re-run; R1 basis 4.37 W/macro);
- the VSS drop;
- full-die PDNSim;
- a run with the clock lanes drawn;
- per-type power for the non-tile types (no netlists).

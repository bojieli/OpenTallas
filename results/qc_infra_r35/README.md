# INFRA-FIRST-QC-R35 (2026-10-27 19:50-20:20 PDT): M8/M9 clock-row reservation for the QC PER-SLICE clock form

Scope (12.13f, narrowed): the die-wide QC clock work has stopped. This lane delivers only the class reservation that
COORD ruled in QC-R34 (A) and QC-SLICECLK-2 (b), for the per-slice form. Consumer: QC-SLICECLK-3.
Basis: the landed slice plan `results/qc_sliceclk_1027/plan/die_plan_sliceclk.json.gz` (claude/qc-sliceclk-1027@88bc183c7c)
and regions.json. The legality rules are die_trial.SiteMap (claude/qc-sliceclk2-1027@d2a6b2d12b tools).
Labels: OWN = my run, not independently checked. Nothing here is CHECKED by a second party.

**Plan input: `qc_slice_rows.json`** (generator `qc_slice_rows.py PLAN REGIONS TOOLS OUT`; render `qc_slice_rows.png`, viewed).

## Unit and shielding (fixes the R34 root cause by construction)
- PG (plan die.pg.grid, unchanged): M8/M9 0.48 @ 8.64, offset 4.32, VDD/VSS. VSS stripes sit at 8.64m and VDD stripes at 4.32+8.64m.
- PAIR-ROW m (M8) / PAIR-COL m (M9) = the 8.64-um period centred on a VSS stripe and bounded by two VDD stripes.
  - It holds two 16w tracks at VSS ±1.16 (on the 0.04+0.08n grid).
  - Near side: the VSS stripe is the shield (flank gap 0.60; 0.504 with the M9 .672 grid; must be ≥0.5 and ≤1.14).
  - Far side: a drawn 0.64 VSS shield at ±2.30, 1.46 / 1.36 from the VDD edge. OWN geometry, `checks.shield`.
- Pin windows: trunk ±1.16 ± the 2.5-um riser = ±3.66 < 4.32, so every class's windows stay inside its own pair-row.
  - No escape into another class's window is ever needed. That cascade was R34's 266.
- The H = 26,265.6 = 8.64·3040 = 32·95 pitches. So the slice root (y = H/2, = the plan spine root y 13,132.8) and every equal y-bisection node (L1-L4 / strip centres) land exactly on a VSS row.

## Reservation (classes)
| class | layer / rows | span | role |
|---|---|---|---|
| TOP | M8 pair-rows 1520 (T3 = tap level), 1521 T2, 1522 T1, 1523 T0, 1524 FEED, 1525 spare (y 13,132.8-13,176.0) | x 1,166.4 .. 30,659.0 | 1-D balanced tree, 13 taps (HUB + 12 slice roots), depth 4; root x 16,639.3 |
| TOP | M9 pair-col 135 (x 1,166.4) | y 8,432.6 .. 13,167.4 | source feed from coll_core (clk_rx) in the HUB |
| COL:<slice> | M9 pair-cols E0 2117-2120 (x 18,290.9-18,316.8; spine x 18,303.84); E_k +286k; W mirrored (m' = 3794-m) | full height | y-bisection L1-L4 |
| COL:<slice> | M8 node rows L1 {760,2280}, L2 {380,...}, L3 {190·odd}, root jog 1519 | column band ±8.64 | node A/Y jogs |
| COL:<slice> legs | M8 rows 95+190i (strip centres), 16 per slice | cb .. spine column | equal 678.24-um leg to each strip centre |
| LOCAL | every other pair-row / pair-col | | strip-local bisection, core feeds, reset |

The full-height legal column per slice (core+halo free, analytic) is wider than the earlier sampled 18,307-18,322:
- E0: 18,239.5-18,322.8. W0: 14,465.5-14,540.6. All slices are translations at the 2,471.04 pitch, and both sides exist.
- The W mirror tracks at 14,462.2 / 14,464.5 are ≤3.3 um outside the legal column, within jog reach (8.64).

## Feasibility checks (OWN, `checks` in the JSON)
- Class exclusivity: 0 conflicts over all reservations.
- Demand ≤ supply:
  - TOP: 1 net per row (2 tracks), +1 root jog at the column band.
  - Column: at most 4 concurrent levels on 8 M9 tracks. Vertical chains need no escape: the in/out jogs are on opposite sides of the pin row.
  - Node rows: 2 of 2 tracks.
  - Leg rows: 1 trunk + the L4 A-jog inside the column band.
- VIA78 access (pin row within 2.5 um of the trunk, on legal sites):
  - TOP rows: the max illegal gap along x 778-30,669 is ≤1 um (partition seams only). The sl band has no hard cores above y 11,770.
  - Columns: all 8 tracks reachable in all 12 slices.
- VIA89: M8×M9 junctions only at node jogs (6×6 V8 array 0.57 ≤ 0.64). Both wires are in PG gaps, so no via lands on a PG stripe.
- **FLAG (legs):** in 12 of 16 strips per slice, the leg row crosses the A0 core. The longest stage without a buffer site is 462.2 um (cb+75 .. cb+537), above the 448.5 export reach.
  - Strip 6: 263.5. Strips 7-9: 1.0.
  - No common y-shift of all legs fixes it (scanned ±95 rows).
  - Per-strip shifts to the nearest full-legal row (up to ±52 rows = 449 um) break the equal y-bisection.
  - Estimate for 16w M8 (R/16, C×2.2), 462 um: Elmore ≈24 ps, slew ≈55 ps ≪ 320 ps (UNCHECKED). → ASK COORD: accept a 462.2-um 16w leg stage. Otherwise SLICECLK-3 puts that stage on 2x16w.
- Wire inventory (reserved classes): top 79.6 mm, column 52.5 mm/slice, legs 10.9 mm/slice, total 840 mm.

## PG / IR
- The reservation cuts, moves or narrows no PG stripe; drawn shields only add tied VSS metal. So the upper-deck number is unchanged: 30.403 mV (PG-ACTIVITY-3, CHECKED above M7, M9 .672 grid).
- Added clock load estimate (UNCHECKED), at 0.2287 fF/um, 0.7 V, 1.2 GHz:
  - Wire ≈113 mW + ≈1,870 BUFx24 ≈45 mW ≈ 0.16 W die-wide.
  - Local worst case (column × top band crossing): ≈ +2 % of the canonical 0.5823 W/mm² in one 150-um bump cell.
  - So the upper-deck bound is ≤ +0.6 mV (30.403 → ≤31.0).
- **FINDING (OWN, not my scope; PG-ACTIVITY-5 owns the verdict):** I collected the finished QC .672 below-M7 runs.
  - Runs: intel2 pg-act-3-1027/qc_orig_full and pg-act4-1027/qc_sta_only. Superposition (exact Codex load only): co-located max 20.429 mV (VDD 10.651 + VSS 9.778), p99 16.45. The conservative slice gives 21.817.
  - Worst cell: u_ft_out_data_rd_wi_s0 at (441.18, 4.59), coll_ftm. → `qc672_below_m7_superpose.json`.
  - The budget for below-M7 was ≤4.597 mV, so QC .672 = 30.403 + 20.429 = 50.8 mV FAILS on this canonical flat-load basis. That is independent of this reservation.
  - It is not a measured-activity number. No QC measured-activity map exists that I could find.
  - So "PG IR still PASS" is NOT shown. The reservation adds ≤0.6 mV to whatever the PG owner closes.

## Reusable from R34 / R35 (die-wide form, stopped per 12.13f)
- R34 opt-ins (merge_collinear_m8, escape_alt_side, top-rep-col-clear) are generic builder fixes for any M8 trunk tree.
- R34 blocker census: the root cause is the PG pitch vs pin windows. This reservation is the structural answer.
- The predecessor R35 uncommitted die-wide work is saved as `predecessor_dry19_optin.patch`:
  - export --top-lane-base/--top-lane-step;
  - builder escape_class_rows = class-row exclusivity in the V2 escape.
- Its dry19 runs finished (UNCHECKED, intel2 qc-infra-r35/d19_*): f22/f22c 71, f31 170, f31c 180, ebc 247 no_clock_track (vs 266). The row-class idea cuts the errors, but they are not 0.
- Not pursued.

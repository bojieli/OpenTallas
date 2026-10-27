# INFRA-FIRST-QC-R28 (2026-10-27): PG option A (VSS cut under the clock-mesh straps) + D-QC-A0-R3B, one QC plan event

Base: claude/qc-infra-r27-1027@3e4a794033 (codex/qc-clock-1027@77c339e5bc + R27 census) + cherry-pick of
claude/qc-a0-plan-delta-1027@ba3b9825ea (D-QC-A0-R3B, COORD approved 11:2x to ride this plan event).

## 1. PG cut (COORD 11:08 OPTION A) -- DONE, gate PASS (own runs, CHECKED as runs; NUMBER-CHECK pending)
* Tool: `die.pg.grid[].net_holes_um {net: [rect]}` (schema) = exact per-net cut-outs, honoured by `die_infra.pg_rects`
  (clock router / shield ties / mesh inventory / IR model) and `die_trial.pg_stripes` (GRT OBS); pdngen builds get the
  same cut from `post_pdn_cut.tcl` (ORFS `POST_PDN_TCL`, runs after pdngen: cuts the VSS M8/M9 sboxes and drops the
  VIA89s inside the holes). Generator + checks: `tools/die_plan/pg_mesh_cut.py PLAN MESH OUT`.
* Rule: one hole per merged collinear strap run on the strap's own layer; across = clock half-width + NDR space
  (0.24 um at 8w: only the VSS stripe the strap sits on); along = shield end extension + space (0.64 um past each
  strap end, so the kept VSS neither touches the clock metal nor merges with a shield end). Kept pieces that meet no
  perpendicular VSS stripe are cut too (178 M8 tails, 8 um, east of the straps whose end column is cut).
* QC plan (physical/die_plan/qwen_compute/die_plan.json), mesh = prototype8 export8 mesh (`mesh_straps.json`,
  clock_spec sha256 956139e1...): holes M8 356 / M9 433; VSS removed M8 5,266.0 mm (5.55 %), M9 5,269.9 mm (5.55 %);
  VDD untouched (0.0 um).
* Checks (`pg_mesh_cut.json`): mesh clock metal vs PG 3,299 shorts -> **0**; drawn-shield wide merges 6,598 -> **0**;
  VSS M8/M9 graph **1 component**, 0 floating pieces, 0 cut ends without a VIA89 within one pitch (8.64 um); die-edge
  stubs max 17.28 um (uncut stripe ends whose last column is a cut M9 strap column; info).
* Render `pg_cut_mesh.png` (viewed): corner window (strap corner 1632.96/250.56) and a mid-die strap crossing; the VSS
  stripe is absent under each green strap, VSS shields (black) flank it, VDD (red) unchanged.
* G0 / G0C on the combined plan (R3B + cut): **0 E / 111 W**, identical to the R3B delta and the base
  (`g0_combined.txt`, `g0c_combined.txt`, `diff` vs results/qc_a0_kits_1027/plan_delta/g0*_delta.txt empty).

## 2. IR on the cut grid (task 4) -- own PDNSim runs, UNCHECKED (NUMBER-CHECK please), `ir_window.json`
Deck = copy of the QC-PG-WC core_centre window (864 x 864 um at die 15171.84/12700.8, 0.5666 W = 0.759 W/mm2
worst-case uncapped AR, 64 window-local bumps, open window edges). Changed only: PG stripes (pg_regions.core_stripes_tcl
form incl. -starts_with POWER), the R28 cut (4 M8 + 1 M9 straps in the window; cut 5 stripes, 891 / 2,791 VIA89 removed),
VSS solve added. check_power_grid VDD + VSS OK in every run.

| grid | VSS worst / avg mV | VDD worst mV |
|---|---|---|
| plan die.pg.grid 0.48@8.64 M8/M9, uncut | 111.0 / 68.6 | 111.0 |
| plan die.pg.grid, R28 cut | 113.0 / 71.8 | 111.0 |
| QC-PG-WC IR grid M8 0.48@2.16 / M9 0.48@1.728, uncut | 33.2 / 21.3 | 33.8 |
| same, R28 cut | 33.3 / 21.5 | 33.8 |

* The cut itself costs +0.1 mV (dense grid) / +2.0 mV (plan grid) VSS worst: small, as expected for 5.5 %.
* **FINDING (needs a ruling): the plan die.pg.grid (8.64 pitch) is NOT the IR-closed grid.** At this power it is
  111 mV, 3.1x the 35.45 strict bound, cut or not; even scaled linearly to 0.417 W/mm2 it is ~61 mV (UNCHECKED
  arithmetic). The 33.5 mV QC core IR (and NUMBER-CHECK 18.4 mV at 0.417) was solved on the denser grid, which the
  clock planner and the dry build do NOT use (dry build pg_source = plan die.pg.grid). On the dense grid the mesh
  straps still sit on VSS (0 mod 2.16 / 1.728), so the same cut applies, but its 0.6-um / 0.384-um stripe gaps leave
  no drawn-shield clock track at all, so the whole tree/mesh track model changes. The QC PG grid must be decided
  (plan grid + more metal elsewhere, e.g. M9 width as on HEAD, or the dense grid + flank-mode clock) before die STA
  numbers can count (12.4e: PG IR closed before signal GRT).

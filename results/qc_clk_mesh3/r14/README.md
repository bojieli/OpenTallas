# INFRA-FIRST-QC-R14: why the R13 top tree cannot route, and the lane structure that does (QC die)

Every number here is UNCHECKED and goes to NUMBER-CHECK. Branch `claude/qc-mesh-r14-1026`, off R13 a67e46af8a.
Run data: `epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r12/pkg/out/r14`. Drivers are in `scripts/`.

## Status against the R14 task list
- **(1) Row trunks on legal tracks + per-type slot rows:** root cause measured, structure found and shown on one probe tree (below). Not yet in the solver.
- **(2) MC re-solve:** not run. The solver geometry has to change first.
- **(3) Dry build 0/0:** reached on the probe tree only. The full die is still at 3147.
- **(4) Physical build, DRC, RCX, STA:** not started. No live jobs.

## Measured root causes of the R13 dry errors (3147 reproduced exactly, `dry/dry_repro_classes.txt`)
1. **Legal 16W shielded M8 tracks exist only beside VSS stripes** (`dry/m8_legal_tracks_probe.txt`, router probe on the plan PG).
   - The M8 PG has 0.48 um stripes every 4.32 um, alternating VDD/VSS.
   - A 16W trunk (0.64 um wire, VSS shields at +-1.14 um, 2.92 um total) is legal only at VSS +-1.08 to 2.12 um. Its shield merges into the VSS stripe; it can never sit next to VDD.
   - So each 8.64 um period has **2 trunk positions**. A cell pin must lie within 2.5 um (`STACK_RISER_MAX_UM`) of its trunk, so a pin row sitting on a VSS stripe reaches both positions with at most a ~2.3 um riser.
   - The R13 slot lattice (19.3 um pitch) puts pin rows at 50 different phases mod 8.64. Many land next to VDD, which gives the 3.1-6.9 um risers.
   - **Phase lock is identity-safe:** all 377 partition origins are multiples of 8.64, and H = 3040 x 8.64, so VSS maps to VSS under MX.
2. **The trees fold back onto one line.**
   - A delay-balanced tree laid on one row (lift -> root -> a/b -> leaves) overlaps itself. Row-line overlap depth is 3 on 19 of 25 lines and 7 on the centre line, counting drawn extents only (`dry/r13_m8_row_depth.txt`).
   - The builder reserves each trunk 8.64 um wider than it is drawn, which raises the depth to 4-5 (10 on the centre line). Only 2 positions exist per line.
   - The column y-trees fold the same way on M9: depth 6 at x ~ 2177 and ~ 4647 (`dry/r13_m9_col_depth.txt`), against about 3-4 legal M9 tracks within the 8.64 um move.
   - About 1000 off-row cells come from the 19.3-pitch slot rows missing the row line. The fix in 1 removes them as well.

## Structure that routes: one lane per tree level, on VSS phase (probe, `probe/`)
- **Lanes:** each tree node level gets its own 8.64 um lane. A node, or a leaf, sits one lane past its parent node. Repeaters stay on the lane of the node that drives their edge.
- **Rows:** every cell row is phase-locked to VSS. The origin is on the stripe in R0, and the body top is on it in MX.
- **Result:** each lane carries only edges that do not overlap in x, so nothing folds back. The parent-to-child step is the builder's existing L-drop (an M9 drop plus an M8 jog).
- **Probe:** the R13 period-0 local row x-tree (12 groups, 22 BUFx24, 11 nets) dry-built alone on the real QC plan PG gives **0 plan errors**. It has 13 wires and 24 pin stacks; max riser 1.375 um and max track move 1.375 um. It builds both with and without exact reservation.
- **Render:** `probe/r14_lane_probe.png` (viewed). Lanes 3922.56 / 3931.20 / 3939.84 / 3948.48; every trunk flanks a VSS stripe.
- **Cost:** the leaves sit 3 lanes (25.92 um) above the planned row, so the solver has to re-balance.

## Tool change (opt-in; default unchanged; `tools/die_plan/test_die_clock_mesh.py` 38 PASS)
- `die_clock_128._fixed_wires_stack(exact_reserve=True)`, enabled per explicit spec with `"exact_reserve": true`:
  - A horizontal trunk whose loads all land on it is reserved over its exact pin-bar span, not the span widened by +-8.64 um.
  - A vertical trunk is reserved over its span widened by the riser bound (`STACK_RISER_MAX_UM` + offset + 2 rows).
  - A drawn trunk that leaves its reservation is reported as a `reserve_overflow` plan error.
- On the unchanged R13 export (`dry/dry_exact2_classes.txt`): no_clock_track goes from 779 to 466 and no_pin_stack from 2368 to 2302, with 599 reserve_overflow. Only 36 of the overflows occur on a net with no other error.
- Exact reservation helps, but it does not fix the R13 export. The geometry (causes 1 and 2) has to change.

## Next (R15, solver work, then the R14 steps 2-4)
1. In `qc_clk_mesh3` (`--feed periodic`):
   - Islands y grid = 8.64 um VSS-phase rows in every type frame.
   - `periodic_feed` / `dtree` place each node level on its own lane, and repeaters on the lane of the node that drives their edge.
   - Column y-trees get per-level M9 lanes, which needs per-net trunk hints in `build_explicit`.
   - Recheck per-type identity (74/74). Re-solve, then run MC with 13 or more samples.
2. Split the centre fine-driver row at the seam (COORD R13 ASK-2): one row per half, YC -/+ delta, each fed only by its own half tree. Seam pairs go into the related-pair STA.
3. Add the 17.28 um centre clock channel as a QC PLAN-DELTA (G0 and cut gates rechecked) and fold the 22 x 0.86 um moves into it. The channel x-tree then needs no partition hosts.
4. Dry build 0/0, then ot-run build, DRC, RCX (0.64), resistor-graph check, and RCX-fed related-pair STA with the F4G RP1 view.

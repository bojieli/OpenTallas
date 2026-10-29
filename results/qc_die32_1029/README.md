# DIE-QC-32 — QC die owner slice, 2026-10-29

Successor of DIE-QC-31 (claude/die-qc31-1029@d21b1402c9e). Branch claude/die-qc-32-1029.

## 1. A3 keep-out form carried into the die mesh build (COORD 07:55 ruling)
Root cause (DIE-QC-31): the A3 clip harness wrote the ck_mesh straps as FIXED wiring of a REGULAR net that DRT also
routes, and GRT demoted the clock NDR of the tree nets under congestion (`[WARNING GRT-0273] Disabled NDR (to reduce
congestion)`, CHECKED in intel1 die-qc31/base/a3/c1/run.log: 10 lines; also in the vK ECO route.log for n_B1/n_P1u).
OpenROAD 26Q3 (the asap7lock image) has no switch to turn this soft-NDR demotion off (CHECKED: `help global_route`
options and binary strings; only debug 'softNDR'). So the spacing cannot rely on the GRT NDR; vK held it with a
keep-out band (obstruction 0.32 um each side of the M9 strap) and DRT then kept the nets' own NDR (DRT 0).

Shared-tool state (read on origin/main 88641ebb97):
- `tools/clk/mesh_form.py` (the ot_clk region mesh form QC-IMPORT-2 runs): ck_mesh is already a SPECIALNET
  (good: obstruction for DRT, capacity for GRT); the tree nets n_* get the NDR, GRT runs with -allow_congestion,
  so they can be demoted -> gap = no keep-out band.
- `tools/die_plan/explicit_clock_mesh.routed_mesh_tcl` (die-level explicit mesh emitter, used by the HEAD die path via
  clock_routed.routed_tcl) writes the whole mesh as ONE REGULAR FIXED dbWire = the same form as the A3 harness.
  Not changed here (HEAD default untouched); flagged to COORD for the all-die estimate-only risk sweep.

Fix (this branch, 1513eb7514e): `region.mesh.strap_keepout_um` opt-in key in mesh_form.py: a strap-layer routing
blockage band of that width along both sides of every strap (vertical straps on the v layer over y_span, horizontal
straps on the h layer over x_span). Absent or 0 = DEF bytes unchanged (test); negative = config error. Test
`test_strap_keepout_opt_in_bands_both_sides_default_unchanged`; tools/clk suite 73 PASS (2 failures are sparse-checkout
fixtures missing: results/die_qc21_1028 cal + s81_head pins, unrelated). QC die config for QC-IMPORT-2: set
`strap_keepout_um: 0.32`. The reference pilot config qc_mesh_p1.yaml is left as is (its replay must stay IDENTICAL).

## 2. NK A0 floorplan = V1L (plan_event_qc32.json)
GEOM-56 (07:54): direction PASS (V1 > V2), V1 as drawn FAIL on the existing macro_channels preflight (street 7.56,
E 9.26 < 10.8). Its legal variant V1L is adopted: node x 15.12, rawfault columns 73.44/199.80/325.94, romleaf col0
16.20; channels W 10.8 / street 10.8 / E 12.32 (CHECKED by GEOM-56). Placement only -> QC-A0-KITS-14, placed
AUTO-GEOM + GRT50 back to GEOM.

## 3. BTAB F2 pin move
Still PENDING: no routed sign-off PASS (F2 NOT SIGNED; F3b/F3r wait GEOM verdicts).

## 4. NUMBER-CHECK
ASK posted for the DIE-QC-31 keep-out numbers (run dir intel1:/srv/opentallas-scratch2/claude/die-qc31). UNCHECKED
until the checker reports.

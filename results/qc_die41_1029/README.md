# DIE-QC-41 QC-001 fixed-clock prebuild (2026-10-29 20:31-22:xx PDT)

Successor of DIE-QC-40 (results/qc_die40_1029). Geometry prebuild only: no GRT/CTS/STA, no sign-off/freeze claim.
Run root intel2:/srv/opentallas-scratch2/claude/die-qc41 (ot-run local, 4 thr). Numbers from each prov_*/prebuild.json,
diag_top.json, prov_stats.json [CHECKED].

## Shared fix (root cause of the 18/6 native census)

`tools/die_plan/die_clock_128.py::_fixed_wires_stack` now consumes `router.stack_backbone_xy(cell, pin, actual_xy)`:
the stack's `xy` (M7 riser, VIA78 junction, trunk branch / jog end) moves to the backbone column on the SAME pin row and
`m6_entry_xy` keeps the actual bar, so the existing `clock_routed.stack_down / stack_pad_layers / stack_shapes`
(794b2e095) draw the M6 jog + VIA67 + M7 riser in BOTH the census shapes and the routed Tcl. Trunk direction is still
chosen on the actual pin coordinates; no callback (or backbone == actual) = old geometry (test). Test
`test_clock128_m6_backbone.py` fails 2/3 on the old code.

## Die-local adapter `fixed_tree_prov_f1d_r.py` (= DIE-QC-40 fixed_tree_prov_f1.py + DIE-QC-41 items)

* outward VIA78 patch: `patch_aware_place` widened `a0-=.056; a1+=.056` assuming a0 < a1; a driver jog toward a trunk on
  its left is placed with a0 > a1 and was SHRUNK .056 per end -> the 18 "VIA78 pad vs adjacent-driver jog" spacing rows
  at 0.24 um (e.g. ck_n1162 jog reserved to 19480.187, pad to 19480.299, ck_n329 jog from 19480.539).
* root: H-tree node 0 sits in the M9 VDD strap 17007.504-17008.176 -> moved +0.92 um to x 17008.76 (nearest M9 track
  0.5 um clear of every M9 strap) and its drawn M9 port join reserved (+-4 um) so later shielded M9 trunks keep clear.
  PLAN ITEM: the die clock source join must land at the new root x (17008.76, 12463.16).
* NOBB: 4 driver Y pins (ck_b7488, ck_r8145_0, ck_b8370, ck_r9090_0; backbone shift 0.023-0.027 um) keep the actual bar:
  with their backbone drawn, a neighbour's drop/jog took the only free M8 track of their 0.9-5.8 um driver-jog window
  (order contention, diag in prov_R7D/prebuild.json driver_jog_diag). Reordering them first (R7A) moves the failure to
  2 trunks (ck_rn7480_0, ck_rn8362_0). Their native census stays 0 with the pin-x riser.
* F1d: far provider M8 landing pad row must clear PG, the reserved tree/shields so far (F1) AND every later M8
  trunk/jog + drawn VSS shields of a reference prebuild of the same plan (OT_DQC41_FUTURE), pads unreserved.

| run | change vs R7J | result | native census | top-access conflicts |
|---|---|---|---|---|
| R7J (DIE-QC-40) | - | FAIL pin-access | 18/6 | 128 = 108 shield + 18 adj jog + 2 root |
| R7M | + shared M6-entry fix | FAIL 4 no_clock_track (driver jog) | - | - |
| R7P | + outward patch + root move | FAIL same 4 | - | - |
| R7A | + 4 nets first | FAIL 2 no_clock_track (trunk) | - | - |
| R7B | + NOBB 4 | FAIL pin-access | **0/0** | 110 = 108 shield + 2 root-join vs M9 shield |
| R7BF | R7B + F1d (future = R7B) | FAIL pin-access | 0/0 | 38 = 36 + 2 root-join |
| R7BFR | R7BF + root join reserved | FAIL pin-access | **0/0** | **36** (12 nets x 3) |
| R7BFR2 | + future horizontal trunk = its RESERVATION (+-8.64+.056) | **pin-access PASS** (encoder census 0/0, top-access 0); FAIL next stage: shield power continuity, 88 of 191,962 drawn VSS shield stripes untied (0 shorts) | **0/0** | **0** |

R7BFR 36 rows = far provider landing of ck_rn*_1 (12 nets) at y 11017.48 vs the ck_rn*_2 trunk RESERVATION
(load span +- router.max_move 8.64), not its drawn metal: e.g. ck_rn38_2 drawn 17013.08-17292.96, reserved to 17301.696,
pad at x 17296.2 -> 3.1 um from real metal. The check is fail-closed against reservations and is kept; R7BFR2 makes F1d
avoid the reservation span.

Render R7B_review.png (c_E2_bf_10 region, plan level; sub-um M6 jogs not visible at this scale) viewed: trunks/branches in
the channel, no visible anomaly. The M6 jog geometry claim rests on the census (0/0), not the render.

## Next stage (first reached in R7BFR2)

Shield grid attachment: `C128.shield_ties` -> untied 88 / shorts 0 (stripes 191,962, grid vias 397,743, shield vias
297,094) [CHECKED, ties_probe.py on prov_R7BFR2/fixed_wires.json + pg_rects.json]. The adapter's FAIL write then crashed
on json.dumps(set) (ties carries sets) so prebuild.json was not written for R7BFR2; diag_top.json (0 hits) and
run.log (encoder census=0/0) are the record. Next: list the 88 untied stripes (short stub shields with no VSS grid
crossing within tie reach) -> extend/merge or FLANK mode, then PG access -> materialize -> die GRT0 >= 50 it -> clock check.

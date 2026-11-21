# S81-LEAF-CLASS-1730 handoff (started 2026-11-20 17:10 PST)

Task (COORD): class floorplan for S81 leaf no-growth classes (`s81.leaf_nogrowth_j4e`, 4,500-bit cap, ~33 builds):
representative carries the union of every member's ft + pin windows, windows solved jointly across the column (0 overlaps),
no outline growth. Extend class_window_solve --column (5176daec13e), class_merge (f64c1e8092c), landing_role_strap, pad_hoist.
Prove on leaf_F4500_00 (private strict bind 0, LATCHECK, one build per class, G0), then all no-growth classes.
Rows -> S81-DIE-R4 (J6 cut 11-21 13:00 if green, else J7).

Inputs: UNIFY-TOOLS-R2/R3 handoffs; R2 rows epyc9 /srv/opentallas-scratch2/claude/unify-tools-r2-work/s81col/s81_leaf_col_rows.json
(30 windows moved, mismatch 44->7, 45 new overlaps, 142 lane ends with no window); FABLE-SUPERSET-0415 sec 9/10.

## Status
- 17:10 started; reading data.
- 17:45 Work: epyc10 /srv/opentallas-scratch2/claude/s81-leaf-class-1730-work (W); lane clone epyc10 .../s81-leaf-class-1730.
  Base = J5 live plan (913a7026, kw45 d8j5 tree) + sidecar_new.json, not j4e (same 75 leaf types).
- Finding 1 (width): schema needs port width == bus width, so a lane cannot ride a wider class slot. FABLE's 4,500-bit
  classes bin lanes by capacity (571 in 668 etc). Exact-width union: F00 = 5,576 ft bits, N face 6,841 pins > 4.6/um.
  -> exact-width sub-classes (class_window_solve.exact_classes, 3.6 pins/um, 4,500 bits): leaf 75 -> 35 builds (F00 -> 8+20, F03 -> 1+2).
- Finding 2 (joint windows): class_window_solve.class_floorplan joint solver (union-find over class ends with x/y flips,
  slot-assignment search, first-fit packing) on all 11 classes F00..F08 of J5: 166 class-class ports joined, 0 conflicts,
  0 overlaps, then solve() re-pins neighbours: port geometry mismatches 525 -> 0. 15 s.
- Finding 3 (BLOCKER for superset with spares): every S81 leaf ft lane is clock-landed at every tile (fclk_in/out_<slot>,
  cland_fstart_*). spare_ft.declared() refuses a spare slot with a landing role ("needs its own dormant protocol").
  So superset classes need a dormant landing protocol (use strap masking ring ready/fault, fclk/fstart tied 0) in
  clock_landings emit + bind tie audit + spare_ft. Not on main. Equal-profile classes need no spare: 8 groups, 18 types -> 8 builds.
- 20:5x Rebased on b8ab33d192d (--ft-superset, COORD slot-naming ruling). class_floorplan now keeps member slot names and
  lets class_merge --ft-superset collapse equal pin sets (no ft0..N renaming); per-end landing pins + cland_tstart pins follow
  their window; landing contract mapped to rep frame. class_merge --child-union adds missing member collector child sites
  (the 11 missing sites); role pin site tolerance 1 um. Members with own-landed leafdn/leafup vs not, and cland_tstart site,
  split into separate sub-classes (fixes the 23 leafup/leafdn members). t53__clb66fa5cb kept own row (tstart on another site).
- J5 result: 13 classes, 0 conflicts, 0 overlaps, mismatches 479 -> 0; chained class_merge --ft-superset --child-union
  --role-strap: 0 refusals on all 13; 34 member types folded (leaf types 75 -> 41; 34 builds replaced). +1 cycle on 6 kit-priced lanes.
- PUSHED main f1a929e38f2 + 0d5c6f35990 (class_window_solve --classes CLI, class_floorplan, exact_classes; class_merge
  --child-union; 25 tests). Reproduce: W/drv.py (EXCLUDE=ot_s81sl_leaf__t53__clb66fa5cb) -> p_all.json.cli_classes.json;
  class_window_solve.py plan_j5.json --classes ... ; W/merge_all.sh -> W/m1/plan_13.json side_13.json.
- Private strict bind + LATCHECK + G0 running: W/bind_class.sh via ot-run (epyc10) -> W/gate_cls, W/bind_class.out.
- Open: dormant landing protocol for landed spare slots (Finding 3) still not on main; spare_ends rows in the class plan rely on
  --ft-superset spare_ends handling.

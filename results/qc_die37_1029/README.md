# DIE-QC-37 — QC-001 range-window backbone + KV-019 leaf drivers on QC (2026-10-29)

Lane DIE-QC-37 (QC die owner, successor of DIE-QC-36). COORD rulings [DIE-QC-36-PARK] (2)/(3).
Run root: intel2:/srv/opentallas-scratch2/claude/die-qc37 (bb2/, prebuild_e3_R*/, leaf_fixed_rf/).

## 1. Inherited state (all terminal, collected, nothing killed)
- BB1 (DIE-QC-36): FAIL 88,801 records / 379 unresolved; 25,204 pins forced to a fallback single track.
- Codex residual-only repair (unit 395843, 2.0 um jog): terminal, still 379 unresolved.
- E2 prebuild (unit 383438): FAIL 17,859 no_clock_track; 10,394/11,048 trunk failures have a FALLBACK driver record (CHECKED).
- Codex base-stack aliasing concern ((net,x) key): resolved by using DIE-QC-36's row-keyed `clock_base_resite_v2.json`
  (exactly 8,156 moved stacks) as input; dqc37_backbone.py no longer re-shifts.

## 2. Estimate before build
E2 failure = demand/supply mismatch created by the plan, not by the die: each pin got ONE M8 track (its M8 pad was
reserved pre-route with a shielded dry place, so pins of a shared trunk competed for pads -> 25k fallbacks off the
router's track). A range window that contains the E1 router track for (nearly) every pin returns the router to the
E1 solution, which passed the track stage on the same sites (44,591 nets, 0 no_clock_track). So expected
no_clock_track ~ number of pins whose window misses the E1 track.

## 3. dqc37_backbone.py (range windows; M8 landings reserved only after the router picks)
Pass 1 column per pin (M6 jog + pad + M7 stub, island-covered, clear of SIGNAL/OBS/PG/other-pin M6/M7);
pass 2 maximal clear M7 riser range on the column (every M8 track in [lo,hi] legal), different-net pins on the same
column split at the midpoint (disjoint windows). No M8 witness, no pre-route pad.

| variant | riser contract | riser max | column select | E1 track in window | E3 prebuild |
|---|---|---|---|---|---|
| R1 | in PG island union | 2.5 | nearest | 65,369 / 89,180 | FAIL 13,721 no_clock_track |
| R2 | R1 clipped to E1 track +-1 um | 2.5 | nearest | 65,369 | FAIL 13,985 |
| R3 | clear of actual M6/M7 shapes (island not required) | 2.5 | nearest | 84,267 | FAIL 2,715 |
| R4 | R3 clipped +-1 um | 2.5 | nearest | 84,267 | FAIL 3,183 |
| R5 | as R3 | 4.0 | track (nearest column whose range holds the E1 track) | 88,448 | FAIL 220 |
| R6 | as R3 | 9.0 | track | 89,152 | FAIL 18 (all 'driver jog' of vertical-trunk nets, 4 rows x 6 template replicas) |
| **R7** | R6; the 36 pins of those 18 nets keep the native default column window (E1 geometry) | 9.0 | track | - | **track stage PASS (0 no_clock_track)**; next stage FAIL pin-access 535/89 + 20,751 top |
All CHECKED from bb2/*/summary.json and prebuild_e3_*/prebuild.json. 0 unresolved pins in every variant (all 89,180
pins get a column; the 379 BB1 failures were the M8 witness, not the M6/M7 jog).

Finding R1 (CHECKED): 8,294 / 8,660 remaining trunk failures have the E1 track OUTSIDE the island-limited window
(island M7 windows are ~2.2-2.3 um tall; E1 trunks sit up to 8.5 um from the pin, 3,390 E1 risers > 2.5 um). The
island band cannot hold the shielded trunks of dense rows (e.g. y~12463: ck_n2, rn5_0, rn9_0, rn15_0 ...). R3+
therefore lets the M7 riser leave the island union while staying clear of every actual PG/signal/OBS/other-pin M6/M7
shape; the PG access replan (next step) then routes around the reserved risers (rule 12.8 principle-first: the
reservation is explicit, no new check kind).

## 4. KV-019 leaf drivers on QC (COORD: same ot_clk subcommand, no fork; main 3670a2b6a)
Config `leaf/qc_leaf_fixed_rf.yaml` = kv_e26a_leaf_fixed knobs (x5p33->x16, merge 30 um, search 40, halo 0.1) on the
CURRENT QC provider (codex-qc-import-0824/reachfix: inventory 5f7989df, placements b491955f, reachfix constraints).
Result [CHECKED leaf_fixed_rf_summary.json]: 2,420 trunk nets, 22,365 FFs -> 3,266 clusters, 6,532 new cells
(estimate before run 3,266 — CHECKED equal), 7 FF/cluster typical, leaf HPWL median 6.21 / max 85.59 um (one bit
spread by the reachfix reset-first move), a->b max 2.754 um, area +2,476 um2. Provider preflight (qc_import_2 preflight
--die-plan, reachfix bindings): READY_FOR_REVIEW, 54,791 cells, 0 issues [CHECKED preflight_leaf_rf.json].
(qc-import-1 inputs were stale: its preflight without the die-plan reset source reports global_raw_reset_star_forbidden.)
Next: GEOM review of the leaf placements -> apply_cells (reachfix chain) -> clock_loads -> provider-clock access ->
fixed-tree prebuild with the new loads (trunk nets then carry only clock cells).

## 5. E3 R7 = first range-window backbone through the track stage [CHECKED prebuild_e3_R7.json.gz, run.log]
- Track stage PASS on all 44,591 nets with 89,144 range-window records + 36 explicit default-window pins
  (`default_window_pins` in the plan; not failures, not partial: the E1 column contract, which passed this stage).
  Render review_region_e3_R7.png (c_E2_bf_10) VIEWED: M8/M9 trunks over the hard cores, drops at the core faces,
  same structure as E1; no claim beyond "drawn".
- Next stage FAILS exactly like E1 (backbone-independent): encoder census 535 shorts / 89 spacing (E1 535/89), e.g.
  M7 spacing ck_rn6_1 vs ck_rn1717_0 at x 17934.572 y 12796.5-12797.6 (two nets' stacks on one column), and
  20,751 top-access conflicts (E1 20,707): sampled 100 = M8 vs REAL PG grid straps (58 short VDD, 30 spacing VSS/VDD);
  e.g. ck_n0 port drop VIA89 landing at y 12463.36-12463.44 inside VDD M8 strap 12462.96-12463.44 = native endpoint
  landing (endpoint_access) vs real PG, not a backbone or PG-ACCESS item.
- Consequence for the fix order: PG access replan (PA) cannot clear the 20,751 (they are against the real grid);
  the next structural fix is (i) endpoint landing selection with the full M8 enclosure + spacing against real PG
  (fixed_tree endpoint_access uses half-height .04 and touches the strap edge) and (ii) the 535/89 same-column stack
  pairs (de-stack residue or two nets on one M7 column). Then PA -> materialize -> prebuild -> mesh -> GRT0.
- R6 18 residual nets: driver at x 20636.7/25578.8/14467.8/19409.8/26822.96, y 3175.9/8403.1/17860.6/23087.8
  (template replicas); window either ~1 um (blocked below by another pin stub) or contains the E1 track while the M8
  driver jog still finds no track -> left to the default column in R7 (explicit).

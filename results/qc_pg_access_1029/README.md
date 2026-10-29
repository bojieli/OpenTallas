# QC actual clock-cell power access

This packet constructs physical PG access for all 44,590 clock cells / 89,180 native M1 contacts in release26's lawful 98-type island DB. It does not claim complete die power, DRC, IR, or source119 adoption. A scoped 100-contact actual ODB coupon has all 100 contacts physically connected to actual canonical M8 PG metal, using read-back conductor geometry and technology-via layer enclosures rather than net-name connections alone.

## Construction

`pg_census.py` reads actual oriented contact geometry and technology vias. `export_geometry.py` reads actual cell signals, unmodified native macro supply metal, master/block obstructions, grid tracks and die bounds. All geometry is integer DBU (1000/um). Only exact matches between BLOCK M8/M9 obstructions and canonical PG stripe rectangles are classified as owned existing PG conductors (13,304 matches); every other obstruction remains blocking. Opposite supplies remain obstacles even where a PG obstruction is classified.

`plan_access.py` groups only abutting/overlapping actual M1 same-net rails with identical y extents. Release26 has 89,178 such groups covering 89,180 contacts. VIA12's M1 enclosure is 22nm tall versus the native 18nm rail. Its centre is offset 2nm outward from the cell (VDD +y / VSS -y), extending the extra 4nm metal away from A/Y and preserving the native 18nm inner spacing. This is a landing patch, not movement of a signal or native rail.

The stack uses actual VIA12..67 and minimum-area M2..M7 patches, then a short M7 stem wholly outside actual OBS, VIA78, and an M8 bridge to an actual same-net canonical M9 stripe. This avoids routing M7 beyond an owned island opening to a distant M8 stripe. M7 x tracks and M8 y tracks alternate global supply net parity. Actual A/Y metal, native target M7 clock pin metal, the fixed future clock lower-layer access, actual existing opposite supplies, and already constructed opposite PG are checked with layer spacing. Every via routing-layer enclosure is included in the power-first reserved rectangles.

The first complete construction covers all 89,178 groups / 89,180 contacts, with zero unresolved groups: 713,424 access vias and 2,407,806 wire/enclosure rectangles. These are construction results, not full-die DRC. The future clock seed originally under-reserved VIA67 M7 at +/-20nm instead of the technology +/-27nm. Mesh supplied a corrected seed; `recheck_clock_seed.py` confirms zero conflicts for all 89,178 PG groups against all 89,180 corrected M7 clock bases at 32nm spacing. No PG replan was needed.

## Scoped actual ODB coupon

`emit_coupon.py` emits the first 100-contact construction into the real source ODB, with the real canonical M8/M9 stripe subset and same-net VIA89 grid crossings. `read_coupon.py` reads back actual special-wire metal, actual technology-via layer enclosures, and the native terminal shapes from the written DB. `check_coupon.py` builds physical same-net metal components across actual vias and checks each contact reaches an actual canonical M8 stripe. Result: 100/100 connected, no unconnected contacts; 900 actual vias (800 access +100 grid crossings), 2,797 wire rectangles. The remaining contacts in this scoped coupon are deliberately outside its scope, not a whole-die power result.

## Artifacts and next source delta

All large artifacts are on intel2 under `/srv/opentallas-scratch2/claude/codex-qc-pg-access-1029`:

- `census26/{geometry.json,power_terms.json,census.json}`: actual 98-type release26 source.
- `access26_full/{access_plan.json,reserved_access.json,summary.json,actualvia_recheck.json}`: full construction and corrected-seed receipt. `reserved_access.json` is 117MB, schema `[net,layer,x0,y0,x1,y1]` in um, canonical VDD/VSS, includes wire rectangles and routing-layer via enclosures. Shared with mesh for power-first reservation.
- `coupon26_100/{coupon.tcl,power_coupon.odb,readback.json,connectivity.json,coupon_scope.json}`: actual scoped physical coupon.
- Logs `access26_full.log`, `coupon26_100.log`, `actualvia_recheck.log`: all EXIT0.
- The original failed first100 probe/diagnostic is retained: treating owned grid stripes as foreign OBS blocked every contact; after correcting only exact-owned PG classification, VDD centred landing failures identified the outward patch requirement.

QC is generating the authoritative functional 119-type reframe with unchanged clock-body locations. Before full PG adoption/materialization, recheck this construction against its actual OBS, target-pin and native supply geometry. The separate native partition M7 PG stripe terminal-to-grid join scope remains to be inventoried/owned; this packet closes clock-cell M1 access only. No logical global-connect claim substitutes for those physical joins.

## Actual119 and minimum-area successor

The authoritative119 source was exported from `baseline26/mechanics119/clock_grafted.odb`, including ALL native nonclock signal terminals as obstacles: 3,741,625 actual signal rectangles, 384,041 actual obstructions, and actual native supply rectangles. Clock cell names/masters/orientations/bboxes match source98 exactly. The full candidate with corrected M8 landings passes all89,178 groups /89,180 contacts against actual119 geometry with zero conflicts. Receipt `access26_full/source119_minarea_recheck.json`.

An actual technology-rule read from the physical coupon found M8/M9 minimum area7520 DBU². The initial80x40nm M8 landing could be too short for that rule where the bridge was short. `extend_m8_area.py` extends every local M8 landing to192x40nm (7680 DBU²), keeping every contact path, via position, and routing track unchanged. The source119 check above includes these larger landings. **Superseding PG reservation:** `access119_minarea/reserved_access.json`; the older `access26_full/reserved_access.json` is retained as diagnostic, not the current physical candidate. This larger landing is not in the first100-contact coupon; that coupon proves actual physical connectivity only, as explicitly scoped, and is not a DRC receipt. The fix adds connected metal to the same M8 component.

The clock lane is also constructing short-stack M7 minimum-area patches; its future seed is being enlarged to +/-36nm y (72x32nm=2304>2188 minimum). A focused PG-stem versus that exact seed check passes all89,178groups /89,180clockbases with zero conflicts (`access119_minarea/clock_minarea_recheck.json`). The constructor requires an explicit `--clock-seed` input to prevent accidental reuse of an older seed. QC also has a forthcoming native target pin height .800 successor for264 PG-incompatible .768 target pins; actual source geometry remains authoritative and its changed pin metal must remain clear. QC owns native partition M7 supply stripe VIA78-to-grid joins separately.

A conservative forthcoming nativepin .800 envelope check (all7,889current M7 nativeclock rectangles extended16nm at both ends, unchangedcentres) also has zero PGstem conflicts at32nmspacing. This proposed-envelope check does not replace the actual new provider source.

## Joint clock/power successor (Codex mesh5)

The previous power-first construction left 460 clock bases with no shielded M8 witness. `jog_backbones.py --joint-clock` chooses actual island-contained M6/M7 jogs and reserves mutually compatible M8 witnesses against canonical die PG, then emits `joint_clock_reserved.json`. The power constructor accepts this explicit reservation through `--joint-clock-reserved`; defaults remain power-first. M8 reserved rectangles include 280nm beyond physical .08-wide witness metal, so the constructor's ordinary40nm PG clearance gives the required320nm shield separation. Lower-layer rectangles remain physical metal with ordinary technology spacing. This changes geometry allocation only; clock sites/topology and cycles remain unchanged.

First source119 construction:484/484 blocked bases receive witnesses, zero unresolved, intel2`codex-qc-mesh5-1029/joint_seed`, unit2681909 EXIT0. This is a clock-first geometry result, not joint power/clock closure or a physical route. Full89180contact PG reconstruction against refreshed authoritative119_h800 geometry is running at`codex-qc-mesh5-1029/pg_joint484`; inspect`joint_pg.log` and`summary.json`. Review and actual whole-plan access replay remain required before materialization.

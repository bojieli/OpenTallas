# FABLE-PD-HEAD-0700: HEAD die route by region-net units, why the count is flat (2026-11-15 08:1x PST)

Scope: physical design only. Evidence: epyc2 `/srv/opentallas-scratch3/claude/die-head-route-1/head/p20nc_gate/unitruns/probe_u201_b`
(`drc_TT.rpt`, 2,800 markers after iteration 2, crop form), the unit database `unit.odb`, the kit under `tree/kit`.
My runs: epyc2 `/srv/opentallas-scratch3/claude/fable-pd-head-0700` (wi1, wi2), epyc10 `/srv/opentallas-scratch2/claude/fable-pd-head-0700`.
MEASURED unless marked INFERENCE.

## 1. What the 2,800 markers are (u201, crop form, after iteration 2)

| layer | markers | object pair |
|---|---|---|
| M1 | 721 | Short 400 clock net vs tile abstract (obstruction), 178 clock net vs VDD/VSS, 97 clock vs clock; spacing 46 |
| M2, M3, M4, M5, M6 | 252 each (+13 EOL/spacing on M4/M5) | Short, clock net vs the tile abstract `ot_s81hd_tile_p` (its obstruction), all of them |
| M7 | 323 | Short 244 clock net vs tile abstract, 77 clock net vs VDD/VSS (the tile's M7 PG pins), 2 clock vs clock |
| M8 | 475 | 297 clock net vs die obstruction, 74 clock net vs PG stripe, 104 clock vs clock (min step 83 included) |
| M9, V8 | 8 | clock vs obstruction / PG |

- 2,788 of 2,800 markers lie within 0.5 um of a die clock inverter body; 2,796 within 2 um. They sit on 250 sites.
- No marker is at the unit box or crop edge. No marker involves a fixed net of an earlier pass (this is pass 1; the
  685 other clock nets are special with no shapes). No abstract signal pin is involved.
- So the answer to the classes asked: PG stripe 329 (M1 178, M7 77, M8 74), abstract obstruction about 1,900
  (M1-M7), die obstruction on M8/M9 301, via stack = all of M2-M6, fixed net 0, unit boundary 0, macro pin 0.

## 2. Root cause

**The die clock inverters are placed on top of the partitions, and the abstracts are solid there.**
- The unit has 606 `CKINVDCx16` cells; 600 lie inside a tile's bounding box (6 outside). Their pins are on M1.
- The unit's 141 own nets have 282 M1 cell pins and 43 M9 tap terminals; the wire is on M8/M9 (6.7 / 4.7 mm). Every
  cell pin therefore needs one via stack M1 -> M8. The log counts 254 up-vias on each of M1..M6: one stack per pin
  that DRT managed to build.
- The tile abstract (closed view, `write_abstract_lef -bloat_occupied_layers`) has ONE obstruction rectangle on
  each of M1..M7 covering 99.2 % of the tile, plus 164 full-height M7 PG pins. Each stack crosses that slab once per
  layer: one short per layer per stack. That is the "252 on each of M2-M6". It is the stack count, not a layer effect.
  M1 and M7 are higher because the cell's own M1 pins and rails and the tile's M7 PG pins add shorts.
- It cannot converge: both objects are fixed (cell position, abstract). DRT can only move the stack inside the
  slab. Iterations 3-9 go 2,679 -> 2,604; the pilots are flat for the same reason.
- The plan does reserve islands for die clock cells (`clock.die_islands_um`, 63 per tile, 8.64 x 8.64 um, one row at
  y 349.92-358.56), but they belong to an older clock. Of the 600 cells over tiles, 3 have their centre in a declared
  island. The adopted regional tree (link_htree + DME, feed hk6) puts its cells elsewhere, and the kit was built
  without island windows (`--island-sites` is not in its arguments).

**Second cause, M8/M9 (about 480 markers): GRT-only obstructions are still in the route database.**
- The unit database carries 51,091 M8 and 45,971 M9 die obstructions from `grt/obs.tcl`. The kit writes them for
  global route: PG stripes as obstructions, and `reserve_rects`, the tracks reserved FOR the clock legs (0.4 um wide).
- In detail route the clock wire is put on its own reserved track and shorts against the reservation: 297 of the
  475 M8 markers name an obstruction; the 0.4 um reservation class is the largest.

Not the cause: unit split, crop, reach, pass colouring, small worker. Form (a) and form (b) agree to 1 marker at
iteration 0 and u201 a/b are identical through iteration 3 (3,276 / 2,786 / 2,800 / 2,679).

## 3. Fix, ranked, with the what-if

**What-if wi1 (u201, same database, same guides, same steps):** the tile abstract's M1-M7 obstruction and M7 PG
pins cut by a window at every clock cell body (+1.08 um each side; 600 windows, under 5,511 um2 of 6.6 mm2 of tiles).

| | iteration 0 | iteration 1 | by layer at iteration 1 |
|---|---|---|---|
| as built | 3,276 | 2,786 | M1 668, M2-M6 255-258 each, M7 335, M8 782, M9 108 (iteration 0 table) |
| wi1 windows | 621 | 96 | M1-M7: 0. M8 91 (short 55, spacing 26, min step 10), M9 4, V8 1 |

So the windows remove every M1-M7 marker in two iterations. The 96 left are all M8/M9.
wi2 (windows + the GRT-only obstructions removed from the route database): 340, 44, 44, 21; see section 6.

Ranked changes:
1. **Remove the GRT-only obstructions before detail route** (owner DIE-HEAD-ROUTE-1, `unit_prep.py`; KV the same):
   delete every die obstruction on M8/M9 that comes from `grt/obs.tcl` (clock reservations and PG duplicates).
   The real PG stripes are in the database as special wires and stay.
2. **Clock cell sites must be holes in the types** (owner HEAD-99 for the plan, KIT-OPS-5 for the clock kit):
   - Take the cell list of the ADOPTED kit clock, map each cell into its partition type frame, union over all
     instances of the type (`apply_clkmesh_sites.py` does exactly this) and write `clock.die_islands_um`.
     Measured on this crop: R0 tiles share the template (97 of 98 and 70 of 93 sites equal to tW1b8's 141);
     the MY tiles have 0 exact matches after mirroring. Force one site template per type (mirror the R0 tree for
     MY/MX/R180) before the union, otherwise the tile carries two or four sets.
   - Build the kit with `--island-sites`, and extend the window cut from M1-M3 to M1-M7 for closed views
     (`island_windows` / `abstract_lef`, `ISLAND_PG_CUT` already cuts M7 PG).
   - A signed type whose layout is not empty at a site must be rebuilt with the island as a placement and M1-M7
     routing blockage. For hd_tile this is one type for about 300 instances. NOT verified by me: whether the signed
     hd_tile is empty at the new sites (its `6_final.odb` on epyc2 did not load: read_db iostream error; check the
     copy). Expect it is not empty, since the sites are not the declared ones.
   - Cheaper alternative to test first (KIT-OPS-5): snap the region tree cells to the islands the type already has.
     With 63 islands in one row against 141 cells spread over the tile height I do not expect it to hold the
     405 um leg bound; a one-kit run answers it.
3. **Tap ends** (owner KIT-OPS-5, low): the 43 taps of a unit are die terminals on M9 (`t_<part>__clk_tN`,
   DRT-0422 "no track through the centre" on all 43); the tile's real `clk_tN` pins are on M7 and are not on the
   net. Connect the net to the abstract pin so the last drop is routed and checked. Not a cause of the flat count.

Gate for "one unit at 0": u201 with 1 + the windows. Then the three pilot units, then volume.

## 4. Stop list

- Stop iterating the six pilot runs (u198/u201/u261, forms a and b): they are at 2,604-2,621 and cannot fall.
- Stop the full-die run `p16g/drt7_small96_TT`: same database, same two causes, no iteration line yet.
- Do not start pass 2..11 or any KV unit until one unit is at 0.
- Do not tune DRT (iterations, costs, worker size, pin access) for this; do not move via stacks by hand.
- Do not regenerate abstracts with "pin shape on the plan layer only" (the earlier inference in
  FABLE-CLOSURE-STRATEGY lever 2): no abstract pin is in any marker.
- Do not keep the windows what-if as a result: it only shows the mechanism. A window over a type that is not empty
  there hides a real short.

## 5. KV

Same cause, three layers instead of seven. On the kvgeom6 route kit (epyc10 `die-kv-route-1/runs6/p6/die_grt.odb`):
- 32,856 `CKINVDCx16` die clock cells, all 32,856 with their centre inside a partition and under that partition's
  M1, M2 and M3 obstruction (plan abstracts; M4-M7 are not solid there).
- 437 of 32,856 are inside a plan-declared die island (the plan has 4,977 island rectangles in 44 of 56 types);
  the kit was built without `--island-sites`.
- 65,712 M1 cell pins on 32,858 nets: expect about 3 shorts per pin on M1-M3 plus the M8/M9 class, since the same
  `obs.tcl` reservations are in the database.
- DIE-KV-ROUTE-1's check "M8/M9 abstract pins against PG: 0 shorts" is correct and is not this class.
Keep KV units stopped; apply fixes 1 and 2 with KV's region map.

## 6. Later results

u201, crop form, same guides and step table, violations after iterations 0 / 1 / 2 / 3 / 4:

| run | 0 | 1 | 2 | 3 | 4 | what is left |
|---|---|---|---|---|---|---|
| as built (pilot u201_b) | 3,276 | 2,786 | 2,800 | 2,679 | 2,619 | section 1 (2,604 at iteration 9) |
| wi1: windows at the clock cells | 621 | 96 | 96 | 74 | 73 | M8/M9 only: 61 clock vs die obstruction, 9 min step, 3 clock vs PG |
| wi2: windows + no GRT-only obstructions | 340 | 44 | 44 | 21 | (stopped, 4 steps asked) | 19 min step on M8 (clock net alone, 7-24 nm steps), 1 short M8 and 1 short M9 clock vs PG |

- **0 was NOT reached** in the 4 steps I ran. wi2 was still falling (44 -> 21 on the first DRC-driven step); the
  stock table has 21 more steps. The M1-M7 classes are gone in both what-ifs from iteration 1 on.
- The 19 M8 min-step markers are own-net geometry (a via landing or jog on the M8 clock wire), not a fixed-object
  conflict. INFERENCE: they clear in the DRC-driven steps; if a residue stays, it is the M7-to-M8 via landing against
  the clock wire width, to be read from the marker list of a 10-step run.
- Cost seen: wi1 83 GB and wi2 99 GB peak against 9.4 GB as built. I did not find which of my two changes causes
  it (the abstract obstruction cut into 548 rectangles per layer, or loading through LEF + DEF instead of the
  database). Measure on the real fix before volume; it sets units per host.
- Files: epyc2 `/srv/opentallas-scratch3/claude/fable-pd-head-0700/wi1` and `wi2` (`drt.log`, `drc_TT.rpt`,
  `lef/ot_s81hd_tile_p.lef` = the windowed abstract, `mklef.py` one level up).

Next step for DIE-HEAD-ROUTE-1: rerun wi2's form for 12 steps on u201 with `-output_drc`; that is the "one unit at
0" proof of the mechanism. In parallel HEAD-99 + KIT-OPS-5 make the sites real (fix 2), because the windows are not
valid on the signed tile until the type is empty there.

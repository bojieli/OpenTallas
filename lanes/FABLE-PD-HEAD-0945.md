# FABLE-PD-HEAD-0945: HEAD NF7 clock site templates, structural review (2026-11-15 10:2x PST)

Scope: physical design only. Read-only. No build, no STA, no tool run on a database; Python on the plan and tree JSON only.
Inputs: epyc7 `head-99/prep21z20NF7/prep/source_plan.json` (= `head-100/nf7_plan.json`), `head-100/rep_isl.json`,
`head-100/tree_nc.json` (adopted NC tree, 44,547 cells, 27,164 nodes, 13,093 taps, 327 region trees), `head_island_template_delta.py`;
epyc2 `die-head-route-1/reemit/nc_start_stages/start_stages.json`, `p20nc_gate/tree/kit/abstracts/ot_s81hd_tile_p.lef`,
`die-route-abs-1/r_cut2`, `r_w1t32` logs. My scripts and output: epyc7 `/srv/opentallas-scratch2/claude/fable-pd-head-0945` (an1..an5.py).
MEASURED unless marked INFERENCE.

## 0. Verdict

**Do not adopt NF7 as it is.** One template per type is the right form. The NF7 template is the site set of one instance's
tree, while the other 263 hd_tile instances keep their own, different trees. Moving those trees onto the template does not
hold the leg bound or the balance (section 2). The fix is in the clock generator: build the region tree once per type and
stamp it on every instance. Then the template is exact for all instances and NF7 needs about 20 more rectangles per tile
(section 4), so one event NF8 replaces NF7.

## 1. Why 132 R0 tiles have 131 site sets

All 264 hd_tile region trees have the same size: 86 nodes, 43 taps, 42 merges, 1 feed to the next region. They differ in four things:

| cause | measured |
|---|---|
| entry point of the region (type frame) | R0: (367.6, 688.5) 66 instances, (693.8, 688.5) 54, (376.8, 377.5) 6, (693.9, 688.5) 6 |
| inverter parity at the entry | R0: odd 76, even 56. It decides which leaves get the extra leaf inverter (`q` cell): 25 or 18 of 43 |
| merge points and the slide legaliser, in die coordinates | 118 distinct requested-point sets in 132 R0; 29 distinct in the 36 instances with the same entry and parity. The closest sibling of the template differs in one merge point by 8.64 um |
| mirror | MY trees are not the mirror of R0 trees: `q` cells per instance 6 to 36 (R0 18 to 25), repeaters 13 to 34 (R0 28 to 34). Where the tree does match, the cell body is offset by 1.62 um (`b`, `r`) or 2.70 um (`q`), because the node point is mirrored, not the cell box |

None of the four is a need of the design. The taps, cores and outline are the same in every instance.
Other multi-instance types show the same: hd_spn 5 sets in 5, wshim_rx 6 in 6 (56 % on template), turn_a 6 in 6.

## 2. What happens if the adopted tree is snapped to the NF7 templates

What-if on the adopted tree, all 26 types, each cell moved to a free template site of its type (greedy one-to-one, so an upper bound):

| | as built | snapped |
|---|---|---|
| cells moved | 0 | 26,771 of 44,547 |
| cells with no site left | 0 | 124 (hd_tile 41, hd_st_str 37, wshim_rx 23, mesh_e 8, turn_b 7, serdes 5, st_m 2, eshim_tx 1) |
| stage length p50 / p90 / p99 / max, um | 75 / 143 / 305 / 402.4 | 82 / 230 / 595 / 1,757 |
| stages over 405 um | 0 (147 over 350) | 1,326 |
| tree wire | 2,987 mm | 4,132 mm |
| tap insertion change (model 8.8 ps + 0.24 ps/um per stage, fitted, 0.00 ps error) | 0 | p50 +463 ps, max +1,565 ps |
| tap spread inside one partition, added | 0 (as built p50 35, max 102 ps) | p50 +47, p90 +356, max +607 ps |

Lower bound (each cell to its nearest template site, sites shared): hd_tile R0 repeaters p90 29, p99 74, max 309 um; MY repeaters
p90 62, p99 103, max 311 um; MY `b` p90 31, max 139 um. The truth lies between, and the reason is structural: an instance with
36 leaf inverters cannot sit on a template with 25. Snapping a different tree onto one site set does not work.

## 3. Answers

1. **One template per type from the best-agreeing R0 instance:** the template form is right, the selection rule is not. Agreement
   of site sets (69.5 %) is not the question. Choose the instance whose TREE every instance will get, and give every instance that tree.
2. **Cells outside the template:** neither re-legalise each instance's tree nor per-instance templates. Per-instance templates turn
   one type into 264. The union is 3,539 distinct sites over R0 + MY (2,589 at 2.7 x 0.81 um bins), 24 times the template, and it
   changes at every clock regeneration; the 716 bins used by at least 2 % of instances cover only 90 % of cells. Stamp one tree (section 4).
3. **Mirrored instances and the 405 um bound:** yes if the tree is mirrored with the instance (lengths are preserved exactly, the R0
   tree has max 402.4 um). No if the MY tree is snapped (section 2). The cell box must be mirrored, not the node point.
4. **Blockage:** hard placement blockage plus M1-M7 routing blockage, both on the same rectangle = cell 1.62 x 0.27 plus 0.54 / 0.27
   halo (2.70 x 0.81 um), as in NF7. Placement-only is not enough: each pin needs a via stack M1 to M8 and a signed type has real
   wire there. The halo is large enough: DIE-ROUTE-ABS-1 `r_w1t32` (windows of cell + 0.3 um, GRT-only obstructions dropped) goes
   383 -> 41 at iteration 1 with 0 markers on M1-M7 (left: 38 M8 min step, 1 M8 spacing, 1 M8 short, 1 V8). My 1.08 um windows gave the same
   (44). Do not grow it. Cost in hd_tile: 328 um2 of 253,435 um2 outside the cores (0.13 %), 1,675 of 894,427 cells displaced.
   - The abstract cut must be the plan's island list, the same rectangles and layers, not a list from `tree.json`. Then a cut can
     never be larger than what the type kept free.
   - M7 PG: the tile has 164 M7 PG pins, VSS/VDD pairs 0.672 um wide at 8.64 um pitch. 31 of the 150 NF7 cell bodies lie over a
     stripe (42 with halo). That is the "77 M7 clock against PG" class of 0700. Slide those sites by at most 1.3 um to sit between
     pairs (7.97 um free per pitch, 2.70 needed). No PG cut is then needed; `ISLAND_PG_CUT` stays as the fallback only.
5. **Skew and slack:** with the stamped tree the skew inside a region is that of the template tree, once per type, so it is
   checked once. Insertion between regions changes by the entry leg: at most 326 um more inside a tile, 2 to 3 stages, about
   90 ps. Regions are not balanced against each other today (model insertion 586 to 5,764 ps); the count-aligned proof carries
   that (427 crossings, worst margin 113.3 ps on ca4). So the proof and the start stages are rerun on the new tree; that is a gate, not a risk
   I can size without the run. With snapping instead: no (section 2).

## 4. Ranked fix

**1. Region tree built once per type and stamped (owner CLKSITE-RESERVE-1115; that lane has no post and no handoff on the hub at
10:1x, COORD confirms it is alive, else KIT-OPS-5).** In the clock kit's region tree step:
- one entry point per type. For hd_tile take (367.6, 688.5); the 60 R0 instances fed from the other side get 326 um of feed
  inside the tile on template sites;
- parity fixed at the entry: one inverter site at the region root, used when the incoming parity is odd, so every instance has
  the same leaf set;
- merge and legalise in the type frame against the type's own forbidden areas (cores, pins, M7 PG pairs). Die-frame forbidden
  rectangles (1,826 today) that touch a partition are mapped into the type frame and unioned over its instances first;
- stamp by the instance transform with the cell box mirrored; cell orientation follows the instance (MX / R180: 6 types, 12 instances).
Checks, in this order: site sets per type = 1 for all 26 types; die clock cells outside an island = 0 (make it a kit error);
stages over 405 um = 0; region spread no worse than today (worst 19); then die STA on related pairs and the count-aligned proof 427 / 427.
Cost: tool change, then a 20 minute clock kit.

**2. Start-stage flops need sites too (owner CLKSITE-RESERVE-1115 for `start_stage_emit`, HEAD-100 for the rows). Not in NF7.**
The NC emit has 1,452 stages with 5,663 flops in rows of 4.32 x 0.27 um (149 of 3.24), within 4.86 um of their clock cell.
1,035 stages (4,036 flops) are under hd_tile, 3 to 7 per instance, in 104 distinct type-frame sets. 0 of the 1,452 rows is inside
an NF7 island. They are die cells with M1 pins under the abstracts, the same class as the inverters. Give `start_stage_emit` the
island list as its legal set and put at most 7 row sites (5.40 x 0.81 um) per tile in the template. Without it hd_tile re-keys a second time.

**3. NF8 instead of NF7 (owner HEAD-100).** NF8 = NF6 + `clock.die_islands_um` taken from the stamped tree of fix 1: the tree
sites, the entry feed sites and parity site (about 10), the start-stage rows (at most 7), and x clear of the M7 PG pairs.
Same gate chain as NF7 (G0, bind, cohort 26 / 26, LATCHECK 329 / 329). NF7 stays as the proof that the key does not disturb the gates.

**4. hd_tile rebuild, once, on NF8 (owner KIT-OPS-5 launch, HEAD-100 type).** Islands as hard placement blockage and M1-M7 routing
blockage in the type kit. This rebuild is owed anyway: the kit abstract and the signed `6_final.odb` are 708.48 x 1036.8, the
plan outline is 717.12 x 1036.8. So no signed record is lost to the template. The other 25 types follow on the same event.

**5. Abstract cut and the unit proof (owner DIE-ROUTE-ABS-1).** `abstract_cutout.py` takes its windows from the plan islands.
Then u201 for 12 steps on the stamped kit with the GRT-only obstructions removed (`die_unit_obs.py`), target 0. Read the 38 M8
min-step markers after step 12; they are on the clock wire itself. Unit volume after one unit is at 0.

**6. KV 7u, QC S4q4, S81 B6gE (owners KV-102, DIE-QC-103, DIE-S81-92).** Use the same stamp mode before reserving sites. A
template taken from an unstamped tree repeats section 2 on each die.

## 5. Stop list

- Do not adopt NF7 over NF6. Do not launch hd_tile or any HEAD type on the NF7 islands (26 types would re-key twice).
- Do not run the adopted slide-mode tree with `--island-sites` on the NF7 templates and call it the fix (1,326 stages over 405 um).
- No per-instance, per-orientation or union templates.
- Do not choose the template by site agreement between instances.
- No abstract cut from `tree.json` on a signed view outside the u201 proof; it hides real metal.
- No M7 PG cut where a slide of at most 1.3 um clears the stripe pair.
- No halo above 0.54 / 0.27 um and no M8 / M9 blockage in the type.
- Do not re-emit start stages for NF without the island list as legal set.
- No DRT iterations, unit volume or full-die route until one unit is at 0 (unchanged from 0700).

## 6. Not verified

- No stamped tree exists; its skew, the entry feed and the count-aligned margins are not measured.
- The snap what-if is greedy (upper bound) and uses a per-stage delay model fitted to the kit's own leg delays, no STA.
- Pin access on a real signed tile with the 0.27 um row halo: only abstract windows are measured (`r_w1t32`, my wi1 / wi2).
- INFERENCE: the start-stage flops are not in the p20nc route unit (the 0700 unit held 606 inverters); they enter with the count-aligned die route.
- Rail polarity of a die cell in MX / R180 instances.
- The M7 PG count uses the 708.48 abstract; the 717.12 view may shift the stripes (58 of 150 at a half-pitch shift).

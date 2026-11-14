# EXPLORER-REVIEW-1: die-level detailed route viewer (Fable survey, 2026-11-14)

Owner question: can the chip explorer show detailed routes at die level when zoomed in to a type, instead of opening
one element page per hard core? Is it hard in the corners and the inter-type area?

## Answer

Yes, and most of it is already built. Recommend building it as a composition layer over the existing layout store:
about 6-8 lane-days to a first die (S81) at type zoom, about 12-15 lane-days for all 5 dies with seams and overlays.

The corners and inter-type area are NOT the hard part. Partitions abut and cover 85-96 % of each die, so a seam is
just two type edges whose pins meet. The real limit is different: there is no die-level routed database today, so
die-top nets, the die PG on M8/M9 and the clock H-tree/mesh can only be shown as plan or prototype (GRT guide)
overlays, clearly labelled as such. Everything inside a signed type or core can be shown exactly.

## What exists today (measured)

Two explorers:
- fleet-viz explorer (localhost :8765, `tools/fleet_viz/explorer.js` + `explorer_geom.py`, kind `plan` from
  `plan_now.plan_geometry`): one 2-D canvas per die, every partition and every hard core as a rectangle. This is
  the "many hard cores" view. A click opens `/explorer/element/<name>`.
- design explorer EXPLORER-2 (epyc8 :8766, tunnel localhost :8760; `design_service.py`, `explorer/design/design.js`):
  die -> type -> core pages, each with a Plan view and a Routed layout view. Not on the localhost main checkout.

The routed view is not a PNG. It is a lossless vector viewer (`tools/fleet_viz/LAYOUT_VIEWER.md`):
- `tools/layout_viewer/lv_extract.py` (openroad -python on the 6_final.odb) + `lv_tile.py` cut one "pack" per
  signed type/core: 25.6 um vector tiles per layer (brotli, 1 nm exact), a per-layer density raster pyramid
  (finest 0.4 um/px), name tables, macro list, clock/timing overlays. `lv_verify.js` must report IDENTICAL vs OpenDB.
- Browser: deck.gl 8.9 (WebGL2), `explorer/element/layout.js`. Geometry is drawn when the visible shape estimate is
  under 5 M (1.6 M on phones); above that it draws the density raster. So the level-of-detail idea in the question
  already exists, per element.
- Store: content-addressed, immutable, cut once at sign-off. Packs are keyed by node id (`s81.t.<type>`, `s81.c.<core>`).

Die-level instance counts (current plans of record, localhost geom cache):

| die | outline um | partitions (unique types) | hard-core insts (unique) | orients used | partition area | core area |
|---|---|---|---|---|---|---|
| S81 | 31951 x 25436 | 398 (205) | 21,013 (66) | R0 MX MY R180 | 95 % | 35 % |
| S81 head | 17522 x 17556 | 357 (25) | 1,849 (12) | R0 MX MY R180 | 91 % | 43 % |
| Qwen compute | 31216 x 25644 | 377 (123) | 1,779 (41) | R0 MX | 96 % | 54 % |
| Qwen KV/sys | 11180 x 27043 | 160 (56) | 1,851 (33) | R0 MX MY R180 | 85 % | 30 % |
| HBM | 28400 x 18541 | 90 (81) | 3,497 (111) | R0 MY | 97 % | 41 % |

No R90 family orient is used on any die, which removes the worst orientation problem (layer direction swap).

Pack sizes in the EXPLORER-2 store (latest closure per node, 282 nodes, 12 GB with history and unsigned attempts):

| die | type packs: n, total, median, max | core packs: n, total, median, max |
|---|---|---|
| S81 | 45, 1.6 GB, 26 MB, 131 MB | 57, 0.6 GB, 10 MB, 31 MB |
| S81 head | 17, 0.19 GB, 10 MB, 31 MB | 2, 0.05 GB |
| Qwen compute | 21, 1.2 GB, 68 MB, 125 MB | 24, 0.44 GB, 24 MB, 40 MB |
| Qwen KV/sys | 13, 0.24 GB, 15 MB, 36 MB | 29, 0.33 GB, 11 MB, 22 MB |
| HBM | 1, 22 MB | 73, 0.82 GB, 10 MB, 31 MB |

Shape density: one 428 x 246 um core (hbm hfd_ep_static, 337 k cells) has 14.0 M shapes, about 130 shapes/um2.
A whole die would be about 1e11 shapes, so it can never be drawn as geometry. With the 5 M budget, real wires
appear when the view is about 200 um wide (wider with layers filtered); above that the raster carries the picture.

FINDING, needs an owner: the design explorer is down. `/api/design/index` on :8766 answers
"design index not built yet". `/srv/opentallas-scratch2/claude/explorer-2-work/state/` and `signed-store/` are gone
(parent dir mtime 11-13 18:22, the cleanup window). The pack store (12 GB) and the code are intact. The design
index must be rebuilt (`design_index.py`) and state/ + store/ added to the cleanup keep set before any new work.

## Recommended architecture

Vector + raster hybrid on the existing deck.gl viewer. Do not add OpenSeadragon/Leaflet and do not prerender PNG
pyramids with KLayout: that would be a second pipeline, about 10x the storage, no net hover or highlight, and it
throws away the verified exporter. Cost scales with unique signed types, not instances.

1. Die composition manifest (new, small): `die_compose/<die>/<plan sha>.json` = for each partition instance
   {node id, pack id or null, x, y, orient, status}, and for each type the placed cores {core node id, pack id,
   x, y, orient} taken from the type's own pack header (`header.macros`), not from the plan, so nested placement is
   what was really routed. Built by `design_index.py` data + plan geometry. Rebuilt on a plan event or re-sign.
2. Viewer: make `layout.js` multi-pack. Today it is one global pack (`V`). Each pack becomes an object with a 2-D
   transform (offset + orient) applied as a shader uniform in `LVRectLayer` and as bounds for the raster bitmaps.
   The orient maths already exists for cells (`orient_apply`, OpenDB dbTransform convention).
3. Level of detail, three bands:
   - die zoom (more than about 3 mm across): today's plan rectangles coloured by status, plus one small composite
     bitmap per unique type (type level-0 raster with its cores' rasters baked in at export time). 205 textures on
     S81, drawn 398 times. The 21,013 core rectangles are not drawn one by one any more.
   - type zoom (about 0.2-3 mm): the per-layer density rasters of the few types in view and of their cores.
   - wire zoom (under about 0.2 mm): vector tiles of the packs that intersect the view (one to four types and
     their cores), exactly as the element page draws them now. Hover, net highlight and layer panel keep working
     inside one pack.
4. Seams and die level, as overlays in the same view:
   - block pins of both types at each seam come from the packs (real geometry); a pin that does not meet its
     partner is visible, which is a useful check in itself;
   - port windows, ft slots and register stations, clock root/taps from the plan (as the design explorer and
     `explorer_render.py die` already draw);
   - die GRT prototype guides (DIE-PROTO chain) as a per-layer congestion heatmap, labelled ADVISORY;
   - when a real die-level routed DB exists, it is cut as one more pack (`<die>.top`) with transform identity.
     No new code is needed for that.

## What can and cannot be shown between types

| area | today | shown as |
|---|---|---|
| inside a signed type or core | routed ODB, pack exists or can be cut | exact wires |
| seam between abutted types | pins on both sides (real), port windows (plan) | exact pins + plan windows |
| ft register stations inside types | real cells in the type pack | exact |
| hard partitions (PHY, HBM, 1-14 % of area) | outline, pins from LEF | outline + pins, "hard IP" |
| uncovered area (3-15 %: ring, channels, corners) | plan only | plan regions |
| die-top signal nets | die GRT prototype with plan-shape abstracts, advisory | guides/heatmap, labelled |
| die PG on M8/M9, clock H-tree and mesh, reset tree | plan and tool outputs, no routed DB | plan overlay, labelled |
| unsigned or re-layout types | no routed DB, sometimes placed/GRT | status-coloured placeholder + plan view |

So corners and inter-type area are not hard to draw; they are mostly empty of real geometry until a die route exists.

## Effort (lane-days, one Opus/Sonnet lane, Fable review at the milestones)

| step | days | reuse |
|---|---|---|
| 0. restore design index + protect store from cleanup | 0.5 | all |
| 1. die composition manifest + coverage report per die | 1.5 | design_index, plan_now.plan_geometry |
| 2. multi-pack viewer with transforms, three LOD bands | 3-4 | layout.js, lv_worker, lv_decode, store, service |
| 3. composite type overview bitmaps at export | 1 | lv_tile raster pyramid |
| M1: S81 at type zoom (signed types exact, rest placeholders) | 6-8 total | |
| 4. seam pins, port windows, stations, clock overlays | 2 | design.js plan view, explorer_render |
| 5. die GRT guide heatmap, cross-pack net follow at seams, search | 2-3 | DIE-PROTO outputs, name tables |
| 6. all 5 dies, phone budget, regression (KLayout XOR window across a seam) | 2 | lv_visual.py |
| total | 12-15 | |

Storage: packs are already paid for by the element pages. Full coverage is about 5-8 GB per large die
(S81, Qwen compute), 1-2 GB for the small ones, about 20-25 GB for all five at one closure each, plus about
1-2 GB of composite bitmaps. `LV_STORE_GB` is 20 today; set it to 60.

## Risks and pitfalls

1. Orientation: two nested transforms (core in type, type in die) with MX/MY/R180. A sign error mirrors a whole
   type silently. Gate: one KLayout XOR window across a seam and across a core edge of a mirrored instance.
2. Units: ASAP7 packs are 1000 DBU/um and exact to 1 nm in float32 only up to 16.7 mm. Dies are up to 32 mm, so
   die coordinates must stay per-pack local + a float64 offset on the CPU (deck does this relative to the camera).
3. Nested cores: a type pack holds the core as a macro (pins + OBS), not its wires. The core pack must be drawn
   on top, and the core closure used must be the one the type was routed against (check LEF hash in the manifest),
   or pins will not line up.
4. Coverage: many types are unsigned or in re-layout, so the first die view will be patchy. The view must show
   status honestly; it will also make coverage gaps very visible, which is the point of a die view.
5. Staleness: packs are immutable per closure. The die manifest must pin plan sha + pack ids and be rebuilt on
   re-sign and plan events; show "plan X, N of M types current" in the header.
6. `__cl<hash>` type variants: 205 S81 masters map to far fewer families. Packs can be shared only between
   identical masters, never by family name.
7. GPU load: the 300 MB cap and the shape budget are per page, so they must be shared across packs. Dense
   power-via arrays stay the slow case.
8. Cleanup: the store and index were already hit once (finding above). Protected paths first.
9. Source DBs: 23 signed nodes had no routed DB left on 11-12 (NO_DB). A pack can only be cut while the ODB exists,
   so the cut must stay hooked to sign-off.

## Phased plan

- P0 (0.5 d): rebuild the design index, bring :8766 back, protect state/ + store/.
- P1 = first milestone (6-8 d): S81 die page where zooming into a signed type shows its routed wires and its
  cores' wires in place, no page change; unsigned types are placeholders. Review on 3 instances: one R0, one MX,
  one R180, each checked against the element page and one KLayout window.
- P2 (4-5 d): seams, stations, clock/PG plan overlays, die GRT heatmap; the other four dies.
- P3 (when a die route exists): cut the die-top DB as one more pack; die nets become real.

Not recommended: a prerendered raster-only viewer (loses nets, second pipeline), or flattening a die into one
DEF/ODB for the viewer (1e11 shapes, and it would go stale at every re-sign).

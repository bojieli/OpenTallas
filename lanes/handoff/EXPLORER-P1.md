# EXPLORER-P1 handoff (11-14), for EXPLORER-FABLE-1

Branch `claude/explorer-p1-1114` @ fe116d035b on hub (READY for ROOT-MERGE-63 posted). Worktree epyc8 `explorer-2-work/p1-sp` (sparse), dev server :8791 `/explorer/design/diemap.html#n=s81`. :8766 untouched.

## Files
- `tools/fleet_viz/die_compose.py` : `python3 -I die_compose.py --die s81[,..] --out $FLEET_VIZ_STATE/die_compose` (needs brotli, reads design_index.json + LV_STORE). Writes `<die>/<plan sha>.json` + `latest.json`. Not yet in refresh.sh (U0 asked to add after design_index.py).
- `design_service.py` : `GET /api/design/compose/<die>` -> latest.json (gzip ok, no-cache); 404 if not built.
- `explorer/design/diemap.{js,css,html}` : engine. `lv_worker.js` now multi-pack (init/tile/raster take `pack`; default '' = element page unchanged). `layout.js` exports `window.LVShared` (shader strings, palette, helpers) and must load before diemap.js, after deck.gl.

## /api/design/compose/<die>
`{schema, die, label, outline:[W,H] DBU, dbu:1000, plan:{path,commit,date}, index_generated, made, summary, packs, instances}`
- `packs[node]`: `{level:type|core, state, job, id (store manifest id), header (object hash), r0 {"0/0_0": hash} (level-0 raster), die [x0,y0,x1,y1] DBU pack-local, dbu, bytes, shapes, n_objects, cores:[{core node|null, name, master, origin[x,y], orient, bbox}]}` (cores = macros from the type pack header, not the plan). One entry per unique master, shared by instances.
- `instances[]`: `{name, node, pack|null, state, x,y,w,h (plan bbox, DBU), orient, ok, why?}`. ok=false when no pack, orient not in R0/MX/MY/R180, or pack die != plan bbox.
- Transform: world = origin + S*local, S=diag(sx,sy) of orient, origin = bbox corner mapped to the lower-left by the flip (MX: y+h, MY: x+w, R180: both). Core = compose(type xf, core origin/orient).
- Pack URLs: `/layout_store/objects/<h[:2]>/<h>.br`; manifest `/layout_store/elements/<node>/<job>.json` (objects table, loaded lazily).

## mountDieLayout(el, opts)  (window.mountDieLayout, returns {zoomTo(bbox_um,pad), select(nodeId), destroy()})
opts: `node` (design-index id: die, type or core; default from `#n=`, `#die=` legacy), `unsigned` (bool, draw non-signed packs as-routed, labelled), `onSelect(nodeId, instName)` on click. View state `#v=x_um,y_um,zoom` (+`u=1`). Colours only from CSS vars (--bg --panel --line --ink --dim --faint --accent --canvas --macro --cellgrey --topbg --tipbg --s-signed|failed|building|queued|waiting|notbuilt|hardip --mono --sans); layer palette is layout.js's PAL. Debug handle `window.DieMap.state()`.

## Verified
- Seam R0|MY (s_3N_x06 | s_4N_x06, x=15975.36 um): 357 block pins each side, every pin matched (layer + y span), abut exactly.
- 831 core placements (4 type orients x 4 core orients) : composed core bbox == recorded macro bbox, 0 mismatch (computed from compose manifest, not rendered).
- Exact geometry at 11 px/um for 2 types (285k shapes); far view = plan + 30 level-0 rasters.

## Known limits
- All 30 signed S81 types with packs are flat slice_station: no cores inside signed packs. Cores in place only visible with `unsigned` (col_h*, leaf types). 5 signed types have no pack (shown as outline).
- Only S81 composed so far; other dies untested (run die_compose --die). Packs are latest closure per node; LEF hash of core vs type not checked (job pinned only).
- Rasters brighten poorly at far zoom (composite alpha); intermediate raster levels need the lazy manifest fetch (1-2 MB per pack).
- No net hover/highlight, no pick of shapes, no seam/PG/clock overlays, no die GRT heatmap (REVIEW-1 P2). Die-top routing does not exist.
- Float32: pack-local exact; offset uses float64 relative to camera. Software-GL screenshots of dense windows take >30 s.
- KLayout XOR not done (no klayout, no DEF handy).
- Budget 3M shapes (1.2M phone), GPU cap 300 MB, geometry only above 0.25 px/um.

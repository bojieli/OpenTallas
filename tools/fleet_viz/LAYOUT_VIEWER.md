# Layout viewer (Chip Explorer element page, Layout tab)

The Layout tab of `/explorer/element/<element>` draws the routed geometry of a closed element from its final OpenDB
database: every wire, via, special (power) wire, block pin, macro pin/OBS, standard-cell pin/OBS and cell outline, on
every routing and cut layer (V0–V9, M1–M9, Pad), at 1 nm (1 DBU) precision. Overlays show the hierarchy-contract
findings, the worst timing paths, the clock tree with arrival colouring, per-layer routing congestion, macro outlines and
module outlines.

## Pieces

| file | runs | role |
|---|---|---|
| `tools/layout_viewer/lv_extract.py` | ORFS container (`openroad -python`), on the host holding the DB | lossless OpenDB extraction: wires (`dbWirePathItr`) plus RECT patches (decoded from the wire opcodes, because `dbWirePathItr` skips them), vias with a via-type table that holds the exact cut and enclosure boxes, special wires and special vias, block pins, obstructions, fills, instances (origin, orient, master) with per-pin nets, the master table (pin and OBS boxes), name tables, track grids. It also writes `truth.i32`, the canonical expanded shape set as OpenDB itself produces it (`dbInstShapeItr`, `dbSBox.getViaBoxes`). |
| `tools/layout_viewer/lv_tile.py` | numpy + brotli, beside the extraction | cuts the **pack** (`.lvp`): header, 25.6 µm geometry tiles split into one section per layer plus vias and cells, a 256² density-raster pyramid per layer, the congestion grid, lint findings, name tables, search side tables, and the DB truth summary (per-layer count, bbox and 2×32-bit order-independent hash) |
| `tools/layout_viewer/lv_lint.py` | inside `lv_tile.py` | contract findings with geometry. It applies `tools/hier_contract/child_lint.py` (b) PG pins not full stripes, (c) signals or OBS on the parent strap layer, and (f) covered edge (face) pins, both to the element as a hard child and to every macro placed in it. It adds off-grid macro pins via the DRT-0419 centre test (`check_macro_track_alignment.check_placement`) against the DB's own track grids. |
| `tools/layout_viewer/lv_verify.js` | node | round trip. It decodes every tile with the viewer's own decoder, re-joins clipped pieces by shape id, expands vias and cells exactly as the viewer draws them, and compares each layer with the DB truth summary. Exit 0 means IDENTICAL. |
| `tools/layout_viewer/lv_visual.py` | here (KLayout ≥ 0.29 python module + Playwright) | independent regression against KLayout reading `6_final.def` + LEFs: per-layer XOR area over the whole die, and pixel IoU of a window, KLayout render vs the viewer's `?lvsolid=1` render |
| `tools/fleet_viz/layout_store.py` | fleet-viz host | export pipeline and the static store (below); CLI `export / backfill / gc / status` |
| `tools/fleet_viz/layout_service.py` | inside `server.py` | `/layout_store/…` static files, `/api/layout/<el>/…` (status, on-demand fallback, name lookup, search) |
| `tools/fleet_viz/explorer/element/layout.js`, `lv_worker.js`, `lv_decode.js`, `vendor/deck.gl-8.9.36.min.js` | browser | the viewer |
| `tools/layout_viewer/lv_post_record.sh` | closure loop (detached) | post-record hook: waits for the element-page export, then `layout_store.py export --job <job>` |

## Static store (closed elements)

Owner design (2026-10-11): an element is cut **once, at closure**. The export is immutable and served as plain static
files; nothing is cut at view time for closed elements.

```
~/.local/share/fleet-viz/layout_store/        (LV_STORE)
  objects/<h[:2]>/<sha256>.br                 content-addressed brotli blobs, shared across elements and closures
  elements/<el>/<job>.json                    manifest of one closure: closure record (job, status, commit, slacks, DRC,
                                              bench, page facts), round-trip verdict, logical name -> object hash
  elements/<el>/index.json                    {latest, history: newest first, at most 3}
  STATUS.json                                 per-element export state; `no_db`: closed elements whose DB is gone
  SIZE.json                                   store size vs the 20 GB budget (LV_STORE_GB), per element
```

* **Source of the DB.** First choice is the closed-layout archive on this host (`~/closed_archive/<el>/<job>/`, written by
  closed-archive-1011), cut here in the ORFS container (nice 19, 2 CPUs, memory cap, one cut at a time). Otherwise the
  job's fleet host, cut there under `ot-heavy` (ot-epyc4 is streamed through this host to ot-epyc3). A DB found
  under the job's run dir counts as well.
* **Verify before publish.** Every pack must pass `lv_verify.js` (IDENTICAL) before it enters the store. The verdict is
  stored in the manifest and shown in the viewer's Closure section.
* **History.** A newer closure becomes `latest`. The previous closures stay selectable in the viewer (Closure → history),
  capped at 3. `gc` deletes objects that no manifest references.
* **Backfill:** `python3 ~/.local/share/fleet-viz/layout_store.py backfill`. It covers every CLOSED element of the
  registry in priority order (element pages first, then DeepSeek, HBM, Qwen), with one queue per DB source and 2 cuts per
  queue. Log: `~/.local/state/layout-viewer/backfill.log`.
* **New closures.** The closure loop's one-line hook (branch `layout-viewer-1011-loop-hook`) starts
  `lv_post_record.sh <job>`.

Elements that are not closed (or not exported yet) fall back to an on-demand cut into a bounded LRU cache
(`~/.cache/layout-viewer`, `LV_CACHE_GB`, default 8). The viewer shows the cut stage while it waits, and offers the
Placement view in the meantime.

## Pack / tile format (schema `opentallas.layout_viewer.pack.v1`)

Every blob is brotli-compressed on its own. Tiles are 25.6 µm leaf tiles over the die, one blob per section:
`t/<x>_<y>/L<layer>`, `t/<x>_<y>/v` (vias) and `t/<x>_<y>/c` (standard cells). Section payloads are LEB128 column
streams:

* **Rectangles** are sorted along the layer's preferred direction (track order). The major coordinate is
  delta-coded; the minor coordinate is delta-coded when the major repeats. Then come w, h, a net delta, kind and clip
  bits.
* **Clipped pieces.** A rectangle that crosses tile edges is cut into pieces. Each piece carries clip bits (which edges were cut, so no
  outline is drawn there) and the shape id, so the decoder can re-join the exact DB rectangle.
* **Vias** are (x, y, via type, net, kind). The via-type table in the header holds the exact cut and enclosure boxes.
* **Cells** are (origin, orient, master, instance, flags) plus the per-pin net list. Shapes come from the master table,
  transformed with OpenDB's `dbTransform` convention.

The density rasters are the exact per-pixel coverage of each layer, computed with a 2-D ramp-integral
(`lv_tile.coverage`). Finest pixel is 0.4 µm, with 2×2 means above it.

## Viewer

* **Rendering.**
  * Uses deck.gl 8.9.36 (vendored; WebGL2) with one custom instanced-rectangle layer per loaded tile.
  * Per-layer colour, stipple (10 patterns), opacity, visibility and the highlighted net are shader uniforms, so a toggle
    never rebuilds buffers. Shapes keep a 1-device-pixel minimum size.
  * Outlines are suppressed on clipped edges.
  * Coordinates are absolute DBU in float32, which is exact to 16.7 mm; deck's identity projection works relative to the
    camera, so precision holds at every zoom.
* **Level of detail.** Geometry is drawn when the visible shape estimate (from the per-tile, per-layer counts in the
  header) is within the budget: 5 M on desktop, 1.6 M on phones. Otherwise the density raster level whose pixel is about
  one screen pixel is drawn. Tiles load centre-first with a one-tile margin, in workers. Only the sections of visible
  layers are fetched. GPU memory is capped at about 300 MB (LRU eviction).
* **UX.**
  * Layer panel with swatches, visibility, opacity and solo.
  * Presets: All, Signals only, Power grid, M6+ die contract. Shape-kind filters. Classic palette or colour-blind-safe
    palette. Dark and light themes.
  * Navigation: scroll zoom, drag pan, pinch, double-click, keyboard. Minimap. Fit (F). µm coordinates and a scale bar.
    Ruler (R).
  * Hover shows the layer, kind, net, instance/master/pin, size and position. Click highlights the whole net across
    layers.
  * Search for nets and instances (server-side over the name tables).
  * View state lives in the URL (`#tab=geo&v=x,y,zoom&h=hidden&k=kinds&n=net&o=overlays&f=finding&j=closure`).
  * `?perf=1` shows fps, frame p95, loaded instances, GPU MB and first-paint times. `?lvsolid=1` is the regression render.
* **Overlays.**
  * Contract findings, each clickable with its reason and fix and drawn on its shapes.
  * Worst setup and hold paths (from the element export).
  * Clock tree edges and sinks, coloured by TT arrival.
  * Per-layer congestion: signal-track utilisation per bin (coverage × pitch / width), with p50/p99/max per layer.
  * Macro outlines and module outlines (RTL blocks from the placement data).
* **Share-safe view** (`?safe=1` or proxied requests): geometry only. Names, search and raw manifests are withheld; header
  and lint are redacted.

## Validation (2026-10-11)

* **Round trip vs OpenDB**, measured by `lv_verify.js`: IDENTICAL on every exported element. The backfill refuses to
  publish anything else. Reference cases:
  * ot_mtp_hist_ring_p (52 µm leaf): 641,291 shapes, plus an exact sorted-list equality with `truth.i32`.
  * ot_hgi_seq (360 µm tile): 19,177,076 shapes.
  * dsfd_coll_cbq0 (78 × 340 µm): 6,166,058 shapes.
* **KLayout 0.29.12, independent DEF/LEF reader**, on ot_mtp_hist_ring_p: XOR area 0 nm² on M1–M7 and V1–V6 over the
  whole die.
  * The first comparison found 9 nm RECT patches that `dbWirePathItr` silently drops. The extractor now decodes them
    from the wire opcodes.
  * KLayout needs `macro_resolution_mode = 1` plus the obstruction and LEF-pin suffixes on the plain layer; that gives
    the same composition as the viewer's layers.
* **Pixels.** On a 2.5 µm window at 240 px/µm, IoU after a ≤1 px registration shift is 0.94 (M2), 0.81 (M3), 0.89 (M4)
  and 0.96 (M5). There are essentially no differing pixels beyond 1 px of an edge on M2–M5 and V2.

## Known gaps

* **No GPU fps measured yet.** Headless Chrome on the fleet-viz host only gets llvmpipe; the RTX's EGL and Vulkan stack
  hangs, `vulkaninfo` included. Numbers measured there are software lower bounds. Use `?perf=1` on a real browser.
* Cell outlines and pins of physical-only cells (filler, tap, decap) are not drawn until the "Filler / tap" layer is
  switched on. Their M1 rails coincide with the follow-pin straps.
* Module outlines are bounding boxes of the module's cells, not hulls.

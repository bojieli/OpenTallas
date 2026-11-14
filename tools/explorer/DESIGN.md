# OpenTallas Explorer: DESIGN (EXPLORER-FABLE-1, 2026-11-14)

One web tool for the 5-die chip (S81, HEAD, QC, KV, HBM). New front end, built end-to-end from REQUIREMENTS.md.
The proven data engines stay as back-end libraries behind one API. Code: `tools/explorer/` on branch
`claude/explorer-fable-1-1114`. Dev service: epyc8 `:8770`. The live service on `:8766` is not touched.

## 1. What is kept and what is new

| kept as an engine (not rewritten) | where | used through |
|---|---|---|
| layout pack cutter and store (`lv_extract`, `lv_tile`, `layout_store`, `lv_verify` IDENTICAL) | `tools/layout_viewer`, `tools/fleet_viz/layout_store.py` | `/api/v1/store/...` (immutable blobs) |
| pack tile decoder + worker (`lv_decode.js`, `lv_worker.js`, multi-pack from P1) | `tools/fleet_viz/explorer/element/` | loaded as-is by the new layout engine |
| deck.gl 8.9.36 (vendored, WebGL2) | same `vendor/` | layout canvas only |
| design index and node ids (`design_index.py`, `design_service.py`) | `tools/fleet_viz` | `/api/v1/dies`, `/die`, `/node`, `/resolve` |
| die composition manifest (`die_compose.py`, EXPLORER-P1) | `tools/fleet_viz` | `/api/v1/compose/<die>` |
| token simulator records + token-to-node map (`token_path_export.py`, `token_design_map.py`) | repo + state | `/api/v1/token/...` |
| data-flow link records and link model (`dataflow_links.py`, `model.js`) | repo | `/api/v1/dataflow/...` |
| coverage ledger (`coverage.py`) | repo | `/api/v1/coverage` |

New: everything the user sees. One shell, one router, one selection, one design system, seven views, one
layout engine for die scope and element scope, one API server (`tools/explorer/server.py`), Playwright tests.
Nothing in `tools/fleet_viz` is edited, so `:8766` and the owner's `:8765` keep working until the switch.

## 2. Information architecture

One page. Five regions, all of them the same in every view:

```
+--------------------------------------------------------------------------------------------+
| top bar: product | die switcher | breadcrumb die > type > core | search (/) | freshness | theme |
+----+----------------+-------------------------------------------------+--------------------+
|rail| navigator      | stage: view toolbar + canvas / page             | inspector          |
|    | (tree, filter) |                                                 | (details, tabs)    |
| 7  | resizable      | focus mode: \ ; browser full screen: Shift+\    | resizable          |
|view| collapsible [  |                                                 | collapsible ]      |
+----+----------------+-------------------------------------------------+--------------------+
| status bar: view read-out (cursor um, zoom, LOD) | data as of ... | plan <sha> | service <sha> |
+--------------------------------------------------------------------------------------------+
```

Views (left rail, keys 1-7). Each view shows the current selection; changing view never loses it.

| # | view | question it answers | scope |
|---|---|---|---|
| 1 | Overview | where does each die stand, how fresh is the data | chip |
| 2 | Plan | what is the floorplan: partitions, seams, clock, PG, cores; a type's plan contents | die or type |
| 3 | Layout | the die with the real routed wires of every signed type and core, in place (P1 engine) | die |
| 4 | Element | one type or core in full: status, metrics, routed layout, paths, clock tree, nets, history | type or core |
| 5 | Dataflow | which blocks talk, how wide, how far, within reach or not | die |
| 6 | Token | where one token spends its cycles, mapped to current nodes | token design |
| 7 | Closure | sign-off status table and matrix for every type and core; architecture coverage ledger | die / chip |

Panels:
- Navigator (left): die > status group > type > core tree with a filter box and status dots. Width 180-520 px by
  dragging the edge, double-click resets, `[` or the chevron collapses it to nothing.
- Inspector (right): details of the selection, the same component in every view; a view may add tabs
  (Layers, Paths, Clock, Net). Width 260-720 px, `]` or the chevron collapses it.
- Stage: `\` hides rail, navigator, inspector, top and status bars (focus mode, canvas fills the window);
  `Shift+\` asks the browser for true full screen. `Esc` leaves. A button for each is in the stage toolbar.
  `F` stays "fit the canvas", as in the old viewer and in layout tools.
- Sizes, collapsed state and theme persist in localStorage. Under 900 px width the two panels become drawers.

Navigation rules: no page reloads, no pop-ups, no second header. Every cross-reference is a link to
`#/<view>/<node>`; the breadcrumb is always die > type > core; Back/Forward work.

## 3. Identity model and URL

Canonical ids are the design-index node ids. Nothing else is stored in a URL.

| thing | id | example |
|---|---|---|
| die | `<die>` | `s81`, `s81_head`, `qwen_compute`, `qwen_kvsys`, `hbm` |
| type (partition master) | `<die>.t.<type>` | `s81.t.iqf__t1` |
| core (hard-core module) | `<die>.c.<module>` | `s81.c.ot_s81sl_vq` |
| instance (a placement of a type in the die) | `inst=<partition name>` | `inst=s_3N_x06` |
| core instance inside a type | `inst=<partition>/<core inst>` | `inst=fW0_p1_b0/u_r0.u_bn0` |
| net (inside one pack) | `net=<name>` (resolved to the pack's id by the names API) | `net=clk_i` |
| lane / link (data flow) | `lane=<link id>` | `lane=L123` |
| token group / operator | `tok=<design>:<group>[:<op>]` | `tok=ds_rom:su` |

Selection object held by the shell: `{die, node, inst, net, lane, tok}`. One URL scheme:

```
#/<view>/<node id>?inst=..&net=..&lane=..&tok=..&<view params>
#/layout/s81.t.iqf__t1?inst=iqf&cam=3104.2,880.5,1.25&hide=M1.M2
```

- Selection keys (`inst net lane tok`) survive a view change. View params (`cam`, `hide`, `ov`, `tab`, ...) belong
  to one view; the shell remembers them per view for the session, so coming back restores the camera.
- `history.pushState` on a selection or view change, `replaceState` on camera moves (debounced).
- Old links are accepted and rewritten at boot: `#n=`, `#q=`, `#element=`, `#design=`, `#die=`, `#t=`, and the old
  page paths (`/explorer/design/`, `/explorer/element/`, `/explorer/dataflow/`, `/explorer/token/`,
  `/explorer/coverage/`) redirect to the matching view. Names go through `/api/v1/resolve`.

## 4. Data freshness

Every dataset has a row in `/api/v1/meta`: `{id, label, generated, age_s, source, plan: {die: {path, sha, commit,
date}}, stale_after_s, state: fresh|stale|missing}`. The shell shows:
- a freshness chip in the top bar (worst state of the datasets the current view uses; click opens the list);
- "data as of <time> · plan <sha>" in the status bar of every view, from the datasets that view declares;
- a banner inside a view when its dataset is stale or belongs to another plan than the plan of record
  (the October token and data-flow records say so in plain words instead of looking current).

## 5. Visual design system

- Tokens in `web/css/tokens.css` only; no hex literal anywhere else (checked by a test). Light and dark, both
  selected, switch on `data-theme` (default follows the OS).
- Neutral, quiet chrome so the layout colours carry the picture: surface 0/1/2, line, ink 1/2/3, one accent.
- Type: system sans for UI (13 px base, 12 px dense tables, 11 px captions), system mono for ids, nets, numbers.
  Tabular numerals in tables. 4 px spacing grid, 6 px radius, 28 px control height, 44 px top bar.
- Sign-off state colours (reserved, never reused for series, always with a label): signed, failed, building,
  queued, waiting, not built, hard IP. Verdict colours (within reach / relay / over) likewise.
- Categorical series (token classes, data-flow groups): the validated 8-slot palette in fixed order.
- Routing-layer palettes (classic and colour-vision-safe, with stipples) are data of the layout engine and are
  kept exactly, because the regression images depend on them.
- Components (classes in `app.css`, helpers in `dom.js`): button, segmented control, checkbox row, slider, chip, status dot, key-value list,
  data table (sort, filter, sticky head, row link), tabs, tooltip, menu, splitter, toast, empty/error/loading
  states. Every interactive control has a `data-testid`, a title, and a keyboard path.

## 6. Front-end architecture

Stack: plain ES modules, no framework, no bundler, no node in the serve path. The app is canvas and WebGL work
plus small panels; a build chain would add a moving part and no capability. deck.gl stays for the layout canvas.

```
tools/explorer/
  server.py            stdlib HTTP server: static web/ + the /api/v1 handlers (imports the fleet_viz engines)
  web/index.html
  web/css/             tokens.css (all colour) app.css (shell + components) views.css
  web/js/app.js        boot, legacy-URL rewrite, view registry
  web/js/core/         store.js (selection + URL), api.js (fetch + cache), dom.js (DOM, format, icons)
  web/js/shell/        shell.js (bars, panels, splitters, focus mode, search, freshness) navigator.js inspector.js
  web/js/engine/       layout-engine.js (multi-pack deck.gl renderer) plan-canvas.js (2-D floorplan canvas)
  web/js/views/        overview.js plan.js layout.js element.js dataflow.js token.js closure.js
  tests/               Playwright (pytest): every view, every button
```

View contract: `{id, title, icon, datasets, mount(host, ctx)}` returning `{update(sel, params), destroy()}`.
`ctx` gives the store, the API client, the inspector and toolbar slots. A view never touches the URL or another
view's DOM; it calls `ctx.select({...})` and `ctx.setParams({...})`.

Layout engine (one for both scopes): a scene is `{outline um, items: [{pack, transform, level, state, name}]}`.
Die scope = the composition manifest (398 placements on S81, each pack reused); element scope = one pack at
identity. Coordinates stay pack-local integer DBU in float32; the die offset is added in float64 relative to the
camera (P1's method), so a 32 mm die loses no precision. LOD bands: plan rectangles + level-0 rasters far out,
finer rasters closer, exact vector tiles inside the shape budget (3 M desktop, 1.2 M phone; 300 MB GPU cap,
shared across packs). Hover, net highlight, search, ruler, minimap, scale bar, layer/kind visibility, opacity,
solo, presets, palettes; overlays: macros/cores, timing paths, clock tree with arrivals, congestion, seams and
plan windows, unsigned as-routed packs (labelled).

## 7. API contract (`/api/v1`)

All JSON, gzip, `Cache-Control: no-cache` except the immutable store. Errors: `{error, detail}` with 4xx/5xx.

| endpoint | returns |
|---|---|
| `GET /api/v1/meta` | service sha, datasets with freshness (section 4), dies list |
| `GET /api/v1/dies` | per die: label, target, outline, counts by state, plan {path, sha, commit, date}, packs exported |
| `GET /api/v1/die/<die>` | die node (plan: partitions, seams, clock, PG, landing) + slim rows of its types and cores |
| `GET /api/v1/node/<id>` | full node + children + users + placements + pack history |
| `GET /api/v1/compose/<die>` | die composition manifest (packs, instances, transforms, summary) |
| `GET /api/v1/closure/<die>` | one row per type and core: state, label, stage, attempt, metrics, pack, visual verdict |
| `GET /api/v1/resolve?q=a,b` | names (type, core, partition, old element, token class, data-flow block) -> node ids |
| `GET /api/v1/search?q=&die=` | ranked nodes and instances for the search box |
| `GET /api/v1/layout/<node>/names?k=net|inst&ids=` , `/search?q=` | name tables of one pack |
| `GET /api/v1/store/objects/<h2>/<hash>.br` , `/store/elements/<node>/...` | immutable pack blobs and manifests |
| `GET /api/v1/dataflow/index` , `/dataflow/record/<id>` | link records, with plan and generated time |
| `GET /api/v1/token/index` , `/token/record/<design>` , `/token/map/<design>` | token records and the node map |
| `GET /api/v1/coverage` | architecture coverage ledger |
| `GET /health` | per-dataset check, 200 only when all required datasets answer |

The server is a thin adapter: it imports `design_service`, `layout_service`, `die_compose`, `coverage` from
`tools/fleet_viz` and reads the same state directory and pack store (`explorer2.env`), read-only.

## 8. Testing

Playwright (Python, headless Chromium, already on epyc8) under `tools/explorer/tests/`:
- smoke per view on 3 dies: loads, no console error, no failed request, freshness shown;
- every control with a `data-testid` is clicked and must change the DOM, the URL or the canvas (no dead buttons);
- shell: resize, collapse and restore both panels; focus mode and Esc; theme; deep link round trip; Back/Forward;
  selection kept across all seven views; old URL schemes rewritten;
- layout engine: far view draws rasters, zoom draws exact tiles, a mirrored instance matches the element view;
- screenshots saved per view (light and dark) for the STATE posts;
- static check: no hex colour outside `tokens.css` and the engine palettes.
`python3 -m pytest tools/explorer/tests -q` is the gate for each milestone.

## 9. Deployment and switch

- Now: `server.py --port 8770` on epyc8 beside the store, env from `explorer2.env`; tunnel requested from
  EXPLORER-U0/COORD. `:8766` keeps serving the old pages.
- Switch (after M5, COORD decides): the `explorer2.service` unit starts `tools/explorer/server.py` from the pinned
  checkout; old page paths redirect into the new app; `tools/fleet_viz/explorer/{design,dataflow,token,coverage}`
  page files are retired in a later cleanup, the engines stay.

## 10. Milestones

| M | content | check |
|---|---|---|
| 1 | shell, navigation, panels, identity/URL, freshness; Overview, Plan, Layout (die route view) | screenshots, shell tests |
| 2 | Element detail with routed layout, paths, clock, nets, history | element tests on 3 dies |
| 3 | Dataflow and Token views on the kept models | view tests, stale banners |
| 4 | Closure status table/matrix and coverage ledger | table tests |
| 5 | Playwright green on every view and button; old-URL redirects | full suite |

# OpenTallas Explorer: feature inventory of the existing tools

Author: EXPLORER-FABLE-1-INV. Date of observation: 2026-11-14 09:40 to 10:25 PT, host epyc8. Read-only; nothing served was changed.
Code read: `epyc8:/srv/opentallas-scratch2/claude/explorer-fable-1/wt/tools/fleet_viz/` (worktree). Observed live: 8766 (main) and 8791 (dev, has the die map).
Browser: Playwright Chromium, SwiftShader WebGL, 1600x1000 and 390x844. Host load average was 70 to 220 during the run, so timings are pessimistic and a few "Failed to fetch" tile warnings may be load artefacts (flagged where relevant).
Screenshots: `shots-old/` (names quoted below). Raw run logs: `inv-tmp/out-*.txt`, `lout-*.txt`, `sout-*.txt`.

Status vocabulary: works = observed to do what the code says; broken = observed failure; partial = works with a visible defect or only part of the function; not verified = could not exercise.

## 0. Findings that cut across all tools

### 0.1 Servers and what is actually served (important for the redesign)
| port | process | what it serves | notes |
|---|---|---|---|
| 8766 ("main") | `design_dev_server.py --port 8766` (started 16 min before the run, pre-die-map checkout) | `/explorer/design/`, `/explorer/element/`, `/explorer/dataflow/`, `/explorer/token/`, `/explorer/coverage/`, `/api/design/*`, `/api/layout/*`, `/layout_store/*`, `/api/coverage*`, `/api/plan_now`, `/fv_stale.js` | `diemap.html`, `diemap.js`, `/api/design/compose/<die>` are 404 here. `/api/explorer/*`, `/api/native/coverage`, `/fv_flow.js`, `/explorer.html`, `/explorer.js`, `/api/fleet` etc. are 404 (that is the legacy fleet-viz `server.py`, not running here). |
| 8791 (dev) | `design_dev_server.py --port 8791` | same plus `diemap.html`, `diemap.js`, `/api/design/compose/<die>` (200 KB) | the die map exists only here |
| 8767 | `design_dev_server.py --port 8767`, up 2 days | not probed | not verified |
| (owner machine) | fleet-viz `server.py` | `/` fleet page (`index.html`), `/explorer` old chip explorer (`explorer.html`), `/explorer/design/` etc. | not reachable from epyc8; old explorer inventoried from code only |

On this server `/`, `/explorer` and `/explorer/` all redirect or serve the design explorer. Every "Chip Explorer", "Fleet" and `/explorer` link in the other pages therefore lands on the design explorer, with a meaningless hash for the old explorer (see D-nav bugs).

### 0.2 Navigation and cross-links (owner complaint d): confirmed
Link matrix observed in the browser (from page row, to column; "-" means no link at all):
| from \ to | design | diemap | element | dataflow | token | coverage | fleet |
|---|---|---|---|---|---|---|---|
| design (die/type/core) | self | **-** | **-** | "Dataflow" button (die to design id map) | **-** | **-** | **-** |
| diemap | **-** (no `<a>` on page, zero links) | self | - | - | - | - | - |
| element | "Chip Explorer" crumb (`/explorer`) and legacy banner link to `#n=` | - | self | - | - | - | - |
| dataflow | block link in side card (only for `plan_*` records, none exist), "Chip Explorer" | - | - | self | "Token Explorer" | - | - |
| token | "Chip Explorer" | - | `a.tp-el` links go to design `#q=` | panel and link to dataflow | self | "Coverage" | - |
| coverage | "Chip Explorer", cell drawer links to design `#q=`/`#n=` | - | - | - | "Token path" per target (AR/MTP/DFlash) | self | "Fleet" (`/`) |

There is no shared header or nav. Each page has its own top bar with a different set of links, different style, different label for the same destination. The die map (diemap.html) is not linked from anywhere (grep: 0 occurrences of `diemap` in design.js, index.html, design_service.py).

### 0.3 URL state schemes (all hash based, no shared parser)
| page | hash parameters |
|---|---|
| design | `n=<node id>` (die `s81`, type `s81.t.<name>`, core `s81.c.<module>`), `v=plan\|layout`, `from=<type node id>` (core breadcrumb), `q=<name>` (resolve to node(s)), `die=` (only used with `q`) ; while the layout viewer is open it also writes `tab=geo`, `v=<x>,<y>,<zoom>` (collides with the plan/layout `v`), `h=` hidden layers, `k=` hidden shape kinds, `o=` overlays, `net=` selected net, `f=` selected finding, `j=` closure job |
| diemap | `n=<node id>`, `v=<x>,<y>,<zoom>`, `u=1` (show unsigned), query `?unsigned=1`, `?phone=1` |
| element | path `/explorer/element/<id>` or `?e=<id>` or `?p=<page id>`, `?safe=1`, `#tab=<geo\|layout\|timing\|arrival\|tree\|density\|rtl\|facts\|how>`; layout viewer adds `v,h,k,o,n,f,j` |
| dataflow | `design=qwen_rom\|ds_rom\|hbm_gen_qwen\|hbm_gen_ds`, `die=<record id>`, `t=<cycles>` |
| token | `design=`, `mode=mtp` (omitted for ar), `group=<stage id>` e.g. `S029` |
| coverage | `t=T1,T2,..` (visible targets), `phase=`, `plane=`, `group=`, `owner=`, `gap=<classes>`, `only=1`, `beyond=1`, `q=`, `cell=<fid>@<T>` |
| old explorer | `die=`, `master=`, `element=`, `story=`; `?safe=1` |
Overloaded names: `v` means plan/layout on design but x,y,zoom on diemap and layout viewer; `n` is a node id on design/diemap but a net id on the element page; `die` is a die id in design/old explorer but a dataflow record id in dataflow; `q` is a name to resolve on design but a text filter on coverage.

### 0.4 Styling approach
Every page defines its own CSS: inline `<style>` in design/element/dataflow/token/coverage/diemap html plus per-tool css files. Common intent: CSS custom properties (`--bg --panel --line --ink --dim --accent --s-signed ...`), dark by default.
* design and element: dark tokens, light override via `@media (prefers-color-scheme: light)` and `[data-theme]`; Theme button stores `localStorage otx.design.theme` / `otx.elem.theme`. Headless Chromium has no dark preference, so the first screenshots of these pages are light.
* diemap: its own copy of the dark tokens ("stand-in for the shell's tokens.css"), no theme switch, no light mode.
* dataflow: dark colours hard-coded as literals in index.html and dataflow.css, no theme switch.
* token: hard-coded hex in token.js template CSS (`.tp-x ...`), injected at runtime; no theme switch.
* coverage: own coverage.css, dark, no theme switch.
* Result: 3 different dark palettes plus 2 light themes, status colours defined 3 times (`--s-*` in design, `--st-*` in old explorer, `--s-closed/enc/open` in element shell.css).
* Layout viewer panels inside the design page use classes (`.lv-*`) styled in design/index.html, but several element-page classes it also emits (`.rampl`, `.tw`, `table.t`, `.ctl`, `.u`, `.note`) are not defined there, so those blocks render unstyled (shots-old/design-type-desk.png: clock ramp labels run together "0 psclock arrival (TT, p1..p99)1 ps"; congestion table unformatted).

### 0.5 Data freshness shown to the user
| page | freshness visible? |
|---|---|
| design die | plan commit + date line ("commit 165da7676d 2026-11-12") but the index `generated` time (2026-11-14 10:00:39Z, regenerated live) is never shown; layout block shows export time `made` |
| diemap | no date; header shows plan file name only |
| element | none observed (data not loaded) |
| dataflow | **no date shown**; its data are 2026-10-15/16 (22 records) while the die plans are 2026-11-12 to 11-14 |
| token | banner "Current token-pass state . release tree Nov 14, 08:31 ... the token-path model below is the analytic record of Nov 14, 09:28, not a token pass"; model block "GRADED COMPOSITION 10-18"; the record itself is October |
| coverage | yes: "loaded 2026-11-14 09:38:47 . matrix 8b704a0fd5... . element status 9:55:39 AM" (timezone mix) and `fv_stale.js` indicator |

### 0.6 Owner complaints, verdicts
| complaint | verdict | evidence |
|---|---|---|
| (a) layout canvases cannot go full screen | **confirmed** | no fullscreen/maximize control on any page (grep for `fullscreen|requestFull|maxim` in all front end files: 0 hits; DOM scan for such labels: none); `#geo` is fixed to the centre grid cell, 900 x 954 px of 1600 x 1000 at desktop (shots-old/design-type-desk.png). `document.fullscreenEnabled` is true, `requestFullscreen` exists but no UI calls it. Pressing F only fits the view. diemap is the only page with a full-width canvas, but its side bar is fixed 210 px. |
| (b) details panels cannot be hidden or resized | **confirmed on design and diemap; element page can hide, not resize** | design: keys `[` `]` do nothing (GEOM identical before/after), no handles, dragging the column borders by 200/150 px changed nothing (lcol 300 px, rcol 400 px fixed in CSS grid). diemap: side bar 210 px fixed, `display:none` below 980 px so the layer panel is unreachable on phones. element: `lbtn`/`rbtn` and keys `[`/`]` toggle columns (works, remembered in localStorage `otx.elem.nol/nor`); no resize. dataflow, token, coverage: fixed panes. |
| (c) some buttons broken | **confirmed**, see per-tool bug lists. Click log below. | |
| (d) navigation cluttered / pages not linked | **confirmed** | section 0.2: zero links to the die map, no common header, 6 different top bars, `/explorer` target is wrong on this server. |

### 0.7 Click log summary (every button was clicked; full per-control results are in the section tables and `inv-tmp/out-*.txt`)
Controls with no observable effect (DOM, URL, network, console) are listed under each tool as "nothing observed" bugs when they are not already the active state.

---

## 1. Design explorer: die / type / core pages (`explorer/design/index.html` + `design.js`, 363 lines)
Entry `/explorer/design/` (also `/`, `/explorer`). Loads: `/explorer/design/` 14.8 KB, `design.js` 30 KB, `/explorer/element/layout.js` 68 KB, `lv_decode.js` 8 KB, `/api/design/index` 1.1 KB (gz), `/api/design/die/<die>` 510 KB gz (4.5 MB raw, 0.38 s), `/api/design/node/<id>` 1 to 130 KB; layout view adds deck.gl 1.59 MB, store manifest 1.87 MB (`/layout_store/elements/<id>/<job>.json`), brotli objects (36 requests at open, several hundred while panning), timing object `/layout_store/objects/xx/<hash>.br` (294 KB for the sample). Load to first paint about 5 s under load. State: hash (section 0.3). Screens: design-die-desk.png, design-die-phone.png, design-type-desk.png, design-type-phone.png, design-typeplan-*.png, design-core-*.png.

### 1.1 Features and controls
| feature | what it is for | data source | status | notes |
|---|---|---|---|---|
| Breadcrumb `S81 > [from-type] > node` | location, up-navigation | design.js `render()`; `from` hash param | works | die crumb always present; core crumb shows "core of N types" unless `from` given; crumbs are links with `#n=` |
| View segment `Plan` / `Routed layout` | switch node view | hash `v`; `has = node.layout.store` | works; `Routed layout` disabled with a title when no pack | default for node with pack = layout; for a core, Plan is default-off (see bug 1.5) |
| `Dataflow` button | open the dataflow page for this die | hard map die to design id (`ds_rom`, `qwen_rom`, `hbm_gen_ds`) + `&die=plan_<die>` | partial | the record `plan_<die>` does not exist in dataflow `index.json`; the dataflow page silently falls back to the October canonical record (see 4.x) |
| `Theme` button | light/dark | `data-theme`, localStorage `otx.design.theme` | works | |
| Dies list (left) | switch die with progress `35/204 types` | `/api/design/index` | works | 5 dies listed, click changes hash and reloads `/api/design/die/<die>` |
| Types-by-status legend (7 checkboxes) | hide a sign-off state on the die plan | `S.hide`, die canvas | works | die page only; counts per state; label says "click to hide" |
| Overlays (6 checkboxes: seams, hard cores inside slots, clock root/spine, PG domains, landing cohort of hovered type, partition names) | toggle plan layers | `p.seams`, `hard_cores`, `p.clock`, `p.pg_domains`, `landing_base` | works (redraw only, no network) | die page only; clock "H-tree" is a 2-level topology sketch, not routed geometry |
| Types filter box + list | find a type, sorted by status then name | `S.die.nodes` | works | lists all 205 types (no virtualisation); rows show `layout` tag and instance count; selection highlights `.on`; list scroll max 46 vh |
| Die canvas (2D canvas, to scale) | plan of record: partitions coloured by sign-off, seams, clock root star, PG dashed boxes, hard cores | `die.plan.partitions/seams/clock/pg_domains` | works | wheel zoom, drag pan, click slot opens type, hover tooltip + Hover panel, key `F` fit; hint bar bottom-left |
| Hover tooltip + `Hover` card (right) | partition name, type, status, LEC, hard core count, routed layout flag | die node | works | shots-old/design-die-hover.png |
| Right panel, die: Plan (file, commit, subject, outline, period, reach, partitions, seams, clock, PG), Sign-off counts, note "Die-level route has not run yet" | plan provenance | `die.plan` | works | no timestamp of the index; the "not routed" note conflicts with the new die map |
| Right panel, type: title, status badge + label, metrics (TT setup WNS, FF hold WNS, DRC, GRT overflow, LEC, cells), Routed layout facts (source, stage, DB, signed record, archive, DB size, exported, paths/clock), Hard cores list (links with `&from`), Plan contents (face buses, ft slots, stations, taps, placements), Visual review (VIS-SWEEP verdict) | per-type facts | `/api/design/node/<id>` | partial | for the sample type `s81.t.iqf__t1` (status BUILDING) the Routed layout block shows blank `source`, `stage ?`, `DB —` (shots-old/design-type-desk.png) |
| Type Plan view (2D canvas) | outline, face-window bars (cyan in / orange out), grey ft slots, station polylines, hard cores coloured by status, clock taps | `node.plan` | works | hover core tooltip, click core opens core with `&from=`; observed on `s81.t.col_h10_r0_p4__t1` (design-typeplan-cores.png, design-core-from-type-click.png) |
| Core page right panel: status, metrics, Routed layout facts, "Used by N type(s)" list | core facts | node + `users` | works | |
| Core Plan view | outline of the core inside type | `node.plan` | **broken** | see 1.5 |
| Routed layout view: layout viewer in `#geo`, controls in `#geonav` (left) and `#geoside` (right) | exact routed geometry of a type/core pack | `layout.js` (LayoutViewer), `/layout_store/*`, `/api/layout/<id>/search`, `lv_worker.js` | works | features in section 3.2 (identical viewer); here `E:null`, no element JSON, timing paths from the store timing object |
| Macro card (type layout, click a macro outline) | jump from a hard-core macro to the core page | `macroPick()`, overlay `macros` | not verified (overlay was toggled, macro click not exercised) | |
| `#q=<name>` resolver | arrive from other pages by old/element/core names | `/api/design/resolve?q=` | works | single hit redirects to `#n=`; multiple hits list; none says "not a type or core of any current die plan"; observed `#q=iqf` -> `s81.t.iqf__t1`, `#q=dsfd_qbank_N` -> core |
| Error panel | show failed load | `err()` writes into the right panel | works | `#n=nodie` and `#n=s81.t.nonexistent` give "Error: 404 /api/design/die/nodie" plain text in right column, canvas left stale/empty |
| Phone layout (<=860 px) | stack | CSS | partial | order centre (62 vh), details, then nav; page scrolls (height 3678 to 4113 px for a layout page); no horizontal scroll (390 = 390); nav with 205-type list is last, 2157 px down |

### 1.2 Click log (design die page, probe run 1; layout page controls in 3.2)
Dies list links, Dataflow, Theme, 7 status checkboxes, 6 overlay checkboxes, type filter, type rows: every control produced an effect except: clicking the already-active die ("S81"/"S81 data die") = nothing (expected), the 7+6 checkboxes change only the canvas (no DOM/URL/network, expected, visual effect not diff-checked). The `Dataflow` click navigated away to `/explorer/dataflow/#design=ds_rom&die=plan_s81` (works as a link).

### 1.3 Datasets loaded (die page, cold)
`/api/design/index` 1.1 KB, `/api/design/die/s81` 511 KB transfer (gzip), `design.js` 30 KB, `layout.js` 68 KB, `lv_decode.js` 8 KB: 6 requests, 0 errors, console clean.

### 1.4 What works well and should survive the redesign
Die plan to scale with status colouring; hash deep links; `#q=` resolver; breadcrumbs with `from`; status counts per die; routed layout for type/core in the same shell.

### 1.5 Bugs and UX problems observed (tool 1)
1. **Core "Plan" view crashes.** `#n=s81.c.dsfd_qbank_N&v=plan` and the Plan button on any core: `PAGEERROR n.plan.ft_slots is not iterable` (design.js `drawType`, a core's plan has no `ft_slots`). Canvas shows nothing, hint bar empty (shots-old/design-core-plan-crash.png, design-core-desk-planview.png). The error repeats on every redraw (Theme click: second identical error). The Plan button for a core is not disabled.
2. **Layout canvas is boxed, no full screen** (complaint a). Canvas 900 x 954 of 1600 x 1000; details column 400 px and nav column 300 px permanently take 44% of the width. Keys `[` `]` and column drag do nothing (complaint b).
3. **URL state collision**: `v=plan|layout` is the design view, but the layout viewer overwrites `v` with `x,y,zoom` on every pan (`#n=s81.t.iqf__t1&tab=geo&v=721440,613440,-10.77&h=Filler%20%2F%20tap&o=macros`). Pressing Plan then sets `v=plan` and the viewport/layer state is lost; Routed layout (`v=layout`) comes back at default zoom. `tab=geo` is a leftover from the element page.
4. **Hash polluted with defaults**: `h=Filler / tap` and `o=macros` appear in every layout URL even though they are defaults.
5. **Routed-layout facts block blank for unsigned-but-routed packs**: `source`, `stage`, `DB` empty (`layoutFacts` reads `l.source/l.stage/l.db`, which the index does not carry for `store`-only layouts).
6. **Layout viewer panels unstyled in design page**: `.rampl`, `.tw`, `table.t`, `.ctl`, `.u` not defined (design-type-desk.png).
7. **"Die-level route has not run yet: this page shows the plan placement, not a routed die"** is stale: the die map (diemap.html, 8791) draws exactly that, but nothing links to it.
8. **Tile fetch warnings**: 337 console warnings `layout worker {op: error, key: 17_23, what: tile, error: Failed to fetch}` after rapid layer/preset changes (lout-design-type.txt). Likely partly host load (load average 220), but the viewer neither retries visibly nor tells the user. Not verified on an idle host.
9. **Renderer crash risk**: first run, clicking preset `Power grid` then `M6+ die contract` on the 248 M-shape type `s81.t.iqf__t1` ended with `Page.evaluate: Target crashed` (software GL, may not reproduce on a GPU; the second run survived both presets). Not verified on real GPU.
10. Timing paths panel, `history` select and timing row click are absent for packs without STA (`s.timing.sta:false`): Panel says "No timing paths were exported for this element (timing not re-run)". Acceptable but wordy.
11. Type list (205 rows) rendered in full on every filter keystroke (`renderNav()` rebuilds the nav incl. the whole list and re-focuses the input); the filter box loses the IME/selection state on re-render (worked in test).
12. `Dataflow` button points at a non-existent record (`plan_<die>`), so the destination shows a month-old revision without saying so (see tool 4).
13. Error state leaves the stale canvas up; no "go to the die" link on the error panel.
14. Phone: nav list last (2157 px down); layout canvas 523 px tall; cannot hide panels.

Counts: feature rows 20, bugs 14.

---

## 2. Die route map (`explorer/design/diemap.html`, `diemap.js`, `diemap.css`, 367 lines; only on port 8791)
URL `http://127.0.0.1:8791/explorer/design/diemap.html#n=s81`. On 8766: 404. Datasets (cold, s81): deck.gl 1.59 MB, `/api/design/compose/s81` 197 KB (composition manifest: plan + 69 pinned pack ids + 398 instances), then per visible pack: header object (~145 KB) + raster levels (brotli), up to 74 requests at first paint, 87 after zooming to one type, 197 at close zoom; worker pool of 2 to 4 (`lv_worker.js`). First paint about 20 s (software GL, loaded host). No data date on the page except the plan name. Screens: diemap-desk.png, diemap-desk-hover.png, diemap-desk-zoom.png, diemap-desk-zoomed-signed.png, diemap-desk-zoomed-close.png, diemap-phone.png.

### 2.1 Features and controls
| feature | what it is for | data source | status | notes |
|---|---|---|---|---|
| Header line: die label, plan name, "30 of 35 signed placements have a routed pack . 69 unique packs (1.82 GB)" | provenance and coverage | `compose.summary` | works | |
| Status legend (signed/failed/building/waiting/not built) | colour key | `STATE_VAR` | works | static, not clickable; `queued` and `hard ip` missing from the legend |
| Go to partition / type box | find an instance by name | `M.insts` search, `change` event (Enter or blur) | works (flies to bbox and flashes it) | only the first match; no result list; the earlier run with `col_h10` navigated and issued 818 requests; screenshot after that timed out (30 s) because the page was busy |
| `Fit` button | fit the die | `zoomTo` | works (URL gets `v=`) | |
| "show unsigned as-routed packs" checkbox | draw newest as-routed pack of unsigned types | `M.showUnsigned`, hash `u=1` | partial | works but logs `deck: Multiple new layers with same id r312s81.c.ot_dsrom_su_hcpo...` and the page became so busy that a screenshot timed out after 30 s (first run). Not verified that this is not only host load |
| Routing layers list (M1..M9, V1..V9, Pad, Cells, Filler/tap) with checkboxes | layer visibility | `M.L`, `styleUniforms` | works (network re-fetch of tiles, 5 requests for one toggle) | no opacity slider, no solo, no presets, no shape-kind filter (those exist in the element/design viewer) |
| Map canvas (deck.gl OrthographicView) | die floorplan: plan rectangles coloured by status, density rasters far out, exact vector tiles when zoomed, hard cores outlined in place | compose manifest + store packs | works | wheel zoom (speed 0.012), drag pan, double-click zoom, keyboard (deck default); zoom range fit-1 .. 14; zoomed to 20.85 px/um the exact wires of one type were drawn (1 exact, 105,178 shapes est, 4 MB GPU) |
| Hover tooltip | instance, node id, state, orient, pack job and size | `hoverAt` | works | shows "no pack" for building types; shows pack-local coordinates |
| Coordinate read-out (bottom right) and info line (bottom left: zoom, px/um, masters in view, exact, shapes, GPU MB, packs open) | debug / scale | `renderInfo` | works | no scale bar, no minimap |
| Click an instance | select a node | `onSelect` rewrites `n=` in the hash | **partial/broken** | the hash changes to the node id (`#n=s81.t.ot_s81sl_leaf__t40__clf8bbdae1`) but nothing else happens: no panel, no navigation, no highlight; the next pan/zoom writes `n=s81` back (saveUrl uses `M.node`, not the click) |
| URL state `n`, `v`, `u` | shareable view | `saveUrl` | works | `n` of a type/core zooms to it and flashes (`node !== die`) |
| Phone layout | | CSS `@media (max-width:980px)` hides `.dm-side` | partial | layer panel and notes disappear on phones (computed display none), canvas fills; budget halves (`PH`) |
| Notes text | states scope | static | works | says "Die-top nets, PG and clock are not routed yet and are not drawn" |

### 2.2 Bugs and UX problems observed (tool 2)
1. **Not reachable**: no link from any page; absent on the main server 8766 (404 for html, js, and `/api/design/compose/s81`).
2. **No header, no navigation, no theme switch, no way back** to design/dataflow/token (page contains zero `<a>`); own copy of dark tokens.
3. **Selection does nothing** and is reset by the next pan (see table). `onSelect` hooks only rewrite the hash; no details panel, no type/core page link, no status facts. (`mountDieLayout` is given `onSelect` by diemap.html, designed to be replaced by a shell.)
4. **Side panel fixed 210 px, not hideable, hidden entirely under 980 px** (complaint b); canvas is full height but there is no fullscreen button (complaint a).
5. **Console warning "Multiple new layers with same id"** when unsigned packs are shown; page then very slow.
6. Legend incomplete (`queued`, `hard ip`), no per-state toggle, no count per state.
7. No search result list; no layer opacity/solo/presets; no PG/clock/route overlays (by design: "not routed yet").
8. 74 requests and 1.82 GB of pack data referenced; first paint takes 15 to 20 s under load; no progress indicator except the info line.

Counts: feature rows 13, bugs 8.

---

## 3. Element page and routed layout viewer (`explorer/element/index.html`, `elem.js` 1014 lines, `layout.js` 909, `shell.js` 163, `lv_worker.js`, `lv_decode.js`, deck.gl vendor)
Two things live here: (3.1) the legacy element page `/explorer/element/` (pairs/elements of the October element index: Layout, Placement, Timing, Clock arrival, Clock tree, Density, RTL, Facts, How it works), and (3.2) the layout viewer `layout.js`, reused by the design page. The legacy page is retired in favour of the design explorer ("elements are retired in favour of the die -> type -> core node index") but is still served and linked.

### 3.1 Legacy element page
Observed on 8766 at `/explorer/element/` and `?p=bf-hier-vs-halfphl`: loads `elem.js` 93 KB, `shell.js` 12 KB, `shell.css` 8 KB, `pages.json` 9.6 KB (page definitions + RTL prose), `lv_decode.js`; then `data/bf_col600.json` and `data/bf_halfphl.json` -> 404; `/api/explorer/elem_tput?blocks=...` -> 404; `/fv_flow.js` -> 404 with MIME error. Screens: element-root-desk.png, element-root-phone.png.
| feature | what it is for | data source | status | notes |
|---|---|---|---|---|
| Top tab bar (Layout, Placement, Timing, Clock arrival, Clock tree, Density, RTL, Facts, How it works) | views of one element | `TABS` in elem.js, `data/<id>.json`, `.cells.bin`, `.clk.bin`, `.rtl.json`, `/api/explorer/elem_shell` | **broken** here | only `Facts` is enabled; the other 8 tabs are not clickable (click timed out). Panes show "Could not load bf_halfphl: Error: 404 data/bf_halfphl.json" |
| `?` help button next to tabs | per-tab description popover | `TABS[i][2]` | works | |
| Left column toggle (`lbtn`, key `[`) and right column toggle (`rbtn`, key `]`), close `x` buttons, scrim on narrow | hide/show nav and details | `toggleCol`, localStorage `otx.elem.nol/nor` | works | only page where panels can be hidden; <=900 px they become drawers; Escape closes |
| Theme button | light/dark | localStorage `otx.elem.theme` | works | |
| "Jump to element..." search (`#esq`) | type-ahead over element summaries | `/api/explorer/elem_summaries` | **broken** (404 on 8766, endpoint belongs to the legacy server) | arrow keys / Enter / Escape implemented |
| Hierarchy crumbs ("Chip Explorer" > die > region > element) | navigation | `elem_shell` | partial | "Chip Explorer" link is `/explorer` which on this server is the design explorer; die/region links use `#die=`/`#element=` which the design page ignores |
| Pair view: two panes bf_halfphl vs bf_col600 with `+` `-` fit buttons per pane | side-by-side layout compare | `pages.json` | broken (no data); zoom buttons have no visible effect on the error panes | |
| Details column: title, summary text, source/exporter text | provenance | `pages.json` | works | |
| Flow/progress box (`FVFlow.mount`) | closure progress for the element | `/fv_flow.js` | broken (404, script refused) | |
| Legacy banner | redirects to current design node(s) | `/api/design/resolve?q=` | works only when `e` is given | not shown on the root page |
| Layout tab | the layout viewer (3.2) for this element | `/api/layout/<el>/status` | broken for legacy names: `{"state":"nodb","reason":"no routed DB recorded for this element"}` | |
| Phone layout | | CSS | partial | no horizontal overflow (390 = 390) |

Bugs (tool 3.1): 8 of 9 tabs not clickable (click timed out) and 2 data files + the throughput API + fv_flow.js fail (4 failed requests); `fv_flow.js` MIME error (`Refused to execute script from 'http://127.0.0.1:8766/fv_flow.js' because its MIME type ('text/plain') is not executable`); search endpoint 404; element names are October names that the design index does not know; the page still has the retired "Chip Explorer" crumb. Console: 5 errors on every load. Counts: feature rows 12, bugs 7. Elements pages with real data: not verified (needs the legacy server, owner machine).

### 3.2 Layout viewer (layout.js), observed on design pages `#n=s81.t.iqf__t1` and `#n=s81.c.dsfd_qbank_N`
Screens: design-type-desk.png, design-type-desk-ov-clock.png, design-type-desk-ov-paths.png, design-type-desk-afternetsearch.png, design-type-desk-preset-power.png, design-core-desk.png, design-core-desk-ov-clock.png.
| feature | what it is for | data source | status | notes |
|---|---|---|---|---|
| deck.gl canvas (`lv-canvas`) | lossless routed layout: every wire, via, pin, cell on M1..M9, V0..V9, Pad, at 1 nm | brotli tile objects via `lv_worker.js`, header, name tables | works | LOD: density raster (L1/L2) far out, vector tiles near; sample type has 10.7 M shapes + 6.0 M instances, 248 M expanded shapes |
| `Search net / instance...` box + result list (40 max) | find by name | `/api/layout/<id>/search?q=&k=all` (0.2 to 0.5 s) | works | click result flies to it and highlights the net (`net=81` in hash); `clk` gave 40 results; core `clk` 26 |
| `Fit` (key F), `Ruler` (key R, two clicks), `Clear` (Esc) | view/measure | `layout.js` toolbar | works | Ruler/Clear only change DOM state |
| Minimap (180 x 120) | overview + viewport jump | rasters | works (click moves view) | fixed size and position |
| Scale bar, coordinate read-out, info chip ("density raster L2 . 26,283,448 shapes in view . GPU 0 MB") | feedback | | works | |
| Hover tooltip | lint finding / clock sink / path / path pin / macro under cursor | overlay layers | works only over overlay objects; plain hover shows no tip (tip null in test) | net highlight on click of a wire |
| Layers panel (22 rows): visibility checkbox, colour swatch with stipple, opacity range, `solo` button; presets `All`, `Signals only`, `Power grid`, `M6+ die contract` | layer control | `V.L`, URL `h=` | works (each change refetches 130 to 580 tiles) | Power grid / M6+ presets: renderer crash once (see 1.5) |
| Shape kinds (14 checkboxes) in a `<details>` | filter wire/via/pin/obs/... | `KINDS`, URL `k=` | works | |
| Palette select (`Classic layout`, `Colour-blind safe`) | palette | `S.PAL` | works | not stored in URL |
| Overlays: contract findings, worst timing paths, clock tree arrival-coloured, congestion heatmap, macro outlines, module outlines (6 checkboxes) | analysis overlays | store lint, timing object, congestion grid, `mods` (needs placement data) | works (checkbox toggles); paths/clock/module overlays depend on exported data | URL `o=`; for the sample type paths: none (`sta:false`), clock topology 38,168 sinks; congestion layer select + table shown |
| Contract findings list (`FAIL 1. Covered edge pins ... 1151 shapes`) and detail card | child_lint results with geometry | store `lint` | works | click zooms to the finding (URL `f=`) |
| Timing paths table (slack, endpoint) | worst setup/hold paths | timing object | works when exported; absent for samples | path rows selectable |
| Clock tree section (ramp, cell/sink counts) | arrival colouring | timing object | works; label overlap bug (0.4) | |
| Congestion section (layer select, ramp, per-layer p50/p99/max/bins>100%) | routing demand | store | partial (unstyled table) | |
| Closure block (job, commit, setup/hold, closed, record, export verify, `history` select) | provenance | manifest | works when manifest has closure data | `history` select only if >1 closure |
| Data block (source, die size, DBU, tiles, DB truth, cut time, first paint ms) | provenance | header | works | |
| Net card (`zoom to net`, `clear`) | selected net info | `names()` | works | |
| URL state (see 0.3) | share view | `saveUrl` | partial (collides with design `v`) | |
| Fallback buttons (`Open the placement view`, `Retry`) | when no pack / failed | `onFallback` | works in design (switches to Plan); on element page would open Placement | |

Bugs and UX problems (3.2): 1. no fullscreen, no panel hide or resize in the design embedding (complaint a, b); 2. 337 `Failed to fetch` tile warnings under load, no user-visible retry; 3. renderer crash on Power grid preset once; 4. URL `v` collision with design; 5. panels unstyled outside the element shell (0.4); 6. no tooltip for plain geometry (only overlay objects), so a user cannot read a net name without clicking; 7. layer panel has 22 rows with 3 controls each in a 300 px column (22 x 3 inputs = 66 + 14 kinds + 6 overlays + 4 presets + 3 tools in the DOM: 103 controls); 8. no way to save a view or screenshot; 9. `Ruler` and `Clear` give no visible state in the toolbar (aria-pressed only). Counts: feature rows 19, bugs 9.

---

## 4. Dataflow explorer (`explorer/dataflow/`: index.html, dataflow.js 499 lines, floor.js 423, model.js 274, table.js, dag.js, dataflow.css; data/*.links.json.gz)
URL `/explorer/dataflow/#design=ds_rom[&die=<record>][&t=<cycles>]`. Cold load: `dataflow.js` 39 KB, `floor.js` 26 KB, `model.js` 15 KB, `core.js` 15 KB, css 11 KB, `dag.js` 8 KB, `table.js` 6 KB, `token/data/ds_rom.json` 2.05 MB, `dataflow/data/index.json` 44 KB (22 records), `s81_gen18c.links.json.gz` 2.89 MB, `coverage/gaps.js` 3 KB: 12 requests, 0 errors, load plus render about 10 s. Screens: dataflow-desk.png, dataflow-select.png, dataflow-fullpage.png, dataflow-phone.png.
| feature | what it is for | data source | status | notes |
|---|---|---|---|---|
| Header: design buttons (Qwen ROM, DeepSeek ROM (S81), HBM die Qwen3-8B, HBM die DeepSeek) | choose token design | `DESIGNS`, `token/data/<design>.json` | works | hash `design=`; clicking active one = nothing (expected) |
| Header links `Token Explorer`, `Chip Explorer` | cross-nav | static | partial | Chip Explorer = `/explorer` (design page here) |
| Die record `<select>` + "Compare" cards (10 candidates) | choose die revision / floorplan candidate and compare metrics | `data/index.json` | works | hash `die=`; cards show sum width-length, bit-um, relay stages, worst cut; select change loads `<id>.links.json.gz` (observed `gfp_s81_C1_B_compact2x2_codex`) |
| View toggle `Replay token` / `All links` | replay current schedule window vs whole link map | `S.mode` | works | |
| `Fit` button, key `0` | fit the die | floor.js | works (no URL/DOM effect, canvas only) | |
| Toggles: cut congestion, Manhattan, trail, bypass only | link-map overlays/filters | model.js `cutMap` | works | congestion ratio limit 0.60; legend explains |
| Selects: min width (all, 8, 64, 256, 1024 bit), min length (auto, all, 100 um, reach, 2 mm) | filter links | `visibleLinks()` | works | |
| Width scale slider | stroke width | | works | |
| Floor canvas | link map over the floorplan: green within reach, amber relayed, red hop > reach, dashed bypass, density fill for local links, bundled strokes | links record | works | wheel zoom, drag, double-click zoom, keys `+ - 0` and arrows, hover tip, click selects link/block; "12,506 links in view . 10,952 local as density" |
| Legend + coverage text | encoding and mapping stats ("99.1 % of operator cycles land on blocks of this die") | | works | text still says "token mapping (October instance globs)" |
| Window card + "Top active links by bit.um" buttons | current window facts and top links | | works | each link button selects it |
| Right tabs `Stage flow` (DAG), `Worst links` (table), `Source` | detail views | `dag.js`, `table.js`, provenance | works | table rows keyboard accessible |
| Timeline strip (canvas, stage labels) + transport: previous stage, step back, play/pause, step forward, next stage, step size select (1/4/16 windows), replay length select (6..120 s), slider, time read-out | replay token windows | `Clock` from token/core.js | works | strip click/drag seeks; keys left/right/PageUp/PageDown; `t=` hash is read once, not written |
| Block link in selection card to `/explorer/design/#n=` | go to design node | `loadDesign()` only when the record id starts with `plan_` | **never active** | no `plan_*` record exists (0 files); default record `s81_gen18c` is not a `plan_` record, so there are no links to design pages |
| Phone layout (<=980 px) | stack | CSS | partial | no horizontal overflow; panes stack, page scrolls |

### 4.x Bugs and UX problems observed (tool 4)
1. **Stale data, not dated**: all 22 records generated 2026-10-15/16; current plans are 2026-11-12 to 11-14; page shows no date, and links from the design page (`Dataflow`, `die=plan_<die>`) pass an id that does not exist, so `rows.find(...) || pickRecord(...)` silently falls back to the canonical October record.
2. **No link from the dataflow blocks to the design node pages** for the default records (see table) although the code was written for it.
3. Fixed dark theme, no Theme button, hard-coded colours; own header.
4. Link-map and replay panes fixed layout (left 300 px, right ~460 px): cannot hide or resize (complaint b); floor canvas cannot go full screen (complaint a).
5. `Chip Explorer` link target wrong on this server; no link to coverage or diemap.
6. Page uses `token/data/<design>.json` (2.05 MB) just for the clock/stage model: heavy for a link view.
7. Hash `t=` is read but never written; `die=` written only on select change.
8. Compare cards are `div`s with click handlers (not buttons): not reachable by keyboard (not verified), and one click test target "NOT PRESENT" after reload (dynamic).
Counts: feature rows 15, bugs 8.

---

## 5. Token explorer (`explorer/token/`: index.html, token.js 563 lines, core.js 263, flow.js 309, gantt.js 127, data/*.json; embeds the dataflow floor panel)
URL `/explorer/token/#design=ds_rom[&mode=mtp][&group=S029]`. Cold load (ds_rom): `token.js` 47 KB, `flow.js`, `gantt.js`, `core.js`, dataflow modules (floorplan panel), `token/data/ds_rom.json` 2.05 MB, `dataflow/data/s81_gen18c.links.json.gz` 2.9 MB, `/api/plan_now` 722 KB, `/api/coverage/token?design=` 106 KB, `/api/design/token/<design>` 33 KB, and `/api/native/coverage?design=ds_rom` -> **404 every time**. 19 requests, DOM about 737 KB of HTML (ds_rom), 2.2 MB for DFlash. Screens: token-desk.png, token-stage1.png, token-group-S029.png, token-fullpage.png.
| feature | what it is for | data source | status | notes |
|---|---|---|---|---|
| Header links `Chip Explorer`, `Coverage` | cross-nav | static | partial | Chip Explorer wrong target here |
| "Current token-pass state" `<details>` banner | says analytic record vs token pass, lists release-tree TOK.* lines and newest token_pass records | `/api/plan_now` | works | the only freshness statement among the old tools |
| Design tabs (Qwen ROM, DeepSeek ROM (S81 array), HBM generic die Qwen3-8B, HBM generic die DeepSeek) | choose design | `DESIGNS`, `data/<design>.json` | works | |
| `AR` / `MTP` switch | autoregressive vs speculative verify step | `data/<design>_mtp.json` | works for ds_rom; MTP disabled with a reason when `mtpInfo.available` false | |
| Token stages tree (left, 60 stage rows, folders Token path > Input/Pipeline stages) | pick a stage | `data.groups`, hash `group=` | works | keyboard tree (arrows, Home/End); stage click -> hash `group=S001`, flow graph re-renders |
| Headline cards (graded composition %, tok/s composed, price of record, "Token pass on the release dies" block) | numbers with provenance | token record `headline`, `composition_1018`, `token_pass_1019` | works | dated 10-18/10-20 inside text |
| Flow graph by stage (SVG, 99 group nodes) | stage overview; click drills into one stage; hover tooltip | `flow.js` | works | node click -> `group=`; enter key |
| Play / replay control, replay length select, slider | replay token over the graph | `Clock` | works | `Back to whole token` after drill |
| Gap-class chips (`MH OD NC NE NP MO UE` toggles) and coverage summary | colour/filter operators by coverage gap | `/api/coverage/token` | works | each chip toggle refetches `/api/design/token/` + `/api/native/coverage` (404 console error) |
| Swimlane timeline (gantt) of the step | when each operator runs; click zoom, dblclick seek | `gantt.js` | works | not separately exercised beyond load |
| Detail/"critical path" tables (clickable rows) | operators with cycles/share | token.js | works | |
| `a.tp-el` element links -> design `#q=` | cross-nav | `elementHref` | works | one test click ended on `/explorer/dataflow/#design=ds_rom` (selector hit the Data-flow link), so the design hop is not verified |
| Panel "Data flow on the floorplan" | the dataflow floor view inline | `mountDataflow` | works | includes all dataflow controls (4.x) |
| `Native lifecycle` `<details>` audit (QUALIFIED/INCOMPLETE, per-operation rows, current die gaps) | RTL -> routed leaf -> die chain evidence | `/api/native/coverage?design=` | **broken here** (404) | empty or absent panel |
| `Timing provenance, accounting and source records` `<details>` | sources | record | works | |
| Phone layout | | CSS | partial: no horizontal overflow, page is very long |

### 5.x Bugs and UX problems observed (tool 5)
1. **`GET /api/native/coverage?design=ds_rom` returns 404 on every design/chip switch**, producing one console error (`Failed to load resource: the server responded with a status of 404 (Not Found)`) per click (this is a route of the full server.py, absent in design_dev_server). The Native lifecycle panel therefore has no data.
2. Heavy: 2 MB token record + 2.9 MB link record + 0.7 MB plan_now for one view; DOM 737 KB; MTP/DFlash up to 2.2 MB DOM.
3. Fixed dark theme, own header, no shared navigation; no link to design nodes except per-element `#q=` links; no link to the die map.
4. Data is the analytic October record, only the banner says so; headline cards carry dates in prose.
5. Page is one long scrolling column: no collapsible/resizable panels (complaint b); the embedded floorplan cannot go full screen (complaint a).
6. `AR` clicked while already AR: nothing (expected).
7. The tabs, AR/MTP and chips are `<button type=submit>` outside a form (harmless).
Counts: feature rows 16, bugs 7.

---

## 6. Coverage matrix (`explorer/coverage/`: index.html, coverage.js 310 lines, gaps.js, coverage.css)
URL `/explorer/coverage/`, hash filters. Cold load: `/api/coverage` 368 KB gz (377 KB raw JSON, 0.2 s), `coverage.js` 22 KB, css 8 KB, `fv_stale.js` 6 KB, `gaps.js` 3 KB: 6 requests, 0 errors. Polls `/api/coverage/version` every 20 s and the full matrix every 60 s. Screens: coverage-desk.png, coverage-phone.png.
| feature | what it is for | data source | status | notes |
|---|---|---|---|---|
| Header: `<- Fleet` (`/`), title, description, links `Chip Explorer`, `Token path` | nav | static | partial | `/` and `/explorer` land on the design page on this server |
| Status line "source origin/main:... (tree 8b704a0fd5) . matrix 8b704a0fd5... loaded 2026-11-14 09:38:47 . element status ... . 101 rows, 304 ledger nodes . refreshes on every ledger change" | freshness/provenance | `/api/coverage` | works | |
| Target cards T1..T4 (covered / with gap / no HW counts, gap-class chips MH OD NC NE NP MO UE, ledger node counts, critical-cycle share, token-path links AR / MTP / DFlash) | per-target summary; click toggles the target column in the matrix | `summary`, `TOKEN` map | works | click -> `t=T2,T3,T4`; token links navigate to `/explorer/token/#design=...` |
| Ownerless gaps table (20 nodes in 9 groups + 1 structural) | gaps with no owner | `ownerless` | works | |
| Owner streams chips (qwen-system 33 gaps ...) | filter by owner | `streams` | works | click -> `owner=`; "OWNERLESS" chip |
| Filters: target buttons, phase select, plane select, group select, owner select, gap-class chips, "only gaps" and "beyond" checkboxes, search "function, node, element" | filter the matrix | `F` object, hash | works | each writes the hash; select change -> DOM 310 KB to 20 KB |
| Legend row | colour/letter key (H D R E C P) | `COLS` | works | |
| Matrix (rows = functions, 4 target cells with H D R E C P letter strips and gap classes) | the coverage matrix | `rows` | works | 304 ledger nodes; cells are `<td>` with click + Enter handlers; click opens drawer, hash `cell=<fid>@<T>` |
| Cell drawer (right, `Close` x, Esc) | per-cell detail with element names, closure status, links to design `#q=`/`#n=` | `openCell` | works | drawer not resizable; closes on Esc |
| `fv_stale.js` indicator | staleness | | works (not exercised) | |
| Phone layout | | CSS | works (no horizontal overflow); matrix scrolls |

### 6.x Bugs and UX problems observed (tool 6)
1. Link targets `/` and `/explorer` are wrong on this server (land on design page); `Chip Explorer`/`Fleet` wording points at pages that do not exist here.
2. The status line mixes time zones (loaded 09:38:47 PT versus "element status 9:55:39 AM" in the future relative to load).
3. Cells are keyboard-accessible but not announced; matrix rows in test (first 45 controls) include dozens of identical-label cells ("NO HW...", "GAP...").
4. Element names in the drawer link to design `#q=` but unresolved names say "not a type or core of any current die plan" (design page).
5. No panel/drawer resize (complaint b); no link to the die map or dataflow records.
6. 368 KB JSON fully re-fetched every 60 s even if unchanged (version endpoint exists, but the 60 s poll is for element status).
Counts: feature rows 11, bugs 6.

---

## 7. Old chip explorer (`explorer.html` 245 lines, `explorer.js` 766, `explorer_story.js` 286; also `index.html` fleet page 1141 lines)
Served only by the owner's fleet-viz `server.py` (`/explorer`, `/explorer.js`, `/explorer_story.js`, `/api/explorer/*`). Not served on epyc8 (404 for `/explorer.html`, `/explorer.js`, `/api/explorer/meta`). **Inventory from code only; status "not verified" for every row.**
| feature | what it is for | data source (code) | status | notes |
|---|---|---|---|---|
| Header: `<- Fleet`, title, die segment buttons, search box "Search element, master, alias or instance", `Token path ->`, `Coverage ->`, SAFE VIEW badge | nav and search | `/api/explorer/meta`, `/api/explorer/elem_summaries` | not verified | search: Arrow keys, Enter selects, Shift/Ctrl+Enter opens element page |
| Hierarchy tree (left): die headers, groups, masters/elements, "unplaced" list | pick element/master | `/api/explorer/meta` | not verified | keyboard navigable (tabIndex, keydown) |
| Die map canvas: every instance placed from the die recipe, coloured by element closure status or by kind; zoom `+`/`-`/`Fit`, wheel, pinch, drag, double-click zoom-to-instance, hover/click | the main map | `/api/explorer/geom` (explorer_geom.py, `geom/<die>.json.gz` columns) | not verified | LIMIT 30000 instances drawn individually, overview bitmap otherwise |
| `Colour by: Status / Kind` buttons, `Buses` toggle, `Data flow ->` link, `Clear selection` | map options | | not verified | Data flow link maps die to design with `DF_DESIGN` (qwen_r21b, s81_layer_r3, hbm_r25gph: October ids) |
| Legend (clickable status keys closed, closed<margin, running, failing, revoked, superseded, placeholder, hard macro, relay) | focus a status | `ST_KEYS` | not verified | |
| Element card (right): what it is, where, status, closure history, masters table, instances table, story buttons, copy link | element facts | `/api/explorer/card` | not verified | `data-copy` builds `#element=` URL |
| Stories overlay (curated step-by-step diagrams, Naive/Trick toggle, Step/Play, filters by target and status) | explain elements | `/api/explorer/story`, `explorer_story.js` (`stDraw`, dg* diagrams) | not verified | |
| Keys: `+ - 0`, `O` opens element page, `Esc` clears/closes | | explorer.js | not verified | |
| URL: `#die=&master=&element=&story=`, `?safe=1` | | | not verified | |
| Fleet page (`index.html`): live host/job table, element table, nav `Chip Explorer ->`, `Coverage ->` | fleet overview | `/api/fleet`, `/api/elements`, `/api/stream` | not verified | the only page that links to coverage |
Bugs and UX problems (from code, unverified): October die set (`qwen_r21b`, `s81_layer_r3`, `hbm_r25gph`) vs the current five dies; its element names no longer exist in the design index; hard dependency on the fleet server (`/api/explorer/*`); its own status colours (`--st-*`). Counts: feature rows 10, bugs 4 (all from code, not verified).

---

## 8. Plan views: where the die plan and type plan are drawn
| where | what is drawn | technology | data | status |
|---|---|---|---|---|
| design.js `drawDie` | die plan of record to scale: partitions by sign-off colour, seams, clock root star + 2-level H-tree sketch, PG domains, hard cores in slots, partition names | 2D canvas, own camera | `die.plan` (partitions `[name,type,x,y,w,h,orient]`, seams, clock, pg_domains) | works |
| design.js `drawType` | type plan: outline, ft slots (grey), face buses (cyan/orange), stations, clock taps, hard cores coloured by status | 2D canvas | `node.plan` | works for types, **crashes for cores** |
| diemap.js | the same die plan as rectangles + density rasters + exact vector tiles of signed packs; hard core outlines in place | deck.gl, custom shader, workers | `/api/design/compose/<die>` + store packs | works (8791 only) |
| dataflow `floor.js` | floorplan with links (record's blocks, not the design index partitions) | 2D canvas | `links.json.gz` records (Oct 15) | works, stale |
| token page floorplan panel | same as dataflow | | same | works |
| old `explorer.js` map | recipe-placed instances | 2D canvas | `/api/explorer/geom` | not verified |
| `explorer_render.py` (CLI, headless) | `record` (any links record), `type`, `die` views to PNG/SVG + links TSV; `--delta` before/after; `--supply` route supply maps | matplotlib, same link model as dataflow (`dataflow_links.py`) | die plan json(.gz), `plan_dataflow.py` | not run here (advisory CLI for lanes; EXPLORER_RENDER.md) |
Observations: four independent implementations of "draw a die plan" (canvas x2, deck.gl, matplotlib) with different coordinate/orientation handling (design.js `placeChild` for MY/MX/R180 only; diemap `xfOf`), different status colours, different data (design index vs link records vs recipe geometry). Counts: feature rows 6, bugs 2 (duplication; stale link-record geometry).

---

## 9. Cross-tool summary

### 9.1 Counts (feature rows = rows in the section's feature table)
| tool | features | bugs/UX problems |
|---|---|---|
| 1 design explorer | 20 | 14 |
| 2 die map | 13 | 8 |
| 3.1 element page (legacy) | 12 | 7 |
| 3.2 layout viewer | 19 | 9 |
| 4 dataflow | 15 | 8 |
| 5 token | 16 | 7 |
| 6 coverage | 11 | 6 |
| 7 old chip explorer (code only) | 10 | 4 |
| 8 plan views | 6 | 2 |

### 9.2 API endpoints and static files in use (top-level keys)
| URL | used by | response top-level keys / shape | size, time |
|---|---|---|---|
| `GET /api/design/index` | design, token via others | `schema, generated, states, dies, sources` (dies: `id,label,target,counts,outline,partitions,types,hard_ip,plan,plan_date,release_header,exported`) | 3.6 KB raw (1.1 KB gz), 20 ms |
| `GET /api/design/die/<die>` | design, dataflow (plan_ records) | `die, states, generated, nodes` (die: `id,level,die,label,target,plan,children,counts,type_count,hard_ip`; nodes: id -> `id,level,die,name,parent,status,layout,vis,plan,children`) | 4.57 MB raw (511 KB gz), 0.38 s |
| `GET /api/design/node/<id>` | design | `node, die, children, users, placements, states, generated` | 2.4 KB (type) to 132 KB (die node) |
| `GET /api/design/resolve?q=a,b` | design `#q=`, element banner | `{name: [node ids]}` | 26 B |
| `GET /api/design/token/<design>` | token, dataflow | `design, record, record_tool, record_head, dies, classes, steps, coverage, unmapped, nodes, generated` | 33 KB |
| `GET /api/design/compose/<die>` (8791 only) | diemap | `schema, die, label, outline, dbu, plan, index_generated, made, packs, instances, summary` | 197 KB |
| `GET /api/layout/<id>/status` | layout viewer | `state, job, id, manifest, index` (or `{state:nodb, reason}`) | 201 B |
| `GET /api/layout/<id>/search?q=&k=` | layout viewer | `results` [`k,id,name,sig,bbox`] | 3.6 KB, 0.2 to 0.5 s |
| `GET /layout_store/elements/<id>/index.json` | layout viewer | `element, latest, history, updated, manifests` | small |
| `GET /layout_store/elements/<id>/<job>.json` | layout viewer, diemap | `schema, id, element, job, made, design, closure, db, source, die, dbu, counts, lint, verify, objects, timing` | 1.87 MB (sample) |
| `GET /layout_store/objects/<h2>/<hash>.br` | layout viewer, diemap | brotli blobs (header, tiles, rasters, timing) | 0.01 to 300 KB each |
| `GET /api/coverage` | coverage | `schema, generated, generator, targets, gap_classes, uncovered_classes, streams, ownerless, ownerless_structural, summary, rows, token_map_note, plan, token_paths, streams_live, source` | 368 KB, 0.2 s |
| `GET /api/coverage/version` | coverage poll | `v, err, source` | 107 B |
| `GET /api/coverage/token?design=` | token | `v, design, target, uncovered, gap_classes, nodes, rows` | 106 KB |
| `GET /api/plan_now` | token | `schema, generated, build_s, cats, repo, sources, dies, elements, token` | 722 KB (regenerated every 30 min, 10:00:21Z observed) |
| `GET /api/native/coverage?design=` | token | **404 on dev server** (full server only) | 9 B error body |
| `GET /explorer/token/data/<design>[_mtp].json` | token, dataflow | `schema, design, title, clock_hz, tool, repo_head, headline, mode, totals, classes, groups, group_edges, drill, critical_path, adder_items, nodes, edges, notes, geometry, mtp, inputs, composition_1018, token_pass_1019` | 2.05 MB (ds_rom) |
| `GET /explorer/dataflow/data/index.json` | dataflow, token | `schema, records` (record: `id,file,label,design,token_designs,revision,role,candidate,scope,coverage,inputs,generated,bytes`) | 44 KB, 22 records, all 2026-10-15/16 |
| `GET /explorer/dataflow/data/<id>.links.json.gz` | dataflow, token | `schema, id, label, design, token_designs, revision, role, scope, reach_um, reach_source, outline, relay_reach_um, stages_explicit, relay_reach_source, registers, direction, ...` | 2.89 MB (gen18c) |
| `GET /explorer/element/pages.json` | element | `schema, note, throughput_budget, pages, elements` | 9.6 KB |
| `GET /explorer/element/data/<id>.json` | element | **404** for `bf_col600`, `bf_halfphl` | |
| `GET /api/explorer/elem_summaries`, `/api/explorer/elem_shell`, `/api/explorer/meta`, `/api/explorer/elem_tput`, `/api/explorer/story`, `/api/explorer/card`, `/api/explorer/geom` | element page, old explorer | legacy fleet server; **404 here** | |
| `GET /fv_stale.js` (200), `/fv_flow.js` (404, MIME text/plain) | coverage / element | scripts | |
| Static: `/explorer/element/vendor/deck.gl-8.9.36.min.js` 1.59 MB, `layout.js`, `lv_worker.js`, `lv_decode.js`, `/explorer/<tool>/*.js,css` | all | | |

### 9.3 All URL hash / query parameters
`n`, `v`, `from`, `q`, `die` (design); `tab`, `h`, `k`, `o`, `net`, `f`, `j` (layout viewer inside design/element); `u` and `?unsigned=1`, `?phone=1` (diemap); `?e`, `?p`, `?safe=1`, `#tab=` (element); `design`, `die`, `t` (dataflow); `design`, `mode`, `group` (token); `t`, `phase`, `plane`, `group`, `owner`, `gap`, `only`, `beyond`, `q`, `cell` (coverage); `die`, `master`, `element`, `story`, `?safe=1` (old explorer); `?lvsolid=1` (layout viewer regression mode).

### 9.4 Fifteen most important bugs (one line each)
1. Core "Plan" view throws `n.plan.ft_slots is not iterable` and draws nothing (design.js drawType; Plan button not disabled for cores).
2. No layout canvas can go full screen; the layout is a fixed 900 px grid cell between two fixed side columns (owner complaint a).
3. Details/nav panels cannot be hidden or resized on design, diemap, dataflow, token, coverage; `[`/`]` only work on the legacy element page (complaint b).
4. The die route map (diemap.html) is linked from nowhere, absent on the main server (404) and has no header, no nav, no theme switch.
5. Die map click selects nothing: it only rewrites `n=` in the hash and the next pan writes `n=s81` back; no details panel.
6. `v` hash key is used for plan/layout by design.js and for `x,y,zoom` by the layout viewer; panning destroys view state and Plan/Layout toggling loses the viewport; `tab=geo` leaks into design URLs.
7. Dataflow data are 2026-10-15/16 (22 records, no dates shown) while plans are 11-12..14; design's "Dataflow" button passes non-existent `die=plan_<die>` and silently falls back to the October canonical record.
8. Dataflow block-to-design links never appear: `loadDesign()` needs a `plan_*` record and none exists.
9. Token page requests `/api/native/coverage?design=` on every design/chip/group change and gets 404 each time (console error), so the Native lifecycle panel has no data.
10. Legacy element page is dead on this server: 8 of 9 tabs disabled, `data/bf_*.json` 404, `/api/explorer/elem_summaries` 404 (search), `/fv_flow.js` 404 with MIME refusal; 5 console errors per load.
11. Every "Chip Explorer", "Fleet" and `/explorer` link (element, dataflow, token, coverage) lands on the design explorer here; links with `#die=...&element=` hashes are ignored by design.js.
12. Navigation is six unrelated top bars; no shared header, no way to reach coverage/token/diemap from design pages (complaint d).
13. Layout-viewer panels are unstyled inside the design page (`.rampl`, `.tw`, `table.t` missing): clock ramp label and congestion table render as run-together text; routed-layout facts block shows blank source/stage/DB for unsigned packs.
14. Layout viewer floods 337 `Failed to fetch` tile warnings after rapid layer changes and renderer crashed once on the Power-grid preset (software GL, host load 220: not verified on idle GPU host).
15. Status colours and design tokens are defined three or more times (design `--s-*`, old explorer `--st-*`, element shell `--s-closed...`), diemap/dataflow/token/coverage hard-code dark, only design/element have a light theme; four separate die-plan drawing implementations.

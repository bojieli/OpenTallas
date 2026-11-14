# OpenTallas Explorer: REQUIREMENTS (EXPLORER-FABLE-1, 2026-11-14)

Scope: one professional web tool for the 5-die ASAP7 chip (S81, HEAD, QC, KV, HBM) that replaces the chip
explorer, the design/element explorer, the die route map, the data-flow explorer, the token explorer and the
coverage matrix. The front end is rebuilt end-to-end from this list. The data engines are kept (DESIGN.md
section 1). The full per-control inventory of the old tools, with click-through results, is INVENTORY.md in the
same directory.

Priority: P0 = must work for the tool to replace the old pages; P1 = expected by a daily user; P2 = later.
M = milestone that delivers it (DESIGN.md section 10). Every P0/P1 line has a Playwright test.

## A. Owner complaints (all P0, the reason for the rebuild)

| id | complaint | requirement | acceptance |
|---|---|---|---|
| A1 | layout canvases cannot go full screen | every canvas view has focus mode (canvas fills the window) and browser full screen | `\` or the Focus button hides all chrome; `Shift+\` or the button enters full screen; `Esc` returns; the canvas is redrawn at the new size |
| A2 | detail panels cannot hide or change width | navigator and inspector are resizable, collapsible and remembered | drag the edge between 180-520 px (navigator) and 260-720 px (inspector); `[` and `]` or the chevrons hide/show; double-click resets; state survives reload |
| A3 | some buttons are broken | no dead control | every control with a test id is clicked by the suite and must change the DOM, URL or canvas, with no console error and no failed request |
| A4 | navigation is cluttered | one shell, one header, one view rail, one breadcrumb | no page reload between views, no second header, no page without a way to every other view; old URLs redirect |

## B. Shell, identity, freshness (M1)

| id | P | requirement | acceptance |
|---|---|---|---|
| B1 | P0 | one page with top bar, view rail (7 views), navigator, stage, inspector, status bar | all seven views reachable by rail click and keys 1-7 |
| B2 | P0 | die switcher for the five dies with a signed-off meter | switching die keeps the view; unknown die shows an error state, not a blank page |
| B3 | P0 | one selection `{die, node, inst, net, lane, tok}` on design-index node ids, kept across views | select `s81.t.iqf__t1` in any view, visit the other six, the breadcrumb and inspector still show it |
| B4 | P0 | deep links: `#/<view>/<node>?inst=&net=&...`; Back/Forward work; "copy link" button | reload of any copied link restores view, selection, camera and layer visibility |
| B5 | P0 | old URL schemes accepted (`#n= #q= #element= #design= #die= #t=`, old page paths) | each old form lands on the matching view and node |
| B6 | P0 | data freshness in every view: "data as of", plan sha, service sha; freshness chip with the dataset list | status bar always filled; stale or missing datasets turn the chip amber/red; token and data-flow records show their own date and die revision |
| B7 | P0 | global search over types, cores and partition instances, keyboard driven | `/` focuses; arrows and Enter select; result opens in the current view |
| B8 | P1 | navigator tree: die > status groups > types > cores; filter; "routed only" switch | filter narrows as typed; groups collapse; the selected node is visible |
| B9 | P1 | inspector "Details" for the selection in every view: state, metrics, routed-pack facts, placements, cores, used-by, plan contents, visual verdict, actions | the same content regardless of view; links navigate without reload |
| B10 | P1 | light and dark theme, one token file, no colour literal elsewhere | toggle repaints chrome and canvases; static test finds no hex colour outside tokens.css and the engine palettes |
| B11 | P1 | keyboard list (`?`), visible focus, titles on every icon button | present |
| B12 | P1 | loading, empty and error states for every view; one broken dataset never blanks the app | a 404/500 from one endpoint shows a message with the reason and a retry |
| B13 | P2 | narrow screens (under 900 px): panels become drawers | usable at 390 px width |

## C. Overview (M1)

| id | P | requirement | source |
|---|---|---|---|
| C1 | P0 | five die cards: floorplan thumbnail coloured by state, types and cores signed off, share of die area signed, plan sha and date, routed-pack counts, release-tree header line | `/api/v1/dies`, `/die/<die>` |
| C2 | P0 | chip totals (types, cores, packs, failed) with one state bar and legend | same |
| C3 | P1 | dataset freshness table | `/api/v1/meta` |

## D. Plan view (M1)

| id | P | requirement | old tool |
|---|---|---|---|
| D1 | P0 | die plan of record to scale: every partition as a rectangle coloured by sign-off state; pan, zoom, fit; hover tooltip (partition, type, state, size, position, orient) | design explorer die page, chip explorer |
| D2 | P0 | click a partition = select type + instance; double-click = open the element | design explorer |
| D3 | P0 | overlays, each switchable: seams (port windows between abutting partitions, width by bits), hard cores inside partitions, clock root and trunk sketch (labelled plan, not routed), power domains, partition names | design explorer overlays |
| D4 | P0 | state legend with counts; click a state to hide it | design explorer |
| D5 | P0 | type scope: outline, hard cores coloured by their own state, face buses in/out, feed-through slots with stations, internal station chains, clock taps; click a core = select it | design explorer type plan |
| D6 | P1 | colour by: sign-off state, routed pack available, visual verdict | new |
| D7 | P1 | all placements of the selected type ringed; cores: the types that use them ringed | new |
| D8 | P2 | landing cohorts, PG rails, port-window list per seam | design explorer (cohort hover) |

## E. Layout view: die-level routed map (M1)

| id | P | requirement | old tool |
|---|---|---|---|
| E1 | P0 | the die with the routed geometry of every signed type and of its hard cores in place, from the composition manifest; orient R0/MX/MY/R180 | EXPLORER-P1 diemap |
| E2 | P0 | level of detail: plan rectangles + level-0 rasters far out; finer rasters; exact vector wires inside the shape budget; no page change while zooming | P1, layout viewer |
| E3 | P0 | honest coverage: unsigned types are outlines; "Unsigned" switch draws their newest as-routed pack, labelled; a summary line says how many placements are drawn; die-top nets, PG and clock trunks are stated as not routed | P1 |
| E4 | P0 | layers panel: per-layer visibility, opacity, solo; presets (all, signals, power, M6 and up, cells); shape kinds; classic and colour-vision-safe palettes | layout viewer |
| E5 | P0 | hover: layer, kind, size, net name, cell instance and master; click a wire = highlight its net; click a partition = select it | layout viewer |
| E6 | P0 | minimap (click to move), scale bar, cursor coordinates, zoom read-out, LOD read-out | layout viewer |
| E7 | P1 | ruler (two clicks, dx/dy), clear | layout viewer |
| E8 | P1 | zoom to the selected placement; rings on every placement of the selected type or core | new |
| E9 | P1 | camera and hidden layers in the URL | layout viewer `#v= #h=` |
| E10 | P2 | seam check overlay (pins of both sides), die GRT guide heatmap (advisory), die-top pack when a die route exists | REVIEW-1 P2/P3 |

## F. Element view: one type or core in full (M2)

| id | P | requirement | old tool |
|---|---|---|---|
| F1 | P0 | routed layout of one design (single pack) with everything in E2, E4-E7 | element page layout tab, design explorer routed view |
| F2 | P0 | header: name, level, state, stage, attempt, reason; metric tiles (TT setup WNS, FF hold WNS, DRC, GRT overflow, LEC, cells) against the academic gates | design explorer facts |
| F3 | P0 | Plan / Routed switch; when no pack exists the view says why and shows the plan | design explorer |
| F4 | P0 | timing paths: worst setup and hold paths listed with slack, start, end; click = draw on the layout with pins; corner switch | layout viewer paths overlay |
| F5 | P0 | clock tree overlay coloured by arrival, sinks and buffers with tooltips | layout viewer clock overlay |
| F6 | P0 | net and instance search inside the pack; result highlights and zooms | layout viewer search |
| F7 | P1 | hard cores (macros) outlined; click a macro = open that core; core page lists the types that use it | design explorer macro card |
| F8 | P1 | congestion heatmap per layer; contract-lint findings list with locate | layout viewer overlays |
| F9 | P1 | closure history: pick an older pack of the same design | layout viewer `#j=` |
| F10 | P1 | pack facts: source DB, host, stage, verify verdict, shapes, bytes, cut time | design explorer |
| F11 | P2 | module outlines, share-safe mode | element page |

## G. Dataflow view (M3)

| id | P | requirement | old tool |
|---|---|---|---|
| G1 | P0 | link records per die revision: blocks to scale, links pin to pin, width by bits, colour by reach verdict (within reach, relayed, over reach, unplaced) | data-flow floor |
| G2 | P0 | record picker with revision, role (canonical / candidate), generated date; a banner when the record is not the plan of record | data-flow record select |
| G3 | P0 | filters: all links / token replay, minimum width, minimum length, bypass only, cut congestion, Manhattan | data-flow filters |
| G4 | P0 | worst-links table (bits x length), click = locate; link details in the inspector | data-flow table |
| G5 | P1 | token replay: schedule windows, play/step/speed, active links per window, stage DAG | data-flow replay, dag |
| G6 | P1 | compare revisions and floorplan candidates on the same metrics | data-flow compare cards |
| G7 | P1 | block = design node where the names resolve; click a block selects the node | new (resolve) |

## H. Token view (M3)

| id | P | requirement | old tool |
|---|---|---|---|
| H1 | P0 | token designs (Qwen ROM, DeepSeek ROM, HBM x2), AR / MTP; headline tok/s, cycles, provenance grades (measured current RTL, old RTL, modelled, priced) | token explorer banner |
| H2 | P0 | stage tree (whole token > path > stages > operators) with share per stage | token stage nav |
| H3 | P0 | flow graph by stage with the critical path; swimlane timeline per element class; shared replay clock | flow.js, gantt.js |
| H4 | P0 | "runs on": token class -> current types and cores with state and confidence grade; click = select the node | `/api/design/token` |
| H5 | P0 | record date, repo head and die revision shown; banner when the record is older than the plan of record | new (REVIEW-2 risk 1) |
| H6 | P1 | operator details: cycles, grade, source, hardware status | token detail panel |

## I. Closure view (M4)

| id | P | requirement | old tool |
|---|---|---|---|
| I1 | P0 | per die: one row per type and core with state, stage, attempt, TT setup WNS, FF hold WNS, DRC, GRT overflow, LEC, cells, pack, visual verdict; sort, filter, search; click = select | new (plan_now, design index) |
| I2 | P0 | state matrix: dies x states for types and cores, counts and area share | release tree counts |
| I3 | P0 | academic gates shown per row (DRC 0, setup >= -42 ps, hold >= 0) with pass/fail | owner profile 11-13 |
| I4 | P1 | failure groups: rows grouped by failure class and reason | plan_now categories |
| I5 | P1 | architecture coverage ledger (targets T1-T4, gap classes, owners) | coverage matrix |
| I6 | P2 | export the table as TSV | new |

## J. Service and quality (all milestones)

| id | P | requirement | acceptance |
|---|---|---|---|
| J1 | P0 | `/api/v1` contract (DESIGN.md section 7); read-only; thin adapter over the engines | contract tests on every endpoint |
| J2 | P0 | the live service on :8766 and the owner's :8765 are untouched until the switch | new service on :8770 only |
| J3 | P0 | Playwright suite on every view and every button; screenshots per milestone | `pytest tools/explorer/tests` green |
| J4 | P0 | first paint under 2 s on the tunnel; die layout far view under 5 s; no view fetches more than it shows | measured in the suite |
| J5 | P1 | `/health` per dataset | 200 only with the required datasets |
| J6 | P1 | no generated data committed; no in-place patch of served code | review |

## K. Known defects of the old tools that the rebuild removes

From the two reviews and the click-through (details and evidence in INVENTORY.md):

1. No full screen and fixed-width side panels on the layout and design pages (A1, A2).
2. Six URL schemes and four die-name vocabularies; a link from one tool rarely opens the same thing in another.
3. Design explorer has no link to the other tools; each page has its own header and palette (268 colour literals).
4. Token and data-flow pages show October die revisions without saying so next to the picture.
5. Token "runs on" links point at element names that no current plan has.
6. The die route map is a separate page with its own top bar and side panel, not reachable from the design page.
7. Search exists only inside one loaded pack; no search for a type, core or partition across dies.
8. No data-as-of on the design, element and die-map pages.
9. Two served forks and hand-patched copies (REVIEW-2); the service lost its state once in a cleanup.

## L. Out of scope for this rebuild

Fleet monitoring and the release page (stay on :8765), the landing page and recordings, editing of any data,
re-export of token and data-flow records against today's dies (REVIEW-2 phase U2, a data job; the new views show
the records' own dates until then).

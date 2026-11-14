# EXPLORER-REVIEW-2: rebuild the four explorers as one tool? (Fable survey, 2026-11-14)

Owner question: rebuild the chip explorer, element explorer, dataflow explorer and token explorer as one professional,
unified tool, all at once with Fable?

## Answer

Unify: yes. Rewrite from scratch: no.

The four tools are already one code tree with good engines. What makes them feel old is not the code quality of the
views. It is three other things, and a rewrite fixes only the third:

1. The data is a month old. The token and data-flow pages show October dies, not today's plans.
2. The deployment is two hand-copied forks on two ports, and parts of it are broken since the 11-13 cleanup.
3. There is no common shell: no shared header, navigation, identifiers or styling.

Recommended: one shell app, one identity model, one data API with freshness shown, one service deployed from git, and
the proven engines kept as modules. About 13-17 Sonnet lane-days plus about 1.5 Fable days (spec and two reviews).
A full rewrite would be about 25-35 lane-days, would put the verified layout viewer at risk, and would still need the
same data work before it showed anything current.

## What exists (measured 11-14)

Everything lives in `tools/fleet_viz/` on main: 181 commits, 10-08 to 11-12. Without tests and the landing page it is
about 11,200 lines of Python, 6,900 of JavaScript, 2,100 of HTML and 300 of CSS. Stack: Python standard-library HTTP
server, plain ES modules, no framework, no build step. deck.gl 8.9 is vendored for the layout viewer only.

| tool | URL | code | data it reads | data age |
|---|---|---|---|---|
| chip explorer | :8765 `/explorer` | `explorer.js` 766, `explorer.py` 568, `explorer_geom.py` 445 | die geometry cache from `plan_now` + `/api/elements` (9.5 MB) | live (30 min cron); page code is from 10-15 |
| element explorer | :8765 and :8760 `/explorer/element/` | `elem.js` 1014, `layout.js` 906, `lv_worker/lv_decode` 263, `elements.py` 1103 | element registry + layout packs | live registry; packs cut at sign-off |
| design explorer (EXPLORER-2) | :8760 `/explorer/design/` only | `design.js` 363, `design_index.py` 284, `design_service.py` 130, `layout_store.py` 605 | `design_index.json` (738 nodes: 5 dies, 490 types, 243 cores) + pack store (12 GB) | hourly since 11-14 (EXPLORER-P0) |
| data-flow explorer | `/explorer/dataflow/` | `dataflow.js` 499, `floor.js` 423, `model.js` 274, `dag.js`, `table.js`; `dataflow_links.py` 620 | 22 link records committed in the repo (28 MB) | all generated 10-15/10-16, October die revisions (`s81_gen18c`, `qwen_c17_wide27`, `hbm_v15_compact`) |
| token explorer | `/explorer/token/` | `token.js` 563, `flow.js` 309, `core.js` 263, `gantt.js` 127 | `opentallas.token_path.v1` records from `tools/token_path_export.py` | exported 10-20 at repo heads `d9c5afcfc`/`aaf45dd75`; exporter last changed 10-11; dies `s81_layer_r3`, `qwen_r21b`, `hbm_r25gph` |
| coverage matrix | `/explorer/coverage/` | `coverage.js` 310, `coverage.py` 172 | native coverage API | live |
| first chip explorer | not served | `site/chip_explorer/` 19 files, 10-05 to 10-09 | static inputs | dead, but the token page still takes two geometry files from it |

Findings that need an owner:

- Two forks of the same tree, neither a git checkout. Localhost :8765 runs an installed copy in
  `~/.local/share/fleet-viz/` whose explorer files date from 10-15, hand-patched since, with 50 `.bak-*` files. It has
  no design explorer (`/explorer/design/` and `/api/design/*` answer 404). epyc8 :8766 runs a copy of the
  `claude/explorer-2` branch that differs from origin/main in three files (`plan_now.py` was patched in place by P0).
- Data-flow explorer is broken on :8760. `/explorer/dataflow/data/index.json` answers 404 there: `explorer2.env` points
  `DATAFLOW_DATA` at `explorer-2-work/df/data`, which no longer exists (cleanup window 11-13). It still works on :8765.
- Token-to-design links are dead on :8760. `/api/design/token/<design>` answers "token design map not built yet". The
  map was lost with `state/` on 11-13 and `refresh.sh` does not rebuild it. On :8765 the token page links to October
  element names that no current plan has (the `token_design_map.py` header says the old join maps about 0 %).
- Six URL state schemes for the same things: `#n=` (node id), `#element=` (element name), `#design=` (token design),
  `#die=`, `#t=`, `#q=`. Die names differ per tool: `s81` (design index), `s81_layer_r3` (token), `s81_gen18c`
  (data flow), `ds_rom` (token design). `/api/design/resolve?q=` is the only bridge, and only for type and core names.
- Styling: 268 distinct hex colours, one `<style>` block per page, CSS strings inside `token.js`, three copies of the
  DOM helper. The design explorer page has no link to any other page; there is no common header.
- Reliability: the design explorer lost its state on 11-13 and was down until P0 restored it on 11-14. Its refresh timer
  now exists; nothing checks that the pages actually answer. `m5-reroute-compare.service` on localhost is in failed state.

What is good and must be kept:

- The layout pack pipeline (`lv_extract`, `lv_tile`, `lv_verify` IDENTICAL against OpenDB) and the deck.gl viewer.
- The token views. They are already mountable modules with a documented API (`mountTokenExplorer`, `mountFlow`,
  `mountGantt`, a shared replay `Clock`) and carry provenance grades per number.
- The data-flow view (`mountDataflow`) and its link model, which states its source and writes null for unknown fields.
- `design_index.py` node ids (`<die>.t.<type>`, `<die>.c.<core>`): the right canonical identity for everything.

## Recommended architecture

One shell, one API, one store, engines as modules.

- Stack: keep plain ES modules and the Python standard-library server. No React, no bundler. The pages are canvas and
  WebGL work where a framework adds little, the hosts have no node toolchain in the serve path, and Sonnet lanes can
  maintain it without a build.
- Shell (`explorer/app/`): one page at `http://127.0.0.1:8760/`. Header with die switcher, search, breadcrumb
  die > type > core, status chip, and a freshness badge. Tabs: Plan | Layout | Data flow | Token | Coverage. Each tab
  mounts an existing module through one interface, `mount(el, {selection, onSelect})`.
- Identity: the design-index node id is canonical. One selection object `{die, node, instance, net, lane, tokenGroup}`
  held by the shell and written to one URL scheme (`#die=s81&n=s81.t.iqf__t1&view=layout`). `/api/v1/resolve` grows
  to accept old element names, token classes, data-flow block names, lanes and nets. Old URLs redirect.
- Data API (`/api/v1/`): one manifest that lists every dataset with generated time, source commit and plan sha. Every
  view shows that badge, so stale data says it is stale. Data-flow and token records move out of the repo into the
  state directory, keyed by plan sha, built by the refresh timer.
- Design system: one `tokens.css` (colour, type, spacing, status colours) and one small component file (table, chip,
  panel, legend, tooltip). Views lose their private palettes as they are mounted.
- Service: one service on epyc8 beside the pack store, one tunnel port. Runs from a git checkout at a pinned sha, not
  a copy. State and store under one path that is in the cleanup keep set. A `/health` endpoint checks every dataset;
  a timer posts to COORD when it is red. Fleet monitoring and the release page stay on :8765 (different job,
  operational) and link in; `/explorer*` on :8765 redirects to the shell.

## Phases and effort

| phase | content | lane-days | who |
|---|---|---|---|
| U0 | Repair and single source: merge serve-code drift to main, serve from git, restore data-flow data and the token map on :8760, add both to `refresh.sh`, keep set, `/health` + alert timer | 1 | Sonnet, now |
| spec | Identity model, URL scheme, API manifest, module interface, design tokens (one document) | 0.5 Fable | Fable, after the 11-19 reset |
| U1 | Shell, router, identity module, tokens.css; mount the five views as tabs; redirects | 3-4 | Sonnet, Fable review |
| U2 | Current data: data-flow links per plan of record from plan geometry and die binds; token records re-exported against today's dies with bind lane latency; token-to-node map from bind manifests instead of name patterns | 5-7 | Sonnet + die-owner input |
| U3 | Cross-links: node -> its place on the die (P1 view) -> lanes through it -> token share; selection kept across tabs | 3 | Sonnet, Fable review |
| U4 | Retire `site/chip_explorer`, the :8765 explorer copies and the `.bak` files; screenshot regression set | 1-2 | Sonnet |
| total | | 13-17 Sonnet + about 1.5 Fable | |

U2 is the most valuable phase and the one a rewrite would not shorten. It also overlaps closure work: the lane
latency and token-at-die numbers it needs are the same ones the academic profile gates on.

## Who builds it

Fable architect plus Sonnet builders, not Fable building. Reasons: the weekly limit (reset 11-19) and closure lanes
come first; the work is mostly mounting, moving and regenerating, which Sonnet does well against a fixed spec;
Fable adds most at the spec (identity and API contract) and at two visual reviews (after U1 and U3). U0 needs no Fable
and can start today. At most two explorer lanes at once, so closure lanes are not starved.

## EXPLORER-P1: continue

P1 should continue now, not wait and not fold in. It extends the engine that is kept (`layout.js` multi-pack) and its
die composition manifest is exactly the data the unified Plan/Layout tab needs. Four cheap constraints so it drops
into the shell later:

1. Use canonical node ids and keep state in `#n=`; add no new URL scheme.
2. Export a mount function (`mountDieLayout(el, opts)`) rather than a page-bound global.
3. Take colours from variables, not new literals.
4. Land on main through a branch; no more in-place patches of serve-code.

## Risks

1. New shell over October data would look current and be wrong. Freshness badges come in U1, before any polish.
2. Token-to-node mapping is by name pattern with a confidence grade. Until U2 binds it to the manifests it must show
   that grade, not hide it.
3. Scope creep into a rewrite of working views. Rule: a view is restyled when mounted, rewritten only if it cannot mount.
4. Conflict between P1 and U1 in `explorer/element/`. U1 touches the shell and page files, P1 touches `layout.js`.
5. epyc8 is a build host and may be released. The store path and service must be movable (one env file, documented).
6. Cleanup: the store and state were hit once already. Keep set first (U0).
7. Localhost memory rule: the unified service stays on epyc8; localhost keeps only the tunnel.

## First milestone (M-U1, about 5 lane-days after U0)

One URL, `http://127.0.0.1:8760/`. Header with die switcher, search and tabs. Selecting `s81.t.iqf__t1` in any tab
keeps it selected in Plan, Layout, Data flow, Token and Coverage. Every tab shows "data as of <time>, plan <sha>".
Old explorer URLs redirect. The service runs from a named git sha and `/health` is green after a cleanup pass.
Review: Fable opens five nodes on three dies and checks each tab against the old page.

## What to stop or merge

- Stop: in-place patching of served copies; new standalone explorer pages; committing generated data to the repo.
- Merge: the `claude/explorer-2` serve-code drift into main (three files).
- Retire in U4: `site/chip_explorer`, the explorer pages under `~/.local/share/fleet-viz/`, the 50 `.bak-*` files.
- Not checked in this review: browser rendering of each page (HTTP status only), and whether the token exporter still
  runs against today's sources.

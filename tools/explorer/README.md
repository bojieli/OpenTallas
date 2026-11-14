# OpenTallas Explorer (`tools/explorer`)

One web tool for the five dies (S81, HEAD, QC, KV, HBM): Overview, Plan, Layout (die-level routed map), Element,
Dataflow, Token, Closure. New front end (EXPLORER-FABLE-1, 2026-11-14); the data engines stay in `tools/fleet_viz`
and `tools/layout_viewer` and are used as libraries. Requirements and design: `REQUIREMENTS.md`, `DESIGN.md`.

## Run

```
set -a; . <explorer2.env>; EXPLORER_STATE=<own cache dir>; set +a      # same env file as the old service
python3 -I tools/explorer/server.py --port 8770 --bind 127.0.0.1         # needs brotli (the service venv has it)
```

Environment: `FLEET_VIZ_STATE`, `DESIGN_INDEX`, `LV_STORE`, `TOKEN_DESIGN_MAP`, `FLEET_VIZ_REPO` (as `design_service.py`
and `layout_service.py` read them); optional `EXPLORER_STATE` (composition manifests, default `<state>/explorer_v1`),
`DATAFLOW_DATA`, `TOKEN_DATA`. The server is read-only: no pollers, no ssh, nothing is cut at view time.

## Layout

| path | what |
|---|---|
| `server.py` | static app + `/api/v1` (meta/freshness, dies, die, node, compose, closure, resolve, search, layout names, store, dataflow, token, coverage), `/health`, old page paths redirect |
| `web/css/tokens.css` | every colour (light + dark). No colour literal elsewhere except the routing-layer palettes of the engine |
| `web/js/core/` | `store.js` selection + URL (`#/<view>/<node>?inst=&net=&lane=&tok=&...`), `api.js`, `dom.js` |
| `web/js/shell/` | top bar, rail, navigator, inspector, status bar, panel resize/collapse, focus mode, search, freshness |
| `web/js/engine/layout-engine.js` | multi-pack deck.gl renderer (die scope and element scope), LOD, picking, minimap, ruler |
| `web/js/engine/plan-canvas.js` | 2-D floorplan canvas + die plan / type plan drawings |
| `web/js/views/` | the seven views |
| `tests/` | Playwright + API + static tests (`README.md` there) |

Kept engines loaded as-is: `fleet_viz/explorer/element/{lv_worker,lv_decode}.js`, `vendor/deck.gl`,
`fleet_viz/explorer/dataflow/model.js`, `fleet_viz/explorer/token/{core,flow,gantt}.js`, and the Python modules
`design_service`, `layout_service`, `layout_store`, `die_compose`, `coverage`.

## Keys

`/` search · `1`-`7` views · `[` `]` panels · `\` focus mode · `Shift+\` full screen · `F` fit · `R` ruler · `Esc`

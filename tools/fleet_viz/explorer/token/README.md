# /explorer/token: critical path of one token

Served by `server.py` at `http://127.0.0.1:8765/explorer/token/` (`index.html` is the entry page; html/js/css/json/svg/png/webp
are served with their types; a placeholder answers until `index.html` exists). `install.sh` copies this directory
whole (`rm -rf` + `cp -r`), so everything the views need lives here.

Owned by the token-path stream; the explorer-core stream owns `server.py`, `install.sh` and `/explorer`.

## Files

| file | role |
|---|---|
| `index.html` | entry page; state in the hash: `#design=qwen_rom|ds_rom|hbm_ds[&mode=mtp]&group=<group id>` |
| `token.js` | `mountTokenExplorer(el, opts)`: tabs, provenance banner, replay controls, the three views, share tables |
| `flow.js` | (a) flow graph: `mountFlow(el, data, {clock, group, onDrill, onSelect})` |
| `gantt.js` | (b) swimlane timeline: `mountGantt(el, data, {clock, range, onZoom, onSelect})` |
| `overlay.js` | (c) floorplan driver: `overlayEvents`, `activeAt`, `resolveInstances`, `normalizeGeometry`, `DieReplay` |
| `core.js` | shared: `prepare/P`, `Clock`, `critAt`, `detail`, `elementHref`, palette, formatting |
| `data/*.json` | written by `python3 tools/token_path_export.py --viz-dir tools/fleet_viz/explorer/token` (main) |

`data/<design>.json` is an `opentallas.token_path.v1` record (the same file as `results/arch/token_path_20261008/` on
main): `nodes[]` (id, label, group, cls, start, end, cycles, base_cycles, adders, src.grade/record/pointer/note,
critical, slack, share), `edges[]`, `critical_path[]` (node ids in order), `groups[]` (stages / layers), `classes[]`
(element class -> `elements` = element names for `/explorer#element=`, `instances` = instance-name globs on the die),
`totals` (cycles, tok/s, reproduction line, cycles by grade and by class), `headline`, `drill`, `notes`, `geometry`.
Grades: `measured`, `measured+vendor`, `apportioned` (measured total, split by trace), `priced`, `lever`, `modelled`.
`data/geo_<design>.json` are fallback die snapshots from `site/chip_explorer/inputs/geo.json`.

## Mounting the views elsewhere (e.g. inside /explorer)

```js
import { mountTokenExplorer } from '/explorer/token/token.js';
const api = await mountTokenExplorer(el, {
  base: '/explorer/token/data/',   // where <design>.json lives
  design: 'ds_rom', group: 'S029', // group = drill target (null = whole token)
  geometryUrl: (design) => [...], // URL or URL list; default /api/explorer/geom?die=<die>, then data/geo_<design>.json
  onState: ({design, group}) => {},
});
api.show('hbm_ds', 'L14'); api.clock.play(); api.clock.seek(cycles);
```

Design -> die map used by default (`DESIGNS` in `token.js`): `qwen_rom` -> `qwen_r21b`, `ds_rom` -> `s81_layer_r3`,
`hbm_ds` -> `hbm_r25` (ids of `explorer_dies.json`).

## Floorplan-overlay driver for the explorer die map

The die map does not need `DieReplay`; it can draw its own geometry and ask for the events:

```js
import { overlayEvents, activeAt } from '/explorer/token/overlay.js';
const ev = overlayEvents(record, geom, { group: 'S029' });  // geom = the /api/explorer/geom record as returned
// ev = {t0, t1, events: [{t0, t1, node, label, cls, color, critical, idx: [inst index], instances: [inst name]}],
//       links: [{t0, t1, src, dst, from: [x, y], to: [x, y], critical, bytes, link}]}   (cycles; DEF µm, y up)
const { events, links } = activeAt(ev, t);                 // what to light at token time t
```

`idx` indexes `geom.inst.name` directly (the columnar explorer export is accepted as is), so the die map can light its
own instances by index. Instances resolve from the class's name globs plus any instance whose master is one of the
class's elements.

## Links out

Every operator detail lists its elements as `/explorer#element=<name>` links. The die caption links
`/explorer#die=<die id>`. `/explorer` can link in with `/explorer/token/#design=<d>&group=<g>`.

## AR | MTP

`data/<design>.json` carries `mtp`: `{available, file, tok_s, tau}` (DS ROM, HBM) or `{available: false, reason}` (Qwen ROM:
AR only by the owner's decision). `data/<design>_mtp.json` is the same `token_path.v1` schema for ONE MTP verify step
(`mode: "mtp"`), plus `phases[]` (draft / verify / accept spans), `accounting` (tau, step and per-accepted-token cycles,
speedup over AR), `hw_summary`, and for the DS ROM `mtp_variants` (HALF_PHL and full-rate BF at phase level). Nodes and
groups carry `phase`; MTP-only operators carry `hw: {status: built|partial|none, note, evidence}` and `flag` when none.
The views draw `none` hatched with a NOT BUILT badge (the die replay lights nothing and hatches the die), `partial`
dashed. `mountTokenExplorer(el, {mode: 'mtp'})`, `api.show(design, group, mode)`.

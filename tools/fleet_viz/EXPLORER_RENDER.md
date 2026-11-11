# explorer_render.py: the Dataflow Explorer, headless

A CLI for lanes and subagents. It draws the explorer's views to PNG, SVG and a links TSV without a browser.
It is ADVISORY: you get a picture and a table, never a gate.

How it works. The links come from the same model the browser uses. `dataflow_links.py` (`Builder`) gives the
pin ends, register hops, stage counts, Manhattan length, bit-um and the flight lines that cross unrelated blocks.
Each run also writes an `opentallas.dataflow.links.v1` record (`<name>.links.json.gz` + `index.json`).
The browser explorer can load that record too.

The drawing uses the same encoding as the floor view (`explorer/dataflow/floor.js`, `model.js`):

| Mark | Meaning |
|---|---|
| green | within reach |
| amber | relayed through stations, or needs a relay |
| red | at least one hop is longer than the reach |
| grey | unplaced |
| line width | `min(5, 0.45 + 0.32 log2 bits)` |
| dashed | crosses an unrelated block |
| white squares | register stages / stations |
| `#N` | the N worst links: hop > reach first, then bits x hop. Same order as `worst_rank` in the TSV |

Run it on epyc4 under `nice -n 19`. It needs python3 with matplotlib (it adds the user site itself under `-I`).
A type or die takes about 5-30 s; `--supply` adds one or two route_supply runs.

## Die view
```
python3 -I tools/fleet_viz/explorer_render.py die --plan DIE_PLAN.json[.gz] --out DIR [--name N] [--top 20] [--highlight-type T ...]
```
- Partitions are drawn as type blocks.
- Every plan lane is one link, src -> dst. It runs through its ports' face windows and through the `ft_slots`
  `regs_um` of each partition it passes, placed with that partition's orient.
- Width = the port width. Stages = the ft regs passed. `cycles` = the lane's `fixed_cycles`.
- Ports without windows (QC, HEAD) use the middle of the shared edge.
- TSV columns: worst_rank, id, class, bits, driver, sinks, stages, length_um, max_hop_um, bit_mm, status, bypass,
  note, cycles, via (the ft partitions).

## Type (intra-type) view
```
python3 -I tools/fleet_viz/explorer_render.py type --plan PLAN --type T --repo REPO [--die DIE] [--ref-dirs DIR ...]
        [--delta D.json | --after-plan P2] [--supply [--release-cache RC]] [--per-port] --out DIR
```
- Hard cores are filled by module family. The triangle marks the R0 origin corner, so it shows the orient.
- `N12/S4/E../W..` = signal pins per face. Dots = pins. `#k` = pipeline rank: SCC levels over the directed core
  links, with feedback loops sharing one rank.
- Face windows: cyan = in, orange = out.
- `ft_slots` and `internal_stations` are drawn with their regs. The clock tap is the star; core taps are x.
- Core-core and core-face links come from core_conns. The plan's own sidecar includes PLAN-ROUTE-1's netlist fill.
  - Pins and partners are resolved by `route_supply.py` itself (`core_pins`, `load_conns`), so this view and the scorer agree.
  - Bits = pin bits of the bus.
  - Direction comes from LEF DIRECTION, else the bus dir, else the port-name suffix.
  - Links are bundled per core pair by default. `--per-port` keeps one link per port.
  - Core pairs that the plan routes through internal stations are drawn from the stations.
- `--delta` accepts four formats. Before and after are drawn side by side, and moved cores get a pink outline.
  - CLEANSLATE `{type: {inst: [x, y, orient]}}`.
  - The route_supply delta (`{"types"|"partition_types": ...}` or a list of `{type, inst, ...}` rows).
  - A `core_place.v1` report: its `plan_output` when that file exists, else `rows[].cores_after`.
- In the after view of a positions-only delta, station ends follow their cores but the regs stay where they are.
  The TSV note marks these as stale.
- `--supply` runs `route_supply.py --maps` (default `REPO/tools/die_plan/route_supply.py`) on the before plan and
  on the after plan. Each result gets its own panel: demand/supply max(H, V) on a 0..2 scale, with the verdict,
  worst region and flag regions.

## Record view
```
python3 -I tools/fleet_viz/explorer_render.py record --record X.links.json.gz --out DIR
```
This is the browser floor view of any links record, for example `explorer/dataflow/data/*.links.json.gz`.

Read the PNG yourself, then read the TSV top rows. They are the `#N` links in the picture.

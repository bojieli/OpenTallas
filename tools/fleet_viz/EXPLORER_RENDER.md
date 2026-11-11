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
| purple dotted | quasi-static: reset / strap / dead input (`static` column); never ranked, never red |
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
- Where a lane crosses from one partition to the next, the crossing is taken from, in order: the port's own
  `face`/`window_um` (`pin`); the src (else dst) type's bus window of that bus name, placed with the partition
  orient (`tbus`); the whole shared edge of the two abutting partitions (`edge`, a stand-in); the src outline (`box`).
  On a window or edge the crossing sits at the point that minimises the longer of its two hops: a best case.
- Ft slot stations follow the kit (gen_rtl + face_flops.tcl), in every schema form: k = `stations` (default 1)
  + `built_station_extra`; station 0 is the in-face flop AT the slot's in window (the crossing), stations 1..k-1 sit
  at `regs_um[1..k-1]` (regs_um carries k sites, [0] is ignored by the kit), else at the `bit_sites_um` stages
  (k-1 of them, centroids), else at L*j/k along the slot route (`spread`, e.g. HEAD hd_spn `stations: 6`).
  The out port is not registered (the next partition's station 0 is).
- Crossing order: port window (`pin`), then the ft slot's in/out window (`slot`, overlap of both sides when they
  abut), then the type bus window (`tbus`), then the shared edge (`edge`), then the outline (`box`).
- Internal stations: one chain per bus conn as kit_istations.bus_entries (capture groups merged to the deepest
  depth, bits-weighted centroid; bit_route / exact-site entries as written).
- The record keeps per chain point `hk` (crossing / station provenance) and `hg` (the crossing segment), per hop
  `hp` (partition) and `hs` (slot provenance).
- The title shows the plan file, its sha256 and the plan's own `die.label` separately (a label can be stale).
- TSV columns: worst_rank, id, class, bits, driver, sinks, stages, length_um, max_hop_um, bit_mm, status, bypass,
  note, cycles, via (the ft partitions).

## Hop audit (REAL or MODEL)
```
python3 -I tools/fleet_viz/explorer_render.py audit --record DIE.links.json.gz --top 30 --out DIR
```
For the N worst lanes, each hop over reach is REAL (between plan facts: port windows, type bus windows, regs_um,
bit sites, an even spread of a declared count, or a slot with no stations) or MODEL (it depends on a stand-in:
`edge`/`box` crossing, missing slot, chain break). An `edge` hop is still REAL when even the best point on that
shared edge leaves a hop over reach (`hop_lower_um`). Output: `<name>__hop_audit.tsv`, one row per over-reach hop
plus one LANE row (REAL / MODEL / MIXED / ok).

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
- core_conns lookup is the same as route_supply: exact type, then `__clXXXXXXXX` stripped, then the family
  before `__` (so `bk_sel__t2` finds `bk_sel`).
- Quasi-static links are flagged in the `static` column and drawn purple dotted, never ranked: `reset` (a reset
  port, false_path from arst_n in gen_phys), `strap` (id/count/parent straps, false_path in straps.py), `dead`
  (plan dead_inputs). Config ports such as `cfg_*`/`go`/`xs_*` are NOT flagged: no plan, RTL or SDC declares them
  multicycle or false-path, so the flow times them single-cycle and so does this view.
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

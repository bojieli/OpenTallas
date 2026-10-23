# tools/die_feedthrough — die feedthrough pushdown + top-down layer budget (FT-PLAN, owner 10-23)

Shared by the four release dies (S81, Qwen compute `qc`, Qwen KV `kv`, HBM `hbm`). Per-die defaults are in
`dies.py` (reach from REACH-M89, repeater spacing 450 um, relay families, ft layers M8/M9, ratio limit 0.6).

## 1. Dump (OpenROAD, read-only)

    tools/die_feedthrough/dump.sh DIE.odb OUTDIR [MEM_GB=80]      # docker openroad/orfs:asap7lock, openroad -python

`odb_dump.py` writes `die.json`, `blocks.tsv`, `masters.tsv`, `mpins.tsv.gz`, `bundles.tsv.gz`, `hifan.tsv` and
`stdcells.tsv` (format in its docstring). Connectivity collapses pass-through buffers (BUF/INV/HB), so a relay to
relay hop with die repeaters on it is one bundle. Runtime is about 1-2 min on a 1-4 GB die ODB, using under 10 GB.

## 2. Census

    python3 tools/die_feedthrough/census.py --die s81|kv|qc|hbm --dump DUMPDIR --out OUTDIR
            [--reach-um R] [--big-min-um2 A] [--merge-gap-um G] [--ft-layers M8,M9] [--no-png]

Outputs (schema `opentallas.die_feedthrough.census.v1`):
- `<die>_census.json`, with these keys:
  - `summary`
  - `blocks[]` (per big block or merged region): `faces{N,S,E,W: bits, tracks, ratio, peak_ratio}`, `ft_obs_cover`,
    `ft_blocked`, `stages_in`, `lanes`
  - `groups[]` (per lane group): `src`, `src_bus`, `dst`, `dst_bus`, `kind` (data, ctl or reset), `bits`, `chains`,
    `stages`, `ideal_stages`, `cur_um`, `straight_um`, `detour`, `route` (HV or VH), `src_pt`, `dst_pt`,
    `crosses[]` (block, um, face_in, face_out, stages_in) and `relays[]` (longest chain)
- `<die>_lanes.tsv`: one row per group, sorted by bits x length.
- `<die>_census.png`: on the left, the floorplan with the relays and the top-300 chains; on the right, the straight
  routes with each block coloured by bits/track.

Definitions:
- **Lane group**: the relay chains from one source block bus to one sink block bus. Bits are the minimum edge width
  along each path, summed over the distinct last hops. Reconvergent DAGs and taps are handled by a memoised walk.
- **Relay**: a master matching the die's `relay_re`. The data pairs are i->o, a->b, y->b, d->q*, or else a unique
  equal-width pair. ck, rs, ea, k*, fault and tie pins are side pins, not lane bits.
- **Big block**: a non-relay block of at least `big_min_um2` (0.1 mm2). With `merge_gap_um` set (KV: 30 um), arrays
  of small blocks are merged into `region:` obstacles.
- **Face capacity**: wires that cross a W or E face run on the horizontal ft layers, and wires that cross an N or S
  face on the vertical ones. The ratio is bits / tracks, with a limit of 0.6.
- **Ideal stages**: `ceil(straight / reach) - 1`, placed evenly at j * L / (n + 1). `stages_in` counts the stages
  that fall inside a block.

## 3. plan.py (lane routing, stage placement, per-block ft spec)

    python3 tools/die_feedthrough/plan.py --die D --census OUT/<die>_census.json.gz --dump DUMPDIR --out PLANDIR
            [--policy straight|row] [--ft-reg inout|single] [--ft-clock block|forwarded] [--kinds data,ctl]
            [--forbid-re REGEX] [--slot-um S] [--occupancy 0.6]

Outputs:
- `PLANDIR/<die>_plan.json`, schema `opentallas.die_feedthrough.plan.v1`, with these keys:
  - `summary`
  - `lanes[]`: per lane, `id`, `src`, `src_bus`, `dst`, `dst_bus`, `bits`, `pts` (the final rectilinear route after
    track assignment), `segments[]` (kind channel or block, `block`, `len_um`, `stages`, `reps`), `stages_old`,
    `stages_new` and `keep_channel`
  - `variants{}`
- `PLANDIR/<die>_schedule.tsv`: `src src_bus dst dst_bus bits stages_old stages_new` (input to the static schedule).
- `PLANDIR/ftspec/<block_inst>.json`: one per block that hosts feedthroughs (the pushdown input below).

### ft spec (schema `opentallas.die_feedthrough.ftspec.v1`), the stable pushdown interface
```
{ "schema": ..., "die": "s81", "block": "<inst>", "master": "<master>", "variant": "<master>__ft<8 hex>",
  "outline": [w_um, h_um],            # master frame; every coordinate below is MASTER frame (orientation undone)
  "orient": "R0",
  "layer_contract": {"signal_max": "M7", "ft_layers": ["M8", "M9"], "pg_max": "M7"},
  "clock": "block" | "forwarded",     # forwarded: each path also has a 1-bit clock port pair <name>_ck_i/_ck_o
  "ports": [ {"name": "ft3_i", "path": 3, "dir": "input",  "face": "W", "lo": 812.4, "hi": 857.6,
              "layer": "M8", "bits": 276},
             {"name": "ft3_o", "path": 3, "dir": "output", "face": "E", "lo": 812.4, "hi": 857.6,
              "layer": "M8", "bits": 276}, ... ],
  "paths": [ {"path": 3, "lane": "<lane id>", "in": "ft3_i", "out": "ft3_o", "bits": 276,
              "stages": 3,                       # registers inside the block from in pin to out pin (latency cycles)
              "len_um": 2410.0, "rep_sites": 5,  # buffers the block P&R inserts between registers (<= rep_um apart)
              "regs_um": [[20.0, 835.0], [1205.0, 835.0], [2390.0, 835.0]] } ] }   # register positions, master frame
```
The rules:
- Port offsets of abutting neighbours are equal in die coordinates. The tracks are assigned once, per lane leg, in
  the die frame.
- `inout` registers every ft path at its in pin and at its out pin (the pin-register rule), with more registers in
  between at most `reach` apart. `single` uses one register for a short crossing.
- Port width is `bits x pitch / occupancy`.

## Tests
    python3 -m pytest -q tools/die_feedthrough/

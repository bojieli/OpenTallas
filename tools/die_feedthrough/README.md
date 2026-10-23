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


## 4. pushdown.py (per-block wrapper, ft pins, layer contract, abstract check, die ECO)

    python3 tools/die_feedthrough/pushdown.py wrapper  SPEC.json --kit-top MOD (--kit-verilog F | --kit-ports P.json) --out DIR
            [--station-module ot_dvrly_st|ft_pipe_reg] [--hc 1] [--clock PORT] [--reset PORT] [--kit-param N=V]
    python3 tools/die_feedthrough/pushdown.py pins     SPEC.json --out DIR [--layers die.json] [--dbu 1000] [--pin-len-um 0.32]
    python3 tools/die_feedthrough/pushdown.py contract SPEC.json --out DIR [--margin-um 2] [--signal-min M2] [--adjust 0.5]
    python3 tools/die_feedthrough/pushdown.py check    SPEC.json --lef BLOCK.lef [--max-cover 0.05] [--allow-stripes 0.48:8.64]
    python3 tools/die_feedthrough/pushdown.py die      SPEC_DIR --plan PLAN.json --die-verilog die.v --out DIR

Outputs (named after `spec["variant"]`):
- `wrapper`: `<variant>.v`. The wrapper instantiates the UNMODIFIED kit top as `u_kit` and passes every port through.
  Per path k it adds a chain of `stages` station instances `ft<k>_s<j>`, either `ot_dvrly_st #(W, HC)` or the emitted
  `ft_pipe_reg` (same ports; posedge D-flops, no data reset). Clock `block` uses the kit clock; `forwarded` adds
  `ft<k>_ck_i`/`ft<k>_ck_o` and chains ck -> ck_o. `<variant>.ft.json` lists the register names and the repeater sites,
  which block P&R inserts (they are not RTL).
- `pins`: `<variant>.pins.tcl` writes one `place_pin` per bit on the spec layer and face. The bits are spread over
  [lo, hi] at an integer multiple of the track pitch and snapped to `offset + k*pitch` (ASAP7 M8/M9: 0.116 + k*0.080).
  Equal ranges give equal offsets, so in/out ports and abutting neighbours line up. A forwarded clock takes the middle
  slot. `<variant>.pins.json` holds the pins plus register placement hints, which also appear as a commented-out Tcl block.
- `contract`: `<variant>.fastroute.tcl` is the ORFS `FASTROUTE_TCL`, with `MIN_ROUTING_LAYER=M2` and
  `MAX_ROUTING_LAYER=M9`. OpenROAD 26Q3 has no per-net layer range, so the contract routes signals on M2-M9 and applies
  `set_global_routing_region_adjustment ... -adjustment 1.0` on M8/M9 over the outline minus the ft corridors.
  `<variant>.contract.json` holds signal_max, ft_layers, pg_max, ft_nets, obs_rule, corridors and fence.
  `<variant>.ft_audit.tcl` runs after global_route and lists non-ft nets with M8/M9 guides outside the corridors
  (`FT_AUDIT PASS|FAIL`). Known limit: GRT keeps capacity in the last gcell column/row at the outline's max edges, and
  regions past the die are refused (GRT-0067). The audit catches any leak there.
- `check`: `check_abstract(lef_text, spec)` returns FAIL for an ft-layer OBS over 5% of the outline (stripes up to the
  allowed width are excluded, up to 1.25x their nominal density), and for an ft pin bit that is missing, on the wrong
  layer, on the wrong face or outside [lo, hi]. Exit 1 on FAIL.
- `die` (best-effort skeleton): `die_eco.json` + `die_eco.tcl` cover every lane with block segments and
  keep_channel false. They delete the lane's relays (`lanes[].relays`) and their inter-relay nets, then connect
  src -> blk/ft_i ... blk/ft_o -> dst (and the forwarded clocks) with `delete_instance`, `delete_net`, `make_net` and
  `connect_pin`. die.v is only read. The JSON lists TODOs per lane: new channel relays are not inserted yet, only the
  census longest chain is removed (taps need review), and MX/MY blocks may mirror bit order.

## 5. checks.py (GRT probe harness; every probe writes DIR/run.sh + probe.tcl, --run executes it -> DIR/grt.json)

    python3 tools/die_feedthrough/checks.py extract-lef --odb DIE.odb --masters M1,M2 --out DIR [--run]
    python3 tools/die_feedthrough/checks.py abstract-probe SPEC.json --lef MASTER.lef --out DIR [--layers M8-M9] [--run]
    python3 tools/die_feedthrough/checks.py block-probe SPEC.json --odb BLOCK_PLACED.odb --out DIR [--signal M2-M9] [--run]
    python3 tools/die_feedthrough/checks.py die-probe --odb DIE.odb --out DIR [--plan PLAN.json --drop-pushed] [--eco die_eco.tcl] [--run]
    python3 tools/die_feedthrough/checks.py parse GRT.log

- `extract-lef`: runs `odb.write_lef` on the die-case library that holds each master. Use it when the abstract only
  exists inside the die ODB.
- `abstract-probe`: ft traffic over the exported abstract. The DEF has die = outline, the macro FIXED, and one
  in -> out 2-pin net per ft bit on the spec pins. GRT runs on the ft layers only. Overflow > 0 means the abstract's
  M8/M9 OBS or the face width cannot carry the ft.
- `block-probe`: the block's placed ODB plus the ft pins and nets, with GRT on the block's signal layers.
- `die-probe`: a read-only die GRT. `--drop-pushed` deletes the channel relays of the pushed lanes, which gives an
  UPPER BOUND on the channel relief. `--eco` sources pushdown.py's die ECO instead.
- Docker uses `--memory = --memory-swap`. This is a short diagnostic (owner 10-23); keep >= 64 GB physical headroom.

## Tests
    python3 -m pytest -q tools/die_feedthrough/


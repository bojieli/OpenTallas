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

## 3. plan.py, pushdown, checks
Not built yet. The interfaces will be added here when those tools land.

## Tests
    python3 -m pytest -q tools/die_feedthrough/

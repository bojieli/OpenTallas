# Die clock delivery method (DIE-CLOCK, 2026-10-16)

This is the shared method for the physical die-level clock on all three dies (S81, Qwen compute / KV-system, HBM).
"Die clock" means the trees from the PLL / clock-generator outputs, and from the region roots such as the S81
column FIFO `co`, to every tile clock entry pin. The tile-internal trees belong to the tiles and are not covered here.
The tools are `tools/die_clock/` and `tools/die_clock_check.py`. The stream log is `el1016-die-clock.log`.

## 1. Why the earlier die trees failed

The S81 c26b_r pilots from 10-16 were measured with OpenSTA propagated clocks:

| tree | sinks | cells | TT insertion (pin) | pin spread |
|---|---|---|---|---|
| Codex serial, graph mode | 180 | 950 | 0.38 .. 8.15 ns | 7,772 ps |
| Codex serial, full-die H-tree | 180 | 2,756 (1,283 pads) | 29.9 .. 33.8 ns | 3,885 ps |
| DIE-CLOCK serial, regional + measured trim | 180 | 3,529 | 2.54 .. 2.77 ns | flop spread 16 ps |

Four causes were found:

- **Balance existed only in the model.** The H-tree model predicted 42.8 ps of spread. Each stage's error in the
  `stage_ps` model, and each fixed 20 ps pad, adds up over 100+ stages: the model gave 14.8 ns of insertion and the
  measurement gave 32 ns.
- **The tree ignored where its sinks were.** A full-die H-tree was rooted at the die centre for sinks that sit in a
  7 x 8 mm hub.
- **Some runs over blocks were never buffered.** Wires of 0.4 to 1.2 mm over hard blocks left 57 nets with slews up to
  894 ps, so the stage delays depended on slew.
- **Graph mode is unbalanced by construction.** In it, insertion grows with depth in the communication graph.

ASAP7 M8 measures 8.4 ohm/um and 0.10 fF/um. A BUFx24 repeater every 170-200 um therefore costs about 0.3 ps/um, so the
insertion of a die tree is set mainly by how far the root is from the sinks. An insertion of a few ns is unavoidable
over several mm. What must be controlled is the skew between sinks, and the non-common path between communicating tiles.

## 2. Structure

1. **Clock regions.** Each region gets one tree.
   - A region is a set of sinks that exchange data synchronously: a hub, a field column, a quadrant, a lane.
   - Regions that are connected only through mesochronous FIFOs or forwarded clocks are not balanced against each
     other. Examples are the S81 `dsfd_cfifo` (`ot_meso_fifo`, DEPTH 8 / OFFSET 4) and the forwarded station clocks
     fi/fo/fn.
   - Regions whose clocks have a fixed-ratio seam share one target through `balance_group`. Examples are S81
     stream 833.3 / serial 1111.1 on the 3.333 ns epoch, with the VM x34/x43 and capture x8x t/s seams, and HBM
     serial:stream 3:4. The group offset is applied as pads on the tree's common path, at the input of its top
     buffer, and never at the leaves.
2. **Leaves.** Sinks are clustered by master pin, within a 60 um cell, with at most 12 pins per cluster. Each cluster
   gets one BUFx24 at the nearest free site. All pins of a leaf share one target R.
3. **Topology.** Leaves are paired by recursive median bisection and merged bottom-up with zero skew (DME-like).
   - The merge point lies on the actual obstacle-aware route (`die_clock_tree.Grid.route`) between the two child
     roots, where their model delays meet. Balance therefore comes from where wire is placed, not from pads.
   - A repeater is placed every 200 um, and a run over a block is at most 400 um.
4. **Measured trim. This is the only balance that counts.**
   - In-process OpenSTA with propagated clocks and placement parasitics (`set_wire_rc -clock -layer M8`) measures the
     arrival at every sink.
   - Target per sink: `arrival + R = phi`, where R is the tile view's in-arc clock insertion (the die kit's
     `insertion_per_clock_pin_ps`). Each pin therefore arrives at phi - R, which is the owner's 10-13 delivery rule.
   - Each leaf gets `round((phi - mean(arrival + R)) / pad_ps)` real BUFx12f pads at its input. `pad_ps` is measured
     in context, from the previous iteration's padded leaves.
   - Iterate until every tree and every group is within `--tol` (20 ps), or 4 iterations.
5. **Legal physical cells.** Every cell is a real ASAP7 buffer on a 1.62 x 0.27 um site lattice, outside every hard
   block and every existing standard cell. Its nets are typed CLOCK. Nothing is ideal: the output ODB is the
   input to GRT.

## 3. Measurement and report

- `build.py` writes `manifest.json` (cells, parent map, leaves, iterations), `arrivals_tt.tsv` (every sink and every
  clock-cell output), `drv_tt.rpt` and `clock.odb`.
- `build.py --measure ... --corner ff|ss` re-measures the final ODB at another corner.
- `to_dump.py` converts the manifest and arrivals into a `die_clock_check.py` dump, carrying the die's data pairs.
- `die_clock_check.py report DUMP --targets kit.json` reports, per region:
  - entries;
  - insertion, late and early;
  - flop-arrival spread (pin + R);
  - for intra-region pairs, the non-common path (NCP) and the pin and flop skew;
  - inter-region pairs.

  A multi-entry tile is paired with its neighbour through the nearest entry pin.
- `plot.py` draws the picture: blocks, tree edges per region, and sinks coloured by flop arrival minus target.
  **Look at it every step.**

Targets per region:

| quantity | target |
|---|---|
| flop-arrival spread at TT and FF | <= 80 ps (trim tolerance 20 ps) |
| flop skew on intra-region pairs | <= 80 ps |
| slew / cap violations | 0 |
| insertion | reported; no rule at die level (the owner's 300 ps rule is for tiles over 15k sinks/root) |
| NCP | reported, and minimised by the topology |

## 4. Integration into a die trial (S81 shown; the same hooks apply to Qwen and HBM)

1. PLACE writes `a_real/floorplan.odb`. The kit writes `kit/kit.json`, which holds R per master pin.
2. `CLOCK_PHYS`: `build.py --odb a_real/floorplan.odb --spec spec.json --targets kit/kit.json --write-odb`, then
   `--measure` at ff and ss. The ODB with the tree becomes the GRT input.
3. `kit_latency.py --kit kit --phys CLOCK_DIR --out kit_phys` rewrites `latency_<c>.tcl` with the measured pin
   arrivals.
   - No `balance_latency` is applied, because R is already compensated physically. The ETM reference compensation is
     unchanged.
   - Each column clock gets its source latency from the measured trunk arrival at its cfifo `ck` plus the ck -> co
     pass.
4. GRT on the clocked ODB, then die STA with `kit_phys`. Later, propagated STA on `die_grt.v` + SPEF replaces step 3.
5. Fixed-ratio seams must be timed as related clocks, with multicycles taken from the compiled schedule. For S81 the
   windows are >= 1.389 ns setup and >= 1.111 ns hold, on the 3.333 ns epoch. Do not use `set_clock_groups
   -asynchronous` for them. Both capture resets must release on the common epoch edge.

## 5. Spec format

```json
{"rc_layer": "M8", "leaf_um": 60, "leaf_max": 12,
 "trees": [
  {"name": "serial", "root": "sp_collective/pll_serial[0]", "period": 1111.111, "balance_group": "hub"},
  {"name": "scfifo", "root": "sp_collective/pll_stream[0]", "select": {"master_prefix": ["dsfd_cfifo"]}},
  {"name": "shub",   "root": "sp_collective/pll_stream[0]", "balance_group": "hub",
   "select": {"bbox": [11500, 14500, 21500, 24500]}},
  {"name": "sfar",   "root": "sp_collective/pll_stream[0]", "select": "all"},
  {"name": "col", "root_master_prefix": "dsfd_cfifo", "root_port": "co[0]", "balance_group": "col"}]}
```

Trees that share a root claim its loads in spec order: the first matching selection wins. Every load of a root must
be claimed by some tree. `root_master_prefix` expands to one tree per instance of that master.

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
     serial:stream 3:4. The group offset is applied as pads on the tree's common path (hierarchical trim, step 4),
     never at the leaves.
2. **Leaves.** Sinks are clustered by master pin, within a 60 um cell, with at most 12 pins per cluster. Each cluster
   gets one BUFx24 at the nearest free site. All pins of a leaf share one target R.
3. **Topology.** Leaves are paired by recursive median bisection and merged bottom-up with zero skew (DME-like).
   - Each leaf enters the merge with its model delay **plus R** (the leaf master pin's TT in-arc insertion), so the
     merge balances flop arrival (pin + R): every pin arrives at phi - R by construction. Balancing pin arrival
     instead left the whole R spread (300-730 ps on S81) to the trim, which then put pads on nearly every one of 62k
     leaves (1.58 M pads in one iteration, s81_full_t2b, 10-16 13:40).
   - The merge point lies on the actual obstacle-aware route (`die_clock_tree.Grid.route`) between the two child
     roots, where their model delays meet. Balance therefore comes from where wire is placed, not from pads.
   - A repeater is placed every 200 um, and a run over a block is at most 400 um.
4. **Measured trim. This is the only balance that counts.**
   - In-process OpenSTA with propagated clocks and placement parasitics (`set_wire_rc -clock -layer M8`) measures the
     arrival at every sink.
   - Target per sink: `arrival + R = phi`, where R is the tile view's in-arc clock insertion (the die kit's
     `insertion_per_clock_pin_ps`). Each pin therefore arrives at phi - R, which is the owner's 10-13 delivery rule.
     phi is the maximum flop arrival of the tree's **balance group** (one target for trees with a fixed-ratio seam).
   - **Hierarchical trim.** Each leaf needs `round((phi - flop arrival) / pad_ps)` real BUFx12f pads between the root
     and itself. The part that every leaf below a tree node needs is inserted **once, at that node's input** (the
     minimum over its leaves minus what its parent already carries). A group offset therefore lands on the tree's
     common path next to the root, a subtree offset at its branch point, and only the residual at the leaves. Trimming
     every leaf to the group maximum instead (the first HBM t1/t2 builds) needs 2.4-4.6 M pads for a 5-9 ns
     tree-to-tree insertion difference; the within-tree spread there is only 55-312 ps.
   - `pad_ps` is measured directly on the chains inserted in the previous iteration (arrival at the last pad's
     output minus the arrival at its driver's output). Calibrating it from the change in leaf arrival is wrong once
     the common path also moves (it read 441.6 ps/pad on HBM t3; a pad is about 15 ps).
   - Iterate until every tree and every group is within `--tol` (20 ps), or `--iters`.
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
5. Fixed-ratio seams must be timed as related clocks, with the window taken from the compiled schedule. For S81 the
   windows are >= 1.389 ns setup and >= 1.111 ns hold (the bank's next write), on the 3.333 ns epoch
   (`rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_x8_x43.sv` bank table). `tools/s81/die_sta.py` (`seam_constraints`) does
   this whenever seam leaves are in the die (masters `*x34_[ts]*`, `*x43_[ts]*`, `*x8x_[ts]*`; `_t` = stream root,
   `_s` = serial root):
   - serial and stream are in one clock group (only hbm stays asynchronous);
   - `set_max_delay 1388.889` / `set_min_delay -1111.111` from the other root's clock into every pin of a seam leaf,
     with clock latencies included, so the physical tree skew counts;
   - every other serial <-> stream path keeps the tightest-edge default (277.8 ps) and fails visibly: only a
     scheduled seam may cross;
   - the seam leaves' reset nets are timed (both capture resets release on the common epoch edge); the other
     endpoints of those nets stay false-pathed.
   The same pattern applies to the HBM serial:stream 3:4 seams and to any Qwen ratio seam: relate the clocks, give
   each seam its compiled window, and never use `set_clock_groups -asynchronous` for a scheduled seam.

## 4b. Method for the HBM and Qwen die leads (H-DIE, Q-COMPUTE-DIE, Q-KVSYS-DIE)

1. Dump the die's clock nets: `tools/die_clock_geom_dump.py` (or the die's `die_clock_dump.tsv`). Find every clock
   root (PLL / clock-generator outputs, region roots such as forwarded or FIFO roots).
2. Draw the regions: one tree per synchronous region (a quadrant, a lane group, a hub, one column). Put trees that
   exchange data synchronously, or across a fixed-ratio seam, into one `balance_group`. Regions joined only by
   mesochronous / Gray FIFOs or forwarded clocks need no common target.
3. Write the spec (section 5) and run `build.py --odb <PLACE odb> --spec --targets <kit with R per master pin>
   --iters 5 --write-odb` through ot-run (EPYC4, about 5-45 GB). Then run `--measure` at ff (and ss for sensitivity).
4. Look at `plot.py` images of the whole die and of each region, and read the report of
   `die_clock_check.py report` (`to_dump.py` first). Gate: flop-arrival spread within each group <= 80 ps at TT and
   FF, zero slew / cap violators.
5. Hand the clocked ODB to GRT and the measured arrivals to the die STA (S81 uses `kit_latency.py`; HBM / Qwen use
   the same arrivals as `set_clock_latency` per tile clock pin, with no balance_latency).
6. Large die insertion (8-13 ns on an 830 mm2 die) is expected. It is not a violation by itself: what is checked is
   the skew within a group at TT and FF, and the non-common path of communicating pairs, which `die_clock_check.py`
   reports per region.

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

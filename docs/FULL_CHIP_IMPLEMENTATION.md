# Full-chip hierarchical implementation

Workstream of [TOKEN_PIPELINE_OPTIMIZATION_PLAN.md](TOKEN_PIPELINE_OPTIMIZATION_PLAN.md) §6:
hardened blocks with abstracts, timing budgets at block boundaries, re-closure
against the budgets, and a top-level floorplan, power grid, clock tree and
route, for all three architectures, on ASAP7 at a 1.0 ns clock.

Flow: `tools/chip_assembly/` (tests: `tests/test_chip_assembly.py`).
Records: `results/physical_abi3/asap7/chip/`.

**Status (2026-09-28):** The Qwen tile and reduced-die flow is available,
with adopted reduced physical-sector tests and physical tile routes tracked in
`results/physical_hdc/`. The DeepSeek-V4.1 core used by current RTL campaigns
is `rtl/hdc/v41x/ot_hdc_core_v41x.sv`. Its RTL tile and layer die
(`rtl/chip/ot_chip_v41x_tile.sv`, `rtl/chip/ot_chip_v41x_die.sv`) wire the
core with all adopted units to its ROM banks, the QE weight stream, the pooled
index-key path and the attention KV prefetch, all on four behavioural HBM3E
stack interfaces. A reduced token through the die top is bit-exact with the KV
starting in HBM (`results/rtl/hdc_v41x_die_top_smoke.json`). The V4.1 physical
assembly stays disabled until matching memory macro interfaces, a floorplan and
routes exist. Block and array campaigns
are evidence for their stated boundaries, not substitutes for a chip route.

## 1. The hierarchy

Three levels, each an OpenROAD-flow-scripts design driven by
`tools/chip_assembly/case.py`. A parent receives its children's abstracts as
macros and places them with `MACRO_PLACEMENT_TCL` from the floorplan in
`tools/chip_assembly/floorplans.py`. The ORFS `BLOCKS` feature is not used,
so each block's constraints, pins and power grid belong to this flow.

| Level | Design | Routing layers | Power pins | Contents |
|---|---|---|---|---|
| 1 | hardened block | M2–M6 | M6 stripes | standard cells |
| 2 | Qwen tile (`rtl/chip/ot_chip_hdc_tile.sv`) | M2–M8 | M8 | level-1 macros, memories, glue |
| 3 | Qwen reduced die (`rtl/chip/ot_chip_die2x2.sv`) | M2–M9 | M9 | tile macros, PHY placeholders, collectives |

The V4.1 tile and die exist as RTL around `rtl/hdc/v41x/ot_hdc_core_v41x.sv`
(`rtl/chip/ot_chip_v41x_tile.sv`, `rtl/chip/ot_chip_v41x_die.sv`), with the
HBM3E interfaces as the adopted gates' simulation timing models. They have no
floorplan, macro views or route yet, so
`tools/chip_assembly/assemble.py --arch v41_rom` still rejects the build.

Each level's grid is in `tools/chip_assembly/tcl/pdn_{block,tile,die}.tcl`.
A child's power pins sit on the top layer it uses, and the parent drops vias
onto them: M6–M7 for blocks and M8–M9 for tiles. The memory and PHY
placeholders expose power on M4, like the platform's fakeram macros, and take
M4–M5 vias.

Abstracts come from ORFS `generate_abstract`. `write_abstract_lef
-bloat_occupied_layers` gives a LEF with every used layer obstructed.
`write_timing_model` gives a Liberty model of the routed block with its
extracted parasitics. Both are copied to `results/.../chip/abstracts/`.

### Tile

The tile is one mesh node. It is the composition that
`rtl/test/tb_hdc_array.sv` and `tb_hdc_core_hbm.sv` simulate, made
synthesizable:

- the decode core: sequencer, matrix engine (ME, `ot_hdc_matvec`) and stream
  unit (SU, `ot_hdc_stream`);
- the KV streamer (KVS, `ot_hdc_kv_stream`);
- the package controller (`ot_rom_pkg_ctrl`, wrapped as `ot_chip_pkg_ctrl`);
- a 5-port 512-bit router (`ot_rom_fabric_router`, wrapped as `ot_chip_router`);
- the core's memories as macros.

The ME, SU, KVS, controller and router are hardened macros. The sequencer and
glue are flat logic in the tile.

The router's four mesh ports use a pipelined, credit-flow link
(`rtl/chip/ot_chip_mesh_link.sv`), split at the tile boundary so that every
tile pin is a register. The link is needed because ASAP7 buffered wire costs
0.60 ps per µm plus 190 ps of flop overhead. That is a least-squares fit of the
routed express-link records (`floorplans.wire_delay_model()`). At that cost a
router-to-router hop of one tile pitch, 1.2–2.4 mm, cannot fit in one cycle.
The link carries 3 register stages each way and a 12-flit receive FIFO, which
covers the credit round trip. `rtl/test/tb_chip_mesh_link.sv` checks it:
2,000 flits arrive in order in 2,000 cycles, and in order under 40% and 90%
receiver stalls.

Memories are placeholders (`tools/chip_assembly/macros.py`) until the memory
compilers land. Each has LEF, Liberty and a blackbox Verilog stub with the
exact multi-port port list the core uses. Area and timing come from stated
models:

- SRAM uses the bit density of the platform's `fakeram7_256x256` times a port
  factor. Its clock-to-q is 218 ps and its setup 50 ps, as that macro's
  liberty gives.
- ROM uses 9.630 MB/mm², the ASAP7 via-programmed density
  (docs/RESEARCH_PROVENANCE.md).

The fakeram macros themselves are single-port, and the core's memories are
not.

### Die

The reduced die is 2 × 2 tiles, mirrored MY in the second column and MX in the
second row. That is the usual tile flipping: neighbours face each other with
the same edge, so the mesh channel between them is a 20 µm, flop-to-flop gap.

- **Qwen ROM and HBM die:** every tile's outward S port and its KV HBM port
  face a PHY strip. The strip holds a UCIe module and an HBM PHY-and-controller
  slice under each tile. The outward W ports go to board SerDes.
- **V4.1 layer die:** `rtl/chip/ot_chip_v41x_die.sv` connects a vector-memory
  collective DMA to the one-shot reduction and multicast engine, then to UCIe
  and board-link ports, beside the package controller and fabric router. The
  reduced token runs through the die's core tile and HBM stacks; the collective
  and link paths are linted and elaborated but not yet exercised by a bench,
  and the die has no physical closure.

## 2. Timing budgets

`tools/chip_assembly/budgets.py` derives every block's I/O budget from the
tile's top-level paths:

1. **Characterise the boundary.** Each block is synthesised (ORFS) and
   characterised per port bus by OpenSTA (`boundary.py`). The characterisation
   gives the pre-layout internal delay of each port: in2reg for an input and
   reg2out for an output. Records: `results/.../chip/boundary/`.
2. **Time the tile with block models.** Each block becomes a pre-layout timing
   model, a Liberty cell with those delays. The tile is synthesised with the
   models as black boxes, and OpenSTA times every macro pin.
3. **Add the floorplan's wire.** The wire is the Manhattan distance from the
   pin's edge to the far end of the worst path, priced with the wire model.
   Glue logic is taken to sit within 200 µm of the pin it serves. A capture
   register fed by a single macro pin is taken to sit within 50 µm.
4. **Divide the slack.** Path slack is `T − U − internal − external − wire`,
   with T = 1,000 ps and U = 30 ps. The slack is divided in proportion to the
   delays on the path. A block keeps at least `max(1.3 × internal + 40 ps,
   150 ps)` when the outside can afford it, and the port is marked `tight`
   when it cannot. A path whose slack is negative is a `violation`. A port on
   a combinational path through the block gets a through-budget instead.
   Quasi-static configuration ports are false paths.
5. **Write the block's constraints.** Each block's SDC carries
   `set_input_delay` or `set_output_delay` equal to `T − U − budget` per port
   bus. There are no I/O false paths. The tables are in
   `results/.../chip/budgets/tile_<arch>.{json,md}`.

The first pass found three architectural problems at this floorplan, and the
floorplan and RTL changed in response:

- **The SU's KV writes crossed the ME to reach the streamer.** They needed
  970 µm of wire (582 ps). The streamer moved to the south row beside the
  SU.
- **The controller drove the core's start, token and position
  combinationally.** Its boundary was timed for an adjacent core. The tile now
  registers them, which costs one cycle per token. The controller's
  `core_token` is still 923 ps deep inside the controller, so it remains the
  table's only violation.
- **The HBM request ports ran from the tile's W edge to the streamer.** They
  now leave on the south edge under the streamer, where the die puts the HBM
  slice.

## 3. Block re-closure against the budgets

`tools/chip_assembly/harden.py` hardens each block on the die size and pin
edges the tile floorplan gives it. The budgeted SDC replaces the synthesis
SDC, and a changed budget restarts the flow from the netlist. After
`generate_abstract`, every budgeted port's routed delay, read from the block's
extracted timing model (`etm.py`), is compared with its budget. Records:
`results/.../chip/blocks/<block>.json`.

## 4. Top level

`tools/chip_assembly/assemble.py` builds the tile (level 2) and then the die
(level 3) from the abstracts. The flow places the macros, then builds the
power grid, the clock tree across the macros and the route. Both steps then run
the same post-route boundary report: every macro pin is timed with the
macros' extracted models and the parent's extracted parasitics. It gives the
worst slack per bus and the clock arrival at every macro (the inter-block
skew). Records: `results/.../chip/tiles/`, `results/.../chip/dies/`.

## 5. Current implementation status

| Gate | Qwen3-8B | DeepSeek-V4.1-Flash |
|---|---|---|
| Adopted core RTL | `rtl/hdc/ot_hdc_core.sv`; timed HBM KV and physical sector tests | `rtl/hdc/v41x/ot_hdc_core_v41x.sv`; reduced all-unit, HBM and switched-array campaigns |
| Chip tile and reduced die | `rtl/chip/ot_chip_hdc_tile.sv` and `rtl/chip/ot_chip_die2x2.sv` | `rtl/chip/ot_chip_v41x_tile.sv` and `rtl/chip/ot_chip_v41x_die.sv`: RTL only; one reduced token bit-exact through the die top (`results/rtl/hdc_v41x_die_top_smoke.json`) |
| Memory interface | core KV requests reach the tile HBM interface | QE weights, pooled index keys and attention KV (prefetch behind the core's KV_HBM gate, K ports arbitrated with the indexer) on the die's behavioural HBM3E stacks |
| Physical closure | W4/G2 reduced tile accepted at 1.5 ns; wider G4/W4 and G4/W8 routes remain open | adopted block routes exist; no whole-core, tile or die timing closure |

The flow's former V4.1 tile macro dimensions and placement were tied to an
older port list. A new floorplan must be derived from the adopted core's
per-lane vector ports, dedicated weight/attention/index engines, the pooled
HBM request channels, and actual ROM/SRAM compiler interfaces. The analytical
die area model does not supply that missing port-level floorplan.

## 6. Remaining implementation work

1. Replace the tile's behavioural ROM and vector-memory arrays with compiler
   macros and a banked vector memory; register and constrain every memory and
   link boundary.
2. Exercise the die's package controller, fabric router, collective engine and
   UCIe / board-link ports in a multi-die bench (the smoke drives the core from
   the host port), and add the remaining collective engines of the ledger.
3. Run full-token RTL across the integrated die and switched multi-package
   array, then characterise the adopted tile and die with macro views, clock
   trees, routing and extracted timing. Treat the 1.087 GHz V4.1 design point
   as conditional until these gates close.
4. Complete scan, multi-corner timing, IR drop and power sign-off on the
   adopted implementation.

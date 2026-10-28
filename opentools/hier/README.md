# opentools/hier — macro-aware hierarchical flow around OpenROAD

Status: **v0.2** (lane OSS-HIER-1, 2026-10-27): region-map partitions, shared plan schema,
abstract check, boundary-pin hierarchical STA. Working end to end on
one small public design; not production quality. Not published; no outside
contact without owner approval.

## Why

OpenROAD runs flat designs well up to a few hundred thousand cells. In our
measurements, runs of 0.53–1.31 M cells failed in CTS or global placement.
A 600–860 mm² die therefore turns into thousands of ~0.1 mm² hard cores,
and every one of them adds a clock entry, a latency match, seam timing and
pin placement. Industry flows use a few dozen to a few hundred larger
partitions instead. This tool takes a gate-level netlist and produces:

1. **partitions from the region map** (`--region-map`, METHODOLOGY 12.13/12.14g):
   each locality region of the shared plan becomes one partition (1 clock region ==
   1 partition); cells are mapped by instance-path prefix, unmapped glue follows its
   strongest connection, the region rectangles are binding, the 400k cell cap is
   enforced. Without a map, K partitions come from connectivity clustering;
2. **top-down pins and timing budgets** for each partition;
3. **ORFS design directories** for each partition and for the top (ORFS
   `BLOCKS` convention, `SYNTH_NETLIST_FILES`), plus a flat baseline
   built from exactly the same cells;
4. **abstracts** for each partition: an ORFS `generate_abstract` LEF and
   an ETM liberty model (`write_timing_model`; it includes the
   partition's own clock insertion), and **top assembly** on those
   abstracts;
5. **hierarchical STA** in three views, flat, stitched and ETM, with the
   correlation between them reported.

## Pipeline

```
 gate netlist (Yosys JSON) ──► ohier plan ──► GEN/plan.json  (shared plan schema: regions, pins, budgets)
                                           ├► GEN/<top>_P<i>/{.v, constraint.sdc, io.tcl, config.mk}
                                           ├► GEN/{top.v, config.mk, macro_place.tcl, design.sdc}
                                           └► GEN/flat/{<top>.v, config.mk}       (same cells, same die)
 ohier plan --region-map MAP.json ...          : partitions = the map's regions
 ohier verify      : name-based structural equivalence, original vs partitioned (and vs flat)
 scripts/orfs_flow.sh GEN WORK blocks|top|flat   (ORFS docker; partitions run in parallel)
 ohier sta-scripts + scripts/sta_run.sh          (OpenSTA: flat / stitched / etm views)
 ohier abstract    : LEF/ETM vs plan (slot size, pin sets), partition clock insertion -> shared plan
 ohier compare     : WNS/TNS per view, boundary WNS, per-endpoint and per-boundary-pin slack correlation
```

### Modules (`ohier/`)

| file | job |
|---|---|
| `liberty.py` | minimal Liberty scanner (area, sequential, pin directions) and LEF macro sizes |
| `netlist.py` | Yosys JSON → flat leaf graph with hierarchical names; instance tree with cell/area/macro counts |
| `partition.py` | frontier items (subtrees ≤ `unit_max_cells` stay whole) → agglomerative clustering under cap + area balance → FM-style refinement → slicing floorplan with shelf-packed macro fit |
| `pins.py` | per-port edge choice facing the centroid of the net's other regions (die edge for chip IO; clock pin faces the die centre); per-edge legalization at a fixed pitch with spill to the next edge; `set_io_pin_constraint` slots |
| `budget.py` | flat levelization; budget split by logic depth before and after each crossing; SDC with `-network_latency_included` against a common partition clock latency L |
| `emit.py` | flat, partition and top Verilog; ORFS `config.mk` for each partition, the top and the flat baseline; `place_macro` for the top |
| `verify.py` | structural equivalence by leaf name: same leaves, same types, same connectivity, same constants |
| `hsta.py` | OpenSTA Tcl for the three views; `-format end` parser; correlation statistics |
| `schema.py` | plan I/O through the shared schema `opentools/common/plan.py` (see below) |
| `abstract.py` | LEF + ETM readers; abstract check against the plan; ETM clock insertion |

### Shared plan schema

ohier reads and writes `opentools.plan/1` through `opentools/common/plan.py`
(owner OSS-CLKPLAN-1; not forked). Mapping:

- `regions[]`: one per partition, `{name, rect, partition: <module>}`;
- `macros[]`: each partition as a die-level hard block `u_<module>`
  (`kind: hard_core`, `rect` = slot, `region`, `clock_pins[clk]{xy, insertion_ps{TT}}`).
  `ohier abstract` fills `insertion_ps` from the ETM `max_clock_tree_path`, so the
  clock tools balance the partition like any other macro with its own insertion;
- `clock`: `{name, period_ps, target_latency_ps}`;
- `hier`: ohier's own output (pins, budgets, metrics, region details, abstract checks).
  Input key `hier.region_members = {region: [instance-path prefix, ...]}` is the
  membership part of the region map (proposed for the locality tool to write).

## Demo: ORFS `asap7/riscv32i` (4 fakeram7_256x32 macros), 3 map regions

The script is in `demo/riscv32i/run_demo.sh`; results are in
`demo/riscv32i/RESULTS.md`.

The flat baseline runs on the identical netlist and die. A stock ORFS
re-synthesis would rename cells, so endpoint-level correlation would not
be possible.

## Tests

`python3 opentools/hier/tests/test_ohier.py` (or pytest) runs 7 tests on a
synthetic hierarchical design with macros, with no EDA tools needed. They
cover:

- Liberty and LEF parsing;
- flattening;
- the cap, overlap, macro-fit and in-die rules for regions;
- pins on their own edge at least one pitch apart;
- budgets summing to the period;
- emitted Verilog that is structurally equivalent to the input;
- the verifier catching a changed connection;
- levelization;
- STA report parsing and correlation.

## Limits (honest list)

- **Corner.** Emitted ORFS configs pin `CORNER = TC` (ORFS asap7 defaults to BC = FF; before OSS-HIER-2 every
  block/ETM was FF while the STA was TT, which was the whole +340 ps ETM error). Old FF runs: `scripts/etm_tt.sh`.
- **ETM hold.** OpenSTA `write_timing_model` keeps one (max) table per arc: the ETM view is setup-only, hold is
  signed off on the stitched view (OSS-HIER-2: per-pin hold error mean +176..+191 ps optimistic).
- **Context.** `set_driving_cell`/`set_load` from the top (default on) double-count the driver delay with
  load-indexed ETMs (measured -21 ps, pessimistic); `--no-context` turns it off.

- **Partitioner.** The partitioner is greedy agglomerative clustering plus
  FM moves. It is not multilevel hMETIS/TritonPart quality and has not been
  tried above about 10k items. The cost is cut only; wire length enters
  through the floorplan order and the pin placement, not through the
  clustering objective.
- **Floorplan.** The floorplan is a slicing floorplan with an exhaustive
  bisection search for K ≤ 8 and a balanced cut above that. Macro fit is
  checked by shelf packing with no rotation (ORFS macro placement does
  not rotate fakeram). The core grows in 5% steps until the macros fit.
  There is no channel sizing from routing demand.
- **Budgets.** The budgets are first-pass: a logic-depth ratio, a wire
  delay of `ps_per_um` times the Manhattan distance between pin slots,
  and a common latency L. Hold budgets are zero-logic (input `-min` = L,
  output `-min` = −L). There is **no re-budgeting loop** from the measured
  ETM arcs yet. The chip IO budget is the design SDC IO delay, applied
  approximately. Multi-clock designs are not handled: only one clock is
  supported.
- **Top-level clock.** The top-level clock is ORFS CTS on the top netlist.
  It does not yet balance against each partition's measured insertion;
  that is OSS-MSCTS-1's job through the shared schema.
- **Top routing.** Top-level routing uses M2–M9 in the channels and over
  the partitions; the partitions use ≤ M5. Track allocation is
  OSS-METAL-1's job.
- **Netlist I/O.** Ports must be `[W-1:0]` buses (no offset or downto
  checks). Undriven `x` bits are written as `1'bx`. The netlist flow
  assumes every leaf cell is in the liberty set given to `ohier plan`.
- **ORFS hierarchical synthesis.** ORFS hierarchical synthesis with
  `SYNTH_MINIMUM_KEEP_SIZE=0` writes `input signed` declarations that the
  OpenSTA Verilog reader rejects (`synth_odb`, STA-0171). ohier avoids
  this because it re-emits the netlist itself; the problem is upstream
  and was not reported (no outside contact).
- **Runtime.** No partition runs above about 10k cells have been made
  with this tool yet. The 400k cap comes from the owner measurement, not
  from this demo.

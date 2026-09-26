# Design for test: scan, JTAG and ATPG

Date: 2026-09-25. Workstream "Scan and test" of
`docs/TOKEN_PIPELINE_OPTIMIZATION_PLAN.md` section 6. Before this work no
design in the repository had any design-for-test.

This document covers four things:

- the scan-insertion option in the physical flow;
- the JTAG test access port;
- the stuck-at ATPG, with fault coverage, pattern counts and gate-level
  confirmation;
- the area, clock and wirelength cost of scan.

It closes with the status for each of the three architectures and the
interfaces the memory-BIST and full-chip workstreams hook to.

## 1. Scan insertion

### What the ORFS image offers

The pinned ORFS image's OpenROAD has a DFT module (`scan_replace`,
`set_dft_config`, `execute_dft_plan`). It cannot scan an ASAP7 design. On a
two-flop test netlist `scan_replace` reports "No scan equivalent lib cell
found" for `DFFHQNx1_ASAP7_75t_R`. The reason is that the ASAP7 Liberty
carries no `test_cell` groups, which is how that module finds a scan
equivalent. ASAP7 does ship muxed-D scan flops (`SDFHx1`…`SDFHx4`,
`SDFLx1`…`SDFLx4`), and ORFS lists them as don't-use.

### The inserter

Scan is inserted by `tools/dft/scan_insert.py` into the flat netlist ORFS
synthesised. The driver runs it between synthesis and floorplan, in the gap it
already uses to normalise the netlist. Every step is derived from the Liberty
functions, not from cell names:

- **Flops with a scan equivalent** (`DFFHQN*`, `DFFLQN*`) become `SDFH*` or
  `SDFL*`. The equivalence is checked on the truth tables: with `SE`=0 the
  scan cell's next state must equal the flop's.
- **Flops without one** keep their cell and get an `AO22` scan multiplexer on
  the data pin (`D & !SE | SI & SE`). These are the asynchronous set/reset
  `DFFASRHQNx1` and the Q-output `DFF*Qx4`.
- **Chains.** Chains are balanced in length. They are formed per clock
  domain: the root clock net, traced back through buffers and inverters, plus
  the active edge. Within a domain, cells are chained in natural instance-name
  order, which keeps the bits of one register together.
- **Clock mixing.** With `mix`, a chain may cross domains. Each crossing gets
  a lock-up latch clocked by the launching domain and transparent in its
  inactive phase (`DLLx1` after a rising-edge cell). Negative-edge cells are
  ordered first, so a same-clock hand-off never needs a latch.
- **Asynchronous set and reset.** Each set or reset pin is traced to its
  source. A pin driven from a port is recorded as a test constraint that
  holds it inactive. A pin driven by logic is forced inactive through an
  `OR2`/`AND2` with a new `test_mode` input.
- **Ports.** The netlist gains `scan_en`, `scan_in[N-1:0]` and
  `scan_out[N-1:0]`, plus `test_mode` when a reset needed it. Each scan output
  is driven by a buffer from the last cell of its chain.

The rewrite is textual. Changed instances are re-emitted and new ones
appended; every other byte of the netlist is left as the synthesis tool
wrote it. The scan description (chains, cell order, polarities, constraints)
goes to `scan_chains.json`.

### In the physical flow

```
python3 tools/run_abi3_physical.py --view asap7 ... --stages pnr \
    --dft scan [--scan-chains N | --scan-max-length L] [--scan-clock-mixing mix]
```

A scanned route gets its own `DESIGN_NICKNAME` (`..._scan`), so it never
shares the ORFS results namespace with an unscanned route of the same top.
The summary is recorded under `place_and_route.dft`, and `scan_chains.json`
and the scanned netlist are retained as artifacts. Without `--dft` the
config.mk, the SDC and the record are unchanged
(`tests/test_abi3_physical_dft.py`). No SDC change is needed.
`--false-path-io` covers the new ports like any other. The shift path
(QN to SI) is register to register in the functional clock, so the routed
Fmax prices at-speed shift, and ORFS repairs its hold like any other path.

### Scan off changes nothing

`tools/dft/check_scan_equivalence.py` proves this with Yosys. The scanned
netlist, with `scan_en`=0 and `test_mode`=0, is checked against the netlist
before insertion (`equiv_make`, `equiv_simple`, `equiv_induct`). Cell models
are generated from Liberty. Flop states are matched by instance name, and
every state and every output must be proven equal. A mutated gate in the
test netlist fails the proof, which is the negative control
(`tests/test_dft_scan.py`).

## 2. Test access: the JTAG TAP

`rtl/dft/ot_tap.sv` is an IEEE 1149.1 TAP subset. It implements:

- the 16-state controller, with `TRST_N` and the five-TMS-high reset;
- a 4-bit instruction register. Capture-IR loads `0001`, and Test-Logic-Reset
  selects IDCODE.

| Opcode | Instruction | Data register |
|---|---|---|
| `0001` | IDCODE | 32-bit ID, LSB 1 (parameter) |
| `1111` and every unused code | BYPASS | 1 bit, captures 0 |
| `1000` | SCAN_CFG | `test_mode`, `scan_clk_sel`, serial/one-chain, chain index |
| `1001` | SCAN_ACCESS | the internal scan chains |
| `1010` | MBIST_CTRL | Capture-DR loads the BIST status, Update-DR writes the BIST control |
| `1011` | DFT_STATUS | read-only status word |

**Scan through the TAP.** Under SCAN_ACCESS, Shift-DR shifts the chains one
bit per TCK with `scan_en`=1, and Capture-DR applies one capture clock with
`scan_en`=0. A scan pattern is therefore a load (Shift-DR), a capture
(Capture-DR), and an unload that loads the next pattern (Shift-DR). Two modes
are selectable:

- serial: TDI → chain 0 → … → chain N-1 → TDO, which reaches every cell;
- one chain: the selected chain alone, for chain diagnosis.

**Clocking.** The chains keep the core's clock tree.
`rtl/dft/ot_dft_scan_clock.sv` selects the functional clock or TCK
glitch-free, with a two-stage synchroniser per side. It passes exactly the
TCK cycles the TAP enables, through a latch-based gate. TDO, the instruction
and the update registers change on the falling edge of TCK, as the standard
requires.

**Deviation from 1149.1.** EXTEST and SAMPLE/PRELOAD, and the boundary
register behind them, are not implemented. The standard makes them
mandatory, but the dies' pads are not in the RTL yet.

**Verification.** `rtl/test/tb_ot_tap.sv` drives only the TAP pins. It
connects a toy two-chain scanned core through the clock controller and runs
25 checks under Verilator 5.050 and under Icarus (`tests/test_dft_tap.py`):

- IDCODE, BYPASS (also for an unused opcode) and the Capture-IR value;
- SCAN_CFG write and read-back, and the clock switch-over;
- a full load, capture and unload through SCAN_ACCESS, checked against the
  core's next state, and a single-chain flush;
- MBIST_CTRL status capture, control update and update strobe, and
  DFT_STATUS;
- TMS reset, TRST_N and TDO enable.

The TAP lints clean under `-Wall`.

## 3. ATPG

`tools/dft/run_atpg.py` drives the flow. It has three parts.

- **The model** (`tools/dft/atpg_model.py`). This is the full-scan
  combinational model of the scanned netlist. The sources are the primary
  inputs and every scan cell's state. The observation points are the primary
  outputs and every scan cell's next state. Each library cell becomes a
  pin-buffer per input, the primitive network of its Liberty function, and a
  buffer per output. The fault list is stuck-at-0 and stuck-at-1 on every pin
  of every cell, uncollapsed, which is the universe commercial tools report
  on. Capture holds `scan_en`=0, the async resets inactive and `test_mode`=1.
- **The engine** (`tools/dft/otatpg.cpp`, written for this work). It runs:
  - 64-way parallel-pattern random patterns with event-driven fault
    simulation and fault dropping;
  - PODEM on every remaining fault, run in parallel, with SCOAP-guided
    backtrace and an X-path check. Each test cube is grown by further
    targets before it is randomly filled (dynamic compaction). Aborted faults
    are retried at 16 times the backtrack limit;
  - reverse-order fault simulation to drop redundant patterns.

  A fault counts as detected only when the final, fully specified pattern
  detects it in fault simulation. A fault PODEM exhausts without aborting is
  proven untestable under the constraints.
- **The chain test.** Scan-path faults (SI, SE, clock pins, the scan-out
  buffers) cannot be seen by capture. The engine's `--flush` mode grades them
  exactly. It is a three-valued sequential simulation of a 0011… flush through
  every chain from an unknown state, with the scan cells' next states
  Shannon-expanded on `scan_en`. A clock pin stuck at either value is modelled
  as a cell that never updates.

The fault classes are:

- DT: detected by a capture pattern;
- DS: detected by the chain test;
- UT: proven untestable;
- AU: aborted.

Fault coverage is (DT+DS)/all faults. Test coverage is (DT+DS)/(all − UT).

**Gate-level confirmation.** The engine's answers are checked on the netlist
itself (`tools/dft/gate_sim.py`), under Verilator 5 (or Icarus), with cell
models generated from Liberty. Each input pin is buffered inside its model,
so one pin of one cell can be forced without touching the net's other
branches. The bench works like a tester:

- it shifts every load through `scan_in` one clock per bit, all chains in
  parallel, while the previous response comes out of `scan_out`;
- it compares the primary outputs, pulses one capture clock and compares the
  unload;
- it runs a chain flush.

The load and unload streams are derived from the scan description (chain
order, and the inversion of every link), not from the ATPG model. A sample
of capture-detected faults is injected, each with its detecting pattern, and
a sample of chain-test faults is injected during a flush. Every injected
fault must produce a mismatch. On the toy netlist Verilator and Icarus give
identical per-fault results.

**Building the bench for big blocks.** The first benches called the shift and
capture tasks once per injected fault. Verilator inlines each call and
compiles large translation units, so the argmax collective's bench (about
10,000 cells) peaked at 8.3 GB <!-- figure: 8.3 src="results/dft/gate_bench_build_memory.json#default_build.peak_rss_kb" scale="1e-6" name="argmax bench default build peak GB" -->, and the stream unit's would have needed
several times that. Two changes fixed it:

- the bench now drives all faults from one loop, so each task has a single
  call site;
- `run_atpg.py --lean-build` builds without module inlining, with split
  output, `-O1` C++ and 4 jobs.

On the argmax bench this cut the peak to 1.2 GB <!-- figure: 1.2 src="results/dft/gate_bench_build_memory.json#lean_build.peak_rss_kb" scale="1e-6" name="argmax bench lean build peak GB" --> with identical results: the
same 82 patterns, 0 mismatches, and all 130 injected faults detected. That
measurement was taken at `-O0`; lean builds now compile at `-O1` for speed,
since split output already bounds each compile unit's memory.

**Sampling on the largest blocks.** Simulation time scales with cells ×
patterns × chain length, so replaying every pattern of the stream unit or the
matrix engine would take weeks. On those two blocks the check replays a
sample of patterns plus each sampled fault's detecting pattern, and injects a
random sample of faults. Each record's `gate_level.sampling` states the
sample sizes, the population they were drawn from and the seed.

## 4. Results: coverage, patterns and the cost of scan

The records are in `results/dft/<block>/` (`atpg.json`, `equivalence.json`,
`scan_chains.json.gz`). The paired routes are in
`results/physical_abi3/asap7/dft/<block>/{noscan,scan}/`, and
`results/dft/summary.json` collects them all. `tools/dft/summarize.py
--write-doc` regenerates the tables below from the summary.

**Test settings.** Chains are at most 1,024 cells long (`--scan-max-length
1024`). Faults are uncollapsed pin faults, clock pins included. The ATPG uses
a backtrack limit of 256, and aborted faults are retried at 4,096.

**Which netlist was tested.** For the package controller, the ATPG netlist is
the exact netlist the scanned route placed. For the stream unit, it is the
same ORFS synthesis, scanned with the same inserter settings. The other blocks
use the host Yosys synthesis of the same RTL
(`run_abi3_physical.py --stages synth`), because the gate kept their ORFS
routes waiting. Both syntheses map to the same ASAP7 RVT cells, and scan
insertion does not depend on which one produced the netlist.

**Paired routes.** Both routes of a pair use the same RTL, parameters and
settings: 0.9 ns target, `--false-path-io`, `--slew-margin-percent 20`,
`--stages pnr`. The only difference is `--dft scan`.

<!-- dft-tables:begin -->
| Block | Architectures | Scan cells | Chains (longest) | Pin faults | Fault coverage | Test coverage | Patterns | Gate-level check | Scan off equivalent |
|---|---|---|---|---|---|---|---|---|---|
| argmax collective `ot_rom_argmax_reduce` | V4.1 array | 2,264 <!-- figure: 2264 src="results/dft/summary.json#blocks.argmax_reduce.atpg.scan_cells" name="argmax_reduce scan cells" --> | 3 (755) | 80,616 <!-- figure: 80616 src="results/dft/summary.json#blocks.argmax_reduce.atpg.faults" name="argmax_reduce pin faults" --> | 98.52 <!-- figure: 98.52 src="results/dft/summary.json#blocks.argmax_reduce.atpg.fault_coverage" scale="100" name="argmax_reduce fault coverage %" -->% | 99.60 <!-- figure: 99.60 src="results/dft/summary.json#blocks.argmax_reduce.atpg.test_coverage" scale="100" name="argmax_reduce test coverage %" -->% | 2,376 <!-- figure: 2376 src="results/dft/summary.json#blocks.argmax_reduce.atpg.capture_patterns" name="argmax_reduce patterns" --> | 82 patterns, 0 mismatches; 130/130 injected faults seen | proven (2,813 points) |
| MoE expert port `ot_rom_moe_expert_port` | V4.1 array | 3,185 <!-- figure: 3185 src="results/dft/summary.json#blocks.expert_port.atpg.scan_cells" name="expert_port scan cells" --> | 4 (797) | 103,156 <!-- figure: 103156 src="results/dft/summary.json#blocks.expert_port.atpg.faults" name="expert_port pin faults" --> | 99.66 <!-- figure: 99.66 src="results/dft/summary.json#blocks.expert_port.atpg.fault_coverage" scale="100" name="expert_port fault coverage %" -->% | 100.00 <!-- figure: 100.00 src="results/dft/summary.json#blocks.expert_port.atpg.test_coverage" scale="100" name="expert_port test coverage %" -->% | 158 <!-- figure: 158 src="results/dft/summary.json#blocks.expert_port.atpg.capture_patterns" name="expert_port patterns" --> | 51 patterns, 0 mismatches; 130/130 injected faults seen | proven (4,312 points) |
| fabric router `ot_rom_fabric_router` | V4.1 array | 13,226 <!-- figure: 13226 src="results/dft/summary.json#blocks.fabric_router.atpg.scan_cells" name="fabric_router scan cells" --> | 13 (1018) | 506,234 <!-- figure: 506234 src="results/dft/summary.json#blocks.fabric_router.atpg.faults" name="fabric_router pin faults" --> | 99.87 <!-- figure: 99.87 src="results/dft/summary.json#blocks.fabric_router.atpg.fault_coverage" scale="100" name="fabric_router fault coverage %" -->% | 99.99 <!-- figure: 99.99 src="results/dft/summary.json#blocks.fabric_router.atpg.test_coverage" scale="100" name="fabric_router test coverage %" -->% | 508 <!-- figure: 508 src="results/dft/summary.json#blocks.fabric_router.atpg.capture_patterns" name="fabric_router patterns" --> | not run | proven (15,839 points) |
| KV streamer `ot_hdc_kv_stream` | HBM | 7,187 <!-- figure: 7187 src="results/dft/summary.json#blocks.kv_stream.atpg.scan_cells" name="kv_stream scan cells" --> | 8 (899) | 294,762 <!-- figure: 294762 src="results/dft/summary.json#blocks.kv_stream.atpg.faults" name="kv_stream pin faults" --> | 98.69 <!-- figure: 98.69 src="results/dft/summary.json#blocks.kv_stream.atpg.fault_coverage" scale="100" name="kv_stream fault coverage %" -->% | 99.87 <!-- figure: 99.87 src="results/dft/summary.json#blocks.kv_stream.atpg.test_coverage" scale="100" name="kv_stream test coverage %" -->% | 4,532 <!-- figure: 4532 src="results/dft/summary.json#blocks.kv_stream.atpg.capture_patterns" name="kv_stream patterns" --> | not run | proven (11,187 points) |
| matrix engine `ot_hdc_matvec` | HBM, Qwen3 ROM | 95,737 <!-- figure: 95737 src="results/dft/summary.json#blocks.matvec.atpg.scan_cells" name="matvec scan cells" --> | 94 (1019) | 3,230,104 <!-- figure: 3230104 src="results/dft/summary.json#blocks.matvec.atpg.faults" name="matvec pin faults" --> | 96.18 <!-- figure: 96.18 src="results/dft/summary.json#blocks.matvec.atpg.fault_coverage" scale="100" name="matvec fault coverage %" -->% | 99.85 <!-- figure: 99.85 src="results/dft/summary.json#blocks.matvec.atpg.test_coverage" scale="100" name="matvec test coverage %" -->% | 22,817 <!-- figure: 22817 src="results/dft/summary.json#blocks.matvec.atpg.capture_patterns" name="matvec patterns" --> | not run | not run |
| multicast node `ot_rom_mcast_node` | V4.1 array | 4,216 <!-- figure: 4216 src="results/dft/summary.json#blocks.mcast_node.atpg.scan_cells" name="mcast_node scan cells" --> | 5 (844) | 136,390 <!-- figure: 136390 src="results/dft/summary.json#blocks.mcast_node.atpg.faults" name="mcast_node pin faults" --> | 99.83 <!-- figure: 99.83 src="results/dft/summary.json#blocks.mcast_node.atpg.fault_coverage" scale="100" name="mcast_node fault coverage %" -->% | 100.00 <!-- figure: 100.00 src="results/dft/summary.json#blocks.mcast_node.atpg.test_coverage" scale="100" name="mcast_node test coverage %" -->% | 220 <!-- figure: 220 src="results/dft/summary.json#blocks.mcast_node.atpg.capture_patterns" name="mcast_node patterns" --> | 54 patterns, 0 mismatches; 130/130 injected faults seen | proven (5,342 points) |
| MoE dispatch `ot_rom_moe_dispatch` | V4.1 array | 2,155 <!-- figure: 2155 src="results/dft/summary.json#blocks.moe_dispatch.atpg.scan_cells" name="moe_dispatch scan cells" --> | 3 (719) | 71,156 <!-- figure: 71156 src="results/dft/summary.json#blocks.moe_dispatch.atpg.faults" name="moe_dispatch pin faults" --> | 99.48 <!-- figure: 99.48 src="results/dft/summary.json#blocks.moe_dispatch.atpg.fault_coverage" scale="100" name="moe_dispatch fault coverage %" -->% | 99.98 <!-- figure: 99.98 src="results/dft/summary.json#blocks.moe_dispatch.atpg.test_coverage" scale="100" name="moe_dispatch test coverage %" -->% | 296 <!-- figure: 296 src="results/dft/summary.json#blocks.moe_dispatch.atpg.capture_patterns" name="moe_dispatch patterns" --> | 51 patterns, 0 mismatches; 130/130 injected faults seen | proven (2,767 points) |
| package controller `ot_rom_pkg_ctrl` | V4.1 array | 4,482 <!-- figure: 4482 src="results/dft/summary.json#blocks.pkg_ctrl.atpg.scan_cells" name="pkg_ctrl scan cells" --> | 5 (897) | 189,740 <!-- figure: 189740 src="results/dft/summary.json#blocks.pkg_ctrl.atpg.faults" name="pkg_ctrl pin faults" --> | 97.74 <!-- figure: 97.74 src="results/dft/summary.json#blocks.pkg_ctrl.atpg.fault_coverage" scale="100" name="pkg_ctrl fault coverage %" -->% | 99.74 <!-- figure: 99.74 src="results/dft/summary.json#blocks.pkg_ctrl.atpg.test_coverage" scale="100" name="pkg_ctrl test coverage %" -->% | 1,223 <!-- figure: 1223 src="results/dft/summary.json#blocks.pkg_ctrl.atpg.capture_patterns" name="pkg_ctrl patterns" --> | 123 patterns, 0 mismatches; 250/250 injected faults seen | proven (5,660 points) |
| package link `ot_rom_pkg_link` | V4.1 array | 11,856 <!-- figure: 11856 src="results/dft/summary.json#blocks.pkg_link.atpg.scan_cells" name="pkg_link scan cells" --> | 12 (988) | 362,820 <!-- figure: 362820 src="results/dft/summary.json#blocks.pkg_link.atpg.faults" name="pkg_link pin faults" --> | 94.80 <!-- figure: 94.80 src="results/dft/summary.json#blocks.pkg_link.atpg.fault_coverage" scale="100" name="pkg_link fault coverage %" -->% | 100.00 <!-- figure: 100.00 src="results/dft/summary.json#blocks.pkg_link.atpg.test_coverage" scale="100" name="pkg_link test coverage %" -->% | 336 <!-- figure: 336 src="results/dft/summary.json#blocks.pkg_link.atpg.capture_patterns" name="pkg_link patterns" --> | not run | not run |
| stream unit `ot_hdc_stream` | HBM, Qwen3 ROM | 53,022 <!-- figure: 53022 src="results/dft/summary.json#blocks.stream.atpg.scan_cells" name="stream scan cells" --> | 52 (1020) | 2,227,034 <!-- figure: 2227034 src="results/dft/summary.json#blocks.stream.atpg.faults" name="stream pin faults" --> | 96.11 <!-- figure: 96.11 src="results/dft/summary.json#blocks.stream.atpg.fault_coverage" scale="100" name="stream fault coverage %" -->% | 99.85 <!-- figure: 99.85 src="results/dft/summary.json#blocks.stream.atpg.test_coverage" scale="100" name="stream test coverage %" -->% | 11,650 <!-- figure: 11650 src="results/dft/summary.json#blocks.stream.atpg.capture_patterns" name="stream patterns" --> | not run | not run |

| Block | Std-cell area, no scan → scan (µm²) | Area | Routed Fmax, no scan → scan (MHz) | Fmax | Routed wirelength | Status, no scan / scan |
|---|---|---|---|---|---|---|
| KV streamer `ot_hdc_kv_stream` | 6,423.88 → 7,073.21 | +10.1 <!-- figure: 10.1 src="results/dft/summary.json#blocks.kv_stream.route.overhead.standard_cell_area" scale="100" name="kv_stream scan area overhead %" -->% | 1,106.8 <!-- figure: 1106.8 src="results/dft/summary.json#blocks.kv_stream.route.noscan.fmax_mhz" name="kv_stream Fmax no scan" --> → 1,122.1 <!-- figure: 1122.1 src="results/dft/summary.json#blocks.kv_stream.route.scan.fmax_mhz" name="kv_stream Fmax scan" --> | +1.4 <!-- figure: 1.4 src="results/dft/summary.json#blocks.kv_stream.route.overhead.fmax" scale="100" name="kv_stream scan Fmax change %" -->% | +19.3 <!-- figure: 19.3 src="results/dft/summary.json#blocks.kv_stream.route.overhead.routed_wirelength" scale="100" name="kv_stream scan wirelength overhead %" -->% | not_met / pass |
| package controller `ot_rom_pkg_ctrl` | 3,444.39 → 3,919.07 | +13.8 <!-- figure: 13.8 src="results/dft/summary.json#blocks.pkg_ctrl.route.overhead.standard_cell_area" scale="100" name="pkg_ctrl scan area overhead %" -->% | 1,161.8 <!-- figure: 1161.8 src="results/dft/summary.json#blocks.pkg_ctrl.route.noscan.fmax_mhz" name="pkg_ctrl Fmax no scan" --> → 1,132.6 <!-- figure: 1132.6 src="results/dft/summary.json#blocks.pkg_ctrl.route.scan.fmax_mhz" name="pkg_ctrl Fmax scan" --> | -2.5 <!-- figure: -2.5 src="results/dft/summary.json#blocks.pkg_ctrl.route.overhead.fmax" scale="100" name="pkg_ctrl scan Fmax change %" -->% | +15.0 <!-- figure: 15.0 src="results/dft/summary.json#blocks.pkg_ctrl.route.overhead.routed_wirelength" scale="100" name="pkg_ctrl scan wirelength overhead %" -->% | pass / pass |
<!-- dft-tables:end -->

What the numbers say:

- **Coverage.** Test coverage is above 99.5 per cent on every block tested
  (first table), the level a production stuck-at target asks for. The gap between fault coverage and
  test coverage is almost entirely the untestable class, and most of it is
  structural:
  - the asynchronous set/reset pins, held inactive by the test constraint
    (half of them tie SETN high);
  - tie cells;
  - inputs that the functional logic never lets matter, which PODEM proves
    redundant.
  
  What is left untested is the aborted faults: well under half a per cent of
  each block's faults.
- **Patterns.** There is no test compression. Pattern counts are what plain
  full scan gives, and tester time is one load of the longest chain per
  pattern. A production flow would add EDT-style compression, which cuts
  tester time by the compression ratio. It does not change the coverage.
- **Area.** Swapping to SDFH/SDFL cells costs a quarter of each plain flop's
  area. Flops with asynchronous set/reset need an AO22 as well, and a third
  or more of the flops in these designs have one. The inserter's own count of
  added cell area (`cell_area_added_fraction` in each `scan_chains.json`) and
  the routed standard-cell area in the second table agree: about a seventh of
  the cell area of these register-heavy blocks.
- **Fmax.** The scan multiplexer sits in every D path. The functional clock
  moves only a few percent, because the critical paths of these pipelined
  blocks are not flop-to-flop without logic. A change that small is within
  the placer's run-to-run spread, so the sign can go either way: the KV
  streamer's scanned route came out slightly faster than its unscanned one.
- **Wirelength.** The chains are ordered by instance name, not by placement:
  OpenROAD in this image has no scan-chain reordering after placement. A
  placement-aware order would recover part of the wirelength cost.

## 5. Status for each architecture

The plan counts this workstream complete only when it covers all three
columns.

| | HBM comparator | Qwen3-8B ROM reticle | DeepSeek-V4.1 ROM array |
|---|---|---|---|
| Scan insertion in the physical flow | available for every block (`--dft scan`) | available | available |
| Blocks with ATPG coverage | stream unit, matrix engine, KV streamer | stream unit, matrix engine (the same decode core) | package controller, fabric router, package link; argmax, multicast, MoE-dispatch and expert-port collectives |
| Gate-level confirmation of patterns and faults | pending (Verilator builds queued behind the machine's memory gate) | pending | package controller; argmax, multicast, MoE-dispatch and expert-port collectives |
| Scan-off equivalence proven | KV streamer (stream unit, matrix engine pending) | pending | package controller, fabric router; argmax, multicast, MoE-dispatch and expert-port collectives |
| Paired scan / no-scan routes | pending (queued) | pending (queued) | package controller |
| JTAG TAP | `ot_tap`, verified by its bench; kept off internal scan (see below) | the same | the same; one TAP per die |
| Functional RTL campaigns with scan off | HDC decode, KV stream: pass | HDC decode: pass | V4.1 decode, package TP, ROM fabric: pass |

Functional campaigns: the scan chains exist only in the gate netlists, so the
functional RTL is unchanged. `results/dft/functional_campaigns.json` records
the campaigns re-run on this branch:

- `rtl_rom_fabric_campaign`
- `rtl_hdc_decode_campaign`
- `rtl_hdc_kv_stream_campaign`
- `rtl_hdc_v41_decode_campaign`
- `rtl_hdc_package_tp_campaign`

All five pass. The KV-stream campaign first failed in its timing-model
projection, on a field that was missing before main's `2aebf056`. It passed
once main was merged.

**Not yet covered.** These items are still running or queued. The machine is
shared and heavy jobs wait for a memory gate; results are appended to the
tables by `tools/dft/summarize.py --write-doc` as they land.

- The Sinkhorn unit. Its host synthesis timed out at 0.9 ns, so it is being
  re-synthesised at its 4 ns route target.
- The remaining paired routes: stream unit, matrix engine, KV streamer,
  fabric router, package link, collectives and Sinkhorn unit. The stream
  unit's unscanned baseline was killed by the machine running out of memory
  in detailed routing and has been requeued.

**The TAP is not scanned.** Scanning it runs into the one design rule the
ATPG model enforces: 45 of its cells capture on the falling edge of TCK from
cells that captured on the rising edge of the same pulse. A single-frame
capture model cannot grade that, and `atpg_model.py` now refuses such a
design rather than report wrong coverage. A first, unguarded run showed the
problem directly: 245 good-machine mismatches in the gate-level replay. The
TAP controls the test, and test-access logic is usually left off internal
scan and checked by its own functional and JTAG tests, which
`rtl/test/tb_ot_tap.sv` provides. Scan-off equivalence of the inserted TAP
netlist was proven anyway (195 points), so the inserter itself handles it.

**Out of scope for this pass:**

- The whole core and whole die as one scanned netlist. Blocks are scanned
  and graded one at a time; stitching block chains into top-level chains is
  the full-chip workstream's (section 6).
- The HBM weight streamers under `rtl/hdc/hbm/`, which were still being
  built when this ran.
- Memory arrays. The ROM banks and SRAM macros are black boxes to scan and
  belong to the memory-BIST workstream. The flop-mapped register files inside
  these blocks are scanned like any other flop.
- Transition (at-speed) faults. The flow grades stuck-at faults only. The
  launch-on-capture patterns an at-speed test needs are a next step for the
  same engine.

## 7. Reproducing

```
# one route pair
python3 tools/run_abi3_physical.py --view asap7 --top ot_rom_pkg_ctrl --source rtl/rom/ot_rom_pkg_ctrl.sv \
    --param ... --clock-period-ns 0.9 --false-path-io --slew-margin-percent 20 --stages pnr \
    --output noscan/physical.json
python3 tools/run_abi3_physical.py ... --dft scan --scan-max-length 1024 \
    --output scan/physical.json --keep-workdir scan/wd
# ATPG, chain test and gate-level confirmation on the scanned netlist
python3 tools/dft/run_atpg.py --netlist scan/wd/orfs/1_2_yosys.scan.v \
    --scan scan/wd/orfs/scan_chains.json --work atpg --output atpg.json
# scan off equals no scan
python3 tools/dft/check_scan_equivalence.py --prescan scan/wd/orfs/1_2_yosys.prescan.v \
    --scan-netlist scan/wd/orfs/1_2_yosys.scan.v --scan scan/wd/orfs/scan_chains.json \
    --work eq --output equivalence.json
```

Tests: `tests/test_dft_scan.py`, `tests/test_dft_tap.py` and
`tests/test_abi3_physical_dft.py`. They cover a toy netlist with every case the
inserter handles (both clock edges, two clock domains, asynchronous
set/reset, a logic-driven reset and a tie cell). The full ATPG flow on that
netlist is checked in both simulators, the equivalence proof is checked
together with its negative control, and the TAP bench runs in Verilator and
Icarus.

## 6. Interfaces for the memory-BIST and full-chip workstreams

**Scan ports of a hardened block.** Every block routed with `--dft scan` has
these ports:

| Port | Direction | Meaning |
|---|---|---|
| `scan_en` | in | 1 = shift, 0 = capture and functional |
| `scan_in[N-1:0]` | in | chain inputs |
| `scan_out[N-1:0]` | out | chain outputs, buffered |
| `test_mode` | in | only when a logic-driven asynchronous reset was found; 1 holds it inactive |

`scan_chains.json`, retained beside the route, gives N, the cells of each
chain in order, the per-cell output polarity and the test constraints. A
full-chip integrator can use it in two ways:

- concatenate block chains into top-level chains;
- route them to package scan pins, or to `ot_tap`'s `scan_in`/`scan_out` for
  TAP access.

The block's functional ports are unchanged, so a scanned block drops into its
functional parent as-is, with `scan_en` tied low if the parent is not yet
scanned. The equivalence proof in section 1 covers exactly that case.

**TAP hookup.** `ot_tap` (parameters: `IDCODE`, `NCHAINS`, `MBIST_CTRL_W`,
`MBIST_STATUS_W`, `STATUS_W`) connects on three sides:

- **Pins:** `tck`, `tms`, `tdi`, `trst_n`, `tdo`, `tdo_en`.
- **Scan side:** `scan_en`, `scan_in`, `scan_out`, `test_mode`,
  `scan_clk_sel` and `scan_clk_en`. The last two feed
  `ot_dft_scan_clock` (`func_clk`, `tck`, `rst_n` in; `core_clk` out), which
  drives the core clock tree.
- **Memory BIST side:**
  - `mbist_ctrl[MBIST_CTRL_W-1:0]`, updated on the falling TCK edge of
    Update-DR;
  - `mbist_ctrl_update`, one TCK cycle high after each update, which the BIST
    engine synchronises into its own clock;
  - `mbist_status[MBIST_STATUS_W-1:0]`, sampled at Capture-DR, which the BIST
    engine should hold stable (for example done/fail sticky bits and a
    signature) or synchronise into TCK.

The bit assignment inside `mbist_ctrl` and `mbist_status` (start, algorithm,
memory select, repair enable; done, fail, fail address, signature) belongs to
the BIST engines (`rtl/dft/ot_mbist*.sv`). The TAP only transports the words.
`dft_status[STATUS_W-1:0]` is a free read-only word for chip-level status.


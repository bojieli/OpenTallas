# Power and clock sign-off on ASAP7

Date: 2026-09-26. Workstream "Power and clock sign-off" of
`docs/TOKEN_PIPELINE_OPTIMIZATION_PLAN.md` section 6, for all three
architectures: the HBM comparator, the Qwen3-8B ROM reticle and the
DeepSeek-V4.1 ROM array (per die and per package).

Before this work the routed records under `results/physical_abi3/asap7/`
reported one thing about power and clocking: setup and hold at one corner
(TT, 0.70 V) and ORFS's vectorless `power_total_w`. This document adds, on
routed (or, for the full core, placed and clock-tree-synthesised) databases:

- power from the switching activity of the real decode campaigns, per block
  and per sub-hierarchy, with internal, switching and leakage parts;
- energy per decoded token of each architecture's reduced vehicle, and the
  energy per weight MAC, set against the analytical model's power terms;
- static IR drop and electromigration on the routed power grid;
- clock-tree latency, skew, size and power share;
- timing at the SS, TT and FF corners the ORFS image ships, with and without
  an on-chip-variation derate.

ASAP7 is a predictive academic PDK. No number here is a foundry number, and
none may be scaled to N6/N5/N7 (`docs/METHODOLOGY.md` section 9). The numbers
rank blocks, expose mechanisms and test the analytical model's assumptions
for internal consistency; they are not silicon predictions.

## How the analysis is done

Everything runs from `tools/signoff_analysis.py` on a route retained with
`tools/run_abi3_physical.py --keep-workdir` (the routed `6_final.odb`,
`6_final.spef`, `6_final.v` and `6_final.sdc`). The tool never changes a
routed record. Blocks were re-routed with their databases retained (the
records in the tree keep only the netlist and reports); each re-route's
Fmax is within a few MHz of the committed record.

The full reduced-Qwen core (0.85 M cells) did not finish routing: its
global-route timing repair ran eight hours on the shared machine, the flow
hit its 12-hour limit, and the detailed route that continued was stopped. It
is analysed at the post-clock-tree stage instead (`4_cts.odb`: placed, clock
tree built, power grid in place) with placement-estimated wire parasitics
(`estimate_parasitics -placement` with the platform's `setRC.tcl`). Every
result records its stage and parasitic source. The IR analysis does not
depend on the signal routes (the grid and the instance currents are the
same), the clock tree is final, and wire capacitance estimated from
placement typically differs from extraction by some tens of percent on the
switching part.

The plans are in `configs/signoff/`:

| Plan | Architecture | What it signs off |
|---|---|---|
| `qwen_core.json` | Qwen3-8B ROM reticle | the reduced-Qwen3 decode core (`ot_hdc_core`), its matrix engine and stream unit |
| `hbm_kv_stream.json` | HBM comparator | the KV streamer (`ot_hdc_kv_stream`) in front of HBM |
| `v41_core.json` | DeepSeek-V4.1 ROM array, per die | the V4.1 core's matrix engine and its routed units |
| `rom_fabric.json` | DeepSeek-V4.1 ROM array, per package | the collectives, package controller, fabric router and express link |
| `energy_per_token.json` | all three | energy per token from the results above and the analytical model's per-byte terms |

`tools/run_abi3_physical.py --nickname-tag` (new, default unchanged) lets a
sign-off re-route of a top run beside another route of the same top without
sharing the ORFS results namespace.

### Switching activity

The activity comes from the real decode campaigns: the same benches
(`rtl/test/tb_hdc_core.sv`, `tb_hdc_core_hbm.sv`, `tb_hdc_core_v41.sv`), the
same program images (`tools/hdc_program.py`, `tools/hdc_program_v41.py`) and
the same step (Qwen: position 15, 32,246 cycles; V4.1: position 7, token
3118, 1,088,551 cycles). Every run re-checks the campaign's own pass line
(token, every logit, vector memory and KV cache bit-exact), so the activity is
of a correct decode.

The VCD never reaches the disk. The simulator writes it into a FIFO that
`tools/signoff/vcd2saif` (C++) reads, keeping per bit the time at 0, at 1 and
the toggle count, and writing SAIF. A toggle is counted between timestamps
only, so the zero-delay glitches an event-driven simulator writes inside one
timestamp are not counted as switching. Long runs are sampled: the V4.1 step is
traced 1,000 cycles of every 10,000.

Two ways of mapping that activity onto a routed netlist were built:

* **Gate level.** The routed netlist is simulated inside the campaign bench.
  The ASAP7 platform's Verilog cell models are UDPs, which Verilator rejects,
  so `cell-models` writes zero-delay models of the used cells straight from
  the Liberty functions (asynchronous set/reset flops and clock gates
  included); `gl-bench` removes the bench's peeks into the DUT's RTL
  hierarchy. OpenSTA's `read_saif` annotates *pins*, so the net activity is
  expanded through the netlist onto every cell pin (`expand_saif_to_pins`):
  on the routed argmax collective 45,754 of 45,988 pins annotate. This works
  for blocks up to ~0.1 M cells. For the 0.85 M-cell core, Verilator emits
  about 1 GB of C++ that did not compile in hours on the shared machine, and
  Icarus simulates about 0.3 cycles per second; a 1,000-cycle window is the
  practical gate-level sample.
* **RTL-name matching** (what the full-length runs use). Yosys keeps each
  register's RTL path in its flop's instance name
  (`u_me.g_grp[1].g_lane[6].u_mul.s1_a[2]$_DFF_P_`), so the register toggles
  of the fast RTL simulation map one-to-one onto the routed flops' outputs
  (`map_rtl_saif_to_netlist`; the `genblk` scopes Verilator does not name are
  normalised, and an inverting `QN` output swaps T0 and T1). The ports are
  annotated too, and OpenSTA propagates activity through the combinational
  logic. Every one of the core's 150,844 flops matches (and every flop
  of each V4.1 unit).

The error of the second method was measured against the first on the same
stimulus: the routed argmax collective (14,355 cells), driven 1,800 cycles by
random logits and flags (`rtl/test/tb_signoff_argmax_random.sv`), simulated
gate-level and as RTL. Power at the routed SPEF, TT:

| Activity | Sequential mW | Combinational mW | Clock network mW | Total mW |
|---|---:|---:|---:|---:|
| gate level (45,754 of 45,988 pins annotated) | 4.36 | 2.63 | 2.88 | 9.87 |
| RTL registers mapped onto flops, OpenSTA propagation | 4.42 | 5.53 | 2.88 | 12.83 |

The register and clock parts agree to 1.4%; OpenSTA's probabilistic
propagation through the logic over-estimates the combinational part 2.1x
(it ignores the correlation between signals, and random operands are its
worst case). Every RTL-mapped total below is therefore an upper bound whose
combinational part may be up to about 2x high; the sequential and clock
parts, which dominate every block here, are not affected.

### Power, clock, corners, IR drop

One OpenROAD session per corner reads the corner's RVT Liberty, the routed
database and the routed SPEF, and reads the SAIF:

* **power**: OpenSTA's group totals (sequential, combinational, clock) and a
  per-instance sum by instance-name prefix (`u_me.` matrix engine, `u_su.`
  stream unit), split into internal, switching and leakage;
* **clock** (TT): setup and hold skew and insertion latency
  (`report_clock_skew`, `report_clock_latency`), clock-tree cells and their
  area, register clock pins, and the clock network's share of the power;
* **timing** at SS (0.63 V, 100 C), TT (0.70 V, 25 C) and FF (0.77 V, 0 C),
  the three corners the ORFS image ships, as setup/hold WNS and
  `report_clock_min_period`, and again under a flat 5% on-chip-variation
  derate (early 0.95, late 1.05). The SPEF is the typical extraction at every
  corner (ASAP7 ships one RC corner), so the corner spread is the cells';
* **IR drop and EM** (TT): PSM `analyze_power_grid` on VDD and VSS with the
  activity-annotated instance power, on the PDN the route itself built
  (ORFS `grid_strategy-M1-M2-M5-M6`: M1/M2 follow-pins 18 nm wide, M5 stripes
  120 nm on a 5.4 um pitch, M6 288 nm on 5.4 um), with two source models:
  *pins*, the block's M6 PDN pins held at the rail (a block inside an ideal
  parent grid), and *bumps*, a flip-chip array of alternating VDD/VSS bumps on
  a 140 um pitch landing directly on the block's top layer (no upper
  redistribution grid -- a pessimistic bound). Current density per stripe
  layer is reported against an assumed 1 mA/um DC limit, because ASAP7's
  technology LEF carries no electromigration rules.

## Results

The tables below are generated from the result JSONs by
`python3 tools/signoff_analysis.py report`; the JSONs are
`results/physical_abi3/asap7/signoff/{qwen_core,hbm_kv_stream,v41_core,rom_fabric}_signoff.json`
and `energy_per_token.json`.

<!-- signoff-tables:begin (generated by tools/signoff_analysis.py report; do not edit) -->

#### Power per block (activity-annotated, TT 0.70 V 25 C, at the routed 0.9 ns clock)

| Architecture | Block | Stage | Activity | Total mW | Internal | Switching | Leakage | Clock network | Clock share |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| qwen3-8b-rom-reticle | qwen_core | cts | RTL-mapped | 654.02 | 435.97 | 217.97 | 0.09 | 209.51 | 32% |
| | &nbsp;&nbsp;`u_me.*` (139,983 instances) | | | 175.01 | 150.92 | 24.06 | 0.02 | | |
| | &nbsp;&nbsp;`u_su.*` (73,096 instances) | | | 64.75 | 62.66 | 2.07 | 0.01 | | |
| hbm-comparator | hbm_kv_stream | final | RTL-mapped | 20.30 | 15.71 | 4.58 | 0.01 | 10.92 | 54% |
| | &nbsp;&nbsp;`u_*` (292 instances) | | | 0.12 | 0.11 | 0.00 | 0.00 | | |
| deepseek-v41-rom-array | v41_actquant | final | RTL-mapped | 32.89 | 26.58 | 6.31 | 0.01 | 16.21 | 49% |
| deepseek-v41-rom-array | v41_blockdot_lane0 | final | RTL-mapped | 6.24 | 4.80 | 1.43 | 0.00 | 3.04 | 49% |
| deepseek-v41-rom-array | v41_blockdot_lane15 | final | RTL-mapped | 6.24 | 4.80 | 1.43 | 0.00 | 3.04 | 49% |
| deepseek-v41-rom-array | v41_select | final | RTL-mapped | 5.15 | 4.15 | 1.00 | 0.00 | 2.65 | 52% |
| deepseek-v41-rom-array | rom_argmax_reduce_gate_level | final | gate-level | 9.87 | 6.92 | 2.95 | 0.00 | 2.88 | 29% |
| deepseek-v41-rom-array | rom_argmax_reduce_rtl_mapped | final | RTL-mapped | 12.83 | 8.54 | 4.29 | 0.00 | 2.88 | 22% |
| deepseek-v41-rom-array | rom_mcast_node | final | vectorless | 23.27 | 15.49 | 7.78 | 0.00 | 5.12 | 22% |
| deepseek-v41-rom-array | rom_moe_dispatch | final | vectorless | 11.04 | 7.61 | 3.43 | 0.00 | 2.76 | 25% |

#### Clock tree (TT)

| Block | Register clock pins | Tree cells | Tree cell area um2 | Insertion latency ns (min-max) | Setup skew ns | Hold skew ns |
|---|---:|---:|---:|---|---:|---:|
| qwen_core | 150,844 | 17,607 | 5,653.6 | 0.802-0.905 | 0.071 | -0.101 |
| hbm_kv_stream | 7,222 | 842 | 290.4 | 0.232-0.269 | 0.026 | -0.033 |
| v41_actquant | 13,233 | 1,338 | 443.1 | 0.191-0.224 | 0.026 | -0.033 |
| v41_blockdot_lane0 | 2,369 | 266 | 85.1 | 0.114-0.133 | 0.016 | -0.023 |
| v41_blockdot_lane15 | 2,369 | 266 | 85.1 | 0.114-0.133 | 0.016 | -0.023 |
| v41_select | 2,006 | 228 | 71.9 | 0.112-0.134 | 0.018 | -0.023 |
| rom_argmax_reduce_gate_level | 2,266 | 245 | 78.6 | 0.108-0.127 | 0.016 | -0.020 |
| rom_argmax_reduce_rtl_mapped | 2,266 | 245 | 78.6 | 0.108-0.127 | 0.016 | -0.020 |
| rom_mcast_node | 4,216 | 445 | 132.0 | 0.122-0.148 | 0.019 | -0.026 |
| rom_moe_dispatch | 2,155 | 233 | 72.7 | 0.105-0.123 | 0.011 | -0.018 |

#### Fmax per corner (reg-to-reg `report_clock_min_period`; OCV = flat 5% early/late derate)

| Block | SS 0.63 V 100 C | SS + OCV | TT 0.70 V 25 C | TT + OCV | FF 0.77 V 0 C | FF + OCV | Hold WNS ns (SS / TT / FF) |
|---|---:|---:|---:|---:|---:|---:|---|
| qwen_core | 688 | 640 | 1,051 | 954 | 1,374 | 1,243 | +0.014 / +0.000 / -0.012 |
| hbm_kv_stream | 740 | 698 | 1,128 | 1,062 | 1,569 | 1,475 | +0.051 / +0.030 / +0.014 |
| v41_actquant | 741 | 696 | 1,126 | 1,055 | 1,546 | 1,447 | +0.035 / +0.020 / +0.008 |
| v41_blockdot_lane0 | 789 | 749 | 1,196 | 1,135 | 1,643 | 1,555 | +0.041 / +0.026 / +0.015 |
| v41_select | 1,019 | 959 | 1,526 | 1,435 | 2,104 | 1,976 | +0.033 / +0.009 / -0.004 |
| rom_argmax_reduce_gate_level | 770 | 729 | 1,151 | 1,085 | 1,579 | 1,488 | +0.047 / +0.031 / +0.019 |
| rom_mcast_node | 900 | 847 | 1,359 | 1,278 | 1,895 | 1,781 | +0.077 / +0.052 / +0.036 |
| rom_moe_dispatch | 933 | 881 | 1,408 | 1,327 | 1,943 | 1,829 | +0.074 / +0.050 / +0.034 |

#### Static IR drop and EM (TT, activity-annotated instance power)

| Block | Die um | Source model | VDD worst mV | VDD average mV | VSS worst mV | Max M2 mA/um | Max M5 mA/um | Max M6 mA/um |
|---|---|---|---:|---:|---:|---:|---:|---:|
| qwen_core | -- | pins | 3.0 | 0.22 | 3.3 | 1.98 | 1.02 | 0.00 |
| qwen_core | -- | bumps | 224.0 | 101.00 | 217.0 | 6.66 | 23.17 | 17.85 |
| hbm_kv_stream | -- | pins | 2.1 | 0.11 | 2.2 | 1.81 | 0.37 | 0.00 |
| v41_actquant | -- | pins | 3.0 | 0.33 | 2.5 | 1.73 | 0.75 | 0.00 |
| v41_blockdot_lane0 | -- | pins | 1.7 | 0.18 | 1.7 | 1.19 | 0.50 | 0.00 |
| v41_select | -- | pins | 2.0 | 0.24 | 1.8 | 1.45 | 0.41 | 0.00 |
| rom_argmax_reduce_gate_level | -- | pins | 2.4 | 0.45 | 2.4 | 1.47 | 1.06 | 0.00 |
| rom_argmax_reduce_gate_level | -- | bumps | 9.8 | 2.19 | 5.9 | 1.59 | 2.66 | 1.01 |
| rom_mcast_node | -- | pins | 2.8 | 0.66 | 2.6 | 1.70 | 1.30 | 0.00 |
| rom_mcast_node | -- | bumps | 29.9 | 11.20 | 29.1 | 1.94 | 6.68 | 4.09 |
| rom_moe_dispatch | -- | pins | 1.9 | 0.58 | 1.9 | 1.21 | 0.64 | 0.00 |
| rom_moe_dispatch | -- | bumps | 3.6 | 0.93 | 4.9 | 1.19 | 1.42 | 1.01 |

#### Energy per decode step of the reduced vehicles (TT)

| Architecture | Step cycles | Logic uJ | Memory and links uJ | Static uJ | Token uJ | pJ per weight MAC (matrix engine / whole step) | Not included |
|---|---:|---:|---:|---:|---:|---|---|
| deepseek_v41_rom_array_die | 1,088,551 | 135.08 | 139.75 | 0.00 | 274.83 | -- | sequencer, V4.1 stream unit (ot_hdc_v41_stream), hc projection (ot_hdc_v41_hcproj) and Sinkhorn unit: no retained route (being routed by the full-chip workstream); their energy is not in the logic total; matrix_engine (u_me): block v41_matvec not in results/physical_abi3/asap7/signoff/v41_core_signoff.json; FP4 quantise-dequantise: block v41_fp4qdq not in results/physical_abi3/asap7/signoff/v41_core_signoff.json; Engram hash: block v41_engram_hash not in results/physical_abi3/asap7/signoff/v41_core_signoff.json; softplus / sqrt: block v41_softplus not in results/physical_abi3/asap7/signoff/v41_core_signoff.json |
| hbm_comparator | 32,275 | 19.57 | 305.61 | 10.17 | 335.35 | 14.85 / 262.41 | -- |
| qwen3_8b_rom_reticle | 32,246 | 18.98 | 2.17 | 0.00 | 21.15 | 3.97 / 16.55 | -- |

<!-- signoff-tables:end -->

@@FINDINGS@@

## Reproduce

```bash
export OT_SIGNOFF_SCRATCH=/scratch/signoff   # simulations, SAIFs, sessions (large; not committed)
export OT_SIGNOFF_ROUTES=/scratch/routes     # the kept route workdirs: core/, blocks/<name>/
# optional on a shared machine: an admission gate in front of the heavy OpenROAD sessions
export OT_SIGNOFF_GATE=/path/to/gate.sh

# routes, with the routed database retained (one per block; see each plan for the exact argv)
python3 tools/run_abi3_physical.py --view asap7 --top ot_hdc_core ... --stages synth,pnr \
    --nickname-tag signoff --keep-workdir $OT_SIGNOFF_ROUTES/core/wd --output $OT_SIGNOFF_ROUTES/core/physical.json

# activity, analysis, summary, tables
python3 tools/signoff_analysis.py plan configs/signoff/qwen_core.json
python3 tools/signoff_analysis.py plan configs/signoff/hbm_kv_stream.json
python3 tools/signoff_analysis.py plan configs/signoff/v41_core.json
python3 tools/signoff_analysis.py plan configs/signoff/rom_fabric.json
python3 tools/signoff_analysis.py summary
python3 tools/signoff_analysis.py report
```

A plan can be run with `--activity-only` before its routes exist; a later
run reuses the simulation and only maps and analyses. Tests:
`tests/test_signoff_analysis.py`.

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
| deepseek-v41-rom-array | v41_engram_hash | final | RTL-mapped | 79.89 | 67.44 | 12.43 | 0.02 | 53.16 | 67% |
| deepseek-v41-rom-array | v41_fp4qdq | final | RTL-mapped | 18.84 | 15.17 | 3.67 | 0.01 | 9.24 | 49% |
| deepseek-v41-rom-array | v41_matvec (`u_me.*` of ot_hdc_core, 139,983 instances) | cts | RTL-mapped | 120.62 | 112.99 | 7.61 | 0.02 | | |
| deepseek-v41-rom-array | v41_select | final | RTL-mapped | 5.15 | 4.15 | 1.00 | 0.00 | 2.65 | 52% |
| deepseek-v41-rom-array | v41_softplus | final | RTL-mapped | 197.28 | 135.67 | 61.59 | 0.02 | 71.23 | 36% |
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
| v41_engram_hash | 20,100 | 3,695 | 1,610.4 | 0.268-0.293 | 0.019 | -0.027 |
| v41_fp4qdq | 7,559 | 771 | 253.0 | 0.160-0.190 | 0.026 | -0.031 |
| v41_select | 2,006 | 228 | 71.9 | 0.112-0.134 | 0.018 | -0.023 |
| v41_softplus | 34,779 | 6,860 | 2,402.6 | 0.306-0.353 | 0.038 | -0.045 |
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
| v41_engram_hash | 1,016 | 953 | 1,524 | 1,427 | 2,054 | 1,898 | +0.048 / +0.030 / -0.004 |
| v41_fp4qdq | 747 | 704 | 1,121 | 1,062 | 1,506 | 1,418 | +0.040 / +0.022 / +0.009 |
| v41_select | 1,019 | 959 | 1,526 | 1,435 | 2,104 | 1,976 | +0.033 / +0.009 / -0.004 |
| v41_softplus | 678 | 641 | 1,034 | 976 | 1,438 | 1,354 | +0.028 / +0.011 / -0.009 |
| rom_argmax_reduce_gate_level | 770 | 729 | 1,151 | 1,085 | 1,579 | 1,488 | +0.047 / +0.031 / +0.019 |
| rom_mcast_node | 900 | 847 | 1,359 | 1,278 | 1,895 | 1,781 | +0.077 / +0.052 / +0.036 |
| rom_moe_dispatch | 933 | 881 | 1,408 | 1,327 | 1,943 | 1,829 | +0.074 / +0.050 / +0.034 |

#### Static IR drop and EM (TT, activity-annotated instance power)

| Block | Die um | Source model | VDD worst mV | VDD average mV | VSS worst mV | Max M2 mA/um | Max M5 mA/um | Max M6 mA/um |
|---|---|---|---:|---:|---:|---:|---:|---:|
| qwen_core | -- | pins | 3.0 | 0.22 | 3.3 | 1.98 | 1.02 | 0.00 |
| qwen_core | -- | bumps | 224.0 | 101.00 | 217.0 | 6.66 | 23.17 | 17.85 |
| hbm_kv_stream | 198 x 198 | pins | 2.1 | 0.11 | 2.2 | 1.81 | 0.37 | 0.00 |
| v41_actquant | -- | pins | 3.0 | 0.33 | 2.5 | 1.73 | 0.75 | 0.00 |
| v41_blockdot_lane0 | -- | pins | 1.7 | 0.18 | 1.7 | 1.19 | 0.50 | 0.00 |
| v41_engram_hash | 207 x 207 | pins | 2.3 | 0.41 | 2.1 | 1.59 | 0.70 | 0.00 |
| v41_fp4qdq | 124 x 124 | pins | 2.4 | 0.27 | 2.6 | 2.03 | 0.73 | 0.00 |
| v41_select | -- | pins | 2.0 | 0.24 | 1.8 | 1.45 | 0.41 | 0.00 |
| v41_softplus | 272 x 272 | pins | 6.5 | 0.57 | 6.3 | 3.75 | 2.73 | 0.00 |
| rom_argmax_reduce_gate_level | 74 x 74 | pins | 2.4 | 0.45 | 2.4 | 1.47 | 1.06 | 0.00 |
| rom_argmax_reduce_gate_level | 74 x 74 | bumps | 9.8 | 2.19 | 5.9 | 1.59 | 2.66 | 1.01 |
| rom_mcast_node | 91 x 91 | pins | 2.8 | 0.66 | 2.6 | 1.70 | 1.30 | 0.00 |
| rom_mcast_node | 91 x 91 | bumps | 29.9 | 11.20 | 29.1 | 1.94 | 6.68 | 4.09 |
| rom_moe_dispatch | 66 x 66 | pins | 1.9 | 0.58 | 1.9 | 1.21 | 0.64 | 0.00 |
| rom_moe_dispatch | 66 x 66 | bumps | 3.6 | 0.93 | 4.9 | 1.19 | 1.42 | 1.01 |

#### Energy per decode step of the reduced vehicles (TT)

| Architecture | Step cycles | Logic uJ | Memory and links uJ | Static uJ | Token uJ | pJ per weight MAC (matrix engine / whole step) | Not included |
|---|---:|---:|---:|---:|---:|---|---|
| deepseek_v41_rom_array_die | 1,088,551 | 543.26 | 139.75 | 0.00 | 683.01 | 11.51 / 66.54 | sequencer, V4.1 stream unit (ot_hdc_v41_stream), hc projection (ot_hdc_v41_hcproj) and Sinkhorn unit: no retained route (being routed by the full-chip workstream); their energy is not in the logic total |
| deepseek_v41_rom_array_package | 1,088,551 | 726.30 | 5.70 | 0.00 | 732.00 | -- | four-die tensor group (one die-step equivalent): sequencer, V4.1 stream unit (ot_hdc_v41_stream), hc projection (ot_hdc_v41_hcproj) and Sinkhorn unit: no retained route (being routed by the full-chip workstream); their energy is not in the logic total; package controller: block rom_pkg_ctrl not in results/physical_abi3/asap7/signoff/rom_fabric_signoff.json; fabric router: block rom_fabric_router not in results/physical_abi3/asap7/signoff/rom_fabric_signoff.json; MoE expert port: block rom_moe_expert_port not in results/physical_abi3/asap7/signoff/rom_fabric_signoff.json; express link: block rom_express_link not in results/physical_abi3/asap7/signoff/rom_fabric_signoff.json |
| hbm_comparator | 32,275 | 19.57 | 305.61 | 10.17 | 335.35 | 3.97 / 262.41 | -- |
| qwen3_8b_rom_reticle | 32,246 | 18.98 | 2.17 | 0.00 | 21.15 | 3.97 / 16.55 | -- |

<!-- signoff-tables:end -->

## What the results say

### Qwen3-8B ROM reticle: the reduced decode core

The core (0.85 M cells at the post-CTS stage, 0.9 ns clock) draws 654 mW at
TT over a decode step. The matrix engine (`u_me`) is 175 mW and the stream
unit (`u_su`) 65 mW; the remaining 414 mW is the sequencer, the core-level
operand and result registers and, above all, the clock tree. By OpenSTA's
grouping the clock network is 210 mW (32%), the registers 240 mW and the
combinational logic 204 mW. Leakage is 0.09 mW: ASAP7's RVT library at
25 C leaks almost nothing, so every number here is dynamic.

One step is 32,246 cycles, 29.0 us at the routed clock. It costs 19.0 uJ of
core logic plus 2.2 uJ of memory reads (2.64 MB of weight ROM at the
analytical model's 0.08 pJ/B; 0.26 MB of KV and 0.49 MB of vector memory
SRAM traffic at 2.6 pJ/B): 21.2 uJ per token. The matrix engine spends
3.97 pJ per weight MAC (1,277,952 BF16 MACs per step); the whole step is
16.5 pJ per MAC.

Timing gives 688 MHz at SS (640 MHz under the 5% OCV derate), 1,051 MHz at
TT (954) and 1,374 MHz at FF (1,243). Hold closes at SS and TT but fails at
FF by 12 ps, and under the OCV derate by 52-56 ps at every corner: ORFS
repairs hold at the one corner it routes at, with no derate.

The clock tree drives 150,844 register clock pins through 17,607 buffers
and inverters (5,654 um2). Insertion latency is 0.80-0.90 ns, about one
clock period, with 71 ps of setup skew and 101 ps of hold skew.

Fed at its own M6 pins, the route's grid drops at worst 3.0 mV on VDD and
3.3 mV on VSS (under 0.5%). Fed from a 140 um flip-chip bump array landing
directly on M6, it drops 224 mV (32% of the supply) and the M5 stripes carry
23 mA/um. The ORFS block grid has no layer that can spread bump current, so
a die built from these blocks needs an upper grid; the M7/M8 variant below
sizes one.

### HBM comparator

The KV streamer (`ot_hdc_kv_stream`, 55,125 cells, 1,128 MHz at TT) draws
20.3 mW, 54% of it in the clock network: it idles through most of the step
and is never clock-gated. Its logic is 0.6 uJ per step and the core is the
Qwen core above (19.0 uJ). The HBM path dominates. The 2.64 MB of weights
per step cost 277 uJ at the measured 104.9 pJ/B, the KV bytes 27.6 uJ, and
the stack's idle interface power (1/8 of 2.8 W for 4 of 32 pseudo-channels)
10.2 uJ. A step is 335 uJ, 15.9 times the ROM reticle's 21.2 uJ; 88% of the
difference is moving the weights.

### DeepSeek-V4.1 ROM array, per die

The V4.1 step is 1,088,551 cycles (0.98 ms). With their register activity
mapped from the campaign, the routed V4.1 units draw 32.9 mW (activation
quantiser), 6.2 mW per block-dot lane (16 lanes) and 5.2 mW (top-16
select), about half of each in the clock network. These units are busy for
a few percent of the step (the QE, which holds the quantiser and the
block-dot lanes, is busy 73,098 of 1,088,551 cycles), so their energy is
almost all idle clocking: the 16 block-dot lanes alone spend 98 uJ per
step. The memories move 46.9 MB of ROM (3.8 uJ) and 52.3 MB of SRAM traffic
(136 uJ, of which 32 MB is KV reads) per step.

### DeepSeek-V4.1 ROM array, per package

The routed fabric blocks, vectorless, draw 10-25 mW each and close at
1.15-1.41 GHz at TT and 0.77-0.93 GHz at SS. A package step is a four-die
tensor group (about one die-step of energy), the fabric logic over the
step, and 2.46 MB of UCIe all-reduce traffic at 0.29 pJ/b (5.7 uJ, derived
under the Qwen package campaign's split rule, not simulated for V4.1).

### Against the analytical model

| Term | Analytical (`configs/hardware/technology.json`) | Measured here (ASAP7, TT) | Ratio |
|---|---|---|---|
| MAC energy, BF16 | 0.33 pJ (0.13-0.70) | 3.97 pJ per MAC in the matrix engine; 16.5 pJ per MAC for the whole Qwen step | 12x; 50x |
| Clock energy | 8.5e-11 J/mm2/cycle (3e-11-1.6e-10) | `analytical_comparison` in `energy_per_token.json`, clock network alone and with the registers' clock pins | see the JSON |
| Logic leakage | 0.06 W/mm2 (0.011-0.2) | 0.2 mW/mm2 (Qwen core, RVT, 25 C) | ~300x lower |
| ROM read | 0.08 pJ/B | not measured (no ROM macro in the routed blocks) | -- |

The MAC disagreement is the one that matters. The analytical 0.33 pJ is a
datapath-only figure. The matrix engine pays a pipelined BF16 multiplier, an
FP32 adder and about 1,500 flip-flops per lane (95,995 in 64 lanes), all
clocked every cycle whether or not a lane has work, plus the reduction tree
behind them. Over the whole step, the core's clock tree and sequencer, which
the analytical term never sees, bring it to 16.5 pJ. ASAP7 is a predictive
library, so the ratio rather than the absolute pJ is the finding: for this
microarchitecture the analytical model's logic energy per token is
optimistic by about an order of magnitude, and its clock term (a whole-die
budget taken from GPU TDPs) does not stand in for the clock tree a core with
150,000 always-clocked flops actually builds. Leakage runs the other way:
the analytical term is a foundry-class assumption at operating temperature,
ASAP7 RVT at 25 C is not a foundry library, and neither number should move
the other.

### Recommendations

1. **Clock gating.** No block has an integrated clock gate. The clock
   network is 22-54% of every block's power, and the registers' own clock
   pins are most of the rest of the sequential power. The V4.1 units are
   idle for over 90% of a step; gating the QE, XU and HE by their busy
   signals, and the matrix-engine lanes by lane validity, would remove most
   of the V4.1 die's logic energy and a large part of the Qwen core's.
2. **Hold at every corner.** Hold fails at FF (12 ps on the core, 4 ps on the
   top-16 select) and under a 5% OCV derate by about 55 ps. ORFS's hold
   repair needs an FF scenario and a derated one, or a budgeted margin.
3. **Upper power grid.** The M1/M2/M5/M6 block grid holds 3 mV fed at its
   pins but 224 mV fed from bumps. A die needs M7/M8 straps (and a
   redistribution layer to the bumps).
4. **Follow-pin current density.** Even fed ideally at the M6 pins, the
   18 nm M1/M2 follow-pins carry 1.2-2.4 mA/um near the densest flop
   clusters, above the assumed 1 mA/um. ASAP7 has no EM rule to check
   against; a foundry flow would need wider rails or M3 straps over the
   matrix engine's register columns.
5. **Clock latency.** A 0.8-0.9 ns insertion delay on a 0.64 mm core is one
   clock period. A full die's tree will be longer, so the full-chip
   workstream should plan a mesh or H-tree top level and carry the skew in
   the block timing budgets.

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

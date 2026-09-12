# The control path: measured, found binding, and fixed

A datapath is not a chip. A transformer decode step is hundreds of kernel
launches per token, and every one has to be fetched, decoded, have its operand
views resolved and be issued before an array can run it. `docs/DATAPATH_PIPELINE_REDESIGN.md`
covers the arithmetic; this covers the half that turned out to be binding.

## What was measured

Both sides come from artifacts, not estimates.

| side | block | evidence | figure |
|---|---|---|---|
| control | `ot_a3_microsequencer` | `results/physical_abi3/asap7/a3_microsequencer/pnr.json` | **265 MHz**, 416,715 cells, 136,926 µm² |
| control | same, frontend only | `.../pnr_frontend_only.json` | 548 MHz, 66,100 cells, 21,765 µm² |
| control | instruction cost | `results/rtl/abi3_g1e_control_end_to_end.json` | **116.4 cycles/command**, 691 commands/forward pass |
| datapath | `ot_compute_unit` | `results/physical_abi3/asap7/compute_unit/pnr.json` | **1,290 MHz** |
| datapath | one K=256 pass | `rtl/test/tb_kernel_dispatch_throughput.sv` | **270 cycles** |

The instruction cost is not a synthetic benchmark. G1e runs the shipped Qwen3
program through the real control plane in RTL and checks every engine issue,
every resolved operand view and every per-pass counter against an independent
Python golden model that reads no RTL. It passes. 241,290 simulated cycles
retired 2,073 engine commands.

## The finding

One descriptor costs the control plane 439 ns and earns the array 209 ns of work.

* the control plane is **2.1× too slow for one compute unit**
* at 16 units it is **34× short**; at the 512-unit wafer, **1,075× short**
* it is also **4.3× larger in area** than the compute unit it drives

A 1,290 MHz datapath behind this is a 265 MHz chip with a mostly idle array. Every
frequency gain in the arithmetic is thrown away at the issue port.

## Why neither obvious fix works alone

**Fan-out alone.** Broadcasting one descriptor to every unit removes the factor of
`UNITS` but not the 2.1× per-unit deficit. Measured on 16 real compute units:
**48.5%** array utilisation.

**Coarsening alone.** A descriptor covering several weight-SRAM passes keeps one
unit busy, and leaves the rest of the array starved by the factor of `UNITS`.

**A deeper queue never helps.** A queue absorbs bursts. It cannot absorb a rate
deficit, at any depth.

## The design: `ot_cluster_dispatcher`

One descriptor is expanded **in hardware** across `UNITS` compute units and
`PASSES` weight-SRAM passes, so the sequencer's rate is divided by `UNITS` and
multiplied by `PASSES`. Completion is a scoreboard mask rather than a watch on one
unit, so it stays correct once units stop finishing in lockstep — which they do as
soon as their memory paths differ.

This is not novel. It is the GigaThread-engine-to-SM hierarchy in a GPU, the
descriptor ring in a DPU, and the single instruction stream driving a whole MXU in
a TPU. In none of them does a sequencer issue one command per arithmetic unit.

### Measured, on 16 real compute units with their real SRAM macros

Control modelled at exactly its measured rate — one descriptor every 567 datapath
cycles:

| passes/descriptor | array utilisation | starved |
|---:|---:|---:|
| 1 | 48.5% | 51.0% |
| 2 | 95.4% | 3.8% |
| **3** | **99.1%** | **0.0%** |
| 4 | 99.2% | 0.0% |
| 8 | 99.2% | 0.0% |

With control infinitely fast and one pass per descriptor: 98.9%. That is the
dispatcher's own ceiling, so at three passes the control plane has stopped being
visible.

`tools/audit_control_path_throughput.py` predicted 47.6% and ~100% before the RTL
ran; the RTL returned 48.5% and 99.1%.

### The cost of the fix

`results/physical_abi3/asap7/cluster_dispatcher/pnr.json`: **1,290 MHz in 828 µm²
and 2,734 cells** — 2.6% of a compute unit's area. It matches the datapath's clock,
so it is not a new bottleneck.

## The design rule

> A descriptor must cover at least as many datapath cycles of work per unit as the
> control plane takes to produce it, **and** it must be expanded in hardware across
> the array.

At these clocks that is 567 cycles, so ≥ 3 K=256 passes.

## Every model on every accelerator

`tools/audit_control_path_throughput.py` prices both sides per token for four
models (Qwen3-8B, DeepSeek-V4-Flash-0731, DeepSeek-V4-Pro-0813, Kimi-K3) against
seven capability configs — 28 combinations.

**Control is not the bottleneck in any of the 28, minimum headroom 2.4×** — given
descriptor fan-out across every compute unit.

The tightest case is the most informative: Qwen3-8B on the 512-unit wafer leaves
each command covering 1,337 datapath cycles against the 567 a command costs.
Headroom shrinks as the array widens and as the model shrinks, because the array
finishes a command sooner. **The binding case is a small model on a big machine**,
not a big model anywhere.

### What that number does not cover

Recorded as refusals in the tool, not as prose caveats:

* 691 commands per pass is **one model's** measurement, extrapolated by layer count
  to the other three.
* the arithmetic is **compute-bound**: no weight traffic, no attention over the KV
  cache, no interconnect. At batch 1 a real step is usually memory-bound, so the
  datapath times are lower bounds — and the control headroom is a lower bound with
  them.
* only the **tensor** engine's descriptors are counted, so the required control
  rate is a lower bound too.
* the decoupled tokens/s column is valid **only because** the dispatcher puts a
  queue between two clock domains. The serialised column is what a design without
  it gets, and it is worse in every row.

## Resolved: the 98% padding figure is not a cost

`results/abi3/cycle_characterization_feedback.json` reports, for one Qwen3-8B
decode transaction on the single-chip capability:

* `tiling.padding_fraction` **0.981668** — issued tile work is 54.5× the useful work
* `tensor.busy_cycles` is **99.1%** of `total_cycles`
* the dominant tensor SCHEDULE shape in the built deployment is **512 rows × 4096
  columns**

That looks like a 54.5× waste sitting on top of everything else, and larger than
the 20.2× the machine clock just gained. **It is not.** For the tensor family the
charge in `runtime/cycle/model.py` `_compute_cycles` is

```python
cycles = mapping.tensor_lanes.output_waves * depth_cycles
```

with the reason stated in the code: *"Masked lanes do no work and cannot accelerate
a live lane, so a wave's time depends on active K depth, not on a padded row
rectangle or on the number of tail lanes."* `tensor_lane_mapping` additionally
asserts `active_lane_slots == rows * cols`, so the wave count covers the real
output surface exactly and pads nothing.

So `padding_fraction` is a **reported statistic about tile geometry, not a charged
cost**, for the tensor family — which is also what
`tools/audit_c2_padding_cost_attribution.py` concluded from the other direction.

This is recorded because getting there took three readings and the first two were
wrong. A numerical coincidence made the wrong answer look confirmed:
`tensor.busy_cycles × lanes` comes within 0.14% of `issued_tile_work`, which is
exactly what one would expect if the padded rectangle *were* being charged. It is
a coincidence. An arithmetic near-match is not a mechanism, and the only thing that
settled it was reading the branch that computes the number.

### What that leaves open

Tensor throughput in the model is still far below the array's peak: 1.5×10¹⁰ useful
operations in 1.74×10⁹ cycles on 256 lanes is about 3.4% of peak. Padding is now
ruled out as the cause, so the remaining candidates are the `work_per_lane_cycle`
characterization, the depth-tile charge, and `issue_window`. That is a separate
investigation and it is not attributed here.

Note separately that the redesigned `ot_compute_unit` is output-stationary — lanes
hold output columns and the single activation column is broadcast — so a batch-1
decode step maps onto it with no row dimension to pad in the hardware either.

## Cross-references

* `docs/DATAPATH_PIPELINE_REDESIGN.md` — the arithmetic side
* `rtl/proto/ot_cluster_dispatcher.sv` — the design, with its reasoning in the header
* `rtl/test/tb_cluster_dispatch_throughput.sv` — the 16-unit measurement
* `rtl/test/tb_kernel_dispatch_throughput.sv` — the single-unit overhead measurement
* `tools/audit_control_path_throughput.py` — the 28-combination audit

# Compute sharing and performance recovery

Status: proposed implementation direction, 2026-09-28. This plan does not replace
the adopted architecture or promote any rate. TASKS.md owns execution status.

## Objective

Maximize measured single-user decode performance within an explicit die/package
count, area, memory capacity, power/cooling and arithmetic contract. Token rate is
an output. Optimize AR first; evaluate MTP/DFlash separately with measured accepted
tokens, full producer work and commit costs. Report 200K and 1M V4.1 contexts
separately, and the agreed Qwen context. Multi-user saturation is a separate result.
If a candidate improves one operating point and hurts another, retain a Pareto
comparison rather than averaging away the regression.

## Proposed sharing boundary

A cluster owns nearby ROM banks, distributed banked activation/accumulator storage,
small queues, a local scheduler, matrix tiles, and connections to vector/SFU
pipelines. Matrix tiles are reused across compatible matrices and experts.
Cluster-to-cluster transfers use bounded registered links with explicit credits.
No cluster size, global pooling claim or broadcast fanout is adopted before exact
execution, port accounting and physical characterization.

The candidate arithmetic pools are:

- Quantized block-dot tiles for compatible FP4/FP8 weight matvecs and index scoring.
- BF16-compatible tiles for weight projections and attention dots/value reductions.
- Dedicated pipelined vector/SFU/reduction/quantization/select circuits, preserving
  the required rounding and reduction order. HCP pooling versus separate hardware
  remains a measured choice because its arithmetic and latency requirements differ.

The adopted model already proposes weight/index and BF16/attention pooling in
tools/arch_utilization_v41.py: unified(), area_of() and pool_conflicts(). It charges
an assumed 10% area for operand selection. This proposal makes that physical
boundary and its schedule explicit; it does not treat the 10% as measured evidence.

GPU-derived principles are distributed registers and scratchpads, tiled reuse,
separate operand-transfer and compute queues, dependency tracking, and local
scheduling. ROM bank placement and read ports constrain which matrices a cluster
can serve. Whole-die fully flexible weight routing is not assumed. Independent
work of the same token, routed experts and verified speculative positions can
overlap only when they fit the same finite resource schedule.

## Required executable contract

One manifest must bind checkpoint tensor ranges, expert IDs, scales/constants,
ROM word/sector units, cluster and die ownership, ISA geometry, accumulator order,
SRAM ports/capacity, queue depths, link widths and HBM channel ownership. Generate
the program, image map and schedule from it. Every tensor fragment and transfer
must have a concrete owner; fractional layer bytes alone are insufficient.

Include RoPE, Engram data, activation stores, metadata, masks, scales, double
buffers and speculation state in the capacity ledger. Account for physical macro
depth waste and routing whitespace. ROM/HBM comparison uses the same compute
contract with an explicit list of every tensor supplied by each memory.

## Experiments and acceptance

1. Preserve and merge completed exact operator and local route records. Finish
   already-running high-value gates; prevent duplicate experiments.
2. Build a finite-resource schedule for the mapped full-shape layer, then token:
   reserve MAC tiles, all VM/SRAM ports, HBM service, queues and link bandwidth.
   Charge loads, conversion, fill/drain, spills, stalls and metadata. A dependency
   graph plus separate bandwidth ceilings is not sufficient for this gate.
3. Evaluate a bounded family of clusters using the existing exact tiles. Sweep
   sharing/fanout, SRAM banks, read width, queue depth and local MAC count. Select
   physical candidates using end-to-end latency improvement per area/power, then
   calibrate that prediction from RTL and route. Do not scale isolated cell area
   without the interconnect and storage it requires.
4. Execute checkpoint-backed layer-0 and index-heavy layer cases with dense,
   routed-expert, attention and HCP paths. Include adverse expert placement,
   multi-descriptor reuse, realistic KV/index contents and simultaneous HBM
   weight/KV/index service. Narrow full-shape arithmetic gates remain references;
   performance needs the selected width and schedule.
5. Route a complete cluster with actual operand/control widths and characterized
   memory views. Compose clusters through characterized interfaces. Zero-arc macro
   views and global-route estimates are geometry evidence only.
6. Derive token latency from the exact mapped schedule and achieved frequency;
   reprice area/power and compare matched ROM/HBM, AR and speculation. If the
   physical result misses its predicted service budget, revise the mapping or
   report the lower performance before increasing scale.

## Metrics

For each engine and operating point record useful arithmetic, issued arithmetic
(including padding/replay), active cycles and each stall reason. Report useful
utilization against the implemented arithmetic-mode peak both while the cluster
is scheduled and over the entire token; whole-system utilization includes idle
pipeline stages. Speculative work is reported separately from accepted output.

For ROM, activation SRAM, HBM and links record physical bytes, useful bytes,
capacity and measured sustained service, with per-bank/port conflicts. High
bandwidth occupancy caused by unnecessary traffic is not an optimization success.
Use these measurements to maximize useful single-user rate, not to enforce an
arbitrary MFU/MBU percentage. Dependencies and fixed weight placement impose idle
time even when local dataflow is efficient.

## Ownership and immediate dependencies

| Workstream | Owner | Next artifact |
| --- | --- | --- |
| Integration, immutable contract, candidate selection | root | Integrated source snapshot; complete capacity and resource ledger |
| Full-shape placement and arithmetic | fullshape emitter/core/golden owners | Exact tensor/expert ownership, fully bound layer and token program |
| Finite-resource schedule and counters | model_reprice with root | Full schedule including pools, ports, shared HBM, speculative work |
| ROM-to-pool data path | weight-layout and HBM-comparator owners | Packed input conversion, bank-to-tile mapping, matched memory sources |
| Shared activation storage and multicast | me_he_macro_pipeline, vm_bank_physical | Cluster-local bank/read/convert/broadcast gate and routed cost |
| Collectives and tensor parallelism | collective_throughput | Exact packing/bank-order/rounding plus full-width physical boundary |
| Index/KV service | index_sharding, die_packed_kv | Sustained full-shape shared-stack gate and selected-row attention schedule |
| Physical composition | die_physical and tile physical owners | Characterized local macros, real arcs, cluster and die closure |
| Qwen | Qwen emitter/golden/end-to-end/comparator owners | Shared cluster contract applied to INT8 TP-2 AR, DFlash and all-weight HBM |

The user reset subagent service usage after plan creation. Root resumed ten
critical-path owners and retained the already-running index owner: finite-resource
schedule, executable placement, ROM stream adapter, shared activation storage,
VM/collective physical boundary, die composition, Qwen full-shape replay, Qwen HBM
replay, packed attention integration, and full-shape core/RoPE. Existing jobs must
be inspected before any new launch. Optional queue sweeps, superseded flat CTS
repairs and standard-cell memory surrogate routes stay stopped. These assignments
do not mark any unfinished gate passed.

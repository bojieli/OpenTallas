# V4.1 resource-first arrays: layer locality and active bandwidth

This study chooses ROM area and weight placement first, then derives capacity
and local read limits. It does not choose a token deadline. The primary comparison
remains ROM array versus optimized HBM array; wafer designs are secondary.

## Concrete capacity candidates

Use 815 mm² planning chips, the existing assumed 9,379,500 ROM B/mm² and 2%
reserve. Assign each chip backbone weights from only one layer. Whole experts
remain on one chip; dense inventory is evenly divided among that layer's chips.
This dense division is a capacity assumption, not a legal operator/bank layout.

| ROM area/chip | Area left/chip for all other uses | Chips/layer | Layer-dedicated chips | Total silicon area |
|---|---:|---:|---:|---:|
| 300 mm² | 515 mm² | 3 | 120 | 97,800 mm² |
| 400 mm² | 415 mm² | 3 | 120 | 97,800 mm² |
| 500 mm² | 315 mm² | 2 | 80 | 65,200 mm² |

In all three cases, unused ROM bytes on those chips are enough for the remaining
hybrid checkpoint inventory under perfect packing. This includes the head and
retained draft/resident objects; their service and placement are not proven by
spare capacity. Engram tables remain external and separately charged. No replicas
or bank-alignment overhead beyond the general reserve are credited.

The 400 mm² case illustrates a discontinuity: two chips have sufficient ROM for
the 7.219 GB expert bank alone, but not for the expert bank plus layer-dense data.
A third chip is required by this layer-local policy. The earlier globally packed
84-chip hybrid capacity screen does not prove an 84-chip layer-dedicated layout.
Relaxing locality or moving selected dense objects to separately scheduled chips
might recover capacity efficiency, but adds real placement and communication work.

**These are byte-feasible candidate layouts, not physically feasible chips.**
The remaining 315–515 mm² must fit compute, SRAM, PHYs, clock/power infrastructure
and wiring. A ROM-area increase can reduce chip count while making the active
compute/port problem harder. Wider ROM ports may invalidate the assumed density.
Do not choose the 80-chip design solely because it has fewer chips.

## Whole-expert placement limits HBM active bandwidth

Consider a separate HBM placement screen: each expert is wholly resident on one
chip, expert IDs are balanced over P chips for each layer, and the six selected
experts are uncached. All chips serving the layer can read concurrently. One
packed expert is 18,800,640 B. With delivered rate b on each chip, the per-layer
read lower bound is `max_selected_experts_on_one_chip × expert_bytes / b`.

Across forty dependent layers, at the existing **assumed** 4.5 TB/s per chip:

| Chips owning a layer | Expert-read floor, most spread selection | Expert-read floor, concentrated selection |
|---|---:|---:|
| 1 | 1,002.701 µs | 1,002.701 µs |
| 2 | 501.350 µs | 1,002.701 µs |
| 3 | 334.234 µs | 1,002.701 µs |
| 6 | 167.117 µs | 1,002.701 µs |
| 32 | 167.117 µs | 1,002.701 µs |
| 84 | 167.117 µs | 835.584 µs |
| 384 | 167.117 µs | 167.117 µs |

The columns are analytical routing extremes, not observed frequencies. Best
maximum load is `ceil(6/min(P,6))`; worst is `min(6,ceil(384/P))` under balanced
expert-ID ownership. Concurrent users and skew require a separate queue/service
analysis. Routing outputs are model semantics, not knobs the scheduler can change.

For a single sequence, more than six chips do not improve this best-case read
floor when experts remain whole. At most six expert-owning chips are active for
that token/layer. The 167.117 µs read floor gives an optimistic ceiling of roughly
**5,984 tokens/s for this uncached, unstriped placement**, before dense work,
compute recurrence, communication, attention and numerical service. The
three-chip best-route case gives about 2,992 tokens/s from expert reads alone.
These are not full-system forecasts or universal HBM ceilings.

To exploit more chips for one token, HBM may stripe each expert across chips,
cache weights, or use another placement. Stripe read time can decrease, but
partial reductions/activation gathering, latency and numerical association must
be charged. Caching can remove HBM reads; local SRAM reads and compute remain.
The HBM baseline is allowed these optimizations. Comparing ROM only against the
whole-expert HBM case would not establish superiority over an optimized baseline.

The same ownership reasoning applies to ROM: cold banks do not contribute active
bandwidth. Substitute qualified local ROM service for b; do not assume ROM has
HBM's rate, or assign its rate from a desired token deadline. ROM banking can
stripe within a chip and avoid package reductions, but its compute and port area
must support that service.

## Next architectural comparison

Carry two placement families forward for both arrays:

1. Layer-local, whole-expert execution: fewer package reductions, but concentrated
   local service and idle capacity for a single sequence.
2. Cross-chip tensor-striped execution: more usable active-chip service, at the
   cost of fabric, reduction and synchronization.

Within each family, use the dense projection alternatives and explicit caches.
Choose per-chip engines and ROM banks from area/power evidence, then derive local
rates and the complete dependency path. Report single-sequence latency separately
from aggregate pipeline throughput. No numeric physical maximum is justified yet
for the ROM array because local macro/compute/power qualification remains open.

Run `python3 tools/audit_v41_layer_local_arrays.py` for the
[capacity and placement calculation](../results/architecture/v41_layer_local_arrays.json).
No workload or RTL simulation is performed.

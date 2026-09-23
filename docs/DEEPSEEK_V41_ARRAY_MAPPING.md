# V4.1: fit expert striping into an actual array map

The previous striping calculation assumed six selected experts on disjoint chip
sets. This study makes that ownership explicit and tests it against the 80- and
120-chip capacity candidates. No desired token deadline determines the mapping.

## Mapping family

Divide forty layers into stages. Within each stage, split 384 expert IDs evenly
among islands; an island has S chips and stripes each of its experts across all
S chips. The same island partition holds expert weights for every layer in that
stage. Dense weights are ideally partitioned over the stage chips for a capacity
screen. There are no expert replicas.

For C chips and L layers/stage, the island count per stage is:

`floor(C / [(40/L) × S])`.

This count determines both capacity and whether six selected experts can reach
six different islands. Sharing more layers on each island increases active-chip
reach for one layer, while sharing those chips' compute among more layers. That
changes concurrent pipeline service; it cannot be counted as free throughput.

## Eighty-chip, four-chip-island example

Each 815 mm² chip allocates 500 mm² to ROM. At the current assumed density and
2% reserve it holds 4.596 GB. The remaining 315 mm² has not yet been proven to fit
compute, SRAM, PHYs and physical infrastructure.

| Layers/stage | Stages | Islands/stage | Maximum backbone bytes/chip | Expert-read best route | Expert-read concentrated route |
|---|---:|---:|---:|---:|---:|
| 2 | 20 | 1 | 3.738 GB | 250.675 µs | 250.675 µs |
| 4 | 10 | 2 | 3.716 GB | 125.338 µs | 250.675 µs |
| 8 | 5 | 4 | 3.707 GB | 83.558 µs | 250.675 µs |
| 20 | 2 | 10 | 3.760 GB | 41.779 µs | 250.675 µs |
| 40 | 1 | 20 | 3.850 GB | 41.779 µs | 250.675 µs |

Read times use **4.5 TB/s per chip solely as a common service sensitivity**, matching
the existing HBM assumption. They are not ROM predictions. They omit compute,
fabric, caches, dense operators, attention and control. For another qualified
local read rate b, multiply by `4.5 TB/s / b`.

The two-layer stage puts all six selected experts on the same four chips. The
previous 41.779 µs expert-read point is therefore invalid for that map: it needs
six disjoint expert islands. Twenty-layer stages provide ten islands and permit
that best-case routing, but all six selected experts can still reside on one
island. Router traces are needed to estimate distribution; deterministic bounds
must retain the concentrated case. The scheduler cannot change the model's
selected experts to obtain a convenient balance.

A one-layer-per-stage, four-chip-island layout would need at least 160 chips just
to give every layer one island. It cannot fit the eighty-chip array. More capable
per-chip compute or links cannot repair a missing capacity/ownership assignment.

## Capacity proof boundary

All displayed layouts fit the backbone tensors under the ideal dense partition.
The complete hybrid inventory also fits aggregate array ROM capacity, but its head,
draft and remaining resident tensors have not been individually assigned to spare
banks. Bank alignment, replicas and executable dense-operator grouping may consume
more capacity. Engram tables remain external and separately charged.

The executable sweep includes 120-chip/400-mm²-ROM candidates and shard counts
1, 2, 4, 8 and 16, checking the peak owner rather than just average bytes. It does
not assert a physically feasible compute/port organization on any chip.

## Consequence for the primary comparison

Keep two independent design choices explicit:

- **Layers sharing a compute region:** controls available islands per active layer
  and the opportunity for different tokens to occupy different stages.
- **Chips sharing one expert:** controls local read parallelism, partial reductions
  and fabric cost.

Selecting a good shard count from a read/fabric curve does not select a valid
array. First fit that shard count into a stage/island map. Then derive route-aware
read and compute service, actual dispatch destinations and reduction topology.
Dispatch can reuse the same activation at an island serving multiple experts;
partial outputs must retain required arithmetic semantics. Do not copy the earlier
six-disjoint-set fabric bytes into a concentrated map without rederiving them.

Apply the same topology choices to the HBM baseline. HBM's different storage
capacity may permit different layer sharing, while ROM's physical capacity can
force more chips or larger multi-layer regions. Equal total area comparisons must
allow independent optimization, not impose the ROM map on HBM. Neither baseline
nor proposal has a qualified whole-token estimate yet.

Run `python3 tools/audit_v41_array_mapping.py` for the
[placement sweep](../results/architecture/v41_array_mapping.json). This is static
capacity and service arithmetic, not workload or RTL simulation.

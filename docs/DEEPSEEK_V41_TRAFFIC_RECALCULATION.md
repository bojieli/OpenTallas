# V4.1 traffic recalculation: bytes first, latency second

The **112.8 TB/s** figure is conditional on an aggressive allocation: 40 µs for
routed experts within a hypothetical 100 µs token. Neither number is a user
requirement or an intrinsic property of V4.1. No token-latency target is selected.
The earlier study spent too much effort sizing this probe before establishing an
appropriate system target. Its resource screens remain sensitivity cases.

## Model-derived inventory

The pinned DeepSeek-V4.1-Flash configuration has hidden width 5,120, expert
intermediate width 2,304, 40 ordinary layers, 384 routed experts per layer and six
selected experts per token/layer. Vendor `ModelArgs.get_moe_config` applies these
counts to all ordinary layers; draft layers have a separate configuration.
Each routed expert has gate, up and down matrices:

`3 × 5120 × 2304 = 35,389,440 weight values/expert`.

The pinned vendor `Linear` FP4 branch stores two values per byte and **one E8M0
scale byte per output row per 32 K values**. This is a 1×32 scale layout, distinct
from the dense FP8 32×32 layout. The profile's general prose incorrectly calls the
routed layout 32×32; its byte inventory agrees with the actual 1×32 source layout.
This audit uses the source layout and validates the existing byte inventory.

| Quantity | Bytes |
|---|---:|
| One expert, FP4 values | 17,694,720 |
| One expert, E8M0 scales | 1,105,920 |
| One expert, total | 18,800,640 |
| Six selected experts, one layer | 112,803,840 |
| Six selected experts × 40 layers | 4,512,153,600 |

Thus ordinary batch-one routed expert execution reads **4.512 GB/token** under a
one-read-per-selected-weight assumption. It does not read all 384 experts. Scale
storage adds 6.25% over FP4 payload; it does not explain an orders-of-magnitude
bandwidth difference. FP8/BF16-expanded reads are not used in this calculation.

The routed arithmetic is `35,389,440 × 6 × 40` MACs, or **16.987 Goperations/token**
when one MAC counts as two operations. Shared expert, dense projections, attention,
Engram, routing, quantization and nonlinear work are excluded from these routed
figures. They must be added to the full model service ledger, not silently assumed
free. Resident model capacity is also a different quantity from active reads.

## Where the large rates came from

The previous study allocated `40 µs / 40 layers = 1 µs/layer` to routed experts:

- `112.804 MB / 1 µs = 112.804 TB/s` active-layer local reads.
- `16.987 Goperations / 40 µs = 424.673 TOp/s` routed arithmetic.

Across an entire **100 µs token**, the average routed read rate would instead be
**45.122 TB/s**. The 112.804 TB/s rate is higher because those reads were allocated
only 40% of the token interval. These are decimal GB/TB units.

| Total time available to routed experts across 40 layers | Aggregate local reads | Routed arithmetic |
|---|---:|---:|
| 40 µs, previous probe | 112.804 TB/s | 424.673 TOp/s |
| 100 µs | 45.122 TB/s | 169.869 TOp/s |
| 250 µs | 18.049 TB/s | 67.948 TOp/s |
| 500 µs | 9.024 TB/s | 33.974 TOp/s |
| 1 ms | 4.512 TB/s | 16.987 TOp/s |
| 5 ms | 0.902 TB/s | 3.397 TOp/s |
| 10 ms | 0.451 TB/s | 1.699 TOp/s |

The first column is **expert service time**, not complete token latency. For
example, if experts retain a 40% allocation within a 1 ms token, their budget is
400 µs and the required rate is 11.280 TB/s. A 1 ms expert budget gives 4.512 TB/s
but leaves the other model work to be accounted for separately.

## What “weight delivery” means for ROM and HBM

For ROM, these are aggregate local reads from weight banks into arithmetic. They
need not cross one package, die-to-die link or central bus. At the 40 µs probe,
six equally provisioned selected experts each need 18.801 TB/s locally; a group
containing all six must deliver the sum. Keeping computation by the ROM avoids
shipping the full weight stream across the global network. Activation multicast
and returned outputs are separately priced traffic.

For HBM, 4.512 GB/token is the routed portion of uncached external weight reads.
A persistent SRAM expert cache reduces HBM reads on hits but still supplies local
weights to compute. Batched tokens selecting the same expert can reuse a weight
read across several activations. Those cases need explicit cache-hit and route
reuse assumptions; dividing by batch size without shared expert use is invalid.

A distributed layer pipeline can improve multi-user throughput by overlapping
different tokens in different layers. It does not divide a single user's latency
by forty. Installed bandwidth in inactive banks also does not automatically
satisfy the selected experts' local service demand.

## Revised planning decision

Keep **4.512 GB of selected routed weights and 16.987 Goperations per ordinary
batch-one decode token** as the checked inventory. Sweep latency and reuse rather
than treating 100 µs or 40 µs as requirements. Choose a target only after deriving
full-model service, achievable local ROM rates, comparable HBM cache/placement,
area and power. The several-fold ROM advantage remains the objective to evaluate;
it does not itself imply a 100 µs token.

Reproduce the geometry and sensitivity table with
`python3 tools/audit_v41_budget_sensitivity.py`. Results and input hashes are in
[the JSON calculation](../results/architecture/v41_budget_sensitivity.json).
This is a static calculation, not implementation or workload simulation.

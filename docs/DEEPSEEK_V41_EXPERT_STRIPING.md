# V4.1 expert striping: where more chips stop helping

This static study tests the alternative to whole-expert placement for both the
HBM baseline and ROM chip array. No token deadline determines the resource count.
It prices only expert weight reads and dispatch/return communication; it is not a
whole-token forecast or a physical implementation qualification.

## Partition and numerical boundary

Partition an expert's 2,304 intermediate rows over S chips. Each chip owns matching
gate and up rows, performs its local nonlinear products, and owns the corresponding
K slice of the down projection. This avoids transporting gate/up intermediates
between shards, but produces S partial hidden vectors that must be combined.
Six selected experts on disjoint shard sets activate **6S chips**. All six sets
being distinct is an optimistic placement assumption, not a guarantee under route
concentration or a capacity-qualified deployment.

Activation quantization blocks, routing-weight placement, partial accumulation,
rounding and final expert combination need explicit contracts. The vendor applies
routing weights inside the expert before the down projection. It is not generally
valid to move that multiplication after a rounded projection. No such rewrite or
numerical reassociation is authorized by this byte-service screen.

For controlled comparison, all return vectors are FP32, including S=1. The prior
whole-expert BF16 return case is cheaper; the tables are not directly interchangeable.
No reduction arithmetic or network aggregation is credited.

## Read versus fabric tradeoff

For local delivered weight bandwidth b per chip and packed expert bytes E:

`expert reads across 40 layers = 40 × E / (S × b)`.

With six selected experts, unicast BF16 input and FP32 partial returns:

`endpoint payload per layer = 6S × 5120 × (2 + 4) bytes`.

Use the same illustrative 400 GB/s delivered endpoint rate per direction and
0.5 µs fixed one-way delay as the earlier communication screen. Dispatch and
return contribute 40 µs of fixed delay across forty layers before serialization.
The following totals sum reads and fabric without overlap:

| Shards/expert | Active chips | Reads at 4.5 TB/s/chip | Fabric | Read + fabric subtotal |
|---|---:|---:|---:|---:|
| 1 | 6 | 167.117 µs | 58.432 µs | 225.549 µs |
| 2 | 12 | 83.558 µs | 76.864 µs | 160.422 µs |
| 4 | 24 | 41.779 µs | 113.728 µs | 155.507 µs |
| 8 | 48 | 20.890 µs | 187.456 µs | 208.346 µs |
| 16 | 96 | 10.445 µs | 334.912 µs | 345.357 µs |

More chips eventually increase this subtotal. Four shards are best among these
five tested choices, but this is **not** a selected architecture. Compute, reduction,
scale service, dense operators, KV/attention, control and queueing remain missing.
A real pipeline can overlap some reads and compute; the artifact separately reports
`max(read_time, fabric_time)` as an optimistic overlap floor, not a realizable
schedule. Neither the sum nor that floor establishes full-system tokens/s.

Source multicast reduces dispatch injection, while still requiring leaf delivery.
At four shards it reduces this example's subtotal to **131.955 µs**, but does not
eliminate partial return traffic. A distributed reduction topology may reduce the
central ingress bottleneck at the cost of hops, arithmetic, association changes
and publication service; that needs its own qualified model.

## Why ROM may favor a different partition

Keeping all other assumptions fixed gives this sensitivity:

| Local delivered rate/chip | Best tested S, unicast | Best tested read + fabric subtotal |
|---|---:|---:|
| 4.5 TB/s | 4 | 155.507 µs |
| 18 TB/s | 2 | 97.754 µs |
| 72 TB/s | 1 | 68.877 µs |

The 4.5 TB/s rate is the existing HBM assumption. **18 and 72 TB/s are hypothetical
local-service values, not established ROM capabilities.** The useful conclusion
is structural: as local weight supply improves, extra package sharding buys less
and its communication cost can dominate. ROM's candidate advantage is sufficient
bank-local compute and weight supply with fewer package reductions, not infinitely
large installed bandwidth. SRAM-cached HBM may also favor local execution and must
receive the same opportunity.

The comparison must now fit these shard sets into the capacity-constrained arrays,
charge route concentration, and supply finite compute/ROM-port area and power.
The local rate cannot be selected solely to make this table favorable. Hardware
collectives and on-chip shard reduction remain possible alternatives; their
latency and numerical behavior need evidence before reducing the communication
charge. Dense attention-output communication remains separate and must not be lost
when optimizing this expert path.

Reproduce with `python3 tools/audit_v41_expert_striping.py`; see the
[calculation](../results/architecture/v41_expert_striping.json). No workload or RTL
simulation is run.

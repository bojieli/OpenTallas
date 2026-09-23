# V4.1: primary HBM-array versus ROM-array comparison

The user has specified **three designs**, with a 100 µs/token decode feasibility
target. This supersedes the earlier wafer-first ordering.

| Design | Role | Weight placement | Mutable-state placement |
|---|---|---|---|
| HBM accelerator array | Primary baseline | HBM plus explicitly priced SRAM caching | HBM/SRAM |
| ROM chip array with fast fabric | Primary proposed design | Distributed local ROM; hybrid Engram placement evaluated separately | Conventional per-chip or attached memory service, fully charged |
| Integrated ROM wafer, or connected ROM wafers | Secondary proposed design | ROM across one or more wafers | Explicit external/attached service; integration remains unqualified |

The objective is to establish whether the ROM approach improves **decode speed**
over an optimized GPU-style HBM array. It is not enough to show a high ROM rate in
isolation. Compare ordinary batch-one token latency and multi-user throughput
separately; preserve model, precision/accuracy criteria, context and output work.
The pinned deployment is V4.1-Flash. Qwen remains a separate validation workload.

## Fair primary comparison

First compare arrays with equal total compute-die area and separately equal system
power. Charge PHYs, switches, package links, SRAM, controllers and cooling-related
limits; off-die resources are not free. Also report capacity-matched deployments
when equal-area systems cannot hold the same inventory. Price manufacturing and
memory/package cost separately rather than presenting equal area as equal cost.

Both arrays get the same opportunity to optimize local compute, KV/index ownership,
numerical services, expert routing and batching. The HBM baseline gets persistent
non-routed/hot-expert caches and feasible prefetch. The ROM candidate gets local
weight consumption and appropriate bank organization. Neither gets perfect cache
hits, globally usable installed bandwidth, or unqualified numerical reassociation.

Use conventional HBM GPU arrays as the architectural baseline. Actual NVIDIA
product comparisons require pinned specifications and measured or independently
validated workload results; the current 4.5 TB/s endpoint is an analytical
assumption, not an NVIDIA benchmark. NVLink/NVL72-style connectivity describes
the class of fabric; it does not select a particular topology or rate.

## Expert traffic: small payload, potentially large serial latency

A candidate local-expert placement sends a collapsed BF16 hidden vector of 5,120
values to each of six experts and returns one BF16 vector per expert. The pinned
model's expert path returns the final Linear result and the MoE accumulates expert
outputs into FP32. Numerical equivalence of a proposed central merge still needs
qualification. Do not replace that merge with an arbitrary in-network tree.

Without multicast, per layer:

- Dispatch: `5120 × 2 × 6 = 61,440 B`.
- Return: another `61,440 B`.
- Forty layers: **4.915 MB/token** at the dispatch/merge endpoints.

At 100 µs/token this averages **49.152 GB/s** of summed dispatch-plus-return
endpoint traffic. This is not 112.8 TB/s: the latter is local expert weight reads
under the separate 40 µs expert allocation. No weight payload crosses the array
fabric in this local-expert placement. Expert sharding would add communication.

For an illustrative serial schedule with a common dispatch/merge endpoint,
delivered payload bandwidth B per direction and fixed one-way delivery delay d:

`expert fabric time = 40 × [2d + 122880/B]`.

Dispatch and return are on opposite sides of expert compute, so this screen adds
their serialization. It omits packet overhead, contention, errors, other operators
and topology-dependent hop traffic. It credits no overlap with compute. At an
**assumed**, not measured, 400 GB/s delivered per direction:

| Fixed one-way delivery delay | Expert dispatch/return across 40 layers |
|---|---:|
| 0.10 µs | 20.288 µs |
| 0.25 µs | 32.288 µs |
| 0.50 µs | 52.288 µs |
| 1.00 µs | 92.288 µs |
| 2.00 µs | 172.288 µs |

At infinite bandwidth, fixed delay alone exceeds the whole 100 µs target when
d > 1.25 µs for this placement. An illustrative 20 µs expert-fabric allocation at
400 GB/s requires d ≤ 96.4 ns. That is a demanding requirement, not a chosen
allocation or an assertion that current GPU fabrics deliver it. Endpoint software,
DMA, switch traversal and synchronization cannot disappear from d.

Hardware multicast can reduce source injection to one 10,240 B vector, but still
must deliver six copies at the leaves. It does not remove the return dependency.
FP32 returns increase payload. The executable sweep covers both cases; neither
multicast delivery nor a numerical merge is assumed free. Per-direction rates
must not be confused with summed bidirectional specifications.

**Implication:** optimize placement and serial message count before purchasing more
aggregate bandwidth. Keep expert weights beside compute, use bounded hardware
activation dispatch/return, and avoid unnecessary system-wide collectives. Analyze
shared/dense operators and KV transfers independently. Apply these improvements
to the HBM baseline too. A fabric limitation shared by both arrays can prevent a
3× system gain even if ROM weight service is much faster.

## Secondary wafer design

Retain all-ROM and hybrid wafer variants and permit multiple wafers when one
cannot hold the inventory. At current density, all-ROM weights require about
55,515 mm² of ROM alone, or hybrid weights 33,456 mm² with Engram elsewhere.
Partition over two or more wafers when appropriate; charge each wafer's compute,
repair, routing, power and inter-wafer endpoints. Choosing more wafers does not
remove expert dispatch, reduction or cross-layer boundary costs.

Wafer-scale HBM attachment for KV storage is **not established in this project**.
Treat the user's manufacturing concern as a reason for secondary priority. Do not
assume an available memory integration technology, and do not make an unsupported
industry-wide claim that none exists. Evaluate explicit external KV memory-service
and link options, including capacity and worst-case service, before accepting a
wafer deployment. A wafer comparison must not count free HBM or external Engram.

## Work order and acceptance

1. Reconcile full-model tensor reads, numerical work and dependencies for the
   HBM-array and ROM-array deployments, including non-routed matrices and caches.
2. Derive finite local compute/bank service and exact placement for both arrays;
   price expert and non-expert communication on a common fabric model.
3. Combine service, dependency, area and power constraints to determine whether
   either array can reach 100 µs, and their conditional performance ceilings.
4. Establish ROM/HBM speedup at equal area and power, with context, batch, routing
   concentration and cache sensitivity. Do not promote memory-only ratios to
   token-speedup claims.
5. Apply the same ledger to secondary one-/multi-wafer ROM candidates, with a
   separately qualified external-memory interface and inter-wafer fabric.
6. Start implementation and simulation only after the feasibility gate is met.

The new expert-fabric screen is reproduced with
`python3 tools/audit_v41_fabric_feasibility.py`; its
[results](../results/architecture/v41_fabric_feasibility.json) are conditional
arithmetic, not a link benchmark or workload simulation. Other supporting studies:
[physical capacity](DEEPSEEK_V41_PHYSICAL_LIMITS.md),
[traffic inventory](DEEPSEEK_V41_TRAFFIC_RECALCULATION.md), and
[cache/common-work speedup limits](DEEPSEEK_V41_SPEEDUP_CONDITIONS.md).

The [non-routed tensor audit](DEEPSEEK_V41_DENSE_PLACEMENT.md) reconciles the
8.523 GB inventory and identifies attention, shared experts and the output head
as the main non-routed placement targets. Runtime-role qualification remains open.

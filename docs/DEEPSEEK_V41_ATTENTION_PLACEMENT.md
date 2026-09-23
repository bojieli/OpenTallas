# V4.1 attention placement: eight logical groups

This is a concrete placement candidate for the primary HBM-array versus ROM-array
comparison, not a selected chip count or a qualified numerical implementation.
The pinned configuration has 64 heads of width 512, eight output groups, Q rank
1,280 and output rank 1,024 per group. Each logical group can own eight heads and:

| Matrix slice | Weight values per group | Input/output role |
|---|---:|---|
| Q expansion `wq_b` | 5,242,880 | 1,280 shared Q features → eight heads |
| Grouped output `wo_a` | 4,194,304 | 4,096 head features → 1,024 group features |
| Final output `wo_b`, K slice | 5,242,880 | 1,024 group features → 5,120 partial outputs |

`wo_a` is block-diagonal over groups, not a full 32,768-to-8,192 dense matrix.
Place each group's attention heads and `wo_a` together to avoid transporting the
full head output to a central projection. `wq_a`, query normalization, window KV,
compressed KV/index ownership and the attention data itself still need placement.
Logical groups may share a chip; eight groups does not require eight chips/layer.

## Two choices for the final output projection

**K-shard `wo_b` with the group.** Each group retains its own 1,024-feature input
and produces a 5,120-element partial output. A central FP32 merge receives eight
20,480 B vectors, or **163,840 B/layer and 6,553,600 B/token**. It additionally needs
35,840 FP32 additions/layer for a simple eight-input ordered merge. Return format
and association must be qualified: the pinned RowParallelLinear computes local
linear results, casts to FP32 and calls distributed all-reduce. A new ordered
central merge is not automatically bit-equivalent to that operation.

At an assumed 400 GB/s delivered ingress, the partial return alone takes:

| Fixed one-way delay | Forty-layer ingress time |
|---|---:|
| 0.1 µs | 20.384 µs |
| 0.5 µs | 36.384 µs |
| 1.0 µs | 56.384 µs |

This excludes query multicast, output publication, local merge work, attention
KV delivery, all compute and contention. It includes all eight group contributions;
co-locating groups and a merge endpoint can reduce external bytes. A network tree
can redistribute the merge work, but its arithmetic ordering, hop cost and output
delivery need proof. It is not a free replacement for the central sensitivity.

**Gather group features and output-row-shard `wo_b`.** The unique BF16 source
features total only 16,384 B/layer. Supply those features to the owners of output
rows, each of which computes a complete dot product. This can avoid a cross-chip
partial-sum merge and preserve an ordered full-K accumulation if that is the
admitted contract. However, every row owner needs all input features: 16,384 B is
unique source payload, not total delivered or hop bytes. Allgather latency,
replication, output ownership, matrix layout and recurrence can offset the apparent
payload benefit. Evaluate both choices on both architectures.

For context, the earlier serial expert-dispatch sensitivity used 52.288 µs at
400 GB/s and 0.5 µs fixed one-way latency. Adding this central output-partial return
without overlap gives **88.672 µs**, leaving only 11.328 µs of a 100 µs token for
all omitted work. This is a warning about that particular placement, not a universal
array lower bound: local co-location, different sharding and qualified overlap
can change it. A bandwidth-only comparison misses this serial-message constraint.

## Checkpoint format is not necessarily the execution format

The checkpoint headers store `wo_a` as FP8 weights plus E8M0 scales:
**1,343,488,000 B** across forty layers. The pinned `inference/convert.py` multiplies
by the scales and converts these tensors to BF16, deleting their scale tensors.
The resulting resident `wo_a` data occupy **2,684,354,560 B**.

Thus materializing only this conversion adds **1,340,866,560 B**, changing the
active weight inventory from 13,035,075,008 B to **14,375,941,568 B/token** under a
one-read-per-weight assumption. This is a sensitivity for `wo_a` only, not a full
vendor-GPU deployment inventory; expert recasting and other layout choices must
be accounted for separately.

A ROM or HBM design can retain packed FP8/scales and reconstruct the required BF16
operands near compute, if it reproduces the vendor conversion and prices its
throughput, range handling and buffering. Keeping packed storage does not authorize
replacing the BF16 grouped contraction with a different FP8 GEMM association.
Both designs receive the same reconstruction option for a fair comparison.
The existing packed inventory is therefore retained and explicitly labeled; it
must not be presented as the bytes of an already-expanded GPU deployment.

## Next acceptance work

Integrate the two `wo_b` placements with dense/shared-expert placement and finite
compute service. Count actual boundaries after co-location rather than presuming
a global collective at every step. Qualify deployment formats and numerical
contracts before declaring either communication scheme feasible. Preserve full
KV/index and hyper-connection service in the total; these projection numbers do
not cover all attention work.

Reproduce with `python3 tools/audit_v41_attention_placement.py`. The
[calculation](../results/architecture/v41_attention_placement.json) pins both vendor
source files and the tensor inventory. No workload or RTL simulation was launched.

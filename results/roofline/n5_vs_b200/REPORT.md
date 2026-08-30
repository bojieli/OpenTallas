# Area-constrained roofline: n5_vs_b200

> Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 76.6 us, or 13,063 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 614x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate -- runs `tensor` on 1 device. On the GPU side the correction reaches 260x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate -- runs `hybrid` on 29 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **The ROM advantage is a batch-1, per-user advantage, and it is large.** At equal area the best batch-1 point is DeepSeek-V4-Flash-0731 on 92,450 mm2 of ROM silicon at 5,606 tok/s per user, against 92,800 mm2 of b200_sxm-x58-tensor at 821 tok/s: **7x**. Both sides bind on `link_latency`, and the whole difference is that one reads its weights from HBM and the other from an on-die array.
4. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on Qwen3-8B at batch 1, the iso-area GPU cluster is 347 devices. Cut as one serial pipeline that is 44 stages and 418 us of link latency per token; but the model has 36 layers, so at most 36 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 381 us. The iso-area per-user ratio at that point falls from 3.6x to 3.5x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
5. **Letting the GPU choose its own parallelism is worth up to 66.78x to it.** At 554,700 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 7.63 tok/s and the same silicon running tensor delivers 509 tok/s.
6. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.04x (Qwen3-8B, ROM binding on `weight_read`) to 19.64x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
7. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 35.7% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 808 to 11,591 tok/s, and its rate with every slot occupied from 11,307 to 11,591. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 14 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
8. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,572 us over NVLink, capping per-user decode at 636 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 1,431.2 us and cap it at 699 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 2.0x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
9. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 24 of 24 operating points and an array 0; on tokens per second per square millimetre the same points go 11 to the array and 13 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
10. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 318 of 3016 feasible points.
11. **The largest open question is not in this model's inputs but in the architecture, and the anchor cannot settle it.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 28.5x of aggregate throughput (DeepSeek-V4-Flash-0731). The machines are identical at batch 1, which is where the published anchor sits, so no amount of validation against it resolves the fork.
12. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 8.77x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 3.02x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 44 of 48 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
13. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.

## The overlap and serialisation rule

```
t_memory  = t_weight + t_kv        weights and KV share one memory system
t_memory  = max(t_weight, t_kv)    weights and KV are separate arrays
t_service = max(t_memory, t_compute)      on the AGGREGATE machine
t_user    = token_slots * t_service / stage_balance + t_link
t_user   *= thermal_scale

per_user_tokens_s  = 1 / t_user
aggregate_tokens_s = fill_users / t_user      fill_users = max(batch, slots)
delivered_tokens_s = batch / t_user
```

Compute overlaps memory. Weight and KV traffic **add** on a GPU because they
contend for the same HBM channels, and **overlap** on a ROM part because the
mask ROM and the KV store are physically separate arrays -- that single rule
is most of the architectural difference and it is stated rather than hidden
in an efficiency factor. Hop and collective latency is **added** to the
critical path at every batch size, because decode is sequential across
layers.

`t_service` is computed on the machine's **aggregate** resources: all of the
array bandwidth, all of the compute roof. That denominator is correct only
for partitions that are working on the same token at the same instant, which
is what tensor parallelism is. `token_slots = partitions / tensor_group` is
how many independent groups the machine is cut into, and a token is served by
exactly one of them at a time, so its latency is `token_slots` service times
long. **Under pipeline parallelism the two factors cancel exactly** -- each of
N stages holds 1/N of the weights and reads them with 1/N of the bandwidth --
so adding devices buys aggregate throughput and buys one user nothing.
Tensor parallelism is different in kind: every partition is on the same token,
`token_slots` is 1, and the price is two all-reduces per layer, charged in
`t_link`.

**`aggregate = batch x per-user rate` no longer holds and its removal is the
point.** The aggregate rate is the machine's rate with every slot occupied,
which needs `token_slots` concurrent users; below that the surplus slots idle
and the machine delivers `delivered_tokens_s` instead. The fill is capped by
the users whose KV the machine can hold, reported per point as
`pipeline_fill_limited_by`. Fill and drain are not charged: decode is a
continuous stream of steps and the pipeline is taken to be in steady state,
which flatters a deep pipeline by at most one traversal per request.

Every point also carries `per_user_tokens_s_throughput_view`: the single
number this study reported for both quantities before they were separated, so
the size of this correction is separable from every other one.

## Validation gates

| Gate | Published | Modelled | Ratio | Tolerance | Result |
|---|---:|---:|---:|---:|---|
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 12,232.4 tok/s | 0.72x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |

HC1 binds on `weight_read`. Its component times are weight_read 76.55 us, kv_read 2.71 us, compute 76.55 us, link_latency 0.00 us, layer_fixed_latency 5.20 us.

The model **under**-predicts the shipping part by 1.39x. Rather than tune the densities until the anchor
is hit, the gate back-derives what each input would have to be for the
model to land exactly on 17,000 tok/s:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 1.764e+11 | 2.290e+11 | 1.30x |
| Compute density (ops/s/mm2) | 1.261e+12 | 2.840e+13 | 22.52x |

The compute density derived from A100's published dense roofs and die
area is within 2152.4% of what the shipping part must have. The ROM read-bandwidth density derived from a
28 nm simulated ROM-CIM macro is the input that is short, and the
required value is still below the SRAM read-bandwidth density derived
from Cerebras WSE-2 (5.563e+11 B/s/mm2), so it is physically unremarkable. That is a falsifiable
statement about one technology input, which is what a gate is for.

### The per-layer latency band, and why the gate is not fitted

Every term in the per-layer latency block is `assumed` and carries
a stated range. Reporting the gate at one point inside a wide band
would invite the point to be read as measured, which is how a gate
becomes a one-parameter curve fit. The terms are derived from
primitives independent of this anchor -- SRAM access time,
sequencer issue and decode, pipeline fill and drain across a
dependent array-pass boundary, the layer barrier, and an on-die
wire delay over a distance taken from the floorplan -- and the gate
is evaluated at both ends.

| Per-layer latency | Value | Per token | Modelled tok/s | Ratio | Binds on |
|---|---:|---:|---:|---:|---|
| range low | 65.4 ns/layer | 2.09 us | 12,715.1 | 0.75x | weight_read |
| range stated | 162.4 ns/layer | 5.20 us | 12,232.4 | 0.72x | weight_read |
| range high | 726.8 ns/layer | 23.26 us | 10,018.9 | 0.59x | weight_read |

The per-layer cost that would land the model exactly on the
published figure is **-549.7 ns/layer**. It is negative, which means the model is already slower than the shipping part before any fixed cost is charged: no value of this term could have closed the gap, and the residual lies in the ROM read-bandwidth density instead.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 12,232.4 | 0.72x | weight_read |
| 3.5 | 12,232.4 | 0.72x | weight_read |
| 4.0 | 12,232.4 | 0.72x | weight_read |
| 5.0 | 12,232.4 | 0.72x | weight_read |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 12,232.4 | 0.72x | weight_read |
| 1,536 | 12,232.4 | 0.72x | weight_read |
| 2,048 | 12,232.4 | 0.72x | weight_read |

## Derived technology at N5

These are outputs of the graded primitives, not inputs.

| Quantity | Value | Grade |
|---|---:|---|
| SRAM capacity density | 3.869 MB/mm2 | assumed |
| ROM capacity density | 20.833 MB/mm2 | assumed |
| ROM read bandwidth density | 362.9 GB/s/mm2 | derived |
| SRAM read bandwidth density | 556.3 GB/s/mm2 | derived |
| Compute density, bf16 | 0.680 Tops/s/mm2 | derived |
| Compute density, fp8 | 1.360 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.923 Tops/s/mm2 | derived |
| Compute density, fp4 | 2.720 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.042 Tops/s/mm2 | derived |
| ROM full-array sweep time | 76.6 us | derived |
| ROM per-token ceiling from that sweep | 13,063 tok/s | derived |
| ROM per-token ceiling before the read derate | 17,417 tok/s | derived |

The ROM full-array sweep time is rom_capacity_density divided by rom_read_bandwidth_density. Both scale with the same published bitcell-area ratio under this derivation, so the sweep time -- and hence the ROM path's hard per-token ceiling -- is the SAME at every node. Process scaling buys a ROM design capacity, not per-token speed. No clock-frequency bonus is credited, which makes this the conservative reading.

## Models and their work

| Model | Context | Params | Checkpoint | Native bits/param | KV read/token | KV/user | W:KV at B=1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 8,192 | 8 B | 16.4 GB | 16.00 | 1.208 GB | 1.208 GB | 12.5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 284 B | 166.9 GB | 4.70 | 0.317 GB | 1.382 GB | 35.3 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1,600 B | 892.7 GB | 4.46 | 2.207 GB | 9.856 GB | 18.0 |

## The latency separation, before and after, at batch 1

Per-user latency and aggregate throughput used to be one number in
this study. The service time was computed on the machine's
**aggregate** resources -- the throughput view -- and the hops were
added on the single-token path, which is the latency view. A token
under pipeline parallelism is served by one stage's silicon at a time
and has to visit every stage, so its latency is that service time
multiplied by the slot count, not divided by anything.

**Before** is not a memory of an earlier run. Every point carries
`per_user_tokens_s_throughput_view`, the number the old rule produced,
and each side is ranked by it -- so the before column reproduces the
previous topology choice as well as the previous rate, and the two
corrections stay separable. Both sides are read at the same seven
rungs of silicon.

| Model | Wafer-eq | mm2 | ROM before | topo | ROM after | topo | ROM /x | GPU before | topo | GPU after | topo | GPU /x | Ratio before | Ratio after | Ratio change |
|---|---:|---:|---:|---|---:|---|---:|---:|---|---:|---|---:|---:|---:|---:|
| Qwen3-8B | 1 | 46,225 | 53,701.4 | wafer-pipeline | 7,936.4 | wafer-tensor | 6.77x | 6,681.8 | pipeline | 1,650.3 | hybrid | 4.05x | 8.04x | 4.81x | 0.60x |
| Qwen3-8B | 2 | 92,450 | 50,885.4 | wafer-pipeline | 7,022.9 | wafer-hybrid | 7.25x | 8,522.9 | pipeline | 1,601.0 | hybrid | 5.32x | 5.97x | 4.39x | 0.73x |
| Qwen3-8B | 3 | 138,675 | 50,885.4 | wafer-pipeline | 6,339.1 | wafer-hybrid | 8.03x | 9,805.6 | pipeline | 1,645.0 | hybrid | 5.96x | 5.19x | 3.85x | 0.74x |
| Qwen3-8B | 4 | 184,900 | 53,971.3 | wafer-pipeline | 5,930.6 | wafer-hybrid | 9.10x | 10,603.6 | pipeline | 1,576.8 | hybrid | 6.72x | 5.09x | 3.76x | 0.74x |
| Qwen3-8B | 6 | 277,350 | 64,650.3 | wafer-pipeline | 5,595.2 | wafer-hybrid | 11.55x | 11,531.1 | pipeline | 1,512.5 | hybrid | 7.62x | 5.61x | 3.70x | 0.66x |
| Qwen3-8B | 8 | 369,800 | 71,748.5 | wafer-pipeline | 5,295.6 | wafer-hybrid | 13.55x | 12,070.6 | pipeline | 1,450.4 | hybrid | 8.32x | 5.94x | 3.65x | 0.61x |
| Qwen3-8B | 12 | 554,700 | 80,597.5 | wafer-pipeline | 4,783.5 | wafer-hybrid | 16.85x | 12,661.3 | pipeline | 1,378.4 | hybrid | 9.19x | 6.37x | 3.47x | 0.55x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 23,759.5 | wafer-pipeline | 5,871.0 | wafer-tensor | 4.05x | 4,196.2 | pipeline | 1,008.7 | hybrid | 4.16x | 5.66x | 5.82x | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 33,928.8 | wafer-pipeline | 5,606.3 | wafer-hybrid | 6.05x | 4,415.8 | pipeline | 820.8 | tensor | 5.38x | 7.68x | 6.83x | 0.89x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 41,226.1 | wafer-pipeline | 5,453.3 | wafer-hybrid | 7.56x | 4,707.1 | pipeline | 829.3 | tensor | 5.68x | 8.76x | 6.58x | 0.75x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 46,180.5 | wafer-pipeline | 5,307.7 | wafer-hybrid | 8.70x | 4,872.8 | pipeline | 833.6 | tensor | 5.85x | 9.48x | 6.37x | 0.67x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 52,477.1 | wafer-pipeline | 5,038.0 | wafer-hybrid | 10.42x | 5,052.5 | pipeline | 838.1 | tensor | 6.03x | 10.39x | 6.01x | 0.58x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 56,311.6 | wafer-pipeline | 4,794.2 | wafer-hybrid | 11.75x | 5,151.2 | pipeline | 840.4 | tensor | 6.13x | 10.93x | 5.70x | 0.52x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 60,746.8 | wafer-pipeline | 4,370.8 | wafer-hybrid | 13.90x | 5,254.9 | pipeline | 842.8 | tensor | 6.23x | 11.56x | 5.19x | 0.45x |
| DeepSeek-V4-Pro-0813 | 2 | 92,450 | 9,107.3 | wafer-pipeline | 2,653.6 | wafer-hybrid | 3.43x | 1,581.0 | pipeline | 479.8 | tensor | 3.29x | 5.76x | 5.53x | 0.96x |
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 12,382.7 | wafer-pipeline | 2,632.5 | wafer-hybrid | 4.70x | 1,706.8 | pipeline | 491.0 | tensor | 3.48x | 7.25x | 5.36x | 0.74x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 14,980.4 | wafer-pipeline | 2,597.7 | wafer-hybrid | 5.77x | 1,787.3 | pipeline | 496.8 | tensor | 3.60x | 8.38x | 5.23x | 0.62x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 18,958.7 | wafer-pipeline | 2,530.8 | wafer-hybrid | 7.49x | 1,876.8 | pipeline | 503.0 | tensor | 3.73x | 10.10x | 5.03x | 0.50x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 21,888.5 | wafer-pipeline | 2,470.1 | wafer-hybrid | 8.86x | 1,926.9 | pipeline | 506.2 | tensor | 3.81x | 11.36x | 4.88x | 0.43x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 25,862.8 | wafer-pipeline | 2,354.3 | wafer-hybrid | 10.99x | 1,980.4 | pipeline | 509.5 | tensor | 3.89x | 13.06x | 4.62x | 0.35x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.35x to 1.03x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


## Iso-area comparison

Two ROM designs per operating point -- the **fastest** and the
**smallest silicon that serves the point at all** -- each against the GPU
cluster of the closest equal silicon area. **The area is stated on both
sides.** Where one row appears, the two coincide.

**Both sides choose their own parallelism.** The GPU cluster is
evaluated under pipeline, tensor and hybrid and the best is reported,
exactly as the ROM side is. `PP-only ratio` is what the same comparison
says when the GPU is allowed pipeline and nothing else.

`Ratio without the layer cap` is what the comparison says when a token
is allowed to cross more stage boundaries than the model has layers --
which is what this study charged before. That column, not the topology
sweep, is where the previously published ratios came from.

**`user tok/s` and `aggregate tok/s` are different quantities and no
longer differ by the batch.** `user tok/s` is one user's token rate on
the full serial path through the machine. `aggregate tok/s` is the
machine's total rate with a user in every slot, which needs
`token_slots` concurrent users; where the batch is smaller than that,
the surplus slots idle and what the machine actually delivers at the
stated batch is `batch x user tok/s`, carried per point as
`delivered_tokens_s`. Read the per-user ratio for a latency claim and
the aggregate ratio for a throughput claim; reading either as the other
is the error this study made.

| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | GPU parallelism | GPU link us | GPU user tok/s | GPU aggregate tok/s | GPU binds on | Per-user ratio | Aggregate ratio | PP-only ratio | Ratio without the layer cap |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---:|
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 7,936.4 | 7,936.4 | link_latency | Qwen3-8B/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 231.71 | 1,650.3 | 6,601.4 | weight_read | 4.81x | 1.20x | 21.65x | 4.81x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x3 | 2,445 | 3,787.3 | 3,787.3 | weight_read | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 0.76x | tensor | 216.98 | 641.8 | 641.8 | weight_read | 5.90x | 5.90x | 10.14x | 5.90x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 6,308.8 | 12,617.7 | link_latency | Qwen3-8B/b200_sxm-x58-hybrid | 92,800 | 1.00x | hybrid | 250.37 | 1,601.0 | 12,808.4 | weight_read | 3.94x | 0.99x | 17.30x | 3.94x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4-romfill | 3,260 | 3,065.4 | 12,261.7 | kv_read | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 217.97 | 603.2 | 1,206.4 | weight_read | 5.08x | 10.16x | 8.21x | 5.08x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 5,930.6 | 23,722.4 | link_latency | Qwen3-8B/b200_sxm-x116-hybrid | 185,600 | 1.00x | hybrid | 283.01 | 1,576.8 | 23,651.3 | weight_read | 3.76x | 1.00x | 16.26x | 3.76x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4-romfill | 3,260 | 3,065.4 | 12,261.7 | kv_read | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 219.93 | 538.4 | 2,153.7 | weight_read | 5.69x | 5.69x | 8.81x | 5.69x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 5,295.6 | 42,365.0 | link_latency | Qwen3-8B/b200_sxm-x231-hybrid | 369,600 | 1.00x | hybrid | 348.31 | 1,450.4 | 42,063.0 | link_latency | 3.65x | 1.01x | 14.52x | 3.65x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 1,557.4 | 12,459.3 | kv_read | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 223.86 | 443.3 | 3,546.1 | weight_read | 3.51x | 3.51x | 5.09x | 3.51x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,514.8 | 72,236.0 | link_latency | Qwen3-8B/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 380.95 | 1,378.4 | 60,651.7 | link_latency | 3.28x | 1.19x | 12.38x | 3.44x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 785.0 | 12,560.5 | kv_read | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 231.73 | 327.5 | 5,239.9 | kv_read | 2.40x | 2.40x | 3.19x | 2.40x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,686.4 | 117,965.7 | link_latency | Qwen3-8B/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 380.95 | 1,378.4 | 60,651.7 | link_latency | 2.67x | 1.94x | 10.11x | 2.81x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 394.1 | 12,611.7 | kv_read | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 247.46 | 215.1 | 6,884.1 | kv_read | 1.83x | 1.83x | 2.22x | 1.83x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,696.8 | 172,597.9 | kv_read | Qwen3-8B/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 384.34 | 1,350.9 | 86,460.7 | link_latency | 2.00x | 2.00x | 7.39x | 2.10x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 197.5 | 12,637.5 | kv_read | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 278.91 | 127.6 | 8,165.0 | kv_read | 1.55x | 1.55x | 1.74x | 1.55x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,033.0 | 264,453.1 | kv_read | Qwen3-8B/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 416.87 | 1,133.8 | 290,257.3 | link_latency | 0.91x | 0.91x | 2.83x | 0.96x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 49.4 | 12,656.9 | kv_read | Qwen3-8B/b200_sxm-x2-pipeline | 3,200 | 1.02x | pipeline | 2.67 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 5,871.0 | 5,871.0 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 274.05 | 1,008.7 | 4,034.7 | weight_read | 5.82x | 1.46x | 30.48x | 5.82x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x14 | 11,410 | 2,249.7 | 4,499.4 | link_latency | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 260.01 | 1,526.3 | 1,526.3 | weight_read | 1.47x | 2.95x | 6.11x | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 5,869.1 | 11,738.2 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 274.05 | 1,008.7 | 4,034.7 | weight_read | 5.82x | 2.91x | 30.47x | 5.82x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x14 | 11,410 | 2,238.9 | 4,477.9 | link_latency | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 262.03 | 1,267.7 | 2,535.3 | weight_read | 1.77x | 1.77x | 6.08x | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 5,654.2 | 22,616.8 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 274.05 | 1,008.7 | 4,034.7 | weight_read | 5.61x | 5.61x | 29.36x | 5.61x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x14 | 11,410 | 1,610.0 | 6,440.1 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 266.05 | 978.9 | 3,915.7 | weight_read | 1.64x | 1.64x | 4.37x | 1.64x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 5,440.2 | 43,521.8 | link_latency | DSV4-Flash/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 1,355.86 | 604.5 | 4,836.4 | link_latency | 9.00x | 9.00x | 58.99x | 9.00x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x14 | 11,410 | 1,030.9 | 8,247.0 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 274.10 | 701.9 | 5,615.6 | weight_read | 1.47x | 1.47x | 2.95x | 1.47x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 5,092.3 | 81,476.4 | link_latency | DSV4-Flash/b200_sxm-x116-tensor | 185,600 | 1.00x | tensor | 1,696.12 | 486.4 | 7,782.9 | link_latency | 10.47x | 10.47x | 69.21x | 10.47x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 709.0 | 11,343.6 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 290.21 | 477.2 | 7,634.5 | weight_read | 1.49x | 1.49x | 2.75x | 1.49x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 4,603.0 | 147,295.9 | link_latency | DSV4-Flash/b200_sxm-x231-tensor | 369,600 | 1.00x | tensor | 2,403.77 | 361.9 | 11,582.1 | link_latency | 12.72x | 12.72x | 112.37x | 12.72x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 358.6 | 11,474.5 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 322.41 | 321.7 | 10,295.3 | weight_read | 1.11x | 1.11x | 2.03x | 1.11x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,971.5 | 254,175.9 | link_latency | DSV4-Flash/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 3,807.35 | 239.1 | 15,304.6 | link_latency | 16.61x | 16.61x | 140.19x | 16.61x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 180.3 | 11,541.0 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 386.83 | 228.6 | 14,627.9 | weight_read | 0.79x | 0.79x | 1.57x | 0.79x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,404.8 | 615,618.9 | link_latency | DSV4-Flash/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 498.99 | 122.4 | 31,345.3 | weight_read | 19.64x | 19.64x | 84.89x | 19.65x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 45.3 | 11,591.5 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 773.30 | 142.6 | 36,509.9 | weight_read | 0.32x | 0.32x | 0.95x | 0.32x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 2,653.6 | 2,653.6 | link_latency | DSV4-Pro/b200_sxm-x58-tensor | 92,800 | 1.00x | tensor | 1,560.92 | 479.8 | 479.8 | link_latency | 5.53x | 5.53x | 78.74x | 5.53x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x72 | 58,680 | 679.4 | 679.4 | compute | DSV4-Pro/b200_sxm-x37-tensor | 59,200 | 0.99x | tensor | 1,553.05 | 463.1 | 463.1 | link_latency | 1.47x | 1.47x | 14.95x | 1.47x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,632.5 | 7,897.6 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 1,665.00 | 440.2 | 880.4 | link_latency | 5.98x | 8.97x | 105.30x | 5.98x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 658.2 | 6,582.2 | compute | DSV4-Pro/b200_sxm-x38-tensor | 60,800 | 0.99x | tensor | 1,642.11 | 407.8 | 815.5 | link_latency | 1.61x | 8.07x | 14.73x | 1.61x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,632.1 | 10,528.3 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 1,866.00 | 371.6 | 1,486.6 | link_latency | 7.08x | 7.08x | 105.28x | 7.08x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 658.2 | 6,582.2 | compute | DSV4-Pro/b200_sxm-x38-tensor | 60,800 | 0.99x | tensor | 1,820.21 | 341.0 | 1,364.0 | link_latency | 1.93x | 4.83x | 14.73x | 1.93x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 2,595.7 | 20,765.9 | link_latency | DSV4-Pro/b200_sxm-x116-tensor | 185,600 | 1.00x | tensor | 2,288.36 | 304.1 | 2,432.6 | link_latency | 8.54x | 8.54x | 130.38x | 8.54x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 658.2 | 6,582.2 | compute | DSV4-Pro/b200_sxm-x38-tensor | 60,800 | 0.99x | tensor | 2,176.42 | 265.2 | 2,121.8 | link_latency | 2.48x | 3.10x | 14.73x | 2.48x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 2,463.0 | 39,407.8 | link_latency | DSV4-Pro/b200_sxm-x231-tensor | 369,600 | 1.00x | tensor | 3,166.75 | 236.0 | 3,776.4 | link_latency | 10.44x | 10.44x | 222.98x | 10.44x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 459.0 | 7,344.0 | compute | DSV4-Pro/b200_sxm-x38-tensor | 60,800 | 0.99x | tensor | 2,888.85 | 190.9 | 3,054.5 | link_latency | 2.40x | 2.40x | 10.27x | 2.40x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,281.1 | 72,994.8 | link_latency | DSV4-Pro/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 4,908.98 | 163.3 | 5,224.0 | link_latency | 13.97x | 13.97x | 298.98x | 13.97x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 254.0 | 8,127.9 | compute | DSV4-Pro/b200_sxm-x38-hybrid | 60,800 | 0.99x | hybrid | 423.99 | 134.3 | 4,297.2 | weight_read | 1.89x | 1.89x | 5.68x | 1.89x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,612.5 | 103,201.1 | kv_read | DSV4-Pro/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 8,353.97 | 101.1 | 6,469.4 | link_latency | 15.95x | 15.95x | 211.35x | 15.95x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 134.2 | 8,586.2 | compute | DSV4-Pro/b200_sxm-x38-hybrid | 60,800 | 0.99x | hybrid | 463.98 | 93.0 | 5,951.3 | weight_read | 1.44x | 1.44x | 3.76x | 1.44x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 584.6 | 149,645.3 | kv_read | DSV4-Pro/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 660.91 | 33.9 | 8,677.3 | weight_read | 17.25x | 17.25x | 76.62x | 17.25x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x74 | 60,310 | 35.6 | 9,119.3 | compute | DSV4-Pro/b200_sxm-x38-hybrid | 60,800 | 0.99x | hybrid | 703.90 | 43.2 | 11,052.1 | weight_read | 0.83x | 0.83x | 1.95x | 0.83x |

## Every hop latency in this model is assumed, so the headline is a band

NVIDIA publishes no NVLink or NVSwitch latency figure in any form,
and Cerebras publishes none for the on-wafer mesh or for SwarmX. The
table below re-runs the whole study with **every** assumed hop
latency at the low end of its stated range and again at the high end
-- on both sides at once, because a ratio is only tested by moving
both ends of it together. Where the band is wide the ratio is not a
number, it is an interval.

| Model | ROM mm2 | Ratio at low | Ratio stated | Ratio at high |
|---|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 11,410 | 1.59x | 1.47x | 1.18x |
| DeepSeek-V4-Flash-0731 | 46,225 | 11.63x | 5.82x | 2.40x |
| DeepSeek-V4-Flash-0731 | 92,450 | 12.18x | 6.83x | 2.94x |
| DeepSeek-V4-Flash-0731 | 138,675 | 11.88x | 6.58x | 2.90x |
| DeepSeek-V4-Flash-0731 | 184,900 | 11.66x | 6.37x | 2.86x |
| DeepSeek-V4-Flash-0731 | 277,350 | 11.30x | 6.01x | 2.77x |
| DeepSeek-V4-Flash-0731 | 369,800 | 11.00x | 5.70x | 2.70x |
| DeepSeek-V4-Flash-0731 | 554,700 | 10.46x | 5.19x | 2.56x |
| DeepSeek-V4-Pro-0813 | 58,680 | — | 1.47x | 1.39x |
| DeepSeek-V4-Pro-0813 | 60,310 | 1.60x | 1.68x | 1.51x |
| DeepSeek-V4-Pro-0813 | 61,940 | 1.59x | 1.68x | 1.51x |
| DeepSeek-V4-Pro-0813 | 92,450 | 7.32x | 5.53x | 2.96x |
| DeepSeek-V4-Pro-0813 | 138,675 | 7.15x | 5.36x | 2.90x |
| DeepSeek-V4-Pro-0813 | 184,900 | 7.02x | 5.23x | 2.85x |
| DeepSeek-V4-Pro-0813 | 277,350 | 6.86x | 5.03x | 2.78x |
| DeepSeek-V4-Pro-0813 | 369,800 | 6.76x | 4.88x | 2.72x |
| DeepSeek-V4-Pro-0813 | 554,700 | 6.60x | 4.62x | 2.62x |
| Qwen3-8B | 2,445 | 6.29x | 5.90x | 9.63x |
| Qwen3-8B | 3,260 | 6.45x | 5.15x | 6.31x |
| Qwen3-8B | 4,075 | — | 5.50x | 7.73x |
| Qwen3-8B | 5,705 | 4.60x | 4.45x | — |
| Qwen3-8B | 6,520 | 4.29x | 3.39x | — |
| Qwen3-8B | 46,225 | 10.99x | 4.81x | 2.15x |
| Qwen3-8B | 92,450 | 9.00x | 4.39x | 2.05x |
| Qwen3-8B | 138,675 | 7.32x | 3.85x | 1.96x |
| Qwen3-8B | 184,900 | 6.97x | 3.76x | 1.96x |
| Qwen3-8B | 277,350 | 7.06x | 3.70x | 1.95x |
| Qwen3-8B | 369,800 | 7.15x | 3.65x | 1.95x |
| Qwen3-8B | 554,700 | 7.15x | 3.47x | 1.90x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 8 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 8 | Link us at domain 72 | tok/s at 8 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 4 | 6,400 | 259.76 | 259.76 | 1,184.4 | 1,184.4 |
| DeepSeek-V4-Flash-0731 | 7 | 11,200 | 260.01 | 260.01 | 1,526.3 | 1,526.3 |
| DeepSeek-V4-Flash-0731 | 11 | 17,600 | 264.72 | 260.13 | 1,170.6 | 1,176.9 |
| DeepSeek-V4-Flash-0731 | 12 | 19,200 | 264.72 | 260.15 | 1,211.3 | 1,218.1 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 269.38 | 260.22 | 1,081.6 | 1,092.5 |
| DeepSeek-V4-Flash-0731 | 20 | 32,000 | 269.38 | 260.23 | 1,100.9 | 1,112.1 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 274.05 | 260.27 | 1,008.7 | 1,022.9 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 1,071.04 | 260.31 | 820.8 | 2,453.3 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 1,072.48 | 1,055.45 | 829.3 | 841.2 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 1,073.51 | 1,055.45 | 833.6 | 846.4 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 1,074.40 | 1,062.50 | 838.1 | 846.6 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 1,074.87 | 1,066.02 | 840.4 | 846.7 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 1,075.36 | 1,068.13 | 842.8 | 848.0 |
| DeepSeek-V4-Pro-0813 | 22 | 35,200 | 1,539.06 | 371.56 | 436.5 | 890.2 |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 1,547.81 | 371.63 | 451.6 | 963.3 |
| DeepSeek-V4-Pro-0813 | 37 | 59,200 | 1,553.05 | 371.67 | 463.1 | 1,022.7 |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 1,553.05 | 371.68 | 464.4 | 1,028.8 |
| DeepSeek-V4-Pro-0813 | 39 | 62,400 | 1,553.05 | 371.68 | 465.6 | 1,034.8 |
| DeepSeek-V4-Pro-0813 | 56 | 89,600 | 1,559.05 | 371.73 | 479.0 | 1,110.7 |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 1,560.92 | 371.73 | 479.8 | 1,117.4 |
| DeepSeek-V4-Pro-0813 | 60 | 96,000 | 1,560.92 | 371.73 | 481.0 | 1,123.7 |
| DeepSeek-V4-Pro-0813 | 68 | 108,800 | 1,562.38 | 371.74 | 484.7 | 1,146.0 |
| DeepSeek-V4-Pro-0813 | 81 | 129,600 | 1,564.50 | 1,522.22 | 489.2 | 499.5 |
| DeepSeek-V4-Pro-0813 | 84 | 134,400 | 1,564.50 | 1,522.22 | 490.1 | 500.5 |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 1,564.50 | 1,522.22 | 491.0 | 501.4 |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 1,567.04 | 1,522.22 | 496.8 | 508.2 |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 1,569.27 | 1,539.71 | 503.0 | 510.5 |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 1,570.42 | 1,548.45 | 506.2 | 511.9 |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 1,571.66 | 1,553.70 | 509.5 | 514.2 |
| Qwen3-8B | 2 | 3,200 | 216.98 | 216.98 | 641.8 | 641.8 |
| Qwen3-8B | 3 | 4,800 | 217.31 | 217.31 | 898.1 | 898.1 |
| Qwen3-8B | 4 | 6,400 | 217.47 | 217.47 | 1,122.3 | 1,122.3 |
| Qwen3-8B | 29 | 46,400 | 231.71 | 217.90 | 1,650.3 | 1,688.8 |
| Qwen3-8B | 58 | 92,800 | 250.37 | 217.93 | 1,601.0 | 1,688.7 |
| Qwen3-8B | 87 | 139,200 | 264.36 | 222.60 | 1,645.0 | 1,766.4 |
| Qwen3-8B | 116 | 185,600 | 283.01 | 222.60 | 1,576.8 | 1,742.8 |
| Qwen3-8B | 173 | 276,800 | 315.66 | 227.27 | 1,512.5 | 1,746.0 |
| Qwen3-8B | 231 | 369,600 | 348.31 | 231.93 | 1,450.4 | 1,745.0 |
| Qwen3-8B | 347 | 555,200 | 380.95 | 236.59 | 1,378.4 | 1,720.9 |

## The GPU's own topology choice, at batch 1

Every cluster size in the study, under each parallelism it can
actually run, at **per-user** rate. `pipeline` is what this study
charged the GPU before, at every size; `hybrid` is tensor-parallel
inside the NVLink domain and pipeline-parallel across it, which is
what a real deployment of this size runs. A blank cell is a topology
that collapses onto another at that size and is not emitted twice.

**This table is where the latency separation shows up most
plainly.** A pipeline column is now a machine cut into as many slots
as it has GPUs, and a token visits every one of them; the whole
cluster's HBM bandwidth is on that token's path only under `tensor`,
which is why a 672-GPU pipeline reads as fractions of a token per
second while the same silicon tensor-parallel reads in the hundreds.

| Model | GPUs | mm2 | Pipeline tok/s | Tensor tok/s | Hybrid tok/s | Best | Best link us | Link share | Binds on |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 4 | 6,400 | 432.2 | 1,184.4 | — | tensor | 259.76 | 30.8% | weight_read |
| DeepSeek-V4-Flash-0731 | 7 | 11,200 | 368.0 | 1,526.3 | — | tensor | 260.01 | 39.7% | weight_read |
| DeepSeek-V4-Flash-0731 | 11 | 17,600 | 310.8 | 738.1 | 1,170.6 | hybrid | 264.72 | 31.0% | weight_read |
| DeepSeek-V4-Flash-0731 | 12 | 19,200 | 299.7 | 746.0 | 1,211.3 | hybrid | 264.72 | 32.1% | weight_read |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 242.1 | 777.0 | 1,081.6 | hybrid | 269.38 | 29.1% | weight_read |
| DeepSeek-V4-Flash-0731 | 20 | 32,000 | 235.9 | 780.2 | 1,100.9 | hybrid | 269.38 | 29.7% | weight_read |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 192.6 | 798.5 | 1,008.7 | hybrid | 274.05 | 27.6% | weight_read |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 123.9 | 820.8 | 712.5 | tensor | 1,071.04 | 87.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 92.2 | 829.3 | 596.6 | tensor | 1,072.48 | 88.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 73.6 | 833.6 | 480.6 | tensor | 1,073.51 | 89.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 52.7 | 838.1 | 361.3 | tensor | 1,074.40 | 90.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 41.0 | 840.4 | 289.5 | tensor | 1,074.87 | 90.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 28.3 | 842.8 | 202.8 | tensor | 1,075.36 | 90.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 22 | 35,200 | 61.4 | 436.5 | 383.4 | tensor | 1,539.06 | 67.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 52.6 | 451.6 | 332.2 | tensor | 1,547.81 | 69.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 37 | 59,200 | 45.5 | 463.1 | 297.1 | tensor | 1,553.05 | 71.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 44.7 | 464.4 | 299.7 | tensor | 1,553.05 | 72.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 39 | 62,400 | 44.0 | 465.6 | 302.2 | tensor | 1,553.05 | 72.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 56 | 89,600 | 34.5 | 479.0 | 248.9 | tensor | 1,559.05 | 74.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 33.7 | 479.8 | 222.5 | tensor | 1,560.92 | 74.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 60 | 96,000 | 32.9 | 481.0 | 224.5 | tensor | 1,560.92 | 75.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 68 | 108,800 | 30.1 | 484.7 | 208.0 | tensor | 1,562.38 | 75.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 81 | 129,600 | 26.4 | 489.2 | 179.9 | tensor | 1,564.50 | 76.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 84 | 134,400 | 25.7 | 490.1 | 181.3 | tensor | 1,564.50 | 76.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 25.0 | 491.0 | 182.7 | tensor | 1,564.50 | 76.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 19.9 | 496.8 | 144.3 | tensor | 1,567.04 | 77.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 14.2 | 503.0 | 106.4 | tensor | 1,569.27 | 78.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 11.0 | 506.2 | 84.3 | tensor | 1,570.42 | 79.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 7.6 | 509.5 | 58.2 | tensor | 1,571.66 | 80.1% | link_latency |
| Qwen3-8B | 2 | 3,200 | 373.4 | 641.8 | — | tensor | 216.98 | 13.9% | weight_read |
| Qwen3-8B | 3 | 4,800 | 373.2 | 898.1 | — | tensor | 217.31 | 19.5% | weight_read |
| Qwen3-8B | 4 | 6,400 | 373.0 | 1,122.3 | — | tensor | 217.47 | 24.4% | weight_read |
| Qwen3-8B | 29 | 46,400 | 366.5 | 1,009.9 | 1,650.3 | hybrid | 231.71 | 38.2% | weight_read |
| Qwen3-8B | 58 | 92,800 | 364.7 | 1,054.2 | 1,601.0 | hybrid | 250.37 | 40.1% | weight_read |
| Qwen3-8B | 87 | 139,200 | 364.7 | 1,070.2 | 1,645.0 | hybrid | 264.36 | 43.5% | weight_read |
| Qwen3-8B | 116 | 185,600 | 364.7 | 1,078.0 | 1,576.8 | hybrid | 283.01 | 44.6% | weight_read |
| Qwen3-8B | 173 | 276,800 | 364.7 | 1,086.0 | 1,512.5 | hybrid | 315.66 | 47.7% | link_latency |
| Qwen3-8B | 231 | 369,600 | 364.7 | 1,090.2 | 1,450.4 | hybrid | 348.31 | 50.5% | link_latency |
| Qwen3-8B | 347 | 555,200 | 364.7 | 1,094.3 | 1,378.4 | hybrid | 380.95 | 52.5% | link_latency |

## Array or wafer: the crossover, reported rather than assumed

`Array viable to` is the per-user rate at which the topology's hops alone
consume 10% of the token budget; `hard ceiling` is the rate at which they
consume all of it. Below the first number the interconnect is a design
cost; above the second the topology cannot deliver the rate at all.

Each event is priced on the link it actually crosses and, for a
collective, on how many partitions it spans: an all-reduce costs
`traversals x hop latency` plus `(p-1)/p` of the payload each way, where
`traversals` is `2 lg p` in the fabric's own switch radix (Thakur,
Rabenseifner & Gropp 2005) or 1.1x the mesh diameter on a stitched
fabric (Rocki et al., SC20). `Events` spells the breakdown out.

| Design | Model | Devices | Parallelism | Intra link | Inter link | Hops/token | Link latency/token | Viable to (10% budget) | Hard ceiling | Events |
|---|---|---:|---|---|---|---:|---:|---:|---:|---|
| Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x3 | Qwen3-8B | 3 | pipeline | nvlink5 | infiniband_ndr | 2 | 3.02 us | 33,132.3 tok/s | 331,322.8 tok/s | 2 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.02 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 3.50 us | 28,571.3 tok/s | 285,713.4 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 3.50 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x3 | Qwen3-8B | 3 | tensor | nvlink5 | infiniband_ndr | 72 | 217.31 us | 460.2 tok/s | 4,601.7 tok/s | 72 x all_reduce span 3 on nvlink5 (traversals 2.0) = 217.31 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 110.88 us | 901.9 tok/s | 9,018.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 110.88 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | Qwen3-8B | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 4.53 us | 22,088.2 tok/s | 220,881.9 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 4.53 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 3.50 us | 28,571.3 tok/s | 285,713.4 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 3.50 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | Qwen3-8B | 4 | tensor | nvlink5 | infiniband_ndr | 72 | 217.47 us | 459.8 tok/s | 4,598.2 tok/s | 72 x all_reduce span 4 on nvlink5 (traversals 2.0) = 217.47 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 110.88 us | 901.9 tok/s | 9,018.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 110.88 us |
| Qwen3-8B/b200_sxm-x2-pipeline | Qwen3-8B | 2 | pipeline | nvlink5 | infiniband_ndr | 1 | 1.51 us | 66,264.6 tok/s | 662,645.6 tok/s | 1 x point_to_point span 2 on nvlink5 (traversals 1.0) = 1.51 us |
| Qwen3-8B/b200_sxm-x2-tensor | Qwen3-8B | 2 | tensor | nvlink5 | infiniband_ndr | 72 | 216.98 us | 460.9 tok/s | 4,608.7 tok/s | 72 x all_reduce span 2 on nvlink5 (traversals 2.0) = 216.98 us |
| Qwen3-8B/b200_sxm-x3-pipeline | Qwen3-8B | 3 | pipeline | nvlink5 | infiniband_ndr | 2 | 3.02 us | 33,132.3 tok/s | 331,322.8 tok/s | 2 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.02 us |
| Qwen3-8B/b200_sxm-x3-tensor | Qwen3-8B | 3 | tensor | nvlink5 | infiniband_ndr | 72 | 217.31 us | 460.2 tok/s | 4,601.7 tok/s | 72 x all_reduce span 3 on nvlink5 (traversals 2.0) = 217.31 us |
| Qwen3-8B/b200_sxm-x4-pipeline | Qwen3-8B | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 4.53 us | 22,088.2 tok/s | 220,881.9 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 4.53 us |
| Qwen3-8B/b200_sxm-x4-tensor | Qwen3-8B | 4 | tensor | nvlink5 | infiniband_ndr | 72 | 217.47 us | 459.8 tok/s | 4,598.2 tok/s | 72 x all_reduce span 4 on nvlink5 (traversals 2.0) = 217.47 us |
| Qwen3-8B/b200_sxm-x29-pipeline | Qwen3-8B | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 51.72 us | 1,933.5 tok/s | 19,335.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.73 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.99 us |
| Qwen3-8B/b200_sxm-x29-tensor | Qwen3-8B | 29 | tensor | nvlink5 | infiniband_ndr | 144 | 892.26 us | 112.1 tok/s | 1,120.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 674.54 us |
| Qwen3-8B/b200_sxm-x29-hybrid | Qwen3-8B | 29 | hybrid | nvlink5 | infiniband_ndr | 75 | 231.71 us | 431.6 tok/s | 4,315.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.99 us |
| Qwen3-8B/b200_sxm-x58-pipeline | Qwen3-8B | 58 | pipeline | nvlink5 | infiniband_ndr | 35 | 65.44 us | 1,528.2 tok/s | 15,281.8 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 46.78 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x58-tensor | Qwen3-8B | 58 | tensor | nvlink5 | infiniband_ndr | 144 | 896.69 us | 111.5 tok/s | 1,115.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 72 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 678.97 us |
| Qwen3-8B/b200_sxm-x58-hybrid | Qwen3-8B | 58 | hybrid | nvlink5 | infiniband_ndr | 79 | 250.37 us | 399.4 tok/s | 3,994.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.65 us |
| Qwen3-8B/b200_sxm-x87-pipeline | Qwen3-8B | 87 | pipeline | nvlink5 | infiniband_ndr | 35 | 65.44 us | 1,528.2 tok/s | 15,281.8 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 46.78 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x87-tensor | Qwen3-8B | 87 | tensor | nvlink5 | infiniband_ndr | 144 | 897.89 us | 111.4 tok/s | 1,113.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 72 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 680.17 us |
| Qwen3-8B/b200_sxm-x87-hybrid | Qwen3-8B | 87 | hybrid | nvlink5 | infiniband_ndr | 82 | 264.36 us | 378.3 tok/s | 3,782.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.64 us |
| Qwen3-8B/b200_sxm-x116-pipeline | Qwen3-8B | 116 | pipeline | nvlink5 | infiniband_ndr | 35 | 65.44 us | 1,528.2 tok/s | 15,281.8 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 46.78 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x116-tensor | Qwen3-8B | 116 | tensor | nvlink5 | infiniband_ndr | 144 | 898.75 us | 111.3 tok/s | 1,112.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 72 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 681.03 us |
| Qwen3-8B/b200_sxm-x116-hybrid | Qwen3-8B | 116 | hybrid | nvlink5 | infiniband_ndr | 86 | 283.01 us | 353.3 tok/s | 3,533.4 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 65.29 us |
| Qwen3-8B/b200_sxm-x173-pipeline | Qwen3-8B | 173 | pipeline | nvlink5 | infiniband_ndr | 35 | 65.44 us | 1,528.2 tok/s | 15,281.8 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 46.78 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x173-tensor | Qwen3-8B | 173 | tensor | nvlink5 | infiniband_ndr | 144 | 899.50 us | 111.2 tok/s | 1,111.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 72 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 681.78 us |
| Qwen3-8B/b200_sxm-x173-hybrid | Qwen3-8B | 173 | hybrid | nvlink5 | infiniband_ndr | 93 | 315.66 us | 316.8 tok/s | 3,168.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 97.94 us |
| Qwen3-8B/b200_sxm-x231-pipeline | Qwen3-8B | 231 | pipeline | nvlink5 | infiniband_ndr | 35 | 65.44 us | 1,528.2 tok/s | 15,281.8 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 46.78 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x231-tensor | Qwen3-8B | 231 | tensor | nvlink5 | infiniband_ndr | 144 | 899.89 us | 111.1 tok/s | 1,111.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 72 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 682.17 us |
| Qwen3-8B/b200_sxm-x231-hybrid | Qwen3-8B | 231 | hybrid | nvlink5 | infiniband_ndr | 100 | 348.31 us | 287.1 tok/s | 2,871.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 130.59 us |
| Qwen3-8B/b200_sxm-x347-pipeline | Qwen3-8B | 347 | pipeline | nvlink5 | infiniband_ndr | 35 | 65.44 us | 1,528.2 tok/s | 15,281.8 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 46.78 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x347-tensor | Qwen3-8B | 347 | tensor | nvlink5 | infiniband_ndr | 144 | 900.31 us | 111.1 tok/s | 1,110.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 72 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 682.59 us |
| Qwen3-8B/b200_sxm-x347-hybrid | Qwen3-8B | 347 | hybrid | nvlink5 | infiniband_ndr | 107 | 380.95 us | 262.5 tok/s | 2,625.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 217.72 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.23 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x14 | DeepSeek-V4-Flash-0731 | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 22.77 us | 4,391.2 tok/s | 43,911.5 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.11 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 4.20 us | 23,809.5 tok/s | 238,094.5 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.20 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x14 | DeepSeek-V4-Flash-0731 | 14 | tensor | nvlink5 | infiniband_ndr | 172 | 1,055.19 us | 94.8 tok/s | 947.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 795.14 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 132.44 us | 755.1 tok/s | 7,550.6 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 132.44 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x14 | DeepSeek-V4-Flash-0731 | 14 | hybrid | nvlink5 | infiniband_ndr | 87 | 264.72 us | 377.8 tok/s | 3,777.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | DeepSeek-V4-Flash-0731 | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 22.77 us | 4,391.2 tok/s | 43,911.5 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.11 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 4.20 us | 23,809.5 tok/s | 238,094.5 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.20 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x14 | DeepSeek-V4-Flash-0731 | 14 | tensor | nvlink5 | infiniband_ndr | 172 | 1,055.19 us | 94.8 tok/s | 947.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 795.14 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 132.44 us | 755.1 tok/s | 7,550.6 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 132.44 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x14 | DeepSeek-V4-Flash-0731 | 14 | hybrid | nvlink5 | infiniband_ndr | 87 | 264.72 us | 377.8 tok/s | 3,777.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x4-pipeline | DeepSeek-V4-Flash-0731 | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 4.53 us | 22,088.2 tok/s | 220,881.9 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 4.53 us |
| DSV4-Flash/b200_sxm-x4-tensor | DeepSeek-V4-Flash-0731 | 4 | tensor | nvlink5 | infiniband_ndr | 86 | 259.76 us | 385.0 tok/s | 3,849.7 tok/s | 86 x all_reduce span 4 on nvlink5 (traversals 2.0) = 259.76 us |
| DSV4-Flash/b200_sxm-x7-pipeline | DeepSeek-V4-Flash-0731 | 7 | pipeline | nvlink5 | infiniband_ndr | 6 | 9.05 us | 11,044.1 tok/s | 110,440.9 tok/s | 6 x point_to_point span 2 on nvlink5 (traversals 1.0) = 9.05 us |
| DSV4-Flash/b200_sxm-x7-tensor | DeepSeek-V4-Flash-0731 | 7 | tensor | nvlink5 | infiniband_ndr | 86 | 260.01 us | 384.6 tok/s | 3,846.0 tok/s | 86 x all_reduce span 7 on nvlink5 (traversals 2.0) = 260.01 us |
| DSV4-Flash/b200_sxm-x11-pipeline | DeepSeek-V4-Flash-0731 | 11 | pipeline | nvlink5 | infiniband_ndr | 10 | 18.25 us | 5,480.7 tok/s | 54,807.3 tok/s | 9 x point_to_point span 2 on nvlink5 (traversals 1.0) = 13.58 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x11-tensor | DeepSeek-V4-Flash-0731 | 11 | tensor | nvlink5 | infiniband_ndr | 172 | 1,055.19 us | 94.8 tok/s | 947.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 795.14 us |
| DSV4-Flash/b200_sxm-x11-hybrid | DeepSeek-V4-Flash-0731 | 11 | hybrid | nvlink5 | infiniband_ndr | 87 | 264.72 us | 377.8 tok/s | 3,777.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x12-pipeline | DeepSeek-V4-Flash-0731 | 12 | pipeline | nvlink5 | infiniband_ndr | 11 | 19.75 us | 5,062.0 tok/s | 50,620.4 tok/s | 10 x point_to_point span 2 on nvlink5 (traversals 1.0) = 15.09 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x12-tensor | DeepSeek-V4-Flash-0731 | 12 | tensor | nvlink5 | infiniband_ndr | 172 | 1,055.19 us | 94.8 tok/s | 947.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 795.14 us |
| DSV4-Flash/b200_sxm-x12-hybrid | DeepSeek-V4-Flash-0731 | 12 | hybrid | nvlink5 | infiniband_ndr | 87 | 264.72 us | 377.8 tok/s | 3,777.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink5 | infiniband_ndr | 18 | 33.47 us | 2,987.5 tok/s | 29,874.5 tok/s | 16 x point_to_point span 2 on nvlink5 (traversals 1.0) = 24.15 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.33 us |
| DSV4-Flash/b200_sxm-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink5 | infiniband_ndr | 172 | 1,062.24 us | 94.1 tok/s | 941.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 802.18 us |
| DSV4-Flash/b200_sxm-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink5 | infiniband_ndr | 88 | 269.38 us | 371.2 tok/s | 3,712.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.33 us |
| DSV4-Flash/b200_sxm-x20-pipeline | DeepSeek-V4-Flash-0731 | 20 | pipeline | nvlink5 | infiniband_ndr | 19 | 34.98 us | 2,858.6 tok/s | 28,585.8 tok/s | 17 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.33 us |
| DSV4-Flash/b200_sxm-x20-tensor | DeepSeek-V4-Flash-0731 | 20 | tensor | nvlink5 | infiniband_ndr | 172 | 1,062.24 us | 94.1 tok/s | 941.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 802.18 us |
| DSV4-Flash/b200_sxm-x20-hybrid | DeepSeek-V4-Flash-0731 | 20 | hybrid | nvlink5 | infiniband_ndr | 88 | 269.38 us | 371.2 tok/s | 3,712.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.33 us |
| DSV4-Flash/b200_sxm-x29-pipeline | DeepSeek-V4-Flash-0731 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 51.72 us | 1,933.5 tok/s | 19,335.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.73 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.99 us |
| DSV4-Flash/b200_sxm-x29-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5 | infiniband_ndr | 172 | 1,065.76 us | 93.8 tok/s | 938.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 805.70 us |
| DSV4-Flash/b200_sxm-x29-hybrid | DeepSeek-V4-Flash-0731 | 29 | hybrid | nvlink5 | infiniband_ndr | 89 | 274.05 us | 364.9 tok/s | 3,649.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.99 us |
| DSV4-Flash/b200_sxm-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 79.16 us | 1,263.3 tok/s | 12,633.3 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 55.84 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5 | infiniband_ndr | 172 | 1,071.04 us | 93.4 tok/s | 933.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 810.99 us |
| DSV4-Flash/b200_sxm-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink5 | infiniband_ndr | 93 | 292.70 us | 341.6 tok/s | 3,416.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.65 us |
| DSV4-Flash/b200_sxm-x87-pipeline | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink5 | infiniband_ndr | 42 | 79.16 us | 1,263.3 tok/s | 12,633.3 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 55.84 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x87-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5 | infiniband_ndr | 172 | 1,072.48 us | 93.2 tok/s | 932.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 812.43 us |
| DSV4-Flash/b200_sxm-x87-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5 | infiniband_ndr | 96 | 306.69 us | 326.1 tok/s | 3,260.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.64 us |
| DSV4-Flash/b200_sxm-x116-pipeline | DeepSeek-V4-Flash-0731 | 116 | pipeline | nvlink5 | infiniband_ndr | 42 | 79.16 us | 1,263.3 tok/s | 12,633.3 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 55.84 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x116-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5 | infiniband_ndr | 172 | 1,073.51 us | 93.2 tok/s | 931.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 813.45 us |
| DSV4-Flash/b200_sxm-x116-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5 | infiniband_ndr | 100 | 325.35 us | 307.4 tok/s | 3,073.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 65.29 us |
| DSV4-Flash/b200_sxm-x173-pipeline | DeepSeek-V4-Flash-0731 | 173 | pipeline | nvlink5 | infiniband_ndr | 42 | 79.16 us | 1,263.3 tok/s | 12,633.3 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 55.84 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x173-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5 | infiniband_ndr | 172 | 1,074.40 us | 93.1 tok/s | 930.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 814.35 us |
| DSV4-Flash/b200_sxm-x173-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5 | infiniband_ndr | 107 | 358.00 us | 279.3 tok/s | 2,793.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 97.94 us |
| DSV4-Flash/b200_sxm-x231-pipeline | DeepSeek-V4-Flash-0731 | 231 | pipeline | nvlink5 | infiniband_ndr | 42 | 79.16 us | 1,263.3 tok/s | 12,633.3 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 55.84 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x231-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5 | infiniband_ndr | 172 | 1,074.87 us | 93.0 tok/s | 930.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 814.81 us |
| DSV4-Flash/b200_sxm-x231-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5 | infiniband_ndr | 114 | 390.64 us | 256.0 tok/s | 2,559.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 130.59 us |
| DSV4-Flash/b200_sxm-x347-pipeline | DeepSeek-V4-Flash-0731 | 347 | pipeline | nvlink5 | infiniband_ndr | 42 | 79.16 us | 1,263.3 tok/s | 12,633.3 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 55.84 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x347-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5 | infiniband_ndr | 172 | 1,075.36 us | 93.0 tok/s | 929.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 86 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 815.31 us |
| DSV4-Flash/b200_sxm-x347-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5 | infiniband_ndr | 128 | 455.94 us | 219.3 tok/s | 2,193.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 260.05 us; 42 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.88 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x74 | DeepSeek-V4-Pro-0813 | 74 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4-Pro-0813 | 2 | pipeline | on_wafer | inter_wafer | 60 | 11.00 us | 9,094.5 tok/s | 90,945.4 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.90 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x72 | DeepSeek-V4-Pro-0813 | 72 | tensor | nvlink5 | infiniband_ndr | 244 | 1,562.38 us | 64.0 tok/s | 640.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 1,191.28 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4-Pro-0813 | 2 | tensor | on_wafer | inter_wafer | 244 | 1,425.37 us | 70.2 tok/s | 701.6 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 122 x all_reduce span 2 on inter_wafer (traversals 2.0) = 1,237.49 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x74 | DeepSeek-V4-Pro-0813 | 74 | hybrid | nvlink5 | infiniband_ndr | 131 | 414.18 us | 241.4 tok/s | 2,414.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 43.08 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4-Pro-0813 | 2 | hybrid | on_wafer | inter_wafer | 123 | 192.98 us | 518.2 tok/s | 5,182.0 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x76 | DeepSeek-V4-Pro-0813 | 76 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3 | DeepSeek-V4-Pro-0813 | 3 | pipeline | on_wafer | inter_wafer | 60 | 11.00 us | 9,094.5 tok/s | 90,945.4 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.90 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x74 | DeepSeek-V4-Pro-0813 | 74 | tensor | nvlink5 | infiniband_ndr | 244 | 1,563.55 us | 64.0 tok/s | 639.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 1,192.45 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer | inter_wafer | 244 | 1,431.20 us | 69.9 tok/s | 698.7 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 122 x all_reduce span 3 on inter_wafer (traversals 2.0) = 1,243.32 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x76 | DeepSeek-V4-Pro-0813 | 76 | hybrid | nvlink5 | infiniband_ndr | 131 | 414.18 us | 241.4 tok/s | 2,414.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 43.08 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | DeepSeek-V4-Pro-0813 | 3 | hybrid | on_wafer | inter_wafer | 124 | 198.07 us | 504.9 tok/s | 5,048.7 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 2 x point_to_point span 2 on inter_wafer (traversals 1.0) = 10.19 us |
| DSV4-Pro/b200_sxm-x22-pipeline | DeepSeek-V4-Pro-0813 | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 38.38 us | 2,605.8 tok/s | 26,057.9 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 28.80 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.57 us |
| DSV4-Pro/b200_sxm-x22-tensor | DeepSeek-V4-Pro-0813 | 22 | tensor | nvlink5 | infiniband_ndr | 244 | 1,539.06 us | 65.0 tok/s | 649.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 1,167.96 us |
| DSV4-Pro/b200_sxm-x22-hybrid | DeepSeek-V4-Pro-0813 | 22 | hybrid | nvlink5 | infiniband_ndr | 124 | 380.67 us | 262.7 tok/s | 2,626.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.57 us |
| DSV4-Pro/b200_sxm-x29-pipeline | DeepSeek-V4-Pro-0813 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 52.26 us | 1,913.6 tok/s | 19,135.7 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.90 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 14.36 us |
| DSV4-Pro/b200_sxm-x29-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5 | infiniband_ndr | 244 | 1,547.81 us | 64.6 tok/s | 646.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 1,176.70 us |
| DSV4-Pro/b200_sxm-x29-hybrid | DeepSeek-V4-Pro-0813 | 29 | hybrid | nvlink5 | infiniband_ndr | 125 | 385.46 us | 259.4 tok/s | 2,594.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 14.36 us |
| DSV4-Pro/b200_sxm-x37-pipeline | DeepSeek-V4-Pro-0813 | 37 | pipeline | nvlink5 | infiniband_ndr | 36 | 67.66 us | 1,478.1 tok/s | 14,780.5 tok/s | 32 x point_to_point span 2 on nvlink5 (traversals 1.0) = 48.51 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x37-tensor | DeepSeek-V4-Pro-0813 | 37 | tensor | nvlink5 | infiniband_ndr | 244 | 1,553.05 us | 64.4 tok/s | 643.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 1,181.95 us |
| DSV4-Pro/b200_sxm-x37-hybrid | DeepSeek-V4-Pro-0813 | 37 | hybrid | nvlink5 | infiniband_ndr | 126 | 390.25 us | 256.2 tok/s | 2,562.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x38-pipeline | DeepSeek-V4-Pro-0813 | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 69.17 us | 1,445.7 tok/s | 14,456.6 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.03 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x38-tensor | DeepSeek-V4-Pro-0813 | 38 | tensor | nvlink5 | infiniband_ndr | 244 | 1,553.05 us | 64.4 tok/s | 643.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 1,181.95 us |
| DSV4-Pro/b200_sxm-x38-hybrid | DeepSeek-V4-Pro-0813 | 38 | hybrid | nvlink5 | infiniband_ndr | 126 | 390.25 us | 256.2 tok/s | 2,562.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x39-pipeline | DeepSeek-V4-Pro-0813 | 39 | pipeline | nvlink5 | infiniband_ndr | 38 | 70.69 us | 1,414.7 tok/s | 14,146.6 tok/s | 34 x point_to_point span 2 on nvlink5 (traversals 1.0) = 51.54 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x39-tensor | DeepSeek-V4-Pro-0813 | 39 | tensor | nvlink5 | infiniband_ndr | 244 | 1,553.05 us | 64.4 tok/s | 643.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 1,181.95 us |
| DSV4-Pro/b200_sxm-x39-hybrid | DeepSeek-V4-Pro-0813 | 39 | hybrid | nvlink5 | infiniband_ndr | 126 | 390.25 us | 256.2 tok/s | 2,562.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink5 | infiniband_ndr | 55 | 103.00 us | 970.9 tok/s | 9,708.7 tok/s | 49 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.28 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 28.72 us |
| DSV4-Pro/b200_sxm-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink5 | infiniband_ndr | 244 | 1,559.05 us | 64.1 tok/s | 641.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 1,187.95 us |
| DSV4-Pro/b200_sxm-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink5 | infiniband_ndr | 128 | 399.82 us | 250.1 tok/s | 2,501.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 28.72 us |
| DSV4-Pro/b200_sxm-x58-pipeline | DeepSeek-V4-Pro-0813 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 109.30 us | 914.9 tok/s | 9,148.8 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 75.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x58-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5 | infiniband_ndr | 244 | 1,560.92 us | 64.1 tok/s | 640.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 1,189.82 us |
| DSV4-Pro/b200_sxm-x58-hybrid | DeepSeek-V4-Pro-0813 | 58 | hybrid | nvlink5 | infiniband_ndr | 129 | 404.61 us | 247.2 tok/s | 2,471.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x60-pipeline | DeepSeek-V4-Pro-0813 | 60 | pipeline | nvlink5 | infiniband_ndr | 59 | 112.34 us | 890.2 tok/s | 8,901.9 tok/s | 52 x point_to_point span 2 on nvlink5 (traversals 1.0) = 78.83 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x60-tensor | DeepSeek-V4-Pro-0813 | 60 | tensor | nvlink5 | infiniband_ndr | 244 | 1,560.92 us | 64.1 tok/s | 640.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 1,189.82 us |
| DSV4-Pro/b200_sxm-x60-hybrid | DeepSeek-V4-Pro-0813 | 60 | hybrid | nvlink5 | infiniband_ndr | 129 | 404.61 us | 247.2 tok/s | 2,471.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x68-pipeline | DeepSeek-V4-Pro-0813 | 68 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x68-tensor | DeepSeek-V4-Pro-0813 | 68 | tensor | nvlink5 | infiniband_ndr | 244 | 1,562.38 us | 64.0 tok/s | 640.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 1,191.28 us |
| DSV4-Pro/b200_sxm-x68-hybrid | DeepSeek-V4-Pro-0813 | 68 | hybrid | nvlink5 | infiniband_ndr | 130 | 409.39 us | 244.3 tok/s | 2,442.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 38.29 us |
| DSV4-Pro/b200_sxm-x81-pipeline | DeepSeek-V4-Pro-0813 | 81 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x81-tensor | DeepSeek-V4-Pro-0813 | 81 | tensor | nvlink5 | infiniband_ndr | 244 | 1,564.50 us | 63.9 tok/s | 639.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 1,193.40 us |
| DSV4-Pro/b200_sxm-x81-hybrid | DeepSeek-V4-Pro-0813 | 81 | hybrid | nvlink5 | infiniband_ndr | 132 | 418.97 us | 238.7 tok/s | 2,386.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.87 us |
| DSV4-Pro/b200_sxm-x84-pipeline | DeepSeek-V4-Pro-0813 | 84 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x84-tensor | DeepSeek-V4-Pro-0813 | 84 | tensor | nvlink5 | infiniband_ndr | 244 | 1,564.50 us | 63.9 tok/s | 639.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 1,193.40 us |
| DSV4-Pro/b200_sxm-x84-hybrid | DeepSeek-V4-Pro-0813 | 84 | hybrid | nvlink5 | infiniband_ndr | 132 | 418.97 us | 238.7 tok/s | 2,386.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.87 us |
| DSV4-Pro/b200_sxm-x87-pipeline | DeepSeek-V4-Pro-0813 | 87 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x87-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5 | infiniband_ndr | 244 | 1,564.50 us | 63.9 tok/s | 639.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 1,193.40 us |
| DSV4-Pro/b200_sxm-x87-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5 | infiniband_ndr | 132 | 418.97 us | 238.7 tok/s | 2,386.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.87 us |
| DSV4-Pro/b200_sxm-x116-pipeline | DeepSeek-V4-Pro-0813 | 116 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x116-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5 | infiniband_ndr | 244 | 1,567.04 us | 63.8 tok/s | 638.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 1,195.94 us |
| DSV4-Pro/b200_sxm-x116-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5 | infiniband_ndr | 136 | 438.12 us | 228.3 tok/s | 2,282.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 67.01 us |
| DSV4-Pro/b200_sxm-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5 | infiniband_ndr | 244 | 1,569.27 us | 63.7 tok/s | 637.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 1,198.17 us |
| DSV4-Pro/b200_sxm-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5 | infiniband_ndr | 143 | 471.62 us | 212.0 tok/s | 2,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 100.52 us |
| DSV4-Pro/b200_sxm-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5 | infiniband_ndr | 244 | 1,570.42 us | 63.7 tok/s | 636.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 1,199.32 us |
| DSV4-Pro/b200_sxm-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5 | infiniband_ndr | 150 | 505.13 us | 198.0 tok/s | 1,979.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 134.03 us |
| DSV4-Pro/b200_sxm-x347-pipeline | DeepSeek-V4-Pro-0813 | 347 | pipeline | nvlink5 | infiniband_ndr | 60 | 113.85 us | 878.3 tok/s | 8,783.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 80.34 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x347-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5 | infiniband_ndr | 244 | 1,571.66 us | 63.6 tok/s | 636.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 122 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 1,200.55 us |
| DSV4-Pro/b200_sxm-x347-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5 | infiniband_ndr | 165 | 576.93 us | 173.3 tok/s | 1,733.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 371.10 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 205.83 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 7,936.4 | 0.172 | 4,935.4 (4,075) | 7,936.4 (46,225) | 1.61x | link_latency |
| Qwen3-8B | 2 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 6,308.8 | 0.068 | 3,286.8 (6,520) | 6,308.8 (92,450) | 1.92x | link_latency |
| Qwen3-8B | 4 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 5,687.0 | 0.041 | 3,065.4 (3,260) | 5,687.0 (138,675) | 1.86x | link_latency |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 5,234.0 | 0.019 | 3,009.7 (6,520) | 5,234.0 (277,350) | 1.74x | link_latency |
| Qwen3-8B | 16 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 4,425.9 | 0.012 | 1,542.8 (6,520) | 4,425.9 (369,800) | 2.87x | link_latency |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,686.4 | 0.007 | 781.3 (6,520) | 3,686.4 (554,700) | 4.72x | link_latency |
| Qwen3-8B | 64 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,696.8 | 0.005 | 393.1 (6,520) | 2,696.8 (554,700) | 6.86x | kv_read |
| Qwen3-8B | 256 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,033.0 | 0.002 | 98.8 (6,520) | 1,033.0 (554,700) | 10.46x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 5,871.0 | 0.127 | 2,249.7 (11,410) | 5,871.0 (46,225) | 2.61x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 5,869.1 | 0.127 | 2,238.9 (11,410) | 5,869.1 (46,225) | 2.62x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 5,654.2 | 0.122 | 1,610.0 (11,410) | 5,654.2 (46,225) | 3.51x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 5,378.1 | 0.058 | 1,030.9 (11,410) | 5,378.1 (92,450) | 5.22x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,897.8 | 0.035 | 709.0 (11,410) | 4,897.8 (138,675) | 6.91x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 4,544.5 | 0.016 | 358.6 (11,410) | 4,544.5 (277,350) | 12.67x | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,885.2 | 0.011 | 180.3 (11,410) | 3,885.2 (369,800) | 21.55x | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,404.8 | 0.004 | 45.3 (11,410) | 2,404.8 (554,700) | 53.11x | link_latency |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 2,653.6 | 0.029 | 782.2 (60,310) | 2,653.6 (92,450) | 3.39x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,632.5 | 0.019 | 782.2 (61,940) | 2,632.5 (138,675) | 3.37x | link_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,632.1 | 0.019 | 782.2 (61,940) | 2,632.1 (138,675) | 3.37x | link_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,556.9 | 0.018 | 782.2 (61,940) | 2,556.9 (138,675) | 3.27x | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 2,457.9 | 0.009 | 603.5 (61,940) | 2,457.9 (277,350) | 4.07x | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,281.1 | 0.004 | 345.6 (61,940) | 2,281.1 (554,700) | 6.60x | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,612.5 | 0.003 | 186.3 (61,940) | 1,612.5 (554,700) | 8.66x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 584.6 | 0.001 | 50.7 (61,940) | 584.6 (554,700) | 11.53x | kv_read |

## The two ROM floorplans on one die

Both machines hold the same 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. They are different floorplans, not one floorplan with two arithmetics.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 168.6 mm2 | 269.8 mm2 |
| compute block | 499.7 mm2 | 16.3 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 382.2 mm2 |
| sustained fp8 compute roof | 3.737e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.868e+14 | n/a |
| weight bytes/s the array supplies | 4.589e+13 | 4.589e+13 |
| **can the compute block be fed?** | **0.25x** | there is nothing to feed |
| full-array sweep | 76.55 us | 76.55 us |

**The sweep is identical.** Both the capacity density and the
read-bandwidth density scale as one over bitcell area, so a larger
compute-in-ROM cell holds proportionally fewer bits AND delivers
proportionally fewer bytes per second: the cell size cancels in
their ratio. What the larger cell costs is capacity -- the same
weights need a bigger array, and that silicon comes out of the SRAM
beside it. An earlier version of this model applied the multiplier
to area alone and credited the result with the storage cell's
bandwidth density, which handed compute-in-ROM a free 1.6x on throughput.

What compute-in-ROM does buy on this die is that it has no MAC
array to starve: the storage machine's 500 mm2 of MAC array can be fed at only 0.25x of what it
wants at one weight byte per multiply-accumulate, so more than half
the die runs at a fraction of its duty and the step is weight-bound
anyway.

## Sizing one expert region

The per-region machine's cost is not arithmetic; it is a
pre-compute block and an activation distribution network per
region. The block is small against the array it serves. The
distribution network is the real cost and this model does not
price it.

| Model | Experts | Routed bytes/expert | One region | Pre-compute/region | All regions | All pre-compute | Whole checkpoint |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 44.2 mm2 | 0.88 mm2 (2.0%) | 11,303 mm2 | 226 mm2 | 12,816 mm2 = 15.7 reticles |
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 164.4 mm2 | 3.29 mm2 (2.0%) | 63,134 mm2 | 1,263 mm2 | 68,561 mm2 = 84.1 reticles |

## The batch-amortisation fork, reported rather than resolved

`docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` names an open
question the anchor cannot settle. If a ROM cell both stores its bits
and performs the multiply for them -- compute-in-ROM, as Taalas
describes HC1 -- then a second concurrent stream needs a second pass
through the fabric, and **aggregate per-die throughput equals per-user
throughput at every batch**. If instead the ROM is storage feeding a
separate MAC array, one sweep serves the whole batch exactly as one HBM
fetch does on a GPU. The two are *identical at batch 1*, which is
precisely why the published 16,960 tok/s figure cannot distinguish
them, and why it must not be used to justify a high-batch claim.

Every other table in this report uses the batched (ROM-as-storage)
machine; `-perstream` is compute-in-ROM with a global activation broadcast and `-perregion` gives each expert region its own port
variant.

The third column set is the per-region machine, which is the whole
subject of `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`: its sweep depth
is the load of the **busiest** expert region, computed from the routing
distribution rather than from the mean engaged region.

| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | Per-region aggregate | Per-stream penalty | Per-region over broadcast | Batched binds on | Per-stream binds on | Per-region binds on |
|---|---:|---|---:|---:|---:|---:|---:|---|---|---|
| Qwen3-8B | 1 | sram | 13,034.9 | 13,034.9 | 13,034.9 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 13,034.9 | 13,034.9 | 13,034.9 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 16,068.0 | 13,034.9 | 13,034.9 | 1.23x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 27,391.3 | 13,034.9 | 13,034.9 | 2.10x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 41,831.6 | 13,034.9 | 13,034.9 | 3.21x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 67,614.2 | 13,034.9 | 13,034.9 | 5.19x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 97,711.0 | 13,038.0 | 13,038.0 | 7.49x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 212,404.1 | 13,056.6 | 13,056.6 | 16.27x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 325,283.8 | 30,104.6 | 30,104.6 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 325,283.8 | 30,104.6 | 30,104.6 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 325,283.8 | 30,104.6 | 30,104.6 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 325,283.8 | 30,104.6 | 30,104.6 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 325,283.8 | 30,104.6 | 30,104.6 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 325,283.8 | 30,104.6 | 30,104.6 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 325,283.8 | 30,120.9 | 30,120.9 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 325,283.8 | 30,220.6 | 30,220.6 | 10.76x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 13,021.5 | 13,021.5 | 13,021.5 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 13,021.5 | 13,021.5 | 13,021.5 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 18,292.8 | 13,021.5 | 15,240.6 | 1.40x | 1.17x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | sram | 36,585.6 | 13,021.5 | 26,191.7 | 2.81x | 2.01x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 56,918.5 | 13,021.5 | 44,096.3 | 4.37x | 3.39x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 100,595.9 | 13,021.5 | 71,060.4 | 7.73x | 5.46x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 156,242.4 | 13,026.0 | 108,750.6 | 11.99x | 8.35x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 371,489.0 | 13,053.6 | 114,472.9 | 28.46x | 8.77x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 379,058.9 | 36,918.5 | 36,918.5 | 10.27x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 379,058.9 | 36,918.5 | 36,918.5 | 10.27x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 379,058.9 | 36,918.5 | 36,918.5 | 10.27x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 379,058.9 | 36,918.5 | 37,805.8 | 10.27x | 1.02x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | rom | 379,058.9 | 36,918.5 | 56,918.5 | 10.27x | 1.54x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 379,058.9 | 36,918.5 | 76,173.1 | 10.27x | 2.06x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 379,058.9 | 36,954.8 | 91,680.0 | 10.26x | 2.48x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 615,618.9 | 37,178.2 | 157,915.0 | 16.56x | 4.25x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 11,751.6 | 11,736.6 | 11,736.6 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 11,751.6 | 11,736.6 | 11,736.6 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 11,751.6 | 11,736.6 | 11,736.6 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 17,119.1 | 11,736.6 | 15,488.3 | 1.46x | 1.32x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 28,673.3 | 11,736.6 | 25,105.6 | 2.44x | 2.14x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 43,270.7 | 11,736.6 | 34,427.3 | 3.69x | 2.93x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 69,380.4 | 11,736.6 | 38,850.0 | 5.91x | 3.31x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 149,645.3 | 11,743.2 | 64,890.1 | 12.74x | 5.53x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 71,224.5 | 25,001.3 | 25,001.3 | 2.85x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 71,224.5 | 25,001.3 | 25,001.3 | 2.85x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 71,224.5 | 25,001.3 | 25,001.3 | 2.85x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 71,224.5 | 25,001.3 | 25,001.3 | 2.85x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 71,224.5 | 25,001.3 | 32,907.6 | 2.85x | 1.32x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 72,994.8 | 25,001.3 | 42,339.7 | 2.92x | 1.69x | link_latency | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 103,201.1 | 25,001.3 | 49,422.5 | 4.13x | 1.98x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 149,645.3 | 25,009.0 | 74,873.3 | 5.98x | 2.99x | kv_read | weight_read | weight_read |

## The floorplan sweep: where the recovered silicon goes

Compute-in-ROM has no MAC array, so it recovers that silicon.
What it is spent on decides the comparison, so it is swept
rather than assumed, and **the same sweep is offered to the
amortising machine** -- offering it to one side only would move
the artefact rather than remove it.

* `sram` sizes the array to the stored bytes. Compute-in-ROM's
  spare silicon becomes KV store, which is the split Taalas
  describes; the amortising machine's becomes MAC array.
* `rom` grows the array into that silicon as **replicated copies
  of the same weights**. R copies carry R sets of bitlines and
  sense amps, so R disjoint slices of the weight set are read at
  once and the sweep time falls by R. On the amortising machine
  the MAC array is then sized to consume exactly what the array
  can read, at one weight byte per multiply-accumulate -- a
  derived split, not a swept one.

`R` is the replication factor the design ended up with, which is
`weight_capacity / stored`. **Areas differ down this table**, so
read `tok/s/mm2` and not only aggregate: a design is allowed to
buy throughput with silicon here, and the iso-area table above is
where that is controlled for.

| Model | B | Amortisation | Spare | Design | mm2 | R | Sweeps | Aggregate | tok/s/mm2 | Binds on | vs ROM+MAC/sram |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---:|
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,283.8 | 0.586 | kv_read | 24.95x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 2.31x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 2.31x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,283.8 | 0.586 | kv_read | 24.95x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 2.31x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 2.31x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 16,068.0 | 0.348 | kv_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,283.8 | 0.586 | kv_read | 20.24x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.81x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 1.87x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.81x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 1.87x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 27,391.3 | 0.296 | weight_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,283.8 | 0.586 | kv_read | 11.88x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.48x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 1.10x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.48x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 1.10x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 41,831.6 | 0.302 | weight_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,283.8 | 0.586 | kv_read | 7.78x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.31x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 0.72x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.31x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 0.72x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 67,614.2 | 0.366 | weight_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,283.8 | 0.586 | kv_read | 4.81x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.19x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 0.45x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.19x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,104.6 | 0.651 | kv_read | 0.45x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 97,711.0 | 0.352 | weight_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,283.8 | 0.586 | kv_read | 3.33x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 13,038.0 | 0.282 | weight_read | 0.13x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.12 | 30,120.9 | 0.652 | kv_read | 0.31x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 13,038.0 | 0.282 | weight_read | 0.13x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.12 | 30,120.9 | 0.652 | kv_read | 0.31x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 212,404.1 | 0.383 | weight_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,283.8 | 0.586 | kv_read | 1.53x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 13,056.6 | 0.282 | weight_read | 0.06x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 4.49 | 30,220.6 | 0.654 | kv_read | 0.14x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.49 | 13,056.6 | 0.282 | weight_read | 0.06x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 4.49 | 30,220.6 | 0.654 | kv_read | 0.14x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 379,058.9 | 0.683 | weight_read | 29.11x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,918.5 | 0.799 | weight_read | 2.84x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.85 | 1.00 | 36,918.5 | 0.799 | weight_read | 2.84x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 379,058.9 | 0.683 | weight_read | 29.11x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,918.5 | 0.799 | weight_read | 2.84x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.85 | 1.00 | 36,918.5 | 0.799 | weight_read | 2.84x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 18,292.8 | 0.396 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 379,058.9 | 0.683 | weight_read | 20.72x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 0.71x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,918.5 | 0.799 | weight_read | 2.02x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 1.57 | 15,240.6 | 0.330 | link_latency | 0.83x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.85 | 1.00 | 36,918.5 | 0.799 | weight_read | 2.02x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 36,585.6 | 0.791 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 379,058.9 | 0.683 | weight_read | 10.36x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 0.36x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,918.5 | 0.799 | weight_read | 1.01x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.13 | 26,191.7 | 0.567 | weight_read | 0.72x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.85 | 2.13 | 37,805.8 | 0.818 | link_latency | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 56,918.5 | 1.231 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 379,058.9 | 0.683 | weight_read | 6.66x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,918.5 | 0.799 | weight_read | 0.65x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.88 | 44,096.3 | 0.954 | weight_read | 0.77x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.85 | 2.88 | 56,918.5 | 1.231 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 100,595.9 | 1.088 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 379,058.9 | 0.683 | weight_read | 3.77x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 0.13x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,918.5 | 0.799 | weight_read | 0.37x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.03 | 71,060.4 | 1.537 | weight_read | 0.71x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.85 | 4.03 | 76,173.1 | 1.648 | kv_read | 0.76x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 156,242.4 | 1.127 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 379,058.9 | 0.683 | weight_read | 2.43x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 13,026.0 | 0.282 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.12 | 36,954.8 | 0.799 | weight_read | 0.24x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 5.83 | 108,750.6 | 2.353 | weight_read | 0.70x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.85 | 5.83 | 91,680.0 | 1.983 | kv_read | 0.59x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 371,489.0 | 1.339 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 32.49 | 1.00 | 615,618.9 | 1.110 | link_latency | 1.66x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 13,053.6 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 4.49 | 37,178.2 | 0.804 | weight_read | 0.10x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x22-perregion | 17,930 | 1.00 | 6.88 | 114,472.9 | 6.384 | weight_read | 0.31x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x39-perregion-romfill | 31,785 | 1.83 | 5.15 | 157,915.0 | 4.968 | weight_read | 0.43x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.6 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,224.5 | 0.128 | weight_read | 6.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.6 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,224.5 | 0.128 | weight_read | 6.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.6 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,224.5 | 0.128 | weight_read | 6.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 17,119.1 | 0.123 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,224.5 | 0.128 | weight_read | 4.16x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 0.69x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 1.46x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 1.19 | 15,488.3 | 0.112 | weight_read | 0.90x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 1.46x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 28,673.3 | 0.155 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,224.5 | 0.128 | weight_read | 2.48x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 0.41x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 0.87x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 1.66 | 25,105.6 | 0.181 | weight_read | 0.88x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 2.13 | 1.43 | 32,907.6 | 0.178 | kv_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 43,270.7 | 0.156 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 6.07 | 1.00 | 72,994.8 | 0.132 | link_latency | 1.69x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 0.27x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 0.58x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.18 | 34,427.3 | 0.248 | kv_read | 0.80x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 2.13 | 1.99 | 42,339.7 | 0.229 | kv_read | 0.98x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 69,380.4 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 6.07 | 1.00 | 103,201.1 | 0.186 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,736.6 | 0.085 | weight_read | 0.17x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 25,001.3 | 0.135 | weight_read | 0.36x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.93 | 38,850.0 | 0.280 | kv_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 2.13 | 2.54 | 49,422.5 | 0.267 | kv_read | 0.71x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 149,645.3 | 0.270 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 6.07 | 1.00 | 149,645.3 | 0.270 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.50 | 11,743.2 | 0.085 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.13 | 25,009.0 | 0.135 | weight_read | 0.17x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x114-perregion | 92,910 | 1.00 | 2.62 | 64,890.1 | 0.698 | weight_read | 0.43x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x164-perregion-romfill | 133,660 | 1.44 | 2.27 | 74,873.3 | 0.560 | weight_read | 0.50x |

## What the completeness corrections cost

Four terms the model priced wrongly or not at all. Each row is
computed from the evaluated points, not restated from prose.

### 1. Per-region sweep depth: the busiest region, not the mean

The compute-in-ROM per-region machine used to charge `batch * k /
(N * coverage)` -- the load of the AVERAGE engaged region -- and then
divide it by a flat 0.85 whose own note said the depth is set by the
busiest region. The busiest region is now computed from the routing
distribution. The correction is not a constant: it is a function of
how many users one array pass actually serves.

**Read the `Users per slot` column, not the batch.** Since per-user
latency was separated from aggregate throughput, a machine cut into
`token_slots` slots spreads its batch across them, and the region
collisions this correction is about happen inside **one** slot. Where
the design the sweep chose has more slots than the batch has users, one
pass serves one user, no two tokens can collide on a region, and the
correction is 1.00x by construction rather than by accident. The
statistic itself is unchanged and is checked against a Monte Carlo of
the routing in `tests/test_roofline.py`; what moved is which point on it
these designs sit at.

| Model | B | Slots | Users per slot | Mean engaged region | Busiest region | Correction |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 1 | 3 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 3 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 57 | 1.12 | 1.123 | 1.123 | 1.00x |
| Qwen3-8B | 256 | 4 | 64.00 | 64.000 | 64.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 21 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 21 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 57 | 1.12 | 1.001 | 1.014 | 1.01x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 11.64 | 1.131 | 2.460 | 2.18x |
| DeepSeek-V4-Pro-0813 | 1 | 110 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 114 | 2.25 | 1.010 | 1.128 | 1.12x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 8 | 4 | 3.87 | 2.62 | 1.47x |
| DeepSeek-V4-Flash-0731 | 16 | 4 | 3.99 | 2.91 | 1.37x |
| DeepSeek-V4-Flash-0731 | 32 | 4 | 4.00 | 3.15 | 1.27x |
| DeepSeek-V4-Flash-0731 | 64 | 4 | 4.00 | 3.33 | 1.20x |
| DeepSeek-V4-Flash-0731 | 256 | 4 | 4.00 | 3.55 | 1.13x |
| DeepSeek-V4-Flash-0731 | 1 | 7 | 4.22 | 2.86 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 7 | 4.22 | 2.86 | 1.47x |
| DeepSeek-V4-Flash-0731 | 4 | 7 | 4.22 | 2.86 | 1.47x |
| DeepSeek-V4-Flash-0731 | 8 | 7 | 4.56 | 2.98 | 1.53x |
| DeepSeek-V4-Flash-0731 | 16 | 7 | 6.13 | 3.59 | 1.71x |
| DeepSeek-V4-Flash-0731 | 32 | 7 | 6.88 | 4.18 | 1.65x |
| DeepSeek-V4-Flash-0731 | 64 | 7 | 7.00 | 4.71 | 1.48x |
| DeepSeek-V4-Flash-0731 | 256 | 7 | 7.00 | 5.48 | 1.28x |
| DeepSeek-V4-Flash-0731 | 1 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 2 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 8 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 16 | 11 | 6.19 | 3.78 | 1.64x |
| DeepSeek-V4-Flash-0731 | 32 | 11 | 8.84 | 4.72 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 11 | 10.53 | 5.67 | 1.86x |
| DeepSeek-V4-Flash-0731 | 256 | 11 | 11.00 | 7.32 | 1.50x |
| DeepSeek-V4-Flash-0731 | 1 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 8 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 16 | 12 | 6.00 | 3.78 | 1.59x |
| DeepSeek-V4-Flash-0731 | 32 | 12 | 8.94 | 4.77 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 12 | 11.15 | 5.81 | 1.92x |
| DeepSeek-V4-Flash-0731 | 256 | 12 | 12.00 | 7.67 | 1.56x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 7.95 | 4.78 | 1.66x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 12.44 | 6.24 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 18.57 | 9.38 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 2 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 4 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 8 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 16 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 32 | 20 | 7.73 | 4.75 | 1.63x |
| DeepSeek-V4-Flash-0731 | 64 | 20 | 12.34 | 6.25 | 1.97x |
| DeepSeek-V4-Flash-0731 | 256 | 20 | 19.36 | 9.54 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 6.01 | 4.50 | 1.34x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 10.66 | 6.08 | 1.75x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 23.69 | 10.39 | 2.28x |
| DeepSeek-V4-Flash-0731 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 4 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 8 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 16 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 32 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 64 | 58 | 6.30 | 5.21 | 1.21x |
| DeepSeek-V4-Flash-0731 | 256 | 58 | 20.74 | 10.34 | 2.01x |
| DeepSeek-V4-Flash-0731 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 8 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 16 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 32 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 64 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 256 | 87 | 15.73 | 9.34 | 1.68x |
| DeepSeek-V4-Flash-0731 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 256 | 116 | 12.40 | 8.75 | 1.42x |
| DeepSeek-V4-Flash-0731 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 4 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 8 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 16 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 32 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 64 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 256 | 173 | 8.63 | 7.48 | 1.15x |
| DeepSeek-V4-Flash-0731 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 4 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 8 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 16 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 32 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 64 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 256 | 231 | 6.56 | 6.17 | 1.06x |
| DeepSeek-V4-Flash-0731 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 2 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 8 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 16 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 32 | 22 | 7.32 | 4.70 | 1.56x |
| DeepSeek-V4-Pro-0813 | 64 | 22 | 12.11 | 6.27 | 1.93x |
| DeepSeek-V4-Pro-0813 | 256 | 22 | 20.89 | 9.93 | 2.10x |
| DeepSeek-V4-Pro-0813 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 2 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 8 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 16 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 32 | 29 | 6.01 | 4.50 | 1.34x |
| DeepSeek-V4-Pro-0813 | 64 | 29 | 10.70 | 6.10 | 1.75x |
| DeepSeek-V4-Pro-0813 | 256 | 29 | 23.96 | 10.50 | 2.28x |
| DeepSeek-V4-Pro-0813 | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 2 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 8 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 16 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 32 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 64 | 37 | 9.11 | 5.85 | 1.56x |
| DeepSeek-V4-Pro-0813 | 256 | 37 | 24.51 | 10.72 | 2.29x |
| DeepSeek-V4-Pro-0813 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 2 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 8 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 16 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 32 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 64 | 38 | 8.93 | 5.82 | 1.53x |
| DeepSeek-V4-Pro-0813 | 256 | 38 | 24.44 | 10.72 | 2.28x |
| DeepSeek-V4-Pro-0813 | 1 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 2 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 4 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 8 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 16 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 32 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 64 | 39 | 8.76 | 5.80 | 1.51x |
| DeepSeek-V4-Pro-0813 | 256 | 39 | 24.36 | 10.72 | 2.27x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 21.37 | 10.48 | 2.04x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 6.30 | 5.21 | 1.21x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 20.96 | 10.41 | 2.01x |
| DeepSeek-V4-Pro-0813 | 1 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 4 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 8 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 16 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 32 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 64 | 60 | 6.12 | 5.13 | 1.19x |
| DeepSeek-V4-Pro-0813 | 256 | 60 | 20.55 | 10.34 | 1.99x |
| DeepSeek-V4-Pro-0813 | 1 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 2 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 8 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 16 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 32 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 64 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 256 | 68 | 18.99 | 10.03 | 1.89x |
| DeepSeek-V4-Pro-0813 | 1 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 4 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 8 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 16 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 32 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 64 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 256 | 81 | 16.75 | 9.55 | 1.75x |
| DeepSeek-V4-Pro-0813 | 1 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 4 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 8 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 16 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 32 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 64 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 256 | 84 | 16.29 | 9.46 | 1.72x |
| DeepSeek-V4-Pro-0813 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 8 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 16 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 32 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 64 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 256 | 87 | 15.84 | 9.37 | 1.69x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 12.45 | 8.77 | 1.42x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 8.65 | 7.49 | 1.15x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 6.56 | 6.17 | 1.06x |
| DeepSeek-V4-Pro-0813 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 347 | 5.96 | 5.77 | 1.03x |

### 3. The per-layer serial cost, and who pays it

Before this term the only latency in the model was
`links.*.hop_latency_s`, charged at inter-partition boundaries -- so
a `single_chip` design had a decode step with no fixed cost at all.
**The asymmetry is the finding and it runs against the ROM thesis:**
a ROM step is tens of microseconds over 32-61 layers while a GPU step
for the same model is milliseconds, so the same per-layer floor is a
large fraction of one and a rounding error on the other.

| Family | Model | B | Fixed latency (us) | Share of the fastest step |
|---|---|---:|---:|---:|
| gpu | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 1.5% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 0.7% |
| gpu | Qwen3-8B | 1 | 5.85 | 1.0% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 5.7% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 3.7% |
| rom | Qwen3-8B | 1 | 5.85 | 4.6% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Qwen3-8B | sram | interleaved | 128 B | 1.00x |
| Qwen3-8B | hbm | interleaved | 32 B | 1.00x |
| DeepSeek-V4-Flash-0731 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Flash-0731 | hbm | interleaved | 32 B | 1.00x |
| DeepSeek-V4-Pro-0813 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Pro-0813 | hbm | interleaved | 32 B | 1.00x |

### 5. The SRAM KV path, which is still never exercised

A reported bound rather than a correction. The step credits ONE user
with the whole array's read bandwidth. That is defensible for KV in a
way it is not for ROM -- KV is written at run time and can be striped
across every bank, whereas an expert's weights live where they were
masked -- but it holds only if the design really stripes, and nothing
in the model checks. The bound below is what the same read costs if a
user can draw only the banks its own footprint occupies.

| Model | B | Devices | Bank occupancy | KV read as charged (us) | Under bank locality (us) |
|---|---:|---:|---:|---:|---:|
| Qwen3-8B | 1 | 3 | 44.74% | 12.45 | 9.27 |
| Qwen3-8B | 2 | 3 | 44.74% | 12.45 | 9.27 |
| Qwen3-8B | 4 | 1 | 0.87% | 4.62 | 9.27 |
| Qwen3-8B | 8 | 1 | 0.87% | 4.62 | 9.27 |
| Qwen3-8B | 16 | 1 | 0.87% | 4.62 | 9.27 |
| Qwen3-8B | 32 | 1 | 0.87% | 4.62 | 9.27 |
| Qwen3-8B | 64 | 1 | 0.98% | 5.19 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 21 | 40.78% | 18.25 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 21 | 40.78% | 18.25 | 2.13 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 1.48% | 1.80 | 2.13 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 1.48% | 1.80 | 2.13 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 1.48% | 1.80 | 2.13 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 1.48% | 1.80 | 2.13 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 1.66% | 2.02 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 110 | 80.65% | 184.27 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 47.19% | 111.73 | 2.08 |

## Sparse-MoE engagement on a ROM machine

Expected distinct experts touched by a batch is `1 - (1 - k/N)^B`, so the
bytes a step engages grow with batch while the ROM full-array sweep time
does not: an unselected expert's read ports cannot be borrowed, and a
selected one is read once however many batch members chose it. **MoE
sparsity on a ROM machine therefore converts into aggregate throughput,
not into lower per-token latency** -- which is the opposite of what it does
on an HBM machine, where bandwidth is global and sparsity directly
reduces the bytes fetched.

| Model | B | Expert coverage | Engaged weight bytes | Engaged fraction | Effective ROM read | Peak ROM read | Per-user tok/s | Aggregate tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 2,852.2 | 11,408.7 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 2,852.2 | 11,408.7 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 2,852.2 | 11,408.7 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,557.4 | 12,459.3 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 785.0 | 12,560.5 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 394.1 | 12,611.7 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 197.5 | 12,637.5 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 49.4 | 12,656.9 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 807.6 | 11,306.8 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 807.6 | 11,306.8 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 807.6 | 11,306.8 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 807.6 | 11,306.8 |
| DeepSeek-V4-Flash-0731 | 16 | 2.67% | 11.7 GB | 7.01% | 152.88 TB/s | 2,179.91 TB/s | 709.0 | 11,343.6 |
| DeepSeek-V4-Flash-0731 | 32 | 5.28% | 15.5 GB | 9.31% | 202.92 TB/s | 2,179.91 TB/s | 358.6 | 11,474.5 |
| DeepSeek-V4-Flash-0731 | 64 | 10.27% | 22.9 GB | 13.72% | 299.00 TB/s | 2,179.91 TB/s | 180.3 | 11,541.0 |
| DeepSeek-V4-Flash-0731 | 256 | 35.19% | 59.6 GB | 35.69% | 777.94 TB/s | 2,179.91 TB/s | 45.3 | 11,591.5 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 121.9 | 9,020.7 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 121.9 | 9,020.7 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 121.9 | 9,020.7 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 121.9 | 9,020.7 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 121.9 | 9,020.7 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 121.9 | 9,020.7 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 121.9 | 9,020.7 |
| DeepSeek-V4-Pro-0813 | 256 | 5.30% | 70.4 GB | 7.89% | 919.76 TB/s | 11,661.57 TB/s | 35.6 | 9,119.3 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 2 |
| gpu | kv_read | 22 |
| gpu | link_latency | 295 |
| gpu | weight_read | 577 |
| rom | compute | 80 |
| rom | infeasible | 1574 |
| rom | kv_read | 296 |
| rom | link_latency | 787 |
| rom | weight_read | 959 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 2 |
| rom | CAPACITY | 1574 |

## Mechanical consistency audit

**PASS** over 77,307 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 1 |
| published | 67 |
| derived | 30 |
| assumed | 53 |

Every `assumed` input, in full, because an ungraded assumption is the
failure mode this program exists to prevent:

- `efficiencies.compute`
- `efficiencies.expert_router_imbalance`
- `efficiencies.hbm_bandwidth`
- `efficiencies.hbm_capacity`
- `efficiencies.rom_read_bandwidth`
- `efficiencies.sram_read_bandwidth`
- `efficiencies.stage_balance`
- `energy.mac_energy_j_per_op.bf16`
- `energy.mac_energy_j_per_op.fp32`
- `energy.mac_energy_j_per_op.fp4`
- `energy.mac_energy_j_per_op.fp8`
- `energy.mac_energy_j_per_op.w4a8`
- `energy.rom_read_j_per_byte`
- `energy.sram_read_j_per_byte`
- `floorplan.interconnect_area_fraction`
- `floorplan.overhead_area_fraction`
- `hbm.hbm2e.phy_area_mm2_per_stack`
- `hbm.hbm2e.stack_beachfront_mm`
- `hbm.hbm3e.phy_area_mm2_per_stack`
- `hbm.hbm3e.stack_beachfront_mm`
- `kv.access_granularity_bytes.hbm`
- `kv.access_granularity_bytes.sram`
- `kv.index_layout`
- `latency.array_pass_boundaries_per_layer`
- `latency.global_wire_delay_s_per_mm`
- `latency.layer_barrier_s`
- `latency.pipeline_fill_drain_s`
- `latency.sequencer_issue_decode_s`
- `latency.sparse_index_dependency_s`
- `latency.sram_access_s`
- `links.ethernet.bytes_s`
- `links.ethernet.fabric`
- `links.ethernet.hop_latency_s`
- `links.ethernet.switch_radix`
- `links.inter_wafer.domain_size`
- `links.inter_wafer.fabric`
- `links.inter_wafer.hop_latency_s`
- `links.inter_wafer.switch_radix`
- `links.nvlink.hop_latency_s`
- `links.nvlink3.hop_latency_s`
- `links.nvlink5.hop_latency_s`
- `links.nvlink5_nvl72.hop_latency_s`
- `links.on_package.fabric`
- `links.on_package.hop_latency_s`
- `links.on_wafer.hop_latency_s`
- `reference_parts.taalas_hc1.batch_size`
- `reference_parts.taalas_hc1.weight_amortization`
- `reference_parts.taalas_hc1.weight_bits_per_parameter`
- `rom.array_efficiency`
- `rom.cell_to_sram_cell_area_ratio`
- `rom.cim_cell_area_multiplier`
- `rom.cim_precompute_area_fraction`
- `sram.array_efficiency`

## Interpretation boundary

- No mask-ROM macro has been fabricated at a leading node for this
  program. The ROM capacity density rests on an assumed cell-area ratio
  against a published SRAM bitcell, and the ROM read bandwidth density on
  a *simulated* 28 nm ROM-CIM macro scaled by published bitcell areas.
  Both are named in the evidence ledger above.
- Compute density is charged at a published GPU's whole-die roof per mm2,
  applied to a modelled design's compute-only area. Newer parts are
  denser than the A100 anchor, so this understates a 2026 design.
- Hop latencies are floors. They ignore switch contention, per-hop
  payload queueing beyond the modelled serialisation, and pipeline fill
  at batch 1. Each of those makes an array worse, never better, so the
  reported array crossovers are upper bounds.
- **Power is wrong by 7-9x and every rate above is independent of it.**
  The model counts memory bytes and MACs and nothing else, so it gives
  54.2 W for an A100 at batch 1 against a published 400 W and 27.0 W for
  Taalas HC1 against a published 200-250 W. It is not an activity-factor
  error: driven at peak HBM bandwidth AND the peak BF16 roof at once the
  model still gives 85.3 W. Leakage, clock distribution, operand delivery
  and control logic are not modelled at all. `thermal_scale` is therefore
  exactly 1.0 at every feasible point, and since `step_time = raw_step_time
  x thermal_scale` is the only path from power to any other quantity, no
  tokens/s in this report depends on the energy model -- and no watt or
  joule-per-token in it should be quoted.
- **Aggregate throughput is reported at steady state with every slot
  occupied, and fill and drain are not charged.** A request that is short
  compared with the slot count pays up to one extra traversal that this
  model does not bill, which flatters a deep pipeline. The delivered rate
  at the requested concurrency is reported separately and is not affected.
- **The weight replication a deep pipeline implies is not charged against
  capacity.** Beyond the layer count the surplus partitions hold replicas
  of a stage, and each replica needs its own copy of that stage's weights;
  the capacity check credits the machine with holding the model once. This
  favours the deepest pipelines, which are on the GPU side of this
  comparison, so correcting it would widen the ROM ratios rather than
  narrow them.
- Prefill, speculative decoding and cost are out of scope for this model.

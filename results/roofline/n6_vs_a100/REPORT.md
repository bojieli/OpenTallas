# Area-constrained roofline: n6_vs_a100

> Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 76.6 us, or 13,063 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 614x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate -- runs `tensor` on 1 device. On the GPU side the correction reaches 615x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate -- runs `tensor` on 112 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **The ROM advantage is a batch-1, per-user advantage, and it is large.** At equal area the best batch-1 point is DeepSeek-V4-Flash-0731 on 277,350 mm2 of ROM silicon at 4,750 tok/s per user, against 277,536 mm2 of a100_sxm_80gb-x336-tensor at 434 tok/s: **11x**. Both sides bind on `link_latency`, and the whole difference is that one reads its weights from HBM and the other from an on-die array.
4. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
5. **Letting the GPU choose its own parallelism is worth up to 226.97x to it.** At 554,700 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 1.04 tok/s and the same silicon running tensor delivers 237 tok/s.
6. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.09x (Qwen3-8B, ROM binding on `weight_read`) to 36.52x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
7. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 29.9% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 531 to 9,765 tok/s, and its rate with every slot occupied from 9,567 to 9,765. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 18 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
8. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 2,785 us over NVLink, capping per-user decode at 359 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 1,435.9 us and cap it at 696 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 2.0x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
9. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 24 of 24 operating points and an array 0; on tokens per second per square millimetre the same points go 20 to the array and 4 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
10. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 495 of 3164 feasible points.
11. **The largest open question is not in this model's inputs but in the architecture, and the anchor cannot settle it.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 20.7x of aggregate throughput (DeepSeek-V4-Flash-0731). The machines are identical at batch 1, which is where the published anchor sits, so no amount of validation against it resolves the fork.
12. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 7.20x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 3.04x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 43 of 48 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
13. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.

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
from Cerebras WSE-2 (4.327e+11 B/s/mm2), so it is physically unremarkable. That is a falsifiable
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

## Derived technology at N6

These are outputs of the graded primitives, not inputs.

| Quantity | Value | Grade |
|---|---:|---|
| SRAM capacity density | 3.009 MB/mm2 | assumed |
| ROM capacity density | 16.204 MB/mm2 | assumed |
| ROM read bandwidth density | 282.2 GB/s/mm2 | derived |
| SRAM read bandwidth density | 432.7 GB/s/mm2 | derived |
| Compute density, bf16 | 0.446 Tops/s/mm2 | derived |
| Compute density, fp8 | 0.891 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.261 Tops/s/mm2 | derived |
| Compute density, fp4 | 1.783 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.028 Tops/s/mm2 | derived |
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
| Qwen3-8B | 1 | 46,225 | 53,701.4 | wafer-pipeline | 7,936.4 | wafer-tensor | 6.77x | 3,851.8 | pipeline | 890.6 | tensor | 4.32x | 13.94x | 8.91x | 0.64x |
| Qwen3-8B | 2 | 92,450 | 50,885.4 | wafer-pipeline | 7,022.9 | wafer-hybrid | 7.25x | 6,021.8 | pipeline | 966.8 | tensor | 6.23x | 8.45x | 7.26x | 0.86x |
| Qwen3-8B | 3 | 138,675 | 50,885.4 | wafer-pipeline | 6,339.1 | wafer-hybrid | 8.03x | 7,414.2 | pipeline | 995.2 | tensor | 7.45x | 6.86x | 6.37x | 0.93x |
| Qwen3-8B | 4 | 184,900 | 50,885.4 | wafer-pipeline | 5,776.6 | wafer-hybrid | 8.81x | 8,383.4 | pipeline | 1,010.1 | tensor | 8.30x | 6.07x | 5.72x | 0.94x |
| Qwen3-8B | 6 | 277,350 | 50,885.4 | wafer-pipeline | 4,906.0 | wafer-hybrid | 10.37x | 9,644.1 | pipeline | 616.0 | tensor | 15.66x | 5.28x | 7.96x | 1.51x |
| Qwen3-8B | 8 | 369,800 | 50,885.4 | wafer-pipeline | 4,263.5 | wafer-hybrid | 11.94x | 10,428.2 | pipeline | 618.8 | tensor | 16.85x | 4.88x | 6.89x | 1.41x |
| Qwen3-8B | 12 | 554,700 | 59,341.0 | wafer-pipeline | 3,811.2 | wafer-hybrid | 15.57x | 11,351.1 | pipeline | 621.7 | tensor | 18.26x | 5.23x | 6.13x | 1.17x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 18,841.1 | wafer-pipeline | 5,515.2 | wafer-tensor | 3.42x | 1,572.1 | pipeline | 600.2 | tensor | 2.62x | 11.98x | 9.19x | 0.77x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 28,140.7 | wafer-pipeline | 5,249.5 | wafer-hybrid | 5.36x | 1,818.0 | pipeline | 630.5 | tensor | 2.88x | 15.48x | 8.33x | 0.54x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 35,354.3 | wafer-pipeline | 5,116.1 | wafer-hybrid | 6.91x | 1,922.7 | pipeline | 641.8 | tensor | 3.00x | 18.39x | 7.97x | 0.43x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 40,533.8 | wafer-pipeline | 4,988.2 | wafer-hybrid | 8.13x | 1,980.7 | pipeline | 647.7 | tensor | 3.06x | 20.46x | 7.70x | 0.38x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 47,474.8 | wafer-pipeline | 4,749.7 | wafer-hybrid | 10.00x | 2,043.2 | pipeline | 434.1 | tensor | 4.71x | 23.24x | 10.94x | 0.47x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 51,912.8 | wafer-pipeline | 4,532.6 | wafer-hybrid | 11.45x | 2,076.2 | pipeline | 435.5 | tensor | 4.77x | 25.00x | 10.41x | 0.42x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 57,260.3 | wafer-pipeline | 4,152.5 | wafer-hybrid | 13.79x | 2,110.6 | pipeline | 436.9 | tensor | 4.83x | 27.13x | 9.50x | 0.35x |
| DeepSeek-V4-Pro-0813 | 2 | 92,450 | 9,107.3 | wafer-pipeline | 2,653.6 | wafer-hybrid | 3.43x | 544.3 | pipeline | 294.7 | tensor | 1.85x | 16.73x | 9.01x | 0.54x |
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 9,632.6 | wafer-pipeline | 2,227.0 | wafer-hybrid | 4.33x | 578.8 | pipeline | 304.0 | tensor | 1.90x | 16.64x | 7.33x | 0.44x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 11,960.3 | wafer-pipeline | 2,210.5 | wafer-hybrid | 5.41x | 598.1 | pipeline | 309.0 | tensor | 1.94x | 20.00x | 7.15x | 0.36x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 15,728.1 | wafer-pipeline | 2,173.3 | wafer-hybrid | 7.24x | 619.0 | pipeline | 233.6 | tensor | 2.65x | 25.41x | 9.30x | 0.37x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 18,568.4 | wafer-pipeline | 2,126.8 | wafer-hybrid | 8.73x | 630.1 | pipeline | 235.1 | tensor | 2.68x | 29.47x | 9.04x | 0.31x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 22,685.8 | wafer-pipeline | 2,041.9 | wafer-hybrid | 11.11x | 641.7 | pipeline | 236.7 | tensor | 2.71x | 35.35x | 8.63x | 0.24x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.24x to 1.51x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 7,936.4 | 7,936.4 | link_latency | Qwen3-8B/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 929.83 | 890.6 | 890.6 | link_latency | 8.91x | 8.91x | 83.74x | 8.91x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x3 | 2,445 | 2,927.7 | 2,927.7 | link_latency | Qwen3-8B/a100_sxm_80gb-x3-tensor | 2,478 | 0.99x | tensor | 219.93 | 268.9 | 268.9 | weight_read | 10.89x | 10.89x | 30.70x | 10.89x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,720.5 | 9,441.1 | link_latency | Qwen3-8B/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,005.77 | 899.2 | 1,798.4 | link_latency | 5.25x | 5.25x | 49.81x | 5.25x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x5 | 4,075 | 1,848.1 | 3,696.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 225.44 | 402.9 | 805.8 | weight_read | 4.59x | 4.59x | 19.39x | 4.59x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,505.5 | 18,022.1 | link_latency | Qwen3-8B/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 1,157.65 | 819.2 | 3,276.9 | link_latency | 5.50x | 5.50x | 47.54x | 5.50x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 1,271.5 | 6,357.6 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 234.87 | 357.0 | 1,428.0 | weight_read | 3.56x | 4.45x | 13.34x | 3.56x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 4,129.4 | 33,034.9 | link_latency | Qwen3-8B/a100_sxm_80gb-x448-hybrid | 370,048 | 1.00x | hybrid | 390.13 | 586.2 | 32,829.1 | weight_read | 7.04x | 1.01x | 43.57x | 7.44x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 799.2 | 6,393.7 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 253.75 | 290.7 | 2,325.8 | weight_read | 2.75x | 2.75x | 8.76x | 2.75x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,417.6 | 54,680.9 | link_latency | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 390.13 | 586.2 | 49,243.6 | weight_read | 5.83x | 1.11x | 36.06x | 6.62x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 401.5 | 6,424.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 291.50 | 212.0 | 3,392.3 | kv_read | 1.89x | 1.89x | 4.90x | 1.89x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,418.5 | 77,390.6 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 390.13 | 586.2 | 49,243.6 | weight_read | 4.13x | 1.57x | 25.52x | 4.69x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 201.2 | 6,439.4 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 366.99 | 137.5 | 4,401.3 | kv_read | 1.46x | 1.46x | 2.95x | 1.46x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,526.1 | 97,673.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 390.13 | 586.2 | 49,243.6 | weight_read | 2.60x | 1.98x | 16.10x | 2.96x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 100.7 | 6,447.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 517.99 | 80.8 | 5,170.3 | kv_read | 1.25x | 1.25x | 1.98x | 1.25x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 474.9 | 121,568.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 424.18 | 516.0 | 132,088.6 | weight_read | 0.92x | 0.92x | 5.01x | 1.05x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 25.2 | 6,452.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 1,423.96 | 23.2 | 5,950.0 | kv_read | 1.08x | 1.08x | 1.24x | 1.08x |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 5,515.2 | 5,515.2 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,110.63 | 600.2 | 600.2 | link_latency | 9.19x | 9.19x | 169.06x | 9.19x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x18 | 14,670 | 1,856.4 | 1,856.4 | link_latency | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 1,094.53 | 507.2 | 507.2 | link_latency | 3.66x | 3.66x | 29.07x | 3.66x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 5,413.7 | 10,827.4 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,189.26 | 520.0 | 1,039.9 | link_latency | 10.41x | 10.41x | 165.95x | 10.41x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x18 | 14,670 | 1,694.8 | 5,084.4 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 1,157.05 | 428.3 | 856.6 | link_latency | 3.96x | 5.94x | 26.54x | 3.96x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 5,139.8 | 20,559.3 | link_latency | DSV4-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,370.67 | 461.4 | 1,845.7 | link_latency | 11.14x | 11.14x | 265.11x | 11.14x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x18 | 14,670 | 1,439.9 | 5,759.6 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 1,282.10 | 340.9 | 1,363.6 | weight_read | 4.22x | 4.22x | 22.54x | 4.22x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,883.4 | 39,066.9 | link_latency | DSV4-Flash/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 1,733.49 | 387.2 | 3,097.8 | link_latency | 12.61x | 12.61x | 453.90x | 12.61x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x18 | 14,670 | 899.0 | 7,192.2 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 1,532.20 | 253.1 | 2,025.1 | weight_read | 3.55x | 3.55x | 14.08x | 3.55x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 4,440.2 | 71,043.5 | link_latency | DSV4-Flash/a100_sxm_80gb-x448-tensor | 370,048 | 1.00x | tensor | 3,233.14 | 242.8 | 3,885.3 | link_latency | 18.29x | 18.29x | 778.82x | 18.29x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 531.5 | 9,566.7 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 2,032.41 | 176.8 | 2,828.8 | weight_read | 3.01x | 3.38x | 8.32x | 3.01x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,819.3 | 122,216.4 | link_latency | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 4,676.38 | 176.8 | 5,658.3 | link_latency | 21.60x | 21.60x | 984.56x | 21.60x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 301.9 | 9,659.2 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 3,032.81 | 119.3 | 3,816.1 | weight_read | 2.53x | 2.53x | 6.03x | 2.53x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,062.3 | 195,988.5 | link_latency | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 7,546.77 | 114.8 | 7,344.3 | link_latency | 26.69x | 26.69x | 789.43x | 26.69x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 151.9 | 9,719.6 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 5,033.63 | 80.4 | 5,146.5 | weight_read | 1.89x | 1.89x | 4.23x | 1.89x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,398.9 | 358,110.0 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 24,769.07 | 38.3 | 9,806.5 | link_latency | 36.52x | 36.52x | 360.61x | 36.52x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 38.1 | 9,765.4 | compute | DSV4-Flash/a100_sxm_80gb-x18-hybrid | 14,868 | 0.99x | hybrid | 848.96 | 39.2 | 10,045.7 | weight_read | 0.97x | 0.97x | 2.32x | 0.97x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 2,653.6 | 2,653.6 | link_latency | DSV4-Pro/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,674.19 | 294.7 | 294.7 | link_latency | 9.01x | 9.01x | 507.32x | 9.01x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x94 | 76,610 | 570.2 | 570.2 | compute | DSV4-Pro/a100_sxm_80gb-x93-tensor | 76,818 | 1.00x | tensor | 1,671.69 | 289.3 | 289.3 | link_latency | 1.97x | 1.97x | 94.01x | 1.97x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill | 231,125 | 2,197.6 | 10,988.2 | weight_read | DSV4-Pro/a100_sxm_80gb-x280-tensor | 231,280 | 1.00x | tensor | 1,902.37 | 274.6 | 549.1 | link_latency | 8.00x | 20.01x | 927.49x | 8.00x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 552.1 | 6,624.6 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 1,879.39 | 240.6 | 481.3 | weight_read | 2.29x | 13.76x | 92.56x | 2.29x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill | 231,125 | 2,197.6 | 10,988.2 | weight_read | DSV4-Pro/a100_sxm_80gb-x280-tensor | 231,280 | 1.00x | tensor | 2,340.74 | 215.0 | 860.0 | link_latency | 10.22x | 12.78x | 927.49x | 10.22x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 552.1 | 6,624.6 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 2,294.77 | 184.9 | 739.7 | weight_read | 2.99x | 8.96x | 92.56x | 2.99x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 2,172.5 | 17,380.3 | link_latency | DSV4-Pro/a100_sxm_80gb-x336-tensor | 277,536 | 1.00x | tensor | 4,323.48 | 138.1 | 1,105.1 | link_latency | 15.73x | 15.73x | 1083.68x | 15.73x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 552.1 | 6,624.6 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 3,125.54 | 136.8 | 1,094.2 | weight_read | 4.04x | 6.05x | 92.56x | 4.04x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,036.4 | 32,582.9 | link_latency | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 6,124.95 | 108.8 | 1,740.2 | link_latency | 18.72x | 18.72x | 1953.06x | 18.72x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 440.1 | 7,041.8 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 4,787.08 | 94.3 | 1,508.3 | weight_read | 4.67x | 4.67x | 73.79x | 4.67x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,432.1 | 45,827.9 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 9,687.89 | 73.9 | 2,365.6 | link_latency | 19.37x | 19.37x | 1373.49x | 19.37x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 243.0 | 7,776.3 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 8,110.17 | 61.5 | 1,968.4 | link_latency | 3.95x | 3.95x | 40.74x | 3.95x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 877.3 | 56,145.1 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 16,813.79 | 46.4 | 2,972.7 | link_latency | 18.89x | 18.89x | 841.35x | 18.89x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 128.2 | 8,204.2 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 14,756.34 | 38.6 | 2,472.3 | link_latency | 3.32x | 3.32x | 21.49x | 3.32x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 263.9 | 67,551.0 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 59,569.14 | 15.2 | 3,898.4 | link_latency | 17.33x | 17.33x | 253.07x | 17.33x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x96 | 78,240 | 34.3 | 8,776.9 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 54,633.36 | 13.9 | 3,560.2 | link_latency | 2.47x | 2.47x | 8.49x | 2.47x |

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
| DeepSeek-V4-Flash-0731 | 14,670 | 3.88x | 3.66x | 2.33x |
| DeepSeek-V4-Flash-0731 | 15,485 | 3.82x | 3.62x | 2.31x |
| DeepSeek-V4-Flash-0731 | 46,225 | 16.28x | 9.19x | 3.60x |
| DeepSeek-V4-Flash-0731 | 92,450 | 14.53x | 8.33x | 3.42x |
| DeepSeek-V4-Flash-0731 | 138,675 | 14.08x | 7.97x | 3.34x |
| DeepSeek-V4-Flash-0731 | 184,900 | 13.79x | 7.70x | 3.27x |
| DeepSeek-V4-Flash-0731 | 277,350 | 19.85x | 10.94x | 4.45x |
| DeepSeek-V4-Flash-0731 | 369,800 | 19.37x | 10.41x | 4.33x |
| DeepSeek-V4-Flash-0731 | 554,700 | 18.51x | 9.50x | 4.11x |
| DeepSeek-V4-Pro-0813 | 76,610 | 2.13x | 1.97x | — |
| DeepSeek-V4-Pro-0813 | 78,240 | 2.34x | 2.34x | 1.92x |
| DeepSeek-V4-Pro-0813 | 80,685 | 2.18x | 2.20x | 1.84x |
| DeepSeek-V4-Pro-0813 | 92,450 | 12.75x | 9.01x | 4.11x |
| DeepSeek-V4-Pro-0813 | 138,675 | 9.60x | 7.33x | 3.77x |
| DeepSeek-V4-Pro-0813 | 184,900 | 9.45x | 7.15x | 3.70x |
| DeepSeek-V4-Pro-0813 | 231,125 | 9.39x | 7.04x | 3.65x |
| DeepSeek-V4-Pro-0813 | 277,350 | 12.21x | 9.30x | 4.72x |
| DeepSeek-V4-Pro-0813 | 369,800 | 12.04x | 9.04x | 4.63x |
| DeepSeek-V4-Pro-0813 | 554,700 | 11.82x | 8.63x | 4.46x |
| Qwen3-8B | 2,445 | 13.53x | 10.89x | 11.79x |
| Qwen3-8B | 3,260 | 11.59x | 9.14x | 11.24x |
| Qwen3-8B | 4,075 | 7.27x | 6.09x | 3.61x |
| Qwen3-8B | 4,890 | 9.55x | 7.28x | 8.50x |
| Qwen3-8B | 5,705 | — | 6.52x | 2.83x |
| Qwen3-8B | 6,520 | 7.82x | 4.75x | — |
| Qwen3-8B | 46,225 | 19.34x | 8.91x | 3.39x |
| Qwen3-8B | 92,450 | 13.94x | 7.26x | 3.02x |
| Qwen3-8B | 138,675 | 11.33x | 6.37x | 2.87x |
| Qwen3-8B | 184,900 | 9.62x | 5.72x | 2.75x |
| Qwen3-8B | 277,350 | 12.44x | 7.96x | 3.46x |
| Qwen3-8B | 369,800 | 10.19x | 6.89x | 3.26x |
| Qwen3-8B | 554,700 | 9.28x | 6.13x | 3.05x |

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
| DeepSeek-V4-Flash-0731 | 8 | 6,608 | 90.1 | 602.7 | — | tensor | 264.16 | 15.9% | weight_read |
| DeepSeek-V4-Flash-0731 | 18 | 14,868 | 63.9 | 507.2 | 346.5 | tensor | 1,094.53 | 55.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 19 | 15,694 | 62.2 | 513.3 | 355.1 | tensor | 1,094.53 | 56.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 26 | 21,476 | 52.7 | 543.7 | 312.5 | tensor | 1,101.57 | 59.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 28 | 23,128 | 50.5 | 550.7 | 321.9 | tensor | 1,101.57 | 60.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 31 | 25,606 | 47.6 | 559.8 | 334.6 | tensor | 1,101.57 | 61.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 42 | 34,692 | 39.5 | 581.8 | 256.4 | tensor | 1,108.62 | 64.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 44 | 36,344 | 38.3 | 585.2 | 260.3 | tensor | 1,108.62 | 64.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 32.6 | 600.2 | 242.5 | tensor | 1,110.63 | 66.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 19.4 | 630.5 | 147.6 | tensor | 1,116.67 | 70.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 13.8 | 641.8 | 106.4 | tensor | 1,118.68 | 71.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 10.8 | 647.7 | 83.3 | tensor | 1,119.69 | 72.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 7.5 | 434.1 | 58.0 | tensor | 1,894.69 | 82.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 5.7 | 435.5 | 44.7 | tensor | 1,895.20 | 82.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 3.9 | 436.9 | 30.6 | tensor | 1,895.70 | 82.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 48 | 39,648 | 9.8 | 264.0 | 76.1 | tensor | 1,654.20 | 43.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 8.8 | 270.8 | 68.7 | tensor | 1,659.20 | 44.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 93 | 76,818 | 6.1 | 289.3 | 46.1 | tensor | 1,671.69 | 48.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 95 | 78,470 | 6.0 | 289.9 | 46.3 | tensor | 1,671.69 | 48.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 98 | 80,948 | 5.8 | 290.8 | 43.0 | tensor | 1,673.04 | 48.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 5.2 | 294.7 | 41.1 | tensor | 1,674.19 | 49.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 139 | 114,814 | 4.4 | 300.0 | 33.3 | tensor | 1,677.52 | 50.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 145 | 119,770 | 4.2 | 300.9 | 31.8 | tensor | 1,678.14 | 50.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 147 | 121,422 | 4.2 | 301.2 | 31.8 | tensor | 1,678.14 | 50.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 154 | 127,204 | 4.0 | 302.2 | 30.5 | tensor | 1,678.69 | 50.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 155 | 128,030 | 4.0 | 302.4 | 30.5 | tensor | 1,678.69 | 50.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 156 | 128,856 | 4.0 | 302.5 | 30.5 | tensor | 1,678.69 | 50.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 3.7 | 304.0 | 29.4 | tensor | 1,679.19 | 51.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 2.9 | 309.0 | 22.9 | tensor | 1,681.69 | 52.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 2.4 | 312.1 | 18.8 | tensor | 1,683.19 | 52.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 2.0 | 233.6 | 15.9 | tensor | 2,782.19 | 65.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 1.5 | 235.1 | 12.2 | tensor | 2,783.43 | 65.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 1.0 | 236.7 | 8.3 | tensor | 2,784.68 | 65.9% | link_latency |
| Qwen3-8B | 3 | 2,478 | 95.4 | 268.9 | — | tensor | 219.93 | 5.9% | weight_read |
| Qwen3-8B | 4 | 3,304 | 95.3 | 351.4 | — | tensor | 220.42 | 7.7% | weight_read |
| Qwen3-8B | 5 | 4,130 | 95.3 | 430.6 | — | tensor | 220.72 | 9.5% | weight_read |
| Qwen3-8B | 6 | 4,956 | 95.3 | 506.8 | — | tensor | 220.92 | 11.2% | weight_read |
| Qwen3-8B | 7 | 5,782 | 95.3 | 580.1 | — | tensor | 221.06 | 12.8% | weight_read |
| Qwen3-8B | 8 | 6,608 | 95.3 | 650.7 | — | tensor | 221.16 | 14.4% | weight_read |
| Qwen3-8B | 56 | 46,256 | 94.8 | 890.6 | 638.7 | tensor | 929.83 | 82.8% | link_latency |
| Qwen3-8B | 112 | 92,512 | 94.8 | 966.8 | 625.2 | tensor | 934.88 | 90.4% | link_latency |
| Qwen3-8B | 168 | 138,768 | 94.8 | 995.2 | 612.2 | tensor | 936.57 | 93.2% | link_latency |
| Qwen3-8B | 224 | 185,024 | 94.8 | 1,010.1 | 599.8 | tensor | 937.41 | 94.7% | link_latency |
| Qwen3-8B | 336 | 277,536 | 94.8 | 616.0 | 586.2 | tensor | 1,586.25 | 97.7% | link_latency |
| Qwen3-8B | 448 | 370,048 | 94.8 | 618.8 | 586.2 | tensor | 1,586.68 | 98.2% | link_latency |
| Qwen3-8B | 672 | 555,072 | 94.8 | 621.7 | 586.2 | tensor | 1,587.10 | 98.7% | link_latency |

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
| Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x3 | Qwen3-8B | 3 | pipeline | nvlink3 | infiniband_hdr | 2 | 3.05 us | 32,737.4 tok/s | 327,373.7 tok/s | 2 x point_to_point span 2 on nvlink3 (traversals 1.0) = 3.05 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 3.50 us | 28,571.3 tok/s | 285,713.4 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 3.50 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x4 | Qwen3-8B | 4 | tensor | nvlink3 | infiniband_hdr | 72 | 220.42 us | 453.7 tok/s | 4,536.7 tok/s | 72 x all_reduce span 4 on nvlink3 (traversals 2.0) = 220.42 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 110.88 us | 901.9 tok/s | 9,018.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 110.88 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | Qwen3-8B | 5 | pipeline | nvlink3 | infiniband_hdr | 4 | 6.11 us | 16,368.7 tok/s | 163,686.8 tok/s | 4 x point_to_point span 2 on nvlink3 (traversals 1.0) = 6.11 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 3.50 us | 28,571.3 tok/s | 285,713.4 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 3.50 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x8 | Qwen3-8B | 8 | tensor | nvlink3 | infiniband_hdr | 72 | 221.16 us | 452.2 tok/s | 4,521.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 110.88 us | 901.9 tok/s | 9,018.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 110.88 us |
| Qwen3-8B/a100_sxm_80gb-x3-pipeline | Qwen3-8B | 3 | pipeline | nvlink3 | infiniband_hdr | 2 | 3.05 us | 32,737.4 tok/s | 327,373.7 tok/s | 2 x point_to_point span 2 on nvlink3 (traversals 1.0) = 3.05 us |
| Qwen3-8B/a100_sxm_80gb-x3-tensor | Qwen3-8B | 3 | tensor | nvlink3 | infiniband_hdr | 72 | 219.93 us | 454.7 tok/s | 4,546.9 tok/s | 72 x all_reduce span 3 on nvlink3 (traversals 2.0) = 219.93 us |
| Qwen3-8B/a100_sxm_80gb-x4-pipeline | Qwen3-8B | 4 | pipeline | nvlink3 | infiniband_hdr | 3 | 4.58 us | 21,824.9 tok/s | 218,249.1 tok/s | 3 x point_to_point span 2 on nvlink3 (traversals 1.0) = 4.58 us |
| Qwen3-8B/a100_sxm_80gb-x4-tensor | Qwen3-8B | 4 | tensor | nvlink3 | infiniband_hdr | 72 | 220.42 us | 453.7 tok/s | 4,536.7 tok/s | 72 x all_reduce span 4 on nvlink3 (traversals 2.0) = 220.42 us |
| Qwen3-8B/a100_sxm_80gb-x5-pipeline | Qwen3-8B | 5 | pipeline | nvlink3 | infiniband_hdr | 4 | 6.11 us | 16,368.7 tok/s | 163,686.8 tok/s | 4 x point_to_point span 2 on nvlink3 (traversals 1.0) = 6.11 us |
| Qwen3-8B/a100_sxm_80gb-x5-tensor | Qwen3-8B | 5 | tensor | nvlink3 | infiniband_hdr | 72 | 220.72 us | 453.1 tok/s | 4,530.7 tok/s | 72 x all_reduce span 5 on nvlink3 (traversals 2.0) = 220.72 us |
| Qwen3-8B/a100_sxm_80gb-x6-pipeline | Qwen3-8B | 6 | pipeline | nvlink3 | infiniband_hdr | 5 | 7.64 us | 13,094.9 tok/s | 130,949.5 tok/s | 5 x point_to_point span 2 on nvlink3 (traversals 1.0) = 7.64 us |
| Qwen3-8B/a100_sxm_80gb-x6-tensor | Qwen3-8B | 6 | tensor | nvlink3 | infiniband_hdr | 72 | 220.92 us | 452.7 tok/s | 4,526.6 tok/s | 72 x all_reduce span 6 on nvlink3 (traversals 2.0) = 220.92 us |
| Qwen3-8B/a100_sxm_80gb-x7-pipeline | Qwen3-8B | 7 | pipeline | nvlink3 | infiniband_hdr | 6 | 9.16 us | 10,912.5 tok/s | 109,124.6 tok/s | 6 x point_to_point span 2 on nvlink3 (traversals 1.0) = 9.16 us |
| Qwen3-8B/a100_sxm_80gb-x7-tensor | Qwen3-8B | 7 | tensor | nvlink3 | infiniband_hdr | 72 | 221.06 us | 452.4 tok/s | 4,523.7 tok/s | 72 x all_reduce span 7 on nvlink3 (traversals 2.0) = 221.06 us |
| Qwen3-8B/a100_sxm_80gb-x8-pipeline | Qwen3-8B | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 10.69 us | 9,353.5 tok/s | 93,535.3 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.69 us |
| Qwen3-8B/a100_sxm_80gb-x8-tensor | Qwen3-8B | 8 | tensor | nvlink3 | infiniband_hdr | 72 | 221.16 us | 452.2 tok/s | 4,521.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us |
| Qwen3-8B/a100_sxm_80gb-x56-pipeline | Qwen3-8B | 56 | pipeline | nvlink3 | infiniband_hdr | 35 | 66.66 us | 1,500.2 tok/s | 15,002.1 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 47.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x56-tensor | Qwen3-8B | 56 | tensor | nvlink3 | infiniband_hdr | 144 | 929.83 us | 107.5 tok/s | 1,075.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 708.67 us |
| Qwen3-8B/a100_sxm_80gb-x56-hybrid | Qwen3-8B | 56 | hybrid | nvlink3 | infiniband_hdr | 78 | 250.13 us | 399.8 tok/s | 3,998.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.97 us |
| Qwen3-8B/a100_sxm_80gb-x112-pipeline | Qwen3-8B | 112 | pipeline | nvlink3 | infiniband_hdr | 35 | 66.66 us | 1,500.2 tok/s | 15,002.1 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 47.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x112-tensor | Qwen3-8B | 112 | tensor | nvlink3 | infiniband_hdr | 144 | 934.88 us | 107.0 tok/s | 1,069.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 713.72 us |
| Qwen3-8B/a100_sxm_80gb-x112-hybrid | Qwen3-8B | 112 | hybrid | nvlink3 | infiniband_hdr | 85 | 283.92 us | 352.2 tok/s | 3,522.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.76 us |
| Qwen3-8B/a100_sxm_80gb-x168-pipeline | Qwen3-8B | 168 | pipeline | nvlink3 | infiniband_hdr | 35 | 66.66 us | 1,500.2 tok/s | 15,002.1 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 47.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x168-tensor | Qwen3-8B | 168 | tensor | nvlink3 | infiniband_hdr | 144 | 936.57 us | 106.8 tok/s | 1,067.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 715.41 us |
| Qwen3-8B/a100_sxm_80gb-x168-hybrid | Qwen3-8B | 168 | hybrid | nvlink3 | infiniband_hdr | 92 | 317.71 us | 314.7 tok/s | 3,147.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.55 us |
| Qwen3-8B/a100_sxm_80gb-x224-pipeline | Qwen3-8B | 224 | pipeline | nvlink3 | infiniband_hdr | 35 | 66.66 us | 1,500.2 tok/s | 15,002.1 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 47.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x224-tensor | Qwen3-8B | 224 | tensor | nvlink3 | infiniband_hdr | 144 | 937.41 us | 106.7 tok/s | 1,066.8 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 716.25 us |
| Qwen3-8B/a100_sxm_80gb-x224-hybrid | Qwen3-8B | 224 | hybrid | nvlink3 | infiniband_hdr | 99 | 351.51 us | 284.5 tok/s | 2,844.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 130.35 us |
| Qwen3-8B/a100_sxm_80gb-x336-pipeline | Qwen3-8B | 336 | pipeline | nvlink3 | infiniband_hdr | 35 | 66.66 us | 1,500.2 tok/s | 15,002.1 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 47.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x336-tensor | Qwen3-8B | 336 | tensor | nvlink3 | infiniband_hdr | 144 | 1,586.25 us | 63.0 tok/s | 630.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,365.09 us |
| Qwen3-8B/a100_sxm_80gb-x336-hybrid | Qwen3-8B | 336 | hybrid | nvlink3 | infiniband_hdr | 107 | 390.13 us | 256.3 tok/s | 2,563.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 168.97 us |
| Qwen3-8B/a100_sxm_80gb-x448-pipeline | Qwen3-8B | 448 | pipeline | nvlink3 | infiniband_hdr | 35 | 66.66 us | 1,500.2 tok/s | 15,002.1 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 47.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x448-tensor | Qwen3-8B | 448 | tensor | nvlink3 | infiniband_hdr | 144 | 1,586.68 us | 63.0 tok/s | 630.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,365.51 us |
| Qwen3-8B/a100_sxm_80gb-x448-hybrid | Qwen3-8B | 448 | hybrid | nvlink3 | infiniband_hdr | 107 | 390.13 us | 256.3 tok/s | 2,563.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 168.97 us |
| Qwen3-8B/a100_sxm_80gb-x672-pipeline | Qwen3-8B | 672 | pipeline | nvlink3 | infiniband_hdr | 35 | 66.66 us | 1,500.2 tok/s | 15,002.1 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 47.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x672-tensor | Qwen3-8B | 672 | tensor | nvlink3 | infiniband_hdr | 144 | 1,587.10 us | 63.0 tok/s | 630.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,365.94 us |
| Qwen3-8B/a100_sxm_80gb-x672-hybrid | Qwen3-8B | 672 | hybrid | nvlink3 | infiniband_hdr | 107 | 390.13 us | 256.3 tok/s | 2,563.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 168.97 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x18 | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 32.56 us | 3,070.8 tok/s | 30,707.9 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 22.91 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 4.20 us | 23,809.5 tok/s | 238,094.5 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.20 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x18 | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink3 | infiniband_hdr | 172 | 1,094.53 us | 91.4 tok/s | 913.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 830.36 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 132.44 us | 755.1 tok/s | 7,550.6 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 132.44 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x18 | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink3 | infiniband_hdr | 88 | 273.82 us | 365.2 tok/s | 3,652.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 34.09 us | 2,933.2 tok/s | 29,332.2 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 24.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 4.20 us | 23,809.5 tok/s | 238,094.5 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.20 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x18 | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink3 | infiniband_hdr | 172 | 1,094.53 us | 91.4 tok/s | 913.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 830.36 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 132.44 us | 755.1 tok/s | 7,550.6 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 132.44 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x19 | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink3 | infiniband_hdr | 88 | 273.82 us | 365.2 tok/s | 3,652.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x8-pipeline | DeepSeek-V4-Flash-0731 | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 10.69 us | 9,353.5 tok/s | 93,535.3 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.69 us |
| DSV4-Flash/a100_sxm_80gb-x8-tensor | DeepSeek-V4-Flash-0731 | 8 | tensor | nvlink3 | infiniband_hdr | 86 | 264.16 us | 378.6 tok/s | 3,785.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us |
| DSV4-Flash/a100_sxm_80gb-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 32.56 us | 3,070.8 tok/s | 30,707.9 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 22.91 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink3 | infiniband_hdr | 172 | 1,094.53 us | 91.4 tok/s | 913.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 830.36 us |
| DSV4-Flash/a100_sxm_80gb-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink3 | infiniband_hdr | 88 | 273.82 us | 365.2 tok/s | 3,652.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 34.09 us | 2,933.2 tok/s | 29,332.2 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 24.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink3 | infiniband_hdr | 172 | 1,094.53 us | 91.4 tok/s | 913.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 830.36 us |
| DSV4-Flash/a100_sxm_80gb-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink3 | infiniband_hdr | 88 | 273.82 us | 365.2 tok/s | 3,652.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x26-pipeline | DeepSeek-V4-Flash-0731 | 26 | pipeline | nvlink3 | infiniband_hdr | 25 | 48.08 us | 2,079.7 tok/s | 20,797.0 tok/s | 22 x point_to_point span 2 on nvlink3 (traversals 1.0) = 33.60 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x26-tensor | DeepSeek-V4-Flash-0731 | 26 | tensor | nvlink3 | infiniband_hdr | 172 | 1,101.57 us | 90.8 tok/s | 907.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 837.41 us |
| DSV4-Flash/a100_sxm_80gb-x26-hybrid | DeepSeek-V4-Flash-0731 | 26 | hybrid | nvlink3 | infiniband_hdr | 89 | 278.65 us | 358.9 tok/s | 3,588.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x28-pipeline | DeepSeek-V4-Flash-0731 | 28 | pipeline | nvlink3 | infiniband_hdr | 27 | 51.14 us | 1,955.5 tok/s | 19,554.8 tok/s | 24 x point_to_point span 2 on nvlink3 (traversals 1.0) = 36.66 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x28-tensor | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink3 | infiniband_hdr | 172 | 1,101.57 us | 90.8 tok/s | 907.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 837.41 us |
| DSV4-Flash/a100_sxm_80gb-x28-hybrid | DeepSeek-V4-Flash-0731 | 28 | hybrid | nvlink3 | infiniband_hdr | 89 | 278.65 us | 358.9 tok/s | 3,588.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x31-pipeline | DeepSeek-V4-Flash-0731 | 31 | pipeline | nvlink3 | infiniband_hdr | 30 | 55.72 us | 1,794.7 tok/s | 17,946.8 tok/s | 27 x point_to_point span 2 on nvlink3 (traversals 1.0) = 41.24 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x31-tensor | DeepSeek-V4-Flash-0731 | 31 | tensor | nvlink3 | infiniband_hdr | 172 | 1,101.57 us | 90.8 tok/s | 907.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 837.41 us |
| DSV4-Flash/a100_sxm_80gb-x31-hybrid | DeepSeek-V4-Flash-0731 | 31 | hybrid | nvlink3 | infiniband_hdr | 89 | 278.65 us | 358.9 tok/s | 3,588.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x42-pipeline | DeepSeek-V4-Flash-0731 | 42 | pipeline | nvlink3 | infiniband_hdr | 41 | 79.12 us | 1,263.9 tok/s | 12,638.8 tok/s | 36 x point_to_point span 2 on nvlink3 (traversals 1.0) = 54.98 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x42-tensor | DeepSeek-V4-Flash-0731 | 42 | tensor | nvlink3 | infiniband_hdr | 172 | 1,108.62 us | 90.2 tok/s | 902.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 844.45 us |
| DSV4-Flash/a100_sxm_80gb-x42-hybrid | DeepSeek-V4-Flash-0731 | 42 | hybrid | nvlink3 | infiniband_hdr | 91 | 288.30 us | 346.9 tok/s | 3,468.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x44-pipeline | DeepSeek-V4-Flash-0731 | 44 | pipeline | nvlink3 | infiniband_hdr | 42 | 80.65 us | 1,239.9 tok/s | 12,399.4 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 56.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x44-tensor | DeepSeek-V4-Flash-0731 | 44 | tensor | nvlink3 | infiniband_hdr | 172 | 1,108.62 us | 90.2 tok/s | 902.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 844.45 us |
| DSV4-Flash/a100_sxm_80gb-x44-hybrid | DeepSeek-V4-Flash-0731 | 44 | hybrid | nvlink3 | infiniband_hdr | 91 | 288.30 us | 346.9 tok/s | 3,468.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 80.65 us | 1,239.9 tok/s | 12,399.4 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 56.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 1,110.63 us | 90.0 tok/s | 900.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 846.46 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 293.13 us | 341.1 tok/s | 3,411.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.97 us |
| DSV4-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Flash-0731 | 112 | pipeline | nvlink3 | infiniband_hdr | 42 | 80.65 us | 1,239.9 tok/s | 12,399.4 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 56.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Flash-0731 | 112 | tensor | nvlink3 | infiniband_hdr | 172 | 1,116.67 us | 89.6 tok/s | 895.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 852.50 us |
| DSV4-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Flash-0731 | 112 | hybrid | nvlink3 | infiniband_hdr | 99 | 326.92 us | 305.9 tok/s | 3,058.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.76 us |
| DSV4-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Flash-0731 | 168 | pipeline | nvlink3 | infiniband_hdr | 42 | 80.65 us | 1,239.9 tok/s | 12,399.4 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 56.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Flash-0731 | 168 | tensor | nvlink3 | infiniband_hdr | 172 | 1,118.68 us | 89.4 tok/s | 893.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 854.52 us |
| DSV4-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Flash-0731 | 168 | hybrid | nvlink3 | infiniband_hdr | 106 | 360.72 us | 277.2 tok/s | 2,772.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.55 us |
| DSV4-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Flash-0731 | 224 | pipeline | nvlink3 | infiniband_hdr | 42 | 80.65 us | 1,239.9 tok/s | 12,399.4 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 56.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Flash-0731 | 224 | tensor | nvlink3 | infiniband_hdr | 172 | 1,119.69 us | 89.3 tok/s | 893.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 855.52 us |
| DSV4-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Flash-0731 | 224 | hybrid | nvlink3 | infiniband_hdr | 113 | 394.51 us | 253.5 tok/s | 2,534.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 130.35 us |
| DSV4-Flash/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Flash-0731 | 336 | pipeline | nvlink3 | infiniband_hdr | 42 | 80.65 us | 1,239.9 tok/s | 12,399.4 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 56.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Flash-0731 | 336 | tensor | nvlink3 | infiniband_hdr | 172 | 1,894.69 us | 52.8 tok/s | 527.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,630.53 us |
| DSV4-Flash/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Flash-0731 | 336 | hybrid | nvlink3 | infiniband_hdr | 127 | 462.10 us | 216.4 tok/s | 2,164.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.93 us |
| DSV4-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Flash-0731 | 448 | pipeline | nvlink3 | infiniband_hdr | 42 | 80.65 us | 1,239.9 tok/s | 12,399.4 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 56.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Flash-0731 | 448 | tensor | nvlink3 | infiniband_hdr | 172 | 1,895.20 us | 52.8 tok/s | 527.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,631.03 us |
| DSV4-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Flash-0731 | 448 | hybrid | nvlink3 | infiniband_hdr | 128 | 466.93 us | 214.2 tok/s | 2,141.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 202.76 us |
| DSV4-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Flash-0731 | 672 | pipeline | nvlink3 | infiniband_hdr | 42 | 80.65 us | 1,239.9 tok/s | 12,399.4 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 56.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Flash-0731 | 672 | tensor | nvlink3 | infiniband_hdr | 172 | 1,895.70 us | 52.8 tok/s | 527.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,631.53 us |
| DSV4-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Flash-0731 | 672 | hybrid | nvlink3 | infiniband_hdr | 128 | 466.93 us | 214.2 tok/s | 2,141.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 202.76 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x96 | DeepSeek-V4-Pro-0813 | 96 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4-Pro-0813 | 2 | pipeline | on_wafer | inter_wafer | 60 | 11.00 us | 9,094.5 tok/s | 90,945.4 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.90 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x94 | DeepSeek-V4-Pro-0813 | 94 | tensor | nvlink3 | infiniband_hdr | 244 | 1,671.69 us | 59.8 tok/s | 598.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4-Pro-0813 | 2 | tensor | on_wafer | inter_wafer | 244 | 1,425.37 us | 70.2 tok/s | 701.6 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 122 x all_reduce span 2 on inter_wafer (traversals 2.0) = 1,237.49 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x96 | DeepSeek-V4-Pro-0813 | 96 | hybrid | nvlink3 | infiniband_hdr | 133 | 437.11 us | 228.8 tok/s | 2,287.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.81 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4-Pro-0813 | 2 | hybrid | on_wafer | inter_wafer | 123 | 192.98 us | 518.2 tok/s | 5,182.0 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x99 | DeepSeek-V4-Pro-0813 | 99 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5 | DeepSeek-V4-Pro-0813 | 5 | pipeline | on_wafer | inter_wafer | 60 | 11.00 us | 9,094.5 tok/s | 90,945.4 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.90 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x96 | DeepSeek-V4-Pro-0813 | 96 | tensor | nvlink3 | infiniband_hdr | 244 | 1,671.69 us | 59.8 tok/s | 598.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x5 | DeepSeek-V4-Pro-0813 | 5 | tensor | on_wafer | inter_wafer | 244 | 1,435.86 us | 69.6 tok/s | 696.4 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 122 x all_reduce span 5 on inter_wafer (traversals 2.0) = 1,247.98 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x99 | DeepSeek-V4-Pro-0813 | 99 | hybrid | nvlink3 | infiniband_hdr | 134 | 442.18 us | 226.1 tok/s | 2,261.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.88 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer | inter_wafer | 126 | 208.26 us | 480.2 tok/s | 4,801.6 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 4 x point_to_point span 2 on inter_wafer (traversals 1.0) = 20.38 us |
| DSV4-Pro/a100_sxm_80gb-x48-pipeline | DeepSeek-V4-Pro-0813 | 48 | pipeline | nvlink3 | infiniband_hdr | 47 | 90.37 us | 1,106.5 tok/s | 11,065.1 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 65.01 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.37 us |
| DSV4-Pro/a100_sxm_80gb-x48-tensor | DeepSeek-V4-Pro-0813 | 48 | tensor | nvlink3 | infiniband_hdr | 244 | 1,654.20 us | 60.5 tok/s | 604.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 1,272.90 us |
| DSV4-Pro/a100_sxm_80gb-x48-hybrid | DeepSeek-V4-Pro-0813 | 48 | hybrid | nvlink3 | infiniband_hdr | 127 | 406.67 us | 245.9 tok/s | 2,459.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.37 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 106.28 us | 940.9 tok/s | 9,408.9 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 75.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.44 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,659.20 us | 60.3 tok/s | 602.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 1,277.90 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 411.74 us | 242.9 tok/s | 2,428.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.44 us |
| DSV4-Pro/a100_sxm_80gb-x93-pipeline | DeepSeek-V4-Pro-0813 | 93 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x93-tensor | DeepSeek-V4-Pro-0813 | 93 | tensor | nvlink3 | infiniband_hdr | 244 | 1,671.69 us | 59.8 tok/s | 598.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/a100_sxm_80gb-x93-hybrid | DeepSeek-V4-Pro-0813 | 93 | hybrid | nvlink3 | infiniband_hdr | 133 | 437.11 us | 228.8 tok/s | 2,287.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.81 us |
| DSV4-Pro/a100_sxm_80gb-x95-pipeline | DeepSeek-V4-Pro-0813 | 95 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x95-tensor | DeepSeek-V4-Pro-0813 | 95 | tensor | nvlink3 | infiniband_hdr | 244 | 1,671.69 us | 59.8 tok/s | 598.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/a100_sxm_80gb-x95-hybrid | DeepSeek-V4-Pro-0813 | 95 | hybrid | nvlink3 | infiniband_hdr | 133 | 437.11 us | 228.8 tok/s | 2,287.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.81 us |
| DSV4-Pro/a100_sxm_80gb-x98-pipeline | DeepSeek-V4-Pro-0813 | 98 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x98-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink3 | infiniband_hdr | 244 | 1,673.04 us | 59.8 tok/s | 597.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 1,291.73 us |
| DSV4-Pro/a100_sxm_80gb-x98-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink3 | infiniband_hdr | 134 | 442.18 us | 226.1 tok/s | 2,261.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.88 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,674.19 us | 59.7 tok/s | 597.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 1,292.89 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 447.26 us | 223.6 tok/s | 2,235.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.95 us |
| DSV4-Pro/a100_sxm_80gb-x139-pipeline | DeepSeek-V4-Pro-0813 | 139 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x139-tensor | DeepSeek-V4-Pro-0813 | 139 | tensor | nvlink3 | infiniband_hdr | 244 | 1,677.52 us | 59.6 tok/s | 596.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 1,296.22 us |
| DSV4-Pro/a100_sxm_80gb-x139-hybrid | DeepSeek-V4-Pro-0813 | 139 | hybrid | nvlink3 | infiniband_hdr | 139 | 467.55 us | 213.9 tok/s | 2,138.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 86.25 us |
| DSV4-Pro/a100_sxm_80gb-x145-pipeline | DeepSeek-V4-Pro-0813 | 145 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x145-tensor | DeepSeek-V4-Pro-0813 | 145 | tensor | nvlink3 | infiniband_hdr | 244 | 1,678.14 us | 59.6 tok/s | 595.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 1,296.83 us |
| DSV4-Pro/a100_sxm_80gb-x145-hybrid | DeepSeek-V4-Pro-0813 | 145 | hybrid | nvlink3 | infiniband_hdr | 140 | 472.63 us | 211.6 tok/s | 2,115.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 91.32 us |
| DSV4-Pro/a100_sxm_80gb-x147-pipeline | DeepSeek-V4-Pro-0813 | 147 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x147-tensor | DeepSeek-V4-Pro-0813 | 147 | tensor | nvlink3 | infiniband_hdr | 244 | 1,678.14 us | 59.6 tok/s | 595.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 1,296.83 us |
| DSV4-Pro/a100_sxm_80gb-x147-hybrid | DeepSeek-V4-Pro-0813 | 147 | hybrid | nvlink3 | infiniband_hdr | 140 | 472.63 us | 211.6 tok/s | 2,115.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 91.32 us |
| DSV4-Pro/a100_sxm_80gb-x154-pipeline | DeepSeek-V4-Pro-0813 | 154 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x154-tensor | DeepSeek-V4-Pro-0813 | 154 | tensor | nvlink3 | infiniband_hdr | 244 | 1,678.69 us | 59.6 tok/s | 595.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 1,297.39 us |
| DSV4-Pro/a100_sxm_80gb-x154-hybrid | DeepSeek-V4-Pro-0813 | 154 | hybrid | nvlink3 | infiniband_hdr | 141 | 477.70 us | 209.3 tok/s | 2,093.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.40 us |
| DSV4-Pro/a100_sxm_80gb-x155-pipeline | DeepSeek-V4-Pro-0813 | 155 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x155-tensor | DeepSeek-V4-Pro-0813 | 155 | tensor | nvlink3 | infiniband_hdr | 244 | 1,678.69 us | 59.6 tok/s | 595.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 1,297.39 us |
| DSV4-Pro/a100_sxm_80gb-x155-hybrid | DeepSeek-V4-Pro-0813 | 155 | hybrid | nvlink3 | infiniband_hdr | 141 | 477.70 us | 209.3 tok/s | 2,093.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.40 us |
| DSV4-Pro/a100_sxm_80gb-x156-pipeline | DeepSeek-V4-Pro-0813 | 156 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x156-tensor | DeepSeek-V4-Pro-0813 | 156 | tensor | nvlink3 | infiniband_hdr | 244 | 1,678.69 us | 59.6 tok/s | 595.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 1,297.39 us |
| DSV4-Pro/a100_sxm_80gb-x156-hybrid | DeepSeek-V4-Pro-0813 | 156 | hybrid | nvlink3 | infiniband_hdr | 141 | 477.70 us | 209.3 tok/s | 2,093.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.40 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,679.19 us | 59.6 tok/s | 595.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 1,297.88 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 482.77 us | 207.1 tok/s | 2,071.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 101.47 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,681.69 us | 59.5 tok/s | 594.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 1,300.38 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 518.29 us | 192.9 tok/s | 1,929.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 136.98 us |
| DSV4-Pro/a100_sxm_80gb-x280-pipeline | DeepSeek-V4-Pro-0813 | 280 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x280-tensor | DeepSeek-V4-Pro-0813 | 280 | tensor | nvlink3 | infiniband_hdr | 244 | 1,683.19 us | 59.4 tok/s | 594.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 1,301.88 us |
| DSV4-Pro/a100_sxm_80gb-x280-hybrid | DeepSeek-V4-Pro-0813 | 280 | hybrid | nvlink3 | infiniband_hdr | 156 | 553.80 us | 180.6 tok/s | 1,805.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 172.50 us |
| DSV4-Pro/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Pro-0813 | 336 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Pro-0813 | 336 | tensor | nvlink3 | infiniband_hdr | 244 | 2,782.19 us | 35.9 tok/s | 359.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 2,400.88 us |
| DSV4-Pro/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Pro-0813 | 336 | hybrid | nvlink3 | infiniband_hdr | 163 | 589.31 us | 169.7 tok/s | 1,696.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 208.01 us |
| DSV4-Pro/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Pro-0813 | 448 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Pro-0813 | 448 | tensor | nvlink3 | infiniband_hdr | 244 | 2,783.43 us | 35.9 tok/s | 359.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 2,402.13 us |
| DSV4-Pro/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Pro-0813 | 448 | hybrid | nvlink3 | infiniband_hdr | 177 | 660.34 us | 151.4 tok/s | 1,514.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 279.04 us |
| DSV4-Pro/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Pro-0813 | 672 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Pro-0813 | 672 | tensor | nvlink3 | infiniband_hdr | 244 | 2,784.68 us | 35.9 tok/s | 359.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 2,403.38 us |
| DSV4-Pro/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Pro-0813 | 672 | hybrid | nvlink3 | infiniband_hdr | 182 | 685.71 us | 145.8 tok/s | 1,458.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 304.41 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 7,936.4 | 0.172 | 3,687.7 (4,890) | 7,936.4 (46,225) | 2.15x | link_latency |
| Qwen3-8B | 2 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,720.5 | 0.051 | 2,348.5 (6,520) | 4,720.5 (92,450) | 2.01x | link_latency |
| Qwen3-8B | 4 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,505.5 | 0.024 | 1,587.9 (6,520) | 4,505.5 (184,900) | 2.84x | link_latency |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 4,129.4 | 0.011 | 1,264.1 (6,520) | 4,129.4 (369,800) | 3.27x | link_latency |
| Qwen3-8B | 16 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,417.6 | 0.006 | 638.7 (6,520) | 3,417.6 (554,700) | 5.35x | link_latency |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,418.5 | 0.004 | 321.0 (6,520) | 2,418.5 (554,700) | 7.53x | kv_read |
| Qwen3-8B | 64 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,526.1 | 0.003 | 160.9 (6,520) | 1,526.1 (554,700) | 9.48x | kv_read |
| Qwen3-8B | 256 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 474.9 | 0.001 | 40.3 (6,520) | 474.9 (554,700) | 11.78x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 5,515.2 | 0.119 | 1,856.4 (14,670) | 5,515.2 (46,225) | 2.97x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 5,413.7 | 0.117 | 1,856.4 (15,485) | 5,413.7 (46,225) | 2.92x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 5,139.8 | 0.056 | 1,848.6 (15,485) | 5,139.8 (92,450) | 2.78x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,639.9 | 0.033 | 1,309.8 (15,485) | 4,639.9 (138,675) | 3.54x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 4,329.8 | 0.016 | 799.8 (15,485) | 4,329.8 (277,350) | 5.41x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,658.8 | 0.010 | 521.1 (15,485) | 3,658.8 (369,800) | 7.02x | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,062.3 | 0.006 | 263.5 (15,485) | 3,062.3 (554,700) | 11.62x | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,398.9 | 0.003 | 66.4 (15,485) | 1,398.9 (554,700) | 21.06x | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 2,653.6 | 0.029 | 679.5 (78,240) | 2,653.6 (92,450) | 3.91x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill | 231,125 | 2,197.6 | 0.010 | 640.3 (80,685) | 2,197.6 (231,125) | 3.43x | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill | 231,125 | 2,197.6 | 0.010 | 640.3 (80,685) | 2,197.6 (231,125) | 3.43x | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 2,172.5 | 0.008 | 640.3 (80,685) | 2,172.5 (277,350) | 3.39x | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,036.4 | 0.004 | 579.7 (80,685) | 2,036.4 (554,700) | 3.51x | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,432.1 | 0.003 | 331.5 (80,685) | 1,432.1 (554,700) | 4.32x | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 877.3 | 0.002 | 178.6 (80,685) | 877.3 (554,700) | 4.91x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 263.9 | 0.000 | 49.1 (80,685) | 263.9 (554,700) | 5.37x | kv_read |

## The two ROM floorplans on one die

Both machines hold the same 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. They are different floorplans, not one floorplan with two arithmetics.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 216.8 mm2 | 346.9 mm2 |
| compute block | 451.5 mm2 | 16.3 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 305.1 mm2 |
| sustained fp8 compute roof | 2.214e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.107e+14 | n/a |
| weight bytes/s the array supplies | 4.589e+13 | 4.589e+13 |
| **can the compute block be fed?** | **0.41x** | there is nothing to feed |
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
array to starve: the storage machine's 451 mm2 of MAC array can be fed at only 0.41x of what it
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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 56.8 mm2 | 1.14 mm2 (2.0%) | 14,532 mm2 | 291 mm2 | 16,478 mm2 = 20.2 reticles |
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 211.4 mm2 | 4.23 mm2 (2.0%) | 81,172 mm2 | 1,623 mm2 | 88,150 mm2 = 108.2 reticles |

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
| Qwen3-8B | 1 | sram | 12,312.6 | 13,034.9 | 13,034.9 | 0.94x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 12,312.6 | 13,034.9 | 13,034.9 | 0.94x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 13,247.0 | 13,034.9 | 13,034.9 | 1.02x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 20,931.7 | 13,034.9 | 13,034.9 | 1.61x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 32,479.4 | 13,034.9 | 13,034.9 | 2.49x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 48,964.4 | 13,034.9 | 13,034.9 | 3.76x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 73,121.2 | 13,038.0 | 13,038.0 | 5.61x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 121,568.5 | 12,332.0 | 12,332.0 | 9.86x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1 | rom | 133,002.4 | 24,131.7 | 24,131.7 | 5.51x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 2 | rom | 133,002.4 | 12,312.6 | 12,312.6 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 133,002.4 | 12,312.6 | 12,312.6 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 133,002.4 | 12,312.6 | 12,312.6 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 133,002.4 | 12,312.6 | 12,312.6 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 133,002.4 | 12,312.6 | 12,312.6 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 133,002.4 | 12,315.4 | 12,315.4 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 133,002.4 | 12,332.0 | 12,332.0 | 10.79x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 13,021.5 | 13,021.5 | 13,021.5 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 13,021.5 | 13,021.5 | 13,021.5 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 17,596.4 | 13,021.5 | 15,240.6 | 1.35x | 1.17x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | sram | 25,597.7 | 13,021.5 | 26,191.7 | 1.97x | 2.01x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 47,491.9 | 13,021.5 | 44,096.3 | 3.65x | 3.39x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 78,344.2 | 13,021.5 | 71,060.4 | 6.02x | 5.46x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 118,862.9 | 13,026.0 | 46,493.0 | 9.13x | 3.57x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 270,398.8 | 13,053.6 | 94,029.5 | 20.71x | 7.20x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 273,946.3 | 28,771.8 | 28,771.8 | 9.52x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 273,946.3 | 28,771.8 | 28,771.8 | 9.52x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 273,946.3 | 28,771.8 | 28,771.8 | 9.52x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 273,946.3 | 28,771.8 | 28,771.8 | 9.52x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 273,946.3 | 28,771.8 | 33,130.1 | 9.52x | 1.15x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 273,946.3 | 28,771.8 | 38,845.5 | 9.52x | 1.35x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 273,946.3 | 28,793.9 | 57,739.9 | 9.51x | 2.01x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 358,110.0 | 28,929.3 | 123,528.4 | 12.38x | 4.27x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 11,751.6 | 11,744.5 | 11,744.5 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 11,751.6 | 11,744.5 | 11,744.5 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 11,751.6 | 11,744.5 | 11,744.5 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 12,354.6 | 11,744.5 | 11,940.9 | 1.05x | 1.02x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 21,672.7 | 11,744.5 | 20,837.0 | 1.85x | 1.77x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 34,791.1 | 11,744.5 | 25,053.3 | 2.96x | 2.13x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 49,885.4 | 11,744.5 | 27,433.4 | 4.25x | 2.34x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 67,551.0 | 11,744.5 | 55,454.6 | 5.75x | 4.72x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 51,400.3 | 24,321.6 | 24,321.6 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 51,400.3 | 24,321.6 | 24,321.6 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 51,400.3 | 24,321.6 | 24,321.6 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 51,400.3 | 24,321.6 | 24,321.6 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 51,400.3 | 24,321.6 | 24,321.6 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 51,400.3 | 24,321.6 | 25,053.3 | 2.11x | 1.03x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 56,145.1 | 24,321.6 | 27,433.4 | 2.31x | 1.13x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 67,551.0 | 24,321.6 | 57,595.1 | 2.78x | 2.37x | kv_read | weight_read | weight_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,312.6 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 133,002.4 | 0.240 | kv_read | 10.80x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x6-perstream-romfill | 4,890 | 2.17 | 1.00 | 24,131.7 | 4.935 | weight_read | 1.96x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x6-perregion-romfill | 4,890 | 2.17 | 1.00 | 24,131.7 | 4.935 | weight_read | 1.96x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,312.6 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 133,002.4 | 0.240 | kv_read | 10.80x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 13,247.0 | 0.143 | kv_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 133,002.4 | 0.240 | kv_read | 10.04x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.98x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 0.93x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.98x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 0.93x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 20,931.7 | 0.151 | weight_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 133,002.4 | 0.240 | kv_read | 6.35x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.62x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 0.59x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.62x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 0.59x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 32,479.4 | 0.176 | kv_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 133,002.4 | 0.240 | kv_read | 4.09x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.40x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 0.38x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.40x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 0.38x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 48,964.4 | 0.177 | weight_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 133,002.4 | 0.240 | kv_read | 2.72x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.27x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 0.25x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,034.9 | 0.282 | weight_read | 0.27x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,312.6 | 0.266 | kv_read | 0.25x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 73,121.2 | 0.198 | kv_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 133,002.4 | 0.240 | kv_read | 1.82x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 13,038.0 | 0.282 | weight_read | 0.18x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.12 | 12,315.4 | 0.266 | kv_read | 0.17x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 13,038.0 | 0.282 | weight_read | 0.18x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.12 | 12,315.4 | 0.266 | kv_read | 0.17x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 121,568.5 | 0.219 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 133,002.4 | 0.240 | kv_read | 1.09x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 12,332.0 | 0.267 | kv_read | 0.10x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 4.49 | 12,332.0 | 0.267 | kv_read | 0.10x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.49 | 12,332.0 | 0.267 | kv_read | 0.10x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 4.49 | 12,332.0 | 0.267 | kv_read | 0.10x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,946.3 | 0.494 | weight_read | 21.04x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 2.21x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,946.3 | 0.494 | weight_read | 21.04x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 2.21x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 2.21x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 17,596.4 | 0.381 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,946.3 | 0.494 | weight_read | 15.57x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 0.74x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 1.64x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 1.57 | 15,240.6 | 0.330 | link_latency | 0.87x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 1.64x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 25,597.7 | 0.554 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,946.3 | 0.494 | weight_read | 10.70x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 0.51x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 1.12x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.13 | 26,191.7 | 0.567 | weight_read | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 1.12x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 47,491.9 | 0.514 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,946.3 | 0.494 | weight_read | 5.77x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 0.27x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 0.61x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.88 | 44,096.3 | 0.954 | weight_read | 0.93x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 2.88 | 33,130.1 | 0.717 | kv_read | 0.70x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 78,344.2 | 0.565 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,946.3 | 0.494 | weight_read | 3.50x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,021.5 | 0.282 | weight_read | 0.17x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,771.8 | 0.622 | weight_read | 0.37x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.03 | 71,060.4 | 1.537 | weight_read | 0.91x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 4.03 | 38,845.5 | 0.840 | kv_read | 0.50x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 118,862.9 | 0.643 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,946.3 | 0.494 | weight_read | 2.30x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 13,026.0 | 0.282 | weight_read | 0.11x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.12 | 28,793.9 | 0.623 | weight_read | 0.24x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x28-perregion | 22,820 | 1.00 | 2.88 | 46,493.0 | 2.037 | weight_read | 0.39x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x45-perregion-romfill | 36,675 | 1.64 | 2.37 | 57,739.9 | 1.574 | weight_read | 0.49x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 270,398.8 | 0.731 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 23.43 | 1.00 | 358,110.0 | 0.646 | kv_read | 1.32x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 13,053.6 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 4.49 | 28,929.3 | 0.626 | weight_read | 0.11x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x28-perregion | 22,820 | 1.00 | 5.83 | 94,029.5 | 4.120 | weight_read | 0.35x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x45-perregion-romfill | 36,675 | 1.64 | 4.67 | 123,528.4 | 3.368 | weight_read | 0.46x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.6 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,400.3 | 0.093 | weight_read | 4.37x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.6 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,400.3 | 0.093 | weight_read | 4.37x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.6 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,400.3 | 0.093 | weight_read | 4.37x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 1.00 | 1.00 | 12,354.6 | 0.053 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,400.3 | 0.093 | weight_read | 4.16x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 0.95x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion | 231,125 | 1.00 | 1.05 | 11,940.9 | 0.052 | weight_read | 0.97x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 21,672.7 | 0.078 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,400.3 | 0.093 | weight_read | 2.37x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 0.54x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 1.12x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion | 231,125 | 1.00 | 1.28 | 20,837.0 | 0.090 | weight_read | 0.96x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 1.12x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 34,791.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,400.3 | 0.093 | weight_read | 1.48x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 0.70x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion | 231,125 | 1.00 | 1.82 | 25,053.3 | 0.108 | kv_read | 0.72x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion-romfill | 231,125 | 2.07 | 1.82 | 25,053.3 | 0.108 | kv_read | 0.72x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 49,885.4 | 0.090 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4.38 | 1.00 | 56,145.1 | 0.101 | kv_read | 1.13x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 0.24x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 0.49x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion | 231,125 | 1.00 | 2.31 | 27,433.4 | 0.119 | kv_read | 0.55x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion-romfill | 231,125 | 2.07 | 2.31 | 27,433.4 | 0.119 | kv_read | 0.55x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 67,551.0 | 0.122 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4.38 | 1.00 | 67,551.0 | 0.122 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,744.5 | 0.051 | weight_read | 0.17x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,321.6 | 0.105 | weight_read | 0.36x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x147-perregion | 119,805 | 1.00 | 2.36 | 55,454.6 | 0.463 | weight_read | 0.82x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x158-perregion-romfill | 128,770 | 1.08 | 2.31 | 57,595.1 | 0.447 | weight_read | 0.85x |

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
| Qwen3-8B | 1 | 4 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 4 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 57 | 1.12 | 1.123 | 1.123 | 1.00x |
| Qwen3-8B | 256 | 5 | 51.20 | 51.200 | 51.200 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 26 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 28 | 2.29 | 1.015 | 1.192 | 1.17x |
| DeepSeek-V4-Flash-0731 | 256 | 28 | 9.14 | 1.099 | 2.232 | 2.03x |
| DeepSeek-V4-Pro-0813 | 1 | 141 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 147 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 147 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 147 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 147 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 147 | 1.74 | 1.006 | 1.066 | 1.06x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 4 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 8 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 16 | 8 | 6.36 | 3.68 | 1.73x |
| DeepSeek-V4-Flash-0731 | 32 | 8 | 7.64 | 4.38 | 1.74x |
| DeepSeek-V4-Flash-0731 | 64 | 8 | 7.98 | 5.03 | 1.59x |
| DeepSeek-V4-Flash-0731 | 256 | 8 | 8.00 | 6.01 | 1.33x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 8.16 | 4.80 | 1.70x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 12.49 | 6.22 | 2.01x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 17.73 | 9.20 | 1.93x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 7.95 | 4.78 | 1.66x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 12.44 | 6.24 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 18.57 | 9.38 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 2 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 4 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 8 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 16 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 32 | 26 | 6.52 | 4.59 | 1.42x |
| DeepSeek-V4-Flash-0731 | 64 | 26 | 11.29 | 6.18 | 1.83x |
| DeepSeek-V4-Flash-0731 | 256 | 26 | 22.79 | 10.20 | 2.23x |
| DeepSeek-V4-Flash-0731 | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 2 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 4 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 8 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 16 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 32 | 28 | 6.17 | 4.53 | 1.36x |
| DeepSeek-V4-Flash-0731 | 64 | 28 | 10.87 | 6.12 | 1.78x |
| DeepSeek-V4-Flash-0731 | 256 | 28 | 23.44 | 10.33 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 8 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 16 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 32 | 31 | 5.70 | 4.42 | 1.29x |
| DeepSeek-V4-Flash-0731 | 64 | 31 | 10.24 | 6.02 | 1.70x |
| DeepSeek-V4-Flash-0731 | 256 | 31 | 24.03 | 10.48 | 2.29x |
| DeepSeek-V4-Flash-0731 | 1 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 8 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 16 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 32 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 64 | 42 | 8.26 | 5.71 | 1.45x |
| DeepSeek-V4-Flash-0731 | 256 | 42 | 23.69 | 10.62 | 2.23x |
| DeepSeek-V4-Flash-0731 | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 8 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 16 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 32 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 64 | 44 | 7.96 | 5.66 | 1.41x |
| DeepSeek-V4-Flash-0731 | 256 | 44 | 23.39 | 10.61 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 21.14 | 10.40 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 112 | 12.78 | 8.82 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 256 | 168 | 8.87 | 7.61 | 1.17x |
| DeepSeek-V4-Flash-0731 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4-Flash-0731 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 1 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 2 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 4 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 8 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 16 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 32 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 64 | 48 | 7.42 | 5.55 | 1.34x |
| DeepSeek-V4-Pro-0813 | 256 | 48 | 22.97 | 10.64 | 2.16x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 21.37 | 10.48 | 2.04x |
| DeepSeek-V4-Pro-0813 | 1 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 8 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 16 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 32 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 256 | 93 | 15.02 | 9.23 | 1.63x |
| DeepSeek-V4-Pro-0813 | 1 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 8 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 16 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 32 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 256 | 95 | 14.76 | 9.18 | 1.61x |
| DeepSeek-V4-Pro-0813 | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 8 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 16 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 32 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 256 | 98 | 14.38 | 9.12 | 1.58x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 12.84 | 8.85 | 1.45x |
| DeepSeek-V4-Pro-0813 | 1 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 8 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 16 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 32 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 64 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 256 | 139 | 10.59 | 8.30 | 1.28x |
| DeepSeek-V4-Pro-0813 | 1 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 8 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 16 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 32 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 64 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 256 | 145 | 10.19 | 8.16 | 1.25x |
| DeepSeek-V4-Pro-0813 | 1 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 8 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 16 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 32 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 64 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 256 | 147 | 10.06 | 8.12 | 1.24x |
| DeepSeek-V4-Pro-0813 | 1 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 154 | 9.64 | 7.95 | 1.21x |
| DeepSeek-V4-Pro-0813 | 1 | 155 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 155 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 155 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 155 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 155 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 155 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 155 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 155 | 9.58 | 7.93 | 1.21x |
| DeepSeek-V4-Pro-0813 | 1 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 156 | 9.53 | 7.91 | 1.20x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 8.89 | 7.62 | 1.17x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4-Pro-0813 | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 16 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 32 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 64 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 256 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 256 | 672 | 5.98 | 5.88 | 1.02x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 0.6% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 0.4% |
| gpu | Qwen3-8B | 1 | 5.85 | 0.6% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 5.5% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 3.6% |
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
| Qwen3-8B | 1 | 4 | 40.53% | 15.04 | 9.27 |
| Qwen3-8B | 2 | 4 | 40.53% | 15.04 | 9.27 |
| Qwen3-8B | 4 | 1 | 1.14% | 6.00 | 9.27 |
| Qwen3-8B | 8 | 1 | 1.14% | 6.00 | 9.27 |
| Qwen3-8B | 16 | 1 | 1.14% | 6.00 | 9.27 |
| Qwen3-8B | 32 | 1 | 1.14% | 6.00 | 9.27 |
| Qwen3-8B | 64 | 1 | 1.27% | 6.74 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 26 | 96.88% | 53.68 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 141 | 86.61% | 253.66 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 3 | 14.37% | 51.05 | 2.08 |
| DeepSeek-V4-Pro-0813 | 4 | 3 | 14.37% | 51.05 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,271.5 | 6,357.6 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,271.5 | 6,357.6 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,271.5 | 6,357.6 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 799.2 | 6,393.7 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 401.5 | 6,424.1 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 201.2 | 6,439.4 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 100.7 | 6,447.1 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 25.2 | 6,452.9 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 531.5 | 9,566.7 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 531.5 | 9,566.7 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 531.5 | 9,566.7 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 531.5 | 9,566.7 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 531.5 | 9,566.7 |
| DeepSeek-V4-Flash-0731 | 32 | 4.13% | 13.8 GB | 8.30% | 180.85 TB/s | 2,179.91 TB/s | 301.9 | 9,659.2 |
| DeepSeek-V4-Flash-0731 | 64 | 8.09% | 19.7 GB | 11.79% | 256.94 TB/s | 2,179.91 TB/s | 151.9 | 9,719.6 |
| DeepSeek-V4-Flash-0731 | 256 | 28.63% | 49.9 GB | 29.90% | 651.89 TB/s | 2,179.91 TB/s | 38.1 | 9,765.4 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.8 | 8,714.7 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.8 | 8,714.7 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.8 | 8,714.7 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.8 | 8,714.7 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.8 | 8,714.7 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.8 | 8,714.7 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.8 | 8,714.7 |
| DeepSeek-V4-Pro-0813 | 256 | 4.11% | 60.6 GB | 6.79% | 792.00 TB/s | 11,661.57 TB/s | 34.3 | 8,776.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 4 |
| gpu | kv_read | 31 |
| gpu | link_latency | 260 |
| gpu | weight_read | 753 |
| rom | compute | 99 |
| rom | infeasible | 1592 |
| rom | kv_read | 464 |
| rom | link_latency | 708 |
| rom | weight_read | 849 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 4 |
| rom | CAPACITY | 1592 |

## Mechanical consistency audit

**PASS** over 80,371 checks.

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

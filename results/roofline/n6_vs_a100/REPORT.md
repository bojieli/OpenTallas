# Area-constrained roofline: n6_vs_a100

> Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 76.6 us, or 13,063 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **The ROM advantage is a batch-1, per-user advantage, and it is large.** At equal area the best batch-1 point is Qwen3-8B on 1,630 mm2 of ROM silicon at 10,819 tok/s per user, against 1,652 mm2 of a100_sxm_80gb-x2-pipeline at 191 tok/s: **57x**. Both sides bind on `weight_read`, and the whole difference is that one reads its weights from HBM and the other from an on-die array.
3. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on Qwen3-8B at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 672 stages and 1,299 us of link latency per token; but the model has 36 layers, so at most 36 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 67 us. The iso-area per-user ratio at that point falls from 78.3x to 5.2x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
4. **Giving the GPU the same topology sweep the ROM side gets changes almost nothing, and that is itself a result about this model.** Pipeline, tensor and hybrid are all evaluated at every cluster size and the best is never more than 1.00x the pipeline-only answer. The reason is structural: this model computes the service time on the machine's **aggregate** memory bandwidth and compute roof whatever the parallelism, so tensor parallelism buys a token nothing here and only costs it two all-reduces per layer. The asymmetry that mattered was never the choice of topology -- it was the serial depth each topology was charged, and that is what the layer cap above fixes. A model that priced a pipeline stage's service time on that stage's own silicon would rank these topologies differently, and this one does not; see the open item on the pipeline service-time rule.
5. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.17x (Qwen3-8B, ROM binding on `link_latency`) to 4.03x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
6. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 92.6% at batch 256, while the weight-read time is identical at both. Aggregate throughput rises from 6,924 to 9,670 tok/s on the same machine. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
7. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 2,786 us over NVLink, capping per-user decode at 359 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 1,435.9 us and cap it at 696 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 2.0x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. Both studies consequently choose pipeline over tensor parallelism on the wafer at every operating point.
8. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 24 of 24 operating points and an array 0; on tokens per second per square millimetre the same points go 18 to the array and 6 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
9. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 1343 of 4473 feasible points.
10. **The largest open question is not in this model's inputs but in the architecture, and the anchor cannot settle it.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 37.8x of aggregate throughput (DeepSeek-V4-Flash-0731). The machines are identical at batch 1, which is where the published anchor sits, so no amount of validation against it resolves the fork.
11. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 8.38x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 2.30x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 37 of 48 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
12. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.

## The overlap and serialisation rule

```
t_memory  = t_weight + t_kv        weights and KV share one memory system
t_memory  = max(t_weight, t_kv)    weights and KV are separate arrays
t_service = max(t_memory, t_compute)
t_token   = t_service / stage_balance + t_link
t_token  *= thermal_scale
```

Compute overlaps memory. Weight and KV traffic **add** on a GPU because they
contend for the same HBM channels, and **overlap** on a ROM part because the
mask ROM and the KV store are physically separate arrays -- that single rule
is most of the architectural difference and it is stated rather than hidden
in an efficiency factor. Hop and collective latency is **added** to the
critical path at every batch size, because decode is sequential across
layers and a pipelined array supplies no parallelism at batch 1. Per-user
latency is the full serial traversal, so `aggregate = batch x per-user rate`
holds by construction.

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

| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | GPU parallelism | GPU link us | GPU user tok/s | GPU aggregate tok/s | GPU binds on | Per-user ratio | Aggregate ratio | PP-only ratio | Ratio without the layer cap |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---:|
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 59,341.0 | 59,341.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 66.66 | 11,351.1 | 11,351.1 | link_latency | 5.23x | 5.23x | 5.23x | 78.34x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-fp8-SRAMKV-array-pipeline-x2 | 1,630 | 10,818.7 | 10,818.7 | weight_read | Qwen3-8B/a100_sxm_80gb-x2-pipeline | 1,652 | 0.99x | pipeline | 1.53 | 190.6 | 190.6 | weight_read | 56.76x | 56.76x | 56.76x | 56.76x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 41,056.5 | 82,112.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 68.81 | 10,940.1 | 21,880.2 | link_latency | 3.75x | 3.75x | 3.75x | 56.03x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x8 | 6,520 | 4,753.8 | 9,507.7 | kv_read | Qwen3-8B/a100_sxm_80gb-x8-pipeline | 6,608 | 0.99x | pipeline | 10.88 | 702.6 | 1,405.1 | weight_read | 6.77x | 6.77x | 6.77x | 6.77x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 25,402.2 | 101,609.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 73.13 | 10,201.3 | 40,805.3 | link_latency | 2.49x | 2.49x | 2.49x | 36.92x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x8 | 6,520 | 2,473.0 | 9,892.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x8-pipeline | 6,608 | 0.99x | pipeline | 11.26 | 618.3 | 2,473.1 | weight_read | 4.00x | 4.00x | 4.00x | 4.00x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14,412.0 | 115,296.4 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 81.76 | 8,987.5 | 71,900.0 | link_latency | 1.60x | 1.60x | 1.60x | 23.51x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x8 | 6,520 | 1,262.0 | 10,096.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x8-pipeline | 6,608 | 0.99x | pipeline | 12.03 | 498.7 | 3,989.2 | weight_read | 2.53x | 2.53x | 2.53x | 2.53x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 7,726.4 | 123,622.8 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 99.02 | 7,259.9 | 116,157.7 | link_latency | 1.06x | 1.06x | 1.06x | 15.35x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x8 | 6,520 | 637.6 | 10,201.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x8-pipeline | 6,608 | 0.99x | pipeline | 13.56 | 359.5 | 5,752.4 | kv_read | 1.77x | 1.77x | 1.77x | 1.77x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 4,007.9 | 128,253.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 133.53 | 5,243.8 | 167,802.7 | link_latency | 0.76x | 0.76x | 0.76x | 10.81x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x8 | 6,520 | 320.5 | 10,254.8 | kv_read | Qwen3-8B/a100_sxm_80gb-x8-pipeline | 6,608 | 0.99x | pipeline | 16.62 | 230.8 | 7,384.3 | kv_read | 1.39x | 1.39x | 1.39x | 1.39x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 2,042.2 | 130,702.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 202.56 | 3,371.4 | 215,769.5 | link_latency | 0.61x | 0.61x | 0.61x | 8.41x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x8 | 6,520 | 160.7 | 10,281.7 | kv_read | Qwen3-8B/a100_sxm_80gb-x8-pipeline | 6,608 | 0.99x | pipeline | 22.73 | 134.5 | 8,604.8 | kv_read | 1.19x | 1.19x | 1.19x | 1.19x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 518.0 | 132,600.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 616.75 | 1,072.9 | 274,652.0 | link_latency | 0.48x | 0.48x | 0.48x | 6.55x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x8 | 6,520 | 40.2 | 10,302.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x8-pipeline | 6,608 | 0.99x | pipeline | 59.43 | 38.4 | 9,822.5 | kv_read | 1.05x | 1.05x | 1.05x | 1.05x |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x12-romfill | 554,700 | 57,260.3 | 57,260.3 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 80.65 | 2,110.6 | 2,110.6 | weight_read | 27.13x | 27.13x | 27.13x | 96.88x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x18 | 14,670 | 7,855.7 | 7,855.7 | weight_read | DSV4-Flash/a100_sxm_80gb-x18-pipeline | 14,868 | 0.99x | pipeline | 32.56 | 1,099.2 | 1,099.2 | weight_read | 7.15x | 7.15x | 7.15x | 7.15x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 56,127.7 | 112,255.4 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 83.30 | 1,987.7 | 3,975.4 | weight_read | 28.24x | 28.24x | 28.24x | 98.89x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 4,037.7 | 8,075.4 | compute | DSV4-Flash/a100_sxm_80gb-x18-pipeline | 14,868 | 0.99x | pipeline | 33.63 | 825.5 | 1,651.0 | weight_read | 4.89x | 4.89x | 4.89x | 4.89x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 45,953.1 | 183,812.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 88.59 | 1,689.2 | 6,756.9 | weight_read | 27.20x | 27.20x | 27.20x | 88.78x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 2,201.9 | 8,807.4 | compute | DSV4-Flash/a100_sxm_80gb-x18-pipeline | 14,868 | 0.99x | pipeline | 35.76 | 592.7 | 2,371.0 | weight_read | 3.71x | 3.71x | 3.71x | 3.71x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 33,725.7 | 269,805.4 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 99.19 | 1,294.8 | 10,358.4 | weight_read | 26.05x | 26.05x | 26.05x | 76.71x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 1,153.2 | 9,225.6 | compute | DSV4-Flash/a100_sxm_80gb-x18-pipeline | 14,868 | 0.99x | pipeline | 40.02 | 406.8 | 3,254.4 | weight_read | 2.83x | 2.83x | 2.83x | 2.83x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 22,011.7 | 352,187.8 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 120.38 | 1,069.2 | 17,106.5 | weight_read | 20.59x | 20.59x | 20.59x | 60.81x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 590.6 | 9,450.0 | compute | DSV4-Flash/a100_sxm_80gb-x18-pipeline | 14,868 | 0.99x | pipeline | 48.54 | 272.3 | 4,357.1 | weight_read | 2.17x | 2.17x | 2.17x | 2.17x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 12,988.9 | 415,644.1 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 162.76 | 875.8 | 28,025.7 | weight_read | 14.83x | 14.83x | 14.83x | 47.00x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 298.9 | 9,566.3 | compute | DSV4-Flash/a100_sxm_80gb-x18-pipeline | 14,868 | 0.99x | pipeline | 65.58 | 184.6 | 5,905.8 | weight_read | 1.62x | 1.62x | 1.62x | 1.62x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 7,137.4 | 456,796.3 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 247.52 | 706.7 | 45,228.6 | weight_read | 10.10x | 10.10x | 10.10x | 37.05x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 150.4 | 9,625.5 | compute | DSV4-Flash/a100_sxm_80gb-x18-pipeline | 14,868 | 0.99x | pipeline | 99.66 | 133.3 | 8,531.4 | weight_read | 1.13x | 1.13x | 1.13x | 1.13x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1,927.5 | 493,437.1 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-pipeline | 555,072 | 1.00x | pipeline | 756.08 | 478.0 | 122,360.9 | weight_read | 4.03x | 4.03x | 4.03x | 26.34x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 37.8 | 9,670.4 | compute | DSV4-Flash/a100_sxm_80gb-x18-pipeline | 14,868 | 0.99x | pipeline | 304.13 | 88.5 | 22,657.0 | weight_read | 0.43x | 0.43x | 0.43x | 0.43x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 27,021.8 | 27,021.8 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x1063-pipeline | 878,038 | 1.00x | pipeline | 117.55 | 650.6 | 650.6 | weight_read | 41.53x | 41.53x | 41.53x | 95.35x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x94 | 76,610 | 4,168.7 | 4,168.7 | link_latency | DSV4-Pro/a100_sxm_80gb-x93-pipeline | 76,818 | 1.00x | pipeline | 117.55 | 525.5 | 525.5 | weight_read | 7.93x | 7.93x | 7.93x | 8.20x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 23,718.8 | 47,437.6 | kv_read | DSV4-Pro/a100_sxm_80gb-x1063-pipeline | 878,038 | 1.00x | pipeline | 124.09 | 621.0 | 1,242.1 | weight_read | 38.19x | 38.19x | 38.19x | 88.13x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x96 | 78,240 | 2,742.7 | 5,485.4 | compute | DSV4-Pro/a100_sxm_80gb-x95-pipeline | 78,470 | 1.00x | pipeline | 124.09 | 416.6 | 833.2 | weight_read | 6.58x | 6.58x | 6.58x | 6.78x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 16,757.6 | 67,030.5 | kv_read | DSV4-Pro/a100_sxm_80gb-x1063-pipeline | 878,038 | 1.00x | pipeline | 137.19 | 542.1 | 2,168.5 | weight_read | 30.91x | 30.91x | 30.91x | 70.00x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x96 | 78,240 | 1,654.4 | 6,617.5 | compute | DSV4-Pro/a100_sxm_80gb-x95-pipeline | 78,470 | 1.00x | pipeline | 137.19 | 307.7 | 1,230.7 | weight_read | 5.38x | 5.38x | 5.38x | 5.51x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 10,559.5 | 84,475.9 | kv_read | DSV4-Pro/a100_sxm_80gb-x1063-pipeline | 878,038 | 1.00x | pipeline | 163.37 | 412.9 | 3,303.0 | weight_read | 25.58x | 25.58x | 25.58x | 55.00x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x96 | 78,240 | 922.4 | 7,379.0 | compute | DSV4-Pro/a100_sxm_80gb-x95-pipeline | 78,470 | 1.00x | pipeline | 163.37 | 229.9 | 1,839.3 | weight_read | 4.01x | 4.01x | 4.01x | 4.10x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6,069.6 | 97,113.3 | kv_read | DSV4-Pro/a100_sxm_80gb-x1063-pipeline | 878,038 | 1.00x | pipeline | 215.75 | 325.7 | 5,210.8 | weight_read | 18.64x | 18.64x | 18.64x | 41.07x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x96 | 78,240 | 489.3 | 7,829.4 | compute | DSV4-Pro/a100_sxm_80gb-x95-pipeline | 78,470 | 1.00x | pipeline | 215.75 | 165.7 | 2,650.5 | weight_read | 2.95x | 2.95x | 2.95x | 3.01x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 3,280.1 | 104,964.6 | kv_read | DSV4-Pro/a100_sxm_80gb-x1063-pipeline | 878,038 | 1.00x | pipeline | 320.50 | 272.9 | 8,733.7 | weight_read | 12.02x | 12.02x | 12.02x | 30.10x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x96 | 78,240 | 252.4 | 8,075.9 | compute | DSV4-Pro/a100_sxm_80gb-x95-pipeline | 78,470 | 1.00x | pipeline | 320.50 | 118.1 | 3,779.3 | weight_read | 2.14x | 2.14x | 2.14x | 2.18x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 1,709.2 | 109,386.3 | kv_read | DSV4-Pro/a100_sxm_80gb-x1063-pipeline | 878,038 | 1.00x | pipeline | 529.99 | 214.2 | 13,707.1 | weight_read | 7.98x | 7.98x | 7.98x | 23.62x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x96 | 78,240 | 128.2 | 8,205.0 | compute | DSV4-Pro/a100_sxm_80gb-x95-pipeline | 78,470 | 1.00x | pipeline | 529.99 | 85.8 | 5,488.5 | weight_read | 1.49x | 1.49x | 1.49x | 1.53x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 441.2 | 112,955.0 | kv_read | DSV4-Pro/a100_sxm_80gb-x1063-pipeline | 878,038 | 1.00x | pipeline | 1,786.97 | 145.3 | 37,195.9 | weight_read | 3.04x | 3.04x | 3.04x | 16.70x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x96 | 78,240 | 32.4 | 8,304.6 | compute | DSV4-Pro/a100_sxm_80gb-x95-pipeline | 78,470 | 1.00x | pipeline | 1,786.97 | 52.5 | 13,431.0 | weight_read | 0.62x | 0.62x | 0.62x | 0.65x |

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
| DeepSeek-V4-Flash-0731 | 14,670 | 7.62x | 7.15x | 5.12x |
| DeepSeek-V4-Flash-0731 | 15,485 | 7.37x | 6.89x | 4.89x |
| DeepSeek-V4-Flash-0731 | 46,225 | 12.24x | 11.98x | 11.31x |
| DeepSeek-V4-Flash-0731 | 92,450 | 16.18x | 15.48x | 13.45x |
| DeepSeek-V4-Flash-0731 | 138,675 | 19.63x | 18.39x | 14.95x |
| DeepSeek-V4-Flash-0731 | 184,900 | 22.20x | 20.46x | 15.89x |
| DeepSeek-V4-Flash-0731 | 277,350 | 25.76x | 23.24x | 16.99x |
| DeepSeek-V4-Flash-0731 | 369,800 | 28.13x | 25.00x | 17.63x |
| DeepSeek-V4-Flash-0731 | 554,700 | 31.07x | 27.13x | 18.32x |
| DeepSeek-V4-Pro-0813 | 76,610 | 9.00x | 7.93x | 4.61x |
| DeepSeek-V4-Pro-0813 | 77,425 | — | 8.41x | 4.38x |
| DeepSeek-V4-Pro-0813 | 78,240 | 10.11x | 8.76x | 4.84x |
| DeepSeek-V4-Pro-0813 | 79,870 | 9.91x | 8.61x | 4.79x |
| DeepSeek-V4-Pro-0813 | 92,450 | 17.75x | 16.73x | 14.87x |
| DeepSeek-V4-Pro-0813 | 138,675 | 17.72x | 16.64x | 14.71x |
| DeepSeek-V4-Pro-0813 | 184,900 | 21.72x | 20.00x | 16.86x |
| DeepSeek-V4-Pro-0813 | 231,125 | 15.80x | 22.96x | 18.59x |
| DeepSeek-V4-Pro-0813 | 277,350 | 28.55x | 25.41x | 19.92x |
| DeepSeek-V4-Pro-0813 | 369,800 | 34.00x | 29.47x | 21.92x |
| DeepSeek-V4-Pro-0813 | 554,700 | 42.45x | 35.35x | 24.47x |
| Qwen3-8B | 1,630 | 57.07x | 56.76x | 54.45x |
| Qwen3-8B | 3,260 | 27.97x | 27.54x | 24.58x |
| Qwen3-8B | 5,705 | 49.08x | 44.81x | 20.08x |
| Qwen3-8B | 6,520 | 45.24x | 40.51x | 9.58x |
| Qwen3-8B | 7,335 | 11.46x | 11.04x | 8.89x |
| Qwen3-8B | 8,150 | — | 22.12x | 8.27x |
| Qwen3-8B | 8,965 | 23.04x | 20.58x | — |
| Qwen3-8B | 46,225 | 14.90x | 13.94x | 11.91x |
| Qwen3-8B | 92,450 | 8.57x | 8.45x | 8.76x |
| Qwen3-8B | 138,675 | 6.75x | 6.86x | 7.84x |
| Qwen3-8B | 184,900 | 5.85x | 6.07x | 7.37x |
| Qwen3-8B | 277,350 | 4.94x | 5.28x | 6.91x |
| Qwen3-8B | 369,800 | 4.49x | 4.88x | 6.68x |
| Qwen3-8B | 554,700 | 4.82x | 5.23x | 7.03x |

## The GPU's own topology choice, at batch 1

Every cluster size in the study, under each parallelism it can
actually run. `pipeline` is what this study charged the GPU before,
at every size; `hybrid` is tensor-parallel inside the NVLink domain
and pipeline-parallel across it, which is what a real deployment of
this size runs. A blank cell is a topology that collapses onto
another at that size and is not emitted twice.

| Model | GPUs | mm2 | Pipeline tok/s | Tensor tok/s | Hybrid tok/s | Best | Best link us | Link share | Binds on |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 8 | 6,608 | 711.3 | 602.7 | — | pipeline | 10.69 | 0.8% | weight_read |
| DeepSeek-V4-Flash-0731 | 18 | 14,868 | 1,099.2 | 507.2 | 868.8 | pipeline | 32.56 | 3.6% | weight_read |
| DeepSeek-V4-Flash-0731 | 19 | 15,694 | 1,126.2 | 513.3 | 886.8 | pipeline | 34.09 | 3.8% | weight_read |
| DeepSeek-V4-Flash-0731 | 26 | 21,476 | 1,272.8 | 543.7 | 984.0 | pipeline | 48.08 | 6.1% | weight_read |
| DeepSeek-V4-Flash-0731 | 28 | 23,128 | 1,306.4 | 550.7 | 1,007.1 | pipeline | 51.14 | 6.7% | weight_read |
| DeepSeek-V4-Flash-0731 | 29 | 23,954 | 1,321.9 | 553.9 | 1,017.8 | pipeline | 52.67 | 7.0% | weight_read |
| DeepSeek-V4-Flash-0731 | 30 | 24,780 | 1,336.6 | 556.9 | 1,028.2 | pipeline | 54.19 | 7.2% | weight_read |
| DeepSeek-V4-Flash-0731 | 39 | 32,214 | 1,433.1 | 577.3 | 1,098.9 | pipeline | 71.24 | 10.2% | weight_read |
| DeepSeek-V4-Flash-0731 | 42 | 34,692 | 1,450.9 | 581.8 | 1,113.1 | pipeline | 79.12 | 11.5% | weight_read |
| DeepSeek-V4-Flash-0731 | 44 | 36,344 | 1,468.5 | 585.2 | 1,125.4 | pipeline | 80.65 | 11.8% | weight_read |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 1,572.1 | 600.2 | 1,178.5 | pipeline | 80.65 | 12.7% | weight_read |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 1,818.0 | 630.5 | 1,255.8 | pipeline | 80.65 | 14.7% | weight_read |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 1,922.7 | 641.8 | 1,249.7 | pipeline | 80.65 | 15.5% | weight_read |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 1,980.7 | 647.7 | 1,221.4 | pipeline | 80.65 | 16.0% | weight_read |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 2,043.2 | 434.1 | 1,148.3 | pipeline | 80.65 | 16.5% | weight_read |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 2,076.2 | 435.5 | 1,152.2 | pipeline | 80.65 | 16.7% | weight_read |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 2,110.6 | 436.9 | 1,162.7 | pipeline | 80.65 | 17.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 48 | 39,648 | 449.5 | 264.0 | 393.5 | pipeline | 90.37 | 4.1% | weight_read |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 467.3 | 270.8 | 408.9 | pipeline | 106.28 | 5.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 93 | 76,818 | 525.5 | 289.3 | 450.0 | pipeline | 117.55 | 6.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 94 | 77,644 | 526.6 | 289.6 | 450.8 | pipeline | 117.55 | 6.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 95 | 78,470 | 527.8 | 289.9 | 451.6 | pipeline | 117.55 | 6.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 97 | 80,122 | 529.9 | 290.5 | 452.2 | pipeline | 117.55 | 6.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 544.3 | 294.7 | 461.5 | pipeline | 117.55 | 6.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 139 | 114,814 | 563.8 | 300.0 | 470.9 | pipeline | 117.55 | 6.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 145 | 119,770 | 567.3 | 300.9 | 472.2 | pipeline | 117.55 | 6.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 154 | 127,204 | 572.2 | 302.2 | 474.4 | pipeline | 117.55 | 6.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 156 | 128,856 | 573.2 | 302.5 | 475.1 | pipeline | 117.55 | 6.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 578.8 | 304.0 | 477.8 | pipeline | 117.55 | 6.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 598.1 | 309.0 | 482.5 | pipeline | 117.55 | 7.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 610.5 | 312.1 | 482.1 | pipeline | 117.55 | 7.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 619.0 | 233.6 | 479.1 | pipeline | 117.55 | 7.3% | weight_read |
| DeepSeek-V4-Pro-0813 | 356 | 294,056 | 621.5 | 234.0 | 477.1 | pipeline | 117.55 | 7.3% | weight_read |
| DeepSeek-V4-Pro-0813 | 358 | 295,708 | 621.7 | 234.0 | 477.2 | pipeline | 117.55 | 7.3% | weight_read |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 630.1 | 235.1 | 469.5 | pipeline | 117.55 | 7.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 641.7 | 236.7 | 470.3 | pipeline | 117.55 | 7.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 1063 | 878,038 | 650.6 | 237.8 | 475.0 | pipeline | 117.55 | 7.6% | weight_read |
| Qwen3-8B | 2 | 1,652 | 190.6 | 183.0 | — | pipeline | 1.53 | 0.0% | weight_read |
| Qwen3-8B | 4 | 3,304 | 380.2 | 351.4 | — | pipeline | 4.58 | 0.2% | weight_read |
| Qwen3-8B | 5 | 4,130 | 474.5 | 430.6 | — | pipeline | 6.11 | 0.3% | weight_read |
| Qwen3-8B | 7 | 5,782 | 661.4 | 580.1 | — | pipeline | 9.16 | 0.6% | weight_read |
| Qwen3-8B | 8 | 6,608 | 753.9 | 650.7 | — | pipeline | 10.69 | 0.8% | weight_read |
| Qwen3-8B | 9 | 7,434 | 843.4 | 482.0 | 716.3 | pipeline | 15.52 | 1.3% | weight_read |
| Qwen3-8B | 10 | 8,260 | 933.9 | 510.7 | 781.4 | pipeline | 17.05 | 1.6% | weight_read |
| Qwen3-8B | 11 | 9,086 | 1,023.5 | 536.8 | 844.3 | pipeline | 18.57 | 1.9% | weight_read |
| Qwen3-8B | 12 | 9,912 | 1,112.1 | 560.7 | 904.9 | pipeline | 20.10 | 2.2% | weight_read |
| Qwen3-8B | 16 | 13,216 | 1,455.7 | 638.9 | 1,127.7 | pipeline | 26.21 | 3.8% | weight_read |
| Qwen3-8B | 56 | 46,256 | 3,851.8 | 890.6 | 2,256.9 | pipeline | 66.66 | 25.7% | weight_read |
| Qwen3-8B | 112 | 92,512 | 6,021.8 | 966.8 | 2,608.7 | pipeline | 66.66 | 40.1% | weight_read |
| Qwen3-8B | 168 | 138,768 | 7,414.2 | 995.2 | 2,591.1 | pipeline | 66.66 | 49.4% | link_latency |
| Qwen3-8B | 224 | 185,024 | 8,383.4 | 1,010.1 | 2,474.4 | pipeline | 66.66 | 55.9% | link_latency |
| Qwen3-8B | 336 | 277,536 | 9,644.1 | 616.0 | 2,341.0 | pipeline | 66.66 | 64.3% | link_latency |
| Qwen3-8B | 448 | 370,048 | 10,428.2 | 618.8 | 2,384.5 | pipeline | 66.66 | 69.5% | link_latency |
| Qwen3-8B | 672 | 555,072 | 11,351.1 | 621.7 | 2,429.7 | pipeline | 66.66 | 75.7% | link_latency |

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
| Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x4 | Qwen3-8B | 4 | pipeline | nvlink3 | infiniband_hdr | 3 | 4.58 us | 21,824.9 tok/s | 218,249.1 tok/s | 3 x point_to_point span 2 on nvlink3 (traversals 1.0) = 4.58 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 3.50 us | 28,571.3 tok/s | 285,713.4 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 3.50 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x4 | Qwen3-8B | 4 | tensor | nvlink3 | infiniband_hdr | 72 | 220.42 us | 453.7 tok/s | 4,536.7 tok/s | 72 x all_reduce span 4 on nvlink3 (traversals 2.0) = 220.42 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 110.88 us | 901.9 tok/s | 9,018.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 110.88 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | Qwen3-8B | 9 | pipeline | nvlink3 | infiniband_hdr | 8 | 15.52 us | 6,443.8 tok/s | 64,437.9 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.69 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 3.50 us | 28,571.3 tok/s | 285,713.4 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 3.50 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x8 | Qwen3-8B | 8 | tensor | nvlink3 | infiniband_hdr | 72 | 221.16 us | 452.2 tok/s | 4,521.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 110.88 us | 901.9 tok/s | 9,018.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 110.88 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-hybrid-x9 | Qwen3-8B | 9 | hybrid | nvlink3 | infiniband_hdr | 73 | 225.99 us | 442.5 tok/s | 4,425.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/ROM-N6-fp8-SRAMKV-array-pipeline-x2 | Qwen3-8B | 2 | pipeline | nvlink3 | infiniband_hdr | 1 | 1.53 us | 65,474.7 tok/s | 654,747.4 tok/s | 1 x point_to_point span 2 on nvlink3 (traversals 1.0) = 1.53 us |
| Qwen3-8B/ROM-N6-fp8-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 3.50 us | 28,571.3 tok/s | 285,713.4 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 3.50 us |
| Qwen3-8B/ROM-N6-fp8-SRAMKV-array-tensor-x2 | Qwen3-8B | 2 | tensor | nvlink3 | infiniband_hdr | 72 | 218.95 us | 456.7 tok/s | 4,567.3 tok/s | 72 x all_reduce span 2 on nvlink3 (traversals 2.0) = 218.95 us |
| Qwen3-8B/ROM-N6-fp8-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 110.88 us | 901.9 tok/s | 9,018.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 110.88 us |
| Qwen3-8B/ROM-N6-fp8-HBMKV-array-pipeline-x9 | Qwen3-8B | 9 | pipeline | nvlink3 | infiniband_hdr | 8 | 15.52 us | 6,443.8 tok/s | 64,437.9 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.69 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/ROM-N6-fp8-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 3.50 us | 28,571.3 tok/s | 285,713.4 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 3.50 us |
| Qwen3-8B/ROM-N6-fp8-HBMKV-array-tensor-x8 | Qwen3-8B | 8 | tensor | nvlink3 | infiniband_hdr | 72 | 221.16 us | 452.2 tok/s | 4,521.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us |
| Qwen3-8B/ROM-N6-fp8-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 110.88 us | 901.9 tok/s | 9,018.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 110.88 us |
| Qwen3-8B/ROM-N6-fp8-HBMKV-array-hybrid-x9 | Qwen3-8B | 9 | hybrid | nvlink3 | infiniband_hdr | 73 | 225.99 us | 442.5 tok/s | 4,425.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x2-pipeline | Qwen3-8B | 2 | pipeline | nvlink3 | infiniband_hdr | 1 | 1.53 us | 65,474.7 tok/s | 654,747.4 tok/s | 1 x point_to_point span 2 on nvlink3 (traversals 1.0) = 1.53 us |
| Qwen3-8B/a100_sxm_80gb-x2-tensor | Qwen3-8B | 2 | tensor | nvlink3 | infiniband_hdr | 72 | 218.95 us | 456.7 tok/s | 4,567.3 tok/s | 72 x all_reduce span 2 on nvlink3 (traversals 2.0) = 218.95 us |
| Qwen3-8B/a100_sxm_80gb-x4-pipeline | Qwen3-8B | 4 | pipeline | nvlink3 | infiniband_hdr | 3 | 4.58 us | 21,824.9 tok/s | 218,249.1 tok/s | 3 x point_to_point span 2 on nvlink3 (traversals 1.0) = 4.58 us |
| Qwen3-8B/a100_sxm_80gb-x4-tensor | Qwen3-8B | 4 | tensor | nvlink3 | infiniband_hdr | 72 | 220.42 us | 453.7 tok/s | 4,536.7 tok/s | 72 x all_reduce span 4 on nvlink3 (traversals 2.0) = 220.42 us |
| Qwen3-8B/a100_sxm_80gb-x5-pipeline | Qwen3-8B | 5 | pipeline | nvlink3 | infiniband_hdr | 4 | 6.11 us | 16,368.7 tok/s | 163,686.8 tok/s | 4 x point_to_point span 2 on nvlink3 (traversals 1.0) = 6.11 us |
| Qwen3-8B/a100_sxm_80gb-x5-tensor | Qwen3-8B | 5 | tensor | nvlink3 | infiniband_hdr | 72 | 220.72 us | 453.1 tok/s | 4,530.7 tok/s | 72 x all_reduce span 5 on nvlink3 (traversals 2.0) = 220.72 us |
| Qwen3-8B/a100_sxm_80gb-x7-pipeline | Qwen3-8B | 7 | pipeline | nvlink3 | infiniband_hdr | 6 | 9.16 us | 10,912.5 tok/s | 109,124.6 tok/s | 6 x point_to_point span 2 on nvlink3 (traversals 1.0) = 9.16 us |
| Qwen3-8B/a100_sxm_80gb-x7-tensor | Qwen3-8B | 7 | tensor | nvlink3 | infiniband_hdr | 72 | 221.06 us | 452.4 tok/s | 4,523.7 tok/s | 72 x all_reduce span 7 on nvlink3 (traversals 2.0) = 221.06 us |
| Qwen3-8B/a100_sxm_80gb-x8-pipeline | Qwen3-8B | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 10.69 us | 9,353.5 tok/s | 93,535.3 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.69 us |
| Qwen3-8B/a100_sxm_80gb-x8-tensor | Qwen3-8B | 8 | tensor | nvlink3 | infiniband_hdr | 72 | 221.16 us | 452.2 tok/s | 4,521.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us |
| Qwen3-8B/a100_sxm_80gb-x9-pipeline | Qwen3-8B | 9 | pipeline | nvlink3 | infiniband_hdr | 8 | 15.52 us | 6,443.8 tok/s | 64,437.9 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.69 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x9-tensor | Qwen3-8B | 9 | tensor | nvlink3 | infiniband_hdr | 144 | 904.55 us | 110.6 tok/s | 1,105.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 683.39 us |
| Qwen3-8B/a100_sxm_80gb-x9-hybrid | Qwen3-8B | 9 | hybrid | nvlink3 | infiniband_hdr | 73 | 225.99 us | 442.5 tok/s | 4,425.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x10-pipeline | Qwen3-8B | 10 | pipeline | nvlink3 | infiniband_hdr | 9 | 17.05 us | 5,866.4 tok/s | 58,664.3 tok/s | 8 x point_to_point span 2 on nvlink3 (traversals 1.0) = 12.22 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x10-tensor | Qwen3-8B | 10 | tensor | nvlink3 | infiniband_hdr | 144 | 904.55 us | 110.6 tok/s | 1,105.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 683.39 us |
| Qwen3-8B/a100_sxm_80gb-x10-hybrid | Qwen3-8B | 10 | hybrid | nvlink3 | infiniband_hdr | 73 | 225.99 us | 442.5 tok/s | 4,425.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x11-pipeline | Qwen3-8B | 11 | pipeline | nvlink3 | infiniband_hdr | 10 | 18.57 us | 5,384.0 tok/s | 53,840.3 tok/s | 9 x point_to_point span 2 on nvlink3 (traversals 1.0) = 13.75 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x11-tensor | Qwen3-8B | 11 | tensor | nvlink3 | infiniband_hdr | 144 | 904.55 us | 110.6 tok/s | 1,105.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 683.39 us |
| Qwen3-8B/a100_sxm_80gb-x11-hybrid | Qwen3-8B | 11 | hybrid | nvlink3 | infiniband_hdr | 73 | 225.99 us | 442.5 tok/s | 4,425.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x12-pipeline | Qwen3-8B | 12 | pipeline | nvlink3 | infiniband_hdr | 11 | 20.10 us | 4,974.9 tok/s | 49,749.4 tok/s | 10 x point_to_point span 2 on nvlink3 (traversals 1.0) = 15.27 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x12-tensor | Qwen3-8B | 12 | tensor | nvlink3 | infiniband_hdr | 144 | 904.55 us | 110.6 tok/s | 1,105.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 683.39 us |
| Qwen3-8B/a100_sxm_80gb-x12-hybrid | Qwen3-8B | 12 | hybrid | nvlink3 | infiniband_hdr | 73 | 225.99 us | 442.5 tok/s | 4,425.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x16-pipeline | Qwen3-8B | 16 | pipeline | nvlink3 | infiniband_hdr | 15 | 26.21 us | 3,815.3 tok/s | 38,153.4 tok/s | 14 x point_to_point span 2 on nvlink3 (traversals 1.0) = 21.38 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
| Qwen3-8B/a100_sxm_80gb-x16-tensor | Qwen3-8B | 16 | tensor | nvlink3 | infiniband_hdr | 144 | 904.55 us | 110.6 tok/s | 1,105.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 683.39 us |
| Qwen3-8B/a100_sxm_80gb-x16-hybrid | Qwen3-8B | 16 | hybrid | nvlink3 | infiniband_hdr | 73 | 225.99 us | 442.5 tok/s | 4,425.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 221.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.83 us |
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
| DSV4-Flash/a100_sxm_80gb-x29-pipeline | DeepSeek-V4-Flash-0731 | 29 | pipeline | nvlink3 | infiniband_hdr | 28 | 52.67 us | 1,898.8 tok/s | 18,987.7 tok/s | 25 x point_to_point span 2 on nvlink3 (traversals 1.0) = 38.18 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x29-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink3 | infiniband_hdr | 172 | 1,101.57 us | 90.8 tok/s | 907.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 837.41 us |
| DSV4-Flash/a100_sxm_80gb-x29-hybrid | DeepSeek-V4-Flash-0731 | 29 | hybrid | nvlink3 | infiniband_hdr | 89 | 278.65 us | 358.9 tok/s | 3,588.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x30-pipeline | DeepSeek-V4-Flash-0731 | 30 | pipeline | nvlink3 | infiniband_hdr | 29 | 54.19 us | 1,845.3 tok/s | 18,452.6 tok/s | 26 x point_to_point span 2 on nvlink3 (traversals 1.0) = 39.71 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x30-tensor | DeepSeek-V4-Flash-0731 | 30 | tensor | nvlink3 | infiniband_hdr | 172 | 1,101.57 us | 90.8 tok/s | 907.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 837.41 us |
| DSV4-Flash/a100_sxm_80gb-x30-hybrid | DeepSeek-V4-Flash-0731 | 30 | hybrid | nvlink3 | infiniband_hdr | 89 | 278.65 us | 358.9 tok/s | 3,588.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x39-pipeline | DeepSeek-V4-Flash-0731 | 39 | pipeline | nvlink3 | infiniband_hdr | 38 | 71.24 us | 1,403.7 tok/s | 14,037.2 tok/s | 34 x point_to_point span 2 on nvlink3 (traversals 1.0) = 51.93 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| DSV4-Flash/a100_sxm_80gb-x39-tensor | DeepSeek-V4-Flash-0731 | 39 | tensor | nvlink3 | infiniband_hdr | 172 | 1,105.80 us | 90.4 tok/s | 904.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 841.63 us |
| DSV4-Flash/a100_sxm_80gb-x39-hybrid | DeepSeek-V4-Flash-0731 | 39 | hybrid | nvlink3 | infiniband_hdr | 90 | 283.48 us | 352.8 tok/s | 3,527.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 264.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
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
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x95 | DeepSeek-V4-Pro-0813 | 95 | hybrid | nvlink3 | infiniband_hdr | 133 | 437.11 us | 228.8 tok/s | 2,287.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.81 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4-Pro-0813 | 2 | hybrid | on_wafer | inter_wafer | 123 | 192.98 us | 518.2 tok/s | 5,182.0 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | DeepSeek-V4-Pro-0813 | 98 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5 | DeepSeek-V4-Pro-0813 | 5 | pipeline | on_wafer | inter_wafer | 60 | 11.00 us | 9,094.5 tok/s | 90,945.4 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.90 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x96 | DeepSeek-V4-Pro-0813 | 96 | tensor | nvlink3 | infiniband_hdr | 244 | 1,671.69 us | 59.8 tok/s | 598.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x5 | DeepSeek-V4-Pro-0813 | 5 | tensor | on_wafer | inter_wafer | 244 | 1,435.86 us | 69.6 tok/s | 696.4 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 187.88 us; 122 x all_reduce span 5 on inter_wafer (traversals 2.0) = 1,247.98 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x98 | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink3 | infiniband_hdr | 134 | 442.18 us | 226.1 tok/s | 2,261.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.88 us |
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
| DSV4-Pro/a100_sxm_80gb-x94-pipeline | DeepSeek-V4-Pro-0813 | 94 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x94-tensor | DeepSeek-V4-Pro-0813 | 94 | tensor | nvlink3 | infiniband_hdr | 244 | 1,671.69 us | 59.8 tok/s | 598.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/a100_sxm_80gb-x94-hybrid | DeepSeek-V4-Pro-0813 | 94 | hybrid | nvlink3 | infiniband_hdr | 133 | 437.11 us | 228.8 tok/s | 2,287.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.81 us |
| DSV4-Pro/a100_sxm_80gb-x95-pipeline | DeepSeek-V4-Pro-0813 | 95 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x95-tensor | DeepSeek-V4-Pro-0813 | 95 | tensor | nvlink3 | infiniband_hdr | 244 | 1,671.69 us | 59.8 tok/s | 598.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/a100_sxm_80gb-x95-hybrid | DeepSeek-V4-Pro-0813 | 95 | hybrid | nvlink3 | infiniband_hdr | 133 | 437.11 us | 228.8 tok/s | 2,287.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.81 us |
| DSV4-Pro/a100_sxm_80gb-x97-pipeline | DeepSeek-V4-Pro-0813 | 97 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x97-tensor | DeepSeek-V4-Pro-0813 | 97 | tensor | nvlink3 | infiniband_hdr | 244 | 1,673.04 us | 59.8 tok/s | 597.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 1,291.73 us |
| DSV4-Pro/a100_sxm_80gb-x97-hybrid | DeepSeek-V4-Pro-0813 | 97 | hybrid | nvlink3 | infiniband_hdr | 134 | 442.18 us | 226.1 tok/s | 2,261.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.88 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,674.19 us | 59.7 tok/s | 597.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 1,292.89 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 447.26 us | 223.6 tok/s | 2,235.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.95 us |
| DSV4-Pro/a100_sxm_80gb-x139-pipeline | DeepSeek-V4-Pro-0813 | 139 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x139-tensor | DeepSeek-V4-Pro-0813 | 139 | tensor | nvlink3 | infiniband_hdr | 244 | 1,677.52 us | 59.6 tok/s | 596.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 1,296.22 us |
| DSV4-Pro/a100_sxm_80gb-x139-hybrid | DeepSeek-V4-Pro-0813 | 139 | hybrid | nvlink3 | infiniband_hdr | 139 | 467.55 us | 213.9 tok/s | 2,138.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 86.25 us |
| DSV4-Pro/a100_sxm_80gb-x145-pipeline | DeepSeek-V4-Pro-0813 | 145 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x145-tensor | DeepSeek-V4-Pro-0813 | 145 | tensor | nvlink3 | infiniband_hdr | 244 | 1,678.14 us | 59.6 tok/s | 595.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 1,296.83 us |
| DSV4-Pro/a100_sxm_80gb-x145-hybrid | DeepSeek-V4-Pro-0813 | 145 | hybrid | nvlink3 | infiniband_hdr | 140 | 472.63 us | 211.6 tok/s | 2,115.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 91.32 us |
| DSV4-Pro/a100_sxm_80gb-x154-pipeline | DeepSeek-V4-Pro-0813 | 154 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x154-tensor | DeepSeek-V4-Pro-0813 | 154 | tensor | nvlink3 | infiniband_hdr | 244 | 1,678.69 us | 59.6 tok/s | 595.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 1,297.39 us |
| DSV4-Pro/a100_sxm_80gb-x154-hybrid | DeepSeek-V4-Pro-0813 | 154 | hybrid | nvlink3 | infiniband_hdr | 141 | 477.70 us | 209.3 tok/s | 2,093.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.40 us |
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
| DSV4-Pro/a100_sxm_80gb-x356-pipeline | DeepSeek-V4-Pro-0813 | 356 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x356-tensor | DeepSeek-V4-Pro-0813 | 356 | tensor | nvlink3 | infiniband_hdr | 244 | 2,782.52 us | 35.9 tok/s | 359.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 2,401.22 us |
| DSV4-Pro/a100_sxm_80gb-x356-hybrid | DeepSeek-V4-Pro-0813 | 356 | hybrid | nvlink3 | infiniband_hdr | 166 | 604.54 us | 165.4 tok/s | 1,654.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 223.23 us |
| DSV4-Pro/a100_sxm_80gb-x358-pipeline | DeepSeek-V4-Pro-0813 | 358 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x358-tensor | DeepSeek-V4-Pro-0813 | 358 | tensor | nvlink3 | infiniband_hdr | 244 | 2,782.52 us | 35.9 tok/s | 359.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 2,401.22 us |
| DSV4-Pro/a100_sxm_80gb-x358-hybrid | DeepSeek-V4-Pro-0813 | 358 | hybrid | nvlink3 | infiniband_hdr | 166 | 604.54 us | 165.4 tok/s | 1,654.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 223.23 us |
| DSV4-Pro/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Pro-0813 | 448 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Pro-0813 | 448 | tensor | nvlink3 | infiniband_hdr | 244 | 2,783.43 us | 35.9 tok/s | 359.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 2,402.13 us |
| DSV4-Pro/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Pro-0813 | 448 | hybrid | nvlink3 | infiniband_hdr | 177 | 660.34 us | 151.4 tok/s | 1,514.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 279.04 us |
| DSV4-Pro/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Pro-0813 | 672 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Pro-0813 | 672 | tensor | nvlink3 | infiniband_hdr | 244 | 2,784.68 us | 35.9 tok/s | 359.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 2,403.38 us |
| DSV4-Pro/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Pro-0813 | 672 | hybrid | nvlink3 | infiniband_hdr | 182 | 685.71 us | 145.8 tok/s | 1,458.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 304.41 us |
| DSV4-Pro/a100_sxm_80gb-x1063-pipeline | DeepSeek-V4-Pro-0813 | 1063 | pipeline | nvlink3 | infiniband_hdr | 60 | 117.55 us | 850.7 tok/s | 8,507.3 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 82.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x1063-tensor | DeepSeek-V4-Pro-0813 | 1063 | tensor | nvlink3 | infiniband_hdr | 244 | 2,785.60 us | 35.9 tok/s | 359.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 122 x all_reduce span 133 on infiniband_hdr (traversals 4.0) = 2,404.30 us |
| DSV4-Pro/a100_sxm_80gb-x1063-hybrid | DeepSeek-V4-Pro-0813 | 1063 | hybrid | nvlink3 | infiniband_hdr | 182 | 685.71 us | 145.8 tok/s | 1,458.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 381.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 304.41 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 59,341.0 | 0.107 | 29,634.1 (5,705) | 59,341.0 (554,700) | 2.00x | kv_read |
| Qwen3-8B | 2 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 41,056.5 | 0.074 | 7,717.2 (13,040) | 41,056.5 (554,700) | 5.32x | kv_read |
| Qwen3-8B | 4 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 25,402.2 | 0.046 | 4,389.5 (13,040) | 25,402.2 (554,700) | 5.79x | kv_read |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14,412.0 | 0.026 | 2,356.9 (13,040) | 14,412.0 (554,700) | 6.11x | kv_read |
| Qwen3-8B | 16 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 7,726.4 | 0.014 | 1,223.7 (13,040) | 7,726.4 (554,700) | 6.31x | kv_read |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 4,007.9 | 0.007 | 623.8 (13,040) | 4,007.9 (554,700) | 6.43x | kv_read |
| Qwen3-8B | 64 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 2,042.2 | 0.004 | 315.0 (13,040) | 2,042.2 (554,700) | 6.48x | kv_read |
| Qwen3-8B | 256 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 518.0 | 0.001 | 79.3 (13,040) | 518.0 (554,700) | 6.53x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x12-romfill | 554,700 | 57,260.3 | 0.103 | 7,855.7 (14,670) | 57,260.3 (554,700) | 7.29x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 56,127.7 | 0.101 | 6,172.4 (15,485) | 56,127.7 (554,700) | 9.09x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 45,953.1 | 0.083 | 3,554.3 (15,485) | 45,953.1 (554,700) | 12.93x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 33,725.7 | 0.061 | 1,923.0 (15,485) | 33,725.7 (554,700) | 17.54x | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 22,011.7 | 0.040 | 1,002.6 (15,485) | 22,011.7 (554,700) | 21.95x | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 12,988.9 | 0.023 | 512.3 (15,485) | 12,988.9 (554,700) | 25.36x | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 7,137.4 | 0.013 | 259.0 (15,485) | 7,137.4 (554,700) | 27.56x | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1,927.5 | 0.003 | 65.3 (15,485) | 1,927.5 (554,700) | 29.53x | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 27,021.8 | 0.031 | 4,430.6 (77,425) | 27,021.8 (878,275) | 6.10x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 23,718.8 | 0.027 | 3,188.7 (79,870) | 23,718.8 (878,275) | 7.44x | kv_read |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 16,757.6 | 0.019 | 1,990.1 (79,870) | 16,757.6 (878,275) | 8.42x | kv_read |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 10,559.5 | 0.012 | 1,136.1 (79,870) | 10,559.5 (878,275) | 9.29x | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6,069.6 | 0.007 | 611.4 (79,870) | 6,069.6 (878,275) | 9.93x | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 3,280.1 | 0.004 | 317.8 (79,870) | 3,280.1 (878,275) | 10.32x | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 1,709.2 | 0.002 | 162.1 (79,870) | 1,709.2 (878,275) | 10.54x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 441.2 | 0.001 | 41.2 (79,870) | 441.2 (878,275) | 10.72x | kv_read |

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
| Qwen3-8B | 1 | sram | 11,641.5 | 11,641.5 | 11,641.5 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 21,185.2 | 12,311.3 | 12,311.3 | 1.72x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 42,370.3 | 12,675.9 | 12,675.9 | 3.34x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 84,740.6 | 12,866.5 | 12,866.5 | 6.59x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 123,622.8 | 12,963.9 | 12,963.9 | 9.54x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 128,253.9 | 13,013.2 | 13,013.2 | 9.86x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 130,702.0 | 13,038.0 | 13,038.0 | 10.02x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 132,600.3 | 12,332.0 | 12,332.0 | 10.75x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1 | rom | 59,341.0 | 53,701.4 | 53,701.4 | 1.11x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 82,112.9 | 36,780.6 | 36,780.6 | 2.23x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 101,609.0 | 40,239.0 | 40,239.0 | 2.53x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 115,296.4 | 42,224.1 | 42,224.1 | 2.73x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 123,622.8 | 43,291.9 | 43,291.9 | 2.86x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 128,253.9 | 43,846.4 | 43,846.4 | 2.93x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 130,702.0 | 44,128.9 | 44,128.9 | 2.96x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 132,600.3 | 44,343.3 | 44,343.3 | 2.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 11,058.9 | 11,058.9 | 11,058.9 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 22,117.9 | 11,977.7 | 19,906.6 | 1.85x | 1.66x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 40,432.4 | 12,496.7 | 29,802.7 | 3.24x | 2.38x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 80,864.8 | 12,773.5 | 45,146.9 | 6.33x | 3.53x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 161,729.4 | 12,916.6 | 68,200.8 | 12.52x | 5.28x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 323,458.1 | 12,989.3 | 99,354.5 | 24.90x | 7.65x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 456,796.3 | 13,026.0 | 96,967.7 | 35.07x | 7.44x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 493,437.1 | 13,053.6 | 109,418.2 | 37.80x | 8.38x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 57,260.3 | 42,777.8 | 42,777.8 | 1.34x | 1.00x | layer_fixed_latency | layer_fixed_latency | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | rom | 112,255.4 | 60,522.6 | 77,802.5 | 1.85x | 1.29x | layer_fixed_latency | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 183,812.2 | 76,600.0 | 106,551.4 | 2.40x | 1.39x | layer_fixed_latency | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 269,805.4 | 88,332.4 | 130,698.8 | 3.05x | 1.48x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 352,187.8 | 95,658.2 | 147,401.4 | 3.68x | 1.54x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 415,644.1 | 99,796.4 | 157,462.8 | 4.16x | 1.58x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 456,796.3 | 102,002.8 | 163,026.7 | 4.48x | 1.60x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 493,437.1 | 103,722.6 | 167,464.8 | 4.76x | 1.61x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 9,107.3 | 9,107.3 | 9,107.3 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 18,198.8 | 10,258.7 | 17,019.9 | 1.77x | 1.66x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 36,334.5 | 10,951.0 | 27,280.2 | 3.32x | 2.49x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 59,206.4 | 11,333.3 | 27,709.2 | 5.22x | 2.44x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 65,148.2 | 11,534.7 | 35,894.6 | 5.65x | 3.11x | kv_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | sram | 68,590.0 | 11,638.1 | 49,819.2 | 5.89x | 4.28x | kv_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | sram | 70,450.9 | 11,690.5 | 55,177.2 | 6.03x | 4.72x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 71,914.3 | 11,730.1 | 60,018.4 | 6.13x | 5.12x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 27,021.8 | 28,137.6 | 28,137.6 | 0.96x | 1.00x | layer_fixed_latency | layer_fixed_latency | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 2 | rom | 47,437.6 | 43,073.5 | 47,437.6 | 1.10x | 1.10x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 67,030.5 | 58,636.0 | 67,030.5 | 1.14x | 1.14x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 84,475.9 | 71,564.1 | 84,475.9 | 1.18x | 1.18x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 97,113.3 | 80,430.8 | 97,113.3 | 1.21x | 1.21x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 104,964.6 | 85,742.5 | 104,964.6 | 1.22x | 1.22x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 109,386.3 | 88,670.5 | 109,386.3 | 1.23x | 1.23x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 112,955.0 | 91,001.1 | 112,955.0 | 1.24x | 1.24x | kv_read | weight_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 11,641.5 | 0.252 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 59,341.0 | 0.107 | kv_read | 5.10x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 11,641.5 | 0.252 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.61 | 1.00 | 53,701.4 | 1.162 | kv_read | 4.61x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 11,641.5 | 0.252 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.61 | 1.00 | 53,701.4 | 1.162 | kv_read | 4.61x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x3 | 138,675 | 1.00 | 1.00 | 21,185.2 | 0.153 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 82,112.9 | 0.148 | kv_read | 3.88x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 2.00 | 12,311.3 | 0.266 | weight_read | 0.58x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 90.38 | 2.00 | 36,780.6 | 0.199 | kv_read | 1.74x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 2.00 | 12,311.3 | 0.266 | weight_read | 0.58x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 90.38 | 2.00 | 36,780.6 | 0.199 | kv_read | 1.74x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x6 | 277,350 | 1.00 | 1.00 | 42,370.3 | 0.153 | weight_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 101,609.0 | 0.183 | kv_read | 2.40x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.00 | 12,675.9 | 0.274 | weight_read | 0.30x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 90.38 | 4.00 | 40,239.0 | 0.218 | kv_read | 0.95x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.00 | 12,675.9 | 0.274 | weight_read | 0.30x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 90.38 | 4.00 | 40,239.0 | 0.218 | kv_read | 0.95x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 84,740.6 | 0.153 | weight_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 115,296.4 | 0.208 | kv_read | 1.36x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 8.00 | 12,866.5 | 0.278 | weight_read | 0.15x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 90.38 | 8.00 | 42,224.1 | 0.228 | kv_read | 0.50x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 8.00 | 12,866.5 | 0.278 | weight_read | 0.15x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 90.38 | 8.00 | 42,224.1 | 0.228 | kv_read | 0.50x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 123,622.8 | 0.223 | kv_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 123,622.8 | 0.223 | kv_read | 1.00x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 16.00 | 12,963.9 | 0.280 | weight_read | 0.10x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 90.38 | 16.00 | 43,291.9 | 0.234 | kv_read | 0.35x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 16.00 | 12,963.9 | 0.280 | weight_read | 0.10x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 90.38 | 16.00 | 43,291.9 | 0.234 | kv_read | 0.35x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 128,253.9 | 0.231 | kv_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 128,253.9 | 0.231 | kv_read | 1.00x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 32.00 | 13,013.2 | 0.282 | weight_read | 0.10x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 90.38 | 32.00 | 43,846.4 | 0.237 | kv_read | 0.34x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 32.00 | 13,013.2 | 0.282 | weight_read | 0.10x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 90.38 | 32.00 | 43,846.4 | 0.237 | kv_read | 0.34x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 130,702.0 | 0.236 | kv_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 130,702.0 | 0.236 | kv_read | 1.00x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 64.00 | 13,038.0 | 0.282 | weight_read | 0.10x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 90.38 | 64.00 | 44,128.9 | 0.239 | kv_read | 0.34x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 64.00 | 13,038.0 | 0.282 | weight_read | 0.10x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 90.38 | 64.00 | 44,128.9 | 0.239 | kv_read | 0.34x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 132,600.3 | 0.239 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 132,600.3 | 0.239 | kv_read | 1.00x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 256.00 | 12,332.0 | 0.267 | kv_read | 0.09x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 90.38 | 256.00 | 44,343.3 | 0.240 | kv_read | 0.33x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 256.00 | 12,332.0 | 0.267 | kv_read | 0.09x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 90.38 | 256.00 | 44,343.3 | 0.240 | kv_read | 0.33x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 11,058.9 | 0.239 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x12-romfill | 554,700 | 23.68 | 1.00 | 57,260.3 | 0.103 | layer_fixed_latency | 5.18x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 11,058.9 | 0.239 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 8.95 | 1.00 | 42,777.8 | 0.231 | layer_fixed_latency | 3.87x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 11,058.9 | 0.239 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 8.95 | 1.00 | 42,777.8 | 0.231 | layer_fixed_latency | 3.87x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 22,117.9 | 0.478 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 112,255.4 | 0.202 | layer_fixed_latency | 5.08x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 2.00 | 11,977.7 | 0.259 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 8.87 | 2.00 | 60,522.6 | 0.327 | weight_read | 2.74x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.13 | 19,906.6 | 0.431 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 8.87 | 1.13 | 77,802.5 | 0.421 | kv_read | 3.52x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 40,432.4 | 0.437 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 183,812.2 | 0.331 | layer_fixed_latency | 4.55x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.00 | 12,496.7 | 0.270 | weight_read | 0.31x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 8.87 | 4.00 | 76,600.0 | 0.414 | weight_read | 1.89x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.57 | 29,802.7 | 0.645 | weight_read | 0.74x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 8.87 | 1.57 | 106,551.4 | 0.576 | kv_read | 2.64x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3 | 138,675 | 1.00 | 1.00 | 80,864.8 | 0.583 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 269,805.4 | 0.486 | kv_read | 3.34x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 8.00 | 12,773.5 | 0.276 | weight_read | 0.16x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 8.87 | 8.00 | 88,332.4 | 0.478 | weight_read | 1.09x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 2.13 | 45,146.9 | 0.977 | weight_read | 0.56x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 8.87 | 2.13 | 130,698.8 | 0.707 | kv_read | 1.62x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6 | 277,350 | 1.00 | 1.00 | 161,729.4 | 0.583 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 352,187.8 | 0.635 | kv_read | 2.18x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 16.00 | 12,916.6 | 0.279 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 8.87 | 16.00 | 95,658.2 | 0.517 | weight_read | 0.59x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 2.88 | 68,200.8 | 1.475 | weight_read | 0.42x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 8.87 | 2.88 | 147,401.4 | 0.797 | kv_read | 0.91x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 323,458.1 | 0.583 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 415,644.1 | 0.749 | kv_read | 1.29x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 32.00 | 12,989.3 | 0.281 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 8.87 | 32.00 | 99,796.4 | 0.540 | weight_read | 0.31x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.03 | 99,354.5 | 2.149 | weight_read | 0.31x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 8.87 | 4.03 | 157,462.8 | 0.852 | kv_read | 0.49x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 456,796.3 | 0.824 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 456,796.3 | 0.824 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 64.00 | 13,026.0 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 8.87 | 64.00 | 102,002.8 | 0.552 | weight_read | 0.22x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x28-perregion | 22,820 | 1.00 | 5.83 | 96,967.7 | 4.249 | weight_read | 0.21x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 8.87 | 5.83 | 163,026.7 | 0.882 | kv_read | 0.36x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 493,437.1 | 0.890 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 493,437.1 | 0.890 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 256.00 | 13,053.6 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 8.87 | 256.00 | 103,722.6 | 0.561 | weight_read | 0.21x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x28-perregion | 22,820 | 1.00 | 13.84 | 109,418.2 | 4.795 | kv_read | 0.22x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 8.87 | 13.84 | 167,464.8 | 0.906 | kv_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 9,107.3 | 0.099 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6.94 | 1.00 | 27,021.8 | 0.031 | layer_fixed_latency | 2.97x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 9,107.3 | 0.066 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perstream-romfill | 878,275 | 7.88 | 1.00 | 28,137.6 | 0.032 | layer_fixed_latency | 3.09x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 9,107.3 | 0.066 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perregion-romfill | 878,275 | 7.88 | 1.00 | 28,137.6 | 0.032 | layer_fixed_latency | 3.09x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5 | 231,125 | 1.00 | 1.00 | 18,198.8 | 0.079 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6.94 | 1.00 | 47,437.6 | 0.054 | kv_read | 2.61x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 2.00 | 10,258.7 | 0.074 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perstream-romfill | 878,275 | 7.88 | 2.00 | 43,073.5 | 0.049 | weight_read | 2.37x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.09 | 17,019.9 | 0.123 | weight_read | 0.94x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perregion-romfill | 878,275 | 7.88 | 1.09 | 47,437.6 | 0.054 | kv_read | 2.61x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x8 | 369,800 | 1.00 | 1.00 | 36,334.5 | 0.098 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6.94 | 1.00 | 67,030.5 | 0.076 | kv_read | 1.84x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 4.00 | 10,951.0 | 0.079 | weight_read | 0.30x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perstream-romfill | 878,275 | 7.88 | 4.00 | 58,636.0 | 0.067 | weight_read | 1.61x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.43 | 27,280.2 | 0.197 | weight_read | 0.75x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perregion-romfill | 878,275 | 7.88 | 1.43 | 67,030.5 | 0.076 | kv_read | 1.84x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 59,206.4 | 0.107 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6.94 | 1.00 | 84,475.9 | 0.096 | kv_read | 1.43x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 8.00 | 11,333.3 | 0.049 | weight_read | 0.19x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perstream-romfill | 878,275 | 7.88 | 8.00 | 71,564.1 | 0.081 | weight_read | 1.21x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.99 | 27,709.2 | 0.120 | kv_read | 0.47x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perregion-romfill | 878,275 | 7.88 | 1.99 | 84,475.9 | 0.096 | kv_read | 1.43x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 65,148.2 | 0.117 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6.94 | 1.00 | 97,113.3 | 0.111 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 16.00 | 11,534.7 | 0.050 | weight_read | 0.18x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perstream-romfill | 878,275 | 7.88 | 16.00 | 80,430.8 | 0.092 | weight_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x147-perregion | 119,805 | 1.00 | 2.54 | 35,894.6 | 0.300 | link_latency | 0.55x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perregion-romfill | 878,275 | 7.88 | 2.54 | 97,113.3 | 0.111 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 68,590.0 | 0.124 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6.94 | 1.00 | 104,964.6 | 0.120 | kv_read | 1.53x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 32.00 | 11,638.1 | 0.050 | weight_read | 0.17x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perstream-romfill | 878,275 | 7.88 | 32.00 | 85,742.5 | 0.098 | weight_read | 1.25x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x147-perregion | 119,805 | 1.00 | 3.49 | 49,819.2 | 0.416 | link_latency | 0.73x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perregion-romfill | 878,275 | 7.88 | 3.49 | 104,964.6 | 0.120 | kv_read | 1.53x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 70,450.9 | 0.127 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6.94 | 1.00 | 109,386.3 | 0.125 | kv_read | 1.55x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 64.00 | 11,690.5 | 0.051 | weight_read | 0.17x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perstream-romfill | 878,275 | 7.88 | 64.00 | 88,670.5 | 0.101 | weight_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x147-perregion | 119,805 | 1.00 | 4.92 | 55,177.2 | 0.461 | kv_read | 0.78x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perregion-romfill | 878,275 | 7.88 | 4.92 | 109,386.3 | 0.125 | kv_read | 1.55x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 71,914.3 | 0.130 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-romfill | 878,275 | 6.94 | 1.00 | 112,955.0 | 0.129 | kv_read | 1.57x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 256.00 | 11,730.1 | 0.051 | weight_read | 0.16x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perstream-romfill | 878,275 | 7.88 | 256.00 | 91,001.1 | 0.104 | weight_read | 1.27x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x147-perregion | 119,805 | 1.00 | 10.96 | 60,018.4 | 0.501 | kv_read | 0.83x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x19-perregion-romfill | 878,275 | 7.88 | 10.96 | 112,955.0 | 0.129 | kv_read | 1.57x |

## What the completeness corrections cost

Four terms the model priced wrongly or not at all. Each row is
computed from the evaluated points, not restated from prose.

### 1. Per-region sweep depth: the busiest region, not the mean

The compute-in-ROM per-region machine used to charge `batch * k /
(N * coverage)` -- the load of the AVERAGE engaged region -- and then
divide it by a flat 0.85 whose own note said the depth is set by the
busiest region. The busiest region is now computed from the routing
distribution. The correction is not a constant: it is a function of
batch.

| Model | B | Mean engaged region | Busiest region | Correction |
|---|---:|---:|---:|---:|
| Qwen3-8B | 1 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 2.000 | 2.000 | 1.00x |
| Qwen3-8B | 4 | 4.000 | 4.000 | 1.00x |
| Qwen3-8B | 8 | 8.000 | 8.000 | 1.00x |
| Qwen3-8B | 16 | 16.000 | 16.000 | 1.00x |
| Qwen3-8B | 32 | 32.000 | 32.000 | 1.00x |
| Qwen3-8B | 64 | 64.000 | 64.000 | 1.00x |
| Qwen3-8B | 256 | 256.000 | 256.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 1.012 | 1.131 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 1.036 | 1.572 | 1.52x |
| DeepSeek-V4-Flash-0731 | 8 | 1.085 | 2.134 | 1.97x |
| DeepSeek-V4-Flash-0731 | 16 | 1.188 | 2.883 | 2.43x |
| DeepSeek-V4-Flash-0731 | 32 | 1.410 | 4.026 | 2.85x |
| DeepSeek-V4-Flash-0731 | 64 | 1.921 | 5.831 | 3.04x |
| DeepSeek-V4-Flash-0731 | 256 | 6.014 | 13.844 | 2.30x |
| DeepSeek-V4-Pro-0813 | 1 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 1.008 | 1.089 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 1.024 | 1.430 | 1.40x |
| DeepSeek-V4-Pro-0813 | 8 | 1.056 | 1.992 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 1.122 | 2.542 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 1.263 | 3.488 | 2.76x |
| DeepSeek-V4-Pro-0813 | 64 | 1.575 | 4.922 | 3.13x |
| DeepSeek-V4-Pro-0813 | 256 | 4.072 | 10.965 | 2.69x |

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
| DeepSeek-V4-Flash-0731 | 2 | 8 | 6.36 | 3.68 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 8 | 7.64 | 4.38 | 1.74x |
| DeepSeek-V4-Flash-0731 | 8 | 8 | 7.98 | 5.03 | 1.59x |
| DeepSeek-V4-Flash-0731 | 16 | 8 | 8.00 | 5.58 | 1.43x |
| DeepSeek-V4-Flash-0731 | 32 | 8 | 8.00 | 6.01 | 1.33x |
| DeepSeek-V4-Flash-0731 | 64 | 8 | 8.00 | 6.29 | 1.27x |
| DeepSeek-V4-Flash-0731 | 256 | 8 | 8.00 | 6.45 | 1.24x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 8.86 | 5.03 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 13.21 | 6.47 | 2.04x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 16.56 | 7.99 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 17.82 | 9.44 | 1.89x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 17.99 | 10.67 | 1.69x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 18.00 | 11.53 | 1.56x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 8.99 | 5.12 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 13.57 | 6.62 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 17.26 | 8.21 | 2.10x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 18.76 | 9.75 | 1.92x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 18.99 | 11.05 | 1.72x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 19.00 | 11.97 | 1.59x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 2 | 26 | 9.67 | 5.64 | 1.71x |
| DeepSeek-V4-Flash-0731 | 4 | 26 | 15.52 | 7.51 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 26 | 21.41 | 9.57 | 2.24x |
| DeepSeek-V4-Flash-0731 | 16 | 26 | 24.91 | 11.64 | 2.14x |
| DeepSeek-V4-Flash-0731 | 32 | 26 | 25.88 | 13.47 | 1.92x |
| DeepSeek-V4-Flash-0731 | 64 | 26 | 25.99 | 14.79 | 1.76x |
| DeepSeek-V4-Flash-0731 | 256 | 26 | 26.00 | 15.62 | 1.66x |
| DeepSeek-V4-Flash-0731 | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 2 | 28 | 9.81 | 5.76 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 28 | 15.94 | 7.73 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 28 | 22.40 | 9.90 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 28 | 26.52 | 12.12 | 2.19x |
| DeepSeek-V4-Flash-0731 | 32 | 28 | 27.80 | 14.09 | 1.97x |
| DeepSeek-V4-Flash-0731 | 64 | 28 | 27.98 | 15.53 | 1.80x |
| DeepSeek-V4-Flash-0731 | 256 | 28 | 28.00 | 16.42 | 1.70x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 9.87 | 5.82 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 16.14 | 7.83 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 22.86 | 10.06 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 27.30 | 12.35 | 2.21x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 28.76 | 14.39 | 2.00x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 28.97 | 15.88 | 1.82x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 1 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 30 | 9.93 | 5.88 | 1.69x |
| DeepSeek-V4-Flash-0731 | 4 | 30 | 16.32 | 7.93 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 30 | 23.31 | 10.22 | 2.28x |
| DeepSeek-V4-Flash-0731 | 16 | 30 | 28.06 | 12.57 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 30 | 29.70 | 14.68 | 2.02x |
| DeepSeek-V4-Flash-0731 | 64 | 30 | 29.97 | 16.23 | 1.85x |
| DeepSeek-V4-Flash-0731 | 256 | 30 | 29.99 | 17.20 | 1.74x |
| DeepSeek-V4-Flash-0731 | 1 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 2 | 39 | 10.34 | 6.32 | 1.64x |
| DeepSeek-V4-Flash-0731 | 4 | 39 | 17.64 | 8.71 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 39 | 26.64 | 11.45 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 39 | 34.22 | 14.37 | 2.38x |
| DeepSeek-V4-Flash-0731 | 32 | 39 | 37.86 | 17.07 | 2.22x |
| DeepSeek-V4-Flash-0731 | 64 | 39 | 38.78 | 19.11 | 2.03x |
| DeepSeek-V4-Flash-0731 | 256 | 39 | 38.95 | 20.40 | 1.91x |
| DeepSeek-V4-Flash-0731 | 1 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 42 | 10.44 | 6.45 | 1.62x |
| DeepSeek-V4-Flash-0731 | 4 | 42 | 17.97 | 8.93 | 2.01x |
| DeepSeek-V4-Flash-0731 | 8 | 42 | 27.54 | 11.80 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 42 | 36.01 | 14.90 | 2.42x |
| DeepSeek-V4-Flash-0731 | 32 | 42 | 40.42 | 17.79 | 2.27x |
| DeepSeek-V4-Flash-0731 | 64 | 42 | 41.66 | 19.97 | 2.09x |
| DeepSeek-V4-Flash-0731 | 256 | 42 | 41.91 | 21.37 | 1.96x |
| DeepSeek-V4-Flash-0731 | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 44 | 10.50 | 6.53 | 1.61x |
| DeepSeek-V4-Flash-0731 | 4 | 44 | 18.17 | 9.06 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 44 | 28.09 | 12.03 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 44 | 37.14 | 15.23 | 2.44x |
| DeepSeek-V4-Flash-0731 | 32 | 44 | 42.08 | 18.24 | 2.31x |
| DeepSeek-V4-Flash-0731 | 64 | 44 | 43.56 | 20.53 | 2.12x |
| DeepSeek-V4-Flash-0731 | 256 | 44 | 43.88 | 22.00 | 1.99x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 10.77 | 6.96 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 19.11 | 9.76 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 30.77 | 13.20 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 42.95 | 17.03 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 51.18 | 20.71 | 2.47x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 54.47 | 23.58 | 2.31x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 55.44 | 25.44 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 112 | 11.30 | 8.26 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 112 | 21.01 | 11.62 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 112 | 36.68 | 16.79 | 2.18x |
| DeepSeek-V4-Flash-0731 | 16 | 112 | 57.76 | 22.59 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 112 | 78.97 | 28.66 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 112 | 93.35 | 33.67 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 112 | 100.67 | 37.08 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 168 | 11.48 | 9.01 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 168 | 21.70 | 12.77 | 1.70x |
| DeepSeek-V4-Flash-0731 | 8 | 168 | 39.00 | 18.86 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 168 | 64.32 | 25.90 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 168 | 93.48 | 33.74 | 2.77x |
| DeepSeek-V4-Flash-0731 | 64 | 168 | 117.06 | 40.37 | 2.90x |
| DeepSeek-V4-Flash-0731 | 256 | 168 | 131.43 | 44.95 | 2.92x |
| DeepSeek-V4-Flash-0731 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 224 | 11.58 | 9.50 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 224 | 22.06 | 13.68 | 1.61x |
| DeepSeek-V4-Flash-0731 | 8 | 224 | 40.23 | 20.13 | 2.00x |
| DeepSeek-V4-Flash-0731 | 16 | 224 | 67.98 | 28.43 | 2.39x |
| DeepSeek-V4-Flash-0731 | 32 | 224 | 102.19 | 37.57 | 2.72x |
| DeepSeek-V4-Flash-0731 | 64 | 224 | 132.41 | 45.34 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 224 | 152.56 | 50.95 | 2.99x |
| DeepSeek-V4-Flash-0731 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 336 | 11.67 | 10.11 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 336 | 22.42 | 15.09 | 1.49x |
| DeepSeek-V4-Flash-0731 | 8 | 336 | 41.51 | 21.75 | 1.91x |
| DeepSeek-V4-Flash-0731 | 16 | 336 | 71.94 | 32.26 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 336 | 112.08 | 42.70 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 336 | 150.82 | 52.80 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 336 | 179.07 | 59.69 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 448 | 11.72 | 10.47 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 448 | 22.61 | 16.14 | 1.40x |
| DeepSeek-V4-Flash-0731 | 8 | 448 | 42.17 | 22.95 | 1.84x |
| DeepSeek-V4-Flash-0731 | 16 | 448 | 74.04 | 34.77 | 2.13x |
| DeepSeek-V4-Flash-0731 | 32 | 448 | 117.52 | 46.50 | 2.53x |
| DeepSeek-V4-Flash-0731 | 64 | 448 | 161.39 | 58.19 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 448 | 194.83 | 66.34 | 2.94x |
| DeepSeek-V4-Flash-0731 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 672 | 11.76 | 10.87 | 1.08x |
| DeepSeek-V4-Flash-0731 | 4 | 672 | 22.79 | 17.60 | 1.29x |
| DeepSeek-V4-Flash-0731 | 8 | 672 | 42.85 | 24.95 | 1.72x |
| DeepSeek-V4-Flash-0731 | 16 | 672 | 76.22 | 37.57 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 672 | 123.33 | 52.69 | 2.34x |
| DeepSeek-V4-Flash-0731 | 64 | 672 | 173.01 | 65.13 | 2.66x |
| DeepSeek-V4-Flash-0731 | 256 | 672 | 212.61 | 75.82 | 2.80x |
| DeepSeek-V4-Pro-0813 | 1 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 2 | 48 | 10.64 | 6.69 | 1.59x |
| DeepSeek-V4-Pro-0813 | 4 | 48 | 18.70 | 9.37 | 2.00x |
| DeepSeek-V4-Pro-0813 | 8 | 48 | 29.57 | 12.59 | 2.35x |
| DeepSeek-V4-Pro-0813 | 16 | 48 | 40.07 | 16.21 | 2.47x |
| DeepSeek-V4-Pro-0813 | 32 | 48 | 46.04 | 19.82 | 2.32x |
| DeepSeek-V4-Pro-0813 | 64 | 48 | 47.72 | 22.90 | 2.08x |
| DeepSeek-V4-Pro-0813 | 256 | 48 | 47.98 | 25.74 | 1.86x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4-Pro-0813 | 1 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 93 | 11.23 | 7.92 | 1.42x |
| DeepSeek-V4-Pro-0813 | 4 | 93 | 20.82 | 11.20 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 93 | 36.11 | 16.00 | 2.26x |
| DeepSeek-V4-Pro-0813 | 16 | 93 | 56.11 | 21.60 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 93 | 75.02 | 27.64 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 93 | 86.34 | 33.16 | 2.60x |
| DeepSeek-V4-Pro-0813 | 256 | 93 | 91.42 | 38.56 | 2.37x |
| DeepSeek-V4-Pro-0813 | 1 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 94 | 11.24 | 7.94 | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | 94 | 20.85 | 11.23 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 94 | 36.19 | 16.05 | 2.25x |
| DeepSeek-V4-Pro-0813 | 16 | 94 | 56.34 | 21.70 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 94 | 75.50 | 27.77 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 94 | 87.07 | 33.34 | 2.61x |
| DeepSeek-V4-Pro-0813 | 256 | 94 | 92.34 | 38.79 | 2.38x |
| DeepSeek-V4-Pro-0813 | 1 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 95 | 11.25 | 7.96 | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | 95 | 20.87 | 11.25 | 1.85x |
| DeepSeek-V4-Pro-0813 | 8 | 95 | 36.28 | 16.11 | 2.25x |
| DeepSeek-V4-Pro-0813 | 16 | 95 | 56.57 | 21.79 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 95 | 75.98 | 27.91 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 95 | 87.80 | 33.52 | 2.62x |
| DeepSeek-V4-Pro-0813 | 256 | 95 | 93.25 | 39.02 | 2.39x |
| DeepSeek-V4-Pro-0813 | 1 | 97 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 97 | 11.26 | 8.00 | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | 97 | 20.92 | 11.31 | 1.85x |
| DeepSeek-V4-Pro-0813 | 8 | 97 | 36.44 | 16.23 | 2.25x |
| DeepSeek-V4-Pro-0813 | 16 | 97 | 57.02 | 21.97 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 97 | 76.93 | 28.18 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 97 | 89.25 | 33.88 | 2.63x |
| DeepSeek-V4-Pro-0813 | 256 | 97 | 95.05 | 39.49 | 2.41x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 139 | 11.45 | 8.69 | 1.32x |
| DeepSeek-V4-Pro-0813 | 4 | 139 | 21.64 | 12.29 | 1.76x |
| DeepSeek-V4-Pro-0813 | 8 | 139 | 38.89 | 18.19 | 2.14x |
| DeepSeek-V4-Pro-0813 | 16 | 139 | 64.04 | 25.07 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 139 | 92.62 | 32.95 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 139 | 115.10 | 40.42 | 2.85x |
| DeepSeek-V4-Pro-0813 | 256 | 139 | 129.87 | 47.97 | 2.71x |
| DeepSeek-V4-Pro-0813 | 1 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 145 | 11.47 | 8.77 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 145 | 21.72 | 12.41 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 145 | 39.14 | 18.42 | 2.13x |
| DeepSeek-V4-Pro-0813 | 16 | 145 | 64.78 | 25.43 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 145 | 94.36 | 33.52 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 145 | 118.18 | 41.22 | 2.87x |
| DeepSeek-V4-Pro-0813 | 256 | 145 | 134.34 | 49.03 | 2.74x |
| DeepSeek-V4-Pro-0813 | 1 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 154 | 11.49 | 8.88 | 1.29x |
| DeepSeek-V4-Pro-0813 | 4 | 154 | 21.81 | 12.59 | 1.73x |
| DeepSeek-V4-Pro-0813 | 8 | 154 | 39.47 | 18.73 | 2.11x |
| DeepSeek-V4-Pro-0813 | 16 | 154 | 65.79 | 25.94 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 154 | 96.79 | 34.34 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 154 | 122.55 | 42.37 | 2.89x |
| DeepSeek-V4-Pro-0813 | 256 | 154 | 140.81 | 50.56 | 2.79x |
| DeepSeek-V4-Pro-0813 | 1 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 156 | 11.50 | 8.90 | 1.29x |
| DeepSeek-V4-Pro-0813 | 4 | 156 | 21.83 | 12.63 | 1.73x |
| DeepSeek-V4-Pro-0813 | 8 | 156 | 39.54 | 18.79 | 2.10x |
| DeepSeek-V4-Pro-0813 | 16 | 156 | 66.00 | 26.05 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 156 | 97.31 | 34.51 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 156 | 123.48 | 42.62 | 2.90x |
| DeepSeek-V4-Pro-0813 | 256 | 156 | 142.21 | 50.89 | 2.79x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 280 | 11.68 | 9.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 280 | 22.53 | 14.53 | 1.55x |
| DeepSeek-V4-Pro-0813 | 8 | 280 | 42.03 | 21.42 | 1.96x |
| DeepSeek-V4-Pro-0813 | 16 | 280 | 73.81 | 31.44 | 2.35x |
| DeepSeek-V4-Pro-0813 | 32 | 280 | 117.46 | 42.98 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 280 | 162.98 | 54.48 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 280 | 207.38 | 66.94 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 336 | 11.71 | 10.14 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 336 | 22.68 | 15.18 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 336 | 42.57 | 22.15 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 336 | 75.61 | 33.27 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 336 | 122.42 | 45.52 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 336 | 173.56 | 58.30 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 336 | 226.83 | 72.31 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 356 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 356 | 11.73 | 10.21 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 356 | 22.72 | 15.39 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 356 | 42.73 | 22.38 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 356 | 76.13 | 33.85 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 356 | 123.86 | 46.31 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 356 | 176.71 | 59.56 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 356 | 232.79 | 74.07 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 358 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 358 | 11.73 | 10.22 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 358 | 22.72 | 15.41 | 1.47x |
| DeepSeek-V4-Pro-0813 | 8 | 358 | 42.74 | 22.40 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 358 | 76.17 | 33.90 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 358 | 124.00 | 46.38 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 358 | 177.01 | 59.68 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 358 | 233.36 | 74.24 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 448 | 11.76 | 10.50 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 448 | 22.87 | 16.25 | 1.41x |
| DeepSeek-V4-Pro-0813 | 8 | 448 | 43.27 | 23.34 | 1.85x |
| DeepSeek-V4-Pro-0813 | 16 | 448 | 77.94 | 36.03 | 2.16x |
| DeepSeek-V4-Pro-0813 | 32 | 448 | 129.03 | 49.47 | 2.61x |
| DeepSeek-V4-Pro-0813 | 64 | 448 | 188.21 | 64.80 | 2.90x |
| DeepSeek-V4-Pro-0813 | 256 | 448 | 255.15 | 81.21 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 672 | 11.81 | 10.91 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 672 | 23.06 | 17.73 | 1.30x |
| DeepSeek-V4-Pro-0813 | 8 | 672 | 43.98 | 25.33 | 1.74x |
| DeepSeek-V4-Pro-0813 | 16 | 672 | 80.37 | 39.17 | 2.05x |
| DeepSeek-V4-Pro-0813 | 32 | 672 | 136.13 | 55.89 | 2.44x |
| DeepSeek-V4-Pro-0813 | 64 | 672 | 204.63 | 73.69 | 2.78x |
| DeepSeek-V4-Pro-0813 | 256 | 672 | 288.80 | 93.78 | 3.08x |
| DeepSeek-V4-Pro-0813 | 1 | 1063 | 5.99 | 5.93 | 1.01x |
| DeepSeek-V4-Pro-0813 | 2 | 1063 | 11.85 | 11.24 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 1063 | 23.20 | 19.24 | 1.21x |
| DeepSeek-V4-Pro-0813 | 8 | 1063 | 44.52 | 28.12 | 1.58x |
| DeepSeek-V4-Pro-0813 | 16 | 1063 | 82.22 | 41.87 | 1.96x |
| DeepSeek-V4-Pro-0813 | 32 | 1063 | 141.70 | 63.78 | 2.22x |
| DeepSeek-V4-Pro-0813 | 64 | 1063 | 217.99 | 83.17 | 2.62x |
| DeepSeek-V4-Pro-0813 | 256 | 1063 | 317.65 | 109.56 | 2.90x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 2.0% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 0.9% |
| gpu | Qwen3-8B | 1 | 5.85 | 6.6% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 55.4% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 38.7% |
| rom | Qwen3-8B | 1 | 5.85 | 34.7% |

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
| Qwen3-8B | 1 | 4 | 40.53% | 3.76 | 9.27 |
| Qwen3-8B | 2 | 4 | 81.06% | 7.52 | 9.27 |
| Qwen3-8B | 4 | 1 | 4.54% | 0.42 | 9.27 |
| Qwen3-8B | 8 | 1 | 9.08% | 0.84 | 9.27 |
| Qwen3-8B | 16 | 1 | 18.16% | 1.68 | 9.27 |
| Qwen3-8B | 32 | 1 | 36.32% | 3.37 | 9.27 |
| Qwen3-8B | 64 | 1 | 72.65% | 6.74 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 26 | 96.88% | 2.06 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 1 | 4.48% | 0.10 | 2.13 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 8.96% | 0.19 | 2.13 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 17.92% | 0.38 | 2.13 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 35.83% | 0.76 | 2.13 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 71.66% | 1.53 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 141 | 86.61% | 1.80 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 3 | 28.74% | 0.60 | 2.08 |
| DeepSeek-V4-Pro-0813 | 4 | 3 | 57.49% | 1.19 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 8,822.1 | 8,822.1 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 4,753.8 | 9,507.7 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 2,473.0 | 9,892.0 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,262.0 | 10,096.1 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 637.6 | 10,201.3 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 320.5 | 10,254.8 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 160.7 | 10,281.7 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 40.2 | 10,302.0 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 6,924.3 | 6,924.3 |
| DeepSeek-V4-Flash-0731 | 2 | 4.63% | 14.6 GB | 8.74% | 190.54 TB/s | 2,179.91 TB/s | 4,037.7 | 8,075.4 |
| DeepSeek-V4-Flash-0731 | 4 | 9.05% | 21.1 GB | 12.64% | 275.47 TB/s | 2,179.91 TB/s | 2,201.9 | 8,807.4 |
| DeepSeek-V4-Flash-0731 | 8 | 17.28% | 33.2 GB | 19.90% | 433.71 TB/s | 2,179.91 TB/s | 1,153.2 | 9,225.6 |
| DeepSeek-V4-Flash-0731 | 16 | 31.58% | 54.2 GB | 32.50% | 708.53 TB/s | 2,179.91 TB/s | 590.6 | 9,450.0 |
| DeepSeek-V4-Flash-0731 | 32 | 53.18% | 86.0 GB | 51.56% | 1,123.90 TB/s | 2,179.91 TB/s | 298.9 | 9,566.3 |
| DeepSeek-V4-Flash-0731 | 64 | 78.08% | 122.7 GB | 73.52% | 1,602.57 TB/s | 2,179.91 TB/s | 150.4 | 9,625.5 |
| DeepSeek-V4-Flash-0731 | 256 | 99.77% | 154.6 GB | 92.64% | 2,019.50 TB/s | 2,179.91 TB/s | 37.8 | 9,670.4 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 4,087.1 | 4,087.1 |
| DeepSeek-V4-Pro-0813 | 2 | 3.10% | 52.3 GB | 5.86% | 683.32 TB/s | 11,661.57 TB/s | 2,742.7 | 5,485.4 |
| DeepSeek-V4-Pro-0813 | 4 | 6.11% | 77.0 GB | 8.63% | 1,005.95 TB/s | 11,661.57 TB/s | 1,654.4 | 6,617.5 |
| DeepSeek-V4-Pro-0813 | 8 | 11.84% | 124.1 GB | 13.90% | 1,621.51 TB/s | 11,661.57 TB/s | 922.4 | 7,379.0 |
| DeepSeek-V4-Pro-0813 | 16 | 22.27% | 209.9 GB | 23.51% | 2,742.18 TB/s | 11,661.57 TB/s | 489.3 | 7,829.4 |
| DeepSeek-V4-Pro-0813 | 32 | 39.59% | 352.2 GB | 39.46% | 4,601.25 TB/s | 11,661.57 TB/s | 252.4 | 8,075.9 |
| DeepSeek-V4-Pro-0813 | 64 | 63.50% | 548.8 GB | 61.48% | 7,169.39 TB/s | 11,661.57 TB/s | 128.2 | 8,205.0 |
| DeepSeek-V4-Pro-0813 | 256 | 98.23% | 834.3 GB | 93.45% | 10,898.18 TB/s | 11,661.57 TB/s | 32.4 | 8,304.6 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 4 |
| gpu | kv_read | 99 |
| gpu | link_latency | 438 |
| gpu | weight_read | 707 |
| rom | compute | 104 |
| rom | infeasible | 2275 |
| rom | kv_read | 1244 |
| rom | layer_fixed_latency | 17 |
| rom | link_latency | 1434 |
| rom | weight_read | 430 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 4 |
| rom | CAPACITY | 2275 |

## Mechanical consistency audit

**PASS** over 96,723 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 1 |
| published | 68 |
| derived | 29 |
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
- **A pipeline's service time is charged on the machine's aggregate
  resources, which is the steady-state throughput view, while its hops are
  charged on the single-token latency view.** A balanced S-stage
  pipeline's per-user latency is S times what is reported. The bias runs
  the same way on both families and grows with device count, and it is why
  the topology sweep above ranks pipeline first at every size. Whether it
  cancels in the iso-area ratio is not established.
- Prefill, speculative decoding and cost are out of scope for this model.

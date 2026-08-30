# Area-constrained roofline: n6_vs_a100

> Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 76.6 us, or 13,063 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **The ROM advantage is a batch-1, per-user advantage, and it is large.** At equal area the best batch-1 point is Qwen3-8B on 1,630 mm2 of ROM silicon at 10,821 tok/s per user, against 1,652 mm2 of a100_sxm_80gb-x2 at 191 tok/s: **57x**. Both sides bind on `weight_read`, and the whole difference is that one reads its weights from HBM and the other from an on-die array.
3. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.19x (Qwen3-8B, ROM binding on `kv_read`) to 6.64x (DeepSeek-V4-Pro-0813, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
4. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 92.6% at batch 256, while the weight-read time is identical at both. Aggregate throughput rises from 8,204 to 16,982 tok/s on the same machine. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
5. **Tensor parallelism is a latency argument for wafer-scale, and it is the sharpest one.** Two all-reduces per layer per token cost up to 189 us over NVLink, capping per-user decode at 5,296 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 12.2 us and cap it at 81,966 tok/s.
6. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 24 of 24 operating points and an array 0; on tokens per second per square millimetre the same points go 11 to the array and 13 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
7. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 490 of 1250 feasible points.
8. **The largest open question is not in this model's inputs but in the architecture, and the anchor cannot settle it.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 8.8x of aggregate throughput (DeepSeek-V4-Flash-0731). The machines are identical at batch 1, which is where the published anchor sits, so no amount of validation against it resolves the fork.
9. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 15.20x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 2.30x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 11 of 48 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
10. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.

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
| DeepSeek-V4-Flash-0731 | 200,000 | 284 B | 166.9 GB | 4.70 | 0.099 GB | 0.705 GB | 113.2 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1,600 B | 892.7 GB | 4.46 | 0.674 GB | 5.028 GB | 58.9 |

## Iso-area comparison

Two ROM designs per operating point -- the **fastest** and the
**smallest silicon that serves the point at all** -- each against the GPU
cluster of the closest equal silicon area. **The area is stated on both
sides.** Where one row appears, the two coincide.

| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | GPU user tok/s | GPU aggregate tok/s | GPU binds on | Per-user ratio | Aggregate ratio |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---:|
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-romfill | 46,225 | 48,259.1 | 48,259.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x56 | 46,256 | 1.00x | 3,623.6 | 3,623.6 | weight_read | 13.32x | 13.32x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-fp8-SRAMKV-array-pipeline-x2 | 1,630 | 10,820.8 | 10,820.8 | weight_read | Qwen3-8B/a100_sxm_80gb-x2 | 1,652 | 0.99x | 190.6 | 190.6 | weight_read | 56.77x | 56.77x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 17,218.7 | 34,437.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x224 | 185,024 | 1.00x | 2,533.9 | 5,067.9 | link_latency | 6.80x | 6.80x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 5,260.2 | 10,520.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 788.4 | 1,576.9 | weight_read | 6.67x | 6.67x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 9,698.7 | 38,794.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x224 | 185,024 | 1.00x | 2,465.4 | 9,861.5 | link_latency | 3.93x | 3.93x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 2,759.7 | 11,038.6 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 694.2 | 2,776.6 | weight_read | 3.98x | 3.98x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 5,176.9 | 41,415.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x224 | 185,024 | 1.00x | 2,338.8 | 18,710.5 | link_latency | 2.21x | 2.21x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 1,414.7 | 11,317.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 560.2 | 4,481.5 | weight_read | 2.53x | 2.53x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 2,678.9 | 42,862.7 | kv_read | Qwen3-8B/a100_sxm_80gb-x224 | 185,024 | 1.00x | 2,121.0 | 33,936.6 | link_latency | 1.26x | 1.26x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 716.4 | 11,462.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 404.2 | 6,466.9 | kv_read | 1.77x | 1.77x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 1,363.3 | 43,625.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x224 | 185,024 | 1.00x | 1,788.1 | 57,217.8 | link_latency | 0.76x | 0.76x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 360.5 | 11,535.7 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 259.6 | 8,306.9 | kv_read | 1.39x | 1.39x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 687.8 | 44,016.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x224 | 185,024 | 1.00x | 1,360.8 | 87,090.9 | link_latency | 0.51x | 0.51x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 180.8 | 11,573.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 151.3 | 9,684.7 | kv_read | 1.19x | 1.19x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 173.1 | 44,314.8 | kv_read | Qwen3-8B/a100_sxm_80gb-x224 | 185,024 | 1.00x | 559.1 | 143,140.7 | link_latency | 0.31x | 0.31x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 45.3 | 11,601.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 43.2 | 11,060.6 | kv_read | 1.05x | 1.05x |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x4-romfill | 184,900 | 34,417.7 | 34,417.7 | weight_read | DSV4-Flash/a100_sxm_80gb-x224 | 185,024 | 1.00x | 1,315.4 | 1,315.4 | weight_read | 26.16x | 26.16x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x18 | 14,670 | 8,306.7 | 8,306.7 | weight_read | DSV4-Flash/a100_sxm_80gb-x18 | 14,868 | 0.99x | 1,116.0 | 1,116.0 | weight_read | 7.44x | 7.44x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 34,291.5 | 68,582.9 | weight_read | DSV4-Flash/a100_sxm_80gb-x224 | 185,024 | 1.00x | 1,203.2 | 2,406.4 | weight_read | 28.50x | 28.50x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 6,487.0 | 12,974.0 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 861.1 | 1,722.2 | weight_read | 7.53x | 7.53x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 34,291.3 | 137,165.1 | weight_read | DSV4-Flash/a100_sxm_80gb-x224 | 185,024 | 1.00x | 999.7 | 3,998.6 | weight_read | 34.30x | 34.30x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 3,681.4 | 14,725.5 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 622.4 | 2,489.7 | weight_read | 5.91x | 5.91x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 26,684.2 | 213,473.6 | kv_read | DSV4-Flash/a100_sxm_80gb-x224 | 185,024 | 1.00x | 836.5 | 6,692.2 | weight_read | 31.90x | 31.90x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 1,973.9 | 15,791.4 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 430.9 | 3,447.5 | weight_read | 4.58x | 4.58x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 17,643.2 | 282,291.3 | kv_read | DSV4-Flash/a100_sxm_80gb-x224 | 185,024 | 1.00x | 688.3 | 11,013.5 | weight_read | 25.63x | 25.63x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 1,024.0 | 16,384.5 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 291.7 | 4,667.4 | weight_read | 3.51x | 3.51x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 10,516.8 | 336,536.0 | kv_read | DSV4-Flash/a100_sxm_80gb-x224 | 185,024 | 1.00x | 562.2 | 17,991.4 | weight_read | 18.71x | 18.71x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 521.8 | 16,698.0 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 200.6 | 6,420.5 | weight_read | 2.60x | 2.60x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 5,817.3 | 372,307.0 | kv_read | DSV4-Flash/a100_sxm_80gb-x224 | 185,024 | 1.00x | 466.2 | 29,838.1 | weight_read | 12.48x | 12.48x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 263.4 | 16,859.3 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 148.3 | 9,491.9 | weight_read | 1.78x | 1.78x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 1,580.3 | 404,557.9 | kv_read | DSV4-Flash/a100_sxm_80gb-x224 | 185,024 | 1.00x | 353.6 | 90,520.6 | weight_read | 4.47x | 4.47x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 66.3 | 16,982.3 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 111.5 | 28,549.8 | weight_read | 0.59x | 0.59x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 22,042.9 | 22,042.9 | weight_read | DSV4-Pro/a100_sxm_80gb-x672 | 555,072 | 1.00x | 407.1 | 407.1 | weight_read | 54.15x | 54.15x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x93 | 75,795 | 4,116.4 | 4,116.4 | link_latency | DSV4-Pro/a100_sxm_80gb-x92 | 75,992 | 1.00x | 521.3 | 521.3 | weight_read | 7.90x | 7.90x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 22,042.8 | 44,085.6 | weight_read | DSV4-Pro/a100_sxm_80gb-x672 | 555,072 | 1.00x | 389.5 | 779.0 | weight_read | 56.59x | 56.59x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 2,957.6 | 5,915.3 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 418.2 | 836.4 | weight_read | 7.07x | 7.07x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 20,865.6 | 83,462.3 | kv_read | DSV4-Pro/a100_sxm_80gb-x672 | 555,072 | 1.00x | 344.0 | 1,376.0 | weight_read | 60.66x | 60.66x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 1,934.4 | 7,737.4 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 311.6 | 1,246.4 | weight_read | 6.21x | 6.21x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 14,305.2 | 114,441.6 | kv_read | DSV4-Pro/a100_sxm_80gb-x672 | 555,072 | 1.00x | 277.7 | 2,221.8 | weight_read | 51.51x | 51.51x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 1,143.3 | 9,146.1 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 235.9 | 1,887.3 | weight_read | 4.85x | 4.85x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 8,782.5 | 140,520.8 | kv_read | DSV4-Pro/a100_sxm_80gb-x672 | 555,072 | 1.00x | 236.6 | 3,785.2 | weight_read | 37.12x | 37.12x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 628.9 | 10,062.0 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 172.5 | 2,760.3 | weight_read | 3.65x | 3.65x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4,956.0 | 158,590.7 | kv_read | DSV4-Pro/a100_sxm_80gb-x672 | 555,072 | 1.00x | 194.3 | 6,216.5 | weight_read | 25.51x | 25.51x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 331.0 | 10,592.4 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 125.4 | 4,012.4 | weight_read | 2.64x | 2.64x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 2,648.3 | 169,488.2 | kv_read | DSV4-Pro/a100_sxm_80gb-x672 | 555,072 | 1.00x | 158.1 | 10,117.9 | weight_read | 16.75x | 16.75x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 170.0 | 10,879.2 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 93.6 | 5,990.6 | weight_read | 1.82x | 1.82x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 698.0 | 178,697.5 | kv_read | DSV4-Pro/a100_sxm_80gb-x672 | 555,072 | 1.00x | 105.1 | 26,896.2 | weight_read | 6.64x | 6.64x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 43.4 | 11,104.6 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 65.2 | 16,696.3 | weight_read | 0.67x | 0.67x |

## Array or wafer: the crossover, reported rather than assumed

`Array viable to` is the per-user rate at which the topology's hops alone
consume 10% of the token budget; `hard ceiling` is the rate at which they
consume all of it. Below the first number the interconnect is a design
cost; above the second the topology cannot deliver the rate at all.

| Design | Model | Devices | Parallelism | Link | Hops/token | Link latency/token | Viable to (10% budget) | Hard ceiling |
|---|---|---:|---|---|---:|---:|---:|---:|
| Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x4 | Qwen3-8B | 4 | pipeline | nvlink | 3 | 4.53 us | 22,088.2 tok/s | 220,881.9 tok/s |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x4 | Qwen3-8B | 4 | tensor | nvlink | 72 | 109.97 us | 909.4 tok/s | 9,093.7 tok/s |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | 72 | 7.20 us | 13,888.8 tok/s | 138,887.6 tok/s |
| Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | Qwen3-8B | 9 | pipeline | nvlink | 8 | 12.07 us | 8,283.1 tok/s | 82,830.7 tok/s |
| Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x9 | Qwen3-8B | 9 | tensor | nvlink | 72 | 109.97 us | 909.4 tok/s | 9,093.7 tok/s |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | 72 | 7.20 us | 13,888.8 tok/s | 138,887.6 tok/s |
| Qwen3-8B/ROM-N6-fp8-SRAMKV-array-pipeline-x2 | Qwen3-8B | 2 | pipeline | nvlink | 1 | 1.51 us | 66,264.6 tok/s | 662,645.6 tok/s |
| Qwen3-8B/ROM-N6-fp8-SRAMKV-array-tensor-x2 | Qwen3-8B | 2 | tensor | nvlink | 72 | 109.97 us | 909.4 tok/s | 9,093.7 tok/s |
| Qwen3-8B/ROM-N6-fp8-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| Qwen3-8B/ROM-N6-fp8-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | 72 | 7.20 us | 13,888.8 tok/s | 138,887.6 tok/s |
| Qwen3-8B/ROM-N6-fp8-HBMKV-array-pipeline-x9 | Qwen3-8B | 9 | pipeline | nvlink | 8 | 12.07 us | 8,283.1 tok/s | 82,830.7 tok/s |
| Qwen3-8B/ROM-N6-fp8-HBMKV-array-tensor-x9 | Qwen3-8B | 9 | tensor | nvlink | 72 | 109.97 us | 909.4 tok/s | 9,093.7 tok/s |
| Qwen3-8B/ROM-N6-fp8-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| Qwen3-8B/ROM-N6-fp8-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | 72 | 7.20 us | 13,888.8 tok/s | 138,887.6 tok/s |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x18 | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink | 17 | 25.65 us | 3,897.9 tok/s | 38,979.2 tok/s |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x18 | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink | 86 | 131.35 us | 761.3 tok/s | 7,613.3 tok/s |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | 86 | 8.60 us | 11,627.8 tok/s | 116,278.0 tok/s |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink | 18 | 27.16 us | 3,681.4 tok/s | 36,813.6 tok/s |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x19 | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink | 86 | 131.35 us | 761.3 tok/s | 7,613.3 tok/s |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | 86 | 8.60 us | 11,627.8 tok/s | 116,278.0 tok/s |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x93 | DeepSeek-V4-Pro-0813 | 93 | pipeline | nvlink | 92 | 139.47 us | 717.0 tok/s | 7,170.2 tok/s |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x93 | DeepSeek-V4-Pro-0813 | 93 | tensor | nvlink | 122 | 188.83 us | 529.6 tok/s | 5,295.8 tok/s |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4-Pro-0813 | 2 | pipeline | on_wafer | 113 | 11.30 us | 8,849.5 tok/s | 88,495.1 tok/s |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4-Pro-0813 | 2 | tensor | on_wafer | 122 | 12.20 us | 8,196.6 tok/s | 81,965.9 tok/s |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | DeepSeek-V4-Pro-0813 | 98 | pipeline | nvlink | 97 | 147.05 us | 680.1 tok/s | 6,800.6 tok/s |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x98 | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink | 122 | 188.83 us | 529.6 tok/s | 5,295.8 tok/s |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3 | DeepSeek-V4-Pro-0813 | 3 | pipeline | on_wafer | 170 | 17.00 us | 5,882.3 tok/s | 58,823.2 tok/s |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer | 122 | 12.20 us | 8,196.6 tok/s | 81,965.9 tok/s |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-romfill | 46,225 | 48,259.1 | 1.044 | 30,662.7 (6,520) | 48,259.1 (46,225) | 1.57x | kv_read |
| Qwen3-8B | 2 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 17,218.7 | 0.093 | 8,495.2 (14,670) | 17,218.7 (184,900) | 2.03x | kv_read |
| Qwen3-8B | 4 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 9,698.7 | 0.052 | 4,900.1 (14,670) | 9,698.7 (184,900) | 1.98x | kv_read |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 5,176.9 | 0.028 | 2,653.8 (14,670) | 5,176.9 (184,900) | 1.95x | kv_read |
| Qwen3-8B | 16 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 2,678.9 | 0.014 | 1,384.5 (14,670) | 2,678.9 (184,900) | 1.93x | kv_read |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 1,363.3 | 0.007 | 707.6 (14,670) | 1,363.3 (184,900) | 1.93x | kv_read |
| Qwen3-8B | 64 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 687.8 | 0.004 | 357.8 (14,670) | 687.8 (184,900) | 1.92x | kv_read |
| Qwen3-8B | 256 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 173.1 | 0.001 | 90.2 (14,670) | 173.1 (184,900) | 1.92x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x4-romfill | 184,900 | 34,417.7 | 0.186 | 8,306.7 (14,670) | 34,417.7 (184,900) | 4.14x | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 34,291.5 | 0.185 | 6,487.0 (15,485) | 34,291.5 (184,900) | 5.29x | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 34,291.3 | 0.185 | 3,681.4 (15,485) | 34,291.3 (184,900) | 9.31x | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 26,684.2 | 0.144 | 1,973.9 (15,485) | 26,684.2 (184,900) | 13.52x | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 17,643.2 | 0.095 | 1,024.0 (15,485) | 17,643.2 (184,900) | 17.23x | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 10,516.8 | 0.057 | 521.8 (15,485) | 10,516.8 (184,900) | 20.15x | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 5,817.3 | 0.031 | 263.4 (15,485) | 5,817.3 (184,900) | 22.08x | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 1,580.3 | 0.009 | 66.3 (15,485) | 1,580.3 (184,900) | 23.82x | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 22,042.9 | 0.040 | 4,116.4 (75,795) | 22,042.9 (554,700) | 5.35x | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 22,042.8 | 0.040 | 2,957.6 (79,870) | 22,042.8 (554,700) | 7.45x | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 20,865.6 | 0.038 | 1,934.4 (79,870) | 20,865.6 (554,700) | 10.79x | kv_read |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 14,305.2 | 0.026 | 1,143.3 (79,870) | 14,305.2 (554,700) | 12.51x | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 8,782.5 | 0.016 | 628.9 (79,870) | 8,782.5 (554,700) | 13.97x | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4,956.0 | 0.009 | 331.0 (79,870) | 4,956.0 (554,700) | 14.97x | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 2,648.3 | 0.005 | 170.0 (79,870) | 2,648.3 (554,700) | 15.58x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 698.0 | 0.001 | 43.4 (79,870) | 698.0 (554,700) | 16.09x | kv_read |

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
| Qwen3-8B | 1 | sram | 11,363.7 | 11,363.7 | 11,363.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 11,523.8 | 12,154.2 | 12,154.2 | 0.95x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 11,916.8 | 12,592.1 | 12,592.1 | 0.95x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 12,123.5 | 12,823.2 | 12,823.2 | 0.95x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 12,229.6 | 12,941.9 | 12,941.9 | 0.94x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 12,283.3 | 13,002.1 | 13,002.1 | 0.94x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 12,310.4 | 13,032.4 | 13,032.4 | 0.94x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 12,330.8 | 12,330.8 | 12,330.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1 | rom | 48,259.1 | 48,259.1 | 48,259.1 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 34,437.3 | 34,437.3 | 34,437.3 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 38,794.9 | 38,794.9 | 38,794.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 41,415.2 | 41,415.2 | 41,415.2 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 42,862.7 | 42,862.7 | 42,862.7 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 43,625.1 | 43,625.1 | 43,625.1 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 44,016.5 | 44,016.5 | 44,016.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 44,314.8 | 44,314.8 | 44,314.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 10,890.3 | 10,890.3 | 10,890.3 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 21,780.6 | 11,878.1 | 19,633.0 | 1.83x | 1.65x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 43,561.3 | 12,442.3 | 29,495.0 | 3.50x | 2.37x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 87,122.5 | 12,745.0 | 44,793.0 | 6.84x | 3.51x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 104,211.5 | 12,902.0 | 67,796.2 | 8.08x | 5.25x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 109,665.6 | 12,981.9 | 98,924.5 | 8.45x | 7.62x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 112,612.5 | 13,022.3 | 138,630.5 | 8.65x | 10.65x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 114,928.7 | 13,052.7 | 198,349.4 | 8.80x | 15.20x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 34,417.7 | 36,020.2 | 36,020.2 | 0.96x | 1.00x | weight_read | layer_fixed_latency | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | rom | 68,582.9 | 53,410.8 | 68,689.2 | 1.28x | 1.29x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 137,165.1 | 70,646.9 | 119,965.3 | 1.94x | 1.70x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 213,473.6 | 84,239.3 | 206,578.5 | 2.53x | 2.45x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 282,291.3 | 93,205.7 | 282,291.3 | 3.03x | 3.03x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 336,536.0 | 98,444.9 | 336,536.0 | 3.42x | 3.42x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 372,307.0 | 101,291.8 | 372,307.0 | 3.68x | 3.68x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 404,557.9 | 103,537.3 | 404,557.9 | 3.91x | 3.91x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 9,082.2 | 9,008.5 | 9,008.5 | 1.01x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 18,017.0 | 10,200.7 | 16,860.8 | 1.77x | 1.65x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 35,130.9 | 10,923.5 | 27,110.4 | 3.22x | 2.48x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 39,648.6 | 11,324.7 | 40,950.0 | 3.50x | 3.62x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 42,373.1 | 11,536.6 | 42,373.1 | 3.67x | 3.67x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 43,880.8 | 11,645.5 | 52,991.5 | 3.77x | 4.55x | kv_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | sram | 44,675.6 | 11,700.8 | 79,976.4 | 3.82x | 6.84x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 45,290.8 | 11,742.6 | 141,001.0 | 3.86x | 12.01x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 22,042.9 | 23,305.9 | 23,305.9 | 0.95x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 44,085.6 | 33,256.9 | 44,870.6 | 1.33x | 1.35x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 83,462.3 | 42,404.8 | 79,386.1 | 1.97x | 1.87x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 114,441.6 | 49,167.0 | 114,441.6 | 2.33x | 2.33x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 140,520.8 | 53,427.0 | 140,520.8 | 2.63x | 2.63x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 158,590.7 | 55,846.3 | 158,590.7 | 2.84x | 2.84x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 169,488.2 | 57,140.0 | 169,488.2 | 2.97x | 2.97x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 178,697.5 | 58,150.4 | 178,697.5 | 3.07x | 3.07x | kv_read | weight_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 11,363.7 | 0.246 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-romfill | 46,225 | 19.91 | 1.00 | 48,259.1 | 1.044 | kv_read | 4.25x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 11,363.7 | 0.246 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.61 | 1.00 | 48,259.1 | 1.044 | kv_read | 4.25x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 11,363.7 | 0.246 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.61 | 1.00 | 48,259.1 | 1.044 | kv_read | 4.25x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 11,523.8 | 0.249 | kv_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 79.57 | 1.00 | 34,437.3 | 0.186 | kv_read | 2.99x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 2.00 | 12,154.2 | 0.263 | weight_read | 1.05x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 90.38 | 2.00 | 34,437.3 | 0.186 | kv_read | 2.99x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 2.00 | 12,154.2 | 0.263 | weight_read | 1.05x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 90.38 | 2.00 | 34,437.3 | 0.186 | kv_read | 2.99x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 11,916.8 | 0.258 | kv_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 79.57 | 1.00 | 38,794.9 | 0.210 | kv_read | 3.26x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.00 | 12,592.1 | 0.272 | weight_read | 1.06x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 90.38 | 4.00 | 38,794.9 | 0.210 | kv_read | 3.26x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.00 | 12,592.1 | 0.272 | weight_read | 1.06x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 90.38 | 4.00 | 38,794.9 | 0.210 | kv_read | 3.26x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,123.5 | 0.262 | kv_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 79.57 | 1.00 | 41,415.2 | 0.224 | kv_read | 3.42x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 8.00 | 12,823.2 | 0.277 | weight_read | 1.06x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 90.38 | 8.00 | 41,415.2 | 0.224 | kv_read | 3.42x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 8.00 | 12,823.2 | 0.277 | weight_read | 1.06x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 90.38 | 8.00 | 41,415.2 | 0.224 | kv_read | 3.42x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,229.6 | 0.265 | kv_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 79.57 | 1.00 | 42,862.7 | 0.232 | kv_read | 3.50x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 16.00 | 12,941.9 | 0.280 | weight_read | 1.06x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 90.38 | 16.00 | 42,862.7 | 0.232 | kv_read | 3.50x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 16.00 | 12,941.9 | 0.280 | weight_read | 1.06x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 90.38 | 16.00 | 42,862.7 | 0.232 | kv_read | 3.50x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,283.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 79.57 | 1.00 | 43,625.1 | 0.236 | kv_read | 3.55x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 32.00 | 13,002.1 | 0.281 | weight_read | 1.06x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 90.38 | 32.00 | 43,625.1 | 0.236 | kv_read | 3.55x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 32.00 | 13,002.1 | 0.281 | weight_read | 1.06x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 90.38 | 32.00 | 43,625.1 | 0.236 | kv_read | 3.55x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,310.4 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 79.57 | 1.00 | 44,016.5 | 0.238 | kv_read | 3.58x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 64.00 | 13,032.4 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 90.38 | 64.00 | 44,016.5 | 0.238 | kv_read | 3.58x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 64.00 | 13,032.4 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 90.38 | 64.00 | 44,016.5 | 0.238 | kv_read | 3.58x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,330.8 | 0.267 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 79.57 | 1.00 | 44,314.8 | 0.240 | kv_read | 3.59x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 256.00 | 12,330.8 | 0.267 | kv_read | 1.00x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 90.38 | 256.00 | 44,314.8 | 0.240 | kv_read | 3.59x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 256.00 | 12,330.8 | 0.267 | kv_read | 1.00x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 90.38 | 256.00 | 44,314.8 | 0.240 | kv_read | 3.59x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 10,890.3 | 0.236 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x4-romfill | 184,900 | 7.89 | 1.00 | 34,417.7 | 0.186 | weight_read | 3.16x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 10,890.3 | 0.236 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 8.96 | 1.00 | 36,020.2 | 0.195 | layer_fixed_latency | 3.31x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 10,890.3 | 0.236 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 8.96 | 1.00 | 36,020.2 | 0.195 | layer_fixed_latency | 3.31x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 21,780.6 | 0.471 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 7.81 | 1.00 | 68,582.9 | 0.371 | weight_read | 3.15x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 2.00 | 11,878.1 | 0.257 | weight_read | 0.55x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 8.87 | 2.00 | 53,410.8 | 0.289 | weight_read | 2.45x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.13 | 19,633.0 | 0.425 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 8.87 | 1.13 | 68,689.2 | 0.371 | weight_read | 3.15x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 43,561.3 | 0.942 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 7.81 | 1.00 | 137,165.1 | 0.742 | weight_read | 3.15x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.00 | 12,442.3 | 0.269 | weight_read | 0.29x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 8.87 | 4.00 | 70,646.9 | 0.382 | weight_read | 1.62x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.57 | 29,495.0 | 0.638 | weight_read | 0.68x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 8.87 | 1.57 | 119,965.3 | 0.649 | weight_read | 2.75x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 87,122.5 | 1.885 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 7.81 | 1.00 | 213,473.6 | 1.155 | kv_read | 2.45x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 8.00 | 12,745.0 | 0.276 | weight_read | 0.15x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 8.87 | 8.00 | 84,239.3 | 0.456 | weight_read | 0.97x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 2.13 | 44,793.0 | 0.969 | weight_read | 0.51x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 8.87 | 2.13 | 206,578.5 | 1.117 | weight_read | 2.37x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 104,211.5 | 2.254 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 7.81 | 1.00 | 282,291.3 | 1.527 | kv_read | 2.71x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 16.00 | 12,902.0 | 0.279 | weight_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 8.87 | 16.00 | 93,205.7 | 0.504 | weight_read | 0.89x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 2.88 | 67,796.2 | 1.467 | weight_read | 0.65x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 8.87 | 2.88 | 282,291.3 | 1.527 | kv_read | 2.71x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 109,665.6 | 2.372 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 7.81 | 1.00 | 336,536.0 | 1.820 | kv_read | 3.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 32.00 | 12,981.9 | 0.281 | weight_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 8.87 | 32.00 | 98,444.9 | 0.532 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.03 | 98,924.5 | 2.140 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 8.87 | 4.03 | 336,536.0 | 1.820 | kv_read | 3.07x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 112,612.5 | 2.436 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 7.81 | 1.00 | 372,307.0 | 2.014 | kv_read | 3.31x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 64.00 | 13,022.3 | 0.282 | weight_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 8.87 | 64.00 | 101,291.8 | 0.548 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 5.83 | 138,630.5 | 2.999 | weight_read | 1.23x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 8.87 | 5.83 | 372,307.0 | 2.014 | kv_read | 3.31x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 114,928.7 | 2.486 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 7.81 | 1.00 | 404,557.9 | 2.188 | kv_read | 3.52x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 256.00 | 13,052.7 | 0.282 | weight_read | 0.11x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 8.87 | 256.00 | 103,537.3 | 0.560 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x28-perregion | 22,820 | 1.00 | 13.84 | 198,349.4 | 8.692 | weight_read | 1.73x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 8.87 | 13.84 | 404,557.9 | 2.188 | kv_read | 3.52x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 9,082.2 | 0.098 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4.38 | 1.00 | 22,042.9 | 0.040 | weight_read | 2.43x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3-perstream | 138,675 | 1.00 | 1.00 | 9,008.5 | 0.065 | weight_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x12-perstream-romfill | 554,700 | 5.02 | 1.00 | 23,305.9 | 0.042 | weight_read | 2.57x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3-perregion | 138,675 | 1.00 | 1.00 | 9,008.5 | 0.065 | weight_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x12-perregion-romfill | 554,700 | 5.02 | 1.00 | 23,305.9 | 0.042 | weight_read | 2.57x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 1.00 | 1.00 | 18,017.0 | 0.130 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4.38 | 1.00 | 44,085.6 | 0.079 | weight_read | 2.45x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3-perstream | 138,675 | 1.00 | 2.00 | 10,200.7 | 0.074 | weight_read | 0.57x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perstream-romfill | 554,700 | 4.98 | 2.00 | 33,256.9 | 0.060 | weight_read | 1.85x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3-perregion | 138,675 | 1.00 | 1.09 | 16,860.8 | 0.122 | weight_read | 0.94x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perregion-romfill | 554,700 | 4.98 | 1.09 | 44,870.6 | 0.081 | weight_read | 2.49x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 1.00 | 1.00 | 35,130.9 | 0.253 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4.38 | 1.00 | 83,462.3 | 0.150 | kv_read | 2.38x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3-perstream | 138,675 | 1.00 | 4.00 | 10,923.5 | 0.079 | weight_read | 0.31x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perstream-romfill | 554,700 | 4.98 | 4.00 | 42,404.8 | 0.076 | weight_read | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3-perregion | 138,675 | 1.00 | 1.43 | 27,110.4 | 0.195 | weight_read | 0.77x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perregion-romfill | 554,700 | 4.98 | 1.43 | 79,386.1 | 0.143 | weight_read | 2.26x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 1.00 | 1.00 | 39,648.6 | 0.286 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4.38 | 1.00 | 114,441.6 | 0.206 | kv_read | 2.89x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3-perstream | 138,675 | 1.00 | 8.00 | 11,324.7 | 0.082 | weight_read | 0.29x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perstream-romfill | 554,700 | 4.98 | 8.00 | 49,167.0 | 0.089 | weight_read | 1.24x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3-perregion | 138,675 | 1.00 | 1.99 | 40,950.0 | 0.295 | weight_read | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perregion-romfill | 554,700 | 4.98 | 1.99 | 114,441.6 | 0.206 | kv_read | 2.89x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 1.00 | 1.00 | 42,373.1 | 0.306 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4.38 | 1.00 | 140,520.8 | 0.253 | kv_read | 3.32x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3-perstream | 138,675 | 1.00 | 16.00 | 11,536.6 | 0.083 | weight_read | 0.27x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perstream-romfill | 554,700 | 4.98 | 16.00 | 53,427.0 | 0.096 | weight_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3-perregion | 138,675 | 1.00 | 2.54 | 42,373.1 | 0.306 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perregion-romfill | 554,700 | 4.98 | 2.54 | 140,520.8 | 0.253 | kv_read | 3.32x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 1.00 | 1.00 | 43,880.8 | 0.316 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4.38 | 1.00 | 158,590.7 | 0.286 | kv_read | 3.61x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3-perstream | 138,675 | 1.00 | 32.00 | 11,645.5 | 0.084 | weight_read | 0.27x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perstream-romfill | 554,700 | 4.98 | 32.00 | 55,846.3 | 0.101 | weight_read | 1.27x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x147-perregion | 119,805 | 1.00 | 3.49 | 52,991.5 | 0.442 | link_latency | 1.21x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perregion-romfill | 554,700 | 4.98 | 3.49 | 158,590.7 | 0.286 | kv_read | 3.61x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 1.00 | 1.00 | 44,675.6 | 0.322 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4.38 | 1.00 | 169,488.2 | 0.306 | kv_read | 3.79x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3-perstream | 138,675 | 1.00 | 64.00 | 11,700.8 | 0.084 | weight_read | 0.26x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perstream-romfill | 554,700 | 4.98 | 64.00 | 57,140.0 | 0.103 | weight_read | 1.28x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x147-perregion | 119,805 | 1.00 | 4.92 | 79,976.4 | 0.668 | weight_read | 1.79x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perregion-romfill | 554,700 | 4.98 | 4.92 | 169,488.2 | 0.306 | kv_read | 3.79x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 1.00 | 1.00 | 45,290.8 | 0.327 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-romfill | 554,700 | 4.38 | 1.00 | 178,697.5 | 0.322 | kv_read | 3.95x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3-perstream | 138,675 | 1.00 | 256.00 | 11,742.6 | 0.085 | weight_read | 0.26x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perstream-romfill | 554,700 | 4.98 | 256.00 | 58,150.4 | 0.105 | weight_read | 1.28x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x147-perregion | 119,805 | 1.00 | 10.96 | 141,001.0 | 1.177 | kv_read | 3.11x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x12-perregion-romfill | 554,700 | 4.98 | 10.96 | 178,697.5 | 0.322 | kv_read | 3.95x |

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
| DeepSeek-V4-Flash-0731 | 1 | 5 | 3.69 | 2.53 | 1.46x |
| DeepSeek-V4-Flash-0731 | 2 | 5 | 4.65 | 2.95 | 1.57x |
| DeepSeek-V4-Flash-0731 | 4 | 5 | 4.97 | 3.34 | 1.49x |
| DeepSeek-V4-Flash-0731 | 8 | 5 | 5.00 | 3.69 | 1.36x |
| DeepSeek-V4-Flash-0731 | 16 | 5 | 5.00 | 3.96 | 1.26x |
| DeepSeek-V4-Flash-0731 | 32 | 5 | 5.00 | 4.16 | 1.20x |
| DeepSeek-V4-Flash-0731 | 64 | 5 | 5.00 | 4.29 | 1.17x |
| DeepSeek-V4-Flash-0731 | 256 | 5 | 5.00 | 4.36 | 1.15x |
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
| DeepSeek-V4-Flash-0731 | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 32 | 10.04 | 5.99 | 1.68x |
| DeepSeek-V4-Flash-0731 | 4 | 32 | 16.66 | 8.12 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 32 | 24.15 | 10.52 | 2.30x |
| DeepSeek-V4-Flash-0731 | 16 | 32 | 29.54 | 13.00 | 2.27x |
| DeepSeek-V4-Flash-0731 | 32 | 32 | 31.58 | 15.25 | 2.07x |
| DeepSeek-V4-Flash-0731 | 64 | 32 | 31.94 | 16.91 | 1.89x |
| DeepSeek-V4-Flash-0731 | 256 | 32 | 31.99 | 17.95 | 1.78x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 10.77 | 6.96 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 19.11 | 9.76 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 30.77 | 13.20 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 42.95 | 17.03 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 51.18 | 20.71 | 2.47x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 54.47 | 23.58 | 2.31x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 55.44 | 25.44 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1 | 90 | 5.84 | 5.22 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 90 | 11.17 | 7.85 | 1.42x |
| DeepSeek-V4-Flash-0731 | 4 | 90 | 20.53 | 11.04 | 1.86x |
| DeepSeek-V4-Flash-0731 | 8 | 90 | 35.10 | 15.62 | 2.25x |
| DeepSeek-V4-Flash-0731 | 16 | 90 | 53.53 | 20.79 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 90 | 70.34 | 26.03 | 2.70x |
| DeepSeek-V4-Flash-0731 | 64 | 90 | 80.36 | 30.29 | 2.65x |
| DeepSeek-V4-Flash-0731 | 256 | 90 | 84.81 | 33.14 | 2.56x |
| DeepSeek-V4-Flash-0731 | 1 | 96 | 5.85 | 5.26 | 1.11x |
| DeepSeek-V4-Flash-0731 | 2 | 96 | 11.21 | 7.97 | 1.41x |
| DeepSeek-V4-Flash-0731 | 4 | 96 | 20.68 | 11.21 | 1.85x |
| DeepSeek-V4-Flash-0731 | 8 | 96 | 35.59 | 15.96 | 2.23x |
| DeepSeek-V4-Flash-0731 | 16 | 96 | 54.82 | 21.32 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 96 | 72.93 | 26.80 | 2.72x |
| DeepSeek-V4-Flash-0731 | 64 | 96 | 84.16 | 31.27 | 2.69x |
| DeepSeek-V4-Flash-0731 | 256 | 96 | 89.38 | 34.28 | 2.61x |
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
| DeepSeek-V4-Pro-0813 | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Pro-0813 | 2 | 31 | 10.02 | 5.94 | 1.69x |
| DeepSeek-V4-Pro-0813 | 4 | 31 | 16.63 | 8.07 | 2.06x |
| DeepSeek-V4-Pro-0813 | 8 | 31 | 24.02 | 10.47 | 2.29x |
| DeepSeek-V4-Pro-0813 | 16 | 31 | 29.12 | 13.02 | 2.24x |
| DeepSeek-V4-Pro-0813 | 32 | 31 | 30.79 | 15.43 | 2.00x |
| DeepSeek-V4-Pro-0813 | 64 | 31 | 30.99 | 17.39 | 1.78x |
| DeepSeek-V4-Pro-0813 | 256 | 31 | 31.00 | 19.13 | 1.62x |
| DeepSeek-V4-Pro-0813 | 1 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 92 | 11.23 | 7.90 | 1.42x |
| DeepSeek-V4-Pro-0813 | 4 | 92 | 20.79 | 11.17 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 92 | 36.02 | 15.94 | 2.26x |
| DeepSeek-V4-Pro-0813 | 16 | 92 | 55.87 | 21.51 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 92 | 74.53 | 27.50 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 92 | 85.60 | 32.97 | 2.60x |
| DeepSeek-V4-Pro-0813 | 256 | 92 | 90.51 | 38.32 | 2.36x |
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
| DeepSeek-V4-Pro-0813 | 1 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 136 | 11.44 | 8.65 | 1.32x |
| DeepSeek-V4-Pro-0813 | 4 | 136 | 21.61 | 12.23 | 1.77x |
| DeepSeek-V4-Pro-0813 | 8 | 136 | 38.76 | 18.08 | 2.14x |
| DeepSeek-V4-Pro-0813 | 16 | 136 | 63.66 | 24.88 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 136 | 91.71 | 32.65 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 136 | 113.51 | 40.01 | 2.84x |
| DeepSeek-V4-Pro-0813 | 256 | 136 | 127.59 | 47.43 | 2.69x |
| DeepSeek-V4-Pro-0813 | 1 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 145 | 11.47 | 8.77 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 145 | 21.72 | 12.41 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 145 | 39.14 | 18.42 | 2.13x |
| DeepSeek-V4-Pro-0813 | 16 | 145 | 64.78 | 25.43 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 145 | 94.36 | 33.52 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 145 | 118.18 | 41.22 | 2.87x |
| DeepSeek-V4-Pro-0813 | 256 | 145 | 134.34 | 49.03 | 2.74x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 150.33 | 52.81 | 2.85x |
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
| DeepSeek-V4-Pro-0813 | 1 | 341 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 341 | 11.72 | 10.16 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 341 | 22.69 | 15.24 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 341 | 42.61 | 22.21 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 341 | 75.74 | 33.42 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 341 | 122.79 | 45.72 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 341 | 174.38 | 58.62 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 341 | 228.37 | 72.75 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 343 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 343 | 11.72 | 10.16 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 343 | 22.69 | 15.26 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 343 | 42.63 | 22.23 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 343 | 75.80 | 33.48 | 2.26x |
| DeepSeek-V4-Pro-0813 | 32 | 343 | 122.94 | 45.80 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 343 | 174.70 | 58.74 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 343 | 228.97 | 72.93 | 3.14x |
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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 1.6% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 0.7% |
| gpu | Qwen3-8B | 1 | 5.85 | 2.1% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 34.8% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 32.0% |
| rom | Qwen3-8B | 1 | 5.85 | 28.2% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Qwen3-8B | sram | interleaved | 128 B | 1.00x |
| Qwen3-8B | hbm | interleaved | 32 B | 1.00x |
| DeepSeek-V4-Flash-0731 | sram | interleaved | 128 B | 1.64x |
| DeepSeek-V4-Flash-0731 | hbm | interleaved | 32 B | 1.30x |
| DeepSeek-V4-Pro-0813 | sram | interleaved | 128 B | 1.67x |
| DeepSeek-V4-Pro-0813 | hbm | interleaved | 32 B | 1.31x |

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
| DeepSeek-V4-Flash-0731 | 1 | 26 | 49.43% | 1.06 | 2.14 |
| DeepSeek-V4-Flash-0731 | 2 | 26 | 98.86% | 2.12 | 2.14 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 4.57% | 0.10 | 2.14 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 9.14% | 0.20 | 2.14 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 18.28% | 0.39 | 2.14 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 36.57% | 0.78 | 2.14 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 73.13% | 1.57 | 2.14 |
| DeepSeek-V4-Pro-0813 | 1 | 138 | 91.53% | 1.90 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 3 | 14.66% | 0.30 | 2.08 |
| DeepSeek-V4-Pro-0813 | 4 | 3 | 29.33% | 0.61 | 2.08 |
| DeepSeek-V4-Pro-0813 | 8 | 3 | 58.66% | 1.22 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 9,617.6 | 9,617.6 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 5,260.2 | 10,520.5 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 2,759.7 | 11,038.6 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,414.7 | 11,317.3 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 716.4 | 11,462.0 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 360.5 | 11,535.7 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 180.8 | 11,573.0 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 45.3 | 11,601.0 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 8,203.8 | 8,203.8 |
| DeepSeek-V4-Flash-0731 | 2 | 4.63% | 14.6 GB | 8.74% | 190.54 TB/s | 2,179.91 TB/s | 6,487.0 | 12,974.0 |
| DeepSeek-V4-Flash-0731 | 4 | 9.05% | 21.1 GB | 12.64% | 275.47 TB/s | 2,179.91 TB/s | 3,681.4 | 14,725.5 |
| DeepSeek-V4-Flash-0731 | 8 | 17.28% | 33.2 GB | 19.90% | 433.71 TB/s | 2,179.91 TB/s | 1,973.9 | 15,791.4 |
| DeepSeek-V4-Flash-0731 | 16 | 31.58% | 54.2 GB | 32.50% | 708.53 TB/s | 2,179.91 TB/s | 1,024.0 | 16,384.5 |
| DeepSeek-V4-Flash-0731 | 32 | 53.18% | 86.0 GB | 51.56% | 1,123.90 TB/s | 2,179.91 TB/s | 521.8 | 16,698.0 |
| DeepSeek-V4-Flash-0731 | 64 | 78.08% | 122.7 GB | 73.52% | 1,602.57 TB/s | 2,179.91 TB/s | 263.4 | 16,859.3 |
| DeepSeek-V4-Flash-0731 | 256 | 99.77% | 154.6 GB | 92.64% | 2,019.50 TB/s | 2,179.91 TB/s | 66.3 | 16,982.3 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 4,021.3 | 4,021.3 |
| DeepSeek-V4-Pro-0813 | 2 | 3.10% | 52.3 GB | 5.86% | 683.32 TB/s | 11,661.57 TB/s | 2,957.6 | 5,915.3 |
| DeepSeek-V4-Pro-0813 | 4 | 6.11% | 77.0 GB | 8.63% | 1,005.95 TB/s | 11,661.57 TB/s | 1,934.4 | 7,737.4 |
| DeepSeek-V4-Pro-0813 | 8 | 11.84% | 124.1 GB | 13.90% | 1,621.51 TB/s | 11,661.57 TB/s | 1,143.3 | 9,146.1 |
| DeepSeek-V4-Pro-0813 | 16 | 22.27% | 209.9 GB | 23.51% | 2,742.18 TB/s | 11,661.57 TB/s | 628.9 | 10,062.0 |
| DeepSeek-V4-Pro-0813 | 32 | 39.59% | 352.2 GB | 39.46% | 4,601.25 TB/s | 11,661.57 TB/s | 331.0 | 10,592.4 |
| DeepSeek-V4-Pro-0813 | 64 | 63.50% | 548.8 GB | 61.48% | 7,169.39 TB/s | 11,661.57 TB/s | 170.0 | 10,879.2 |
| DeepSeek-V4-Pro-0813 | 256 | 98.23% | 834.3 GB | 93.45% | 10,898.18 TB/s | 11,661.57 TB/s | 43.4 | 11,104.6 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 2 |
| gpu | kv_read | 42 |
| gpu | link_latency | 8 |
| gpu | weight_read | 244 |
| rom | compute | 52 |
| rom | infeasible | 580 |
| rom | kv_read | 448 |
| rom | layer_fixed_latency | 4 |
| rom | link_latency | 121 |
| rom | weight_read | 331 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 2 |
| rom | CAPACITY | 580 |

## Mechanical consistency audit

**PASS** over 26,667 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 1 |
| published | 48 |
| derived | 21 |
| assumed | 43 |

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
- `links.ethernet.hop_latency_s`
- `links.nvlink.hop_latency_s`
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
- Power is a dynamic-activity lower bound: leakage, clock distribution
  and idle logic are not modelled, so `thermal` binding is under-reported.
- Prefill, speculative decoding and cost are out of scope for this model.

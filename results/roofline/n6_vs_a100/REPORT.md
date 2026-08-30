# Area-constrained roofline: n6_vs_a100

> Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 76.6 us, or 13,063 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **The ROM advantage is a batch-1, per-user advantage, and it is large.** At equal area the best batch-1 point is Qwen3-8B on 1,630 mm2 of ROM silicon at 11,552 tok/s per user, against 1,652 mm2 of a100_sxm_80gb-x2 at 191 tok/s: **61x**. Both sides bind on `weight_read`, and the whole difference is that one reads its weights from HBM and the other from an on-die array.
3. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.19x (Qwen3-8B, ROM binding on `kv_read`) to 1.34x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
4. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 92.6% at batch 256, while the weight-read time is identical at both. Aggregate throughput rises from 8,911 to 16,993 tok/s on the same machine. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
5. **Tensor parallelism is a latency argument for wafer-scale, and it is the sharpest one.** Two all-reduces per layer per token cost up to 189 us over NVLink, capping per-user decode at 5,296 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 12.2 us and cap it at 81,966 tok/s.
6. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 15 of 15 operating points and an array 0; on tokens per second per square millimetre the same points go 6 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
7. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 103 of 260 feasible points.
8. **The largest open question is not in this model's inputs but in the architecture, and the anchor cannot settle it.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 11.5x of aggregate throughput (DeepSeek-V4-Flash-0731). The two machines are identical at batch 1, which is where the published anchor sits, so no amount of validation against it resolves the fork.
9. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 13,062.9 tok/s | 0.77x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |

HC1 binds on `weight_read`. Its component times are weight_read 76.55 us, kv_read 9.28 us, compute 59.75 us, link_latency 0.00 us.

The model **under**-predicts the shipping part by 1.30x. Rather than tune the densities until the anchor
is hit, the gate back-derives what each input would have to be for the
model to land exactly on 17,000 tok/s:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 2.822e+11 | 3.664e+11 | 1.30x |
| Compute density (ops/s/mm2) | 1.261e+12 | 1.278e+12 | 1.01x |

The compute density derived from A100's published dense roofs and die
area is within 1.3% of what the shipping part must have. The ROM read-bandwidth density derived from a
28 nm simulated ROM-CIM macro is the input that is short, and the
required value is still below the SRAM read-bandwidth density derived
from Cerebras WSE-2 (4.327e+11 B/s/mm2), so it is physically unremarkable. That is a falsifiable
statement about one technology input, which is what a gate is for.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 13,062.9 | 0.77x | weight_read |
| 3.5 | 13,062.9 | 0.77x | weight_read |
| 4.0 | 13,062.9 | 0.77x | weight_read |
| 5.0 | 12,442.8 | 0.73x | compute |
| 6.0 | 9,581.2 | 0.56x | compute |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 13,062.9 | 0.77x | weight_read |
| 1,536 | 13,062.9 | 0.77x | weight_read |
| 2,048 | 13,062.9 | 0.77x | weight_read |

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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 12,172.4 | weight_read | Qwen3-8B/a100_sxm_80gb-x56 | 46,256 | 1.00x | 3,702.1 | 3,702.1 | weight_read | 3.29x | 3.29x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-fp8-SRAMKV-array-pipeline-x2 | 1,630 | 11,551.6 | 11,551.6 | weight_read | Qwen3-8B/a100_sxm_80gb-x2 | 1,652 | 0.99x | 190.8 | 190.8 | weight_read | 60.54x | 60.54x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1,529.0 | 12,231.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x56 | 46,256 | 1.00x | 2,699.5 | 21,596.1 | weight_read | 0.57x | 0.57x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 1,426.5 | 11,411.7 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 562.0 | 4,496.2 | weight_read | 2.54x | 2.54x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 384.7 | 12,311.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x56 | 46,256 | 1.00x | 1,399.8 | 44,793.8 | kv_read | 0.27x | 0.27x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 361.3 | 11,560.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 260.0 | 8,319.5 | kv_read | 1.39x | 1.39x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 192.6 | 12,324.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x56 | 46,256 | 1.00x | 852.5 | 54,561.8 | kv_read | 0.23x | 0.23x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 181.0 | 11,585.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 151.5 | 9,693.3 | kv_read | 1.20x | 1.20x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 48.2 | 12,334.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x56 | 46,256 | 1.00x | 254.8 | 65,230.2 | kv_read | 0.19x | 0.19x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x9 | 7,335 | 45.3 | 11,604.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x9 | 7,434 | 0.99x | 43.2 | 11,063.4 | kv_read | 1.05x | 1.05x |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 12,172.4 | weight_read | DSV4-Flash/a100_sxm_80gb-x56 | 46,256 | 1.00x | 1,790.8 | 1,790.8 | weight_read | 6.80x | 6.80x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x18 | 14,670 | 9,032.3 | 9,032.3 | weight_read | DSV4-Flash/a100_sxm_80gb-x18 | 14,868 | 0.99x | 1,371.7 | 1,371.7 | weight_read | 6.58x | 6.58x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 97,379.2 | weight_read | DSV4-Flash/a100_sxm_80gb-x56 | 46,256 | 1.00x | 1,399.6 | 11,196.7 | weight_read | 8.70x | 8.70x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 2,012.3 | 16,098.8 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 792.6 | 6,340.5 | weight_read | 2.54x | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 4,578.2 | 146,503.1 | kv_read | DSV4-Flash/a100_sxm_80gb-x56 | 46,256 | 1.00x | 830.5 | 26,575.1 | weight_read | 5.51x | 5.51x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 524.5 | 16,782.7 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 328.5 | 10,512.4 | weight_read | 1.60x | 1.60x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 2,318.8 | 148,405.5 | kv_read | DSV4-Flash/a100_sxm_80gb-x56 | 46,256 | 1.00x | 614.1 | 39,299.3 | weight_read | 3.78x | 3.78x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 264.1 | 16,902.4 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 227.7 | 14,574.9 | weight_read | 1.16x | 1.16x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 585.4 | 149,865.1 | kv_read | DSV4-Flash/a100_sxm_80gb-x56 | 46,256 | 1.00x | 437.0 | 111,884.6 | weight_read | 1.34x | 1.34x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | 15,485 | 66.4 | 16,993.2 | compute | DSV4-Flash/a100_sxm_80gb-x19 | 15,694 | 0.99x | 162.8 | 41,682.6 | weight_read | 0.41x | 0.41x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | 92,450 | 10,377.9 | 10,377.9 | weight_read | DSV4-Pro/a100_sxm_80gb-x112 | 92,512 | 1.00x | 578.4 | 578.4 | weight_read | 17.94x | 17.94x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x93 | 75,795 | 4,363.3 | 4,363.3 | link_latency | DSV4-Pro/a100_sxm_80gb-x92 | 75,992 | 1.00x | 574.8 | 574.8 | weight_read | 7.59x | 7.59x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 6,843.4 | 54,747.0 | kv_read | DSV4-Pro/a100_sxm_80gb-x168 | 138,768 | 1.00x | 511.0 | 4,087.7 | weight_read | 13.39x | 13.39x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 1,161.5 | 9,292.1 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 480.5 | 3,843.9 | weight_read | 2.42x | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 1,825.1 | 58,404.0 | kv_read | DSV4-Pro/a100_sxm_80gb-x168 | 138,768 | 1.00x | 384.3 | 12,297.6 | weight_read | 4.75x | 4.75x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 332.5 | 10,640.9 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 310.1 | 9,923.4 | weight_read | 1.07x | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 922.8 | 59,061.6 | kv_read | DSV4-Pro/a100_sxm_80gb-x168 | 138,768 | 1.00x | 304.4 | 19,479.3 | weight_read | 3.03x | 3.03x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 170.4 | 10,904.7 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 224.5 | 14,369.6 | weight_read | 0.76x | 0.76x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 232.7 | 59,564.5 | kv_read | DSV4-Pro/a100_sxm_80gb-x168 | 138,768 | 1.00x | 194.7 | 49,848.3 | weight_read | 1.19x | 1.19x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x98 | 79,870 | 43.4 | 11,111.2 | compute | DSV4-Pro/a100_sxm_80gb-x97 | 80,122 | 1.00x | 137.0 | 35,075.1 | weight_read | 0.32x | 0.32x |

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
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 0.263 | 11,551.6 (1,630) | 12,172.4 (46,225) | 1.05x | weight_read |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1,529.0 | 0.033 | 1,426.5 (7,335) | 1,529.0 (46,225) | 1.07x | kv_read |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 384.7 | 0.008 | 361.3 (7,335) | 384.7 (46,225) | 1.06x | kv_read |
| Qwen3-8B | 64 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 192.6 | 0.004 | 181.0 (7,335) | 192.6 (46,225) | 1.06x | kv_read |
| Qwen3-8B | 256 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 48.2 | 0.001 | 45.3 (7,335) | 48.2 (46,225) | 1.06x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 0.263 | 9,032.3 (14,670) | 12,172.4 (46,225) | 1.35x | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 0.263 | 2,012.3 (15,485) | 12,172.4 (46,225) | 6.05x | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 4,578.2 | 0.099 | 524.5 (15,485) | 4,578.2 (46,225) | 8.73x | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 2,318.8 | 0.050 | 264.1 (15,485) | 2,318.8 (46,225) | 8.78x | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 585.4 | 0.013 | 66.4 (15,485) | 585.4 (46,225) | 8.82x | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | 92,450 | 10,377.9 | 0.112 | 4,363.3 (75,795) | 10,377.9 (92,450) | 2.38x | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 6,843.4 | 0.049 | 1,161.5 (79,870) | 6,843.4 (138,675) | 5.89x | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 1,825.1 | 0.013 | 332.5 (79,870) | 1,825.1 (138,675) | 5.49x | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 922.8 | 0.007 | 170.4 (79,870) | 922.8 (138,675) | 5.42x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3 | 138,675 | 232.7 | 0.002 | 43.4 (79,870) | 232.7 (138,675) | 5.36x | kv_read |

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
machine; a design identifier ending `-perstream` is the compute-in-ROM
variant.

| Model | B | Batched user tok/s | Batched aggregate | Per-stream user tok/s | Per-stream aggregate | Aggregate penalty | Batched binds on | Per-stream binds on |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Qwen3-8B | 1 | 12,172.4 | 12,172.4 | 12,172.4 | 12,172.4 | 1.00x | weight_read | weight_read |
| Qwen3-8B | 8 | 1,529.0 | 12,231.9 | 1,529.0 | 12,231.9 | 1.00x | kv_read | kv_read |
| Qwen3-8B | 32 | 384.7 | 12,311.0 | 384.7 | 12,311.0 | 1.00x | kv_read | kv_read |
| Qwen3-8B | 64 | 192.6 | 12,324.3 | 192.6 | 12,324.3 | 1.00x | kv_read | kv_read |
| Qwen3-8B | 256 | 48.2 | 12,334.2 | 48.2 | 12,334.2 | 1.00x | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | 12,172.4 | 12,172.4 | 12,172.4 | 12,172.4 | 1.00x | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | 12,172.4 | 97,379.2 | 1,618.1 | 12,944.5 | 7.52x | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | 4,578.2 | 146,503.1 | 407.3 | 13,033.1 | 11.24x | kv_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | 2,318.8 | 148,405.5 | 203.9 | 13,047.9 | 11.37x | kv_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | 585.4 | 149,865.1 | 51.0 | 13,059.1 | 11.48x | kv_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | 10,377.9 | 10,377.9 | 10,377.9 | 10,377.9 | 1.00x | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | 6,843.4 | 54,747.0 | 1,443.7 | 11,549.5 | 4.74x | kv_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | 1,825.1 | 58,404.0 | 365.8 | 11,704.1 | 4.99x | kv_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | 922.8 | 59,061.6 | 183.3 | 11,730.3 | 5.03x | kv_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | 232.7 | 59,564.5 | 45.9 | 11,750.0 | 5.07x | kv_read | weight_read |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 10,190.6 | 10,190.6 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,426.5 | 11,411.7 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 361.3 | 11,560.1 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 181.0 | 11,585.2 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 45.3 | 11,604.1 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 8,910.9 | 8,910.9 |
| DeepSeek-V4-Flash-0731 | 8 | 17.28% | 33.2 GB | 19.90% | 433.71 TB/s | 2,179.91 TB/s | 2,012.3 | 16,098.8 |
| DeepSeek-V4-Flash-0731 | 32 | 53.18% | 86.0 GB | 51.56% | 1,123.90 TB/s | 2,179.91 TB/s | 524.5 | 16,782.7 |
| DeepSeek-V4-Flash-0731 | 64 | 78.08% | 122.7 GB | 73.52% | 1,602.57 TB/s | 2,179.91 TB/s | 264.1 | 16,902.4 |
| DeepSeek-V4-Flash-0731 | 256 | 99.77% | 154.6 GB | 92.64% | 2,019.50 TB/s | 2,179.91 TB/s | 66.4 | 16,993.2 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 4,256.6 | 4,256.6 |
| DeepSeek-V4-Pro-0813 | 8 | 11.84% | 124.1 GB | 13.90% | 1,621.51 TB/s | 11,661.57 TB/s | 1,161.5 | 9,292.1 |
| DeepSeek-V4-Pro-0813 | 32 | 39.59% | 352.2 GB | 39.46% | 4,601.25 TB/s | 11,661.57 TB/s | 332.5 | 10,640.9 |
| DeepSeek-V4-Pro-0813 | 64 | 63.50% | 548.8 GB | 61.48% | 7,169.39 TB/s | 11,661.57 TB/s | 170.4 | 10,904.7 |
| DeepSeek-V4-Pro-0813 | 256 | 98.23% | 834.3 GB | 93.45% | 10,898.18 TB/s | 11,661.57 TB/s | 43.4 | 11,111.2 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 2 |
| gpu | kv_read | 13 |
| gpu | weight_read | 55 |
| rom | compute | 24 |
| rom | infeasible | 128 |
| rom | kv_read | 90 |
| rom | link_latency | 20 |
| rom | weight_read | 58 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 2 |
| rom | CAPACITY | 128 |

## Mechanical consistency audit

**PASS** over 5,351 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 1 |
| published | 48 |
| derived | 21 |
| assumed | 30 |

Every `assumed` input, in full, because an ungraded assumption is the
failure mode this program exists to prevent:

- `efficiencies.compute`
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

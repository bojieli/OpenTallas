# Area-constrained roofline: n5_vs_b200

> Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 76.6 us, or 13,063 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **The ROM advantage is a batch-1, per-user advantage, and it is large.** At equal area the best batch-1 point is Qwen3-8B on 1,630 mm2 of ROM silicon at 11,552 tok/s per user, against 1,600 mm2 of b200_sxm-x1 at 416 tok/s: **28x**. Both sides bind on `weight_read`, and the whole difference is that one reads its weights from HBM and the other from an on-die array.
3. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.18x (DeepSeek-V4-Pro-0813, ROM binding on `compute`) to 1.60x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
4. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 92.6% at batch 256, while the weight-read time is identical at both. Aggregate throughput rises from 9,457 to 11,585 tok/s on the same machine. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
5. **Tensor parallelism is a latency argument for wafer-scale, and it is the sharpest one.** Two all-reduces per layer per token cost up to 189 us over NVLink, capping per-user decode at 5,296 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 12.2 us and cap it at 81,966 tok/s.
6. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 15 of 15 operating points and an array 0; on tokens per second per square millimetre the same points go 6 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
7. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 104 of 329 feasible points.
8. **The largest open question is not in this model's inputs but in the architecture, and the anchor cannot settle it.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 17.5x of aggregate throughput (DeepSeek-V4-Flash-0731). The machines are identical at batch 1, which is where the published anchor sits, so no amount of validation against it resolves the fork.
9. **A third machine sits between them, and for a sparse model it recovers most of what compute-in-ROM gives up.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise. At batch 256 that closes the gap to 1.00x of the amortising machine (DeepSeek-V4-Flash-0731), against 17.5x for a global activation broadcast. A dense model has one region, so it gains nothing — the disjointness is what sparsity buys.
10. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 20,900.6 tok/s | 1.23x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |

HC1 binds on `weight_read`. Its component times are weight_read 47.85 us, kv_read 2.71 us, compute 47.85 us, link_latency 0.00 us.

The model **under**-predicts the shipping part by 0.81x. Rather than tune the densities until the anchor
is hit, the gate back-derives what each input would have to be for the
model to land exactly on 17,000 tok/s:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 2.822e+11 | 2.290e+11 | 0.81x |
| Compute density (ops/s/mm2) | 1.261e+12 | 2.840e+13 | 22.52x |

The compute density derived from A100's published dense roofs and die
area is within 2152.4% of what the shipping part must have. The ROM read-bandwidth density derived from a
28 nm simulated ROM-CIM macro is the input that is short, and the
required value is still below the SRAM read-bandwidth density derived
from Cerebras WSE-2 (5.563e+11 B/s/mm2), so it is physically unremarkable. That is a falsifiable
statement about one technology input, which is what a gate is for.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 20,900.6 | 1.23x | weight_read |
| 3.5 | 20,900.6 | 1.23x | weight_read |
| 4.0 | 20,900.6 | 1.23x | weight_read |
| 5.0 | 20,900.6 | 1.23x | weight_read |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 20,900.6 | 1.23x | weight_read |
| 1,536 | 20,900.6 | 1.23x | weight_read |
| 2,048 | 20,900.6 | 1.23x | weight_read |

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
| DeepSeek-V4-Flash-0731 | 200,000 | 284 B | 166.9 GB | 4.70 | 0.099 GB | 0.705 GB | 113.2 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1,600 B | 892.7 GB | 4.46 | 0.674 GB | 5.028 GB | 58.9 |

## Iso-area comparison

Two ROM designs per operating point -- the **fastest** and the
**smallest silicon that serves the point at all** -- each against the GPU
cluster of the closest equal silicon area. **The area is stated on both
sides.** Where one row appears, the two coincide.

| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | GPU user tok/s | GPU aggregate tok/s | GPU binds on | Per-user ratio | Aggregate ratio |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---:|
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 12,172.4 | weight_read | Qwen3-8B/b200_sxm-x29 | 46,400 | 1.00x | 7,443.3 | 7,443.3 | weight_read | 1.64x | 1.64x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N5-fp8-SRAMKV-array-pipeline-x2 | 1,630 | 11,551.6 | 11,551.6 | weight_read | Qwen3-8B/b200_sxm-x1 | 1,600 | 1.02x | 416.0 | 416.0 | weight_read | 27.77x | 27.77x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 3,703.3 | 29,626.5 | kv_read | Qwen3-8B/b200_sxm-x29 | 46,400 | 1.00x | 5,441.2 | 43,529.8 | weight_read | 0.68x | 0.68x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 1,571.3 | 12,570.5 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | 493.1 | 3,945.1 | weight_read | 3.19x | 3.19x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 940.5 | 30,094.6 | kv_read | Qwen3-8B/b200_sxm-x29 | 46,400 | 1.00x | 2,830.7 | 90,583.0 | kv_read | 0.33x | 0.33x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 394.9 | 12,637.6 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | 227.4 | 7,277.8 | kv_read | 1.74x | 1.74x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 471.5 | 30,174.0 | kv_read | Qwen3-8B/b200_sxm-x29 | 46,400 | 1.00x | 1,726.4 | 110,488.3 | kv_read | 0.27x | 0.27x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 197.6 | 12,648.8 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | 132.4 | 8,470.5 | kv_read | 1.49x | 1.49x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 118.1 | 30,233.9 | kv_read | Qwen3-8B/b200_sxm-x29 | 46,400 | 1.00x | 516.8 | 132,291.2 | kv_read | 0.23x | 0.23x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 49.4 | 12,657.2 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | infeasible | — | capacity_or_format | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 12,172.4 | weight_read | DSV4-Flash/b200_sxm-x29 | 46,400 | 1.00x | 5,292.5 | 5,292.5 | weight_read | 2.30x | 2.30x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x14 | 11,410 | 9,553.2 | 9,553.2 | weight_read | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 3,066.3 | 3,066.3 | weight_read | 3.12x | 3.12x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 97,379.2 | weight_read | DSV4-Flash/b200_sxm-x29 | 46,400 | 1.00x | 3,648.7 | 29,189.5 | weight_read | 3.34x | 3.34x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 1,409.5 | 11,276.4 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 1,244.4 | 9,954.9 | weight_read | 1.13x | 1.13x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 10,823.6 | 346,355.9 | kv_read | DSV4-Flash/b200_sxm-x29 | 46,400 | 1.00x | 1,796.8 | 57,497.4 | weight_read | 6.02x | 6.02x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 359.8 | 11,513.7 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 477.7 | 15,288.0 | weight_read | 0.75x | 0.75x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 5,580.9 | 357,180.7 | kv_read | DSV4-Flash/b200_sxm-x29 | 46,400 | 1.00x | 1,272.5 | 81,437.3 | weight_read | 4.39x | 4.39x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 180.5 | 11,554.3 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 330.7 | 21,161.9 | weight_read | 0.55x | 0.55x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1,428.7 | 365,754.0 | kv_read | DSV4-Flash/b200_sxm-x29 | 46,400 | 1.00x | 891.7 | 228,283.4 | weight_read | 1.60x | 1.60x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 45.3 | 11,584.8 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 236.7 | 60,604.7 | weight_read | 0.19x | 0.19x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | 92,450 | 10,377.9 | 10,377.9 | weight_read | DSV4-Pro/b200_sxm-x58 | 92,800 | 1.00x | 1,890.2 | 1,890.2 | weight_read | 5.49x | 5.49x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x72 | 58,680 | 5,189.7 | 5,189.7 | link_latency | DSV4-Pro/b200_sxm-x37 | 59,200 | 0.99x | 1,817.6 | 1,817.6 | weight_read | 2.86x | 2.86x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 10,377.8 | 83,022.6 | weight_read | DSV4-Pro/b200_sxm-x58 | 92,800 | 1.00x | 1,459.4 | 11,674.9 | weight_read | 7.11x | 7.11x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 1,190.2 | 9,521.6 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 1,258.8 | 10,070.7 | weight_read | 0.95x | 0.95x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 2,949.9 | 94,398.0 | kv_read | DSV4-Pro/b200_sxm-x58 | 92,800 | 1.00x | 807.9 | 25,852.5 | weight_read | 3.65x | 3.65x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 330.3 | 10,568.8 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 586.0 | 18,753.0 | weight_read | 0.56x | 0.56x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1,500.0 | 95,998.0 | kv_read | DSV4-Pro/b200_sxm-x58 | 92,800 | 1.00x | 545.6 | 34,920.1 | weight_read | 2.75x | 2.75x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 168.2 | 10,766.1 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 378.5 | 24,224.3 | weight_read | 0.44x | 0.44x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 379.8 | 97,234.1 | kv_read | DSV4-Pro/b200_sxm-x58 | 92,800 | 1.00x | 316.7 | 81,079.0 | weight_read | 1.20x | 1.20x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 42.7 | 10,919.1 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 220.5 | 56,443.0 | weight_read | 0.19x | 0.19x |

## Array or wafer: the crossover, reported rather than assumed

`Array viable to` is the per-user rate at which the topology's hops alone
consume 10% of the token budget; `hard ceiling` is the rate at which they
consume all of it. Below the first number the interconnect is a design
cost; above the second the topology cannot deliver the rate at all.

| Design | Model | Devices | Parallelism | Link | Hops/token | Link latency/token | Viable to (10% budget) | Hard ceiling |
|---|---|---:|---|---|---:|---:|---:|---:|
| Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x3 | Qwen3-8B | 3 | pipeline | nvlink | 2 | 3.02 us | 33,132.3 tok/s | 331,322.8 tok/s |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x3 | Qwen3-8B | 3 | tensor | nvlink | 72 | 109.97 us | 909.4 tok/s | 9,093.7 tok/s |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | 72 | 7.20 us | 13,888.8 tok/s | 138,887.6 tok/s |
| Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | Qwen3-8B | 4 | pipeline | nvlink | 3 | 4.53 us | 22,088.2 tok/s | 220,881.9 tok/s |
| Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | Qwen3-8B | 4 | tensor | nvlink | 72 | 109.97 us | 909.4 tok/s | 9,093.7 tok/s |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | 72 | 7.20 us | 13,888.8 tok/s | 138,887.6 tok/s |
| Qwen3-8B/ROM-N5-fp8-SRAMKV-array-pipeline-x2 | Qwen3-8B | 2 | pipeline | nvlink | 1 | 1.51 us | 66,264.6 tok/s | 662,645.6 tok/s |
| Qwen3-8B/ROM-N5-fp8-SRAMKV-array-tensor-x2 | Qwen3-8B | 2 | tensor | nvlink | 72 | 109.97 us | 909.4 tok/s | 9,093.7 tok/s |
| Qwen3-8B/ROM-N5-fp8-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| Qwen3-8B/ROM-N5-fp8-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | 72 | 7.20 us | 13,888.8 tok/s | 138,887.6 tok/s |
| Qwen3-8B/ROM-N5-fp8-HBMKV-array-pipeline-x4 | Qwen3-8B | 4 | pipeline | nvlink | 3 | 4.53 us | 22,088.2 tok/s | 220,881.9 tok/s |
| Qwen3-8B/ROM-N5-fp8-HBMKV-array-tensor-x4 | Qwen3-8B | 4 | tensor | nvlink | 72 | 109.97 us | 909.4 tok/s | 9,093.7 tok/s |
| Qwen3-8B/ROM-N5-fp8-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| Qwen3-8B/ROM-N5-fp8-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | 72 | 7.20 us | 13,888.8 tok/s | 138,887.6 tok/s |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x14 | DeepSeek-V4-Flash-0731 | 14 | pipeline | nvlink | 13 | 19.62 us | 5,097.3 tok/s | 50,972.7 tok/s |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x14 | DeepSeek-V4-Flash-0731 | 14 | tensor | nvlink | 86 | 131.35 us | 761.3 tok/s | 7,613.3 tok/s |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | 86 | 8.60 us | 11,627.8 tok/s | 116,278.0 tok/s |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | DeepSeek-V4-Flash-0731 | 14 | pipeline | nvlink | 13 | 19.62 us | 5,097.3 tok/s | 50,972.7 tok/s |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x14 | DeepSeek-V4-Flash-0731 | 14 | tensor | nvlink | 86 | 131.35 us | 761.3 tok/s | 7,613.3 tok/s |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | 56 | 5.60 us | 17,857.1 tok/s | 178,570.9 tok/s |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | 86 | 8.60 us | 11,627.8 tok/s | 116,278.0 tok/s |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x72 | DeepSeek-V4-Pro-0813 | 72 | pipeline | nvlink | 71 | 107.63 us | 929.1 tok/s | 9,291.0 tok/s |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x72 | DeepSeek-V4-Pro-0813 | 72 | tensor | nvlink | 122 | 188.83 us | 529.6 tok/s | 5,295.8 tok/s |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4-Pro-0813 | 2 | pipeline | on_wafer | 113 | 11.30 us | 8,849.5 tok/s | 88,495.1 tok/s |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4-Pro-0813 | 2 | tensor | on_wafer | 122 | 12.20 us | 8,196.6 tok/s | 81,965.9 tok/s |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | DeepSeek-V4-Pro-0813 | 75 | pipeline | nvlink | 74 | 112.18 us | 891.4 tok/s | 8,914.3 tok/s |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x75 | DeepSeek-V4-Pro-0813 | 75 | tensor | nvlink | 122 | 188.83 us | 529.6 tok/s | 5,295.8 tok/s |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4-Pro-0813 | 2 | pipeline | on_wafer | 113 | 11.30 us | 8,849.5 tok/s | 88,495.1 tok/s |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4-Pro-0813 | 2 | tensor | on_wafer | 122 | 12.20 us | 8,196.6 tok/s | 81,965.9 tok/s |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 0.263 | 11,551.6 (1,630) | 12,172.4 (46,225) | 1.05x | weight_read |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 3,703.3 | 0.080 | 1,571.3 (3,260) | 3,703.3 (46,225) | 2.36x | kv_read |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 940.5 | 0.020 | 394.9 (3,260) | 940.5 (46,225) | 2.38x | kv_read |
| Qwen3-8B | 64 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 471.5 | 0.010 | 197.6 (3,260) | 471.5 (46,225) | 2.39x | kv_read |
| Qwen3-8B | 256 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 118.1 | 0.003 | 49.4 (3,260) | 118.1 (46,225) | 2.39x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 0.263 | 9,553.2 (11,410) | 12,172.4 (46,225) | 1.27x | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 12,172.4 | 0.263 | 1,409.5 (11,410) | 12,172.4 (46,225) | 8.64x | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 10,823.6 | 0.234 | 359.8 (11,410) | 10,823.6 (46,225) | 30.08x | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 5,580.9 | 0.121 | 180.5 (11,410) | 5,580.9 (46,225) | 30.91x | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1,428.7 | 0.031 | 45.3 (11,410) | 1,428.7 (46,225) | 31.57x | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | 92,450 | 10,377.9 | 0.112 | 5,189.7 (58,680) | 10,377.9 (92,450) | 2.00x | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 10,377.8 | 0.112 | 1,190.2 (61,125) | 10,377.8 (92,450) | 8.72x | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 2,949.9 | 0.032 | 330.3 (61,125) | 2,949.9 (92,450) | 8.93x | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1,500.0 | 0.016 | 168.2 (61,125) | 1,500.0 (92,450) | 8.92x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 379.8 | 0.004 | 42.7 (61,125) | 379.8 (92,450) | 8.90x | kv_read |

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

| Model | B | Batched user tok/s | Batched aggregate | Per-stream user tok/s | Per-stream aggregate | Aggregate penalty | Batched binds on | Per-stream binds on |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Qwen3-8B | 1 | 12,172.4 | 12,172.4 | 18,710.6 | 18,710.6 | 0.65x | weight_read | weight_read |
| Qwen3-8B | 8 | 3,703.3 | 29,626.5 | 2,574.9 | 20,599.2 | 1.44x | kv_read | weight_read |
| Qwen3-8B | 32 | 940.5 | 30,094.6 | 650.8 | 20,824.4 | 1.45x | kv_read | weight_read |
| Qwen3-8B | 64 | 471.5 | 30,174.0 | 326.0 | 20,862.4 | 1.45x | kv_read | weight_read |
| Qwen3-8B | 256 | 118.1 | 30,233.9 | 81.6 | 20,891.0 | 1.45x | kv_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | 12,172.4 | 12,172.4 | 18,710.6 | 18,710.6 | 0.65x | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | 12,172.4 | 97,379.2 | 2,574.9 | 20,599.2 | 4.73x | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | 10,823.6 | 346,355.9 | 650.8 | 20,824.4 | 16.63x | kv_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | 5,580.9 | 357,180.7 | 326.0 | 20,862.4 | 17.12x | kv_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | 1,428.7 | 365,754.0 | 81.6 | 20,891.0 | 17.51x | kv_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | 10,377.9 | 10,377.9 | 15,513.1 | 15,513.1 | 0.67x | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | 10,377.8 | 83,022.6 | 2,290.5 | 18,323.6 | 4.53x | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | 2,949.9 | 94,398.0 | 583.9 | 18,686.4 | 5.05x | kv_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | 1,500.0 | 95,998.0 | 292.9 | 18,748.2 | 5.12x | kv_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | 379.8 | 97,234.1 | 73.4 | 18,794.9 | 5.17x | kv_read | weight_read |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 11,162.4 | 11,162.4 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,571.3 | 12,570.5 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 394.9 | 12,637.6 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 197.6 | 12,648.8 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 49.4 | 12,657.2 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 9,456.8 | 9,456.8 |
| DeepSeek-V4-Flash-0731 | 8 | 17.28% | 33.2 GB | 19.90% | 433.71 TB/s | 2,179.91 TB/s | 1,409.5 | 11,276.4 |
| DeepSeek-V4-Flash-0731 | 32 | 53.18% | 86.0 GB | 51.56% | 1,123.90 TB/s | 2,179.91 TB/s | 359.8 | 11,513.7 |
| DeepSeek-V4-Flash-0731 | 64 | 78.08% | 122.7 GB | 73.52% | 1,602.57 TB/s | 2,179.91 TB/s | 180.5 | 11,554.3 |
| DeepSeek-V4-Flash-0731 | 256 | 99.77% | 154.6 GB | 92.64% | 2,019.50 TB/s | 2,179.91 TB/s | 45.3 | 11,584.8 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 4,946.8 | 4,946.8 |
| DeepSeek-V4-Pro-0813 | 8 | 11.84% | 124.1 GB | 13.90% | 1,621.51 TB/s | 11,661.57 TB/s | 1,190.2 | 9,521.6 |
| DeepSeek-V4-Pro-0813 | 32 | 39.59% | 352.2 GB | 39.46% | 4,601.25 TB/s | 11,661.57 TB/s | 330.3 | 10,568.8 |
| DeepSeek-V4-Pro-0813 | 64 | 63.50% | 548.8 GB | 61.48% | 7,169.39 TB/s | 11,661.57 TB/s | 168.2 | 10,766.1 |
| DeepSeek-V4-Pro-0813 | 256 | 98.23% | 834.3 GB | 93.45% | 10,898.18 TB/s | 11,661.57 TB/s | 42.7 | 10,919.1 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 2 |
| gpu | kv_read | 10 |
| gpu | weight_read | 43 |
| rom | compute | 17 |
| rom | infeasible | 204 |
| rom | kv_read | 94 |
| rom | link_latency | 18 |
| rom | weight_read | 147 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 2 |
| rom | AREA | 80 |
| rom | CAPACITY | 156 |

## Mechanical consistency audit

**PASS** over 7,026 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 1 |
| published | 48 |
| derived | 21 |
| assumed | 33 |

Every `assumed` input, in full, because an ungraded assumption is the
failure mode this program exists to prevent:

- `efficiencies.compute`
- `efficiencies.expert_load_balance`
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

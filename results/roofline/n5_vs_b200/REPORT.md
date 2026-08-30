# Area-constrained roofline: n5_vs_b200

> Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 76.6 us, or 13,063 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **The ROM advantage is a batch-1, per-user advantage, and it is large.** At equal area the best batch-1 point is Qwen3-8B on 1,630 mm2 of ROM silicon at 10,821 tok/s per user, against 1,600 mm2 of b200_sxm-x1 at 415 tok/s: **26x**. Both sides bind on `weight_read`, and the whole difference is that one reads its weights from HBM and the other from an on-die array.
3. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.23x (DeepSeek-V4-Flash-0731, ROM binding on `compute`) to 4.25x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
4. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 92.6% at batch 256, while the weight-read time is identical at both. Aggregate throughput rises from 8,664 to 11,580 tok/s on the same machine. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
5. **Tensor parallelism is a latency argument for wafer-scale, and it is the sharpest one.** Two all-reduces per layer per token cost up to 189 us over NVLink, capping per-user decode at 5,296 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 12.2 us and cap it at 81,966 tok/s.
6. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 24 of 24 operating points and an array 0; on tokens per second per square millimetre the same points go 10 to the array and 14 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
7. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 324 of 1198 feasible points.
8. **The largest open question is not in this model's inputs but in the architecture, and the anchor cannot settle it.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 21.4x of aggregate throughput (DeepSeek-V4-Flash-0731). The machines are identical at batch 1, which is where the published anchor sits, so no amount of validation against it resolves the fork.
9. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 18.24x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 2.30x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 25 of 48 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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
| DeepSeek-V4-Flash-0731 | 200,000 | 284 B | 166.9 GB | 4.70 | 0.099 GB | 0.705 GB | 113.2 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1,600 B | 892.7 GB | 4.46 | 0.674 GB | 5.028 GB | 58.9 |

## Iso-area comparison

Two ROM designs per operating point -- the **fastest** and the
**smallest silicon that serves the point at all** -- each against the GPU
cluster of the closest equal silicon area. **The area is stated on both
sides.** Where one row appears, the two coincide.

| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | GPU user tok/s | GPU aggregate tok/s | GPU binds on | Per-user ratio | Aggregate ratio |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---:|
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-romfill | 46,225 | 48,259.1 | 48,259.1 | kv_read | Qwen3-8B/b200_sxm-x29 | 46,400 | 1.00x | 7,132.9 | 7,132.9 | weight_read | 6.77x | 6.77x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N5-fp8-SRAMKV-array-pipeline-x2 | 1,630 | 10,820.8 | 10,820.8 | weight_read | Qwen3-8B/b200_sxm-x1 | 1,600 | 1.02x | 415.0 | 415.0 | weight_read | 26.07x | 26.07x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 31,837.0 | 63,674.0 | kv_read | Qwen3-8B/b200_sxm-x116 | 185,600 | 1.00x | 4,874.1 | 9,748.2 | link_latency | 6.53x | 6.53x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 5,940.9 | 11,881.9 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | 693.8 | 1,387.5 | weight_read | 8.56x | 8.56x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 20,091.1 | 80,364.5 | kv_read | Qwen3-8B/b200_sxm-x116 | 185,600 | 1.00x | 4,746.9 | 18,987.7 | link_latency | 4.23x | 4.23x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 3,064.7 | 12,258.6 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | 610.2 | 2,440.7 | weight_read | 5.02x | 5.02x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 11,560.7 | 92,485.9 | kv_read | Qwen3-8B/b200_sxm-x116 | 185,600 | 1.00x | 4,511.5 | 36,091.8 | link_latency | 2.56x | 2.56x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 1,557.0 | 12,456.1 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | 491.7 | 3,933.7 | weight_read | 3.17x | 3.17x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 6,251.9 | 100,029.7 | kv_read | Qwen3-8B/b200_sxm-x116 | 185,600 | 1.00x | 4,104.3 | 65,669.4 | link_latency | 1.52x | 1.52x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 784.8 | 12,557.3 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | 354.2 | 5,667.0 | kv_read | 2.22x | 2.22x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 3,258.8 | 104,282.7 | kv_read | Qwen3-8B/b200_sxm-x116 | 185,600 | 1.00x | 3,476.8 | 111,257.6 | link_latency | 0.94x | 0.94x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 394.0 | 12,608.5 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | 227.1 | 7,268.2 | kv_read | 1.73x | 1.73x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 1,664.8 | 106,547.8 | kv_read | Qwen3-8B/b200_sxm-x116 | 185,600 | 1.00x | 2,662.6 | 170,406.3 | link_latency | 0.63x | 0.63x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 197.4 | 12,634.2 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | 132.2 | 8,463.9 | kv_read | 1.49x | 1.49x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 423.1 | 108,312.2 | kv_read | Qwen3-8B/b200_sxm-x116 | 185,600 | 1.00x | 1,107.1 | 283,409.6 | link_latency | 0.38x | 0.38x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 49.4 | 12,653.6 | kv_read | Qwen3-8B/b200_sxm-x2 | 3,200 | 1.02x | infeasible | — | capacity_or_format | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x4-romfill | 184,900 | 38,394.7 | 38,394.7 | layer_fixed_latency | DSV4-Flash/b200_sxm-x116 | 185,600 | 1.00x | 3,340.6 | 3,340.6 | link_latency | 11.49x | 11.49x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x14 | 11,410 | 8,745.2 | 8,745.2 | weight_read | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 2,501.2 | 2,501.2 | weight_read | 3.50x | 3.50x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 38,277.4 | 76,554.8 | layer_fixed_latency | DSV4-Flash/b200_sxm-x116 | 185,600 | 1.00x | 3,036.5 | 6,073.0 | link_latency | 12.61x | 12.61x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 4,958.9 | 9,917.7 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 1,897.1 | 3,794.2 | weight_read | 2.61x | 2.61x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 38,277.2 | 153,108.7 | layer_fixed_latency | DSV4-Flash/b200_sxm-x116 | 185,600 | 1.00x | 2,605.1 | 10,420.2 | weight_read | 14.69x | 14.69x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 2,672.8 | 10,691.0 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 1,338.5 | 5,354.1 | weight_read | 2.00x | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 38,276.7 | 306,213.8 | layer_fixed_latency | DSV4-Flash/b200_sxm-x116 | 185,600 | 1.00x | 2,233.4 | 17,867.5 | weight_read | 17.14x | 17.14x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 1,390.6 | 11,124.7 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 889.1 | 7,113.0 | weight_read | 1.56x | 1.56x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 29,468.1 | 471,490.3 | kv_read | DSV4-Flash/b200_sxm-x116 | 185,600 | 1.00x | 1,836.0 | 29,376.0 | weight_read | 16.05x | 16.05x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 709.7 | 11,355.0 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 573.1 | 9,169.4 | weight_read | 1.24x | 1.24x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 20,162.0 | 645,184.4 | kv_read | DSV4-Flash/b200_sxm-x116 | 185,600 | 1.00x | 1,487.8 | 47,610.2 | weight_read | 13.55x | 13.55x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 358.6 | 11,473.8 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 376.6 | 12,050.0 | weight_read | 0.95x | 0.95x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 12,357.2 | 790,858.0 | kv_read | DSV4-Flash/b200_sxm-x116 | 185,600 | 1.00x | 1,219.2 | 78,026.4 | weight_read | 10.14x | 10.14x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 180.2 | 11,534.1 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 268.9 | 17,209.1 | weight_read | 0.67x | 0.67x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 3,719.1 | 952,083.4 | kv_read | DSV4-Flash/b200_sxm-x116 | 185,600 | 1.00x | 874.6 | 223,903.0 | weight_read | 4.25x | 4.25x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 45.2 | 11,579.8 | compute | DSV4-Flash/b200_sxm-x7 | 11,200 | 1.02x | 194.8 | 49,865.5 | weight_read | 0.23x | 0.23x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x8-romfill | 369,800 | 21,365.7 | 21,365.7 | weight_read | DSV4-Pro/b200_sxm-x231 | 369,600 | 1.00x | 1,328.3 | 1,328.3 | weight_read | 16.08x | 16.08x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x72 | 58,680 | 4,844.1 | 4,844.1 | link_latency | DSV4-Pro/b200_sxm-x37 | 59,200 | 0.99x | 1,527.0 | 1,527.0 | weight_read | 3.17x | 3.17x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 21,297.8 | 42,595.7 | weight_read | DSV4-Pro/b200_sxm-x231 | 369,600 | 1.00x | 1,217.8 | 2,435.6 | weight_read | 17.49x | 17.49x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 3,256.8 | 6,513.7 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 1,168.7 | 2,337.4 | weight_read | 2.79x | 2.79x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 21,297.6 | 85,190.6 | weight_read | DSV4-Pro/b200_sxm-x231 | 369,600 | 1.00x | 1,013.8 | 4,055.1 | weight_read | 21.01x | 21.01x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 2,043.5 | 8,174.2 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 871.5 | 3,486.0 | weight_read | 2.34x | 2.34x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 18,926.3 | 151,410.4 | kv_read | DSV4-Pro/b200_sxm-x231 | 369,600 | 1.00x | 845.4 | 6,763.3 | weight_read | 22.39x | 22.39x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 1,171.0 | 9,368.3 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 621.6 | 4,973.1 | weight_read | 1.88x | 1.88x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 12,543.0 | 200,687.5 | kv_read | DSV4-Pro/b200_sxm-x231 | 369,600 | 1.00x | 685.5 | 10,968.0 | weight_read | 18.30x | 18.30x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 631.7 | 10,106.5 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 430.4 | 6,887.0 | weight_read | 1.47x | 1.47x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 7,490.4 | 239,691.7 | kv_read | DSV4-Pro/b200_sxm-x231 | 369,600 | 1.00x | 543.7 | 17,399.2 | weight_read | 13.78x | 13.78x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 328.8 | 10,521.0 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 295.7 | 9,461.2 | weight_read | 1.11x | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 4,148.3 | 265,491.2 | kv_read | DSV4-Pro/b200_sxm-x231 | 369,600 | 1.00x | 427.2 | 27,340.5 | weight_read | 9.71x | 9.71x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 167.8 | 10,741.3 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 209.8 | 13,424.9 | weight_read | 0.80x | 0.80x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 1,128.1 | 288,805.7 | kv_read | DSV4-Pro/b200_sxm-x231 | 369,600 | 1.00x | 276.0 | 70,667.1 | weight_read | 4.09x | 4.09x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x75 | 61,125 | 42.6 | 10,912.7 | compute | DSV4-Pro/b200_sxm-x38 | 60,800 | 1.01x | 137.0 | 35,076.7 | weight_read | 0.31x | 0.31x |

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
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-romfill | 46,225 | 48,259.1 | 1.044 | 35,542.3 (5,705) | 48,259.1 (46,225) | 1.36x | kv_read |
| Qwen3-8B | 2 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 31,837.0 | 0.172 | 13,300.0 (9,780) | 31,837.0 (184,900) | 2.39x | kv_read |
| Qwen3-8B | 4 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 20,091.1 | 0.109 | 7,810.7 (9,780) | 20,091.1 (184,900) | 2.57x | kv_read |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 11,560.7 | 0.063 | 4,278.8 (9,780) | 11,560.7 (184,900) | 2.70x | kv_read |
| Qwen3-8B | 16 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 6,251.9 | 0.034 | 2,246.8 (9,780) | 6,251.9 (184,900) | 2.78x | kv_read |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 3,258.8 | 0.018 | 1,152.3 (9,780) | 3,258.8 (184,900) | 2.83x | kv_read |
| Qwen3-8B | 64 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 1,664.8 | 0.009 | 630.0 (12,225) | 1,664.8 (184,900) | 2.64x | kv_read |
| Qwen3-8B | 256 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 423.1 | 0.002 | 166.5 (12,225) | 423.1 (184,900) | 2.54x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x4-romfill | 184,900 | 38,394.7 | 0.208 | 8,745.2 (11,410) | 38,394.7 (184,900) | 4.39x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 38,277.4 | 0.207 | 5,463.5 (39,120) | 38,277.4 (184,900) | 7.01x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 38,277.2 | 0.207 | 5,326.8 (39,120) | 38,277.2 (184,900) | 7.19x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 38,276.7 | 0.207 | 5,073.0 (39,120) | 38,276.7 (184,900) | 7.55x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 29,468.1 | 0.159 | 4,041.1 (39,120) | 29,468.1 (184,900) | 7.29x | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 20,162.0 | 0.109 | 2,807.1 (39,120) | 20,162.0 (184,900) | 7.18x | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 12,357.2 | 0.067 | 1,742.7 (39,120) | 12,357.2 (184,900) | 7.09x | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 3,719.1 | 0.020 | 532.1 (39,120) | 3,719.1 (184,900) | 6.99x | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x8-romfill | 369,800 | 21,365.7 | 0.058 | 4,844.1 (58,680) | 21,365.7 (369,800) | 4.41x | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 21,297.8 | 0.058 | 3,256.8 (61,125) | 21,297.8 (369,800) | 6.54x | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 21,297.6 | 0.058 | 2,043.5 (61,125) | 21,297.6 (369,800) | 10.42x | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 18,926.3 | 0.051 | 1,171.0 (61,125) | 18,926.3 (369,800) | 16.16x | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 12,543.0 | 0.034 | 631.7 (61,125) | 12,543.0 (369,800) | 19.86x | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 7,490.4 | 0.020 | 328.8 (61,125) | 7,490.4 (369,800) | 22.78x | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 4,148.3 | 0.011 | 167.8 (61,125) | 4,148.3 (369,800) | 24.72x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 1,128.1 | 0.003 | 42.6 (61,125) | 1,128.1 (369,800) | 26.47x | kv_read |

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
| Qwen3-8B | 1 | sram | 11,363.7 | 11,363.7 | 11,363.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 22,727.3 | 12,154.2 | 12,154.2 | 1.87x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 27,843.3 | 12,592.1 | 12,592.1 | 2.21x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 28,998.6 | 12,823.2 | 12,823.2 | 2.26x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 29,613.0 | 12,941.9 | 12,941.9 | 2.29x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 29,930.0 | 13,002.1 | 13,002.1 | 2.30x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 30,091.1 | 13,032.4 | 13,032.4 | 2.31x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 30,213.1 | 13,055.2 | 13,055.2 | 2.31x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 48,259.1 | 48,259.1 | 48,259.1 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 63,674.0 | 63,674.0 | 63,674.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 80,364.5 | 80,364.5 | 80,364.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 92,485.9 | 92,485.9 | 92,485.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 100,029.7 | 100,029.7 | 100,029.7 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 104,282.7 | 104,282.7 | 104,282.7 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 106,547.8 | 106,547.8 | 106,547.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 108,312.2 | 108,312.2 | 108,312.2 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 10,890.3 | 10,890.3 | 10,890.3 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 21,780.6 | 11,878.1 | 19,633.0 | 1.83x | 1.65x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 43,561.3 | 12,442.3 | 29,495.0 | 3.50x | 2.37x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 87,122.5 | 12,745.0 | 44,793.0 | 6.84x | 3.51x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 174,244.7 | 12,902.0 | 67,796.2 | 13.51x | 5.25x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 249,924.5 | 12,981.9 | 98,924.5 | 19.25x | 7.62x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 265,774.5 | 13,022.3 | 138,630.5 | 20.41x | 10.65x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 279,047.2 | 13,052.7 | 238,120.7 | 21.38x | 18.24x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 38,394.7 | 38,985.4 | 38,985.4 | 0.98x | 1.00x | layer_fixed_latency | layer_fixed_latency | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | rom | 76,554.8 | 60,268.6 | 74,887.6 | 1.27x | 1.24x | layer_fixed_latency | weight_read | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | rom | 153,108.7 | 83,163.7 | 133,360.6 | 1.84x | 1.60x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 306,213.8 | 102,664.0 | 234,048.9 | 2.98x | 2.28x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 471,490.3 | 116,298.9 | 402,286.7 | 4.05x | 3.46x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 645,184.4 | 124,571.1 | 645,184.4 | 5.18x | 5.18x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 790,858.0 | 129,164.8 | 790,858.0 | 6.12x | 6.12x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 952,083.4 | 132,838.7 | 952,083.4 | 7.17x | 7.17x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 9,082.2 | 9,082.2 | 9,082.2 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 18,164.3 | 10,247.7 | 16,989.7 | 1.77x | 1.66x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 36,328.6 | 10,950.4 | 27,276.9 | 3.32x | 2.49x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 60,332.3 | 11,339.2 | 41,139.8 | 5.32x | 3.63x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 66,624.7 | 11,544.1 | 66,307.1 | 5.77x | 5.74x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 70,290.3 | 11,649.4 | 70,290.3 | 6.03x | 6.03x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 72,278.6 | 11,702.7 | 89,249.0 | 6.18x | 7.63x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 73,845.2 | 11,743.1 | 162,363.9 | 6.29x | 13.83x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 21,365.7 | 21,859.5 | 21,859.5 | 0.98x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 42,595.7 | 30,378.3 | 41,949.1 | 1.40x | 1.38x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 85,190.6 | 37,833.8 | 73,448.7 | 2.25x | 1.94x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 151,410.4 | 43,125.7 | 121,817.6 | 3.51x | 2.82x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 200,687.5 | 46,368.6 | 200,687.5 | 4.33x | 4.33x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 239,691.7 | 48,180.0 | 239,691.7 | 4.97x | 4.97x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 265,491.2 | 49,139.9 | 265,491.2 | 5.40x | 5.40x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 288,805.7 | 49,885.3 | 288,805.7 | 5.79x | 5.79x | kv_read | weight_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 11,363.7 | 0.246 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-romfill | 46,225 | 27.67 | 1.00 | 48,259.1 | 1.044 | kv_read | 4.25x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 11,363.7 | 0.246 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.15 | 1.00 | 48,259.1 | 1.044 | kv_read | 4.25x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 11,363.7 | 0.246 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.15 | 1.00 | 48,259.1 | 1.044 | kv_read | 4.25x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 22,727.3 | 0.492 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 110.34 | 1.00 | 63,674.0 | 0.344 | kv_read | 2.80x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 2.00 | 12,154.2 | 0.263 | weight_read | 0.53x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 116.21 | 2.00 | 63,674.0 | 0.344 | kv_read | 2.80x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 2.00 | 12,154.2 | 0.263 | weight_read | 0.53x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 116.21 | 2.00 | 63,674.0 | 0.344 | kv_read | 2.80x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 27,843.3 | 0.602 | kv_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 110.34 | 1.00 | 80,364.5 | 0.435 | kv_read | 2.89x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.00 | 12,592.1 | 0.272 | weight_read | 0.45x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 116.21 | 4.00 | 80,364.5 | 0.435 | kv_read | 2.89x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.00 | 12,592.1 | 0.272 | weight_read | 0.45x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 116.21 | 4.00 | 80,364.5 | 0.435 | kv_read | 2.89x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,998.6 | 0.627 | kv_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 110.34 | 1.00 | 92,485.9 | 0.500 | kv_read | 3.19x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 8.00 | 12,823.2 | 0.277 | weight_read | 0.44x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 116.21 | 8.00 | 92,485.9 | 0.500 | kv_read | 3.19x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 8.00 | 12,823.2 | 0.277 | weight_read | 0.44x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 116.21 | 8.00 | 92,485.9 | 0.500 | kv_read | 3.19x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 29,613.0 | 0.641 | kv_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 110.34 | 1.00 | 100,029.7 | 0.541 | kv_read | 3.38x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 16.00 | 12,941.9 | 0.280 | weight_read | 0.44x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 116.21 | 16.00 | 100,029.7 | 0.541 | kv_read | 3.38x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 16.00 | 12,941.9 | 0.280 | weight_read | 0.44x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 116.21 | 16.00 | 100,029.7 | 0.541 | kv_read | 3.38x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 29,930.0 | 0.647 | kv_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 110.34 | 1.00 | 104,282.7 | 0.564 | kv_read | 3.48x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 32.00 | 13,002.1 | 0.281 | weight_read | 0.43x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 116.21 | 32.00 | 104,282.7 | 0.564 | kv_read | 3.48x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 32.00 | 13,002.1 | 0.281 | weight_read | 0.43x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 116.21 | 32.00 | 104,282.7 | 0.564 | kv_read | 3.48x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 30,091.1 | 0.651 | kv_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 110.34 | 1.00 | 106,547.8 | 0.576 | kv_read | 3.54x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 64.00 | 13,032.4 | 0.282 | weight_read | 0.43x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 116.21 | 64.00 | 106,547.8 | 0.576 | kv_read | 3.54x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 64.00 | 13,032.4 | 0.282 | weight_read | 0.43x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 116.21 | 64.00 | 106,547.8 | 0.576 | kv_read | 3.54x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 30,213.1 | 0.654 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 110.34 | 1.00 | 108,312.2 | 0.586 | kv_read | 3.58x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 256.00 | 13,055.2 | 0.282 | weight_read | 0.43x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 116.21 | 256.00 | 108,312.2 | 0.586 | kv_read | 3.58x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 256.00 | 13,055.2 | 0.282 | weight_read | 0.43x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 116.21 | 256.00 | 108,312.2 | 0.586 | kv_read | 3.58x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 10,890.3 | 0.236 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x4-romfill | 184,900 | 10.94 | 1.00 | 38,394.7 | 0.208 | layer_fixed_latency | 3.53x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 10,890.3 | 0.236 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 11.53 | 1.00 | 38,985.4 | 0.211 | layer_fixed_latency | 3.58x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 10,890.3 | 0.236 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 11.53 | 1.00 | 38,985.4 | 0.211 | layer_fixed_latency | 3.58x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 21,780.6 | 0.471 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 10.83 | 1.00 | 76,554.8 | 0.414 | layer_fixed_latency | 3.51x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 2.00 | 11,878.1 | 0.257 | weight_read | 0.55x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 11.41 | 2.00 | 60,268.6 | 0.326 | weight_read | 2.77x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.13 | 19,633.0 | 0.425 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 11.41 | 1.13 | 74,887.6 | 0.405 | layer_fixed_latency | 3.44x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 43,561.3 | 0.942 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 10.83 | 1.00 | 153,108.7 | 0.828 | layer_fixed_latency | 3.51x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.00 | 12,442.3 | 0.269 | weight_read | 0.29x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 11.41 | 4.00 | 83,163.7 | 0.450 | weight_read | 1.91x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.57 | 29,495.0 | 0.638 | weight_read | 0.68x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 11.41 | 1.57 | 133,360.6 | 0.721 | weight_read | 3.06x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 87,122.5 | 1.885 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 10.83 | 1.00 | 306,213.8 | 1.656 | layer_fixed_latency | 3.51x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 8.00 | 12,745.0 | 0.276 | weight_read | 0.15x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 11.41 | 8.00 | 102,664.0 | 0.555 | weight_read | 1.18x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 2.13 | 44,793.0 | 0.969 | weight_read | 0.51x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 11.41 | 2.13 | 234,048.9 | 1.266 | weight_read | 2.69x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 174,244.7 | 3.769 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 10.83 | 1.00 | 471,490.3 | 2.550 | kv_read | 2.71x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 16.00 | 12,902.0 | 0.279 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 11.41 | 16.00 | 116,298.9 | 0.629 | weight_read | 0.67x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 2.88 | 67,796.2 | 1.467 | weight_read | 0.39x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 11.41 | 2.88 | 402,286.7 | 2.176 | weight_read | 2.31x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 249,924.5 | 5.407 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 10.83 | 1.00 | 645,184.4 | 3.489 | kv_read | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 32.00 | 12,981.9 | 0.281 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 11.41 | 32.00 | 124,571.1 | 0.674 | weight_read | 0.50x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.03 | 98,924.5 | 2.140 | weight_read | 0.40x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 11.41 | 4.03 | 645,184.4 | 3.489 | kv_read | 2.58x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 265,774.5 | 5.750 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 10.83 | 1.00 | 790,858.0 | 4.277 | kv_read | 2.98x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 64.00 | 13,022.3 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 11.41 | 64.00 | 129,164.8 | 0.699 | weight_read | 0.49x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 5.83 | 138,630.5 | 2.999 | weight_read | 0.52x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 11.41 | 5.83 | 790,858.0 | 4.277 | kv_read | 2.98x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 279,047.2 | 6.037 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-romfill | 184,900 | 10.83 | 1.00 | 952,083.4 | 5.149 | kv_read | 3.41x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 256.00 | 13,052.7 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perstream-romfill | 184,900 | 11.41 | 256.00 | 132,838.7 | 0.718 | weight_read | 0.48x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 13.84 | 238,120.7 | 5.151 | weight_read | 0.85x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 11.41 | 13.84 | 952,083.4 | 5.149 | kv_read | 3.41x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 9,082.2 | 0.098 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x8-romfill | 369,800 | 4.08 | 1.00 | 21,365.7 | 0.058 | weight_read | 2.35x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 9,082.2 | 0.098 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x8-perstream-romfill | 369,800 | 4.30 | 1.00 | 21,859.5 | 0.059 | weight_read | 2.41x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 9,082.2 | 0.098 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x8-perregion-romfill | 369,800 | 4.30 | 1.00 | 21,859.5 | 0.059 | weight_read | 2.41x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 18,164.3 | 0.196 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 4.05 | 1.00 | 42,595.7 | 0.115 | weight_read | 2.35x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 2.00 | 10,247.7 | 0.111 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perstream-romfill | 369,800 | 4.26 | 2.00 | 30,378.3 | 0.082 | weight_read | 1.67x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.09 | 16,989.7 | 0.184 | weight_read | 0.94x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perregion-romfill | 369,800 | 4.26 | 1.09 | 41,949.1 | 0.113 | weight_read | 2.31x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 36,328.6 | 0.393 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 4.05 | 1.00 | 85,190.6 | 0.230 | weight_read | 2.35x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 4.00 | 10,950.4 | 0.118 | weight_read | 0.30x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perstream-romfill | 369,800 | 4.26 | 4.00 | 37,833.8 | 0.102 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.43 | 27,276.9 | 0.295 | weight_read | 0.75x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perregion-romfill | 369,800 | 4.26 | 1.43 | 73,448.7 | 0.199 | weight_read | 2.02x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 60,332.3 | 0.653 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 4.05 | 1.00 | 151,410.4 | 0.409 | kv_read | 2.51x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 8.00 | 11,339.2 | 0.123 | weight_read | 0.19x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perstream-romfill | 369,800 | 4.26 | 8.00 | 43,125.7 | 0.117 | weight_read | 0.71x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.99 | 41,139.8 | 0.445 | weight_read | 0.68x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perregion-romfill | 369,800 | 4.26 | 1.99 | 121,817.6 | 0.329 | weight_read | 2.02x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 66,624.7 | 0.721 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 4.05 | 1.00 | 200,687.5 | 0.543 | kv_read | 3.01x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 16.00 | 11,544.1 | 0.125 | weight_read | 0.17x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perstream-romfill | 369,800 | 4.26 | 16.00 | 46,368.6 | 0.125 | weight_read | 0.70x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 2.54 | 66,307.1 | 0.717 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perregion-romfill | 369,800 | 4.26 | 2.54 | 200,687.5 | 0.543 | kv_read | 3.01x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 70,290.3 | 0.760 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 4.05 | 1.00 | 239,691.7 | 0.648 | kv_read | 3.41x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 32.00 | 11,649.4 | 0.126 | weight_read | 0.17x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perstream-romfill | 369,800 | 4.26 | 32.00 | 48,180.0 | 0.130 | weight_read | 0.69x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 3.49 | 70,290.3 | 0.760 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perregion-romfill | 369,800 | 4.26 | 3.49 | 239,691.7 | 0.648 | kv_read | 3.41x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 72,278.6 | 0.782 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 4.05 | 1.00 | 265,491.2 | 0.718 | kv_read | 3.67x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 64.00 | 11,702.7 | 0.127 | weight_read | 0.16x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perstream-romfill | 369,800 | 4.26 | 64.00 | 49,139.9 | 0.133 | weight_read | 0.68x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x114-perregion | 92,910 | 1.00 | 4.92 | 89,249.0 | 0.961 | weight_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perregion-romfill | 369,800 | 4.26 | 4.92 | 265,491.2 | 0.718 | kv_read | 3.67x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2 | 92,450 | 1.00 | 1.00 | 73,845.2 | 0.799 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-romfill | 369,800 | 4.05 | 1.00 | 288,805.7 | 0.781 | kv_read | 3.91x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 256.00 | 11,743.1 | 0.127 | weight_read | 0.16x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perstream-romfill | 369,800 | 4.26 | 256.00 | 49,885.3 | 0.135 | weight_read | 0.68x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x114-perregion | 92,910 | 1.00 | 10.96 | 162,363.9 | 1.748 | weight_read | 2.20x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x8-perregion-romfill | 369,800 | 4.26 | 10.96 | 288,805.7 | 0.781 | kv_read | 3.91x |

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
| DeepSeek-V4-Flash-0731 | 1 | 3 | 2.74 | 2.02 | 1.35x |
| DeepSeek-V4-Flash-0731 | 2 | 3 | 2.98 | 2.23 | 1.34x |
| DeepSeek-V4-Flash-0731 | 4 | 3 | 3.00 | 2.40 | 1.25x |
| DeepSeek-V4-Flash-0731 | 8 | 3 | 3.00 | 2.54 | 1.18x |
| DeepSeek-V4-Flash-0731 | 16 | 3 | 3.00 | 2.65 | 1.13x |
| DeepSeek-V4-Flash-0731 | 32 | 3 | 3.00 | 2.72 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 3 | 3.00 | 2.77 | 1.08x |
| DeepSeek-V4-Flash-0731 | 256 | 3 | 3.00 | 2.79 | 1.08x |
| DeepSeek-V4-Flash-0731 | 1 | 7 | 4.22 | 2.86 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 7 | 5.88 | 3.47 | 1.69x |
| DeepSeek-V4-Flash-0731 | 4 | 7 | 6.80 | 4.07 | 1.67x |
| DeepSeek-V4-Flash-0731 | 8 | 7 | 6.99 | 4.62 | 1.51x |
| DeepSeek-V4-Flash-0731 | 16 | 7 | 7.00 | 5.08 | 1.38x |
| DeepSeek-V4-Flash-0731 | 32 | 7 | 7.00 | 5.42 | 1.29x |
| DeepSeek-V4-Flash-0731 | 64 | 7 | 7.00 | 5.65 | 1.24x |
| DeepSeek-V4-Flash-0731 | 256 | 7 | 7.00 | 5.78 | 1.21x |
| DeepSeek-V4-Flash-0731 | 1 | 10 | 4.69 | 3.22 | 1.45x |
| DeepSeek-V4-Flash-0731 | 2 | 10 | 7.13 | 4.05 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 10 | 9.13 | 4.92 | 1.86x |
| DeepSeek-V4-Flash-0731 | 8 | 10 | 9.91 | 5.76 | 1.72x |
| DeepSeek-V4-Flash-0731 | 16 | 10 | 10.00 | 6.50 | 1.54x |
| DeepSeek-V4-Flash-0731 | 32 | 10 | 10.00 | 7.09 | 1.41x |
| DeepSeek-V4-Flash-0731 | 64 | 10 | 10.00 | 7.48 | 1.34x |
| DeepSeek-V4-Flash-0731 | 256 | 10 | 10.00 | 7.71 | 1.30x |
| DeepSeek-V4-Flash-0731 | 1 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 2 | 11 | 7.45 | 4.21 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 11 | 9.79 | 5.16 | 1.90x |
| DeepSeek-V4-Flash-0731 | 8 | 11 | 10.84 | 6.09 | 1.78x |
| DeepSeek-V4-Flash-0731 | 16 | 11 | 11.00 | 6.93 | 1.59x |
| DeepSeek-V4-Flash-0731 | 32 | 11 | 11.00 | 7.60 | 1.45x |
| DeepSeek-V4-Flash-0731 | 64 | 11 | 11.00 | 8.04 | 1.37x |
| DeepSeek-V4-Flash-0731 | 256 | 11 | 11.00 | 8.31 | 1.32x |
| DeepSeek-V4-Flash-0731 | 1 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Flash-0731 | 2 | 14 | 8.19 | 4.61 | 1.78x |
| DeepSeek-V4-Flash-0731 | 4 | 14 | 11.49 | 5.79 | 1.98x |
| DeepSeek-V4-Flash-0731 | 8 | 14 | 13.47 | 6.99 | 1.93x |
| DeepSeek-V4-Flash-0731 | 16 | 14 | 13.96 | 8.09 | 1.73x |
| DeepSeek-V4-Flash-0731 | 32 | 14 | 14.00 | 9.00 | 1.55x |
| DeepSeek-V4-Flash-0731 | 64 | 14 | 14.00 | 9.63 | 1.45x |
| DeepSeek-V4-Flash-0731 | 256 | 14 | 14.00 | 10.00 | 1.40x |
| DeepSeek-V4-Flash-0731 | 1 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 2 | 15 | 8.38 | 4.73 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 15 | 11.97 | 5.97 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 15 | 14.29 | 7.25 | 1.97x |
| DeepSeek-V4-Flash-0731 | 16 | 15 | 14.94 | 8.45 | 1.77x |
| DeepSeek-V4-Flash-0731 | 32 | 15 | 15.00 | 9.44 | 1.59x |
| DeepSeek-V4-Flash-0731 | 64 | 15 | 15.00 | 10.12 | 1.48x |
| DeepSeek-V4-Flash-0731 | 256 | 15 | 15.00 | 10.53 | 1.42x |
| DeepSeek-V4-Flash-0731 | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4-Flash-0731 | 2 | 24 | 9.51 | 5.51 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 24 | 15.05 | 7.28 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 24 | 20.35 | 9.21 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 24 | 23.23 | 11.14 | 2.09x |
| DeepSeek-V4-Flash-0731 | 32 | 24 | 23.93 | 12.82 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 24 | 24.00 | 14.03 | 1.71x |
| DeepSeek-V4-Flash-0731 | 256 | 24 | 24.00 | 14.78 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 9.87 | 5.82 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 16.14 | 7.83 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 22.86 | 10.06 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 27.30 | 12.35 | 2.21x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 28.76 | 14.39 | 2.00x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 28.97 | 15.88 | 1.82x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 1 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4-Flash-0731 | 2 | 36 | 10.22 | 6.19 | 1.65x |
| DeepSeek-V4-Flash-0731 | 4 | 36 | 17.26 | 8.47 | 2.04x |
| DeepSeek-V4-Flash-0731 | 8 | 36 | 25.65 | 11.07 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 36 | 32.31 | 13.81 | 2.34x |
| DeepSeek-V4-Flash-0731 | 32 | 36 | 35.22 | 16.32 | 2.16x |
| DeepSeek-V4-Flash-0731 | 64 | 36 | 35.87 | 18.20 | 1.97x |
| DeepSeek-V4-Flash-0731 | 256 | 36 | 35.97 | 19.38 | 1.86x |
| DeepSeek-V4-Flash-0731 | 1 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 2 | 39 | 10.34 | 6.32 | 1.64x |
| DeepSeek-V4-Flash-0731 | 4 | 39 | 17.64 | 8.71 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 39 | 26.64 | 11.45 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 39 | 34.22 | 14.37 | 2.38x |
| DeepSeek-V4-Flash-0731 | 32 | 39 | 37.86 | 17.07 | 2.22x |
| DeepSeek-V4-Flash-0731 | 64 | 39 | 38.78 | 19.11 | 2.03x |
| DeepSeek-V4-Flash-0731 | 256 | 39 | 38.95 | 20.40 | 1.91x |
| DeepSeek-V4-Flash-0731 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 58 | 10.81 | 7.02 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4 | 58 | 19.24 | 9.86 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 58 | 31.13 | 13.37 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 58 | 43.78 | 17.30 | 2.53x |
| DeepSeek-V4-Flash-0731 | 32 | 58 | 52.57 | 21.09 | 2.49x |
| DeepSeek-V4-Flash-0731 | 64 | 58 | 56.21 | 24.04 | 2.34x |
| DeepSeek-V4-Flash-0731 | 256 | 58 | 57.32 | 25.97 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 116 | 11.32 | 8.33 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 116 | 21.08 | 11.71 | 1.80x |
| DeepSeek-V4-Flash-0731 | 8 | 116 | 36.91 | 16.98 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 116 | 58.39 | 22.88 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 116 | 80.31 | 29.09 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 116 | 95.45 | 34.23 | 2.79x |
| DeepSeek-V4-Flash-0731 | 256 | 116 | 103.29 | 37.73 | 2.74x |
| DeepSeek-V4-Pro-0813 | 1 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Pro-0813 | 2 | 14 | 8.21 | 4.62 | 1.78x |
| DeepSeek-V4-Pro-0813 | 4 | 14 | 11.54 | 5.81 | 1.99x |
| DeepSeek-V4-Pro-0813 | 8 | 14 | 13.52 | 7.04 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 14 | 13.98 | 8.20 | 1.71x |
| DeepSeek-V4-Pro-0813 | 32 | 14 | 14.00 | 9.19 | 1.52x |
| DeepSeek-V4-Pro-0813 | 64 | 14 | 14.00 | 9.93 | 1.41x |
| DeepSeek-V4-Pro-0813 | 256 | 14 | 14.00 | 10.55 | 1.33x |
| DeepSeek-V4-Pro-0813 | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 2 | 37 | 10.30 | 6.24 | 1.65x |
| DeepSeek-V4-Pro-0813 | 4 | 37 | 17.54 | 8.59 | 2.04x |
| DeepSeek-V4-Pro-0813 | 8 | 37 | 26.35 | 11.32 | 2.33x |
| DeepSeek-V4-Pro-0813 | 16 | 37 | 33.45 | 14.27 | 2.34x |
| DeepSeek-V4-Pro-0813 | 32 | 37 | 36.43 | 17.13 | 2.13x |
| DeepSeek-V4-Pro-0813 | 64 | 37 | 36.95 | 19.50 | 1.90x |
| DeepSeek-V4-Pro-0813 | 256 | 37 | 37.00 | 21.63 | 1.71x |
| DeepSeek-V4-Pro-0813 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 2 | 38 | 10.34 | 6.29 | 1.64x |
| DeepSeek-V4-Pro-0813 | 4 | 38 | 17.66 | 8.67 | 2.04x |
| DeepSeek-V4-Pro-0813 | 8 | 38 | 26.69 | 11.45 | 2.33x |
| DeepSeek-V4-Pro-0813 | 16 | 38 | 34.12 | 14.46 | 2.36x |
| DeepSeek-V4-Pro-0813 | 32 | 38 | 37.34 | 17.39 | 2.15x |
| DeepSeek-V4-Pro-0813 | 64 | 38 | 37.94 | 19.83 | 1.91x |
| DeepSeek-V4-Pro-0813 | 256 | 38 | 38.00 | 22.03 | 1.72x |
| DeepSeek-V4-Pro-0813 | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 55 | 10.79 | 6.94 | 1.56x |
| DeepSeek-V4-Pro-0813 | 4 | 55 | 19.23 | 9.76 | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | 55 | 31.11 | 13.27 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 55 | 43.55 | 17.27 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 55 | 51.62 | 21.32 | 2.42x |
| DeepSeek-V4-Pro-0813 | 64 | 55 | 54.37 | 24.83 | 2.19x |
| DeepSeek-V4-Pro-0813 | 256 | 55 | 54.95 | 28.10 | 1.96x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4-Pro-0813 | 1 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 144 | 11.47 | 8.75 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 144 | 21.70 | 12.39 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 144 | 39.10 | 18.38 | 2.13x |
| DeepSeek-V4-Pro-0813 | 16 | 144 | 64.66 | 25.37 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 144 | 94.08 | 33.43 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 144 | 117.67 | 41.09 | 2.86x |
| DeepSeek-V4-Pro-0813 | 256 | 144 | 133.60 | 48.85 | 2.73x |
| DeepSeek-V4-Pro-0813 | 1 | 170 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 170 | 11.53 | 9.05 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 170 | 21.96 | 12.88 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 170 | 39.99 | 19.23 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 170 | 67.36 | 26.78 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 170 | 100.66 | 35.70 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 170 | 129.67 | 44.29 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 170 | 151.63 | 53.12 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1 | 172 | 5.91 | 5.55 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 172 | 11.54 | 9.08 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 172 | 21.98 | 12.92 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 172 | 40.05 | 19.28 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 172 | 67.54 | 26.88 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 172 | 101.11 | 35.87 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 172 | 130.50 | 44.52 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 172 | 152.93 | 53.43 | 2.86x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 186.03 | 61.46 | 3.03x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 4.3% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 2.3% |
| gpu | Qwen3-8B | 1 | 5.85 | 4.2% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 37.7% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 30.1% |
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
| Qwen3-8B | 1 | 3 | 44.74% | 4.15 | 9.27 |
| Qwen3-8B | 2 | 3 | 89.47% | 8.30 | 9.27 |
| Qwen3-8B | 4 | 1 | 3.50% | 0.32 | 9.27 |
| Qwen3-8B | 8 | 1 | 6.99% | 0.65 | 9.27 |
| Qwen3-8B | 16 | 1 | 13.98% | 1.30 | 9.27 |
| Qwen3-8B | 32 | 1 | 27.97% | 2.59 | 9.27 |
| Qwen3-8B | 64 | 1 | 55.94% | 5.19 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 20 | 81.44% | 1.74 | 2.14 |
| DeepSeek-V4-Flash-0731 | 2 | 1 | 1.51% | 0.03 | 2.14 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 3.02% | 0.06 | 2.14 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 6.03% | 0.13 | 2.14 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 12.07% | 0.26 | 2.14 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 24.13% | 0.52 | 2.14 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 48.26% | 1.03 | 2.14 |
| DeepSeek-V4-Pro-0813 | 1 | 108 | 70.08% | 1.45 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 48.15% | 1.00 | 2.08 |
| DeepSeek-V4-Pro-0813 | 4 | 2 | 96.29% | 2.00 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 10,478.6 | 10,478.6 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 5,940.9 | 11,881.9 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 3,064.7 | 12,258.6 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,557.0 | 12,456.1 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 784.8 | 12,557.3 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 394.0 | 12,608.5 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 197.4 | 12,634.2 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 49.4 | 12,653.6 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 8,664.4 | 8,664.4 |
| DeepSeek-V4-Flash-0731 | 2 | 4.63% | 14.6 GB | 8.74% | 190.54 TB/s | 2,179.91 TB/s | 4,958.9 | 9,917.7 |
| DeepSeek-V4-Flash-0731 | 4 | 9.05% | 21.1 GB | 12.64% | 275.47 TB/s | 2,179.91 TB/s | 2,672.8 | 10,691.0 |
| DeepSeek-V4-Flash-0731 | 8 | 17.28% | 33.2 GB | 19.90% | 433.71 TB/s | 2,179.91 TB/s | 1,390.6 | 11,124.7 |
| DeepSeek-V4-Flash-0731 | 16 | 31.58% | 54.2 GB | 32.50% | 708.53 TB/s | 2,179.91 TB/s | 709.7 | 11,355.0 |
| DeepSeek-V4-Flash-0731 | 32 | 53.18% | 86.0 GB | 51.56% | 1,123.90 TB/s | 2,179.91 TB/s | 358.6 | 11,473.8 |
| DeepSeek-V4-Flash-0731 | 64 | 78.08% | 122.7 GB | 73.52% | 1,602.57 TB/s | 2,179.91 TB/s | 180.2 | 11,534.1 |
| DeepSeek-V4-Flash-0731 | 256 | 99.77% | 154.6 GB | 92.64% | 2,019.50 TB/s | 2,179.91 TB/s | 45.2 | 11,579.8 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 4,631.8 | 4,631.8 |
| DeepSeek-V4-Pro-0813 | 2 | 3.10% | 52.3 GB | 5.86% | 683.32 TB/s | 11,661.57 TB/s | 3,256.8 | 6,513.7 |
| DeepSeek-V4-Pro-0813 | 4 | 6.11% | 77.0 GB | 8.63% | 1,005.95 TB/s | 11,661.57 TB/s | 2,043.5 | 8,174.2 |
| DeepSeek-V4-Pro-0813 | 8 | 11.84% | 124.1 GB | 13.90% | 1,621.51 TB/s | 11,661.57 TB/s | 1,171.0 | 9,368.3 |
| DeepSeek-V4-Pro-0813 | 16 | 22.27% | 209.9 GB | 23.51% | 2,742.18 TB/s | 11,661.57 TB/s | 631.7 | 10,106.5 |
| DeepSeek-V4-Pro-0813 | 32 | 39.59% | 352.2 GB | 39.46% | 4,601.25 TB/s | 11,661.57 TB/s | 328.8 | 10,521.0 |
| DeepSeek-V4-Pro-0813 | 64 | 63.50% | 548.8 GB | 61.48% | 7,169.39 TB/s | 11,661.57 TB/s | 167.8 | 10,741.3 |
| DeepSeek-V4-Pro-0813 | 256 | 98.23% | 834.3 GB | 93.45% | 10,898.18 TB/s | 11,661.57 TB/s | 42.6 | 10,912.7 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 2 |
| gpu | kv_read | 32 |
| gpu | link_latency | 16 |
| gpu | weight_read | 198 |
| rom | compute | 50 |
| rom | infeasible | 584 |
| rom | kv_read | 292 |
| rom | layer_fixed_latency | 10 |
| rom | link_latency | 119 |
| rom | weight_read | 481 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 2 |
| rom | CAPACITY | 584 |

## Mechanical consistency audit

**PASS** over 25,835 checks.

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

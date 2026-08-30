# Which road to take

Every number here comes from `src/opentallas/roofline.py` and the studies under
`results/roofline/`, not from hand arithmetic. The model reproduces two shipping
parts: an A100 weight-bound decode to the digit, and Taalas HC1 within 1.23×.

## The result

Aggregate tokens/s, best design at each point, N6 against iso-area A100:

| model | batch | ROM+MAC | compute-in-ROM | **CIM + per-region** | winner |
|---|---:|---:|---:|---:|---|
| Qwen3-8B @8K | 1 | 12,172 | **18,711** | 18,711 | CIM **1.54×** |
| | 64 | 12,324 | **20,862** | 20,862 | CIM **1.69×** |
| | 256 | 12,334 | 12,334 | 12,334 | tie (KV-bound) |
| DeepSeek-Flash @200K | 1 | 12,172 | **18,711** | 18,711 | CIM **1.54×** |
| | 8 | 97,379 | 20,599 | **119,993** | per-region **1.23×** |
| | 64 | 148,406 | 20,862 | **562,709** | per-region **3.79×** |
| DeepSeek-Pro @1M | 1 | 10,378 | **15,299** | 15,299 | CIM **1.47×** |
| | 64 | **59,062** | 18,743 | 59,062 | tie |

## Recommendation

**1. Build compute-in-ROM, not ROM feeding a MAC array.**

It wins at batch 1 on every model by ~1.5×, and the reason is structural rather
than marginal: a storage-plus-MAC design spends silicon on an array that then
becomes its own bottleneck, while compute-in-ROM spends that area on more ROM
and has no separate compute roof to bind on. Taalas has also shown it is
buildable, at DRAM-class density with 0.0017% of cells switching per cycle,
which is what allows 200–250 W on 815 mm².

**2. Add a per-region activation port. This is the single highest-value
departure from what Taalas built.**

For a dense model it is worth nothing — one region, every token lands on it.
For sparse MoE it is worth **3.79× at batch 64** on DeepSeek-Flash, because
tokens selecting disjoint experts drive disjoint regions at the same time. Taalas
did not need it: Llama-3.1-8B is dense. Our models are not, and this is the one
place sparsity converts directly into throughput.

Cost is a pre-compute block per region — `2^b` shift-add units, 8 at 3-bit
weights — and the activation distribution wiring. Small against the array it
serves.

**3. Array of reticle-class chips, not a wafer, unless per-user latency demands
otherwise.**

Wafer-scale is not required by capacity. A composable array is viable for all
three models at their realistic per-user rates: Qwen needs no distribution at
all (416 mm² of ROM in FP8, one chip), Flash costs 4.4% of its budget over ten
chips, Pro 8.4% over fifty-three. The array yields better, tolerates single-chip
failure, and composes.

The wafer earns its difficulty only above ~7,400 tok/s per user for Flash or
~1,280 for Pro, or for tensor parallelism at any interesting rate — NVLink
tensor parallelism costs 108–183 µs of pure collective latency against a 58.8 µs
budget at Taalas-class speed, while on-wafer it costs 7.2–12.2 µs. **That is the
one argument for a wafer, and it is about latency, not capacity.**

**4. KV in SRAM for the dense small model; HBM for the sparse large ones.**

Qwen at 8K needs 12.08 TB/s of KV bandwidth but only 1.2 GB per user, so SRAM is
chosen for *bandwidth* and capacity caps context and batch. DeepSeek at 200K
needs 0.65 TB/s but 45 GB at batch 64, so HBM is chosen for *capacity* and its
bandwidth is never the constraint. Sparsity reduces the KV *read*, not the cache.

**5. Target the sparse long-context models. That is where the thesis is
strongest, and it is counter-intuitive.**

The weight-to-KV read ratio is 113:1 for Flash at 200K and 260:1 for Pro at 200K,
against 3.1:1 for dense Qwen at 32K. Sparse attention keeps the KV read tiny
while the weights stay large, so **long context plus sparsity is the
ROM-favourable regime, not the adverse one**. A dense model's ROM advantage is a
short-context advantage — which is precisely the regime Taalas shipped into.

## What would change this

- **The compute-in-ROM cell area multiplier (assumed 1.6×)** is the second most
  load-bearing number in the model after the ROM-to-SRAM cell ratio, and it
  decides recommendation 1. No compute-in-ROM bitcell has been published at any
  node. A fabricated test structure would settle it.
- **Whether per-region activation is realisable** at the wiring cost assumed. It
  decides recommendation 2, and it is a circuit question this analysis cannot
  answer.
- **The batch size behind Taalas's 16,960 tok/s**, which is published nowhere. If
  it is not 1, the anchor means something different and every ratio here shifts.

Each is falsifiable, and each is named in `configs/hardware/technology.json`
with its grade.

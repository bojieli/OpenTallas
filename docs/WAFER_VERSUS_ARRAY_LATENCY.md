# Wafer or array: the latency budget decides, and it decides differently per model

A wafer is hard to build — stitching, yield, repair, a single 15–23 kW thermal
object. An array of reticle-class chips on an NVLink-class fabric is easier to
yield, naturally fault-tolerant, and composable. The question is whether the
array can meet the latency budget, because **decode is sequential across tokens
and across layers**, and at batch 1 a pipelined array supplies no parallelism at
all: every token still traverses every layer in order. Pipelining only overlaps
*different sequences*.

So the array buys composability and pays hops. Whether that trade is available
depends entirely on the target per-user decode rate.

## 1. The budget

| per-user rate | budget per token |
|---:|---:|
| 17,000 tok/s (Taalas HC1 class) | 58.8 µs |
| 10,000 | 100 µs |
| 3,000 | 333 µs |
| 1,000 | 1,000 µs |

Hop latencies used below: **on-wafer 100 ns**, on-package chiplet 300 ns,
**NVLink 1.5 µs**, InfiniBand/Ethernet 5 µs. NVLink point-to-point sits "around
a microsecond" for small messages ([NVIDIA](https://www.nvidia.com/en-us/data-center/nvlink/),
[Thunder Compute](https://www.thundercompute.com/blog/what-is-nvlink)); a real
all-reduce is two phases through a switch plus launch and synchronisation
overhead, so 1.5 µs is if anything optimistic and 3–10 µs is common in practice.

## 2. Pipeline parallel: N−1 serial hops per token

Cost as a fraction of the token budget, NVLink-class:

| per-user rate | N=4 | N=10 | N=16 | N=56 | N=112 |
|---|---:|---:|---:|---:|---:|
| 17,000 tok/s | 8% | 23% | 38% | **140%** | **283%** |
| 10,000 | 4% | 13% | 22% | **82%** | **166%** |
| 3,000 | 1% | 4% | 7% | 25% | 50% |
| 1,000 | 0% | 1% | 2% | 8% | 17% |

At Taalas-class speed an iso-area array of 56 chips is **impossible** — the hops
alone exceed the whole budget by 40%. At 1,000–3,000 tok/s the same array costs
8–25%, which is a design cost rather than a wall.

## 3. Tensor parallel is roughly fifteen times worse

Tensor parallelism needs two all-reduces per layer, every token, *regardless of
how few chips it is spread over*:

| model | layers | collectives/token | on-wafer | NVLink |
|---|---:|---:|---:|---:|
| Qwen3-8B | 36 | 72 | 7.2 µs | **108 µs** |
| DeepSeek-V4-Flash | 43 | 86 | 8.6 µs | **129 µs** |
| DeepSeek-V4-Pro | 61 | 122 | 12.2 µs | **183 µs** |

Against a 58.8 µs budget, NVLink tensor parallelism is simply not available at
high decode rates — the collectives alone are 1.8–3.1× the entire budget. The
same tensor parallelism on-wafer costs 7.2–12.2 µs, or 12–21% of the budget, and
fits. **This is the sharpest argument for wafer-scale**, and it is an argument
about latency, not bandwidth.

## 4. The result, per model — and it is not what the wafer framing suggests

Chips needed for the ROM array alone, at 19.7 MB/mm², and the per-user rate at
which pipeline hops reach 10% of the budget:

| model | ROM array | reticle chips | PP hops | hop cost | array viable up to |
|---|---:|---:|---:|---:|---:|
| Qwen3-8B FP8 | 416 mm² | **1** | 0 | 0 | **no distribution needed** |
| DeepSeek-V4-Flash | 8,472 mm² | 10 | 9 | 13.5 µs | **7,400 tok/s** |
| DeepSeek-V4-Pro | 45,315 mm² | 53 | 52 | 78.0 µs | **1,280 tok/s** |

**A composable array is viable for all three targets at their realistic decode
rates.** Qwen3-8B needs no distribution at all — half a reticle of ROM, one
chip, and Taalas has built essentially that part. Flash over ten chips costs
4.4% of a 308 µs budget. Pro over fifty-three chips costs 8.4% of a 926 µs
budget.

Wafer-scale is therefore **not required by capacity**. It is required only when
you want per-user speed that the hop count forbids: above ~7,400 tok/s for
Flash, above ~1,280 tok/s for Pro, or for tensor parallelism at any interesting
rate.

## 5. What this changes

The project has been assuming wafer-scale for the large models. The latency
arithmetic says the honest framing is a **choice with a stated crossover**:

- **Array of reticle chips** — better yield, fault-tolerant to single-chip
  failure, composable, incrementally purchasable. Caps per-user decode at the
  rates above, and forecloses tensor parallelism.
- **Wafer** — 15× the latency headroom, tensor parallelism available, and the
  only route to Taalas-class per-user speed on a model too large for one chip.
  Costs stitching, yield, repair and a 15–23 kW thermal object.

Both should be modelled, and the comparison should report the crossover rather
than assert one topology. The array is the better default for the large models
at their realistic per-user rates; the wafer earns its difficulty only where the
latency budget is tight.

**Caveat.** These are hop-latency floors. They ignore per-hop serialisation of
the activation payload, switch contention, and the pipeline fill cost at batch
1. Each of those makes the array worse, never better, so the crossover rates
above are upper bounds on where the array remains viable.

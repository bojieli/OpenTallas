# Per-region compute-in-ROM: the design, and why not ROM plus a MAC array

Every figure below comes from `src/opentallas/roofline.py` and
`configs/hardware/technology.json`. The model reproduces an A100's weight-bound
decode exactly and Taalas HC1 within 1.23×.

---

## 1. Why compute-in-ROM beats ROM feeding a MAC array

The intuition — "one transistor per weight gives you billions of multipliers" —
is *not* the reason, and it is worth killing first. On raw arithmetic the two
machines are nearly identical:

| | area | multiply throughput |
|---|---:|---:|
| ROM (248 mm²) + MAC array (331 mm²) | 815 mm² die | 1.48e14 MAC/s |
| compute-in-ROM, 8.03e9 cells | 815 mm² die | 1.40e14 MAC/s at a storage-cell sweep |

**The real reason is that the MAC array cannot be fed.** At 1 byte per MAC an
FP8 array of 1.48e14 MAC/s wants 1.48e14 B/s of weights. The 248 mm² of ROM
beside it supplies 6.99e13 B/s — **0.47×**. So a third of the die is a MAC array
running at under half duty, and the step is weight-bound anyway.

The second reason is a genuine surprise and it is where the win actually comes
from. **The array sweep is a per-bit quantity, not a per-area one:**

```
sweep_time = capacity_density / bandwidth_density      (bits/mm² ÷ bytes/s/mm²)
```

Both densities scale with area, so area cancels. A compute-in-ROM cell is ~1.6×
larger than a storage-only cell, which means **1.6× fewer bits per mm² at the
same bytes/s per mm² — so every stored bit is reachable 1.6× sooner**:

| | sweep of the whole array |
|---|---:|
| storage-only cell | **57.4 µs** |
| compute-in-ROM cell | **35.9 µs** |

And because the multiply happens *at* the cell, that sweep **is** the compute.
There is no second unit to feed and nothing to starve.

| Qwen-class 8B, 815 mm², N6 | step | tokens/s |
|---|---:|---:|
| ROM + MAC array | max(57.4 read, 54.4 compute) = 57.4 µs | 17,417 |
| compute-in-ROM | 35.9 µs, read and compute fused | **27,867** |
| | | **1.60×** |

**The load-bearing subtlety:** the cell-area multiplier cuts both ways. Larger
cell means less capacity per mm² (you need more silicon for the same model) *and*
faster access per bit. The design wins on throughput and pays on capacity. At
1.6× that trade is favourable; below about 1.2× the advantage largely
disappears, and no compute-in-ROM bitcell has been published at any node, so
**this is the number a fabricated test structure should settle first.**

---

## 2. Per-region activation: the design

### What Taalas appears to build

One activation `x` enters. A pre-compute block forms every product `x·w` over the
weight alphabet — 8 values at 3 bits, built from shifts and carry-save adders.
Those 8 values are **broadcast on global product lines spanning the whole
fabric**. Each cell's stored weight, one-hot decoded, opens a single pass
transistor tapping its line. Accumulators sum per output.

One pass = one token. A second token has a *different* activation, so the
product lines must be redriven: **a second pass in time**. Aggregate throughput
equals per-user throughput.

For Llama-3.1-8B that costs nothing, because a dense model engages the whole
array for every token anyway. There is no concurrency to lose.

### The change

Partition the fabric into **R regions, one per expert**, and give each its own
pre-compute block and its own *local* product lines. Now R different activations
can be resident at once. A token routed to experts `{e₁…e_k}` drives its
activation into those k regions only. **Two tokens selecting disjoint experts run
at the same time.**

Sweep depth is then the busiest region's queue rather than the batch:

```
passes = (B · k) / (N · coverage(B)) / load_balance      coverage = 1 − (1 − k/N)^B
```

At B=1 that is exactly one pass — which is why all three machines agree at batch
1, and why the published anchor cannot choose between them.

### Sizing, and why the overhead is small

| | DeepSeek-V4-Flash | DeepSeek-V4-Pro |
|---|---:|---:|
| experts / active per token | 256 / 6 | 384 / 6 |
| routed weights per expert | 574.9 MB | 2,140.8 MB |
| **one region** | **56.8 mm²** | **211.4 mm²** |
| pre-compute block per region | 1.14 mm² (**2.0%**) | 4.23 mm² (**2.0%**) |
| all R blocks | 290.6 mm² (**1.8%** of array) | 1,623 mm² (**1.8%**) |
| whole checkpoint | 16,478 mm² = 19.2 reticles | 88,150 mm² = 102.7 reticles |

A region is tens to hundreds of mm². Eight shift-add units are negligible against
that — **1.8% of the array buys the concurrency.**

The real cost is not the pre-compute block; it is the **activation distribution
network** that must deliver B activations to R regions, and a small activation
queue per region. Local product lines are *shorter* than global ones, so their
capacitance and drive energy fall — a second-order gain that partly offsets the
distribution cost.

### What it is worth

Aggregate tokens/s, best design, iso-area against A100 at N6:

| model | batch | ROM+MAC | CIM broadcast | **CIM per-region** |
|---|---:|---:|---:|---:|
| Qwen3-8B @8K | 64 | 12,324 | 20,862 | 20,862 (**no gain**) |
| DeepSeek-Flash @200K | 8 | 97,379 | 20,599 | **119,993** |
| DeepSeek-Flash @200K | 64 | 148,406 | 20,862 | **562,709** — 27× broadcast |
| DeepSeek-Pro @1M | 64 | 59,062 | 18,743 | 59,062 |

**Nothing for a dense model; 27× over a global broadcast for sparse MoE at batch
64.** One region, every token lands on it, no disjointness to exploit — that is
why Taalas did not need this, and why we do.

---

## 3. What would falsify this

1. **The compute-in-ROM cell area multiplier (assumed 1.6×).** It decides section
   1 in both directions — capacity and speed. Nothing comparable is published.
2. **Whether per-region activation is realisable at the assumed wiring cost.** A
   circuit question this analysis cannot answer; the 1.8% is the pre-compute
   block only, not the distribution network.
3. **The batch size behind Taalas's 16,960 tok/s**, published nowhere. If it is
   not 1, the anchor means something different and every ratio moves.

All three are graded `assumed` in `configs/hardware/technology.json` with their
reasons.

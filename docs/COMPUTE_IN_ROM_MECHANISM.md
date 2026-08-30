# What "the ROM cell does the multiply" actually means

Ljubisa Bajic's line — *"we can store four bits away and do the multiply
related to it – everything – with a single transistor"* — is widely repeated,
including by me. It is worth taking apart, because the mechanism decides whether
batching helps, and that in turn decides the whole ROM-versus-GPU comparison.

**Taalas has published no microarchitecture.** What follows separates what is
established from what is a reconstruction.

## 1. It is not analog compute-in-memory

The well-known way to "compute in memory" is analog, and it genuinely gets both
operations for free:

- **multiply** — cell conductance × wordline voltage gives a current, by Ohm's law;
- **accumulate** — every cell on a bitline dumps its current onto the same wire,
  and Kirchhoff's current law sums them with no adder at all.

That approach needs an ADC per column, and the ADC usually dominates area and
power. Its precision is set by noise and ADC resolution, not by a number format.

**Taalas does not appear to be doing this.** No ADCs are described anywhere, the
weights are a conventional integer alphabet (a 3-bit base mixed with 6-bit), and
the reported system energy of ~1.5–1.8 pJ/MAC is orders of magnitude above what
analog CIM achieves. The design reads as fully digital.

## 2. The reconstructed mechanism: pre-compute, select, accumulate

The most detailed public reconstruction ([Taalas HC1 Architecture
Decoded](https://yongwei.site/en/taalas-hc1-arch/)) describes a lookup strategy
that "eliminates repeated multiplications through pre-computation and
selection", in three stages:

1. **Pre-compute.** For one input activation `x`, compute *every* product `x·w`
   over the small weight alphabet — 8 values for a 3-bit weight. This is cheap:
   multiplying by a small constant is shifts and carry-save adders, and the
   analysis notes the activation "can be input bit-by-bit from LSB to MSB".
2. **Select.** The mask ROM holds the weight, decoded to a one-hot line that
   drives a **single-transistor transmission gate** in a crossbar, tapping the
   one pre-computed product this weight wants. The ROM itself is built from
   complementary via placement across two metal layers — which is exactly why a
   model change is two mask layers.
3. **Accumulate.** Ordinary digital accumulators sum the selected products per
   output neuron.

So, answering the question directly: **the matrix multiply is not performed by
the ROM.** The multiply is done once per activation, in normal digital logic,
against the whole weight alphabet. The ROM's job is *selection* — it says which
pre-computed product this weight contributes. And the addition is a conventional
digital adder tree, not a free physical summation.

The reconstruction is explicit that Bajic's "single transistor" is **the
switching element, not the multiplier**.

## 3. Why this is still a very good idea

A column of `N` weights sharing one activation costs `2^b` multiplies plus `N`
selects, instead of `N` multiplies. With `b = 3` that is 8 real multiplies for a
column of any length. The expensive operation is amortised across *the weights*,
and the cheap per-weight operation is a single pass transistor — which is how one
transistor per 4-bit parameter becomes credible, and how 8.03 billion parameters
fit in ~815 mm² with only ~136,000 cells switching per cycle (0.0017%
activation). That activation figure is what makes 200–250 W possible.

## 4. The consequence that matters: batching does not amortise

This is the part that bears on the project's thesis.

On a GPU, a weight fetched from HBM is **reused across every sequence in the
batch**. That is precisely what batching amortises, and why GPU aggregate
throughput climbs steeply with batch while per-user latency degrades.

On a compute-in-ROM fabric the weight never moves — but the *select-and-
accumulate path is physically bound to the weight's location*. A second
concurrent sequence has a different activation, so it needs its own
pre-computation and its own pass through the same crossbar. There is nothing to
amortise, because nothing was being fetched.

If that reading is right, **aggregate throughput per die ≈ per-user throughput**,
and the iso-area comparison splits sharply:

| | HC1 | A100 826 mm² | ratio |
|---|---:|---:|---:|
| per-user, batch 1 | 16,960 tok/s | 254 tok/s | **66.8×** |
| aggregate per die | ~16,960 tok/s | ~7,771 tok/s (40% MFU) | **~2.2×** |

It also explains why Taalas quotes **per user** everywhere and never states a
batch size, and why the SRAM budget supports only ~1.4–8 concurrent users at 2k
context. A part whose aggregate equals its per-user rate has no reason to
advertise concurrency.

## 5. The design fork this creates

Two different machines, with different scaling laws:

| | compute-in-ROM (HC1) | ROM storage + MAC array |
|---|---|---|
| weight density | ~0.0023–0.0040 µm²/bit, DRAM-class | same ROM density |
| cell activation | 0.0017% per cycle | whole array read per step |
| multiply | pre-computed per activation, selected per weight | conventional MAC |
| **batching** | **no amortisation; aggregate ≈ per-user** | **amortises like a GPU** |
| sparse MoE | unselected experts cost nothing | unselected experts cost nothing |
| best at | per-user latency | aggregate throughput |

**The sparse-MoE argument — that batching lights up idle expert regions and
raises aggregate throughput — requires the second machine, not the first.** On a
compute-in-ROM fabric, engaging more experts engages more fabric, but each token
still needs its own pass, so aggregate does not climb the way it would if a
weight read were being shared.

The project has been implicitly assuming the second machine. That assumption
should be made explicit and defended, because the shipping part is the first one.

## 6. What is established and what is not

**Published:** TSMC N6, 815 mm², 53 B transistors, 16,960 tok/s per user on
Llama 3.1 8B at 1k/1k sequence length, mask ROM for weights, SRAM for KV and
adapters, 3-bit base mixed with 6-bit, model change = 2 mask layers, ~200–250 W
per card. All figures self-run by Taalas; no third-party or MLPerf measurement.

**Not published:** the microarchitecture, the clock, the SRAM capacity, the batch
size, and whether aggregate exceeds per-user.

**Reconstructed, not authoritative:** the pre-compute / select / accumulate
mechanism, and therefore the batching conclusion. It is coherent, it explains the
quote, the density, the activation fraction and the per-user framing — but it is
one analyst's reading of a chip whose designers have described it only in
sentences.

**This is the highest-value open question in the comparison**, because the
per-user and aggregate ratios differ by 30×.

# What "the ROM cell does the multiply" actually means

> **CORRECTION, 2026-08-30.** The closing claim of the previous version — *"the
> per-user and aggregate ratios differ by **30×**"* — rested on a `~2.2×
> aggregate` figure computed from an assumed **40% MFU** for an A100. That
> assumption appears in no config, no artifact and no test in this repository:
> **nothing produced it.** The fork it was trying to size *is* now produced, by
> a different derivation, and it is smaller: the executable study quantifies
> compute-in-ROM's cost as **up to 20.71× of aggregate throughput at batch 256**
> against A100, and **up to 28.5×** against B200. The per-user side of the
> comparison (66.8×) survives with both of its terms cited. The paragraph
> asserting that the activation fraction *"is what makes 200–250 W possible"* is
> **withdrawn**: it is a power-model inference. The rebuilt HC1 power gate still
> reaches only 87.6 W against the published 200–250 W band, a 2.3–2.9×
> shortfall, and the throughput reconstruction is capacity-infeasible.
>
> Nothing in the *mechanism* reconstruction changed. §§1–3 stand as written.

Ljubisa Bajic's line — *"we can store four bits away and do the multiply
related to it – everything – with a single transistor"* — is widely repeated,
including by me. It is worth taking apart, because the mechanism decides whether
batching helps, and that in turn decides the whole ROM-versus-GPU comparison.

**Taalas has published no microarchitecture.** What follows separates what is
established from what is a reconstruction. Regenerate every quantitative claim
below with `make roofline`; each is cited to
[`results/roofline/n6_vs_a100/REPORT.md`](../results/roofline/n6_vs_a100/REPORT.md)
or its N5/B200 twin
[`results/roofline/n5_vs_b200/REPORT.md`](../results/roofline/n5_vs_b200/REPORT.md),
by section and column name.

## 1. It is not analog compute-in-memory

The well-known way to "compute in memory" is analog, and it genuinely gets both
operations for free:

- **multiply** — cell conductance × wordline voltage gives a current, by Ohm's law;
- **accumulate** — every cell on a bitline dumps its current onto the same wire,
  and Kirchhoff's current law sums them with no adder at all.

That approach needs an ADC per column, and the ADC usually dominates area and
power. Its precision is set by noise and ADC resolution, not by a number format.

**Taalas does not appear to be doing this.** No ADCs are described anywhere, and
the weights are a conventional integer alphabet — a 3-bit base mixed with 6-bit
(`configs/hardware/technology.json` →
`reference_parts.taalas_hc1.weight_bits_per_parameter`, `assumed` at 3.5,
swept 3.0–6.0, sourced to the press reports registered in
[`docs/SOURCES.md`](SOURCES.md) under `SRC-TAALAS-HC1`). The design reads as
fully digital. A reported system energy of order 1.5–1.8 pJ/MAC is orders of
magnitude above what analog CIM achieves, which is consistent with that reading —
but that figure is **reported, not produced here**, and no energy or power number
in this repository is currently publishable (see the note at the end).

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
fit in ~815 mm² (`technology.json` → `reference_parts.taalas_hc1.die_area_mm2`,
`published`).

The model gives that argument a shape of its own. Compute-in-ROM has no MAC
array, so it recovers that silicon; what it spends the silicon on is swept rather
than assumed, and the same sweep is offered to the amortising machine so that
offering it to one side does not move the artefact
(`n6_vs_a100/REPORT.md` → "The floorplan sweep: where the recovered silicon
goes"). Two inputs carry the whole argument and neither is measured:
`rom.cim_cell_area_multiplier` = **1.6** (a compute-in-ROM cell against a
storage-only mask-ROM cell) and `rom.cim_precompute_area_fraction` = **0.02**
(the pre-computation block's share of die area). Both are graded `assumed` with
the note *"no published compute-in-ROM bitcell at any node"*, and the first is
described in the config as the second most load-bearing assumption in the file.

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

The study models both machines and reports the difference rather than choosing.
`-perstream` is compute-in-ROM; the default is ROM-as-storage feeding a MAC
array; the `Per-stream penalty` column is the ratio between them
(`n6_vs_a100/REPORT.md` → "The batch-amortisation fork, reported rather than
resolved").

**The per-user side of the comparison, both terms cited:**

| | published / modelled | source |
|---|---:|---|
| Taalas HC1, Llama-3.1-8B on 815 mm² at N6, per user | **16,960 tok/s** | published; `n6_vs_a100/REPORT.md` → "Validation gates" |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm² | **253.91 tok/s** | same table; modelled = published to 1.00× |
| ratio | **66.8×** | 16,960 / 253.91, my division of two cited cells |

The model's own current HC1 reconstruction admits **zero throughput**: after
the ROM-density and compute-in-ROM floorplan corrections, the 815 mm² die has
only 432.4 mm² available for an array that needs 770.5 mm². The gate is
deliberately not fitted to close that (`n6_vs_a100/REPORT.md` → "The per-layer
latency band, and why the gate is not fitted"). Quoting 66.8× therefore quotes
Taalas's own self-run figure against this project's A100 model; it is not a
ratio reproduced by the current HC1 model.

**The aggregate side, replacing the retracted `~2.2×` and `30×`:**

| | value | where |
|---|---:|---|
| largest per-stream penalty, N6 vs A100 | **20.71×** | Flash, B=256, `sram` spare |
| largest per-stream penalty, N5 vs B200 | **28.5×** | finding 11 |
| per-stream penalty at **batch 1**, Flash and Pro | **1.00×** | same table |
| per-stream penalty at batch 1, Qwen3-8B (`sram` spare) | **0.94×** | same table |

The Qwen batch-1 cell is below one, which is worth stating because it is the one
case where compute-in-ROM is *ahead*: the amortising machine binds on `kv_read`
there and the per-stream machine binds on `weight_read`, so the fork is not a
uniform penalty.

**The point the previous version was making survives in a narrower form.** The
two policies have the same sweep count at batch 1, so that one operating point
cannot validate their distinct high-batch amortisation laws. They are not the
same physical machine there: the compute-in-ROM cell multiplier and pre-compute
reservation change capacity and the solved floorplan. The current HC1
reconstruction demonstrates that distinction by failing capacity. What is
retracted is both the old claim of machine identity and the 40%-MFU arithmetic
that produced the earlier gap.

Taalas's launch-deck footnote now resolves the batch-size question: the quoted
point is **BS=1 per chip**, and
`technology.json` → `reference_parts.taalas_hc1.batch_size` is graded
`published`. That still supplies no evidence for the high-batch scaling law.

## 5. The design fork this creates

Three machines, not two — the study models a third that sits between them.

| | compute-in-ROM (`per_stream`) | per-expert-port (`per_region`) | ROM storage + MAC (`batched`) |
|---|---|---|---|
| weight density | mask-ROM cell × 1.6 (`assumed`) | same | mask-ROM cell |
| multiply | pre-computed per activation, selected per weight | same | conventional MAC |
| **batching** | **no amortisation; aggregate ≈ per-user** | disjoint experts run concurrently | **amortises like a GPU** |
| sparse MoE | unselected experts cost nothing | unselected experts cost nothing | unselected experts cost nothing |
| best at | per-user latency | sparse aggregate | aggregate throughput |

**The sparse-MoE argument — that batching lights up idle expert regions and
raises aggregate throughput — requires the second or third machine, not the
first.** On a compute-in-ROM fabric with a global activation broadcast, engaging
more experts engages more fabric, but each token still needs its own pass.

The middle machine recovers part of what compute-in-ROM gives up, and the model
sizes that recovery: giving each expert region its own activation port is worth
**up to 7.20×** over a global broadcast at N6 (Flash, batch 256, where the
busiest region carries 3.04× the load of the mean engaged one) and **up to
8.77×** at N5. It is not free ground — per-region still loses to the amortising
machine at **43 of 48** operating points at N6 — and a dense model has one
region, so it gains nothing. Full treatment in
[`docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`](PER_REGION_COMPUTE_IN_ROM_DESIGN.md).

The project has been implicitly assuming the third machine. That assumption is
now explicit and swept rather than defended in prose, because the shipping part
is the first one.

## 6. What is established and what is not

**Published:** TSMC N6, 815 mm², 53 B transistors, 16,960 tok/s per user on
Llama 3.1 8B at 1k/1k sequence length, mask ROM for weights, SRAM for KV and
adapters, 3-bit base mixed with 6-bit, model change = 2 mask layers. All figures
self-run by Taalas; no third-party or MLPerf measurement. Each of these is
registered in [`docs/SOURCES.md`](SOURCES.md) under `SRC-TAALAS-HC1` with its
individual grade, because they do not all come from the same place: the die area
and the token rate are on the vendor's own product page, while the transistor
count, the weight format and the card power come from secondary press.

**Not published:** the microarchitecture, the clock, the SRAM capacity, the batch
size, and whether aggregate exceeds per-user.

**Reconstructed, not authoritative:** the pre-compute / select / accumulate
mechanism, and therefore the batching conclusion. It is coherent, it explains the
quote, the density and the per-user framing — but it is one analyst's reading of
a chip whose designers have described it only in sentences.

**This is the highest-value open question in the comparison**, because it is
worth up to **20.71×** of aggregate throughput at batch 256, while the published
anchor sits at batch 1 where the competing sweep-count laws coincide. The
anchor can test the candidate floorplans at that point; it cannot establish
their scaling.

---

## Power figures: withdrawn

Two claims in the previous version are withdrawn rather than corrected.

- *"~136,000 cells switching per cycle (0.0017% activation). That activation
  figure is what makes 200–250 W possible."* **Nothing produces the 136,000, the
  0.0017%, or the inference.** No config, artifact or test in this repository
  contains any of them, and the second half is a power claim.
- *"~200–250 W per card"* as a stated Taalas figure. The number itself is
  registered (`technology.json` → `reference_parts.taalas_hc1.power_w` = 250,
  graded `published`, sourced to a Kaitchup post — a secondary press report, and
  `docs/SOURCES.md` forbids secondary press for a value where a primary source
  exists). It is retained *there*, as a source-register entry, and not quoted
  here as evidence for anything.

**This project's power model is bounded, not measured.** Its A100 gate passes at
1.15× of TDP, while the HC1 gate remains 2.3–2.9× below the published card-power
band. Watts in `results/roofline/*/REPORT.md` are model outputs whose assumed
terms and both gate results must travel with them; they are not fabricated-ROM
power evidence. The infeasible HC1 attempt supports no tokens-per-joule claim.

## What nothing produces

- **`~365–1,130 MB of SRAM → 1.4–8 concurrent users at 2k context.`** Removed
  from §4. Taalas publishes no SRAM capacity, and no artifact here derives one.
  The model's own HC1 point reports its KV area from the anchor's assumed batch
  of 1, which is not the same quantity.
- **`~1.5–1.8 pJ/MAC`.** Reported externally; not produced, not registered as a
  graded source, and not used as an input anywhere.
- **The `66.8×` ratio itself.** Both of its terms are in the gate table; their
  quotient is not, and I computed it. If the A100 gate moves, this number goes
  stale silently.

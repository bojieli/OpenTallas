# Per-region compute-in-ROM: the design, and why not ROM plus a MAC array

Every figure below is emitted by `src/opentallas/roofline.py` and read out of
`results/roofline/n6_vs_a100/REPORT.md` and `analytical.json`. Nothing is
recomputed in prose — the previous version of this document said the same thing
and did not do it, and section 1 is the retraction that resulted.

The model reproduces an A100's weight-bound decode exactly (253.91 tok/s against
253.91) and the Taalas HC1 at **0.72×** of its published 16,960 tok/s per user,
within a 2× gate that is not relaxed anywhere in this program. The KV accounting
is validated against executed hardware to a ratio of exactly 1.0000 on both Qwen
lanes in `results/roofline/qwen3_execution_validation.json`.

---

## 1. Why compute-in-ROM does *not* beat ROM feeding a MAC array on throughput

**RETRACTED: "compute-in-ROM beats ROM+MAC by 1.60×."** That result was a
modelling error, and the shape of the error is worth more than the claim.

`balanced_area_split` applied the 1.6× compute-in-ROM cell-area multiplier to
**area only**, and then `weight_read = rom_mm2 × bandwidth_density` credited that
larger area with the *storage* cell's bandwidth density. The design was charged
for a bigger cell and handed the bandwidth of an array without one. Sweep time is

```
sweep = capacity_density / bandwidth_density          (bytes/mm2 over bytes/s/mm2)
```

so scaling only the numerator makes the array look 1.6× faster for no physical
reason. Both densities are cells-per-mm² quantities: a 1.6× larger cell means
1.6× fewer bits per mm² **and** 1.6× fewer bytes per second per mm², because the
extra area is select transistors and product-line taps — it adds no bitline and
no sense amp. **The cell size cancels.** From the model, on the anchor die:

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0× | 1.6× |
| ROM array | 216.8 mm² | 346.9 mm² |
| compute block | 451.5 mm² | 16.3 mm² (pre-compute only) |
| SRAM | 0.0 mm² | 305.1 mm² |
| sustained fp8 compute roof | 2.214e14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.107e14 | n/a |
| weight bytes/s the array supplies | 4.589e13 | 4.589e13 |
| **can the compute block be fed?** | **0.41×** | there is nothing to feed |
| **full-array sweep** | **76.55 µs** | **76.55 µs** |

Two further notes on the retraction, because both are instructive.

The retraction had already been written as a banner on this document and on
`docs/TECHNICAL_DIRECTION_RECOMMENDATION.md`, and the fix had **not been made in
the code** — the model still contained the error. And the banner's own arithmetic
was wrong in the same way as the claim it retracted: it gave "the corrected sweep
is **57.4 µs** either way … 17,400 vs 17,417 tok/s", which is the sweep with
`efficiencies.rom_read_bandwidth = 0.75` dropped. The model's own numbers are
57.41 µs / 17,417 tok/s before that derate and **76.55 µs / 13,063 tok/s** after
it, and only the second enters a result. A hand-computed retraction reproduced
the failure it was retracting. Both documents are now generated from the model's
own output for exactly this reason.

### What survives, and it is an area argument

The intuition "one transistor per weight gives you billions of multipliers" was
never the reason and is still not. The reason that survives is the 0.41× row
above: **more than half the storage machine's die is a MAC array that can be fed
at 0.41× of what it wants** at one weight byte per multiply-accumulate. Compute-
in-ROM does not spend that silicon.

The corrected model tests what the recovered silicon is worth rather than
asserting it. Whatever a compute-in-ROM part does not spend on a MAC array it can
spend on KV store or on **a replicated copy of the array** — R copies, each with
its own bitlines and sense amps, reading R disjoint slices of the weight set at
once, so the sweep falls by R. Both destinations are swept, and the same sweep is
offered to the amortising machine, whose balanced floorplan sizes its MAC array to
consume exactly what the array beside it can read. From `The floorplan sweep` in
the study, DeepSeek-Flash at batch 8:

| amortisation | spare | design | mm² | R | aggregate | tok/s/mm² | binds on |
|---|---|---|---:|---:|---:|---:|---|
| batched | sram | HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 87,122.5 | **1.885** | weight_read |
| batched | rom | HBMKV-wafer-tensor-x4-romfill | 184,900 | 7.81 | 213,473.6 | 1.155 | kv_read |
| per_region | sram | SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 44,793.0 | 0.969 | weight_read |
| per_region | rom | HBMKV-wafer-tensor-x4-perregion-romfill | 184,900 | 8.87 | 206,578.5 | 1.117 | weight_read |

**Replication buys per-user latency and costs throughput per square
millimetre.** That is the real content of the area argument, and it is the same
for both machines. What compute-in-ROM contributes is that it starts with ~300
mm² per device already free.

The third argument — compute-in-ROM moves no weights, so it burns no transport
energy — **is not represented in this model at all**. Its energy term charges
`rom_read_j_per_byte` against engaged bytes identically for both policies. Do not
read that silence as support.

---

## 2. Per-region activation: the design

### What Taalas appears to build

One activation `x` enters. A pre-compute block forms every product `x·w` over the
weight alphabet — 8 values at 3 bits, built from shifts and carry-save adders.
Those 8 values are broadcast on **global product lines spanning the whole
fabric**. Each cell's stored weight, one-hot decoded, opens a single pass
transistor tapping its line. Accumulators sum per output.

One pass = one token. A second token has a *different* activation, so the product
lines must be redriven: a second pass in time. Aggregate throughput equals
per-user throughput.

For Llama-3.1-8B that costs nothing, because a dense model engages the whole array
for every token anyway. There is no concurrency to lose.

### The change

Partition the fabric into **R regions, one per expert**, and give each its own
pre-compute block and its own *local* product lines. R different activations can
then be resident at once. A token routed to experts `{e₁…e_k}` drives its
activation into those k regions only. **Two tokens selecting disjoint experts run
at the same time.**

### How deep the sweep actually is — the correction that had to land

The previous version of this document gave the sweep depth as

```
passes = (B · k) / (N · coverage(B)) / load_balance      coverage = 1 − (1 − k/N)^B
```

which is the load of the **average engaged region**, divided by a flat
`expert_load_balance = 0.85`. The array does not finish when the average region
drains. It finishes when the deepest queue does — and the constant's own note in
`configs/hardware/technology.json` said so: *"the sweep depth is set by the
busiest region rather than the mean."* The code did not do what its parameter
documented.

`roofline.expected_max_region_load` now computes the busiest region directly. One
region's load is exactly `Binomial(B, k/N)` — a token marks a given region with
probability `k/N`, independently across tokens — so

```
P(max >= L) = 1 - (1 - P(Bin(B, k/N) >= L))^N
E[max]      = sum over L >= 1 of P(max >= L)
```

`tests/test_roofline.py` checks this against a 4,000-trial Monte Carlo that draws
the routing directly, at every batch from 1 to 256 for both 256 and 384 experts.
Agreement is within 3% everywhere and the estimator returns exactly 1.000 at
batch 1, where the true answer is one pass. (Two asymptotic closed forms —
`ln N / ln(ln N / m)` below unit mean and `m + sqrt(2 m ln N)` above it — were
tried first and are 24–31% low across batch 4 to 32, which is the middle of the
range where the per-region argument is made.)

From the model, DeepSeek-V4-Flash:

| B | mean engaged region | busiest region | correction |
|---:|---:|---:|---:|
| 1 | 1.000 | 1.000 | 1.00× |
| 8 | 1.085 | 2.134 | 1.97× |
| 32 | 1.410 | 4.026 | 2.85× |
| 64 | 1.921 | 5.831 | **3.04×** |
| 256 | 6.014 | 13.844 | 2.30× |

At B=1 the depth is exactly one pass, which is why all three machines agree at
batch 1 and why the published anchor cannot choose between them.

`expert_load_balance` is retired. Its replacement,
`efficiencies.expert_router_imbalance`, is a multiplier applied **on top of** the
busiest-region load rather than instead of it, and it carries only what is left:
the residual imbalance of a *trained* router against the uniform-random draw the
statistic assumes. It is 1.0 — the neutral value, which makes it inert — because
no routing trace exists to set it, and because a parameter must not take its
value from the answer it is wanted to produce. Every per-region result is exactly
linear in it, so a trace showing a 1.3× hot-expert bias moves every number in
section 3 by 1.3×.

### Sizing, and why the block overhead is small

From `Sizing one expert region` in the study, at the compute-in-ROM array density
(the storage density divided by the 1.6× cell multiplier):

| | DeepSeek-V4-Flash | DeepSeek-V4-Pro |
|---|---:|---:|
| experts / active per token | 256 / 6 | 384 / 6 |
| routed weights per expert | 574.9 MB | 2,140.8 MB |
| **one region** | **56.8 mm²** | **211.4 mm²** |
| pre-compute block per region | 1.14 mm² (**2.0%**) | 4.23 mm² (**2.0%**) |
| all R blocks | 291 mm² | 1,623 mm² |
| whole checkpoint | 16,478 mm² = 20.2 reticles | 88,150 mm² = 108.2 reticles |

A region is tens to hundreds of mm². Eight shift-add units are negligible against
that. The real cost is not the pre-compute block; it is the **activation
distribution network** that must deliver B activations to R regions, plus a small
activation queue per region. **This model does not price that network**, and no
number in this document should be read as if it did. Local product lines are
shorter than global ones, so their capacitance and drive energy fall — a
second-order gain that partly offsets the distribution cost, and one the model
does not represent either.

### One cost the design does carry, which was previously hidden

A compute-in-ROM cell is 1.6× a storage cell, so the same weights need 1.6× the
array — and more dies to hold it. The study now sizes DeepSeek-Flash at **26
dies against the batched machine's 18**, and DeepSeek-Pro at **138 against 93**.
Until this audit the
study sized every amortisation policy on the *batched* machine's floorplan and
handed the resulting device count to all three, so every compute-in-ROM DeepSeek
point came back infeasible with a capacity shortfall. That was the harness saying
*"we never tried enough dies"* and the report reading it as *"compute-in-ROM
cannot hold this model"*. Each policy is now sized on its own floorplan; the
capacity cost is real and is charged, and the infeasibility was not.

---

## 3. What per-region activation is worth

Aggregate tokens/s, best feasible design per policy at a **matched floorplan**,
N6 against iso-area A100. Matching the floorplan matters: comparing a per-region
machine that replicated its array against a broadcast one that did not would mix
the amortisation question with the allocation question and hide both.

| model | B | spare | ROM+MAC | CIM broadcast | **CIM per-region** | per-region over broadcast |
|---|---:|---|---:|---:|---:|---:|
| Qwen3-8B @8K (dense) | 1 | sram | 11,364 | 11,364 | 11,364 | **1.00×** |
| | 64 | sram | 12,310 | 13,032 | 13,032 | **1.00×** |
| | 64 | rom | 44,017 | 44,017 | 44,017 | **1.00×** |
| DeepSeek-Flash @200K | 1 | sram | 10,890 | 10,890 | 10,890 | 1.00× |
| | 8 | sram | 87,123 | 12,745 | 44,793 | 3.51× |
| | 64 | sram | 112,613 | 13,022 | **138,631** | **10.65×** |
| | 256 | sram | 114,929 | 13,053 | **198,349** | **15.20×** |
| | 64 | rom | 372,307 | 101,292 | 372,307 | 3.68× |
| DeepSeek-Pro @1M | 64 | sram | 44,676 | 11,701 | **79,976** | 6.84× |
| | 256 | sram | 45,291 | 11,743 | **141,001** | 12.01× |

**RETRACTED: "27× over a global broadcast at batch 64."** The model now says
**10.65×** at that point. The 27× came entirely from charging the mean engaged
region instead of the busiest one.

Three things to read out of this table.

**The dense row is the mechanism working, not a disappointment.** Per-region
recovers ROM regions that a sparse router left idle. Qwen3-8B has one region, so
every token lands on it and there is nothing to recover — the three policies must
tie, and they do, at 1.00× at every batch and in both floorplans. That is the
honest answer to "why do ROM+MAC and per-region perform identically on Qwen", and
any claim that a dense model benefits from per-region activation is wrong on the
face of the design. Differentiation can only appear on the MoE models, which is
why the sizing fault in section 2 was the one that decided the question.

**It is not free ground.** Against the amortising ROM-plus-MAC machine at a
matched floorplan, per-region wins 26 of 30 operating points and **loses 4** —
DeepSeek-Flash at batch 8 (44,793 against 87,123) is the clearest. The previous
version of this document reported it as never losing.

**Under a replicated array the two converge, because neither is weight-bound any
more.** At `spare = rom` on Flash at batch 64 both reach 372,307 tok/s and both
bind on `kv_read`. Per-region's value is specifically in the regime where the
array sweep is what binds; buy your way out of that regime with silicon and the
per-region port earns nothing. That is a design boundary, and it is the one the
study is most useful for finding.

---

## 4. What would falsify this

1. **`rom.cim_cell_area_multiplier` (assumed 1.6×).** It no longer decides
   section 1 — it cancels in the sweep — but it decides how much *capacity* a
   compute-in-ROM die gives up and therefore how many dies a model needs. Nothing
   comparable is published at any node.
2. **Whether per-region activation is realisable at the assumed wiring cost.** A
   circuit question this analysis cannot answer. The 2.0% is the pre-compute block
   only, not the distribution network, and the model prices the network at zero.
3. **`efficiencies.expert_router_imbalance` (assumed 1.0, range 1.0–1.5).** One
   measured routing trace settles it, and every number in section 3 is exactly
   linear in it.
4. **The per-layer serial cost (`latency.*`, seven assumed inputs, 162.4 ns per
   dense layer over a 65.4–726.8 ns range).** On the fastest DeepSeek-Flash design
   at batch 1 it is now the *binding* constraint. Its terms are derived from
   primitives independent of the Taalas anchor — SRAM access time, sequencer issue
   and decode, pipeline fill and drain across a dependent array-pass boundary, the
   layer barrier, and a floorplan-derived wire delay — and the anchor is reported
   at both ends of the band (0.75× low, 0.72× stated, 0.59× high). The per-layer
   cost that would land the model exactly on the published figure is **negative**,
   so no value of this term could have closed the gap and it cannot have been
   fitted to it.
5. **`reference_parts.taalas_hc1.batch_size` (assumed 1).** Published nowhere. If
   HC1's 16,960 tok/s is not a batch-1 figure, the anchor means something
   different and every ratio here moves.

All five are graded `assumed` in `configs/hardware/technology.json` with their
reasons, alongside the other 38 the study's evidence ledger lists.

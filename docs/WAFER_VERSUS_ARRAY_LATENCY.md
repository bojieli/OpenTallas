# Wafer or array: the latency budget decides — and this document's own answer was wrong

> **RETRACTION, 2026-08-30.** Section 3 of the previous version of this document
> concluded that on-wafer tensor parallelism costs *"7.2–12.2 µs, or 12–21% of
> the budget, and fits"*, and called that **"the sharpest argument for
> wafer-scale"**. That conclusion is **inverted**, not merely mis-stated. The
> executable model now charges an on-wafer all-reduce **110.88–187.88 µs** for
> the same three models, which against this document's own 58.8 µs budget is
> **189–319% of it**. On-wafer tensor parallelism does not fit; it misses by
> roughly a factor of two to three.
>
> **The cause is nameable and isolated.** Section 3 charged an on-wafer
> all-reduce **one** hop traversal regardless of how far it reached. A stitched
> 2-D mesh has no switch, so an all-reduce costs about **1.1 × the mesh
> diameter** (Rocki et al., SC20, measured on a Cerebras wafer as *"a cycle
> count only about 10% greater than the diameter of the system"*). For the
> 57-reticle-region span this study models, that is **15.4 traversals**, not 1.
> The 100 ns hop input is unchanged and is still this document's contribution to
> the model; only the traversal count moved.
>
> Two published rates derived from the retracted figures — **116,278 tok/s** and
> **81,966 tok/s** per user, which are the reciprocals of the 8.6 µs and 12.2 µs
> in the old §3 table — are **RETRACTED**. Nothing in this repository supports
> them. The corrected on-wafer hard ceiling is **5,000–9,000 tok/s**.
>
> Everything in the old §5 that followed from "15× the latency headroom" is
> rewritten below. The document's *framing* — that the choice is a crossover to
> be reported rather than a topology to be asserted — survives, and the
> executable model has since adopted it verbatim as a report section.

**Every number in this document now carries a citation.** The previous version
carried 58 numeric tokens, zero `results/` references, zero commands and zero
`src/` references, and that is exactly why its errors survived four model
corrections without being caught. Regenerate everything below with:

```sh
make roofline    # = python3 tools/run_roofline_studies.py --force
```

Unless a row says otherwise, values are read from
[`results/roofline/n5_vs_b200/REPORT.md`](../results/roofline/n5_vs_b200/REPORT.md),
section **"Array or wafer: the crossover, reported rather than assumed"**, and
the row is named by its `Design` cell so the citation survives line-number
drift. The N6/A100 twin is
[`results/roofline/n6_vs_a100/REPORT.md`](../results/roofline/n6_vs_a100/REPORT.md).

---

A wafer is hard to build — stitching, yield, repair, and a thermal object in the
class of a shipping wafer-scale system.<sup>[W]</sup> An array of reticle-class
chips on an NVLink-class fabric is easier to yield, naturally fault-tolerant,
and composable. The question is whether the array can meet the latency budget,
because **decode is sequential across tokens and across layers**, and at batch 1
a pipelined array supplies no parallelism at all: every token still traverses
every layer in order. Pipelining only overlaps *different sequences*.

That reasoning is unchanged and is now built into the model, which states it as
`t_user = token_slots * t_service / stage_balance + t_link`
(`n5_vs_b200/REPORT.md`, "The overlap and serialisation rule"). What changed is
the price of `t_link` on a wafer.

## 1. The budget

| per-user rate | budget per token |
|---:|---:|
| **16,960 tok/s** (Taalas HC1, published) | **58.96 µs** |
| 10,000 | 100 µs |
| 3,000 | 333 µs |
| 1,000 | 1,000 µs |

16,960 tok/s is `configs/hardware/technology.json` →
`reference_parts.taalas_hc1.published_tokens_s_per_user`, graded `published`,
sourced to <https://taalas.com/products/> (Llama 3.1 8B, 1k in / 1k out). The
product page's rounded "17k" is the same number and gives 58.82 µs. The previous
version of this document used the rounded value and a 58.8 µs budget; the
retraction below is stated against **58.8 µs**, which is the number the old
conclusion was measured against, so that the comparison is like for like.

**Hop latencies, all from `configs/hardware/technology.json` → `links`:**

| link | `hop_latency_s` | grade | swept range |
|---|---:|---|---|
| `on_wafer` | **100 ns** | assumed | 30–500 ns |
| `nvlink5` | **1.5 µs** | assumed | 1.0–5.5 µs |
| `infiniband_ndr` | **4.5 µs** | published | 3.7–5.7 µs |
| `inter_wafer` | **5.0 µs** | assumed | 1.0–10.0 µs |
| `ethernet` | **5.0 µs** | assumed | 2.0–10.0 µs |

Two of these rows cite *this document* as their source (`on_wafer` and
`ethernet`), so its inputs are load-bearing in the model even though its
arithmetic was not. The `on_wafer` note now carries an independent cross-check
it did not have before: Cerebras publishes one clock per tile hop and ~900,000
cores over 46,225 mm², about 73 tiles across an 815 mm² reticle field, so a
reticle crossing is on the order of 73 cycles.

`nvlink5` is a **per-traversal** cost and a switched all-reduce is charged two
traversals, so the stated 1.5 µs is a **3.0 µs in-domain all-reduce**. The old
version of this document charged 1.5 µs for the whole all-reduce, so its NVLink
column was also 2× low — a smaller error in the same direction as the on-wafer
one, and it did not change that column's conclusion.

## 2. Pipeline parallel: N−1 serial hops per token, capped by the layer count

The old §2 table extrapolated `(N−1) × 1.5 µs` to N = 112. That extrapolation is
wrong for a reason the model now enforces: **a token cannot cross more stage
boundaries than the model has layers.** Qwen3-8B has 36 layers, so at most 35
boundaries can exist; the rest of a larger cluster is replication, which adds
bandwidth and no serial event.

Measured rows, B200 pipeline on Qwen3-8B, `nvlink5` inside an 8-GPU domain and
`infiniband_ndr` across domains:

| design | devices | hops/token | link latency/token | % of 58.8 µs | viable to (10% budget) | hard ceiling |
|---|---:|---:|---:|---:|---:|---:|
| `Qwen3-8B/b200_sxm-x2-pipeline` | 2 | 1 | 1.51 µs | 3% | 66,264.6 tok/s | 662,645.6 tok/s |
| `Qwen3-8B/b200_sxm-x4-pipeline` | 4 | 3 | 4.53 µs | 8% | 22,088.2 tok/s | 220,881.9 tok/s |
| `Qwen3-8B/b200_sxm-x29-pipeline` | 29 | 28 | 51.72 µs | 88% | 1,933.5 tok/s | 19,335.2 tok/s |
| `Qwen3-8B/b200_sxm-x58-pipeline` | 58 | **35 (capped)** | 65.44 µs | **111%** | 1,528.2 tok/s | 15,281.8 tok/s |
| `Qwen3-8B/b200_sxm-x347-pipeline` | 347 | **35 (capped)** | 65.44 µs | **111%** | 1,528.2 tok/s | 15,281.8 tok/s |

The qualitative claim survives and the numbers move. At Taalas-class speed a
56-chip array is still not available on a pipeline — but the overrun is
**11%**, not the 40% the old table asserted, and it stops growing at 58 devices
instead of doubling again at 112. At 3,000 tok/s the same array costs 20% of the
budget and at 1,000 tok/s it costs 7%, which is a design cost rather than a
wall. The old table's
`N=112 → 283%` cell is **retracted**: no array of any size can charge Qwen3-8B
more than 35 pipeline hops.

## 3. Tensor parallel: the retracted section

Tensor parallelism needs two all-reduces per layer, every token, *regardless of
how few devices it is spread over*. That much is unchanged, and it is
`docs/METHODOLOGY.md` §6.

| model | layers | collectives/token | **on-wafer** | **NVLink array** | on-wafer as % of 58.8 µs |
|---|---:|---:|---:|---:|---:|
| Qwen3-8B | 36 | 72 | **110.88 µs** | **217.31 µs** | **189%** |
| DeepSeek-V4-Flash | 43 | 86 | **132.44 µs** | **1,055.19 µs** | **225%** |
| DeepSeek-V4-Pro | 61 | 122 | **187.88 µs** (on-wafer term only) | **1,562.38 µs** | **319%** |

On-wafer rows: `Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1`,
`DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1`,
`DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x2`. Array rows:
`Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x3`,
`DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x14`,
`DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x72`. Each row's `Events` cell
spells out the arithmetic, e.g. `72 x all_reduce span 57 on on_wafer
(traversals 15.4) = 110.88 us`.

**Pro does not fit on one wafer, and the honest total is worse than the table
suggests.** Its ROM array is 52.6 reticle fields at N5 (§4), so a tensor group
spans two wafers and pays `inter_wafer` as well: 187.88 µs on-wafer **plus**
1,237.49 µs across the wafer boundary = **1,425.37 µs**, a hard ceiling of
**701.6 tok/s**. Charging that link the on-wafer 100 ns hop — which this study
previously did — is the ROM-side mirror of charging a GPU cluster a 672-way
pipeline.

**The corrected conclusion.** On-wafer tensor parallelism is *better than
NVLink* and is *not good anywhere*. The ordering survives; the fit does not. The
hard ceilings are:

| | on-wafer hard ceiling | NVLink-array hard ceiling |
|---|---:|---:|
| Qwen3-8B | 9,018.8 tok/s | 4,601.7 tok/s |
| DeepSeek-V4-Flash | 7,550.6 tok/s | 947.7 tok/s |
| DeepSeek-V4-Pro | 701.6 tok/s | 640.0 tok/s |

That band — **5,000–9,000 tok/s** for the two models that fit on one wafer — is
the replacement for the retracted 116,278 / 81,966 tok/s. The report states the
retraction itself as finding 8 (`n5_vs_b200/REPORT.md`, "What the model says"),
and a test pins it:
`tests/test_roofline.py::test_on_wafer_tensor_parallelism_no_longer_reaches_taalas_rates`.

**What the collective still buys, and why anything pays it.** Once per-user
latency is separated from aggregate throughput, a tensor group is the *only*
arrangement that puts a whole machine on one token: under pipeline parallelism
each of N stages holds 1/N of the weights and reads them with 1/N of the
bandwidth, so the two factors cancel exactly and adding devices buys aggregate
throughput and buys one user nothing. Both families therefore still choose a
tensor group at batch 1 in spite of this cost
(`n5_vs_b200/REPORT.md`, "Topology choice at each operating point").

## 4. The result, per model

ROM array area at the **released packing only** — the study no longer prices a
re-encoding on either side, and the FP8 rows the old version of this table
carried are retracted with it (see `docs/FIRST_PRINCIPLES_MEMORY_DESIGN.md` §5).
Checkpoint bytes and bits/parameter are
`n5_vs_b200/REPORT.md` → "Models and their work"; ROM capacity density is
`n5_vs_b200/REPORT.md` → "Derived technology at N5" = **20.833 MB/mm²**
(16.204 MB/mm² at N6); the reticle field is 815 mm²
(`configs/hardware/technology.json` → `reticle.area_mm2`).

| model | checkpoint | bits/param | ROM array @N5 | reticles | array design the study builds | array viable to |
|---|---:|---:|---:|---:|---|---:|
| Qwen3-8B | 16.4 GB | 16.00 | 786 mm² | **1.0** | `…array-pipeline-x3`, 3 devices, 2 hops, 3.02 µs | **33,132.3 tok/s** |
| DeepSeek-V4-Flash | 166.9 GB | 4.70 | 8,010 mm² | **9.8** | `…array-pipeline-x14`, 14 devices, 13 hops, 22.77 µs | **4,391.2 tok/s** |
| DeepSeek-V4-Pro | 892.7 GB | 4.46 | 42,852 mm² | **52.6** | `…array-pipeline-x74`, 74 devices, 60 hops, 113.85 µs | **878.3 tok/s** |

The device counts are larger than the ROM area alone implies because a design
also has to carry compute, KV store and beachfront; they are the counts the
study's own design generator produced, not a division I performed.

Three of the old §4 numbers moved and one claim changed shape:

- Flash: **10 chips → 14**, **7,400 tok/s → 4,391.2**;
- Pro: **53 chips → 74**, **1,280 tok/s → 878.3**;
- Qwen3-8B: the old row said **416 mm², one chip, no distribution needed**. That
  416 mm² was an **FP8 re-encoding of a BF16 release** and is retracted. At the
  released BF16 packing Qwen3-8B is **786 mm² of ROM at N5 — still one reticle
  field, but only just — and 1,011 mm² at N6, which is two.** The smallest
  Qwen design either study actually builds is three reticle chips
  (`Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x3`, 2,445 mm²). "No distribution
  needed" is true at N5 for the ROM array alone and false for a whole machine.

**A composable array remains viable for all three targets at their realistic
decode rates**, and that part of the old conclusion stands — but the previous
version measured it against per-model budgets of 308 µs and 926 µs that nothing
produced, so it is restated against the model's own threshold instead. The
`Array viable to` column *is* the 10%-of-budget rate: Flash over fourteen chips
spends 10% of the token budget at 4,391.2 tok/s and all of it at 43,911.5;
Pro over seventy-four spends 10% at 878.3 tok/s and all of it at 8,783.4. Below
the first number the interconnect is a design cost; above the second the
topology cannot deliver the rate at all.

## 5. What this changes — rewritten

The old §5 offered a choice in which the wafer bought *"15× the latency
headroom"*. **That figure is retracted.** The model reports the wafer/array
per-user ratio directly, at batch 1, each side on its own best design
(`REPORT.md` → "Topology choice at each operating point", `Wafer/array` column):

| | N5 vs B200 | N6 vs A100 |
|---|---:|---:|
| Qwen3-8B | **1.61×** | **2.15×** |
| DeepSeek-V4-Flash | **2.61×** | **2.97×** |
| DeepSeek-V4-Pro | **3.39×** | **3.91×** |

On collective cost alone, like for like, the report states the wafer is *"at
least 2.0× cheaper"* (finding 8). The per-model collective ratios follow from
the §3 table by division — Qwen 217.31/110.88 = **1.96×**, Flash
1,055.19/132.44 = **7.97×**, Pro 1,562.38/1,425.37 = **1.10×** — and note that
Pro's is barely better than one, because its wafer machine pays an inter-wafer
link the array does not have. A claim elsewhere in this repository that the
wafer is 8.3× cheaper on Flash and 8.9× on Pro has **no producer**; those
per-model values appear in neither study report.

- **Array of reticle chips** — better yield, fault-tolerant to single-chip
  failure, composable, incrementally purchasable. Caps per-user decode at the
  §4 rates, and forecloses tensor parallelism above ~600–4,600 tok/s.
- **Wafer** — **1.6–3.9× the per-user rate**, tensor parallelism available but
  **not at Taalas-class rates**, and the only route to a per-user rate an array's
  hop count forbids. Costs stitching, yield, repair, and a thermal object in the
  class of a shipping wafer-scale system.<sup>[W]</sup>

**Which one wins depends on what is being maximised, and the study reports both
rather than choosing.** On per-user rate at equal area the wafer wins **24 of
24** operating points in both studies. On tokens per second per square
millimetre the same points split **11 array / 13 wafer** at N5-vs-B200 and
**20 array / 4 wafer** at N6-vs-A100 (finding 9 in each report). So the old §5's
*"the array is the better default for the large models"* is now **half right and
half inverted**: it is right per unit silicon, and wrong per user, and it was
stated as though those were the same quantity. They are not — separating them
was the single largest correction in the study.

The wafer also has a structural disadvantage the old version of this document
never mentioned: perimeter grows as the square root of area, so HBM beachfront —
and therefore KV bandwidth — does not scale with wafer area the way compute and
ROM capacity do. 318 of 3,016 feasible points at N5 bind on `kv_read` for that
reason (finding 10).

**Caveat.** These are hop-latency floors plus the model's payload
serialisation. They ignore switch contention and the pipeline fill cost at batch
1. Each of those makes the array worse, never better, so the crossover rates
above remain upper bounds on where the array stays viable.

---

<sup>[W]</sup> **Power figure withdrawn.** The previous version of this document
quoted a *"15–23 kW thermal object"* twice. That number is a system-level figure
for a shipping wafer-scale part and appears in this repository only as a
cross-check note inside `configs/hardware/technology.json` →
`thermal.cooling_limit_w_per_mm2.note`; it is not an output of anything. The
project's own power model is separately known to be **7–9× low** and is being
rebuilt, and no watt from it is publishable. Both quotations are therefore
replaced by the qualitative statement above until a power model lands.

## What nothing produces

Listed rather than filled in, per the rule that a gap is not an invitation to
invent a figure.

- **The 300 ns on-package chiplet hop** in the old §1. It is a registered input —
  `configs/hardware/technology.json` → `links.on_package.hop_latency_s`, graded
  `assumed`, swept 100 ns–1 µs, and sourced (like the on-wafer and Ethernet hops)
  to *this document* — and it appears in both roofline reports only inside their
  assumed-inputs ledger, at `links.on_package.hop_latency_s`. **No design row in
  either study exercises it**, so no report line prices it. It is an input with
  no consumer, and the 300 ns has never been checked against anything.
- **A per-model "wafer is N× cheaper on the collective" figure** as an artifact
  field. The reports state only "at least 2.0×"; the per-model ratios in §5 are
  my division of two cited cells and are labelled as such.

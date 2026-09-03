# Wafer or array: the latency budget decides — and this document's own answer was wrong

> **RETRACTION, 2026-08-30.** Section 3 of the previous version of this document
> concluded that on-wafer tensor parallelism costs *"7.2–12.2 µs, or 12–21% of
> the budget, and fits"*, and called that **"the sharpest argument for
> wafer-scale"**. That conclusion is **inverted**, not merely mis-stated. The
> executable model now charges an on-wafer all-reduce **138.60–234.85 µs** for
> the same three models, which against this document's own 58.8 µs budget is
> **236–399% of it**. On-wafer tensor parallelism does not fit; it misses by
> roughly a factor of two to four.
>
> **The cause is nameable and isolated.** Section 3 charged an on-wafer
> all-reduce **one** hop traversal regardless of how far it reached. A stitched
> 2-D mesh has no switch, so an all-reduce costs about **1.1 × the mesh
> diameter** (Rocki et al., SC20, measured on a Cerebras wafer as *"a cycle
> count only about 10% greater than the diameter of the system"*). For the
> 57-reticle-region span this study models, that is **15.4 traversals**, not 1.
> When this retraction was written the 100 ns hop input was unchanged and was
> still this document's contribution to the model. **On 2026-08-31 it stopped
> being ours**: `links.on_wafer.hop_latency_s` is now **125 ns, graded
> `derived`**, from Cerebras' published core grid and clock and Tesla's
> published reticle-die crossing, swept 75–250 ns instead of 30–500 ns. §1
> carries the derivation. The re-grading moved the number *up* by 25%, so the
> figures in this banner are, if anything, understated — they are the ones the
> retraction was written against and are left as they were so the comparison
> stays like for like.
>
> Two published rates derived from the retracted figures — **116,278 tok/s** and
> **81,966 tok/s** per user, which are the reciprocals of the 8.6 µs and 12.2 µs
> in the old §3 table — are **RETRACTED**. Nothing in this repository supports
> them. The corrected on-wafer hard ceiling is **6,000–7,200 tok/s** at the
> re-graded 125 ns hop (it was quoted as 5,000–9,000 tok/s at 100 ns).
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
| **16,960 tok/s** (Taalas HC1, published) | **58.96 µs** | <!-- figure: 16,960 src="configs/hardware/technology.json#reference_parts.taalas_hc1.published_tokens_s_per_user.value" name="Taalas HC1 published per-user rate (input echo)" -->
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
| `on_wafer` (N7, WSE-2) | **125 ns** | **derived** | 75–250 ns | <!-- figure: 125 src="configs/hardware/technology.json#links.on_wafer.hop_latency_s.value" scale="1e9" name="on_wafer hop latency, ns" -->
| `on_wafer_n5` (N5, WSE-3) | **125 ns** | **derived** | 75–250 ns | <!-- figure: 125 src="configs/hardware/technology.json#links.on_wafer_n5.hop_latency_s.value" scale="1e9" name="on_wafer_n5 hop latency, ns" -->
| `nvlink5` | **1.2 µs** | **derived** | 0.7–5.5 µs | <!-- figure: 1.2 src="configs/hardware/technology.json#links.nvlink5.hop_latency_s.value" scale="1e6" name="nvlink5 hop latency, us" -->
| `infiniband_ndr` | **2.03 µs** | **measured** | 1.9–22 µs | <!-- figure: 2.03 src="configs/hardware/technology.json#links.infiniband_ndr.hop_latency_s.value" scale="1e6" name="infiniband_ndr hop latency, us" -->
| `inter_wafer` | **5.0 µs** | assumed | 1.0–10.0 µs | <!-- figure: 5.0 src="configs/hardware/technology.json#links.inter_wafer.hop_latency_s.value" scale="1e6" name="inter_wafer hop latency, us" -->
| `ethernet` | **5.0 µs** | assumed | 2.0–10.0 µs | <!-- figure: 5.0 src="configs/hardware/technology.json#links.ethernet.hop_latency_s.value" scale="1e6" name="ethernet hop latency, us" -->

**The wafer rows changed on 2026-08-31 and no longer cite this document.**
`on_wafer` was 100 ns graded `assumed` and swept 30–500 ns; `nvlink5` (and its
`nvlink3` twin, which the N6/A100 study uses) was 1.5 µs graded `assumed` and
swept 1.0–5.5 µs. Neither is a judgement any more, and neither re-grading is a
correction that only flatters us: the wafer hop went **up** 25%, `nvlink5` went
**down** 20%, and its A100-generation twin `nvlink3` went up to 2.5 µs. The
intermediate ratios those changes produced are now superseded by the scale-out
correction below; they are not current study results.

**The scale-out hop was corrected later the same day.** Both HDR and NDR had
carried 4.5 µs under a note that assigned an Alps measurement to Leonardo.
Leonardo, the A100 + HDR InfiniBand system the source actually measured, reports
2.03 µs within a switch. The point is therefore 2.03 µs, graded `measured`, and
the range is 1.9–22 µs: the measured minimum to the small-message collective
cost of the shipped library. No NDR system appears in that study, so the NDR
entry explicitly transfers the HDR measurement. Carrying it unchanged does not
invent an unmeasured NDR speed-up and therefore under-credits the newer fabric.
This correction makes every array that crosses a domain faster; §5 reports the
current ratios. `ethernet` and `on_package` still cite this document, and
`ethernet` is exercised by no design in either study.

**`on_wafer_n5` was split out of `on_wafer` later the same day, and it is a
null result.** Until then one wafer constant served **both** studies while the
GPU side already had two — `nvlink3` at 2.5 µs for the A100/N7 study,
`nvlink5` at 1.2 µs for the B200/4NP study. `on_wafer` is derived from Cerebras
WSE-2, a **TSMC 7 nm** part, so the N6/N7 study was correctly matched and the
N5/4NP study was not: it charged the ROM side a 7 nm-era wafer fabric against a
4 nm-era NVLink, which understates the ROM side in the study where it should be
strongest. The wafer fabric is now node-keyed too, and each study names its own
(`tools/run_roofline_studies.py` → `STUDIES[…]["rom_intra_link"]`, pinned by
`tests/test_roofline.py::test_each_study_charges_a_wafer_fabric_of_its_own_node`).
**The N5 entry lands on the same 125 ns**, and the next subsection derives why
rather than asserting it. The direction matters and is therefore stated: a
faster N5 wafer fabric would have *raised* every ratio a wafer design appears
in — §6's N5 wafer-fabric band runs 3.76× → 1.66× at 554,700 mm², so this
constant is worth about 2.3× there — and the derivation does not support one.
It would not have moved the N5 study's own headline point at all, which is an
`array` design on NVLink that touches no wafer fabric; the null is a null on
the band, not merely on a number that was already insensitive.

**What the model charges an `on_wafer` hop for, and what the sources measured.**
The model's hop is one step between adjacent **815 mm² reticle fields** — a
28.55 mm square, 57 to a wafer. It is *not* a tile-to-tile hop, and getting that
wrong is a factor of 125 in the ROM side's favour — at the revision that exposed
the bug it took the headline iso-area ratio from 8.33× to 14.7× — because the single clock cycle
Cerebras publishes is a hop between **adjacent cores about 0.23 mm apart**, and
there are ~126 of those across one of this model's fields. The transferable
primitive is "one cycle per router pitch", published for a shipping part (WSE-3
white paper, *"This design enables single clock cycle latency between nodes"*;
Hot Chips 34, *"Single cycle latency between cores"*) and independently stated
on fabricated silicon by four peer-reviewed groups. The field crossing is then
`(28.55 mm / core pitch) cycles / clock`, and Cerebras publishes the core pitch
outright at Hot Chips 34 — die "17mm x 30mm", "66 x 154 Cores", core
"228um x 170um":

| part | node | core pitch | hops across 815 mm² | clock | field crossing |
|---|---|---:|---:|---|---:|
| CS-1 / WSE-1 (Rocki Fig. 2, 89 × 51 tiles) | 16 nm | 0.348 mm | 82 | 0.85–1.1 GHz | **75–97 ns** |
| WSE-2 (HC34 published grid) | N7 | 0.224 mm | 127 | 0.85–1.1 GHz | **116–150 ns** |
| WSE-3, 46,225 mm² / 900,000 **active** cores | N5 | 0.227 mm | 126 | 0.85–1.1 GHz | **115–148 ns** |
| WSE-3, 46,225 mm² / 970,000 **physical** cores | N5 | 0.218 mm | 131 | 0.85–1.1 GHz | **119–154 ns** |
| WSE-3, published core area 38,000 µm² at WSE-2's fill | N5 | 0.222 mm | 129 | 0.85–1.1 GHz | **117–152 ns** |
| Tesla Dojo D1, bonded reticle die (HC34: *"100ns die-to-die latency"*) | N7 | — | — | 2 GHz | **~111 ns** |

Two **measured** end-to-end results land inside that band and neither was used
to set it: Rocki et al.'s full-wafer scalar AllReduce over ~380,000 processors
takes *"under 1.5 microseconds"*, which through this model's own 15.4 traversals
at span 57 is **≤ 97 ns** per field crossing; and Santos et al. (SC24) state a
wafer edge-to-edge latency *"of around a microsecond"*, which the published
geometry reproduces without adjustment (7 × 154 = 1,078 hops at 850 MHz =
1.27 µs). **125 ns** is the middle of the two routes available at N7 — Cerebras
stitched, Tesla bonded — and it is 25% *above* the 100 ns this document used to
supply.

**And the same method at N5 gives the same answer, which is the null result.**
Cerebras publishes **no** WSE-3 geometry: the Hot Chips 2024 successor to the
slide that carried "17mm x 30mm", "66 x 154 Cores", "228um x 170um", "12 x 7
Die" and "215mm x 215mm" carries only three labels — "10.7k Cores", "84 Die",
"900k Cores" — so the last three rows above are *estimators*, not a published
pitch, and they bracket the N7 figure of 127 hops at **126–131**. They point
1–3% the *wrong* way. The reason is physical rather than accidental: latency
across a fixed 28.55 mm is `(distance / router pitch) × 1 cycle`, so a *smaller*
core puts **more** routers across the same millimetre and costs **more** cycles.
Process scaling buys a mesh cores, not distance — and Cerebras spent the
N7→N5 shrink on the core rather than on the pitch, keeping 48 kB of SRAM,
110,000 standard cells and a 50/50 logic-to-SRAM split while doubling the FP16
SIMD from 4-wide to 8-wide.

That leaves the clock, and it did not move either. Cerebras publishes **1.1 GHz**
for WSE-2 (Hot Chips 34, *"Power efficient design point … 1.1GHz clock
frequency"*) and publishes **no WSE-3 clock in any document** — not the Hot
Chips 36 deck, not the 2024 white paper, not the press release, not the product
page. Two back-derivations from figures Cerebras *does* publish, each calibrated
on WSE-2 where the answer is known, converge:

| route | WSE-2 (N7) | published WSE-2 | method bias | WSE-3 (N5) | WSE-3 corrected |
|---|---:|---:|---:|---:|---:|
| memory BW / cores / 24 B per cycle | 20 PB/s ÷ 850,000 ÷ 24 = 0.98 GHz | 1.1 GHz | 1.12× | 21 PB/s ÷ 900,000 ÷ 24 = 0.97 GHz | **1.09 GHz** |
| fabric BW / cores / 256 bit per cycle | 220 Pb/s ÷ 850,000 ÷ 256 = 1.01 GHz | 1.1 GHz | 1.09× | 214 Pb/s ÷ 900,000 ÷ 256 = 0.93 GHz | **1.01 GHz** |

(The 24 B per cycle is Cerebras' own *"192-bit access per cycle from two 64-bit
reads and one 64-bit write"*; the 256 bit is its five-port router's *"32-bit
bidirectional interfaces in each of the four cardinal directions"*. On the
21.6 PB/s that the CS-4 datasheet's 43.2 PB/s implies for exactly half a WSE-3
Turbo, the memory route reads 1.00 GHz and corrects to 1.12.)

1.01–1.12 GHz at N5 against 1.1 GHz published at N7 is flat inside a method
whose own error on the calibration part is 9–12%. The **1.4 GHz** that 2026
press reports quote for WSE-3 has no vendor source — it is a journalist's
explicitly hedged inference (*"I think"*, The Next Platform, 19 August 2026)
back-read from the CS-4 launch — and it is not used.

The bonded route is offered at **both** nodes. No bonded wafer-scale part has
been published at N5, and withholding Tesla's 111 ns from the N5 entry would put
it at the stitched-only midpoint of ~132 ns and make N5 look *worse* than N7 —
but that would be applying a different method at the two nodes, and two figures
derived two ways are not comparable, which is the whole reason for splitting the
entry. A bonded reticle interface is a packaging choice, not a property of the
logic node.

So the two nodes are stated equal, and the 1.6% the median estimator says the
N5 hop is *slower* is a credit to this study's own side, recorded so it is not
mistaken for a correction that went our way. Regenerating both studies with the
split in place moves **no number in either report** except the evidence-ledger
counts: same headlines, same per-side bands, same four gates to the digit.

**The split is live rather than cosmetic.** The regression test perturbs each
wafer link independently and requires only its matching study to move; §6's
separate wafer-fabric bands are the committed numerical result. Earlier
one-off probe values are omitted because no artifact carried them and the later
scale-out correction changed their baselines. The conclusion that matters is
stable: an N5-specific wafer speed-up would help only the N5 study, which is why
the derivation had to be done rather than chosen.

**WITHDRAWN.** The previous version of this section said the `on_wafer` note
*"now carries an independent cross-check it did not have before: … about 73
tiles across an 815 mm² reticle field, so a reticle crossing is on the order of
73 cycles."* That arithmetic does not reproduce. 900,000 cores over 46,225 mm²
is 15,868 cores in 815 mm², and √15,868 = **126**, not 73. The error was 1.7×
and it ran in this study's favour: it made 100 ns look like a comfortable
over-estimate when the same inputs, done correctly, make it a mild
under-estimate.

**The band, 75–250 ns, and what its ends mean.** The low end is the coarsest
tile pitch any wafer-scale part has shipped at the fastest clock any vendor has
published — and it is a live possibility rather than a formality, because a ROM
region is a mask-ROM array and not a 38,000 µm² processing element, so a
purpose-built design may put fewer routers across the same millimetres. The high
end is **not a slower wire**: it is the same wire under the collective Cerebras'
SDK actually ships. Luczynski et al. measure a corner-rooted X-Y AllReduce whose
path is ~2× the mesh diameter, against the 1.1× diameter this model charges from
Rocki's hand-written kernel; 1.8× on the traversal count, folded into the hop
because the model has no term for the collective algorithm, is ~230 ns. The old
30–500 ns sweep is retired: 30 ns needs 1.05 ns/mm, three times faster than the
fastest axis any wafer-scale part has ever shipped, and 500 ns is above every
measurement in the literature.

**`nvlink5` is a per-traversal cost and a switched all-reduce is charged two
traversals**, so the stated 1.2 µs is a **2.4 µs in-domain all-reduce** — which
is the 2.37 µs best device-initiated kernel measured on a GB200 NVL72, halved.
The band's ends are the measured speed-of-light floor (1.404 µs, halved) and
stock NCCL's measured ring (11.0 µs, halved). Its A100-generation twin
`nvlink3`, which the N6 study charges, is set the same way from an 8×A100
measurement: 2.5 µs stated (best measured kernel 5.0 µs ÷ 2), swept
1.0–10.3 µs (stock NCCL's measured 20.6 µs ÷ 2). The previous note on all three
entries claimed *"NVIDIA publishes no NVLink or NVSwitch latency figure in any
form"*; that is **withdrawn** — NCCL's shipping source carries
`hwLatencies[NVLINK][Ring][LL] = 0.6 µs` per ring step. The old version of this
document charged 1.5 µs for the whole all-reduce rather than per traversal, and
that error stands corrected as before.

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
| `Qwen3-8B/b200_sxm-x2-pipeline` | 2 | 1 | 1.21 µs | 2% | 82,706.0 tok/s | 827,059.9 tok/s | <!-- figure: 1.21 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x2-pipeline" name="B200 x2 pipeline link latency/token" --> <!-- figure: 82,706.0 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x2-pipeline" name="B200 x2 pipeline viable to" --> <!-- figure: 827,059.9 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x2-pipeline" name="B200 x2 pipeline hard ceiling" -->
| `Qwen3-8B/b200_sxm-x4-pipeline` | 4 | 3 | 3.63 µs | 6% | 27,568.7 tok/s | 275,686.6 tok/s | <!-- figure: 3.63 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x4-pipeline" name="B200 x4 pipeline link latency/token" --> <!-- figure: 27,568.7 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x4-pipeline" name="B200 x4 pipeline viable to" --> <!-- figure: 275,686.6 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x4-pipeline" name="B200 x4 pipeline hard ceiling" -->
| `Qwen3-8B/b200_sxm-x29-pipeline` | 29 | 28 | 36.81 µs | 63% | 2,716.7 tok/s | 27,167.2 tok/s | <!-- figure: 36.81 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x29-pipeline" name="B200 x29 pipeline link latency/token" --> <!-- figure: 2,716.7 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x29-pipeline" name="B200 x29 pipeline viable to" --> <!-- figure: 27,167.2 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x29-pipeline" name="B200 x29 pipeline hard ceiling" -->
| `Qwen3-8B/b200_sxm-x58-pipeline` | 58 | **35 (capped)** | 46.26 µs | **79%** | 2,161.8 tok/s | 21,618.1 tok/s | <!-- figure: 46.26 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x58-pipeline" name="B200 x58 pipeline link latency/token" --> <!-- figure: 2,161.8 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x58-pipeline" name="B200 x58 pipeline viable to" --> <!-- figure: 21,618.1 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x58-pipeline" name="B200 x58 pipeline hard ceiling" -->
| `Qwen3-8B/b200_sxm-x347-pipeline` | 347 | **35 (capped)** | 46.26 µs | **79%** | 2,161.8 tok/s | 21,618.1 tok/s | <!-- figure: 46.26 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x347-pipeline" name="B200 x347 pipeline link latency/token" --> <!-- figure: 2,161.8 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x347-pipeline" name="B200 x347 pipeline viable to" --> <!-- figure: 21,618.1 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x347-pipeline" name="B200 x347 pipeline hard ceiling" -->

The qualitative claim survives, but the 2.03 µs scale-out correction gives the
array materially more room. At Taalas-class speed a 58-device array spends
**79%** of the budget on its pipeline. It stops growing at 58 devices instead
of doubling again at 112 because the 35 layer boundaries are already exhausted.
At 3,000 tok/s the same array costs **14%** of the budget and at 1,000 tok/s
**5%**, which is a design cost rather than a wall. The old table's
`N=112 → 283%` cell is **retracted**: no array of any size can charge Qwen3-8B
more than 35 pipeline hops.

## 3. Tensor parallel: the retracted section

Tensor parallelism needs two all-reduces per layer, every token, *regardless of
how few devices it is spread over*. That much is unchanged, and it is
`docs/METHODOLOGY.md` §6.

| model | layers | collectives/token | **on-wafer** | **NVLink array** | on-wafer as % of 58.8 µs |
|---|---:|---:|---:|---:|---:|
| Qwen3-8B | 36 | 72 | **138.60 µs** | **174.37 µs** | **236%** | <!-- figure: 138.60 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1" name="Qwen on-wafer tensor link latency/token" --> <!-- figure: 174.37 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x5" name="Qwen NVLink tensor link latency/token" -->
| DeepSeek-V4-Flash | 43 | 86 | **165.55 µs** | **589.32 µs** | **282%** | <!-- figure: 165.55 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1" name="Flash on-wafer tensor link latency/token" --> <!-- figure: 589.32 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x29" name="Flash NVLink tensor link latency/token" -->
| DeepSeek-V4-Pro | 61 | 122 | **234.85 µs** (on-wafer term only) | **892.91 µs** | **399%** | <!-- figure: 892.91 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x155" name="Pro NVLink tensor link latency/token" -->

On-wafer rows: `Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1`,
`DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1`,
`DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x3`. Array rows:
`Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x5`,
`DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x29`,
`DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x155`. Each row's `Events` cell
spells out the arithmetic, e.g. `72 x all_reduce span 57 on on_wafer
(traversals 15.4) = 138.60 us`.

**Pro does not fit on one wafer, and the honest total is worse than the table
suggests.** Its current N5 tensor machine spans three wafers and pays
`inter_wafer` as well: 234.85 µs on-wafer **plus** 1,243.32 µs across wafer
boundaries = **1,478.17 µs**, a hard ceiling of <!-- figure: 1,478.17 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x3" name="Pro three-wafer tensor link latency/token" -->
**676.5 tok/s**. Charging that link the on-wafer stitched-mesh hop — which this
study previously did — is the ROM-side mirror of charging a GPU cluster a
672-way pipeline. Note what the re-grading did here: raising the on-wafer hop by
25% moved this design's total by only 3%, because 84% of it is the `inter_wafer`
link, which is still `assumed` at 5.0 µs and is now the largest unmeasured
number left on the ROM side.

**The corrected conclusion.** A tensor collective contained on one wafer is
better than the corresponding switched array and is *not good anywhere* at
Taalas-class rates. Once capacity forces Pro across three wafers, the
inter-wafer term reverses even that ordering. The hard ceilings are:

| | on-wafer hard ceiling | NVLink-array hard ceiling |
|---|---:|---:|
| Qwen3-8B | 7,215.0 tok/s | 5,734.8 tok/s | <!-- figure: 7,215.0 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1" name="Qwen on-wafer tensor hard ceiling" --> <!-- figure: 5,734.8 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x5" name="Qwen NVLink tensor hard ceiling" -->
| DeepSeek-V4-Flash | 6,040.5 tok/s | 1,696.9 tok/s | <!-- figure: 6,040.5 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1" name="Flash on-wafer tensor hard ceiling" --> <!-- figure: 1,696.9 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x29" name="Flash NVLink tensor hard ceiling" -->
| DeepSeek-V4-Pro | 676.5 tok/s | 1,119.9 tok/s | <!-- figure: 676.5 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x3" name="Pro three-wafer tensor hard ceiling" --> <!-- figure: 1,119.9 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x155" name="Pro NVLink tensor hard ceiling" -->

That band — **6,000–7,200 tok/s** for the two models that fit on one wafer — is
the replacement for the retracted 116,278 / 81,966 tok/s. It narrowed from
5,000–9,000 tok/s when the on-wafer hop was re-graded upward from 100 to
125 ns. The report states the
retraction itself as finding 9 (`n5_vs_b200/REPORT.md`, "What the model says"),
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
`n5_vs_b200/REPORT.md` → "Derived technology at N5" = **9.380 MB/mm²**
(7.295 MB/mm² at N6); the reticle field is 815 mm²
(`configs/hardware/technology.json` → `reticle.area_mm2`).

| model | checkpoint | bits/param | ROM array @N5 | reticles | array design the study builds | array viable to |
|---|---:|---:|---:|---:|---|---:|
| Qwen3-8B | 16.4 GB | 16.00 | 1,747 mm² | **2.1** | `…array-pipeline-x5`, 5 devices, 4 hops, 4.84 µs | **20,676.5 tok/s** | <!-- figure: 16.4 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=Qwen3-8B].checkpoint_bytes" scale="1e-9" name="Qwen checkpoint, GB" --> <!-- figure: 16.00 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=Qwen3-8B].native_bits_per_parameter" name="Qwen bits/param" --> <!-- figure: 4.84 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x5" name="Qwen array pipeline link latency/token" --> <!-- figure: 20,676.5 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x5" name="Qwen array pipeline viable to" -->
| DeepSeek-V4-Flash | 166.9 GB | 4.70 | 17,792 mm² | **21.8** | `…array-pipeline-x30`, 30 devices, 29 hops, 38.02 µs | **2,630.3 tok/s** | <!-- figure: 166.9 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].checkpoint_bytes" scale="1e-9" name="Flash checkpoint, GB" --> <!-- figure: 4.70 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].native_bits_per_parameter" name="Flash bits/param" --> <!-- figure: 38.02 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x30" name="Flash array pipeline link latency/token" --> <!-- figure: 2,630.3 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x30" name="Flash array pipeline viable to" -->
| DeepSeek-V4-Pro | 892.7 GB | 4.46 | 95,178 mm² | **116.8** | `…array-pipeline-x159`, 159 devices, 60 hops, 80.66 µs | **1,239.8 tok/s** | <!-- figure: 892.7 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].checkpoint_bytes" scale="1e-9" name="Pro checkpoint, GB" --> <!-- figure: 4.46 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].native_bits_per_parameter" name="Pro bits/param" --> <!-- figure: 80.66 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x159" name="Pro array pipeline link latency/token" --> <!-- figure: 1,239.8 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x159" name="Pro array pipeline viable to" -->

The device counts are larger than the ROM area alone implies because a design
also has to carry compute, KV store and beachfront; they are the counts the
study's own design generator produced, not a division I performed.

The corrected cell-to-SRAM ratio and macro efficiency make every bare ROM
larger than the previous revision reported. Qwen3-8B alone now needs **2.1 N5
reticles** (2.8 at N6), so the old claim that its released checkpoint needs no
distribution is false even before compute, KV storage, and interfaces are
added. Flash needs 21.8 bare reticles and its emitted pipeline uses 30; Pro
needs 116.8 and its emitted pipeline uses 159. Those are generated floorplans,
not checkpoint-area divisions presented as complete machines.

**A composable array remains viable for all three targets at their realistic
decode rates**, and that part of the old conclusion stands — but the previous
version measured it against per-model budgets of 308 µs and 926 µs that nothing
produced, so it is restated against the model's own threshold instead. The
`Array viable to` column *is* the 10%-of-budget rate: Flash over thirty chips
spends 10% of the token budget at 2,630.3 tok/s and all of it at 26,303;
Pro over 159 spends 10% at 1,239.8 tok/s and all of it at 12,398.
Below
the first number the interconnect is a design cost; above the second the
topology cannot deliver the rate at all.

## 4b. Which one the study now builds, and why the answer is not the same for all three

**The old §5 below reports the wafer/array *ratio*, which is a fact about the two
classes. It does not answer the question a reader actually has, which is which
machine to build, and until 2026-08-31 the study's answer to that was produced by
a rule that could not see area.**

That rule ranked feasible ROM designs by per-user tokens/s, kept everything
within 5% of the peak, and reported the smallest silicon in the band. For
Qwen3-8B at batch 1 the peak *is* the wafer (6,464 tok/s), the 5% floor is 6,141,
and the best sub-wafer design in the N6 study reaches 3,518 — 54% of the peak — so
the band never engaged and the published answer for an 8B checkpoint was
**one 46,225 mm² wafer**. A rate tolerance is orthogonal to area; it can only
shrink a machine that was already near the peak.

**The rule the reports now state and apply** has two parts. Keep every feasible
design that no other feasible design of the same model and batch beats on *both*
per-user tokens/s and tokens/s per 1,000 mm² — that non-dominated set is the
published frontier. Then walk it by ascending area from the smallest feasible
machine, accepting a rung only while the per-user tokens/s it adds per added mm²
is strictly greater than the tokens/s per mm² the incumbent already returns on
average. The bar is parity and it cannot be tuned to move an answer: accepting
when `(r − r0)/(a − a0) ≥ r0/a0` is exactly `r/a ≥ r0/a0`.

### The answer, at batch 1

| model | N6 vs A100 | N5 vs B200 |
|---|---|---|
| Qwen3-8B @8K | **array**, 7 × 815 mm² = 5,705 mm², 3,110.4 tok/s/user, 636.1 per 1,000 mm² | **array**, 5 × 815 mm² = 4,075 mm², 4,941.0 tok/s/user, 1,212.5 per 1,000 mm² | <!-- figure: 3,110.4 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="Qwen recommended per-user rate, N6" --> <!-- figure: 636.1 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.tokens_s_per_1000mm2" name="Qwen recommended throughput density, N6" --> <!-- figure: 4,941.0 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="Qwen recommended per-user rate, N5" --> <!-- figure: 1,212.5 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.tokens_s_per_1000mm2" name="Qwen recommended throughput density, N5" -->
| DeepSeek-V4-Flash @200K | **wafer**, 1 × 46,225 mm², 4,707.9 tok/s/user, 101.8 per 1,000 mm² | **array**, 30 × 815 mm² = 24,450 mm², 2,627.4 tok/s/user, 107.5 per 1,000 mm² | <!-- figure: 4,707.9 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_tokens_s" name="Flash recommended per-user rate, N6" --> <!-- figure: 101.8 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.tokens_s_per_1000mm2" name="Flash recommended throughput density, N6" --> <!-- figure: 2,627.4 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_tokens_s" name="Flash recommended per-user rate, N5" --> <!-- figure: 107.5 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.tokens_s_per_1000mm2" name="Flash recommended throughput density, N5" -->
| DeepSeek-V4-Pro @1M | **wafer**, 4 × 46,225 mm² = 184,900 mm², 2,375.7 tok/s/user, 12.8 per 1,000 mm² | **wafer**, 3 × 46,225 mm² = 138,675 mm², 2,648.8 tok/s/user, 19.1 per 1,000 mm² | <!-- figure: 2,375.7 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_tokens_s" name="Pro recommended per-user rate, N6" --> <!-- figure: 12.8 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.tokens_s_per_1000mm2" name="Pro recommended throughput density, N6" -->

**Qwen3-8B gets seven N6 reticle dies and never should have got a wafer.** Its
current frontier has only two rows. The wafer adds per-user rate at a marginal
72.7 tok/s per 1,000 mm² of added silicon against the 616.6 the array already
returns, so the walk stops on the array:

| design | mm² | user tok/s | per 1,000 mm² | sessions | binds on | marginal return |
|---|---:|---:|---:|---:|---|---:|
| `…array-pipeline-x6` **← recommended** | 4,890 | 3,517.9 | **616.6** | 1 | `weight_read` | — | <!-- figure: 4,890 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.silicon_area_mm2" name="Qwen recommended area, N6" --> <!-- figure: 1 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.max_resident_users" name="Qwen recommended resident sessions, N6" -->
| `…wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 | `link_latency` | 72.7 |

**For the two DeepSeek models at N6 the frontier is a single row**, and that is a
stronger statement than any ratio: the wafer beats every reticle array on *both*
axes at once, so there is no trade-off to argue about. For Pro it is not even a
preference — 150 reticles of bare N6 mask ROM exceed two 57-reticle wafers, so
wafer-scale is a **capacity floor** and the answer is the four-wafer machine the
whole floorplan requires. §2's hop budget is why: Pro's 122 per-token
all-reduces cannot fit inside an NVLink domain of 8, so a reticle array pays every
collective twice — once inside a baseboard and once across InfiniBand — while a
four-wafer machine keeps each tensor group on a wafer and crosses wafer seams as
pipeline hand-offs.

**At N5 the same rule gives Flash an array**, and two things move together to do
it. `nvlink5`'s hop is 1.2 µs against `nvlink3`'s 2.5, so the array's collective
is cheaper; and N5's ROM capacity density is 9.380 MB/mm² against N6's 7.295, so
the bare checkpoint needs **21.8 reticles instead of 28.1**. The emitted N5
array uses 30 dies and returns 107.5 tok/s per 1,000 mm², narrowly above the N6
wafer's 101.8. Same rule, different node, different answer: Flash is an array
at N5 and a wafer at N6.

### Where the class flips with batch

The recommendation is recomputed at every studied batch and the contiguous runs
are published as regimes. At N6:

| model | batch 1 | first change | last regime |
|---|---|---|---|
| Qwen3-8B | array ×6, SRAM KV, 4,890 mm², **1 session** | batch 2 → array ×5, HBM KV, 4,075 mm², 298 sessions | batch 4–256 → array ×5 pipeline |
| DeepSeek-Flash | **wafer** ×1, HBM KV, 448 sessions | unchanged through batch 64 | batch 256 → wafer ×1 pipeline |
| DeepSeek-Pro | **wafer** ×4, SRAM KV, **1 session** | batch 2 → wafer ×5, HBM KV, 314 sessions | batch 256 → **array** ×218, 177,670 mm², 1,592 sessions |

Only Pro flips class as batch rises. Every SRAM-KV winner is a batch-1 winner
that holds exactly one session — `DESIGN_BATCH = 1` sizes the SRAM-KV floorplan
for a single stream. **So the honest one-line answer to "wafer or array" is:
array for Qwen, wafer for Flash at N6 but array at N5, and wafer for Pro until
the N6 batch-256 throughput regime.** A single recommendation per model would
have suppressed that dependence on node and operating point.

### What this section cannot tell you

The reticle-array class is sampled only at the device counts each floorplan's own
sizing sweep happened to choose: `ROM_AREA_LADDER` is applied where
`plan.kind == "wafer"` and nowhere else, so an array exists at an area only if
some sweep landed there. For Qwen3-8B at N6 the emitted batched-array counts are
SRAM-KV at {7} and HBM-KV at {5, 8}; Flash emits SRAM-KV {38, 39} and HBM-KV
{40, 41}; Pro emits SRAM-KV {199, 207} and HBM-KV {210, 218}. **The omission
runs against the array class**, so the published ROM curve is a lower bound on
the ROM curve rather than an upper one.

**Which of the six answers above that touches, precisely.** The three array
answers — Qwen3-8B at both nodes and Flash at N5 — sit at the floor of the
relevant compact class; no unvisited rung below that floor can hide. **The three
wafer answers — Flash at N6 and Pro at both nodes — are exposed**, because each
is a wafer chosen over an array class sampled at a handful of device counts, and
a rung the sweep never visited could in principle beat it on throughput
density. Those three are the weakest results on this page and should be
re-derived once the array class is emitted on the same explicit ladder the wafer
class already gets. Either way the curve *between* rungs is not evidence.

## 5. What this changes — rewritten

> **Read §4b first.** This section reports the wafer/array *ratio*, which is a
> property of the two classes and is still correct. It is not the answer to
> "which do I build" — §4b is, and for Qwen3-8B the two disagree: the wafer wins
> the ratio here and loses the build there, because winning a ratio by 1.84×
> while costing 8.1× the silicon is not winning.

The old §5 offered a choice in which the wafer bought *"15× the latency
headroom"*. **That figure is retracted.** The model reports the wafer/array
per-user ratio directly, at batch 1, each side on its own best design
(`REPORT.md` → "Topology choice at each operating point", `Wafer/array` column):

| | N5 vs B200 | N6 vs A100 |
|---|---:|---:|
| Qwen3-8B | **1.31×** | **1.84×** | <!-- figure: 1.31 src="results/roofline/n5_vs_b200/REPORT.md#Wafer/array" table="Topology choice" where="Model=Qwen3-8B;B=1" name="Qwen wafer/array at N5, B=1" --> <!-- figure: 1.84 src="results/roofline/n6_vs_a100/REPORT.md#Wafer/array" table="Topology choice" where="Model=Qwen3-8B;B=1" name="Qwen wafer/array at N6, B=1" -->
| DeepSeek-V4-Flash | **1.85×** | **3.13×** | <!-- figure: 1.85 src="results/roofline/n5_vs_b200/REPORT.md#Wafer/array" table="Topology choice" where="Model=DeepSeek-V4-Flash-0731;B=1" name="Flash wafer/array at N5, B=1" --> <!-- figure: 3.13 src="results/roofline/n6_vs_a100/REPORT.md#Wafer/array" table="Topology choice" where="Model=DeepSeek-V4-Flash-0731;B=1" name="Flash wafer/array at N6, B=1" -->
| DeepSeek-V4-Pro | **2.55×** | **3.34×** | <!-- figure: 2.55 src="results/roofline/n5_vs_b200/REPORT.md#Wafer/array" table="Topology choice" where="Model=DeepSeek-V4-Pro-0813;B=1" name="Pro wafer/array at N5, B=1" --> <!-- figure: 3.34 src="results/roofline/n6_vs_a100/REPORT.md#Wafer/array" table="Topology choice" where="Model=DeepSeek-V4-Pro-0813;B=1" name="Pro wafer/array at N6, B=1" -->

These are the values after all three link corrections: node-specific NVLink,
the 125 ns wafer crossing, and the 2.03 µs scale-out point. The last correction
makes arrays spanning multiple high-bandwidth domains faster, so it lowers the
Flash and Pro ratios most. The ordering is unchanged and the wafer still wins
every cell on per-user rate, but the N5 margin is now as low as **1.31×**.

On collective cost alone, like for like, the report states the wafer is *"at
least 1.3× cheaper"* (finding 9; it said 2.0× before the re-grading). The
per-model collective ratios follow from the §3 table by division — Qwen
174.37/138.60 = **1.26×** and Flash 589.32/165.55 = **3.56×**. Pro is the
capacity exception: its 892.91 µs array collective is **1.66× cheaper** than the
three-wafer layout's 1,478.17 µs total because the latter pays the inter-wafer
link. A claim elsewhere in this repository that the wafer is 8.3× cheaper on
Flash and 8.9× on Pro has **no producer**; those per-model values appear in
neither study report.

- **Array of reticle chips** — better yield, fault-tolerant to single-chip
  failure, composable, incrementally purchasable. Caps per-user decode at the
  §4 rates, and forecloses tensor parallelism above ~1,100–5,700 tok/s.
- **Wafer** — **1.3–3.34× the per-user rate**, tensor parallelism available but
  **not at Taalas-class rates**, and the only route to a per-user rate an array's
  hop count forbids. Costs stitching, yield, repair, and a thermal object in the
  class of a shipping wafer-scale system.<sup>[W]</sup>

**Which one wins depends on what is being maximised, and the study reports both
rather than choosing.** On per-user rate at equal area the wafer wins **24 of
24** operating points in both studies. On tokens per second per square
millimetre the same points split **9 array / 15 wafer** in each study (finding
10 in each report). So the old §5's
*"the array is the better default for the large models"* is now **half right and
half inverted**: it is right per unit silicon, and wrong per user, and it was
stated as though those were the same quantity. They are not — separating them
was the single largest correction in the study.

The wafer also has a structural disadvantage the old version of this document
never mentioned: perimeter grows as the square root of area, so HBM beachfront —
and therefore KV bandwidth — does not scale with wafer area the way compute and
ROM capacity do. 217 of 2,916 feasible points at N5 bind on `kv_read` for that
reason (finding 11).

## 6. How much of the uncertainty is ours, reported apart from theirs

The published band used to move every link on both sides at once. That is the
right test for a *common-mode* error and the wrong one for locating uncertainty,
because movements on the two sides can cancel. Since 2026-08-31 each report
prints three bands instead of one
(`REPORT.md` → "The headline is a band, and each side's share of it is reported
apart"). At 554,700 mm², batch 1, DeepSeek-V4-Pro at 1M context:

| study | stated | wafer fabric alone, low → high | cluster fabric alone, low → high | both together |
|---|---:|---:|---:|---:|
| N6 vs A100 | **5.90×** | 7.92× → 3.84× | 5.10× → 27.45× | 6.85× → 17.87× | <!-- figure: 5.90 src="results/roofline/n6_vs_a100/REPORT.md#Ratio stated" table="headline is a band" where="Model=DeepSeek-V4-Pro-0813;ROM mm2=554700" name="Pro headline ratio, N6" --> <!-- figure: 7.92 src="results/roofline/n6_vs_a100/REPORT.md#Wafer fabric low → high" table="headline is a band" where="Model=DeepSeek-V4-Pro-0813;ROM mm2=554700" name="Pro wafer-fabric band low, N6" -->
| N5 vs B200 | **2.67×** | 3.76× → 1.66× | 2.35× → 15.12× | 3.31× → 9.40× | <!-- figure: 2.67 src="results/roofline/n5_vs_b200/REPORT.md#Ratio stated" table="headline is a band" where="Model=DeepSeek-V4-Pro-0813;ROM mm2=554700" name="Pro headline ratio, N5" -->

**The wafer fabric column is ours** (`on_wafer`/`on_wafer_n5` per study, and
`inter_wafer`); no GPU design in either study touches either link. **The cluster fabric column is charged to both
families** (`nvlink3`/`nvlink5` and InfiniBand), because a ROM *array* is built
on the same interconnect the GPUs are — it is grouped as theirs only because the
headline GPU design is the one machine whose entire link budget is made of it.
A low wafer hop makes the ROM machine faster and the ratio larger; a low cluster
hop makes the GPU faster and the ratio smaller, so the two columns run in
opposite directions by construction and their product is what the joint column
shows.

Read the N6 row: the wafer-only span is 2.1×, the cluster-only span is 5.4×,
and the joint span is 2.6×. **The broad 1.9–22 µs scale-out range now dominates
the uncertainty and overwhelms the old cancellation.** The N5 joint interval is
similarly wide at 3.31×–9.40×. Reporting the one-sided bands is what makes the
source of that width visible.

For scale, this is what the same presentation showed before the re-grading, when
`on_wafer` was 100 ns swept 30–500 ns and `nvlink3` 1.5 µs swept 1.0–5.5 µs
(`docs/COMPARISON_FAIRNESS_AUDIT.md` A1): wafer fabric alone **13.48× → 3.26×**,
a 4.1× span, against a published joint band of 11.82× → 4.46×, 2.6×. The
one-sided ROM band was wider than the band being published. The current wafer
span is 2.1×; the much wider cluster span is the explicit cost of replacing a
narrow, misattributed scale-out range with the measured floor and shipped
collective-library ceiling.

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
project's power model has since been rebuilt: its A100 saturating gate is
**1.15×** published TDP and passes, while its reconstructed HC1 card is **0.35×**
the top of the published power band and fails. It still does not produce or
validate the quoted system-level 15–23 kW figure, so both quotations remain
replaced by the qualitative statement above.

## What nothing produces

Listed rather than filled in, per the rule that a gap is not an invitation to
invent a figure.

- **The 300 ns on-package chiplet hop** in the old §1. It is a registered input —
  `configs/hardware/technology.json` → `links.on_package.hop_latency_s`, graded
  `assumed`, swept 100 ns–1 µs, and sourced (like the on-wafer and Ethernet hops)
  to *this document* — and it appears in both roofline reports only inside their
  assumed-inputs ledger, at `links.on_package.hop_latency_s`. **No design row in
  either study exercises it**, so no report line prices it. It is an input with
  no consumer, and the 300 ns has never been checked against anything. The
  2026-08-31 node audit therefore leaves it single-valued: a constant no
  comparator binds on cannot make one study disagree with the other. That it is
  charged by nothing is asserted, not assumed, by
  `tests/test_roofline.py::test_on_package_is_charged_by_no_design_in_either_study`.
- **The one-sided perturbation probe in §1.** No committed artifact carries the
  earlier ad hoc probe values, and later input corrections changed their
  baselines. The per-side band in §6 is the artifact-backed version of the
  experiment. `tests/test_roofline.py::test_the_wafer_split_is_load_bearing`
  pins the property the probe illustrates — that each study moves only with its
  own wafer fabric — without pinning the numbers.
- **A per-model "wafer is N× cheaper on the collective" figure** as an artifact
  field. The reports state only "at least 1.3×"; the per-model ratios in §5 are
  my division of two cited cells and are labelled as such.
- **A measured reticle-field-to-reticle-field latency on a wafer-scale part.**
  §1's 125 ns is `derived`, not `measured`: it composes a published per-tile
  cycle, a published tile pitch and a published clock, and it is corroborated by
  two measured *whole-wafer* collectives. Nobody has published a latency for the
  object this model actually charges — one crossing of one reticle field — and
  nobody has published one for a stitched reticle **boundary** in cycles at all.
- **A wafer-to-wafer (SwarmX-class) latency.** `links.inter_wafer.hop_latency_s`
  is still `assumed` at 5.0 µs, swept 1–10 µs, and after the re-grading it is the
  largest unmeasured number left on the ROM side — 84% of the three-wafer Pro
  design's link budget in §3. The one adjacent figure Cerebras publishes is a
  Hot Chips 2024 slide bullet, *"CS-3 IO is <5us / 4 hops required"*, which reads
  per hop as exactly the assumed value and read as a whole path would be 1.25 µs
  and would move the headline sharply in this study's favour. A slide bullet
  cannot be disambiguated, so the value is unchanged. **The node audit leaves it
  single-valued too, and for a reason the GPU side supplies.** `inter_wafer` is
  charged by both studies, which looks like the defect `on_wafer` had; but its
  counterpart on the GPU side is the scale-out fabric, where `infiniband_hdr`
  and `infiniband_ndr` are distinct entries carrying the same **2.03 µs** point
  and 1.9–22 µs band. HDR is directly measured; NDR explicitly transfers that
  value because no comparable NDR measurement was found. They still differ in
  bandwidth, domain size, and switch radix. One scale-out latency per side
  across the two studies is symmetric, but the NDR transfer remains a named
  evidence gap rather than a node-specific measurement.
- **A band on `MESH_ALLREDUCE_DIAMETER_FACTOR` (1.1).** It is measured, and it is
  the *optimistic* end of a measured range: Rocki's 1.1× is a hand-written
  centre-rooted collective, while the corner-rooted X-Y collective Cerebras' SDK
  ships and Luczynski et al. measured costs about 2× the diameter. That 1.8× is
  currently folded into the top of the `on_wafer` sweep rather than swept in its
  own right, and it is the second-largest unswept quantity on the ROM side.

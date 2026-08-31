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
| `infiniband_ndr` | **4.5 µs** | published | 3.7–5.7 µs | <!-- figure: 4.5 src="configs/hardware/technology.json#links.infiniband_ndr.hop_latency_s.value" scale="1e6" name="infiniband_ndr hop latency, us" -->
| `inter_wafer` | **5.0 µs** | assumed | 1.0–10.0 µs | <!-- figure: 5.0 src="configs/hardware/technology.json#links.inter_wafer.hop_latency_s.value" scale="1e6" name="inter_wafer hop latency, us" -->
| `ethernet` | **5.0 µs** | assumed | 2.0–10.0 µs | <!-- figure: 5.0 src="configs/hardware/technology.json#links.ethernet.hop_latency_s.value" scale="1e6" name="ethernet hop latency, us" -->

**The wafer rows changed on 2026-08-31 and no longer cite this document.**
`on_wafer` was 100 ns graded `assumed` and swept 30–500 ns; `nvlink5` (and its
`nvlink3` twin, which the N6/A100 study uses) was 1.5 µs graded `assumed` and
swept 1.0–5.5 µs. Neither is a judgement any more, and neither re-grading is a
correction that only flatters us: the wafer hop went **up** 25%, which lowers
every ratio in this document; `nvlink5` went **down** 20%, which lowers them
again; and only its A100-generation twin `nvlink3` went up (1.5 → 2.5 µs), which
raises the N6 ratios. That is why every N5 cell of §5's table falls
(1.61/2.61/3.39× → 1.31/1.93/2.84×) while the N6 cells move both ways
(2.15/2.97/3.91× → 1.85/3.31/4.05×): the wafer hop pulls all six down and the
`nvlink3` correction pushes only the two sparse N6 cells back above where they
started. `ethernet` and `on_package` still cite this document; `ethernet` is
exercised by no design in either study.

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
in — §5's N5 wafer-fabric band runs 5.66× → 2.48× at 554,700 mm², so this
constant is worth about 2.3× there — and the derivation does not support one.
It would not have moved the N5 study's own headline point at all, which is an
`array` design on NVLink that touches no wafer fabric; the null is a null on
the band, not merely on a number that was already insensitive.

**What the model charges an `on_wafer` hop for, and what the sources measured.**
The model's hop is one step between adjacent **815 mm² reticle fields** — a
28.55 mm square, 57 to a wafer. It is *not* a tile-to-tile hop, and getting that
wrong is a factor of 125 in the ROM side's favour — it would take the headline
iso-area ratio from 8.33× to 14.7× — because the single clock cycle
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

**What the null cost, measured rather than argued.** Driving `on_wafer_n5` to
the low end of its own band, 75 ns, and re-simulating both studies moves the N5
study and *only* the N5 study — headline 5.85× → 8.03×, and DeepSeek-V4-Pro at
554,700 mm² 4.01× → 5.00×, with the N6 study unchanged to four decimals. The
mirror holds: driving `on_wafer` to 75 ns moves N6 (10.78× → 13.95×, Pro
8.33× → 10.09×) and leaves N5 untouched. So the split is live, and **an
N5-specific wafer speed-up was worth up to 1.37× on that study's headline** —
which is exactly why the derivation had to be done rather than chosen, and
exactly why the null is worth stating. (This probe is a diagnostic; it is
listed under "What nothing produces" below, because no committed artifact
carries it.)

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
| `Qwen3-8B/b200_sxm-x29-pipeline` | 29 | 28 | 44.22 µs | 75% | 2,261.5 tok/s | 22,614.7 tok/s | <!-- figure: 44.22 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x29-pipeline" name="B200 x29 pipeline link latency/token" --> <!-- figure: 2,261.5 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x29-pipeline" name="B200 x29 pipeline viable to" --> <!-- figure: 22,614.7 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x29-pipeline" name="B200 x29 pipeline hard ceiling" -->
| `Qwen3-8B/b200_sxm-x58-pipeline` | 58 | **35 (capped)** | 56.14 µs | **95%** | 1,781.3 tok/s | 17,813.4 tok/s | <!-- figure: 56.14 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x58-pipeline" name="B200 x58 pipeline link latency/token" --> <!-- figure: 1,781.3 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x58-pipeline" name="B200 x58 pipeline viable to" --> <!-- figure: 17,813.4 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x58-pipeline" name="B200 x58 pipeline hard ceiling" -->
| `Qwen3-8B/b200_sxm-x347-pipeline` | 347 | **35 (capped)** | 56.14 µs | **95%** | 1,781.3 tok/s | 17,813.4 tok/s | <!-- figure: 56.14 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x347-pipeline" name="B200 x347 pipeline link latency/token" --> <!-- figure: 1,781.3 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x347-pipeline" name="B200 x347 pipeline viable to" --> <!-- figure: 17,813.4 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/b200_sxm-x347-pipeline" name="B200 x347 pipeline hard ceiling" -->

The qualitative claim survives and the numbers move again with the re-graded
`nvlink5` hop (1.5 → 1.2 µs, §1). At Taalas-class speed a 56-chip array now
spends **95%** of the budget on its pipeline rather than overrunning it — the
old table asserted 40% over, the previous version of this table 11% over, and
the corrected NVLink constant brings it just inside. It stops growing at 58
devices instead of doubling again at 112. At 3,000 tok/s the same array costs
**17%** of the budget and at 1,000 tok/s **6%**, which is a design cost rather
than a wall. The old table's `N=112 → 283%` cell is **retracted**: no array of
any size can charge Qwen3-8B more than 35 pipeline hops.

## 3. Tensor parallel: the retracted section

Tensor parallelism needs two all-reduces per layer, every token, *regardless of
how few devices it is spread over*. That much is unchanged, and it is
`docs/METHODOLOGY.md` §6.

| model | layers | collectives/token | **on-wafer** | **NVLink array** | on-wafer as % of 58.8 µs |
|---|---:|---:|---:|---:|---:|
| Qwen3-8B | 36 | 72 | **138.60 µs** | **174.11 µs** | **236%** | <!-- figure: 138.60 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1" name="Qwen on-wafer tensor link latency/token" --> <!-- figure: 174.11 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x3" name="Qwen NVLink tensor link latency/token" -->
| DeepSeek-V4-Flash | 43 | 86 | **165.55 µs** | **1,003.59 µs** | **282%** | <!-- figure: 165.55 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1" name="Flash on-wafer tensor link latency/token" --> <!-- figure: 1,003.59 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x14" name="Flash NVLink tensor link latency/token" -->
| DeepSeek-V4-Pro | 61 | 122 | **234.85 µs** (on-wafer term only) | **1,489.18 µs** | **399%** | <!-- figure: 1,489.18 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x72" name="Pro NVLink tensor link latency/token" -->

On-wafer rows: `Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1`,
`DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1`,
`DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x2`. Array rows:
`Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x3`,
`DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x14`,
`DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x72`. Each row's `Events` cell
spells out the arithmetic, e.g. `72 x all_reduce span 57 on on_wafer
(traversals 15.4) = 138.60 us`.

**Pro does not fit on one wafer, and the honest total is worse than the table
suggests.** Its ROM array is 52.6 reticle fields at N5 (§4), so a tensor group
spans two wafers and pays `inter_wafer` as well: 234.85 µs on-wafer **plus**
1,237.49 µs across the wafer boundary = **1,472.34 µs**, a hard ceiling of <!-- figure: 1,472.34 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x2" name="Pro two-wafer tensor link latency/token" -->
**679.2 tok/s**. Charging that link the on-wafer stitched-mesh hop — which this
study previously did — is the ROM-side mirror of charging a GPU cluster a
672-way pipeline. Note what the re-grading did here: raising the on-wafer hop by
25% moved this design's total by only 3%, because 84% of it is the `inter_wafer`
link, which is still `assumed` at 5.0 µs and is now the largest unmeasured
number left on the ROM side.

**The corrected conclusion.** On-wafer tensor parallelism is *better than
NVLink* and is *not good anywhere*. The ordering survives; the fit does not. The
hard ceilings are:

| | on-wafer hard ceiling | NVLink-array hard ceiling |
|---|---:|---:|
| Qwen3-8B | 7,215.0 tok/s | 5,743.5 tok/s | <!-- figure: 7,215.0 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1" name="Qwen on-wafer tensor hard ceiling" --> <!-- figure: 5,743.5 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x3" name="Qwen NVLink tensor hard ceiling" -->
| DeepSeek-V4-Flash | 6,040.5 tok/s | 996.4 tok/s | <!-- figure: 6,040.5 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1" name="Flash on-wafer tensor hard ceiling" --> <!-- figure: 996.4 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x14" name="Flash NVLink tensor hard ceiling" -->
| DeepSeek-V4-Pro | 679.2 tok/s | 671.5 tok/s | <!-- figure: 679.2 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x2" name="Pro two-wafer tensor hard ceiling" --> <!-- figure: 671.5 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x72" name="Pro NVLink tensor hard ceiling" -->

That band — **6,000–7,200 tok/s** for the two models that fit on one wafer — is
the replacement for the retracted 116,278 / 81,966 tok/s. It narrowed from
5,000–9,000 tok/s when the on-wafer hop was re-graded upward from 100 to
125 ns. The report states the
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
| Qwen3-8B | 16.4 GB | 16.00 | 786 mm² | **1.0** | `…array-pipeline-x3`, 3 devices, 2 hops, 2.42 µs | **41,353.0 tok/s** | <!-- figure: 16.4 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=Qwen3-8B].checkpoint_bytes" scale="1e-9" name="Qwen checkpoint, GB" --> <!-- figure: 16.00 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=Qwen3-8B].native_bits_per_parameter" name="Qwen bits/param" --> <!-- figure: 2.42 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x3" name="Qwen array pipeline link latency/token" --> <!-- figure: 41,353.0 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x3" name="Qwen array pipeline viable to" -->
| DeepSeek-V4-Flash | 166.9 GB | 4.70 | 8,010 mm² | **9.8** | `…array-pipeline-x14`, 14 devices, 13 hops, 19.17 µs | **5,215.6 tok/s** | <!-- figure: 166.9 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].checkpoint_bytes" scale="1e-9" name="Flash checkpoint, GB" --> <!-- figure: 4.70 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].native_bits_per_parameter" name="Flash bits/param" --> <!-- figure: 19.17 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x14" name="Flash array pipeline link latency/token" --> <!-- figure: 5,215.6 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x14" name="Flash array pipeline viable to" -->
| DeepSeek-V4-Pro | 892.7 GB | 4.46 | 42,852 mm² | **52.6** | `…array-pipeline-x74`, 74 devices, 60 hops, 97.95 µs | **1,020.9 tok/s** | <!-- figure: 892.7 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].checkpoint_bytes" scale="1e-9" name="Pro checkpoint, GB" --> <!-- figure: 4.46 src="results/roofline/n5_vs_b200/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].native_bits_per_parameter" name="Pro bits/param" --> <!-- figure: 97.95 src="results/roofline/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x74" name="Pro array pipeline link latency/token" --> <!-- figure: 1,020.9 src="results/roofline/n5_vs_b200/REPORT.md#Viable to (10% budget)" table="Array or wafer" where="Design=DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x74" name="Pro array pipeline viable to" -->

The device counts are larger than the ROM area alone implies because a design
also has to carry compute, KV store and beachfront; they are the counts the
study's own design generator produced, not a division I performed.

Three of the old §4 numbers moved and one claim changed shape:

- Flash: **10 chips → 14**, **7,400 tok/s → 5,215.6**;
- Pro: **53 chips → 74**, **1,280 tok/s → 1,020.9**;
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
spends 10% of the token budget at 5,215.6 tok/s and all of it at 52,156.5;
Pro over seventy-four spends 10% at 1,020.9 tok/s and all of it at 10,209.2.
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
Qwen3-8B at batch 1 the peak *is* the wafer (6,505 tok/s), the 5% floor is 6,180,
and the best sub-wafer design in the study reaches 3,530 — 54% of the peak — so
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
| Qwen3-8B @8K | **array**, 3 × 815 mm² = 2,445 mm², 2,791.2 tok/s/user, 1,141.6 per 1,000 mm² | **array**, 3 × 815 mm² = 2,445 mm², 3,795.9 tok/s/user, 1,552.5 per 1,000 mm² | <!-- figure: 2,791.2 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="Qwen recommended per-user rate, N6" --> <!-- figure: 1,141.6 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.tokens_s_per_1000mm2" name="Qwen recommended throughput density, N6" --> <!-- figure: 3,795.9 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="Qwen recommended per-user rate, N5" --> <!-- figure: 1,552.5 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.tokens_s_per_1000mm2" name="Qwen recommended throughput density, N5" -->
| DeepSeek-V4-Flash @200K | **wafer**, 1 × 46,225 mm², 4,663.6 tok/s/user, 100.9 per 1,000 mm² | **array**, 14 × 815 mm² = 11,410 mm², 2,545.1 tok/s/user, 223.1 per 1,000 mm² | <!-- figure: 4,663.6 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_tokens_s" name="Flash recommended per-user rate, N6" --> <!-- figure: 100.9 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.tokens_s_per_1000mm2" name="Flash recommended throughput density, N6" --> <!-- figure: 2,545.1 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_tokens_s" name="Flash recommended per-user rate, N5" --> <!-- figure: 223.1 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.tokens_s_per_1000mm2" name="Flash recommended throughput density, N5" -->
| DeepSeek-V4-Pro @1M | **wafer**, 2 × 46,225 mm², 2,359.5 tok/s/user, 25.5 per 1,000 mm² | **wafer**, 2 × 46,225 mm², 2,359.5 tok/s/user, 25.5 per 1,000 mm² | <!-- figure: 2,359.5 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_tokens_s" name="Pro recommended per-user rate, N6" --> <!-- figure: 25.5 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.tokens_s_per_1000mm2" name="Pro recommended throughput density, N6" -->

**Qwen3-8B gets three reticle dies and never should have got a wafer.** The walk
stops at the first rung because the next one returns 44.6 tok/s per 1,000 mm² of
added silicon against the 1,141.6 the machine already returns, and the wafer —
four rungs further on — returns 84.8. Its whole frontier, from the report:

| design | mm² | user tok/s | per 1,000 mm² | sessions | binds on | marginal return |
|---|---:|---:|---:|---:|---|---:|
| `…array-pipeline-x3` **← recommended** | 2,445 | 2,791.2 | **1,141.6** | 1 | `compute` | — | <!-- figure: 2,445 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.silicon_area_mm2" name="Qwen recommended area, N6" --> <!-- figure: 1 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.max_resident_users" name="Qwen recommended resident sessions, N6" -->
| `…array-pipeline-x4` | 3,260 | 2,827.5 | 867.3 | 1 | `weight_read` | 44.6 |
| `…array-pipeline-x6-romfill` | 4,890 | 3,509.6 | 717.7 | 1 | `weight_read` | 293.8 |
| `…array-pipeline-x7-romfill` | 5,705 | 3,529.9 | 618.7 | 1 | `weight_read` | 226.6 |
| `…wafer-tensor-x1-romfill` | 46,225 | 6,505.3 | 140.7 | 1 | `link_latency` | 84.8 |

**For the two DeepSeek models at N6 the frontier is a single row**, and that is a
stronger statement than any ratio: the wafer beats every reticle array on *both*
axes at once, so there is no trade-off to argue about. For Pro it is not even a
preference — 94 reticles of mask ROM exceeds one 57-reticle wafer, so wafer-scale
is a **capacity floor** and the only question is how many, to which the answer is
the fewest that hold the model. §2's hop budget is why: Pro's 122 per-token
all-reduces cannot fit inside an NVLink domain of 8, so a reticle array pays every
collective twice — once inside a baseboard and once across InfiniBand — while a
two-wafer machine keeps all 122 inside one 57-region mesh and crosses the wafer
seam once, as a pipeline hand-off.

**At N5 the same rule gives Flash an array**, and two things move together to do
it. `nvlink5`'s hop is 1.2 µs against `nvlink3`'s 2.5, so the array's collective
gets cheaper; and N5's ROM capacity density is 20.833 MB/mm² against N6's 16.204,
so the same checkpoint needs **14 reticles instead of 18** — less silicon and
fewer hops at once. The array's throughput density goes from 95.9 tok/s per
1,000 mm² at N6 to **223.1 at N5** while the wafer's barely moves (100.9 → 106.3),
and the class flips. Same rule, different node, different answer. That is the
rule doing its job rather than a result being chosen.

### Where the class flips with batch

The recommendation is recomputed at every studied batch and the contiguous runs
are published as regimes. At N6:

| model | batch 1 | first change | last regime |
|---|---|---|---|
| Qwen3-8B | array ×3, SRAM KV, 2,445 mm², **1 session** | batch 2 → array ×5, HBM KV, 4,075 mm², 298 sessions | unchanged to batch 256 |
| DeepSeek-Flash | **wafer** ×1, HBM KV, 448 sessions | batch 4 → **array** ×19, 15,485 mm², 990 sessions | array ×19 to batch 256 |
| DeepSeek-Pro | **wafer** ×2, SRAM KV, **1 session** | batch 2 → wafer ×5, HBM KV, 314 sessions | batch 16 → **array** ×99, 80,685 mm², 723 sessions |

Two of the three models flip class as the batch rises, and every SRAM-KV winner
is a batch-1 winner that holds exactly one session — `DESIGN_BATCH = 1` sizes the
SRAM-KV floorplan for a single stream. **So the honest one-line answer to "wafer
or array" is: wafer for latency on the two large models, array for throughput on
all three, and array for both on the 8B.** A single recommendation per model
would have had to suppress that.

### What this section cannot tell you

The reticle-array class is sampled only at the device counts each floorplan's own
sizing sweep happened to choose: `ROM_AREA_LADDER` is applied where
`plan.kind == "wafer"` and nowhere else, so an array exists at an area only if
some sweep landed there. For Qwen3-8B at N6 the emitted batched-array counts are
SRAM-KV/`spare=sram` at {3, 4}, SRAM-KV/`romfill` at {6, 7} and HBM-KV at {5, 8}
— no romfill array at 4 or 5 dies, no SRAM-KV array at 5 or 8. **The omission
runs against the array class**, so the published ROM curve is a lower bound on
the ROM curve rather than an upper one.

**Which of the six answers above that touches, precisely.** Qwen3-8B at both
nodes and DeepSeek-Flash at N5 are won by the *smallest feasible machine*, and
the gap cannot reach those: nothing exists below the minimum area for a denser
rung to hide in. **The three wafer answers — Flash at N6 and Pro at both nodes —
are exposed**, because each is a wafer chosen over an array class sampled at a
handful of device counts, and a rung the sweep never visited could in principle
beat it on throughput density. Those three are the weakest results on this page
and should be re-derived once the array class is emitted on the same explicit
ladder the wafer class already gets. Either way the curve *between* rungs is not
evidence.

## 5. What this changes — rewritten

> **Read §4b first.** This section reports the wafer/array *ratio*, which is a
> property of the two classes and is still correct. It is not the answer to
> "which do I build" — §4b is, and for Qwen3-8B the two disagree: the wafer wins
> the ratio here and loses the build there, because winning a ratio by 1.85×
> while costing 18.9× the silicon is not winning.

The old §5 offered a choice in which the wafer bought *"15× the latency
headroom"*. **That figure is retracted.** The model reports the wafer/array
per-user ratio directly, at batch 1, each side on its own best design
(`REPORT.md` → "Topology choice at each operating point", `Wafer/array` column):

| | N5 vs B200 | N6 vs A100 |
|---|---:|---:|
| Qwen3-8B | **1.31×** | **1.85×** | <!-- figure: 1.31 src="results/roofline/n5_vs_b200/REPORT.md#Wafer/array" table="Topology choice" where="Model=Qwen3-8B;B=1" name="Qwen wafer/array at N5, B=1" --> <!-- figure: 1.85 src="results/roofline/n6_vs_a100/REPORT.md#Wafer/array" table="Topology choice" where="Model=Qwen3-8B;B=1" name="Qwen wafer/array at N6, B=1" -->
| DeepSeek-V4-Flash | **1.93×** | **3.31×** | <!-- figure: 1.93 src="results/roofline/n5_vs_b200/REPORT.md#Wafer/array" table="Topology choice" where="Model=DeepSeek-V4-Flash-0731;B=1" name="Flash wafer/array at N5, B=1" --> <!-- figure: 3.31 src="results/roofline/n6_vs_a100/REPORT.md#Wafer/array" table="Topology choice" where="Model=DeepSeek-V4-Flash-0731;B=1" name="Flash wafer/array at N6, B=1" -->
| DeepSeek-V4-Pro | **2.84×** | **4.05×** | <!-- figure: 2.84 src="results/roofline/n5_vs_b200/REPORT.md#Wafer/array" table="Topology choice" where="Model=DeepSeek-V4-Pro-0813;B=1" name="Pro wafer/array at N5, B=1" --> <!-- figure: 4.05 src="results/roofline/n6_vs_a100/REPORT.md#Wafer/array" table="Topology choice" where="Model=DeepSeek-V4-Pro-0813;B=1" name="Pro wafer/array at N6, B=1" -->

**The N5 column fell and the N6 column rose, and that is the re-grading, not
noise.** The N5 study charges `nvlink5`, which got *faster* (1.5 → 1.2 µs), so
its array side improved; the N6 study charges `nvlink3`, which got *slower*
(1.5 → 2.5 µs), so its array side worsened. Both columns also carry the 25%
slower wafer hop. The ordering is unchanged and the wafer still wins every cell,
but the N5 margin is now as low as **1.31×**.

On collective cost alone, like for like, the report states the wafer is *"at
least 1.3× cheaper"* (finding 8; it said 2.0× before the re-grading). The
per-model collective ratios follow from the §3 table by division — Qwen
174.11/138.60 = **1.26×**, Flash 1,003.59/165.55 = **6.06×**, Pro
1,489.18/1,472.34 = **1.01×** — and note that Pro's is now barely distinguishable
from one, because its wafer machine pays an inter-wafer link the array does not
have. A claim elsewhere in this repository that the wafer is 8.3× cheaper on
Flash and 8.9× on Pro has **no producer**; those per-model values appear in
neither study report.

- **Array of reticle chips** — better yield, fault-tolerant to single-chip
  failure, composable, incrementally purchasable. Caps per-user decode at the
  §4 rates, and forecloses tensor parallelism above ~670–5,700 tok/s.
- **Wafer** — **1.3–4.1× the per-user rate**, tensor parallelism available but
  **not at Taalas-class rates**, and the only route to a per-user rate an array's
  hop count forbids. Costs stitching, yield, repair, and a thermal object in the
  class of a shipping wafer-scale system.<sup>[W]</sup>

**Which one wins depends on what is being maximised, and the study reports both
rather than choosing.** On per-user rate at equal area the wafer wins **24 of
24** operating points in both studies. On tokens per second per square
millimetre the same points split **12 array / 12 wafer** at N5-vs-B200 and
**18 array / 6 wafer** at N6-vs-A100 (finding 9 in each report). So the old §5's
*"the array is the better default for the large models"* is now **half right and
half inverted**: it is right per unit silicon, and wrong per user, and it was
stated as though those were the same quantity. They are not — separating them
was the single largest correction in the study.

The wafer also has a structural disadvantage the old version of this document
never mentioned: perimeter grows as the square root of area, so HBM beachfront —
and therefore KV bandwidth — does not scale with wafer area the way compute and
ROM capacity do. 224 of 3,016 feasible points at N5 bind on `kv_read` for that
reason (finding 10).

## 6. How much of the uncertainty is ours, reported apart from theirs

The published band used to move every link on both sides at once. That is the
right test for a *common-mode* error and the wrong one for the question a reader
actually has, because the two sides partly cancel: the joint band came out
**narrower than the wafer side's own band**, which hid where the width lived.
Since 2026-08-31 each report prints three bands instead of one
(`REPORT.md` → "The headline is a band, and each side's share of it is reported
apart"). At 554,700 mm², batch 1, DeepSeek-V4-Pro at 1M context:

| study | stated | wafer fabric alone, low → high | cluster fabric alone, low → high | both together |
|---|---:|---:|---:|---:|
| N6 vs A100 | **8.33×** | 11.21× → 5.41× | 6.92× → 12.96× | 9.31× → 8.42× | <!-- figure: 8.33 src="results/roofline/n6_vs_a100/REPORT.md#Ratio stated" table="headline is a band" where="Model=DeepSeek-V4-Pro-0813;ROM mm2=554700" name="Pro headline ratio, N6" --> <!-- figure: 11.21 src="results/roofline/n6_vs_a100/REPORT.md#Wafer fabric low → high" table="headline is a band" where="Model=DeepSeek-V4-Pro-0813;ROM mm2=554700" name="Pro wafer-fabric band low, N6" -->
| N5 vs B200 | **4.01×** | 5.66× → 2.48× | 3.33× → 6.85× | 4.71× → 4.24× | <!-- figure: 4.01 src="results/roofline/n5_vs_b200/REPORT.md#Ratio stated" table="headline is a band" where="Model=DeepSeek-V4-Pro-0813;ROM mm2=554700" name="Pro headline ratio, N5" -->

**The wafer fabric column is ours** (`on_wafer`/`on_wafer_n5` per study, and
`inter_wafer`); no GPU design in either study touches either link. **The cluster fabric column is charged to both
families** (`nvlink3`/`nvlink5` and InfiniBand), because a ROM *array* is built
on the same interconnect the GPUs are — it is grouped as theirs only because the
headline GPU design is the one machine whose entire link budget is made of it.
A low wafer hop makes the ROM machine faster and the ratio larger; a low cluster
hop makes the GPU faster and the ratio smaller, so the two columns run in
opposite directions by construction and their product is what the joint column
shows.

Read the N6 row: the joint band is a 1.1× interval and each side alone is about
2×. **Nothing about the comparison got more certain when the two were moved
together — the two uncertainties simply cancelled**, and reporting only the
joint interval would have claimed a precision neither constant supports.

For scale, this is what the same presentation showed before the re-grading, when
`on_wafer` was 100 ns swept 30–500 ns and `nvlink3` 1.5 µs swept 1.0–5.5 µs
(`docs/COMPARISON_FAIRNESS_AUDIT.md` A1): wafer fabric alone **13.48× → 3.26×**,
a 4.1× span, against a published joint band of 11.82× → 4.46×, 2.6×. The
one-sided ROM band was wider than the band being published. It is now 2.1×,
and the reason is not a narrower opinion — it is that the constant stopped being
an opinion.

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
  no consumer, and the 300 ns has never been checked against anything. The
  2026-08-31 node audit therefore leaves it single-valued: a constant no
  comparator binds on cannot make one study disagree with the other. That it is
  charged by nothing is asserted, not assumed, by
  `tests/test_roofline.py::test_on_package_is_charged_by_no_design_in_either_study`.
- **The one-sided perturbation probe in §1** (`on_wafer_n5` alone at 75 ns →
  N5 headline 8.03×, N6 unchanged). It is `_simulate_study` called twice on a
  perturbed `Technology` in memory; no committed artifact carries it, because
  the studies are generated at the stated values and the per-side *band* in §5
  is the version of this that is an artifact. `tests/test_roofline.py::test_the_wafer_split_is_load_bearing`
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
  largest unmeasured number left on the ROM side — 84% of the two-wafer Pro
  design's link budget in §3. The one adjacent figure Cerebras publishes is a
  Hot Chips 2024 slide bullet, *"CS-3 IO is <5us / 4 hops required"*, which reads
  per hop as exactly the assumed value and read as a whole path would be 1.25 µs
  and would move the headline sharply in this study's favour. A slide bullet
  cannot be disambiguated, so the value is unchanged. **The node audit leaves it
  single-valued too, and for a reason the GPU side supplies.** `inter_wafer` is
  charged by both studies, which looks like the defect `on_wafer` had; but its
  counterpart on the GPU side is the scale-out fabric, where `infiniband_hdr`
  and `infiniband_ndr` are *two* entries carrying the **same** measured 4.5 µs
  hop — they differ in bandwidth and domain size, not in latency, because
  small-message RDMA latency between accelerator buffers is set by the NIC and
  the protocol stack rather than by the logic node. One scale-out number per
  side across the two studies is symmetric. What was asymmetric was one number
  on one side against two on the other, and that was `on_wafer`.
- **A band on `MESH_ALLREDUCE_DIAMETER_FACTOR` (1.1).** It is measured, and it is
  the *optimistic* end of a measured range: Rocki's 1.1× is a hand-written
  centre-rooted collective, while the corner-rooted X-Y collective Cerebras' SDK
  ships and Luczynski et al. measured costs about 2× the diameter. That 1.8× is
  currently folded into the top of the `on_wafer` sweep rather than swept in its
  own right, and it is the second-largest unswept quantity on the ROM side.

# Which road to take

Every number here is emitted by `src/opentallas/roofline.py` and read out of
`results/roofline/n6_vs_a100/REPORT.md` and `analytical.json`. Nothing below is
recomputed in prose. That sentence appeared at the top of the previous version
of this document too and was not true — several of its headline figures were
shell arithmetic that reproduced the model's internals and dropped a derate
while doing it. Section 0 says which, because a retraction with its cause
attached is worth more than the claim it replaces.

The model reproduces two shipping parts:

| Gate | Published | Modelled | Ratio | Tolerance | Result |
|---|---:|---:|---:|---|---|
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 | 253.91 tok/s | 253.91 tok/s | 1.00× | within 1% | **PASS** |
| Taalas HC1, Llama-3.1-8B on 815 mm² at N6, per user | 16,960 tok/s | 12,232.4 tok/s | 0.72× | within 2× | **PASS** |

The HC1 gate now **under**-predicts by 1.39×, where the previous version of the
model over-predicted by 1.23×. That reversal is a consequence of the
corrections, not a tuning choice, and section 0.6 shows the gate across the
whole assumed band rather than at one point.

**Neither gate moved when the interconnect model was rebuilt** (section 0.9).
Both are single-device figures, so no topology change can reach them; that they
are unchanged to the last digit is the check that the rebuild touched only what
it claimed to touch.

**What this document now recommends, in one table.** Each model gets one design,
picked by a rule stated in the reports that produce it (§0.13, §2.3), read
iso-area against N copies of the one unified HBM die the GPU side is built from,
at the area the rule chose rather than at a rung of an area ladder:

| model | ROM design | mm² | user tok/s | tok/s per 1,000 mm² | resident sessions | iso-area GPU | ratio |
|---|---|---:|---:|---:|---:|---|---:|
| Qwen3-8B @8K | **3 × 815 mm² reticle dies**, SRAM KV, pipeline | 2,445 | 2,791.2 | 1,141.6 | 1 | 3 × A100 | 10.78× | <!-- figure: 2,445 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.silicon_area_mm2" name="headline Qwen area" --> <!-- figure: 2,791.2 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="headline Qwen per-user rate" --> <!-- figure: 1,141.6 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.tokens_s_per_1000mm2" name="headline Qwen density" --> <!-- figure: 10.78 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_speed_ratio" name="headline Qwen iso-area ratio" -->
| DeepSeek-V4-Flash @200K | **1 wafer**, HBM KV, tensor | 46,225 | 4,663.6 | 100.9 | 448 | 56 × A100 | 8.57× | <!-- figure: 4,663.6 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_tokens_s" name="headline Flash per-user rate" --> <!-- figure: 100.9 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.tokens_s_per_1000mm2" name="headline Flash density" --> <!-- figure: 8.57 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_speed_ratio" name="headline Flash iso-area ratio" -->
| DeepSeek-V4-Pro @1M | **2 wafers**, SRAM KV, hybrid | 92,450 | 2,359.5 | 25.5 | 1 | 112 × A100 | 8.58× | <!-- figure: 2,359.5 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_tokens_s" name="headline Pro per-user rate" --> <!-- figure: 25.5 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.tokens_s_per_1000mm2" name="headline Pro density" --> <!-- figure: 8.58 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_speed_ratio" name="headline Pro iso-area ratio" -->

**The 8B model gets three reticle dies.** It used to get a whole wafer, because
the rule that named a "best design" ranked on per-user tokens/s and could not see
area (§0.13). Two of these three rows hold **one** 8,192-token or 1M-token
session and the GPU cluster beside them holds hundreds; the ratio is a latency
claim and the batch-regime tables in §2.3 are where the serving answer lives. A
secondary, clearly-labelled quantised variant is published in §2.6, at 4.25 bits
on **both** sides, as a projection of a machine nobody has run.

**Four published claims fell.** Read them separately; they are four different
corrections that happen to land across two re-runs.

1. **Per-user latency and aggregate throughput were one number, and separating
   them is the largest correction this program has made.** The model charged a
   pipeline's service time on the machine's *aggregate* resources and its hops
   on the single-token path — a throughput view of the silicon wearing a latency
   view of the fabric. **The iso-area advantage for DeepSeek-V4-Pro at
   554,700 mm², batch 1, was 35.4× and is now 8.6×**, and `aggregate = batch ×
   per-user` is gone. It did **not** cancel in the ratio: across the seven-rung
   area ladder the ratio moves by between 0.24× and 1.51×, and it changes sign.
   Section 0.12.
2. **The iso-area advantage for DeepSeek-V4-Pro at 554,700 mm², batch 1, was
   54.2× and became 35.4×** (joint band 24.5–42.5×) before item 1 took it to
   8.6×, and the 2026-08-31 link re-grading took it to **8.3×**. The
   comparison let the ROM side choose its parallelism and not the GPU, and
   charged both sides a serial pipeline deeper than the model has layers.
   Section 0.9.
3. **DeepSeek-Flash's weight-to-KV read ratio at 200K was 113.2:1 and is
   35.3:1**. Two KV entry sizes had been read off the implementation instead of
   measured while running it. Section 0.10.
4. **The power model has been rebuilt and is no longer wrong by 7–9× — it is
   right on one published part and 2.9–3.6× low on the other, and the surviving
   gap is reported rather than closed.** Six power terms were derived from
   primitives and adversarially verified; **every one was refuted and every one
   was applied at its verifier's corrected value**, two of them moving power
   down. The A100 lands at 0.97× of its published 400 W TDP under a saturating
   load and Taalas HC1 at 0.28× of the top of its published 200–250 W band.
   Static power is now charged per mm² per second, so **`thermal_scale` binds
   for the first time**: 100 of 6,180 feasible points are power-limited, and
   **not one of them is a wafer**. Section 0.11.

The KV side of the model is no longer assumed at all. `results/roofline/
qwen3_execution_validation.json` compares the roofline's KV accounting against
executed hardware on both Qwen lanes: the (layer, position) pairs visited match
the causal triangle exactly (`position_ratio` 1.0) and the bytes match the
profile's own 4,096-byte entry exactly (`byte_ratio` 1.0). The weight side comes
in at 1.007–1.008× of prediction on those lanes, the excess being scales, index
tables and activations the analytical weight model does not count.

---

## 0. What was retracted, and why

Seven terms were audited for completeness. Five were wrong, and two more
problems in the study harness were found while fixing them. Four further
defects have landed since: the interconnect asymmetry (0.9), the DeepSeek-Flash
KV entry sizes (0.10), the power model (0.11, characterised in the previous
version and **rebuilt in this one**) and the pipeline service-time rule (0.12,
the largest of all of them). Each
correction that is in the model is tabulated in
`results/roofline/n6_vs_a100/REPORT.md` under *What the completeness corrections
cost* and *The floorplan sweep*.

### 0.1 The compute-in-ROM cell multiplier was applied to area alone

`balanced_area_split` charged a compute-in-ROM design 1.6× the silicon per
stored byte and then credited that larger array with the *storage* cell's
bandwidth per mm². Sweep time is capacity density over bandwidth density, so
scaling only the numerator handed compute-in-ROM a free 1.6× on throughput.
Both densities now carry the multiplier and it cancels — the model reports
**76.55 µs of full-array sweep for either machine.**

This retraction had already been written into the banner at the top of this
document. It had **not** been made in the code; the model still contained the
error. And the banner's own numbers were wrong in a second way: it gave the
corrected sweep as "57.4 µs either way … 17,400 vs 17,417 tok/s", which is the
sweep with `efficiencies.rom_read_bandwidth = 0.75` omitted. The model's own
before-derate figure is 57.41 µs and 17,417 tok/s; the figure that enters a
result is 76.55 µs and 13,063 tok/s. A retraction computed by hand reproduced
the very failure it was retracting.

### 0.2 The per-region sweep depth used the mean where the physics is the maximum

`evaluate` charged `batch · k / (N · coverage)` — the load of the *average*
engaged expert region — and divided it by a flat `expert_load_balance = 0.85`
whose own note in `technology.json` said "the sweep depth is set by the busiest
region rather than the mean". The code did not do what its parameter documented.
The array is not finished when the average region drains; it is finished when
the deepest queue does. `roofline.expected_max_region_load` now computes the
busiest region from the routing distribution, and the test suite checks it
against a 4,000-trial Monte Carlo of the actual routing — agreement within 3% at
every batch from 1 to 256, for both 256 and 384 experts, and exactly 1.000 at
batch 1.

The correction is a function of batch, which is why no constant could have
carried it. From the model, DeepSeek-V4-Flash:

| B | mean engaged region | busiest region | correction |
|---:|---:|---:|---:|
| 1 | 1.000 | 1.000 | 1.00× |
| 8 | 1.085 | 2.134 | 1.97× |
| 32 | 1.410 | 4.026 | 2.85× |
| 64 | 1.921 | 5.831 | 3.04× |
| 256 | 6.014 | 13.844 | 2.30× |

**The published claim "per-region beats a global broadcast by up to 27× at batch
64" is retracted. At a matched floorplan the model said 10.65×, and with the
measured KV entry sizes of section 0.10 it now says 7.44×.**

### 0.3 The same mean-for-maximum error was on the GPU side

`workload.expected_engaged_devices` returns the expected number of devices
holding at least one selected expert, and the routed fetch was divided by it —
but the fetch finishes when the busiest device finishes. `workload.py` is shared
with `opentallas.analytical` and was not edited; the correction lives in
`roofline.effective_engaged_devices`, and **both numbers are carried on every
evaluated point**, because correcting only the ROM side would have been its own
bias. The model reports corrections from **1.02× to 3.14×** over the 125 GPU
points in the study where routed experts are spread across more than one device
— for example DeepSeek-Flash on 5 A100s at batch 1: 3.69 devices engaged on the
mean, 2.53 effective, a 1.46× correction.

### 0.4 There was no fixed per-layer cost anywhere on-die

The only latency in the model was `links.*.hop_latency_s`, charged at
inter-partition boundaries, so a `single_chip` design had a decode step with
*literally zero* fixed cost. A graded per-layer budget is now charged, built
from primitives that exist independently of the HC1 anchor: SRAM access time,
sequencer instruction issue and decode, pipeline fill and drain across a
serially dependent array-pass boundary, the layer barrier, and an on-die wire
delay over a distance derived from the floorplan (`sqrt(reticle.area_mm2)`).
That comes to **162.4 ns per dense layer** and **290.4 ns per compressed-sparse
layer**, with a stated range of 65.4–726.8 ns.

The asymmetry is the finding, and it runs against this program's own thesis. At
batch 1, on the fastest feasible design of each family. The shares are larger
than when this was first found -- 34.8/32.0/28.2% on the ROM side then, against
55.4/38.7/34.7% now -- because the interconnect rebuild of 0.9 and the KV
measurement of 0.10 both shrank the terms this floor competes with.

| family | model | fixed latency | share of the step |
|---|---|---:|---:|
| rom | DeepSeek-V4-Flash-0731 | 9.67 µs | **55.4%** |
| rom | DeepSeek-V4-Pro-0813 | 13.75 µs | **38.7%** |
| rom | Qwen3-8B | 5.85 µs | **34.7%** |
| gpu | Qwen3-8B | 5.85 µs | 6.6% |
| gpu | DeepSeek-V4-Flash-0731 | 9.67 µs | 2.0% |
| gpu | DeepSeek-V4-Pro-0813 | 13.75 µs | 0.9% |

The same floor, five to forty times more expensive on the architecture this
program is arguing for, because a ROM step is tens of microseconds over 32–61
layers while a GPU step for the same model is milliseconds. At batch 1 it is now
the **binding constraint on the fastest design of both DeepSeek models**, which
it was not when this was written -- another consequence of 0.9 and 0.10 shrinking
the terms around it.

### 0.5 KV access granularity was not modelled at all

**RETRACTED IN FULL.** This section said that for DeepSeek-V4-Flash at 200K,
*"72% of the KV read is a scan of 50,000 68-byte index entries per
compressed-sparse layer"*, and that interleaving them with their payload cost
1.64×/1.30× on SRAM/HBM against 1.00× contiguous. The 68 bytes was read off the
implementation. Measured, the index entry is **256 bytes** (section 0.10) —
larger than the 128-byte SRAM granule and the 32-byte HBM granule alike — so an
interleaved index array now costs exactly nothing, on either store, on **both**
DeepSeek models:

| model | KV store | granule | inflation before | inflation now |
|---|---|---:|---:|---:|
| Qwen3-8B | sram / hbm | 128 B / 32 B | 1.00× / 1.00× | 1.00× / 1.00× |
| DeepSeek-V4-Flash-0731 | sram / hbm | 128 B / 32 B | 1.64× / 1.30× | **1.00× / 1.00×** |
| DeepSeek-V4-Pro-0813 | sram / hbm | 128 B / 32 B | 1.67× / 1.31× | **1.00× / 1.00×** |

**There is now no granularity inflation anywhere in either study.** The
mechanism is real and is still parameterised — shrink the index entry below the
granule in the profile and the penalty returns, which the test suite checks —
but this workload does not exercise it. The one surviving fact from the original
observation is that the index scan is *most* of the KV read, and it is more of
it than was claimed: **84.7% for Flash and 87.0% for Pro**, up from 72%, because
the payload entries grew too.

This is a **layout choice, not a physical constant** — a design can pack the
index array separately and pay nothing — so `kv.index_layout` is a named, graded
input and every step reports which layout produced its answer.

### 0.6 The per-layer cost is a band, and the gate is not fitted

Every term in the `latency` block is `assumed` and carries `range_low` and
`range_high`. The gate is evaluated at both ends and the band is what the reader
is asked to believe:

| per-layer latency | value | per token | modelled | ratio | binds on |
|---|---:|---:|---:|---:|---|
| range low | 65.4 ns/layer | 2.09 µs | 12,715.1 | 0.75× | weight_read |
| **range stated** | **162.4 ns/layer** | **5.20 µs** | **12,232.4** | **0.72×** | weight_read |
| range high | 726.8 ns/layer | 23.26 µs | 10,018.9 | 0.59× | weight_read |

The gate passes across the whole band. The per-layer cost that would land the
model exactly on the published figure is **−549.7 ns/layer** — negative, meaning
the corrected sweep alone (76.55 µs) already exceeds the published token budget
(58.96 µs). **No value of this term could have closed the gap**, so the term
cannot have been fitted to it even in principle, and the residual lies elsewhere:
the gate back-derives that the ROM read-bandwidth density would have to be
**1.30×** the 1.764e11 B/s/mm² this model derives, which is still below the
4.327e11 B/s/mm² the same model derives for SRAM from Cerebras WSE-2. That is a
falsifiable statement about one technology input, which is what a gate is for.

### 0.7 Two harness faults that were deciding results

**The ROM weight-capacity check was tautological.** `balanced_area_split` sized
ROM to the stored bytes, so `weight_capacity / stored` was exactly the cell
multiplier at every model size, node and area. It could not fail. The array is
now clamped to the silicon actually left after SRAM, HBM PHY, overhead and
interconnect, so a design whose weights do not fit reports a capacity below them
and `evaluate` refuses it.

**Every amortisation policy was sized on the batched machine's floorplan.** The
sizing sweep chose a device count on the storage machine and handed it to all
three policies, on a comment that said they are identical at batch 1 — true
before the floorplan started depending on the policy, false after. A
compute-in-ROM cell is 1.6× a storage cell, so the same weights need 1.6× the
array and more dies to hold it: the study now sizes DeepSeek-Flash at **26 dies
against the batched machine's 18**, and DeepSeek-Pro at **138 against 93**. Every
compute-in-ROM DeepSeek point was reported infeasible. That was the harness saying *"we never tried enough
dies"* and the report reading it as *"it cannot hold this model"*. Each policy is
now sized on its own floorplan.

**And the silicon compute-in-ROM recovers was being spent on the wrong thing.**
Not having a MAC array frees ~300 mm² per device; `balanced_area_split` gave it
to SRAM, which on a weight-bound design is the component with a twenty-fold
margin. All three policies then landed on the same number and the study reported
per-region as worthless — an artefact of the allocation rule. Where the
recovered silicon goes is now a swept design variable, and **the same sweep is
offered to the amortising machine**, because offering it to one side only would
move the artefact rather than remove it.

### 0.8 The SRAM KV path is still never exercised

At batch 1 the step credits one user with the whole array's read bandwidth. That
is defensible for KV in a way it is not for ROM — KV is written at run time and
can be striped across every bank, while an expert's weights live where they were
masked — but it holds only if the design really stripes, and nothing checks.
Rather than assert either, the model reports the bank-locality bound at every
point: for DeepSeek-Flash on one wafer the charged KV read at batch 1 is 0.20 µs
and the bound is 2.14 µs, and the bound is *batch-independent*, which is the ROM
locality rule turning up on the SRAM side. It happens to be harmless for these
designs because both sit below the sweep. That is a fact about these designs, not
a property of the model.

---

### 0.9 The iso-area comparison let one side choose its topology and not the other

**RETRACTED: 54.2× for DeepSeek-V4-Pro at 1M context, batch 1, at 554,700 mm².
The model said 35.4× when this section was written; it says **8.33×** now
(§0.12 and §3), and the band across the hop latencies is no longer the joint
24.5–42.5× quoted here — see §3, where each side's band is reported apart.** Also retracted: *"two all-reduces per layer per token cost 131.35 µs
on NVLink for Flash and 188.83 µs for Pro, against 8.60 µs and 12.20 µs
on-wafer — hard ceilings of 7,613 and 5,296 tok/s per user against 116,278 and
81,966."* The on-wafer half of that sentence was wrong by more than an order of
magnitude and it was wrong in our favour.

The ROM side was swept over pipeline **and** tensor parallelism and the better
reported. The GPU side was only ever evaluated under pipeline, which at 672
devices charged it 671 serial hops per token at batch 1 — 1,017 µs, 41% of its
step — and made it get *slower* as it was given more silicon: 532 tok/s at 112
devices down to 407 at 672. That decline was most of the headline.

Three corrections, each applied to both sides:

**0.9.1 Both sides now choose their parallelism.** Pipeline, tensor and hybrid
— tensor-parallel inside the high-bandwidth domain, pipeline-parallel across it
— are evaluated at every cluster size on both sides. **On its own this changed
almost nothing**, which is itself a finding and is the subject of 0.9.4.

**0.9.2 Both sides are charged two link classes, from published domain sizes.**
An HGX/DGX A100 baseboard is eight GPUs on six NVSwitches with twelve links from
each GPU to all six of them — a single all-to-all tier, stated verbatim in
NVIDIA's DGX A100 system architecture white paper. HGX B200 is also 8 (two
fifth-generation NVSwitch chips, eighteen links per GPU); GB200 NVL72 is 72 in a
single tier and is reported as a sensitivity rather than borrowed, because the
part this study prices is a B200 SXM module and not a GB200 superchip. Outside
the domain the fabric is ConnectX-6 HDR at 25 GB/s per GPU (A100) or ConnectX-7
NDR at 50 GB/s (B200), one twelfth and one eighteenth of the NVLink rate beside
it. A 93-partition pipeline crosses 81 island-internal boundaries and 11 network
boundaries, not 92 of either.

A collective is now priced by the published cost model for its fabric rather
than by a flat hop count. On a switched fabric an all-reduce is `2 lg p`
traversals in the fabric's own radix (Thakur, Rabenseifner & Gropp, IJHPCA 19(1),
2005) — which inside one NVSwitch tier is 2, independent of rank count, exactly
as the measured speed-of-light all-reduce floor on GB200 comes out
rank-count-independent. On a mesh it is `1.1 × diameter`, which is what Cerebras
measured on their own wafer (Rocki et al., SC20).

**0.9.3 A token cannot cross more stage boundaries than the model has layers.**
This is the correction that moved the number. 672 partitions do not make 671
pipeline stages of a 61-layer model; they make at most 61, and the silicon past
that adds bandwidth and no serial event. The GPU's link cost stops growing with
area at **117.5 µs** — 60 boundaries, 53 inside an NVLink island and 7 across
the network — instead of 1,331 µs at 672 devices.

DeepSeek-V4-Pro, 1M, batch 1, per-user tok/s at equal silicon. `before` is the
published figure; `after` is this re-run, which also carries the KV correction
of section 0.10 — that correction moves these particular rows by at most 0.7×
of a ratio point, so what is shown here is the interconnect rebuild:

| ROM mm² | GPU n | ROM before | GPU before | ratio published | ROM after | GPU after | **ratio now** | band |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 75,795 | 93 | 4,116 | 521 | 7.9× | 4,169 | 526 | **7.9×** | — |
| 79,870 | 97 | 4,021 | 525 | 7.7× | 4,562 | 530 | **8.6×** | 4.8–9.9× |
| 92,450 | 112 | 9,082 | 532 | 17.1× | 9,107 | 544 | **16.7×** | 14.9–17.8× |
| 138,675 | 168 | 9,009 | 538 | 16.7× | 9,633 | 579 | **16.6×** | 14.7–17.7× |
| 277,350 | 336 | 11,570 | 499 | 23.2× | 15,728 | 619 | **25.4×** | 19.9–28.6× |
| 369,800 | 448 | 18,213 | 466 | 39.1× | 18,568 | 630 | **29.5×** | 21.9–34.0× |
| 554,700 | 672 | 22,043 | **407** | **54.2×** | 22,686 | **642** | **35.4×** | 24.5–42.5× |

A dash in the band column is an area at which the best design under one of the two
bounds is a different machine, so the two are not the same comparison and no
interval is quoted.

**The N5-versus-B200 study moves the same way and further.** At 554,700 mm² the
per-user ratio there is **13.1×** against 27.3× under the old serial-depth
accounting — and **4.01× after the latency separation of section 0.12 and the
2026-08-31 link re-grading**, which
supersedes both. The B200's own published NVLink domain sensitivity — 8 GPUs on
an HGX B200 baseboard against 72 in a GB200 NVL72 rack — is worth a further
3–4% to the GPU at every cluster size, reported rather than borrowed because the
part this study prices is a B200 SXM module and not a GB200 superchip.

**The GPU no longer degrades with added silicon.** It rises monotonically from
449 tok/s at 48 devices to 642 at 672. What is left is a saturation, not a
decline: past about eight devices a sparse MoE's routed experts stop spreading
further, so extra HBM bandwidth stops buying weight-fetch time. The remaining
ROM advantage is therefore an advantage over a *flat* GPU curve rather than over
a falling one, and the mechanism is the one this program has always claimed —
weight fetch, not interconnect.

**The mirror-image faults on our own side were larger.** Two of them:

* The on-wafer collective was charged one flat hop however far it reached. A
  57-region all-reduce cost 0.20 µs and now costs 1.93 µs; a 681-region one cost
  0.20 µs and now costs 7.15 µs. Per token at 61 layers that is 24 µs → 235 µs
  and 24 µs → 872 µs. (Those figures are at the re-graded 125 ns hop; at the
  100 ns this section was written against they were 1.54 µs / 5.72 µs and
  188 µs / 698 µs.)
* A twelve-wafer machine was charged the **on-wafer stitching** for its
  wafer-to-wafer links. The only shipping multi-wafer machine is a Cerebras
  cluster whose off-wafer fabric is twelve 100 GbE ports — 150 GB/s against
  26.75 PB/s on-wafer, a factor of 180,000 — with no published latency at all.
  `links.inter_wafer.hop_latency_s` is now a named assumed input at 5 µs, swept
  1–10 µs, and it is the ROM side's most load-bearing assumption after the
  bitcell area ratio.

A third, smaller: a ROM array in the N6-vs-A100 study was charged NVLink-5
bandwidth, 900 GB/s, against an A100 whose published NVLink 3 rate is 300 GB/s.
Each study now charges one fabric to both sides.

**0.9.4 What this exposed and did not fix at the time.** Giving the GPU the
topology sweep changed almost nothing because **the model computed the service
time on the machine's aggregate memory bandwidth and compute roof whatever the
parallelism.** That is right for tensor parallelism and wrong for pipeline
parallelism, and it made pipeline win on both sides at every size above one
device — which is why the topology sweep was inert. **This has since been fixed;
see section 0.12.** It did not cancel in the ratio, the topology sweep is no
longer inert, and every number in section 0.9 that is a per-user rate has moved
again. The 35.4× in this section is superseded by 8.6×.


---

### 0.10 The DeepSeek KV entry sizes were read off the implementation, not measured

Landed separately by the model owner in
`configs/models/deepseek-v4-flash-0731.json` at commit `84577b6` and carried to
`deepseek-v4-pro-0813.json` at `37d0063`, and re-run here. Two per-entry
constants were wrong on both: `entry_bytes` 583 → **1,024** and
`index_entry_bytes` 68 → **256**. The profiles' *structure* was correct and is
unchanged; only the constants moved. Against the reference oracle the Flash
profile now predicts 64,800,000 B/step where the engine reads 64,774,144
(0.9996) at 32K, and 209,184,000 against 209,158,144 (0.9999) at 128K; the
artifact is `results/roofline/deepseek_v4_kv_model_validation.json`. **Pro has
never been executed on the oracle**, so its correction is graded
`assumed_by_analogy` rather than measured and every Pro KV figure inherits that
grade.

The root cause is not a transcription slip: 583 bytes is an FP8 KV assumption —
576 elements at one byte plus scales — where the released implementation reads
the 512-wide latent at BF16. It was a KV *precision* disagreement carried as a
measurement.

| | Flash @200K before | after | Pro @1M before | after |
|---|---:|---:|---:|---:|
| KV read per user token | 99.1 MB | **317.5 MB** | 673.7 MB | **2,207.5 MB** |
| KV storage per user | 705.0 MB | **1,381.6 MB** | 5,028.3 MB | **9,856.0 MB** |
| weight-to-KV read ratio, batch 1 | 113.2:1 | **35.3:1** | 58.9:1 | **18.0:1** |

**At batch 1 this is invisible and above it, it is decisive.** Both machines are
weight-bound at batch 1, so a 3.2× heavier KV read changes the Flash iso-area
ratio from 27.1× to 27.1×. The aggregate picture is a different story, and the
GPU is almost untouched throughout — every GPU figure below moves by less than
2%, so the whole change is ROM-side:

Flash, aggregate tokens/s on the best feasible design at each batch:

*(Both tables below predate section 0.12: their `aggregate` column is the old
`batch x per-user` quantity, and their ratios are superseded.)*

| B | ROM aggregate before | after | ratio before | ratio after | ROM binds on |
|---:|---:|---:|---:|---:|---|
| 1 | 57,266 | 57,260 | 27.1× | **27.1×** | layer_fixed_latency |
| 4 | 228,549 | 183,812 | 33.8× | **27.2×** | layer_fixed_latency |
| 8 | 394,617 | 269,805 | 38.0× | **26.0×** | layer_fixed_latency → **kv_read** |
| 16 | 599,837 | 352,188 | 35.0× | **20.6×** | kv_read |
| 64 | 983,395 | 456,796 | 21.6× | **10.1×** | kv_read |
| 256 | 1,170,513 | 493,437 | 9.4× | **4.0×** | kv_read |

Pro, the same. Its batch-1 iso-area ratio was untouched at 35.4x by *this*
correction because both machines are weight-bound there — section 0.12 has since
taken it to 8.6x, and every aggregate figure in the two tables in this section is
on the old `batch x per-user` definition. Everything above batch 1 moves here
too:

| B | ROM aggregate before | after | ratio before | ratio after |
|---:|---:|---:|---:|---:|
| 1 | 22,721 | 27,022 | 35.4× | **41.5×** |
| 4 | 85,093 | 67,031 | 42.4× | **30.9×** |
| 8 | 115,327 | 84,476 | 38.5× | **25.6×** |
| 16 | 140,242 | 97,113 | 28.6× | **18.6×** |
| 64 | 167,358 | 109,386 | 13.5× | **8.0×** |
| 256 | 175,859 | 112,955 | 5.2× | **3.0×** |

Three things follow. **The batch at which free weight-bound batching gives way
to a KV-bound taper moves down** — from 16 to 8 on Flash and from 8 to 4 on Pro.
**The aggregate advantage at batch 256 falls by 2.4× on Flash and 1.7× on
Pro**, which is the regime a serving deployment actually runs in. And on the
designs common to both runs, **10 Flash points and 6 Pro points that were
feasible are not**, because their KV no longer fits.

Every DeepSeek number in this document is the re-run figure. Qwen is unaffected:
its KV term was already exact against executed hardware.

**The methodological point is the same one as section 0.9 and the same one the
power rebuild in 0.11 turned on.** A number derived by reading an
implementation is a hypothesis. A number derived by running it is a
measurement. Six power terms were derived from primitives, adversarially
verified, and all six were refuted; the one that came back at its submitted
value came back with its grade cut from `derived` to `assumed`, because its
value stood and its derivation did not. Both of the
constants above were hypotheses that had been carried as facts, and neither
survived contact with the oracle. Where this program has both, the measurement
wins; where it has only the reading, the grade must say so.


---

### 0.11 The power model has been rebuilt. It is right on the A100 and 2.9-3.6x low on HC1, and the residual is reported rather than closed

**Superseded, in this direction.** The previous version of this section said
every watt in this program was 7–9× low against both published parts, that the
gap survived at simultaneous peak on the A100, and that `thermal_scale` was
exactly 1.0 at all 11,747 feasible points so no rate depended on the energy
model at all. All of that was true of the model as it then stood. It is no
longer true of any of it.

**How the terms got here, which is the part that matters.** Six power terms
were derived from graded primitives and then adversarially verified against
those primitives, the sources they cited, and the repository's own executed
artifacts. **Every one of the six was refuted.** Not one survived as submitted.
Each verifier returned a corrected value, and **the corrections are what is
applied** — including the two that move power *down*, which is the direction
that makes the headline defect worse.

| term | submitted | applied | direction | why the submission failed |
|---|---:|---:|---|---|
| `power.static_leakage_w_per_mm2.logic` | 0.03 W/mm² | **0.06** | up 2× | Relative Vt offsets were placed inside an exponential that needs the absolute saturation threshold. The resulting 25→100 °C ratio of 12.69× sits *below* the 13.82× ASAP7's own SS liberty measures at a slower process and a lower voltage, which is impossible. Unit also restated: **per mm² of standard-cell region, not of die.** |
| `power.clock_energy_j_per_mm2_per_cycle` | 1.0e-10 | **8.5e-11** | down 15% | Violated its own selection rule (the stated "take the estimator that closes less" yields 8.48e-11). Its second "independent estimator" was not independent and, rebuilt on measured ASAP7 and post-route primitives, returns 578 W on a 400 W part — reported now as a **ceiling check that fails**. |
| `energy.operand_delivery_j_per_byte` | 3.43e-13 | **2.3e-13** | down 1.5× | `α·C·V²` with α = 0.5 double-counts the transition; the correct coefficient for random data is 0.25. The corrected form reproduces Dally's published 45 nm wire figure to 18%; the submitted one missed it by 1.7×. Its Sze et al. citation was a misreading — that figure is normalised only and contains no pJ. |
| `energy.rom_read_j_per_byte` | 8e-14 `derived` | **8e-14 `assumed`** | grade only | Value stood; the derivation did not. Its cross-check was misread by 10.5× (macro-only column, divided by 32 columns instead of 16 sensed weights), its "self-validating" scaling rule tested a factor that cancels, and "five of six fabricated" was false — at most three are. |
| `energy.hbm_j_per_byte` | 1.049e-10 + a static companion | **1.0488e-10, companion dropped** | up 3.36× | The per-byte figure survived and is now the **only `measured` energy term in the file**. The companion could not hold `measured` (its source is an anonymous artifact drop for a paper under review) and its range was false precision — both endpoints were the same measurement times two similar ratios. |
| `gpu_device_fixed_overhead_w` | 52 W, GPU-only | **50 W, both device classes, as a floor** | scope | The leakage evidence was an instrumentation artifact: it averaged a window 4–10 s after a 411 W load stopped. The replicated steady clocked-idle state is 77.03 W, committed as an artifact. Charging a clocked-die floor to only one side of a two-sided comparison is the same class of error as a fitted multiplier and harder to see. |

**Where the watts come from now.** Static power is charged **per mm² per
second against the area split**, not against traffic. Leakage is per mm² of
standard-cell region and per mm² of SRAM array; the clock term is per mm² per
cycle times a graded clock frequency and a region-class multiplier; the
memory-interface idle floor is per HBM stack. The three are combined with the
measured clocked-idle floor by **`max`, never by addition**, because a measured
clocked-idle reading *is* mostly leakage and clock tree, and adding a bottom-up
enumeration of those to a measurement of them double-counts.

| term | A100 at TDP, saturating | Taalas HC1 at its published point |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 3.2 W |
| KV traffic | — | 3.3 W |
| operand delivery | 0.5 W | 10.0 W |
| arithmetic | 31.2 W | 3.7 W |
| static: leakage | 31.4 W | 11.3 W |
| static: clock distribution | 99.0 W | 22.2 W |
| static: memory-interface idle | 14.0 W | — |
| **static charged** | 144.4 W | 50.0 W (the floor binds; the enumeration is 33.5 W) |
| **total** | **389.9 W** | **70.2 W** |
| published | 400 W | 200–250 W |
| **ratio** | **0.97×** | **0.28×** |

**The two new gates, and the outcome stated as an outcome.**

| gate | published | modelled | ratio | tolerance | result |
|---|---:|---:|---:|---:|---|
| A100 80GB at TDP, saturating load | 400 W | 389.9 W | 0.97× | within 2× | **PASS** | <!-- figure: 389.9 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.a100_tdp_power.modelled_value" name="A100 TDP power gate" -->
| Taalas HC1 card power at its published operating point | 200–250 W | 70.2 W | 0.28× | within 2× | **FAIL** | <!-- figure: 70.2 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.modelled_value" name="HC1 card power gate" -->

Both are reported at both ends of the whole power band, with every term moved
together — moving one at a time reports a sensitivity that is really a bias:

| power band | A100 | ratio | HC1 | ratio to 250 W | ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 267.1 W | 0.67× | 54.3 W | 0.22× | 0.27× | <!-- figure: 54.3 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.power_gate_band.low.taalas_hc1_card_power_w" name="HC1 power, band low" -->
| **stated** | **389.9 W** | **0.97×** | **70.2 W** | **0.28×** | **0.35×** | <!-- figure: 0.35 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.detail.ratio_to_band_low" name="HC1 power against the bottom of its band" -->
| high | 626.6 W | 1.57× | 267.1 W | 1.07× | 1.34× | <!-- figure: 267.1 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.power_gate_band.high.taalas_hc1_card_power_w" name="HC1 power, band high" -->

**The A100 gate is the weaker of the two and must not be quoted as
independent.** `power.clock_energy_j_per_mm2_per_cycle` was calibrated as
20–45% of a shipping GPU's published TDP density — a *different* GPU, P100 and
GV100 at 16FF+/12FFN, but still a GPU TDP. Adding that term to the others and
comparing the sum with a GPU's TDP is partly checking an input against its own
family. What the gate does test is that the traffic terms, the arithmetic and
the static terms are mutually consistent in size, and it would fail loudly if
any were an order of magnitude out. **The HC1 gate has no such circularity** —
nothing on the ROM side was calibrated on a Taalas figure, because Taalas
publishes no microarchitecture and no energy at all — **and it is the one that
fails.**

**The residual on HC1 is 2.9–3.6× and none of it was closed by tuning.** Three
things about it are worth stating because each of them runs against the ROM
thesis:

- `energy.rom_read_j_per_byte` moved from 0.5 to 0.08 pJ/B **on the evidence**,
  which made this gate worse by about 4× on that term alone. It was adopted
  anyway. The previous version of this section named that input as the single
  competing explanation for the whole HC1 shortfall; the evidence went the
  other way.
- The ROM array is charged **zero leakage**, because the companion term for it
  was refuted as underived. At the top of its reconstructed 0.006–0.03 W/mm²
  bracket it would add 10.4 W — 70.2 → 80.6 W, still short of 200 W.
- Operand delivery is now the **largest** dynamic term on HC1 (10.0 W of <!-- figure: 10.0 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.detail.dynamic_power_w_by_term.operand_delivery_j" name="HC1 operand-delivery power" -->
  20.2 W), which is a direct consequence of the ROM read term collapsing. A
  mask-ROM array reads its weights for almost nothing; getting those bytes to
  the arithmetic is what it actually pays for.

The honest reading is that a compute-in-ROM part's energy has never been
published at any node, and this model's ROM side is built from macros that are
mostly simulated, at 28–130 nm, with boundaries that do not match the term they
are being asked to supply.

### 0.11.1 The thermal limit binds. It is not the wafers, and it is not batch-dependent

The old throttle rule divided total energy by the total limit, so **stretching
a step always reduced modelled power and every design was coolable at some
speed**. Static power does not fall when a step is stretched, so the coolable
step time now solves

```
P(t) = P_static + E_dynamic / t  <=  cooling_limit
t    >=  E_dynamic / (cooling_limit - P_static)
```

and a part whose leakage and clock alone meet its budget is not slow — **it
does not exist**, which is dark silicon in its strongest form and which the
model previously could not express at all.

<!-- figure: 105 src="results/roofline/n5_vs_b200/analytical.json#power_and_energy.thermally_throttled_points" name="power-limited points, N5/B200" -->
**105 of 6,108 feasible points (1.7%) are power-limited.** All 105 are in the
N5/B200 study; none in N6/A100. The worst is throttled 1.35×, taking a four-chip
3,260 mm² array from 1,560 to 1,151 tok/s per user.

The earlier uniform-multiplier analysis predicted the worst points would be
small dense arrays rather than wafers. **Half of that survives and half does
not:**

- **It survives on shape.** Every throttled point is a small or large array
  (1,600–40,000 mm²). **No wafer is throttled in either study, and no
  wafer-scale ROM design exceeds 47% of its cooling budget**, <!-- figure: 47 src="results/roofline/n5_vs_b200/analytical.json#power_and_energy.wafer_scale_rom_max_power_headroom_fraction" scale="100" tol="1%" name="busiest wafer-scale ROM design, N5" -->
  against a median of 21%. A ROM sweep is a fixed cost spread over far more silicon, so
  wafer-scale is power-*sparse* — which is an argument for wafer-scale that
  this program had not previously been able to make from a correct power term.
- **It does not survive on batch.** A uniform multiplier on a
  traffic-proportional model necessarily peaks at high batch. Static power does
  not scale with traffic, so **batch 1 is throttled too** and the worst point in
  either study is at **batch 8**.
- **A finding the earlier analysis could not have produced at all: every one of
  the 100 throttled points puts its KV in HBM.** The worst point's dynamic
  energy is 96.8% KV read and 0.5% weight read. **The ROM sweep is not what
  melts it.** A mask-ROM array reads weights for almost nothing; what it still
  pays for, at exactly the rate a GPU does, is KV traffic to DRAM. Every
  SRAM-KV ROM design in both studies stays under its budget. That is a design
  conclusion — keep the KV on die — and it is visible only because the power
  model now distinguishes the two paths.

### 0.11.2 Energy per token, which has been unpublishable until now

Not paying DRAM access energy for weights is much of the ROM argument, and the
model could not state it while every watt in it was 7–9× low. The figures
include the static share amortised over the tokens the step actually produces,
so a machine that is fast and leaky is not flattered against one that is slow
and cool.

At the two anchors, on the same workload — Llama-3.1-8B at batch 1:

| part | J/token | W | tok/s |
|---|---:|---:|---:|
| Taalas HC1 (modelled reconstruction) | **0.005736** | 70.2 | 12,232 | <!-- figure: 0.005736 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.detail.energy_j_per_token" name="HC1 J/token" -->
| A100 80GB, weight-bound gate, same model and batch | **1.462191** | 358.8 | 245 | <!-- figure: 1.462191 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.a100_weight_bound.detail.step.metrics.energy_j_per_token" name="A100 J/token at the weight-bound gate" -->

That is 255× in tokens per joule, and **it is a ceiling on the ROM advantage,
not a measurement of it**, for three reasons that all point the same way: the
GPU is at batch 1, which is a GPU's worst operating point; the ROM side's read
energy is `assumed` over a 17× bracket; and the HC1 power gate says the ROM
total is 2.9–3.6× below a shipping part, so the ROM joules are a lower bound by
roughly that factor.

At equal area, on the study's own best designs, the advantage is far smaller
and it moves with batch in the direction the architecture predicts:

| study | model | batch 1 | batch 256 |
|---|---|---:|---:|
| N6 vs A100 | Qwen3-8B (dense) | 19.3× | **1.8×** | <!-- figure: 1.8 src="results/roofline/n6_vs_a100/analytical.json#power_and_energy.energy_per_token[model=Qwen3-8B,batch_size=256].tokens_per_joule_advantage_x" name="Qwen3-8B tokens/joule advantage at batch 256, N6" -->
| N6 vs A100 | DeepSeek-V4-Flash (sparse) | 17.3× | **55.5×** |
| N6 vs A100 | DeepSeek-V4-Pro (sparse) | 25.9× | 18.8× |
| N5 vs B200 | Qwen3-8B (dense) | 5.3× | **2.6×** |
| N5 vs B200 | DeepSeek-V4-Flash (sparse) | 4.6× | **36.9×** | <!-- figure: 36.9 src="results/roofline/n5_vs_b200/analytical.json#power_and_energy.energy_per_token[model=DeepSeek-V4-Flash-0731,batch_size=256].tokens_per_joule_advantage_x" name="Flash tokens/joule advantage at batch 256, N5" -->
| N5 vs B200 | DeepSeek-V4-Pro (sparse) | 14.3× | 20.9× |

**A dense model gives the energy advantage back as batch rises and a sparse one
does not.** The GPU amortises one weight read over the whole batch, so its
joules per token fall roughly as 1/batch until KV takes over; the ROM part's
weight read was already nearly free, so it has nothing to amortise. On a sparse
model the GPU cannot amortise — batching engages more experts — so the ROM
advantage grows instead. **Every ROM figure in this table is a lower bound by
the HC1 gate's 2.9–3.6×; every GPU figure rests on a measured, peer-reviewed
HBM number and a gate that lands within 3% of a published TDP. The two sides
are not equally well founded and the ratio inherits the weaker of them.**

**What is still missing, and it is now a short list.** L1/L2 traversal, which
the same SC 2025 paper measures at a further 6.30 pJ/bit on an A100 for
streaming traffic and which this model charges at zero on both sides. The
long-path operand ladder — the scalar applied here is the *tile-local floor*,
and HBM→L2→register file is 8–10 pJ/B further. ROM-array leakage, held at zero
because its companion was refuted. And a fabricated leading-node mask-ROM macro
reporting read energy at the macro boundary separately from compute, which
would settle the term the HC1 gate is failing on: **no such part exists.**

---

### 0.12 Per-user latency and aggregate throughput were one number. Separating them is the largest correction this program has made

**RETRACTED: every per-user rate in every previous version of this document at
every multi-device operating point.** The headline case: DeepSeek-V4-Pro at 1M
context, batch 1, at 554,700 mm² was published as 54.2×, corrected to 35.4× by
the interconnect rebuild, and is **8.6×** now. This is not a refinement of that
correction; it is a different error that the interconnect rebuild uncovered and
section 0.9.4 named without fixing.

**The defect.** The service time was computed on the machine's *aggregate*
memory bandwidth and compute roof, and the hops a single token crosses were then
added to it. That mixes two views. The aggregate denominator is correct only for
partitions that are all working on the same token at the same instant — which is
what tensor parallelism is. Under pipeline parallelism a token is served by one
stage's silicon at a time and has to visit every stage in turn, so a balanced
`S`-stage pipeline's per-user latency is `S` times what was charged.

**The physics, because it is the whole argument.** Under pipeline parallelism
each of `N` stages holds `1/N` of the weights and reads them with `1/N` of the
machine's bandwidth. **The two cancel exactly.** One user's latency on an
`N`-device pipeline is what it would be on a single device holding the whole
model at one device's bandwidth, minus whatever the hops take off it. *Adding
devices under pipeline parallelism buys aggregate throughput and buys one user
nothing.* Tensor parallelism is different in kind rather than in degree: every
partition is on the same token, so the whole machine's bandwidth is on that
token's critical path, and the price is two all-reduces per layer.

**The fix.** `token_slots = partitions / tensor_group` counts the independent
groups the machine is cut into. One user's latency is

```
t_user = token_slots × t_service(microbatch) / stage_balance + t_link + t_layer
```

where `microbatch = max(1, batch / token_slots)` is the users sharing one weight
pass inside one slot. The machine's aggregate rate is that same latency with a
user in **every** slot:

```
aggregate_tokens_s = fill_users / t_user,  fill_users = max(batch, token_slots)
```

capped by the users whose KV the machine can actually hold — the cap is reported
per point as `pipeline_fill_limited_by`. **`aggregate = batch × per-user` no
longer holds**, and what a machine delivers at the requested concurrency is
reported separately as `delivered_tokens_s`. The identity survives exactly where
it is true: a one-slot machine, which is a single chip or a tensor group
spanning every partition.

**Both validation gates are unchanged to the digit.** A100 weight-bound at
253.91 tok/s (ratio 1.0000) and Taalas HC1 at 12,232.40 against 16,960, ratio
0.7213. Both are single-device machines with `token_slots = 1`, so a correct
separation cannot reach them; the consistency audit now asserts that a one-slot
machine has a latency correction of exactly 1.0, at all 99,147 checks.

**What is not charged.** Three things, and the first two flatter the deep
pipeline while the third flatters the machine this correction promoted.

*Fill and drain cost nothing.* Aggregate throughput is the steady-state rate, so
a request short compared with the slot count pays up to one traversal that is
not billed.

*A deep pipeline's implied weight replication is not charged against capacity.*
Past the layer count the surplus partitions hold replicas of a stage, each
needing its own copy of that stage's weights; the capacity check still credits
the machine with holding the model once. With fill/drain, this favours the
deepest pipelines, which after this correction are on the GPU side, so charging
them would widen the ROM ratios rather than narrow them.

*The `stage_balance` derate is applied per **device**, not per partition.*
`efficiencies.stage_balance` (0.9, assumed) charges a multi-device machine for
imperfect layer balance, and the model applies it when `device_count > 1`. A
single wafer partitioned into 57 tensor-parallel reticle fields has
`device_count = 1` and escapes it; a twelve-wafer machine does not. That is a
**1.11× bias in favour of the one-wafer design that now wins at batch 1 for two
of the three models**, and it runs the opposite way to the two above. It is left
as it is rather than changed, because whether a monolithic co-designed floorplan
deserves the same balance derate as a model cut across parts nobody co-designed
is a modelling judgement and not an arithmetic slip — but the direction is stated
here so it is not mistaken for a result.

**It did not cancel in the ratio.** The tempting argument is that both families
are pipelines of similar depth at iso-area, so the `N` cancels. It does not.
Per-user tok/s at batch 1 on the same seven-rung area ladder, `n6_vs_a100`, from
`The latency separation, before and after` in the study report. `before` is not a
memory of an earlier run: every point now carries
`per_user_tokens_s_throughput_view`, the number the old rule produced, and each
side is ranked by it, so the `before` column reproduces the previous *topology
choice* as well as the previous rate:

| model | mm² | ROM before → after | ROM topology before → after | GPU n | GPU before → after | GPU topology | ratio before | **ratio now** | change |
|---|---:|---:|---|---:|---:|---|---:|---:|---:|
| Qwen3-8B | 46,225 | 51,291.3 → 6,505.3 | wafer-pipeline → wafer-tensor | 56 | 3,440.9 → 789.4 | pipeline → tensor | 14.91× | **8.24×** | 0.55× |
| Qwen3-8B | 92,450 | 48,716.3 → 5,878.5 | wafer-pipeline → wafer-hybrid | 112 | 5,074.5 → 848.7 | pipeline → tensor | 9.60× | **6.93×** | 0.72× |
| Qwen3-8B | 138,675 | 48,716.3 → 5,391.7 | wafer-pipeline → wafer-hybrid | 168 | 6,028.6 → 870.5 | pipeline → tensor | 8.08× | **6.19×** | 0.77× |
| Qwen3-8B | 184,900 | 48,716.3 → 4,979.3 | wafer-pipeline → wafer-hybrid | 224 | 6,654.1 → 881.8 | pipeline → tensor | 7.32× | **5.65×** | 0.77× |
| Qwen3-8B | 277,350 | 48,716.3 → 4,318.7 | wafer-pipeline → wafer-hybrid | 336 | 7,424.4 → 565.8 | pipeline → tensor | 6.56× | **7.63×** | 1.16× |
| Qwen3-8B | 369,800 | 48,716.3 → 3,812.9 | wafer-pipeline → wafer-hybrid | 448 | 7,880.6 → 568.2 | pipeline → tensor | 6.18× | **6.71×** | 1.09× |
| Qwen3-8B | 554,700 | 56,411.9 → 3,447.0 | wafer-pipeline → wafer-hybrid | 672 | 8,396.5 → 570.6 | pipeline → tensor | 6.72× | **6.04×** | 0.90× |
| Flash @200K | 46,225 | 18,475.6 → 4,663.6 | wafer-pipeline → wafer-tensor | 56 | 1,485.7 → 544.1 | pipeline → tensor | 12.44× | **8.57×** | 0.69× |
| Flash @200K | 92,450 | 27,333.1 → 4,472.2 | wafer-pipeline → wafer-hybrid | 112 | 1,703.4 → 568.8 | pipeline → tensor | 16.05× | **7.86×** | 0.49× |
| Flash @200K | 138,675 | 34,088.9 → 4,375.0 | wafer-pipeline → wafer-hybrid | 168 | 1,795.0 → 578.0 | pipeline → tensor | 18.99× | **7.57×** | 0.40× |
| Flash @200K | 184,900 | 38,879.0 → 4,281.2 | wafer-pipeline → wafer-hybrid | 224 | 1,845.5 → 582.8 | pipeline → tensor | 21.07× | **7.35×** | 0.35× |
| Flash @200K | 277,350 | 45,220.6 → 4,104.3 | wafer-pipeline → wafer-hybrid | 336 | 1,899.6 → 404.0 | pipeline → tensor | 23.81× | **10.16×** | 0.43× |
| Flash @200K | 369,800 | 49,229.4 → 3,941.1 | wafer-pipeline → wafer-hybrid | 448 | 1,928.1 → 405.2 | pipeline → tensor | 25.53× | **9.73×** | 0.38× |
| Flash @200K | 554,700 | 54,012.8 → 3,650.5 | wafer-pipeline → wafer-hybrid | 672 | 1,957.7 → 406.4 | pipeline → tensor | 27.59× | **8.98×** | 0.33× |
| Pro @1M | 92,450 | 8,986.6 → 2,359.5 | wafer-pipeline → wafer-hybrid | 112 | 529.1 → 274.9 | pipeline → tensor | 16.99× | **8.58×** | 0.51× |
| Pro @1M | 138,675 | 9,497.6 → 2,016.1 | wafer-pipeline → wafer-hybrid | 168 | 561.6 → 283.0 | pipeline → tensor | 16.91× | **7.12×** | 0.42× |
| Pro @1M | 184,900 | 11,753.0 → 2,002.6 | wafer-pipeline → wafer-hybrid | 224 | 579.7 → 287.4 | pipeline → tensor | 20.27× | **6.97×** | 0.34× |
| Pro @1M | 277,350 | 15,371.5 → 1,972.0 | wafer-pipeline → wafer-hybrid | 336 | 599.4 → 221.0 | pipeline → tensor | 25.65× | **8.92×** | 0.35× |
| Pro @1M | 369,800 | 18,073.4 → 1,933.6 | wafer-pipeline → wafer-hybrid | 448 | 609.8 → 222.4 | pipeline → tensor | 29.64× | **8.70×** | 0.29× |
| Pro @1M | 554,700 | 21,951.3 → 1,863.2 | wafer-pipeline → wafer-hybrid | 672 | 620.6 → 223.7 | pipeline → tensor | 35.37× | **8.33×** | 0.24× |

The N5-versus-B200 study moves the same way: Pro at 554,700 mm² goes from
**13.06× to 4.01×**, and every rung of that ladder falls.

**Three mechanisms put the change where it is, and none of them cancels.**

1. *The two families reach iso-area at very different slot counts.* At
   554,700 mm² the ROM side is twelve wafers spanning 681 reticle fields; the
   GPU side is 672 devices. Charged as pipelines those raw corrections are close
   — 16.4× against 14.7× on Qwen. But the correction is not applied to a fixed
   topology, which is mechanism 2.
2. *It changes which topology wins, and the winner is chosen per design.* **Both
   families abandon pipeline at batch 1.** The GPU goes to `tensor`: one slot,
   the whole cluster on one token, 122 all-reduces per token for Pro. The ROM
   side goes to `wafer-tensor` on one wafer and `wafer-hybrid` above it —
   tensor-parallel across each wafer's reticle fields, pipeline-parallel across
   wafers, so its slot count is the *wafer* count rather than the field count.
   That is the finding section 0.9.4 predicted would appear and could not
   produce: the topology sweep is no longer inert, and tensor parallelism is now
   the right choice at batch 1 on both sides.
3. *The two sides pay very different prices for that switch.* A wafer's mesh
   collective is cheap enough to afford a 57-to-84-way tensor group; a GPU
   cluster large enough to hold DeepSeek-Pro spans 84 NVLink islands, so most of
   its all-reduce crosses InfiniBand. Where the GPU's correction exceeds the
   ROM's the ratio **rises** — Qwen at 277,350 mm², 6.56× to 7.63×. Where the
   ROM's exceeds the GPU's it falls — Pro at 554,700 mm², 35.37× to 8.33×.

**The batch curves change shape, and for the sparse models they change sign.**
Per-user tok/s at equal silicon, best design on each side at each batch:

| batch | Qwen3-8B @8K | DeepSeek-Flash @200K | DeepSeek-Pro @1M |
|---:|---:|---:|---:|
| 1 | 8.24× | 8.57× | 8.58× |
| 8 | 6.85× | 11.58× | 14.75× |
| 32 | 4.19× | 19.76× | 18.48× |
| 64 | 2.71× | 24.71× | 18.35× |
| 256 | **0.98×** | **35.13×** | **17.18×** |

Under the old rule every one of these fell with batch — Flash from 27.1× at
batch 1 to 4.0× at 256 — and "the advantage erodes with batch" was one of this
document's standing findings. **It survives only for the dense model.** For both
sparse models the per-user ratio now *rises* with batch, because the GPU's
per-user rate collapses faster than the ROM's: a GPU cluster large enough to
hold DeepSeek-Flash has to choose between a pipeline whose slots multiply its
latency and a tensor group whose collective it cannot afford, and at batch 256
the best it can do is 38 tok/s per user against the ROM machine's 1,399. Qwen is
the counter-case and the honest one: at batch 256 the GPU wins outright, 516
against 475, because a dense model's KV read is per-user, never amortises, and is
what binds a ROM machine at batch.

**What survives and what does not.** The *direction* at batch 1 survives
everywhere: at equal silicon a ROM design is still faster per user than a GPU
cluster at every rung, by 5.7× to 10.9× on N6-vs-A100 and 3.5× to 6.8× on
N5-vs-B200. What is
gone is the claim that the advantage **grows** with silicon. It does not. The
ROM side's per-user rate now *falls* monotonically with area under every topology
it can run — 7,936 tok/s on one wafer to 3,811 on twelve for Qwen — because more
silicon means either more slots for a token to traverse or a wider collective for
it to wait on. **The best per-user ROM machine is the smallest one that holds the
model.** That inverts section 2.3 as it was written.

---

### 0.13 The study named a "best design" by a rule that could not see area, and it handed an 8B model a wafer

**This is the correction that moves the recommendation in §2.3, and it moves
nothing else.** Every per-user rate in this document is unchanged to the digit.

The old rule is `_pick_best` in `tools/run_roofline_studies.py`: rank the
feasible ROM designs by per-user tokens/s, take the best rate, keep everything
within `BEST_DESIGN_TOLERANCE = 5%` of it, and report the smallest silicon in
that band. Its docstring says the tolerance stops an 8B model being handed a
46,225 mm² wafer. It does not, and the artifact says so: for Qwen3-8B at batch 1
the wafer's 6,505 tok/s is the per-user peak, the 5% floor is 6,180, and the
best sub-wafer design in the study reaches 3,530 — 54% of the peak. The band
never engages. **A 5% rate tolerance is a tie-break among near-peak designs and
is orthogonal to area**, so it shrinks the machine exactly in the cases nobody
was worried about and never in the case everybody is.

What it published for Qwen3-8B at N6: **one 46,225 mm² wafer at 6,505 tok/s per
user and 141 tok/s per 1,000 mm²**, for a checkpoint whose ROM array is 1,011 mm²
and which the study's own design generator holds in **three 815 mm² reticle
dies** at 2,791 tok/s per user and 1,142 tok/s per 1,000 mm². That is **2.33× the
per-user rate for 18.9× the silicon**, at one eighth of the throughput density,
on a model where — after the fix in §0.13.1 — both machines hold exactly one
8,192-token session.

**The replacement rule is stated in the reports it governs**, in a section
called *The recommended design per model, and the rule that picks it*, and it
has two parts:

1. **Domination filter.** Keep every feasible design that no other feasible
   design of the same model and batch beats on **both** per-user tokens/s and
   tokens/s per 1,000 mm². That non-dominated set is the published frontier.
2. **Marginal-return walk.** Order the frontier by area, start at the smallest
   feasible machine, and accept each larger rung only while the per-user
   tokens/s it adds per added mm² is strictly greater than the tokens/s per mm²
   the incumbent already returns on average. Ties go to the smaller machine.

The bar is parity, not a tuned fraction, and it cannot be used to move an
answer: at parity the walk is algebraically identical to maximising per-user
tokens/s per mm², because accepting when `(r − r0)/(a − a0) ≥ r0/a0` is exactly
`r/a ≥ r0/a0`. The marginal form is the one to read because it is the
engineering question — *does the next slab of silicon work at least as hard as
the slab you already bought?*

Three things follow that the old rule could not deliver.

**The class is now chosen per model, on evidence.** One rule gives an array for
Qwen3-8B and a wafer for both DeepSeek models at N6. The study is no longer
answering "wafer" three times and calling it a finding.

**The frontier is published, not just the pick.** Where the recommendation is a
curve rather than a point the whole curve is in the report with per-user rate,
aggregate rate, resident sessions, throughput density, watts, mJ/token and the
binding constraint on every row, so a reader with a latency target this study
does not know about can read their own machine off it. An honest curve beats a
false single answer.

**The recommendation is recomputed at every batch and the regimes are
reported.** For Qwen3-8B at N6 the answer changes at batch 2 — from a
one-session SRAM-KV array to a 298-session HBM-KV array at 4,075 mm² — and
saying so is the point rather than an embarrassment.

The property is pinned by a test,
`test_a_recommended_design_is_never_dominated_on_both_axes`, which checks the
recommendation against the raw point list rather than against the frontier the
selector built, so a bug in the selector fails the test instead of producing a
self-consistent wrong answer. It pins the property and not an area, a device
count or a topology, because those have to be retyped every time a technology
input moves and the property does not.

### 0.13.1 A one-byte float shortfall was inflating the aggregate throughput of every SRAM-KV design at batch 1

Found while making the recommendation quotable. `evaluate` tested capacity
feasibility with a one-byte tolerance — `resident_kv > remaining + 1.0` — and
then computed `max_resident_users` from an **exact** floor division. On a design
sized to hold precisely one session the two disagree: the three-reticle Qwen
machine's SRAM comes out at **1,207,959,551.9999998 B** against a session
needing **1,207,959,552.0 B**, so it was feasible for one user and reported room
for zero. Zero is falsy, and the pipeline-fill cap that reads it was written
`if max_resident_users and fill_users > max_resident_users`, so **the cap was
skipped on exactly the machines that needed it most** and the design published
the aggregate rate of as many sessions as it had pipeline stages.

Both now read one constant, `CAPACITY_TOLERANCE_BYTES`. The blast radius,
measured by diffing the artifacts before and after:

| quantity | n6_vs_a100 | n5_vs_b200 |
|---|---:|---:|
| points evaluated | 4,688 | 4,592 |
| `per_user_tokens_s` changed | **0** | **0** |
| `step_time_s` changed | **0** | **0** |
| `feasible` changed | **0** | **0** |
| `binding_constraint` changed | **0** | **0** |
| `aggregate_tokens_s` changed | 14 | 8 |
| `max_resident_users` changed | 176 | 96 |
| `power_w`, `energy_j_per_token`, `pipeline_fill_users` changed | 69 | 24 |

Every changed aggregate is a batch-1 SRAM-KV row and every one of them fell. The
largest was `Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x12-romfill`, which
claimed **96,897 tok/s aggregate** on a machine that holds one session; it now
reports **142**. The three-reticle machine this document now recommends fell
from 8,373 to **2,791**, which is its per-user rate, because one session is all
it holds. **No latency number in this document moved.**

## 1. The result

> **The tables in this section are the design space, not the recommendation.**
> They report the best design *per amortisation policy and floorplan*, which is a
> different question from "which machine should be built" — §2.3 answers that,
> by the rule §0.13 states, and the two do not pick the same rows.

**This table now has two halves and they select different machines.** Since
section 0.12 the study reports per-user latency and aggregate throughput as
separate quantities, and the design that maximises one is usually not the design
that maximises the other: the throughput-optimal ROM machine is a deep pipeline
with a poor per-user rate, and the latency-optimal one is the smallest machine
that holds the model with a tensor group across it. Reading one number as the
other is the error section 0.12 retracts.

Best feasible design per policy at a **matched floorplan**, N6 ROM silicon,
against the best iso-area GPU cluster, from `The batch-amortisation fork` and the
points behind it. `spare = sram` sizes the array to the stored bytes and gives the
rest to KV store or MAC array; `spare = rom` grows the array into that silicon as
replicated copies.

**Aggregate tokens/s — the machine's rate with every slot occupied:**

| model | B | spare | ROM+MAC | compute-in-ROM | + per-region | best GPU at equal area |
|---|---:|---|---:|---:|---:|---|
| Qwen3-8B @8K | 1 | sram | 12,313 | 13,035 | 13,035 | 5,307 (pipeline) |
| | 1 | rom | **133,002** | 24,132 | 24,132 | 63,690 (pipeline) |
| | 64 | sram | 73,121 | 13,038 | 13,038 | 42,460 (pipeline) |
| | 64 | rom | **133,002** | 12,315 | 12,315 | 63,690 (hybrid) |
| DeepSeek-Flash @200K | 1 | sram | 13,021 | 13,021 | 13,021 | 1,827 (pipeline) |
| | 1 | rom | **273,946** | 28,772 | 28,772 | 2,607 (pipeline) |
| | 8 | sram | 25,598 | 13,021 | 26,192 | 2,645 (tensor) |
| | 64 | sram | **118,863** | 13,026 | 46,493 | 7,656 (tensor) |
| | 64 | rom | **273,946** | 28,794 | 57,740 | 7,344 (tensor) |
| | 256 | sram | **270,399** | 13,054 | 94,029 | 9,772 (tensor) |
| DeepSeek-Pro @1M | 1 | sram | 11,752 | 11,745 | 11,745 | 701 (pipeline) |
| | 64 | sram | **49,885** | 11,745 | 27,433 | 2,973 (tensor) |
| | 256 | sram | **67,551** | 11,745 | 55,455 | 3,898 (tensor) |

**Per-user tokens/s — one user's rate on the same designs:**

| model | B | spare | ROM+MAC | compute-in-ROM | + per-region | best GPU at equal area |
|---|---:|---|---:|---:|---:|---|
| Qwen3-8B @8K | 1 | sram | 216 | 229 | 229 | 891 (tensor) |
| | 1 | rom | 195 | **4,022** | **4,022** | 622 (tensor) |
| | 64 | sram | **1,143** | 204 | 204 | 581 (hybrid) |
| | 64 | rom | 195 | 192 | 192 | 586 (hybrid) |
| DeepSeek-Flash @200K | 1 | sram | 228 | 228 | 228 | 600 (tensor) |
| | 1 | rom | 402 | 505 | 505 | 437 (tensor) |
| | 8 | sram | 3,200 | 228 | **3,274** | 331 (tensor) |
| | 64 | sram | **1,857** | 204 | 726 | 120 (tensor) |
| | 64 | rom | 402 | 450 | **902** | 115 (tensor) |
| | 256 | sram | **1,056** | 51 | 367 | 38 (tensor) |
| DeepSeek-Pro @1M | 1 | sram | 17 | **41** | **41** | 237 (tensor) |
| | 64 | sram | **779** | 41 | 429 | 46 (tensor) |
| | 256 | sram | **264** | 41 | 217 | 15 (tensor) |

**Read the second table before quoting the first.** Several rows where the ROM
side's aggregate is an order of magnitude ahead are rows where its *per-user*
rate is behind the GPU's — DeepSeek-Pro at batch 1 on the `sram` floorplan is
11,752 aggregate against 701, and 17 tok/s per user against 237. That machine is
a 681-slot pipeline. It is a throughput machine and it is not a latency machine,
and the previous version of this table could not say so because it reported one
number for both.

**Three independent corrections have moved figures in this table since it was
last published, and they must not be read as one.**

*The latency separation* (section 0.12) redefined both columns. The aggregate
column is now the machine's rate with every slot occupied rather than
`batch × per-user`, and the per-user column is the full serial path. It is the
largest of the three and it is the reason the two tables disagree about which
machine to build.

*The interconnect rebuild* (section 0.9) moved every multi-device design on both
sides, because link latency is on the critical path of all of them.

*The DeepSeek-Flash KV measurement* (section 0.10) moved the Flash rows and
nothing else. It is invisible at batch 1 and decisive above it.

---

## 2. Recommendation

### 2.1 The *throughput* case for compute-in-ROM over ROM-plus-MAC is RETRACTED. The case that survives is an area case.

The previous recommendation was "build compute-in-ROM, not ROM feeding a MAC
array — it wins at batch 1 on every model by ~1.5×". That 1.5× was the cell
multiplier applied to area and not to bandwidth. With the correction the two
machines are **the same machine at batch 1 for the same budget**: at one user
per slot each policy sweeps its array once, and `rom_sweeps_per_step` is 1 for
both. What separates them at batch 1 in the tables above is not the amortisation
rule but the *floorplan* it forces — a compute-in-ROM cell is 1.6× the area, so
the two policies solve to different area splits and the sizing sweep can pick
different machines. On the `sram` floorplan at batch 1 that is worth 6% to
compute-in-ROM on Qwen (229 against 216 tok/s per user) and nothing on either
DeepSeek model.

Do not restate the win as a bandwidth argument. Whatever case exists is about
**area**: the multiply moves into the array and the MAC array's silicon is
recovered. On the anchor die, from *The two ROM floorplans on one die*:

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0× | 1.6× |
| ROM array | 216.8 mm² | 346.9 mm² |
| compute block | 451.5 mm² | 16.3 mm² (pre-compute only) |
| SRAM | 0.0 mm² | 305.1 mm² |
| sustained fp8 roof | 2.214e14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.107e14 | n/a |
| weight bytes/s the array supplies | 4.589e13 | 4.589e13 |
| **can the compute block be fed?** | **0.41×** | nothing to feed |
| full-array sweep | **76.55 µs** | **76.55 µs** |

More than half the storage machine's die is a MAC array that can be fed at 0.41×
of what it wants at one weight byte per multiply-accumulate. That is the honest
argument, and the corrected model tests it directly: give both machines the
option of spending spare silicon on a replicated array instead, and the
amortising machine's balanced floorplan — MAC array sized to consume exactly
what the array beside it can read — closes most of the gap.

**The convergence this section previously claimed is retracted.** It said that
on Flash at batch 64 with `spare = rom` both machines reach 372,307 tok/s and
both bind on `kv_read`. Under the separated views they do not converge: the
amortising machine reaches 273,946 aggregate and compute-in-ROM 28,794, because
the throughput-optimal amortising design is a twelve-wafer pipeline whose slots
are all occupied and the compute-in-ROM design is a single wafer. The two
policies converge on *per-user* rate there instead — 402 against 450 tok/s — and
that is the comparison the earlier sentence should have been making.

The second surviving argument, that compute-in-ROM moves no weights and
therefore burns no transport energy, **this model does not represent at all**:
its energy term charges `rom_read_j_per_byte` against engaged bytes identically
for both policies. Do not read that silence as support.

**Where this leaves the decision.** The model does not choose between the two
machines on throughput; it ties them at batch 1 and splits above it depending on
the floorplan. If the choice is to be made on energy or on throughput per mm², it
must be made with an instrument that measures those — and the study already
reports `tok/s/mm2` in the floorplan sweep, where the replicated-array designs
are *worse* per unit silicon (Flash at batch 8: 0.554 tok/s/mm² on one wafer
against 0.494 on twelve). Replication buys sweep time and costs throughput
density. That trade is the real content of this section.

### 2.2 Per-region activation is still the highest-value departure from what Taalas built — at a third of the claimed value

The mechanism is untouched by every correction above: per-region activation
changes sweep *depth*, not sweep *rate*. What changed is how deep the sweep
actually is. At a matched floorplan, per-region over a global activation
broadcast:

| model | B=1 | B=8 | B=32 | B=64 | B=256 |
|---|---:|---:|---:|---:|---:|
| DeepSeek-Flash @200K | 1.00× | 2.01× | 5.46× | 3.57× | **7.20×** |
| DeepSeek-Pro @1M | 1.00× | 1.02× | 2.13× | 2.34× | **4.72×** |
| Qwen3-8B @8K (dense) | 1.00× | 1.00× | 1.00× | 1.00× | 1.00× |

The retracted figure was 27× at batch 64; this document then published 10.65×,
then 7.44×. It is now **3.57× at batch 64 and 7.20× at batch 256**, and the peak
has moved up the batch axis because of section 0.12: on a machine cut into slots,
the batch is spread across them and each slot sees `batch / token_slots` users,
so the region-collision statistic that per-region activation exploits does not
begin to bite until the batch exceeds the slot count. **The dense row is not a
disappointment, it is the mechanism working**: per-region recovers ROM regions
that a sparse router left idle, and Qwen has no experts, so there is nothing to
recover. Any claim that a dense model benefits from per-region activation is
wrong on the face of the design.

Against the amortising machine at a matched floorplan, per-region now **loses at
43 of 48 operating points**. The previous version of this document reported it as
losing at 4 of 30 and, before that, as never losing. Two corrections put it
there: the busiest-region statistic replacing the mean, and the separation of
per-user latency from aggregate throughput, which lets the amortising machine
occupy a deep pipeline's slots with users that a compute-in-ROM machine would
have to sweep for one at a time.

The design and its sizing are in `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`. The
pre-compute block is 2.0% of a region; the activation distribution network is the
real cost and neither document prices it.

### 2.3 Array or wafer: one rule, and it no longer answers "wafer" three times

**The previous version of this section is superseded and the sentence that has
to go is its conclusion**: *"The right latency machine is the smallest one that
holds the model: one wafer for Qwen and Flash, two for Pro."* That was read off a
rule that ranks by per-user rate and cannot see area (§0.13). Under the rule the
reports now state and apply — domination on both axes, then a marginal-return
walk from the smallest feasible machine — the answer splits by model:

| model | recommended design | mm² | devices | user tok/s | tok/s per 1,000 mm² | resident sessions | binds on |
|---|---|---:|---:|---:|---:|---:|---|
| Qwen3-8B @8K | `…SRAMKV-array-pipeline-x3` | **2,445** | 3 × 815 mm² | 2,791.2 | **1,141.6** | 1 | `compute` | <!-- figure: 2,445 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.silicon_area_mm2" name="Qwen recommended area, N6" --> <!-- figure: 2,791.2 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="Qwen recommended per-user rate, N6" --> <!-- figure: 1,141.6 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.tokens_s_per_1000mm2" name="Qwen recommended throughput density, N6" -->
| DeepSeek-Flash @200K | `…HBMKV-wafer-tensor-x1-romfill` | **46,225** | 1 wafer | 4,663.6 | **100.9** | 448 | `link_latency` | <!-- figure: 46,225 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.silicon_area_mm2" name="Flash recommended area, N6" --> <!-- figure: 4,663.6 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_tokens_s" name="Flash recommended per-user rate, N6" --> <!-- figure: 100.9 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.tokens_s_per_1000mm2" name="Flash recommended throughput density, N6" -->
| DeepSeek-Pro @1M | `…SRAMKV-wafer-hybrid-x2` | **92,450** | 2 wafers | 2,359.5 | **25.5** | 1 | `link_latency` | <!-- figure: 92,450 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.silicon_area_mm2" name="Pro recommended area, N6" --> <!-- figure: 2,359.5 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_tokens_s" name="Pro recommended per-user rate, N6" --> <!-- figure: 25.5 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.tokens_s_per_1000mm2" name="Pro recommended throughput density, N6" -->

**An 8B model gets three reticle dies. It never should have got a wafer.** The
walk stops at the first rung for Qwen because the next one buys 44.6 tok/s per
1,000 mm² of added silicon against 1,141.6 the machine already returns — a
twenty-fold worse return — and the wafer, four rungs further on, buys 84.8. For
Flash and Pro the walk stops at the first rung too, but for the opposite reason:
there is nothing else on the frontier at all. **For those two models the wafer
wins on both axes at once**, which is what a one-row frontier means, and it is a
stronger result than the old table's ratio because it needs no trade-off to be
argued. Pro's is not even a preference: 94 reticles of mask ROM exceeds one
57-reticle wafer, so wafer-scale is a capacity floor there and the question is
only *how many*, to which the answer is the fewest that hold the model.

**Iso-area, read at the area the rule chose rather than at a ladder rung.** The
comparator is N copies of the one unified 826 mm² A100 die, N set by the ROM
side's own area, and the cluster picks its own parallelism:

| model | ROM mm² | GPU | GPU mm² | ROM user tok/s | GPU user tok/s | ratio | ROM sessions | GPU sessions |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 2,445 | 3 × A100, tensor | 2,478 | 2,791.2 | 258.9 | **10.78×** | 1 | 165 | <!-- figure: 2,478 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.iso_area_gpu_silicon_area_mm2" name="Qwen iso-area GPU silicon, N6" --> <!-- figure: 258.9 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.iso_area_gpu_per_user_tokens_s" name="Qwen iso-area GPU rate, N6" --> <!-- figure: 10.78 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_speed_ratio" name="Qwen recommended-design iso-area ratio, N6" --> <!-- figure: 165 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.iso_area_gpu_max_resident_users" name="Qwen iso-area GPU resident sessions, N6" -->
| DeepSeek-Flash | 46,225 | 56 × A100, tensor | 46,256 | 4,663.6 | 544.1 | **8.57×** | 448 | 2,797 | <!-- figure: 46,256 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.iso_area_gpu_silicon_area_mm2" name="Flash iso-area GPU silicon, N6" --> <!-- figure: 544.1 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.iso_area_gpu_per_user_tokens_s" name="Flash iso-area GPU rate, N6" --> <!-- figure: 8.57 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_speed_ratio" name="Flash recommended-design iso-area ratio, N6" --> <!-- figure: 448 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.max_resident_users" name="Flash recommended resident sessions, N6" -->
| DeepSeek-Pro | 92,450 | 112 × A100, tensor | 92,512 | 2,359.5 | 274.9 | **8.58×** | 1 | 727 | <!-- figure: 92,512 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.iso_area_gpu_silicon_area_mm2" name="Pro iso-area GPU silicon, N6" --> <!-- figure: 274.9 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.iso_area_gpu_per_user_tokens_s" name="Pro iso-area GPU rate, N6" --> <!-- figure: 8.58 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_speed_ratio" name="Pro recommended-design iso-area ratio, N6" --> <!-- figure: 727 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.iso_area_gpu_max_resident_users" name="Pro iso-area GPU resident sessions, N6" -->

**Read the last two columns before the ratio.** Two of these three rows divide a
one-session machine's rate by a several-hundred-session machine's rate. That is a
latency claim and it is a real one — the ROM part reaches a rate the cluster
cannot reach at any batch — but it is not a serving claim, and the batch-regime
table below is where the serving answer lives. The report prints both counts on
the same row for exactly this reason.

**Headline before and after, by rule, at N6:**

| model | old rule's design | old mm² | old ratio | new design | new mm² | new ratio |
|---|---|---:|---:|---|---:|---:|
| Qwen3-8B | wafer ×1 romfill | 46,225 | 8.24× | array ×3 | **2,445** | **10.78×** | <!-- figure: 46,225 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].previous_rule_choice.silicon_area_mm2" name="Qwen area under the replaced rule, N6" --> <!-- figure: 8.24 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].previous_rule_choice.per_user_speed_ratio" name="Qwen ratio under the replaced rule, N6" -->
| DeepSeek-Flash | wafer ×1 romfill | 46,225 | 8.57× | *unchanged* | 46,225 | 8.57× |
| DeepSeek-Pro | wafer ×2 | 92,450 | 8.58× | *unchanged* | 92,450 | 8.58× |

**The Qwen ratio went up, and that has to be said plainly rather than banked.**
Moving the ROM side from a wafer to three reticles moved the GPU comparator from
56 A100s to 3, and a 3-GPU tensor group degrades faster than a 3-reticle ROM
pipeline does, so the quotient rises from 8.24× to 10.78×. The number that
should be quoted is not the ratio; it is that **the same rate now costs 2,445 mm²
instead of 46,225**, and that the machine it names is one session wide. At N5 the
same correction moves the Qwen ratio from 3.66× to 5.75× and moves
DeepSeek-Flash's the other way, from **4.62× down to 1.54×**, because at N5 the
walk lands Flash on a 11,410 mm² array whose iso-area B200 comparator is the
GPU's own best machine anywhere. A rule that only ever moved ratios upward would
be a rule worth distrusting; this one moves them both ways.

**The best design differs by batch, and the reports say where.** At N6:

| model | batch 1 | batch 2–8 | batch 16–256 |
|---|---|---|---|
| Qwen3-8B | array ×3, SRAM KV, 2,445 mm², **1 session** | array ×5, HBM KV, 4,075 mm², 298 sessions | array ×5, HBM KV, 4,075 mm², 298 sessions |
| DeepSeek-Flash | wafer ×1, HBM KV, 46,225 mm², 448 sessions | array ×19 from batch 4, 15,485 mm², 990 sessions | array ×19, 15,485 mm², 990 sessions |
| DeepSeek-Pro | wafer ×2, SRAM KV, 92,450 mm², **1 session** | wafer ×5, HBM KV, 231,125 mm², 314 sessions | array ×99, HBM KV, 80,685 mm², 723 sessions |

Every SRAM-KV winner is a batch-1 winner and holds one session, because
`DESIGN_BATCH = 1` sizes the SRAM-KV floorplan for a single stream. Every serving
regime is won by an HBM-KV machine, and on two of the three models the class
flips from wafer to array as the batch rises. **A single "best design" per model
would have had to suppress that**, which is why the reports publish the regime
table beside the pick.

**What is unchanged.** Tensor parallelism is still the right choice wherever a
machine can afford it, for the reason the previous version gave: a stitched mesh
carries a 57-way all-reduce at 1.1× its diameter and a GPU-class fabric cannot,
so a wafer can put its whole silicon on one token and an array cannot. The
tensor-parallelism cost table stands unchanged:

| model | collectives/token | on NVLink 3 | on-wafer (57 regions) | on-wafer ceiling |
|---|---:|---:|---:|---:|
| Qwen3-8B | 72 | 364.4 µs | **138.6 µs** | 7,215 tok/s |
| DeepSeek-V4-Flash | 86 | 1,266.5 µs | **165.6 µs** | 6,041 tok/s |
| DeepSeek-V4-Pro | 122 | 1,915.7 µs | **234.9 µs** | 4,258 tok/s |

And so does the inversion: more silicon does not buy per-user speed on either
side past the model's own optimum. The published claim that on-wafer tensor
parallelism reaches 82,000–116,000 tok/s per user remains **retracted**.

**What this section still cannot tell you.** The reticle-array class is sampled
only at the device counts each floorplan's own sizing sweep happened to choose:
`ROM_AREA_LADDER` is applied where `plan.kind == "wafer"` and nowhere else. So a
reticle array exists at an area only if some sweep landed there. For Qwen3-8B at
N6 the emitted batched-array counts are SRAM-KV/`spare=sram` at {3, 4},
SRAM-KV/`romfill` at {6, 7} and HBM-KV at {5, 8} — no romfill array at 4 or 5
dies, no SRAM-KV array at 5 or 8. The omission runs **against** the array class,
so the published curve is a lower bound on the ROM curve, not an upper one.

**That splits the three recommendations into two kinds and the split has to be
stated.** Qwen3-8B's winner *is* the smallest feasible machine, so the gap
cannot touch it: nothing exists below 2,445 mm² for a missing rung to hide in.
Both DeepSeek winners are wafers chosen over an array class sampled at a handful
of counts, and **that** is live: a rung the sweep never visited could in
principle beat the wafer on throughput density. Those two are the weakest results
in this section and should be re-derived once the array class is emitted on the
same explicit ladder the wafer class already gets. Fixing it is a separate
change and it must be separate, or nobody will be able to tell which correction
moved the headline.

### 2.4 KV in SRAM for the dense small model, HBM for the sparse large ones — unchanged, with one new and cheap action

The reasoning survives. Qwen at 8K needs bandwidth and little capacity, so SRAM
is chosen for bandwidth and capacity caps context and batch; DeepSeek at 200K
needs capacity and little bandwidth, so HBM is chosen for capacity. Every
DeepSeek design the study sizes above batch 1 is an HBM-KV design.

**The action this section carried is withdrawn.** It said *"pack the index array
separately from the payload — it is the cheapest 30% in this document"*, on the
strength of a 1.30×/1.64× granularity inflation. Measured, the index entry is
larger than either granule and the inflation is 1.00× on both DeepSeek models
and both stores (section 0.5). There is no 30% there to collect. Pack the index
separately if it is convenient; it buys nothing in this model.

**And the reasoning behind "HBM for the sparse large ones" is now under more
pressure than when it was written.** Flash's KV read per user token is 3.2× and
Pro's is 3.3× what this document previously claimed, so every DeepSeek design
above batch 4 binds on `kv_read` rather than on the ROM sweep, and sixteen
previously feasible DeepSeek design points no longer fit their KV. The choice of HBM over SRAM
is more clearly right than before — it is a capacity argument and the capacity
requirement roughly doubled on both models — but the *value* of the whole ROM
approach at serving batch is a third to a half of what was published.

### 2.5 Target the sparse long-context models — unchanged and unaffected

The weight-to-KV read ratio at batch 1 is **35.3:1** for Flash at 200K and
**18.0:1** for Pro at 1M, against 12.5:1 for dense Qwen at 8K. Sparse attention keeps
the KV read small while the weights stay large, so long context plus sparsity is
the ROM-favourable regime rather than the adverse one. A dense model's ROM
advantage is a short-context advantage — precisely the regime Taalas shipped
into.

**Both DeepSeek figures are retracted** (section 0.10): Flash was published as
113.2:1 and Pro as 58.9:1, and both rested on KV entry sizes read off the
implementation rather than measured while running it. The direction of the
conclusion survives — 35.3 and 18.0 still bracket Qwen's 12.5 from above — but
the margins are a third of what was claimed, and **Pro at 1M, the longest
context in the study, is now the *least* ROM-favourable of the three on this
measure.** That inverts the ordering this recommendation was resting on. What
survives is the mechanism, not the size: sparse attention keeps the KV read
sub-linear in context while the weights stay fixed, and that is still the
regime in which ROM helps.

Nothing else in this recommendation is touched by it. It is the only one of the
five original recommendations that comes through intact in direction, and the
only one whose *magnitude* has now been cut by a measurement.

**Section 0.12 strengthens it, and this is the one place that correction helps.**
With per-user latency charged honestly, the per-user ratio at equal silicon now
*rises* with batch on both sparse models — Flash from 9.2× at batch 1 to 36.5× at
256, Pro from 9.0× to 17.3× — and *falls* on the dense one, where the GPU wins
outright at batch 256. The mechanism is that a GPU cluster large enough to hold a
sparse long-context model has no cheap topology left: pipeline multiplies its
per-user latency by the slot count and tensor parallelism costs it 122
all-reduces that mostly cross InfiniBand. **Sparse plus long context is now the
ROM-favourable regime at every batch, not only at batch 1.**

### 2.6 The quantised variant is published, it is SECONDARY, and no token has ever been produced at that precision

**BF16 is the primary result and nothing above this heading depends on
anything below it.** The variant lives in
`results/roofline/quantised_variant/{n6_vs_a100,n5_vs_b200}/`, never in the
primary artifacts, and its report opens with what it is not.

**The rule it obeys is the one this repository already records for an FP8 KV
latent: a quantisation applies to BOTH sides.** A GPU serving 4.25-bit weights
reads 3.76× fewer weight bytes exactly as a mask-ROM part does. Halving one
side's weight traffic and not the other's is the asymmetry the released-packing
rule exists to forbid, and it is the asymmetry that once had half of every
feasible Qwen comparison won by an 8-bit ROM machine racing a 16-bit GPU.

- **Width.** 4.25 bits per parameter, identical on both sides. That is MXFP4 as
  the OCP Microscaling specification defines it — 4-bit E2M1 elements in blocks
  of 32 with one 8-bit E8M0 scale, (32×4 + 8)/32 = 4.25 — and it is within a
  rounding of INT4 group-128 with an FP16 scale and an INT4 zero point,
  (128×4 + 16 + 4)/128 = 4.16, which is how vLLM and TensorRT-LLM ship 4-bit
  weights today. It is **not** the 3-to-6-bit mixture Taalas describes: no mix
  ratio is published anywhere, so that width is `assumed` and must not be a
  headline.
- **Arithmetic, and the asymmetry that is a fact rather than a choice.** Both
  sides declare the `w4a8` datapath their stored width implies and each part
  then executes or emulates it by its own published format table.
  `configs/hardware/technology.json` gives `a100_sxm_80gb` native formats
  `[bf16, fp32]` and emulates `fp4`, `fp8` and `w4a8` to `bf16` — Ampere has no
  low-precision floating-point tensor core, so an A100 serving 4-bit weights
  gains **bytes and never arithmetic**. `b200_sxm` declares `w4a8` native. That
  is why **both** pairings are published: reporting only the A100 one would be
  selecting the study in which the GPU is architecturally forbidden from taking
  the credit the ROM side takes.
- **Scope: Qwen3-8B only.** The variant is defined only where the release ships
  *above* the width production GPU stacks already serve. Qwen3-8B ships at 16.00
  bits and qualifies. DeepSeek V4 Flash (4.70) and Pro (4.46) already ship mixed
  FP8 dense plus MXFP4 routed; re-quantising them would push the GPU below what
  any production stack serves, which is the same one-sided offer in the other
  direction.

What it says, with the primary on the same line so the pair is the only way to
read it:

| study | | design | mm² | user tok/s | tok/s per 1,000 mm² | iso-area GPU | GPU user tok/s | ratio |
|---|---|---|---:|---:|---:|---|---:|---:|
| N6/A100 | PRIMARY, BF16 | array ×3 | 2,445 | 2,791.2 | 1,141.6 | 3 × A100 | 258.9 | **10.78×** | <!-- figure: 2,791.2 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="Qwen primary per-user rate, N6" -->
| N6/A100 | variant, 4.25 b | array ×2 | 1,630 | 5,602.5 | 3,437.1 | 2 × A100 | 489.0 | 11.46× | <!-- figure: 1,630 src="results/roofline/quantised_variant/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.silicon_area_mm2" name="Qwen variant area, N6" --> <!-- figure: 5,602.5 src="results/roofline/quantised_variant/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="Qwen variant per-user rate, N6" --> <!-- figure: 11.46 src="results/roofline/quantised_variant/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_speed_ratio" name="Qwen variant iso-area ratio, N6" -->
| N5/B200 | PRIMARY, BF16 | array ×3 | 2,445 | 3,795.9 | 1,552.5 | 2 × B200 | 660.1 | **5.75×** | <!-- figure: 3,795.9 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="Qwen primary per-user rate, N5" --> <!-- figure: 5.75 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_speed_ratio" name="Qwen recommended-design iso-area ratio, N5" -->
| N5/B200 | variant, 4.25 b | array ×1 | 815 | 9,703.7 | 11,906.3 | 1 × B200 | 1,181.2 | 8.21× | <!-- figure: 815 src="results/roofline/quantised_variant/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.silicon_area_mm2" name="Qwen variant area, N5" --> <!-- figure: 9,703.7 src="results/roofline/quantised_variant/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="Qwen variant per-user rate, N5" --> <!-- figure: 8.21 src="results/roofline/quantised_variant/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_speed_ratio" name="Qwen variant iso-area ratio, N5" -->

**The ratio widens, and the reason is in the component times rather than in a
free lunch.** Take the same A100 cluster in both artifacts — 112 devices, tensor
— and the quantisation does exactly what it should: stored bytes fall by
16,381,470,720 → 4,351,328,160, precisely 4.25/16, and its weight-read term falls
78.0 µs → 20.7 µs, 3.76×. Its **compute term does not move at all** (0.788 µs
either way), because Ampere emulates `w4a8` on the BF16 tensor core. The ROM side
gains differently and in two places. Its weight term is a full-array sweep whose
duration is a technology constant independent of the bytes stored — 76.55 µs per
sweep at any width — so fewer bits do not shorten a sweep; what they buy is a
machine that needs **two dies instead of three**, hence 153.1 µs of sweep instead
of 229.7. And its compute term falls **312.6 µs → 65.5 µs**, because the ROM part
builds the `w4a8` datapath its stored width implies and an A100 cannot. So most
of the ROM side's gain here is **arithmetic density, not storage**, which is
worth stating plainly: it rests on the `w4a8` compute density, which is `derived`
from published A100 INT4/INT8 roofs scaled by logic density and has no silicon
behind it at N6. Note also that the N5 variant's 815 mm² machine is compared
against a **1,600 mm² B200 package**, roughly twice its silicon, because a
cluster is quantised in whole dies and a reticle design is not; the report states
that on the row.

**What is wrong with these numbers, before anyone quotes them.**

- **Nothing has been executed at this precision, anywhere in this program, on
  either backend.** `configs/hardware/abi3_capability/rom_qwen3.json` declares
  BF16 numeric contracts and no sub-byte weight decode and no `w4a8`
  contraction; the oracle-identical tokens this program rests on were produced
  at BF16. Every variant figure is graded `derived`.
- **No accuracy has been measured on either side.** The published band on
  4.25-bit weights runs from NVIDIA's vendor-run "1% or less" on one model to
  the OCP MX authors' own direct-cast MXFP4 measurement of a 24% relative
  Lambada drop on LLaMA-7B (0.736 → 0.557). Where a real deployment lands inside
  that band is the variant's real exposure, not its rate.
- **A modelling defect is left in deliberately and is recorded.** The balanced
  ROM+MAC floorplan rule sizes the MAC array at one weight byte per
  multiply-accumulate against a hard-coded fp8 compute density. At 4.25 bits a
  byte carries 1.88 weights, so the MAC array is under-provisioned by that factor
  and the array over-provisioned. The rule is exactly right at 16 bits on a bf16
  datapath, which is why the BF16 primary is untouched by it. It is **not** fixed
  here because fixing it would move **1,456 published ROM points in the *primary*
  studies** — 728 in each, every `batched` design with `spare_area_policy = rom`
  on a `w4a8` datapath, all of them DeepSeek, which already executes `w4a8` at
  its released packing of 4.70 and 4.46 bits — and this revision's rule is that
  the primary does not move except where the design selection moves it. It should be fixed on its own, where the size of
  the correction is the only thing being read.
- **Four genuine mask-ROM advantages have no term in this model** and the variant
  must not be argued on them: zero scale storage, zero dequantisation
  instructions and energy, free non-byte-aligned widths, free codebook
  quantisation. One genuine mask-ROM *dis*advantage is equally unmodelled: a
  mask ROM cannot be re-quantised after tape-out, so a bad quantisation is a
  scrapped mask set — a risk with no GPU counterpart.

**What would make it a measurement** is listed in the variant's own report:
quantise Qwen3-8B and run the existing HBM lane (the FP4 quantise/reconstruct
contracts already exist and are executed for DeepSeek); build the ROM lane, where
nothing exists; replace the impossible oracle-identity gate with cross-backend
identity at the *same* format plus a measured accuracy budget; and put silicon
behind the `w4a8` compute density at N6.

---

## 3. What would change this

Ranked by how much the answer moves. All are graded `assumed` in
`configs/hardware/technology.json` with their reasons, and the study's evidence
ledger lists all 43 of them.

- **`rom.cell_to_sram_cell_area_ratio` (0.2)** — still the most load-bearing
  number in the model. It sets the ROM capacity density and therefore the sweep
  time, and it is unmeasured at N6.
- **`rom.cim_cell_area_multiplier` (1.6)** — it no longer decides section 2.1,
  because it cancels in the sweep. It now decides how much *capacity* a
  compute-in-ROM die gives up, and therefore how many dies a model needs — 26
  against 18 for DeepSeek-Flash, 138 against 93 for DeepSeek-Pro. That is a
  smaller and more tractable question than the
  one it used to decide, which is itself a result: correcting the model demoted
  the parameter the previous document called second most load-bearing.
- **The per-layer latency block (`latency.*`, seven assumed inputs)** — 162.4 ns
  per dense layer, range 65.4–726.8 ns, costing a batch-1 ROM design 28–35% and a
  GPU 0.7–2.1%. `pipeline_fill_drain_s` is the largest term and carries the
  widest band; a measured per-layer floor on any real inference ASIC would
  replace the whole block.
- **`kv.index_layout` (`interleaved`)** — worth 1.30–1.67× on the binding term
  for both DeepSeek models, and it is a decision rather than a measurement.
- **`efficiencies.expert_router_imbalance` (1.0)** — replaces
  `expert_load_balance` (0.85), which was standing in for a batch-dependent
  function ranging over 1.0–3.0. What remains for it is the residual imbalance of
  a *trained* router against the uniform-random draw the busiest-region statistic
  assumes. It is inert at the neutral value because no trace exists to set it, and
  because a parameter must not take its value from the answer it is wanted to
  produce. Every per-region result is exactly linear in it.
- **`reference_parts.taalas_hc1.batch_size` (1)** — published nowhere. If HC1's
  16,960 tok/s is not a batch-1 figure, the anchor means something different and
  every ratio here moves.
- **The hop latencies (`links.*.hop_latency_s`) — TWO OF THE FOUR WERE RE-GRADED
  ON 2026-08-31 AND ARE NO LONGER ASSUMED.** This bullet previously said that
  *"NVIDIA publishes no NVLink or NVSwitch latency figure of any kind"* and that
  Cerebras publishes none for the on-wafer mesh. The first half is **withdrawn**:
  NCCL's shipping source carries NVIDIA's own per-traversal NVLink constant,
  `hwLatencies[NVLINK][Ring][LL] = 0.6 µs`. The second half is true as stated but
  was the wrong question — Cerebras publishes the *primitives* (one clock cycle
  per core-to-core hop, the per-die core grid, the clock), and composing them
  gives the reticle-field crossing this model charges.
  - `links.on_wafer.hop_latency_s`: **125 ns, `derived`, swept 75–250 ns**
    (was 100 ns assumed, swept 30–500 ns). It is the traversal of one 815 mm²
    reticle field — *not* a tile hop, which is 1 ns and 125× smaller — at the
    core pitch and clock of shipping wafer-scale silicon, and it is corroborated
    by two measured whole-wafer collectives and by Tesla's published 100 ns
    reticle-die crossing. **The number went up 25%**, against this study.
  - `links.nvlink3.hop_latency_s`: **2.5 µs, `derived`, swept 1.0–10.3 µs**
    (was 1.5 µs assumed, swept 1.0–5.5 µs), and `nvlink5`/`nvlink5_nvl72`
    **1.2 µs, `derived`, swept 0.7–5.5 µs**. Each is half a measured
    small-message in-domain all-reduce on the fabric it prices: 5.0 µs on
    8× A100 (MSCCL++, ASPLOS 2026) and 2.37 µs on GB200. The old 1.5 µs was
    *below every A100 measurement in existence*. **The A100 number went up 67%,
    which moves the headline up**, and is why the point is pinned to the best
    measured kernel rather than to stock NCCL's measured 20.6 µs.
  - Still `assumed`: `links.inter_wafer.hop_latency_s` at 5 µs (swept 1–10 µs) —
    now the largest unmeasured link on the ROM side — plus `ethernet` and
    `on_package`, neither of which any design in either study exercises.
  - `infiniband_hdr`/`ndr` remain `published`: 4.5 µs GPU-buffer to GPU-buffer,
    from De Sensi et al.'s SC24 measurements of 3.7–5.7 µs, which is the number
    a decode step pays rather than the 1.07 µs CPU-memory MPI ping-pong usually
    quoted.
  - **The band is now reported per side.** The joint band it used to be reported
    as, 24.5–42.5×, concealed which side the width came from; at 554,700 mm² on
    Pro the headline is **8.33×**, the wafer fabric alone spans **11.21×–5.41×**
    and the cluster fabric alone **6.92×–12.96×**, while the two moved together
    span only 9.31×–8.42× because they cancel. See §3's own table and
    `n6_vs_a100/REPORT.md` → "The headline is a band, and each side's share of it
    is reported apart".
- **The `energy` and `power` blocks — REBUILT, section 0.11, and one gate still
  fails.** Six terms were derived and adversarially verified; all six were
  refuted and all six are applied at their corrected values. The A100 now lands
  at 0.97× of its published TDP and Taalas HC1 at 0.28× of its published card
  power, so **the ROM side's watts and joules-per-token are lower bounds by
  2.9–3.6× and must be quoted as such.** `energy.rom_read_j_per_byte` moved from
  0.5 to 0.08 pJ/byte on the evidence, which made that gate worse rather than
  better and removed it as the competing explanation for the HC1 shortfall.
  `energy.hbm_j_per_byte` is now the only `measured` energy term in the file.
  What remains uncharged on both sides: L1/L2 traversal (6.30 pJ/bit further on
  an A100, same source), the long-path operand ladder beyond the tile-local
  floor, and ROM-array leakage.
- **The pipeline service-time rule — FIXED, section 0.12.** It was listed here
  as the most serious item and it was. A pipeline's service time was charged on
  the machine's aggregate resources while its hops were charged on the
  single-token path, making a balanced `S`-stage pipeline look `S` times faster
  per user than it is. Per-user latency and aggregate throughput are now separate
  quantities and every rate in this document has moved. It did not cancel in the
  ratio.

Two modelling choices replace it on this list, both stated in section 0.12 and
both favouring the deepest pipeline in a comparison:

- **Fill and drain are not charged.** Aggregate throughput is the steady-state
  rate with every slot occupied. A request short compared with the slot count
  pays up to one extra traversal that is not billed.
- **A deep pipeline's implied weight replication is not charged against
  capacity.** Past the layer count the surplus partitions hold replicas of a
  stage, each needing its own copy of that stage's weights, and the capacity
  check still credits the machine with holding the model once.
- **`efficiencies.stage_balance` (0.9) is applied per device rather than per
  partition**, so a one-wafer tensor-parallel design escapes it and a
  twelve-wafer one does not — worth 1.11× to the design that now wins at batch 1
  for Qwen and DeepSeek-Flash, and it runs the other way to the two items above.

Each is falsifiable. None of them was chosen by looking at the answer.

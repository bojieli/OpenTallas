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
   54.2× and became 35.4×** (band 24.5–42.5×) before item 1 took it to 8.6×. The
   comparison let the ROM side choose its parallelism and not the GPU, and
   charged both sides a serial pipeline deeper than the model has layers.
   Section 0.9.
3. **DeepSeek-Flash's weight-to-KV read ratio at 200K was 113.2:1 and is
   35.3:1**. Two KV entry sizes had been read off the implementation instead of
   measured while running it. Section 0.10.
4. **Every watt this program has ever reported is wrong by 7–9×**, against both
   published parts, and is not fixed here. No *rate* depends on it — that is
   shown structurally, not asserted. Section 0.11.

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
KV entry sizes (0.10), the power model (0.11, characterised but **not** fixed)
and the pipeline service-time rule (0.12, the largest of all of them). Each
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
The model now says 35.4×, with a band of 24.5–42.5× across the assumed hop
latencies.** Also retracted: *"two all-reduces per layer per token cost 131.35 µs
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
accounting — and **4.62× after the latency separation of section 0.12**, which
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
  57-region all-reduce cost 0.20 µs and now costs 1.54 µs; a 681-region one cost
  0.20 µs and now costs 5.72 µs. Per token at 61 layers that is 24 µs → 188 µs
  and 24 µs → 698 µs.
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

**The methodological point is the same one as section 0.9 and the same one as
the open power defect.** A number derived by reading an implementation is a
hypothesis. A number derived by running it is a measurement. Both of the
constants above were hypotheses that had been carried as facts, and neither
survived contact with the oracle. Where this program has both, the measurement
wins; where it has only the reading, the grade must say so.


---

### 0.11 The power model is 7-9x low against both published parts, and it is NOT fitted here

Characterised, not fixed. Every number below is computed from the model as it
stands.

| part | published | modelled | shortfall |
|---|---:|---:|---:|
| A100 SXM 80GB, 826 mm², Llama-3.1-8B batch 1 | 400 W (TDP) | **54.21 W** | 7.38× |
| Taalas HC1, 815 mm² at N6, at its published operating point | 200–250 W | **27.04 W** | 7.40–9.25× |

**Where the modelled watts come from.** On the A100 the step is 97.9% HBM
weight fetch (53.09 W), 1.8% KV (0.95 W) and 0.3% MACs (0.17 W). On HC1 it is
79% ROM array read. The model counts three things — bytes out of a memory,
bytes out of a KV store, and multiply-accumulates — and nothing else.

**It is not an activity-factor error, and the check that shows this is worth
stating.** Drive the A100 at its published peak HBM bandwidth *and* its
published BF16 roof simultaneously and the model produces **85.3 W against a
400 W TDP — still 4.7× low.** An activity factor would close at peak. This one
does not, so the missing power is power the model does not enumerate at all:
static leakage, clock distribution, register-file and operand delivery (a
Horowitz-class MAC energy is the ALU, not the cost of getting operands to it),
L2 and staging SRAM, control, the NoC, and HBM PHY and controller floor.

**The two anchors' shortfalls are nearly equal and that is probably a
coincidence, which matters because it makes the obvious fix wrong.** The A100's
gap survives at simultaneous peak, so it is structural. HC1's gap has a
competing and entirely sufficient explanation inside a single existing input:
`energy.rom_read_j_per_byte` is 0.5 pJ/byte, graded `assumed`, sourced as *"no
fabricated leading-node mask-ROM macro energy published"* and noted as *"carried
over from `src/opentallas/schema.py` defaults"*. Reaching 200–250 W would need
4.6–5.8 pJ/byte from that term alone — which is not obviously wrong for a
compute-in-ROM array in which the read **is** the multiply. **A single 8×
multiplier would close both gates and would be a fit, not a derivation.** The
same ruling that applied to the per-layer latency block applies here.

**The consequence, and it is the one the framing asked about.** `thermal_scale`
is exactly 1.0 at **all 11,747 feasible points across both studies**. Since
`step_time = raw_step_time × thermal_scale` and `thermal_scale` is the only path
by which power reaches any other quantity, **the energy model currently has zero
influence on any rate this program reports.** That is a structural statement,
not an empirical one, and it cuts both ways: every throughput number here
survives the power defect untouched, and every watt and every joule-per-token
here is unpublishable.

The cooling limit itself is sound: 0.50 W/mm², derived from the A100's published
400 W over 826 mm² (0.484) and cross-checked against HC1 at 0.31 and a 15–23 kW
wafer at 0.32–0.50. **It is the power that is low, not the limit that is
loose** — which is precisely why dark silicon never appears. Modelled power
density peaks at 0.181 W/mm² anywhere in either study; a twelve-wafer Pro
machine at batch 256 sits at 0.0112 W/mm², 45× under its own limit.

Under a uniform correction — a placeholder for the real, non-uniform term, and
stated as a bound rather than a result:

| uniform multiplier | feasible points over 0.50 W/mm² | worst point |
|---:|---:|---:|
| 1.0 (today) | 0 of 11,747 | 0.181 W/mm² |
| 4.7 (the A100 peak shortfall) | 339 (2.9%) | 0.851 W/mm² |
| 7.4 | 581 (4.9%) | 1.340 W/mm² |
| 9.3 | 987 (8.4%) | 1.684 W/mm² |

So the shape of the answer is already visible and it is not the intuitive one:
**thermal throttling would bite the small, dense, high-batch designs first —
the worst point at every multiplier is an eight-die Qwen array at batch 256 —
and would still not bind on the large wafers**, which are power-sparse because
a ROM sweep is a fixed cost spread over far more silicon. If that survives a
correct power term it is an argument *for* wafer-scale that this program has
not yet made.

**What is needed, and it is not small.** Two power gates in the shape of the
two that exist — the A100 at its published TDP under a saturating load, and HC1
at its published operating point — with the missing terms derived from graded
primitives (leakage at N6/N7, clock distribution as a fraction of dynamic,
operand-delivery energy per MAC) and reported at both ends of every assumed
range. That is comparable in size to the interconnect rebuild in section 0.9,
and it is handed back rather than half-done.

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
| Qwen3-8B | 46,225 | 53,701 → 7,936 | wafer-pipeline → wafer-tensor | 56 | 3,852 → 891 | pipeline → tensor | 13.94× | **8.91×** | 0.64× |
| Qwen3-8B | 92,450 | 50,885 → 7,023 | wafer-pipeline → wafer-hybrid | 112 | 6,022 → 967 | pipeline → tensor | 8.45× | **7.26×** | 0.86× |
| Qwen3-8B | 138,675 | 50,885 → 6,339 | wafer-pipeline → wafer-hybrid | 168 | 7,414 → 995 | pipeline → tensor | 6.86× | **6.37×** | 0.93× |
| Qwen3-8B | 184,900 | 50,885 → 5,777 | wafer-pipeline → wafer-hybrid | 224 | 8,383 → 1,010 | pipeline → tensor | 6.07× | **5.72×** | 0.94× |
| Qwen3-8B | 277,350 | 50,885 → 4,906 | wafer-pipeline → wafer-hybrid | 336 | 9,644 → 616 | pipeline → tensor | 5.28× | **7.96×** | 1.51× |
| Qwen3-8B | 369,800 | 50,885 → 4,263 | wafer-pipeline → wafer-hybrid | 448 | 10,428 → 619 | pipeline → tensor | 4.88× | **6.89×** | 1.41× |
| Qwen3-8B | 554,700 | 59,341 → 3,811 | wafer-pipeline → wafer-hybrid | 672 | 11,351 → 622 | pipeline → tensor | 5.23× | **6.13×** | 1.17× |
| Flash @200K | 46,225 | 18,841 → 5,515 | wafer-pipeline → wafer-tensor | 56 | 1,572 → 600 | pipeline → tensor | 11.98× | **9.19×** | 0.77× |
| Flash @200K | 92,450 | 28,141 → 5,249 | wafer-pipeline → wafer-hybrid | 112 | 1,818 → 631 | pipeline → tensor | 15.48× | **8.33×** | 0.54× |
| Flash @200K | 138,675 | 35,354 → 5,116 | wafer-pipeline → wafer-hybrid | 168 | 1,923 → 642 | pipeline → tensor | 18.39× | **7.97×** | 0.43× |
| Flash @200K | 184,900 | 40,534 → 4,988 | wafer-pipeline → wafer-hybrid | 224 | 1,981 → 648 | pipeline → tensor | 20.46× | **7.70×** | 0.38× |
| Flash @200K | 277,350 | 47,475 → 4,750 | wafer-pipeline → wafer-hybrid | 336 | 2,043 → 434 | pipeline → tensor | 23.24× | **10.94×** | 0.47× |
| Flash @200K | 369,800 | 51,913 → 4,533 | wafer-pipeline → wafer-hybrid | 448 | 2,076 → 436 | pipeline → tensor | 25.00× | **10.41×** | 0.42× |
| Flash @200K | 554,700 | 57,260 → 4,152 | wafer-pipeline → wafer-hybrid | 672 | 2,111 → 437 | pipeline → tensor | 27.13× | **9.50×** | 0.35× |
| Pro @1M | 92,450 | 9,107 → 2,654 | wafer-pipeline → wafer-hybrid | 112 | 544 → 295 | pipeline → tensor | 16.73× | **9.01×** | 0.54× |
| Pro @1M | 138,675 | 9,633 → 2,227 | wafer-pipeline → wafer-hybrid | 168 | 579 → 304 | pipeline → tensor | 16.64× | **7.33×** | 0.44× |
| Pro @1M | 184,900 | 11,960 → 2,211 | wafer-pipeline → wafer-hybrid | 224 | 598 → 309 | pipeline → tensor | 20.00× | **7.15×** | 0.36× |
| Pro @1M | 277,350 | 15,728 → 2,173 | wafer-pipeline → wafer-hybrid | 336 | 619 → 234 | pipeline → tensor | 25.41× | **9.30×** | 0.37× |
| Pro @1M | 369,800 | 18,568 → 2,127 | wafer-pipeline → wafer-hybrid | 448 | 630 → 235 | pipeline → tensor | 29.47× | **9.04×** | 0.31× |
| Pro @1M | 554,700 | 22,686 → 2,042 | wafer-pipeline → wafer-hybrid | 672 | 642 → 237 | pipeline → tensor | 35.35× | **8.63×** | 0.24× |

The N5-versus-B200 study moves the same way: Pro at 554,700 mm² goes from
**13.06× to 4.62×**, and every rung of that ladder falls (0.35×–1.03×).

**Three mechanisms put the change where it is, and none of them cancels.**

1. *The two families reach iso-area at very different slot counts.* At
   554,700 mm² the ROM side is twelve wafers spanning 681 reticle fields; the
   GPU side is 672 devices. Charged as pipelines those raw corrections are close
   — 15.6× against 18.3× on Qwen. But the correction is not applied to a fixed
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
   ROM's the ratio **rises** — Qwen at 277,350 mm², 5.28× to 7.96×. Where the
   ROM's exceeds the GPU's it falls — Pro at 554,700 mm², 35.35× to 8.63×.

**The batch curves change shape, and for the sparse models they change sign.**
Per-user tok/s at equal silicon, best design on each side at each batch:

| batch | Qwen3-8B @8K | DeepSeek-Flash @200K | DeepSeek-Pro @1M |
|---:|---:|---:|---:|
| 1 | 8.91× | 9.19× | 9.01× |
| 8 | 7.04× | 12.61× | 15.73× |
| 32 | 4.13× | 21.60× | 19.37× |
| 64 | 2.60× | 26.69× | 18.89× |
| 256 | **0.92×** | **36.52×** | **17.33×** |

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

## 1. The result

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

### 2.3 Array or wafer, and pipeline or tensor: both answers change once per-user latency is charged honestly

**The previous version of this section is superseded, and so is the version
before it.** It said the array case was weaker than reported and that the model
"chooses pipeline over tensor parallelism on the wafer at every operating point".
The second half is now false and the first half is true for a different reason.

What the study chooses at batch 1, on per-user rate, after section 0.12:

| model | best design | mm² | per-user tok/s | binds on | best array design | array tok/s | wafer over array |
|---|---|---:|---:|---|---|---:|---:|
| Qwen3-8B @8K | `wafer-tensor` ×1 romfill | 46,225 | **7,936** | link_latency | `array-pipeline` ×5 romfill | 6,747 | 1.18× |
| DeepSeek-Flash @200K | `wafer-tensor` ×1 romfill | 46,225 | **5,515** | link_latency | `array-hybrid` ×18 | 1,856 | 2.97× |
| DeepSeek-Pro @1M | `wafer-hybrid` ×2 | 92,450 | **2,654** | link_latency | `array-hybrid` ×96 | 680 | 3.90× |

Three things changed and they are worth separating.

**1. Tensor parallelism is now the right choice, and it was the correction that
made it so.** The previous section dismissed on-wafer tensor parallelism because
its collective ceiling — 9,019 tok/s on Qwen, 7,551 on Flash, 5,322 on Pro — sat
an order of magnitude below the ~50,000 tok/s a wafer-scale pipeline appeared to
deliver. That 50,000 was the defect: it was the whole wafer's ROM bandwidth
credited to a single token that only ever touched one reticle field at a time.
With the pipeline charged honestly, **the tensor ceiling is the best rate
available**, and every winning design above sits within 12–50% of it and binds
on `link_latency`. Wafer-scale tensor parallelism is an argument for wafer-scale
again — not because the collective got cheaper, but because the alternative
turned out to be far more expensive than it looked.

**2. The wafer still wins on per-user rate, by more than before, and for a
different reason.** It wins 24 of 24 batch-1 operating points. The mechanism is
no longer "a hop latency an array cannot match" in a pipeline; it is that a
stitched mesh can carry a 57-to-84-way all-reduce at 1.1× its diameter while a
GPU-class or package-class fabric cannot, so **a wafer can afford a tensor group
wide enough to put the whole machine on one token and an array cannot.** On
tokens per second per square millimetre the array still wins 20 of 24 points; a
wafer is not faster per unit silicon, it is faster because a wafer is one
collective domain.

**3. More silicon no longer buys per-user speed on either side.** This is the
inversion. The ROM per-user rate falls monotonically with area at batch 1 —
7,936 → 3,811 tok/s for Qwen from one wafer to twelve — because past one wafer
the only ways to spend silicon are more slots to traverse or a wider collective
to wait on. **The right latency machine is the smallest one that holds the
model**: one wafer for Qwen and Flash, two for Pro. Twelve-wafer machines remain
the right *throughput* machines and the study still reports them as such, at
133,002 and 273,946 aggregate tokens/s — but at 195 and 402 tokens/s per user.
The two objectives now select different machines and the study no longer
pretends otherwise.

**The tensor-parallelism cost table stands.** Two all-reduces per layer per
token, like for like — the same model's collective on one wafer against the same
model's on NVLink plus InfiniBand:

| model | collectives/token | on NVLink 3 | on-wafer (57 regions) | on-wafer ceiling |
|---|---:|---:|---:|---:|
| Qwen3-8B | 72 | 220.4 µs | **110.9 µs** | 9,019 tok/s |
| DeepSeek-V4-Flash | 86 | 1,094.5 µs | **132.4 µs** | 7,551 tok/s |
| DeepSeek-V4-Pro | 122 | 1,671.7 µs | **187.9 µs** | 5,322 tok/s |

The published claim that on-wafer tensor parallelism reaches 82,000–116,000
tok/s per user remains **retracted**: it came from charging a stitched 2-D mesh
one flat hop however far the collective reached. What has changed since that
retraction is only that 5,000–9,000 tok/s is now the number to beat rather than
a number to dismiss.

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
- **Every hop latency in the model (`links.*.hop_latency_s`)** — new to this
  list and immediately near the top of it. NVIDIA publishes **no** NVLink or
  NVSwitch latency figure of any kind; six first-party pages were checked and
  every one gives bandwidth only. Cerebras publishes none for the on-wafer mesh
  and none at all for SwarmX. The stated values are 1.5 µs for NVLink (swept
  1.0–5.5 µs, which brackets the measured 1.4 µs speed-of-light all-reduce floor
  on GB200 at one end and stock NCCL's 11 µs ring at the other), 100 ns per
  on-wafer reticle hop (swept 30–500 ns), and 5 µs wafer-to-wafer (swept
  1–10 µs). The InfiniBand figure is the exception and is measured rather than
  assumed: 4.5 µs GPU-buffer to GPU-buffer, from De Sensi et al.'s SC24
  measurements of 3.7–5.7 µs across five production supercomputers, which is the
  number that matters for a decode step and not the 1.07 µs CPU-memory MPI
  ping-pong usually quoted. **The headline iso-area ratio at 554,700 mm² spans
  24.5–42.5× across this band**, and the study reports it at both ends.
- **The whole `energy` block, and therefore every watt in this program** —
  section 0.11. Both published anchors are reproduced 7–9× low, the gap survives
  at simultaneous peak on the A100, and `thermal_scale` is 1.0 at every one of
  11,747 feasible points, so no rate here depends on it and no watt here is
  publishable. `energy.rom_read_j_per_byte` (0.5 pJ/byte) is the single most
  exposed input: it is `assumed`, sourced as "no fabricated leading-node
  mask-ROM macro energy published", and it alone could account for the whole HC1
  shortfall.
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

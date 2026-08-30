# Iso-area comparison, and the shipping part that anchors it

This document exists because the project derived an impossible result from a
placeholder it never checked, and then compared it unfairly. Both failures have
the same root: a configured number was treated as ground truth.

It has since been amended four more times, for the same reason each time.
Sections 2b through 2f are the amendments, and the largest of them is a
retraction of this document's own headline, twice over: **the iso-area advantage
for DeepSeek-V4-Pro at 554,700 mm² was published as 54.2x, was corrected to
35.4x when the interconnect was rebuilt (section 2c), and is 8.6x now that
per-user latency has been separated from aggregate throughput (section 2d).**

## 1. The anchor

**Taalas HC1** is a shipping mask-ROM inference accelerator. AMD announced an
acquisition of the company in August 2026.

| | published |
|---|---|
| process | TSMC 6 nm |
| die area | **815 mm²** |
| transistors | **53 billion** |
| weights | mask ROM on-die |
| KV cache | on-die SRAM |
| throughput | **16,960 tokens/s per user**, Llama 3.1 8B |
| qualification | **1k input / 1k output** (~2k context). **Batch size is stated nowhere** |
| weight format | custom **3-bit base mixed with 6-bit**, with acknowledged quality loss |
| KV concurrency | ~365–1,130 MB of SRAM → **1.4–8 concurrent users** at 2k context |
| validation | all figures self-run by Taalas; no MLPerf or third-party measurement |

Sources: [ServeTheHome](https://www.servethehome.com/amd-to-acquire-taalas-for-model-specific-ai-inference-chips/),
[The Register](https://www.theregister.com/systems/2026/08/06/amd-acquires-ai-chip-startup-taalas-to-boost-inference-performance-by-etching-models-into-silicon/5284344),
[HC1 analysis](https://medium.com/@bmilew/a-look-at-taalas-hc1-chip-reaching-new-heights-in-llm-inference-56cd079f59a3).

**Any model of a ROM accelerator must reproduce this.** A methodology that
predicts 2,000 tok/s or 200,000 tok/s for an 8B model on 815 mm² at N6 is wrong,
however internally consistent it is, because a real part says otherwise. The
anchor is a test the model must pass, not a datapoint to be averaged in.

## 2. The iso-area comparison

An NVIDIA A100 80GB is 826 mm² at TSMC N7 with 54.2 billion transistors —
essentially the same die as HC1, one node apart. That is the comparison:

| | Taalas HC1 | NVIDIA A100 80GB |
|---|---:|---:|
| node / die | N6 / 815 mm² | N7 / 826 mm² |
| transistors | 53 B | 54.2 B |
| weights live in | mask ROM on-die | HBM at 2.04 TB/s |
| 8B model, batch 1 | **17,000 tok/s** | 254 tok/s (FP8) · 127 (BF16) |
| ratio | | **67× · 134×** |

The anchor reproduces exactly. Llama 3.1 8B is 8.0300 B parameters from its
published config, so decode costs `2N` = 16.060 GFLOP/token; times 16,960 tok/s
is **272.4 TFLOP/s** on 815 mm² at N6.

**But calling that "GPU-class compute" was wrong, and the error flatters the
design.** HC1's 272 TFLOP/s is *4-bit* work. An A100 at matched INT4 does 1,248
TOPS dense, so HC1 has roughly **0.22× an A100's 4-bit arithmetic throughput** —
and still wins 67× at batch 1. **The mechanism is the absence of weight fetch,
not a compute surplus.** Stating it as a compute surplus overstates what the
architecture does and misplaces the reason it works.

**The per-user and aggregate ratios are very different, and the difference is
the open question.** Each ROM cell performs its own multiply — Bajic: *"we can
store four bits away and do the multiply related to it – everything – with a
single transistor."* If that means a second concurrent stream needs a second
pass through the fabric, then a compute-in-ROM part **cannot amortise weight
access across a batch the way a GPU does**, aggregate per-die throughput equals
per-user throughput, and the iso-area comparison splits:

| | HC1 | A100 826 mm² | ratio |
|---|---:|---:|---:|
| per-user latency, batch 1 | 16,960 tok/s | 254 tok/s | **66.8×** |
| aggregate per die | ~16,960 tok/s | ~7,771 tok/s (40% MFU) | **~2.2×** |

That is derived, not published, and **it is the most important thing to resolve
before any wafer-scale or high-batch claim rests on this anchor.** It also forks
the architecture this project should design:

- **Compute-in-ROM**, as Taalas built it: one transistor stores and multiplies.
  Extraordinary density (~0.0023–0.0040 µm²/bit, genuinely DRAM-class) and
  extraordinary power (only ~136,000 of 8.03 B cells fire per cycle, 0.0017%
  activation, which is what allows 200–250 W). But no batch amortisation.
- **ROM as storage with a separate MAC array**: weights read out of ROM into a
  compute fabric. Batch amortises the read exactly as on a GPU, so aggregate
  throughput rises with batch — the behaviour the sparse-MoE argument depends on
  — at the cost of the density and the activation-energy advantage.

These are different machines with different scaling laws, and the project has
not yet chosen between them.

## 2b. The comparison was not symmetric, and the asymmetry inflated our own number

**RETRACTED: the published iso-area ratio of 54.2x for DeepSeek-V4-Pro at 1M
context, batch 1, at 554,700 mm2. The model said 35.4x when this section was
written and says 8.6x now; section 2d supersedes every per-user rate below.**
Everything below
is emitted by `src/opentallas/roofline.py` and read out of
`results/roofline/n6_vs_a100/analytical.json`.

The ROM side was evaluated under both pipeline and tensor parallelism and the
better of the two was reported. The GPU side was only ever evaluated under
pipeline. At 672 devices that charged the GPU **671 serial hops per token at
batch 1** -- 1,017 us, 41% of its whole step -- while the ROM wafer at the same
area ran tensor-parallel for 12.2 us. The GPU therefore got *slower* as it was
given more silicon, 532 tok/s at 112 devices falling to 407 at 672, and that
decline was most of the headline. **No deployment of a 1.6 T model on 672 GPUs
runs 672-way pipeline at batch 1.**

Three corrections, each applied to **both** sides:

1. **Both sides choose their own parallelism.** Pipeline, tensor and hybrid --
   tensor-parallel inside a high-bandwidth domain, pipeline-parallel across it
   -- are evaluated at every cluster size on both sides and the best is
   reported. On its own this changes almost nothing, and that is a result in
   itself: see section 2d.
2. **Both sides are charged two link classes.** A cluster is an NVLink island
   of 8 GPUs (published, NVIDIA DGX A100 system architecture: twelve NVLinks
   from each GPU to all six NVSwitches; HGX B200 the same at 8, GB200 NVL72 at
   72) plus a scale-out fabric an order of magnitude slower. A wafer machine is
   the same shape: an on-wafer mesh inside one wafer, and a link between
   wafers. A 93-partition pipeline crosses 81 island-internal boundaries and 11
   network boundaries, not 92 of either.
3. **A token cannot cross more stage boundaries than the model has layers.**
   This is the one that moved the number. 672 partitions do not make 671
   pipeline stages of a 61-layer model; they make at most 61, and the silicon
   past that adds bandwidth and no serial event. The GPU's link cost stops
   growing with area at 117.5 us and its rate rises monotonically instead of
   falling.

DeepSeek-V4-Pro, 1M context, batch 1, per-user tokens/s at equal silicon:

| ROM mm2 | GPU n | ROM before | GPU before | ratio published | ROM after | GPU after | **ratio now** | band |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 75,795 | 93 | 4,116 | 521 | 7.9x | 4,169 | 526 | **7.9x** | — |
| 79,870 | 97 | 4,021 | 525 | 7.7x | 4,562 | 530 | **8.6x** | 4.8-9.9x |
| 92,450 | 112 | 9,082 | 532 | 17.1x | 9,107 | 544 | **16.7x** | 14.9-17.8x |
| 138,675 | 168 | 9,009 | 538 | 16.7x | 9,633 | 579 | **16.6x** | 14.7-17.7x |
| 277,350 | 336 | 11,570 | 499 | 23.2x | 15,728 | 619 | **25.4x** | 19.9-28.6x |
| 369,800 | 448 | 18,213 | 466 | 39.1x | 18,568 | 630 | **29.5x** | 21.9-34.0x |
| 554,700 | 672 | 22,043 | **407** | **54.2x** | 22,686 | **642** | **35.4x** | 24.5-42.5x |

A dash in the band column is an area at which the best design under one of the two
bounds is a different machine, so the two are not the same comparison and no
interval is quoted.

The GPU's link latency is now 117.5 us at every size from 61 devices upward --
61 stages, 60 boundaries, of which 53 stay inside an NVLink island and 7 cross
the network -- against 180 us at 92 devices and 1,331 us at 672 under the old
accounting. **The GPU no longer degrades with added silicon.** It rises
monotonically from 449 tok/s at 48 devices through 526 at 93 to 642 at 672, and
what remains is a slow saturation rather than a decline:
past about eight devices the routed experts of a sparse MoE stop spreading
further, so extra HBM bandwidth stops buying weight-fetch time.

The ratio band is the study re-run with *every* assumed hop latency at each end
of its stated range, on both sides at once. NVIDIA publishes no NVLink latency
figure of any kind and Cerebras publishes none for the on-wafer mesh or for
SwarmX, so the headline is an interval and not a number.

## 2c. The mirror-image problem on the ROM side, and it was worse

The instruction that produced section 2b was to look for the same fault on our
own side. There were two, and both flattered us.

**The on-wafer collective was charged a flat two hops however far it reached.**
A stitched wafer is a 2-D mesh with no switch -- Cerebras states this outright
-- so an all-reduce cannot finish before the far corner has answered. Cerebras
measured their own at *"a cycle count only about 10% greater than the diameter
of the system"* (Rocki et al., SC20), and the diameter of an N-region mesh is
`2(sqrt(N)-1)`. The model now charges `1.1 x diameter` traversals:

| span | old traversals | new traversals | all-reduce at 100 ns/hop | per token, 61 layers |
|---:|---:|---:|---:|---:|
| 57 regions (1 wafer) | 1 | 15.4 | 0.20 -> 1.54 us | 24 -> 188 us |
| 681 regions (12 wafers) | 1 | 57.2 | 0.20 -> 5.72 us | 24 -> 698 us |

**And a twelve-wafer machine was charged the on-wafer stitching for its
wafer-to-wafer links.** Twelve wafers are twelve manufactured objects; the
signal leaves the die. The only shipping multi-wafer machine is a Cerebras
cluster, whose off-wafer fabric is twelve 100 GbE ports per system --
**150 GB/s against 26.75 PB/s on-wafer, a factor of 180,000** -- with no
published latency at all. That link is now a named, assumed input at 5 us,
swept 1-10 us, and it is the ROM side's most load-bearing assumption after the
bitcell area ratio.

The consequence is that **on-wafer tensor parallelism no longer reaches
Taalas-class rates**, and the previously published claim that it does -- "hard
ceilings of 116,278 and 81,966 tok/s per user" -- is retracted. It reaches
5,000-9,000 tok/s. When this section was written that made the model choose
pipeline over tensor parallelism on the wafer at every operating point;
**section 2d reverses that**, because the pipeline it was being compared against
was itself overstated by its slot count. Wafer-scale tensor parallelism now wins
at batch 1 on both families, at those same 5,000-9,000 tok/s.

The ordering survives but the margin is smaller than the framing implied. Like
for like -- the same model's collective on one wafer against the same model's on
NVLink -- the wafer is 2.0x cheaper on Qwen, 8.3x on Flash and 8.9x on Pro. The
Qwen figure is the instructive one: a four-GPU Qwen cluster fits inside a single
eight-GPU NVLink domain, where a collective is two switch traversals and nothing
else, and a 57-reticle mesh's 15.4 traversals is barely better than that. **The
wafer's collective advantage is a property of the cluster having outgrown its
NVLink island, not a property of the wafer.**

**A third asymmetry, smaller and also ours:** a ROM array in the N6-vs-A100
study was charged NVLink-5 bandwidth, 900 GB/s, against an A100 whose published
NVLink 3 rate is 300 GB/s. Each study now charges one fabric to both sides.

## 2d. The pipeline service-time defect is FIXED, and this document's headline falls again

**RETRACTED: 35.4x for DeepSeek-V4-Pro at 1M context, batch 1, at 554,700 mm2.
The model now says 8.6x.** The previous version of this section named the defect
and left it open. It is closed here, and closing it was worth more than either
of the two corrections that preceded it.

**What was wrong.** The model computed the service time on the machine's
*aggregate* memory bandwidth and compute roof whatever the parallelism, and then
added the hops a single token crosses. That is a throughput view of the silicon
wearing a latency view of the fabric. It is right for tensor parallelism, where
every partition is on the same token at the same instant. It is not right for
pipeline parallelism: a token at stage *i* is served by stage *i*'s silicon
alone and has to visit every stage, so a balanced `S`-stage pipeline's per-user
latency is `S` times what the model charged.

**The fix.** `token_slots = partitions / tensor_group` counts the independent
groups a machine is cut into; a token is served by one of them at a time. One
user's latency is

```
t_user = token_slots x t_service(microbatch) / stage_balance + t_link
```

and the machine's aggregate rate is that latency with a user in every slot,
`fill_users / t_user`, where `fill_users = max(batch, token_slots)` capped by
the users whose KV the machine can hold. **`aggregate = batch x per-user` is
gone**, and what a machine delivers at the requested concurrency is reported
separately as `delivered_tokens_s`.

The physics the fix encodes is worth stating plainly, because it is the whole
argument: under pipeline parallelism each of `N` stages holds `1/N` of the
weights and reads them with `1/N` of the bandwidth. **The two cancel exactly.
Adding devices under pipeline parallelism buys aggregate throughput and buys one
user nothing.** Tensor parallelism is different in kind rather than in degree --
it is the only arrangement that puts the whole machine on one token -- and what
it pays for that is two all-reduces per layer.

**Both validation gates are unchanged to the digit**: A100 weight-bound at
253.91 tok/s (ratio 1.0000) and Taalas HC1 at 0.7213x of 16,960. Both are
single-device machines, `token_slots` is 1 for both, and a correct separation
cannot reach them. That they did not move is the check that this touched only
what it claimed to.

**It did not cancel in the ratio.** The tempting argument -- that both families
are pipelines of similar depth at iso-area, so the `N` cancels -- is false, and
the seven-rung area ladder shows why. Per-user tok/s at batch 1,
`n6_vs_a100`, from `The latency separation, before and after` in the study
report:

| model | mm2 | ROM before | ROM after | /x | GPU n | GPU before | GPU after | /x | ratio before | **ratio after** | change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 46,225 | 53,701 | 7,936 | 6.8x | 56 | 3,852 | 891 | 4.3x | 13.94x | **8.91x** | 0.64x |
| Qwen3-8B | 92,450 | 50,885 | 7,023 | 7.2x | 112 | 6,022 | 967 | 6.2x | 8.45x | **7.26x** | 0.86x |
| Qwen3-8B | 138,675 | 50,885 | 6,339 | 8.0x | 168 | 7,414 | 995 | 7.4x | 6.86x | **6.37x** | 0.93x |
| Qwen3-8B | 184,900 | 50,885 | 5,777 | 8.8x | 224 | 8,383 | 1,010 | 8.3x | 6.07x | **5.72x** | 0.94x |
| Qwen3-8B | 277,350 | 50,885 | 4,906 | 10.4x | 336 | 9,644 | 616 | 15.7x | 5.28x | **7.96x** | 1.51x |
| Qwen3-8B | 369,800 | 50,885 | 4,263 | 11.9x | 448 | 10,428 | 619 | 16.9x | 4.88x | **6.89x** | 1.41x |
| Qwen3-8B | 554,700 | 59,341 | 3,811 | 15.6x | 672 | 11,351 | 622 | 18.3x | 5.23x | **6.13x** | 1.17x |
| Flash @200K | 46,225 | 18,841 | 5,515 | 3.4x | 56 | 1,572 | 600 | 2.6x | 11.98x | **9.19x** | 0.77x |
| Flash @200K | 92,450 | 28,141 | 5,249 | 5.4x | 112 | 1,818 | 631 | 2.9x | 15.48x | **8.33x** | 0.54x |
| Flash @200K | 138,675 | 35,354 | 5,116 | 6.9x | 168 | 1,923 | 642 | 3.0x | 18.39x | **7.97x** | 0.43x |
| Flash @200K | 184,900 | 40,534 | 4,988 | 8.1x | 224 | 1,981 | 648 | 3.1x | 20.46x | **7.70x** | 0.38x |
| Flash @200K | 277,350 | 47,475 | 4,750 | 10.0x | 336 | 2,043 | 434 | 4.7x | 23.24x | **10.94x** | 0.47x |
| Flash @200K | 369,800 | 51,913 | 4,533 | 11.5x | 448 | 2,076 | 436 | 4.8x | 25.00x | **10.41x** | 0.42x |
| Flash @200K | 554,700 | 57,260 | 4,152 | 13.8x | 672 | 2,111 | 437 | 4.8x | 27.13x | **9.50x** | 0.35x |
| Pro @1M | 92,450 | 9,107 | 2,654 | 3.4x | 112 | 544 | 295 | 1.8x | 16.73x | **9.01x** | 0.54x |
| Pro @1M | 138,675 | 9,633 | 2,227 | 4.3x | 168 | 579 | 304 | 1.9x | 16.64x | **7.33x** | 0.44x |
| Pro @1M | 184,900 | 11,960 | 2,211 | 5.4x | 224 | 598 | 309 | 1.9x | 20.00x | **7.15x** | 0.36x |
| Pro @1M | 277,350 | 15,728 | 2,173 | 7.2x | 336 | 619 | 234 | 2.6x | 25.41x | **9.30x** | 0.37x |
| Pro @1M | 369,800 | 18,568 | 2,127 | 8.7x | 448 | 630 | 235 | 2.7x | 29.47x | **9.04x** | 0.31x |
| Pro @1M | 554,700 | 22,686 | 2,042 | 11.1x | 672 | 642 | 237 | 2.7x | 35.35x | **8.63x** | 0.24x |

`before` is not a memory of an earlier run. Every point in the study now carries
`per_user_tokens_s_throughput_view`, the number the old rule produced, and each
side is ranked by it, so the `before` column reproduces the previous topology
choice as well as the previous rate and the two corrections stay separable.

**The change runs from 0.24x to 1.51x, and it changes sign.** Three mechanisms
put it there and none of them cancels:

1. **The two families reach iso-area at very different slot counts.** At 554,700
   mm2 the ROM side is twelve wafers spanning 681 reticle fields and the GPU
   side is 672 devices. Under `pipeline` both are charged their own slot count,
   which is why the raw corrections are 15.6x and 18.3x on Qwen -- close. But
   the correction is not applied to a fixed topology.
2. **It changes which topology wins, and the winner is chosen per design.** Both
   families abandon pipeline at batch 1. The GPU goes to `tensor` -- one slot,
   the whole cluster on one token, 122 all-reduces per token. The ROM side goes
   to `wafer-tensor` at one wafer and to `wafer-hybrid` above it: tensor-parallel
   across the 57-to-84 reticle fields of each wafer, pipeline-parallel across the
   wafers, so `token_slots` is the wafer count rather than the field count.
3. **The two sides pay very different prices for that switch.** A wafer's mesh
   collective is cheap enough that a ROM design can afford a 57-way tensor group;
   a GPU cluster large enough to hold DeepSeek-Pro spans 84 NVLink islands, so
   most of its all-reduce crosses InfiniBand. On Qwen at 277,350 mm2 the GPU's
   correction (15.7x) exceeds the ROM's (10.4x) and the ratio **rises** to
   7.96x; on Pro at 554,700 mm2 the ROM's (11.1x) exceeds the GPU's (2.7x) and
   the ratio falls to 8.63x.

**The batch curves change shape, and for the sparse models they change sign.**
Per-user tok/s at equal silicon, best design on each side at each batch:

| batch | Qwen3-8B @8K | DeepSeek-Flash @200K | DeepSeek-Pro @1M |
|---:|---:|---:|---:|
| 1 | 8.91x | 9.19x | 9.01x |
| 8 | 7.04x | 12.61x | 15.73x |
| 32 | 4.13x | 21.60x | 19.37x |
| 64 | 2.60x | 26.69x | 18.89x |
| 256 | **0.92x** | **36.52x** | **17.33x** |

Under the old rule every one of these fell with batch, and "the advantage erodes
with batch" was a standing finding of this document. **It survives only for the
dense model.** For both sparse models the ratio now rises, because the GPU's
per-user rate collapses faster than the ROM's: a cluster large enough to hold
DeepSeek-Flash must choose between a pipeline whose slots multiply its latency
and a tensor group whose collective it cannot afford. Qwen is the counter-case
and the honest one -- at batch 256 the GPU wins outright, 516 against 475,
because a dense model's KV read is per-user, never amortises, and is what binds a
ROM machine at batch.

**What survives.** The direction at batch 1 is intact -- at equal silicon a ROM
design is still faster per user than a GPU cluster at every rung of the ladder,
by 5.7x to 10.9x. What is gone is the claim that the advantage *grows* with silicon. It
does not: on the corrected model the ROM side's per-user rate **falls** with
area under every topology it can run, from 7,936 tok/s on one wafer to 3,811 on
twelve for Qwen, because more silicon means either more slots to traverse or a
wider collective to complete. **The best per-user ROM machine is the smallest one
that holds the model**, which is the opposite of what this document previously
recommended.

**What is assumed.** Aggregate throughput is reported at steady state; fill and
drain are not charged, so a request short compared with the slot count pays up to
one extra traversal that is not billed. The weight replication a pipeline deeper
than the layer count implies -- the surplus partitions hold replicas of a stage,
each needing its own copy of that stage's weights -- is not charged against
capacity. Both favour the deepest pipelines, which after this correction are on
the GPU side of the comparison. Running the other way,
`efficiencies.stage_balance` (0.9) is applied when `device_count > 1` rather than
when the machine has more than one partition, so a **one-wafer** tensor-parallel
design escapes it while a twelve-wafer one does not -- 1.11x in favour of the
design that now wins at batch 1 for two of the three models. All three are stated
in `TECHNICAL_DIRECTION_RECOMMENDATION.md` section 0.12 and none is fixed here.

## 2e. The DeepSeek KV profiles were read, not run, and they were 3.2x low

Landed separately by the model owner in
`configs/models/deepseek-v4-flash-0731.json` at commit `84577b6` and carried to
`deepseek-v4-pro-0813.json` at `37d0063`, and re-run here. Two per-entry
constants had been read off the implementation rather than measured while
running it: `entry_bytes` 583 -> **1,024** and `index_entry_bytes` 68 -> **256**.
The structure was right; the constants were not. Against the reference oracle
the corrected Flash profile now matches the engine's own KV reads to 0.9996 at
32K and 0.9999 at 128K, recorded in
`results/roofline/deepseek_v4_kv_model_validation.json`. Pro has never been executed on the oracle, so its
correction is graded `assumed_by_analogy` and every Pro KV number inherits that
grade.

The root cause is worth naming: 583 bytes is an **FP8 KV assumption** -- 576
elements at one byte plus scales -- where the released implementation reads the
512-wide latent at BF16. A KV precision disagreement had been carried as a
measurement.

The weight-to-KV read ratio at batch 1 **falls from 113.2:1 to 35.3:1 for Flash
at 200K and from 58.9:1 to 18.0:1 for Pro at 1M**. Pro, the longest context in
the study, is now the *least* ROM-favourable of the three models on this measure
rather than the most -- an inversion of the ordering section 2 rests on. The
iso-area comparison at batch 1 does not move at all, because both machines are
weight-bound there; the aggregate comparison at serving batch is halved:

| B | ROM aggregate before | after | ratio before | **ratio after** |
|---:|---:|---:|---:|---:|
| 1 | 57,266 | 57,260 | 27.1x | **27.1x** |
| 8 | 394,617 | 269,805 | 38.0x | **26.0x** |
| 64 | 983,395 | 456,796 | 21.6x | **10.1x** |
| 256 | 1,170,513 | 493,437 | 9.4x | **4.0x** |

Pro moves the same way: its aggregate ratio at batch 256 falls from 5.2x to
**3.0x**, and its taper starts at batch 4 instead of 8.

Every GPU figure in those tables moves by less than 2%, so the whole of the
change is the ROM side losing an advantage it never had. And on the designs
common to both runs, 10 Flash points and 6 Pro points that were reported
feasible do not fit their KV.

**One further consequence, retracted in full.** The published claim that an
interleaved KV index array costs 1.30x-1.67x in access granularity, and the
recommendation to pack it separately as "the cheapest 30% in this program",
both rested on the 68-byte index entry. At the measured 256 bytes the entry
exceeds both the 32-byte HBM granule and the 128-byte SRAM granule, so the
inflation is **1.00x on both models and both stores** and there is no 30% to
collect. The mechanism is real and still parameterised; this workload simply
does not exercise it.

This is the same failure as section 2b and 2c in a different costume, and it is
worth naming as a rule rather than as three incidents. **A number derived by
reading an implementation is a hypothesis. A number derived by running it is a
measurement.** 583 bytes was a hypothesis. So was "an on-wafer all-reduce costs
one hop". So is every watt this model currently reports.

## 2f. The power numbers in this document are wrong by 7-9x, and none of the speed numbers depend on them

Characterised, not fixed. The model reproduces **54.21 W** for an A100 running
Llama-3.1-8B at batch 1 against a published 400 W, and **27.04 W** for Taalas
HC1 at its published operating point against a published 200-250 W.

The model counts three things -- bytes out of a memory, bytes out of a KV store,
and multiply-accumulates -- and nothing else. Drive the A100 at its published
peak HBM bandwidth **and** its published BF16 roof at the same time and the
model still produces only **85.3 W against a 400 W TDP**, so this is not an
activity-factor error: it is power the model does not enumerate at all --
leakage, clock distribution, operand delivery, control, NoC, memory-controller
floor.

**Nothing in section 2 depends on it.** `thermal_scale` is exactly 1.0 at all
11,747 feasible points in both studies, and `step_time = raw_step_time x
thermal_scale` is the only path by which power reaches any other quantity. That
is a structural statement rather than an empirical one. Every tokens/s in this
document survives; every watt and every joule-per-token in it is unpublishable.

**The dark-silicon question this program was asked cannot currently be
answered.** The cooling limit is sound -- 0.50 W/mm2 derived from the A100's own
400 W over 826 mm2 -- and modelled power density peaks at 0.181 W/mm2 anywhere
in either study, so the limit never binds. Scaling every point by the observed
shortfall as a bound rather than a result, 2.9-8.4% of feasible points would
exceed the cooling limit, and **the worst of them at every multiplier is a small
dense array at high batch, not a wafer.** A wafer is power-sparse because a ROM
sweep is a fixed cost spread over far more silicon. If that survives a correct
power term, it is an argument for wafer-scale this document has not yet made.

**Do not close this with one multiplier.** The two shortfalls are nearly equal
and that is most likely a coincidence: the A100's survives at simultaneous peak
and is therefore structural, while HC1's could be entirely inside
`energy.rom_read_j_per_byte` -- 0.5 pJ/byte, graded `assumed`, sourced as *"no
fabricated leading-node mask-ROM macro energy published"*. Reaching 250 W needs
about 4.6-5.8 pJ/byte from that one term, which is not obviously wrong for an
array whose read **is** the multiply.

**Every comparison in this program must state the silicon area on both sides.**

- A reticle-class ROM chip is compared against **one** GPU die.
- A wafer-scale part (46,225 mm²) is compared against **~56 A100-equivalent
  dies**, because that is equal silicon. Blackwell is a two-die package, so
  count per package accordingly.

## 3. What went wrong, twice

**The legacy study's ROM profile was compute-starved by assumption.** It gave a
whole wafer a 5.00e14 ops/s FP8 roof — 0.11× the compute of a single B200 die —
across 29× the area, an assumed compute density 0.0038× NVIDIA's per mm². Its
own evidence field said `"assumed:midpoint hypothesis only"`. Every ROM point
was therefore `compute_C5`-bound, and that was read as a property of ROM
architectures rather than of the placeholder.

**The current study's comparison was not iso-area.** It reported ROM-wafer-N7 at
4,125 tok/s for Qwen3-8B against A100-x32 and A100-x64 — one 46,225 mm² wafer
against 26,432–52,864 mm² of GPU. Per unit area that ROM model is **234× more
pessimistic than a shipping part**: 0.089 tok/s/mm² against HC1's 20.9.

**The design error underneath it is nameable.** The study's ROM wafer is
`kv_beachfront_C8`-bound at every batch for Qwen, because it puts the KV cache
behind HBM2e. Taalas keeps KV in on-die SRAM. For an 8B model that is the whole
difference — the study penalised ROM with a memory technology the real product
does not use for that data.

## 4. The method, stated so it is checkable

1. **Fix the silicon area first.** It is the binding constraint; everything else
   is an allocation decision within it.
2. **Derive capacity, bandwidth and compute roof from area and published
   densities.** They are outputs. A profile that states them as free inputs is
   not a design.
3. **Search for current published data** rather than inheriting a configured
   number. Grade every figure published / derived / measured / assumed, with a
   source.
4. **Validate against a shipping part** before predicting one that does not
   exist.
5. **Compare at equal area**, and say the area on both sides.

The failure mode this replaces is not arithmetic error. It is accepting a number
because it was already in the file.

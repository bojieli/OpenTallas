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
written and says 8.33x now; section 2d supersedes every per-user rate below, and
section 2d-bis records the 2026-08-31 link re-grading that took it from 8.63x to
8.33x.**
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

The ratio band in that column is the study re-run with *every* hop latency at
each end of its stated range, **on both sides at once**. That presentation was
itself an artefact and is superseded: moving both sides partly cancels, so the
joint interval came out narrower than the wafer side's own and hid where the
width lived. Section 2d-bis carries the replacement, in which each side's band is
reported apart. The premise quoted here -- that NVIDIA publishes no NVLink
latency figure of any kind -- is also **withdrawn**; NCCL's shipping source
carries one.

## 2c. The mirror-image problem on the ROM side, and it was worse

The instruction that produced section 2b was to look for the same fault on our
own side. There were two, and both flattered us.

**The on-wafer collective was charged a flat two hops however far it reached.**
A stitched wafer is a 2-D mesh with no switch -- Cerebras states this outright
-- so an all-reduce cannot finish before the far corner has answered. Cerebras
measured their own at *"a cycle count only about 10% greater than the diameter
of the system"* (Rocki et al., SC20), and the diameter of an N-region mesh is
`2(sqrt(N)-1)`. The model now charges `1.1 x diameter` traversals:

| span | old traversals | new traversals | all-reduce at 125 ns/hop | per token, 61 layers |
|---:|---:|---:|---:|---:|
| 57 regions (1 wafer) | 1 | 15.4 | 0.25 -> 1.93 us | 31 -> 235 us |
| 681 regions (12 wafers) | 1 | 57.2 | 0.25 -> 7.15 us | 31 -> 872 us |

(At the 100 ns this section was written against, the same rows read
0.20 -> 1.54 us / 24 -> 188 us and 0.20 -> 5.72 us / 24 -> 698 us. The hop was
re-graded to 125 ns on 2026-08-31; section 2d-bis.)

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
6,000-7,200 tok/s. When this section was written that made the model choose
pipeline over tensor parallelism on the wafer at every operating point;
**section 2d reverses that**, because the pipeline it was being compared against
was itself overstated by its slot count. Wafer-scale tensor parallelism now wins
at batch 1 on both families, at those same 6,000-7,200 tok/s.

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
| Qwen3-8B | 46,225 | 51,291.3 | 6,505.3 | 7.88x | 56 | 3,440.9 | 789.4 | 4.36x | 14.91x | **8.24x** | 0.55x |
| Qwen3-8B | 92,450 | 48,716.3 | 5,878.5 | 8.29x | 112 | 5,074.5 | 848.7 | 5.98x | 9.60x | **6.93x** | 0.72x |
| Qwen3-8B | 138,675 | 48,716.3 | 5,391.7 | 9.04x | 168 | 6,028.6 | 870.5 | 6.93x | 8.08x | **6.19x** | 0.77x |
| Qwen3-8B | 184,900 | 48,716.3 | 4,979.3 | 9.78x | 224 | 6,654.1 | 881.8 | 7.55x | 7.32x | **5.65x** | 0.77x |
| Qwen3-8B | 277,350 | 48,716.3 | 4,318.7 | 11.28x | 336 | 7,424.4 | 565.8 | 13.12x | 6.56x | **7.63x** | 1.16x |
| Qwen3-8B | 369,800 | 48,716.3 | 3,812.9 | 12.78x | 448 | 7,880.6 | 568.2 | 13.87x | 6.18x | **6.71x** | 1.09x |
| Qwen3-8B | 554,700 | 56,411.9 | 3,447.0 | 16.37x | 672 | 8,396.5 | 570.6 | 14.72x | 6.72x | **6.04x** | 0.90x |
| Flash @200K | 46,225 | 18,475.6 | 4,663.6 | 3.96x | 56 | 1,485.7 | 544.1 | 2.73x | 12.44x | **8.57x** | 0.69x |
| Flash @200K | 92,450 | 27,333.1 | 4,472.2 | 6.11x | 112 | 1,703.4 | 568.8 | 2.99x | 16.05x | **7.86x** | 0.49x |
| Flash @200K | 138,675 | 34,088.9 | 4,375.0 | 7.79x | 168 | 1,795.0 | 578.0 | 3.11x | 18.99x | **7.57x** | 0.40x |
| Flash @200K | 184,900 | 38,879.0 | 4,281.2 | 9.08x | 224 | 1,845.5 | 582.8 | 3.17x | 21.07x | **7.35x** | 0.35x |
| Flash @200K | 277,350 | 45,220.6 | 4,104.3 | 11.02x | 336 | 1,899.6 | 404.0 | 4.70x | 23.81x | **10.16x** | 0.43x |
| Flash @200K | 369,800 | 49,229.4 | 3,941.1 | 12.49x | 448 | 1,928.1 | 405.2 | 4.76x | 25.53x | **9.73x** | 0.38x |
| Flash @200K | 554,700 | 54,012.8 | 3,650.5 | 14.80x | 672 | 1,957.7 | 406.4 | 4.82x | 27.59x | **8.98x** | 0.33x |
| Pro @1M | 92,450 | 8,986.6 | 2,359.5 | 3.81x | 112 | 529.1 | 274.9 | 1.92x | 16.99x | **8.58x** | 0.51x |
| Pro @1M | 138,675 | 9,497.6 | 2,016.1 | 4.71x | 168 | 561.6 | 283.0 | 1.98x | 16.91x | **7.12x** | 0.42x |
| Pro @1M | 184,900 | 11,753.0 | 2,002.6 | 5.87x | 224 | 579.7 | 287.4 | 2.02x | 20.27x | **6.97x** | 0.34x |
| Pro @1M | 277,350 | 15,371.5 | 1,972.0 | 7.79x | 336 | 599.4 | 221.0 | 2.71x | 25.65x | **8.92x** | 0.35x |
| Pro @1M | 369,800 | 18,073.4 | 1,933.6 | 9.35x | 448 | 609.8 | 222.4 | 2.74x | 29.64x | **8.70x** | 0.29x |
| Pro @1M | 554,700 | 21,951.3 | 1,863.2 | 11.78x | 672 | 620.6 | 223.7 | 2.77x | 35.37x | **8.33x** | 0.24x |

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
   correction (13.1x) exceeds the ROM's (11.3x) and the ratio **rises** to
   7.63x; on Pro at 554,700 mm2 the ROM's (11.8x) exceeds the GPU's (2.8x) and
   the ratio falls to 8.33x.

**The batch curves change shape, and for the sparse models they change sign.**
Per-user tok/s at equal silicon, best design on each side at each batch:

| batch | Qwen3-8B @8K | DeepSeek-Flash @200K | DeepSeek-Pro @1M |
|---:|---:|---:|---:|
| 1 | 8.24x | 8.57x | 8.58x |
| 8 | 6.85x | 11.58x | 14.75x |
| 32 | 4.19x | 19.76x | 18.48x |
| 64 | 2.71x | 24.71x | 18.35x |
| 256 | **0.98x** | **35.13x** | **17.18x** |

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

## 2d-bis. Both binding link constants were re-graded, and the band is now reported per side

**2026-08-31.** The two constants that decide most of this comparison were both
graded `assumed`. Neither is now.

| constant | was | is | grade | swept | direction |
|---|---|---|---|---|---|
| `links.on_wafer.hop_latency_s` | 100 ns | **125 ns** | assumed -> **derived** | 30-500 ns -> **75-250 ns** | **against** this study |
| `links.nvlink3.hop_latency_s` | 1.5 us | **2.5 us** | assumed -> **derived** | 1.0-5.5 us -> **1.0-10.3 us** | **for** this study |
| `links.nvlink5` / `nvlink5_nvl72` | 1.5 us | **1.2 us** | assumed -> **derived** | 1.0-5.5 us -> **0.7-5.5 us** | against |

**Granularity is the whole content of the on-wafer row.** The model charges an
`on_wafer` hop for crossing one 815 mm2 reticle field -- a 28.55 mm square, 57 to
a wafer. Cerebras publishes a *single clock cycle* per hop, but that hop is
between adjacent cores about 0.23 mm apart, and there are ~126 of them across one
of this model's fields. Substituting the published cycle directly would have set
this constant to about 1.2 ns and taken the headline from 8.33x to 14.7x. What
transfers is the primitive -- one cycle per router pitch -- plus Cerebras'
published core grid (Hot Chips 34: die "17mm x 30mm", "66 x 154 Cores") and
clock, which give 116-150 ns at N7 and 115-148 ns at N5; Tesla's published
"100ns die-to-die latency" for a 645 mm2 reticle-class die gives ~111 ns for the
same object built the other way. 125 ns is the middle of those. The withdrawn
cross-check in the old note -- "about 73 tiles across one 815 mm2 reticle field"
-- was 1.7x low and ran in this study's favour.

**The NVLink row is the one that flatters us, so it is pinned to the best
measured kernel rather than to the shipping one.** The model has no
per-collective software term, so `2 x hop` *is* the whole in-domain all-reduce.
The best measured small-message all-reduce on 8x A100 over NVLink 3.0 is 5.0 us
(MSCCL++, ASPLOS 2026); stock NCCL on the same hardware measures 20.6 us across
four independent runs. 2.5 us is the first of those halved. The old 1.5 us was
below every A100 measurement in existence.

**And the band is now reported per side.** At 554,700 mm2, batch 1, Pro at 1M:

| | stated | wafer fabric alone | cluster fabric alone | both together |
|---|---:|---:|---:|---:|
| N6 vs A100 | **8.33x** | 11.21x -> 5.41x | 6.92x -> 12.96x | 9.31x -> 8.42x |
| N5 vs B200 | **4.01x** | 5.66x -> 2.48x | 3.33x -> 6.85x | 4.71x -> 4.24x |

The joint column is a 1.1x interval and each side alone is about 2x. Nothing got
more certain when the two were moved together -- the two uncertainties cancelled,
and publishing only the joint interval claimed a precision neither constant
supports. Before the re-grading the same presentation gave a one-sided ROM band
of 13.48x-3.26x against a published joint band of 11.82x-4.46x: the ROM side's
own band was *wider than the interval being published*
(`docs/COMPARISON_FAIRNESS_AUDIT.md` A1).

What is still `assumed` on the ROM side: `links.inter_wafer.hop_latency_s`
(5 us, swept 1-10 us), which is now the largest unmeasured link in the model and
84% of the two-wafer Pro design's link budget; and
`MESH_ALLREDUCE_DIAMETER_FACTOR` = 1.1, which is *measured* but is the optimistic
end of a measured 1.1-2.0x range and has no sweep of its own.

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
one hop". So was every watt this model reported until section 2f, where six
power terms were derived from primitives, adversarially verified, and all six
refuted -- one of them by re-running the measurement it rested on and finding it
was the decay tail of a preceding workload rather than a steady state.

## 2f. The power model was rebuilt. It is right on the A100, 2.9-3.6x low on HC1, and the ROM joules here are lower bounds

**Superseded.** The previous version of this section said the power numbers in
this document were wrong by 7-9x, that `thermal_scale` was exactly 1.0 at all
11,747 feasible points, and that the dark-silicon question could not be
answered. All three statements were true of the model as it then stood and none
of them is true now.

Six power terms were derived from graded primitives and adversarially verified.
**All six were refuted** and all six are applied at their verifiers' corrected
values -- including the two that move power *down*, which is the direction that
makes this document's own thesis harder to argue.

**Where the two published parts now land.**

| gate | published | modelled | ratio | result |
|---|---:|---:|---:|---|
| A100 80GB at its TDP, under a saturating load | 400 W | 389.9 W | 0.97x | PASS (within 2x) | <!-- figure: 0.97 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.a100_tdp_power.ratio" name="A100 TDP power gate ratio" -->
| Taalas HC1 card power at its published operating point | 200-250 W | 70.2 W | 0.28x | **FAIL** | <!-- figure: 0.28 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.ratio" name="HC1 card power gate ratio" -->

Reported at both ends of the whole power band, every term moved together:

| power band | A100 | ratio | HC1 | ratio to 250 W | ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 267.1 W | 0.67x | 54.3 W | 0.22x | 0.27x | <!-- figure: 267.1 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.power_gate_band.low.a100_tdp_power_w" name="A100 TDP power, band low" -->
| **stated** | **389.9 W** | **0.97x** | **70.2 W** | **0.28x** | **0.35x** | <!-- figure: 70.2 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.modelled_value" name="HC1 card power, stated" -->
| high | 626.6 W | 1.57x | 267.1 W | 1.07x | 1.34x | <!-- figure: 1.57 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.power_gate_band.high.a100_ratio_to_published" name="A100 TDP power ratio, band high" -->

**The A100 gate is the weaker of the two and this document must not quote it as
independent.** The clock term inside it was calibrated as 20-45% of a shipping
GPU's published TDP density -- a different GPU, but still a GPU TDP -- so a sum
containing it, compared with a GPU's TDP, is partly an input checked against its
own family. The HC1 gate has no such circularity, because Taalas publishes no
microarchitecture and no energy at all, and **it is the one that fails.**

**The previous version's own competing explanation was tested and it went the
other way.** That section said HC1's shortfall could be entirely inside
`energy.rom_read_j_per_byte` -- 0.5 pJ/byte, `assumed` -- and that reaching
250 W needed about 4.6-5.8 pJ/byte from that one term. The evidence moved that
term to **0.08 pJ/byte**, six times *lower*, which made this gate worse by about
4x on that term alone. It was adopted anyway. The consequence is that operand
delivery is now the **largest** dynamic term on HC1 -- 10.0 W against 3.2 W of <!-- figure: 10.0 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.detail.dynamic_power_w_by_term.operand_delivery_j" name="HC1 operand-delivery power" -->
array read -- which is the physically sensible picture for a mask-ROM array: it
reads its weights for almost nothing, and what it pays for is getting those
bytes to the arithmetic.

**Dark silicon, which this document could not previously express at all.** The
old throttle divided total energy by the total limit, so stretching a step
always reduced modelled power and every design was coolable at some speed.
Static power does not fall when a step is stretched, so the coolable step time
now solves `t >= E_dynamic / (cooling_limit - P_static)`, and a part whose
leakage and clock alone meet its budget does not exist rather than running
slowly.

<!-- figure: 105 src="results/roofline/n5_vs_b200/analytical.json#power_and_energy.thermally_throttled_points" name="power-limited points, N5/B200" -->
**105 of 6,108 feasible points are power-limited** -- all of them in the
N5/B200 study, the worst throttled 1.35x.
The prediction this section made under a uniform multiplier half survives:

- **It survives on shape.** Every throttled point is a small or large array.
  **No wafer is throttled**, and no wafer-scale ROM design exceeds 46% of its
  cooling budget against a median of 21%. A ROM sweep is a fixed cost spread
  over far more silicon, so wafer-scale is power-sparse -- and that is now an
  argument this document *can* make, from a correct power term rather than from
  a bound.
- **It does not survive on batch.** A uniform multiplier on a
  traffic-proportional model necessarily peaks at high batch. Static power does
  not scale with traffic, so **batch 1 is throttled too**, and the worst point
  in either study is at **batch 8**.
- **And it produced a design conclusion the bound could not have.** Every one of
  the 100 throttled points puts its KV in HBM, and the worst point's dynamic
  energy is **96.8% KV read against 0.5% weight read**. The ROM sweep is not
  what melts it. Every SRAM-KV ROM design in both studies stays under budget.
  **Keep the KV on die.**

## 2g. Energy per token, on both sides, which this document could not state before

Not paying DRAM access energy for weights is much of this document's argument,
and it could not be quantified while every watt in the model was 7-9x low. The
figures below include the static share amortised over the tokens the step
actually produces, so a machine that is fast and leaky is not flattered against
one that is slow and cool.

**At the two anchors, same workload -- Llama-3.1-8B at batch 1:**

| part | J/token | W | tok/s |
|---|---:|---:|---:|
| Taalas HC1 (modelled reconstruction) | 0.005736 | 70.2 | 12,232 | <!-- figure: 0.005736 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.detail.energy_j_per_token" name="HC1 J/token" -->
| A100 80GB, weight-bound gate | 1.462191 | 358.8 | 245 | <!-- figure: 1.462191 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.a100_weight_bound.detail.step.metrics.energy_j_per_token" name="A100 J/token at the weight-bound gate" -->

255x in tokens per joule -- and it is a **ceiling on the ROM advantage, not a
measurement of it.** The GPU is at batch 1, which is a GPU's worst operating
point; the ROM read energy is `assumed` over a 17x bracket; and the HC1 power
gate says the ROM total is 2.9-3.6x below a shipping part, so the ROM joules
are a lower bound by roughly that factor.

**At equal area, on the study's own best designs, it is far smaller and it moves
with batch in the direction the architecture predicts:**

| study | model | batch 1 | batch 256 |
|---|---|---:|---:|
| N6 vs A100 | Qwen3-8B (dense) | 19.3x | **1.8x** | <!-- figure: 19.3 src="results/roofline/n6_vs_a100/analytical.json#power_and_energy.energy_per_token[model=Qwen3-8B,batch_size=1].tokens_per_joule_advantage_x" name="Qwen3-8B tokens/joule advantage at batch 1, N6" -->
| N6 vs A100 | DeepSeek-V4-Flash (sparse) | 17.3x | **55.5x** |
| N6 vs A100 | DeepSeek-V4-Pro (sparse) | 25.9x | 18.8x |
| N5 vs B200 | Qwen3-8B (dense) | 5.3x | **2.6x** |
| N5 vs B200 | DeepSeek-V4-Flash (sparse) | 4.6x | **36.9x** |
| N5 vs B200 | DeepSeek-V4-Pro (sparse) | 14.3x | 20.9x | <!-- figure: 20.9 src="results/roofline/n5_vs_b200/analytical.json#power_and_energy.energy_per_token[model=DeepSeek-V4-Pro-0813,batch_size=256].tokens_per_joule_advantage_x" name="Pro tokens/joule advantage at batch 256, N5" -->

**A dense model gives the energy advantage back as batch rises; a sparse one
does not.** A GPU amortises one weight read over the whole batch, so its joules
per token fall roughly as 1/batch until KV takes over. The ROM part's weight
read was already nearly free, so it has nothing to amortise. On a sparse model
the GPU cannot amortise -- batching engages more experts -- so the ROM advantage
*grows*. **The batch-1 headline is the weakest form of this argument on a dense
model and the strongest on a sparse one, and quoting the dense batch-1 number
without the batch-256 number beside it would be quoting the best case as the
case.**

**What is still uncharged, on both sides.** L1/L2 traversal, which the same
SC 2025 measurement puts at a further 6.30 pJ/bit on an A100 for streaming
traffic. The long-path operand ladder -- the term applied here is the
*tile-local floor*, and HBM to L2 to register file is 8-10 pJ/B further.
ROM-array leakage, held at zero because its companion term was refuted as
underived; at the top of its reconstructed bracket it would add 10.4 W to HC1
and still not reach 200 W.

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
   exist -- and report the gate's outcome rather than tuning to it. There are
   four gates now: the HC1 throughput gate at 0.72x, the A100 weight-bound gate
   at 1.000x, the A100 TDP power gate at 0.97x, and the HC1 card-power gate at
   0.28x, **which fails**. A failing gate that is reported is worth more than a
   passing one that was fitted, and the residual is stated with its size in
   section 2f.
5. **Compare at equal area**, and say the area on both sides.

The failure mode this replaces is not arithmetic error. It is accepting a number
because it was already in the file.

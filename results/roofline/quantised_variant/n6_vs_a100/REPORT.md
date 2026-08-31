# SECONDARY: quantised variant of `n6_vs_a100`

> **SECONDARY -- PROJECTION, NOT A MEASUREMENT.** Both sides are re-quantised to 4.25 bits per parameter. **0 tokens have ever been produced at this precision anywhere in this program, on either backend**, and no accuracy has been measured on either side. Every figure below is `derived`. This is a projection of a machine nobody has run.

> **This is not the primary result.** The primary result is `results/roofline/n6_vs_a100/`, which prices the released checkpoint's own packing on both sides and is unchanged by anything here. No ratio on this page may be quoted without the primary ratio from the same row in the same sentence, and the columns below are laid out so that is the natural way to read it.

## The rule the variant follows

**A quantisation applies to both sides.** That is not a courtesy; it is
arithmetic. A GPU serving 4.25-bit weights reads 3.76x fewer weight bytes
exactly as the ROM part does, and a study that gave the saving to one side
would be running the asymmetry the released-packing rule exists to stop --
the same rule this program already records for an FP8 KV latent in the
DeepSeek profile's `kv_precision_sensitivity`.

- **Format.** 4.25 bits per parameter, held identical on both sides. That is MXFP4 as the OCP Microscaling specification defines it -- 4-bit E2M1 elements in blocks of 32 with one 8-bit E8M0 block scale, (32x4 + 8) / 32 = 4.25 -- and it is within a rounding of INT4 group-128 with an FP16 scale and an INT4 zero point, (128x4 + 16 + 4) / 128 = 4.16, which is how vLLM and TensorRT-LLM actually ship 4-bit weights today.
- **Arithmetic.** Both sides declare the w4a8 datapath their stored width implies, and each part then executes it or emulates it according to its OWN published format table, which is where the two studies stop being symmetric. configs/hardware/technology.json gives a100_sxm_80gb native_formats [bf16, fp32] and emulates fp4, fp8 and w4a8 to bf16: Ampere has no low-precision floating-point tensor core, so an A100 serving 4-bit weights gains BYTES and never arithmetic. b200_sxm declares w4a8 native. The ROM side takes the arithmetic credit in both studies. That asymmetry is a fact about Ampere, not a modelling choice, and it is the reason BOTH pairings are published: reporting only n6_vs_a100 would be selecting the study in which the GPU is architecturally forbidden from taking the credit the ROM side takes.
- **Scope.** Qwen3-8B only. The variant is defined only where the release ships ABOVE the width production GPU stacks already serve. Qwen3-8B ships at 16.00 bits and qualifies. DeepSeek-V4-Flash-0731 at 4.70 and DeepSeek-V4-Pro-0813 at 4.46 bits already ship mixed FP8 dense plus MXFP4 routed -- they are at that floor, and re-quantising them would mean pushing the GPU below what any production stack serves, which is the same one-sided offer in the other direction.

## What it changes, against the primary, row for row

| Model | | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area GPU | GPU user tok/s | ratio |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Qwen3-8B | PRIMARY (BF16, 16.00 bits) | `ROM-N6-native-SRAMKV-array-pipeline-x3` | 2,445 | 2,791.2 | 1,141.6 | 1 | `a100_sxm_80gb-x3-tensor` | 258.9 | 10.78x |
| Qwen3-8B | variant (4.25 bits, both sides) | `ROM-N6-q4p25-SRAMKV-array-pipeline-x2` | 1,630 | 5,602.5 | 3,437.1 | 1 | `a100_sxm_80gb-x2-tensor` | 489.0 | 11.46x |

**Read the ratio column as a pair, never alone.** If the variant's ratio
is larger than the primary's, quantisation did not level the comparison,
and the reason has to be stated rather than banked: on a ROM machine the
weight term is a full-array sweep whose duration is a technology constant
independent of the bytes stored, so fewer bits buy the ROM side array area
and replication rather than sweep time, while the GPU's weight term is
bytes over bandwidth and falls exactly in proportion. Whichever way the
number moves, both studies are published, because the A100 pairing is the
one where the GPU physically cannot follow the ROM side's datapath change
and the B200 pairing is the one where it can.

**The variant is selected by the same rule as the primary, applied to
the same code path.** That is not a nicety: if the two artifacts were
selected by different rules, the row-for-row table above would be
comparing a rule change and a precision change at once and no reader
could tell which one moved the number. The rule and the frontier it
produces follow.

## The recommended design per model, and the rule that picks it

**The metric, stated here because a recommendation without its rule is an
opinion.**

> Among the ROM designs feasible for this model at this batch, keep every design that no other feasible design of the same model and batch beats on BOTH per-user tokens/s and tokens/s per 1,000 mm2. That non-dominated set is the reported frontier, and it is published in full. Order it by silicon area, start at the smallest feasible machine, and accept each larger rung only while the per-user tokens/s it adds per added mm2 is strictly greater than the tokens/s per mm2 the incumbent already returns on average; ties go to the smaller machine. The rung the walk stops on is the recommended design. Equivalently: maximise per-user tokens/s per mm2 over the feasible set. The two statements are the same rule -- accepting when (r - r0) / (a - a0) >= r0 / a0 is exactly r / a >= r0 / a0 -- and the marginal form is the one to read, because it is the engineering question: does the next slab of silicon work at least as hard as the slab you have?

Why this rule and not another: Ranking on per-user tokens/s alone hands an 8B model a 46,225 mm2 wafer, because a per-user rate has no area in it and a wafer is always at least as fast as anything cut out of it -- on Qwen3-8B that is 2.33x the rate of the three 815 mm2 reticles that hold the same checkpoint, bought with 18.9x the silicon and an eighth of the throughput density. Ranking on silicon area alone picks the smallest machine that physically holds the checkpoint, whatever it delivers. A 5%-of-peak tolerance does not fix the first: it is a tie-break among near-peak designs and is orthogonal to area, so it shrinks the machine only in the cases nobody was worried about. The domination filter plus the marginal-return walk fixes both, needs no latency target to be stated, and -- because the filter is on (per-user rate, rate per mm2) -- makes it structurally impossible to recommend a design that another feasible design of the same model beats on both axes at once.

The bar is `1` -- parity. The frontier is
taken over the `batched` machine, which is what the
main tables show. **The recommendation is not a single number and must not be
quoted as one:** every row below carries per-user rate, aggregate rate,
resident sessions, throughput density, power, energy per token and the
binding constraint together, because a per-user rate published without the
resident-session count beside it is how a one-session latency device gets
read as a server.

The GPU comparator at each ROM area is N copies of one unified HBM die, N chosen so the silicon matches, and the cluster is allowed to pick its own parallelism. The comparison is read at the ROM side's CHOSEN area, not at a fixed rung of the area ladder where both sides are past their own optimum.

### Qwen3-8B at 8,192 tokens

**Recommended: `ROM-N6-q4p25-SRAMKV-array-pipeline-x2`** -- 2 x 815 mm2 reticle dies, 1,630 mm2 total, `pipeline`-parallel, KV in SRAM, spare silicon to `sram`.

- **5,602.5 tok/s per user** (0.18 ms/token), binding on `weight_read`
- **3,437.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 5,603 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 167 W at 0.102 W/mm2, 29.8 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 2 copies of one unified HBM die -- `a100_sxm_80gb-x2-tensor`, 1,652 mm2, area ratio 0.9867 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 1,630 | 1,652 | 0.9867 |
| user tok/s | 5,602.5 | 489.0 | 11.46x |
| aggregate tok/s | 5,603 | 489 | 11.46x |
| resident sessions | 1 | 115 | -- |
| J/token | 0.0298 | 1.1404 | 38.3x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 115 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x8-tensor` at 6,608 mm2 and 1,265.8 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-q4p25-SRAMKV-array-pipeline-x4-romfill` | 3,260 | 9,469.6 | 2,904.8 | 1 | 11.44x |
| rank on per-user rate alone | `ROM-N6-q4p25-SRAMKV-array-pipeline-x5-romfill` | 4,075 | 9,525.4 | 2,337.5 | 1 | 9.92x |
| smallest feasible machine | `ROM-N6-q4p25-SRAMKV-array-pipeline-x2` | 1,630 | 5,602.5 | 3,437.1 | 1 | 11.46x |
| **after -- this report's rule** | `ROM-N6-q4p25-SRAMKV-array-pipeline-x2` | 1,630 | 5,602.5 | 3,437.1 | 1 | 11.46x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-q4p25-SRAMKV-array-pipeline-x2` | 1,630 | 5,602.5 | 3,437.1 | -- | 3,437.1 | ACCEPT |
| `ROM-N6-q4p25-SRAMKV-array-pipeline-x4-romfill` | 3,260 | 9,469.6 | 2,904.8 | 2,372.4 | 3,437.1 | stop |
| `ROM-N6-q4p25-SRAMKV-array-pipeline-x5-romfill` | 4,075 | 9,525.4 | 2,337.5 | 1,604.4 | 3,437.1 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-q4p25-SRAMKV-array-pipeline-x2` **<-- recommended** | 1,630 | 2 | 5,602.5 | 5,603 | 3,437.1 | 1 | `weight_read` | 167 | 29.8 | `a100_sxm_80gb-x2-tensor` | 11.46x |
| `ROM-N6-q4p25-SRAMKV-array-pipeline-x4-romfill` | 3,260 | 4 | 9,469.6 | 9,470 | 2,904.8 | 1 | `compute` | 289 | 30.5 | `a100_sxm_80gb-x4-tensor` | 11.44x |
| `ROM-N6-q4p25-SRAMKV-array-pipeline-x5-romfill` | 4,075 | 5 | 9,525.4 | 9,525 | 2,337.5 | 1 | `compute` | 360 | 37.8 | `a100_sxm_80gb-x5-tensor` | 9.92x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 14 | densest | `ROM-N6-q4p25-SRAMKV-array-pipeline-x2` | 1,630 | 5,602.5 | 3,437.1 | 1 |
| array | 14 | fastest | `ROM-N6-q4p25-SRAMKV-array-pipeline-x5-romfill` | 4,075 | 9,525.4 | 2,337.5 | 1 |
| array | 14 | smallest | `ROM-N6-q4p25-SRAMKV-array-pipeline-x2` | 1,630 | 5,602.5 | 3,437.1 | 1 |
| wafer | 80 | densest | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,505.3 | 140.7 | 1 |
| wafer | 80 | fastest | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,505.3 | 140.7 | 1 |
| wafer | 80 | smallest | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,505.3 | 140.7 | 1 |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-q4p25-SRAMKV-array-pipeline-x2` | 1,630 | array | SRAM | 1 |
| 2 | `ROM-N6-q4p25-HBMKV-array-tensor-x5` | 4,075 | array | HBM | 298 |
| 4-256 | `ROM-N6-q4p25-HBMKV-array-pipeline-x5` | 4,075 | array | HBM | 298 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**What this section does not fix, and which recommendations it leaves exposed.** The ROM array class is sampled only at the device counts each floorplan's own sizing sweep chose: `ROM_AREA_LADDER` is applied where `plan.kind == "wafer"` and nowhere else, so a reticle array exists at an area only if some sweep landed there. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below so the holes are visible rather than described:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Qwen3-8B | HBM | rom | 5, 8 |
| Qwen3-8B | HBM | sram | 5, 8 |
| Qwen3-8B | SRAM | rom | 4, 5 |
| Qwen3-8B | SRAM | sram | 2 |

The omission runs **against** the array class, so the published ROM curve is a lower bound on the ROM curve rather than an upper one.

That splits the recommendations above into two kinds, and the split should be stated rather than left for a reader to work out. **Where the winner is the smallest feasible machine, the gap cannot touch it**: no rung exists below the minimum area, so nothing denser can be hiding there. **Where the winner is a wafer chosen over the array class, the gap is live**: the wafer is being compared against an array curve that is sampled at a handful of counts, and a rung the sweep never visited could in principle beat it on throughput density. Those are the weakest results on this page and they should be re-derived once the array class is emitted on the same explicit ladder the wafer class already gets. Either way, the curve BETWEEN rungs is not evidence and must not be read as any.

## What is wrong with these numbers, stated before anyone quotes them

- **Known modelling defect.** src/opentallas/roofline.py's balanced ROM+MAC rule sizes the MAC array at one weight byte per multiply-accumulate against a hard-coded fp8 compute density. At 4.25 bits a byte carries 1.88 weights, so the MAC array is under-provisioned by that factor and the array is correspondingly over-provisioned. The rule is exactly right at 16 bits on a bf16 datapath, which is why the BF16 primary is untouched by it. It is left as it is here rather than corrected, because correcting it would move 1,456 published ROM points in the PRIMARY studies -- 728 in each, every batched design with spare_area_policy = rom on a w4a8 datapath, all of them DeepSeek, which already executes w4a8 at its released packing of 4.70 and 4.46 bits -- and the instruction for this revision is that the primary result does not move except where the design selection moves it. The defect is recorded, its direction is stated on every variant table, and it should be fixed on its own, in its own change, where the size of the correction is the only thing being read.
- **Unmodelled on both sides.** Four real mask-ROM advantages have no term in this roofline and the variant must not be argued on them: zero scale-storage (a GPU pays 0.25 bits per parameter for an MXFP4 block scale and 0.5 for NVFP4, a mask ROM folds it into the datapath at mask time), zero dequantisation instructions and energy (QServe measures 20-90% GPU runtime overhead for INT4 dequant), free non-byte-aligned widths, and free codebook quantisation. One real mask-ROM DISadvantage is equally unmodelled: a mask ROM cannot be re-quantised after tape-out, so a bad quantisation is a scrapped mask set, a risk with no GPU counterpart. A fifth term, the balanced ROM+MAC floorplan rule, IS modelled and is modelled wrongly at this width -- see known_defect.
- **Accuracy.** ABSENT ENTIRELY, on both sides, and this is the variant's real exposure rather than its rate. The published band on 4.25-bit weights runs from NVIDIA's vendor-run '1% or less' on one model to the OCP MX authors' own direct-cast MXFP4 measurement of a 24% relative Lambada drop on LLaMA-7B (0.736 -> 0.557). Nothing in this program has measured where a real deployment lands inside that band, on either backend. A rate reported without that band beside it is the same class of claim as a projected speedup for a machine nobody has run.
- **What would make this a measurement.** (i) Quantise Qwen3-8B to this format and run the existing HBM lane: configs/hardware/abi3_capability/hbm_sram_single_chip.json already declares mxfp4 and fp8 contracts and an FP4 quantise/reconstruct pair, executed for DeepSeek. (ii) Build the ROM lane, where nothing exists: rom_qwen3.json needs a sub-byte weight-decode contract, a w4a8 contraction contract, backend lowering and a re-exported image. (iii) The gate cannot be token identity against the BF16 oracle -- quantisation changes tokens by construction. It has to be cross-backend identity, the ROM lane and the HBM lane at the SAME format producing identical tokens position for position, plus a measured accuracy budget with a divergence horizon in the form this program already reports. (iv) The w4a8 compute density needs silicon behind it at N6; it is currently derived from published A100 INT4/INT8 roofs scaled by logic density.
- **Everything the primary report's interpretation boundary says still
  applies here, and one thing more: the primary is a projection of a
  machine nobody has built running arithmetic this program HAS executed.
  The variant is a projection of a machine nobody has built running
  arithmetic nobody has executed. Those are not the same claim and this
  page is the weaker one.

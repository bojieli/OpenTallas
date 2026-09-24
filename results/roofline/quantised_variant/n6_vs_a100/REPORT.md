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
| Qwen3-8B | PRIMARY (BF16, 16.00 bits) | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 4,890 | 8,223.7 | 1,681.7 | 1 | `a100_sxm_80gb-x6-tensor` | 386.4 | 21.28x |
| Qwen3-8B | variant (4.25 bits, both sides) | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 10,140.7 | 4,147.5 | 1 | `a100_sxm_80gb-x3-tensor` | 501.9 | 20.20x |

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

**Recommended: `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill`** -- 3 x 815 mm2 reticle dies, 2,445 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `rom`.

- **10,140.7 tok/s per user** (0.10 ms/token), binding on `layer_fixed_latency`
- **4,147.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 10,141 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 249 W at 0.102 W/mm2, 24.5 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 3 copies of one unified HBM die -- `a100_sxm_80gb-x3-tensor`, 2,478 mm2, area ratio 0.9867 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 2,445 | 2,478 | 0.9867 |
| user tok/s | 10,140.7 | 501.9 | 20.20x |
| aggregate tok/s | 10,141 | 502 | 12.64x |
| resident sessions | 1 | 175 | -- |
| J/token | 0.0245 | 1.4132 | 57.6x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 175 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x8-tensor` at 6,608 mm2 and 749.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 11,401.6 | 3,497.4 | 1 | 19.72x |
| rank on per-user rate alone | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 11,712.7 | 1,796.4 | 1 | 15.63x |
| smallest feasible machine | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 10,140.7 | 4,147.5 | 1 | 20.20x |
| **after -- this report's rule** | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 10,140.7 | 4,147.5 | 1 | 20.20x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 10,140.7 | 4,147.5 | -- | 4,147.5 | ACCEPT |
| `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 11,401.6 | 3,497.4 | 1,547.1 | 4,147.5 | stop |
| `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 11,712.7 | 1,796.4 | 385.8 | 4,147.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` **<-- recommended** | 2,445 | 3 | 10,140.7 | 10,141 | 4,147.5 | 1 | `layer_fixed_latency` | 249 | 24.5 | `a100_sxm_80gb-x3-tensor` | 20.20x |
| `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 4 | 11,401.6 | 11,402 | 3,497.4 | 1 | `layer_fixed_latency` | 328 | 28.8 | `a100_sxm_80gb-x4-tensor` | 19.72x |
| `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 8 | 11,712.7 | 11,713 | 1,796.4 | 1 | `layer_fixed_latency` | 623 | 53.2 | `a100_sxm_80gb-x8-tensor` | 15.63x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 227 | densest | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 10,140.7 | 4,147.5 | 1 |
| array | 227 | fastest | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 11,712.7 | 1,796.4 | 1 |
| array | 227 | smallest | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 10,140.7 | 4,147.5 | 1 |
| wafer | 52 | densest | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,879.7 | 105.6 | 1 |
| wafer | 52 | fastest | `ROM-N6-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,014.9 | 54.2 | 1 |
| wafer | 52 | smallest | `ROM-N6-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,879.7 | 105.6 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 11,712.7 | 11,713 | 1 | 623 | 53.2 | `layer_fixed_latency` | `a100_sxm_80gb-x8-tensor` | 749.4 | 473 | 2,091.5 | 0.987 | 15.63x | 39.3x |
| 1 | wafer | `ROM-N6-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,014.9 | 5,015 | 1 | 8,300 | 1,655.0 | `link_latency` | `a100_sxm_80gb-x112-hybrid` | 731.5 | 6,672 | 22,657.6 | 0.999 | 6.86x | 13.7x |
| 1 | array @ wafer area | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 7,794.7 | 31,179 | 6,735 | 14,245 | 1,441.0 | `layer_fixed_latency` | `a100_sxm_80gb-x111-hybrid` | 729.6 | 6,612 | 22,517.4 | 1.004 | 10.68x | 15.6x |
| 1 | wafer reference | `ROM-N6-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,014.9 | -- | 1 | -- | 1,655.0 | -- | -- | -- | -- | -- | 0.996 | 0.64x wafer/array | -- |
| 2 | array | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 7,874.5 | 70,870 | 16,450 | 34,112 | 1,715.1 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 707.1 | 16,208 | 28,320.9 | 1.001 | 11.14x | 16.5x |
| 2 | wafer | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,553.8 | 28,431 | 4,100 | 38,048 | 4,966.6 | `link_latency` | `a100_sxm_80gb-x448-hybrid` | 704.7 | 26,699 | 46,442.6 | 0.999 | 5.04x | 9.4x |
| 4 | array | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 7,874.5 | 70,870 | 16,450 | 34,112 | 922.0 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 707.1 | 16,208 | 14,435.5 | 1.001 | 11.14x | 15.7x |
| 4 | wafer | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,553.8 | 28,431 | 4,100 | 38,048 | 2,547.7 | `link_latency` | `a100_sxm_80gb-x448-hybrid` | 704.7 | 26,699 | 23,496.4 | 0.999 | 5.04x | 9.2x |
| 8 | array | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 7,874.5 | 70,870 | 16,450 | 34,112 | 525.4 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 707.1 | 16,208 | 7,492.9 | 1.001 | 11.14x | 14.3x |
| 8 | wafer | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,553.8 | 28,431 | 4,100 | 38,048 | 1,338.3 | `link_latency` | `a100_sxm_80gb-x448-hybrid` | 704.7 | 26,699 | 12,023.3 | 0.999 | 5.04x | 9.0x |
| 16 | array | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 7,510.6 | 135,191 | 16,450 | 42,398 | 336.7 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 707.1 | 16,208 | 4,021.5 | 1.001 | 10.62x | 11.9x |
| 16 | wafer | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,163.6 | 69,599 | 6,151 | 60,544 | 1,147.8 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 704.7 | 40,050 | 9,155.0 | 0.999 | 4.49x | 8.0x |
| 32 | array | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,021.8 | 192,697 | 20,265 | 55,524 | 288.1 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 704.1 | 19,963 | 2,696.8 | 1.001 | 8.55x | 9.4x |
| 32 | wafer | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,525.5 | 80,817 | 6,151 | 61,957 | 766.6 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 704.7 | 40,050 | 4,852.6 | 0.999 | 3.58x | 6.3x |
| 64 | array | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 4,434.2 | 283,791 | 20,265 | 67,218 | 236.9 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 676.7 | 19,963 | 1,521.8 | 1.001 | 6.55x | 6.4x |
| 64 | wafer | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,680.2 | 107,533 | 6,151 | 65,387 | 608.1 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 704.7 | 40,050 | 2,701.4 | 0.999 | 2.38x | 4.4x |
| 256 | array | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 1,589.6 | 406,930 | 20,265 | 83,026 | 204.0 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 504.8 | 19,963 | 571.2 | 1.001 | 3.15x | 2.8x |
| 256 | wafer | `ROM-N6-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 524.5 | 134,268 | 6,151 | 68,819 | 512.5 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 608.4 | 40,050 | 889.2 | 0.999 | 0.86x | 1.7x |
| 1024 | array | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 430.2 | 440,475 | 20,265 | 87,151 | 197.9 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 250.4 | 19,963 | 333.5 | 1.001 | 1.72x | 1.7x |
| 1024 | wafer | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 136.6 | 139,885 | 6,151 | 69,540 | 497.1 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 377.7 | 40,050 | 413.1 | 0.999 | 0.36x | 0.8x |
| 4096 | array | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x340` | 277,100 | 111.0 | 454,517 | 20,265 | 102,873 | 226.3 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 89.7 | 19,963 | 267.9 | 1.001 | 1.24x | 1.2x |
| 4096 | wafer | `ROM-N6-q4p25-HBMKV-wafer-pipeline-x12` | 554,700 | 34.4 | 140,780 | 6,151 | 99,790 | 708.8 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 156.9 | 40,050 | 295.9 | 0.999 | 0.22x | 0.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | array | SRAM | 1 |
| 2-32 | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x69-romfill` | 56,235 | array | HBM | 4,112 |
| 64 | `ROM-N6-q4p25-HBMKV-array-hw-hybrid-x69` | 56,235 | array | HBM | 4,112 |
| 256-4096 | `ROM-N6-q4p25-HBMKV-array-hw-pipeline-x69` | 56,235 | array | HBM | 4,112 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Qwen3-8B | HBM | rom | 69, 86, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| Qwen3-8B | HBM | sram | 69, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| Qwen3-8B | SRAM | rom | 3, 4, 5, 6, 8, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 3, 4, 6, 8, 57, 113, 170, 227, 340 |

A wafer chosen over the array class is now compared against an array sampled at the wafer's own area and at four rungs above the array's floor; the `array @ wafer area` rows in the iso-area table above are that comparison. The curve BETWEEN rungs is still not evidence and must not be read as any.

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

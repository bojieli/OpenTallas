# SECONDARY: quantised variant of `n5_vs_b200`

> **SECONDARY -- PROJECTION, NOT A MEASUREMENT.** Both sides are re-quantised to 4.25 bits per parameter. **0 tokens have ever been produced at this precision anywhere in this program, on either backend**, and no accuracy has been measured on either side. Every figure below is `derived`. This is a projection of a machine nobody has run.

> **This is not the primary result.** The primary result is `results/roofline/n5_vs_b200/`, which prices the released checkpoint's own packing on both sides and is unchanged by anything here. No ratio on this page may be quoted without the primary ratio from the same row in the same sentence, and the columns below are laid out so that is the natural way to read it.

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
| Qwen3-8B | PRIMARY (BF16, 16.00 bits) | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 16,619.5 | 4,078.4 | 1 | `b200_sxm-x3-tensor` | 978.7 | 16.98x |
| Qwen3-8B | variant (4.25 bits, both sides) | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 22,797.1 | 13,986.0 | 1 | `b200_sxm-x1` | 1,180.6 | 19.31x |

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

**Recommended: `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2`** -- 2 x 815 mm2 reticle dies, 1,630 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **22,797.1 tok/s per user** (0.04 ms/token), binding on `weight_read`
- **13,986.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 22,797 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 258 W at 0.158 W/mm2, 11.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 1 copies of one unified HBM die -- `b200_sxm-x1`, 1,600 mm2, area ratio 1.0188 -- running the `none` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 1,630 | 1,600 | 1.0188 |
| user tok/s | 22,797.1 | 1,180.6 | 19.31x |
| aggregate tok/s | 22,797 | 1,181 | 19.31x |
| resident sessions | 1 | 130 | -- |
| J/token | 0.0113 | 0.8470 | 74.8x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 130 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x58-nvl72-tensor` at 92,800 mm2 and 5,116.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 40,683.1 | 12,479.5 | 1 | 23.76x |
| rank on per-user rate alone | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 40,683.1 | 12,479.5 | 1 | 23.76x |
| smallest feasible machine | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 22,797.1 | 13,986.0 | 1 | 19.31x |
| **after -- this report's rule** | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 22,797.1 | 13,986.0 | 1 | 19.31x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 22,797.1 | 13,986.0 | -- | 13,986.0 | ACCEPT |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 32,408.3 | 13,254.9 | 11,792.8 | 13,986.0 | stop |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 40,683.1 | 12,479.5 | 10,973.0 | 13,986.0 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` **<-- recommended** | 1,630 | 2 | 22,797.1 | 22,797 | 13,986.0 | 1 | `weight_read` | 258 | 11.3 | `b200_sxm-x1` | 19.31x |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 3 | 32,408.3 | 32,408 | 13,254.9 | 1 | `compute` | 362 | 11.2 | `b200_sxm-x2-tensor` | 18.93x |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 4 | 40,683.1 | 40,683 | 12,479.5 | 1 | `compute` | 475 | 11.7 | `b200_sxm-x2-tensor` | 23.76x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 249 | densest | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 22,797.1 | 13,986.0 | 1 |
| array | 249 | fastest | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 40,683.1 | 12,479.5 | 1 |
| array | 249 | smallest | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 22,797.1 | 13,986.0 | 1 |
| wafer | 58 | densest | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 58 | fastest | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 58 | smallest | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 40,683.1 | 40,683 | 1 | 475 | 11.7 | `compute` | `b200_sxm-x2-tensor` | 1,712.2 | 264 | 959.5 | 1.019 | 23.76x | 82.1x |
| 1 | wafer | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 6,464 | 1 | 3,965 | 613.4 | `link_latency` | `b200_sxm-x29-nvl72-tensor` | 4,776.9 | 3,885 | 2,677.7 | 0.996 | 1.35x | 4.4x |
| 1 | array @ wafer area | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x57-romfill` | 46,455 | 16,061.3 | 16,061 | 4,777 | 7,042 | 438.4 | `link_latency` | `b200_sxm-x29-nvl72-tensor` | 4,776.9 | 3,885 | 2,677.7 | 1.001 | 3.36x | 6.1x |
| 1 | wafer reference | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | -- | 1 | -- | 613.4 | -- | -- | -- | -- | -- | 1.005 | 0.40x wafer/array | -- |
| 2 | array | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x62-romfill` | 50,530 | 14,725.8 | 29,452 | 5,196 | 9,185 | 311.9 | `link_latency` | `b200_sxm-x32-nvl72-tensor` | 4,662.6 | 4,287 | 1,541.4 | 0.987 | 3.16x | 4.9x |
| 2 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 5,536.7 | 33,220 | 4,325 | 28,879 | 2,350.3 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 5,001.5 | 23,197 | 6,610.9 | 1.002 | 1.11x | 2.8x |
| 2 | array @ wafer area | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,944.2 | 845,256 | 28,498 | 138,550 | 1,620.3 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 5,001.5 | 23,197 | 6,610.9 | 1.001 | 1.99x | 4.1x |
| 2 | wafer reference | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 5,536.7 | -- | 4,325 | -- | 2,350.3 | -- | -- | -- | -- | -- | 0.999 | 0.56x wafer/array | -- |
| 4 | array | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x62-romfill` | 50,530 | 12,494.2 | 49,977 | 5,196 | 11,801 | 236.1 | `link_latency` | `b200_sxm-x32-nvl72-tensor` | 4,349.1 | 4,287 | 877.8 | 0.987 | 2.87x | 3.7x |
| 4 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 5,536.7 | 33,220 | 4,325 | 28,879 | 1,239.6 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 4,956.1 | 23,197 | 3,502.7 | 1.002 | 1.12x | 2.8x |
| 4 | array @ wafer area | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,944.2 | 845,256 | 28,498 | 138,550 | 874.6 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 4,956.1 | 23,197 | 3,502.7 | 1.001 | 2.01x | 4.0x |
| 4 | wafer reference | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 5,536.7 | -- | 4,325 | -- | 1,239.6 | -- | -- | -- | -- | -- | 0.999 | 0.56x wafer/array | -- |
| 8 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 159,740 | 9,944.2 | 487,265 | 16,428 | 79,870 | 343.8 | `thermal` | `b200_sxm-x100-nvl72-hybrid` | 4,600.2 | 13,407 | 1,185.5 | 0.998 | 2.16x | 3.4x |
| 8 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,530.5 | 44,244 | 5,766 | 38,499 | 870.1 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 4,813.0 | 30,975 | 2,441.3 | 1.001 | 1.15x | 2.8x |
| 16 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 159,740 | 9,944.2 | 487,265 | 16,428 | 79,870 | 236.3 | `thermal` | `b200_sxm-x100-nvl72-hybrid` | 4,154.4 | 13,407 | 707.6 | 0.998 | 2.39x | 3.0x |
| 16 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,187.1 | 82,993 | 8,650 | 59,864 | 721.3 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 4,682.1 | 46,532 | 1,882.9 | 0.999 | 1.11x | 2.6x |
| 32 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x196-romfill` | 159,740 | 9,944.2 | 487,265 | 16,428 | 79,870 | 182.6 | `thermal` | `b200_sxm-x100-nvl72-hybrid` | 3,480.0 | 13,407 | 468.7 | 0.998 | 2.86x | 2.6x |
| 32 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,183.1 | 133,861 | 8,650 | 66,338 | 495.6 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 4,338.9 | 46,532 | 1,069.4 | 0.999 | 0.96x | 2.2x |
| 64 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,944.2 | 845,256 | 28,498 | 138,550 | 175.4 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 3,207.6 | 23,197 | 442.7 | 1.001 | 3.10x | 2.5x |
| 64 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,015.8 | 193,009 | 8,650 | 73,867 | 382.7 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 3,784.0 | 46,532 | 662.7 | 0.999 | 0.80x | 1.7x |
| 256 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,323.3 | 850,754 | 28,498 | 138,550 | 162.9 | `thermal` | `b200_sxm-x173-hybrid` | 1,569.6 | 23,197 | 314.8 | 1.001 | 2.12x | 1.8x |
| 256 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 554,700 | 1,127.6 | 288,677 | 8,650 | 118,663 | 411.1 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 2,141.1 | 46,532 | 357.7 | 0.999 | 0.53x | 0.9x |
| 1024 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 832.8 | 852,822 | 28,498 | 138,550 | 162.5 | `thermal` | `b200_sxm-x173-hybrid` | 607.9 | 23,197 | 234.0 | 1.001 | 1.37x | 1.4x |
| 1024 | wafer | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 336.6 | 344,659 | 8,650 | 93,454 | 271.1 | `kv_read` | `b200_sxm-x347-hybrid` | 949.7 | 46,532 | 270.8 | 0.999 | 0.35x | 1.0x |
| 4096 | array | `ROM-N5-q4p25-HBMKV-array-hybrid-x340-romfill` | 277,100 | 208.4 | 853,426 | 28,498 | 138,550 | 162.3 | `thermal` | `b200_sxm-x173-pipeline` | 188.7 | 23,197 | 223.9 | 1.001 | 1.10x | 1.3x |
| 4096 | wafer | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 84.4 | 345,636 | 8,650 | 93,365 | 270.1 | `kv_read` | `b200_sxm-x347-pipeline` | 336.8 | 46,532 | 251.5 | 0.999 | 0.25x | 0.8x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | array | SRAM | 1 |
| 2-4 | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x49-romfill` | 39,935 | array | HBM | 4,107 |
| 8-64 | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x51-romfill` | 41,565 | array | HBM | 4,274 |
| 256 | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x62-romfill` | 50,530 | array | HBM | 5,196 |
| 1024-4096 | `ROM-N5-q4p25-HBMKV-array-hw-tensor-x74-romfill` | 60,310 | array | HBM | 6,202 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Qwen3-8B | HBM | rom | 49, 50, 51, 57, 62, 74, 98, 113, 147, 170, 196, 227, 340 |
| Qwen3-8B | HBM | sram | 49, 57, 62, 74, 98, 113, 147, 170, 196, 227, 340 |
| Qwen3-8B | SRAM | rom | 3, 4, 5, 6, 8, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 2, 3, 4, 6, 8, 57, 113, 170, 227, 340 |

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

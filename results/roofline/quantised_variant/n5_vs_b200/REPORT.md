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
| Qwen3-8B | PRIMARY (BF16, 16.00 bits) | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 9,332.7 | 2,290.2 | 1 | `b200_sxm-x3-tensor` | 631.1 | 14.79x |
| Qwen3-8B | variant (4.25 bits, both sides) | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 9,334.5 | 5,726.7 | 1 | `b200_sxm-x1` | 773.4 | 12.07x |

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

- **9,334.5 tok/s per user** (0.11 ms/token), binding on `layer_fixed_latency`
- **5,726.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 9,334 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 187 W at 0.115 W/mm2, 20.1 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 1 copies of one unified HBM die -- `b200_sxm-x1`, 1,600 mm2, area ratio 1.0188 -- running the `none` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 1,630 | 1,600 | 1.0188 |
| user tok/s | 9,334.5 | 773.4 | 12.07x |
| aggregate tok/s | 9,334 | 773 | 12.07x |
| resident sessions | 1 | 130 | -- |
| J/token | 0.0201 | 1.0033 | 50.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 130 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x58-nvl72-tensor` at 92,800 mm2 and 1,318.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 12,166.3 | 3,732.0 | 1 | 13.95x |
| rank on per-user rate alone | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 12,166.3 | 3,732.0 | 1 | 13.95x |
| smallest feasible machine | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 9,334.5 | 5,726.7 | 1 | 12.07x |
| **after -- this report's rule** | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 9,334.5 | 5,726.7 | 1 | 12.07x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 9,334.5 | 5,726.7 | -- | 5,726.7 | ACCEPT |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 11,091.5 | 4,536.4 | 2,155.9 | 5,726.7 | stop |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 12,166.3 | 3,732.0 | 1,737.3 | 5,726.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` **<-- recommended** | 1,630 | 2 | 9,334.5 | 9,334 | 5,726.7 | 1 | `layer_fixed_latency` | 187 | 20.1 | `b200_sxm-x1` | 12.07x |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x3-romfill` | 2,445 | 3 | 11,091.5 | 11,092 | 4,536.4 | 1 | `layer_fixed_latency` | 250 | 22.5 | `b200_sxm-x2-tensor` | 12.72x |
| `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 4 | 12,166.3 | 12,166 | 3,732.0 | 1 | `layer_fixed_latency` | 325 | 26.7 | `b200_sxm-x2-tensor` | 13.95x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 237 | densest | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 9,334.5 | 5,726.7 | 1 |
| array | 237 | fastest | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 12,166.3 | 3,732.0 | 1 |
| array | 237 | smallest | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | 9,334.5 | 5,726.7 | 1 |
| wafer | 58 | densest | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,874.6 | 105.5 | 1 |
| wafer | 58 | fastest | `ROM-N5-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,002.6 | 54.1 | 1 |
| wafer | 58 | smallest | `ROM-N5-q4p25-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,874.6 | 105.5 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x4-romfill` | 3,260 | 12,166.3 | 12,166 | 1 | 325 | 26.7 | `layer_fixed_latency` | `b200_sxm-x2-tensor` | 872.0 | 264 | 1,353.9 | 1.019 | 13.95x | 50.6x |
| 1 | wafer | `ROM-N5-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,002.6 | 5,003 | 1 | 7,906 | 1,580.3 | `link_latency` | `b200_sxm-x58-nvl72-tensor` | 1,318.4 | 7,774 | 15,966.9 | 0.996 | 3.79x | 10.1x |
| 1 | array @ wafer area | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 9,407.7 | 75,262 | 9,471 | 19,554 | 1,176.8 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,318.4 | 7,774 | 15,966.9 | 0.992 | 7.14x | 13.6x |
| 1 | wafer reference | `ROM-N5-q4p25-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,002.6 | -- | 1 | -- | 1,580.3 | -- | -- | -- | -- | -- | 0.996 | 0.53x wafer/array | -- |
| 2 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 50,530 | 9,598.9 | 38,396 | 5,196 | 10,355 | 410.6 | `layer_fixed_latency` | `b200_sxm-x32-nvl72-tensor` | 1,285.1 | 4,287 | 4,701.8 | 0.987 | 7.47x | 11.5x |
| 2 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,482.5 | 49,308 | 4,325 | 30,951 | 2,872.7 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,307.2 | 23,197 | 23,739.4 | 1.002 | 3.43x | 8.3x |
| 2 | array @ wafer area | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,402.4 | 206,852 | 28,498 | 56,310 | 1,706.3 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,307.2 | 23,197 | 23,739.4 | 1.001 | 7.19x | 13.9x |
| 2 | wafer reference | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,482.5 | -- | 4,325 | -- | 2,872.7 | -- | -- | -- | -- | -- | 0.999 | 0.48x wafer/array | -- |
| 4 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x62-romfill` | 50,530 | 9,598.9 | 38,396 | 5,196 | 10,355 | 269.7 | `layer_fixed_latency` | `b200_sxm-x32-nvl72-tensor` | 1,258.1 | 4,287 | 2,461.6 | 0.987 | 7.63x | 9.1x |
| 4 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,482.5 | 49,308 | 4,325 | 30,951 | 1,500.8 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,303.7 | 23,197 | 12,070.2 | 1.002 | 3.44x | 8.0x |
| 4 | array @ wafer area | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,402.4 | 206,852 | 28,498 | 56,310 | 917.5 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,303.7 | 23,197 | 12,070.2 | 1.001 | 7.21x | 13.2x |
| 4 | wafer reference | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,482.5 | -- | 4,325 | -- | 1,500.8 | -- | -- | -- | -- | -- | 0.999 | 0.48x wafer/array | -- |
| 8 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 9,518.8 | 104,706 | 14,249 | 28,320 | 323.6 | `layer_fixed_latency` | `b200_sxm-x87-nvl72-hybrid` | 1,268.3 | 11,664 | 3,238.0 | 0.995 | 7.51x | 10.0x |
| 8 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,482.5 | 49,308 | 4,325 | 30,951 | 814.8 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,289.9 | 23,197 | 6,160.9 | 1.002 | 3.47x | 7.6x |
| 8 | array @ wafer area | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,402.4 | 206,852 | 28,498 | 56,310 | 523.2 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,289.9 | 23,197 | 6,160.9 | 1.001 | 7.29x | 11.8x |
| 8 | wafer reference | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,482.5 | -- | 4,325 | -- | 814.8 | -- | -- | -- | -- | -- | 0.999 | 0.48x wafer/array | -- |
| 16 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,402.4 | 206,852 | 28,498 | 56,310 | 326.0 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,263.3 | 23,197 | 3,206.3 | 1.001 | 7.44x | 9.8x |
| 16 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,459.3 | 98,105 | 8,650 | 61,837 | 818.4 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,282.0 | 46,532 | 6,188.2 | 0.999 | 3.48x | 7.6x |
| 32 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 8,579.9 | 368,938 | 28,498 | 77,190 | 236.9 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,214.9 | 23,197 | 1,766.3 | 1.001 | 7.06x | 7.5x |
| 32 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,878.2 | 166,764 | 8,650 | 70,681 | 525.3 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 1,251.5 | 46,532 | 3,230.0 | 0.999 | 3.10x | 6.1x |
| 64 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,926.4 | 588,747 | 28,498 | 105,506 | 195.7 | `kv_read` | `b200_sxm-x173-nvl72-hybrid` | 1,145.4 | 23,197 | 994.2 | 1.001 | 6.05x | 5.1x |
| 64 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,053.5 | 195,423 | 8,650 | 74,293 | 380.2 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 1,199.0 | 46,532 | 1,784.9 | 0.999 | 2.55x | 4.7x |
| 256 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,281.0 | 839,931 | 28,498 | 137,512 | 163.7 | `kv_read` | `b200_sxm-x173-nvl72-hybrid` | 877.5 | 23,197 | 415.6 | 1.001 | 3.74x | 2.5x |
| 256 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,199.2 | 306,988 | 8,650 | 88,618 | 288.7 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 1,010.0 | 46,532 | 634.2 | 0.999 | 1.19x | 2.2x |
| 1024 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 832.2 | 852,132 | 28,498 | 138,550 | 162.6 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 480.0 | 23,197 | 260.0 | 1.001 | 1.73x | 1.6x |
| 1024 | wafer | `ROM-N5-q4p25-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 330.8 | 338,720 | 8,650 | 92,691 | 273.7 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 671.6 | 46,532 | 322.6 | 0.999 | 0.49x | 1.2x |
| 4096 | array | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 208.3 | 853,168 | 28,498 | 138,550 | 162.4 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 179.0 | 23,197 | 214.8 | 1.001 | 1.16x | 1.3x |
| 4096 | wafer | `ROM-N5-q4p25-HBMKV-wafer-hybrid-x12` | 554,700 | 83.9 | 343,451 | 8,650 | 125,652 | 365.8 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 306.9 | 46,532 | 233.3 | 0.999 | 0.27x | 0.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-q4p25-SRAMKV-array-hw-tensor-x2` | 1,630 | array | SRAM | 1 |
| 2-4096 | `ROM-N5-q4p25-HBMKV-array-hw-hybrid-x49-romfill` | 39,935 | array | HBM | 4,107 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Qwen3-8B | HBM | rom | 49, 57, 62, 74, 98, 113, 147, 170, 196, 227, 340 |
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

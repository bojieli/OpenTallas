# Area-constrained roofline: n5_vs_b200-pro-32k

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Pro-0813 at 32,768 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 10x (ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream, 114 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 193 devices. On the GPU side the correction reaches 5x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 29 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Pro-0813 takes 156 x 815 mm2 (127,140 mm2, array, KV in SRAM) at 1,589 tok/s per user and 12 tok/s per 1,000 mm2, holding 1 session, against 79 copies of one unified HBM die at the same silicon: 3.9x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 251,020 mm2 of ROM silicon at 1,891 tok/s per user against 251,200 mm2 of b200_sxm-x157-nvl72-hybrid at 417 tok/s: **4.5x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 94,301 resident sessions against the GPU cluster's 74,211. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 3.05x to it.** At 231,125 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 138.48 tok/s and the same silicon running hybrid delivers 422 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`) to 8.09x (DeepSeek-V4-Pro-0813, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Pro-0813 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 116 to 18,934 tok/s, and its rate with every slot occupied from 18,399 to 18,934. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 158 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 896 us over NVLink, capping per-user decode at 1,116 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 262.3 us and cap it at 3,813 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 3 of 10 operating points and an array 7; on tokens per second per square millimetre the same points go 7 to the array and 3 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 24 of 4388 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 61.2x of aggregate throughput (DeepSeek-V4-Pro-0813). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 16.33x, on DeepSeek-V4-Pro-0813 at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 59 of 4,388 feasible points (1.3%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DSV4-Pro/b200_sxm-x14-pipeline` at batch 4096 on 22,400 mm2, throttled 1.07x from 7 to 7 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 94% weight read against 94.0% weight read. The ROM sweep is not what melts it.


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

### DeepSeek-V4-Pro-0813 at 32,768 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-hybrid-x156`** -- 156 x 815 mm2 reticle dies, 127,140 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **1,588.7 tok/s per user** (0.63 ms/token), binding on `layer_fixed_latency`
- **12.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 1,589 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 7,827 W at 0.062 W/mm2, 4,927.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 79 copies of one unified HBM die -- `b200_sxm-x79-nvl72-hybrid`, 126,400 mm2, area ratio 1.0059 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 127,140 | 126,400 | 1.0059 |
| user tok/s | 1,588.7 | 411.6 | 3.86x |
| aggregate tok/s | 1,589 | 823 | 0.15x |
| resident sessions | 1 | 36,000 | -- |
| J/token | 4.9270 | 71.4530 | 14.5x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 36,000 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x144-nvl72-hybrid` at 230,400 mm2 and 422.2 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-array-hw-hybrid-x193` | 157,295 | 1,817.4 | 11.6 | 59,091 | 4.37x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 8.7 | 82,054 | 4.49x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-hybrid-x146` | 118,990 | 1,124.5 | 9.5 | 1 | 2.74x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` | 127,140 | 1,588.7 | 12.5 | 1 | 3.86x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` | 127,140 | 1,588.7 | 12.5 | -- | 12.5 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x176` | 143,440 | 1,772.5 | 12.4 | 11.3 | 12.5 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x180` | 146,700 | 1,775.5 | 12.1 | 9.6 | 12.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x193` | 157,295 | 1,817.4 | 11.6 | 7.6 | 12.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x198` | 161,370 | 1,826.0 | 11.3 | 6.9 | 12.5 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x215` | 175,225 | 1,826.3 | 10.4 | 4.9 | 12.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 1,845.1 | 10.0 | 4.4 | 12.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x231` | 188,265 | 1,847.6 | 9.8 | 4.2 | 12.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x238` | 193,970 | 1,876.7 | 9.7 | 4.3 | 12.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x260-romfill` | 211,900 | 1,883.9 | 8.9 | 3.5 | 12.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 8.7 | 3.3 | 12.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` **<-- recommended** | 127,140 | 156 | 1,588.7 | 1,589 | 12.5 | 1 | `layer_fixed_latency` | 7,827 | 4,927.0 | `b200_sxm-x79-nvl72-hybrid` | 3.86x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x176` | 143,440 | 176 | 1,772.5 | 1,772 | 12.4 | 1 | `layer_fixed_latency` | 8,869 | 5,003.6 | `b200_sxm-x90-nvl72-hybrid` | 4.28x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x180` | 146,700 | 180 | 1,775.5 | 1,776 | 12.1 | 1 | `layer_fixed_latency` | 9,342 | 5,261.3 | `b200_sxm-x92-nvl72-hybrid` | 4.28x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x193` | 157,295 | 193 | 1,817.4 | 23,627 | 11.6 | 59,091 | `layer_fixed_latency` | 14,234 | 7,489.6 | `b200_sxm-x98-nvl72-hybrid` | 4.37x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x198` | 161,370 | 198 | 1,826.0 | 23,738 | 11.3 | 60,622 | `layer_fixed_latency` | 14,898 | 7,816.7 | `b200_sxm-x101-nvl72-hybrid` | 4.38x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x215` | 175,225 | 215 | 1,826.3 | 1,826 | 10.4 | 1 | `layer_fixed_latency` | 13,479 | 7,380.1 | `b200_sxm-x110-nvl72-hybrid` | 4.36x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 227 | 1,845.1 | 27,676 | 10.0 | 69,501 | `layer_fixed_latency` | 18,844 | 9,813.4 | `b200_sxm-x116-nvl72-hybrid` | 4.40x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x231` | 188,265 | 231 | 1,847.6 | 27,714 | 9.8 | 70,726 | `layer_fixed_latency` | 19,374 | 10,086.5 | `b200_sxm-x118-nvl72-hybrid` | 4.40x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x238` | 193,970 | 238 | 1,876.7 | 28,151 | 9.7 | 72,869 | `layer_fixed_latency` | 20,311 | 10,423.2 | `b200_sxm-x121-nvl72-hybrid` | 4.47x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x260-romfill` | 211,900 | 260 | 1,883.9 | 122,453 | 8.9 | 79,605 | `layer_fixed_latency` | 25,910 | 11,927.2 | `b200_sxm-x132-nvl72-hybrid` | 4.47x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 268 | 1,892.4 | 126,790 | 8.7 | 82,054 | `layer_fixed_latency` | 27,091 | 12,432.6 | `b200_sxm-x137-nvl72-hybrid` | 4.49x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 264 | densest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` | 127,140 | 1,588.7 | 12.5 | 1 |
| array | 264 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 8.7 | 82,054 |
| array | 264 | smallest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x146` | 118,990 | 1,124.5 | 9.5 | 1 |
| wafer | 66 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,492.0 | 10.8 | 1 |
| wafer | 66 | fastest | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 1,733.1 | 7.5 | 13,165 |
| wafer | 66 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,492.0 | 10.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 126,790 | 82,054 | 27,091 | 12,432.6 | `layer_fixed_latency` | `b200_sxm-x137-nvl72-hybrid` | 421.6 | 64,413 | 118,074.8 | 0.996 | 4.49x | 9.5x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 1,733.1 | 123,048 | 13,165 | 24,011 | 11,857.0 | `layer_fixed_latency` | `b200_sxm-x144-nvl72-hybrid` | 422.2 | 67,842 | 123,702.6 | 1.003 | 4.10x | 10.4x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x286` | 233,090 | 1,792.5 | 1,793 | 1 | 21,868 | 12,199.9 | `layer_fixed_latency` | `b200_sxm-x146-nvl72-hybrid` | 415.6 | 68,822 | 127,301.0 | 0.998 | 4.31x | 10.4x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 1,733.1 | -- | 13,165 | -- | 11,857.0 | -- | -- | -- | -- | -- | 1.009 | 0.97x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 126,790 | 82,054 | 27,091 | 6,230.6 | `layer_fixed_latency` | `b200_sxm-x137-nvl72-hybrid` | 421.6 | 64,413 | 61,131.4 | 0.996 | 4.49x | 9.8x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 1,733.1 | 123,048 | 13,165 | 24,011 | 5,942.7 | `layer_fixed_latency` | `b200_sxm-x144-nvl72-hybrid` | 422.2 | 67,842 | 63,945.3 | 1.003 | 4.10x | 10.8x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 126,790 | 82,054 | 27,091 | 3,129.6 | `layer_fixed_latency` | `b200_sxm-x137-nvl72-hybrid` | 408.3 | 64,413 | 32,875.7 | 0.996 | 4.63x | 10.5x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 1,733.1 | 123,048 | 13,165 | 24,011 | 2,985.6 | `layer_fixed_latency` | `b200_sxm-x144-nvl72-hybrid` | 409.4 | 67,842 | 34,294.7 | 1.003 | 4.23x | 11.5x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 126,790 | 82,054 | 27,091 | 1,579.0 | `layer_fixed_latency` | `b200_sxm-x137-nvl72-hybrid` | 399.1 | 64,413 | 19,226.6 | 0.996 | 4.74x | 12.2x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 1,733.1 | 123,048 | 13,165 | 24,011 | 1,507.1 | `layer_fixed_latency` | `b200_sxm-x144-nvl72-hybrid` | 402.0 | 67,842 | 19,880.8 | 1.003 | 4.31x | 13.2x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 126,790 | 82,054 | 27,091 | 803.8 | `layer_fixed_latency` | `b200_sxm-x137-nvl72-hybrid` | 378.9 | 64,413 | 10,864.7 | 0.996 | 4.99x | 13.5x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 1,733.1 | 123,048 | 13,165 | 24,011 | 767.8 | `layer_fixed_latency` | `b200_sxm-x144-nvl72-hybrid` | 382.2 | 67,842 | 11,197.9 | 1.003 | 4.53x | 14.6x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 126,790 | 82,054 | 27,091 | 416.2 | `layer_fixed_latency` | `b200_sxm-x137-nvl72-hybrid` | 340.3 | 64,413 | 6,543.8 | 0.996 | 5.56x | 15.7x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 1,733.1 | 123,048 | 13,165 | 24,011 | 398.2 | `layer_fixed_latency` | `b200_sxm-x144-nvl72-hybrid` | 344.1 | 67,842 | 6,717.4 | 1.003 | 5.04x | 16.9x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x268` | 218,420 | 1,892.4 | 126,790 | 82,054 | 27,091 | 222.4 | `layer_fixed_latency` | `b200_sxm-x137-nvl72-hybrid` | 284.0 | 64,413 | 4,343.9 | 0.996 | 6.66x | 19.5x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 1,733.1 | 123,048 | 13,165 | 24,011 | 213.4 | `layer_fixed_latency` | `b200_sxm-x144-nvl72-hybrid` | 288.3 | 67,842 | 4,437.7 | 1.003 | 6.01x | 20.8x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 1,410.4 | 361,064 | 104,099 | 42,279 | 117.1 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 177.0 | 82,049 | 2,842.1 | 1.001 | 7.97x | 24.3x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,614.8 | 550,650 | 31,597 | 64,913 | 147.5 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 237.1 | 167,288 | 3,806.6 | 0.999 | 6.81x | 25.8x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 277,100 | 662.5 | 678,425 | 104,099 | 48,540 | 71.5 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 78.3 | 82,049 | 1,799.3 | 1.001 | 8.46x | 25.1x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,012.3 | 1,036,594 | 31,597 | 75,877 | 73.2 | `compute` | `b200_sxm-x347-nvl72-hybrid` | 119.1 | 167,288 | 2,275.7 | 0.999 | 8.50x | 31.1x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 277,100 | 193.9 | 794,244 | 104,099 | 49,340 | 62.1 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 36.7 | 82,049 | 876.1 | 1.001 | 5.28x | 14.1x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 390.0 | 1,597,407 | 31,597 | 101,764 | 63.7 | `weight_read` | `b200_sxm-x347-nvl72-hybrid` | 51.7 | 167,288 | 1,336.7 | 0.999 | 7.54x | 21.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` | 127,140 | array | SRAM | 1 |
| 2-8 | `ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 138,550 | array | HBM | 52,049 |
| 16-32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x193` | 157,295 | array | HBM | 59,091 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 185,005 | array | HBM | 69,501 |
| 256 | `ROM-N5-native-HBMKV-wafer-pipeline-x4` | 184,900 | wafer | HBM | 10,532 |
| 1024 | `ROM-N5-native-HBMKV-wafer-pipeline-x6` | 277,350 | wafer | HBM | 15,798 |
| 4096 | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 369,800 | wafer | HBM | 21,064 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro-0813 | HBM | rom | 158, 162, 170, 193, 198, 227, 231, 238, 260, 308, 340 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 158, 162, 170, 193, 198, 227, 231, 238, 268, 308, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 146, 156, 170, 176, 179, 180, 196, 215, 227, 286, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 146, 156, 170, 176, 179, 180, 196, 215, 227, 286, 340 |

A wafer chosen over the array class is now compared against an array sampled at the wafer's own area and at four rungs above the array's floor; the `array @ wafer area` rows in the iso-area table above are that comparison. The curve BETWEEN rungs is still not evidence and must not be read as any.

## Serial latency and collectives

The serial part of every step is the longest path of one token's operator
dependency graph (`src/opentallas/critical_path.py`): the dependent-operator
chain priced with measured RTL depths (ROM) or a published CUDA-graph launch gap
per dependent kernel (GPU), every collective the weight split needs with its
latency and real payload, and every pipeline hop. A hybrid layout's tensor
group and every collective's reduction algorithm are searched per point.
`legacy` is the flat per-layer floor plus two all-reduces per layer this
replaced.

| Model | Design | Batch | Group | Coll./layer | Algorithms | Chain (us) | Comm. (us) | Sweep (us) | Legacy serial (us) | tok/s/user |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x156` | 1 | 32 | 6.51 | hierarchical, one_shot | 444.84 | 130.07 | 70.89 | 77.69 | 1,588.7 |
| DeepSeek-V4-Pro-0813 | `b200_sxm-x79-nvl72-hybrid` | 1 | 64 | 6.51 | measured_floor | 1,340.30 | 948.04 | 155.40 | 318.46 | 411.6 |
| DeepSeek-V4-Pro-0813 | `b200_sxm-x79-nvl72-hybrid` | 64 | 8 | 5.51 | measured_floor | 1,344.20 | 1,027.58 | 2,077.38 | 357.34 | 233.1 |

## The overlap and serialisation rule

```
t_memory  = t_weight + t_kv        weights and KV share one memory system
t_memory  = max(t_weight, t_kv)    weights and KV are separate arrays
t_service = max(t_memory, t_compute)      on the AGGREGATE machine
S         = token_slots * t_service / stage_balance      the sweep a token waits for
t_user    = max(S, longest path of the token's operator graph with S spread
                over its operators by bytes, + every pipeline hop)
t_user   *= thermal_scale

per_user_tokens_s  = 1 / t_user
aggregate_tokens_s = fill_users / t_user      fill_users = max(batch, slots)
delivered_tokens_s = batch / t_user
```

Compute overlaps memory. Weight and KV traffic **add** on a GPU because they
contend for the same HBM channels, and **overlap** on a ROM part because the
mask ROM and the KV store are physically separate arrays -- that single rule
is most of the architectural difference and it is stated rather than hidden
in an efficiency factor. Hop and collective latency is **added** to the
critical path at every batch size, because decode is sequential across
layers.

`t_service` is computed on the machine's **aggregate** resources: all of the
array bandwidth, all of the compute roof. That denominator is correct only
for partitions that are working on the same token at the same instant, which
is what tensor parallelism is. `token_slots = partitions / tensor_group` is
how many independent groups the machine is cut into, and a token is served by
exactly one of them at a time, so its latency is `token_slots` service times
long. **Under pipeline parallelism the two factors cancel exactly** -- each of
N stages holds 1/N of the weights and reads them with 1/N of the bandwidth --
so adding devices buys aggregate throughput and buys one user nothing.
Tensor parallelism is different in kind: every partition is on the same token,
`token_slots` is 1, and the price is every collective the weight split needs,
charged on the token's operator graph (see *Serial latency and collectives*).

**`aggregate = batch x per-user rate` no longer holds and its removal is the
point.** The aggregate rate is the machine's rate with every slot occupied,
which needs `token_slots` concurrent users; below that the surplus slots idle
and the machine delivers `delivered_tokens_s` instead. The fill is capped by
the users whose KV the machine can hold, reported per point as
`pipeline_fill_limited_by`. Fill and drain are not charged: decode is a
continuous stream of steps and the pipeline is taken to be in steady state,
which flatters a deep pipeline by at most one traversal per request.

Every point also carries `per_user_tokens_s_throughput_view`: the single
number this study reported for both quantities before they were separated, so
the size of this correction is separable from every other one.

## Validation gates

| Gate | Published | Modelled | Ratio | Tolerance | Result |
|---|---:|---:|---:|---:|---|
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 10,802.5 tok/s | 0.64x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 77.8 W | 0.31x | within 2x | FAIL |

HC1 binds on `layer_fixed_latency`. Its component times are weight_read 34.47 us, kv_read 3.13 us, compute 34.47 us, link_latency 0.00 us, layer_fixed_latency 59.54 us.

The model **under**-predicts the shipping part by 1.57x. Rather than tune the densities until the anchor
is hit, the gate back-derives what each input would have to be for the
model to land exactly on 17,000 tok/s:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 5.292e+11 | 3.093e+11 | 0.58x |
| Compute density (ops/s/mm2) | 1.261e+12 | 3.155e+12 | 2.50x |

The gate fails before either rate density can bind: the corrected
ROM capacity density and compute-in-ROM floorplan cannot fit the
published model in 815 mm2. The rate diagnostics remain useful --
ROM read density is 0.58x and
compute density is 2.50x
the value implied by the shipping rate -- but neither can rescue a
capacity failure. The required ROM read density remains below the SRAM
read-bandwidth density derived from Cerebras WSE-2
(5.563e+11 B/s/mm2).

### The serial-latency band, and why the gate is not fitted

The serial part of the step is the dependent-operator chain of the
Llama-3.1-8B decode graph (`src/opentallas/critical_path.py`), priced
with this repository's measured RTL depths
(`serial_latency.rom_datapath`). Nothing in it is fitted to this
anchor. Its few assumed inputs -- the clock the RTL is applied at,
the stream-unit share of the compute area, the select units, the
row-access latency -- carry ranges, and the gate is evaluated at both
ends. The flat per-layer floor this chain replaced is shown beside it.

| Serial chain | Per layer | Per token | Legacy floor per token | Modelled tok/s | Ratio | Binds on |
|---|---:|---:|---:|---:|---:|---|
| range low | 1,368.9 ns/layer | 43.81 us | 6.06 us | 13,014.5 | 0.77x | layer_fixed_latency |
| range stated | 1,860.6 ns/layer | 59.54 us | 6.06 us | 10,802.5 | 0.64x | layer_fixed_latency |
| range high | 3,206.3 ns/layer | 102.60 us | 6.06 us | 7,497.8 | 0.44x | layer_fixed_latency |

The per-layer serial cost that would land the model exactly on the
published figure is **810.3 ns/layer**. It is reported so the distance between the measured chain and the one the shipping part implies is visible. It is never used as an input: a chain longer than it means the hardwired datapath modelled here is serially slower than HC1's.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 10,783.7 | 0.64x | layer_fixed_latency |
| 3.5 | 10,802.5 | 0.64x | layer_fixed_latency |
| 4.0 | 10,783.7 | 0.64x | layer_fixed_latency |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 11,698.3 | 0.69x | layer_fixed_latency |
| 1,536 | 11,242.9 | 0.66x | layer_fixed_latency |
| 2,048 | 10,802.5 | 0.64x | layer_fixed_latency |

### The two power gates, and the residual they leave

Two gates in the shape of the two above, added because every watt this
program reported was 7-9x low against both published parts and because
`thermal_scale` was exactly 1.0 at every feasible point, so no rate
depended on the energy model at all. **Nothing was tuned to close
either of them.** Six power terms were derived from primitives and
adversarially verified; every one was sent back with a correction, and
the corrections are what is applied. Two of them move power up and two
move it down.

The A100 gate is evaluated at a **saturating** operating point --
2.039 TB/s of published HBM
bandwidth and 312 T ops/s of published
dense roof at 1,410 MHz, both at
once -- because a TDP is what a part is built to shed under load, not
what a decode step draws. The HC1 gate is evaluated at exactly the point
its throughput gate already uses, read off that gate's own step so the
two cannot drift apart.

| Gate | Published | Modelled | Ratio | Result |
|---|---:|---:|---:|---|
| A100 at TDP, saturating | 400.0 W | 461.7 W | 1.15x | PASS |
| Taalas HC1 card power | 200.0-250.0 W | 77.8 W | 0.31x | FAIL |

**Where the watts come from.**

| Term | A100 at TDP | Taalas HC1 |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 2.8 W |
| KV traffic | n/a: one saturating HBM stream | 7.5 W |
| operand delivery | 0.5 W | 8.8 W |
| arithmetic | 103.0 W | 6.3 W |
| static: leakage | 31.4 W | 20.6 W |
| static: clock distribution | 99.0 W | 31.6 W |
| static: memory-interface idle | 14.0 W | 0.0 W |
| **static charged** (max of the enumeration and the measured clocked-idle floor) | 144.4 W | 52.2 W |
| **total** | 461.7 W | 77.8 W |

On HC1 the enumerated static power is 52.2 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 57.0 W | 0.23x | 0.28x |
| stated | 461.7 W | 1.15x | 77.8 W | 0.31x | 0.39x |
| high | 698.3 W | 1.75x | 339.3 W | 1.36x | 1.70x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.31x of the top of its published band, **3.21x low**, against 2.57x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

**Why the A100 gate is the weaker of the two, and must not be quoted
as independent.** `power.clock_energy_j_per_mm2_per_cycle` was
calibrated as 20-45% of a shipping GPU's published TDP density. It is
a different GPU -- P100 and GV100 at 16FF+/12FFN, not this part -- but
it is still a GPU TDP, so adding that term to the others and comparing
the sum with a GPU's TDP is partly checking an input against its own
family. What the gate does test is that the traffic terms, the
arithmetic and the static terms are mutually consistent in size, and
it would fail loudly if any were an order of magnitude out. The HC1
gate has no such circularity: nothing on the ROM side was calibrated
on a Taalas figure, because Taalas publishes no microarchitecture and
no energy at all. **It is the stronger gate and it is the one that
fails.**

**Energy accounting at the two anchors.** Both parts serve the same workload -- Llama-3.1-8B at batch 1 -- so this is the cleanest statement the model can make about the ROM argument, and it could not be made at all until the power terms existed:

| Part | Energy | W | tok/s |
|---|---:|---:|---:|
| Taalas HC1 (modelled reconstruction) | 0.007199 J/token | 77.8 | 10,802.5 |
| A100 80GB, weight-bound gate, same model and batch | 1.537721 J/token | 336.2 | 218.6 |

That is a factor of 214 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 2.6-3.2x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

**Where the remaining HC1 shortfall could live, none of it fitted.**
The ROM array is charged its stated leakage density: 1.7 W at the point
and 6.7 W at the
top of its range. The point charge moves the enumerated static
estimate just above the measured clocked-idle floor and is therefore
included in the charged static total. `energy.rom_read_j_per_byte`
moved from 0.5 to 0.08 pJ/B on the evidence, which made this gate
**worse by about 4x on that term alone** and was adopted anyway. The
honest reading is that a compute-in-ROM part's energy has never been
published at any node, and this model's ROM side is built from macros
that are mostly simulated, at 28-130 nm, with boundaries that do not
match the term they are being asked to supply.


## Power, dark silicon and energy per token

**The thermal limit binds here, and this is the first version of this
study in which it could.**
Static power is charged per mm2 per second whether or not a byte moves,
so the coolable step time solves
`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the
total energy by the total limit. Under the old rule stretching a step
always reduced modelled power, so every design was coolable at some speed
and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across
both studies.

- **59 of 4,388 feasible points (1.3%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 59.
- By area class: large array (5,000-40,000 mm2) 3, wafer (>=40,000 mm2) 56.
- By KV store: hbm 59.
- By batch: B=256 4, B=1024 26, B=4096 29.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 39% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 256 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 60 | 3 | 54.2% | 100.0% | 0.625 | 69% |
| gpu | wafer (>=40,000 mm2) | 1,910 | 56 | 38.5% | 100.0% | 0.625 | 91% |
| rom | wafer (>=40,000 mm2) | 2,418 | 0 | 19.7% | 38.8% | 0.194 | 95% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DSV4-Pro/b200_sxm-x14-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 22,400 | hbm | 1.072x | 14,000.0 / 14,000.0 W | 35% | 6.9 | 7.4 |
| `DSV4-Pro/b200_sxm-x29-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 46,400 | hbm | 1.061x | 29,000.0 / 29,000.0 W | 35% | 7.9 | 8.4 |
| `DSV4-Pro/b200_sxm-x38-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 60,800 | hbm | 1.059x | 38,000.0 / 38,000.0 W | 35% | 8.6 | 9.1 |
| `DSV4-Pro/b200_sxm-x41-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 65,600 | hbm | 1.059x | 41,000.0 / 41,000.0 W | 35% | 8.9 | 9.4 |
| `DSV4-Pro/b200_sxm-x42-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 67,200 | hbm | 1.058x | 42,000.0 / 42,000.0 W | 35% | 9.0 | 9.5 |
| `DSV4-Pro/b200_sxm-x14-pipeline` | DeepSeek-V4-Pro-0813 | 1024 | 22,400 | hbm | 1.057x | 14,000.0 / 14,000.0 W | 35% | 10.3 | 10.9 |
| `DSV4-Pro/b200_sxm-x58-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 92,800 | hbm | 1.057x | 58,000.0 / 58,000.0 W | 35% | 10.5 | 11.1 |
| `DSV4-Pro/b200_sxm-x74-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 118,400 | hbm | 1.056x | 74,000.0 / 74,000.0 W | 35% | 12.0 | 12.7 |
| `DSV4-Pro/b200_sxm-x79-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 126,400 | hbm | 1.056x | 79,000.0 / 79,000.0 W | 35% | 12.5 | 13.2 |
| `DSV4-Pro/b200_sxm-x80-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 128,000 | hbm | 1.056x | 80,000.0 / 80,000.0 W | 35% | 12.6 | 13.3 |
| `DSV4-Pro/b200_sxm-x83-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 132,800 | hbm | 1.056x | 83,000.0 / 83,000.0 W | 35% | 12.9 | 13.6 |
| `DSV4-Pro/b200_sxm-x87-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 139,200 | hbm | 1.056x | 87,000.0 / 87,000.0 W | 35% | 13.3 | 14.0 |

The worst point's dynamic energy is weight read 94.0%, kv read 3.6%, arithmetic 2.2%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
reads its weights for almost nothing; what it still pays for, at
the same rate a GPU does, is KV traffic to DRAM. That is an
argument for keeping KV on die, and it is visible here only
because the power model now distinguishes the two.

### Energy per token, both sides, at equal area

**This number has been unpublishable until now.** Not paying DRAM
access energy for weights is much of the ROM argument, and the
model could not state it while every watt in it was 7-9x low. The
figures below include the static share amortised over the tokens
the step actually produces, so a machine that is fast and leaky is
not flattered against one that is slow and cool.

One row per (model, batch). The ROM design is the smallest silicon within 5% of the fastest per-user rate -- the same rule the report uses everywhere it says 'best' -- and the GPU beside it is the iso-area comparator that comparison already chose. Listing every comparison instead buries the answer under wafers serving one user.

| Model | B | mm2 | ROM design | ROM J/token | ROM W | ROM binds | iso-area GPU | GPU J/token | GPU W | GPU binds | ROM tokens/joule |
|---|---:|---:|---|---:|---:|---|---|---:|---:|---|---:|
| DeepSeek-V4-Pro-0813 | 1 | 157,295 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x193` | 7.489643 | 14,234.4 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x98-nvl72-hybrid` | 86.689571 | 37,829.7 | layer_fixed_latency | 11.57x |
| DeepSeek-V4-Pro-0813 | 2 | 157,295 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x193` | 3.759090 | 14,234.4 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x98-nvl72-hybrid` | 45.438743 | 37,829.7 | layer_fixed_latency | 12.09x |
| DeepSeek-V4-Pro-0813 | 4 | 157,295 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x193` | 1.893814 | 14,234.4 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x98-nvl72-hybrid` | 25.731678 | 41,019.1 | layer_fixed_latency | 13.59x |
| DeepSeek-V4-Pro-0813 | 8 | 157,295 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x193` | 0.961175 | 14,234.4 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x98-nvl72-hybrid` | 14.822960 | 46,325.3 | layer_fixed_latency | 15.42x |
| DeepSeek-V4-Pro-0813 | 16 | 185,005 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 0.642399 | 19,575.3 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x116-nvl72-hybrid` | 9.619604 | 57,071.6 | layer_fixed_latency | 14.97x |
| DeepSeek-V4-Pro-0813 | 32 | 188,265 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x231` | 0.350585 | 20,180.4 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x118-nvl72-hybrid` | 5.956781 | 62,924.1 | layer_fixed_latency | 16.99x |
| DeepSeek-V4-Pro-0813 | 64 | 193,970 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x238` | 0.196309 | 22,755.4 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x121-nvl72-hybrid` | 4.074320 | 71,248.1 | layer_fixed_latency | 20.75x |
| DeepSeek-V4-Pro-0813 | 256 | 369,800 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 0.110281 | 43,743.3 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x231-nvl72-hybrid` | 3.171077 | 164,264.6 | weight_read | 28.75x |
| DeepSeek-V4-Pro-0813 | 1024 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.073198 | 75,876.9 | compute | `DSV4-Pro/b200_sxm-x347-nvl72-hybrid` | 2.275736 | 277,629.3 | weight_read | 31.09x |
| DeepSeek-V4-Pro-0813 | 4096 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12` | 0.063706 | 101,764.4 | weight_read | `DSV4-Pro/b200_sxm-x347-nvl72-hybrid` | 1.336661 | 283,227.1 | weight_read | 20.98x |

**Read this with the power gates beside it.** The ROM side's energy
rests on `energy.rom_read_j_per_byte`, which is `assumed` over a
17x-wide bracket, and on an operand-delivery scalar that is the
tile-local floor with no long-path ladder in it. The HC1 power gate
says the ROM side's total is several times below a shipping part's
published card power, so **every ROM joule-per-token here is a
lower bound and should be quoted as one.** The GPU side rests on
a measured, peer-reviewed HBM figure and on a gate that lands
within a few percent of a published TDP, so the two sides are not
equally well founded and the ratio inherits the weaker of them.

**A dense model gives the energy advantage back as batch rises and
a sparse one does not.** A GPU amortises one weight read over the
whole batch, so its joules per token fall roughly as 1/batch until
KV takes over; the ROM part's weight read was already nearly free,
so it has nothing to amortise. On a sparse model the GPU cannot
amortise -- batching engages more experts -- so the ROM advantage
grows instead. Quoting a dense model's batch-1 number without its
batch-256 number beside it is quoting the best case as the case.


## Derived technology at N5

These are outputs of the graded primitives, not inputs.

| Quantity | Value | Grade |
|---|---:|---|
| SRAM capacity density | 3.869 MB/mm2 | assumed |
| ROM capacity density | 9.380 MB/mm2 | derived |
| ROM read bandwidth density | 362.9 GB/s/mm2 | derived |
| SRAM read bandwidth density | 556.3 GB/s/mm2 | derived |
| Compute density, bf16 | 0.680 Tops/s/mm2 | derived |
| Compute density, fp8 | 1.360 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.923 Tops/s/mm2 | derived |
| Compute density, fp4 | 2.720 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.042 Tops/s/mm2 | derived |
| ROM full-array sweep time | 34.5 us | derived |
| ROM per-token ceiling from that sweep | 29,015 tok/s | derived |
| ROM per-token ceiling before the read derate | 38,686 tok/s | derived |

The ROM full-array sweep time is rom_capacity_density divided by rom_read_bandwidth_density. Both scale with the same published bitcell-area ratio under this derivation, so the sweep time -- and hence the ROM path's hard per-token ceiling -- is the SAME at every node. Process scaling buys a ROM design capacity, not per-token speed. No clock-frequency bonus is credited, which makes this the conservative reading.

## Models and their work

| Model | Context | Params | Checkpoint | Native bits/param | KV read/token | KV/user | W:KV at B=1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 32,768 | 1,600 B | 892.7 GB | 4.46 | 0.110 GB | 0.331 GB | 359.0 |

## The latency separation, before and after, at batch 1

Per-user latency and aggregate throughput used to be one number in
this study. The service time was computed on the machine's
**aggregate** resources -- the throughput view -- and the hops were
added on the single-token path, which is the latency view. A token
under pipeline parallelism is served by one stage's silicon at a time
and has to visit every stage, so its latency is that service time
multiplied by the slot count, not divided by anything.

**Before** is not a memory of an earlier run. Every point carries
`per_user_tokens_s_throughput_view`, the number the old rule produced,
and each side is ranked by it -- so the before column reproduces the
previous topology choice as well as the previous rate, and the two
corrections stay separable. Both sides are read at the same seven
rungs of silicon.

| Model | Wafer-eq | mm2 | ROM before | topo | ROM after | topo | ROM /x | GPU before | topo | GPU after | topo | GPU /x | Ratio before | Ratio after | Ratio change |
|---|---:|---:|---:|---|---:|---|---:|---:|---|---:|---|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 2,158.2 | wafer-pipeline | 1,492.0 | wafer-hybrid | 1.45x | 684.2 | pipeline | 413.8 | hybrid | 1.65x | 3.15x | 3.61x | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 2,161.7 | wafer-pipeline | 1,700.6 | wafer-hybrid | 1.27x | 691.9 | pipeline | 419.4 | hybrid | 1.65x | 3.12x | 4.06x | 1.30x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 2,161.7 | wafer-pipeline | 1,731.2 | wafer-hybrid | 1.25x | 699.7 | pipeline | 418.7 | hybrid | 1.67x | 3.09x | 4.13x | 1.34x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 2,161.7 | wafer-pipeline | 1,732.4 | wafer-hybrid | 1.25x | 703.7 | pipeline | 418.2 | hybrid | 1.68x | 3.07x | 4.14x | 1.35x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 2,162.1 | wafer-pipeline | 1,732.4 | wafer-hybrid | 1.25x | 707.8 | pipeline | 420.1 | hybrid | 1.69x | 3.05x | 4.12x | 1.35x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.14x to 1.35x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


## Iso-area comparison

Two ROM designs per operating point -- the **fastest** and the
**smallest silicon that serves the point at all** -- each against the GPU
cluster of the closest equal silicon area. **The area is stated on both
sides.** Where one row appears, the two coincide.

**Both sides choose their own parallelism.** The GPU cluster is
evaluated under pipeline, tensor and hybrid and the best is reported,
exactly as the ROM side is. `PP-only ratio` is what the same comparison
says when the GPU is allowed pipeline and nothing else.

`Ratio without the layer cap` is what the comparison says when a token
is allowed to cross more stage boundaries than the model has layers --
which is what this study charged before. That column, not the topology
sweep, is where the previously published ratios came from.

**`user tok/s` and `aggregate tok/s` are different quantities and no
longer differ by the batch.** `user tok/s` is one user's token rate on
the full serial path through the machine. `aggregate tok/s` is the
machine's total rate with a user in every slot, which needs
`token_slots` concurrent users; where the batch is smaller than that,
the surplus slots idle and what the machine actually delivers at the
stated batch is `batch x user tok/s`, carried per point as
`delivered_tokens_s`. Read the per-user ratio for a latency claim and
the aggregate ratio for a throughput claim; reading either as the other
is the error this study made.

| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | GPU parallelism | GPU link us | GPU user tok/s | GPU aggregate tok/s | GPU binds on | Per-user ratio | Aggregate ratio | PP-only ratio | Ratio without the layer cap |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x268 | 218,420 | 1,892.4 | 126,789.7 | layer_fixed_latency | DSV4-Pro/b200_sxm-x137-nvl72-hybrid | 219,200 | 1.00x | hybrid | 950.33 | 421.6 | 843.1 | layer_fixed_latency | 4.49x | 6.68x | 13.67x | 4.49x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x146 | 118,990 | 1,124.5 | 1,124.5 | layer_fixed_latency | DSV4-Pro/b200_sxm-x74-nvl72-hybrid | 118,400 | 1.00x | hybrid | 948.04 | 410.0 | 819.9 | layer_fixed_latency | 2.74x | 0.11x | 8.12x | 2.74x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x268 | 218,420 | 1,892.4 | 126,789.7 | layer_fixed_latency | DSV4-Pro/b200_sxm-x137-nvl72-hybrid | 219,200 | 1.00x | hybrid | 950.33 | 421.6 | 843.1 | layer_fixed_latency | 4.49x | 6.68x | 13.67x | 4.49x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 1,163.2 | 3,489.6 | layer_fixed_latency | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 948.04 | 411.9 | 823.8 | layer_fixed_latency | 2.82x | 0.31x | 8.40x | 2.82x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x268 | 218,420 | 1,892.4 | 126,789.7 | layer_fixed_latency | DSV4-Pro/b200_sxm-x137-nvl72-hybrid | 219,200 | 1.00x | hybrid | 973.46 | 408.3 | 1,633.2 | layer_fixed_latency | 4.63x | 6.68x | 13.67x | 4.63x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 1,147.6 | 5,738.0 | layer_fixed_latency | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 782.47 | 403.1 | 2,015.4 | layer_fixed_latency | 2.85x | 0.52x | 8.29x | 2.85x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x268 | 218,420 | 1,892.4 | 126,789.7 | layer_fixed_latency | DSV4-Pro/b200_sxm-x137-nvl72-hybrid | 219,200 | 1.00x | hybrid | 789.44 | 399.1 | 3,591.5 | layer_fixed_latency | 4.74x | 6.68x | 13.67x | 4.74x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 955.9 | 9,559.0 | layer_fixed_latency | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 812.48 | 387.7 | 3,101.7 | layer_fixed_latency | 2.47x | 0.86x | 6.90x | 2.47x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x268 | 218,420 | 1,892.4 | 126,789.7 | layer_fixed_latency | DSV4-Pro/b200_sxm-x137-nvl72-hybrid | 219,200 | 1.00x | hybrid | 829.38 | 378.9 | 6,063.1 | layer_fixed_latency | 4.99x | 6.68x | 13.67x | 4.99x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 690.9 | 11,054.0 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 892.50 | 352.3 | 5,636.7 | layer_fixed_latency | 1.96x | 1.00x | 4.99x | 1.96x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x268 | 218,420 | 1,892.4 | 126,789.7 | layer_fixed_latency | DSV4-Pro/b200_sxm-x137-nvl72-hybrid | 219,200 | 1.00x | hybrid | 920.67 | 340.3 | 10,889.3 | layer_fixed_latency | 5.56x | 6.68x | 13.67x | 5.56x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 444.3 | 14,217.6 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 1,052.54 | 299.0 | 9,569.6 | layer_fixed_latency | 1.49x | 1.28x | 3.21x | 1.49x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x268 | 218,420 | 1,892.4 | 126,789.7 | layer_fixed_latency | DSV4-Pro/b200_sxm-x137-nvl72-hybrid | 219,200 | 1.00x | hybrid | 1,103.25 | 284.0 | 18,175.2 | layer_fixed_latency | 6.66x | 6.68x | 13.67x | 6.66x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 258.6 | 16,552.7 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 1,027.58 | 234.4 | 15,001.7 | weight_read | 1.10x | 1.10x | 1.87x | 1.10x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,614.8 | 550,650.2 | layer_fixed_latency | DSV4-Pro/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 1,076.10 | 237.1 | 60,704.1 | weight_read | 6.81x | 9.07x | 11.66x | 6.81x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x158 | 128,770 | 72.8 | 18,625.6 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 1,894.93 | 115.9 | 29,673.4 | weight_read | 0.63x | 0.63x | 0.83x | 0.63x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,012.3 | 1,036,594.3 | compute | DSV4-Pro/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 1,959.16 | 119.1 | 121,995.4 | weight_read | 8.50x | 8.50x | 11.09x | 8.50x |
| DeepSeek-V4-Pro-0813 | 1024 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x158 | 128,770 | 18.4 | 18,887.3 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 6,504.22 | 51.0 | 52,213.7 | weight_read | 0.36x | 0.36x | 0.53x | 0.36x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 390.0 | 1,597,407.2 | weight_read | DSV4-Pro/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 6,521.76 | 51.7 | 211,891.5 | weight_read | 7.54x | 7.54x | 10.62x | 7.54x |
| DeepSeek-V4-Pro-0813 | 4096 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x158 | 128,770 | 4.6 | 18,934.0 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 23,995.90 | 24.7 | 101,001.7 | link_latency | 0.19x | 0.19x | 0.37x | 0.19x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 14 | 22,400 | 772.50 | 298.21 | 396.6 | 488.5 |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 932.24 | 298.43 | 405.7 | 546.1 |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 935.18 | 298.48 | 412.8 | 560.0 |
| DeepSeek-V4-Pro-0813 | 41 | 65,600 | 936.09 | 298.49 | 414.5 | 563.4 |
| DeepSeek-V4-Pro-0813 | 42 | 67,200 | 936.39 | 298.49 | 415.0 | 564.4 |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 941.12 | 298.53 | 420.6 | 576.3 |
| DeepSeek-V4-Pro-0813 | 74 | 118,400 | 948.04 | 300.87 | 410.0 | 558.0 |
| DeepSeek-V4-Pro-0813 | 79 | 126,400 | 948.04 | 300.87 | 411.6 | 561.0 |
| DeepSeek-V4-Pro-0813 | 80 | 128,000 | 948.04 | 300.87 | 411.9 | 561.6 |
| DeepSeek-V4-Pro-0813 | 83 | 132,800 | 948.04 | 300.87 | 412.7 | 563.2 |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 948.04 | 300.87 | 413.8 | 565.1 |
| DeepSeek-V4-Pro-0813 | 90 | 144,000 | 948.04 | 300.87 | 414.5 | 566.5 |
| DeepSeek-V4-Pro-0813 | 91 | 145,600 | 948.04 | 300.87 | 414.8 | 566.9 |
| DeepSeek-V4-Pro-0813 | 92 | 147,200 | 948.04 | 300.87 | 415.0 | 567.4 |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 948.04 | 300.87 | 416.3 | 569.8 |
| DeepSeek-V4-Pro-0813 | 100 | 160,000 | 948.04 | 300.87 | 416.7 | 570.5 |
| DeepSeek-V4-Pro-0813 | 101 | 161,600 | 948.04 | 300.87 | 416.9 | 570.9 |
| DeepSeek-V4-Pro-0813 | 110 | 176,000 | 948.04 | 300.87 | 418.4 | 573.8 |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 948.04 | 300.87 | 419.4 | 575.6 |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 948.04 | 300.87 | 419.6 | 576.1 |
| DeepSeek-V4-Pro-0813 | 121 | 193,600 | 948.04 | 300.87 | 420.1 | 576.9 |
| DeepSeek-V4-Pro-0813 | 132 | 211,200 | 950.33 | 300.87 | 421.0 | 579.5 |
| DeepSeek-V4-Pro-0813 | 137 | 219,200 | 950.33 | 300.87 | 421.6 | 580.5 |
| DeepSeek-V4-Pro-0813 | 144 | 230,400 | 1,038.09 | 300.87 | 422.2 | 613.1 |
| DeepSeek-V4-Pro-0813 | 146 | 233,600 | 951.22 | 303.18 | 415.6 | 568.8 |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 951.22 | 303.18 | 417.0 | 571.4 |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 951.22 | 303.18 | 418.7 | 574.6 |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 954.39 | 305.50 | 418.2 | 573.9 |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 959.87 | 307.82 | 420.1 | 578.5 |

## The GPU's own topology choice, at batch 1

Every cluster size in the study, under each parallelism it can
actually run, at **per-user** rate. `pipeline` is what this study
charged the GPU before, at every size; `hybrid` is tensor-parallel
inside the NVLink domain and pipeline-parallel across it, which is
what a real deployment of this size runs. A blank cell is a topology
that collapses onto another at that size and is not emitted twice.

**This table is where the latency separation shows up most
plainly.** A pipeline column is now a machine cut into as many slots
as it has GPUs, and a token visits every one of them; the whole
cluster's HBM bandwidth is on that token's path only under `tensor`,
which is why a 672-GPU pipeline reads as fractions of a token per
second while the same silicon tensor-parallel reads in the hundreds.

| Model | GPUs | mm2 | Pipeline tok/s | Tensor tok/s | Hybrid tok/s | Best | Best link us | Link share | Binds on |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| DeepSeek-V4-Pro-0813 | 14 | 22,400 | 139.9 | 396.6 | 341.6 | tensor | 772.50 | 30.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 139.4 | 405.7 | 344.2 | tensor | 932.24 | 37.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 139.2 | 412.8 | 348.1 | tensor | 935.18 | 38.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 41 | 65,600 | 139.0 | 414.5 | 337.9 | tensor | 936.09 | 38.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 42 | 67,200 | 139.0 | 415.0 | 340.1 | tensor | 936.39 | 38.9% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 138.6 | 420.6 | 342.7 | tensor | 941.12 | 39.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 74 | 118,400 | 138.5 | 210.2 | 410.0 | hybrid | 948.04 | 38.9% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 79 | 126,400 | 138.5 | 209.8 | 411.6 | hybrid | 948.04 | 39.0% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 80 | 128,000 | 138.5 | 209.7 | 411.9 | hybrid | 948.04 | 39.0% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 83 | 132,800 | 138.5 | 209.4 | 412.7 | hybrid | 948.04 | 39.1% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 138.5 | 209.1 | 413.8 | hybrid | 948.04 | 39.2% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 90 | 144,000 | 138.5 | 208.8 | 414.5 | hybrid | 948.04 | 39.3% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 91 | 145,600 | 138.5 | 208.7 | 414.8 | hybrid | 948.04 | 39.3% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 92 | 147,200 | 138.5 | 208.6 | 415.0 | hybrid | 948.04 | 39.3% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 138.5 | 208.0 | 416.3 | hybrid | 948.04 | 39.5% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 100 | 160,000 | 138.5 | 207.8 | 416.7 | hybrid | 948.04 | 39.5% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 101 | 161,600 | 138.5 | 207.8 | 416.9 | hybrid | 948.04 | 39.5% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 110 | 176,000 | 138.5 | 206.9 | 418.4 | hybrid | 948.04 | 39.7% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 138.5 | 206.3 | 419.4 | hybrid | 948.04 | 39.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 138.5 | 206.1 | 419.6 | hybrid | 948.04 | 39.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 121 | 193,600 | 138.5 | 205.8 | 420.1 | hybrid | 948.04 | 39.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 132 | 211,200 | 138.5 | 204.7 | 421.0 | hybrid | 950.33 | 40.0% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 137 | 219,200 | 138.5 | 204.1 | 421.6 | hybrid | 950.33 | 40.1% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 144 | 230,400 | 138.5 | 203.4 | 422.2 | hybrid | 1,038.09 | 43.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 146 | 233,600 | 138.5 | 191.4 | 415.6 | hybrid | 951.22 | 39.5% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 138.5 | 190.1 | 417.0 | hybrid | 951.22 | 39.7% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 138.5 | 188.2 | 418.7 | hybrid | 951.22 | 39.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 138.5 | 175.5 | 418.2 | hybrid | 954.39 | 39.9% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 138.5 | 159.0 | 420.1 | hybrid | 959.87 | 40.3% | layer_fixed_latency |

## Array or wafer: the crossover, reported rather than assumed

`Array viable to` is the per-user rate at which the topology's hops alone
consume 10% of the token budget; `hard ceiling` is the rate at which they
consume all of it. Below the first number the interconnect is a design
cost; above the second the topology cannot deliver the rate at all.

Each event is priced on the link it actually crosses and, for a
collective, on how many partitions it spans: an all-reduce costs
`traversals x hop latency` plus `(p-1)/p` of the payload each way, where
`traversals` is `2 lg p` in the fabric's own switch radix (Thakur,
Rabenseifner & Gropp 2005) or 1.1x the mesh diameter on a stitched
fabric (Rocki et al., SC20). `Events` spells the breakdown out.

| Design | Model | Devices | Parallelism | Intra link | Inter link | Hops/token | Link latency/token | Viable to (10% budget) | Hard ceiling | Events |
|---|---|---:|---|---|---|---:|---:|---:|---:|---|
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x196 | DeepSeek-V4-Pro-0813 | 196 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x156 | DeepSeek-V4-Pro-0813 | 156 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.30 us | 597.7 tok/s | 5,977.1 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 39 on rom_board_serdes (traversals 13.2) = 163.88 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x180 | DeepSeek-V4-Pro-0813 | 180 | hybrid | rom_package_ucie | rom_board_serdes | 166 | 8.17 us | 12,233.5 tok/s | 122,335.5 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 44 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.75 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x196 | DeepSeek-V4-Pro-0813 | 196 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x4 | DeepSeek-V4-Pro-0813 | 4 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x146 | DeepSeek-V4-Pro-0813 | 146 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 262.27 us | 381.3 tok/s | 3,812.8 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 27.42 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x176 | DeepSeek-V4-Pro-0813 | 176 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x4 | DeepSeek-V4-Pro-0813 | 4 | hybrid | on_wafer_n5 | rom_wafer_serdes | 125 | 235.16 us | 425.2 tok/s | 4,252.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x268 | DeepSeek-V4-Pro-0813 | 268 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x162 | DeepSeek-V4-Pro-0813 | 162 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.31 us | 597.7 tok/s | 5,977.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 41 on rom_board_serdes (traversals 13.2) = 163.88 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x238 | DeepSeek-V4-Pro-0813 | 238 | hybrid | rom_package_ucie | rom_board_serdes | 181 | 9.79 us | 10,210.6 tok/s | 102,106.3 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 59 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.37 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x268 | DeepSeek-V4-Pro-0813 | 268 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x5 | DeepSeek-V4-Pro-0813 | 5 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x158 | DeepSeek-V4-Pro-0813 | 158 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 262.27 us | 381.3 tok/s | 3,812.8 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 27.42 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x198 | DeepSeek-V4-Pro-0813 | 198 | hybrid | nvlink5 | infiniband_ndr | 146 | 353.50 us | 282.9 tok/s | 2,828.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 55.60 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | DeepSeek-V4-Pro-0813 | 4 | hybrid | on_wafer_n5 | rom_wafer_serdes | 125 | 235.16 us | 425.2 tok/s | 4,252.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| DSV4-Pro/b200_sxm-x14-pipeline | DeepSeek-V4-Pro-0813 | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 16.91 us | 5,914.4 tok/s | 59,144.1 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 14.59 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x14-tensor | DeepSeek-V4-Pro-0813 | 14 | tensor | nvlink5 | infiniband_ndr | 244 | 845.69 us | 118.2 tok/s | 1,182.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x14-hybrid | DeepSeek-V4-Pro-0813 | 14 | hybrid | nvlink5 | infiniband_ndr | 123 | 300.22 us | 333.1 tok/s | 3,330.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x14-nvl72-tensor | DeepSeek-V4-Pro-0813 | 14 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.21 us | 335.3 tok/s | 3,353.3 tok/s | 122 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 298.21 us |
| DSV4-Pro/b200_sxm-x14-expert | DeepSeek-V4-Pro-0813 | 14 | expert | nvlink5 | infiniband_ndr | 244 | 560.55 us | 178.4 tok/s | 1,784.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 262.65 us |
| DSV4-Pro/b200_sxm-x14-nvl72-expert | DeepSeek-V4-Pro-0813 | 14 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.45 us | 224.5 tok/s | 2,244.9 tok/s | 122 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 298.21 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 147.23 us |
| DSV4-Pro/b200_sxm-x29-pipeline | DeepSeek-V4-Pro-0813 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.35 us | 2,677.5 tok/s | 26,774.9 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.40 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5 | infiniband_ndr | 244 | 871.93 us | 114.7 tok/s | 1,146.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x29-hybrid | DeepSeek-V4-Pro-0813 | 29 | hybrid | nvlink5 | infiniband_ndr | 125 | 304.85 us | 328.0 tok/s | 3,280.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-nvl72-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.43 us | 335.1 tok/s | 3,350.9 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us |
| DSV4-Pro/b200_sxm-x29-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5 | infiniband_ndr | 244 | 549.40 us | 182.0 tok/s | 1,820.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 294.50 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 254.90 us |
| DSV4-Pro/b200_sxm-x29-nvl72-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.23 us | 224.6 tok/s | 2,246.0 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.80 us |
| DSV4-Pro/b200_sxm-x38-pipeline | DeepSeek-V4-Pro-0813 | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 49.39 us | 2,024.6 tok/s | 20,246.0 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 40.13 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x38-tensor | DeepSeek-V4-Pro-0813 | 38 | tensor | nvlink5 | infiniband_ndr | 244 | 877.17 us | 114.0 tok/s | 1,140.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x38-hybrid | DeepSeek-V4-Pro-0813 | 38 | hybrid | nvlink5 | infiniband_ndr | 126 | 307.17 us | 325.6 tok/s | 3,255.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x38-nvl72-tensor | DeepSeek-V4-Pro-0813 | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.48 us | 335.0 tok/s | 3,350.3 tok/s | 122 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 298.48 us |
| DSV4-Pro/b200_sxm-x38-expert | DeepSeek-V4-Pro-0813 | 38 | expert | nvlink5 | infiniband_ndr | 244 | 547.26 us | 182.7 tok/s | 1,827.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 294.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 253.18 us |
| DSV4-Pro/b200_sxm-x38-nvl72-expert | DeepSeek-V4-Pro-0813 | 38 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.18 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 298.48 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.71 us |
| DSV4-Pro/b200_sxm-x41-pipeline | DeepSeek-V4-Pro-0813 | 41 | pipeline | nvlink5 | infiniband_ndr | 40 | 54.14 us | 1,847.0 tok/s | 18,470.3 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.56 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x41-tensor | DeepSeek-V4-Pro-0813 | 41 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x41-hybrid | DeepSeek-V4-Pro-0813 | 41 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x41-nvl72-tensor | DeepSeek-V4-Pro-0813 | 41 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.49 us | 335.0 tok/s | 3,350.2 tok/s | 122 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 298.49 us |
| DSV4-Pro/b200_sxm-x41-expert | DeepSeek-V4-Pro-0813 | 41 | expert | nvlink5 | infiniband_ndr | 244 | 546.60 us | 182.9 tok/s | 1,829.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.78 us |
| DSV4-Pro/b200_sxm-x41-nvl72-expert | DeepSeek-V4-Pro-0813 | 41 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.17 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 298.49 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.68 us |
| DSV4-Pro/b200_sxm-x42-pipeline | DeepSeek-V4-Pro-0813 | 42 | pipeline | nvlink5 | infiniband_ndr | 41 | 55.36 us | 1,806.5 tok/s | 18,064.5 tok/s | 36 x point_to_point span 2 on nvlink5 (traversals 1.0) = 43.77 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x42-tensor | DeepSeek-V4-Pro-0813 | 42 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x42-hybrid | DeepSeek-V4-Pro-0813 | 42 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x42-nvl72-tensor | DeepSeek-V4-Pro-0813 | 42 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.49 us | 335.0 tok/s | 3,350.2 tok/s | 122 x all_reduce span 42 on nvlink5_nvl72 (traversals 2.0) = 298.49 us |
| DSV4-Pro/b200_sxm-x42-expert | DeepSeek-V4-Pro-0813 | 42 | expert | nvlink5 | infiniband_ndr | 244 | 546.48 us | 183.0 tok/s | 1,829.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.66 us |
| DSV4-Pro/b200_sxm-x42-nvl72-expert | DeepSeek-V4-Pro-0813 | 42 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.17 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 42 on nvlink5_nvl72 (traversals 2.0) = 298.49 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.68 us |
| DSV4-Pro/b200_sxm-x58-pipeline | DeepSeek-V4-Pro-0813 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 77.01 us | 1,298.5 tok/s | 12,984.7 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5 | infiniband_ndr | 244 | 885.04 us | 113.0 tok/s | 1,129.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 587.14 us |
| DSV4-Pro/b200_sxm-x58-hybrid | DeepSeek-V4-Pro-0813 | 58 | hybrid | nvlink5 | infiniband_ndr | 129 | 314.12 us | 318.4 tok/s | 3,183.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-nvl72-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.53 us | 335.0 tok/s | 3,349.8 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us |
| DSV4-Pro/b200_sxm-x58-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5 | infiniband_ndr | 244 | 544.81 us | 183.6 tok/s | 1,835.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.53 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 251.28 us |
| DSV4-Pro/b200_sxm-x58-nvl72-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.13 us | 224.7 tok/s | 2,246.5 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.60 us |
| DSV4-Pro/b200_sxm-x74-pipeline | DeepSeek-V4-Pro-0813 | 74 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x74-tensor | DeepSeek-V4-Pro-0813 | 74 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x74-hybrid | DeepSeek-V4-Pro-0813 | 74 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x74-nvl72-tensor | DeepSeek-V4-Pro-0813 | 74 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x74-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 74 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x74-expert | DeepSeek-V4-Pro-0813 | 74 | expert | nvlink5 | infiniband_ndr | 244 | 543.86 us | 183.9 tok/s | 1,838.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.37 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.50 us |
| DSV4-Pro/b200_sxm-x74-nvl72-expert | DeepSeek-V4-Pro-0813 | 74 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 549.05 us | 182.1 tok/s | 1,821.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.50 us |
| DSV4-Pro/b200_sxm-x79-pipeline | DeepSeek-V4-Pro-0813 | 79 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x79-tensor | DeepSeek-V4-Pro-0813 | 79 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x79-hybrid | DeepSeek-V4-Pro-0813 | 79 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x79-nvl72-tensor | DeepSeek-V4-Pro-0813 | 79 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x79-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 79 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x79-expert | DeepSeek-V4-Pro-0813 | 79 | expert | nvlink5 | infiniband_ndr | 244 | 543.68 us | 183.9 tok/s | 1,839.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.37 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.32 us |
| DSV4-Pro/b200_sxm-x79-nvl72-expert | DeepSeek-V4-Pro-0813 | 79 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.87 us | 182.2 tok/s | 1,821.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.32 us |
| DSV4-Pro/b200_sxm-x80-pipeline | DeepSeek-V4-Pro-0813 | 80 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x80-tensor | DeepSeek-V4-Pro-0813 | 80 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x80-hybrid | DeepSeek-V4-Pro-0813 | 80 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x80-nvl72-tensor | DeepSeek-V4-Pro-0813 | 80 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x80-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 80 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x80-expert | DeepSeek-V4-Pro-0813 | 80 | expert | nvlink5 | infiniband_ndr | 244 | 543.59 us | 184.0 tok/s | 1,839.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.28 us |
| DSV4-Pro/b200_sxm-x80-nvl72-expert | DeepSeek-V4-Pro-0813 | 80 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.83 us | 182.2 tok/s | 1,822.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.28 us |
| DSV4-Pro/b200_sxm-x83-pipeline | DeepSeek-V4-Pro-0813 | 83 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x83-tensor | DeepSeek-V4-Pro-0813 | 83 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x83-hybrid | DeepSeek-V4-Pro-0813 | 83 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x83-nvl72-tensor | DeepSeek-V4-Pro-0813 | 83 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x83-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 83 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x83-expert | DeepSeek-V4-Pro-0813 | 83 | expert | nvlink5 | infiniband_ndr | 244 | 543.50 us | 184.0 tok/s | 1,839.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.19 us |
| DSV4-Pro/b200_sxm-x83-nvl72-expert | DeepSeek-V4-Pro-0813 | 83 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.74 us | 182.2 tok/s | 1,822.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.19 us |
| DSV4-Pro/b200_sxm-x87-pipeline | DeepSeek-V4-Pro-0813 | 87 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x87-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x87-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x87-nvl72-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x87-expert | DeepSeek-V4-Pro-0813 | 87 | expert | nvlink5 | infiniband_ndr | 244 | 543.38 us | 184.0 tok/s | 1,840.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.07 us |
| DSV4-Pro/b200_sxm-x87-nvl72-expert | DeepSeek-V4-Pro-0813 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.62 us | 182.3 tok/s | 1,822.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.07 us |
| DSV4-Pro/b200_sxm-x90-pipeline | DeepSeek-V4-Pro-0813 | 90 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x90-tensor | DeepSeek-V4-Pro-0813 | 90 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x90-hybrid | DeepSeek-V4-Pro-0813 | 90 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x90-nvl72-tensor | DeepSeek-V4-Pro-0813 | 90 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x90-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 90 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x90-expert | DeepSeek-V4-Pro-0813 | 90 | expert | nvlink5 | infiniband_ndr | 244 | 543.26 us | 184.1 tok/s | 1,840.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.26 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.99 us |
| DSV4-Pro/b200_sxm-x90-nvl72-expert | DeepSeek-V4-Pro-0813 | 90 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.54 us | 182.3 tok/s | 1,823.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.99 us |
| DSV4-Pro/b200_sxm-x91-pipeline | DeepSeek-V4-Pro-0813 | 91 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x91-tensor | DeepSeek-V4-Pro-0813 | 91 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x91-hybrid | DeepSeek-V4-Pro-0813 | 91 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x91-nvl72-tensor | DeepSeek-V4-Pro-0813 | 91 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x91-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 91 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x91-expert | DeepSeek-V4-Pro-0813 | 91 | expert | nvlink5 | infiniband_ndr | 244 | 543.23 us | 184.1 tok/s | 1,840.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.26 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.97 us |
| DSV4-Pro/b200_sxm-x91-nvl72-expert | DeepSeek-V4-Pro-0813 | 91 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.52 us | 182.3 tok/s | 1,823.1 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.97 us |
| DSV4-Pro/b200_sxm-x92-pipeline | DeepSeek-V4-Pro-0813 | 92 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x92-tensor | DeepSeek-V4-Pro-0813 | 92 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x92-hybrid | DeepSeek-V4-Pro-0813 | 92 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x92-nvl72-tensor | DeepSeek-V4-Pro-0813 | 92 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x92-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 92 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x92-expert | DeepSeek-V4-Pro-0813 | 92 | expert | nvlink5 | infiniband_ndr | 244 | 543.21 us | 184.1 tok/s | 1,840.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.26 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.94 us |
| DSV4-Pro/b200_sxm-x92-nvl72-expert | DeepSeek-V4-Pro-0813 | 92 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.49 us | 182.3 tok/s | 1,823.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.94 us |
| DSV4-Pro/b200_sxm-x98-pipeline | DeepSeek-V4-Pro-0813 | 98 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x98-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink5 | infiniband_ndr | 244 | 890.09 us | 112.3 tok/s | 1,123.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 592.19 us |
| DSV4-Pro/b200_sxm-x98-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink5 | infiniband_ndr | 134 | 325.70 us | 307.0 tok/s | 3,070.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.80 us |
| DSV4-Pro/b200_sxm-x98-nvl72-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x98-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x98-expert | DeepSeek-V4-Pro-0813 | 98 | expert | nvlink5 | infiniband_ndr | 244 | 543.03 us | 184.2 tok/s | 1,841.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.23 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.80 us |
| DSV4-Pro/b200_sxm-x98-nvl72-expert | DeepSeek-V4-Pro-0813 | 98 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.35 us | 182.4 tok/s | 1,823.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.80 us |
| DSV4-Pro/b200_sxm-x100-pipeline | DeepSeek-V4-Pro-0813 | 100 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x100-tensor | DeepSeek-V4-Pro-0813 | 100 | tensor | nvlink5 | infiniband_ndr | 244 | 890.09 us | 112.3 tok/s | 1,123.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 592.19 us |
| DSV4-Pro/b200_sxm-x100-hybrid | DeepSeek-V4-Pro-0813 | 100 | hybrid | nvlink5 | infiniband_ndr | 134 | 325.70 us | 307.0 tok/s | 3,070.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.80 us |
| DSV4-Pro/b200_sxm-x100-nvl72-tensor | DeepSeek-V4-Pro-0813 | 100 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x100-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 100 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x100-expert | DeepSeek-V4-Pro-0813 | 100 | expert | nvlink5 | infiniband_ndr | 244 | 542.98 us | 184.2 tok/s | 1,841.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.23 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.76 us |
| DSV4-Pro/b200_sxm-x100-nvl72-expert | DeepSeek-V4-Pro-0813 | 100 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.31 us | 182.4 tok/s | 1,823.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.76 us |
| DSV4-Pro/b200_sxm-x101-pipeline | DeepSeek-V4-Pro-0813 | 101 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x101-tensor | DeepSeek-V4-Pro-0813 | 101 | tensor | nvlink5 | infiniband_ndr | 244 | 890.09 us | 112.3 tok/s | 1,123.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 592.19 us |
| DSV4-Pro/b200_sxm-x101-hybrid | DeepSeek-V4-Pro-0813 | 101 | hybrid | nvlink5 | infiniband_ndr | 134 | 325.70 us | 307.0 tok/s | 3,070.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.80 us |
| DSV4-Pro/b200_sxm-x101-nvl72-tensor | DeepSeek-V4-Pro-0813 | 101 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x101-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 101 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x101-expert | DeepSeek-V4-Pro-0813 | 101 | expert | nvlink5 | infiniband_ndr | 244 | 542.96 us | 184.2 tok/s | 1,841.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.23 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.74 us |
| DSV4-Pro/b200_sxm-x101-nvl72-expert | DeepSeek-V4-Pro-0813 | 101 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.29 us | 182.4 tok/s | 1,823.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.74 us |
| DSV4-Pro/b200_sxm-x110-pipeline | DeepSeek-V4-Pro-0813 | 110 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x110-tensor | DeepSeek-V4-Pro-0813 | 110 | tensor | nvlink5 | infiniband_ndr | 244 | 890.67 us | 112.3 tok/s | 1,122.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 592.76 us |
| DSV4-Pro/b200_sxm-x110-hybrid | DeepSeek-V4-Pro-0813 | 110 | hybrid | nvlink5 | infiniband_ndr | 135 | 328.02 us | 304.9 tok/s | 3,048.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.12 us |
| DSV4-Pro/b200_sxm-x110-nvl72-tensor | DeepSeek-V4-Pro-0813 | 110 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x110-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 110 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x110-expert | DeepSeek-V4-Pro-0813 | 110 | expert | nvlink5 | infiniband_ndr | 244 | 542.76 us | 184.2 tok/s | 1,842.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.19 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.57 us |
| DSV4-Pro/b200_sxm-x110-nvl72-expert | DeepSeek-V4-Pro-0813 | 110 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.12 us | 182.4 tok/s | 1,824.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.57 us |
| DSV4-Pro/b200_sxm-x116-pipeline | DeepSeek-V4-Pro-0813 | 116 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x116-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x116-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x116-nvl72-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x116-expert | DeepSeek-V4-Pro-0813 | 116 | expert | nvlink5 | infiniband_ndr | 244 | 542.63 us | 184.3 tok/s | 1,842.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.47 us |
| DSV4-Pro/b200_sxm-x116-nvl72-expert | DeepSeek-V4-Pro-0813 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.02 us | 182.5 tok/s | 1,824.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.47 us |
| DSV4-Pro/b200_sxm-x118-pipeline | DeepSeek-V4-Pro-0813 | 118 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x118-tensor | DeepSeek-V4-Pro-0813 | 118 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x118-hybrid | DeepSeek-V4-Pro-0813 | 118 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x118-nvl72-tensor | DeepSeek-V4-Pro-0813 | 118 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x118-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 118 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x118-expert | DeepSeek-V4-Pro-0813 | 118 | expert | nvlink5 | infiniband_ndr | 244 | 542.60 us | 184.3 tok/s | 1,843.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.44 us |
| DSV4-Pro/b200_sxm-x118-nvl72-expert | DeepSeek-V4-Pro-0813 | 118 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.99 us | 182.5 tok/s | 1,824.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.44 us |
| DSV4-Pro/b200_sxm-x121-pipeline | DeepSeek-V4-Pro-0813 | 121 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x121-tensor | DeepSeek-V4-Pro-0813 | 121 | tensor | nvlink5 | infiniband_ndr | 244 | 891.60 us | 112.2 tok/s | 1,121.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 593.70 us |
| DSV4-Pro/b200_sxm-x121-hybrid | DeepSeek-V4-Pro-0813 | 121 | hybrid | nvlink5 | infiniband_ndr | 137 | 332.65 us | 300.6 tok/s | 3,006.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 34.75 us |
| DSV4-Pro/b200_sxm-x121-nvl72-tensor | DeepSeek-V4-Pro-0813 | 121 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x121-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 121 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x121-expert | DeepSeek-V4-Pro-0813 | 121 | expert | nvlink5 | infiniband_ndr | 244 | 542.53 us | 184.3 tok/s | 1,843.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.14 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.39 us |
| DSV4-Pro/b200_sxm-x121-nvl72-expert | DeepSeek-V4-Pro-0813 | 121 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.94 us | 182.5 tok/s | 1,825.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.39 us |
| DSV4-Pro/b200_sxm-x132-pipeline | DeepSeek-V4-Pro-0813 | 132 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x132-tensor | DeepSeek-V4-Pro-0813 | 132 | tensor | nvlink5 | infiniband_ndr | 244 | 891.99 us | 112.1 tok/s | 1,121.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 594.09 us |
| DSV4-Pro/b200_sxm-x132-hybrid | DeepSeek-V4-Pro-0813 | 132 | hybrid | nvlink5 | infiniband_ndr | 138 | 334.97 us | 298.5 tok/s | 2,985.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.07 us |
| DSV4-Pro/b200_sxm-x132-nvl72-tensor | DeepSeek-V4-Pro-0813 | 132 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x132-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 132 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x132-expert | DeepSeek-V4-Pro-0813 | 132 | expert | nvlink5 | infiniband_ndr | 244 | 542.37 us | 184.4 tok/s | 1,843.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.12 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.25 us |
| DSV4-Pro/b200_sxm-x132-nvl72-expert | DeepSeek-V4-Pro-0813 | 132 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.80 us | 182.5 tok/s | 1,825.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.25 us |
| DSV4-Pro/b200_sxm-x137-pipeline | DeepSeek-V4-Pro-0813 | 137 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x137-tensor | DeepSeek-V4-Pro-0813 | 137 | tensor | nvlink5 | infiniband_ndr | 244 | 892.33 us | 112.1 tok/s | 1,120.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 594.43 us |
| DSV4-Pro/b200_sxm-x137-hybrid | DeepSeek-V4-Pro-0813 | 137 | hybrid | nvlink5 | infiniband_ndr | 139 | 337.29 us | 296.5 tok/s | 2,964.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 39.38 us |
| DSV4-Pro/b200_sxm-x137-nvl72-tensor | DeepSeek-V4-Pro-0813 | 137 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x137-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 137 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x137-expert | DeepSeek-V4-Pro-0813 | 137 | expert | nvlink5 | infiniband_ndr | 244 | 542.29 us | 184.4 tok/s | 1,844.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.10 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.19 us |
| DSV4-Pro/b200_sxm-x137-nvl72-expert | DeepSeek-V4-Pro-0813 | 137 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.74 us | 182.6 tok/s | 1,825.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.19 us |
| DSV4-Pro/b200_sxm-x144-pipeline | DeepSeek-V4-Pro-0813 | 144 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x144-tensor | DeepSeek-V4-Pro-0813 | 144 | tensor | nvlink5 | infiniband_ndr | 244 | 892.33 us | 112.1 tok/s | 1,120.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 594.43 us |
| DSV4-Pro/b200_sxm-x144-hybrid | DeepSeek-V4-Pro-0813 | 144 | hybrid | nvlink5 | infiniband_ndr | 139 | 337.29 us | 296.5 tok/s | 2,964.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 39.38 us |
| DSV4-Pro/b200_sxm-x144-nvl72-tensor | DeepSeek-V4-Pro-0813 | 144 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x144-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 144 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x144-expert | DeepSeek-V4-Pro-0813 | 144 | expert | nvlink5 | infiniband_ndr | 244 | 542.20 us | 184.4 tok/s | 1,844.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.12 us |
| DSV4-Pro/b200_sxm-x144-nvl72-expert | DeepSeek-V4-Pro-0813 | 144 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.79 us | 183.6 tok/s | 1,835.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.12 us |
| DSV4-Pro/b200_sxm-x146-pipeline | DeepSeek-V4-Pro-0813 | 146 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x146-tensor | DeepSeek-V4-Pro-0813 | 146 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x146-hybrid | DeepSeek-V4-Pro-0813 | 146 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x146-nvl72-tensor | DeepSeek-V4-Pro-0813 | 146 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x146-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 146 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x146-expert | DeepSeek-V4-Pro-0813 | 146 | expert | nvlink5 | infiniband_ndr | 244 | 542.18 us | 184.4 tok/s | 1,844.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.10 us |
| DSV4-Pro/b200_sxm-x146-nvl72-expert | DeepSeek-V4-Pro-0813 | 146 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.77 us | 183.6 tok/s | 1,835.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.10 us |
| DSV4-Pro/b200_sxm-x157-pipeline | DeepSeek-V4-Pro-0813 | 157 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x157-tensor | DeepSeek-V4-Pro-0813 | 157 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/b200_sxm-x157-hybrid | DeepSeek-V4-Pro-0813 | 157 | hybrid | nvlink5 | infiniband_ndr | 141 | 341.92 us | 292.5 tok/s | 2,924.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| DSV4-Pro/b200_sxm-x157-nvl72-tensor | DeepSeek-V4-Pro-0813 | 157 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x157-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 157 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x157-expert | DeepSeek-V4-Pro-0813 | 157 | expert | nvlink5 | infiniband_ndr | 244 | 542.07 us | 184.5 tok/s | 1,844.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.07 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.00 us |
| DSV4-Pro/b200_sxm-x157-nvl72-expert | DeepSeek-V4-Pro-0813 | 157 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.67 us | 183.6 tok/s | 1,836.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.00 us |
| DSV4-Pro/b200_sxm-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x173-nvl72-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x173-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5 | infiniband_ndr | 244 | 541.92 us | 184.5 tok/s | 1,845.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.04 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x173-nvl72-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.55 us | 183.6 tok/s | 1,836.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5 | infiniband_ndr | 244 | 894.54 us | 111.8 tok/s | 1,117.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 596.64 us |
| DSV4-Pro/b200_sxm-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5 | infiniband_ndr | 150 | 362.77 us | 275.7 tok/s | 2,756.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 64.87 us |
| DSV4-Pro/b200_sxm-x231-nvl72-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 872.57 us | 114.6 tok/s | 1,146.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 125 | 305.50 us | 327.3 tok/s | 3,273.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x231-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5 | infiniband_ndr | 244 | 541.55 us | 184.7 tok/s | 1,846.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.98 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x231-nvl72-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 543.28 us | 184.1 tok/s | 1,840.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.72 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x347-pipeline | DeepSeek-V4-Pro-0813 | 347 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x347-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5 | infiniband_ndr | 244 | 895.78 us | 111.6 tok/s | 1,116.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 597.87 us |
| DSV4-Pro/b200_sxm-x347-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5 | infiniband_ndr | 165 | 397.52 us | 251.6 tok/s | 2,515.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 99.62 us |
| DSV4-Pro/b200_sxm-x347-nvl72-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 877.82 us | 113.9 tok/s | 1,139.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 126 | 307.82 us | 324.9 tok/s | 3,248.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x347-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5 | infiniband_ndr | 244 | 541.18 us | 184.8 tok/s | 1,847.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.92 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |
| DSV4-Pro/b200_sxm-x347-nvl72-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 542.50 us | 184.3 tok/s | 1,843.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.24 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Pro-0813 | 1 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x193 | 157,295 | 1,817.4 | 0.012 | 1,817.4 (157,295) | 1,700.6 (184,900) | 0.94x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 2 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x193 | 157,295 | 1,817.4 | 0.012 | 1,817.4 (157,295) | 1,700.6 (184,900) | 0.94x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 4 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x193 | 157,295 | 1,817.4 | 0.012 | 1,817.4 (157,295) | 1,700.6 (184,900) | 0.94x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 8 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x193 | 157,295 | 1,817.4 | 0.012 | 1,817.4 (157,295) | 1,700.6 (184,900) | 0.94x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 16 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1,838.2 | 0.010 | 1,838.2 (185,005) | 1,700.6 (184,900) | 0.93x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 32 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x231 | 188,265 | 1,798.8 | 0.010 | 1,798.8 (188,265) | 1,700.6 (184,900) | 0.95x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x238 | 193,970 | 1,811.2 | 0.009 | 1,811.2 (193,970) | 1,657.7 (184,900) | 0.92x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 1,549.4 | 0.004 | 1,388.9 (251,020) | 1,549.4 (369,800) | 1.12x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,012.3 | 0.002 | 662.5 (277,100) | 1,012.3 (554,700) | 1.53x | compute |
| DeepSeek-V4-Pro-0813 | 4096 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 390.0 | 0.001 | 193.9 (277,100) | 390.0 (554,700) | 2.01x | weight_read |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. The ROM-plus-MAC floorplan holds the requested weights; the compute-in-ROM floorplan holds only 100.0% and is infeasible at this area. The failed floorplan is retained so the capacity cost of the larger cell remains visible.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 374.6 mm2 | 199.8 mm2 |
| weight capacity | 3.51 GB (100.0%) | 3.51 GB (100.0%) |
| capacity-feasible | yes | **no** |
| compute block | 293.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 321.8 mm2 |
| sustained fp8 compute roof | 2.197e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.098e+14 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 1.019e+14 |
| **can the compute block be fed?** | **0.93x** | there is nothing to feed |
| full-array sweep | 34.47 us | 34.47 us |

**The sweep is identical.** Both the capacity density and the
read-bandwidth density scale as one over bitcell area, so a larger
compute-in-ROM cell holds proportionally fewer bits AND delivers
proportionally fewer bytes per second: the cell size cancels in
their ratio. What the larger cell costs is capacity -- the same
weights need a bigger array, and that silicon comes out of the SRAM
beside it. An earlier version of this model applied the multiplier
to area alone and credited the result with the storage cell's
bandwidth density, which handed compute-in-ROM a free 1.6x on throughput.

The ROM-plus-MAC machine is bandwidth-starved: its array supplies
only 0.93x of the bytes its MAC roof wants,
so some compute capacity cannot be exercised.

## Sizing one expert region

The per-region machine's cost is not arithmetic; it is a
pre-compute block and an activation distribution network per
region. The block is small against the array it serves. The
distribution network is the real cost and this model does not
price it.

| Model | Experts | Routed bytes/expert | One region | Pre-compute/region | All regions | All pre-compute | Whole checkpoint |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 365.2 mm2 | 65.73 mm2 (18.0%) | 140,230 mm2 | 25,241 mm2 | 152,286 mm2 = 186.9 reticles |

## The batch-amortisation fork, reported rather than resolved

`docs/ANALYTICAL_REPORT.md` names an open
high-batch question the anchor cannot settle. If a ROM cell both stores its bits
and performs the multiply for them -- compute-in-ROM, as Taalas
describes HC1 -- then a second concurrent stream needs a second pass
through the fabric, and **aggregate per-die throughput equals per-user
throughput at every batch**. If instead the ROM is storage feeding a
separate MAC array, one sweep serves the whole batch exactly as one HBM
fetch does on a GPU. Their sweep counts coincide at batch 1, but
their cell size and pre-compute reservation give them different
floorplans; the current compute-in-ROM anchor reconstruction is
capacity-infeasible. A batch-1 rate therefore cannot validate the
distinct high-batch scaling laws.

Every other table in this report uses the batched (ROM-as-storage)
machine; `-perstream` is compute-in-ROM with a global activation broadcast and `-perregion` gives each expert region its own port
variant.

The third column set is the per-region machine, which is the whole
subject of `docs/ANALYTICAL_REPORT.md`: its sweep depth
is the load of the **busiest** expert region, computed from the routing
distribution rather than from the mean engaged region.

| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | Per-region aggregate | Per-stream penalty | Per-region over broadcast | Batched binds on | Per-stream binds on | Per-region binds on |
|---|---:|---|---:|---:|---:|---:|---:|---|---|---|
| DeepSeek-V4-Pro-0813 | 1 | sram | 472,839.1 | 25,026.1 | 25,026.1 | 18.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 472,839.1 | 25,026.1 | 25,026.1 | 18.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 472,839.1 | 25,026.1 | 25,026.1 | 18.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 472,839.1 | 25,026.1 | 25,026.1 | 18.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 472,839.1 | 25,026.1 | 25,026.1 | 18.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 472,839.1 | 25,026.1 | 32,812.7 | 18.89x | 1.31x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 472,839.1 | 25,026.1 | 55,266.9 | 18.89x | 2.21x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 472,839.1 | 25,944.0 | 138,461.9 | 18.23x | 5.34x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 908,792.0 | 26,113.2 | 266,194.8 | 34.80x | 10.19x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 1,597,407.2 | 26,113.2 | 426,343.8 | 61.17x | 16.33x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 896,033.2 | 36,918.8 | 36,918.8 | 24.27x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 896,033.2 | 36,918.8 | 36,918.8 | 24.27x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 896,033.2 | 36,918.8 | 36,918.8 | 24.27x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 896,033.2 | 36,918.8 | 36,918.8 | 24.27x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 896,033.2 | 36,918.8 | 36,918.8 | 24.27x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 896,033.2 | 36,918.8 | 37,323.7 | 24.27x | 1.01x | compute | weight_read | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | rom | 896,033.2 | 36,918.8 | 64,748.9 | 24.27x | 1.75x | compute | weight_read | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 256 | rom | 896,033.2 | 39,052.2 | 165,046.8 | 22.94x | 4.23x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 1,036,594.3 | 39,993.4 | 320,414.1 | 25.92x | 8.01x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 1,343,111.9 | 39,993.4 | 507,351.7 | 33.58x | 12.69x | compute | weight_read | weight_read |

## The floorplan sweep: where the recovered silicon goes

Compute-in-ROM has no MAC array, so it recovers that silicon.
What it is spent on decides the comparison, so it is swept
rather than assumed, and **the same sweep is offered to the
amortising machine** -- offering it to one side only would move
the artefact rather than remove it.

* `sram` sizes the array to the stored bytes. Compute-in-ROM's
  spare silicon becomes KV store, which is the split Taalas
  describes; the amortising machine's becomes MAC array.
* `rom` grows the array into that silicon as **replicated copies
  of the same weights**. R copies carry R sets of bitlines and
  sense amps, so R disjoint slices of the weight set are read at
  once and the sweep time falls by R. On the amortising machine
  the MAC array is then sized to consume exactly what the array
  can read, at one weight byte per multiply-accumulate -- a
  derived split, not a swept one.

`R` is the replication factor the design ended up with, which is
`weight_capacity / stored`. **Areas differ down this table**, so
read `tok/s/mm2` and not only aggregate: a design is allowed to
buy throughput with silicon here, and the iso-area table above is
where that is controlled for.

| Model | B | Amortisation | Spare | Design | mm2 | R | Sweeps | Aggregate | tok/s/mm2 | Binds on | vs ROM+MAC/sram |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---:|
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 472,839.1 | 0.852 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 896,033.2 | 1.615 | compute | 1.90x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 472,839.1 | 0.852 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 896,033.2 | 1.615 | compute | 1.90x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 472,839.1 | 0.852 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 896,033.2 | 1.615 | compute | 1.90x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 472,839.1 | 0.852 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 896,033.2 | 1.615 | compute | 1.90x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 472,839.1 | 0.852 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 896,033.2 | 1.615 | compute | 1.90x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 472,839.1 | 0.852 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 896,033.2 | 1.615 | compute | 1.90x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.43 | 32,812.7 | 0.355 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.53 | 1.43 | 37,323.7 | 0.404 | layer_fixed_latency | 0.08x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 472,839.1 | 0.852 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 896,033.2 | 1.615 | compute | 1.90x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,026.1 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 1.00 | 36,918.8 | 0.399 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.99 | 55,266.9 | 0.598 | weight_read | 0.12x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.53 | 1.99 | 64,748.9 | 0.700 | layer_fixed_latency | 0.14x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 472,839.1 | 0.852 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 896,033.2 | 1.615 | compute | 1.90x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 2.25 | 25,944.0 | 0.281 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 2.25 | 39,052.2 | 0.422 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.49 | 138,461.9 | 1.498 | weight_read | 0.29x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.53 | 2.62 | 165,046.8 | 1.785 | weight_read | 0.35x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 908,792.0 | 2.458 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 1,036,594.3 | 1.869 | compute | 1.14x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 8.98 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 8.98 | 39,993.4 | 0.433 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 5.09 | 266,194.8 | 2.879 | weight_read | 0.29x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.53 | 3.65 | 320,414.1 | 3.466 | weight_read | 0.35x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,597,407.2 | 2.880 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 1,343,111.9 | 2.421 | compute | 0.84x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x81-perstream | 66,015 | 1.00 | 50.57 | 26,113.2 | 0.396 | weight_read | 0.02x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.53 | 35.93 | 39,993.4 | 0.433 | weight_read | 0.03x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 7.62 | 426,343.8 | 4.612 | weight_read | 0.27x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.53 | 5.24 | 507,351.7 | 5.488 | weight_read | 0.32x |

## What the completeness corrections cost

Four terms the model priced wrongly or not at all. Each row is
computed from the evaluated points, not restated from prose.

### 1. Per-region sweep depth: the busiest region, not the mean

The compute-in-ROM per-region machine used to charge `batch * k /
(N * coverage)` -- the load of the AVERAGE engaged region -- and then
divide it by a flat 0.85 whose own note said the depth is set by the
busiest region. The busiest region is now computed from the routing
distribution. The correction is not a constant: it is a function of
how many users one array pass actually serves.

**Read the `Users per slot` column, not the batch.** Since per-user
latency was separated from aggregate throughput, a machine cut into
`token_slots` slots spreads its batch across them, and the region
collisions this correction is about happen inside **one** slot. Where
the design the sweep chose has more slots than the batch has users, one
pass serves one user, no two tokens can collide on a region, and the
correction is 1.00x by construction rather than by accident. The
statistic itself is unchanged and is checked against a Monte Carlo of
the routing in `tests/test_roofline.py`; what moved is which point on it
these designs sit at.

| Model | B | Slots | Users per slot | Mean engaged region | Busiest region | Correction |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 74 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 74 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 74 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 81 | 3.16 | 1.017 | 1.274 | 1.25x |
| DeepSeek-V4-Pro-0813 | 1024 | 81 | 12.64 | 1.094 | 2.301 | 2.10x |
| DeepSeek-V4-Pro-0813 | 4096 | 81 | 50.57 | 1.439 | 4.371 | 3.04x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Pro-0813 | 2 | 14 | 8.21 | 4.62 | 1.78x |
| DeepSeek-V4-Pro-0813 | 4 | 14 | 11.54 | 5.81 | 1.99x |
| DeepSeek-V4-Pro-0813 | 8 | 14 | 13.52 | 7.04 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 14 | 13.98 | 8.20 | 1.71x |
| DeepSeek-V4-Pro-0813 | 32 | 14 | 14.00 | 9.19 | 1.52x |
| DeepSeek-V4-Pro-0813 | 64 | 14 | 14.00 | 9.93 | 1.41x |
| DeepSeek-V4-Pro-0813 | 256 | 14 | 14.00 | 10.55 | 1.33x |
| DeepSeek-V4-Pro-0813 | 1024 | 14 | 14.00 | 10.57 | 1.32x |
| DeepSeek-V4-Pro-0813 | 4096 | 14 | 14.00 | 10.57 | 1.32x |
| DeepSeek-V4-Pro-0813 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4-Pro-0813 | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4-Pro-0813 | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4-Pro-0813 | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4-Pro-0813 | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4-Pro-0813 | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4-Pro-0813 | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4-Pro-0813 | 4096 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4-Pro-0813 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 2 | 38 | 10.34 | 6.29 | 1.64x |
| DeepSeek-V4-Pro-0813 | 4 | 38 | 17.66 | 8.67 | 2.04x |
| DeepSeek-V4-Pro-0813 | 8 | 38 | 26.69 | 11.45 | 2.33x |
| DeepSeek-V4-Pro-0813 | 16 | 38 | 34.12 | 14.46 | 2.36x |
| DeepSeek-V4-Pro-0813 | 32 | 38 | 37.34 | 17.39 | 2.15x |
| DeepSeek-V4-Pro-0813 | 64 | 38 | 37.94 | 19.83 | 1.91x |
| DeepSeek-V4-Pro-0813 | 256 | 38 | 38.00 | 22.03 | 1.72x |
| DeepSeek-V4-Pro-0813 | 1024 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4-Pro-0813 | 4096 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4-Pro-0813 | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Pro-0813 | 2 | 41 | 10.44 | 6.42 | 1.63x |
| DeepSeek-V4-Pro-0813 | 4 | 41 | 18.02 | 8.90 | 2.02x |
| DeepSeek-V4-Pro-0813 | 8 | 41 | 27.65 | 11.82 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 41 | 36.04 | 15.02 | 2.40x |
| DeepSeek-V4-Pro-0813 | 32 | 41 | 40.04 | 18.16 | 2.20x |
| DeepSeek-V4-Pro-0813 | 64 | 41 | 40.90 | 20.80 | 1.97x |
| DeepSeek-V4-Pro-0813 | 256 | 41 | 41.00 | 23.19 | 1.77x |
| DeepSeek-V4-Pro-0813 | 1024 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4-Pro-0813 | 4096 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4-Pro-0813 | 1 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Pro-0813 | 2 | 42 | 10.48 | 6.46 | 1.62x |
| DeepSeek-V4-Pro-0813 | 4 | 42 | 18.13 | 8.97 | 2.02x |
| DeepSeek-V4-Pro-0813 | 8 | 42 | 27.95 | 11.94 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 42 | 36.65 | 15.20 | 2.41x |
| DeepSeek-V4-Pro-0813 | 32 | 42 | 40.92 | 18.41 | 2.22x |
| DeepSeek-V4-Pro-0813 | 64 | 42 | 41.88 | 21.11 | 1.98x |
| DeepSeek-V4-Pro-0813 | 256 | 42 | 42.00 | 23.57 | 1.78x |
| DeepSeek-V4-Pro-0813 | 1024 | 42 | 42.00 | 23.67 | 1.77x |
| DeepSeek-V4-Pro-0813 | 4096 | 42 | 42.00 | 23.67 | 1.77x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4-Pro-0813 | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4-Pro-0813 | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4-Pro-0813 | 1 | 74 | 5.80 | 5.09 | 1.14x |
| DeepSeek-V4-Pro-0813 | 2 | 74 | 11.07 | 7.49 | 1.48x |
| DeepSeek-V4-Pro-0813 | 4 | 74 | 20.21 | 10.59 | 1.91x |
| DeepSeek-V4-Pro-0813 | 8 | 74 | 34.13 | 14.78 | 2.31x |
| DeepSeek-V4-Pro-0813 | 16 | 74 | 50.89 | 19.67 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 74 | 64.65 | 24.79 | 2.61x |
| DeepSeek-V4-Pro-0813 | 64 | 74 | 71.32 | 29.36 | 2.43x |
| DeepSeek-V4-Pro-0813 | 256 | 74 | 73.56 | 33.74 | 2.18x |
| DeepSeek-V4-Pro-0813 | 1024 | 74 | 73.60 | 33.92 | 2.17x |
| DeepSeek-V4-Pro-0813 | 4096 | 74 | 73.60 | 33.92 | 2.17x |
| DeepSeek-V4-Pro-0813 | 1 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 79 | 11.12 | 7.61 | 1.46x |
| DeepSeek-V4-Pro-0813 | 4 | 79 | 20.40 | 10.76 | 1.89x |
| DeepSeek-V4-Pro-0813 | 8 | 79 | 34.73 | 15.12 | 2.30x |
| DeepSeek-V4-Pro-0813 | 16 | 79 | 52.43 | 20.21 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 79 | 67.61 | 25.59 | 2.64x |
| DeepSeek-V4-Pro-0813 | 64 | 79 | 75.46 | 30.42 | 2.48x |
| DeepSeek-V4-Pro-0813 | 256 | 79 | 78.35 | 35.08 | 2.23x |
| DeepSeek-V4-Pro-0813 | 1024 | 79 | 78.41 | 35.27 | 2.22x |
| DeepSeek-V4-Pro-0813 | 4096 | 79 | 78.41 | 35.27 | 2.22x |
| DeepSeek-V4-Pro-0813 | 1 | 80 | 5.82 | 5.14 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 80 | 11.13 | 7.64 | 1.46x |
| DeepSeek-V4-Pro-0813 | 4 | 80 | 20.43 | 10.80 | 1.89x |
| DeepSeek-V4-Pro-0813 | 8 | 80 | 34.84 | 15.19 | 2.29x |
| DeepSeek-V4-Pro-0813 | 16 | 80 | 52.72 | 20.32 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 80 | 68.18 | 25.75 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 80 | 76.28 | 30.63 | 2.49x |
| DeepSeek-V4-Pro-0813 | 256 | 80 | 79.30 | 35.34 | 2.24x |
| DeepSeek-V4-Pro-0813 | 1024 | 80 | 79.36 | 35.53 | 2.23x |
| DeepSeek-V4-Pro-0813 | 4096 | 80 | 79.36 | 35.53 | 2.23x |
| DeepSeek-V4-Pro-0813 | 1 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 83 | 11.15 | 7.71 | 1.45x |
| DeepSeek-V4-Pro-0813 | 4 | 83 | 20.53 | 10.90 | 1.88x |
| DeepSeek-V4-Pro-0813 | 8 | 83 | 35.16 | 15.38 | 2.29x |
| DeepSeek-V4-Pro-0813 | 16 | 83 | 53.57 | 20.63 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 83 | 69.85 | 26.20 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 83 | 78.68 | 31.24 | 2.52x |
| DeepSeek-V4-Pro-0813 | 256 | 83 | 82.14 | 36.11 | 2.27x |
| DeepSeek-V4-Pro-0813 | 1024 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4-Pro-0813 | 4096 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4-Pro-0813 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4-Pro-0813 | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4-Pro-0813 | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4-Pro-0813 | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4-Pro-0813 | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4-Pro-0813 | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4-Pro-0813 | 1 | 90 | 5.84 | 5.22 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 90 | 11.21 | 7.86 | 1.43x |
| DeepSeek-V4-Pro-0813 | 4 | 90 | 20.74 | 11.11 | 1.87x |
| DeepSeek-V4-Pro-0813 | 8 | 90 | 35.84 | 15.82 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 90 | 55.39 | 21.32 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 90 | 73.53 | 27.22 | 2.70x |
| DeepSeek-V4-Pro-0813 | 64 | 90 | 84.10 | 32.60 | 2.58x |
| DeepSeek-V4-Pro-0813 | 256 | 90 | 88.67 | 37.84 | 2.34x |
| DeepSeek-V4-Pro-0813 | 1024 | 90 | 88.77 | 38.06 | 2.33x |
| DeepSeek-V4-Pro-0813 | 4096 | 90 | 88.77 | 38.06 | 2.33x |
| DeepSeek-V4-Pro-0813 | 1 | 91 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 91 | 11.22 | 7.88 | 1.42x |
| DeepSeek-V4-Pro-0813 | 4 | 91 | 20.77 | 11.14 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 91 | 35.93 | 15.88 | 2.26x |
| DeepSeek-V4-Pro-0813 | 16 | 91 | 55.63 | 21.42 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 91 | 74.03 | 27.36 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 91 | 84.85 | 32.79 | 2.59x |
| DeepSeek-V4-Pro-0813 | 256 | 91 | 89.59 | 38.08 | 2.35x |
| DeepSeek-V4-Pro-0813 | 1024 | 91 | 89.69 | 38.30 | 2.34x |
| DeepSeek-V4-Pro-0813 | 4096 | 91 | 89.69 | 38.30 | 2.34x |
| DeepSeek-V4-Pro-0813 | 1 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 92 | 11.23 | 7.90 | 1.42x |
| DeepSeek-V4-Pro-0813 | 4 | 92 | 20.79 | 11.17 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 92 | 36.02 | 15.94 | 2.26x |
| DeepSeek-V4-Pro-0813 | 16 | 92 | 55.87 | 21.51 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 92 | 74.53 | 27.50 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 92 | 85.60 | 32.97 | 2.60x |
| DeepSeek-V4-Pro-0813 | 256 | 92 | 90.51 | 38.32 | 2.36x |
| DeepSeek-V4-Pro-0813 | 1024 | 92 | 90.62 | 38.54 | 2.35x |
| DeepSeek-V4-Pro-0813 | 4096 | 92 | 90.62 | 38.54 | 2.35x |
| DeepSeek-V4-Pro-0813 | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 98 | 11.27 | 8.02 | 1.40x |
| DeepSeek-V4-Pro-0813 | 4 | 98 | 20.94 | 11.34 | 1.85x |
| DeepSeek-V4-Pro-0813 | 8 | 98 | 36.52 | 16.28 | 2.24x |
| DeepSeek-V4-Pro-0813 | 16 | 98 | 57.24 | 22.06 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 98 | 77.39 | 28.31 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 98 | 89.96 | 34.06 | 2.64x |
| DeepSeek-V4-Pro-0813 | 256 | 98 | 95.95 | 39.72 | 2.42x |
| DeepSeek-V4-Pro-0813 | 1024 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4-Pro-0813 | 4096 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4-Pro-0813 | 1 | 100 | 5.85 | 5.28 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 100 | 11.28 | 8.06 | 1.40x |
| DeepSeek-V4-Pro-0813 | 4 | 100 | 20.99 | 11.39 | 1.84x |
| DeepSeek-V4-Pro-0813 | 8 | 100 | 36.67 | 16.39 | 2.24x |
| DeepSeek-V4-Pro-0813 | 16 | 100 | 57.67 | 22.23 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 100 | 78.30 | 28.57 | 2.74x |
| DeepSeek-V4-Pro-0813 | 64 | 100 | 91.38 | 34.42 | 2.66x |
| DeepSeek-V4-Pro-0813 | 256 | 100 | 97.74 | 40.17 | 2.43x |
| DeepSeek-V4-Pro-0813 | 1024 | 100 | 97.89 | 40.41 | 2.42x |
| DeepSeek-V4-Pro-0813 | 4096 | 100 | 97.89 | 40.41 | 2.42x |
| DeepSeek-V4-Pro-0813 | 1 | 101 | 5.85 | 5.29 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 101 | 11.28 | 8.08 | 1.40x |
| DeepSeek-V4-Pro-0813 | 4 | 101 | 21.01 | 11.42 | 1.84x |
| DeepSeek-V4-Pro-0813 | 8 | 101 | 36.75 | 16.45 | 2.23x |
| DeepSeek-V4-Pro-0813 | 16 | 101 | 57.88 | 22.32 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 101 | 78.74 | 28.70 | 2.74x |
| DeepSeek-V4-Pro-0813 | 64 | 101 | 92.08 | 34.59 | 2.66x |
| DeepSeek-V4-Pro-0813 | 256 | 101 | 98.63 | 40.39 | 2.44x |
| DeepSeek-V4-Pro-0813 | 1024 | 101 | 98.79 | 40.64 | 2.43x |
| DeepSeek-V4-Pro-0813 | 4096 | 101 | 98.79 | 40.64 | 2.43x |
| DeepSeek-V4-Pro-0813 | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 110 | 11.33 | 8.24 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 110 | 21.20 | 11.65 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 110 | 37.37 | 16.92 | 2.21x |
| DeepSeek-V4-Pro-0813 | 16 | 110 | 59.63 | 23.06 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 110 | 82.55 | 29.82 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 110 | 98.14 | 36.10 | 2.72x |
| DeepSeek-V4-Pro-0813 | 256 | 110 | 106.49 | 42.35 | 2.51x |
| DeepSeek-V4-Pro-0813 | 1024 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4-Pro-0813 | 4096 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4-Pro-0813 | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4-Pro-0813 | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4-Pro-0813 | 1 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 118 | 11.37 | 8.38 | 1.36x |
| DeepSeek-V4-Pro-0813 | 4 | 118 | 21.34 | 11.84 | 1.80x |
| DeepSeek-V4-Pro-0813 | 8 | 118 | 37.86 | 17.30 | 2.19x |
| DeepSeek-V4-Pro-0813 | 16 | 118 | 61.02 | 23.67 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 118 | 85.64 | 30.75 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 118 | 103.19 | 37.37 | 2.76x |
| DeepSeek-V4-Pro-0813 | 256 | 118 | 113.24 | 43.99 | 2.57x |
| DeepSeek-V4-Pro-0813 | 1024 | 118 | 113.51 | 44.27 | 2.56x |
| DeepSeek-V4-Pro-0813 | 4096 | 118 | 113.51 | 44.27 | 2.56x |
| DeepSeek-V4-Pro-0813 | 1 | 121 | 5.88 | 5.39 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 121 | 11.38 | 8.43 | 1.35x |
| DeepSeek-V4-Pro-0813 | 4 | 121 | 21.39 | 11.90 | 1.80x |
| DeepSeek-V4-Pro-0813 | 8 | 121 | 38.02 | 17.44 | 2.18x |
| DeepSeek-V4-Pro-0813 | 16 | 121 | 61.50 | 23.88 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 121 | 86.73 | 31.09 | 2.79x |
| DeepSeek-V4-Pro-0813 | 64 | 121 | 105.01 | 37.83 | 2.78x |
| DeepSeek-V4-Pro-0813 | 256 | 121 | 115.71 | 44.59 | 2.59x |
| DeepSeek-V4-Pro-0813 | 1024 | 121 | 116.00 | 44.88 | 2.58x |
| DeepSeek-V4-Pro-0813 | 4096 | 121 | 116.00 | 44.88 | 2.58x |
| DeepSeek-V4-Pro-0813 | 1 | 132 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 132 | 11.43 | 8.59 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 132 | 21.55 | 12.15 | 1.77x |
| DeepSeek-V4-Pro-0813 | 8 | 132 | 38.58 | 17.92 | 2.15x |
| DeepSeek-V4-Pro-0813 | 16 | 132 | 63.12 | 24.63 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 132 | 90.45 | 32.25 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 132 | 111.33 | 39.45 | 2.82x |
| DeepSeek-V4-Pro-0813 | 256 | 132 | 124.50 | 46.70 | 2.67x |
| DeepSeek-V4-Pro-0813 | 1024 | 132 | 124.88 | 47.00 | 2.66x |
| DeepSeek-V4-Pro-0813 | 4096 | 132 | 124.88 | 47.00 | 2.66x |
| DeepSeek-V4-Pro-0813 | 1 | 137 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 137 | 11.44 | 8.66 | 1.32x |
| DeepSeek-V4-Pro-0813 | 4 | 137 | 21.62 | 12.25 | 1.76x |
| DeepSeek-V4-Pro-0813 | 8 | 137 | 38.80 | 18.11 | 2.14x |
| DeepSeek-V4-Pro-0813 | 16 | 137 | 63.79 | 24.94 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 137 | 92.01 | 32.75 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 137 | 114.04 | 40.14 | 2.84x |
| DeepSeek-V4-Pro-0813 | 256 | 137 | 128.36 | 47.61 | 2.70x |
| DeepSeek-V4-Pro-0813 | 1024 | 137 | 128.78 | 47.93 | 2.69x |
| DeepSeek-V4-Pro-0813 | 4096 | 137 | 128.78 | 47.93 | 2.69x |
| DeepSeek-V4-Pro-0813 | 1 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 144 | 11.47 | 8.75 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 144 | 21.70 | 12.39 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 144 | 39.10 | 18.38 | 2.13x |
| DeepSeek-V4-Pro-0813 | 16 | 144 | 64.66 | 25.37 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 144 | 94.08 | 33.43 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 144 | 117.67 | 41.09 | 2.86x |
| DeepSeek-V4-Pro-0813 | 256 | 144 | 133.60 | 48.85 | 2.73x |
| DeepSeek-V4-Pro-0813 | 1024 | 144 | 134.09 | 49.19 | 2.73x |
| DeepSeek-V4-Pro-0813 | 4096 | 144 | 134.09 | 49.19 | 2.73x |
| DeepSeek-V4-Pro-0813 | 1 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 146 | 11.47 | 8.78 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 146 | 21.73 | 12.43 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 146 | 39.17 | 18.45 | 2.12x |
| DeepSeek-V4-Pro-0813 | 16 | 146 | 64.89 | 25.48 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 146 | 94.64 | 33.61 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 146 | 118.68 | 41.35 | 2.87x |
| DeepSeek-V4-Pro-0813 | 256 | 146 | 135.07 | 49.20 | 2.75x |
| DeepSeek-V4-Pro-0813 | 1024 | 146 | 135.57 | 49.54 | 2.74x |
| DeepSeek-V4-Pro-0813 | 4096 | 146 | 135.57 | 49.54 | 2.74x |
| DeepSeek-V4-Pro-0813 | 1 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 157 | 11.50 | 8.91 | 1.29x |
| DeepSeek-V4-Pro-0813 | 4 | 157 | 21.84 | 12.64 | 1.73x |
| DeepSeek-V4-Pro-0813 | 8 | 157 | 39.58 | 18.83 | 2.10x |
| DeepSeek-V4-Pro-0813 | 16 | 157 | 66.10 | 26.10 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 157 | 97.56 | 34.60 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 157 | 123.95 | 42.74 | 2.90x |
| DeepSeek-V4-Pro-0813 | 256 | 157 | 142.90 | 51.05 | 2.80x |
| DeepSeek-V4-Pro-0813 | 1024 | 157 | 143.50 | 51.41 | 2.79x |
| DeepSeek-V4-Pro-0813 | 4096 | 157 | 143.50 | 51.41 | 2.79x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4-Pro-0813 | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4-Pro-0813 | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 347 | 11.72 | 10.18 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 347 | 22.70 | 15.30 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 347 | 42.66 | 22.28 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 347 | 75.90 | 33.59 | 2.26x |
| DeepSeek-V4-Pro-0813 | 32 | 347 | 123.23 | 45.96 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 347 | 175.33 | 59.00 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 347 | 230.16 | 73.28 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 347 | 232.44 | 73.90 | 3.15x |

### 3. The per-layer serial cost, and who pays it

Before this term the only latency in the model was
`links.*.hop_latency_s`, charged at inter-partition boundaries -- so
a `single_chip` design had a decode step with no fixed cost at all.
**The asymmetry is the finding and it runs against the ROM thesis:**
a ROM step is tens of microseconds over 32-61 layers while a GPU step
for the same model is milliseconds, so the same per-layer floor is a
large fraction of one and a rounding error on the other.

| Family | Model | B | Fixed latency (us) | Share of the fastest step |
|---|---|---:|---:|---:|
| gpu | DeepSeek-V4-Pro-0813 | 1 | 1,259.70 | 53.2% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 472.87 | 89.5% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4-Pro-0813 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Pro-0813 | hbm | interleaved | 32 B | 1.00x |

### 5. The SRAM KV path, which is still never exercised

A reported bound rather than a correction. The step credits ONE user
with the whole array's read bandwidth. That is defensible for KV in a
way it is not for ROM -- KV is written at run time and can be striped
across every bank, whereas an expert's weights live where they were
masked -- but it holds only if the design really stripes, and nothing
in the model checks. The bound below is what the same read costs if a
user can draw only the banks its own footprint occupies.

| Model | B | Devices | Bank occupancy | KV read as charged (us) | Under bank locality (us) |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 74 | 16.22% | 37.21 | 3.10 |
| DeepSeek-V4-Pro-0813 | 2 | 74 | 16.22% | 37.21 | 3.10 |
| DeepSeek-V4-Pro-0813 | 4 | 74 | 16.22% | 37.21 | 3.10 |
| DeepSeek-V4-Pro-0813 | 8 | 2 | 0.41% | 1.43 | 3.10 |
| DeepSeek-V4-Pro-0813 | 16 | 2 | 0.41% | 1.43 | 3.10 |
| DeepSeek-V4-Pro-0813 | 32 | 2 | 0.41% | 1.43 | 3.10 |
| DeepSeek-V4-Pro-0813 | 64 | 2 | 0.41% | 1.43 | 3.10 |

## Sparse-MoE engagement on a ROM machine

Expected distinct experts touched by a batch is `1 - (1 - k/N)^B`, so the
bytes a step engages grow with batch while the ROM full-array sweep time
does not: an unselected expert's read ports cannot be borrowed, and a
selected one is read once however many batch members chose it. **MoE
sparsity on a ROM machine therefore converts into aggregate throughput,
not into lower per-token latency** -- which is the opposite of what it does
on an HBM machine, where bandwidth is global and sparsity directly
reduces the bytes fetched.

| Model | B | Expert coverage | Engaged weight bytes | Engaged fraction | Effective ROM read | Peak ROM read | Per-user tok/s | Aggregate tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 116.5 | 18,399.4 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 116.5 | 18,399.4 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 116.5 | 18,399.4 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 116.5 | 18,399.4 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 116.5 | 18,399.4 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 116.5 | 18,399.4 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 116.5 | 18,399.4 |
| DeepSeek-V4-Pro-0813 | 256 | 2.52% | 47.5 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 72.8 | 18,625.6 |
| DeepSeek-V4-Pro-0813 | 1024 | 9.70% | 106.6 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 18.4 | 18,887.3 |
| DeepSeek-V4-Pro-0813 | 4096 | 33.52% | 302.4 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 4.6 | 18,934.0 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | layer_fixed_latency | 377 |
| gpu | link_latency | 1135 |
| gpu | thermal | 59 |
| gpu | weight_read | 399 |
| rom | compute | 685 |
| rom | infeasible | 1722 |
| rom | kv_read | 24 |
| rom | layer_fixed_latency | 422 |
| rom | link_latency | 931 |
| rom | weight_read | 356 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 1722 |

## Mechanical consistency audit

**FAIL** over 134,098 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x146', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x156', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x176', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x179', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x196', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x215', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x286', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x146', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x156', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x176', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x179', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x196', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x215', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x286', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x146', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x156', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x176', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x179', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x196', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x215', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x286', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x146', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x156', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x176', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x179', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x196', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x215', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x286', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x146', 'DeepSeek-V4-Pro-0813', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 48 |
| assumed | 77 |

Every `assumed` input, in full, because an ungraded assumption is the
failure mode this program exists to prevent:

- `efficiencies.compute`
- `efficiencies.expert_router_imbalance`
- `efficiencies.hbm_bandwidth`
- `efficiencies.hbm_capacity`
- `efficiencies.rom_read_bandwidth`
- `efficiencies.sram_read_bandwidth`
- `efficiencies.stage_balance`
- `energy.mac_energy_j_per_op.bf16`
- `energy.mac_energy_j_per_op.fp32`
- `energy.mac_energy_j_per_op.fp4`
- `energy.mac_energy_j_per_op.fp8`
- `energy.mac_energy_j_per_op.w4a8`
- `energy.operand_delivery_j_per_byte`
- `energy.rom_read_j_per_byte`
- `energy.sram_read_j_per_byte`
- `floorplan.interconnect_area_fraction`
- `floorplan.overhead_area_fraction`
- `hbm.hbm2e.phy_area_mm2_per_stack`
- `hbm.hbm2e.stack_beachfront_mm`
- `hbm.hbm3e.phy_area_mm2_per_stack`
- `hbm.hbm3e.stack_beachfront_mm`
- `kv.access_granularity_bytes.sram`
- `kv.index_layout`
- `latency.array_pass_boundaries_per_layer`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4-Flash-0731`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4-Pro-0813`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash-engram-hbm`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash-engram-host`
- `latency.array_pass_boundaries_per_layer_by_model.Kimi-K3`
- `latency.array_pass_boundaries_per_layer_by_model.MiMo-V2.6-Flash`
- `latency.array_pass_boundaries_per_layer_by_model.MiMo-V2.6-Pro`
- `latency.array_pass_boundaries_per_layer_by_model.Qwen3-8B`
- `latency.global_wire_delay_s_per_mm`
- `latency.layer_barrier_s`
- `latency.pipeline_fill_drain_s`
- `latency.sequencer_issue_decode_s`
- `latency.sparse_index_dependency_s`
- `latency.sram_access_s`
- `links.ethernet.bytes_s`
- `links.ethernet.fabric`
- `links.ethernet.hop_latency_s`
- `links.ethernet.switch_radix`
- `links.inter_wafer.domain_size`
- `links.inter_wafer.hop_latency_s`
- `links.nvlink.hop_latency_s`
- `links.on_package.fabric`
- `links.on_package.hop_latency_s`
- `links.rom_board_serdes.fabric`
- `links.rom_board_serdes.hop_latency_s`
- `links.rom_package_ucie.domain_size`
- `links.rom_package_ucie.fabric`
- `links.rom_wafer_serdes.fabric`
- `links.rom_wafer_serdes.hop_latency_s`
- `power.clock_energy_j_per_mm2_per_cycle`
- `power.clock_region_multiplier.rom_array`
- `power.clock_region_multiplier.sram_array`
- `power.fabric_clock_hz`
- `power.gpu_logic_area_fraction`
- `power.memory_interface_idle_w_per_stack`
- `power.static_leakage_w_per_mm2.logic`
- `power.static_leakage_w_per_mm2.rom_array`
- `power.static_leakage_w_per_mm2.sram_array`
- `reference_parts.b200_sxm.clock_frequency_hz`
- `reference_parts.taalas_hc1.weight_amortization`
- `reference_parts.taalas_hc1.weight_bits_per_parameter`
- `rom.cim_cell_area_multiplier`
- `rom.cim_precompute_area_fraction`
- `rom.expert_bank_pooling`
- `serial_latency.hardware_links.rom_board_serdes`
- `serial_latency.hardware_links.rom_package_ucie`
- `serial_latency.hardware_links.rom_wafer_serdes`
- `serial_latency.rom_datapath.hbm_random_row_latency_s`
- `serial_latency.rom_datapath.rom_row_access_s`
- `serial_latency.rom_datapath.select_units_per_die`
- `serial_latency.rom_datapath.stream_area_fraction`
- `sram.array_efficiency`

## Interpretation boundary

- No mask-ROM macro has been fabricated at a leading node for this
  program. The ROM capacity density rests on an assumed cell-area ratio
  against a published SRAM bitcell, and the ROM read bandwidth density on
  a *simulated* 28 nm ROM-CIM macro scaled by published bitcell areas.
  Both are named in the evidence ledger above.
- Compute density is charged at a published GPU's whole-die roof per mm2,
  applied to a modelled design's compute-only area. Newer parts are
  denser than the A100 anchor, so this understates a 2026 design.
- Hop latencies are floors. They ignore switch contention, per-hop
  payload queueing beyond the modelled serialisation, and pipeline fill
  at batch 1. Each of those makes an array worse, never better, so the
  reported array crossovers are upper bounds.
- **Power is now enumerated, and it is close on one published part and
  2.6-3.2x low on the other.** Leakage, clock distribution, operand
  delivery and a measured clocked-idle floor are charged per mm2 per
  second whether or not a byte moves, and the HBM traffic energy is a
  measured SC 2025 figure rather than an HBM2-era model. The A100 lands
  at 1.15x of its published TDP under a saturating load; the Taalas HC1
  lands at 0.31x of its published card power. **The second one FAILS its
  gate and the failure is reported rather than tuned away.** The A100
  gate is also the weaker of the two, because the clock term inside it
  was calibrated as a fraction of a shipping GPU's TDP density -- read
  the power-gate section before quoting it. Every ROM watt and every ROM
  joule-per-token here is a LOWER BOUND by roughly the HC1 gate's
  shortfall.
- **`thermal_scale` now binds, which it never did before.** Static power
  does not fall when a step is stretched, so the coolable step time
  solves `t >= E_dynamic / (cooling_limit - P_static)` rather than
  dividing total energy by the total limit. Some designs are power-
  limited and their rates are reduced accordingly; the power-and-energy
  section names every one of them. Rates on unthrottled points are
  unchanged, so the two validation gates above are untouched by this.
- **Aggregate throughput is reported at steady state with every slot
  occupied, and fill and drain are not charged.** A request that is short
  compared with the slot count pays up to one extra traversal that this
  model does not bill, which flatters a deep pipeline. The delivered rate
  at the requested concurrency is reported separately and is not affected.
- **The weight replication a deep pipeline implies is not charged against
  capacity.** Beyond the layer count the surplus partitions hold replicas
  of a stage, and each replica needs its own copy of that stage's weights;
  the capacity check credits the machine with holding the model once. This
  favours the deepest pipelines, which are on the GPU side of this
  comparison, so correcting it would widen the ROM ratios rather than
  narrow them.
- Prefill, speculative decoding and cost are out of scope for this model.

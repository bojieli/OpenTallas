# Area-constrained roofline: n5_vs_b200-flash-32k

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Flash-0731 at 32,768 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 467x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 1 device. On the GPU side the correction reaches 203x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 14 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 29 x 815 mm2 (23,635 mm2, array, KV in SRAM) at 2,627 tok/s per user and 111 tok/s per 1,000 mm2, holding 1 session, against 15 copies of one unified HBM die at the same silicon: 1.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 46,225 mm2 of ROM silicon at 4,856 tok/s per user against 46,400 mm2 of b200_sxm-x29-tensor at 1,303 tok/s: **3.7x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 19,608. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 47.07x to it.** At 554,700 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 30.04 tok/s and the same silicon running tensor delivers 1,414 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.23x (DeepSeek-V4-Flash-0731, ROM binding on `compute`) to 25.57x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 20.8% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 661 to 20,411 tok/s, and its rate with every slot occupied from 19,819 to 20,411. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 30 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 599 us over NVLink, capping per-user decode at 1,670 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 165.6 us and cap it at 6,040 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 8 of 8 operating points and an array 0; on tokens per second per square millimetre the same points go 1 to the array and 7 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 3 of 1880 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 24.8x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 13.50x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 2.92x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 13 of 16 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 4 of 1,880 feasible points (0.2%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DSV4-Flash/b200_sxm-x2-pipeline` at batch 256 on 3,200 mm2, throttled 1.03x from 40 to 39 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 93% weight read against 92.9% weight read. The ROM sweep is not what melts it.


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

### DeepSeek-V4-Flash-0731 at 32,768 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hybrid-x29`** -- 29 x 815 mm2 reticle dies, 23,635 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **2,627.4 tok/s per user** (0.38 ms/token), binding on `link_latency`
- **111.2 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 2,627 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 1,463 W at 0.062 W/mm2, 556.9 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 15 copies of one unified HBM die -- `b200_sxm-x15-hybrid`, 24,000 mm2, area ratio 0.9848 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 23,635 | 24,000 | 0.9848 |
| user tok/s | 2,627.4 | 1,476.2 | 1.78x |
| aggregate tok/s | 2,627 | 2,952 | 0.89x |
| resident sessions | 1 | 9,793 | -- |
| J/token | 0.5569 | 2.9685 | 5.3x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 9,793 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x16-hybrid` at 25,600 mm2 and 1,510.3 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,855.8 | 105.0 | 1 | 3.73x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,855.8 | 105.0 | 1 | 3.73x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hybrid-x28` | 22,820 | 2,506.1 | 109.8 | 1 | 1.74x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 23,635 | 2,627.4 | 111.2 | 1 | 1.78x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hybrid-x29` | 23,635 | 2,627.4 | 111.2 | -- | 111.2 | ACCEPT |
| `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,855.8 | 105.0 | 98.6 | 111.2 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hybrid-x29` **<-- recommended** | 23,635 | 29 | 2,627.4 | 2,627 | 111.2 | 1 | `link_latency` | 1,463 | 556.9 | `b200_sxm-x15-hybrid` | 1.78x |
| `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 1 | 4,855.8 | 4,856 | 105.0 | 1 | `link_latency` | 3,969 | 817.4 | `b200_sxm-x29-tensor` | 3.73x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 144 | densest | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 23,635 | 2,627.4 | 111.2 | 1 |
| array | 144 | fastest | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 23,635 | 2,627.4 | 111.2 | 1 |
| array | 144 | smallest | `ROM-N5-native-SRAMKV-array-hybrid-x28` | 22,820 | 2,506.1 | 109.8 | 1 |
| wafer | 80 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,855.8 | 105.0 | 1 |
| wafer | 80 | fastest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,855.8 | 105.0 | 1 |
| wafer | 80 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,855.8 | 105.0 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 23,635 | 2,627.4 | 2,627 | 1 | 1,463 | 556.9 | `link_latency` | `b200_sxm-x15-hybrid` | 1,476.2 | 9,793 | 2,968.5 | 0.985 | 1.78x | 5.3x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,855.8 | 4,856 | 1 | 3,969 | 817.4 | `link_latency` | `b200_sxm-x29-tensor` | 1,303.0 | 19,608 | 8,987.7 | 0.996 | 3.73x | 11.0x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hybrid-x54-romfill` | 44,010 | 2,161.1 | 2,161 | 1 | 3,767 | 1,742.9 | `link_latency` | `b200_sxm-x28-tensor` | 1,298.8 | 18,907 | 8,743.1 | 0.982 | 1.66x | 5.0x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,855.8 | -- | 1 | -- | 817.4 | -- | -- | -- | -- | -- | 0.952 | 2.25x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hybrid-x31` | 25,265 | 2,627.4 | 10,509 | 13,582 | 1,987 | 189.1 | `link_latency` | `b200_sxm-x16-hybrid` | 1,510.3 | 10,494 | 3,044.5 | 0.987 | 1.74x | 16.1x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,849.3 | 9,699 | 3,768 | 4,202 | 433.2 | `link_latency` | `b200_sxm-x29-tensor` | 1,165.2 | 19,608 | 5,136.5 | 0.996 | 4.16x | 11.9x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x58-romfill` | 47,270 | 2,004.8 | 16,038 | 25,413 | 5,248 | 327.3 | `weight_read` | `b200_sxm-x30-tensor` | 1,169.5 | 20,309 | 5,270.3 | 0.985 | 1.71x | 16.1x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,849.3 | -- | 3,768 | -- | 433.2 | -- | -- | -- | -- | -- | 1.023 | 2.42x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hybrid-x31` | 25,265 | 2,627.4 | 10,509 | 13,582 | 1,987 | 189.1 | `link_latency` | `b200_sxm-x16-hybrid` | 1,230.1 | 10,494 | 1,915.2 | 0.987 | 2.14x | 10.1x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,849.3 | 19,397 | 3,768 | 4,292 | 221.3 | `link_latency` | `b200_sxm-x29-hybrid` | 1,123.0 | 19,608 | 3,450.5 | 0.996 | 4.32x | 15.6x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x58-romfill` | 47,270 | 2,004.8 | 16,038 | 25,413 | 5,248 | 327.3 | `weight_read` | `b200_sxm-x30-hybrid` | 1,134.9 | 20,309 | 3,504.0 | 0.985 | 1.77x | 10.7x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,849.3 | -- | 3,768 | -- | 221.3 | -- | -- | -- | -- | -- | 1.023 | 2.42x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | 2,365.6 | 18,925 | 16,211 | 2,862 | 151.2 | `link_latency` | `b200_sxm-x19-hybrid` | 868.5 | 12,597 | 1,629.1 | 0.992 | 2.72x | 10.8x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,849.3 | 38,794 | 3,768 | 4,470 | 115.2 | `link_latency` | `b200_sxm-x29-hybrid` | 892.1 | 19,608 | 2,199.6 | 0.996 | 5.44x | 19.1x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x58-romfill` | 47,270 | 2,004.8 | 16,038 | 25,413 | 5,248 | 327.3 | `weight_read` | `b200_sxm-x30-hybrid` | 902.2 | 20,309 | 2,232.2 | 0.985 | 2.22x | 6.8x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,849.3 | -- | 3,768 | -- | 115.2 | -- | -- | -- | -- | -- | 1.023 | 2.42x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | 2,341.6 | 37,465 | 16,211 | 3,033 | 81.0 | `link_latency` | `b200_sxm-x19-hybrid` | 646.9 | 12,597 | 1,150.0 | 0.992 | 3.62x | 14.2x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,725.1 | 75,602 | 3,768 | 4,804 | 63.5 | `link_latency` | `b200_sxm-x29-hybrid` | 686.8 | 19,608 | 1,488.1 | 0.996 | 6.88x | 23.4x |
| 16 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x58-romfill` | 47,270 | 1,992.0 | 31,872 | 25,413 | 5,396 | 169.3 | `weight_read` | `b200_sxm-x30-hybrid` | 695.8 | 20,309 | 1,507.5 | 0.985 | 2.86x | 8.9x |
| 16 | wafer reference | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,725.1 | -- | 3,768 | -- | 63.5 | -- | -- | -- | -- | -- | 1.023 | 2.37x wafer/array | -- |
| 32 | array | `ROM-N5-native-HBMKV-array-hybrid-x44` | 35,860 | 2,109.5 | 67,505 | 19,279 | 4,239 | 62.8 | `link_latency` | `b200_sxm-x22-hybrid` | 496.2 | 14,701 | 895.3 | 1.019 | 4.25x | 14.3x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 4,534.7 | 145,110 | 11,304 | 13,670 | 94.2 | `link_latency` | `b200_sxm-x87-hybrid` | 454.8 | 60,269 | 2,739.2 | 0.996 | 9.97x | 29.1x |
| 32 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 138,550 | 1,953.6 | 62,514 | 59,589 | 14,919 | 238.6 | `link_latency` | `b200_sxm-x87-hybrid` | 454.8 | 60,269 | 2,739.2 | 0.995 | 4.30x | 11.5x |
| 32 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 4,534.7 | -- | 11,304 | -- | 94.2 | -- | -- | -- | -- | -- | 0.999 | 2.32x wafer/array | -- |
| 64 | array | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 70,905 | 1,994.8 | 127,667 | 38,119 | 8,827 | 69.1 | `link_latency` | `b200_sxm-x44-hybrid` | 367.7 | 30,124 | 1,064.9 | 1.007 | 5.42x | 15.4x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,291.8 | 274,677 | 15,072 | 18,957 | 69.0 | `link_latency` | `b200_sxm-x116-hybrid` | 319.5 | 80,600 | 2,537.0 | 0.996 | 13.43x | 36.8x |
| 64 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,901.5 | 121,696 | 59,677 | 19,470 | 160.0 | `link_latency` | `b200_sxm-x116-hybrid` | 319.5 | 80,600 | 2,537.0 | 0.997 | 5.95x | 15.9x |
| 64 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,291.8 | -- | 15,072 | -- | 69.0 | -- | -- | -- | -- | -- | 1.001 | 2.26x wafer/array | -- |
| 256 | array | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 138,550 | 1,761.1 | 450,834 | 59,589 | 18,476 | 41.0 | `link_latency` | `b200_sxm-x87-hybrid` | 198.0 | 60,269 | 927.4 | 0.995 | 8.89x | 22.6x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,382.1 | 865,819 | 45,218 | 57,184 | 66.0 | `link_latency` | `b200_sxm-x347-hybrid` | 132.3 | 242,544 | 4,083.3 | 0.999 | 25.57x | 61.8x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 23,635 | array | SRAM | 1 |
| 2-16 | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | wafer | HBM | 3,768 |
| 32-256 | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | wafer | HBM | 3,768 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 30, 31, 37, 44, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 30, 31, 37, 44, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 28, 29, 34, 41, 54, 57, 81, 108, 113, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 28, 29, 34, 41, 54, 57, 81, 108, 113, 170, 227, 340 |

A wafer chosen over the array class is now compared against an array sampled at the wafer's own area and at four rungs above the array's floor; the `array @ wafer area` rows in the iso-area table above are that comparison. The curve BETWEEN rungs is still not evidence and must not be read as any.

## The overlap and serialisation rule

```
t_memory  = t_weight + t_kv        weights and KV share one memory system
t_memory  = max(t_weight, t_kv)    weights and KV are separate arrays
t_service = max(t_memory, t_compute)      on the AGGREGATE machine
t_user    = token_slots * t_service / stage_balance + t_link
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
`token_slots` is 1, and the price is two all-reduces per layer, charged in
`t_link`.

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 0.0 tok/s | 0.00x | within 2x | FAIL |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 87.6 W | 0.35x | within 2x | FAIL |

HC1 binds on `capacity_or_format`. Its component times are weight_read 61.42 us, kv_read 9.28 us, compute 61.42 us, link_latency 0.00 us, layer_fixed_latency 6.06 us.

**THE ANCHOR IS INFEASIBLE, AND THAT IS THE RESULT.** The model does not
under-predict the shipping part here -- it cannot place it. Taalas ships
this die; this model says the die cannot hold its own weights. At least one
of the constants below is therefore wrong, and the gate exists to say so
rather than to be closed:

- AREA: the array needs 770.5 mm2 to hold 3,513,239,296 B but only 432.4 mm2 of 815 mm2 is left after SRAM, HBM PHY, overhead and interconnect

The candidates, in the order they should be attacked: `rom.cell_to_sram_cell_area_ratio` and `rom.array_efficiency`, whose
product is now set by one sentence in one paper about a foundry memory
compiler and which together cut ROM capacity density by 2.243x;
`rom.cim_precompute_area_fraction`, taken from a different fabricated part
with a different architecture; `rom.cim_cell_area_multiplier`, for which no
published compute-in-ROM cell exists at any node; and
`reference_parts.taalas_hc1.weight_bits_per_parameter`, whose 3.0-6.0 sweep
the vendor's own 3-bit base type sits at the bottom of. **Nothing here is
tuned to make this gate pass.** The back-derivation below is still printed,
because what each input would have to be is exactly the question a failing
gate asks:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 1.764e+11 | 1.837e+11 | 1.04x |
| Compute density (ops/s/mm2) | 1.261e+12 | 3.155e+12 | 2.50x |

The gate fails before either rate density can bind: the corrected
ROM capacity density and compute-in-ROM floorplan cannot fit the
published model in 815 mm2. The rate diagnostics remain useful --
ROM read density is 1.04x and
compute density is 2.50x
the value implied by the shipping rate -- but neither can rescue a
capacity failure. The required ROM read density remains below the SRAM
read-bandwidth density derived from Cerebras WSE-2
(5.563e+11 B/s/mm2).

### The per-layer latency band, and why the gate is not fitted

Every term in the per-layer latency block is `assumed` and carries
a stated range. Reporting the gate at one point inside a wide band
would invite the point to be read as measured, which is how a gate
becomes a one-parameter curve fit. The terms are derived from
primitives independent of this anchor -- SRAM access time,
sequencer issue and decode, pipeline fill and drain across a
dependent array-pass boundary, the layer barrier, and an on-die
wire delay over a distance taken from the floorplan -- and the gate
is evaluated at both ends.

| Per-layer latency | Value | Per token | Modelled tok/s | Ratio | Binds on |
|---|---:|---:|---:|---:|---|
| range low | 70.0 ns/layer | 2.24 us | 0.0 | 0.00x | capacity_or_format |
| range stated | 189.4 ns/layer | 6.06 us | 0.0 | 0.00x | capacity_or_format |
| range high | 894.8 ns/layer | 28.63 us | 0.0 | 0.00x | capacity_or_format |

The per-layer cost that would land the model exactly on the
published figure is **-76.7 ns/layer**. It is negative, which means no positive latency term could close the gate. The current result is decided earlier by the reported capacity failure.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 0.0 | 0.00x | capacity_or_format |
| 3.5 | 0.0 | 0.00x | capacity_or_format |
| 4.0 | 0.0 | 0.00x | capacity_or_format |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 0.0 | 0.00x | capacity_or_format |
| 1,536 | 0.0 | 0.00x | capacity_or_format |
| 2,048 | 0.0 | 0.00x | capacity_or_format |

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
| Taalas HC1 card power | 200.0-250.0 W | 87.6 W | 0.35x | FAIL |

**Where the watts come from.**

| Term | A100 at TDP | Taalas HC1 |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 3.9 W |
| KV traffic | n/a: one saturating HBM stream | 10.3 W |
| operand delivery | 0.5 W | 12.1 W |
| arithmetic | 103.0 W | 8.7 W |
| static: leakage | 31.4 W | 20.9 W |
| static: clock distribution | 99.0 W | 31.6 W |
| static: memory-interface idle | 14.0 W | 0.0 W |
| **static charged** (max of the enumeration and the measured clocked-idle floor) | 144.4 W | 52.5 W |
| **total** | 461.7 W | 87.6 W |

On HC1 the enumerated static power is 52.5 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 63.3 W | 0.25x | 0.32x |
| stated | 461.7 W | 1.15x | 87.6 W | 0.35x | 0.44x |
| high | 698.3 W | 1.75x | 374.6 W | 1.50x | 1.87x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.35x of the top of its published band, **2.86x low**, against 2.28x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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
| Taalas HC1 (modelled reconstruction) | n/a (0.005908 J/attempt) | 87.6 | 0.0 |
| A100 80GB, weight-bound gate, same model and batch | 1.465768 J/token | 359.6 | 245.3 |

No tokens-per-joule ratio is admissible for this pair: the HC1 throughput reconstruction is capacity-infeasible and delivers zero modelled tokens. Its energy cell above is the attempted-step energy inside the diagnostic power calculation, not the energy of a feasible machine. The power gate remains useful as a disclosed component check, and it is 2.3-2.9x below the shipping card's published band, but it cannot support an efficiency advantage.

**Where the remaining HC1 shortfall could live, none of it fitted.**
The ROM array is charged its stated leakage density: 2.9 W at the point
and 11.2 W at the
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

- **4 of 1,880 feasible points (0.2%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 4.
- By area class: small array (1,600-5,000 mm2) 4.
- By KV store: hbm 4.
- By batch: B=32 1, B=64 1, B=256 2.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 36% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 32 throttles too, and the worst point here is at batch 256.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 168 | 0 | 62.7% | 80.8% | 0.505 | 57% |
| gpu | small array (1,600-5,000 mm2) | 16 | 4 | 98.5% | 100.0% | 0.625 | 36% |
| gpu | wafer (>=40,000 mm2) | 384 | 0 | 46.7% | 71.9% | 0.449 | 75% |
| rom | large array (5,000-40,000 mm2) | 216 | 0 | 17.1% | 29.5% | 0.147 | 94% |
| rom | wafer (>=40,000 mm2) | 1,096 | 0 | 21.2% | 35.7% | 0.179 | 98% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DSV4-Flash/b200_sxm-x2-pipeline` | DeepSeek-V4-Flash-0731 | 256 | 3,200 | hbm | 1.032x | 2,000.0 / 2,000.0 W | 35% | 38.9 | 40.1 |
| `DSV4-Flash/b200_sxm-x2-pipeline` | DeepSeek-V4-Flash-0731 | 64 | 3,200 | hbm | 1.012x | 2,000.0 / 2,000.0 W | 35% | 69.6 | 70.4 |
| `DSV4-Flash/b200_sxm-x2-tensor` | DeepSeek-V4-Flash-0731 | 256 | 3,200 | hbm | 1.010x | 2,000.0 / 2,000.0 W | 35% | 70.0 | 70.7 |
| `DSV4-Flash/b200_sxm-x2-pipeline` | DeepSeek-V4-Flash-0731 | 32 | 3,200 | hbm | 1.000x | 2,000.0 / 2,000.0 W | 35% | 111.1 | 111.2 |

The worst point's dynamic energy is weight read 92.9%, kv read 5.3%, arithmetic 1.6%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | `DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 0.817411 | 3,969.2 | link_latency | `DSV4-Flash/b200_sxm-x29-tensor` | 8.987696 | 11,710.9 | link_latency | 11.00x |
| DeepSeek-V4-Flash-0731 | 2 | 46,225 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 0.433250 | 4,201.9 | link_latency | `DSV4-Flash/b200_sxm-x29-tensor` | 5.136460 | 11,970.3 | link_latency | 11.86x |
| DeepSeek-V4-Flash-0731 | 4 | 46,225 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 0.221259 | 4,291.8 | link_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 3.450482 | 15,499.9 | weight_read | 15.59x |
| DeepSeek-V4-Flash-0731 | 8 | 46,225 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 0.115229 | 4,470.3 | link_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 2.199551 | 15,698.4 | weight_read | 19.09x |
| DeepSeek-V4-Flash-0731 | 16 | 46,225 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 0.063542 | 4,803.8 | link_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 1.488064 | 16,351.1 | weight_read | 23.42x |
| DeepSeek-V4-Flash-0731 | 32 | 92,450 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 0.066006 | 9,546.5 | link_latency | `DSV4-Flash/b200_sxm-x58-hybrid` | 1.887731 | 28,967.7 | weight_read | 28.60x |
| DeepSeek-V4-Flash-0731 | 64 | 138,675 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 0.055382 | 14,757.1 | link_latency | `DSV4-Flash/b200_sxm-x87-hybrid` | 1.840589 | 41,613.3 | weight_read | 33.23x |
| DeepSeek-V4-Flash-0731 | 256 | 369,800 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 0.047537 | 40,558.1 | link_latency | `DSV4-Flash/b200_sxm-x231-hybrid` | 2.420745 | 98,563.6 | weight_read | 50.92x |

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
| DeepSeek-V4-Flash-0731 | 32,768 | 284 B | 166.9 GB | 4.70 | 0.066 GB | 0.231 GB | 170.1 |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 21,911.6 | wafer-pipeline | 4,855.8 | wafer-tensor | 4.51x | 4,652.1 | pipeline | 1,303.0 | tensor | 3.57x | 4.71x | 3.73x | 0.79x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 30,135.6 | wafer-pipeline | 4,671.2 | wafer-hybrid | 6.45x | 5,065.5 | pipeline | 1,358.1 | tensor | 3.73x | 5.95x | 3.44x | 0.58x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 35,713.7 | wafer-pipeline | 4,563.6 | wafer-hybrid | 7.83x | 5,423.0 | pipeline | 1,379.8 | tensor | 3.93x | 6.59x | 3.31x | 0.50x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 39,354.5 | wafer-pipeline | 4,460.8 | wafer-hybrid | 8.82x | 5,627.8 | pipeline | 1,390.7 | tensor | 4.05x | 6.99x | 3.21x | 0.46x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 43,820.7 | wafer-pipeline | 4,268.4 | wafer-hybrid | 10.27x | 5,851.1 | pipeline | 1,402.2 | tensor | 4.17x | 7.49x | 3.04x | 0.41x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 46,456.2 | wafer-pipeline | 4,091.9 | wafer-hybrid | 11.35x | 5,974.4 | pipeline | 1,408.2 | tensor | 4.24x | 7.78x | 2.91x | 0.37x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 49,357.0 | wafer-pipeline | 3,774.2 | wafer-hybrid | 13.08x | 6,104.2 | pipeline | 1,414.3 | tensor | 4.32x | 8.09x | 2.67x | 0.33x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.33x to 0.79x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 4,855.8 | 4,855.8 | link_latency | DSV4-Flash/b200_sxm-x29-tensor | 46,400 | 1.00x | tensor | 589.32 | 1,303.0 | 1,303.0 | link_latency | 3.73x | 3.73x | 23.58x | 3.73x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x28 | 22,820 | 2,506.1 | 2,506.1 | link_latency | DSV4-Flash/b200_sxm-x14-hybrid | 22,400 | 1.02x | hybrid | 210.65 | 1,439.6 | 2,879.2 | weight_read | 1.74x | 0.87x | 8.35x | 1.74x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,849.3 | 9,698.6 | link_latency | DSV4-Flash/b200_sxm-x29-tensor | 46,400 | 1.00x | tensor | 623.08 | 1,165.2 | 2,330.5 | link_latency | 4.16x | 4.16x | 23.55x | 4.16x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x30 | 24,450 | 2,366.7 | 9,466.8 | link_latency | DSV4-Flash/b200_sxm-x15-hybrid | 24,000 | 1.02x | hybrid | 210.65 | 1,476.2 | 2,952.5 | weight_read | 1.60x | 3.21x | 8.14x | 1.60x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,849.3 | 19,397.3 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 215.04 | 1,123.0 | 4,492.1 | weight_read | 4.32x | 4.32x | 23.55x | 4.32x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x30 | 24,450 | 2,366.7 | 9,466.8 | link_latency | DSV4-Flash/b200_sxm-x15-hybrid | 24,000 | 1.02x | hybrid | 212.87 | 1,200.4 | 4,801.6 | weight_read | 1.97x | 1.97x | 8.14x | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,849.3 | 38,794.5 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 217.58 | 892.1 | 7,137.1 | weight_read | 5.44x | 5.44x | 23.55x | 5.44x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x30 | 24,450 | 1,612.4 | 12,899.5 | compute | DSV4-Flash/b200_sxm-x15-hybrid | 24,000 | 1.02x | hybrid | 217.30 | 923.1 | 7,385.1 | weight_read | 1.75x | 1.75x | 5.54x | 1.75x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,725.1 | 75,601.6 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 222.68 | 686.8 | 10,988.2 | weight_read | 6.88x | 6.88x | 22.95x | 6.88x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x30 | 24,450 | 984.8 | 15,756.2 | compute | DSV4-Flash/b200_sxm-x15-hybrid | 24,000 | 1.02x | hybrid | 226.18 | 670.5 | 10,728.2 | weight_read | 1.47x | 1.47x | 3.47x | 1.47x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,534.7 | 145,110.5 | link_latency | DSV4-Flash/b200_sxm-x87-hybrid | 139,200 | 1.00x | hybrid | 237.44 | 454.8 | 14,553.0 | weight_read | 9.97x | 9.97x | 46.19x | 9.97x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x30 | 24,450 | 620.6 | 19,860.2 | compute | DSV4-Flash/b200_sxm-x15-hybrid | 24,000 | 1.02x | hybrid | 243.93 | 468.3 | 14,986.8 | weight_read | 1.33x | 1.33x | 2.93x | 1.33x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,291.8 | 274,677.5 | link_latency | DSV4-Flash/b200_sxm-x116-hybrid | 185,600 | 1.00x | hybrid | 253.37 | 319.5 | 20,451.2 | weight_read | 13.43x | 13.43x | 54.85x | 13.43x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x30 | 24,450 | 315.2 | 20,171.1 | compute | DSV4-Flash/b200_sxm-x15-hybrid | 24,000 | 1.02x | hybrid | 279.43 | 327.4 | 20,954.7 | weight_read | 0.96x | 0.96x | 2.10x | 0.96x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,382.1 | 865,819.0 | link_latency | DSV4-Flash/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 343.65 | 132.3 | 33,860.8 | weight_read | 25.57x | 25.57x | 112.57x | 25.58x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x30 | 24,450 | 79.7 | 20,410.9 | compute | DSV4-Flash/b200_sxm-x15-hybrid | 24,000 | 1.02x | hybrid | 492.42 | 201.0 | 51,464.3 | weight_read | 0.40x | 0.40x | 1.17x | 0.40x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 8 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 8 | Link us at domain 72 | tok/s at 8 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 2 | 3,200 | 207.57 | 207.57 | 869.1 | 869.1 |
| DeepSeek-V4-Flash-0731 | 14 | 22,400 | 210.65 | 208.58 | 1,439.6 | 1,443.9 |
| DeepSeek-V4-Flash-0731 | 15 | 24,000 | 210.65 | 208.59 | 1,476.2 | 1,480.7 |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 210.65 | 208.60 | 1,510.3 | 1,514.9 |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 585.80 | 208.61 | 1,233.1 | 2,305.4 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 585.80 | 208.62 | 1,251.0 | 2,368.7 |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 585.80 | 208.64 | 1,266.1 | 2,423.4 |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 585.80 | 208.64 | 1,272.9 | 2,448.1 |
| DeepSeek-V4-Flash-0731 | 28 | 44,800 | 589.32 | 208.66 | 1,298.8 | 2,568.7 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 589.32 | 208.67 | 1,303.0 | 2,585.2 |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 589.32 | 208.67 | 1,307.0 | 2,600.9 |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 589.32 | 208.67 | 1,310.7 | 2,615.7 |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 589.32 | 208.67 | 1,314.3 | 2,629.9 |
| DeepSeek-V4-Flash-0731 | 41 | 65,600 | 592.84 | 208.69 | 1,333.2 | 2,732.8 |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 592.84 | 208.70 | 1,339.5 | 2,759.6 |
| DeepSeek-V4-Flash-0731 | 50 | 80,000 | 593.85 | 208.70 | 1,348.4 | 2,805.2 |
| DeepSeek-V4-Flash-0731 | 55 | 88,000 | 593.85 | 208.71 | 1,355.7 | 2,836.9 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 594.60 | 208.71 | 1,358.1 | 2,853.8 |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 594.60 | 208.71 | 1,359.3 | 2,859.0 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 596.04 | 579.01 | 1,379.8 | 1,413.0 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 597.07 | 579.01 | 1,390.7 | 1,426.5 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 597.96 | 586.06 | 1,402.2 | 1,426.0 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 598.43 | 589.58 | 1,408.2 | 1,426.0 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 598.92 | 591.69 | 1,414.3 | 1,429.0 |

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
| DeepSeek-V4-Flash-0731 | 2 | 3,200 | 533.3 | 869.1 | — | tensor | 207.57 | 18.0% | weight_read |
| DeepSeek-V4-Flash-0731 | 14 | 22,400 | 300.3 | 1,209.3 | 1,439.6 | hybrid | 210.65 | 30.3% | weight_read |
| DeepSeek-V4-Flash-0731 | 15 | 24,000 | 290.9 | 1,222.0 | 1,476.2 | hybrid | 210.65 | 31.1% | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 282.1 | 1,233.5 | 1,510.3 | hybrid | 210.65 | 31.8% | weight_read |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 273.9 | 1,233.1 | 1,158.1 | tensor | 585.80 | 72.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 259.2 | 1,251.0 | 1,206.7 | tensor | 585.80 | 73.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 246.2 | 1,266.1 | 1,249.9 | tensor | 585.80 | 74.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 240.2 | 1,272.9 | 1,269.8 | tensor | 585.80 | 74.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 28 | 44,800 | 210.1 | 1,298.8 | 1,110.6 | tensor | 589.32 | 76.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 205.9 | 1,303.0 | 1,123.0 | tensor | 589.32 | 76.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 201.9 | 1,307.0 | 1,134.9 | tensor | 589.32 | 77.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 198.0 | 1,310.7 | 1,146.3 | tensor | 589.32 | 77.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 194.3 | 1,314.3 | 1,157.3 | tensor | 589.32 | 77.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 41 | 65,600 | 166.5 | 1,333.2 | 908.4 | tensor | 592.84 | 79.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 159.1 | 1,339.5 | 926.3 | tensor | 592.84 | 79.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 50 | 80,000 | 146.3 | 1,348.4 | 846.2 | tensor | 593.85 | 80.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 55 | 88,000 | 137.1 | 1,355.7 | 866.7 | tensor | 593.85 | 80.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 132.1 | 1,358.1 | 787.0 | tensor | 594.60 | 80.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 130.6 | 1,359.3 | 790.2 | tensor | 594.60 | 80.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 98.2 | 1,379.8 | 657.0 | tensor | 596.04 | 82.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 78.2 | 1,390.7 | 527.6 | tensor | 597.07 | 83.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 56.0 | 1,402.2 | 395.5 | tensor | 597.96 | 83.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 43.5 | 1,408.2 | 316.3 | tensor | 598.43 | 84.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 30.0 | 1,414.3 | 221.0 | tensor | 598.92 | 84.7% | link_latency |

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
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x29 | DeepSeek-V4-Flash-0731 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x28 | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x29 | DeepSeek-V4-Flash-0731 | 29 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x31 | DeepSeek-V4-Flash-0731 | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.23 us | 2,549.2 tok/s | 25,492.5 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x30 | DeepSeek-V4-Flash-0731 | 30 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x31 | DeepSeek-V4-Flash-0731 | 31 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x2-pipeline | DeepSeek-V4-Flash-0731 | 2 | pipeline | nvlink5 | infiniband_ndr | 1 | 1.21 us | 82,706.0 tok/s | 827,059.9 tok/s | 1 x point_to_point span 2 on nvlink5 (traversals 1.0) = 1.21 us |
| DSV4-Flash/b200_sxm-x2-tensor | DeepSeek-V4-Flash-0731 | 2 | tensor | nvlink5 | infiniband_ndr | 86 | 207.57 us | 481.8 tok/s | 4,817.6 tok/s | 86 x all_reduce span 2 on nvlink5 (traversals 2.0) = 207.57 us |
| DSV4-Flash/b200_sxm-x14-pipeline | DeepSeek-V4-Flash-0731 | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 16.70 us | 5,986.9 tok/s | 59,869.2 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 14.51 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x14-tensor | DeepSeek-V4-Flash-0731 | 14 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x14-hybrid | DeepSeek-V4-Flash-0731 | 14 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x15-pipeline | DeepSeek-V4-Flash-0731 | 15 | pipeline | nvlink5 | infiniband_ndr | 14 | 17.91 us | 5,582.8 tok/s | 55,828.0 tok/s | 13 x point_to_point span 2 on nvlink5 (traversals 1.0) = 15.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x15-tensor | DeepSeek-V4-Flash-0731 | 15 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x15-hybrid | DeepSeek-V4-Flash-0731 | 15 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-pipeline | DeepSeek-V4-Flash-0731 | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.12 us | 5,229.8 tok/s | 52,297.8 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-tensor | DeepSeek-V4-Flash-0731 | 16 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x16-hybrid | DeepSeek-V4-Flash-0731 | 16 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x17-pipeline | DeepSeek-V4-Flash-0731 | 17 | pipeline | nvlink5 | infiniband_ndr | 16 | 21.32 us | 4,691.5 tok/s | 46,915.1 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x17-tensor | DeepSeek-V4-Flash-0731 | 17 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x17-hybrid | DeepSeek-V4-Flash-0731 | 17 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink5 | infiniband_ndr | 18 | 23.73 us | 4,213.5 tok/s | 42,134.9 tok/s | 16 x point_to_point span 2 on nvlink5 (traversals 1.0) = 19.35 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-pipeline | DeepSeek-V4-Flash-0731 | 21 | pipeline | nvlink5 | infiniband_ndr | 20 | 26.15 us | 3,823.9 tok/s | 38,238.7 tok/s | 18 x point_to_point span 2 on nvlink5 (traversals 1.0) = 21.76 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-tensor | DeepSeek-V4-Flash-0731 | 21 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x21-hybrid | DeepSeek-V4-Flash-0731 | 21 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.36 us | 3,654.9 tok/s | 36,548.9 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 22.97 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x28-pipeline | DeepSeek-V4-Flash-0731 | 28 | pipeline | nvlink5 | infiniband_ndr | 27 | 35.60 us | 2,809.0 tok/s | 28,089.9 tok/s | 24 x point_to_point span 2 on nvlink5 (traversals 1.0) = 29.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x28-tensor | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x28-hybrid | DeepSeek-V4-Flash-0731 | 28 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x29-pipeline | DeepSeek-V4-Flash-0731 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x29-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x29-hybrid | DeepSeek-V4-Flash-0731 | 29 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x30-pipeline | DeepSeek-V4-Flash-0731 | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.02 us | 2,630.3 tok/s | 26,303.2 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.44 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x30-tensor | DeepSeek-V4-Flash-0731 | 30 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x30-hybrid | DeepSeek-V4-Flash-0731 | 30 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x31-pipeline | DeepSeek-V4-Flash-0731 | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.23 us | 2,549.2 tok/s | 25,492.5 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x31-tensor | DeepSeek-V4-Flash-0731 | 31 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x31-hybrid | DeepSeek-V4-Flash-0731 | 31 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x32-pipeline | DeepSeek-V4-Flash-0731 | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.44 us | 2,473.0 tok/s | 24,730.2 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x32-tensor | DeepSeek-V4-Flash-0731 | 32 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x32-hybrid | DeepSeek-V4-Flash-0731 | 32 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x41-pipeline | DeepSeek-V4-Flash-0731 | 41 | pipeline | nvlink5 | infiniband_ndr | 40 | 53.29 us | 1,876.6 tok/s | 18,766.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.32 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x41-tensor | DeepSeek-V4-Flash-0731 | 41 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x41-hybrid | DeepSeek-V4-Flash-0731 | 41 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x44-pipeline | DeepSeek-V4-Flash-0731 | 44 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x44-tensor | DeepSeek-V4-Flash-0731 | 44 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x44-hybrid | DeepSeek-V4-Flash-0731 | 44 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x50-pipeline | DeepSeek-V4-Flash-0731 | 50 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x50-tensor | DeepSeek-V4-Flash-0731 | 50 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/b200_sxm-x50-hybrid | DeepSeek-V4-Flash-0731 | 50 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/b200_sxm-x55-pipeline | DeepSeek-V4-Flash-0731 | 55 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x55-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/b200_sxm-x55-hybrid | DeepSeek-V4-Flash-0731 | 55 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/b200_sxm-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x59-pipeline | DeepSeek-V4-Flash-0731 | 59 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x59-tensor | DeepSeek-V4-Flash-0731 | 59 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x59-hybrid | DeepSeek-V4-Flash-0731 | 59 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x87-pipeline | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x87-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5 | infiniband_ndr | 172 | 596.04 us | 167.8 tok/s | 1,677.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 387.59 us |
| DSV4-Flash/b200_sxm-x87-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.39 us | 434.0 tok/s | 4,340.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| DSV4-Flash/b200_sxm-x116-pipeline | DeepSeek-V4-Flash-0731 | 116 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x116-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5 | infiniband_ndr | 172 | 597.07 us | 167.5 tok/s | 1,674.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 388.61 us |
| DSV4-Flash/b200_sxm-x116-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.17 us | 418.1 tok/s | 4,181.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| DSV4-Flash/b200_sxm-x173-pipeline | DeepSeek-V4-Flash-0731 | 173 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x173-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5 | infiniband_ndr | 172 | 597.96 us | 167.2 tok/s | 1,672.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 389.51 us |
| DSV4-Flash/b200_sxm-x173-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5 | infiniband_ndr | 107 | 254.53 us | 392.9 tok/s | 3,928.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| DSV4-Flash/b200_sxm-x231-pipeline | DeepSeek-V4-Flash-0731 | 231 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x231-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5 | infiniband_ndr | 172 | 598.43 us | 167.1 tok/s | 1,671.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 389.97 us |
| DSV4-Flash/b200_sxm-x231-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5 | infiniband_ndr | 114 | 269.88 us | 370.5 tok/s | 3,705.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| DSV4-Flash/b200_sxm-x347-pipeline | DeepSeek-V4-Flash-0731 | 347 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x347-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5 | infiniband_ndr | 172 | 598.92 us | 167.0 tok/s | 1,669.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 390.47 us |
| DSV4-Flash/b200_sxm-x347-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5 | infiniband_ndr | 128 | 300.60 us | 332.7 tok/s | 3,326.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 42 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 92.14 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 4,855.8 | 0.105 | 2,506.1 (22,820) | 4,855.8 (46,225) | 1.94x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,849.3 | 0.105 | 2,627.4 (25,265) | 4,849.3 (46,225) | 1.85x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,849.3 | 0.105 | 2,627.4 (25,265) | 4,849.3 (46,225) | 1.85x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,849.3 | 0.105 | 2,248.3 (25,265) | 4,849.3 (46,225) | 2.16x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,725.1 | 0.102 | 2,341.6 (30,155) | 4,725.1 (46,225) | 2.02x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,519.7 | 0.049 | 2,097.9 (30,155) | 4,519.7 (92,450) | 2.15x | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,163.4 | 0.030 | 1,958.1 (35,860) | 4,163.4 (138,675) | 2.13x | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,332.8 | 0.009 | 1,761.1 (138,550) | 3,332.8 (369,800) | 1.89x | link_latency |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. The ROM-plus-MAC floorplan holds the requested weights; the compute-in-ROM floorplan holds only 87.0% and is infeasible at this area. The failed floorplan is retained so the capacity cost of the larger cell remains visible.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 374.6 mm2 | 521.6 mm2 |
| weight capacity | 3.51 GB (100.0%) | 3.06 GB (87.0%) |
| capacity-feasible | yes | **no** |
| compute block | 293.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 0.0 mm2 |
| sustained fp8 compute roof | 2.197e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.098e+14 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 8.872e+13 |
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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 98.1 mm2 | 17.65 mm2 (18.0%) | 25,105 mm2 | 4,519 mm2 | 28,467 mm2 = 34.9 reticles |

## The batch-amortisation fork, reported rather than resolved

`docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` names an open
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
subject of `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`: its sweep depth
is the load of the **busiest** expert region, computed from the routing
distribution rather than from the mean engaged region.

| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | Per-region aggregate | Per-stream penalty | Per-region over broadcast | Batched binds on | Per-stream binds on | Per-region binds on |
|---|---:|---|---:|---:|---:|---:|---:|---|---|---|
| DeepSeek-V4-Flash-0731 | 1 | sram | 28,756.4 | 28,756.4 | 28,756.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 28,756.4 | 28,756.4 | 28,756.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 28,756.4 | 28,756.4 | 28,756.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 37,663.2 | 28,756.4 | 31,812.2 | 1.31x | 1.11x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 75,326.2 | 28,756.4 | 57,695.1 | 2.62x | 2.01x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 137,632.9 | 28,756.4 | 101,040.4 | 4.79x | 3.51x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | sram | 244,945.4 | 28,784.4 | 168,901.9 | 8.51x | 5.87x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 717,864.9 | 28,956.7 | 390,776.4 | 24.79x | 13.50x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 378,264.9 | 41,602.4 | 41,602.4 | 9.09x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 378,264.9 | 41,602.4 | 41,602.4 | 9.09x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 378,264.9 | 41,602.4 | 41,602.4 | 9.09x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 378,264.9 | 41,602.4 | 41,602.4 | 9.09x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 378,264.9 | 41,602.4 | 58,186.5 | 9.09x | 1.40x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | rom | 378,264.9 | 41,602.4 | 102,094.6 | 9.09x | 2.45x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | rom | 378,264.9 | 41,602.4 | 171,039.9 | 9.09x | 4.11x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 865,819.0 | 42,332.7 | 397,601.3 | 20.45x | 9.39x | link_latency | weight_read | weight_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 13.15x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perstream-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 1.45x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perregion-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 1.45x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 13.15x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perstream-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 1.45x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perregion-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 1.45x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 13.15x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perstream-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 1.45x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perregion-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 1.45x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 37,663.2 | 0.815 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 10.04x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.76x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perstream-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.13 | 31,812.2 | 0.688 | link_latency | 0.84x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perregion-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 75,326.2 | 1.630 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 5.02x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perstream-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 0.55x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.88 | 57,695.1 | 1.248 | link_latency | 0.77x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.02 | 2.88 | 58,186.5 | 1.259 | link_latency | 0.77x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 137,632.9 | 2.977 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 2.75x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.21x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perstream-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 0.30x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.03 | 101,040.4 | 2.186 | link_latency | 0.73x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.02 | 4.03 | 102,094.6 | 2.209 | link_latency | 0.74x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 244,945.4 | 2.649 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 1.54x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,784.4 | 0.623 | weight_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perstream-romfill | 80,685 | 1.64 | 1.00 | 41,602.4 | 0.516 | weight_read | 0.17x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 5.83 | 168,901.9 | 3.654 | weight_read | 0.69x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.02 | 5.83 | 171,039.9 | 3.700 | weight_read | 0.70x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 717,864.9 | 3.882 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 14.63 | 1.00 | 865,819.0 | 1.561 | link_latency | 1.21x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,956.7 | 0.626 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x99-perstream-romfill | 80,685 | 1.64 | 2.59 | 42,332.7 | 0.525 | weight_read | 0.06x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 13.84 | 390,776.4 | 8.454 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.02 | 13.84 | 397,601.3 | 8.601 | weight_read | 0.55x |

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
| DeepSeek-V4-Flash-0731 | 1 | 55 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 55 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 61 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 61 | 1.05 | 1.001 | 1.004 | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | 61 | 4.20 | 1.038 | 1.611 | 1.55x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 2 | 1.97 | 1.63 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 2 | 1.97 | 1.63 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 2 | 2.00 | 1.72 | 1.16x |
| DeepSeek-V4-Flash-0731 | 8 | 2 | 2.00 | 1.79 | 1.12x |
| DeepSeek-V4-Flash-0731 | 16 | 2 | 2.00 | 1.84 | 1.08x |
| DeepSeek-V4-Flash-0731 | 32 | 2 | 2.00 | 1.88 | 1.06x |
| DeepSeek-V4-Flash-0731 | 64 | 2 | 2.00 | 1.91 | 1.05x |
| DeepSeek-V4-Flash-0731 | 256 | 2 | 2.00 | 1.93 | 1.04x |
| DeepSeek-V4-Flash-0731 | 1 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Flash-0731 | 2 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Flash-0731 | 4 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Flash-0731 | 8 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Flash-0731 | 16 | 14 | 5.57 | 3.75 | 1.49x |
| DeepSeek-V4-Flash-0731 | 32 | 14 | 8.86 | 4.83 | 1.83x |
| DeepSeek-V4-Flash-0731 | 64 | 14 | 12.01 | 6.02 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 14 | 13.98 | 8.29 | 1.69x |
| DeepSeek-V4-Flash-0731 | 1 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 2 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 4 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 8 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 16 | 15 | 5.35 | 3.73 | 1.44x |
| DeepSeek-V4-Flash-0731 | 32 | 15 | 8.72 | 4.84 | 1.80x |
| DeepSeek-V4-Flash-0731 | 64 | 15 | 12.26 | 6.09 | 2.01x |
| DeepSeek-V4-Flash-0731 | 256 | 15 | 14.96 | 8.55 | 1.75x |
| DeepSeek-V4-Flash-0731 | 1 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 2 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 4 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 8 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 16 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 32 | 16 | 8.56 | 4.83 | 1.77x |
| DeepSeek-V4-Flash-0731 | 64 | 16 | 12.41 | 6.15 | 2.02x |
| DeepSeek-V4-Flash-0731 | 256 | 16 | 15.91 | 8.79 | 1.81x |
| DeepSeek-V4-Flash-0731 | 1 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 2 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 4 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 8 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 16 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 32 | 17 | 8.37 | 4.82 | 1.74x |
| DeepSeek-V4-Flash-0731 | 64 | 17 | 12.48 | 6.19 | 2.02x |
| DeepSeek-V4-Flash-0731 | 256 | 17 | 16.84 | 9.01 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 7.95 | 4.78 | 1.66x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 12.44 | 6.24 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 18.57 | 9.38 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 2 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 4 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 8 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 16 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 32 | 21 | 7.52 | 4.73 | 1.59x |
| DeepSeek-V4-Flash-0731 | 64 | 21 | 12.21 | 6.25 | 1.95x |
| DeepSeek-V4-Flash-0731 | 256 | 21 | 20.09 | 9.68 | 2.07x |
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 7.31 | 4.70 | 1.55x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 12.05 | 6.25 | 1.93x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 20.76 | 9.81 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 2 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 4 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 8 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 16 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 32 | 28 | 6.17 | 4.53 | 1.36x |
| DeepSeek-V4-Flash-0731 | 64 | 28 | 10.87 | 6.12 | 1.78x |
| DeepSeek-V4-Flash-0731 | 256 | 28 | 23.44 | 10.33 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 6.01 | 4.50 | 1.34x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 10.66 | 6.08 | 1.75x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 23.69 | 10.39 | 2.28x |
| DeepSeek-V4-Flash-0731 | 1 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 4 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 8 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 16 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 32 | 30 | 5.85 | 4.46 | 1.31x |
| DeepSeek-V4-Flash-0731 | 64 | 30 | 10.45 | 6.05 | 1.73x |
| DeepSeek-V4-Flash-0731 | 256 | 30 | 23.88 | 10.44 | 2.29x |
| DeepSeek-V4-Flash-0731 | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 8 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 16 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 32 | 31 | 5.70 | 4.42 | 1.29x |
| DeepSeek-V4-Flash-0731 | 64 | 31 | 10.24 | 6.02 | 1.70x |
| DeepSeek-V4-Flash-0731 | 256 | 31 | 24.03 | 10.48 | 2.29x |
| DeepSeek-V4-Flash-0731 | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 8 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 16 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 32 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 64 | 32 | 10.04 | 5.99 | 1.68x |
| DeepSeek-V4-Flash-0731 | 256 | 32 | 24.15 | 10.52 | 2.30x |
| DeepSeek-V4-Flash-0731 | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Flash-0731 | 8 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Flash-0731 | 16 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Flash-0731 | 32 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Flash-0731 | 64 | 41 | 8.42 | 5.74 | 1.47x |
| DeepSeek-V4-Flash-0731 | 256 | 41 | 23.82 | 10.62 | 2.24x |
| DeepSeek-V4-Flash-0731 | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 8 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 16 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 32 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 64 | 44 | 7.96 | 5.66 | 1.41x |
| DeepSeek-V4-Flash-0731 | 256 | 44 | 23.39 | 10.61 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 4 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 8 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 16 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 32 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 64 | 50 | 7.16 | 5.48 | 1.31x |
| DeepSeek-V4-Flash-0731 | 256 | 50 | 22.32 | 10.54 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 4 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 8 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 16 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 32 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 64 | 55 | 6.60 | 5.32 | 1.24x |
| DeepSeek-V4-Flash-0731 | 256 | 55 | 21.34 | 10.43 | 2.05x |
| DeepSeek-V4-Flash-0731 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 4 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 8 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 16 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 32 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 64 | 58 | 6.30 | 5.21 | 1.21x |
| DeepSeek-V4-Flash-0731 | 256 | 58 | 20.74 | 10.34 | 2.01x |
| DeepSeek-V4-Flash-0731 | 1 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 4 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 8 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 16 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 32 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 64 | 59 | 6.21 | 5.17 | 1.20x |
| DeepSeek-V4-Flash-0731 | 256 | 59 | 20.54 | 10.31 | 1.99x |
| DeepSeek-V4-Flash-0731 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 8 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 16 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 32 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 64 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 256 | 87 | 15.73 | 9.34 | 1.68x |
| DeepSeek-V4-Flash-0731 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 256 | 116 | 12.40 | 8.75 | 1.42x |
| DeepSeek-V4-Flash-0731 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 4 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 8 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 16 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 32 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 64 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 256 | 173 | 8.63 | 7.48 | 1.15x |
| DeepSeek-V4-Flash-0731 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 4 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 8 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 16 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 32 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 64 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 256 | 231 | 6.56 | 6.17 | 1.06x |
| DeepSeek-V4-Flash-0731 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 347 | 5.96 | 5.77 | 1.03x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 1.9% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 6.0% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4-Flash-0731 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Flash-0731 | hbm | interleaved | 32 B | 1.00x |

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
| DeepSeek-V4-Flash-0731 | 1 | 55 | 27.01% | 39.34 | 2.65 |
| DeepSeek-V4-Flash-0731 | 2 | 55 | 27.01% | 39.34 | 2.65 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 5.35% | 8.07 | 2.65 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 5.35% | 8.07 | 2.65 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 5.35% | 8.07 | 2.65 |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 660.6 | 19,819.4 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 660.6 | 19,819.4 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 660.6 | 19,819.4 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 660.6 | 19,819.4 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 660.6 | 19,819.4 |
| DeepSeek-V4-Flash-0731 | 32 | 2.50% | 11.4 GB | 6.86% | 332.06 TB/s | 4,841.92 TB/s | 620.6 | 19,860.2 |
| DeepSeek-V4-Flash-0731 | 64 | 4.93% | 15.0 GB | 9.01% | 436.06 TB/s | 4,841.92 TB/s | 315.2 | 20,171.1 |
| DeepSeek-V4-Flash-0731 | 256 | 18.32% | 34.7 GB | 20.81% | 1,007.74 TB/s | 4,841.92 TB/s | 79.7 | 20,410.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 184 |
| gpu | thermal | 4 |
| gpu | weight_read | 380 |
| rom | compute | 59 |
| rom | infeasible | 944 |
| rom | kv_read | 3 |
| rom | link_latency | 620 |
| rom | weight_read | 630 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 944 |

## Mechanical consistency audit

**PASS** over 59,781 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 70 |
| derived | 41 |
| assumed | 57 |

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
  2.3-2.9x low on the other.** Leakage, clock distribution, operand
  delivery and a measured clocked-idle floor are charged per mm2 per
  second whether or not a byte moves, and the HBM traffic energy is a
  measured SC 2025 figure rather than an HBM2-era model. The A100 lands
  at 1.15x of its published TDP under a saturating load; the Taalas HC1
  lands at 0.35x of its published card power. **The second one FAILS its
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

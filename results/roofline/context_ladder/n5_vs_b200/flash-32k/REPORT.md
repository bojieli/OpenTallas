# Area-constrained roofline: n5_vs_b200-flash-32k

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Flash-0731 at 32,768 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 16x (ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream, 114 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 40 devices. On the GPU side the correction reaches 3x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 8 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 32 x 815 mm2 (26,080 mm2, array, KV in SRAM) at 3,241 tok/s per user and 124 tok/s per 1,000 mm2, holding 1 session, against 16 copies of one unified HBM die at the same silicon: 5.4x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 46,225 mm2 of ROM silicon at 3,548 tok/s per user against 46,400 mm2 of b200_sxm-x29-nvl72-tensor at 611 tok/s: **5.8x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 1 resident session against the GPU cluster's 19,608. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 1.60x to it.** At 94,540 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 386.97 tok/s and the same silicon running tensor delivers 619 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 6.33x (DeepSeek-V4-Flash-0731, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 958 to 34,218 tok/s, and its rate with every slot occupied from 29,707 to 34,218. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 31 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 599 us over NVLink, capping per-user decode at 1,670 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 184.6 us and cap it at 5,416 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 3 of 10 operating points and an array 7; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 40 of 4462 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 65.3x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 16.63x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 40 of 4,462 feasible points (0.9%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DSV4-Flash/b200_sxm-x7-pipeline` at batch 4096 on 11,200 mm2, throttled 1.10x from 33 to 30 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 75% weight read against 75.3% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-SRAMKV-array-hw-hybrid-x32`** -- 32 x 815 mm2 reticle dies, 26,080 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **3,240.6 tok/s per user** (0.31 ms/token), binding on `layer_fixed_latency`
- **124.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,241 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 1,616 W at 0.062 W/mm2, 498.7 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 16 copies of one unified HBM die -- `b200_sxm-x16-hybrid`, 25,600 mm2, area ratio 1.0188 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 26,080 | 25,600 | 1.0188 |
| user tok/s | 3,240.6 | 596.2 | 5.44x |
| aggregate tok/s | 3,241 | 1,192 | 0.52x |
| resident sessions | 1 | 10,494 | -- |
| J/token | 0.4987 | 10.5934 | 21.2x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 10,494 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x59-nvl72-tensor` at 94,400 mm2 and 619.1 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-hybrid-x40` | 32,600 | 3,395.9 | 104.2 | 1 | 5.64x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,548.2 | 76.8 | 1 | 5.81x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x28` | 22,820 | 2,685.1 | 117.7 | 1 | 4.54x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 26,080 | 3,240.6 | 124.3 | 1 | 5.44x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 26,080 | 3,240.6 | 124.3 | -- | 124.3 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x34` | 27,710 | 3,261.2 | 117.7 | 12.6 | 124.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x36` | 29,340 | 3,315.2 | 113.0 | 22.9 | 124.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x37` | 30,155 | 3,322.4 | 110.2 | 20.1 | 124.3 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x40` | 32,600 | 3,395.9 | 104.2 | 23.8 | 124.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x42` | 34,230 | 3,414.0 | 99.7 | 21.3 | 124.3 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 3,434.2 | 95.8 | 19.8 | 124.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x47-romfill` | 38,305 | 3,470.0 | 90.6 | 18.8 | 124.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 39,120 | 3,474.7 | 88.8 | 18.0 | 124.3 | stop |
| `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,548.2 | 76.8 | 15.3 | 124.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` **<-- recommended** | 26,080 | 32 | 3,240.6 | 3,241 | 124.3 | 1 | `layer_fixed_latency` | 1,616 | 498.7 | `b200_sxm-x16-hybrid` | 5.44x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x34` | 27,710 | 34 | 3,261.2 | 3,261 | 117.7 | 1 | `layer_fixed_latency` | 1,793 | 549.8 | `b200_sxm-x17-nvl72-tensor` | 5.46x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x36` | 29,340 | 36 | 3,315.2 | 29,837 | 113.0 | 15,773 | `layer_fixed_latency` | 2,875 | 773.2 | `b200_sxm-x18-nvl72-tensor` | 5.53x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x37` | 30,155 | 37 | 3,322.4 | 33,224 | 110.2 | 16,211 | `layer_fixed_latency` | 3,047 | 811.4 | `b200_sxm-x19-nvl72-tensor` | 5.53x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x40` | 32,600 | 40 | 3,395.9 | 3,396 | 104.2 | 1 | `layer_fixed_latency` | 2,503 | 736.9 | `b200_sxm-x20-nvl72-tensor` | 5.64x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x42` | 34,230 | 42 | 3,414.0 | 37,554 | 99.7 | 18,402 | `layer_fixed_latency` | 3,758 | 983.5 | `b200_sxm-x21-nvl72-tensor` | 5.66x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 44 | 3,434.2 | 3,434 | 95.8 | 1 | `layer_fixed_latency` | 2,975 | 866.4 | `b200_sxm-x22-nvl72-tensor` | 5.68x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x47-romfill` | 38,305 | 47 | 3,470.0 | 41,640 | 90.6 | 20,593 | `layer_fixed_latency` | 4,467 | 1,158.3 | `b200_sxm-x24-nvl72-tensor` | 5.72x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 39,120 | 48 | 3,474.7 | 41,696 | 88.8 | 21,031 | `layer_fixed_latency` | 4,600 | 1,194.8 | `b200_sxm-x24-nvl72-tensor` | 5.72x |
| `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 1 | 3,548.2 | 3,548 | 76.8 | 1 | `layer_fixed_latency` | 4,479 | 1,262.3 | `b200_sxm-x29-nvl72-tensor` | 5.81x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 372 | densest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 26,080 | 3,240.6 | 124.3 | 1 |
| array | 372 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 39,120 | 3,474.7 | 88.8 | 21,031 |
| array | 372 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x28` | 22,820 | 2,685.1 | 117.7 | 1 |
| wafer | 76 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,548.2 | 76.8 | 1 |
| wafer | 76 | fastest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,548.2 | 76.8 | 1 |
| wafer | 76 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,548.2 | 76.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 39,120 | 3,474.7 | 41,696 | 21,031 | 4,600 | 1,194.8 | `layer_fixed_latency` | `b200_sxm-x24-nvl72-tensor` | 607.0 | 16,103 | 15,044.5 | 1.019 | 5.72x | 12.6x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,548.2 | 3,548 | 1 | 4,479 | 1,262.3 | `layer_fixed_latency` | `b200_sxm-x29-nvl72-tensor` | 610.7 | 19,608 | 17,828.9 | 0.996 | 5.81x | 14.1x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 47,270 | 3,469.9 | 52,048 | 25,413 | 5,671 | 1,470.1 | `layer_fixed_latency` | `b200_sxm-x30-nvl72-tensor` | 611.3 | 20,309 | 18,386.4 | 0.985 | 5.68x | 12.5x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,548.2 | -- | 1 | -- | 1,262.3 | -- | -- | -- | -- | -- | 1.023 | 1.02x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 39,120 | 3,474.7 | 41,696 | 21,031 | 4,600 | 603.2 | `layer_fixed_latency` | `b200_sxm-x24-hybrid` | 595.2 | 16,103 | 8,253.4 | 1.019 | 5.84x | 13.1x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,528.1 | 14,113 | 7,536 | 8,365 | 1,173.8 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 603.9 | 39,939 | 17,604.9 | 0.996 | 5.84x | 15.0x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 94,540 | 3,443.7 | 99,868 | 50,826 | 11,293 | 1,481.1 | `layer_fixed_latency` | `b200_sxm-x59-nvl72-tensor` | 604.0 | 40,640 | 17,891.4 | 1.001 | 5.70x | 12.1x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,528.1 | -- | 7,536 | -- | 1,173.8 | -- | -- | -- | -- | -- | 1.023 | 1.02x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 39,120 | 3,474.7 | 41,696 | 21,031 | 4,600 | 307.5 | `layer_fixed_latency` | `b200_sxm-x24-hybrid` | 585.9 | 16,103 | 4,571.2 | 1.019 | 5.93x | 14.1x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,528.1 | 14,113 | 7,536 | 8,365 | 592.8 | `layer_fixed_latency` | `b200_sxm-x58-hybrid` | 583.3 | 39,939 | 9,898.9 | 0.996 | 6.05x | 15.8x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 94,540 | 3,443.7 | 99,868 | 50,826 | 11,293 | 746.4 | `layer_fixed_latency` | `b200_sxm-x59-hybrid` | 584.6 | 40,640 | 10,029.7 | 1.001 | 5.89x | 12.8x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,528.1 | -- | 7,536 | -- | 592.8 | -- | -- | -- | -- | -- | 1.023 | 1.02x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x48-romfill` | 39,120 | 3,474.7 | 41,696 | 21,031 | 4,600 | 159.6 | `layer_fixed_latency` | `b200_sxm-x24-hybrid` | 552.0 | 16,103 | 2,575.4 | 1.019 | 6.29x | 15.8x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 3,522.1 | 28,177 | 15,072 | 16,730 | 593.8 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 591.4 | 80,600 | 9,367.6 | 0.996 | 5.96x | 15.8x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 3,414.9 | 194,651 | 99,462 | 22,090 | 736.7 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 591.4 | 80,600 | 9,367.6 | 0.997 | 5.77x | 12.7x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 3,522.1 | -- | 15,072 | -- | 593.8 | -- | -- | -- | -- | -- | 1.001 | 1.03x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 70,905 | 3,457.2 | 76,059 | 38,119 | 8,483 | 149.0 | `layer_fixed_latency` | `b200_sxm-x44-hybrid` | 540.4 | 30,124 | 2,454.0 | 1.007 | 6.40x | 16.5x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,501.6 | 77,036 | 45,218 | 50,103 | 889.9 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 596.3 | 242,544 | 13,676.2 | 0.999 | 5.87x | 15.4x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,415.3 | 290,299 | 148,974 | 33,071 | 283.2 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 573.4 | 120,560 | 4,235.4 | 1.001 | 5.96x | 15.0x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,488.3 | 198,835 | 30,145 | 35,133 | 305.6 | `layer_fixed_latency` | `b200_sxm-x231-nvl72-hybrid` | 580.4 | 161,221 | 5,469.9 | 1.001 | 6.01x | 17.9x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,415.3 | 290,299 | 148,974 | 33,071 | 147.4 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 537.4 | 120,560 | 2,406.9 | 1.001 | 6.35x | 16.3x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,488.2 | 299,983 | 45,218 | 52,720 | 232.1 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 563.9 | 242,544 | 4,300.2 | 0.999 | 6.19x | 18.5x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 3,087.0 | 1,049,597 | 148,974 | 41,984 | 49.3 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 395.0 | 120,560 | 999.4 | 1.001 | 7.82x | 20.3x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,256.3 | 833,601 | 45,218 | 58,312 | 70.0 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 469.7 | 242,544 | 1,503.3 | 0.999 | 6.93x | 21.5x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,633.5 | 1,672,666 | 148,974 | 46,565 | 27.8 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 222.1 | 120,560 | 592.7 | 1.001 | 7.36x | 21.3x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 2,542.5 | 2,603,562 | 45,218 | 77,643 | 29.8 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 303.6 | 242,544 | 789.7 | 0.999 | 8.37x | 26.5x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 503.6 | 2,062,562 | 148,974 | 49,055 | 23.8 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 115.4 | 120,560 | 294.0 | 1.001 | 4.36x | 12.4x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,010.0 | 4,136,879 | 45,218 | 89,199 | 21.6 | `compute` | `b200_sxm-x347-nvl72-hybrid` | 159.4 | 242,544 | 433.6 | 0.999 | 6.33x | 20.1x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 26,080 | array | SRAM | 1 |
| 2-4 | `ROM-N5-native-HBMKV-array-hw-hybrid-x32` | 26,080 | array | HBM | 14,021 |
| 8 | `ROM-N5-native-HBMKV-array-hw-hybrid-x36` | 29,340 | array | HBM | 15,773 |
| 16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x37` | 30,155 | array | HBM | 16,211 |
| 32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x42` | 34,230 | array | HBM | 18,402 |
| 64 | `ROM-N5-native-HBMKV-array-hw-pipeline-x50` | 40,750 | array | HBM | 21,908 |
| 256 | `ROM-N5-native-HBMKV-array-hw-pipeline-x58` | 47,270 | array | HBM | 25,413 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-pipeline-x87` | 70,905 | array | HBM | 38,119 |
| 4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x116` | 94,540 | array | HBM | 50,826 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 31, 32, 36, 37, 42, 44, 47, 48, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 31, 32, 36, 37, 42, 44, 49, 50, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 28, 31, 32, 34, 40, 41, 44, 54, 57, 81, 108, 113, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 28, 31, 32, 34, 40, 41, 44, 54, 57, 81, 108, 113, 170, 227, 340 |

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
| DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 1 | 8 | 5.51 | hierarchical | 267.93 | 15.79 | 41.80 | 34.33 | 3,240.6 |
| DeepSeek-V4-Flash-0731 | `b200_sxm-x16-hybrid` | 1 | 8 | 5.51 | measured_floor | 946.40 | 530.52 | 217.66 | 223.04 | 596.2 |
| DeepSeek-V4-Flash-0731 | `b200_sxm-x16-hybrid` | 64 | 4 | 5.51 | measured_floor | 946.40 | 755.52 | 2,133.34 | 254.32 | 272.5 |

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 10,723.2 tok/s | 0.63x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 77.6 W | 0.31x | within 2x | FAIL |

HC1 binds on `layer_fixed_latency`. Its component times are weight_read 34.47 us, kv_read 3.13 us, compute 34.47 us, link_latency 0.00 us, layer_fixed_latency 60.22 us.

The model **under**-predicts the shipping part by 1.58x. Rather than tune the densities until the anchor
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
| range low | 1,387.3 ns/layer | 44.40 us | 6.06 us | 12,915.3 | 0.76x | layer_fixed_latency |
| range stated | 1,882.0 ns/layer | 60.22 us | 6.06 us | 10,723.2 | 0.63x | layer_fixed_latency |
| range high | 3,233.9 ns/layer | 103.49 us | 6.06 us | 7,448.3 | 0.44x | layer_fixed_latency |

The per-layer serial cost that would land the model exactly on the
published figure is **810.3 ns/layer**. It is reported so the distance between the measured chain and the one the shipping part implies is visible. It is never used as an input: a chain longer than it means the hardwired datapath modelled here is serially slower than HC1's.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 10,704.6 | 0.63x | layer_fixed_latency |
| 3.5 | 10,723.2 | 0.63x | layer_fixed_latency |
| 4.0 | 10,704.6 | 0.63x | layer_fixed_latency |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 11,622.0 | 0.69x | layer_fixed_latency |
| 1,536 | 11,157.1 | 0.66x | layer_fixed_latency |
| 2,048 | 10,723.2 | 0.63x | layer_fixed_latency |

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
| Taalas HC1 card power | 200.0-250.0 W | 77.6 W | 0.31x | FAIL |

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
| **total** | 461.7 W | 77.6 W |

On HC1 the enumerated static power is 52.2 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 56.8 W | 0.23x | 0.28x |
| stated | 461.7 W | 1.15x | 77.6 W | 0.31x | 0.39x |
| high | 698.3 W | 1.75x | 338.7 W | 1.35x | 1.69x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.31x of the top of its published band, **3.22x low**, against 2.58x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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
| Taalas HC1 (modelled reconstruction) | 0.007235 J/token | 77.6 | 10,723.2 |
| A100 80GB, weight-bound gate, same model and batch | 1.537721 J/token | 336.2 | 218.6 |

That is a factor of 213 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 2.6-3.2x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

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

- **40 of 4,462 feasible points (0.9%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 40.
- By area class: large array (5,000-40,000 mm2) 24, wafer (>=40,000 mm2) 16.
- By KV store: hbm 40.
- By batch: B=256 2, B=1024 16, B=4096 22.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 44% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 256 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 640 | 24 | 44.4% | 100.0% | 0.625 | 79% |
| gpu | wafer (>=40,000 mm2) | 890 | 16 | 37.9% | 100.0% | 0.625 | 93% |
| rom | large array (5,000-40,000 mm2) | 1,260 | 0 | 20.3% | 53.5% | 0.267 | 89% |
| rom | wafer (>=40,000 mm2) | 1,672 | 0 | 26.6% | 52.3% | 0.262 | 96% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DSV4-Flash/b200_sxm-x7-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 11,200 | hbm | 1.104x | 7,000.0 / 7,000.0 W | 35% | 30.1 | 33.2 |
| `DSV4-Flash/b200_sxm-x8-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 12,800 | hbm | 1.097x | 8,000.0 / 8,000.0 W | 35% | 31.1 | 34.1 |
| `DSV4-Flash/b200_sxm-x14-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 22,400 | hbm | 1.067x | 14,000.0 / 14,000.0 W | 35% | 34.3 | 36.6 |
| `DSV4-Flash/b200_sxm-x16-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 25,600 | hbm | 1.064x | 16,000.0 / 16,000.0 W | 35% | 35.0 | 37.2 |
| `DSV4-Flash/b200_sxm-x7-pipeline` | DeepSeek-V4-Flash-0731 | 1024 | 11,200 | hbm | 1.062x | 7,000.0 / 7,000.0 W | 35% | 37.9 | 40.3 |
| `DSV4-Flash/b200_sxm-x8-pipeline` | DeepSeek-V4-Flash-0731 | 1024 | 12,800 | hbm | 1.059x | 8,000.0 / 8,000.0 W | 35% | 38.9 | 41.2 |
| `DSV4-Flash/b200_sxm-x17-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 27,200 | hbm | 1.056x | 17,000.0 / 17,000.0 W | 35% | 35.3 | 37.3 |
| `DSV4-Flash/b200_sxm-x18-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 28,800 | hbm | 1.055x | 18,000.0 / 18,000.0 W | 35% | 35.5 | 37.5 |
| `DSV4-Flash/b200_sxm-x19-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 30,400 | hbm | 1.055x | 19,000.0 / 19,000.0 W | 35% | 35.8 | 37.8 |
| `DSV4-Flash/b200_sxm-x20-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 32,000 | hbm | 1.054x | 20,000.0 / 20,000.0 W | 35% | 36.1 | 38.0 |
| `DSV4-Flash/b200_sxm-x21-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 33,600 | hbm | 1.053x | 21,000.0 / 21,000.0 W | 35% | 36.3 | 38.2 |
| `DSV4-Flash/b200_sxm-x22-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 35,200 | hbm | 1.052x | 22,000.0 / 22,000.0 W | 35% | 36.5 | 38.4 |

The worst point's dynamic energy is weight read 75.3%, kv read 18.8%, arithmetic 5.7%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4-Flash-0731 | 1 | 32,600 | `DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x40` | 0.736948 | 2,502.6 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x20-nvl72-tensor` | 12.823077 | 7,724.5 | layer_fixed_latency | 17.40x |
| DeepSeek-V4-Flash-0731 | 2 | 34,230 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x42` | 0.497624 | 3,758.4 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x21-nvl72-tensor` | 7.048984 | 8,269.1 | layer_fixed_latency | 14.17x |
| DeepSeek-V4-Flash-0731 | 4 | 34,230 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x42` | 0.254681 | 3,758.4 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x21-hybrid` | 4.180681 | 9,620.2 | layer_fixed_latency | 15.23x |
| DeepSeek-V4-Flash-0731 | 8 | 34,230 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x42` | 0.133209 | 3,758.4 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x21-hybrid` | 2.376920 | 10,252.4 | layer_fixed_latency | 17.11x |
| DeepSeek-V4-Flash-0731 | 16 | 38,305 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x47-romfill` | 0.084615 | 4,581.1 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x24-hybrid` | 1.568291 | 12,425.6 | layer_fixed_latency | 18.53x |
| DeepSeek-V4-Flash-0731 | 32 | 70,905 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 0.081732 | 8,768.3 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x44-hybrid` | 1.506379 | 23,236.2 | layer_fixed_latency | 18.43x |
| DeepSeek-V4-Flash-0731 | 64 | 138,550 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 0.081410 | 18,150.4 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x87-nvl72-hybrid` | 1.477758 | 45,708.4 | layer_fixed_latency | 18.15x |
| DeepSeek-V4-Flash-0731 | 256 | 369,800 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 0.051823 | 42,115.3 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x231-nvl72-hybrid` | 1.170381 | 128,409.8 | layer_fixed_latency | 22.58x |
| DeepSeek-V4-Flash-0731 | 1024 | 554,700 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.029822 | 77,642.5 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x347-nvl72-hybrid` | 0.789658 | 245,508.3 | weight_read | 26.48x |
| DeepSeek-V4-Flash-0731 | 4096 | 554,700 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.021562 | 89,199.2 | compute | `DSV4-Flash/b200_sxm-x347-nvl72-hybrid` | 0.433579 | 283,164.5 | weight_read | 20.11x |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 3,724.8 | wafer-pipeline | 3,548.2 | wafer-tensor | 1.05x | 984.8 | pipeline | 610.7 | tensor | 1.61x | 3.78x | 5.81x | 1.54x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 3,724.5 | wafer-pipeline | 3,541.3 | wafer-hybrid | 1.05x | 992.1 | pipeline | 619.0 | tensor | 1.60x | 3.75x | 5.72x | 1.52x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 3,724.5 | wafer-pipeline | 3,533.5 | wafer-hybrid | 1.05x | 1,001.3 | pipeline | 613.8 | hybrid | 1.63x | 3.72x | 5.76x | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 3,724.5 | wafer-pipeline | 3,527.0 | wafer-hybrid | 1.06x | 1,005.9 | pipeline | 616.9 | hybrid | 1.63x | 3.70x | 5.72x | 1.54x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 3,724.5 | wafer-pipeline | 3,518.2 | wafer-hybrid | 1.06x | 1,010.5 | pipeline | 615.9 | hybrid | 1.64x | 3.69x | 5.71x | 1.55x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 3,724.5 | wafer-pipeline | 3,512.0 | wafer-hybrid | 1.06x | 1,012.9 | pipeline | 614.9 | hybrid | 1.65x | 3.68x | 5.71x | 1.55x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 3,724.5 | wafer-pipeline | 3,505.5 | wafer-hybrid | 1.06x | 1,015.3 | pipeline | 615.1 | hybrid | 1.65x | 3.67x | 5.70x | 1.55x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.52x to 1.55x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | 46,225 | 3,548.2 | 3,548.2 | layer_fixed_latency | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 696.63 | 610.7 | 610.7 | layer_fixed_latency | 5.81x | 0.31x | 9.10x | 5.81x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x28 | 22,820 | 2,685.1 | 2,685.1 | layer_fixed_latency | DSV4-Flash/b200_sxm-x14-nvl72-tensor | 22,400 | 1.02x | tensor | 637.98 | 590.8 | 590.8 | layer_fixed_latency | 4.54x | 0.49x | 6.83x | 4.54x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 3,528.1 | 14,112.6 | layer_fixed_latency | DSV4-Flash/b200_sxm-x58-nvl72-tensor | 92,800 | 1.00x | tensor | 732.65 | 603.9 | 1,207.7 | layer_fixed_latency | 5.84x | 0.63x | 9.12x | 5.84x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x31 | 25,265 | 2,914.8 | 5,829.6 | layer_fixed_latency | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 530.52 | 596.2 | 1,192.3 | layer_fixed_latency | 4.89x | 0.93x | 7.42x | 4.89x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 3,528.1 | 14,112.6 | layer_fixed_latency | DSV4-Flash/b200_sxm-x58-hybrid | 92,800 | 1.00x | hybrid | 546.63 | 583.3 | 4,666.8 | layer_fixed_latency | 6.05x | 0.63x | 9.12x | 6.05x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x31 | 25,265 | 2,816.7 | 11,267.0 | layer_fixed_latency | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 548.18 | 569.4 | 2,277.7 | layer_fixed_latency | 4.95x | 1.79x | 7.17x | 4.95x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 3,522.1 | 28,176.7 | layer_fixed_latency | DSV4-Flash/b200_sxm-x116-nvl72-hybrid | 185,600 | 1.00x | hybrid | 734.74 | 591.4 | 4,731.3 | layer_fixed_latency | 5.96x | 0.63x | 9.10x | 5.96x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x31 | 25,265 | 2,370.8 | 18,966.5 | layer_fixed_latency | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 662.08 | 523.6 | 4,189.2 | layer_fixed_latency | 4.53x | 3.02x | 6.03x | 4.53x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,501.6 | 77,036.2 | layer_fixed_latency | DSV4-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 733.77 | 596.3 | 9,541.1 | layer_fixed_latency | 5.87x | 0.57x | 9.05x | 5.87x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x31 | 25,265 | 1,561.4 | 24,982.9 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 763.30 | 451.3 | 7,220.3 | layer_fixed_latency | 3.46x | 3.46x | 3.97x | 3.46x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,488.3 | 198,834.6 | layer_fixed_latency | DSV4-Flash/b200_sxm-x231-nvl72-hybrid | 369,600 | 1.00x | hybrid | 568.86 | 580.4 | 18,572.0 | layer_fixed_latency | 6.01x | 2.22x | 9.01x | 6.01x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x31 | 25,265 | 932.3 | 29,832.5 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 965.74 | 360.2 | 11,527.8 | link_latency | 2.59x | 2.59x | 2.83x | 2.59x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,488.2 | 299,983.3 | layer_fixed_latency | DSV4-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 595.11 | 563.9 | 36,092.4 | layer_fixed_latency | 6.19x | 2.23x | 9.01x | 6.19x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x31 | 25,265 | 500.7 | 32,045.5 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 755.52 | 272.5 | 17,442.9 | weight_read | 1.84x | 1.84x | 2.02x | 1.84x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,256.3 | 833,600.6 | layer_fixed_latency | DSV4-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 779.28 | 469.7 | 120,249.0 | layer_fixed_latency | 6.93x | 6.21x | 8.41x | 6.94x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x31 | 25,265 | 132.3 | 33,873.2 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 1,845.55 | 141.3 | 36,161.2 | weight_read | 0.94x | 0.94x | 1.21x | 0.94x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2,542.5 | 2,603,562.3 | layer_fixed_latency | DSV4-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 763.64 | 303.6 | 310,904.5 | weight_read | 8.37x | 8.37x | 9.06x | 8.53x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x31 | 25,265 | 33.5 | 34,288.8 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 6,041.16 | 77.9 | 79,807.2 | link_latency | 0.43x | 0.43x | 0.69x | 0.43x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,010.0 | 4,136,879.2 | compute | DSV4-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 1,722.45 | 159.4 | 653,086.3 | weight_read | 6.33x | 6.33x | 7.66x | 6.42x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x31 | 25,265 | 8.4 | 34,218.0 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 7,972.99 | 45.1 | 184,653.9 | weight_read | 0.19x | 0.19x | 0.24x | 0.19x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 7 | 11,200 | 525.37 | 208.41 | 587.9 | 722.6 |
| DeepSeek-V4-Flash-0731 | 8 | 12,800 | 525.80 | 208.45 | 597.8 | 737.8 |
| DeepSeek-V4-Flash-0731 | 14 | 22,400 | 637.98 | 208.58 | 590.8 | 791.6 |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 530.52 | 208.60 | 596.2 | 737.7 |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 638.56 | 208.61 | 597.6 | 804.2 |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 638.72 | 208.62 | 599.3 | 807.5 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 638.87 | 208.62 | 600.9 | 810.5 |
| DeepSeek-V4-Flash-0731 | 20 | 32,000 | 639.01 | 208.63 | 602.4 | 813.2 |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 639.15 | 208.64 | 603.7 | 815.7 |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 639.29 | 208.64 | 604.9 | 818.0 |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 639.55 | 208.65 | 607.0 | 822.0 |
| DeepSeek-V4-Flash-0731 | 25 | 40,000 | 639.71 | 208.65 | 607.9 | 823.7 |
| DeepSeek-V4-Flash-0731 | 28 | 44,800 | 696.50 | 208.66 | 610.1 | 868.6 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 696.63 | 208.67 | 610.7 | 870.0 |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 696.76 | 208.67 | 611.3 | 871.2 |
| DeepSeek-V4-Flash-0731 | 41 | 65,600 | 698.09 | 208.69 | 615.7 | 881.2 |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 698.42 | 208.70 | 616.5 | 883.1 |
| DeepSeek-V4-Flash-0731 | 55 | 88,000 | 699.61 | 208.71 | 618.6 | 888.3 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 699.93 | 208.71 | 619.0 | 889.4 |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 700.03 | 208.71 | 619.1 | 889.7 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 705.26 | 210.91 | 613.8 | 881.1 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 705.26 | 210.91 | 616.9 | 887.7 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 707.95 | 213.10 | 615.9 | 885.8 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 710.63 | 215.30 | 614.9 | 884.1 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 714.14 | 217.49 | 615.1 | 885.7 |

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
| DeepSeek-V4-Flash-0731 | 7 | 11,200 | 395.0 | 587.9 | — | tensor | 525.37 | 30.9% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | 12,800 | 394.8 | 597.8 | — | tensor | 525.80 | 31.4% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 14 | 22,400 | 393.3 | 590.8 | 586.2 | tensor | 637.98 | 37.7% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 392.9 | 595.6 | 596.2 | hybrid | 530.52 | 31.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 392.5 | 597.6 | 567.3 | tensor | 638.56 | 38.2% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 392.3 | 599.3 | 572.4 | tensor | 638.72 | 38.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 392.1 | 600.9 | 577.1 | tensor | 638.87 | 38.4% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 20 | 32,000 | 391.9 | 602.4 | 581.3 | tensor | 639.01 | 38.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 391.8 | 603.7 | 585.2 | tensor | 639.15 | 38.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 391.6 | 604.9 | 588.8 | tensor | 639.29 | 38.7% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 391.2 | 607.0 | 595.2 | tensor | 639.55 | 38.8% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 25 | 40,000 | 390.8 | 607.9 | 575.1 | tensor | 639.71 | 38.9% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 28 | 44,800 | 390.2 | 610.1 | 584.3 | tensor | 696.50 | 42.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 390.0 | 610.7 | 587.0 | tensor | 696.63 | 42.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 389.8 | 611.3 | 589.6 | tensor | 696.76 | 42.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 41 | 65,600 | 387.3 | 615.7 | 580.6 | tensor | 698.09 | 43.0% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 387.0 | 616.5 | 586.0 | tensor | 698.42 | 43.1% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 55 | 88,000 | 387.0 | 618.6 | 590.2 | tensor | 699.61 | 43.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 387.0 | 619.0 | 583.3 | tensor | 699.93 | 43.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 387.0 | 619.1 | 584.6 | tensor | 700.03 | 43.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 387.0 | 322.3 | 613.8 | hybrid | 705.26 | 43.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 387.0 | 319.8 | 616.9 | hybrid | 705.26 | 43.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 387.0 | 302.2 | 615.9 | hybrid | 707.95 | 43.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 387.0 | 289.5 | 614.9 | hybrid | 710.63 | 43.7% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 387.0 | 272.7 | 615.1 | hybrid | 714.14 | 43.9% | layer_fixed_latency |

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
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x44 | DeepSeek-V4-Flash-0731 | 44 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x31 | DeepSeek-V4-Flash-0731 | 31 | tensor | rom_package_ucie | rom_board_serdes | 172 | 40.98 us | 2,440.0 tok/s | 24,399.9 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 8 on rom_board_serdes (traversals 4.4) = 38.87 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x40 | DeepSeek-V4-Flash-0731 | 40 | hybrid | rom_package_ucie | rom_board_serdes | 95 | 3.06 us | 32,709.2 tok/s | 327,091.6 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.94 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x44 | DeepSeek-V4-Flash-0731 | 44 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x28 | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x32 | DeepSeek-V4-Flash-0731 | 32 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x50 | DeepSeek-V4-Flash-0731 | 50 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x32 | DeepSeek-V4-Flash-0731 | 32 | tensor | rom_package_ucie | rom_board_serdes | 172 | 40.98 us | 2,440.0 tok/s | 24,399.9 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 8 on rom_board_serdes (traversals 4.4) = 38.87 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x42 | DeepSeek-V4-Flash-0731 | 42 | hybrid | rom_package_ucie | rom_board_serdes | 96 | 3.16 us | 31,627.6 tok/s | 316,275.6 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x49 | DeepSeek-V4-Flash-0731 | 49 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4-Flash-0731 | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x31 | DeepSeek-V4-Flash-0731 | 31 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4-Flash-0731 | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 172 | 184.65 us | 541.6 tok/s | 5,415.8 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 86 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 19.10 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x36 | DeepSeek-V4-Flash-0731 | 36 | hybrid | nvlink5 | infiniband_ndr | 90 | 217.23 us | 460.3 tok/s | 4,603.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4-Flash-0731 | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 87 | 165.65 us | 603.7 tok/s | 6,036.8 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Flash/b200_sxm-x7-pipeline | DeepSeek-V4-Flash-0731 | 7 | pipeline | nvlink5 | infiniband_ndr | 6 | 7.25 us | 13,784.3 tok/s | 137,843.3 tok/s | 6 x point_to_point span 2 on nvlink5 (traversals 1.0) = 7.25 us |
| DSV4-Flash/b200_sxm-x7-tensor | DeepSeek-V4-Flash-0731 | 7 | tensor | nvlink5 | infiniband_ndr | 86 | 208.41 us | 479.8 tok/s | 4,798.2 tok/s | 86 x all_reduce span 7 on nvlink5 (traversals 2.0) = 208.41 us |
| DSV4-Flash/b200_sxm-x7-nvl72-tensor | DeepSeek-V4-Flash-0731 | 7 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.41 us | 479.8 tok/s | 4,798.2 tok/s | 86 x all_reduce span 7 on nvlink5_nvl72 (traversals 2.0) = 208.41 us |
| DSV4-Flash/b200_sxm-x7-expert | DeepSeek-V4-Flash-0731 | 7 | expert | nvlink5 | infiniband_ndr | 172 | 312.28 us | 320.2 tok/s | 3,202.2 tok/s | 86 x all_reduce span 7 on nvlink5 (traversals 2.0) = 208.41 us; 86 x point_to_point span 2 on nvlink5 (traversals 1.0) = 103.87 us |
| DSV4-Flash/b200_sxm-x7-nvl72-expert | DeepSeek-V4-Flash-0731 | 7 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.28 us | 320.2 tok/s | 3,202.2 tok/s | 86 x all_reduce span 7 on nvlink5_nvl72 (traversals 2.0) = 208.41 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.87 us |
| DSV4-Flash/b200_sxm-x8-pipeline | DeepSeek-V4-Flash-0731 | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.46 us | 11,815.1 tok/s | 118,151.4 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us |
| DSV4-Flash/b200_sxm-x8-tensor | DeepSeek-V4-Flash-0731 | 8 | tensor | nvlink5 | infiniband_ndr | 86 | 208.45 us | 479.7 tok/s | 4,797.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us |
| DSV4-Flash/b200_sxm-x8-nvl72-tensor | DeepSeek-V4-Flash-0731 | 8 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.45 us | 479.7 tok/s | 4,797.2 tok/s | 86 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 208.45 us |
| DSV4-Flash/b200_sxm-x8-expert | DeepSeek-V4-Flash-0731 | 8 | expert | nvlink5 | infiniband_ndr | 172 | 312.24 us | 320.3 tok/s | 3,202.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on nvlink5 (traversals 1.0) = 103.79 us |
| DSV4-Flash/b200_sxm-x8-nvl72-expert | DeepSeek-V4-Flash-0731 | 8 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.24 us | 320.3 tok/s | 3,202.6 tok/s | 86 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.79 us |
| DSV4-Flash/b200_sxm-x14-pipeline | DeepSeek-V4-Flash-0731 | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 16.70 us | 5,986.9 tok/s | 59,869.2 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 14.51 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x14-tensor | DeepSeek-V4-Flash-0731 | 14 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x14-hybrid | DeepSeek-V4-Flash-0731 | 14 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x14-nvl72-tensor | DeepSeek-V4-Flash-0731 | 14 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.58 us | 479.4 tok/s | 4,794.3 tok/s | 86 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 208.58 us |
| DSV4-Flash/b200_sxm-x14-expert | DeepSeek-V4-Flash-0731 | 14 | expert | nvlink5 | infiniband_ndr | 172 | 389.07 us | 257.0 tok/s | 2,570.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 180.62 us |
| DSV4-Flash/b200_sxm-x14-nvl72-expert | DeepSeek-V4-Flash-0731 | 14 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.12 us | 320.4 tok/s | 3,203.9 tok/s | 86 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 208.58 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.54 us |
| DSV4-Flash/b200_sxm-x16-pipeline | DeepSeek-V4-Flash-0731 | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.12 us | 5,229.8 tok/s | 52,297.8 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-tensor | DeepSeek-V4-Flash-0731 | 16 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x16-hybrid | DeepSeek-V4-Flash-0731 | 16 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-nvl72-tensor | DeepSeek-V4-Flash-0731 | 16 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.60 us | 479.4 tok/s | 4,793.8 tok/s | 86 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 208.60 us |
| DSV4-Flash/b200_sxm-x16-expert | DeepSeek-V4-Flash-0731 | 16 | expert | nvlink5 | infiniband_ndr | 172 | 387.29 us | 258.2 tok/s | 2,582.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.86 us |
| DSV4-Flash/b200_sxm-x16-nvl72-expert | DeepSeek-V4-Flash-0731 | 16 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.10 us | 320.4 tok/s | 3,204.2 tok/s | 86 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 208.60 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.49 us |
| DSV4-Flash/b200_sxm-x17-pipeline | DeepSeek-V4-Flash-0731 | 17 | pipeline | nvlink5 | infiniband_ndr | 16 | 21.32 us | 4,691.5 tok/s | 46,915.1 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x17-tensor | DeepSeek-V4-Flash-0731 | 17 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x17-hybrid | DeepSeek-V4-Flash-0731 | 17 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x17-nvl72-tensor | DeepSeek-V4-Flash-0731 | 17 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.61 us | 479.4 tok/s | 4,793.6 tok/s | 86 x all_reduce span 17 on nvlink5_nvl72 (traversals 2.0) = 208.61 us |
| DSV4-Flash/b200_sxm-x17-expert | DeepSeek-V4-Flash-0731 | 17 | expert | nvlink5 | infiniband_ndr | 172 | 386.98 us | 258.4 tok/s | 2,584.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.55 us |
| DSV4-Flash/b200_sxm-x17-nvl72-expert | DeepSeek-V4-Flash-0731 | 17 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.09 us | 320.4 tok/s | 3,204.2 tok/s | 86 x all_reduce span 17 on nvlink5_nvl72 (traversals 2.0) = 208.61 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.48 us |
| DSV4-Flash/b200_sxm-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink5 | infiniband_ndr | 17 | 22.52 us | 4,439.7 tok/s | 44,396.7 tok/s | 15 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.14 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x18-nvl72-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.62 us | 479.3 tok/s | 4,793.5 tok/s | 86 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 208.62 us |
| DSV4-Flash/b200_sxm-x18-expert | DeepSeek-V4-Flash-0731 | 18 | expert | nvlink5 | infiniband_ndr | 172 | 386.70 us | 258.6 tok/s | 2,586.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.28 us |
| DSV4-Flash/b200_sxm-x18-nvl72-expert | DeepSeek-V4-Flash-0731 | 18 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.08 us | 320.4 tok/s | 3,204.3 tok/s | 86 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 208.62 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.46 us |
| DSV4-Flash/b200_sxm-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink5 | infiniband_ndr | 18 | 23.73 us | 4,213.5 tok/s | 42,134.9 tok/s | 16 x point_to_point span 2 on nvlink5 (traversals 1.0) = 19.35 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-nvl72-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.62 us | 479.3 tok/s | 4,793.3 tok/s | 86 x all_reduce span 19 on nvlink5_nvl72 (traversals 2.0) = 208.62 us |
| DSV4-Flash/b200_sxm-x19-expert | DeepSeek-V4-Flash-0731 | 19 | expert | nvlink5 | infiniband_ndr | 172 | 386.46 us | 258.8 tok/s | 2,587.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.03 us |
| DSV4-Flash/b200_sxm-x19-nvl72-expert | DeepSeek-V4-Flash-0731 | 19 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.07 us | 320.4 tok/s | 3,204.4 tok/s | 86 x all_reduce span 19 on nvlink5_nvl72 (traversals 2.0) = 208.62 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.45 us |
| DSV4-Flash/b200_sxm-x20-pipeline | DeepSeek-V4-Flash-0731 | 20 | pipeline | nvlink5 | infiniband_ndr | 19 | 24.94 us | 4,009.2 tok/s | 40,092.3 tok/s | 17 x point_to_point span 2 on nvlink5 (traversals 1.0) = 20.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x20-tensor | DeepSeek-V4-Flash-0731 | 20 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x20-hybrid | DeepSeek-V4-Flash-0731 | 20 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x20-nvl72-tensor | DeepSeek-V4-Flash-0731 | 20 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.63 us | 479.3 tok/s | 4,793.2 tok/s | 86 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 208.63 us |
| DSV4-Flash/b200_sxm-x20-expert | DeepSeek-V4-Flash-0731 | 20 | expert | nvlink5 | infiniband_ndr | 172 | 386.23 us | 258.9 tok/s | 2,589.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.81 us |
| DSV4-Flash/b200_sxm-x20-nvl72-expert | DeepSeek-V4-Flash-0731 | 20 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.07 us | 320.4 tok/s | 3,204.5 tok/s | 86 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 208.63 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.43 us |
| DSV4-Flash/b200_sxm-x21-pipeline | DeepSeek-V4-Flash-0731 | 21 | pipeline | nvlink5 | infiniband_ndr | 20 | 26.15 us | 3,823.9 tok/s | 38,238.7 tok/s | 18 x point_to_point span 2 on nvlink5 (traversals 1.0) = 21.76 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-tensor | DeepSeek-V4-Flash-0731 | 21 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x21-hybrid | DeepSeek-V4-Flash-0731 | 21 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-nvl72-tensor | DeepSeek-V4-Flash-0731 | 21 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.64 us | 479.3 tok/s | 4,793.0 tok/s | 86 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 208.64 us |
| DSV4-Flash/b200_sxm-x21-expert | DeepSeek-V4-Flash-0731 | 21 | expert | nvlink5 | infiniband_ndr | 172 | 386.03 us | 259.0 tok/s | 2,590.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.61 us |
| DSV4-Flash/b200_sxm-x21-nvl72-expert | DeepSeek-V4-Flash-0731 | 21 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.06 us | 320.5 tok/s | 3,204.5 tok/s | 86 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 208.64 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.42 us |
| DSV4-Flash/b200_sxm-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.36 us | 3,654.9 tok/s | 36,548.9 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 22.97 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-nvl72-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.64 us | 479.3 tok/s | 4,792.9 tok/s | 86 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 208.64 us |
| DSV4-Flash/b200_sxm-x22-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink5 | infiniband_ndr | 172 | 385.85 us | 259.2 tok/s | 2,591.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.42 us |
| DSV4-Flash/b200_sxm-x22-nvl72-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.06 us | 320.5 tok/s | 3,204.6 tok/s | 86 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 208.64 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.41 us |
| DSV4-Flash/b200_sxm-x24-pipeline | DeepSeek-V4-Flash-0731 | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 29.78 us | 3,358.1 tok/s | 33,580.9 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x24-tensor | DeepSeek-V4-Flash-0731 | 24 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x24-hybrid | DeepSeek-V4-Flash-0731 | 24 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x24-nvl72-tensor | DeepSeek-V4-Flash-0731 | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.7 tok/s | 86 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x24-expert | DeepSeek-V4-Flash-0731 | 24 | expert | nvlink5 | infiniband_ndr | 172 | 385.19 us | 259.6 tok/s | 2,596.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.10 us |
| DSV4-Flash/b200_sxm-x24-nvl72-expert | DeepSeek-V4-Flash-0731 | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.05 us | 320.5 tok/s | 3,204.7 tok/s | 86 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.40 us |
| DSV4-Flash/b200_sxm-x25-pipeline | DeepSeek-V4-Flash-0731 | 25 | pipeline | nvlink5 | infiniband_ndr | 24 | 31.97 us | 3,127.7 tok/s | 31,276.7 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x25-tensor | DeepSeek-V4-Flash-0731 | 25 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x25-hybrid | DeepSeek-V4-Flash-0731 | 25 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x25-nvl72-tensor | DeepSeek-V4-Flash-0731 | 25 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.6 tok/s | 86 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x25-expert | DeepSeek-V4-Flash-0731 | 25 | expert | nvlink5 | infiniband_ndr | 172 | 385.05 us | 259.7 tok/s | 2,597.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.96 us |
| DSV4-Flash/b200_sxm-x25-nvl72-expert | DeepSeek-V4-Flash-0731 | 25 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.04 us | 320.5 tok/s | 3,204.7 tok/s | 86 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.39 us |
| DSV4-Flash/b200_sxm-x28-pipeline | DeepSeek-V4-Flash-0731 | 28 | pipeline | nvlink5 | infiniband_ndr | 27 | 35.60 us | 2,809.0 tok/s | 28,089.9 tok/s | 24 x point_to_point span 2 on nvlink5 (traversals 1.0) = 29.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x28-tensor | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x28-hybrid | DeepSeek-V4-Flash-0731 | 28 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x28-nvl72-tensor | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.66 us | 479.2 tok/s | 4,792.4 tok/s | 86 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 208.66 us |
| DSV4-Flash/b200_sxm-x28-expert | DeepSeek-V4-Flash-0731 | 28 | expert | nvlink5 | infiniband_ndr | 172 | 384.68 us | 260.0 tok/s | 2,599.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.60 us |
| DSV4-Flash/b200_sxm-x28-nvl72-expert | DeepSeek-V4-Flash-0731 | 28 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.03 us | 320.5 tok/s | 3,204.8 tok/s | 86 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 208.66 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.37 us |
| DSV4-Flash/b200_sxm-x29-pipeline | DeepSeek-V4-Flash-0731 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x29-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x29-hybrid | DeepSeek-V4-Flash-0731 | 29 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x29-nvl72-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.67 us | 479.2 tok/s | 4,792.3 tok/s | 86 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 208.67 us |
| DSV4-Flash/b200_sxm-x29-expert | DeepSeek-V4-Flash-0731 | 29 | expert | nvlink5 | infiniband_ndr | 172 | 384.58 us | 260.0 tok/s | 2,600.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.50 us |
| DSV4-Flash/b200_sxm-x29-nvl72-expert | DeepSeek-V4-Flash-0731 | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.03 us | 320.5 tok/s | 3,204.8 tok/s | 86 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 208.67 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.36 us |
| DSV4-Flash/b200_sxm-x30-pipeline | DeepSeek-V4-Flash-0731 | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.02 us | 2,630.3 tok/s | 26,303.2 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.44 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x30-tensor | DeepSeek-V4-Flash-0731 | 30 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x30-hybrid | DeepSeek-V4-Flash-0731 | 30 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x30-nvl72-tensor | DeepSeek-V4-Flash-0731 | 30 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.67 us | 479.2 tok/s | 4,792.3 tok/s | 86 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 208.67 us |
| DSV4-Flash/b200_sxm-x30-expert | DeepSeek-V4-Flash-0731 | 30 | expert | nvlink5 | infiniband_ndr | 172 | 384.48 us | 260.1 tok/s | 2,600.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.40 us |
| DSV4-Flash/b200_sxm-x30-nvl72-expert | DeepSeek-V4-Flash-0731 | 30 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.03 us | 320.5 tok/s | 3,204.9 tok/s | 86 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 208.67 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.36 us |
| DSV4-Flash/b200_sxm-x41-pipeline | DeepSeek-V4-Flash-0731 | 41 | pipeline | nvlink5 | infiniband_ndr | 40 | 53.29 us | 1,876.6 tok/s | 18,766.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.32 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x41-tensor | DeepSeek-V4-Flash-0731 | 41 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x41-hybrid | DeepSeek-V4-Flash-0731 | 41 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x41-nvl72-tensor | DeepSeek-V4-Flash-0731 | 41 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.69 us | 479.2 tok/s | 4,791.8 tok/s | 86 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 208.69 us |
| DSV4-Flash/b200_sxm-x41-expert | DeepSeek-V4-Flash-0731 | 41 | expert | nvlink5 | infiniband_ndr | 172 | 383.45 us | 260.8 tok/s | 2,607.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.81 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.64 us |
| DSV4-Flash/b200_sxm-x41-nvl72-expert | DeepSeek-V4-Flash-0731 | 41 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.01 us | 320.5 tok/s | 3,205.1 tok/s | 86 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 208.69 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.31 us |
| DSV4-Flash/b200_sxm-x44-pipeline | DeepSeek-V4-Flash-0731 | 44 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x44-tensor | DeepSeek-V4-Flash-0731 | 44 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x44-hybrid | DeepSeek-V4-Flash-0731 | 44 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x44-nvl72-tensor | DeepSeek-V4-Flash-0731 | 44 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.70 us | 479.2 tok/s | 4,791.7 tok/s | 86 x all_reduce span 44 on nvlink5_nvl72 (traversals 2.0) = 208.70 us |
| DSV4-Flash/b200_sxm-x44-expert | DeepSeek-V4-Flash-0731 | 44 | expert | nvlink5 | infiniband_ndr | 172 | 383.31 us | 260.9 tok/s | 2,608.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.81 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.50 us |
| DSV4-Flash/b200_sxm-x44-nvl72-expert | DeepSeek-V4-Flash-0731 | 44 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.00 us | 320.5 tok/s | 3,205.1 tok/s | 86 x all_reduce span 44 on nvlink5_nvl72 (traversals 2.0) = 208.70 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.31 us |
| DSV4-Flash/b200_sxm-x55-pipeline | DeepSeek-V4-Flash-0731 | 55 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x55-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/b200_sxm-x55-hybrid | DeepSeek-V4-Flash-0731 | 55 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/b200_sxm-x55-nvl72-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.4 tok/s | 86 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x55-expert | DeepSeek-V4-Flash-0731 | 55 | expert | nvlink5 | infiniband_ndr | 172 | 382.86 us | 261.2 tok/s | 2,611.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.74 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.12 us |
| DSV4-Flash/b200_sxm-x55-nvl72-expert | DeepSeek-V4-Flash-0731 | 55 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.29 us |
| DSV4-Flash/b200_sxm-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x58-nvl72-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.4 tok/s | 86 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x58-expert | DeepSeek-V4-Flash-0731 | 58 | expert | nvlink5 | infiniband_ndr | 172 | 382.73 us | 261.3 tok/s | 2,612.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.69 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.04 us |
| DSV4-Flash/b200_sxm-x58-nvl72-expert | DeepSeek-V4-Flash-0731 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.28 us |
| DSV4-Flash/b200_sxm-x59-pipeline | DeepSeek-V4-Flash-0731 | 59 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x59-tensor | DeepSeek-V4-Flash-0731 | 59 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x59-hybrid | DeepSeek-V4-Flash-0731 | 59 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x59-nvl72-tensor | DeepSeek-V4-Flash-0731 | 59 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.4 tok/s | 86 x all_reduce span 59 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x59-expert | DeepSeek-V4-Flash-0731 | 59 | expert | nvlink5 | infiniband_ndr | 172 | 382.71 us | 261.3 tok/s | 2,613.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.69 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.01 us |
| DSV4-Flash/b200_sxm-x59-nvl72-expert | DeepSeek-V4-Flash-0731 | 59 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 59 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.28 us |
| DSV4-Flash/b200_sxm-x87-pipeline | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x87-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5 | infiniband_ndr | 172 | 596.04 us | 167.8 tok/s | 1,677.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 387.59 us |
| DSV4-Flash/b200_sxm-x87-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.39 us | 434.0 tok/s | 4,340.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| DSV4-Flash/b200_sxm-x87-nvl72-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x87-expert | DeepSeek-V4-Flash-0731 | 87 | expert | nvlink5 | infiniband_ndr | 172 | 382.16 us | 261.7 tok/s | 2,616.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.61 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.55 us |
| DSV4-Flash/b200_sxm-x87-nvl72-expert | DeepSeek-V4-Flash-0731 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.27 us | 260.2 tok/s | 2,602.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.55 us |
| DSV4-Flash/b200_sxm-x116-pipeline | DeepSeek-V4-Flash-0731 | 116 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x116-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5 | infiniband_ndr | 172 | 597.07 us | 167.5 tok/s | 1,674.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 388.61 us |
| DSV4-Flash/b200_sxm-x116-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.17 us | 418.1 tok/s | 4,181.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| DSV4-Flash/b200_sxm-x116-nvl72-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x116-expert | DeepSeek-V4-Flash-0731 | 116 | expert | nvlink5 | infiniband_ndr | 172 | 381.86 us | 261.9 tok/s | 2,618.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.55 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.31 us |
| DSV4-Flash/b200_sxm-x116-nvl72-expert | DeepSeek-V4-Flash-0731 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.02 us | 260.4 tok/s | 2,604.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.31 us |
| DSV4-Flash/b200_sxm-x173-pipeline | DeepSeek-V4-Flash-0731 | 173 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x173-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5 | infiniband_ndr | 172 | 597.96 us | 167.2 tok/s | 1,672.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 389.51 us |
| DSV4-Flash/b200_sxm-x173-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5 | infiniband_ndr | 107 | 254.53 us | 392.9 tok/s | 3,928.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| DSV4-Flash/b200_sxm-x173-nvl72-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 586.06 us | 170.6 tok/s | 1,706.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 88 | 213.10 us | 469.3 tok/s | 4,692.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x173-expert | DeepSeek-V4-Flash-0731 | 173 | expert | nvlink5 | infiniband_ndr | 172 | 381.57 us | 262.1 tok/s | 2,620.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.50 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.07 us |
| DSV4-Flash/b200_sxm-x173-nvl72-expert | DeepSeek-V4-Flash-0731 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.63 us | 261.4 tok/s | 2,613.5 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.56 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.07 us |
| DSV4-Flash/b200_sxm-x231-pipeline | DeepSeek-V4-Flash-0731 | 231 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x231-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5 | infiniband_ndr | 172 | 598.43 us | 167.1 tok/s | 1,671.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 389.97 us |
| DSV4-Flash/b200_sxm-x231-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5 | infiniband_ndr | 114 | 269.88 us | 370.5 tok/s | 3,705.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| DSV4-Flash/b200_sxm-x231-nvl72-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 589.58 us | 169.6 tok/s | 1,696.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 89 | 215.30 us | 464.5 tok/s | 4,644.7 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x231-expert | DeepSeek-V4-Flash-0731 | 231 | expert | nvlink5 | infiniband_ndr | 172 | 381.42 us | 262.2 tok/s | 2,621.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.47 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.95 us |
| DSV4-Flash/b200_sxm-x231-nvl72-expert | DeepSeek-V4-Flash-0731 | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.12 us | 261.7 tok/s | 2,617.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.17 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.95 us |
| DSV4-Flash/b200_sxm-x347-pipeline | DeepSeek-V4-Flash-0731 | 347 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x347-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5 | infiniband_ndr | 172 | 598.92 us | 167.0 tok/s | 1,669.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 390.47 us |
| DSV4-Flash/b200_sxm-x347-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5 | infiniband_ndr | 128 | 300.60 us | 332.7 tok/s | 3,326.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 42 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 92.14 us |
| DSV4-Flash/b200_sxm-x347-nvl72-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 591.69 us | 169.0 tok/s | 1,690.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 382.98 us |
| DSV4-Flash/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 90 | 217.49 us | 459.8 tok/s | 4,597.9 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/b200_sxm-x347-expert | DeepSeek-V4-Flash-0731 | 347 | expert | nvlink5 | infiniband_ndr | 172 | 381.27 us | 262.3 tok/s | 2,622.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.82 us |
| DSV4-Flash/b200_sxm-x347-nvl72-expert | DeepSeek-V4-Flash-0731 | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 381.80 us | 261.9 tok/s | 2,619.2 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 206.98 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.82 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x40 | 32,600 | 3,395.9 | 0.104 | 3,315.2 (29,340) | 3,548.2 (46,225) | 1.07x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x42 | 34,230 | 3,414.0 | 0.100 | 3,315.2 (29,340) | 3,528.1 (92,450) | 1.06x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x42 | 34,230 | 3,414.0 | 0.100 | 3,315.2 (29,340) | 3,528.1 (92,450) | 1.06x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x42 | 34,230 | 3,414.0 | 0.100 | 3,315.2 (29,340) | 3,502.6 (92,450) | 1.06x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x47-romfill | 38,305 | 3,383.8 | 0.088 | 3,288.3 (35,860) | 3,445.0 (92,450) | 1.05x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill | 70,905 | 3,352.5 | 0.047 | 3,296.1 (46,455) | 3,360.0 (92,450) | 1.02x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill | 138,550 | 3,326.2 | 0.024 | 3,260.3 (92,095) | 3,351.8 (184,900) | 1.03x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,174.5 | 0.009 | 2,966.9 (185,005) | 3,174.5 (369,800) | 1.07x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 1024 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2,542.5 | 0.005 | 1,633.5 (277,100) | 2,542.5 (554,700) | 1.56x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4096 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,010.0 | 0.002 | 503.6 (277,100) | 1,010.0 (554,700) | 2.01x | compute |

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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 98.1 mm2 | 17.65 mm2 (18.0%) | 25,105 mm2 | 4,519 mm2 | 28,467 mm2 = 34.9 reticles |

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
| DeepSeek-V4-Flash-0731 | 1 | sram | 365,808.7 | 27,648.9 | 27,648.9 | 13.23x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 365,808.7 | 27,648.9 | 27,648.9 | 13.23x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 365,808.7 | 27,648.9 | 27,648.9 | 13.23x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 365,808.7 | 27,648.9 | 27,648.9 | 13.23x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 365,808.7 | 27,648.9 | 37,623.9 | 13.23x | 1.36x | weight_read | weight_read | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 365,808.7 | 27,648.9 | 57,705.9 | 13.23x | 2.09x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 365,808.7 | 27,875.3 | 87,233.1 | 13.12x | 3.13x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 530,912.2 | 29,014.6 | 162,047.4 | 18.30x | 5.59x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 977,296.3 | 26,113.2 | 275,144.7 | 37.43x | 10.54x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 1,705,703.6 | 26,113.2 | 434,329.0 | 65.32x | 16.63x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 2,037,119.2 | 167,961.4 | 167,961.4 | 12.13x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 2,037,119.2 | 167,961.4 | 167,961.4 | 12.13x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 2,037,119.2 | 167,961.4 | 167,961.4 | 12.13x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 2,037,119.2 | 167,961.4 | 167,961.4 | 12.13x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 2,037,119.2 | 167,961.4 | 167,961.4 | 12.13x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 2,037,119.2 | 167,961.4 | 167,961.4 | 12.13x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 2,037,119.2 | 167,961.4 | 177,466.1 | 12.13x | 1.06x | layer_fixed_latency | weight_read | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 256 | rom | 2,037,119.2 | 192,467.0 | 473,281.8 | 10.58x | 2.46x | layer_fixed_latency | weight_read | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 2,603,562.3 | 211,097.0 | 823,372.5 | 12.33x | 3.90x | layer_fixed_latency | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 4,136,879.2 | 213,947.5 | 987,880.0 | 19.34x | 4.62x | compute | weight_read | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,808.7 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 2,037,119.2 | 3.672 | layer_fixed_latency | 5.57x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,808.7 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 2,037,119.2 | 3.672 | layer_fixed_latency | 5.57x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,808.7 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 2,037,119.2 | 3.672 | layer_fixed_latency | 5.57x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,808.7 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 2,037,119.2 | 3.672 | layer_fixed_latency | 5.57x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,808.7 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 2,037,119.2 | 3.672 | layer_fixed_latency | 5.57x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.13 | 37,623.9 | 0.407 | layer_fixed_latency | 0.10x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,808.7 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 2,037,119.2 | 3.672 | layer_fixed_latency | 5.57x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,648.9 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.13 | 57,705.9 | 0.624 | weight_read | 0.16x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,808.7 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 2,037,119.2 | 3.672 | layer_fixed_latency | 5.57x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 27,875.3 | 0.603 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 167,961.4 | 1.817 | weight_read | 0.46x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.88 | 87,233.1 | 0.944 | weight_read | 0.24x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 8.19 | 1.18 | 177,466.1 | 1.920 | layer_fixed_latency | 0.49x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 530,912.2 | 3.828 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 2,037,119.2 | 3.672 | layer_fixed_latency | 3.84x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 29,014.6 | 0.628 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 2.25 | 192,467.0 | 2.082 | weight_read | 0.36x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 4.03 | 162,047.4 | 1.753 | weight_read | 0.31x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 8.19 | 2.20 | 473,281.8 | 5.119 | layer_fixed_latency | 0.89x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 977,296.3 | 5.286 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 2,603,562.3 | 4.694 | layer_fixed_latency | 2.66x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 8.98 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 8.98 | 211,097.0 | 2.283 | weight_read | 0.22x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 8.80 | 275,144.7 | 2.976 | weight_read | 0.28x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 8.19 | 3.05 | 823,372.5 | 8.906 | kv_read | 0.84x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 1,705,703.6 | 4.613 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,136,879.2 | 7.458 | compute | 2.43x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 35.93 | 26,113.2 | 0.282 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 35.93 | 213,947.5 | 2.314 | weight_read | 0.13x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 14.47 | 434,329.0 | 4.698 | weight_read | 0.25x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 4.28 | 987,880.0 | 10.686 | kv_read | 0.58x |

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
| DeepSeek-V4-Flash-0731 | 1 | 14 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 14 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 57 | 1.12 | 1.001 | 1.014 | 1.01x |
| DeepSeek-V4-Flash-0731 | 256 | 57 | 4.49 | 1.042 | 1.670 | 1.60x |
| DeepSeek-V4-Flash-0731 | 1024 | 16 | 64.00 | 1.921 | 5.831 | 3.04x |
| DeepSeek-V4-Flash-0731 | 4096 | 16 | 256.00 | 6.014 | 13.844 | 2.30x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 7 | 4.22 | 2.86 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 7 | 5.88 | 3.47 | 1.69x |
| DeepSeek-V4-Flash-0731 | 4 | 7 | 6.80 | 4.07 | 1.67x |
| DeepSeek-V4-Flash-0731 | 8 | 7 | 6.99 | 4.62 | 1.51x |
| DeepSeek-V4-Flash-0731 | 16 | 7 | 7.00 | 5.08 | 1.38x |
| DeepSeek-V4-Flash-0731 | 32 | 7 | 7.00 | 5.42 | 1.29x |
| DeepSeek-V4-Flash-0731 | 64 | 7 | 7.00 | 5.65 | 1.24x |
| DeepSeek-V4-Flash-0731 | 256 | 7 | 7.00 | 5.78 | 1.21x |
| DeepSeek-V4-Flash-0731 | 1024 | 7 | 7.00 | 5.78 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4096 | 7 | 7.00 | 5.78 | 1.21x |
| DeepSeek-V4-Flash-0731 | 1 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 8 | 6.36 | 3.68 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 8 | 7.64 | 4.38 | 1.74x |
| DeepSeek-V4-Flash-0731 | 8 | 8 | 7.98 | 5.03 | 1.59x |
| DeepSeek-V4-Flash-0731 | 16 | 8 | 8.00 | 5.58 | 1.43x |
| DeepSeek-V4-Flash-0731 | 32 | 8 | 8.00 | 6.01 | 1.33x |
| DeepSeek-V4-Flash-0731 | 64 | 8 | 8.00 | 6.29 | 1.27x |
| DeepSeek-V4-Flash-0731 | 256 | 8 | 8.00 | 6.45 | 1.24x |
| DeepSeek-V4-Flash-0731 | 1024 | 8 | 8.00 | 6.45 | 1.24x |
| DeepSeek-V4-Flash-0731 | 4096 | 8 | 8.00 | 6.45 | 1.24x |
| DeepSeek-V4-Flash-0731 | 1 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Flash-0731 | 2 | 14 | 8.19 | 4.61 | 1.78x |
| DeepSeek-V4-Flash-0731 | 4 | 14 | 11.49 | 5.79 | 1.98x |
| DeepSeek-V4-Flash-0731 | 8 | 14 | 13.47 | 6.99 | 1.93x |
| DeepSeek-V4-Flash-0731 | 16 | 14 | 13.96 | 8.09 | 1.73x |
| DeepSeek-V4-Flash-0731 | 32 | 14 | 14.00 | 9.00 | 1.55x |
| DeepSeek-V4-Flash-0731 | 64 | 14 | 14.00 | 9.63 | 1.45x |
| DeepSeek-V4-Flash-0731 | 256 | 14 | 14.00 | 10.00 | 1.40x |
| DeepSeek-V4-Flash-0731 | 1024 | 14 | 14.00 | 10.00 | 1.40x |
| DeepSeek-V4-Flash-0731 | 4096 | 14 | 14.00 | 10.00 | 1.40x |
| DeepSeek-V4-Flash-0731 | 1 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 2 | 16 | 8.56 | 4.83 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 16 | 12.41 | 6.15 | 2.02x |
| DeepSeek-V4-Flash-0731 | 8 | 16 | 15.08 | 7.51 | 2.01x |
| DeepSeek-V4-Flash-0731 | 16 | 16 | 15.91 | 8.79 | 1.81x |
| DeepSeek-V4-Flash-0731 | 32 | 16 | 16.00 | 9.86 | 1.62x |
| DeepSeek-V4-Flash-0731 | 64 | 16 | 16.00 | 10.60 | 1.51x |
| DeepSeek-V4-Flash-0731 | 256 | 16 | 16.00 | 11.05 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1024 | 16 | 16.00 | 11.05 | 1.45x |
| DeepSeek-V4-Flash-0731 | 4096 | 16 | 16.00 | 11.05 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 2 | 17 | 8.72 | 4.94 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 17 | 12.83 | 6.31 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 17 | 15.84 | 7.75 | 2.04x |
| DeepSeek-V4-Flash-0731 | 16 | 17 | 16.87 | 9.12 | 1.85x |
| DeepSeek-V4-Flash-0731 | 32 | 17 | 17.00 | 10.27 | 1.65x |
| DeepSeek-V4-Flash-0731 | 64 | 17 | 17.00 | 11.07 | 1.54x |
| DeepSeek-V4-Flash-0731 | 256 | 17 | 17.00 | 11.55 | 1.47x |
| DeepSeek-V4-Flash-0731 | 1024 | 17 | 17.00 | 11.56 | 1.47x |
| DeepSeek-V4-Flash-0731 | 4096 | 17 | 17.00 | 11.56 | 1.47x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 8.86 | 5.03 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 13.21 | 6.47 | 2.04x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 16.56 | 7.99 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 17.82 | 9.44 | 1.89x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 17.99 | 10.67 | 1.69x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 18.00 | 11.53 | 1.56x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1024 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 4096 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 8.99 | 5.12 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 13.57 | 6.62 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 17.26 | 8.21 | 2.10x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 18.76 | 9.75 | 1.92x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 18.99 | 11.05 | 1.72x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 19.00 | 11.97 | 1.59x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1024 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 4096 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 2 | 20 | 9.11 | 5.21 | 1.75x |
| DeepSeek-V4-Flash-0731 | 4 | 20 | 13.91 | 6.76 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 20 | 17.93 | 8.43 | 2.13x |
| DeepSeek-V4-Flash-0731 | 16 | 20 | 19.68 | 10.04 | 1.96x |
| DeepSeek-V4-Flash-0731 | 32 | 20 | 19.98 | 11.42 | 1.75x |
| DeepSeek-V4-Flash-0731 | 64 | 20 | 20.00 | 12.40 | 1.61x |
| DeepSeek-V4-Flash-0731 | 256 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 1024 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4096 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 1 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 2 | 21 | 9.23 | 5.29 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 21 | 14.22 | 6.90 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 21 | 18.57 | 8.63 | 2.15x |
| DeepSeek-V4-Flash-0731 | 16 | 21 | 20.59 | 10.33 | 1.99x |
| DeepSeek-V4-Flash-0731 | 32 | 21 | 20.97 | 11.79 | 1.78x |
| DeepSeek-V4-Flash-0731 | 64 | 21 | 21.00 | 12.82 | 1.64x |
| DeepSeek-V4-Flash-0731 | 256 | 21 | 21.00 | 13.46 | 1.56x |
| DeepSeek-V4-Flash-0731 | 1024 | 21 | 21.00 | 13.46 | 1.56x |
| DeepSeek-V4-Flash-0731 | 4096 | 21 | 21.00 | 13.46 | 1.56x |
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 9.33 | 5.36 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 14.51 | 7.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 19.19 | 8.83 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 21.49 | 10.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 21.96 | 12.14 | 1.81x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 22.00 | 13.24 | 1.66x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1024 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 4096 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4-Flash-0731 | 2 | 24 | 9.51 | 5.51 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 24 | 15.05 | 7.28 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 24 | 20.35 | 9.21 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 24 | 23.23 | 11.14 | 2.09x |
| DeepSeek-V4-Flash-0731 | 32 | 24 | 23.93 | 12.82 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 24 | 24.00 | 14.03 | 1.71x |
| DeepSeek-V4-Flash-0731 | 256 | 24 | 24.00 | 14.78 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 24 | 24.00 | 14.79 | 1.62x |
| DeepSeek-V4-Flash-0731 | 4096 | 24 | 24.00 | 14.79 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1 | 25 | 5.43 | 4.15 | 1.31x |
| DeepSeek-V4-Flash-0731 | 2 | 25 | 9.59 | 5.58 | 1.72x |
| DeepSeek-V4-Flash-0731 | 4 | 25 | 15.29 | 7.40 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 25 | 20.89 | 9.39 | 2.22x |
| DeepSeek-V4-Flash-0731 | 16 | 25 | 24.08 | 11.39 | 2.11x |
| DeepSeek-V4-Flash-0731 | 32 | 25 | 24.90 | 13.15 | 1.89x |
| DeepSeek-V4-Flash-0731 | 64 | 25 | 24.99 | 14.42 | 1.73x |
| DeepSeek-V4-Flash-0731 | 256 | 25 | 25.00 | 15.20 | 1.64x |
| DeepSeek-V4-Flash-0731 | 1024 | 25 | 25.00 | 15.21 | 1.64x |
| DeepSeek-V4-Flash-0731 | 4096 | 25 | 25.00 | 15.21 | 1.64x |
| DeepSeek-V4-Flash-0731 | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 2 | 28 | 9.81 | 5.76 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 28 | 15.94 | 7.73 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 28 | 22.40 | 9.90 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 28 | 26.52 | 12.12 | 2.19x |
| DeepSeek-V4-Flash-0731 | 32 | 28 | 27.80 | 14.09 | 1.97x |
| DeepSeek-V4-Flash-0731 | 64 | 28 | 27.98 | 15.53 | 1.80x |
| DeepSeek-V4-Flash-0731 | 256 | 28 | 28.00 | 16.42 | 1.70x |
| DeepSeek-V4-Flash-0731 | 1024 | 28 | 28.00 | 16.43 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4096 | 28 | 28.00 | 16.43 | 1.70x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 9.87 | 5.82 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 16.14 | 7.83 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 22.86 | 10.06 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 27.30 | 12.35 | 2.21x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 28.76 | 14.39 | 2.00x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 28.97 | 15.88 | 1.82x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 1024 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 4096 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 1 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 30 | 9.93 | 5.88 | 1.69x |
| DeepSeek-V4-Flash-0731 | 4 | 30 | 16.32 | 7.93 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 30 | 23.31 | 10.22 | 2.28x |
| DeepSeek-V4-Flash-0731 | 16 | 30 | 28.06 | 12.57 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 30 | 29.70 | 14.68 | 2.02x |
| DeepSeek-V4-Flash-0731 | 64 | 30 | 29.97 | 16.23 | 1.85x |
| DeepSeek-V4-Flash-0731 | 256 | 30 | 29.99 | 17.20 | 1.74x |
| DeepSeek-V4-Flash-0731 | 1024 | 30 | 29.99 | 17.21 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4096 | 30 | 29.99 | 17.21 | 1.74x |
| DeepSeek-V4-Flash-0731 | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 41 | 10.41 | 6.41 | 1.62x |
| DeepSeek-V4-Flash-0731 | 4 | 41 | 17.86 | 8.85 | 2.02x |
| DeepSeek-V4-Flash-0731 | 8 | 41 | 27.25 | 11.69 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 41 | 35.43 | 14.72 | 2.41x |
| DeepSeek-V4-Flash-0731 | 32 | 41 | 39.58 | 17.55 | 2.25x |
| DeepSeek-V4-Flash-0731 | 64 | 41 | 40.71 | 19.69 | 2.07x |
| DeepSeek-V4-Flash-0731 | 256 | 41 | 40.93 | 21.05 | 1.94x |
| DeepSeek-V4-Flash-0731 | 1024 | 41 | 40.93 | 21.07 | 1.94x |
| DeepSeek-V4-Flash-0731 | 4096 | 41 | 40.93 | 21.07 | 1.94x |
| DeepSeek-V4-Flash-0731 | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 44 | 10.50 | 6.53 | 1.61x |
| DeepSeek-V4-Flash-0731 | 4 | 44 | 18.17 | 9.06 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 44 | 28.09 | 12.03 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 44 | 37.14 | 15.23 | 2.44x |
| DeepSeek-V4-Flash-0731 | 32 | 44 | 42.08 | 18.24 | 2.31x |
| DeepSeek-V4-Flash-0731 | 64 | 44 | 43.56 | 20.53 | 2.12x |
| DeepSeek-V4-Flash-0731 | 256 | 44 | 43.88 | 22.00 | 1.99x |
| DeepSeek-V4-Flash-0731 | 1024 | 44 | 43.88 | 22.01 | 1.99x |
| DeepSeek-V4-Flash-0731 | 4096 | 44 | 43.88 | 22.01 | 1.99x |
| DeepSeek-V4-Flash-0731 | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 55 | 10.76 | 6.93 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 55 | 19.05 | 9.71 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 55 | 30.58 | 13.11 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 55 | 42.52 | 16.89 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 55 | 50.48 | 20.52 | 2.46x |
| DeepSeek-V4-Flash-0731 | 64 | 55 | 53.60 | 23.34 | 2.30x |
| DeepSeek-V4-Flash-0731 | 256 | 55 | 54.49 | 25.18 | 2.16x |
| DeepSeek-V4-Flash-0731 | 1024 | 55 | 54.50 | 25.19 | 2.16x |
| DeepSeek-V4-Flash-0731 | 4096 | 55 | 54.50 | 25.19 | 2.16x |
| DeepSeek-V4-Flash-0731 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 58 | 10.81 | 7.02 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4 | 58 | 19.24 | 9.86 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 58 | 31.13 | 13.37 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 58 | 43.78 | 17.30 | 2.53x |
| DeepSeek-V4-Flash-0731 | 32 | 58 | 52.57 | 21.09 | 2.49x |
| DeepSeek-V4-Flash-0731 | 64 | 58 | 56.21 | 24.04 | 2.34x |
| DeepSeek-V4-Flash-0731 | 256 | 58 | 57.32 | 25.97 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1024 | 58 | 57.32 | 25.99 | 2.21x |
| DeepSeek-V4-Flash-0731 | 4096 | 58 | 57.32 | 25.99 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 59 | 10.83 | 7.05 | 1.53x |
| DeepSeek-V4-Flash-0731 | 4 | 59 | 19.30 | 9.90 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 59 | 31.31 | 13.45 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 59 | 44.18 | 17.43 | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | 59 | 53.24 | 21.27 | 2.50x |
| DeepSeek-V4-Flash-0731 | 64 | 59 | 57.06 | 24.27 | 2.35x |
| DeepSeek-V4-Flash-0731 | 256 | 59 | 58.25 | 26.23 | 2.22x |
| DeepSeek-V4-Flash-0731 | 1024 | 59 | 58.26 | 26.25 | 2.22x |
| DeepSeek-V4-Flash-0731 | 4096 | 59 | 58.26 | 26.25 | 2.22x |
| DeepSeek-V4-Flash-0731 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 87 | 11.15 | 7.78 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 87 | 20.44 | 10.95 | 1.87x |
| DeepSeek-V4-Flash-0731 | 8 | 87 | 34.83 | 15.44 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 87 | 52.83 | 20.51 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 87 | 68.97 | 25.63 | 2.69x |
| DeepSeek-V4-Flash-0731 | 64 | 87 | 78.37 | 29.78 | 2.63x |
| DeepSeek-V4-Flash-0731 | 256 | 87 | 82.46 | 32.55 | 2.53x |
| DeepSeek-V4-Flash-0731 | 1024 | 87 | 82.49 | 32.58 | 2.53x |
| DeepSeek-V4-Flash-0731 | 4096 | 87 | 82.49 | 32.58 | 2.53x |
| DeepSeek-V4-Flash-0731 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 116 | 11.32 | 8.33 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 116 | 21.08 | 11.71 | 1.80x |
| DeepSeek-V4-Flash-0731 | 8 | 116 | 36.91 | 16.98 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 116 | 58.39 | 22.88 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 116 | 80.31 | 29.09 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 116 | 95.45 | 34.23 | 2.79x |
| DeepSeek-V4-Flash-0731 | 256 | 116 | 103.29 | 37.73 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1024 | 116 | 103.36 | 37.77 | 2.74x |
| DeepSeek-V4-Flash-0731 | 4096 | 116 | 103.36 | 37.77 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 173 | 11.49 | 9.06 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 173 | 21.74 | 12.85 | 1.69x |
| DeepSeek-V4-Flash-0731 | 8 | 173 | 39.14 | 19.00 | 2.06x |
| DeepSeek-V4-Flash-0731 | 16 | 173 | 64.73 | 26.15 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 173 | 94.43 | 34.13 | 2.77x |
| DeepSeek-V4-Flash-0731 | 64 | 173 | 118.70 | 40.88 | 2.90x |
| DeepSeek-V4-Flash-0731 | 256 | 173 | 133.64 | 45.54 | 2.93x |
| DeepSeek-V4-Flash-0731 | 1024 | 173 | 133.78 | 45.59 | 2.93x |
| DeepSeek-V4-Flash-0731 | 4096 | 173 | 133.78 | 45.59 | 2.93x |
| DeepSeek-V4-Flash-0731 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 231 | 11.58 | 9.55 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 231 | 22.09 | 13.78 | 1.60x |
| DeepSeek-V4-Flash-0731 | 8 | 231 | 40.34 | 20.26 | 1.99x |
| DeepSeek-V4-Flash-0731 | 16 | 231 | 68.33 | 28.71 | 2.38x |
| DeepSeek-V4-Flash-0731 | 32 | 231 | 103.04 | 37.98 | 2.71x |
| DeepSeek-V4-Flash-0731 | 64 | 231 | 133.95 | 45.87 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 231 | 154.72 | 51.61 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 231 | 154.92 | 51.66 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 231 | 154.92 | 51.66 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 347 | 11.68 | 10.15 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 347 | 22.44 | 15.21 | 1.48x |
| DeepSeek-V4-Flash-0731 | 8 | 347 | 41.59 | 21.88 | 1.90x |
| DeepSeek-V4-Flash-0731 | 16 | 347 | 72.20 | 32.56 | 2.22x |
| DeepSeek-V4-Flash-0731 | 32 | 347 | 112.75 | 43.11 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 347 | 152.11 | 53.42 | 2.85x |
| DeepSeek-V4-Flash-0731 | 256 | 347 | 180.96 | 60.40 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 347 | 181.25 | 60.47 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 347 | 181.25 | 60.47 | 3.00x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 890.50 | 55.1% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 268.01 | 95.1% |

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
| DeepSeek-V4-Flash-0731 | 1 | 14 | 32.17% | 11.92 | 2.65 |
| DeepSeek-V4-Flash-0731 | 2 | 14 | 32.17% | 11.92 | 2.65 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 0.27% | 0.40 | 2.65 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 0.27% | 0.40 | 2.65 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 0.27% | 0.40 | 2.65 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 0.27% | 0.40 | 2.65 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 0.30% | 0.45 | 2.65 |
| DeepSeek-V4-Flash-0731 | 256 | 1 | 1.19% | 1.80 | 2.65 |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 958.3 | 29,707.0 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 958.3 | 29,707.0 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 958.3 | 29,707.0 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 958.3 | 29,707.0 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 958.3 | 29,707.0 |
| DeepSeek-V4-Flash-0731 | 32 | 2.42% | 11.3 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 932.3 | 29,832.5 |
| DeepSeek-V4-Flash-0731 | 64 | 4.78% | 14.8 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 500.7 | 32,045.5 |
| DeepSeek-V4-Flash-0731 | 256 | 17.79% | 33.9 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 132.3 | 33,873.2 |
| DeepSeek-V4-Flash-0731 | 1024 | 54.32% | 87.7 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 33.5 | 34,288.8 |
| DeepSeek-V4-Flash-0731 | 4096 | 95.64% | 148.5 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 8.4 | 34,218.0 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | layer_fixed_latency | 379 |
| gpu | link_latency | 800 |
| gpu | thermal | 40 |
| gpu | weight_read | 311 |
| rom | compute | 489 |
| rom | infeasible | 2228 |
| rom | kv_read | 40 |
| rom | layer_fixed_latency | 1095 |
| rom | link_latency | 896 |
| rom | weight_read | 412 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2228 |

## Mechanical consistency audit

**FAIL** over 141,263 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x28', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x31', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x32', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x34', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x40', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x54', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x81', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x108', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x28', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x31', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x32', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x34', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x40', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x54', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x81', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x108', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x28', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x31', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x32', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x34', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x40', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x54', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x81', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x108', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x28', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x31', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x32', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x34', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x40', 'DeepSeek-V4-Flash-0731', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 50 |
| assumed | 85 |

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
- `links.rom_wafer_express.fabric`
- `links.rom_wafer_express.hop_latency_s`
- `links.rom_wafer_express.router_latency_s`
- `links.rom_wafer_express.wire_clock_hz`
- `links.rom_wafer_express.wire_layers`
- `links.rom_wafer_express.wire_track_pitch_um`
- `links.rom_wafer_express.wire_track_share`
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
- `serial_latency.hardware_links.rom_wafer_express`
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

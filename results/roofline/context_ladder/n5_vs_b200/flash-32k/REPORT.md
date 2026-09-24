# Area-constrained roofline: n5_vs_b200-flash-32k

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Flash-0731 at 32,768 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 98x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 44 devices. On the GPU side the correction reaches 25x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 41 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 34 x 815 mm2 (27,710 mm2, array, KV in SRAM) at 16,400 tok/s per user and 592 tok/s per 1,000 mm2, holding 1 session, against 17 copies of one unified HBM die at the same silicon: 5.3x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 35,860 mm2 of ROM silicon at 19,717 tok/s per user against 35,200 mm2 of b200_sxm-x22-nvl72-tensor at 3,331 tok/s: **5.9x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 14,701. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 7.30x to it.** At 94,540 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 546.71 tok/s and the same silicon running tensor delivers 3,990 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 2.83x (DeepSeek-V4-Flash-0731, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 1,650 to 53,969 tok/s, and its rate with every slot occupied from 52,791 to 53,969. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 32 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 599 us over NVLink, capping per-user decode at 1,670 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 184.6 us and cap it at 5,416 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 86 of 4246 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 188.8x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 28.93x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 252 of 4,246 feasible points (5.9%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DSV4-Flash/b200_sxm-x7-pipeline` at batch 4096 on 11,200 mm2, throttled 1.11x from 33 to 30 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 75% weight read against 75.3% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x34`** -- 34 x 815 mm2 reticle dies, 27,710 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **16,400.1 tok/s per user** (0.06 ms/token), binding on `link_latency`
- **591.8 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 16,400 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 1,858 W at 0.067 W/mm2, 113.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 17 copies of one unified HBM die -- `b200_sxm-x17-nvl72-tensor`, 27,200 mm2, area ratio 1.0188 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 27,710 | 27,200 | 1.0188 |
| user tok/s | 16,400.1 | 3,091.8 | 5.30x |
| aggregate tok/s | 16,400 | 3,092 | 1.76x |
| resident sessions | 1 | 11,195 | -- |
| J/token | 0.1133 | 3.1150 | 27.5x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 11,195 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x59-nvl72-tensor` at 94,400 mm2 and 3,990.2 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 19,717.5 | 549.8 | 1 | 5.92x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 20,313.6 | 479.3 | 22,784 | 5.85x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x30` | 24,450 | 14,248.5 | 582.8 | 1 | 4.80x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | 27,710 | 16,400.1 | 591.8 | 1 | 5.30x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | 27,710 | 16,400.1 | 591.8 | -- | 591.8 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | 16,649.9 | 583.7 | 306.5 | 591.8 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 19,717.5 | 549.8 | 407.0 | 591.8 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 20,313.6 | 479.3 | 266.8 | 591.8 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x34` **<-- recommended** | 27,710 | 34 | 16,400.1 | 16,400 | 591.8 | 1 | `link_latency` | 1,858 | 113.3 | `b200_sxm-x17-nvl72-tensor` | 5.30x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | 35 | 16,649.9 | 16,650 | 583.7 | 1 | `link_latency` | 1,978 | 118.8 | `b200_sxm-x18-nvl72-tensor` | 5.29x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 44 | 19,717.5 | 19,717 | 549.8 | 1 | `compute` | 3,057 | 155.0 | `b200_sxm-x22-nvl72-tensor` | 5.92x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 52 | 20,313.6 | 264,077 | 479.3 | 22,784 | `weight_read` | 7,739 | 240.1 | `b200_sxm-x26-nvl72-tensor` | 5.85x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 348 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | 27,710 | 16,400.1 | 591.8 | 1 |
| array | 348 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 20,313.6 | 479.3 | 22,784 |
| array | 348 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x30` | 24,450 | 14,248.5 | 582.8 | 1 |
| wafer | 76 | densest | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 5,932.2 | 128.3 | 1 |
| wafer | 76 | fastest | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | 36.0 | 15,072 |
| wafer | 76 | smallest | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 5,932.2 | 128.3 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 20,313.6 | 264,077 | 22,784 | 7,739 | 240.1 | `weight_read` | `b200_sxm-x26-nvl72-tensor` | 3,471.9 | 17,505 | 3,812.4 | 1.019 | 5.85x | 15.9x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | 1,509,105 | 15,072 | 34,113 | 2,478.6 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,947.5 | 80,600 | 11,486.0 | 0.996 | 1.68x | 4.6x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 18,345.9 | 1,045,719 | 99,462 | 32,079 | 1,091.3 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,947.5 | 80,600 | 11,486.0 | 0.997 | 4.65x | 10.5x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | -- | 15,072 | -- | 2,478.6 | -- | -- | -- | -- | -- | 1.001 | 0.36x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 20,313.6 | 264,077 | 22,784 | 7,739 | 125.9 | `weight_read` | `b200_sxm-x26-nvl72-tensor` | 3,218.9 | 17,505 | 2,190.9 | 1.019 | 6.31x | 17.4x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | 1,509,105 | 15,072 | 34,113 | 1,245.2 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,947.5 | 80,600 | 6,337.1 | 0.996 | 1.68x | 5.1x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 18,345.9 | 1,045,719 | 99,462 | 32,079 | 551.5 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,947.5 | 80,600 | 6,337.1 | 0.997 | 4.65x | 11.5x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | -- | 15,072 | -- | 1,245.2 | -- | -- | -- | -- | -- | 1.001 | 0.36x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 20,313.6 | 264,077 | 22,784 | 7,739 | 68.8 | `weight_read` | `b200_sxm-x26-nvl72-tensor` | 2,820.4 | 17,505 | 1,370.8 | 1.019 | 7.20x | 19.9x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | 1,509,105 | 15,072 | 34,113 | 628.4 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,774.4 | 80,600 | 3,468.2 | 0.996 | 1.76x | 5.5x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 18,345.9 | 1,045,719 | 99,462 | 32,079 | 281.6 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,774.4 | 80,600 | 3,468.2 | 0.997 | 4.86x | 12.3x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | -- | 15,072 | -- | 628.4 | -- | -- | -- | -- | -- | 1.001 | 0.36x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 20,313.6 | 264,077 | 22,784 | 7,739 | 40.3 | `weight_read` | `b200_sxm-x26-nvl72-tensor` | 2,288.0 | 17,505 | 943.1 | 1.019 | 8.88x | 23.4x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | 1,509,105 | 15,072 | 34,113 | 320.1 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,477.6 | 80,600 | 2,024.3 | 0.996 | 1.91x | 6.3x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 18,345.9 | 1,045,719 | 99,462 | 32,079 | 146.7 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,477.6 | 80,600 | 2,024.3 | 0.997 | 5.28x | 13.8x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | -- | 15,072 | -- | 320.1 | -- | -- | -- | -- | -- | 1.001 | 0.36x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill` | 70,905 | 19,024.5 | 418,540 | 38,119 | 12,503 | 36.7 | `compute` | `b200_sxm-x44-nvl72-tensor` | 2,224.9 | 30,124 | 798.5 | 1.007 | 8.55x | 21.8x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | 1,509,105 | 15,072 | 34,113 | 165.9 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,026.6 | 80,600 | 1,284.7 | 0.996 | 2.20x | 7.7x |
| 16 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 18,345.9 | 1,045,719 | 99,462 | 32,079 | 79.2 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,026.6 | 80,600 | 1,284.7 | 0.997 | 6.06x | 16.2x |
| 16 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | -- | 15,072 | -- | 165.9 | -- | -- | -- | -- | -- | 1.001 | 0.36x wafer/array | -- |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 18,398.7 | 1,563,886 | 148,974 | 48,020 | 62.1 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 2,764.3 | 120,560 | 1,095.1 | 1.001 | 6.66x | 17.6x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | 1,509,105 | 15,072 | 34,113 | 88.8 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 2,453.2 | 80,600 | 883.2 | 0.996 | 2.71x | 9.9x |
| 32 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 18,345.9 | 1,045,719 | 99,462 | 32,079 | 45.5 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 2,453.2 | 80,600 | 883.2 | 0.997 | 7.48x | 19.4x |
| 32 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | -- | 15,072 | -- | 88.8 | -- | -- | -- | -- | -- | 1.001 | 0.36x wafer/array | -- |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 18,398.7 | 1,563,886 | 148,974 | 48,020 | 36.9 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 2,173.0 | 120,560 | 771.2 | 1.001 | 8.47x | 20.9x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | 1,509,105 | 15,072 | 34,113 | 50.3 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 1,870.2 | 80,600 | 631.3 | 0.996 | 3.55x | 12.6x |
| 64 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 16,962.7 | 1,085,611 | 99,462 | 32,260 | 29.7 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 1,870.2 | 80,600 | 631.3 | 0.997 | 9.07x | 21.2x |
| 64 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,648.0 | -- | 15,072 | -- | 50.3 | -- | -- | -- | -- | -- | 1.001 | 0.39x wafer/array | -- |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 7,883.1 | 2,018,072 | 148,974 | 50,055 | 24.8 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 1,210.5 | 120,560 | 371.6 | 1.001 | 6.51x | 14.4x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 369,800 | 6,648.0 | 3,018,210 | 30,145 | 68,227 | 31.0 | `compute` | `b200_sxm-x231-nvl72-hybrid` | 1,344.7 | 161,221 | 445.7 | 1.001 | 4.94x | 13.6x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 2,266.9 | 2,321,290 | 148,974 | 53,119 | 22.9 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 625.0 | 120,560 | 151.5 | 1.001 | 3.63x | 5.5x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 4,602.0 | 4,712,456 | 45,218 | 100,682 | 21.4 | `compute` | `b200_sxm-x347-nvl72-hybrid` | 828.2 | 242,544 | 231.4 | 0.999 | 5.56x | 8.1x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 580.2 | 2,376,700 | 148,974 | 52,008 | 21.9 | `compute` | `b200_sxm-x173-expert` | 271.7 | 119,888 | 67.5 | 1.001 | 2.14x | 3.1x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,225.1 | 5,018,025 | 45,218 | 97,719 | 19.5 | `compute` | `b200_sxm-x347-expert` | 448.2 | 241,132 | 79.3 | 0.999 | 2.73x | 4.1x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x34` | 27,710 | array | SRAM | 1 |
| 2-16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x52` | 42,380 | array | HBM | 22,784 |
| 32-64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x58` | 47,270 | array | HBM | 25,413 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x87` | 70,905 | array | HBM | 38,119 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x116` | 94,540 | array | HBM | 50,826 |
| 4096 | `ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 138,550 | array | HBM | 74,487 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 32, 36, 37, 44, 49, 51, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 32, 36, 37, 44, 51, 52, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 30, 34, 35, 38, 41, 44, 45, 54, 57, 81, 108, 113, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 30, 34, 35, 38, 41, 44, 45, 54, 57, 81, 108, 113, 170, 227, 340 |

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 24,675.2 tok/s | 1.45x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 110.6 W | 0.44x | within 2x | FAIL |

HC1 binds on `weight_read`. Its component times are weight_read 34.47 us, kv_read 3.13 us, compute 34.47 us, link_latency 0.00 us, layer_fixed_latency 6.06 us.

The model **under**-predicts the shipping part by 0.69x. Rather than tune the densities until the anchor
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
| range low | 70.0 ns/layer | 2.24 us | 27,243.5 | 1.61x | weight_read |
| range stated | 189.4 ns/layer | 6.06 us | 24,675.2 | 1.45x | weight_read |
| range high | 894.8 ns/layer | 28.63 us | 15,847.9 | 0.93x | weight_read |

The per-layer cost that would land the model exactly on the
published figure is **765.5 ns/layer**. It is reported so the distance between the derived value and the fitted one is visible. It is never used as an input.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 24,675.2 | 1.45x | weight_read |
| 3.5 | 24,675.2 | 1.45x | weight_read |
| 4.0 | 24,675.2 | 1.45x | weight_read |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 24,675.2 | 1.45x | weight_read |
| 1,536 | 24,675.2 | 1.45x | weight_read |
| 2,048 | 24,675.2 | 1.45x | weight_read |

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
| Taalas HC1 card power | 200.0-250.0 W | 110.6 W | 0.44x | FAIL |

**Where the watts come from.**

| Term | A100 at TDP | Taalas HC1 |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 6.5 W |
| KV traffic | n/a: one saturating HBM stream | 17.2 W |
| operand delivery | 0.5 W | 20.2 W |
| arithmetic | 103.0 W | 14.4 W |
| static: leakage | 31.4 W | 20.6 W |
| static: clock distribution | 99.0 W | 31.6 W |
| static: memory-interface idle | 14.0 W | 0.0 W |
| **static charged** (max of the enumeration and the measured clocked-idle floor) | 144.4 W | 52.2 W |
| **total** | 461.7 W | 110.6 W |

On HC1 the enumerated static power is 52.2 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 78.8 W | 0.32x | 0.39x |
| stated | 461.7 W | 1.15x | 110.6 W | 0.44x | 0.55x |
| high | 698.3 W | 1.75x | 407.5 W | 1.63x | 2.04x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.44x of the top of its published band, **2.26x low**, against 1.81x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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
| Taalas HC1 (modelled reconstruction) | 0.004480 J/token | 110.6 | 24,675.2 |
| A100 80GB, weight-bound gate, same model and batch | 1.465768 J/token | 359.6 | 245.3 |

That is a factor of 327 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 1.8-2.3x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

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

- **252 of 4,246 feasible points (5.9%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 250, rom 2.
- By area class: large array (5,000-40,000 mm2) 102, wafer (>=40,000 mm2) 150.
- By KV store: hbm 252.
- By batch: B=1 25, B=2 25, B=4 25, B=8 25, B=16 25, B=32 25, B=64 25, B=256 25, B=1024 25, B=4096 27.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 46% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 580 | 100 | 69.3% | 100.0% | 0.625 | 51% |
| gpu | wafer (>=40,000 mm2) | 950 | 150 | 50.9% | 100.0% | 0.625 | 69% |
| rom | large array (5,000-40,000 mm2) | 924 | 2 | 22.2% | 100.0% | 0.500 | 80% |
| rom | wafer (>=40,000 mm2) | 1,792 | 0 | 30.0% | 57.7% | 0.289 | 86% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DSV4-Flash/b200_sxm-x7-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 11,200 | hbm | 1.110x | 7,000.0 / 7,000.0 W | 35% | 30.1 | 33.4 |
| `DSV4-Flash/b200_sxm-x8-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 12,800 | hbm | 1.104x | 8,000.0 / 8,000.0 W | 35% | 31.1 | 34.3 |
| `DSV4-Flash/b200_sxm-x15-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 24,000 | hbm | 1.078x | 15,000.0 / 15,000.0 W | 35% | 34.7 | 37.4 |
| `DSV4-Flash/b200_sxm-x16-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 25,600 | hbm | 1.076x | 16,000.0 / 16,000.0 W | 35% | 35.0 | 37.6 |
| `DSV4-Flash/b200_sxm-x17-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 27,200 | hbm | 1.073x | 17,000.0 / 17,000.0 W | 35% | 35.3 | 37.8 |
| `DSV4-Flash/b200_sxm-x18-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 28,800 | hbm | 1.071x | 18,000.0 / 18,000.0 W | 35% | 35.5 | 38.1 |
| `DSV4-Flash/b200_sxm-x19-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 30,400 | hbm | 1.070x | 19,000.0 / 19,000.0 W | 35% | 35.8 | 38.3 |
| `DSV4-Flash/b200_sxm-x21-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 33,600 | hbm | 1.068x | 21,000.0 / 21,000.0 W | 35% | 36.3 | 38.7 |
| `DSV4-Flash/b200_sxm-x22-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 35,200 | hbm | 1.067x | 22,000.0 / 22,000.0 W | 35% | 36.5 | 39.0 |
| `DSV4-Flash/b200_sxm-x7-pipeline` | DeepSeek-V4-Flash-0731 | 1024 | 11,200 | hbm | 1.067x | 7,000.0 / 7,000.0 W | 35% | 37.9 | 40.5 |
| `DSV4-Flash/b200_sxm-x23-pipeline` | DeepSeek-V4-Flash-0731 | 4096 | 36,800 | hbm | 1.066x | 23,000.0 / 23,000.0 W | 35% | 36.8 | 39.2 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x16-perregion-romfill` | DeepSeek-V4-Flash-0731 | 4096 | 13,040 | hbm | 1.065x | 6,520.0 / 6,520.0 W | 18% | 155.7 | 165.8 |

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
| DeepSeek-V4-Flash-0731 | 1 | 35,860 | `DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x44` | 0.155026 | 3,056.7 | compute | `DSV4-Flash/b200_sxm-x22-nvl72-tensor` | 3.502446 | 11,667.7 | link_latency | 22.59x |
| DeepSeek-V4-Flash-0731 | 2 | 41,565 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 0.126000 | 7,516.7 | compute | `DSV4-Flash/b200_sxm-x26-nvl72-tensor` | 2.190922 | 14,104.7 | link_latency | 17.39x |
| DeepSeek-V4-Flash-0731 | 4 | 41,565 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 0.068869 | 7,516.7 | compute | `DSV4-Flash/b200_sxm-x26-nvl72-tensor` | 1.370814 | 15,465.1 | link_latency | 19.90x |
| DeepSeek-V4-Flash-0731 | 8 | 41,565 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x51` | 0.040304 | 7,516.7 | compute | `DSV4-Flash/b200_sxm-x26-nvl72-tensor` | 0.943057 | 17,261.9 | link_latency | 23.40x |
| DeepSeek-V4-Flash-0731 | 16 | 47,270 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill` | 0.029020 | 8,423.4 | compute | `DSV4-Flash/b200_sxm-x30-nvl72-tensor` | 0.719901 | 21,347.8 | weight_read | 24.81x |
| DeepSeek-V4-Flash-0731 | 32 | 94,540 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill` | 0.029415 | 16,627.3 | compute | `DSV4-Flash/b200_sxm-x59-nvl72-tensor` | 0.629724 | 38,512.9 | link_latency | 21.41x |
| DeepSeek-V4-Flash-0731 | 64 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.036930 | 48,020.2 | compute | `DSV4-Flash/b200_sxm-x173-nvl72-hybrid` | 0.771161 | 107,249.4 | link_latency | 20.88x |
| DeepSeek-V4-Flash-0731 | 256 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.024803 | 50,054.8 | compute | `DSV4-Flash/b200_sxm-x173-nvl72-hybrid` | 0.371566 | 115,148.1 | link_latency | 14.40x |
| DeepSeek-V4-Flash-0731 | 1024 | 554,700 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.021365 | 100,682.1 | compute | `DSV4-Flash/b200_sxm-x347-nvl72-hybrid` | 0.231362 | 196,214.1 | link_latency | 8.09x |
| DeepSeek-V4-Flash-0731 | 4096 | 554,700 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.019474 | 97,719.3 | compute | `DSV4-Flash/b200_sxm-x347-expert` | 0.079265 | 145,503.7 | link_latency | 4.07x |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 49,283.7 | wafer-pipeline | 5,932.2 | wafer-pipeline | 8.31x | 8,960.3 | pipeline | 3,557.4 | tensor | 2.52x | 5.50x | 1.67x | 0.30x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 53,155.7 | wafer-pipeline | 6,622.3 | wafer-pipeline | 8.03x | 10,081.5 | pipeline | 3,982.1 | tensor | 2.53x | 5.27x | 1.66x | 0.32x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 54,280.8 | wafer-pipeline | 6,622.3 | wafer-pipeline | 8.20x | 11,226.6 | pipeline | 3,797.5 | hybrid | 2.96x | 4.84x | 1.74x | 0.36x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 54,861.4 | wafer-pipeline | 6,648.0 | wafer-pipeline | 8.25x | 11,902.5 | pipeline | 3,947.5 | hybrid | 3.02x | 4.61x | 1.68x | 0.37x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 55,454.6 | wafer-pipeline | 6,639.4 | wafer-pipeline | 8.35x | 12,655.6 | pipeline | 3,911.0 | hybrid | 3.24x | 4.38x | 1.70x | 0.39x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 55,756.0 | wafer-pipeline | 6,648.0 | wafer-pipeline | 8.39x | 13,078.4 | pipeline | 3,878.3 | hybrid | 3.37x | 4.26x | 1.71x | 0.40x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 56,060.7 | wafer-pipeline | 6,648.0 | wafer-pipeline | 8.43x | 13,529.2 | pipeline | 3,922.0 | hybrid | 3.45x | 4.14x | 1.70x | 0.41x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.30x to 0.41x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x52 | 42,380 | 20,313.6 | 264,077.0 | weight_read | DSV4-Flash/b200_sxm-x26-nvl72-tensor | 41,600 | 1.02x | tensor | 208.66 | 3,471.9 | 3,471.9 | link_latency | 5.85x | 18.58x | 37.16x | 5.85x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x30 | 24,450 | 14,248.5 | 14,248.5 | link_latency | DSV4-Flash/b200_sxm-x15-nvl72-tensor | 24,000 | 1.02x | tensor | 208.59 | 2,966.7 | 2,966.7 | link_latency | 4.80x | 1.74x | 26.06x | 4.80x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x52 | 42,380 | 20,313.6 | 264,077.0 | weight_read | DSV4-Flash/b200_sxm-x26-nvl72-tensor | 41,600 | 1.02x | tensor | 210.92 | 3,218.9 | 6,437.8 | link_latency | 6.31x | 18.58x | 37.16x | 6.31x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x32 | 26,080 | 10,887.7 | 21,775.3 | link_latency | DSV4-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 210.80 | 2,738.6 | 5,477.2 | link_latency | 3.98x | 2.49x | 19.91x | 3.98x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x52 | 42,380 | 20,313.6 | 264,077.0 | weight_read | DSV4-Flash/b200_sxm-x26-nvl72-tensor | 41,600 | 1.02x | tensor | 215.43 | 2,820.4 | 11,281.7 | link_latency | 7.20x | 18.58x | 37.16x | 7.20x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x32 | 26,080 | 7,590.6 | 30,362.5 | compute | DSV4-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 215.21 | 2,306.6 | 9,226.4 | link_latency | 3.29x | 3.29x | 13.88x | 3.29x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x52 | 42,380 | 20,313.6 | 264,077.0 | weight_read | DSV4-Flash/b200_sxm-x26-nvl72-tensor | 41,600 | 1.02x | tensor | 224.46 | 2,288.0 | 18,304.2 | link_latency | 8.88x | 14.43x | 37.16x | 8.88x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x32 | 26,080 | 6,118.9 | 48,951.1 | compute | DSV4-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 224.01 | 1,780.2 | 14,241.7 | weight_read | 3.44x | 3.44x | 11.19x | 3.44x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x87-romfill | 70,905 | 19,024.5 | 418,539.7 | compute | DSV4-Flash/b200_sxm-x44-nvl72-tensor | 70,400 | 1.01x | tensor | 243.12 | 2,224.9 | 35,598.9 | link_latency | 8.55x | 11.76x | 34.80x | 8.55x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x32 | 26,080 | 3,204.7 | 51,274.8 | compute | DSV4-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 241.63 | 1,270.1 | 20,321.3 | weight_read | 2.52x | 2.52x | 5.86x | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 18,398.7 | 1,563,885.8 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 238.66 | 2,764.3 | 88,458.9 | link_latency | 6.66x | 16.53x | 33.65x | 6.66x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 1,649.7 | 52,791.1 | compute | DSV4-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 276.85 | 877.6 | 28,083.7 | weight_read | 1.88x | 1.88x | 3.94x | 1.88x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 18,398.7 | 1,563,885.8 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 266.85 | 2,173.0 | 139,075.2 | link_latency | 8.47x | 11.24x | 33.65x | 8.47x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 834.0 | 53,378.1 | compute | DSV4-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 347.30 | 631.4 | 40,411.9 | weight_read | 1.32x | 1.32x | 2.89x | 1.32x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 7,883.1 | 2,018,072.2 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 436.03 | 1,210.5 | 309,899.4 | link_latency | 6.51x | 6.51x | 16.55x | 6.51x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 210.3 | 53,827.0 | compute | DSV4-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 770.01 | 410.4 | 105,071.9 | weight_read | 0.51x | 0.51x | 1.89x | 0.51x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4,602.0 | 4,712,455.5 | compute | DSV4-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 823.00 | 828.2 | 848,083.2 | link_latency | 5.56x | 5.56x | 13.38x | 5.56x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 52.7 | 53,940.4 | compute | DSV4-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 2,460.84 | 216.5 | 221,679.9 | link_latency | 0.24x | 0.24x | 1.09x | 0.24x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,225.1 | 5,018,024.5 | compute | DSV4-Flash/b200_sxm-x347-expert | 555,200 | 1.00x | expert | 1,574.64 | 448.2 | 1,835,660.7 | link_latency | 2.73x | 2.73x | 8.87x | 2.73x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 13.2 | 53,968.8 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 1.02x | hybrid | 4,752.26 | 96.5 | 395,365.0 | link_latency | 0.14x | 0.14x | 0.38x | 0.14x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 7 | 11,200 | 208.41 | 208.41 | 2,129.6 | 2,129.6 |
| DeepSeek-V4-Flash-0731 | 8 | 12,800 | 208.45 | 208.45 | 2,280.5 | 2,280.5 |
| DeepSeek-V4-Flash-0731 | 15 | 24,000 | 208.59 | 208.59 | 2,966.7 | 2,966.7 |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 208.60 | 208.60 | 3,031.9 | 3,031.9 |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 208.61 | 208.61 | 3,091.8 | 3,091.8 |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 208.62 | 208.62 | 3,147.1 | 3,147.1 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 208.62 | 208.62 | 3,198.3 | 3,198.3 |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 208.64 | 208.64 | 3,290.0 | 3,290.0 |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 208.64 | 208.64 | 3,331.3 | 3,331.3 |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 208.65 | 208.65 | 3,369.9 | 3,369.9 |
| DeepSeek-V4-Flash-0731 | 25 | 40,000 | 208.65 | 208.65 | 3,440.0 | 3,440.0 |
| DeepSeek-V4-Flash-0731 | 26 | 41,600 | 208.66 | 208.66 | 3,471.9 | 3,471.9 |
| DeepSeek-V4-Flash-0731 | 28 | 44,800 | 208.66 | 208.66 | 3,530.5 | 3,530.5 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 208.67 | 208.67 | 3,557.4 | 3,557.4 |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 208.67 | 208.67 | 3,582.9 | 3,582.9 |
| DeepSeek-V4-Flash-0731 | 41 | 65,600 | 208.69 | 208.69 | 3,794.3 | 3,794.3 |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 208.70 | 208.70 | 3,836.4 | 3,836.4 |
| DeepSeek-V4-Flash-0731 | 55 | 88,000 | 208.71 | 208.71 | 3,956.3 | 3,956.3 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 208.71 | 208.71 | 3,982.1 | 3,982.1 |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 208.71 | 208.71 | 3,990.2 | 3,990.2 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 210.91 | 210.91 | 3,797.5 | 3,797.5 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 210.91 | 210.91 | 3,947.5 | 3,947.5 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 213.10 | 213.10 | 3,911.0 | 3,911.0 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 215.30 | 215.30 | 3,878.3 | 3,878.3 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 217.49 | 217.49 | 3,922.0 | 3,922.0 |

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
| DeepSeek-V4-Flash-0731 | 7 | 11,200 | 546.7 | 2,129.6 | — | tensor | 208.41 | 44.4% | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | 12,800 | 546.7 | 2,280.5 | — | tensor | 208.45 | 47.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 15 | 24,000 | 546.7 | 2,966.7 | 2,196.8 | tensor | 208.59 | 61.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 546.7 | 3,031.9 | 2,269.1 | tensor | 208.60 | 63.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 546.7 | 3,091.8 | 1,877.9 | tensor | 208.61 | 64.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 546.7 | 3,147.1 | 1,940.1 | tensor | 208.62 | 65.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 546.7 | 3,198.3 | 1,999.3 | tensor | 208.62 | 66.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 546.7 | 3,290.0 | 2,109.7 | tensor | 208.64 | 68.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 546.7 | 3,331.3 | 2,161.3 | tensor | 208.64 | 69.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 546.7 | 3,369.9 | 2,210.6 | tensor | 208.65 | 70.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 25 | 40,000 | 546.7 | 3,440.0 | 1,976.1 | tensor | 208.65 | 71.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 26 | 41,600 | 546.7 | 3,471.9 | 2,018.9 | tensor | 208.66 | 72.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 28 | 44,800 | 546.7 | 3,530.5 | 2,100.0 | tensor | 208.66 | 73.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 546.7 | 3,557.4 | 2,138.5 | tensor | 208.67 | 74.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 546.7 | 3,582.9 | 2,175.8 | tensor | 208.67 | 74.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 41 | 65,600 | 546.7 | 3,794.3 | 2,054.9 | tensor | 208.69 | 79.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 546.7 | 3,836.4 | 2,131.0 | tensor | 208.70 | 80.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 55 | 88,000 | 546.7 | 3,956.3 | 2,194.8 | tensor | 208.71 | 82.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 546.7 | 3,982.1 | 2,099.2 | tensor | 208.71 | 83.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 546.7 | 3,990.2 | 2,117.2 | tensor | 208.71 | 83.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 546.7 | 1,635.5 | 3,797.5 | hybrid | 210.91 | 80.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 546.7 | 1,649.0 | 3,947.5 | hybrid | 210.91 | 83.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 546.7 | 1,643.3 | 3,911.0 | hybrid | 213.10 | 83.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 546.7 | 1,640.7 | 3,878.3 | hybrid | 215.30 | 83.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 546.7 | 1,641.8 | 3,922.0 | hybrid | 217.49 | 85.3% | link_latency |

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
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x45 | DeepSeek-V4-Flash-0731 | 45 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x35 | DeepSeek-V4-Flash-0731 | 35 | tensor | rom_package_ucie | rom_board_serdes | 172 | 41.00 us | 2,439.0 tok/s | 24,390.2 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 9 on rom_board_serdes (traversals 4.4) = 38.88 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x44 | DeepSeek-V4-Flash-0731 | 44 | hybrid | rom_package_ucie | rom_board_serdes | 96 | 3.16 us | 31,627.6 tok/s | 316,275.6 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x45 | DeepSeek-V4-Flash-0731 | 45 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x30 | DeepSeek-V4-Flash-0731 | 30 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x38 | DeepSeek-V4-Flash-0731 | 38 | hybrid | nvlink5 | infiniband_ndr | 90 | 217.23 us | 460.3 tok/s | 4,603.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x52 | DeepSeek-V4-Flash-0731 | 52 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x36 | DeepSeek-V4-Flash-0731 | 36 | tensor | rom_package_ucie | rom_board_serdes | 172 | 41.00 us | 2,439.0 tok/s | 24,390.2 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 9 on rom_board_serdes (traversals 4.4) = 38.88 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x52 | DeepSeek-V4-Flash-0731 | 52 | hybrid | rom_package_ucie | rom_board_serdes | 98 | 3.37 us | 29,665.7 tok/s | 296,656.6 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 12 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x51 | DeepSeek-V4-Flash-0731 | 51 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4-Flash-0731 | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x32 | DeepSeek-V4-Flash-0731 | 32 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4-Flash-0731 | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 172 | 184.65 us | 541.6 tok/s | 5,415.8 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 86 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 19.10 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x44 | DeepSeek-V4-Flash-0731 | 44 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
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
| DSV4-Flash/b200_sxm-x15-pipeline | DeepSeek-V4-Flash-0731 | 15 | pipeline | nvlink5 | infiniband_ndr | 14 | 17.91 us | 5,582.8 tok/s | 55,828.0 tok/s | 13 x point_to_point span 2 on nvlink5 (traversals 1.0) = 15.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x15-tensor | DeepSeek-V4-Flash-0731 | 15 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x15-hybrid | DeepSeek-V4-Flash-0731 | 15 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x15-nvl72-tensor | DeepSeek-V4-Flash-0731 | 15 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.59 us | 479.4 tok/s | 4,794.1 tok/s | 86 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 208.59 us |
| DSV4-Flash/b200_sxm-x15-expert | DeepSeek-V4-Flash-0731 | 15 | expert | nvlink5 | infiniband_ndr | 172 | 388.67 us | 257.3 tok/s | 2,572.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 180.22 us |
| DSV4-Flash/b200_sxm-x15-nvl72-expert | DeepSeek-V4-Flash-0731 | 15 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.10 us | 320.4 tok/s | 3,204.1 tok/s | 86 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 208.59 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.51 us |
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
| DSV4-Flash/b200_sxm-x23-pipeline | DeepSeek-V4-Flash-0731 | 23 | pipeline | nvlink5 | infiniband_ndr | 22 | 28.57 us | 3,500.2 tok/s | 35,002.1 tok/s | 20 x point_to_point span 2 on nvlink5 (traversals 1.0) = 24.18 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x23-tensor | DeepSeek-V4-Flash-0731 | 23 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x23-hybrid | DeepSeek-V4-Flash-0731 | 23 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x23-nvl72-tensor | DeepSeek-V4-Flash-0731 | 23 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.8 tok/s | 86 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x23-expert | DeepSeek-V4-Flash-0731 | 23 | expert | nvlink5 | infiniband_ndr | 172 | 385.68 us | 259.3 tok/s | 2,592.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.26 us |
| DSV4-Flash/b200_sxm-x23-nvl72-expert | DeepSeek-V4-Flash-0731 | 23 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.05 us | 320.5 tok/s | 3,204.6 tok/s | 86 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.40 us |
| DSV4-Flash/b200_sxm-x25-pipeline | DeepSeek-V4-Flash-0731 | 25 | pipeline | nvlink5 | infiniband_ndr | 24 | 31.97 us | 3,127.7 tok/s | 31,276.7 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x25-tensor | DeepSeek-V4-Flash-0731 | 25 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x25-hybrid | DeepSeek-V4-Flash-0731 | 25 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x25-nvl72-tensor | DeepSeek-V4-Flash-0731 | 25 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.6 tok/s | 86 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x25-expert | DeepSeek-V4-Flash-0731 | 25 | expert | nvlink5 | infiniband_ndr | 172 | 385.05 us | 259.7 tok/s | 2,597.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.96 us |
| DSV4-Flash/b200_sxm-x25-nvl72-expert | DeepSeek-V4-Flash-0731 | 25 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.04 us | 320.5 tok/s | 3,204.7 tok/s | 86 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.39 us |
| DSV4-Flash/b200_sxm-x26-pipeline | DeepSeek-V4-Flash-0731 | 26 | pipeline | nvlink5 | infiniband_ndr | 25 | 33.18 us | 3,013.7 tok/s | 30,137.0 tok/s | 22 x point_to_point span 2 on nvlink5 (traversals 1.0) = 26.60 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x26-tensor | DeepSeek-V4-Flash-0731 | 26 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x26-hybrid | DeepSeek-V4-Flash-0731 | 26 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x26-nvl72-tensor | DeepSeek-V4-Flash-0731 | 26 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.66 us | 479.3 tok/s | 4,792.5 tok/s | 86 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 208.66 us |
| DSV4-Flash/b200_sxm-x26-expert | DeepSeek-V4-Flash-0731 | 26 | expert | nvlink5 | infiniband_ndr | 172 | 384.92 us | 259.8 tok/s | 2,598.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.83 us |
| DSV4-Flash/b200_sxm-x26-nvl72-expert | DeepSeek-V4-Flash-0731 | 26 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.04 us | 320.5 tok/s | 3,204.7 tok/s | 86 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 208.66 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.38 us |
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
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x44 | 35,860 | 19,717.5 | 0.550 | 19,717.5 (35,860) | 6,622.3 (92,450) | 0.34x | compute |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x51 | 41,565 | 19,722.9 | 0.475 | 19,722.9 (41,565) | 6,622.3 (92,450) | 0.34x | compute |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x51 | 41,565 | 19,722.9 | 0.475 | 19,722.9 (41,565) | 6,622.3 (92,450) | 0.34x | compute |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x51 | 41,565 | 19,722.9 | 0.475 | 19,722.9 (41,565) | 6,622.3 (92,450) | 0.34x | compute |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x58-romfill | 47,270 | 18,141.4 | 0.384 | 18,141.4 (47,270) | 6,622.3 (92,450) | 0.37x | compute |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x116-romfill | 94,540 | 17,664.8 | 0.187 | 17,664.8 (94,540) | 6,622.3 (92,450) | 0.37x | compute |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 18,398.7 | 0.066 | 18,398.7 (277,100) | 6,622.3 (92,450) | 0.36x | compute |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 7,883.1 | 0.028 | 7,883.1 (277,100) | 6,639.4 (277,350) | 0.84x | compute |
| DeepSeek-V4-Flash-0731 | 1024 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4,602.0 | 0.008 | 2,266.9 (277,100) | 4,602.0 (554,700) | 2.03x | compute |
| DeepSeek-V4-Flash-0731 | 4096 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,225.1 | 0.002 | 553.5 (138,550) | 1,225.1 (554,700) | 2.21x | compute |

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
| DeepSeek-V4-Flash-0731 | 1 | sram | 384,602.4 | 28,756.4 | 28,756.4 | 13.37x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 384,602.4 | 28,756.4 | 28,756.4 | 13.37x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 384,602.4 | 28,756.4 | 40,674.6 | 13.37x | 1.41x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 384,602.4 | 28,756.4 | 64,025.0 | 13.37x | 2.23x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 384,602.4 | 28,756.4 | 97,631.5 | 13.37x | 3.40x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 393,410.0 | 28,756.4 | 140,306.5 | 13.68x | 4.88x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 601,532.9 | 28,784.4 | 189,317.4 | 20.90x | 6.58x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 991,339.1 | 28,956.7 | 390,776.4 | 34.24x | 13.50x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 2,268,824.4 | 26,103.0 | 550,222.5 | 86.92x | 21.08x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 4,930,189.7 | 26,110.2 | 755,388.3 | 188.82x | 28.93x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 4,527,314.4 | 207,090.5 | 207,090.5 | 21.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 4,527,314.4 | 207,090.5 | 207,090.5 | 21.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 4,527,314.4 | 207,090.5 | 207,090.5 | 21.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 4,527,314.4 | 207,090.5 | 207,090.5 | 21.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 4,527,314.4 | 207,090.5 | 207,090.5 | 21.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 4,527,314.4 | 207,090.5 | 207,090.5 | 21.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 4,527,314.4 | 207,090.5 | 268,109.9 | 21.86x | 1.29x | compute | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | rom | 4,527,314.4 | 210,838.7 | 608,503.8 | 21.47x | 2.89x | compute | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 4,712,455.5 | 213,161.7 | 891,452.1 | 22.11x | 4.18x | compute | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 5,018,024.5 | 213,750.5 | 1,050,992.9 | 23.48x | 4.92x | compute | weight_read | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,527,314.4 | 8.162 | compute | 11.77x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,527,314.4 | 8.162 | compute | 11.77x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,527,314.4 | 8.162 | compute | 11.77x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x16-perregion | 13,040 | 1.00 | 1.57 | 40,674.6 | 3.119 | weight_read | 0.11x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,527,314.4 | 8.162 | compute | 11.77x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x16-perregion | 13,040 | 1.00 | 2.13 | 64,025.0 | 4.910 | weight_read | 0.17x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,527,314.4 | 8.162 | compute | 11.77x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x16-perregion | 13,040 | 1.00 | 2.88 | 97,631.5 | 7.487 | weight_read | 0.25x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x87 | 70,905 | 1.00 | 1.00 | 393,410.0 | 5.548 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,527,314.4 | 8.162 | compute | 11.51x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.53x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x16-perregion | 13,040 | 1.00 | 4.03 | 140,306.5 | 10.760 | weight_read | 0.36x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.53x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x87 | 70,905 | 1.00 | 1.00 | 601,532.9 | 8.484 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,527,314.4 | 8.162 | compute | 7.53x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,784.4 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 1.00 | 207,090.5 | 2.240 | weight_read | 0.34x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x16-perregion | 13,040 | 1.00 | 5.83 | 189,317.4 | 14.518 | weight_read | 0.31x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 8.19 | 4.03 | 268,109.9 | 2.900 | link_latency | 0.45x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x116 | 94,540 | 1.00 | 1.00 | 991,339.1 | 10.486 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,527,314.4 | 8.162 | compute | 4.57x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,956.7 | 0.626 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 2.25 | 210,838.7 | 2.281 | weight_read | 0.21x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 13.84 | 390,776.4 | 8.454 | weight_read | 0.39x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 8.19 | 8.80 | 608,503.8 | 6.582 | kv_read | 0.61x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 2,268,824.4 | 6.135 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 4,712,455.5 | 8.496 | compute | 2.08x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x16-perstream | 13,040 | 1.00 | 64.00 | 26,103.0 | 2.002 | weight_read | 0.01x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 8.98 | 213,161.7 | 2.306 | weight_read | 0.09x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x2-perregion | 92,450 | 1.00 | 38.75 | 550,222.5 | 5.952 | weight_read | 0.24x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 8.19 | 22.71 | 891,452.1 | 9.643 | kv_read | 0.39x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 4,930,189.7 | 8.888 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 5,018,024.5 | 9.046 | compute | 1.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 35.93 | 26,110.2 | 0.282 | weight_read | 0.01x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 8.19 | 35.93 | 213,750.5 | 2.312 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 68.43 | 755,388.3 | 8.171 | weight_read | 0.15x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 8.19 | 4.28 | 1,050,992.9 | 11.368 | kv_read | 0.21x |

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
| DeepSeek-V4-Flash-0731 | 1 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 2 | 15 | 8.38 | 4.73 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 15 | 11.97 | 5.97 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 15 | 14.29 | 7.25 | 1.97x |
| DeepSeek-V4-Flash-0731 | 16 | 15 | 14.94 | 8.45 | 1.77x |
| DeepSeek-V4-Flash-0731 | 32 | 15 | 15.00 | 9.44 | 1.59x |
| DeepSeek-V4-Flash-0731 | 64 | 15 | 15.00 | 10.12 | 1.48x |
| DeepSeek-V4-Flash-0731 | 256 | 15 | 15.00 | 10.53 | 1.42x |
| DeepSeek-V4-Flash-0731 | 1024 | 15 | 15.00 | 10.54 | 1.42x |
| DeepSeek-V4-Flash-0731 | 4096 | 15 | 15.00 | 10.54 | 1.42x |
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
| DeepSeek-V4-Flash-0731 | 1 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 23 | 9.42 | 5.44 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 23 | 14.79 | 7.16 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 23 | 19.78 | 9.03 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 23 | 22.37 | 10.88 | 2.06x |
| DeepSeek-V4-Flash-0731 | 32 | 23 | 22.95 | 12.49 | 1.84x |
| DeepSeek-V4-Flash-0731 | 64 | 23 | 23.00 | 13.64 | 1.69x |
| DeepSeek-V4-Flash-0731 | 256 | 23 | 23.00 | 14.35 | 1.60x |
| DeepSeek-V4-Flash-0731 | 1024 | 23 | 23.00 | 14.35 | 1.60x |
| DeepSeek-V4-Flash-0731 | 4096 | 23 | 23.00 | 14.35 | 1.60x |
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
| DeepSeek-V4-Flash-0731 | 1 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 2 | 26 | 9.67 | 5.64 | 1.71x |
| DeepSeek-V4-Flash-0731 | 4 | 26 | 15.52 | 7.51 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 26 | 21.41 | 9.57 | 2.24x |
| DeepSeek-V4-Flash-0731 | 16 | 26 | 24.91 | 11.64 | 2.14x |
| DeepSeek-V4-Flash-0731 | 32 | 26 | 25.88 | 13.47 | 1.92x |
| DeepSeek-V4-Flash-0731 | 64 | 26 | 25.99 | 14.79 | 1.76x |
| DeepSeek-V4-Flash-0731 | 256 | 26 | 26.00 | 15.62 | 1.66x |
| DeepSeek-V4-Flash-0731 | 1024 | 26 | 26.00 | 15.62 | 1.66x |
| DeepSeek-V4-Flash-0731 | 4096 | 26 | 26.00 | 15.62 | 1.66x |
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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 4.9% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 25.2% |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,649.7 | 52,791.1 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,649.7 | 52,791.1 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,649.7 | 52,791.1 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,649.7 | 52,791.1 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,649.7 | 52,791.1 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,649.7 | 52,791.1 |
| DeepSeek-V4-Flash-0731 | 64 | 4.63% | 14.6 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 834.0 | 53,378.1 |
| DeepSeek-V4-Flash-0731 | 256 | 17.28% | 33.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 210.3 | 53,827.0 |
| DeepSeek-V4-Flash-0731 | 1024 | 53.18% | 86.0 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 52.7 | 53,940.4 |
| DeepSeek-V4-Flash-0731 | 4096 | 95.20% | 147.9 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 13.2 | 53,968.8 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 804 |
| gpu | thermal | 250 |
| gpu | weight_read | 476 |
| rom | compute | 904 |
| rom | infeasible | 2444 |
| rom | kv_read | 86 |
| rom | link_latency | 1127 |
| rom | thermal | 2 |
| rom | weight_read | 597 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2444 |

## Mechanical consistency audit

**FAIL** over 135,619 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x30', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x34', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x35', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x54', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x81', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x108', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x30', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x34', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x35', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x54', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x81', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x108', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x30', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x34', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x35', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x54', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x81', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x108', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x30', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x34', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x35', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x41', 'DeepSeek-V4-Flash-0731', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 71 |
| derived | 47 |
| assumed | 70 |

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
  1.8-2.3x low on the other.** Leakage, clock distribution, operand
  delivery and a measured clocked-idle floor are charged per mm2 per
  second whether or not a byte moves, and the HBM traffic energy is a
  measured SC 2025 figure rather than an HBM2-era model. The A100 lands
  at 1.15x of its published TDP under a saturating load; the Taalas HC1
  lands at 0.44x of its published card power. **The second one FAILS its
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

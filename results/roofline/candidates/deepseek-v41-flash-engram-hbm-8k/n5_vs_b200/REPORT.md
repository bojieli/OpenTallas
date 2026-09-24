# Area-constrained roofline: n5_vs_b200-deepseek-v41-flash-engram-hbm-8k

> CANDIDATE MODEL under n5_vs_b200: DeepSeek-V4.1-Flash-engram-hbm at 8,192 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 123x (ROM-N5-native-SRAMKV-wafer-pipeline-x3-perstream, 171 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 90 devices. On the GPU side the correction reaches 31x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 55 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-hbm takes 62 x 815 mm2 (50,530 mm2, array, KV in HBM) at 13,577 tok/s per user and 269 tok/s per 1,000 mm2, holding 607,824 sessions, against 32 copies of one unified HBM die at the same silicon: 3.6x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-hbm on 74,980 mm2 of ROM silicon at 18,538 tok/s per user against 75,200 mm2 of b200_sxm-x47-nvl72-tensor at 4,039 tok/s: **4.6x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 911,749 resident sessions against the GPU cluster's 710,780. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 9.07x to it.** At 113,285 mm2 on DeepSeek-V4.1-Flash-engram-hbm the pipeline-only GPU delivers 472.85 tok/s and the same silicon running tensor delivers 4,290 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `link_latency`) to 4.19x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-hbm engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 2,137 to 125,779 tok/s, and its rate with every slot occupied from 121,822 to 125,779. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 57 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 567 us over NVLink, capping per-user decode at 1,763 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 171.9 us and cap it at 5,818 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.7x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 8 to the array and 2 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 1 of 5897 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 230.0x of aggregate throughput (DeepSeek-V4.1-Flash-engram-hbm). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 43.84x, on DeepSeek-V4.1-Flash-engram-hbm at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 404 of 5,897 feasible points (6.9%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x4-pipeline` at batch 4096 on 6,400 mm2, throttled 1.12x from 21 to 19 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 89% weight read against 89.3% weight read. The ROM sweep is not what melts it.


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

### DeepSeek-V4.1-Flash-engram-hbm at 8,192 tokens

**Recommended: `ROM-N5-native-HBMKV-array-hw-tensor-x62`** -- 62 x 815 mm2 reticle dies, 50,530 mm2 total, `tensor`-parallel, KV in HBM, spare silicon to `sram`.

- **13,577.1 tok/s per user** (0.07 ms/token), binding on `link_latency`
- **268.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 13,577 tok/s aggregate with every slot full, over 607,824 resident sessions (fill limited by `batch`)
- 4,173 W at 0.083 W/mm2, 307.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 32 copies of one unified HBM die -- `b200_sxm-x32-nvl72-tensor`, 51,200 mm2, area ratio 0.9869 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 50,530 | 51,200 | 0.9869 |
| user tok/s | 13,577.1 | 3,736.6 | 3.63x |
| aggregate tok/s | 13,577 | 3,737 | 0.90x |
| resident sessions | 607,824 | 467,640 | -- |
| J/token | 0.3073 | 4.3749 | 14.2x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 607,824 sessions against one that holds 467,640 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x71-nvl72-tensor` at 113,600 mm2 and 4,289.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 73,350 | 17,831.9 | 243.1 | 891,487 | 4.43x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | 18,538.3 | 247.2 | 911,749 | 4.59x |
| smallest feasible machine | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,814.0 | 125.8 | 66,837 | 1.59x |
| **after -- this report's rule** | `ROM-N5-native-HBMKV-array-hw-tensor-x62` | 50,530 | 13,577.1 | 268.7 | 607,824 | 3.63x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-HBMKV-array-hw-tensor-x62` | 50,530 | 13,577.1 | 268.7 | -- | 268.7 | ACCEPT |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | 18,538.3 | 247.2 | 202.9 | 268.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-HBMKV-array-hw-tensor-x62` **<-- recommended** | 50,530 | 62 | 13,577.1 | 13,577 | 268.7 | 607,824 | `link_latency` | 4,173 | 307.3 | `b200_sxm-x32-nvl72-tensor` | 3.63x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | 92 | 18,538.3 | 426,381 | 247.2 | 911,749 | `compute` | 11,002 | 440.8 | `b200_sxm-x47-nvl72-tensor` | 4.59x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 330 | densest | `ROM-N5-native-HBMKV-array-hw-tensor-x62` | 50,530 | 13,577.1 | 268.7 | 607,824 |
| array | 330 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | 18,538.3 | 247.2 | 911,749 |
| array | 330 | smallest | `ROM-N5-native-HBMKV-array-hw-tensor-x57` | 46,455 | 12,042.5 | 259.2 | 557,170 |
| wafer | 73 | densest | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,814.0 | 125.8 | 66,837 |
| wafer | 73 | fastest | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | 33.0 | 328,213 |
| wafer | 73 | smallest | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,814.0 | 125.8 | 66,837 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | 18,538.3 | 426,381 | 911,749 | 11,002 | 440.8 | `compute` | `b200_sxm-x47-nvl72-tensor` | 4,039.3 | 710,780 | 5,451.3 | 0.997 | 4.59x | 12.4x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | 1,386,470 | 328,213 | 26,020 | 2,692.0 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 4,137.4 | 1,829,225 | 11,199.0 | 0.996 | 1.48x | 4.2x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 176,040 | 17,868.8 | 964,914 | 2,167,972 | 25,540 | 1,061.6 | `compute` | `b200_sxm-x110-nvl72-hybrid` | 4,105.2 | 1,731,969 | 10,763.8 | 1.000 | 4.35x | 10.1x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | -- | 328,213 | -- | 2,692.0 | -- | -- | -- | -- | -- | 0.952 | 0.34x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | 18,538.3 | 426,381 | 911,749 | 11,002 | 223.9 | `compute` | `b200_sxm-x47-nvl72-tensor` | 3,775.5 | 710,780 | 3,103.4 | 0.997 | 4.91x | 13.9x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | 1,386,470 | 328,213 | 26,020 | 1,349.4 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 4,137.4 | 1,829,225 | 6,286.3 | 0.996 | 1.48x | 4.7x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 176,040 | 17,868.8 | 964,914 | 2,167,972 | 25,540 | 534.3 | `compute` | `b200_sxm-x110-nvl72-hybrid` | 4,105.2 | 1,731,969 | 6,068.7 | 1.000 | 4.35x | 11.4x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | -- | 328,213 | -- | 1,349.4 | -- | -- | -- | -- | -- | 0.952 | 0.34x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | 18,538.3 | 426,381 | 911,749 | 11,002 | 115.4 | `compute` | `b200_sxm-x47-nvl72-tensor` | 3,346.8 | 710,780 | 1,921.1 | 0.997 | 5.54x | 16.6x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | 1,386,470 | 328,213 | 26,020 | 678.2 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,899.4 | 1,829,225 | 3,528.3 | 0.996 | 1.57x | 5.2x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 176,040 | 17,868.8 | 964,914 | 2,167,972 | 25,540 | 270.6 | `compute` | `b200_sxm-x110-nvl72-hybrid` | 3,861.2 | 1,731,969 | 3,418.0 | 1.000 | 4.63x | 12.6x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | -- | 328,213 | -- | 678.2 | -- | -- | -- | -- | -- | 0.952 | 0.34x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | 18,538.3 | 426,381 | 911,749 | 11,002 | 61.2 | `compute` | `b200_sxm-x47-nvl72-tensor` | 2,747.2 | 710,780 | 1,314.1 | 0.997 | 6.75x | 21.5x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | 1,386,470 | 328,213 | 26,020 | 342.6 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,503.9 | 1,829,225 | 2,141.0 | 0.996 | 1.74x | 6.3x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 176,040 | 17,868.8 | 964,914 | 2,167,972 | 25,540 | 138.8 | `compute` | `b200_sxm-x110-nvl72-hybrid` | 3,457.8 | 1,731,969 | 2,084.4 | 1.000 | 5.17x | 15.0x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | -- | 328,213 | -- | 342.6 | -- | -- | -- | -- | -- | 0.952 | 0.34x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | 18,538.3 | 426,381 | 911,749 | 11,002 | 34.1 | `compute` | `b200_sxm-x47-nvl72-tensor` | 2,063.1 | 710,780 | 981.1 | 0.997 | 8.99x | 28.8x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | 1,386,470 | 328,213 | 26,020 | 174.8 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 2,931.0 | 1,829,225 | 1,431.5 | 0.996 | 2.08x | 8.2x |
| 16 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 176,040 | 17,868.8 | 964,914 | 2,167,972 | 25,540 | 72.9 | `compute` | `b200_sxm-x110-nvl72-hybrid` | 2,878.6 | 1,731,969 | 1,401.7 | 1.000 | 6.21x | 19.2x |
| 16 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | -- | 328,213 | -- | 174.8 | -- | -- | -- | -- | -- | 0.952 | 0.34x wafer/array | -- |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 176,040 | 17,868.8 | 964,914 | 2,167,972 | 25,540 | 39.9 | `compute` | `b200_sxm-x110-nvl72-hybrid` | 2,195.7 | 1,731,969 | 1,030.8 | 1.000 | 8.14x | 25.8x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | 1,386,470 | 328,213 | 26,020 | 90.8 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 2,248.0 | 1,829,225 | 1,047.2 | 0.996 | 2.72x | 11.5x |
| 32 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 176,040 | 17,868.8 | 964,914 | 2,167,972 | 25,540 | 39.9 | `compute` | `b200_sxm-x110-nvl72-hybrid` | 2,195.7 | 1,731,969 | 1,030.8 | 1.000 | 8.14x | 25.8x |
| 32 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | -- | 328,213 | -- | 90.8 | -- | -- | -- | -- | -- | 0.952 | 0.34x wafer/array | -- |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 17,868.8 | 1,518,847 | 3,424,196 | 40,202 | 32.9 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 1,936.5 | 2,753,157 | 940.8 | 1.001 | 9.23x | 28.6x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | 1,386,470 | 328,213 | 26,020 | 48.9 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 1,600.6 | 1,829,225 | 803.9 | 0.996 | 3.82x | 16.4x |
| 64 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 16,360.5 | 1,047,071 | 2,279,412 | 26,766 | 25.6 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 1,600.6 | 1,829,225 | 803.9 | 0.997 | 10.22x | 31.4x |
| 64 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 6,107.8 | -- | 328,213 | -- | 48.9 | -- | -- | -- | -- | -- | 1.001 | 0.37x wafer/array | -- |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 7,285.3 | 1,865,039 | 3,424,196 | 39,272 | 21.1 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 936.4 | 2,753,157 | 529.9 | 1.001 | 7.78x | 22.9x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 369,800 | 6,107.8 | 2,772,940 | 676,713 | 52,039 | 27.9 | `compute` | `b200_sxm-x231-nvl72-hybrid` | 1,069.6 | 3,693,298 | 614.4 | 1.001 | 5.71x | 19.9x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 2,039.7 | 2,088,704 | 3,424,196 | 40,424 | 19.4 | `compute` | `b200_sxm-x173-expert` | 485.3 | 2,736,101 | 156.1 | 1.001 | 4.20x | 8.1x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 4,189.9 | 4,290,433 | 1,025,214 | 75,147 | 17.5 | `compute` | `b200_sxm-x347-expert` | 674.0 | 5,537,764 | 210.3 | 0.999 | 6.22x | 12.0x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 609.5 | 2,496,649 | 2,279,412 | 35,321 | 14.1 | `compute` | `b200_sxm-x116-expert` | 172.9 | 1,818,138 | 68.6 | 0.997 | 3.52x | 4.8x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,629.1 | 6,672,651 | 1,025,214 | 98,889 | 14.8 | `weight_read` | `b200_sxm-x347-expert` | 393.2 | 5,537,764 | 86.7 | 0.999 | 4.14x | 5.9x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-HBMKV-array-hw-tensor-x62` | 50,530 | array | HBM | 607,824 |
| 2-16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x92` | 74,980 | array | HBM | 911,749 |
| 32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x93` | 75,795 | array | HBM | 921,880 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 1,124,496 |
| 256 | `ROM-N5-native-HBMKV-wafer-pipeline-x2` | 92,450 | wafer | HBM | 153,962 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 138,550 | array | HBM | 1,701,954 |
| 4096 | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 277,350 | wafer | HBM | 502,463 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | rom | 57, 58, 62, 68, 77, 81, 90, 91, 108, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | sram | 57, 58, 62, 68, 77, 81, 92, 93, 108, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | rom | 133, 139, 157, 160, 170, 192, 227, 256, 340, 362, 364, 369, 384 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | sram | 132, 139, 157, 160, 164, 165, 170, 192, 227, 256, 340, 384 |

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

- **404 of 5,897 feasible points (6.9%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 404.
- By area class: large array (5,000-40,000 mm2) 54, wafer (>=40,000 mm2) 350.
- By KV store: hbm 404.
- By batch: B=1 40, B=2 40, B=4 40, B=8 40, B=16 40, B=32 40, B=64 42, B=256 42, B=1024 40, B=4096 40.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 47% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 290 | 54 | 75.1% | 100.0% | 0.625 | 47% |
| gpu | wafer (>=40,000 mm2) | 2,310 | 350 | 47.8% | 100.0% | 0.625 | 73% |
| rom | large array (5,000-40,000 mm2) | 600 | 0 | 19.4% | 38.0% | 0.190 | 92% |
| rom | wafer (>=40,000 mm2) | 2,697 | 0 | 22.1% | 47.0% | 0.235 | 93% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x4-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 6,400 | hbm | 1.119x | 4,000.0 / 4,000.0 W | 35% | 18.6 | 20.8 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 22,400 | hbm | 1.067x | 14,000.0 / 14,000.0 W | 35% | 20.3 | 21.7 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x4-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 1024 | 6,400 | hbm | 1.067x | 4,000.0 / 4,000.0 W | 35% | 20.5 | 21.9 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x16-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 25,600 | hbm | 1.064x | 16,000.0 / 16,000.0 W | 35% | 20.5 | 21.9 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x18-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 28,800 | hbm | 1.062x | 18,000.0 / 18,000.0 W | 35% | 20.8 | 22.1 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 32,000 | hbm | 1.060x | 20,000.0 / 20,000.0 W | 35% | 21.1 | 22.4 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 46,400 | hbm | 1.056x | 29,000.0 / 29,000.0 W | 35% | 22.8 | 24.1 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 48,000 | hbm | 1.055x | 30,000.0 / 30,000.0 W | 35% | 23.0 | 24.3 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x4-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 256 | 6,400 | hbm | 1.055x | 4,000.0 / 4,000.0 W | 35% | 31.8 | 33.6 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 51,200 | hbm | 1.055x | 32,000.0 / 32,000.0 W | 35% | 23.5 | 24.8 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 1024 | 22,400 | hbm | 1.055x | 14,000.0 / 14,000.0 W | 35% | 29.6 | 31.3 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x16-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 1024 | 25,600 | hbm | 1.054x | 16,000.0 / 16,000.0 W | 35% | 31.8 | 33.6 |

The worst point's dynamic energy is weight read 89.3%, arithmetic 6.4%, kv read 4.1%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 73,350 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 0.443197 | 10,625.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-tensor` | 5.379556 | 21,648.3 | link_latency | 12.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 73,350 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 0.225068 | 10,625.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-tensor` | 3.067000 | 23,050.1 | link_latency | 13.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 73,350 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 0.116003 | 10,625.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-tensor` | 1.902479 | 25,311.1 | link_latency | 16.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 73,350 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 0.061471 | 10,625.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-tensor` | 1.304326 | 28,427.9 | link_latency | 21.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 73,350 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 0.034205 | 10,625.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-tensor` | 0.975698 | 31,866.6 | link_latency | 28.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 132,030 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 0.031873 | 19,172.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-nvl72-hybrid` | 0.956706 | 58,635.4 | weight_read | 30.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.032877 | 40,202.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid` | 0.940750 | 116,594.2 | link_latency | 28.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.021057 | 39,271.8 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid` | 0.529920 | 127,028.4 | weight_read | 22.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.017515 | 75,147.2 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-expert` | 0.210283 | 145,141.6 | link_latency | 12.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12` | 0.014820 | 98,888.5 | weight_read | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-expert` | 0.086711 | 139,668.3 | link_latency | 5.85x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 552 B | 307.5 GB | 4.46 | 0.012 GB | 0.010 GB | 1,091.7 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 46,225 | 43,718.6 | wafer-pipeline | 5,814.0 | wafer-tensor | 7.52x | 8,365.7 | pipeline | 3,648.0 | tensor | 2.29x | 5.23x | 1.59x | 0.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 92,450 | 61,584.9 | wafer-pipeline | 6,083.4 | wafer-pipeline | 10.12x | 10,209.3 | pipeline | 4,176.2 | tensor | 2.44x | 6.03x | 1.46x | 0.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 3 | 138,675 | 63,288.1 | wafer-pipeline | 6,083.4 | wafer-pipeline | 10.40x | 11,607.0 | pipeline | 3,948.3 | hybrid | 2.94x | 5.45x | 1.54x | 0.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 184,900 | 64,175.6 | wafer-pipeline | 6,107.8 | wafer-pipeline | 10.51x | 12,459.9 | pipeline | 4,137.4 | hybrid | 3.01x | 5.15x | 1.48x | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 6 | 277,350 | 65,088.3 | wafer-pipeline | 6,099.7 | wafer-pipeline | 10.67x | 13,435.7 | pipeline | 4,096.1 | hybrid | 3.28x | 4.84x | 1.49x | 0.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 369,800 | 65,554.4 | wafer-pipeline | 6,107.8 | wafer-pipeline | 10.73x | 13,995.8 | pipeline | 4,059.8 | hybrid | 3.45x | 4.68x | 1.50x | 0.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 12 | 554,700 | 66,027.3 | wafer-pipeline | 6,107.8 | wafer-pipeline | 10.81x | 14,602.8 | pipeline | 4,120.3 | hybrid | 3.54x | 4.52x | 1.48x | 0.33x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.24x to 0.33x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x92 | 74,980 | 18,538.3 | 426,381.1 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-nvl72-tensor | 75,200 | 1.00x | tensor | 194.67 | 4,039.3 | 4,039.3 | link_latency | 4.59x | 19.19x | 39.21x | 4.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 5,814.0 | 5,814.0 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 194.64 | 3,648.0 | 3,648.0 | link_latency | 1.59x | 0.42x | 12.30x | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x92 | 74,980 | 18,538.3 | 426,381.1 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-nvl72-tensor | 75,200 | 1.00x | tensor | 197.35 | 3,775.5 | 7,550.9 | link_latency | 4.91x | 19.19x | 39.21x | 4.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 5,557.2 | 11,114.5 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 197.27 | 3,328.1 | 6,656.3 | link_latency | 1.67x | 0.81x | 11.75x | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x92 | 74,980 | 18,538.3 | 426,381.1 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-nvl72-tensor | 75,200 | 1.00x | tensor | 202.69 | 3,346.8 | 13,387.3 | link_latency | 5.54x | 19.19x | 39.21x | 5.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 5,106.2 | 20,424.9 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 202.55 | 2,840.5 | 11,361.9 | link_latency | 1.80x | 1.49x | 10.80x | 1.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x92 | 74,980 | 18,538.3 | 426,381.1 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-nvl72-tensor | 75,200 | 1.00x | tensor | 213.38 | 2,747.2 | 21,977.4 | link_latency | 6.75x | 19.19x | 39.21x | 6.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,393.2 | 35,145.2 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 213.09 | 2,217.4 | 17,739.3 | link_latency | 1.98x | 1.98x | 9.29x | 1.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x92 | 74,980 | 18,538.3 | 426,381.1 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-nvl72-tensor | 75,200 | 1.00x | tensor | 234.76 | 2,063.1 | 33,010.3 | link_latency | 8.99x | 12.92x | 39.21x | 8.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 3,434.0 | 54,944.6 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 234.18 | 1,579.7 | 25,275.9 | weight_read | 2.17x | 2.17x | 7.26x | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill | 176,040 | 17,868.8 | 964,914.3 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-nvl72-hybrid | 176,000 | 1.00x | hybrid | 240.39 | 2,195.7 | 70,262.6 | link_latency | 8.14x | 13.73x | 37.79x | 8.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 2,390.3 | 76,490.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 276.37 | 1,061.1 | 33,956.4 | weight_read | 2.25x | 2.25x | 5.24x | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 17,868.8 | 1,518,846.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 262.24 | 1,936.5 | 123,937.4 | link_latency | 9.23x | 12.25x | 37.79x | 9.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1,910.1 | 122,248.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 360.74 | 716.0 | 45,827.1 | weight_read | 2.67x | 2.67x | 5.71x | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 7,285.3 | 1,865,039.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 460.79 | 936.4 | 239,712.4 | weight_read | 7.78x | 7.78x | 17.95x | 7.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 488.0 | 124,919.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 866.95 | 408.1 | 104,484.9 | weight_read | 1.20x | 1.20x | 3.66x | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4,189.9 | 4,290,432.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-expert | 555,200 | 1.00x | expert | 701.40 | 674.0 | 690,219.4 | link_latency | 6.22x | 6.22x | 14.74x | 6.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 122.7 | 125,606.1 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 2,891.78 | 219.4 | 224,698.9 | link_latency | 0.56x | 0.56x | 2.64x | 0.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,629.1 | 6,672,650.5 | weight_read | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-expert | 555,200 | 1.00x | expert | 1,742.38 | 393.2 | 1,610,724.8 | link_latency | 4.14x | 4.14x | 15.27x | 4.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 30.7 | 125,778.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 3,273.91 | 101.0 | 413,508.8 | weight_read | 0.30x | 0.30x | 1.35x | 0.30x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 6,400 | 194.05 | 194.05 | 1,413.4 | 1,413.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 14 | 22,400 | 194.54 | 194.54 | 2,870.1 | 2,870.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 25,600 | 194.56 | 194.56 | 3,026.0 | 3,026.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 18 | 28,800 | 194.58 | 194.58 | 3,159.5 | 3,159.5 |
| DeepSeek-V4.1-Flash-engram-hbm | 20 | 32,000 | 194.59 | 194.59 | 3,275.2 | 3,275.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 29 | 46,400 | 194.64 | 194.64 | 3,648.0 | 3,648.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 30 | 48,000 | 194.64 | 194.64 | 3,679.0 | 3,679.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 51,200 | 194.65 | 194.65 | 3,736.6 | 3,736.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 35 | 56,000 | 194.65 | 194.65 | 3,813.3 | 3,813.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 39 | 62,400 | 194.66 | 194.66 | 3,901.0 | 3,901.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 41 | 65,600 | 194.66 | 194.66 | 3,939.7 | 3,939.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 46 | 73,600 | 194.67 | 194.67 | 4,024.2 | 4,024.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 47 | 75,200 | 194.67 | 194.67 | 4,039.3 | 4,039.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 55 | 88,000 | 194.68 | 194.68 | 4,143.4 | 4,143.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 58 | 92,800 | 194.68 | 194.68 | 4,176.2 | 4,176.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 102,400 | 194.69 | 194.69 | 4,233.6 | 4,233.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 67 | 107,200 | 194.69 | 194.69 | 4,259.0 | 4,259.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 68 | 108,800 | 194.69 | 194.69 | 4,267.0 | 4,267.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 71 | 113,600 | 194.69 | 194.69 | 4,289.9 | 4,289.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 80 | 128,000 | 196.93 | 196.93 | 3,886.2 | 3,886.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 82 | 131,200 | 196.93 | 196.93 | 3,904.8 | 3,904.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 83 | 132,800 | 196.93 | 196.93 | 3,913.9 | 3,913.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 84 | 134,400 | 196.93 | 196.93 | 3,922.7 | 3,922.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 87 | 139,200 | 196.93 | 196.93 | 3,948.3 | 3,948.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 98 | 156,800 | 196.93 | 196.93 | 4,031.0 | 4,031.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 110 | 176,000 | 196.93 | 196.93 | 4,105.2 | 4,105.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 116 | 185,600 | 196.93 | 196.93 | 4,137.4 | 4,137.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 126 | 201,600 | 196.93 | 196.93 | 4,185.1 | 4,185.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 130 | 208,000 | 196.93 | 196.93 | 4,202.4 | 4,202.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 173 | 276,800 | 199.16 | 199.16 | 4,096.1 | 4,096.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 184 | 294,400 | 199.16 | 199.16 | 4,131.5 | 4,131.5 |
| DeepSeek-V4.1-Flash-engram-hbm | 185 | 296,000 | 199.16 | 199.16 | 4,134.5 | 4,134.5 |
| DeepSeek-V4.1-Flash-engram-hbm | 188 | 300,800 | 199.16 | 199.16 | 4,143.4 | 4,143.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 192 | 307,200 | 199.16 | 199.16 | 4,154.9 | 4,154.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 193 | 308,800 | 199.16 | 199.16 | 4,157.8 | 4,157.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 194 | 310,400 | 199.16 | 199.16 | 4,160.5 | 4,160.5 |
| DeepSeek-V4.1-Flash-engram-hbm | 196 | 313,600 | 199.16 | 199.16 | 4,166.1 | 4,166.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 231 | 369,600 | 201.40 | 201.40 | 4,059.8 | 4,059.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 318 | 508,800 | 203.63 | 203.63 | 4,075.9 | 4,075.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 347 | 555,200 | 203.63 | 203.63 | 4,120.3 | 4,120.3 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 6,400 | 472.9 | 1,413.4 | — | tensor | 194.05 | 27.4% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 14 | 22,400 | 472.9 | 2,870.1 | 2,022.9 | tensor | 194.54 | 55.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 25,600 | 472.9 | 3,026.0 | 2,181.6 | tensor | 194.56 | 58.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 18 | 28,800 | 472.9 | 3,159.5 | 1,836.5 | tensor | 194.58 | 61.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 20 | 32,000 | 472.9 | 3,275.2 | 1,957.1 | tensor | 194.59 | 63.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 29 | 46,400 | 472.9 | 3,648.0 | 2,045.4 | tensor | 194.64 | 71.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 30 | 48,000 | 472.9 | 3,679.0 | 2,084.9 | tensor | 194.64 | 71.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 51,200 | 472.9 | 3,736.6 | 2,160.5 | tensor | 194.65 | 72.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 35 | 56,000 | 472.9 | 3,813.3 | 1,995.8 | tensor | 194.65 | 74.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 39 | 62,400 | 472.9 | 3,901.0 | 2,120.7 | tensor | 194.66 | 75.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 41 | 65,600 | 472.9 | 3,939.7 | 1,959.6 | tensor | 194.66 | 76.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 46 | 73,600 | 472.9 | 4,024.2 | 2,090.9 | tensor | 194.67 | 78.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 47 | 75,200 | 472.9 | 4,039.3 | 2,115.6 | tensor | 194.67 | 78.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 55 | 88,000 | 472.9 | 4,143.4 | 2,109.1 | tensor | 194.68 | 80.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 58 | 92,800 | 472.9 | 4,176.2 | 2,008.7 | tensor | 194.68 | 81.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 102,400 | 472.9 | 4,233.6 | 2,119.6 | tensor | 194.69 | 82.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 67 | 107,200 | 472.9 | 4,259.0 | 2,029.2 | tensor | 194.69 | 82.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 68 | 108,800 | 472.9 | 4,267.0 | 2,045.7 | tensor | 194.69 | 83.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 71 | 113,600 | 472.9 | 4,289.9 | 2,093.9 | tensor | 194.69 | 83.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 80 | 128,000 | 472.9 | 1,726.2 | 3,886.2 | hybrid | 196.93 | 76.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 82 | 131,200 | 472.9 | 1,728.1 | 3,904.8 | hybrid | 196.93 | 76.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 83 | 132,800 | 472.9 | 1,729.0 | 3,913.9 | hybrid | 196.93 | 77.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 84 | 134,400 | 472.9 | 1,729.8 | 3,922.7 | hybrid | 196.93 | 77.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 87 | 139,200 | 472.9 | 1,732.3 | 3,948.3 | hybrid | 196.93 | 77.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 98 | 156,800 | 472.9 | 1,740.1 | 4,031.0 | hybrid | 196.93 | 79.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 110 | 176,000 | 472.9 | 1,746.9 | 4,105.2 | hybrid | 196.93 | 80.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 116 | 185,600 | 472.9 | 1,749.8 | 4,137.4 | hybrid | 196.93 | 81.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 126 | 201,600 | 472.9 | 1,754.1 | 4,185.1 | hybrid | 196.93 | 82.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 130 | 208,000 | 472.9 | 1,755.6 | 4,202.4 | hybrid | 196.93 | 82.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 173 | 276,800 | 472.9 | 1,742.3 | 4,096.1 | hybrid | 199.16 | 81.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 184 | 294,400 | 472.9 | 1,744.4 | 4,131.5 | hybrid | 199.16 | 82.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 185 | 296,000 | 472.9 | 1,744.6 | 4,134.5 | hybrid | 199.16 | 82.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 188 | 300,800 | 472.9 | 1,745.1 | 4,143.4 | hybrid | 199.16 | 82.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 192 | 307,200 | 472.9 | 1,745.8 | 4,154.9 | hybrid | 199.16 | 82.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 193 | 308,800 | 472.9 | 1,746.0 | 4,157.8 | hybrid | 199.16 | 82.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 194 | 310,400 | 472.9 | 1,746.1 | 4,160.5 | hybrid | 199.16 | 82.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 196 | 313,600 | 472.9 | 1,746.5 | 4,166.1 | hybrid | 199.16 | 83.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 231 | 369,600 | 472.9 | 1,738.8 | 4,059.8 | hybrid | 201.40 | 81.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 318 | 508,800 | 472.9 | 1,738.5 | 4,075.9 | hybrid | 203.63 | 83.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 347 | 555,200 | 472.9 | 1,740.1 | 4,120.3 | hybrid | 203.63 | 83.9% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x165 | DeepSeek-V4.1-Flash-engram-hbm | 165 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x139 | DeepSeek-V4.1-Flash-engram-hbm | 139 | tensor | rom_package_ucie | rom_board_serdes | 160 | 91.39 us | 1,094.2 tok/s | 10,942.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 35 on rom_board_serdes (traversals 11.0) = 89.33 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x164 | DeepSeek-V4.1-Flash-engram-hbm | 164 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x165 | DeepSeek-V4.1-Flash-engram-hbm | 165 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-tensor-x132 | DeepSeek-V4.1-Flash-engram-hbm | 132 | tensor | nvlink5 | infiniband_ndr | 160 | 565.45 us | 176.9 tok/s | 1,768.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 371.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | tensor | on_wafer_n5 | rom_wafer_serdes | 160 | 171.87 us | 581.8 tok/s | 5,818.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 80 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 17.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hybrid-x157 | DeepSeek-V4.1-Flash-engram-hbm | 157 | hybrid | nvlink5 | infiniband_ndr | 99 | 236.85 us | 422.2 tok/s | 4,222.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 42.46 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | hybrid | on_wafer_n5 | rom_wafer_serdes | 82 | 154.20 us | 648.5 tok/s | 6,484.9 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x93 | DeepSeek-V4.1-Flash-engram-hbm | 93 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x62 | DeepSeek-V4.1-Flash-engram-hbm | 62 | tensor | rom_package_ucie | rom_board_serdes | 160 | 56.14 us | 1,781.2 tok/s | 17,812.4 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 16 on rom_board_serdes (traversals 6.6) = 54.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x92 | DeepSeek-V4.1-Flash-engram-hbm | 92 | hybrid | rom_package_ucie | rom_board_serdes | 102 | 4.39 us | 22,800.0 tok/s | 228,000.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 22 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.33 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-pipeline-x93 | DeepSeek-V4.1-Flash-engram-hbm | 93 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-tensor-x58 | DeepSeek-V4.1-Flash-engram-hbm | 58 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4.1-Flash-engram-hbm | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 80 | 154.00 us | 649.4 tok/s | 6,493.5 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hybrid-x77 | DeepSeek-V4.1-Flash-engram-hbm | 77 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x4-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,516.9 tok/s | 275,168.8 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x4-tensor | DeepSeek-V4.1-Flash-engram-hbm | 4 | tensor | nvlink5 | infiniband_ndr | 80 | 194.05 us | 515.3 tok/s | 5,153.4 tok/s | 80 x all_reduce span 4 on nvlink5 (traversals 2.0) = 194.05 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x4-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 4 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.05 us | 515.3 tok/s | 5,153.4 tok/s | 80 x all_reduce span 4 on nvlink5_nvl72 (traversals 2.0) = 194.05 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x4-expert | DeepSeek-V4.1-Flash-engram-hbm | 4 | expert | nvlink5 | infiniband_ndr | 160 | 291.41 us | 343.2 tok/s | 3,431.6 tok/s | 80 x all_reduce span 4 on nvlink5 (traversals 2.0) = 194.05 us; 80 x point_to_point span 2 on nvlink5 (traversals 1.0) = 97.37 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x4-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 4 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 291.41 us | 343.2 tok/s | 3,431.6 tok/s | 80 x all_reduce span 4 on nvlink5_nvl72 (traversals 2.0) = 194.05 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 97.37 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 16.77 us | 5,962.6 tok/s | 59,625.6 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 14.54 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-tensor | DeepSeek-V4.1-Flash-engram-hbm | 14 | tensor | nvlink5 | infiniband_ndr | 160 | 543.77 us | 183.9 tok/s | 1,839.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 14 | hybrid | nvlink5 | infiniband_ndr | 81 | 196.62 us | 508.6 tok/s | 5,085.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 14 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.54 us | 514.0 tok/s | 5,140.4 tok/s | 80 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 194.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-expert | DeepSeek-V4.1-Flash-engram-hbm | 14 | expert | nvlink5 | infiniband_ndr | 160 | 363.81 us | 274.9 tok/s | 2,748.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 169.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 14 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.93 us | 343.7 tok/s | 3,437.3 tok/s | 80 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 194.54 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.39 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x16-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.19 us | 5,209.9 tok/s | 52,099.4 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.96 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x16-tensor | DeepSeek-V4.1-Flash-engram-hbm | 16 | tensor | nvlink5 | infiniband_ndr | 160 | 543.77 us | 183.9 tok/s | 1,839.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x16-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 16 | hybrid | nvlink5 | infiniband_ndr | 81 | 196.62 us | 508.6 tok/s | 5,085.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x16-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 16 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.56 us | 514.0 tok/s | 5,139.8 tok/s | 80 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 194.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x16-expert | DeepSeek-V4.1-Flash-engram-hbm | 16 | expert | nvlink5 | infiniband_ndr | 160 | 361.74 us | 276.4 tok/s | 2,764.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 168.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x16-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 16 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.90 us | 343.8 tok/s | 3,437.6 tok/s | 80 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 194.56 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.34 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x18-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 18 | pipeline | nvlink5 | infiniband_ndr | 17 | 22.64 us | 4,416.9 tok/s | 44,169.1 tok/s | 15 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.17 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x18-tensor | DeepSeek-V4.1-Flash-engram-hbm | 18 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x18-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 18 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x18-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 18 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.58 us | 513.9 tok/s | 5,139.3 tok/s | 80 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 194.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x18-expert | DeepSeek-V4.1-Flash-engram-hbm | 18 | expert | nvlink5 | infiniband_ndr | 160 | 361.06 us | 277.0 tok/s | 2,769.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 167.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x18-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 18 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.88 us | 343.8 tok/s | 3,437.8 tok/s | 80 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 194.58 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.30 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 20 | pipeline | nvlink5 | infiniband_ndr | 19 | 25.06 us | 3,989.9 tok/s | 39,899.4 tok/s | 17 x point_to_point span 2 on nvlink5 (traversals 1.0) = 20.59 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-tensor | DeepSeek-V4.1-Flash-engram-hbm | 20 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 20 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 20 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.59 us | 513.9 tok/s | 5,138.9 tok/s | 80 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 194.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-expert | DeepSeek-V4.1-Flash-engram-hbm | 20 | expert | nvlink5 | infiniband_ndr | 160 | 360.51 us | 277.4 tok/s | 2,773.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 167.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 20 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.87 us | 343.8 tok/s | 3,438.0 tok/s | 80 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 194.59 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.27 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.99 us | 2,703.5 tok/s | 27,035.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.28 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-tensor | DeepSeek-V4.1-Flash-engram-hbm | 29 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 29 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.8 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-expert | DeepSeek-V4.1-Flash-engram-hbm | 29 | expert | nvlink5 | infiniband_ndr | 160 | 358.59 us | 278.9 tok/s | 2,788.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.8 tok/s | 3,438.5 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.20 us | 2,617.8 tok/s | 26,177.9 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.50 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-tensor | DeepSeek-V4.1-Flash-engram-hbm | 30 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 30 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 30 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.7 tok/s | 80 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-expert | DeepSeek-V4.1-Flash-engram-hbm | 30 | expert | nvlink5 | infiniband_ndr | 160 | 358.47 us | 279.0 tok/s | 2,789.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 30 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.5 tok/s | 80 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.62 us | 2,461.7 tok/s | 24,616.6 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.92 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-tensor | DeepSeek-V4.1-Flash-engram-hbm | 32 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 32 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 32 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.65 us | 513.8 tok/s | 5,137.5 tok/s | 80 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 194.65 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-expert | DeepSeek-V4.1-Flash-engram-hbm | 32 | expert | nvlink5 | infiniband_ndr | 160 | 358.07 us | 279.3 tok/s | 2,792.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 32 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.6 tok/s | 80 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 194.65 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 35 | pipeline | nvlink5 | infiniband_ndr | 34 | 45.28 us | 2,208.5 tok/s | 22,084.5 tok/s | 30 x point_to_point span 2 on nvlink5 (traversals 1.0) = 36.34 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-tensor | DeepSeek-V4.1-Flash-engram-hbm | 35 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 35 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 35 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.65 us | 513.7 tok/s | 5,137.4 tok/s | 80 x all_reduce span 35 on nvlink5_nvl72 (traversals 2.0) = 194.65 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-expert | DeepSeek-V4.1-Flash-engram-hbm | 35 | expert | nvlink5 | infiniband_ndr | 160 | 357.81 us | 279.5 tok/s | 2,794.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 35 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.81 us | 343.9 tok/s | 3,438.7 tok/s | 80 x all_reduce span 35 on nvlink5_nvl72 (traversals 2.0) = 194.65 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x39-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 39 | pipeline | nvlink5 | infiniband_ndr | 38 | 50.13 us | 1,995.0 tok/s | 19,949.7 tok/s | 34 x point_to_point span 2 on nvlink5 (traversals 1.0) = 41.19 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x39-tensor | DeepSeek-V4.1-Flash-engram-hbm | 39 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x39-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 39 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x39-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 39 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.1 tok/s | 80 x all_reduce span 39 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x39-expert | DeepSeek-V4.1-Flash-engram-hbm | 39 | expert | nvlink5 | infiniband_ndr | 160 | 357.52 us | 279.7 tok/s | 2,797.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x39-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 39 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 39 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 41 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-tensor | DeepSeek-V4.1-Flash-engram-hbm | 41 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 41 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 41 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.1 tok/s | 80 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-expert | DeepSeek-V4.1-Flash-engram-hbm | 41 | expert | nvlink5 | infiniband_ndr | 160 | 357.28 us | 279.9 tok/s | 2,799.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.80 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 41 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.13 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 46 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-tensor | DeepSeek-V4.1-Flash-engram-hbm | 46 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 46 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.9 tok/s | 80 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-expert | DeepSeek-V4.1-Flash-engram-hbm | 46 | expert | nvlink5 | infiniband_ndr | 160 | 357.01 us | 280.1 tok/s | 2,801.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 47 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-tensor | DeepSeek-V4.1-Flash-engram-hbm | 47 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 47 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 47 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.8 tok/s | 80 x all_reduce span 47 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-expert | DeepSeek-V4.1-Flash-engram-hbm | 47 | expert | nvlink5 | infiniband_ndr | 160 | 356.97 us | 280.1 tok/s | 2,801.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x47-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 47 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 47 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 55 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-tensor | DeepSeek-V4.1-Flash-engram-hbm | 55 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 55 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 55 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.6 tok/s | 80 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-expert | DeepSeek-V4.1-Flash-engram-hbm | 55 | expert | nvlink5 | infiniband_ndr | 160 | 356.59 us | 280.4 tok/s | 2,804.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 55 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.10 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 58 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-tensor | DeepSeek-V4.1-Flash-engram-hbm | 58 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 58 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.5 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-expert | DeepSeek-V4.1-Flash-engram-hbm | 58 | expert | nvlink5 | infiniband_ndr | 160 | 356.44 us | 280.6 tok/s | 2,805.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.09 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.09 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x64-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 64 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x64-tensor | DeepSeek-V4.1-Flash-engram-hbm | 64 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x64-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 64 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x64-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 64 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 64 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x64-expert | DeepSeek-V4.1-Flash-engram-hbm | 64 | expert | nvlink5 | infiniband_ndr | 160 | 356.23 us | 280.7 tok/s | 2,807.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x64-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 64 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 64 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.09 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x67-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 67 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x67-tensor | DeepSeek-V4.1-Flash-engram-hbm | 67 | tensor | nvlink5 | infiniband_ndr | 160 | 562.88 us | 177.7 tok/s | 1,776.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 368.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x67-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 67 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x67-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 67 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 67 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x67-expert | DeepSeek-V4.1-Flash-engram-hbm | 67 | expert | nvlink5 | infiniband_ndr | 160 | 356.17 us | 280.8 tok/s | 2,807.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x67-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 67 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 67 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x68-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 68 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x68-tensor | DeepSeek-V4.1-Flash-engram-hbm | 68 | tensor | nvlink5 | infiniband_ndr | 160 | 562.88 us | 177.7 tok/s | 1,776.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 368.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x68-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 68 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x68-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 68 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 68 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x68-expert | DeepSeek-V4.1-Flash-engram-hbm | 68 | expert | nvlink5 | infiniband_ndr | 160 | 356.14 us | 280.8 tok/s | 2,807.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.85 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x68-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 68 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 68 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 71 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-tensor | DeepSeek-V4.1-Flash-engram-hbm | 71 | tensor | nvlink5 | infiniband_ndr | 160 | 562.88 us | 177.7 tok/s | 1,776.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 368.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 71 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 71 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.3 tok/s | 80 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-expert | DeepSeek-V4.1-Flash-engram-hbm | 71 | expert | nvlink5 | infiniband_ndr | 160 | 356.08 us | 280.8 tok/s | 2,808.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.78 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 71 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.2 tok/s | 80 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x80-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 80 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x80-tensor | DeepSeek-V4.1-Flash-engram-hbm | 80 | tensor | nvlink5 | infiniband_ndr | 160 | 563.43 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 369.04 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x80-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 80 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x80-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 80 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x80-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 80 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x80-expert | DeepSeek-V4.1-Flash-engram-hbm | 80 | expert | nvlink5 | infiniband_ndr | 160 | 355.87 us | 281.0 tok/s | 2,810.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x80-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 80 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.32 us | 279.1 tok/s | 2,790.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 82 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-tensor | DeepSeek-V4.1-Flash-engram-hbm | 82 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 82 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 82 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 82 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-expert | DeepSeek-V4.1-Flash-engram-hbm | 82 | expert | nvlink5 | infiniband_ndr | 160 | 355.84 us | 281.0 tok/s | 2,810.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.60 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 82 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.29 us | 279.1 tok/s | 2,791.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.60 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 83 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-tensor | DeepSeek-V4.1-Flash-engram-hbm | 83 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 83 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 83 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 83 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-expert | DeepSeek-V4.1-Flash-engram-hbm | 83 | expert | nvlink5 | infiniband_ndr | 160 | 355.82 us | 281.0 tok/s | 2,810.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 83 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.28 us | 279.1 tok/s | 2,791.1 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x84-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 84 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x84-tensor | DeepSeek-V4.1-Flash-engram-hbm | 84 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x84-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 84 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x84-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 84 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x84-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 84 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x84-expert | DeepSeek-V4.1-Flash-engram-hbm | 84 | expert | nvlink5 | infiniband_ndr | 160 | 355.81 us | 281.0 tok/s | 2,810.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x84-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 84 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.26 us | 279.1 tok/s | 2,791.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 87 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-tensor | DeepSeek-V4.1-Flash-engram-hbm | 87 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 87 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-expert | DeepSeek-V4.1-Flash-engram-hbm | 87 | expert | nvlink5 | infiniband_ndr | 160 | 355.77 us | 281.1 tok/s | 2,810.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.22 us | 279.2 tok/s | 2,791.6 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 98 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-tensor | DeepSeek-V4.1-Flash-engram-hbm | 98 | tensor | nvlink5 | infiniband_ndr | 160 | 564.56 us | 177.1 tok/s | 1,771.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 370.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 98 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.21 us | 452.1 tok/s | 4,520.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 26.82 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 98 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 98 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-expert | DeepSeek-V4.1-Flash-engram-hbm | 98 | expert | nvlink5 | infiniband_ndr | 160 | 355.60 us | 281.2 tok/s | 2,812.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.20 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 98 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.10 us | 279.3 tok/s | 2,792.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 110 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-tensor | DeepSeek-V4.1-Flash-engram-hbm | 110 | tensor | nvlink5 | infiniband_ndr | 160 | 564.83 us | 177.0 tok/s | 1,770.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 370.44 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 110 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.44 us | 447.5 tok/s | 4,475.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 29.05 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 110 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 110 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-expert | DeepSeek-V4.1-Flash-engram-hbm | 110 | expert | nvlink5 | infiniband_ndr | 160 | 355.48 us | 281.3 tok/s | 2,813.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.18 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.29 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 110 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.99 us | 279.3 tok/s | 2,793.4 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.29 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 116 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-tensor | DeepSeek-V4.1-Flash-engram-hbm | 116 | tensor | nvlink5 | infiniband_ndr | 160 | 565.06 us | 177.0 tok/s | 1,769.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 370.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 116 | hybrid | nvlink5 | infiniband_ndr | 94 | 225.68 us | 443.1 tok/s | 4,431.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.29 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-expert | DeepSeek-V4.1-Flash-engram-hbm | 116 | expert | nvlink5 | infiniband_ndr | 160 | 355.42 us | 281.4 tok/s | 2,813.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.17 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.94 us | 279.4 tok/s | 2,793.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 126 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-tensor | DeepSeek-V4.1-Flash-engram-hbm | 126 | tensor | nvlink5 | infiniband_ndr | 160 | 565.27 us | 176.9 tok/s | 1,769.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 370.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 126 | hybrid | nvlink5 | infiniband_ndr | 95 | 227.91 us | 438.8 tok/s | 4,387.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 126 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 126 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-expert | DeepSeek-V4.1-Flash-engram-hbm | 126 | expert | nvlink5 | infiniband_ndr | 160 | 355.34 us | 281.4 tok/s | 2,814.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.16 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 126 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.87 us | 279.4 tok/s | 2,794.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 130 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-tensor | DeepSeek-V4.1-Flash-engram-hbm | 130 | tensor | nvlink5 | infiniband_ndr | 160 | 565.45 us | 176.9 tok/s | 1,768.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 371.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 130 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.15 us | 434.5 tok/s | 4,345.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 35.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 130 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 130 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-expert | DeepSeek-V4.1-Flash-engram-hbm | 130 | expert | nvlink5 | infiniband_ndr | 160 | 355.31 us | 281.4 tok/s | 2,814.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.15 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 130 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.85 us | 279.4 tok/s | 2,794.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 173 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-tensor | DeepSeek-V4.1-Flash-engram-hbm | 173 | tensor | nvlink5 | infiniband_ndr | 160 | 566.11 us | 176.6 tok/s | 1,766.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 371.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 173 | hybrid | nvlink5 | infiniband_ndr | 101 | 241.32 us | 414.4 tok/s | 4,143.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-expert | DeepSeek-V4.1-Flash-engram-hbm | 173 | expert | nvlink5 | infiniband_ndr | 160 | 355.08 us | 281.6 tok/s | 2,816.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.11 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.31 us | 280.7 tok/s | 2,806.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x184-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 184 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x184-tensor | DeepSeek-V4.1-Flash-engram-hbm | 184 | tensor | nvlink5 | infiniband_ndr | 160 | 566.20 us | 176.6 tok/s | 1,766.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 23 on infiniband_ndr (traversals 2.0) = 371.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x184-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 184 | hybrid | nvlink5 | infiniband_ndr | 102 | 243.55 us | 410.6 tok/s | 4,105.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 22 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 49.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x184-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 184 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x184-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 184 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x184-expert | DeepSeek-V4.1-Flash-engram-hbm | 184 | expert | nvlink5 | infiniband_ndr | 160 | 355.04 us | 281.7 tok/s | 2,816.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x184-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 184 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.28 us | 280.7 tok/s | 2,806.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x185-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 185 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x185-tensor | DeepSeek-V4.1-Flash-engram-hbm | 185 | tensor | nvlink5 | infiniband_ndr | 160 | 566.29 us | 176.6 tok/s | 1,765.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 371.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x185-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 185 | hybrid | nvlink5 | infiniband_ndr | 103 | 245.79 us | 406.9 tok/s | 4,068.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 51.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x185-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 185 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x185-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 185 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x185-expert | DeepSeek-V4.1-Flash-engram-hbm | 185 | expert | nvlink5 | infiniband_ndr | 160 | 355.04 us | 281.7 tok/s | 2,816.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x185-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 185 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.28 us | 280.7 tok/s | 2,806.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 188 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-tensor | DeepSeek-V4.1-Flash-engram-hbm | 188 | tensor | nvlink5 | infiniband_ndr | 160 | 566.29 us | 176.6 tok/s | 1,765.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 371.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 188 | hybrid | nvlink5 | infiniband_ndr | 103 | 245.79 us | 406.9 tok/s | 4,068.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 51.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 188 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 188 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-expert | DeepSeek-V4.1-Flash-engram-hbm | 188 | expert | nvlink5 | infiniband_ndr | 160 | 355.03 us | 281.7 tok/s | 2,816.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 188 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.27 us | 280.7 tok/s | 2,806.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 192 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-tensor | DeepSeek-V4.1-Flash-engram-hbm | 192 | tensor | nvlink5 | infiniband_ndr | 160 | 566.29 us | 176.6 tok/s | 1,765.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 371.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 192 | hybrid | nvlink5 | infiniband_ndr | 103 | 245.79 us | 406.9 tok/s | 4,068.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 51.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 192 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 192 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-expert | DeepSeek-V4.1-Flash-engram-hbm | 192 | expert | nvlink5 | infiniband_ndr | 160 | 355.01 us | 281.7 tok/s | 2,816.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 192 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.26 us | 280.7 tok/s | 2,807.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 193 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-tensor | DeepSeek-V4.1-Flash-engram-hbm | 193 | tensor | nvlink5 | infiniband_ndr | 160 | 566.38 us | 176.6 tok/s | 1,765.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 371.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 193 | hybrid | nvlink5 | infiniband_ndr | 104 | 248.02 us | 403.2 tok/s | 4,031.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 53.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 193 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 193 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-expert | DeepSeek-V4.1-Flash-engram-hbm | 193 | expert | nvlink5 | infiniband_ndr | 160 | 355.01 us | 281.7 tok/s | 2,816.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 193 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.26 us | 280.7 tok/s | 2,807.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 194 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-tensor | DeepSeek-V4.1-Flash-engram-hbm | 194 | tensor | nvlink5 | infiniband_ndr | 160 | 566.38 us | 176.6 tok/s | 1,765.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 371.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 194 | hybrid | nvlink5 | infiniband_ndr | 104 | 248.02 us | 403.2 tok/s | 4,031.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 53.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 194 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 194 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-expert | DeepSeek-V4.1-Flash-engram-hbm | 194 | expert | nvlink5 | infiniband_ndr | 160 | 355.01 us | 281.7 tok/s | 2,816.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 194 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.25 us | 280.7 tok/s | 2,807.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 196 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-tensor | DeepSeek-V4.1-Flash-engram-hbm | 196 | tensor | nvlink5 | infiniband_ndr | 160 | 566.38 us | 176.6 tok/s | 1,765.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 371.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 196 | hybrid | nvlink5 | infiniband_ndr | 104 | 248.02 us | 403.2 tok/s | 4,031.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 53.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 196 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 196 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-expert | DeepSeek-V4.1-Flash-engram-hbm | 196 | expert | nvlink5 | infiniband_ndr | 160 | 355.00 us | 281.7 tok/s | 2,816.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 196 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.25 us | 280.7 tok/s | 2,807.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 231 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-tensor | DeepSeek-V4.1-Flash-engram-hbm | 231 | tensor | nvlink5 | infiniband_ndr | 160 | 566.65 us | 176.5 tok/s | 1,764.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 372.26 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 231 | hybrid | nvlink5 | infiniband_ndr | 108 | 256.96 us | 389.2 tok/s | 3,891.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 62.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 556.36 us | 179.7 tok/s | 1,797.4 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 83 | 201.40 us | 496.5 tok/s | 4,965.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-expert | DeepSeek-V4.1-Flash-engram-hbm | 231 | expert | nvlink5 | infiniband_ndr | 160 | 354.91 us | 281.8 tok/s | 2,817.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.09 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.72 us | 281.1 tok/s | 2,811.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.90 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 318 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-tensor | DeepSeek-V4.1-Flash-engram-hbm | 318 | tensor | nvlink5 | infiniband_ndr | 160 | 567.11 us | 176.3 tok/s | 1,763.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 40 on infiniband_ndr (traversals 2.0) = 372.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 318 | hybrid | nvlink5 | infiniband_ndr | 119 | 281.55 us | 355.2 tok/s | 3,551.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 39 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 87.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 318 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 558.81 us | 179.0 tok/s | 1,789.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 318 | hybrid | nvlink5_nvl72 | infiniband_ndr | 84 | 203.63 us | 491.1 tok/s | 4,910.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-expert | DeepSeek-V4.1-Flash-engram-hbm | 318 | expert | nvlink5 | infiniband_ndr | 160 | 354.77 us | 281.9 tok/s | 2,818.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.06 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 318 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.38 us | 281.4 tok/s | 2,813.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.67 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 347 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-tensor | DeepSeek-V4.1-Flash-engram-hbm | 347 | tensor | nvlink5 | infiniband_ndr | 160 | 567.22 us | 176.3 tok/s | 1,763.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 372.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 347 | hybrid | nvlink5 | infiniband_ndr | 119 | 281.55 us | 355.2 tok/s | 3,551.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 39 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 87.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 558.81 us | 179.0 tok/s | 1,789.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 84 | 203.63 us | 491.1 tok/s | 4,910.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-expert | DeepSeek-V4.1-Flash-engram-hbm | 347 | expert | nvlink5 | infiniband_ndr | 160 | 354.74 us | 281.9 tok/s | 2,819.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.06 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.36 us | 281.4 tok/s | 2,814.1 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.67 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash-engram-hbm | 1 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill | 73,350 | 17,831.9 | 0.243 | 17,831.9 (73,350) | 5,814.0 (46,225) | 0.33x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill | 73,350 | 17,831.9 | 0.243 | 17,831.9 (73,350) | 6,083.4 (92,450) | 0.34x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill | 73,350 | 17,831.9 | 0.243 | 17,831.9 (73,350) | 6,083.4 (92,450) | 0.34x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill | 73,350 | 17,831.9 | 0.243 | 17,831.9 (73,350) | 6,083.4 (92,450) | 0.34x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill | 73,350 | 17,831.9 | 0.243 | 17,831.9 (73,350) | 6,083.4 (92,450) | 0.34x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill | 132,030 | 17,713.5 | 0.134 | 17,713.5 (132,030) | 6,083.4 (92,450) | 0.34x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 17,868.8 | 0.064 | 17,868.8 (277,100) | 6,083.4 (92,450) | 0.34x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | array | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 7,285.3 | 0.026 | 7,285.3 (277,100) | 6,099.7 (277,350) | 0.84x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | wafer | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4,189.9 | 0.008 | 2,039.7 (277,100) | 4,189.9 (554,700) | 2.05x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,629.1 | 0.003 | 609.5 (185,005) | 1,629.1 (554,700) | 2.67x | weight_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 384 | 752.0 MB | 128.3 mm2 | 23.09 mm2 (18.0%) | 49,261 mm2 | 8,867 mm2 | 52,460 mm2 = 64.4 reticles |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | sram | 607,862.2 | 28,795.8 | 28,795.8 | 21.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | sram | 607,862.2 | 28,795.8 | 28,795.8 | 21.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | sram | 607,862.2 | 28,795.8 | 36,995.6 | 21.11x | 1.28x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | sram | 607,862.2 | 28,795.8 | 58,749.1 | 21.11x | 2.04x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | sram | 607,862.2 | 28,795.8 | 93,946.4 | 21.11x | 3.26x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | sram | 607,862.2 | 28,795.8 | 137,559.1 | 21.11x | 4.78x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | sram | 733,489.5 | 28,819.6 | 191,793.5 | 25.45x | 6.65x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | sram | 1,271,077.0 | 28,965.6 | 472,336.4 | 43.88x | 16.31x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | sram | 2,648,118.0 | 29,002.3 | 882,529.1 | 91.31x | 30.43x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | sram | 6,672,650.5 | 29,011.5 | 1,271,764.2 | 230.00x | 43.84x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | rom | 4,159,410.6 | 63,427.3 | 63,427.3 | 65.58x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | rom | 4,159,410.6 | 63,427.3 | 63,427.3 | 65.58x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | rom | 4,159,410.6 | 63,427.3 | 63,427.3 | 65.58x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | rom | 4,159,410.6 | 63,427.3 | 66,198.2 | 65.58x | 1.04x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | rom | 4,159,410.6 | 63,427.3 | 105,959.6 | 65.58x | 1.67x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | rom | 4,159,410.6 | 63,427.3 | 154,910.8 | 65.58x | 2.44x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | rom | 4,159,410.6 | 63,542.7 | 266,259.0 | 65.46x | 4.19x | compute | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | rom | 4,159,410.6 | 64,257.0 | 766,288.3 | 64.73x | 11.93x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | rom | 4,290,432.8 | 64,438.0 | 1,672,480.5 | 66.58x | 25.95x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | rom | 4,501,583.5 | 64,483.5 | 2,578,575.8 | 69.81x | 39.99x | compute | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,159,410.6 | 7.498 | compute | 6.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,159,410.6 | 7.498 | compute | 6.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,159,410.6 | 7.498 | compute | 6.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x28-perregion | 22,820 | 1.00 | 1.43 | 36,995.6 | 1.621 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,159,410.6 | 7.498 | compute | 6.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x28-perregion | 22,820 | 1.00 | 1.99 | 58,749.1 | 2.574 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x35-perregion-romfill | 28,525 | 1.26 | 1.99 | 66,198.2 | 2.321 | weight_read | 0.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,159,410.6 | 7.498 | compute | 6.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x28-perregion | 22,820 | 1.00 | 2.54 | 93,946.4 | 4.117 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x35-perregion-romfill | 28,525 | 1.26 | 2.54 | 105,959.6 | 3.715 | weight_read | 0.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,159,410.6 | 7.498 | compute | 6.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x28-perregion | 22,820 | 1.00 | 3.49 | 137,559.1 | 6.028 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x35-perregion-romfill | 28,525 | 1.26 | 3.49 | 154,910.8 | 5.431 | weight_read | 0.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x113 | 92,095 | 1.00 | 1.00 | 733,489.5 | 7.964 | compute | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,159,410.6 | 7.498 | compute | 5.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,819.6 | 0.623 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.12 | 63,542.7 | 1.375 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.92 | 191,793.5 | 4.149 | weight_read | 0.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 4.92 | 266,259.0 | 5.760 | link_latency | 0.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x162 | 132,030 | 1.00 | 1.00 | 1,271,077.0 | 9.627 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,159,410.6 | 7.498 | compute | 3.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,965.6 | 0.627 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 4.49 | 64,257.0 | 1.390 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 10.96 | 472,336.4 | 10.218 | weight_read | 0.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 10.96 | 766,288.3 | 16.577 | weight_read | 0.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 2,648,118.0 | 9.548 | compute | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,290,432.8 | 7.735 | compute | 1.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 17.96 | 29,002.3 | 0.627 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 17.96 | 64,438.0 | 1.394 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 28.90 | 882,529.1 | 19.092 | weight_read | 0.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 28.90 | 1,672,480.5 | 36.181 | weight_read | 0.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 6,672,650.5 | 12.029 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,501,583.5 | 8.115 | compute | 0.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 71.86 | 29,011.5 | 0.628 | weight_read | 0.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 71.86 | 64,483.5 | 1.395 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 88.68 | 1,271,764.2 | 27.512 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 88.68 | 2,578,575.8 | 55.783 | kv_read | 0.39x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 126 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 126 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 126 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 126 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 126 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 126 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 126 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 171 | 1.50 | 1.004 | 1.043 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 171 | 5.99 | 1.040 | 1.767 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 171 | 23.95 | 1.191 | 3.085 | 2.59x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 4 | 3.87 | 2.63 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 4 | 4.00 | 2.91 | 1.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 4 | 4.00 | 3.16 | 1.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 4 | 4.00 | 3.35 | 1.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 4 | 4.00 | 3.49 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 4 | 4.00 | 3.59 | 1.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 4 | 4.00 | 3.66 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 4 | 4.00 | 3.66 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 4 | 4.00 | 3.66 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 14 | 8.21 | 4.62 | 1.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 14 | 11.54 | 5.81 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 14 | 13.52 | 7.04 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 14 | 13.98 | 8.20 | 1.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 14 | 14.00 | 9.19 | 1.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 14 | 14.00 | 9.93 | 1.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 14 | 14.00 | 10.55 | 1.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 14 | 14.00 | 10.57 | 1.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 14 | 14.00 | 10.57 | 1.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 16 | 8.58 | 4.84 | 1.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 16 | 12.48 | 6.17 | 2.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 16 | 15.15 | 7.57 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 16 | 15.94 | 8.91 | 1.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 16 | 16.00 | 10.08 | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 16 | 16.00 | 10.97 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 16 | 16.00 | 11.71 | 1.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 16 | 16.00 | 11.74 | 1.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 16 | 16.00 | 11.74 | 1.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 18 | 8.89 | 5.04 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 18 | 13.29 | 6.50 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 18 | 16.66 | 8.05 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 18 | 17.86 | 9.57 | 1.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 18 | 18.00 | 10.92 | 1.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 18 | 18.00 | 11.95 | 1.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 18 | 18.00 | 12.83 | 1.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 18 | 18.00 | 12.86 | 1.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 18 | 18.00 | 12.86 | 1.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 20 | 9.14 | 5.21 | 1.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 20 | 13.99 | 6.79 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 20 | 18.06 | 8.50 | 2.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 20 | 19.75 | 10.19 | 1.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 20 | 19.99 | 11.71 | 1.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 20 | 20.00 | 12.89 | 1.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 20 | 20.00 | 13.90 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 20 | 20.00 | 13.93 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 20 | 20.00 | 13.93 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 30 | 9.96 | 5.89 | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 30 | 16.45 | 7.97 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 30 | 23.58 | 10.32 | 2.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 30 | 28.35 | 12.80 | 2.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 30 | 29.83 | 15.13 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 30 | 29.99 | 17.02 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 30 | 30.00 | 18.69 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 30 | 30.00 | 18.76 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 30 | 30.00 | 18.76 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 32 | 10.07 | 6.00 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 32 | 16.80 | 8.16 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 32 | 24.44 | 10.62 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 32 | 29.88 | 13.24 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 32 | 31.74 | 15.73 | 2.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 32 | 31.99 | 17.76 | 1.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 32 | 32.00 | 19.56 | 1.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 32 | 32.00 | 19.64 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 32 | 32.00 | 19.64 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 35 | 10.22 | 6.15 | 1.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 35 | 17.26 | 8.43 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 35 | 25.63 | 11.05 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 35 | 32.07 | 13.87 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 35 | 34.57 | 16.58 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 35 | 34.97 | 18.82 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 35 | 35.00 | 20.82 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 35 | 35.00 | 20.90 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 35 | 35.00 | 20.90 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 39 | 10.37 | 6.33 | 1.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 39 | 17.79 | 8.75 | 2.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 39 | 27.02 | 11.57 | 2.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 39 | 34.77 | 14.65 | 2.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 39 | 38.25 | 17.65 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 39 | 38.93 | 20.16 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 39 | 39.00 | 22.42 | 1.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 39 | 39.00 | 22.51 | 1.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 39 | 39.00 | 22.51 | 1.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 41 | 10.44 | 6.42 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 41 | 18.02 | 8.90 | 2.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 41 | 27.65 | 11.82 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 41 | 36.04 | 15.02 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 41 | 40.04 | 18.16 | 2.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 41 | 40.90 | 20.80 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 41 | 41.00 | 23.19 | 1.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 46 | 10.59 | 6.62 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 46 | 18.52 | 9.24 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 46 | 29.06 | 12.38 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 46 | 38.98 | 15.89 | 2.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 46 | 44.37 | 19.37 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 46 | 45.78 | 22.32 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 46 | 45.99 | 25.03 | 1.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 46 | 45.99 | 25.14 | 1.83x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 46 | 45.99 | 25.14 | 1.83x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 47 | 5.69 | 4.73 | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 47 | 10.62 | 6.66 | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 47 | 18.61 | 9.31 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 47 | 29.32 | 12.49 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 47 | 39.53 | 16.05 | 2.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 47 | 45.21 | 19.60 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 47 | 46.75 | 22.61 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 47 | 46.99 | 25.39 | 1.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 47 | 46.99 | 25.50 | 1.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 47 | 46.99 | 25.50 | 1.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 55 | 10.79 | 6.94 | 1.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 55 | 19.23 | 9.76 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 55 | 31.11 | 13.27 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 55 | 43.55 | 17.27 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 55 | 51.62 | 21.32 | 2.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 55 | 54.37 | 24.83 | 2.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 55 | 54.95 | 28.10 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 55 | 54.95 | 28.23 | 1.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 55 | 54.95 | 28.23 | 1.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 64 | 5.77 | 4.98 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 64 | 10.94 | 7.22 | 1.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 64 | 19.76 | 10.19 | 1.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 64 | 32.72 | 14.03 | 2.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 64 | 47.36 | 18.48 | 2.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 64 | 58.16 | 23.06 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 64 | 62.62 | 27.09 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 64 | 63.83 | 30.89 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 64 | 63.85 | 31.05 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 64 | 63.85 | 31.05 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 67 | 5.78 | 5.02 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 67 | 10.98 | 7.30 | 1.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 67 | 19.91 | 10.32 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 67 | 33.18 | 14.26 | 2.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 67 | 48.49 | 18.85 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 67 | 60.19 | 23.60 | 2.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 67 | 65.29 | 27.79 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 67 | 66.77 | 31.78 | 2.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 67 | 66.79 | 31.94 | 2.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 67 | 66.79 | 31.94 | 2.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 68 | 11.00 | 7.33 | 1.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 68 | 19.95 | 10.36 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 68 | 33.32 | 14.34 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 68 | 48.85 | 18.97 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 68 | 60.85 | 23.78 | 2.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 68 | 66.17 | 28.02 | 2.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 68 | 67.75 | 32.06 | 2.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 68 | 67.77 | 32.23 | 2.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 68 | 67.77 | 32.23 | 2.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 71 | 11.03 | 7.41 | 1.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 71 | 20.09 | 10.48 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 71 | 33.74 | 14.56 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 71 | 49.90 | 19.33 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 71 | 62.78 | 24.30 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 71 | 68.77 | 28.70 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 71 | 70.66 | 32.91 | 2.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 71 | 70.69 | 33.09 | 2.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 71 | 70.69 | 33.09 | 2.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 80 | 5.82 | 5.14 | 1.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 80 | 11.13 | 7.64 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 80 | 20.43 | 10.80 | 1.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 80 | 34.84 | 15.19 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 80 | 52.72 | 20.32 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 80 | 68.18 | 25.75 | 2.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 80 | 76.28 | 30.63 | 2.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 80 | 79.30 | 35.34 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 80 | 79.36 | 35.53 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 80 | 79.36 | 35.53 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 82 | 11.15 | 7.68 | 1.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 82 | 20.50 | 10.86 | 1.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 82 | 35.06 | 15.32 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 82 | 53.29 | 20.53 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 82 | 69.30 | 26.05 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 82 | 77.88 | 31.04 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 82 | 81.20 | 35.85 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 82 | 81.26 | 36.05 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 82 | 81.26 | 36.05 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 83 | 11.15 | 7.71 | 1.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 83 | 20.53 | 10.90 | 1.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 83 | 35.16 | 15.38 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 83 | 53.57 | 20.63 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 83 | 69.85 | 26.20 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 83 | 78.68 | 31.24 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 83 | 82.14 | 36.11 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 84 | 11.16 | 7.73 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 84 | 20.56 | 10.93 | 1.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 84 | 35.26 | 15.45 | 2.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 84 | 53.84 | 20.73 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 84 | 70.40 | 26.35 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 84 | 79.47 | 31.44 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 84 | 83.08 | 36.36 | 2.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 84 | 83.15 | 36.57 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 84 | 83.15 | 36.57 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 98 | 11.27 | 8.02 | 1.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 98 | 20.94 | 11.34 | 1.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 98 | 36.52 | 16.28 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 98 | 57.24 | 22.06 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 98 | 77.39 | 28.31 | 2.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 98 | 89.96 | 34.06 | 2.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 98 | 95.95 | 39.72 | 2.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 110 | 11.33 | 8.24 | 1.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 110 | 21.20 | 11.65 | 1.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 110 | 37.37 | 16.92 | 2.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 110 | 59.63 | 23.06 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 110 | 82.55 | 29.82 | 2.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 110 | 98.14 | 36.10 | 2.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 110 | 106.49 | 42.35 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 126 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 126 | 11.40 | 8.50 | 1.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 126 | 21.47 | 12.02 | 1.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 126 | 38.29 | 17.66 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 126 | 62.26 | 24.23 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 126 | 88.47 | 31.63 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 126 | 107.95 | 38.58 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 126 | 119.76 | 45.56 | 2.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 126 | 120.09 | 45.86 | 2.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 126 | 120.09 | 45.86 | 2.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 130 | 11.42 | 8.56 | 1.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 130 | 21.53 | 12.10 | 1.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 130 | 38.48 | 17.83 | 2.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 130 | 62.84 | 24.50 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 130 | 89.81 | 32.05 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 130 | 110.22 | 39.16 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 130 | 122.94 | 46.32 | 2.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 130 | 123.30 | 46.63 | 2.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 130 | 123.30 | 46.63 | 2.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 184 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 184 | 11.56 | 9.19 | 1.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 184 | 22.07 | 13.13 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 184 | 40.37 | 19.61 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 184 | 68.55 | 27.47 | 2.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 184 | 103.64 | 36.82 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 184 | 135.28 | 45.85 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 184 | 160.44 | 55.21 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 184 | 161.30 | 55.62 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 184 | 161.30 | 55.62 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 185 | 11.56 | 9.20 | 1.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 185 | 22.07 | 13.14 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 185 | 40.40 | 19.63 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 185 | 68.63 | 27.52 | 2.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 185 | 103.84 | 36.90 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 185 | 135.66 | 45.96 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 185 | 161.05 | 55.36 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 185 | 161.92 | 55.76 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 185 | 161.92 | 55.76 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 188 | 11.57 | 9.23 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 188 | 22.10 | 13.19 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 188 | 40.47 | 19.71 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 188 | 68.86 | 27.66 | 2.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 188 | 104.43 | 37.13 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 188 | 136.79 | 46.29 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 188 | 162.85 | 55.79 | 2.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 188 | 163.75 | 56.20 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 188 | 163.75 | 56.20 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 192 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 192 | 11.57 | 9.27 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 192 | 22.12 | 13.26 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 192 | 40.57 | 19.81 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 192 | 69.16 | 27.85 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 192 | 105.19 | 37.43 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 192 | 138.26 | 46.71 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 192 | 165.21 | 56.35 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 192 | 166.15 | 56.77 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 192 | 166.15 | 56.77 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 193 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 193 | 11.58 | 9.28 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 193 | 22.13 | 13.28 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 193 | 40.59 | 19.83 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 193 | 69.24 | 27.89 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 193 | 105.38 | 37.51 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 193 | 138.62 | 46.82 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 193 | 165.80 | 56.49 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 193 | 166.74 | 56.91 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 193 | 166.74 | 56.91 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 194 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 194 | 11.58 | 9.29 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 194 | 22.14 | 13.29 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 194 | 40.62 | 19.86 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 194 | 69.31 | 27.94 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 194 | 105.56 | 37.58 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 194 | 138.98 | 46.92 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 194 | 166.38 | 56.63 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 194 | 167.33 | 57.05 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 194 | 167.33 | 57.05 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 196 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 196 | 11.58 | 9.30 | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 196 | 22.15 | 13.32 | 1.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 196 | 40.66 | 19.90 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 196 | 69.45 | 28.03 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 196 | 105.93 | 37.73 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 196 | 139.69 | 47.13 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 196 | 167.53 | 56.91 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 196 | 168.51 | 57.33 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 196 | 168.51 | 57.33 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 318 | 5.95 | 5.75 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 318 | 11.70 | 10.06 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 318 | 22.63 | 14.98 | 1.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 318 | 42.42 | 21.93 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 318 | 75.10 | 32.72 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 318 | 120.98 | 44.77 | 2.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 318 | 170.47 | 57.13 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 318 | 221.06 | 70.66 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 318 | 223.12 | 71.25 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 318 | 223.12 | 71.25 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 347 | 11.72 | 10.18 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 347 | 22.70 | 15.30 | 1.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 347 | 42.66 | 22.28 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 347 | 75.90 | 33.59 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 347 | 123.23 | 45.96 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 347 | 175.33 | 59.00 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 347 | 230.16 | 73.28 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 347 | 232.44 | 73.90 | 3.15x |

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
| gpu | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 4.3% |
| rom | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 18.6% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | sram | interleaved | 128 B | 1.42x |
| DeepSeek-V4.1-Flash-engram-hbm | hbm | interleaved | 32 B | 1.12x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 132 | 0.00% | 0.10 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 126 | 0.00% | 0.10 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 126 | 0.00% | 0.10 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 126 | 0.00% | 0.10 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 126 | 0.00% | 0.10 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 126 | 0.00% | 0.10 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 126 | 0.00% | 0.10 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 3 | 0.01% | 0.14 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 3 | 0.02% | 0.55 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 3 | 0.08% | 2.21 | 15.81 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 2,137.2 | 121,822.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 2,137.2 | 121,822.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 2,137.2 | 121,822.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 2,137.2 | 121,822.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 2,137.2 | 121,822.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 2,137.2 | 121,822.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 1.75% | 13.6 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 1,910.1 | 122,248.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 6.83% | 28.2 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 488.0 | 124,919.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 24.64% | 79.7 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 122.7 | 125,606.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 67.75% | 204.2 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 30.7 | 125,778.8 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 4 |
| gpu | link_latency | 1369 |
| gpu | thermal | 404 |
| gpu | weight_read | 823 |
| rom | compute | 1061 |
| rom | infeasible | 2493 |
| rom | kv_read | 1 |
| rom | link_latency | 1342 |
| rom | weight_read | 893 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2493 |

## Mechanical consistency audit

**FAIL** over 181,007 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x132', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x139', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x157', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x164', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x165', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x132', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x139', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x157', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x164', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x165', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x132', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x139', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x157', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x164', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x165', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x132', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x139', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x157', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x164', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x165', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4.1-Flash-engram-hbm', 1)

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

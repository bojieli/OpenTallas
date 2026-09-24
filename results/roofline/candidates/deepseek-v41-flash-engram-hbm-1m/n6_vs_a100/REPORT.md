# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash-engram-hbm-1m

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash-engram-hbm at 1,000,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 287x (ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream, 398 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 158 devices. On the GPU side the correction reaches 68x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 102 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-hbm takes 75 x 815 mm2 (61,125 mm2, array, KV in HBM) at 9,381 tok/s per user and 153 tok/s per 1,000 mm2, holding 5,821 sessions, against 74 copies of one unified HBM die at the same silicon: 8.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-hbm on 277,100 mm2 of ROM silicon at 9,990 tok/s per user against 276,710 mm2 of a100_sxm_80gb-x335-tensor at 843 tok/s: **11.9x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 27,195 resident sessions against the GPU cluster's 26,447. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 9.41x to it.** At 231,125 mm2 on DeepSeek-V4.1-Flash-engram-hbm the pipeline-only GPU delivers 122.62 tok/s and the same silicon running tensor delivers 1,154 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `link_latency`) to 3.60x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-hbm engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 581 to 43,872 tok/s, and its rate with every slot occupied from 43,590 to 43,872. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 75 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 189.6 us and cap it at 5,276 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 137 of 4547 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 65.6x of aggregate throughput (DeepSeek-V4.1-Flash-engram-hbm). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 14.71x, on DeepSeek-V4.1-Flash-engram-hbm at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 80% of its cooling budget. The companion study at the other node does have power-limited points.


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

### DeepSeek-V4.1-Flash-engram-hbm at 1,000,000 tokens

**Recommended: `ROM-N6-native-HBMKV-array-hw-tensor-x75`** -- 75 x 815 mm2 reticle dies, 61,125 mm2 total, `tensor`-parallel, KV in HBM, spare silicon to `sram`.

- **9,381.3 tok/s per user** (0.11 ms/token), binding on `link_latency`
- **153.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 9,381 tok/s aggregate with every slot full, over 5,821 resident sessions (fill limited by `batch`)
- 4,931 W at 0.081 W/mm2, 525.6 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 74 copies of one unified HBM die -- `a100_sxm_80gb-x74-tensor`, 61,124 mm2, area ratio 1.0000 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 61,125 | 61,124 | 1.0000 |
| user tok/s | 9,381.3 | 1,064.7 | 8.81x |
| aggregate tok/s | 9,381 | 1,065 | 1.03x |
| resident sessions | 5,821 | 5,396 | -- |
| J/token | 0.5256 | 11.4347 | 21.8x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 5,821 sessions against one that holds 5,396 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x280-tensor` at 231,280 mm2 and 1,154.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x158` | 128,770 | 11,701.3 | 90.9 | 12,516 | 10.38x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 11,911.5 | 91.3 | 12,677 | 10.56x |
| smallest feasible machine | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | 61,125 | 9,381.3 | 153.5 | 5,821 | 8.81x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | 61,125 | 9,381.3 | 153.5 | 5,821 | 8.81x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-HBMKV-array-hw-tensor-x75` | 61,125 | 9,381.3 | 153.5 | -- | 153.5 | ACCEPT |
| `ROM-N6-native-HBMKV-array-hw-tensor-x87` | 70,905 | 10,860.7 | 153.2 | 151.3 | 153.5 | stop |
| `ROM-N6-native-HBMKV-array-hw-tensor-x92` | 74,980 | 11,068.8 | 147.6 | 121.8 | 153.5 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 11,911.5 | 91.3 | 36.5 | 153.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-array-hw-tensor-x75` **<-- recommended** | 61,125 | 75 | 9,381.3 | 9,381 | 153.5 | 5,821 | `link_latency` | 4,931 | 525.6 | `a100_sxm_80gb-x74-tensor` | 8.81x |
| `ROM-N6-native-HBMKV-array-hw-tensor-x87` | 70,905 | 87 | 10,860.7 | 10,861 | 153.2 | 6,789 | `link_latency` | 6,566 | 604.6 | `a100_sxm_80gb-x86-tensor` | 10.05x |
| `ROM-N6-native-HBMKV-array-hw-tensor-x92` | 74,980 | 92 | 11,068.8 | 11,069 | 147.6 | 7,193 | `link_latency` | 7,234 | 653.5 | `a100_sxm_80gb-x91-tensor` | 10.19x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 160 | 11,911.5 | 476,460 | 91.3 | 12,677 | `compute` | 31,622 | 1,364.2 | `a100_sxm_80gb-x158-tensor` | 10.56x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 306 | densest | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | 61,125 | 9,381.3 | 153.5 | 5,821 |
| array | 306 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 11,911.5 | 91.3 | 12,677 |
| array | 306 | smallest | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | 61,125 | 9,381.3 | 153.5 | 5,821 |
| wafer | 54 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | 138,675 | 4,838.6 | 34.9 | 1 |
| wafer | 54 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,827.5 | 10.5 | 1 |
| wafer | 54 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x3` | 138,675 | 4,838.6 | 34.9 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 11,911.5 | 476,460 | 12,677 | 31,622 | 1,364.2 | `compute` | `a100_sxm_80gb-x158-tensor` | 1,128.2 | 12,171 | 21,619.2 | 0.999 | 10.56x | 15.8x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,827.5 | 5,828 | 1 | 45,776 | 7,855.1 | `link_latency` | `a100_sxm_80gb-x672-tensor` | 850.4 | 53,627 | 115,495.2 | 0.999 | 6.85x | 14.7x |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 11,911.5 | 476,460 | 12,677 | 31,622 | 698.6 | `compute` | `a100_sxm_80gb-x158-tensor` | 995.1 | 12,171 | 12,410.0 | 0.999 | 11.97x | 17.8x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 323,575 | 5,476.8 | 38,337 | 4,628 | 43,737 | 3,910.3 | `link_latency` | `a100_sxm_80gb-x392-tensor` | 772.6 | 31,044 | 37,577.5 | 0.999 | 7.09x | 9.6x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 11,911.5 | 476,460 | 12,677 | 31,622 | 365.9 | `compute` | `a100_sxm_80gb-x158-tensor` | 805.7 | 12,171 | 7,795.4 | 0.999 | 14.78x | 21.3x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x7` | 323,575 | 5,476.8 | 38,337 | 4,628 | 43,737 | 1,971.7 | `link_latency` | `a100_sxm_80gb-x392-tensor` | 659.9 | 31,044 | 22,160.2 | 0.999 | 8.30x | 11.2x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 11,911.5 | 476,460 | 12,677 | 31,622 | 199.5 | `compute` | `a100_sxm_80gb-x158-hybrid` | 674.7 | 12,171 | 5,626.0 | 0.999 | 17.65x | 27.4x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 369,800 | 5,473.7 | 43,790 | 5,321 | 50,741 | 1,158.7 | `link_latency` | `a100_sxm_80gb-x448-hybrid` | 658.7 | 35,561 | 13,674.9 | 0.999 | 8.31x | 11.8x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 11,911.5 | 476,460 | 12,677 | 31,622 | 116.3 | `compute` | `a100_sxm_80gb-x158-hybrid` | 674.7 | 12,171 | 3,512.7 | 0.999 | 17.65x | 30.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 5,288.8 | 84,620 | 8,096 | 79,328 | 937.5 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 658.7 | 53,627 | 10,606.0 | 0.999 | 8.03x | 11.3x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x160` | 130,400 | 11,911.5 | 476,460 | 12,677 | 31,622 | 74.7 | `compute` | `a100_sxm_80gb-x158-hybrid` | 585.6 | 12,171 | 2,278.8 | 0.999 | 20.34x | 30.5x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,694.6 | 150,228 | 8,096 | 81,304 | 541.2 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 658.7 | 53,627 | 6,002.8 | 0.999 | 7.13x | 11.1x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 9,989.5 | 689,276 | 22,033 | 47,792 | 72.2 | `compute` | `a100_sxm_80gb-x272-hybrid` | 544.8 | 21,366 | 2,102.8 | 1.001 | 18.34x | 29.1x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,833.4 | 245,336 | 8,096 | 84,164 | 343.1 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 658.7 | 53,627 | 3,701.2 | 0.999 | 5.82x | 10.8x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 224,940 | 4,307.8 | 1,102,798 | 22,033 | 65,521 | 59.4 | `weight_read` | `a100_sxm_80gb-x272-hybrid` | 258.6 | 21,366 | 1,192.4 | 1.001 | 16.66x | 13.4x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,824.8 | 467,145 | 8,096 | 90,772 | 194.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 437.1 | 53,627 | 1,657.2 | 0.999 | 4.17x | 7.0x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 1,557.1 | 1,594,518 | 27,195 | 88,367 | 55.4 | `weight_read` | `a100_sxm_80gb-x335-expert` | 205.9 | 26,065 | 289.3 | 1.001 | 7.56x | 5.2x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 647.4 | 662,891 | 8,096 | 97,930 | 147.7 | `kv_read` | `a100_sxm_80gb-x672-expert` | 271.3 | 52,835 | 409.2 | 0.999 | 2.39x | 2.8x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 418.3 | 1,713,187 | 27,195 | 91,203 | 53.2 | `compute` | `a100_sxm_80gb-x335-expert` | 116.1 | 26,065 | 138.7 | 1.001 | 3.60x | 2.6x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 163.0 | 667,730 | 8,096 | 97,173 | 145.5 | `kv_read` | `a100_sxm_80gb-x672-expert` | 180.1 | 52,835 | 168.6 | 0.999 | 0.91x | 1.2x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-HBMKV-array-hw-tensor-x75` | 61,125 | array | HBM | 5,821 |
| 2 | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | 70,905 | array | HBM | 6,789 |
| 4 | `ROM-N6-native-HBMKV-array-hw-tensor-x92` | 74,980 | array | HBM | 7,193 |
| 8-32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x127-romfill` | 103,505 | array | HBM | 10,015 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x170` | 138,550 | array | HBM | 13,484 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 185,005 | array | HBM | 18,081 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | array | HBM | 27,195 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | rom | 75, 87, 92, 103, 104, 113, 125, 127, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | sram | 75, 87, 92, 103, 104, 113, 138, 158, 160, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | rom | 170, 172, 185, 207, 208, 227, 248, 330, 340, 373, 376, 378 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | sram | 170, 172, 185, 207, 221, 227, 248, 250, 251, 330, 340 |

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
(4.327e+11 B/s/mm2).

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

**The thermal limit can bind now, and this is the first version of this
study in which it could -- in this one it does not, and the companion
study at the other node is where it does.**
Static power is charged per mm2 per second whether or not a byte moves,
so the coolable step time solves
`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the
total energy by the total limit. Under the old rule stretching a step
always reduced modelled power, so every design was coolable at some speed
and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across
both studies.

- **0 of 4,547 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 35%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,787 | 0 | 64.9% | 79.7% | 0.386 | 56% |
| rom | wafer (>=40,000 mm2) | 2,760 | 0 | 24.7% | 65.8% | 0.329 | 77% |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 128,770 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158` | 1.365512 | 31,079.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-tensor` | 21.378006 | 24,101.8 | link_latency | 15.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 128,770 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158` | 0.699302 | 31,079.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-tensor` | 12.274884 | 24,408.8 | link_latency | 17.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 128,770 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158` | 0.366197 | 31,079.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-tensor` | 7.713353 | 24,831.0 | link_latency | 21.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 128,770 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158` | 0.199644 | 31,079.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-hybrid` | 5.609219 | 41,244.3 | weight_read | 27.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 128,770 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158` | 0.116368 | 31,079.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-hybrid` | 3.504373 | 41,244.3 | weight_read | 30.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 128,770 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158` | 0.074730 | 31,079.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-hybrid` | 2.274512 | 42,229.5 | weight_read | 30.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 224,940 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 0.072168 | 47,792.1 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid` | 2.102774 | 73,311.3 | weight_read | 29.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 224,940 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 0.059413 | 65,520.7 | weight_read | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid` | 1.192352 | 78,939.3 | weight_read | 13.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.055419 | 88,366.7 | weight_read | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-expert` | 0.289315 | 61,005.0 | weight_read | 5.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.053236 | 91,203.3 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-expert` | 0.138715 | 65,989.3 | compute | 2.61x |

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


## Derived technology at N6

These are outputs of the graded primitives, not inputs.

| Quantity | Value | Grade |
|---|---:|---|
| SRAM capacity density | 3.009 MB/mm2 | assumed |
| ROM capacity density | 7.295 MB/mm2 | derived |
| ROM read bandwidth density | 282.2 GB/s/mm2 | derived |
| SRAM read bandwidth density | 432.7 GB/s/mm2 | derived |
| Compute density, bf16 | 0.446 Tops/s/mm2 | derived |
| Compute density, fp8 | 0.891 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.261 Tops/s/mm2 | derived |
| Compute density, fp4 | 1.783 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.028 Tops/s/mm2 | derived |
| ROM full-array sweep time | 34.5 us | derived |
| ROM per-token ceiling from that sweep | 29,015 tok/s | derived |
| ROM per-token ceiling before the read derate | 38,686 tok/s | derived |

The ROM full-array sweep time is rom_capacity_density divided by rom_read_bandwidth_density. Both scale with the same published bitcell-area ratio under this derivation, so the sweep time -- and hence the ROM path's hard per-token ceiling -- is the SAME at every node. Process scaling buys a ROM design capacity, not per-token speed. No clock-frequency bonus is credited, which makes this the conservative reading.

## Models and their work

| Model | Context | Params | Checkpoint | Native bits/param | KV read/token | KV/user | W:KV at B=1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 552 B | 307.5 GB | 4.46 | 0.183 GB | 0.893 GB | 71.3 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 3 | 138,675 | 25,205.3 | wafer-pipeline | 4,838.6 | wafer-tensor | 5.21x | 6,393.8 | pipeline | 1,131.8 | tensor | 5.65x | 3.94x | 4.28x | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 184,900 | 58,049.2 | wafer-pipeline | 5,761.8 | wafer-hybrid | 10.07x | 6,923.9 | pipeline | 1,145.8 | tensor | 6.04x | 8.38x | 5.03x | 0.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 6 | 277,350 | 61,632.6 | wafer-pipeline | 5,802.1 | wafer-hybrid | 10.62x | 7,549.8 | pipeline | 842.7 | tensor | 8.96x | 8.16x | 6.89x | 0.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 369,800 | 63,261.8 | wafer-pipeline | 5,820.4 | wafer-hybrid | 10.87x | 7,907.3 | pipeline | 846.5 | tensor | 9.34x | 8.00x | 6.88x | 0.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 12 | 554,700 | 64,672.6 | wafer-pipeline | 5,827.5 | wafer-hybrid | 11.10x | 8,300.2 | pipeline | 850.4 | tensor | 9.76x | 7.79x | 6.85x | 0.88x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.60x to 1.08x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x160 | 130,400 | 11,911.5 | 476,459.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-tensor | 130,508 | 1.00x | tensor | 825.36 | 1,128.2 | 1,128.2 | link_latency | 10.56x | 24.59x | 97.14x | 10.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x75 | 61,125 | 9,381.3 | 9,381.3 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-tensor | 61,124 | 1.00x | tensor | 820.44 | 1,064.7 | 1,064.7 | link_latency | 8.81x | 1.03x | 76.51x | 8.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x160 | 130,400 | 11,911.5 | 476,459.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-tensor | 130,508 | 1.00x | tensor | 925.91 | 995.1 | 1,990.3 | link_latency | 11.97x | 24.59x | 97.14x | 11.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x75 | 61,125 | 7,625.5 | 15,251.0 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-tensor | 61,124 | 1.00x | tensor | 916.08 | 931.7 | 1,863.4 | link_latency | 8.18x | 1.68x | 62.19x | 8.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x160 | 130,400 | 11,911.5 | 476,459.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-tensor | 130,508 | 1.00x | tensor | 1,127.03 | 805.7 | 3,222.7 | link_latency | 14.78x | 24.59x | 97.14x | 14.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x75 | 61,125 | 5,548.6 | 22,194.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-tensor | 61,124 | 1.00x | tensor | 1,107.37 | 746.4 | 2,985.7 | link_latency | 7.43x | 2.45x | 45.25x | 7.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x160 | 130,400 | 11,911.5 | 476,459.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-hybrid | 130,508 | 1.00x | hybrid | 453.52 | 674.7 | 13,494.1 | weight_read | 17.65x | 24.59x | 97.14x | 17.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x75 | 61,125 | 3,592.0 | 28,735.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-hybrid | 61,124 | 1.00x | hybrid | 429.12 | 655.1 | 6,550.7 | weight_read | 5.48x | 3.17x | 29.29x | 5.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x160 | 130,400 | 11,911.5 | 476,459.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-hybrid | 130,508 | 1.00x | hybrid | 453.52 | 674.7 | 13,494.1 | weight_read | 17.65x | 24.59x | 97.14x | 17.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x75 | 61,125 | 2,237.1 | 42,504.5 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-hybrid | 61,124 | 1.00x | hybrid | 435.64 | 566.8 | 9,068.7 | weight_read | 3.95x | 4.68x | 18.24x | 3.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x160 | 130,400 | 11,911.5 | 476,459.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-hybrid | 130,508 | 1.00x | hybrid | 462.49 | 585.6 | 18,738.6 | weight_read | 20.34x | 24.59x | 97.14x | 20.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x75 | 61,125 | 1,344.7 | 43,030.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-hybrid | 61,124 | 1.00x | hybrid | 453.00 | 418.7 | 13,398.6 | weight_read | 3.21x | 3.21x | 10.97x | 3.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 9,989.5 | 689,275.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 505.93 | 544.8 | 34,864.1 | weight_read | 18.34x | 19.77x | 81.47x | 18.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x75 | 61,125 | 678.5 | 43,423.3 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-hybrid | 61,124 | 1.00x | hybrid | 487.74 | 278.3 | 17,808.1 | weight_read | 2.44x | 2.44x | 5.53x | 2.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276 | 224,940 | 4,307.8 | 1,102,797.6 | weight_read | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 622.73 | 258.6 | 66,204.7 | weight_read | 16.66x | 16.66x | 35.13x | 16.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x75 | 61,125 | 171.1 | 43,792.5 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-expert | 61,124 | 1.00x | expert | 1,446.45 | 129.7 | 33,214.6 | weight_read | 1.32x | 1.32x | 2.58x | 1.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1,557.1 | 1,594,518.2 | weight_read | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-expert | 276,710 | 1.00x | expert | 1,342.40 | 205.9 | 210,860.3 | weight_read | 7.56x | 7.56x | 21.74x | 7.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x75 | 61,125 | 42.8 | 43,855.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-expert | 61,124 | 1.00x | expert | 4,098.59 | 83.2 | 85,163.1 | weight_read | 0.51x | 0.51x | 1.78x | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 418.3 | 1,713,187.1 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-expert | 276,710 | 1.00x | expert | 3,682.40 | 116.1 | 475,718.9 | compute | 3.60x | 3.60x | 15.81x | 3.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x75 | 61,125 | 10.7 | 43,871.7 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-expert | 61,124 | 1.00x | expert | 14,707.15 | 28.3 | 115,742.7 | compute | 0.38x | 0.38x | 1.24x | 0.38x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 53 | 43,778 | 122.6 | 1,022.4 | 669.1 | tensor | 816.23 | 83.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 54 | 44,604 | 122.6 | 1,025.3 | 678.0 | tensor | 816.23 | 83.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 56 | 46,256 | 122.6 | 1,031.0 | 695.6 | tensor | 816.23 | 84.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 58 | 47,908 | 122.6 | 1,034.4 | 647.6 | tensor | 817.98 | 84.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 59 | 48,734 | 122.6 | 1,036.9 | 655.6 | tensor | 817.98 | 84.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 74 | 61,124 | 122.6 | 1,064.7 | 655.1 | tensor | 820.44 | 87.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 86 | 71,036 | 122.6 | 1,081.1 | 679.9 | tensor | 821.34 | 88.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 91 | 75,166 | 122.6 | 1,086.3 | 664.4 | tensor | 822.08 | 89.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 102 | 84,252 | 122.6 | 1,096.9 | 679.3 | tensor | 822.71 | 90.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 103 | 85,078 | 122.6 | 1,097.8 | 684.0 | tensor | 822.71 | 90.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 111 | 91,686 | 122.6 | 1,104.0 | 683.1 | tensor | 823.25 | 90.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 112 | 92,512 | 122.6 | 1,104.8 | 687.4 | tensor | 823.25 | 91.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 123 | 101,598 | 122.6 | 1,111.6 | 666.4 | tensor | 824.13 | 91.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 125 | 103,250 | 122.6 | 1,112.9 | 674.0 | tensor | 824.13 | 91.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 136 | 112,336 | 122.6 | 1,118.9 | 684.0 | tensor | 824.49 | 92.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 156 | 128,856 | 122.6 | 1,127.4 | 668.8 | tensor | 825.36 | 93.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 158 | 130,508 | 122.6 | 1,128.2 | 674.7 | tensor | 825.36 | 93.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 161 | 132,986 | 122.6 | 1,129.2 | 659.8 | tensor | 825.59 | 93.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 168 | 138,768 | 122.6 | 1,131.8 | 679.4 | tensor | 825.59 | 93.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 170 | 140,420 | 122.6 | 1,132.3 | 662.3 | tensor | 825.80 | 93.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 177 | 146,202 | 122.6 | 1,134.4 | 659.4 | tensor | 826.00 | 93.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 183 | 151,158 | 122.6 | 1,136.3 | 674.7 | tensor | 826.00 | 93.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 185 | 152,810 | 122.6 | 1,136.7 | 659.1 | tensor | 826.18 | 93.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 204 | 168,504 | 122.6 | 1,141.6 | 665.0 | tensor | 826.49 | 94.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 205 | 169,330 | 122.6 | 1,141.8 | 667.2 | tensor | 826.49 | 94.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 218 | 180,068 | 122.6 | 1,144.5 | 659.4 | tensor | 826.76 | 94.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 224 | 185,024 | 122.6 | 1,145.8 | 671.6 | tensor | 826.76 | 94.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 245 | 202,370 | 122.6 | 1,149.4 | 662.9 | tensor | 827.10 | 95.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 247 | 204,022 | 122.6 | 1,149.8 | 666.5 | tensor | 827.10 | 95.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 248 | 204,848 | 122.6 | 1,150.0 | 668.3 | tensor | 827.10 | 95.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 272 | 224,672 | 122.6 | 1,153.4 | 665.1 | tensor | 827.38 | 95.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 280 | 231,280 | 122.6 | 1,154.4 | 664.0 | tensor | 827.46 | 95.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 326 | 269,276 | 122.6 | 842.2 | 656.0 | tensor | 1,152.67 | 97.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 335 | 276,710 | 122.6 | 842.6 | 657.4 | tensor | 1,152.73 | 97.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 336 | 277,536 | 122.6 | 842.7 | 658.7 | tensor | 1,152.73 | 97.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 354 | 292,404 | 122.6 | 843.4 | 651.4 | tensor | 1,152.89 | 97.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 368 | 303,968 | 122.6 | 844.0 | 658.7 | tensor | 1,152.93 | 97.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 371 | 306,446 | 122.6 | 844.1 | 652.8 | tensor | 1,152.98 | 97.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 373 | 308,098 | 122.6 | 844.2 | 655.2 | tensor | 1,152.98 | 97.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 379 | 313,054 | 122.6 | 844.4 | 653.0 | tensor | 1,153.02 | 97.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 380 | 313,880 | 122.6 | 844.4 | 654.1 | tensor | 1,153.02 | 97.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 392 | 323,792 | 122.6 | 844.8 | 658.7 | tensor | 1,153.07 | 97.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 448 | 370,048 | 122.6 | 846.5 | 658.7 | tensor | 1,153.32 | 97.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 616 | 508,816 | 122.6 | 849.7 | 658.7 | tensor | 1,153.80 | 98.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 672 | 555,072 | 122.6 | 850.4 | 658.7 | tensor | 1,153.90 | 98.1% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x251 | DeepSeek-V4.1-Flash-engram-hbm | 251 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x185 | DeepSeek-V4.1-Flash-engram-hbm | 185 | tensor | rom_package_ucie | rom_board_serdes | 160 | 109.00 us | 917.5 tok/s | 9,174.6 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 47 on rom_board_serdes (traversals 13.2) = 106.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x251 | DeepSeek-V4.1-Flash-engram-hbm | 251 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x250 | DeepSeek-V4.1-Flash-engram-hbm | 250 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x5 | DeepSeek-V4.1-Flash-engram-hbm | 5 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x172 | DeepSeek-V4.1-Flash-engram-hbm | 172 | tensor | nvlink3 | infiniband_hdr | 160 | 825.80 us | 121.1 tok/s | 1,210.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 418.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4.1-Flash-engram-hbm | 4 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.91 us | 581.7 tok/s | 5,817.1 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 17.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hybrid-x221 | DeepSeek-V4.1-Flash-engram-hbm | 221 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | DeepSeek-V4.1-Flash-engram-hbm | 4 | hybrid | on_wafer | rom_wafer_serdes | 83 | 154.31 us | 648.1 tok/s | 6,480.7 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x160 | DeepSeek-V4.1-Flash-engram-hbm | 160 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x92 | DeepSeek-V4.1-Flash-engram-hbm | 92 | tensor | rom_package_ucie | rom_board_serdes | 160 | 73.77 us | 1,355.6 tok/s | 13,556.2 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 23 on rom_board_serdes (traversals 8.8) = 71.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x160 | DeepSeek-V4.1-Flash-engram-hbm | 160 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-pipeline-x158 | DeepSeek-V4.1-Flash-engram-hbm | 158 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7 | DeepSeek-V4.1-Flash-engram-hbm | 7 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-tensor-x75 | DeepSeek-V4.1-Flash-engram-hbm | 75 | tensor | nvlink3 | infiniband_hdr | 160 | 820.44 us | 121.9 tok/s | 1,218.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 413.27 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x7 | DeepSeek-V4.1-Flash-engram-hbm | 7 | tensor | on_wafer | rom_wafer_serdes | 160 | 189.55 us | 527.6 tok/s | 5,275.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 7 on rom_wafer_serdes (traversals 4.4) = 35.55 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x103 | DeepSeek-V4.1-Flash-engram-hbm | 103 | hybrid | nvlink3 | infiniband_hdr | 92 | 436.44 us | 229.1 tok/s | 2,291.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 29.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7 | DeepSeek-V4.1-Flash-engram-hbm | 7 | hybrid | on_wafer | rom_wafer_serdes | 86 | 154.61 us | 646.8 tok/s | 6,467.9 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 6 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.61 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x53-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 53 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x53-tensor | DeepSeek-V4.1-Flash-engram-hbm | 53 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x53-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 53 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x53-expert | DeepSeek-V4.1-Flash-engram-hbm | 53 | expert | nvlink3 | infiniband_hdr | 160 | 567.30 us | 176.3 tok/s | 1,762.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 166.11 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x54-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 54 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x54-tensor | DeepSeek-V4.1-Flash-engram-hbm | 54 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x54-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 54 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x54-expert | DeepSeek-V4.1-Flash-engram-hbm | 54 | expert | nvlink3 | infiniband_hdr | 160 | 567.24 us | 176.3 tok/s | 1,762.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 166.04 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash-engram-hbm | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-expert | DeepSeek-V4.1-Flash-engram-hbm | 56 | expert | nvlink3 | infiniband_hdr | 160 | 566.93 us | 176.4 tok/s | 1,763.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x58-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 58 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x58-tensor | DeepSeek-V4.1-Flash-engram-hbm | 58 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x58-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 58 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x58-expert | DeepSeek-V4.1-Flash-engram-hbm | 58 | expert | nvlink3 | infiniband_hdr | 160 | 566.81 us | 176.4 tok/s | 1,764.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x59-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 59 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x59-tensor | DeepSeek-V4.1-Flash-engram-hbm | 59 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x59-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 59 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x59-expert | DeepSeek-V4.1-Flash-engram-hbm | 59 | expert | nvlink3 | infiniband_hdr | 160 | 566.76 us | 176.4 tok/s | 1,764.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.73 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 74 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-tensor | DeepSeek-V4.1-Flash-engram-hbm | 74 | tensor | nvlink3 | infiniband_hdr | 160 | 820.44 us | 121.9 tok/s | 1,218.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 413.27 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 74 | hybrid | nvlink3 | infiniband_hdr | 89 | 429.12 us | 233.0 tok/s | 2,330.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-expert | DeepSeek-V4.1-Flash-engram-hbm | 74 | expert | nvlink3 | infiniband_hdr | 160 | 565.85 us | 176.7 tok/s | 1,767.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.80 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 86 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-tensor | DeepSeek-V4.1-Flash-engram-hbm | 86 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 86 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-expert | DeepSeek-V4.1-Flash-engram-hbm | 86 | expert | nvlink3 | infiniband_hdr | 160 | 565.40 us | 176.9 tok/s | 1,768.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.72 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x91-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 91 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x91-tensor | DeepSeek-V4.1-Flash-engram-hbm | 91 | tensor | nvlink3 | infiniband_hdr | 160 | 822.08 us | 121.6 tok/s | 1,216.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 414.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x91-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 91 | hybrid | nvlink3 | infiniband_hdr | 91 | 434.00 us | 230.4 tok/s | 2,304.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 26.84 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x91-expert | DeepSeek-V4.1-Flash-engram-hbm | 91 | expert | nvlink3 | infiniband_hdr | 160 | 565.21 us | 176.9 tok/s | 1,769.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.65 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x102-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 102 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x102-tensor | DeepSeek-V4.1-Flash-engram-hbm | 102 | tensor | nvlink3 | infiniband_hdr | 160 | 822.71 us | 121.5 tok/s | 1,215.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 415.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x102-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 102 | hybrid | nvlink3 | infiniband_hdr | 92 | 436.44 us | 229.1 tok/s | 2,291.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 29.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x102-expert | DeepSeek-V4.1-Flash-engram-hbm | 102 | expert | nvlink3 | infiniband_hdr | 160 | 564.92 us | 177.0 tok/s | 1,770.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.60 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.33 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x103-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 103 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x103-tensor | DeepSeek-V4.1-Flash-engram-hbm | 103 | tensor | nvlink3 | infiniband_hdr | 160 | 822.71 us | 121.5 tok/s | 1,215.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 415.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x103-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 103 | hybrid | nvlink3 | infiniband_hdr | 92 | 436.44 us | 229.1 tok/s | 2,291.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 29.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x103-expert | DeepSeek-V4.1-Flash-engram-hbm | 103 | expert | nvlink3 | infiniband_hdr | 160 | 564.91 us | 177.0 tok/s | 1,770.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.60 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.31 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 111 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-tensor | DeepSeek-V4.1-Flash-engram-hbm | 111 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 111 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-expert | DeepSeek-V4.1-Flash-engram-hbm | 111 | expert | nvlink3 | infiniband_hdr | 160 | 564.72 us | 177.1 tok/s | 1,770.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.55 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 112 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor | DeepSeek-V4.1-Flash-engram-hbm | 112 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 112 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-expert | DeepSeek-V4.1-Flash-engram-hbm | 112 | expert | nvlink3 | infiniband_hdr | 160 | 564.67 us | 177.1 tok/s | 1,771.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x123-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 123 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x123-tensor | DeepSeek-V4.1-Flash-engram-hbm | 123 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x123-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 123 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x123-expert | DeepSeek-V4.1-Flash-engram-hbm | 123 | expert | nvlink3 | infiniband_hdr | 160 | 564.48 us | 177.2 tok/s | 1,771.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.00 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x125-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 125 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x125-tensor | DeepSeek-V4.1-Flash-engram-hbm | 125 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x125-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 125 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x125-expert | DeepSeek-V4.1-Flash-engram-hbm | 125 | expert | nvlink3 | infiniband_hdr | 160 | 564.45 us | 177.2 tok/s | 1,771.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.97 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 136 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-tensor | DeepSeek-V4.1-Flash-engram-hbm | 136 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 136 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-expert | DeepSeek-V4.1-Flash-engram-hbm | 136 | expert | nvlink3 | infiniband_hdr | 160 | 564.27 us | 177.2 tok/s | 1,772.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.85 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 156 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-tensor | DeepSeek-V4.1-Flash-engram-hbm | 156 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 156 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x156-expert | DeepSeek-V4.1-Flash-engram-hbm | 156 | expert | nvlink3 | infiniband_hdr | 160 | 564.04 us | 177.3 tok/s | 1,772.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 158 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-tensor | DeepSeek-V4.1-Flash-engram-hbm | 158 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 158 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x158-expert | DeepSeek-V4.1-Flash-engram-hbm | 158 | expert | nvlink3 | infiniband_hdr | 160 | 564.02 us | 177.3 tok/s | 1,773.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x161-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 161 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x161-tensor | DeepSeek-V4.1-Flash-engram-hbm | 161 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x161-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 161 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x161-expert | DeepSeek-V4.1-Flash-engram-hbm | 161 | expert | nvlink3 | infiniband_hdr | 160 | 563.98 us | 177.3 tok/s | 1,773.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.36 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.62 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 168 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-tensor | DeepSeek-V4.1-Flash-engram-hbm | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 168 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-expert | DeepSeek-V4.1-Flash-engram-hbm | 168 | expert | nvlink3 | infiniband_hdr | 160 | 563.91 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x170-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 170 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x170-tensor | DeepSeek-V4.1-Flash-engram-hbm | 170 | tensor | nvlink3 | infiniband_hdr | 160 | 825.80 us | 121.1 tok/s | 1,210.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 418.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x170-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 170 | hybrid | nvlink3 | infiniband_hdr | 101 | 458.40 us | 218.2 tok/s | 2,181.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 51.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x170-expert | DeepSeek-V4.1-Flash-engram-hbm | 170 | expert | nvlink3 | infiniband_hdr | 160 | 563.90 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 177 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-tensor | DeepSeek-V4.1-Flash-engram-hbm | 177 | tensor | nvlink3 | infiniband_hdr | 160 | 826.00 us | 121.1 tok/s | 1,210.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 418.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 177 | hybrid | nvlink3 | infiniband_hdr | 102 | 460.84 us | 217.0 tok/s | 2,170.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 53.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-expert | DeepSeek-V4.1-Flash-engram-hbm | 177 | expert | nvlink3 | infiniband_hdr | 160 | 563.84 us | 177.4 tok/s | 1,773.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.33 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x183-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 183 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x183-tensor | DeepSeek-V4.1-Flash-engram-hbm | 183 | tensor | nvlink3 | infiniband_hdr | 160 | 826.00 us | 121.1 tok/s | 1,210.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 418.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x183-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 183 | hybrid | nvlink3 | infiniband_hdr | 102 | 460.84 us | 217.0 tok/s | 2,170.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 53.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x183-expert | DeepSeek-V4.1-Flash-engram-hbm | 183 | expert | nvlink3 | infiniband_hdr | 160 | 563.80 us | 177.4 tok/s | 1,773.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.33 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x185-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 185 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x185-tensor | DeepSeek-V4.1-Flash-engram-hbm | 185 | tensor | nvlink3 | infiniband_hdr | 160 | 826.18 us | 121.0 tok/s | 1,210.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 419.01 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x185-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 185 | hybrid | nvlink3 | infiniband_hdr | 103 | 463.28 us | 215.9 tok/s | 2,158.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 56.11 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x185-expert | DeepSeek-V4.1-Flash-engram-hbm | 185 | expert | nvlink3 | infiniband_hdr | 160 | 563.77 us | 177.4 tok/s | 1,773.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.31 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.46 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 204 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-tensor | DeepSeek-V4.1-Flash-engram-hbm | 204 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 204 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-expert | DeepSeek-V4.1-Flash-engram-hbm | 204 | expert | nvlink3 | infiniband_hdr | 160 | 563.65 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x205-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 205 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x205-tensor | DeepSeek-V4.1-Flash-engram-hbm | 205 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x205-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 205 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x205-expert | DeepSeek-V4.1-Flash-engram-hbm | 205 | expert | nvlink3 | infiniband_hdr | 160 | 563.65 us | 177.4 tok/s | 1,774.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x218-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 218 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x218-tensor | DeepSeek-V4.1-Flash-engram-hbm | 218 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x218-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 218 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x218-expert | DeepSeek-V4.1-Flash-engram-hbm | 218 | expert | nvlink3 | infiniband_hdr | 160 | 563.57 us | 177.4 tok/s | 1,774.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.27 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.30 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash-engram-hbm | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-expert | DeepSeek-V4.1-Flash-engram-hbm | 224 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x245-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 245 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x245-tensor | DeepSeek-V4.1-Flash-engram-hbm | 245 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x245-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 245 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x245-expert | DeepSeek-V4.1-Flash-engram-hbm | 245 | expert | nvlink3 | infiniband_hdr | 160 | 563.44 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x247-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 247 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x247-tensor | DeepSeek-V4.1-Flash-engram-hbm | 247 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x247-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 247 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x247-expert | DeepSeek-V4.1-Flash-engram-hbm | 247 | expert | nvlink3 | infiniband_hdr | 160 | 563.43 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x248-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 248 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x248-tensor | DeepSeek-V4.1-Flash-engram-hbm | 248 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x248-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 248 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x248-expert | DeepSeek-V4.1-Flash-engram-hbm | 248 | expert | nvlink3 | infiniband_hdr | 160 | 563.42 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.23 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 272 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-tensor | DeepSeek-V4.1-Flash-engram-hbm | 272 | tensor | nvlink3 | infiniband_hdr | 160 | 827.38 us | 120.9 tok/s | 1,208.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 420.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 272 | hybrid | nvlink3 | infiniband_hdr | 113 | 487.67 us | 205.1 tok/s | 2,050.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 80.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-expert | DeepSeek-V4.1-Flash-engram-hbm | 272 | expert | nvlink3 | infiniband_hdr | 160 | 563.33 us | 177.5 tok/s | 1,775.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.21 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 280 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-tensor | DeepSeek-V4.1-Flash-engram-hbm | 280 | tensor | nvlink3 | infiniband_hdr | 160 | 827.46 us | 120.9 tok/s | 1,208.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 420.30 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 280 | hybrid | nvlink3 | infiniband_hdr | 114 | 490.11 us | 204.0 tok/s | 2,040.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-expert | DeepSeek-V4.1-Flash-engram-hbm | 280 | expert | nvlink3 | infiniband_hdr | 160 | 563.31 us | 177.5 tok/s | 1,775.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.20 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.10 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x326-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 326 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x326-tensor | DeepSeek-V4.1-Flash-engram-hbm | 326 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.67 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 41 on infiniband_hdr (traversals 4.0) = 745.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x326-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 326 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x326-expert | DeepSeek-V4.1-Flash-engram-hbm | 326 | expert | nvlink3 | infiniband_hdr | 160 | 563.18 us | 177.6 tok/s | 1,775.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.18 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.00 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 335 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-tensor | DeepSeek-V4.1-Flash-engram-hbm | 335 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 335 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-expert | DeepSeek-V4.1-Flash-engram-hbm | 335 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 336 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-tensor | DeepSeek-V4.1-Flash-engram-hbm | 336 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 336 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-expert | DeepSeek-V4.1-Flash-engram-hbm | 336 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x354-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 354 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x354-tensor | DeepSeek-V4.1-Flash-engram-hbm | 354 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.89 us | 86.7 tok/s | 867.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 745.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x354-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 354 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x354-expert | DeepSeek-V4.1-Flash-engram-hbm | 354 | expert | nvlink3 | infiniband_hdr | 160 | 563.12 us | 177.6 tok/s | 1,775.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x368-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 368 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x368-tensor | DeepSeek-V4.1-Flash-engram-hbm | 368 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.93 us | 86.7 tok/s | 867.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 745.77 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x368-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 368 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x368-expert | DeepSeek-V4.1-Flash-engram-hbm | 368 | expert | nvlink3 | infiniband_hdr | 160 | 563.09 us | 177.6 tok/s | 1,775.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x371-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 371 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x371-tensor | DeepSeek-V4.1-Flash-engram-hbm | 371 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.98 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 745.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x371-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 371 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x371-expert | DeepSeek-V4.1-Flash-engram-hbm | 371 | expert | nvlink3 | infiniband_hdr | 160 | 563.09 us | 177.6 tok/s | 1,775.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x373-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 373 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x373-tensor | DeepSeek-V4.1-Flash-engram-hbm | 373 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.98 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 745.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x373-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 373 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x373-expert | DeepSeek-V4.1-Flash-engram-hbm | 373 | expert | nvlink3 | infiniband_hdr | 160 | 563.08 us | 177.6 tok/s | 1,775.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x379-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 379 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x379-tensor | DeepSeek-V4.1-Flash-engram-hbm | 379 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.02 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 745.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x379-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 379 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x379-expert | DeepSeek-V4.1-Flash-engram-hbm | 379 | expert | nvlink3 | infiniband_hdr | 160 | 563.07 us | 177.6 tok/s | 1,776.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.15 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 380 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-tensor | DeepSeek-V4.1-Flash-engram-hbm | 380 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.02 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 745.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 380 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-expert | DeepSeek-V4.1-Flash-engram-hbm | 380 | expert | nvlink3 | infiniband_hdr | 160 | 563.07 us | 177.6 tok/s | 1,776.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.15 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 392 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-tensor | DeepSeek-V4.1-Flash-engram-hbm | 392 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.07 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 745.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 392 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-expert | DeepSeek-V4.1-Flash-engram-hbm | 392 | expert | nvlink3 | infiniband_hdr | 160 | 563.05 us | 177.6 tok/s | 1,776.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.15 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 448 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-tensor | DeepSeek-V4.1-Flash-engram-hbm | 448 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.32 us | 86.7 tok/s | 867.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 746.15 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 448 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-expert | DeepSeek-V4.1-Flash-engram-hbm | 448 | expert | nvlink3 | infiniband_hdr | 160 | 562.97 us | 177.6 tok/s | 1,776.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.13 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.84 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x616-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 616 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x616-tensor | DeepSeek-V4.1-Flash-engram-hbm | 616 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.80 us | 86.7 tok/s | 866.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 77 on infiniband_hdr (traversals 4.0) = 746.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x616-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 616 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x616-expert | DeepSeek-V4.1-Flash-engram-hbm | 616 | expert | nvlink3 | infiniband_hdr | 160 | 562.81 us | 177.7 tok/s | 1,776.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.09 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 672 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-tensor | DeepSeek-V4.1-Flash-engram-hbm | 672 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.90 us | 86.7 tok/s | 866.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 746.73 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 672 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-expert | DeepSeek-V4.1-Flash-engram-hbm | 672 | expert | nvlink3 | infiniband_hdr | 160 | 562.78 us | 177.7 tok/s | 1,776.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.09 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.69 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash-engram-hbm | 1 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 11,701.3 | 0.091 | 11,701.3 (128,770) | 5,761.8 (184,900) | 0.49x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 11,701.3 | 0.091 | 11,701.3 (128,770) | 5,476.8 (323,575) | 0.47x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 11,701.3 | 0.091 | 11,701.3 (128,770) | 5,476.8 (323,575) | 0.47x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 11,701.3 | 0.091 | 11,701.3 (128,770) | 5,401.0 (323,575) | 0.46x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 11,701.3 | 0.091 | 11,701.3 (128,770) | 5,288.8 (554,700) | 0.45x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 11,701.3 | 0.091 | 11,701.3 (128,770) | 4,694.6 (554,700) | 0.40x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 9,989.5 | 0.044 | 9,989.5 (224,940) | 3,833.4 (554,700) | 0.38x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276 | 224,940 | 4,307.8 | 0.019 | 4,307.8 (224,940) | 1,824.8 (554,700) | 0.42x | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1,557.1 | 0.006 | 1,557.1 (277,100) | 647.4 (554,700) | 0.42x | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 418.3 | 0.002 | 418.3 (277,100) | 163.0 (554,700) | 0.39x | compute |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. Both machines hold the requested weights. They are different floorplans, not one floorplan with two arithmetics.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 481.6 mm2 | 256.8 mm2 |
| weight capacity | 3.51 GB (100.0%) | 3.51 GB (100.0%) |
| capacity-feasible | yes | yes |
| compute block | 186.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 264.8 mm2 |
| sustained fp8 compute roof | 9.154e+13 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 4.577e+13 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 1.019e+14 |
| **can the compute block be fed?** | **2.23x** | there is nothing to feed |
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

The ROM-plus-MAC machine is not bandwidth-starved at this point:
its array supplies 2.23x the bytes its MAC
roof demands, so the fp8 compute block can be fully fed and the
remaining array bandwidth is unused.

## Sizing one expert region

The per-region machine's cost is not arithmetic; it is a
pre-compute block and an activation distribution network per
region. The block is small against the array it serves. The
distribution network is the real cost and this model does not
price it.

| Model | Experts | Routed bytes/expert | One region | Pre-compute/region | All regions | All pre-compute | Whole checkpoint |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 384 | 752.0 MB | 164.9 mm2 | 29.69 mm2 (18.0%) | 63,336 mm2 | 11,400 mm2 | 67,448 mm2 = 82.8 reticles |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | sram | 607,862.2 | 26,087.6 | 26,087.6 | 23.30x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | sram | 607,862.2 | 26,087.6 | 26,087.6 | 23.30x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | sram | 607,862.2 | 26,087.6 | 31,718.0 | 23.30x | 1.22x | weight_read | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | sram | 607,862.2 | 26,087.6 | 51,762.4 | 23.30x | 1.98x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | sram | 607,862.2 | 26,087.6 | 84,445.9 | 23.30x | 3.24x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | sram | 607,862.2 | 26,087.6 | 126,308.4 | 23.30x | 4.84x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | sram | 607,862.2 | 26,087.6 | 176,034.2 | 23.30x | 6.75x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | sram | 1,102,797.6 | 26,087.6 | 270,959.4 | 42.27x | 10.39x | weight_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | sram | 1,594,518.2 | 26,104.0 | 367,194.2 | 61.08x | 14.07x | weight_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | sram | 1,713,187.1 | 26,110.7 | 384,207.5 | 65.61x | 14.71x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | rom | 980,215.5 | 312,341.1 | 312,341.1 | 3.14x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | rom | 980,215.5 | 312,341.1 | 312,341.1 | 3.14x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | rom | 980,215.5 | 312,341.1 | 312,341.1 | 3.14x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | rom | 980,215.5 | 312,341.1 | 312,341.1 | 3.14x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | rom | 980,215.5 | 312,341.1 | 312,341.1 | 3.14x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | rom | 980,215.5 | 312,341.1 | 312,341.1 | 3.14x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | rom | 980,215.5 | 312,341.1 | 312,341.1 | 3.14x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | rom | 980,215.5 | 312,341.1 | 312,341.1 | 3.14x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | rom | 1,001,925.2 | 314,593.9 | 388,249.5 | 3.18x | 1.23x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | rom | 1,010,266.8 | 315,679.7 | 389,904.5 | 3.20x | 1.24x | compute | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 980,215.5 | 3.537 | compute | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 980,215.5 | 3.537 | compute | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 980,215.5 | 3.537 | compute | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x54-perregion | 44,010 | 1.00 | 1.43 | 31,718.0 | 0.721 | link_latency | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 980,215.5 | 3.537 | compute | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x54-perregion | 44,010 | 1.00 | 1.99 | 51,762.4 | 1.176 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 980,215.5 | 3.537 | compute | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x54-perregion | 44,010 | 1.00 | 2.54 | 84,445.9 | 1.919 | weight_read | 0.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 980,215.5 | 3.537 | compute | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x54-perregion | 44,010 | 1.00 | 3.49 | 126,308.4 | 2.870 | weight_read | 0.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 980,215.5 | 3.537 | compute | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x54-perregion | 44,010 | 1.00 | 4.92 | 176,034.2 | 4.000 | weight_read | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276 | 224,940 | 1.00 | 1.00 | 1,102,797.6 | 4.903 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 980,215.5 | 3.537 | compute | 0.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,087.6 | 0.081 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x7-perregion | 323,575 | 1.00 | 10.96 | 270,959.4 | 0.837 | kv_read | 0.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 312,341.1 | 0.965 | weight_read | 0.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 1,594,518.2 | 5.754 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 1,001,925.2 | 3.616 | compute | 0.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x54-perstream | 44,010 | 1.00 | 18.96 | 26,104.0 | 0.593 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 2.57 | 314,593.9 | 0.972 | weight_read | 0.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 7.78 | 367,194.2 | 1.135 | kv_read | 0.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.18 | 388,249.5 | 1.200 | kv_read | 0.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 1,713,187.1 | 6.183 | compute | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 1,010,266.8 | 3.646 | compute | 0.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 10.29 | 26,110.7 | 0.081 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 10.29 | 315,679.7 | 0.976 | weight_read | 0.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 19.16 | 384,207.5 | 1.187 | kv_read | 0.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 2.15 | 389,904.5 | 1.205 | kv_read | 0.23x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 163 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 163 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 54 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 54 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 54 | 1.19 | 1.001 | 1.015 | 1.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 54 | 4.74 | 1.030 | 1.564 | 1.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 54 | 18.96 | 1.148 | 2.764 | 2.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 54 | 75.85 | 1.700 | 5.388 | 3.17x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 53 | 5.72 | 4.83 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 53 | 10.75 | 6.87 | 1.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 53 | 19.09 | 9.66 | 1.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 53 | 30.70 | 13.08 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 53 | 42.61 | 16.98 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 53 | 50.07 | 20.91 | 2.39x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 53 | 52.49 | 24.29 | 2.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 53 | 52.96 | 27.44 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 53 | 52.96 | 27.57 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 54 | 5.73 | 4.85 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 54 | 10.77 | 6.91 | 1.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 54 | 19.16 | 9.71 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 54 | 30.91 | 13.18 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 54 | 43.08 | 17.13 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 54 | 50.85 | 21.12 | 2.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 54 | 53.43 | 24.56 | 2.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 54 | 53.95 | 27.77 | 1.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 54 | 53.96 | 27.90 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 59 | 10.87 | 7.07 | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 59 | 19.48 | 9.96 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 59 | 31.87 | 13.62 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 59 | 45.33 | 17.83 | 2.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 59 | 54.61 | 22.12 | 2.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 59 | 58.09 | 25.86 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 59 | 58.91 | 29.37 | 2.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 59 | 58.92 | 29.52 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 59 | 58.92 | 29.52 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 74 | 5.80 | 5.09 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 74 | 11.07 | 7.49 | 1.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 74 | 20.21 | 10.59 | 1.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 74 | 34.13 | 14.78 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 74 | 50.89 | 19.67 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 74 | 64.65 | 24.79 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 74 | 71.32 | 29.36 | 2.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 74 | 73.56 | 33.74 | 2.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 74 | 73.60 | 33.92 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 74 | 73.60 | 33.92 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 86 | 11.18 | 7.77 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 86 | 20.62 | 10.99 | 1.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 86 | 35.46 | 15.57 | 2.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 86 | 54.37 | 20.93 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 86 | 71.47 | 26.65 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 86 | 81.04 | 31.83 | 2.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 86 | 84.96 | 36.86 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 86 | 85.04 | 37.07 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 86 | 85.04 | 37.07 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 91 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 91 | 11.22 | 7.88 | 1.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 91 | 20.77 | 11.14 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 91 | 35.93 | 15.88 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 91 | 55.63 | 21.42 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 91 | 74.03 | 27.36 | 2.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 91 | 84.85 | 32.79 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 91 | 89.59 | 38.08 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 91 | 89.69 | 38.30 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 91 | 89.69 | 38.30 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 102 | 5.85 | 5.30 | 1.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 102 | 11.29 | 8.10 | 1.39x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 102 | 21.04 | 11.44 | 1.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 102 | 36.82 | 16.50 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 102 | 58.08 | 22.40 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 102 | 79.19 | 28.83 | 2.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 102 | 92.77 | 34.76 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 102 | 99.52 | 40.62 | 2.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 102 | 99.68 | 40.86 | 2.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 102 | 99.68 | 40.86 | 2.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 103 | 11.30 | 8.12 | 1.39x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 103 | 21.06 | 11.47 | 1.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 103 | 36.89 | 16.56 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 103 | 58.29 | 22.49 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 103 | 79.62 | 28.95 | 2.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 103 | 93.46 | 34.93 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 103 | 100.40 | 40.84 | 2.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 103 | 100.57 | 41.08 | 2.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 103 | 100.57 | 41.08 | 2.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 111 | 11.34 | 8.26 | 1.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 111 | 21.22 | 11.67 | 1.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 111 | 37.44 | 16.97 | 2.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 111 | 59.81 | 23.14 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 111 | 82.95 | 29.94 | 2.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 111 | 98.78 | 36.26 | 2.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 111 | 107.35 | 42.56 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 123 | 5.88 | 5.40 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 123 | 11.39 | 8.46 | 1.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 123 | 21.42 | 11.95 | 1.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 123 | 38.13 | 17.53 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 123 | 61.81 | 24.02 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 123 | 87.44 | 31.31 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 123 | 106.20 | 38.13 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 123 | 117.34 | 44.98 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 123 | 117.65 | 45.27 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 123 | 117.65 | 45.27 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 125 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 125 | 11.40 | 8.49 | 1.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 125 | 21.45 | 11.99 | 1.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 125 | 38.23 | 17.62 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 125 | 62.11 | 24.16 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 125 | 88.13 | 31.52 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 125 | 107.37 | 38.43 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 125 | 118.96 | 45.37 | 2.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 136 | 11.44 | 8.65 | 1.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 136 | 21.61 | 12.23 | 1.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 136 | 38.76 | 18.08 | 2.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 136 | 63.66 | 24.88 | 2.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 136 | 91.71 | 32.65 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 136 | 113.51 | 40.01 | 2.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 136 | 127.59 | 47.43 | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 136 | 128.01 | 47.75 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 136 | 128.01 | 47.75 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 156 | 11.50 | 8.90 | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 156 | 21.83 | 12.63 | 1.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 156 | 39.54 | 18.79 | 2.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 156 | 66.00 | 26.05 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 156 | 97.31 | 34.51 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 156 | 123.48 | 42.62 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 156 | 142.21 | 50.89 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 156 | 142.80 | 51.24 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 156 | 142.80 | 51.24 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 158 | 5.91 | 5.52 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 158 | 11.50 | 8.92 | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 158 | 21.85 | 12.66 | 1.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 158 | 39.61 | 18.86 | 2.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 158 | 66.21 | 26.16 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 158 | 97.81 | 34.69 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 158 | 124.41 | 42.86 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 158 | 143.59 | 51.22 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 158 | 144.20 | 51.57 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 158 | 144.20 | 51.57 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 161 | 5.91 | 5.53 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 161 | 11.51 | 8.96 | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 161 | 21.88 | 12.72 | 1.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 161 | 39.71 | 18.95 | 2.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 161 | 66.51 | 26.32 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 161 | 98.55 | 34.95 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 161 | 125.76 | 43.23 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 161 | 145.65 | 51.70 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 161 | 146.28 | 52.06 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 161 | 146.28 | 52.06 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 170 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 170 | 11.53 | 9.05 | 1.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 170 | 21.96 | 12.88 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 170 | 39.99 | 19.23 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 170 | 67.36 | 26.78 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 170 | 100.66 | 35.70 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 170 | 129.67 | 44.29 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 170 | 151.63 | 53.12 | 2.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 170 | 152.36 | 53.50 | 2.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 170 | 152.36 | 53.50 | 2.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 177 | 5.92 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 177 | 11.55 | 9.13 | 1.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 177 | 22.02 | 13.01 | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 177 | 40.19 | 19.42 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 177 | 67.98 | 27.13 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 177 | 102.19 | 36.27 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 177 | 132.54 | 45.08 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 177 | 156.11 | 54.18 | 2.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 177 | 156.90 | 54.57 | 2.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 177 | 156.90 | 54.57 | 2.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 183 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 183 | 11.56 | 9.18 | 1.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 183 | 22.06 | 13.11 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 183 | 40.35 | 19.58 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 183 | 68.47 | 27.42 | 2.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 183 | 103.44 | 36.74 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 183 | 134.90 | 45.74 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 183 | 159.83 | 55.07 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 183 | 160.68 | 55.47 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 183 | 160.68 | 55.47 | 2.90x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 204 | 11.59 | 9.37 | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 204 | 22.20 | 13.45 | 1.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 204 | 40.84 | 20.08 | 2.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 204 | 70.00 | 28.39 | 2.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 204 | 107.35 | 38.32 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 204 | 142.45 | 47.95 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 204 | 172.04 | 58.00 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 204 | 173.09 | 58.43 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 204 | 173.09 | 58.43 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 205 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 205 | 11.59 | 9.38 | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 205 | 22.20 | 13.47 | 1.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 205 | 40.86 | 20.11 | 2.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 205 | 70.07 | 28.44 | 2.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 205 | 107.52 | 38.39 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 205 | 142.78 | 48.05 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 205 | 172.59 | 58.13 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 205 | 173.65 | 58.57 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 205 | 173.65 | 58.57 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 218 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 218 | 11.61 | 9.48 | 1.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 218 | 22.28 | 13.67 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 218 | 41.11 | 20.38 | 2.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 218 | 70.88 | 29.00 | 2.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 218 | 109.62 | 39.29 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 218 | 146.95 | 49.31 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 218 | 179.51 | 59.83 | 3.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 218 | 180.70 | 60.29 | 3.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 218 | 180.70 | 60.29 | 3.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 245 | 11.64 | 9.67 | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 245 | 22.40 | 14.06 | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 245 | 41.57 | 20.88 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 245 | 72.32 | 30.12 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 245 | 113.43 | 41.03 | 2.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 245 | 154.63 | 51.73 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 245 | 192.62 | 63.12 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 245 | 194.06 | 63.62 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 245 | 194.06 | 63.62 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 247 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 247 | 11.65 | 9.68 | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 247 | 22.41 | 14.09 | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 247 | 41.59 | 20.91 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 247 | 72.42 | 30.20 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 247 | 113.68 | 41.15 | 2.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 247 | 155.15 | 51.90 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 247 | 193.52 | 63.36 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 247 | 194.98 | 63.86 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 247 | 194.98 | 63.86 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 248 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 248 | 11.65 | 9.69 | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 248 | 22.41 | 14.10 | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 248 | 41.61 | 20.93 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 248 | 72.46 | 30.24 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 248 | 113.81 | 41.21 | 2.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 248 | 155.41 | 51.98 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 248 | 193.98 | 63.47 | 3.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 248 | 195.44 | 63.97 | 3.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 248 | 195.44 | 63.97 | 3.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 272 | 11.67 | 9.83 | 1.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 272 | 22.50 | 14.42 | 1.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 272 | 41.93 | 21.30 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 272 | 73.50 | 31.15 | 2.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 272 | 116.61 | 42.56 | 2.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 272 | 161.21 | 53.89 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 272 | 204.20 | 66.11 | 3.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 272 | 205.88 | 66.65 | 3.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 272 | 205.88 | 66.65 | 3.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 280 | 11.68 | 9.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 280 | 22.53 | 14.53 | 1.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 280 | 42.03 | 21.42 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 280 | 73.81 | 31.44 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 280 | 117.46 | 42.98 | 2.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 280 | 162.98 | 54.48 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 280 | 207.38 | 66.94 | 3.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 326 | 5.95 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 326 | 11.71 | 10.10 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 326 | 22.65 | 15.07 | 1.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 326 | 42.49 | 22.03 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 326 | 75.33 | 32.97 | 2.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 326 | 121.64 | 45.11 | 2.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 326 | 171.88 | 57.65 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 326 | 223.68 | 71.40 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 326 | 225.80 | 72.00 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 326 | 225.80 | 72.00 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 335 | 11.71 | 10.13 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 335 | 22.67 | 15.17 | 1.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 335 | 42.57 | 22.14 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 335 | 75.58 | 33.24 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 335 | 122.34 | 45.48 | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 335 | 173.40 | 58.23 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 335 | 226.52 | 72.22 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 336 | 11.71 | 10.14 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 336 | 22.68 | 15.18 | 1.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 336 | 42.57 | 22.15 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 336 | 75.61 | 33.27 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 336 | 122.42 | 45.52 | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 336 | 173.56 | 58.30 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 336 | 226.83 | 72.31 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 354 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 354 | 11.72 | 10.21 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 354 | 22.71 | 15.37 | 1.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 354 | 42.71 | 22.36 | 1.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 354 | 76.08 | 33.79 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 354 | 123.72 | 46.23 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 354 | 176.41 | 59.43 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 354 | 232.21 | 73.90 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 354 | 234.54 | 74.52 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 354 | 234.54 | 74.52 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 368 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 368 | 11.73 | 10.26 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 368 | 22.74 | 15.52 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 368 | 42.81 | 22.51 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 368 | 76.41 | 34.18 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 368 | 124.66 | 46.76 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 368 | 178.47 | 60.29 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 368 | 236.14 | 75.09 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 368 | 238.56 | 75.73 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 368 | 238.56 | 75.73 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 371 | 11.73 | 10.27 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 371 | 22.75 | 15.55 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 371 | 42.84 | 22.55 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 371 | 76.48 | 34.25 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 371 | 124.86 | 46.87 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 371 | 178.89 | 60.47 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 371 | 236.96 | 75.34 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 371 | 239.40 | 75.98 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 371 | 239.40 | 75.98 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 373 | 11.73 | 10.27 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 373 | 22.75 | 15.57 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 373 | 42.85 | 22.57 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 373 | 76.52 | 34.31 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 373 | 124.98 | 46.94 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 373 | 179.17 | 60.59 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 373 | 237.50 | 75.51 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 373 | 239.95 | 76.15 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 373 | 239.95 | 76.15 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 379 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 379 | 11.74 | 10.30 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 379 | 22.76 | 15.62 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 379 | 42.89 | 22.64 | 1.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 379 | 76.66 | 34.46 | 2.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 379 | 125.36 | 47.15 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 379 | 180.00 | 60.95 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 379 | 239.09 | 76.01 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 379 | 241.59 | 76.65 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 379 | 241.59 | 76.65 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 380 | 11.74 | 10.30 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 380 | 22.76 | 15.63 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 380 | 42.90 | 22.65 | 1.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 380 | 76.68 | 34.49 | 2.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 380 | 125.42 | 47.19 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 380 | 180.14 | 61.01 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 380 | 239.35 | 76.09 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 380 | 241.85 | 76.74 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 380 | 241.85 | 76.74 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 392 | 11.74 | 10.34 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 392 | 22.78 | 15.75 | 1.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 392 | 42.97 | 22.77 | 1.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 392 | 76.93 | 34.79 | 2.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 392 | 126.14 | 47.61 | 2.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 392 | 181.73 | 61.71 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 392 | 242.42 | 77.06 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 392 | 245.00 | 77.72 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 392 | 245.00 | 77.72 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 448 | 11.76 | 10.50 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 448 | 22.87 | 16.25 | 1.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 448 | 43.27 | 23.34 | 1.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 448 | 77.94 | 36.03 | 2.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 448 | 129.03 | 49.47 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 448 | 188.21 | 64.80 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 448 | 255.15 | 81.21 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 616 | 5.98 | 5.87 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 616 | 11.80 | 10.83 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 616 | 23.02 | 17.42 | 1.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 616 | 43.85 | 24.87 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 616 | 79.92 | 38.58 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 616 | 134.80 | 54.41 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 616 | 201.50 | 71.91 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 616 | 282.24 | 90.95 | 3.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 616 | 285.91 | 91.83 | 3.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 616 | 285.91 | 91.83 | 3.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 672 | 11.81 | 10.91 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 672 | 23.06 | 17.73 | 1.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 672 | 43.98 | 25.33 | 1.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 672 | 80.37 | 39.17 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 672 | 136.13 | 55.89 | 2.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 672 | 204.63 | 73.69 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 672 | 288.80 | 93.78 | 3.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 672 | 292.67 | 94.67 | 3.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 672 | 292.67 | 94.67 | 3.09x |

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
| gpu | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 1.2% |
| rom | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 12.0% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | sram | interleaved | 128 B | 1.85x |
| DeepSeek-V4.1-Flash-engram-hbm | hbm | interleaved | 32 B | 1.39x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 170 | 0.44% | 2.62 | 3.52 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 163 | 0.44% | 2.50 | 3.52 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 3 | 0.41% | 2.48 | 3.52 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 3 | 0.41% | 2.48 | 3.52 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 581.2 | 43,590.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 581.2 | 43,590.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 581.2 | 43,590.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 581.2 | 43,590.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 581.2 | 43,590.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 581.2 | 43,590.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 581.2 | 43,590.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 5.23% | 23.6 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 171.1 | 43,792.5 |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 19.35% | 64.4 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 42.8 | 43,855.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 57.69% | 175.1 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 10.7 | 43,871.7 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 44 |
| gpu | infeasible | 13 |
| gpu | link_latency | 447 |
| gpu | weight_read | 1296 |
| rom | compute | 928 |
| rom | infeasible | 2400 |
| rom | kv_read | 137 |
| rom | link_latency | 1138 |
| rom | weight_read | 557 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 13 |
| rom | CAPACITY | 2400 |

## Mechanical consistency audit

**FAIL** over 142,605 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x172', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x185', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x207', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x221', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x248', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x250', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x251', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x330', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x172', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x185', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x207', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x221', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x248', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x250', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x251', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x330', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x172', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x185', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x207', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x221', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x248', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x250', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x251', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x330', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x172', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x185', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x207', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x221', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x248', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x250', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x251', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x330', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x5', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4.1-Flash-engram-hbm', 1)

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

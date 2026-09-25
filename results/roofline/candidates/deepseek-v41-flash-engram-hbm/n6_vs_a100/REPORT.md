# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash-engram-hbm

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash-engram-hbm at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 28x (ROM-N6-native-SRAMKV-wafer-pipeline-x3-perstream, 171 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 113 devices. On the GPU side the correction reaches 9x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 36 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-hbm takes 75 x 815 mm2 (61,125 mm2, array, KV in HBM) at 3,611 tok/s per user and 59 tok/s per 1,000 mm2, holding 28,761 sessions, against 74 copies of one unified HBM die at the same silicon: 9.9x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-hbm on 277,350 mm2 of ROM silicon at 4,341 tok/s per user against 277,536 mm2 of a100_sxm_80gb-x336-hybrid at 358 tok/s: **12.1x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 131,052. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on DeepSeek-V4.1-Flash-engram-hbm at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 1,161 us of link latency per token; but the model has 40 layers, so at most 40 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 1,054 us. The iso-area per-user ratio at that point falls from 12.5x to 12.1x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 3.08x to it.** At 92,450 mm2 on DeepSeek-V4.1-Flash-engram-hbm the pipeline-only GPU delivers 120.59 tok/s and the same silicon running hybrid delivers 371 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.01x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `link_latency`) to 11.68x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `weight_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-hbm engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 333 to 24,072 tok/s, and its rate with every slot occupied from 23,670 to 24,072. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 71 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 171.9 us and cap it at 5,818 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 3 of 10 operating points and an array 7; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 106 of 4543 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 73.7x of aggregate throughput (DeepSeek-V4.1-Flash-engram-hbm). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 16.44x, on DeepSeek-V4.1-Flash-engram-hbm at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4.1-Flash-engram-hbm at 200,000 tokens

**Recommended: `ROM-N6-native-HBMKV-array-hw-hybrid-x75`** -- 75 x 815 mm2 reticle dies, 61,125 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **3,610.5 tok/s per user** (0.28 ms/token), binding on `layer_fixed_latency`
- **59.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 18,053 tok/s aggregate with every slot full, over 28,761 resident sessions (fill limited by `pipeline_slots`)
- 4,842 W at 0.079 W/mm2, 1,292.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 74 copies of one unified HBM die -- `a100_sxm_80gb-x74-hybrid`, 61,124 mm2, area ratio 1.0000 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 61,125 | 61,124 | 1.0000 |
| user tok/s | 3,610.5 | 363.6 | 9.93x |
| aggregate tok/s | 18,053 | 3,636 | 2.02x |
| resident sessions | 28,761 | 26,660 | -- |
| J/token | 1.2920 | 30.7606 | 23.8x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 28,761 sessions against one that holds 26,660 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 375.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x113` | 92,095 | 4,155.7 | 45.1 | 43,902 | 11.23x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 4,344.8 | 23.5 | 1 | 11.94x |
| smallest feasible machine | `ROM-N6-native-HBMKV-array-hw-tensor-x71` | 57,865 | 2,571.0 | 44.4 | 27,167 | 6.94x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | 61,125 | 3,610.5 | 59.1 | 28,761 | 9.93x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | 61,125 | 3,610.5 | 59.1 | -- | 59.1 | ACCEPT |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 4,021.3 | 57.4 | 45.8 | 59.1 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 70,905 | 4,031.7 | 56.9 | 43.1 | 59.1 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x102-romfill` | 83,130 | 4,093.7 | 49.2 | 22.0 | 59.1 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x103` | 83,945 | 4,096.9 | 48.8 | 21.3 | 59.1 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x104` | 84,760 | 4,099.8 | 48.4 | 20.7 | 59.1 | stop |
| `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,314.9 | 46.7 | 22.5 | 59.1 | stop |
| `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 4,315.4 | 31.1 | 9.1 | 59.1 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 4,344.8 | 23.5 | 5.9 | 59.1 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x75` **<-- recommended** | 61,125 | 75 | 3,610.5 | 18,053 | 59.1 | 28,761 | `layer_fixed_latency` | 4,842 | 1,292.0 | `a100_sxm_80gb-x74-hybrid` | 9.93x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 86 | 4,021.3 | 24,128 | 57.4 | 33,144 | `layer_fixed_latency` | 6,371 | 1,522.8 | `a100_sxm_80gb-x85-hybrid` | 10.91x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 70,905 | 87 | 4,031.7 | 24,190 | 56.9 | 33,542 | `layer_fixed_latency` | 6,504 | 1,551.7 | `a100_sxm_80gb-x86-hybrid` | 10.90x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x102-romfill` | 83,130 | 102 | 4,093.7 | 28,656 | 49.2 | 39,519 | `layer_fixed_latency` | 8,541 | 2,012.7 | `a100_sxm_80gb-x101-hybrid` | 11.12x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x103` | 83,945 | 103 | 4,096.9 | 28,679 | 48.8 | 39,917 | `layer_fixed_latency` | 8,673 | 2,043.4 | `a100_sxm_80gb-x102-hybrid` | 11.09x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x104` | 84,760 | 104 | 4,099.8 | 28,698 | 48.4 | 40,316 | `layer_fixed_latency` | 8,806 | 2,074.2 | `a100_sxm_80gb-x103-hybrid` | 11.06x |
| `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 2 | 4,314.9 | 8,630 | 46.7 | 5,731 | `layer_fixed_latency` | 8,459 | 1,948.2 | `a100_sxm_80gb-x112-hybrid` | 11.62x |
| `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3 | 4,315.4 | 12,946 | 31.1 | 9,157 | `layer_fixed_latency` | 15,335 | 3,529.1 | `a100_sxm_80gb-x168-hybrid` | 11.74x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 4 | 4,344.8 | 4,345 | 23.5 | 1 | `layer_fixed_latency` | 12,962 | 2,983.4 | `a100_sxm_80gb-x224-hybrid` | 11.94x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 306 | densest | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | 61,125 | 3,610.5 | 59.1 | 28,761 |
| array | 306 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,174.4 | 37.1 | 53,863 |
| array | 306 | smallest | `ROM-N6-native-HBMKV-array-hw-tensor-x71` | 57,865 | 2,571.0 | 44.4 | 27,167 |
| wafer | 69 | densest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,314.9 | 46.7 | 5,731 |
| wafer | 69 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 4,344.8 | 23.5 | 1 |
| wafer | 69 | smallest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,314.9 | 46.7 | 5,731 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,174.4 | 37,570 | 53,863 | 13,409 | 3,113.9 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 369.6 | 51,364 | 54,509.3 | 1.001 | 11.29x | 17.5x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 4,344.8 | 4,345 | 1 | 12,962 | 2,983.4 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 363.9 | 86,427 | 90,262.6 | 0.999 | 11.94x | 30.3x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 4,148.3 | 62,224 | 89,324 | 21,311 | 4,965.5 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 363.9 | 86,427 | 90,262.6 | 1.000 | 11.40x | 18.2x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 4,344.8 | -- | 1 | -- | 2,983.4 | -- | -- | -- | -- | -- | 1.001 | 1.05x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,174.4 | 37,570 | 53,863 | 13,409 | 1,563.1 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 369.6 | 51,364 | 27,944.1 | 1.001 | 11.29x | 17.9x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 4,315.4 | 12,946 | 9,157 | 15,335 | 1,770.7 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 367.5 | 64,114 | 34,381.2 | 0.999 | 11.74x | 19.4x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x170` | 138,550 | 4,164.1 | 45,805 | 66,613 | 17,739 | 2,074.8 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 367.5 | 64,114 | 34,381.2 | 0.998 | 11.33x | 16.6x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 4,315.4 | -- | 9,157 | -- | 1,770.7 | -- | -- | -- | -- | -- | 0.999 | 1.04x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,174.4 | 37,570 | 53,863 | 13,409 | 787.7 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 369.6 | 51,364 | 14,661.6 | 1.001 | 11.29x | 18.6x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,310.8 | 17,243 | 12,584 | 17,404 | 1,009.3 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 363.9 | 86,427 | 23,599.9 | 0.999 | 11.85x | 23.4x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 4,148.3 | 62,224 | 89,324 | 21,311 | 1,250.6 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 363.9 | 86,427 | 23,599.9 | 1.000 | 11.40x | 18.9x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,310.8 | -- | 12,584 | -- | 1,009.3 | -- | -- | -- | -- | -- | 1.001 | 1.04x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,174.4 | 37,570 | 53,863 | 13,409 | 400.0 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 369.6 | 51,364 | 8,020.3 | 1.001 | 11.29x | 20.1x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 4,301.1 | 34,409 | 26,290 | 34,808 | 1,011.6 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 357.8 | 175,678 | 23,976.7 | 0.999 | 12.02x | 23.7x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x134` | 109,210 | 4,156.4 | 70,659 | 52,269 | 13,286 | 199.0 | `layer_fixed_latency` | `a100_sxm_80gb-x132-hybrid` | 366.0 | 49,770 | 4,633.7 | 1.002 | 11.36x | 23.3x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,239.9 | 93,278 | 39,997 | 52,723 | 772.6 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 357.8 | 264,929 | 18,327.3 | 0.999 | 11.85x | 23.7x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 4,084.9 | 142,971 | 108,848 | 26,737 | 203.4 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 360.8 | 105,552 | 4,780.4 | 1.001 | 11.32x | 23.5x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,180.4 | 179,756 | 39,997 | 53,784 | 397.8 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 357.8 | 264,929 | 9,853.1 | 0.999 | 11.68x | 24.8x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 3,993.4 | 275,544 | 108,848 | 28,364 | 110.0 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 321.9 | 105,552 | 2,862.3 | 1.001 | 12.41x | 26.0x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,066.7 | 349,736 | 39,997 | 55,870 | 210.4 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 357.8 | 264,929 | 5,616.1 | 0.999 | 11.37x | 26.7x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,068.8 | 785,612 | 134,348 | 39,715 | 50.6 | `compute` | `a100_sxm_80gb-x335-hybrid` | 210.7 | 130,654 | 1,508.4 | 1.001 | 14.56x | 29.8x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,496.2 | 895,031 | 39,997 | 61,772 | 69.0 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 278.5 | 264,929 | 2,130.3 | 0.999 | 12.55x | 30.9x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 1,176.6 | 1,204,812 | 134,348 | 51,375 | 42.6 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 93.8 | 130,654 | 1,021.0 | 1.001 | 12.55x | 23.9x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,976.1 | 2,023,507 | 39,997 | 74,608 | 36.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 144.9 | 264,929 | 1,265.6 | 0.999 | 13.64x | 34.3x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 428.3 | 1,754,161 | 134,348 | 55,914 | 31.9 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 36.7 | 130,654 | 584.4 | 1.001 | 11.68x | 18.3x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 601.6 | 2,463,979 | 39,997 | 76,255 | 30.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 57.8 | 264,929 | 852.1 | 0.999 | 10.40x | 27.5x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-4 | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | 61,125 | array | HBM | 28,761 |
| 8 | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | array | HBM | 33,144 |
| 16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 70,905 | array | HBM | 33,542 |
| 32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x102-romfill` | 83,130 | array | HBM | 39,519 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 43,902 |
| 256 | `ROM-N6-native-HBMKV-array-hw-pipeline-x138` | 112,470 | array | HBM | 53,863 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-pipeline-x207` | 168,705 | array | HBM | 81,355 |
| 4096 | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 224,940 | array | HBM | 108,848 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | rom | 71, 75, 86, 87, 102, 104, 113, 123, 124, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | sram | 71, 75, 86, 87, 103, 104, 113, 132, 134, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | rom | 168, 170, 179, 196, 205, 227, 246, 328, 340, 362, 369 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | sram | 168, 170, 179, 196, 205, 226, 227, 246, 328, 340 |

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
| DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | 1 | 16 | 6.25 | hierarchical, one_shot | 203.60 | 26.02 | 82.82 | 31.16 | 3,610.5 |
| DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x75` | 64 | 2 | 5.25 | one_shot, two_step | 173.85 | 7.99 | 1,060.10 | 14.41 | 836.6 |
| DeepSeek-V4.1-Flash-engram-hbm | `a100_sxm_80gb-x74-hybrid` | 1 | 8 | 5.25 | measured_floor | 860.60 | 937.89 | 1,071.67 | 439.18 | 363.6 |
| DeepSeek-V4.1-Flash-engram-hbm | `a100_sxm_80gb-x74-hybrid` | 64 | 8 | 5.25 | measured_floor | 860.60 | 1,113.87 | 2,995.55 | 497.79 | 215.7 |

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
(4.327e+11 B/s/mm2).

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

- **0 of 4,543 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 35%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 120 | 0 | 53.2% | 80.2% | 0.388 | 71% |
| gpu | wafer (>=40,000 mm2) | 1,480 | 0 | 51.5% | 79.8% | 0.387 | 85% |
| rom | large array (5,000-40,000 mm2) | 360 | 0 | 19.5% | 36.6% | 0.183 | 92% |
| rom | wafer (>=40,000 mm2) | 2,583 | 0 | 22.2% | 41.4% | 0.207 | 97% |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 92,095 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x113` | 2.332748 | 10,051.2 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-hybrid` | 44.681722 | 23,171.8 | link_latency | 19.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 84,760 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x104` | 1.043260 | 8,805.8 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x103-hybrid` | 21.447183 | 21,513.8 | link_latency | 20.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 83,945 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x103` | 0.520056 | 8,673.4 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x102-hybrid` | 11.347735 | 21,348.1 | link_latency | 21.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 92,095 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x113` | 0.302331 | 10,051.2 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-hybrid` | 6.791814 | 23,171.8 | link_latency | 22.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 92,095 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x113` | 0.160141 | 10,431.8 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-hybrid` | 4.022627 | 23,390.9 | link_latency | 25.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 100,245 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x123-romfill` | 0.098327 | 12,516.5 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x121-hybrid` | 2.628969 | 26,991.4 | weight_read | 26.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 168,705 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 0.087372 | 21,655.1 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-hybrid` | 2.359756 | 45,784.4 | weight_read | 27.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.069016 | 61,771.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid` | 2.130317 | 151,894.6 | weight_read | 30.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.036871 | 74,608.0 | kv_read | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid` | 1.265625 | 187,763.7 | weight_read | 34.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.030948 | 76,255.4 | kv_read | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid` | 0.852060 | 201,876.9 | weight_read | 27.53x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 552 B | 307.5 GB | 4.46 | 0.047 GB | 0.181 GB | 278.7 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 92,450 | 4,327.8 | wafer-hybrid | 4,314.9 | wafer-hybrid | 1.00x | 977.0 | pipeline | 371.2 | hybrid | 2.63x | 4.43x | 11.62x | 2.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 3 | 138,675 | 4,346.3 | wafer-hybrid | 4,315.4 | wafer-hybrid | 1.01x | 997.5 | pipeline | 367.5 | hybrid | 2.71x | 4.36x | 11.74x | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 184,900 | 4,349.8 | wafer-hybrid | 4,344.8 | wafer-hybrid | 1.00x | 1,008.0 | pipeline | 363.9 | hybrid | 2.77x | 4.32x | 11.94x | 2.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 6 | 277,350 | 4,345.3 | wafer-hybrid | 4,340.8 | wafer-hybrid | 1.00x | 1,018.7 | pipeline | 357.8 | hybrid | 2.85x | 4.27x | 12.13x | 2.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 369,800 | 4,340.4 | wafer-hybrid | 4,336.4 | wafer-hybrid | 1.00x | 1,024.2 | pipeline | 357.8 | hybrid | 2.86x | 4.24x | 12.12x | 2.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 12 | 554,700 | 4,325.5 | wafer-hybrid | 4,322.0 | wafer-hybrid | 1.00x | 1,029.7 | pipeline | 357.8 | hybrid | 2.88x | 4.20x | 12.08x | 2.88x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 2.62x to 2.88x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | 184,900 | 4,344.8 | 4,344.8 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-hybrid | 185,024 | 1.00x | hybrid | 1,007.54 | 363.9 | 10,188.3 | link_latency | 11.94x | 0.16x | 36.03x | 11.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x71 | 57,865 | 2,571.0 | 2,571.0 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 934.09 | 370.4 | 3,333.4 | link_latency | 6.94x | 0.30x | 21.32x | 6.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 4,315.4 | 12,946.2 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-hybrid | 138,768 | 1.00x | hybrid | 980.40 | 367.5 | 7,717.5 | link_latency | 11.74x | 0.64x | 35.79x | 11.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 2,548.1 | 7,644.3 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 934.09 | 370.4 | 3,333.4 | link_latency | 6.88x | 0.91x | 21.13x | 6.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,310.8 | 17,243.2 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-hybrid | 185,024 | 1.00x | hybrid | 1,007.54 | 363.9 | 10,188.3 | link_latency | 11.85x | 0.64x | 35.75x | 11.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 2,328.0 | 11,640.1 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 934.09 | 370.4 | 3,333.4 | link_latency | 6.29x | 1.38x | 19.31x | 6.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 4,301.1 | 34,408.7 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-hybrid | 370,048 | 1.00x | hybrid | 1,054.14 | 357.8 | 20,036.9 | link_latency | 12.02x | 0.64x | 35.67x | 12.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 1,779.3 | 16,013.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 934.09 | 370.4 | 3,333.4 | link_latency | 4.80x | 1.90x | 14.75x | 4.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,239.9 | 93,278.0 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,054.14 | 357.8 | 30,055.3 | link_latency | 11.85x | 1.15x | 35.16x | 12.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 1,120.0 | 17,919.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 958.05 | 337.1 | 5,393.1 | weight_read | 3.32x | 2.12x | 9.29x | 3.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,180.4 | 179,756.2 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,054.14 | 357.8 | 30,055.3 | link_latency | 11.68x | 2.22x | 34.67x | 12.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 658.8 | 21,080.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 1,012.84 | 280.5 | 8,974.4 | weight_read | 2.35x | 2.35x | 5.46x | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,066.7 | 349,735.8 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,054.14 | 357.8 | 30,055.3 | link_latency | 11.37x | 4.32x | 33.72x | 11.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 357.8 | 22,897.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 1,122.41 | 211.9 | 13,560.3 | weight_read | 1.69x | 1.69x | 2.97x | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,496.2 | 895,031.3 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,234.22 | 278.5 | 71,301.4 | weight_read | 12.55x | 11.04x | 28.99x | 13.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x71 | 57,865 | 94.2 | 24,113.3 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 1,574.72 | 93.5 | 23,924.1 | weight_read | 1.01x | 1.01x | 1.42x | 1.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,976.1 | 2,023,507.4 | kv_read | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,289.29 | 144.9 | 148,356.6 | weight_read | 13.64x | 13.64x | 19.06x | 14.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x71 | 57,865 | 23.6 | 24,168.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 4,189.07 | 42.2 | 43,237.8 | weight_read | 0.56x | 0.56x | 0.98x | 0.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 601.6 | 2,463,978.6 | kv_read | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 2,026.60 | 57.8 | 236,928.1 | weight_read | 10.40x | 10.40x | 12.87x | 10.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x71 | 57,865 | 5.9 | 24,072.1 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 15,546.70 | 25.1 | 102,701.7 | weight_read | 0.23x | 0.23x | 0.66x | 0.23x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 18 | 14,868 | 121.5 | 274.1 | 339.6 | hybrid | 910.78 | 30.9% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 36 | 29,736 | 120.7 | 285.1 | 362.7 | hybrid | 918.55 | 33.3% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 44 | 36,344 | 120.6 | 286.5 | 364.6 | hybrid | 922.35 | 33.6% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 56 | 46,256 | 120.6 | 287.6 | 375.0 | hybrid | 926.32 | 34.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 70 | 57,820 | 120.6 | 259.8 | 370.4 | hybrid | 934.09 | 34.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 74 | 61,124 | 120.6 | 259.6 | 363.6 | hybrid | 937.89 | 34.1% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 85 | 70,210 | 120.6 | 259.3 | 368.5 | hybrid | 941.85 | 34.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 86 | 71,036 | 120.6 | 259.3 | 370.0 | hybrid | 941.85 | 34.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 101 | 83,426 | 120.6 | 258.4 | 368.1 | hybrid | 949.62 | 35.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 102 | 84,252 | 120.6 | 258.4 | 369.3 | hybrid | 949.62 | 35.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 103 | 85,078 | 120.6 | 258.4 | 370.5 | hybrid | 949.62 | 35.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 111 | 91,686 | 120.6 | 257.9 | 370.1 | hybrid | 953.29 | 35.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 112 | 92,512 | 120.6 | 257.8 | 371.2 | hybrid | 953.29 | 35.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 121 | 99,946 | 120.6 | 257.1 | 363.3 | hybrid | 961.06 | 34.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 122 | 100,772 | 120.6 | 257.1 | 364.3 | hybrid | 961.06 | 35.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 130 | 107,380 | 120.6 | 256.4 | 364.1 | hybrid | 965.03 | 35.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 132 | 109,032 | 120.6 | 256.2 | 366.0 | hybrid | 965.03 | 35.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 136 | 112,336 | 120.6 | 256.0 | 369.6 | hybrid | 965.03 | 35.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 160 | 132,160 | 120.6 | 254.2 | 368.0 | hybrid | 976.60 | 35.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 166 | 137,116 | 120.6 | 253.7 | 366.1 | hybrid | 980.40 | 35.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 168 | 138,768 | 120.6 | 253.5 | 367.5 | hybrid | 980.40 | 36.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 177 | 146,202 | 120.6 | 252.8 | 361.8 | hybrid | 988.17 | 35.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 183 | 151,158 | 120.6 | 252.4 | 365.8 | hybrid | 988.17 | 36.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 193 | 159,418 | 120.6 | 251.5 | 361.2 | hybrid | 995.93 | 36.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 202 | 166,852 | 120.6 | 250.7 | 361.4 | hybrid | 999.90 | 36.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 204 | 168,504 | 120.6 | 250.6 | 362.6 | hybrid | 999.90 | 36.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 223 | 184,198 | 120.6 | 249.1 | 363.3 | hybrid | 1,007.54 | 36.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 224 | 185,024 | 120.6 | 249.0 | 363.9 | hybrid | 1,007.54 | 36.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 243 | 200,718 | 120.6 | 247.4 | 360.0 | hybrid | 1,019.11 | 36.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 272 | 224,672 | 120.6 | 245.1 | 360.8 | hybrid | 1,030.84 | 37.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 300 | 247,800 | 120.6 | 242.8 | 357.3 | hybrid | 1,046.38 | 37.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 324 | 267,624 | 120.6 | 205.0 | 356.4 | hybrid | 1,054.14 | 37.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 335 | 276,710 | 120.6 | 204.4 | 357.5 | hybrid | 1,054.14 | 37.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 336 | 277,536 | 120.6 | 204.4 | 357.8 | hybrid | 1,054.14 | 37.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 357 | 294,882 | 120.6 | 203.2 | 356.9 | hybrid | 1,054.14 | 37.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 364 | 300,664 | 120.6 | 202.8 | 356.6 | hybrid | 1,054.14 | 37.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 378 | 312,228 | 120.6 | 202.0 | 356.0 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 448 | 370,048 | 120.6 | 198.1 | 357.8 | hybrid | 1,054.14 | 37.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 616 | 508,816 | 120.6 | 189.4 | 357.8 | hybrid | 1,054.14 | 37.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 672 | 555,072 | 120.6 | 186.6 | 357.8 | hybrid | 1,054.14 | 37.7% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x226 | DeepSeek-V4.1-Flash-engram-hbm | 226 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x179 | DeepSeek-V4.1-Flash-engram-hbm | 179 | tensor | rom_package_ucie | rom_board_serdes | 160 | 109.00 us | 917.5 tok/s | 9,174.7 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 45 on rom_board_serdes (traversals 13.2) = 106.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x196 | DeepSeek-V4.1-Flash-engram-hbm | 196 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x226 | DeepSeek-V4.1-Flash-engram-hbm | 226 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x4 | DeepSeek-V4.1-Flash-engram-hbm | 4 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x168 | DeepSeek-V4.1-Flash-engram-hbm | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.87 us | 581.8 tok/s | 5,818.2 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 17.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hybrid-x196 | DeepSeek-V4.1-Flash-engram-hbm | 196 | hybrid | nvlink3 | infiniband_hdr | 104 | 465.72 us | 214.7 tok/s | 2,147.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 58.55 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | hybrid | on_wafer | rom_wafer_serdes | 82 | 154.20 us | 648.5 tok/s | 6,484.9 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x134 | DeepSeek-V4.1-Flash-engram-hbm | 134 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x75 | DeepSeek-V4.1-Flash-engram-hbm | 75 | tensor | rom_package_ucie | rom_board_serdes | 160 | 73.75 us | 1,355.9 tok/s | 13,558.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 19 on rom_board_serdes (traversals 8.8) = 71.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x103 | DeepSeek-V4.1-Flash-engram-hbm | 103 | hybrid | rom_package_ucie | rom_board_serdes | 105 | 4.70 us | 21,262.9 tok/s | 212,629.2 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 25 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-pipeline-x132 | DeepSeek-V4.1-Flash-engram-hbm | 132 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-tensor-x71 | DeepSeek-V4.1-Flash-engram-hbm | 71 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x86 | DeepSeek-V4.1-Flash-engram-hbm | 86 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | hybrid | on_wafer | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x18-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 42.89 us | 2,331.5 tok/s | 23,314.8 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 38.01 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x18-tensor | DeepSeek-V4.1-Flash-engram-hbm | 18 | tensor | nvlink3 | infiniband_hdr | 160 | 797.50 us | 125.4 tok/s | 1,253.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 390.34 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x18-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 18 | hybrid | nvlink3 | infiniband_hdr | 82 | 412.05 us | 242.7 tok/s | 2,426.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x18-expert | DeepSeek-V4.1-Flash-engram-hbm | 18 | expert | nvlink3 | infiniband_hdr | 160 | 576.91 us | 173.3 tok/s | 1,733.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 403.58 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x36-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 36 | pipeline | nvlink3 | infiniband_hdr | 35 | 88.32 us | 1,132.3 tok/s | 11,322.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.56 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x36-tensor | DeepSeek-V4.1-Flash-engram-hbm | 36 | tensor | nvlink3 | infiniband_hdr | 160 | 810.61 us | 123.4 tok/s | 1,233.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 403.44 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x36-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 36 | hybrid | nvlink3 | infiniband_hdr | 84 | 416.93 us | 239.9 tok/s | 2,398.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x36-expert | DeepSeek-V4.1-Flash-engram-hbm | 36 | expert | nvlink3 | infiniband_hdr | 160 | 569.65 us | 175.5 tok/s | 1,755.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.79 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 167.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x44-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 44 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x44-tensor | DeepSeek-V4.1-Flash-engram-hbm | 44 | tensor | nvlink3 | infiniband_hdr | 160 | 813.89 us | 122.9 tok/s | 1,228.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 406.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x44-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 44 | hybrid | nvlink3 | infiniband_hdr | 85 | 419.37 us | 238.5 tok/s | 2,384.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 12.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x44-expert | DeepSeek-V4.1-Flash-engram-hbm | 44 | expert | nvlink3 | infiniband_hdr | 160 | 568.30 us | 176.0 tok/s | 1,759.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.43 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 166.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash-engram-hbm | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-expert | DeepSeek-V4.1-Flash-engram-hbm | 56 | expert | nvlink3 | infiniband_hdr | 160 | 566.93 us | 176.4 tok/s | 1,763.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 70 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-tensor | DeepSeek-V4.1-Flash-engram-hbm | 70 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 70 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-expert | DeepSeek-V4.1-Flash-engram-hbm | 70 | expert | nvlink3 | infiniband_hdr | 160 | 566.10 us | 176.6 tok/s | 1,766.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.90 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 74 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-tensor | DeepSeek-V4.1-Flash-engram-hbm | 74 | tensor | nvlink3 | infiniband_hdr | 160 | 820.44 us | 121.9 tok/s | 1,218.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 413.27 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 74 | hybrid | nvlink3 | infiniband_hdr | 89 | 429.12 us | 233.0 tok/s | 2,330.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-expert | DeepSeek-V4.1-Flash-engram-hbm | 74 | expert | nvlink3 | infiniband_hdr | 160 | 565.85 us | 176.7 tok/s | 1,767.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.80 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x85-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 85 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x85-tensor | DeepSeek-V4.1-Flash-engram-hbm | 85 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x85-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 85 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x85-expert | DeepSeek-V4.1-Flash-engram-hbm | 85 | expert | nvlink3 | infiniband_hdr | 160 | 565.43 us | 176.9 tok/s | 1,768.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.72 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 86 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-tensor | DeepSeek-V4.1-Flash-engram-hbm | 86 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 86 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-expert | DeepSeek-V4.1-Flash-engram-hbm | 86 | expert | nvlink3 | infiniband_hdr | 160 | 565.40 us | 176.9 tok/s | 1,768.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.72 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x101-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 101 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x101-tensor | DeepSeek-V4.1-Flash-engram-hbm | 101 | tensor | nvlink3 | infiniband_hdr | 160 | 822.71 us | 121.5 tok/s | 1,215.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 415.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x101-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 101 | hybrid | nvlink3 | infiniband_hdr | 92 | 436.44 us | 229.1 tok/s | 2,291.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 29.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x101-expert | DeepSeek-V4.1-Flash-engram-hbm | 101 | expert | nvlink3 | infiniband_hdr | 160 | 564.94 us | 177.0 tok/s | 1,770.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.60 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.35 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x121-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 121 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x121-tensor | DeepSeek-V4.1-Flash-engram-hbm | 121 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x121-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 121 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x121-expert | DeepSeek-V4.1-Flash-engram-hbm | 121 | expert | nvlink3 | infiniband_hdr | 160 | 564.50 us | 177.1 tok/s | 1,771.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.02 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 122 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-tensor | DeepSeek-V4.1-Flash-engram-hbm | 122 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 122 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-expert | DeepSeek-V4.1-Flash-engram-hbm | 122 | expert | nvlink3 | infiniband_hdr | 160 | 564.49 us | 177.2 tok/s | 1,771.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.01 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x130-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 130 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x130-tensor | DeepSeek-V4.1-Flash-engram-hbm | 130 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x130-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 130 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x130-expert | DeepSeek-V4.1-Flash-engram-hbm | 130 | expert | nvlink3 | infiniband_hdr | 160 | 564.36 us | 177.2 tok/s | 1,771.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x132-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 132 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x132-tensor | DeepSeek-V4.1-Flash-engram-hbm | 132 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x132-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 132 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x132-expert | DeepSeek-V4.1-Flash-engram-hbm | 132 | expert | nvlink3 | infiniband_hdr | 160 | 564.34 us | 177.2 tok/s | 1,772.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.89 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 136 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-tensor | DeepSeek-V4.1-Flash-engram-hbm | 136 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 136 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-expert | DeepSeek-V4.1-Flash-engram-hbm | 136 | expert | nvlink3 | infiniband_hdr | 160 | 564.27 us | 177.2 tok/s | 1,772.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.85 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x160-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 160 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x160-tensor | DeepSeek-V4.1-Flash-engram-hbm | 160 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x160-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 160 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x160-expert | DeepSeek-V4.1-Flash-engram-hbm | 160 | expert | nvlink3 | infiniband_hdr | 160 | 563.99 us | 177.3 tok/s | 1,773.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.36 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x166-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 166 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x166-tensor | DeepSeek-V4.1-Flash-engram-hbm | 166 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x166-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 166 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x166-expert | DeepSeek-V4.1-Flash-engram-hbm | 166 | expert | nvlink3 | infiniband_hdr | 160 | 563.94 us | 177.3 tok/s | 1,773.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.36 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 168 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-tensor | DeepSeek-V4.1-Flash-engram-hbm | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 168 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-expert | DeepSeek-V4.1-Flash-engram-hbm | 168 | expert | nvlink3 | infiniband_hdr | 160 | 563.91 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 177 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-tensor | DeepSeek-V4.1-Flash-engram-hbm | 177 | tensor | nvlink3 | infiniband_hdr | 160 | 826.00 us | 121.1 tok/s | 1,210.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 418.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 177 | hybrid | nvlink3 | infiniband_hdr | 102 | 460.84 us | 217.0 tok/s | 2,170.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 53.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-expert | DeepSeek-V4.1-Flash-engram-hbm | 177 | expert | nvlink3 | infiniband_hdr | 160 | 563.84 us | 177.4 tok/s | 1,773.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.33 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x183-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 183 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x183-tensor | DeepSeek-V4.1-Flash-engram-hbm | 183 | tensor | nvlink3 | infiniband_hdr | 160 | 826.00 us | 121.1 tok/s | 1,210.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 418.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x183-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 183 | hybrid | nvlink3 | infiniband_hdr | 102 | 460.84 us | 217.0 tok/s | 2,170.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 53.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x183-expert | DeepSeek-V4.1-Flash-engram-hbm | 183 | expert | nvlink3 | infiniband_hdr | 160 | 563.80 us | 177.4 tok/s | 1,773.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.33 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x193-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 193 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x193-tensor | DeepSeek-V4.1-Flash-engram-hbm | 193 | tensor | nvlink3 | infiniband_hdr | 160 | 826.34 us | 121.0 tok/s | 1,210.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 419.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x193-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 193 | hybrid | nvlink3 | infiniband_hdr | 104 | 465.72 us | 214.7 tok/s | 2,147.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 58.55 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x193-expert | DeepSeek-V4.1-Flash-engram-hbm | 193 | expert | nvlink3 | infiniband_hdr | 160 | 563.72 us | 177.4 tok/s | 1,773.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.30 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 202 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-tensor | DeepSeek-V4.1-Flash-engram-hbm | 202 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 202 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-expert | DeepSeek-V4.1-Flash-engram-hbm | 202 | expert | nvlink3 | infiniband_hdr | 160 | 563.66 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.37 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 204 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-tensor | DeepSeek-V4.1-Flash-engram-hbm | 204 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 204 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-expert | DeepSeek-V4.1-Flash-engram-hbm | 204 | expert | nvlink3 | infiniband_hdr | 160 | 563.65 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x223-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 223 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x223-tensor | DeepSeek-V4.1-Flash-engram-hbm | 223 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x223-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 223 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x223-expert | DeepSeek-V4.1-Flash-engram-hbm | 223 | expert | nvlink3 | infiniband_hdr | 160 | 563.55 us | 177.4 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.27 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash-engram-hbm | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-expert | DeepSeek-V4.1-Flash-engram-hbm | 224 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 243 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-tensor | DeepSeek-V4.1-Flash-engram-hbm | 243 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 243 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-expert | DeepSeek-V4.1-Flash-engram-hbm | 243 | expert | nvlink3 | infiniband_hdr | 160 | 563.45 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 272 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-tensor | DeepSeek-V4.1-Flash-engram-hbm | 272 | tensor | nvlink3 | infiniband_hdr | 160 | 827.38 us | 120.9 tok/s | 1,208.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 420.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 272 | hybrid | nvlink3 | infiniband_hdr | 113 | 487.67 us | 205.1 tok/s | 2,050.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 80.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-expert | DeepSeek-V4.1-Flash-engram-hbm | 272 | expert | nvlink3 | infiniband_hdr | 160 | 563.33 us | 177.5 tok/s | 1,775.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.21 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x300-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 300 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x300-tensor | DeepSeek-V4.1-Flash-engram-hbm | 300 | tensor | nvlink3 | infiniband_hdr | 160 | 827.69 us | 120.8 tok/s | 1,208.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 38 on infiniband_hdr (traversals 2.0) = 420.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x300-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 300 | hybrid | nvlink3 | infiniband_hdr | 117 | 497.43 us | 201.0 tok/s | 2,010.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 37 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 90.27 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x300-expert | DeepSeek-V4.1-Flash-engram-hbm | 300 | expert | nvlink3 | infiniband_hdr | 160 | 563.25 us | 177.5 tok/s | 1,775.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 324 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-tensor | DeepSeek-V4.1-Flash-engram-hbm | 324 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.67 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 41 on infiniband_hdr (traversals 4.0) = 745.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 324 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-expert | DeepSeek-V4.1-Flash-engram-hbm | 324 | expert | nvlink3 | infiniband_hdr | 160 | 563.19 us | 177.6 tok/s | 1,775.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.18 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.01 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 335 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-tensor | DeepSeek-V4.1-Flash-engram-hbm | 335 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 335 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-expert | DeepSeek-V4.1-Flash-engram-hbm | 335 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 336 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-tensor | DeepSeek-V4.1-Flash-engram-hbm | 336 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 336 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-expert | DeepSeek-V4.1-Flash-engram-hbm | 336 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x357-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 357 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x357-tensor | DeepSeek-V4.1-Flash-engram-hbm | 357 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.89 us | 86.7 tok/s | 867.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 745.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x357-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 357 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x357-expert | DeepSeek-V4.1-Flash-engram-hbm | 357 | expert | nvlink3 | infiniband_hdr | 160 | 563.11 us | 177.6 tok/s | 1,775.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x364-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 364 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x364-tensor | DeepSeek-V4.1-Flash-engram-hbm | 364 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.93 us | 86.7 tok/s | 867.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 745.77 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x364-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 364 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x364-expert | DeepSeek-V4.1-Flash-engram-hbm | 364 | expert | nvlink3 | infiniband_hdr | 160 | 563.10 us | 177.6 tok/s | 1,775.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x378-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 378 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x378-tensor | DeepSeek-V4.1-Flash-engram-hbm | 378 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.02 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 745.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x378-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 378 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x378-expert | DeepSeek-V4.1-Flash-engram-hbm | 378 | expert | nvlink3 | infiniband_hdr | 160 | 563.07 us | 177.6 tok/s | 1,776.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.15 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.92 us |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x113 | 92,095 | 4,155.7 | 0.045 | 4,021.3 (70,090) | 4,314.9 (92,450) | 1.07x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x104 | 84,760 | 4,099.8 | 0.048 | 4,021.3 (70,090) | 4,314.9 (92,450) | 1.07x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x103 | 83,945 | 4,096.9 | 0.049 | 4,021.3 (70,090) | 4,274.3 (92,450) | 1.06x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x113 | 92,095 | 4,155.7 | 0.045 | 4,042.2 (83,130) | 4,206.7 (92,450) | 1.04x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x113 | 92,095 | 4,071.3 | 0.044 | 4,071.3 (92,095) | 4,119.5 (138,675) | 1.01x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x123-romfill | 100,245 | 3,978.0 | 0.040 | 3,899.8 (92,095) | 4,001.9 (184,900) | 1.03x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill | 168,705 | 3,872.6 | 0.023 | 3,832.8 (138,550) | 3,990.8 (369,800) | 1.04x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | wafer | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,496.2 | 0.006 | 3,068.8 (277,100) | 3,496.2 (554,700) | 1.14x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | wafer | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,976.1 | 0.004 | 1,158.7 (224,940) | 1,976.1 (554,700) | 1.71x | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | wafer | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 601.6 | 0.001 | 428.3 (277,100) | 601.6 (554,700) | 1.40x | kv_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | sram | 579,549.8 | 26,113.2 | 26,113.2 | 22.19x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | sram | 579,549.8 | 26,113.2 | 26,113.2 | 22.19x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | sram | 579,549.8 | 26,113.2 | 26,113.2 | 22.19x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | sram | 579,549.8 | 26,113.2 | 28,474.4 | 22.19x | 1.09x | weight_read | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | sram | 579,549.8 | 26,113.2 | 44,493.4 | 22.19x | 1.70x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | sram | 579,549.8 | 26,113.2 | 71,129.4 | 22.19x | 2.72x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | sram | 579,549.8 | 26,113.2 | 101,668.7 | 22.19x | 3.89x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | sram | 702,586.6 | 26,113.2 | 188,410.5 | 26.91x | 7.22x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | sram | 1,273,080.3 | 26,113.2 | 309,018.1 | 48.75x | 11.83x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | sram | 1,925,611.7 | 26,113.2 | 429,366.6 | 73.74x | 16.44x | weight_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | rom | 1,760,294.8 | 86,178.6 | 86,178.6 | 20.43x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | rom | 1,760,294.8 | 86,178.6 | 86,178.6 | 20.43x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | rom | 1,760,294.8 | 86,178.6 | 86,178.6 | 20.43x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | rom | 1,760,294.8 | 86,178.6 | 86,178.6 | 20.43x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | rom | 1,760,294.8 | 86,178.6 | 86,178.6 | 20.43x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | rom | 1,760,294.8 | 86,178.6 | 106,836.1 | 20.43x | 1.24x | kv_read | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | rom | 1,760,294.8 | 86,178.6 | 161,577.0 | 20.43x | 1.87x | kv_read | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | rom | 1,760,294.8 | 90,298.1 | 312,957.5 | 19.49x | 3.47x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | rom | 2,023,507.4 | 90,298.1 | 420,374.3 | 22.41x | 4.66x | kv_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | rom | 2,463,978.6 | 90,298.1 | 441,389.0 | 27.29x | 4.89x | kv_read | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,549.8 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,760,294.8 | 3.173 | kv_read | 3.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,549.8 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,760,294.8 | 3.173 | kv_read | 3.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,549.8 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,760,294.8 | 3.173 | kv_read | 3.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,549.8 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,760,294.8 | 3.173 | kv_read | 3.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.43 | 28,474.4 | 0.308 | layer_fixed_latency | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,549.8 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,760,294.8 | 3.173 | kv_read | 3.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 1.66 | 44,493.4 | 0.321 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,549.8 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,760,294.8 | 3.173 | kv_read | 3.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.18 | 71,129.4 | 0.513 | weight_read | 0.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 3.46 | 1.43 | 106,836.1 | 1.156 | layer_fixed_latency | 0.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,549.8 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,760,294.8 | 3.173 | kv_read | 3.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,178.6 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.54 | 101,668.7 | 1.100 | weight_read | 0.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 3.46 | 1.99 | 161,577.0 | 1.748 | layer_fixed_latency | 0.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 702,586.6 | 1.267 | layer_fixed_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,760,294.8 | 3.173 | kv_read | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x36-perstream | 29,340 | 1.00 | 7.11 | 26,113.2 | 0.890 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 2.25 | 90,298.1 | 0.977 | weight_read | 0.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.49 | 188,410.5 | 2.038 | weight_read | 0.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 3.46 | 2.06 | 312,957.5 | 3.385 | weight_read | 0.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,273,080.3 | 2.295 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 2,023,507.4 | 3.648 | kv_read | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x36-perstream | 29,340 | 1.00 | 28.44 | 26,113.2 | 0.890 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 8.98 | 90,298.1 | 0.977 | weight_read | 0.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 5.09 | 309,018.1 | 3.343 | weight_read | 0.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 3.46 | 2.69 | 420,374.3 | 4.547 | kv_read | 0.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,925,611.7 | 3.471 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 2,463,978.6 | 4.442 | kv_read | 1.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x36-perstream | 29,340 | 1.00 | 113.78 | 26,113.2 | 0.890 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 35.93 | 90,298.1 | 0.977 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 7.62 | 429,366.6 | 4.644 | kv_read | 0.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 3.69 | 441,389.0 | 4.774 | kv_read | 0.23x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 36 | 7.11 | 1.049 | 1.906 | 1.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 36 | 28.44 | 1.231 | 3.315 | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 36 | 113.78 | 2.133 | 6.729 | 3.15x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 36 | 10.26 | 6.20 | 1.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 36 | 17.40 | 8.51 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 36 | 26.00 | 11.19 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 36 | 32.76 | 14.07 | 2.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 36 | 35.50 | 16.86 | 2.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 36 | 35.96 | 19.16 | 1.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 36 | 36.00 | 21.23 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 36 | 36.00 | 21.31 | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 36 | 36.00 | 21.31 | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 44 | 10.54 | 6.54 | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 44 | 18.33 | 9.11 | 2.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 44 | 28.53 | 12.16 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 44 | 37.84 | 15.55 | 2.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 44 | 42.66 | 18.90 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 44 | 43.84 | 21.72 | 2.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 44 | 43.99 | 24.31 | 1.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 44 | 43.99 | 24.41 | 1.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 44 | 43.99 | 24.41 | 1.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 70 | 11.02 | 7.38 | 1.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 70 | 20.04 | 10.44 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 70 | 33.60 | 14.49 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 70 | 49.55 | 19.21 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 70 | 62.14 | 24.12 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 70 | 67.90 | 28.48 | 2.38x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 70 | 69.69 | 32.63 | 2.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 70 | 69.72 | 32.80 | 2.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 70 | 69.72 | 32.80 | 2.13x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 85 | 11.17 | 7.75 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 85 | 20.59 | 10.96 | 1.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 85 | 35.36 | 15.51 | 2.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 85 | 54.11 | 20.83 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 85 | 70.93 | 26.50 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 85 | 80.26 | 31.63 | 2.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 85 | 84.02 | 36.61 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 85 | 84.10 | 36.82 | 2.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 85 | 84.10 | 36.82 | 2.28x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 101 | 5.85 | 5.29 | 1.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 101 | 11.28 | 8.08 | 1.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 101 | 21.01 | 11.42 | 1.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 101 | 36.75 | 16.45 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 101 | 57.88 | 22.32 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 101 | 78.74 | 28.70 | 2.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 101 | 92.08 | 34.59 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 101 | 98.63 | 40.39 | 2.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 101 | 98.79 | 40.64 | 2.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 101 | 98.79 | 40.64 | 2.43x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 121 | 5.88 | 5.39 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 121 | 11.38 | 8.43 | 1.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 121 | 21.39 | 11.90 | 1.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 121 | 38.02 | 17.44 | 2.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 121 | 61.50 | 23.88 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 121 | 86.73 | 31.09 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 121 | 105.01 | 37.83 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 121 | 115.71 | 44.59 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 121 | 116.00 | 44.88 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 121 | 116.00 | 44.88 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 122 | 5.88 | 5.39 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 122 | 11.39 | 8.44 | 1.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 122 | 21.41 | 11.93 | 1.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 122 | 38.08 | 17.49 | 2.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 122 | 61.66 | 23.95 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 122 | 87.09 | 31.20 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 122 | 105.60 | 37.98 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 122 | 116.53 | 44.79 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 122 | 116.83 | 45.08 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 122 | 116.83 | 45.08 | 2.59x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 132 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 132 | 11.43 | 8.59 | 1.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 132 | 21.55 | 12.15 | 1.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 132 | 38.58 | 17.92 | 2.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 132 | 63.12 | 24.63 | 2.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 132 | 90.45 | 32.25 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 132 | 111.33 | 39.45 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 132 | 124.50 | 46.70 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 132 | 124.88 | 47.00 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 132 | 124.88 | 47.00 | 2.66x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 160 | 5.91 | 5.52 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 160 | 11.51 | 8.95 | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 160 | 21.87 | 12.70 | 1.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 160 | 39.68 | 18.92 | 2.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 160 | 66.41 | 26.26 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 160 | 98.31 | 34.86 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 160 | 125.31 | 43.11 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 160 | 144.97 | 51.54 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 160 | 145.59 | 51.90 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 160 | 145.59 | 51.90 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 166 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 166 | 11.52 | 9.01 | 1.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 166 | 21.92 | 12.81 | 1.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 166 | 39.87 | 19.11 | 2.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 166 | 66.99 | 26.58 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 166 | 99.75 | 35.37 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 166 | 127.96 | 43.82 | 2.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 166 | 149.01 | 52.50 | 2.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 166 | 149.69 | 52.87 | 2.83x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 166 | 149.69 | 52.87 | 2.83x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 202 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 202 | 22.19 | 13.42 | 1.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 202 | 40.79 | 20.04 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 202 | 69.87 | 28.30 | 2.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 202 | 107.00 | 38.17 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 202 | 141.77 | 47.74 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 202 | 170.93 | 57.73 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 202 | 171.96 | 58.16 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 202 | 171.96 | 58.16 | 2.96x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 223 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 223 | 11.62 | 9.52 | 1.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 223 | 22.30 | 13.75 | 1.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 223 | 41.21 | 20.48 | 2.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 223 | 71.17 | 29.22 | 2.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 223 | 110.38 | 39.63 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 223 | 148.47 | 49.78 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 223 | 182.07 | 60.47 | 3.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 223 | 183.30 | 60.93 | 3.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 223 | 183.30 | 60.93 | 3.01x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 243 | 11.64 | 9.66 | 1.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 243 | 22.39 | 14.03 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 243 | 41.53 | 20.84 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 243 | 72.22 | 30.04 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 243 | 113.17 | 40.91 | 2.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 243 | 154.10 | 51.56 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 243 | 191.70 | 62.89 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 243 | 193.12 | 63.38 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 243 | 193.12 | 63.38 | 3.05x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 300 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 300 | 11.69 | 9.98 | 1.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 300 | 22.59 | 14.77 | 1.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 300 | 42.24 | 21.70 | 1.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 300 | 74.53 | 32.13 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 300 | 119.41 | 43.96 | 2.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 300 | 167.10 | 55.91 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 300 | 214.85 | 68.94 | 3.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 300 | 216.77 | 69.52 | 3.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 300 | 216.77 | 69.52 | 3.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 324 | 11.71 | 10.09 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 324 | 22.65 | 15.05 | 1.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 324 | 42.47 | 22.00 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 324 | 75.27 | 32.91 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 324 | 121.48 | 45.03 | 2.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 324 | 171.53 | 57.52 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 324 | 223.03 | 71.21 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 324 | 225.14 | 71.81 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 324 | 225.14 | 71.81 | 3.14x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 357 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 357 | 11.73 | 10.22 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 357 | 22.72 | 15.40 | 1.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 357 | 42.74 | 22.39 | 1.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 357 | 76.15 | 33.88 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 357 | 123.93 | 46.35 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 357 | 176.86 | 59.62 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 357 | 233.07 | 74.16 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 357 | 235.42 | 74.78 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 357 | 235.42 | 74.78 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 364 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 364 | 11.73 | 10.24 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 364 | 22.73 | 15.48 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 364 | 42.79 | 22.47 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 364 | 76.32 | 34.07 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 364 | 124.40 | 46.61 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 364 | 177.89 | 60.05 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 364 | 235.04 | 74.75 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 364 | 237.43 | 75.39 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 364 | 237.43 | 75.39 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 378 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 378 | 11.74 | 10.29 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 378 | 22.76 | 15.61 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 378 | 42.88 | 22.62 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 378 | 76.63 | 34.44 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 378 | 125.30 | 47.12 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 378 | 179.87 | 60.89 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 378 | 238.83 | 75.92 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 378 | 241.32 | 76.57 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 378 | 241.32 | 76.57 | 3.15x |
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
| gpu | DeepSeek-V4.1-Flash-engram-hbm | 1 | 860.60 | 32.3% |
| rom | DeepSeek-V4.1-Flash-engram-hbm | 1 | 224.57 | 97.6% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | sram | interleaved | 128 B | 1.77x |
| DeepSeek-V4.1-Flash-engram-hbm | hbm | interleaved | 32 B | 1.34x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 168 | 0.09% | 0.63 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 162 | 0.09% | 0.61 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 162 | 0.09% | 0.61 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 3 | 0.08% | 0.61 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 3 | 0.08% | 0.61 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 3 | 0.08% | 0.61 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 3 | 0.08% | 0.61 | 4.24 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 333.4 | 23,669.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 333.4 | 23,669.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 333.4 | 23,669.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 333.4 | 23,669.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 333.4 | 23,669.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 333.4 | 23,669.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 333.4 | 23,669.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 5.52% | 24.5 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 94.2 | 24,113.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 20.32% | 67.2 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 23.6 | 24,168.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 59.69% | 180.9 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 5.9 | 24,072.1 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 3 |
| gpu | link_latency | 930 |
| gpu | weight_read | 667 |
| rom | compute | 710 |
| rom | infeasible | 2127 |
| rom | kv_read | 106 |
| rom | layer_fixed_latency | 794 |
| rom | link_latency | 844 |
| rom | weight_read | 489 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2127 |

## Mechanical consistency audit

**FAIL** over 142,239 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x179', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x196', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x226', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x246', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x328', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x179', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x196', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x226', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x246', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x328', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x179', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x196', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x226', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x246', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x328', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x179', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x196', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x226', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x246', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x328', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x179', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x196', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)

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

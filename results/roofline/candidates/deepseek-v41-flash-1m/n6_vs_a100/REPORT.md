# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash-1m

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash at 1,000,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 62x (ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream, 341 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 3 devices. On the GPU side the correction reaches 17x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 54 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash takes 2 x 46,225 mm2 (92,450 mm2, wafer, KV in SRAM) at 3,670 tok/s per user and 40 tok/s per 1,000 mm2, holding 1 session, against 112 copies of one unified HBM die at the same silicon: 8.2x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash on 138,675 mm2 of ROM silicon at 4,449 tok/s per user against 138,768 mm2 of a100_sxm_80gb-x168-hybrid at 445 tok/s: **10.0x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 12,978. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on DeepSeek-V4.1-Flash at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 1,172 us of link latency per token; but the model has 40 layers, so at most 40 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 1,065 us. The iso-area per-user ratio at that point falls from 10.2x to 9.8x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 3.62x to it.** At 92,450 mm2 on DeepSeek-V4.1-Flash the pipeline-only GPU delivers 124.28 tok/s and the same silicon running hybrid delivers 450 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.01x (DeepSeek-V4.1-Flash, ROM binding on `link_latency`) to 6.26x (DeepSeek-V4.1-Flash, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 185 to 21,889 tok/s, and its rate with every slot occupied from 21,774 to 21,889. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 118 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 227.9 us and cap it at 4,387 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 6 of 10 operating points and an array 4; on tokens per second per square millimetre the same points go 9 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 125 of 3667 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 34.8x of aggregate throughput (DeepSeek-V4.1-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 12.42x, on DeepSeek-V4.1-Flash at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4.1-Flash at 1,000,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-wafer-hybrid-x2`** -- 2 x 46,225 mm2 wafers, 92,450 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **3,670.0 tok/s per user** (0.27 ms/token), binding on `layer_fixed_latency`
- **39.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,670 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 4,615 W at 0.050 W/mm2, 1,257.6 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 112 copies of one unified HBM die -- `a100_sxm_80gb-x112-hybrid`, 92,512 mm2, area ratio 0.9993 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 92,450 | 92,512 | 0.9993 |
| user tok/s | 3,670.0 | 450.3 | 8.15x |
| aggregate tok/s | 3,670 | 6,304 | 0.26x |
| resident sessions | 1 | 8,461 | -- |
| J/token | 1.2576 | 37.3108 | 29.7x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 8,461 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 455.8 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,448.8 | 32.1 | 1 | 10.00x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,448.8 | 32.1 | 1 | 10.00x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-hybrid-x110` | 89,650 | 1,697.4 | 18.9 | 1 | 3.81x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,670.0 | 39.7 | 1 | 8.15x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,670.0 | 39.7 | -- | 39.7 | ACCEPT |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,448.8 | 32.1 | 16.8 | 39.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x2` **<-- recommended** | 92,450 | 2 | 3,670.0 | 3,670 | 39.7 | 1 | `layer_fixed_latency` | 4,615 | 1,257.6 | `a100_sxm_80gb-x112-hybrid` | 8.15x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3 | 4,448.8 | 4,449 | 32.1 | 1 | `layer_fixed_latency` | 11,324 | 2,545.4 | `a100_sxm_80gb-x168-hybrid` | 10.00x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 312 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x136` | 110,840 | 2,894.5 | 26.1 | 1 |
| array | 312 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 3,552.7 | 12.7 | 27,583 |
| array | 312 | smallest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x110` | 89,650 | 1,697.4 | 18.9 | 1 |
| wafer | 54 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,670.0 | 39.7 | 1 |
| wafer | 54 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,448.8 | 32.1 | 1 |
| wafer | 54 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,670.0 | 39.7 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 3,552.7 | 152,768 | 27,583 | 41,606 | 10,285.7 | `layer_fixed_latency` | `a100_sxm_80gb-x337-hybrid` | 427.3 | 26,608 | 115,258.7 | 1.001 | 8.31x | 11.2x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,448.8 | 4,449 | 1 | 11,324 | 2,545.4 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 444.9 | 12,978 | 55,923.9 | 0.999 | 10.00x | 22.0x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x171` | 139,365 | 3,159.5 | 69,510 | 13,791 | 16,179 | 4,407.9 | `layer_fixed_latency` | `a100_sxm_80gb-x169-hybrid` | 437.0 | 13,058 | 57,242.8 | 0.998 | 7.23x | 13.0x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,448.8 | -- | 1 | -- | 2,545.4 | -- | -- | -- | -- | -- | 1.005 | 1.41x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 3,552.7 | 152,768 | 27,583 | 41,606 | 5,159.8 | `layer_fixed_latency` | `a100_sxm_80gb-x337-hybrid` | 427.3 | 26,608 | 58,329.1 | 1.001 | 8.31x | 11.3x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,212.6 | 92,678 | 8,323 | 76,239 | 8,709.5 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 430.7 | 53,627 | 114,026.0 | 0.999 | 9.78x | 13.1x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 3,552.7 | 152,768 | 27,583 | 41,606 | 2,596.9 | `layer_fixed_latency` | `a100_sxm_80gb-x337-hybrid` | 427.3 | 26,608 | 29,864.3 | 1.001 | 8.31x | 11.5x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,212.6 | 92,678 | 8,323 | 76,239 | 4,371.7 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 430.7 | 53,627 | 57,712.7 | 0.999 | 9.78x | 13.2x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 3,552.7 | 152,768 | 27,583 | 41,606 | 1,315.4 | `layer_fixed_latency` | `a100_sxm_80gb-x337-hybrid` | 427.3 | 26,608 | 15,631.9 | 1.001 | 8.31x | 11.9x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,212.6 | 92,678 | 8,323 | 76,239 | 2,202.8 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 430.7 | 53,627 | 29,556.1 | 0.999 | 9.78x | 13.4x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 3,552.7 | 152,768 | 27,583 | 41,606 | 674.7 | `layer_fixed_latency` | `a100_sxm_80gb-x337-hybrid` | 427.3 | 26,608 | 8,515.7 | 1.001 | 8.31x | 12.6x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,212.6 | 92,678 | 8,323 | 76,239 | 1,118.4 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 430.7 | 53,627 | 15,477.8 | 0.999 | 9.78x | 13.8x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 3,552.7 | 152,768 | 27,583 | 41,606 | 354.3 | `layer_fixed_latency` | `a100_sxm_80gb-x337-hybrid` | 427.3 | 26,608 | 4,957.6 | 1.001 | 8.31x | 14.0x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,116.3 | 176,999 | 8,323 | 79,101 | 588.9 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 430.7 | 53,627 | 8,438.7 | 0.999 | 9.56x | 14.3x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 3,535.8 | 300,546 | 27,422 | 46,357 | 193.7 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 394.2 | 26,447 | 3,006.8 | 1.001 | 8.97x | 15.5x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,540.0 | 226,563 | 8,323 | 80,585 | 355.7 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 430.7 | 53,627 | 4,919.1 | 0.999 | 8.22x | 13.8x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 2,395.1 | 613,137 | 27,583 | 56,688 | 92.5 | `compute` | `a100_sxm_80gb-x337-hybrid` | 230.7 | 26,608 | 1,459.9 | 1.001 | 10.38x | 15.8x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,874.5 | 479,874 | 8,323 | 88,956 | 185.4 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 318.0 | 53,627 | 1,982.1 | 0.999 | 5.90x | 10.7x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | 827.5 | 847,310 | 27,583 | 63,667 | 75.1 | `compute` | `a100_sxm_80gb-x337-hybrid` | 94.7 | 26,608 | 1,040.8 | 1.001 | 8.74x | 13.9x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 597.6 | 611,959 | 8,323 | 93,317 | 152.5 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 151.4 | 53,627 | 1,163.6 | 0.999 | 3.95x | 7.6x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | 222.0 | 909,258 | 27,583 | 64,973 | 71.5 | `compute` | `a100_sxm_80gb-x337-hybrid` | 35.5 | 26,608 | 621.3 | 1.001 | 6.26x | 8.7x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 156.6 | 641,525 | 8,323 | 93,418 | 145.6 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 56.9 | 53,627 | 879.3 | 0.999 | 2.75x | 6.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | wafer | SRAM | 1 |
| 2-16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x152` | 123,880 | array | HBM | 12,259 |
| 32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x171` | 139,365 | array | HBM | 13,791 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 167,890 | array | HBM | 16,614 |
| 256 | `ROM-N6-native-HBMKV-array-hw-pipeline-x246` | 200,490 | array | HBM | 19,840 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | array | HBM | 27,583 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash | HBM | rom | 118, 125, 143, 152, 170, 171, 196, 206, 207, 227, 228, 340, 342 |
| DeepSeek-V4.1-Flash | HBM | sram | 118, 125, 143, 152, 170, 171, 227, 228, 246, 313, 316, 340, 342 |
| DeepSeek-V4.1-Flash | SRAM | rom | 110, 113, 133, 136, 152, 155, 156, 159, 170, 212, 227, 318, 340 |
| DeepSeek-V4.1-Flash | SRAM | sram | 110, 113, 133, 136, 152, 155, 156, 159, 170, 212, 227, 318, 340 |

A wafer chosen over the array class is now compared against an array sampled at the wafer's own area and at four rungs above the array's floor; the `array @ wafer area` rows in the iso-area table above are that comparison. The curve BETWEEN rungs is still not evidence and must not be read as any.

## Serial latency and collectives

The serial part of every step is the longest path of one token's operator
dependency graph (`src/opentallas/critical_path.py`): the dependent-operator
chain priced with measured RTL depths (ROM) or, on the GPU, a megakernel/PDL
execution in which every remaining dependent boundary pays only its measured
residual dependency signal (all-SM gather or one-to-one handoff, no launch;
`serial_latency.gpu_datapath`), every collective the weight split needs with its
latency and real payload, and every pipeline hop. A hybrid layout's tensor
group and every collective's reduction algorithm are searched per point.
`legacy` is the flat per-layer floor plus two all-reduces per layer this
replaced.

| Model | Design | Batch | Group | Coll./layer | Algorithms | Chain (us) | Comm. (us) | Sweep (us) | Legacy serial (us) | tok/s/user |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 1 | 57 on `rom_wafer_express` | 6.25 | one_shot, rec_doubling | 149.36 | 84.21 | 48.01 | 47.41 | 3,670.0 |
| DeepSeek-V4.1-Flash | `a100_sxm_80gb-x112-hybrid` | 1 | 8 | 5.25 | measured_floor | 368.98 | 963.69 | 1,005.83 | 448.93 | 450.3 |
| DeepSeek-V4.1-Flash | `a100_sxm_80gb-x112-hybrid` | 64 | 8 | 5.25 | measured_floor | 370.98 | 1,095.69 | 2,251.32 | 493.55 | 287.8 |

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
| A100 80GB, weight-bound gate, same model and batch | 1.487141 J/token | 352.1 | 236.7 |

That is a factor of 206 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 2.6-3.2x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

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

- **0 of 3,667 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 34%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,311 | 0 | 54.9% | 79.8% | 0.387 | 66% |
| rom | wafer (>=40,000 mm2) | 2,356 | 0 | 22.2% | 50.0% | 0.250 | 93% |

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
| DeepSeek-V4.1-Flash | 1 | 138,675 | `DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2.545446 | 11,324.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid` | 55.923910 | 37,331.4 | link_latency | 21.97x |
| DeepSeek-V4.1-Flash | 2 | 277,350 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6` | 3.872238 | 33,719.8 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-hybrid` | 57.712740 | 73,832.2 | link_latency | 14.90x |
| DeepSeek-V4.1-Flash | 4 | 277,350 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6` | 1.953087 | 33,719.8 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-hybrid` | 29.556133 | 73,832.2 | link_latency | 15.13x |
| DeepSeek-V4.1-Flash | 8 | 277,350 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6` | 0.993512 | 33,719.8 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-hybrid` | 15.477829 | 73,832.2 | link_latency | 15.58x |
| DeepSeek-V4.1-Flash | 16 | 277,350 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6` | 0.525137 | 35,210.9 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-hybrid` | 8.438677 | 73,832.2 | link_latency | 16.07x |
| DeepSeek-V4.1-Flash | 32 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.588857 | 79,101.0 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid` | 8.438677 | 147,664.3 | link_latency | 14.33x |
| DeepSeek-V4.1-Flash | 64 | 255,095 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x313` | 0.179087 | 41,993.8 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x309-hybrid` | 2.850081 | 70,529.3 | link_latency | 15.91x |
| DeepSeek-V4.1-Flash | 256 | 277,100 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.092362 | 56,298.7 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid` | 1.453186 | 85,612.3 | weight_read | 15.73x |
| DeepSeek-V4.1-Flash | 1024 | 277,100 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340` | 0.075154 | 63,188.7 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid` | 1.038277 | 100,350.2 | weight_read | 13.82x |
| DeepSeek-V4.1-Flash | 4096 | 277,100 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340` | 0.071494 | 64,473.1 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid` | 0.616698 | 89,344.3 | weight_read | 8.63x |

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
| DeepSeek-V4.1-Flash | 1,000,000 | 552 B | 510.3 GB | 7.40 | 0.183 GB | 0.893 GB | 71.3 |

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
| DeepSeek-V4.1-Flash | 2 | 92,450 | 4,863.6 | wafer-pipeline | 3,670.0 | wafer-hybrid | 1.33x | 1,861.0 | pipeline | 450.3 | hybrid | 4.13x | 2.61x | 8.15x | 3.12x |
| DeepSeek-V4.1-Flash | 3 | 138,675 | 5,299.9 | wafer-pipeline | 4,448.8 | wafer-hybrid | 1.19x | 1,937.9 | pipeline | 444.9 | hybrid | 4.36x | 2.73x | 10.00x | 3.66x |
| DeepSeek-V4.1-Flash | 4 | 184,900 | 5,299.9 | wafer-pipeline | 4,212.9 | wafer-hybrid | 1.26x | 1,978.7 | pipeline | 439.6 | hybrid | 4.50x | 2.68x | 9.58x | 3.58x |
| DeepSeek-V4.1-Flash | 6 | 277,350 | 5,302.5 | wafer-pipeline | 4,188.8 | wafer-hybrid | 1.27x | 2,021.3 | pipeline | 430.7 | hybrid | 4.69x | 2.62x | 9.72x | 3.71x |
| DeepSeek-V4.1-Flash | 8 | 369,800 | 5,319.4 | wafer-pipeline | 4,193.9 | wafer-hybrid | 1.27x | 2,043.3 | pipeline | 430.7 | hybrid | 4.74x | 2.60x | 9.74x | 3.74x |
| DeepSeek-V4.1-Flash | 12 | 554,700 | 5,327.6 | wafer-pipeline | 4,212.6 | wafer-hybrid | 1.26x | 2,065.8 | pipeline | 430.7 | hybrid | 4.80x | 2.58x | 9.78x | 3.79x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 3.12x to 3.79x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash | 1 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 4,448.8 | 4,448.8 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid | 138,768 | 1.00x | hybrid | 990.79 | 444.9 | 9,342.4 | link_latency | 10.00x | 0.21x | 35.80x | 10.00x |
| DeepSeek-V4.1-Flash | 1 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x110 | 89,650 | 1,697.4 | 1,697.4 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x109-hybrid | 90,034 | 1.00x | hybrid | 963.69 | 445.4 | 6,235.6 | link_latency | 3.81x | 0.13x | 13.66x | 3.81x |
| DeepSeek-V4.1-Flash | 2 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 4,212.6 | 92,678.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,064.54 | 430.7 | 36,182.4 | link_latency | 9.78x | 1.11x | 33.90x | 10.23x |
| DeepSeek-V4.1-Flash | 2 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x118 | 96,170 | 1,587.9 | 6,351.5 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | 95,816 | 1.00x | hybrid | 967.65 | 443.4 | 6,651.0 | link_latency | 3.58x | 0.44x | 12.78x | 3.58x |
| DeepSeek-V4.1-Flash | 4 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 4,212.6 | 92,678.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,064.54 | 430.7 | 36,182.4 | link_latency | 9.78x | 1.11x | 33.90x | 10.23x |
| DeepSeek-V4.1-Flash | 4 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x118 | 96,170 | 1,587.9 | 6,351.5 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | 95,816 | 1.00x | hybrid | 967.65 | 443.4 | 6,651.0 | link_latency | 3.58x | 0.44x | 12.78x | 3.58x |
| DeepSeek-V4.1-Flash | 8 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 4,212.6 | 92,678.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,064.54 | 430.7 | 36,182.4 | link_latency | 9.78x | 1.11x | 33.90x | 10.23x |
| DeepSeek-V4.1-Flash | 8 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x118 | 96,170 | 1,412.1 | 11,296.9 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | 95,816 | 1.00x | hybrid | 967.65 | 443.4 | 6,651.0 | link_latency | 3.18x | 0.78x | 11.36x | 3.18x |
| DeepSeek-V4.1-Flash | 16 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 4,212.6 | 92,678.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,064.54 | 430.7 | 36,182.4 | link_latency | 9.78x | 1.11x | 33.90x | 10.23x |
| DeepSeek-V4.1-Flash | 16 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x118 | 96,170 | 1,017.9 | 16,286.1 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | 95,816 | 1.00x | hybrid | 970.47 | 438.6 | 7,017.5 | link_latency | 2.32x | 1.13x | 8.19x | 2.32x |
| DeepSeek-V4.1-Flash | 32 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 4,116.3 | 176,999.1 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,064.54 | 430.7 | 36,182.4 | link_latency | 9.56x | 2.12x | 33.12x | 10.00x |
| DeepSeek-V4.1-Flash | 32 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x118 | 96,170 | 605.8 | 19,385.8 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | 95,816 | 1.00x | hybrid | 1,004.64 | 374.1 | 11,971.4 | weight_read | 1.62x | 1.34x | 4.87x | 1.62x |
| DeepSeek-V4.1-Flash | 64 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 3,540.0 | 226,563.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,064.54 | 430.7 | 36,182.4 | link_latency | 8.22x | 2.71x | 28.49x | 8.60x |
| DeepSeek-V4.1-Flash | 64 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x118 | 96,170 | 328.2 | 21,005.6 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | 95,816 | 1.00x | hybrid | 1,093.83 | 290.2 | 18,574.1 | weight_read | 1.13x | 1.13x | 2.64x | 1.13x |
| DeepSeek-V4.1-Flash | 256 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x342 | 278,730 | 2,395.1 | 613,137.2 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-hybrid | 278,362 | 1.00x | hybrid | 1,489.78 | 230.7 | 59,071.3 | weight_read | 10.38x | 10.38x | 19.27x | 10.41x |
| DeepSeek-V4.1-Flash | 256 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x118 | 96,170 | 85.5 | 21,885.8 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | 95,816 | 1.00x | hybrid | 1,425.91 | 129.6 | 33,171.0 | weight_read | 0.66x | 0.66x | 0.98x | 0.66x |
| DeepSeek-V4.1-Flash | 1024 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 827.5 | 847,310.0 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-hybrid | 278,362 | 1.00x | hybrid | 1,393.74 | 94.7 | 96,996.8 | weight_read | 8.74x | 8.74x | 11.42x | 8.92x |
| DeepSeek-V4.1-Flash | 1024 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x118 | 96,170 | 21.4 | 21,920.5 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | 95,816 | 1.00x | hybrid | 3,557.27 | 50.4 | 51,624.4 | weight_read | 0.42x | 0.42x | 0.63x | 0.42x |
| DeepSeek-V4.1-Flash | 4096 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 222.0 | 909,258.4 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-hybrid | 278,362 | 1.00x | hybrid | 9,126.35 | 35.5 | 145,272.3 | weight_read | 6.26x | 6.26x | 8.32x | 6.29x |
| DeepSeek-V4.1-Flash | 4096 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x118 | 96,170 | 5.3 | 21,888.7 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | 95,816 | 1.00x | hybrid | 12,560.87 | 25.2 | 103,322.3 | weight_read | 0.21x | 0.21x | 0.46x | 0.21x |

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
| DeepSeek-V4.1-Flash | 54 | 44,604 | 124.3 | 333.6 | 449.1 | hybrid | 936.71 | 42.1% | link_latency |
| DeepSeek-V4.1-Flash | 56 | 46,256 | 124.3 | 333.8 | 455.8 | hybrid | 936.71 | 42.7% | link_latency |
| DeepSeek-V4.1-Flash | 58 | 47,908 | 124.3 | 333.5 | 436.8 | hybrid | 940.51 | 41.1% | weight_read |
| DeepSeek-V4.1-Flash | 59 | 48,734 | 124.3 | 333.6 | 440.0 | hybrid | 940.51 | 41.4% | weight_read |
| DeepSeek-V4.1-Flash | 109 | 90,034 | 124.3 | 294.7 | 445.4 | hybrid | 963.69 | 42.9% | link_latency |
| DeepSeek-V4.1-Flash | 111 | 91,686 | 124.3 | 294.5 | 448.7 | hybrid | 963.69 | 43.2% | link_latency |
| DeepSeek-V4.1-Flash | 112 | 92,512 | 124.3 | 294.5 | 450.3 | hybrid | 963.69 | 43.4% | link_latency |
| DeepSeek-V4.1-Flash | 116 | 95,816 | 124.3 | 294.0 | 443.4 | hybrid | 967.65 | 42.9% | link_latency |
| DeepSeek-V4.1-Flash | 123 | 101,598 | 124.3 | 293.4 | 441.6 | hybrid | 971.45 | 42.9% | link_latency |
| DeepSeek-V4.1-Flash | 131 | 108,206 | 124.3 | 292.5 | 441.2 | hybrid | 975.42 | 43.0% | link_latency |
| DeepSeek-V4.1-Flash | 134 | 110,684 | 124.3 | 292.3 | 445.3 | hybrid | 975.42 | 43.4% | link_latency |
| DeepSeek-V4.1-Flash | 141 | 116,466 | 124.3 | 291.6 | 443.4 | hybrid | 979.22 | 43.4% | link_latency |
| DeepSeek-V4.1-Flash | 150 | 123,900 | 124.3 | 290.7 | 444.0 | hybrid | 983.19 | 43.7% | link_latency |
| DeepSeek-V4.1-Flash | 153 | 126,378 | 124.3 | 290.4 | 437.7 | hybrid | 986.99 | 43.2% | link_latency |
| DeepSeek-V4.1-Flash | 154 | 127,204 | 124.3 | 290.3 | 438.9 | hybrid | 986.99 | 43.3% | link_latency |
| DeepSeek-V4.1-Flash | 157 | 129,682 | 124.3 | 290.0 | 442.3 | hybrid | 986.99 | 43.7% | link_latency |
| DeepSeek-V4.1-Flash | 168 | 138,768 | 124.3 | 288.9 | 444.9 | hybrid | 990.79 | 44.1% | link_latency |
| DeepSeek-V4.1-Flash | 169 | 139,594 | 124.3 | 288.8 | 437.0 | hybrid | 994.76 | 43.5% | link_latency |
| DeepSeek-V4.1-Flash | 193 | 159,418 | 124.3 | 286.2 | 435.6 | hybrid | 1,006.33 | 43.8% | link_latency |
| DeepSeek-V4.1-Flash | 203 | 167,678 | 124.3 | 285.2 | 436.8 | hybrid | 1,010.29 | 44.1% | link_latency |
| DeepSeek-V4.1-Flash | 204 | 168,504 | 124.3 | 285.1 | 437.7 | hybrid | 1,010.29 | 44.2% | link_latency |
| DeepSeek-V4.1-Flash | 209 | 172,634 | 124.3 | 284.6 | 434.6 | hybrid | 1,013.96 | 44.1% | link_latency |
| DeepSeek-V4.1-Flash | 224 | 185,024 | 124.3 | 283.1 | 439.6 | hybrid | 1,017.93 | 44.7% | link_latency |
| DeepSeek-V4.1-Flash | 225 | 185,850 | 124.3 | 282.9 | 433.6 | hybrid | 1,021.73 | 44.3% | link_latency |
| DeepSeek-V4.1-Flash | 243 | 200,718 | 124.3 | 281.1 | 433.9 | hybrid | 1,029.50 | 44.7% | link_latency |
| DeepSeek-V4.1-Flash | 309 | 255,234 | 124.3 | 274.2 | 429.9 | hybrid | 1,060.57 | 45.6% | link_latency |
| DeepSeek-V4.1-Flash | 312 | 257,712 | 124.3 | 273.9 | 431.5 | hybrid | 1,060.57 | 45.8% | link_latency |
| DeepSeek-V4.1-Flash | 314 | 259,364 | 124.3 | 273.7 | 427.6 | hybrid | 1,064.54 | 45.5% | link_latency |
| DeepSeek-V4.1-Flash | 335 | 276,710 | 124.3 | 226.8 | 430.3 | hybrid | 1,064.54 | 45.8% | link_latency |
| DeepSeek-V4.1-Flash | 336 | 277,536 | 124.3 | 226.8 | 430.7 | hybrid | 1,064.54 | 45.9% | link_latency |
| DeepSeek-V4.1-Flash | 337 | 278,362 | 124.3 | 226.7 | 427.3 | hybrid | 1,064.54 | 45.5% | link_latency |
| DeepSeek-V4.1-Flash | 448 | 370,048 | 124.3 | 219.1 | 430.7 | hybrid | 1,064.54 | 45.9% | link_latency |
| DeepSeek-V4.1-Flash | 672 | 555,072 | 124.3 | 205.1 | 430.7 | hybrid | 1,064.54 | 45.9% | link_latency |

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
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x156 | DeepSeek-V4.1-Flash | 156 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 4.34 us | 23,067.6 tok/s | 230,675.7 tok/s | 20 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.25 us; 19 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.09 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x110 | DeepSeek-V4.1-Flash | 110 | tensor | rom_package_ucie | rom_board_serdes | 160 | 260.97 us | 383.2 tok/s | 3,831.8 tok/s | 80 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.05 us; 80 x all_reduce span 55 on rom_board_serdes (traversals 15.4) = 258.92 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x152 | DeepSeek-V4.1-Flash | 152 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 10.44 us | 9,578.3 tok/s | 95,782.7 tok/s | 80 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.05 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 8.39 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x155 | DeepSeek-V4.1-Flash | 155 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x3 | DeepSeek-V4.1-Flash | 3 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-tensor-x110 | DeepSeek-V4.1-Flash | 110 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer | rom_wafer_serdes | 160 | 191.00 us | 523.6 tok/s | 5,235.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 37.00 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hybrid-x136 | DeepSeek-V4.1-Flash | 136 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4.1-Flash | 3 | hybrid | on_wafer | rom_wafer_serdes | 82 | 154.42 us | 647.6 tok/s | 6,475.8 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.42 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x316 | DeepSeek-V4.1-Flash | 316 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 4.34 us | 23,067.6 tok/s | 230,675.7 tok/s | 20 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.25 us; 19 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.09 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x125 | DeepSeek-V4.1-Flash | 125 | tensor | rom_package_ucie | rom_board_serdes | 160 | 260.97 us | 383.2 tok/s | 3,831.8 tok/s | 80 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.05 us; 80 x all_reduce span 63 on rom_board_serdes (traversals 15.4) = 258.92 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x246 | DeepSeek-V4.1-Flash | 246 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 10.44 us | 9,578.3 tok/s | 95,782.7 tok/s | 80 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.05 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 8.39 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-pipeline-x313 | DeepSeek-V4.1-Flash | 313 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6 | DeepSeek-V4.1-Flash | 6 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-tensor-x118 | DeepSeek-V4.1-Flash | 118 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-tensor-x6 | DeepSeek-V4.1-Flash | 6 | tensor | on_wafer | rom_wafer_serdes | 160 | 227.93 us | 438.7 tok/s | 4,387.3 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 6 on rom_wafer_serdes (traversals 4.4) = 73.93 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hybrid-x152 | DeepSeek-V4.1-Flash | 152 | hybrid | nvlink3 | infiniband_hdr | 98 | 451.08 us | 221.7 tok/s | 2,216.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 43.91 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | DeepSeek-V4.1-Flash | 6 | hybrid | on_wafer | rom_wafer_serdes | 85 | 155.05 us | 644.9 tok/s | 6,449.4 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 5 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 1.05 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x54-pipeline | DeepSeek-V4.1-Flash | 54 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x54-tensor | DeepSeek-V4.1-Flash | 54 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x54-hybrid | DeepSeek-V4.1-Flash | 54 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x54-expert | DeepSeek-V4.1-Flash | 54 | expert | nvlink3 | infiniband_hdr | 160 | 567.24 us | 176.3 tok/s | 1,762.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 166.04 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-expert | DeepSeek-V4.1-Flash | 56 | expert | nvlink3 | infiniband_hdr | 160 | 566.93 us | 176.4 tok/s | 1,763.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x58-pipeline | DeepSeek-V4.1-Flash | 58 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x58-tensor | DeepSeek-V4.1-Flash | 58 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x58-hybrid | DeepSeek-V4.1-Flash | 58 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x58-expert | DeepSeek-V4.1-Flash | 58 | expert | nvlink3 | infiniband_hdr | 160 | 566.81 us | 176.4 tok/s | 1,764.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-pipeline | DeepSeek-V4.1-Flash | 59 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-tensor | DeepSeek-V4.1-Flash | 59 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-hybrid | DeepSeek-V4.1-Flash | 59 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-expert | DeepSeek-V4.1-Flash | 59 | expert | nvlink3 | infiniband_hdr | 160 | 566.76 us | 176.4 tok/s | 1,764.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.73 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x109-pipeline | DeepSeek-V4.1-Flash | 109 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x109-tensor | DeepSeek-V4.1-Flash | 109 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x109-hybrid | DeepSeek-V4.1-Flash | 109 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x109-expert | DeepSeek-V4.1-Flash | 109 | expert | nvlink3 | infiniband_hdr | 160 | 564.76 us | 177.1 tok/s | 1,770.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.55 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.20 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4.1-Flash | 111 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4.1-Flash | 111 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4.1-Flash | 111 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-expert | DeepSeek-V4.1-Flash | 111 | expert | nvlink3 | infiniband_hdr | 160 | 564.72 us | 177.1 tok/s | 1,770.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.55 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.17 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4.1-Flash | 112 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4.1-Flash | 112 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4.1-Flash | 112 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-expert | DeepSeek-V4.1-Flash | 112 | expert | nvlink3 | infiniband_hdr | 160 | 564.67 us | 177.1 tok/s | 1,771.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.16 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-pipeline | DeepSeek-V4.1-Flash | 116 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-tensor | DeepSeek-V4.1-Flash | 116 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | DeepSeek-V4.1-Flash | 116 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-expert | DeepSeek-V4.1-Flash | 116 | expert | nvlink3 | infiniband_hdr | 160 | 564.61 us | 177.1 tok/s | 1,771.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.09 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x123-pipeline | DeepSeek-V4.1-Flash | 123 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x123-tensor | DeepSeek-V4.1-Flash | 123 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x123-hybrid | DeepSeek-V4.1-Flash | 123 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x123-expert | DeepSeek-V4.1-Flash | 123 | expert | nvlink3 | infiniband_hdr | 160 | 564.48 us | 177.2 tok/s | 1,771.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.00 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x131-pipeline | DeepSeek-V4.1-Flash | 131 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x131-tensor | DeepSeek-V4.1-Flash | 131 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x131-hybrid | DeepSeek-V4.1-Flash | 131 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x131-expert | DeepSeek-V4.1-Flash | 131 | expert | nvlink3 | infiniband_hdr | 160 | 564.35 us | 177.2 tok/s | 1,772.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.90 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x134-pipeline | DeepSeek-V4.1-Flash | 134 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x134-tensor | DeepSeek-V4.1-Flash | 134 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x134-hybrid | DeepSeek-V4.1-Flash | 134 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x134-expert | DeepSeek-V4.1-Flash | 134 | expert | nvlink3 | infiniband_hdr | 160 | 564.32 us | 177.2 tok/s | 1,772.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.87 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-pipeline | DeepSeek-V4.1-Flash | 141 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-tensor | DeepSeek-V4.1-Flash | 141 | tensor | nvlink3 | infiniband_hdr | 160 | 824.81 us | 121.2 tok/s | 1,212.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 417.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-hybrid | DeepSeek-V4.1-Flash | 141 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-expert | DeepSeek-V4.1-Flash | 141 | expert | nvlink3 | infiniband_hdr | 160 | 564.22 us | 177.2 tok/s | 1,772.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x150-pipeline | DeepSeek-V4.1-Flash | 150 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x150-tensor | DeepSeek-V4.1-Flash | 150 | tensor | nvlink3 | infiniband_hdr | 160 | 825.10 us | 121.2 tok/s | 1,212.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 417.93 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x150-hybrid | DeepSeek-V4.1-Flash | 150 | hybrid | nvlink3 | infiniband_hdr | 98 | 451.08 us | 221.7 tok/s | 2,216.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 43.91 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x150-expert | DeepSeek-V4.1-Flash | 150 | expert | nvlink3 | infiniband_hdr | 160 | 564.11 us | 177.3 tok/s | 1,772.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.40 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x153-pipeline | DeepSeek-V4.1-Flash | 153 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x153-tensor | DeepSeek-V4.1-Flash | 153 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x153-hybrid | DeepSeek-V4.1-Flash | 153 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x153-expert | DeepSeek-V4.1-Flash | 153 | expert | nvlink3 | infiniband_hdr | 160 | 564.06 us | 177.3 tok/s | 1,772.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.69 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x154-pipeline | DeepSeek-V4.1-Flash | 154 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x154-tensor | DeepSeek-V4.1-Flash | 154 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x154-hybrid | DeepSeek-V4.1-Flash | 154 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x154-expert | DeepSeek-V4.1-Flash | 154 | expert | nvlink3 | infiniband_hdr | 160 | 564.05 us | 177.3 tok/s | 1,772.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.68 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x157-pipeline | DeepSeek-V4.1-Flash | 157 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x157-tensor | DeepSeek-V4.1-Flash | 157 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x157-hybrid | DeepSeek-V4.1-Flash | 157 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x157-expert | DeepSeek-V4.1-Flash | 157 | expert | nvlink3 | infiniband_hdr | 160 | 564.03 us | 177.3 tok/s | 1,773.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.65 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4.1-Flash | 168 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4.1-Flash | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4.1-Flash | 168 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-expert | DeepSeek-V4.1-Flash | 168 | expert | nvlink3 | infiniband_hdr | 160 | 563.91 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-pipeline | DeepSeek-V4.1-Flash | 169 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-tensor | DeepSeek-V4.1-Flash | 169 | tensor | nvlink3 | infiniband_hdr | 160 | 825.80 us | 121.1 tok/s | 1,210.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 418.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-hybrid | DeepSeek-V4.1-Flash | 169 | hybrid | nvlink3 | infiniband_hdr | 101 | 458.40 us | 218.2 tok/s | 2,181.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 51.23 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-expert | DeepSeek-V4.1-Flash | 169 | expert | nvlink3 | infiniband_hdr | 160 | 563.90 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.56 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x193-pipeline | DeepSeek-V4.1-Flash | 193 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x193-tensor | DeepSeek-V4.1-Flash | 193 | tensor | nvlink3 | infiniband_hdr | 160 | 826.34 us | 121.0 tok/s | 1,210.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 419.17 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x193-hybrid | DeepSeek-V4.1-Flash | 193 | hybrid | nvlink3 | infiniband_hdr | 104 | 465.72 us | 214.7 tok/s | 2,147.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 58.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x193-expert | DeepSeek-V4.1-Flash | 193 | expert | nvlink3 | infiniband_hdr | 160 | 563.72 us | 177.4 tok/s | 1,773.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.30 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.42 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x203-pipeline | DeepSeek-V4.1-Flash | 203 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x203-tensor | DeepSeek-V4.1-Flash | 203 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x203-hybrid | DeepSeek-V4.1-Flash | 203 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x203-expert | DeepSeek-V4.1-Flash | 203 | expert | nvlink3 | infiniband_hdr | 160 | 563.66 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.37 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x204-pipeline | DeepSeek-V4.1-Flash | 204 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x204-tensor | DeepSeek-V4.1-Flash | 204 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x204-hybrid | DeepSeek-V4.1-Flash | 204 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x204-expert | DeepSeek-V4.1-Flash | 204 | expert | nvlink3 | infiniband_hdr | 160 | 563.65 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x209-pipeline | DeepSeek-V4.1-Flash | 209 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x209-tensor | DeepSeek-V4.1-Flash | 209 | tensor | nvlink3 | infiniband_hdr | 160 | 826.63 us | 121.0 tok/s | 1,209.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 419.46 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x209-hybrid | DeepSeek-V4.1-Flash | 209 | hybrid | nvlink3 | infiniband_hdr | 106 | 470.60 us | 212.5 tok/s | 2,125.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.43 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x209-expert | DeepSeek-V4.1-Flash | 209 | expert | nvlink3 | infiniband_hdr | 160 | 563.62 us | 177.4 tok/s | 1,774.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.28 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.34 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-expert | DeepSeek-V4.1-Flash | 224 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.28 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-pipeline | DeepSeek-V4.1-Flash | 225 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-tensor | DeepSeek-V4.1-Flash | 225 | tensor | nvlink3 | infiniband_hdr | 160 | 826.88 us | 120.9 tok/s | 1,209.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 419.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-hybrid | DeepSeek-V4.1-Flash | 225 | hybrid | nvlink3 | infiniband_hdr | 108 | 475.48 us | 210.3 tok/s | 2,103.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 68.31 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-expert | DeepSeek-V4.1-Flash | 225 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.27 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x243-pipeline | DeepSeek-V4.1-Flash | 243 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x243-tensor | DeepSeek-V4.1-Flash | 243 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x243-hybrid | DeepSeek-V4.1-Flash | 243 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x243-expert | DeepSeek-V4.1-Flash | 243 | expert | nvlink3 | infiniband_hdr | 160 | 563.45 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.21 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x309-pipeline | DeepSeek-V4.1-Flash | 309 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x309-tensor | DeepSeek-V4.1-Flash | 309 | tensor | nvlink3 | infiniband_hdr | 160 | 827.75 us | 120.8 tok/s | 1,208.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 39 on infiniband_hdr (traversals 2.0) = 420.58 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x309-hybrid | DeepSeek-V4.1-Flash | 309 | hybrid | nvlink3 | infiniband_hdr | 118 | 499.87 us | 200.1 tok/s | 2,000.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 38 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 92.70 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x309-expert | DeepSeek-V4.1-Flash | 309 | expert | nvlink3 | infiniband_hdr | 160 | 563.22 us | 177.5 tok/s | 1,775.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.04 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x312-pipeline | DeepSeek-V4.1-Flash | 312 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x312-tensor | DeepSeek-V4.1-Flash | 312 | tensor | nvlink3 | infiniband_hdr | 160 | 827.75 us | 120.8 tok/s | 1,208.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 39 on infiniband_hdr (traversals 2.0) = 420.58 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x312-hybrid | DeepSeek-V4.1-Flash | 312 | hybrid | nvlink3 | infiniband_hdr | 118 | 499.87 us | 200.1 tok/s | 2,000.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 38 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 92.70 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x312-expert | DeepSeek-V4.1-Flash | 312 | expert | nvlink3 | infiniband_hdr | 160 | 563.21 us | 177.6 tok/s | 1,775.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.18 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-pipeline | DeepSeek-V4.1-Flash | 314 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-tensor | DeepSeek-V4.1-Flash | 314 | tensor | nvlink3 | infiniband_hdr | 160 | 827.81 us | 120.8 tok/s | 1,208.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 40 on infiniband_hdr (traversals 2.0) = 420.65 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-hybrid | DeepSeek-V4.1-Flash | 314 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-expert | DeepSeek-V4.1-Flash | 314 | expert | nvlink3 | infiniband_hdr | 160 | 563.21 us | 177.6 tok/s | 1,775.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.18 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-pipeline | DeepSeek-V4.1-Flash | 335 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-tensor | DeepSeek-V4.1-Flash | 335 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid | DeepSeek-V4.1-Flash | 335 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-expert | DeepSeek-V4.1-Flash | 335 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-pipeline | DeepSeek-V4.1-Flash | 336 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-tensor | DeepSeek-V4.1-Flash | 336 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-hybrid | DeepSeek-V4.1-Flash | 336 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-expert | DeepSeek-V4.1-Flash | 336 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-pipeline | DeepSeek-V4.1-Flash | 337 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-tensor | DeepSeek-V4.1-Flash | 337 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.79 us | 86.7 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 43 on infiniband_hdr (traversals 4.0) = 745.62 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-hybrid | DeepSeek-V4.1-Flash | 337 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-expert | DeepSeek-V4.1-Flash | 337 | expert | nvlink3 | infiniband_hdr | 160 | 563.15 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.98 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4.1-Flash | 448 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4.1-Flash | 448 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.32 us | 86.7 tok/s | 867.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 746.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4.1-Flash | 448 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-expert | DeepSeek-V4.1-Flash | 448 | expert | nvlink3 | infiniband_hdr | 160 | 562.97 us | 177.6 tok/s | 1,776.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.13 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.84 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4.1-Flash | 672 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4.1-Flash | 672 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.90 us | 86.7 tok/s | 866.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 746.73 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4.1-Flash | 672 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-expert | DeepSeek-V4.1-Flash | 672 | expert | nvlink3 | infiniband_hdr | 160 | 562.78 us | 177.7 tok/s | 1,776.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.09 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.69 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash | 1 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 4,448.8 | 0.032 | 3,403.1 (167,890) | 4,448.8 (138,675) | 1.31x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 2 | wafer | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 4,188.8 | 0.015 | 3,403.1 (167,890) | 4,188.8 (277,350) | 1.23x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 4 | wafer | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 4,188.8 | 0.015 | 3,403.1 (167,890) | 4,188.8 (277,350) | 1.23x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 8 | wafer | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 4,188.8 | 0.015 | 3,403.1 (167,890) | 4,188.8 (277,350) | 1.23x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 16 | wafer | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 4,091.5 | 0.015 | 3,403.1 (167,890) | 4,091.5 (277,350) | 1.20x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 32 | wafer | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 4,116.3 | 0.007 | 3,538.0 (255,095) | 4,116.3 (554,700) | 1.16x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 64 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x313 | 255,095 | 3,508.1 | 0.014 | 3,508.1 (255,095) | 3,540.0 (554,700) | 1.01x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 256 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 2,381.0 | 0.009 | 2,381.0 (277,100) | 1,874.5 (554,700) | 0.79x | compute |
| DeepSeek-V4.1-Flash | 1024 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340 | 277,100 | 821.1 | 0.003 | 821.1 (277,100) | 597.6 (554,700) | 0.73x | compute |
| DeepSeek-V4.1-Flash | 4096 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340 | 277,100 | 220.2 | 0.001 | 220.2 (277,100) | 156.6 (554,700) | 0.71x | compute |

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
| DeepSeek-V4.1-Flash | 384 | 752.0 MB | 164.9 mm2 | 29.69 mm2 (18.0%) | 63,336 mm2 | 11,400 mm2 | 111,918 mm2 = 137.3 reticles |

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
| DeepSeek-V4.1-Flash | 1 | sram | 695,518.0 | 26,113.2 | 26,113.2 | 26.63x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | sram | 695,518.0 | 26,113.2 | 26,113.2 | 26.63x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | sram | 695,518.0 | 26,113.2 | 26,113.2 | 26.63x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | sram | 695,518.0 | 26,113.2 | 26,113.2 | 26.63x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | sram | 695,518.0 | 26,113.2 | 33,956.7 | 26.63x | 1.30x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | sram | 695,518.0 | 26,113.2 | 54,496.0 | 26.63x | 2.09x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | sram | 695,518.0 | 26,113.2 | 87,894.8 | 26.63x | 3.37x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 256 | sram | 695,518.0 | 26,113.2 | 171,672.8 | 26.63x | 6.57x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1024 | sram | 847,310.0 | 26,113.2 | 271,100.5 | 32.45x | 10.38x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | sram | 909,258.4 | 26,113.2 | 324,376.5 | 34.82x | 12.42x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash | 1 | rom | 583,059.6 | 158,063.2 | 158,063.2 | 3.69x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | rom | 583,059.6 | 158,063.2 | 158,063.2 | 3.69x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | rom | 583,059.6 | 158,063.2 | 158,063.2 | 3.69x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | rom | 583,059.6 | 158,063.2 | 158,063.2 | 3.69x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | rom | 583,059.6 | 158,063.2 | 158,063.2 | 3.69x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | rom | 583,059.6 | 158,063.2 | 158,063.2 | 3.69x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | rom | 583,059.6 | 158,063.2 | 171,644.8 | 3.69x | 1.09x | kv_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash | 256 | rom | 583,059.6 | 158,063.2 | 282,662.5 | 3.69x | 1.79x | kv_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash | 1024 | rom | 626,806.0 | 163,256.6 | 319,350.0 | 3.84x | 1.96x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash | 4096 | rom | 659,135.6 | 163,256.6 | 324,739.7 | 4.04x | 1.99x | compute | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash | 1 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 695,518.0 | 2.495 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 583,059.6 | 1.051 | kv_read | 0.84x |
| DeepSeek-V4.1-Flash | 1 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 1 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 1 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 1 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 2 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 695,518.0 | 2.495 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 2 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 583,059.6 | 1.051 | kv_read | 0.84x |
| DeepSeek-V4.1-Flash | 2 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 2 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 2 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 2 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 4 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 695,518.0 | 2.495 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 583,059.6 | 1.051 | kv_read | 0.84x |
| DeepSeek-V4.1-Flash | 4 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 4 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 4 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 4 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 8 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 695,518.0 | 2.495 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 8 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 583,059.6 | 1.051 | kv_read | 0.84x |
| DeepSeek-V4.1-Flash | 8 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 8 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 8 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 8 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 16 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 695,518.0 | 2.495 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 16 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 583,059.6 | 1.051 | kv_read | 0.84x |
| DeepSeek-V4.1-Flash | 16 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 16 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 16 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 1.19 | 33,956.7 | 0.122 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash | 16 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 32 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 695,518.0 | 2.495 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 32 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 583,059.6 | 1.051 | kv_read | 0.84x |
| DeepSeek-V4.1-Flash | 32 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 32 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 32 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 1.66 | 54,496.0 | 0.196 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash | 32 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 64 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 695,518.0 | 2.495 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 64 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 583,059.6 | 1.051 | kv_read | 0.84x |
| DeepSeek-V4.1-Flash | 64 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,113.2 | 0.094 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 64 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 64 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 2.18 | 87,894.8 | 0.317 | weight_read | 0.13x |
| DeepSeek-V4.1-Flash | 64 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 6.25 | 1.23 | 171,644.8 | 0.619 | kv_read | 0.25x |
| DeepSeek-V4.1-Flash | 256 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 695,518.0 | 2.495 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 256 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 583,059.6 | 1.051 | kv_read | 0.84x |
| DeepSeek-V4.1-Flash | 256 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x60-perstream | 48,900 | 1.00 | 4.27 | 26,113.2 | 0.534 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 256 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 158,063.2 | 0.570 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash | 256 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 4.02 | 171,672.8 | 0.619 | weight_read | 0.25x |
| DeepSeek-V4.1-Flash | 256 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 6.25 | 1.24 | 282,662.5 | 1.019 | kv_read | 0.41x |
| DeepSeek-V4.1-Flash | 1024 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 847,310.0 | 3.040 | compute | 1.00x |
| DeepSeek-V4.1-Flash | 1024 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 626,806.0 | 2.249 | compute | 0.74x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x60-perstream | 48,900 | 1.00 | 17.07 | 26,113.2 | 0.534 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 3.00 | 163,256.6 | 0.589 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash | 1024 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 4.20 | 271,100.5 | 0.977 | weight_read | 0.32x |
| DeepSeek-V4.1-Flash | 1024 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.25 | 319,350.0 | 1.151 | kv_read | 0.38x |
| DeepSeek-V4.1-Flash | 4096 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 909,258.4 | 3.262 | compute | 1.00x |
| DeepSeek-V4.1-Flash | 4096 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 659,135.6 | 2.365 | compute | 0.72x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x60-perstream | 48,900 | 1.00 | 68.27 | 26,113.2 | 0.534 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 12.01 | 163,256.6 | 0.589 | weight_read | 0.18x |
| DeepSeek-V4.1-Flash | 4096 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 6.09 | 324,376.5 | 1.170 | kv_read | 0.36x |
| DeepSeek-V4.1-Flash | 4096 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 2.26 | 324,739.7 | 1.171 | kv_read | 0.36x |

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
| DeepSeek-V4.1-Flash | 1 | 55 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 2 | 55 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 8 | 60 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 16 | 60 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 32 | 60 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 64 | 60 | 1.07 | 1.001 | 1.004 | 1.00x |
| DeepSeek-V4.1-Flash | 256 | 60 | 4.27 | 1.026 | 1.478 | 1.44x |
| DeepSeek-V4.1-Flash | 1024 | 60 | 17.07 | 1.131 | 2.623 | 2.32x |
| DeepSeek-V4.1-Flash | 4096 | 60 | 68.27 | 1.619 | 5.094 | 3.15x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | 1 | 54 | 5.73 | 4.85 | 1.18x |
| DeepSeek-V4.1-Flash | 2 | 54 | 10.77 | 6.91 | 1.56x |
| DeepSeek-V4.1-Flash | 4 | 54 | 19.16 | 9.71 | 1.97x |
| DeepSeek-V4.1-Flash | 8 | 54 | 30.91 | 13.18 | 2.35x |
| DeepSeek-V4.1-Flash | 16 | 54 | 43.08 | 17.13 | 2.52x |
| DeepSeek-V4.1-Flash | 32 | 54 | 50.85 | 21.12 | 2.41x |
| DeepSeek-V4.1-Flash | 64 | 54 | 53.43 | 24.56 | 2.18x |
| DeepSeek-V4.1-Flash | 256 | 54 | 53.95 | 27.77 | 1.94x |
| DeepSeek-V4.1-Flash | 1024 | 54 | 53.96 | 27.90 | 1.93x |
| DeepSeek-V4.1-Flash | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4.1-Flash | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4.1-Flash | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4.1-Flash | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4.1-Flash | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4.1-Flash | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4.1-Flash | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4.1-Flash | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4.1-Flash | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4.1-Flash | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4.1-Flash | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4.1-Flash | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4.1-Flash | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash | 1 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4.1-Flash | 2 | 59 | 10.87 | 7.07 | 1.54x |
| DeepSeek-V4.1-Flash | 4 | 59 | 19.48 | 9.96 | 1.96x |
| DeepSeek-V4.1-Flash | 8 | 59 | 31.87 | 13.62 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 59 | 45.33 | 17.83 | 2.54x |
| DeepSeek-V4.1-Flash | 32 | 59 | 54.61 | 22.12 | 2.47x |
| DeepSeek-V4.1-Flash | 64 | 59 | 58.09 | 25.86 | 2.25x |
| DeepSeek-V4.1-Flash | 256 | 59 | 58.91 | 29.37 | 2.01x |
| DeepSeek-V4.1-Flash | 1024 | 59 | 58.92 | 29.52 | 2.00x |
| DeepSeek-V4.1-Flash | 4096 | 59 | 58.92 | 29.52 | 2.00x |
| DeepSeek-V4.1-Flash | 1 | 109 | 5.86 | 5.33 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 109 | 11.33 | 8.23 | 1.38x |
| DeepSeek-V4.1-Flash | 4 | 109 | 21.18 | 11.62 | 1.82x |
| DeepSeek-V4.1-Flash | 8 | 109 | 37.31 | 16.87 | 2.21x |
| DeepSeek-V4.1-Flash | 16 | 109 | 59.45 | 22.98 | 2.59x |
| DeepSeek-V4.1-Flash | 32 | 109 | 82.15 | 29.70 | 2.77x |
| DeepSeek-V4.1-Flash | 64 | 109 | 97.48 | 35.94 | 2.71x |
| DeepSeek-V4.1-Flash | 256 | 109 | 105.63 | 42.13 | 2.51x |
| DeepSeek-V4.1-Flash | 1024 | 109 | 105.84 | 42.39 | 2.50x |
| DeepSeek-V4.1-Flash | 4096 | 109 | 105.84 | 42.39 | 2.50x |
| DeepSeek-V4.1-Flash | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 111 | 11.34 | 8.26 | 1.37x |
| DeepSeek-V4.1-Flash | 4 | 111 | 21.22 | 11.67 | 1.82x |
| DeepSeek-V4.1-Flash | 8 | 111 | 37.44 | 16.97 | 2.21x |
| DeepSeek-V4.1-Flash | 16 | 111 | 59.81 | 23.14 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 111 | 82.95 | 29.94 | 2.77x |
| DeepSeek-V4.1-Flash | 64 | 111 | 98.78 | 36.26 | 2.72x |
| DeepSeek-V4.1-Flash | 256 | 111 | 107.35 | 42.56 | 2.52x |
| DeepSeek-V4.1-Flash | 1024 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4.1-Flash | 4096 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4.1-Flash | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4.1-Flash | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4.1-Flash | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4.1-Flash | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4.1-Flash | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4.1-Flash | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4.1-Flash | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4.1-Flash | 4096 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4.1-Flash | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4.1-Flash | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4.1-Flash | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4.1-Flash | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4.1-Flash | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4.1-Flash | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash | 1 | 123 | 5.88 | 5.40 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 123 | 11.39 | 8.46 | 1.35x |
| DeepSeek-V4.1-Flash | 4 | 123 | 21.42 | 11.95 | 1.79x |
| DeepSeek-V4.1-Flash | 8 | 123 | 38.13 | 17.53 | 2.17x |
| DeepSeek-V4.1-Flash | 16 | 123 | 61.81 | 24.02 | 2.57x |
| DeepSeek-V4.1-Flash | 32 | 123 | 87.44 | 31.31 | 2.79x |
| DeepSeek-V4.1-Flash | 64 | 123 | 106.20 | 38.13 | 2.78x |
| DeepSeek-V4.1-Flash | 256 | 123 | 117.34 | 44.98 | 2.61x |
| DeepSeek-V4.1-Flash | 1024 | 123 | 117.65 | 45.27 | 2.60x |
| DeepSeek-V4.1-Flash | 4096 | 123 | 117.65 | 45.27 | 2.60x |
| DeepSeek-V4.1-Flash | 1 | 131 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 131 | 11.42 | 8.58 | 1.33x |
| DeepSeek-V4.1-Flash | 4 | 131 | 21.54 | 12.12 | 1.78x |
| DeepSeek-V4.1-Flash | 8 | 131 | 38.53 | 17.87 | 2.16x |
| DeepSeek-V4.1-Flash | 16 | 131 | 62.98 | 24.56 | 2.56x |
| DeepSeek-V4.1-Flash | 32 | 131 | 90.13 | 32.15 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 131 | 110.78 | 39.30 | 2.82x |
| DeepSeek-V4.1-Flash | 256 | 131 | 123.72 | 46.51 | 2.66x |
| DeepSeek-V4.1-Flash | 1024 | 131 | 124.09 | 46.82 | 2.65x |
| DeepSeek-V4.1-Flash | 4096 | 131 | 124.09 | 46.82 | 2.65x |
| DeepSeek-V4.1-Flash | 1 | 134 | 5.89 | 5.44 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 134 | 11.43 | 8.62 | 1.33x |
| DeepSeek-V4.1-Flash | 4 | 134 | 21.58 | 12.19 | 1.77x |
| DeepSeek-V4.1-Flash | 8 | 134 | 38.67 | 18.00 | 2.15x |
| DeepSeek-V4.1-Flash | 16 | 134 | 63.39 | 24.76 | 2.56x |
| DeepSeek-V4.1-Flash | 32 | 134 | 91.09 | 32.45 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 134 | 112.43 | 39.73 | 2.83x |
| DeepSeek-V4.1-Flash | 256 | 134 | 126.06 | 47.07 | 2.68x |
| DeepSeek-V4.1-Flash | 1024 | 134 | 126.45 | 47.38 | 2.67x |
| DeepSeek-V4.1-Flash | 4096 | 134 | 126.45 | 47.38 | 2.67x |
| DeepSeek-V4.1-Flash | 1 | 141 | 5.89 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 141 | 11.46 | 8.71 | 1.31x |
| DeepSeek-V4.1-Flash | 4 | 141 | 21.67 | 12.33 | 1.76x |
| DeepSeek-V4.1-Flash | 8 | 141 | 38.97 | 18.27 | 2.13x |
| DeepSeek-V4.1-Flash | 16 | 141 | 64.29 | 25.19 | 2.55x |
| DeepSeek-V4.1-Flash | 32 | 141 | 93.21 | 33.14 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 141 | 116.14 | 40.69 | 2.85x |
| DeepSeek-V4.1-Flash | 256 | 141 | 131.38 | 48.33 | 2.72x |
| DeepSeek-V4.1-Flash | 1024 | 141 | 131.83 | 48.65 | 2.71x |
| DeepSeek-V4.1-Flash | 4096 | 141 | 131.83 | 48.65 | 2.71x |
| DeepSeek-V4.1-Flash | 1 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 150 | 11.48 | 8.83 | 1.30x |
| DeepSeek-V4.1-Flash | 4 | 150 | 21.77 | 12.51 | 1.74x |
| DeepSeek-V4.1-Flash | 8 | 150 | 39.33 | 18.59 | 2.12x |
| DeepSeek-V4.1-Flash | 16 | 150 | 65.35 | 25.71 | 2.54x |
| DeepSeek-V4.1-Flash | 32 | 150 | 95.74 | 33.98 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 150 | 120.64 | 41.87 | 2.88x |
| DeepSeek-V4.1-Flash | 256 | 150 | 137.97 | 49.89 | 2.77x |
| DeepSeek-V4.1-Flash | 1024 | 150 | 138.50 | 50.23 | 2.76x |
| DeepSeek-V4.1-Flash | 4096 | 150 | 138.50 | 50.23 | 2.76x |
| DeepSeek-V4.1-Flash | 1 | 153 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 153 | 11.49 | 8.86 | 1.30x |
| DeepSeek-V4.1-Flash | 4 | 153 | 21.80 | 12.57 | 1.73x |
| DeepSeek-V4.1-Flash | 8 | 153 | 39.44 | 18.69 | 2.11x |
| DeepSeek-V4.1-Flash | 16 | 153 | 65.68 | 25.88 | 2.54x |
| DeepSeek-V4.1-Flash | 32 | 153 | 96.53 | 34.25 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 153 | 122.08 | 42.25 | 2.89x |
| DeepSeek-V4.1-Flash | 256 | 153 | 140.10 | 50.39 | 2.78x |
| DeepSeek-V4.1-Flash | 1024 | 153 | 140.67 | 50.74 | 2.77x |
| DeepSeek-V4.1-Flash | 4096 | 153 | 140.67 | 50.74 | 2.77x |
| DeepSeek-V4.1-Flash | 1 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 154 | 11.49 | 8.88 | 1.29x |
| DeepSeek-V4.1-Flash | 4 | 154 | 21.81 | 12.59 | 1.73x |
| DeepSeek-V4.1-Flash | 8 | 154 | 39.47 | 18.73 | 2.11x |
| DeepSeek-V4.1-Flash | 16 | 154 | 65.79 | 25.94 | 2.54x |
| DeepSeek-V4.1-Flash | 32 | 154 | 96.79 | 34.34 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 154 | 122.55 | 42.37 | 2.89x |
| DeepSeek-V4.1-Flash | 256 | 154 | 140.81 | 50.56 | 2.79x |
| DeepSeek-V4.1-Flash | 1024 | 154 | 141.38 | 50.91 | 2.78x |
| DeepSeek-V4.1-Flash | 4096 | 154 | 141.38 | 50.91 | 2.78x |
| DeepSeek-V4.1-Flash | 1 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 157 | 11.50 | 8.91 | 1.29x |
| DeepSeek-V4.1-Flash | 4 | 157 | 21.84 | 12.64 | 1.73x |
| DeepSeek-V4.1-Flash | 8 | 157 | 39.58 | 18.83 | 2.10x |
| DeepSeek-V4.1-Flash | 16 | 157 | 66.10 | 26.10 | 2.53x |
| DeepSeek-V4.1-Flash | 32 | 157 | 97.56 | 34.60 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 157 | 123.95 | 42.74 | 2.90x |
| DeepSeek-V4.1-Flash | 256 | 157 | 142.90 | 51.05 | 2.80x |
| DeepSeek-V4.1-Flash | 1024 | 157 | 143.50 | 51.41 | 2.79x |
| DeepSeek-V4.1-Flash | 4096 | 157 | 143.50 | 51.41 | 2.79x |
| DeepSeek-V4.1-Flash | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4.1-Flash | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4.1-Flash | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4.1-Flash | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4.1-Flash | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4.1-Flash | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4.1-Flash | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4.1-Flash | 4096 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4.1-Flash | 1 | 169 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 169 | 11.53 | 9.04 | 1.27x |
| DeepSeek-V4.1-Flash | 4 | 169 | 21.95 | 12.86 | 1.71x |
| DeepSeek-V4.1-Flash | 8 | 169 | 39.96 | 19.20 | 2.08x |
| DeepSeek-V4.1-Flash | 16 | 169 | 67.27 | 26.73 | 2.52x |
| DeepSeek-V4.1-Flash | 32 | 169 | 100.44 | 35.62 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 169 | 129.24 | 44.17 | 2.93x |
| DeepSeek-V4.1-Flash | 256 | 169 | 150.98 | 52.97 | 2.85x |
| DeepSeek-V4.1-Flash | 1024 | 169 | 151.70 | 53.34 | 2.84x |
| DeepSeek-V4.1-Flash | 4096 | 169 | 151.70 | 53.34 | 2.84x |
| DeepSeek-V4.1-Flash | 1 | 193 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 193 | 11.58 | 9.28 | 1.25x |
| DeepSeek-V4.1-Flash | 4 | 193 | 22.13 | 13.28 | 1.67x |
| DeepSeek-V4.1-Flash | 8 | 193 | 40.59 | 19.83 | 2.05x |
| DeepSeek-V4.1-Flash | 16 | 193 | 69.24 | 27.89 | 2.48x |
| DeepSeek-V4.1-Flash | 32 | 193 | 105.38 | 37.51 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 193 | 138.62 | 46.82 | 2.96x |
| DeepSeek-V4.1-Flash | 256 | 193 | 165.80 | 56.49 | 2.93x |
| DeepSeek-V4.1-Flash | 1024 | 193 | 166.74 | 56.91 | 2.93x |
| DeepSeek-V4.1-Flash | 4096 | 193 | 166.74 | 56.91 | 2.93x |
| DeepSeek-V4.1-Flash | 1 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 203 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4.1-Flash | 4 | 203 | 22.19 | 13.44 | 1.65x |
| DeepSeek-V4.1-Flash | 8 | 203 | 40.82 | 20.06 | 2.03x |
| DeepSeek-V4.1-Flash | 16 | 203 | 69.94 | 28.35 | 2.47x |
| DeepSeek-V4.1-Flash | 32 | 203 | 107.17 | 38.24 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 203 | 142.11 | 47.84 | 2.97x |
| DeepSeek-V4.1-Flash | 256 | 203 | 171.48 | 57.86 | 2.96x |
| DeepSeek-V4.1-Flash | 1024 | 203 | 172.53 | 58.30 | 2.96x |
| DeepSeek-V4.1-Flash | 4096 | 203 | 172.53 | 58.30 | 2.96x |
| DeepSeek-V4.1-Flash | 1 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 204 | 11.59 | 9.37 | 1.24x |
| DeepSeek-V4.1-Flash | 4 | 204 | 22.20 | 13.45 | 1.65x |
| DeepSeek-V4.1-Flash | 8 | 204 | 40.84 | 20.08 | 2.03x |
| DeepSeek-V4.1-Flash | 16 | 204 | 70.00 | 28.39 | 2.47x |
| DeepSeek-V4.1-Flash | 32 | 204 | 107.35 | 38.32 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 204 | 142.45 | 47.95 | 2.97x |
| DeepSeek-V4.1-Flash | 256 | 204 | 172.04 | 58.00 | 2.97x |
| DeepSeek-V4.1-Flash | 1024 | 204 | 173.09 | 58.43 | 2.96x |
| DeepSeek-V4.1-Flash | 4096 | 204 | 173.09 | 58.43 | 2.96x |
| DeepSeek-V4.1-Flash | 1 | 209 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 209 | 11.60 | 9.41 | 1.23x |
| DeepSeek-V4.1-Flash | 4 | 209 | 22.23 | 13.53 | 1.64x |
| DeepSeek-V4.1-Flash | 8 | 209 | 40.94 | 20.19 | 2.03x |
| DeepSeek-V4.1-Flash | 16 | 209 | 70.33 | 28.61 | 2.46x |
| DeepSeek-V4.1-Flash | 32 | 209 | 108.19 | 38.67 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 209 | 144.10 | 48.44 | 2.97x |
| DeepSeek-V4.1-Flash | 256 | 209 | 174.76 | 58.66 | 2.98x |
| DeepSeek-V4.1-Flash | 1024 | 209 | 175.86 | 59.11 | 2.98x |
| DeepSeek-V4.1-Flash | 4096 | 209 | 175.86 | 59.11 | 2.98x |
| DeepSeek-V4.1-Flash | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4.1-Flash | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4.1-Flash | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4.1-Flash | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4.1-Flash | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4.1-Flash | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4.1-Flash | 4096 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4.1-Flash | 1 | 225 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 225 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4.1-Flash | 4 | 225 | 22.31 | 13.77 | 1.62x |
| DeepSeek-V4.1-Flash | 8 | 225 | 41.24 | 20.52 | 2.01x |
| DeepSeek-V4.1-Flash | 16 | 225 | 71.28 | 29.30 | 2.43x |
| DeepSeek-V4.1-Flash | 32 | 225 | 110.68 | 39.76 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 225 | 149.06 | 49.97 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 225 | 183.07 | 60.72 | 3.02x |
| DeepSeek-V4.1-Flash | 1024 | 225 | 184.32 | 61.18 | 3.01x |
| DeepSeek-V4.1-Flash | 4096 | 225 | 184.32 | 61.18 | 3.01x |
| DeepSeek-V4.1-Flash | 1 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 243 | 11.64 | 9.66 | 1.21x |
| DeepSeek-V4.1-Flash | 4 | 243 | 22.39 | 14.03 | 1.60x |
| DeepSeek-V4.1-Flash | 8 | 243 | 41.53 | 20.84 | 1.99x |
| DeepSeek-V4.1-Flash | 16 | 243 | 72.22 | 30.04 | 2.40x |
| DeepSeek-V4.1-Flash | 32 | 243 | 113.17 | 40.91 | 2.77x |
| DeepSeek-V4.1-Flash | 64 | 243 | 154.10 | 51.56 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 243 | 191.70 | 62.89 | 3.05x |
| DeepSeek-V4.1-Flash | 1024 | 243 | 193.12 | 63.38 | 3.05x |
| DeepSeek-V4.1-Flash | 4096 | 243 | 193.12 | 63.38 | 3.05x |
| DeepSeek-V4.1-Flash | 1 | 309 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 2 | 309 | 11.70 | 10.02 | 1.17x |
| DeepSeek-V4.1-Flash | 4 | 309 | 22.61 | 14.88 | 1.52x |
| DeepSeek-V4.1-Flash | 8 | 309 | 42.33 | 21.81 | 1.94x |
| DeepSeek-V4.1-Flash | 16 | 309 | 74.82 | 32.43 | 2.31x |
| DeepSeek-V4.1-Flash | 32 | 309 | 120.22 | 44.37 | 2.71x |
| DeepSeek-V4.1-Flash | 64 | 309 | 168.82 | 56.52 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 309 | 218.01 | 69.81 | 3.12x |
| DeepSeek-V4.1-Flash | 1024 | 309 | 220.00 | 70.39 | 3.13x |
| DeepSeek-V4.1-Flash | 4096 | 309 | 220.00 | 70.39 | 3.13x |
| DeepSeek-V4.1-Flash | 1 | 312 | 5.95 | 5.75 | 1.04x |
| DeepSeek-V4.1-Flash | 2 | 312 | 11.70 | 10.03 | 1.17x |
| DeepSeek-V4.1-Flash | 4 | 312 | 22.62 | 14.91 | 1.52x |
| DeepSeek-V4.1-Flash | 8 | 312 | 42.36 | 21.85 | 1.94x |
| DeepSeek-V4.1-Flash | 16 | 312 | 74.91 | 32.53 | 2.30x |
| DeepSeek-V4.1-Flash | 32 | 312 | 120.48 | 44.50 | 2.71x |
| DeepSeek-V4.1-Flash | 64 | 312 | 169.38 | 56.73 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 312 | 219.04 | 70.09 | 3.13x |
| DeepSeek-V4.1-Flash | 1024 | 312 | 221.05 | 70.68 | 3.13x |
| DeepSeek-V4.1-Flash | 4096 | 312 | 221.05 | 70.68 | 3.13x |
| DeepSeek-V4.1-Flash | 1 | 314 | 5.95 | 5.75 | 1.04x |
| DeepSeek-V4.1-Flash | 2 | 314 | 11.70 | 10.04 | 1.17x |
| DeepSeek-V4.1-Flash | 4 | 314 | 22.62 | 14.94 | 1.51x |
| DeepSeek-V4.1-Flash | 8 | 314 | 42.38 | 21.88 | 1.94x |
| DeepSeek-V4.1-Flash | 16 | 314 | 74.97 | 32.59 | 2.30x |
| DeepSeek-V4.1-Flash | 32 | 314 | 120.65 | 44.59 | 2.71x |
| DeepSeek-V4.1-Flash | 64 | 314 | 169.75 | 56.86 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 314 | 219.72 | 70.28 | 3.13x |
| DeepSeek-V4.1-Flash | 1024 | 314 | 221.75 | 70.87 | 3.13x |
| DeepSeek-V4.1-Flash | 4096 | 314 | 221.75 | 70.87 | 3.13x |
| DeepSeek-V4.1-Flash | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 335 | 11.71 | 10.13 | 1.16x |
| DeepSeek-V4.1-Flash | 4 | 335 | 22.67 | 15.17 | 1.49x |
| DeepSeek-V4.1-Flash | 8 | 335 | 42.57 | 22.14 | 1.92x |
| DeepSeek-V4.1-Flash | 16 | 335 | 75.58 | 33.24 | 2.27x |
| DeepSeek-V4.1-Flash | 32 | 335 | 122.34 | 45.48 | 2.69x |
| DeepSeek-V4.1-Flash | 64 | 335 | 173.40 | 58.23 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 335 | 226.52 | 72.22 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4.1-Flash | 4096 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4.1-Flash | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 336 | 11.71 | 10.14 | 1.16x |
| DeepSeek-V4.1-Flash | 4 | 336 | 22.68 | 15.18 | 1.49x |
| DeepSeek-V4.1-Flash | 8 | 336 | 42.57 | 22.15 | 1.92x |
| DeepSeek-V4.1-Flash | 16 | 336 | 75.61 | 33.27 | 2.27x |
| DeepSeek-V4.1-Flash | 32 | 336 | 122.42 | 45.52 | 2.69x |
| DeepSeek-V4.1-Flash | 64 | 336 | 173.56 | 58.30 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 336 | 226.83 | 72.31 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4.1-Flash | 4096 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4.1-Flash | 1 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 337 | 11.72 | 10.14 | 1.16x |
| DeepSeek-V4.1-Flash | 4 | 337 | 22.68 | 15.19 | 1.49x |
| DeepSeek-V4.1-Flash | 8 | 337 | 42.58 | 22.16 | 1.92x |
| DeepSeek-V4.1-Flash | 16 | 337 | 75.64 | 33.30 | 2.27x |
| DeepSeek-V4.1-Flash | 32 | 337 | 122.49 | 45.56 | 2.69x |
| DeepSeek-V4.1-Flash | 64 | 337 | 173.73 | 58.36 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 337 | 227.14 | 72.40 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 337 | 229.35 | 73.00 | 3.14x |
| DeepSeek-V4.1-Flash | 4096 | 337 | 229.35 | 73.00 | 3.14x |
| DeepSeek-V4.1-Flash | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 2 | 448 | 11.76 | 10.50 | 1.12x |
| DeepSeek-V4.1-Flash | 4 | 448 | 22.87 | 16.25 | 1.41x |
| DeepSeek-V4.1-Flash | 8 | 448 | 43.27 | 23.34 | 1.85x |
| DeepSeek-V4.1-Flash | 16 | 448 | 77.94 | 36.03 | 2.16x |
| DeepSeek-V4.1-Flash | 32 | 448 | 129.03 | 49.47 | 2.61x |
| DeepSeek-V4.1-Flash | 64 | 448 | 188.21 | 64.80 | 2.90x |
| DeepSeek-V4.1-Flash | 256 | 448 | 255.15 | 81.21 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4.1-Flash | 4096 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4.1-Flash | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash | 2 | 672 | 11.81 | 10.91 | 1.08x |
| DeepSeek-V4.1-Flash | 4 | 672 | 23.06 | 17.73 | 1.30x |
| DeepSeek-V4.1-Flash | 8 | 672 | 43.98 | 25.33 | 1.74x |
| DeepSeek-V4.1-Flash | 16 | 672 | 80.37 | 39.17 | 2.05x |
| DeepSeek-V4.1-Flash | 32 | 672 | 136.13 | 55.89 | 2.44x |
| DeepSeek-V4.1-Flash | 64 | 672 | 204.63 | 73.69 | 2.78x |
| DeepSeek-V4.1-Flash | 256 | 672 | 288.80 | 93.78 | 3.08x |
| DeepSeek-V4.1-Flash | 1024 | 672 | 292.67 | 94.67 | 3.09x |
| DeepSeek-V4.1-Flash | 4096 | 672 | 292.67 | 94.67 | 3.09x |

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
| gpu | DeepSeek-V4.1-Flash | 1 | 368.98 | 16.8% |
| rom | DeepSeek-V4.1-Flash | 1 | 152.80 | 68.0% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash | sram | interleaved | 128 B | 1.85x |
| DeepSeek-V4.1-Flash | hbm | interleaved | 32 B | 1.39x |

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
| DeepSeek-V4.1-Flash | 1 | 55 | 41.86% | 80.99 | 3.52 |
| DeepSeek-V4.1-Flash | 2 | 55 | 41.86% | 80.99 | 3.52 |
| DeepSeek-V4.1-Flash | 4 | 1 | 18.49% | 37.07 | 3.52 |

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
| DeepSeek-V4.1-Flash | 1 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 184.5 | 21,774.0 |
| DeepSeek-V4.1-Flash | 2 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 184.5 | 21,774.0 |
| DeepSeek-V4.1-Flash | 4 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 184.5 | 21,774.0 |
| DeepSeek-V4.1-Flash | 8 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 184.5 | 21,774.0 |
| DeepSeek-V4.1-Flash | 16 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 184.5 | 21,774.0 |
| DeepSeek-V4.1-Flash | 32 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 184.5 | 21,774.0 |
| DeepSeek-V4.1-Flash | 64 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 184.5 | 21,774.0 |
| DeepSeek-V4.1-Flash | 256 | 3.36% | 18.2 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 85.5 | 21,885.8 |
| DeepSeek-V4.1-Flash | 1024 | 12.77% | 45.4 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 21.4 | 21,920.5 |
| DeepSeek-V4.1-Flash | 4096 | 42.11% | 130.1 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 5.3 | 21,888.7 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 2 |
| gpu | infeasible | 9 |
| gpu | link_latency | 780 |
| gpu | weight_read | 529 |
| rom | compute | 684 |
| rom | infeasible | 2104 |
| rom | kv_read | 125 |
| rom | layer_fixed_latency | 345 |
| rom | link_latency | 958 |
| rom | weight_read | 244 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 9 |
| rom | CAPACITY | 2104 |

## Mechanical consistency audit

**FAIL** over 116,969 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x110', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x133', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x136', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x152', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x155', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x156', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x159', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x212', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x318', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x110', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x133', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x136', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x152', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x155', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x156', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x159', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x212', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x318', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x110', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x133', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x136', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x152', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x155', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x156', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x159', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x212', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x318', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x110', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x133', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x136', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x152', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x155', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x156', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x159', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x212', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 52 |
| assumed | 86 |

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
- `links.rom_package_ucie.relay_latency_s`
- `links.rom_package_ucie_diagonal.hop_latency_s`
- `links.rom_wafer_express.fabric`
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

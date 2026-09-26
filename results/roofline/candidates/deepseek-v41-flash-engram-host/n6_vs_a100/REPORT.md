# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash-engram-host

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash-engram-host at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 24x (ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream, 114 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 2 devices. On the GPU side the correction reaches 16x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 15 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-host takes 2 x 46,225 mm2 (92,450 mm2, wafer, KV in HBM) at 5,081 tok/s per user and 55 tok/s per 1,000 mm2, holding 6,853 sessions, against 112 copies of one unified HBM die at the same silicon: 11.2x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-host on 369,800 mm2 of ROM silicon at 5,062 tok/s per user against 370,048 mm2 of a100_sxm_80gb-x448-hybrid at 433 tok/s: **11.7x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 27,412 resident sessions against the GPU cluster's 176,800. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on DeepSeek-V4.1-Flash-engram-host at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 1,172 us of link latency per token; but the model has 40 layers, so at most 40 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 1,065 us. The iso-area per-user ratio at that point falls from 12.2x to 11.7x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 3.61x to it.** At 52,160 mm2 on DeepSeek-V4.1-Flash-engram-host the pipeline-only GPU delivers 126.10 tok/s and the same silicon running hybrid delivers 455 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.01x (DeepSeek-V4.1-Flash-engram-host, ROM binding on `link_latency`) to 11.07x (DeepSeek-V4.1-Flash-engram-host, ROM binding on `weight_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-host engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 333 to 24,056 tok/s, and its rate with every slot occupied from 23,631 to 24,056. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 71 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 191.0 us and cap it at 5,236 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 10 of 10 operating points and an array 0; on tokens per second per square millimetre the same points go 3 to the array and 7 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 151 of 4468 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 75.7x of aggregate throughput (DeepSeek-V4.1-Flash-engram-host). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 16.46x, on DeepSeek-V4.1-Flash-engram-host at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4.1-Flash-engram-host at 200,000 tokens

**Recommended: `ROM-N6-native-HBMKV-wafer-hybrid-x2`** -- 2 x 46,225 mm2 wafers, 92,450 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **5,080.8 tok/s per user** (0.20 ms/token), binding on `layer_fixed_latency`
- **55.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 76,212 tok/s aggregate with every slot full, over 6,853 resident sessions (fill limited by `pipeline_slots`)
- 9,289 W at 0.100 W/mm2, 1,656.4 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 112 copies of one unified HBM die -- `a100_sxm_80gb-x112-hybrid`, 92,512 mm2, area ratio 0.9993 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 92,450 | 92,512 | 0.9993 |
| user tok/s | 5,080.8 | 453.3 | 11.21x |
| aggregate tok/s | 76,212 | 6,346 | 5.40x |
| resident sessions | 6,853 | 42,923 | -- |
| J/token | 1.6564 | 37.0552 | 22.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 6,853 sessions against one that holds 42,923 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 458.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 5,080.8 | 55.0 | 6,853 | 11.21x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | 36.7 | 10,279 | 11.36x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 52,160 | 1,297.5 | 24.9 | 1 | 2.85x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 5,080.8 | 55.0 | 6,853 | 11.21x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 5,080.8 | 55.0 | -- | 55.0 | ACCEPT |
| `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | 36.7 | 0.1 | 55.0 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-wafer-hybrid-x2` **<-- recommended** | 92,450 | 2 | 5,080.8 | 76,212 | 55.0 | 6,853 | `layer_fixed_latency` | 9,289 | 1,656.4 | `a100_sxm_80gb-x112-hybrid` | 11.21x |
| `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 3 | 5,084.7 | 111,864 | 36.7 | 10,279 | `layer_fixed_latency` | 14,267 | 2,548.2 | `a100_sxm_80gb-x168-hybrid` | 11.36x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 348 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 65,200 | 3,405.4 | 52.2 | 1 |
| array | 348 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,024.9 | 35.8 | 54,985 |
| array | 348 | smallest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x64` | 52,160 | 1,297.5 | 24.9 | 1 |
| wafer | 72 | densest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 5,080.8 | 55.0 | 6,853 |
| wafer | 72 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | 36.7 | 10,279 |
| wafer | 72 | smallest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 5,080.8 | 55.0 | 6,853 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,024.9 | 140,870 | 54,985 | 14,676 | 3,229.2 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 450.9 | 52,486 | 44,930.6 | 1.001 | 8.93x | 13.9x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | 111,864 | 10,279 | 14,267 | 2,548.2 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 55,550.9 | 0.999 | 11.36x | 21.8x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 3,928.2 | 168,914 | 67,735 | 17,460 | 3,929.5 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 55,550.9 | 0.998 | 8.77x | 14.1x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | -- | 10,279 | -- | 2,548.2 | -- | -- | -- | -- | -- | 0.999 | 1.29x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,024.9 | 140,870 | 54,985 | 14,676 | 1,620.7 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 450.9 | 52,486 | 23,154.8 | 1.001 | 8.93x | 14.3x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | 111,864 | 10,279 | 14,267 | 1,280.2 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 28,464.9 | 0.999 | 11.36x | 22.2x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 3,928.2 | 168,914 | 67,735 | 17,460 | 1,970.9 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 28,464.9 | 0.998 | 8.77x | 14.4x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | -- | 10,279 | -- | 1,280.2 | -- | -- | -- | -- | -- | 0.999 | 1.29x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,024.9 | 140,870 | 54,985 | 14,676 | 816.5 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 450.9 | 52,486 | 12,266.9 | 1.001 | 8.93x | 15.0x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | 111,864 | 10,279 | 14,267 | 646.2 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 14,921.9 | 0.999 | 11.36x | 23.1x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 3,928.2 | 168,914 | 67,735 | 17,460 | 991.6 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 14,921.9 | 0.998 | 8.77x | 15.0x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | -- | 10,279 | -- | 646.2 | -- | -- | -- | -- | -- | 0.999 | 1.29x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,024.9 | 140,870 | 54,985 | 14,676 | 414.4 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 450.9 | 52,486 | 6,822.9 | 1.001 | 8.93x | 16.5x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | 111,864 | 10,279 | 14,267 | 329.3 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 8,150.5 | 0.999 | 11.36x | 24.8x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 3,928.2 | 168,914 | 67,735 | 17,460 | 501.9 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 8,150.5 | 0.998 | 8.77x | 16.2x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | -- | 10,279 | -- | 329.3 | -- | -- | -- | -- | -- | 0.999 | 1.29x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,024.9 | 140,870 | 54,985 | 14,676 | 213.3 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 450.9 | 52,486 | 4,100.9 | 1.001 | 8.93x | 19.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | 111,864 | 10,279 | 14,267 | 170.8 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 4,764.7 | 0.999 | 11.36x | 27.9x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 3,928.2 | 168,914 | 67,735 | 17,460 | 257.1 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 447.8 | 65,236 | 4,764.7 | 0.998 | 8.77x | 18.5x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,084.7 | -- | 10,279 | -- | 170.8 | -- | -- | -- | -- | -- | 0.999 | 1.29x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | 4,024.9 | 140,870 | 54,985 | 14,676 | 112.8 | `layer_fixed_latency` | `a100_sxm_80gb-x136-hybrid` | 396.2 | 52,486 | 2,504.6 | 1.001 | 10.16x | 22.2x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,062.4 | 288,559 | 27,412 | 37,926 | 224.5 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 433.5 | 176,800 | 6,042.4 | 0.999 | 11.68x | 26.9x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 3,937.8 | 271,706 | 109,970 | 28,316 | 111.4 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 382.0 | 106,674 | 2,561.9 | 1.001 | 10.31x | 23.0x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,059.2 | 435,089 | 41,119 | 56,917 | 171.6 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 433.5 | 266,051 | 4,876.5 | 0.999 | 11.67x | 28.4x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 2,960.5 | 757,892 | 135,470 | 39,398 | 52.0 | `compute` | `a100_sxm_80gb-x335-hybrid` | 234.9 | 131,776 | 1,415.8 | 1.001 | 12.60x | 27.2x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,982.8 | 1,019,597 | 41,119 | 63,188 | 62.0 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 322.5 | 266,051 | 1,944.7 | 0.999 | 12.35x | 31.4x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,129.9 | 1,157,066 | 135,470 | 42,906 | 37.1 | `compute` | `a100_sxm_80gb-x335-hybrid` | 97.7 | 131,776 | 1,000.9 | 1.001 | 11.57x | 27.0x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,978.0 | 2,025,474 | 41,119 | 74,627 | 36.8 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 155.6 | 266,051 | 1,126.2 | 0.999 | 12.71x | 30.6x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 401.3 | 1,643,561 | 135,470 | 55,280 | 33.6 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 37.2 | 131,776 | 579.4 | 1.001 | 10.77x | 17.2x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 602.8 | 2,469,078 | 41,119 | 76,302 | 30.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 59.3 | 266,051 | 842.0 | 0.999 | 10.16x | 27.2x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-64 | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | wafer | HBM | 6,853 |
| 256 | `ROM-N6-native-HBMKV-array-hw-pipeline-x138` | 112,470 | array | HBM | 54,985 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-pipeline-x207` | 168,705 | array | HBM | 82,477 |
| 4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x276` | 224,940 | array | HBM | 109,970 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-host | HBM | rom | 71, 72, 86, 87, 104, 113, 119, 123, 124, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-host | HBM | sram | 71, 72, 86, 87, 104, 113, 124, 132, 134, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-host | SRAM | rom | 64, 69, 76, 80, 83, 85, 96, 113, 128, 170, 192, 227, 256, 340 |
| DeepSeek-V4.1-Flash-engram-host | SRAM | sram | 64, 69, 76, 80, 83, 85, 96, 113, 128, 170, 192, 227, 256, 340 |

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
| DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1 | 8 on `rom_wafer_express` | 5.25 | one_shot | 149.56 | 24.12 | 33.07 | 21.57 | 5,080.8 |
| DeepSeek-V4.1-Flash-engram-host | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 64 | 2 on `rom_wafer_express` | 5.25 | one_shot | 147.98 | 7.51 | 141.08 | 16.83 | 3,483.7 |
| DeepSeek-V4.1-Flash-engram-host | `a100_sxm_80gb-x112-hybrid` | 1 | 8 | 5.25 | measured_floor | 368.98 | 963.69 | 991.29 | 448.93 | 453.3 |
| DeepSeek-V4.1-Flash-engram-host | `a100_sxm_80gb-x112-hybrid` | 64 | 8 | 5.25 | measured_floor | 370.98 | 1,095.69 | 2,184.89 | 493.55 | 293.4 |

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

- **0 of 4,468 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 35%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 240 | 0 | 56.6% | 80.3% | 0.389 | 66% |
| gpu | wafer (>=40,000 mm2) | 1,280 | 0 | 54.8% | 79.8% | 0.387 | 85% |
| rom | large array (5,000-40,000 mm2) | 432 | 0 | 19.0% | 36.3% | 0.181 | 94% |
| rom | wafer (>=40,000 mm2) | 2,516 | 0 | 22.4% | 41.2% | 0.206 | 95% |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 92,450 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.656398 | 9,288.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x112-hybrid` | 37.055227 | 24,921.7 | link_latency | 22.37x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 92,450 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 0.834334 | 9,288.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x112-hybrid` | 19.217097 | 24,921.7 | link_latency | 23.03x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 92,450 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 0.423302 | 9,288.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x112-hybrid` | 10.298032 | 24,921.7 | link_latency | 24.33x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 92,450 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 0.217786 | 9,288.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x112-hybrid` | 5.838500 | 24,921.7 | link_latency | 26.81x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 138,675 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 0.170765 | 14,267.1 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-hybrid` | 4.764712 | 37,223.2 | link_latency | 27.90x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 277,350 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 0.171566 | 28,458.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x336-hybrid` | 4.876513 | 73,617.4 | link_latency | 28.42x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 554,700 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.171566 | 56,916.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-hybrid` | 4.876513 | 147,234.8 | link_latency | 28.42x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 554,700 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.061974 | 63,188.5 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-hybrid` | 1.944745 | 160,558.3 | weight_read | 31.38x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 554,700 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.036844 | 74,626.8 | kv_read | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-hybrid` | 1.126228 | 179,443.7 | weight_read | 30.57x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 554,700 | `DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.030903 | 76,302.1 | kv_read | `DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-hybrid` | 0.841975 | 204,523.4 | weight_read | 27.25x |

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
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 552 B | 307.5 GB | 4.46 | 0.047 GB | 0.181 GB | 278.7 |

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
| DeepSeek-V4.1-Flash-engram-host | 2 | 92,450 | 6,336.2 | wafer-pipeline | 5,080.8 | wafer-hybrid | 1.25x | 1,864.7 | pipeline | 453.3 | hybrid | 4.11x | 3.40x | 11.21x | 3.30x |
| DeepSeek-V4.1-Flash-engram-host | 3 | 138,675 | 6,347.5 | wafer-pipeline | 5,084.7 | wafer-hybrid | 1.25x | 1,940.5 | pipeline | 447.8 | hybrid | 4.33x | 3.27x | 11.36x | 3.47x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 184,900 | 6,350.9 | wafer-pipeline | 5,075.2 | wafer-hybrid | 1.25x | 1,980.7 | pipeline | 442.4 | hybrid | 4.48x | 3.21x | 11.47x | 3.58x |
| DeepSeek-V4.1-Flash-engram-host | 6 | 277,350 | 6,355.1 | wafer-pipeline | 5,059.2 | wafer-hybrid | 1.26x | 2,022.7 | pipeline | 433.5 | hybrid | 4.67x | 3.14x | 11.67x | 3.71x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 369,800 | 6,356.3 | wafer-pipeline | 5,062.4 | wafer-hybrid | 1.26x | 2,044.4 | pipeline | 433.5 | hybrid | 4.72x | 3.11x | 11.68x | 3.76x |
| DeepSeek-V4.1-Flash-engram-host | 12 | 554,700 | 6,357.4 | wafer-pipeline | 5,059.2 | wafer-hybrid | 1.26x | 2,066.5 | pipeline | 433.5 | hybrid | 4.77x | 3.08x | 11.67x | 3.79x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 3.30x to 3.79x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-host | 1 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 5,084.7 | 111,864.4 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-hybrid | 138,768 | 1.00x | hybrid | 990.79 | 447.8 | 9,403.2 | link_latency | 11.36x | 5.28x | 40.32x | 11.36x |
| DeepSeek-V4.1-Flash-engram-host | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x64 | 52,160 | 1,297.5 | 1,297.5 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x63-hybrid | 52,038 | 1.00x | hybrid | 940.51 | 455.2 | 3,641.5 | link_latency | 2.85x | 0.16x | 10.29x | 2.85x |
| DeepSeek-V4.1-Flash-engram-host | 2 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 5,084.7 | 111,864.4 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-hybrid | 138,768 | 1.00x | hybrid | 990.79 | 447.8 | 9,403.2 | link_latency | 11.36x | 5.28x | 40.32x | 11.36x |
| DeepSeek-V4.1-Flash-engram-host | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 1,815.8 | 9,079.2 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 944.48 | 452.1 | 4,068.8 | link_latency | 4.02x | 1.03x | 14.40x | 4.02x |
| DeepSeek-V4.1-Flash-engram-host | 4 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 5,084.7 | 111,864.4 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-hybrid | 138,768 | 1.00x | hybrid | 990.79 | 447.8 | 9,403.2 | link_latency | 11.36x | 5.28x | 40.32x | 11.36x |
| DeepSeek-V4.1-Flash-engram-host | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 1,815.8 | 9,079.2 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 944.48 | 452.1 | 4,068.8 | link_latency | 4.02x | 1.03x | 14.40x | 4.02x |
| DeepSeek-V4.1-Flash-engram-host | 8 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 5,084.7 | 111,864.4 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-hybrid | 138,768 | 1.00x | hybrid | 990.79 | 447.8 | 9,403.2 | link_latency | 11.36x | 5.28x | 40.32x | 11.36x |
| DeepSeek-V4.1-Flash-engram-host | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 1,603.1 | 14,428.1 | compute | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 944.48 | 452.1 | 4,068.8 | link_latency | 3.55x | 1.63x | 12.71x | 3.55x |
| DeepSeek-V4.1-Flash-engram-host | 16 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 5,084.7 | 111,864.4 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-hybrid | 138,768 | 1.00x | hybrid | 990.79 | 447.8 | 9,403.2 | link_latency | 11.36x | 5.28x | 40.32x | 11.36x |
| DeepSeek-V4.1-Flash-engram-host | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 1,068.4 | 19,231.8 | compute | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 968.76 | 403.7 | 6,458.8 | weight_read | 2.65x | 2.18x | 8.47x | 2.65x |
| DeepSeek-V4.1-Flash-engram-host | 32 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 5,062.4 | 288,558.5 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x448-hybrid | 370,048 | 1.00x | hybrid | 1,064.54 | 433.5 | 24,273.5 | link_latency | 11.68x | 5.11x | 40.15x | 11.88x |
| DeepSeek-V4.1-Flash-engram-host | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 643.8 | 20,602.8 | compute | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 1,012.84 | 325.1 | 10,402.9 | weight_read | 1.98x | 1.98x | 5.11x | 1.98x |
| DeepSeek-V4.1-Flash-engram-host | 64 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 5,059.2 | 435,089.1 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,064.54 | 433.5 | 36,410.3 | link_latency | 11.67x | 5.13x | 40.12x | 12.21x |
| DeepSeek-V4.1-Flash-engram-host | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-hybrid-x71 | 57,865 | 356.3 | 22,802.8 | compute | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 1,122.41 | 236.4 | 15,129.9 | weight_read | 1.51x | 1.51x | 2.83x | 1.51x |
| DeepSeek-V4.1-Flash-engram-host | 256 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,982.8 | 1,019,597.3 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,234.22 | 322.5 | 82,560.1 | weight_read | 12.35x | 12.03x | 31.59x | 12.92x |
| DeepSeek-V4.1-Flash-engram-host | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-pipeline-x71 | 57,865 | 94.1 | 24,090.9 | compute | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 1,574.72 | 97.3 | 24,915.2 | weight_read | 0.97x | 0.97x | 1.42x | 0.97x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,978.0 | 2,025,473.8 | kv_read | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 2,038.28 | 155.6 | 159,331.6 | weight_read | 12.71x | 12.71x | 18.52x | 13.32x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-pipeline-x71 | 57,865 | 23.6 | 24,151.2 | compute | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 4,380.72 | 43.0 | 44,025.3 | weight_read | 0.55x | 0.55x | 0.98x | 0.55x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 602.8 | 2,469,077.6 | kv_read | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 2,026.60 | 59.3 | 242,909.2 | weight_read | 10.16x | 10.16x | 12.90x | 10.76x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-pipeline-x71 | 57,865 | 5.9 | 24,056.4 | compute | DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 15,546.70 | 25.3 | 103,776.8 | weight_read | 0.23x | 0.23x | 0.66x | 0.23x |

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
| DeepSeek-V4.1-Flash-engram-host | 15 | 12,390 | 126.1 | 312.4 | 450.9 | hybrid | 917.21 | 41.4% | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 33 | 27,258 | 126.1 | 329.2 | 424.3 | hybrid | 928.94 | 39.4% | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 35 | 28,910 | 126.1 | 330.3 | 435.5 | hybrid | 928.94 | 40.5% | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 36 | 29,736 | 126.1 | 330.8 | 440.8 | hybrid | 928.94 | 40.9% | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 37 | 30,562 | 126.1 | 331.2 | 446.0 | hybrid | 928.94 | 41.4% | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 38 | 31,388 | 126.1 | 331.6 | 451.0 | hybrid | 928.94 | 41.9% | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 56 | 46,256 | 126.1 | 334.1 | 458.9 | hybrid | 936.71 | 43.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 63 | 52,038 | 126.1 | 334.1 | 455.2 | hybrid | 940.51 | 42.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 68 | 56,168 | 126.1 | 297.1 | 446.8 | hybrid | 944.48 | 42.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 70 | 57,820 | 126.1 | 297.2 | 452.1 | hybrid | 944.48 | 42.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 71 | 58,646 | 126.1 | 297.2 | 454.7 | hybrid | 944.48 | 42.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 75 | 61,950 | 126.1 | 296.9 | 444.6 | hybrid | 948.28 | 42.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 79 | 65,254 | 126.1 | 296.9 | 454.2 | hybrid | 948.28 | 43.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 82 | 67,732 | 126.1 | 296.5 | 442.7 | hybrid | 952.25 | 42.2% | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 84 | 69,384 | 126.1 | 296.5 | 447.2 | hybrid | 952.25 | 42.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 85 | 70,210 | 126.1 | 296.5 | 449.3 | hybrid | 952.25 | 42.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 86 | 71,036 | 126.1 | 296.4 | 451.5 | hybrid | 952.25 | 43.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 95 | 78,470 | 126.1 | 295.9 | 453.0 | hybrid | 956.05 | 43.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 103 | 85,078 | 126.1 | 295.3 | 452.3 | hybrid | 960.02 | 43.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 111 | 91,686 | 126.1 | 294.6 | 451.7 | hybrid | 963.69 | 43.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 112 | 92,512 | 126.1 | 294.6 | 453.3 | hybrid | 963.69 | 43.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 117 | 96,642 | 126.1 | 294.1 | 447.9 | hybrid | 967.65 | 43.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 121 | 99,946 | 126.1 | 293.6 | 441.6 | hybrid | 971.45 | 42.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 122 | 100,772 | 126.1 | 293.6 | 443.1 | hybrid | 971.45 | 43.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 126 | 104,076 | 126.1 | 293.3 | 448.9 | hybrid | 971.45 | 43.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 130 | 107,380 | 126.1 | 292.7 | 442.8 | hybrid | 975.42 | 43.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 132 | 109,032 | 126.1 | 292.5 | 445.6 | hybrid | 975.42 | 43.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 136 | 112,336 | 126.1 | 292.2 | 450.9 | hybrid | 975.42 | 44.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 168 | 138,768 | 126.1 | 289.0 | 447.8 | hybrid | 990.79 | 44.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 189 | 156,114 | 126.1 | 286.8 | 442.7 | hybrid | 1,002.53 | 44.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 204 | 168,504 | 126.1 | 285.2 | 440.5 | hybrid | 1,010.29 | 44.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 224 | 185,024 | 126.1 | 283.1 | 442.4 | hybrid | 1,017.93 | 45.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 253 | 208,978 | 126.1 | 280.1 | 437.4 | hybrid | 1,033.47 | 45.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 272 | 224,672 | 126.1 | 278.1 | 437.9 | hybrid | 1,041.23 | 45.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 335 | 276,710 | 126.1 | 226.8 | 433.0 | hybrid | 1,064.54 | 46.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 336 | 277,536 | 126.1 | 226.8 | 433.5 | hybrid | 1,064.54 | 46.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 448 | 370,048 | 126.1 | 219.1 | 433.5 | hybrid | 1,064.54 | 46.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 672 | 555,072 | 126.1 | 205.1 | 433.5 | hybrid | 1,064.54 | 46.1% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x85 | DeepSeek-V4.1-Flash-engram-host | 85 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 4.34 us | 23,067.6 tok/s | 230,675.7 tok/s | 20 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.25 us; 19 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.09 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x69 | DeepSeek-V4.1-Flash-engram-host | 69 | tensor | rom_package_ucie | rom_board_serdes | 160 | 187.39 us | 533.7 tok/s | 5,336.5 tok/s | 80 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.05 us; 80 x all_reduce span 35 on rom_board_serdes (traversals 11.0) = 185.34 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x83 | DeepSeek-V4.1-Flash-engram-host | 83 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 10.44 us | 9,578.3 tok/s | 95,782.7 tok/s | 80 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.05 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 8.39 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-pipeline-x85 | DeepSeek-V4.1-Flash-engram-host | 85 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash-engram-host | 2 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-tensor-x64 | DeepSeek-V4.1-Flash-engram-host | 64 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash-engram-host | 2 | tensor | on_wafer | rom_wafer_serdes | 160 | 191.00 us | 523.6 tok/s | 5,235.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 37.00 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hybrid-x76 | DeepSeek-V4.1-Flash-engram-host | 76 | hybrid | nvlink3 | infiniband_hdr | 89 | 429.12 us | 233.0 tok/s | 2,330.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.96 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash-engram-host | 2 | hybrid | on_wafer | rom_wafer_serdes | 81 | 154.21 us | 648.5 tok/s | 6,484.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-pipeline-x134 | DeepSeek-V4.1-Flash-engram-host | 134 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 4.34 us | 23,067.6 tok/s | 230,675.7 tok/s | 20 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.25 us; 19 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.09 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-tensor-x72 | DeepSeek-V4.1-Flash-engram-host | 72 | tensor | rom_package_ucie | rom_board_serdes | 160 | 187.39 us | 533.6 tok/s | 5,336.5 tok/s | 80 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.05 us; 80 x all_reduce span 36 on rom_board_serdes (traversals 11.0) = 185.34 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-hybrid-x124 | DeepSeek-V4.1-Flash-engram-host | 124 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 10.44 us | 9,578.3 tok/s | 95,782.7 tok/s | 80 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.05 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 8.39 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-pipeline-x132 | DeepSeek-V4.1-Flash-engram-host | 132 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash-engram-host | 2 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-tensor-x71 | DeepSeek-V4.1-Flash-engram-host | 71 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash-engram-host | 2 | tensor | on_wafer | rom_wafer_serdes | 160 | 191.00 us | 523.6 tok/s | 5,235.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 37.00 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hybrid-x86 | DeepSeek-V4.1-Flash-engram-host | 86 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash-engram-host | 2 | hybrid | on_wafer | rom_wafer_serdes | 81 | 154.21 us | 648.5 tok/s | 6,484.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x15-pipeline | DeepSeek-V4.1-Flash-engram-host | 15 | pipeline | nvlink3 | infiniband_hdr | 14 | 35.38 us | 2,826.2 tok/s | 28,261.9 tok/s | 13 x point_to_point span 2 on nvlink3 (traversals 1.0) = 32.94 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.44 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x15-tensor | DeepSeek-V4.1-Flash-engram-host | 15 | tensor | nvlink3 | infiniband_hdr | 160 | 781.12 us | 128.0 tok/s | 1,280.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 373.95 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x15-hybrid | DeepSeek-V4.1-Flash-engram-host | 15 | hybrid | nvlink3 | infiniband_hdr | 81 | 409.61 us | 244.1 tok/s | 2,441.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.44 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x15-expert | DeepSeek-V4.1-Flash-engram-host | 15 | expert | nvlink3 | infiniband_hdr | 160 | 582.68 us | 171.6 tok/s | 1,716.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.51 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x33-pipeline | DeepSeek-V4.1-Flash-engram-host | 33 | pipeline | nvlink3 | infiniband_hdr | 32 | 80.71 us | 1,238.9 tok/s | 12,389.4 tok/s | 28 x point_to_point span 2 on nvlink3 (traversals 1.0) = 70.96 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x33-tensor | DeepSeek-V4.1-Flash-engram-host | 33 | tensor | nvlink3 | infiniband_hdr | 160 | 810.61 us | 123.4 tok/s | 1,233.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 403.44 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x33-hybrid | DeepSeek-V4.1-Flash-engram-host | 33 | hybrid | nvlink3 | infiniband_hdr | 84 | 416.93 us | 239.9 tok/s | 2,398.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x33-expert | DeepSeek-V4.1-Flash-engram-host | 33 | expert | nvlink3 | infiniband_hdr | 160 | 570.15 us | 175.4 tok/s | 1,753.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.79 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 168.36 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x35-pipeline | DeepSeek-V4.1-Flash-engram-host | 35 | pipeline | nvlink3 | infiniband_hdr | 34 | 85.78 us | 1,165.7 tok/s | 11,657.4 tok/s | 30 x point_to_point span 2 on nvlink3 (traversals 1.0) = 76.02 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x35-tensor | DeepSeek-V4.1-Flash-engram-host | 35 | tensor | nvlink3 | infiniband_hdr | 160 | 810.61 us | 123.4 tok/s | 1,233.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 403.44 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x35-hybrid | DeepSeek-V4.1-Flash-engram-host | 35 | hybrid | nvlink3 | infiniband_hdr | 84 | 416.93 us | 239.9 tok/s | 2,398.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x35-expert | DeepSeek-V4.1-Flash-engram-host | 35 | expert | nvlink3 | infiniband_hdr | 160 | 569.81 us | 175.5 tok/s | 1,755.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.79 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 168.02 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x36-pipeline | DeepSeek-V4.1-Flash-engram-host | 36 | pipeline | nvlink3 | infiniband_hdr | 35 | 88.32 us | 1,132.3 tok/s | 11,322.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.56 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x36-tensor | DeepSeek-V4.1-Flash-engram-host | 36 | tensor | nvlink3 | infiniband_hdr | 160 | 810.61 us | 123.4 tok/s | 1,233.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 403.44 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x36-hybrid | DeepSeek-V4.1-Flash-engram-host | 36 | hybrid | nvlink3 | infiniband_hdr | 84 | 416.93 us | 239.9 tok/s | 2,398.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x36-expert | DeepSeek-V4.1-Flash-engram-host | 36 | expert | nvlink3 | infiniband_hdr | 160 | 569.65 us | 175.5 tok/s | 1,755.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.79 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 167.86 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x37-pipeline | DeepSeek-V4.1-Flash-engram-host | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.85 us | 1,100.7 tok/s | 11,007.1 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 81.09 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x37-tensor | DeepSeek-V4.1-Flash-engram-host | 37 | tensor | nvlink3 | infiniband_hdr | 160 | 810.61 us | 123.4 tok/s | 1,233.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 403.44 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x37-hybrid | DeepSeek-V4.1-Flash-engram-host | 37 | hybrid | nvlink3 | infiniband_hdr | 84 | 416.93 us | 239.9 tok/s | 2,398.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x37-expert | DeepSeek-V4.1-Flash-engram-host | 37 | expert | nvlink3 | infiniband_hdr | 160 | 569.51 us | 175.6 tok/s | 1,755.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.79 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 167.71 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x38-pipeline | DeepSeek-V4.1-Flash-engram-host | 38 | pipeline | nvlink3 | infiniband_hdr | 37 | 93.38 us | 1,070.8 tok/s | 10,708.4 tok/s | 33 x point_to_point span 2 on nvlink3 (traversals 1.0) = 83.63 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x38-tensor | DeepSeek-V4.1-Flash-engram-host | 38 | tensor | nvlink3 | infiniband_hdr | 160 | 810.61 us | 123.4 tok/s | 1,233.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 403.44 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x38-hybrid | DeepSeek-V4.1-Flash-engram-host | 38 | hybrid | nvlink3 | infiniband_hdr | 84 | 416.93 us | 239.9 tok/s | 2,398.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x38-expert | DeepSeek-V4.1-Flash-engram-host | 38 | expert | nvlink3 | infiniband_hdr | 160 | 569.37 us | 175.6 tok/s | 1,756.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.79 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 167.57 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash-engram-host | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash-engram-host | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash-engram-host | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x56-expert | DeepSeek-V4.1-Flash-engram-host | 56 | expert | nvlink3 | infiniband_hdr | 160 | 566.93 us | 176.4 tok/s | 1,763.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x63-pipeline | DeepSeek-V4.1-Flash-engram-host | 63 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x63-tensor | DeepSeek-V4.1-Flash-engram-host | 63 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x63-hybrid | DeepSeek-V4.1-Flash-engram-host | 63 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x63-expert | DeepSeek-V4.1-Flash-engram-host | 63 | expert | nvlink3 | infiniband_hdr | 160 | 566.54 us | 176.5 tok/s | 1,765.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.52 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x68-pipeline | DeepSeek-V4.1-Flash-engram-host | 68 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x68-tensor | DeepSeek-V4.1-Flash-engram-host | 68 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x68-hybrid | DeepSeek-V4.1-Flash-engram-host | 68 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x68-expert | DeepSeek-V4.1-Flash-engram-host | 68 | expert | nvlink3 | infiniband_hdr | 160 | 566.19 us | 176.6 tok/s | 1,766.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.90 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.29 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-pipeline | DeepSeek-V4.1-Flash-engram-host | 70 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-tensor | DeepSeek-V4.1-Flash-engram-host | 70 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-hybrid | DeepSeek-V4.1-Flash-engram-host | 70 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x70-expert | DeepSeek-V4.1-Flash-engram-host | 70 | expert | nvlink3 | infiniband_hdr | 160 | 566.10 us | 176.6 tok/s | 1,766.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.90 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.21 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x71-pipeline | DeepSeek-V4.1-Flash-engram-host | 71 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x71-tensor | DeepSeek-V4.1-Flash-engram-host | 71 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x71-hybrid | DeepSeek-V4.1-Flash-engram-host | 71 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x71-expert | DeepSeek-V4.1-Flash-engram-host | 71 | expert | nvlink3 | infiniband_hdr | 160 | 566.07 us | 176.7 tok/s | 1,766.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.90 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.17 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x75-pipeline | DeepSeek-V4.1-Flash-engram-host | 75 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x75-tensor | DeepSeek-V4.1-Flash-engram-host | 75 | tensor | nvlink3 | infiniband_hdr | 160 | 820.44 us | 121.9 tok/s | 1,218.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 413.27 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x75-hybrid | DeepSeek-V4.1-Flash-engram-host | 75 | hybrid | nvlink3 | infiniband_hdr | 89 | 429.12 us | 233.0 tok/s | 2,330.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.96 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x75-expert | DeepSeek-V4.1-Flash-engram-host | 75 | expert | nvlink3 | infiniband_hdr | 160 | 565.82 us | 176.7 tok/s | 1,767.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.80 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.02 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x79-pipeline | DeepSeek-V4.1-Flash-engram-host | 79 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x79-tensor | DeepSeek-V4.1-Flash-engram-host | 79 | tensor | nvlink3 | infiniband_hdr | 160 | 820.44 us | 121.9 tok/s | 1,218.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 413.27 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x79-hybrid | DeepSeek-V4.1-Flash-engram-host | 79 | hybrid | nvlink3 | infiniband_hdr | 89 | 429.12 us | 233.0 tok/s | 2,330.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.96 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x79-expert | DeepSeek-V4.1-Flash-engram-host | 79 | expert | nvlink3 | infiniband_hdr | 160 | 565.69 us | 176.8 tok/s | 1,767.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.80 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.89 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x82-pipeline | DeepSeek-V4.1-Flash-engram-host | 82 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x82-tensor | DeepSeek-V4.1-Flash-engram-host | 82 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x82-hybrid | DeepSeek-V4.1-Flash-engram-host | 82 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x82-expert | DeepSeek-V4.1-Flash-engram-host | 82 | expert | nvlink3 | infiniband_hdr | 160 | 565.51 us | 176.8 tok/s | 1,768.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.72 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.80 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x84-pipeline | DeepSeek-V4.1-Flash-engram-host | 84 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x84-tensor | DeepSeek-V4.1-Flash-engram-host | 84 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x84-hybrid | DeepSeek-V4.1-Flash-engram-host | 84 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x84-expert | DeepSeek-V4.1-Flash-engram-host | 84 | expert | nvlink3 | infiniband_hdr | 160 | 565.46 us | 176.8 tok/s | 1,768.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.72 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.74 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x85-pipeline | DeepSeek-V4.1-Flash-engram-host | 85 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x85-tensor | DeepSeek-V4.1-Flash-engram-host | 85 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x85-hybrid | DeepSeek-V4.1-Flash-engram-host | 85 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x85-expert | DeepSeek-V4.1-Flash-engram-host | 85 | expert | nvlink3 | infiniband_hdr | 160 | 565.43 us | 176.9 tok/s | 1,768.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.72 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.71 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x86-pipeline | DeepSeek-V4.1-Flash-engram-host | 86 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x86-tensor | DeepSeek-V4.1-Flash-engram-host | 86 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x86-hybrid | DeepSeek-V4.1-Flash-engram-host | 86 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x86-expert | DeepSeek-V4.1-Flash-engram-host | 86 | expert | nvlink3 | infiniband_hdr | 160 | 565.40 us | 176.9 tok/s | 1,768.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.72 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.69 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x95-pipeline | DeepSeek-V4.1-Flash-engram-host | 95 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x95-tensor | DeepSeek-V4.1-Flash-engram-host | 95 | tensor | nvlink3 | infiniband_hdr | 160 | 822.08 us | 121.6 tok/s | 1,216.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 414.91 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x95-hybrid | DeepSeek-V4.1-Flash-engram-host | 95 | hybrid | nvlink3 | infiniband_hdr | 91 | 434.00 us | 230.4 tok/s | 2,304.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 26.84 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x95-expert | DeepSeek-V4.1-Flash-engram-host | 95 | expert | nvlink3 | infiniband_hdr | 160 | 565.12 us | 177.0 tok/s | 1,769.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.65 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.47 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x103-pipeline | DeepSeek-V4.1-Flash-engram-host | 103 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x103-tensor | DeepSeek-V4.1-Flash-engram-host | 103 | tensor | nvlink3 | infiniband_hdr | 160 | 822.71 us | 121.5 tok/s | 1,215.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 415.54 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x103-hybrid | DeepSeek-V4.1-Flash-engram-host | 103 | hybrid | nvlink3 | infiniband_hdr | 92 | 436.44 us | 229.1 tok/s | 2,291.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 29.28 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x103-expert | DeepSeek-V4.1-Flash-engram-host | 103 | expert | nvlink3 | infiniband_hdr | 160 | 564.91 us | 177.0 tok/s | 1,770.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.60 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.31 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x111-pipeline | DeepSeek-V4.1-Flash-engram-host | 111 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x111-tensor | DeepSeek-V4.1-Flash-engram-host | 111 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x111-hybrid | DeepSeek-V4.1-Flash-engram-host | 111 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x111-expert | DeepSeek-V4.1-Flash-engram-host | 111 | expert | nvlink3 | infiniband_hdr | 160 | 564.72 us | 177.1 tok/s | 1,770.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.55 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.17 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x112-pipeline | DeepSeek-V4.1-Flash-engram-host | 112 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x112-tensor | DeepSeek-V4.1-Flash-engram-host | 112 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x112-hybrid | DeepSeek-V4.1-Flash-engram-host | 112 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x112-expert | DeepSeek-V4.1-Flash-engram-host | 112 | expert | nvlink3 | infiniband_hdr | 160 | 564.67 us | 177.1 tok/s | 1,771.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.16 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x117-pipeline | DeepSeek-V4.1-Flash-engram-host | 117 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x117-tensor | DeepSeek-V4.1-Flash-engram-host | 117 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x117-hybrid | DeepSeek-V4.1-Flash-engram-host | 117 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x117-expert | DeepSeek-V4.1-Flash-engram-host | 117 | expert | nvlink3 | infiniband_hdr | 160 | 564.59 us | 177.1 tok/s | 1,771.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.08 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x121-pipeline | DeepSeek-V4.1-Flash-engram-host | 121 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x121-tensor | DeepSeek-V4.1-Flash-engram-host | 121 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x121-hybrid | DeepSeek-V4.1-Flash-engram-host | 121 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x121-expert | DeepSeek-V4.1-Flash-engram-host | 121 | expert | nvlink3 | infiniband_hdr | 160 | 564.50 us | 177.1 tok/s | 1,771.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.02 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x122-pipeline | DeepSeek-V4.1-Flash-engram-host | 122 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x122-tensor | DeepSeek-V4.1-Flash-engram-host | 122 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x122-hybrid | DeepSeek-V4.1-Flash-engram-host | 122 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x122-expert | DeepSeek-V4.1-Flash-engram-host | 122 | expert | nvlink3 | infiniband_hdr | 160 | 564.49 us | 177.2 tok/s | 1,771.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.01 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x126-pipeline | DeepSeek-V4.1-Flash-engram-host | 126 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x126-tensor | DeepSeek-V4.1-Flash-engram-host | 126 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x126-hybrid | DeepSeek-V4.1-Flash-engram-host | 126 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x126-expert | DeepSeek-V4.1-Flash-engram-host | 126 | expert | nvlink3 | infiniband_hdr | 160 | 564.44 us | 177.2 tok/s | 1,771.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.96 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x130-pipeline | DeepSeek-V4.1-Flash-engram-host | 130 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x130-tensor | DeepSeek-V4.1-Flash-engram-host | 130 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x130-hybrid | DeepSeek-V4.1-Flash-engram-host | 130 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x130-expert | DeepSeek-V4.1-Flash-engram-host | 130 | expert | nvlink3 | infiniband_hdr | 160 | 564.36 us | 177.2 tok/s | 1,771.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.91 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x132-pipeline | DeepSeek-V4.1-Flash-engram-host | 132 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x132-tensor | DeepSeek-V4.1-Flash-engram-host | 132 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x132-hybrid | DeepSeek-V4.1-Flash-engram-host | 132 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x132-expert | DeepSeek-V4.1-Flash-engram-host | 132 | expert | nvlink3 | infiniband_hdr | 160 | 564.34 us | 177.2 tok/s | 1,772.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.89 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x136-pipeline | DeepSeek-V4.1-Flash-engram-host | 136 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x136-tensor | DeepSeek-V4.1-Flash-engram-host | 136 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x136-hybrid | DeepSeek-V4.1-Flash-engram-host | 136 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x136-expert | DeepSeek-V4.1-Flash-engram-host | 136 | expert | nvlink3 | infiniband_hdr | 160 | 564.27 us | 177.2 tok/s | 1,772.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.85 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-pipeline | DeepSeek-V4.1-Flash-engram-host | 168 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-tensor | DeepSeek-V4.1-Flash-engram-host | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-hybrid | DeepSeek-V4.1-Flash-engram-host | 168 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x168-expert | DeepSeek-V4.1-Flash-engram-host | 168 | expert | nvlink3 | infiniband_hdr | 160 | 563.91 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x189-pipeline | DeepSeek-V4.1-Flash-engram-host | 189 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x189-tensor | DeepSeek-V4.1-Flash-engram-host | 189 | tensor | nvlink3 | infiniband_hdr | 160 | 826.18 us | 121.0 tok/s | 1,210.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 419.01 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x189-hybrid | DeepSeek-V4.1-Flash-engram-host | 189 | hybrid | nvlink3 | infiniband_hdr | 103 | 463.28 us | 215.9 tok/s | 2,158.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 56.11 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x189-expert | DeepSeek-V4.1-Flash-engram-host | 189 | expert | nvlink3 | infiniband_hdr | 160 | 563.75 us | 177.4 tok/s | 1,773.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.31 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.44 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x204-pipeline | DeepSeek-V4.1-Flash-engram-host | 204 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x204-tensor | DeepSeek-V4.1-Flash-engram-host | 204 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x204-hybrid | DeepSeek-V4.1-Flash-engram-host | 204 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x204-expert | DeepSeek-V4.1-Flash-engram-host | 204 | expert | nvlink3 | infiniband_hdr | 160 | 563.65 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash-engram-host | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash-engram-host | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash-engram-host | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x224-expert | DeepSeek-V4.1-Flash-engram-host | 224 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.28 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x253-pipeline | DeepSeek-V4.1-Flash-engram-host | 253 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x253-tensor | DeepSeek-V4.1-Flash-engram-host | 253 | tensor | nvlink3 | infiniband_hdr | 160 | 827.20 us | 120.9 tok/s | 1,208.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 32 on infiniband_hdr (traversals 2.0) = 420.03 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x253-hybrid | DeepSeek-V4.1-Flash-engram-host | 253 | hybrid | nvlink3 | infiniband_hdr | 111 | 482.80 us | 207.1 tok/s | 2,071.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 31 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.63 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x253-expert | DeepSeek-V4.1-Flash-engram-host | 253 | expert | nvlink3 | infiniband_hdr | 160 | 563.41 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.23 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.18 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x272-pipeline | DeepSeek-V4.1-Flash-engram-host | 272 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x272-tensor | DeepSeek-V4.1-Flash-engram-host | 272 | tensor | nvlink3 | infiniband_hdr | 160 | 827.38 us | 120.9 tok/s | 1,208.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 420.21 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x272-hybrid | DeepSeek-V4.1-Flash-engram-host | 272 | hybrid | nvlink3 | infiniband_hdr | 113 | 487.67 us | 205.1 tok/s | 2,050.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 80.51 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x272-expert | DeepSeek-V4.1-Flash-engram-host | 272 | expert | nvlink3 | infiniband_hdr | 160 | 563.33 us | 177.5 tok/s | 1,775.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.21 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.12 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x335-pipeline | DeepSeek-V4.1-Flash-engram-host | 335 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x335-tensor | DeepSeek-V4.1-Flash-engram-host | 335 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x335-hybrid | DeepSeek-V4.1-Flash-engram-host | 335 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x335-expert | DeepSeek-V4.1-Flash-engram-host | 335 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x336-pipeline | DeepSeek-V4.1-Flash-engram-host | 336 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x336-tensor | DeepSeek-V4.1-Flash-engram-host | 336 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x336-hybrid | DeepSeek-V4.1-Flash-engram-host | 336 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x336-expert | DeepSeek-V4.1-Flash-engram-host | 336 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x448-pipeline | DeepSeek-V4.1-Flash-engram-host | 448 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x448-tensor | DeepSeek-V4.1-Flash-engram-host | 448 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.32 us | 86.7 tok/s | 867.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 746.15 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x448-hybrid | DeepSeek-V4.1-Flash-engram-host | 448 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x448-expert | DeepSeek-V4.1-Flash-engram-host | 448 | expert | nvlink3 | infiniband_hdr | 160 | 562.97 us | 177.6 tok/s | 1,776.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.13 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.84 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-pipeline | DeepSeek-V4.1-Flash-engram-host | 672 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-tensor | DeepSeek-V4.1-Flash-engram-host | 672 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.90 us | 86.7 tok/s | 866.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 746.73 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-hybrid | DeepSeek-V4.1-Flash-engram-host | 672 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-host/a100_sxm_80gb-x672-expert | DeepSeek-V4.1-Flash-engram-host | 672 | expert | nvlink3 | infiniband_hdr | 160 | 562.78 us | 177.7 tok/s | 1,776.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.09 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.69 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash-engram-host | 1 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 5,080.8 | 0.055 | 3,837.6 (92,095) | 5,080.8 (92,450) | 1.32x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 2 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 5,080.8 | 0.055 | 3,837.6 (92,095) | 5,080.8 (92,450) | 1.32x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 4 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 5,080.8 | 0.055 | 3,837.6 (92,095) | 5,080.8 (92,450) | 1.32x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 8 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 5,080.8 | 0.055 | 3,837.6 (92,095) | 5,080.8 (92,450) | 1.32x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 16 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 5,084.7 | 0.037 | 3,837.6 (92,095) | 5,084.7 (138,675) | 1.32x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 32 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 5,059.2 | 0.018 | 3,839.6 (100,245) | 5,059.2 (277,350) | 1.32x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 64 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 5,059.2 | 0.009 | 3,768.2 (107,580) | 5,059.2 (554,700) | 1.34x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 256 | wafer | array | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,982.8 | 0.007 | 2,960.5 (277,100) | 3,982.8 (554,700) | 1.35x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 1024 | wafer | array | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,978.0 | 0.004 | 1,114.1 (224,940) | 1,978.0 (554,700) | 1.78x | kv_read |
| DeepSeek-V4.1-Flash-engram-host | 4096 | wafer | array | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 602.8 | 0.001 | 382.7 (224,940) | 602.8 (554,700) | 1.58x | kv_read |

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
| DeepSeek-V4.1-Flash-engram-host | 384 | 752.0 MB | 164.9 mm2 | 29.69 mm2 (18.0%) | 63,336 mm2 | 11,400 mm2 | 67,448 mm2 = 82.8 reticles |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | sram | 579,529.6 | 28,976.6 | 28,976.6 | 20.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 2 | sram | 579,529.6 | 28,976.6 | 28,976.6 | 20.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 4 | sram | 579,529.6 | 28,976.6 | 28,976.6 | 20.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 8 | sram | 579,529.6 | 28,976.6 | 28,976.6 | 20.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 16 | sram | 579,529.6 | 28,976.6 | 39,542.5 | 20.00x | 1.36x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 32 | sram | 579,529.6 | 28,976.6 | 63,369.3 | 20.00x | 2.19x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 64 | sram | 579,529.6 | 29,014.6 | 99,668.0 | 19.97x | 3.44x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 256 | sram | 687,541.8 | 26,113.2 | 193,528.4 | 26.33x | 7.41x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 1024 | sram | 1,288,695.7 | 26,113.2 | 313,755.9 | 49.35x | 12.02x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 4096 | sram | 1,977,681.8 | 26,113.2 | 429,899.1 | 75.74x | 16.46x | weight_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-host | 1 | rom | 1,808,122.2 | 86,176.0 | 86,176.0 | 20.98x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 2 | rom | 1,808,122.2 | 86,176.0 | 86,176.0 | 20.98x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 4 | rom | 1,808,122.2 | 86,176.0 | 86,176.0 | 20.98x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 8 | rom | 1,808,122.2 | 86,176.0 | 86,176.0 | 20.98x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 16 | rom | 1,808,122.2 | 86,176.0 | 86,176.0 | 20.98x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 32 | rom | 1,808,122.2 | 86,176.0 | 103,510.1 | 20.98x | 1.20x | kv_read | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 64 | rom | 1,808,122.2 | 86,176.0 | 157,187.3 | 20.98x | 1.82x | kv_read | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-host | 256 | rom | 1,808,122.2 | 90,298.1 | 313,862.1 | 20.02x | 3.48x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 1024 | rom | 2,025,473.8 | 90,298.1 | 422,787.0 | 22.43x | 4.68x | kv_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-host | 4096 | rom | 2,469,077.6 | 90,298.1 | 441,504.5 | 27.34x | 4.89x | kv_read | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,529.6 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,808,122.2 | 3.260 | kv_read | 3.12x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,529.6 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,808,122.2 | 3.260 | kv_read | 3.12x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,529.6 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,808,122.2 | 3.260 | kv_read | 3.12x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,529.6 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,808,122.2 | 3.260 | kv_read | 3.12x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,529.6 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,808,122.2 | 3.260 | kv_read | 3.12x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.43 | 39,542.5 | 0.428 | weight_read | 0.07x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,529.6 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,808,122.2 | 3.260 | kv_read | 3.12x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,976.6 | 0.627 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.99 | 63,369.3 | 0.685 | weight_read | 0.11x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 3.46 | 1.43 | 103,510.1 | 1.120 | layer_fixed_latency | 0.18x |
| DeepSeek-V4.1-Flash-engram-host | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 579,529.6 | 1.045 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,808,122.2 | 3.260 | kv_read | 3.12x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 29,014.6 | 0.628 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 1.00 | 86,176.0 | 0.932 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.54 | 99,668.0 | 1.078 | weight_read | 0.17x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 3.46 | 1.99 | 157,187.3 | 1.700 | layer_fixed_latency | 0.27x |
| DeepSeek-V4.1-Flash-engram-host | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 687,541.8 | 1.859 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 1,808,122.2 | 3.260 | kv_read | 2.63x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-pipeline-x36-perstream | 29,340 | 1.00 | 7.11 | 26,113.2 | 0.890 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 2.25 | 90,298.1 | 0.977 | weight_read | 0.13x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.49 | 193,528.4 | 2.093 | weight_read | 0.28x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 3.46 | 2.06 | 313,862.1 | 3.395 | weight_read | 0.46x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,288,695.7 | 2.323 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 2,025,473.8 | 3.651 | kv_read | 1.57x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-pipeline-x36-perstream | 29,340 | 1.00 | 28.44 | 26,113.2 | 0.890 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 8.98 | 90,298.1 | 0.977 | weight_read | 0.07x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 5.09 | 313,755.9 | 3.394 | weight_read | 0.24x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 3.46 | 2.69 | 422,787.0 | 4.573 | kv_read | 0.33x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,977,681.8 | 3.565 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 2,469,077.6 | 4.451 | kv_read | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-array-hw-pipeline-x36-perstream | 29,340 | 1.00 | 113.78 | 26,113.2 | 0.890 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 3.46 | 35.93 | 90,298.1 | 0.977 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 7.62 | 429,899.1 | 4.650 | kv_read | 0.22x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 3.46 | 3.69 | 441,504.5 | 4.776 | kv_read | 0.22x |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 33 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 33 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 33 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 57 | 1.12 | 1.001 | 1.009 | 1.01x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 36 | 7.11 | 1.049 | 1.906 | 1.82x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 36 | 28.44 | 1.231 | 3.315 | 2.69x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 36 | 113.78 | 2.133 | 6.729 | 3.15x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-host | 1 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 15 | 8.40 | 4.73 | 1.78x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 15 | 12.02 | 6.00 | 2.01x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 15 | 14.35 | 7.31 | 1.96x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 15 | 14.96 | 8.56 | 1.75x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 15 | 15.00 | 9.64 | 1.56x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 15 | 15.00 | 10.46 | 1.43x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 15 | 15.00 | 11.14 | 1.35x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 15 | 15.00 | 11.16 | 1.34x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 15 | 15.00 | 11.16 | 1.34x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 33 | 5.56 | 4.41 | 1.26x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 33 | 10.12 | 6.05 | 1.67x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 33 | 16.96 | 8.25 | 2.06x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 33 | 24.85 | 10.77 | 2.31x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 33 | 30.63 | 13.46 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 33 | 32.69 | 16.02 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 33 | 32.98 | 18.12 | 1.82x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 33 | 33.00 | 19.99 | 1.65x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 33 | 33.00 | 20.06 | 1.64x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 33 | 33.00 | 20.06 | 1.64x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 35 | 10.22 | 6.15 | 1.66x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 35 | 17.26 | 8.43 | 2.05x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 35 | 25.63 | 11.05 | 2.32x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 35 | 32.07 | 13.87 | 2.31x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 35 | 34.57 | 16.58 | 2.08x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 35 | 34.97 | 18.82 | 1.86x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 35 | 35.00 | 20.82 | 1.68x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 35 | 35.00 | 20.90 | 1.67x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 35 | 35.00 | 20.90 | 1.67x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 36 | 10.26 | 6.20 | 1.66x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 36 | 17.40 | 8.51 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 36 | 26.00 | 11.19 | 2.32x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 36 | 32.76 | 14.07 | 2.33x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 36 | 35.50 | 16.86 | 2.11x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 36 | 35.96 | 19.16 | 1.88x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 36 | 36.00 | 21.23 | 1.70x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 36 | 36.00 | 21.31 | 1.69x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 36 | 36.00 | 21.31 | 1.69x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 37 | 10.30 | 6.24 | 1.65x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 37 | 17.54 | 8.59 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 37 | 26.35 | 11.32 | 2.33x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 37 | 33.45 | 14.27 | 2.34x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 37 | 36.43 | 17.13 | 2.13x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 37 | 36.95 | 19.50 | 1.90x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 37 | 37.00 | 21.63 | 1.71x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 37 | 37.00 | 21.72 | 1.70x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 37 | 37.00 | 21.72 | 1.70x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 38 | 10.34 | 6.29 | 1.64x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 38 | 17.66 | 8.67 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 38 | 26.69 | 11.45 | 2.33x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 38 | 34.12 | 14.46 | 2.36x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 38 | 37.34 | 17.39 | 2.15x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 38 | 37.94 | 19.83 | 1.91x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 38 | 38.00 | 22.03 | 1.72x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 63 | 5.77 | 4.97 | 1.16x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 63 | 10.93 | 7.19 | 1.52x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 63 | 19.71 | 10.15 | 1.94x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 63 | 32.56 | 13.95 | 2.33x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 63 | 46.97 | 18.35 | 2.56x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 63 | 57.47 | 22.88 | 2.51x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 63 | 61.73 | 26.85 | 2.30x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 63 | 62.85 | 30.60 | 2.05x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 63 | 62.86 | 30.75 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 63 | 62.86 | 30.75 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 68 | 11.00 | 7.33 | 1.50x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 68 | 19.95 | 10.36 | 1.93x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 68 | 33.32 | 14.34 | 2.32x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 68 | 48.85 | 18.97 | 2.57x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 68 | 60.85 | 23.78 | 2.56x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 68 | 66.17 | 28.02 | 2.36x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 68 | 67.75 | 32.06 | 2.11x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 68 | 67.77 | 32.23 | 2.10x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 68 | 67.77 | 32.23 | 2.10x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 70 | 11.02 | 7.38 | 1.49x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 70 | 20.04 | 10.44 | 1.92x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 70 | 33.60 | 14.49 | 2.32x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 70 | 49.55 | 19.21 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 70 | 62.14 | 24.12 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 70 | 67.90 | 28.48 | 2.38x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 70 | 69.69 | 32.63 | 2.14x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 70 | 69.72 | 32.80 | 2.13x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 70 | 69.72 | 32.80 | 2.13x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 71 | 11.03 | 7.41 | 1.49x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 71 | 20.09 | 10.48 | 1.92x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 71 | 33.74 | 14.56 | 2.32x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 71 | 49.90 | 19.33 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 71 | 62.78 | 24.30 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 71 | 68.77 | 28.70 | 2.40x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 71 | 70.66 | 32.91 | 2.15x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 71 | 70.69 | 33.09 | 2.14x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 71 | 70.69 | 33.09 | 2.14x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 75 | 11.08 | 7.51 | 1.47x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 75 | 20.25 | 10.63 | 1.91x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 75 | 34.25 | 14.85 | 2.31x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 75 | 51.21 | 19.78 | 2.59x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 75 | 65.25 | 24.96 | 2.61x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 75 | 72.16 | 29.58 | 2.44x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 75 | 74.53 | 34.01 | 2.19x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 75 | 74.57 | 34.20 | 2.18x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 75 | 74.57 | 34.20 | 2.18x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 79 | 11.12 | 7.61 | 1.46x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 79 | 20.40 | 10.76 | 1.89x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 79 | 34.73 | 15.12 | 2.30x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 79 | 52.43 | 20.21 | 2.59x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 79 | 67.61 | 25.59 | 2.64x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 79 | 75.46 | 30.42 | 2.48x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 79 | 78.35 | 35.08 | 2.23x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 79 | 78.41 | 35.27 | 2.22x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 79 | 78.41 | 35.27 | 2.22x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 82 | 11.15 | 7.68 | 1.45x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 82 | 20.50 | 10.86 | 1.89x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 82 | 35.06 | 15.32 | 2.29x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 82 | 53.29 | 20.53 | 2.60x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 82 | 69.30 | 26.05 | 2.66x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 82 | 77.88 | 31.04 | 2.51x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 82 | 81.20 | 35.85 | 2.26x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 82 | 81.26 | 36.05 | 2.25x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 82 | 81.26 | 36.05 | 2.25x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 84 | 11.16 | 7.73 | 1.44x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 84 | 20.56 | 10.93 | 1.88x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 84 | 35.26 | 15.45 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 84 | 53.84 | 20.73 | 2.60x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 84 | 70.40 | 26.35 | 2.67x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 84 | 79.47 | 31.44 | 2.53x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 84 | 83.08 | 36.36 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 84 | 83.15 | 36.57 | 2.27x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 84 | 83.15 | 36.57 | 2.27x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 85 | 11.17 | 7.75 | 1.44x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 85 | 20.59 | 10.96 | 1.88x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 85 | 35.36 | 15.51 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 85 | 54.11 | 20.83 | 2.60x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 85 | 70.93 | 26.50 | 2.68x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 85 | 80.26 | 31.63 | 2.54x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 85 | 84.02 | 36.61 | 2.29x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 85 | 84.10 | 36.82 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 85 | 84.10 | 36.82 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 86 | 11.18 | 7.77 | 1.44x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 86 | 20.62 | 10.99 | 1.88x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 86 | 35.46 | 15.57 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 86 | 54.37 | 20.93 | 2.60x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 86 | 71.47 | 26.65 | 2.68x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 86 | 81.04 | 31.83 | 2.55x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 86 | 84.96 | 36.86 | 2.30x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 86 | 85.04 | 37.07 | 2.29x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 86 | 85.04 | 37.07 | 2.29x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 95 | 11.25 | 7.96 | 1.41x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 95 | 20.87 | 11.25 | 1.85x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 95 | 36.28 | 16.11 | 2.25x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 95 | 56.57 | 21.79 | 2.60x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 95 | 75.98 | 27.91 | 2.72x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 95 | 87.80 | 33.52 | 2.62x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 95 | 93.25 | 39.02 | 2.39x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 95 | 93.37 | 39.25 | 2.38x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 95 | 93.37 | 39.25 | 2.38x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 103 | 11.30 | 8.12 | 1.39x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 103 | 21.06 | 11.47 | 1.84x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 103 | 36.89 | 16.56 | 2.23x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 103 | 58.29 | 22.49 | 2.59x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 103 | 79.62 | 28.95 | 2.75x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 103 | 93.46 | 34.93 | 2.68x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 103 | 100.40 | 40.84 | 2.46x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 103 | 100.57 | 41.08 | 2.45x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 103 | 100.57 | 41.08 | 2.45x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 111 | 11.34 | 8.26 | 1.37x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 111 | 21.22 | 11.67 | 1.82x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 111 | 37.44 | 16.97 | 2.21x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 111 | 59.81 | 23.14 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 111 | 82.95 | 29.94 | 2.77x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 111 | 98.78 | 36.26 | 2.72x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 111 | 107.35 | 42.56 | 2.52x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 117 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 117 | 11.37 | 8.36 | 1.36x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 117 | 21.33 | 11.81 | 1.81x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 117 | 37.80 | 17.26 | 2.19x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 117 | 60.85 | 23.59 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 117 | 85.27 | 30.64 | 2.78x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 117 | 102.57 | 37.22 | 2.76x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 117 | 112.41 | 43.79 | 2.57x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 117 | 112.67 | 44.07 | 2.56x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 117 | 112.67 | 44.07 | 2.56x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 121 | 5.88 | 5.39 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 121 | 11.38 | 8.43 | 1.35x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 121 | 21.39 | 11.90 | 1.80x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 121 | 38.02 | 17.44 | 2.18x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 121 | 61.50 | 23.88 | 2.57x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 121 | 86.73 | 31.09 | 2.79x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 121 | 105.01 | 37.83 | 2.78x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 121 | 115.71 | 44.59 | 2.59x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 121 | 116.00 | 44.88 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 121 | 116.00 | 44.88 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 122 | 5.88 | 5.39 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 122 | 11.39 | 8.44 | 1.35x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 122 | 21.41 | 11.93 | 1.79x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 122 | 38.08 | 17.49 | 2.18x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 122 | 61.66 | 23.95 | 2.57x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 122 | 87.09 | 31.20 | 2.79x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 122 | 105.60 | 37.98 | 2.78x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 122 | 116.53 | 44.79 | 2.60x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 122 | 116.83 | 45.08 | 2.59x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 122 | 116.83 | 45.08 | 2.59x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 126 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 126 | 11.40 | 8.50 | 1.34x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 126 | 21.47 | 12.02 | 1.79x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 126 | 38.29 | 17.66 | 2.17x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 126 | 62.26 | 24.23 | 2.57x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 126 | 88.47 | 31.63 | 2.80x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 126 | 107.95 | 38.58 | 2.80x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 126 | 119.76 | 45.56 | 2.63x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 126 | 120.09 | 45.86 | 2.62x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 126 | 120.09 | 45.86 | 2.62x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 130 | 11.42 | 8.56 | 1.33x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 130 | 21.53 | 12.10 | 1.78x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 130 | 38.48 | 17.83 | 2.16x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 130 | 62.84 | 24.50 | 2.57x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 130 | 89.81 | 32.05 | 2.80x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 130 | 110.22 | 39.16 | 2.81x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 130 | 122.94 | 46.32 | 2.65x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 130 | 123.30 | 46.63 | 2.64x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 130 | 123.30 | 46.63 | 2.64x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 132 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 132 | 11.43 | 8.59 | 1.33x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 132 | 21.55 | 12.15 | 1.77x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 132 | 38.58 | 17.92 | 2.15x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 132 | 63.12 | 24.63 | 2.56x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 132 | 90.45 | 32.25 | 2.80x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 132 | 111.33 | 39.45 | 2.82x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 132 | 124.50 | 46.70 | 2.67x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 132 | 124.88 | 47.00 | 2.66x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 132 | 124.88 | 47.00 | 2.66x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 136 | 11.44 | 8.65 | 1.32x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 136 | 21.61 | 12.23 | 1.77x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 136 | 38.76 | 18.08 | 2.14x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 136 | 63.66 | 24.88 | 2.56x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 136 | 91.71 | 32.65 | 2.81x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 136 | 113.51 | 40.01 | 2.84x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 136 | 127.59 | 47.43 | 2.69x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 136 | 128.01 | 47.75 | 2.68x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 136 | 128.01 | 47.75 | 2.68x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 189 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 189 | 11.57 | 9.24 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 189 | 22.10 | 13.21 | 1.67x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 189 | 40.50 | 19.73 | 2.05x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 189 | 68.94 | 27.71 | 2.49x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 189 | 104.62 | 37.20 | 2.81x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 189 | 137.16 | 46.39 | 2.96x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 189 | 163.45 | 55.93 | 2.92x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 189 | 164.35 | 56.34 | 2.92x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 189 | 164.35 | 56.34 | 2.92x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 204 | 11.59 | 9.37 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 204 | 22.20 | 13.45 | 1.65x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 204 | 40.84 | 20.08 | 2.03x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 204 | 70.00 | 28.39 | 2.47x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 204 | 107.35 | 38.32 | 2.80x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 204 | 142.45 | 47.95 | 2.97x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 204 | 172.04 | 58.00 | 2.97x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 204 | 173.09 | 58.43 | 2.96x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 204 | 173.09 | 58.43 | 2.96x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 253 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 253 | 11.65 | 9.72 | 1.20x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 253 | 22.43 | 14.17 | 1.58x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 253 | 41.68 | 21.01 | 1.98x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 253 | 72.69 | 30.43 | 2.39x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 253 | 114.43 | 41.50 | 2.76x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 253 | 156.68 | 52.39 | 2.99x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 253 | 196.20 | 64.04 | 3.06x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 253 | 197.71 | 64.55 | 3.06x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 253 | 197.71 | 64.55 | 3.06x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 272 | 11.67 | 9.83 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 272 | 22.50 | 14.42 | 1.56x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 272 | 41.93 | 21.30 | 1.97x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 272 | 73.50 | 31.15 | 2.36x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 272 | 116.61 | 42.56 | 2.74x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 272 | 161.21 | 53.89 | 2.99x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 272 | 204.20 | 66.11 | 3.09x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 272 | 205.88 | 66.65 | 3.09x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 272 | 205.88 | 66.65 | 3.09x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 335 | 11.71 | 10.13 | 1.16x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 335 | 22.67 | 15.17 | 1.49x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 335 | 42.57 | 22.14 | 1.92x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 335 | 75.58 | 33.24 | 2.27x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 335 | 122.34 | 45.48 | 2.69x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 335 | 173.40 | 58.23 | 2.98x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 335 | 226.52 | 72.22 | 3.14x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 336 | 11.71 | 10.14 | 1.16x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 336 | 22.68 | 15.18 | 1.49x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 336 | 42.57 | 22.15 | 1.92x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 336 | 75.61 | 33.27 | 2.27x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 336 | 122.42 | 45.52 | 2.69x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 336 | 173.56 | 58.30 | 2.98x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 336 | 226.83 | 72.31 | 3.14x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 448 | 11.76 | 10.50 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 448 | 22.87 | 16.25 | 1.41x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 448 | 43.27 | 23.34 | 1.85x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 448 | 77.94 | 36.03 | 2.16x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 448 | 129.03 | 49.47 | 2.61x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 448 | 188.21 | 64.80 | 2.90x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 448 | 255.15 | 81.21 | 3.14x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 672 | 11.81 | 10.91 | 1.08x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 672 | 23.06 | 17.73 | 1.30x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 672 | 43.98 | 25.33 | 1.74x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 672 | 80.37 | 39.17 | 2.05x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 672 | 136.13 | 55.89 | 2.44x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 672 | 204.63 | 73.69 | 2.78x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 672 | 288.80 | 93.78 | 3.08x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 672 | 292.67 | 94.67 | 3.09x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 672 | 292.67 | 94.67 | 3.09x |

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
| gpu | DeepSeek-V4.1-Flash-engram-host | 1 | 368.98 | 16.9% |
| rom | DeepSeek-V4.1-Flash-engram-host | 1 | 149.56 | 76.0% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash-engram-host | sram | interleaved | 128 B | 1.77x |
| DeepSeek-V4.1-Flash-engram-host | hbm | interleaved | 32 B | 1.34x |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 33 | 17.12% | 23.94 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 2 | 33 | 17.12% | 23.94 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 4 | 33 | 17.12% | 23.94 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 8 | 1 | 0.47% | 1.14 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 16 | 1 | 0.47% | 1.14 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 1 | 0.47% | 1.14 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 64 | 1 | 0.53% | 1.28 | 4.24 |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 332.8 | 23,630.5 |
| DeepSeek-V4.1-Flash-engram-host | 2 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 332.8 | 23,630.5 |
| DeepSeek-V4.1-Flash-engram-host | 4 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 332.8 | 23,630.5 |
| DeepSeek-V4.1-Flash-engram-host | 8 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 332.8 | 23,630.5 |
| DeepSeek-V4.1-Flash-engram-host | 16 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 332.8 | 23,630.5 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 332.8 | 23,630.5 |
| DeepSeek-V4.1-Flash-engram-host | 64 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 332.8 | 23,630.5 |
| DeepSeek-V4.1-Flash-engram-host | 256 | 5.52% | 24.5 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 94.1 | 24,090.9 |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 20.32% | 67.2 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 23.6 | 24,151.2 |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 59.69% | 180.9 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 5.9 | 24,056.4 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 6 |
| gpu | link_latency | 830 |
| gpu | weight_read | 684 |
| rom | compute | 692 |
| rom | infeasible | 2292 |
| rom | kv_read | 151 |
| rom | layer_fixed_latency | 548 |
| rom | link_latency | 1058 |
| rom | weight_read | 499 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2292 |

## Mechanical consistency audit

**FAIL** over 141,419 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x64', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x69', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x76', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x80', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x83', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x85', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x96', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x128', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x192', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x256', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x64', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x69', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x76', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x80', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x83', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x85', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x96', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x128', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x192', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x256', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x64', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x69', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x76', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x80', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x83', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x85', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x96', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x128', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x192', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x256', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-pipeline-x64', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-pipeline-x69', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-pipeline-x76', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-pipeline-x80', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-pipeline-x83', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-pipeline-x85', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-pipeline-x96', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N6-native-SRAMKV-array-pipeline-x113', 'DeepSeek-V4.1-Flash-engram-host', 1)

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

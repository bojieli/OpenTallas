# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash-engram-hbm-1m

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash-engram-hbm at 1,000,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 73x (ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream, 398 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 136 devices. On the GPU side the correction reaches 9x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 53 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-hbm takes 87 x 815 mm2 (70,905 mm2, array, KV in HBM) at 4,202 tok/s per user and 59 tok/s per 1,000 mm2, holding 6,789 sessions, against 86 copies of one unified HBM die at the same silicon: 11.4x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-hbm on 508,475 mm2 of ROM silicon at 4,989 tok/s per user against 508,816 mm2 of a100_sxm_80gb-x616-hybrid at 356 tok/s: **14.0x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 49,111. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on DeepSeek-V4.1-Flash-engram-hbm at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 1,161 us of link latency per token; but the model has 40 layers, so at most 40 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 1,054 us. The iso-area per-user ratio at that point falls from 14.6x to 14.0x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 3.11x to it.** At 58,680 mm2 on DeepSeek-V4.1-Flash-engram-hbm the pipeline-only GPU delivers 118.92 tok/s and the same silicon running hybrid delivers 370 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.01x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `link_latency`) to 9.46x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-hbm engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 324 to 23,783 tok/s, and its rate with every slot occupied from 23,327 to 23,783. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 72 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 189.6 us and cap it at 5,276 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 92 of 4460 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 51.7x of aggregate throughput (DeepSeek-V4.1-Flash-engram-hbm). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 14.21x, on DeepSeek-V4.1-Flash-engram-hbm at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

**Recommended: `ROM-N6-native-HBMKV-array-hw-hybrid-x87`** -- 87 x 815 mm2 reticle dies, 70,905 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **4,202.1 tok/s per user** (0.24 ms/token), binding on `layer_fixed_latency`
- **59.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 25,212 tok/s aggregate with every slot full, over 6,789 resident sessions (fill limited by `pipeline_slots`)
- 7,041 W at 0.099 W/mm2, 1,510.1 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 86 copies of one unified HBM die -- `a100_sxm_80gb-x86-hybrid`, 71,036 mm2, area ratio 0.9982 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 70,905 | 71,036 | 0.9982 |
| user tok/s | 4,202.1 | 367.9 | 11.42x |
| aggregate tok/s | 25,212 | 4,047 | 2.47x |
| resident sessions | 6,789 | 6,364 | -- |
| J/token | 1.5101 | 35.1477 | 23.3x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 6,789 sessions against one that holds 6,364 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 372.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x136` | 110,840 | 4,809.6 | 43.4 | 10,741 | 13.15x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 508,475 | 4,989.2 | 9.8 | 1 | 14.02x |
| smallest feasible machine | `ROM-N6-native-HBMKV-array-hw-tensor-x72` | 58,680 | 2,773.7 | 47.3 | 5,579 | 7.49x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 70,905 | 4,202.1 | 59.3 | 6,789 | 11.42x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 70,905 | 4,202.1 | 59.3 | -- | 59.3 | ACCEPT |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x93` | 75,795 | 4,398.0 | 58.0 | 40.1 | 59.3 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x104` | 84,760 | 4,508.5 | 53.2 | 22.1 | 59.3 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x112-romfill` | 91,280 | 4,663.3 | 51.1 | 22.6 | 59.3 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 101,060 | 4,702.2 | 46.5 | 16.6 | 59.3 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x136` | 110,840 | 4,809.6 | 43.4 | 15.2 | 59.3 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x156` | 127,140 | 4,872.8 | 38.3 | 11.9 | 59.3 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 127,955 | 4,881.0 | 38.1 | 11.9 | 59.3 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 4,928.4 | 21.3 | 4.5 | 59.3 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,929.8 | 17.8 | 3.5 | 59.3 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x8-romfill` | 369,800 | 4,970.9 | 13.4 | 2.6 | 59.3 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 508,475 | 4,989.2 | 9.8 | 1.8 | 59.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x87` **<-- recommended** | 70,905 | 87 | 4,202.1 | 25,212 | 59.3 | 6,789 | `layer_fixed_latency` | 7,041 | 1,510.1 | `a100_sxm_80gb-x86-hybrid` | 11.42x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x93` | 75,795 | 93 | 4,398.0 | 26,388 | 58.0 | 7,273 | `layer_fixed_latency` | 7,873 | 1,624.6 | `a100_sxm_80gb-x92-hybrid` | 12.05x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x104` | 84,760 | 104 | 4,508.5 | 31,560 | 53.2 | 8,160 | `layer_fixed_latency` | 9,498 | 1,908.1 | `a100_sxm_80gb-x103-hybrid` | 12.23x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x112-romfill` | 91,280 | 112 | 4,663.3 | 32,643 | 51.1 | 8,806 | `layer_fixed_latency` | 10,591 | 2,072.6 | `a100_sxm_80gb-x111-hybrid` | 12.67x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 101,060 | 124 | 4,702.2 | 37,618 | 46.5 | 9,773 | `layer_fixed_latency` | 12,342 | 2,393.1 | `a100_sxm_80gb-x122-hybrid` | 12.98x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x136` | 110,840 | 136 | 4,809.6 | 81,764 | 43.4 | 10,741 | `layer_fixed_latency` | 15,389 | 2,670.1 | `a100_sxm_80gb-x134-hybrid` | 13.15x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x156` | 127,140 | 156 | 4,872.8 | 97,456 | 38.3 | 12,354 | `layer_fixed_latency` | 18,552 | 3,178.4 | `a100_sxm_80gb-x154-hybrid` | 13.48x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 127,955 | 157 | 4,881.0 | 97,620 | 38.1 | 12,435 | `layer_fixed_latency` | 18,689 | 3,200.3 | `a100_sxm_80gb-x155-hybrid` | 13.47x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 5 | 4,928.4 | 4,928 | 21.3 | 1 | `layer_fixed_latency` | 19,645 | 3,986.1 | `a100_sxm_80gb-x280-hybrid` | 13.75x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x6-romfill` | 277,350 | 6 | 4,929.8 | 4,930 | 17.8 | 1 | `layer_fixed_latency` | 20,877 | 4,234.8 | `a100_sxm_80gb-x336-hybrid` | 13.85x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x8-romfill` | 369,800 | 8 | 4,970.9 | 4,971 | 13.4 | 1 | `layer_fixed_latency` | 29,175 | 5,869.1 | `a100_sxm_80gb-x448-hybrid` | 13.97x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 508,475 | 11 | 4,989.2 | 4,989 | 9.8 | 1 | `layer_fixed_latency` | 41,621 | 8,342.2 | `a100_sxm_80gb-x616-hybrid` | 14.02x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 318 | densest | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 70,905 | 4,202.1 | 59.3 | 6,789 |
| array | 318 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 127,955 | 4,881.0 | 38.1 | 12,435 |
| array | 318 | smallest | `ROM-N6-native-HBMKV-array-hw-tensor-x72` | 58,680 | 2,773.7 | 47.3 | 5,579 |
| wafer | 57 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 4,832.5 | 26.1 | 1 |
| wafer | 57 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 508,475 | 4,989.2 | 9.8 | 1 |
| wafer | 57 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,533.0 | 25.5 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 127,955 | 4,881.0 | 97,620 | 12,435 | 18,689 | 3,200.3 | `layer_fixed_latency` | `a100_sxm_80gb-x155-hybrid` | 362.2 | 11,929 | 63,182.5 | 0.999 | 13.47x | 19.7x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill` | 508,475 | 4,989.2 | 4,989 | 1 | 41,621 | 8,342.2 | `layer_fixed_latency` | `a100_sxm_80gb-x616-hybrid` | 356.0 | 49,111 | 251,267.5 | 0.999 | 14.02x | 30.1x |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 127,955 | 4,881.0 | 97,620 | 12,435 | 18,689 | 1,616.7 | `layer_fixed_latency` | `a100_sxm_80gb-x155-hybrid` | 362.2 | 11,929 | 32,291.0 | 0.999 | 13.47x | 20.0x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 369,800 | 4,273.7 | 64,105 | 5,321 | 51,413 | 5,800.0 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 356.0 | 35,561 | 92,260.6 | 0.999 | 12.01x | 15.9x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 127,955 | 4,881.0 | 97,620 | 12,435 | 18,689 | 824.9 | `layer_fixed_latency` | `a100_sxm_80gb-x155-hybrid` | 362.2 | 11,929 | 16,845.3 | 0.999 | 13.47x | 20.4x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 369,800 | 4,273.7 | 64,105 | 5,321 | 51,413 | 2,916.5 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 356.0 | 35,561 | 46,830.1 | 0.999 | 12.01x | 16.1x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 127,955 | 4,881.0 | 97,620 | 12,435 | 18,689 | 429.0 | `layer_fixed_latency` | `a100_sxm_80gb-x155-hybrid` | 362.2 | 11,929 | 9,122.4 | 0.999 | 13.47x | 21.3x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 369,800 | 4,273.7 | 64,105 | 5,321 | 51,413 | 1,474.8 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 356.0 | 35,561 | 24,114.8 | 0.999 | 12.01x | 16.4x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x157` | 127,955 | 4,881.0 | 97,620 | 12,435 | 18,689 | 231.0 | `layer_fixed_latency` | `a100_sxm_80gb-x155-hybrid` | 362.2 | 11,929 | 5,261.0 | 0.999 | 13.47x | 22.8x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,267.0 | 93,874 | 8,096 | 79,690 | 1,154.8 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 356.0 | 53,627 | 18,436.0 | 0.999 | 11.99x | 16.0x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 4,654.1 | 162,894 | 22,033 | 30,373 | 200.8 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 358.9 | 21,366 | 4,818.8 | 1.001 | 12.97x | 24.0x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,079.4 | 175,414 | 8,096 | 82,389 | 619.8 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 356.0 | 53,627 | 9,917.8 | 0.999 | 11.46x | 16.0x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 4,200.2 | 289,814 | 22,033 | 34,573 | 126.0 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 319.1 | 21,366 | 2,899.6 | 1.001 | 13.16x | 23.0x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,615.9 | 231,416 | 8,096 | 84,040 | 363.2 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 356.0 | 53,627 | 5,658.6 | 0.999 | 10.16x | 15.6x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 224,940 | 2,413.0 | 617,725 | 22,033 | 50,419 | 81.6 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 189.4 | 21,366 | 1,409.0 | 1.001 | 12.74x | 17.3x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,901.6 | 486,806 | 8,096 | 92,263 | 189.5 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 275.1 | 53,627 | 2,167.7 | 0.999 | 6.91x | 11.4x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 1,032.0 | 1,056,739 | 27,195 | 71,935 | 68.1 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 90.7 | 26,447 | 1,058.4 | 1.001 | 11.37x | 15.5x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 601.7 | 616,177 | 8,096 | 96,425 | 156.5 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 141.3 | 53,627 | 1,303.0 | 0.999 | 4.26x | 8.3x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 329.6 | 1,350,176 | 27,195 | 80,603 | 59.7 | `compute` | `a100_sxm_80gb-x335-hybrid` | 34.8 | 26,447 | 621.7 | 1.001 | 9.46x | 10.4x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 157.6 | 645,354 | 8,096 | 96,484 | 149.5 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 55.6 | 53,627 | 889.4 | 0.999 | 2.84x | 5.9x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-8 | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 70,905 | array | HBM | 6,789 |
| 16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x93` | 75,795 | array | HBM | 7,273 |
| 32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 8,886 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 101,060 | array | HBM | 9,773 |
| 256 | `ROM-N6-native-HBMKV-array-hw-pipeline-x170` | 138,550 | array | HBM | 13,484 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 224,940 | array | HBM | 22,033 |
| 4096 | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | array | HBM | 27,195 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | rom | 72, 75, 87, 93, 104, 112, 113, 124, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | sram | 72, 75, 87, 93, 104, 113, 136, 138, 156, 157, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | rom | 168, 170, 179, 197, 207, 214, 227, 248, 330, 340, 365, 370 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | sram | 168, 170, 179, 198, 207, 227, 244, 248, 249, 250, 330, 340 |

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
| DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 1 | 16 | 6.25 | hierarchical, one_shot | 146.54 | 45.99 | 49.56 | 31.26 | 4,202.1 |
| DeepSeek-V4.1-Flash-engram-hbm | `ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 64 | 2 | 5.25 | one_shot, two_step | 180.32 | 8.05 | 528.59 | 14.43 | 1,445.4 |
| DeepSeek-V4.1-Flash-engram-hbm | `a100_sxm_80gb-x86-hybrid` | 1 | 8 | 5.25 | measured_floor | 860.60 | 941.85 | 1,029.22 | 441.62 | 367.9 |
| DeepSeek-V4.1-Flash-engram-hbm | `a100_sxm_80gb-x86-hybrid` | 64 | 8 | 5.25 | measured_floor | 860.60 | 1,108.20 | 2,732.89 | 495.89 | 226.9 |

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

- **0 of 4,460 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 35%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,751 | 0 | 51.7% | 79.8% | 0.387 | 70% |
| rom | wafer (>=40,000 mm2) | 2,709 | 0 | 23.0% | 58.3% | 0.291 | 92% |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 110,840 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x136` | 2.670145 | 15,389.0 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x134-hybrid` | 54.288036 | 28,051.0 | link_latency | 20.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 91,280 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x112-romfill` | 1.052866 | 10,591.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-hybrid` | 23.168398 | 23,239.1 | link_latency | 22.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 91,280 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x112-romfill` | 0.542979 | 10,591.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-hybrid` | 12.283963 | 23,239.1 | link_latency | 22.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 101,060 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 0.328091 | 12,342.0 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-hybrid` | 7.477300 | 25,727.2 | link_latency | 22.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 101,060 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 0.180738 | 13,584.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-hybrid` | 4.438414 | 25,727.2 | link_latency | 24.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 127,140 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x156` | 0.140323 | 21,091.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x154-hybrid` | 3.143001 | 33,572.1 | weight_read | 22.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 224,940 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 0.126029 | 34,573.2 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid` | 2.899632 | 59,208.4 | weight_read | 23.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 224,940 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 0.081621 | 50,419.1 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid` | 1.408979 | 68,328.4 | weight_read | 17.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.068073 | 71,935.1 | weight_read | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid` | 1.058384 | 98,342.7 | weight_read | 15.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.059698 | 80,603.1 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid` | 0.621727 | 88,736.7 | weight_read | 10.41x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 3 | 138,675 | 5,008.0 | wafer-pipeline | 3,533.0 | wafer-hybrid | 1.42x | 996.8 | pipeline | 365.5 | hybrid | 2.73x | 5.02x | 9.66x | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 184,900 | 5,350.7 | wafer-pipeline | 4,832.5 | wafer-hybrid | 1.11x | 1,007.5 | pipeline | 362.0 | hybrid | 2.78x | 5.31x | 13.35x | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 6 | 277,350 | 5,356.0 | wafer-pipeline | 4,929.8 | wafer-hybrid | 1.09x | 1,018.4 | pipeline | 356.0 | hybrid | 2.86x | 5.26x | 13.85x | 2.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 369,800 | 5,356.0 | wafer-pipeline | 4,970.9 | wafer-hybrid | 1.08x | 1,023.9 | pipeline | 356.0 | hybrid | 2.88x | 5.23x | 13.97x | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 12 | 554,700 | 5,356.9 | wafer-pipeline | 4,988.8 | wafer-hybrid | 1.07x | 1,029.6 | pipeline | 356.0 | hybrid | 2.89x | 5.20x | 14.02x | 2.69x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.92x to 2.69x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-hybrid-x11-romfill | 508,475 | 4,989.2 | 4,989.2 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x616-hybrid | 508,816 | 1.00x | hybrid | 1,054.14 | 356.0 | 27,408.2 | link_latency | 14.02x | 0.07x | 41.95x | 14.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x72 | 58,680 | 2,773.7 | 2,773.7 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 934.09 | 370.1 | 3,331.0 | link_latency | 7.49x | 0.33x | 23.32x | 7.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x157 | 127,955 | 4,881.0 | 97,619.9 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x155-hybrid | 128,030 | 1.00x | hybrid | 976.60 | 362.2 | 7,244.6 | link_latency | 13.47x | 5.30x | 41.04x | 13.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x72 | 58,680 | 2,722.5 | 8,167.5 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 934.09 | 370.1 | 3,331.0 | link_latency | 7.36x | 0.97x | 22.89x | 7.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x157 | 127,955 | 4,881.0 | 97,619.9 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x155-hybrid | 128,030 | 1.00x | hybrid | 976.60 | 362.2 | 7,244.6 | link_latency | 13.47x | 5.30x | 41.04x | 13.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x72 | 58,680 | 2,460.7 | 12,303.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 934.09 | 370.1 | 3,331.0 | link_latency | 6.65x | 1.46x | 20.69x | 6.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x157 | 127,955 | 4,881.0 | 97,619.9 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x155-hybrid | 128,030 | 1.00x | hybrid | 976.60 | 362.2 | 7,244.6 | link_latency | 13.47x | 5.30x | 41.04x | 13.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x72 | 58,680 | 1,831.4 | 16,482.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 934.09 | 370.1 | 3,331.0 | link_latency | 4.95x | 1.95x | 15.40x | 4.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x157 | 127,955 | 4,881.0 | 97,619.9 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x155-hybrid | 128,030 | 1.00x | hybrid | 976.60 | 362.2 | 7,244.6 | link_latency | 13.47x | 5.30x | 41.04x | 13.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x72 | 58,680 | 1,162.7 | 18,603.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 958.05 | 335.9 | 5,375.0 | weight_read | 3.46x | 2.20x | 9.78x | 3.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 4,654.1 | 162,893.8 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 1,030.84 | 358.9 | 12,203.5 | link_latency | 12.97x | 5.04x | 39.14x | 12.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x72 | 58,680 | 668.3 | 21,386.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 1,012.84 | 278.2 | 8,903.1 | weight_read | 2.40x | 2.40x | 5.62x | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 4,200.2 | 289,814.2 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 1,098.62 | 319.1 | 20,419.3 | weight_read | 13.16x | 8.96x | 35.32x | 13.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x72 | 58,680 | 355.9 | 22,774.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 1,122.41 | 208.9 | 13,372.6 | weight_read | 1.70x | 1.70x | 2.99x | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276 | 224,940 | 2,413.0 | 617,725.4 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 1,532.43 | 189.4 | 48,495.0 | weight_read | 12.74x | 12.74x | 20.29x | 12.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x72 | 58,680 | 92.7 | 23,737.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 1,574.72 | 90.9 | 23,269.0 | weight_read | 1.02x | 1.02x | 1.42x | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1,032.0 | 1,056,738.5 | weight_read | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,401.10 | 90.7 | 92,917.8 | weight_read | 11.37x | 11.37x | 14.34x | 11.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x72 | 58,680 | 23.3 | 23,821.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 4,189.07 | 39.8 | 40,803.8 | weight_read | 0.58x | 0.58x | 1.00x | 0.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 329.6 | 1,350,176.3 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 9,325.40 | 34.8 | 142,726.1 | weight_read | 9.46x | 9.46x | 12.42x | 9.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x72 | 58,680 | 5.8 | 23,783.3 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | 58,646 | 1.00x | hybrid | 15,546.70 | 21.6 | 88,549.6 | weight_read | 0.27x | 0.27x | 0.69x | 0.27x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 53 | 43,778 | 118.9 | 287.1 | 366.0 | hybrid | 926.32 | 33.9% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 56 | 46,256 | 118.9 | 287.4 | 372.9 | hybrid | 926.32 | 34.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 58 | 47,908 | 118.9 | 287.1 | 360.0 | hybrid | 930.12 | 33.5% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 71 | 58,646 | 118.9 | 259.7 | 370.1 | hybrid | 934.09 | 34.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 74 | 61,124 | 118.9 | 259.5 | 361.6 | hybrid | 937.89 | 33.9% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 86 | 71,036 | 118.9 | 259.2 | 367.9 | hybrid | 941.85 | 34.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 92 | 75,992 | 118.9 | 258.8 | 365.0 | hybrid | 945.66 | 34.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 103 | 85,078 | 118.9 | 258.3 | 368.5 | hybrid | 949.62 | 35.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 111 | 91,686 | 118.9 | 257.8 | 368.1 | hybrid | 953.29 | 35.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 112 | 92,512 | 118.9 | 257.7 | 369.2 | hybrid | 953.29 | 35.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 122 | 100,772 | 118.9 | 257.0 | 362.3 | hybrid | 961.06 | 34.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 134 | 110,684 | 118.9 | 256.1 | 365.8 | hybrid | 965.03 | 35.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 136 | 112,336 | 118.9 | 255.9 | 367.6 | hybrid | 965.03 | 35.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 154 | 127,204 | 118.9 | 254.5 | 361.4 | hybrid | 976.60 | 35.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 155 | 128,030 | 118.9 | 254.5 | 362.2 | hybrid | 976.60 | 35.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 161 | 132,986 | 118.9 | 254.0 | 360.4 | hybrid | 980.40 | 35.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 166 | 137,116 | 118.9 | 253.6 | 364.1 | hybrid | 980.40 | 35.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 168 | 138,768 | 118.9 | 253.5 | 365.5 | hybrid | 980.40 | 35.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 177 | 146,202 | 118.9 | 252.7 | 359.9 | hybrid | 988.17 | 35.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 183 | 151,158 | 118.9 | 252.3 | 363.9 | hybrid | 988.17 | 36.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 194 | 160,244 | 118.9 | 251.3 | 359.9 | hybrid | 995.93 | 35.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 195 | 161,070 | 118.9 | 251.3 | 360.5 | hybrid | 995.93 | 35.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 204 | 168,504 | 118.9 | 250.6 | 360.7 | hybrid | 999.90 | 36.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 211 | 174,286 | 118.9 | 250.0 | 359.7 | hybrid | 1,003.57 | 36.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 224 | 185,024 | 118.9 | 249.0 | 362.0 | hybrid | 1,007.54 | 36.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 241 | 199,066 | 118.9 | 247.6 | 357.1 | hybrid | 1,019.11 | 36.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 245 | 202,370 | 118.9 | 247.3 | 359.0 | hybrid | 1,019.11 | 36.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 246 | 203,196 | 118.9 | 247.2 | 359.5 | hybrid | 1,019.11 | 36.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 247 | 204,022 | 118.9 | 247.1 | 360.0 | hybrid | 1,019.11 | 36.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 272 | 224,672 | 118.9 | 245.1 | 358.9 | hybrid | 1,030.84 | 37.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 280 | 231,280 | 118.9 | 244.4 | 358.4 | hybrid | 1,034.64 | 37.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 308 | 254,408 | 118.9 | 242.2 | 355.0 | hybrid | 1,050.18 | 37.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 326 | 269,276 | 118.9 | 204.9 | 355.3 | hybrid | 1,054.14 | 37.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 335 | 276,710 | 118.9 | 204.4 | 355.6 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 336 | 277,536 | 118.9 | 204.3 | 356.0 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 360 | 297,360 | 118.9 | 203.0 | 356.0 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 365 | 301,490 | 118.9 | 202.7 | 355.0 | hybrid | 1,054.14 | 37.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 377 | 311,402 | 118.9 | 202.0 | 353.9 | hybrid | 1,054.14 | 37.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 378 | 312,228 | 118.9 | 202.0 | 354.2 | hybrid | 1,054.14 | 37.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 392 | 323,792 | 118.9 | 201.2 | 356.0 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 448 | 370,048 | 118.9 | 198.1 | 356.0 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 504 | 416,304 | 118.9 | 195.1 | 356.0 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 616 | 508,816 | 118.9 | 189.4 | 356.0 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 672 | 555,072 | 118.9 | 186.6 | 356.0 | hybrid | 1,054.14 | 37.5% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x250 | DeepSeek-V4.1-Flash-engram-hbm | 250 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x179 | DeepSeek-V4.1-Flash-engram-hbm | 179 | tensor | rom_package_ucie | rom_board_serdes | 160 | 109.00 us | 917.5 tok/s | 9,174.7 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 45 on rom_board_serdes (traversals 13.2) = 106.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x244 | DeepSeek-V4.1-Flash-engram-hbm | 244 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x249 | DeepSeek-V4.1-Flash-engram-hbm | 249 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x5 | DeepSeek-V4.1-Flash-engram-hbm | 5 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x168 | DeepSeek-V4.1-Flash-engram-hbm | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.87 us | 581.8 tok/s | 5,818.2 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 17.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hybrid-x198 | DeepSeek-V4.1-Flash-engram-hbm | 198 | hybrid | nvlink3 | infiniband_hdr | 104 | 465.72 us | 214.7 tok/s | 2,147.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 58.55 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | DeepSeek-V4.1-Flash-engram-hbm | 4 | hybrid | on_wafer | rom_wafer_serdes | 83 | 154.31 us | 648.1 tok/s | 6,480.7 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x157 | DeepSeek-V4.1-Flash-engram-hbm | 157 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x75 | DeepSeek-V4.1-Flash-engram-hbm | 75 | tensor | rom_package_ucie | rom_board_serdes | 160 | 73.75 us | 1,355.9 tok/s | 13,558.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 19 on rom_board_serdes (traversals 8.8) = 71.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x136 | DeepSeek-V4.1-Flash-engram-hbm | 136 | hybrid | rom_package_ucie | rom_board_serdes | 113 | 5.55 us | 18,022.8 tok/s | 180,227.8 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 33 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-pipeline-x156 | DeepSeek-V4.1-Flash-engram-hbm | 156 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7 | DeepSeek-V4.1-Flash-engram-hbm | 7 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-tensor-x72 | DeepSeek-V4.1-Flash-engram-hbm | 72 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x7 | DeepSeek-V4.1-Flash-engram-hbm | 7 | tensor | on_wafer | rom_wafer_serdes | 160 | 189.55 us | 527.6 tok/s | 5,275.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 7 on rom_wafer_serdes (traversals 4.4) = 35.55 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x93 | DeepSeek-V4.1-Flash-engram-hbm | 93 | hybrid | nvlink3 | infiniband_hdr | 91 | 434.00 us | 230.4 tok/s | 2,304.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 26.84 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7 | DeepSeek-V4.1-Flash-engram-hbm | 7 | hybrid | on_wafer | rom_wafer_serdes | 86 | 154.61 us | 646.8 tok/s | 6,467.9 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 6 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.61 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x53-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 53 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x53-tensor | DeepSeek-V4.1-Flash-engram-hbm | 53 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x53-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 53 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x53-expert | DeepSeek-V4.1-Flash-engram-hbm | 53 | expert | nvlink3 | infiniband_hdr | 160 | 567.30 us | 176.3 tok/s | 1,762.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 166.11 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash-engram-hbm | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-expert | DeepSeek-V4.1-Flash-engram-hbm | 56 | expert | nvlink3 | infiniband_hdr | 160 | 566.93 us | 176.4 tok/s | 1,763.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x58-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 58 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x58-tensor | DeepSeek-V4.1-Flash-engram-hbm | 58 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x58-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 58 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x58-expert | DeepSeek-V4.1-Flash-engram-hbm | 58 | expert | nvlink3 | infiniband_hdr | 160 | 566.81 us | 176.4 tok/s | 1,764.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 71 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-tensor | DeepSeek-V4.1-Flash-engram-hbm | 71 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 71 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-expert | DeepSeek-V4.1-Flash-engram-hbm | 71 | expert | nvlink3 | infiniband_hdr | 160 | 566.07 us | 176.7 tok/s | 1,766.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.90 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 74 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-tensor | DeepSeek-V4.1-Flash-engram-hbm | 74 | tensor | nvlink3 | infiniband_hdr | 160 | 820.44 us | 121.9 tok/s | 1,218.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 413.27 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 74 | hybrid | nvlink3 | infiniband_hdr | 89 | 429.12 us | 233.0 tok/s | 2,330.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x74-expert | DeepSeek-V4.1-Flash-engram-hbm | 74 | expert | nvlink3 | infiniband_hdr | 160 | 565.85 us | 176.7 tok/s | 1,767.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.80 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 86 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-tensor | DeepSeek-V4.1-Flash-engram-hbm | 86 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 86 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-expert | DeepSeek-V4.1-Flash-engram-hbm | 86 | expert | nvlink3 | infiniband_hdr | 160 | 565.40 us | 176.9 tok/s | 1,768.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.72 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x92-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 92 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x92-tensor | DeepSeek-V4.1-Flash-engram-hbm | 92 | tensor | nvlink3 | infiniband_hdr | 160 | 822.08 us | 121.6 tok/s | 1,216.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 414.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x92-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 92 | hybrid | nvlink3 | infiniband_hdr | 91 | 434.00 us | 230.4 tok/s | 2,304.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 26.84 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x92-expert | DeepSeek-V4.1-Flash-engram-hbm | 92 | expert | nvlink3 | infiniband_hdr | 160 | 565.19 us | 176.9 tok/s | 1,769.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.65 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.54 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 122 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-tensor | DeepSeek-V4.1-Flash-engram-hbm | 122 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 122 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-expert | DeepSeek-V4.1-Flash-engram-hbm | 122 | expert | nvlink3 | infiniband_hdr | 160 | 564.49 us | 177.2 tok/s | 1,771.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.01 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x134-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 134 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x134-tensor | DeepSeek-V4.1-Flash-engram-hbm | 134 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x134-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 134 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x134-expert | DeepSeek-V4.1-Flash-engram-hbm | 134 | expert | nvlink3 | infiniband_hdr | 160 | 564.32 us | 177.2 tok/s | 1,772.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 136 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-tensor | DeepSeek-V4.1-Flash-engram-hbm | 136 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 136 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-expert | DeepSeek-V4.1-Flash-engram-hbm | 136 | expert | nvlink3 | infiniband_hdr | 160 | 564.27 us | 177.2 tok/s | 1,772.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.85 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x154-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 154 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x154-tensor | DeepSeek-V4.1-Flash-engram-hbm | 154 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x154-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 154 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x154-expert | DeepSeek-V4.1-Flash-engram-hbm | 154 | expert | nvlink3 | infiniband_hdr | 160 | 564.05 us | 177.3 tok/s | 1,772.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x155-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 155 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x155-tensor | DeepSeek-V4.1-Flash-engram-hbm | 155 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x155-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 155 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x155-expert | DeepSeek-V4.1-Flash-engram-hbm | 155 | expert | nvlink3 | infiniband_hdr | 160 | 564.05 us | 177.3 tok/s | 1,772.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x161-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 161 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x161-tensor | DeepSeek-V4.1-Flash-engram-hbm | 161 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x161-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 161 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x161-expert | DeepSeek-V4.1-Flash-engram-hbm | 161 | expert | nvlink3 | infiniband_hdr | 160 | 563.98 us | 177.3 tok/s | 1,773.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.36 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.62 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x194-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 194 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x194-tensor | DeepSeek-V4.1-Flash-engram-hbm | 194 | tensor | nvlink3 | infiniband_hdr | 160 | 826.34 us | 121.0 tok/s | 1,210.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 419.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x194-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 194 | hybrid | nvlink3 | infiniband_hdr | 104 | 465.72 us | 214.7 tok/s | 2,147.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 58.55 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x194-expert | DeepSeek-V4.1-Flash-engram-hbm | 194 | expert | nvlink3 | infiniband_hdr | 160 | 563.71 us | 177.4 tok/s | 1,774.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.30 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.41 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x195-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 195 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x195-tensor | DeepSeek-V4.1-Flash-engram-hbm | 195 | tensor | nvlink3 | infiniband_hdr | 160 | 826.34 us | 121.0 tok/s | 1,210.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 419.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x195-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 195 | hybrid | nvlink3 | infiniband_hdr | 104 | 465.72 us | 214.7 tok/s | 2,147.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 58.55 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x195-expert | DeepSeek-V4.1-Flash-engram-hbm | 195 | expert | nvlink3 | infiniband_hdr | 160 | 563.71 us | 177.4 tok/s | 1,774.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.30 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.41 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 204 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-tensor | DeepSeek-V4.1-Flash-engram-hbm | 204 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 204 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-expert | DeepSeek-V4.1-Flash-engram-hbm | 204 | expert | nvlink3 | infiniband_hdr | 160 | 563.65 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x211-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 211 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x211-tensor | DeepSeek-V4.1-Flash-engram-hbm | 211 | tensor | nvlink3 | infiniband_hdr | 160 | 826.63 us | 121.0 tok/s | 1,209.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 419.46 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x211-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 211 | hybrid | nvlink3 | infiniband_hdr | 106 | 470.60 us | 212.5 tok/s | 2,125.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.43 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x211-expert | DeepSeek-V4.1-Flash-engram-hbm | 211 | expert | nvlink3 | infiniband_hdr | 160 | 563.61 us | 177.4 tok/s | 1,774.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.28 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.33 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash-engram-hbm | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-expert | DeepSeek-V4.1-Flash-engram-hbm | 224 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x241-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 241 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x241-tensor | DeepSeek-V4.1-Flash-engram-hbm | 241 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x241-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 241 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x241-expert | DeepSeek-V4.1-Flash-engram-hbm | 241 | expert | nvlink3 | infiniband_hdr | 160 | 563.45 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.22 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x245-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 245 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x245-tensor | DeepSeek-V4.1-Flash-engram-hbm | 245 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x245-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 245 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x245-expert | DeepSeek-V4.1-Flash-engram-hbm | 245 | expert | nvlink3 | infiniband_hdr | 160 | 563.44 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x246-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 246 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x246-tensor | DeepSeek-V4.1-Flash-engram-hbm | 246 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x246-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 246 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x246-expert | DeepSeek-V4.1-Flash-engram-hbm | 246 | expert | nvlink3 | infiniband_hdr | 160 | 563.44 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x247-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 247 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x247-tensor | DeepSeek-V4.1-Flash-engram-hbm | 247 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x247-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 247 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x247-expert | DeepSeek-V4.1-Flash-engram-hbm | 247 | expert | nvlink3 | infiniband_hdr | 160 | 563.43 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 272 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-tensor | DeepSeek-V4.1-Flash-engram-hbm | 272 | tensor | nvlink3 | infiniband_hdr | 160 | 827.38 us | 120.9 tok/s | 1,208.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 420.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 272 | hybrid | nvlink3 | infiniband_hdr | 113 | 487.67 us | 205.1 tok/s | 2,050.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 80.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-expert | DeepSeek-V4.1-Flash-engram-hbm | 272 | expert | nvlink3 | infiniband_hdr | 160 | 563.33 us | 177.5 tok/s | 1,775.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.21 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 280 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-tensor | DeepSeek-V4.1-Flash-engram-hbm | 280 | tensor | nvlink3 | infiniband_hdr | 160 | 827.46 us | 120.9 tok/s | 1,208.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 420.30 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 280 | hybrid | nvlink3 | infiniband_hdr | 114 | 490.11 us | 204.0 tok/s | 2,040.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-expert | DeepSeek-V4.1-Flash-engram-hbm | 280 | expert | nvlink3 | infiniband_hdr | 160 | 563.31 us | 177.5 tok/s | 1,775.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.20 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.10 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x308-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 308 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x308-tensor | DeepSeek-V4.1-Flash-engram-hbm | 308 | tensor | nvlink3 | infiniband_hdr | 160 | 827.75 us | 120.8 tok/s | 1,208.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 39 on infiniband_hdr (traversals 2.0) = 420.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x308-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 308 | hybrid | nvlink3 | infiniband_hdr | 118 | 499.87 us | 200.1 tok/s | 2,000.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 38 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 92.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x308-expert | DeepSeek-V4.1-Flash-engram-hbm | 308 | expert | nvlink3 | infiniband_hdr | 160 | 563.23 us | 177.5 tok/s | 1,775.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.04 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x360-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 360 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x360-tensor | DeepSeek-V4.1-Flash-engram-hbm | 360 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.89 us | 86.7 tok/s | 867.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 745.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x360-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 360 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x360-expert | DeepSeek-V4.1-Flash-engram-hbm | 360 | expert | nvlink3 | infiniband_hdr | 160 | 563.11 us | 177.6 tok/s | 1,775.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x365-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 365 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x365-tensor | DeepSeek-V4.1-Flash-engram-hbm | 365 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.93 us | 86.7 tok/s | 867.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 745.77 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x365-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 365 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x365-expert | DeepSeek-V4.1-Flash-engram-hbm | 365 | expert | nvlink3 | infiniband_hdr | 160 | 563.10 us | 177.6 tok/s | 1,775.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x377-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 377 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x377-tensor | DeepSeek-V4.1-Flash-engram-hbm | 377 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.02 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 745.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x377-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 377 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x377-expert | DeepSeek-V4.1-Flash-engram-hbm | 377 | expert | nvlink3 | infiniband_hdr | 160 | 563.07 us | 177.6 tok/s | 1,776.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.15 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x378-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 378 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x378-tensor | DeepSeek-V4.1-Flash-engram-hbm | 378 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.02 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 745.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x378-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 378 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x378-expert | DeepSeek-V4.1-Flash-engram-hbm | 378 | expert | nvlink3 | infiniband_hdr | 160 | 563.07 us | 177.6 tok/s | 1,776.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.15 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 392 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-tensor | DeepSeek-V4.1-Flash-engram-hbm | 392 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.07 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 745.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 392 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-expert | DeepSeek-V4.1-Flash-engram-hbm | 392 | expert | nvlink3 | infiniband_hdr | 160 | 563.05 us | 177.6 tok/s | 1,776.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.15 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 448 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-tensor | DeepSeek-V4.1-Flash-engram-hbm | 448 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.32 us | 86.7 tok/s | 867.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 746.15 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 448 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-expert | DeepSeek-V4.1-Flash-engram-hbm | 448 | expert | nvlink3 | infiniband_hdr | 160 | 562.97 us | 177.6 tok/s | 1,776.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.13 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.84 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x504-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 504 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x504-tensor | DeepSeek-V4.1-Flash-engram-hbm | 504 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.51 us | 86.7 tok/s | 866.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 63 on infiniband_hdr (traversals 4.0) = 746.34 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x504-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 504 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x504-expert | DeepSeek-V4.1-Flash-engram-hbm | 504 | expert | nvlink3 | infiniband_hdr | 160 | 562.90 us | 177.7 tok/s | 1,776.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.11 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.79 us |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x136 | 110,840 | 4,809.6 | 0.043 | 4,663.3 (91,280) | 4,832.5 (184,900) | 1.04x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x112-romfill | 91,280 | 4,663.3 | 0.051 | 4,663.3 (91,280) | 4,268.7 (323,575) | 0.92x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x112-romfill | 91,280 | 4,663.3 | 0.051 | 4,663.3 (91,280) | 4,268.7 (323,575) | 0.92x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill | 101,060 | 4,702.2 | 0.047 | 4,702.2 (101,060) | 4,268.7 (323,575) | 0.91x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill | 101,060 | 4,697.5 | 0.046 | 4,697.5 (101,060) | 4,177.3 (323,575) | 0.89x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x156 | 127,140 | 4,466.6 | 0.035 | 4,466.6 (127,140) | 3,899.2 (369,800) | 0.87x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 4,200.2 | 0.019 | 4,200.2 (224,940) | 3,615.9 (554,700) | 0.86x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276 | 224,940 | 2,413.0 | 0.011 | 2,413.0 (224,940) | 1,901.6 (554,700) | 0.79x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1,032.0 | 0.004 | 1,032.0 (277,100) | 601.7 (554,700) | 0.58x | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 329.6 | 0.001 | 329.6 (277,100) | 157.6 (554,700) | 0.48x | compute |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | sram | 555,591.7 | 26,113.2 | 26,113.2 | 21.28x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | sram | 555,591.7 | 26,113.2 | 26,113.2 | 21.28x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | sram | 555,591.7 | 26,113.2 | 26,113.2 | 21.28x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | sram | 555,591.7 | 26,113.2 | 26,113.2 | 21.28x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | sram | 555,591.7 | 26,113.2 | 35,926.6 | 21.28x | 1.38x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | sram | 555,591.7 | 26,113.2 | 53,645.2 | 21.28x | 2.05x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | sram | 555,591.7 | 26,113.2 | 85,572.2 | 21.28x | 3.28x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | sram | 617,725.4 | 26,113.2 | 182,771.4 | 23.66x | 7.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | sram | 1,056,738.5 | 26,113.2 | 308,204.3 | 40.47x | 11.80x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | sram | 1,350,176.3 | 26,113.2 | 371,196.3 | 51.70x | 14.21x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | rom | 691,256.3 | 290,025.9 | 290,025.9 | 2.38x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | rom | 691,256.3 | 290,025.9 | 290,025.9 | 2.38x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | rom | 691,256.3 | 290,025.9 | 290,025.9 | 2.38x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | rom | 691,256.3 | 290,025.9 | 290,025.9 | 2.38x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | rom | 691,256.3 | 290,025.9 | 290,025.9 | 2.38x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | rom | 691,256.3 | 290,025.9 | 290,025.9 | 2.38x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | rom | 691,256.3 | 290,025.9 | 290,025.9 | 2.38x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | rom | 691,256.3 | 290,025.9 | 325,127.0 | 2.38x | 1.12x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | rom | 818,659.5 | 306,017.0 | 368,145.4 | 2.68x | 1.20x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | rom | 874,768.6 | 314,284.2 | 376,592.1 | 2.78x | 1.20x | compute | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 555,591.7 | 1.002 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 691,256.3 | 2.495 | compute | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 555,591.7 | 1.002 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 691,256.3 | 2.495 | compute | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 555,591.7 | 1.002 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 691,256.3 | 2.495 | compute | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 555,591.7 | 1.002 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 691,256.3 | 2.495 | compute | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 555,591.7 | 1.002 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 691,256.3 | 2.495 | compute | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x54-perregion | 44,010 | 1.00 | 1.43 | 35,926.6 | 0.816 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 555,591.7 | 1.002 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 691,256.3 | 2.495 | compute | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 1.99 | 53,645.2 | 0.166 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 555,591.7 | 1.002 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 691,256.3 | 2.495 | compute | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 2.54 | 85,572.2 | 0.264 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276 | 224,940 | 1.00 | 1.00 | 617,725.4 | 2.746 | layer_fixed_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 691,256.3 | 2.495 | compute | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x54-perstream | 44,010 | 1.00 | 4.74 | 26,113.2 | 0.593 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 1.00 | 290,025.9 | 0.896 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 3.72 | 182,771.4 | 0.565 | weight_read | 0.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion-romfill | 323,575 | 12.10 | 1.02 | 325,127.0 | 1.005 | kv_read | 0.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 1,056,738.5 | 3.814 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 818,659.5 | 2.954 | compute | 0.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x54-perstream | 44,010 | 1.00 | 18.96 | 26,113.2 | 0.593 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 2.57 | 306,017.0 | 0.946 | weight_read | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 5.50 | 308,204.3 | 0.952 | weight_read | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 1.18 | 368,145.4 | 1.138 | kv_read | 0.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 1,350,176.3 | 4.873 | compute | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2.68 | 1.00 | 874,768.6 | 3.157 | compute | 0.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x54-perstream | 44,010 | 1.00 | 75.85 | 26,113.2 | 0.593 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 12.10 | 10.29 | 314,284.2 | 0.971 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 5.61 | 371,196.3 | 1.147 | weight_read | 0.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 12.10 | 2.15 | 376,592.1 | 1.164 | kv_read | 0.28x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 92 | 11.23 | 7.90 | 1.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 92 | 20.79 | 11.17 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 92 | 36.02 | 15.94 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 92 | 55.87 | 21.51 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 92 | 74.53 | 27.50 | 2.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 92 | 85.60 | 32.97 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 92 | 90.51 | 38.32 | 2.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 92 | 90.62 | 38.54 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 92 | 90.62 | 38.54 | 2.35x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 134 | 5.89 | 5.44 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 134 | 11.43 | 8.62 | 1.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 134 | 21.58 | 12.19 | 1.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 134 | 38.67 | 18.00 | 2.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 134 | 63.39 | 24.76 | 2.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 134 | 91.09 | 32.45 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 134 | 112.43 | 39.73 | 2.83x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 134 | 126.06 | 47.07 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 134 | 126.45 | 47.38 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 134 | 126.45 | 47.38 | 2.67x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 154 | 11.49 | 8.88 | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 154 | 21.81 | 12.59 | 1.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 154 | 39.47 | 18.73 | 2.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 154 | 65.79 | 25.94 | 2.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 154 | 96.79 | 34.34 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 154 | 122.55 | 42.37 | 2.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 154 | 140.81 | 50.56 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 154 | 141.38 | 50.91 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 154 | 141.38 | 50.91 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 155 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 155 | 11.50 | 8.89 | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 155 | 21.82 | 12.61 | 1.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 155 | 39.51 | 18.76 | 2.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 155 | 65.89 | 25.99 | 2.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 155 | 97.05 | 34.43 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 155 | 123.02 | 42.49 | 2.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 155 | 141.51 | 50.72 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 155 | 142.09 | 51.08 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 155 | 142.09 | 51.08 | 2.78x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 195 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 195 | 11.58 | 9.29 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 195 | 22.14 | 13.31 | 1.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 195 | 40.64 | 19.88 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 195 | 69.38 | 27.99 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 195 | 105.75 | 37.66 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 195 | 139.34 | 47.02 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 195 | 166.96 | 56.77 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 195 | 167.92 | 57.19 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 195 | 167.92 | 57.19 | 2.94x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 211 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 211 | 11.60 | 9.43 | 1.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 211 | 22.24 | 13.56 | 1.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 211 | 40.98 | 20.23 | 2.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 211 | 70.45 | 28.70 | 2.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 211 | 108.51 | 38.81 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 211 | 144.75 | 48.64 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 211 | 175.84 | 58.93 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 211 | 176.96 | 59.37 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 211 | 176.96 | 59.37 | 2.98x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 241 | 5.94 | 5.67 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 241 | 11.64 | 9.65 | 1.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 241 | 22.38 | 14.01 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 241 | 41.50 | 20.81 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 241 | 72.12 | 29.96 | 2.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 241 | 112.91 | 40.78 | 2.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 241 | 153.57 | 51.39 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 241 | 190.78 | 62.66 | 3.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 241 | 192.18 | 63.15 | 3.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 241 | 192.18 | 63.15 | 3.04x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 246 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 246 | 11.65 | 9.68 | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 246 | 22.40 | 14.08 | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 246 | 41.58 | 20.89 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 246 | 72.37 | 30.16 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 246 | 113.56 | 41.09 | 2.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 246 | 154.89 | 51.81 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 246 | 193.07 | 63.24 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 246 | 194.52 | 63.74 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 246 | 194.52 | 63.74 | 3.05x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 308 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 308 | 11.70 | 10.02 | 1.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 308 | 22.61 | 14.87 | 1.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 308 | 42.32 | 21.80 | 1.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 308 | 74.79 | 32.40 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 308 | 120.13 | 44.32 | 2.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 308 | 168.63 | 56.46 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 308 | 217.67 | 69.71 | 3.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 308 | 219.65 | 70.30 | 3.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 308 | 219.65 | 70.30 | 3.12x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 360 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 360 | 11.73 | 10.23 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 360 | 22.73 | 15.43 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 360 | 42.76 | 22.43 | 1.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 360 | 76.22 | 33.96 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 360 | 124.13 | 46.46 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 360 | 177.31 | 59.80 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 360 | 233.92 | 74.41 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 360 | 236.29 | 75.04 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 360 | 236.29 | 75.04 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 365 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 365 | 11.73 | 10.25 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 365 | 22.74 | 15.49 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 365 | 42.79 | 22.48 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 365 | 76.34 | 34.09 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 365 | 124.47 | 46.65 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 365 | 178.04 | 60.11 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 365 | 235.32 | 74.84 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 365 | 237.72 | 75.47 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 365 | 237.72 | 75.47 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 377 | 11.74 | 10.29 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 377 | 22.76 | 15.60 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 377 | 42.88 | 22.61 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 377 | 76.61 | 34.41 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 377 | 125.23 | 47.08 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 377 | 179.73 | 60.83 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 377 | 238.56 | 75.84 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 377 | 241.04 | 76.49 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 377 | 241.04 | 76.49 | 3.15x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 504 | 5.97 | 5.84 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 504 | 11.78 | 10.63 | 1.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 504 | 22.93 | 16.68 | 1.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 504 | 43.51 | 23.88 | 1.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 504 | 78.74 | 37.04 | 2.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 504 | 131.34 | 51.20 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 504 | 193.47 | 67.52 | 2.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 504 | 265.72 | 84.79 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 504 | 268.92 | 85.61 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 504 | 268.92 | 85.61 | 3.14x |
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
| gpu | DeepSeek-V4.1-Flash-engram-hbm | 1 | 860.60 | 32.1% |
| rom | DeepSeek-V4.1-Flash-engram-hbm | 1 | 144.07 | 71.9% |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 168 | 0.44% | 2.59 | 3.52 |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 324.0 | 23,326.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 324.0 | 23,326.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 324.0 | 23,326.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 324.0 | 23,326.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 324.0 | 23,326.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 324.0 | 23,326.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 324.0 | 23,326.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 5.45% | 24.2 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 92.7 | 23,737.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 20.07% | 66.5 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 23.3 | 23,821.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 59.18% | 179.4 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 5.8 | 23,783.3 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 1 |
| gpu | infeasible | 9 |
| gpu | link_latency | 1049 |
| gpu | weight_read | 701 |
| rom | compute | 727 |
| rom | infeasible | 2481 |
| rom | kv_read | 92 |
| rom | layer_fixed_latency | 617 |
| rom | link_latency | 888 |
| rom | weight_read | 385 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 9 |
| rom | CAPACITY | 2481 |

## Mechanical consistency audit

**FAIL** over 140,597 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x179', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x198', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x207', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x244', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x248', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x249', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x250', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x330', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x179', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x198', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x207', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x244', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x248', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x249', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x250', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x330', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x179', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x198', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x207', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x244', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x248', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x249', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x250', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x330', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x179', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x198', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x207', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x244', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x248', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x249', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x250', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x330', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4.1-Flash-engram-hbm', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 49 |
| assumed | 84 |

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

# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash-1m

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash at 1,000,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 246x (ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream, 341 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 55 devices. On the GPU side the correction reaches 68x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 111 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash takes 115 x 815 mm2 (93,725 mm2, array, KV in SRAM) at 8,221 tok/s per user and 88 tok/s per 1,000 mm2, holding 1 session, against 113 copies of one unified HBM die at the same silicon: 7.4x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash on 277,100 mm2 of ROM silicon at 10,062 tok/s per user against 276,710 mm2 of a100_sxm_80gb-x335-tensor at 843 tok/s: **11.9x**, ROM binding on `weight_read` and the GPU on `link_latency`. It holds 27,422 resident sessions against the GPU cluster's 26,447. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 9.45x to it.** At 262,430 mm2 on DeepSeek-V4.1-Flash the pipeline-only GPU delivers 122.62 tok/s and the same silicon running tensor delivers 1,159 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4.1-Flash, ROM binding on `link_latency`) to 2.21x (DeepSeek-V4.1-Flash, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 404 to 50,309 tok/s, and its rate with every slot occupied from 50,088 to 50,309. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 124 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 189.5 us and cap it at 5,276 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 182 of 3849 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 40.4x of aggregate throughput (DeepSeek-V4.1-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 14.68x, on DeepSeek-V4.1-Flash at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x115`** -- 115 x 815 mm2 reticle dies, 93,725 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **8,221.1 tok/s per user** (0.12 ms/token), binding on `link_latency`
- **87.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 8,221 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 5,817 W at 0.062 W/mm2, 707.6 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 113 copies of one unified HBM die -- `a100_sxm_80gb-x113-tensor`, 93,338 mm2, area ratio 1.0041 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 93,725 | 93,338 | 1.0041 |
| user tok/s | 8,221.1 | 1,105.0 | 7.44x |
| aggregate tok/s | 8,221 | 1,105 | 0.59x |
| resident sessions | 1 | 8,542 | -- |
| J/token | 0.7076 | 16.1646 | 22.8x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 8,542 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x318-tensor` at 262,668 mm2 and 1,158.5 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x318` | 259,170 | 9,941.6 | 38.4 | 25,647 | 8.58x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 36.3 | 27,422 | 11.94x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x113` | 92,095 | 7,888.8 | 85.7 | 1 | 7.15x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x115` | 93,725 | 8,221.1 | 87.7 | 1 | 7.44x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x115` | 93,725 | 8,221.1 | 87.7 | -- | 87.7 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x133` | 108,395 | 9,207.8 | 84.9 | 67.3 | 87.7 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x144` | 117,360 | 9,382.7 | 79.9 | 49.1 | 87.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x320` | 260,800 | 10,022.9 | 38.4 | 10.8 | 87.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 36.3 | 10.0 | 87.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x115` **<-- recommended** | 93,725 | 115 | 8,221.1 | 8,221 | 87.7 | 1 | `link_latency` | 5,817 | 707.6 | `a100_sxm_80gb-x113-tensor` | 7.44x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x133` | 108,395 | 133 | 9,207.8 | 9,208 | 84.9 | 1 | `link_latency` | 6,972 | 757.2 | `a100_sxm_80gb-x131-tensor` | 8.25x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x144` | 117,360 | 144 | 9,382.7 | 9,383 | 79.9 | 1 | `link_latency` | 8,274 | 881.8 | `a100_sxm_80gb-x142-tensor` | 8.36x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x320` | 260,800 | 320 | 10,022.9 | 801,829 | 38.4 | 25,809 | `compute` | 60,725 | 3,377.7 | `a100_sxm_80gb-x316-tensor` | 8.65x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 340 | 10,062.0 | 855,270 | 36.3 | 27,422 | `weight_read` | 65,182 | 3,627.4 | `a100_sxm_80gb-x335-tensor` | 11.94x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 282 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x115` | 93,725 | 8,221.1 | 87.7 | 1 |
| array | 282 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 36.3 | 27,422 |
| array | 282 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x113` | 92,095 | 7,888.8 | 85.7 | 1 |
| wafer | 54 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x2` | 92,450 | 4,857.6 | 52.5 | 1 |
| wafer | 54 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 5,682.5 | 41.0 | 1 |
| wafer | 54 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x2` | 92,450 | 4,857.6 | 52.5 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 855,270 | 27,422 | 65,182 | 3,627.4 | `weight_read` | `a100_sxm_80gb-x335-tensor` | 842.6 | 26,447 | 58,803.6 | 1.001 | 11.94x | 16.2x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 5,682.5 | 5,682 | 1 | 11,334 | 1,994.6 | `link_latency` | `a100_sxm_80gb-x168-tensor` | 1,131.8 | 12,978 | 22,831.1 | 0.999 | 5.02x | 11.4x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-tensor-x173` | 140,995 | 8,153.0 | 8,153 | 13,953 | 14,361 | 1,761.4 | `link_latency` | `a100_sxm_80gb-x171-tensor` | 1,132.6 | 13,220 | 23,198.3 | 0.998 | 7.20x | 13.2x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 5,682.5 | -- | 1 | -- | 1,994.6 | -- | -- | -- | -- | -- | 1.017 | 0.70x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 855,270 | 27,422 | 65,182 | 1,830.7 | `weight_read` | `a100_sxm_80gb-x335-tensor` | 770.2 | 26,447 | 32,349.4 | 1.001 | 13.06x | 17.7x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 5,479.9 | 32,879 | 4,161 | 33,272 | 2,968.0 | `link_latency` | `a100_sxm_80gb-x336-tensor` | 770.2 | 26,528 | 32,440.8 | 0.999 | 7.11x | 10.9x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 855,270 | 27,422 | 65,182 | 1,830.7 | `weight_read` | `a100_sxm_80gb-x335-tensor` | 770.2 | 26,447 | 32,349.4 | 1.001 | 13.06x | 17.7x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 5,479.9 | -- | 4,161 | -- | 2,968.0 | -- | -- | -- | -- | -- | 0.999 | 0.54x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 855,270 | 27,422 | 65,182 | 932.3 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 657.4 | 26,447 | 19,794.0 | 1.001 | 15.31x | 20.5x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 5,479.9 | 32,879 | 4,161 | 33,272 | 1,501.0 | `link_latency` | `a100_sxm_80gb-x336-hybrid` | 658.7 | 26,528 | 19,812.5 | 0.999 | 8.32x | 12.8x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 855,270 | 27,422 | 65,182 | 932.3 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 657.4 | 26,447 | 19,794.0 | 1.001 | 15.31x | 20.5x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 5,479.9 | -- | 4,161 | -- | 1,501.0 | -- | -- | -- | -- | -- | 0.999 | 0.54x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 855,270 | 27,422 | 65,182 | 483.1 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 657.4 | 26,447 | 10,596.8 | 1.001 | 15.31x | 21.9x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 369,800 | 5,473.7 | 43,790 | 5,548 | 47,288 | 1,079.9 | `link_latency` | `a100_sxm_80gb-x448-hybrid` | 658.7 | 35,561 | 13,674.9 | 0.999 | 8.31x | 12.7x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 855,270 | 27,422 | 65,182 | 258.5 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 657.4 | 26,447 | 5,998.2 | 1.001 | 15.31x | 23.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 5,288.8 | 84,621 | 8,323 | 75,910 | 897.1 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 658.7 | 53,627 | 10,606.0 | 0.999 | 8.03x | 11.8x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 855,270 | 27,422 | 65,182 | 146.2 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 657.4 | 26,447 | 3,698.8 | 1.001 | 15.31x | 25.3x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,694.7 | 150,231 | 8,323 | 77,942 | 518.8 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 658.7 | 53,627 | 6,002.8 | 0.999 | 7.13x | 11.6x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 10,062.0 | 855,270 | 27,422 | 65,182 | 90.1 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 581.2 | 26,447 | 2,390.1 | 1.001 | 17.31x | 26.5x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,833.5 | 245,343 | 8,323 | 80,882 | 329.7 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 658.7 | 53,627 | 3,701.2 | 0.999 | 5.82x | 11.2x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 3,857.9 | 987,625 | 27,583 | 68,184 | 69.0 | `compute` | `a100_sxm_80gb-x337-hybrid` | 294.2 | 26,608 | 1,282.3 | 1.001 | 13.11x | 12.9x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,824.9 | 467,168 | 8,323 | 87,678 | 187.7 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 437.1 | 53,627 | 1,657.2 | 0.999 | 4.17x | 7.3x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | 1,022.4 | 1,046,895 | 27,583 | 70,085 | 66.9 | `compute` | `a100_sxm_80gb-x337-expert` | 206.1 | 26,217 | 290.4 | 1.001 | 4.96x | 4.3x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 647.4 | 662,936 | 8,323 | 95,002 | 143.3 | `kv_read` | `a100_sxm_80gb-x672-expert` | 271.3 | 52,835 | 409.2 | 0.999 | 2.39x | 2.9x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | 257.8 | 1,056,006 | 27,583 | 69,581 | 65.9 | `compute` | `a100_sxm_80gb-x337-expert` | 116.6 | 26,217 | 138.9 | 1.001 | 2.21x | 2.1x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 163.0 | 667,776 | 8,323 | 94,249 | 141.1 | `kv_read` | `a100_sxm_80gb-x672-expert` | 180.1 | 52,835 | 168.6 | 0.999 | 0.91x | 1.2x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x115` | 93,725 | array | SRAM | 1 |
| 2 | `ROM-N6-native-HBMKV-array-hw-tensor-x137` | 111,655 | array | HBM | 11,049 |
| 4-8 | `ROM-N6-native-HBMKV-array-hw-tensor-x143` | 116,545 | array | HBM | 11,533 |
| 16-32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x208-romfill` | 169,520 | array | HBM | 16,776 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | array | HBM | 18,389 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | array | HBM | 27,583 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | array | HBM | 27,583 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash | HBM | rom | 124, 137, 143, 170, 171, 173, 207, 208, 227, 228, 340, 342 |
| DeepSeek-V4.1-Flash | HBM | sram | 124, 137, 143, 170, 171, 173, 227, 228, 318, 320, 322, 340, 342 |
| DeepSeek-V4.1-Flash | SRAM | rom | 113, 115, 133, 144, 155, 159, 170, 212, 227, 318, 340 |
| DeepSeek-V4.1-Flash | SRAM | sram | 113, 115, 133, 144, 155, 159, 170, 212, 227, 318, 340 |

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

- **0 of 3,849 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 34%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,307 | 0 | 64.9% | 79.7% | 0.386 | 56% |
| rom | wafer (>=40,000 mm2) | 2,542 | 0 | 23.0% | 65.1% | 0.325 | 83% |

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
| DeepSeek-V4.1-Flash | 1 | 259,170 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318` | 3.378429 | 60,240.2 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-tensor` | 40.547336 | 46,957.4 | link_latency | 12.00x |
| DeepSeek-V4.1-Flash | 2 | 259,170 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318` | 1.706183 | 60,240.2 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-tensor` | 23.062242 | 47,279.9 | link_latency | 13.52x |
| DeepSeek-V4.1-Flash | 4 | 259,170 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318` | 0.870060 | 60,240.2 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-tensor` | 14.309726 | 47,726.8 | link_latency | 16.45x |
| DeepSeek-V4.1-Flash | 8 | 259,170 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318` | 0.451998 | 60,240.2 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-hybrid` | 10.112142 | 81,749.2 | weight_read | 21.93x |
| DeepSeek-V4.1-Flash | 16 | 259,170 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318` | 0.242967 | 60,240.2 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-hybrid` | 5.755834 | 81,749.2 | weight_read | 23.69x |
| DeepSeek-V4.1-Flash | 32 | 259,170 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318` | 0.138452 | 60,240.2 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-hybrid` | 3.577680 | 81,749.2 | weight_read | 25.84x |
| DeepSeek-V4.1-Flash | 64 | 259,170 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318` | 0.086194 | 60,240.2 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-hybrid` | 2.314686 | 83,729.0 | weight_read | 26.85x |
| DeepSeek-V4.1-Flash | 256 | 277,100 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.069064 | 67,647.6 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid` | 1.274846 | 95,947.3 | weight_read | 12.82x |
| DeepSeek-V4.1-Flash | 1024 | 277,100 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340` | 0.066988 | 69,524.1 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-expert` | 0.289312 | 61,004.7 | weight_read | 4.32x |
| DeepSeek-V4.1-Flash | 4096 | 277,100 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340` | 0.065940 | 69,026.1 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-expert` | 0.138711 | 65,988.7 | compute | 2.10x |

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
| DeepSeek-V4.1-Flash | 2 | 92,450 | 25,685.8 | wafer-pipeline | 4,857.6 | wafer-tensor | 5.29x | 5,544.8 | pipeline | 1,104.8 | tensor | 5.02x | 4.63x | 4.40x | 0.95x |
| DeepSeek-V4.1-Flash | 3 | 138,675 | 53,092.9 | wafer-pipeline | 5,682.5 | wafer-hybrid | 9.34x | 6,393.8 | pipeline | 1,131.8 | tensor | 5.65x | 8.30x | 5.02x | 0.60x |
| DeepSeek-V4.1-Flash | 4 | 184,900 | 53,092.9 | wafer-pipeline | 5,555.9 | wafer-hybrid | 9.56x | 6,923.9 | pipeline | 1,145.8 | tensor | 6.04x | 7.67x | 4.85x | 0.63x |
| DeepSeek-V4.1-Flash | 6 | 277,350 | 55,820.8 | wafer-pipeline | 5,479.9 | wafer-hybrid | 10.19x | 7,549.8 | pipeline | 842.7 | tensor | 8.96x | 7.39x | 6.50x | 0.88x |
| DeepSeek-V4.1-Flash | 8 | 369,800 | 58,249.4 | wafer-pipeline | 5,473.7 | wafer-hybrid | 10.64x | 7,907.3 | pipeline | 846.5 | tensor | 9.34x | 7.37x | 6.47x | 0.88x |
| DeepSeek-V4.1-Flash | 12 | 554,700 | 60,899.1 | wafer-pipeline | 5,461.6 | wafer-hybrid | 11.15x | 8,300.2 | pipeline | 850.4 | tensor | 9.76x | 7.34x | 6.42x | 0.88x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.60x to 0.95x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash | 1 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 10,062.0 | 855,269.6 | weight_read | DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-tensor | 276,710 | 1.00x | tensor | 1,152.73 | 842.6 | 842.6 | link_latency | 11.94x | 20.82x | 82.06x | 11.94x |
| DeepSeek-V4.1-Flash | 1 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113 | 92,095 | 7,888.8 | 7,888.8 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-tensor | 91,686 | 1.00x | tensor | 823.25 | 1,104.0 | 1,104.0 | link_latency | 7.15x | 0.58x | 64.33x | 7.15x |
| DeepSeek-V4.1-Flash | 2 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 10,062.0 | 855,269.6 | weight_read | DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-tensor | 276,710 | 1.00x | tensor | 1,255.86 | 770.2 | 1,540.3 | link_latency | 13.06x | 20.82x | 82.06x | 13.06x |
| DeepSeek-V4.1-Flash | 2 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x124 | 101,060 | 6,994.8 | 13,989.7 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-tensor | 100,772 | 1.00x | tensor | 923.46 | 977.7 | 1,955.5 | link_latency | 7.15x | 0.94x | 57.04x | 7.15x |
| DeepSeek-V4.1-Flash | 4 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 10,062.0 | 855,269.6 | weight_read | DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 502.31 | 657.4 | 27,609.9 | weight_read | 15.31x | 20.82x | 82.06x | 15.36x |
| DeepSeek-V4.1-Flash | 4 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x124 | 101,060 | 5,368.5 | 21,473.8 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-tensor | 100,772 | 1.00x | tensor | 1,122.11 | 789.3 | 3,157.0 | link_latency | 6.80x | 1.44x | 43.78x | 6.80x |
| DeepSeek-V4.1-Flash | 8 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 10,062.0 | 855,269.6 | weight_read | DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 502.31 | 657.4 | 27,609.9 | weight_read | 15.31x | 20.82x | 82.06x | 15.36x |
| DeepSeek-V4.1-Flash | 8 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x124 | 101,060 | 3,664.4 | 29,315.4 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-hybrid | 100,772 | 1.00x | hybrid | 443.76 | 662.6 | 10,602.3 | weight_read | 5.53x | 1.96x | 29.88x | 5.53x |
| DeepSeek-V4.1-Flash | 16 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 10,062.0 | 855,269.6 | weight_read | DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 502.31 | 657.4 | 27,609.9 | weight_read | 15.31x | 20.82x | 82.06x | 15.36x |
| DeepSeek-V4.1-Flash | 16 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x124 | 101,060 | 2,241.5 | 35,863.4 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-hybrid | 100,772 | 1.00x | hybrid | 443.76 | 662.6 | 10,602.3 | weight_read | 3.38x | 2.40x | 18.28x | 3.38x |
| DeepSeek-V4.1-Flash | 32 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 10,062.0 | 855,269.6 | weight_read | DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 502.31 | 657.4 | 27,609.9 | weight_read | 15.31x | 20.82x | 82.06x | 15.36x |
| DeepSeek-V4.1-Flash | 32 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x124 | 101,060 | 1,535.5 | 49,136.4 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-hybrid | 100,772 | 1.00x | hybrid | 457.07 | 527.6 | 16,883.6 | weight_read | 2.91x | 2.91x | 12.52x | 2.91x |
| DeepSeek-V4.1-Flash | 64 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 10,062.0 | 855,269.6 | weight_read | DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 514.43 | 581.2 | 37,193.9 | weight_read | 17.31x | 20.82x | 82.06x | 17.37x |
| DeepSeek-V4.1-Flash | 64 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x124 | 101,060 | 776.5 | 49,695.5 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-hybrid | 100,772 | 1.00x | hybrid | 483.70 | 377.2 | 24,138.7 | weight_read | 2.06x | 2.06x | 6.33x | 2.06x |
| DeepSeek-V4.1-Flash | 256 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x342 | 278,730 | 3,857.9 | 987,624.8 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-hybrid | 278,362 | 1.00x | hybrid | 616.95 | 294.2 | 75,311.0 | weight_read | 13.11x | 13.11x | 31.46x | 13.17x |
| DeepSeek-V4.1-Flash | 256 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x124 | 101,060 | 196.1 | 50,205.2 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-expert | 100,772 | 1.00x | expert | 1,097.29 | 169.5 | 43,389.9 | weight_read | 1.16x | 1.16x | 2.21x | 1.16x |
| DeepSeek-V4.1-Flash | 1024 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1,022.4 | 1,046,895.0 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-expert | 278,362 | 1.00x | expert | 1,334.57 | 206.1 | 211,080.3 | weight_read | 4.96x | 4.96x | 14.22x | 4.96x |
| DeepSeek-V4.1-Flash | 1024 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x124 | 101,060 | 49.1 | 50,288.5 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-expert | 100,772 | 1.00x | expert | 2,701.95 | 117.4 | 120,194.9 | weight_read | 0.42x | 0.42x | 1.39x | 0.42x |
| DeepSeek-V4.1-Flash | 4096 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 257.8 | 1,056,005.7 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-expert | 278,362 | 1.00x | expert | 3,651.08 | 116.6 | 477,774.1 | compute | 2.21x | 2.21x | 9.70x | 2.21x |
| DeepSeek-V4.1-Flash | 4096 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x124 | 101,060 | 12.3 | 50,309.3 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-expert | 100,772 | 1.00x | expert | 9,120.61 | 46.1 | 189,024.0 | compute | 0.27x | 0.27x | 1.01x | 0.27x |

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
| DeepSeek-V4.1-Flash | 54 | 44,604 | 122.6 | 1,025.3 | 678.0 | tensor | 816.23 | 83.7% | link_latency |
| DeepSeek-V4.1-Flash | 55 | 45,430 | 122.6 | 1,028.2 | 686.8 | tensor | 816.23 | 83.9% | link_latency |
| DeepSeek-V4.1-Flash | 56 | 46,256 | 122.6 | 1,031.0 | 695.6 | tensor | 816.23 | 84.1% | link_latency |
| DeepSeek-V4.1-Flash | 58 | 47,908 | 122.6 | 1,034.4 | 647.6 | tensor | 817.98 | 84.6% | link_latency |
| DeepSeek-V4.1-Flash | 59 | 48,734 | 122.6 | 1,036.9 | 655.6 | tensor | 817.98 | 84.8% | link_latency |
| DeepSeek-V4.1-Flash | 60 | 49,560 | 122.6 | 1,039.3 | 663.5 | tensor | 817.98 | 85.0% | link_latency |
| DeepSeek-V4.1-Flash | 66 | 54,516 | 122.6 | 1,051.2 | 651.9 | tensor | 819.35 | 86.1% | link_latency |
| DeepSeek-V4.1-Flash | 111 | 91,686 | 122.6 | 1,104.0 | 683.1 | tensor | 823.25 | 90.9% | link_latency |
| DeepSeek-V4.1-Flash | 112 | 92,512 | 122.6 | 1,104.8 | 687.4 | tensor | 823.25 | 91.0% | link_latency |
| DeepSeek-V4.1-Flash | 113 | 93,338 | 122.6 | 1,105.0 | 658.1 | tensor | 823.72 | 91.0% | link_latency |
| DeepSeek-V4.1-Flash | 122 | 100,772 | 122.6 | 1,110.9 | 662.6 | tensor | 824.13 | 91.6% | link_latency |
| DeepSeek-V4.1-Flash | 131 | 108,206 | 122.6 | 1,116.1 | 666.5 | tensor | 824.49 | 92.0% | link_latency |
| DeepSeek-V4.1-Flash | 135 | 111,510 | 122.6 | 1,118.4 | 680.5 | tensor | 824.49 | 92.2% | link_latency |
| DeepSeek-V4.1-Flash | 141 | 116,466 | 122.6 | 1,121.2 | 673.0 | tensor | 824.81 | 92.5% | link_latency |
| DeepSeek-V4.1-Flash | 142 | 117,292 | 122.6 | 1,121.7 | 676.3 | tensor | 824.81 | 92.5% | link_latency |
| DeepSeek-V4.1-Flash | 153 | 126,378 | 122.6 | 1,126.1 | 659.9 | tensor | 825.36 | 92.9% | link_latency |
| DeepSeek-V4.1-Flash | 157 | 129,682 | 122.6 | 1,127.8 | 671.8 | tensor | 825.36 | 93.1% | link_latency |
| DeepSeek-V4.1-Flash | 168 | 138,768 | 122.6 | 1,131.8 | 679.4 | tensor | 825.59 | 93.4% | link_latency |
| DeepSeek-V4.1-Flash | 169 | 139,594 | 122.6 | 1,131.9 | 659.7 | tensor | 825.80 | 93.5% | link_latency |
| DeepSeek-V4.1-Flash | 171 | 141,246 | 122.6 | 1,132.6 | 665.0 | tensor | 825.80 | 93.5% | link_latency |
| DeepSeek-V4.1-Flash | 204 | 168,504 | 122.6 | 1,141.6 | 665.0 | tensor | 826.49 | 94.3% | link_latency |
| DeepSeek-V4.1-Flash | 205 | 169,330 | 122.6 | 1,141.8 | 667.2 | tensor | 826.49 | 94.4% | link_latency |
| DeepSeek-V4.1-Flash | 209 | 172,634 | 122.6 | 1,142.6 | 657.8 | tensor | 826.63 | 94.5% | link_latency |
| DeepSeek-V4.1-Flash | 224 | 185,024 | 122.6 | 1,145.8 | 671.6 | tensor | 826.76 | 94.7% | link_latency |
| DeepSeek-V4.1-Flash | 225 | 185,850 | 122.6 | 1,145.9 | 656.8 | tensor | 826.88 | 94.8% | link_latency |
| DeepSeek-V4.1-Flash | 314 | 259,364 | 122.6 | 1,158.1 | 650.4 | tensor | 827.81 | 95.9% | link_latency |
| DeepSeek-V4.1-Flash | 316 | 261,016 | 122.6 | 1,158.3 | 653.2 | tensor | 827.81 | 95.9% | link_latency |
| DeepSeek-V4.1-Flash | 318 | 262,668 | 122.6 | 1,158.5 | 655.9 | tensor | 827.81 | 95.9% | link_latency |
| DeepSeek-V4.1-Flash | 335 | 276,710 | 122.6 | 842.6 | 657.4 | tensor | 1,152.73 | 97.1% | link_latency |
| DeepSeek-V4.1-Flash | 336 | 277,536 | 122.6 | 842.7 | 658.7 | tensor | 1,152.73 | 97.1% | link_latency |
| DeepSeek-V4.1-Flash | 337 | 278,362 | 122.6 | 842.7 | 649.7 | tensor | 1,152.79 | 97.1% | link_latency |
| DeepSeek-V4.1-Flash | 448 | 370,048 | 122.6 | 846.5 | 658.7 | tensor | 1,153.32 | 97.6% | link_latency |
| DeepSeek-V4.1-Flash | 672 | 555,072 | 122.6 | 850.4 | 658.7 | tensor | 1,153.90 | 98.1% | link_latency |

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
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x155 | DeepSeek-V4.1-Flash | 155 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x133 | DeepSeek-V4.1-Flash | 133 | tensor | rom_package_ucie | rom_board_serdes | 160 | 91.39 us | 1,094.3 tok/s | 10,942.6 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 34 on rom_board_serdes (traversals 11.0) = 89.33 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x155 | DeepSeek-V4.1-Flash | 155 | hybrid | rom_package_ucie | rom_board_serdes | 118 | 6.08 us | 16,455.5 tok/s | 164,555.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 38 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.02 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x155 | DeepSeek-V4.1-Flash | 155 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x3 | DeepSeek-V4.1-Flash | 3 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-tensor-x115 | DeepSeek-V4.1-Flash | 115 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4.1-Flash | 3 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.87 us | 581.8 tok/s | 5,818.2 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 17.87 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hybrid-x144 | DeepSeek-V4.1-Flash | 144 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4.1-Flash | 3 | hybrid | on_wafer | rom_wafer_serdes | 82 | 154.20 us | 648.5 tok/s | 6,484.9 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x322 | DeepSeek-V4.1-Flash | 322 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x137 | DeepSeek-V4.1-Flash | 137 | tensor | rom_package_ucie | rom_board_serdes | 160 | 91.39 us | 1,094.2 tok/s | 10,942.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 35 on rom_board_serdes (traversals 11.0) = 89.33 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x320 | DeepSeek-V4.1-Flash | 320 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-pipeline-x318 | DeepSeek-V4.1-Flash | 318 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6 | DeepSeek-V4.1-Flash | 6 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-tensor-x124 | DeepSeek-V4.1-Flash | 124 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-tensor-x6 | DeepSeek-V4.1-Flash | 6 | tensor | on_wafer | rom_wafer_serdes | 160 | 189.54 us | 527.6 tok/s | 5,275.9 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 6 on rom_wafer_serdes (traversals 4.4) = 35.54 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hybrid-x173 | DeepSeek-V4.1-Flash | 173 | hybrid | nvlink3 | infiniband_hdr | 101 | 458.40 us | 218.2 tok/s | 2,181.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 51.23 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | DeepSeek-V4.1-Flash | 6 | hybrid | on_wafer | rom_wafer_serdes | 85 | 154.51 us | 647.2 tok/s | 6,472.1 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 5 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.51 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x54-pipeline | DeepSeek-V4.1-Flash | 54 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x54-tensor | DeepSeek-V4.1-Flash | 54 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x54-hybrid | DeepSeek-V4.1-Flash | 54 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x54-expert | DeepSeek-V4.1-Flash | 54 | expert | nvlink3 | infiniband_hdr | 160 | 567.24 us | 176.3 tok/s | 1,762.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 166.04 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x55-pipeline | DeepSeek-V4.1-Flash | 55 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x55-tensor | DeepSeek-V4.1-Flash | 55 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x55-hybrid | DeepSeek-V4.1-Flash | 55 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x55-expert | DeepSeek-V4.1-Flash | 55 | expert | nvlink3 | infiniband_hdr | 160 | 567.17 us | 176.3 tok/s | 1,763.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.97 us |
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
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x60-pipeline | DeepSeek-V4.1-Flash | 60 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x60-tensor | DeepSeek-V4.1-Flash | 60 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x60-hybrid | DeepSeek-V4.1-Flash | 60 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x60-expert | DeepSeek-V4.1-Flash | 60 | expert | nvlink3 | infiniband_hdr | 160 | 566.70 us | 176.5 tok/s | 1,764.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.68 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x66-pipeline | DeepSeek-V4.1-Flash | 66 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x66-tensor | DeepSeek-V4.1-Flash | 66 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x66-hybrid | DeepSeek-V4.1-Flash | 66 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x66-expert | DeepSeek-V4.1-Flash | 66 | expert | nvlink3 | infiniband_hdr | 160 | 566.27 us | 176.6 tok/s | 1,765.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.90 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.38 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4.1-Flash | 111 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4.1-Flash | 111 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4.1-Flash | 111 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-expert | DeepSeek-V4.1-Flash | 111 | expert | nvlink3 | infiniband_hdr | 160 | 564.72 us | 177.1 tok/s | 1,770.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.55 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.17 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4.1-Flash | 112 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4.1-Flash | 112 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4.1-Flash | 112 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-expert | DeepSeek-V4.1-Flash | 112 | expert | nvlink3 | infiniband_hdr | 160 | 564.67 us | 177.1 tok/s | 1,771.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.16 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x113-pipeline | DeepSeek-V4.1-Flash | 113 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x113-tensor | DeepSeek-V4.1-Flash | 113 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x113-hybrid | DeepSeek-V4.1-Flash | 113 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x113-expert | DeepSeek-V4.1-Flash | 113 | expert | nvlink3 | infiniband_hdr | 160 | 564.65 us | 177.1 tok/s | 1,771.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-pipeline | DeepSeek-V4.1-Flash | 122 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-tensor | DeepSeek-V4.1-Flash | 122 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-hybrid | DeepSeek-V4.1-Flash | 122 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x122-expert | DeepSeek-V4.1-Flash | 122 | expert | nvlink3 | infiniband_hdr | 160 | 564.49 us | 177.2 tok/s | 1,771.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.01 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x131-pipeline | DeepSeek-V4.1-Flash | 131 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x131-tensor | DeepSeek-V4.1-Flash | 131 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x131-hybrid | DeepSeek-V4.1-Flash | 131 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x131-expert | DeepSeek-V4.1-Flash | 131 | expert | nvlink3 | infiniband_hdr | 160 | 564.35 us | 177.2 tok/s | 1,772.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.90 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x135-pipeline | DeepSeek-V4.1-Flash | 135 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x135-tensor | DeepSeek-V4.1-Flash | 135 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x135-hybrid | DeepSeek-V4.1-Flash | 135 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x135-expert | DeepSeek-V4.1-Flash | 135 | expert | nvlink3 | infiniband_hdr | 160 | 564.30 us | 177.2 tok/s | 1,772.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.86 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-pipeline | DeepSeek-V4.1-Flash | 141 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-tensor | DeepSeek-V4.1-Flash | 141 | tensor | nvlink3 | infiniband_hdr | 160 | 824.81 us | 121.2 tok/s | 1,212.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 417.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-hybrid | DeepSeek-V4.1-Flash | 141 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-expert | DeepSeek-V4.1-Flash | 141 | expert | nvlink3 | infiniband_hdr | 160 | 564.22 us | 177.2 tok/s | 1,772.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x142-pipeline | DeepSeek-V4.1-Flash | 142 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x142-tensor | DeepSeek-V4.1-Flash | 142 | tensor | nvlink3 | infiniband_hdr | 160 | 824.81 us | 121.2 tok/s | 1,212.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 417.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x142-hybrid | DeepSeek-V4.1-Flash | 142 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x142-expert | DeepSeek-V4.1-Flash | 142 | expert | nvlink3 | infiniband_hdr | 160 | 564.21 us | 177.2 tok/s | 1,772.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.78 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x153-pipeline | DeepSeek-V4.1-Flash | 153 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x153-tensor | DeepSeek-V4.1-Flash | 153 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x153-hybrid | DeepSeek-V4.1-Flash | 153 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x153-expert | DeepSeek-V4.1-Flash | 153 | expert | nvlink3 | infiniband_hdr | 160 | 564.06 us | 177.3 tok/s | 1,772.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.69 us |
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
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x171-pipeline | DeepSeek-V4.1-Flash | 171 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x171-tensor | DeepSeek-V4.1-Flash | 171 | tensor | nvlink3 | infiniband_hdr | 160 | 825.80 us | 121.1 tok/s | 1,210.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 418.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x171-hybrid | DeepSeek-V4.1-Flash | 171 | hybrid | nvlink3 | infiniband_hdr | 101 | 458.40 us | 218.2 tok/s | 2,181.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 51.23 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x171-expert | DeepSeek-V4.1-Flash | 171 | expert | nvlink3 | infiniband_hdr | 160 | 563.89 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x204-pipeline | DeepSeek-V4.1-Flash | 204 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x204-tensor | DeepSeek-V4.1-Flash | 204 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x204-hybrid | DeepSeek-V4.1-Flash | 204 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x204-expert | DeepSeek-V4.1-Flash | 204 | expert | nvlink3 | infiniband_hdr | 160 | 563.65 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x205-pipeline | DeepSeek-V4.1-Flash | 205 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x205-tensor | DeepSeek-V4.1-Flash | 205 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x205-hybrid | DeepSeek-V4.1-Flash | 205 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x205-expert | DeepSeek-V4.1-Flash | 205 | expert | nvlink3 | infiniband_hdr | 160 | 563.65 us | 177.4 tok/s | 1,774.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.36 us |
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
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-pipeline | DeepSeek-V4.1-Flash | 314 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-tensor | DeepSeek-V4.1-Flash | 314 | tensor | nvlink3 | infiniband_hdr | 160 | 827.81 us | 120.8 tok/s | 1,208.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 40 on infiniband_hdr (traversals 2.0) = 420.65 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-hybrid | DeepSeek-V4.1-Flash | 314 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x314-expert | DeepSeek-V4.1-Flash | 314 | expert | nvlink3 | infiniband_hdr | 160 | 563.21 us | 177.6 tok/s | 1,775.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.18 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x316-pipeline | DeepSeek-V4.1-Flash | 316 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x316-tensor | DeepSeek-V4.1-Flash | 316 | tensor | nvlink3 | infiniband_hdr | 160 | 827.81 us | 120.8 tok/s | 1,208.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 40 on infiniband_hdr (traversals 2.0) = 420.65 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x316-hybrid | DeepSeek-V4.1-Flash | 316 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x316-expert | DeepSeek-V4.1-Flash | 316 | expert | nvlink3 | infiniband_hdr | 160 | 563.21 us | 177.6 tok/s | 1,775.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.18 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.02 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x318-pipeline | DeepSeek-V4.1-Flash | 318 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x318-tensor | DeepSeek-V4.1-Flash | 318 | tensor | nvlink3 | infiniband_hdr | 160 | 827.81 us | 120.8 tok/s | 1,208.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 40 on infiniband_hdr (traversals 2.0) = 420.65 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x318-hybrid | DeepSeek-V4.1-Flash | 318 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x318-expert | DeepSeek-V4.1-Flash | 318 | expert | nvlink3 | infiniband_hdr | 160 | 563.20 us | 177.6 tok/s | 1,775.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.18 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.02 us |
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
| DeepSeek-V4.1-Flash | 1 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318 | 259,170 | 9,941.6 | 0.038 | 9,941.6 (259,170) | 5,682.5 (138,675) | 0.57x | compute |
| DeepSeek-V4.1-Flash | 2 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318 | 259,170 | 9,941.6 | 0.038 | 9,941.6 (259,170) | 5,479.9 (277,350) | 0.55x | compute |
| DeepSeek-V4.1-Flash | 4 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318 | 259,170 | 9,941.6 | 0.038 | 9,941.6 (259,170) | 5,479.9 (277,350) | 0.55x | compute |
| DeepSeek-V4.1-Flash | 8 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318 | 259,170 | 9,941.6 | 0.038 | 9,941.6 (259,170) | 5,306.0 (277,350) | 0.53x | compute |
| DeepSeek-V4.1-Flash | 16 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318 | 259,170 | 9,941.6 | 0.038 | 9,941.6 (259,170) | 5,288.8 (554,700) | 0.53x | compute |
| DeepSeek-V4.1-Flash | 32 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318 | 259,170 | 9,941.6 | 0.038 | 9,941.6 (259,170) | 4,694.7 (554,700) | 0.47x | compute |
| DeepSeek-V4.1-Flash | 64 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x318 | 259,170 | 9,941.6 | 0.038 | 9,941.6 (259,170) | 3,833.5 (554,700) | 0.39x | compute |
| DeepSeek-V4.1-Flash | 256 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 3,826.1 | 0.014 | 3,826.1 (277,100) | 1,824.9 (554,700) | 0.48x | compute |
| DeepSeek-V4.1-Flash | 1024 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340 | 277,100 | 1,013.5 | 0.004 | 1,013.5 (277,100) | 647.4 (554,700) | 0.64x | compute |
| DeepSeek-V4.1-Flash | 4096 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340 | 277,100 | 255.6 | 0.001 | 255.6 (277,100) | 163.0 (554,700) | 0.64x | compute |

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
| DeepSeek-V4.1-Flash | 1 | sram | 988,627.7 | 26,083.3 | 26,083.3 | 37.90x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | sram | 988,627.7 | 26,083.3 | 26,083.3 | 37.90x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | sram | 988,627.7 | 26,083.3 | 31,711.5 | 37.90x | 1.22x | weight_read | weight_read | link_latency |
| DeepSeek-V4.1-Flash | 8 | sram | 988,627.7 | 26,083.3 | 51,745.0 | 37.90x | 1.98x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | sram | 988,627.7 | 26,083.3 | 84,399.6 | 37.90x | 3.24x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | sram | 988,627.7 | 26,083.3 | 126,204.8 | 37.90x | 4.84x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | sram | 988,627.7 | 26,083.3 | 175,832.9 | 37.90x | 6.74x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 256 | sram | 988,627.7 | 26,083.3 | 243,458.4 | 37.90x | 9.33x | weight_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash | 1024 | sram | 1,046,895.0 | 26,104.2 | 344,051.0 | 40.10x | 13.18x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | sram | 1,056,005.7 | 26,110.7 | 383,338.4 | 40.44x | 14.68x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash | 1 | rom | 716,112.9 | 162,098.2 | 162,098.2 | 4.42x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | rom | 716,112.9 | 162,098.2 | 162,098.2 | 4.42x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | rom | 716,112.9 | 162,098.2 | 162,098.2 | 4.42x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | rom | 716,112.9 | 162,098.2 | 162,098.2 | 4.42x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | rom | 716,112.9 | 162,098.2 | 162,098.2 | 4.42x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | rom | 716,112.9 | 162,098.2 | 162,098.2 | 4.42x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | rom | 716,112.9 | 162,098.2 | 179,846.9 | 4.42x | 1.11x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash | 256 | rom | 716,112.9 | 162,098.2 | 275,334.6 | 4.42x | 1.70x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash | 1024 | rom | 727,528.8 | 162,869.0 | 366,380.2 | 4.47x | 2.25x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | rom | 731,917.0 | 163,159.5 | 427,955.6 | 4.49x | 2.62x | compute | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash | 1 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 988,627.7 | 3.547 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 716,112.9 | 2.569 | compute | 0.72x |
| DeepSeek-V4.1-Flash | 1 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 1 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 2 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 988,627.7 | 3.547 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 2 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 716,112.9 | 2.569 | compute | 0.72x |
| DeepSeek-V4.1-Flash | 2 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 2 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 4 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 988,627.7 | 3.547 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 716,112.9 | 2.569 | compute | 0.72x |
| DeepSeek-V4.1-Flash | 4 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 4 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x60-perregion | 48,900 | 1.00 | 1.43 | 31,711.5 | 0.648 | link_latency | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 8 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 988,627.7 | 3.547 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 8 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 716,112.9 | 2.569 | compute | 0.72x |
| DeepSeek-V4.1-Flash | 8 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 8 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x60-perregion | 48,900 | 1.00 | 1.99 | 51,745.0 | 1.058 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash | 8 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 16 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 988,627.7 | 3.547 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 16 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 716,112.9 | 2.569 | compute | 0.72x |
| DeepSeek-V4.1-Flash | 16 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 16 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 16 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x60-perregion | 48,900 | 1.00 | 2.54 | 84,399.6 | 1.726 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 16 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 32 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 988,627.7 | 3.547 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 32 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 716,112.9 | 2.569 | compute | 0.72x |
| DeepSeek-V4.1-Flash | 32 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 32 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 32 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x60-perregion | 48,900 | 1.00 | 3.49 | 126,204.8 | 2.581 | weight_read | 0.13x |
| DeepSeek-V4.1-Flash | 32 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 64 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 988,627.7 | 3.547 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 64 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 716,112.9 | 2.569 | compute | 0.72x |
| DeepSeek-V4.1-Flash | 64 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 64 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 64 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x60-perregion | 48,900 | 1.00 | 4.92 | 175,832.9 | 3.596 | weight_read | 0.18x |
| DeepSeek-V4.1-Flash | 64 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 6.25 | 2.18 | 179,846.9 | 0.648 | kv_read | 0.18x |
| DeepSeek-V4.1-Flash | 256 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 988,627.7 | 3.547 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 256 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 716,112.9 | 2.569 | compute | 0.72x |
| DeepSeek-V4.1-Flash | 256 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,083.3 | 0.094 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 256 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 1.00 | 162,098.2 | 0.584 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 256 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-tensor-x6-perregion | 277,350 | 1.00 | 10.96 | 243,458.4 | 0.878 | kv_read | 0.25x |
| DeepSeek-V4.1-Flash | 256 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 6.25 | 4.02 | 275,334.6 | 0.993 | kv_read | 0.28x |
| DeepSeek-V4.1-Flash | 1024 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 1,046,895.0 | 3.756 | compute | 1.00x |
| DeepSeek-V4.1-Flash | 1024 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 727,528.8 | 2.610 | compute | 0.69x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x60-perstream | 48,900 | 1.00 | 17.07 | 26,104.2 | 0.534 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 3.00 | 162,869.0 | 0.587 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 1024 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion | 48,900 | 1.00 | 5.09 | 344,051.0 | 7.036 | weight_read | 0.33x |
| DeepSeek-V4.1-Flash | 1024 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x67-perregion-romfill | 54,605 | 1.13 | 4.77 | 366,380.2 | 6.710 | weight_read | 0.35x |
| DeepSeek-V4.1-Flash | 4096 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342 | 278,730 | 1.00 | 1.00 | 1,056,005.7 | 3.789 | compute | 1.00x |
| DeepSeek-V4.1-Flash | 4096 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x342-romfill | 278,730 | 1.62 | 1.00 | 731,917.0 | 2.626 | compute | 0.69x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 12.01 | 26,110.7 | 0.094 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 6.25 | 12.01 | 163,159.5 | 0.588 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash | 4096 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion | 48,900 | 1.00 | 11.43 | 383,338.4 | 7.839 | kv_read | 0.36x |
| DeepSeek-V4.1-Flash | 4096 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x67-perregion-romfill | 54,605 | 1.13 | 10.55 | 427,955.6 | 7.837 | kv_read | 0.41x |

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
| DeepSeek-V4.1-Flash | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash | 2 | 55 | 10.79 | 6.94 | 1.56x |
| DeepSeek-V4.1-Flash | 4 | 55 | 19.23 | 9.76 | 1.97x |
| DeepSeek-V4.1-Flash | 8 | 55 | 31.11 | 13.27 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 55 | 43.55 | 17.27 | 2.52x |
| DeepSeek-V4.1-Flash | 32 | 55 | 51.62 | 21.32 | 2.42x |
| DeepSeek-V4.1-Flash | 64 | 55 | 54.37 | 24.83 | 2.19x |
| DeepSeek-V4.1-Flash | 256 | 55 | 54.95 | 28.10 | 1.96x |
| DeepSeek-V4.1-Flash | 1024 | 55 | 54.95 | 28.23 | 1.95x |
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
| DeepSeek-V4.1-Flash | 1 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4.1-Flash | 2 | 60 | 10.88 | 7.10 | 1.53x |
| DeepSeek-V4.1-Flash | 4 | 60 | 19.54 | 10.01 | 1.95x |
| DeepSeek-V4.1-Flash | 8 | 60 | 32.05 | 13.70 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 60 | 45.75 | 17.96 | 2.55x |
| DeepSeek-V4.1-Flash | 32 | 60 | 55.34 | 22.31 | 2.48x |
| DeepSeek-V4.1-Flash | 64 | 60 | 59.00 | 26.11 | 2.26x |
| DeepSeek-V4.1-Flash | 256 | 60 | 59.89 | 29.68 | 2.02x |
| DeepSeek-V4.1-Flash | 1024 | 60 | 59.91 | 29.83 | 2.01x |
| DeepSeek-V4.1-Flash | 4096 | 60 | 59.91 | 29.83 | 2.01x |
| DeepSeek-V4.1-Flash | 1 | 66 | 5.78 | 5.01 | 1.15x |
| DeepSeek-V4.1-Flash | 2 | 66 | 10.97 | 7.27 | 1.51x |
| DeepSeek-V4.1-Flash | 4 | 66 | 19.86 | 10.28 | 1.93x |
| DeepSeek-V4.1-Flash | 8 | 66 | 33.03 | 14.19 | 2.33x |
| DeepSeek-V4.1-Flash | 16 | 66 | 48.12 | 18.73 | 2.57x |
| DeepSeek-V4.1-Flash | 32 | 66 | 59.52 | 23.42 | 2.54x |
| DeepSeek-V4.1-Flash | 64 | 66 | 64.41 | 27.56 | 2.34x |
| DeepSeek-V4.1-Flash | 256 | 66 | 65.79 | 31.48 | 2.09x |
| DeepSeek-V4.1-Flash | 1024 | 66 | 65.81 | 31.65 | 2.08x |
| DeepSeek-V4.1-Flash | 4096 | 66 | 65.81 | 31.65 | 2.08x |
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
| DeepSeek-V4.1-Flash | 1 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 113 | 11.35 | 8.30 | 1.37x |
| DeepSeek-V4.1-Flash | 4 | 113 | 21.26 | 11.72 | 1.81x |
| DeepSeek-V4.1-Flash | 8 | 113 | 37.56 | 17.07 | 2.20x |
| DeepSeek-V4.1-Flash | 16 | 113 | 60.17 | 23.29 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 113 | 83.74 | 30.18 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 113 | 100.07 | 36.59 | 2.74x |
| DeepSeek-V4.1-Flash | 256 | 113 | 109.05 | 42.97 | 2.54x |
| DeepSeek-V4.1-Flash | 1024 | 113 | 109.28 | 43.24 | 2.53x |
| DeepSeek-V4.1-Flash | 4096 | 113 | 109.28 | 43.24 | 2.53x |
| DeepSeek-V4.1-Flash | 1 | 122 | 5.88 | 5.39 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 122 | 11.39 | 8.44 | 1.35x |
| DeepSeek-V4.1-Flash | 4 | 122 | 21.41 | 11.93 | 1.79x |
| DeepSeek-V4.1-Flash | 8 | 122 | 38.08 | 17.49 | 2.18x |
| DeepSeek-V4.1-Flash | 16 | 122 | 61.66 | 23.95 | 2.57x |
| DeepSeek-V4.1-Flash | 32 | 122 | 87.09 | 31.20 | 2.79x |
| DeepSeek-V4.1-Flash | 64 | 122 | 105.60 | 37.98 | 2.78x |
| DeepSeek-V4.1-Flash | 256 | 122 | 116.53 | 44.79 | 2.60x |
| DeepSeek-V4.1-Flash | 1024 | 122 | 116.83 | 45.08 | 2.59x |
| DeepSeek-V4.1-Flash | 4096 | 122 | 116.83 | 45.08 | 2.59x |
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
| DeepSeek-V4.1-Flash | 1 | 135 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 135 | 11.44 | 8.63 | 1.32x |
| DeepSeek-V4.1-Flash | 4 | 135 | 21.59 | 12.21 | 1.77x |
| DeepSeek-V4.1-Flash | 8 | 135 | 38.71 | 18.04 | 2.15x |
| DeepSeek-V4.1-Flash | 16 | 135 | 63.52 | 24.82 | 2.56x |
| DeepSeek-V4.1-Flash | 32 | 135 | 91.40 | 32.55 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 135 | 112.97 | 39.87 | 2.83x |
| DeepSeek-V4.1-Flash | 256 | 135 | 126.83 | 47.25 | 2.68x |
| DeepSeek-V4.1-Flash | 1024 | 135 | 127.23 | 47.56 | 2.68x |
| DeepSeek-V4.1-Flash | 4096 | 135 | 127.23 | 47.56 | 2.68x |
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
| DeepSeek-V4.1-Flash | 1 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 142 | 11.46 | 8.73 | 1.31x |
| DeepSeek-V4.1-Flash | 4 | 142 | 21.68 | 12.35 | 1.76x |
| DeepSeek-V4.1-Flash | 8 | 142 | 39.01 | 18.31 | 2.13x |
| DeepSeek-V4.1-Flash | 16 | 142 | 64.42 | 25.25 | 2.55x |
| DeepSeek-V4.1-Flash | 32 | 142 | 93.50 | 33.24 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 142 | 116.66 | 40.82 | 2.86x |
| DeepSeek-V4.1-Flash | 256 | 142 | 132.12 | 48.50 | 2.72x |
| DeepSeek-V4.1-Flash | 1024 | 142 | 132.59 | 48.83 | 2.72x |
| DeepSeek-V4.1-Flash | 4096 | 142 | 132.59 | 48.83 | 2.72x |
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
| DeepSeek-V4.1-Flash | 1 | 171 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 171 | 11.53 | 9.06 | 1.27x |
| DeepSeek-V4.1-Flash | 4 | 171 | 21.97 | 12.90 | 1.70x |
| DeepSeek-V4.1-Flash | 8 | 171 | 40.02 | 19.25 | 2.08x |
| DeepSeek-V4.1-Flash | 16 | 171 | 67.45 | 26.83 | 2.51x |
| DeepSeek-V4.1-Flash | 32 | 171 | 100.89 | 35.78 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 171 | 130.09 | 44.40 | 2.93x |
| DeepSeek-V4.1-Flash | 256 | 171 | 152.28 | 53.27 | 2.86x |
| DeepSeek-V4.1-Flash | 1024 | 171 | 153.02 | 53.65 | 2.85x |
| DeepSeek-V4.1-Flash | 4096 | 171 | 153.02 | 53.65 | 2.85x |
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
| DeepSeek-V4.1-Flash | 1 | 205 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 205 | 11.59 | 9.38 | 1.24x |
| DeepSeek-V4.1-Flash | 4 | 205 | 22.20 | 13.47 | 1.65x |
| DeepSeek-V4.1-Flash | 8 | 205 | 40.86 | 20.11 | 2.03x |
| DeepSeek-V4.1-Flash | 16 | 205 | 70.07 | 28.44 | 2.46x |
| DeepSeek-V4.1-Flash | 32 | 205 | 107.52 | 38.39 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 205 | 142.78 | 48.05 | 2.97x |
| DeepSeek-V4.1-Flash | 256 | 205 | 172.59 | 58.13 | 2.97x |
| DeepSeek-V4.1-Flash | 1024 | 205 | 173.65 | 58.57 | 2.96x |
| DeepSeek-V4.1-Flash | 4096 | 205 | 173.65 | 58.57 | 2.96x |
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
| DeepSeek-V4.1-Flash | 1 | 316 | 5.95 | 5.75 | 1.04x |
| DeepSeek-V4.1-Flash | 2 | 316 | 11.70 | 10.05 | 1.16x |
| DeepSeek-V4.1-Flash | 4 | 316 | 22.63 | 14.96 | 1.51x |
| DeepSeek-V4.1-Flash | 8 | 316 | 42.40 | 21.90 | 1.94x |
| DeepSeek-V4.1-Flash | 16 | 316 | 75.04 | 32.66 | 2.30x |
| DeepSeek-V4.1-Flash | 32 | 316 | 120.82 | 44.68 | 2.70x |
| DeepSeek-V4.1-Flash | 64 | 316 | 170.11 | 56.99 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 316 | 220.40 | 70.47 | 3.13x |
| DeepSeek-V4.1-Flash | 1024 | 316 | 222.44 | 71.06 | 3.13x |
| DeepSeek-V4.1-Flash | 4096 | 316 | 222.44 | 71.06 | 3.13x |
| DeepSeek-V4.1-Flash | 1 | 318 | 5.95 | 5.75 | 1.04x |
| DeepSeek-V4.1-Flash | 2 | 318 | 11.70 | 10.06 | 1.16x |
| DeepSeek-V4.1-Flash | 4 | 318 | 22.63 | 14.98 | 1.51x |
| DeepSeek-V4.1-Flash | 8 | 318 | 42.42 | 21.93 | 1.93x |
| DeepSeek-V4.1-Flash | 16 | 318 | 75.10 | 32.72 | 2.30x |
| DeepSeek-V4.1-Flash | 32 | 318 | 120.98 | 44.77 | 2.70x |
| DeepSeek-V4.1-Flash | 64 | 318 | 170.47 | 57.13 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 318 | 221.06 | 70.66 | 3.13x |
| DeepSeek-V4.1-Flash | 1024 | 318 | 223.12 | 71.25 | 3.13x |
| DeepSeek-V4.1-Flash | 4096 | 318 | 223.12 | 71.25 | 3.13x |
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
| gpu | DeepSeek-V4.1-Flash | 1 | 10.05 | 1.2% |
| rom | DeepSeek-V4.1-Flash | 1 | 10.05 | 10.1% |

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
| DeepSeek-V4.1-Flash | 1 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 403.9 | 50,087.6 |
| DeepSeek-V4.1-Flash | 2 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 403.9 | 50,087.6 |
| DeepSeek-V4.1-Flash | 4 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 403.9 | 50,087.6 |
| DeepSeek-V4.1-Flash | 8 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 403.9 | 50,087.6 |
| DeepSeek-V4.1-Flash | 16 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 403.9 | 50,087.6 |
| DeepSeek-V4.1-Flash | 32 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 403.9 | 50,087.6 |
| DeepSeek-V4.1-Flash | 64 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 403.9 | 50,087.6 |
| DeepSeek-V4.1-Flash | 256 | 3.20% | 17.8 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 196.1 | 50,205.2 |
| DeepSeek-V4.1-Flash | 1024 | 12.19% | 43.7 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 49.1 | 50,288.5 |
| DeepSeek-V4.1-Flash | 4096 | 40.56% | 125.7 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 12.3 | 50,309.3 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 34 |
| gpu | infeasible | 13 |
| gpu | link_latency | 327 |
| gpu | weight_read | 946 |
| rom | compute | 859 |
| rom | infeasible | 2158 |
| rom | kv_read | 182 |
| rom | link_latency | 1024 |
| rom | weight_read | 477 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 13 |
| rom | CAPACITY | 2158 |

## Mechanical consistency audit

**FAIL** over 122,377 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x115', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x133', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x144', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x155', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x159', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x212', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x318', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x115', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x133', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x144', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x155', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x159', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x212', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x318', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x115', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x133', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x144', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x155', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x159', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x212', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x318', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x115', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x133', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x144', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x155', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x159', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x212', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x318', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4.1-Flash', 1)

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

# Area-constrained roofline: n6_vs_a100-pro-200k

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Pro-0813 at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 77x (ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream, 795 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 5 devices. On the GPU side the correction reaches 31x (a100_sxm_80gb-x783-pipeline, 783 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 56 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Pro-0813 takes 4 x 46,225 mm2 (184,900 mm2, wafer, KV in SRAM) at 1,879 tok/s per user and 10 tok/s per 1,000 mm2, holding 1 session, against 224 copies of one unified HBM die at the same silicon: 9.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 277,350 mm2 of ROM silicon at 2,088 tok/s per user against 277,536 mm2 of a100_sxm_80gb-x336-hybrid at 190 tok/s: **11.0x**, ROM binding on `layer_fixed_latency` and the GPU on `weight_read`. It holds 1 resident session against the GPU cluster's 11,781. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 647,150 mm2 on DeepSeek-V4-Pro-0813 at batch 1, the iso-area GPU cluster is 783 devices. Cut as one serial pipeline that is 98 stages and 2,310 us of link latency per token; but the model has 61 layers, so at most 61 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 2,214 us. The iso-area per-user ratio at that point falls from 10.2x to 10.1x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 4.68x to it.** At 185,005 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 41.06 tok/s and the same silicon running hybrid delivers 192 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`) to 8.32x (DeepSeek-V4-Pro-0813, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Pro-0813 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 37 to 7,476 tok/s, and its rate with every slot occupied from 7,450 to 7,476. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 201 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,824 us over NVLink, capping per-user decode at 548 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 404.0 us and cap it at 2,475 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 7 of 10 operating points and an array 3; on tokens per second per square millimetre the same points go 9 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 44 of 3455 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 17.3x of aggregate throughput (DeepSeek-V4-Pro-0813). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 13.76x, on DeepSeek-V4-Pro-0813 at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4-Pro-0813 at 200,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-wafer-hybrid-x4`** -- 4 x 46,225 mm2 wafers, 184,900 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **1,879.0 tok/s per user** (0.53 ms/token), binding on `layer_fixed_latency`
- **10.2 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 1,879 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 11,400 W at 0.062 W/mm2, 6,067.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 224 copies of one unified HBM die -- `a100_sxm_80gb-x224-hybrid`, 185,024 mm2, area ratio 0.9993 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 184,900 | 185,024 | 0.9993 |
| user tok/s | 1,879.0 | 192.2 | 9.78x |
| aggregate tok/s | 1,879 | 5,381 | 0.20x |
| resident sessions | 1 | 7,703 | -- |
| J/token | 6.0670 | 172.5200 | 28.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 7,703 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 195.6 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 2,048.6 | 8.9 | 1 | 10.72x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,087.8 | 7.5 | 1 | 10.99x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-hybrid-x188` | 153,220 | 634.7 | 4.1 | 1 | 3.35x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,879.0 | 10.2 | 1 | 9.78x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,879.0 | 10.2 | -- | 10.2 | ACCEPT |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 2,048.6 | 8.9 | 3.7 | 10.2 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,087.8 | 7.5 | 2.3 | 10.2 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x4` **<-- recommended** | 184,900 | 4 | 1,879.0 | 1,879 | 10.2 | 1 | `layer_fixed_latency` | 11,400 | 6,067.0 | `a100_sxm_80gb-x224-hybrid` | 9.78x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 5 | 2,048.6 | 2,049 | 8.9 | 1 | `layer_fixed_latency` | 18,106 | 8,838.0 | `a100_sxm_80gb-x280-hybrid` | 10.72x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 6 | 2,087.8 | 2,088 | 7.5 | 1 | `layer_fixed_latency` | 24,809 | 11,882.8 | `a100_sxm_80gb-x336-hybrid` | 10.99x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 264 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x232` | 189,080 | 1,224.5 | 6.5 | 1 |
| array | 264 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,430.0 | 4.4 | 14,417 |
| array | 264 | smallest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x188` | 153,220 | 634.7 | 4.1 | 1 |
| wafer | 36 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,879.0 | 10.2 | 1 |
| wafer | 36 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,087.8 | 7.5 | 1 |
| wafer | 36 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,879.0 | 10.2 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,430.0 | 141,567 | 14,417 | 46,585 | 25,926.7 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 188.6 | 13,783 | 303,484.4 | 0.999 | 7.58x | 11.7x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,087.8 | 2,088 | 1 | 24,809 | 11,882.8 | `layer_fixed_latency` | `a100_sxm_80gb-x336-hybrid` | 190.0 | 11,781 | 259,603.3 | 0.999 | 10.99x | 21.8x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x325` | 264,875 | 1,415.8 | 1,416 | 1 | 22,987 | 16,236.6 | `layer_fixed_latency` | `a100_sxm_80gb-x321-hybrid` | 188.1 | 11,235 | 250,589.5 | 0.999 | 7.53x | 15.4x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,087.8 | -- | 1 | -- | 11,882.8 | -- | -- | -- | -- | -- | 0.955 | 1.47x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,430.0 | 141,567 | 14,417 | 46,585 | 12,997.3 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 188.6 | 13,783 | 153,855.9 | 0.999 | 7.58x | 11.8x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 1,881.4 | 47,035 | 4,383 | 83,350 | 21,370.8 | `layer_fixed_latency` | `a100_sxm_80gb-x783-hybrid` | 186.9 | 28,055 | 306,615.2 | 1.001 | 10.06x | 14.3x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,430.0 | 141,567 | 14,417 | 46,585 | 6,532.6 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 188.6 | 13,783 | 79,041.7 | 0.999 | 7.58x | 12.1x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 1,881.4 | 47,035 | 4,383 | 83,350 | 10,719.3 | `layer_fixed_latency` | `a100_sxm_80gb-x783-hybrid` | 186.9 | 28,055 | 155,421.3 | 1.001 | 10.06x | 14.5x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,430.0 | 141,567 | 14,417 | 46,585 | 3,300.2 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 188.6 | 13,783 | 41,634.6 | 0.999 | 7.58x | 12.6x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 1,881.4 | 47,035 | 4,383 | 83,350 | 5,393.6 | `layer_fixed_latency` | `a100_sxm_80gb-x783-hybrid` | 186.9 | 28,055 | 79,824.4 | 1.001 | 10.06x | 14.8x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,430.0 | 141,567 | 14,417 | 46,585 | 1,684.0 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 188.6 | 13,783 | 22,931.0 | 0.999 | 7.58x | 13.6x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 1,881.4 | 47,035 | 4,383 | 83,350 | 2,730.7 | `layer_fixed_latency` | `a100_sxm_80gb-x783-hybrid` | 186.9 | 28,055 | 42,025.9 | 1.001 | 10.06x | 15.4x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,430.0 | 141,567 | 14,417 | 46,585 | 876.0 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 188.6 | 13,783 | 13,579.2 | 0.999 | 7.58x | 15.5x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 1,841.2 | 92,059 | 4,383 | 86,406 | 1,428.4 | `layer_fixed_latency` | `a100_sxm_80gb-x783-hybrid` | 186.9 | 28,055 | 23,126.7 | 1.001 | 9.85x | 16.2x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,430.0 | 141,567 | 14,417 | 46,585 | 471.9 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 176.0 | 13,783 | 8,575.3 | 0.999 | 8.12x | 18.2x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 1,709.4 | 109,401 | 4,383 | 87,383 | 798.7 | `layer_fixed_latency` | `a100_sxm_80gb-x783-hybrid` | 186.9 | 28,055 | 13,677.1 | 1.001 | 9.14x | 17.1x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,093.9 | 280,029 | 14,417 | 55,451 | 198.0 | `compute` | `a100_sxm_80gb-x391-hybrid` | 95.6 | 13,783 | 4,209.5 | 0.999 | 11.44x | 21.3x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 1,024.3 | 262,211 | 4,383 | 97,465 | 371.7 | `kv_read` | `a100_sxm_80gb-x783-hybrid` | 135.4 | 28,055 | 5,731.6 | 1.001 | 7.56x | 15.4x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 401.6 | 411,276 | 14,417 | 62,770 | 152.6 | `compute` | `a100_sxm_80gb-x391-hybrid` | 37.1 | 13,783 | 3,069.0 | 0.999 | 10.83x | 20.1x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 647,150 | 364.5 | 373,235 | 4,383 | 104,790 | 280.8 | `kv_read` | `a100_sxm_80gb-x783-hybrid` | 59.6 | 28,055 | 3,755.9 | 1.001 | 6.11x | 13.4x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 110.1 | 451,162 | 14,417 | 64,080 | 142.0 | `compute` | `a100_sxm_80gb-x391-hybrid` | 13.2 | 13,783 | 2,163.9 | 0.999 | 8.32x | 15.2x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 647,150 | 99.0 | 405,346 | 4,383 | 104,899 | 258.8 | `kv_read` | `a100_sxm_80gb-x783-hybrid` | 22.1 | 28,055 | 2,600.3 | 1.001 | 4.47x | 10.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | wafer | SRAM | 1 |
| 2-16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x248` | 202,120 | array | HBM | 9,029 |
| 32-64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x260` | 211,900 | array | HBM | 9,465 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | array | HBM | 14,417 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | array | HBM | 14,417 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro-0813 | HBM | rom | 201, 208, 227, 248, 260, 297, 328, 340, 360, 361, 396 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 201, 208, 227, 248, 260, 297, 340, 349, 388, 389, 396 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 188, 192, 227, 232, 240, 278, 296, 324, 325, 340, 370 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 188, 192, 227, 232, 240, 278, 296, 324, 325, 340, 370 |

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
| DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 1 | 32 on `rom_wafer_express` | 6.51 | one_shot, rec_doubling | 362.07 | 111.11 | 68.39 | 59.75 | 1,879.0 |
| DeepSeek-V4-Pro-0813 | `a100_sxm_80gb-x224-hybrid` | 1 | 8 | 5.51 | measured_floor | 572.70 | 2,070.81 | 3,037.96 | 713.20 | 192.2 |
| DeepSeek-V4-Pro-0813 | `a100_sxm_80gb-x224-hybrid` | 64 | 8 | 5.51 | measured_floor | 572.70 | 2,519.49 | 4,311.61 | 752.79 | 148.6 |

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

- **0 of 3,455 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 32%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,379 | 0 | 60.7% | 79.8% | 0.386 | 59% |
| rom | wafer (>=40,000 mm2) | 2,076 | 0 | 20.5% | 47.9% | 0.240 | 96% |

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
| DeepSeek-V4-Pro-0813 | 1 | 231,125 | `DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x5` | 8.837968 | 18,105.5 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x280-hybrid` | 215.816891 | 68,697.7 | weight_read | 24.42x |
| DeepSeek-V4-Pro-0813 | 2 | 647,150 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14` | 21.370798 | 83,350.4 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x783-hybrid` | 306.615155 | 190,497.2 | weight_read | 14.35x |
| DeepSeek-V4-Pro-0813 | 4 | 647,150 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14` | 10.719331 | 83,350.4 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x783-hybrid` | 155.421296 | 190,497.2 | weight_read | 14.50x |
| DeepSeek-V4-Pro-0813 | 8 | 647,150 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14` | 5.393597 | 83,350.4 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x783-hybrid` | 79.824366 | 190,497.2 | weight_read | 14.80x |
| DeepSeek-V4-Pro-0813 | 16 | 647,150 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14` | 2.730730 | 83,350.4 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x783-hybrid` | 42.025902 | 190,497.2 | weight_read | 15.39x |
| DeepSeek-V4-Pro-0813 | 32 | 647,150 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14` | 1.428371 | 86,405.9 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x783-hybrid` | 23.126669 | 190,497.2 | weight_read | 16.19x |
| DeepSeek-V4-Pro-0813 | 64 | 647,150 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14` | 0.798740 | 87,382.8 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x783-hybrid` | 13.677053 | 190,497.2 | weight_read | 17.12x |
| DeepSeek-V4-Pro-0813 | 256 | 316,220 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x388` | 0.197169 | 53,927.8 | compute | `DSV4-Pro/a100_sxm_80gb-x383-hybrid` | 4.176368 | 101,094.0 | weight_read | 21.18x |
| DeepSeek-V4-Pro-0813 | 1024 | 316,220 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x388` | 0.153096 | 60,799.5 | compute | `DSV4-Pro/a100_sxm_80gb-x383-hybrid` | 3.053064 | 114,224.0 | weight_read | 19.94x |
| DeepSeek-V4-Pro-0813 | 4096 | 316,220 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x388` | 0.142788 | 61,991.3 | compute | `DSV4-Pro/a100_sxm_80gb-x383-hybrid` | 2.150325 | 114,855.5 | weight_read | 15.06x |

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
| DeepSeek-V4-Pro-0813 | 200,000 | 1,600 B | 892.7 GB | 4.46 | 0.473 GB | 1.978 GB | 83.8 |

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
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 2,634.4 | wafer-pipeline | 1,879.0 | wafer-hybrid | 1.40x | 1,178.0 | pipeline | 192.2 | hybrid | 6.13x | 2.24x | 9.78x | 4.37x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 2,643.6 | wafer-pipeline | 2,087.8 | wafer-hybrid | 1.27x | 1,226.3 | pipeline | 190.0 | hybrid | 6.46x | 2.16x | 10.99x | 5.10x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 2,643.6 | wafer-pipeline | 2,022.3 | wafer-hybrid | 1.31x | 1,251.9 | pipeline | 187.8 | hybrid | 6.67x | 2.11x | 10.77x | 5.10x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 2,643.6 | wafer-pipeline | 1,908.9 | wafer-hybrid | 1.38x | 1,278.7 | pipeline | 187.0 | hybrid | 6.84x | 2.07x | 10.21x | 4.94x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 4.37x to 5.10x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x6 | 277,350 | 2,087.8 | 2,087.8 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x336-hybrid | 277,536 | 1.00x | hybrid | 2,131.35 | 190.0 | 7,978.6 | weight_read | 10.99x | 0.15x | 50.85x | 10.99x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x188 | 153,220 | 634.7 | 634.7 | link_latency | DSV4-Pro/a100_sxm_80gb-x185-hybrid | 152,810 | 1.00x | hybrid | 2,053.52 | 189.3 | 4,542.8 | weight_read | 3.35x | 0.08x | 15.46x | 3.35x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,881.4 | 47,034.9 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x783-hybrid | 646,758 | 1.00x | hybrid | 2,213.52 | 186.9 | 18,319.5 | weight_read | 10.06x | 1.46x | 45.82x | 10.25x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x201 | 163,815 | 509.7 | 2,038.9 | link_latency | DSV4-Pro/a100_sxm_80gb-x198-hybrid | 163,548 | 1.00x | hybrid | 2,057.84 | 191.7 | 4,792.6 | weight_read | 2.66x | 0.25x | 12.41x | 2.66x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,881.4 | 47,034.9 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x783-hybrid | 646,758 | 1.00x | hybrid | 2,213.52 | 186.9 | 18,319.5 | weight_read | 10.06x | 1.46x | 45.82x | 10.25x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x201 | 163,815 | 509.7 | 2,038.9 | link_latency | DSV4-Pro/a100_sxm_80gb-x198-hybrid | 163,548 | 1.00x | hybrid | 2,057.84 | 191.7 | 4,792.6 | weight_read | 2.66x | 0.25x | 12.41x | 2.66x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,881.4 | 47,034.9 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x783-hybrid | 646,758 | 1.00x | hybrid | 2,213.52 | 186.9 | 18,319.5 | weight_read | 10.06x | 1.46x | 45.82x | 10.25x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x201 | 163,815 | 453.4 | 3,627.0 | compute | DSV4-Pro/a100_sxm_80gb-x198-hybrid | 163,548 | 1.00x | hybrid | 2,057.84 | 191.7 | 4,792.6 | weight_read | 2.37x | 0.45x | 11.04x | 2.37x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,881.4 | 47,034.9 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x783-hybrid | 646,758 | 1.00x | hybrid | 2,213.52 | 186.9 | 18,319.5 | weight_read | 10.06x | 1.46x | 45.82x | 10.25x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x201 | 163,815 | 327.4 | 5,238.7 | compute | DSV4-Pro/a100_sxm_80gb-x198-hybrid | 163,548 | 1.00x | hybrid | 2,057.84 | 191.7 | 4,792.6 | weight_read | 1.71x | 0.64x | 7.97x | 1.71x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,841.2 | 92,059.5 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x783-hybrid | 646,758 | 1.00x | hybrid | 2,213.52 | 186.9 | 18,319.5 | weight_read | 9.85x | 2.86x | 44.84x | 10.03x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x201 | 163,815 | 199.1 | 6,371.8 | compute | DSV4-Pro/a100_sxm_80gb-x198-hybrid | 163,548 | 1.00x | hybrid | 2,153.62 | 180.1 | 5,764.5 | weight_read | 1.11x | 0.78x | 4.85x | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,709.4 | 109,400.8 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x783-hybrid | 646,758 | 1.00x | hybrid | 2,213.52 | 186.9 | 18,319.5 | weight_read | 9.14x | 3.40x | 41.63x | 9.31x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x201 | 163,815 | 108.9 | 6,971.4 | compute | DSV4-Pro/a100_sxm_80gb-x198-hybrid | 163,548 | 1.00x | hybrid | 2,591.50 | 141.5 | 9,053.9 | weight_read | 0.77x | 0.77x | 2.65x | 0.77x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 1,093.9 | 280,028.6 | compute | DSV4-Pro/a100_sxm_80gb-x391-hybrid | 322,966 | 1.00x | hybrid | 3,548.05 | 95.6 | 24,486.1 | weight_read | 11.44x | 11.44x | 26.64x | 11.44x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x201 | 163,815 | 29.1 | 7,460.4 | compute | DSV4-Pro/a100_sxm_80gb-x198-hybrid | 163,548 | 1.00x | hybrid | 4,926.09 | 62.6 | 16,019.8 | weight_read | 0.47x | 0.47x | 0.78x | 0.47x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 401.6 | 411,276.1 | compute | DSV4-Pro/a100_sxm_80gb-x391-hybrid | 322,966 | 1.00x | hybrid | 3,278.35 | 37.1 | 37,981.1 | weight_read | 10.83x | 10.83x | 14.90x | 10.91x |
| DeepSeek-V4-Pro-0813 | 1024 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x201 | 163,815 | 7.3 | 7,478.6 | compute | DSV4-Pro/a100_sxm_80gb-x198-hybrid | 163,548 | 1.00x | hybrid | 4,795.75 | 22.5 | 22,988.9 | weight_read | 0.33x | 0.33x | 0.41x | 0.33x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 110.1 | 451,162.4 | compute | DSV4-Pro/a100_sxm_80gb-x391-hybrid | 322,966 | 1.00x | hybrid | 14,800.19 | 13.2 | 54,209.5 | weight_read | 8.32x | 8.32x | 10.46x | 8.38x |
| DeepSeek-V4-Pro-0813 | 4096 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x201 | 163,815 | 1.8 | 7,476.2 | compute | DSV4-Pro/a100_sxm_80gb-x198-hybrid | 163,548 | 1.00x | hybrid | 57,431.12 | 8.5 | 34,869.7 | link_latency | 0.21x | 0.21x | 0.29x | 0.21x |

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
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 41.1 | 111.0 | 195.6 | hybrid | 1,980.00 | 38.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 95 | 78,470 | 41.1 | 105.2 | 193.8 | hybrid | 2,001.62 | 38.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 111 | 91,686 | 41.1 | 103.2 | 193.6 | hybrid | 2,010.27 | 38.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 41.1 | 103.1 | 194.4 | hybrid | 2,010.27 | 39.1% | weight_read |
| DeepSeek-V4-Pro-0813 | 116 | 95,816 | 41.1 | 102.5 | 191.0 | hybrid | 2,014.60 | 38.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 125 | 103,250 | 41.1 | 101.5 | 191.8 | hybrid | 2,018.92 | 38.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 41.1 | 91.9 | 193.3 | hybrid | 2,040.54 | 39.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 185 | 152,810 | 41.1 | 90.3 | 189.3 | hybrid | 2,053.52 | 38.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 189 | 156,114 | 41.1 | 90.0 | 191.3 | hybrid | 2,053.52 | 39.3% | weight_read |
| DeepSeek-V4-Pro-0813 | 198 | 163,548 | 41.1 | 89.2 | 191.7 | hybrid | 2,057.84 | 39.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 205 | 169,330 | 41.1 | 88.6 | 191.1 | hybrid | 2,062.16 | 39.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 41.1 | 87.0 | 192.2 | hybrid | 2,070.81 | 39.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 229 | 189,154 | 41.1 | 86.6 | 190.8 | hybrid | 2,075.14 | 39.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 237 | 195,762 | 41.1 | 86.0 | 190.7 | hybrid | 2,079.46 | 39.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 245 | 202,370 | 41.1 | 85.3 | 190.6 | hybrid | 2,083.79 | 39.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 257 | 212,282 | 41.1 | 84.4 | 188.9 | hybrid | 2,092.43 | 39.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 274 | 226,324 | 41.1 | 83.1 | 189.0 | hybrid | 2,101.08 | 39.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 41.1 | 82.7 | 191.1 | hybrid | 2,101.08 | 40.1% | weight_read |
| DeepSeek-V4-Pro-0813 | 292 | 241,192 | 41.1 | 81.8 | 189.5 | hybrid | 2,109.73 | 40.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 293 | 242,018 | 41.1 | 81.7 | 189.8 | hybrid | 2,109.73 | 40.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 320 | 264,320 | 41.1 | 79.9 | 190.3 | hybrid | 2,122.71 | 40.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 321 | 265,146 | 41.1 | 71.9 | 188.1 | hybrid | 2,127.03 | 40.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 324 | 267,624 | 41.1 | 71.8 | 189.0 | hybrid | 2,127.03 | 40.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 335 | 276,710 | 41.1 | 71.2 | 189.7 | hybrid | 2,131.35 | 40.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 41.1 | 71.1 | 190.0 | hybrid | 2,131.35 | 40.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 344 | 284,144 | 41.1 | 70.7 | 189.8 | hybrid | 2,135.68 | 40.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 355 | 293,230 | 41.1 | 70.1 | 188.2 | hybrid | 2,144.33 | 40.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 356 | 294,056 | 41.1 | 70.1 | 188.5 | hybrid | 2,144.33 | 40.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 365 | 301,490 | 41.1 | 69.6 | 188.6 | hybrid | 2,148.65 | 40.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 383 | 316,358 | 41.1 | 68.7 | 188.8 | hybrid | 2,157.30 | 40.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 384 | 317,184 | 41.1 | 68.7 | 189.0 | hybrid | 2,157.30 | 40.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 391 | 322,966 | 41.1 | 68.3 | 188.6 | hybrid | 2,161.63 | 40.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 41.1 | 65.6 | 187.8 | hybrid | 2,191.90 | 41.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 41.1 | 56.8 | 187.0 | hybrid | 2,213.52 | 41.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 783 | 646,758 | 41.1 | 53.2 | 186.9 | hybrid | 2,213.52 | 41.4% | weight_read |

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
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x325 | DeepSeek-V4-Pro-0813 | 325 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 6.93 us | 14,435.6 tok/s | 144,355.6 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.40 us; 30 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.52 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x192 | DeepSeek-V4-Pro-0813 | 192 | tensor | rom_package_ucie | rom_board_serdes | 244 | 511.25 us | 195.6 tok/s | 1,956.0 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 122 x all_reduce span 96 on rom_board_serdes (traversals 19.8) = 507.94 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x296 | DeepSeek-V4-Pro-0813 | 296 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 16.36 us | 6,113.0 tok/s | 61,130.2 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 13.05 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x324 | DeepSeek-V4-Pro-0813 | 324 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6 | DeepSeek-V4-Pro-0813 | 6 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.59 us | 13,181.2 tok/s | 131,812.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x188 | DeepSeek-V4-Pro-0813 | 188 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | rom_wafer_serdes | 244 | 291.64 us | 342.9 tok/s | 3,428.9 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 56.79 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x240 | DeepSeek-V4-Pro-0813 | 240 | hybrid | nvlink3 | infiniband_hdr | 151 | 700.80 us | 142.7 tok/s | 1,426.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 29 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.50 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer | rom_wafer_serdes | 126 | 235.70 us | 424.3 tok/s | 4,242.7 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.85 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x389 | DeepSeek-V4-Pro-0813 | 389 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 6.93 us | 14,435.6 tok/s | 144,355.6 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.40 us; 30 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.52 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x208 | DeepSeek-V4-Pro-0813 | 208 | tensor | rom_package_ucie | rom_board_serdes | 244 | 567.34 us | 176.3 tok/s | 1,762.6 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 122 x all_reduce span 104 on rom_board_serdes (traversals 22.0) = 564.04 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x349 | DeepSeek-V4-Pro-0813 | 349 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 16.36 us | 6,113.0 tok/s | 61,130.2 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 13.05 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x388 | DeepSeek-V4-Pro-0813 | 388 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | DeepSeek-V4-Pro-0813 | 14 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.59 us | 13,181.2 tok/s | 131,812.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x201 | DeepSeek-V4-Pro-0813 | 201 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x14 | DeepSeek-V4-Pro-0813 | 14 | tensor | on_wafer | rom_wafer_serdes | 244 | 404.00 us | 247.5 tok/s | 2,475.3 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 14 on rom_wafer_serdes (traversals 6.6) = 169.15 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x260 | DeepSeek-V4-Pro-0813 | 260 | hybrid | nvlink3 | infiniband_hdr | 154 | 708.61 us | 141.1 tok/s | 1,411.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 32 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 83.31 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | DeepSeek-V4-Pro-0813 | 14 | hybrid | on_wafer | rom_wafer_serdes | 135 | 237.60 us | 420.9 tok/s | 4,208.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 13 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 2.75 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,300.52 us | 76.9 tok/s | 768.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 675.22 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 640.92 us | 156.0 tok/s | 1,560.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink3 | infiniband_hdr | 244 | 867.34 us | 115.3 tok/s | 1,152.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 612.19 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 255.16 us |
| DSV4-Pro/a100_sxm_80gb-x95-pipeline | DeepSeek-V4-Pro-0813 | 95 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x95-tensor | DeepSeek-V4-Pro-0813 | 95 | tensor | nvlink3 | infiniband_hdr | 244 | 1,313.01 us | 76.2 tok/s | 761.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 687.71 us |
| DSV4-Pro/a100_sxm_80gb-x95-hybrid | DeepSeek-V4-Pro-0813 | 95 | hybrid | nvlink3 | infiniband_hdr | 133 | 653.94 us | 152.9 tok/s | 1,529.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| DSV4-Pro/a100_sxm_80gb-x95-expert | DeepSeek-V4-Pro-0813 | 95 | expert | nvlink3 | infiniband_hdr | 244 | 863.47 us | 115.8 tok/s | 1,158.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.39 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 252.08 us |
| DSV4-Pro/a100_sxm_80gb-x111-pipeline | DeepSeek-V4-Pro-0813 | 111 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x111-tensor | DeepSeek-V4-Pro-0813 | 111 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x111-hybrid | DeepSeek-V4-Pro-0813 | 111 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x111-expert | DeepSeek-V4-Pro-0813 | 111 | expert | nvlink3 | infiniband_hdr | 244 | 862.62 us | 115.9 tok/s | 1,159.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.18 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.44 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x112-expert | DeepSeek-V4-Pro-0813 | 112 | expert | nvlink3 | infiniband_hdr | 244 | 862.50 us | 115.9 tok/s | 1,159.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.09 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.41 us |
| DSV4-Pro/a100_sxm_80gb-x116-pipeline | DeepSeek-V4-Pro-0813 | 116 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x116-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink3 | infiniband_hdr | 244 | 1,316.51 us | 76.0 tok/s | 759.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 691.21 us |
| DSV4-Pro/a100_sxm_80gb-x116-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink3 | infiniband_hdr | 136 | 661.75 us | 151.1 tok/s | 1,511.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.45 us |
| DSV4-Pro/a100_sxm_80gb-x116-expert | DeepSeek-V4-Pro-0813 | 116 | expert | nvlink3 | infiniband_hdr | 244 | 862.37 us | 116.0 tok/s | 1,159.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.09 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.28 us |
| DSV4-Pro/a100_sxm_80gb-x125-pipeline | DeepSeek-V4-Pro-0813 | 125 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x125-tensor | DeepSeek-V4-Pro-0813 | 125 | tensor | nvlink3 | infiniband_hdr | 244 | 1,317.39 us | 75.9 tok/s | 759.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 692.08 us |
| DSV4-Pro/a100_sxm_80gb-x125-hybrid | DeepSeek-V4-Pro-0813 | 125 | hybrid | nvlink3 | infiniband_hdr | 137 | 664.36 us | 150.5 tok/s | 1,505.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.05 us |
| DSV4-Pro/a100_sxm_80gb-x125-expert | DeepSeek-V4-Pro-0813 | 125 | expert | nvlink3 | infiniband_hdr | 244 | 862.04 us | 116.0 tok/s | 1,160.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.02 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.02 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.51 us | 75.7 tok/s | 757.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 695.20 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 677.37 us | 147.6 tok/s | 1,476.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| DSV4-Pro/a100_sxm_80gb-x168-expert | DeepSeek-V4-Pro-0813 | 168 | expert | nvlink3 | infiniband_hdr | 244 | 860.89 us | 116.2 tok/s | 1,161.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.73 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 250.16 us |
| DSV4-Pro/a100_sxm_80gb-x185-pipeline | DeepSeek-V4-Pro-0813 | 185 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x185-tensor | DeepSeek-V4-Pro-0813 | 185 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x185-hybrid | DeepSeek-V4-Pro-0813 | 185 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x185-expert | DeepSeek-V4-Pro-0813 | 185 | expert | nvlink3 | infiniband_hdr | 244 | 860.59 us | 116.2 tok/s | 1,162.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.67 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.93 us |
| DSV4-Pro/a100_sxm_80gb-x189-pipeline | DeepSeek-V4-Pro-0813 | 189 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x189-tensor | DeepSeek-V4-Pro-0813 | 189 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x189-hybrid | DeepSeek-V4-Pro-0813 | 189 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x189-expert | DeepSeek-V4-Pro-0813 | 189 | expert | nvlink3 | infiniband_hdr | 244 | 860.55 us | 116.2 tok/s | 1,162.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.67 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.88 us |
| DSV4-Pro/a100_sxm_80gb-x198-pipeline | DeepSeek-V4-Pro-0813 | 198 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x198-tensor | DeepSeek-V4-Pro-0813 | 198 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.11 us | 75.6 tok/s | 756.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 696.80 us |
| DSV4-Pro/a100_sxm_80gb-x198-hybrid | DeepSeek-V4-Pro-0813 | 198 | hybrid | nvlink3 | infiniband_hdr | 146 | 687.79 us | 145.4 tok/s | 1,453.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.48 us |
| DSV4-Pro/a100_sxm_80gb-x198-expert | DeepSeek-V4-Pro-0813 | 198 | expert | nvlink3 | infiniband_hdr | 244 | 860.42 us | 116.2 tok/s | 1,162.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.64 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.78 us |
| DSV4-Pro/a100_sxm_80gb-x205-pipeline | DeepSeek-V4-Pro-0813 | 205 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x205-tensor | DeepSeek-V4-Pro-0813 | 205 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x205-hybrid | DeepSeek-V4-Pro-0813 | 205 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x205-expert | DeepSeek-V4-Pro-0813 | 205 | expert | nvlink3 | infiniband_hdr | 244 | 860.32 us | 116.2 tok/s | 1,162.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.61 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.71 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x224-expert | DeepSeek-V4-Pro-0813 | 224 | expert | nvlink3 | infiniband_hdr | 244 | 860.08 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.53 us |
| DSV4-Pro/a100_sxm_80gb-x229-pipeline | DeepSeek-V4-Pro-0813 | 229 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x229-tensor | DeepSeek-V4-Pro-0813 | 229 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.27 us | 75.6 tok/s | 755.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 697.96 us |
| DSV4-Pro/a100_sxm_80gb-x229-hybrid | DeepSeek-V4-Pro-0813 | 229 | hybrid | nvlink3 | infiniband_hdr | 150 | 698.20 us | 143.2 tok/s | 1,432.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 72.90 us |
| DSV4-Pro/a100_sxm_80gb-x229-expert | DeepSeek-V4-Pro-0813 | 229 | expert | nvlink3 | infiniband_hdr | 244 | 860.04 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.49 us |
| DSV4-Pro/a100_sxm_80gb-x237-pipeline | DeepSeek-V4-Pro-0813 | 237 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x237-tensor | DeepSeek-V4-Pro-0813 | 237 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.51 us | 75.6 tok/s | 755.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 30 on infiniband_hdr (traversals 2.0) = 698.20 us |
| DSV4-Pro/a100_sxm_80gb-x237-hybrid | DeepSeek-V4-Pro-0813 | 237 | hybrid | nvlink3 | infiniband_hdr | 151 | 700.80 us | 142.7 tok/s | 1,426.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 29 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.50 us |
| DSV4-Pro/a100_sxm_80gb-x237-expert | DeepSeek-V4-Pro-0813 | 237 | expert | nvlink3 | infiniband_hdr | 244 | 859.96 us | 116.3 tok/s | 1,162.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.53 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.43 us |
| DSV4-Pro/a100_sxm_80gb-x245-pipeline | DeepSeek-V4-Pro-0813 | 245 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x245-tensor | DeepSeek-V4-Pro-0813 | 245 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.73 us | 75.5 tok/s | 755.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 698.43 us |
| DSV4-Pro/a100_sxm_80gb-x245-hybrid | DeepSeek-V4-Pro-0813 | 245 | hybrid | nvlink3 | infiniband_hdr | 152 | 703.41 us | 142.2 tok/s | 1,421.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.10 us |
| DSV4-Pro/a100_sxm_80gb-x245-expert | DeepSeek-V4-Pro-0813 | 245 | expert | nvlink3 | infiniband_hdr | 244 | 859.88 us | 116.3 tok/s | 1,162.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.51 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.37 us |
| DSV4-Pro/a100_sxm_80gb-x257-pipeline | DeepSeek-V4-Pro-0813 | 257 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x257-tensor | DeepSeek-V4-Pro-0813 | 257 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.14 us | 75.5 tok/s | 755.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 33 on infiniband_hdr (traversals 2.0) = 698.84 us |
| DSV4-Pro/a100_sxm_80gb-x257-hybrid | DeepSeek-V4-Pro-0813 | 257 | hybrid | nvlink3 | infiniband_hdr | 154 | 708.61 us | 141.1 tok/s | 1,411.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 32 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 83.31 us |
| DSV4-Pro/a100_sxm_80gb-x257-expert | DeepSeek-V4-Pro-0813 | 257 | expert | nvlink3 | infiniband_hdr | 244 | 859.77 us | 116.3 tok/s | 1,163.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.48 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.29 us |
| DSV4-Pro/a100_sxm_80gb-x274-pipeline | DeepSeek-V4-Pro-0813 | 274 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x274-tensor | DeepSeek-V4-Pro-0813 | 274 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.51 us | 75.5 tok/s | 755.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 699.20 us |
| DSV4-Pro/a100_sxm_80gb-x274-hybrid | DeepSeek-V4-Pro-0813 | 274 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/a100_sxm_80gb-x274-expert | DeepSeek-V4-Pro-0813 | 274 | expert | nvlink3 | infiniband_hdr | 244 | 859.64 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.45 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.19 us |
| DSV4-Pro/a100_sxm_80gb-x280-pipeline | DeepSeek-V4-Pro-0813 | 280 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x280-tensor | DeepSeek-V4-Pro-0813 | 280 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.51 us | 75.5 tok/s | 755.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 699.20 us |
| DSV4-Pro/a100_sxm_80gb-x280-hybrid | DeepSeek-V4-Pro-0813 | 280 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/a100_sxm_80gb-x280-expert | DeepSeek-V4-Pro-0813 | 280 | expert | nvlink3 | infiniband_hdr | 244 | 859.60 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.44 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.16 us |
| DSV4-Pro/a100_sxm_80gb-x292-pipeline | DeepSeek-V4-Pro-0813 | 292 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x292-tensor | DeepSeek-V4-Pro-0813 | 292 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.83 us | 75.5 tok/s | 754.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 37 on infiniband_hdr (traversals 2.0) = 699.53 us |
| DSV4-Pro/a100_sxm_80gb-x292-hybrid | DeepSeek-V4-Pro-0813 | 292 | hybrid | nvlink3 | infiniband_hdr | 158 | 719.03 us | 139.1 tok/s | 1,390.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 36 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 93.72 us |
| DSV4-Pro/a100_sxm_80gb-x292-expert | DeepSeek-V4-Pro-0813 | 292 | expert | nvlink3 | infiniband_hdr | 244 | 859.52 us | 116.3 tok/s | 1,163.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.43 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.10 us |
| DSV4-Pro/a100_sxm_80gb-x293-pipeline | DeepSeek-V4-Pro-0813 | 293 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x293-tensor | DeepSeek-V4-Pro-0813 | 293 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.83 us | 75.5 tok/s | 754.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 37 on infiniband_hdr (traversals 2.0) = 699.53 us |
| DSV4-Pro/a100_sxm_80gb-x293-hybrid | DeepSeek-V4-Pro-0813 | 293 | hybrid | nvlink3 | infiniband_hdr | 158 | 719.03 us | 139.1 tok/s | 1,390.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 36 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 93.72 us |
| DSV4-Pro/a100_sxm_80gb-x293-expert | DeepSeek-V4-Pro-0813 | 293 | expert | nvlink3 | infiniband_hdr | 244 | 859.52 us | 116.3 tok/s | 1,163.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.43 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.09 us |
| DSV4-Pro/a100_sxm_80gb-x320-pipeline | DeepSeek-V4-Pro-0813 | 320 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x320-tensor | DeepSeek-V4-Pro-0813 | 320 | tensor | nvlink3 | infiniband_hdr | 244 | 1,325.26 us | 75.5 tok/s | 754.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 40 on infiniband_hdr (traversals 2.0) = 699.95 us |
| DSV4-Pro/a100_sxm_80gb-x320-hybrid | DeepSeek-V4-Pro-0813 | 320 | hybrid | nvlink3 | infiniband_hdr | 161 | 726.84 us | 137.6 tok/s | 1,375.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 101.53 us |
| DSV4-Pro/a100_sxm_80gb-x320-expert | DeepSeek-V4-Pro-0813 | 320 | expert | nvlink3 | infiniband_hdr | 244 | 859.35 us | 116.4 tok/s | 1,163.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.38 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.97 us |
| DSV4-Pro/a100_sxm_80gb-x321-pipeline | DeepSeek-V4-Pro-0813 | 321 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x321-tensor | DeepSeek-V4-Pro-0813 | 321 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.70 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 41 on infiniband_hdr (traversals 4.0) = 1,195.40 us |
| DSV4-Pro/a100_sxm_80gb-x321-hybrid | DeepSeek-V4-Pro-0813 | 321 | hybrid | nvlink3 | infiniband_hdr | 162 | 729.44 us | 137.1 tok/s | 1,370.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 40 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 104.14 us |
| DSV4-Pro/a100_sxm_80gb-x321-expert | DeepSeek-V4-Pro-0813 | 321 | expert | nvlink3 | infiniband_hdr | 244 | 859.35 us | 116.4 tok/s | 1,163.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.38 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.97 us |
| DSV4-Pro/a100_sxm_80gb-x324-pipeline | DeepSeek-V4-Pro-0813 | 324 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x324-tensor | DeepSeek-V4-Pro-0813 | 324 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.70 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 41 on infiniband_hdr (traversals 4.0) = 1,195.40 us |
| DSV4-Pro/a100_sxm_80gb-x324-hybrid | DeepSeek-V4-Pro-0813 | 324 | hybrid | nvlink3 | infiniband_hdr | 162 | 729.44 us | 137.1 tok/s | 1,370.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 40 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 104.14 us |
| DSV4-Pro/a100_sxm_80gb-x324-expert | DeepSeek-V4-Pro-0813 | 324 | expert | nvlink3 | infiniband_hdr | 244 | 859.34 us | 116.4 tok/s | 1,163.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.38 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.96 us |
| DSV4-Pro/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Pro-0813 | 335 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Pro-0813 | 335 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Pro-0813 | 335 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x335-expert | DeepSeek-V4-Pro-0813 | 335 | expert | nvlink3 | infiniband_hdr | 244 | 859.29 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.37 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.91 us |
| DSV4-Pro/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Pro-0813 | 336 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Pro-0813 | 336 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Pro-0813 | 336 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x336-expert | DeepSeek-V4-Pro-0813 | 336 | expert | nvlink3 | infiniband_hdr | 244 | 859.27 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.36 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.91 us |
| DSV4-Pro/a100_sxm_80gb-x344-pipeline | DeepSeek-V4-Pro-0813 | 344 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x344-tensor | DeepSeek-V4-Pro-0813 | 344 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.94 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 43 on infiniband_hdr (traversals 4.0) = 1,195.64 us |
| DSV4-Pro/a100_sxm_80gb-x344-hybrid | DeepSeek-V4-Pro-0813 | 344 | hybrid | nvlink3 | infiniband_hdr | 164 | 734.65 us | 136.1 tok/s | 1,361.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 109.34 us |
| DSV4-Pro/a100_sxm_80gb-x344-expert | DeepSeek-V4-Pro-0813 | 344 | expert | nvlink3 | infiniband_hdr | 244 | 859.24 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.36 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.88 us |
| DSV4-Pro/a100_sxm_80gb-x355-pipeline | DeepSeek-V4-Pro-0813 | 355 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x355-tensor | DeepSeek-V4-Pro-0813 | 355 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.16 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,195.86 us |
| DSV4-Pro/a100_sxm_80gb-x355-hybrid | DeepSeek-V4-Pro-0813 | 355 | hybrid | nvlink3 | infiniband_hdr | 166 | 739.86 us | 135.2 tok/s | 1,351.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 114.55 us |
| DSV4-Pro/a100_sxm_80gb-x355-expert | DeepSeek-V4-Pro-0813 | 355 | expert | nvlink3 | infiniband_hdr | 244 | 859.19 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.35 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.84 us |
| DSV4-Pro/a100_sxm_80gb-x356-pipeline | DeepSeek-V4-Pro-0813 | 356 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x356-tensor | DeepSeek-V4-Pro-0813 | 356 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.16 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,195.86 us |
| DSV4-Pro/a100_sxm_80gb-x356-hybrid | DeepSeek-V4-Pro-0813 | 356 | hybrid | nvlink3 | infiniband_hdr | 166 | 739.86 us | 135.2 tok/s | 1,351.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 114.55 us |
| DSV4-Pro/a100_sxm_80gb-x356-expert | DeepSeek-V4-Pro-0813 | 356 | expert | nvlink3 | infiniband_hdr | 244 | 859.19 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.35 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.84 us |
| DSV4-Pro/a100_sxm_80gb-x365-pipeline | DeepSeek-V4-Pro-0813 | 365 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x365-tensor | DeepSeek-V4-Pro-0813 | 365 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.26 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 1,195.96 us |
| DSV4-Pro/a100_sxm_80gb-x365-hybrid | DeepSeek-V4-Pro-0813 | 365 | hybrid | nvlink3 | infiniband_hdr | 167 | 742.46 us | 134.7 tok/s | 1,346.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 45 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 117.15 us |
| DSV4-Pro/a100_sxm_80gb-x365-expert | DeepSeek-V4-Pro-0813 | 365 | expert | nvlink3 | infiniband_hdr | 244 | 859.15 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.34 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.81 us |
| DSV4-Pro/a100_sxm_80gb-x383-pipeline | DeepSeek-V4-Pro-0813 | 383 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x383-tensor | DeepSeek-V4-Pro-0813 | 383 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.45 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 1,196.15 us |
| DSV4-Pro/a100_sxm_80gb-x383-hybrid | DeepSeek-V4-Pro-0813 | 383 | hybrid | nvlink3 | infiniband_hdr | 169 | 747.67 us | 133.7 tok/s | 1,337.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 122.36 us |
| DSV4-Pro/a100_sxm_80gb-x383-expert | DeepSeek-V4-Pro-0813 | 383 | expert | nvlink3 | infiniband_hdr | 244 | 859.08 us | 116.4 tok/s | 1,164.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.33 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.76 us |
| DSV4-Pro/a100_sxm_80gb-x384-pipeline | DeepSeek-V4-Pro-0813 | 384 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x384-tensor | DeepSeek-V4-Pro-0813 | 384 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.45 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 1,196.15 us |
| DSV4-Pro/a100_sxm_80gb-x384-hybrid | DeepSeek-V4-Pro-0813 | 384 | hybrid | nvlink3 | infiniband_hdr | 169 | 747.67 us | 133.7 tok/s | 1,337.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 122.36 us |
| DSV4-Pro/a100_sxm_80gb-x384-expert | DeepSeek-V4-Pro-0813 | 384 | expert | nvlink3 | infiniband_hdr | 244 | 859.07 us | 116.4 tok/s | 1,164.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.32 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.75 us |
| DSV4-Pro/a100_sxm_80gb-x391-pipeline | DeepSeek-V4-Pro-0813 | 391 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x391-tensor | DeepSeek-V4-Pro-0813 | 391 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x391-hybrid | DeepSeek-V4-Pro-0813 | 391 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x391-expert | DeepSeek-V4-Pro-0813 | 391 | expert | nvlink3 | infiniband_hdr | 244 | 859.05 us | 116.4 tok/s | 1,164.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.32 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.73 us |
| DSV4-Pro/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Pro-0813 | 448 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Pro-0813 | 448 | tensor | nvlink3 | infiniband_hdr | 244 | 1,822.07 us | 54.9 tok/s | 548.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,196.77 us |
| DSV4-Pro/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Pro-0813 | 448 | hybrid | nvlink3 | infiniband_hdr | 177 | 768.49 us | 130.1 tok/s | 1,301.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 143.19 us |
| DSV4-Pro/a100_sxm_80gb-x448-expert | DeepSeek-V4-Pro-0813 | 448 | expert | nvlink3 | infiniband_hdr | 244 | 858.87 us | 116.4 tok/s | 1,164.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.27 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.60 us |
| DSV4-Pro/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Pro-0813 | 672 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Pro-0813 | 672 | tensor | nvlink3 | infiniband_hdr | 244 | 1,823.32 us | 54.8 tok/s | 548.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,198.02 us |
| DSV4-Pro/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Pro-0813 | 672 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |
| DSV4-Pro/a100_sxm_80gb-x672-expert | DeepSeek-V4-Pro-0813 | 672 | expert | nvlink3 | infiniband_hdr | 244 | 858.47 us | 116.5 tok/s | 1,164.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.18 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.28 us |
| DSV4-Pro/a100_sxm_80gb-x783-pipeline | DeepSeek-V4-Pro-0813 | 783 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x783-tensor | DeepSeek-V4-Pro-0813 | 783 | tensor | nvlink3 | infiniband_hdr | 244 | 1,823.68 us | 54.8 tok/s | 548.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 98 on infiniband_hdr (traversals 4.0) = 1,198.38 us |
| DSV4-Pro/a100_sxm_80gb-x783-hybrid | DeepSeek-V4-Pro-0813 | 783 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |
| DSV4-Pro/a100_sxm_80gb-x783-expert | DeepSeek-V4-Pro-0813 | 783 | expert | nvlink3 | infiniband_hdr | 244 | 858.35 us | 116.5 tok/s | 1,165.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.16 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.20 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x5 | 231,125 | 2,048.6 | 0.009 | 1,367.9 (226,570) | 2,048.6 (231,125) | 1.50x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,881.4 | 0.003 | 1,391.6 (267,320) | 1,881.4 (647,150) | 1.35x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,881.4 | 0.003 | 1,391.6 (267,320) | 1,881.4 (647,150) | 1.35x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,881.4 | 0.003 | 1,391.6 (267,320) | 1,881.4 (647,150) | 1.35x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,881.4 | 0.003 | 1,391.6 (267,320) | 1,881.4 (647,150) | 1.35x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,841.2 | 0.003 | 1,391.6 (267,320) | 1,841.2 (647,150) | 1.32x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | 647,150 | 1,709.4 | 0.003 | 1,360.9 (277,100) | 1,709.4 (647,150) | 1.26x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 256 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x388 | 316,220 | 1,068.4 | 0.003 | 1,068.4 (316,220) | 1,024.3 (647,150) | 0.96x | compute |
| DeepSeek-V4-Pro-0813 | 1024 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x388 | 316,220 | 387.8 | 0.001 | 387.8 (316,220) | 364.5 (647,150) | 0.94x | compute |
| DeepSeek-V4-Pro-0813 | 4096 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x388 | 316,220 | 106.0 | 0.000 | 106.0 (316,220) | 99.0 (647,150) | 0.93x | compute |

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
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 469.5 mm2 | 84.51 mm2 (18.0%) | 180,295 mm2 | 32,453 mm2 | 195,796 mm2 = 240.2 reticles |

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
| DeepSeek-V4-Pro-0813 | 1 | sram | 362,107.0 | 26,113.2 | 26,113.2 | 13.87x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 362,107.0 | 26,113.2 | 26,113.2 | 13.87x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 362,107.0 | 26,113.2 | 26,113.2 | 13.87x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 362,107.0 | 26,113.2 | 26,113.2 | 13.87x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 362,107.0 | 26,113.2 | 26,113.2 | 13.87x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 362,107.0 | 26,113.2 | 30,200.5 | 13.87x | 1.16x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 362,107.0 | 26,113.2 | 50,144.0 | 13.87x | 1.92x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 362,107.0 | 26,113.2 | 127,687.3 | 13.87x | 4.89x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 411,276.1 | 26,113.2 | 250,415.1 | 15.75x | 9.59x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 451,162.4 | 26,113.2 | 359,355.8 | 17.28x | 13.76x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 360,586.3 | 203,180.3 | 203,180.3 | 1.77x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 360,586.3 | 203,180.3 | 203,180.3 | 1.77x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 360,586.3 | 203,180.3 | 203,180.3 | 1.77x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 360,586.3 | 203,180.3 | 203,180.3 | 1.77x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 360,586.3 | 203,180.3 | 203,180.3 | 1.77x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 360,586.3 | 203,180.3 | 203,180.3 | 1.77x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 360,586.3 | 203,180.3 | 203,180.3 | 1.77x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 360,586.3 | 203,180.3 | 256,310.9 | 1.77x | 1.26x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 386,292.7 | 206,738.9 | 368,384.3 | 1.87x | 1.78x | compute | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 421,186.4 | 216,631.0 | 406,603.8 | 1.94x | 1.88x | compute | weight_read | kv_read |

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
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | 647,150 | 1.00 | 1.00 | 362,107.0 | 0.560 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-romfill | 647,150 | 2.30 | 1.00 | 360,586.3 | 0.557 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | 647,150 | 1.00 | 1.00 | 362,107.0 | 0.560 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-romfill | 647,150 | 2.30 | 1.00 | 360,586.3 | 0.557 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | 647,150 | 1.00 | 1.00 | 362,107.0 | 0.560 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-romfill | 647,150 | 2.30 | 1.00 | 360,586.3 | 0.557 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | 647,150 | 1.00 | 1.00 | 362,107.0 | 0.560 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-romfill | 647,150 | 2.30 | 1.00 | 360,586.3 | 0.557 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | 647,150 | 1.00 | 1.00 | 362,107.0 | 0.560 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-romfill | 647,150 | 2.30 | 1.00 | 360,586.3 | 0.557 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | 647,150 | 1.00 | 1.00 | 362,107.0 | 0.560 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-romfill | 647,150 | 2.30 | 1.00 | 360,586.3 | 0.557 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion | 647,150 | 1.00 | 1.13 | 30,200.5 | 0.047 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | 647,150 | 1.00 | 1.00 | 362,107.0 | 0.560 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-romfill | 647,150 | 2.30 | 1.00 | 360,586.3 | 0.557 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion | 647,150 | 1.00 | 1.53 | 50,144.0 | 0.077 | weight_read | 0.14x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | 647,150 | 1.00 | 1.00 | 362,107.0 | 0.560 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-romfill | 647,150 | 2.30 | 1.00 | 360,586.3 | 0.557 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,113.2 | 0.040 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 203,180.3 | 0.314 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion | 647,150 | 1.00 | 2.71 | 127,687.3 | 0.197 | weight_read | 0.35x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion-romfill | 647,150 | 8.34 | 1.18 | 256,310.9 | 0.396 | kv_read | 0.71x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 411,276.1 | 1.274 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 386,292.7 | 1.197 | compute | 0.94x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perstream | 647,150 | 1.00 | 73.14 | 26,113.2 | 0.040 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.29 | 206,738.9 | 0.319 | weight_read | 0.50x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion | 647,150 | 1.00 | 5.29 | 250,415.1 | 0.387 | weight_read | 0.61x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion-romfill | 647,150 | 8.34 | 1.18 | 368,384.3 | 0.569 | kv_read | 0.90x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 451,162.4 | 1.398 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 421,186.4 | 1.305 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perstream | 647,150 | 1.00 | 292.57 | 26,113.2 | 0.040 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 5.15 | 216,631.0 | 0.335 | weight_read | 0.48x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion | 647,150 | 1.00 | 5.61 | 359,355.8 | 0.555 | weight_read | 0.80x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.64 | 406,603.8 | 0.628 | kv_read | 0.90x |

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
| DeepSeek-V4-Pro-0813 | 1 | 96 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 113 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 113 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 113 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 113 | 2.27 | 1.010 | 1.131 | 1.12x |
| DeepSeek-V4-Pro-0813 | 1024 | 113 | 9.06 | 1.065 | 2.072 | 1.95x |
| DeepSeek-V4-Pro-0813 | 4096 | 113 | 36.25 | 1.302 | 3.701 | 2.84x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4-Pro-0813 | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4-Pro-0813 | 1 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 95 | 11.25 | 7.96 | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | 95 | 20.87 | 11.25 | 1.85x |
| DeepSeek-V4-Pro-0813 | 8 | 95 | 36.28 | 16.11 | 2.25x |
| DeepSeek-V4-Pro-0813 | 16 | 95 | 56.57 | 21.79 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 95 | 75.98 | 27.91 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 95 | 87.80 | 33.52 | 2.62x |
| DeepSeek-V4-Pro-0813 | 256 | 95 | 93.25 | 39.02 | 2.39x |
| DeepSeek-V4-Pro-0813 | 1024 | 95 | 93.37 | 39.25 | 2.38x |
| DeepSeek-V4-Pro-0813 | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 111 | 11.34 | 8.26 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 111 | 21.22 | 11.67 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 111 | 37.44 | 16.97 | 2.21x |
| DeepSeek-V4-Pro-0813 | 16 | 111 | 59.81 | 23.14 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 111 | 82.95 | 29.94 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 111 | 98.78 | 36.26 | 2.72x |
| DeepSeek-V4-Pro-0813 | 256 | 111 | 107.35 | 42.56 | 2.52x |
| DeepSeek-V4-Pro-0813 | 1024 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4-Pro-0813 | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4-Pro-0813 | 1 | 125 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 125 | 11.40 | 8.49 | 1.34x |
| DeepSeek-V4-Pro-0813 | 4 | 125 | 21.45 | 11.99 | 1.79x |
| DeepSeek-V4-Pro-0813 | 8 | 125 | 38.23 | 17.62 | 2.17x |
| DeepSeek-V4-Pro-0813 | 16 | 125 | 62.11 | 24.16 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 125 | 88.13 | 31.52 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 125 | 107.37 | 38.43 | 2.79x |
| DeepSeek-V4-Pro-0813 | 256 | 125 | 118.96 | 45.37 | 2.62x |
| DeepSeek-V4-Pro-0813 | 1024 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4-Pro-0813 | 4096 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4-Pro-0813 | 1 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 185 | 11.56 | 9.20 | 1.26x |
| DeepSeek-V4-Pro-0813 | 4 | 185 | 22.07 | 13.14 | 1.68x |
| DeepSeek-V4-Pro-0813 | 8 | 185 | 40.40 | 19.63 | 2.06x |
| DeepSeek-V4-Pro-0813 | 16 | 185 | 68.63 | 27.52 | 2.49x |
| DeepSeek-V4-Pro-0813 | 32 | 185 | 103.84 | 36.90 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 185 | 135.66 | 45.96 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 185 | 161.05 | 55.36 | 2.91x |
| DeepSeek-V4-Pro-0813 | 1024 | 185 | 161.92 | 55.76 | 2.90x |
| DeepSeek-V4-Pro-0813 | 4096 | 185 | 161.92 | 55.76 | 2.90x |
| DeepSeek-V4-Pro-0813 | 1 | 189 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 189 | 11.57 | 9.24 | 1.25x |
| DeepSeek-V4-Pro-0813 | 4 | 189 | 22.10 | 13.21 | 1.67x |
| DeepSeek-V4-Pro-0813 | 8 | 189 | 40.50 | 19.73 | 2.05x |
| DeepSeek-V4-Pro-0813 | 16 | 189 | 68.94 | 27.71 | 2.49x |
| DeepSeek-V4-Pro-0813 | 32 | 189 | 104.62 | 37.20 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 189 | 137.16 | 46.39 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 189 | 163.45 | 55.93 | 2.92x |
| DeepSeek-V4-Pro-0813 | 1024 | 189 | 164.35 | 56.34 | 2.92x |
| DeepSeek-V4-Pro-0813 | 4096 | 189 | 164.35 | 56.34 | 2.92x |
| DeepSeek-V4-Pro-0813 | 1 | 198 | 5.92 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 198 | 11.58 | 9.32 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 198 | 22.16 | 13.36 | 1.66x |
| DeepSeek-V4-Pro-0813 | 8 | 198 | 40.71 | 19.95 | 2.04x |
| DeepSeek-V4-Pro-0813 | 16 | 198 | 69.59 | 28.12 | 2.47x |
| DeepSeek-V4-Pro-0813 | 32 | 198 | 106.29 | 37.88 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 198 | 140.40 | 47.34 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 198 | 168.67 | 57.18 | 2.95x |
| DeepSeek-V4-Pro-0813 | 1024 | 198 | 169.67 | 57.61 | 2.95x |
| DeepSeek-V4-Pro-0813 | 4096 | 198 | 169.67 | 57.61 | 2.95x |
| DeepSeek-V4-Pro-0813 | 1 | 205 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 205 | 11.59 | 9.38 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 205 | 22.20 | 13.47 | 1.65x |
| DeepSeek-V4-Pro-0813 | 8 | 205 | 40.86 | 20.11 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 205 | 70.07 | 28.44 | 2.46x |
| DeepSeek-V4-Pro-0813 | 32 | 205 | 107.52 | 38.39 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 205 | 142.78 | 48.05 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 205 | 172.59 | 58.13 | 2.97x |
| DeepSeek-V4-Pro-0813 | 1024 | 205 | 173.65 | 58.57 | 2.96x |
| DeepSeek-V4-Pro-0813 | 4096 | 205 | 173.65 | 58.57 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4-Pro-0813 | 4096 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1 | 229 | 5.93 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 229 | 11.63 | 9.56 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 229 | 22.33 | 13.83 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 229 | 41.31 | 20.59 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 229 | 71.50 | 29.47 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 229 | 111.26 | 40.03 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 229 | 150.23 | 50.33 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 229 | 185.05 | 61.21 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1024 | 229 | 186.34 | 61.68 | 3.02x |
| DeepSeek-V4-Pro-0813 | 4096 | 229 | 186.34 | 61.68 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 237 | 5.94 | 5.67 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 237 | 11.64 | 9.62 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 237 | 22.37 | 13.95 | 1.60x |
| DeepSeek-V4-Pro-0813 | 8 | 237 | 41.44 | 20.74 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 237 | 71.92 | 29.80 | 2.41x |
| DeepSeek-V4-Pro-0813 | 32 | 237 | 112.37 | 40.54 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 237 | 152.48 | 51.04 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 237 | 188.90 | 62.18 | 3.04x |
| DeepSeek-V4-Pro-0813 | 1024 | 237 | 190.27 | 62.66 | 3.04x |
| DeepSeek-V4-Pro-0813 | 4096 | 237 | 190.27 | 62.66 | 3.04x |
| DeepSeek-V4-Pro-0813 | 1 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 245 | 11.64 | 9.67 | 1.20x |
| DeepSeek-V4-Pro-0813 | 4 | 245 | 22.40 | 14.06 | 1.59x |
| DeepSeek-V4-Pro-0813 | 8 | 245 | 41.57 | 20.88 | 1.99x |
| DeepSeek-V4-Pro-0813 | 16 | 245 | 72.32 | 30.12 | 2.40x |
| DeepSeek-V4-Pro-0813 | 32 | 245 | 113.43 | 41.03 | 2.76x |
| DeepSeek-V4-Pro-0813 | 64 | 245 | 154.63 | 51.73 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 245 | 192.62 | 63.12 | 3.05x |
| DeepSeek-V4-Pro-0813 | 1024 | 245 | 194.06 | 63.62 | 3.05x |
| DeepSeek-V4-Pro-0813 | 4096 | 245 | 194.06 | 63.62 | 3.05x |
| DeepSeek-V4-Pro-0813 | 1 | 257 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 257 | 11.66 | 9.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 4 | 257 | 22.45 | 14.23 | 1.58x |
| DeepSeek-V4-Pro-0813 | 8 | 257 | 41.74 | 21.07 | 1.98x |
| DeepSeek-V4-Pro-0813 | 16 | 257 | 72.87 | 30.59 | 2.38x |
| DeepSeek-V4-Pro-0813 | 32 | 257 | 114.91 | 41.73 | 2.75x |
| DeepSeek-V4-Pro-0813 | 64 | 257 | 157.67 | 52.72 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 257 | 197.94 | 64.49 | 3.07x |
| DeepSeek-V4-Pro-0813 | 1024 | 257 | 199.49 | 65.00 | 3.07x |
| DeepSeek-V4-Pro-0813 | 4096 | 257 | 199.49 | 65.00 | 3.07x |
| DeepSeek-V4-Pro-0813 | 1 | 274 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 274 | 11.67 | 9.84 | 1.19x |
| DeepSeek-V4-Pro-0813 | 4 | 274 | 22.51 | 14.45 | 1.56x |
| DeepSeek-V4-Pro-0813 | 8 | 274 | 41.96 | 21.33 | 1.97x |
| DeepSeek-V4-Pro-0813 | 16 | 274 | 73.58 | 31.22 | 2.36x |
| DeepSeek-V4-Pro-0813 | 32 | 274 | 116.83 | 42.67 | 2.74x |
| DeepSeek-V4-Pro-0813 | 64 | 274 | 161.66 | 54.04 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 274 | 205.01 | 66.32 | 3.09x |
| DeepSeek-V4-Pro-0813 | 1024 | 274 | 206.70 | 66.86 | 3.09x |
| DeepSeek-V4-Pro-0813 | 4096 | 274 | 206.70 | 66.86 | 3.09x |
| DeepSeek-V4-Pro-0813 | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 280 | 11.68 | 9.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 280 | 22.53 | 14.53 | 1.55x |
| DeepSeek-V4-Pro-0813 | 8 | 280 | 42.03 | 21.42 | 1.96x |
| DeepSeek-V4-Pro-0813 | 16 | 280 | 73.81 | 31.44 | 2.35x |
| DeepSeek-V4-Pro-0813 | 32 | 280 | 117.46 | 42.98 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 280 | 162.98 | 54.48 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 280 | 207.38 | 66.94 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1024 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4-Pro-0813 | 4096 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1 | 292 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 292 | 11.69 | 9.94 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 292 | 22.56 | 14.68 | 1.54x |
| DeepSeek-V4-Pro-0813 | 8 | 292 | 42.16 | 21.59 | 1.95x |
| DeepSeek-V4-Pro-0813 | 16 | 292 | 74.25 | 31.86 | 2.33x |
| DeepSeek-V4-Pro-0813 | 32 | 292 | 118.66 | 43.58 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 292 | 165.50 | 55.35 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 292 | 211.94 | 68.16 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1024 | 292 | 213.79 | 68.72 | 3.11x |
| DeepSeek-V4-Pro-0813 | 4096 | 292 | 213.79 | 68.72 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 293 | 11.69 | 9.94 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 293 | 22.57 | 14.69 | 1.54x |
| DeepSeek-V4-Pro-0813 | 8 | 293 | 42.17 | 21.60 | 1.95x |
| DeepSeek-V4-Pro-0813 | 16 | 293 | 74.29 | 31.89 | 2.33x |
| DeepSeek-V4-Pro-0813 | 32 | 293 | 118.75 | 43.62 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 293 | 165.70 | 55.42 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 293 | 212.31 | 68.26 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1024 | 293 | 214.17 | 68.82 | 3.11x |
| DeepSeek-V4-Pro-0813 | 4096 | 293 | 214.17 | 68.82 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1 | 320 | 5.95 | 5.75 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 320 | 11.71 | 10.07 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 320 | 22.64 | 15.00 | 1.51x |
| DeepSeek-V4-Pro-0813 | 8 | 320 | 42.44 | 21.95 | 1.93x |
| DeepSeek-V4-Pro-0813 | 16 | 320 | 75.16 | 32.78 | 2.29x |
| DeepSeek-V4-Pro-0813 | 32 | 320 | 121.15 | 44.85 | 2.70x |
| DeepSeek-V4-Pro-0813 | 64 | 320 | 170.83 | 57.26 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 320 | 221.72 | 70.84 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1024 | 320 | 223.80 | 71.44 | 3.13x |
| DeepSeek-V4-Pro-0813 | 4096 | 320 | 223.80 | 71.44 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1 | 321 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 321 | 11.71 | 10.07 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 321 | 22.64 | 15.02 | 1.51x |
| DeepSeek-V4-Pro-0813 | 8 | 321 | 42.45 | 21.96 | 1.93x |
| DeepSeek-V4-Pro-0813 | 16 | 321 | 75.19 | 32.81 | 2.29x |
| DeepSeek-V4-Pro-0813 | 32 | 321 | 121.23 | 44.90 | 2.70x |
| DeepSeek-V4-Pro-0813 | 64 | 321 | 171.00 | 57.33 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 321 | 222.05 | 70.94 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1024 | 321 | 224.14 | 71.53 | 3.13x |
| DeepSeek-V4-Pro-0813 | 4096 | 321 | 224.14 | 71.53 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 324 | 11.71 | 10.09 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 324 | 22.65 | 15.05 | 1.50x |
| DeepSeek-V4-Pro-0813 | 8 | 324 | 42.47 | 22.00 | 1.93x |
| DeepSeek-V4-Pro-0813 | 16 | 324 | 75.27 | 32.91 | 2.29x |
| DeepSeek-V4-Pro-0813 | 32 | 324 | 121.48 | 45.03 | 2.70x |
| DeepSeek-V4-Pro-0813 | 64 | 324 | 171.53 | 57.52 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 324 | 223.03 | 71.21 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1024 | 324 | 225.14 | 71.81 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 324 | 225.14 | 71.81 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 335 | 11.71 | 10.13 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 335 | 22.67 | 15.17 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 335 | 42.57 | 22.14 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 335 | 75.58 | 33.24 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 335 | 122.34 | 45.48 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 335 | 173.40 | 58.23 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 335 | 226.52 | 72.22 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 336 | 11.71 | 10.14 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 336 | 22.68 | 15.18 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 336 | 42.57 | 22.15 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 336 | 75.61 | 33.27 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 336 | 122.42 | 45.52 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 336 | 173.56 | 58.30 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 336 | 226.83 | 72.31 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 344 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 344 | 11.72 | 10.17 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 344 | 22.69 | 15.27 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 344 | 42.64 | 22.24 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 344 | 75.82 | 33.51 | 2.26x |
| DeepSeek-V4-Pro-0813 | 32 | 344 | 123.01 | 45.84 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 344 | 174.85 | 58.81 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 344 | 229.27 | 73.02 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 344 | 231.52 | 73.63 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 344 | 231.52 | 73.63 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 355 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 355 | 11.73 | 10.21 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 355 | 22.72 | 15.38 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 355 | 42.72 | 22.37 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 355 | 76.10 | 33.82 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 355 | 123.79 | 46.27 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 355 | 176.56 | 59.49 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 355 | 232.50 | 73.98 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 355 | 234.83 | 74.61 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 355 | 234.83 | 74.61 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 356 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 356 | 11.73 | 10.21 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 356 | 22.72 | 15.39 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 356 | 42.73 | 22.38 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 356 | 76.13 | 33.85 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 356 | 123.86 | 46.31 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 356 | 176.71 | 59.56 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 356 | 232.79 | 74.07 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 356 | 235.12 | 74.69 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 356 | 235.12 | 74.69 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 365 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 365 | 11.73 | 10.25 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 365 | 22.74 | 15.49 | 1.47x |
| DeepSeek-V4-Pro-0813 | 8 | 365 | 42.79 | 22.48 | 1.90x |
| DeepSeek-V4-Pro-0813 | 16 | 365 | 76.34 | 34.09 | 2.24x |
| DeepSeek-V4-Pro-0813 | 32 | 365 | 124.47 | 46.65 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 365 | 178.04 | 60.11 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 365 | 235.32 | 74.84 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 365 | 237.72 | 75.47 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 365 | 237.72 | 75.47 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 383 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 383 | 11.74 | 10.31 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 383 | 22.77 | 15.66 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 383 | 42.91 | 22.68 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 383 | 76.74 | 34.56 | 2.22x |
| DeepSeek-V4-Pro-0813 | 32 | 383 | 125.60 | 47.30 | 2.66x |
| DeepSeek-V4-Pro-0813 | 64 | 383 | 180.54 | 61.19 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 383 | 240.13 | 76.33 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 383 | 242.65 | 76.99 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 383 | 242.65 | 76.99 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 384 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 384 | 11.74 | 10.31 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 384 | 22.77 | 15.67 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 384 | 42.92 | 22.69 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 384 | 76.76 | 34.59 | 2.22x |
| DeepSeek-V4-Pro-0813 | 32 | 384 | 125.66 | 47.33 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 384 | 180.68 | 61.24 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 384 | 240.39 | 76.42 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 384 | 242.92 | 77.07 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 384 | 242.92 | 77.07 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 391 | 11.74 | 10.33 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 391 | 22.78 | 15.74 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 391 | 42.96 | 22.76 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 391 | 76.91 | 34.76 | 2.21x |
| DeepSeek-V4-Pro-0813 | 32 | 391 | 126.08 | 47.58 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 391 | 181.60 | 61.65 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 391 | 242.17 | 76.98 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 391 | 244.74 | 77.64 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 391 | 244.74 | 77.64 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 448 | 11.76 | 10.50 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 448 | 22.87 | 16.25 | 1.41x |
| DeepSeek-V4-Pro-0813 | 8 | 448 | 43.27 | 23.34 | 1.85x |
| DeepSeek-V4-Pro-0813 | 16 | 448 | 77.94 | 36.03 | 2.16x |
| DeepSeek-V4-Pro-0813 | 32 | 448 | 129.03 | 49.47 | 2.61x |
| DeepSeek-V4-Pro-0813 | 64 | 448 | 188.21 | 64.80 | 2.90x |
| DeepSeek-V4-Pro-0813 | 256 | 448 | 255.15 | 81.21 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 672 | 11.81 | 10.91 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 672 | 23.06 | 17.73 | 1.30x |
| DeepSeek-V4-Pro-0813 | 8 | 672 | 43.98 | 25.33 | 1.74x |
| DeepSeek-V4-Pro-0813 | 16 | 672 | 80.37 | 39.17 | 2.05x |
| DeepSeek-V4-Pro-0813 | 32 | 672 | 136.13 | 55.89 | 2.44x |
| DeepSeek-V4-Pro-0813 | 64 | 672 | 204.63 | 73.69 | 2.78x |
| DeepSeek-V4-Pro-0813 | 256 | 672 | 288.80 | 93.78 | 3.08x |
| DeepSeek-V4-Pro-0813 | 1024 | 672 | 292.67 | 94.67 | 3.09x |
| DeepSeek-V4-Pro-0813 | 4096 | 672 | 292.67 | 94.67 | 3.09x |
| DeepSeek-V4-Pro-0813 | 1 | 783 | 5.98 | 5.90 | 1.01x |
| DeepSeek-V4-Pro-0813 | 2 | 783 | 11.82 | 11.03 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 783 | 23.11 | 18.26 | 1.27x |
| DeepSeek-V4-Pro-0813 | 8 | 783 | 44.19 | 26.20 | 1.69x |
| DeepSeek-V4-Pro-0813 | 16 | 783 | 81.07 | 40.13 | 2.02x |
| DeepSeek-V4-Pro-0813 | 32 | 783 | 138.24 | 58.57 | 2.36x |
| DeepSeek-V4-Pro-0813 | 64 | 783 | 209.64 | 76.70 | 2.73x |
| DeepSeek-V4-Pro-0813 | 256 | 783 | 299.47 | 99.03 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1024 | 783 | 303.67 | 99.95 | 3.04x |
| DeepSeek-V4-Pro-0813 | 4096 | 783 | 303.67 | 99.95 | 3.04x |

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
| gpu | DeepSeek-V4-Pro-0813 | 1 | 572.70 | 11.2% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 366.11 | 76.4% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4-Pro-0813 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Pro-0813 | hbm | interleaved | 32 B | 1.00x |

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
| DeepSeek-V4-Pro-0813 | 1 | 96 | 58.43% | 124.46 | 2.22 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 6.43% | 16.27 | 2.22 |
| DeepSeek-V4-Pro-0813 | 4 | 2 | 6.43% | 16.27 | 2.22 |
| DeepSeek-V4-Pro-0813 | 8 | 2 | 6.43% | 16.27 | 2.22 |

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
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 37.1 | 7,450.5 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 37.1 | 7,450.5 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 37.1 | 7,450.5 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 37.1 | 7,450.5 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 37.1 | 7,450.5 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 37.1 | 7,450.5 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 37.1 | 7,450.5 |
| DeepSeek-V4-Pro-0813 | 256 | 1.99% | 43.1 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 29.1 | 7,460.4 |
| DeepSeek-V4-Pro-0813 | 1024 | 7.71% | 90.2 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 7.3 | 7,478.6 |
| DeepSeek-V4-Pro-0813 | 4096 | 27.45% | 252.5 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 1.8 | 7,476.2 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 21 |
| gpu | link_latency | 585 |
| gpu | weight_read | 794 |
| rom | compute | 622 |
| rom | infeasible | 1764 |
| rom | kv_read | 44 |
| rom | layer_fixed_latency | 207 |
| rom | link_latency | 964 |
| rom | weight_read | 239 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 21 |
| rom | CAPACITY | 1764 |

## Mechanical consistency audit

**FAIL** over 108,365 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x188', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x192', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x232', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x240', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x278', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x296', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x324', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x325', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x370', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x188', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x192', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x232', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x240', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x278', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x296', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x324', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x325', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x370', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x188', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x192', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x232', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x240', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x278', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x296', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x324', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x325', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x370', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x188', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x192', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x232', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x240', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x278', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x296', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x324', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x325', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x370', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x5', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x188', 'DeepSeek-V4-Pro-0813', 1)

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

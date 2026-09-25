# Area-constrained roofline: n5_vs_b200-deepseek-v41-flash-8k

> CANDIDATE MODEL under n5_vs_b200: DeepSeek-V4.1-Flash at 8,192 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 52x (ROM-N5-native-SRAMKV-wafer-pipeline-x12-romfill, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 1 device. On the GPU side the correction reaches 3x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 21 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash takes 97 x 815 mm2 (79,055 mm2, array, KV in HBM) at 3,820 tok/s per user and 48 tok/s per 1,000 mm2, holding 982,691 sessions, against 49 copies of one unified HBM die at the same silicon: 5.4x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash on 138,675 mm2 of ROM silicon at 4,373 tok/s per user against 139,200 mm2 of b200_sxm-x87-nvl72-hybrid at 697 tok/s: **6.3x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 261,375 resident sessions against the GPU cluster's 1,359,154. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 1.90x to it.** At 107,580 mm2 on DeepSeek-V4.1-Flash the pipeline-only GPU delivers 371.09 tok/s and the same silicon running tensor delivers 706 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4.1-Flash, ROM binding on `link_latency`) to 5.06x (DeepSeek-V4.1-Flash, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 554 to 54,360 tok/s, and its rate with every slot occupied from 51,492 to 54,360. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 93 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 567 us over NVLink, capping per-user decode at 1,763 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 171.8 us and cap it at 5,821 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 8 of 10 operating points and an array 2; on tokens per second per square millimetre the same points go 3 to the array and 7 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 60 of 4990 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 103.9x of aggregate throughput (DeepSeek-V4.1-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 13.72x, on DeepSeek-V4.1-Flash at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 65 of 4,990 feasible points (1.3%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DeepSeek-V4.1-Flash/b200_sxm-x4-pipeline` at batch 4096 on 6,400 mm2, throttled 1.12x from 21 to 19 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 89% weight read against 89.3% weight read. The ROM sweep is not what melts it.


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

### DeepSeek-V4.1-Flash at 8,192 tokens

**Recommended: `ROM-N5-native-HBMKV-array-hw-hybrid-x97`** -- 97 x 815 mm2 reticle dies, 79,055 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **3,819.7 tok/s per user** (0.26 ms/token), binding on `layer_fixed_latency`
- **48.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 26,738 tok/s aggregate with every slot full, over 982,691 resident sessions (fill limited by `pipeline_slots`)
- 6,190 W at 0.078 W/mm2, 1,575.8 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 49 copies of one unified HBM die -- `b200_sxm-x49-nvl72-tensor`, 78,400 mm2, area ratio 1.0084 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 79,055 | 78,400 | 1.0084 |
| user tok/s | 3,819.7 | 701.5 | 5.45x |
| aggregate tok/s | 26,738 | 701 | 1.47x |
| resident sessions | 982,691 | 743,199 | -- |
| J/token | 1.5758 | 25.8536 | 16.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 982,691 sessions against one that holds 743,199 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x67-nvl72-tensor` at 107,200 mm2 and 706.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | 47.3 | 174,250 | 6.21x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | 47.3 | 174,250 | 6.21x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-hybrid-x85` | 69,275 | 2,968.1 | 42.8 | 1 | 4.25x |
| **after -- this report's rule** | `ROM-N5-native-HBMKV-array-hw-hybrid-x97` | 79,055 | 3,819.7 | 48.3 | 982,691 | 5.45x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x97` | 79,055 | 3,819.7 | 48.3 | -- | 48.3 | ACCEPT |
| `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | 47.3 | 41.5 | 48.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x97` **<-- recommended** | 79,055 | 97 | 3,819.7 | 26,738 | 48.3 | 982,691 | `layer_fixed_latency` | 6,190 | 1,575.8 | `b200_sxm-x49-nvl72-tensor` | 5.45x |
| `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 2 | 4,375.3 | 8,751 | 47.3 | 174,250 | `layer_fixed_latency` | 6,881 | 1,565.2 | `b200_sxm-x58-nvl72-tensor` | 6.21x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 330 | densest | `ROM-N5-native-HBMKV-array-hw-hybrid-x97` | 79,055 | 3,819.7 | 48.3 | 982,691 |
| array | 330 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 4,204.5 | 29.3 | 1,783,027 |
| array | 330 | smallest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x85` | 69,275 | 2,968.1 | 42.8 | 1 |
| wafer | 72 | densest | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | 47.3 | 174,250 |
| wafer | 72 | fastest | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | 47.3 | 174,250 |
| wafer | 72 | smallest | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | 47.3 | 174,250 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 4,204.5 | 92,499 | 1,783,027 | 17,124 | 3,915.7 | `layer_fixed_latency` | `b200_sxm-x90-nvl72-hybrid` | 697.2 | 1,407,782 | 46,613.3 | 0.996 | 6.03x | 11.9x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | 8,751 | 174,250 | 6,881 | 1,565.2 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 704.1 | 889,083 | 30,242.1 | 0.996 | 6.21x | 19.3x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 4,142.2 | 28,995 | 1,134,653 | 8,190 | 1,932.3 | `layer_fixed_latency` | `b200_sxm-x57-nvl72-tensor` | 703.8 | 872,874 | 29,754.4 | 1.001 | 5.89x | 15.4x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | -- | 174,250 | -- | 1,565.2 | -- | -- | -- | -- | -- | 0.987 | 1.06x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 4,204.5 | 92,499 | 1,783,027 | 17,124 | 1,961.6 | `layer_fixed_latency` | `b200_sxm-x90-nvl72-hybrid` | 697.2 | 1,407,782 | 23,993.5 | 0.996 | 6.03x | 12.2x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | 8,751 | 174,250 | 6,881 | 786.3 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 695.0 | 889,083 | 15,545.4 | 0.996 | 6.30x | 19.8x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 4,142.2 | 28,995 | 1,134,653 | 8,190 | 969.9 | `layer_fixed_latency` | `b200_sxm-x57-nvl72-tensor` | 694.7 | 872,874 | 15,299.8 | 1.001 | 5.96x | 15.8x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,375.3 | -- | 174,250 | -- | 786.3 | -- | -- | -- | -- | -- | 0.987 | 1.06x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 4,204.5 | 92,499 | 1,783,027 | 17,124 | 984.5 | `layer_fixed_latency` | `b200_sxm-x90-nvl72-hybrid` | 686.3 | 1,407,782 | 12,411.5 | 0.996 | 6.13x | 12.6x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 4,372.8 | 26,237 | 261,375 | 13,835 | 787.2 | `layer_fixed_latency` | `b200_sxm-x87-nvl72-hybrid` | 685.4 | 1,359,154 | 12,042.5 | 0.996 | 6.38x | 15.3x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 4,204.5 | 92,499 | 1,783,027 | 17,124 | 984.5 | `layer_fixed_latency` | `b200_sxm-x90-nvl72-hybrid` | 686.3 | 1,407,782 | 12,411.5 | 0.996 | 6.13x | 12.6x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 4,372.8 | -- | 261,375 | -- | 787.2 | -- | -- | -- | -- | -- | 1.034 | 1.04x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 4,204.5 | 92,499 | 1,783,027 | 17,124 | 496.0 | `layer_fixed_latency` | `b200_sxm-x90-nvl72-hybrid` | 666.1 | 1,407,782 | 6,726.8 | 0.996 | 6.31x | 13.6x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,365.7 | 34,926 | 348,500 | 20,723 | 593.3 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 673.8 | 1,829,225 | 8,232.4 | 0.996 | 6.48x | 13.9x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 4,184.8 | 62,772 | 2,299,699 | 23,642 | 699.7 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 673.8 | 1,829,225 | 8,232.4 | 0.997 | 6.21x | 11.8x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,365.7 | -- | 348,500 | -- | 593.3 | -- | -- | -- | -- | -- | 1.001 | 1.04x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 4,204.5 | 92,499 | 1,783,027 | 17,124 | 251.7 | `layer_fixed_latency` | `b200_sxm-x90-nvl72-hybrid` | 634.9 | 1,407,782 | 3,734.7 | 0.996 | 6.62x | 14.8x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,332.1 | 95,305 | 522,751 | 25,312 | 362.4 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 661.3 | 2,753,157 | 6,537.7 | 1.002 | 6.55x | 18.0x |
| 16 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 286,880 | 4,171.8 | 91,780 | 3,566,054 | 40,381 | 602.2 | `layer_fixed_latency` | `b200_sxm-x179-nvl72-hybrid` | 662.7 | 2,850,413 | 6,723.6 | 1.002 | 6.30x | 11.2x |
| 16 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,332.1 | -- | 522,751 | -- | 362.4 | -- | -- | -- | -- | -- | 1.034 | 1.04x wafer/array | -- |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 4,158.1 | 182,955 | 1,783,027 | 17,800 | 131.0 | `layer_fixed_latency` | `b200_sxm-x90-nvl72-hybrid` | 590.7 | 1,407,782 | 2,476.1 | 0.996 | 7.04x | 18.9x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,305.6 | 185,141 | 1,045,502 | 50,583 | 364.6 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 654.6 | 5,573,581 | 6,584.0 | 0.999 | 6.58x | 18.1x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 215,160 | 4,137.8 | 273,097 | 2,674,540 | 25,074 | 94.4 | `layer_fixed_latency` | `b200_sxm-x134-nvl72-hybrid` | 564.4 | 2,120,993 | 2,005.7 | 1.004 | 7.33x | 21.2x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,299.5 | 369,753 | 1,045,502 | 51,962 | 186.3 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 619.1 | 5,573,581 | 4,161.0 | 0.999 | 6.94x | 22.3x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x352-romfill` | 286,880 | 3,402.3 | 871,001 | 3,566,054 | 36,497 | 41.9 | `layer_fixed_latency` | `b200_sxm-x179-nvl72-hybrid` | 420.8 | 2,850,413 | 1,104.9 | 1.002 | 8.09x | 26.4x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,131.4 | 1,057,633 | 1,045,502 | 56,170 | 53.1 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 502.8 | 5,573,581 | 1,559.2 | 0.999 | 8.22x | 29.4x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 1,713.1 | 1,754,221 | 3,444,484 | 47,261 | 26.9 | `weight_read` | `b200_sxm-x173-nvl72-hybrid` | 235.8 | 2,753,157 | 515.1 | 1.001 | 7.26x | 19.1x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 2,431.0 | 2,489,395 | 1,045,502 | 65,589 | 26.3 | `compute` | `b200_sxm-x347-nvl72-hybrid` | 304.7 | 5,573,581 | 832.1 | 0.999 | 7.98x | 31.6x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 277,100 | 620.7 | 2,542,202 | 3,444,484 | 50,660 | 19.9 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 133.8 | 2,753,157 | 197.9 | 1.001 | 4.64x | 9.9x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 767.9 | 3,145,239 | 1,045,502 | 65,611 | 20.9 | `compute` | `b200_sxm-x347-nvl72-hybrid` | 161.9 | 5,573,581 | 346.2 | 0.999 | 4.74x | 16.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-4 | `ROM-N5-native-HBMKV-array-hw-hybrid-x97` | 79,055 | array | HBM | 982,691 |
| 8-64 | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | wafer | HBM | 174,250 |
| 256 | `ROM-N5-native-HBMKV-wafer-pipeline-x3` | 138,675 | wafer | HBM | 261,375 |
| 1024 | `ROM-N5-native-HBMKV-wafer-pipeline-x4` | 184,900 | wafer | HBM | 348,500 |
| 4096 | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 277,350 | wafer | HBM | 522,751 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash | HBM | rom | 93, 97, 107, 110, 112, 113, 132, 148, 149, 170, 176, 227, 264, 340, 352 |
| DeepSeek-V4.1-Flash | HBM | sram | 93, 97, 107, 110, 112, 113, 132, 170, 174, 176, 227, 264, 340, 352 |
| DeepSeek-V4.1-Flash | SRAM | rom | 85, 86, 87, 89, 103, 113, 123, 164, 170, 227, 246, 328, 340 |
| DeepSeek-V4.1-Flash | SRAM | sram | 85, 86, 87, 89, 103, 113, 123, 164, 170, 227, 246, 328, 340 |

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
| DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x97` | 1 | 16 | 6.25 | hierarchical, one_shot | 203.58 | 26.42 | 71.60 | 31.37 | 3,819.7 |
| DeepSeek-V4.1-Flash | `ROM-N5-native-HBMKV-array-hw-hybrid-x97` | 64 | 2 | 5.25 | one_shot, two_step | 155.97 | 7.23 | 654.65 | 14.36 | 1,284.6 |
| DeepSeek-V4.1-Flash | `b200_sxm-x49-nvl72-tensor` | 1 | 49 | 6.25 | measured_floor | 860.60 | 528.54 | 41.10 | 204.73 | 701.5 |
| DeepSeek-V4.1-Flash | `b200_sxm-x49-nvl72-tensor` | 64 | 49 | 6.25 | measured_floor | 852.80 | 1,030.31 | 607.08 | 373.25 | 413.6 |

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

- **65 of 4,990 feasible points (1.3%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 65.
- By area class: large array (5,000-40,000 mm2) 14, wafer (>=40,000 mm2) 51.
- By KV store: hbm 65.
- By batch: B=32 1, B=64 1, B=256 5, B=1024 25, B=4096 33.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 34% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 32 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 230 | 14 | 50.0% | 100.0% | 0.625 | 71% |
| gpu | wafer (>=40,000 mm2) | 1,880 | 51 | 38.8% | 100.0% | 0.625 | 90% |
| rom | large array (5,000-40,000 mm2) | 336 | 0 | 18.3% | 25.1% | 0.126 | 96% |
| rom | wafer (>=40,000 mm2) | 2,544 | 0 | 20.4% | 36.6% | 0.183 | 97% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DeepSeek-V4.1-Flash/b200_sxm-x4-pipeline` | DeepSeek-V4.1-Flash | 4096 | 6,400 | hbm | 1.120x | 4,000.0 / 4,000.0 W | 35% | 18.6 | 20.8 |
| `DeepSeek-V4.1-Flash/b200_sxm-x4-pipeline` | DeepSeek-V4.1-Flash | 1024 | 6,400 | hbm | 1.067x | 4,000.0 / 4,000.0 W | 35% | 20.5 | 21.9 |
| `DeepSeek-V4.1-Flash/b200_sxm-x21-pipeline` | DeepSeek-V4.1-Flash | 4096 | 33,600 | hbm | 1.063x | 21,000.0 / 21,000.0 W | 35% | 21.3 | 22.6 |
| `DeepSeek-V4.1-Flash/b200_sxm-x23-pipeline` | DeepSeek-V4.1-Flash | 4096 | 36,800 | hbm | 1.062x | 23,000.0 / 23,000.0 W | 35% | 21.6 | 23.0 |
| `DeepSeek-V4.1-Flash/b200_sxm-x24-pipeline` | DeepSeek-V4.1-Flash | 4096 | 38,400 | hbm | 1.062x | 24,000.0 / 24,000.0 W | 35% | 21.8 | 23.1 |
| `DeepSeek-V4.1-Flash/b200_sxm-x28-pipeline` | DeepSeek-V4.1-Flash | 4096 | 44,800 | hbm | 1.060x | 28,000.0 / 28,000.0 W | 35% | 22.6 | 24.0 |
| `DeepSeek-V4.1-Flash/b200_sxm-x29-pipeline` | DeepSeek-V4.1-Flash | 4096 | 46,400 | hbm | 1.060x | 29,000.0 / 29,000.0 W | 35% | 22.8 | 24.2 |
| `DeepSeek-V4.1-Flash/b200_sxm-x30-pipeline` | DeepSeek-V4.1-Flash | 4096 | 48,000 | hbm | 1.060x | 30,000.0 / 30,000.0 W | 35% | 23.0 | 24.4 |
| `DeepSeek-V4.1-Flash/b200_sxm-x43-pipeline` | DeepSeek-V4.1-Flash | 4096 | 68,800 | hbm | 1.057x | 43,000.0 / 43,000.0 W | 35% | 26.2 | 27.7 |
| `DeepSeek-V4.1-Flash/b200_sxm-x44-pipeline` | DeepSeek-V4.1-Flash | 4096 | 70,400 | hbm | 1.057x | 44,000.0 / 44,000.0 W | 35% | 26.4 | 27.9 |
| `DeepSeek-V4.1-Flash/b200_sxm-x45-pipeline` | DeepSeek-V4.1-Flash | 4096 | 72,000 | hbm | 1.057x | 45,000.0 / 45,000.0 W | 35% | 26.7 | 28.2 |
| `DeepSeek-V4.1-Flash/b200_sxm-x47-pipeline` | DeepSeek-V4.1-Flash | 4096 | 75,200 | hbm | 1.057x | 47,000.0 / 47,000.0 W | 35% | 27.2 | 28.8 |

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
| DeepSeek-V4.1-Flash | 1 | 92,450 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 1.565205 | 6,881.0 | layer_fixed_latency | `DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-tensor` | 30.242054 | 21,292.7 | layer_fixed_latency | 19.32x |
| DeepSeek-V4.1-Flash | 2 | 92,450 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 0.786340 | 6,881.0 | layer_fixed_latency | `DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-tensor` | 15.545412 | 21,607.1 | layer_fixed_latency | 19.77x |
| DeepSeek-V4.1-Flash | 4 | 92,450 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 0.397239 | 6,946.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-tensor` | 8.189164 | 22,198.1 | layer_fixed_latency | 20.62x |
| DeepSeek-V4.1-Flash | 8 | 92,450 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 0.203835 | 7,075.0 | layer_fixed_latency | `DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-tensor` | 4.495755 | 23,245.3 | layer_fixed_latency | 22.06x |
| DeepSeek-V4.1-Flash | 16 | 92,450 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 0.107510 | 7,312.7 | layer_fixed_latency | `DeepSeek-V4.1-Flash/b200_sxm-x58-hybrid` | 3.025563 | 29,235.3 | layer_fixed_latency | 24.38x |
| DeepSeek-V4.1-Flash | 32 | 120,620 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x148-romfill` | 0.103498 | 13,877.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash/b200_sxm-x75-nvl72-hybrid` | 2.175650 | 40,101.6 | layer_fixed_latency | 21.02x |
| DeepSeek-V4.1-Flash | 64 | 138,550 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 0.067293 | 18,234.7 | layer_fixed_latency | `DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid` | 1.532020 | 50,898.0 | layer_fixed_latency | 22.77x |
| DeepSeek-V4.1-Flash | 256 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.053110 | 56,170.5 | layer_fixed_latency | `DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-hybrid` | 1.559153 | 200,669.4 | layer_fixed_latency | 29.36x |
| DeepSeek-V4.1-Flash | 1024 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.026347 | 65,589.1 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-hybrid` | 0.832055 | 259,590.0 | weight_read | 31.58x |
| DeepSeek-V4.1-Flash | 4096 | 369,800 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8` | 0.020425 | 61,572.1 | weight_read | `DeepSeek-V4.1-Flash/b200_sxm-x231-nvl72-hybrid` | 0.252149 | 150,493.2 | link_latency | 12.35x |

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
| DeepSeek-V4.1-Flash | 8,192 | 552 B | 510.3 GB | 7.40 | 0.012 GB | 0.010 GB | 1,092.9 |

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
| DeepSeek-V4.1-Flash | 2 | 92,450 | 4,458.8 | wafer-pipeline | 4,375.3 | wafer-hybrid | 1.02x | 1,065.3 | pipeline | 704.1 | tensor | 1.51x | 4.19x | 6.21x | 1.48x |
| DeepSeek-V4.1-Flash | 3 | 138,675 | 4,457.1 | wafer-pipeline | 4,373.3 | wafer-hybrid | 1.02x | 1,077.1 | pipeline | 696.5 | hybrid | 1.55x | 4.14x | 6.28x | 1.52x |
| DeepSeek-V4.1-Flash | 4 | 184,900 | 4,457.3 | wafer-pipeline | 4,369.8 | wafer-hybrid | 1.02x | 1,083.1 | pipeline | 701.5 | hybrid | 1.54x | 4.12x | 6.23x | 1.51x |
| DeepSeek-V4.1-Flash | 6 | 277,350 | 4,457.5 | wafer-pipeline | 4,364.4 | wafer-hybrid | 1.02x | 1,089.1 | pipeline | 700.0 | hybrid | 1.56x | 4.09x | 6.24x | 1.52x |
| DeepSeek-V4.1-Flash | 8 | 369,800 | 4,457.6 | wafer-pipeline | 4,359.4 | wafer-hybrid | 1.02x | 1,092.2 | pipeline | 698.6 | hybrid | 1.56x | 4.08x | 6.24x | 1.53x |
| DeepSeek-V4.1-Flash | 12 | 554,700 | 4,457.7 | wafer-pipeline | 4,349.5 | wafer-hybrid | 1.02x | 1,095.3 | pipeline | 699.5 | hybrid | 1.57x | 4.07x | 6.22x | 1.53x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.48x to 1.53x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash | 1 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,375.3 | 8,750.7 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-tensor | 92,800 | 1.00x | tensor | 528.89 | 704.1 | 704.1 | layer_fixed_latency | 6.21x | 0.41x | 11.79x | 6.21x |
| DeepSeek-V4.1-Flash | 1 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x85 | 69,275 | 2,968.1 | 2,968.1 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x43-nvl72-tensor | 68,800 | 1.01x | tensor | 528.30 | 699.1 | 699.1 | layer_fixed_latency | 4.25x | 0.19x | 8.00x | 4.25x |
| DeepSeek-V4.1-Flash | 2 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,375.3 | 8,750.7 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-tensor | 92,800 | 1.00x | tensor | 536.98 | 695.0 | 1,389.9 | layer_fixed_latency | 6.30x | 0.41x | 11.79x | 6.30x |
| DeepSeek-V4.1-Flash | 2 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x93 | 75,795 | 3,363.9 | 10,091.6 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x47-nvl72-tensor | 75,200 | 1.01x | tensor | 536.10 | 690.7 | 1,381.5 | layer_fixed_latency | 4.87x | 0.58x | 9.06x | 4.87x |
| DeepSeek-V4.1-Flash | 4 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 4,372.8 | 26,236.7 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid | 139,200 | 1.00x | hybrid | 543.27 | 685.4 | 2,741.6 | layer_fixed_latency | 6.38x | 0.81x | 11.78x | 6.38x |
| DeepSeek-V4.1-Flash | 4 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x93 | 75,795 | 3,246.4 | 19,478.3 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x47-nvl72-tensor | 75,200 | 1.01x | tensor | 551.41 | 671.9 | 2,687.5 | layer_fixed_latency | 4.83x | 1.12x | 8.75x | 4.83x |
| DeepSeek-V4.1-Flash | 8 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 4,365.7 | 34,926.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x116-nvl72-hybrid | 185,600 | 1.00x | hybrid | 561.68 | 673.8 | 5,390.2 | layer_fixed_latency | 6.48x | 0.81x | 11.76x | 6.48x |
| DeepSeek-V4.1-Flash | 8 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x93 | 75,795 | 2,800.1 | 22,401.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x47-hybrid | 75,200 | 1.01x | hybrid | 450.21 | 639.0 | 5,111.7 | layer_fixed_latency | 4.38x | 1.28x | 7.55x | 4.38x |
| DeepSeek-V4.1-Flash | 16 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 4,332.1 | 95,305.2 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 554.56 | 661.3 | 10,580.5 | layer_fixed_latency | 6.55x | 1.48x | 11.67x | 6.55x |
| DeepSeek-V4.1-Flash | 16 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x93 | 75,795 | 2,125.0 | 33,999.9 | compute | DeepSeek-V4.1-Flash/b200_sxm-x47-hybrid | 75,200 | 1.01x | hybrid | 463.44 | 594.8 | 9,516.3 | layer_fixed_latency | 3.57x | 1.95x | 5.73x | 3.57x |
| DeepSeek-V4.1-Flash | 32 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,305.6 | 185,141.4 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 573.74 | 654.6 | 20,947.1 | layer_fixed_latency | 6.58x | 1.44x | 11.60x | 6.58x |
| DeepSeek-V4.1-Flash | 32 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x93 | 75,795 | 1,352.9 | 43,293.5 | compute | DeepSeek-V4.1-Flash/b200_sxm-x47-hybrid | 75,200 | 1.01x | hybrid | 489.90 | 524.2 | 16,775.4 | layer_fixed_latency | 2.58x | 2.48x | 3.65x | 2.58x |
| DeepSeek-V4.1-Flash | 64 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,299.5 | 369,753.1 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 492.70 | 619.1 | 39,623.3 | layer_fixed_latency | 6.94x | 2.87x | 11.59x | 6.97x |
| DeepSeek-V4.1-Flash | 64 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x93 | 75,795 | 762.7 | 48,809.6 | compute | DeepSeek-V4.1-Flash/b200_sxm-x47-hybrid | 75,200 | 1.01x | hybrid | 542.82 | 428.1 | 27,399.8 | weight_read | 1.78x | 1.78x | 2.23x | 1.78x |
| DeepSeek-V4.1-Flash | 256 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,131.4 | 1,057,633.3 | layer_fixed_latency | DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 539.95 | 502.8 | 128,704.2 | layer_fixed_latency | 8.22x | 8.21x | 11.13x | 8.24x |
| DeepSeek-V4.1-Flash | 256 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x93 | 75,795 | 209.1 | 53,525.2 | compute | DeepSeek-V4.1-Flash/b200_sxm-x47-nvl72-tensor | 75,200 | 1.01x | tensor | 2,522.25 | 236.3 | 60,503.6 | link_latency | 0.88x | 0.88x | 1.15x | 0.88x |
| DeepSeek-V4.1-Flash | 1024 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2,431.0 | 2,489,395.1 | compute | DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 728.97 | 304.7 | 311,986.7 | weight_read | 7.98x | 7.98x | 9.60x | 7.99x |
| DeepSeek-V4.1-Flash | 1024 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x93 | 75,795 | 53.1 | 54,359.8 | compute | DeepSeek-V4.1-Flash/b200_sxm-x47-hybrid | 75,200 | 1.01x | hybrid | 2,179.56 | 124.4 | 127,359.9 | weight_read | 0.43x | 0.43x | 0.80x | 0.43x |
| DeepSeek-V4.1-Flash | 4096 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 767.9 | 3,145,238.7 | compute | DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 2,900.67 | 161.9 | 663,002.4 | link_latency | 4.74x | 4.74x | 7.20x | 4.74x |
| DeepSeek-V4.1-Flash | 4096 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x93 | 75,795 | 13.3 | 54,359.8 | compute | DeepSeek-V4.1-Flash/b200_sxm-x47-hybrid | 75,200 | 1.01x | hybrid | 7,758.05 | 71.0 | 290,720.6 | link_latency | 0.19x | 0.19x | 0.49x | 0.19x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | 4 | 6,400 | 429.26 | 194.05 | 575.8 | 666.1 |
| DeepSeek-V4.1-Flash | 21 | 33,600 | 527.29 | 194.60 | 678.9 | 877.0 |
| DeepSeek-V4.1-Flash | 23 | 36,800 | 527.39 | 194.61 | 682.3 | 882.7 |
| DeepSeek-V4.1-Flash | 24 | 38,400 | 527.44 | 194.62 | 683.8 | 885.2 |
| DeepSeek-V4.1-Flash | 28 | 44,800 | 527.65 | 194.63 | 688.7 | 893.6 |
| DeepSeek-V4.1-Flash | 29 | 46,400 | 527.69 | 194.64 | 689.7 | 895.4 |
| DeepSeek-V4.1-Flash | 30 | 48,000 | 527.73 | 194.64 | 690.7 | 897.0 |
| DeepSeek-V4.1-Flash | 43 | 68,800 | 528.30 | 194.67 | 699.1 | 911.7 |
| DeepSeek-V4.1-Flash | 44 | 70,400 | 528.33 | 194.67 | 699.5 | 912.5 |
| DeepSeek-V4.1-Flash | 45 | 72,000 | 528.37 | 194.67 | 699.9 | 913.3 |
| DeepSeek-V4.1-Flash | 47 | 75,200 | 528.45 | 194.67 | 700.7 | 914.7 |
| DeepSeek-V4.1-Flash | 49 | 78,400 | 528.54 | 194.67 | 701.5 | 916.0 |
| DeepSeek-V4.1-Flash | 52 | 83,200 | 528.65 | 194.68 | 702.4 | 917.7 |
| DeepSeek-V4.1-Flash | 55 | 88,000 | 528.77 | 194.68 | 703.3 | 919.3 |
| DeepSeek-V4.1-Flash | 56 | 89,600 | 528.81 | 194.68 | 703.6 | 919.8 |
| DeepSeek-V4.1-Flash | 57 | 91,200 | 528.85 | 194.68 | 703.8 | 920.3 |
| DeepSeek-V4.1-Flash | 58 | 92,800 | 528.89 | 194.68 | 704.1 | 920.7 |
| DeepSeek-V4.1-Flash | 63 | 100,800 | 529.08 | 194.69 | 705.2 | 922.8 |
| DeepSeek-V4.1-Flash | 67 | 107,200 | 529.24 | 194.69 | 706.0 | 924.2 |
| DeepSeek-V4.1-Flash | 75 | 120,000 | 534.07 | 196.93 | 693.3 | 904.8 |
| DeepSeek-V4.1-Flash | 76 | 121,600 | 534.07 | 196.93 | 693.6 | 905.3 |
| DeepSeek-V4.1-Flash | 84 | 134,400 | 534.07 | 196.93 | 695.8 | 909.0 |
| DeepSeek-V4.1-Flash | 87 | 139,200 | 534.07 | 196.93 | 696.5 | 910.2 |
| DeepSeek-V4.1-Flash | 89 | 142,400 | 534.07 | 196.93 | 697.0 | 911.0 |
| DeepSeek-V4.1-Flash | 90 | 144,000 | 534.07 | 196.93 | 697.2 | 911.4 |
| DeepSeek-V4.1-Flash | 116 | 185,600 | 534.07 | 196.93 | 701.5 | 918.8 |
| DeepSeek-V4.1-Flash | 125 | 200,000 | 534.07 | 196.93 | 702.6 | 920.7 |
| DeepSeek-V4.1-Flash | 134 | 214,400 | 534.37 | 196.93 | 703.4 | 922.3 |
| DeepSeek-V4.1-Flash | 167 | 267,200 | 537.06 | 199.16 | 699.4 | 915.9 |
| DeepSeek-V4.1-Flash | 173 | 276,800 | 537.06 | 199.16 | 700.0 | 916.8 |
| DeepSeek-V4.1-Flash | 179 | 286,400 | 537.06 | 199.16 | 700.5 | 917.7 |
| DeepSeek-V4.1-Flash | 231 | 369,600 | 539.98 | 201.40 | 698.6 | 915.0 |
| DeepSeek-V4.1-Flash | 347 | 555,200 | 543.28 | 203.63 | 699.5 | 917.4 |

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
| DeepSeek-V4.1-Flash | 4 | 6,400 | 378.5 | 575.8 | — | tensor | 429.26 | 24.7% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 21 | 33,600 | 374.9 | 678.9 | 643.5 | tensor | 527.29 | 35.8% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 23 | 36,800 | 374.5 | 682.3 | 652.8 | tensor | 527.39 | 36.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 24 | 38,400 | 374.3 | 683.8 | 657.0 | tensor | 527.44 | 36.1% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 28 | 44,800 | 373.4 | 688.7 | 642.3 | tensor | 527.65 | 36.3% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 29 | 46,400 | 373.2 | 689.7 | 646.0 | tensor | 527.69 | 36.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 30 | 48,000 | 373.0 | 690.7 | 649.4 | tensor | 527.73 | 36.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 43 | 68,800 | 371.1 | 699.1 | 642.3 | tensor | 528.30 | 36.9% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 44 | 70,400 | 371.1 | 699.5 | 644.7 | tensor | 528.33 | 37.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 45 | 72,000 | 371.1 | 699.9 | 646.9 | tensor | 528.37 | 37.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 47 | 75,200 | 371.1 | 700.7 | 651.2 | tensor | 528.45 | 37.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 49 | 78,400 | 371.1 | 701.5 | 638.7 | tensor | 528.54 | 37.1% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 52 | 83,200 | 371.1 | 702.4 | 644.7 | tensor | 528.65 | 37.1% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 55 | 88,000 | 371.1 | 703.3 | 650.2 | tensor | 528.77 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 56 | 89,600 | 371.1 | 703.6 | 651.9 | tensor | 528.81 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 57 | 91,200 | 371.1 | 703.8 | 639.3 | tensor | 528.85 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 58 | 92,800 | 371.1 | 704.1 | 641.1 | tensor | 528.89 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 63 | 100,800 | 371.1 | 705.2 | 649.2 | tensor | 529.08 | 37.3% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 67 | 107,200 | 371.1 | 706.0 | 642.5 | tensor | 529.24 | 37.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 75 | 120,000 | 371.1 | 414.7 | 693.3 | hybrid | 534.07 | 37.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 76 | 121,600 | 371.1 | 414.7 | 693.6 | hybrid | 534.07 | 37.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 84 | 134,400 | 371.1 | 414.6 | 695.8 | hybrid | 534.07 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 87 | 139,200 | 371.1 | 414.5 | 696.5 | hybrid | 534.07 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 89 | 142,400 | 371.1 | 414.5 | 697.0 | hybrid | 534.07 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 90 | 144,000 | 371.1 | 414.4 | 697.2 | hybrid | 534.07 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 116 | 185,600 | 371.1 | 413.6 | 701.5 | hybrid | 534.07 | 37.5% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 125 | 200,000 | 371.1 | 413.2 | 702.6 | hybrid | 534.07 | 37.5% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 134 | 214,400 | 371.1 | 412.8 | 703.4 | hybrid | 534.37 | 37.6% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 167 | 267,200 | 371.1 | 405.2 | 699.4 | hybrid | 537.06 | 37.6% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 173 | 276,800 | 371.1 | 404.8 | 700.0 | hybrid | 537.06 | 37.6% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 179 | 286,400 | 371.1 | 404.4 | 700.5 | hybrid | 537.06 | 37.6% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 231 | 369,600 | 371.1 | 397.3 | 698.6 | hybrid | 539.98 | 37.7% | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 347 | 555,200 | 371.1 | 385.8 | 699.5 | hybrid | 543.28 | 38.0% | layer_fixed_latency |

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
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x87 | DeepSeek-V4.1-Flash | 87 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x89 | DeepSeek-V4.1-Flash | 89 | tensor | rom_package_ucie | rom_board_serdes | 160 | 73.77 us | 1,355.6 tok/s | 13,556.2 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 23 on rom_board_serdes (traversals 8.8) = 71.71 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x89 | DeepSeek-V4.1-Flash | 89 | hybrid | rom_package_ucie | rom_board_serdes | 102 | 4.39 us | 22,800.0 tok/s | 228,000.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 22 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.33 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x87 | DeepSeek-V4.1-Flash | 87 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-tensor-x85 | DeepSeek-V4.1-Flash | 85 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hybrid-x86 | DeepSeek-V4.1-Flash | 86 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x176 | DeepSeek-V4.1-Flash | 176 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x97 | DeepSeek-V4.1-Flash | 97 | tensor | rom_package_ucie | rom_board_serdes | 160 | 73.77 us | 1,355.5 tok/s | 13,555.4 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 25 on rom_board_serdes (traversals 8.8) = 71.71 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x107 | DeepSeek-V4.1-Flash | 107 | hybrid | rom_package_ucie | rom_board_serdes | 106 | 4.81 us | 20,795.6 tok/s | 207,955.9 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 26 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.75 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-pipeline-x174 | DeepSeek-V4.1-Flash | 174 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3 | DeepSeek-V4.1-Flash | 3 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-tensor-x93 | DeepSeek-V4.1-Flash | 93 | tensor | nvlink5 | infiniband_ndr | 160 | 564.25 us | 177.2 tok/s | 1,772.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 369.86 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hybrid-x112 | DeepSeek-V4.1-Flash | 112 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.44 us | 447.5 tok/s | 4,475.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 29.05 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-pipeline | DeepSeek-V4.1-Flash | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,516.9 tok/s | 275,168.8 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-tensor | DeepSeek-V4.1-Flash | 4 | tensor | nvlink5 | infiniband_ndr | 80 | 194.05 us | 515.3 tok/s | 5,153.4 tok/s | 80 x all_reduce span 4 on nvlink5 (traversals 2.0) = 194.05 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-nvl72-tensor | DeepSeek-V4.1-Flash | 4 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.05 us | 515.3 tok/s | 5,153.4 tok/s | 80 x all_reduce span 4 on nvlink5_nvl72 (traversals 2.0) = 194.05 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-expert | DeepSeek-V4.1-Flash | 4 | expert | nvlink5 | infiniband_ndr | 160 | 291.41 us | 343.2 tok/s | 3,431.6 tok/s | 80 x all_reduce span 4 on nvlink5 (traversals 2.0) = 194.05 us; 80 x point_to_point span 2 on nvlink5 (traversals 1.0) = 97.37 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-nvl72-expert | DeepSeek-V4.1-Flash | 4 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 291.41 us | 343.2 tok/s | 3,431.6 tok/s | 80 x all_reduce span 4 on nvlink5_nvl72 (traversals 2.0) = 194.05 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 97.37 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-pipeline | DeepSeek-V4.1-Flash | 21 | pipeline | nvlink5 | infiniband_ndr | 20 | 26.27 us | 3,806.0 tok/s | 38,059.9 tok/s | 18 x point_to_point span 2 on nvlink5 (traversals 1.0) = 21.80 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-tensor | DeepSeek-V4.1-Flash | 21 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-hybrid | DeepSeek-V4.1-Flash | 21 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-nvl72-tensor | DeepSeek-V4.1-Flash | 21 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.60 us | 513.9 tok/s | 5,138.7 tok/s | 80 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 194.60 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-expert | DeepSeek-V4.1-Flash | 21 | expert | nvlink5 | infiniband_ndr | 160 | 360.28 us | 277.6 tok/s | 2,775.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 167.08 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-nvl72-expert | DeepSeek-V4.1-Flash | 21 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.86 us | 343.8 tok/s | 3,438.1 tok/s | 80 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 194.60 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.26 us |
| DeepSeek-V4.1-Flash/b200_sxm-x23-pipeline | DeepSeek-V4.1-Flash | 23 | pipeline | nvlink5 | infiniband_ndr | 22 | 28.70 us | 3,484.7 tok/s | 34,846.7 tok/s | 20 x point_to_point span 2 on nvlink5 (traversals 1.0) = 24.23 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x23-tensor | DeepSeek-V4.1-Flash | 23 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x23-hybrid | DeepSeek-V4.1-Flash | 23 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x23-nvl72-tensor | DeepSeek-V4.1-Flash | 23 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.61 us | 513.8 tok/s | 5,138.4 tok/s | 80 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 194.61 us |
| DeepSeek-V4.1-Flash/b200_sxm-x23-expert | DeepSeek-V4.1-Flash | 23 | expert | nvlink5 | infiniband_ndr | 160 | 359.87 us | 277.9 tok/s | 2,778.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 166.67 us |
| DeepSeek-V4.1-Flash/b200_sxm-x23-nvl72-expert | DeepSeek-V4.1-Flash | 23 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.85 us | 343.8 tok/s | 3,438.2 tok/s | 80 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 194.61 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.24 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-pipeline | DeepSeek-V4.1-Flash | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 29.91 us | 3,343.5 tok/s | 33,435.3 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.44 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-tensor | DeepSeek-V4.1-Flash | 24 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-hybrid | DeepSeek-V4.1-Flash | 24 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-nvl72-tensor | DeepSeek-V4.1-Flash | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.62 us | 513.8 tok/s | 5,138.3 tok/s | 80 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 194.62 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-expert | DeepSeek-V4.1-Flash | 24 | expert | nvlink5 | infiniband_ndr | 160 | 359.29 us | 278.3 tok/s | 2,783.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 166.50 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-nvl72-expert | DeepSeek-V4.1-Flash | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.84 us | 343.8 tok/s | 3,438.3 tok/s | 80 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 194.62 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x28-pipeline | DeepSeek-V4.1-Flash | 28 | pipeline | nvlink5 | infiniband_ndr | 27 | 35.78 us | 2,795.1 tok/s | 27,950.6 tok/s | 24 x point_to_point span 2 on nvlink5 (traversals 1.0) = 29.07 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x28-tensor | DeepSeek-V4.1-Flash | 28 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash/b200_sxm-x28-hybrid | DeepSeek-V4.1-Flash | 28 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x28-nvl72-tensor | DeepSeek-V4.1-Flash | 28 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.63 us | 513.8 tok/s | 5,137.9 tok/s | 80 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 194.63 us |
| DeepSeek-V4.1-Flash/b200_sxm-x28-expert | DeepSeek-V4.1-Flash | 28 | expert | nvlink5 | infiniband_ndr | 160 | 358.71 us | 278.8 tok/s | 2,787.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash/b200_sxm-x28-nvl72-expert | DeepSeek-V4.1-Flash | 28 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.83 us | 343.8 tok/s | 3,438.5 tok/s | 80 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 194.63 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.20 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-pipeline | DeepSeek-V4.1-Flash | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.99 us | 2,703.5 tok/s | 27,035.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.28 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-tensor | DeepSeek-V4.1-Flash | 29 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-hybrid | DeepSeek-V4.1-Flash | 29 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-nvl72-tensor | DeepSeek-V4.1-Flash | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.8 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-expert | DeepSeek-V4.1-Flash | 29 | expert | nvlink5 | infiniband_ndr | 160 | 358.59 us | 278.9 tok/s | 2,788.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.79 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-nvl72-expert | DeepSeek-V4.1-Flash | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.8 tok/s | 3,438.5 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.19 us |
| DeepSeek-V4.1-Flash/b200_sxm-x30-pipeline | DeepSeek-V4.1-Flash | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.20 us | 2,617.8 tok/s | 26,177.9 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.50 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x30-tensor | DeepSeek-V4.1-Flash | 30 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash/b200_sxm-x30-hybrid | DeepSeek-V4.1-Flash | 30 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x30-nvl72-tensor | DeepSeek-V4.1-Flash | 30 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.7 tok/s | 80 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x30-expert | DeepSeek-V4.1-Flash | 30 | expert | nvlink5 | infiniband_ndr | 160 | 358.47 us | 279.0 tok/s | 2,789.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x30-nvl72-expert | DeepSeek-V4.1-Flash | 30 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.5 tok/s | 80 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.18 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-pipeline | DeepSeek-V4.1-Flash | 43 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-tensor | DeepSeek-V4.1-Flash | 43 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-hybrid | DeepSeek-V4.1-Flash | 43 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-nvl72-tensor | DeepSeek-V4.1-Flash | 43 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,137.0 tok/s | 80 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-expert | DeepSeek-V4.1-Flash | 43 | expert | nvlink5 | infiniband_ndr | 160 | 357.16 us | 280.0 tok/s | 2,799.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-nvl72-expert | DeepSeek-V4.1-Flash | 43 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.13 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-pipeline | DeepSeek-V4.1-Flash | 44 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-tensor | DeepSeek-V4.1-Flash | 44 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-hybrid | DeepSeek-V4.1-Flash | 44 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-nvl72-tensor | DeepSeek-V4.1-Flash | 44 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.9 tok/s | 80 x all_reduce span 44 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-expert | DeepSeek-V4.1-Flash | 44 | expert | nvlink5 | infiniband_ndr | 160 | 357.11 us | 280.0 tok/s | 2,800.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.63 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-nvl72-expert | DeepSeek-V4.1-Flash | 44 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 44 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash/b200_sxm-x45-pipeline | DeepSeek-V4.1-Flash | 45 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x45-tensor | DeepSeek-V4.1-Flash | 45 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash/b200_sxm-x45-hybrid | DeepSeek-V4.1-Flash | 45 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash/b200_sxm-x45-nvl72-tensor | DeepSeek-V4.1-Flash | 45 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.9 tok/s | 80 x all_reduce span 45 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash/b200_sxm-x45-expert | DeepSeek-V4.1-Flash | 45 | expert | nvlink5 | infiniband_ndr | 160 | 357.06 us | 280.1 tok/s | 2,800.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.58 us |
| DeepSeek-V4.1-Flash/b200_sxm-x45-nvl72-expert | DeepSeek-V4.1-Flash | 45 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 45 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash/b200_sxm-x47-pipeline | DeepSeek-V4.1-Flash | 47 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x47-tensor | DeepSeek-V4.1-Flash | 47 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash/b200_sxm-x47-hybrid | DeepSeek-V4.1-Flash | 47 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash/b200_sxm-x47-nvl72-tensor | DeepSeek-V4.1-Flash | 47 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.8 tok/s | 80 x all_reduce span 47 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash/b200_sxm-x47-expert | DeepSeek-V4.1-Flash | 47 | expert | nvlink5 | infiniband_ndr | 160 | 356.97 us | 280.1 tok/s | 2,801.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.49 us |
| DeepSeek-V4.1-Flash/b200_sxm-x47-nvl72-expert | DeepSeek-V4.1-Flash | 47 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 47 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash/b200_sxm-x49-pipeline | DeepSeek-V4.1-Flash | 49 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x49-tensor | DeepSeek-V4.1-Flash | 49 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash/b200_sxm-x49-hybrid | DeepSeek-V4.1-Flash | 49 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash/b200_sxm-x49-nvl72-tensor | DeepSeek-V4.1-Flash | 49 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.8 tok/s | 80 x all_reduce span 49 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash/b200_sxm-x49-expert | DeepSeek-V4.1-Flash | 49 | expert | nvlink5 | infiniband_ndr | 160 | 356.80 us | 280.3 tok/s | 2,802.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.41 us |
| DeepSeek-V4.1-Flash/b200_sxm-x49-nvl72-expert | DeepSeek-V4.1-Flash | 49 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 49 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.11 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-pipeline | DeepSeek-V4.1-Flash | 52 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-tensor | DeepSeek-V4.1-Flash | 52 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-hybrid | DeepSeek-V4.1-Flash | 52 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-nvl72-tensor | DeepSeek-V4.1-Flash | 52 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.7 tok/s | 80 x all_reduce span 52 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-expert | DeepSeek-V4.1-Flash | 52 | expert | nvlink5 | infiniband_ndr | 160 | 356.69 us | 280.4 tok/s | 2,803.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.29 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-nvl72-expert | DeepSeek-V4.1-Flash | 52 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 52 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.11 us |
| DeepSeek-V4.1-Flash/b200_sxm-x55-pipeline | DeepSeek-V4.1-Flash | 55 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x55-tensor | DeepSeek-V4.1-Flash | 55 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash/b200_sxm-x55-hybrid | DeepSeek-V4.1-Flash | 55 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash/b200_sxm-x55-nvl72-tensor | DeepSeek-V4.1-Flash | 55 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.6 tok/s | 80 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x55-expert | DeepSeek-V4.1-Flash | 55 | expert | nvlink5 | infiniband_ndr | 160 | 356.59 us | 280.4 tok/s | 2,804.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.19 us |
| DeepSeek-V4.1-Flash/b200_sxm-x55-nvl72-expert | DeepSeek-V4.1-Flash | 55 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.10 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-pipeline | DeepSeek-V4.1-Flash | 56 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-tensor | DeepSeek-V4.1-Flash | 56 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-hybrid | DeepSeek-V4.1-Flash | 56 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-nvl72-tensor | DeepSeek-V4.1-Flash | 56 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.6 tok/s | 80 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-expert | DeepSeek-V4.1-Flash | 56 | expert | nvlink5 | infiniband_ndr | 160 | 356.50 us | 280.5 tok/s | 2,805.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.16 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-nvl72-expert | DeepSeek-V4.1-Flash | 56 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.10 us |
| DeepSeek-V4.1-Flash/b200_sxm-x57-pipeline | DeepSeek-V4.1-Flash | 57 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x57-tensor | DeepSeek-V4.1-Flash | 57 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash/b200_sxm-x57-hybrid | DeepSeek-V4.1-Flash | 57 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x57-nvl72-tensor | DeepSeek-V4.1-Flash | 57 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.6 tok/s | 80 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x57-expert | DeepSeek-V4.1-Flash | 57 | expert | nvlink5 | infiniband_ndr | 160 | 356.47 us | 280.5 tok/s | 2,805.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.12 us |
| DeepSeek-V4.1-Flash/b200_sxm-x57-nvl72-expert | DeepSeek-V4.1-Flash | 57 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.10 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-pipeline | DeepSeek-V4.1-Flash | 58 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-tensor | DeepSeek-V4.1-Flash | 58 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-hybrid | DeepSeek-V4.1-Flash | 58 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-tensor | DeepSeek-V4.1-Flash | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.5 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-expert | DeepSeek-V4.1-Flash | 58 | expert | nvlink5 | infiniband_ndr | 160 | 356.44 us | 280.6 tok/s | 2,805.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.09 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-expert | DeepSeek-V4.1-Flash | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.09 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-pipeline | DeepSeek-V4.1-Flash | 63 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-tensor | DeepSeek-V4.1-Flash | 63 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-hybrid | DeepSeek-V4.1-Flash | 63 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-nvl72-tensor | DeepSeek-V4.1-Flash | 63 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-expert | DeepSeek-V4.1-Flash | 63 | expert | nvlink5 | infiniband_ndr | 160 | 356.30 us | 280.7 tok/s | 2,806.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.96 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-nvl72-expert | DeepSeek-V4.1-Flash | 63 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.09 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-pipeline | DeepSeek-V4.1-Flash | 67 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-tensor | DeepSeek-V4.1-Flash | 67 | tensor | nvlink5 | infiniband_ndr | 160 | 562.88 us | 177.7 tok/s | 1,776.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 368.49 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-hybrid | DeepSeek-V4.1-Flash | 67 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-nvl72-tensor | DeepSeek-V4.1-Flash | 67 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 67 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-expert | DeepSeek-V4.1-Flash | 67 | expert | nvlink5 | infiniband_ndr | 160 | 356.17 us | 280.8 tok/s | 2,807.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.87 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-nvl72-expert | DeepSeek-V4.1-Flash | 67 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 67 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.08 us |
| DeepSeek-V4.1-Flash/b200_sxm-x75-pipeline | DeepSeek-V4.1-Flash | 75 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x75-tensor | DeepSeek-V4.1-Flash | 75 | tensor | nvlink5 | infiniband_ndr | 160 | 563.43 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 369.04 us |
| DeepSeek-V4.1-Flash/b200_sxm-x75-hybrid | DeepSeek-V4.1-Flash | 75 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash/b200_sxm-x75-nvl72-tensor | DeepSeek-V4.1-Flash | 75 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x75-nvl72-hybrid | DeepSeek-V4.1-Flash | 75 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x75-expert | DeepSeek-V4.1-Flash | 75 | expert | nvlink5 | infiniband_ndr | 160 | 355.98 us | 280.9 tok/s | 2,809.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.27 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.71 us |
| DeepSeek-V4.1-Flash/b200_sxm-x75-nvl72-expert | DeepSeek-V4.1-Flash | 75 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.40 us | 279.0 tok/s | 2,790.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.71 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-pipeline | DeepSeek-V4.1-Flash | 76 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-tensor | DeepSeek-V4.1-Flash | 76 | tensor | nvlink5 | infiniband_ndr | 160 | 563.43 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 369.04 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-hybrid | DeepSeek-V4.1-Flash | 76 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-nvl72-tensor | DeepSeek-V4.1-Flash | 76 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-nvl72-hybrid | DeepSeek-V4.1-Flash | 76 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-expert | DeepSeek-V4.1-Flash | 76 | expert | nvlink5 | infiniband_ndr | 160 | 355.96 us | 280.9 tok/s | 2,809.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.27 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-nvl72-expert | DeepSeek-V4.1-Flash | 76 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.39 us | 279.0 tok/s | 2,790.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-pipeline | DeepSeek-V4.1-Flash | 84 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-tensor | DeepSeek-V4.1-Flash | 84 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-hybrid | DeepSeek-V4.1-Flash | 84 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-nvl72-tensor | DeepSeek-V4.1-Flash | 84 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-nvl72-hybrid | DeepSeek-V4.1-Flash | 84 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-expert | DeepSeek-V4.1-Flash | 84 | expert | nvlink5 | infiniband_ndr | 160 | 355.81 us | 281.0 tok/s | 2,810.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-nvl72-expert | DeepSeek-V4.1-Flash | 84 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.26 us | 279.1 tok/s | 2,791.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-pipeline | DeepSeek-V4.1-Flash | 87 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-tensor | DeepSeek-V4.1-Flash | 87 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-hybrid | DeepSeek-V4.1-Flash | 87 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-tensor | DeepSeek-V4.1-Flash | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4.1-Flash | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-expert | DeepSeek-V4.1-Flash | 87 | expert | nvlink5 | infiniband_ndr | 160 | 355.77 us | 281.1 tok/s | 2,810.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-expert | DeepSeek-V4.1-Flash | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.22 us | 279.2 tok/s | 2,791.6 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash/b200_sxm-x89-pipeline | DeepSeek-V4.1-Flash | 89 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x89-tensor | DeepSeek-V4.1-Flash | 89 | tensor | nvlink5 | infiniband_ndr | 160 | 564.25 us | 177.2 tok/s | 1,772.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 369.86 us |
| DeepSeek-V4.1-Flash/b200_sxm-x89-hybrid | DeepSeek-V4.1-Flash | 89 | hybrid | nvlink5 | infiniband_ndr | 91 | 218.97 us | 456.7 tok/s | 4,566.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 24.58 us |
| DeepSeek-V4.1-Flash/b200_sxm-x89-nvl72-tensor | DeepSeek-V4.1-Flash | 89 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x89-nvl72-hybrid | DeepSeek-V4.1-Flash | 89 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x89-expert | DeepSeek-V4.1-Flash | 89 | expert | nvlink5 | infiniband_ndr | 160 | 355.72 us | 281.1 tok/s | 2,811.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.22 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.50 us |
| DeepSeek-V4.1-Flash/b200_sxm-x89-nvl72-expert | DeepSeek-V4.1-Flash | 89 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.20 us | 279.2 tok/s | 2,791.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.50 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-pipeline | DeepSeek-V4.1-Flash | 90 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-tensor | DeepSeek-V4.1-Flash | 90 | tensor | nvlink5 | infiniband_ndr | 160 | 564.25 us | 177.2 tok/s | 1,772.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 369.86 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-hybrid | DeepSeek-V4.1-Flash | 90 | hybrid | nvlink5 | infiniband_ndr | 91 | 218.97 us | 456.7 tok/s | 4,566.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 24.58 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-nvl72-tensor | DeepSeek-V4.1-Flash | 90 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-nvl72-hybrid | DeepSeek-V4.1-Flash | 90 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-expert | DeepSeek-V4.1-Flash | 90 | expert | nvlink5 | infiniband_ndr | 160 | 355.71 us | 281.1 tok/s | 2,811.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.22 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.49 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-nvl72-expert | DeepSeek-V4.1-Flash | 90 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.19 us | 279.2 tok/s | 2,791.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.49 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-pipeline | DeepSeek-V4.1-Flash | 116 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-tensor | DeepSeek-V4.1-Flash | 116 | tensor | nvlink5 | infiniband_ndr | 160 | 565.06 us | 177.0 tok/s | 1,769.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 370.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-hybrid | DeepSeek-V4.1-Flash | 116 | hybrid | nvlink5 | infiniband_ndr | 94 | 225.68 us | 443.1 tok/s | 4,431.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.29 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-nvl72-tensor | DeepSeek-V4.1-Flash | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4.1-Flash | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-expert | DeepSeek-V4.1-Flash | 116 | expert | nvlink5 | infiniband_ndr | 160 | 355.42 us | 281.4 tok/s | 2,813.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.17 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-nvl72-expert | DeepSeek-V4.1-Flash | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.94 us | 279.4 tok/s | 2,793.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-pipeline | DeepSeek-V4.1-Flash | 125 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-tensor | DeepSeek-V4.1-Flash | 125 | tensor | nvlink5 | infiniband_ndr | 160 | 565.27 us | 176.9 tok/s | 1,769.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 370.88 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-hybrid | DeepSeek-V4.1-Flash | 125 | hybrid | nvlink5 | infiniband_ndr | 95 | 227.91 us | 438.8 tok/s | 4,387.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.52 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-nvl72-tensor | DeepSeek-V4.1-Flash | 125 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-nvl72-hybrid | DeepSeek-V4.1-Flash | 125 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-expert | DeepSeek-V4.1-Flash | 125 | expert | nvlink5 | infiniband_ndr | 160 | 355.35 us | 281.4 tok/s | 2,814.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.16 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.19 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-nvl72-expert | DeepSeek-V4.1-Flash | 125 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.88 us | 279.4 tok/s | 2,794.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.19 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-pipeline | DeepSeek-V4.1-Flash | 134 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-tensor | DeepSeek-V4.1-Flash | 134 | tensor | nvlink5 | infiniband_ndr | 160 | 565.45 us | 176.9 tok/s | 1,768.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 371.06 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-hybrid | DeepSeek-V4.1-Flash | 134 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.15 us | 434.5 tok/s | 4,345.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 35.76 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-nvl72-tensor | DeepSeek-V4.1-Flash | 134 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-nvl72-hybrid | DeepSeek-V4.1-Flash | 134 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-expert | DeepSeek-V4.1-Flash | 134 | expert | nvlink5 | infiniband_ndr | 160 | 355.28 us | 281.5 tok/s | 2,814.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.15 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.13 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-nvl72-expert | DeepSeek-V4.1-Flash | 134 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.83 us | 279.5 tok/s | 2,794.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.13 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-pipeline | DeepSeek-V4.1-Flash | 167 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-tensor | DeepSeek-V4.1-Flash | 167 | tensor | nvlink5 | infiniband_ndr | 160 | 566.00 us | 176.7 tok/s | 1,766.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 371.61 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-hybrid | DeepSeek-V4.1-Flash | 167 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.09 us | 418.3 tok/s | 4,182.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-nvl72-tensor | DeepSeek-V4.1-Flash | 167 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-nvl72-hybrid | DeepSeek-V4.1-Flash | 167 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-expert | DeepSeek-V4.1-Flash | 167 | expert | nvlink5 | infiniband_ndr | 160 | 355.11 us | 281.6 tok/s | 2,816.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.12 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-nvl72-expert | DeepSeek-V4.1-Flash | 167 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.34 us | 280.6 tok/s | 2,806.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-pipeline | DeepSeek-V4.1-Flash | 173 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-tensor | DeepSeek-V4.1-Flash | 173 | tensor | nvlink5 | infiniband_ndr | 160 | 566.11 us | 176.6 tok/s | 1,766.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 371.72 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-hybrid | DeepSeek-V4.1-Flash | 173 | hybrid | nvlink5 | infiniband_ndr | 101 | 241.32 us | 414.4 tok/s | 4,143.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.93 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-nvl72-tensor | DeepSeek-V4.1-Flash | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4.1-Flash | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-expert | DeepSeek-V4.1-Flash | 173 | expert | nvlink5 | infiniband_ndr | 160 | 355.08 us | 281.6 tok/s | 2,816.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.11 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-nvl72-expert | DeepSeek-V4.1-Flash | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.31 us | 280.7 tok/s | 2,806.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-pipeline | DeepSeek-V4.1-Flash | 179 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-tensor | DeepSeek-V4.1-Flash | 179 | tensor | nvlink5 | infiniband_ndr | 160 | 566.20 us | 176.6 tok/s | 1,766.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 23 on infiniband_ndr (traversals 2.0) = 371.81 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-hybrid | DeepSeek-V4.1-Flash | 179 | hybrid | nvlink5 | infiniband_ndr | 102 | 243.55 us | 410.6 tok/s | 4,105.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 22 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 49.17 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-nvl72-tensor | DeepSeek-V4.1-Flash | 179 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-nvl72-hybrid | DeepSeek-V4.1-Flash | 179 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-expert | DeepSeek-V4.1-Flash | 179 | expert | nvlink5 | infiniband_ndr | 160 | 355.06 us | 281.6 tok/s | 2,816.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.11 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.95 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-nvl72-expert | DeepSeek-V4.1-Flash | 179 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.30 us | 280.7 tok/s | 2,806.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.95 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-pipeline | DeepSeek-V4.1-Flash | 231 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-tensor | DeepSeek-V4.1-Flash | 231 | tensor | nvlink5 | infiniband_ndr | 160 | 566.65 us | 176.5 tok/s | 1,764.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 372.26 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-hybrid | DeepSeek-V4.1-Flash | 231 | hybrid | nvlink5 | infiniband_ndr | 108 | 256.96 us | 389.2 tok/s | 3,891.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 62.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-nvl72-tensor | DeepSeek-V4.1-Flash | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 556.36 us | 179.7 tok/s | 1,797.4 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4.1-Flash | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 83 | 201.40 us | 496.5 tok/s | 4,965.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-expert | DeepSeek-V4.1-Flash | 231 | expert | nvlink5 | infiniband_ndr | 160 | 354.91 us | 281.8 tok/s | 2,817.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.09 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-nvl72-expert | DeepSeek-V4.1-Flash | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.72 us | 281.1 tok/s | 2,811.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.90 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-pipeline | DeepSeek-V4.1-Flash | 347 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-tensor | DeepSeek-V4.1-Flash | 347 | tensor | nvlink5 | infiniband_ndr | 160 | 567.22 us | 176.3 tok/s | 1,763.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 372.83 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-hybrid | DeepSeek-V4.1-Flash | 347 | hybrid | nvlink5 | infiniband_ndr | 119 | 281.55 us | 355.2 tok/s | 3,551.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 39 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 87.16 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-tensor | DeepSeek-V4.1-Flash | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 558.81 us | 179.0 tok/s | 1,789.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4.1-Flash | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 84 | 203.63 us | 491.1 tok/s | 4,910.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-expert | DeepSeek-V4.1-Flash | 347 | expert | nvlink5 | infiniband_ndr | 160 | 354.74 us | 281.9 tok/s | 2,819.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.06 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-expert | DeepSeek-V4.1-Flash | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.36 us | 281.4 tok/s | 2,814.1 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.67 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash | 1 | wafer | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,375.3 | 0.047 | 4,126.4 (87,205) | 4,375.3 (92,450) | 1.06x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 2 | wafer | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,375.3 | 0.047 | 4,126.4 (87,205) | 4,375.3 (92,450) | 1.06x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 4 | wafer | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,371.6 | 0.047 | 4,126.4 (87,205) | 4,371.6 (92,450) | 1.06x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 8 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,338.7 | 0.047 | 4,079.4 (87,205) | 4,338.7 (92,450) | 1.06x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 16 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,251.2 | 0.046 | 4,028.7 (89,650) | 4,251.2 (92,450) | 1.06x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 32 | array | wafer | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x148-romfill | 120,620 | 4,143.4 | 0.034 | 4,076.7 (107,580) | 4,271.0 (138,675) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 64 | array | wafer | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 4,085.1 | 0.029 | 3,945.1 (120,620) | 4,184.0 (138,675) | 1.06x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 256 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,131.4 | 0.007 | 3,240.3 (215,160) | 4,131.4 (554,700) | 1.27x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 1024 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2,431.0 | 0.004 | 1,713.1 (277,100) | 2,431.0 (554,700) | 1.42x | compute |
| DeepSeek-V4.1-Flash | 4096 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 736.0 | 0.002 | 620.7 (277,100) | 736.0 (369,800) | 1.19x | weight_read |

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
| DeepSeek-V4.1-Flash | 384 | 752.0 MB | 128.3 mm2 | 23.09 mm2 (18.0%) | 49,261 mm2 | 8,867 mm2 | 87,047 mm2 = 106.8 reticles |

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
| DeepSeek-V4.1-Flash | 1 | sram | 915,145.2 | 29,014.6 | 29,014.6 | 31.54x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | sram | 915,145.2 | 29,014.6 | 29,014.6 | 31.54x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | sram | 915,145.2 | 29,014.6 | 29,014.6 | 31.54x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | sram | 915,145.2 | 29,014.6 | 29,014.6 | 31.54x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | sram | 915,145.2 | 29,014.6 | 37,161.2 | 31.54x | 1.28x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | sram | 915,145.2 | 29,014.6 | 56,120.5 | 31.54x | 1.93x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | sram | 915,145.2 | 29,014.6 | 83,549.0 | 31.54x | 2.88x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 256 | sram | 919,567.6 | 29,014.6 | 150,471.2 | 31.69x | 5.19x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1024 | sram | 1,890,192.1 | 29,014.6 | 255,708.0 | 65.15x | 8.81x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | sram | 3,014,535.9 | 29,014.6 | 398,209.7 | 103.90x | 13.72x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1 | rom | 2,156,106.3 | 38,144.2 | 38,144.2 | 56.53x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | rom | 2,156,106.3 | 38,144.2 | 38,144.2 | 56.53x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | rom | 2,156,106.3 | 38,144.2 | 38,144.2 | 56.53x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | rom | 2,156,106.3 | 38,144.2 | 38,144.2 | 56.53x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | rom | 2,156,106.3 | 38,144.2 | 40,829.2 | 56.53x | 1.07x | compute | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 32 | rom | 2,156,106.3 | 38,144.2 | 61,902.7 | 56.53x | 1.62x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | rom | 2,156,106.3 | 38,472.0 | 90,783.1 | 56.04x | 2.36x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 256 | rom | 2,156,106.3 | 38,870.6 | 175,832.3 | 55.47x | 4.52x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1024 | rom | 2,489,395.1 | 38,870.6 | 298,091.8 | 64.04x | 7.67x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | rom | 3,145,238.7 | 38,870.6 | 533,477.9 | 80.92x | 13.72x | compute | weight_read | weight_read |

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
| DeepSeek-V4.1-Flash | 1 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 915,145.2 | 1.650 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 2,156,106.3 | 3.887 | compute | 2.36x |
| DeepSeek-V4.1-Flash | 1 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 1 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 2 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 915,145.2 | 1.650 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 2 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 2,156,106.3 | 3.887 | compute | 2.36x |
| DeepSeek-V4.1-Flash | 2 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 2 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 4 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 915,145.2 | 1.650 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 2,156,106.3 | 3.887 | compute | 2.36x |
| DeepSeek-V4.1-Flash | 4 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 4 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 8 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 915,145.2 | 1.650 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 8 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 2,156,106.3 | 3.887 | compute | 2.36x |
| DeepSeek-V4.1-Flash | 8 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 8 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 16 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 915,145.2 | 1.650 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 16 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 2,156,106.3 | 3.887 | compute | 2.36x |
| DeepSeek-V4.1-Flash | 16 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 16 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 16 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x42-perregion | 34,230 | 1.00 | 1.19 | 37,161.2 | 1.086 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 16 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x58-perregion-romfill | 47,270 | 1.26 | 1.43 | 40,829.2 | 0.864 | layer_fixed_latency | 0.04x |
| DeepSeek-V4.1-Flash | 32 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 915,145.2 | 1.650 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 32 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 2,156,106.3 | 3.887 | compute | 2.36x |
| DeepSeek-V4.1-Flash | 32 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 32 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 1.00 | 38,144.2 | 0.825 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 32 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x42-perregion | 34,230 | 1.00 | 1.66 | 56,120.5 | 1.640 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash | 32 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x58-perregion-romfill | 47,270 | 1.26 | 1.43 | 61,902.7 | 1.310 | weight_read | 0.07x |
| DeepSeek-V4.1-Flash | 64 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 915,145.2 | 1.650 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 64 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 2,156,106.3 | 3.887 | compute | 2.36x |
| DeepSeek-V4.1-Flash | 64 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 64 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 1.12 | 38,472.0 | 0.832 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 64 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x47-perregion | 38,305 | 1.00 | 2.18 | 83,549.0 | 2.181 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 64 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x58-perregion-romfill | 47,270 | 1.26 | 1.99 | 90,783.1 | 1.921 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash | 256 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 919,567.6 | 3.316 | layer_fixed_latency | 1.00x |
| DeepSeek-V4.1-Flash | 256 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 2,156,106.3 | 3.887 | compute | 2.34x |
| DeepSeek-V4.1-Flash | 256 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 256 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 4.49 | 38,870.6 | 0.841 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 256 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x47-perregion | 38,305 | 1.00 | 2.93 | 150,471.2 | 3.928 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 256 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x58-perregion-romfill | 47,270 | 1.26 | 3.49 | 175,832.3 | 3.720 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash | 1024 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 1,890,192.1 | 5.111 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1024 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 2,489,395.1 | 4.488 | compute | 1.32x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 17.96 | 29,014.6 | 0.628 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 17.96 | 38,870.6 | 0.841 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash | 1024 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x47-perregion | 38,305 | 1.00 | 5.74 | 255,708.0 | 6.676 | weight_read | 0.14x |
| DeepSeek-V4.1-Flash | 1024 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x58-perregion-romfill | 47,270 | 1.26 | 5.09 | 298,091.8 | 6.306 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash | 4096 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 3,014,535.9 | 8.152 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4096 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,145,238.7 | 5.670 | compute | 1.04x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 71.86 | 29,014.6 | 0.628 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.34 | 71.86 | 38,870.6 | 0.841 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash | 4096 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 5.24 | 398,209.7 | 8.615 | weight_read | 0.13x |
| DeepSeek-V4.1-Flash | 4096 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.34 | 5.24 | 533,477.9 | 11.541 | weight_read | 0.18x |

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
| DeepSeek-V4.1-Flash | 1 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 2 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 4 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 8 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 16 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 32 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 64 | 57 | 1.12 | 1.001 | 1.009 | 1.01x |
| DeepSeek-V4.1-Flash | 256 | 57 | 4.49 | 1.028 | 1.519 | 1.48x |
| DeepSeek-V4.1-Flash | 1024 | 57 | 17.96 | 1.139 | 2.691 | 2.36x |
| DeepSeek-V4.1-Flash | 4096 | 47 | 87.15 | 1.824 | 5.801 | 3.18x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | 1 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4.1-Flash | 2 | 4 | 3.87 | 2.63 | 1.47x |
| DeepSeek-V4.1-Flash | 4 | 4 | 4.00 | 2.91 | 1.37x |
| DeepSeek-V4.1-Flash | 8 | 4 | 4.00 | 3.16 | 1.27x |
| DeepSeek-V4.1-Flash | 16 | 4 | 4.00 | 3.35 | 1.19x |
| DeepSeek-V4.1-Flash | 32 | 4 | 4.00 | 3.49 | 1.15x |
| DeepSeek-V4.1-Flash | 64 | 4 | 4.00 | 3.59 | 1.11x |
| DeepSeek-V4.1-Flash | 256 | 4 | 4.00 | 3.66 | 1.09x |
| DeepSeek-V4.1-Flash | 1024 | 4 | 4.00 | 3.66 | 1.09x |
| DeepSeek-V4.1-Flash | 4096 | 4 | 4.00 | 3.66 | 1.09x |
| DeepSeek-V4.1-Flash | 1 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4.1-Flash | 2 | 21 | 9.25 | 5.30 | 1.75x |
| DeepSeek-V4.1-Flash | 4 | 21 | 14.31 | 6.93 | 2.06x |
| DeepSeek-V4.1-Flash | 8 | 21 | 18.71 | 8.71 | 2.15x |
| DeepSeek-V4.1-Flash | 16 | 21 | 20.68 | 10.49 | 1.97x |
| DeepSeek-V4.1-Flash | 32 | 21 | 20.99 | 12.09 | 1.74x |
| DeepSeek-V4.1-Flash | 64 | 21 | 21.00 | 13.34 | 1.57x |
| DeepSeek-V4.1-Flash | 256 | 21 | 21.00 | 14.41 | 1.46x |
| DeepSeek-V4.1-Flash | 1024 | 21 | 21.00 | 14.46 | 1.45x |
| DeepSeek-V4.1-Flash | 4096 | 21 | 21.00 | 14.46 | 1.45x |
| DeepSeek-V4.1-Flash | 1 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4.1-Flash | 2 | 23 | 9.45 | 5.45 | 1.74x |
| DeepSeek-V4.1-Flash | 4 | 23 | 14.89 | 7.19 | 2.07x |
| DeepSeek-V4.1-Flash | 8 | 23 | 19.95 | 9.11 | 2.19x |
| DeepSeek-V4.1-Flash | 16 | 23 | 22.49 | 11.05 | 2.03x |
| DeepSeek-V4.1-Flash | 32 | 23 | 22.97 | 12.82 | 1.79x |
| DeepSeek-V4.1-Flash | 64 | 23 | 23.00 | 14.22 | 1.62x |
| DeepSeek-V4.1-Flash | 256 | 23 | 23.00 | 15.42 | 1.49x |
| DeepSeek-V4.1-Flash | 1024 | 23 | 23.00 | 15.47 | 1.49x |
| DeepSeek-V4.1-Flash | 4096 | 23 | 23.00 | 15.47 | 1.49x |
| DeepSeek-V4.1-Flash | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4.1-Flash | 2 | 24 | 9.54 | 5.52 | 1.73x |
| DeepSeek-V4.1-Flash | 4 | 24 | 15.15 | 7.31 | 2.07x |
| DeepSeek-V4.1-Flash | 8 | 24 | 20.53 | 9.30 | 2.21x |
| DeepSeek-V4.1-Flash | 16 | 24 | 23.37 | 11.32 | 2.06x |
| DeepSeek-V4.1-Flash | 32 | 24 | 23.96 | 13.17 | 1.82x |
| DeepSeek-V4.1-Flash | 64 | 24 | 24.00 | 14.64 | 1.64x |
| DeepSeek-V4.1-Flash | 256 | 24 | 24.00 | 15.91 | 1.51x |
| DeepSeek-V4.1-Flash | 1024 | 24 | 24.00 | 15.96 | 1.50x |
| DeepSeek-V4.1-Flash | 4096 | 24 | 24.00 | 15.96 | 1.50x |
| DeepSeek-V4.1-Flash | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4.1-Flash | 2 | 28 | 9.84 | 5.77 | 1.70x |
| DeepSeek-V4.1-Flash | 4 | 28 | 16.06 | 7.76 | 2.07x |
| DeepSeek-V4.1-Flash | 8 | 28 | 22.64 | 10.00 | 2.26x |
| DeepSeek-V4.1-Flash | 16 | 28 | 26.75 | 12.33 | 2.17x |
| DeepSeek-V4.1-Flash | 32 | 28 | 27.89 | 14.50 | 1.92x |
| DeepSeek-V4.1-Flash | 64 | 28 | 28.00 | 16.26 | 1.72x |
| DeepSeek-V4.1-Flash | 256 | 28 | 28.00 | 17.80 | 1.57x |
| DeepSeek-V4.1-Flash | 1024 | 28 | 28.00 | 17.86 | 1.57x |
| DeepSeek-V4.1-Flash | 4096 | 28 | 28.00 | 17.86 | 1.57x |
| DeepSeek-V4.1-Flash | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4.1-Flash | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4.1-Flash | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4.1-Flash | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4.1-Flash | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4.1-Flash | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4.1-Flash | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4.1-Flash | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash | 4096 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash | 1 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4.1-Flash | 2 | 30 | 9.96 | 5.89 | 1.69x |
| DeepSeek-V4.1-Flash | 4 | 30 | 16.45 | 7.97 | 2.06x |
| DeepSeek-V4.1-Flash | 8 | 30 | 23.58 | 10.32 | 2.28x |
| DeepSeek-V4.1-Flash | 16 | 30 | 28.35 | 12.80 | 2.22x |
| DeepSeek-V4.1-Flash | 32 | 30 | 29.83 | 15.13 | 1.97x |
| DeepSeek-V4.1-Flash | 64 | 30 | 29.99 | 17.02 | 1.76x |
| DeepSeek-V4.1-Flash | 256 | 30 | 30.00 | 18.69 | 1.60x |
| DeepSeek-V4.1-Flash | 1024 | 30 | 30.00 | 18.76 | 1.60x |
| DeepSeek-V4.1-Flash | 4096 | 30 | 30.00 | 18.76 | 1.60x |
| DeepSeek-V4.1-Flash | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4.1-Flash | 2 | 43 | 10.51 | 6.50 | 1.62x |
| DeepSeek-V4.1-Flash | 4 | 43 | 18.23 | 9.04 | 2.02x |
| DeepSeek-V4.1-Flash | 8 | 43 | 28.24 | 12.05 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 43 | 37.25 | 15.38 | 2.42x |
| DeepSeek-V4.1-Flash | 32 | 43 | 41.80 | 18.66 | 2.24x |
| DeepSeek-V4.1-Flash | 64 | 43 | 42.86 | 21.42 | 2.00x |
| DeepSeek-V4.1-Flash | 256 | 43 | 42.99 | 23.94 | 1.80x |
| DeepSeek-V4.1-Flash | 1024 | 43 | 42.99 | 24.04 | 1.79x |
| DeepSeek-V4.1-Flash | 4096 | 43 | 42.99 | 24.04 | 1.79x |
| DeepSeek-V4.1-Flash | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4.1-Flash | 2 | 44 | 10.54 | 6.54 | 1.61x |
| DeepSeek-V4.1-Flash | 4 | 44 | 18.33 | 9.11 | 2.01x |
| DeepSeek-V4.1-Flash | 8 | 44 | 28.53 | 12.16 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 44 | 37.84 | 15.55 | 2.43x |
| DeepSeek-V4.1-Flash | 32 | 44 | 42.66 | 18.90 | 2.26x |
| DeepSeek-V4.1-Flash | 64 | 44 | 43.84 | 21.72 | 2.02x |
| DeepSeek-V4.1-Flash | 256 | 44 | 43.99 | 24.31 | 1.81x |
| DeepSeek-V4.1-Flash | 1024 | 44 | 43.99 | 24.41 | 1.80x |
| DeepSeek-V4.1-Flash | 4096 | 44 | 43.99 | 24.41 | 1.80x |
| DeepSeek-V4.1-Flash | 1 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4.1-Flash | 2 | 45 | 10.56 | 6.58 | 1.61x |
| DeepSeek-V4.1-Flash | 4 | 45 | 18.43 | 9.18 | 2.01x |
| DeepSeek-V4.1-Flash | 8 | 45 | 28.80 | 12.28 | 2.35x |
| DeepSeek-V4.1-Flash | 16 | 45 | 38.42 | 15.72 | 2.44x |
| DeepSeek-V4.1-Flash | 32 | 45 | 43.52 | 19.13 | 2.27x |
| DeepSeek-V4.1-Flash | 64 | 45 | 44.81 | 22.02 | 2.03x |
| DeepSeek-V4.1-Flash | 256 | 45 | 44.99 | 24.67 | 1.82x |
| DeepSeek-V4.1-Flash | 1024 | 45 | 44.99 | 24.78 | 1.82x |
| DeepSeek-V4.1-Flash | 4096 | 45 | 44.99 | 24.78 | 1.82x |
| DeepSeek-V4.1-Flash | 1 | 47 | 5.69 | 4.73 | 1.20x |
| DeepSeek-V4.1-Flash | 2 | 47 | 10.62 | 6.66 | 1.59x |
| DeepSeek-V4.1-Flash | 4 | 47 | 18.61 | 9.31 | 2.00x |
| DeepSeek-V4.1-Flash | 8 | 47 | 29.32 | 12.49 | 2.35x |
| DeepSeek-V4.1-Flash | 16 | 47 | 39.53 | 16.05 | 2.46x |
| DeepSeek-V4.1-Flash | 32 | 47 | 45.21 | 19.60 | 2.31x |
| DeepSeek-V4.1-Flash | 64 | 47 | 46.75 | 22.61 | 2.07x |
| DeepSeek-V4.1-Flash | 256 | 47 | 46.99 | 25.39 | 1.85x |
| DeepSeek-V4.1-Flash | 1024 | 47 | 46.99 | 25.50 | 1.84x |
| DeepSeek-V4.1-Flash | 4096 | 47 | 46.99 | 25.50 | 1.84x |
| DeepSeek-V4.1-Flash | 1 | 49 | 5.70 | 4.77 | 1.20x |
| DeepSeek-V4.1-Flash | 2 | 49 | 10.67 | 6.73 | 1.58x |
| DeepSeek-V4.1-Flash | 4 | 49 | 18.78 | 9.43 | 1.99x |
| DeepSeek-V4.1-Flash | 8 | 49 | 29.81 | 12.70 | 2.35x |
| DeepSeek-V4.1-Flash | 16 | 49 | 40.60 | 16.37 | 2.48x |
| DeepSeek-V4.1-Flash | 32 | 49 | 46.87 | 20.05 | 2.34x |
| DeepSeek-V4.1-Flash | 64 | 49 | 48.68 | 23.19 | 2.10x |
| DeepSeek-V4.1-Flash | 256 | 49 | 48.98 | 26.09 | 1.88x |
| DeepSeek-V4.1-Flash | 1024 | 49 | 48.98 | 26.21 | 1.87x |
| DeepSeek-V4.1-Flash | 4096 | 49 | 48.98 | 26.21 | 1.87x |
| DeepSeek-V4.1-Flash | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4.1-Flash | 2 | 52 | 10.73 | 6.84 | 1.57x |
| DeepSeek-V4.1-Flash | 4 | 52 | 19.02 | 9.60 | 1.98x |
| DeepSeek-V4.1-Flash | 8 | 52 | 30.49 | 12.99 | 2.35x |
| DeepSeek-V4.1-Flash | 16 | 52 | 42.12 | 16.83 | 2.50x |
| DeepSeek-V4.1-Flash | 32 | 52 | 49.28 | 20.70 | 2.38x |
| DeepSeek-V4.1-Flash | 64 | 52 | 51.54 | 24.02 | 2.15x |
| DeepSeek-V4.1-Flash | 256 | 52 | 51.97 | 27.11 | 1.92x |
| DeepSeek-V4.1-Flash | 1024 | 52 | 51.97 | 27.24 | 1.91x |
| DeepSeek-V4.1-Flash | 4096 | 52 | 51.97 | 27.24 | 1.91x |
| DeepSeek-V4.1-Flash | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash | 2 | 55 | 10.79 | 6.94 | 1.56x |
| DeepSeek-V4.1-Flash | 4 | 55 | 19.23 | 9.76 | 1.97x |
| DeepSeek-V4.1-Flash | 8 | 55 | 31.11 | 13.27 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 55 | 43.55 | 17.27 | 2.52x |
| DeepSeek-V4.1-Flash | 32 | 55 | 51.62 | 21.32 | 2.42x |
| DeepSeek-V4.1-Flash | 64 | 55 | 54.37 | 24.83 | 2.19x |
| DeepSeek-V4.1-Flash | 256 | 55 | 54.95 | 28.10 | 1.96x |
| DeepSeek-V4.1-Flash | 1024 | 55 | 54.95 | 28.23 | 1.95x |
| DeepSeek-V4.1-Flash | 4096 | 55 | 54.95 | 28.23 | 1.95x |
| DeepSeek-V4.1-Flash | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4.1-Flash | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4.1-Flash | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4.1-Flash | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4.1-Flash | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4.1-Flash | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4.1-Flash | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash | 1 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4.1-Flash | 2 | 57 | 10.83 | 7.00 | 1.55x |
| DeepSeek-V4.1-Flash | 4 | 57 | 19.36 | 9.87 | 1.96x |
| DeepSeek-V4.1-Flash | 8 | 57 | 31.50 | 13.45 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 57 | 44.46 | 17.56 | 2.53x |
| DeepSeek-V4.1-Flash | 32 | 57 | 53.13 | 21.73 | 2.45x |
| DeepSeek-V4.1-Flash | 64 | 57 | 56.24 | 25.35 | 2.22x |
| DeepSeek-V4.1-Flash | 256 | 57 | 56.93 | 28.74 | 1.98x |
| DeepSeek-V4.1-Flash | 1024 | 57 | 56.94 | 28.88 | 1.97x |
| DeepSeek-V4.1-Flash | 4096 | 57 | 56.94 | 28.88 | 1.97x |
| DeepSeek-V4.1-Flash | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4.1-Flash | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4.1-Flash | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4.1-Flash | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4.1-Flash | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4.1-Flash | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4.1-Flash | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash | 1 | 63 | 5.77 | 4.97 | 1.16x |
| DeepSeek-V4.1-Flash | 2 | 63 | 10.93 | 7.19 | 1.52x |
| DeepSeek-V4.1-Flash | 4 | 63 | 19.71 | 10.15 | 1.94x |
| DeepSeek-V4.1-Flash | 8 | 63 | 32.56 | 13.95 | 2.33x |
| DeepSeek-V4.1-Flash | 16 | 63 | 46.97 | 18.35 | 2.56x |
| DeepSeek-V4.1-Flash | 32 | 63 | 57.47 | 22.88 | 2.51x |
| DeepSeek-V4.1-Flash | 64 | 63 | 61.73 | 26.85 | 2.30x |
| DeepSeek-V4.1-Flash | 256 | 63 | 62.85 | 30.60 | 2.05x |
| DeepSeek-V4.1-Flash | 1024 | 63 | 62.86 | 30.75 | 2.04x |
| DeepSeek-V4.1-Flash | 4096 | 63 | 62.86 | 30.75 | 2.04x |
| DeepSeek-V4.1-Flash | 1 | 67 | 5.78 | 5.02 | 1.15x |
| DeepSeek-V4.1-Flash | 2 | 67 | 10.98 | 7.30 | 1.50x |
| DeepSeek-V4.1-Flash | 4 | 67 | 19.91 | 10.32 | 1.93x |
| DeepSeek-V4.1-Flash | 8 | 67 | 33.18 | 14.26 | 2.33x |
| DeepSeek-V4.1-Flash | 16 | 67 | 48.49 | 18.85 | 2.57x |
| DeepSeek-V4.1-Flash | 32 | 67 | 60.19 | 23.60 | 2.55x |
| DeepSeek-V4.1-Flash | 64 | 67 | 65.29 | 27.79 | 2.35x |
| DeepSeek-V4.1-Flash | 256 | 67 | 66.77 | 31.78 | 2.10x |
| DeepSeek-V4.1-Flash | 1024 | 67 | 66.79 | 31.94 | 2.09x |
| DeepSeek-V4.1-Flash | 4096 | 67 | 66.79 | 31.94 | 2.09x |
| DeepSeek-V4.1-Flash | 1 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4.1-Flash | 2 | 75 | 11.08 | 7.51 | 1.47x |
| DeepSeek-V4.1-Flash | 4 | 75 | 20.25 | 10.63 | 1.91x |
| DeepSeek-V4.1-Flash | 8 | 75 | 34.25 | 14.85 | 2.31x |
| DeepSeek-V4.1-Flash | 16 | 75 | 51.21 | 19.78 | 2.59x |
| DeepSeek-V4.1-Flash | 32 | 75 | 65.25 | 24.96 | 2.61x |
| DeepSeek-V4.1-Flash | 64 | 75 | 72.16 | 29.58 | 2.44x |
| DeepSeek-V4.1-Flash | 256 | 75 | 74.53 | 34.01 | 2.19x |
| DeepSeek-V4.1-Flash | 1024 | 75 | 74.57 | 34.20 | 2.18x |
| DeepSeek-V4.1-Flash | 4096 | 75 | 74.57 | 34.20 | 2.18x |
| DeepSeek-V4.1-Flash | 1 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash | 2 | 76 | 11.09 | 7.54 | 1.47x |
| DeepSeek-V4.1-Flash | 4 | 76 | 20.29 | 10.66 | 1.90x |
| DeepSeek-V4.1-Flash | 8 | 76 | 34.38 | 14.92 | 2.30x |
| DeepSeek-V4.1-Flash | 16 | 76 | 51.52 | 19.89 | 2.59x |
| DeepSeek-V4.1-Flash | 32 | 76 | 65.85 | 25.12 | 2.62x |
| DeepSeek-V4.1-Flash | 64 | 76 | 72.99 | 29.79 | 2.45x |
| DeepSeek-V4.1-Flash | 256 | 76 | 75.49 | 34.28 | 2.20x |
| DeepSeek-V4.1-Flash | 1024 | 76 | 75.53 | 34.47 | 2.19x |
| DeepSeek-V4.1-Flash | 4096 | 76 | 75.53 | 34.47 | 2.19x |
| DeepSeek-V4.1-Flash | 1 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4.1-Flash | 2 | 84 | 11.16 | 7.73 | 1.44x |
| DeepSeek-V4.1-Flash | 4 | 84 | 20.56 | 10.93 | 1.88x |
| DeepSeek-V4.1-Flash | 8 | 84 | 35.26 | 15.45 | 2.28x |
| DeepSeek-V4.1-Flash | 16 | 84 | 53.84 | 20.73 | 2.60x |
| DeepSeek-V4.1-Flash | 32 | 84 | 70.40 | 26.35 | 2.67x |
| DeepSeek-V4.1-Flash | 64 | 84 | 79.47 | 31.44 | 2.53x |
| DeepSeek-V4.1-Flash | 256 | 84 | 83.08 | 36.36 | 2.28x |
| DeepSeek-V4.1-Flash | 1024 | 84 | 83.15 | 36.57 | 2.27x |
| DeepSeek-V4.1-Flash | 4096 | 84 | 83.15 | 36.57 | 2.27x |
| DeepSeek-V4.1-Flash | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4.1-Flash | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4.1-Flash | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4.1-Flash | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4.1-Flash | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4.1-Flash | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4.1-Flash | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4.1-Flash | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash | 1 | 89 | 5.83 | 5.21 | 1.12x |
| DeepSeek-V4.1-Flash | 2 | 89 | 11.20 | 7.84 | 1.43x |
| DeepSeek-V4.1-Flash | 4 | 89 | 20.71 | 11.08 | 1.87x |
| DeepSeek-V4.1-Flash | 8 | 89 | 35.75 | 15.76 | 2.27x |
| DeepSeek-V4.1-Flash | 16 | 89 | 55.14 | 21.22 | 2.60x |
| DeepSeek-V4.1-Flash | 32 | 89 | 73.03 | 27.08 | 2.70x |
| DeepSeek-V4.1-Flash | 64 | 89 | 83.34 | 32.41 | 2.57x |
| DeepSeek-V4.1-Flash | 256 | 89 | 87.75 | 37.60 | 2.33x |
| DeepSeek-V4.1-Flash | 1024 | 89 | 87.84 | 37.82 | 2.32x |
| DeepSeek-V4.1-Flash | 4096 | 89 | 87.84 | 37.82 | 2.32x |
| DeepSeek-V4.1-Flash | 1 | 90 | 5.84 | 5.22 | 1.12x |
| DeepSeek-V4.1-Flash | 2 | 90 | 11.21 | 7.86 | 1.43x |
| DeepSeek-V4.1-Flash | 4 | 90 | 20.74 | 11.11 | 1.87x |
| DeepSeek-V4.1-Flash | 8 | 90 | 35.84 | 15.82 | 2.27x |
| DeepSeek-V4.1-Flash | 16 | 90 | 55.39 | 21.32 | 2.60x |
| DeepSeek-V4.1-Flash | 32 | 90 | 73.53 | 27.22 | 2.70x |
| DeepSeek-V4.1-Flash | 64 | 90 | 84.10 | 32.60 | 2.58x |
| DeepSeek-V4.1-Flash | 256 | 90 | 88.67 | 37.84 | 2.34x |
| DeepSeek-V4.1-Flash | 1024 | 90 | 88.77 | 38.06 | 2.33x |
| DeepSeek-V4.1-Flash | 4096 | 90 | 88.77 | 38.06 | 2.33x |
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
| DeepSeek-V4.1-Flash | 1 | 125 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 125 | 11.40 | 8.49 | 1.34x |
| DeepSeek-V4.1-Flash | 4 | 125 | 21.45 | 11.99 | 1.79x |
| DeepSeek-V4.1-Flash | 8 | 125 | 38.23 | 17.62 | 2.17x |
| DeepSeek-V4.1-Flash | 16 | 125 | 62.11 | 24.16 | 2.57x |
| DeepSeek-V4.1-Flash | 32 | 125 | 88.13 | 31.52 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 125 | 107.37 | 38.43 | 2.79x |
| DeepSeek-V4.1-Flash | 256 | 125 | 118.96 | 45.37 | 2.62x |
| DeepSeek-V4.1-Flash | 1024 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4.1-Flash | 4096 | 125 | 119.28 | 45.67 | 2.61x |
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
| DeepSeek-V4.1-Flash | 1 | 167 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 167 | 11.53 | 9.02 | 1.28x |
| DeepSeek-V4.1-Flash | 4 | 167 | 21.93 | 12.83 | 1.71x |
| DeepSeek-V4.1-Flash | 8 | 167 | 39.90 | 19.14 | 2.08x |
| DeepSeek-V4.1-Flash | 16 | 167 | 67.09 | 26.63 | 2.52x |
| DeepSeek-V4.1-Flash | 32 | 167 | 99.98 | 35.45 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 167 | 128.39 | 43.94 | 2.92x |
| DeepSeek-V4.1-Flash | 256 | 167 | 149.67 | 52.65 | 2.84x |
| DeepSeek-V4.1-Flash | 1024 | 167 | 150.36 | 53.03 | 2.84x |
| DeepSeek-V4.1-Flash | 4096 | 167 | 150.36 | 53.03 | 2.84x |
| DeepSeek-V4.1-Flash | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4.1-Flash | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4.1-Flash | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4.1-Flash | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4.1-Flash | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4.1-Flash | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4.1-Flash | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash | 1 | 179 | 5.92 | 5.57 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 179 | 11.55 | 9.15 | 1.26x |
| DeepSeek-V4.1-Flash | 4 | 179 | 22.03 | 13.04 | 1.69x |
| DeepSeek-V4.1-Flash | 8 | 179 | 40.24 | 19.48 | 2.07x |
| DeepSeek-V4.1-Flash | 16 | 179 | 68.14 | 27.23 | 2.50x |
| DeepSeek-V4.1-Flash | 32 | 179 | 102.61 | 36.43 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 179 | 133.34 | 45.30 | 2.94x |
| DeepSeek-V4.1-Flash | 256 | 179 | 157.37 | 54.48 | 2.89x |
| DeepSeek-V4.1-Flash | 1024 | 179 | 158.18 | 54.87 | 2.88x |
| DeepSeek-V4.1-Flash | 4096 | 179 | 158.18 | 54.87 | 2.88x |
| DeepSeek-V4.1-Flash | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4.1-Flash | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4.1-Flash | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4.1-Flash | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4.1-Flash | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4.1-Flash | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 347 | 11.72 | 10.18 | 1.15x |
| DeepSeek-V4.1-Flash | 4 | 347 | 22.70 | 15.30 | 1.48x |
| DeepSeek-V4.1-Flash | 8 | 347 | 42.66 | 22.28 | 1.92x |
| DeepSeek-V4.1-Flash | 16 | 347 | 75.90 | 33.59 | 2.26x |
| DeepSeek-V4.1-Flash | 32 | 347 | 123.23 | 45.96 | 2.68x |
| DeepSeek-V4.1-Flash | 64 | 347 | 175.33 | 59.00 | 2.97x |
| DeepSeek-V4.1-Flash | 256 | 347 | 230.16 | 73.28 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| DeepSeek-V4.1-Flash | 4096 | 347 | 232.44 | 73.90 | 3.15x |

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
| gpu | DeepSeek-V4.1-Flash | 1 | 860.60 | 60.8% |
| rom | DeepSeek-V4.1-Flash | 1 | 223.04 | 97.6% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash | sram | interleaved | 128 B | 1.42x |
| DeepSeek-V4.1-Flash | hbm | interleaved | 32 B | 1.12x |

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
| DeepSeek-V4.1-Flash | 1 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 2 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 4 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 8 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 16 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 32 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 64 | 1 | 0.04% | 0.33 | 15.79 |
| DeepSeek-V4.1-Flash | 256 | 1 | 0.15% | 1.34 | 15.79 |
| DeepSeek-V4.1-Flash | 1024 | 1 | 0.59% | 5.34 | 15.79 |

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
| DeepSeek-V4.1-Flash | 1 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 553.7 | 51,492.5 |
| DeepSeek-V4.1-Flash | 2 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 553.7 | 51,492.5 |
| DeepSeek-V4.1-Flash | 4 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 553.7 | 51,492.5 |
| DeepSeek-V4.1-Flash | 8 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 553.7 | 51,492.5 |
| DeepSeek-V4.1-Flash | 16 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 553.7 | 51,492.5 |
| DeepSeek-V4.1-Flash | 32 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 553.7 | 51,492.5 |
| DeepSeek-V4.1-Flash | 64 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 553.7 | 51,492.5 |
| DeepSeek-V4.1-Flash | 256 | 4.24% | 20.8 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 209.1 | 53,525.2 |
| DeepSeek-V4.1-Flash | 1024 | 15.92% | 54.5 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 53.1 | 54,359.8 |
| DeepSeek-V4.1-Flash | 4096 | 50.02% | 153.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 13.3 | 54,359.8 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | layer_fixed_latency | 578 |
| gpu | link_latency | 1054 |
| gpu | thermal | 65 |
| gpu | weight_read | 413 |
| rom | compute | 796 |
| rom | infeasible | 2140 |
| rom | kv_read | 60 |
| rom | layer_fixed_latency | 758 |
| rom | link_latency | 821 |
| rom | weight_read | 445 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2140 |

## Mechanical consistency audit

**FAIL** over 153,996 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x85', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x86', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x87', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x89', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x103', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x123', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x164', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x246', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x328', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x85', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x86', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x87', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x89', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x103', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x123', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x164', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x246', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x328', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x85', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x86', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x87', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x89', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x103', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x123', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x164', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x246', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x328', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x85', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x86', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x87', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x89', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x103', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x123', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x164', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x246', 'DeepSeek-V4.1-Flash', 1)

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

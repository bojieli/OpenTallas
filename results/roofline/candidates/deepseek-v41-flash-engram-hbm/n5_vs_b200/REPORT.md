# Area-constrained roofline: n5_vs_b200-deepseek-v41-flash-engram-hbm

> CANDIDATE MODEL under n5_vs_b200: DeepSeek-V4.1-Flash-engram-hbm at 200,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 28x (ROM-N5-native-SRAMKV-wafer-pipeline-x3-perstream, 171 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 73 devices. On the GPU side the correction reaches 3x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 29 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-hbm takes 59 x 815 mm2 (48,085 mm2, array, KV in HBM) at 3,918 tok/s per user and 81 tok/s per 1,000 mm2, holding 31,936 sessions, against 30 copies of one unified HBM die at the same silicon: 5.7x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-hbm on 138,675 mm2 of ROM silicon at 4,350 tok/s per user against 139,200 mm2 of b200_sxm-x87-nvl72-hybrid at 696 tok/s: **6.2x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 1 resident session against the GPU cluster's 75,171. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 1.91x to it.** At 113,285 mm2 on DeepSeek-V4.1-Flash-engram-hbm the pipeline-only GPU delivers 370.04 tok/s and the same silicon running tensor delivers 707 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.01x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `link_latency`) to 5.45x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-hbm engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 655 to 38,814 tok/s, and its rate with every slot occupied from 36,665 to 38,814. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 56 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 567 us over NVLink, capping per-user decode at 1,763 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 171.9 us and cap it at 5,818 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 3 of 10 operating points and an array 7; on tokens per second per square millimetre the same points go 7 to the array and 3 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 5 of 5677 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 76.7x of aggregate throughput (DeepSeek-V4.1-Flash-engram-hbm). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 18.88x, on DeepSeek-V4.1-Flash-engram-hbm at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 73 of 5,677 feasible points (1.3%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x8-pipeline` at batch 4096 on 12,800 mm2, throttled 1.08x from 20 to 18 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 87% weight read against 87.1% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-HBMKV-array-hw-hybrid-x59`** -- 59 x 815 mm2 reticle dies, 48,085 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **3,918.0 tok/s per user** (0.26 ms/token), binding on `layer_fixed_latency`
- **81.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 15,672 tok/s aggregate with every slot full, over 31,936 resident sessions (fill limited by `pipeline_slots`)
- 3,874 W at 0.081 W/mm2, 952.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 30 copies of one unified HBM die -- `b200_sxm-x30-nvl72-tensor`, 48,000 mm2, area ratio 1.0018 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 48,085 | 48,000 | 1.0018 |
| user tok/s | 3,918.0 | 690.5 | 5.67x |
| aggregate tok/s | 15,672 | 691 | 1.40x |
| resident sessions | 31,936 | 24,071 | -- |
| J/token | 0.9520 | 16.6037 | 17.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 31,936 sessions against one that holds 24,071 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x71-nvl72-tensor` at 113,600 mm2 and 706.6 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-array-hw-hybrid-x73-romfill` | 59,495 | 4,135.2 | 69.5 | 39,780 | 5.94x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,350.2 | 31.4 | 1 | 6.25x |
| smallest feasible machine | `ROM-N5-native-HBMKV-array-hw-hybrid-x56` | 45,640 | 3,382.7 | 74.1 | 30,255 | 4.91x |
| **after -- this report's rule** | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | 48,085 | 3,918.0 | 81.5 | 31,936 | 5.67x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | 48,085 | 3,918.0 | 81.5 | -- | 81.5 | ACCEPT |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 4,114.7 | 74.2 | 26.8 | 81.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 57,050 | 4,125.6 | 72.3 | 23.1 | 81.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x73-romfill` | 59,495 | 4,135.2 | 69.5 | 19.0 | 81.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x75` | 61,125 | 4,138.3 | 67.7 | 16.9 | 81.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x81` | 66,015 | 4,142.7 | 62.8 | 12.5 | 81.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x89-romfill` | 72,535 | 4,208.8 | 58.0 | 11.9 | 81.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 73,350 | 4,211.3 | 57.4 | 11.6 | 81.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x95` | 77,425 | 4,219.2 | 54.5 | 10.3 | 81.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 4,220.4 | 53.9 | 10.0 | 81.5 | stop |
| `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,327.8 | 46.8 | 9.2 | 81.5 | stop |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,350.2 | 31.4 | 4.8 | 81.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x59` **<-- recommended** | 48,085 | 59 | 3,918.0 | 15,672 | 81.5 | 31,936 | `layer_fixed_latency` | 3,874 | 952.0 | `b200_sxm-x30-nvl72-tensor` | 5.67x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 68 | 4,114.7 | 20,574 | 74.2 | 36,979 | `layer_fixed_latency` | 5,124 | 1,196.2 | `b200_sxm-x35-nvl72-tensor` | 5.92x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 57,050 | 70 | 4,125.6 | 20,628 | 72.3 | 38,099 | `layer_fixed_latency` | 5,389 | 1,257.1 | `b200_sxm-x36-nvl72-tensor` | 5.93x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x73-romfill` | 59,495 | 73 | 4,135.2 | 20,676 | 69.5 | 39,780 | `layer_fixed_latency` | 5,786 | 1,350.1 | `b200_sxm-x37-nvl72-tensor` | 5.94x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x75` | 61,125 | 75 | 4,138.3 | 20,691 | 67.7 | 40,901 | `layer_fixed_latency` | 6,051 | 1,413.0 | `b200_sxm-x38-nvl72-tensor` | 5.94x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x81` | 66,015 | 81 | 4,142.7 | 45,570 | 62.8 | 44,263 | `layer_fixed_latency` | 7,149 | 1,602.9 | `b200_sxm-x41-nvl72-tensor` | 5.93x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x89-romfill` | 72,535 | 89 | 4,208.8 | 50,506 | 58.0 | 48,745 | `layer_fixed_latency` | 8,267 | 1,829.2 | `b200_sxm-x45-nvl72-tensor` | 6.01x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 73,350 | 90 | 4,211.3 | 50,535 | 57.4 | 49,305 | `layer_fixed_latency` | 8,399 | 1,859.5 | `b200_sxm-x46-nvl72-tensor` | 6.01x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x95` | 77,425 | 95 | 4,219.2 | 50,630 | 54.5 | 52,107 | `layer_fixed_latency` | 9,062 | 2,012.7 | `b200_sxm-x48-nvl72-tensor` | 6.02x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 96 | 4,220.4 | 50,645 | 53.9 | 52,667 | `layer_fixed_latency` | 9,194 | 2,043.4 | `b200_sxm-x49-nvl72-tensor` | 6.02x |
| `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 2 | 4,327.8 | 8,656 | 46.8 | 8,515 | `layer_fixed_latency` | 9,636 | 2,214.2 | `b200_sxm-x58-nvl72-tensor` | 6.15x |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3 | 4,350.2 | 4,350 | 31.4 | 1 | `layer_fixed_latency` | 9,343 | 2,147.6 | `b200_sxm-x87-nvl72-hybrid` | 6.25x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 330 | densest | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | 48,085 | 3,918.0 | 81.5 | 31,936 |
| array | 330 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 4,220.4 | 53.9 | 52,667 |
| array | 330 | smallest | `ROM-N5-native-HBMKV-array-hw-hybrid-x56` | 45,640 | 3,382.7 | 74.1 | 30,255 |
| wafer | 69 | densest | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,327.8 | 46.8 | 8,515 |
| wafer | 69 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,350.2 | 31.4 | 1 |
| wafer | 69 | smallest | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,327.8 | 46.8 | 8,515 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 4,220.4 | 50,645 | 52,667 | 9,194 | 2,043.4 | `layer_fixed_latency` | `b200_sxm-x49-nvl72-tensor` | 701.4 | 41,104 | 25,861.5 | 0.998 | 6.02x | 12.7x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,350.2 | 4,350 | 1 | 9,343 | 2,147.6 | `layer_fixed_latency` | `b200_sxm-x87-nvl72-hybrid` | 696.4 | 75,171 | 45,157.7 | 0.996 | 6.25x | 21.0x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 132,030 | 4,183.1 | 87,845 | 89,648 | 15,212 | 3,391.0 | `layer_fixed_latency` | `b200_sxm-x83-nvl72-hybrid` | 695.5 | 71,585 | 43,202.7 | 0.994 | 6.01x | 12.7x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,350.2 | -- | 1 | -- | 2,147.6 | -- | -- | -- | -- | -- | 0.952 | 1.04x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 4,220.4 | 50,645 | 52,667 | 9,194 | 1,027.9 | `layer_fixed_latency` | `b200_sxm-x49-nvl72-tensor` | 691.5 | 41,104 | 13,343.3 | 0.998 | 6.10x | 13.0x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,327.8 | 8,656 | 8,515 | 9,636 | 1,113.3 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 694.8 | 49,172 | 15,553.3 | 0.996 | 6.23x | 14.0x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 88,020 | 4,209.9 | 58,939 | 59,391 | 10,882 | 1,218.8 | `layer_fixed_latency` | `b200_sxm-x55-nvl72-tensor` | 693.9 | 46,483 | 14,816.4 | 1.000 | 6.07x | 12.2x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,327.8 | -- | 8,515 | -- | 1,113.3 | -- | -- | -- | -- | -- | 0.952 | 1.03x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 4,220.4 | 50,645 | 52,667 | 9,194 | 520.1 | `layer_fixed_latency` | `b200_sxm-x49-nvl72-tensor` | 672.8 | 41,104 | 7,076.3 | 0.998 | 6.27x | 13.6x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,322.7 | 17,291 | 18,152 | 16,612 | 960.7 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 691.8 | 101,169 | 15,617.2 | 0.996 | 6.25x | 16.3x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x216` | 176,040 | 4,174.1 | 58,438 | 119,905 | 25,151 | 1,475.6 | `layer_fixed_latency` | `b200_sxm-x110-nvl72-hybrid` | 690.7 | 95,790 | 14,879.3 | 1.000 | 6.04x | 10.1x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,322.7 | -- | 18,152 | -- | 960.7 | -- | -- | -- | -- | -- | 0.952 | 1.04x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 4,220.4 | 50,645 | 52,667 | 9,194 | 266.2 | `layer_fixed_latency` | `b200_sxm-x49-nvl72-tensor` | 639.3 | 41,104 | 3,927.5 | 0.998 | 6.60x | 14.8x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 4,313.0 | 34,504 | 37,427 | 33,223 | 962.9 | `layer_fixed_latency` | `b200_sxm-x231-nvl72-hybrid` | 688.0 | 204,266 | 15,634.4 | 1.001 | 6.27x | 16.2x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x162-romfill` | 132,030 | 4,183.1 | 87,845 | 89,648 | 15,212 | 223.4 | `layer_fixed_latency` | `b200_sxm-x83-nvl72-hybrid` | 630.8 | 71,585 | 3,979.2 | 0.994 | 6.63x | 17.8x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,276.2 | 94,076 | 56,702 | 50,353 | 731.4 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 677.4 | 308,260 | 11,975.0 | 0.999 | 6.31x | 16.4x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 4,117.9 | 177,072 | 189,383 | 31,836 | 237.4 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 628.8 | 152,270 | 4,110.1 | 1.001 | 6.55x | 17.3x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,250.2 | 182,761 | 56,702 | 51,441 | 374.0 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 654.3 | 308,260 | 6,591.9 | 0.999 | 6.50x | 17.6x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 4,094.6 | 348,040 | 189,383 | 33,934 | 125.5 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 583.0 | 152,270 | 2,408.8 | 1.001 | 7.02x | 19.2x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,201.1 | 361,291 | 56,702 | 53,632 | 195.3 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 618.6 | 308,260 | 4,169.0 | 0.999 | 6.79x | 21.4x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,551.9 | 909,294 | 189,383 | 40,010 | 44.0 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 414.3 | 152,270 | 1,094.3 | 1.001 | 8.57x | 24.9x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,830.2 | 980,538 | 56,702 | 60,366 | 61.6 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 501.3 | 308,260 | 1,567.1 | 0.999 | 7.64x | 25.5x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,474.7 | 1,510,138 | 189,383 | 45,497 | 30.1 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 233.3 | 152,270 | 523.0 | 1.001 | 6.32x | 17.4x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 2,631.1 | 2,694,262 | 56,702 | 79,863 | 29.6 | `compute` | `b200_sxm-x347-nvl72-hybrid` | 302.6 | 308,260 | 840.0 | 0.999 | 8.69x | 28.3x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 434.2 | 1,778,552 | 189,383 | 57,317 | 32.2 | `weight_read` | `b200_sxm-x173-nvl72-hybrid` | 130.7 | 152,270 | 205.8 | 1.001 | 3.32x | 6.4x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 870.3 | 3,564,570 | 56,702 | 84,899 | 23.8 | `compute` | `b200_sxm-x347-nvl72-hybrid` | 159.6 | 308,260 | 354.1 | 0.999 | 5.45x | 14.9x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-8 | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | 48,085 | array | HBM | 31,936 |
| 16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x68` | 55,420 | array | HBM | 36,979 |
| 32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x73-romfill` | 59,495 | array | HBM | 39,780 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x89-romfill` | 72,535 | array | HBM | 48,745 |
| 256 | `ROM-N5-native-HBMKV-wafer-pipeline-x2` | 92,450 | wafer | HBM | 8,515 |
| 1024 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | wafer | HBM | 13,333 |
| 4096 | `ROM-N5-native-HBMKV-wafer-pipeline-x3` | 138,675 | wafer | HBM | 13,333 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | rom | 56, 57, 59, 68, 70, 73, 81, 89, 90, 108, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | sram | 56, 57, 59, 68, 70, 75, 81, 95, 96, 108, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | rom | 133, 139, 153, 160, 170, 192, 227, 256, 340, 345, 350, 384 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | sram | 133, 139, 153, 160, 168, 170, 192, 227, 256, 340, 384 |

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
| DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | 1 | 16 | 6.25 | hierarchical, one_shot | 233.96 | 9.45 | 49.61 | 31.05 | 3,918.0 |
| DeepSeek-V4.1-Flash-engram-hbm | `ROM-N5-native-HBMKV-array-hw-hybrid-x59` | 64 | 2 | 5.25 | one_shot, two_step | 189.23 | 7.79 | 793.77 | 14.11 | 1,051.6 |
| DeepSeek-V4.1-Flash-engram-hbm | `b200_sxm-x30-nvl72-tensor` | 1 | 30 | 6.25 | measured_floor | 860.60 | 527.73 | 67.38 | 204.69 | 690.5 |
| DeepSeek-V4.1-Flash-engram-hbm | `b200_sxm-x30-nvl72-tensor` | 64 | 30 | 6.25 | measured_floor | 860.60 | 964.53 | 1,007.76 | 370.99 | 367.4 |

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

- **73 of 5,677 feasible points (1.3%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 73.
- By area class: large array (5,000-40,000 mm2) 10, wafer (>=40,000 mm2) 63.
- By KV store: hbm 73.
- By batch: B=64 1, B=256 4, B=1024 28, B=4096 40.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 44% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 64 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 170 | 10 | 52.6% | 100.0% | 0.625 | 67% |
| gpu | wafer (>=40,000 mm2) | 2,420 | 63 | 38.5% | 100.0% | 0.625 | 91% |
| rom | large array (5,000-40,000 mm2) | 360 | 0 | 20.3% | 40.9% | 0.205 | 88% |
| rom | wafer (>=40,000 mm2) | 2,727 | 0 | 22.0% | 46.4% | 0.232 | 96% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x8-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 12,800 | hbm | 1.084x | 8,000.0 / 8,000.0 W | 35% | 18.2 | 19.7 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 22,400 | hbm | 1.070x | 14,000.0 / 14,000.0 W | 35% | 19.4 | 20.7 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x15-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 24,000 | hbm | 1.068x | 15,000.0 / 15,000.0 W | 35% | 19.5 | 20.9 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 46,400 | hbm | 1.060x | 29,000.0 / 29,000.0 W | 35% | 22.2 | 23.6 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 48,000 | hbm | 1.060x | 30,000.0 / 30,000.0 W | 35% | 22.5 | 23.8 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x8-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 1024 | 12,800 | hbm | 1.059x | 8,000.0 / 8,000.0 W | 35% | 22.9 | 24.3 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 56,000 | hbm | 1.059x | 35,000.0 / 35,000.0 W | 35% | 23.6 | 25.0 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x36-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 57,600 | hbm | 1.059x | 36,000.0 / 36,000.0 W | 35% | 23.9 | 25.3 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x37-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 59,200 | hbm | 1.058x | 37,000.0 / 37,000.0 W | 35% | 24.1 | 25.5 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x38-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 60,800 | hbm | 1.058x | 38,000.0 / 38,000.0 W | 35% | 24.4 | 25.8 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 65,600 | hbm | 1.058x | 41,000.0 / 41,000.0 W | 35% | 25.1 | 26.6 |
| `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x45-pipeline` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 72,000 | hbm | 1.057x | 45,000.0 / 45,000.0 W | 35% | 26.2 | 27.7 |

The worst point's dynamic energy is weight read 87.1%, kv read 9.4%, arithmetic 3.2%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 59,495 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x73-romfill` | 1.350128 | 5,786.1 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x37-nvl72-tensor` | 20.013377 | 13,925.8 | layer_fixed_latency | 14.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 55,420 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x68` | 0.604226 | 5,123.9 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-nvl72-tensor` | 9.909585 | 13,531.7 | layer_fixed_latency | 16.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 55,420 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x68` | 0.308249 | 5,123.9 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-nvl72-tensor` | 5.336900 | 14,105.1 | layer_fixed_latency | 17.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 57,050 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 0.168634 | 5,589.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x36-nvl72-tensor` | 3.098811 | 15,459.3 | layer_fixed_latency | 18.38x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 72,535 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x89-romfill` | 0.127725 | 8,815.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x45-hybrid` | 2.488361 | 23,421.2 | layer_fixed_latency | 17.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 78,240 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 0.077898 | 10,073.4 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x49-hybrid` | 1.693539 | 28,302.3 | layer_fixed_latency | 18.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 176,040 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 0.085186 | 21,892.1 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-nvl72-hybrid` | 1.773793 | 61,725.4 | layer_fixed_latency | 20.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 369,800 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 0.046959 | 44,021.2 | layer_fixed_latency | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-nvl72-hybrid` | 1.254889 | 145,480.1 | layer_fixed_latency | 26.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.029642 | 79,862.7 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid` | 0.839983 | 260,286.7 | weight_read | 28.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.023817 | 84,898.8 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid` | 0.354080 | 231,400.2 | link_latency | 14.87x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 92,450 | 4,333.3 | wafer-hybrid | 4,327.8 | wafer-hybrid | 1.00x | 1,065.2 | pipeline | 704.0 | tensor | 1.51x | 4.07x | 6.15x | 1.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 3 | 138,675 | 4,366.9 | wafer-hybrid | 4,350.2 | wafer-hybrid | 1.00x | 1,077.0 | pipeline | 696.4 | hybrid | 1.55x | 4.05x | 6.25x | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 184,900 | 4,350.3 | wafer-hybrid | 4,347.0 | wafer-hybrid | 1.00x | 1,083.0 | pipeline | 701.5 | hybrid | 1.54x | 4.02x | 6.20x | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 6 | 277,350 | 4,345.3 | wafer-hybrid | 4,342.7 | wafer-hybrid | 1.00x | 1,089.1 | pipeline | 699.9 | hybrid | 1.56x | 3.99x | 6.20x | 1.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 369,800 | 4,340.4 | wafer-hybrid | 4,338.1 | wafer-hybrid | 1.00x | 1,092.2 | pipeline | 698.5 | hybrid | 1.56x | 3.97x | 6.21x | 1.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 12 | 554,700 | 4,325.5 | wafer-hybrid | 4,323.4 | wafer-hybrid | 1.00x | 1,095.3 | pipeline | 699.4 | hybrid | 1.57x | 3.95x | 6.18x | 1.57x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.51x to 1.57x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 4,350.2 | 4,350.2 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-nvl72-hybrid | 139,200 | 1.00x | hybrid | 534.07 | 696.4 | 1,392.8 | layer_fixed_latency | 6.25x | 0.14x | 11.76x | 6.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,382.7 | 6,765.4 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 527.69 | 689.6 | 689.6 | layer_fixed_latency | 4.91x | 0.63x | 9.09x | 4.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,327.8 | 8,655.5 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-nvl72-tensor | 92,800 | 1.00x | tensor | 536.98 | 694.8 | 1,389.7 | layer_fixed_latency | 6.23x | 0.40x | 11.70x | 6.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,382.7 | 6,765.4 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 534.58 | 676.4 | 1,352.8 | layer_fixed_latency | 5.00x | 0.63x | 9.09x | 5.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,322.7 | 17,290.9 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-nvl72-hybrid | 185,600 | 1.00x | hybrid | 543.27 | 691.8 | 2,767.3 | layer_fixed_latency | 6.25x | 0.40x | 11.68x | 6.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,323.2 | 13,292.8 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 548.36 | 652.0 | 2,607.9 | layer_fixed_latency | 5.10x | 1.23x | 8.93x | 5.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 4,313.0 | 34,503.8 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-nvl72-hybrid | 369,600 | 1.00x | hybrid | 551.04 | 688.0 | 5,504.3 | layer_fixed_latency | 6.27x | 0.40x | 11.66x | 6.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 2,624.4 | 20,995.5 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 575.92 | 609.4 | 4,875.6 | layer_fixed_latency | 4.31x | 1.95x | 7.05x | 4.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,276.2 | 94,076.1 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 570.42 | 677.4 | 10,838.0 | layer_fixed_latency | 6.31x | 0.73x | 11.56x | 6.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 1,804.8 | 28,876.5 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 465.19 | 547.9 | 8,766.8 | layer_fixed_latency | 3.29x | 2.68x | 4.85x | 3.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,250.2 | 182,760.6 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 573.74 | 654.3 | 20,937.5 | layer_fixed_latency | 6.50x | 1.42x | 11.49x | 6.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 1,053.6 | 33,715.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 497.46 | 459.7 | 14,710.5 | layer_fixed_latency | 2.29x | 2.29x | 2.90x | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,201.1 | 361,291.4 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 492.70 | 618.6 | 39,589.0 | layer_fixed_latency | 6.79x | 2.81x | 11.35x | 6.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 577.8 | 36,977.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 961.77 | 363.7 | 23,274.5 | link_latency | 1.59x | 1.59x | 2.01x | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,830.2 | 980,538.5 | layer_fixed_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 539.95 | 501.3 | 128,342.8 | layer_fixed_latency | 7.64x | 7.64x | 10.35x | 7.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 150.8 | 38,617.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 2,326.60 | 215.8 | 55,245.0 | link_latency | 0.70x | 0.70x | 1.14x | 0.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2,631.1 | 2,694,261.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 728.97 | 302.6 | 309,871.5 | weight_read | 8.69x | 8.69x | 10.45x | 8.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 38.0 | 38,940.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 2,622.72 | 105.5 | 108,079.1 | weight_read | 0.36x | 0.36x | 0.83x | 0.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 870.3 | 3,564,570.0 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 2,900.67 | 159.6 | 653,525.2 | link_latency | 5.45x | 5.45x | 8.24x | 5.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 9.5 | 38,813.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 9,565.33 | 57.1 | 233,845.7 | link_latency | 0.17x | 0.17x | 0.43x | 0.17x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 12,800 | 430.13 | 194.39 | 660.0 | 781.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 14 | 22,400 | 526.84 | 194.54 | 659.8 | 845.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 15 | 24,000 | 526.90 | 194.55 | 663.5 | 851.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 29 | 46,400 | 527.69 | 194.64 | 689.6 | 895.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 30 | 48,000 | 527.73 | 194.64 | 690.5 | 896.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 35 | 56,000 | 527.96 | 194.65 | 694.5 | 903.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 36 | 57,600 | 528.00 | 194.65 | 695.2 | 904.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 37 | 59,200 | 528.04 | 194.66 | 695.8 | 906.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 38 | 60,800 | 528.08 | 194.66 | 696.4 | 907.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 41 | 65,600 | 528.22 | 194.66 | 698.0 | 909.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 45 | 72,000 | 528.37 | 194.67 | 699.9 | 913.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 46 | 73,600 | 528.41 | 194.67 | 700.3 | 913.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 48 | 76,800 | 528.49 | 194.67 | 701.0 | 915.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 49 | 78,400 | 528.54 | 194.67 | 701.4 | 915.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 55 | 88,000 | 528.77 | 194.68 | 703.2 | 919.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 58 | 92,800 | 528.89 | 194.68 | 704.0 | 920.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 102,400 | 529.12 | 194.69 | 705.3 | 923.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 65 | 104,000 | 529.16 | 194.69 | 705.5 | 923.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 68 | 108,800 | 529.28 | 194.69 | 706.1 | 924.5 |
| DeepSeek-V4.1-Flash-engram-hbm | 71 | 113,600 | 529.39 | 194.69 | 706.6 | 925.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 78 | 124,800 | 534.07 | 196.93 | 694.1 | 906.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 82 | 131,200 | 534.07 | 196.93 | 695.2 | 908.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 83 | 132,800 | 534.07 | 196.93 | 695.5 | 908.5 |
| DeepSeek-V4.1-Flash-engram-hbm | 86 | 137,600 | 534.07 | 196.93 | 696.2 | 909.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 87 | 139,200 | 534.07 | 196.93 | 696.4 | 910.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 98 | 156,800 | 534.07 | 196.93 | 698.7 | 914.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 105 | 168,000 | 534.07 | 196.93 | 699.9 | 916.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 110 | 176,000 | 534.07 | 196.93 | 700.6 | 917.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 116 | 185,600 | 534.07 | 196.93 | 701.5 | 918.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 130 | 208,000 | 534.37 | 196.93 | 702.9 | 921.5 |
| DeepSeek-V4.1-Flash-engram-hbm | 173 | 276,800 | 537.06 | 199.16 | 699.9 | 916.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 176 | 281,600 | 537.06 | 199.16 | 700.2 | 917.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 178 | 284,800 | 537.06 | 199.16 | 700.3 | 917.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 191 | 305,600 | 537.06 | 199.16 | 701.3 | 919.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 192 | 307,200 | 537.06 | 199.16 | 701.4 | 919.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 196 | 313,600 | 537.37 | 199.16 | 701.5 | 919.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 231 | 369,600 | 539.98 | 201.40 | 698.5 | 914.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 289 | 462,400 | 542.98 | 203.63 | 697.0 | 913.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 318 | 508,800 | 542.98 | 203.63 | 698.4 | 915.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 347 | 555,200 | 543.28 | 203.63 | 699.4 | 917.4 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 12,800 | 376.7 | 660.0 | — | tensor | 430.13 | 28.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 14 | 22,400 | 375.3 | 659.8 | 644.3 | tensor | 526.84 | 34.8% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 15 | 24,000 | 375.1 | 663.5 | 651.5 | tensor | 526.90 | 35.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 29 | 46,400 | 372.2 | 689.6 | 645.5 | tensor | 527.69 | 36.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 30 | 48,000 | 372.0 | 690.5 | 649.0 | tensor | 527.73 | 36.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 35 | 56,000 | 370.9 | 694.5 | 640.6 | tensor | 527.96 | 36.7% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 36 | 57,600 | 370.7 | 695.2 | 643.6 | tensor | 528.00 | 36.7% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 37 | 59,200 | 370.6 | 695.8 | 646.4 | tensor | 528.04 | 36.7% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 38 | 60,800 | 370.4 | 696.4 | 649.1 | tensor | 528.08 | 36.8% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 41 | 65,600 | 370.0 | 698.0 | 636.9 | tensor | 528.22 | 36.9% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 45 | 72,000 | 370.0 | 699.9 | 646.5 | tensor | 528.37 | 37.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 46 | 73,600 | 370.0 | 700.3 | 648.7 | tensor | 528.41 | 37.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 48 | 76,800 | 370.0 | 701.0 | 652.8 | tensor | 528.49 | 37.0% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 49 | 78,400 | 370.0 | 701.4 | 638.2 | tensor | 528.54 | 37.1% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 55 | 88,000 | 370.0 | 703.2 | 649.8 | tensor | 528.77 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 58 | 92,800 | 370.0 | 704.0 | 640.6 | tensor | 528.89 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 102,400 | 370.0 | 705.3 | 650.3 | tensor | 529.12 | 37.3% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 65 | 104,000 | 370.0 | 705.5 | 639.0 | tensor | 529.16 | 37.3% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 68 | 108,800 | 370.0 | 706.1 | 643.5 | tensor | 529.28 | 37.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 71 | 113,600 | 370.0 | 706.6 | 647.7 | tensor | 529.39 | 37.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 78 | 124,800 | 370.0 | 414.7 | 694.1 | hybrid | 534.07 | 37.1% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 82 | 131,200 | 370.0 | 414.6 | 695.2 | hybrid | 534.07 | 37.1% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 83 | 132,800 | 370.0 | 414.6 | 695.5 | hybrid | 534.07 | 37.1% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 86 | 137,600 | 370.0 | 414.5 | 696.2 | hybrid | 534.07 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 87 | 139,200 | 370.0 | 414.5 | 696.4 | hybrid | 534.07 | 37.2% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 98 | 156,800 | 370.0 | 414.2 | 698.7 | hybrid | 534.07 | 37.3% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 105 | 168,000 | 370.0 | 414.0 | 699.9 | hybrid | 534.07 | 37.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 110 | 176,000 | 370.0 | 413.8 | 700.6 | hybrid | 534.07 | 37.4% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 116 | 185,600 | 370.0 | 413.6 | 701.5 | hybrid | 534.07 | 37.5% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 130 | 208,000 | 370.0 | 413.0 | 702.9 | hybrid | 534.37 | 37.6% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 173 | 276,800 | 370.0 | 404.8 | 699.9 | hybrid | 537.06 | 37.6% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 176 | 281,600 | 370.0 | 404.6 | 700.2 | hybrid | 537.06 | 37.6% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 178 | 284,800 | 370.0 | 404.5 | 700.3 | hybrid | 537.06 | 37.6% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 191 | 305,600 | 370.0 | 403.6 | 701.3 | hybrid | 537.06 | 37.7% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 192 | 307,200 | 370.0 | 403.5 | 701.4 | hybrid | 537.06 | 37.7% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 196 | 313,600 | 370.0 | 403.2 | 701.5 | hybrid | 537.37 | 37.7% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 231 | 369,600 | 370.0 | 397.3 | 698.5 | hybrid | 539.98 | 37.7% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 289 | 462,400 | 370.0 | 390.5 | 697.0 | hybrid | 542.98 | 37.8% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 318 | 508,800 | 370.0 | 388.1 | 698.4 | hybrid | 542.98 | 37.9% | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 347 | 555,200 | 370.0 | 385.8 | 699.4 | hybrid | 543.28 | 38.0% | layer_fixed_latency |

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
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x168 | DeepSeek-V4.1-Flash-engram-hbm | 168 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x139 | DeepSeek-V4.1-Flash-engram-hbm | 139 | tensor | rom_package_ucie | rom_board_serdes | 160 | 91.39 us | 1,094.2 tok/s | 10,942.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 35 on rom_board_serdes (traversals 11.0) = 89.33 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x153 | DeepSeek-V4.1-Flash-engram-hbm | 153 | hybrid | rom_package_ucie | rom_board_serdes | 118 | 6.08 us | 16,455.5 tok/s | 164,555.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 38 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.02 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x168 | DeepSeek-V4.1-Flash-engram-hbm | 168 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-tensor-x133 | DeepSeek-V4.1-Flash-engram-hbm | 133 | tensor | nvlink5 | infiniband_ndr | 160 | 565.45 us | 176.9 tok/s | 1,768.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 371.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | tensor | on_wafer_n5 | rom_wafer_serdes | 160 | 171.87 us | 581.8 tok/s | 5,818.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 80 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 17.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hybrid-x153 | DeepSeek-V4.1-Flash-engram-hbm | 153 | hybrid | nvlink5 | infiniband_ndr | 99 | 236.85 us | 422.2 tok/s | 4,222.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 42.46 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | hybrid | on_wafer_n5 | rom_wafer_serdes | 82 | 154.20 us | 648.5 tok/s | 6,484.9 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x96 | DeepSeek-V4.1-Flash-engram-hbm | 96 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x59 | DeepSeek-V4.1-Flash-engram-hbm | 59 | tensor | rom_package_ucie | rom_board_serdes | 160 | 56.14 us | 1,781.4 tok/s | 17,814.2 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 15 on rom_board_serdes (traversals 6.6) = 54.07 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x75 | DeepSeek-V4.1-Flash-engram-hbm | 75 | hybrid | rom_package_ucie | rom_board_serdes | 98 | 3.96 us | 25,232.1 tok/s | 252,321.4 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 18 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-pipeline-x95 | DeepSeek-V4.1-Flash-engram-hbm | 95 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-tensor-x56 | DeepSeek-V4.1-Flash-engram-hbm | 56 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hybrid-x70 | DeepSeek-V4.1-Flash-engram-hbm | 70 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x8-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.48 us | 11,792.9 tok/s | 117,929.5 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x8-tensor | DeepSeek-V4.1-Flash-engram-hbm | 8 | tensor | nvlink5 | infiniband_ndr | 80 | 194.39 us | 514.4 tok/s | 5,144.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x8-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 8 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.39 us | 514.4 tok/s | 5,144.3 tok/s | 80 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 194.39 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x8-expert | DeepSeek-V4.1-Flash-engram-hbm | 8 | expert | nvlink5 | infiniband_ndr | 160 | 291.07 us | 343.6 tok/s | 3,435.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x point_to_point span 2 on nvlink5 (traversals 1.0) = 96.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x8-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 8 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 291.07 us | 343.6 tok/s | 3,435.6 tok/s | 80 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 194.39 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 16.77 us | 5,962.6 tok/s | 59,625.6 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 14.54 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-tensor | DeepSeek-V4.1-Flash-engram-hbm | 14 | tensor | nvlink5 | infiniband_ndr | 160 | 543.77 us | 183.9 tok/s | 1,839.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 14 | hybrid | nvlink5 | infiniband_ndr | 81 | 196.62 us | 508.6 tok/s | 5,085.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 14 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.54 us | 514.0 tok/s | 5,140.4 tok/s | 80 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 194.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-expert | DeepSeek-V4.1-Flash-engram-hbm | 14 | expert | nvlink5 | infiniband_ndr | 160 | 363.81 us | 274.9 tok/s | 2,748.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 169.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x14-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 14 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.93 us | 343.7 tok/s | 3,437.3 tok/s | 80 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 194.54 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.39 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x15-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 15 | pipeline | nvlink5 | infiniband_ndr | 14 | 17.98 us | 5,560.9 tok/s | 55,609.0 tok/s | 13 x point_to_point span 2 on nvlink5 (traversals 1.0) = 15.75 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x15-tensor | DeepSeek-V4.1-Flash-engram-hbm | 15 | tensor | nvlink5 | infiniband_ndr | 160 | 543.77 us | 183.9 tok/s | 1,839.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x15-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 15 | hybrid | nvlink5 | infiniband_ndr | 81 | 196.62 us | 508.6 tok/s | 5,085.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x15-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 15 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.55 us | 514.0 tok/s | 5,140.1 tok/s | 80 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 194.55 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x15-expert | DeepSeek-V4.1-Flash-engram-hbm | 15 | expert | nvlink5 | infiniband_ndr | 160 | 363.34 us | 275.2 tok/s | 2,752.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 168.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x15-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 15 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.91 us | 343.7 tok/s | 3,437.5 tok/s | 80 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 194.55 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.36 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 35 | pipeline | nvlink5 | infiniband_ndr | 34 | 45.28 us | 2,208.5 tok/s | 22,084.5 tok/s | 30 x point_to_point span 2 on nvlink5 (traversals 1.0) = 36.34 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-tensor | DeepSeek-V4.1-Flash-engram-hbm | 35 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 35 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 35 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.65 us | 513.7 tok/s | 5,137.4 tok/s | 80 x all_reduce span 35 on nvlink5_nvl72 (traversals 2.0) = 194.65 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-expert | DeepSeek-V4.1-Flash-engram-hbm | 35 | expert | nvlink5 | infiniband_ndr | 160 | 357.81 us | 279.5 tok/s | 2,794.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 35 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.81 us | 343.9 tok/s | 3,438.7 tok/s | 80 x all_reduce span 35 on nvlink5_nvl72 (traversals 2.0) = 194.65 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x36-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 36 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.49 us | 2,150.9 tok/s | 21,509.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.55 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x36-tensor | DeepSeek-V4.1-Flash-engram-hbm | 36 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x36-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 36 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x36-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 36 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.65 us | 513.7 tok/s | 5,137.3 tok/s | 80 x all_reduce span 36 on nvlink5_nvl72 (traversals 2.0) = 194.65 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x36-expert | DeepSeek-V4.1-Flash-engram-hbm | 36 | expert | nvlink5 | infiniband_ndr | 160 | 357.73 us | 279.5 tok/s | 2,795.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.13 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x36-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 36 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.81 us | 343.9 tok/s | 3,438.7 tok/s | 80 x all_reduce span 36 on nvlink5_nvl72 (traversals 2.0) = 194.65 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.15 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x37-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 37 | pipeline | nvlink5 | infiniband_ndr | 36 | 47.70 us | 2,096.3 tok/s | 20,962.9 tok/s | 32 x point_to_point span 2 on nvlink5 (traversals 1.0) = 38.76 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x37-tensor | DeepSeek-V4.1-Flash-engram-hbm | 37 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x37-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 37 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x37-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 37 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.2 tok/s | 80 x all_reduce span 37 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x37-expert | DeepSeek-V4.1-Flash-engram-hbm | 37 | expert | nvlink5 | infiniband_ndr | 160 | 357.65 us | 279.6 tok/s | 2,796.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x37-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 37 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.7 tok/s | 80 x all_reduce span 37 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.15 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x38-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 48.91 us | 2,044.4 tok/s | 20,443.8 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 39.98 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x38-tensor | DeepSeek-V4.1-Flash-engram-hbm | 38 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x38-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 38 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x38-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.2 tok/s | 80 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x38-expert | DeepSeek-V4.1-Flash-engram-hbm | 38 | expert | nvlink5 | infiniband_ndr | 160 | 357.58 us | 279.7 tok/s | 2,796.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x38-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 38 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 41 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-tensor | DeepSeek-V4.1-Flash-engram-hbm | 41 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 41 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 41 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.1 tok/s | 80 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-expert | DeepSeek-V4.1-Flash-engram-hbm | 41 | expert | nvlink5 | infiniband_ndr | 160 | 357.28 us | 279.9 tok/s | 2,799.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.80 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 41 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.13 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x45-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 45 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x45-tensor | DeepSeek-V4.1-Flash-engram-hbm | 45 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x45-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 45 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x45-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 45 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.9 tok/s | 80 x all_reduce span 45 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x45-expert | DeepSeek-V4.1-Flash-engram-hbm | 45 | expert | nvlink5 | infiniband_ndr | 160 | 357.06 us | 280.1 tok/s | 2,800.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x45-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 45 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 45 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 46 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-tensor | DeepSeek-V4.1-Flash-engram-hbm | 46 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 46 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.9 tok/s | 80 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-expert | DeepSeek-V4.1-Flash-engram-hbm | 46 | expert | nvlink5 | infiniband_ndr | 160 | 357.01 us | 280.1 tok/s | 2,801.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x48-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 48 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x48-tensor | DeepSeek-V4.1-Flash-engram-hbm | 48 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x48-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 48 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x48-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 48 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.8 tok/s | 80 x all_reduce span 48 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x48-expert | DeepSeek-V4.1-Flash-engram-hbm | 48 | expert | nvlink5 | infiniband_ndr | 160 | 356.85 us | 280.2 tok/s | 2,802.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.45 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x48-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 48 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 48 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.11 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x49-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 49 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x49-tensor | DeepSeek-V4.1-Flash-engram-hbm | 49 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x49-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 49 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x49-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 49 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.8 tok/s | 80 x all_reduce span 49 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x49-expert | DeepSeek-V4.1-Flash-engram-hbm | 49 | expert | nvlink5 | infiniband_ndr | 160 | 356.80 us | 280.3 tok/s | 2,802.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.41 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x49-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 49 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 49 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.11 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 65 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-tensor | DeepSeek-V4.1-Flash-engram-hbm | 65 | tensor | nvlink5 | infiniband_ndr | 160 | 562.88 us | 177.7 tok/s | 1,776.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 368.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 65 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 65 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 65 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-expert | DeepSeek-V4.1-Flash-engram-hbm | 65 | expert | nvlink5 | infiniband_ndr | 160 | 356.21 us | 280.7 tok/s | 2,807.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 65 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 65 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.08 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x78-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 78 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x78-tensor | DeepSeek-V4.1-Flash-engram-hbm | 78 | tensor | nvlink5 | infiniband_ndr | 160 | 563.43 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 369.04 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x78-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 78 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x78-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 78 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x78-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 78 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x78-expert | DeepSeek-V4.1-Flash-engram-hbm | 78 | expert | nvlink5 | infiniband_ndr | 160 | 355.93 us | 281.0 tok/s | 2,809.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.27 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x78-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 78 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.35 us | 279.1 tok/s | 2,790.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.66 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x86-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 86 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x86-tensor | DeepSeek-V4.1-Flash-engram-hbm | 86 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x86-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 86 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x86-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 86 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x86-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 86 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x86-expert | DeepSeek-V4.1-Flash-engram-hbm | 86 | expert | nvlink5 | infiniband_ndr | 160 | 355.78 us | 281.1 tok/s | 2,810.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x86-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 86 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.24 us | 279.1 tok/s | 2,791.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.54 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x105-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 105 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x105-tensor | DeepSeek-V4.1-Flash-engram-hbm | 105 | tensor | nvlink5 | infiniband_ndr | 160 | 564.83 us | 177.0 tok/s | 1,770.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 370.44 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x105-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 105 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.44 us | 447.5 tok/s | 4,475.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 29.05 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x105-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 105 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x105-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 105 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x105-expert | DeepSeek-V4.1-Flash-engram-hbm | 105 | expert | nvlink5 | infiniband_ndr | 160 | 355.52 us | 281.3 tok/s | 2,812.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.18 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.34 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x105-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 105 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.03 us | 279.3 tok/s | 2,793.1 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.34 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x176-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 176 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x176-tensor | DeepSeek-V4.1-Flash-engram-hbm | 176 | tensor | nvlink5 | infiniband_ndr | 160 | 566.11 us | 176.6 tok/s | 1,766.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 371.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x176-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 176 | hybrid | nvlink5 | infiniband_ndr | 101 | 241.32 us | 414.4 tok/s | 4,143.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x176-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 176 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x176-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 176 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x176-expert | DeepSeek-V4.1-Flash-engram-hbm | 176 | expert | nvlink5 | infiniband_ndr | 160 | 355.07 us | 281.6 tok/s | 2,816.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.11 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x176-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 176 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.30 us | 280.7 tok/s | 2,806.6 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x178-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 178 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x178-tensor | DeepSeek-V4.1-Flash-engram-hbm | 178 | tensor | nvlink5 | infiniband_ndr | 160 | 566.20 us | 176.6 tok/s | 1,766.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 23 on infiniband_ndr (traversals 2.0) = 371.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x178-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 178 | hybrid | nvlink5 | infiniband_ndr | 102 | 243.55 us | 410.6 tok/s | 4,105.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 22 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 49.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x178-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 178 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x178-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 178 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x178-expert | DeepSeek-V4.1-Flash-engram-hbm | 178 | expert | nvlink5 | infiniband_ndr | 160 | 355.06 us | 281.6 tok/s | 2,816.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.11 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x178-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 178 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.30 us | 280.7 tok/s | 2,806.6 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x191-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 191 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x191-tensor | DeepSeek-V4.1-Flash-engram-hbm | 191 | tensor | nvlink5 | infiniband_ndr | 160 | 566.29 us | 176.6 tok/s | 1,765.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 371.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x191-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 191 | hybrid | nvlink5 | infiniband_ndr | 103 | 245.79 us | 406.9 tok/s | 4,068.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 51.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x191-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 191 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x191-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 191 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x191-expert | DeepSeek-V4.1-Flash-engram-hbm | 191 | expert | nvlink5 | infiniband_ndr | 160 | 355.02 us | 281.7 tok/s | 2,816.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x191-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 191 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.26 us | 280.7 tok/s | 2,806.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 192 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-tensor | DeepSeek-V4.1-Flash-engram-hbm | 192 | tensor | nvlink5 | infiniband_ndr | 160 | 566.29 us | 176.6 tok/s | 1,765.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 371.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 192 | hybrid | nvlink5 | infiniband_ndr | 103 | 245.79 us | 406.9 tok/s | 4,068.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 51.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 192 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 192 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-expert | DeepSeek-V4.1-Flash-engram-hbm | 192 | expert | nvlink5 | infiniband_ndr | 160 | 355.01 us | 281.7 tok/s | 2,816.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x192-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 192 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.26 us | 280.7 tok/s | 2,807.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x289-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 289 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x289-tensor | DeepSeek-V4.1-Flash-engram-hbm | 289 | tensor | nvlink5 | infiniband_ndr | 160 | 567.01 us | 176.4 tok/s | 1,763.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 37 on infiniband_ndr (traversals 2.0) = 372.62 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x289-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 289 | hybrid | nvlink5 | infiniband_ndr | 116 | 274.84 us | 363.8 tok/s | 3,638.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 36 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 80.45 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x289-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 289 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 558.81 us | 179.0 tok/s | 1,789.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x289-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 289 | hybrid | nvlink5_nvl72 | infiniband_ndr | 84 | 203.63 us | 491.1 tok/s | 4,910.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x289-expert | DeepSeek-V4.1-Flash-engram-hbm | 289 | expert | nvlink5 | infiniband_ndr | 160 | 354.81 us | 281.8 tok/s | 2,818.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.07 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.74 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x289-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 289 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.41 us | 281.4 tok/s | 2,813.6 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.67 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.74 us |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x73-romfill | 59,495 | 4,135.2 | 0.070 | 4,114.7 (55,420) | 4,327.8 (92,450) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 4,114.7 | 0.074 | 4,114.7 (55,420) | 4,327.8 (92,450) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 4,114.7 | 0.074 | 4,114.7 (55,420) | 4,317.7 (92,450) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x70 | 57,050 | 4,105.7 | 0.072 | 4,084.3 (55,420) | 4,291.7 (92,450) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x89-romfill | 72,535 | 4,139.7 | 0.057 | 3,977.2 (57,050) | 4,181.7 (92,450) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 4,041.1 | 0.052 | 3,993.4 (72,535) | 4,088.6 (138,675) | 1.02x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill | 176,040 | 4,015.5 | 0.023 | 3,904.9 (88,020) | 4,052.8 (277,350) | 1.04x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,661.9 | 0.010 | 3,551.9 (277,100) | 3,661.9 (369,800) | 1.03x | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2,631.1 | 0.005 | 1,474.7 (277,100) | 2,631.1 (554,700) | 1.78x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 870.3 | 0.002 | 428.3 (176,040) | 870.3 (554,700) | 2.03x | compute |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | sram | 582,987.7 | 26,113.2 | 26,113.2 | 22.33x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | sram | 582,987.7 | 26,113.2 | 26,113.2 | 22.33x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | sram | 582,987.7 | 26,113.2 | 26,113.2 | 22.33x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | sram | 582,987.7 | 26,113.2 | 28,623.1 | 22.33x | 1.10x | weight_read | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | sram | 582,987.7 | 26,113.2 | 45,034.1 | 22.33x | 1.72x | weight_read | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | sram | 582,987.7 | 26,113.2 | 71,128.6 | 22.33x | 2.72x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | sram | 582,987.7 | 26,113.2 | 104,589.7 | 22.33x | 4.01x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | sram | 716,627.0 | 26,113.2 | 202,144.8 | 27.44x | 7.74x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | sram | 1,303,001.3 | 26,113.2 | 318,255.5 | 49.90x | 12.19x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | sram | 2,001,952.5 | 26,113.2 | 493,015.0 | 76.66x | 18.88x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | rom | 2,205,396.0 | 108,309.7 | 108,309.7 | 20.36x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | rom | 2,205,396.0 | 108,309.7 | 108,309.7 | 20.36x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | rom | 2,205,396.0 | 108,309.7 | 108,309.7 | 20.36x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | rom | 2,205,396.0 | 108,309.7 | 108,309.7 | 20.36x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | rom | 2,205,396.0 | 108,309.7 | 108,309.7 | 20.36x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | rom | 2,205,396.0 | 108,309.7 | 116,435.0 | 20.36x | 1.08x | layer_fixed_latency | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | rom | 2,205,396.0 | 108,309.7 | 184,801.7 | 20.36x | 1.71x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | rom | 2,205,396.0 | 115,391.7 | 383,964.3 | 19.11x | 3.33x | layer_fixed_latency | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | rom | 2,694,261.6 | 116,097.5 | 726,621.0 | 23.21x | 6.26x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | rom | 3,564,570.0 | 116,097.5 | 1,013,875.5 | 30.70x | 8.73x | compute | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 582,987.7 | 1.051 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 2,205,396.0 | 3.976 | layer_fixed_latency | 3.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 582,987.7 | 1.051 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 2,205,396.0 | 3.976 | layer_fixed_latency | 3.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 582,987.7 | 1.051 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 2,205,396.0 | 3.976 | layer_fixed_latency | 3.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 582,987.7 | 1.051 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 2,205,396.0 | 3.976 | layer_fixed_latency | 3.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.43 | 28,623.1 | 0.310 | layer_fixed_latency | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 582,987.7 | 1.051 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 2,205,396.0 | 3.976 | layer_fixed_latency | 3.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.99 | 45,034.1 | 0.487 | layer_fixed_latency | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 582,987.7 | 1.051 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 2,205,396.0 | 3.976 | layer_fixed_latency | 3.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.18 | 71,128.6 | 0.513 | weight_read | 0.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 4.45 | 1.43 | 116,435.0 | 1.259 | layer_fixed_latency | 0.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 582,987.7 | 1.051 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 2,205,396.0 | 3.976 | layer_fixed_latency | 3.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 1.00 | 108,309.7 | 1.172 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.54 | 104,589.7 | 1.131 | weight_read | 0.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 4.45 | 1.48 | 184,801.7 | 1.999 | weight_read | 0.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 716,627.0 | 1.292 | layer_fixed_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 2,205,396.0 | 3.976 | layer_fixed_latency | 3.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x28-perstream | 22,820 | 1.00 | 9.14 | 26,113.2 | 1.144 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 2.25 | 115,391.7 | 1.248 | weight_read | 0.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 4.02 | 202,144.8 | 1.458 | weight_read | 0.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 4.45 | 2.62 | 383,964.3 | 4.153 | layer_fixed_latency | 0.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,303,001.3 | 2.349 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 2,694,261.6 | 4.857 | compute | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x28-perstream | 22,820 | 1.00 | 36.57 | 26,113.2 | 1.144 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 8.98 | 116,097.5 | 1.256 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 5.09 | 318,255.5 | 3.442 | weight_read | 0.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 4.45 | 3.65 | 726,621.0 | 7.860 | kv_read | 0.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 2,001,952.5 | 3.609 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,564,570.0 | 6.426 | compute | 1.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x28-perstream | 22,820 | 1.00 | 146.29 | 26,113.2 | 1.144 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 4.45 | 35.93 | 116,097.5 | 1.256 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 11.43 | 493,015.0 | 5.333 | weight_read | 0.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 4.45 | 3.69 | 1,013,875.5 | 10.967 | kv_read | 0.51x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 171 | 1.50 | 1.004 | 1.043 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 28 | 36.57 | 1.305 | 3.718 | 2.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 28 | 146.29 | 2.539 | 7.780 | 3.06x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 8 | 6.37 | 3.69 | 1.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 8 | 7.65 | 4.39 | 1.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 8 | 7.98 | 5.05 | 1.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 8 | 8.00 | 5.63 | 1.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 8 | 8.00 | 6.09 | 1.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 8 | 8.00 | 6.42 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 8 | 8.00 | 6.68 | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 8 | 8.00 | 6.69 | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 8 | 8.00 | 6.69 | 1.20x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 15 | 8.40 | 4.73 | 1.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 15 | 12.02 | 6.00 | 2.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 15 | 14.35 | 7.31 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 15 | 14.96 | 8.56 | 1.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 15 | 15.00 | 9.64 | 1.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 15 | 15.00 | 10.46 | 1.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 15 | 15.00 | 11.14 | 1.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 15 | 15.00 | 11.16 | 1.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 15 | 15.00 | 11.16 | 1.34x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 37 | 10.30 | 6.24 | 1.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 37 | 17.54 | 8.59 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 37 | 26.35 | 11.32 | 2.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 37 | 33.45 | 14.27 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 37 | 36.43 | 17.13 | 2.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 37 | 36.95 | 19.50 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 37 | 37.00 | 21.63 | 1.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 37 | 37.00 | 21.72 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 37 | 37.00 | 21.72 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 38 | 10.34 | 6.29 | 1.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 38 | 17.66 | 8.67 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 38 | 26.69 | 11.45 | 2.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 38 | 34.12 | 14.46 | 2.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 38 | 37.34 | 17.39 | 2.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 38 | 37.94 | 19.83 | 1.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 38 | 38.00 | 22.03 | 1.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 38 | 38.00 | 22.12 | 1.72x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 45 | 10.56 | 6.58 | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 45 | 18.43 | 9.18 | 2.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 45 | 28.80 | 12.28 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 45 | 38.42 | 15.72 | 2.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 45 | 43.52 | 19.13 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 45 | 44.81 | 22.02 | 2.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 45 | 44.99 | 24.67 | 1.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 45 | 44.99 | 24.78 | 1.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 45 | 44.99 | 24.78 | 1.82x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 48 | 10.64 | 6.69 | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 48 | 18.70 | 9.37 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 48 | 29.57 | 12.59 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 48 | 40.07 | 16.21 | 2.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 48 | 46.04 | 19.82 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 48 | 47.72 | 22.90 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 48 | 47.98 | 25.74 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 48 | 47.99 | 25.86 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 48 | 47.99 | 25.86 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 49 | 5.70 | 4.77 | 1.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 49 | 10.67 | 6.73 | 1.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 49 | 18.78 | 9.43 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 49 | 29.81 | 12.70 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 49 | 40.60 | 16.37 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 49 | 46.87 | 20.05 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 49 | 48.68 | 23.19 | 2.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 49 | 48.98 | 26.09 | 1.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 49 | 48.98 | 26.21 | 1.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 49 | 48.98 | 26.21 | 1.87x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 65 | 5.77 | 4.99 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 65 | 10.96 | 7.25 | 1.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 65 | 19.81 | 10.23 | 1.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 65 | 32.87 | 14.11 | 2.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 65 | 47.74 | 18.61 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 65 | 58.84 | 23.24 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 65 | 63.52 | 27.33 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 65 | 64.81 | 31.19 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 65 | 64.83 | 31.35 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 65 | 64.83 | 31.35 | 2.07x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 78 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 78 | 11.11 | 7.59 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 78 | 20.36 | 10.73 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 78 | 34.61 | 15.05 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 78 | 52.13 | 20.11 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 78 | 67.03 | 25.44 | 2.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 78 | 74.65 | 30.21 | 2.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 78 | 77.40 | 34.82 | 2.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 78 | 77.45 | 35.01 | 2.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 78 | 77.45 | 35.01 | 2.21x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 105 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 105 | 11.31 | 8.16 | 1.39x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 105 | 21.10 | 11.52 | 1.83x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 105 | 37.04 | 16.66 | 2.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 105 | 58.68 | 22.66 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 105 | 80.48 | 29.21 | 2.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 105 | 94.82 | 35.27 | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 105 | 102.16 | 41.27 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 105 | 102.34 | 41.53 | 2.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 105 | 102.34 | 41.53 | 2.46x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 176 | 5.92 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 176 | 11.54 | 9.12 | 1.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 176 | 22.01 | 12.99 | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 176 | 40.16 | 19.39 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 176 | 67.89 | 27.08 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 176 | 101.98 | 36.19 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 176 | 132.14 | 44.97 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 176 | 155.48 | 54.03 | 2.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 176 | 156.26 | 54.42 | 2.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 176 | 156.26 | 54.42 | 2.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 178 | 5.92 | 5.57 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 178 | 11.55 | 9.14 | 1.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 178 | 22.02 | 13.02 | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 178 | 40.21 | 19.45 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 178 | 68.06 | 27.18 | 2.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 178 | 102.41 | 36.35 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 178 | 132.94 | 45.19 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 178 | 156.74 | 54.33 | 2.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 178 | 157.54 | 54.72 | 2.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 178 | 157.54 | 54.72 | 2.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 191 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 191 | 11.57 | 9.26 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 191 | 22.12 | 13.24 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 191 | 40.55 | 19.78 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 191 | 69.09 | 27.80 | 2.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 191 | 105.00 | 37.36 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 191 | 137.90 | 46.60 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 191 | 164.63 | 56.21 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 191 | 165.55 | 56.63 | 2.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 191 | 165.55 | 56.63 | 2.92x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 289 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 289 | 11.68 | 9.92 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 289 | 22.56 | 14.64 | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 289 | 42.13 | 21.55 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 289 | 74.15 | 31.75 | 2.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 289 | 118.36 | 43.43 | 2.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 289 | 164.88 | 55.14 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 289 | 210.82 | 67.86 | 3.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 289 | 212.64 | 68.42 | 3.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 289 | 212.64 | 68.42 | 3.11x |
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
| gpu | DeepSeek-V4.1-Flash-engram-hbm | 1 | 860.60 | 60.8% |
| rom | DeepSeek-V4.1-Flash-engram-hbm | 1 | 225.56 | 98.1% |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 133 | 0.09% | 0.50 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 126 | 0.09% | 0.47 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 126 | 0.09% | 0.47 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 3 | 0.06% | 0.45 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 3 | 0.06% | 0.45 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 3 | 0.06% | 0.45 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 3 | 0.06% | 0.45 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 3 | 0.09% | 0.67 | 4.24 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 654.7 | 36,665.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 654.7 | 36,665.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 654.7 | 36,665.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 654.7 | 36,665.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 654.7 | 36,665.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 654.7 | 36,665.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 1.78% | 13.7 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 577.8 | 36,977.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 6.95% | 28.6 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 150.8 | 38,617.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 25.02% | 80.8 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 38.0 | 38,940.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 68.40% | 206.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 9.5 | 38,813.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | layer_fixed_latency | 684 |
| gpu | link_latency | 1334 |
| gpu | thermal | 73 |
| gpu | weight_read | 499 |
| rom | compute | 783 |
| rom | infeasible | 2283 |
| rom | kv_read | 5 |
| rom | layer_fixed_latency | 906 |
| rom | link_latency | 842 |
| rom | weight_read | 551 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2283 |

## Mechanical consistency audit

**FAIL** over 173,236 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x133', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x139', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x153', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x133', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x139', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x153', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x133', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x139', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x153', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x133', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x139', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x153', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x168', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-tensor-x133', 'DeepSeek-V4.1-Flash-engram-hbm', 1)

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

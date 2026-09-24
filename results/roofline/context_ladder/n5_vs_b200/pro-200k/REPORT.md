# Area-constrained roofline: n5_vs_b200-pro-200k

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Pro-0813 at 200,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 344x (ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream, 568 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 80 devices. On the GPU side the correction reaches 54x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 56 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Pro-0813 takes 154 x 815 mm2 (125,510 mm2, array, KV in SRAM) at 4,829 tok/s per user and 38 tok/s per 1,000 mm2, holding 1 session, against 78 copies of one unified HBM die at the same silicon: 2.3x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 251,020 mm2 of ROM silicon at 6,308 tok/s per user against 251,200 mm2 of b200_sxm-x157-nvl72-hybrid at 2,277 tok/s: **2.8x**, ROM binding on `weight_read` and the GPU on `link_latency`. It holds 15,769 resident sessions against the GPU cluster's 12,409. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 15.84x to it.** At 214,345 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 153.65 tok/s and the same silicon running hybrid delivers 2,434 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`) to 1.94x (DeepSeek-V4-Pro-0813, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Pro-0813 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 279 to 46,545 tok/s, and its rate with every slot occupied from 46,301 to 46,545. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 166 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 896 us over NVLink, capping per-user decode at 1,116 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 316.2 us and cap it at 3,163 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 71 of 4339 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 33.7x of aggregate throughput (DeepSeek-V4-Pro-0813). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 26.21x, on DeepSeek-V4-Pro-0813 at batch 4096, where the busiest region carries 3.07x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 289 of 4,339 feasible points (6.7%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x81-perregion-romfill` at batch 4096 on 66,015 mm2, throttled 1.11x from 131 to 118 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 88% kv read against 0.3% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x154`** -- 154 x 815 mm2 reticle dies, 125,510 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **4,829.2 tok/s per user** (0.21 ms/token), binding on `link_latency`
- **38.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,829 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 7,794 W at 0.062 W/mm2, 1,613.9 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 78 copies of one unified HBM die -- `b200_sxm-x78-nvl72-hybrid`, 124,800 mm2, area ratio 1.0057 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 125,510 | 124,800 | 1.0057 |
| user tok/s | 4,829.2 | 2,095.1 | 2.30x |
| aggregate tok/s | 4,829 | 4,190 | 0.40x |
| resident sessions | 1 | 5,938 | -- |
| J/token | 1.6139 | 17.2742 | 10.7x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 5,938 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x134-nvl72-hybrid` at 214,400 mm2 and 2,433.5 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-array-hw-hybrid-x299` | 243,685 | 6,192.9 | 25.4 | 15,308 | 2.74x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 25.1 | 15,769 | 2.77x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x154` | 125,510 | 4,829.2 | 38.5 | 1 | 2.30x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x154` | 125,510 | 4,829.2 | 38.5 | 1 | 2.30x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x154` | 125,510 | 4,829.2 | 38.5 | -- | 38.5 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x170` | 138,550 | 5,158.4 | 37.2 | 25.2 | 38.5 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x172` | 140,180 | 5,175.0 | 36.9 | 23.6 | 38.5 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 146,700 | 5,223.8 | 35.6 | 18.6 | 38.5 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x238` | 193,970 | 5,583.4 | 28.8 | 11.0 | 38.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x300` | 244,500 | 6,228.2 | 25.5 | 11.8 | 38.5 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 25.1 | 11.8 | 38.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x154` **<-- recommended** | 125,510 | 154 | 4,829.2 | 4,829 | 38.5 | 1 | `link_latency` | 7,794 | 1,613.9 | `b200_sxm-x78-nvl72-hybrid` | 2.30x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x170` | 138,550 | 170 | 5,158.4 | 5,158 | 37.2 | 1 | `link_latency` | 8,600 | 1,667.3 | `b200_sxm-x87-nvl72-hybrid` | 2.38x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x172` | 140,180 | 172 | 5,175.0 | 5,175 | 36.9 | 1 | `link_latency` | 8,701 | 1,681.3 | `b200_sxm-x88-nvl72-hybrid` | 2.38x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 146,700 | 180 | 5,223.8 | 5,224 | 35.6 | 1 | `link_latency` | 9,359 | 1,791.5 | `b200_sxm-x92-nvl72-hybrid` | 2.37x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x238` | 193,970 | 238 | 5,583.4 | 5,583 | 28.8 | 1 | `compute` | 16,220 | 2,905.0 | `b200_sxm-x121-nvl72-hybrid` | 2.35x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x300` | 244,500 | 300 | 6,228.2 | 467,118 | 25.5 | 15,359 | `compute` | 59,403 | 4,515.8 | `b200_sxm-x153-nvl72-hybrid` | 2.75x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 308 | 6,308.0 | 485,716 | 25.1 | 15,769 | `weight_read` | 61,722 | 4,627.2 | `b200_sxm-x157-nvl72-hybrid` | 2.77x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 264 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x154` | 125,510 | 4,829.2 | 38.5 | 1 |
| array | 264 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 25.1 | 15,769 |
| array | 264 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x154` | 125,510 | 4,829.2 | 38.5 | 1 |
| wafer | 42 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,580.0 | 25.8 | 1 |
| wafer | 42 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 3,784.7 | 20.5 | 1 |
| wafer | 42 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,580.0 | 25.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 485,716 | 15,769 | 61,722 | 4,627.2 | `weight_read` | `b200_sxm-x157-nvl72-hybrid` | 2,277.1 | 12,409 | 28,389.3 | 0.999 | 2.77x | 6.1x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 3,784.7 | 3,785 | 1 | 14,869 | 3,928.9 | `link_latency` | `b200_sxm-x116-nvl72-hybrid` | 2,351.4 | 9,050 | 21,515.2 | 0.996 | 1.61x | 5.5x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x238` | 193,970 | 5,583.4 | 5,583 | 1 | 16,220 | 2,905.0 | `compute` | `b200_sxm-x121-nvl72-hybrid` | 2,376.1 | 9,460 | 22,073.3 | 1.002 | 2.35x | 7.6x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 3,784.7 | -- | 1 | -- | 3,928.9 | -- | -- | -- | -- | -- | 1.049 | 0.68x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 485,716 | 15,769 | 61,722 | 2,347.5 | `weight_read` | `b200_sxm-x157-nvl72-hybrid` | 2,277.1 | 12,409 | 16,308.4 | 0.999 | 2.77x | 6.9x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 3,745.8 | 37,458 | 4,403 | 43,541 | 5,540.5 | `link_latency` | `b200_sxm-x289-nvl72-hybrid` | 2,311.6 | 23,222 | 26,133.3 | 1.000 | 1.62x | 4.7x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 485,716 | 15,769 | 61,722 | 1,207.7 | `weight_read` | `b200_sxm-x157-nvl72-hybrid` | 2,201.6 | 12,409 | 9,766.8 | 0.999 | 2.87x | 8.1x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 3,745.8 | 37,458 | 4,403 | 43,541 | 2,804.2 | `link_latency` | `b200_sxm-x289-nvl72-hybrid` | 2,311.6 | 23,222 | 15,180.4 | 1.000 | 1.62x | 5.4x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 485,716 | 15,769 | 61,722 | 637.8 | `weight_read` | `b200_sxm-x157-nvl72-hybrid` | 1,946.2 | 12,409 | 5,981.7 | 0.999 | 3.24x | 9.4x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 3,745.8 | 37,458 | 4,403 | 43,541 | 1,436.0 | `link_latency` | `b200_sxm-x289-nvl72-hybrid` | 2,184.3 | 23,222 | 8,959.5 | 1.000 | 1.71x | 6.2x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 485,716 | 15,769 | 61,722 | 352.8 | `weight_read` | `b200_sxm-x157-nvl72-hybrid` | 1,587.3 | 12,409 | 4,058.3 | 0.999 | 3.97x | 11.5x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,680.5 | 58,887 | 5,283 | 53,072 | 901.2 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 2,026.6 | 27,973 | 6,016.4 | 0.999 | 1.82x | 6.7x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 485,716 | 15,769 | 61,722 | 210.3 | `weight_read` | `b200_sxm-x157-nvl72-hybrid` | 1,175.5 | 12,409 | 3,037.7 | 0.999 | 5.37x | 14.4x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,450.0 | 110,401 | 5,283 | 76,839 | 696.0 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,654.8 | 27,973 | 4,089.4 | 0.999 | 2.08x | 5.9x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 6,308.0 | 485,716 | 15,769 | 61,722 | 139.1 | `weight_read` | `b200_sxm-x157-nvl72-hybrid` | 800.1 | 12,409 | 2,420.5 | 0.999 | 7.88x | 17.4x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,066.1 | 196,230 | 5,283 | 81,892 | 417.3 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,229.1 | 27,973 | 3,056.6 | 0.999 | 2.49x | 7.3x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 2,584.2 | 661,564 | 17,407 | 74,170 | 112.1 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 376.0 | 13,720 | 1,469.5 | 1.001 | 6.87x | 11.7x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,838.5 | 470,657 | 5,283 | 97,867 | 207.9 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 556.5 | 27,973 | 1,900.8 | 0.999 | 3.30x | 8.5x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 277,100 | 691.3 | 707,939 | 17,407 | 77,057 | 108.8 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 193.6 | 13,720 | 624.2 | 1.001 | 3.57x | 4.2x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 844.4 | 864,661 | 5,283 | 105,455 | 122.0 | `kv_read` | `b200_sxm-x347-expert` | 267.1 | 27,404 | 589.8 | 0.999 | 3.16x | 4.8x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 277,100 | 174.6 | 715,192 | 17,407 | 75,838 | 106.0 | `compute` | `b200_sxm-x173-expert` | 90.1 | 13,448 | 244.2 | 1.001 | 1.94x | 2.3x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 554,700 | 214.5 | 878,618 | 5,283 | 123,327 | 140.4 | `kv_read` | `b200_sxm-x347-expert` | 151.2 | 27,404 | 276.2 | 0.999 | 1.42x | 2.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x154` | 125,510 | array | SRAM | 1 |
| 2-4 | `ROM-N5-native-HBMKV-array-hw-tensor-x180` | 146,700 | array | HBM | 9,215 |
| 8-64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x300` | 244,500 | array | HBM | 15,359 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | array | HBM | 17,407 |
| 1024-4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 277,100 | array | HBM | 17,407 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro-0813 | HBM | rom | 166, 170, 180, 193, 227, 231, 232, 262, 263, 308, 340 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 166, 170, 180, 193, 227, 231, 238, 299, 300, 308, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 154, 170, 172, 180, 215, 216, 227, 237, 238, 288, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 154, 170, 172, 180, 215, 216, 227, 237, 238, 288, 340 |

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

- **289 of 4,339 feasible points (6.7%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 284, rom 5.
- By area class: wafer (>=40,000 mm2) 289.
- By KV store: hbm 289.
- By batch: B=1 29, B=2 29, B=4 29, B=8 29, B=16 29, B=32 29, B=64 29, B=256 30, B=1024 29, B=4096 27.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 44% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,897 | 284 | 53.5% | 100.0% | 0.625 | 66% |
| rom | wafer (>=40,000 mm2) | 2,442 | 5 | 23.1% | 100.0% | 0.500 | 77% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x81-perregion-romfill` | DeepSeek-V4-Pro-0813 | 4096 | 66,015 | hbm | 1.108x | 33,007.5 / 33,007.5 W | 18% | 117.8 | 130.6 |
| `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x83-perregion-romfill` | DeepSeek-V4-Pro-0813 | 4096 | 67,645 | hbm | 1.108x | 33,822.5 / 33,822.5 W | 18% | 120.7 | 133.7 |
| `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x81-perregion` | DeepSeek-V4-Pro-0813 | 4096 | 66,015 | hbm | 1.105x | 33,007.5 / 33,007.5 W | 18% | 117.8 | 130.2 |
| `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x85-perregion-romfill` | DeepSeek-V4-Pro-0813 | 4096 | 69,275 | hbm | 1.089x | 34,637.5 / 34,637.5 W | 18% | 123.6 | 134.6 |
| `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x91-perregion-romfill` | DeepSeek-V4-Pro-0813 | 4096 | 74,165 | hbm | 1.070x | 37,082.5 / 37,082.5 W | 18% | 132.3 | 141.5 |
| `DSV4-Pro/b200_sxm-x56-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 89,600 | hbm | 1.055x | 56,000.0 / 56,000.0 W | 35% | 9.8 | 10.4 |
| `DSV4-Pro/b200_sxm-x58-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 92,800 | hbm | 1.055x | 58,000.0 / 58,000.0 W | 35% | 10.0 | 10.6 |
| `DSV4-Pro/b200_sxm-x29-pipeline` | DeepSeek-V4-Pro-0813 | 1024 | 46,400 | hbm | 1.054x | 29,000.0 / 29,000.0 W | 35% | 15.6 | 16.4 |
| `DSV4-Pro/b200_sxm-x78-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 124,800 | hbm | 1.054x | 78,000.0 / 78,000.0 W | 35% | 11.9 | 12.6 |
| `DSV4-Pro/b200_sxm-x85-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 136,000 | hbm | 1.054x | 85,000.0 / 85,000.0 W | 35% | 12.6 | 13.3 |
| `DSV4-Pro/b200_sxm-x87-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 139,200 | hbm | 1.053x | 87,000.0 / 87,000.0 W | 35% | 12.8 | 13.5 |
| `DSV4-Pro/b200_sxm-x88-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 140,800 | hbm | 1.053x | 88,000.0 / 88,000.0 W | 35% | 12.9 | 13.6 |

The worst point's dynamic energy is kv read 88.4%, arithmetic 10.4%, operand delivery 1.0%, weight read 0.3%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4-Pro-0813 | 1 | 243,685 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299` | 4.519866 | 59,090.6 | compute | `DSV4-Pro/b200_sxm-x152-nvl72-hybrid` | 27.827207 | 81,892.0 | link_latency | 6.16x |
| DeepSeek-V4-Pro-0813 | 2 | 243,685 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299` | 2.293864 | 59,090.6 | compute | `DSV4-Pro/b200_sxm-x152-nvl72-hybrid` | 16.027322 | 81,892.0 | link_latency | 6.99x |
| DeepSeek-V4-Pro-0813 | 4 | 243,685 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299` | 1.180864 | 59,090.6 | compute | `DSV4-Pro/b200_sxm-x152-nvl72-hybrid` | 9.625342 | 83,965.1 | link_latency | 8.15x |
| DeepSeek-V4-Pro-0813 | 8 | 243,685 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299` | 0.624363 | 59,090.6 | compute | `DSV4-Pro/b200_sxm-x152-nvl72-hybrid` | 5.909142 | 90,938.4 | link_latency | 9.46x |
| DeepSeek-V4-Pro-0813 | 16 | 243,685 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299` | 0.346113 | 59,090.6 | compute | `DSV4-Pro/b200_sxm-x152-nvl72-hybrid` | 4.020135 | 100,617.0 | link_latency | 11.62x |
| DeepSeek-V4-Pro-0813 | 32 | 243,685 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299` | 0.206988 | 59,090.6 | compute | `DSV4-Pro/b200_sxm-x152-nvl72-hybrid` | 3.016760 | 111,455.5 | weight_read | 14.57x |
| DeepSeek-V4-Pro-0813 | 64 | 243,685 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299` | 0.137425 | 59,090.6 | compute | `DSV4-Pro/b200_sxm-x152-nvl72-hybrid` | 2.408210 | 120,763.9 | weight_read | 17.52x |
| DeepSeek-V4-Pro-0813 | 256 | 277,100 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 0.112113 | 74,169.9 | compute | `DSV4-Pro/b200_sxm-x173-nvl72-hybrid` | 1.469489 | 141,430.8 | weight_read | 11.74x |
| DeepSeek-V4-Pro-0813 | 1024 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.121961 | 105,455.2 | kv_read | `DSV4-Pro/b200_sxm-x347-expert` | 0.589813 | 161,320.4 | weight_read | 4.84x |
| DeepSeek-V4-Pro-0813 | 4096 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12` | 0.140365 | 123,327.0 | kv_read | `DSV4-Pro/b200_sxm-x347-expert` | 0.276186 | 171,070.4 | link_latency | 1.97x |

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
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 29,434.6 | wafer-pipeline | 3,580.0 | wafer-hybrid | 8.22x | 5,705.4 | pipeline | 2,169.8 | hybrid | 2.63x | 5.16x | 1.65x | 0.32x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 35,779.0 | wafer-pipeline | 3,784.7 | wafer-hybrid | 9.45x | 6,375.0 | pipeline | 2,351.4 | hybrid | 2.71x | 5.61x | 1.61x | 0.29x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 36,297.7 | wafer-pipeline | 3,734.7 | wafer-hybrid | 9.72x | 7,211.6 | pipeline | 2,335.3 | hybrid | 3.09x | 5.03x | 1.60x | 0.32x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 36,297.7 | wafer-pipeline | 3,664.4 | wafer-hybrid | 9.91x | 7,729.9 | pipeline | 2,323.6 | hybrid | 3.33x | 4.70x | 1.58x | 0.34x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 38,143.6 | wafer-pipeline | 3,743.0 | wafer-hybrid | 10.19x | 8,326.7 | pipeline | 2,411.5 | hybrid | 3.45x | 4.58x | 1.55x | 0.34x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.29x to 0.34x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x308 | 251,020 | 6,308.0 | 485,715.8 | weight_read | DSV4-Pro/b200_sxm-x157-nvl72-hybrid | 251,200 | 1.00x | hybrid | 303.18 | 2,277.1 | 6,831.3 | link_latency | 2.77x | 20.13x | 41.05x | 2.77x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x154 | 125,510 | 4,829.2 | 4,829.2 | link_latency | DSV4-Pro/b200_sxm-x78-nvl72-hybrid | 124,800 | 1.01x | hybrid | 300.87 | 2,095.1 | 4,190.2 | link_latency | 2.30x | 0.40x | 31.43x | 2.30x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x308 | 251,020 | 6,308.0 | 485,715.8 | weight_read | DSV4-Pro/b200_sxm-x157-nvl72-hybrid | 251,200 | 1.00x | hybrid | 303.18 | 2,277.1 | 6,831.3 | link_latency | 2.77x | 20.13x | 41.05x | 2.77x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x166 | 135,290 | 4,315.9 | 8,631.8 | link_latency | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 300.87 | 2,154.1 | 4,308.3 | link_latency | 2.00x | 0.66x | 28.09x | 2.00x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x308 | 251,020 | 6,308.0 | 485,715.8 | weight_read | DSV4-Pro/b200_sxm-x157-nvl72-hybrid | 251,200 | 1.00x | hybrid | 305.29 | 2,201.6 | 8,806.3 | link_latency | 2.87x | 20.13x | 41.05x | 2.87x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x166 | 135,290 | 3,542.1 | 14,168.4 | link_latency | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 306.90 | 1,930.9 | 7,723.7 | link_latency | 1.83x | 1.08x | 23.05x | 1.83x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x308 | 251,020 | 6,308.0 | 485,715.8 | weight_read | DSV4-Pro/b200_sxm-x157-nvl72-hybrid | 251,200 | 1.00x | hybrid | 313.72 | 1,946.2 | 15,569.2 | link_latency | 3.24x | 20.13x | 41.05x | 3.24x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x166 | 135,290 | 2,607.2 | 20,857.9 | link_latency | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 318.97 | 1,604.9 | 12,839.5 | link_latency | 1.62x | 1.60x | 16.97x | 1.62x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x308 | 251,020 | 6,308.0 | 485,715.8 | weight_read | DSV4-Pro/b200_sxm-x157-nvl72-hybrid | 251,200 | 1.00x | hybrid | 330.58 | 1,587.3 | 25,396.6 | link_latency | 3.97x | 19.13x | 41.05x | 3.97x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x166 | 135,290 | 1,706.5 | 27,303.3 | compute | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 343.12 | 1,211.8 | 19,389.3 | weight_read | 1.41x | 1.41x | 11.11x | 1.41x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x308 | 251,020 | 6,308.0 | 485,715.8 | weight_read | DSV4-Pro/b200_sxm-x157-nvl72-hybrid | 251,200 | 1.00x | hybrid | 364.30 | 1,175.5 | 37,615.2 | weight_read | 5.37x | 12.91x | 41.05x | 5.37x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x166 | 135,290 | 1,078.1 | 45,280.9 | compute | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 391.40 | 834.2 | 26,694.7 | weight_read | 1.29x | 1.70x | 7.02x | 1.29x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x308 | 251,020 | 6,308.0 | 485,715.8 | weight_read | DSV4-Pro/b200_sxm-x157-nvl72-hybrid | 251,200 | 1.00x | hybrid | 431.74 | 800.1 | 51,203.3 | weight_read | 7.88x | 9.49x | 41.05x | 7.88x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x166 | 135,290 | 713.9 | 45,689.8 | compute | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 487.97 | 543.6 | 34,790.8 | weight_read | 1.31x | 1.31x | 4.65x | 1.31x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 2,584.2 | 661,564.2 | compute | DSV4-Pro/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 836.38 | 376.0 | 96,244.9 | weight_read | 6.87x | 6.87x | 19.48x | 6.87x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x166 | 135,290 | 181.2 | 46,390.2 | compute | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 1,067.40 | 250.7 | 64,166.6 | weight_read | 0.72x | 0.72x | 1.95x | 0.72x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 844.4 | 864,661.3 | kv_read | DSV4-Pro/b200_sxm-x347-expert | 555,200 | 1.00x | expert | 1,281.30 | 267.1 | 273,510.9 | weight_read | 3.16x | 3.16x | 8.99x | 3.16x |
| DeepSeek-V4-Pro-0813 | 1024 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x166 | 135,290 | 45.4 | 46,513.8 | compute | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 3,385.12 | 135.8 | 139,059.6 | link_latency | 0.33x | 0.33x | 1.29x | 0.33x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 214.5 | 878,617.7 | kv_read | DSV4-Pro/b200_sxm-x347-expert | 555,200 | 1.00x | expert | 3,503.80 | 151.2 | 619,402.5 | link_latency | 1.42x | 1.42x | 6.00x | 1.42x |
| DeepSeek-V4-Pro-0813 | 4096 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x166 | 135,290 | 11.4 | 46,544.8 | compute | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 12,655.99 | 51.9 | 212,509.6 | link_latency | 0.22x | 0.22x | 0.90x | 0.22x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 298.43 | 298.43 | 1,888.1 | 1,888.1 |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 298.48 | 298.48 | 2,087.3 | 2,087.3 |
| DeepSeek-V4-Pro-0813 | 40 | 64,000 | 298.48 | 298.48 | 2,123.4 | 2,123.4 |
| DeepSeek-V4-Pro-0813 | 41 | 65,600 | 298.49 | 298.49 | 2,140.5 | 2,140.5 |
| DeepSeek-V4-Pro-0813 | 42 | 67,200 | 298.49 | 298.49 | 2,157.1 | 2,157.1 |
| DeepSeek-V4-Pro-0813 | 43 | 68,800 | 298.49 | 298.49 | 2,173.2 | 2,173.2 |
| DeepSeek-V4-Pro-0813 | 46 | 73,600 | 298.50 | 298.50 | 2,218.4 | 2,218.4 |
| DeepSeek-V4-Pro-0813 | 56 | 89,600 | 298.53 | 298.53 | 2,343.3 | 2,343.3 |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 298.53 | 298.53 | 2,364.4 | 2,364.4 |
| DeepSeek-V4-Pro-0813 | 78 | 124,800 | 300.87 | 300.87 | 2,095.1 | 2,095.1 |
| DeepSeek-V4-Pro-0813 | 85 | 136,000 | 300.87 | 300.87 | 2,154.1 | 2,154.1 |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 300.87 | 300.87 | 2,169.8 | 2,169.8 |
| DeepSeek-V4-Pro-0813 | 88 | 140,800 | 300.87 | 300.87 | 2,177.4 | 2,177.4 |
| DeepSeek-V4-Pro-0813 | 92 | 147,200 | 300.87 | 300.87 | 2,206.9 | 2,206.9 |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 300.87 | 300.87 | 2,247.7 | 2,247.7 |
| DeepSeek-V4-Pro-0813 | 110 | 176,000 | 300.87 | 300.87 | 2,319.7 | 2,319.7 |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 300.87 | 300.87 | 2,351.4 | 2,351.4 |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 300.87 | 300.87 | 2,361.5 | 2,361.5 |
| DeepSeek-V4-Pro-0813 | 121 | 193,600 | 300.87 | 300.87 | 2,376.1 | 2,376.1 |
| DeepSeek-V4-Pro-0813 | 133 | 212,800 | 300.87 | 300.87 | 2,429.4 | 2,429.4 |
| DeepSeek-V4-Pro-0813 | 134 | 214,400 | 300.87 | 300.87 | 2,433.5 | 2,433.5 |
| DeepSeek-V4-Pro-0813 | 147 | 235,200 | 303.18 | 303.18 | 2,236.1 | 2,236.1 |
| DeepSeek-V4-Pro-0813 | 152 | 243,200 | 303.18 | 303.18 | 2,257.1 | 2,257.1 |
| DeepSeek-V4-Pro-0813 | 153 | 244,800 | 303.18 | 303.18 | 2,261.2 | 2,261.2 |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 303.18 | 303.18 | 2,277.1 | 2,277.1 |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 303.18 | 303.18 | 2,335.3 | 2,335.3 |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 305.50 | 305.50 | 2,323.6 | 2,323.6 |
| DeepSeek-V4-Pro-0813 | 289 | 462,400 | 307.82 | 307.82 | 2,311.6 | 2,311.6 |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 307.82 | 307.82 | 2,411.5 | 2,411.5 |

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
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 153.7 | 1,888.1 | 849.7 | tensor | 298.43 | 56.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 153.7 | 2,087.3 | 877.3 | tensor | 298.48 | 62.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 40 | 64,000 | 153.7 | 2,123.4 | 909.9 | tensor | 298.48 | 63.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 41 | 65,600 | 153.7 | 2,140.5 | 810.6 | tensor | 298.49 | 63.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 42 | 67,200 | 153.7 | 2,157.1 | 825.1 | tensor | 298.49 | 64.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 43 | 68,800 | 153.7 | 2,173.2 | 839.3 | tensor | 298.49 | 64.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 46 | 73,600 | 153.7 | 2,218.4 | 881.0 | tensor | 298.50 | 66.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 56 | 89,600 | 153.7 | 2,343.3 | 906.0 | tensor | 298.53 | 70.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 153.7 | 2,364.4 | 843.1 | tensor | 298.53 | 70.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 78 | 124,800 | 153.7 | 1,060.0 | 2,095.1 | hybrid | 300.87 | 63.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 85 | 136,000 | 153.7 | 1,067.4 | 2,154.1 | hybrid | 300.87 | 64.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 153.7 | 1,069.4 | 2,169.8 | hybrid | 300.87 | 65.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 88 | 140,800 | 153.7 | 1,070.3 | 2,177.4 | hybrid | 300.87 | 65.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 92 | 147,200 | 153.7 | 1,073.8 | 2,206.9 | hybrid | 300.87 | 66.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 153.7 | 1,078.6 | 2,247.7 | hybrid | 300.87 | 67.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 110 | 176,000 | 153.7 | 1,086.7 | 2,319.7 | hybrid | 300.87 | 69.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 153.7 | 1,090.1 | 2,351.4 | hybrid | 300.87 | 70.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 153.7 | 1,091.2 | 2,361.5 | hybrid | 300.87 | 71.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 121 | 193,600 | 153.7 | 1,092.7 | 2,376.1 | hybrid | 300.87 | 71.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 133 | 212,800 | 153.7 | 1,098.3 | 2,429.4 | hybrid | 300.87 | 73.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 134 | 214,400 | 153.7 | 1,098.7 | 2,433.5 | hybrid | 300.87 | 73.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 147 | 235,200 | 153.7 | 1,082.7 | 2,236.1 | hybrid | 303.18 | 67.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 152 | 243,200 | 153.7 | 1,084.4 | 2,257.1 | hybrid | 303.18 | 68.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 153 | 244,800 | 153.7 | 1,084.7 | 2,261.2 | hybrid | 303.18 | 68.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 153.7 | 1,085.9 | 2,277.1 | hybrid | 303.18 | 69.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 153.7 | 1,090.2 | 2,335.3 | hybrid | 303.18 | 70.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 153.7 | 1,090.5 | 2,323.6 | hybrid | 305.50 | 71.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 289 | 462,400 | 153.7 | 1,090.7 | 2,311.6 | hybrid | 307.82 | 71.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 153.7 | 1,095.0 | 2,411.5 | hybrid | 307.82 | 74.2% | link_latency |

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
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x237 | DeepSeek-V4-Pro-0813 | 237 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x172 | DeepSeek-V4-Pro-0813 | 172 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.31 us | 597.7 tok/s | 5,976.9 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 43 on rom_board_serdes (traversals 13.2) = 163.89 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x238 | DeepSeek-V4-Pro-0813 | 238 | hybrid | rom_package_ucie | rom_board_serdes | 181 | 9.79 us | 10,210.6 tok/s | 102,106.3 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 59 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.37 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x237 | DeepSeek-V4-Pro-0813 | 237 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x4 | DeepSeek-V4-Pro-0813 | 4 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x154 | DeepSeek-V4-Pro-0813 | 154 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 262.35 us | 381.2 tok/s | 3,811.8 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 27.50 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x215 | DeepSeek-V4-Pro-0813 | 215 | hybrid | nvlink5 | infiniband_ndr | 148 | 358.14 us | 279.2 tok/s | 2,792.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 26 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 60.23 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x4 | DeepSeek-V4-Pro-0813 | 4 | hybrid | on_wafer_n5 | rom_wafer_serdes | 125 | 235.16 us | 425.2 tok/s | 4,252.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x300 | DeepSeek-V4-Pro-0813 | 300 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x180 | DeepSeek-V4-Pro-0813 | 180 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.31 us | 597.7 tok/s | 5,976.8 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 45 on rom_board_serdes (traversals 13.2) = 163.89 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299 | DeepSeek-V4-Pro-0813 | 299 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x300 | DeepSeek-V4-Pro-0813 | 300 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10 | DeepSeek-V4-Pro-0813 | 10 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x166 | DeepSeek-V4-Pro-0813 | 166 | tensor | nvlink5 | infiniband_ndr | 244 | 893.16 us | 112.0 tok/s | 1,119.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 595.26 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x10 | DeepSeek-V4-Pro-0813 | 10 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 316.16 us | 316.3 tok/s | 3,163.0 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 10 on rom_wafer_serdes (traversals 6.6) = 81.31 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x238 | DeepSeek-V4-Pro-0813 | 238 | hybrid | nvlink5 | infiniband_ndr | 151 | 365.09 us | 273.9 tok/s | 2,739.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 29 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 67.18 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10 | DeepSeek-V4-Pro-0813 | 10 | hybrid | on_wafer_n5 | rom_wafer_serdes | 131 | 235.77 us | 424.1 tok/s | 4,241.4 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 9 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.92 us |
| DSV4-Pro/b200_sxm-x29-pipeline | DeepSeek-V4-Pro-0813 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.35 us | 2,677.5 tok/s | 26,774.9 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.40 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5 | infiniband_ndr | 244 | 871.93 us | 114.7 tok/s | 1,146.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x29-hybrid | DeepSeek-V4-Pro-0813 | 29 | hybrid | nvlink5 | infiniband_ndr | 125 | 304.85 us | 328.0 tok/s | 3,280.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-nvl72-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.43 us | 335.1 tok/s | 3,350.9 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us |
| DSV4-Pro/b200_sxm-x29-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5 | infiniband_ndr | 244 | 549.40 us | 182.0 tok/s | 1,820.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 294.50 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 254.90 us |
| DSV4-Pro/b200_sxm-x29-nvl72-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.23 us | 224.6 tok/s | 2,246.0 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.80 us |
| DSV4-Pro/b200_sxm-x38-pipeline | DeepSeek-V4-Pro-0813 | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 49.39 us | 2,024.6 tok/s | 20,246.0 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 40.13 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x38-tensor | DeepSeek-V4-Pro-0813 | 38 | tensor | nvlink5 | infiniband_ndr | 244 | 877.17 us | 114.0 tok/s | 1,140.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x38-hybrid | DeepSeek-V4-Pro-0813 | 38 | hybrid | nvlink5 | infiniband_ndr | 126 | 307.17 us | 325.6 tok/s | 3,255.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x38-nvl72-tensor | DeepSeek-V4-Pro-0813 | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.48 us | 335.0 tok/s | 3,350.3 tok/s | 122 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 298.48 us |
| DSV4-Pro/b200_sxm-x38-expert | DeepSeek-V4-Pro-0813 | 38 | expert | nvlink5 | infiniband_ndr | 244 | 547.26 us | 182.7 tok/s | 1,827.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 294.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 253.18 us |
| DSV4-Pro/b200_sxm-x38-nvl72-expert | DeepSeek-V4-Pro-0813 | 38 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.18 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 298.48 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.71 us |
| DSV4-Pro/b200_sxm-x40-pipeline | DeepSeek-V4-Pro-0813 | 40 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.82 us | 1,929.6 tok/s | 19,295.9 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.56 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x40-tensor | DeepSeek-V4-Pro-0813 | 40 | tensor | nvlink5 | infiniband_ndr | 244 | 877.17 us | 114.0 tok/s | 1,140.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x40-hybrid | DeepSeek-V4-Pro-0813 | 40 | hybrid | nvlink5 | infiniband_ndr | 126 | 307.17 us | 325.6 tok/s | 3,255.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x40-nvl72-tensor | DeepSeek-V4-Pro-0813 | 40 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.48 us | 335.0 tok/s | 3,350.3 tok/s | 122 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 298.48 us |
| DSV4-Pro/b200_sxm-x40-expert | DeepSeek-V4-Pro-0813 | 40 | expert | nvlink5 | infiniband_ndr | 244 | 546.73 us | 182.9 tok/s | 1,829.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.91 us |
| DSV4-Pro/b200_sxm-x40-nvl72-expert | DeepSeek-V4-Pro-0813 | 40 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.18 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 298.48 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.69 us |
| DSV4-Pro/b200_sxm-x41-pipeline | DeepSeek-V4-Pro-0813 | 41 | pipeline | nvlink5 | infiniband_ndr | 40 | 54.14 us | 1,847.0 tok/s | 18,470.3 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.56 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x41-tensor | DeepSeek-V4-Pro-0813 | 41 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x41-hybrid | DeepSeek-V4-Pro-0813 | 41 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x41-nvl72-tensor | DeepSeek-V4-Pro-0813 | 41 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.49 us | 335.0 tok/s | 3,350.2 tok/s | 122 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 298.49 us |
| DSV4-Pro/b200_sxm-x41-expert | DeepSeek-V4-Pro-0813 | 41 | expert | nvlink5 | infiniband_ndr | 244 | 546.60 us | 182.9 tok/s | 1,829.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.78 us |
| DSV4-Pro/b200_sxm-x41-nvl72-expert | DeepSeek-V4-Pro-0813 | 41 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.17 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 298.49 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.68 us |
| DSV4-Pro/b200_sxm-x42-pipeline | DeepSeek-V4-Pro-0813 | 42 | pipeline | nvlink5 | infiniband_ndr | 41 | 55.36 us | 1,806.5 tok/s | 18,064.5 tok/s | 36 x point_to_point span 2 on nvlink5 (traversals 1.0) = 43.77 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x42-tensor | DeepSeek-V4-Pro-0813 | 42 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x42-hybrid | DeepSeek-V4-Pro-0813 | 42 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x42-nvl72-tensor | DeepSeek-V4-Pro-0813 | 42 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.49 us | 335.0 tok/s | 3,350.2 tok/s | 122 x all_reduce span 42 on nvlink5_nvl72 (traversals 2.0) = 298.49 us |
| DSV4-Pro/b200_sxm-x42-expert | DeepSeek-V4-Pro-0813 | 42 | expert | nvlink5 | infiniband_ndr | 244 | 546.48 us | 183.0 tok/s | 1,829.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.66 us |
| DSV4-Pro/b200_sxm-x42-nvl72-expert | DeepSeek-V4-Pro-0813 | 42 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.17 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 42 on nvlink5_nvl72 (traversals 2.0) = 298.49 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.68 us |
| DSV4-Pro/b200_sxm-x43-pipeline | DeepSeek-V4-Pro-0813 | 43 | pipeline | nvlink5 | infiniband_ndr | 42 | 56.57 us | 1,767.6 tok/s | 17,676.3 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.99 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x43-tensor | DeepSeek-V4-Pro-0813 | 43 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x43-hybrid | DeepSeek-V4-Pro-0813 | 43 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x43-nvl72-tensor | DeepSeek-V4-Pro-0813 | 43 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.49 us | 335.0 tok/s | 3,350.1 tok/s | 122 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 298.49 us |
| DSV4-Pro/b200_sxm-x43-expert | DeepSeek-V4-Pro-0813 | 43 | expert | nvlink5 | infiniband_ndr | 244 | 546.36 us | 183.0 tok/s | 1,830.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.54 us |
| DSV4-Pro/b200_sxm-x43-nvl72-expert | DeepSeek-V4-Pro-0813 | 43 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.17 us | 224.6 tok/s | 2,246.4 tok/s | 122 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 298.49 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.67 us |
| DSV4-Pro/b200_sxm-x46-pipeline | DeepSeek-V4-Pro-0813 | 46 | pipeline | nvlink5 | infiniband_ndr | 45 | 60.22 us | 1,660.6 tok/s | 16,605.6 tok/s | 40 x point_to_point span 2 on nvlink5 (traversals 1.0) = 48.64 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x46-tensor | DeepSeek-V4-Pro-0813 | 46 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x46-hybrid | DeepSeek-V4-Pro-0813 | 46 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x46-nvl72-tensor | DeepSeek-V4-Pro-0813 | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.50 us | 335.0 tok/s | 3,350.0 tok/s | 122 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 298.50 us |
| DSV4-Pro/b200_sxm-x46-expert | DeepSeek-V4-Pro-0813 | 46 | expert | nvlink5 | infiniband_ndr | 244 | 546.04 us | 183.1 tok/s | 1,831.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.22 us |
| DSV4-Pro/b200_sxm-x46-nvl72-expert | DeepSeek-V4-Pro-0813 | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.16 us | 224.6 tok/s | 2,246.4 tok/s | 122 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 298.50 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.65 us |
| DSV4-Pro/b200_sxm-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink5 | infiniband_ndr | 55 | 73.48 us | 1,360.9 tok/s | 13,609.0 tok/s | 49 x point_to_point span 2 on nvlink5 (traversals 1.0) = 59.58 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.90 us |
| DSV4-Pro/b200_sxm-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink5 | infiniband_ndr | 244 | 883.17 us | 113.2 tok/s | 1,132.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 585.27 us |
| DSV4-Pro/b200_sxm-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink5 | infiniband_ndr | 128 | 311.80 us | 320.7 tok/s | 3,207.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.90 us |
| DSV4-Pro/b200_sxm-x56-nvl72-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.53 us | 335.0 tok/s | 3,349.8 tok/s | 122 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 298.53 us |
| DSV4-Pro/b200_sxm-x56-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink5 | infiniband_ndr | 244 | 544.94 us | 183.5 tok/s | 1,835.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.53 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 251.41 us |
| DSV4-Pro/b200_sxm-x56-nvl72-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.13 us | 224.7 tok/s | 2,246.5 tok/s | 122 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 298.53 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.61 us |
| DSV4-Pro/b200_sxm-x58-pipeline | DeepSeek-V4-Pro-0813 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 77.01 us | 1,298.5 tok/s | 12,984.7 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5 | infiniband_ndr | 244 | 885.04 us | 113.0 tok/s | 1,129.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 587.14 us |
| DSV4-Pro/b200_sxm-x58-hybrid | DeepSeek-V4-Pro-0813 | 58 | hybrid | nvlink5 | infiniband_ndr | 129 | 314.12 us | 318.4 tok/s | 3,183.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-nvl72-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.53 us | 335.0 tok/s | 3,349.8 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us |
| DSV4-Pro/b200_sxm-x58-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5 | infiniband_ndr | 244 | 544.81 us | 183.6 tok/s | 1,835.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.53 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 251.28 us |
| DSV4-Pro/b200_sxm-x58-nvl72-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.13 us | 224.7 tok/s | 2,246.5 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.60 us |
| DSV4-Pro/b200_sxm-x78-pipeline | DeepSeek-V4-Pro-0813 | 78 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x78-tensor | DeepSeek-V4-Pro-0813 | 78 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x78-hybrid | DeepSeek-V4-Pro-0813 | 78 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x78-nvl72-tensor | DeepSeek-V4-Pro-0813 | 78 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x78-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 78 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x78-expert | DeepSeek-V4-Pro-0813 | 78 | expert | nvlink5 | infiniband_ndr | 244 | 543.72 us | 183.9 tok/s | 1,839.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.37 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.35 us |
| DSV4-Pro/b200_sxm-x78-nvl72-expert | DeepSeek-V4-Pro-0813 | 78 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.90 us | 182.2 tok/s | 1,821.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.35 us |
| DSV4-Pro/b200_sxm-x85-pipeline | DeepSeek-V4-Pro-0813 | 85 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x85-tensor | DeepSeek-V4-Pro-0813 | 85 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x85-hybrid | DeepSeek-V4-Pro-0813 | 85 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x85-nvl72-tensor | DeepSeek-V4-Pro-0813 | 85 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x85-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 85 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x85-expert | DeepSeek-V4-Pro-0813 | 85 | expert | nvlink5 | infiniband_ndr | 244 | 543.44 us | 184.0 tok/s | 1,840.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.13 us |
| DSV4-Pro/b200_sxm-x85-nvl72-expert | DeepSeek-V4-Pro-0813 | 85 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.68 us | 182.3 tok/s | 1,822.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.13 us |
| DSV4-Pro/b200_sxm-x87-pipeline | DeepSeek-V4-Pro-0813 | 87 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x87-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x87-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x87-nvl72-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x87-expert | DeepSeek-V4-Pro-0813 | 87 | expert | nvlink5 | infiniband_ndr | 244 | 543.38 us | 184.0 tok/s | 1,840.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.07 us |
| DSV4-Pro/b200_sxm-x87-nvl72-expert | DeepSeek-V4-Pro-0813 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.62 us | 182.3 tok/s | 1,822.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.07 us |
| DSV4-Pro/b200_sxm-x88-pipeline | DeepSeek-V4-Pro-0813 | 88 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x88-tensor | DeepSeek-V4-Pro-0813 | 88 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x88-hybrid | DeepSeek-V4-Pro-0813 | 88 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x88-nvl72-tensor | DeepSeek-V4-Pro-0813 | 88 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x88-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 88 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x88-expert | DeepSeek-V4-Pro-0813 | 88 | expert | nvlink5 | infiniband_ndr | 244 | 543.31 us | 184.1 tok/s | 1,840.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.26 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.04 us |
| DSV4-Pro/b200_sxm-x88-nvl72-expert | DeepSeek-V4-Pro-0813 | 88 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.59 us | 182.3 tok/s | 1,822.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.04 us |
| DSV4-Pro/b200_sxm-x92-pipeline | DeepSeek-V4-Pro-0813 | 92 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x92-tensor | DeepSeek-V4-Pro-0813 | 92 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x92-hybrid | DeepSeek-V4-Pro-0813 | 92 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x92-nvl72-tensor | DeepSeek-V4-Pro-0813 | 92 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x92-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 92 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x92-expert | DeepSeek-V4-Pro-0813 | 92 | expert | nvlink5 | infiniband_ndr | 244 | 543.21 us | 184.1 tok/s | 1,840.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.26 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.94 us |
| DSV4-Pro/b200_sxm-x92-nvl72-expert | DeepSeek-V4-Pro-0813 | 92 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.49 us | 182.3 tok/s | 1,823.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.94 us |
| DSV4-Pro/b200_sxm-x98-pipeline | DeepSeek-V4-Pro-0813 | 98 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x98-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink5 | infiniband_ndr | 244 | 890.09 us | 112.3 tok/s | 1,123.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 592.19 us |
| DSV4-Pro/b200_sxm-x98-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink5 | infiniband_ndr | 134 | 325.70 us | 307.0 tok/s | 3,070.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.80 us |
| DSV4-Pro/b200_sxm-x98-nvl72-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x98-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x98-expert | DeepSeek-V4-Pro-0813 | 98 | expert | nvlink5 | infiniband_ndr | 244 | 543.03 us | 184.2 tok/s | 1,841.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.23 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.80 us |
| DSV4-Pro/b200_sxm-x98-nvl72-expert | DeepSeek-V4-Pro-0813 | 98 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.35 us | 182.4 tok/s | 1,823.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.80 us |
| DSV4-Pro/b200_sxm-x110-pipeline | DeepSeek-V4-Pro-0813 | 110 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x110-tensor | DeepSeek-V4-Pro-0813 | 110 | tensor | nvlink5 | infiniband_ndr | 244 | 890.67 us | 112.3 tok/s | 1,122.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 592.76 us |
| DSV4-Pro/b200_sxm-x110-hybrid | DeepSeek-V4-Pro-0813 | 110 | hybrid | nvlink5 | infiniband_ndr | 135 | 328.02 us | 304.9 tok/s | 3,048.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.12 us |
| DSV4-Pro/b200_sxm-x110-nvl72-tensor | DeepSeek-V4-Pro-0813 | 110 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x110-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 110 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x110-expert | DeepSeek-V4-Pro-0813 | 110 | expert | nvlink5 | infiniband_ndr | 244 | 542.76 us | 184.2 tok/s | 1,842.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.19 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.57 us |
| DSV4-Pro/b200_sxm-x110-nvl72-expert | DeepSeek-V4-Pro-0813 | 110 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.12 us | 182.4 tok/s | 1,824.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.57 us |
| DSV4-Pro/b200_sxm-x116-pipeline | DeepSeek-V4-Pro-0813 | 116 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x116-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x116-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x116-nvl72-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x116-expert | DeepSeek-V4-Pro-0813 | 116 | expert | nvlink5 | infiniband_ndr | 244 | 542.63 us | 184.3 tok/s | 1,842.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.47 us |
| DSV4-Pro/b200_sxm-x116-nvl72-expert | DeepSeek-V4-Pro-0813 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.02 us | 182.5 tok/s | 1,824.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.47 us |
| DSV4-Pro/b200_sxm-x118-pipeline | DeepSeek-V4-Pro-0813 | 118 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x118-tensor | DeepSeek-V4-Pro-0813 | 118 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x118-hybrid | DeepSeek-V4-Pro-0813 | 118 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x118-nvl72-tensor | DeepSeek-V4-Pro-0813 | 118 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x118-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 118 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x118-expert | DeepSeek-V4-Pro-0813 | 118 | expert | nvlink5 | infiniband_ndr | 244 | 542.60 us | 184.3 tok/s | 1,843.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.44 us |
| DSV4-Pro/b200_sxm-x118-nvl72-expert | DeepSeek-V4-Pro-0813 | 118 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.99 us | 182.5 tok/s | 1,824.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.44 us |
| DSV4-Pro/b200_sxm-x121-pipeline | DeepSeek-V4-Pro-0813 | 121 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x121-tensor | DeepSeek-V4-Pro-0813 | 121 | tensor | nvlink5 | infiniband_ndr | 244 | 891.60 us | 112.2 tok/s | 1,121.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 593.70 us |
| DSV4-Pro/b200_sxm-x121-hybrid | DeepSeek-V4-Pro-0813 | 121 | hybrid | nvlink5 | infiniband_ndr | 137 | 332.65 us | 300.6 tok/s | 3,006.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 34.75 us |
| DSV4-Pro/b200_sxm-x121-nvl72-tensor | DeepSeek-V4-Pro-0813 | 121 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x121-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 121 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x121-expert | DeepSeek-V4-Pro-0813 | 121 | expert | nvlink5 | infiniband_ndr | 244 | 542.53 us | 184.3 tok/s | 1,843.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.14 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.39 us |
| DSV4-Pro/b200_sxm-x121-nvl72-expert | DeepSeek-V4-Pro-0813 | 121 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.94 us | 182.5 tok/s | 1,825.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.39 us |
| DSV4-Pro/b200_sxm-x133-pipeline | DeepSeek-V4-Pro-0813 | 133 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x133-tensor | DeepSeek-V4-Pro-0813 | 133 | tensor | nvlink5 | infiniband_ndr | 244 | 891.99 us | 112.1 tok/s | 1,121.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 594.09 us |
| DSV4-Pro/b200_sxm-x133-hybrid | DeepSeek-V4-Pro-0813 | 133 | hybrid | nvlink5 | infiniband_ndr | 138 | 334.97 us | 298.5 tok/s | 2,985.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.07 us |
| DSV4-Pro/b200_sxm-x133-nvl72-tensor | DeepSeek-V4-Pro-0813 | 133 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x133-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 133 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x133-expert | DeepSeek-V4-Pro-0813 | 133 | expert | nvlink5 | infiniband_ndr | 244 | 542.36 us | 184.4 tok/s | 1,843.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.12 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.24 us |
| DSV4-Pro/b200_sxm-x133-nvl72-expert | DeepSeek-V4-Pro-0813 | 133 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.79 us | 182.6 tok/s | 1,825.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.24 us |
| DSV4-Pro/b200_sxm-x134-pipeline | DeepSeek-V4-Pro-0813 | 134 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x134-tensor | DeepSeek-V4-Pro-0813 | 134 | tensor | nvlink5 | infiniband_ndr | 244 | 891.99 us | 112.1 tok/s | 1,121.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 594.09 us |
| DSV4-Pro/b200_sxm-x134-hybrid | DeepSeek-V4-Pro-0813 | 134 | hybrid | nvlink5 | infiniband_ndr | 138 | 334.97 us | 298.5 tok/s | 2,985.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.07 us |
| DSV4-Pro/b200_sxm-x134-nvl72-tensor | DeepSeek-V4-Pro-0813 | 134 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x134-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 134 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x134-expert | DeepSeek-V4-Pro-0813 | 134 | expert | nvlink5 | infiniband_ndr | 244 | 542.35 us | 184.4 tok/s | 1,843.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.12 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.23 us |
| DSV4-Pro/b200_sxm-x134-nvl72-expert | DeepSeek-V4-Pro-0813 | 134 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.78 us | 182.6 tok/s | 1,825.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.23 us |
| DSV4-Pro/b200_sxm-x147-pipeline | DeepSeek-V4-Pro-0813 | 147 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x147-tensor | DeepSeek-V4-Pro-0813 | 147 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x147-hybrid | DeepSeek-V4-Pro-0813 | 147 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x147-nvl72-tensor | DeepSeek-V4-Pro-0813 | 147 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x147-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 147 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x147-expert | DeepSeek-V4-Pro-0813 | 147 | expert | nvlink5 | infiniband_ndr | 244 | 542.17 us | 184.4 tok/s | 1,844.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.09 us |
| DSV4-Pro/b200_sxm-x147-nvl72-expert | DeepSeek-V4-Pro-0813 | 147 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.76 us | 183.6 tok/s | 1,835.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.09 us |
| DSV4-Pro/b200_sxm-x152-pipeline | DeepSeek-V4-Pro-0813 | 152 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x152-tensor | DeepSeek-V4-Pro-0813 | 152 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x152-hybrid | DeepSeek-V4-Pro-0813 | 152 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x152-nvl72-tensor | DeepSeek-V4-Pro-0813 | 152 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x152-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 152 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x152-expert | DeepSeek-V4-Pro-0813 | 152 | expert | nvlink5 | infiniband_ndr | 244 | 542.11 us | 184.5 tok/s | 1,844.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.07 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.04 us |
| DSV4-Pro/b200_sxm-x152-nvl72-expert | DeepSeek-V4-Pro-0813 | 152 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.72 us | 183.6 tok/s | 1,835.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.04 us |
| DSV4-Pro/b200_sxm-x153-pipeline | DeepSeek-V4-Pro-0813 | 153 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x153-tensor | DeepSeek-V4-Pro-0813 | 153 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/b200_sxm-x153-hybrid | DeepSeek-V4-Pro-0813 | 153 | hybrid | nvlink5 | infiniband_ndr | 141 | 341.92 us | 292.5 tok/s | 2,924.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| DSV4-Pro/b200_sxm-x153-nvl72-tensor | DeepSeek-V4-Pro-0813 | 153 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x153-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 153 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x153-expert | DeepSeek-V4-Pro-0813 | 153 | expert | nvlink5 | infiniband_ndr | 244 | 542.10 us | 184.5 tok/s | 1,844.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.07 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.03 us |
| DSV4-Pro/b200_sxm-x153-nvl72-expert | DeepSeek-V4-Pro-0813 | 153 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.71 us | 183.6 tok/s | 1,835.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.03 us |
| DSV4-Pro/b200_sxm-x157-pipeline | DeepSeek-V4-Pro-0813 | 157 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x157-tensor | DeepSeek-V4-Pro-0813 | 157 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/b200_sxm-x157-hybrid | DeepSeek-V4-Pro-0813 | 157 | hybrid | nvlink5 | infiniband_ndr | 141 | 341.92 us | 292.5 tok/s | 2,924.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| DSV4-Pro/b200_sxm-x157-nvl72-tensor | DeepSeek-V4-Pro-0813 | 157 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x157-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 157 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x157-expert | DeepSeek-V4-Pro-0813 | 157 | expert | nvlink5 | infiniband_ndr | 244 | 542.07 us | 184.5 tok/s | 1,844.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.07 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.00 us |
| DSV4-Pro/b200_sxm-x157-nvl72-expert | DeepSeek-V4-Pro-0813 | 157 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.67 us | 183.6 tok/s | 1,836.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.00 us |
| DSV4-Pro/b200_sxm-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x173-nvl72-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x173-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5 | infiniband_ndr | 244 | 541.92 us | 184.5 tok/s | 1,845.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.04 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x173-nvl72-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.55 us | 183.6 tok/s | 1,836.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5 | infiniband_ndr | 244 | 894.54 us | 111.8 tok/s | 1,117.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 596.64 us |
| DSV4-Pro/b200_sxm-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5 | infiniband_ndr | 150 | 362.77 us | 275.7 tok/s | 2,756.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 64.87 us |
| DSV4-Pro/b200_sxm-x231-nvl72-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 872.57 us | 114.6 tok/s | 1,146.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 125 | 305.50 us | 327.3 tok/s | 3,273.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x231-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5 | infiniband_ndr | 244 | 541.55 us | 184.7 tok/s | 1,846.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.98 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x231-nvl72-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 543.28 us | 184.1 tok/s | 1,840.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.72 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x289-pipeline | DeepSeek-V4-Pro-0813 | 289 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x289-tensor | DeepSeek-V4-Pro-0813 | 289 | tensor | nvlink5 | infiniband_ndr | 244 | 895.32 us | 111.7 tok/s | 1,116.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 37 on infiniband_ndr (traversals 2.0) = 597.42 us |
| DSV4-Pro/b200_sxm-x289-hybrid | DeepSeek-V4-Pro-0813 | 289 | hybrid | nvlink5 | infiniband_ndr | 158 | 381.30 us | 262.3 tok/s | 2,622.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 36 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 83.40 us |
| DSV4-Pro/b200_sxm-x289-nvl72-tensor | DeepSeek-V4-Pro-0813 | 289 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 877.82 us | 113.9 tok/s | 1,139.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x289-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 289 | hybrid | nvlink5_nvl72 | infiniband_ndr | 126 | 307.82 us | 324.9 tok/s | 3,248.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x289-expert | DeepSeek-V4-Pro-0813 | 289 | expert | nvlink5 | infiniband_ndr | 244 | 541.33 us | 184.7 tok/s | 1,847.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.94 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.39 us |
| DSV4-Pro/b200_sxm-x289-nvl72-expert | DeepSeek-V4-Pro-0813 | 289 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 542.62 us | 184.3 tok/s | 1,842.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.24 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.39 us |
| DSV4-Pro/b200_sxm-x347-pipeline | DeepSeek-V4-Pro-0813 | 347 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x347-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5 | infiniband_ndr | 244 | 895.78 us | 111.6 tok/s | 1,116.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 597.87 us |
| DSV4-Pro/b200_sxm-x347-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5 | infiniband_ndr | 165 | 397.52 us | 251.6 tok/s | 2,515.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 99.62 us |
| DSV4-Pro/b200_sxm-x347-nvl72-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 877.82 us | 113.9 tok/s | 1,139.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 126 | 307.82 us | 324.9 tok/s | 3,248.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x347-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5 | infiniband_ndr | 244 | 541.18 us | 184.8 tok/s | 1,847.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.92 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |
| DSV4-Pro/b200_sxm-x347-nvl72-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 542.50 us | 184.3 tok/s | 1,843.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.24 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Pro-0813 | 1 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299 | 243,685 | 6,192.9 | 0.025 | 6,192.9 (243,685) | 3,784.7 (184,900) | 0.61x | compute |
| DeepSeek-V4-Pro-0813 | 2 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299 | 243,685 | 6,192.9 | 0.025 | 6,192.9 (243,685) | 3,745.8 (462,250) | 0.60x | compute |
| DeepSeek-V4-Pro-0813 | 4 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299 | 243,685 | 6,192.9 | 0.025 | 6,192.9 (243,685) | 3,745.8 (462,250) | 0.60x | compute |
| DeepSeek-V4-Pro-0813 | 8 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299 | 243,685 | 6,192.9 | 0.025 | 6,192.9 (243,685) | 3,745.8 (462,250) | 0.60x | compute |
| DeepSeek-V4-Pro-0813 | 16 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299 | 243,685 | 6,192.9 | 0.025 | 6,192.9 (243,685) | 3,634.7 (462,250) | 0.59x | compute |
| DeepSeek-V4-Pro-0813 | 32 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299 | 243,685 | 6,192.9 | 0.025 | 6,192.9 (243,685) | 3,368.2 (462,250) | 0.54x | compute |
| DeepSeek-V4-Pro-0813 | 64 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x299 | 243,685 | 6,192.9 | 0.025 | 6,192.9 (243,685) | 2,937.4 (462,250) | 0.47x | compute |
| DeepSeek-V4-Pro-0813 | 256 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 2,584.2 | 0.009 | 2,584.2 (277,100) | 1,838.5 (554,700) | 0.71x | compute |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 844.4 | 0.002 | 691.3 (277,100) | 844.4 (554,700) | 1.22x | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 214.5 | 0.000 | 174.6 (277,100) | 214.5 (554,700) | 1.23x | kv_read |

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
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 365.2 mm2 | 65.73 mm2 (18.0%) | 140,230 mm2 | 25,241 mm2 | 152,286 mm2 = 186.9 reticles |

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
| DeepSeek-V4-Pro-0813 | 1 | sram | 575,243.9 | 26,083.1 | 26,083.1 | 22.05x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 575,243.9 | 26,083.1 | 26,083.1 | 22.05x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 575,243.9 | 26,083.1 | 26,083.1 | 22.05x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 575,243.9 | 26,083.1 | 34,223.3 | 22.05x | 1.31x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | sram | 575,243.9 | 26,083.1 | 56,154.6 | 22.05x | 2.15x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | sram | 575,243.9 | 26,083.1 | 83,921.7 | 22.05x | 3.22x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | sram | 575,243.9 | 26,083.1 | 114,998.4 | 22.05x | 4.41x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 256 | sram | 661,564.2 | 26,083.1 | 268,227.8 | 25.36x | 10.28x | compute | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 747,112.7 | 26,097.8 | 404,720.4 | 28.63x | 15.51x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 878,617.7 | 26,109.0 | 684,237.7 | 33.65x | 26.21x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 855,534.9 | 198,216.7 | 198,216.7 | 4.32x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 855,534.9 | 198,216.7 | 198,216.7 | 4.32x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 855,534.9 | 198,216.7 | 198,216.7 | 4.32x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 855,534.9 | 198,216.7 | 198,216.7 | 4.32x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 855,534.9 | 198,216.7 | 198,216.7 | 4.32x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 855,534.9 | 198,216.7 | 198,216.7 | 4.32x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 855,534.9 | 198,216.7 | 198,216.7 | 4.32x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 855,534.9 | 198,216.7 | 425,482.0 | 4.32x | 2.15x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 864,661.3 | 198,992.3 | 621,883.6 | 4.35x | 3.13x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 878,617.7 | 199,722.4 | 732,838.6 | 4.40x | 3.67x | kv_read | weight_read | kv_read |

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
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 855,534.9 | 1.542 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 855,534.9 | 1.542 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 855,534.9 | 1.542 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 855,534.9 | 1.542 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x81-perregion | 66,015 | 1.00 | 1.99 | 34,223.3 | 0.518 | link_latency | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 855,534.9 | 1.542 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x81-perregion | 66,015 | 1.00 | 2.54 | 56,154.6 | 0.851 | link_latency | 0.10x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 855,534.9 | 1.542 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x81-perregion | 66,015 | 1.00 | 3.49 | 83,921.7 | 1.271 | link_latency | 0.15x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 855,534.9 | 1.542 | kv_read | 1.49x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x81-perregion | 66,015 | 1.00 | 4.92 | 114,998.4 | 1.742 | link_latency | 0.20x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 661,564.2 | 2.387 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 855,534.9 | 1.542 | kv_read | 1.29x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,083.1 | 0.056 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 198,216.7 | 0.429 | weight_read | 0.30x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x10-perregion | 462,250 | 1.00 | 10.96 | 268,227.8 | 0.580 | link_latency | 0.41x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perregion-romfill | 462,250 | 7.66 | 3.17 | 425,482.0 | 0.920 | kv_read | 0.64x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 747,112.7 | 1.347 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 864,661.3 | 1.559 | kv_read | 1.16x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x81-perstream | 66,015 | 1.00 | 12.64 | 26,097.8 | 0.395 | weight_read | 0.03x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.80 | 198,992.3 | 0.430 | weight_read | 0.27x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x10-perregion | 462,250 | 1.00 | 28.90 | 404,720.4 | 0.876 | kv_read | 0.54x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perregion-romfill | 462,250 | 7.66 | 6.34 | 621,883.6 | 1.345 | kv_read | 0.83x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 878,617.7 | 1.584 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 878,617.7 | 1.584 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 7.21 | 26,109.0 | 0.056 | weight_read | 0.03x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 7.21 | 199,722.4 | 0.432 | weight_read | 0.23x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 14.95 | 684,237.7 | 1.480 | weight_read | 0.78x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.92 | 732,838.6 | 1.585 | kv_read | 0.83x |

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
| DeepSeek-V4-Pro-0813 | 1 | 74 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 81 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 81 | 3.16 | 1.017 | 1.274 | 1.25x |
| DeepSeek-V4-Pro-0813 | 1024 | 81 | 12.64 | 1.094 | 2.301 | 2.10x |
| DeepSeek-V4-Pro-0813 | 4096 | 81 | 50.57 | 1.439 | 4.371 | 3.04x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4-Pro-0813 | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4-Pro-0813 | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4-Pro-0813 | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4-Pro-0813 | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4-Pro-0813 | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4-Pro-0813 | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4-Pro-0813 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 2 | 38 | 10.34 | 6.29 | 1.64x |
| DeepSeek-V4-Pro-0813 | 4 | 38 | 17.66 | 8.67 | 2.04x |
| DeepSeek-V4-Pro-0813 | 8 | 38 | 26.69 | 11.45 | 2.33x |
| DeepSeek-V4-Pro-0813 | 16 | 38 | 34.12 | 14.46 | 2.36x |
| DeepSeek-V4-Pro-0813 | 32 | 38 | 37.34 | 17.39 | 2.15x |
| DeepSeek-V4-Pro-0813 | 64 | 38 | 37.94 | 19.83 | 1.91x |
| DeepSeek-V4-Pro-0813 | 256 | 38 | 38.00 | 22.03 | 1.72x |
| DeepSeek-V4-Pro-0813 | 1024 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4-Pro-0813 | 1 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Pro-0813 | 2 | 40 | 10.41 | 6.38 | 1.63x |
| DeepSeek-V4-Pro-0813 | 4 | 40 | 17.91 | 8.83 | 2.03x |
| DeepSeek-V4-Pro-0813 | 8 | 40 | 27.35 | 11.70 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 40 | 35.41 | 14.84 | 2.39x |
| DeepSeek-V4-Pro-0813 | 32 | 40 | 39.15 | 17.91 | 2.19x |
| DeepSeek-V4-Pro-0813 | 64 | 40 | 39.92 | 20.48 | 1.95x |
| DeepSeek-V4-Pro-0813 | 256 | 40 | 40.00 | 22.81 | 1.75x |
| DeepSeek-V4-Pro-0813 | 1024 | 40 | 40.00 | 22.90 | 1.75x |
| DeepSeek-V4-Pro-0813 | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Pro-0813 | 2 | 41 | 10.44 | 6.42 | 1.63x |
| DeepSeek-V4-Pro-0813 | 4 | 41 | 18.02 | 8.90 | 2.02x |
| DeepSeek-V4-Pro-0813 | 8 | 41 | 27.65 | 11.82 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 41 | 36.04 | 15.02 | 2.40x |
| DeepSeek-V4-Pro-0813 | 32 | 41 | 40.04 | 18.16 | 2.20x |
| DeepSeek-V4-Pro-0813 | 64 | 41 | 40.90 | 20.80 | 1.97x |
| DeepSeek-V4-Pro-0813 | 256 | 41 | 41.00 | 23.19 | 1.77x |
| DeepSeek-V4-Pro-0813 | 1024 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4-Pro-0813 | 1 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Pro-0813 | 2 | 42 | 10.48 | 6.46 | 1.62x |
| DeepSeek-V4-Pro-0813 | 4 | 42 | 18.13 | 8.97 | 2.02x |
| DeepSeek-V4-Pro-0813 | 8 | 42 | 27.95 | 11.94 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 42 | 36.65 | 15.20 | 2.41x |
| DeepSeek-V4-Pro-0813 | 32 | 42 | 40.92 | 18.41 | 2.22x |
| DeepSeek-V4-Pro-0813 | 64 | 42 | 41.88 | 21.11 | 1.98x |
| DeepSeek-V4-Pro-0813 | 256 | 42 | 42.00 | 23.57 | 1.78x |
| DeepSeek-V4-Pro-0813 | 1024 | 42 | 42.00 | 23.67 | 1.77x |
| DeepSeek-V4-Pro-0813 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Pro-0813 | 2 | 43 | 10.51 | 6.50 | 1.62x |
| DeepSeek-V4-Pro-0813 | 4 | 43 | 18.23 | 9.04 | 2.02x |
| DeepSeek-V4-Pro-0813 | 8 | 43 | 28.24 | 12.05 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 43 | 37.25 | 15.38 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 43 | 41.80 | 18.66 | 2.24x |
| DeepSeek-V4-Pro-0813 | 64 | 43 | 42.86 | 21.42 | 2.00x |
| DeepSeek-V4-Pro-0813 | 256 | 43 | 42.99 | 23.94 | 1.80x |
| DeepSeek-V4-Pro-0813 | 1024 | 43 | 42.99 | 24.04 | 1.79x |
| DeepSeek-V4-Pro-0813 | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Pro-0813 | 2 | 46 | 10.59 | 6.62 | 1.60x |
| DeepSeek-V4-Pro-0813 | 4 | 46 | 18.52 | 9.24 | 2.00x |
| DeepSeek-V4-Pro-0813 | 8 | 46 | 29.06 | 12.38 | 2.35x |
| DeepSeek-V4-Pro-0813 | 16 | 46 | 38.98 | 15.89 | 2.45x |
| DeepSeek-V4-Pro-0813 | 32 | 46 | 44.37 | 19.37 | 2.29x |
| DeepSeek-V4-Pro-0813 | 64 | 46 | 45.78 | 22.32 | 2.05x |
| DeepSeek-V4-Pro-0813 | 256 | 46 | 45.99 | 25.03 | 1.84x |
| DeepSeek-V4-Pro-0813 | 1024 | 46 | 45.99 | 25.14 | 1.83x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4-Pro-0813 | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4-Pro-0813 | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4-Pro-0813 | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4-Pro-0813 | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4-Pro-0813 | 1 | 78 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 78 | 11.11 | 7.59 | 1.46x |
| DeepSeek-V4-Pro-0813 | 4 | 78 | 20.36 | 10.73 | 1.90x |
| DeepSeek-V4-Pro-0813 | 8 | 78 | 34.61 | 15.05 | 2.30x |
| DeepSeek-V4-Pro-0813 | 16 | 78 | 52.13 | 20.11 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 78 | 67.03 | 25.44 | 2.64x |
| DeepSeek-V4-Pro-0813 | 64 | 78 | 74.65 | 30.21 | 2.47x |
| DeepSeek-V4-Pro-0813 | 256 | 78 | 77.40 | 34.82 | 2.22x |
| DeepSeek-V4-Pro-0813 | 1024 | 78 | 77.45 | 35.01 | 2.21x |
| DeepSeek-V4-Pro-0813 | 4096 | 78 | 77.45 | 35.01 | 2.21x |
| DeepSeek-V4-Pro-0813 | 1 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 85 | 11.17 | 7.75 | 1.44x |
| DeepSeek-V4-Pro-0813 | 4 | 85 | 20.59 | 10.96 | 1.88x |
| DeepSeek-V4-Pro-0813 | 8 | 85 | 35.36 | 15.51 | 2.28x |
| DeepSeek-V4-Pro-0813 | 16 | 85 | 54.11 | 20.83 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 85 | 70.93 | 26.50 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 85 | 80.26 | 31.63 | 2.54x |
| DeepSeek-V4-Pro-0813 | 256 | 85 | 84.02 | 36.61 | 2.29x |
| DeepSeek-V4-Pro-0813 | 1024 | 85 | 84.10 | 36.82 | 2.28x |
| DeepSeek-V4-Pro-0813 | 4096 | 85 | 84.10 | 36.82 | 2.28x |
| DeepSeek-V4-Pro-0813 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4-Pro-0813 | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4-Pro-0813 | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4-Pro-0813 | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4-Pro-0813 | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4-Pro-0813 | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4-Pro-0813 | 1 | 88 | 5.83 | 5.21 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 88 | 11.20 | 7.82 | 1.43x |
| DeepSeek-V4-Pro-0813 | 4 | 88 | 20.68 | 11.05 | 1.87x |
| DeepSeek-V4-Pro-0813 | 8 | 88 | 35.66 | 15.70 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 88 | 54.89 | 21.13 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 88 | 72.51 | 26.94 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 88 | 82.58 | 32.22 | 2.56x |
| DeepSeek-V4-Pro-0813 | 256 | 88 | 86.82 | 37.35 | 2.32x |
| DeepSeek-V4-Pro-0813 | 1024 | 88 | 86.91 | 37.57 | 2.31x |
| DeepSeek-V4-Pro-0813 | 4096 | 88 | 86.91 | 37.57 | 2.31x |
| DeepSeek-V4-Pro-0813 | 1 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 92 | 11.23 | 7.90 | 1.42x |
| DeepSeek-V4-Pro-0813 | 4 | 92 | 20.79 | 11.17 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 92 | 36.02 | 15.94 | 2.26x |
| DeepSeek-V4-Pro-0813 | 16 | 92 | 55.87 | 21.51 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 92 | 74.53 | 27.50 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 92 | 85.60 | 32.97 | 2.60x |
| DeepSeek-V4-Pro-0813 | 256 | 92 | 90.51 | 38.32 | 2.36x |
| DeepSeek-V4-Pro-0813 | 1024 | 92 | 90.62 | 38.54 | 2.35x |
| DeepSeek-V4-Pro-0813 | 4096 | 92 | 90.62 | 38.54 | 2.35x |
| DeepSeek-V4-Pro-0813 | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 98 | 11.27 | 8.02 | 1.40x |
| DeepSeek-V4-Pro-0813 | 4 | 98 | 20.94 | 11.34 | 1.85x |
| DeepSeek-V4-Pro-0813 | 8 | 98 | 36.52 | 16.28 | 2.24x |
| DeepSeek-V4-Pro-0813 | 16 | 98 | 57.24 | 22.06 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 98 | 77.39 | 28.31 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 98 | 89.96 | 34.06 | 2.64x |
| DeepSeek-V4-Pro-0813 | 256 | 98 | 95.95 | 39.72 | 2.42x |
| DeepSeek-V4-Pro-0813 | 1024 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4-Pro-0813 | 4096 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4-Pro-0813 | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 110 | 11.33 | 8.24 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 110 | 21.20 | 11.65 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 110 | 37.37 | 16.92 | 2.21x |
| DeepSeek-V4-Pro-0813 | 16 | 110 | 59.63 | 23.06 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 110 | 82.55 | 29.82 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 110 | 98.14 | 36.10 | 2.72x |
| DeepSeek-V4-Pro-0813 | 256 | 110 | 106.49 | 42.35 | 2.51x |
| DeepSeek-V4-Pro-0813 | 1024 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4-Pro-0813 | 4096 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4-Pro-0813 | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4-Pro-0813 | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4-Pro-0813 | 1 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 118 | 11.37 | 8.38 | 1.36x |
| DeepSeek-V4-Pro-0813 | 4 | 118 | 21.34 | 11.84 | 1.80x |
| DeepSeek-V4-Pro-0813 | 8 | 118 | 37.86 | 17.30 | 2.19x |
| DeepSeek-V4-Pro-0813 | 16 | 118 | 61.02 | 23.67 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 118 | 85.64 | 30.75 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 118 | 103.19 | 37.37 | 2.76x |
| DeepSeek-V4-Pro-0813 | 256 | 118 | 113.24 | 43.99 | 2.57x |
| DeepSeek-V4-Pro-0813 | 1024 | 118 | 113.51 | 44.27 | 2.56x |
| DeepSeek-V4-Pro-0813 | 4096 | 118 | 113.51 | 44.27 | 2.56x |
| DeepSeek-V4-Pro-0813 | 1 | 121 | 5.88 | 5.39 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 121 | 11.38 | 8.43 | 1.35x |
| DeepSeek-V4-Pro-0813 | 4 | 121 | 21.39 | 11.90 | 1.80x |
| DeepSeek-V4-Pro-0813 | 8 | 121 | 38.02 | 17.44 | 2.18x |
| DeepSeek-V4-Pro-0813 | 16 | 121 | 61.50 | 23.88 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 121 | 86.73 | 31.09 | 2.79x |
| DeepSeek-V4-Pro-0813 | 64 | 121 | 105.01 | 37.83 | 2.78x |
| DeepSeek-V4-Pro-0813 | 256 | 121 | 115.71 | 44.59 | 2.59x |
| DeepSeek-V4-Pro-0813 | 1024 | 121 | 116.00 | 44.88 | 2.58x |
| DeepSeek-V4-Pro-0813 | 4096 | 121 | 116.00 | 44.88 | 2.58x |
| DeepSeek-V4-Pro-0813 | 1 | 133 | 5.89 | 5.44 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 133 | 11.43 | 8.60 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 133 | 21.57 | 12.17 | 1.77x |
| DeepSeek-V4-Pro-0813 | 8 | 133 | 38.62 | 17.96 | 2.15x |
| DeepSeek-V4-Pro-0813 | 16 | 133 | 63.26 | 24.69 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 133 | 90.77 | 32.35 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 133 | 111.88 | 39.59 | 2.83x |
| DeepSeek-V4-Pro-0813 | 256 | 133 | 125.28 | 46.88 | 2.67x |
| DeepSeek-V4-Pro-0813 | 1024 | 133 | 125.67 | 47.19 | 2.66x |
| DeepSeek-V4-Pro-0813 | 4096 | 133 | 125.67 | 47.19 | 2.66x |
| DeepSeek-V4-Pro-0813 | 1 | 134 | 5.89 | 5.44 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 134 | 11.43 | 8.62 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 134 | 21.58 | 12.19 | 1.77x |
| DeepSeek-V4-Pro-0813 | 8 | 134 | 38.67 | 18.00 | 2.15x |
| DeepSeek-V4-Pro-0813 | 16 | 134 | 63.39 | 24.76 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 134 | 91.09 | 32.45 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 134 | 112.43 | 39.73 | 2.83x |
| DeepSeek-V4-Pro-0813 | 256 | 134 | 126.06 | 47.07 | 2.68x |
| DeepSeek-V4-Pro-0813 | 1024 | 134 | 126.45 | 47.38 | 2.67x |
| DeepSeek-V4-Pro-0813 | 4096 | 134 | 126.45 | 47.38 | 2.67x |
| DeepSeek-V4-Pro-0813 | 1 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 147 | 11.47 | 8.79 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 147 | 21.74 | 12.45 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 147 | 39.21 | 18.49 | 2.12x |
| DeepSeek-V4-Pro-0813 | 16 | 147 | 65.01 | 25.54 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 147 | 94.92 | 33.70 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 147 | 119.17 | 41.48 | 2.87x |
| DeepSeek-V4-Pro-0813 | 256 | 147 | 135.80 | 49.37 | 2.75x |
| DeepSeek-V4-Pro-0813 | 1024 | 147 | 136.31 | 49.71 | 2.74x |
| DeepSeek-V4-Pro-0813 | 4096 | 147 | 136.31 | 49.71 | 2.74x |
| DeepSeek-V4-Pro-0813 | 1 | 152 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 152 | 11.49 | 8.85 | 1.30x |
| DeepSeek-V4-Pro-0813 | 4 | 152 | 21.79 | 12.55 | 1.74x |
| DeepSeek-V4-Pro-0813 | 8 | 152 | 39.40 | 18.66 | 2.11x |
| DeepSeek-V4-Pro-0813 | 16 | 152 | 65.57 | 25.83 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 152 | 96.27 | 34.16 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 152 | 121.60 | 42.12 | 2.89x |
| DeepSeek-V4-Pro-0813 | 256 | 152 | 139.39 | 50.22 | 2.78x |
| DeepSeek-V4-Pro-0813 | 1024 | 152 | 139.95 | 50.57 | 2.77x |
| DeepSeek-V4-Pro-0813 | 4096 | 152 | 139.95 | 50.57 | 2.77x |
| DeepSeek-V4-Pro-0813 | 1 | 153 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 153 | 11.49 | 8.86 | 1.30x |
| DeepSeek-V4-Pro-0813 | 4 | 153 | 21.80 | 12.57 | 1.73x |
| DeepSeek-V4-Pro-0813 | 8 | 153 | 39.44 | 18.69 | 2.11x |
| DeepSeek-V4-Pro-0813 | 16 | 153 | 65.68 | 25.88 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 153 | 96.53 | 34.25 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 153 | 122.08 | 42.25 | 2.89x |
| DeepSeek-V4-Pro-0813 | 256 | 153 | 140.10 | 50.39 | 2.78x |
| DeepSeek-V4-Pro-0813 | 1024 | 153 | 140.67 | 50.74 | 2.77x |
| DeepSeek-V4-Pro-0813 | 4096 | 153 | 140.67 | 50.74 | 2.77x |
| DeepSeek-V4-Pro-0813 | 1 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 157 | 11.50 | 8.91 | 1.29x |
| DeepSeek-V4-Pro-0813 | 4 | 157 | 21.84 | 12.64 | 1.73x |
| DeepSeek-V4-Pro-0813 | 8 | 157 | 39.58 | 18.83 | 2.10x |
| DeepSeek-V4-Pro-0813 | 16 | 157 | 66.10 | 26.10 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 157 | 97.56 | 34.60 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 157 | 123.95 | 42.74 | 2.90x |
| DeepSeek-V4-Pro-0813 | 256 | 157 | 142.90 | 51.05 | 2.80x |
| DeepSeek-V4-Pro-0813 | 1024 | 157 | 143.50 | 51.41 | 2.79x |
| DeepSeek-V4-Pro-0813 | 4096 | 157 | 143.50 | 51.41 | 2.79x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4-Pro-0813 | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4-Pro-0813 | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 289 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 289 | 11.68 | 9.92 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 289 | 22.56 | 14.64 | 1.54x |
| DeepSeek-V4-Pro-0813 | 8 | 289 | 42.13 | 21.55 | 1.96x |
| DeepSeek-V4-Pro-0813 | 16 | 289 | 74.15 | 31.75 | 2.33x |
| DeepSeek-V4-Pro-0813 | 32 | 289 | 118.36 | 43.43 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 289 | 164.88 | 55.14 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 289 | 210.82 | 67.86 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1024 | 289 | 212.64 | 68.42 | 3.11x |
| DeepSeek-V4-Pro-0813 | 4096 | 289 | 212.64 | 68.42 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 347 | 11.72 | 10.18 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 347 | 22.70 | 15.30 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 347 | 42.66 | 22.28 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 347 | 75.90 | 33.59 | 2.26x |
| DeepSeek-V4-Pro-0813 | 32 | 347 | 123.23 | 45.96 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 347 | 175.33 | 59.00 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 347 | 230.16 | 73.28 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 347 | 232.44 | 73.90 | 3.15x |

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
| gpu | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 4.3% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 11.1% |

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
| DeepSeek-V4-Pro-0813 | 1 | 74 | 96.99% | 159.24 | 2.22 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 2.42% | 6.13 | 2.22 |
| DeepSeek-V4-Pro-0813 | 4 | 2 | 2.42% | 6.13 | 2.22 |
| DeepSeek-V4-Pro-0813 | 8 | 2 | 2.42% | 6.13 | 2.22 |
| DeepSeek-V4-Pro-0813 | 16 | 2 | 2.42% | 6.13 | 2.22 |
| DeepSeek-V4-Pro-0813 | 32 | 2 | 2.42% | 6.13 | 2.22 |

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
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 278.9 | 46,301.2 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 278.9 | 46,301.2 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 278.9 | 46,301.2 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 278.9 | 46,301.2 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 278.9 | 46,301.2 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 278.9 | 46,301.2 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 278.9 | 46,301.2 |
| DeepSeek-V4-Pro-0813 | 256 | 2.40% | 46.5 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 181.2 | 46,390.2 |
| DeepSeek-V4-Pro-0813 | 1024 | 9.26% | 102.9 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 45.4 | 46,513.8 |
| DeepSeek-V4-Pro-0813 | 4096 | 32.20% | 291.5 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 11.4 | 46,544.8 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 43 |
| gpu | link_latency | 788 |
| gpu | thermal | 284 |
| gpu | weight_read | 825 |
| rom | compute | 796 |
| rom | infeasible | 2238 |
| rom | kv_read | 71 |
| rom | link_latency | 937 |
| rom | thermal | 5 |
| rom | weight_read | 633 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 43 |
| rom | CAPACITY | 2238 |

## Mechanical consistency audit

**FAIL** over 135,146 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x154', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x172', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x215', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x216', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x237', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x238', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x288', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x154', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x172', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x215', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x216', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x237', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x238', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x288', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x154', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x172', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x215', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x216', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x237', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x238', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x288', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x154', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x172', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x215', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x216', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x237', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x238', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x288', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x154', 'DeepSeek-V4-Pro-0813', 1)

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

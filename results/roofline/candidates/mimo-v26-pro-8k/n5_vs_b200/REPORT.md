# Area-constrained roofline: n5_vs_b200-mimo-v26-pro-8k

> CANDIDATE MODEL under n5_vs_b200: MiMo-V2.6-Pro at 8,192 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 203x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 154 devices. On the GPU side the correction reaches 50x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 58 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Pro takes 99 x 815 mm2 (80,685 mm2, array, KV in SRAM) at 6,159 tok/s per user and 76 tok/s per 1,000 mm2, holding 1 session, against 50 copies of one unified HBM die at the same silicon: 3.0x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Pro on 126,325 mm2 of ROM silicon at 7,748 tok/s per user against 126,400 mm2 of b200_sxm-x79-nvl72-hybrid at 1,941 tok/s: **4.0x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 34,209 resident sessions against the GPU cluster's 26,663. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 14.57x to it.** At 114,915 mm2 on MiMo-V2.6-Pro the pipeline-only GPU delivers 155.04 tok/s and the same silicon running tensor delivers 2,259 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (MiMo-V2.6-Pro, ROM binding on `link_latency`) to 4.50x (MiMo-V2.6-Pro, ROM binding on `weight_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Pro engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 394 to 41,215 tok/s, and its rate with every slot occupied from 40,930 to 41,215. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 104 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,010 us over NVLink, capping per-user decode at 990 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 300.9 us and cap it at 3,324 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 211 of 4668 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 67.2x of aggregate throughput (MiMo-V2.6-Pro). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 12.71x, on MiMo-V2.6-Pro at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 284 of 4,668 feasible points (6.1%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x54-perregion-romfill` at batch 4096 on 44,010 mm2, throttled 1.33x from 112 to 84 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 92% kv read against 0.3% weight read. The ROM sweep is not what melts it.


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

### MiMo-V2.6-Pro at 8,192 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x99`** -- 99 x 815 mm2 reticle dies, 80,685 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **6,159.0 tok/s per user** (0.16 ms/token), binding on `link_latency`
- **76.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 6,159 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 5,055 W at 0.063 W/mm2, 820.8 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 50 copies of one unified HBM die -- `b200_sxm-x50-nvl72-tensor`, 80,000 mm2, area ratio 1.0086 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 80,685 | 80,000 | 1.0086 |
| user tok/s | 6,159.0 | 2,082.2 | 2.96x |
| aggregate tok/s | 6,159 | 2,082 | 0.79x |
| resident sessions | 1 | 16,422 | -- |
| J/token | 0.8208 | 12.6047 | 15.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 16,422 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x72-nvl72-tensor` at 115,200 mm2 and 2,258.6 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 125,510 | 7,637.0 | 60.8 | 33,988 | 3.95x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 7,747.6 | 61.3 | 34,209 | 3.99x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x95` | 77,425 | 5,641.5 | 72.9 | 1 | 2.74x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x99` | 80,685 | 6,159.0 | 76.3 | 1 | 2.96x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x99` | 80,685 | 6,159.0 | 76.3 | -- | 76.3 | ACCEPT |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 7,747.6 | 61.3 | 34.8 | 76.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x99` **<-- recommended** | 80,685 | 99 | 6,159.0 | 6,159 | 76.3 | 1 | `link_latency` | 5,055 | 820.8 | `b200_sxm-x50-nvl72-tensor` | 2.96x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 155 | 7,747.6 | 302,157 | 61.3 | 34,209 | `compute` | 32,253 | 1,730.4 | `b200_sxm-x79-nvl72-hybrid` | 3.99x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 312 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x99` | 80,685 | 6,159.0 | 76.3 | 1 |
| array | 312 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 7,747.6 | 61.3 | 34,209 |
| array | 312 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x95` | 77,425 | 5,641.5 | 72.9 | 1 |
| wafer | 66 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,267.7 | 35.3 | 1 |
| wafer | 66 | fastest | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,348.0 | 24.1 | 5,694 |
| wafer | 66 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,267.7 | 35.3 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 7,747.6 | 302,157 | 34,209 | 32,253 | 1,730.4 | `compute` | `b200_sxm-x79-nvl72-hybrid` | 1,940.9 | 26,663 | 18,453.4 | 0.999 | 3.99x | 10.7x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,348.0 | 10,044 | 5,694 | 13,535 | 3,914.8 | `link_latency` | `b200_sxm-x87-nvl72-hybrid` | 1,996.3 | 29,488 | 19,462.0 | 0.996 | 1.68x | 5.0x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 7,268.4 | 312,542 | 37,520 | 34,839 | 2,104.6 | `weight_read` | `b200_sxm-x87-nvl72-hybrid` | 1,996.3 | 29,488 | 19,462.0 | 0.995 | 3.64x | 9.2x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,348.0 | -- | 5,694 | -- | 3,914.8 | -- | -- | -- | -- | -- | 0.999 | 0.46x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 7,747.6 | 302,157 | 34,209 | 32,253 | 897.2 | `compute` | `b200_sxm-x79-nvl72-hybrid` | 1,940.9 | 26,663 | 11,321.6 | 0.999 | 3.99x | 12.6x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,348.0 | 10,044 | 5,694 | 13,535 | 1,989.4 | `link_latency` | `b200_sxm-x87-nvl72-hybrid` | 1,996.3 | 29,488 | 11,825.8 | 0.996 | 1.68x | 5.9x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 7,268.4 | 312,542 | 37,520 | 34,839 | 1,084.3 | `weight_read` | `b200_sxm-x87-nvl72-hybrid` | 1,996.3 | 29,488 | 11,825.8 | 0.995 | 3.64x | 10.9x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,348.0 | -- | 5,694 | -- | 1,989.4 | -- | -- | -- | -- | -- | 0.999 | 0.46x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 7,747.6 | 302,157 | 34,209 | 32,253 | 480.6 | `compute` | `b200_sxm-x79-nvl72-hybrid` | 1,769.1 | 26,663 | 6,604.1 | 0.999 | 4.38x | 13.7x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,346.9 | 13,387 | 7,592 | 20,572 | 1,536.7 | `link_latency` | `b200_sxm-x116-nvl72-hybrid` | 1,993.7 | 39,729 | 7,789.3 | 0.996 | 1.68x | 5.1x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 7,233.2 | 412,293 | 50,100 | 46,198 | 748.5 | `weight_read` | `b200_sxm-x116-nvl72-hybrid` | 1,993.7 | 39,729 | 7,789.3 | 0.997 | 3.63x | 10.4x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,346.9 | -- | 7,592 | -- | 1,536.7 | -- | -- | -- | -- | -- | 1.001 | 0.46x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 7,747.6 | 302,157 | 34,209 | 32,253 | 272.3 | `compute` | `b200_sxm-x79-nvl72-hybrid` | 1,508.9 | 26,663 | 4,218.6 | 0.999 | 5.13x | 15.5x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,342.3 | 26,738 | 15,184 | 34,511 | 1,290.7 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 1,971.5 | 80,339 | 7,824.3 | 1.001 | 1.70x | 6.1x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 7,747.6 | 302,157 | 34,209 | 32,253 | 168.2 | `compute` | `b200_sxm-x79-nvl72-hybrid` | 1,179.8 | 26,663 | 2,974.8 | 0.999 | 6.57x | 17.7x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,289.4 | 52,631 | 22,777 | 52,452 | 996.6 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,907.4 | 121,302 | 6,104.8 | 0.999 | 1.72x | 6.1x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | 7,747.6 | 302,157 | 34,209 | 32,253 | 116.1 | `compute` | `b200_sxm-x79-nvl72-hybrid` | 846.7 | 26,663 | 2,260.4 | 0.999 | 9.15x | 19.5x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,109.4 | 99,499 | 22,777 | 55,017 | 552.9 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,611.0 | 121,302 | 3,977.8 | 0.999 | 1.93x | 7.2x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 319,480 | 7,186.7 | 704,298 | 86,517 | 79,286 | 138.4 | `weight_read` | `b200_sxm-x200-nvl72-hybrid` | 980.3 | 69,392 | 2,258.3 | 0.998 | 7.33x | 16.3x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 2,802.5 | 179,362 | 22,777 | 84,477 | 471.0 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,250.1 | 121,302 | 2,837.4 | 0.999 | 2.24x | 6.0x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 319,480 | 3,705.5 | 948,615 | 86,517 | 89,740 | 94.6 | `compute` | `b200_sxm-x200-nvl72-hybrid` | 484.9 | 69,392 | 1,200.0 | 0.998 | 7.64x | 11.9x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,760.3 | 450,635 | 22,777 | 99,095 | 219.9 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 627.2 | 121,302 | 1,589.6 | 0.999 | 2.81x | 6.5x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x294` | 239,610 | 1,163.8 | 1,191,709 | 64,888 | 97,376 | 81.7 | `weight_read` | `b200_sxm-x150-nvl72-hybrid` | 214.4 | 51,735 | 466.2 | 0.998 | 5.43x | 4.8x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 870.2 | 891,039 | 22,777 | 103,607 | 116.3 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 316.8 | 121,302 | 713.0 | 0.999 | 2.75x | 4.5x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 319,480 | 428.3 | 1,754,398 | 86,517 | 139,562 | 79.5 | `weight_read` | `b200_sxm-x200-expert` | 95.2 | 67,913 | 248.8 | 0.998 | 4.50x | 3.1x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 554,700 | 221.1 | 905,457 | 22,777 | 125,489 | 138.6 | `kv_read` | `b200_sxm-x347-expert` | 146.0 | 118,714 | 272.3 | 0.999 | 1.51x | 2.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x99` | 80,685 | array | SRAM | 1 |
| 2-32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x155` | 126,325 | array | HBM | 34,209 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 138,550 | array | HBM | 37,520 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 185,005 | array | HBM | 50,100 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x294` | 239,610 | array | HBM | 64,888 |
| 4096 | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 319,480 | array | HBM | 86,517 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Pro | HBM | rom | 104, 113, 120, 123, 141, 147, 154, 155, 170, 196, 227, 294, 340, 392 |
| MiMo-V2.6-Pro | HBM | sram | 104, 113, 120, 123, 141, 147, 154, 155, 170, 196, 227, 294, 340, 392 |
| MiMo-V2.6-Pro | SRAM | rom | 95, 99, 104, 113, 114, 137, 170, 182, 227, 273, 340, 364 |
| MiMo-V2.6-Pro | SRAM | sram | 95, 99, 104, 113, 114, 137, 170, 182, 227, 273, 340, 364 |

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

- **284 of 4,668 feasible points (6.1%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 280, rom 4.
- By area class: large array (5,000-40,000 mm2) 20, wafer (>=40,000 mm2) 264.
- By KV store: hbm 284.
- By batch: B=1 28, B=2 28, B=4 28, B=8 28, B=16 28, B=32 28, B=64 28, B=256 28, B=1024 28, B=4096 32.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 120 | 20 | 73.0% | 100.0% | 0.625 | 48% |
| gpu | wafer (>=40,000 mm2) | 1,700 | 260 | 53.6% | 100.0% | 0.625 | 65% |
| rom | large array (5,000-40,000 mm2) | 48 | 0 | 13.1% | 13.8% | 0.069 | 99% |
| rom | wafer (>=40,000 mm2) | 2,800 | 4 | 25.9% | 100.0% | 0.500 | 70% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x54-perregion-romfill` | MiMo-V2.6-Pro | 4096 | 44,010 | hbm | 1.331x | 22,005.0 / 22,005.0 W | 18% | 84.1 | 112.0 |
| `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x59-perregion-romfill` | MiMo-V2.6-Pro | 4096 | 48,085 | hbm | 1.330x | 24,042.5 / 24,042.5 W | 18% | 91.9 | 122.2 |
| `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x52-perregion-romfill` | MiMo-V2.6-Pro | 4096 | 42,380 | hbm | 1.330x | 21,190.0 / 21,190.0 W | 18% | 81.0 | 107.8 |
| `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x52-perregion` | MiMo-V2.6-Pro | 4096 | 42,380 | hbm | 1.330x | 21,190.0 / 21,190.0 W | 18% | 81.0 | 107.8 |
| `MiMo-V2.6-Pro/b200_sxm-x16-pipeline` | MiMo-V2.6-Pro | 4096 | 25,600 | hbm | 1.071x | 16,000.0 / 16,000.0 W | 35% | 9.0 | 9.6 |
| `MiMo-V2.6-Pro/b200_sxm-x24-pipeline` | MiMo-V2.6-Pro | 4096 | 38,400 | hbm | 1.064x | 24,000.0 / 24,000.0 W | 35% | 9.8 | 10.4 |
| `MiMo-V2.6-Pro/b200_sxm-x26-pipeline` | MiMo-V2.6-Pro | 4096 | 41,600 | hbm | 1.062x | 26,000.0 / 26,000.0 W | 35% | 9.9 | 10.6 |
| `MiMo-V2.6-Pro/b200_sxm-x28-pipeline` | MiMo-V2.6-Pro | 4096 | 44,800 | hbm | 1.062x | 28,000.0 / 28,000.0 W | 35% | 10.1 | 10.7 |
| `MiMo-V2.6-Pro/b200_sxm-x29-pipeline` | MiMo-V2.6-Pro | 4096 | 46,400 | hbm | 1.061x | 29,000.0 / 29,000.0 W | 35% | 10.2 | 10.8 |
| `MiMo-V2.6-Pro/b200_sxm-x30-pipeline` | MiMo-V2.6-Pro | 4096 | 48,000 | hbm | 1.061x | 30,000.0 / 30,000.0 W | 35% | 10.3 | 10.9 |
| `MiMo-V2.6-Pro/b200_sxm-x16-pipeline` | MiMo-V2.6-Pro | 1024 | 25,600 | hbm | 1.057x | 16,000.0 / 16,000.0 W | 35% | 13.6 | 14.4 |
| `MiMo-V2.6-Pro/b200_sxm-x48-pipeline` | MiMo-V2.6-Pro | 4096 | 76,800 | hbm | 1.056x | 48,000.0 / 48,000.0 W | 35% | 12.0 | 12.7 |

The worst point's dynamic energy is kv read 91.9%, arithmetic 6.8%, operand delivery 1.1%, weight read 0.3%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| MiMo-V2.6-Pro | 1 | 125,510 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 1.737235 | 31,844.7 | compute | `MiMo-V2.6-Pro/b200_sxm-x78-nvl72-hybrid` | 18.327384 | 43,535.3 | link_latency | 10.55x |
| MiMo-V2.6-Pro | 2 | 125,510 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 0.900625 | 31,844.7 | compute | `MiMo-V2.6-Pro/b200_sxm-x78-nvl72-hybrid` | 11.258532 | 43,535.3 | link_latency | 12.50x |
| MiMo-V2.6-Pro | 4 | 125,510 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 0.482320 | 31,844.7 | compute | `MiMo-V2.6-Pro/b200_sxm-x78-nvl72-hybrid` | 6.572045 | 46,296.5 | link_latency | 13.63x |
| MiMo-V2.6-Pro | 8 | 125,510 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 0.273167 | 31,844.7 | compute | `MiMo-V2.6-Pro/b200_sxm-x78-nvl72-hybrid` | 4.202027 | 50,446.4 | link_latency | 15.38x |
| MiMo-V2.6-Pro | 16 | 125,510 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 0.168591 | 31,844.7 | compute | `MiMo-V2.6-Pro/b200_sxm-x78-nvl72-hybrid` | 2.966025 | 55,612.6 | weight_read | 17.59x |
| MiMo-V2.6-Pro | 32 | 125,510 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 0.116303 | 31,844.7 | compute | `MiMo-V2.6-Pro/b200_sxm-x78-nvl72-hybrid` | 2.255486 | 60,628.0 | weight_read | 19.39x |
| MiMo-V2.6-Pro | 64 | 185,005 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 0.107076 | 48,169.4 | weight_read | `MiMo-V2.6-Pro/b200_sxm-x116-nvl72-hybrid` | 1.860445 | 88,201.2 | weight_read | 17.38x |
| MiMo-V2.6-Pro | 256 | 319,480 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 0.094601 | 89,740.2 | compute | `MiMo-V2.6-Pro/b200_sxm-x200-nvl72-hybrid` | 1.200005 | 148,950.8 | weight_read | 11.93x |
| MiMo-V2.6-Pro | 1024 | 239,610 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x294` | 0.081712 | 97,376.4 | weight_read | `MiMo-V2.6-Pro/b200_sxm-x150-nvl72-hybrid` | 0.466190 | 102,366.1 | link_latency | 4.79x |
| MiMo-V2.6-Pro | 4096 | 319,480 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 0.079550 | 139,561.7 | weight_read | `MiMo-V2.6-Pro/b200_sxm-x200-expert` | 0.248760 | 96,965.0 | link_latency | 3.13x |

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
| MiMo-V2.6-Pro | 8,192 | 1,020 B | 566.0 GB | 4.44 | 0.459 GB | 0.459 GB | 85.8 |

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
| MiMo-V2.6-Pro | 2 | 92,450 | 28,808.0 | wafer-pipeline | 3,267.7 | wafer-hybrid | 8.82x | 4,874.1 | pipeline | 2,158.3 | tensor | 2.26x | 5.91x | 1.51x | 0.26x |
| MiMo-V2.6-Pro | 3 | 138,675 | 34,728.9 | wafer-pipeline | 3,348.0 | wafer-hybrid | 10.37x | 5,424.4 | pipeline | 1,996.3 | hybrid | 2.72x | 6.40x | 1.68x | 0.26x |
| MiMo-V2.6-Pro | 4 | 184,900 | 36,106.3 | wafer-pipeline | 3,346.9 | wafer-hybrid | 10.79x | 6,019.1 | pipeline | 2,147.7 | hybrid | 2.80x | 6.00x | 1.56x | 0.26x |
| MiMo-V2.6-Pro | 6 | 277,350 | 37,597.5 | wafer-pipeline | 3,344.6 | wafer-hybrid | 11.24x | 6,750.6 | pipeline | 2,134.4 | hybrid | 3.16x | 5.57x | 1.57x | 0.28x |
| MiMo-V2.6-Pro | 8 | 369,800 | 38,390.2 | wafer-pipeline | 3,342.3 | wafer-hybrid | 11.49x | 7,197.6 | pipeline | 2,124.8 | hybrid | 3.39x | 5.33x | 1.57x | 0.29x |
| MiMo-V2.6-Pro | 12 | 554,700 | 39,217.1 | wafer-pipeline | 3,337.8 | wafer-hybrid | 11.75x | 7,706.4 | pipeline | 2,197.5 | hybrid | 3.51x | 5.09x | 1.52x | 0.30x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.26x to 0.30x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Pro | 1 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x155 | 126,325 | 7,747.6 | 302,156.6 | compute | MiMo-V2.6-Pro/b200_sxm-x79-nvl72-hybrid | 126,400 | 1.00x | hybrid | 343.93 | 1,940.9 | 3,881.8 | link_latency | 3.99x | 24.67x | 49.97x | 3.99x |
| MiMo-V2.6-Pro | 1 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x95 | 77,425 | 5,641.5 | 5,641.5 | link_latency | MiMo-V2.6-Pro/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 341.61 | 2,060.3 | 2,060.3 | link_latency | 2.74x | 0.76x | 36.39x | 2.74x |
| MiMo-V2.6-Pro | 2 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x155 | 126,325 | 7,747.6 | 302,156.6 | compute | MiMo-V2.6-Pro/b200_sxm-x79-nvl72-hybrid | 126,400 | 1.00x | hybrid | 343.93 | 1,940.9 | 3,881.8 | link_latency | 3.99x | 24.67x | 49.97x | 3.99x |
| MiMo-V2.6-Pro | 2 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x104 | 84,760 | 4,375.2 | 8,750.5 | link_latency | MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | 84,800 | 1.00x | tensor | 347.25 | 1,953.8 | 3,907.5 | link_latency | 2.24x | 1.06x | 28.22x | 2.24x |
| MiMo-V2.6-Pro | 4 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x155 | 126,325 | 7,747.6 | 302,156.6 | compute | MiMo-V2.6-Pro/b200_sxm-x79-nvl72-hybrid | 126,400 | 1.00x | hybrid | 349.83 | 1,769.1 | 7,076.4 | link_latency | 4.38x | 24.67x | 49.97x | 4.38x |
| MiMo-V2.6-Pro | 4 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x104 | 84,760 | 3,514.7 | 14,058.7 | link_latency | MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | 84,800 | 1.00x | tensor | 358.50 | 1,703.8 | 6,815.2 | link_latency | 2.06x | 1.71x | 22.67x | 2.06x |
| MiMo-V2.6-Pro | 8 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x155 | 126,325 | 7,747.6 | 302,156.6 | compute | MiMo-V2.6-Pro/b200_sxm-x79-nvl72-hybrid | 126,400 | 1.00x | hybrid | 361.63 | 1,508.9 | 12,071.5 | link_latency | 5.13x | 24.67x | 49.97x | 5.13x |
| MiMo-V2.6-Pro | 8 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x104 | 84,760 | 2,522.4 | 20,179.5 | link_latency | MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | 84,800 | 1.00x | tensor | 381.01 | 1,370.5 | 10,964.3 | link_latency | 1.84x | 1.84x | 16.27x | 1.84x |
| MiMo-V2.6-Pro | 16 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x155 | 126,325 | 7,747.6 | 302,156.6 | compute | MiMo-V2.6-Pro/b200_sxm-x79-nvl72-hybrid | 126,400 | 1.00x | hybrid | 385.23 | 1,179.8 | 18,876.5 | weight_read | 6.57x | 16.01x | 49.97x | 6.57x |
| MiMo-V2.6-Pro | 16 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x104 | 84,760 | 1,612.2 | 25,794.5 | compute | MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | 84,800 | 1.00x | tensor | 426.02 | 1,012.2 | 16,194.6 | weight_read | 1.59x | 1.59x | 10.40x | 1.59x |
| MiMo-V2.6-Pro | 32 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x155 | 126,325 | 7,747.6 | 302,156.6 | compute | MiMo-V2.6-Pro/b200_sxm-x79-nvl72-hybrid | 126,400 | 1.00x | hybrid | 432.44 | 846.7 | 27,094.1 | weight_read | 9.15x | 11.15x | 49.97x | 9.15x |
| MiMo-V2.6-Pro | 32 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x104 | 84,760 | 1,252.1 | 40,065.7 | compute | MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | 84,800 | 1.00x | tensor | 516.04 | 706.6 | 22,609.7 | weight_read | 1.77x | 1.77x | 8.08x | 1.77x |
| MiMo-V2.6-Pro | 64 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 7,186.7 | 704,298.2 | weight_read | MiMo-V2.6-Pro/b200_sxm-x200-nvl72-hybrid | 320,000 | 1.00x | hybrid | 471.18 | 980.3 | 62,737.3 | link_latency | 7.33x | 11.23x | 46.35x | 7.33x |
| MiMo-V2.6-Pro | 64 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x104 | 84,760 | 634.4 | 40,601.9 | compute | MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | 84,800 | 1.00x | tensor | 696.08 | 493.9 | 31,608.5 | weight_read | 1.28x | 1.28x | 4.34x | 1.28x |
| MiMo-V2.6-Pro | 256 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 3,705.5 | 948,614.7 | compute | MiMo-V2.6-Pro/b200_sxm-x200-nvl72-hybrid | 320,000 | 1.00x | hybrid | 864.54 | 484.9 | 124,125.1 | weight_read | 7.64x | 7.64x | 25.82x | 7.64x |
| MiMo-V2.6-Pro | 256 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x104 | 84,760 | 160.6 | 41,103.3 | compute | MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | 84,800 | 1.00x | tensor | 1,776.31 | 266.2 | 68,144.4 | link_latency | 0.60x | 0.60x | 2.13x | 0.60x |
| MiMo-V2.6-Pro | 1024 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x294 | 239,610 | 1,163.8 | 1,191,709.1 | weight_read | MiMo-V2.6-Pro/b200_sxm-x150-nvl72-hybrid | 240,000 | 1.00x | hybrid | 2,437.99 | 214.4 | 219,580.1 | link_latency | 5.43x | 5.43x | 19.39x | 5.43x |
| MiMo-V2.6-Pro | 1024 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x104 | 84,760 | 40.2 | 41,192.7 | compute | MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | 84,800 | 1.00x | tensor | 6,097.23 | 109.8 | 112,387.0 | link_latency | 0.37x | 0.37x | 1.41x | 0.37x |
| MiMo-V2.6-Pro | 4096 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392 | 319,480 | 428.3 | 1,754,397.5 | weight_read | MiMo-V2.6-Pro/b200_sxm-x200-expert | 320,000 | 1.00x | expert | 7,079.43 | 95.2 | 389,793.4 | link_latency | 4.50x | 4.50x | 15.60x | 4.50x |
| MiMo-V2.6-Pro | 4096 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x104 | 84,760 | 10.1 | 41,215.1 | compute | MiMo-V2.6-Pro/b200_sxm-x53-hybrid | 84,800 | 1.00x | hybrid | 4,147.02 | 47.5 | 194,634.9 | weight_read | 0.21x | 0.21x | 0.81x | 0.21x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 16 | 25,600 | 341.38 | 341.38 | 1,349.4 | 1,349.4 |
| MiMo-V2.6-Pro | 24 | 38,400 | 341.50 | 341.50 | 1,630.8 | 1,630.8 |
| MiMo-V2.6-Pro | 26 | 41,600 | 341.51 | 341.51 | 1,684.8 | 1,684.8 |
| MiMo-V2.6-Pro | 28 | 44,800 | 341.53 | 341.53 | 1,734.1 | 1,734.1 |
| MiMo-V2.6-Pro | 29 | 46,400 | 341.54 | 341.54 | 1,757.1 | 1,757.1 |
| MiMo-V2.6-Pro | 30 | 48,000 | 341.54 | 341.54 | 1,779.1 | 1,779.1 |
| MiMo-V2.6-Pro | 48 | 76,800 | 341.61 | 341.61 | 2,060.3 | 2,060.3 |
| MiMo-V2.6-Pro | 50 | 80,000 | 341.62 | 341.62 | 2,082.2 | 2,082.2 |
| MiMo-V2.6-Pro | 53 | 84,800 | 341.63 | 341.63 | 2,112.8 | 2,112.8 |
| MiMo-V2.6-Pro | 58 | 92,800 | 341.64 | 341.64 | 2,158.3 | 2,158.3 |
| MiMo-V2.6-Pro | 61 | 97,600 | 341.64 | 341.64 | 2,182.8 | 2,182.8 |
| MiMo-V2.6-Pro | 63 | 100,800 | 341.64 | 341.64 | 2,198.1 | 2,198.1 |
| MiMo-V2.6-Pro | 70 | 112,000 | 341.65 | 341.65 | 2,246.2 | 2,246.2 |
| MiMo-V2.6-Pro | 72 | 115,200 | 341.65 | 341.65 | 2,258.6 | 2,258.6 |
| MiMo-V2.6-Pro | 75 | 120,000 | 343.93 | 343.93 | 1,910.2 | 1,910.2 |
| MiMo-V2.6-Pro | 78 | 124,800 | 343.93 | 343.93 | 1,933.4 | 1,933.4 |
| MiMo-V2.6-Pro | 79 | 126,400 | 343.93 | 343.93 | 1,940.9 | 1,940.9 |
| MiMo-V2.6-Pro | 87 | 139,200 | 343.93 | 343.93 | 1,996.3 | 1,996.3 |
| MiMo-V2.6-Pro | 93 | 148,800 | 343.93 | 343.93 | 2,033.3 | 2,033.3 |
| MiMo-V2.6-Pro | 100 | 160,000 | 343.93 | 343.93 | 2,072.2 | 2,072.2 |
| MiMo-V2.6-Pro | 116 | 185,600 | 343.93 | 343.93 | 2,147.7 | 2,147.7 |
| MiMo-V2.6-Pro | 139 | 222,400 | 343.93 | 343.93 | 2,231.6 | 2,231.6 |
| MiMo-V2.6-Pro | 150 | 240,000 | 346.21 | 346.21 | 2,062.5 | 2,062.5 |
| MiMo-V2.6-Pro | 173 | 276,800 | 346.21 | 346.21 | 2,134.4 | 2,134.4 |
| MiMo-V2.6-Pro | 185 | 296,000 | 346.21 | 346.21 | 2,166.4 | 2,166.4 |
| MiMo-V2.6-Pro | 200 | 320,000 | 346.21 | 346.21 | 2,202.0 | 2,202.0 |
| MiMo-V2.6-Pro | 231 | 369,600 | 348.48 | 348.48 | 2,124.8 | 2,124.8 |
| MiMo-V2.6-Pro | 347 | 555,200 | 350.76 | 350.76 | 2,197.5 | 2,197.5 |

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
| MiMo-V2.6-Pro | 16 | 25,600 | 155.0 | 1,349.4 | 887.4 | tensor | 341.38 | 46.1% | weight_read |
| MiMo-V2.6-Pro | 24 | 38,400 | 155.0 | 1,630.8 | 885.7 | tensor | 341.50 | 55.7% | link_latency |
| MiMo-V2.6-Pro | 26 | 41,600 | 155.0 | 1,684.8 | 764.2 | tensor | 341.51 | 57.5% | link_latency |
| MiMo-V2.6-Pro | 28 | 44,800 | 155.0 | 1,734.1 | 805.8 | tensor | 341.53 | 59.2% | link_latency |
| MiMo-V2.6-Pro | 29 | 46,400 | 155.0 | 1,757.1 | 825.9 | tensor | 341.54 | 60.0% | link_latency |
| MiMo-V2.6-Pro | 30 | 48,000 | 155.0 | 1,779.1 | 845.6 | tensor | 341.54 | 60.8% | link_latency |
| MiMo-V2.6-Pro | 48 | 76,800 | 155.0 | 2,060.3 | 880.3 | tensor | 341.61 | 70.4% | link_latency |
| MiMo-V2.6-Pro | 50 | 80,000 | 155.0 | 2,082.2 | 812.8 | tensor | 341.62 | 71.1% | link_latency |
| MiMo-V2.6-Pro | 53 | 84,800 | 155.0 | 2,112.8 | 846.3 | tensor | 341.63 | 72.2% | link_latency |
| MiMo-V2.6-Pro | 58 | 92,800 | 155.0 | 2,158.3 | 819.7 | tensor | 341.64 | 73.7% | link_latency |
| MiMo-V2.6-Pro | 61 | 97,600 | 155.0 | 2,182.8 | 848.7 | tensor | 341.64 | 74.6% | link_latency |
| MiMo-V2.6-Pro | 63 | 100,800 | 155.0 | 2,198.1 | 867.5 | tensor | 341.64 | 75.1% | link_latency |
| MiMo-V2.6-Pro | 70 | 112,000 | 155.0 | 2,246.2 | 858.6 | tensor | 341.65 | 76.7% | link_latency |
| MiMo-V2.6-Pro | 72 | 115,200 | 155.0 | 2,258.6 | 875.1 | tensor | 341.65 | 77.2% | link_latency |
| MiMo-V2.6-Pro | 75 | 120,000 | 155.0 | 944.0 | 1,910.2 | hybrid | 343.93 | 65.7% | link_latency |
| MiMo-V2.6-Pro | 78 | 124,800 | 155.0 | 946.8 | 1,933.4 | hybrid | 343.93 | 66.5% | link_latency |
| MiMo-V2.6-Pro | 79 | 126,400 | 155.0 | 947.7 | 1,940.9 | hybrid | 343.93 | 66.8% | link_latency |
| MiMo-V2.6-Pro | 87 | 139,200 | 155.0 | 954.1 | 1,996.3 | hybrid | 343.93 | 68.7% | link_latency |
| MiMo-V2.6-Pro | 93 | 148,800 | 155.0 | 958.3 | 2,033.3 | hybrid | 343.93 | 69.9% | link_latency |
| MiMo-V2.6-Pro | 100 | 160,000 | 155.0 | 962.6 | 2,072.2 | hybrid | 343.93 | 71.3% | link_latency |
| MiMo-V2.6-Pro | 116 | 185,600 | 155.0 | 970.5 | 2,147.7 | hybrid | 343.93 | 73.9% | link_latency |
| MiMo-V2.6-Pro | 139 | 222,400 | 155.0 | 978.8 | 2,231.6 | hybrid | 343.93 | 76.8% | link_latency |
| MiMo-V2.6-Pro | 150 | 240,000 | 155.0 | 965.6 | 2,062.5 | hybrid | 346.21 | 71.4% | link_latency |
| MiMo-V2.6-Pro | 173 | 276,800 | 155.0 | 970.7 | 2,134.4 | hybrid | 346.21 | 73.9% | link_latency |
| MiMo-V2.6-Pro | 185 | 296,000 | 155.0 | 972.9 | 2,166.4 | hybrid | 346.21 | 75.0% | link_latency |
| MiMo-V2.6-Pro | 200 | 320,000 | 155.0 | 975.3 | 2,202.0 | hybrid | 346.21 | 76.2% | link_latency |
| MiMo-V2.6-Pro | 231 | 369,600 | 155.0 | 971.0 | 2,124.8 | hybrid | 348.48 | 74.0% | link_latency |
| MiMo-V2.6-Pro | 347 | 555,200 | 155.0 | 974.5 | 2,197.5 | hybrid | 350.76 | 77.1% | link_latency |

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
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x104 | MiMo-V2.6-Pro | 104 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 2.50 us | 40,067.4 tok/s | 400,673.6 tok/s | 52 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.68 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.82 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x99 | MiMo-V2.6-Pro | 99 | tensor | rom_package_ucie | rom_board_serdes | 280 | 129.72 us | 770.9 tok/s | 7,708.9 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 140 x all_reduce span 25 on rom_board_serdes (traversals 8.8) = 125.95 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x104 | MiMo-V2.6-Pro | 104 | hybrid | rom_package_ucie | rom_board_serdes | 165 | 6.44 us | 15,531.9 tok/s | 155,319.4 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 25 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.67 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x104 | MiMo-V2.6-Pro | 104 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | MiMo-V2.6-Pro | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-tensor-x95 | MiMo-V2.6-Pro | 95 | tensor | nvlink5 | infiniband_ndr | 280 | 1,004.04 us | 99.6 tok/s | 996.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 663.02 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x2 | MiMo-V2.6-Pro | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 280 | 300.73 us | 332.5 tok/s | 3,325.2 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 140 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 31.23 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hybrid-x104 | MiMo-V2.6-Pro | 104 | hybrid | nvlink5 | infiniband_ndr | 152 | 368.33 us | 271.5 tok/s | 2,715.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.31 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | MiMo-V2.6-Pro | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 141 | 269.60 us | 370.9 tok/s | 3,709.2 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x154 | MiMo-V2.6-Pro | 154 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 2.50 us | 40,067.4 tok/s | 400,673.6 tok/s | 52 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.68 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.82 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x120 | MiMo-V2.6-Pro | 120 | tensor | rom_package_ucie | rom_board_serdes | 280 | 160.54 us | 622.9 tok/s | 6,229.0 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 140 x all_reduce span 30 on rom_board_serdes (traversals 11.0) = 156.77 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x155 | MiMo-V2.6-Pro | 155 | hybrid | rom_package_ucie | rom_board_serdes | 178 | 7.83 us | 12,776.1 tok/s | 127,761.3 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 38 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.06 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-pipeline-x154 | MiMo-V2.6-Pro | 154 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3 | MiMo-V2.6-Pro | 3 | pipeline | on_wafer_n5 | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-tensor-x104 | MiMo-V2.6-Pro | 104 | tensor | nvlink5 | infiniband_ndr | 280 | 1,004.70 us | 99.5 tok/s | 995.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 663.68 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x3 | MiMo-V2.6-Pro | 3 | tensor | on_wafer_n5 | rom_wafer_serdes | 280 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 140 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 31.37 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hybrid-x141 | MiMo-V2.6-Pro | 141 | hybrid | nvlink5 | infiniband_ndr | 157 | 379.71 us | 263.4 tok/s | 2,633.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 38.69 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | MiMo-V2.6-Pro | 3 | hybrid | on_wafer_n5 | rom_wafer_serdes | 142 | 269.70 us | 370.8 tok/s | 3,707.8 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| MiMo-V2.6-Pro/b200_sxm-x16-pipeline | MiMo-V2.6-Pro | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.27 us | 5,190.2 tok/s | 51,902.5 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.99 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x16-tensor | MiMo-V2.6-Pro | 16 | tensor | nvlink5 | infiniband_ndr | 280 | 961.03 us | 104.1 tok/s | 1,040.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x16-hybrid | MiMo-V2.6-Pro | 16 | hybrid | nvlink5 | infiniband_ndr | 141 | 343.29 us | 291.3 tok/s | 2,913.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x16-nvl72-tensor | MiMo-V2.6-Pro | 16 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.38 us | 292.9 tok/s | 2,929.3 tok/s | 140 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 341.38 us |
| MiMo-V2.6-Pro/b200_sxm-x16-expert | MiMo-V2.6-Pro | 16 | expert | nvlink5 | infiniband_ndr | 280 | 639.91 us | 156.3 tok/s | 1,562.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 338.51 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 301.40 us |
| MiMo-V2.6-Pro/b200_sxm-x16-nvl72-expert | MiMo-V2.6-Pro | 16 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.33 us | 196.0 tok/s | 1,959.5 tok/s | 140 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 341.38 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.96 us |
| MiMo-V2.6-Pro/b200_sxm-x24-pipeline | MiMo-V2.6-Pro | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 30.04 us | 3,329.1 tok/s | 33,290.9 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.49 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x24-tensor | MiMo-V2.6-Pro | 24 | tensor | nvlink5 | infiniband_ndr | 280 | 978.23 us | 102.2 tok/s | 1,022.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x24-hybrid | MiMo-V2.6-Pro | 24 | hybrid | nvlink5 | infiniband_ndr | 142 | 345.57 us | 289.4 tok/s | 2,893.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x24-nvl72-tensor | MiMo-V2.6-Pro | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.50 us | 292.8 tok/s | 2,928.3 tok/s | 140 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 341.50 us |
| MiMo-V2.6-Pro/b200_sxm-x24-expert | MiMo-V2.6-Pro | 24 | expert | nvlink5 | infiniband_ndr | 280 | 633.34 us | 157.9 tok/s | 1,578.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 295.67 us |
| MiMo-V2.6-Pro/b200_sxm-x24-nvl72-expert | MiMo-V2.6-Pro | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.13 us | 196.0 tok/s | 1,960.3 tok/s | 140 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 341.50 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.64 us |
| MiMo-V2.6-Pro/b200_sxm-x26-pipeline | MiMo-V2.6-Pro | 26 | pipeline | nvlink5 | infiniband_ndr | 25 | 33.53 us | 2,982.6 tok/s | 29,826.1 tok/s | 22 x point_to_point span 2 on nvlink5 (traversals 1.0) = 26.70 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x26-tensor | MiMo-V2.6-Pro | 26 | tensor | nvlink5 | infiniband_ndr | 280 | 986.83 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x26-hybrid | MiMo-V2.6-Pro | 26 | hybrid | nvlink5 | infiniband_ndr | 143 | 347.84 us | 287.5 tok/s | 2,874.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x26-nvl72-tensor | MiMo-V2.6-Pro | 26 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.51 us | 292.8 tok/s | 2,928.1 tok/s | 140 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 341.51 us |
| MiMo-V2.6-Pro/b200_sxm-x26-expert | MiMo-V2.6-Pro | 26 | expert | nvlink5 | infiniband_ndr | 280 | 632.46 us | 158.1 tok/s | 1,581.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 294.79 us |
| MiMo-V2.6-Pro/b200_sxm-x26-nvl72-expert | MiMo-V2.6-Pro | 26 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.10 us | 196.0 tok/s | 1,960.4 tok/s | 140 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 341.51 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.59 us |
| MiMo-V2.6-Pro/b200_sxm-x28-pipeline | MiMo-V2.6-Pro | 28 | pipeline | nvlink5 | infiniband_ndr | 27 | 35.95 us | 2,781.3 tok/s | 27,812.6 tok/s | 24 x point_to_point span 2 on nvlink5 (traversals 1.0) = 29.13 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x28-tensor | MiMo-V2.6-Pro | 28 | tensor | nvlink5 | infiniband_ndr | 280 | 986.83 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x28-hybrid | MiMo-V2.6-Pro | 28 | hybrid | nvlink5 | infiniband_ndr | 143 | 347.84 us | 287.5 tok/s | 2,874.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x28-nvl72-tensor | MiMo-V2.6-Pro | 28 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.53 us | 292.8 tok/s | 2,928.0 tok/s | 140 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 341.53 us |
| MiMo-V2.6-Pro/b200_sxm-x28-expert | MiMo-V2.6-Pro | 28 | expert | nvlink5 | infiniband_ndr | 280 | 631.70 us | 158.3 tok/s | 1,583.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 294.03 us |
| MiMo-V2.6-Pro/b200_sxm-x28-nvl72-expert | MiMo-V2.6-Pro | 28 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.08 us | 196.0 tok/s | 1,960.5 tok/s | 140 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 341.53 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.55 us |
| MiMo-V2.6-Pro/b200_sxm-x29-pipeline | MiMo-V2.6-Pro | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.17 us | 2,690.4 tok/s | 26,904.4 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.34 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x29-tensor | MiMo-V2.6-Pro | 29 | tensor | nvlink5 | infiniband_ndr | 280 | 986.83 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x29-hybrid | MiMo-V2.6-Pro | 29 | hybrid | nvlink5 | infiniband_ndr | 143 | 347.84 us | 287.5 tok/s | 2,874.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x29-nvl72-tensor | MiMo-V2.6-Pro | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.54 us | 292.8 tok/s | 2,927.9 tok/s | 140 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 341.54 us |
| MiMo-V2.6-Pro/b200_sxm-x29-expert | MiMo-V2.6-Pro | 29 | expert | nvlink5 | infiniband_ndr | 280 | 631.36 us | 158.4 tok/s | 1,583.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 293.69 us |
| MiMo-V2.6-Pro/b200_sxm-x29-nvl72-expert | MiMo-V2.6-Pro | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.06 us | 196.1 tok/s | 1,960.5 tok/s | 140 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 341.54 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.53 us |
| MiMo-V2.6-Pro/b200_sxm-x30-pipeline | MiMo-V2.6-Pro | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.38 us | 2,605.4 tok/s | 26,053.7 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.55 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x30-tensor | MiMo-V2.6-Pro | 30 | tensor | nvlink5 | infiniband_ndr | 280 | 986.83 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x30-hybrid | MiMo-V2.6-Pro | 30 | hybrid | nvlink5 | infiniband_ndr | 143 | 347.84 us | 287.5 tok/s | 2,874.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x30-nvl72-tensor | MiMo-V2.6-Pro | 30 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.54 us | 292.8 tok/s | 2,927.9 tok/s | 140 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 341.54 us |
| MiMo-V2.6-Pro/b200_sxm-x30-expert | MiMo-V2.6-Pro | 30 | expert | nvlink5 | infiniband_ndr | 280 | 631.05 us | 158.5 tok/s | 1,584.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 293.38 us |
| MiMo-V2.6-Pro/b200_sxm-x30-nvl72-expert | MiMo-V2.6-Pro | 30 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.05 us | 196.1 tok/s | 1,960.6 tok/s | 140 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 341.54 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.51 us |
| MiMo-V2.6-Pro/b200_sxm-x48-pipeline | MiMo-V2.6-Pro | 48 | pipeline | nvlink5 | infiniband_ndr | 47 | 62.35 us | 1,603.8 tok/s | 16,037.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.97 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.38 us |
| MiMo-V2.6-Pro/b200_sxm-x48-tensor | MiMo-V2.6-Pro | 48 | tensor | nvlink5 | infiniband_ndr | 280 | 995.43 us | 100.5 tok/s | 1,004.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 654.42 us |
| MiMo-V2.6-Pro/b200_sxm-x48-hybrid | MiMo-V2.6-Pro | 48 | hybrid | nvlink5 | infiniband_ndr | 145 | 352.40 us | 283.8 tok/s | 2,837.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.38 us |
| MiMo-V2.6-Pro/b200_sxm-x48-nvl72-tensor | MiMo-V2.6-Pro | 48 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.61 us | 292.7 tok/s | 2,927.3 tok/s | 140 x all_reduce span 48 on nvlink5_nvl72 (traversals 2.0) = 341.61 us |
| MiMo-V2.6-Pro/b200_sxm-x48-expert | MiMo-V2.6-Pro | 48 | expert | nvlink5 | infiniband_ndr | 280 | 626.77 us | 159.5 tok/s | 1,595.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.84 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 289.93 us |
| MiMo-V2.6-Pro/b200_sxm-x48-nvl72-expert | MiMo-V2.6-Pro | 48 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.93 us | 196.1 tok/s | 1,961.0 tok/s | 140 x all_reduce span 48 on nvlink5_nvl72 (traversals 2.0) = 341.61 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.32 us |
| MiMo-V2.6-Pro/b200_sxm-x50-pipeline | MiMo-V2.6-Pro | 50 | pipeline | nvlink5 | infiniband_ndr | 49 | 65.84 us | 1,518.8 tok/s | 15,188.0 tok/s | 43 x point_to_point span 2 on nvlink5 (traversals 1.0) = 52.19 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x50-tensor | MiMo-V2.6-Pro | 50 | tensor | nvlink5 | infiniband_ndr | 280 | 997.89 us | 100.2 tok/s | 1,002.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 656.87 us |
| MiMo-V2.6-Pro/b200_sxm-x50-hybrid | MiMo-V2.6-Pro | 50 | hybrid | nvlink5 | infiniband_ndr | 146 | 354.67 us | 282.0 tok/s | 2,819.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x50-nvl72-tensor | MiMo-V2.6-Pro | 50 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.62 us | 292.7 tok/s | 2,927.2 tok/s | 140 x all_reduce span 50 on nvlink5_nvl72 (traversals 2.0) = 341.62 us |
| MiMo-V2.6-Pro/b200_sxm-x50-expert | MiMo-V2.6-Pro | 50 | expert | nvlink5 | infiniband_ndr | 280 | 626.54 us | 159.6 tok/s | 1,596.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.84 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 289.71 us |
| MiMo-V2.6-Pro/b200_sxm-x50-nvl72-expert | MiMo-V2.6-Pro | 50 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.93 us | 196.1 tok/s | 1,961.1 tok/s | 140 x all_reduce span 50 on nvlink5_nvl72 (traversals 2.0) = 341.62 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.31 us |
| MiMo-V2.6-Pro/b200_sxm-x53-pipeline | MiMo-V2.6-Pro | 53 | pipeline | nvlink5 | infiniband_ndr | 52 | 69.48 us | 1,439.2 tok/s | 14,392.1 tok/s | 46 x point_to_point span 2 on nvlink5 (traversals 1.0) = 55.83 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x53-tensor | MiMo-V2.6-Pro | 53 | tensor | nvlink5 | infiniband_ndr | 280 | 997.89 us | 100.2 tok/s | 1,002.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 656.87 us |
| MiMo-V2.6-Pro/b200_sxm-x53-hybrid | MiMo-V2.6-Pro | 53 | hybrid | nvlink5 | infiniband_ndr | 146 | 354.67 us | 282.0 tok/s | 2,819.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | MiMo-V2.6-Pro | 53 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.63 us | 292.7 tok/s | 2,927.2 tok/s | 140 x all_reduce span 53 on nvlink5_nvl72 (traversals 2.0) = 341.63 us |
| MiMo-V2.6-Pro/b200_sxm-x53-expert | MiMo-V2.6-Pro | 53 | expert | nvlink5 | infiniband_ndr | 280 | 626.23 us | 159.7 tok/s | 1,596.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.84 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 289.39 us |
| MiMo-V2.6-Pro/b200_sxm-x53-nvl72-expert | MiMo-V2.6-Pro | 53 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.91 us | 196.1 tok/s | 1,961.1 tok/s | 140 x all_reduce span 53 on nvlink5_nvl72 (traversals 2.0) = 341.63 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.29 us |
| MiMo-V2.6-Pro/b200_sxm-x58-pipeline | MiMo-V2.6-Pro | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 76.61 us | 1,305.3 tok/s | 13,052.6 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.68 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x58-tensor | MiMo-V2.6-Pro | 58 | tensor | nvlink5 | infiniband_ndr | 280 | 999.73 us | 100.0 tok/s | 1,000.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 658.72 us |
| MiMo-V2.6-Pro/b200_sxm-x58-hybrid | MiMo-V2.6-Pro | 58 | hybrid | nvlink5 | infiniband_ndr | 147 | 356.95 us | 280.2 tok/s | 2,801.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x58-nvl72-tensor | MiMo-V2.6-Pro | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.64 us | 292.7 tok/s | 2,927.1 tok/s | 140 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 341.64 us |
| MiMo-V2.6-Pro/b200_sxm-x58-expert | MiMo-V2.6-Pro | 58 | expert | nvlink5 | infiniband_ndr | 280 | 625.66 us | 159.8 tok/s | 1,598.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.72 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.95 us |
| MiMo-V2.6-Pro/b200_sxm-x58-nvl72-expert | MiMo-V2.6-Pro | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.90 us | 196.1 tok/s | 1,961.2 tok/s | 140 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 341.64 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.26 us |
| MiMo-V2.6-Pro/b200_sxm-x61-pipeline | MiMo-V2.6-Pro | 61 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.25 us | 1,246.0 tok/s | 12,460.4 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.32 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x61-tensor | MiMo-V2.6-Pro | 61 | tensor | nvlink5 | infiniband_ndr | 280 | 999.73 us | 100.0 tok/s | 1,000.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 658.72 us |
| MiMo-V2.6-Pro/b200_sxm-x61-hybrid | MiMo-V2.6-Pro | 61 | hybrid | nvlink5 | infiniband_ndr | 147 | 356.95 us | 280.2 tok/s | 2,801.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x61-nvl72-tensor | MiMo-V2.6-Pro | 61 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.64 us | 292.7 tok/s | 2,927.1 tok/s | 140 x all_reduce span 61 on nvlink5_nvl72 (traversals 2.0) = 341.64 us |
| MiMo-V2.6-Pro/b200_sxm-x61-expert | MiMo-V2.6-Pro | 61 | expert | nvlink5 | infiniband_ndr | 280 | 625.43 us | 159.9 tok/s | 1,598.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.72 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.71 us |
| MiMo-V2.6-Pro/b200_sxm-x61-nvl72-expert | MiMo-V2.6-Pro | 61 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.89 us | 196.1 tok/s | 1,961.2 tok/s | 140 x all_reduce span 61 on nvlink5_nvl72 (traversals 2.0) = 341.64 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.25 us |
| MiMo-V2.6-Pro/b200_sxm-x63-pipeline | MiMo-V2.6-Pro | 63 | pipeline | nvlink5 | infiniband_ndr | 62 | 82.68 us | 1,209.5 tok/s | 12,094.6 tok/s | 55 x point_to_point span 2 on nvlink5 (traversals 1.0) = 66.75 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x63-tensor | MiMo-V2.6-Pro | 63 | tensor | nvlink5 | infiniband_ndr | 280 | 999.73 us | 100.0 tok/s | 1,000.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 658.72 us |
| MiMo-V2.6-Pro/b200_sxm-x63-hybrid | MiMo-V2.6-Pro | 63 | hybrid | nvlink5 | infiniband_ndr | 147 | 356.95 us | 280.2 tok/s | 2,801.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x63-nvl72-tensor | MiMo-V2.6-Pro | 63 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.64 us | 292.7 tok/s | 2,927.0 tok/s | 140 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 341.64 us |
| MiMo-V2.6-Pro/b200_sxm-x63-expert | MiMo-V2.6-Pro | 63 | expert | nvlink5 | infiniband_ndr | 280 | 625.29 us | 159.9 tok/s | 1,599.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.72 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.57 us |
| MiMo-V2.6-Pro/b200_sxm-x63-nvl72-expert | MiMo-V2.6-Pro | 63 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.89 us | 196.1 tok/s | 1,961.2 tok/s | 140 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 341.64 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.24 us |
| MiMo-V2.6-Pro/b200_sxm-x70-pipeline | MiMo-V2.6-Pro | 70 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x70-tensor | MiMo-V2.6-Pro | 70 | tensor | nvlink5 | infiniband_ndr | 280 | 1,001.17 us | 99.9 tok/s | 998.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 660.15 us |
| MiMo-V2.6-Pro/b200_sxm-x70-hybrid | MiMo-V2.6-Pro | 70 | hybrid | nvlink5 | infiniband_ndr | 148 | 359.22 us | 278.4 tok/s | 2,783.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x70-nvl72-tensor | MiMo-V2.6-Pro | 70 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.65 us | 292.7 tok/s | 2,927.0 tok/s | 140 x all_reduce span 70 on nvlink5_nvl72 (traversals 2.0) = 341.65 us |
| MiMo-V2.6-Pro/b200_sxm-x70-expert | MiMo-V2.6-Pro | 70 | expert | nvlink5 | infiniband_ndr | 280 | 624.76 us | 160.1 tok/s | 1,600.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.63 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.13 us |
| MiMo-V2.6-Pro/b200_sxm-x70-nvl72-expert | MiMo-V2.6-Pro | 70 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.87 us | 196.1 tok/s | 1,961.3 tok/s | 140 x all_reduce span 70 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.22 us |
| MiMo-V2.6-Pro/b200_sxm-x72-pipeline | MiMo-V2.6-Pro | 72 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x72-tensor | MiMo-V2.6-Pro | 72 | tensor | nvlink5 | infiniband_ndr | 280 | 1,001.17 us | 99.9 tok/s | 998.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 660.15 us |
| MiMo-V2.6-Pro/b200_sxm-x72-hybrid | MiMo-V2.6-Pro | 72 | hybrid | nvlink5 | infiniband_ndr | 148 | 359.22 us | 278.4 tok/s | 2,783.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x72-nvl72-tensor | MiMo-V2.6-Pro | 72 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.65 us | 292.7 tok/s | 2,926.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us |
| MiMo-V2.6-Pro/b200_sxm-x72-expert | MiMo-V2.6-Pro | 72 | expert | nvlink5 | infiniband_ndr | 280 | 624.58 us | 160.1 tok/s | 1,601.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.56 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.02 us |
| MiMo-V2.6-Pro/b200_sxm-x72-nvl72-expert | MiMo-V2.6-Pro | 72 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.87 us | 196.1 tok/s | 1,961.3 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.21 us |
| MiMo-V2.6-Pro/b200_sxm-x75-pipeline | MiMo-V2.6-Pro | 75 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x75-tensor | MiMo-V2.6-Pro | 75 | tensor | nvlink5 | infiniband_ndr | 280 | 1,002.31 us | 99.8 tok/s | 997.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 661.30 us |
| MiMo-V2.6-Pro/b200_sxm-x75-hybrid | MiMo-V2.6-Pro | 75 | hybrid | nvlink5 | infiniband_ndr | 149 | 361.50 us | 276.6 tok/s | 2,766.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.48 us |
| MiMo-V2.6-Pro/b200_sxm-x75-nvl72-tensor | MiMo-V2.6-Pro | 75 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x75-nvl72-hybrid | MiMo-V2.6-Pro | 75 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x75-expert | MiMo-V2.6-Pro | 75 | expert | nvlink5 | infiniband_ndr | 280 | 624.43 us | 160.1 tok/s | 1,601.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.56 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.87 us |
| MiMo-V2.6-Pro/b200_sxm-x75-nvl72-expert | MiMo-V2.6-Pro | 75 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.52 us | 158.8 tok/s | 1,588.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.87 us |
| MiMo-V2.6-Pro/b200_sxm-x78-pipeline | MiMo-V2.6-Pro | 78 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x78-tensor | MiMo-V2.6-Pro | 78 | tensor | nvlink5 | infiniband_ndr | 280 | 1,002.31 us | 99.8 tok/s | 997.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 661.30 us |
| MiMo-V2.6-Pro/b200_sxm-x78-hybrid | MiMo-V2.6-Pro | 78 | hybrid | nvlink5 | infiniband_ndr | 149 | 361.50 us | 276.6 tok/s | 2,766.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.48 us |
| MiMo-V2.6-Pro/b200_sxm-x78-nvl72-tensor | MiMo-V2.6-Pro | 78 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x78-nvl72-hybrid | MiMo-V2.6-Pro | 78 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x78-expert | MiMo-V2.6-Pro | 78 | expert | nvlink5 | infiniband_ndr | 280 | 624.29 us | 160.2 tok/s | 1,601.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.56 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.73 us |
| MiMo-V2.6-Pro/b200_sxm-x78-nvl72-expert | MiMo-V2.6-Pro | 78 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.38 us | 158.9 tok/s | 1,588.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.73 us |
| MiMo-V2.6-Pro/b200_sxm-x79-pipeline | MiMo-V2.6-Pro | 79 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x79-tensor | MiMo-V2.6-Pro | 79 | tensor | nvlink5 | infiniband_ndr | 280 | 1,002.31 us | 99.8 tok/s | 997.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 661.30 us |
| MiMo-V2.6-Pro/b200_sxm-x79-hybrid | MiMo-V2.6-Pro | 79 | hybrid | nvlink5 | infiniband_ndr | 149 | 361.50 us | 276.6 tok/s | 2,766.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.48 us |
| MiMo-V2.6-Pro/b200_sxm-x79-nvl72-tensor | MiMo-V2.6-Pro | 79 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x79-nvl72-hybrid | MiMo-V2.6-Pro | 79 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x79-expert | MiMo-V2.6-Pro | 79 | expert | nvlink5 | infiniband_ndr | 280 | 624.24 us | 160.2 tok/s | 1,601.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.56 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.68 us |
| MiMo-V2.6-Pro/b200_sxm-x79-nvl72-expert | MiMo-V2.6-Pro | 79 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.34 us | 158.9 tok/s | 1,589.0 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.68 us |
| MiMo-V2.6-Pro/b200_sxm-x87-pipeline | MiMo-V2.6-Pro | 87 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x87-tensor | MiMo-V2.6-Pro | 87 | tensor | nvlink5 | infiniband_ndr | 280 | 1,003.25 us | 99.7 tok/s | 996.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 662.24 us |
| MiMo-V2.6-Pro/b200_sxm-x87-hybrid | MiMo-V2.6-Pro | 87 | hybrid | nvlink5 | infiniband_ndr | 150 | 363.78 us | 274.9 tok/s | 2,749.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.76 us |
| MiMo-V2.6-Pro/b200_sxm-x87-nvl72-tensor | MiMo-V2.6-Pro | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x87-nvl72-hybrid | MiMo-V2.6-Pro | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x87-expert | MiMo-V2.6-Pro | 87 | expert | nvlink5 | infiniband_ndr | 280 | 623.87 us | 160.3 tok/s | 1,602.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.50 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.36 us |
| MiMo-V2.6-Pro/b200_sxm-x87-nvl72-expert | MiMo-V2.6-Pro | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.02 us | 159.0 tok/s | 1,589.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.36 us |
| MiMo-V2.6-Pro/b200_sxm-x93-pipeline | MiMo-V2.6-Pro | 93 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x93-tensor | MiMo-V2.6-Pro | 93 | tensor | nvlink5 | infiniband_ndr | 280 | 1,004.04 us | 99.6 tok/s | 996.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 663.02 us |
| MiMo-V2.6-Pro/b200_sxm-x93-hybrid | MiMo-V2.6-Pro | 93 | hybrid | nvlink5 | infiniband_ndr | 151 | 366.05 us | 273.2 tok/s | 2,731.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.03 us |
| MiMo-V2.6-Pro/b200_sxm-x93-nvl72-tensor | MiMo-V2.6-Pro | 93 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x93-nvl72-hybrid | MiMo-V2.6-Pro | 93 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x93-expert | MiMo-V2.6-Pro | 93 | expert | nvlink5 | infiniband_ndr | 280 | 623.62 us | 160.4 tok/s | 1,603.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.46 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.16 us |
| MiMo-V2.6-Pro/b200_sxm-x93-nvl72-expert | MiMo-V2.6-Pro | 93 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.81 us | 159.0 tok/s | 1,590.3 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.16 us |
| MiMo-V2.6-Pro/b200_sxm-x100-pipeline | MiMo-V2.6-Pro | 100 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x100-tensor | MiMo-V2.6-Pro | 100 | tensor | nvlink5 | infiniband_ndr | 280 | 1,004.70 us | 99.5 tok/s | 995.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 663.68 us |
| MiMo-V2.6-Pro/b200_sxm-x100-hybrid | MiMo-V2.6-Pro | 100 | hybrid | nvlink5 | infiniband_ndr | 152 | 368.33 us | 271.5 tok/s | 2,715.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.31 us |
| MiMo-V2.6-Pro/b200_sxm-x100-nvl72-tensor | MiMo-V2.6-Pro | 100 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x100-nvl72-hybrid | MiMo-V2.6-Pro | 100 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x100-expert | MiMo-V2.6-Pro | 100 | expert | nvlink5 | infiniband_ndr | 280 | 623.37 us | 160.4 tok/s | 1,604.2 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.42 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.95 us |
| MiMo-V2.6-Pro/b200_sxm-x100-nvl72-expert | MiMo-V2.6-Pro | 100 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.61 us | 159.1 tok/s | 1,590.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.95 us |
| MiMo-V2.6-Pro/b200_sxm-x116-pipeline | MiMo-V2.6-Pro | 116 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x116-tensor | MiMo-V2.6-Pro | 116 | tensor | nvlink5 | infiniband_ndr | 280 | 1,005.76 us | 99.4 tok/s | 994.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 664.74 us |
| MiMo-V2.6-Pro/b200_sxm-x116-hybrid | MiMo-V2.6-Pro | 116 | hybrid | nvlink5 | infiniband_ndr | 154 | 372.88 us | 268.2 tok/s | 2,681.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.86 us |
| MiMo-V2.6-Pro/b200_sxm-x116-nvl72-tensor | MiMo-V2.6-Pro | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x116-nvl72-hybrid | MiMo-V2.6-Pro | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x116-expert | MiMo-V2.6-Pro | 116 | expert | nvlink5 | infiniband_ndr | 280 | 622.93 us | 160.5 tok/s | 1,605.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.36 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.57 us |
| MiMo-V2.6-Pro/b200_sxm-x116-nvl72-expert | MiMo-V2.6-Pro | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.23 us | 159.2 tok/s | 1,591.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.57 us |
| MiMo-V2.6-Pro/b200_sxm-x139-pipeline | MiMo-V2.6-Pro | 139 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x139-tensor | MiMo-V2.6-Pro | 139 | tensor | nvlink5 | infiniband_ndr | 280 | 1,006.90 us | 99.3 tok/s | 993.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 665.88 us |
| MiMo-V2.6-Pro/b200_sxm-x139-hybrid | MiMo-V2.6-Pro | 139 | hybrid | nvlink5 | infiniband_ndr | 157 | 379.71 us | 263.4 tok/s | 2,633.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 38.69 us |
| MiMo-V2.6-Pro/b200_sxm-x139-nvl72-tensor | MiMo-V2.6-Pro | 139 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x139-nvl72-hybrid | MiMo-V2.6-Pro | 139 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x139-expert | MiMo-V2.6-Pro | 139 | expert | nvlink5 | infiniband_ndr | 280 | 622.48 us | 160.6 tok/s | 1,606.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.30 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.18 us |
| MiMo-V2.6-Pro/b200_sxm-x139-nvl72-expert | MiMo-V2.6-Pro | 139 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 627.83 us | 159.3 tok/s | 1,592.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.18 us |
| MiMo-V2.6-Pro/b200_sxm-x150-pipeline | MiMo-V2.6-Pro | 150 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x150-tensor | MiMo-V2.6-Pro | 150 | tensor | nvlink5 | infiniband_ndr | 280 | 1,007.20 us | 99.3 tok/s | 992.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 666.19 us |
| MiMo-V2.6-Pro/b200_sxm-x150-hybrid | MiMo-V2.6-Pro | 150 | hybrid | nvlink5 | infiniband_ndr | 158 | 381.98 us | 261.8 tok/s | 2,617.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 40.96 us |
| MiMo-V2.6-Pro/b200_sxm-x150-nvl72-tensor | MiMo-V2.6-Pro | 150 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x150-nvl72-hybrid | MiMo-V2.6-Pro | 150 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x150-expert | MiMo-V2.6-Pro | 150 | expert | nvlink5 | infiniband_ndr | 280 | 622.31 us | 160.7 tok/s | 1,606.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.28 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.04 us |
| MiMo-V2.6-Pro/b200_sxm-x150-nvl72-expert | MiMo-V2.6-Pro | 150 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.86 us | 160.0 tok/s | 1,600.4 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.04 us |
| MiMo-V2.6-Pro/b200_sxm-x173-pipeline | MiMo-V2.6-Pro | 173 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x173-tensor | MiMo-V2.6-Pro | 173 | tensor | nvlink5 | infiniband_ndr | 280 | 1,007.95 us | 99.2 tok/s | 992.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 666.93 us |
| MiMo-V2.6-Pro/b200_sxm-x173-hybrid | MiMo-V2.6-Pro | 173 | hybrid | nvlink5 | infiniband_ndr | 161 | 388.81 us | 257.2 tok/s | 2,572.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.79 us |
| MiMo-V2.6-Pro/b200_sxm-x173-nvl72-tensor | MiMo-V2.6-Pro | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x173-nvl72-hybrid | MiMo-V2.6-Pro | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x173-expert | MiMo-V2.6-Pro | 173 | expert | nvlink5 | infiniband_ndr | 280 | 622.03 us | 160.8 tok/s | 1,607.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.24 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.79 us |
| MiMo-V2.6-Pro/b200_sxm-x173-nvl72-expert | MiMo-V2.6-Pro | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.62 us | 160.1 tok/s | 1,601.0 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.79 us |
| MiMo-V2.6-Pro/b200_sxm-x185-pipeline | MiMo-V2.6-Pro | 185 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x185-tensor | MiMo-V2.6-Pro | 185 | tensor | nvlink5 | infiniband_ndr | 280 | 1,008.34 us | 99.2 tok/s | 991.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 667.32 us |
| MiMo-V2.6-Pro/b200_sxm-x185-hybrid | MiMo-V2.6-Pro | 185 | hybrid | nvlink5 | infiniband_ndr | 163 | 393.36 us | 254.2 tok/s | 2,542.2 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 52.34 us |
| MiMo-V2.6-Pro/b200_sxm-x185-nvl72-tensor | MiMo-V2.6-Pro | 185 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x185-nvl72-hybrid | MiMo-V2.6-Pro | 185 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x185-expert | MiMo-V2.6-Pro | 185 | expert | nvlink5 | infiniband_ndr | 280 | 621.91 us | 160.8 tok/s | 1,608.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.22 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.69 us |
| MiMo-V2.6-Pro/b200_sxm-x185-nvl72-expert | MiMo-V2.6-Pro | 185 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.52 us | 160.1 tok/s | 1,601.2 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.69 us |
| MiMo-V2.6-Pro/b200_sxm-x200-pipeline | MiMo-V2.6-Pro | 200 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x200-tensor | MiMo-V2.6-Pro | 200 | tensor | nvlink5 | infiniband_ndr | 280 | 1,008.51 us | 99.2 tok/s | 991.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 667.49 us |
| MiMo-V2.6-Pro/b200_sxm-x200-hybrid | MiMo-V2.6-Pro | 200 | hybrid | nvlink5 | infiniband_ndr | 164 | 395.64 us | 252.8 tok/s | 2,527.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 54.62 us |
| MiMo-V2.6-Pro/b200_sxm-x200-nvl72-tensor | MiMo-V2.6-Pro | 200 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x200-nvl72-hybrid | MiMo-V2.6-Pro | 200 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x200-expert | MiMo-V2.6-Pro | 200 | expert | nvlink5 | infiniband_ndr | 280 | 621.78 us | 160.8 tok/s | 1,608.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.20 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.58 us |
| MiMo-V2.6-Pro/b200_sxm-x200-nvl72-expert | MiMo-V2.6-Pro | 200 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.40 us | 160.2 tok/s | 1,601.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.58 us |
| MiMo-V2.6-Pro/b200_sxm-x231-pipeline | MiMo-V2.6-Pro | 231 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x231-tensor | MiMo-V2.6-Pro | 231 | tensor | nvlink5 | infiniband_ndr | 280 | 1,009.08 us | 99.1 tok/s | 991.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 668.06 us |
| MiMo-V2.6-Pro/b200_sxm-x231-hybrid | MiMo-V2.6-Pro | 231 | hybrid | nvlink5 | infiniband_ndr | 168 | 404.74 us | 247.1 tok/s | 2,470.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 63.72 us |
| MiMo-V2.6-Pro/b200_sxm-x231-nvl72-tensor | MiMo-V2.6-Pro | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 987.47 us | 101.3 tok/s | 1,012.7 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x231-nvl72-hybrid | MiMo-V2.6-Pro | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 143 | 348.48 us | 287.0 tok/s | 2,869.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x231-expert | MiMo-V2.6-Pro | 231 | expert | nvlink5 | infiniband_ndr | 280 | 621.57 us | 160.9 tok/s | 1,608.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.18 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.39 us |
| MiMo-V2.6-Pro/b200_sxm-x231-nvl72-expert | MiMo-V2.6-Pro | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 623.28 us | 160.4 tok/s | 1,604.4 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 337.88 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.39 us |
| MiMo-V2.6-Pro/b200_sxm-x347-pipeline | MiMo-V2.6-Pro | 347 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x347-tensor | MiMo-V2.6-Pro | 347 | tensor | nvlink5 | infiniband_ndr | 280 | 1,010.29 us | 99.0 tok/s | 989.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 669.27 us |
| MiMo-V2.6-Pro/b200_sxm-x347-hybrid | MiMo-V2.6-Pro | 347 | hybrid | nvlink5 | infiniband_ndr | 183 | 438.88 us | 227.9 tok/s | 2,278.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 97.86 us |
| MiMo-V2.6-Pro/b200_sxm-x347-nvl72-tensor | MiMo-V2.6-Pro | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 992.63 us | 100.7 tok/s | 1,007.4 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 650.98 us |
| MiMo-V2.6-Pro/b200_sxm-x347-nvl72-hybrid | MiMo-V2.6-Pro | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 144 | 350.76 us | 285.1 tok/s | 2,851.0 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.10 us |
| MiMo-V2.6-Pro/b200_sxm-x347-expert | MiMo-V2.6-Pro | 347 | expert | nvlink5 | infiniband_ndr | 280 | 621.11 us | 161.0 tok/s | 1,610.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.12 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 284.99 us |
| MiMo-V2.6-Pro/b200_sxm-x347-nvl72-expert | MiMo-V2.6-Pro | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 622.41 us | 160.7 tok/s | 1,606.7 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 337.41 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 284.99 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Pro | 1 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154 | 125,510 | 7,637.0 | 0.061 | 7,637.0 (125,510) | 3,267.7 (92,450) | 0.43x | compute |
| MiMo-V2.6-Pro | 2 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154 | 125,510 | 7,637.0 | 0.061 | 7,637.0 (125,510) | 3,348.0 (138,675) | 0.44x | compute |
| MiMo-V2.6-Pro | 4 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154 | 125,510 | 7,637.0 | 0.061 | 7,637.0 (125,510) | 3,299.5 (138,675) | 0.43x | compute |
| MiMo-V2.6-Pro | 8 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154 | 125,510 | 7,637.0 | 0.061 | 7,637.0 (125,510) | 3,205.4 (184,900) | 0.42x | compute |
| MiMo-V2.6-Pro | 16 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154 | 125,510 | 7,637.0 | 0.061 | 7,637.0 (125,510) | 3,201.1 (369,800) | 0.42x | compute |
| MiMo-V2.6-Pro | 32 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x154 | 125,510 | 7,637.0 | 0.061 | 7,637.0 (125,510) | 3,109.4 (554,700) | 0.41x | compute |
| MiMo-V2.6-Pro | 64 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill | 185,005 | 7,029.1 | 0.038 | 7,029.1 (185,005) | 2,802.5 (554,700) | 0.40x | weight_read |
| MiMo-V2.6-Pro | 256 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 3,705.5 | 0.012 | 3,705.5 (319,480) | 1,760.3 (554,700) | 0.48x | compute |
| MiMo-V2.6-Pro | 1024 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x294 | 239,610 | 1,163.8 | 0.005 | 1,163.8 (239,610) | 870.2 (554,700) | 0.75x | weight_read |
| MiMo-V2.6-Pro | 4096 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392 | 319,480 | 428.3 | 0.001 | 428.3 (319,480) | 221.1 (554,700) | 0.52x | weight_read |

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
| MiMo-V2.6-Pro | 384 | 1,383.7 MB | 236.0 mm2 | 42.49 mm2 (18.0%) | 90,640 mm2 | 16,315 mm2 | 96,556 mm2 = 118.5 reticles |

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
| MiMo-V2.6-Pro | 1 | sram | 370,722.5 | 26,016.2 | 26,016.2 | 14.25x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | sram | 370,722.5 | 26,016.2 | 26,016.2 | 14.25x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | sram | 370,722.5 | 26,016.2 | 26,016.2 | 14.25x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | sram | 370,722.5 | 26,016.2 | 35,958.7 | 14.25x | 1.38x | weight_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 16 | sram | 370,722.5 | 26,016.2 | 57,137.1 | 14.25x | 2.20x | weight_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 32 | sram | 370,722.5 | 26,016.2 | 84,270.1 | 14.25x | 3.24x | weight_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 64 | sram | 395,417.9 | 26,016.2 | 114,081.7 | 15.20x | 4.39x | compute | weight_read | link_latency |
| MiMo-V2.6-Pro | 256 | sram | 758,993.4 | 26,064.3 | 181,472.4 | 29.12x | 6.96x | compute | weight_read | kv_read |
| MiMo-V2.6-Pro | 1024 | sram | 1,191,709.1 | 26,098.9 | 310,986.6 | 45.66x | 11.92x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4096 | sram | 1,754,397.5 | 26,109.1 | 331,951.1 | 67.19x | 12.71x | weight_read | weight_read | thermal |
| MiMo-V2.6-Pro | 1 | rom | 881,611.9 | 93,354.8 | 93,354.8 | 9.44x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | rom | 881,611.9 | 93,354.8 | 93,354.8 | 9.44x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | rom | 881,611.9 | 93,354.8 | 93,354.8 | 9.44x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | rom | 881,611.9 | 93,354.8 | 93,354.8 | 9.44x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 16 | rom | 881,611.9 | 93,354.8 | 93,354.8 | 9.44x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 32 | rom | 881,611.9 | 93,354.8 | 93,354.8 | 9.44x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 64 | rom | 881,611.9 | 93,354.8 | 119,868.8 | 9.44x | 1.28x | kv_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 256 | rom | 948,614.7 | 93,769.5 | 181,472.4 | 10.12x | 1.94x | compute | weight_read | kv_read |
| MiMo-V2.6-Pro | 1024 | rom | 1,043,640.8 | 94,402.3 | 336,817.7 | 11.06x | 3.57x | compute | weight_read | weight_read |
| MiMo-V2.6-Pro | 4096 | rom | 1,058,215.7 | 94,561.8 | 376,423.1 | 11.19x | 3.98x | compute | weight_read | thermal |

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
| MiMo-V2.6-Pro | 1 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 370,722.5 | 0.668 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 1 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 881,611.9 | 1.589 | kv_read | 2.38x |
| MiMo-V2.6-Pro | 1 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 1 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 1 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 1 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 2 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 370,722.5 | 0.668 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 2 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 881,611.9 | 1.589 | kv_read | 2.38x |
| MiMo-V2.6-Pro | 2 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 2 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 2 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 2 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 4 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 370,722.5 | 0.668 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 4 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 881,611.9 | 1.589 | kv_read | 2.38x |
| MiMo-V2.6-Pro | 4 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 4 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 4 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 4 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 8 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 370,722.5 | 0.668 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 8 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 881,611.9 | 1.589 | kv_read | 2.38x |
| MiMo-V2.6-Pro | 8 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 8 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 8 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x52-perregion | 42,380 | 1.00 | 2.16 | 35,958.7 | 0.848 | link_latency | 0.10x |
| MiMo-V2.6-Pro | 8 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 16 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 370,722.5 | 0.668 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 16 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 881,611.9 | 1.589 | kv_read | 2.38x |
| MiMo-V2.6-Pro | 16 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 16 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 16 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x52-perregion | 42,380 | 1.00 | 2.90 | 57,137.1 | 1.348 | link_latency | 0.15x |
| MiMo-V2.6-Pro | 16 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 32 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 370,722.5 | 0.668 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 32 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 881,611.9 | 1.589 | kv_read | 2.38x |
| MiMo-V2.6-Pro | 32 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 32 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 32 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x52-perregion | 42,380 | 1.00 | 4.00 | 84,270.1 | 1.988 | link_latency | 0.23x |
| MiMo-V2.6-Pro | 32 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 64 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 1.00 | 1.00 | 395,417.9 | 2.854 | compute | 1.00x |
| MiMo-V2.6-Pro | 64 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 881,611.9 | 1.589 | kv_read | 2.23x |
| MiMo-V2.6-Pro | 64 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,016.2 | 0.188 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 64 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 93,354.8 | 0.673 | weight_read | 0.24x |
| MiMo-V2.6-Pro | 64 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x52-perregion | 42,380 | 1.00 | 5.71 | 114,081.7 | 2.692 | link_latency | 0.29x |
| MiMo-V2.6-Pro | 64 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x59-perregion-romfill | 48,085 | 1.15 | 5.71 | 119,868.8 | 2.493 | link_latency | 0.30x |
| MiMo-V2.6-Pro | 256 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1.00 | 1.00 | 758,993.4 | 4.103 | compute | 1.00x |
| MiMo-V2.6-Pro | 256 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 2.32 | 1.00 | 948,614.7 | 2.969 | compute | 1.25x |
| MiMo-V2.6-Pro | 256 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x52-perstream | 42,380 | 1.00 | 4.92 | 26,064.3 | 0.615 | weight_read | 0.03x |
| MiMo-V2.6-Pro | 256 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.50 | 93,769.5 | 0.676 | weight_read | 0.12x |
| MiMo-V2.6-Pro | 256 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 6.70 | 181,472.4 | 1.309 | kv_read | 0.24x |
| MiMo-V2.6-Pro | 256 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 3.62 | 6.70 | 181,472.4 | 1.309 | kv_read | 0.24x |
| MiMo-V2.6-Pro | 1024 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x294 | 239,610 | 1.00 | 1.00 | 1,191,709.1 | 4.974 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x392-romfill | 319,480 | 2.32 | 1.00 | 1,043,640.8 | 3.267 | compute | 0.88x |
| MiMo-V2.6-Pro | 1024 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x52-perstream | 42,380 | 1.00 | 19.69 | 26,098.9 | 0.616 | weight_read | 0.02x |
| MiMo-V2.6-Pro | 1024 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 5.99 | 94,402.3 | 0.681 | weight_read | 0.08x |
| MiMo-V2.6-Pro | 1024 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x52-perregion | 42,380 | 1.00 | 6.41 | 310,986.6 | 7.338 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 1024 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x59-perregion-romfill | 48,085 | 1.15 | 5.91 | 336,817.7 | 7.005 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 4096 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392 | 319,480 | 1.00 | 1.00 | 1,754,397.5 | 5.491 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x392-romfill | 319,480 | 2.32 | 1.00 | 1,058,215.7 | 3.312 | compute | 0.60x |
| MiMo-V2.6-Pro | 4096 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 23.95 | 26,109.1 | 0.188 | weight_read | 0.01x |
| MiMo-V2.6-Pro | 4096 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 23.95 | 94,561.8 | 0.682 | weight_read | 0.05x |
| MiMo-V2.6-Pro | 4096 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x52-perregion | 42,380 | 1.00 | 15.17 | 331,951.1 | 7.833 | thermal | 0.19x |
| MiMo-V2.6-Pro | 4096 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x59-perregion-romfill | 48,085 | 1.15 | 13.77 | 376,423.1 | 7.828 | thermal | 0.21x |

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
| MiMo-V2.6-Pro | 1 | 47 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 2 | 47 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 64 | 52 | 1.23 | 1.002 | 1.035 | 1.03x |
| MiMo-V2.6-Pro | 256 | 52 | 4.92 | 1.042 | 1.817 | 1.74x |
| MiMo-V2.6-Pro | 1024 | 52 | 19.69 | 1.209 | 3.186 | 2.64x |
| MiMo-V2.6-Pro | 4096 | 52 | 78.77 | 2.027 | 6.408 | 3.16x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 1 | 16 | 6.45 | 4.14 | 1.56x |
| MiMo-V2.6-Pro | 2 | 16 | 10.24 | 5.39 | 1.90x |
| MiMo-V2.6-Pro | 4 | 16 | 13.84 | 6.75 | 2.05x |
| MiMo-V2.6-Pro | 8 | 16 | 15.66 | 8.14 | 1.92x |
| MiMo-V2.6-Pro | 16 | 16 | 15.99 | 9.43 | 1.70x |
| MiMo-V2.6-Pro | 32 | 16 | 16.00 | 10.49 | 1.53x |
| MiMo-V2.6-Pro | 64 | 16 | 16.00 | 11.24 | 1.42x |
| MiMo-V2.6-Pro | 256 | 16 | 16.00 | 11.74 | 1.36x |
| MiMo-V2.6-Pro | 1024 | 16 | 16.00 | 11.74 | 1.36x |
| MiMo-V2.6-Pro | 4096 | 16 | 16.00 | 11.74 | 1.36x |
| MiMo-V2.6-Pro | 1 | 24 | 6.93 | 4.65 | 1.49x |
| MiMo-V2.6-Pro | 2 | 24 | 11.77 | 6.25 | 1.88x |
| MiMo-V2.6-Pro | 4 | 24 | 17.59 | 8.13 | 2.16x |
| MiMo-V2.6-Pro | 8 | 24 | 22.09 | 10.15 | 2.18x |
| MiMo-V2.6-Pro | 16 | 24 | 23.78 | 12.13 | 1.96x |
| MiMo-V2.6-Pro | 32 | 24 | 23.99 | 13.85 | 1.73x |
| MiMo-V2.6-Pro | 64 | 24 | 24.00 | 15.10 | 1.59x |
| MiMo-V2.6-Pro | 256 | 24 | 24.00 | 15.95 | 1.50x |
| MiMo-V2.6-Pro | 1024 | 24 | 24.00 | 15.96 | 1.50x |
| MiMo-V2.6-Pro | 4096 | 24 | 24.00 | 15.96 | 1.50x |
| MiMo-V2.6-Pro | 1 | 26 | 7.00 | 4.76 | 1.47x |
| MiMo-V2.6-Pro | 2 | 26 | 12.03 | 6.42 | 1.87x |
| MiMo-V2.6-Pro | 4 | 26 | 18.30 | 8.41 | 2.18x |
| MiMo-V2.6-Pro | 8 | 26 | 23.48 | 10.58 | 2.22x |
| MiMo-V2.6-Pro | 16 | 26 | 25.65 | 12.72 | 2.02x |
| MiMo-V2.6-Pro | 32 | 26 | 25.98 | 14.59 | 1.78x |
| MiMo-V2.6-Pro | 64 | 26 | 26.00 | 15.97 | 1.63x |
| MiMo-V2.6-Pro | 256 | 26 | 26.00 | 16.91 | 1.54x |
| MiMo-V2.6-Pro | 1024 | 26 | 26.00 | 16.93 | 1.54x |
| MiMo-V2.6-Pro | 4096 | 26 | 26.00 | 16.93 | 1.54x |
| MiMo-V2.6-Pro | 1 | 28 | 7.07 | 4.85 | 1.46x |
| MiMo-V2.6-Pro | 2 | 28 | 12.26 | 6.57 | 1.86x |
| MiMo-V2.6-Pro | 4 | 28 | 18.94 | 8.67 | 2.18x |
| MiMo-V2.6-Pro | 8 | 28 | 24.79 | 10.98 | 2.26x |
| MiMo-V2.6-Pro | 16 | 28 | 27.48 | 13.27 | 2.07x |
| MiMo-V2.6-Pro | 32 | 28 | 27.97 | 15.30 | 1.83x |
| MiMo-V2.6-Pro | 64 | 28 | 28.00 | 16.81 | 1.67x |
| MiMo-V2.6-Pro | 256 | 28 | 28.00 | 17.84 | 1.57x |
| MiMo-V2.6-Pro | 1024 | 28 | 28.00 | 17.86 | 1.57x |
| MiMo-V2.6-Pro | 4096 | 28 | 28.00 | 17.86 | 1.57x |
| MiMo-V2.6-Pro | 1 | 29 | 7.10 | 4.90 | 1.45x |
| MiMo-V2.6-Pro | 2 | 29 | 12.36 | 6.65 | 1.86x |
| MiMo-V2.6-Pro | 4 | 29 | 19.23 | 8.80 | 2.19x |
| MiMo-V2.6-Pro | 8 | 29 | 25.41 | 11.17 | 2.27x |
| MiMo-V2.6-Pro | 16 | 29 | 28.39 | 13.54 | 2.10x |
| MiMo-V2.6-Pro | 32 | 29 | 28.96 | 15.65 | 1.85x |
| MiMo-V2.6-Pro | 64 | 29 | 29.00 | 17.22 | 1.68x |
| MiMo-V2.6-Pro | 256 | 29 | 29.00 | 18.30 | 1.59x |
| MiMo-V2.6-Pro | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| MiMo-V2.6-Pro | 4096 | 29 | 29.00 | 18.31 | 1.58x |
| MiMo-V2.6-Pro | 1 | 30 | 7.13 | 4.94 | 1.44x |
| MiMo-V2.6-Pro | 2 | 30 | 12.46 | 6.72 | 1.86x |
| MiMo-V2.6-Pro | 4 | 30 | 19.52 | 8.92 | 2.19x |
| MiMo-V2.6-Pro | 8 | 30 | 26.01 | 11.36 | 2.29x |
| MiMo-V2.6-Pro | 16 | 30 | 29.28 | 13.81 | 2.12x |
| MiMo-V2.6-Pro | 32 | 30 | 29.95 | 15.99 | 1.87x |
| MiMo-V2.6-Pro | 64 | 30 | 30.00 | 17.62 | 1.70x |
| MiMo-V2.6-Pro | 256 | 30 | 30.00 | 18.74 | 1.60x |
| MiMo-V2.6-Pro | 1024 | 30 | 30.00 | 18.76 | 1.60x |
| MiMo-V2.6-Pro | 4096 | 30 | 30.00 | 18.76 | 1.60x |
| MiMo-V2.6-Pro | 1 | 48 | 7.44 | 5.56 | 1.34x |
| MiMo-V2.6-Pro | 2 | 48 | 13.61 | 7.68 | 1.77x |
| MiMo-V2.6-Pro | 4 | 48 | 23.02 | 10.66 | 2.16x |
| MiMo-V2.6-Pro | 8 | 48 | 34.29 | 14.08 | 2.44x |
| MiMo-V2.6-Pro | 16 | 48 | 43.25 | 17.75 | 2.44x |
| MiMo-V2.6-Pro | 32 | 48 | 47.09 | 21.21 | 2.22x |
| MiMo-V2.6-Pro | 64 | 48 | 47.88 | 23.90 | 2.00x |
| MiMo-V2.6-Pro | 256 | 48 | 47.98 | 25.83 | 1.86x |
| MiMo-V2.6-Pro | 1024 | 48 | 47.99 | 25.86 | 1.86x |
| MiMo-V2.6-Pro | 4096 | 48 | 47.99 | 25.86 | 1.86x |
| MiMo-V2.6-Pro | 1 | 50 | 7.46 | 5.61 | 1.33x |
| MiMo-V2.6-Pro | 2 | 50 | 13.69 | 7.76 | 1.76x |
| MiMo-V2.6-Pro | 4 | 50 | 23.28 | 10.81 | 2.15x |
| MiMo-V2.6-Pro | 8 | 50 | 34.98 | 14.33 | 2.44x |
| MiMo-V2.6-Pro | 16 | 50 | 44.56 | 18.12 | 2.46x |
| MiMo-V2.6-Pro | 32 | 50 | 48.88 | 21.71 | 2.25x |
| MiMo-V2.6-Pro | 64 | 50 | 49.84 | 24.51 | 2.03x |
| MiMo-V2.6-Pro | 256 | 50 | 49.98 | 26.52 | 1.88x |
| MiMo-V2.6-Pro | 1024 | 50 | 49.98 | 26.55 | 1.88x |
| MiMo-V2.6-Pro | 4096 | 50 | 49.98 | 26.55 | 1.88x |
| MiMo-V2.6-Pro | 1 | 53 | 7.49 | 5.69 | 1.32x |
| MiMo-V2.6-Pro | 2 | 53 | 13.80 | 7.88 | 1.75x |
| MiMo-V2.6-Pro | 4 | 53 | 23.64 | 11.04 | 2.14x |
| MiMo-V2.6-Pro | 8 | 53 | 35.94 | 14.69 | 2.45x |
| MiMo-V2.6-Pro | 16 | 53 | 46.46 | 18.65 | 2.49x |
| MiMo-V2.6-Pro | 32 | 53 | 51.53 | 22.43 | 2.30x |
| MiMo-V2.6-Pro | 64 | 53 | 52.76 | 25.40 | 2.08x |
| MiMo-V2.6-Pro | 256 | 53 | 52.96 | 27.54 | 1.92x |
| MiMo-V2.6-Pro | 1024 | 53 | 52.96 | 27.57 | 1.92x |
| MiMo-V2.6-Pro | 4096 | 53 | 52.96 | 27.57 | 1.92x |
| MiMo-V2.6-Pro | 1 | 58 | 7.53 | 5.80 | 1.30x |
| MiMo-V2.6-Pro | 2 | 58 | 13.96 | 8.07 | 1.73x |
| MiMo-V2.6-Pro | 4 | 58 | 24.18 | 11.39 | 2.12x |
| MiMo-V2.6-Pro | 8 | 58 | 37.40 | 15.25 | 2.45x |
| MiMo-V2.6-Pro | 16 | 58 | 49.41 | 19.49 | 2.54x |
| MiMo-V2.6-Pro | 32 | 58 | 55.80 | 23.57 | 2.37x |
| MiMo-V2.6-Pro | 64 | 58 | 57.59 | 26.82 | 2.15x |
| MiMo-V2.6-Pro | 256 | 58 | 57.92 | 29.16 | 1.99x |
| MiMo-V2.6-Pro | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| MiMo-V2.6-Pro | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| MiMo-V2.6-Pro | 1 | 61 | 7.56 | 5.86 | 1.29x |
| MiMo-V2.6-Pro | 2 | 61 | 14.05 | 8.17 | 1.72x |
| MiMo-V2.6-Pro | 4 | 61 | 24.47 | 11.58 | 2.11x |
| MiMo-V2.6-Pro | 8 | 61 | 38.19 | 15.56 | 2.45x |
| MiMo-V2.6-Pro | 16 | 61 | 51.07 | 19.96 | 2.56x |
| MiMo-V2.6-Pro | 32 | 61 | 58.28 | 24.23 | 2.41x |
| MiMo-V2.6-Pro | 64 | 61 | 60.44 | 27.63 | 2.19x |
| MiMo-V2.6-Pro | 256 | 61 | 60.89 | 30.10 | 2.02x |
| MiMo-V2.6-Pro | 1024 | 61 | 60.89 | 30.14 | 2.02x |
| MiMo-V2.6-Pro | 4096 | 61 | 60.89 | 30.14 | 2.02x |
| MiMo-V2.6-Pro | 1 | 63 | 7.57 | 5.90 | 1.28x |
| MiMo-V2.6-Pro | 2 | 63 | 14.10 | 8.24 | 1.71x |
| MiMo-V2.6-Pro | 4 | 63 | 24.64 | 11.70 | 2.11x |
| MiMo-V2.6-Pro | 8 | 63 | 38.69 | 15.76 | 2.45x |
| MiMo-V2.6-Pro | 16 | 63 | 52.13 | 20.27 | 2.57x |
| MiMo-V2.6-Pro | 32 | 63 | 59.90 | 24.65 | 2.43x |
| MiMo-V2.6-Pro | 64 | 63 | 62.33 | 28.16 | 2.21x |
| MiMo-V2.6-Pro | 256 | 63 | 62.86 | 30.71 | 2.05x |
| MiMo-V2.6-Pro | 1024 | 63 | 62.86 | 30.75 | 2.04x |
| MiMo-V2.6-Pro | 4096 | 63 | 62.86 | 30.75 | 2.04x |
| MiMo-V2.6-Pro | 1 | 70 | 7.61 | 6.03 | 1.26x |
| MiMo-V2.6-Pro | 2 | 70 | 14.26 | 8.47 | 1.68x |
| MiMo-V2.6-Pro | 4 | 70 | 25.20 | 12.11 | 2.08x |
| MiMo-V2.6-Pro | 8 | 70 | 40.27 | 16.42 | 2.45x |
| MiMo-V2.6-Pro | 16 | 70 | 55.58 | 21.29 | 2.61x |
| MiMo-V2.6-Pro | 32 | 70 | 65.34 | 26.07 | 2.51x |
| MiMo-V2.6-Pro | 64 | 70 | 68.83 | 29.93 | 2.30x |
| MiMo-V2.6-Pro | 256 | 70 | 69.71 | 32.76 | 2.13x |
| MiMo-V2.6-Pro | 1024 | 70 | 69.72 | 32.80 | 2.13x |
| MiMo-V2.6-Pro | 4096 | 70 | 69.72 | 32.80 | 2.13x |
| MiMo-V2.6-Pro | 1 | 72 | 7.62 | 6.07 | 1.26x |
| MiMo-V2.6-Pro | 2 | 72 | 14.30 | 8.53 | 1.68x |
| MiMo-V2.6-Pro | 4 | 72 | 25.34 | 12.22 | 2.07x |
| MiMo-V2.6-Pro | 8 | 72 | 40.68 | 16.60 | 2.45x |
| MiMo-V2.6-Pro | 16 | 72 | 56.50 | 21.56 | 2.62x |
| MiMo-V2.6-Pro | 32 | 72 | 66.82 | 26.45 | 2.53x |
| MiMo-V2.6-Pro | 64 | 72 | 70.65 | 30.41 | 2.32x |
| MiMo-V2.6-Pro | 256 | 72 | 71.66 | 33.32 | 2.15x |
| MiMo-V2.6-Pro | 1024 | 72 | 71.67 | 33.37 | 2.15x |
| MiMo-V2.6-Pro | 4096 | 72 | 71.67 | 33.37 | 2.15x |
| MiMo-V2.6-Pro | 1 | 75 | 7.64 | 6.12 | 1.25x |
| MiMo-V2.6-Pro | 2 | 75 | 14.36 | 8.62 | 1.67x |
| MiMo-V2.6-Pro | 4 | 75 | 25.54 | 12.37 | 2.06x |
| MiMo-V2.6-Pro | 8 | 75 | 41.27 | 16.85 | 2.45x |
| MiMo-V2.6-Pro | 16 | 75 | 57.83 | 21.96 | 2.63x |
| MiMo-V2.6-Pro | 32 | 75 | 69.01 | 27.01 | 2.55x |
| MiMo-V2.6-Pro | 64 | 75 | 73.35 | 31.12 | 2.36x |
| MiMo-V2.6-Pro | 256 | 75 | 74.56 | 34.15 | 2.18x |
| MiMo-V2.6-Pro | 1024 | 75 | 74.57 | 34.20 | 2.18x |
| MiMo-V2.6-Pro | 4096 | 75 | 74.57 | 34.20 | 2.18x |
| MiMo-V2.6-Pro | 1 | 78 | 7.65 | 6.16 | 1.24x |
| MiMo-V2.6-Pro | 2 | 78 | 14.41 | 8.70 | 1.66x |
| MiMo-V2.6-Pro | 4 | 78 | 25.72 | 12.52 | 2.06x |
| MiMo-V2.6-Pro | 8 | 78 | 41.81 | 17.10 | 2.45x |
| MiMo-V2.6-Pro | 16 | 78 | 59.09 | 22.35 | 2.64x |
| MiMo-V2.6-Pro | 32 | 78 | 71.13 | 27.56 | 2.58x |
| MiMo-V2.6-Pro | 64 | 78 | 76.01 | 31.82 | 2.39x |
| MiMo-V2.6-Pro | 256 | 78 | 77.44 | 34.96 | 2.22x |
| MiMo-V2.6-Pro | 1024 | 78 | 77.45 | 35.01 | 2.21x |
| MiMo-V2.6-Pro | 4096 | 78 | 77.45 | 35.01 | 2.21x |
| MiMo-V2.6-Pro | 1 | 79 | 7.65 | 6.18 | 1.24x |
| MiMo-V2.6-Pro | 2 | 79 | 14.43 | 8.73 | 1.65x |
| MiMo-V2.6-Pro | 4 | 79 | 25.78 | 12.56 | 2.05x |
| MiMo-V2.6-Pro | 8 | 79 | 41.99 | 17.18 | 2.44x |
| MiMo-V2.6-Pro | 16 | 79 | 59.50 | 22.48 | 2.65x |
| MiMo-V2.6-Pro | 32 | 79 | 71.82 | 27.74 | 2.59x |
| MiMo-V2.6-Pro | 64 | 79 | 76.88 | 32.04 | 2.40x |
| MiMo-V2.6-Pro | 256 | 79 | 78.39 | 35.22 | 2.23x |
| MiMo-V2.6-Pro | 1024 | 79 | 78.41 | 35.27 | 2.22x |
| MiMo-V2.6-Pro | 4096 | 79 | 78.41 | 35.27 | 2.22x |
| MiMo-V2.6-Pro | 1 | 87 | 7.69 | 6.29 | 1.22x |
| MiMo-V2.6-Pro | 2 | 87 | 14.55 | 8.95 | 1.63x |
| MiMo-V2.6-Pro | 4 | 87 | 26.21 | 12.92 | 2.03x |
| MiMo-V2.6-Pro | 8 | 87 | 43.28 | 17.78 | 2.43x |
| MiMo-V2.6-Pro | 16 | 87 | 62.56 | 23.44 | 2.67x |
| MiMo-V2.6-Pro | 32 | 87 | 77.13 | 29.11 | 2.65x |
| MiMo-V2.6-Pro | 64 | 87 | 83.74 | 33.79 | 2.48x |
| MiMo-V2.6-Pro | 256 | 87 | 85.95 | 37.27 | 2.31x |
| MiMo-V2.6-Pro | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| MiMo-V2.6-Pro | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| MiMo-V2.6-Pro | 1 | 93 | 7.71 | 6.37 | 1.21x |
| MiMo-V2.6-Pro | 2 | 93 | 14.63 | 9.10 | 1.61x |
| MiMo-V2.6-Pro | 4 | 93 | 26.49 | 13.16 | 2.01x |
| MiMo-V2.6-Pro | 8 | 93 | 44.13 | 18.20 | 2.42x |
| MiMo-V2.6-Pro | 16 | 93 | 64.63 | 24.11 | 2.68x |
| MiMo-V2.6-Pro | 32 | 93 | 80.85 | 30.08 | 2.69x |
| MiMo-V2.6-Pro | 64 | 93 | 88.69 | 35.03 | 2.53x |
| MiMo-V2.6-Pro | 256 | 93 | 91.51 | 38.72 | 2.36x |
| MiMo-V2.6-Pro | 1024 | 93 | 91.54 | 38.78 | 2.36x |
| MiMo-V2.6-Pro | 4096 | 93 | 91.54 | 38.78 | 2.36x |
| MiMo-V2.6-Pro | 1 | 100 | 7.73 | 6.45 | 1.20x |
| MiMo-V2.6-Pro | 2 | 100 | 14.71 | 9.27 | 1.59x |
| MiMo-V2.6-Pro | 4 | 100 | 26.78 | 13.41 | 2.00x |
| MiMo-V2.6-Pro | 8 | 100 | 45.02 | 18.66 | 2.41x |
| MiMo-V2.6-Pro | 16 | 100 | 66.84 | 24.85 | 2.69x |
| MiMo-V2.6-Pro | 32 | 100 | 84.92 | 31.16 | 2.73x |
| MiMo-V2.6-Pro | 64 | 100 | 94.25 | 36.40 | 2.59x |
| MiMo-V2.6-Pro | 256 | 100 | 97.85 | 40.35 | 2.43x |
| MiMo-V2.6-Pro | 1024 | 100 | 97.89 | 40.41 | 2.42x |
| MiMo-V2.6-Pro | 4096 | 100 | 97.89 | 40.41 | 2.42x |
| MiMo-V2.6-Pro | 1 | 116 | 7.76 | 6.60 | 1.18x |
| MiMo-V2.6-Pro | 2 | 116 | 14.86 | 9.62 | 1.55x |
| MiMo-V2.6-Pro | 4 | 116 | 27.32 | 13.91 | 1.96x |
| MiMo-V2.6-Pro | 8 | 116 | 46.71 | 19.63 | 2.38x |
| MiMo-V2.6-Pro | 16 | 116 | 71.17 | 26.40 | 2.70x |
| MiMo-V2.6-Pro | 32 | 116 | 93.27 | 33.39 | 2.79x |
| MiMo-V2.6-Pro | 64 | 116 | 106.10 | 39.31 | 2.70x |
| MiMo-V2.6-Pro | 256 | 116 | 111.76 | 43.79 | 2.55x |
| MiMo-V2.6-Pro | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| MiMo-V2.6-Pro | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| MiMo-V2.6-Pro | 1 | 139 | 7.80 | 6.78 | 1.15x |
| MiMo-V2.6-Pro | 2 | 139 | 15.02 | 10.06 | 1.49x |
| MiMo-V2.6-Pro | 4 | 139 | 27.89 | 14.50 | 1.92x |
| MiMo-V2.6-Pro | 8 | 139 | 48.56 | 20.86 | 2.33x |
| MiMo-V2.6-Pro | 16 | 139 | 76.10 | 28.36 | 2.68x |
| MiMo-V2.6-Pro | 32 | 139 | 103.29 | 36.22 | 2.85x |
| MiMo-V2.6-Pro | 64 | 139 | 121.14 | 43.00 | 2.82x |
| MiMo-V2.6-Pro | 256 | 139 | 130.20 | 48.21 | 2.70x |
| MiMo-V2.6-Pro | 1024 | 139 | 130.31 | 48.29 | 2.70x |
| MiMo-V2.6-Pro | 4096 | 139 | 130.31 | 48.29 | 2.70x |
| MiMo-V2.6-Pro | 1 | 150 | 7.82 | 6.85 | 1.14x |
| MiMo-V2.6-Pro | 2 | 150 | 15.07 | 10.25 | 1.47x |
| MiMo-V2.6-Pro | 4 | 150 | 28.10 | 14.74 | 1.91x |
| MiMo-V2.6-Pro | 8 | 150 | 49.27 | 21.39 | 2.30x |
| MiMo-V2.6-Pro | 16 | 150 | 78.04 | 29.19 | 2.67x |
| MiMo-V2.6-Pro | 32 | 150 | 107.41 | 37.45 | 2.87x |
| MiMo-V2.6-Pro | 64 | 150 | 127.59 | 44.61 | 2.86x |
| MiMo-V2.6-Pro | 256 | 150 | 138.37 | 50.14 | 2.76x |
| MiMo-V2.6-Pro | 1024 | 150 | 138.50 | 50.23 | 2.76x |
| MiMo-V2.6-Pro | 4096 | 150 | 138.50 | 50.23 | 2.76x |
| MiMo-V2.6-Pro | 1 | 173 | 7.84 | 6.97 | 1.12x |
| MiMo-V2.6-Pro | 2 | 173 | 15.17 | 10.61 | 1.43x |
| MiMo-V2.6-Pro | 4 | 173 | 28.47 | 15.19 | 1.87x |
| MiMo-V2.6-Pro | 8 | 173 | 50.49 | 22.41 | 2.25x |
| MiMo-V2.6-Pro | 16 | 173 | 81.47 | 30.74 | 2.65x |
| MiMo-V2.6-Pro | 32 | 173 | 114.90 | 39.77 | 2.89x |
| MiMo-V2.6-Pro | 64 | 173 | 139.69 | 47.69 | 2.93x |
| MiMo-V2.6-Pro | 256 | 173 | 154.13 | 53.87 | 2.86x |
| MiMo-V2.6-Pro | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| MiMo-V2.6-Pro | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| MiMo-V2.6-Pro | 1 | 185 | 7.85 | 7.02 | 1.12x |
| MiMo-V2.6-Pro | 2 | 185 | 15.21 | 10.78 | 1.41x |
| MiMo-V2.6-Pro | 4 | 185 | 28.62 | 15.41 | 1.86x |
| MiMo-V2.6-Pro | 8 | 185 | 51.01 | 22.88 | 2.23x |
| MiMo-V2.6-Pro | 16 | 185 | 82.98 | 31.46 | 2.64x |
| MiMo-V2.6-Pro | 32 | 185 | 118.31 | 40.86 | 2.90x |
| MiMo-V2.6-Pro | 64 | 185 | 145.35 | 49.16 | 2.96x |
| MiMo-V2.6-Pro | 256 | 185 | 161.70 | 55.66 | 2.91x |
| MiMo-V2.6-Pro | 1024 | 185 | 161.92 | 55.76 | 2.90x |
| MiMo-V2.6-Pro | 4096 | 185 | 161.92 | 55.76 | 2.90x |
| MiMo-V2.6-Pro | 1 | 200 | 7.86 | 7.08 | 1.11x |
| MiMo-V2.6-Pro | 2 | 200 | 15.26 | 10.97 | 1.39x |
| MiMo-V2.6-Pro | 4 | 200 | 28.80 | 15.66 | 1.84x |
| MiMo-V2.6-Pro | 8 | 200 | 51.59 | 23.43 | 2.20x |
| MiMo-V2.6-Pro | 16 | 200 | 84.66 | 32.28 | 2.62x |
| MiMo-V2.6-Pro | 32 | 200 | 122.15 | 42.14 | 2.90x |
| MiMo-V2.6-Pro | 64 | 200 | 151.88 | 50.89 | 2.98x |
| MiMo-V2.6-Pro | 256 | 200 | 170.56 | 57.78 | 2.95x |
| MiMo-V2.6-Pro | 1024 | 200 | 170.82 | 57.89 | 2.95x |
| MiMo-V2.6-Pro | 4096 | 200 | 170.82 | 57.89 | 2.95x |
| MiMo-V2.6-Pro | 1 | 231 | 7.88 | 7.19 | 1.10x |
| MiMo-V2.6-Pro | 2 | 231 | 15.33 | 11.34 | 1.35x |
| MiMo-V2.6-Pro | 4 | 231 | 29.08 | 16.14 | 1.80x |
| MiMo-V2.6-Pro | 8 | 231 | 52.57 | 24.42 | 2.15x |
| MiMo-V2.6-Pro | 16 | 231 | 87.55 | 33.78 | 2.59x |
| MiMo-V2.6-Pro | 32 | 231 | 128.92 | 44.54 | 2.89x |
| MiMo-V2.6-Pro | 64 | 231 | 163.68 | 54.17 | 3.02x |
| MiMo-V2.6-Pro | 256 | 231 | 187.01 | 61.81 | 3.03x |
| MiMo-V2.6-Pro | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| MiMo-V2.6-Pro | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| MiMo-V2.6-Pro | 1 | 347 | 7.92 | 7.43 | 1.07x |
| MiMo-V2.6-Pro | 2 | 347 | 15.50 | 12.32 | 1.26x |
| MiMo-V2.6-Pro | 4 | 347 | 29.71 | 17.67 | 1.68x |
| MiMo-V2.6-Pro | 8 | 347 | 54.77 | 26.85 | 2.04x |
| MiMo-V2.6-Pro | 16 | 347 | 94.25 | 38.30 | 2.46x |
| MiMo-V2.6-Pro | 32 | 347 | 145.44 | 51.79 | 2.81x |
| MiMo-V2.6-Pro | 64 | 347 | 194.20 | 63.82 | 3.04x |
| MiMo-V2.6-Pro | 256 | 347 | 231.86 | 73.74 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| MiMo-V2.6-Pro | 4096 | 347 | 232.44 | 73.90 | 3.15x |

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
| gpu | MiMo-V2.6-Pro | 1 | 15.80 | 3.6% |
| rom | MiMo-V2.6-Pro | 1 | 15.80 | 12.2% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| MiMo-V2.6-Pro | sram | interleaved | 128 B | 1.00x |
| MiMo-V2.6-Pro | hbm | interleaved | 32 B | 1.00x |

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
| MiMo-V2.6-Pro | 1 | 47 | 31.51% | 137.45 | 9.28 |
| MiMo-V2.6-Pro | 2 | 47 | 31.51% | 137.45 | 9.28 |
| MiMo-V2.6-Pro | 4 | 1 | 2.18% | 11.52 | 9.28 |
| MiMo-V2.6-Pro | 8 | 1 | 2.18% | 11.52 | 9.28 |
| MiMo-V2.6-Pro | 16 | 1 | 2.18% | 11.52 | 9.28 |
| MiMo-V2.6-Pro | 32 | 1 | 2.18% | 11.52 | 9.28 |

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
| MiMo-V2.6-Pro | 1 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 393.6 | 40,930.2 |
| MiMo-V2.6-Pro | 2 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 393.6 | 40,930.2 |
| MiMo-V2.6-Pro | 4 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 393.6 | 40,930.2 |
| MiMo-V2.6-Pro | 8 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 393.6 | 40,930.2 |
| MiMo-V2.6-Pro | 16 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 393.6 | 40,930.2 |
| MiMo-V2.6-Pro | 32 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 393.6 | 40,930.2 |
| MiMo-V2.6-Pro | 64 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 393.6 | 40,930.2 |
| MiMo-V2.6-Pro | 256 | 5.05% | 55.1 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 160.6 | 41,103.3 |
| MiMo-V2.6-Pro | 1024 | 18.72% | 127.8 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 40.2 | 41,192.7 |
| MiMo-V2.6-Pro | 4096 | 56.36% | 327.7 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 10.1 | 41,215.1 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | kv_read | 2 |
| gpu | link_latency | 813 |
| gpu | thermal | 280 |
| gpu | weight_read | 725 |
| rom | compute | 681 |
| rom | infeasible | 2092 |
| rom | kv_read | 209 |
| rom | link_latency | 1224 |
| rom | thermal | 4 |
| rom | weight_read | 730 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2092 |

## Mechanical consistency audit

**FAIL** over 145,283 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x95', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x99', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x104', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x114', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x182', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x273', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x364', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x95', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x99', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x104', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x114', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x182', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x273', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x364', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x95', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x99', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x104', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x114', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x182', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x273', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x364', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x95', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x99', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x104', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x114', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x182', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x273', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x364', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'MiMo-V2.6-Pro', 1)

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

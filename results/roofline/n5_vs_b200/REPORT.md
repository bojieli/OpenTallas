# Area-constrained roofline: n5_vs_b200

> Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 1,611x (ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream, 2,666 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 4 devices. On the GPU side the correction reaches 64x (b200_sxm-x1358-pipeline, 1,358 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 50 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 5 x 815 mm2 (4,075 mm2, array, KV in SRAM) at 16,619 tok/s per user and 4,078 tok/s per 1,000 mm2, holding 1 session, against 3 copies of one unified HBM die at the same silicon: 17.0x per user. DeepSeek-V4-Flash-0731 takes 35 x 815 mm2 (28,525 mm2, array, KV in SRAM) at 15,623 tok/s per user and 548 tok/s per 1,000 mm2, holding 1 session, against 18 copies of one unified HBM die at the same silicon: 5.0x per user. DeepSeek-V4-Pro-0813 takes 166 x 815 mm2 (135,290 mm2, array, KV in SRAM) at 4,787 tok/s per user and 35 tok/s per 1,000 mm2, holding 1 session, against 85 copies of one unified HBM die at the same silicon: 2.3x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 4,890 mm2 of ROM silicon at 18,588 tok/s per user against 4,800 mm2 of b200_sxm-x3-tensor at 979 tok/s: **19.0x**, ROM binding on `compute` and the GPU on `weight_read`. It holds 1 resident session against the GPU cluster's 388. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 16.66x to it.** At 231,125 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 147.08 tok/s and the same silicon running hybrid delivers 2,450 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.03x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 2.75x (DeepSeek-V4-Flash-0731, ROM binding on `thermal`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 5,027 to 302,050 tok/s, and its rate with every slot occupied from 281,513 to 302,050. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 56 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,393 us over NVLink, capping per-user decode at 718 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 396.7 us and cap it at 2,521 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 1.3x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 30 operating points and an array 28; on tokens per second per square millimetre the same points go 30 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 500 of 9413 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 72.9x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 23.11x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 48 of 60 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 1,501 of 9,413 feasible points (15.9%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x170` at batch 4096 on 138,550 mm2, throttled 1.60x from 139 to 87 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 96% kv read against 0.0% weight read. The ROM sweep is not what melts it.


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

### Qwen3-8B at 8,192 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill`** -- 5 x 815 mm2 reticle dies, 4,075 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `rom`.

- **16,619.5 tok/s per user** (0.06 ms/token), binding on `weight_read`
- **4,078.4 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 16,619 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 549 W at 0.135 W/mm2, 33.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 3 copies of one unified HBM die -- `b200_sxm-x3-tensor`, 4,800 mm2, area ratio 0.8490 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 4,075 | 4,800 | 0.8490 |
| user tok/s | 16,619.5 | 978.7 | 16.98x |
| aggregate tok/s | 16,619 | 979 | 14.69x |
| resident sessions | 1 | 388 | -- |
| J/token | 0.0330 | 2.7972 | 84.7x |

**The areas do not match exactly, and the mismatch is stated rather than rounded away.** A GPU cluster is quantised in whole dies and a ROM design is not, so at 4,075 mm2 the closest whole number of 1,600 mm2 dies is 3, i.e. 4,800 mm2. The ROM side is therefore compared against 18% MORE silicon than it has, which makes the ratio CONSERVATIVE for the ROM side.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 388 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x58-nvl72-tensor` at 92,800 mm2 and 4,443.7 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-tensor-x15-romfill` | 12,225 | 27,653.4 | 2,262.0 | 1 | 13.73x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 28,190.4 | 2,161.8 | 1 | 14.00x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 16,619.5 | 4,078.4 | 1 | 16.98x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 16,619.5 | 4,078.4 | 1 | 16.98x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 16,619.5 | 4,078.4 | -- | 4,078.4 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x6-romfill` | 4,890 | 18,587.5 | 3,801.1 | 2,414.7 | 4,078.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 20,251.4 | 3,549.8 | 2,228.2 | 4,078.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 21,676.7 | 3,324.6 | 2,068.4 | 4,078.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x10-romfill` | 8,150 | 23,896.9 | 2,932.1 | 1,785.9 | 4,078.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x12-romfill` | 9,780 | 25,680.7 | 2,625.8 | 1,588.3 | 4,078.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x15-romfill` | 12,225 | 27,653.4 | 2,262.0 | 1,353.9 | 4,078.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 28,190.4 | 2,161.8 | 1,290.7 | 4,078.4 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` **<-- recommended** | 4,075 | 5 | 16,619.5 | 16,619 | 4,078.4 | 1 | `weight_read` | 549 | 33.0 | `b200_sxm-x3-tensor` | 16.98x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x6-romfill` | 4,890 | 6 | 18,587.5 | 18,588 | 3,801.1 | 1 | `compute` | 644 | 34.7 | `b200_sxm-x3-tensor` | 18.99x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 7 | 20,251.4 | 20,251 | 3,549.8 | 1 | `compute` | 736 | 36.3 | `b200_sxm-x4-tensor` | 16.44x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 8 | 21,676.7 | 21,677 | 3,324.6 | 1 | `compute` | 824 | 38.0 | `b200_sxm-x4-tensor` | 17.59x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x10-romfill` | 8,150 | 10 | 23,896.9 | 23,897 | 2,932.1 | 1 | `link_latency` | 992 | 41.5 | `b200_sxm-x5-tensor` | 16.39x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x12-romfill` | 9,780 | 12 | 25,680.7 | 25,681 | 2,625.8 | 1 | `link_latency` | 1,155 | 45.0 | `b200_sxm-x6-tensor` | 15.45x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x15-romfill` | 12,225 | 15 | 27,653.4 | 27,653 | 2,262.0 | 1 | `link_latency` | 1,390 | 50.2 | `b200_sxm-x8-tensor` | 13.73x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 16 | 28,190.4 | 28,190 | 2,161.8 | 1 | `link_latency` | 1,466 | 52.0 | `b200_sxm-x8-tensor` | 14.00x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 275 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 16,619.5 | 4,078.4 | 1 |
| array | 275 | fastest | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 28,190.4 | 2,161.8 | 1 |
| array | 275 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 16,619.5 | 4,078.4 | 1 |
| wafer | 58 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 58 | fastest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 58 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 28,190.4 | 28,190 | 1 | 1,466 | 52.0 | `link_latency` | `b200_sxm-x8-tensor` | 2,013.6 | 1,059 | 3,115.3 | 1.019 | 14.00x | 59.9x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 6,464 | 1 | 4,016 | 621.2 | `link_latency` | `b200_sxm-x29-nvl72-tensor` | 3,724.5 | 3,875 | 4,451.7 | 0.996 | 1.74x | 7.2x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-tensor-x57-romfill` | 46,455 | 16,061.3 | 16,061 | 4,777 | 7,168 | 446.3 | `link_latency` | `b200_sxm-x29-nvl72-tensor` | 3,724.5 | 3,875 | 4,451.7 | 1.001 | 4.31x | 10.0x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | -- | 1 | -- | 621.2 | -- | -- | -- | -- | -- | 1.005 | 0.40x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill` | 50,530 | 14,725.8 | 29,452 | 5,196 | 9,365 | 318.0 | `link_latency` | `b200_sxm-x32-nvl72-tensor` | 3,730.3 | 4,277 | 2,430.6 | 0.987 | 3.95x | 7.6x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 5,536.7 | 33,220 | 4,325 | 29,140 | 2,358.1 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 4,353.8 | 23,187 | 8,685.5 | 1.002 | 1.27x | 3.7x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,373.0 | 796,702 | 28,498 | 138,550 | 1,719.1 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 4,353.8 | 23,187 | 8,685.5 | 1.001 | 2.15x | 5.1x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 5,536.7 | -- | 4,325 | -- | 2,358.1 | -- | -- | -- | -- | -- | 0.999 | 0.59x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill` | 50,530 | 12,494.2 | 49,977 | 5,196 | 12,064 | 241.4 | `link_latency` | `b200_sxm-x32-nvl72-tensor` | 3,526.8 | 4,277 | 1,324.6 | 0.987 | 3.54x | 5.5x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 5,536.7 | 33,220 | 4,325 | 29,140 | 1,247.4 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 4,319.3 | 23,187 | 4,834.3 | 1.002 | 1.28x | 3.9x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,373.0 | 796,702 | 28,498 | 138,550 | 927.9 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 4,319.3 | 23,187 | 4,834.3 | 1.001 | 2.17x | 5.2x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 5,536.7 | -- | 4,325 | -- | 1,247.4 | -- | -- | -- | -- | -- | 0.999 | 0.59x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-tensor-x62` | 50,530 | 9,588.1 | 76,705 | 5,196 | 18,144 | 236.5 | `link_latency` | `b200_sxm-x32-nvl72-tensor` | 3,180.0 | 4,277 | 771.7 | 0.987 | 3.02x | 3.3x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,530.5 | 44,244 | 5,766 | 38,846 | 878.0 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 4,211.0 | 30,965 | 3,330.5 | 1.001 | 1.31x | 3.8x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,373.0 | 796,702 | 28,498 | 138,550 | 334.5 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 3,944.5 | 23,187 | 1,390.9 | 1.001 | 2.38x | 4.2x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,187.1 | 82,993 | 8,650 | 60,444 | 728.3 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 4,196.5 | 46,522 | 2,440.3 | 0.999 | 1.24x | 3.4x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,373.0 | 796,702 | 28,498 | 138,550 | 235.6 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 3,535.5 | 23,187 | 817.0 | 1.001 | 2.65x | 3.5x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,183.1 | 133,861 | 8,650 | 67,101 | 501.3 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,918.6 | 46,522 | 1,350.3 | 0.999 | 1.07x | 2.7x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,373.0 | 796,702 | 28,498 | 138,550 | 186.1 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 2,928.2 | 23,187 | 530.1 | 1.001 | 3.20x | 2.8x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,015.8 | 193,009 | 8,650 | 74,842 | 387.8 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 3,460.3 | 46,522 | 805.4 | 0.999 | 0.87x | 2.1x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,185.2 | 815,402 | 28,498 | 138,550 | 169.9 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 1,442.0 | 23,187 | 314.9 | 1.001 | 2.21x | 1.9x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,127.6 | 288,677 | 8,650 | 119,820 | 415.1 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 2,033.5 | 46,522 | 396.6 | 0.999 | 0.55x | 1.0x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 803.3 | 822,600 | 28,498 | 138,550 | 168.4 | `thermal` | `b200_sxm-x173-hybrid` | 536.8 | 23,187 | 276.5 | 1.001 | 1.50x | 1.5x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 336.6 | 344,659 | 8,650 | 95,762 | 277.8 | `kv_read` | `b200_sxm-x347-hybrid` | 787.1 | 46,522 | 351.2 | 0.999 | 0.43x | 1.1x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 277,100 | 201.3 | 824,720 | 28,498 | 138,550 | 168.0 | `thermal` | `b200_sxm-x173-hybrid` | 169.7 | 23,187 | 227.8 | 1.001 | 1.19x | 1.4x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 84.4 | 345,636 | 8,650 | 95,085 | 275.1 | `kv_read` | `b200_sxm-x347-hybrid` | 290.6 | 46,522 | 251.2 | 0.999 | 0.29x | 0.9x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | array | SRAM | 1 |
| 2-4 | `ROM-N5-native-HBMKV-array-hw-tensor-x49-romfill` | 39,935 | array | HBM | 4,107 |
| 8-32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 41,565 | array | HBM | 4,274 |
| 64 | `ROM-N5-native-HBMKV-array-hw-tensor-x51-romfill` | 41,565 | array | HBM | 4,274 |
| 256 | `ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill` | 50,530 | array | HBM | 5,196 |
| 1024-4096 | `ROM-N5-native-HBMKV-array-hw-tensor-x74-romfill` | 60,310 | array | HBM | 6,202 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Flash-0731 at 200,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x35`** -- 35 x 815 mm2 reticle dies, 28,525 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **15,623.1 tok/s per user** (0.06 ms/token), binding on `link_latency`
- **547.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 15,623 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 1,957 W at 0.069 W/mm2, 125.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 18 copies of one unified HBM die -- `b200_sxm-x18-nvl72-tensor`, 28,800 mm2, area ratio 0.9905 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 28,525 | 28,800 | 0.9905 |
| user tok/s | 15,623.1 | 3,125.9 | 5.00x |
| aggregate tok/s | 15,623 | 3,126 | 1.62x |
| resident sessions | 1 | 1,989 | -- |
| J/token | 0.1253 | 3.2331 | 25.8x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,989 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x58-nvl72-tensor` at 92,800 mm2 and 3,971.5 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 17,768.6 | 389.3 | 1 | 5.02x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 48,085 | 18,118.9 | 376.8 | 1 | 5.08x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | 26,080 | 14,171.0 | 543.4 | 1 | 4.71x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | 15,623.1 | 547.7 | 1 | 5.00x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | 15,623.1 | 547.7 | -- | 547.7 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 17,768.6 | 389.3 | 125.4 | 547.7 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 48,085 | 18,118.9 | 376.8 | 127.6 | 547.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x35` **<-- recommended** | 28,525 | 35 | 15,623.1 | 15,623 | 547.7 | 1 | `link_latency` | 1,957 | 125.3 | `b200_sxm-x18-nvl72-tensor` | 5.00x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 56 | 17,768.6 | 17,769 | 389.3 | 1 | `compute` | 4,452 | 250.6 | `b200_sxm-x29-nvl72-tensor` | 5.02x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 48,085 | 59 | 18,118.9 | 18,119 | 376.8 | 1 | `compute` | 4,809 | 265.4 | `b200_sxm-x30-nvl72-tensor` | 5.08x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 312 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | 15,623.1 | 547.7 | 1 |
| array | 312 | fastest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 48,085 | 18,118.9 | 376.8 | 1 |
| array | 312 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | 26,080 | 14,171.0 | 543.4 | 1 |
| wafer | 58 | densest | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 6,168.1 | 133.4 | 1 |
| wafer | 58 | fastest | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 6,168.1 | 133.4 | 1 |
| wafer | 58 | smallest | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 6,168.1 | 133.4 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 48,085 | 18,118.9 | 18,119 | 1 | 4,809 | 265.4 | `compute` | `b200_sxm-x30-nvl72-tensor` | 3,566.3 | 3,396 | 4,163.1 | 1.002 | 5.08x | 15.7x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 6,168.1 | 6,168 | 1 | 4,463 | 723.5 | `compute` | `b200_sxm-x29-nvl72-tensor` | 3,540.5 | 3,279 | 4,085.6 | 0.996 | 1.74x | 5.6x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | 48,085 | 18,118.9 | 18,119 | 1 | 4,809 | 265.4 | `compute` | `b200_sxm-x30-nvl72-tensor` | 3,566.3 | 3,396 | 4,163.1 | 1.002 | 5.08x | 15.7x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 6,168.1 | -- | 1 | -- | 723.5 | -- | -- | -- | -- | -- | 1.040 | 0.34x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 51,345 | 17,197.9 | 275,166 | 4,616 | 16,789 | 216.0 | `compute` | `b200_sxm-x32-nvl72-tensor` | 3,369.9 | 3,631 | 2,466.6 | 1.003 | 5.10x | 11.4x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 323,575 | 5,328.6 | 37,300 | 4,411 | 30,149 | 2,731.8 | `link_latency` | `b200_sxm-x202-nvl72-hybrid` | 3,969.3 | 23,564 | 10,132.2 | 1.001 | 1.34x | 3.7x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 51,345 | 17,197.9 | 275,166 | 4,616 | 16,789 | 127.4 | `compute` | `b200_sxm-x32-nvl72-tensor` | 2,978.7 | 3,631 | 1,531.4 | 1.003 | 5.77x | 12.0x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x7-romfill` | 323,575 | 5,328.6 | 37,300 | 4,411 | 30,149 | 1,385.3 | `link_latency` | `b200_sxm-x202-nvl72-hybrid` | 3,911.6 | 23,564 | 5,534.0 | 1.001 | 1.36x | 4.0x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 51,345 | 17,197.9 | 275,166 | 4,616 | 16,789 | 83.2 | `compute` | `b200_sxm-x32-nvl72-tensor` | 2,442.8 | 3,631 | 1,046.2 | 1.003 | 7.04x | 12.6x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,325.7 | 42,606 | 5,041 | 34,455 | 808.7 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 3,687.7 | 26,964 | 3,546.7 | 1.001 | 1.44x | 4.4x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 51,345 | 17,197.9 | 275,166 | 4,616 | 16,789 | 61.0 | `compute` | `b200_sxm-x32-nvl72-tensor` | 1,847.5 | 3,631 | 771.8 | 1.003 | 9.31x | 12.6x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,229.6 | 83,674 | 7,562 | 52,400 | 626.2 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,573.1 | 40,565 | 2,771.6 | 0.999 | 1.46x | 4.4x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 136,920 | 13,849.4 | 581,675 | 12,311 | 37,267 | 71.9 | `compute` | `b200_sxm-x86-nvl72-hybrid` | 2,112.4 | 9,962 | 838.3 | 0.995 | 6.56x | 11.7x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,916.6 | 157,332 | 7,562 | 55,074 | 350.1 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,186.7 | 40,565 | 1,696.6 | 0.999 | 1.54x | 4.8x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 13,829.4 | 1,175,496 | 24,915 | 75,356 | 72.4 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 2,107.3 | 20,163 | 811.8 | 1.001 | 6.56x | 11.2x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,390.9 | 281,020 | 7,562 | 59,557 | 211.9 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 2,653.0 | 40,565 | 1,132.5 | 0.999 | 1.66x | 5.3x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 5,526.7 | 1,414,839 | 24,915 | 82,348 | 58.2 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 1,131.8 | 20,163 | 412.2 | 1.001 | 4.88x | 6.8x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 2,675.0 | 684,789 | 7,562 | 104,538 | 152.7 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 1,509.3 | 40,565 | 579.2 | 0.999 | 1.77x | 3.8x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,521.0 | 1,557,471 | 24,915 | 87,659 | 56.3 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 546.5 | 20,163 | 192.1 | 1.001 | 2.78x | 3.0x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,257.0 | 1,287,185 | 7,562 | 98,186 | 76.3 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 756.4 | 40,565 | 272.0 | 0.999 | 1.66x | 2.8x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 464.4 | 1,902,184 | 24,915 | 111,351 | 58.5 | `weight_read` | `b200_sxm-x173-expert` | 217.4 | 20,051 | 108.2 | 1.001 | 2.14x | 1.8x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 319.6 | 1,308,957 | 7,562 | 97,371 | 74.4 | `kv_read` | `b200_sxm-x347-expert` | 371.8 | 40,329 | 119.9 | 0.999 | 0.86x | 1.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | array | SRAM | 1 |
| 2-8 | `ROM-N5-native-HBMKV-array-hw-hybrid-x56` | 45,640 | array | HBM | 4,103 |
| 16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x63` | 51,345 | array | HBM | 4,616 |
| 32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 57,050 | array | HBM | 5,129 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x84` | 68,460 | array | HBM | 6,155 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 8,280 |
| 1024-4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x112` | 91,280 | array | HBM | 8,207 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Pro-0813 at 1,000,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill`** -- 166 x 815 mm2 reticle dies, 135,290 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `rom`.

- **4,787.0 tok/s per user** (0.21 ms/token), binding on `link_latency`
- **35.4 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,787 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 8,445 W at 0.062 W/mm2, 1,764.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 85 copies of one unified HBM die -- `b200_sxm-x85-nvl72-hybrid`, 136,000 mm2, area ratio 0.9948 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 135,290 | 136,000 | 0.9948 |
| user tok/s | 4,787.0 | 2,125.3 | 2.25x |
| aggregate tok/s | 4,787 | 4,251 | 0.38x |
| resident sessions | 1 | 1,306 | -- |
| J/token | 1.7640 | 18.4321 | 10.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,306 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x71-nvl72-tensor` at 113,600 mm2 and 2,456.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-tensor-x167` | 136,105 | 4,813.6 | 35.4 | 1 | 2.26x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | 149,960 | 5,063.9 | 33.8 | 1 | 2.31x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill` | 135,290 | 4,787.0 | 35.4 | 1 | 2.25x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill` | 135,290 | 4,787.0 | 35.4 | 1 | 2.25x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill` | 135,290 | 4,787.0 | 35.4 | -- | 35.4 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x167` | 136,105 | 4,813.6 | 35.4 | 32.6 | 35.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x170` | 138,550 | 4,881.3 | 35.2 | 28.9 | 35.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x182` | 148,330 | 5,046.0 | 34.0 | 19.9 | 35.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | 149,960 | 5,063.9 | 33.8 | 18.9 | 35.4 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill` **<-- recommended** | 135,290 | 166 | 4,787.0 | 4,787 | 35.4 | 1 | `link_latency` | 8,445 | 1,764.0 | `b200_sxm-x85-nvl72-hybrid` | 2.25x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x167` | 136,105 | 167 | 4,813.6 | 4,814 | 35.4 | 1 | `link_latency` | 8,495 | 1,764.8 | `b200_sxm-x85-nvl72-hybrid` | 2.26x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x170` | 138,550 | 170 | 4,881.3 | 4,881 | 35.2 | 1 | `link_latency` | 8,647 | 1,771.5 | `b200_sxm-x87-nvl72-hybrid` | 2.28x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x182` | 148,330 | 182 | 5,046.0 | 5,046 | 34.0 | 1 | `link_latency` | 9,386 | 1,860.2 | `b200_sxm-x93-nvl72-hybrid` | 2.31x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | 149,960 | 184 | 5,063.9 | 5,064 | 33.8 | 1 | `link_latency` | 9,623 | 1,900.4 | `b200_sxm-x94-nvl72-hybrid` | 2.31x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 144 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill` | 135,290 | 4,787.0 | 35.4 | 1 |
| array | 144 | fastest | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | 149,960 | 5,063.9 | 33.8 | 1 |
| array | 144 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill` | 135,290 | 4,787.0 | 35.4 | 1 |
| wafer | 42 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | 138,675 | 3,336.7 | 24.1 | 1 |
| wafer | 42 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 3,736.6 | 13.5 | 1 |
| wafer | 42 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | 138,675 | 3,336.7 | 24.1 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | 149,960 | 5,063.9 | 5,064 | 1 | 9,623 | 1,900.4 | `link_latency` | `b200_sxm-x94-nvl72-hybrid` | 2,193.2 | 1,454 | 19,436.6 | 0.997 | 2.31x | 10.2x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 3,736.6 | 3,737 | 1 | 28,055 | 7,508.2 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 2,310.3 | 2,752 | 30,658.4 | 1.002 | 1.62x | 4.1x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x343` | 279,545 | 4,260.4 | 4,260 | 1 | 28,389 | 6,663.4 | `compute` | `b200_sxm-x175-nvl72-hybrid` | 2,317.1 | 2,785 | 30,883.3 | 0.998 | 1.84x | 4.6x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 3,736.6 | -- | 1 | -- | 7,508.2 | -- | -- | -- | -- | -- | 1.008 | 0.88x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 4,226.3 | 422,634 | 4,098 | 148,974 | 5,081.5 | `compute` | `b200_sxm-x203-nvl72-hybrid` | 2,402.2 | 3,246 | 19,223.7 | 1.001 | 1.76x | 3.8x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 3,119.7 | 146,624 | 4,152 | 230,228 | 31,139.9 | `link_latency` | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 22,230 | 111,081.5 | 1.000 | 1.40x | 3.6x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 4,226.3 | 422,634 | 4,098 | 148,974 | 2,668.7 | `compute` | `b200_sxm-x203-nvl72-hybrid` | 2,327.0 | 3,246 | 11,350.9 | 1.001 | 1.82x | 4.3x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 3,119.7 | 146,624 | 4,152 | 230,228 | 15,697.9 | `link_latency` | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 22,230 | 57,749.0 | 1.000 | 1.40x | 3.7x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 4,226.3 | 422,634 | 4,098 | 148,974 | 1,462.3 | `compute` | `b200_sxm-x203-nvl72-hybrid` | 2,070.3 | 3,246 | 6,932.2 | 1.001 | 2.04x | 4.7x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 3,119.7 | 146,624 | 4,152 | 230,228 | 7,977.0 | `link_latency` | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 22,230 | 31,082.8 | 1.000 | 1.40x | 3.9x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 4,226.3 | 422,634 | 4,098 | 148,974 | 859.2 | `compute` | `b200_sxm-x203-nvl72-hybrid` | 1,702.9 | 3,246 | 4,691.9 | 1.001 | 2.48x | 5.5x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 3,119.7 | 146,624 | 4,152 | 230,228 | 4,116.5 | `link_latency` | `b200_sxm-x1358-nvl72-hybrid` | 2,230.8 | 22,230 | 17,749.6 | 1.000 | 1.40x | 4.3x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 4,226.3 | 422,634 | 4,098 | 148,974 | 557.6 | `compute` | `b200_sxm-x203-nvl72-hybrid` | 1,271.2 | 3,246 | 3,512.9 | 1.001 | 3.32x | 6.3x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 3,119.7 | 146,624 | 4,152 | 230,228 | 2,186.2 | `link_latency` | `b200_sxm-x1358-nvl72-hybrid` | 2,093.3 | 22,230 | 10,368.5 | 1.000 | 1.49x | 4.7x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 4,226.3 | 422,634 | 4,098 | 148,974 | 406.8 | `compute` | `b200_sxm-x203-nvl72-hybrid` | 867.4 | 3,246 | 2,816.5 | 1.001 | 4.87x | 6.9x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 2,911.1 | 186,311 | 4,152 | 239,973 | 1,288.0 | `link_latency` | `b200_sxm-x1358-nvl72-hybrid` | 1,820.3 | 22,230 | 6,494.4 | 1.000 | 1.60x | 5.0x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 1,769.6 | 453,024 | 4,098 | 154,436 | 340.9 | `compute` | `b200_sxm-x203-nvl72-hybrid` | 366.2 | 3,246 | 1,787.4 | 1.001 | 4.83x | 5.0x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 2,172,575 | 1,658.7 | 424,630 | 4,152 | 414,489 | 976.1 | `kv_read` | `b200_sxm-x1358-nvl72-hybrid` | 1,046.7 | 22,230 | 3,458.6 | 1.000 | 1.58x | 3.5x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 325,185 | 462.6 | 473,748 | 4,098 | 159,631 | 337.0 | `compute` | `b200_sxm-x203-nvl72-hybrid` | 163.4 | 3,246 | 932.4 | 1.001 | 2.83x | 2.3x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 2,172,575 | 609.6 | 624,261 | 4,152 | 463,214 | 742.0 | `kv_read` | `b200_sxm-x1358-nvl72-hybrid` | 441.5 | 22,230 | 2,269.3 | 1.000 | 1.38x | 2.0x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 325,185 | 116.5 | 476,985 | 4,098 | 159,175 | 333.7 | `compute` | `b200_sxm-x203-pipeline` | 0.0 | 3,246 | 2,390.3 | 1.001 | --x | --x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 2,172,575 | 180.2 | 738,201 | 4,152 | 495,542 | 671.3 | `kv_read` | `b200_sxm-x1358-expert` | 254.4 | 21,773 | 725.6 | 1.000 | 0.71x | 1.1x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill` | 135,290 | array | SRAM | 1 |
| 2-256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | array | HBM | 4,098 |
| 1024-4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 325,185 | array | HBM | 4,098 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 56, 57, 70, 84, 112, 113, 168, 170, 224, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 56, 57, 62, 63, 70, 84, 112, 113, 168, 170, 224, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 32, 35, 42, 44, 46, 47, 56, 57, 84, 112, 113, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 32, 35, 42, 46, 56, 57, 58, 59, 84, 112, 113, 170, 227, 340 |
| DeepSeek-V4-Pro-0813 | HBM | rom | 399 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 399 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 166, 170, 182, 184, 221, 227, 237, 248, 294, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 167, 170, 182, 184, 221, 227, 262, 294, 340, 341, 342, 343 |
| Qwen3-8B | HBM | rom | 49, 50, 51, 57, 62, 74, 98, 113, 147, 170, 196, 227, 340 |
| Qwen3-8B | HBM | sram | 49, 57, 62, 74, 98, 113, 147, 170, 196, 227, 340 |
| Qwen3-8B | SRAM | rom | 5, 6, 7, 8, 10, 12, 15, 16, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 5, 6, 8, 12, 16, 57, 113, 170, 227, 340 |

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

- **1,501 of 9,413 feasible points (15.9%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 697, rom 804.
- By area class: large array (5,000-40,000 mm2) 253, small array (1,600-5,000 mm2) 30, wafer (>=40,000 mm2) 1218.
- By KV store: hbm 1501.
- By batch: B=1 130, B=2 130, B=4 130, B=8 130, B=16 130, B=32 134, B=64 150, B=256 186, B=1024 201, B=4096 180.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 46% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 571 | 123 | 77.8% | 100.0% | 0.625 | 45% |
| gpu | small array (1,600-5,000 mm2) | 52 | 30 | 100.0% | 100.0% | 0.625 | 35% |
| gpu | wafer (>=40,000 mm2) | 3,231 | 544 | 55.6% | 100.0% | 0.625 | 63% |
| rom | large array (5,000-40,000 mm2) | 531 | 130 | 35.1% | 100.0% | 0.500 | 56% |
| rom | small array (1,600-5,000 mm2) | 46 | 0 | 24.3% | 47.2% | 0.236 | 64% |
| rom | wafer (>=40,000 mm2) | 4,982 | 674 | 35.6% | 100.0% | 0.500 | 67% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x170` | Qwen3-8B | 4096 | 138,550 | hbm | 1.600x | 69,275.0 / 69,275.0 W | 32% | 86.9 | 138.9 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x147` | Qwen3-8B | 4096 | 119,805 | hbm | 1.598x | 59,902.5 / 59,902.5 W | 32% | 75.2 | 120.2 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x113` | Qwen3-8B | 4096 | 92,095 | hbm | 1.596x | 46,047.5 / 46,047.5 W | 32% | 57.9 | 92.4 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x98` | Qwen3-8B | 4096 | 79,870 | hbm | 1.594x | 39,935.0 / 39,935.0 W | 32% | 50.3 | 80.1 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x74` | Qwen3-8B | 1024 | 60,310 | hbm | 1.590x | 30,155.0 / 30,155.0 W | 32% | 152.0 | 241.7 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x74` | Qwen3-8B | 4096 | 60,310 | hbm | 1.590x | 30,155.0 / 30,155.0 W | 32% | 38.1 | 60.5 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340` | Qwen3-8B | 4096 | 277,100 | hbm | 1.589x | 138,550.0 / 138,550.0 W | 32% | 173.4 | 275.6 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x227` | Qwen3-8B | 4096 | 185,005 | hbm | 1.588x | 92,502.5 / 92,502.5 W | 32% | 116.0 | 184.2 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x196` | Qwen3-8B | 4096 | 159,740 | hbm | 1.588x | 79,870.0 / 79,870.0 W | 32% | 100.2 | 159.1 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | Qwen3-8B | 4096 | 138,550 | hbm | 1.587x | 69,275.0 / 69,275.0 W | 32% | 87.0 | 138.0 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x62` | Qwen3-8B | 1024 | 50,530 | hbm | 1.587x | 25,265.0 / 25,265.0 W | 32% | 127.7 | 202.6 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x62` | Qwen3-8B | 4096 | 50,530 | hbm | 1.586x | 25,265.0 / 25,265.0 W | 32% | 32.0 | 50.7 |

The worst point's dynamic energy is kv read 95.9%, arithmetic 3.8%, operand delivery 0.3%, weight read 0.0%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4-Flash-0731 | 1 | 45,640 | `DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 0.250568 | 4,452.2 | compute | `DSV4-Flash/b200_sxm-x29-nvl72-tensor` | 4.085597 | 14,465.2 | link_latency | 16.31x |
| DeepSeek-V4-Flash-0731 | 2 | 50,530 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x62` | 0.215953 | 16,429.0 | compute | `DSV4-Flash/b200_sxm-x32-nvl72-tensor` | 2.466555 | 16,624.0 | link_latency | 11.42x |
| DeepSeek-V4-Flash-0731 | 4 | 50,530 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x62` | 0.127412 | 16,429.0 | compute | `DSV4-Flash/b200_sxm-x32-nvl72-tensor` | 1.531437 | 18,246.9 | link_latency | 12.02x |
| DeepSeek-V4-Flash-0731 | 8 | 50,530 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x62` | 0.083141 | 16,429.0 | compute | `DSV4-Flash/b200_sxm-x32-nvl72-tensor` | 1.046175 | 20,445.1 | link_latency | 12.58x |
| DeepSeek-V4-Flash-0731 | 16 | 50,530 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x62` | 0.061006 | 16,429.0 | compute | `DSV4-Flash/b200_sxm-x32-nvl72-tensor` | 0.771805 | 22,814.8 | link_latency | 12.65x |
| DeepSeek-V4-Flash-0731 | 32 | 136,920 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 0.071943 | 37,267.2 | compute | `DSV4-Flash/b200_sxm-x86-nvl72-hybrid` | 0.838283 | 56,666.0 | link_latency | 11.65x |
| DeepSeek-V4-Flash-0731 | 64 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.072385 | 75,355.5 | compute | `DSV4-Flash/b200_sxm-x173-nvl72-hybrid` | 0.811836 | 109,489.6 | link_latency | 11.22x |
| DeepSeek-V4-Flash-0731 | 256 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.058203 | 82,347.7 | compute | `DSV4-Flash/b200_sxm-x173-nvl72-hybrid` | 0.412241 | 119,447.7 | link_latency | 6.83x |
| DeepSeek-V4-Flash-0731 | 1024 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.056283 | 87,658.8 | compute | `DSV4-Flash/b200_sxm-x173-nvl72-hybrid` | 0.192140 | 107,533.6 | link_latency | 2.95x |
| DeepSeek-V4-Flash-0731 | 4096 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 0.058539 | 111,351.5 | weight_read | `DSV4-Flash/b200_sxm-x173-expert` | 0.108172 | 96,328.9 | link_latency | 1.85x |
| DeepSeek-V4-Pro-0813 | 1 | 136,105 | `DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x167` | 1.764850 | 8,495.3 | link_latency | `DSV4-Pro/b200_sxm-x85-nvl72-hybrid` | 18.432107 | 48,560.2 | link_latency | 10.44x |
| DeepSeek-V4-Pro-0813 | 2 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 5.081451 | 148,974.1 | compute | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 19.223724 | 102,967.0 | link_latency | 3.78x |
| DeepSeek-V4-Pro-0813 | 4 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 2.668716 | 148,974.1 | compute | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 11.350938 | 105,654.9 | link_latency | 4.25x |
| DeepSeek-V4-Pro-0813 | 8 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1.462348 | 148,974.1 | compute | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 6.932200 | 114,813.0 | link_latency | 4.74x |
| DeepSeek-V4-Pro-0813 | 16 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 0.859164 | 148,974.1 | compute | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 4.691925 | 127,836.2 | link_latency | 5.46x |
| DeepSeek-V4-Pro-0813 | 32 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 0.557572 | 148,974.1 | compute | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 3.512916 | 142,896.1 | link_latency | 6.30x |
| DeepSeek-V4-Pro-0813 | 64 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 0.406776 | 148,974.1 | compute | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 2.816548 | 156,353.8 | weight_read | 6.92x |
| DeepSeek-V4-Pro-0813 | 256 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 0.340900 | 154,436.1 | compute | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 1.787416 | 167,578.3 | weight_read | 4.96x |
| DeepSeek-V4-Pro-0813 | 1024 | 2,172,575 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47` | 0.742020 | 463,213.6 | kv_read | `DSV4-Pro/b200_sxm-x1358-nvl72-hybrid` | 2.269266 | 1,025,893.0 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 4096 | 2,172,575 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47` | 0.671284 | 495,542.2 | kv_read | `DSV4-Pro/b200_sxm-x1358-expert` | 0.725592 | 756,142.9 | weight_read | 1.08x |
| Qwen3-8B | 1 | 12,225 | `Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x15-romfill` | 0.050250 | 1,389.6 | link_latency | `Qwen3-8B/b200_sxm-x8-tensor` | 3.115335 | 6,272.9 | weight_read | 62.00x |
| Qwen3-8B | 2 | 39,935 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49-romfill` | 0.284876 | 8,089.3 | link_latency | `Qwen3-8B/b200_sxm-x25-nvl72-tensor` | 2.205486 | 15,119.2 | link_latency | 7.74x |
| Qwen3-8B | 4 | 41,565 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x51-romfill` | 0.226738 | 10,780.2 | link_latency | `Qwen3-8B/b200_sxm-x26-nvl72-tensor` | 1.226093 | 16,042.8 | link_latency | 5.41x |
| Qwen3-8B | 8 | 41,565 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill` | 0.197175 | 20,782.5 | thermal | `Qwen3-8B/b200_sxm-x26-nvl72-tensor` | 0.720316 | 16,851.9 | link_latency | 3.65x |
| Qwen3-8B | 16 | 50,530 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 0.173904 | 25,265.0 | thermal | `Qwen3-8B/b200_sxm-x32-nvl72-tensor` | 0.495166 | 21,053.6 | link_latency | 2.85x |
| Qwen3-8B | 32 | 119,805 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x147-romfill` | 0.179722 | 59,902.5 | thermal | `Qwen3-8B/b200_sxm-x75-nvl72-hybrid` | 0.524744 | 47,019.0 | link_latency | 2.92x |
| Qwen3-8B | 64 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.186121 | 138,550.0 | thermal | `Qwen3-8B/b200_sxm-x173-nvl72-hybrid` | 0.530063 | 99,336.1 | link_latency | 2.85x |
| Qwen3-8B | 256 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.169916 | 138,550.0 | thermal | `Qwen3-8B/b200_sxm-x173-nvl72-hybrid` | 0.314853 | 116,230.0 | link_latency | 1.85x |
| Qwen3-8B | 1024 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.168429 | 138,550.0 | thermal | `Qwen3-8B/b200_sxm-x173-hybrid` | 0.276464 | 151,954.4 | kv_read | 1.55x |
| Qwen3-8B | 4096 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 0.167996 | 138,550.0 | thermal | `Qwen3-8B/b200_sxm-x173-hybrid` | 0.227768 | 158,278.0 | kv_read | 1.36x |

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
| Qwen3-8B | 8,192 | 8 B | 16.4 GB | 16.00 | 1.208 GB | 1.208 GB | 12.5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 284 B | 166.9 GB | 4.70 | 0.317 GB | 1.382 GB | 35.3 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1,600 B | 892.7 GB | 4.46 | 2.207 GB | 9.856 GB | 18.0 |

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
| Qwen3-8B | 1 | 46,225 | 48,855.6 | wafer-pipeline | 6,464.4 | wafer-tensor | 7.56x | 7,406.7 | pipeline | 3,724.5 | tensor | 1.99x | 6.60x | 1.74x | 0.26x |
| Qwen3-8B | 2 | 92,450 | 46,513.8 | wafer-pipeline | 6,019.4 | wafer-hybrid | 7.73x | 10,054.5 | pipeline | 4,443.7 | tensor | 2.26x | 4.63x | 1.35x | 0.29x |
| Qwen3-8B | 3 | 138,675 | 46,513.8 | wafer-pipeline | 5,822.1 | wafer-tensor | 7.99x | 11,830.5 | pipeline | 4,136.7 | hybrid | 2.86x | 3.93x | 1.41x | 0.36x |
| Qwen3-8B | 4 | 184,900 | 46,513.8 | wafer-pipeline | 5,821.2 | wafer-tensor | 7.99x | 12,976.6 | pipeline | 4,400.6 | hybrid | 2.95x | 3.58x | 1.32x | 0.37x |
| Qwen3-8B | 6 | 277,350 | 58,910.9 | wafer-pipeline | 5,536.7 | wafer-hybrid | 10.64x | 14,350.7 | pipeline | 4,353.8 | hybrid | 3.30x | 4.11x | 1.27x | 0.31x |
| Qwen3-8B | 8 | 369,800 | 64,393.4 | wafer-pipeline | 5,530.5 | wafer-hybrid | 11.64x | 15,171.6 | pipeline | 4,313.8 | hybrid | 3.52x | 4.24x | 1.28x | 0.30x |
| Qwen3-8B | 12 | 554,700 | 71,001.1 | wafer-pipeline | 5,518.2 | wafer-hybrid | 12.87x | 16,089.4 | pipeline | 4,411.5 | hybrid | 3.65x | 4.41x | 1.25x | 0.28x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 49,560.0 | wafer-pipeline | 6,168.1 | wafer-pipeline | 8.03x | 8,842.3 | pipeline | 3,540.5 | tensor | 2.50x | 5.60x | 1.74x | 0.31x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 49,973.2 | wafer-pipeline | 5,471.1 | wafer-hybrid | 9.13x | 10,000.2 | pipeline | 3,971.5 | tensor | 2.52x | 5.00x | 1.38x | 0.28x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 49,973.2 | wafer-pipeline | 5,398.1 | wafer-hybrid | 9.26x | 11,155.4 | pipeline | 3,784.7 | hybrid | 2.95x | 4.48x | 1.43x | 0.32x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 49,973.2 | wafer-pipeline | 5,327.1 | wafer-hybrid | 9.38x | 11,839.3 | pipeline | 3,937.1 | hybrid | 3.01x | 4.22x | 1.35x | 0.32x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 49,973.2 | wafer-pipeline | 5,190.6 | wafer-hybrid | 9.63x | 12,602.9 | pipeline | 3,900.7 | hybrid | 3.23x | 3.97x | 1.33x | 0.34x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 53,241.6 | wafer-pipeline | 5,325.7 | wafer-hybrid | 10.00x | 13,032.4 | pipeline | 3,868.3 | hybrid | 3.37x | 4.09x | 1.38x | 0.34x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 54,340.5 | wafer-pipeline | 5,314.2 | wafer-hybrid | 10.23x | 13,490.9 | pipeline | 3,913.4 | hybrid | 3.45x | 4.03x | 1.36x | 0.34x |
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 22,270.5 | wafer-pipeline | 3,336.7 | wafer-tensor | 6.67x | 5,592.0 | pipeline | 2,141.2 | hybrid | 2.61x | 3.98x | 1.56x | 0.39x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 32,295.7 | wafer-pipeline | 3,619.5 | wafer-hybrid | 8.92x | 6,266.3 | pipeline | 2,326.2 | hybrid | 2.69x | 5.15x | 1.56x | 0.30x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 36,327.2 | wafer-pipeline | 3,736.6 | wafer-hybrid | 9.72x | 7,114.4 | pipeline | 2,310.3 | hybrid | 3.08x | 5.11x | 1.62x | 0.32x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 36,506.2 | wafer-pipeline | 3,681.4 | wafer-hybrid | 9.92x | 7,642.9 | pipeline | 2,298.8 | hybrid | 3.32x | 4.78x | 1.60x | 0.34x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 36,506.2 | wafer-pipeline | 3,555.2 | wafer-hybrid | 10.27x | 8,254.4 | pipeline | 2,389.3 | hybrid | 3.45x | 4.42x | 1.49x | 0.34x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.26x to 0.39x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill | 13,040 | 28,190.4 | 28,190.4 | link_latency | Qwen3-8B/b200_sxm-x8-tensor | 12,800 | 1.02x | tensor | 174.52 | 2,013.6 | 2,013.6 | weight_read | 14.00x | 9.35x | 74.78x | 14.00x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill | 4,075 | 16,619.5 | 16,619.5 | weight_read | Qwen3-8B/b200_sxm-x3-tensor | 4,800 | 0.85x | tensor | 174.11 | 978.7 | 978.7 | weight_read | 16.98x | 14.69x | 44.08x | 16.98x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill | 50,530 | 14,725.8 | 29,451.6 | link_latency | Qwen3-8B/b200_sxm-x32-nvl72-tensor | 51,200 | 0.99x | tensor | 176.61 | 3,730.3 | 7,460.5 | link_latency | 3.95x | 2.44x | 39.06x | 3.95x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49-romfill | 39,935 | 14,198.0 | 28,395.9 | link_latency | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 176.57 | 3,427.6 | 6,855.3 | link_latency | 4.14x | 3.01x | 37.66x | 4.14x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x62-romfill | 50,530 | 12,494.2 | 49,976.7 | link_latency | Qwen3-8B/b200_sxm-x32-nvl72-tensor | 51,200 | 0.99x | tensor | 180.42 | 3,526.8 | 14,107.4 | link_latency | 3.54x | 3.54x | 33.14x | 3.54x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49-romfill | 39,935 | 11,752.8 | 47,011.0 | link_latency | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 180.35 | 3,221.3 | 12,885.1 | link_latency | 3.65x | 3.65x | 31.18x | 3.65x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x62 | 50,530 | 9,588.1 | 76,704.9 | link_latency | Qwen3-8B/b200_sxm-x32-nvl72-tensor | 51,200 | 0.99x | tensor | 188.04 | 3,180.0 | 25,440.2 | link_latency | 3.02x | 3.02x | 25.43x | 3.02x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 8,832.2 | 114,818.8 | thermal | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 187.90 | 2,875.1 | 23,000.7 | link_latency | 3.07x | 4.99x | 23.43x | 3.07x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 9,373.0 | 796,701.8 | thermal | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 188.95 | 3,944.5 | 63,112.2 | link_latency | 2.38x | 12.22x | 24.86x | 2.38x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 7,222.7 | 115,562.7 | thermal | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 203.00 | 2,366.4 | 37,863.2 | link_latency | 3.05x | 3.05x | 19.16x | 3.05x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 9,373.0 | 796,701.8 | thermal | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 201.04 | 3,535.5 | 113,135.4 | link_latency | 2.65x | 7.04x | 24.86x | 2.65x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 3,662.8 | 117,208.1 | thermal | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 233.20 | 1,748.0 | 55,935.0 | link_latency | 2.10x | 2.10x | 9.92x | 2.10x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 9,373.0 | 796,701.8 | thermal | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 225.21 | 2,928.2 | 187,404.2 | link_latency | 3.20x | 4.25x | 24.86x | 3.20x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49-romfill | 39,935 | 1,856.8 | 118,835.1 | thermal | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 293.60 | 1,147.9 | 73,467.9 | kv_read | 1.62x | 1.62x | 5.51x | 1.62x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,185.2 | 815,402.0 | thermal | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 370.26 | 1,442.0 | 369,156.5 | link_latency | 2.21x | 2.21x | 8.76x | 2.21x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49-romfill | 39,935 | 464.4 | 118,884.6 | thermal | Qwen3-8B/b200_sxm-x25-hybrid | 40,000 | 1.00x | hybrid | 320.45 | 383.1 | 98,079.7 | kv_read | 1.21x | 1.21x | 2.10x | 1.21x |
| Qwen3-8B | 1024 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 803.3 | 822,600.1 | thermal | Qwen3-8B/b200_sxm-x173-hybrid | 276,800 | 1.00x | hybrid | 455.65 | 536.8 | 549,635.6 | kv_read | 1.50x | 1.50x | 2.93x | 1.50x |
| Qwen3-8B | 1024 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49-romfill | 39,935 | 116.1 | 118,896.9 | thermal | Qwen3-8B/b200_sxm-x25-hybrid | 40,000 | 1.00x | hybrid | 745.12 | 114.1 | 116,866.7 | kv_read | 1.02x | 1.02x | 1.25x | 1.02x |
| Qwen3-8B | 4096 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 201.3 | 824,720.0 | thermal | Qwen3-8B/b200_sxm-x173-hybrid | 276,800 | 1.00x | hybrid | 1,176.31 | 169.7 | 694,908.5 | kv_read | 1.19x | 1.19x | 1.46x | 1.19x |
| Qwen3-8B | 4096 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49-romfill | 39,935 | 29.0 | 118,900.0 | thermal | Qwen3-8B/b200_sxm-x25-pipeline | 40,000 | 1.00x | pipeline | 143.14 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x59 | 48,085 | 18,118.9 | 18,118.9 | compute | DSV4-Flash/b200_sxm-x30-nvl72-tensor | 48,000 | 1.00x | tensor | 208.67 | 3,566.3 | 3,566.3 | link_latency | 5.08x | 1.13x | 33.90x | 5.08x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x32 | 26,080 | 14,171.0 | 14,171.0 | link_latency | DSV4-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 208.60 | 3,009.8 | 3,009.8 | link_latency | 4.71x | 1.66x | 26.51x | 4.71x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x63 | 51,345 | 17,197.9 | 275,166.3 | compute | DSV4-Flash/b200_sxm-x32-nvl72-tensor | 51,200 | 1.00x | tensor | 210.95 | 3,369.9 | 6,739.8 | link_latency | 5.10x | 16.09x | 32.17x | 5.10x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 16,091.7 | 225,284.5 | compute | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 210.93 | 3,286.0 | 6,571.9 | link_latency | 4.90x | 14.53x | 30.10x | 4.90x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x63 | 51,345 | 17,197.9 | 275,166.3 | compute | DSV4-Flash/b200_sxm-x32-nvl72-tensor | 51,200 | 1.00x | tensor | 215.50 | 2,978.7 | 11,914.9 | link_latency | 5.77x | 16.09x | 32.17x | 5.77x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 16,091.7 | 225,284.5 | compute | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 215.47 | 2,883.2 | 11,532.8 | link_latency | 5.58x | 14.53x | 30.10x | 5.58x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x63 | 51,345 | 17,197.9 | 275,166.3 | compute | DSV4-Flash/b200_sxm-x32-nvl72-tensor | 51,200 | 1.00x | tensor | 224.60 | 2,442.8 | 19,542.7 | link_latency | 7.04x | 14.08x | 32.17x | 7.04x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 16,091.7 | 225,284.5 | compute | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 224.54 | 2,341.2 | 18,729.6 | link_latency | 6.87x | 12.03x | 30.10x | 6.87x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x63 | 51,345 | 17,197.9 | 275,166.3 | compute | DSV4-Flash/b200_sxm-x32-nvl72-tensor | 51,200 | 1.00x | tensor | 242.80 | 1,847.5 | 29,560.2 | link_latency | 9.31x | 9.31x | 32.17x | 9.31x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 14,530.8 | 232,492.3 | compute | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 242.68 | 1,752.1 | 28,033.8 | weight_read | 8.29x | 8.29x | 27.18x | 8.29x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill | 136,920 | 13,849.4 | 581,674.5 | compute | DSV4-Flash/b200_sxm-x86-nvl72-hybrid | 137,600 | 1.00x | hybrid | 248.10 | 2,112.4 | 67,597.6 | link_latency | 6.56x | 8.60x | 25.91x | 6.56x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 8,181.6 | 261,809.8 | compute | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 278.96 | 1,244.9 | 39,837.7 | weight_read | 6.57x | 6.57x | 15.82x | 6.57x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 13,829.4 | 1,175,496.4 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 266.85 | 2,107.3 | 134,866.8 | link_latency | 6.56x | 8.72x | 25.87x | 6.56x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 4,436.9 | 283,959.4 | compute | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 351.51 | 889.0 | 56,895.1 | weight_read | 4.99x | 4.99x | 11.51x | 4.99x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 5,526.7 | 1,414,839.4 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 436.03 | 1,131.8 | 289,752.3 | link_latency | 4.88x | 4.88x | 11.94x | 4.88x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 1,162.3 | 297,536.4 | compute | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 786.85 | 486.7 | 124,606.8 | link_latency | 2.39x | 2.39x | 7.26x | 2.39x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,521.0 | 1,557,470.8 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 1,112.75 | 546.5 | 559,661.8 | link_latency | 2.78x | 2.78x | 7.16x | 2.78x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 294.1 | 301,136.0 | compute | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 2,528.21 | 196.3 | 200,972.2 | link_latency | 1.50x | 1.50x | 4.92x | 1.50x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 464.4 | 1,902,183.6 | weight_read | DSV4-Flash/b200_sxm-x173-expert | 276,800 | 1.00x | expert | 2,783.40 | 217.4 | 890,516.3 | link_latency | 2.14x | 2.14x | 5.95x | 2.14x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 73.7 | 302,049.5 | compute | DSV4-Flash/b200_sxm-x29-pipeline | 46,400 | 0.98x | pipeline | 137.65 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x184 | 149,960 | 5,063.9 | 5,063.9 | link_latency | DSV4-Pro/b200_sxm-x94-nvl72-hybrid | 150,400 | 1.00x | hybrid | 300.87 | 2,193.2 | 4,386.3 | link_latency | 2.31x | 0.37x | 34.43x | 2.31x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x166-romfill | 135,290 | 4,787.0 | 4,787.0 | link_latency | DSV4-Pro/b200_sxm-x85-nvl72-hybrid | 136,000 | 0.99x | hybrid | 300.87 | 2,125.3 | 4,250.6 | link_latency | 2.25x | 0.38x | 32.55x | 2.25x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 422,634.0 | compute | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 303.18 | 2,402.2 | 7,206.5 | link_latency | 1.76x | 14.16x | 28.74x | 1.76x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 422,634.0 | compute | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 305.29 | 2,327.0 | 9,308.0 | link_latency | 1.82x | 14.16x | 28.74x | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 422,634.0 | compute | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 313.72 | 2,070.3 | 16,562.3 | link_latency | 2.04x | 14.16x | 28.74x | 2.04x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 422,634.0 | compute | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 330.58 | 1,702.9 | 27,246.0 | link_latency | 2.48x | 14.16x | 28.74x | 2.48x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 422,634.0 | compute | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 364.30 | 1,271.2 | 40,677.3 | link_latency | 3.32x | 10.39x | 28.74x | 3.32x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 422,634.0 | compute | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 431.74 | 867.4 | 55,512.6 | weight_read | 4.87x | 7.61x | 28.74x | 4.87x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,769.6 | 453,024.2 | compute | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 836.38 | 366.2 | 93,754.5 | weight_read | 4.83x | 4.83x | 13.16x | 4.83x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | 2,172,575 | 609.6 | 624,260.6 | kv_read | DSV4-Pro/b200_sxm-x1358-nvl72-hybrid | 2,172,800 | 1.00x | hybrid | 917.33 | 441.5 | 452,081.4 | weight_read | 1.38x | 1.38x | 4.14x | 1.38x |
| DeepSeek-V4-Pro-0813 | 1024 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399 | 325,185 | 462.6 | 473,748.1 | compute | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 2,454.92 | 163.4 | 167,368.0 | link_latency | 2.83x | 2.83x | 7.60x | 2.83x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 180.2 | 738,201.0 | kv_read | DSV4-Pro/b200_sxm-x1358-expert | 2,172,800 | 1.00x | expert | 1,297.13 | 254.4 | 1,042,104.9 | weight_read | 0.71x | 0.71x | 2.10x | 0.71x |
| DeepSeek-V4-Pro-0813 | 4096 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399 | 325,185 | 116.5 | 476,985.0 | compute | DSV4-Pro/b200_sxm-x203-pipeline | 324,800 | 1.00x | pipeline | 135.34 | infeasible | — | capacity_or_format | — | — | — | — |

## The headline is a band, and each side's share of it is reported apart

Every hop latency in this model states a range, and the ratio moves inside it.
This table re-runs the whole study at both ends of those ranges three ways:
the **wafer fabric** alone (`on_wafer_n5`, `rom_wafer_serdes`), which no GPU design touches; the
**cluster fabric** alone (`nvlink5`, `infiniband_ndr`), which is charged to both families; and
both together.

**Why three and not one.** This study used to publish the joint band only. Moving
both sides at once is the right test for a *common-mode* error, and the wrong one
for asking how much of the uncertainty is ours: the two sides partly cancel, so the
joint band comes out narrower than the wafer side's own band and the reader cannot
see that most of the width sits on the side with the weaker evidence. Reading the
cells: a **low** wafer hop makes the ROM machine faster and the ratio larger, and a
**low** cluster hop makes the GPU faster and the ratio smaller, so the two columns
run in opposite directions by construction.

| Model | ROM mm2 | Ratio stated | Wafer fabric low → high | Cluster fabric low → high | Both together | Widest one-sided span |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 26,080 | 4.71x | 4.71x → 4.71x | 4.71x → 4.71x | 5.28x → 8.20x | 1.0x |
| DeepSeek-V4-Flash-0731 | 28,525 | 5.00x | 5.00x → 5.00x | 5.00x → 5.00x | 5.83x → 9.17x | 1.0x |
| DeepSeek-V4-Flash-0731 | 34,230 | 3.96x | 3.96x → 3.96x | 3.96x → 3.96x | 5.15x → 12.72x | 1.0x |
| DeepSeek-V4-Flash-0731 | 35,860 | 4.32x | 4.32x → 4.32x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 37,490 | 4.35x | 4.35x → 4.35x | 4.35x → 4.35x | 5.12x → 14.07x | 1.0x |
| DeepSeek-V4-Flash-0731 | 38,305 | 4.43x | 4.43x → 4.43x | 4.47x → 4.43x | 5.07x → 14.41x | 1.0x |
| DeepSeek-V4-Flash-0731 | 45,640 | 5.02x | 5.02x → 5.02x | 5.02x → 5.02x | 4.91x → 16.57x | 1.0x |
| DeepSeek-V4-Flash-0731 | 46,225 | 1.74x | 2.47x → 1.69x | 1.74x → 1.74x | 1.72x → 6.11x | 1.5x |
| DeepSeek-V4-Flash-0731 | 46,455 | 4.88x | 4.88x → 4.88x | 4.88x → 4.88x | 4.92x → 16.13x | 1.0x |
| DeepSeek-V4-Flash-0731 | 47,270 | 4.97x | 4.97x → 4.97x | 4.97x → 4.97x | 4.88x → 16.45x | 1.0x |
| DeepSeek-V4-Flash-0731 | 48,085 | 5.08x | 5.08x → 5.08x | 5.08x → 5.08x | 4.89x → 16.80x | 1.0x |
| DeepSeek-V4-Flash-0731 | 50,530 | 4.66x | 4.66x → 4.66x | 4.66x → 4.66x | 4.79x → 15.61x | 1.0x |
| DeepSeek-V4-Flash-0731 | 51,345 | 4.76x | 4.76x → 4.76x | 4.76x → 4.76x | 4.80x → 15.92x | 1.0x |
| DeepSeek-V4-Flash-0731 | 57,050 | 4.32x | 4.32x → 4.32x | 4.32x → 4.32x | 3.90x → 14.72x | 1.0x |
| DeepSeek-V4-Flash-0731 | 68,460 | 3.96x | 3.96x → 3.96x | 3.96x → 3.96x | 3.75x → 13.77x | 1.0x |
| DeepSeek-V4-Flash-0731 | 91,280 | 3.57x | 3.57x → 3.57x | 3.57x → 3.57x | 3.07x → 12.68x | 1.0x |
| DeepSeek-V4-Flash-0731 | 92,095 | 3.48x | 3.48x → 3.48x | 3.48x → 3.48x | 3.06x → 12.41x | 1.0x |
| DeepSeek-V4-Flash-0731 | 92,450 | 1.38x | 2.16x → 0.86x | 1.38x → 1.38x | 1.42x → 3.39x | 2.5x |
| DeepSeek-V4-Flash-0731 | 136,920 | 3.67x | 3.67x → 3.67x | 3.66x → 3.94x | 2.92x → 12.52x | 1.1x |
| DeepSeek-V4-Flash-0731 | 138,550 | 3.62x | 3.62x → 3.62x | 3.62x → 3.90x | 2.91x → 12.38x | 1.1x |
| DeepSeek-V4-Flash-0731 | 138,675 | 1.43x | 2.22x → 0.75x | 1.43x → 1.53x | 1.50x → 2.92x | 3.0x |
| DeepSeek-V4-Flash-0731 | 182,560 | 3.52x | 3.52x → 3.52x | 3.52x → 3.80x | 2.46x → 12.36x | 1.1x |
| DeepSeek-V4-Flash-0731 | 184,900 | 1.35x | 2.09x → 0.72x | 1.35x → 1.46x | 1.38x → 2.87x | 2.9x |
| DeepSeek-V4-Flash-0731 | 185,005 | 3.50x | 3.50x → 3.50x | 3.50x → 3.78x | 2.46x → 12.32x | 1.1x |
| DeepSeek-V4-Flash-0731 | 277,100 | 3.55x | 3.55x → 3.55x | 3.54x → 4.10x | 2.48x → 12.63x | 1.2x |
| DeepSeek-V4-Flash-0731 | 277,350 | 1.33x | 2.03x → 0.71x | 1.33x → 1.54x | 1.35x → 2.89x | 2.8x |
| DeepSeek-V4-Flash-0731 | 323,575 | 1.34x | 2.08x → 0.71x | 1.34x → 1.56x | 1.37x → 2.91x | 2.9x |
| DeepSeek-V4-Flash-0731 | 369,800 | 1.38x | 2.13x → 0.73x | 1.37x → 1.70x | 1.42x → 2.99x | 2.9x |
| DeepSeek-V4-Flash-0731 | 554,700 | 1.36x | 2.11x → 0.72x | 1.36x → 1.78x | 1.39x → 3.03x | 2.9x |
| DeepSeek-V4-Pro-0813 | 135,290 | 2.25x | 2.25x → 2.25x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 136,105 | 2.26x | 2.26x → 2.26x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 138,550 | 2.28x | 2.28x → 2.28x | 2.28x → 2.38x | 3.24x → 3.40x | 1.0x |
| DeepSeek-V4-Pro-0813 | 138,675 | 1.56x | 2.46x → 0.85x | 1.56x → 1.62x | 1.82x → 2.81x | 2.9x |
| DeepSeek-V4-Pro-0813 | 148,330 | 2.31x | 2.31x → 2.31x | 2.31x → 2.41x | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 149,960 | 2.31x | 2.31x → 2.31x | 2.31x → 2.41x | 3.37x → 3.44x | 1.0x |
| DeepSeek-V4-Pro-0813 | 180,115 | 1.98x | 1.98x → 1.98x | 1.98x → 2.08x | 3.00x → 3.80x | 1.0x |
| DeepSeek-V4-Pro-0813 | 184,900 | 1.56x | 2.45x → 0.84x | 1.56x → 1.63x | 1.75x → 2.93x | 2.9x |
| DeepSeek-V4-Pro-0813 | 185,005 | 1.98x | 1.98x → 1.98x | 1.97x → 2.07x | 2.98x → 4.00x | 1.0x |
| DeepSeek-V4-Pro-0813 | 193,155 | 1.96x | 1.96x → 1.96x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 202,120 | 1.95x | 1.95x → 1.95x | 1.94x → 2.04x | 2.93x → 4.51x | 1.0x |
| DeepSeek-V4-Pro-0813 | 213,530 | 1.71x | 1.71x → 1.71x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 231,125 | 1.51x | 2.32x → 0.80x | 1.51x → 1.59x | 1.63x → 2.91x | 2.9x |
| DeepSeek-V4-Pro-0813 | 239,610 | 1.86x | 1.86x → 1.86x | 1.86x → 2.03x | 2.95x → 5.52x | 1.1x |
| DeepSeek-V4-Pro-0813 | 277,100 | 1.84x | 1.84x → 1.84x | 1.84x → 2.01x | 2.56x → 6.10x | 1.1x |
| DeepSeek-V4-Pro-0813 | 277,350 | 1.62x | 2.50x → 0.86x | 1.62x → 1.77x | 1.79x → 3.02x | 2.9x |
| DeepSeek-V4-Pro-0813 | 277,915 | 1.82x | 1.82x → 1.82x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 278,730 | 1.83x | 1.83x → 1.83x | 1.83x → 2.00x | 2.56x → 6.09x | 1.1x |
| DeepSeek-V4-Pro-0813 | 279,545 | 1.84x | 1.84x → 1.84x | 1.84x → 2.01x | — | 1.1x |
| DeepSeek-V4-Pro-0813 | 325,185 | 1.76x | 1.76x → 1.76x | 1.76x → 1.93x | 2.43x → 6.01x | 1.1x |
| DeepSeek-V4-Pro-0813 | 369,800 | 1.60x | 2.45x → 0.86x | 1.60x → 1.82x | 1.76x → 3.04x | 2.9x |
| DeepSeek-V4-Pro-0813 | 554,700 | 1.49x | 2.24x → 0.81x | 1.49x → 1.77x | 1.59x → 2.99x | 2.8x |
| DeepSeek-V4-Pro-0813 | 2,172,575 | 1.40x | 2.00x → 0.80x | 1.39x → 2.52x | 1.45x → 3.30x | 2.5x |
| Qwen3-8B | 4,075 | 16.98x | 16.98x → 16.98x | 15.78x → 16.98x | 19.13x → 19.96x | 1.1x |
| Qwen3-8B | 4,890 | 18.99x | 18.99x → 18.99x | 17.65x → 18.99x | 21.94x → 23.62x | 1.1x |
| Qwen3-8B | 5,705 | 16.44x | 16.44x → 16.44x | — | — | 1.0x |
| Qwen3-8B | 6,520 | 17.59x | 17.59x → 17.59x | 16.03x → 17.59x | 20.77x → 26.43x | 1.1x |
| Qwen3-8B | 8,150 | 16.39x | 16.39x → 16.39x | 14.66x → 16.39x | — | 1.1x |
| Qwen3-8B | 9,780 | 15.45x | 15.45x → 15.45x | 13.60x → 15.45x | 18.63x → 22.80x | 1.1x |
| Qwen3-8B | 12,225 | 13.73x | 13.73x → 13.73x | 11.74x → 13.73x | — | 1.2x |
| Qwen3-8B | 13,040 | 14.00x | 14.00x → 14.00x | 11.97x → 14.00x | 17.01x → 20.87x | 1.2x |
| Qwen3-8B | 39,935 | 4.48x | 4.48x → 4.48x | 4.48x → 4.48x | 6.26x → 7.96x | 1.0x |
| Qwen3-8B | 40,750 | 4.48x | 4.48x → 4.48x | — | — | 1.0x |
| Qwen3-8B | 41,565 | 4.43x | 4.43x → 4.43x | 4.43x → 4.43x | 6.19x → 8.25x | 1.0x |
| Qwen3-8B | 46,225 | 1.74x | 2.71x → 0.92x | 1.74x → 1.74x | 1.98x → 3.03x | 3.0x |
| Qwen3-8B | 46,455 | 4.31x | 4.31x → 4.31x | 4.31x → 4.31x | 6.00x → 7.90x | 1.0x |
| Qwen3-8B | 50,530 | 4.21x | 4.21x → 4.21x | 4.21x → 4.21x | 5.83x → 7.99x | 1.0x |
| Qwen3-8B | 60,310 | 3.22x | 3.22x → 3.22x | 3.22x → 3.22x | 4.64x → 7.91x | 1.0x |
| Qwen3-8B | 79,870 | 3.06x | 3.06x → 3.06x | 3.06x → 3.06x | 4.33x → 7.82x | 1.0x |
| Qwen3-8B | 92,095 | 2.46x | 2.46x → 2.46x | 2.46x → 2.46x | 3.57x → 7.71x | 1.0x |
| Qwen3-8B | 92,450 | 1.35x | 2.11x → 0.74x | 1.35x → 1.35x | 1.43x → 2.77x | 2.9x |
| Qwen3-8B | 119,805 | 2.35x | 2.35x → 2.35x | 2.35x → 2.54x | 3.68x → 8.29x | 1.1x |
| Qwen3-8B | 138,550 | 2.27x | 2.27x → 2.27x | 2.27x → 2.46x | 3.51x → 8.16x | 1.1x |
| Qwen3-8B | 138,675 | 1.41x | 2.26x → 0.77x | 1.41x → 1.52x | 1.59x → 2.79x | 3.0x |
| Qwen3-8B | 159,740 | 2.21x | 2.21x → 2.21x | 2.21x → 2.40x | 3.37x → 8.19x | 1.1x |
| Qwen3-8B | 184,900 | 1.32x | 2.13x → 0.70x | 1.32x → 1.44x | 1.45x → 2.66x | 3.1x |
| Qwen3-8B | 185,005 | 2.12x | 2.12x → 2.12x | 2.12x → 2.31x | 2.86x → 8.09x | 1.1x |
| Qwen3-8B | 277,100 | 2.15x | 2.15x → 2.15x | 2.15x → 2.53x | 2.37x → 8.33x | 1.2x |
| Qwen3-8B | 277,350 | 1.27x | 2.11x → 0.72x | 1.27x → 1.49x | 1.45x → 2.78x | 2.9x |
| Qwen3-8B | 369,800 | 1.28x | 2.16x → 0.72x | 1.28x → 1.61x | 1.49x → 2.84x | 3.0x |
| Qwen3-8B | 554,700 | 1.25x | 2.02x → 0.71x | 1.25x → 1.69x | 1.37x → 2.88x | 2.9x |

## What the fabric clock is worth, and what it is not

`power.fabric_clock_hz` is `assumed` at 1.0 GHz and it has been read as setting
the compute roof on both sides. **It does not.** It is read in one place, `Technology.clock_frequency_hz`, and consumed in one, the clock leg of the static-power
term; the compute roof comes from `compute.format_roofs_ops_s` over the anchor die
area, scaled by node logic density, and never reads it. Where it *is* load-bearing is
the `latency` block: `pipeline_fill_drain_s` (32 fabric cycles) and `sequencer_issue_decode_s`
(3 fabric cycles) are both derived against it and **neither reads it**, so moving the
clock alone silently falsifies two constants that sit on every token's critical path on
both sides. This table moves all three together, which is the only way the question has
an answer that means anything.

The last rows are this repository's own **routed ASAP7** blocks, at the fmax each
artifact records. ASAP7 is a *predictive* academic PDK -- not a foundry PDK, not
silicon -- and `docs/METHODOLOGY.md` section 9 forbids scaling a frequency from it to
N6/N5/N7/N4, so those rows are **the size of a question and never a value**. They are
here because the slowest of them is 17x below the stated clock and a reader is owed
the measurement of what that would cost rather than an argument about it.

| Fabric clock | GHz | In stated band | Qwen3-8B fixed latency/token | DeepSeek-V4-Flash-0731 @ 28,525 mm2 | DeepSeek-V4-Pro-0813 @ 135,290 mm2 | Qwen3-8B @ 4,075 mm2 |
|---|---:|---|---:|---:|---:|---:|
| `band_low` | 0.5000 | yes | 11.53 us | 4.60x | 2.20x | 15.82x |
| `stated` | 1.0000 | yes | 6.82 us | 5.00x | 2.25x | 16.98x |
| `band_high` | 2.0000 | yes | 4.46 us | 5.23x | — | 17.63x |
| `asap7_reduction_s8_g2` | 1.2874 | yes | 5.77 us | 5.10x | 2.27x | 17.27x |
| `asap7_add_bf16_sram_engine` | 0.2391 | **no** | 21.83 us | 3.96x | 2.09x | 13.79x |
| `asap7_matmul_bf16_sram_engine` | 0.0580 | **no** | 83.47 us | 2.44x | — | 8.03x |

## What the ROM bit-cell ratio is worth, executed rather than declared

`rom.cell_to_sram_cell_area_ratio` decides how much weight fits per mm2, which
decides how many devices a model needs, which decides mesh diameter, which is over
half the step time at batch 1. Its stated uncertainty used to be the prose string
"1/6 to 1/4", which nothing ran and which **excluded a measurement this repository
had already committed** -- 0.1298 at 130 nm. The band is now 0.11-0.33 and every
row below is a full re-run of this study at one ratio, not an extrapolation.

The `measured_*` rows are this repository's own bit-cell measurements at nodes that
are **not** this study's node. `docs/METHODOLOGY.md` section 9 forbids scaling or
blending a 130 nm or predictive-7 nm open-PDK figure to N6/N5/N7/N4, so they are the
size of a question and never a value.

The sign is not obvious and that is why it is run: a **less** dense array is more ROM
silicon for the same weights and therefore more parallel read bandwidth, so the
capacity loss and the bandwidth gain pull opposite ways. The binding constraint on
each side is in the artifact at every point.

| ROM cell ratio | Value | In stated band | ROM capacity | Full-array sweep | DeepSeek-V4-Flash-0731 @ 28,525 mm2 | DeepSeek-V4-Pro-0813 @ 135,290 mm2 | Qwen3-8B @ 4,075 mm2 |
|---|---:|---|---:|---:|---:|---:|---:|
| `band_low` | 0.1100 | yes | 28.139 MB/mm2 | 103.4 us | — | — | 16.98x |
| `stated` | 0.3300 | yes | 9.380 MB/mm2 | 34.5 us | 5.00x | 2.25x | 16.98x |
| `band_high` | 0.3300 | yes | 9.380 MB/mm2 | 34.5 us | 5.00x | 2.25x | 16.98x |
| `measured_ihp_sg13g2_130nm` | 0.1298 | yes | 23.854 MB/mm2 | 87.7 us | — | — | 16.98x |
| `measured_asap7_7nm_via_programmed` | 0.2500 | yes | 12.381 MB/mm2 | 45.5 us | 5.40x | — | 16.98x |
| `measured_asap7_7nm_shared_source_drain` | 0.1250 | yes | 24.762 MB/mm2 | 91.0 us | — | — | 16.98x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 8 | 12,800 | 208.45 | 208.45 | 2,255.5 | 2,255.5 |
| DeepSeek-V4-Flash-0731 | 10 | 16,000 | 208.51 | 208.51 | 2,506.8 | 2,506.8 |
| DeepSeek-V4-Flash-0731 | 11 | 17,600 | 208.53 | 208.53 | 2,612.6 | 2,612.6 |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 208.60 | 208.60 | 3,009.8 | 3,009.8 |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 208.62 | 208.62 | 3,125.9 | 3,125.9 |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 208.64 | 208.64 | 3,270.2 | 3,270.2 |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 208.64 | 208.64 | 3,311.8 | 3,311.8 |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 208.65 | 208.65 | 3,350.8 | 3,350.8 |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 208.65 | 208.65 | 3,387.4 | 3,387.4 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 208.67 | 208.67 | 3,540.5 | 3,540.5 |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 208.67 | 208.67 | 3,566.3 | 3,566.3 |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 208.67 | 208.67 | 3,614.1 | 3,614.1 |
| DeepSeek-V4-Flash-0731 | 36 | 57,600 | 208.68 | 208.68 | 3,696.5 | 3,696.5 |
| DeepSeek-V4-Flash-0731 | 43 | 68,800 | 208.69 | 208.69 | 3,809.8 | 3,809.8 |
| DeepSeek-V4-Flash-0731 | 57 | 91,200 | 208.71 | 208.71 | 3,963.1 | 3,963.1 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 208.71 | 208.71 | 3,971.5 | 3,971.5 |
| DeepSeek-V4-Flash-0731 | 86 | 137,600 | 210.91 | 210.91 | 3,777.9 | 3,777.9 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 210.91 | 210.91 | 3,784.7 | 3,784.7 |
| DeepSeek-V4-Flash-0731 | 114 | 182,400 | 210.91 | 210.91 | 3,928.8 | 3,928.8 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 210.91 | 210.91 | 3,937.1 | 3,937.1 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 213.10 | 213.10 | 3,900.7 | 3,900.7 |
| DeepSeek-V4-Flash-0731 | 202 | 323,200 | 213.10 | 213.10 | 3,969.3 | 3,969.3 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 215.30 | 215.30 | 3,868.3 | 3,868.3 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 217.49 | 217.49 | 3,913.4 | 3,913.4 |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 298.43 | 298.43 | 1,855.7 | 1,855.7 |
| DeepSeek-V4-Pro-0813 | 40 | 64,000 | 298.48 | 298.48 | 2,093.6 | 2,093.6 |
| DeepSeek-V4-Pro-0813 | 44 | 70,400 | 298.50 | 298.50 | 2,160.0 | 2,160.0 |
| DeepSeek-V4-Pro-0813 | 46 | 73,600 | 298.50 | 298.50 | 2,190.1 | 2,190.1 |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 298.53 | 298.53 | 2,338.9 | 2,338.9 |
| DeepSeek-V4-Pro-0813 | 63 | 100,800 | 298.54 | 298.54 | 2,388.2 | 2,388.2 |
| DeepSeek-V4-Pro-0813 | 70 | 112,000 | 298.55 | 298.55 | 2,448.2 | 2,448.2 |
| DeepSeek-V4-Pro-0813 | 71 | 113,600 | 298.55 | 298.55 | 2,456.0 | 2,456.0 |
| DeepSeek-V4-Pro-0813 | 85 | 136,000 | 300.87 | 300.87 | 2,125.3 | 2,125.3 |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 300.87 | 300.87 | 2,141.2 | 2,141.2 |
| DeepSeek-V4-Pro-0813 | 93 | 148,800 | 300.87 | 300.87 | 2,186.1 | 2,186.1 |
| DeepSeek-V4-Pro-0813 | 94 | 150,400 | 300.87 | 300.87 | 2,193.2 | 2,193.2 |
| DeepSeek-V4-Pro-0813 | 113 | 180,800 | 300.87 | 300.87 | 2,310.3 | 2,310.3 |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 300.87 | 300.87 | 2,326.2 | 2,326.2 |
| DeepSeek-V4-Pro-0813 | 121 | 193,600 | 300.87 | 300.87 | 2,351.4 | 2,351.4 |
| DeepSeek-V4-Pro-0813 | 126 | 201,600 | 300.87 | 300.87 | 2,375.0 | 2,375.0 |
| DeepSeek-V4-Pro-0813 | 133 | 212,800 | 300.87 | 300.87 | 2,405.9 | 2,405.9 |
| DeepSeek-V4-Pro-0813 | 144 | 230,400 | 300.87 | 300.87 | 2,449.6 | 2,449.6 |
| DeepSeek-V4-Pro-0813 | 150 | 240,000 | 303.18 | 303.18 | 2,222.1 | 2,222.1 |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 303.18 | 303.18 | 2,310.3 | 2,310.3 |
| DeepSeek-V4-Pro-0813 | 174 | 278,400 | 303.18 | 303.18 | 2,313.7 | 2,313.7 |
| DeepSeek-V4-Pro-0813 | 175 | 280,000 | 303.18 | 303.18 | 2,317.1 | 2,317.1 |
| DeepSeek-V4-Pro-0813 | 203 | 324,800 | 303.18 | 303.18 | 2,402.2 | 2,402.2 |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 305.50 | 305.50 | 2,298.8 | 2,298.8 |
| DeepSeek-V4-Pro-0813 | 255 | 408,000 | 305.50 | 305.50 | 2,355.9 | 2,355.9 |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 307.82 | 307.82 | 2,389.3 | 2,389.3 |
| DeepSeek-V4-Pro-0813 | 1,358 | 2,172,800 | 340.25 | 340.25 | 2,230.8 | 2,230.8 |
| Qwen3-8B | 1 | 1,600 | 0.00 | 0.00 | 377.0 | 377.0 |
| Qwen3-8B | 2 | 3,200 | 173.78 | 173.78 | 693.6 | 693.6 |
| Qwen3-8B | 3 | 4,800 | 174.11 | 174.11 | 978.7 | 978.7 |
| Qwen3-8B | 4 | 6,400 | 174.27 | 174.27 | 1,232.0 | 1,232.0 |
| Qwen3-8B | 5 | 8,000 | 174.37 | 174.37 | 1,458.4 | 1,458.4 |
| Qwen3-8B | 6 | 9,600 | 174.44 | 174.44 | 1,662.1 | 1,662.1 |
| Qwen3-8B | 8 | 12,800 | 174.52 | 174.52 | 2,013.6 | 2,013.6 |
| Qwen3-8B | 25 | 40,000 | 174.69 | 174.69 | 3,541.1 | 3,541.1 |
| Qwen3-8B | 26 | 41,600 | 174.69 | 174.69 | 3,590.4 | 3,590.4 |
| Qwen3-8B | 29 | 46,400 | 174.70 | 174.70 | 3,724.5 | 3,724.5 |
| Qwen3-8B | 31 | 49,600 | 174.70 | 174.70 | 3,803.9 | 3,803.9 |
| Qwen3-8B | 32 | 51,200 | 174.70 | 174.70 | 3,841.0 | 3,841.0 |
| Qwen3-8B | 38 | 60,800 | 174.71 | 174.71 | 4,033.7 | 4,033.7 |
| Qwen3-8B | 50 | 80,000 | 174.73 | 174.73 | 4,310.5 | 4,310.5 |
| Qwen3-8B | 58 | 92,800 | 174.73 | 174.73 | 4,443.7 | 4,443.7 |
| Qwen3-8B | 75 | 120,000 | 176.93 | 176.93 | 3,983.8 | 3,983.8 |
| Qwen3-8B | 87 | 139,200 | 176.93 | 176.93 | 4,136.7 | 4,136.7 |
| Qwen3-8B | 100 | 160,000 | 176.93 | 176.93 | 4,269.9 | 4,269.9 |
| Qwen3-8B | 116 | 185,600 | 176.93 | 176.93 | 4,400.6 | 4,400.6 |
| Qwen3-8B | 173 | 276,800 | 179.13 | 179.13 | 4,353.8 | 4,353.8 |
| Qwen3-8B | 231 | 369,600 | 181.32 | 181.32 | 4,313.8 | 4,313.8 |
| Qwen3-8B | 347 | 555,200 | 183.51 | 183.51 | 4,411.5 | 4,411.5 |

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
| DeepSeek-V4-Flash-0731 | 8 | 12,800 | 534.5 | 2,255.5 | — | tensor | 208.45 | 47.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 10 | 16,000 | 534.5 | 2,506.8 | 1,726.9 | tensor | 208.51 | 52.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 11 | 17,600 | 534.5 | 2,612.6 | 1,829.2 | tensor | 208.53 | 54.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 534.5 | 3,009.8 | 2,244.4 | tensor | 208.60 | 62.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 534.5 | 3,125.9 | 1,916.0 | tensor | 208.62 | 65.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 534.5 | 3,270.2 | 2,085.3 | tensor | 208.64 | 68.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 534.5 | 3,311.8 | 2,136.9 | tensor | 208.64 | 69.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 534.5 | 3,350.8 | 2,186.2 | tensor | 208.65 | 69.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 534.5 | 3,387.4 | 2,233.4 | tensor | 208.65 | 70.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 534.5 | 3,540.5 | 2,114.3 | tensor | 208.67 | 73.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 534.5 | 3,566.3 | 2,151.6 | tensor | 208.67 | 74.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 534.5 | 3,614.1 | 2,222.5 | tensor | 208.67 | 75.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 36 | 57,600 | 534.5 | 3,696.5 | 2,097.1 | tensor | 208.68 | 77.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 68,800 | 534.5 | 3,809.8 | 2,082.5 | tensor | 208.69 | 79.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 57 | 91,200 | 534.5 | 3,963.1 | 2,057.4 | tensor | 208.71 | 82.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 534.5 | 3,971.5 | 2,075.8 | tensor | 208.71 | 82.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 86 | 137,600 | 534.5 | 1,633.7 | 3,777.9 | hybrid | 210.91 | 79.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 534.5 | 1,634.3 | 3,784.7 | hybrid | 210.91 | 79.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 114 | 182,400 | 534.5 | 1,647.4 | 3,928.8 | hybrid | 210.91 | 82.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 534.5 | 1,648.1 | 3,937.1 | hybrid | 210.91 | 83.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 534.5 | 1,642.7 | 3,900.7 | hybrid | 213.10 | 83.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 202 | 323,200 | 534.5 | 1,646.7 | 3,969.3 | hybrid | 213.10 | 84.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 534.5 | 1,640.2 | 3,868.3 | hybrid | 215.30 | 83.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 534.5 | 1,641.5 | 3,913.4 | hybrid | 217.49 | 85.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 147.1 | 1,855.7 | 823.9 | tensor | 298.43 | 55.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 40 | 64,000 | 147.1 | 2,093.6 | 883.0 | tensor | 298.48 | 62.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 44 | 70,400 | 147.1 | 2,160.0 | 827.6 | tensor | 298.50 | 64.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 46 | 73,600 | 147.1 | 2,190.1 | 854.7 | tensor | 298.50 | 65.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 147.1 | 2,338.9 | 817.6 | tensor | 298.53 | 69.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 63 | 100,800 | 147.1 | 2,388.2 | 867.8 | tensor | 298.54 | 71.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 70 | 112,000 | 147.1 | 2,448.2 | 858.5 | tensor | 298.55 | 73.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 71 | 113,600 | 147.1 | 2,456.0 | 867.2 | tensor | 298.55 | 73.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 85 | 136,000 | 147.1 | 1,063.9 | 2,125.3 | hybrid | 300.87 | 63.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 147.1 | 1,065.8 | 2,141.2 | hybrid | 300.87 | 64.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 93 | 148,800 | 147.1 | 1,071.3 | 2,186.1 | hybrid | 300.87 | 65.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 94 | 150,400 | 147.1 | 1,072.2 | 2,193.2 | hybrid | 300.87 | 66.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 113 | 180,800 | 147.1 | 1,085.6 | 2,310.3 | hybrid | 300.87 | 69.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 147.1 | 1,087.4 | 2,326.2 | hybrid | 300.87 | 70.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 121 | 193,600 | 147.1 | 1,090.1 | 2,351.4 | hybrid | 300.87 | 70.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 126 | 201,600 | 147.1 | 1,092.6 | 2,375.0 | hybrid | 300.87 | 71.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 133 | 212,800 | 147.1 | 1,095.9 | 2,405.9 | hybrid | 300.87 | 72.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 144 | 230,400 | 147.1 | 1,100.3 | 2,449.6 | hybrid | 300.87 | 73.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 150 | 240,000 | 147.1 | 1,081.6 | 2,222.1 | hybrid | 303.18 | 67.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 147.1 | 1,088.4 | 2,310.3 | hybrid | 303.18 | 70.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 174 | 278,400 | 147.1 | 1,088.6 | 2,313.7 | hybrid | 303.18 | 70.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 175 | 280,000 | 147.1 | 1,088.9 | 2,317.1 | hybrid | 303.18 | 70.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 203 | 324,800 | 147.1 | 1,095.0 | 2,402.2 | hybrid | 303.18 | 72.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 147.1 | 1,089.1 | 2,298.8 | hybrid | 305.50 | 70.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 255 | 408,000 | 147.1 | 1,092.3 | 2,355.9 | hybrid | 305.50 | 72.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 147.1 | 1,094.0 | 2,389.3 | hybrid | 307.82 | 73.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 1358 | 2,172,800 | 147.1 | 1,092.1 | 2,230.8 | hybrid | 340.25 | 75.9% | link_latency |
| Qwen3-8B | 1 | 1,600 | — | — | — | none | 0.00 | 0.0% | thermal |
| Qwen3-8B | 2 | 3,200 | 377.0 | 693.6 | — | tensor | 173.78 | 12.1% | weight_read |
| Qwen3-8B | 3 | 4,800 | 377.0 | 978.7 | — | tensor | 174.11 | 17.0% | weight_read |
| Qwen3-8B | 4 | 6,400 | 377.0 | 1,232.0 | — | tensor | 174.27 | 21.5% | weight_read |
| Qwen3-8B | 5 | 8,000 | 377.0 | 1,458.4 | — | tensor | 174.37 | 25.4% | weight_read |
| Qwen3-8B | 6 | 9,600 | 377.0 | 1,662.1 | — | tensor | 174.44 | 29.0% | weight_read |
| Qwen3-8B | 8 | 12,800 | 377.0 | 2,013.6 | — | tensor | 174.52 | 35.1% | weight_read |
| Qwen3-8B | 25 | 40,000 | 377.0 | 3,541.1 | 1,690.6 | tensor | 174.69 | 61.9% | link_latency |
| Qwen3-8B | 26 | 41,600 | 377.0 | 3,590.4 | 1,736.2 | tensor | 174.69 | 62.7% | link_latency |
| Qwen3-8B | 29 | 46,400 | 377.0 | 3,724.5 | 1,866.3 | tensor | 174.70 | 65.1% | link_latency |
| Qwen3-8B | 31 | 49,600 | 377.0 | 3,803.9 | 1,947.8 | tensor | 174.70 | 66.5% | link_latency |
| Qwen3-8B | 32 | 51,200 | 377.0 | 3,841.0 | 1,987.2 | tensor | 174.70 | 67.1% | link_latency |
| Qwen3-8B | 38 | 60,800 | 377.0 | 4,033.7 | 1,915.7 | tensor | 174.71 | 70.5% | link_latency |
| Qwen3-8B | 50 | 80,000 | 377.0 | 4,310.5 | 1,826.0 | tensor | 174.73 | 75.3% | link_latency |
| Qwen3-8B | 58 | 92,800 | 377.0 | 4,443.7 | 1,836.2 | tensor | 174.73 | 77.6% | link_latency |
| Qwen3-8B | 75 | 120,000 | 377.0 | 1,904.0 | 3,983.8 | hybrid | 176.93 | 70.5% | link_latency |
| Qwen3-8B | 87 | 139,200 | 377.0 | 1,921.0 | 4,136.7 | hybrid | 176.93 | 73.2% | link_latency |
| Qwen3-8B | 100 | 160,000 | 377.0 | 1,935.0 | 4,269.9 | hybrid | 176.93 | 75.5% | link_latency |
| Qwen3-8B | 116 | 185,600 | 377.0 | 1,948.1 | 4,400.6 | hybrid | 176.93 | 77.9% | link_latency |
| Qwen3-8B | 173 | 276,800 | 377.0 | 1,952.9 | 4,353.8 | hybrid | 179.13 | 78.0% | link_latency |
| Qwen3-8B | 231 | 369,600 | 377.0 | 1,955.6 | 4,313.8 | hybrid | 181.32 | 78.2% | link_latency |
| Qwen3-8B | 347 | 555,200 | 377.0 | 1,962.9 | 4,411.5 | hybrid | 183.51 | 81.0% | link_latency |

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
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x5 | Qwen3-8B | 5 | pipeline | rom_package_ucie | rom_board_serdes | 4 | 0.14 us | 710,756.8 tok/s | 7,107,567.5 tok/s | 3 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.04 us; 1 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.10 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x5 | Qwen3-8B | 5 | tensor | rom_package_ucie | rom_board_serdes | 144 | 18.10 us | 5,523.9 tok/s | 55,238.6 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 2 on rom_board_serdes (traversals 2.2) = 16.33 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x5 | Qwen3-8B | 5 | hybrid | rom_package_ucie | rom_board_serdes | 73 | 1.88 us | 53,295.6 tok/s | 532,956.1 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 1 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.10 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x5 | Qwen3-8B | 5 | pipeline | nvlink5 | infiniband_ndr | 4 | 4.84 us | 20,676.5 tok/s | 206,765.0 tok/s | 4 x point_to_point span 2 on nvlink5 (traversals 1.0) = 4.84 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x5 | Qwen3-8B | 5 | tensor | nvlink5 | infiniband_ndr | 72 | 174.37 us | 573.5 tok/s | 5,734.8 tok/s | 72 x all_reduce span 5 on nvlink5 (traversals 2.0) = 174.37 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x49 | Qwen3-8B | 49 | pipeline | rom_package_ucie | rom_board_serdes | 35 | 1.16 us | 86,080.4 tok/s | 860,803.8 tok/s | 27 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.33 us; 8 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.84 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49 | Qwen3-8B | 49 | tensor | rom_package_ucie | rom_board_serdes | 144 | 50.20 us | 1,992.1 tok/s | 19,920.6 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 13 on rom_board_serdes (traversals 6.6) = 48.43 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49 | Qwen3-8B | 49 | hybrid | rom_package_ucie | rom_board_serdes | 84 | 3.03 us | 33,042.7 tok/s | 330,426.8 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 12 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.25 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x49 | Qwen3-8B | 49 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6 | Qwen3-8B | 6 | pipeline | on_wafer_n5 | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x49 | Qwen3-8B | 49 | tensor | nvlink5 | infiniband_ndr | 144 | 497.17 us | 201.1 tok/s | 2,011.4 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 322.65 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x6 | Qwen3-8B | 6 | tensor | on_wafer_n5 | rom_wafer_serdes | 144 | 170.53 us | 586.4 tok/s | 5,864.2 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us; 72 x all_reduce span 6 on rom_wafer_serdes (traversals 4.4) = 31.93 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x49 | Qwen3-8B | 49 | hybrid | nvlink5 | infiniband_ndr | 78 | 187.68 us | 532.8 tok/s | 5,328.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6 | Qwen3-8B | 6 | hybrid | on_wafer_n5 | rom_wafer_serdes | 77 | 139.11 us | 718.9 tok/s | 7,188.7 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us; 5 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.51 us |
| Qwen3-8B/b200_sxm-x2-pipeline | Qwen3-8B | 2 | pipeline | nvlink5 | infiniband_ndr | 1 | 1.21 us | 82,706.0 tok/s | 827,059.9 tok/s | 1 x point_to_point span 2 on nvlink5 (traversals 1.0) = 1.21 us |
| Qwen3-8B/b200_sxm-x2-tensor | Qwen3-8B | 2 | tensor | nvlink5 | infiniband_ndr | 72 | 173.78 us | 575.4 tok/s | 5,754.3 tok/s | 72 x all_reduce span 2 on nvlink5 (traversals 2.0) = 173.78 us |
| Qwen3-8B/b200_sxm-x2-nvl72-tensor | Qwen3-8B | 2 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 173.78 us | 575.4 tok/s | 5,754.3 tok/s | 72 x all_reduce span 2 on nvlink5_nvl72 (traversals 2.0) = 173.78 us |
| Qwen3-8B/b200_sxm-x3-pipeline | Qwen3-8B | 3 | pipeline | nvlink5 | infiniband_ndr | 2 | 2.42 us | 41,353.0 tok/s | 413,530.0 tok/s | 2 x point_to_point span 2 on nvlink5 (traversals 1.0) = 2.42 us |
| Qwen3-8B/b200_sxm-x3-tensor | Qwen3-8B | 3 | tensor | nvlink5 | infiniband_ndr | 72 | 174.11 us | 574.3 tok/s | 5,743.5 tok/s | 72 x all_reduce span 3 on nvlink5 (traversals 2.0) = 174.11 us |
| Qwen3-8B/b200_sxm-x3-nvl72-tensor | Qwen3-8B | 3 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.11 us | 574.3 tok/s | 5,743.5 tok/s | 72 x all_reduce span 3 on nvlink5_nvl72 (traversals 2.0) = 174.11 us |
| Qwen3-8B/b200_sxm-x4-pipeline | Qwen3-8B | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,568.7 tok/s | 275,686.6 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| Qwen3-8B/b200_sxm-x4-tensor | Qwen3-8B | 4 | tensor | nvlink5 | infiniband_ndr | 72 | 174.27 us | 573.8 tok/s | 5,738.1 tok/s | 72 x all_reduce span 4 on nvlink5 (traversals 2.0) = 174.27 us |
| Qwen3-8B/b200_sxm-x4-nvl72-tensor | Qwen3-8B | 4 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.27 us | 573.8 tok/s | 5,738.1 tok/s | 72 x all_reduce span 4 on nvlink5_nvl72 (traversals 2.0) = 174.27 us |
| Qwen3-8B/b200_sxm-x5-pipeline | Qwen3-8B | 5 | pipeline | nvlink5 | infiniband_ndr | 4 | 4.84 us | 20,676.5 tok/s | 206,765.0 tok/s | 4 x point_to_point span 2 on nvlink5 (traversals 1.0) = 4.84 us |
| Qwen3-8B/b200_sxm-x5-tensor | Qwen3-8B | 5 | tensor | nvlink5 | infiniband_ndr | 72 | 174.37 us | 573.5 tok/s | 5,734.8 tok/s | 72 x all_reduce span 5 on nvlink5 (traversals 2.0) = 174.37 us |
| Qwen3-8B/b200_sxm-x5-nvl72-tensor | Qwen3-8B | 5 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.37 us | 573.5 tok/s | 5,734.8 tok/s | 72 x all_reduce span 5 on nvlink5_nvl72 (traversals 2.0) = 174.37 us |
| Qwen3-8B/b200_sxm-x6-pipeline | Qwen3-8B | 6 | pipeline | nvlink5 | infiniband_ndr | 5 | 6.05 us | 16,541.2 tok/s | 165,412.0 tok/s | 5 x point_to_point span 2 on nvlink5 (traversals 1.0) = 6.05 us |
| Qwen3-8B/b200_sxm-x6-tensor | Qwen3-8B | 6 | tensor | nvlink5 | infiniband_ndr | 72 | 174.44 us | 573.3 tok/s | 5,732.7 tok/s | 72 x all_reduce span 6 on nvlink5 (traversals 2.0) = 174.44 us |
| Qwen3-8B/b200_sxm-x6-nvl72-tensor | Qwen3-8B | 6 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.44 us | 573.3 tok/s | 5,732.7 tok/s | 72 x all_reduce span 6 on nvlink5_nvl72 (traversals 2.0) = 174.44 us |
| Qwen3-8B/b200_sxm-x8-pipeline | Qwen3-8B | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.46 us | 11,815.1 tok/s | 118,151.4 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us |
| Qwen3-8B/b200_sxm-x8-tensor | Qwen3-8B | 8 | tensor | nvlink5 | infiniband_ndr | 72 | 174.52 us | 573.0 tok/s | 5,730.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us |
| Qwen3-8B/b200_sxm-x8-nvl72-tensor | Qwen3-8B | 8 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.52 us | 573.0 tok/s | 5,730.0 tok/s | 72 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 174.52 us |
| Qwen3-8B/b200_sxm-x25-pipeline | Qwen3-8B | 25 | pipeline | nvlink5 | infiniband_ndr | 24 | 31.97 us | 3,127.7 tok/s | 31,276.7 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x25-tensor | Qwen3-8B | 25 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x25-hybrid | Qwen3-8B | 25 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x25-nvl72-tensor | Qwen3-8B | 25 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.69 us | 572.5 tok/s | 5,724.5 tok/s | 72 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 174.69 us |
| Qwen3-8B/b200_sxm-x26-pipeline | Qwen3-8B | 26 | pipeline | nvlink5 | infiniband_ndr | 25 | 33.18 us | 3,013.7 tok/s | 30,137.0 tok/s | 22 x point_to_point span 2 on nvlink5 (traversals 1.0) = 26.60 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x26-tensor | Qwen3-8B | 26 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x26-hybrid | Qwen3-8B | 26 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x26-nvl72-tensor | Qwen3-8B | 26 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.69 us | 572.4 tok/s | 5,724.4 tok/s | 72 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 174.69 us |
| Qwen3-8B/b200_sxm-x29-pipeline | Qwen3-8B | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x29-tensor | Qwen3-8B | 29 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x29-hybrid | Qwen3-8B | 29 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x29-nvl72-tensor | Qwen3-8B | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.70 us | 572.4 tok/s | 5,724.2 tok/s | 72 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 174.70 us |
| Qwen3-8B/b200_sxm-x31-pipeline | Qwen3-8B | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.23 us | 2,549.2 tok/s | 25,492.5 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x31-tensor | Qwen3-8B | 31 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x31-hybrid | Qwen3-8B | 31 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x31-nvl72-tensor | Qwen3-8B | 31 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.70 us | 572.4 tok/s | 5,724.0 tok/s | 72 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 174.70 us |
| Qwen3-8B/b200_sxm-x32-pipeline | Qwen3-8B | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.44 us | 2,473.0 tok/s | 24,730.2 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x32-tensor | Qwen3-8B | 32 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x32-hybrid | Qwen3-8B | 32 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x32-nvl72-tensor | Qwen3-8B | 32 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.70 us | 572.4 tok/s | 5,723.9 tok/s | 72 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 174.70 us |
| Qwen3-8B/b200_sxm-x38-pipeline | Qwen3-8B | 38 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x38-tensor | Qwen3-8B | 38 | tensor | nvlink5 | infiniband_ndr | 144 | 495.15 us | 202.0 tok/s | 2,019.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x38-hybrid | Qwen3-8B | 38 | hybrid | nvlink5 | infiniband_ndr | 76 | 183.30 us | 545.6 tok/s | 5,455.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x38-nvl72-tensor | Qwen3-8B | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.71 us | 572.4 tok/s | 5,723.6 tok/s | 72 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 174.71 us |
| Qwen3-8B/b200_sxm-x50-pipeline | Qwen3-8B | 50 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x50-tensor | Qwen3-8B | 50 | tensor | nvlink5 | infiniband_ndr | 144 | 497.17 us | 201.1 tok/s | 2,011.4 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 322.65 us |
| Qwen3-8B/b200_sxm-x50-hybrid | Qwen3-8B | 50 | hybrid | nvlink5 | infiniband_ndr | 78 | 187.68 us | 532.8 tok/s | 5,328.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| Qwen3-8B/b200_sxm-x50-nvl72-tensor | Qwen3-8B | 50 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.73 us | 572.3 tok/s | 5,723.2 tok/s | 72 x all_reduce span 50 on nvlink5_nvl72 (traversals 2.0) = 174.73 us |
| Qwen3-8B/b200_sxm-x58-pipeline | Qwen3-8B | 58 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x58-tensor | Qwen3-8B | 58 | tensor | nvlink5 | infiniband_ndr | 144 | 497.81 us | 200.9 tok/s | 2,008.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 323.29 us |
| Qwen3-8B/b200_sxm-x58-hybrid | Qwen3-8B | 58 | hybrid | nvlink5 | infiniband_ndr | 79 | 189.88 us | 526.7 tok/s | 5,266.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| Qwen3-8B/b200_sxm-x58-nvl72-tensor | Qwen3-8B | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.73 us | 572.3 tok/s | 5,723.0 tok/s | 72 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 174.73 us |
| Qwen3-8B/b200_sxm-x75-pipeline | Qwen3-8B | 75 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x75-tensor | Qwen3-8B | 75 | tensor | nvlink5 | infiniband_ndr | 144 | 498.69 us | 200.5 tok/s | 2,005.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 324.17 us |
| Qwen3-8B/b200_sxm-x75-hybrid | Qwen3-8B | 75 | hybrid | nvlink5 | infiniband_ndr | 81 | 194.26 us | 514.8 tok/s | 5,147.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.74 us |
| Qwen3-8B/b200_sxm-x75-nvl72-tensor | Qwen3-8B | 75 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x75-nvl72-hybrid | Qwen3-8B | 75 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x87-pipeline | Qwen3-8B | 87 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x87-tensor | Qwen3-8B | 87 | tensor | nvlink5 | infiniband_ndr | 144 | 499.01 us | 200.4 tok/s | 2,004.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 324.49 us |
| Qwen3-8B/b200_sxm-x87-hybrid | Qwen3-8B | 87 | hybrid | nvlink5 | infiniband_ndr | 82 | 196.46 us | 509.0 tok/s | 5,090.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| Qwen3-8B/b200_sxm-x87-nvl72-tensor | Qwen3-8B | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x87-nvl72-hybrid | Qwen3-8B | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x100-pipeline | Qwen3-8B | 100 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x100-tensor | Qwen3-8B | 100 | tensor | nvlink5 | infiniband_ndr | 144 | 499.51 us | 200.2 tok/s | 2,002.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 324.99 us |
| Qwen3-8B/b200_sxm-x100-hybrid | Qwen3-8B | 100 | hybrid | nvlink5 | infiniband_ndr | 84 | 200.85 us | 497.9 tok/s | 4,978.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 26.33 us |
| Qwen3-8B/b200_sxm-x100-nvl72-tensor | Qwen3-8B | 100 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x100-nvl72-hybrid | Qwen3-8B | 100 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x116-pipeline | Qwen3-8B | 116 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x116-tensor | Qwen3-8B | 116 | tensor | nvlink5 | infiniband_ndr | 144 | 499.87 us | 200.1 tok/s | 2,000.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 325.35 us |
| Qwen3-8B/b200_sxm-x116-hybrid | Qwen3-8B | 116 | hybrid | nvlink5 | infiniband_ndr | 86 | 205.23 us | 487.2 tok/s | 4,872.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| Qwen3-8B/b200_sxm-x116-nvl72-tensor | Qwen3-8B | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x116-nvl72-hybrid | Qwen3-8B | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x173-pipeline | Qwen3-8B | 173 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x173-tensor | Qwen3-8B | 173 | tensor | nvlink5 | infiniband_ndr | 144 | 500.62 us | 199.8 tok/s | 1,997.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 326.10 us |
| Qwen3-8B/b200_sxm-x173-hybrid | Qwen3-8B | 173 | hybrid | nvlink5 | infiniband_ndr | 93 | 220.59 us | 453.3 tok/s | 4,533.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| Qwen3-8B/b200_sxm-x173-nvl72-tensor | Qwen3-8B | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 490.65 us | 203.8 tok/s | 2,038.1 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 315.91 us |
| Qwen3-8B/b200_sxm-x173-nvl72-hybrid | Qwen3-8B | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 74 | 179.13 us | 558.3 tok/s | 5,582.6 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| Qwen3-8B/b200_sxm-x231-pipeline | Qwen3-8B | 231 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x231-tensor | Qwen3-8B | 231 | tensor | nvlink5 | infiniband_ndr | 144 | 501.01 us | 199.6 tok/s | 1,996.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 326.49 us |
| Qwen3-8B/b200_sxm-x231-hybrid | Qwen3-8B | 231 | hybrid | nvlink5 | infiniband_ndr | 100 | 235.95 us | 423.8 tok/s | 4,238.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| Qwen3-8B/b200_sxm-x231-nvl72-tensor | Qwen3-8B | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 493.60 us | 202.6 tok/s | 2,025.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x231-nvl72-hybrid | Qwen3-8B | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 75 | 181.32 us | 551.5 tok/s | 5,515.1 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x347-pipeline | Qwen3-8B | 347 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x347-tensor | Qwen3-8B | 347 | tensor | nvlink5 | infiniband_ndr | 144 | 501.43 us | 199.4 tok/s | 1,994.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 326.91 us |
| Qwen3-8B/b200_sxm-x347-hybrid | Qwen3-8B | 347 | hybrid | nvlink5 | infiniband_ndr | 107 | 251.30 us | 397.9 tok/s | 3,979.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.78 us |
| Qwen3-8B/b200_sxm-x347-nvl72-tensor | Qwen3-8B | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 495.37 us | 201.9 tok/s | 2,018.7 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x347-nvl72-hybrid | Qwen3-8B | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 76 | 183.51 us | 544.9 tok/s | 5,449.2 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x58 | DeepSeek-V4-Flash-0731 | 58 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x35 | DeepSeek-V4-Flash-0731 | 35 | tensor | rom_package_ucie | rom_board_serdes | 172 | 41.00 us | 2,439.0 tok/s | 24,390.2 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 9 on rom_board_serdes (traversals 4.4) = 38.88 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x59 | DeepSeek-V4-Flash-0731 | 59 | hybrid | rom_package_ucie | rom_board_serdes | 100 | 3.58 us | 27,932.9 tok/s | 279,329.3 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 14 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.46 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x58 | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x32 | DeepSeek-V4-Flash-0731 | 32 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x46 | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x62 | DeepSeek-V4-Flash-0731 | 62 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x56 | DeepSeek-V4-Flash-0731 | 56 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.97 us | 1,667.6 tok/s | 16,675.9 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 14 on rom_board_serdes (traversals 6.6) = 57.85 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x63 | DeepSeek-V4-Flash-0731 | 63 | hybrid | rom_package_ucie | rom_board_serdes | 101 | 3.68 us | 27,140.3 tok/s | 271,403.2 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.57 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x62 | DeepSeek-V4-Flash-0731 | 62 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7 | DeepSeek-V4-Flash-0731 | 7 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x56 | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x7 | DeepSeek-V4-Flash-0731 | 7 | tensor | on_wafer_n5 | rom_wafer_serdes | 172 | 203.69 us | 490.9 tok/s | 4,909.4 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 86 x all_reduce span 7 on rom_wafer_serdes (traversals 4.4) = 38.14 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x56 | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x7 | DeepSeek-V4-Flash-0731 | 7 | hybrid | on_wafer_n5 | rom_wafer_serdes | 92 | 166.16 us | 601.8 tok/s | 6,018.4 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 6 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.61 us |
| DSV4-Flash/b200_sxm-x8-pipeline | DeepSeek-V4-Flash-0731 | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.46 us | 11,815.1 tok/s | 118,151.4 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us |
| DSV4-Flash/b200_sxm-x8-tensor | DeepSeek-V4-Flash-0731 | 8 | tensor | nvlink5 | infiniband_ndr | 86 | 208.45 us | 479.7 tok/s | 4,797.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us |
| DSV4-Flash/b200_sxm-x8-nvl72-tensor | DeepSeek-V4-Flash-0731 | 8 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.45 us | 479.7 tok/s | 4,797.2 tok/s | 86 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 208.45 us |
| DSV4-Flash/b200_sxm-x8-expert | DeepSeek-V4-Flash-0731 | 8 | expert | nvlink5 | infiniband_ndr | 172 | 312.24 us | 320.3 tok/s | 3,202.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on nvlink5 (traversals 1.0) = 103.79 us |
| DSV4-Flash/b200_sxm-x8-nvl72-expert | DeepSeek-V4-Flash-0731 | 8 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.24 us | 320.3 tok/s | 3,202.6 tok/s | 86 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.79 us |
| DSV4-Flash/b200_sxm-x10-pipeline | DeepSeek-V4-Flash-0731 | 10 | pipeline | nvlink5 | infiniband_ndr | 9 | 11.87 us | 8,427.0 tok/s | 84,269.7 tok/s | 8 x point_to_point span 2 on nvlink5 (traversals 1.0) = 9.67 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x10-tensor | DeepSeek-V4-Flash-0731 | 10 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x10-hybrid | DeepSeek-V4-Flash-0731 | 10 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x10-nvl72-tensor | DeepSeek-V4-Flash-0731 | 10 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.51 us | 479.6 tok/s | 4,795.9 tok/s | 86 x all_reduce span 10 on nvlink5_nvl72 (traversals 2.0) = 208.51 us |
| DSV4-Flash/b200_sxm-x10-expert | DeepSeek-V4-Flash-0731 | 10 | expert | nvlink5 | infiniband_ndr | 172 | 391.49 us | 255.4 tok/s | 2,554.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 183.03 us |
| DSV4-Flash/b200_sxm-x10-nvl72-expert | DeepSeek-V4-Flash-0731 | 10 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.18 us | 320.3 tok/s | 3,203.2 tok/s | 86 x all_reduce span 10 on nvlink5_nvl72 (traversals 2.0) = 208.51 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.67 us |
| DSV4-Flash/b200_sxm-x11-pipeline | DeepSeek-V4-Flash-0731 | 11 | pipeline | nvlink5 | infiniband_ndr | 10 | 13.08 us | 7,647.7 tok/s | 76,477.4 tok/s | 9 x point_to_point span 2 on nvlink5 (traversals 1.0) = 10.88 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x11-tensor | DeepSeek-V4-Flash-0731 | 11 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x11-hybrid | DeepSeek-V4-Flash-0731 | 11 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x11-nvl72-tensor | DeepSeek-V4-Flash-0731 | 11 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.53 us | 479.5 tok/s | 4,795.4 tok/s | 86 x all_reduce span 11 on nvlink5_nvl72 (traversals 2.0) = 208.53 us |
| DSV4-Flash/b200_sxm-x11-expert | DeepSeek-V4-Flash-0731 | 11 | expert | nvlink5 | infiniband_ndr | 172 | 390.72 us | 255.9 tok/s | 2,559.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 182.27 us |
| DSV4-Flash/b200_sxm-x11-nvl72-expert | DeepSeek-V4-Flash-0731 | 11 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.16 us | 320.3 tok/s | 3,203.5 tok/s | 86 x all_reduce span 11 on nvlink5_nvl72 (traversals 2.0) = 208.53 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.63 us |
| DSV4-Flash/b200_sxm-x16-pipeline | DeepSeek-V4-Flash-0731 | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.12 us | 5,229.8 tok/s | 52,297.8 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-tensor | DeepSeek-V4-Flash-0731 | 16 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x16-hybrid | DeepSeek-V4-Flash-0731 | 16 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-nvl72-tensor | DeepSeek-V4-Flash-0731 | 16 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.60 us | 479.4 tok/s | 4,793.8 tok/s | 86 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 208.60 us |
| DSV4-Flash/b200_sxm-x16-expert | DeepSeek-V4-Flash-0731 | 16 | expert | nvlink5 | infiniband_ndr | 172 | 387.29 us | 258.2 tok/s | 2,582.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.86 us |
| DSV4-Flash/b200_sxm-x16-nvl72-expert | DeepSeek-V4-Flash-0731 | 16 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.10 us | 320.4 tok/s | 3,204.2 tok/s | 86 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 208.60 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.49 us |
| DSV4-Flash/b200_sxm-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink5 | infiniband_ndr | 17 | 22.52 us | 4,439.7 tok/s | 44,396.7 tok/s | 15 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.14 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x18-nvl72-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.62 us | 479.3 tok/s | 4,793.5 tok/s | 86 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 208.62 us |
| DSV4-Flash/b200_sxm-x18-expert | DeepSeek-V4-Flash-0731 | 18 | expert | nvlink5 | infiniband_ndr | 172 | 386.70 us | 258.6 tok/s | 2,586.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.28 us |
| DSV4-Flash/b200_sxm-x18-nvl72-expert | DeepSeek-V4-Flash-0731 | 18 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.08 us | 320.4 tok/s | 3,204.3 tok/s | 86 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 208.62 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.46 us |
| DSV4-Flash/b200_sxm-x21-pipeline | DeepSeek-V4-Flash-0731 | 21 | pipeline | nvlink5 | infiniband_ndr | 20 | 26.15 us | 3,823.9 tok/s | 38,238.7 tok/s | 18 x point_to_point span 2 on nvlink5 (traversals 1.0) = 21.76 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-tensor | DeepSeek-V4-Flash-0731 | 21 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x21-hybrid | DeepSeek-V4-Flash-0731 | 21 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-nvl72-tensor | DeepSeek-V4-Flash-0731 | 21 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.64 us | 479.3 tok/s | 4,793.0 tok/s | 86 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 208.64 us |
| DSV4-Flash/b200_sxm-x21-expert | DeepSeek-V4-Flash-0731 | 21 | expert | nvlink5 | infiniband_ndr | 172 | 386.03 us | 259.0 tok/s | 2,590.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.61 us |
| DSV4-Flash/b200_sxm-x21-nvl72-expert | DeepSeek-V4-Flash-0731 | 21 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.06 us | 320.5 tok/s | 3,204.5 tok/s | 86 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 208.64 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.42 us |
| DSV4-Flash/b200_sxm-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.36 us | 3,654.9 tok/s | 36,548.9 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 22.97 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-nvl72-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.64 us | 479.3 tok/s | 4,792.9 tok/s | 86 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 208.64 us |
| DSV4-Flash/b200_sxm-x22-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink5 | infiniband_ndr | 172 | 385.85 us | 259.2 tok/s | 2,591.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.42 us |
| DSV4-Flash/b200_sxm-x22-nvl72-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.06 us | 320.5 tok/s | 3,204.6 tok/s | 86 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 208.64 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.41 us |
| DSV4-Flash/b200_sxm-x23-pipeline | DeepSeek-V4-Flash-0731 | 23 | pipeline | nvlink5 | infiniband_ndr | 22 | 28.57 us | 3,500.2 tok/s | 35,002.1 tok/s | 20 x point_to_point span 2 on nvlink5 (traversals 1.0) = 24.18 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x23-tensor | DeepSeek-V4-Flash-0731 | 23 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x23-hybrid | DeepSeek-V4-Flash-0731 | 23 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x23-nvl72-tensor | DeepSeek-V4-Flash-0731 | 23 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.8 tok/s | 86 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x23-expert | DeepSeek-V4-Flash-0731 | 23 | expert | nvlink5 | infiniband_ndr | 172 | 385.68 us | 259.3 tok/s | 2,592.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.26 us |
| DSV4-Flash/b200_sxm-x23-nvl72-expert | DeepSeek-V4-Flash-0731 | 23 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.05 us | 320.5 tok/s | 3,204.6 tok/s | 86 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.40 us |
| DSV4-Flash/b200_sxm-x24-pipeline | DeepSeek-V4-Flash-0731 | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 29.78 us | 3,358.1 tok/s | 33,580.9 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x24-tensor | DeepSeek-V4-Flash-0731 | 24 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x24-hybrid | DeepSeek-V4-Flash-0731 | 24 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x24-nvl72-tensor | DeepSeek-V4-Flash-0731 | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.7 tok/s | 86 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x24-expert | DeepSeek-V4-Flash-0731 | 24 | expert | nvlink5 | infiniband_ndr | 172 | 385.19 us | 259.6 tok/s | 2,596.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.10 us |
| DSV4-Flash/b200_sxm-x24-nvl72-expert | DeepSeek-V4-Flash-0731 | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.05 us | 320.5 tok/s | 3,204.7 tok/s | 86 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.40 us |
| DSV4-Flash/b200_sxm-x29-pipeline | DeepSeek-V4-Flash-0731 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x29-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x29-hybrid | DeepSeek-V4-Flash-0731 | 29 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x29-nvl72-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.67 us | 479.2 tok/s | 4,792.3 tok/s | 86 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 208.67 us |
| DSV4-Flash/b200_sxm-x29-expert | DeepSeek-V4-Flash-0731 | 29 | expert | nvlink5 | infiniband_ndr | 172 | 384.58 us | 260.0 tok/s | 2,600.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.50 us |
| DSV4-Flash/b200_sxm-x29-nvl72-expert | DeepSeek-V4-Flash-0731 | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.03 us | 320.5 tok/s | 3,204.8 tok/s | 86 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 208.67 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.36 us |
| DSV4-Flash/b200_sxm-x30-pipeline | DeepSeek-V4-Flash-0731 | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.02 us | 2,630.3 tok/s | 26,303.2 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.44 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x30-tensor | DeepSeek-V4-Flash-0731 | 30 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x30-hybrid | DeepSeek-V4-Flash-0731 | 30 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x30-nvl72-tensor | DeepSeek-V4-Flash-0731 | 30 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.67 us | 479.2 tok/s | 4,792.3 tok/s | 86 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 208.67 us |
| DSV4-Flash/b200_sxm-x30-expert | DeepSeek-V4-Flash-0731 | 30 | expert | nvlink5 | infiniband_ndr | 172 | 384.48 us | 260.1 tok/s | 2,600.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.40 us |
| DSV4-Flash/b200_sxm-x30-nvl72-expert | DeepSeek-V4-Flash-0731 | 30 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.03 us | 320.5 tok/s | 3,204.9 tok/s | 86 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 208.67 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.36 us |
| DSV4-Flash/b200_sxm-x32-pipeline | DeepSeek-V4-Flash-0731 | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.44 us | 2,473.0 tok/s | 24,730.2 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x32-tensor | DeepSeek-V4-Flash-0731 | 32 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x32-hybrid | DeepSeek-V4-Flash-0731 | 32 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x32-nvl72-tensor | DeepSeek-V4-Flash-0731 | 32 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.67 us | 479.2 tok/s | 4,792.1 tok/s | 86 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 208.67 us |
| DSV4-Flash/b200_sxm-x32-expert | DeepSeek-V4-Flash-0731 | 32 | expert | nvlink5 | infiniband_ndr | 172 | 384.14 us | 260.3 tok/s | 2,603.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.91 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.22 us |
| DSV4-Flash/b200_sxm-x32-nvl72-expert | DeepSeek-V4-Flash-0731 | 32 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.02 us | 320.5 tok/s | 3,204.9 tok/s | 86 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 208.67 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.35 us |
| DSV4-Flash/b200_sxm-x36-pipeline | DeepSeek-V4-Flash-0731 | 36 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/b200_sxm-x36-tensor | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink5 | infiniband_ndr | 172 | 591.43 us | 169.1 tok/s | 1,690.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 382.98 us |
| DSV4-Flash/b200_sxm-x36-hybrid | DeepSeek-V4-Flash-0731 | 36 | hybrid | nvlink5 | infiniband_ndr | 90 | 217.23 us | 460.3 tok/s | 4,603.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/b200_sxm-x36-nvl72-tensor | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.68 us | 479.2 tok/s | 4,792.0 tok/s | 86 x all_reduce span 36 on nvlink5_nvl72 (traversals 2.0) = 208.68 us |
| DSV4-Flash/b200_sxm-x36-expert | DeepSeek-V4-Flash-0731 | 36 | expert | nvlink5 | infiniband_ndr | 172 | 383.84 us | 260.5 tok/s | 2,605.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.91 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.93 us |
| DSV4-Flash/b200_sxm-x36-nvl72-expert | DeepSeek-V4-Flash-0731 | 36 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.01 us | 320.5 tok/s | 3,205.0 tok/s | 86 x all_reduce span 36 on nvlink5_nvl72 (traversals 2.0) = 208.68 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.33 us |
| DSV4-Flash/b200_sxm-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x43-nvl72-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.69 us | 479.2 tok/s | 4,791.7 tok/s | 86 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 208.69 us |
| DSV4-Flash/b200_sxm-x43-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink5 | infiniband_ndr | 172 | 383.36 us | 260.9 tok/s | 2,608.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.81 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.55 us |
| DSV4-Flash/b200_sxm-x43-nvl72-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.00 us | 320.5 tok/s | 3,205.1 tok/s | 86 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 208.69 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.31 us |
| DSV4-Flash/b200_sxm-x57-pipeline | DeepSeek-V4-Flash-0731 | 57 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x57-tensor | DeepSeek-V4-Flash-0731 | 57 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x57-hybrid | DeepSeek-V4-Flash-0731 | 57 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x57-nvl72-tensor | DeepSeek-V4-Flash-0731 | 57 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.4 tok/s | 86 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x57-expert | DeepSeek-V4-Flash-0731 | 57 | expert | nvlink5 | infiniband_ndr | 172 | 382.76 us | 261.3 tok/s | 2,612.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.69 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.06 us |
| DSV4-Flash/b200_sxm-x57-nvl72-expert | DeepSeek-V4-Flash-0731 | 57 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.28 us |
| DSV4-Flash/b200_sxm-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x58-nvl72-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.4 tok/s | 86 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x58-expert | DeepSeek-V4-Flash-0731 | 58 | expert | nvlink5 | infiniband_ndr | 172 | 382.73 us | 261.3 tok/s | 2,612.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.69 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.04 us |
| DSV4-Flash/b200_sxm-x58-nvl72-expert | DeepSeek-V4-Flash-0731 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.28 us |
| DSV4-Flash/b200_sxm-x86-pipeline | DeepSeek-V4-Flash-0731 | 86 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x86-tensor | DeepSeek-V4-Flash-0731 | 86 | tensor | nvlink5 | infiniband_ndr | 172 | 596.04 us | 167.8 tok/s | 1,677.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 387.59 us |
| DSV4-Flash/b200_sxm-x86-hybrid | DeepSeek-V4-Flash-0731 | 86 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.39 us | 434.0 tok/s | 4,340.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| DSV4-Flash/b200_sxm-x86-nvl72-tensor | DeepSeek-V4-Flash-0731 | 86 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x86-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 86 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x86-expert | DeepSeek-V4-Flash-0731 | 86 | expert | nvlink5 | infiniband_ndr | 172 | 382.17 us | 261.7 tok/s | 2,616.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.61 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.56 us |
| DSV4-Flash/b200_sxm-x86-nvl72-expert | DeepSeek-V4-Flash-0731 | 86 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.28 us | 260.2 tok/s | 2,602.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.56 us |
| DSV4-Flash/b200_sxm-x87-pipeline | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x87-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5 | infiniband_ndr | 172 | 596.04 us | 167.8 tok/s | 1,677.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 387.59 us |
| DSV4-Flash/b200_sxm-x87-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.39 us | 434.0 tok/s | 4,340.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| DSV4-Flash/b200_sxm-x87-nvl72-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x87-expert | DeepSeek-V4-Flash-0731 | 87 | expert | nvlink5 | infiniband_ndr | 172 | 382.16 us | 261.7 tok/s | 2,616.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.61 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.55 us |
| DSV4-Flash/b200_sxm-x87-nvl72-expert | DeepSeek-V4-Flash-0731 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.27 us | 260.2 tok/s | 2,602.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.55 us |
| DSV4-Flash/b200_sxm-x114-pipeline | DeepSeek-V4-Flash-0731 | 114 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x114-tensor | DeepSeek-V4-Flash-0731 | 114 | tensor | nvlink5 | infiniband_ndr | 172 | 597.07 us | 167.5 tok/s | 1,674.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 388.61 us |
| DSV4-Flash/b200_sxm-x114-hybrid | DeepSeek-V4-Flash-0731 | 114 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.17 us | 418.1 tok/s | 4,181.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| DSV4-Flash/b200_sxm-x114-nvl72-tensor | DeepSeek-V4-Flash-0731 | 114 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x114-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 114 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x114-expert | DeepSeek-V4-Flash-0731 | 114 | expert | nvlink5 | infiniband_ndr | 172 | 381.87 us | 261.9 tok/s | 2,618.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.55 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.32 us |
| DSV4-Flash/b200_sxm-x114-nvl72-expert | DeepSeek-V4-Flash-0731 | 114 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.04 us | 260.4 tok/s | 2,603.9 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.32 us |
| DSV4-Flash/b200_sxm-x116-pipeline | DeepSeek-V4-Flash-0731 | 116 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x116-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5 | infiniband_ndr | 172 | 597.07 us | 167.5 tok/s | 1,674.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 388.61 us |
| DSV4-Flash/b200_sxm-x116-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.17 us | 418.1 tok/s | 4,181.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| DSV4-Flash/b200_sxm-x116-nvl72-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x116-expert | DeepSeek-V4-Flash-0731 | 116 | expert | nvlink5 | infiniband_ndr | 172 | 381.86 us | 261.9 tok/s | 2,618.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.55 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.31 us |
| DSV4-Flash/b200_sxm-x116-nvl72-expert | DeepSeek-V4-Flash-0731 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.02 us | 260.4 tok/s | 2,604.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.31 us |
| DSV4-Flash/b200_sxm-x173-pipeline | DeepSeek-V4-Flash-0731 | 173 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x173-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5 | infiniband_ndr | 172 | 597.96 us | 167.2 tok/s | 1,672.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 389.51 us |
| DSV4-Flash/b200_sxm-x173-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5 | infiniband_ndr | 107 | 254.53 us | 392.9 tok/s | 3,928.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| DSV4-Flash/b200_sxm-x173-nvl72-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 586.06 us | 170.6 tok/s | 1,706.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 88 | 213.10 us | 469.3 tok/s | 4,692.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x173-expert | DeepSeek-V4-Flash-0731 | 173 | expert | nvlink5 | infiniband_ndr | 172 | 381.57 us | 262.1 tok/s | 2,620.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.50 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.07 us |
| DSV4-Flash/b200_sxm-x173-nvl72-expert | DeepSeek-V4-Flash-0731 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.63 us | 261.4 tok/s | 2,613.5 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.56 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.07 us |
| DSV4-Flash/b200_sxm-x202-pipeline | DeepSeek-V4-Flash-0731 | 202 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x202-tensor | DeepSeek-V4-Flash-0731 | 202 | tensor | nvlink5 | infiniband_ndr | 172 | 598.26 us | 167.2 tok/s | 1,671.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 26 on infiniband_ndr (traversals 2.0) = 389.80 us |
| DSV4-Flash/b200_sxm-x202-hybrid | DeepSeek-V4-Flash-0731 | 202 | hybrid | nvlink5 | infiniband_ndr | 111 | 263.30 us | 379.8 tok/s | 3,797.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 25 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 54.85 us |
| DSV4-Flash/b200_sxm-x202-nvl72-tensor | DeepSeek-V4-Flash-0731 | 202 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 586.06 us | 170.6 tok/s | 1,706.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x202-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 202 | hybrid | nvlink5_nvl72 | infiniband_ndr | 88 | 213.10 us | 469.3 tok/s | 4,692.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x202-expert | DeepSeek-V4-Flash-0731 | 202 | expert | nvlink5 | infiniband_ndr | 172 | 381.48 us | 262.1 tok/s | 2,621.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.48 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.00 us |
| DSV4-Flash/b200_sxm-x202-nvl72-expert | DeepSeek-V4-Flash-0731 | 202 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.56 us | 261.4 tok/s | 2,614.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.56 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.00 us |
| DSV4-Flash/b200_sxm-x231-pipeline | DeepSeek-V4-Flash-0731 | 231 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x231-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5 | infiniband_ndr | 172 | 598.43 us | 167.1 tok/s | 1,671.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 389.97 us |
| DSV4-Flash/b200_sxm-x231-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5 | infiniband_ndr | 114 | 269.88 us | 370.5 tok/s | 3,705.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| DSV4-Flash/b200_sxm-x231-nvl72-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 589.58 us | 169.6 tok/s | 1,696.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 89 | 215.30 us | 464.5 tok/s | 4,644.7 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x231-expert | DeepSeek-V4-Flash-0731 | 231 | expert | nvlink5 | infiniband_ndr | 172 | 381.42 us | 262.2 tok/s | 2,621.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.47 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.95 us |
| DSV4-Flash/b200_sxm-x231-nvl72-expert | DeepSeek-V4-Flash-0731 | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.12 us | 261.7 tok/s | 2,617.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.17 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.95 us |
| DSV4-Flash/b200_sxm-x347-pipeline | DeepSeek-V4-Flash-0731 | 347 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x347-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5 | infiniband_ndr | 172 | 598.92 us | 167.0 tok/s | 1,669.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 390.47 us |
| DSV4-Flash/b200_sxm-x347-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5 | infiniband_ndr | 128 | 300.60 us | 332.7 tok/s | 3,326.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 42 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 92.14 us |
| DSV4-Flash/b200_sxm-x347-nvl72-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 591.69 us | 169.0 tok/s | 1,690.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 382.98 us |
| DSV4-Flash/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 90 | 217.49 us | 459.8 tok/s | 4,597.9 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/b200_sxm-x347-expert | DeepSeek-V4-Flash-0731 | 347 | expert | nvlink5 | infiniband_ndr | 172 | 381.27 us | 262.3 tok/s | 2,622.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.82 us |
| DSV4-Flash/b200_sxm-x347-nvl72-expert | DeepSeek-V4-Flash-0731 | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 381.80 us | 261.9 tok/s | 2,619.2 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 206.98 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.82 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x342 | DeepSeek-V4-Pro-0813 | 342 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x182 | DeepSeek-V4-Pro-0813 | 182 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.32 us | 597.7 tok/s | 5,976.7 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 46 on rom_board_serdes (traversals 13.2) = 163.89 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x343 | DeepSeek-V4-Pro-0813 | 343 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x341 | DeepSeek-V4-Pro-0813 | 341 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x6 | DeepSeek-V4-Pro-0813 | 6 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x167 | DeepSeek-V4-Pro-0813 | 167 | tensor | nvlink5 | infiniband_ndr | 244 | 893.16 us | 112.0 tok/s | 1,119.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 595.26 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 262.35 us | 381.2 tok/s | 3,811.8 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 27.50 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x262 | DeepSeek-V4-Pro-0813 | 262 | hybrid | nvlink5 | infiniband_ndr | 154 | 372.04 us | 268.8 tok/s | 2,687.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 32 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 74.14 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer_n5 | rom_wafer_serdes | 126 | 235.26 us | 425.1 tok/s | 4,250.6 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.41 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399 | DeepSeek-V4-Pro-0813 | 399 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x399 | DeepSeek-V4-Pro-0813 | 399 | tensor | rom_package_ucie | rom_board_serdes | 244 | 247.87 us | 403.4 tok/s | 4,034.4 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 100 on rom_board_serdes (traversals 19.8) = 244.45 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | DeepSeek-V4-Pro-0813 | 399 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x399 | DeepSeek-V4-Pro-0813 | 399 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | DeepSeek-V4-Pro-0813 | 47 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x399 | DeepSeek-V4-Pro-0813 | 399 | tensor | nvlink5 | infiniband_ndr | 244 | 896.06 us | 111.6 tok/s | 1,116.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 50 on infiniband_ndr (traversals 2.0) = 598.16 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x47 | DeepSeek-V4-Pro-0813 | 47 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 396.75 us | 252.1 tok/s | 2,520.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 47 on rom_wafer_serdes (traversals 13.2) = 161.90 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x399 | DeepSeek-V4-Pro-0813 | 399 | hybrid | nvlink5 | infiniband_ndr | 171 | 411.42 us | 243.1 tok/s | 2,430.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 49 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 113.52 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | DeepSeek-V4-Pro-0813 | 47 | hybrid | on_wafer_n5 | rom_wafer_serdes | 168 | 239.56 us | 417.4 tok/s | 4,174.3 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 46 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 4.71 us |
| DSV4-Pro/b200_sxm-x29-pipeline | DeepSeek-V4-Pro-0813 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.35 us | 2,677.5 tok/s | 26,774.9 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.40 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5 | infiniband_ndr | 244 | 871.93 us | 114.7 tok/s | 1,146.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x29-hybrid | DeepSeek-V4-Pro-0813 | 29 | hybrid | nvlink5 | infiniband_ndr | 125 | 304.85 us | 328.0 tok/s | 3,280.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-nvl72-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.43 us | 335.1 tok/s | 3,350.9 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us |
| DSV4-Pro/b200_sxm-x29-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5 | infiniband_ndr | 244 | 549.40 us | 182.0 tok/s | 1,820.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 294.50 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 254.90 us |
| DSV4-Pro/b200_sxm-x29-nvl72-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.23 us | 224.6 tok/s | 2,246.0 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.80 us |
| DSV4-Pro/b200_sxm-x40-pipeline | DeepSeek-V4-Pro-0813 | 40 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.82 us | 1,929.6 tok/s | 19,295.9 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.56 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x40-tensor | DeepSeek-V4-Pro-0813 | 40 | tensor | nvlink5 | infiniband_ndr | 244 | 877.17 us | 114.0 tok/s | 1,140.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x40-hybrid | DeepSeek-V4-Pro-0813 | 40 | hybrid | nvlink5 | infiniband_ndr | 126 | 307.17 us | 325.6 tok/s | 3,255.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x40-nvl72-tensor | DeepSeek-V4-Pro-0813 | 40 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.48 us | 335.0 tok/s | 3,350.3 tok/s | 122 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 298.48 us |
| DSV4-Pro/b200_sxm-x40-expert | DeepSeek-V4-Pro-0813 | 40 | expert | nvlink5 | infiniband_ndr | 244 | 546.73 us | 182.9 tok/s | 1,829.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.91 us |
| DSV4-Pro/b200_sxm-x40-nvl72-expert | DeepSeek-V4-Pro-0813 | 40 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.18 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 298.48 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.69 us |
| DSV4-Pro/b200_sxm-x44-pipeline | DeepSeek-V4-Pro-0813 | 44 | pipeline | nvlink5 | infiniband_ndr | 43 | 57.79 us | 1,730.4 tok/s | 17,304.4 tok/s | 38 x point_to_point span 2 on nvlink5 (traversals 1.0) = 46.21 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x44-tensor | DeepSeek-V4-Pro-0813 | 44 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x44-hybrid | DeepSeek-V4-Pro-0813 | 44 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x44-nvl72-tensor | DeepSeek-V4-Pro-0813 | 44 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.50 us | 335.0 tok/s | 3,350.1 tok/s | 122 x all_reduce span 44 on nvlink5_nvl72 (traversals 2.0) = 298.50 us |
| DSV4-Pro/b200_sxm-x44-expert | DeepSeek-V4-Pro-0813 | 44 | expert | nvlink5 | infiniband_ndr | 244 | 546.25 us | 183.1 tok/s | 1,830.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.43 us |
| DSV4-Pro/b200_sxm-x44-nvl72-expert | DeepSeek-V4-Pro-0813 | 44 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.16 us | 224.6 tok/s | 2,246.4 tok/s | 122 x all_reduce span 44 on nvlink5_nvl72 (traversals 2.0) = 298.50 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.66 us |
| DSV4-Pro/b200_sxm-x46-pipeline | DeepSeek-V4-Pro-0813 | 46 | pipeline | nvlink5 | infiniband_ndr | 45 | 60.22 us | 1,660.6 tok/s | 16,605.6 tok/s | 40 x point_to_point span 2 on nvlink5 (traversals 1.0) = 48.64 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x46-tensor | DeepSeek-V4-Pro-0813 | 46 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x46-hybrid | DeepSeek-V4-Pro-0813 | 46 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x46-nvl72-tensor | DeepSeek-V4-Pro-0813 | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.50 us | 335.0 tok/s | 3,350.0 tok/s | 122 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 298.50 us |
| DSV4-Pro/b200_sxm-x46-expert | DeepSeek-V4-Pro-0813 | 46 | expert | nvlink5 | infiniband_ndr | 244 | 546.04 us | 183.1 tok/s | 1,831.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.22 us |
| DSV4-Pro/b200_sxm-x46-nvl72-expert | DeepSeek-V4-Pro-0813 | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.16 us | 224.6 tok/s | 2,246.4 tok/s | 122 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 298.50 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.65 us |
| DSV4-Pro/b200_sxm-x58-pipeline | DeepSeek-V4-Pro-0813 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 77.01 us | 1,298.5 tok/s | 12,984.7 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5 | infiniband_ndr | 244 | 885.04 us | 113.0 tok/s | 1,129.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 587.14 us |
| DSV4-Pro/b200_sxm-x58-hybrid | DeepSeek-V4-Pro-0813 | 58 | hybrid | nvlink5 | infiniband_ndr | 129 | 314.12 us | 318.4 tok/s | 3,183.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-nvl72-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.53 us | 335.0 tok/s | 3,349.8 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us |
| DSV4-Pro/b200_sxm-x58-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5 | infiniband_ndr | 244 | 544.81 us | 183.6 tok/s | 1,835.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.53 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 251.28 us |
| DSV4-Pro/b200_sxm-x58-nvl72-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.13 us | 224.7 tok/s | 2,246.5 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.60 us |
| DSV4-Pro/b200_sxm-x63-pipeline | DeepSeek-V4-Pro-0813 | 63 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x63-tensor | DeepSeek-V4-Pro-0813 | 63 | tensor | nvlink5 | infiniband_ndr | 244 | 885.04 us | 113.0 tok/s | 1,129.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 587.14 us |
| DSV4-Pro/b200_sxm-x63-hybrid | DeepSeek-V4-Pro-0813 | 63 | hybrid | nvlink5 | infiniband_ndr | 129 | 314.12 us | 318.4 tok/s | 3,183.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x63-nvl72-tensor | DeepSeek-V4-Pro-0813 | 63 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.54 us | 335.0 tok/s | 3,349.7 tok/s | 122 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 298.54 us |
| DSV4-Pro/b200_sxm-x63-expert | DeepSeek-V4-Pro-0813 | 63 | expert | nvlink5 | infiniband_ndr | 244 | 544.52 us | 183.6 tok/s | 1,836.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.53 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.99 us |
| DSV4-Pro/b200_sxm-x63-nvl72-expert | DeepSeek-V4-Pro-0813 | 63 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.12 us | 224.7 tok/s | 2,246.6 tok/s | 122 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 298.54 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.59 us |
| DSV4-Pro/b200_sxm-x70-pipeline | DeepSeek-V4-Pro-0813 | 70 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x70-tensor | DeepSeek-V4-Pro-0813 | 70 | tensor | nvlink5 | infiniband_ndr | 244 | 886.50 us | 112.8 tok/s | 1,128.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 588.60 us |
| DSV4-Pro/b200_sxm-x70-hybrid | DeepSeek-V4-Pro-0813 | 70 | hybrid | nvlink5 | infiniband_ndr | 130 | 316.43 us | 316.0 tok/s | 3,160.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| DSV4-Pro/b200_sxm-x70-nvl72-tensor | DeepSeek-V4-Pro-0813 | 70 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.55 us | 335.0 tok/s | 3,349.6 tok/s | 122 x all_reduce span 70 on nvlink5_nvl72 (traversals 2.0) = 298.55 us |
| DSV4-Pro/b200_sxm-x70-expert | DeepSeek-V4-Pro-0813 | 70 | expert | nvlink5 | infiniband_ndr | 244 | 544.10 us | 183.8 tok/s | 1,837.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.44 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.66 us |
| DSV4-Pro/b200_sxm-x70-nvl72-expert | DeepSeek-V4-Pro-0813 | 70 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.11 us | 224.7 tok/s | 2,246.6 tok/s | 122 x all_reduce span 70 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.57 us |
| DSV4-Pro/b200_sxm-x71-pipeline | DeepSeek-V4-Pro-0813 | 71 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x71-tensor | DeepSeek-V4-Pro-0813 | 71 | tensor | nvlink5 | infiniband_ndr | 244 | 886.50 us | 112.8 tok/s | 1,128.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 588.60 us |
| DSV4-Pro/b200_sxm-x71-hybrid | DeepSeek-V4-Pro-0813 | 71 | hybrid | nvlink5 | infiniband_ndr | 130 | 316.43 us | 316.0 tok/s | 3,160.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| DSV4-Pro/b200_sxm-x71-nvl72-tensor | DeepSeek-V4-Pro-0813 | 71 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.55 us | 335.0 tok/s | 3,349.5 tok/s | 122 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 298.55 us |
| DSV4-Pro/b200_sxm-x71-expert | DeepSeek-V4-Pro-0813 | 71 | expert | nvlink5 | infiniband_ndr | 244 | 544.05 us | 183.8 tok/s | 1,838.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.44 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.62 us |
| DSV4-Pro/b200_sxm-x71-nvl72-expert | DeepSeek-V4-Pro-0813 | 71 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.11 us | 224.7 tok/s | 2,246.6 tok/s | 122 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.56 us |
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
| DSV4-Pro/b200_sxm-x93-pipeline | DeepSeek-V4-Pro-0813 | 93 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x93-tensor | DeepSeek-V4-Pro-0813 | 93 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x93-hybrid | DeepSeek-V4-Pro-0813 | 93 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x93-nvl72-tensor | DeepSeek-V4-Pro-0813 | 93 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x93-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 93 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x93-expert | DeepSeek-V4-Pro-0813 | 93 | expert | nvlink5 | infiniband_ndr | 244 | 543.18 us | 184.1 tok/s | 1,841.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.26 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.92 us |
| DSV4-Pro/b200_sxm-x93-nvl72-expert | DeepSeek-V4-Pro-0813 | 93 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.47 us | 182.3 tok/s | 1,823.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.92 us |
| DSV4-Pro/b200_sxm-x94-pipeline | DeepSeek-V4-Pro-0813 | 94 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x94-tensor | DeepSeek-V4-Pro-0813 | 94 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x94-hybrid | DeepSeek-V4-Pro-0813 | 94 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x94-nvl72-tensor | DeepSeek-V4-Pro-0813 | 94 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x94-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 94 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x94-expert | DeepSeek-V4-Pro-0813 | 94 | expert | nvlink5 | infiniband_ndr | 244 | 543.16 us | 184.1 tok/s | 1,841.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.26 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.89 us |
| DSV4-Pro/b200_sxm-x94-nvl72-expert | DeepSeek-V4-Pro-0813 | 94 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.44 us | 182.3 tok/s | 1,823.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.89 us |
| DSV4-Pro/b200_sxm-x113-pipeline | DeepSeek-V4-Pro-0813 | 113 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x113-tensor | DeepSeek-V4-Pro-0813 | 113 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x113-hybrid | DeepSeek-V4-Pro-0813 | 113 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x113-nvl72-tensor | DeepSeek-V4-Pro-0813 | 113 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x113-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 113 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x113-expert | DeepSeek-V4-Pro-0813 | 113 | expert | nvlink5 | infiniband_ndr | 244 | 542.68 us | 184.3 tok/s | 1,842.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.52 us |
| DSV4-Pro/b200_sxm-x113-nvl72-expert | DeepSeek-V4-Pro-0813 | 113 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.07 us | 182.5 tok/s | 1,824.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.52 us |
| DSV4-Pro/b200_sxm-x116-pipeline | DeepSeek-V4-Pro-0813 | 116 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x116-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x116-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x116-nvl72-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x116-expert | DeepSeek-V4-Pro-0813 | 116 | expert | nvlink5 | infiniband_ndr | 244 | 542.63 us | 184.3 tok/s | 1,842.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.47 us |
| DSV4-Pro/b200_sxm-x116-nvl72-expert | DeepSeek-V4-Pro-0813 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.02 us | 182.5 tok/s | 1,824.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.47 us |
| DSV4-Pro/b200_sxm-x121-pipeline | DeepSeek-V4-Pro-0813 | 121 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x121-tensor | DeepSeek-V4-Pro-0813 | 121 | tensor | nvlink5 | infiniband_ndr | 244 | 891.60 us | 112.2 tok/s | 1,121.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 593.70 us |
| DSV4-Pro/b200_sxm-x121-hybrid | DeepSeek-V4-Pro-0813 | 121 | hybrid | nvlink5 | infiniband_ndr | 137 | 332.65 us | 300.6 tok/s | 3,006.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 34.75 us |
| DSV4-Pro/b200_sxm-x121-nvl72-tensor | DeepSeek-V4-Pro-0813 | 121 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x121-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 121 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x121-expert | DeepSeek-V4-Pro-0813 | 121 | expert | nvlink5 | infiniband_ndr | 244 | 542.53 us | 184.3 tok/s | 1,843.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.14 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.39 us |
| DSV4-Pro/b200_sxm-x121-nvl72-expert | DeepSeek-V4-Pro-0813 | 121 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.94 us | 182.5 tok/s | 1,825.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.39 us |
| DSV4-Pro/b200_sxm-x126-pipeline | DeepSeek-V4-Pro-0813 | 126 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x126-tensor | DeepSeek-V4-Pro-0813 | 126 | tensor | nvlink5 | infiniband_ndr | 244 | 891.60 us | 112.2 tok/s | 1,121.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 593.70 us |
| DSV4-Pro/b200_sxm-x126-hybrid | DeepSeek-V4-Pro-0813 | 126 | hybrid | nvlink5 | infiniband_ndr | 137 | 332.65 us | 300.6 tok/s | 3,006.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 34.75 us |
| DSV4-Pro/b200_sxm-x126-nvl72-tensor | DeepSeek-V4-Pro-0813 | 126 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x126-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 126 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x126-expert | DeepSeek-V4-Pro-0813 | 126 | expert | nvlink5 | infiniband_ndr | 244 | 542.47 us | 184.3 tok/s | 1,843.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.14 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.33 us |
| DSV4-Pro/b200_sxm-x126-nvl72-expert | DeepSeek-V4-Pro-0813 | 126 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.87 us | 182.5 tok/s | 1,825.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.33 us |
| DSV4-Pro/b200_sxm-x133-pipeline | DeepSeek-V4-Pro-0813 | 133 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x133-tensor | DeepSeek-V4-Pro-0813 | 133 | tensor | nvlink5 | infiniband_ndr | 244 | 891.99 us | 112.1 tok/s | 1,121.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 594.09 us |
| DSV4-Pro/b200_sxm-x133-hybrid | DeepSeek-V4-Pro-0813 | 133 | hybrid | nvlink5 | infiniband_ndr | 138 | 334.97 us | 298.5 tok/s | 2,985.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.07 us |
| DSV4-Pro/b200_sxm-x133-nvl72-tensor | DeepSeek-V4-Pro-0813 | 133 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x133-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 133 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x133-expert | DeepSeek-V4-Pro-0813 | 133 | expert | nvlink5 | infiniband_ndr | 244 | 542.36 us | 184.4 tok/s | 1,843.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.12 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.24 us |
| DSV4-Pro/b200_sxm-x133-nvl72-expert | DeepSeek-V4-Pro-0813 | 133 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.79 us | 182.6 tok/s | 1,825.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.24 us |
| DSV4-Pro/b200_sxm-x144-pipeline | DeepSeek-V4-Pro-0813 | 144 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x144-tensor | DeepSeek-V4-Pro-0813 | 144 | tensor | nvlink5 | infiniband_ndr | 244 | 892.33 us | 112.1 tok/s | 1,120.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 594.43 us |
| DSV4-Pro/b200_sxm-x144-hybrid | DeepSeek-V4-Pro-0813 | 144 | hybrid | nvlink5 | infiniband_ndr | 139 | 337.29 us | 296.5 tok/s | 2,964.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 39.38 us |
| DSV4-Pro/b200_sxm-x144-nvl72-tensor | DeepSeek-V4-Pro-0813 | 144 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x144-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 144 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x144-expert | DeepSeek-V4-Pro-0813 | 144 | expert | nvlink5 | infiniband_ndr | 244 | 542.20 us | 184.4 tok/s | 1,844.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.12 us |
| DSV4-Pro/b200_sxm-x144-nvl72-expert | DeepSeek-V4-Pro-0813 | 144 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.79 us | 183.6 tok/s | 1,835.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.12 us |
| DSV4-Pro/b200_sxm-x150-pipeline | DeepSeek-V4-Pro-0813 | 150 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x150-tensor | DeepSeek-V4-Pro-0813 | 150 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x150-hybrid | DeepSeek-V4-Pro-0813 | 150 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x150-nvl72-tensor | DeepSeek-V4-Pro-0813 | 150 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x150-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 150 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x150-expert | DeepSeek-V4-Pro-0813 | 150 | expert | nvlink5 | infiniband_ndr | 244 | 542.14 us | 184.5 tok/s | 1,844.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.06 us |
| DSV4-Pro/b200_sxm-x150-nvl72-expert | DeepSeek-V4-Pro-0813 | 150 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.73 us | 183.6 tok/s | 1,835.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.06 us |
| DSV4-Pro/b200_sxm-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x173-nvl72-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x173-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5 | infiniband_ndr | 244 | 541.92 us | 184.5 tok/s | 1,845.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.04 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x173-nvl72-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.55 us | 183.6 tok/s | 1,836.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x174-pipeline | DeepSeek-V4-Pro-0813 | 174 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x174-tensor | DeepSeek-V4-Pro-0813 | 174 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x174-hybrid | DeepSeek-V4-Pro-0813 | 174 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x174-nvl72-tensor | DeepSeek-V4-Pro-0813 | 174 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x174-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 174 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x174-expert | DeepSeek-V4-Pro-0813 | 174 | expert | nvlink5 | infiniband_ndr | 244 | 541.91 us | 184.5 tok/s | 1,845.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.04 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x174-nvl72-expert | DeepSeek-V4-Pro-0813 | 174 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.54 us | 183.6 tok/s | 1,836.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x175-pipeline | DeepSeek-V4-Pro-0813 | 175 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x175-tensor | DeepSeek-V4-Pro-0813 | 175 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x175-hybrid | DeepSeek-V4-Pro-0813 | 175 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x175-nvl72-tensor | DeepSeek-V4-Pro-0813 | 175 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x175-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 175 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x175-expert | DeepSeek-V4-Pro-0813 | 175 | expert | nvlink5 | infiniband_ndr | 244 | 541.90 us | 184.5 tok/s | 1,845.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.04 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.86 us |
| DSV4-Pro/b200_sxm-x175-nvl72-expert | DeepSeek-V4-Pro-0813 | 175 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.53 us | 183.6 tok/s | 1,836.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.86 us |
| DSV4-Pro/b200_sxm-x203-pipeline | DeepSeek-V4-Pro-0813 | 203 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x203-tensor | DeepSeek-V4-Pro-0813 | 203 | tensor | nvlink5 | infiniband_ndr | 244 | 894.12 us | 111.8 tok/s | 1,118.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 26 on infiniband_ndr (traversals 2.0) = 596.22 us |
| DSV4-Pro/b200_sxm-x203-hybrid | DeepSeek-V4-Pro-0813 | 203 | hybrid | nvlink5 | infiniband_ndr | 147 | 355.82 us | 281.0 tok/s | 2,810.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 25 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 57.92 us |
| DSV4-Pro/b200_sxm-x203-nvl72-tensor | DeepSeek-V4-Pro-0813 | 203 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x203-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 203 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x203-expert | DeepSeek-V4-Pro-0813 | 203 | expert | nvlink5 | infiniband_ndr | 244 | 541.70 us | 184.6 tok/s | 1,846.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.00 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.69 us |
| DSV4-Pro/b200_sxm-x203-nvl72-expert | DeepSeek-V4-Pro-0813 | 203 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.37 us | 183.7 tok/s | 1,837.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.69 us |
| DSV4-Pro/b200_sxm-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5 | infiniband_ndr | 244 | 894.54 us | 111.8 tok/s | 1,117.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 596.64 us |
| DSV4-Pro/b200_sxm-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5 | infiniband_ndr | 150 | 362.77 us | 275.7 tok/s | 2,756.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 64.87 us |
| DSV4-Pro/b200_sxm-x231-nvl72-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 872.57 us | 114.6 tok/s | 1,146.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 125 | 305.50 us | 327.3 tok/s | 3,273.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x231-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5 | infiniband_ndr | 244 | 541.55 us | 184.7 tok/s | 1,846.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.98 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x231-nvl72-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 543.28 us | 184.1 tok/s | 1,840.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.72 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x255-pipeline | DeepSeek-V4-Pro-0813 | 255 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x255-tensor | DeepSeek-V4-Pro-0813 | 255 | tensor | nvlink5 | infiniband_ndr | 244 | 894.88 us | 111.7 tok/s | 1,117.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 32 on infiniband_ndr (traversals 2.0) = 596.98 us |
| DSV4-Pro/b200_sxm-x255-hybrid | DeepSeek-V4-Pro-0813 | 255 | hybrid | nvlink5 | infiniband_ndr | 153 | 369.72 us | 270.5 tok/s | 2,704.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 31 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 71.82 us |
| DSV4-Pro/b200_sxm-x255-nvl72-tensor | DeepSeek-V4-Pro-0813 | 255 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 872.57 us | 114.6 tok/s | 1,146.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x255-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 255 | hybrid | nvlink5_nvl72 | infiniband_ndr | 125 | 305.50 us | 327.3 tok/s | 3,273.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x255-expert | DeepSeek-V4-Pro-0813 | 255 | expert | nvlink5 | infiniband_ndr | 244 | 541.45 us | 184.7 tok/s | 1,846.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.96 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.48 us |
| DSV4-Pro/b200_sxm-x255-nvl72-expert | DeepSeek-V4-Pro-0813 | 255 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 543.20 us | 184.1 tok/s | 1,840.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.72 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.48 us |
| DSV4-Pro/b200_sxm-x347-pipeline | DeepSeek-V4-Pro-0813 | 347 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x347-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5 | infiniband_ndr | 244 | 895.78 us | 111.6 tok/s | 1,116.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 597.87 us |
| DSV4-Pro/b200_sxm-x347-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5 | infiniband_ndr | 165 | 397.52 us | 251.6 tok/s | 2,515.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 99.62 us |
| DSV4-Pro/b200_sxm-x347-nvl72-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 877.82 us | 113.9 tok/s | 1,139.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 126 | 307.82 us | 324.9 tok/s | 3,248.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x347-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5 | infiniband_ndr | 244 | 541.18 us | 184.8 tok/s | 1,847.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.92 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |
| DSV4-Pro/b200_sxm-x347-nvl72-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 542.50 us | 184.3 tok/s | 1,843.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.24 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |
| DSV4-Pro/b200_sxm-x1358-pipeline | DeepSeek-V4-Pro-0813 | 1358 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x1358-tensor | DeepSeek-V4-Pro-0813 | 1358 | tensor | nvlink5 | infiniband_ndr | 244 | 1,392.86 us | 71.8 tok/s | 717.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 170 on infiniband_ndr (traversals 4.0) = 1,094.96 us |
| DSV4-Pro/b200_sxm-x1358-hybrid | DeepSeek-V4-Pro-0813 | 1358 | hybrid | nvlink5 | infiniband_ndr | 182 | 436.90 us | 228.9 tok/s | 2,288.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 60 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 139.00 us |
| DSV4-Pro/b200_sxm-x1358-nvl72-tensor | DeepSeek-V4-Pro-0813 | 1358 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 893.29 us | 111.9 tok/s | 1,119.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x1358-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 1358 | hybrid | nvlink5_nvl72 | infiniband_ndr | 140 | 340.25 us | 293.9 tok/s | 2,939.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x1358-expert | DeepSeek-V4-Pro-0813 | 1358 | expert | nvlink5 | infiniband_ndr | 244 | 540.64 us | 185.0 tok/s | 1,849.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.83 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 247.81 us |
| DSV4-Pro/b200_sxm-x1358-nvl72-expert | DeepSeek-V4-Pro-0813 | 1358 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 540.93 us | 184.9 tok/s | 1,848.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 293.12 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 247.81 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | array | array | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x15-romfill | 12,225 | 27,653.4 | 2.262 | 27,653.4 (12,225) | 6,464.4 (46,225) | 0.23x | link_latency |
| Qwen3-8B | 2 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49-romfill | 39,935 | 14,198.0 | 0.356 | 14,198.0 (39,935) | 5,536.7 (277,350) | 0.39x | link_latency |
| Qwen3-8B | 4 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x51-romfill | 41,565 | 11,886.2 | 0.286 | 11,886.2 (41,565) | 5,536.7 (277,350) | 0.47x | link_latency |
| Qwen3-8B | 8 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x51-romfill | 41,565 | 9,192.7 | 0.221 | 9,192.7 (41,565) | 5,530.5 (369,800) | 0.60x | thermal |
| Qwen3-8B | 16 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill | 50,530 | 9,080.1 | 0.180 | 9,080.1 (50,530) | 5,187.1 (554,700) | 0.57x | thermal |
| Qwen3-8B | 32 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x147-romfill | 119,805 | 9,309.6 | 0.078 | 9,309.6 (119,805) | 4,183.1 (554,700) | 0.45x | thermal |
| Qwen3-8B | 64 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 9,373.0 | 0.034 | 9,373.0 (277,100) | 3,015.8 (554,700) | 0.32x | thermal |
| Qwen3-8B | 256 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,185.2 | 0.011 | 3,185.2 (277,100) | 1,127.6 (554,700) | 0.35x | thermal |
| Qwen3-8B | 1024 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 803.3 | 0.003 | 803.3 (277,100) | 336.6 (554,700) | 0.42x | thermal |
| Qwen3-8B | 4096 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 201.3 | 0.001 | 201.3 (277,100) | 84.4 (554,700) | 0.42x | thermal |
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56 | 45,640 | 17,768.6 | 0.389 | 17,768.6 (45,640) | 6,168.1 (46,225) | 0.35x | compute |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x62 | 50,530 | 16,831.4 | 0.333 | 16,831.4 (50,530) | 5,328.6 (323,575) | 0.32x | compute |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x62 | 50,530 | 16,831.4 | 0.333 | 16,831.4 (50,530) | 5,328.6 (323,575) | 0.32x | compute |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x62 | 50,530 | 16,831.4 | 0.333 | 16,831.4 (50,530) | 5,291.8 (323,575) | 0.31x | compute |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x62 | 50,530 | 16,831.4 | 0.333 | 16,831.4 (50,530) | 5,015.1 (323,575) | 0.30x | compute |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill | 136,920 | 13,849.4 | 0.101 | 13,849.4 (136,920) | 4,916.6 (554,700) | 0.36x | compute |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 13,829.4 | 0.050 | 13,829.4 (277,100) | 4,390.9 (554,700) | 0.32x | compute |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 5,526.7 | 0.020 | 5,526.7 (277,100) | 2,675.0 (554,700) | 0.48x | compute |
| DeepSeek-V4-Flash-0731 | 1024 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,521.0 | 0.005 | 1,521.0 (277,100) | 1,257.0 (554,700) | 0.83x | compute |
| DeepSeek-V4-Flash-0731 | 4096 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 464.4 | 0.002 | 464.4 (277,100) | 319.6 (554,700) | 0.69x | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | array | array | DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x167 | 136,105 | 4,813.6 | 0.035 | 4,813.6 (136,105) | 3,619.5 (184,900) | 0.75x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 0.013 | 4,226.3 (325,185) | 3,119.7 (2,172,575) | 0.74x | compute |
| DeepSeek-V4-Pro-0813 | 4 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 0.013 | 4,226.3 (325,185) | 3,119.7 (2,172,575) | 0.74x | compute |
| DeepSeek-V4-Pro-0813 | 8 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 0.013 | 4,226.3 (325,185) | 3,119.7 (2,172,575) | 0.74x | compute |
| DeepSeek-V4-Pro-0813 | 16 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 0.013 | 4,226.3 (325,185) | 3,119.7 (2,172,575) | 0.74x | compute |
| DeepSeek-V4-Pro-0813 | 32 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 0.013 | 4,226.3 (325,185) | 3,119.7 (2,172,575) | 0.74x | compute |
| DeepSeek-V4-Pro-0813 | 64 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 4,226.3 | 0.013 | 4,226.3 (325,185) | 2,911.1 (2,172,575) | 0.69x | compute |
| DeepSeek-V4-Pro-0813 | 256 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,769.6 | 0.005 | 1,769.6 (325,185) | 1,658.7 (2,172,575) | 0.94x | compute |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | 2,172,575 | 609.6 | 0.000 | 462.6 (325,185) | 609.6 (2,172,575) | 1.32x | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 180.2 | 0.000 | 116.5 (325,185) | 180.2 (2,172,575) | 1.55x | kv_read |

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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 98.1 mm2 | 17.65 mm2 (18.0%) | 25,105 mm2 | 4,519 mm2 | 28,467 mm2 = 34.9 reticles |
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
| Qwen3-8B | 1 | sram | 28,247.2 | 28,850.2 | 28,850.2 | 0.98x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 28,247.2 | 28,850.2 | 28,850.2 | 0.98x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 41,614.3 | 28,850.2 | 28,850.2 | 1.44x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 76,704.9 | 28,850.2 | 28,850.2 | 2.66x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 113,694.2 | 28,850.2 | 28,850.2 | 3.94x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 165,432.3 | 28,850.2 | 28,850.2 | 5.73x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 225,696.6 | 28,868.1 | 28,868.1 | 7.82x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 361,045.5 | 26,090.9 | 26,090.9 | 13.84x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 1024 | sram | 525,192.7 | 26,106.6 | 26,106.6 | 20.12x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4096 | sram | 710,678.0 | 26,111.3 | 26,111.3 | 27.22x | 1.00x | thermal | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 796,701.8 | 172,004.7 | 172,004.7 | 4.63x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 796,701.8 | 172,004.7 | 172,004.7 | 4.63x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 796,701.8 | 172,004.7 | 172,004.7 | 4.63x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 796,701.8 | 172,004.7 | 172,004.7 | 4.63x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 796,701.8 | 172,004.7 | 172,004.7 | 4.63x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 796,701.8 | 172,004.7 | 172,004.7 | 4.63x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 796,701.8 | 172,004.7 | 172,004.7 | 4.63x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 815,402.0 | 172,004.7 | 172,004.7 | 4.74x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 1024 | rom | 822,600.1 | 172,654.9 | 172,654.9 | 4.76x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 4096 | rom | 824,720.0 | 172,899.6 | 172,899.6 | 4.77x | 1.00x | thermal | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 384,602.4 | 28,756.4 | 28,756.4 | 13.37x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 384,602.4 | 28,756.4 | 28,756.4 | 13.37x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 384,602.4 | 28,756.4 | 29,192.8 | 13.37x | 1.02x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | sram | 384,602.4 | 28,756.4 | 48,641.5 | 13.37x | 1.69x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 384,602.4 | 28,756.4 | 78,019.8 | 13.37x | 2.71x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 402,698.1 | 28,756.4 | 117,378.8 | 14.00x | 4.08x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 543,246.5 | 26,083.0 | 164,390.9 | 20.83x | 6.30x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 890,278.0 | 26,083.0 | 310,960.0 | 34.13x | 11.92x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 1,350,160.7 | 26,102.7 | 509,754.4 | 51.72x | 19.53x | thermal | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 1,902,183.6 | 26,110.2 | 603,512.6 | 72.85x | 23.11x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 1,494,752.7 | 724,758.4 | 724,758.4 | 2.06x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 1,494,752.7 | 724,758.4 | 724,758.4 | 2.06x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 1,494,752.7 | 724,758.4 | 724,758.4 | 2.06x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 1,494,752.7 | 724,758.4 | 724,758.4 | 2.06x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 1,494,752.7 | 724,758.4 | 724,758.4 | 2.06x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 1,494,752.7 | 724,758.4 | 724,758.4 | 2.06x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 1,494,752.7 | 724,758.4 | 724,758.4 | 2.06x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 1,494,752.7 | 724,758.4 | 724,758.4 | 2.06x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 1,557,470.8 | 739,278.2 | 757,861.2 | 2.11x | 1.03x | compute | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 1,582,220.8 | 746,408.6 | 765,356.4 | 2.12x | 1.03x | compute | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 584,464.8 | 26,106.7 | 26,106.7 | 22.39x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 584,464.8 | 26,106.7 | 26,106.7 | 22.39x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 584,464.8 | 26,106.7 | 26,106.7 | 22.39x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 584,464.8 | 26,106.7 | 26,106.7 | 22.39x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 584,464.8 | 26,106.7 | 38,015.4 | 22.39x | 1.46x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | sram | 584,464.8 | 26,106.7 | 61,655.0 | 22.39x | 2.36x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | sram | 584,464.8 | 26,106.7 | 97,446.7 | 22.39x | 3.73x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 256 | sram | 584,464.8 | 26,106.7 | 243,217.4 | 22.39x | 9.32x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 624,260.6 | 26,106.7 | 383,375.5 | 23.91x | 14.68x | kv_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 738,201.0 | 26,109.4 | 433,735.2 | 28.27x | 16.61x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 736,415.4 | 736,415.4 | 736,415.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 736,415.4 | 736,415.4 | 736,415.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 736,415.4 | 736,415.4 | 736,415.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 736,415.4 | 736,415.4 | 736,415.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 736,415.4 | 736,415.4 | 736,415.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 736,415.4 | 736,415.4 | 736,415.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 736,415.4 | 736,415.4 | 736,415.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 736,415.4 | 736,415.4 | 736,415.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 736,415.4 | 736,415.4 | 736,415.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 738,201.0 | 738,201.0 | 738,201.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,247.2 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 28.20x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.02x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 6.09x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.02x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 6.09x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,247.2 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 28.20x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.02x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 6.09x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.02x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 6.09x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49 | 39,935 | 1.00 | 1.00 | 41,614.3 | 1.042 | link_latency | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 19.14x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.69x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 4.13x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.69x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 4.13x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x62 | 50,530 | 1.00 | 1.00 | 76,704.9 | 1.518 | link_latency | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 10.39x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.38x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 2.24x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.38x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 2.24x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x98 | 79,870 | 1.00 | 1.00 | 113,694.2 | 1.423 | link_latency | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 7.01x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.25x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 1.51x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.25x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 1.51x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x196 | 159,740 | 1.00 | 1.00 | 165,432.3 | 1.036 | link_latency | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 4.82x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.17x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 1.04x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.17x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 1.04x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x196 | 159,740 | 1.00 | 1.00 | 225,696.6 | 1.413 | link_latency | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 3.53x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,868.1 | 0.625 | weight_read | 0.13x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 0.76x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 28,868.1 | 0.625 | weight_read | 0.13x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 0.76x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x340 | 277,100 | 1.00 | 1.00 | 361,045.5 | 1.303 | link_latency | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 69.67 | 1.00 | 815,402.0 | 2.943 | thermal | 2.26x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x49-perstream | 39,935 | 1.00 | 5.22 | 26,090.9 | 0.653 | weight_read | 0.07x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 0.48x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x49-perregion | 39,935 | 1.00 | 5.22 | 26,090.9 | 0.653 | weight_read | 0.07x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 172,004.7 | 0.620 | kv_read | 0.48x |
| Qwen3-8B | 1024 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340 | 277,100 | 1.00 | 1.00 | 525,192.7 | 1.895 | weight_read | 1.00x |
| Qwen3-8B | 1024 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 69.67 | 1.00 | 822,600.1 | 2.969 | thermal | 1.57x |
| Qwen3-8B | 1024 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x49-perstream | 39,935 | 1.00 | 20.90 | 26,106.6 | 0.654 | weight_read | 0.05x |
| Qwen3-8B | 1024 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 3.00 | 172,654.9 | 0.623 | kv_read | 0.33x |
| Qwen3-8B | 1024 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x49-perregion | 39,935 | 1.00 | 20.90 | 26,106.6 | 0.654 | weight_read | 0.05x |
| Qwen3-8B | 1024 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 3.00 | 172,654.9 | 0.623 | kv_read | 0.33x |
| Qwen3-8B | 4096 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340 | 277,100 | 1.00 | 1.00 | 710,678.0 | 2.565 | thermal | 1.00x |
| Qwen3-8B | 4096 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 69.67 | 1.00 | 824,720.0 | 2.976 | thermal | 1.16x |
| Qwen3-8B | 4096 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 12.01 | 26,111.3 | 0.094 | weight_read | 0.04x |
| Qwen3-8B | 4096 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 12.01 | 172,899.6 | 0.623 | kv_read | 0.24x |
| Qwen3-8B | 4096 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 12.01 | 26,111.3 | 0.094 | weight_read | 0.04x |
| Qwen3-8B | 4096 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 12.01 | 172,899.6 | 0.623 | kv_read | 0.24x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,494,752.7 | 5.394 | compute | 3.89x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,494,752.7 | 5.394 | compute | 3.89x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,494,752.7 | 5.394 | compute | 3.89x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x56-perregion | 45,640 | 1.00 | 1.57 | 29,192.8 | 0.640 | link_latency | 0.08x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,494,752.7 | 5.394 | compute | 3.89x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x56-perregion | 45,640 | 1.00 | 2.13 | 48,641.5 | 1.066 | weight_read | 0.13x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,494,752.7 | 5.394 | compute | 3.89x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x56-perregion | 45,640 | 1.00 | 2.88 | 78,019.8 | 1.709 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.88x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x84 | 68,460 | 1.00 | 1.00 | 402,698.1 | 5.882 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,494,752.7 | 5.394 | compute | 3.71x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.80x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x56-perregion | 45,640 | 1.00 | 4.03 | 117,378.8 | 2.572 | weight_read | 0.29x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.80x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x112 | 91,280 | 1.00 | 1.00 | 543,246.5 | 5.951 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,494,752.7 | 5.394 | compute | 2.75x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,083.0 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.33x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x56-perregion | 45,640 | 1.00 | 5.83 | 164,390.9 | 3.602 | weight_read | 0.30x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 1.33x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x168 | 136,920 | 1.00 | 1.00 | 890,278.0 | 6.502 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,494,752.7 | 5.394 | compute | 1.68x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,083.0 | 0.081 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 0.81x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x7-perregion | 323,575 | 1.00 | 13.84 | 310,960.0 | 0.961 | weight_read | 0.35x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 724,758.4 | 2.240 | weight_read | 0.81x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 1.00 | 1.00 | 1,350,160.7 | 9.745 | thermal | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,557,470.8 | 5.621 | compute | 1.15x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56-perstream | 45,640 | 1.00 | 18.29 | 26,102.7 | 0.572 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 2.57 | 739,278.2 | 2.285 | weight_read | 0.55x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x7-perregion | 323,575 | 1.00 | 38.75 | 509,754.4 | 1.575 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.25 | 757,861.2 | 2.342 | kv_read | 0.56x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 1,902,183.6 | 6.865 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,582,220.8 | 5.710 | compute | 0.83x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 10.29 | 26,110.2 | 0.081 | weight_read | 0.01x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 10.29 | 746,408.6 | 2.307 | weight_read | 0.39x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x7-perregion | 323,575 | 1.00 | 124.47 | 603,512.6 | 1.865 | kv_read | 0.32x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 2.33 | 765,356.4 | 2.365 | kv_read | 0.40x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 584,464.8 | 0.269 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 584,464.8 | 0.269 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 584,464.8 | 0.269 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 584,464.8 | 0.269 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 584,464.8 | 0.269 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x399-perregion | 325,185 | 1.00 | 2.54 | 38,015.4 | 0.117 | link_latency | 0.07x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 584,464.8 | 0.269 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x399-perregion | 325,185 | 1.00 | 3.49 | 61,655.0 | 0.190 | link_latency | 0.11x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 584,464.8 | 0.269 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x47-perregion | 2,172,575 | 1.00 | 4.92 | 97,446.7 | 0.045 | link_latency | 0.17x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 584,464.8 | 0.269 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x47-perregion | 2,172,575 | 1.00 | 10.96 | 243,217.4 | 0.112 | link_latency | 0.42x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.26x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | 2,172,575 | 1.00 | 1.00 | 624,260.6 | 0.287 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.18x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,106.7 | 0.012 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.18x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x47-perregion | 2,172,575 | 1.00 | 28.90 | 383,375.5 | 0.176 | link_latency | 0.61x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 736,415.4 | 0.339 | kv_read | 1.18x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 738,201.0 | 0.340 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 738,201.0 | 0.340 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399-perstream | 325,185 | 1.00 | 10.27 | 26,109.4 | 0.080 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.54 | 738,201.0 | 0.340 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x47-perregion | 2,172,575 | 1.00 | 88.68 | 433,735.2 | 0.200 | kv_read | 0.59x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.05 | 738,201.0 | 0.340 | kv_read | 1.00x |

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
| Qwen3-8B | 1 | 2 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 57 | 1.12 | 1.123 | 1.123 | 1.00x |
| Qwen3-8B | 256 | 49 | 5.22 | 5.224 | 5.224 | 1.00x |
| Qwen3-8B | 1024 | 49 | 20.90 | 20.898 | 20.898 | 1.00x |
| Qwen3-8B | 4096 | 49 | 83.59 | 83.592 | 83.592 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 1.14 | 1.002 | 1.017 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 4.57 | 1.043 | 1.686 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 56 | 18.29 | 1.218 | 3.075 | 2.52x |
| DeepSeek-V4-Flash-0731 | 4096 | 56 | 73.14 | 2.082 | 6.293 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 78 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 399 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 399 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 399 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 399 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | 399 | 2.57 | 1.012 | 1.177 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4096 | 399 | 10.27 | 1.075 | 2.150 | 2.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 8 | 6.36 | 3.68 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 8 | 7.64 | 4.38 | 1.74x |
| DeepSeek-V4-Flash-0731 | 8 | 8 | 7.98 | 5.03 | 1.59x |
| DeepSeek-V4-Flash-0731 | 16 | 8 | 8.00 | 5.58 | 1.43x |
| DeepSeek-V4-Flash-0731 | 32 | 8 | 8.00 | 6.01 | 1.33x |
| DeepSeek-V4-Flash-0731 | 64 | 8 | 8.00 | 6.29 | 1.27x |
| DeepSeek-V4-Flash-0731 | 256 | 8 | 8.00 | 6.45 | 1.24x |
| DeepSeek-V4-Flash-0731 | 1 | 10 | 4.69 | 3.22 | 1.45x |
| DeepSeek-V4-Flash-0731 | 2 | 10 | 7.13 | 4.05 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 10 | 9.13 | 4.92 | 1.86x |
| DeepSeek-V4-Flash-0731 | 8 | 10 | 9.91 | 5.76 | 1.72x |
| DeepSeek-V4-Flash-0731 | 16 | 10 | 10.00 | 6.50 | 1.54x |
| DeepSeek-V4-Flash-0731 | 32 | 10 | 10.00 | 7.09 | 1.41x |
| DeepSeek-V4-Flash-0731 | 64 | 10 | 10.00 | 7.48 | 1.34x |
| DeepSeek-V4-Flash-0731 | 256 | 10 | 10.00 | 7.71 | 1.30x |
| DeepSeek-V4-Flash-0731 | 1024 | 10 | 10.00 | 7.71 | 1.30x |
| DeepSeek-V4-Flash-0731 | 1 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 2 | 11 | 7.45 | 4.21 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 11 | 9.79 | 5.16 | 1.90x |
| DeepSeek-V4-Flash-0731 | 8 | 11 | 10.84 | 6.09 | 1.78x |
| DeepSeek-V4-Flash-0731 | 16 | 11 | 11.00 | 6.93 | 1.59x |
| DeepSeek-V4-Flash-0731 | 32 | 11 | 11.00 | 7.60 | 1.45x |
| DeepSeek-V4-Flash-0731 | 64 | 11 | 11.00 | 8.04 | 1.37x |
| DeepSeek-V4-Flash-0731 | 256 | 11 | 11.00 | 8.31 | 1.32x |
| DeepSeek-V4-Flash-0731 | 1024 | 11 | 11.00 | 8.31 | 1.32x |
| DeepSeek-V4-Flash-0731 | 1 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 2 | 16 | 8.56 | 4.83 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 16 | 12.41 | 6.15 | 2.02x |
| DeepSeek-V4-Flash-0731 | 8 | 16 | 15.08 | 7.51 | 2.01x |
| DeepSeek-V4-Flash-0731 | 16 | 16 | 15.91 | 8.79 | 1.81x |
| DeepSeek-V4-Flash-0731 | 32 | 16 | 16.00 | 9.86 | 1.62x |
| DeepSeek-V4-Flash-0731 | 64 | 16 | 16.00 | 10.60 | 1.51x |
| DeepSeek-V4-Flash-0731 | 256 | 16 | 16.00 | 11.05 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1024 | 16 | 16.00 | 11.05 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 8.86 | 5.03 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 13.21 | 6.47 | 2.04x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 16.56 | 7.99 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 17.82 | 9.44 | 1.89x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 17.99 | 10.67 | 1.69x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 18.00 | 11.53 | 1.56x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1024 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 2 | 21 | 9.23 | 5.29 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 21 | 14.22 | 6.90 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 21 | 18.57 | 8.63 | 2.15x |
| DeepSeek-V4-Flash-0731 | 16 | 21 | 20.59 | 10.33 | 1.99x |
| DeepSeek-V4-Flash-0731 | 32 | 21 | 20.97 | 11.79 | 1.78x |
| DeepSeek-V4-Flash-0731 | 64 | 21 | 21.00 | 12.82 | 1.64x |
| DeepSeek-V4-Flash-0731 | 256 | 21 | 21.00 | 13.46 | 1.56x |
| DeepSeek-V4-Flash-0731 | 1024 | 21 | 21.00 | 13.46 | 1.56x |
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 9.33 | 5.36 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 14.51 | 7.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 19.19 | 8.83 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 21.49 | 10.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 21.96 | 12.14 | 1.81x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 22.00 | 13.24 | 1.66x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1024 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 23 | 9.42 | 5.44 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 23 | 14.79 | 7.16 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 23 | 19.78 | 9.03 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 23 | 22.37 | 10.88 | 2.06x |
| DeepSeek-V4-Flash-0731 | 32 | 23 | 22.95 | 12.49 | 1.84x |
| DeepSeek-V4-Flash-0731 | 64 | 23 | 23.00 | 13.64 | 1.69x |
| DeepSeek-V4-Flash-0731 | 256 | 23 | 23.00 | 14.35 | 1.60x |
| DeepSeek-V4-Flash-0731 | 1024 | 23 | 23.00 | 14.35 | 1.60x |
| DeepSeek-V4-Flash-0731 | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4-Flash-0731 | 2 | 24 | 9.51 | 5.51 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 24 | 15.05 | 7.28 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 24 | 20.35 | 9.21 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 24 | 23.23 | 11.14 | 2.09x |
| DeepSeek-V4-Flash-0731 | 32 | 24 | 23.93 | 12.82 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 24 | 24.00 | 14.03 | 1.71x |
| DeepSeek-V4-Flash-0731 | 256 | 24 | 24.00 | 14.78 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 24 | 24.00 | 14.79 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 9.87 | 5.82 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 16.14 | 7.83 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 22.86 | 10.06 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 27.30 | 12.35 | 2.21x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 28.76 | 14.39 | 2.00x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 28.97 | 15.88 | 1.82x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 1024 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 1 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 30 | 9.93 | 5.88 | 1.69x |
| DeepSeek-V4-Flash-0731 | 4 | 30 | 16.32 | 7.93 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 30 | 23.31 | 10.22 | 2.28x |
| DeepSeek-V4-Flash-0731 | 16 | 30 | 28.06 | 12.57 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 30 | 29.70 | 14.68 | 2.02x |
| DeepSeek-V4-Flash-0731 | 64 | 30 | 29.97 | 16.23 | 1.85x |
| DeepSeek-V4-Flash-0731 | 256 | 30 | 29.99 | 17.20 | 1.74x |
| DeepSeek-V4-Flash-0731 | 1024 | 30 | 29.99 | 17.21 | 1.74x |
| DeepSeek-V4-Flash-0731 | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 32 | 10.04 | 5.99 | 1.68x |
| DeepSeek-V4-Flash-0731 | 4 | 32 | 16.66 | 8.12 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 32 | 24.15 | 10.52 | 2.30x |
| DeepSeek-V4-Flash-0731 | 16 | 32 | 29.54 | 13.00 | 2.27x |
| DeepSeek-V4-Flash-0731 | 32 | 32 | 31.58 | 15.25 | 2.07x |
| DeepSeek-V4-Flash-0731 | 64 | 32 | 31.94 | 16.91 | 1.89x |
| DeepSeek-V4-Flash-0731 | 256 | 32 | 31.99 | 17.95 | 1.78x |
| DeepSeek-V4-Flash-0731 | 1024 | 32 | 31.99 | 17.96 | 1.78x |
| DeepSeek-V4-Flash-0731 | 1 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4-Flash-0731 | 2 | 36 | 10.22 | 6.19 | 1.65x |
| DeepSeek-V4-Flash-0731 | 4 | 36 | 17.26 | 8.47 | 2.04x |
| DeepSeek-V4-Flash-0731 | 8 | 36 | 25.65 | 11.07 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 36 | 32.31 | 13.81 | 2.34x |
| DeepSeek-V4-Flash-0731 | 32 | 36 | 35.22 | 16.32 | 2.16x |
| DeepSeek-V4-Flash-0731 | 64 | 36 | 35.87 | 18.20 | 1.97x |
| DeepSeek-V4-Flash-0731 | 256 | 36 | 35.97 | 19.38 | 1.86x |
| DeepSeek-V4-Flash-0731 | 1024 | 36 | 35.97 | 19.39 | 1.85x |
| DeepSeek-V4-Flash-0731 | 4096 | 36 | 35.97 | 19.39 | 1.85x |
| DeepSeek-V4-Flash-0731 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 43 | 10.47 | 6.49 | 1.61x |
| DeepSeek-V4-Flash-0731 | 4 | 43 | 18.07 | 9.00 | 2.01x |
| DeepSeek-V4-Flash-0731 | 8 | 43 | 27.82 | 11.92 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 43 | 36.58 | 15.07 | 2.43x |
| DeepSeek-V4-Flash-0731 | 32 | 43 | 41.25 | 18.02 | 2.29x |
| DeepSeek-V4-Flash-0731 | 64 | 43 | 42.61 | 20.26 | 2.10x |
| DeepSeek-V4-Flash-0731 | 256 | 43 | 42.89 | 21.69 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1024 | 43 | 42.90 | 21.70 | 1.98x |
| DeepSeek-V4-Flash-0731 | 4096 | 43 | 42.90 | 21.70 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 10.79 | 6.99 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 19.18 | 9.81 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 30.95 | 13.28 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 43.37 | 17.16 | 2.53x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 51.88 | 20.90 | 2.48x |
| DeepSeek-V4-Flash-0731 | 64 | 57 | 55.34 | 23.81 | 2.32x |
| DeepSeek-V4-Flash-0731 | 256 | 57 | 56.38 | 25.71 | 2.19x |
| DeepSeek-V4-Flash-0731 | 1024 | 57 | 56.39 | 25.73 | 2.19x |
| DeepSeek-V4-Flash-0731 | 4096 | 57 | 56.39 | 25.73 | 2.19x |
| DeepSeek-V4-Flash-0731 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 58 | 10.81 | 7.02 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4 | 58 | 19.24 | 9.86 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 58 | 31.13 | 13.37 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 58 | 43.78 | 17.30 | 2.53x |
| DeepSeek-V4-Flash-0731 | 32 | 58 | 52.57 | 21.09 | 2.49x |
| DeepSeek-V4-Flash-0731 | 64 | 58 | 56.21 | 24.04 | 2.34x |
| DeepSeek-V4-Flash-0731 | 256 | 58 | 57.32 | 25.97 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1024 | 58 | 57.32 | 25.99 | 2.21x |
| DeepSeek-V4-Flash-0731 | 4096 | 58 | 57.32 | 25.99 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 86 | 11.14 | 7.76 | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | 86 | 20.41 | 10.92 | 1.87x |
| DeepSeek-V4-Flash-0731 | 8 | 86 | 34.74 | 15.37 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 86 | 52.59 | 20.42 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 86 | 68.50 | 25.50 | 2.69x |
| DeepSeek-V4-Flash-0731 | 64 | 86 | 77.70 | 29.61 | 2.62x |
| DeepSeek-V4-Flash-0731 | 256 | 86 | 81.66 | 32.36 | 2.52x |
| DeepSeek-V4-Flash-0731 | 1024 | 86 | 81.69 | 32.38 | 2.52x |
| DeepSeek-V4-Flash-0731 | 4096 | 86 | 81.69 | 32.38 | 2.52x |
| DeepSeek-V4-Flash-0731 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 87 | 11.15 | 7.78 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 87 | 20.44 | 10.95 | 1.87x |
| DeepSeek-V4-Flash-0731 | 8 | 87 | 34.83 | 15.44 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 87 | 52.83 | 20.51 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 87 | 68.97 | 25.63 | 2.69x |
| DeepSeek-V4-Flash-0731 | 64 | 87 | 78.37 | 29.78 | 2.63x |
| DeepSeek-V4-Flash-0731 | 256 | 87 | 82.46 | 32.55 | 2.53x |
| DeepSeek-V4-Flash-0731 | 1024 | 87 | 82.49 | 32.58 | 2.53x |
| DeepSeek-V4-Flash-0731 | 4096 | 87 | 82.49 | 32.58 | 2.53x |
| DeepSeek-V4-Flash-0731 | 1 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 114 | 11.31 | 8.30 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 114 | 21.05 | 11.66 | 1.80x |
| DeepSeek-V4-Flash-0731 | 8 | 114 | 36.80 | 16.88 | 2.18x |
| DeepSeek-V4-Flash-0731 | 16 | 114 | 58.08 | 22.74 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 114 | 79.65 | 28.87 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 114 | 94.41 | 33.96 | 2.78x |
| DeepSeek-V4-Flash-0731 | 256 | 114 | 101.99 | 37.41 | 2.73x |
| DeepSeek-V4-Flash-0731 | 1024 | 114 | 102.05 | 37.44 | 2.73x |
| DeepSeek-V4-Flash-0731 | 4096 | 114 | 102.05 | 37.44 | 2.73x |
| DeepSeek-V4-Flash-0731 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 116 | 11.32 | 8.33 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 116 | 21.08 | 11.71 | 1.80x |
| DeepSeek-V4-Flash-0731 | 8 | 116 | 36.91 | 16.98 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 116 | 58.39 | 22.88 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 116 | 80.31 | 29.09 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 116 | 95.45 | 34.23 | 2.79x |
| DeepSeek-V4-Flash-0731 | 256 | 116 | 103.29 | 37.73 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1024 | 116 | 103.36 | 37.77 | 2.74x |
| DeepSeek-V4-Flash-0731 | 4096 | 116 | 103.36 | 37.77 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 173 | 11.49 | 9.06 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 173 | 21.74 | 12.85 | 1.69x |
| DeepSeek-V4-Flash-0731 | 8 | 173 | 39.14 | 19.00 | 2.06x |
| DeepSeek-V4-Flash-0731 | 16 | 173 | 64.73 | 26.15 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 173 | 94.43 | 34.13 | 2.77x |
| DeepSeek-V4-Flash-0731 | 64 | 173 | 118.70 | 40.88 | 2.90x |
| DeepSeek-V4-Flash-0731 | 256 | 173 | 133.64 | 45.54 | 2.93x |
| DeepSeek-V4-Flash-0731 | 1024 | 173 | 133.78 | 45.59 | 2.93x |
| DeepSeek-V4-Flash-0731 | 4096 | 173 | 133.78 | 45.59 | 2.93x |
| DeepSeek-V4-Flash-0731 | 1 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 202 | 11.55 | 9.33 | 1.24x |
| DeepSeek-V4-Flash-0731 | 4 | 202 | 21.94 | 13.34 | 1.64x |
| DeepSeek-V4-Flash-0731 | 8 | 202 | 39.82 | 19.70 | 2.02x |
| DeepSeek-V4-Flash-0731 | 16 | 202 | 66.76 | 27.49 | 2.43x |
| DeepSeek-V4-Flash-0731 | 32 | 202 | 99.22 | 36.20 | 2.74x |
| DeepSeek-V4-Flash-0731 | 64 | 202 | 127.09 | 43.55 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 202 | 145.13 | 48.74 | 2.98x |
| DeepSeek-V4-Flash-0731 | 1024 | 202 | 145.30 | 48.79 | 2.98x |
| DeepSeek-V4-Flash-0731 | 4096 | 202 | 145.30 | 48.79 | 2.98x |
| DeepSeek-V4-Flash-0731 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 231 | 11.58 | 9.55 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 231 | 22.09 | 13.78 | 1.60x |
| DeepSeek-V4-Flash-0731 | 8 | 231 | 40.34 | 20.26 | 1.99x |
| DeepSeek-V4-Flash-0731 | 16 | 231 | 68.33 | 28.71 | 2.38x |
| DeepSeek-V4-Flash-0731 | 32 | 231 | 103.04 | 37.98 | 2.71x |
| DeepSeek-V4-Flash-0731 | 64 | 231 | 133.95 | 45.87 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 231 | 154.72 | 51.61 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 231 | 154.92 | 51.66 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 231 | 154.92 | 51.66 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 347 | 11.68 | 10.15 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 347 | 22.44 | 15.21 | 1.48x |
| DeepSeek-V4-Flash-0731 | 8 | 347 | 41.59 | 21.88 | 1.90x |
| DeepSeek-V4-Flash-0731 | 16 | 347 | 72.20 | 32.56 | 2.22x |
| DeepSeek-V4-Flash-0731 | 32 | 347 | 112.75 | 43.11 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 347 | 152.11 | 53.42 | 2.85x |
| DeepSeek-V4-Flash-0731 | 256 | 347 | 180.96 | 60.40 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 347 | 181.25 | 60.47 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 347 | 181.25 | 60.47 | 3.00x |
| DeepSeek-V4-Pro-0813 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4-Pro-0813 | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4-Pro-0813 | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4-Pro-0813 | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4-Pro-0813 | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4-Pro-0813 | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4-Pro-0813 | 1 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Pro-0813 | 2 | 40 | 10.41 | 6.38 | 1.63x |
| DeepSeek-V4-Pro-0813 | 4 | 40 | 17.91 | 8.83 | 2.03x |
| DeepSeek-V4-Pro-0813 | 8 | 40 | 27.35 | 11.70 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 40 | 35.41 | 14.84 | 2.39x |
| DeepSeek-V4-Pro-0813 | 32 | 40 | 39.15 | 17.91 | 2.19x |
| DeepSeek-V4-Pro-0813 | 64 | 40 | 39.92 | 20.48 | 1.95x |
| DeepSeek-V4-Pro-0813 | 256 | 40 | 40.00 | 22.81 | 1.75x |
| DeepSeek-V4-Pro-0813 | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Pro-0813 | 2 | 44 | 10.54 | 6.54 | 1.61x |
| DeepSeek-V4-Pro-0813 | 4 | 44 | 18.33 | 9.11 | 2.01x |
| DeepSeek-V4-Pro-0813 | 8 | 44 | 28.53 | 12.16 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 44 | 37.84 | 15.55 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 44 | 42.66 | 18.90 | 2.26x |
| DeepSeek-V4-Pro-0813 | 64 | 44 | 43.84 | 21.72 | 2.02x |
| DeepSeek-V4-Pro-0813 | 256 | 44 | 43.99 | 24.31 | 1.81x |
| DeepSeek-V4-Pro-0813 | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Pro-0813 | 2 | 46 | 10.59 | 6.62 | 1.60x |
| DeepSeek-V4-Pro-0813 | 4 | 46 | 18.52 | 9.24 | 2.00x |
| DeepSeek-V4-Pro-0813 | 8 | 46 | 29.06 | 12.38 | 2.35x |
| DeepSeek-V4-Pro-0813 | 16 | 46 | 38.98 | 15.89 | 2.45x |
| DeepSeek-V4-Pro-0813 | 32 | 46 | 44.37 | 19.37 | 2.29x |
| DeepSeek-V4-Pro-0813 | 64 | 46 | 45.78 | 22.32 | 2.05x |
| DeepSeek-V4-Pro-0813 | 256 | 46 | 45.99 | 25.03 | 1.84x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4-Pro-0813 | 1 | 63 | 5.77 | 4.97 | 1.16x |
| DeepSeek-V4-Pro-0813 | 2 | 63 | 10.93 | 7.19 | 1.52x |
| DeepSeek-V4-Pro-0813 | 4 | 63 | 19.71 | 10.15 | 1.94x |
| DeepSeek-V4-Pro-0813 | 8 | 63 | 32.56 | 13.95 | 2.33x |
| DeepSeek-V4-Pro-0813 | 16 | 63 | 46.97 | 18.35 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 63 | 57.47 | 22.88 | 2.51x |
| DeepSeek-V4-Pro-0813 | 64 | 63 | 61.73 | 26.85 | 2.30x |
| DeepSeek-V4-Pro-0813 | 256 | 63 | 62.85 | 30.60 | 2.05x |
| DeepSeek-V4-Pro-0813 | 1 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4-Pro-0813 | 2 | 70 | 11.02 | 7.38 | 1.49x |
| DeepSeek-V4-Pro-0813 | 4 | 70 | 20.04 | 10.44 | 1.92x |
| DeepSeek-V4-Pro-0813 | 8 | 70 | 33.60 | 14.49 | 2.32x |
| DeepSeek-V4-Pro-0813 | 16 | 70 | 49.55 | 19.21 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 70 | 62.14 | 24.12 | 2.58x |
| DeepSeek-V4-Pro-0813 | 64 | 70 | 67.90 | 28.48 | 2.38x |
| DeepSeek-V4-Pro-0813 | 256 | 70 | 69.69 | 32.63 | 2.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 70 | 69.72 | 32.80 | 2.13x |
| DeepSeek-V4-Pro-0813 | 1 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4-Pro-0813 | 2 | 71 | 11.03 | 7.41 | 1.49x |
| DeepSeek-V4-Pro-0813 | 4 | 71 | 20.09 | 10.48 | 1.92x |
| DeepSeek-V4-Pro-0813 | 8 | 71 | 33.74 | 14.56 | 2.32x |
| DeepSeek-V4-Pro-0813 | 16 | 71 | 49.90 | 19.33 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 71 | 62.78 | 24.30 | 2.58x |
| DeepSeek-V4-Pro-0813 | 64 | 71 | 68.77 | 28.70 | 2.40x |
| DeepSeek-V4-Pro-0813 | 256 | 71 | 70.66 | 32.91 | 2.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 71 | 70.69 | 33.09 | 2.14x |
| DeepSeek-V4-Pro-0813 | 1 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 85 | 11.17 | 7.75 | 1.44x |
| DeepSeek-V4-Pro-0813 | 4 | 85 | 20.59 | 10.96 | 1.88x |
| DeepSeek-V4-Pro-0813 | 8 | 85 | 35.36 | 15.51 | 2.28x |
| DeepSeek-V4-Pro-0813 | 16 | 85 | 54.11 | 20.83 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 85 | 70.93 | 26.50 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 85 | 80.26 | 31.63 | 2.54x |
| DeepSeek-V4-Pro-0813 | 256 | 85 | 84.02 | 36.61 | 2.29x |
| DeepSeek-V4-Pro-0813 | 1024 | 85 | 84.10 | 36.82 | 2.28x |
| DeepSeek-V4-Pro-0813 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4-Pro-0813 | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4-Pro-0813 | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4-Pro-0813 | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4-Pro-0813 | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4-Pro-0813 | 1 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 93 | 11.23 | 7.92 | 1.42x |
| DeepSeek-V4-Pro-0813 | 4 | 93 | 20.82 | 11.20 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 93 | 36.11 | 16.00 | 2.26x |
| DeepSeek-V4-Pro-0813 | 16 | 93 | 56.11 | 21.60 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 93 | 75.02 | 27.64 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 93 | 86.34 | 33.16 | 2.60x |
| DeepSeek-V4-Pro-0813 | 256 | 93 | 91.42 | 38.56 | 2.37x |
| DeepSeek-V4-Pro-0813 | 1024 | 93 | 91.54 | 38.78 | 2.36x |
| DeepSeek-V4-Pro-0813 | 1 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 94 | 11.24 | 7.94 | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | 94 | 20.85 | 11.23 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 94 | 36.19 | 16.05 | 2.25x |
| DeepSeek-V4-Pro-0813 | 16 | 94 | 56.34 | 21.70 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 94 | 75.50 | 27.77 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 94 | 87.07 | 33.34 | 2.61x |
| DeepSeek-V4-Pro-0813 | 256 | 94 | 92.34 | 38.79 | 2.38x |
| DeepSeek-V4-Pro-0813 | 1024 | 94 | 92.45 | 39.02 | 2.37x |
| DeepSeek-V4-Pro-0813 | 1 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 113 | 11.35 | 8.30 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 113 | 21.26 | 11.72 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 113 | 37.56 | 17.07 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 113 | 60.17 | 23.29 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 113 | 83.74 | 30.18 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 113 | 100.07 | 36.59 | 2.74x |
| DeepSeek-V4-Pro-0813 | 256 | 113 | 109.05 | 42.97 | 2.54x |
| DeepSeek-V4-Pro-0813 | 1024 | 113 | 109.28 | 43.24 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4-Pro-0813 | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4-Pro-0813 | 1 | 121 | 5.88 | 5.39 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 121 | 11.38 | 8.43 | 1.35x |
| DeepSeek-V4-Pro-0813 | 4 | 121 | 21.39 | 11.90 | 1.80x |
| DeepSeek-V4-Pro-0813 | 8 | 121 | 38.02 | 17.44 | 2.18x |
| DeepSeek-V4-Pro-0813 | 16 | 121 | 61.50 | 23.88 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 121 | 86.73 | 31.09 | 2.79x |
| DeepSeek-V4-Pro-0813 | 64 | 121 | 105.01 | 37.83 | 2.78x |
| DeepSeek-V4-Pro-0813 | 256 | 121 | 115.71 | 44.59 | 2.59x |
| DeepSeek-V4-Pro-0813 | 1024 | 121 | 116.00 | 44.88 | 2.58x |
| DeepSeek-V4-Pro-0813 | 1 | 126 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 126 | 11.40 | 8.50 | 1.34x |
| DeepSeek-V4-Pro-0813 | 4 | 126 | 21.47 | 12.02 | 1.79x |
| DeepSeek-V4-Pro-0813 | 8 | 126 | 38.29 | 17.66 | 2.17x |
| DeepSeek-V4-Pro-0813 | 16 | 126 | 62.26 | 24.23 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 126 | 88.47 | 31.63 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 126 | 107.95 | 38.58 | 2.80x |
| DeepSeek-V4-Pro-0813 | 256 | 126 | 119.76 | 45.56 | 2.63x |
| DeepSeek-V4-Pro-0813 | 1024 | 126 | 120.09 | 45.86 | 2.62x |
| DeepSeek-V4-Pro-0813 | 1 | 133 | 5.89 | 5.44 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 133 | 11.43 | 8.60 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 133 | 21.57 | 12.17 | 1.77x |
| DeepSeek-V4-Pro-0813 | 8 | 133 | 38.62 | 17.96 | 2.15x |
| DeepSeek-V4-Pro-0813 | 16 | 133 | 63.26 | 24.69 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 133 | 90.77 | 32.35 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 133 | 111.88 | 39.59 | 2.83x |
| DeepSeek-V4-Pro-0813 | 256 | 133 | 125.28 | 46.88 | 2.67x |
| DeepSeek-V4-Pro-0813 | 1024 | 133 | 125.67 | 47.19 | 2.66x |
| DeepSeek-V4-Pro-0813 | 1 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 144 | 11.47 | 8.75 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 144 | 21.70 | 12.39 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 144 | 39.10 | 18.38 | 2.13x |
| DeepSeek-V4-Pro-0813 | 16 | 144 | 64.66 | 25.37 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 144 | 94.08 | 33.43 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 144 | 117.67 | 41.09 | 2.86x |
| DeepSeek-V4-Pro-0813 | 256 | 144 | 133.60 | 48.85 | 2.73x |
| DeepSeek-V4-Pro-0813 | 1024 | 144 | 134.09 | 49.19 | 2.73x |
| DeepSeek-V4-Pro-0813 | 1 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 150 | 11.48 | 8.83 | 1.30x |
| DeepSeek-V4-Pro-0813 | 4 | 150 | 21.77 | 12.51 | 1.74x |
| DeepSeek-V4-Pro-0813 | 8 | 150 | 39.33 | 18.59 | 2.12x |
| DeepSeek-V4-Pro-0813 | 16 | 150 | 65.35 | 25.71 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 150 | 95.74 | 33.98 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 150 | 120.64 | 41.87 | 2.88x |
| DeepSeek-V4-Pro-0813 | 256 | 150 | 137.97 | 49.89 | 2.77x |
| DeepSeek-V4-Pro-0813 | 1024 | 150 | 138.50 | 50.23 | 2.76x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4-Pro-0813 | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4-Pro-0813 | 1 | 174 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 174 | 11.54 | 9.10 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 174 | 21.99 | 12.95 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 174 | 40.10 | 19.34 | 2.07x |
| DeepSeek-V4-Pro-0813 | 16 | 174 | 67.72 | 26.98 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 174 | 101.55 | 36.03 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 174 | 131.33 | 44.74 | 2.94x |
| DeepSeek-V4-Pro-0813 | 256 | 174 | 154.21 | 53.73 | 2.87x |
| DeepSeek-V4-Pro-0813 | 1024 | 174 | 154.97 | 54.12 | 2.86x |
| DeepSeek-V4-Pro-0813 | 1 | 175 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 175 | 11.54 | 9.11 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 175 | 22.00 | 12.97 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 175 | 40.13 | 19.37 | 2.07x |
| DeepSeek-V4-Pro-0813 | 16 | 175 | 67.81 | 27.03 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 175 | 101.77 | 36.11 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 175 | 131.73 | 44.86 | 2.94x |
| DeepSeek-V4-Pro-0813 | 256 | 175 | 154.85 | 53.88 | 2.87x |
| DeepSeek-V4-Pro-0813 | 1024 | 175 | 155.62 | 54.27 | 2.87x |
| DeepSeek-V4-Pro-0813 | 1 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 203 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 203 | 22.19 | 13.44 | 1.65x |
| DeepSeek-V4-Pro-0813 | 8 | 203 | 40.82 | 20.06 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 203 | 69.94 | 28.35 | 2.47x |
| DeepSeek-V4-Pro-0813 | 32 | 203 | 107.17 | 38.24 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 203 | 142.11 | 47.84 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 203 | 171.48 | 57.86 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1024 | 203 | 172.53 | 58.30 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 255 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 255 | 11.65 | 9.73 | 1.20x |
| DeepSeek-V4-Pro-0813 | 4 | 255 | 22.44 | 14.20 | 1.58x |
| DeepSeek-V4-Pro-0813 | 8 | 255 | 41.71 | 21.04 | 1.98x |
| DeepSeek-V4-Pro-0813 | 16 | 255 | 72.78 | 30.51 | 2.39x |
| DeepSeek-V4-Pro-0813 | 32 | 255 | 114.67 | 41.62 | 2.76x |
| DeepSeek-V4-Pro-0813 | 64 | 255 | 157.18 | 52.56 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 255 | 197.07 | 64.26 | 3.07x |
| DeepSeek-V4-Pro-0813 | 1024 | 255 | 198.60 | 64.78 | 3.07x |
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
| DeepSeek-V4-Pro-0813 | 1 | 1358 | 5.99 | 5.95 | 1.01x |
| DeepSeek-V4-Pro-0813 | 2 | 1358 | 11.86 | 11.38 | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | 1358 | 23.25 | 19.94 | 1.17x |
| DeepSeek-V4-Pro-0813 | 8 | 1358 | 44.72 | 29.80 | 1.50x |
| DeepSeek-V4-Pro-0813 | 16 | 1358 | 82.92 | 43.33 | 1.91x |
| DeepSeek-V4-Pro-0813 | 32 | 1358 | 143.86 | 67.35 | 2.14x |
| DeepSeek-V4-Pro-0813 | 64 | 1358 | 223.28 | 89.36 | 2.50x |
| DeepSeek-V4-Pro-0813 | 256 | 1358 | 329.44 | 116.81 | 2.82x |
| DeepSeek-V4-Pro-0813 | 1024 | 1358 | 334.59 | 118.22 | 2.83x |
| DeepSeek-V4-Pro-0813 | 4096 | 1358 | 334.59 | 118.22 | 2.83x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 4.9% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 4.3% |
| gpu | Qwen3-8B | 1 | 6.82 | 3.0% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 22.5% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 10.8% |
| rom | Qwen3-8B | 1 | 6.82 | 28.8% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Qwen3-8B | sram | interleaved | 128 B | 1.00x |
| Qwen3-8B | hbm | interleaved | 32 B | 1.00x |
| DeepSeek-V4-Flash-0731 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Flash-0731 | hbm | interleaved | 32 B | 1.00x |
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
| Qwen3-8B | 1 | 2 | 90.60% | 16.81 | 9.27 |
| Qwen3-8B | 2 | 1 | 1.08% | 5.71 | 9.27 |
| Qwen3-8B | 4 | 1 | 1.08% | 5.71 | 9.27 |
| Qwen3-8B | 8 | 1 | 1.08% | 5.71 | 9.27 |
| Qwen3-8B | 16 | 1 | 1.08% | 5.71 | 9.27 |
| Qwen3-8B | 32 | 1 | 1.08% | 5.71 | 9.27 |
| Qwen3-8B | 64 | 1 | 1.21% | 6.42 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 15 | 50.49% | 16.14 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 78 | 97.47% | 157.92 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 12.07% | 28.59 | 2.08 |
| DeepSeek-V4-Pro-0813 | 4 | 2 | 12.07% | 28.59 | 2.08 |
| DeepSeek-V4-Pro-0813 | 8 | 2 | 12.07% | 28.59 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 574.1 | 28,130.9 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 574.1 | 28,130.9 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 574.1 | 28,130.9 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 574.1 | 28,130.9 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 574.1 | 28,130.9 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 574.1 | 28,130.9 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 574.1 | 36,741.8 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 403.0 | 103,179.3 |
| Qwen3-8B | 1024 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 101.3 | 103,705.0 |
| Qwen3-8B | 4096 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 25.4 | 103,837.3 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 5,027.0 | 281,512.6 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 5,027.0 | 281,512.6 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 5,027.0 | 281,512.6 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 5,027.0 | 281,512.6 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 5,027.0 | 281,512.6 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 5,027.0 | 281,512.6 |
| DeepSeek-V4-Flash-0731 | 64 | 2.67% | 11.7 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 4,436.9 | 283,959.4 |
| DeepSeek-V4-Flash-0731 | 256 | 10.27% | 22.9 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,162.3 | 297,536.4 |
| DeepSeek-V4-Flash-0731 | 1024 | 35.19% | 59.6 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 294.1 | 301,136.0 |
| DeepSeek-V4-Flash-0731 | 4096 | 82.35% | 129.0 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 73.7 | 302,049.5 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 1,170.7 | 467,127.5 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 1,170.7 | 467,127.5 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 1,170.7 | 467,127.5 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 1,170.7 | 467,127.5 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 1,170.7 | 467,127.5 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 1,170.7 | 467,127.5 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 1,170.7 | 467,127.5 |
| DeepSeek-V4-Pro-0813 | 256 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 1,170.7 | 467,127.5 |
| DeepSeek-V4-Pro-0813 | 1024 | 3.96% | 59.4 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 462.6 | 473,748.1 |
| DeepSeek-V4-Pro-0813 | 4096 | 14.93% | 149.5 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 116.5 | 476,985.0 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 326 |
| gpu | kv_read | 134 |
| gpu | link_latency | 1767 |
| gpu | thermal | 697 |
| gpu | weight_read | 1256 |
| rom | compute | 791 |
| rom | infeasible | 6751 |
| rom | kv_read | 366 |
| rom | link_latency | 2107 |
| rom | thermal | 804 |
| rom | weight_read | 1491 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 326 |
| rom | CAPACITY | 6751 |

## Mechanical consistency audit

**FAIL** over 305,876 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x2', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x4', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x8', 'Qwen3-8B', 1)

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

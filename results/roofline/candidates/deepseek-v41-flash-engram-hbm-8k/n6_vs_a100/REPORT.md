# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash-engram-hbm-8k

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash-engram-hbm at 8,192 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 125x (ROM-N6-native-SRAMKV-array-hw-pipeline-x162-perstream, 162 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 124 devices. On the GPU side the correction reaches 67x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 103 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-hbm takes 73 x 815 mm2 (59,495 mm2, array, KV in HBM) at 9,525 tok/s per user and 160 tok/s per 1,000 mm2, holding 505,615 sessions, against 72 copies of one unified HBM die at the same silicon: 8.9x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-hbm on 277,100 mm2 of ROM silicon at 14,020 tok/s per user against 276,710 mm2 of a100_sxm_80gb-x335-tensor at 843 tok/s: **16.6x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 2,429,123 resident sessions against the GPU cluster's 2,362,332. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 9.24x to it.** At 224,940 mm2 on DeepSeek-V4.1-Flash-engram-hbm the pipeline-only GPU delivers 124.86 tok/s and the same silicon running tensor delivers 1,154 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `link_latency`) to 5.78x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-hbm engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 642 to 47,206 tok/s, and its rate with every slot occupied from 46,871 to 47,206. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 73 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 171.9 us and cap it at 5,817 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 9 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 3 of 4631 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 175.1x of aggregate throughput (DeepSeek-V4.1-Flash-engram-hbm). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 38.61x, on DeepSeek-V4.1-Flash-engram-hbm at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 81% of its cooling budget. The companion study at the other node does have power-limited points.


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

### DeepSeek-V4.1-Flash-engram-hbm at 8,192 tokens

**Recommended: `ROM-N6-native-HBMKV-array-hw-tensor-x73`** -- 73 x 815 mm2 reticle dies, 59,495 mm2 total, `tensor`-parallel, KV in HBM, spare silicon to `sram`.

- **9,525.1 tok/s per user** (0.10 ms/token), binding on `link_latency`
- **160.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 9,525 tok/s aggregate with every slot full, over 505,615 resident sessions (fill limited by `batch`)
- 4,422 W at 0.074 W/mm2, 464.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 72 copies of one unified HBM die -- `a100_sxm_80gb-x72-tensor`, 59,472 mm2, area ratio 1.0004 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 59,495 | 59,472 | 1.0004 |
| user tok/s | 9,525.1 | 1,064.8 | 8.95x |
| aggregate tok/s | 9,525 | 1,065 | 1.06x |
| resident sessions | 505,615 | 467,640 | -- |
| J/token | 0.4643 | 11.1366 | 24.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 505,615 sessions against one that holds 467,640 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x272-tensor` at 224,672 mm2 and 1,154.1 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 101,060 | 13,891.0 | 137.5 | 873,027 | 12.49x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 14,283.7 | 136.9 | 901,843 | 12.81x |
| smallest feasible machine | `ROM-N6-native-HBMKV-array-hw-tensor-x73` | 59,495 | 9,525.1 | 160.1 | 505,615 | 8.95x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-array-hw-tensor-x73` | 59,495 | 9,525.1 | 160.1 | 505,615 | 8.95x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-HBMKV-array-hw-tensor-x73` | 59,495 | 9,525.1 | 160.1 | -- | 160.1 | ACCEPT |
| `ROM-N6-native-HBMKV-array-hw-tensor-x87` | 70,905 | 11,205.6 | 158.0 | 147.3 | 160.1 | stop |
| `ROM-N6-native-HBMKV-array-hw-tensor-x89` | 72,535 | 11,271.1 | 155.4 | 133.9 | 160.1 | stop |
| `ROM-N6-native-HBMKV-array-hw-tensor-x95` | 77,425 | 11,411.9 | 147.4 | 105.2 | 160.1 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 101,060 | 13,891.0 | 137.5 | 105.0 | 160.1 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 14,283.7 | 136.9 | 106.2 | 160.1 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-array-hw-tensor-x73` **<-- recommended** | 59,495 | 73 | 9,525.1 | 9,525 | 160.1 | 505,615 | `link_latency` | 4,422 | 464.3 | `a100_sxm_80gb-x72-tensor` | 8.95x |
| `ROM-N6-native-HBMKV-array-hw-tensor-x87` | 70,905 | 87 | 11,205.6 | 11,206 | 158.0 | 606,473 | `link_latency` | 6,284 | 560.8 | `a100_sxm_80gb-x86-tensor` | 10.35x |
| `ROM-N6-native-HBMKV-array-hw-tensor-x89` | 72,535 | 89 | 11,271.1 | 11,271 | 155.4 | 620,881 | `link_latency` | 6,549 | 581.1 | `a100_sxm_80gb-x88-tensor` | 10.38x |
| `ROM-N6-native-HBMKV-array-hw-tensor-x95` | 77,425 | 95 | 11,411.9 | 11,412 | 147.4 | 664,106 | `link_latency` | 7,343 | 643.5 | `a100_sxm_80gb-x94-tensor` | 10.46x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 101,060 | 124 | 13,891.0 | 430,622 | 137.5 | 873,027 | `compute` | 14,085 | 805.8 | `a100_sxm_80gb-x122-tensor` | 12.49x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 128 | 14,283.7 | 457,079 | 136.9 | 901,843 | `compute` | 14,797 | 820.9 | `a100_sxm_80gb-x126-tensor` | 12.81x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 306 | densest | `ROM-N6-native-HBMKV-array-hw-tensor-x73` | 59,495 | 9,525.1 | 160.1 | 505,615 |
| array | 306 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 14,283.7 | 136.9 | 901,843 |
| array | 306 | smallest | `ROM-N6-native-HBMKV-array-hw-tensor-x73` | 59,495 | 9,525.1 | 160.1 | 505,615 |
| wafer | 69 | densest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 5,952.2 | 64.4 | 103,623 |
| wafer | 69 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,956.2 | 43.0 | 165,579 |
| wafer | 69 | smallest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 5,952.2 | 64.4 | 103,623 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 14,283.7 | 457,079 | 901,843 | 14,797 | 820.9 | `compute` | `a100_sxm_80gb-x126-tensor` | 1,115.0 | 856,664 | 17,690.2 | 1.002 | 12.81x | 21.6x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,956.2 | 17,869 | 165,579 | 13,018 | 2,171.8 | `link_latency` | `a100_sxm_80gb-x168-tensor` | 1,132.9 | 1,159,239 | 22,784.2 | 0.999 | 5.26x | 10.5x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 13,893.9 | 597,436 | 1,204,417 | 19,533 | 1,114.5 | `compute` | `a100_sxm_80gb-x168-tensor` | 1,132.9 | 1,159,239 | 22,784.2 | 0.998 | 12.26x | 20.4x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,956.2 | -- | 165,579 | -- | 2,171.8 | -- | -- | -- | -- | -- | 0.999 | 0.43x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 14,283.7 | 457,079 | 901,843 | 14,797 | 413.9 | `compute` | `a100_sxm_80gb-x126-tensor` | 982.7 | 856,664 | 10,178.5 | 1.002 | 14.54x | 24.6x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,956.2 | 17,869 | 165,579 | 13,018 | 1,089.4 | `link_latency` | `a100_sxm_80gb-x168-tensor` | 1,000.5 | 1,159,239 | 13,044.5 | 0.999 | 5.95x | 12.0x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 13,893.9 | 597,436 | 1,204,417 | 19,533 | 560.7 | `compute` | `a100_sxm_80gb-x168-tensor` | 1,000.5 | 1,159,239 | 13,044.5 | 0.998 | 13.89x | 23.3x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 5,956.2 | -- | 165,579 | -- | 1,089.4 | -- | -- | -- | -- | -- | 0.999 | 0.43x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 14,283.7 | 457,079 | 901,843 | 14,797 | 210.4 | `compute` | `a100_sxm_80gb-x126-tensor` | 794.9 | 856,664 | 6,412.8 | 1.002 | 17.97x | 30.5x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,952.6 | 23,811 | 227,535 | 17,358 | 729.0 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 824.0 | 1,562,671 | 10,502.9 | 0.999 | 7.22x | 14.4x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 13,972.6 | 796,436 | 1,615,054 | 26,073 | 374.6 | `compute` | `a100_sxm_80gb-x224-tensor` | 824.0 | 1,562,671 | 10,502.9 | 1.000 | 16.96x | 28.0x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,952.6 | -- | 227,535 | -- | 729.0 | -- | -- | -- | -- | -- | 1.001 | 0.43x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 14,283.7 | 457,079 | 901,843 | 14,797 | 108.7 | `compute` | `a100_sxm_80gb-x126-hybrid` | 686.3 | 856,664 | 4,687.1 | 1.002 | 20.81x | 41.5x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,938.3 | 47,506 | 475,358 | 34,715 | 730.7 | `link_latency` | `a100_sxm_80gb-x448-hybrid` | 666.7 | 3,176,401 | 13,501.5 | 0.999 | 8.91x | 18.5x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 14,283.7 | 457,079 | 901,843 | 14,797 | 57.8 | `compute` | `a100_sxm_80gb-x126-hybrid` | 686.3 | 856,664 | 3,030.4 | 1.002 | 20.81x | 52.4x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,881.5 | 94,104 | 723,180 | 52,168 | 554.4 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 666.7 | 4,790,130 | 10,469.5 | 0.999 | 8.82x | 18.9x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | 14,283.7 | 457,079 | 901,843 | 14,797 | 32.4 | `compute` | `a100_sxm_80gb-x126-hybrid` | 551.6 | 856,664 | 1,952.7 | 1.002 | 25.90x | 60.3x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,717.6 | 182,964 | 723,180 | 52,542 | 287.2 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 666.7 | 4,790,130 | 5,921.6 | 0.999 | 8.58x | 20.6x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 14,020.1 | 1,191,709 | 2,429,123 | 39,044 | 41.2 | `compute` | `a100_sxm_80gb-x335-hybrid` | 590.7 | 2,362,332 | 2,343.2 | 1.001 | 23.73x | 56.8x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,415.8 | 346,613 | 723,180 | 53,223 | 153.6 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 666.7 | 4,790,130 | 3,647.7 | 0.999 | 8.12x | 23.8x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 5,448.7 | 1,394,859 | 2,429,123 | 37,962 | 27.2 | `compute` | `a100_sxm_80gb-x335-hybrid` | 304.0 | 2,362,332 | 1,227.9 | 1.001 | 17.93x | 30.8x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 4,519.5 | 3,077,785 | 723,180 | 72,933 | 51.5 | `compute` | `a100_sxm_80gb-x672-hybrid` | 448.0 | 4,790,130 | 1,610.3 | 0.999 | 10.09x | 25.6x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276` | 224,940 | 1,623.3 | 1,662,243 | 1,968,057 | 38,390 | 23.1 | `weight_read` | `a100_sxm_80gb-x272-expert` | 207.1 | 1,880,328 | 219.3 | 1.001 | 7.84x | 9.5x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 3,075.1 | 3,148,942 | 723,180 | 70,623 | 22.4 | `compute` | `a100_sxm_80gb-x672-expert` | 288.7 | 4,719,349 | 362.3 | 0.999 | 10.65x | 16.2x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 566.8 | 2,321,735 | 2,429,123 | 48,796 | 21.0 | `weight_read` | `a100_sxm_80gb-x335-expert` | 146.5 | 2,328,220 | 91.8 | 1.001 | 3.87x | 4.4x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,240.5 | 5,081,113 | 723,180 | 92,673 | 18.2 | `compute` | `a100_sxm_80gb-x672-expert` | 214.5 | 4,719,349 | 121.7 | 0.999 | 5.78x | 6.7x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-HBMKV-array-hw-tensor-x73` | 59,495 | array | HBM | 505,615 |
| 2 | `ROM-N6-native-HBMKV-array-hw-tensor-x87` | 70,905 | array | HBM | 606,473 |
| 4-16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 101,060 | array | HBM | 873,027 |
| 32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x128` | 104,320 | array | HBM | 901,843 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x138` | 112,470 | array | HBM | 973,885 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x207` | 168,705 | array | HBM | 1,470,971 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 185,005 | array | HBM | 1,615,054 |
| 4096 | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 369,800 | wafer | HBM | 475,358 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | rom | 73, 87, 89, 95, 104, 113, 124, 125, 127, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | sram | 73, 87, 89, 95, 104, 113, 128, 129, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | rom | 169, 170, 182, 204, 205, 227, 246, 328, 340, 371, 376, 378 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | sram | 169, 170, 182, 205, 220, 221, 227, 246, 328, 340 |

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

- **0 of 4,631 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 33%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 110 | 0 | 67.4% | 81.0% | 0.392 | 54% |
| gpu | wafer (>=40,000 mm2) | 1,600 | 0 | 64.7% | 79.7% | 0.386 | 68% |
| rom | large array (5,000-40,000 mm2) | 360 | 0 | 19.1% | 32.7% | 0.163 | 94% |
| rom | wafer (>=40,000 mm2) | 2,561 | 0 | 22.4% | 35.2% | 0.176 | 95% |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 101,060 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 0.805809 | 14,085.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-tensor` | 17.208382 | 19,143.0 | link_latency | 21.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 101,060 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 0.406374 | 14,085.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-tensor` | 9.908975 | 19,422.2 | link_latency | 24.38x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 101,060 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 0.206656 | 14,085.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-tensor` | 6.249303 | 19,804.1 | link_latency | 30.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 101,060 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 0.106797 | 14,085.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-hybrid` | 4.654375 | 32,366.5 | weight_read | 41.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 101,060 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill` | 0.056868 | 14,085.0 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x122-hybrid` | 3.014039 | 32,366.5 | weight_read | 53.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 101,875 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x125-romfill` | 0.032518 | 14,275.3 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x123-hybrid` | 1.946415 | 33,745.5 | weight_read | 59.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 224,940 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 0.034781 | 31,694.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid` | 2.055866 | 73,043.1 | weight_read | 59.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.027215 | 37,961.8 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid` | 1.227941 | 95,551.7 | weight_read | 30.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.022427 | 70,622.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-expert` | 0.362312 | 107,107.9 | weight_read | 16.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.018239 | 92,672.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-expert` | 0.121650 | 106,880.2 | weight_read | 6.67x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 8,192 | 552 B | 307.5 GB | 4.46 | 0.012 GB | 0.010 GB | 1,091.7 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 92,450 | 59,340.4 | wafer-pipeline | 5,952.2 | wafer-hybrid | 9.97x | 5,585.2 | pipeline | 1,106.4 | tensor | 5.05x | 10.62x | 5.38x | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 3 | 138,675 | 61,962.8 | wafer-pipeline | 5,956.2 | wafer-hybrid | 10.40x | 6,429.5 | pipeline | 1,132.9 | tensor | 5.68x | 9.64x | 5.26x | 0.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 184,900 | 63,148.4 | wafer-pipeline | 5,952.6 | wafer-hybrid | 10.61x | 6,955.3 | pipeline | 1,146.7 | tensor | 6.07x | 9.08x | 5.19x | 0.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 6 | 277,350 | 64,380.2 | wafer-pipeline | 5,945.4 | wafer-hybrid | 10.83x | 7,574.7 | pipeline | 843.0 | tensor | 8.99x | 8.50x | 7.05x | 0.83x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 369,800 | 65,014.3 | wafer-pipeline | 5,938.3 | wafer-hybrid | 10.95x | 7,927.7 | pipeline | 846.7 | tensor | 9.36x | 8.20x | 7.01x | 0.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 12 | 554,700 | 65,661.0 | wafer-pipeline | 5,923.9 | wafer-hybrid | 11.08x | 8,315.2 | pipeline | 850.5 | tensor | 9.78x | 7.90x | 6.96x | 0.88x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.51x to 0.88x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x128 | 104,320 | 14,283.7 | 457,078.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-tensor | 104,076 | 1.00x | tensor | 824.13 | 1,115.0 | 1,115.0 | link_latency | 12.81x | 29.05x | 114.40x | 12.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x73 | 59,495 | 9,525.1 | 9,525.1 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-tensor | 59,472 | 1.00x | tensor | 819.35 | 1,064.8 | 1,064.8 | link_latency | 8.95x | 1.06x | 76.29x | 8.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x128 | 104,320 | 14,283.7 | 457,078.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-tensor | 104,076 | 1.00x | tensor | 923.46 | 982.7 | 1,965.4 | link_latency | 14.54x | 29.05x | 114.40x | 14.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x73 | 59,495 | 7,817.4 | 15,634.9 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-tensor | 59,472 | 1.00x | tensor | 913.90 | 933.6 | 1,867.2 | link_latency | 8.37x | 1.74x | 62.61x | 8.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x128 | 104,320 | 14,283.7 | 457,078.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-tensor | 104,076 | 1.00x | tensor | 1,122.11 | 794.9 | 3,179.4 | link_latency | 17.97x | 29.05x | 114.40x | 17.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x73 | 59,495 | 5,754.2 | 23,016.7 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-tensor | 59,472 | 1.00x | tensor | 1,103.00 | 749.9 | 2,999.8 | link_latency | 7.67x | 2.56x | 46.09x | 7.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x128 | 104,320 | 14,283.7 | 457,078.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-hybrid | 104,076 | 1.00x | hybrid | 443.76 | 686.3 | 10,981.0 | weight_read | 20.81x | 29.05x | 114.40x | 20.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x73 | 59,495 | 3,766.2 | 30,129.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-hybrid | 59,472 | 1.00x | hybrid | 426.68 | 702.1 | 6,318.8 | weight_read | 5.36x | 3.35x | 30.16x | 5.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x128 | 104,320 | 14,283.7 | 457,078.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-hybrid | 104,076 | 1.00x | hybrid | 443.76 | 686.3 | 10,981.0 | weight_read | 20.81x | 29.05x | 114.40x | 20.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x73 | 59,495 | 2,401.4 | 45,626.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-hybrid | 59,472 | 1.00x | hybrid | 434.81 | 589.9 | 9,438.7 | weight_read | 4.07x | 4.83x | 19.23x | 4.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x128 | 104,320 | 14,283.7 | 457,078.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-hybrid | 104,076 | 1.00x | hybrid | 457.07 | 551.6 | 17,651.2 | weight_read | 25.90x | 25.90x | 114.40x | 25.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x73 | 59,495 | 1,444.8 | 46,233.3 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-hybrid | 59,472 | 1.00x | hybrid | 453.38 | 434.4 | 13,899.3 | weight_read | 3.33x | 3.33x | 11.57x | 3.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 14,020.1 | 1,191,709.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 514.43 | 590.7 | 37,806.8 | weight_read | 23.73x | 28.49x | 112.29x | 23.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x73 | 59,495 | 729.5 | 46,687.0 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-hybrid | 59,472 | 1.00x | hybrid | 490.51 | 288.3 | 18,452.3 | weight_read | 2.53x | 2.53x | 5.84x | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 5,448.7 | 1,394,859.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 620.23 | 304.0 | 77,814.6 | weight_read | 17.93x | 17.93x | 43.64x | 17.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x73 | 59,495 | 184.0 | 47,114.0 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-expert | 59,472 | 1.00x | expert | 1,465.34 | 136.5 | 34,954.9 | weight_read | 1.35x | 1.35x | 2.73x | 1.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3,075.1 | 3,148,941.7 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-expert | 555,072 | 1.00x | expert | 949.37 | 288.7 | 295,623.1 | weight_read | 10.65x | 10.65x | 28.99x | 10.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x73 | 59,495 | 46.1 | 47,187.3 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-expert | 59,472 | 1.00x | expert | 4,174.16 | 98.2 | 100,539.3 | weight_read | 0.47x | 0.47x | 1.87x | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,240.5 | 5,081,112.8 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-expert | 555,072 | 1.00x | expert | 2,110.30 | 214.5 | 878,586.3 | weight_read | 5.78x | 5.78x | 26.47x | 5.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x73 | 59,495 | 11.5 | 47,205.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-hybrid | 59,472 | 1.00x | hybrid | 5,169.78 | 35.6 | 145,622.5 | weight_read | 0.32x | 0.32x | 1.26x | 0.32x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 6,608 | 126.1 | 711.8 | — | tensor | 407.17 | 29.0% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 36 | 29,736 | 125.0 | 961.4 | 656.0 | tensor | 810.61 | 77.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 37 | 30,562 | 125.0 | 966.9 | 669.1 | tensor | 810.61 | 78.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 56 | 46,256 | 124.9 | 1,033.7 | 704.5 | tensor | 816.23 | 84.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 72 | 59,472 | 124.9 | 1,064.8 | 702.1 | tensor | 819.35 | 87.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 86 | 71,036 | 124.9 | 1,083.1 | 688.6 | tensor | 821.34 | 89.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 88 | 72,688 | 124.9 | 1,085.6 | 699.7 | tensor | 821.34 | 89.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 94 | 77,644 | 124.9 | 1,091.5 | 688.4 | tensor | 822.08 | 89.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 103 | 85,078 | 124.9 | 1,099.5 | 692.7 | tensor | 822.71 | 90.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 111 | 91,686 | 124.9 | 1,105.6 | 691.8 | tensor | 823.25 | 91.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 112 | 92,512 | 124.9 | 1,106.4 | 696.1 | tensor | 823.25 | 91.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 122 | 100,772 | 124.9 | 1,112.4 | 671.2 | tensor | 824.13 | 91.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 123 | 101,598 | 124.9 | 1,113.1 | 675.0 | tensor | 824.13 | 91.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 125 | 103,250 | 124.9 | 1,114.3 | 682.6 | tensor | 824.13 | 91.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 126 | 104,076 | 124.9 | 1,115.0 | 686.3 | tensor | 824.13 | 91.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 127 | 104,902 | 124.9 | 1,115.6 | 690.1 | tensor | 824.13 | 91.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 136 | 112,336 | 124.9 | 1,120.3 | 692.6 | tensor | 824.49 | 92.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 160 | 132,160 | 124.9 | 1,130.2 | 689.1 | tensor | 825.36 | 93.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 167 | 137,942 | 124.9 | 1,132.6 | 685.2 | tensor | 825.59 | 93.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 168 | 138,768 | 124.9 | 1,132.9 | 688.0 | tensor | 825.59 | 93.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 177 | 146,202 | 124.9 | 1,135.5 | 667.8 | tensor | 826.00 | 93.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 180 | 148,680 | 124.9 | 1,136.4 | 675.5 | tensor | 826.00 | 93.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 185 | 152,810 | 124.9 | 1,137.7 | 667.4 | tensor | 826.18 | 94.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 201 | 166,026 | 124.9 | 1,141.7 | 666.6 | tensor | 826.49 | 94.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 202 | 166,852 | 124.9 | 1,142.0 | 668.8 | tensor | 826.49 | 94.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 204 | 168,504 | 124.9 | 1,142.5 | 673.3 | tensor | 826.49 | 94.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 217 | 179,242 | 124.9 | 1,145.2 | 665.5 | tensor | 826.76 | 94.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 218 | 180,068 | 124.9 | 1,145.4 | 667.6 | tensor | 826.76 | 94.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 224 | 185,024 | 124.9 | 1,146.7 | 680.0 | tensor | 826.76 | 94.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 243 | 200,718 | 124.9 | 1,149.9 | 667.4 | tensor | 827.10 | 95.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 272 | 224,672 | 124.9 | 1,154.1 | 673.3 | tensor | 827.38 | 95.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 324 | 267,624 | 124.9 | 842.4 | 661.3 | tensor | 1,152.67 | 97.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 335 | 276,710 | 124.9 | 842.9 | 665.4 | tensor | 1,152.73 | 97.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 336 | 277,536 | 124.9 | 843.0 | 666.7 | tensor | 1,152.73 | 97.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 354 | 292,404 | 124.9 | 843.7 | 659.3 | tensor | 1,152.89 | 97.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 366 | 302,316 | 124.9 | 844.2 | 664.3 | tensor | 1,152.93 | 97.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 371 | 306,446 | 124.9 | 844.4 | 660.8 | tensor | 1,152.98 | 97.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 373 | 308,098 | 124.9 | 844.4 | 663.2 | tensor | 1,152.98 | 97.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 379 | 313,054 | 124.9 | 844.7 | 661.0 | tensor | 1,153.02 | 97.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 380 | 313,880 | 124.9 | 844.7 | 662.1 | tensor | 1,153.02 | 97.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 448 | 370,048 | 124.9 | 846.7 | 666.7 | tensor | 1,153.32 | 97.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 616 | 508,816 | 124.9 | 849.9 | 666.7 | tensor | 1,153.80 | 98.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 672 | 555,072 | 124.9 | 850.5 | 666.7 | tensor | 1,153.90 | 98.1% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x221 | DeepSeek-V4.1-Flash-engram-hbm | 221 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x182 | DeepSeek-V4.1-Flash-engram-hbm | 182 | tensor | rom_package_ucie | rom_board_serdes | 160 | 109.00 us | 917.5 tok/s | 9,174.6 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 46 on rom_board_serdes (traversals 13.2) = 106.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x220 | DeepSeek-V4.1-Flash-engram-hbm | 220 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x221 | DeepSeek-V4.1-Flash-engram-hbm | 221 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x4 | DeepSeek-V4.1-Flash-engram-hbm | 4 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x169 | DeepSeek-V4.1-Flash-engram-hbm | 169 | tensor | nvlink3 | infiniband_hdr | 160 | 825.80 us | 121.1 tok/s | 1,210.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 418.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4.1-Flash-engram-hbm | 4 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.91 us | 581.7 tok/s | 5,817.1 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 17.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hybrid-x205 | DeepSeek-V4.1-Flash-engram-hbm | 205 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | DeepSeek-V4.1-Flash-engram-hbm | 4 | hybrid | on_wafer | rom_wafer_serdes | 83 | 154.31 us | 648.1 tok/s | 6,480.7 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-pipeline-x129 | DeepSeek-V4.1-Flash-engram-hbm | 129 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x89 | DeepSeek-V4.1-Flash-engram-hbm | 89 | tensor | rom_package_ucie | rom_board_serdes | 160 | 73.77 us | 1,355.6 tok/s | 13,556.2 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 23 on rom_board_serdes (traversals 8.8) = 71.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x128 | DeepSeek-V4.1-Flash-engram-hbm | 128 | hybrid | rom_package_ucie | rom_board_serdes | 111 | 5.34 us | 18,736.6 tok/s | 187,365.7 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 31 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-pipeline-x128 | DeepSeek-V4.1-Flash-engram-hbm | 128 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-tensor-x73 | DeepSeek-V4.1-Flash-engram-hbm | 73 | tensor | nvlink3 | infiniband_hdr | 160 | 820.44 us | 121.9 tok/s | 1,218.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 413.27 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x95 | DeepSeek-V4.1-Flash-engram-hbm | 95 | hybrid | nvlink3 | infiniband_hdr | 91 | 434.00 us | 230.4 tok/s | 2,304.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 26.84 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | hybrid | on_wafer | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x8-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 17.74 us | 5,637.3 tok/s | 56,373.2 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 17.74 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x8-tensor | DeepSeek-V4.1-Flash-engram-hbm | 8 | tensor | nvlink3 | infiniband_hdr | 80 | 407.17 us | 245.6 tok/s | 2,456.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x8-expert | DeepSeek-V4.1-Flash-engram-hbm | 8 | expert | nvlink3 | infiniband_hdr | 160 | 609.22 us | 164.1 tok/s | 1,641.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x point_to_point span 2 on nvlink3 (traversals 1.0) = 202.05 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x36-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 36 | pipeline | nvlink3 | infiniband_hdr | 35 | 88.32 us | 1,132.3 tok/s | 11,322.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.56 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x36-tensor | DeepSeek-V4.1-Flash-engram-hbm | 36 | tensor | nvlink3 | infiniband_hdr | 160 | 810.61 us | 123.4 tok/s | 1,233.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 403.44 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x36-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 36 | hybrid | nvlink3 | infiniband_hdr | 84 | 416.93 us | 239.9 tok/s | 2,398.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x36-expert | DeepSeek-V4.1-Flash-engram-hbm | 36 | expert | nvlink3 | infiniband_hdr | 160 | 569.65 us | 175.5 tok/s | 1,755.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.79 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 167.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x37-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.85 us | 1,100.7 tok/s | 11,007.1 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 81.09 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x37-tensor | DeepSeek-V4.1-Flash-engram-hbm | 37 | tensor | nvlink3 | infiniband_hdr | 160 | 810.61 us | 123.4 tok/s | 1,233.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 403.44 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x37-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 37 | hybrid | nvlink3 | infiniband_hdr | 84 | 416.93 us | 239.9 tok/s | 2,398.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x37-expert | DeepSeek-V4.1-Flash-engram-hbm | 37 | expert | nvlink3 | infiniband_hdr | 160 | 569.51 us | 175.6 tok/s | 1,755.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.79 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 167.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash-engram-hbm | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-expert | DeepSeek-V4.1-Flash-engram-hbm | 56 | expert | nvlink3 | infiniband_hdr | 160 | 566.93 us | 176.4 tok/s | 1,763.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 72 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 72 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 72 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x72-expert | DeepSeek-V4.1-Flash-engram-hbm | 72 | expert | nvlink3 | infiniband_hdr | 160 | 565.93 us | 176.7 tok/s | 1,767.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.80 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.13 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 86 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-tensor | DeepSeek-V4.1-Flash-engram-hbm | 86 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 86 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-expert | DeepSeek-V4.1-Flash-engram-hbm | 86 | expert | nvlink3 | infiniband_hdr | 160 | 565.40 us | 176.9 tok/s | 1,768.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.72 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x88-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 88 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x88-tensor | DeepSeek-V4.1-Flash-engram-hbm | 88 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x88-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 88 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x88-expert | DeepSeek-V4.1-Flash-engram-hbm | 88 | expert | nvlink3 | infiniband_hdr | 160 | 565.29 us | 176.9 tok/s | 1,769.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.65 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x94-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 94 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x94-tensor | DeepSeek-V4.1-Flash-engram-hbm | 94 | tensor | nvlink3 | infiniband_hdr | 160 | 822.08 us | 121.6 tok/s | 1,216.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 414.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x94-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 94 | hybrid | nvlink3 | infiniband_hdr | 91 | 434.00 us | 230.4 tok/s | 2,304.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 26.84 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x94-expert | DeepSeek-V4.1-Flash-engram-hbm | 94 | expert | nvlink3 | infiniband_hdr | 160 | 565.14 us | 176.9 tok/s | 1,769.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.65 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.49 us |
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
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x123-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 123 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x123-tensor | DeepSeek-V4.1-Flash-engram-hbm | 123 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x123-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 123 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x123-expert | DeepSeek-V4.1-Flash-engram-hbm | 123 | expert | nvlink3 | infiniband_hdr | 160 | 564.48 us | 177.2 tok/s | 1,771.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.00 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x125-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 125 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x125-tensor | DeepSeek-V4.1-Flash-engram-hbm | 125 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x125-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 125 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x125-expert | DeepSeek-V4.1-Flash-engram-hbm | 125 | expert | nvlink3 | infiniband_hdr | 160 | 564.45 us | 177.2 tok/s | 1,771.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.97 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 126 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-tensor | DeepSeek-V4.1-Flash-engram-hbm | 126 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 126 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x126-expert | DeepSeek-V4.1-Flash-engram-hbm | 126 | expert | nvlink3 | infiniband_hdr | 160 | 564.44 us | 177.2 tok/s | 1,771.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x127-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 127 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x127-tensor | DeepSeek-V4.1-Flash-engram-hbm | 127 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x127-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 127 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x127-expert | DeepSeek-V4.1-Flash-engram-hbm | 127 | expert | nvlink3 | infiniband_hdr | 160 | 564.43 us | 177.2 tok/s | 1,771.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 136 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-tensor | DeepSeek-V4.1-Flash-engram-hbm | 136 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 136 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-expert | DeepSeek-V4.1-Flash-engram-hbm | 136 | expert | nvlink3 | infiniband_hdr | 160 | 564.27 us | 177.2 tok/s | 1,772.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.85 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x160-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 160 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x160-tensor | DeepSeek-V4.1-Flash-engram-hbm | 160 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x160-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 160 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x160-expert | DeepSeek-V4.1-Flash-engram-hbm | 160 | expert | nvlink3 | infiniband_hdr | 160 | 563.99 us | 177.3 tok/s | 1,773.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.36 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x167-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 167 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x167-tensor | DeepSeek-V4.1-Flash-engram-hbm | 167 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x167-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 167 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x167-expert | DeepSeek-V4.1-Flash-engram-hbm | 167 | expert | nvlink3 | infiniband_hdr | 160 | 563.94 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.36 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 168 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-tensor | DeepSeek-V4.1-Flash-engram-hbm | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 168 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-expert | DeepSeek-V4.1-Flash-engram-hbm | 168 | expert | nvlink3 | infiniband_hdr | 160 | 563.91 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 177 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-tensor | DeepSeek-V4.1-Flash-engram-hbm | 177 | tensor | nvlink3 | infiniband_hdr | 160 | 826.00 us | 121.1 tok/s | 1,210.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 418.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 177 | hybrid | nvlink3 | infiniband_hdr | 102 | 460.84 us | 217.0 tok/s | 2,170.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 53.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x177-expert | DeepSeek-V4.1-Flash-engram-hbm | 177 | expert | nvlink3 | infiniband_hdr | 160 | 563.84 us | 177.4 tok/s | 1,773.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.33 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x180-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 180 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x180-tensor | DeepSeek-V4.1-Flash-engram-hbm | 180 | tensor | nvlink3 | infiniband_hdr | 160 | 826.00 us | 121.1 tok/s | 1,210.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 418.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x180-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 180 | hybrid | nvlink3 | infiniband_hdr | 102 | 460.84 us | 217.0 tok/s | 2,170.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 53.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x180-expert | DeepSeek-V4.1-Flash-engram-hbm | 180 | expert | nvlink3 | infiniband_hdr | 160 | 563.82 us | 177.4 tok/s | 1,773.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.33 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x185-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 185 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x185-tensor | DeepSeek-V4.1-Flash-engram-hbm | 185 | tensor | nvlink3 | infiniband_hdr | 160 | 826.18 us | 121.0 tok/s | 1,210.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 419.01 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x185-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 185 | hybrid | nvlink3 | infiniband_hdr | 103 | 463.28 us | 215.9 tok/s | 2,158.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 56.11 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x185-expert | DeepSeek-V4.1-Flash-engram-hbm | 185 | expert | nvlink3 | infiniband_hdr | 160 | 563.77 us | 177.4 tok/s | 1,773.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.31 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.46 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x201-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 201 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x201-tensor | DeepSeek-V4.1-Flash-engram-hbm | 201 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x201-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 201 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x201-expert | DeepSeek-V4.1-Flash-engram-hbm | 201 | expert | nvlink3 | infiniband_hdr | 160 | 563.66 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 202 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-tensor | DeepSeek-V4.1-Flash-engram-hbm | 202 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 202 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-expert | DeepSeek-V4.1-Flash-engram-hbm | 202 | expert | nvlink3 | infiniband_hdr | 160 | 563.66 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.37 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 204 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-tensor | DeepSeek-V4.1-Flash-engram-hbm | 204 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 204 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-expert | DeepSeek-V4.1-Flash-engram-hbm | 204 | expert | nvlink3 | infiniband_hdr | 160 | 563.65 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x217-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 217 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x217-tensor | DeepSeek-V4.1-Flash-engram-hbm | 217 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x217-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 217 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x217-expert | DeepSeek-V4.1-Flash-engram-hbm | 217 | expert | nvlink3 | infiniband_hdr | 160 | 563.57 us | 177.4 tok/s | 1,774.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.27 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.31 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x218-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 218 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x218-tensor | DeepSeek-V4.1-Flash-engram-hbm | 218 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x218-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 218 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x218-expert | DeepSeek-V4.1-Flash-engram-hbm | 218 | expert | nvlink3 | infiniband_hdr | 160 | 563.57 us | 177.4 tok/s | 1,774.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.27 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.30 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash-engram-hbm | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-expert | DeepSeek-V4.1-Flash-engram-hbm | 224 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 243 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-tensor | DeepSeek-V4.1-Flash-engram-hbm | 243 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 243 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-expert | DeepSeek-V4.1-Flash-engram-hbm | 243 | expert | nvlink3 | infiniband_hdr | 160 | 563.45 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 272 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-tensor | DeepSeek-V4.1-Flash-engram-hbm | 272 | tensor | nvlink3 | infiniband_hdr | 160 | 827.38 us | 120.9 tok/s | 1,208.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 420.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 272 | hybrid | nvlink3 | infiniband_hdr | 113 | 487.67 us | 205.1 tok/s | 2,050.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 80.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-expert | DeepSeek-V4.1-Flash-engram-hbm | 272 | expert | nvlink3 | infiniband_hdr | 160 | 563.33 us | 177.5 tok/s | 1,775.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.21 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 324 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-tensor | DeepSeek-V4.1-Flash-engram-hbm | 324 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.67 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 41 on infiniband_hdr (traversals 4.0) = 745.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 324 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-expert | DeepSeek-V4.1-Flash-engram-hbm | 324 | expert | nvlink3 | infiniband_hdr | 160 | 563.19 us | 177.6 tok/s | 1,775.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.18 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.01 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 335 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-tensor | DeepSeek-V4.1-Flash-engram-hbm | 335 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 335 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-expert | DeepSeek-V4.1-Flash-engram-hbm | 335 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 336 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-tensor | DeepSeek-V4.1-Flash-engram-hbm | 336 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 336 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-expert | DeepSeek-V4.1-Flash-engram-hbm | 336 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x354-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 354 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x354-tensor | DeepSeek-V4.1-Flash-engram-hbm | 354 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.89 us | 86.7 tok/s | 867.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 745.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x354-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 354 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x354-expert | DeepSeek-V4.1-Flash-engram-hbm | 354 | expert | nvlink3 | infiniband_hdr | 160 | 563.12 us | 177.6 tok/s | 1,775.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.96 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x366-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 366 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x366-tensor | DeepSeek-V4.1-Flash-engram-hbm | 366 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.93 us | 86.7 tok/s | 867.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 745.77 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x366-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 366 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x366-expert | DeepSeek-V4.1-Flash-engram-hbm | 366 | expert | nvlink3 | infiniband_hdr | 160 | 563.10 us | 177.6 tok/s | 1,775.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x371-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 371 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x371-tensor | DeepSeek-V4.1-Flash-engram-hbm | 371 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.98 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 745.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x371-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 371 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x371-expert | DeepSeek-V4.1-Flash-engram-hbm | 371 | expert | nvlink3 | infiniband_hdr | 160 | 563.09 us | 177.6 tok/s | 1,775.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x373-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 373 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x373-tensor | DeepSeek-V4.1-Flash-engram-hbm | 373 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.98 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 745.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x373-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 373 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x373-expert | DeepSeek-V4.1-Flash-engram-hbm | 373 | expert | nvlink3 | infiniband_hdr | 160 | 563.08 us | 177.6 tok/s | 1,775.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.16 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x379-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 379 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x379-tensor | DeepSeek-V4.1-Flash-engram-hbm | 379 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.02 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 745.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x379-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 379 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x379-expert | DeepSeek-V4.1-Flash-engram-hbm | 379 | expert | nvlink3 | infiniband_hdr | 160 | 563.07 us | 177.6 tok/s | 1,776.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.15 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 380 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-tensor | DeepSeek-V4.1-Flash-engram-hbm | 380 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.02 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 745.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 380 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-expert | DeepSeek-V4.1-Flash-engram-hbm | 380 | expert | nvlink3 | infiniband_hdr | 160 | 563.07 us | 177.6 tok/s | 1,776.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.15 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 448 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-tensor | DeepSeek-V4.1-Flash-engram-hbm | 448 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.32 us | 86.7 tok/s | 867.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 746.15 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 448 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-expert | DeepSeek-V4.1-Flash-engram-hbm | 448 | expert | nvlink3 | infiniband_hdr | 160 | 562.97 us | 177.6 tok/s | 1,776.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.13 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.84 us |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill | 101,060 | 13,891.0 | 0.137 | 13,891.0 (101,060) | 5,952.2 (92,450) | 0.43x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill | 101,060 | 13,891.0 | 0.137 | 13,891.0 (101,060) | 5,952.2 (92,450) | 0.43x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill | 101,060 | 13,891.0 | 0.137 | 13,891.0 (101,060) | 5,818.8 (92,450) | 0.42x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill | 101,060 | 13,891.0 | 0.137 | 13,891.0 (101,060) | 5,818.0 (138,675) | 0.42x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x124-romfill | 101,060 | 13,891.0 | 0.137 | 13,891.0 (101,060) | 5,597.7 (138,675) | 0.40x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x125-romfill | 101,875 | 13,718.6 | 0.135 | 13,718.6 (101,875) | 5,435.1 (277,350) | 0.40x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 14,020.1 | 0.062 | 14,020.1 (224,940) | 5,156.4 (369,800) | 0.37x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 5,448.7 | 0.020 | 5,448.7 (277,100) | 4,513.3 (277,350) | 0.83x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | wafer | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3,075.1 | 0.006 | 1,623.3 (224,940) | 3,075.1 (554,700) | 1.89x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,240.5 | 0.002 | 566.8 (277,100) | 1,240.5 (554,700) | 2.19x | compute |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | sram | 607,862.2 | 28,795.8 | 28,795.8 | 21.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | sram | 607,862.2 | 28,795.8 | 28,795.8 | 21.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | sram | 607,862.2 | 28,795.8 | 36,936.3 | 21.11x | 1.28x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | sram | 607,862.2 | 28,795.8 | 58,599.9 | 21.11x | 2.04x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | sram | 607,862.2 | 28,795.8 | 93,565.4 | 21.11x | 3.25x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | sram | 607,862.2 | 28,795.8 | 136,743.7 | 21.11x | 4.75x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | sram | 652,882.6 | 28,819.6 | 191,793.5 | 22.65x | 6.65x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | sram | 1,198,507.0 | 28,965.6 | 472,336.4 | 41.38x | 16.31x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | sram | 2,414,298.6 | 29,002.3 | 882,529.1 | 83.24x | 30.43x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | sram | 5,081,112.8 | 29,011.5 | 1,120,209.9 | 175.14x | 38.61x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | rom | 3,077,785.2 | 49,515.1 | 49,515.1 | 62.16x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | rom | 3,077,785.2 | 49,515.1 | 49,515.1 | 62.16x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | rom | 3,077,785.2 | 49,515.1 | 49,515.1 | 62.16x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | rom | 3,077,785.2 | 49,515.1 | 58,823.7 | 62.16x | 1.19x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | rom | 3,077,785.2 | 49,515.1 | 93,929.5 | 62.16x | 1.90x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | rom | 3,077,785.2 | 49,515.1 | 137,277.3 | 62.16x | 2.77x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | rom | 3,077,785.2 | 49,585.4 | 244,116.2 | 62.07x | 4.92x | compute | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | rom | 3,077,785.2 | 50,019.3 | 669,018.3 | 61.53x | 13.38x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | rom | 3,148,941.7 | 50,128.9 | 987,318.0 | 62.82x | 19.70x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | rom | 3,261,213.3 | 50,156.4 | 1,120,209.9 | 65.02x | 22.33x | compute | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,077,785.2 | 5.549 | compute | 5.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 1.00 | 49,515.1 | 1.071 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.73 | 1.00 | 49,515.1 | 1.071 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,077,785.2 | 5.549 | compute | 5.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 1.00 | 49,515.1 | 1.071 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.73 | 1.00 | 49,515.1 | 1.071 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,077,785.2 | 5.549 | compute | 5.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 1.00 | 49,515.1 | 1.071 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x36-perregion | 29,340 | 1.00 | 1.43 | 36,936.3 | 1.259 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.73 | 1.00 | 49,515.1 | 1.071 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,077,785.2 | 5.549 | compute | 5.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 1.00 | 49,515.1 | 1.071 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x36-perregion | 29,340 | 1.00 | 1.99 | 58,599.9 | 1.997 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x36-perregion-romfill | 29,340 | 1.01 | 1.99 | 58,823.7 | 2.005 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,077,785.2 | 5.549 | compute | 5.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 1.00 | 49,515.1 | 1.071 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x36-perregion | 29,340 | 1.00 | 2.54 | 93,565.4 | 3.189 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x36-perregion-romfill | 29,340 | 1.01 | 2.54 | 93,929.5 | 3.201 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,077,785.2 | 5.549 | compute | 5.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 1.00 | 49,515.1 | 1.071 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x36-perregion | 29,340 | 1.00 | 3.49 | 136,743.7 | 4.661 | weight_read | 0.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-tensor-x36-perregion-romfill | 29,340 | 1.01 | 3.49 | 137,277.3 | 4.679 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 1.00 | 1.00 | 652,882.6 | 4.712 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,077,785.2 | 5.549 | compute | 4.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,819.6 | 0.623 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 1.12 | 49,585.4 | 1.073 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.92 | 191,793.5 | 4.149 | weight_read | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.73 | 4.92 | 244,116.2 | 5.281 | link_latency | 0.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hw-hybrid-x207 | 168,705 | 1.00 | 1.00 | 1,198,507.0 | 7.104 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,077,785.2 | 5.549 | compute | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,965.6 | 0.627 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 4.49 | 50,019.3 | 1.082 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 10.96 | 472,336.4 | 10.218 | weight_read | 0.39x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.73 | 10.96 | 669,018.3 | 14.473 | weight_read | 0.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 2,414,298.6 | 6.529 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,148,941.7 | 5.677 | compute | 1.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 17.96 | 29,002.3 | 0.627 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 17.96 | 50,128.9 | 1.084 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 28.90 | 882,529.1 | 19.092 | weight_read | 0.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.73 | 28.90 | 987,318.0 | 21.359 | kv_read | 0.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 5,081,112.8 | 9.160 | compute | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 3,261,213.3 | 5.879 | compute | 0.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 71.86 | 29,011.5 | 0.628 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.73 | 71.86 | 50,156.4 | 1.085 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 88.68 | 1,120,209.9 | 24.234 | kv_read | 0.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.73 | 88.68 | 1,120,209.9 | 24.234 | kv_read | 0.22x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 162 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 171 | 1.50 | 1.004 | 1.043 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 171 | 5.99 | 1.040 | 1.767 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 36 | 113.78 | 2.133 | 6.729 | 3.15x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 72 | 5.80 | 5.07 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 72 | 11.04 | 7.44 | 1.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 72 | 20.13 | 10.51 | 1.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 72 | 33.87 | 14.63 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 72 | 50.23 | 19.44 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 72 | 63.41 | 24.46 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 72 | 69.62 | 28.93 | 2.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 72 | 71.63 | 33.19 | 2.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 72 | 71.67 | 33.37 | 2.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 72 | 71.67 | 33.37 | 2.15x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 88 | 5.83 | 5.21 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 88 | 11.20 | 7.82 | 1.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 88 | 20.68 | 11.05 | 1.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 88 | 35.66 | 15.70 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 88 | 54.89 | 21.13 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 88 | 72.51 | 26.94 | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 88 | 82.58 | 32.22 | 2.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 88 | 86.82 | 37.35 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 88 | 86.91 | 37.57 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 88 | 86.91 | 37.57 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 94 | 11.24 | 7.94 | 1.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 94 | 20.85 | 11.23 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 94 | 36.19 | 16.05 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 94 | 56.34 | 21.70 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 94 | 75.50 | 27.77 | 2.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 94 | 87.07 | 33.34 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 94 | 92.34 | 38.79 | 2.38x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 94 | 92.45 | 39.02 | 2.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 94 | 92.45 | 39.02 | 2.37x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 123 | 5.88 | 5.40 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 123 | 11.39 | 8.46 | 1.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 123 | 21.42 | 11.95 | 1.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 123 | 38.13 | 17.53 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 123 | 61.81 | 24.02 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 123 | 87.44 | 31.31 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 123 | 106.20 | 38.13 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 123 | 117.34 | 44.98 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 123 | 117.65 | 45.27 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 123 | 117.65 | 45.27 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 125 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 125 | 11.40 | 8.49 | 1.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 125 | 21.45 | 11.99 | 1.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 125 | 38.23 | 17.62 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 125 | 62.11 | 24.16 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 125 | 88.13 | 31.52 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 125 | 107.37 | 38.43 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 125 | 118.96 | 45.37 | 2.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 126 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 126 | 11.40 | 8.50 | 1.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 126 | 21.47 | 12.02 | 1.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 126 | 38.29 | 17.66 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 126 | 62.26 | 24.23 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 126 | 88.47 | 31.63 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 126 | 107.95 | 38.58 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 126 | 119.76 | 45.56 | 2.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 126 | 120.09 | 45.86 | 2.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 126 | 120.09 | 45.86 | 2.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 127 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 127 | 11.41 | 8.52 | 1.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 127 | 21.48 | 12.04 | 1.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 127 | 38.34 | 17.71 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 127 | 62.41 | 24.30 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 127 | 88.81 | 31.73 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 127 | 108.52 | 38.72 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 127 | 120.56 | 45.76 | 2.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 127 | 120.90 | 46.05 | 2.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 127 | 120.90 | 46.05 | 2.63x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 160 | 5.91 | 5.52 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 160 | 11.51 | 8.95 | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 160 | 21.87 | 12.70 | 1.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 160 | 39.68 | 18.92 | 2.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 160 | 66.41 | 26.26 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 160 | 98.31 | 34.86 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 160 | 125.31 | 43.11 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 160 | 144.97 | 51.54 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 160 | 145.59 | 51.90 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 160 | 145.59 | 51.90 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 167 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 167 | 11.53 | 9.02 | 1.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 167 | 21.93 | 12.83 | 1.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 167 | 39.90 | 19.14 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 167 | 67.09 | 26.63 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 167 | 99.98 | 35.45 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 167 | 128.39 | 43.94 | 2.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 167 | 149.67 | 52.65 | 2.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 167 | 150.36 | 53.03 | 2.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 167 | 150.36 | 53.03 | 2.84x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 180 | 5.92 | 5.57 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 180 | 11.55 | 9.16 | 1.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 180 | 22.04 | 13.06 | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 180 | 40.27 | 19.50 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 180 | 68.23 | 27.28 | 2.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 180 | 102.82 | 36.51 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 180 | 133.73 | 45.42 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 180 | 157.99 | 54.63 | 2.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 180 | 158.81 | 55.02 | 2.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 180 | 158.81 | 55.02 | 2.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 185 | 11.56 | 9.20 | 1.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 185 | 22.07 | 13.14 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 185 | 40.40 | 19.63 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 185 | 68.63 | 27.52 | 2.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 185 | 103.84 | 36.90 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 185 | 135.66 | 45.96 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 185 | 161.05 | 55.36 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 185 | 161.92 | 55.76 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 185 | 161.92 | 55.76 | 2.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 201 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 201 | 11.59 | 9.35 | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 201 | 22.18 | 13.41 | 1.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 201 | 40.77 | 20.02 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 201 | 69.80 | 28.26 | 2.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 201 | 106.83 | 38.10 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 201 | 141.43 | 47.64 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 201 | 170.37 | 57.59 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 201 | 171.39 | 58.02 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 201 | 171.39 | 58.02 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 202 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 202 | 22.19 | 13.42 | 1.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 202 | 40.79 | 20.04 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 202 | 69.87 | 28.30 | 2.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 202 | 107.00 | 38.17 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 202 | 141.77 | 47.74 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 202 | 170.93 | 57.73 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 202 | 171.96 | 58.16 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 202 | 171.96 | 58.16 | 2.96x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 217 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 217 | 11.61 | 9.48 | 1.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 217 | 22.27 | 13.65 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 217 | 41.10 | 20.36 | 2.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 217 | 70.82 | 28.96 | 2.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 217 | 109.47 | 39.23 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 217 | 146.64 | 49.22 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 217 | 179.00 | 59.70 | 3.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 217 | 180.17 | 60.16 | 3.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 217 | 180.17 | 60.16 | 3.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 218 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 218 | 11.61 | 9.48 | 1.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 218 | 22.28 | 13.67 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 218 | 41.11 | 20.38 | 2.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 218 | 70.88 | 29.00 | 2.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 218 | 109.62 | 39.29 | 2.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 218 | 146.95 | 49.31 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 218 | 179.51 | 59.83 | 3.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 218 | 180.70 | 60.29 | 3.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 218 | 180.70 | 60.29 | 3.00x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 243 | 11.64 | 9.66 | 1.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 243 | 22.39 | 14.03 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 243 | 41.53 | 20.84 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 243 | 72.22 | 30.04 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 243 | 113.17 | 40.91 | 2.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 243 | 154.10 | 51.56 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 243 | 191.70 | 62.89 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 243 | 193.12 | 63.38 | 3.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 243 | 193.12 | 63.38 | 3.05x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 324 | 11.71 | 10.09 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 324 | 22.65 | 15.05 | 1.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 324 | 42.47 | 22.00 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 324 | 75.27 | 32.91 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 324 | 121.48 | 45.03 | 2.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 324 | 171.53 | 57.52 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 324 | 223.03 | 71.21 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 324 | 225.14 | 71.81 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 324 | 225.14 | 71.81 | 3.14x |
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 354 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 354 | 11.72 | 10.21 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 354 | 22.71 | 15.37 | 1.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 354 | 42.71 | 22.36 | 1.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 354 | 76.08 | 33.79 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 354 | 123.72 | 46.23 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 354 | 176.41 | 59.43 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 354 | 232.21 | 73.90 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 354 | 234.54 | 74.52 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 354 | 234.54 | 74.52 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 366 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 366 | 11.73 | 10.25 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 366 | 22.74 | 15.50 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 366 | 42.80 | 22.49 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 366 | 76.36 | 34.12 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 366 | 124.53 | 46.68 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 366 | 178.18 | 60.17 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 366 | 235.59 | 74.92 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 366 | 238.00 | 75.56 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 366 | 238.00 | 75.56 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 371 | 11.73 | 10.27 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 371 | 22.75 | 15.55 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 371 | 42.84 | 22.55 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 371 | 76.48 | 34.25 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 371 | 124.86 | 46.87 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 371 | 178.89 | 60.47 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 371 | 236.96 | 75.34 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 371 | 239.40 | 75.98 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 371 | 239.40 | 75.98 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 373 | 11.73 | 10.27 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 373 | 22.75 | 15.57 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 373 | 42.85 | 22.57 | 1.90x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 373 | 76.52 | 34.31 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 373 | 124.98 | 46.94 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 373 | 179.17 | 60.59 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 373 | 237.50 | 75.51 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 373 | 239.95 | 76.15 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 373 | 239.95 | 76.15 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 379 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 379 | 11.74 | 10.30 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 379 | 22.76 | 15.62 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 379 | 42.89 | 22.64 | 1.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 379 | 76.66 | 34.46 | 2.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 379 | 125.36 | 47.15 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 379 | 180.00 | 60.95 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 379 | 239.09 | 76.01 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 379 | 241.59 | 76.65 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 379 | 241.59 | 76.65 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 380 | 11.74 | 10.30 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 380 | 22.76 | 15.63 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 380 | 42.90 | 22.65 | 1.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 380 | 76.68 | 34.49 | 2.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 380 | 125.42 | 47.19 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 380 | 180.14 | 61.01 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 380 | 239.35 | 76.09 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 380 | 241.85 | 76.74 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 380 | 241.85 | 76.74 | 3.15x |
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
| gpu | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 1.2% |
| rom | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 14.4% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | sram | interleaved | 128 B | 1.42x |
| DeepSeek-V4.1-Flash-engram-hbm | hbm | interleaved | 32 B | 1.12x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 169 | 0.00% | 0.13 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 162 | 0.00% | 0.13 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 162 | 0.00% | 0.13 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 162 | 0.00% | 0.13 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 162 | 0.00% | 0.13 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 162 | 0.00% | 0.13 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 162 | 0.00% | 0.13 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 3 | 0.01% | 0.19 | 15.81 |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 3 | 0.03% | 0.75 | 15.81 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 642.1 | 46,870.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 642.1 | 46,870.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 642.1 | 46,870.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 642.1 | 46,870.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 642.1 | 46,870.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 642.1 | 46,870.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 642.1 | 46,870.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 5.37% | 24.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 184.0 | 47,114.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 19.82% | 65.8 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 46.1 | 47,187.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 58.67% | 178.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 11.5 | 47,205.6 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 6 |
| gpu | link_latency | 462 |
| gpu | weight_read | 1242 |
| rom | compute | 1003 |
| rom | infeasible | 2229 |
| rom | kv_read | 3 |
| rom | link_latency | 1265 |
| rom | weight_read | 650 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2229 |

## Mechanical consistency audit

**FAIL** over 144,847 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x169', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x182', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x220', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x221', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x246', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x328', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x169', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x182', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x220', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x221', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x246', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x328', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x169', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x182', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x220', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x221', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x246', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x328', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x169', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x182', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x220', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x221', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x246', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x328', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x169', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x182', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x205', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x220', 'DeepSeek-V4.1-Flash-engram-hbm', 1)

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

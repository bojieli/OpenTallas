# Area-constrained roofline: n6_vs_a100

> Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 292x (ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream, 3,744 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 8 devices. On the GPU side the correction reaches 18x (a100_sxm_80gb-x3694-pipeline, 3,694 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 85 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 6 x 815 mm2 (4,890 mm2, array, KV in SRAM) at 8,165 tok/s per user and 1,670 tok/s per 1,000 mm2, holding 1 session, against 6 copies of one unified HBM die at the same silicon: 21.1x per user. DeepSeek-V4-Flash-0731 takes 42 x 815 mm2 (34,230 mm2, array, KV in SRAM) at 3,132 tok/s per user and 91 tok/s per 1,000 mm2, holding 1 session, against 41 copies of one unified HBM die at the same silicon: 9.7x per user. DeepSeek-V4-Pro-0813 takes 4 x 46,225 mm2 (184,900 mm2, wafer, KV in SRAM) at 1,943 tok/s per user and 11 tok/s per 1,000 mm2, holding 1 session, against 224 copies of one unified HBM die at the same silicon: 12.8x per user. Two granularities come out of one rule, which is the point: the class is chosen per model on evidence rather than assumed. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 8,150 mm2 of ROM silicon at 9,611 tok/s per user against 8,260 mm2 of a100_sxm_80gb-x10-tensor at 379 tok/s: **25.4x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 582. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 3,050,850 mm2 on DeepSeek-V4-Pro-0813 at batch 1, the iso-area GPU cluster is 3,694 devices. Cut as one serial pipeline that is 462 stages and 3,836 us of link latency per token; but the model has 61 layers, so at most 61 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 2,792 us. The iso-area per-user ratio at that point falls from 13.0x to 11.3x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 6.10x to it.** At 224,940 mm2 on Qwen3-8B the pipeline-only GPU delivers 94.76 tok/s and the same silicon running tensor delivers 578 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 8.78x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 2,246 to 272,121 tok/s, and its rate with every slot occupied from 177,426 to 272,121. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 79 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,825 us over NVLink, capping per-user decode at 548 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 450.4 us and cap it at 2,220 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 2.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 12 of 30 operating points and an array 18; on tokens per second per square millimetre the same points go 20 to the array and 10 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 903 of 7621 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 49.2x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 14.99x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 50 of 60 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### Qwen3-8B at 8,192 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x6`** -- 6 x 815 mm2 reticle dies, 4,890 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **8,165.0 tok/s per user** (0.12 ms/token), binding on `layer_fixed_latency`
- **1,669.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 8,165 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 483 W at 0.099 W/mm2, 59.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 6 copies of one unified HBM die -- `a100_sxm_80gb-x6-tensor`, 4,956 mm2, area ratio 0.9867 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 4,890 | 4,956 | 0.9867 |
| user tok/s | 8,165.0 | 386.4 | 21.13x |
| aggregate tok/s | 8,165 | 386 | 14.26x |
| resident sessions | 1 | 344 | -- |
| J/token | 0.0592 | 3.9648 | 67.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 344 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x272-tensor` at 224,672 mm2 and 578.1 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 11,638.4 | 251.8 | 1 | 21.64x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 11,638.4 | 251.8 | 1 | 21.64x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x5` | 4,075 | 5,677.6 | 1,393.3 | 1 | 16.56x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 4,890 | 8,165.0 | 1,669.7 | 1 | 21.13x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 4,890 | 8,165.0 | 1,669.7 | -- | 1,669.7 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 9,407.6 | 1,649.0 | 1,524.7 | 1,669.7 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 9,864.2 | 1,512.9 | 1,042.4 | 1,669.7 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x12-romfill` | 9,780 | 9,994.6 | 1,021.9 | 374.1 | 1,669.7 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x15-romfill` | 12,225 | 10,269.3 | 840.0 | 286.9 | 1,669.7 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 10,396.4 | 797.3 | 273.8 | 1,669.7 | stop |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 11,638.4 | 251.8 | 84.0 | 1,669.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x6` **<-- recommended** | 4,890 | 6 | 8,165.0 | 8,165 | 1,669.7 | 1 | `layer_fixed_latency` | 483 | 59.2 | `a100_sxm_80gb-x6-tensor` | 21.13x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 7 | 9,407.6 | 9,408 | 1,649.0 | 1 | `layer_fixed_latency` | 611 | 65.0 | `a100_sxm_80gb-x7-tensor` | 22.13x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 8 | 9,864.2 | 9,864 | 1,512.9 | 1 | `layer_fixed_latency` | 690 | 70.0 | `a100_sxm_80gb-x8-tensor` | 21.46x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x12-romfill` | 9,780 | 12 | 9,994.6 | 9,995 | 1,021.9 | 1 | `layer_fixed_latency` | 985 | 98.5 | `a100_sxm_80gb-x12-tensor` | 24.72x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x15-romfill` | 12,225 | 15 | 10,269.3 | 10,269 | 840.0 | 1 | `layer_fixed_latency` | 1,208 | 117.6 | `a100_sxm_80gb-x15-hybrid` | 23.24x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 16 | 10,396.4 | 10,396 | 797.3 | 1 | `layer_fixed_latency` | 1,283 | 123.4 | `a100_sxm_80gb-x16-hybrid` | 22.67x |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 1 | 11,638.4 | 11,638 | 251.8 | 1 | `layer_fixed_latency` | 4,277 | 367.5 | `a100_sxm_80gb-x56-tensor` | 21.64x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 262 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 4,890 | 8,165.0 | 1,669.7 | 1 |
| array | 262 | fastest | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 10,396.4 | 797.3 | 1 |
| array | 262 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x5` | 4,075 | 5,677.6 | 1,393.3 | 1 |
| wafer | 52 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 11,638.4 | 251.8 | 1 |
| wafer | 52 | fastest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 11,638.4 | 251.8 | 1 |
| wafer | 52 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 11,638.4 | 251.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 10,396.4 | 10,396 | 1 | 1,283 | 123.4 | `layer_fixed_latency` | `a100_sxm_80gb-x16-hybrid` | 458.7 | 940 | 6,759.4 | 0.987 | 22.67x | 54.8x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 11,638.4 | 11,638 | 1 | 4,277 | 367.5 | `layer_fixed_latency` | `a100_sxm_80gb-x56-tensor` | 537.8 | 3,324 | 16,758.5 | 0.999 | 21.64x | 45.6x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 46,455 | 8,276.5 | 8,277 | 1 | 4,254 | 514.0 | `layer_fixed_latency` | `a100_sxm_80gb-x56-tensor` | 537.8 | 3,324 | 16,758.5 | 1.004 | 15.39x | 32.6x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 11,638.4 | -- | 1 | -- | 367.5 | -- | -- | -- | -- | -- | 1.005 | 1.41x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 8,012.3 | 72,111 | 16,450 | 34,838 | 1,695.7 | `layer_fixed_latency` | `a100_sxm_80gb-x272-tensor` | 544.1 | 16,198 | 37,018.3 | 1.001 | 14.73x | 21.8x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 8,007.6 | 16,015 | 4,100 | 36,574 | 2,283.7 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 539.0 | 26,689 | 61,728.1 | 0.999 | 14.86x | 27.0x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 8,012.3 | 72,111 | 16,450 | 34,838 | 916.2 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 532.5 | 16,198 | 20,160.5 | 1.001 | 15.05x | 22.0x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 7,275.2 | 29,101 | 4,100 | 38,363 | 1,318.3 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 539.0 | 26,689 | 31,725.5 | 0.999 | 13.50x | 24.1x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 8,012.3 | 72,111 | 16,450 | 34,838 | 526.4 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 514.3 | 16,198 | 10,672.3 | 1.001 | 15.58x | 20.3x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 6,194.5 | 49,556 | 4,100 | 41,158 | 830.5 | `kv_read` | `a100_sxm_80gb-x448-hybrid` | 534.5 | 26,689 | 16,652.1 | 0.999 | 11.59x | 20.0x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 7,650.1 | 137,701 | 16,450 | 43,802 | 340.8 | `layer_fixed_latency` | `a100_sxm_80gb-x272-hybrid` | 474.5 | 16,198 | 6,200.3 | 1.001 | 16.12x | 18.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,011.4 | 80,183 | 6,151 | 62,443 | 778.8 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 520.1 | 40,040 | 12,886.2 | 0.999 | 9.64x | 16.5x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,230.8 | 199,385 | 20,265 | 57,734 | 289.6 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 447.1 | 19,953 | 4,059.9 | 1.001 | 13.94x | 14.0x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,240.6 | 103,700 | 6,151 | 65,599 | 632.6 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 479.6 | 40,040 | 7,001.2 | 0.999 | 6.76x | 11.1x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 4,555.8 | 291,570 | 20,265 | 70,176 | 240.7 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 430.7 | 19,953 | 2,930.7 | 1.001 | 10.58x | 12.2x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,892.1 | 121,096 | 6,151 | 67,942 | 561.1 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 442.4 | 40,040 | 5,149.7 | 0.999 | 4.28x | 9.2x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 1,594.7 | 408,254 | 20,265 | 85,929 | 210.5 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 354.0 | 19,953 | 926.7 | 1.001 | 4.50x | 4.4x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 532.8 | 136,407 | 6,151 | 70,008 | 513.2 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 402.4 | 40,040 | 1,595.9 | 0.999 | 1.32x | 3.1x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 431.0 | 441,352 | 20,265 | 89,713 | 203.3 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 206.7 | 19,953 | 425.7 | 1.001 | 2.08x | 2.1x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 136.7 | 139,944 | 6,151 | 70,484 | 503.7 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 286.6 | 40,040 | 593.1 | 0.999 | 0.48x | 1.2x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 111.0 | 454,472 | 20,265 | 104,727 | 230.4 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 77.9 | 19,953 | 316.2 | 1.001 | 1.42x | 1.4x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 34.4 | 140,791 | 6,151 | 100,286 | 712.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 133.3 | 40,040 | 342.4 | 0.999 | 0.26x | 0.5x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 4,890 | array | SRAM | 1 |
| 2-32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill` | 56,235 | array | HBM | 4,112 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x69` | 56,235 | array | HBM | 4,112 |
| 256-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x69` | 56,235 | array | HBM | 4,112 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Flash-0731 at 200,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-hybrid-x42`** -- 42 x 815 mm2 reticle dies, 34,230 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **3,131.5 tok/s per user** (0.32 ms/token), binding on `layer_fixed_latency`
- **91.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,132 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 2,120 W at 0.062 W/mm2, 677.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 41 copies of one unified HBM die -- `a100_sxm_80gb-x41-hybrid`, 33,866 mm2, area ratio 1.0107 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 34,230 | 33,866 | 1.0107 |
| user tok/s | 3,131.5 | 322.2 | 9.72x |
| aggregate tok/s | 3,132 | 1,933 | 0.59x |
| resident sessions | 1 | 2,015 | -- |
| J/token | 0.6770 | 19.5890 | 28.9x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 2,015 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x24-hybrid` at 19,824 mm2 and 337.2 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,328.6 | 46.8 | 1 | 13.00x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,328.6 | 46.8 | 1 | 13.00x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x37` | 30,155 | 2,318.2 | 76.9 | 1 | 7.03x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-hybrid-x42` | 34,230 | 3,131.5 | 91.5 | 1 | 9.72x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x42` | 34,230 | 3,131.5 | 91.5 | -- | 91.5 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 3,237.5 | 90.3 | 65.0 | 91.5 | stop |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,092.2 | 88.5 | 80.1 | 91.5 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,328.6 | 46.8 | 20.6 | 91.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x42` **<-- recommended** | 34,230 | 42 | 3,131.5 | 3,132 | 91.5 | 1 | `layer_fixed_latency` | 2,120 | 677.0 | `a100_sxm_80gb-x41-hybrid` | 9.72x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 44 | 3,237.5 | 3,237 | 90.3 | 1 | `layer_fixed_latency` | 2,290 | 707.3 | `a100_sxm_80gb-x43-hybrid` | 9.92x |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 1 | 4,092.2 | 4,092 | 88.5 | 1 | `layer_fixed_latency` | 3,798 | 928.2 | `a100_sxm_80gb-x56-hybrid` | 12.19x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2 | 4,328.6 | 4,329 | 46.8 | 1 | `layer_fixed_latency` | 10,503 | 2,426.3 | `a100_sxm_80gb-x112-hybrid` | 13.00x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 324 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x42` | 34,230 | 3,131.5 | 91.5 | 1 |
| array | 324 | fastest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 65,200 | 3,949.8 | 60.6 | 1 |
| array | 324 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x37` | 30,155 | 2,318.2 | 76.9 | 1 |
| wafer | 52 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,092.2 | 88.5 | 1 |
| wafer | 52 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,328.6 | 46.8 | 1 |
| wafer | 52 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,092.2 | 88.5 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 65,200 | 3,949.8 | 3,950 | 1 | 6,549 | 1,658.0 | `layer_fixed_latency` | `a100_sxm_80gb-x79-hybrid` | 333.5 | 3,996 | 35,417.5 | 0.999 | 11.84x | 21.4x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,328.6 | 4,329 | 1 | 10,503 | 2,426.3 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 333.1 | 5,715 | 49,767.0 | 0.999 | 13.00x | 20.5x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x113` | 92,095 | 3,716.1 | 3,716 | 1 | 10,447 | 2,811.3 | `layer_fixed_latency` | `a100_sxm_80gb-x111-hybrid` | 332.3 | 5,663 | 49,441.8 | 1.004 | 11.18x | 17.6x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,328.6 | -- | 1 | -- | 2,426.3 | -- | -- | -- | -- | -- | 0.996 | 1.16x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 3,844.6 | 84,580 | 4,481 | 11,783 | 1,143.7 | `layer_fixed_latency` | `a100_sxm_80gb-x85-hybrid` | 331.3 | 4,308 | 19,739.9 | 0.998 | 11.61x | 17.3x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 462,250 | 3,953.0 | 39,530 | 4,481 | 66,895 | 8,305.7 | `layer_fixed_latency` | `a100_sxm_80gb-x560-hybrid` | 322.7 | 29,061 | 126,512.0 | 0.999 | 12.25x | 15.2x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 3,844.6 | 84,580 | 4,481 | 11,783 | 591.3 | `layer_fixed_latency` | `a100_sxm_80gb-x85-hybrid` | 331.3 | 4,308 | 10,477.5 | 0.998 | 11.61x | 17.7x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 462,250 | 3,953.0 | 39,530 | 4,481 | 66,895 | 4,172.3 | `layer_fixed_latency` | `a100_sxm_80gb-x560-hybrid` | 322.7 | 29,061 | 63,863.6 | 0.999 | 12.25x | 15.3x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 3,844.6 | 84,580 | 4,481 | 11,783 | 315.1 | `layer_fixed_latency` | `a100_sxm_80gb-x85-hybrid` | 331.3 | 4,308 | 5,846.4 | 0.998 | 11.61x | 18.6x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 462,250 | 3,953.0 | 39,530 | 4,481 | 66,895 | 2,105.6 | `layer_fixed_latency` | `a100_sxm_80gb-x560-hybrid` | 322.7 | 29,061 | 32,539.4 | 0.999 | 12.25x | 15.5x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 3,844.6 | 84,580 | 4,481 | 11,783 | 177.0 | `layer_fixed_latency` | `a100_sxm_80gb-x85-hybrid` | 311.7 | 4,308 | 3,419.2 | 0.998 | 12.34x | 19.3x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 462,250 | 3,829.7 | 68,934 | 4,481 | 68,038 | 1,105.5 | `layer_fixed_latency` | `a100_sxm_80gb-x560-hybrid` | 322.7 | 29,061 | 16,877.3 | 0.999 | 11.87x | 15.3x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 257,540 | 3,628.0 | 286,613 | 16,467 | 39,744 | 285.2 | `layer_fixed_latency` | `a100_sxm_80gb-x312-hybrid` | 324.1 | 16,138 | 5,559.4 | 0.999 | 11.20x | 19.5x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,456.6 | 110,612 | 5,377 | 83,220 | 752.4 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 322.7 | 34,898 | 10,612.5 | 0.999 | 10.71x | 14.1x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 257,540 | 3,628.0 | 286,613 | 16,467 | 39,744 | 162.1 | `layer_fixed_latency` | `a100_sxm_80gb-x312-hybrid` | 296.6 | 16,138 | 3,266.4 | 0.999 | 12.23x | 20.2x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 2,972.3 | 190,224 | 5,377 | 86,247 | 453.4 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 322.7 | 34,898 | 5,913.8 | 0.999 | 9.21x | 13.0x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 2,291.5 | 586,611 | 17,717 | 53,099 | 90.5 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 195.1 | 17,336 | 1,626.5 | 1.001 | 11.75x | 18.0x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,483.1 | 379,675 | 5,377 | 93,146 | 245.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 249.1 | 34,898 | 2,179.2 | 0.999 | 5.95x | 8.9x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 883.5 | 904,731 | 17,717 | 64,465 | 71.3 | `compute` | `a100_sxm_80gb-x335-hybrid` | 95.1 | 17,336 | 918.4 | 1.001 | 9.29x | 12.9x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 480.3 | 491,830 | 5,377 | 97,320 | 197.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 143.1 | 34,898 | 1,173.7 | 0.999 | 3.36x | 5.9x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 313.9 | 1,285,836 | 17,717 | 88,471 | 68.8 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 37.6 | 17,336 | 662.1 | 1.001 | 8.34x | 9.6x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 128.2 | 524,927 | 5,377 | 98,323 | 187.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 60.1 | 34,898 | 816.0 | 0.999 | 2.13x | 4.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x42` | 34,230 | array | SRAM | 1 |
| 2-64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x79` | 64,385 | array | HBM | 4,116 |
| 256 | `ROM-N6-native-HBMKV-array-hw-pipeline-x119` | 96,985 | array | HBM | 6,201 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x158` | 128,770 | array | HBM | 8,233 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Pro-0813 at 1,000,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-wafer-hybrid-x4`** -- 4 x 46,225 mm2 wafers, 184,900 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **1,942.7 tok/s per user** (0.51 ms/token), binding on `layer_fixed_latency`
- **10.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 1,943 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 11,089 W at 0.060 W/mm2, 5,707.7 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 224 copies of one unified HBM die -- `a100_sxm_80gb-x224-hybrid`, 185,024 mm2, area ratio 0.9993 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 184,900 | 185,024 | 0.9993 |
| user tok/s | 1,942.7 | 151.4 | 12.83x |
| aggregate tok/s | 1,943 | 4,240 | 0.23x |
| resident sessions | 1 | 1,545 | -- |
| J/token | 5.7077 | 218.0148 | 38.2x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,545 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 153.5 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x5-romfill` | 231,125 | 2,057.9 | 8.9 | 1 | 13.65x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 2,103.7 | 5.1 | 1 | 14.19x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x190` | 154,850 | 613.3 | 4.0 | 1 | 4.08x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,942.7 | 10.5 | 1 | 12.83x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,942.7 | 10.5 | -- | 10.5 | ACCEPT |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x5-romfill` | 231,125 | 2,057.9 | 8.9 | 2.5 | 10.5 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,081.4 | 7.5 | 1.5 | 10.5 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x8` | 369,800 | 2,097.4 | 5.7 | 0.8 | 10.5 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 2,103.7 | 5.1 | 0.7 | 10.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x4` **<-- recommended** | 184,900 | 4 | 1,942.7 | 1,943 | 10.5 | 1 | `layer_fixed_latency` | 11,089 | 5,707.7 | `a100_sxm_80gb-x224-hybrid` | 12.83x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x5-romfill` | 231,125 | 5 | 2,057.9 | 2,058 | 8.9 | 1 | `layer_fixed_latency` | 17,795 | 8,646.9 | `a100_sxm_80gb-x280-hybrid` | 13.65x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 6 | 2,081.4 | 2,081 | 7.5 | 1 | `layer_fixed_latency` | 24,498 | 11,769.9 | `a100_sxm_80gb-x336-hybrid` | 13.87x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x8` | 369,800 | 8 | 2,097.4 | 2,097 | 5.7 | 1 | `layer_fixed_latency` | 37,904 | 18,071.9 | `a100_sxm_80gb-x448-hybrid` | 14.11x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 9 | 2,103.7 | 2,104 | 5.1 | 1 | `layer_fixed_latency` | 44,607 | 21,203.8 | `a100_sxm_80gb-x504-hybrid` | 14.19x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 126 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x227` | 185,005 | 1,200.0 | 6.5 | 1 |
| array | 126 | fastest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 317,035 | 1,467.1 | 4.6 | 1 |
| array | 126 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x190` | 154,850 | 613.3 | 4.0 | 1 |
| wafer | 39 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,942.7 | 10.5 | 1 |
| wafer | 39 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 2,103.7 | 5.1 | 1 |
| wafer | 39 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,942.7 | 10.5 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 317,035 | 1,467.1 | 1,467 | 1 | 30,234 | 20,608.4 | `layer_fixed_latency` | `a100_sxm_80gb-x384-hybrid` | 149.5 | 2,714 | 375,380.2 | 1.000 | 9.82x | 18.2x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 2,103.7 | 2,104 | 1 | 44,607 | 21,203.8 | `layer_fixed_latency` | `a100_sxm_80gb-x504-hybrid` | 148.2 | 3,591 | 495,397.3 | 0.999 | 14.19x | 23.4x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,671.4 | 110,311 | 4,146 | 463,193 | 130,375.3 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 26,894 | 1,804,093.9 | 1.000 | 11.28x | 13.8x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,671.4 | 110,311 | 4,146 | 463,193 | 65,315.6 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 26,894 | 904,255.2 | 1.000 | 11.28x | 13.8x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,671.4 | 110,311 | 4,146 | 463,193 | 32,785.8 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 26,894 | 454,335.8 | 1.000 | 11.28x | 13.9x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,671.4 | 110,311 | 4,146 | 463,193 | 16,520.9 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 26,894 | 229,376.2 | 1.000 | 11.28x | 13.9x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,671.4 | 110,311 | 4,146 | 463,193 | 8,388.4 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 26,894 | 116,896.3 | 1.000 | 11.28x | 13.9x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,671.4 | 110,311 | 4,146 | 463,193 | 4,322.2 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 26,894 | 60,656.4 | 1.000 | 11.28x | 14.0x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,003.1 | 256,787 | 4,146 | 500,504 | 1,949.1 | `kv_read` | `a100_sxm_80gb-x3694-hybrid` | 148.2 | 26,894 | 18,476.5 | 1.000 | 6.77x | 9.5x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 362.1 | 370,797 | 4,146 | 529,607 | 1,428.3 | `kv_read` | `a100_sxm_80gb-x3694-hybrid` | 109.3 | 26,894 | 7,622.2 | 1.000 | 3.31x | 5.3x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 3,050,850 | 100.3 | 410,873 | 4,146 | 539,836 | 1,313.9 | `kv_read` | `a100_sxm_80gb-x3694-hybrid` | 53.1 | 26,894 | 4,647.8 | 1.000 | 1.89x | 3.5x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | wafer | SRAM | 1 |
| 2-1024 | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | wafer | HBM | 4,146 |
| 4096 | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 3,050,850 | wafer | HBM | 4,146 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 79, 99, 113, 119, 158, 170, 227, 237, 316, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 79, 80, 85, 86, 99, 113, 119, 158, 170, 227, 237, 316, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 37, 42, 44, 46, 53, 57, 62, 63, 70, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 37, 42, 44, 46, 53, 57, 70, 75, 79, 80, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 190, 205, 227, 237, 272, 284, 315, 339, 340, 378 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 190, 205, 227, 237, 272, 284, 329, 340, 378, 388, 389 |
| Qwen3-8B | HBM | rom | 69, 86, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| Qwen3-8B | HBM | sram | 69, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| Qwen3-8B | SRAM | rom | 5, 6, 7, 8, 10, 12, 15, 16, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 5, 6, 7, 8, 12, 16, 57, 113, 170, 227, 340 |

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
| Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 1 | 6 | 2.03 | hierarchical | 61.09 | 11.04 | 50.34 | 24.92 | 8,165.0 |
| Qwen3-8B | `a100_sxm_80gb-x6-tensor` | 1 | 6 | 2.03 | measured_floor | 566.80 | 371.55 | 1,649.41 | 371.73 | 386.4 |
| Qwen3-8B | `a100_sxm_80gb-x6-tensor` | 64 | 6 | 2.03 | measured_floor | 566.80 | 784.43 | 9,329.96 | 681.39 | 93.6 |
| DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x42` | 1 | 16 | 6.51 | hierarchical, one_shot | 191.87 | 80.00 | 53.78 | 34.52 | 3,131.5 |
| DeepSeek-V4-Flash-0731 | `a100_sxm_80gb-x41-hybrid` | 1 | 8 | 5.51 | measured_floor | 894.40 | 1,330.70 | 1,022.08 | 460.35 | 322.2 |
| DeepSeek-V4-Flash-0731 | `a100_sxm_80gb-x41-hybrid` | 64 | 4 | 5.51 | measured_floor | 894.40 | 1,978.83 | 4,643.38 | 506.11 | 145.1 |
| DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 1 | 57 on `rom_wafer_express` | 6.51 | centre_mesh, one_shot | 364.28 | 86.61 | 74.44 | 34.49 | 1,942.7 |
| DeepSeek-V4-Pro-0813 | `a100_sxm_80gb-x224-hybrid` | 1 | 8 | 5.51 | measured_floor | 1,263.60 | 2,649.48 | 3,169.23 | 713.20 | 151.4 |
| DeepSeek-V4-Pro-0813 | `a100_sxm_80gb-x224-hybrid` | 64 | 8 | 5.51 | measured_floor | 1,263.60 | 3,842.16 | 4,611.65 | 752.79 | 110.6 |

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

- **0 of 7,621 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 340 | 0 | 58.7% | 80.0% | 0.388 | 62% |
| gpu | small array (1,600-5,000 mm2) | 60 | 0 | 77.2% | 80.3% | 0.389 | 47% |
| gpu | wafer (>=40,000 mm2) | 2,518 | 0 | 48.3% | 80.2% | 0.389 | 75% |
| rom | large array (5,000-40,000 mm2) | 150 | 0 | 13.4% | 25.7% | 0.128 | 99% |
| rom | small array (1,600-5,000 mm2) | 72 | 0 | 16.8% | 22.2% | 0.111 | 79% |
| rom | wafer (>=40,000 mm2) | 4,481 | 0 | 29.6% | 75.7% | 0.379 | 86% |

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
| DeepSeek-V4-Flash-0731 | 1 | 92,450 | `DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 2.426298 | 10,502.5 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x112-hybrid` | 49.766967 | 21,837.4 | link_latency | 20.51x |
| DeepSeek-V4-Flash-0731 | 2 | 64,385 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79` | 1.035693 | 10,521.7 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x78-hybrid` | 18.154725 | 15,301.5 | link_latency | 17.53x |
| DeepSeek-V4-Flash-0731 | 4 | 64,385 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79` | 0.537282 | 10,521.7 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x78-hybrid` | 9.684960 | 15,301.5 | link_latency | 18.03x |
| DeepSeek-V4-Flash-0731 | 8 | 64,385 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79` | 0.288076 | 10,521.7 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x78-hybrid` | 5.450078 | 15,301.5 | link_latency | 18.92x |
| DeepSeek-V4-Flash-0731 | 16 | 64,385 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79` | 0.163473 | 10,521.7 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x78-hybrid` | 3.198399 | 15,715.9 | link_latency | 19.57x |
| DeepSeek-V4-Flash-0731 | 32 | 80,685 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x99` | 0.127325 | 14,613.9 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x98-hybrid` | 2.344293 | 20,474.7 | link_latency | 18.41x |
| DeepSeek-V4-Flash-0731 | 64 | 193,155 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x237-romfill` | 0.135263 | 30,056.1 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x234-hybrid` | 2.662044 | 47,702.2 | link_latency | 19.68x |
| DeepSeek-V4-Flash-0731 | 256 | 257,540 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 0.088781 | 49,949.4 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x312-hybrid` | 1.564463 | 76,057.9 | weight_read | 17.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 257,540 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 0.081263 | 70,627.1 | weight_read | `DSV4-Flash/a100_sxm_80gb-x312-hybrid` | 0.898410 | 83,472.6 | weight_read | 11.06x |
| DeepSeek-V4-Flash-0731 | 4096 | 257,540 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 0.067601 | 83,987.1 | weight_read | `DSV4-Flash/a100_sxm_80gb-x312-hybrid` | 0.646830 | 95,056.5 | weight_read | 9.57x |
| DeepSeek-V4-Pro-0813 | 1 | 231,125 | `DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x5-romfill` | 8.646904 | 17,794.6 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x280-hybrid` | 272.638165 | 63,726.1 | weight_read | 31.53x |
| DeepSeek-V4-Pro-0813 | 2 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 130.375275 | 463,193.1 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 1,804.093874 | 835,705.8 | link_latency | 13.84x |
| DeepSeek-V4-Pro-0813 | 4 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 65.315627 | 463,193.1 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 904.255185 | 835,705.8 | link_latency | 13.84x |
| DeepSeek-V4-Pro-0813 | 8 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 32.785804 | 463,193.1 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 454.335840 | 835,705.8 | link_latency | 13.86x |
| DeepSeek-V4-Pro-0813 | 16 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 16.520892 | 463,193.1 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 229.376168 | 835,705.8 | link_latency | 13.88x |
| DeepSeek-V4-Pro-0813 | 32 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 8.388436 | 463,193.1 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 116.896332 | 835,705.8 | link_latency | 13.94x |
| DeepSeek-V4-Pro-0813 | 64 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 4.322208 | 463,193.1 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 60.656414 | 835,705.8 | link_latency | 14.03x |
| DeepSeek-V4-Pro-0813 | 256 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1.949102 | 500,504.0 | kv_read | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 18.476475 | 835,705.8 | link_latency | 9.48x |
| DeepSeek-V4-Pro-0813 | 1024 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1.428291 | 529,606.6 | kv_read | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 7.622218 | 853,020.0 | link_latency | 5.34x |
| DeepSeek-V4-Pro-0813 | 4096 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66` | 1.313877 | 539,836.4 | kv_read | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 4.647838 | 1,011,662.0 | weight_read | 3.54x |
| Qwen3-8B | 1 | 46,225 | `Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 0.367516 | 4,277.3 | layer_fixed_latency | `Qwen3-8B/a100_sxm_80gb-x56-tensor` | 16.758465 | 9,012.1 | link_latency | 45.60x |
| Qwen3-8B | 2 | 56,235 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill` | 0.546351 | 9,371.1 | layer_fixed_latency | `Qwen3-8B/a100_sxm_80gb-x68-tensor` | 10.449947 | 10,774.4 | link_latency | 19.13x |
| Qwen3-8B | 4 | 84,760 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x104-romfill` | 0.437993 | 13,683.6 | layer_fixed_latency | `Qwen3-8B/a100_sxm_80gb-x103-hybrid` | 8.333311 | 16,734.1 | link_latency | 19.03x |
| Qwen3-8B | 8 | 112,470 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x138-romfill` | 0.339115 | 21,978.5 | layer_fixed_latency | `Qwen3-8B/a100_sxm_80gb-x136-hybrid` | 5.878508 | 22,414.4 | link_latency | 17.33x |
| Qwen3-8B | 16 | 224,940 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 0.340777 | 43,802.5 | layer_fixed_latency | `Qwen3-8B/a100_sxm_80gb-x272-hybrid` | 6.200319 | 47,068.2 | link_latency | 18.19x |
| Qwen3-8B | 32 | 224,940 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 0.268038 | 53,411.0 | kv_read | `Qwen3-8B/a100_sxm_80gb-x272-hybrid` | 4.491197 | 65,244.7 | weight_read | 16.76x |
| Qwen3-8B | 64 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.240684 | 70,176.1 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 2.930691 | 80,789.8 | weight_read | 12.18x |
| Qwen3-8B | 256 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.210479 | 85,928.9 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.926718 | 83,985.9 | weight_read | 4.40x |
| Qwen3-8B | 1024 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.203268 | 89,712.7 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.425724 | 90,121.7 | kv_read | 2.09x |
| Qwen3-8B | 4096 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.230436 | 104,727.0 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.316213 | 100,885.7 | kv_read | 1.37x |

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
| Qwen3-8B | 1 | 46,225 | 13,393.6 | wafer-pipeline | 11,638.4 | wafer-tensor | 1.15x | 1,200.0 | pipeline | 537.8 | tensor | 2.23x | 11.16x | 21.64x | 1.94x |
| Qwen3-8B | 2 | 92,450 | 13,065.5 | wafer-pipeline | 10,331.2 | wafer-hybrid | 1.26x | 1,342.3 | pipeline | 562.5 | tensor | 2.39x | 9.73x | 18.37x | 1.89x |
| Qwen3-8B | 3 | 138,675 | 12,989.3 | wafer-pipeline | 9,342.4 | wafer-hybrid | 1.39x | 1,397.6 | pipeline | 571.2 | tensor | 2.45x | 9.29x | 16.36x | 1.76x |
| Qwen3-8B | 4 | 184,900 | 12,948.3 | wafer-pipeline | 8,790.2 | wafer-tensor | 1.47x | 1,427.0 | pipeline | 575.7 | tensor | 2.48x | 9.07x | 15.27x | 1.68x |
| Qwen3-8B | 6 | 277,350 | 12,903.3 | wafer-pipeline | 8,192.1 | wafer-tensor | 1.58x | 1,457.6 | pipeline | 533.3 | hybrid | 2.73x | 8.85x | 15.36x | 1.74x |
| Qwen3-8B | 8 | 369,800 | 12,879.0 | wafer-pipeline | 8,049.1 | wafer-hybrid | 1.60x | 1,473.4 | pipeline | 539.0 | hybrid | 2.73x | 8.74x | 14.93x | 1.71x |
| Qwen3-8B | 12 | 554,700 | 13,408.3 | wafer-pipeline | 8,000.8 | wafer-hybrid | 1.68x | 1,489.6 | pipeline | 534.2 | hybrid | 2.79x | 9.00x | 14.98x | 1.66x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 4,740.3 | wafer-pipeline | 4,092.2 | wafer-tensor | 1.16x | 870.0 | pipeline | 335.7 | hybrid | 2.59x | 5.45x | 12.19x | 2.24x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 4,746.3 | wafer-pipeline | 4,328.6 | wafer-hybrid | 1.10x | 915.8 | pipeline | 333.1 | hybrid | 2.75x | 5.18x | 13.00x | 2.51x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 4,747.5 | wafer-pipeline | 4,242.4 | wafer-hybrid | 1.12x | 932.2 | pipeline | 330.5 | hybrid | 2.82x | 5.09x | 12.84x | 2.52x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 4,747.5 | wafer-pipeline | 4,177.0 | wafer-hybrid | 1.14x | 940.6 | pipeline | 328.0 | hybrid | 2.87x | 5.05x | 12.74x | 2.52x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 4,747.5 | wafer-pipeline | 4,094.1 | wafer-hybrid | 1.16x | 949.2 | pipeline | 323.0 | hybrid | 2.94x | 5.00x | 12.68x | 2.53x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 4,747.5 | wafer-pipeline | 4,031.5 | wafer-hybrid | 1.18x | 953.5 | pipeline | 322.7 | hybrid | 2.96x | 4.98x | 12.49x | 2.51x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 4,747.5 | wafer-pipeline | 3,926.8 | wafer-hybrid | 1.21x | 957.9 | pipeline | 322.7 | hybrid | 2.97x | 4.96x | 12.17x | 2.46x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 2,103.5 | wafer-hybrid | 1,942.7 | wafer-hybrid | 1.08x | 630.9 | pipeline | 151.4 | hybrid | 4.17x | 3.33x | 12.83x | 3.85x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 2,125.0 | wafer-pipeline | 2,081.4 | wafer-hybrid | 1.02x | 645.1 | pipeline | 150.0 | hybrid | 4.30x | 3.29x | 13.87x | 4.21x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 2,125.1 | wafer-pipeline | 2,097.4 | wafer-hybrid | 1.01x | 652.5 | pipeline | 148.7 | hybrid | 4.39x | 3.26x | 14.11x | 4.33x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 2,125.1 | wafer-pipeline | 2,079.8 | wafer-hybrid | 1.02x | 660.0 | pipeline | 148.2 | hybrid | 4.45x | 3.22x | 14.03x | 4.36x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.66x to 4.36x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 11,638.4 | 11,638.4 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,116.03 | 537.8 | 537.8 | link_latency | 21.64x | 2.19x | 122.82x | 21.64x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x5 | 4,075 | 5,677.6 | 5,677.6 | compute | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 371.29 | 342.8 | 342.8 | weight_read | 16.56x | 11.90x | 59.48x | 16.56x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 8,012.3 | 72,111.0 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x272-tensor | 224,672 | 1.00x | tensor | 1,232.10 | 544.1 | 1,088.2 | link_latency | 14.73x | 2.80x | 84.55x | 14.73x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 7,622.6 | 22,867.9 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x68-tensor | 56,168 | 1.00x | tensor | 1,216.68 | 515.5 | 1,031.0 | link_latency | 14.79x | 3.55x | 80.44x | 14.79x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 8,012.3 | 72,111.0 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 1,129.18 | 532.5 | 2,662.5 | link_latency | 15.05x | 2.80x | 84.55x | 15.05x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 7,450.4 | 37,252.0 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 1,218.77 | 476.6 | 1,906.4 | link_latency | 15.63x | 5.78x | 78.62x | 15.63x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 8,012.3 | 72,111.0 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 1,187.77 | 514.3 | 4,114.0 | link_latency | 15.58x | 2.80x | 84.55x | 15.58x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 5,959.8 | 53,638.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 392.77 | 440.6 | 3,965.8 | weight_read | 13.53x | 8.32x | 62.89x | 13.53x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 7,650.1 | 137,701.2 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 1,194.61 | 474.5 | 7,591.3 | link_latency | 16.12x | 5.34x | 80.73x | 16.12x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 4,013.3 | 64,212.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 400.16 | 425.2 | 6,802.5 | weight_read | 9.44x | 9.44x | 42.35x | 9.44x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,230.8 | 199,384.7 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,299.18 | 447.1 | 14,306.2 | link_latency | 13.94x | 6.28x | 65.75x | 13.94x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 2,435.3 | 77,929.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 417.06 | 393.5 | 12,593.0 | weight_read | 6.19x | 6.19x | 25.70x | 6.19x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 4,555.8 | 291,569.7 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 466.04 | 430.7 | 27,566.8 | weight_read | 10.58x | 9.18x | 48.08x | 10.65x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69 | 56,235 | 1,331.2 | 85,193.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 450.85 | 342.6 | 21,924.5 | weight_read | 3.89x | 3.89x | 14.05x | 3.89x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 1,594.7 | 408,253.7 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 549.93 | 354.0 | 90,627.3 | weight_read | 4.50x | 4.50x | 16.83x | 4.54x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | 56,235 | 356.0 | 91,140.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 653.58 | 192.8 | 49,352.2 | kv_read | 1.85x | 1.85x | 4.48x | 1.85x |
| Qwen3-8B | 1024 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 431.0 | 441,352.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 885.48 | 206.7 | 211,690.3 | kv_read | 2.08x | 2.08x | 5.20x | 2.11x |
| Qwen3-8B | 1024 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | 56,235 | 90.4 | 92,570.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 1,464.51 | 70.1 | 71,811.4 | kv_read | 1.29x | 1.29x | 1.89x | 1.29x |
| Qwen3-8B | 4096 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 111.0 | 454,472.4 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,029.76 | 77.9 | 319,043.5 | kv_read | 1.42x | 1.42x | 2.08x | 1.48x |
| Qwen3-8B | 4096 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | 56,235 | 22.7 | 92,935.4 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-pipeline | 56,168 | 1.00x | pipeline | 217.61 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 4,328.6 | 4,328.6 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 1,357.43 | 333.1 | 4,662.9 | link_latency | 13.00x | 0.30x | 33.35x | 13.00x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x37 | 30,155 | 2,318.2 | 2,318.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 0.99x | hybrid | 1,327.36 | 329.7 | 1,648.4 | link_latency | 7.03x | 0.48x | 17.83x | 7.03x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,953.0 | 39,530.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x560-hybrid | 462,560 | 1.00x | hybrid | 1,454.33 | 322.7 | 22,585.8 | link_latency | 12.25x | 0.54x | 30.46x | 12.50x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 3,797.0 | 75,939.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,344.06 | 332.4 | 3,324.2 | link_latency | 11.42x | 7.50x | 29.26x | 11.42x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,953.0 | 39,530.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x560-hybrid | 462,560 | 1.00x | hybrid | 1,454.33 | 322.7 | 22,585.8 | link_latency | 12.25x | 0.54x | 30.46x | 12.50x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 3,797.0 | 75,939.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,344.06 | 332.4 | 3,324.2 | link_latency | 11.42x | 7.50x | 29.26x | 11.42x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,953.0 | 39,530.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x560-hybrid | 462,560 | 1.00x | hybrid | 1,454.33 | 322.7 | 22,585.8 | link_latency | 12.25x | 0.54x | 30.46x | 12.50x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 3,797.0 | 75,939.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,344.06 | 332.4 | 3,324.2 | link_latency | 11.42x | 7.50x | 29.26x | 11.42x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x86 | 70,090 | 3,844.6 | 84,580.4 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x85-hybrid | 70,210 | 1.00x | hybrid | 1,422.44 | 311.7 | 4,986.7 | link_latency | 12.34x | 7.67x | 29.62x | 12.34x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 3,797.0 | 75,939.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,442.32 | 307.1 | 4,913.7 | link_latency | 12.36x | 7.50x | 29.26x | 12.36x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill | 257,540 | 3,628.0 | 286,613.4 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x312-hybrid | 257,712 | 1.00x | hybrid | 1,440.96 | 324.1 | 12,638.0 | link_latency | 11.20x | 7.08x | 27.96x | 11.20x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 3,181.2 | 101,798.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,704.34 | 255.9 | 8,188.0 | link_latency | 12.43x | 10.06x | 24.51x | 12.43x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill | 257,540 | 3,628.0 | 286,613.4 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x312-hybrid | 257,712 | 1.00x | hybrid | 1,570.32 | 296.6 | 18,984.7 | link_latency | 12.23x | 7.08x | 27.96x | 12.23x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 2,356.5 | 150,813.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 2,228.38 | 193.3 | 12,371.2 | link_latency | 12.19x | 12.19x | 18.16x | 12.19x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 2,291.5 | 586,611.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,742.42 | 195.1 | 49,939.1 | weight_read | 11.75x | 11.75x | 17.66x | 12.01x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79 | 64,385 | 923.5 | 236,416.9 | compute | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 2,825.26 | 93.0 | 23,819.4 | weight_read | 9.93x | 9.93x | 11.65x | 9.93x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 883.5 | 904,730.7 | compute | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 2,996.94 | 95.1 | 97,383.5 | weight_read | 9.29x | 9.29x | 10.72x | 9.45x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79 | 64,385 | 259.0 | 265,185.1 | compute | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 8,285.12 | 36.7 | 37,621.8 | weight_read | 7.05x | 7.05x | 8.09x | 7.05x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 313.9 | 1,285,835.7 | kv_read | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 3,561.78 | 37.6 | 154,086.9 | weight_read | 8.34x | 8.34x | 9.32x | 8.54x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79 | 64,385 | 66.4 | 272,120.9 | compute | DSV4-Flash/a100_sxm_80gb-x78-pipeline | 64,428 | 1.00x | pipeline | 661.34 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x9 | 416,025 | 2,103.7 | 2,103.7 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x504-hybrid | 416,304 | 1.00x | hybrid | 2,792.18 | 148.2 | 9,337.4 | link_latency | 14.19x | 0.11x | 54.79x | 14.20x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x190 | 154,850 | 613.3 | 613.3 | link_latency | DSV4-Pro/a100_sxm_80gb-x187-hybrid | 154,462 | 1.00x | hybrid | 2,632.18 | 150.2 | 3,604.1 | weight_read | 4.08x | 0.09x | 15.97x | 4.08x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 110,310.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 148.2 | 68,459.5 | link_latency | 11.28x | 0.78x | 43.53x | 13.02x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 110,310.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 148.2 | 68,459.5 | link_latency | 11.28x | 0.78x | 43.53x | 13.02x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 110,310.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 148.2 | 68,459.5 | link_latency | 11.28x | 0.78x | 43.53x | 13.02x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 110,310.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 148.2 | 68,459.5 | link_latency | 11.28x | 0.78x | 43.53x | 13.02x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 110,310.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 148.2 | 68,459.5 | link_latency | 11.28x | 0.78x | 43.53x | 13.02x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 110,310.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 148.2 | 68,459.5 | link_latency | 11.28x | 0.78x | 43.53x | 13.02x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,003.1 | 256,787.0 | kv_read | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 148.2 | 68,459.5 | link_latency | 6.77x | 1.81x | 26.12x | 7.82x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 362.1 | 370,797.3 | kv_read | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 4,012.72 | 109.3 | 111,912.3 | link_latency | 3.31x | 2.61x | 9.43x | 3.79x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 100.3 | 410,872.9 | kv_read | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 5,120.90 | 53.1 | 217,662.9 | weight_read | 1.89x | 1.89x | 2.71x | 2.20x |

## The headline is a band, and each side's share of it is reported apart

Every hop latency in this model states a range, and the ratio moves inside it.
This table re-runs the whole study at both ends of those ranges three ways:
the **wafer fabric** alone (`on_wafer`, `rom_wafer_serdes`, `rom_wafer_express`), which no GPU design touches; the
**cluster fabric** alone (`nvlink3`, `infiniband_hdr`), which is charged to both families; and
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
| DeepSeek-V4-Flash-0731 | 30,155 | 7.03x | 7.03x → 7.03x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 34,230 | 9.72x | 9.72x → 9.72x | 7.54x → 21.64x | — | 2.9x |
| DeepSeek-V4-Flash-0731 | 35,860 | 9.92x | 9.92x → 9.92x | 7.66x → 22.24x | 8.51x → 19.59x | 2.9x |
| DeepSeek-V4-Flash-0731 | 37,490 | 10.03x | 10.03x → 10.03x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 43,195 | 10.81x | 10.81x → 10.81x | 8.33x → 24.43x | 8.86x → 23.16x | 2.9x |
| DeepSeek-V4-Flash-0731 | 46,225 | 12.19x | 12.64x → 11.38x | 9.34x → 27.86x | 9.68x → 26.01x | 3.0x |
| DeepSeek-V4-Flash-0731 | 46,455 | 10.70x | 10.70x → 10.70x | 8.20x → 24.46x | 8.73x → 23.81x | 3.0x |
| DeepSeek-V4-Flash-0731 | 50,530 | 11.22x | 11.22x → 11.22x | 8.63x → 25.52x | — | 3.0x |
| DeepSeek-V4-Flash-0731 | 51,345 | 11.27x | 11.27x → 11.27x | 8.66x → 25.70x | 9.13x → 25.04x | 3.0x |
| DeepSeek-V4-Flash-0731 | 57,050 | 11.58x | 11.58x → 11.58x | 8.90x → 26.42x | 9.26x → 25.69x | 3.0x |
| DeepSeek-V4-Flash-0731 | 61,125 | 11.89x | 11.89x → 11.89x | 9.17x → 27.05x | — | 2.9x |
| DeepSeek-V4-Flash-0731 | 64,385 | 11.83x | 11.83x → 11.83x | 8.77x → 26.19x | 9.14x → 25.45x | 3.0x |
| DeepSeek-V4-Flash-0731 | 65,200 | 11.84x | 11.84x → 11.84x | 9.09x → 27.20x | 9.29x → 26.41x | 3.0x |
| DeepSeek-V4-Flash-0731 | 69,275 | 11.59x | 11.59x → 11.59x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 70,090 | 11.61x | 11.61x → 11.61x | 8.92x → 26.63x | 9.23x → 25.84x | 3.0x |
| DeepSeek-V4-Flash-0731 | 80,685 | 11.60x | 11.60x → 11.60x | 8.94x → 26.63x | 9.29x → 25.81x | 3.0x |
| DeepSeek-V4-Flash-0731 | 85,575 | 11.35x | 11.35x → 11.35x | 8.71x → 26.30x | 9.13x → 25.46x | 3.0x |
| DeepSeek-V4-Flash-0731 | 92,095 | 11.18x | 11.18x → 11.18x | 8.59x → 25.93x | 9.08x → 25.09x | 3.0x |
| DeepSeek-V4-Flash-0731 | 92,450 | 13.00x | 13.22x → 12.57x | 9.98x → 30.18x | 10.15x → 29.19x | 3.0x |
| DeepSeek-V4-Flash-0731 | 96,985 | 11.04x | 11.04x → 11.04x | 8.49x → 25.60x | 9.05x → 24.78x | 3.0x |
| DeepSeek-V4-Flash-0731 | 114,100 | 10.93x | 10.93x → 10.93x | 8.42x → 25.44x | 9.00x → 24.25x | 3.0x |
| DeepSeek-V4-Flash-0731 | 128,770 | 11.03x | 11.03x → 11.03x | 8.50x → 25.87x | 9.08x → 24.88x | 3.0x |
| DeepSeek-V4-Flash-0731 | 138,550 | 10.95x | 10.95x → 10.95x | 8.42x → 25.81x | 8.99x → 24.82x | 3.1x |
| DeepSeek-V4-Flash-0731 | 138,675 | 12.84x | 13.10x → 12.41x | 9.87x → 30.27x | 10.07x → 29.27x | 3.1x |
| DeepSeek-V4-Flash-0731 | 184,900 | 12.74x | 13.10x → 12.12x | 9.81x → 30.48x | 10.09x → 29.01x | 3.1x |
| DeepSeek-V4-Flash-0731 | 185,005 | 11.05x | 11.05x → 11.05x | 8.52x → 26.45x | 9.06x → 25.43x | 3.1x |
| DeepSeek-V4-Flash-0731 | 193,155 | 11.12x | 11.12x → 11.12x | 8.59x → 26.63x | 9.16x → 25.61x | 3.1x |
| DeepSeek-V4-Flash-0731 | 257,540 | 11.20x | 11.20x → 11.20x | 8.65x → 27.41x | 9.16x → 26.35x | 3.2x |
| DeepSeek-V4-Flash-0731 | 277,100 | 11.24x | 11.24x → 11.24x | 8.70x → 27.67x | 9.19x → 26.60x | 3.2x |
| DeepSeek-V4-Flash-0731 | 277,350 | 12.68x | 13.06x → 11.99x | 9.80x → 31.21x | 10.10x → 29.53x | 3.2x |
| DeepSeek-V4-Flash-0731 | 369,800 | 12.49x | 12.97x → 11.63x | 9.67x → 30.83x | 10.04x → 28.69x | 3.2x |
| DeepSeek-V4-Flash-0731 | 462,250 | 12.25x | 12.72x → 11.40x | 9.48x → 30.23x | 9.84x → 28.13x | 3.2x |
| DeepSeek-V4-Flash-0731 | 554,700 | 12.17x | 12.64x → 11.32x | 9.42x → 30.03x | 9.78x → 27.93x | 3.2x |
| DeepSeek-V4-Pro-0813 | 154,850 | 4.08x | 4.08x → 4.08x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 167,075 | 6.97x | 6.97x → 6.97x | 5.92x → 12.95x | — | 2.2x |
| DeepSeek-V4-Pro-0813 | 184,900 | 12.83x | 13.15x → 12.24x | 10.88x → 24.04x | 11.15x → 22.93x | 2.2x |
| DeepSeek-V4-Pro-0813 | 185,005 | 7.93x | 7.93x → 7.93x | 6.72x → 14.85x | 7.73x → 12.70x | 2.2x |
| DeepSeek-V4-Pro-0813 | 193,155 | 8.29x | 8.29x → 8.29x | 7.05x → 15.50x | 7.98x → 13.55x | 2.2x |
| DeepSeek-V4-Pro-0813 | 221,680 | 8.98x | 8.98x → 8.98x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 231,125 | 13.65x | 14.01x → 12.99x | 11.59x → 25.82x | 11.89x → 24.55x | 2.2x |
| DeepSeek-V4-Pro-0813 | 231,460 | 9.20x | 9.20x → 9.20x | 7.81x → 17.39x | 8.44x → 15.04x | 2.2x |
| DeepSeek-V4-Pro-0813 | 256,725 | 9.49x | 9.49x → 9.49x | 8.06x → 18.02x | — | 2.2x |
| DeepSeek-V4-Pro-0813 | 268,135 | 9.59x | 9.59x → 9.59x | 8.15x → 18.25x | — | 2.2x |
| DeepSeek-V4-Pro-0813 | 276,285 | 9.61x | 9.61x → 9.61x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 277,100 | 9.61x | 9.61x → 9.61x | 8.16x → 18.33x | 8.73x → 16.15x | 2.2x |
| DeepSeek-V4-Pro-0813 | 277,350 | 13.87x | 14.24x → 13.22x | 11.78x → 26.47x | 12.10x → 25.22x | 2.2x |
| DeepSeek-V4-Pro-0813 | 308,070 | 9.83x | 9.83x → 9.83x | 8.35x → 18.83x | 8.94x → 16.70x | 2.3x |
| DeepSeek-V4-Pro-0813 | 316,220 | 9.82x | 9.82x → 9.82x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 317,035 | 9.82x | 9.82x → 9.82x | 8.34x → 18.87x | 8.93x → 16.82x | 2.3x |
| DeepSeek-V4-Pro-0813 | 323,575 | 13.92x | 14.29x → 13.25x | 11.83x → 26.78x | 12.14x → 25.50x | 2.3x |
| DeepSeek-V4-Pro-0813 | 369,800 | 14.11x | 14.49x → 13.53x | 12.00x → 27.38x | 12.32x → 26.26x | 2.3x |
| DeepSeek-V4-Pro-0813 | 416,025 | 14.19x | 14.55x → 13.63x | 12.08x → 27.72x | 12.38x → 26.62x | 2.3x |
| DeepSeek-V4-Pro-0813 | 554,700 | 14.03x | 14.42x → 13.33x | 11.94x → 27.41x | 12.27x → 26.03x | 2.3x |
| DeepSeek-V4-Pro-0813 | 3,050,850 | 11.28x | 11.92x → 10.69x | 9.60x → 22.03x | 10.14x → 20.87x | 2.3x |
| Qwen3-8B | 4,075 | 16.56x | 16.56x → 16.56x | 15.32x → 23.03x | 15.80x → 21.35x | 1.5x |
| Qwen3-8B | 4,890 | 21.13x | 21.13x → 21.13x | 19.34x → 30.43x | 20.23x → 27.34x | 1.6x |
| Qwen3-8B | 5,705 | 22.13x | 22.13x → 22.13x | 20.07x → 32.84x | 21.14x → 29.06x | 1.6x |
| Qwen3-8B | 6,520 | 21.46x | 21.46x → 21.46x | 19.30x → 32.70x | 20.39x → 28.77x | 1.7x |
| Qwen3-8B | 8,150 | 25.36x | 25.36x → 25.36x | 21.00x → 39.42x | 23.18x → 31.83x | 1.9x |
| Qwen3-8B | 9,780 | 24.72x | 24.72x → 24.72x | 20.19x → 37.69x | 22.37x → 30.31x | 1.9x |
| Qwen3-8B | 12,225 | 23.24x | 23.24x → 23.24x | 19.05x → 35.34x | 21.17x → 29.44x | 1.9x |
| Qwen3-8B | 13,040 | 22.67x | 22.67x → 22.67x | 18.86x → 34.92x | 20.99x → 29.15x | 1.9x |
| Qwen3-8B | 46,225 | 21.64x | 22.35x → 20.35x | 16.36x → 40.39x | 16.89x → 37.98x | 2.5x |
| Qwen3-8B | 46,455 | 15.39x | 15.39x → 15.39x | 11.63x → 28.72x | 13.76x → 23.44x | 2.5x |
| Qwen3-8B | 56,235 | 13.96x | 13.96x → 13.96x | 10.50x → 27.35x | 12.93x → 22.46x | 2.6x |
| Qwen3-8B | 70,090 | 14.37x | 14.37x → 14.37x | 10.75x → 28.69x | — | 2.7x |
| Qwen3-8B | 70,905 | 14.39x | 14.39x → 14.39x | 10.76x → 28.64x | 12.65x → 22.77x | 2.7x |
| Qwen3-8B | 84,760 | 13.94x | 13.94x → 13.94x | 10.40x → 28.25x | 12.59x → 23.08x | 2.7x |
| Qwen3-8B | 92,095 | 14.11x | 14.11x → 14.11x | 10.51x → 28.86x | 12.63x → 22.82x | 2.7x |
| Qwen3-8B | 92,450 | 18.37x | 18.92x → 17.34x | 13.68x → 37.47x | 14.09x → 35.37x | 2.7x |
| Qwen3-8B | 112,470 | 13.92x | 13.92x → 13.92x | 10.34x → 29.15x | 12.21x → 23.71x | 2.8x |
| Qwen3-8B | 138,550 | 13.87x | 13.87x → 13.87x | 10.27x → 29.98x | 12.36x → 24.25x | 2.9x |
| Qwen3-8B | 138,675 | 16.36x | 17.66x → 15.50x | 12.11x → 35.34x | 13.08x → 33.50x | 2.9x |
| Qwen3-8B | 168,705 | 13.89x | 13.89x → 13.89x | 10.27x → 31.26x | 12.15x → 25.25x | 3.0x |
| Qwen3-8B | 184,900 | 15.27x | 17.44x → 14.08x | 11.28x → 34.63x | 12.88x → 31.92x | 3.1x |
| Qwen3-8B | 185,005 | 13.74x | 13.74x → 13.74x | 10.15x → 31.16x | 12.23x → 24.93x | 3.1x |
| Qwen3-8B | 224,940 | 13.86x | 13.86x → 13.86x | 10.22x → 32.64x | 12.12x → 25.75x | 3.2x |
| Qwen3-8B | 277,100 | 15.02x | 15.02x → 15.02x | 11.38x → 33.01x | 13.52x → 25.93x | 2.9x |
| Qwen3-8B | 277,350 | 15.36x | 18.11x → 12.98x | 11.64x → 33.74x | 13.72x → 28.51x | 2.9x |
| Qwen3-8B | 369,800 | 14.93x | 17.34x → 11.80x | 11.27x → 33.15x | 13.09x → 26.18x | 2.9x |
| Qwen3-8B | 554,700 | 14.98x | 17.34x → 11.84x | 11.33x → 32.95x | 13.12x → 26.04x | 2.9x |

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

| Fabric clock | GHz | In stated band | Qwen3-8B fixed latency/token | DeepSeek-V4-Flash-0731 @ 34,230 mm2 | DeepSeek-V4-Pro-0813 @ 184,900 mm2 | Qwen3-8B @ 4,890 mm2 |
|---|---:|---|---:|---:|---:|---:|
| `band_low` | 0.5000 | yes | 11.53 us | 9.72x | 12.83x | 21.13x |
| `stated` | 1.0000 | yes | 6.82 us | 9.72x | 12.83x | 21.13x |
| `band_high` | 2.0000 | yes | 4.46 us | 9.72x | 12.83x | 21.13x |
| `asap7_reduction_s8_g2` | 1.2874 | yes | 5.77 us | 9.72x | 12.83x | 21.13x |
| `asap7_add_bf16_sram_engine` | 0.2391 | **no** | 21.83 us | 9.72x | 12.83x | 21.13x |
| `asap7_matmul_bf16_sram_engine` | 0.0580 | **no** | 83.47 us | 9.72x | 12.83x | 21.13x |

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

| ROM cell ratio | Value | In stated band | ROM capacity | Full-array sweep | DeepSeek-V4-Flash-0731 @ 34,230 mm2 | DeepSeek-V4-Pro-0813 @ 184,900 mm2 | Qwen3-8B @ 4,890 mm2 |
|---|---:|---|---:|---:|---:|---:|---:|
| `band_low` | 0.1100 | yes | 21.886 MB/mm2 | 103.4 us | — | 14.02x | 22.87x |
| `stated` | 0.3300 | yes | 7.295 MB/mm2 | 34.5 us | 9.72x | 12.83x | 21.13x |
| `band_high` | 0.3300 | yes | 7.295 MB/mm2 | 34.5 us | 9.72x | 12.83x | 21.13x |
| `measured_ihp_sg13g2_130nm` | 0.1298 | yes | 18.553 MB/mm2 | 87.7 us | — | 14.06x | 22.87x |
| `measured_asap7_7nm_via_programmed` | 0.2500 | yes | 9.630 MB/mm2 | 45.5 us | — | 13.71x | 22.87x |
| `measured_asap7_7nm_shared_source_drain` | 0.1250 | yes | 19.259 MB/mm2 | 91.0 us | 11.82x | 14.08x | 22.87x |

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
| DeepSeek-V4-Flash-0731 | 19 | 15,694 | 130.9 | 179.6 | 316.1 | hybrid | 1,320.67 | 41.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 24 | 19,824 | 130.7 | 181.3 | 337.2 | hybrid | 1,320.67 | 44.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 37 | 30,562 | 130.1 | 173.7 | 329.7 | hybrid | 1,327.36 | 43.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 41 | 33,866 | 129.9 | 171.6 | 322.2 | hybrid | 1,330.70 | 42.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 35,518 | 129.8 | 171.6 | 326.5 | hybrid | 1,330.70 | 43.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 45 | 37,170 | 129.8 | 171.6 | 330.5 | hybrid | 1,330.70 | 44.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 52 | 42,952 | 129.8 | 169.9 | 329.3 | hybrid | 1,334.04 | 43.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 129.8 | 169.8 | 335.7 | hybrid | 1,334.04 | 44.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 61 | 50,386 | 129.8 | 168.4 | 331.2 | hybrid | 1,337.38 | 44.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 62 | 51,212 | 129.8 | 168.4 | 332.6 | hybrid | 1,337.38 | 44.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 69 | 56,994 | 129.8 | 156.7 | 331.3 | hybrid | 1,340.72 | 44.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 74 | 61,124 | 129.8 | 155.8 | 327.9 | hybrid | 1,344.06 | 44.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 78 | 64,428 | 129.8 | 155.6 | 332.4 | hybrid | 1,344.06 | 44.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 79 | 65,254 | 129.8 | 155.5 | 333.5 | hybrid | 1,344.06 | 44.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 81 | 66,906 | 129.8 | 154.9 | 327.1 | hybrid | 1,347.40 | 44.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 84 | 69,384 | 129.8 | 154.7 | 330.2 | hybrid | 1,347.40 | 44.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 85 | 70,210 | 129.8 | 154.6 | 331.3 | hybrid | 1,347.40 | 44.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 98 | 80,948 | 129.8 | 153.0 | 328.4 | hybrid | 1,354.09 | 44.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 104 | 85,904 | 129.8 | 152.6 | 333.4 | hybrid | 1,354.09 | 45.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 111 | 91,686 | 129.8 | 151.8 | 332.3 | hybrid | 1,357.43 | 45.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 129.8 | 151.7 | 333.1 | hybrid | 1,357.43 | 45.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 117 | 96,642 | 129.8 | 151.1 | 330.6 | hybrid | 1,360.77 | 45.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 138 | 113,988 | 129.8 | 149.0 | 328.0 | hybrid | 1,370.79 | 45.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 156 | 128,856 | 129.8 | 147.4 | 328.8 | hybrid | 1,377.48 | 45.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 129.8 | 146.4 | 330.5 | hybrid | 1,380.82 | 45.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 129.8 | 141.7 | 328.0 | hybrid | 1,404.21 | 46.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 234 | 193,284 | 129.8 | 140.9 | 325.2 | hybrid | 1,410.89 | 45.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 312 | 257,712 | 129.8 | 135.2 | 324.1 | hybrid | 1,440.96 | 46.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 335 | 276,710 | 129.8 | 118.4 | 322.8 | hybrid | 1,450.99 | 46.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 129.8 | 118.4 | 323.0 | hybrid | 1,450.99 | 46.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 129.8 | 112.7 | 322.7 | hybrid | 1,454.33 | 46.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 560 | 462,560 | 129.8 | 107.7 | 322.7 | hybrid | 1,454.33 | 46.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 129.8 | 103.0 | 322.7 | hybrid | 1,454.33 | 46.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 38.4 | 58.5 | 153.5 | hybrid | 2,558.67 | 39.3% | weight_read |
| DeepSeek-V4-Pro-0813 | 100 | 82,600 | 38.4 | 55.0 | 150.4 | hybrid | 2,584.61 | 38.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 110 | 90,860 | 38.4 | 54.6 | 151.7 | hybrid | 2,588.94 | 39.3% | weight_read |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 38.4 | 54.5 | 152.8 | hybrid | 2,588.94 | 39.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 38.4 | 50.7 | 152.1 | hybrid | 2,619.21 | 39.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 187 | 154,462 | 38.4 | 50.1 | 150.2 | hybrid | 2,632.18 | 39.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 202 | 166,852 | 38.4 | 49.6 | 149.8 | hybrid | 2,640.83 | 39.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 203 | 167,678 | 38.4 | 49.6 | 150.1 | hybrid | 2,640.83 | 39.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 208 | 171,808 | 38.4 | 49.5 | 151.6 | hybrid | 2,640.83 | 40.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 38.4 | 49.0 | 151.4 | hybrid | 2,649.48 | 40.1% | weight_read |
| DeepSeek-V4-Pro-0813 | 234 | 193,284 | 38.4 | 48.7 | 149.7 | hybrid | 2,658.13 | 39.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 268 | 221,368 | 38.4 | 47.7 | 149.9 | hybrid | 2,675.43 | 40.1% | weight_read |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 38.4 | 47.4 | 150.7 | hybrid | 2,679.75 | 40.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 311 | 256,886 | 38.4 | 46.7 | 150.1 | hybrid | 2,697.05 | 40.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 325 | 268,450 | 38.4 | 43.6 | 149.6 | hybrid | 2,705.70 | 40.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 334 | 275,884 | 38.4 | 43.4 | 149.7 | hybrid | 2,710.02 | 40.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 335 | 276,710 | 38.4 | 43.4 | 149.9 | hybrid | 2,710.02 | 40.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 38.4 | 43.3 | 150.0 | hybrid | 2,710.02 | 40.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 373 | 308,098 | 38.4 | 42.6 | 149.1 | hybrid | 2,731.64 | 40.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 383 | 316,358 | 38.4 | 42.4 | 149.3 | hybrid | 2,735.97 | 40.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 384 | 317,184 | 38.4 | 42.4 | 149.5 | hybrid | 2,735.97 | 40.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 392 | 323,792 | 38.4 | 42.2 | 149.4 | hybrid | 2,740.29 | 40.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 38.4 | 41.1 | 148.7 | hybrid | 2,770.56 | 41.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 504 | 416,304 | 38.4 | 40.1 | 148.2 | hybrid | 2,792.18 | 41.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 574 | 474,124 | 38.4 | 38.9 | 148.0 | hybrid | 2,792.18 | 41.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 38.4 | 37.4 | 148.2 | hybrid | 2,792.18 | 41.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 3694 | 3,051,244 | 38.4 | 17.0 | 148.2 | hybrid | 2,792.18 | 41.4% | link_latency |
| Qwen3-8B | 3 | 2,478 | 95.5 | 236.1 | — | tensor | 370.24 | 8.7% | weight_read |
| Qwen3-8B | 4 | 3,304 | 95.5 | 293.1 | — | tensor | 370.90 | 10.9% | weight_read |
| Qwen3-8B | 5 | 4,130 | 95.5 | 342.8 | — | tensor | 371.29 | 12.7% | weight_read |
| Qwen3-8B | 6 | 4,956 | 95.4 | 386.4 | — | tensor | 371.55 | 14.4% | weight_read |
| Qwen3-8B | 7 | 5,782 | 95.4 | 425.1 | — | tensor | 371.74 | 15.8% | weight_read |
| Qwen3-8B | 8 | 6,608 | 95.4 | 459.6 | — | tensor | 371.88 | 17.1% | weight_read |
| Qwen3-8B | 10 | 8,260 | 95.3 | 379.0 | 342.2 | tensor | 1,082.33 | 41.0% | link_latency |
| Qwen3-8B | 12 | 9,912 | 95.3 | 404.2 | 385.7 | tensor | 1,082.33 | 43.8% | link_latency |
| Qwen3-8B | 15 | 12,390 | 95.2 | 433.1 | 442.0 | hybrid | 376.27 | 16.6% | weight_read |
| Qwen3-8B | 16 | 13,216 | 95.2 | 441.0 | 458.7 | hybrid | 376.27 | 17.3% | weight_read |
| Qwen3-8B | 56 | 46,256 | 94.8 | 537.8 | 492.5 | tensor | 1,116.03 | 60.0% | link_latency |
| Qwen3-8B | 68 | 56,168 | 94.8 | 546.0 | 505.1 | tensor | 1,119.03 | 61.1% | link_latency |
| Qwen3-8B | 69 | 56,994 | 94.8 | 546.7 | 506.1 | tensor | 1,119.03 | 61.2% | link_latency |
| Qwen3-8B | 85 | 70,210 | 94.8 | 554.3 | 520.4 | tensor | 1,120.94 | 62.1% | link_latency |
| Qwen3-8B | 86 | 71,036 | 94.8 | 554.7 | 521.1 | tensor | 1,120.94 | 62.2% | link_latency |
| Qwen3-8B | 103 | 85,078 | 94.8 | 560.2 | 531.6 | tensor | 1,122.26 | 62.9% | link_latency |
| Qwen3-8B | 111 | 91,686 | 94.8 | 562.2 | 535.6 | tensor | 1,122.77 | 63.1% | link_latency |
| Qwen3-8B | 112 | 92,512 | 94.8 | 562.5 | 536.0 | tensor | 1,122.77 | 63.2% | link_latency |
| Qwen3-8B | 136 | 112,336 | 94.8 | 567.0 | 523.7 | tensor | 1,123.96 | 63.7% | link_latency |
| Qwen3-8B | 168 | 138,768 | 94.8 | 571.2 | 535.3 | tensor | 1,125.02 | 64.3% | link_latency |
| Qwen3-8B | 204 | 168,504 | 94.8 | 574.3 | 529.8 | tensor | 1,125.89 | 64.7% | link_latency |
| Qwen3-8B | 224 | 185,024 | 94.8 | 575.7 | 534.7 | tensor | 1,126.14 | 64.8% | link_latency |
| Qwen3-8B | 272 | 224,672 | 94.8 | 578.1 | 532.5 | tensor | 1,126.74 | 65.1% | link_latency |
| Qwen3-8B | 335 | 276,710 | 94.8 | 495.1 | 533.2 | hybrid | 1,131.54 | 60.3% | link_latency |
| Qwen3-8B | 336 | 277,536 | 94.8 | 495.1 | 533.3 | hybrid | 1,131.54 | 60.3% | link_latency |
| Qwen3-8B | 448 | 370,048 | 94.8 | 496.7 | 539.0 | hybrid | 1,133.89 | 61.1% | link_latency |
| Qwen3-8B | 672 | 555,072 | 94.8 | 498.4 | 534.2 | hybrid | 1,143.33 | 61.1% | link_latency |

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
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x7 | Qwen3-8B | 7 | pipeline | rom_package_ucie | rom_board_serdes | 6 | 0.16 us | 606,828.8 tok/s | 6,068,288.5 tok/s | 5 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.06 us; 1 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.10 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x7 | Qwen3-8B | 7 | tensor | rom_package_ucie | rom_board_serdes | 144 | 18.10 us | 5,523.9 tok/s | 55,238.6 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 2 on rom_board_serdes (traversals 2.2) = 16.33 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x7 | Qwen3-8B | 7 | hybrid | rom_package_ucie | rom_board_serdes | 73 | 1.88 us | 53,295.6 tok/s | 532,956.1 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 1 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.10 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x7 | Qwen3-8B | 7 | pipeline | nvlink3 | infiniband_hdr | 6 | 15.16 us | 6,594.6 tok/s | 65,946.4 tok/s | 6 x point_to_point span 2 on nvlink3 (traversals 1.0) = 15.16 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x7 | Qwen3-8B | 7 | tensor | nvlink3 | infiniband_hdr | 72 | 365.06 us | 273.9 tok/s | 2,739.3 tok/s | 72 x all_reduce span 7 on nvlink3 (traversals 2.0) = 365.06 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | rom_wafer_serdes | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | Qwen3-8B | 69 | pipeline | rom_package_ucie | rom_board_serdes | 35 | 1.16 us | 86,080.4 tok/s | 860,803.8 tok/s | 27 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.33 us; 8 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.84 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x69 | Qwen3-8B | 69 | tensor | rom_package_ucie | rom_board_serdes | 144 | 66.06 us | 1,513.8 tok/s | 15,137.7 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 18 on rom_board_serdes (traversals 8.8) = 64.29 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69 | Qwen3-8B | 69 | hybrid | rom_package_ucie | rom_board_serdes | 89 | 3.55 us | 28,175.8 tok/s | 281,758.0 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.78 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x69 | Qwen3-8B | 69 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8 | Qwen3-8B | 8 | pipeline | on_wafer | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x69 | Qwen3-8B | 69 | tensor | nvlink3 | infiniband_hdr | 144 | 720.40 us | 138.8 tok/s | 1,388.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 355.23 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x8 | Qwen3-8B | 8 | tensor | on_wafer | rom_wafer_serdes | 144 | 170.54 us | 586.4 tok/s | 5,863.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us; 72 x all_reduce span 8 on rom_wafer_serdes (traversals 4.4) = 31.94 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-hybrid-x69 | Qwen3-8B | 69 | hybrid | nvlink3 | infiniband_hdr | 80 | 384.02 us | 260.4 tok/s | 2,604.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8 | Qwen3-8B | 8 | hybrid | on_wafer | rom_wafer_serdes | 79 | 139.31 us | 717.8 tok/s | 7,178.3 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us; 7 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.71 us |
| Qwen3-8B/a100_sxm_80gb-x3-pipeline | Qwen3-8B | 3 | pipeline | nvlink3 | infiniband_hdr | 2 | 5.05 us | 19,783.9 tok/s | 197,839.1 tok/s | 2 x point_to_point span 2 on nvlink3 (traversals 1.0) = 5.05 us |
| Qwen3-8B/a100_sxm_80gb-x3-tensor | Qwen3-8B | 3 | tensor | nvlink3 | infiniband_hdr | 72 | 363.93 us | 274.8 tok/s | 2,747.8 tok/s | 72 x all_reduce span 3 on nvlink3 (traversals 2.0) = 363.93 us |
| Qwen3-8B/a100_sxm_80gb-x4-pipeline | Qwen3-8B | 4 | pipeline | nvlink3 | infiniband_hdr | 3 | 7.58 us | 13,189.3 tok/s | 131,892.7 tok/s | 3 x point_to_point span 2 on nvlink3 (traversals 1.0) = 7.58 us |
| Qwen3-8B/a100_sxm_80gb-x4-tensor | Qwen3-8B | 4 | tensor | nvlink3 | infiniband_hdr | 72 | 364.42 us | 274.4 tok/s | 2,744.1 tok/s | 72 x all_reduce span 4 on nvlink3 (traversals 2.0) = 364.42 us |
| Qwen3-8B/a100_sxm_80gb-x5-pipeline | Qwen3-8B | 5 | pipeline | nvlink3 | infiniband_hdr | 4 | 10.11 us | 9,892.0 tok/s | 98,919.5 tok/s | 4 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.11 us |
| Qwen3-8B/a100_sxm_80gb-x5-tensor | Qwen3-8B | 5 | tensor | nvlink3 | infiniband_hdr | 72 | 364.72 us | 274.2 tok/s | 2,741.8 tok/s | 72 x all_reduce span 5 on nvlink3 (traversals 2.0) = 364.72 us |
| Qwen3-8B/a100_sxm_80gb-x6-pipeline | Qwen3-8B | 6 | pipeline | nvlink3 | infiniband_hdr | 5 | 12.64 us | 7,913.6 tok/s | 79,135.6 tok/s | 5 x point_to_point span 2 on nvlink3 (traversals 1.0) = 12.64 us |
| Qwen3-8B/a100_sxm_80gb-x6-tensor | Qwen3-8B | 6 | tensor | nvlink3 | infiniband_hdr | 72 | 364.92 us | 274.0 tok/s | 2,740.4 tok/s | 72 x all_reduce span 6 on nvlink3 (traversals 2.0) = 364.92 us |
| Qwen3-8B/a100_sxm_80gb-x7-pipeline | Qwen3-8B | 7 | pipeline | nvlink3 | infiniband_hdr | 6 | 15.16 us | 6,594.6 tok/s | 65,946.4 tok/s | 6 x point_to_point span 2 on nvlink3 (traversals 1.0) = 15.16 us |
| Qwen3-8B/a100_sxm_80gb-x7-tensor | Qwen3-8B | 7 | tensor | nvlink3 | infiniband_hdr | 72 | 365.06 us | 273.9 tok/s | 2,739.3 tok/s | 72 x all_reduce span 7 on nvlink3 (traversals 2.0) = 365.06 us |
| Qwen3-8B/a100_sxm_80gb-x8-pipeline | Qwen3-8B | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 17.69 us | 5,652.5 tok/s | 56,525.4 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 17.69 us |
| Qwen3-8B/a100_sxm_80gb-x8-tensor | Qwen3-8B | 8 | tensor | nvlink3 | infiniband_hdr | 72 | 365.16 us | 273.9 tok/s | 2,738.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us |
| Qwen3-8B/a100_sxm_80gb-x10-pipeline | Qwen3-8B | 10 | pipeline | nvlink3 | infiniband_hdr | 9 | 22.58 us | 4,429.5 tok/s | 44,294.6 tok/s | 8 x point_to_point span 2 on nvlink3 (traversals 1.0) = 20.22 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x10-tensor | Qwen3-8B | 10 | tensor | nvlink3 | infiniband_hdr | 144 | 692.87 us | 144.3 tok/s | 1,443.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 327.71 us |
| Qwen3-8B/a100_sxm_80gb-x10-hybrid | Qwen3-8B | 10 | hybrid | nvlink3 | infiniband_hdr | 73 | 367.52 us | 272.1 tok/s | 2,721.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x12-pipeline | Qwen3-8B | 12 | pipeline | nvlink3 | infiniband_hdr | 11 | 27.63 us | 3,619.2 tok/s | 36,191.6 tok/s | 10 x point_to_point span 2 on nvlink3 (traversals 1.0) = 25.27 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x12-tensor | Qwen3-8B | 12 | tensor | nvlink3 | infiniband_hdr | 144 | 692.87 us | 144.3 tok/s | 1,443.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 327.71 us |
| Qwen3-8B/a100_sxm_80gb-x12-hybrid | Qwen3-8B | 12 | hybrid | nvlink3 | infiniband_hdr | 73 | 367.52 us | 272.1 tok/s | 2,721.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x15-pipeline | Qwen3-8B | 15 | pipeline | nvlink3 | infiniband_hdr | 14 | 35.21 us | 2,839.9 tok/s | 28,398.9 tok/s | 13 x point_to_point span 2 on nvlink3 (traversals 1.0) = 32.85 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x15-tensor | Qwen3-8B | 15 | tensor | nvlink3 | infiniband_hdr | 144 | 692.87 us | 144.3 tok/s | 1,443.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 327.71 us |
| Qwen3-8B/a100_sxm_80gb-x15-hybrid | Qwen3-8B | 15 | hybrid | nvlink3 | infiniband_hdr | 73 | 367.52 us | 272.1 tok/s | 2,721.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x16-pipeline | Qwen3-8B | 16 | pipeline | nvlink3 | infiniband_hdr | 15 | 37.74 us | 2,649.7 tok/s | 26,497.1 tok/s | 14 x point_to_point span 2 on nvlink3 (traversals 1.0) = 35.38 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x16-tensor | Qwen3-8B | 16 | tensor | nvlink3 | infiniband_hdr | 144 | 692.87 us | 144.3 tok/s | 1,443.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 327.71 us |
| Qwen3-8B/a100_sxm_80gb-x16-hybrid | Qwen3-8B | 16 | hybrid | nvlink3 | infiniband_hdr | 73 | 367.52 us | 272.1 tok/s | 2,721.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x56-pipeline | Qwen3-8B | 56 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x56-tensor | Qwen3-8B | 56 | tensor | nvlink3 | infiniband_hdr | 144 | 718.15 us | 139.2 tok/s | 1,392.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 352.99 us |
| Qwen3-8B/a100_sxm_80gb-x56-hybrid | Qwen3-8B | 56 | hybrid | nvlink3 | infiniband_hdr | 78 | 379.31 us | 263.6 tok/s | 2,636.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| Qwen3-8B/a100_sxm_80gb-x68-pipeline | Qwen3-8B | 68 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x68-tensor | Qwen3-8B | 68 | tensor | nvlink3 | infiniband_hdr | 144 | 720.40 us | 138.8 tok/s | 1,388.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 355.23 us |
| Qwen3-8B/a100_sxm_80gb-x68-hybrid | Qwen3-8B | 68 | hybrid | nvlink3 | infiniband_hdr | 80 | 384.02 us | 260.4 tok/s | 2,604.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| Qwen3-8B/a100_sxm_80gb-x69-pipeline | Qwen3-8B | 69 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x69-tensor | Qwen3-8B | 69 | tensor | nvlink3 | infiniband_hdr | 144 | 720.40 us | 138.8 tok/s | 1,388.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 355.23 us |
| Qwen3-8B/a100_sxm_80gb-x69-hybrid | Qwen3-8B | 69 | hybrid | nvlink3 | infiniband_hdr | 80 | 384.02 us | 260.4 tok/s | 2,604.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| Qwen3-8B/a100_sxm_80gb-x85-pipeline | Qwen3-8B | 85 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x85-tensor | Qwen3-8B | 85 | tensor | nvlink3 | infiniband_hdr | 144 | 721.83 us | 138.5 tok/s | 1,385.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 356.66 us |
| Qwen3-8B/a100_sxm_80gb-x85-hybrid | Qwen3-8B | 85 | hybrid | nvlink3 | infiniband_hdr | 82 | 388.74 us | 257.2 tok/s | 2,572.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| Qwen3-8B/a100_sxm_80gb-x86-pipeline | Qwen3-8B | 86 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x86-tensor | Qwen3-8B | 86 | tensor | nvlink3 | infiniband_hdr | 144 | 721.83 us | 138.5 tok/s | 1,385.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 356.66 us |
| Qwen3-8B/a100_sxm_80gb-x86-hybrid | Qwen3-8B | 86 | hybrid | nvlink3 | infiniband_hdr | 82 | 388.74 us | 257.2 tok/s | 2,572.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| Qwen3-8B/a100_sxm_80gb-x103-pipeline | Qwen3-8B | 103 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x103-tensor | Qwen3-8B | 103 | tensor | nvlink3 | infiniband_hdr | 144 | 722.82 us | 138.3 tok/s | 1,383.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 357.65 us |
| Qwen3-8B/a100_sxm_80gb-x103-hybrid | Qwen3-8B | 103 | hybrid | nvlink3 | infiniband_hdr | 84 | 393.45 us | 254.2 tok/s | 2,541.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.29 us |
| Qwen3-8B/a100_sxm_80gb-x111-pipeline | Qwen3-8B | 111 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x111-tensor | Qwen3-8B | 111 | tensor | nvlink3 | infiniband_hdr | 144 | 723.20 us | 138.3 tok/s | 1,382.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 358.04 us |
| Qwen3-8B/a100_sxm_80gb-x111-hybrid | Qwen3-8B | 111 | hybrid | nvlink3 | infiniband_hdr | 85 | 395.81 us | 252.6 tok/s | 2,526.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| Qwen3-8B/a100_sxm_80gb-x112-pipeline | Qwen3-8B | 112 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x112-tensor | Qwen3-8B | 112 | tensor | nvlink3 | infiniband_hdr | 144 | 723.20 us | 138.3 tok/s | 1,382.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 358.04 us |
| Qwen3-8B/a100_sxm_80gb-x112-hybrid | Qwen3-8B | 112 | hybrid | nvlink3 | infiniband_hdr | 85 | 395.81 us | 252.6 tok/s | 2,526.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| Qwen3-8B/a100_sxm_80gb-x136-pipeline | Qwen3-8B | 136 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x136-tensor | Qwen3-8B | 136 | tensor | nvlink3 | infiniband_hdr | 144 | 724.10 us | 138.1 tok/s | 1,381.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 358.94 us |
| Qwen3-8B/a100_sxm_80gb-x136-hybrid | Qwen3-8B | 136 | hybrid | nvlink3 | infiniband_hdr | 88 | 402.88 us | 248.2 tok/s | 2,482.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 37.72 us |
| Qwen3-8B/a100_sxm_80gb-x168-pipeline | Qwen3-8B | 168 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x168-tensor | Qwen3-8B | 168 | tensor | nvlink3 | infiniband_hdr | 144 | 724.89 us | 138.0 tok/s | 1,379.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 359.73 us |
| Qwen3-8B/a100_sxm_80gb-x168-hybrid | Qwen3-8B | 168 | hybrid | nvlink3 | infiniband_hdr | 92 | 412.31 us | 242.5 tok/s | 2,425.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| Qwen3-8B/a100_sxm_80gb-x204-pipeline | Qwen3-8B | 204 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x204-tensor | Qwen3-8B | 204 | tensor | nvlink3 | infiniband_hdr | 144 | 725.54 us | 137.8 tok/s | 1,378.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 360.38 us |
| Qwen3-8B/a100_sxm_80gb-x204-hybrid | Qwen3-8B | 204 | hybrid | nvlink3 | infiniband_hdr | 97 | 424.10 us | 235.8 tok/s | 2,357.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 58.94 us |
| Qwen3-8B/a100_sxm_80gb-x224-pipeline | Qwen3-8B | 224 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x224-tensor | Qwen3-8B | 224 | tensor | nvlink3 | infiniband_hdr | 144 | 725.73 us | 137.8 tok/s | 1,377.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 360.57 us |
| Qwen3-8B/a100_sxm_80gb-x224-hybrid | Qwen3-8B | 224 | hybrid | nvlink3 | infiniband_hdr | 99 | 428.82 us | 233.2 tok/s | 2,332.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| Qwen3-8B/a100_sxm_80gb-x272-pipeline | Qwen3-8B | 272 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x272-tensor | Qwen3-8B | 272 | tensor | nvlink3 | infiniband_hdr | 144 | 726.18 us | 137.7 tok/s | 1,377.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 361.02 us |
| Qwen3-8B/a100_sxm_80gb-x272-hybrid | Qwen3-8B | 272 | hybrid | nvlink3 | infiniband_hdr | 105 | 442.96 us | 225.8 tok/s | 2,257.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 77.80 us |
| Qwen3-8B/a100_sxm_80gb-x335-pipeline | Qwen3-8B | 335 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x335-tensor | Qwen3-8B | 335 | tensor | nvlink3 | infiniband_hdr | 144 | 1,018.89 us | 98.1 tok/s | 981.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 653.73 us |
| Qwen3-8B/a100_sxm_80gb-x335-hybrid | Qwen3-8B | 335 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x336-pipeline | Qwen3-8B | 336 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x336-tensor | Qwen3-8B | 336 | tensor | nvlink3 | infiniband_hdr | 144 | 1,018.89 us | 98.1 tok/s | 981.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 653.73 us |
| Qwen3-8B/a100_sxm_80gb-x336-hybrid | Qwen3-8B | 336 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x448-pipeline | Qwen3-8B | 448 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x448-tensor | Qwen3-8B | 448 | tensor | nvlink3 | infiniband_hdr | 144 | 1,019.32 us | 98.1 tok/s | 981.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 654.15 us |
| Qwen3-8B/a100_sxm_80gb-x448-hybrid | Qwen3-8B | 448 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x672-pipeline | Qwen3-8B | 672 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x672-tensor | Qwen3-8B | 672 | tensor | nvlink3 | infiniband_hdr | 144 | 1,019.74 us | 98.1 tok/s | 980.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 654.58 us |
| Qwen3-8B/a100_sxm_80gb-x672-hybrid | Qwen3-8B | 672 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x80 | DeepSeek-V4-Flash-0731 | 80 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x42 | DeepSeek-V4-Flash-0731 | 42 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.94 us | 1,668.2 tok/s | 16,682.3 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 11 on rom_board_serdes (traversals 6.6) = 57.83 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x75 | DeepSeek-V4-Flash-0731 | 75 | hybrid | rom_package_ucie | rom_board_serdes | 104 | 4.00 us | 25,011.2 tok/s | 250,112.1 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 18 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.88 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x79 | DeepSeek-V4-Flash-0731 | 79 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x37 | DeepSeek-V4-Flash-0731 | 37 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x46 | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x86 | DeepSeek-V4-Flash-0731 | 86 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x79 | DeepSeek-V4-Flash-0731 | 79 | tensor | rom_package_ucie | rom_board_serdes | 172 | 78.91 us | 1,267.2 tok/s | 12,672.4 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 20 on rom_board_serdes (traversals 8.8) = 76.80 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x80 | DeepSeek-V4-Flash-0731 | 80 | hybrid | rom_package_ucie | rom_board_serdes | 105 | 4.10 us | 24,373.8 tok/s | 243,738.4 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 19 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.99 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x85 | DeepSeek-V4-Flash-0731 | 85 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10 | DeepSeek-V4-Flash-0731 | 10 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x79 | DeepSeek-V4-Flash-0731 | 79 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x10 | DeepSeek-V4-Flash-0731 | 10 | tensor | on_wafer | rom_wafer_serdes | 172 | 222.63 us | 449.2 tok/s | 4,491.8 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 86 x all_reduce span 10 on rom_wafer_serdes (traversals 6.6) = 57.08 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x79 | DeepSeek-V4-Flash-0731 | 79 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | DeepSeek-V4-Flash-0731 | 10 | hybrid | on_wafer | rom_wafer_serdes | 95 | 166.46 us | 600.7 tok/s | 6,007.4 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 9 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.91 us |
| DSV4-Flash/a100_sxm_80gb-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 45.15 us | 2,214.7 tok/s | 22,147.3 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 40.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x19-expert | DeepSeek-V4-Flash-0731 | 19 | expert | nvlink3 | infiniband_hdr | 172 | 616.56 us | 162.2 tok/s | 1,621.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.48 us |
| DSV4-Flash/a100_sxm_80gb-x24-pipeline | DeepSeek-V4-Flash-0731 | 24 | pipeline | nvlink3 | infiniband_hdr | 23 | 57.79 us | 1,730.4 tok/s | 17,304.4 tok/s | 21 x point_to_point span 2 on nvlink3 (traversals 1.0) = 53.07 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x24-tensor | DeepSeek-V4-Flash-0731 | 24 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x24-hybrid | DeepSeek-V4-Flash-0731 | 24 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x24-expert | DeepSeek-V4-Flash-0731 | 24 | expert | nvlink3 | infiniband_hdr | 172 | 613.68 us | 163.0 tok/s | 1,629.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 432.05 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 181.63 us |
| DSV4-Flash/a100_sxm_80gb-x37-pipeline | DeepSeek-V4-Flash-0731 | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-tensor | DeepSeek-V4-Flash-0731 | 37 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x37-hybrid | DeepSeek-V4-Flash-0731 | 37 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-expert | DeepSeek-V4-Flash-0731 | 37 | expert | nvlink3 | infiniband_hdr | 172 | 610.69 us | 163.7 tok/s | 1,637.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.15 us |
| DSV4-Flash/a100_sxm_80gb-x41-pipeline | DeepSeek-V4-Flash-0731 | 41 | pipeline | nvlink3 | infiniband_hdr | 40 | 100.24 us | 997.6 tok/s | 9,975.6 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.46 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x41-tensor | DeepSeek-V4-Flash-0731 | 41 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x41-hybrid | DeepSeek-V4-Flash-0731 | 41 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x41-expert | DeepSeek-V4-Flash-0731 | 41 | expert | nvlink3 | infiniband_hdr | 172 | 609.94 us | 164.0 tok/s | 1,639.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.70 us |
| DSV4-Flash/a100_sxm_80gb-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink3 | infiniband_hdr | 172 | 609.75 us | 164.0 tok/s | 1,640.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.51 us |
| DSV4-Flash/a100_sxm_80gb-x45-pipeline | DeepSeek-V4-Flash-0731 | 45 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x45-tensor | DeepSeek-V4-Flash-0731 | 45 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x45-hybrid | DeepSeek-V4-Flash-0731 | 45 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x45-expert | DeepSeek-V4-Flash-0731 | 45 | expert | nvlink3 | infiniband_hdr | 172 | 609.57 us | 164.0 tok/s | 1,640.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.34 us |
| DSV4-Flash/a100_sxm_80gb-x52-pipeline | DeepSeek-V4-Flash-0731 | 52 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x52-tensor | DeepSeek-V4-Flash-0731 | 52 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x52-hybrid | DeepSeek-V4-Flash-0731 | 52 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x52-expert | DeepSeek-V4-Flash-0731 | 52 | expert | nvlink3 | infiniband_hdr | 172 | 608.86 us | 164.2 tok/s | 1,642.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.83 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x56-expert | DeepSeek-V4-Flash-0731 | 56 | expert | nvlink3 | infiniband_hdr | 172 | 608.48 us | 164.3 tok/s | 1,643.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.60 us |
| DSV4-Flash/a100_sxm_80gb-x61-pipeline | DeepSeek-V4-Flash-0731 | 61 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x61-tensor | DeepSeek-V4-Flash-0731 | 61 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x61-hybrid | DeepSeek-V4-Flash-0731 | 61 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x61-expert | DeepSeek-V4-Flash-0731 | 61 | expert | nvlink3 | infiniband_hdr | 172 | 608.23 us | 164.4 tok/s | 1,644.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.35 us |
| DSV4-Flash/a100_sxm_80gb-x62-pipeline | DeepSeek-V4-Flash-0731 | 62 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x62-tensor | DeepSeek-V4-Flash-0731 | 62 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x62-hybrid | DeepSeek-V4-Flash-0731 | 62 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x62-expert | DeepSeek-V4-Flash-0731 | 62 | expert | nvlink3 | infiniband_hdr | 172 | 608.19 us | 164.4 tok/s | 1,644.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.31 us |
| DSV4-Flash/a100_sxm_80gb-x69-pipeline | DeepSeek-V4-Flash-0731 | 69 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x69-tensor | DeepSeek-V4-Flash-0731 | 69 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x69-hybrid | DeepSeek-V4-Flash-0731 | 69 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x69-expert | DeepSeek-V4-Flash-0731 | 69 | expert | nvlink3 | infiniband_hdr | 172 | 607.80 us | 164.5 tok/s | 1,645.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.03 us |
| DSV4-Flash/a100_sxm_80gb-x74-pipeline | DeepSeek-V4-Flash-0731 | 74 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x74-tensor | DeepSeek-V4-Flash-0731 | 74 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x74-hybrid | DeepSeek-V4-Flash-0731 | 74 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x74-expert | DeepSeek-V4-Flash-0731 | 74 | expert | nvlink3 | infiniband_hdr | 172 | 607.55 us | 164.6 tok/s | 1,646.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.86 us |
| DSV4-Flash/a100_sxm_80gb-x78-pipeline | DeepSeek-V4-Flash-0731 | 78 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x78-tensor | DeepSeek-V4-Flash-0731 | 78 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x78-hybrid | DeepSeek-V4-Flash-0731 | 78 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x78-expert | DeepSeek-V4-Flash-0731 | 78 | expert | nvlink3 | infiniband_hdr | 172 | 607.43 us | 164.6 tok/s | 1,646.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.75 us |
| DSV4-Flash/a100_sxm_80gb-x79-pipeline | DeepSeek-V4-Flash-0731 | 79 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x79-tensor | DeepSeek-V4-Flash-0731 | 79 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x79-hybrid | DeepSeek-V4-Flash-0731 | 79 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x79-expert | DeepSeek-V4-Flash-0731 | 79 | expert | nvlink3 | infiniband_hdr | 172 | 607.41 us | 164.6 tok/s | 1,646.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.72 us |
| DSV4-Flash/a100_sxm_80gb-x81-pipeline | DeepSeek-V4-Flash-0731 | 81 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x81-tensor | DeepSeek-V4-Flash-0731 | 81 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x81-hybrid | DeepSeek-V4-Flash-0731 | 81 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x81-expert | DeepSeek-V4-Flash-0731 | 81 | expert | nvlink3 | infiniband_hdr | 172 | 607.28 us | 164.7 tok/s | 1,646.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.67 us |
| DSV4-Flash/a100_sxm_80gb-x84-pipeline | DeepSeek-V4-Flash-0731 | 84 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x84-tensor | DeepSeek-V4-Flash-0731 | 84 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x84-hybrid | DeepSeek-V4-Flash-0731 | 84 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x84-expert | DeepSeek-V4-Flash-0731 | 84 | expert | nvlink3 | infiniband_hdr | 172 | 607.21 us | 164.7 tok/s | 1,646.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.59 us |
| DSV4-Flash/a100_sxm_80gb-x85-pipeline | DeepSeek-V4-Flash-0731 | 85 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x85-tensor | DeepSeek-V4-Flash-0731 | 85 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x85-hybrid | DeepSeek-V4-Flash-0731 | 85 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x85-expert | DeepSeek-V4-Flash-0731 | 85 | expert | nvlink3 | infiniband_hdr | 172 | 607.19 us | 164.7 tok/s | 1,646.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.57 us |
| DSV4-Flash/a100_sxm_80gb-x98-pipeline | DeepSeek-V4-Flash-0731 | 98 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x98-tensor | DeepSeek-V4-Flash-0731 | 98 | tensor | nvlink3 | infiniband_hdr | 172 | 863.36 us | 115.8 tok/s | 1,158.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 427.20 us |
| DSV4-Flash/a100_sxm_80gb-x98-hybrid | DeepSeek-V4-Flash-0731 | 98 | hybrid | nvlink3 | infiniband_hdr | 98 | 464.46 us | 215.3 tok/s | 2,153.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.29 us |
| DSV4-Flash/a100_sxm_80gb-x98-expert | DeepSeek-V4-Flash-0731 | 98 | expert | nvlink3 | infiniband_hdr | 172 | 606.82 us | 164.8 tok/s | 1,647.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.51 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.31 us |
| DSV4-Flash/a100_sxm_80gb-x104-pipeline | DeepSeek-V4-Flash-0731 | 104 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x104-tensor | DeepSeek-V4-Flash-0731 | 104 | tensor | nvlink3 | infiniband_hdr | 172 | 863.36 us | 115.8 tok/s | 1,158.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 427.20 us |
| DSV4-Flash/a100_sxm_80gb-x104-hybrid | DeepSeek-V4-Flash-0731 | 104 | hybrid | nvlink3 | infiniband_hdr | 98 | 464.46 us | 215.3 tok/s | 2,153.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.29 us |
| DSV4-Flash/a100_sxm_80gb-x104-expert | DeepSeek-V4-Flash-0731 | 104 | expert | nvlink3 | infiniband_hdr | 172 | 606.68 us | 164.8 tok/s | 1,648.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.47 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.21 us |
| DSV4-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4-Flash-0731 | 111 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4-Flash-0731 | 111 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4-Flash-0731 | 111 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x111-expert | DeepSeek-V4-Flash-0731 | 111 | expert | nvlink3 | infiniband_hdr | 172 | 606.58 us | 164.9 tok/s | 1,648.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.47 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.10 us |
| DSV4-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Flash-0731 | 112 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Flash-0731 | 112 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Flash-0731 | 112 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x112-expert | DeepSeek-V4-Flash-0731 | 112 | expert | nvlink3 | infiniband_hdr | 172 | 606.53 us | 164.9 tok/s | 1,648.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.44 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.09 us |
| DSV4-Flash/a100_sxm_80gb-x117-pipeline | DeepSeek-V4-Flash-0731 | 117 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x117-tensor | DeepSeek-V4-Flash-0731 | 117 | tensor | nvlink3 | infiniband_hdr | 172 | 864.23 us | 115.7 tok/s | 1,157.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 428.07 us |
| DSV4-Flash/a100_sxm_80gb-x117-hybrid | DeepSeek-V4-Flash-0731 | 117 | hybrid | nvlink3 | infiniband_hdr | 100 | 469.17 us | 213.1 tok/s | 2,131.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.01 us |
| DSV4-Flash/a100_sxm_80gb-x117-expert | DeepSeek-V4-Flash-0731 | 117 | expert | nvlink3 | infiniband_hdr | 172 | 606.47 us | 164.9 tok/s | 1,648.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.44 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.03 us |
| DSV4-Flash/a100_sxm_80gb-x138-pipeline | DeepSeek-V4-Flash-0731 | 138 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x138-tensor | DeepSeek-V4-Flash-0731 | 138 | tensor | nvlink3 | infiniband_hdr | 172 | 865.17 us | 115.6 tok/s | 1,155.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 429.00 us |
| DSV4-Flash/a100_sxm_80gb-x138-hybrid | DeepSeek-V4-Flash-0731 | 138 | hybrid | nvlink3 | infiniband_hdr | 103 | 476.25 us | 210.0 tok/s | 2,099.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| DSV4-Flash/a100_sxm_80gb-x138-expert | DeepSeek-V4-Flash-0731 | 138 | expert | nvlink3 | infiniband_hdr | 172 | 606.17 us | 165.0 tok/s | 1,649.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.36 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.81 us |
| DSV4-Flash/a100_sxm_80gb-x156-pipeline | DeepSeek-V4-Flash-0731 | 156 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x156-tensor | DeepSeek-V4-Flash-0731 | 156 | tensor | nvlink3 | infiniband_hdr | 172 | 865.64 us | 115.5 tok/s | 1,155.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 429.47 us |
| DSV4-Flash/a100_sxm_80gb-x156-hybrid | DeepSeek-V4-Flash-0731 | 156 | hybrid | nvlink3 | infiniband_hdr | 105 | 480.96 us | 207.9 tok/s | 2,079.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 44.80 us |
| DSV4-Flash/a100_sxm_80gb-x156-expert | DeepSeek-V4-Flash-0731 | 156 | expert | nvlink3 | infiniband_hdr | 172 | 605.99 us | 165.0 tok/s | 1,650.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.32 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.66 us |
| DSV4-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Flash-0731 | 168 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Flash-0731 | 168 | tensor | nvlink3 | infiniband_hdr | 172 | 865.84 us | 115.5 tok/s | 1,154.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 429.68 us |
| DSV4-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Flash-0731 | 168 | hybrid | nvlink3 | infiniband_hdr | 106 | 483.32 us | 206.9 tok/s | 2,069.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| DSV4-Flash/a100_sxm_80gb-x168-expert | DeepSeek-V4-Flash-0731 | 168 | expert | nvlink3 | infiniband_hdr | 172 | 605.88 us | 165.0 tok/s | 1,650.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.29 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.59 us |
| DSV4-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Flash-0731 | 224 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Flash-0731 | 224 | tensor | nvlink3 | infiniband_hdr | 172 | 866.85 us | 115.4 tok/s | 1,153.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 430.68 us |
| DSV4-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Flash-0731 | 224 | hybrid | nvlink3 | infiniband_hdr | 113 | 499.82 us | 200.1 tok/s | 2,000.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| DSV4-Flash/a100_sxm_80gb-x224-expert | DeepSeek-V4-Flash-0731 | 224 | expert | nvlink3 | infiniband_hdr | 172 | 605.55 us | 165.1 tok/s | 1,651.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.22 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.33 us |
| DSV4-Flash/a100_sxm_80gb-x234-pipeline | DeepSeek-V4-Flash-0731 | 234 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x234-tensor | DeepSeek-V4-Flash-0731 | 234 | tensor | nvlink3 | infiniband_hdr | 172 | 867.05 us | 115.3 tok/s | 1,153.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 30 on infiniband_hdr (traversals 2.0) = 430.88 us |
| DSV4-Flash/a100_sxm_80gb-x234-hybrid | DeepSeek-V4-Flash-0731 | 234 | hybrid | nvlink3 | infiniband_hdr | 115 | 504.54 us | 198.2 tok/s | 1,982.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 29 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 68.37 us |
| DSV4-Flash/a100_sxm_80gb-x234-expert | DeepSeek-V4-Flash-0731 | 234 | expert | nvlink3 | infiniband_hdr | 172 | 605.52 us | 165.1 tok/s | 1,651.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.21 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.30 us |
| DSV4-Flash/a100_sxm_80gb-x312-pipeline | DeepSeek-V4-Flash-0731 | 312 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x312-tensor | DeepSeek-V4-Flash-0731 | 312 | tensor | nvlink3 | infiniband_hdr | 172 | 867.70 us | 115.2 tok/s | 1,152.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 39 on infiniband_hdr (traversals 2.0) = 431.53 us |
| DSV4-Flash/a100_sxm_80gb-x312-hybrid | DeepSeek-V4-Flash-0731 | 312 | hybrid | nvlink3 | infiniband_hdr | 124 | 525.76 us | 190.2 tok/s | 1,902.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 38 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 89.59 us |
| DSV4-Flash/a100_sxm_80gb-x312-expert | DeepSeek-V4-Flash-0731 | 312 | expert | nvlink3 | infiniband_hdr | 172 | 605.28 us | 165.2 tok/s | 1,652.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.16 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.12 us |
| DSV4-Flash/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Flash-0731 | 335 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Flash-0731 | 335 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.01 us | 82.2 tok/s | 821.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 780.85 us |
| DSV4-Flash/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Flash-0731 | 335 | hybrid | nvlink3 | infiniband_hdr | 127 | 532.83 us | 187.7 tok/s | 1,876.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| DSV4-Flash/a100_sxm_80gb-x335-expert | DeepSeek-V4-Flash-0731 | 335 | expert | nvlink3 | infiniband_hdr | 172 | 605.24 us | 165.2 tok/s | 1,652.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.15 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.08 us |
| DSV4-Flash/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Flash-0731 | 336 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Flash-0731 | 336 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.01 us | 82.2 tok/s | 821.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 780.85 us |
| DSV4-Flash/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Flash-0731 | 336 | hybrid | nvlink3 | infiniband_hdr | 127 | 532.83 us | 187.7 tok/s | 1,876.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| DSV4-Flash/a100_sxm_80gb-x336-expert | DeepSeek-V4-Flash-0731 | 336 | expert | nvlink3 | infiniband_hdr | 172 | 605.23 us | 165.2 tok/s | 1,652.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.15 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.08 us |
| DSV4-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Flash-0731 | 448 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Flash-0731 | 448 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.52 us | 82.1 tok/s | 821.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 781.35 us |
| DSV4-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Flash-0731 | 448 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x448-expert | DeepSeek-V4-Flash-0731 | 448 | expert | nvlink3 | infiniband_hdr | 172 | 605.07 us | 165.3 tok/s | 1,652.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.11 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 174.96 us |
| DSV4-Flash/a100_sxm_80gb-x560-pipeline | DeepSeek-V4-Flash-0731 | 560 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x560-tensor | DeepSeek-V4-Flash-0731 | 560 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.82 us | 82.1 tok/s | 821.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 70 on infiniband_hdr (traversals 4.0) = 781.65 us |
| DSV4-Flash/a100_sxm_80gb-x560-hybrid | DeepSeek-V4-Flash-0731 | 560 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x560-expert | DeepSeek-V4-Flash-0731 | 560 | expert | nvlink3 | infiniband_hdr | 172 | 604.97 us | 165.3 tok/s | 1,653.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.09 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 174.88 us |
| DSV4-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Flash-0731 | 672 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Flash-0731 | 672 | tensor | nvlink3 | infiniband_hdr | 172 | 1,218.02 us | 82.1 tok/s | 821.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 781.85 us |
| DSV4-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Flash-0731 | 672 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x672-expert | DeepSeek-V4-Flash-0731 | 672 | expert | nvlink3 | infiniband_hdr | 172 | 604.90 us | 165.3 tok/s | 1,653.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.07 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 174.83 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x389 | DeepSeek-V4-Pro-0813 | 389 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x205 | DeepSeek-V4-Pro-0813 | 205 | tensor | rom_package_ucie | rom_board_serdes | 244 | 194.16 us | 515.0 tok/s | 5,150.3 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 52 on rom_board_serdes (traversals 15.4) = 190.74 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x329 | DeepSeek-V4-Pro-0813 | 329 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x388 | DeepSeek-V4-Pro-0813 | 388 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x9 | DeepSeek-V4-Pro-0813 | 9 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x190 | DeepSeek-V4-Pro-0813 | 190 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | rom_wafer_serdes | 244 | 262.35 us | 381.2 tok/s | 3,811.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 27.50 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x272 | DeepSeek-V4-Pro-0813 | 272 | hybrid | nvlink3 | infiniband_hdr | 155 | 711.22 us | 140.6 tok/s | 1,406.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.91 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x6 | DeepSeek-V4-Pro-0813 | 6 | hybrid | on_wafer | rom_wafer_serdes | 127 | 235.36 us | 424.9 tok/s | 4,248.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 5 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.51 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | DeepSeek-V4-Pro-0813 | 66 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x66 | DeepSeek-V4-Pro-0813 | 66 | tensor | on_wafer | rom_wafer_serdes | 244 | 450.43 us | 222.0 tok/s | 2,220.1 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 66 on rom_wafer_serdes (traversals 17.6) = 215.58 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | DeepSeek-V4-Pro-0813 | 66 | hybrid | on_wafer | rom_wafer_serdes | 182 | 240.99 us | 414.9 tok/s | 4,149.5 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 60 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 6.14 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,300.52 us | 76.9 tok/s | 768.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 675.22 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 640.92 us | 156.0 tok/s | 1,560.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink3 | infiniband_hdr | 244 | 867.34 us | 115.3 tok/s | 1,152.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 612.19 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 255.16 us |
| DSV4-Pro/a100_sxm_80gb-x100-pipeline | DeepSeek-V4-Pro-0813 | 100 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x100-tensor | DeepSeek-V4-Pro-0813 | 100 | tensor | nvlink3 | infiniband_hdr | 244 | 1,314.36 us | 76.1 tok/s | 760.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 689.05 us |
| DSV4-Pro/a100_sxm_80gb-x100-hybrid | DeepSeek-V4-Pro-0813 | 100 | hybrid | nvlink3 | infiniband_hdr | 134 | 656.54 us | 152.3 tok/s | 1,523.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.24 us |
| DSV4-Pro/a100_sxm_80gb-x100-expert | DeepSeek-V4-Pro-0813 | 100 | expert | nvlink3 | infiniband_hdr | 244 | 863.13 us | 115.9 tok/s | 1,158.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.28 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.86 us |
| DSV4-Pro/a100_sxm_80gb-x110-pipeline | DeepSeek-V4-Pro-0813 | 110 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x110-tensor | DeepSeek-V4-Pro-0813 | 110 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x110-hybrid | DeepSeek-V4-Pro-0813 | 110 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x110-expert | DeepSeek-V4-Pro-0813 | 110 | expert | nvlink3 | infiniband_hdr | 244 | 862.65 us | 115.9 tok/s | 1,159.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.18 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.48 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x112-expert | DeepSeek-V4-Pro-0813 | 112 | expert | nvlink3 | infiniband_hdr | 244 | 862.50 us | 115.9 tok/s | 1,159.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.09 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.41 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.51 us | 75.7 tok/s | 757.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 695.20 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 677.37 us | 147.6 tok/s | 1,476.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| DSV4-Pro/a100_sxm_80gb-x168-expert | DeepSeek-V4-Pro-0813 | 168 | expert | nvlink3 | infiniband_hdr | 244 | 860.89 us | 116.2 tok/s | 1,161.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.73 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 250.16 us |
| DSV4-Pro/a100_sxm_80gb-x187-pipeline | DeepSeek-V4-Pro-0813 | 187 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x187-tensor | DeepSeek-V4-Pro-0813 | 187 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x187-hybrid | DeepSeek-V4-Pro-0813 | 187 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x187-expert | DeepSeek-V4-Pro-0813 | 187 | expert | nvlink3 | infiniband_hdr | 244 | 860.57 us | 116.2 tok/s | 1,162.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.67 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.90 us |
| DSV4-Pro/a100_sxm_80gb-x202-pipeline | DeepSeek-V4-Pro-0813 | 202 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x202-tensor | DeepSeek-V4-Pro-0813 | 202 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x202-hybrid | DeepSeek-V4-Pro-0813 | 202 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x202-expert | DeepSeek-V4-Pro-0813 | 202 | expert | nvlink3 | infiniband_hdr | 244 | 860.35 us | 116.2 tok/s | 1,162.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.61 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.74 us |
| DSV4-Pro/a100_sxm_80gb-x203-pipeline | DeepSeek-V4-Pro-0813 | 203 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x203-tensor | DeepSeek-V4-Pro-0813 | 203 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x203-hybrid | DeepSeek-V4-Pro-0813 | 203 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x203-expert | DeepSeek-V4-Pro-0813 | 203 | expert | nvlink3 | infiniband_hdr | 244 | 860.34 us | 116.2 tok/s | 1,162.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.61 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.73 us |
| DSV4-Pro/a100_sxm_80gb-x208-pipeline | DeepSeek-V4-Pro-0813 | 208 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x208-tensor | DeepSeek-V4-Pro-0813 | 208 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x208-hybrid | DeepSeek-V4-Pro-0813 | 208 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x208-expert | DeepSeek-V4-Pro-0813 | 208 | expert | nvlink3 | infiniband_hdr | 244 | 860.27 us | 116.2 tok/s | 1,162.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.59 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.68 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x224-expert | DeepSeek-V4-Pro-0813 | 224 | expert | nvlink3 | infiniband_hdr | 244 | 860.08 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.53 us |
| DSV4-Pro/a100_sxm_80gb-x234-pipeline | DeepSeek-V4-Pro-0813 | 234 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x234-tensor | DeepSeek-V4-Pro-0813 | 234 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.51 us | 75.6 tok/s | 755.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 30 on infiniband_hdr (traversals 2.0) = 698.20 us |
| DSV4-Pro/a100_sxm_80gb-x234-hybrid | DeepSeek-V4-Pro-0813 | 234 | hybrid | nvlink3 | infiniband_hdr | 151 | 700.80 us | 142.7 tok/s | 1,426.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 29 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.50 us |
| DSV4-Pro/a100_sxm_80gb-x234-expert | DeepSeek-V4-Pro-0813 | 234 | expert | nvlink3 | infiniband_hdr | 244 | 859.98 us | 116.3 tok/s | 1,162.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.53 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.45 us |
| DSV4-Pro/a100_sxm_80gb-x268-pipeline | DeepSeek-V4-Pro-0813 | 268 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x268-tensor | DeepSeek-V4-Pro-0813 | 268 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.33 us | 75.5 tok/s | 755.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 699.03 us |
| DSV4-Pro/a100_sxm_80gb-x268-hybrid | DeepSeek-V4-Pro-0813 | 268 | hybrid | nvlink3 | infiniband_hdr | 155 | 711.22 us | 140.6 tok/s | 1,406.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.91 us |
| DSV4-Pro/a100_sxm_80gb-x268-expert | DeepSeek-V4-Pro-0813 | 268 | expert | nvlink3 | infiniband_hdr | 244 | 859.69 us | 116.3 tok/s | 1,163.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.46 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.23 us |
| DSV4-Pro/a100_sxm_80gb-x280-pipeline | DeepSeek-V4-Pro-0813 | 280 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x280-tensor | DeepSeek-V4-Pro-0813 | 280 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.51 us | 75.5 tok/s | 755.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 699.20 us |
| DSV4-Pro/a100_sxm_80gb-x280-hybrid | DeepSeek-V4-Pro-0813 | 280 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/a100_sxm_80gb-x280-expert | DeepSeek-V4-Pro-0813 | 280 | expert | nvlink3 | infiniband_hdr | 244 | 859.60 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.44 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.16 us |
| DSV4-Pro/a100_sxm_80gb-x311-pipeline | DeepSeek-V4-Pro-0813 | 311 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x311-tensor | DeepSeek-V4-Pro-0813 | 311 | tensor | nvlink3 | infiniband_hdr | 244 | 1,325.12 us | 75.5 tok/s | 754.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 39 on infiniband_hdr (traversals 2.0) = 699.82 us |
| DSV4-Pro/a100_sxm_80gb-x311-hybrid | DeepSeek-V4-Pro-0813 | 311 | hybrid | nvlink3 | infiniband_hdr | 160 | 724.23 us | 138.1 tok/s | 1,380.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 38 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 98.93 us |
| DSV4-Pro/a100_sxm_80gb-x311-expert | DeepSeek-V4-Pro-0813 | 311 | expert | nvlink3 | infiniband_hdr | 244 | 859.41 us | 116.4 tok/s | 1,163.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.40 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.01 us |
| DSV4-Pro/a100_sxm_80gb-x325-pipeline | DeepSeek-V4-Pro-0813 | 325 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x325-tensor | DeepSeek-V4-Pro-0813 | 325 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.70 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 41 on infiniband_hdr (traversals 4.0) = 1,195.40 us |
| DSV4-Pro/a100_sxm_80gb-x325-hybrid | DeepSeek-V4-Pro-0813 | 325 | hybrid | nvlink3 | infiniband_hdr | 162 | 729.44 us | 137.1 tok/s | 1,370.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 40 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 104.14 us |
| DSV4-Pro/a100_sxm_80gb-x325-expert | DeepSeek-V4-Pro-0813 | 325 | expert | nvlink3 | infiniband_hdr | 244 | 859.33 us | 116.4 tok/s | 1,163.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.38 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.95 us |
| DSV4-Pro/a100_sxm_80gb-x334-pipeline | DeepSeek-V4-Pro-0813 | 334 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x334-tensor | DeepSeek-V4-Pro-0813 | 334 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x334-hybrid | DeepSeek-V4-Pro-0813 | 334 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x334-expert | DeepSeek-V4-Pro-0813 | 334 | expert | nvlink3 | infiniband_hdr | 244 | 859.29 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.37 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.92 us |
| DSV4-Pro/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Pro-0813 | 335 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Pro-0813 | 335 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Pro-0813 | 335 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x335-expert | DeepSeek-V4-Pro-0813 | 335 | expert | nvlink3 | infiniband_hdr | 244 | 859.29 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.37 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.91 us |
| DSV4-Pro/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Pro-0813 | 336 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Pro-0813 | 336 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Pro-0813 | 336 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x336-expert | DeepSeek-V4-Pro-0813 | 336 | expert | nvlink3 | infiniband_hdr | 244 | 859.27 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.36 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.91 us |
| DSV4-Pro/a100_sxm_80gb-x373-pipeline | DeepSeek-V4-Pro-0813 | 373 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x373-tensor | DeepSeek-V4-Pro-0813 | 373 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.36 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,196.05 us |
| DSV4-Pro/a100_sxm_80gb-x373-hybrid | DeepSeek-V4-Pro-0813 | 373 | hybrid | nvlink3 | infiniband_hdr | 168 | 745.06 us | 134.2 tok/s | 1,342.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 119.76 us |
| DSV4-Pro/a100_sxm_80gb-x373-expert | DeepSeek-V4-Pro-0813 | 373 | expert | nvlink3 | infiniband_hdr | 244 | 859.12 us | 116.4 tok/s | 1,164.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.33 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.79 us |
| DSV4-Pro/a100_sxm_80gb-x383-pipeline | DeepSeek-V4-Pro-0813 | 383 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x383-tensor | DeepSeek-V4-Pro-0813 | 383 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.45 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 1,196.15 us |
| DSV4-Pro/a100_sxm_80gb-x383-hybrid | DeepSeek-V4-Pro-0813 | 383 | hybrid | nvlink3 | infiniband_hdr | 169 | 747.67 us | 133.7 tok/s | 1,337.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 122.36 us |
| DSV4-Pro/a100_sxm_80gb-x383-expert | DeepSeek-V4-Pro-0813 | 383 | expert | nvlink3 | infiniband_hdr | 244 | 859.08 us | 116.4 tok/s | 1,164.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.33 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.76 us |
| DSV4-Pro/a100_sxm_80gb-x384-pipeline | DeepSeek-V4-Pro-0813 | 384 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x384-tensor | DeepSeek-V4-Pro-0813 | 384 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.45 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 1,196.15 us |
| DSV4-Pro/a100_sxm_80gb-x384-hybrid | DeepSeek-V4-Pro-0813 | 384 | hybrid | nvlink3 | infiniband_hdr | 169 | 747.67 us | 133.7 tok/s | 1,337.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 122.36 us |
| DSV4-Pro/a100_sxm_80gb-x384-expert | DeepSeek-V4-Pro-0813 | 384 | expert | nvlink3 | infiniband_hdr | 244 | 859.07 us | 116.4 tok/s | 1,164.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.32 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.75 us |
| DSV4-Pro/a100_sxm_80gb-x392-pipeline | DeepSeek-V4-Pro-0813 | 392 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x392-tensor | DeepSeek-V4-Pro-0813 | 392 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x392-hybrid | DeepSeek-V4-Pro-0813 | 392 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x392-expert | DeepSeek-V4-Pro-0813 | 392 | expert | nvlink3 | infiniband_hdr | 244 | 859.04 us | 116.4 tok/s | 1,164.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.31 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.73 us |
| DSV4-Pro/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Pro-0813 | 448 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Pro-0813 | 448 | tensor | nvlink3 | infiniband_hdr | 244 | 1,822.07 us | 54.9 tok/s | 548.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,196.77 us |
| DSV4-Pro/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Pro-0813 | 448 | hybrid | nvlink3 | infiniband_hdr | 177 | 768.49 us | 130.1 tok/s | 1,301.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 143.19 us |
| DSV4-Pro/a100_sxm_80gb-x448-expert | DeepSeek-V4-Pro-0813 | 448 | expert | nvlink3 | infiniband_hdr | 244 | 858.87 us | 116.4 tok/s | 1,164.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.27 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.60 us |
| DSV4-Pro/a100_sxm_80gb-x504-pipeline | DeepSeek-V4-Pro-0813 | 504 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x504-tensor | DeepSeek-V4-Pro-0813 | 504 | tensor | nvlink3 | infiniband_hdr | 244 | 1,822.49 us | 54.9 tok/s | 548.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 63 on infiniband_hdr (traversals 4.0) = 1,197.19 us |
| DSV4-Pro/a100_sxm_80gb-x504-hybrid | DeepSeek-V4-Pro-0813 | 504 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |
| DSV4-Pro/a100_sxm_80gb-x504-expert | DeepSeek-V4-Pro-0813 | 504 | expert | nvlink3 | infiniband_hdr | 244 | 858.74 us | 116.5 tok/s | 1,164.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.24 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.49 us |
| DSV4-Pro/a100_sxm_80gb-x574-pipeline | DeepSeek-V4-Pro-0813 | 574 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x574-tensor | DeepSeek-V4-Pro-0813 | 574 | tensor | nvlink3 | infiniband_hdr | 244 | 1,822.91 us | 54.9 tok/s | 548.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 72 on infiniband_hdr (traversals 4.0) = 1,197.60 us |
| DSV4-Pro/a100_sxm_80gb-x574-hybrid | DeepSeek-V4-Pro-0813 | 574 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |
| DSV4-Pro/a100_sxm_80gb-x574-expert | DeepSeek-V4-Pro-0813 | 574 | expert | nvlink3 | infiniband_hdr | 244 | 858.61 us | 116.5 tok/s | 1,164.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.22 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.39 us |
| DSV4-Pro/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Pro-0813 | 672 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Pro-0813 | 672 | tensor | nvlink3 | infiniband_hdr | 244 | 1,823.32 us | 54.8 tok/s | 548.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,198.02 us |
| DSV4-Pro/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Pro-0813 | 672 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |
| DSV4-Pro/a100_sxm_80gb-x672-expert | DeepSeek-V4-Pro-0813 | 672 | expert | nvlink3 | infiniband_hdr | 244 | 858.47 us | 116.5 tok/s | 1,164.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.18 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.28 us |
| DSV4-Pro/a100_sxm_80gb-x3694-pipeline | DeepSeek-V4-Pro-0813 | 3694 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x3694-tensor | DeepSeek-V4-Pro-0813 | 3694 | tensor | nvlink3 | infiniband_hdr | 244 | 1,825.37 us | 54.8 tok/s | 547.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 462 on infiniband_hdr (traversals 4.0) = 1,200.06 us |
| DSV4-Pro/a100_sxm_80gb-x3694-hybrid | DeepSeek-V4-Pro-0813 | 3694 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |
| DSV4-Pro/a100_sxm_80gb-x3694-expert | DeepSeek-V4-Pro-0813 | 3694 | expert | nvlink3 | infiniband_hdr | 244 | 857.81 us | 116.6 tok/s | 1,165.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.03 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 247.77 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 11,638.4 | 0.252 | 9,994.6 (9,780) | 11,638.4 (46,225) | 1.16x | layer_fixed_latency |
| Qwen3-8B | 2 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 7,622.6 | 0.136 | 7,622.6 (56,235) | 8,007.6 (369,800) | 1.05x | layer_fixed_latency |
| Qwen3-8B | 4 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x104-romfill | 84,760 | 7,810.4 | 0.092 | 7,810.4 (84,760) | 7,275.2 (369,800) | 0.93x | layer_fixed_latency |
| Qwen3-8B | 8 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x138-romfill | 112,470 | 7,712.8 | 0.069 | 7,712.8 (112,470) | 6,194.5 (369,800) | 0.80x | layer_fixed_latency |
| Qwen3-8B | 16 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 7,650.1 | 0.034 | 7,650.1 (224,940) | 5,011.4 (554,700) | 0.66x | layer_fixed_latency |
| Qwen3-8B | 32 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 5,943.0 | 0.026 | 5,943.0 (224,940) | 3,240.6 (554,700) | 0.55x | kv_read |
| Qwen3-8B | 64 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 4,555.8 | 0.016 | 4,555.8 (277,100) | 1,892.1 (554,700) | 0.42x | kv_read |
| Qwen3-8B | 256 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 1,594.7 | 0.006 | 1,594.7 (277,100) | 532.8 (554,700) | 0.33x | kv_read |
| Qwen3-8B | 1024 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 431.0 | 0.002 | 431.0 (277,100) | 136.7 (554,700) | 0.32x | kv_read |
| Qwen3-8B | 4096 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 111.0 | 0.000 | 111.0 (277,100) | 34.4 (554,700) | 0.31x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 4,328.6 | 0.047 | 3,836.0 (57,050) | 4,328.6 (92,450) | 1.13x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 3,797.0 | 0.059 | 3,797.0 (64,385) | 3,953.0 (462,250) | 1.04x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 3,797.0 | 0.059 | 3,797.0 (64,385) | 3,953.0 (462,250) | 1.04x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 3,797.0 | 0.059 | 3,797.0 (64,385) | 3,953.0 (462,250) | 1.04x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 3,797.0 | 0.059 | 3,797.0 (64,385) | 3,829.7 (462,250) | 1.01x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x99 | 80,685 | 3,586.8 | 0.044 | 3,586.8 (80,685) | 3,393.7 (462,250) | 0.95x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x237-romfill | 193,155 | 3,472.0 | 0.018 | 3,472.0 (193,155) | 2,972.3 (554,700) | 0.86x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill | 257,540 | 2,197.7 | 0.009 | 2,197.7 (257,540) | 1,483.1 (554,700) | 0.67x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 1024 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316 | 257,540 | 848.7 | 0.003 | 848.7 (257,540) | 480.3 (554,700) | 0.57x | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316 | 257,540 | 303.3 | 0.001 | 303.3 (257,540) | 128.2 (554,700) | 0.42x | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x5-romfill | 231,125 | 2,057.9 | 0.009 | 1,424.2 (256,725) | 2,057.9 (231,125) | 1.44x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 0.001 | — (—) | 1,671.4 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 0.001 | — (—) | 1,671.4 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 0.001 | — (—) | 1,671.4 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 0.001 | — (—) | 1,671.4 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 0.001 | — (—) | 1,671.4 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,671.4 | 0.001 | — (—) | 1,671.4 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,003.1 | 0.000 | — (—) | 1,003.1 (3,050,850) | — | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 362.1 | 0.000 | — (—) | 362.1 (3,050,850) | — | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 100.3 | 0.000 | — (—) | 100.3 (3,050,850) | — | kv_read |

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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 126.1 mm2 | 22.70 mm2 (18.0%) | 32,278 mm2 | 5,810 mm2 | 36,600 mm2 = 44.9 reticles |
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
| Qwen3-8B | 1 | sram | 28,191.7 | 28,167.2 | 28,167.2 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 28,191.7 | 28,167.2 | 28,167.2 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 28,191.7 | 28,167.2 | 28,167.2 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 39,906.9 | 28,167.2 | 28,167.2 | 1.42x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 66,891.9 | 28,167.2 | 28,167.2 | 2.37x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 100,257.7 | 28,167.2 | 28,167.2 | 3.56x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 155,027.5 | 28,256.3 | 28,256.3 | 5.49x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 312,572.1 | 26,024.7 | 26,024.7 | 12.01x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1024 | sram | 434,021.5 | 26,073.2 | 26,073.2 | 16.65x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 4096 | sram | 454,472.4 | 26,102.3 | 26,102.3 | 17.41x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 420,498.3 | 103,913.8 | 103,913.8 | 4.05x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 420,498.3 | 103,913.8 | 103,913.8 | 4.05x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 420,498.3 | 103,913.8 | 103,913.8 | 4.05x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 420,498.3 | 103,913.8 | 103,913.8 | 4.05x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 420,498.3 | 103,913.8 | 103,913.8 | 4.05x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 420,498.3 | 103,913.8 | 103,913.8 | 4.05x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 420,498.3 | 103,913.8 | 103,913.8 | 4.05x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 420,498.3 | 108,867.5 | 108,867.5 | 3.86x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1024 | rom | 441,352.1 | 110,877.6 | 110,877.6 | 3.98x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4096 | rom | 449,151.6 | 111,391.6 | 111,391.6 | 4.03x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 359,396.4 | 26,113.2 | 26,113.2 | 13.76x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 359,396.4 | 26,113.2 | 26,113.2 | 13.76x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 359,396.4 | 26,113.2 | 26,113.2 | 13.76x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 359,396.4 | 26,113.2 | 26,113.2 | 13.76x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 359,396.4 | 26,113.2 | 29,771.9 | 13.76x | 1.14x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 359,396.4 | 26,113.2 | 45,614.9 | 13.76x | 1.75x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 359,396.4 | 26,113.2 | 67,805.9 | 13.76x | 2.60x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 477,788.0 | 26,113.2 | 144,384.2 | 18.30x | 5.53x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 869,117.1 | 26,113.2 | 252,508.8 | 33.28x | 9.67x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 1,285,835.7 | 26,113.2 | 391,558.1 | 49.24x | 14.99x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 704,779.2 | 397,390.1 | 397,390.1 | 1.77x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 704,779.2 | 397,390.1 | 397,390.1 | 1.77x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 704,779.2 | 397,390.1 | 397,390.1 | 1.77x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 704,779.2 | 397,390.1 | 397,390.1 | 1.77x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 704,779.2 | 397,390.1 | 397,390.1 | 1.77x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 704,779.2 | 397,390.1 | 397,390.1 | 1.77x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 704,779.2 | 397,390.1 | 397,390.1 | 1.77x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 704,779.2 | 397,390.1 | 397,390.1 | 1.77x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 904,730.7 | 417,718.0 | 416,499.8 | 2.17x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 1,009,518.9 | 438,707.7 | 435,860.5 | 2.30x | 0.99x | compute | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 409,865.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 409,865.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 409,865.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 409,865.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 409,865.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 409,865.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 409,865.7 | 26,113.2 | 38,935.4 | 15.70x | 1.49x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 409,865.7 | 26,113.2 | 77,271.9 | 15.70x | 2.96x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 409,865.7 | 26,113.2 | 166,088.0 | 15.70x | 6.36x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 410,872.9 | 26,113.2 | 311,600.6 | 15.73x | 11.93x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 406,113.7 | 408,448.2 | 408,448.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 406,113.7 | 408,448.2 | 408,448.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 406,113.7 | 408,448.2 | 408,448.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 406,113.7 | 408,448.2 | 408,448.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 406,113.7 | 408,448.2 | 408,448.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 406,113.7 | 408,448.2 | 408,448.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 406,113.7 | 408,448.2 | 408,448.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 406,113.7 | 408,448.2 | 408,448.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 406,113.7 | 408,448.2 | 408,448.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 407,219.2 | 409,602.9 | 409,424.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,191.7 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 420,498.3 | 1.517 | kv_read | 14.92x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 3.69x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 3.69x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,191.7 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 420,498.3 | 1.517 | kv_read | 14.92x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 3.69x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 3.69x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,191.7 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 420,498.3 | 1.517 | kv_read | 14.92x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 3.69x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 3.69x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 39,906.9 | 0.108 | kv_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 420,498.3 | 1.517 | kv_read | 10.54x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 0.71x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 2.60x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 0.71x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 2.60x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 66,891.9 | 0.121 | kv_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 420,498.3 | 1.517 | kv_read | 6.29x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 0.42x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 1.55x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 0.42x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 1.55x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x138 | 112,470 | 1.00 | 1.00 | 100,257.7 | 0.891 | weight_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 420,498.3 | 1.517 | kv_read | 4.19x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 0.28x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 1.04x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,167.2 | 0.609 | weight_read | 0.28x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 1.04x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x207 | 168,705 | 1.00 | 1.00 | 155,027.5 | 0.919 | weight_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 420,498.3 | 1.517 | kv_read | 2.71x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,256.3 | 0.611 | weight_read | 0.18x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 0.67x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 28,256.3 | 0.611 | weight_read | 0.18x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 1.00 | 103,913.8 | 1.483 | kv_read | 0.67x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276 | 224,940 | 1.00 | 1.00 | 312,572.1 | 1.390 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 420,498.3 | 1.517 | kv_read | 1.35x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream | 369,800 | 1.00 | 1.00 | 26,024.7 | 0.070 | weight_read | 0.08x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 2.98 | 108,867.5 | 1.553 | kv_read | 0.35x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion | 369,800 | 1.00 | 1.00 | 26,024.7 | 0.070 | weight_read | 0.08x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 2.98 | 108,867.5 | 1.553 | kv_read | 0.35x |
| Qwen3-8B | 1024 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 434,021.5 | 1.566 | kv_read | 1.00x |
| Qwen3-8B | 1024 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 441,352.1 | 1.593 | kv_read | 1.02x |
| Qwen3-8B | 1024 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream | 369,800 | 1.00 | 2.26 | 26,073.2 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 1024 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 11.91 | 110,877.6 | 1.582 | kv_read | 0.26x |
| Qwen3-8B | 1024 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion | 369,800 | 1.00 | 2.26 | 26,073.2 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 1024 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 11.91 | 110,877.6 | 1.582 | kv_read | 0.26x |
| Qwen3-8B | 4096 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 454,472.4 | 1.640 | kv_read | 1.00x |
| Qwen3-8B | 4096 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 449,151.6 | 1.621 | kv_read | 0.99x |
| Qwen3-8B | 4096 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream | 369,800 | 1.00 | 9.02 | 26,102.3 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 4096 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perstream-romfill | 70,090 | 45.15 | 47.63 | 111,391.6 | 1.589 | kv_read | 0.25x |
| Qwen3-8B | 4096 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion | 369,800 | 1.00 | 9.02 | 26,102.3 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 4096 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x86-perregion-romfill | 70,090 | 45.15 | 47.63 | 111,391.6 | 1.589 | kv_read | 0.25x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,396.4 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 704,779.2 | 2.543 | compute | 1.96x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,396.4 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 704,779.2 | 2.543 | compute | 1.96x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,396.4 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 704,779.2 | 2.543 | compute | 1.96x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,396.4 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 704,779.2 | 2.543 | compute | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,396.4 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 704,779.2 | 2.543 | compute | 1.96x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 1.39 | 29,771.9 | 0.064 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,396.4 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 704,779.2 | 2.543 | compute | 1.96x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 1.97 | 45,614.9 | 0.099 | weight_read | 0.13x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,396.4 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 704,779.2 | 2.543 | compute | 1.96x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 2.57 | 67,805.9 | 0.147 | weight_read | 0.19x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1.00 | 1.00 | 477,788.0 | 2.583 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 704,779.2 | 2.543 | compute | 1.48x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 0.83x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 3.59 | 144,384.2 | 0.312 | weight_read | 0.30x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,390.1 | 0.860 | kv_read | 0.83x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316 | 257,540 | 1.00 | 1.00 | 869,117.1 | 3.375 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 904,730.7 | 3.265 | compute | 1.04x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79-perstream | 64,385 | 1.00 | 12.96 | 26,113.2 | 0.406 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.80 | 417,718.0 | 0.904 | kv_read | 0.48x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 7.67 | 252,508.8 | 0.546 | weight_read | 0.29x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.10 | 416,499.8 | 0.901 | kv_read | 0.48x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 1,285,835.7 | 4.640 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,009,518.9 | 3.643 | compute | 0.79x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79-perstream | 64,385 | 1.00 | 51.85 | 26,113.2 | 0.406 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 7.21 | 438,707.7 | 0.949 | kv_read | 0.34x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 12.78 | 391,558.1 | 0.847 | kv_read | 0.30x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 2.06 | 435,860.5 | 0.943 | kv_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,865.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,113.7 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,865.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,113.7 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,865.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,113.7 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,865.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,113.7 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,865.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,113.7 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,865.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,113.7 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,865.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,113.7 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66-perregion | 3,050,850 | 1.00 | 1.39 | 38,935.4 | 0.013 | weight_read | 0.09x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,865.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,113.7 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66-perregion | 3,050,850 | 1.00 | 1.97 | 77,271.9 | 0.025 | weight_read | 0.19x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,865.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,113.7 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66-perregion | 3,050,850 | 1.00 | 3.44 | 166,088.0 | 0.054 | weight_read | 0.41x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,448.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 410,872.9 | 0.135 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 407,219.2 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.09 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.09 | 409,602.9 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66-perregion | 3,050,850 | 1.00 | 4.84 | 311,600.6 | 0.102 | weight_read | 0.76x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.01 | 409,424.1 | 0.134 | kv_read | 1.00x |

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
| Qwen3-8B | 1 | 3 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 4 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 57 | 1.12 | 1.123 | 1.123 | 1.00x |
| Qwen3-8B | 256 | 69 | 3.71 | 3.710 | 3.710 | 1.00x |
| Qwen3-8B | 1024 | 69 | 14.84 | 14.841 | 14.841 | 1.00x |
| Qwen3-8B | 4096 | 69 | 59.36 | 59.362 | 59.362 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 79 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | 79 | 3.24 | 1.027 | 1.398 | 1.36x |
| DeepSeek-V4-Flash-0731 | 1024 | 79 | 12.96 | 1.148 | 2.591 | 2.26x |
| DeepSeek-V4-Flash-0731 | 4096 | 79 | 51.85 | 1.717 | 5.191 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 101 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 3,744 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 3,744 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 3,744 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 3,744 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 3,744 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 3,744 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | 3,744 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | 3,744 | 1.09 | 1.001 | 1.006 | 1.01x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 8.99 | 5.12 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 13.57 | 6.62 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 17.26 | 8.21 | 2.10x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 18.76 | 9.75 | 1.92x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 18.99 | 11.05 | 1.72x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 19.00 | 11.97 | 1.59x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4-Flash-0731 | 2 | 24 | 9.51 | 5.51 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 24 | 15.05 | 7.28 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 24 | 20.35 | 9.21 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 24 | 23.23 | 11.14 | 2.09x |
| DeepSeek-V4-Flash-0731 | 32 | 24 | 23.93 | 12.82 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 24 | 24.00 | 14.03 | 1.71x |
| DeepSeek-V4-Flash-0731 | 256 | 24 | 24.00 | 14.78 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 24 | 24.00 | 14.79 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 37 | 10.26 | 6.23 | 1.65x |
| DeepSeek-V4-Flash-0731 | 4 | 37 | 17.39 | 8.55 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 37 | 25.99 | 11.20 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 37 | 32.96 | 14.00 | 2.35x |
| DeepSeek-V4-Flash-0731 | 32 | 37 | 36.11 | 16.57 | 2.18x |
| DeepSeek-V4-Flash-0731 | 64 | 37 | 36.85 | 18.50 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 37 | 36.97 | 19.73 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1024 | 37 | 36.97 | 19.74 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 41 | 10.41 | 6.41 | 1.62x |
| DeepSeek-V4-Flash-0731 | 4 | 41 | 17.86 | 8.85 | 2.02x |
| DeepSeek-V4-Flash-0731 | 8 | 41 | 27.25 | 11.69 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 41 | 35.43 | 14.72 | 2.41x |
| DeepSeek-V4-Flash-0731 | 32 | 41 | 39.58 | 17.55 | 2.25x |
| DeepSeek-V4-Flash-0731 | 64 | 41 | 40.71 | 19.69 | 2.07x |
| DeepSeek-V4-Flash-0731 | 256 | 41 | 40.93 | 21.05 | 1.94x |
| DeepSeek-V4-Flash-0731 | 1024 | 41 | 40.93 | 21.07 | 1.94x |
| DeepSeek-V4-Flash-0731 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 43 | 10.47 | 6.49 | 1.61x |
| DeepSeek-V4-Flash-0731 | 4 | 43 | 18.07 | 9.00 | 2.01x |
| DeepSeek-V4-Flash-0731 | 8 | 43 | 27.82 | 11.92 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 43 | 36.58 | 15.07 | 2.43x |
| DeepSeek-V4-Flash-0731 | 32 | 43 | 41.25 | 18.02 | 2.29x |
| DeepSeek-V4-Flash-0731 | 64 | 43 | 42.61 | 20.26 | 2.10x |
| DeepSeek-V4-Flash-0731 | 256 | 43 | 42.89 | 21.69 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1024 | 43 | 42.90 | 21.70 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 45 | 10.53 | 6.57 | 1.60x |
| DeepSeek-V4-Flash-0731 | 4 | 45 | 18.26 | 9.13 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 45 | 28.35 | 12.14 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 45 | 37.68 | 15.40 | 2.45x |
| DeepSeek-V4-Flash-0731 | 32 | 45 | 42.89 | 18.47 | 2.32x |
| DeepSeek-V4-Flash-0731 | 64 | 45 | 44.50 | 20.81 | 2.14x |
| DeepSeek-V4-Flash-0731 | 256 | 45 | 44.86 | 22.31 | 2.01x |
| DeepSeek-V4-Flash-0731 | 1024 | 45 | 44.86 | 22.32 | 2.01x |
| DeepSeek-V4-Flash-0731 | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 52 | 10.70 | 6.83 | 1.57x |
| DeepSeek-V4-Flash-0731 | 4 | 52 | 18.84 | 9.55 | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | 52 | 29.98 | 12.84 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 52 | 41.18 | 16.47 | 2.50x |
| DeepSeek-V4-Flash-0731 | 32 | 52 | 48.30 | 19.94 | 2.42x |
| DeepSeek-V4-Flash-0731 | 64 | 52 | 50.93 | 22.62 | 2.25x |
| DeepSeek-V4-Flash-0731 | 256 | 52 | 51.64 | 24.35 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1024 | 52 | 51.64 | 24.37 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 10.77 | 6.96 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 19.11 | 9.76 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 30.77 | 13.20 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 42.95 | 17.03 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 51.18 | 20.71 | 2.47x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 54.47 | 23.58 | 2.31x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 55.44 | 25.44 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1024 | 56 | 55.44 | 25.46 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 61 | 10.86 | 7.12 | 1.53x |
| DeepSeek-V4-Flash-0731 | 4 | 61 | 19.41 | 10.00 | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | 61 | 31.64 | 13.62 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 61 | 44.97 | 17.68 | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | 61 | 54.57 | 21.63 | 2.52x |
| DeepSeek-V4-Flash-0731 | 64 | 61 | 58.76 | 24.72 | 2.38x |
| DeepSeek-V4-Flash-0731 | 256 | 61 | 60.10 | 26.74 | 2.25x |
| DeepSeek-V4-Flash-0731 | 1024 | 61 | 60.11 | 26.76 | 2.25x |
| DeepSeek-V4-Flash-0731 | 1 | 62 | 5.76 | 4.96 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 62 | 10.87 | 7.15 | 1.52x |
| DeepSeek-V4-Flash-0731 | 4 | 62 | 19.46 | 10.04 | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | 62 | 31.80 | 13.70 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 62 | 45.35 | 17.81 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 62 | 55.22 | 21.81 | 2.53x |
| DeepSeek-V4-Flash-0731 | 64 | 62 | 59.60 | 24.94 | 2.39x |
| DeepSeek-V4-Flash-0731 | 256 | 62 | 61.03 | 26.99 | 2.26x |
| DeepSeek-V4-Flash-0731 | 1024 | 62 | 61.03 | 27.01 | 2.26x |
| DeepSeek-V4-Flash-0731 | 1 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 69 | 10.97 | 7.34 | 1.49x |
| DeepSeek-V4-Flash-0731 | 4 | 69 | 19.80 | 10.33 | 1.92x |
| DeepSeek-V4-Flash-0731 | 8 | 69 | 32.83 | 14.23 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 69 | 47.80 | 18.64 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 69 | 59.55 | 22.98 | 2.59x |
| DeepSeek-V4-Flash-0731 | 64 | 69 | 65.27 | 26.42 | 2.47x |
| DeepSeek-V4-Flash-0731 | 256 | 69 | 67.34 | 28.68 | 2.35x |
| DeepSeek-V4-Flash-0731 | 1024 | 69 | 67.36 | 28.71 | 2.35x |
| DeepSeek-V4-Flash-0731 | 1 | 74 | 5.80 | 5.09 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 74 | 11.03 | 7.47 | 1.48x |
| DeepSeek-V4-Flash-0731 | 4 | 74 | 20.01 | 10.52 | 1.90x |
| DeepSeek-V4-Flash-0731 | 8 | 74 | 33.47 | 14.59 | 2.29x |
| DeepSeek-V4-Flash-0731 | 16 | 74 | 49.36 | 19.20 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 74 | 62.39 | 23.77 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 74 | 69.12 | 27.41 | 2.52x |
| DeepSeek-V4-Flash-0731 | 256 | 74 | 71.71 | 29.82 | 2.40x |
| DeepSeek-V4-Flash-0731 | 1024 | 74 | 71.73 | 29.85 | 2.40x |
| DeepSeek-V4-Flash-0731 | 1 | 78 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 78 | 11.07 | 7.57 | 1.46x |
| DeepSeek-V4-Flash-0731 | 4 | 78 | 20.16 | 10.66 | 1.89x |
| DeepSeek-V4-Flash-0731 | 8 | 78 | 33.93 | 14.86 | 2.28x |
| DeepSeek-V4-Flash-0731 | 16 | 78 | 50.52 | 19.62 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 78 | 64.54 | 24.37 | 2.65x |
| DeepSeek-V4-Flash-0731 | 64 | 78 | 72.09 | 28.17 | 2.56x |
| DeepSeek-V4-Flash-0731 | 256 | 78 | 75.11 | 30.70 | 2.45x |
| DeepSeek-V4-Flash-0731 | 1024 | 78 | 75.13 | 30.72 | 2.45x |
| DeepSeek-V4-Flash-0731 | 1 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 79 | 11.08 | 7.60 | 1.46x |
| DeepSeek-V4-Flash-0731 | 4 | 79 | 20.19 | 10.69 | 1.89x |
| DeepSeek-V4-Flash-0731 | 8 | 79 | 34.04 | 14.93 | 2.28x |
| DeepSeek-V4-Flash-0731 | 16 | 79 | 50.79 | 19.73 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 79 | 65.06 | 24.51 | 2.65x |
| DeepSeek-V4-Flash-0731 | 64 | 79 | 72.81 | 28.36 | 2.57x |
| DeepSeek-V4-Flash-0731 | 256 | 79 | 75.95 | 30.91 | 2.46x |
| DeepSeek-V4-Flash-0731 | 1024 | 79 | 75.97 | 30.93 | 2.46x |
| DeepSeek-V4-Flash-0731 | 1 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 81 | 11.10 | 7.65 | 1.45x |
| DeepSeek-V4-Flash-0731 | 4 | 81 | 20.26 | 10.76 | 1.88x |
| DeepSeek-V4-Flash-0731 | 8 | 81 | 34.25 | 15.06 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 81 | 51.33 | 19.93 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 81 | 66.07 | 24.80 | 2.66x |
| DeepSeek-V4-Flash-0731 | 64 | 81 | 74.24 | 28.72 | 2.58x |
| DeepSeek-V4-Flash-0731 | 256 | 81 | 77.61 | 31.33 | 2.48x |
| DeepSeek-V4-Flash-0731 | 1024 | 81 | 77.63 | 31.36 | 2.48x |
| DeepSeek-V4-Flash-0731 | 1 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 84 | 11.12 | 7.71 | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | 84 | 20.35 | 10.86 | 1.88x |
| DeepSeek-V4-Flash-0731 | 8 | 84 | 34.55 | 15.25 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 84 | 52.10 | 20.23 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 84 | 67.55 | 25.22 | 2.68x |
| DeepSeek-V4-Flash-0731 | 64 | 84 | 76.33 | 29.26 | 2.61x |
| DeepSeek-V4-Flash-0731 | 256 | 84 | 80.06 | 31.95 | 2.51x |
| DeepSeek-V4-Flash-0731 | 1024 | 84 | 80.08 | 31.98 | 2.50x |
| DeepSeek-V4-Flash-0731 | 4096 | 84 | 80.08 | 31.98 | 2.50x |
| DeepSeek-V4-Flash-0731 | 1 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 85 | 11.13 | 7.74 | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | 85 | 20.38 | 10.89 | 1.87x |
| DeepSeek-V4-Flash-0731 | 8 | 85 | 34.65 | 15.31 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 85 | 52.35 | 20.32 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 85 | 68.03 | 25.36 | 2.68x |
| DeepSeek-V4-Flash-0731 | 64 | 85 | 77.02 | 29.43 | 2.62x |
| DeepSeek-V4-Flash-0731 | 256 | 85 | 80.86 | 32.15 | 2.51x |
| DeepSeek-V4-Flash-0731 | 1024 | 85 | 80.89 | 32.18 | 2.51x |
| DeepSeek-V4-Flash-0731 | 4096 | 85 | 80.89 | 32.18 | 2.51x |
| DeepSeek-V4-Flash-0731 | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Flash-0731 | 2 | 98 | 11.22 | 8.01 | 1.40x |
| DeepSeek-V4-Flash-0731 | 4 | 98 | 20.73 | 11.26 | 1.84x |
| DeepSeek-V4-Flash-0731 | 8 | 98 | 35.75 | 16.07 | 2.22x |
| DeepSeek-V4-Flash-0731 | 16 | 98 | 55.23 | 21.49 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 98 | 73.75 | 27.05 | 2.73x |
| DeepSeek-V4-Flash-0731 | 64 | 98 | 85.39 | 31.59 | 2.70x |
| DeepSeek-V4-Flash-0731 | 256 | 98 | 90.86 | 34.65 | 2.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 98 | 90.91 | 34.68 | 2.62x |
| DeepSeek-V4-Flash-0731 | 4096 | 98 | 90.91 | 34.68 | 2.62x |
| DeepSeek-V4-Flash-0731 | 1 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 104 | 11.26 | 8.12 | 1.39x |
| DeepSeek-V4-Flash-0731 | 4 | 104 | 20.86 | 11.42 | 1.83x |
| DeepSeek-V4-Flash-0731 | 8 | 104 | 36.17 | 16.39 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 104 | 56.38 | 21.98 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 104 | 76.09 | 27.76 | 2.74x |
| DeepSeek-V4-Flash-0731 | 64 | 104 | 88.92 | 32.51 | 2.74x |
| DeepSeek-V4-Flash-0731 | 256 | 104 | 95.18 | 35.72 | 2.66x |
| DeepSeek-V4-Flash-0731 | 1024 | 104 | 95.23 | 35.75 | 2.66x |
| DeepSeek-V4-Flash-0731 | 4096 | 104 | 95.23 | 35.75 | 2.66x |
| DeepSeek-V4-Flash-0731 | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 111 | 11.30 | 8.25 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 111 | 21.00 | 11.59 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 111 | 36.62 | 16.74 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 111 | 57.59 | 22.52 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 111 | 78.62 | 28.55 | 2.75x |
| DeepSeek-V4-Flash-0731 | 64 | 111 | 92.82 | 33.53 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 111 | 100.00 | 36.92 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1024 | 111 | 100.06 | 36.95 | 2.71x |
| DeepSeek-V4-Flash-0731 | 4096 | 111 | 100.06 | 36.95 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 112 | 11.30 | 8.26 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 112 | 21.01 | 11.62 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 112 | 36.68 | 16.79 | 2.18x |
| DeepSeek-V4-Flash-0731 | 16 | 112 | 57.76 | 22.59 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 112 | 78.97 | 28.66 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 112 | 93.35 | 33.67 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 112 | 100.67 | 37.08 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1024 | 112 | 100.73 | 37.11 | 2.71x |
| DeepSeek-V4-Flash-0731 | 4096 | 112 | 100.73 | 37.11 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1 | 117 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 117 | 11.32 | 8.34 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 117 | 21.10 | 11.73 | 1.80x |
| DeepSeek-V4-Flash-0731 | 8 | 117 | 36.97 | 17.02 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 117 | 58.54 | 22.95 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 117 | 80.64 | 29.19 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 117 | 95.96 | 34.37 | 2.79x |
| DeepSeek-V4-Flash-0731 | 256 | 117 | 103.94 | 37.89 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1024 | 117 | 104.00 | 37.93 | 2.74x |
| DeepSeek-V4-Flash-0731 | 4096 | 117 | 104.00 | 37.93 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 138 | 11.40 | 8.65 | 1.32x |
| DeepSeek-V4-Flash-0731 | 4 | 138 | 21.40 | 12.19 | 1.76x |
| DeepSeek-V4-Flash-0731 | 8 | 138 | 37.97 | 17.89 | 2.12x |
| DeepSeek-V4-Flash-0731 | 16 | 138 | 61.34 | 24.29 | 2.53x |
| DeepSeek-V4-Flash-0731 | 32 | 138 | 86.73 | 31.22 | 2.78x |
| DeepSeek-V4-Flash-0731 | 64 | 138 | 105.75 | 37.05 | 2.85x |
| DeepSeek-V4-Flash-0731 | 256 | 138 | 116.46 | 41.05 | 2.84x |
| DeepSeek-V4-Flash-0731 | 1024 | 138 | 116.56 | 41.09 | 2.84x |
| DeepSeek-V4-Flash-0731 | 4096 | 138 | 116.56 | 41.09 | 2.84x |
| DeepSeek-V4-Flash-0731 | 1 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 156 | 11.46 | 8.88 | 1.29x |
| DeepSeek-V4-Flash-0731 | 4 | 156 | 21.60 | 12.54 | 1.72x |
| DeepSeek-V4-Flash-0731 | 8 | 156 | 38.63 | 18.50 | 2.09x |
| DeepSeek-V4-Flash-0731 | 16 | 156 | 63.24 | 25.29 | 2.50x |
| DeepSeek-V4-Flash-0731 | 32 | 156 | 91.01 | 32.78 | 2.78x |
| DeepSeek-V4-Flash-0731 | 64 | 156 | 112.86 | 39.11 | 2.89x |
| DeepSeek-V4-Flash-0731 | 256 | 156 | 125.81 | 43.47 | 2.89x |
| DeepSeek-V4-Flash-0731 | 1024 | 156 | 125.93 | 43.51 | 2.89x |
| DeepSeek-V4-Flash-0731 | 4096 | 156 | 125.93 | 43.51 | 2.89x |
| DeepSeek-V4-Flash-0731 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 168 | 11.48 | 9.01 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 168 | 21.70 | 12.77 | 1.70x |
| DeepSeek-V4-Flash-0731 | 8 | 168 | 39.00 | 18.86 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 168 | 64.32 | 25.90 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 168 | 93.48 | 33.74 | 2.77x |
| DeepSeek-V4-Flash-0731 | 64 | 168 | 117.06 | 40.37 | 2.90x |
| DeepSeek-V4-Flash-0731 | 256 | 168 | 131.43 | 44.95 | 2.92x |
| DeepSeek-V4-Flash-0731 | 1024 | 168 | 131.56 | 45.00 | 2.92x |
| DeepSeek-V4-Flash-0731 | 4096 | 168 | 131.56 | 45.00 | 2.92x |
| DeepSeek-V4-Flash-0731 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 224 | 11.58 | 9.50 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 224 | 22.06 | 13.68 | 1.61x |
| DeepSeek-V4-Flash-0731 | 8 | 224 | 40.23 | 20.13 | 2.00x |
| DeepSeek-V4-Flash-0731 | 16 | 224 | 67.98 | 28.43 | 2.39x |
| DeepSeek-V4-Flash-0731 | 32 | 224 | 102.19 | 37.57 | 2.72x |
| DeepSeek-V4-Flash-0731 | 64 | 224 | 132.41 | 45.34 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 224 | 152.56 | 50.95 | 2.99x |
| DeepSeek-V4-Flash-0731 | 1024 | 224 | 152.75 | 51.00 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 224 | 152.75 | 51.00 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 234 | 11.59 | 9.57 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 234 | 22.10 | 13.82 | 1.60x |
| DeepSeek-V4-Flash-0731 | 8 | 234 | 40.39 | 20.31 | 1.99x |
| DeepSeek-V4-Flash-0731 | 16 | 234 | 68.48 | 28.83 | 2.37x |
| DeepSeek-V4-Flash-0731 | 32 | 234 | 103.39 | 38.15 | 2.71x |
| DeepSeek-V4-Flash-0731 | 64 | 234 | 134.59 | 46.10 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 234 | 155.63 | 51.89 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 234 | 155.82 | 51.94 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 234 | 155.82 | 51.94 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 312 | 5.95 | 5.75 | 1.04x |
| DeepSeek-V4-Flash-0731 | 2 | 312 | 11.66 | 10.01 | 1.16x |
| DeepSeek-V4-Flash-0731 | 4 | 312 | 22.36 | 14.82 | 1.51x |
| DeepSeek-V4-Flash-0731 | 8 | 312 | 41.31 | 21.45 | 1.93x |
| DeepSeek-V4-Flash-0731 | 16 | 312 | 71.31 | 31.56 | 2.26x |
| DeepSeek-V4-Flash-0731 | 32 | 312 | 110.47 | 41.78 | 2.64x |
| DeepSeek-V4-Flash-0731 | 64 | 312 | 147.76 | 51.38 | 2.88x |
| DeepSeek-V4-Flash-0731 | 256 | 312 | 174.58 | 58.08 | 3.01x |
| DeepSeek-V4-Flash-0731 | 1024 | 312 | 174.84 | 58.15 | 3.01x |
| DeepSeek-V4-Flash-0731 | 4096 | 312 | 174.84 | 58.15 | 3.01x |
| DeepSeek-V4-Flash-0731 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 335 | 11.67 | 10.10 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 335 | 22.42 | 15.08 | 1.49x |
| DeepSeek-V4-Flash-0731 | 8 | 335 | 41.50 | 21.74 | 1.91x |
| DeepSeek-V4-Flash-0731 | 16 | 335 | 71.92 | 32.23 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 335 | 112.01 | 42.67 | 2.63x |
| DeepSeek-V4-Flash-0731 | 64 | 335 | 150.70 | 52.74 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 335 | 178.89 | 59.63 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 335 | 179.16 | 59.70 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 335 | 179.16 | 59.70 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 336 | 11.67 | 10.11 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 336 | 22.42 | 15.09 | 1.49x |
| DeepSeek-V4-Flash-0731 | 8 | 336 | 41.51 | 21.75 | 1.91x |
| DeepSeek-V4-Flash-0731 | 16 | 336 | 71.94 | 32.26 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 336 | 112.08 | 42.70 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 336 | 150.82 | 52.80 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 336 | 179.07 | 59.69 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 336 | 179.34 | 59.76 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 336 | 179.34 | 59.76 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 448 | 11.72 | 10.47 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 448 | 22.61 | 16.14 | 1.40x |
| DeepSeek-V4-Flash-0731 | 8 | 448 | 42.17 | 22.95 | 1.84x |
| DeepSeek-V4-Flash-0731 | 16 | 448 | 74.04 | 34.77 | 2.13x |
| DeepSeek-V4-Flash-0731 | 32 | 448 | 117.52 | 46.50 | 2.53x |
| DeepSeek-V4-Flash-0731 | 64 | 448 | 161.39 | 58.19 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 448 | 194.83 | 66.34 | 2.94x |
| DeepSeek-V4-Flash-0731 | 1024 | 448 | 195.17 | 66.42 | 2.94x |
| DeepSeek-V4-Flash-0731 | 4096 | 448 | 195.17 | 66.42 | 2.94x |
| DeepSeek-V4-Flash-0731 | 1 | 560 | 5.97 | 5.86 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 560 | 11.75 | 10.70 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 560 | 22.72 | 16.96 | 1.34x |
| DeepSeek-V4-Flash-0731 | 8 | 560 | 42.58 | 23.99 | 1.77x |
| DeepSeek-V4-Flash-0731 | 16 | 560 | 75.34 | 36.42 | 2.07x |
| DeepSeek-V4-Flash-0731 | 32 | 560 | 120.96 | 49.82 | 2.43x |
| DeepSeek-V4-Flash-0731 | 64 | 560 | 168.23 | 62.01 | 2.71x |
| DeepSeek-V4-Flash-0731 | 256 | 560 | 205.24 | 71.72 | 2.86x |
| DeepSeek-V4-Flash-0731 | 1024 | 560 | 205.61 | 71.82 | 2.86x |
| DeepSeek-V4-Flash-0731 | 4096 | 560 | 205.61 | 71.82 | 2.86x |
| DeepSeek-V4-Flash-0731 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 672 | 11.76 | 10.87 | 1.08x |
| DeepSeek-V4-Flash-0731 | 4 | 672 | 22.79 | 17.60 | 1.29x |
| DeepSeek-V4-Flash-0731 | 8 | 672 | 42.85 | 24.95 | 1.72x |
| DeepSeek-V4-Flash-0731 | 16 | 672 | 76.22 | 37.57 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 672 | 123.33 | 52.69 | 2.34x |
| DeepSeek-V4-Flash-0731 | 64 | 672 | 173.01 | 65.13 | 2.66x |
| DeepSeek-V4-Flash-0731 | 256 | 672 | 212.61 | 75.82 | 2.80x |
| DeepSeek-V4-Flash-0731 | 1024 | 672 | 213.01 | 75.93 | 2.81x |
| DeepSeek-V4-Flash-0731 | 4096 | 672 | 213.01 | 75.93 | 2.81x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4-Pro-0813 | 1 | 100 | 5.85 | 5.28 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 100 | 11.28 | 8.06 | 1.40x |
| DeepSeek-V4-Pro-0813 | 4 | 100 | 20.99 | 11.39 | 1.84x |
| DeepSeek-V4-Pro-0813 | 8 | 100 | 36.67 | 16.39 | 2.24x |
| DeepSeek-V4-Pro-0813 | 16 | 100 | 57.67 | 22.23 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 100 | 78.30 | 28.57 | 2.74x |
| DeepSeek-V4-Pro-0813 | 64 | 100 | 91.38 | 34.42 | 2.66x |
| DeepSeek-V4-Pro-0813 | 256 | 100 | 97.74 | 40.17 | 2.43x |
| DeepSeek-V4-Pro-0813 | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 110 | 11.33 | 8.24 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 110 | 21.20 | 11.65 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 110 | 37.37 | 16.92 | 2.21x |
| DeepSeek-V4-Pro-0813 | 16 | 110 | 59.63 | 23.06 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 110 | 82.55 | 29.82 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 110 | 98.14 | 36.10 | 2.72x |
| DeepSeek-V4-Pro-0813 | 256 | 110 | 106.49 | 42.35 | 2.51x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4-Pro-0813 | 1 | 187 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 187 | 11.57 | 9.22 | 1.25x |
| DeepSeek-V4-Pro-0813 | 4 | 187 | 22.09 | 13.18 | 1.68x |
| DeepSeek-V4-Pro-0813 | 8 | 187 | 40.45 | 19.68 | 2.05x |
| DeepSeek-V4-Pro-0813 | 16 | 187 | 68.79 | 27.61 | 2.49x |
| DeepSeek-V4-Pro-0813 | 32 | 187 | 104.23 | 37.05 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 187 | 136.42 | 46.18 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 187 | 162.25 | 55.64 | 2.92x |
| DeepSeek-V4-Pro-0813 | 1024 | 187 | 163.14 | 56.05 | 2.91x |
| DeepSeek-V4-Pro-0813 | 1 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 202 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 202 | 22.19 | 13.42 | 1.65x |
| DeepSeek-V4-Pro-0813 | 8 | 202 | 40.79 | 20.04 | 2.04x |
| DeepSeek-V4-Pro-0813 | 16 | 202 | 69.87 | 28.30 | 2.47x |
| DeepSeek-V4-Pro-0813 | 32 | 202 | 107.00 | 38.17 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 202 | 141.77 | 47.74 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 202 | 170.93 | 57.73 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1024 | 202 | 171.96 | 58.16 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 203 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 203 | 22.19 | 13.44 | 1.65x |
| DeepSeek-V4-Pro-0813 | 8 | 203 | 40.82 | 20.06 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 203 | 69.94 | 28.35 | 2.47x |
| DeepSeek-V4-Pro-0813 | 32 | 203 | 107.17 | 38.24 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 203 | 142.11 | 47.84 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 203 | 171.48 | 57.86 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1024 | 203 | 172.53 | 58.30 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1 | 208 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 208 | 11.60 | 9.40 | 1.23x |
| DeepSeek-V4-Pro-0813 | 4 | 208 | 22.22 | 13.52 | 1.64x |
| DeepSeek-V4-Pro-0813 | 8 | 208 | 40.92 | 20.17 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 208 | 70.26 | 28.57 | 2.46x |
| DeepSeek-V4-Pro-0813 | 32 | 208 | 108.02 | 38.60 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 208 | 143.78 | 48.34 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 208 | 174.22 | 58.53 | 2.98x |
| DeepSeek-V4-Pro-0813 | 1024 | 208 | 175.31 | 58.97 | 2.97x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 234 | 11.63 | 9.60 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 234 | 22.35 | 13.91 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 234 | 41.39 | 20.68 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 234 | 71.77 | 29.67 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 234 | 111.96 | 40.35 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 234 | 151.65 | 50.78 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 234 | 187.48 | 61.82 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1024 | 234 | 188.81 | 62.30 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1 | 268 | 5.94 | 5.70 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 268 | 11.67 | 9.81 | 1.19x |
| DeepSeek-V4-Pro-0813 | 4 | 268 | 22.49 | 14.37 | 1.56x |
| DeepSeek-V4-Pro-0813 | 8 | 268 | 41.88 | 21.24 | 1.97x |
| DeepSeek-V4-Pro-0813 | 16 | 268 | 73.34 | 31.00 | 2.37x |
| DeepSeek-V4-Pro-0813 | 32 | 268 | 116.18 | 42.35 | 2.74x |
| DeepSeek-V4-Pro-0813 | 64 | 268 | 160.29 | 53.58 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 268 | 202.57 | 65.69 | 3.08x |
| DeepSeek-V4-Pro-0813 | 1024 | 268 | 204.22 | 66.22 | 3.08x |
| DeepSeek-V4-Pro-0813 | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 280 | 11.68 | 9.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 280 | 22.53 | 14.53 | 1.55x |
| DeepSeek-V4-Pro-0813 | 8 | 280 | 42.03 | 21.42 | 1.96x |
| DeepSeek-V4-Pro-0813 | 16 | 280 | 73.81 | 31.44 | 2.35x |
| DeepSeek-V4-Pro-0813 | 32 | 280 | 117.46 | 42.98 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 280 | 162.98 | 54.48 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 280 | 207.38 | 66.94 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1024 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 311 | 11.70 | 10.03 | 1.17x |
| DeepSeek-V4-Pro-0813 | 4 | 311 | 22.62 | 14.90 | 1.52x |
| DeepSeek-V4-Pro-0813 | 8 | 311 | 42.35 | 21.84 | 1.94x |
| DeepSeek-V4-Pro-0813 | 16 | 311 | 74.88 | 32.49 | 2.30x |
| DeepSeek-V4-Pro-0813 | 32 | 311 | 120.39 | 44.46 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 311 | 169.19 | 56.66 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 311 | 218.70 | 70.00 | 3.12x |
| DeepSeek-V4-Pro-0813 | 1024 | 311 | 220.71 | 70.59 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1 | 325 | 5.95 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 325 | 11.71 | 10.09 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 325 | 22.65 | 15.06 | 1.50x |
| DeepSeek-V4-Pro-0813 | 8 | 325 | 42.48 | 22.01 | 1.93x |
| DeepSeek-V4-Pro-0813 | 16 | 325 | 75.30 | 32.94 | 2.29x |
| DeepSeek-V4-Pro-0813 | 32 | 325 | 121.56 | 45.07 | 2.70x |
| DeepSeek-V4-Pro-0813 | 64 | 325 | 171.70 | 57.59 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 325 | 223.36 | 71.31 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1024 | 325 | 225.47 | 71.91 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 334 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 334 | 11.71 | 10.13 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 334 | 22.67 | 15.16 | 1.50x |
| DeepSeek-V4-Pro-0813 | 8 | 334 | 42.56 | 22.12 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 334 | 75.56 | 33.21 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 334 | 122.26 | 45.44 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 334 | 173.23 | 58.17 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 334 | 226.21 | 72.13 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 334 | 228.39 | 72.73 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 335 | 11.71 | 10.13 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 335 | 22.67 | 15.17 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 335 | 42.57 | 22.14 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 335 | 75.58 | 33.24 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 335 | 122.34 | 45.48 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 335 | 173.40 | 58.23 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 335 | 226.52 | 72.22 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 336 | 11.71 | 10.14 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 336 | 22.68 | 15.18 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 336 | 42.57 | 22.15 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 336 | 75.61 | 33.27 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 336 | 122.42 | 45.52 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 336 | 173.56 | 58.30 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 336 | 226.83 | 72.31 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 373 | 11.73 | 10.27 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 373 | 22.75 | 15.57 | 1.46x |
| DeepSeek-V4-Pro-0813 | 8 | 373 | 42.85 | 22.57 | 1.90x |
| DeepSeek-V4-Pro-0813 | 16 | 373 | 76.52 | 34.31 | 2.23x |
| DeepSeek-V4-Pro-0813 | 32 | 373 | 124.98 | 46.94 | 2.66x |
| DeepSeek-V4-Pro-0813 | 64 | 373 | 179.17 | 60.59 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 373 | 237.50 | 75.51 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 373 | 239.95 | 76.15 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 383 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 383 | 11.74 | 10.31 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 383 | 22.77 | 15.66 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 383 | 42.91 | 22.68 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 383 | 76.74 | 34.56 | 2.22x |
| DeepSeek-V4-Pro-0813 | 32 | 383 | 125.60 | 47.30 | 2.66x |
| DeepSeek-V4-Pro-0813 | 64 | 383 | 180.54 | 61.19 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 383 | 240.13 | 76.33 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 383 | 242.65 | 76.99 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 384 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 384 | 11.74 | 10.31 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 384 | 22.77 | 15.67 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 384 | 42.92 | 22.69 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 384 | 76.76 | 34.59 | 2.22x |
| DeepSeek-V4-Pro-0813 | 32 | 384 | 125.66 | 47.33 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 384 | 180.68 | 61.24 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 384 | 240.39 | 76.42 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 384 | 242.92 | 77.07 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 392 | 11.74 | 10.34 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 392 | 22.78 | 15.75 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 392 | 42.97 | 22.77 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 392 | 76.93 | 34.79 | 2.21x |
| DeepSeek-V4-Pro-0813 | 32 | 392 | 126.14 | 47.61 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 392 | 181.73 | 61.71 | 2.94x |
| DeepSeek-V4-Pro-0813 | 256 | 392 | 242.42 | 77.06 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 392 | 245.00 | 77.72 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 448 | 11.76 | 10.50 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 448 | 22.87 | 16.25 | 1.41x |
| DeepSeek-V4-Pro-0813 | 8 | 448 | 43.27 | 23.34 | 1.85x |
| DeepSeek-V4-Pro-0813 | 16 | 448 | 77.94 | 36.03 | 2.16x |
| DeepSeek-V4-Pro-0813 | 32 | 448 | 129.03 | 49.47 | 2.61x |
| DeepSeek-V4-Pro-0813 | 64 | 448 | 188.21 | 64.80 | 2.90x |
| DeepSeek-V4-Pro-0813 | 256 | 448 | 255.15 | 81.21 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 504 | 5.97 | 5.84 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 504 | 11.78 | 10.63 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 504 | 22.93 | 16.68 | 1.37x |
| DeepSeek-V4-Pro-0813 | 8 | 504 | 43.51 | 23.88 | 1.82x |
| DeepSeek-V4-Pro-0813 | 16 | 504 | 78.74 | 37.04 | 2.13x |
| DeepSeek-V4-Pro-0813 | 32 | 504 | 131.34 | 51.20 | 2.57x |
| DeepSeek-V4-Pro-0813 | 64 | 504 | 193.47 | 67.52 | 2.87x |
| DeepSeek-V4-Pro-0813 | 256 | 504 | 265.72 | 84.79 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1024 | 504 | 268.92 | 85.61 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 574 | 5.97 | 5.86 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 574 | 11.79 | 10.76 | 1.10x |
| DeepSeek-V4-Pro-0813 | 4 | 574 | 22.99 | 17.16 | 1.34x |
| DeepSeek-V4-Pro-0813 | 8 | 574 | 43.74 | 24.51 | 1.78x |
| DeepSeek-V4-Pro-0813 | 16 | 574 | 79.53 | 38.07 | 2.09x |
| DeepSeek-V4-Pro-0813 | 32 | 574 | 133.65 | 53.24 | 2.51x |
| DeepSeek-V4-Pro-0813 | 64 | 574 | 198.81 | 70.42 | 2.82x |
| DeepSeek-V4-Pro-0813 | 256 | 574 | 276.64 | 88.75 | 3.12x |
| DeepSeek-V4-Pro-0813 | 1024 | 574 | 280.15 | 89.61 | 3.13x |
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
| DeepSeek-V4-Pro-0813 | 1 | 3694 | 6.00 | 5.99 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 3694 | 11.89 | 11.70 | 1.02x |
| DeepSeek-V4-Pro-0813 | 4 | 3694 | 23.37 | 21.94 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 3694 | 45.18 | 36.69 | 1.23x |
| DeepSeek-V4-Pro-0813 | 16 | 3694 | 84.56 | 52.60 | 1.61x |
| DeepSeek-V4-Pro-0813 | 32 | 3694 | 148.94 | 76.32 | 1.95x |
| DeepSeek-V4-Pro-0813 | 64 | 3694 | 236.00 | 113.11 | 2.09x |
| DeepSeek-V4-Pro-0813 | 256 | 3694 | 358.61 | 152.82 | 2.35x |
| DeepSeek-V4-Pro-0813 | 1024 | 3694 | 364.76 | 154.42 | 2.36x |
| DeepSeek-V4-Pro-0813 | 4096 | 3694 | 364.76 | 154.42 | 2.36x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 894.40 | 30.2% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 1,263.60 | 19.4% |
| gpu | Qwen3-8B | 1 | 566.80 | 32.8% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 199.03 | 86.2% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 378.40 | 79.6% |
| rom | Qwen3-8B | 1 | 67.42 | 78.5% |

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
| Qwen3-8B | 1 | 3 | 60.22% | 16.76 | 9.27 |
| Qwen3-8B | 2 | 4 | 33.78% | 12.53 | 9.27 |
| Qwen3-8B | 4 | 1 | 1.40% | 7.40 | 9.27 |
| Qwen3-8B | 8 | 1 | 1.40% | 7.40 | 9.27 |
| Qwen3-8B | 16 | 1 | 1.40% | 7.40 | 9.27 |
| Qwen3-8B | 32 | 1 | 1.40% | 7.40 | 9.27 |
| Qwen3-8B | 64 | 1 | 1.57% | 8.31 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 60.39% | 24.45 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 1 | 2.25% | 2.73 | 2.13 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 2.25% | 2.73 | 2.13 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 2.25% | 2.73 | 2.13 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 2.25% | 2.73 | 2.13 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 2.25% | 2.73 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 101 | 87.75% | 184.08 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 32.05% | 75.89 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.5 | 27,496.5 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.5 | 27,496.5 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.5 | 27,496.5 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.5 | 27,496.5 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.5 | 27,496.5 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.5 | 27,496.5 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.5 | 27,496.5 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 356.0 | 91,140.5 |
| Qwen3-8B | 1024 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 90.4 | 92,570.1 |
| Qwen3-8B | 4096 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 22.7 | 92,935.4 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,245.9 | 177,425.5 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,245.9 | 177,425.5 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,245.9 | 177,425.5 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,245.9 | 177,425.5 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,245.9 | 177,425.5 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,245.9 | 177,425.5 |
| DeepSeek-V4-Flash-0731 | 64 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,245.9 | 177,425.5 |
| DeepSeek-V4-Flash-0731 | 256 | 7.40% | 18.7 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 923.5 | 236,416.9 |
| DeepSeek-V4-Flash-0731 | 1024 | 26.47% | 46.7 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 259.0 | 265,185.1 |
| DeepSeek-V4-Flash-0731 | 4096 | 70.76% | 111.9 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 66.4 | 272,120.9 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,865.7 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,865.7 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,865.7 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,865.7 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,865.7 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,865.7 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,865.7 |
| DeepSeek-V4-Pro-0813 | 256 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,865.7 |
| DeepSeek-V4-Pro-0813 | 1024 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,865.7 |
| DeepSeek-V4-Pro-0813 | 4096 | 1.71% | 40.9 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 100.3 | 410,872.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 232 |
| gpu | kv_read | 100 |
| gpu | link_latency | 1696 |
| gpu | weight_read | 1122 |
| rom | compute | 475 |
| rom | infeasible | 6647 |
| rom | kv_read | 803 |
| rom | layer_fixed_latency | 817 |
| rom | link_latency | 1654 |
| rom | weight_read | 954 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 232 |
| rom | CAPACITY | 6647 |

## Mechanical consistency audit

**FAIL** over 253,227 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x7', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x7', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x7', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x7', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x2', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'Qwen3-8B', 1)

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

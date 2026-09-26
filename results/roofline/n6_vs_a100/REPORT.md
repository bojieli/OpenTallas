# Area-constrained roofline: n6_vs_a100

> Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 292x (ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream, 3,744 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 1 device. On the GPU side the correction reaches 37x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 103 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 6 x 815 mm2 (4,890 mm2, array, KV in SRAM) at 6,804 tok/s per user and 1,391 tok/s per 1,000 mm2, holding 1 session, against 6 copies of one unified HBM die at the same silicon: 14.9x per user. DeepSeek-V4-Flash-0731 takes 1 x 46,225 mm2 (46,225 mm2, wafer, KV in SRAM) at 3,177 tok/s per user and 69 tok/s per 1,000 mm2, holding 1 session, against 56 copies of one unified HBM die at the same silicon: 7.9x per user. DeepSeek-V4-Pro-0813 takes 4 x 46,225 mm2 (184,900 mm2, wafer, KV in SRAM) at 1,708 tok/s per user and 9 tok/s per 1,000 mm2, holding 1 session, against 224 copies of one unified HBM die at the same silicon: 10.1x per user. Two granularities come out of one rule, which is the point: the class is chosen per model on evidence rather than assumed. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 8,150 mm2 of ROM silicon at 7,255 tok/s per user against 8,260 mm2 of a100_sxm_80gb-x10-tensor at 445 tok/s: **16.3x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 582. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 3,050,850 mm2 on DeepSeek-V4-Pro-0813 at batch 1, the iso-area GPU cluster is 3,694 devices. Cut as one serial pipeline that is 462 stages and 3,836 us of link latency per token; but the model has 61 layers, so at most 61 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 2,792 us. The iso-area per-user ratio at that point falls from 10.5x to 9.0x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 7.60x to it.** At 224,940 mm2 on Qwen3-8B the pipeline-only GPU delivers 98.43 tok/s and the same silicon running tensor delivers 748 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 8.61x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 2,222 to 270,679 tok/s, and its rate with every slot occupied from 175,506 to 270,679. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 79 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,825 us over NVLink, capping per-user decode at 548 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 684.5 us and cap it at 1,461 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 2.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 16 of 30 operating points and an array 14; on tokens per second per square millimetre the same points go 19 to the array and 11 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 912 of 7668 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 46.5x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 15.13x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 50 of 60 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### Qwen3-8B at 8,192 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x6`** -- 6 x 815 mm2 reticle dies, 4,890 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **6,803.6 tok/s per user** (0.15 ms/token), binding on `layer_fixed_latency`
- **1,391.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 6,804 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 465 W at 0.095 W/mm2, 68.4 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 6 copies of one unified HBM die -- `a100_sxm_80gb-x6-tensor`, 4,956 mm2, area ratio 0.9867 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 4,890 | 4,956 | 0.9867 |
| user tok/s | 6,803.6 | 455.8 | 14.93x |
| aggregate tok/s | 6,804 | 456 | 11.44x |
| resident sessions | 1 | 344 | -- |
| J/token | 0.0684 | 3.6237 | 53.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 344 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x272-tensor` at 224,672 mm2 and 748.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 9,289.5 | 201.0 | 1 | 13.62x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 9,289.5 | 201.0 | 1 | 13.62x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x5` | 4,075 | 4,984.0 | 1,223.1 | 1 | 12.58x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 4,890 | 6,803.6 | 1,391.3 | 1 | 14.93x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 4,890 | 6,803.6 | 1,391.3 | -- | 1,391.3 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 7,587.6 | 1,330.0 | 962.0 | 1,391.3 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 7,881.8 | 1,208.9 | 661.5 | 1,391.3 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x16-romfill` | 13,040 | 7,885.6 | 604.7 | 132.8 | 1,391.3 | stop |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 9,289.5 | 201.0 | 60.1 | 1,391.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x6` **<-- recommended** | 4,890 | 6 | 6,803.6 | 6,804 | 1,391.3 | 1 | `layer_fixed_latency` | 465 | 68.4 | `a100_sxm_80gb-x6-tensor` | 14.93x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 7 | 7,587.6 | 7,588 | 1,330.0 | 1 | `layer_fixed_latency` | 587 | 77.4 | `a100_sxm_80gb-x7-tensor` | 14.86x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 8 | 7,881.8 | 7,882 | 1,208.9 | 1 | `layer_fixed_latency` | 664 | 84.3 | `a100_sxm_80gb-x8-tensor` | 14.05x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x16-romfill` | 13,040 | 16 | 7,885.6 | 7,886 | 604.7 | 1 | `layer_fixed_latency` | 1,250 | 158.5 | `a100_sxm_80gb-x16-hybrid` | 14.09x |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 1 | 9,289.5 | 9,290 | 201.0 | 1 | `layer_fixed_latency` | 4,247 | 457.1 | `a100_sxm_80gb-x56-tensor` | 13.62x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 262 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 4,890 | 6,803.6 | 1,391.3 | 1 |
| array | 262 | fastest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x16-romfill` | 13,040 | 7,885.6 | 604.7 | 1 |
| array | 262 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x5` | 4,075 | 4,984.0 | 1,223.1 | 1 |
| wafer | 52 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 9,289.5 | 201.0 | 1 |
| wafer | 52 | fastest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 9,289.5 | 201.0 | 1 |
| wafer | 52 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 9,289.5 | 201.0 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-hybrid-x16-romfill` | 13,040 | 7,885.6 | 7,886 | 1 | 1,250 | 158.5 | `layer_fixed_latency` | `a100_sxm_80gb-x16-hybrid` | 559.8 | 940 | 5,849.8 | 0.987 | 14.09x | 36.9x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 9,289.5 | 9,290 | 1 | 4,247 | 457.1 | `layer_fixed_latency` | `a100_sxm_80gb-x56-tensor` | 682.2 | 3,324 | 13,574.8 | 0.999 | 13.62x | 29.7x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 46,455 | 5,731.4 | 5,731 | 1 | 4,221 | 736.4 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 682.2 | 3,324 | 13,574.8 | 1.004 | 8.40x | 18.4x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 9,289.5 | -- | 1 | -- | 457.1 | -- | -- | -- | -- | -- | 1.005 | 1.62x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 168,705 | 5,514.8 | 71,692 | 12,338 | 28,535 | 1,835.5 | `link_latency` | `a100_sxm_80gb-x204-tensor` | 687.0 | 12,145 | 22,363.5 | 1.001 | 8.03x | 12.2x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,433.8 | 43,470 | 4,100 | 40,326 | 3,300.7 | `kv_read` | `a100_sxm_80gb-x448-hybrid` | 684.2 | 26,689 | 48,993.5 | 0.999 | 7.94x | 14.8x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 168,705 | 5,514.8 | 71,692 | 12,338 | 28,535 | 986.1 | `link_latency` | `a100_sxm_80gb-x204-hybrid` | 669.4 | 12,145 | 12,723.7 | 1.001 | 8.24x | 12.9x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,433.8 | 43,470 | 4,100 | 40,326 | 1,718.7 | `kv_read` | `a100_sxm_80gb-x448-hybrid` | 684.2 | 26,689 | 25,358.3 | 0.999 | 7.94x | 14.8x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill` | 168,705 | 5,514.8 | 71,692 | 12,338 | 28,535 | 561.4 | `link_latency` | `a100_sxm_80gb-x204-hybrid` | 622.8 | 12,145 | 6,838.9 | 1.001 | 8.85x | 12.2x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,433.8 | 43,470 | 4,100 | 40,326 | 927.7 | `kv_read` | `a100_sxm_80gb-x448-hybrid` | 676.9 | 26,689 | 13,468.5 | 0.999 | 8.03x | 14.5x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 5,429.1 | 97,723 | 16,450 | 38,339 | 424.3 | `link_latency` | `a100_sxm_80gb-x272-hybrid` | 583.5 | 16,198 | 5,233.9 | 1.001 | 9.31x | 12.3x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,497.8 | 71,965 | 6,151 | 61,329 | 852.2 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 654.0 | 40,040 | 10,498.5 | 0.999 | 6.88x | 12.3x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 5,053.4 | 217,298 | 20,265 | 60,474 | 327.0 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 542.6 | 19,953 | 3,464.7 | 1.001 | 9.31x | 10.6x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,069.3 | 98,217 | 6,151 | 64,857 | 660.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 591.2 | 40,040 | 5,807.4 | 0.999 | 5.19x | 8.8x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,991.7 | 255,468 | 20,265 | 65,298 | 255.6 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 518.7 | 19,953 | 2,633.1 | 1.001 | 7.70x | 10.3x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,851.7 | 118,507 | 6,151 | 67,592 | 570.4 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 535.7 | 40,040 | 4,552.8 | 0.999 | 3.46x | 8.0x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 1,578.5 | 404,098 | 20,265 | 85,367 | 211.3 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 411.4 | 19,953 | 852.3 | 1.001 | 3.84x | 4.0x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 531.6 | 136,094 | 6,151 | 69,966 | 514.1 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 478.2 | 40,040 | 1,446.7 | 0.999 | 1.11x | 2.8x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 430.3 | 440,653 | 20,265 | 89,619 | 203.4 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 225.0 | 19,953 | 407.1 | 1.001 | 1.91x | 2.0x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 136.7 | 139,933 | 6,151 | 70,483 | 503.7 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 323.1 | 40,040 | 555.8 | 0.999 | 0.42x | 1.1x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 110.7 | 453,465 | 20,265 | 104,594 | 230.7 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 80.4 | 19,953 | 311.6 | 1.001 | 1.38x | 1.4x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 34.4 | 140,792 | 6,151 | 100,286 | 712.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 140.6 | 40,040 | 333.0 | 0.999 | 0.24x | 0.5x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 4,890 | array | SRAM | 1 |
| 2-64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill` | 56,235 | array | HBM | 4,112 |
| 256-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x69` | 56,235 | array | HBM | 4,112 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Flash-0731 at 200,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-wafer-tensor-x1`** -- 1 x 46,225 mm2 wafer, 46,225 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **3,176.6 tok/s per user** (0.31 ms/token), binding on `layer_fixed_latency`
- **68.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,177 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 3,793 W at 0.082 W/mm2, 1,193.9 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 56 copies of one unified HBM die -- `a100_sxm_80gb-x56-hybrid`, 46,256 mm2, area ratio 0.9993 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 46,225 | 46,256 | 0.9993 |
| user tok/s | 3,176.6 | 401.1 | 7.92x |
| aggregate tok/s | 3,177 | 2,808 | 0.41x |
| resident sessions | 1 | 2,797 | -- |
| J/token | 1.1939 | 21.3715 | 17.9x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 2,797 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 401.1 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,938.3 | 42.6 | 1 | 9.91x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,938.3 | 42.6 | 1 | 9.91x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-hybrid-x37` | 30,155 | 1,581.6 | 52.4 | 1 | 4.03x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,176.6 | 68.7 | 1 | 7.92x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,176.6 | 68.7 | -- | 68.7 | ACCEPT |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,938.3 | 42.6 | 16.5 | 68.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1` **<-- recommended** | 46,225 | 1 | 3,176.6 | 3,177 | 68.7 | 1 | `layer_fixed_latency` | 3,793 | 1,193.9 | `a100_sxm_80gb-x56-hybrid` | 7.92x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2 | 3,938.3 | 3,938 | 42.6 | 1 | `layer_fixed_latency` | 10,500 | 2,666.1 | `a100_sxm_80gb-x112-hybrid` | 9.91x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 324 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 2,418.5 | 67.4 | 1 |
| array | 324 | fastest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 65,200 | 3,111.9 | 47.7 | 1 |
| array | 324 | smallest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x37` | 30,155 | 1,581.6 | 52.4 | 1 |
| wafer | 52 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,176.6 | 68.7 | 1 |
| wafer | 52 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,938.3 | 42.6 | 1 |
| wafer | 52 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,176.6 | 68.7 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-hybrid-x80` | 65,200 | 3,111.9 | 3,112 | 1 | 6,543 | 2,102.7 | `layer_fixed_latency` | `a100_sxm_80gb-x79-hybrid` | 398.0 | 3,996 | 29,871.9 | 0.999 | 7.82x | 14.2x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,938.3 | 3,938 | 1 | 10,500 | 2,666.1 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 397.4 | 5,715 | 41,906.0 | 0.999 | 9.91x | 15.7x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x113` | 92,095 | 2,875.6 | 2,876 | 1 | 10,442 | 3,631.1 | `layer_fixed_latency` | `a100_sxm_80gb-x111-hybrid` | 396.4 | 5,663 | 41,650.2 | 1.004 | 7.26x | 11.5x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,938.3 | -- | 1 | -- | 2,666.1 | -- | -- | -- | -- | -- | 0.996 | 1.37x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 3,019.3 | 129,831 | 4,481 | 13,542 | 1,445.6 | `layer_fixed_latency` | `a100_sxm_80gb-x85-hybrid` | 394.9 | 4,308 | 16,755.7 | 0.998 | 7.65x | 11.6x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 462,250 | 3,217.9 | 57,923 | 4,481 | 67,610 | 10,194.2 | `layer_fixed_latency` | `a100_sxm_80gb-x560-hybrid` | 382.7 | 29,061 | 106,859.6 | 0.999 | 8.41x | 10.5x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 3,019.3 | 129,831 | 4,481 | 13,542 | 742.3 | `layer_fixed_latency` | `a100_sxm_80gb-x85-hybrid` | 394.9 | 4,308 | 8,985.5 | 0.998 | 7.65x | 12.1x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 462,250 | 3,217.9 | 57,923 | 4,481 | 67,610 | 5,116.5 | `layer_fixed_latency` | `a100_sxm_80gb-x560-hybrid` | 382.7 | 29,061 | 54,037.4 | 0.999 | 8.41x | 10.6x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 3,019.3 | 129,831 | 4,481 | 13,542 | 390.6 | `layer_fixed_latency` | `a100_sxm_80gb-x85-hybrid` | 394.9 | 4,308 | 5,100.3 | 0.998 | 7.65x | 13.1x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 462,250 | 3,217.9 | 57,923 | 4,481 | 67,610 | 2,577.7 | `layer_fixed_latency` | `a100_sxm_80gb-x560-hybrid` | 382.7 | 29,061 | 27,626.3 | 0.999 | 8.41x | 10.7x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 3,019.3 | 129,831 | 4,481 | 13,542 | 214.7 | `layer_fixed_latency` | `a100_sxm_80gb-x85-hybrid` | 367.4 | 4,308 | 3,045.8 | 0.998 | 8.22x | 14.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 462,250 | 3,217.9 | 57,923 | 4,481 | 67,610 | 1,308.3 | `layer_fixed_latency` | `a100_sxm_80gb-x560-hybrid` | 382.7 | 29,061 | 14,420.7 | 0.999 | 8.41x | 11.0x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x86` | 70,090 | 3,019.3 | 129,831 | 4,481 | 13,542 | 126.8 | `layer_fixed_latency` | `a100_sxm_80gb-x85-hybrid` | 301.2 | 4,308 | 1,944.6 | 0.998 | 10.02x | 15.3x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10` | 462,250 | 3,094.0 | 111,384 | 4,481 | 69,688 | 699.0 | `layer_fixed_latency` | `a100_sxm_80gb-x560-hybrid` | 382.7 | 29,061 | 7,818.0 | 0.999 | 8.09x | 11.2x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 257,540 | 2,805.9 | 221,669 | 16,467 | 37,220 | 198.1 | `layer_fixed_latency` | `a100_sxm_80gb-x312-hybrid` | 346.7 | 16,138 | 2,923.8 | 0.999 | 8.09x | 14.8x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 2,761.8 | 176,755 | 5,377 | 85,734 | 485.0 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 382.7 | 34,898 | 5,176.9 | 0.999 | 7.22x | 10.7x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 2,237.6 | 572,823 | 17,717 | 52,575 | 91.8 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 215.7 | 17,336 | 1,534.1 | 1.001 | 10.38x | 16.7x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,462.6 | 374,423 | 5,377 | 92,950 | 248.2 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 283.6 | 34,898 | 1,994.3 | 0.999 | 5.16x | 8.0x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 877.4 | 898,499 | 17,717 | 64,233 | 71.5 | `compute` | `a100_sxm_80gb-x335-hybrid` | 99.1 | 17,336 | 898.3 | 1.001 | 8.85x | 12.6x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 480.3 | 491,815 | 5,377 | 97,319 | 197.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 153.9 | 34,898 | 1,127.3 | 0.999 | 3.12x | 5.7x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 257,540 | 296.6 | 1,215,047 | 16,467 | 82,994 | 68.3 | `weight_read` | `a100_sxm_80gb-x312-hybrid` | 36.4 | 16,138 | 642.2 | 0.999 | 8.14x | 9.4x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 128.2 | 525,130 | 5,377 | 98,330 | 187.2 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 61.8 | 34,898 | 805.1 | 0.999 | 2.08x | 4.3x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | wafer | SRAM | 1 |
| 2-64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x79` | 64,385 | array | HBM | 4,116 |
| 256 | `ROM-N6-native-HBMKV-array-hw-pipeline-x119` | 96,985 | array | HBM | 6,201 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x158` | 128,770 | array | HBM | 8,233 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Pro-0813 at 1,000,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-wafer-hybrid-x4`** -- 4 x 46,225 mm2 wafers, 184,900 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **1,707.7 tok/s per user** (0.59 ms/token), binding on `layer_fixed_latency`
- **9.2 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 1,708 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 11,081 W at 0.060 W/mm2, 6,489.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 224 copies of one unified HBM die -- `a100_sxm_80gb-x224-hybrid`, 185,024 mm2, area ratio 0.9993 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 184,900 | 185,024 | 0.9993 |
| user tok/s | 1,707.7 | 169.1 | 10.10x |
| aggregate tok/s | 1,708 | 4,735 | 0.19x |
| resident sessions | 1 | 1,545 | -- |
| J/token | 6.4892 | 195.6698 | 30.2x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,545 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 171.7 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,899.8 | 6.8 | 1 | 11.35x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 1,973.7 | 4.7 | 1 | 11.95x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x190` | 154,850 | 374.3 | 2.4 | 1 | 2.23x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,707.7 | 9.2 | 1 | 10.10x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,707.7 | 9.2 | -- | 9.2 | ACCEPT |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,899.8 | 6.8 | 2.1 | 9.2 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x7` | 323,575 | 1,935.9 | 6.0 | 1.6 | 9.2 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x8` | 369,800 | 1,958.8 | 5.3 | 1.4 | 9.2 | stop |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 1,973.7 | 4.7 | 1.2 | 9.2 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x4` **<-- recommended** | 184,900 | 4 | 1,707.7 | 1,708 | 9.2 | 1 | `layer_fixed_latency` | 11,081 | 6,489.2 | `a100_sxm_80gb-x224-hybrid` | 10.10x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 6 | 1,899.8 | 1,900 | 6.8 | 1 | `layer_fixed_latency` | 24,492 | 12,892.5 | `a100_sxm_80gb-x336-hybrid` | 11.35x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x7` | 323,575 | 7 | 1,935.9 | 1,936 | 6.0 | 1 | `layer_fixed_latency` | 31,196 | 16,114.8 | `a100_sxm_80gb-x392-hybrid` | 11.62x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x8` | 369,800 | 8 | 1,958.8 | 1,959 | 5.3 | 1 | `layer_fixed_latency` | 37,900 | 19,348.0 | `a100_sxm_80gb-x448-hybrid` | 11.82x |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 9 | 1,973.7 | 1,974 | 4.7 | 1 | `layer_fixed_latency` | 44,603 | 22,598.1 | `a100_sxm_80gb-x504-hybrid` | 11.95x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 126 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x237` | 193,155 | 869.7 | 4.5 | 1 |
| array | 126 | fastest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 317,035 | 1,066.2 | 3.4 | 1 |
| array | 126 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x190` | 154,850 | 374.3 | 2.4 | 1 |
| wafer | 39 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,707.7 | 9.2 | 1 |
| wafer | 39 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 1,973.7 | 4.7 | 1 |
| wafer | 39 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,707.7 | 9.2 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-hybrid-x389` | 317,035 | 1,066.2 | 1,066 | 1 | 30,222 | 28,344.9 | `link_latency` | `a100_sxm_80gb-x384-hybrid` | 166.7 | 2,714 | 337,074.4 | 1.000 | 6.40x | 11.9x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 1,973.7 | 1,974 | 1 | 44,603 | 22,598.1 | `layer_fixed_latency` | `a100_sxm_80gb-x504-hybrid` | 165.1 | 3,591 | 445,120.9 | 0.999 | 11.95x | 19.7x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,480.8 | 97,734 | 4,146 | 459,974 | 147,119.9 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 26,894 | 1,619,846.9 | 1.000 | 8.97x | 11.0x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,480.8 | 97,734 | 4,146 | 459,974 | 73,687.9 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 26,894 | 812,131.7 | 1.000 | 8.97x | 11.0x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,480.8 | 97,734 | 4,146 | 459,974 | 36,972.0 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 26,894 | 408,274.1 | 1.000 | 8.97x | 11.0x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,480.8 | 97,734 | 4,146 | 459,974 | 18,614.0 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 26,894 | 206,345.3 | 1.000 | 8.97x | 11.1x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,480.8 | 97,734 | 4,146 | 459,974 | 9,435.0 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 26,894 | 105,380.9 | 1.000 | 8.97x | 11.2x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,480.8 | 97,734 | 4,146 | 459,974 | 4,845.5 | `layer_fixed_latency` | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 26,894 | 54,898.7 | 1.000 | 8.97x | 11.3x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 986.7 | 252,591 | 4,146 | 499,433 | 1,977.2 | `kv_read` | `a100_sxm_80gb-x3694-hybrid` | 165.1 | 26,894 | 17,037.0 | 1.000 | 5.98x | 8.6x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 361.1 | 369,793 | 4,146 | 529,350 | 1,431.5 | `kv_read` | `a100_sxm_80gb-x3694-hybrid` | 118.2 | 26,894 | 7,262.4 | 1.000 | 3.05x | 5.1x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 3,050,850 | 100.3 | 410,882 | 4,146 | 539,839 | 1,313.9 | `kv_read` | `a100_sxm_80gb-x3694-hybrid` | 54.9 | 26,894 | 4,570.0 | 1.000 | 1.83x | 3.5x |

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
| DeepSeek-V4-Flash-0731 | HBM | sram | 79, 84, 85, 86, 99, 113, 119, 158, 170, 227, 237, 316, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 37, 39, 44, 46, 53, 57, 60, 63, 70, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 37, 39, 44, 46, 53, 57, 70, 78, 79, 80, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 190, 196, 227, 237, 272, 284, 319, 339, 340, 378 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 190, 196, 227, 237, 272, 284, 340, 357, 378, 388, 389 |
| Qwen3-8B | HBM | rom | 69, 74, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| Qwen3-8B | HBM | sram | 69, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| Qwen3-8B | SRAM | rom | 5, 6, 7, 8, 10, 12, 15, 16, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 5, 6, 7, 8, 12, 16, 57, 113, 170, 227, 340 |

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
| Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x6` | 1 | 6 | 2.03 | hierarchical | 61.09 | 35.55 | 50.34 | 42.42 | 6,803.6 |
| Qwen3-8B | `a100_sxm_80gb-x6-tensor` | 1 | 6 | 2.03 | measured_floor | 173.05 | 371.55 | 1,649.41 | 371.73 | 455.8 |
| Qwen3-8B | `a100_sxm_80gb-x6-tensor` | 64 | 6 | 2.03 | measured_floor | 173.05 | 784.43 | 9,329.96 | 681.39 | 97.2 |
| DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 1 | 57 on `rom_wafer_express` | 6.51 | one_shot, rec_doubling | 204.70 | 109.57 | 5.24 | 52.29 | 3,176.6 |
| DeepSeek-V4-Flash-0731 | `a100_sxm_80gb-x56-hybrid` | 1 | 8 | 5.51 | measured_floor | 403.02 | 1,344.80 | 873.03 | 462.70 | 401.1 |
| DeepSeek-V4-Flash-0731 | `a100_sxm_80gb-x56-hybrid` | 64 | 4 | 5.51 | measured_floor | 405.02 | 1,822.68 | 3,684.50 | 506.09 | 184.8 |
| DeepSeek-V4-Pro-0813 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 1 | 57 on `rom_wafer_express` | 6.51 | one_shot, rec_doubling | 364.28 | 157.47 | 74.44 | 75.02 | 1,707.7 |
| DeepSeek-V4-Pro-0813 | `a100_sxm_80gb-x224-hybrid` | 1 | 8 | 5.51 | measured_floor | 572.70 | 2,649.48 | 3,169.23 | 713.20 | 169.1 |
| DeepSeek-V4-Pro-0813 | `a100_sxm_80gb-x224-hybrid` | 64 | 8 | 5.51 | measured_floor | 572.70 | 3,842.16 | 4,611.65 | 752.79 | 119.7 |

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

- **0 of 7,668 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 339 | 0 | 60.4% | 80.5% | 0.390 | 60% |
| gpu | small array (1,600-5,000 mm2) | 60 | 0 | 78.8% | 80.7% | 0.391 | 46% |
| gpu | wafer (>=40,000 mm2) | 2,558 | 0 | 50.6% | 80.6% | 0.390 | 71% |
| rom | large array (5,000-40,000 mm2) | 150 | 0 | 13.4% | 25.1% | 0.126 | 99% |
| rom | small array (1,600-5,000 mm2) | 80 | 0 | 17.2% | 22.3% | 0.112 | 79% |
| rom | wafer (>=40,000 mm2) | 4,481 | 0 | 29.3% | 75.7% | 0.379 | 86% |

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
| DeepSeek-V4-Flash-0731 | 1 | 92,450 | `DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 2.666103 | 10,500.0 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x112-hybrid` | 41.905976 | 22,932.1 | link_latency | 15.72x |
| DeepSeek-V4-Flash-0731 | 2 | 462,250 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10` | 10.194172 | 67,609.8 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x560-hybrid` | 106.859555 | 113,406.9 | link_latency | 10.48x |
| DeepSeek-V4-Flash-0731 | 4 | 462,250 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10` | 5.116521 | 67,609.8 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x560-hybrid` | 54.037375 | 113,406.9 | link_latency | 10.56x |
| DeepSeek-V4-Flash-0731 | 8 | 462,250 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10` | 2.577696 | 67,609.8 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x560-hybrid` | 27.626285 | 113,406.9 | link_latency | 10.72x |
| DeepSeek-V4-Flash-0731 | 16 | 462,250 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10` | 1.308283 | 67,609.8 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x560-hybrid` | 14.420740 | 113,406.9 | link_latency | 11.02x |
| DeepSeek-V4-Flash-0731 | 32 | 64,385 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79` | 0.119317 | 12,141.9 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x78-hybrid` | 1.848156 | 17,293.3 | link_latency | 15.49x |
| DeepSeek-V4-Flash-0731 | 64 | 80,685 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x99` | 0.096248 | 16,975.4 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x98-hybrid` | 1.474860 | 22,521.3 | link_latency | 15.32x |
| DeepSeek-V4-Flash-0731 | 256 | 257,540 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 0.089988 | 49,454.4 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x312-hybrid` | 1.478349 | 79,235.1 | weight_read | 16.43x |
| DeepSeek-V4-Flash-0731 | 1024 | 277,100 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.071489 | 64,233.0 | compute | `DSV4-Flash/a100_sxm_80gb-x335-hybrid` | 0.898285 | 91,166.2 | weight_read | 12.57x |
| DeepSeek-V4-Flash-0731 | 4096 | 257,540 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316` | 0.068306 | 82,994.5 | weight_read | `DSV4-Flash/a100_sxm_80gb-x312-hybrid` | 0.642151 | 95,831.5 | weight_read | 9.40x |
| DeepSeek-V4-Pro-0813 | 1 | 277,350 | `DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 12.892474 | 24,492.5 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x336-hybrid` | 294.233444 | 79,563.1 | link_latency | 22.82x |
| DeepSeek-V4-Pro-0813 | 2 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 147.119912 | 459,973.7 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 1,619.846915 | 870,190.3 | link_latency | 11.01x |
| DeepSeek-V4-Pro-0813 | 4 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 73.687946 | 459,973.7 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 812.131705 | 870,190.3 | link_latency | 11.02x |
| DeepSeek-V4-Pro-0813 | 8 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 36.971963 | 459,973.7 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 408.274101 | 870,190.3 | link_latency | 11.04x |
| DeepSeek-V4-Pro-0813 | 16 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 18.613972 | 459,973.7 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 206.345298 | 870,190.3 | link_latency | 11.09x |
| DeepSeek-V4-Pro-0813 | 32 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 9.434976 | 459,973.7 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 105.380897 | 870,190.3 | link_latency | 11.17x |
| DeepSeek-V4-Pro-0813 | 64 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 4.845478 | 459,973.7 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 54.898696 | 870,190.3 | link_latency | 11.33x |
| DeepSeek-V4-Pro-0813 | 256 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1.977242 | 499,432.8 | kv_read | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 17.037046 | 870,190.3 | link_latency | 8.62x |
| DeepSeek-V4-Pro-0813 | 1024 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1.431476 | 529,350.3 | kv_read | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 7.262361 | 879,128.6 | link_latency | 5.07x |
| DeepSeek-V4-Pro-0813 | 4096 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66` | 1.313854 | 539,838.7 | kv_read | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 4.569958 | 1,027,363.2 | weight_read | 3.48x |
| Qwen3-8B | 1 | 46,225 | `Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 0.457128 | 4,246.5 | layer_fixed_latency | `Qwen3-8B/a100_sxm_80gb-x56-tensor` | 13.574827 | 9,261.0 | link_latency | 29.70x |
| Qwen3-8B | 2 | 56,235 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill` | 0.718015 | 9,916.5 | link_latency | `Qwen3-8B/a100_sxm_80gb-x68-tensor` | 8.517024 | 11,018.0 | link_latency | 11.86x |
| Qwen3-8B | 4 | 56,235 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill` | 0.427343 | 9,916.5 | link_latency | `Qwen3-8B/a100_sxm_80gb-x68-hybrid` | 5.111027 | 11,994.8 | link_latency | 11.36x |
| Qwen3-8B | 8 | 92,095 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x113-romfill` | 0.374110 | 16,116.0 | link_latency | `Qwen3-8B/a100_sxm_80gb-x111-hybrid` | 4.446529 | 20,250.7 | link_latency | 11.89x |
| Qwen3-8B | 16 | 224,940 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 0.424274 | 38,338.7 | link_latency | `Qwen3-8B/a100_sxm_80gb-x272-hybrid` | 5.233857 | 48,859.1 | link_latency | 12.34x |
| Qwen3-8B | 32 | 224,940 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 0.291168 | 49,154.9 | kv_read | `Qwen3-8B/a100_sxm_80gb-x272-hybrid` | 4.007966 | 70,737.4 | weight_read | 13.77x |
| Qwen3-8B | 64 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.255600 | 65,297.6 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 2.633113 | 87,411.4 | weight_read | 10.30x |
| Qwen3-8B | 256 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.211254 | 85,367.4 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.852323 | 89,754.7 | weight_read | 4.03x |
| Qwen3-8B | 1024 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.203378 | 89,619.4 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.407126 | 93,821.5 | kv_read | 2.00x |
| Qwen3-8B | 4096 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.230655 | 104,593.8 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.311563 | 102,547.4 | kv_read | 1.35x |

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
| Qwen3-8B | 1 | 46,225 | 13,272.7 | wafer-pipeline | 9,289.5 | wafer-tensor | 1.43x | 2,274.9 | pipeline | 682.2 | tensor | 3.33x | 5.83x | 13.62x | 2.33x |
| Qwen3-8B | 2 | 92,450 | 12,950.5 | wafer-pipeline | 8,421.9 | wafer-hybrid | 1.54x | 2,847.2 | pipeline | 722.4 | tensor | 3.94x | 4.55x | 11.66x | 2.56x |
| Qwen3-8B | 3 | 138,675 | 12,875.6 | wafer-pipeline | 7,746.4 | wafer-hybrid | 1.66x | 3,107.8 | pipeline | 736.9 | tensor | 4.22x | 4.14x | 10.51x | 2.54x |
| Qwen3-8B | 4 | 184,900 | 12,835.3 | wafer-pipeline | 7,167.3 | wafer-hybrid | 1.79x | 3,256.9 | pipeline | 744.4 | tensor | 4.38x | 3.94x | 9.63x | 2.44x |
| Qwen3-8B | 6 | 277,350 | 12,791.1 | wafer-pipeline | 6,231.8 | wafer-hybrid | 2.05x | 3,421.0 | pipeline | 675.1 | hybrid | 5.07x | 3.74x | 9.23x | 2.47x |
| Qwen3-8B | 8 | 369,800 | 12,767.2 | wafer-pipeline | 5,510.9 | wafer-hybrid | 2.32x | 3,509.4 | pipeline | 684.2 | hybrid | 5.13x | 3.64x | 8.05x | 2.21x |
| Qwen3-8B | 12 | 554,700 | 13,287.1 | wafer-pipeline | 5,423.1 | wafer-hybrid | 2.45x | 3,602.5 | pipeline | 676.4 | hybrid | 5.33x | 3.69x | 8.02x | 2.17x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 4,733.2 | wafer-pipeline | 3,176.6 | wafer-tensor | 1.49x | 1,576.3 | pipeline | 401.1 | hybrid | 3.93x | 3.00x | 7.92x | 2.64x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 4,739.2 | wafer-pipeline | 3,938.3 | wafer-hybrid | 1.20x | 1,733.6 | pipeline | 397.4 | hybrid | 4.36x | 2.73x | 9.91x | 3.62x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 4,740.4 | wafer-pipeline | 3,809.5 | wafer-hybrid | 1.24x | 1,793.2 | pipeline | 393.8 | hybrid | 4.55x | 2.64x | 9.67x | 3.66x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 4,740.4 | wafer-pipeline | 3,698.3 | wafer-hybrid | 1.28x | 1,824.6 | pipeline | 390.2 | hybrid | 4.68x | 2.60x | 9.48x | 3.65x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 4,740.4 | wafer-pipeline | 3,478.5 | wafer-hybrid | 1.36x | 1,857.1 | pipeline | 383.2 | hybrid | 4.85x | 2.55x | 9.08x | 3.56x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 4,740.4 | wafer-pipeline | 3,318.5 | wafer-hybrid | 1.43x | 1,873.7 | pipeline | 382.7 | hybrid | 4.90x | 2.53x | 8.67x | 3.43x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 4,740.4 | wafer-pipeline | 3,136.1 | wafer-hybrid | 1.51x | 1,890.7 | pipeline | 382.7 | hybrid | 4.94x | 2.51x | 8.20x | 3.27x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 2,094.0 | wafer-pipeline | 1,707.7 | wafer-hybrid | 1.23x | 1,171.6 | pipeline | 169.1 | hybrid | 6.93x | 1.79x | 10.10x | 5.65x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 2,125.3 | wafer-pipeline | 1,899.8 | wafer-hybrid | 1.12x | 1,221.6 | pipeline | 167.4 | hybrid | 7.30x | 1.74x | 11.35x | 6.52x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 2,145.9 | wafer-hybrid | 1,958.8 | wafer-hybrid | 1.10x | 1,248.3 | pipeline | 165.7 | hybrid | 7.53x | 1.72x | 11.82x | 6.88x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 2,125.4 | wafer-pipeline | 1,894.1 | wafer-hybrid | 1.12x | 1,276.1 | pipeline | 165.1 | hybrid | 7.73x | 1.67x | 11.47x | 6.89x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 2.17x to 6.89x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 9,289.5 | 9,289.5 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,116.03 | 682.2 | 682.2 | link_latency | 13.62x | 1.69x | 94.38x | 13.62x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x5 | 4,075 | 4,984.0 | 4,984.0 | compute | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 371.29 | 396.3 | 396.3 | weight_read | 12.58x | 10.05x | 50.25x | 12.58x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill | 168,705 | 5,514.8 | 71,692.0 | link_latency | Qwen3-8B/a100_sxm_80gb-x204-tensor | 168,504 | 1.00x | tensor | 1,230.39 | 687.0 | 1,374.1 | link_latency | 8.03x | 3.57x | 56.03x | 8.03x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 5,371.7 | 26,858.7 | link_latency | Qwen3-8B/a100_sxm_80gb-x68-tensor | 56,168 | 1.00x | tensor | 1,216.68 | 646.8 | 1,293.6 | link_latency | 8.30x | 4.01x | 54.57x | 8.30x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill | 168,705 | 5,514.8 | 71,692.0 | link_latency | Qwen3-8B/a100_sxm_80gb-x204-hybrid | 168,504 | 1.00x | hybrid | 1,126.82 | 669.4 | 2,677.5 | link_latency | 8.24x | 3.57x | 56.03x | 8.24x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 5,371.7 | 26,858.7 | link_latency | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 1,218.77 | 586.7 | 2,346.8 | link_latency | 9.16x | 4.01x | 54.57x | 9.16x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x207-romfill | 168,705 | 5,514.8 | 71,692.0 | link_latency | Qwen3-8B/a100_sxm_80gb-x204-hybrid | 168,504 | 1.00x | hybrid | 1,224.14 | 622.8 | 4,982.6 | link_latency | 8.85x | 3.57x | 56.03x | 8.85x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 5,145.5 | 46,309.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 392.77 | 533.1 | 4,798.3 | weight_read | 9.65x | 6.92x | 52.28x | 9.65x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 5,429.1 | 97,723.3 | link_latency | Qwen3-8B/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 1,194.61 | 583.5 | 9,335.2 | link_latency | 9.31x | 3.65x | 55.16x | 9.31x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 3,620.0 | 65,159.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 400.16 | 510.6 | 8,170.2 | weight_read | 7.09x | 7.98x | 36.78x | 7.09x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 5,053.4 | 217,298.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,299.18 | 542.6 | 17,362.5 | link_latency | 9.31x | 6.59x | 51.34x | 9.31x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 2,319.7 | 74,231.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 417.06 | 465.7 | 14,902.1 | weight_read | 4.98x | 4.98x | 23.57x | 4.98x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,991.7 | 255,468.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 466.04 | 518.7 | 33,197.0 | weight_read | 7.70x | 7.70x | 40.55x | 7.76x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 1,307.8 | 83,699.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 450.85 | 396.0 | 25,342.8 | weight_read | 3.30x | 3.30x | 13.29x | 3.30x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 1,578.5 | 404,097.6 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 549.93 | 411.4 | 105,306.0 | weight_read | 3.84x | 3.84x | 16.04x | 3.88x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | 56,235 | 355.5 | 91,014.4 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 653.58 | 208.6 | 53,406.1 | kv_read | 1.70x | 1.70x | 4.33x | 1.70x |
| Qwen3-8B | 1024 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 430.3 | 440,653.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 885.48 | 225.0 | 230,448.5 | kv_read | 1.91x | 1.91x | 5.02x | 1.94x |
| Qwen3-8B | 1024 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | 56,235 | 90.3 | 92,509.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 1,464.51 | 72.1 | 73,850.7 | kv_read | 1.25x | 1.25x | 1.85x | 1.25x |
| Qwen3-8B | 4096 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 110.7 | 453,464.8 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,029.76 | 80.4 | 329,138.0 | kv_read | 1.38x | 1.38x | 2.04x | 1.44x |
| Qwen3-8B | 4096 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | 56,235 | 22.7 | 92,891.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-pipeline | 56,168 | 1.00x | pipeline | 217.61 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 3,938.3 | 3,938.3 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 1,368.19 | 397.4 | 5,563.8 | link_latency | 9.91x | 0.26x | 28.57x | 9.91x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x37 | 30,155 | 1,581.6 | 1,581.6 | link_latency | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 0.99x | hybrid | 1,338.12 | 392.7 | 1,963.4 | link_latency | 4.03x | 0.31x | 11.45x | 4.03x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,217.9 | 57,922.9 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x560-hybrid | 462,560 | 1.00x | hybrid | 1,465.09 | 382.7 | 26,787.3 | link_latency | 8.41x | 0.75x | 23.34x | 8.61x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 2,940.6 | 117,622.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,354.83 | 396.5 | 3,965.1 | link_latency | 7.42x | 10.94x | 21.33x | 7.42x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,217.9 | 57,922.9 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x560-hybrid | 462,560 | 1.00x | hybrid | 1,465.09 | 382.7 | 26,787.3 | link_latency | 8.41x | 0.75x | 23.34x | 8.61x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 2,940.6 | 117,622.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,354.83 | 396.5 | 3,965.1 | link_latency | 7.42x | 10.94x | 21.33x | 7.42x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,217.9 | 57,922.9 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x560-hybrid | 462,560 | 1.00x | hybrid | 1,465.09 | 382.7 | 26,787.3 | link_latency | 8.41x | 0.75x | 23.34x | 8.61x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 2,940.6 | 117,622.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,354.83 | 396.5 | 3,965.1 | link_latency | 7.42x | 10.94x | 21.33x | 7.42x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,217.9 | 57,922.9 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x560-hybrid | 462,560 | 1.00x | hybrid | 1,465.09 | 382.7 | 26,787.3 | link_latency | 8.41x | 0.75x | 23.34x | 8.61x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 2,940.6 | 117,622.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,453.54 | 361.1 | 5,777.4 | link_latency | 8.14x | 10.94x | 21.33x | 8.14x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,094.0 | 111,384.0 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x560-hybrid | 462,560 | 1.00x | hybrid | 1,465.09 | 382.7 | 26,787.3 | link_latency | 8.09x | 1.44x | 22.45x | 8.28x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 2,940.6 | 117,622.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 1,716.79 | 292.4 | 9,357.0 | link_latency | 10.06x | 10.94x | 21.33x | 10.06x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill | 257,540 | 2,805.9 | 221,668.6 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x312-hybrid | 257,712 | 1.00x | hybrid | 1,581.57 | 346.7 | 22,188.0 | link_latency | 8.09x | 5.15x | 20.36x | 8.09x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 2,301.9 | 147,324.1 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 2,228.38 | 213.5 | 13,663.7 | link_latency | 10.78x | 10.78x | 16.70x | 10.78x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 2,237.6 | 572,823.4 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,742.42 | 215.7 | 55,209.6 | weight_read | 10.38x | 10.38x | 16.23x | 10.63x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79 | 64,385 | 916.6 | 234,642.3 | compute | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 2,825.26 | 96.9 | 24,801.0 | weight_read | 9.46x | 9.46x | 11.15x | 9.46x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 877.4 | 898,498.6 | compute | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 2,996.94 | 99.1 | 101,489.2 | weight_read | 8.85x | 8.85x | 10.25x | 9.01x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79 | 64,385 | 257.5 | 263,642.5 | compute | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 8,285.12 | 37.3 | 38,219.1 | weight_read | 6.90x | 6.90x | 8.00x | 6.90x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316 | 257,540 | 296.6 | 1,215,047.5 | weight_read | DSV4-Flash/a100_sxm_80gb-x312-hybrid | 257,712 | 1.00x | hybrid | 3,754.05 | 36.4 | 149,235.1 | weight_read | 8.14x | 8.14x | 9.22x | 8.31x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79 | 64,385 | 66.1 | 270,678.5 | compute | DSV4-Flash/a100_sxm_80gb-x78-pipeline | 64,428 | 1.00x | pipeline | 661.34 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x9 | 416,025 | 1,973.7 | 1,973.7 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x504-hybrid | 416,304 | 1.00x | hybrid | 2,792.18 | 165.1 | 10,402.6 | link_latency | 11.95x | 0.10x | 50.14x | 11.96x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x190 | 154,850 | 374.3 | 374.3 | link_latency | DSV4-Pro/a100_sxm_80gb-x187-hybrid | 154,462 | 1.00x | hybrid | 2,632.18 | 167.6 | 4,021.4 | weight_read | 2.23x | 0.05x | 9.51x | 2.23x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 97,733.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 165.1 | 76,267.6 | link_latency | 8.97x | 0.67x | 37.62x | 10.52x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 97,733.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 165.1 | 76,267.6 | link_latency | 8.97x | 0.67x | 37.62x | 10.52x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 97,733.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 165.1 | 76,267.6 | link_latency | 8.97x | 0.67x | 37.62x | 10.52x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 97,733.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 165.1 | 76,267.6 | link_latency | 8.97x | 0.67x | 37.62x | 10.52x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 97,733.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 165.1 | 76,267.6 | link_latency | 8.97x | 0.67x | 37.62x | 10.52x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 97,733.6 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 165.1 | 76,267.6 | link_latency | 8.97x | 0.67x | 37.62x | 10.52x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 986.7 | 252,590.6 | kv_read | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 2,792.18 | 165.1 | 76,267.6 | link_latency | 5.98x | 1.74x | 25.07x | 7.01x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 361.1 | 369,793.3 | kv_read | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 4,012.72 | 118.2 | 121,052.7 | link_latency | 3.05x | 2.54x | 9.17x | 3.53x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 100.3 | 410,881.9 | kv_read | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 5,120.90 | 54.9 | 224,808.0 | weight_read | 1.83x | 1.83x | 2.65x | 2.14x |

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
| DeepSeek-V4-Flash-0731 | 30,155 | 4.03x | 4.03x → 4.03x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 31,785 | 5.20x | 5.20x → 5.20x | 3.76x → 13.01x | 4.10x → 10.75x | 3.5x |
| DeepSeek-V4-Flash-0731 | 35,860 | 6.23x | 6.23x → 6.23x | 4.54x → 15.45x | 5.03x → 13.44x | 3.4x |
| DeepSeek-V4-Flash-0731 | 37,490 | 6.35x | 6.35x → 6.35x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 43,195 | 6.97x | 6.97x → 6.97x | 5.06x → 17.45x | 5.46x → 16.05x | 3.4x |
| DeepSeek-V4-Flash-0731 | 46,225 | 7.92x | 10.56x → 7.58x | 5.69x → 20.09x | 7.59x → 19.24x | 3.5x |
| DeepSeek-V4-Flash-0731 | 46,455 | 7.01x | 7.01x → 7.01x | 5.04x → 17.79x | 5.38x → 16.74x | 3.5x |
| DeepSeek-V4-Flash-0731 | 48,900 | 7.39x | 7.39x → 7.39x | 5.37x → 18.51x | — | 3.4x |
| DeepSeek-V4-Flash-0731 | 51,345 | 7.34x | 7.34x → 7.34x | 5.30x → 18.55x | 5.67x → 17.74x | 3.5x |
| DeepSeek-V4-Flash-0731 | 57,050 | 7.61x | 7.61x → 7.61x | 5.51x → 19.26x | 5.81x → 18.60x | 3.5x |
| DeepSeek-V4-Flash-0731 | 63,570 | 7.84x | 7.84x → 7.84x | 5.67x → 19.88x | — | 3.5x |
| DeepSeek-V4-Flash-0731 | 64,385 | 7.79x | 7.79x → 7.79x | 5.36x → 18.86x | 5.73x → 18.19x | 3.5x |
| DeepSeek-V4-Flash-0731 | 65,200 | 7.82x | 7.82x → 7.82x | 5.64x → 19.93x | 5.88x → 19.18x | 3.5x |
| DeepSeek-V4-Flash-0731 | 68,460 | 7.66x | 7.66x → 7.66x | 5.56x → 19.41x | — | 3.5x |
| DeepSeek-V4-Flash-0731 | 69,275 | 7.62x | 7.62x → 7.62x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 70,090 | 7.65x | 7.65x → 7.65x | 5.53x → 19.46x | 5.82x → 18.71x | 3.5x |
| DeepSeek-V4-Flash-0731 | 80,685 | 7.57x | 7.57x → 7.57x | 5.50x → 19.26x | 5.85x → 18.53x | 3.5x |
| DeepSeek-V4-Flash-0731 | 85,575 | 7.37x | 7.37x → 7.37x | 5.32x → 18.97x | 5.67x → 18.26x | 3.6x |
| DeepSeek-V4-Flash-0731 | 92,095 | 7.26x | 7.26x → 7.26x | 5.24x → 18.68x | 5.62x → 17.89x | 3.6x |
| DeepSeek-V4-Flash-0731 | 92,450 | 9.91x | 11.24x → 9.74x | 7.15x → 25.56x | 8.11x → 25.11x | 3.6x |
| DeepSeek-V4-Flash-0731 | 96,985 | 7.20x | 7.20x → 7.20x | 5.21x → 18.52x | 5.58x → 17.55x | 3.6x |
| DeepSeek-V4-Flash-0731 | 114,100 | 7.07x | 7.07x → 7.07x | 5.13x → 18.25x | 5.51x → 16.99x | 3.6x |
| DeepSeek-V4-Flash-0731 | 128,770 | 7.17x | 7.17x → 7.17x | 5.20x → 18.66x | 5.58x → 17.92x | 3.6x |
| DeepSeek-V4-Flash-0731 | 138,550 | 7.11x | 7.11x → 7.11x | 5.15x → 18.62x | 5.52x → 17.93x | 3.6x |
| DeepSeek-V4-Flash-0731 | 138,675 | 9.67x | 11.11x → 9.43x | 7.00x → 25.34x | 8.04x → 24.71x | 3.6x |
| DeepSeek-V4-Flash-0731 | 184,900 | 9.48x | 11.05x → 9.24x | 6.88x → 25.20x | 8.02x → 24.57x | 3.7x |
| DeepSeek-V4-Flash-0731 | 185,005 | 7.19x | 7.19x → 7.19x | 5.22x → 19.11x | 5.60x → 18.34x | 3.7x |
| DeepSeek-V4-Flash-0731 | 193,155 | 7.25x | 7.25x → 7.25x | 5.28x → 19.26x | 5.67x → 18.52x | 3.6x |
| DeepSeek-V4-Flash-0731 | 257,540 | 7.29x | 7.29x → 7.29x | 5.32x → 19.84x | 5.71x → 19.06x | 3.7x |
| DeepSeek-V4-Flash-0731 | 277,100 | 7.33x | 7.33x → 7.33x | 5.35x → 20.04x | 5.75x → 19.25x | 3.7x |
| DeepSeek-V4-Flash-0731 | 277,350 | 9.08x | 11.02x → 8.84x | 6.63x → 24.84x | 8.04x → 24.20x | 3.7x |
| DeepSeek-V4-Flash-0731 | 369,800 | 8.67x | 10.89x → 8.36x | 6.33x → 23.78x | 7.95x → 22.92x | 3.8x |
| DeepSeek-V4-Flash-0731 | 462,250 | 8.41x | 10.66x → 8.06x | 6.14x → 23.06x | 7.79x → 22.11x | 3.8x |
| DeepSeek-V4-Flash-0731 | 554,700 | 8.20x | 10.59x → 7.85x | 5.98x → 22.47x | 7.73x → 21.52x | 3.8x |
| DeepSeek-V4-Pro-0813 | 154,850 | 2.23x | 2.23x → 2.23x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 159,740 | 3.41x | 3.41x → 3.41x | 2.84x → 6.65x | — | 2.3x |
| DeepSeek-V4-Pro-0813 | 184,900 | 10.10x | 12.43x → 9.76x | 8.39x → 19.95x | 10.32x → 19.29x | 2.4x |
| DeepSeek-V4-Pro-0813 | 185,005 | 4.92x | 4.92x → 4.92x | 4.09x → 9.72x | 4.54x → 8.18x | 2.4x |
| DeepSeek-V4-Pro-0813 | 193,155 | 5.21x | 5.21x → 5.21x | 4.34x → 10.26x | 4.81x → 8.80x | 2.4x |
| DeepSeek-V4-Pro-0813 | 221,680 | 5.67x | 5.67x → 5.67x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 231,460 | 5.83x | 5.83x → 5.83x | 4.85x → 11.64x | 5.20x → 10.14x | 2.4x |
| DeepSeek-V4-Pro-0813 | 259,985 | 6.17x | 6.17x → 6.17x | 5.13x → 12.33x | — | 2.4x |
| DeepSeek-V4-Pro-0813 | 276,285 | 6.22x | 6.22x → 6.22x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 277,100 | 6.22x | 6.22x → 6.22x | 5.18x → 12.52x | 5.53x → 10.81x | 2.4x |
| DeepSeek-V4-Pro-0813 | 277,350 | 11.35x | 13.53x → 11.02x | 9.44x → 22.84x | 11.26x → 22.18x | 2.4x |
| DeepSeek-V4-Pro-0813 | 290,955 | 6.29x | 6.29x → 6.29x | 5.23x → 12.70x | — | 2.4x |
| DeepSeek-V4-Pro-0813 | 308,070 | 6.38x | 6.38x → 6.38x | 5.31x → 12.90x | 5.68x → 11.20x | 2.4x |
| DeepSeek-V4-Pro-0813 | 316,220 | 6.40x | 6.40x → 6.40x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 317,035 | 6.40x | 6.40x → 6.40x | 5.33x → 12.98x | 5.70x → 11.28x | 2.4x |
| DeepSeek-V4-Pro-0813 | 323,575 | 11.62x | 13.58x → 11.40x | 9.68x → 23.61x | 11.31x → 23.15x | 2.4x |
| DeepSeek-V4-Pro-0813 | 369,800 | 11.82x | 13.78x → 11.59x | 9.85x → 24.22x | 11.49x → 23.74x | 2.5x |
| DeepSeek-V4-Pro-0813 | 416,025 | 11.95x | 13.85x → 11.71x | 9.97x → 24.65x | 11.54x → 24.14x | 2.5x |
| DeepSeek-V4-Pro-0813 | 554,700 | 11.47x | 13.70x → 11.16x | 9.56x → 23.65x | 11.42x → 23.01x | 2.5x |
| DeepSeek-V4-Pro-0813 | 3,050,850 | 8.97x | 10.80x → 8.57x | 7.48x → 18.49x | 9.00x → 17.67x | 2.5x |
| Qwen3-8B | 4,075 | 12.58x | 12.58x → 12.58x | 11.49x → 18.25x | 12.26x → 15.74x | 1.6x |
| Qwen3-8B | 4,890 | 14.93x | 14.93x → 14.93x | 13.44x → 22.68x | 14.71x → 18.61x | 1.7x |
| Qwen3-8B | 5,705 | 14.86x | 14.86x → 14.86x | 13.20x → 23.50x | 14.61x → 18.90x | 1.8x |
| Qwen3-8B | 6,520 | 14.05x | 14.05x → 14.05x | 12.32x → 23.02x | 13.69x → 18.37x | 1.9x |
| Qwen3-8B | 8,150 | 16.29x | 16.29x → 16.29x | 12.99x → 26.90x | — | 2.1x |
| Qwen3-8B | 9,780 | 15.43x | 15.43x → 15.43x | 12.06x → 25.05x | 13.98x → 21.34x | 2.1x |
| Qwen3-8B | 12,225 | 14.55x | 14.55x → 14.55x | 11.37x → 23.72x | — | 2.1x |
| Qwen3-8B | 13,040 | 14.09x | 14.09x → 14.09x | 11.20x → 23.38x | 12.46x → 18.77x | 2.1x |
| Qwen3-8B | 46,225 | 13.62x | 17.36x → 13.12x | 9.40x → 28.58x | 11.98x → 27.54x | 3.0x |
| Qwen3-8B | 46,455 | 8.40x | 8.40x → 8.40x | 5.80x → 17.63x | 6.76x → 14.32x | 3.0x |
| Qwen3-8B | 56,235 | 7.72x | 7.72x → 7.72x | 5.28x → 17.16x | 6.10x → 13.99x | 3.2x |
| Qwen3-8B | 60,310 | 7.82x | 7.82x → 7.82x | 5.33x → 17.85x | — | 3.3x |
| Qwen3-8B | 70,905 | 7.66x | 7.66x → 7.66x | 5.19x → 17.37x | 6.00x → 14.12x | 3.3x |
| Qwen3-8B | 84,760 | 7.60x | 7.60x → 7.60x | 5.12x → 17.61x | 5.93x → 14.25x | 3.4x |
| Qwen3-8B | 92,095 | 7.46x | 7.46x → 7.46x | 5.01x → 17.47x | 5.79x → 13.95x | 3.5x |
| Qwen3-8B | 92,450 | 11.66x | 14.52x → 11.23x | 7.83x → 27.23x | 9.75x → 26.24x | 3.5x |
| Qwen3-8B | 112,470 | 7.52x | 7.52x → 7.52x | 5.03x → 18.13x | 5.83x → 14.21x | 3.6x |
| Qwen3-8B | 138,550 | 7.45x | 7.45x → 7.45x | 4.96x → 18.60x | 5.75x → 14.54x | 3.8x |
| Qwen3-8B | 138,675 | 10.51x | 12.85x → 10.14x | 7.00x → 26.26x | 8.55x → 25.34x | 3.8x |
| Qwen3-8B | 168,705 | 7.43x | 7.43x → 7.43x | 4.93x → 19.44x | 5.73x → 15.18x | 3.9x |
| Qwen3-8B | 184,900 | 9.63x | 11.72x → 9.30x | 6.37x → 25.41x | 7.76x → 24.55x | 4.0x |
| Qwen3-8B | 185,005 | 7.30x | 7.30x → 7.30x | 4.83x → 19.26x | 5.61x → 15.08x | 4.0x |
| Qwen3-8B | 224,940 | 7.25x | 7.25x → 7.25x | 4.79x → 19.98x | 5.57x → 15.53x | 4.2x |
| Qwen3-8B | 277,100 | 8.02x | 8.02x → 8.02x | 5.56x → 20.17x | 6.47x → 15.72x | 3.6x |
| Qwen3-8B | 277,350 | 9.23x | 11.85x → 8.94x | 6.40x → 23.21x | 8.21x → 22.47x | 3.6x |
| Qwen3-8B | 369,800 | 8.05x | 11.64x → 7.81x | 5.55x → 20.52x | 8.02x → 19.90x | 3.7x |
| Qwen3-8B | 554,700 | 8.02x | 11.70x → 7.72x | 5.55x → 20.20x | 8.10x → 19.46x | 3.6x |

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

| Fabric clock | GHz | In stated band | Qwen3-8B fixed latency/token | DeepSeek-V4-Flash-0731 @ 46,225 mm2 | DeepSeek-V4-Pro-0813 @ 184,900 mm2 | Qwen3-8B @ 4,890 mm2 |
|---|---:|---|---:|---:|---:|---:|
| `band_low` | 0.5000 | yes | 11.53 us | 7.92x | 10.10x | 14.93x |
| `stated` | 1.0000 | yes | 6.82 us | 7.92x | 10.10x | 14.93x |
| `band_high` | 2.0000 | yes | 4.46 us | 7.92x | 10.10x | 14.93x |
| `asap7_reduction_s8_g2` | 1.2874 | yes | 5.77 us | 7.92x | 10.10x | 14.93x |
| `asap7_add_bf16_sram_engine` | 0.2391 | **no** | 21.83 us | 7.92x | 10.10x | 14.93x |
| `asap7_matmul_bf16_sram_engine` | 0.0580 | **no** | 83.47 us | 7.92x | 10.10x | 14.93x |

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

| ROM cell ratio | Value | In stated band | ROM capacity | Full-array sweep | DeepSeek-V4-Flash-0731 @ 46,225 mm2 | DeepSeek-V4-Pro-0813 @ 184,900 mm2 | Qwen3-8B @ 4,890 mm2 |
|---|---:|---|---:|---:|---:|---:|---:|
| `band_low` | 0.1100 | yes | 21.886 MB/mm2 | 103.4 us | 7.92x | 11.80x | 15.94x |
| `stated` | 0.3300 | yes | 7.295 MB/mm2 | 34.5 us | 7.92x | 10.10x | 14.93x |
| `band_high` | 0.3300 | yes | 7.295 MB/mm2 | 34.5 us | 7.92x | 10.10x | 14.93x |
| `measured_ihp_sg13g2_130nm` | 0.1298 | yes | 18.553 MB/mm2 | 87.7 us | 7.92x | 11.87x | 15.94x |
| `measured_asap7_7nm_via_programmed` | 0.2500 | yes | 9.630 MB/mm2 | 45.5 us | 7.92x | 10.98x | 15.94x |
| `measured_asap7_7nm_shared_source_drain` | 0.1250 | yes | 19.259 MB/mm2 | 91.0 us | 7.92x | 11.90x | 15.94x |

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
| DeepSeek-V4-Flash-0731 | 19 | 15,694 | 139.1 | 196.6 | 373.7 | hybrid | 1,331.44 | 49.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 22 | 18,172 | 138.9 | 198.0 | 392.6 | hybrid | 1,331.44 | 52.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 37 | 30,562 | 138.2 | 189.6 | 392.7 | hybrid | 1,338.12 | 52.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 38 | 31,388 | 138.1 | 189.6 | 396.0 | hybrid | 1,338.12 | 53.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 35,518 | 137.8 | 187.1 | 388.2 | hybrid | 1,341.46 | 52.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 45 | 37,170 | 137.8 | 187.1 | 393.8 | hybrid | 1,341.46 | 52.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 52 | 42,952 | 137.8 | 185.1 | 392.1 | hybrid | 1,344.80 | 52.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 137.8 | 184.9 | 401.1 | hybrid | 1,344.80 | 53.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 59 | 48,734 | 137.8 | 183.4 | 390.7 | hybrid | 1,348.14 | 52.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 62 | 51,212 | 137.8 | 183.2 | 396.8 | hybrid | 1,348.14 | 53.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 69 | 56,994 | 137.8 | 169.5 | 395.0 | hybrid | 1,351.49 | 53.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 77 | 63,602 | 137.8 | 168.2 | 395.0 | hybrid | 1,354.83 | 53.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 78 | 64,428 | 137.8 | 168.2 | 396.5 | hybrid | 1,354.83 | 53.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 79 | 65,254 | 137.8 | 168.1 | 398.0 | hybrid | 1,354.83 | 53.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 81 | 66,906 | 137.8 | 167.4 | 389.0 | hybrid | 1,358.17 | 52.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 83 | 68,558 | 137.8 | 167.2 | 392.0 | hybrid | 1,358.17 | 53.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 84 | 69,384 | 137.8 | 167.2 | 393.4 | hybrid | 1,358.17 | 53.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 85 | 70,210 | 137.8 | 167.1 | 394.9 | hybrid | 1,358.17 | 53.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 98 | 80,948 | 137.8 | 165.2 | 390.8 | hybrid | 1,364.85 | 53.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 104 | 85,904 | 137.8 | 164.7 | 397.9 | hybrid | 1,364.85 | 54.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 111 | 91,686 | 137.8 | 163.8 | 396.4 | hybrid | 1,368.19 | 54.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 137.8 | 163.7 | 397.4 | hybrid | 1,368.19 | 54.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 117 | 96,642 | 137.8 | 163.0 | 393.9 | hybrid | 1,371.53 | 54.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 138 | 113,988 | 137.8 | 160.5 | 390.3 | hybrid | 1,381.56 | 53.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 156 | 128,856 | 137.8 | 158.7 | 391.3 | hybrid | 1,388.24 | 54.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 137.8 | 157.5 | 393.8 | hybrid | 1,391.58 | 54.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 137.8 | 152.2 | 390.2 | hybrid | 1,414.97 | 55.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 234 | 193,284 | 137.8 | 151.2 | 386.3 | hybrid | 1,421.65 | 54.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 312 | 257,712 | 137.8 | 144.7 | 384.6 | hybrid | 1,451.73 | 55.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 335 | 276,710 | 137.8 | 125.6 | 382.8 | hybrid | 1,461.75 | 56.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 137.8 | 125.6 | 383.2 | hybrid | 1,461.75 | 56.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 137.8 | 119.2 | 382.7 | hybrid | 1,465.09 | 56.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 560 | 462,560 | 137.8 | 113.6 | 382.7 | hybrid | 1,465.09 | 56.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 137.8 | 108.4 | 382.7 | hybrid | 1,465.09 | 56.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 39.4 | 60.9 | 171.7 | hybrid | 2,558.67 | 43.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 100 | 82,600 | 39.4 | 57.2 | 167.9 | hybrid | 2,584.61 | 43.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 101 | 83,426 | 39.4 | 57.2 | 168.7 | hybrid | 2,584.61 | 43.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 39.4 | 56.6 | 170.9 | hybrid | 2,588.94 | 44.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 39.4 | 52.6 | 170.0 | hybrid | 2,619.21 | 44.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 187 | 154,462 | 39.4 | 51.9 | 167.6 | hybrid | 2,632.18 | 44.1% | weight_read |
| DeepSeek-V4-Pro-0813 | 193 | 159,418 | 39.4 | 51.6 | 166.7 | hybrid | 2,636.51 | 44.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 203 | 167,678 | 39.4 | 51.3 | 167.5 | hybrid | 2,640.83 | 44.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 207 | 170,982 | 39.4 | 51.2 | 169.0 | hybrid | 2,640.83 | 44.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 39.4 | 50.7 | 169.1 | hybrid | 2,649.48 | 44.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 234 | 193,284 | 39.4 | 50.4 | 166.9 | hybrid | 2,658.13 | 44.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 268 | 221,368 | 39.4 | 49.4 | 167.2 | hybrid | 2,675.43 | 44.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 39.4 | 49.1 | 168.2 | hybrid | 2,679.75 | 45.1% | weight_read |
| DeepSeek-V4-Pro-0813 | 315 | 260,190 | 39.4 | 48.1 | 166.4 | hybrid | 2,701.37 | 45.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 334 | 275,884 | 39.4 | 44.7 | 166.9 | hybrid | 2,710.02 | 45.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 335 | 276,710 | 39.4 | 44.7 | 167.2 | hybrid | 2,710.02 | 45.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 39.4 | 44.7 | 167.4 | hybrid | 2,710.02 | 45.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 352 | 290,752 | 39.4 | 44.3 | 167.2 | hybrid | 2,718.67 | 45.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 373 | 308,098 | 39.4 | 43.9 | 166.2 | hybrid | 2,731.64 | 45.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 383 | 316,358 | 39.4 | 43.7 | 166.5 | hybrid | 2,735.97 | 45.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 384 | 317,184 | 39.4 | 43.6 | 166.7 | hybrid | 2,735.97 | 45.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 392 | 323,792 | 39.4 | 43.5 | 166.5 | hybrid | 2,740.29 | 45.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 39.4 | 42.3 | 165.7 | hybrid | 2,770.56 | 45.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 504 | 416,304 | 39.4 | 41.3 | 165.1 | hybrid | 2,792.18 | 46.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 574 | 474,124 | 39.4 | 40.0 | 164.9 | hybrid | 2,792.18 | 46.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 39.4 | 38.4 | 165.1 | hybrid | 2,792.18 | 46.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 3694 | 3,051,244 | 39.4 | 17.2 | 165.1 | hybrid | 2,792.18 | 46.1% | link_latency |
| Qwen3-8B | 3 | 2,478 | 99.2 | 260.3 | — | tensor | 370.24 | 9.6% | weight_read |
| Qwen3-8B | 4 | 3,304 | 99.2 | 331.3 | — | tensor | 370.90 | 12.3% | weight_read |
| Qwen3-8B | 5 | 4,130 | 99.2 | 396.3 | — | tensor | 371.29 | 14.7% | weight_read |
| Qwen3-8B | 6 | 4,956 | 99.2 | 455.8 | — | tensor | 371.55 | 16.9% | weight_read |
| Qwen3-8B | 7 | 5,782 | 99.1 | 510.6 | — | tensor | 371.74 | 19.0% | weight_read |
| Qwen3-8B | 8 | 6,608 | 99.1 | 561.2 | — | tensor | 371.88 | 20.9% | weight_read |
| Qwen3-8B | 10 | 8,260 | 99.1 | 445.4 | 395.5 | tensor | 1,082.33 | 48.2% | link_latency |
| Qwen3-8B | 12 | 9,912 | 99.0 | 480.7 | 454.8 | tensor | 1,082.33 | 52.0% | link_latency |
| Qwen3-8B | 15 | 12,390 | 98.9 | 522.2 | 535.1 | hybrid | 376.27 | 20.1% | weight_read |
| Qwen3-8B | 16 | 13,216 | 98.9 | 533.6 | 559.8 | hybrid | 376.27 | 21.1% | weight_read |
| Qwen3-8B | 56 | 46,256 | 98.4 | 682.2 | 610.9 | tensor | 1,116.03 | 76.1% | link_latency |
| Qwen3-8B | 68 | 56,168 | 98.4 | 695.6 | 630.4 | tensor | 1,119.03 | 77.8% | link_latency |
| Qwen3-8B | 69 | 56,994 | 98.4 | 696.6 | 632.1 | tensor | 1,119.03 | 78.0% | link_latency |
| Qwen3-8B | 73 | 60,298 | 98.4 | 699.9 | 638.4 | tensor | 1,120.08 | 78.4% | link_latency |
| Qwen3-8B | 86 | 71,036 | 98.4 | 709.7 | 655.6 | tensor | 1,120.94 | 79.6% | link_latency |
| Qwen3-8B | 103 | 85,078 | 98.4 | 718.7 | 672.3 | tensor | 1,122.26 | 80.7% | link_latency |
| Qwen3-8B | 111 | 91,686 | 98.4 | 722.0 | 678.7 | tensor | 1,122.77 | 81.1% | link_latency |
| Qwen3-8B | 112 | 92,512 | 98.4 | 722.4 | 679.4 | tensor | 1,122.77 | 81.1% | link_latency |
| Qwen3-8B | 136 | 112,336 | 98.4 | 730.0 | 659.7 | tensor | 1,123.96 | 82.1% | link_latency |
| Qwen3-8B | 168 | 138,768 | 98.4 | 736.9 | 678.3 | tensor | 1,125.02 | 82.9% | link_latency |
| Qwen3-8B | 204 | 168,504 | 98.4 | 742.1 | 669.4 | tensor | 1,125.89 | 83.6% | link_latency |
| Qwen3-8B | 224 | 185,024 | 98.4 | 744.4 | 677.2 | tensor | 1,126.14 | 83.8% | link_latency |
| Qwen3-8B | 272 | 224,672 | 98.4 | 748.4 | 673.8 | tensor | 1,126.74 | 84.3% | link_latency |
| Qwen3-8B | 335 | 276,710 | 98.4 | 614.9 | 674.8 | hybrid | 1,131.54 | 76.4% | link_latency |
| Qwen3-8B | 336 | 277,536 | 98.4 | 614.9 | 675.1 | hybrid | 1,131.54 | 76.4% | link_latency |
| Qwen3-8B | 448 | 370,048 | 98.4 | 617.5 | 684.2 | hybrid | 1,133.89 | 77.6% | link_latency |
| Qwen3-8B | 672 | 555,072 | 98.4 | 620.1 | 676.4 | hybrid | 1,143.33 | 77.3% | link_latency |

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
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x7 | Qwen3-8B | 7 | pipeline | rom_package_ucie | rom_board_serdes | 6 | 0.68 us | 147,619.1 tok/s | 1,476,190.6 tok/s | 3 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.04 us; 3 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.64 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x7 | Qwen3-8B | 7 | tensor | rom_package_ucie | rom_board_serdes | 144 | 35.69 us | 2,802.1 tok/s | 28,021.5 tok/s | 72 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 1.79 us; 72 x all_reduce span 4 on rom_board_serdes (traversals 2.2) = 33.89 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x7 | Qwen3-8B | 7 | hybrid | rom_package_ucie | rom_board_serdes | 75 | 2.44 us | 41,047.2 tok/s | 410,472.1 tok/s | 72 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 1.79 us; 3 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.64 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x7 | Qwen3-8B | 7 | pipeline | nvlink3 | infiniband_hdr | 6 | 15.16 us | 6,594.6 tok/s | 65,946.4 tok/s | 6 x point_to_point span 2 on nvlink3 (traversals 1.0) = 15.16 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x7 | Qwen3-8B | 7 | tensor | nvlink3 | infiniband_hdr | 72 | 365.06 us | 273.9 tok/s | 2,739.3 tok/s | 72 x all_reduce span 7 on nvlink3 (traversals 2.0) = 365.06 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | rom_wafer_serdes | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | Qwen3-8B | 69 | pipeline | rom_package_ucie | rom_board_serdes | 35 | 3.85 us | 25,969.6 tok/s | 259,695.8 tok/s | 18 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.22 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.64 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x69 | Qwen3-8B | 69 | tensor | rom_package_ucie | rom_board_serdes | 144 | 168.34 us | 594.0 tok/s | 5,940.3 tok/s | 72 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 1.79 us; 72 x all_reduce span 35 on rom_board_serdes (traversals 11.0) = 166.55 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69 | Qwen3-8B | 69 | hybrid | rom_package_ucie | rom_board_serdes | 106 | 9.07 us | 11,030.5 tok/s | 110,305.2 tok/s | 72 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 1.79 us; 34 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 7.27 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x69 | Qwen3-8B | 69 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8 | Qwen3-8B | 8 | pipeline | on_wafer | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x69 | Qwen3-8B | 69 | tensor | nvlink3 | infiniband_hdr | 144 | 720.40 us | 138.8 tok/s | 1,388.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 355.23 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x8 | Qwen3-8B | 8 | tensor | on_wafer | rom_wafer_serdes | 144 | 205.08 us | 487.6 tok/s | 4,876.0 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us; 72 x all_reduce span 8 on rom_wafer_serdes (traversals 4.4) = 66.48 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-hybrid-x69 | Qwen3-8B | 69 | hybrid | nvlink3 | infiniband_hdr | 80 | 384.02 us | 260.4 tok/s | 2,604.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8 | Qwen3-8B | 8 | hybrid | on_wafer | rom_wafer_serdes | 79 | 140.07 us | 713.9 tok/s | 7,139.1 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us; 7 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 1.47 us |
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
| Qwen3-8B/a100_sxm_80gb-x73-pipeline | Qwen3-8B | 73 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x73-tensor | Qwen3-8B | 73 | tensor | nvlink3 | infiniband_hdr | 144 | 721.18 us | 138.7 tok/s | 1,386.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 356.02 us |
| Qwen3-8B/a100_sxm_80gb-x73-hybrid | Qwen3-8B | 73 | hybrid | nvlink3 | infiniband_hdr | 81 | 386.38 us | 258.8 tok/s | 2,588.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
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
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x80 | DeepSeek-V4-Flash-0731 | 80 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 4.74 us | 21,088.4 tok/s | 210,884.4 tok/s | 21 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.25 us; 21 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.49 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x39 | DeepSeek-V4-Flash-0731 | 39 | tensor | rom_package_ucie | rom_board_serdes | 172 | 161.51 us | 619.2 tok/s | 6,191.8 tok/s | 86 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.14 us; 86 x all_reduce span 20 on rom_board_serdes (traversals 8.8) = 159.36 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x78 | DeepSeek-V4-Flash-0731 | 78 | hybrid | rom_package_ucie | rom_board_serdes | 124 | 10.27 us | 9,737.0 tok/s | 97,369.7 tok/s | 86 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.14 us; 38 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 8.13 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x79 | DeepSeek-V4-Flash-0731 | 79 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x37 | DeepSeek-V4-Flash-0731 | 37 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x46 | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x86 | DeepSeek-V4-Flash-0731 | 86 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 4.74 us | 21,088.4 tok/s | 210,884.4 tok/s | 21 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.25 us; 21 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.49 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x79 | DeepSeek-V4-Flash-0731 | 79 | tensor | rom_package_ucie | rom_board_serdes | 172 | 240.62 us | 415.6 tok/s | 4,155.9 tok/s | 86 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.14 us; 86 x all_reduce span 40 on rom_board_serdes (traversals 13.2) = 238.48 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x84 | DeepSeek-V4-Flash-0731 | 84 | hybrid | rom_package_ucie | rom_board_serdes | 127 | 10.91 us | 9,164.5 tok/s | 91,644.7 tok/s | 86 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.14 us; 41 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 8.77 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x85 | DeepSeek-V4-Flash-0731 | 85 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10 | DeepSeek-V4-Flash-0731 | 10 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x79 | DeepSeek-V4-Flash-0731 | 79 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x10 | DeepSeek-V4-Flash-0731 | 10 | tensor | on_wafer | rom_wafer_serdes | 172 | 284.51 us | 351.5 tok/s | 3,514.8 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 86 x all_reduce span 10 on rom_wafer_serdes (traversals 6.6) = 118.96 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x79 | DeepSeek-V4-Flash-0731 | 79 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | DeepSeek-V4-Flash-0731 | 10 | hybrid | on_wafer | rom_wafer_serdes | 95 | 167.44 us | 597.2 tok/s | 5,972.1 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 9 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 1.89 us |
| DSV4-Flash/a100_sxm_80gb-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 45.15 us | 2,214.7 tok/s | 22,147.3 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 40.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x19-expert | DeepSeek-V4-Flash-0731 | 19 | expert | nvlink3 | infiniband_hdr | 172 | 616.56 us | 162.2 tok/s | 1,621.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.48 us |
| DSV4-Flash/a100_sxm_80gb-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink3 | infiniband_hdr | 21 | 52.73 us | 1,896.3 tok/s | 18,963.0 tok/s | 19 x point_to_point span 2 on nvlink3 (traversals 1.0) = 48.02 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink3 | infiniband_hdr | 172 | 615.35 us | 162.5 tok/s | 1,625.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 182.27 us |
| DSV4-Flash/a100_sxm_80gb-x37-pipeline | DeepSeek-V4-Flash-0731 | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-tensor | DeepSeek-V4-Flash-0731 | 37 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x37-hybrid | DeepSeek-V4-Flash-0731 | 37 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-expert | DeepSeek-V4-Flash-0731 | 37 | expert | nvlink3 | infiniband_hdr | 172 | 610.69 us | 163.7 tok/s | 1,637.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.15 us |
| DSV4-Flash/a100_sxm_80gb-x38-pipeline | DeepSeek-V4-Flash-0731 | 38 | pipeline | nvlink3 | infiniband_hdr | 37 | 92.83 us | 1,077.2 tok/s | 10,772.2 tok/s | 33 x point_to_point span 2 on nvlink3 (traversals 1.0) = 83.40 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x38-tensor | DeepSeek-V4-Flash-0731 | 38 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x38-hybrid | DeepSeek-V4-Flash-0731 | 38 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x38-expert | DeepSeek-V4-Flash-0731 | 38 | expert | nvlink3 | infiniband_hdr | 172 | 610.57 us | 163.8 tok/s | 1,637.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.03 us |
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
| DSV4-Flash/a100_sxm_80gb-x59-pipeline | DeepSeek-V4-Flash-0731 | 59 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x59-tensor | DeepSeek-V4-Flash-0731 | 59 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x59-hybrid | DeepSeek-V4-Flash-0731 | 59 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x59-expert | DeepSeek-V4-Flash-0731 | 59 | expert | nvlink3 | infiniband_hdr | 172 | 608.33 us | 164.4 tok/s | 1,643.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.45 us |
| DSV4-Flash/a100_sxm_80gb-x62-pipeline | DeepSeek-V4-Flash-0731 | 62 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x62-tensor | DeepSeek-V4-Flash-0731 | 62 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x62-hybrid | DeepSeek-V4-Flash-0731 | 62 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x62-expert | DeepSeek-V4-Flash-0731 | 62 | expert | nvlink3 | infiniband_hdr | 172 | 608.19 us | 164.4 tok/s | 1,644.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.31 us |
| DSV4-Flash/a100_sxm_80gb-x69-pipeline | DeepSeek-V4-Flash-0731 | 69 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x69-tensor | DeepSeek-V4-Flash-0731 | 69 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x69-hybrid | DeepSeek-V4-Flash-0731 | 69 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x69-expert | DeepSeek-V4-Flash-0731 | 69 | expert | nvlink3 | infiniband_hdr | 172 | 607.80 us | 164.5 tok/s | 1,645.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.03 us |
| DSV4-Flash/a100_sxm_80gb-x77-pipeline | DeepSeek-V4-Flash-0731 | 77 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x77-tensor | DeepSeek-V4-Flash-0731 | 77 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x77-hybrid | DeepSeek-V4-Flash-0731 | 77 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x77-expert | DeepSeek-V4-Flash-0731 | 77 | expert | nvlink3 | infiniband_hdr | 172 | 607.46 us | 164.6 tok/s | 1,646.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.78 us |
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
| DSV4-Flash/a100_sxm_80gb-x83-pipeline | DeepSeek-V4-Flash-0731 | 83 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x83-tensor | DeepSeek-V4-Flash-0731 | 83 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x83-hybrid | DeepSeek-V4-Flash-0731 | 83 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x83-expert | DeepSeek-V4-Flash-0731 | 83 | expert | nvlink3 | infiniband_hdr | 172 | 607.23 us | 164.7 tok/s | 1,646.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.62 us |
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
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x389 | DeepSeek-V4-Pro-0813 | 389 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 6.93 us | 14,435.6 tok/s | 144,355.6 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.40 us; 30 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.52 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x196 | DeepSeek-V4-Pro-0813 | 196 | tensor | rom_package_ucie | rom_board_serdes | 244 | 511.25 us | 195.6 tok/s | 1,956.0 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 122 x all_reduce span 98 on rom_board_serdes (traversals 19.8) = 507.94 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x357 | DeepSeek-V4-Pro-0813 | 357 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 16.36 us | 6,113.0 tok/s | 61,130.2 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 13.05 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x388 | DeepSeek-V4-Pro-0813 | 388 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x9 | DeepSeek-V4-Pro-0813 | 9 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.59 us | 13,181.2 tok/s | 131,812.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x190 | DeepSeek-V4-Pro-0813 | 190 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | rom_wafer_serdes | 244 | 291.64 us | 342.9 tok/s | 3,428.9 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 56.79 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x272 | DeepSeek-V4-Pro-0813 | 272 | hybrid | nvlink3 | infiniband_hdr | 155 | 711.22 us | 140.6 tok/s | 1,406.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.91 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x7 | DeepSeek-V4-Pro-0813 | 7 | hybrid | on_wafer | rom_wafer_serdes | 128 | 236.12 us | 423.5 tok/s | 4,235.1 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 6 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 1.27 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | DeepSeek-V4-Pro-0813 | 66 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.59 us | 13,181.2 tok/s | 131,812.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x66 | DeepSeek-V4-Pro-0813 | 66 | tensor | on_wafer | rom_wafer_serdes | 244 | 684.53 us | 146.1 tok/s | 1,460.9 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 66 on rom_wafer_serdes (traversals 17.6) = 449.68 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | DeepSeek-V4-Pro-0813 | 66 | hybrid | on_wafer | rom_wafer_serdes | 182 | 247.54 us | 404.0 tok/s | 4,039.7 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 60 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 12.69 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,300.52 us | 76.9 tok/s | 768.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 675.22 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 640.92 us | 156.0 tok/s | 1,560.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink3 | infiniband_hdr | 244 | 867.34 us | 115.3 tok/s | 1,152.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 612.19 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 255.16 us |
| DSV4-Pro/a100_sxm_80gb-x100-pipeline | DeepSeek-V4-Pro-0813 | 100 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x100-tensor | DeepSeek-V4-Pro-0813 | 100 | tensor | nvlink3 | infiniband_hdr | 244 | 1,314.36 us | 76.1 tok/s | 760.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 689.05 us |
| DSV4-Pro/a100_sxm_80gb-x100-hybrid | DeepSeek-V4-Pro-0813 | 100 | hybrid | nvlink3 | infiniband_hdr | 134 | 656.54 us | 152.3 tok/s | 1,523.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.24 us |
| DSV4-Pro/a100_sxm_80gb-x100-expert | DeepSeek-V4-Pro-0813 | 100 | expert | nvlink3 | infiniband_hdr | 244 | 863.13 us | 115.9 tok/s | 1,158.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.28 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.86 us |
| DSV4-Pro/a100_sxm_80gb-x101-pipeline | DeepSeek-V4-Pro-0813 | 101 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x101-tensor | DeepSeek-V4-Pro-0813 | 101 | tensor | nvlink3 | infiniband_hdr | 244 | 1,314.36 us | 76.1 tok/s | 760.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 689.05 us |
| DSV4-Pro/a100_sxm_80gb-x101-hybrid | DeepSeek-V4-Pro-0813 | 101 | hybrid | nvlink3 | infiniband_hdr | 134 | 656.54 us | 152.3 tok/s | 1,523.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.24 us |
| DSV4-Pro/a100_sxm_80gb-x101-expert | DeepSeek-V4-Pro-0813 | 101 | expert | nvlink3 | infiniband_hdr | 244 | 863.09 us | 115.9 tok/s | 1,158.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.28 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.82 us |
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
| DSV4-Pro/a100_sxm_80gb-x193-pipeline | DeepSeek-V4-Pro-0813 | 193 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x193-tensor | DeepSeek-V4-Pro-0813 | 193 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.11 us | 75.6 tok/s | 756.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 696.80 us |
| DSV4-Pro/a100_sxm_80gb-x193-hybrid | DeepSeek-V4-Pro-0813 | 193 | hybrid | nvlink3 | infiniband_hdr | 146 | 687.79 us | 145.4 tok/s | 1,453.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.48 us |
| DSV4-Pro/a100_sxm_80gb-x193-expert | DeepSeek-V4-Pro-0813 | 193 | expert | nvlink3 | infiniband_hdr | 244 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.64 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.83 us |
| DSV4-Pro/a100_sxm_80gb-x203-pipeline | DeepSeek-V4-Pro-0813 | 203 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x203-tensor | DeepSeek-V4-Pro-0813 | 203 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x203-hybrid | DeepSeek-V4-Pro-0813 | 203 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x203-expert | DeepSeek-V4-Pro-0813 | 203 | expert | nvlink3 | infiniband_hdr | 244 | 860.34 us | 116.2 tok/s | 1,162.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.61 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.73 us |
| DSV4-Pro/a100_sxm_80gb-x207-pipeline | DeepSeek-V4-Pro-0813 | 207 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x207-tensor | DeepSeek-V4-Pro-0813 | 207 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x207-hybrid | DeepSeek-V4-Pro-0813 | 207 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x207-expert | DeepSeek-V4-Pro-0813 | 207 | expert | nvlink3 | infiniband_hdr | 244 | 860.30 us | 116.2 tok/s | 1,162.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.61 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.69 us |
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
| DSV4-Pro/a100_sxm_80gb-x315-pipeline | DeepSeek-V4-Pro-0813 | 315 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x315-tensor | DeepSeek-V4-Pro-0813 | 315 | tensor | nvlink3 | infiniband_hdr | 244 | 1,325.26 us | 75.5 tok/s | 754.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 40 on infiniband_hdr (traversals 2.0) = 699.95 us |
| DSV4-Pro/a100_sxm_80gb-x315-hybrid | DeepSeek-V4-Pro-0813 | 315 | hybrid | nvlink3 | infiniband_hdr | 161 | 726.84 us | 137.6 tok/s | 1,375.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 101.53 us |
| DSV4-Pro/a100_sxm_80gb-x315-expert | DeepSeek-V4-Pro-0813 | 315 | expert | nvlink3 | infiniband_hdr | 244 | 859.38 us | 116.4 tok/s | 1,163.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.39 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.99 us |
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
| DSV4-Pro/a100_sxm_80gb-x352-pipeline | DeepSeek-V4-Pro-0813 | 352 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x352-tensor | DeepSeek-V4-Pro-0813 | 352 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.05 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 44 on infiniband_hdr (traversals 4.0) = 1,195.75 us |
| DSV4-Pro/a100_sxm_80gb-x352-hybrid | DeepSeek-V4-Pro-0813 | 352 | hybrid | nvlink3 | infiniband_hdr | 165 | 737.25 us | 135.6 tok/s | 1,356.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 43 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 111.95 us |
| DSV4-Pro/a100_sxm_80gb-x352-expert | DeepSeek-V4-Pro-0813 | 352 | expert | nvlink3 | infiniband_hdr | 244 | 859.20 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.35 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.85 us |
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
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 9,289.5 | 0.201 | 7,587.6 (5,705) | 9,289.5 (46,225) | 1.22x | layer_fixed_latency |
| Qwen3-8B | 2 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 5,371.7 | 0.096 | 5,371.7 (56,235) | 5,433.8 (369,800) | 1.01x | link_latency |
| Qwen3-8B | 4 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 5,371.7 | 0.096 | 5,371.7 (56,235) | 5,433.8 (369,800) | 1.01x | link_latency |
| Qwen3-8B | 8 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x113-romfill | 92,095 | 5,384.8 | 0.058 | 5,384.8 (92,095) | 5,433.8 (369,800) | 1.01x | link_latency |
| Qwen3-8B | 16 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 5,429.1 | 0.024 | 5,429.1 (224,940) | 4,497.8 (554,700) | 0.83x | link_latency |
| Qwen3-8B | 32 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 5,053.2 | 0.022 | 5,053.2 (224,940) | 3,069.3 (554,700) | 0.61x | kv_read |
| Qwen3-8B | 64 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,991.7 | 0.014 | 3,991.7 (277,100) | 1,851.7 (554,700) | 0.46x | kv_read |
| Qwen3-8B | 256 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 1,578.5 | 0.006 | 1,578.5 (277,100) | 531.6 (554,700) | 0.34x | kv_read |
| Qwen3-8B | 1024 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 430.3 | 0.002 | 430.3 (277,100) | 136.7 (554,700) | 0.32x | kv_read |
| Qwen3-8B | 4096 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 110.7 | 0.000 | 110.7 (277,100) | 34.4 (554,700) | 0.31x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | wafer | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 3,938.3 | 0.043 | 3,006.8 (57,050) | 3,938.3 (92,450) | 1.31x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,217.9 | 0.007 | 2,940.6 (64,385) | 3,217.9 (462,250) | 1.09x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,217.9 | 0.007 | 2,940.6 (64,385) | 3,217.9 (462,250) | 1.09x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,217.9 | 0.007 | 2,940.6 (64,385) | 3,217.9 (462,250) | 1.09x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | 462,250 | 3,217.9 | 0.007 | 2,940.6 (64,385) | 3,217.9 (462,250) | 1.09x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 2,940.6 | 0.046 | 2,940.6 (64,385) | 3,094.0 (462,250) | 1.05x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x99 | 80,685 | 2,755.8 | 0.034 | 2,755.8 (80,685) | 2,644.6 (462,250) | 0.96x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill | 257,540 | 2,146.7 | 0.008 | 2,146.7 (257,540) | 1,462.6 (554,700) | 0.68x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 1024 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 877.4 | 0.003 | 877.4 (277,100) | 480.3 (554,700) | 0.55x | compute |
| DeepSeek-V4-Flash-0731 | 4096 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316 | 257,540 | 296.6 | 0.001 | 296.6 (257,540) | 128.2 (554,700) | 0.43x | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x6 | 277,350 | 1,899.8 | 0.007 | 1,026.1 (259,985) | 1,899.8 (277,350) | 1.85x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 0.000 | — (—) | 1,480.8 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 0.000 | — (—) | 1,480.8 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 0.000 | — (—) | 1,480.8 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 0.000 | — (—) | 1,480.8 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 0.000 | — (—) | 1,480.8 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,480.8 | 0.000 | — (—) | 1,480.8 (3,050,850) | — | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 986.7 | 0.000 | — (—) | 986.7 (3,050,850) | — | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 361.1 | 0.000 | — (—) | 361.1 (3,050,850) | — | kv_read |
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
| Qwen3-8B | 1 | sram | 28,190.9 | 28,157.7 | 28,157.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 28,190.9 | 28,157.7 | 28,157.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 28,190.9 | 28,157.7 | 28,157.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 31,333.1 | 28,157.7 | 28,157.7 | 1.11x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 54,760.4 | 28,157.7 | 28,157.7 | 1.94x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 84,811.6 | 28,157.7 | 28,157.7 | 3.01x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 124,126.4 | 28,248.1 | 28,248.1 | 4.39x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 272,418.6 | 26,023.7 | 26,023.7 | 10.47x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1024 | sram | 418,204.3 | 26,072.9 | 26,072.9 | 16.04x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 4096 | sram | 453,464.8 | 26,102.4 | 26,102.4 | 17.37x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 418,906.1 | 92,905.0 | 92,905.0 | 4.51x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 418,906.1 | 92,905.0 | 92,905.0 | 4.51x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 418,906.1 | 92,905.0 | 92,905.0 | 4.51x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 418,906.1 | 92,905.0 | 92,905.0 | 4.51x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 418,906.1 | 92,905.0 | 92,905.0 | 4.51x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 418,906.1 | 92,905.0 | 92,905.0 | 4.51x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 418,906.1 | 92,905.0 | 92,905.0 | 4.51x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 418,906.1 | 93,860.6 | 93,860.6 | 4.46x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1024 | rom | 440,653.3 | 95,426.5 | 95,426.5 | 4.62x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4096 | rom | 448,836.6 | 95,825.9 | 95,825.9 | 4.68x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 359,336.6 | 26,113.2 | 26,113.2 | 13.76x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 359,336.6 | 26,113.2 | 26,113.2 | 13.76x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 359,336.6 | 26,113.2 | 26,113.2 | 13.76x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 359,336.6 | 26,113.2 | 26,113.2 | 13.76x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 359,336.6 | 26,113.2 | 26,240.3 | 13.76x | 1.00x | weight_read | weight_read | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 359,336.6 | 26,113.2 | 41,148.1 | 13.76x | 1.58x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 359,336.6 | 26,113.2 | 66,596.8 | 13.76x | 2.55x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 434,264.3 | 26,113.2 | 151,525.2 | 16.63x | 5.80x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 796,537.3 | 26,113.2 | 268,445.0 | 30.50x | 10.28x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 1,215,047.5 | 26,113.2 | 395,141.3 | 46.53x | 15.13x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 697,736.1 | 397,302.5 | 397,302.5 | 1.76x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 697,736.1 | 397,302.5 | 397,302.5 | 1.76x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 697,736.1 | 397,302.5 | 397,302.5 | 1.76x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 697,736.1 | 397,302.5 | 397,302.5 | 1.76x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 697,736.1 | 397,302.5 | 397,302.5 | 1.76x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 697,736.1 | 397,302.5 | 397,302.5 | 1.76x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 697,736.1 | 397,302.5 | 397,302.5 | 1.76x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 697,736.1 | 397,302.5 | 397,302.5 | 1.76x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 898,498.6 | 417,754.9 | 416,536.5 | 2.15x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 1,004,262.2 | 438,866.5 | 436,017.2 | 2.29x | 0.99x | compute | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 409,868.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 409,868.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 409,868.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 409,868.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 409,868.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 409,868.7 | 26,113.2 | 26,113.2 | 15.70x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 409,868.7 | 26,113.2 | 37,488.7 | 15.70x | 1.44x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 409,868.7 | 26,113.2 | 83,918.3 | 15.70x | 3.21x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 409,868.7 | 26,113.2 | 175,291.4 | 15.70x | 6.71x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 410,881.9 | 26,113.2 | 317,340.7 | 15.73x | 12.15x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 406,116.6 | 408,451.2 | 408,451.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 406,116.6 | 408,451.2 | 408,451.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 406,116.6 | 408,451.2 | 408,451.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 406,116.6 | 408,451.2 | 408,451.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 406,116.6 | 408,451.2 | 408,451.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 406,116.6 | 408,451.2 | 408,451.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 406,116.6 | 408,451.2 | 408,451.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 406,116.6 | 408,451.2 | 408,451.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 406,116.6 | 408,451.2 | 408,451.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 407,228.1 | 409,611.9 | 409,433.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,190.9 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 418,906.1 | 1.512 | kv_read | 14.86x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 3.30x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 3.30x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,190.9 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 418,906.1 | 1.512 | kv_read | 14.86x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 3.30x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 3.30x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,190.9 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 418,906.1 | 1.512 | kv_read | 14.86x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 3.30x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 1.00x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 3.30x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 31,333.1 | 0.085 | link_latency | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 418,906.1 | 1.512 | kv_read | 13.37x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 0.90x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 2.97x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 0.90x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 2.97x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 54,760.4 | 0.099 | link_latency | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 418,906.1 | 1.512 | kv_read | 7.65x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 0.51x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 1.70x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 0.51x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 1.70x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 84,811.6 | 0.153 | kv_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 418,906.1 | 1.512 | kv_read | 4.94x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 0.33x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 1.10x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,157.7 | 0.609 | weight_read | 0.33x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 1.10x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x207 | 168,705 | 1.00 | 1.00 | 124,126.4 | 0.736 | weight_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 418,906.1 | 1.512 | kv_read | 3.37x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,248.1 | 0.611 | weight_read | 0.23x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 0.75x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 28,248.1 | 0.611 | weight_read | 0.23x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion-romfill | 369,800 | 259.66 | 1.00 | 92,905.0 | 0.251 | kv_read | 0.75x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276 | 224,940 | 1.00 | 1.00 | 272,418.6 | 1.211 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 418,906.1 | 1.512 | kv_read | 1.54x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream | 369,800 | 1.00 | 1.00 | 26,023.7 | 0.070 | weight_read | 0.10x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 38.85 | 3.46 | 93,860.6 | 1.556 | kv_read | 0.34x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion | 369,800 | 1.00 | 1.00 | 26,023.7 | 0.070 | weight_read | 0.10x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x74-perregion-romfill | 60,310 | 38.85 | 3.46 | 93,860.6 | 1.556 | kv_read | 0.34x |
| Qwen3-8B | 1024 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 418,204.3 | 1.509 | kv_read | 1.00x |
| Qwen3-8B | 1024 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 440,653.3 | 1.590 | kv_read | 1.05x |
| Qwen3-8B | 1024 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream | 369,800 | 1.00 | 2.26 | 26,072.9 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 1024 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 38.85 | 13.84 | 95,426.5 | 1.582 | kv_read | 0.23x |
| Qwen3-8B | 1024 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion | 369,800 | 1.00 | 2.26 | 26,072.9 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 1024 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x74-perregion-romfill | 60,310 | 38.85 | 13.84 | 95,426.5 | 1.582 | kv_read | 0.23x |
| Qwen3-8B | 4096 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 453,464.8 | 1.636 | kv_read | 1.00x |
| Qwen3-8B | 4096 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 448,836.6 | 1.620 | kv_read | 0.99x |
| Qwen3-8B | 4096 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream | 369,800 | 1.00 | 9.02 | 26,102.4 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 4096 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 38.85 | 55.35 | 95,825.9 | 1.589 | kv_read | 0.21x |
| Qwen3-8B | 4096 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion | 369,800 | 1.00 | 9.02 | 26,102.4 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 4096 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x74-perregion-romfill | 60,310 | 38.85 | 55.35 | 95,825.9 | 1.589 | kv_read | 0.21x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,336.6 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 697,736.1 | 2.518 | compute | 1.94x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,336.6 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 697,736.1 | 2.518 | compute | 1.94x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,336.6 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 697,736.1 | 2.518 | compute | 1.94x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,336.6 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 697,736.1 | 2.518 | compute | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,336.6 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 697,736.1 | 2.518 | compute | 1.94x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.88 | 26,240.3 | 0.568 | layer_fixed_latency | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,336.6 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 697,736.1 | 2.518 | compute | 1.94x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 1.97 | 41,148.1 | 0.089 | weight_read | 0.11x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 359,336.6 | 0.648 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 697,736.1 | 2.518 | compute | 1.94x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 2.57 | 66,596.8 | 0.144 | weight_read | 0.19x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 1.00 | 1.00 | 434,264.3 | 3.372 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 697,736.1 | 2.518 | compute | 1.61x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 0.91x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 3.59 | 151,525.2 | 0.328 | weight_read | 0.35x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 397,302.5 | 0.859 | kv_read | 0.91x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x237 | 193,155 | 1.00 | 1.00 | 796,537.3 | 4.124 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 898,498.6 | 3.243 | compute | 1.13x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79-perstream | 64,385 | 1.00 | 12.96 | 26,113.2 | 0.406 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.80 | 417,754.9 | 0.904 | kv_read | 0.52x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 7.67 | 268,445.0 | 0.581 | weight_read | 0.34x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.10 | 416,536.5 | 0.901 | kv_read | 0.52x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316 | 257,540 | 1.00 | 1.00 | 1,215,047.5 | 4.718 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,004,262.2 | 3.624 | compute | 0.83x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79-perstream | 64,385 | 1.00 | 51.85 | 26,113.2 | 0.406 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 7.21 | 438,866.5 | 0.949 | kv_read | 0.36x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 12.78 | 395,141.3 | 0.855 | kv_read | 0.33x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 2.06 | 436,017.2 | 0.943 | kv_read | 0.36x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,868.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,116.6 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,868.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,116.6 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,868.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,116.6 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,868.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,116.6 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,868.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,116.6 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,868.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,116.6 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,868.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,116.6 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66-perregion | 3,050,850 | 1.00 | 1.39 | 37,488.7 | 0.012 | weight_read | 0.09x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,868.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,116.6 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66-perregion | 3,050,850 | 1.00 | 2.47 | 83,918.3 | 0.028 | weight_read | 0.20x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 409,868.7 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 406,116.6 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66-perregion | 3,050,850 | 1.00 | 3.44 | 175,291.4 | 0.057 | weight_read | 0.43x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 408,451.2 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 410,881.9 | 0.135 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 407,228.1 | 0.133 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.09 | 26,113.2 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.09 | 409,611.9 | 0.134 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66-perregion | 3,050,850 | 1.00 | 4.84 | 317,340.7 | 0.104 | weight_read | 0.77x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.01 | 409,433.1 | 0.134 | kv_read | 1.00x |

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
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 9.33 | 5.36 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 14.51 | 7.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 19.19 | 8.83 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 21.49 | 10.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 21.96 | 12.14 | 1.81x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 22.00 | 13.24 | 1.66x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 37 | 10.26 | 6.23 | 1.65x |
| DeepSeek-V4-Flash-0731 | 4 | 37 | 17.39 | 8.55 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 37 | 25.99 | 11.20 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 37 | 32.96 | 14.00 | 2.35x |
| DeepSeek-V4-Flash-0731 | 32 | 37 | 36.11 | 16.57 | 2.18x |
| DeepSeek-V4-Flash-0731 | 64 | 37 | 36.85 | 18.50 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 37 | 36.97 | 19.73 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1024 | 37 | 36.97 | 19.74 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 38 | 10.30 | 6.28 | 1.64x |
| DeepSeek-V4-Flash-0731 | 4 | 38 | 17.51 | 8.63 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 38 | 26.32 | 11.33 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 38 | 33.60 | 14.18 | 2.37x |
| DeepSeek-V4-Flash-0731 | 32 | 38 | 36.99 | 16.83 | 2.20x |
| DeepSeek-V4-Flash-0731 | 64 | 38 | 37.82 | 18.81 | 2.01x |
| DeepSeek-V4-Flash-0731 | 256 | 38 | 37.96 | 20.07 | 1.89x |
| DeepSeek-V4-Flash-0731 | 1024 | 38 | 37.96 | 20.08 | 1.89x |
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
| DeepSeek-V4-Flash-0731 | 1 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 59 | 10.83 | 7.05 | 1.53x |
| DeepSeek-V4-Flash-0731 | 4 | 59 | 19.30 | 9.90 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 59 | 31.31 | 13.45 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 59 | 44.18 | 17.43 | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | 59 | 53.24 | 21.27 | 2.50x |
| DeepSeek-V4-Flash-0731 | 64 | 59 | 57.06 | 24.27 | 2.35x |
| DeepSeek-V4-Flash-0731 | 256 | 59 | 58.25 | 26.23 | 2.22x |
| DeepSeek-V4-Flash-0731 | 1024 | 59 | 58.26 | 26.25 | 2.22x |
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
| DeepSeek-V4-Flash-0731 | 1 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 77 | 11.06 | 7.55 | 1.46x |
| DeepSeek-V4-Flash-0731 | 4 | 77 | 20.12 | 10.63 | 1.89x |
| DeepSeek-V4-Flash-0731 | 8 | 77 | 33.82 | 14.80 | 2.29x |
| DeepSeek-V4-Flash-0731 | 16 | 77 | 50.24 | 19.52 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 77 | 64.01 | 24.22 | 2.64x |
| DeepSeek-V4-Flash-0731 | 64 | 77 | 71.35 | 27.98 | 2.55x |
| DeepSeek-V4-Flash-0731 | 256 | 77 | 74.27 | 30.48 | 2.44x |
| DeepSeek-V4-Flash-0731 | 1024 | 77 | 74.29 | 30.51 | 2.44x |
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
| DeepSeek-V4-Flash-0731 | 1 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 83 | 11.11 | 7.69 | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | 83 | 20.32 | 10.82 | 1.88x |
| DeepSeek-V4-Flash-0731 | 8 | 83 | 34.45 | 15.19 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 83 | 51.84 | 20.13 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 83 | 67.06 | 25.08 | 2.67x |
| DeepSeek-V4-Flash-0731 | 64 | 83 | 75.64 | 29.08 | 2.60x |
| DeepSeek-V4-Flash-0731 | 256 | 83 | 79.25 | 31.75 | 2.50x |
| DeepSeek-V4-Flash-0731 | 1024 | 83 | 79.27 | 31.77 | 2.50x |
| DeepSeek-V4-Flash-0731 | 4096 | 83 | 79.27 | 31.77 | 2.50x |
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
| DeepSeek-V4-Pro-0813 | 1 | 101 | 5.85 | 5.29 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 101 | 11.28 | 8.08 | 1.40x |
| DeepSeek-V4-Pro-0813 | 4 | 101 | 21.01 | 11.42 | 1.84x |
| DeepSeek-V4-Pro-0813 | 8 | 101 | 36.75 | 16.45 | 2.23x |
| DeepSeek-V4-Pro-0813 | 16 | 101 | 57.88 | 22.32 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 101 | 78.74 | 28.70 | 2.74x |
| DeepSeek-V4-Pro-0813 | 64 | 101 | 92.08 | 34.59 | 2.66x |
| DeepSeek-V4-Pro-0813 | 256 | 101 | 98.63 | 40.39 | 2.44x |
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
| DeepSeek-V4-Pro-0813 | 1 | 193 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 193 | 11.58 | 9.28 | 1.25x |
| DeepSeek-V4-Pro-0813 | 4 | 193 | 22.13 | 13.28 | 1.67x |
| DeepSeek-V4-Pro-0813 | 8 | 193 | 40.59 | 19.83 | 2.05x |
| DeepSeek-V4-Pro-0813 | 16 | 193 | 69.24 | 27.89 | 2.48x |
| DeepSeek-V4-Pro-0813 | 32 | 193 | 105.38 | 37.51 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 193 | 138.62 | 46.82 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 193 | 165.80 | 56.49 | 2.93x |
| DeepSeek-V4-Pro-0813 | 1024 | 193 | 166.74 | 56.91 | 2.93x |
| DeepSeek-V4-Pro-0813 | 1 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 203 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 203 | 22.19 | 13.44 | 1.65x |
| DeepSeek-V4-Pro-0813 | 8 | 203 | 40.82 | 20.06 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 203 | 69.94 | 28.35 | 2.47x |
| DeepSeek-V4-Pro-0813 | 32 | 203 | 107.17 | 38.24 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 203 | 142.11 | 47.84 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 203 | 171.48 | 57.86 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1024 | 203 | 172.53 | 58.30 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 207 | 11.60 | 9.40 | 1.23x |
| DeepSeek-V4-Pro-0813 | 4 | 207 | 22.22 | 13.50 | 1.65x |
| DeepSeek-V4-Pro-0813 | 8 | 207 | 40.90 | 20.15 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 207 | 70.20 | 28.53 | 2.46x |
| DeepSeek-V4-Pro-0813 | 32 | 207 | 107.85 | 38.53 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 207 | 143.45 | 48.25 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 207 | 173.68 | 58.40 | 2.97x |
| DeepSeek-V4-Pro-0813 | 1024 | 207 | 174.76 | 58.84 | 2.97x |
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
| DeepSeek-V4-Pro-0813 | 1 | 315 | 5.95 | 5.75 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 315 | 11.70 | 10.05 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 315 | 22.63 | 14.95 | 1.51x |
| DeepSeek-V4-Pro-0813 | 8 | 315 | 42.39 | 21.89 | 1.94x |
| DeepSeek-V4-Pro-0813 | 16 | 315 | 75.01 | 32.62 | 2.30x |
| DeepSeek-V4-Pro-0813 | 32 | 315 | 120.73 | 44.64 | 2.70x |
| DeepSeek-V4-Pro-0813 | 64 | 315 | 169.93 | 56.93 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 315 | 220.06 | 70.38 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1024 | 315 | 222.09 | 70.97 | 3.13x |
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
| DeepSeek-V4-Pro-0813 | 1 | 352 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 352 | 11.72 | 10.20 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 352 | 22.71 | 15.35 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 352 | 42.70 | 22.33 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 352 | 76.03 | 33.74 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 352 | 123.58 | 46.15 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 352 | 176.10 | 59.31 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 352 | 231.63 | 73.72 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 352 | 233.94 | 74.34 | 3.15x |
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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 403.02 | 16.2% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 572.70 | 9.8% |
| gpu | Qwen3-8B | 1 | 173.05 | 13.0% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 187.91 | 74.0% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 368.65 | 72.8% |
| rom | Qwen3-8B | 1 | 67.42 | 62.6% |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.0 | 27,462.9 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.0 | 27,462.9 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.0 | 27,462.9 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.0 | 27,462.9 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.0 | 27,462.9 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.0 | 27,462.9 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 398.0 | 27,462.9 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 355.5 | 91,014.4 |
| Qwen3-8B | 1024 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 90.3 | 92,509.5 |
| Qwen3-8B | 4096 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 22.7 | 92,891.9 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,221.6 | 175,506.0 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,221.6 | 175,506.0 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,221.6 | 175,506.0 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,221.6 | 175,506.0 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,221.6 | 175,506.0 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,221.6 | 175,506.0 |
| DeepSeek-V4-Flash-0731 | 64 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,221.6 | 175,506.0 |
| DeepSeek-V4-Flash-0731 | 256 | 7.40% | 18.7 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 916.6 | 234,642.3 |
| DeepSeek-V4-Flash-0731 | 1024 | 26.47% | 46.7 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 257.5 | 263,642.5 |
| DeepSeek-V4-Flash-0731 | 4096 | 70.76% | 111.9 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 66.1 | 270,678.5 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,868.7 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,868.7 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,868.7 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,868.7 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,868.7 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,868.7 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,868.7 |
| DeepSeek-V4-Pro-0813 | 256 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,868.7 |
| DeepSeek-V4-Pro-0813 | 1024 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 109.5 | 409,868.7 |
| DeepSeek-V4-Pro-0813 | 4096 | 1.71% | 40.9 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 100.3 | 410,881.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 233 |
| gpu | kv_read | 101 |
| gpu | link_latency | 1729 |
| gpu | weight_read | 1127 |
| rom | compute | 472 |
| rom | infeasible | 6699 |
| rom | kv_read | 811 |
| rom | layer_fixed_latency | 507 |
| rom | link_latency | 2024 |
| rom | weight_read | 897 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 233 |
| rom | CAPACITY | 6699 |

## Mechanical consistency audit

**FAIL** over 254,693 checks.

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

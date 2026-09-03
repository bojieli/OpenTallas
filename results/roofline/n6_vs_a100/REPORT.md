# Area-constrained roofline: n6_vs_a100

> Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 527x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 1 device. On the GPU side the correction reaches 597x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 168 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 6 x 815 mm2 (4,890 mm2, array, KV in SRAM) at 3,110 tok/s per user and 636 tok/s per 1,000 mm2, holding 1 session, against 6 copies of one unified HBM die at the same silicon: 6.3x per user. DeepSeek-V4-Flash-0731 takes 1 x 46,225 mm2 (46,225 mm2, wafer, KV in HBM) at 4,708 tok/s per user and 102 tok/s per 1,000 mm2, holding 448 sessions, against 56 copies of one unified HBM die at the same silicon: 6.5x per user. DeepSeek-V4-Pro-0813 takes 4 x 46,225 mm2 (184,900 mm2, wafer, KV in SRAM) at 2,376 tok/s per user and 13 tok/s per 1,000 mm2, holding 1 session, against 224 copies of one unified HBM die at the same silicon: 6.6x per user. Two granularities come out of one rule, which is the point: the class is chosen per model on evidence rather than assumed. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 184,900 mm2 of ROM silicon at 2,376 tok/s per user against 185,024 mm2 of a100_sxm_80gb-x224-tensor at 358 tok/s: **6.6x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 1,545. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 284.08x to it.** At 554,700 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 1.10 tok/s and the same silicon running tensor delivers 314 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.11x (Qwen3-8B, ROM binding on `link_latency`) to 35.09x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 17.1% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 516 to 21,651 tok/s, and its rate with every slot occupied from 20,633 to 21,651. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 40 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,823 us over NVLink, capping per-user decode at 548 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 2,702.8 us and cap it at 370 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 2.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 21 of 24 operating points and an array 3; on tokens per second per square millimetre the same points go 13 to the array and 11 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 606 of 4668 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 31.5x of aggregate throughput (Qwen3-8B). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 4.75x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 2.79x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 44 of 48 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

**Recommended: `ROM-N6-native-SRAMKV-array-pipeline-x6`** -- 6 x 815 mm2 reticle dies, 4,890 mm2 total, `pipeline`-parallel, KV in SRAM, spare silicon to `sram`.

- **3,110.4 tok/s per user** (0.32 ms/token), binding on `compute`
- **636.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,110 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 417 W at 0.085 W/mm2, 134.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 6 copies of one unified HBM die -- `a100_sxm_80gb-x6-tensor`, 4,956 mm2, area ratio 0.9867 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 4,890 | 4,956 | 0.9867 |
| user tok/s | 3,110.4 | 494.8 | 6.29x |
| aggregate tok/s | 3,110 | 495 | 6.29x |
| resident sessions | 1 | 344 | -- |
| J/token | 0.1340 | 3.4739 | 25.9x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 344 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x224-tensor` at 185,024 mm2 and 1,287.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 | 5.83x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 | 5.83x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-tensor-x5` | 4,075 | 2,126.2 | 521.8 | 1 | 5.00x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-pipeline-x6` | 4,890 | 3,110.4 | 636.1 | 1 | 6.29x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-pipeline-x6` | 4,890 | 3,110.4 | 636.1 | -- | 636.1 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-pipeline-x7-romfill` | 5,705 | 3,517.9 | 616.6 | 500.0 | 636.1 | stop |
| `ROM-N6-native-SRAMKV-array-pipeline-x8-romfill` | 6,520 | 3,524.3 | 540.5 | 253.9 | 636.1 | stop |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 81.1 | 636.1 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-pipeline-x6` **<-- recommended** | 4,890 | 6 | 3,110.4 | 3,110 | 636.1 | 1 | `compute` | 417 | 134.0 | `a100_sxm_80gb-x6-tensor` | 6.29x |
| `ROM-N6-native-SRAMKV-array-pipeline-x7-romfill` | 5,705 | 7 | 3,517.9 | 3,518 | 616.6 | 1 | `weight_read` | 534 | 151.8 | `a100_sxm_80gb-x7-tensor` | 6.28x |
| `ROM-N6-native-SRAMKV-array-pipeline-x8-romfill` | 6,520 | 8 | 3,524.3 | 3,524 | 540.5 | 1 | `weight_read` | 607 | 172.3 | `a100_sxm_80gb-x8-tensor` | 5.67x |
| `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 1 | 6,464.4 | 6,464 | 139.8 | 1 | `link_latency` | 4,209 | 651.2 | `a100_sxm_80gb-x56-tensor` | 5.83x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 118 | densest | `ROM-N6-native-SRAMKV-array-pipeline-x6` | 4,890 | 3,110.4 | 636.1 | 1 |
| array | 118 | fastest | `ROM-N6-native-SRAMKV-array-pipeline-x8-romfill` | 6,520 | 3,524.3 | 540.5 | 1 |
| array | 118 | smallest | `ROM-N6-native-SRAMKV-array-tensor-x5` | 4,075 | 2,126.2 | 521.8 | 1 |
| wafer | 80 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 80 | fastest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 80 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-pipeline-x8-romfill` | 6,520 | 3,524.3 | 3,524 | 1 | 607 | 172.3 | `weight_read` | `a100_sxm_80gb-x8-tensor` | 621.5 | 463 | 3,581.6 | 0.987 | 5.67x | 20.8x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 6,464 | 1 | 4,209 | 651.2 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 1,109.0 | 3,324 | 9,013.6 | 0.999 | 5.83x | 13.8x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hybrid-x57-romfill` | 46,455 | 2,123.5 | 2,123 | 1 | 4,173 | 1,965.3 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 1,109.0 | 3,324 | 9,013.6 | 1.004 | 1.91x | 4.6x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | -- | 1 | -- | 651.2 | -- | -- | -- | -- | -- | 1.005 | 3.04x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hybrid-x15` | 12,225 | 2,119.2 | 4,238 | 894 | 2,280 | 537.9 | `link_latency` | `a100_sxm_80gb-x15-tensor` | 690.2 | 880 | 2,496.3 | 0.987 | 3.07x | 4.6x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,245.8 | 8,492 | 1,025 | 14,525 | 1,710.5 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 1,116.3 | 6,662 | 8,170.5 | 0.999 | 3.80x | 4.8x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x113-romfill` | 92,095 | 1,991.7 | 29,875 | 6,735 | 14,312 | 479.0 | `link_latency` | `a100_sxm_80gb-x111-tensor` | 1,115.3 | 6,602 | 8,112.7 | 1.004 | 1.79x | 16.9x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,245.8 | -- | 1,025 | -- | 1,710.5 | -- | -- | -- | -- | -- | 0.996 | 2.13x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hybrid-x57-romfill` | 46,455 | 2,036.0 | 16,288 | 3,397 | 7,386 | 453.4 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 878.5 | 3,324 | 2,830.8 | 1.004 | 2.32x | 6.2x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,071.0 | 16,284 | 2,050 | 19,418 | 1,192.5 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 993.3 | 13,337 | 8,669.9 | 0.999 | 4.10x | 7.3x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,881.7 | 54,568 | 13,530 | 28,005 | 513.2 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 993.3 | 13,337 | 8,669.9 | 1.000 | 1.89x | 16.9x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,071.0 | -- | 2,050 | -- | 1,192.5 | -- | -- | -- | -- | -- | 1.001 | 2.16x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hybrid-x57-romfill` | 46,455 | 2,036.0 | 16,288 | 3,397 | 7,386 | 453.4 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 687.8 | 3,324 | 1,800.3 | 1.004 | 2.96x | 4.0x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,761.4 | 30,091 | 4,100 | 38,498 | 1,279.4 | `link_latency` | `a100_sxm_80gb-x448-tensor` | 632.0 | 26,689 | 13,125.3 | 0.999 | 5.95x | 10.3x |
| 16 | array | `ROM-N6-native-HBMKV-array-hybrid-x113-romfill` | 92,095 | 1,963.8 | 31,421 | 6,735 | 14,514 | 461.9 | `link_latency` | `a100_sxm_80gb-x111-hybrid` | 600.5 | 6,602 | 3,192.3 | 1.004 | 3.27x | 6.9x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,178.4 | 50,854 | 6,151 | 58,469 | 1,149.7 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 591.2 | 40,040 | 3,676.9 | 0.999 | 5.38x | 3.2x |
| 32 | array | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,843.0 | 58,976 | 13,530 | 28,582 | 484.6 | `link_latency` | `a100_sxm_80gb-x224-hybrid` | 592.5 | 13,337 | 3,229.9 | 1.000 | 3.11x | 6.7x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,331.9 | 74,620 | 6,151 | 61,558 | 824.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 591.2 | 40,040 | 3,676.9 | 0.999 | 3.94x | 4.5x |
| 64 | array | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 277,100 | 1,665.8 | 106,611 | 20,265 | 45,182 | 423.8 | `link_latency` | `a100_sxm_80gb-x335-hybrid` | 570.8 | 19,953 | 2,500.2 | 1.001 | 2.92x | 5.9x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,521.5 | 97,375 | 6,151 | 64,515 | 662.5 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 591.2 | 40,040 | 3,676.9 | 0.999 | 2.57x | 5.5x |
| 256 | array | `ROM-N6-native-HBMKV-array-pipeline-x340-romfill` | 277,100 | 1,210.5 | 411,584 | 20,265 | 87,028 | 211.4 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 445.0 | 19,953 | 817.6 | 1.001 | 2.72x | 3.9x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 493.2 | 126,247 | 6,151 | 98,284 | 778.5 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 522.8 | 40,040 | 1,379.0 | 0.999 | 0.94x | 1.8x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-pipeline-x6` | 4,890 | array | SRAM | 1 |
| 2 | `ROM-N6-native-HBMKV-array-tensor-x5` | 4,075 | array | HBM | 298 |
| 4-256 | `ROM-N6-native-HBMKV-array-pipeline-x5` | 4,075 | array | HBM | 298 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Flash-0731 at 200,000 tokens

**Recommended: `ROM-N6-native-HBMKV-wafer-tensor-x1`** -- 1 x 46,225 mm2 wafer, 46,225 mm2 total, `tensor`-parallel, KV in HBM, spare silicon to `sram`.

- **4,707.9 tok/s per user** (0.21 ms/token), binding on `link_latency`
- **101.8 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,708 tok/s aggregate with every slot full, over 448 resident sessions (fill limited by `batch`)
- 4,134 W at 0.089 W/mm2, 878.1 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 56 copies of one unified HBM die -- `a100_sxm_80gb-x56-tensor`, 46,256 mm2, area ratio 0.9993 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 46,225 | 46,256 | 0.9993 |
| user tok/s | 4,707.9 | 721.7 | 6.52x |
| aggregate tok/s | 4,708 | 722 | 6.52x |
| resident sessions | 448 | 2,797 | -- |
| J/token | 0.8781 | 12.4186 | 14.1x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 448 sessions against one that holds 2,797 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x224-tensor` at 185,024 mm2 and 786.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 | 6.52x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 | 6.52x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hybrid-x38` | 30,970 | 1,506.3 | 48.6 | 1 | 2.20x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 448 | 6.52x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-wafer-tensor-x1` **<-- recommended** | 46,225 | 1 | 4,707.9 | 4,708 | 101.8 | 448 | `link_latency` | 4,134 | 878.1 | `a100_sxm_80gb-x56-tensor` | 6.52x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 144 | densest | `ROM-N6-native-SRAMKV-array-hybrid-x38` | 30,970 | 1,506.3 | 48.6 | 1 |
| array | 144 | fastest | `ROM-N6-native-SRAMKV-array-hybrid-x39` | 31,785 | 1,539.7 | 48.4 | 1 |
| array | 144 | smallest | `ROM-N6-native-SRAMKV-array-hybrid-x38` | 30,970 | 1,506.3 | 48.6 | 1 |
| wafer | 80 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 |
| wafer | 80 | fastest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 |
| wafer | 80 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hybrid-x39` | 31,785 | 1,539.7 | 1,540 | 1 | 1,960 | 1,272.8 | `link_latency` | `a100_sxm_80gb-x38-tensor` | 687.9 | 1,859 | 9,190.7 | 1.013 | 2.24x | 7.2x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 4,708 | 1 | 3,802 | 807.6 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 721.7 | 2,797 | 12,418.6 | 0.999 | 6.52x | 15.4x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x56` | 45,640 | 1,368.4 | 9,579 | 2,918 | 4,902 | 511.8 | `link_latency` | `a100_sxm_80gb-x55-tensor` | 720.2 | 2,745 | 12,241.3 | 1.005 | 1.90x | 23.9x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | -- | 1 | -- | 807.6 | -- | -- | -- | -- | -- | 0.987 | 3.44x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hybrid-x40` | 32,600 | 1,456.6 | 7,283 | 2,084 | 2,698 | 370.5 | `link_latency` | `a100_sxm_80gb-x39-tensor` | 580.5 | 1,911 | 5,652.6 | 1.012 | 2.51x | 15.3x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,583.4 | 9,167 | 448 | 4,296 | 468.7 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 612.4 | 2,797 | 7,403.9 | 0.999 | 7.48x | 15.8x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x56` | 45,640 | 1,368.4 | 9,579 | 2,918 | 4,902 | 511.8 | `link_latency` | `a100_sxm_80gb-x55-tensor` | 610.8 | 2,745 | 7,303.7 | 1.005 | 2.24x | 14.3x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,583.4 | -- | 448 | -- | 468.7 | -- | -- | -- | -- | -- | 0.987 | 3.35x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hybrid-x40` | 32,600 | 1,456.6 | 7,283 | 2,084 | 2,698 | 370.5 | `link_latency` | `a100_sxm_80gb-x39-tensor` | 464.4 | 1,911 | 3,621.6 | 1.012 | 3.14x | 9.8x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,390.6 | 17,562 | 896 | 9,258 | 527.1 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 533.8 | 5,715 | 8,163.7 | 0.999 | 8.23x | 15.5x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 90,465 | 1,231.2 | 17,237 | 5,784 | 10,717 | 621.8 | `link_latency` | `a100_sxm_80gb-x110-tensor` | 532.7 | 5,611 | 8,043.5 | 0.996 | 2.31x | 12.9x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,390.6 | -- | 896 | -- | 527.1 | -- | -- | -- | -- | -- | 0.979 | 3.57x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hybrid-x47` | 38,305 | 1,443.6 | 11,549 | 2,449 | 3,782 | 327.5 | `link_latency` | `a100_sxm_80gb-x46-tensor` | 357.4 | 2,276 | 2,795.4 | 1.008 | 4.04x | 8.5x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,202.1 | 33,616 | 1,792 | 18,458 | 549.1 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 437.5 | 11,552 | 9,713.1 | 0.999 | 9.60x | 17.7x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,173.9 | 34,043 | 11,829 | 21,871 | 642.4 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 437.5 | 11,552 | 9,713.1 | 1.000 | 2.68x | 15.1x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,202.1 | -- | 1,792 | -- | 549.1 | -- | -- | -- | -- | -- | 1.001 | 3.58x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hybrid-x47` | 38,305 | 1,422.2 | 22,756 | 2,449 | 4,190 | 184.1 | `link_latency` | `a100_sxm_80gb-x46-tensor` | 250.3 | 2,276 | 2,050.8 | 1.008 | 5.68x | 11.1x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,869.7 | 61,916 | 3,585 | 36,717 | 593.0 | `link_latency` | `a100_sxm_80gb-x448-tensor` | 294.6 | 23,225 | 14,115.5 | 0.999 | 13.14x | 23.8x |
| 32 | array | `ROM-N6-native-HBMKV-array-hybrid-x56` | 45,640 | 1,316.1 | 42,116 | 2,918 | 6,086 | 144.5 | `link_latency` | `a100_sxm_80gb-x55-tensor` | 172.0 | 2,745 | 1,761.5 | 1.005 | 7.65x | 12.2x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,399.6 | 108,786 | 5,377 | 55,641 | 511.5 | `link_latency` | `a100_sxm_80gb-x672-tensor` | 203.0 | 34,898 | 15,256.6 | 0.999 | 16.75x | 29.8x |
| 64 | array | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 90,465 | 1,177.3 | 75,345 | 5,784 | 12,831 | 170.3 | `link_latency` | `a100_sxm_80gb-x110-tensor` | 118.4 | 5,611 | 2,334.2 | 0.996 | 9.95x | 13.7x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,814.0 | 180,095 | 5,377 | 58,217 | 323.3 | `link_latency` | `a100_sxm_80gb-x672-tensor` | 125.4 | 34,898 | 12,328.0 | 0.999 | 22.44x | 38.1x |
| 256 | array | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,028.9 | 263,394 | 11,829 | 30,199 | 114.7 | `link_latency` | `a100_sxm_80gb-x224-hybrid` | 42.0 | 11,552 | 3,459.8 | 1.000 | 24.47x | 30.2x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,383.8 | 354,255 | 5,377 | 91,883 | 259.4 | `kv_read` | `a100_sxm_80gb-x672-tensor` | 39.4 | 34,898 | 9,709.9 | 0.999 | 35.09x | 37.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-16 | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | wafer | HBM | 448 |
| 32 | `ROM-N6-native-HBMKV-array-hybrid-x56` | 45,640 | array | HBM | 2,918 |
| 64 | `ROM-N6-native-HBMKV-array-hybrid-x57` | 46,455 | array | HBM | 2,970 |
| 256 | `ROM-N6-native-HBMKV-array-hybrid-x74` | 60,310 | array | HBM | 3,856 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Pro-0813 at 1,000,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-wafer-hybrid-x4`** -- 4 x 46,225 mm2 wafers, 184,900 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **2,375.7 tok/s per user** (0.42 ms/token), binding on `link_latency`
- **12.8 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 2,376 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 11,102 W at 0.060 W/mm2, 4,672.9 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 224 copies of one unified HBM die -- `a100_sxm_80gb-x224-tensor`, 185,024 mm2, area ratio 0.9993 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 184,900 | 185,024 | 0.9993 |
| user tok/s | 2,375.7 | 357.7 | 6.64x |
| aggregate tok/s | 2,376 | 358 | 6.64x |
| resident sessions | 1 | 1,545 | -- |
| J/token | 4.6729 | 94.8324 | 20.3x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,545 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x293-tensor` at 242,018 mm2 and 362.3 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 | 6.64x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 | 6.64x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-tensor-x199` | 162,185 | 711.5 | 4.4 | 1 | 2.00x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 | 6.64x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x4` **<-- recommended** | 184,900 | 4 | 2,375.7 | 2,376 | 12.8 | 1 | `link_latency` | 11,102 | 4,672.9 | `a100_sxm_80gb-x224-tensor` | 6.64x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 84 | densest | `ROM-N6-native-SRAMKV-array-tensor-x199` | 162,185 | 711.5 | 4.4 | 1 |
| array | 84 | fastest | `ROM-N6-native-SRAMKV-array-tensor-x207` | 168,705 | 725.5 | 4.3 | 1 |
| array | 84 | smallest | `ROM-N6-native-SRAMKV-array-tensor-x199` | 162,185 | 711.5 | 4.4 | 1 |
| wafer | 48 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 |
| wafer | 48 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 |
| wafer | 48 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-tensor-x207` | 168,705 | 725.5 | 726 | 1 | 10,372 | 14,295.9 | `link_latency` | `a100_sxm_80gb-x204-tensor` | 355.8 | 1,399 | 87,200.5 | 1.001 | 2.04x | 6.1x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 2,376 | 1 | 11,102 | 4,672.9 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 357.7 | 1,545 | 94,832.4 | 0.999 | 6.64x | 20.3x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-tensor-x227` | 185,005 | 725.1 | 725 | 1 | 11,372 | 15,683.7 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 357.7 | 1,545 | 94,832.4 | 1.000 | 2.03x | 6.0x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | -- | 1 | -- | 4,672.9 | -- | -- | -- | -- | -- | 1.001 | 3.28x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-tensor-x248` | 202,120 | 625.8 | 1,252 | 1,811 | 17,731 | 14,167.2 | `link_latency` | `a100_sxm_80gb-x245-tensor` | 309.3 | 1,699 | 60,171.6 | 0.999 | 2.02x | 4.2x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 2,153.7 | 10,769 | 314 | 21,508 | 1,997.3 | `link_latency` | `a100_sxm_80gb-x280-tensor` | 313.3 | 1,954 | 67,506.1 | 0.999 | 6.87x | 33.8x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-tensor-x297` | 242,055 | 624.8 | 1,250 | 2,169 | 24,207 | 19,372.0 | `link_latency` | `a100_sxm_80gb-x293-tensor` | 314.6 | 2,049 | 70,229.1 | 1.000 | 1.99x | 3.6x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 2,153.7 | -- | 314 | -- | 1,997.3 | -- | -- | -- | -- | -- | 1.047 | 3.45x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hybrid-x218` | 177,670 | 554.6 | 15,529 | 1,592 | 17,425 | 1,122.1 | `compute` | `a100_sxm_80gb-x215-tensor` | 231.3 | 1,480 | 35,822.4 | 1.000 | 2.40x | 31.9x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 2,153.7 | 10,769 | 314 | 21,508 | 1,997.3 | `link_latency` | `a100_sxm_80gb-x280-tensor` | 239.9 | 1,954 | 44,402.7 | 0.999 | 8.98x | 22.2x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-tensor-x297` | 242,055 | 490.2 | 1,961 | 2,169 | 24,382 | 12,433.8 | `link_latency` | `a100_sxm_80gb-x293-tensor` | 241.3 | 2,049 | 46,093.7 | 1.000 | 2.03x | 3.7x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 2,153.7 | -- | 314 | -- | 1,997.3 | -- | -- | -- | -- | -- | 1.047 | 4.39x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hybrid-x218` | 177,670 | 554.6 | 15,529 | 1,592 | 17,425 | 1,122.1 | `compute` | `a100_sxm_80gb-x215-tensor` | 169.9 | 1,480 | 24,722.9 | 1.000 | 3.27x | 22.0x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 1,969.0 | 15,752 | 376 | 29,574 | 1,877.4 | `link_latency` | `a100_sxm_80gb-x336-tensor` | 163.4 | 2,363 | 38,991.7 | 0.999 | 12.05x | 20.8x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x340` | 277,100 | 416.9 | 17,925 | 2,483 | 34,164 | 1,906.0 | `weight_read` | `a100_sxm_80gb-x335-tensor` | 163.3 | 2,356 | 38,891.4 | 1.001 | 2.55x | 20.4x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 1,969.0 | -- | 376 | -- | 1,877.4 | -- | -- | -- | -- | -- | 0.999 | 4.72x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hybrid-x218` | 177,670 | 554.6 | 15,529 | 1,592 | 17,425 | 1,122.1 | `compute` | `a100_sxm_80gb-x215-tensor` | 116.1 | 1,480 | 18,342.3 | 1.000 | 4.78x | 16.3x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,845.4 | 29,527 | 753 | 59,075 | 2,000.7 | `link_latency` | `a100_sxm_80gb-x672-tensor` | 124.0 | 4,818 | 50,547.4 | 0.999 | 14.89x | 25.3x |
| 32 | array | `ROM-N6-native-HBMKV-array-hybrid-x227` | 185,005 | 546.6 | 17,490 | 1,658 | 19,103 | 1,092.2 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 75.1 | 1,545 | 14,862.1 | 1.000 | 7.28x | 13.6x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,379.9 | 44,155 | 753 | 62,649 | 1,418.8 | `kv_read` | `a100_sxm_80gb-x672-tensor` | 80.9 | 4,818 | 38,872.2 | 0.999 | 17.05x | 27.4x |
| 64 | array | `ROM-N6-native-HBMKV-array-hybrid-x248` | 202,120 | 514.7 | 32,943 | 1,811 | 25,706 | 780.3 | `weight_read` | `a100_sxm_80gb-x245-tensor` | 46.2 | 1,699 | 13,102.0 | 0.999 | 11.13x | 16.8x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 875.7 | 56,043 | 753 | 80,472 | 1,435.9 | `kv_read` | `a100_sxm_80gb-x672-tensor` | 49.2 | 4,818 | 31,940.3 | 0.999 | 17.79x | 22.2x |
| 256 | array | `ROM-N6-native-HBMKV-array-hybrid-x340` | 277,100 | 385.5 | 98,688 | 2,483 | 54,140 | 548.6 | `weight_read` | `a100_sxm_80gb-x335-tensor` | 15.2 | 2,356 | 13,026.8 | 1.001 | 25.38x | 23.7x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 274.3 | 70,223 | 753 | 83,891 | 1,194.6 | `kv_read` | `a100_sxm_80gb-x672-tensor` | 15.5 | 4,818 | 24,987.2 | 0.999 | 17.66x | 20.9x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | wafer | SRAM | 1 |
| 2-32 | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | wafer | HBM | 314 |
| 64 | `ROM-N6-native-HBMKV-array-hybrid-x248` | 202,120 | array | HBM | 1,811 |
| 256 | `ROM-N6-native-HBMKV-array-hybrid-x297` | 242,055 | array | HBM | 2,169 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 40, 41, 47, 56, 57, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 40, 41, 47, 56, 57, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 38, 39, 44, 53, 57, 70, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 38, 39, 44, 53, 57, 70, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Pro-0813 | HBM | rom | 210, 218, 227, 248, 297, 340, 396 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 210, 218, 227, 248, 297, 340, 396 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 199, 207, 227, 237, 284, 340, 378 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 199, 207, 227, 237, 284, 340, 378 |
| Qwen3-8B | HBM | rom | 5, 7, 8, 10, 15, 20, 57, 113, 170, 227, 340 |
| Qwen3-8B | HBM | sram | 5, 7, 8, 10, 15, 20, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | rom | 5, 6, 7, 8, 12, 16, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 5, 6, 7, 8, 12, 16, 57, 113, 170, 227, 340 |

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 0.0 tok/s | 0.00x | within 2x | FAIL |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 87.6 W | 0.35x | within 2x | FAIL |

HC1 binds on `capacity_or_format`. Its component times are weight_read 61.42 us, kv_read 9.28 us, compute 61.42 us, link_latency 0.00 us, layer_fixed_latency 6.06 us.

**THE ANCHOR IS INFEASIBLE, AND THAT IS THE RESULT.** The model does not
under-predict the shipping part here -- it cannot place it. Taalas ships
this die; this model says the die cannot hold its own weights. At least one
of the constants below is therefore wrong, and the gate exists to say so
rather than to be closed:

- AREA: the array needs 770.5 mm2 to hold 3,513,239,296 B but only 432.4 mm2 of 815 mm2 is left after SRAM, HBM PHY, overhead and interconnect

The candidates, in the order they should be attacked: `rom.cell_to_sram_cell_area_ratio` and `rom.array_efficiency`, whose
product is now set by one sentence in one paper about a foundry memory
compiler and which together cut ROM capacity density by 2.243x;
`rom.cim_precompute_area_fraction`, taken from a different fabricated part
with a different architecture; `rom.cim_cell_area_multiplier`, for which no
published compute-in-ROM cell exists at any node; and
`reference_parts.taalas_hc1.weight_bits_per_parameter`, whose 3.0-6.0 sweep
the vendor's own 3-bit base type sits at the bottom of. **Nothing here is
tuned to make this gate pass.** The back-derivation below is still printed,
because what each input would have to be is exactly the question a failing
gate asks:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 1.764e+11 | 1.837e+11 | 1.04x |
| Compute density (ops/s/mm2) | 1.261e+12 | 3.155e+12 | 2.50x |

The gate fails before either rate density can bind: the corrected
ROM capacity density and compute-in-ROM floorplan cannot fit the
published model in 815 mm2. The rate diagnostics remain useful --
ROM read density is 1.04x and
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
| range low | 70.0 ns/layer | 2.24 us | 0.0 | 0.00x | capacity_or_format |
| range stated | 189.4 ns/layer | 6.06 us | 0.0 | 0.00x | capacity_or_format |
| range high | 894.8 ns/layer | 28.63 us | 0.0 | 0.00x | capacity_or_format |

The per-layer cost that would land the model exactly on the
published figure is **-76.7 ns/layer**. It is negative, which means no positive latency term could close the gate. The current result is decided earlier by the reported capacity failure.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 0.0 | 0.00x | capacity_or_format |
| 3.5 | 0.0 | 0.00x | capacity_or_format |
| 4.0 | 0.0 | 0.00x | capacity_or_format |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 0.0 | 0.00x | capacity_or_format |
| 1,536 | 0.0 | 0.00x | capacity_or_format |
| 2,048 | 0.0 | 0.00x | capacity_or_format |

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
| Taalas HC1 card power | 200.0-250.0 W | 87.6 W | 0.35x | FAIL |

**Where the watts come from.**

| Term | A100 at TDP | Taalas HC1 |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 3.9 W |
| KV traffic | n/a: one saturating HBM stream | 10.3 W |
| operand delivery | 0.5 W | 12.1 W |
| arithmetic | 103.0 W | 8.7 W |
| static: leakage | 31.4 W | 20.9 W |
| static: clock distribution | 99.0 W | 31.6 W |
| static: memory-interface idle | 14.0 W | 0.0 W |
| **static charged** (max of the enumeration and the measured clocked-idle floor) | 144.4 W | 52.5 W |
| **total** | 461.7 W | 87.6 W |

On HC1 the enumerated static power is 52.5 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 63.3 W | 0.25x | 0.32x |
| stated | 461.7 W | 1.15x | 87.6 W | 0.35x | 0.44x |
| high | 698.3 W | 1.75x | 374.6 W | 1.50x | 1.87x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.35x of the top of its published band, **2.86x low**, against 2.28x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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
| Taalas HC1 (modelled reconstruction) | n/a (0.005908 J/attempt) | 87.6 | 0.0 |
| A100 80GB, weight-bound gate, same model and batch | 1.465768 J/token | 359.6 | 245.3 |

No tokens-per-joule ratio is admissible for this pair: the HC1 throughput reconstruction is capacity-infeasible and delivers zero modelled tokens. Its energy cell above is the attempted-step energy inside the diagnostic power calculation, not the energy of a feasible machine. The power gate remains useful as a disclosed component check, and it is 2.3-2.9x below the shipping card's published band, but it cannot support an efficiency advantage.

**Where the remaining HC1 shortfall could live, none of it fitted.**
The ROM array is charged its stated leakage density: 2.9 W at the point
and 11.2 W at the
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

- **0 of 4,668 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 336 | 0 | 54.6% | 80.7% | 0.391 | 66% |
| gpu | small array (1,600-5,000 mm2) | 32 | 0 | 79.5% | 80.8% | 0.392 | 45% |
| gpu | wafer (>=40,000 mm2) | 1,200 | 0 | 39.8% | 79.6% | 0.385 | 91% |
| rom | large array (5,000-40,000 mm2) | 462 | 0 | 37.3% | 73.1% | 0.365 | 64% |
| rom | small array (1,600-5,000 mm2) | 40 | 0 | 59.9% | 63.4% | 0.317 | 32% |
| rom | wafer (>=40,000 mm2) | 2,598 | 0 | 22.7% | 74.5% | 0.373 | 92% |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | `DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1` | 0.807647 | 3,802.3 | link_latency | `DSV4-Flash/a100_sxm_80gb-x56-tensor` | 12.418646 | 8,962.5 | link_latency | 15.38x |
| DeepSeek-V4-Flash-0731 | 2 | 46,225 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1` | 0.468673 | 4,296.2 | link_latency | `DSV4-Flash/a100_sxm_80gb-x56-tensor` | 7.403878 | 9,068.7 | link_latency | 15.80x |
| DeepSeek-V4-Flash-0731 | 4 | 92,450 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 0.527129 | 9,257.6 | link_latency | `DSV4-Flash/a100_sxm_80gb-x112-tensor` | 8.163677 | 17,431.3 | link_latency | 15.49x |
| DeepSeek-V4-Flash-0731 | 8 | 138,675 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 0.436824 | 14,099.9 | link_latency | `DSV4-Flash/a100_sxm_80gb-x168-tensor` | 7.563290 | 25,872.3 | link_latency | 17.31x |
| DeepSeek-V4-Flash-0731 | 16 | 277,350 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 0.461705 | 28,058.5 | link_latency | `DSV4-Flash/a100_sxm_80gb-x336-tensor` | 10.868727 | 50,330.4 | link_latency | 23.54x |
| DeepSeek-V4-Flash-0731 | 32 | 369,800 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 0.363568 | 38,284.4 | link_latency | `DSV4-Flash/a100_sxm_80gb-x448-tensor` | 10.503182 | 66,708.4 | link_latency | 28.89x |
| DeepSeek-V4-Flash-0731 | 64 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.323254 | 58,216.5 | link_latency | `DSV4-Flash/a100_sxm_80gb-x672-tensor` | 12.327959 | 98,932.9 | link_latency | 38.14x |
| DeepSeek-V4-Flash-0731 | 256 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.259370 | 91,883.3 | kv_read | `DSV4-Flash/a100_sxm_80gb-x672-tensor` | 9.709918 | 98,031.6 | link_latency | 37.44x |
| DeepSeek-V4-Pro-0813 | 1 | 184,900 | `DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 4.672931 | 11,101.6 | link_latency | `DSV4-Pro/a100_sxm_80gb-x224-tensor` | 94.832402 | 33,921.8 | link_latency | 20.29x |
| DeepSeek-V4-Pro-0813 | 2 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5` | 1.997277 | 21,507.8 | link_latency | `DSV4-Pro/a100_sxm_80gb-x280-tensor` | 67.506086 | 42,305.3 | link_latency | 33.80x |
| DeepSeek-V4-Pro-0813 | 4 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5` | 1.997277 | 21,507.8 | link_latency | `DSV4-Pro/a100_sxm_80gb-x280-tensor` | 44.402712 | 42,606.4 | link_latency | 22.23x |
| DeepSeek-V4-Pro-0813 | 8 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5` | 1.475759 | 22,628.2 | link_latency | `DSV4-Pro/a100_sxm_80gb-x280-tensor` | 30.800391 | 43,052.7 | link_latency | 20.87x |
| DeepSeek-V4-Pro-0813 | 16 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 2.000726 | 59,074.6 | link_latency | `DSV4-Pro/a100_sxm_80gb-x672-tensor` | 50.547422 | 100,251.4 | link_latency | 25.26x |
| DeepSeek-V4-Pro-0813 | 32 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.418838 | 62,649.2 | kv_read | `DSV4-Pro/a100_sxm_80gb-x672-tensor` | 38.872247 | 100,662.2 | link_latency | 27.40x |
| DeepSeek-V4-Pro-0813 | 64 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1.435897 | 80,472.4 | kv_read | `DSV4-Pro/a100_sxm_80gb-x672-tensor` | 31.940284 | 100,645.1 | link_latency | 22.24x |
| DeepSeek-V4-Pro-0813 | 256 | 277,100 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x340` | 0.548601 | 54,140.1 | weight_read | `DSV4-Pro/a100_sxm_80gb-x335-tensor` | 13.026795 | 50,662.0 | link_latency | 23.75x |
| Qwen3-8B | 1 | 46,225 | `Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 0.651181 | 4,209.5 | link_latency | `Qwen3-8B/a100_sxm_80gb-x56-tensor` | 9.013634 | 9,996.4 | link_latency | 13.84x |
| Qwen3-8B | 2 | 92,450 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.710494 | 14,524.7 | link_latency | `Qwen3-8B/a100_sxm_80gb-x112-tensor` | 8.170491 | 18,241.8 | link_latency | 4.78x |
| Qwen3-8B | 4 | 184,900 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 1.192468 | 19,418.2 | link_latency | `Qwen3-8B/a100_sxm_80gb-x224-tensor` | 8.669938 | 34,446.7 | link_latency | 7.27x |
| Qwen3-8B | 8 | 369,800 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.279370 | 38,498.0 | link_latency | `Qwen3-8B/a100_sxm_80gb-x448-tensor` | 13.125255 | 66,356.8 | link_latency | 10.26x |
| Qwen3-8B | 16 | 554,700 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.149741 | 58,468.6 | link_latency | `Qwen3-8B/a100_sxm_80gb-x672-hybrid` | 3.676882 | 182,588.0 | weight_read | 3.20x |
| Qwen3-8B | 32 | 554,700 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.824944 | 61,557.7 | kv_read | `Qwen3-8B/a100_sxm_80gb-x672-hybrid` | 3.676882 | 182,588.0 | weight_read | 4.46x |
| Qwen3-8B | 64 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 0.423804 | 45,182.3 | link_latency | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 2.500185 | 91,331.0 | weight_read | 5.90x |
| Qwen3-8B | 256 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill` | 0.211446 | 87,027.6 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.817605 | 93,138.8 | weight_read | 3.87x |

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
| Qwen3-8B | 1 | 46,225 | 48,855.6 | wafer-pipeline | 6,464.4 | wafer-tensor | 7.56x | 3,685.7 | pipeline | 1,109.0 | tensor | 3.32x | 13.26x | 5.83x | 0.44x |
| Qwen3-8B | 2 | 92,450 | 46,513.8 | wafer-pipeline | 5,845.1 | wafer-hybrid | 7.96x | 5,465.8 | pipeline | 1,221.9 | tensor | 4.47x | 8.51x | 4.78x | 0.56x |
| Qwen3-8B | 3 | 138,675 | 46,513.8 | wafer-pipeline | 5,363.6 | wafer-hybrid | 8.67x | 6,514.5 | pipeline | 1,264.8 | tensor | 5.15x | 7.14x | 4.24x | 0.59x |
| Qwen3-8B | 4 | 184,900 | 46,513.8 | wafer-pipeline | 4,955.3 | wafer-hybrid | 9.39x | 7,205.8 | pipeline | 1,287.4 | tensor | 5.60x | 6.46x | 3.85x | 0.60x |
| Qwen3-8B | 6 | 277,350 | 46,513.8 | wafer-pipeline | 4,300.6 | wafer-hybrid | 10.82x | 8,061.3 | pipeline | 947.7 | tensor | 8.51x | 5.77x | 4.54x | 0.79x |
| Qwen3-8B | 8 | 369,800 | 46,513.8 | wafer-pipeline | 3,798.8 | wafer-hybrid | 12.24x | 8,570.0 | pipeline | 954.0 | tensor | 8.98x | 5.43x | 3.98x | 0.73x |
| Qwen3-8B | 12 | 554,700 | 54,699.2 | wafer-pipeline | 3,495.6 | wafer-hybrid | 15.65x | 9,147.2 | pipeline | 960.4 | tensor | 9.52x | 5.98x | 3.64x | 0.61x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 19,190.8 | wafer-pipeline | 4,707.9 | wafer-tensor | 4.08x | 1,579.5 | pipeline | 721.7 | tensor | 2.19x | 12.15x | 6.52x | 0.54x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 25,440.9 | wafer-pipeline | 4,418.4 | wafer-hybrid | 5.76x | 1,812.0 | pipeline | 763.1 | tensor | 2.37x | 14.04x | 5.79x | 0.41x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 31,195.2 | wafer-pipeline | 4,323.5 | wafer-hybrid | 7.22x | 1,909.9 | pipeline | 778.7 | tensor | 2.45x | 16.33x | 5.55x | 0.34x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 35,159.4 | wafer-pipeline | 4,231.9 | wafer-hybrid | 8.31x | 1,963.9 | pipeline | 786.9 | tensor | 2.50x | 17.90x | 5.38x | 0.30x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 40,265.8 | wafer-pipeline | 4,059.0 | wafer-hybrid | 9.92x | 2,021.7 | pipeline | 622.5 | tensor | 3.25x | 19.92x | 6.52x | 0.33x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 43,413.7 | wafer-pipeline | 3,899.3 | wafer-hybrid | 11.13x | 2,052.3 | pipeline | 625.2 | tensor | 3.28x | 21.15x | 6.24x | 0.29x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 47,091.5 | wafer-pipeline | 3,614.6 | wafer-hybrid | 13.03x | 2,083.9 | pipeline | 627.9 | tensor | 3.32x | 22.60x | 5.76x | 0.25x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 14,625.7 | wafer-pipeline | 2,375.7 | wafer-hybrid | 6.16x | 615.1 | pipeline | 357.7 | tensor | 1.72x | 23.78x | 6.64x | 0.28x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 14,625.7 | wafer-pipeline | 1,969.6 | wafer-hybrid | 7.43x | 635.9 | pipeline | 308.6 | tensor | 2.06x | 23.00x | 6.38x | 0.28x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 16,894.7 | wafer-pipeline | 1,919.3 | wafer-hybrid | 8.80x | 647.0 | pipeline | 311.1 | tensor | 2.08x | 26.11x | 6.17x | 0.24x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 20,236.5 | wafer-pipeline | 1,849.9 | wafer-hybrid | 10.94x | 658.5 | pipeline | 313.6 | tensor | 2.10x | 30.73x | 5.90x | 0.19x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.19x to 0.79x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 6,464.4 | 6,464.4 | link_latency | Qwen3-8B/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 718.15 | 1,109.0 | 1,109.0 | link_latency | 5.83x | 5.83x | 64.59x | 5.83x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x5 | 4,075 | 2,126.2 | 2,126.2 | link_latency | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 364.72 | 425.4 | 425.4 | weight_read | 5.00x | 5.00x | 21.08x | 5.00x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,245.8 | 8,491.5 | link_latency | Qwen3-8B/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 794.09 | 1,116.3 | 2,232.6 | link_latency | 3.80x | 3.80x | 42.42x | 3.80x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x5 | 4,075 | 1,495.1 | 2,990.2 | link_latency | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 369.44 | 399.7 | 799.4 | weight_read | 3.74x | 3.74x | 14.82x | 3.74x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,071.0 | 16,284.1 | link_latency | Qwen3-8B/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 945.97 | 993.3 | 3,973.1 | link_latency | 4.10x | 4.10x | 40.67x | 4.10x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 1,336.2 | 6,680.8 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 378.87 | 356.6 | 1,426.6 | weight_read | 3.75x | 4.68x | 13.25x | 3.75x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,761.4 | 30,091.4 | link_latency | Qwen3-8B/a100_sxm_80gb-x448-tensor | 370,048 | 1.00x | tensor | 1,542.05 | 632.0 | 5,055.7 | link_latency | 5.95x | 5.95x | 37.58x | 5.95x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 842.2 | 6,737.6 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 397.75 | 293.4 | 2,347.5 | weight_read | 2.87x | 2.87x | 8.72x | 2.87x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,178.4 | 50,853.7 | link_latency | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 447.68 | 591.2 | 49,658.4 | weight_read | 5.38x | 1.02x | 31.76x | 5.74x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 424.1 | 6,785.7 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 435.50 | 216.6 | 3,466.2 | kv_read | 1.96x | 1.96x | 4.89x | 1.96x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,331.9 | 74,620.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 447.68 | 591.2 | 49,658.4 | weight_read | 3.94x | 1.50x | 23.30x | 4.21x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 212.8 | 6,810.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 510.99 | 142.2 | 4,550.4 | kv_read | 1.50x | 1.50x | 2.95x | 1.50x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 1,665.8 | 106,611.5 | link_latency | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 456.39 | 570.8 | 36,529.7 | weight_read | 2.92x | 2.92x | 16.64x | 2.94x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 106.6 | 6,822.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 661.99 | 84.3 | 5,394.1 | kv_read | 1.26x | 1.26x | 1.98x | 1.26x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 1,210.5 | 411,583.8 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 532.41 | 445.0 | 113,916.6 | weight_read | 2.72x | 3.61x | 12.09x | 2.75x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 26.7 | 6,831.4 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 1,567.96 | 24.5 | 6,265.4 | kv_read | 1.09x | 1.09x | 1.24x | 1.09x |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 4,707.9 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 857.79 | 721.7 | 721.7 | link_latency | 6.52x | 6.52x | 136.45x | 6.52x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x38 | 30,970 | 1,506.3 | 1,506.3 | link_latency | DSV4-Flash/a100_sxm_80gb-x37-tensor | 30,562 | 1.01x | tensor | 852.96 | 685.1 | 685.1 | link_latency | 2.20x | 2.20x | 33.27x | 2.20x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,583.4 | 9,166.7 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 936.42 | 612.4 | 1,224.9 | link_latency | 7.48x | 7.48x | 132.84x | 7.48x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x40 | 32,600 | 1,456.6 | 7,282.9 | link_latency | DSV4-Flash/a100_sxm_80gb-x39-tensor | 32,214 | 1.01x | tensor | 926.76 | 580.5 | 1,161.0 | link_latency | 2.51x | 6.27x | 33.25x | 2.51x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,390.6 | 17,562.3 | link_latency | DSV4-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,117.83 | 533.8 | 2,135.2 | link_latency | 8.23x | 8.23x | 214.03x | 8.23x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x40 | 32,600 | 1,456.6 | 7,282.9 | link_latency | DSV4-Flash/a100_sxm_80gb-x39-tensor | 32,214 | 1.01x | tensor | 1,074.35 | 464.4 | 1,857.6 | link_latency | 3.14x | 3.92x | 33.25x | 3.14x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,202.1 | 33,616.5 | link_latency | DSV4-Flash/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 1,480.65 | 437.5 | 3,499.9 | link_latency | 9.60x | 9.60x | 369.01x | 9.60x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x40 | 32,600 | 1,207.5 | 9,660.1 | link_latency | DSV4-Flash/a100_sxm_80gb-x39-tensor | 32,214 | 1.01x | tensor | 1,369.54 | 346.4 | 2,771.0 | link_latency | 3.49x | 3.49x | 27.57x | 3.49x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,869.7 | 61,915.8 | link_latency | DSV4-Flash/a100_sxm_80gb-x448-tensor | 370,048 | 1.00x | tensor | 2,555.46 | 294.6 | 4,713.5 | link_latency | 13.14x | 13.14x | 641.17x | 13.14x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x40 | 32,600 | 829.3 | 13,269.3 | compute | DSV4-Flash/a100_sxm_80gb-x39-tensor | 32,214 | 1.01x | tensor | 1,959.92 | 242.1 | 3,873.9 | link_latency | 3.43x | 3.43x | 18.93x | 3.43x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,399.6 | 108,786.0 | link_latency | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 3,998.70 | 203.0 | 6,495.3 | link_latency | 16.75x | 16.75x | 827.79x | 16.75x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x40 | 32,600 | 515.8 | 20,632.8 | compute | DSV4-Flash/a100_sxm_80gb-x39-tensor | 32,214 | 1.01x | tensor | 3,140.68 | 161.1 | 5,155.2 | link_latency | 3.20x | 4.00x | 11.78x | 3.20x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,814.0 | 180,095.0 | link_latency | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 6,869.09 | 125.4 | 8,025.1 | link_latency | 22.44x | 22.44x | 685.20x | 22.44x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x40 | 32,600 | 329.3 | 21,073.1 | compute | DSV4-Flash/a100_sxm_80gb-x39-tensor | 32,214 | 1.01x | tensor | 5,502.21 | 104.2 | 6,672.0 | link_latency | 3.16x | 3.16x | 9.23x | 3.16x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,383.8 | 354,255.0 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 24,091.39 | 39.4 | 10,096.0 | link_latency | 35.09x | 35.09x | 336.95x | 35.09x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x40 | 32,600 | 84.6 | 21,650.6 | compute | DSV4-Flash/a100_sxm_80gb-x39-hybrid | 32,214 | 1.01x | hybrid | 820.85 | 51.1 | 13,071.1 | weight_read | 1.66x | 1.66x | 4.50x | 1.66x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | 184,900 | 2,375.7 | 2,375.7 | link_latency | DSV4-Pro/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 1,323.01 | 357.7 | 357.7 | link_latency | 6.64x | 6.64x | 774.70x | 6.64x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x199 | 162,185 | 711.5 | 711.5 | link_latency | DSV4-Pro/a100_sxm_80gb-x196-tensor | 161,896 | 1.00x | tensor | 1,322.11 | 354.9 | 354.9 | weight_read | 2.00x | 2.00x | 206.18x | 2.00x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 2,153.7 | 10,768.6 | link_latency | DSV4-Pro/a100_sxm_80gb-x280-tensor | 231,280 | 1.00x | tensor | 1,543.69 | 313.3 | 626.7 | link_latency | 6.87x | 17.18x | 858.56x | 6.87x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x210 | 171,150 | 592.7 | 1,185.4 | link_latency | DSV4-Pro/a100_sxm_80gb-x207-tensor | 170,982 | 1.00x | tensor | 1,539.54 | 303.9 | 607.7 | weight_read | 1.95x | 1.95x | 180.22x | 1.95x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 2,153.7 | 10,768.6 | link_latency | DSV4-Pro/a100_sxm_80gb-x280-tensor | 231,280 | 1.00x | tensor | 1,982.06 | 239.9 | 959.5 | link_latency | 8.98x | 11.22x | 858.56x | 8.98x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x210 | 171,150 | 444.2 | 1,776.7 | link_latency | DSV4-Pro/a100_sxm_80gb-x207-tensor | 170,982 | 1.00x | tensor | 1,973.76 | 230.1 | 920.3 | weight_read | 1.93x | 1.93x | 135.05x | 1.93x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1,969.0 | 15,752.2 | link_latency | DSV4-Pro/a100_sxm_80gb-x336-tensor | 277,536 | 1.00x | tensor | 3,362.12 | 163.4 | 1,307.1 | link_latency | 12.05x | 12.05x | 927.69x | 12.05x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x210 | 171,150 | 406.9 | 10,987.4 | compute | DSV4-Pro/a100_sxm_80gb-x207-tensor | 170,982 | 1.00x | tensor | 2,842.20 | 169.1 | 1,352.7 | link_latency | 2.41x | 8.12x | 123.73x | 2.41x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,845.4 | 29,526.6 | link_latency | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 5,163.59 | 124.0 | 1,983.3 | link_latency | 14.89x | 14.89x | 1671.62x | 14.89x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x210 | 171,150 | 406.9 | 10,987.4 | compute | DSV4-Pro/a100_sxm_80gb-x207-tensor | 170,982 | 1.00x | tensor | 4,579.09 | 115.4 | 1,846.5 | link_latency | 3.53x | 5.95x | 123.73x | 3.53x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,379.9 | 44,155.2 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 8,726.53 | 80.9 | 2,589.6 | link_latency | 17.05x | 17.05x | 1249.90x | 17.05x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x210 | 171,150 | 358.9 | 11,484.2 | compute | DSV4-Pro/a100_sxm_80gb-x207-tensor | 170,982 | 1.00x | tensor | 8,052.85 | 74.2 | 2,375.8 | link_latency | 4.83x | 4.83x | 109.12x | 4.83x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 875.7 | 56,043.3 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 15,852.43 | 49.2 | 3,151.0 | link_latency | 17.79x | 17.79x | 793.21x | 17.79x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x210 | 171,150 | 204.4 | 13,081.3 | compute | DSV4-Pro/a100_sxm_80gb-x207-tensor | 170,982 | 1.00x | tensor | 15,000.39 | 45.3 | 2,901.0 | link_latency | 4.51x | 4.51x | 62.15x | 4.51x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x340 | 277,100 | 385.5 | 98,687.6 | weight_read | DSV4-Pro/a100_sxm_80gb-x335-tensor | 276,710 | 1.00x | tensor | 57,968.15 | 15.2 | 3,889.1 | link_latency | 25.38x | 25.38x | 181.13x | 25.38x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x210 | 171,150 | 59.8 | 15,298.0 | compute | DSV4-Pro/a100_sxm_80gb-x207-tensor | 170,982 | 1.00x | tensor | 56,685.60 | 15.0 | 3,832.0 | link_latency | 3.99x | 3.99x | 18.83x | 3.99x |

## The headline is a band, and each side's share of it is reported apart

Every hop latency in this model states a range, and the ratio moves inside it.
This table re-runs the whole study at both ends of those ranges three ways:
the **wafer fabric** alone (`on_wafer`, `inter_wafer`), which no GPU design touches; the
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
| DeepSeek-V4-Flash-0731 | 30,970 | 2.20x | 2.20x → 2.20x | 2.91x → 2.42x | 2.91x → 2.42x | 1.2x |
| DeepSeek-V4-Flash-0731 | 31,785 | 2.24x | 2.24x → 2.24x | 3.00x → 2.48x | 3.00x → 2.48x | 1.2x |
| DeepSeek-V4-Flash-0731 | 32,600 | 2.11x | 2.11x → 2.11x | 2.73x → 2.27x | 2.73x → 2.27x | 1.2x |
| DeepSeek-V4-Flash-0731 | 33,415 | 2.09x | 2.09x → 2.09x | 2.69x → 2.32x | 2.69x → 2.32x | 1.2x |
| DeepSeek-V4-Flash-0731 | 35,860 | 2.07x | 2.07x → 2.07x | 2.67x → 2.48x | 2.67x → 2.48x | 1.1x |
| DeepSeek-V4-Flash-0731 | 38,305 | 2.05x | 2.05x → 2.05x | 2.64x → 2.44x | 2.64x → 2.44x | 1.1x |
| DeepSeek-V4-Flash-0731 | 43,195 | 1.91x | 1.91x → 1.91x | 2.37x → 2.56x | 2.37x → 2.56x | 1.1x |
| DeepSeek-V4-Flash-0731 | 45,640 | 1.90x | 1.90x → 1.90x | 2.35x → 2.53x | 2.35x → 2.53x | 1.1x |
| DeepSeek-V4-Flash-0731 | 46,225 | 6.52x | 9.48x → 3.67x | 5.20x → 26.05x | 7.56x → 14.64x | 5.0x |
| DeepSeek-V4-Flash-0731 | 46,455 | 1.80x | 1.80x → 1.80x | 2.16x → 2.46x | 2.16x → 2.46x | 1.1x |
| DeepSeek-V4-Flash-0731 | 57,050 | 1.73x | 1.73x → 1.73x | 2.05x → 2.68x | 2.05x → 2.68x | 1.3x |
| DeepSeek-V4-Flash-0731 | 60,310 | 1.64x | 1.64x → 1.64x | 1.89x → 2.61x | 1.89x → 2.61x | 1.4x |
| DeepSeek-V4-Flash-0731 | 85,575 | 1.63x | 1.63x → 1.63x | 1.89x → 2.53x | 1.89x → 2.53x | 1.3x |
| DeepSeek-V4-Flash-0731 | 90,465 | 1.62x | 1.62x → 1.62x | 1.87x → 2.52x | 1.87x → 2.52x | 1.4x |
| DeepSeek-V4-Flash-0731 | 92,095 | 1.62x | 1.62x → 1.62x | 1.88x → 2.51x | 1.88x → 2.51x | 1.3x |
| DeepSeek-V4-Flash-0731 | 92,450 | 5.79x | 8.39x → 3.30x | 4.55x → 26.89x | 6.60x → 15.34x | 5.9x |
| DeepSeek-V4-Flash-0731 | 114,100 | 1.61x | 1.61x → 1.61x | 1.87x → 2.44x | 1.87x → 2.44x | 1.3x |
| DeepSeek-V4-Flash-0731 | 120,620 | 1.56x | 1.56x → 1.56x | 1.78x → 2.40x | 1.78x → 2.40x | 1.3x |
| DeepSeek-V4-Flash-0731 | 138,550 | 1.57x | 1.57x → 1.57x | 1.81x → 2.35x | 1.81x → 2.35x | 1.3x |
| DeepSeek-V4-Flash-0731 | 138,675 | 5.55x | 8.18x → 3.16x | 4.34x → 26.20x | 6.39x → 14.90x | 6.0x |
| DeepSeek-V4-Flash-0731 | 184,900 | 5.38x | 8.04x → 3.05x | 4.19x → 25.59x | 6.26x → 14.51x | 6.1x |
| DeepSeek-V4-Flash-0731 | 185,005 | 1.54x | 1.54x → 1.54x | 1.75x → 2.22x | 1.75x → 2.22x | 1.3x |
| DeepSeek-V4-Flash-0731 | 277,100 | 1.87x | 1.87x → 1.87x | 2.20x → 3.32x | 2.20x → 3.32x | 1.5x |
| DeepSeek-V4-Flash-0731 | 277,350 | 6.52x | 10.03x → 3.68x | 5.29x → 39.85x | 8.14x → 22.47x | 7.5x |
| DeepSeek-V4-Flash-0731 | 369,800 | 6.24x | 9.86x → 3.50x | 5.06x → 38.26x | 7.99x → 21.47x | 7.6x |
| DeepSeek-V4-Flash-0731 | 554,700 | 5.76x | 9.57x → 3.20x | 4.66x → 35.44x | 7.75x → 19.72x | 7.6x |
| DeepSeek-V4-Pro-0813 | 162,185 | 2.00x | 2.00x → 2.00x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 168,705 | 2.04x | 2.04x → 2.04x | 2.46x → 2.33x | 2.46x → 2.33x | 1.1x |
| DeepSeek-V4-Pro-0813 | 171,150 | 2.00x | 2.00x → 2.00x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 177,670 | 2.03x | 2.03x → 2.03x | 2.45x → 2.26x | 2.45x → 2.26x | 1.1x |
| DeepSeek-V4-Pro-0813 | 184,900 | 6.64x | 8.88x → 4.17x | 5.70x → 22.74x | 7.61x → 14.27x | 4.0x |
| DeepSeek-V4-Pro-0813 | 185,005 | 2.03x | 2.03x → 2.03x | 2.44x → 2.23x | 2.44x → 2.23x | 1.1x |
| DeepSeek-V4-Pro-0813 | 193,155 | 2.02x | 2.02x → 2.02x | 2.44x → 2.20x | 2.44x → 2.20x | 1.1x |
| DeepSeek-V4-Pro-0813 | 202,120 | 2.02x | 2.02x → 2.02x | 2.43x → 2.17x | 2.43x → 2.17x | 1.1x |
| DeepSeek-V4-Pro-0813 | 231,125 | 5.96x | 7.80x → 3.85x | 5.10x → 20.55x | 6.68x → 13.27x | 4.0x |
| DeepSeek-V4-Pro-0813 | 231,460 | 2.00x | 2.00x → 2.00x | 2.41x → 2.02x | 2.41x → 2.02x | 1.2x |
| DeepSeek-V4-Pro-0813 | 242,055 | 2.00x | 2.00x → 2.00x | 2.40x → 1.97x | 2.40x → 1.97x | 1.2x |
| DeepSeek-V4-Pro-0813 | 277,100 | 1.73x | 1.73x → 1.73x | 1.94x → 2.90x | 1.94x → 2.90x | 1.5x |
| DeepSeek-V4-Pro-0813 | 277,350 | 6.38x | 8.23x → 4.22x | 5.54x → 29.33x | 7.14x → 19.40x | 5.3x |
| DeepSeek-V4-Pro-0813 | 308,070 | 1.72x | 1.72x → 1.72x | 1.94x → 2.81x | 1.94x → 2.81x | 1.5x |
| DeepSeek-V4-Pro-0813 | 322,740 | 1.72x | 1.72x → 1.72x | 1.93x → 2.74x | 1.93x → 2.74x | 1.4x |
| DeepSeek-V4-Pro-0813 | 369,800 | 6.17x | 8.05x → 4.06x | 5.35x → 28.53x | 6.98x → 18.79x | 5.3x |
| DeepSeek-V4-Pro-0813 | 554,700 | 5.90x | 7.92x → 3.84x | 5.10x → 27.45x | 6.85x → 17.87x | 5.4x |
| Qwen3-8B | 4,075 | 5.00x | 5.00x → 5.00x | 8.39x → 6.41x | 8.39x → 6.41x | 1.3x |
| Qwen3-8B | 4,890 | 6.29x | 6.29x → 6.29x | 8.76x → 8.72x | 8.76x → 8.72x | 1.0x |
| Qwen3-8B | 5,705 | 6.28x | 6.28x → 6.28x | 8.12x → 8.79x | 8.12x → 8.79x | 1.1x |
| Qwen3-8B | 6,520 | 5.67x | 5.67x → 5.67x | 7.39x → 8.08x | 7.39x → 8.08x | 1.1x |
| Qwen3-8B | 8,150 | 3.24x | 3.24x → 3.24x | 4.78x → 4.15x | 4.78x → 4.15x | 1.2x |
| Qwen3-8B | 9,780 | 5.31x | 5.31x → 5.31x | 6.44x → 8.23x | 6.44x → 8.23x | 1.3x |
| Qwen3-8B | 12,225 | 2.88x | 2.88x → 2.88x | 4.40x → 3.17x | 4.40x → 3.17x | 1.4x |
| Qwen3-8B | 13,040 | 4.49x | 4.49x → 4.49x | 5.72x → 6.51x | 5.72x → 6.51x | 1.1x |
| Qwen3-8B | 16,300 | 2.48x | 2.48x → 2.48x | 3.60x → 3.16x | 3.60x → 3.16x | 1.1x |
| Qwen3-8B | 46,225 | 5.83x | 9.08x → 3.07x | 4.31x → 18.53x | 6.72x → 9.77x | 4.3x |
| Qwen3-8B | 46,455 | 1.91x | 1.91x → 1.91x | 2.63x → 2.86x | 2.63x → 2.86x | 1.1x |
| Qwen3-8B | 92,095 | 1.63x | 1.63x → 1.63x | 2.06x → 2.64x | 2.06x → 2.64x | 1.3x |
| Qwen3-8B | 92,450 | 4.78x | 7.33x → 2.60x | 3.41x → 17.67x | 5.23x → 9.60x | 5.2x |
| Qwen3-8B | 138,550 | 1.53x | 1.53x → 1.53x | 1.87x → 2.77x | 1.87x → 2.77x | 1.5x |
| Qwen3-8B | 138,675 | 4.24x | 6.43x → 2.36x | 2.98x → 17.05x | 4.52x → 9.49x | 5.7x |
| Qwen3-8B | 184,900 | 3.85x | 5.78x → 2.19x | 2.69x → 16.53x | 4.03x → 9.38x | 6.2x |
| Qwen3-8B | 185,005 | 1.46x | 1.46x → 1.46x | 1.74x → 2.91x | 1.74x → 2.91x | 1.7x |
| Qwen3-8B | 277,100 | 1.93x | 1.93x → 1.93x | 2.46x → 3.06x | 2.46x → 3.06x | 1.2x |
| Qwen3-8B | 277,350 | 4.54x | 6.72x → 2.66x | 3.45x → 15.11x | 5.10x → 8.87x | 4.4x |
| Qwen3-8B | 369,800 | 3.98x | 5.83x → 2.40x | 3.02x → 13.35x | 4.42x → 8.04x | 4.4x |
| Qwen3-8B | 554,700 | 3.64x | 5.58x → 2.17x | 2.75x → 12.28x | 4.22x → 7.33x | 4.5x |

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
| `band_low` | 0.5000 | yes | 11.53 us | 6.35x | 6.51x | 6.21x |
| `stated` | 1.0000 | yes | 6.82 us | 6.52x | 6.64x | 6.29x |
| `band_high` | 2.0000 | yes | 4.46 us | 6.62x | 6.71x | 6.33x |
| `asap7_reduction_s8_g2` | 0.4553 | **no** | 12.46 us | 6.31x | 6.49x | 6.20x |
| `asap7_add_bf16_sram_engine` | 0.2391 | **no** | 21.83 us | 6.00x | 6.25x | 6.05x |
| `asap7_matmul_bf16_sram_engine` | 0.0580 | **no** | 83.47 us | 4.60x | 5.08x | 5.27x |

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
| `band_low` | 0.1100 | yes | 21.886 MB/mm2 | 103.4 us | 6.38x | 5.56x | 7.07x |
| `stated` | 0.3300 | yes | 7.295 MB/mm2 | 34.5 us | 6.52x | 6.64x | 6.29x |
| `band_high` | 0.3300 | yes | 7.295 MB/mm2 | 34.5 us | 6.52x | 6.64x | 6.29x |
| `measured_ihp_sg13g2_130nm` | 0.1298 | yes | 18.553 MB/mm2 | 87.7 us | 6.38x | 5.56x | 7.07x |
| `measured_asap7_7nm_via_programmed` | 0.2500 | yes | 9.630 MB/mm2 | 45.5 us | 6.38x | 5.95x | 7.07x |
| `measured_asap7_7nm_shared_source_drain` | 0.1250 | yes | 19.259 MB/mm2 | 91.0 us | 6.38x | 5.56x | 7.07x |

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
| DeepSeek-V4-Flash-0731 | 8 | 6,608 | 95.3 | 569.1 | — | tensor | 436.16 | 24.8% | weight_read |
| DeepSeek-V4-Flash-0731 | 37 | 30,562 | 45.3 | 685.1 | 291.6 | tensor | 852.96 | 58.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 38 | 31,388 | 44.5 | 687.9 | 294.2 | tensor | 852.96 | 58.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 39 | 32,214 | 43.8 | 690.6 | 296.6 | tensor | 852.96 | 58.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 40 | 33,040 | 43.1 | 693.2 | 299.1 | tensor | 852.96 | 59.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 35,518 | 41.2 | 699.1 | 260.8 | tensor | 855.78 | 59.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 46 | 37,996 | 39.4 | 705.5 | 266.2 | tensor | 855.78 | 60.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 52 | 42,952 | 36.3 | 715.5 | 240.7 | tensor | 857.79 | 61.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 55 | 45,430 | 34.9 | 720.2 | 244.4 | tensor | 857.79 | 61.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 34.5 | 721.7 | 245.7 | tensor | 857.79 | 61.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 69 | 56,994 | 29.8 | 736.2 | 206.8 | tensor | 860.47 | 63.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 71 | 58,646 | 29.1 | 738.2 | 208.2 | tensor | 860.47 | 63.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 73 | 60,298 | 28.5 | 739.6 | 190.4 | tensor | 861.41 | 63.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 77 | 63,602 | 27.4 | 743.2 | 192.8 | tensor | 861.41 | 64.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 83 | 68,558 | 25.9 | 747.5 | 179.6 | tensor | 862.18 | 64.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 92 | 75,992 | 24.0 | 753.3 | 169.4 | tensor | 862.82 | 65.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 104 | 85,904 | 21.8 | 759.7 | 161.2 | tensor | 863.36 | 65.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 110 | 90,860 | 20.8 | 762.2 | 152.0 | tensor | 863.83 | 65.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 111 | 91,686 | 20.7 | 762.7 | 152.2 | tensor | 863.83 | 65.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 20.5 | 763.1 | 152.5 | tensor | 863.83 | 65.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 138 | 113,988 | 17.3 | 771.7 | 124.7 | tensor | 865.17 | 66.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 146 | 120,596 | 16.5 | 773.8 | 119.5 | tensor | 865.42 | 67.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 14.6 | 778.7 | 110.9 | tensor | 865.84 | 67.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 11.4 | 786.9 | 87.1 | tensor | 866.85 | 68.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 335 | 276,710 | 7.9 | 622.5 | 61.0 | tensor | 1,217.01 | 75.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 7.9 | 622.5 | 61.1 | tensor | 1,217.01 | 75.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 6.0 | 625.2 | 47.1 | tensor | 1,217.52 | 76.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 4.1 | 627.9 | 32.3 | tensor | 1,218.02 | 76.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 48 | 39,648 | 10.4 | 301.6 | 78.9 | tensor | 1,295.52 | 39.1% | weight_read |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 9.3 | 310.0 | 71.4 | tensor | 1,300.52 | 40.3% | weight_read |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 5.5 | 339.7 | 43.0 | tensor | 1,315.51 | 44.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 3.9 | 351.4 | 30.9 | tensor | 1,320.51 | 46.4% | weight_read |
| DeepSeek-V4-Pro-0813 | 196 | 161,896 | 3.5 | 354.9 | 26.6 | tensor | 1,322.11 | 46.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 204 | 168,504 | 3.3 | 355.8 | 25.7 | tensor | 1,322.43 | 47.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 207 | 170,982 | 3.3 | 356.1 | 25.7 | tensor | 1,322.43 | 47.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 215 | 177,590 | 3.2 | 356.9 | 24.9 | tensor | 1,322.73 | 47.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 3.1 | 357.7 | 24.1 | tensor | 1,323.01 | 47.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 234 | 193,284 | 2.9 | 358.5 | 22.6 | tensor | 1,323.51 | 47.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 245 | 202,370 | 2.8 | 359.4 | 22.0 | tensor | 1,323.73 | 47.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 2.5 | 361.6 | 19.8 | tensor | 1,324.51 | 47.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 293 | 242,018 | 2.4 | 362.3 | 18.8 | tensor | 1,324.83 | 48.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 335 | 276,710 | 2.1 | 308.6 | 16.8 | tensor | 1,820.83 | 56.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 2.1 | 308.6 | 16.8 | tensor | 1,820.83 | 56.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 373 | 308,098 | 1.9 | 309.6 | 15.1 | tensor | 1,821.36 | 56.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 377 | 311,402 | 1.9 | 309.7 | 14.8 | tensor | 1,821.45 | 56.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 391 | 322,966 | 1.8 | 310.0 | 14.6 | tensor | 1,821.54 | 56.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 392 | 323,792 | 1.8 | 310.0 | 14.6 | tensor | 1,821.54 | 56.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 1.6 | 311.1 | 12.9 | tensor | 1,822.07 | 56.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 1.1 | 313.6 | 8.8 | tensor | 1,823.32 | 57.2% | link_latency |
| Qwen3-8B | 5 | 4,130 | 100.9 | 425.4 | — | tensor | 364.72 | 15.5% | weight_read |
| Qwen3-8B | 6 | 4,956 | 100.8 | 494.8 | — | tensor | 364.92 | 18.1% | weight_read |
| Qwen3-8B | 7 | 5,782 | 100.8 | 560.0 | — | tensor | 365.06 | 20.4% | weight_read |
| Qwen3-8B | 8 | 6,608 | 100.8 | 621.5 | — | tensor | 365.16 | 22.7% | weight_read |
| Qwen3-8B | 10 | 8,260 | 100.7 | 591.9 | 424.9 | tensor | 692.87 | 41.0% | weight_read |
| Qwen3-8B | 12 | 9,912 | 100.7 | 656.0 | 494.1 | tensor | 692.87 | 45.5% | link_latency |
| Qwen3-8B | 15 | 12,390 | 100.6 | 735.6 | 590.4 | tensor | 692.87 | 51.0% | link_latency |
| Qwen3-8B | 16 | 13,216 | 100.6 | 758.6 | 620.6 | tensor | 692.87 | 52.6% | link_latency |
| Qwen3-8B | 20 | 16,520 | 100.5 | 829.0 | 537.3 | tensor | 704.67 | 58.4% | link_latency |
| Qwen3-8B | 56 | 46,256 | 100.1 | 1,109.0 | 616.1 | tensor | 718.15 | 79.6% | link_latency |
| Qwen3-8B | 111 | 91,686 | 100.1 | 1,220.7 | 605.8 | tensor | 723.20 | 88.3% | link_latency |
| Qwen3-8B | 112 | 92,512 | 100.1 | 1,221.9 | 609.9 | tensor | 723.20 | 88.4% | link_latency |
| Qwen3-8B | 168 | 138,768 | 100.1 | 1,264.8 | 603.8 | tensor | 724.89 | 91.7% | link_latency |
| Qwen3-8B | 224 | 185,024 | 100.1 | 1,287.4 | 597.8 | tensor | 725.73 | 93.4% | link_latency |
| Qwen3-8B | 335 | 276,710 | 100.1 | 947.6 | 589.9 | tensor | 1,018.89 | 96.6% | link_latency |
| Qwen3-8B | 336 | 277,536 | 100.1 | 947.7 | 591.2 | tensor | 1,018.89 | 96.6% | link_latency |
| Qwen3-8B | 448 | 370,048 | 100.1 | 954.0 | 591.2 | tensor | 1,019.32 | 97.2% | link_latency |
| Qwen3-8B | 672 | 555,072 | 100.1 | 960.4 | 591.2 | tensor | 1,019.74 | 97.9% | link_latency |

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
| Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x7 | Qwen3-8B | 7 | pipeline | nvlink3 | infiniband_hdr | 6 | 15.16 us | 6,594.6 tok/s | 65,946.4 tok/s | 6 x point_to_point span 2 on nvlink3 (traversals 1.0) = 15.16 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x7 | Qwen3-8B | 7 | tensor | nvlink3 | infiniband_hdr | 72 | 365.06 us | 273.9 tok/s | 2,739.3 tok/s | 72 x all_reduce span 7 on nvlink3 (traversals 2.0) = 365.06 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | Qwen3-8B | 5 | pipeline | nvlink3 | infiniband_hdr | 4 | 10.11 us | 9,892.0 tok/s | 98,919.5 tok/s | 4 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.11 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x8 | Qwen3-8B | 8 | tensor | nvlink3 | infiniband_hdr | 72 | 365.16 us | 273.9 tok/s | 2,738.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us |
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
| Qwen3-8B/a100_sxm_80gb-x20-pipeline | Qwen3-8B | 20 | pipeline | nvlink3 | infiniband_hdr | 19 | 47.68 us | 2,097.3 tok/s | 20,973.3 tok/s | 17 x point_to_point span 2 on nvlink3 (traversals 1.0) = 42.96 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| Qwen3-8B/a100_sxm_80gb-x20-tensor | Qwen3-8B | 20 | tensor | nvlink3 | infiniband_hdr | 144 | 704.67 us | 141.9 tok/s | 1,419.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 339.51 us |
| Qwen3-8B/a100_sxm_80gb-x20-hybrid | Qwen3-8B | 20 | hybrid | nvlink3 | infiniband_hdr | 74 | 369.88 us | 270.4 tok/s | 2,703.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| Qwen3-8B/a100_sxm_80gb-x56-pipeline | Qwen3-8B | 56 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x56-tensor | Qwen3-8B | 56 | tensor | nvlink3 | infiniband_hdr | 144 | 718.15 us | 139.2 tok/s | 1,392.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 352.99 us |
| Qwen3-8B/a100_sxm_80gb-x56-hybrid | Qwen3-8B | 56 | hybrid | nvlink3 | infiniband_hdr | 78 | 379.31 us | 263.6 tok/s | 2,636.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| Qwen3-8B/a100_sxm_80gb-x111-pipeline | Qwen3-8B | 111 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x111-tensor | Qwen3-8B | 111 | tensor | nvlink3 | infiniband_hdr | 144 | 723.20 us | 138.3 tok/s | 1,382.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 358.04 us |
| Qwen3-8B/a100_sxm_80gb-x111-hybrid | Qwen3-8B | 111 | hybrid | nvlink3 | infiniband_hdr | 85 | 395.81 us | 252.6 tok/s | 2,526.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| Qwen3-8B/a100_sxm_80gb-x112-pipeline | Qwen3-8B | 112 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x112-tensor | Qwen3-8B | 112 | tensor | nvlink3 | infiniband_hdr | 144 | 723.20 us | 138.3 tok/s | 1,382.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 358.04 us |
| Qwen3-8B/a100_sxm_80gb-x112-hybrid | Qwen3-8B | 112 | hybrid | nvlink3 | infiniband_hdr | 85 | 395.81 us | 252.6 tok/s | 2,526.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| Qwen3-8B/a100_sxm_80gb-x168-pipeline | Qwen3-8B | 168 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x168-tensor | Qwen3-8B | 168 | tensor | nvlink3 | infiniband_hdr | 144 | 724.89 us | 138.0 tok/s | 1,379.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 359.73 us |
| Qwen3-8B/a100_sxm_80gb-x168-hybrid | Qwen3-8B | 168 | hybrid | nvlink3 | infiniband_hdr | 92 | 412.31 us | 242.5 tok/s | 2,425.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| Qwen3-8B/a100_sxm_80gb-x224-pipeline | Qwen3-8B | 224 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x224-tensor | Qwen3-8B | 224 | tensor | nvlink3 | infiniband_hdr | 144 | 725.73 us | 137.8 tok/s | 1,377.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 360.57 us |
| Qwen3-8B/a100_sxm_80gb-x224-hybrid | Qwen3-8B | 224 | hybrid | nvlink3 | infiniband_hdr | 99 | 428.82 us | 233.2 tok/s | 2,332.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
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
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x39 | DeepSeek-V4-Flash-0731 | 39 | pipeline | nvlink3 | infiniband_hdr | 38 | 95.36 us | 1,048.7 tok/s | 10,486.7 tok/s | 34 x point_to_point span 2 on nvlink3 (traversals 1.0) = 85.93 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x38 | DeepSeek-V4-Flash-0731 | 38 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x39 | DeepSeek-V4-Flash-0731 | 39 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x41 | DeepSeek-V4-Flash-0731 | 41 | pipeline | nvlink3 | infiniband_hdr | 40 | 100.24 us | 997.6 tok/s | 9,975.6 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.46 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x40 | DeepSeek-V4-Flash-0731 | 40 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x40 | DeepSeek-V4-Flash-0731 | 40 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x8-pipeline | DeepSeek-V4-Flash-0731 | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 17.69 us | 5,652.5 tok/s | 56,525.4 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 17.69 us |
| DSV4-Flash/a100_sxm_80gb-x8-tensor | DeepSeek-V4-Flash-0731 | 8 | tensor | nvlink3 | infiniband_hdr | 86 | 436.16 us | 229.3 tok/s | 2,292.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us |
| DSV4-Flash/a100_sxm_80gb-x37-pipeline | DeepSeek-V4-Flash-0731 | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-tensor | DeepSeek-V4-Flash-0731 | 37 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x37-hybrid | DeepSeek-V4-Flash-0731 | 37 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x38-pipeline | DeepSeek-V4-Flash-0731 | 38 | pipeline | nvlink3 | infiniband_hdr | 37 | 92.83 us | 1,077.2 tok/s | 10,772.2 tok/s | 33 x point_to_point span 2 on nvlink3 (traversals 1.0) = 83.40 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x38-tensor | DeepSeek-V4-Flash-0731 | 38 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x38-hybrid | DeepSeek-V4-Flash-0731 | 38 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x39-pipeline | DeepSeek-V4-Flash-0731 | 39 | pipeline | nvlink3 | infiniband_hdr | 38 | 95.36 us | 1,048.7 tok/s | 10,486.7 tok/s | 34 x point_to_point span 2 on nvlink3 (traversals 1.0) = 85.93 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x39-tensor | DeepSeek-V4-Flash-0731 | 39 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x39-hybrid | DeepSeek-V4-Flash-0731 | 39 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x40-pipeline | DeepSeek-V4-Flash-0731 | 40 | pipeline | nvlink3 | infiniband_hdr | 39 | 97.89 us | 1,021.6 tok/s | 10,215.9 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.46 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x40-tensor | DeepSeek-V4-Flash-0731 | 40 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x40-hybrid | DeepSeek-V4-Flash-0731 | 40 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-pipeline | DeepSeek-V4-Flash-0731 | 46 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x46-hybrid | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x52-pipeline | DeepSeek-V4-Flash-0731 | 52 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x52-tensor | DeepSeek-V4-Flash-0731 | 52 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x52-hybrid | DeepSeek-V4-Flash-0731 | 52 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x55-pipeline | DeepSeek-V4-Flash-0731 | 55 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x55-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x55-hybrid | DeepSeek-V4-Flash-0731 | 55 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x69-pipeline | DeepSeek-V4-Flash-0731 | 69 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x69-tensor | DeepSeek-V4-Flash-0731 | 69 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x69-hybrid | DeepSeek-V4-Flash-0731 | 69 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x71-pipeline | DeepSeek-V4-Flash-0731 | 71 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x71-tensor | DeepSeek-V4-Flash-0731 | 71 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x71-hybrid | DeepSeek-V4-Flash-0731 | 71 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x73-pipeline | DeepSeek-V4-Flash-0731 | 73 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x73-tensor | DeepSeek-V4-Flash-0731 | 73 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x73-hybrid | DeepSeek-V4-Flash-0731 | 73 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x77-pipeline | DeepSeek-V4-Flash-0731 | 77 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x77-tensor | DeepSeek-V4-Flash-0731 | 77 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x77-hybrid | DeepSeek-V4-Flash-0731 | 77 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x83-pipeline | DeepSeek-V4-Flash-0731 | 83 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x83-tensor | DeepSeek-V4-Flash-0731 | 83 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x83-hybrid | DeepSeek-V4-Flash-0731 | 83 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x92-pipeline | DeepSeek-V4-Flash-0731 | 92 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x92-tensor | DeepSeek-V4-Flash-0731 | 92 | tensor | nvlink3 | infiniband_hdr | 172 | 862.82 us | 115.9 tok/s | 1,159.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 426.66 us |
| DSV4-Flash/a100_sxm_80gb-x92-hybrid | DeepSeek-V4-Flash-0731 | 92 | hybrid | nvlink3 | infiniband_hdr | 97 | 462.10 us | 216.4 tok/s | 2,164.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.93 us |
| DSV4-Flash/a100_sxm_80gb-x104-pipeline | DeepSeek-V4-Flash-0731 | 104 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x104-tensor | DeepSeek-V4-Flash-0731 | 104 | tensor | nvlink3 | infiniband_hdr | 172 | 863.36 us | 115.8 tok/s | 1,158.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 427.20 us |
| DSV4-Flash/a100_sxm_80gb-x104-hybrid | DeepSeek-V4-Flash-0731 | 104 | hybrid | nvlink3 | infiniband_hdr | 98 | 464.46 us | 215.3 tok/s | 2,153.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.29 us |
| DSV4-Flash/a100_sxm_80gb-x110-pipeline | DeepSeek-V4-Flash-0731 | 110 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x110-tensor | DeepSeek-V4-Flash-0731 | 110 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x110-hybrid | DeepSeek-V4-Flash-0731 | 110 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4-Flash-0731 | 111 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4-Flash-0731 | 111 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4-Flash-0731 | 111 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Flash-0731 | 112 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Flash-0731 | 112 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Flash-0731 | 112 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x138-pipeline | DeepSeek-V4-Flash-0731 | 138 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x138-tensor | DeepSeek-V4-Flash-0731 | 138 | tensor | nvlink3 | infiniband_hdr | 172 | 865.17 us | 115.6 tok/s | 1,155.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 429.00 us |
| DSV4-Flash/a100_sxm_80gb-x138-hybrid | DeepSeek-V4-Flash-0731 | 138 | hybrid | nvlink3 | infiniband_hdr | 103 | 476.25 us | 210.0 tok/s | 2,099.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| DSV4-Flash/a100_sxm_80gb-x146-pipeline | DeepSeek-V4-Flash-0731 | 146 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x146-tensor | DeepSeek-V4-Flash-0731 | 146 | tensor | nvlink3 | infiniband_hdr | 172 | 865.42 us | 115.6 tok/s | 1,155.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 429.25 us |
| DSV4-Flash/a100_sxm_80gb-x146-hybrid | DeepSeek-V4-Flash-0731 | 146 | hybrid | nvlink3 | infiniband_hdr | 104 | 478.60 us | 208.9 tok/s | 2,089.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 42.44 us |
| DSV4-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Flash-0731 | 168 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Flash-0731 | 168 | tensor | nvlink3 | infiniband_hdr | 172 | 865.84 us | 115.5 tok/s | 1,154.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 429.68 us |
| DSV4-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Flash-0731 | 168 | hybrid | nvlink3 | infiniband_hdr | 106 | 483.32 us | 206.9 tok/s | 2,069.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| DSV4-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Flash-0731 | 224 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Flash-0731 | 224 | tensor | nvlink3 | infiniband_hdr | 172 | 866.85 us | 115.4 tok/s | 1,153.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 430.68 us |
| DSV4-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Flash-0731 | 224 | hybrid | nvlink3 | infiniband_hdr | 113 | 499.82 us | 200.1 tok/s | 2,000.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| DSV4-Flash/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Flash-0731 | 335 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Flash-0731 | 335 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.01 us | 82.2 tok/s | 821.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 780.85 us |
| DSV4-Flash/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Flash-0731 | 335 | hybrid | nvlink3 | infiniband_hdr | 127 | 532.83 us | 187.7 tok/s | 1,876.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| DSV4-Flash/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Flash-0731 | 336 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Flash-0731 | 336 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.01 us | 82.2 tok/s | 821.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 780.85 us |
| DSV4-Flash/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Flash-0731 | 336 | hybrid | nvlink3 | infiniband_hdr | 127 | 532.83 us | 187.7 tok/s | 1,876.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| DSV4-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Flash-0731 | 448 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Flash-0731 | 448 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.52 us | 82.1 tok/s | 821.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 781.35 us |
| DSV4-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Flash-0731 | 448 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Flash-0731 | 672 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Flash-0731 | 672 | tensor | nvlink3 | infiniband_hdr | 172 | 1,218.02 us | 82.1 tok/s | 821.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 781.85 us |
| DSV4-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Flash-0731 | 672 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x207 | DeepSeek-V4-Pro-0813 | 207 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4 | DeepSeek-V4-Pro-0813 | 4 | pipeline | on_wafer | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x199 | DeepSeek-V4-Pro-0813 | 199 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.11 us | 75.6 tok/s | 756.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 696.80 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | inter_wafer | 244 | 1,481.09 us | 67.5 tok/s | 675.2 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on inter_wafer (traversals 2.0) = 1,246.23 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x207 | DeepSeek-V4-Pro-0813 | 207 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | DeepSeek-V4-Pro-0813 | 4 | hybrid | on_wafer | inter_wafer | 125 | 250.14 us | 399.8 tok/s | 3,997.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 3 x point_to_point span 2 on inter_wafer (traversals 1.0) = 15.29 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x218 | DeepSeek-V4-Pro-0813 | 218 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5 | DeepSeek-V4-Pro-0813 | 5 | pipeline | on_wafer | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x210 | DeepSeek-V4-Pro-0813 | 210 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.73 us | 75.6 tok/s | 756.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 697.43 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x5 | DeepSeek-V4-Pro-0813 | 5 | tensor | on_wafer | inter_wafer | 244 | 2,702.83 us | 37.0 tok/s | 370.0 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 5 on inter_wafer (traversals 4.0) = 2,467.98 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x218 | DeepSeek-V4-Pro-0813 | 218 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer | inter_wafer | 126 | 255.23 us | 391.8 tok/s | 3,918.0 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 4 x point_to_point span 2 on inter_wafer (traversals 1.0) = 20.38 us |
| DSV4-Pro/a100_sxm_80gb-x48-pipeline | DeepSeek-V4-Pro-0813 | 48 | pipeline | nvlink3 | infiniband_hdr | 47 | 120.02 us | 833.2 tok/s | 8,331.7 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 107.01 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 13.02 us |
| DSV4-Pro/a100_sxm_80gb-x48-tensor | DeepSeek-V4-Pro-0813 | 48 | tensor | nvlink3 | infiniband_hdr | 244 | 1,295.52 us | 77.2 tok/s | 771.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 670.22 us |
| DSV4-Pro/a100_sxm_80gb-x48-hybrid | DeepSeek-V4-Pro-0813 | 48 | hybrid | nvlink3 | infiniband_hdr | 127 | 638.32 us | 156.7 tok/s | 1,566.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 13.02 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,300.52 us | 76.9 tok/s | 768.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 675.22 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 640.92 us | 156.0 tok/s | 1,560.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.51 us | 75.7 tok/s | 757.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 695.20 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 677.37 us | 147.6 tok/s | 1,476.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| DSV4-Pro/a100_sxm_80gb-x196-pipeline | DeepSeek-V4-Pro-0813 | 196 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x196-tensor | DeepSeek-V4-Pro-0813 | 196 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.11 us | 75.6 tok/s | 756.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 696.80 us |
| DSV4-Pro/a100_sxm_80gb-x196-hybrid | DeepSeek-V4-Pro-0813 | 196 | hybrid | nvlink3 | infiniband_hdr | 146 | 687.79 us | 145.4 tok/s | 1,453.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.48 us |
| DSV4-Pro/a100_sxm_80gb-x204-pipeline | DeepSeek-V4-Pro-0813 | 204 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x204-tensor | DeepSeek-V4-Pro-0813 | 204 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x204-hybrid | DeepSeek-V4-Pro-0813 | 204 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x207-pipeline | DeepSeek-V4-Pro-0813 | 207 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x207-tensor | DeepSeek-V4-Pro-0813 | 207 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x207-hybrid | DeepSeek-V4-Pro-0813 | 207 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x215-pipeline | DeepSeek-V4-Pro-0813 | 215 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x215-tensor | DeepSeek-V4-Pro-0813 | 215 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.73 us | 75.6 tok/s | 756.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 697.43 us |
| DSV4-Pro/a100_sxm_80gb-x215-hybrid | DeepSeek-V4-Pro-0813 | 215 | hybrid | nvlink3 | infiniband_hdr | 148 | 692.99 us | 144.3 tok/s | 1,443.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 67.69 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x234-pipeline | DeepSeek-V4-Pro-0813 | 234 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x234-tensor | DeepSeek-V4-Pro-0813 | 234 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.51 us | 75.6 tok/s | 755.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 30 on infiniband_hdr (traversals 2.0) = 698.20 us |
| DSV4-Pro/a100_sxm_80gb-x234-hybrid | DeepSeek-V4-Pro-0813 | 234 | hybrid | nvlink3 | infiniband_hdr | 151 | 700.80 us | 142.7 tok/s | 1,426.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 29 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.50 us |
| DSV4-Pro/a100_sxm_80gb-x245-pipeline | DeepSeek-V4-Pro-0813 | 245 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x245-tensor | DeepSeek-V4-Pro-0813 | 245 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.73 us | 75.5 tok/s | 755.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 698.43 us |
| DSV4-Pro/a100_sxm_80gb-x245-hybrid | DeepSeek-V4-Pro-0813 | 245 | hybrid | nvlink3 | infiniband_hdr | 152 | 703.41 us | 142.2 tok/s | 1,421.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.10 us |
| DSV4-Pro/a100_sxm_80gb-x280-pipeline | DeepSeek-V4-Pro-0813 | 280 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x280-tensor | DeepSeek-V4-Pro-0813 | 280 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.51 us | 75.5 tok/s | 755.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 699.20 us |
| DSV4-Pro/a100_sxm_80gb-x280-hybrid | DeepSeek-V4-Pro-0813 | 280 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/a100_sxm_80gb-x293-pipeline | DeepSeek-V4-Pro-0813 | 293 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x293-tensor | DeepSeek-V4-Pro-0813 | 293 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.83 us | 75.5 tok/s | 754.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 37 on infiniband_hdr (traversals 2.0) = 699.53 us |
| DSV4-Pro/a100_sxm_80gb-x293-hybrid | DeepSeek-V4-Pro-0813 | 293 | hybrid | nvlink3 | infiniband_hdr | 158 | 719.03 us | 139.1 tok/s | 1,390.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 36 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 93.72 us |
| DSV4-Pro/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Pro-0813 | 335 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Pro-0813 | 335 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Pro-0813 | 335 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Pro-0813 | 336 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Pro-0813 | 336 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Pro-0813 | 336 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x373-pipeline | DeepSeek-V4-Pro-0813 | 373 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x373-tensor | DeepSeek-V4-Pro-0813 | 373 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.36 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,196.05 us |
| DSV4-Pro/a100_sxm_80gb-x373-hybrid | DeepSeek-V4-Pro-0813 | 373 | hybrid | nvlink3 | infiniband_hdr | 168 | 745.06 us | 134.2 tok/s | 1,342.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 119.76 us |
| DSV4-Pro/a100_sxm_80gb-x377-pipeline | DeepSeek-V4-Pro-0813 | 377 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x377-tensor | DeepSeek-V4-Pro-0813 | 377 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.45 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 1,196.15 us |
| DSV4-Pro/a100_sxm_80gb-x377-hybrid | DeepSeek-V4-Pro-0813 | 377 | hybrid | nvlink3 | infiniband_hdr | 169 | 747.67 us | 133.7 tok/s | 1,337.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 122.36 us |
| DSV4-Pro/a100_sxm_80gb-x391-pipeline | DeepSeek-V4-Pro-0813 | 391 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x391-tensor | DeepSeek-V4-Pro-0813 | 391 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x391-hybrid | DeepSeek-V4-Pro-0813 | 391 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x392-pipeline | DeepSeek-V4-Pro-0813 | 392 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x392-tensor | DeepSeek-V4-Pro-0813 | 392 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x392-hybrid | DeepSeek-V4-Pro-0813 | 392 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Pro-0813 | 448 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Pro-0813 | 448 | tensor | nvlink3 | infiniband_hdr | 244 | 1,822.07 us | 54.9 tok/s | 548.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,196.77 us |
| DSV4-Pro/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Pro-0813 | 448 | hybrid | nvlink3 | infiniband_hdr | 177 | 768.49 us | 130.1 tok/s | 1,301.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 143.19 us |
| DSV4-Pro/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Pro-0813 | 672 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Pro-0813 | 672 | tensor | nvlink3 | infiniband_hdr | 244 | 1,823.32 us | 54.8 tok/s | 548.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,198.02 us |
| DSV4-Pro/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Pro-0813 | 672 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 6,464.4 | 0.140 | 3,517.9 (5,705) | 6,464.4 (46,225) | 1.84x | link_latency |
| Qwen3-8B | 2 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,245.8 | 0.046 | 2,119.2 (12,225) | 4,245.8 (92,450) | 2.00x | link_latency |
| Qwen3-8B | 4 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,071.0 | 0.022 | 2,036.0 (46,455) | 4,071.0 (184,900) | 2.00x | link_latency |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,761.4 | 0.010 | 2,036.0 (46,455) | 3,761.4 (369,800) | 1.85x | link_latency |
| Qwen3-8B | 16 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,178.4 | 0.006 | 1,963.8 (92,095) | 3,178.4 (554,700) | 1.62x | link_latency |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,331.9 | 0.004 | 1,771.0 (138,550) | 2,331.9 (554,700) | 1.32x | kv_read |
| Qwen3-8B | 64 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 1,665.8 | 0.006 | 1,665.8 (277,100) | 1,521.5 (554,700) | 0.91x | link_latency |
| Qwen3-8B | 256 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 1,210.5 | 0.004 | 1,210.5 (277,100) | 493.2 (554,700) | 0.41x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | wafer | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 0.102 | 1,506.3 (30,970) | 4,707.9 (46,225) | 3.13x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,583.4 | 0.099 | 1,456.6 (32,600) | 4,583.4 (46,225) | 3.15x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,390.6 | 0.047 | 1,456.6 (32,600) | 4,390.6 (92,450) | 3.01x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,034.8 | 0.029 | 1,443.6 (38,305) | 4,034.8 (138,675) | 2.79x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 3,798.2 | 0.014 | 1,422.2 (38,305) | 3,798.2 (277,350) | 2.67x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,290.7 | 0.009 | 1,316.1 (45,640) | 3,290.7 (369,800) | 2.50x | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,814.0 | 0.005 | 1,141.9 (60,310) | 2,814.0 (554,700) | 2.46x | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,383.8 | 0.002 | 1,028.9 (185,005) | 1,383.8 (554,700) | 1.34x | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | 184,900 | 2,375.7 | 0.013 | 711.5 (162,185) | 2,375.7 (184,900) | 3.34x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 2,153.7 | 0.009 | 611.2 (177,670) | 2,153.7 (231,125) | 3.52x | link_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 2,153.7 | 0.009 | 554.6 (177,670) | 2,153.7 (231,125) | 3.88x | link_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 1,916.7 | 0.008 | 554.6 (177,670) | 1,916.7 (231,125) | 3.46x | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,845.4 | 0.003 | 554.6 (177,670) | 1,845.4 (554,700) | 3.33x | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,379.9 | 0.002 | 546.6 (185,005) | 1,379.9 (554,700) | 2.52x | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 875.7 | 0.002 | 514.7 (202,120) | 875.7 (554,700) | 1.70x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x340 | 277,100 | 385.5 | 0.001 | 385.5 (277,100) | 274.3 (554,700) | 0.71x | weight_read |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. The ROM-plus-MAC floorplan holds the requested weights; the compute-in-ROM floorplan holds only 67.7% and is infeasible at this area. The failed floorplan is retained so the capacity cost of the larger cell remains visible.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 481.6 mm2 | 521.6 mm2 |
| weight capacity | 3.51 GB (100.0%) | 2.38 GB (67.7%) |
| capacity-feasible | yes | **no** |
| compute block | 186.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 0.0 mm2 |
| sustained fp8 compute roof | 9.154e+13 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 4.577e+13 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 6.900e+13 |
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

`docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` names an open
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
subject of `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`: its sweep depth
is the load of the **busiest** expert region, computed from the routing
distribution rather than from the mean engaged region.

| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | Per-region aggregate | Per-stream penalty | Per-region over broadcast | Batched binds on | Per-stream binds on | Per-region binds on |
|---|---:|---|---:|---:|---:|---:|---:|---|---|---|
| Qwen3-8B | 1 | sram | 26,102.0 | 28,850.2 | 28,850.2 | 0.90x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 26,102.0 | 28,850.2 | 28,850.2 | 0.90x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 26,102.0 | 28,850.2 | 28,850.2 | 0.90x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 26,102.0 | 28,850.2 | 28,850.2 | 0.90x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 39,908.6 | 28,850.2 | 28,850.2 | 1.38x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 61,282.5 | 28,850.2 | 28,850.2 | 2.12x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 96,507.4 | 28,868.1 | 28,868.1 | 3.34x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 155,048.0 | 13,055.8 | 13,055.8 | 11.88x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1 | rom | 411,583.8 | 13,029.9 | 13,029.9 | 31.59x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 411,583.8 | 13,029.9 | 13,029.9 | 31.59x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 411,583.8 | 13,029.9 | 13,029.9 | 31.59x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 411,583.8 | 13,029.9 | 13,029.9 | 31.59x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 411,583.8 | 13,029.9 | 13,029.9 | 31.59x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 411,583.8 | 13,029.9 | 13,029.9 | 31.59x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 411,583.8 | 13,033.5 | 13,033.5 | 31.58x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 411,583.8 | 13,055.8 | 13,055.8 | 31.52x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 28,756.4 | 26,008.0 | 26,008.0 | 1.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 28,756.4 | 26,008.0 | 26,008.0 | 1.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 28,756.4 | 26,008.0 | 26,008.0 | 1.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 29,349.5 | 26,008.0 | 26,353.6 | 1.13x | 1.01x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 51,990.8 | 26,008.0 | 46,137.9 | 2.00x | 1.77x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 85,771.3 | 26,008.0 | 79,080.0 | 3.30x | 3.04x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 144,047.5 | 26,008.0 | 71,109.7 | 5.54x | 2.73x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 354,255.0 | 26,066.2 | 123,811.0 | 13.59x | 4.75x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 273,531.4 | 41,334.8 | 41,334.8 | 6.62x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 273,531.4 | 41,334.8 | 41,334.8 | 6.62x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 273,531.4 | 41,334.8 | 41,334.8 | 6.62x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 273,531.4 | 41,334.8 | 41,334.8 | 6.62x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 273,531.4 | 41,334.8 | 44,173.1 | 6.62x | 1.07x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | rom | 273,531.4 | 41,334.8 | 59,097.3 | 6.62x | 1.43x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 273,531.4 | 41,334.8 | 71,109.7 | 6.62x | 1.72x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 354,255.0 | 41,482.0 | 132,143.7 | 8.54x | 3.19x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 26,083.1 | 26,061.7 | 26,061.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 26,083.1 | 26,061.7 | 26,061.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 26,083.1 | 26,061.7 | 26,061.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 26,083.1 | 26,061.7 | 26,061.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 26,682.8 | 26,061.7 | 26,061.7 | 1.02x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 41,569.2 | 26,061.7 | 32,142.3 | 1.60x | 1.23x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 56,043.3 | 26,061.7 | 37,455.6 | 2.15x | 1.44x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 98,687.6 | 26,061.7 | 42,756.6 | 3.79x | 1.64x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 51,379.6 | 27,161.9 | 27,161.9 | 1.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 51,379.6 | 27,161.9 | 27,161.9 | 1.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 51,379.6 | 27,161.9 | 27,161.9 | 1.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 51,379.6 | 27,161.9 | 27,161.9 | 1.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 51,379.6 | 27,161.9 | 27,161.9 | 1.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 51,379.6 | 27,161.9 | 32,142.3 | 1.89x | 1.18x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 56,043.3 | 27,161.9 | 37,455.6 | 2.06x | 1.38x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 98,687.6 | 27,161.9 | 42,756.6 | 3.63x | 1.57x | weight_read | weight_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,102.0 | 0.047 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 411,583.8 | 1.485 | kv_read | 15.77x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.11x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.50x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.11x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.50x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,102.0 | 0.047 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 411,583.8 | 1.485 | kv_read | 15.77x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.11x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.50x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.11x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.50x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,102.0 | 0.047 | weight_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 411,583.8 | 1.485 | kv_read | 15.77x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.11x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.50x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.11x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.50x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,102.0 | 0.047 | weight_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 411,583.8 | 1.485 | kv_read | 15.77x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.11x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.50x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.11x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.50x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 39,908.6 | 0.144 | weight_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 411,583.8 | 1.485 | kv_read | 10.31x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.72x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.33x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.72x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.33x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 61,282.5 | 0.166 | kv_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 411,583.8 | 1.485 | kv_read | 6.72x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.47x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.21x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.47x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 8.11 | 1.00 | 13,029.9 | 0.282 | kv_read | 0.21x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 96,507.4 | 0.174 | weight_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 411,583.8 | 1.485 | kv_read | 4.26x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,868.1 | 0.625 | weight_read | 0.30x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 8.11 | 1.12 | 13,033.5 | 0.282 | kv_read | 0.14x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 28,868.1 | 0.625 | weight_read | 0.30x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 8.11 | 1.12 | 13,033.5 | 0.282 | kv_read | 0.14x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hybrid-x170 | 138,550 | 1.00 | 1.00 | 155,048.0 | 1.119 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 411,583.8 | 1.485 | kv_read | 2.65x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 13,055.8 | 0.282 | kv_read | 0.08x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 8.11 | 4.49 | 13,055.8 | 0.282 | kv_read | 0.08x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.49 | 13,055.8 | 0.282 | kv_read | 0.08x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 8.11 | 4.49 | 13,055.8 | 0.282 | kv_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 9.51x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 9.51x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 9.51x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 29,349.5 | 0.317 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 9.32x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.89x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.41x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.57 | 26,353.6 | 0.285 | link_latency | 0.90x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.41x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 51,990.8 | 0.375 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 5.26x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.50x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 0.80x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.13 | 46,137.9 | 0.499 | link_latency | 0.89x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.59 | 2.13 | 44,173.1 | 0.478 | link_latency | 0.85x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 85,771.3 | 0.464 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 3.19x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.30x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 0.48x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.88 | 79,080.0 | 0.855 | weight_read | 0.92x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.59 | 2.88 | 59,097.3 | 0.639 | kv_read | 0.69x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 144,047.5 | 0.519 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 1.90x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.18x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 0.29x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 4.03 | 71,109.7 | 0.769 | kv_read | 0.49x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.59 | 4.03 | 71,109.7 | 0.769 | kv_read | 0.49x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 354,255.0 | 0.639 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 10.55 | 1.00 | 354,255.0 | 0.639 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 2.25 | 26,066.2 | 0.282 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 2.25 | 41,482.0 | 0.449 | weight_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x78-perregion | 63,570 | 1.00 | 3.59 | 123,811.0 | 1.948 | weight_read | 0.35x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x93-perregion-romfill | 75,795 | 1.20 | 3.30 | 132,143.7 | 1.743 | weight_read | 0.37x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 26,682.8 | 0.072 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.93x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 0.98x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.02x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 0.98x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.02x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 41,569.2 | 0.075 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.24x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 0.63x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 0.65x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 1.53 | 32,142.3 | 0.099 | kv_read | 0.77x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion-romfill | 323,575 | 1.04 | 1.53 | 32,142.3 | 0.099 | kv_read | 0.77x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 56,043.3 | 0.101 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1.97 | 1.00 | 56,043.3 | 0.101 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 0.47x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 0.48x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 2.08 | 37,455.6 | 0.116 | kv_read | 0.67x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion-romfill | 323,575 | 1.04 | 2.08 | 37,455.6 | 0.116 | kv_read | 0.67x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x340 | 277,100 | 1.00 | 1.00 | 98,687.6 | 0.356 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 1.00 | 1.00 | 98,687.6 | 0.356 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 0.26x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 0.28x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 3.72 | 42,756.6 | 0.132 | kv_read | 0.43x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion-romfill | 323,575 | 1.04 | 3.72 | 42,756.6 | 0.132 | kv_read | 0.43x |

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
| Qwen3-8B | 1 | 8 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 57 | 1.12 | 1.123 | 1.123 | 1.00x |
| Qwen3-8B | 256 | 8 | 32.00 | 32.000 | 32.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 72 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 72 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 78 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | 78 | 3.28 | 1.027 | 1.408 | 1.37x |
| DeepSeek-V4-Pro-0813 | 1 | 382 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |

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
| DeepSeek-V4-Flash-0731 | 2 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 4 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 8 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 16 | 8 | 6.36 | 3.68 | 1.73x |
| DeepSeek-V4-Flash-0731 | 32 | 8 | 7.64 | 4.38 | 1.74x |
| DeepSeek-V4-Flash-0731 | 64 | 8 | 7.98 | 5.03 | 1.59x |
| DeepSeek-V4-Flash-0731 | 256 | 8 | 8.00 | 6.01 | 1.33x |
| DeepSeek-V4-Flash-0731 | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 4 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 8 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 16 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 32 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 64 | 37 | 9.09 | 5.84 | 1.56x |
| DeepSeek-V4-Flash-0731 | 256 | 37 | 24.20 | 10.62 | 2.28x |
| DeepSeek-V4-Flash-0731 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 4 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 8 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 16 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 32 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 64 | 38 | 8.91 | 5.82 | 1.53x |
| DeepSeek-V4-Flash-0731 | 256 | 38 | 24.13 | 10.62 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 2 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 4 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 8 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 16 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 32 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 64 | 39 | 8.74 | 5.79 | 1.51x |
| DeepSeek-V4-Flash-0731 | 256 | 39 | 24.05 | 10.63 | 2.26x |
| DeepSeek-V4-Flash-0731 | 1 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Flash-0731 | 2 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Flash-0731 | 4 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Flash-0731 | 8 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Flash-0731 | 16 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Flash-0731 | 32 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Flash-0731 | 64 | 40 | 8.58 | 5.77 | 1.49x |
| DeepSeek-V4-Flash-0731 | 256 | 40 | 23.94 | 10.63 | 2.25x |
| DeepSeek-V4-Flash-0731 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 8 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 16 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 32 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 64 | 43 | 8.11 | 5.69 | 1.43x |
| DeepSeek-V4-Flash-0731 | 256 | 43 | 23.55 | 10.61 | 2.22x |
| DeepSeek-V4-Flash-0731 | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 8 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 16 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 32 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 64 | 46 | 7.68 | 5.61 | 1.37x |
| DeepSeek-V4-Flash-0731 | 256 | 46 | 23.06 | 10.59 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 4 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 8 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 16 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 32 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 64 | 52 | 6.93 | 5.42 | 1.28x |
| DeepSeek-V4-Flash-0731 | 256 | 52 | 21.93 | 10.50 | 2.09x |
| DeepSeek-V4-Flash-0731 | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 4 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 8 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 16 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 32 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 64 | 55 | 6.60 | 5.32 | 1.24x |
| DeepSeek-V4-Flash-0731 | 256 | 55 | 21.34 | 10.43 | 2.05x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 21.14 | 10.40 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 8 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 16 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 32 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 64 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 256 | 69 | 18.63 | 9.93 | 1.88x |
| DeepSeek-V4-Flash-0731 | 1 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4-Flash-0731 | 4 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4-Flash-0731 | 8 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4-Flash-0731 | 16 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4-Flash-0731 | 32 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4-Flash-0731 | 64 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4-Flash-0731 | 256 | 71 | 18.28 | 9.85 | 1.85x |
| DeepSeek-V4-Flash-0731 | 1 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 4 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 8 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 16 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 32 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 64 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 256 | 73 | 17.93 | 9.78 | 1.83x |
| DeepSeek-V4-Flash-0731 | 1 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 4 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 8 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 16 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 32 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 64 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 256 | 77 | 17.26 | 9.64 | 1.79x |
| DeepSeek-V4-Flash-0731 | 1 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Flash-0731 | 4 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Flash-0731 | 8 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Flash-0731 | 16 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Flash-0731 | 32 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Flash-0731 | 64 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Flash-0731 | 256 | 83 | 16.32 | 9.45 | 1.73x |
| DeepSeek-V4-Flash-0731 | 1 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 8 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 16 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 32 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 64 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 256 | 92 | 15.05 | 9.22 | 1.63x |
| DeepSeek-V4-Flash-0731 | 1 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 104 | 13.61 | 8.97 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 110 | 12.98 | 8.86 | 1.46x |
| DeepSeek-V4-Flash-0731 | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 111 | 12.88 | 8.84 | 1.46x |
| DeepSeek-V4-Flash-0731 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 112 | 12.78 | 8.82 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 4 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 8 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 16 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 32 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 64 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 256 | 138 | 10.63 | 8.30 | 1.28x |
| DeepSeek-V4-Flash-0731 | 1 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 4 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 8 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 16 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 32 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 64 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 256 | 146 | 10.10 | 8.12 | 1.24x |
| DeepSeek-V4-Flash-0731 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 256 | 168 | 8.87 | 7.61 | 1.17x |
| DeepSeek-V4-Flash-0731 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4-Flash-0731 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 1 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 2 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 4 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 8 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 16 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 32 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 64 | 48 | 7.42 | 5.55 | 1.34x |
| DeepSeek-V4-Pro-0813 | 256 | 48 | 22.97 | 10.64 | 2.16x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 21.37 | 10.48 | 2.04x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 12.84 | 8.85 | 1.45x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 8.89 | 7.62 | 1.17x |
| DeepSeek-V4-Pro-0813 | 1 | 196 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 196 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 196 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 196 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 196 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 196 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 196 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 196 | 7.68 | 6.94 | 1.11x |
| DeepSeek-V4-Pro-0813 | 1 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 204 | 7.40 | 6.76 | 1.09x |
| DeepSeek-V4-Pro-0813 | 1 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 207 | 7.29 | 6.69 | 1.09x |
| DeepSeek-V4-Pro-0813 | 1 | 215 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 215 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 215 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 215 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 215 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 215 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 215 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 215 | 7.03 | 6.51 | 1.08x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4-Pro-0813 | 1 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 234 | 6.48 | 6.11 | 1.06x |
| DeepSeek-V4-Pro-0813 | 1 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 245 | 6.20 | 5.90 | 1.05x |
| DeepSeek-V4-Pro-0813 | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 16 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 32 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 64 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 256 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 1 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 16 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 32 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 64 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 256 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 256 | 672 | 5.98 | 5.88 | 1.02x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 1.0% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 0.6% |
| gpu | Qwen3-8B | 1 | 6.82 | 0.9% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 5.8% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 4.2% |
| rom | Qwen3-8B | 1 | 6.82 | 4.4% |

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
| Qwen3-8B | 1 | 8 | 69.21% | 51.35 | 9.27 |
| Qwen3-8B | 2 | 1 | 1.54% | 8.16 | 9.27 |
| Qwen3-8B | 4 | 1 | 1.54% | 8.16 | 9.27 |
| Qwen3-8B | 8 | 1 | 1.54% | 8.16 | 9.27 |
| Qwen3-8B | 16 | 1 | 1.54% | 8.16 | 9.27 |
| Qwen3-8B | 32 | 1 | 1.54% | 8.16 | 9.27 |
| Qwen3-8B | 64 | 1 | 1.73% | 9.17 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 72 | 48.08% | 73.78 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 72 | 48.08% | 73.78 | 2.13 |
| DeepSeek-V4-Flash-0731 | 4 | 2 | 2.03% | 4.94 | 2.13 |
| DeepSeek-V4-Flash-0731 | 8 | 2 | 2.03% | 4.94 | 2.13 |
| DeepSeek-V4-Flash-0731 | 16 | 2 | 2.03% | 4.94 | 2.13 |
| DeepSeek-V4-Flash-0731 | 32 | 2 | 2.03% | 4.94 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 382 | 94.78% | 752.06 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 7 | 29.00% | 239.77 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 1,336.2 | 6,680.8 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 1,336.2 | 6,680.8 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 1,336.2 | 6,680.8 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 842.2 | 6,737.6 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 424.1 | 6,785.7 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 212.8 | 6,810.0 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 106.6 | 6,822.2 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 26.7 | 6,831.4 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 515.8 | 20,632.8 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 515.8 | 20,632.8 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 515.8 | 20,632.8 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 515.8 | 20,632.8 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 515.8 | 20,632.8 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 515.8 | 20,632.8 |
| DeepSeek-V4-Flash-0731 | 64 | 3.72% | 13.2 GB | 7.94% | 384.39 TB/s | 4,841.92 TB/s | 329.3 | 21,073.1 |
| DeepSeek-V4-Flash-0731 | 256 | 14.08% | 28.5 GB | 17.07% | 826.74 TB/s | 4,841.92 TB/s | 84.6 | 21,650.6 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 72.7 | 15,265.2 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 72.7 | 15,265.2 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 72.7 | 15,265.2 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 72.7 | 15,265.2 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 72.7 | 15,265.2 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 72.7 | 15,265.2 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 72.7 | 15,265.2 |
| DeepSeek-V4-Pro-0813 | 256 | 1.90% | 42.5 GB | 4.76% | 1,231.77 TB/s | 25,902.15 TB/s | 59.8 | 15,298.0 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | kv_read | 49 |
| gpu | link_latency | 456 |
| gpu | weight_read | 1063 |
| rom | compute | 130 |
| rom | infeasible | 2356 |
| rom | kv_read | 557 |
| rom | link_latency | 1389 |
| rom | weight_read | 1024 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2356 |

## Mechanical consistency audit

**PASS** over 147,797 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 70 |
| derived | 41 |
| assumed | 57 |

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
  2.3-2.9x low on the other.** Leakage, clock distribution, operand
  delivery and a measured clocked-idle floor are charged per mm2 per
  second whether or not a byte moves, and the HBM traffic energy is a
  measured SC 2025 figure rather than an HBM2-era model. The A100 lands
  at 1.15x of its published TDP under a saturating load; the Taalas HC1
  lands at 0.35x of its published card power. **The second one FAILS its
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

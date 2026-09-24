# Area-constrained roofline: n6_vs_a100

> Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 2,263x (ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream, 3,744 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 4 devices. On the GPU side the correction reaches 144x (a100_sxm_80gb-x3694-pipeline, 3,694 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 136 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 7 x 815 mm2 (5,705 mm2, array, KV in SRAM) at 16,794 tok/s per user and 2,944 tok/s per 1,000 mm2, holding 1 session, against 7 copies of one unified HBM die at the same silicon: 30.0x per user. DeepSeek-V4-Flash-0731 takes 44 x 815 mm2 (35,860 mm2, array, KV in SRAM) at 11,585 tok/s per user and 323 tok/s per 1,000 mm2, holding 1 session, against 43 copies of one unified HBM die at the same silicon: 11.9x per user. DeepSeek-V4-Pro-0813 takes 209 x 815 mm2 (170,335 mm2, array, KV in SRAM) at 4,061 tok/s per user and 24 tok/s per 1,000 mm2, holding 1 session, against 206 copies of one unified HBM die at the same silicon: 5.9x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 8,965 mm2 of ROM silicon at 21,556 tok/s per user against 9,086 mm2 of a100_sxm_80gb-x11-tensor at 625 tok/s: **34.5x**, ROM binding on `compute` and the GPU on `weight_read`. It holds 1 resident session against the GPU cluster's 642. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 17.91x to it.** At 254,280 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 39.18 tok/s and the same silicon running tensor delivers 702 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 3.27x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 3,676 to 305,545 tok/s, and its rate with every slot occupied from 290,439 to 305,545. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 79 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,825 us over NVLink, capping per-user decode at 548 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 450.4 us and cap it at 2,220 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 2.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 9 of 30 operating points and an array 21; on tokens per second per square millimetre the same points go 21 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 1271 of 7820 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 66.4x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 16.80x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 48 of 60 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill`** -- 7 x 815 mm2 reticle dies, 5,705 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `rom`.

- **16,794.4 tok/s per user** (0.06 ms/token), binding on `weight_read`
- **2,943.8 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 16,794 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 708 W at 0.124 W/mm2, 42.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 7 copies of one unified HBM die -- `a100_sxm_80gb-x7-tensor`, 5,782 mm2, area ratio 0.9867 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 5,705 | 5,782 | 0.9867 |
| user tok/s | 16,794.4 | 560.0 | 29.99x |
| aggregate tok/s | 16,794 | 560 | 23.80x |
| resident sessions | 1 | 403 | -- |
| J/token | 0.0422 | 3.5278 | 83.7x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 403 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x272-tensor` at 224,672 mm2 and 1,299.7 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 25,281.1 | 1,938.7 | 1 | 33.33x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 25,281.1 | 1,938.7 | 1 | 33.33x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x5` | 4,075 | 8,084.1 | 1,983.8 | 1 | 19.00x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 16,794.4 | 2,943.8 | 1 | 29.99x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 16,794.4 | 2,943.8 | -- | 2,943.8 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 18,226.6 | 2,795.5 | 1,757.4 | 2,943.8 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x11-romfill` | 8,965 | 21,556.0 | 2,404.5 | 1,460.6 | 2,943.8 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x12-romfill` | 9,780 | 22,460.9 | 2,296.6 | 1,390.6 | 2,943.8 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 25,281.1 | 1,938.7 | 1,157.0 | 2,943.8 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` **<-- recommended** | 5,705 | 7 | 16,794.4 | 16,794 | 2,943.8 | 1 | `weight_read` | 708 | 42.2 | `a100_sxm_80gb-x7-tensor` | 29.99x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 8 | 18,226.6 | 18,227 | 2,795.5 | 1 | `compute` | 800 | 43.9 | `a100_sxm_80gb-x8-tensor` | 29.33x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x11-romfill` | 8,965 | 11 | 21,556.0 | 21,556 | 2,404.5 | 1 | `compute` | 1,063 | 49.3 | `a100_sxm_80gb-x11-tensor` | 34.48x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x12-romfill` | 9,780 | 12 | 22,460.9 | 22,461 | 2,296.6 | 1 | `link_latency` | 1,148 | 51.1 | `a100_sxm_80gb-x12-tensor` | 34.24x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 16 | 25,281.1 | 25,281 | 1,938.7 | 1 | `link_latency` | 1,478 | 58.5 | `a100_sxm_80gb-x16-tensor` | 33.33x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 262 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 16,794.4 | 2,943.8 | 1 |
| array | 262 | fastest | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 25,281.1 | 1,938.7 | 1 |
| array | 262 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x5` | 4,075 | 8,084.1 | 1,983.8 | 1 |
| wafer | 52 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 52 | fastest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 52 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 25,281.1 | 25,281 | 1 | 1,478 | 58.5 | `link_latency` | `a100_sxm_80gb-x16-tensor` | 758.6 | 940 | 4,768.3 | 0.987 | 33.33x | 81.6x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 6,464 | 1 | 4,209 | 651.2 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 1,109.0 | 3,324 | 9,013.6 | 0.999 | 5.83x | 13.8x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-tensor-x57-romfill` | 46,455 | 14,851.5 | 14,852 | 1 | 4,340 | 292.2 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 1,109.0 | 3,324 | 9,013.6 | 1.004 | 13.39x | 30.8x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | -- | 1 | -- | 651.2 | -- | -- | -- | -- | -- | 1.005 | 0.44x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill` | 70,905 | 10,992.1 | 21,984 | 5,185 | 10,828 | 492.5 | `link_latency` | `a100_sxm_80gb-x86-tensor` | 1,084.9 | 5,112 | 6,650.1 | 0.998 | 10.13x | 13.5x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x8-romfill` | 369,800 | 5,028.2 | 10,056 | 4,100 | 35,736 | 3,553.6 | `link_latency` | `a100_sxm_80gb-x448-tensor` | 889.3 | 26,689 | 37,297.2 | 0.999 | 5.65x | 10.5x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill` | 70,905 | 9,063.7 | 36,255 | 5,185 | 12,702 | 350.4 | `link_latency` | `a100_sxm_80gb-x86-tensor` | 927.9 | 5,112 | 3,875.4 | 0.998 | 9.77x | 11.1x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x8` | 369,800 | 4,531.9 | 18,127 | 4,100 | 56,716 | 3,128.7 | `link_latency` | `a100_sxm_80gb-x448-tensor` | 783.0 | 26,689 | 21,182.6 | 0.999 | 5.79x | 6.8x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x138` | 112,470 | 7,134.8 | 57,079 | 8,225 | 25,525 | 447.2 | `link_latency` | `a100_sxm_80gb-x136-tensor` | 744.2 | 8,092 | 3,629.2 | 1.001 | 9.59x | 8.1x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 4,325.6 | 34,604 | 4,100 | 39,115 | 1,130.3 | `link_latency` | `a100_sxm_80gb-x448-tensor` | 632.0 | 26,689 | 13,125.3 | 0.999 | 6.84x | 11.6x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x227` | 185,005 | 5,223.1 | 83,569 | 13,530 | 40,776 | 487.9 | `link_latency` | `a100_sxm_80gb-x224-hybrid` | 597.8 | 13,337 | 5,104.2 | 1.000 | 8.74x | 8.5x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,846.9 | 61,551 | 6,151 | 59,918 | 973.5 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 591.2 | 40,040 | 11,980.8 | 0.999 | 6.51x | 12.3x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 5,125.0 | 353,628 | 16,450 | 73,314 | 289.0 | `kv_read` | `a100_sxm_80gb-x272-hybrid` | 592.8 | 16,198 | 3,793.2 | 1.001 | 8.65x | 13.1x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,678.3 | 85,705 | 6,151 | 63,040 | 735.5 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 591.2 | 40,040 | 6,851.9 | 0.999 | 4.53x | 9.3x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 224,940 | 5,125.0 | 353,628 | 16,450 | 73,314 | 212.8 | `kv_read` | `a100_sxm_80gb-x272-hybrid` | 561.3 | 16,198 | 2,070.5 | 1.001 | 9.13x | 9.7x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,666.0 | 106,626 | 6,151 | 95,761 | 898.1 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 591.2 | 40,040 | 4,287.5 | 0.999 | 2.82x | 4.8x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 1,773.0 | 453,901 | 20,265 | 91,388 | 201.3 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 445.0 | 19,953 | 817.6 | 1.001 | 3.98x | 4.1x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 509.8 | 130,521 | 6,151 | 98,849 | 757.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 522.8 | 40,040 | 1,379.0 | 0.999 | 0.98x | 1.8x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 452.2 | 463,094 | 20,265 | 92,616 | 200.0 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 236.5 | 19,953 | 397.0 | 1.001 | 1.91x | 2.0x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 137.6 | 140,866 | 6,151 | 70,609 | 501.2 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 344.7 | 40,040 | 537.4 | 0.999 | 0.40x | 1.1x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 113.4 | 464,336 | 20,265 | 92,239 | 198.6 | `kv_read` | `a100_sxm_80gb-x335-hybrid` | 82.3 | 19,953 | 291.8 | 1.001 | 1.38x | 1.5x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 34.4 | 141,029 | 6,151 | 100,317 | 711.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 145.9 | 40,040 | 326.9 | 0.999 | 0.24x | 0.5x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | array | SRAM | 1 |
| 2 | `ROM-N6-native-HBMKV-array-hw-tensor-x69-romfill` | 56,235 | array | HBM | 4,112 |
| 4-8 | `ROM-N6-native-HBMKV-array-hw-tensor-x69` | 56,235 | array | HBM | 4,112 |
| 16-32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill` | 56,235 | array | HBM | 4,112 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x69` | 56,235 | array | HBM | 4,112 |
| 256-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x69` | 56,235 | array | HBM | 4,112 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Flash-0731 at 200,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x44`** -- 44 x 815 mm2 reticle dies, 35,860 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **11,585.2 tok/s per user** (0.09 ms/token), binding on `link_latency`
- **323.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 11,585 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 2,343 W at 0.065 W/mm2, 202.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 43 copies of one unified HBM die -- `a100_sxm_80gb-x43-tensor`, 35,518 mm2, area ratio 1.0096 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 35,860 | 35,518 | 1.0096 |
| user tok/s | 11,585.2 | 970.3 | 11.94x |
| aggregate tok/s | 11,585 | 970 | 1.91x |
| resident sessions | 1 | 2,120 | -- |
| J/token | 0.2023 | 7.6136 | 37.6x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 2,120 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x312-tensor` at 257,712 mm2 and 1,108.1 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-hybrid-x81` | 66,015 | 13,427.8 | 203.4 | 1 | 12.91x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | 67,645 | 13,876.3 | 205.1 | 1 | 13.32x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x40` | 32,600 | 10,276.9 | 315.2 | 1 | 10.73x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | 11,585.2 | 323.1 | 1 | 11.94x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | 11,585.2 | 323.1 | -- | 323.1 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x53` | 43,195 | 12,597.3 | 291.6 | 138.0 | 323.1 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x54-romfill` | 44,010 | 12,656.0 | 287.6 | 131.4 | 323.1 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x55` | 44,825 | 12,709.3 | 283.5 | 125.4 | 323.1 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 12,801.5 | 275.6 | 114.8 | 323.1 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x64-romfill` | 52,160 | 13,031.6 | 249.8 | 88.7 | 323.1 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | 67,645 | 13,876.3 | 205.1 | 72.1 | 323.1 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x44` **<-- recommended** | 35,860 | 44 | 11,585.2 | 11,585 | 323.1 | 1 | `link_latency` | 2,343 | 202.3 | `a100_sxm_80gb-x43-tensor` | 11.94x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x53` | 43,195 | 53 | 12,597.3 | 12,597 | 291.6 | 1 | `link_latency` | 3,413 | 271.0 | `a100_sxm_80gb-x52-tensor` | 12.65x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x54-romfill` | 44,010 | 54 | 12,656.0 | 12,656 | 287.6 | 1 | `link_latency` | 3,532 | 279.1 | `a100_sxm_80gb-x53-tensor` | 12.68x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x55` | 44,825 | 55 | 12,709.3 | 12,709 | 283.5 | 1 | `link_latency` | 3,651 | 287.2 | `a100_sxm_80gb-x54-tensor` | 12.70x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 57 | 12,801.5 | 12,802 | 275.6 | 1 | `link_latency` | 3,887 | 303.7 | `a100_sxm_80gb-x56-tensor` | 12.74x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x64-romfill` | 52,160 | 64 | 13,031.6 | 13,032 | 249.8 | 1 | `link_latency` | 4,716 | 361.9 | `a100_sxm_80gb-x63-tensor` | 12.80x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | 67,645 | 83 | 13,876.3 | 13,876 | 205.1 | 1 | `compute` | 6,967 | 502.1 | `a100_sxm_80gb-x82-tensor` | 13.32x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 300 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | 11,585.2 | 323.1 | 1 |
| array | 300 | fastest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | 67,645 | 13,876.3 | 205.1 | 1 |
| array | 300 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x40` | 32,600 | 10,276.9 | 315.2 | 1 |
| wafer | 52 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,458.9 | 118.1 | 1 |
| wafer | 52 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,467.3 | 59.1 | 1 |
| wafer | 52 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,458.9 | 118.1 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-hybrid-x83` | 67,645 | 13,876.3 | 13,876 | 1 | 6,967 | 502.1 | `compute` | `a100_sxm_80gb-x82-tensor` | 1,041.9 | 4,152 | 12,578.1 | 0.999 | 13.32x | 25.1x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,467.3 | 5,467 | 1 | 8,305 | 1,519.0 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 1,065.4 | 5,715 | 16,393.0 | 0.999 | 5.13x | 10.8x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x113-romfill` | 92,095 | 11,337.0 | 11,337 | 1 | 8,311 | 733.1 | `compute` | `a100_sxm_80gb-x111-tensor` | 1,064.8 | 5,663 | 16,266.5 | 1.004 | 10.65x | 22.2x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,467.3 | -- | 1 | -- | 1,519.0 | -- | -- | -- | -- | -- | 0.996 | 0.48x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 71,720 | 13,172.6 | 289,796 | 4,585 | 20,024 | 371.4 | `compute` | `a100_sxm_80gb-x87-tensor` | 940.3 | 4,412 | 7,482.4 | 0.998 | 14.01x | 20.1x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 4,970.0 | 49,700 | 4,481 | 44,914 | 4,363.0 | `link_latency` | `a100_sxm_80gb-x560-tensor` | 748.4 | 29,061 | 54,820.6 | 0.999 | 6.64x | 12.6x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 71,720 | 13,172.6 | 289,796 | 4,585 | 20,024 | 205.1 | `compute` | `a100_sxm_80gb-x87-tensor` | 781.7 | 4,412 | 4,607.5 | 0.998 | 16.85x | 22.5x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 4,970.0 | 49,700 | 4,481 | 44,914 | 2,200.9 | `link_latency` | `a100_sxm_80gb-x560-hybrid` | 703.9 | 29,061 | 29,931.0 | 0.999 | 7.06x | 13.6x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 71,720 | 13,172.6 | 289,796 | 4,585 | 20,024 | 122.0 | `compute` | `a100_sxm_80gb-x87-hybrid` | 737.9 | 4,412 | 3,343.1 | 0.998 | 17.85x | 25.8x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 4,970.0 | 49,700 | 4,481 | 44,914 | 1,119.9 | `link_latency` | `a100_sxm_80gb-x560-hybrid` | 703.9 | 29,061 | 15,573.1 | 0.999 | 7.06x | 13.9x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x88` | 71,720 | 13,172.6 | 289,796 | 4,585 | 20,024 | 80.4 | `compute` | `a100_sxm_80gb-x87-hybrid` | 671.8 | 4,412 | 2,126.7 | 0.998 | 19.61x | 26.4x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,787.7 | 76,603 | 5,377 | 54,509 | 711.6 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 703.9 | 34,898 | 9,830.0 | 0.999 | 6.80x | 13.8x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x99` | 80,685 | 11,363.0 | 363,615 | 5,159 | 24,154 | 66.4 | `compute` | `a100_sxm_80gb-x98-hybrid` | 540.9 | 4,986 | 1,541.6 | 0.997 | 21.01x | 23.2x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 4,189.5 | 134,063 | 5,377 | 84,011 | 626.7 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 703.9 | 34,898 | 5,522.6 | 0.999 | 5.95x | 8.8x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 257,540 | 10,757.0 | 849,805 | 16,467 | 61,636 | 80.4 | `compute` | `a100_sxm_80gb-x312-hybrid` | 624.0 | 16,138 | 2,021.6 | 0.999 | 17.24x | 25.1x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,351.8 | 214,517 | 5,377 | 86,912 | 405.1 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 703.9 | 34,898 | 3,368.9 | 0.999 | 4.76x | 8.3x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 4,112.9 | 1,052,891 | 17,717 | 69,982 | 66.5 | `compute` | `a100_sxm_80gb-x335-hybrid` | 346.6 | 17,336 | 1,056.8 | 1.001 | 11.87x | 10.0x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,523.8 | 390,097 | 5,377 | 93,186 | 238.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 493.5 | 34,898 | 1,425.9 | 0.999 | 3.09x | 4.4x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x237` | 193,155 | 1,164.2 | 1,192,140 | 12,350 | 71,876 | 60.3 | `kv_read` | `a100_sxm_80gb-x234-expert` | 212.1 | 11,915 | 207.6 | 0.999 | 5.49x | 3.4x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 519.4 | 531,900 | 5,377 | 71,821 | 135.0 | `kv_read` | `a100_sxm_80gb-x672-expert` | 332.9 | 34,431 | 336.7 | 0.999 | 1.56x | 2.5x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 423.3 | 1,733,692 | 17,717 | 104,633 | 60.4 | `kv_read` | `a100_sxm_80gb-x335-expert` | 129.6 | 17,111 | 131.2 | 1.001 | 3.27x | 2.2x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 130.8 | 535,581 | 5,377 | 98,715 | 184.3 | `kv_read` | `a100_sxm_80gb-x672-expert` | 204.9 | 34,431 | 155.7 | 0.999 | 0.64x | 0.8x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | array | SRAM | 1 |
| 2-16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x79` | 64,385 | array | HBM | 4,116 |
| 32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x99` | 80,685 | array | HBM | 5,159 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x119` | 96,985 | array | HBM | 6,201 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x158` | 128,770 | array | HBM | 8,233 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x158` | 128,770 | array | HBM | 8,233 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Pro-0813 at 1,000,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x209`** -- 209 x 815 mm2 reticle dies, 170,335 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **4,061.3 tok/s per user** (0.25 ms/token), binding on `link_latency`
- **23.8 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,061 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 10,573 W at 0.062 W/mm2, 2,603.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 206 copies of one unified HBM die -- `a100_sxm_80gb-x206-tensor`, 170,156 mm2, area ratio 1.0011 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 170,335 | 170,156 | 1.0011 |
| user tok/s | 4,061.3 | 683.5 | 5.94x |
| aggregate tok/s | 4,061 | 683 | 0.50x |
| resident sessions | 1 | 1,414 | -- |
| J/token | 2.6033 | 47.9341 | 18.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,414 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x308-tensor` at 254,408 mm2 and 701.7 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 185,005 | 4,341.7 | 23.5 | 1 | 6.31x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | 193,155 | 4,414.2 | 22.9 | 1 | 6.40x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x209` | 170,335 | 4,061.3 | 23.8 | 1 | 5.94x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x209` | 170,335 | 4,061.3 | 23.8 | 1 | 5.94x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x209` | 170,335 | 4,061.3 | 23.8 | -- | 23.8 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 185,005 | 4,341.7 | 23.5 | 19.1 | 23.8 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x236` | 192,340 | 4,408.3 | 22.9 | 15.8 | 23.8 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | 193,155 | 4,414.2 | 22.9 | 15.5 | 23.8 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x209` **<-- recommended** | 170,335 | 209 | 4,061.3 | 4,061 | 23.8 | 1 | `link_latency` | 10,573 | 2,603.3 | `a100_sxm_80gb-x206-tensor` | 5.94x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 185,005 | 227 | 4,341.7 | 4,342 | 23.5 | 1 | `link_latency` | 11,481 | 2,644.4 | `a100_sxm_80gb-x224-tensor` | 6.31x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x236` | 192,340 | 236 | 4,408.3 | 4,408 | 22.9 | 1 | `link_latency` | 12,242 | 2,777.0 | `a100_sxm_80gb-x233-tensor` | 6.39x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | 193,155 | 237 | 4,414.2 | 4,414 | 22.9 | 1 | `link_latency` | 12,360 | 2,800.1 | `a100_sxm_80gb-x234-tensor` | 6.40x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 120 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x209` | 170,335 | 4,061.3 | 23.8 | 1 |
| array | 120 | fastest | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | 193,155 | 4,414.2 | 22.9 | 1 |
| array | 120 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x209` | 170,335 | 4,061.3 | 23.8 | 1 |
| wafer | 39 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | 184,900 | 3,349.4 | 18.1 | 1 |
| wafer | 39 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 3,649.0 | 8.8 | 1 |
| wafer | 39 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x4` | 184,900 | 3,349.4 | 18.1 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-tensor-x237` | 193,155 | 4,414.2 | 4,414 | 1 | 12,360 | 2,800.1 | `link_latency` | `a100_sxm_80gb-x234-tensor` | 689.9 | 1,618 | 53,387.9 | 0.999 | 6.40x | 19.1x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x9` | 416,025 | 3,649.0 | 3,649 | 1 | 44,653 | 12,237.1 | `link_latency` | `a100_sxm_80gb-x504-tensor` | 529.0 | 3,591 | 141,980.4 | 0.999 | 6.90x | 11.6x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 2,415.3 | 159,412 | 4,146 | 475,762 | 90,296.5 | `link_latency` | `a100_sxm_80gb-x3694-tensor` | 481.5 | 26,894 | 556,885.9 | 1.000 | 5.02x | 6.2x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 2,415.3 | 159,412 | 4,146 | 475,762 | 45,276.2 | `link_latency` | `a100_sxm_80gb-x3694-tensor` | 395.1 | 26,894 | 339,781.8 | 1.000 | 6.11x | 7.5x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 2,415.3 | 159,412 | 4,146 | 475,762 | 22,766.1 | `link_latency` | `a100_sxm_80gb-x3694-tensor` | 290.8 | 26,894 | 231,175.0 | 1.000 | 8.31x | 10.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 2,415.3 | 159,412 | 4,146 | 475,762 | 11,511.0 | `link_latency` | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 26,894 | 136,757.3 | 1.000 | 9.59x | 11.9x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 2,415.3 | 159,412 | 4,146 | 475,762 | 5,883.5 | `link_latency` | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 26,894 | 70,586.9 | 1.000 | 9.59x | 12.0x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 2,415.3 | 159,412 | 4,146 | 475,762 | 3,069.7 | `link_latency` | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 26,894 | 37,501.7 | 1.000 | 9.59x | 12.2x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 1,160.3 | 297,033 | 4,146 | 509,131 | 1,714.1 | `kv_read` | `a100_sxm_80gb-x3694-hybrid` | 251.9 | 26,894 | 12,687.8 | 1.000 | 4.61x | 7.4x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | 374.2 | 383,226 | 4,146 | 529,911 | 1,382.8 | `kv_read` | `a100_sxm_80gb-x3694-hybrid` | 185.3 | 26,894 | 5,667.2 | 1.000 | 2.02x | 2.7x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 3,050,850 | 103.4 | 423,553 | 4,146 | 543,073 | 1,282.2 | `kv_read` | `a100_sxm_80gb-x3694-expert` | 121.8 | 25,642 | 1,337.8 | 1.000 | 0.85x | 1.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x209` | 170,335 | array | SRAM | 1 |
| 2-1024 | `ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3,050,850 | wafer | HBM | 4,146 |
| 4096 | `ROM-N6-native-HBMKV-wafer-pipeline-x66` | 3,050,850 | wafer | HBM | 4,146 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 79, 99, 113, 119, 158, 170, 227, 237, 316, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 79, 87, 88, 99, 113, 119, 158, 170, 227, 237, 316, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 40, 44, 53, 54, 57, 64, 70, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 40, 44, 53, 55, 57, 70, 81, 82, 83, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 209, 227, 236, 237, 284, 312, 340, 341, 343, 378 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 209, 227, 236, 237, 284, 328, 340, 378, 391, 392 |
| Qwen3-8B | HBM | rom | 69, 71, 82, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| Qwen3-8B | HBM | sram | 69, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| Qwen3-8B | SRAM | rom | 5, 6, 7, 8, 11, 12, 16, 57, 113, 170, 227, 340 |
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

- **0 of 7,820 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 351 | 0 | 69.3% | 80.7% | 0.391 | 52% |
| gpu | small array (1,600-5,000 mm2) | 60 | 0 | 79.5% | 80.8% | 0.392 | 45% |
| gpu | wafer (>=40,000 mm2) | 2,588 | 0 | 64.4% | 80.7% | 0.391 | 56% |
| rom | large array (5,000-40,000 mm2) | 146 | 0 | 13.2% | 27.2% | 0.136 | 98% |
| rom | small array (1,600-5,000 mm2) | 56 | 0 | 19.7% | 40.6% | 0.203 | 70% |
| rom | wafer (>=40,000 mm2) | 4,619 | 0 | 32.2% | 76.5% | 0.383 | 76% |

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
| DeepSeek-V4-Flash-0731 | 1 | 66,015 | `DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x81` | 0.501024 | 6,727.7 | compute | `DSV4-Flash/a100_sxm_80gb-x80-tensor` | 12.316686 | 12,815.1 | link_latency | 24.58x |
| DeepSeek-V4-Flash-0731 | 2 | 70,905 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 0.371449 | 19,718.8 | compute | `DSV4-Flash/a100_sxm_80gb-x86-tensor` | 7.413240 | 13,924.8 | link_latency | 19.96x |
| DeepSeek-V4-Flash-0731 | 4 | 70,905 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 0.205160 | 19,718.8 | compute | `DSV4-Flash/a100_sxm_80gb-x86-tensor` | 4.566945 | 14,260.1 | link_latency | 22.26x |
| DeepSeek-V4-Flash-0731 | 8 | 70,905 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 0.122015 | 19,718.8 | compute | `DSV4-Flash/a100_sxm_80gb-x86-hybrid` | 3.334574 | 22,206.5 | weight_read | 25.59x |
| DeepSeek-V4-Flash-0731 | 16 | 70,905 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x87` | 0.080443 | 19,718.8 | compute | `DSV4-Flash/a100_sxm_80gb-x86-hybrid` | 2.122404 | 22,634.8 | weight_read | 26.38x |
| DeepSeek-V4-Flash-0731 | 32 | 80,685 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x99` | 0.066429 | 24,154.4 | compute | `DSV4-Flash/a100_sxm_80gb-x98-hybrid` | 1.541616 | 26,685.6 | weight_read | 23.21x |
| DeepSeek-V4-Flash-0731 | 64 | 257,540 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill` | 0.080418 | 61,635.7 | compute | `DSV4-Flash/a100_sxm_80gb-x312-hybrid` | 2.021559 | 80,729.5 | weight_read | 25.14x |
| DeepSeek-V4-Flash-0731 | 256 | 277,100 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.066467 | 69,982.1 | compute | `DSV4-Flash/a100_sxm_80gb-x335-hybrid` | 1.056823 | 93,765.6 | weight_read | 10.02x |
| DeepSeek-V4-Flash-0731 | 1024 | 185,005 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 0.060150 | 68,737.4 | kv_read | `DSV4-Flash/a100_sxm_80gb-x224-expert` | 0.204551 | 43,372.2 | weight_read | 3.40x |
| DeepSeek-V4-Flash-0731 | 4096 | 277,100 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.060353 | 104,632.7 | kv_read | `DSV4-Flash/a100_sxm_80gb-x335-expert` | 0.131244 | 69,643.1 | compute | 2.17x |
| DeepSeek-V4-Pro-0813 | 1 | 185,005 | `DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227` | 2.644366 | 11,481.1 | link_latency | `DSV4-Pro/a100_sxm_80gb-x224-tensor` | 51.435387 | 35,379.9 | link_latency | 19.45x |
| DeepSeek-V4-Pro-0813 | 2 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 90.296455 | 475,762.2 | link_latency | `DSV4-Pro/a100_sxm_80gb-x3694-tensor` | 556.885868 | 536,240.1 | link_latency | 6.17x |
| DeepSeek-V4-Pro-0813 | 4 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 45.276218 | 475,762.2 | link_latency | `DSV4-Pro/a100_sxm_80gb-x3694-tensor` | 339.781793 | 536,943.2 | link_latency | 7.50x |
| DeepSeek-V4-Pro-0813 | 8 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 22.766099 | 475,762.2 | link_latency | `DSV4-Pro/a100_sxm_80gb-x3694-tensor` | 231.175038 | 537,723.3 | link_latency | 10.15x |
| DeepSeek-V4-Pro-0813 | 16 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 11.511040 | 475,762.2 | link_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 136.757271 | 1,047,306.7 | weight_read | 11.88x |
| DeepSeek-V4-Pro-0813 | 32 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 5.883510 | 475,762.2 | link_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 70.586883 | 1,047,306.7 | weight_read | 12.00x |
| DeepSeek-V4-Pro-0813 | 64 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 3.069745 | 475,762.2 | link_latency | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 37.501689 | 1,047,306.7 | weight_read | 12.22x |
| DeepSeek-V4-Pro-0813 | 256 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1.714055 | 509,131.0 | kv_read | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 12.687794 | 1,047,306.7 | weight_read | 7.40x |
| DeepSeek-V4-Pro-0813 | 1024 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66` | 1.382767 | 529,911.5 | kv_read | `DSV4-Pro/a100_sxm_80gb-x3694-hybrid` | 5.667241 | 1,075,350.5 | weight_read | 2.75x |
| DeepSeek-V4-Pro-0813 | 4096 | 3,050,850 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66` | 1.282184 | 543,073.2 | kv_read | `DSV4-Pro/a100_sxm_80gb-x3694-expert` | 1.337810 | 667,542.1 | weight_read | 1.04x |
| Qwen3-8B | 1 | 13,040 | `Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill` | 0.058450 | 1,477.7 | link_latency | `Qwen3-8B/a100_sxm_80gb-x16-tensor` | 4.768287 | 3,617.2 | link_latency | 81.58x |
| Qwen3-8B | 2 | 56,235 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x69-romfill` | 0.432061 | 9,063.4 | link_latency | `Qwen3-8B/a100_sxm_80gb-x68-tensor` | 5.598873 | 11,767.5 | link_latency | 12.96x |
| Qwen3-8B | 4 | 66,830 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x82-romfill` | 0.341671 | 12,162.0 | link_latency | `Qwen3-8B/a100_sxm_80gb-x81-tensor` | 3.706220 | 13,645.5 | link_latency | 10.85x |
| Qwen3-8B | 8 | 112,470 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x138` | 0.447188 | 25,524.9 | link_latency | `Qwen3-8B/a100_sxm_80gb-x136-tensor` | 3.629176 | 21,606.0 | link_latency | 8.12x |
| Qwen3-8B | 16 | 56,235 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill` | 0.215207 | 18,473.4 | kv_read | `Qwen3-8B/a100_sxm_80gb-x68-hybrid` | 2.120440 | 19,038.5 | weight_read | 6.94x |
| Qwen3-8B | 32 | 112,470 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x138-romfill` | 0.213831 | 36,691.3 | kv_read | `Qwen3-8B/a100_sxm_80gb-x136-hybrid` | 2.042860 | 37,643.0 | weight_read | 9.55x |
| Qwen3-8B | 64 | 224,940 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill` | 0.212838 | 73,313.6 | kv_read | `Qwen3-8B/a100_sxm_80gb-x272-hybrid` | 2.070471 | 74,376.4 | weight_read | 9.73x |
| Qwen3-8B | 256 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.201340 | 91,388.4 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.817605 | 93,138.8 | weight_read | 4.06x |
| Qwen3-8B | 1024 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.199994 | 92,616.0 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.396960 | 96,135.0 | kv_read | 1.98x |
| Qwen3-8B | 4096 | 277,100 | `Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.198648 | 92,239.4 | kv_read | `Qwen3-8B/a100_sxm_80gb-x335-hybrid` | 0.291799 | 98,351.3 | kv_read | 1.47x |

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
| Qwen3-8B | 2 | 92,450 | 46,513.8 | wafer-pipeline | 6,019.4 | wafer-hybrid | 7.73x | 5,465.8 | pipeline | 1,221.9 | tensor | 4.47x | 8.51x | 4.93x | 0.58x |
| Qwen3-8B | 3 | 138,675 | 46,513.8 | wafer-pipeline | 5,822.1 | wafer-tensor | 7.99x | 6,514.5 | pipeline | 1,264.8 | tensor | 5.15x | 7.14x | 4.60x | 0.64x |
| Qwen3-8B | 4 | 184,900 | 46,513.8 | wafer-pipeline | 5,821.2 | wafer-tensor | 7.99x | 7,205.8 | pipeline | 1,287.4 | tensor | 5.60x | 6.46x | 4.52x | 0.70x |
| Qwen3-8B | 6 | 277,350 | 46,513.8 | wafer-pipeline | 5,329.1 | wafer-tensor | 8.73x | 8,061.3 | pipeline | 947.7 | tensor | 8.51x | 5.77x | 5.62x | 0.97x |
| Qwen3-8B | 8 | 369,800 | 46,513.8 | wafer-pipeline | 5,328.7 | wafer-tensor | 8.73x | 8,570.0 | pipeline | 954.0 | tensor | 8.98x | 5.43x | 5.59x | 1.03x |
| Qwen3-8B | 12 | 554,700 | 54,699.2 | wafer-pipeline | 4,992.6 | wafer-tensor | 10.96x | 9,147.2 | pipeline | 960.4 | tensor | 9.52x | 5.98x | 5.20x | 0.87x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 43,695.8 | wafer-pipeline | 5,458.9 | wafer-tensor | 8.00x | 4,125.2 | pipeline | 1,005.1 | tensor | 4.10x | 10.59x | 5.43x | 0.51x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 49,816.3 | wafer-pipeline | 5,467.3 | wafer-hybrid | 9.11x | 5,554.0 | pipeline | 1,065.4 | tensor | 5.21x | 8.97x | 5.13x | 0.57x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 49,973.2 | wafer-pipeline | 5,398.1 | wafer-hybrid | 9.26x | 6,278.9 | pipeline | 1,087.2 | tensor | 5.78x | 7.96x | 4.97x | 0.62x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 49,973.2 | wafer-pipeline | 5,327.1 | wafer-hybrid | 9.38x | 6,717.2 | pipeline | 1,098.4 | tensor | 6.12x | 7.44x | 4.85x | 0.65x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 49,973.2 | wafer-pipeline | 5,190.6 | wafer-hybrid | 9.63x | 7,221.4 | pipeline | 799.9 | tensor | 9.03x | 6.92x | 6.49x | 0.94x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 49,973.2 | wafer-pipeline | 5,060.8 | wafer-hybrid | 9.87x | 7,502.9 | pipeline | 802.9 | tensor | 9.34x | 6.66x | 6.30x | 0.95x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 51,267.2 | wafer-pipeline | 4,965.0 | wafer-hybrid | 10.33x | 7,807.3 | pipeline | 805.9 | tensor | 9.69x | 6.57x | 6.16x | 0.94x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 22,886.0 | wafer-pipeline | 3,349.4 | wafer-tensor | 6.83x | 3,520.5 | pipeline | 687.9 | tensor | 5.12x | 6.50x | 4.87x | 0.75x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 33,519.5 | wafer-pipeline | 3,552.9 | wafer-hybrid | 9.43x | 4,059.7 | pipeline | 522.5 | tensor | 7.77x | 8.26x | 6.80x | 0.82x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 35,963.1 | wafer-pipeline | 3,637.1 | wafer-hybrid | 9.89x | 4,396.4 | pipeline | 527.3 | tensor | 8.34x | 8.18x | 6.90x | 0.84x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 36,506.2 | wafer-pipeline | 3,555.2 | wafer-hybrid | 10.27x | 4,794.0 | pipeline | 532.3 | tensor | 9.01x | 7.61x | 6.68x | 0.88x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.44x to 1.03x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill | 13,040 | 25,281.1 | 25,281.1 | link_latency | Qwen3-8B/a100_sxm_80gb-x16-tensor | 13,216 | 0.99x | tensor | 692.87 | 758.6 | 758.6 | link_latency | 33.33x | 15.71x | 251.32x | 33.33x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x5 | 4,075 | 8,084.1 | 8,084.1 | compute | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 364.72 | 425.4 | 425.4 | weight_read | 19.00x | 16.03x | 80.14x | 19.00x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill | 70,905 | 10,992.1 | 21,984.1 | link_latency | Qwen3-8B/a100_sxm_80gb-x86-tensor | 71,036 | 1.00x | tensor | 791.33 | 1,084.9 | 2,169.8 | link_latency | 10.13x | 2.55x | 109.82x | 10.13x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x69-romfill | 56,235 | 10,488.6 | 20,977.2 | link_latency | Qwen3-8B/a100_sxm_80gb-x68-tensor | 56,168 | 1.00x | tensor | 788.47 | 1,050.9 | 2,101.8 | link_latency | 9.98x | 3.08x | 104.79x | 9.98x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x87-romfill | 70,905 | 9,063.7 | 36,254.7 | link_latency | Qwen3-8B/a100_sxm_80gb-x86-tensor | 71,036 | 1.00x | tensor | 930.34 | 927.9 | 3,711.4 | link_latency | 9.77x | 4.21x | 90.56x | 9.77x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x69 | 56,235 | 8,398.8 | 33,595.3 | link_latency | Qwen3-8B/a100_sxm_80gb-x68-tensor | 56,168 | 1.00x | tensor | 924.62 | 901.5 | 3,606.0 | link_latency | 9.32x | 4.94x | 83.91x | 9.32x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x138 | 112,470 | 7,134.8 | 57,078.7 | link_latency | Qwen3-8B/a100_sxm_80gb-x136-tensor | 112,336 | 1.00x | tensor | 1,226.53 | 744.2 | 5,953.4 | link_latency | 9.59x | 4.19x | 71.28x | 9.59x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x69 | 56,235 | 6,005.7 | 48,045.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-tensor | 56,168 | 1.00x | tensor | 1,196.92 | 702.0 | 5,615.7 | link_latency | 8.56x | 7.06x | 60.00x | 8.56x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x227 | 185,005 | 5,223.1 | 83,569.2 | link_latency | Qwen3-8B/a100_sxm_80gb-x224-hybrid | 185,024 | 1.00x | hybrid | 428.82 | 597.8 | 16,739.4 | weight_read | 8.74x | 3.73x | 52.18x | 8.74x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 4,970.4 | 89,468.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 390.08 | 561.2 | 8,978.6 | weight_read | 8.86x | 9.96x | 49.66x | 8.86x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 5,125.0 | 353,628.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 442.96 | 592.8 | 20,156.0 | weight_read | 8.65x | 12.99x | 51.20x | 8.65x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 2,857.8 | 91,448.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 403.91 | 508.1 | 16,260.4 | weight_read | 5.62x | 5.62x | 28.55x | 5.62x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 5,125.0 | 353,628.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x272-hybrid | 224,672 | 1.00x | hybrid | 457.06 | 561.3 | 35,922.5 | weight_read | 9.13x | 9.84x | 51.20x | 9.13x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69 | 56,235 | 1,449.5 | 92,768.6 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 431.58 | 427.4 | 27,352.0 | weight_read | 3.39x | 3.39x | 14.48x | 3.39x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 1,773.0 | 453,900.6 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 532.41 | 445.0 | 113,916.6 | weight_read | 3.98x | 3.98x | 17.71x | 4.03x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | 56,235 | 367.4 | 94,044.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 597.61 | 218.8 | 56,002.2 | kv_read | 1.68x | 1.68x | 4.42x | 1.68x |
| Qwen3-8B | 1024 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 452.2 | 463,094.0 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 836.50 | 236.5 | 242,178.1 | kv_read | 1.91x | 1.91x | 5.20x | 1.94x |
| Qwen3-8B | 1024 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | 56,235 | 92.0 | 94,248.8 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-hybrid | 56,168 | 1.00x | hybrid | 1,261.70 | 74.1 | 75,869.9 | kv_read | 1.24x | 1.24x | 1.87x | 1.24x |
| Qwen3-8B | 4096 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 113.4 | 464,336.4 | kv_read | Qwen3-8B/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 2,052.85 | 82.3 | 337,051.9 | kv_read | 1.38x | 1.38x | 2.07x | 1.40x |
| Qwen3-8B | 4096 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | 56,235 | 23.0 | 94,300.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x68-pipeline | 56,168 | 1.00x | pipeline | 215.56 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x83 | 67,645 | 13,876.3 | 13,876.3 | compute | DSV4-Flash/a100_sxm_80gb-x82-tensor | 67,732 | 1.00x | tensor | 862.18 | 1,041.9 | 1,041.9 | link_latency | 13.32x | 1.20x | 98.55x | 13.32x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x40 | 32,600 | 10,276.9 | 10,276.9 | link_latency | DSV4-Flash/a100_sxm_80gb-x39-tensor | 32,214 | 1.01x | tensor | 852.96 | 957.5 | 957.5 | link_latency | 10.73x | 1.87x | 72.88x | 10.73x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x88 | 71,720 | 13,172.6 | 289,796.2 | compute | DSV4-Flash/a100_sxm_80gb-x87-tensor | 71,862 | 1.00x | tensor | 945.20 | 940.3 | 1,880.5 | link_latency | 14.01x | 23.66x | 93.55x | 14.01x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 12,216.4 | 244,327.8 | compute | DSV4-Flash/a100_sxm_80gb-x78-tensor | 64,428 | 1.00x | tensor | 943.66 | 930.9 | 1,861.8 | link_latency | 13.12x | 22.25x | 86.76x | 13.12x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x88 | 71,720 | 13,172.6 | 289,796.2 | compute | DSV4-Flash/a100_sxm_80gb-x87-tensor | 71,862 | 1.00x | tensor | 1,111.24 | 781.7 | 3,126.9 | link_latency | 16.85x | 23.66x | 93.55x | 16.85x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 12,216.4 | 244,327.8 | compute | DSV4-Flash/a100_sxm_80gb-x78-tensor | 64,428 | 1.00x | tensor | 1,108.17 | 772.7 | 3,090.9 | link_latency | 15.81x | 22.25x | 86.76x | 15.81x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x88 | 71,720 | 13,172.6 | 289,796.2 | compute | DSV4-Flash/a100_sxm_80gb-x87-hybrid | 71,862 | 1.00x | hybrid | 459.74 | 737.9 | 8,116.9 | weight_read | 17.85x | 23.66x | 93.55x | 17.85x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 12,216.4 | 244,327.8 | compute | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 457.38 | 732.5 | 7,325.0 | weight_read | 16.68x | 22.25x | 86.76x | 16.68x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x88 | 71,720 | 13,172.6 | 289,796.2 | compute | DSV4-Flash/a100_sxm_80gb-x87-hybrid | 71,862 | 1.00x | hybrid | 464.03 | 671.8 | 10,749.0 | weight_read | 19.61x | 23.66x | 93.55x | 19.61x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 12,216.4 | 244,327.8 | compute | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 462.85 | 648.1 | 10,368.9 | weight_read | 18.85x | 22.25x | 86.76x | 18.85x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x99 | 80,685 | 11,363.0 | 363,615.0 | compute | DSV4-Flash/a100_sxm_80gb-x98-hybrid | 80,948 | 1.00x | hybrid | 479.21 | 540.9 | 17,310.2 | weight_read | 21.01x | 21.01x | 80.70x | 21.01x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 8,239.7 | 263,669.8 | compute | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 477.43 | 498.3 | 15,947.1 | weight_read | 16.53x | 16.53x | 58.52x | 16.53x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill | 257,540 | 10,757.0 | 849,805.0 | compute | DSV4-Flash/a100_sxm_80gb-x312-hybrid | 257,712 | 1.00x | hybrid | 537.69 | 624.0 | 39,934.3 | weight_read | 17.24x | 19.34x | 76.40x | 17.24x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79 | 64,385 | 4,410.8 | 282,292.8 | compute | DSV4-Flash/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 506.60 | 346.2 | 22,156.3 | weight_read | 12.74x | 12.74x | 31.33x | 12.74x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 4,112.9 | 1,052,890.8 | compute | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 632.69 | 346.6 | 88,724.0 | weight_read | 11.87x | 11.87x | 29.21x | 11.87x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79 | 64,385 | 1,175.5 | 300,927.9 | compute | DSV4-Flash/a100_sxm_80gb-x78-expert | 64,428 | 1.00x | expert | 1,334.86 | 184.6 | 47,258.0 | weight_read | 6.37x | 6.37x | 14.26x | 6.37x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x237 | 193,155 | 1,164.2 | 1,192,139.8 | kv_read | DSV4-Flash/a100_sxm_80gb-x234-expert | 193,284 | 1.00x | expert | 1,562.17 | 212.1 | 217,215.0 | weight_read | 5.49x | 5.49x | 16.83x | 5.49x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79 | 64,385 | 297.5 | 304,610.6 | compute | DSV4-Flash/a100_sxm_80gb-x78-expert | 64,428 | 1.00x | expert | 3,525.72 | 105.2 | 107,730.5 | compute | 2.83x | 2.83x | 9.29x | 2.83x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 423.3 | 1,733,692.1 | kv_read | DSV4-Flash/a100_sxm_80gb-x335-expert | 276,710 | 1.00x | expert | 3,287.78 | 129.6 | 530,636.9 | compute | 3.27x | 3.27x | 12.54x | 3.27x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79 | 64,385 | 74.6 | 305,545.3 | compute | DSV4-Flash/a100_sxm_80gb-x78-pipeline | 64,428 | 1.00x | pipeline | 241.74 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x237 | 193,155 | 4,414.2 | 4,414.2 | link_latency | DSV4-Pro/a100_sxm_80gb-x234-tensor | 193,284 | 1.00x | tensor | 1,323.51 | 689.9 | 689.9 | link_latency | 6.40x | 0.48x | 112.67x | 6.40x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x209 | 170,335 | 4,061.3 | 4,061.3 | link_latency | DSV4-Pro/a100_sxm_80gb-x206-tensor | 170,156 | 1.00x | tensor | 1,322.43 | 683.5 | 683.5 | link_latency | 5.94x | 0.50x | 103.66x | 5.94x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 159,412.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x3694-tensor | 3,051,244 | 1.00x | tensor | 2,050.10 | 481.5 | 962.9 | link_latency | 5.02x | 1.10x | 61.65x | 5.02x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 159,412.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x3694-tensor | 3,051,244 | 1.00x | tensor | 2,499.55 | 395.1 | 1,580.3 | link_latency | 6.11x | 1.10x | 61.65x | 6.11x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 159,412.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x3694-tensor | 3,051,244 | 1.00x | tensor | 3,398.47 | 290.8 | 2,326.0 | link_latency | 8.31x | 1.10x | 61.65x | 8.31x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 159,412.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 781.51 | 251.9 | 116,371.0 | weight_read | 9.59x | 1.10x | 61.65x | 12.11x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 159,412.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 781.51 | 251.9 | 116,371.0 | weight_read | 9.59x | 1.10x | 61.65x | 12.11x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 159,412.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 781.51 | 251.9 | 116,371.0 | weight_read | 9.59x | 1.10x | 61.65x | 12.11x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,160.3 | 297,033.1 | kv_read | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 781.51 | 251.9 | 116,371.0 | weight_read | 4.61x | 2.05x | 29.62x | 5.82x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 374.2 | 383,225.5 | kv_read | DSV4-Pro/a100_sxm_80gb-x3694-hybrid | 3,051,244 | 1.00x | hybrid | 841.98 | 185.3 | 189,748.5 | weight_read | 2.02x | 2.02x | 9.55x | 2.52x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 103.4 | 423,553.1 | kv_read | DSV4-Pro/a100_sxm_80gb-x3694-expert | 3,051,244 | 1.00x | expert | 1,459.07 | 121.8 | 498,981.2 | weight_read | 0.85x | 0.85x | 2.74x | 0.85x |

## The headline is a band, and each side's share of it is reported apart

Every hop latency in this model states a range, and the ratio moves inside it.
This table re-runs the whole study at both ends of those ranges three ways:
the **wafer fabric** alone (`on_wafer`, `rom_wafer_serdes`), which no GPU design touches; the
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
| DeepSeek-V4-Flash-0731 | 32,600 | 10.73x | 10.73x → 10.73x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 35,860 | 11.94x | 11.94x → 11.94x | 8.69x → 33.32x | 14.69x → 16.50x | 3.8x |
| DeepSeek-V4-Flash-0731 | 43,195 | 12.65x | 12.65x → 12.65x | 9.12x → 36.08x | 16.41x → 23.95x | 4.0x |
| DeepSeek-V4-Flash-0731 | 44,010 | 12.68x | 12.68x → 12.68x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 44,825 | 12.70x | 12.70x → 12.70x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 46,225 | 5.43x | 8.51x → 3.09x | 3.90x → 15.27x | 6.11x → 8.69x | 3.9x |
| DeepSeek-V4-Flash-0731 | 46,455 | 12.74x | 12.74x → 12.74x | 9.15x → 35.81x | 16.67x → 25.95x | 3.9x |
| DeepSeek-V4-Flash-0731 | 52,160 | 12.80x | 12.80x → 12.80x | 9.15x → 36.92x | 16.93x → 30.92x | 4.0x |
| DeepSeek-V4-Flash-0731 | 57,050 | 11.96x | 11.96x → 11.96x | 8.52x → 35.36x | 14.36x → 32.94x | 4.2x |
| DeepSeek-V4-Flash-0731 | 64,385 | 11.77x | 11.77x → 11.77x | 8.34x → 35.26x | 14.24x → 32.75x | 4.2x |
| DeepSeek-V4-Flash-0731 | 66,015 | 12.91x | 12.91x → 12.91x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 66,830 | 13.12x | 13.12x → 13.12x | 9.29x → 40.44x | 14.36x → 37.17x | 4.4x |
| DeepSeek-V4-Flash-0731 | 67,645 | 13.32x | 13.32x → 13.32x | 9.43x → 40.94x | 14.35x → 37.58x | 4.3x |
| DeepSeek-V4-Flash-0731 | 70,905 | 12.40x | 12.40x → 12.40x | 8.76x → 37.70x | 14.24x → 34.73x | 4.3x |
| DeepSeek-V4-Flash-0731 | 71,720 | 12.58x | 12.58x → 12.58x | 8.88x → 38.15x | 14.23x → 35.11x | 4.3x |
| DeepSeek-V4-Flash-0731 | 80,685 | 11.64x | 11.64x → 11.64x | 8.19x → 36.68x | 14.10x → 33.76x | 4.5x |
| DeepSeek-V4-Flash-0731 | 85,575 | 10.87x | 10.87x → 10.87x | 7.64x → 33.80x | 12.08x → 31.16x | 4.4x |
| DeepSeek-V4-Flash-0731 | 92,095 | 10.65x | 10.65x → 10.65x | 7.47x → 33.57x | 12.04x → 30.90x | 4.5x |
| DeepSeek-V4-Flash-0731 | 92,450 | 5.13x | 8.05x → 3.13x | 3.60x → 16.15x | 5.64x → 9.84x | 4.5x |
| DeepSeek-V4-Flash-0731 | 96,985 | 10.15x | 10.15x → 10.15x | 7.11x → 32.51x | 11.98x → 29.98x | 4.6x |
| DeepSeek-V4-Flash-0731 | 114,100 | 9.20x | 9.20x → 9.20x | 6.42x → 30.52x | 11.85x → 28.14x | 4.8x |
| DeepSeek-V4-Flash-0731 | 128,770 | 9.86x | 9.86x → 9.86x | 6.86x → 33.23x | 10.41x → 30.23x | 4.8x |
| DeepSeek-V4-Flash-0731 | 138,550 | 9.80x | 9.80x → 9.80x | 6.81x → 33.14x | 10.38x → 30.02x | 4.9x |
| DeepSeek-V4-Flash-0731 | 138,675 | 4.97x | 7.74x → 2.62x | 3.45x → 16.79x | 5.38x → 8.86x | 4.9x |
| DeepSeek-V4-Flash-0731 | 184,900 | 4.85x | 7.50x → 2.57x | 3.36x → 17.40x | 5.19x → 9.23x | 5.2x |
| DeepSeek-V4-Flash-0731 | 185,005 | 9.76x | 9.76x → 9.76x | 6.75x → 35.01x | 9.17x → 31.70x | 5.2x |
| DeepSeek-V4-Flash-0731 | 193,155 | 9.68x | 9.68x → 9.68x | 6.70x → 35.50x | 9.16x → 32.16x | 5.3x |
| DeepSeek-V4-Flash-0731 | 257,540 | 9.71x | 9.71x → 9.71x | 6.69x → 37.77x | 8.19x → 34.19x | 5.6x |
| DeepSeek-V4-Flash-0731 | 277,100 | 13.45x | 13.45x → 13.45x | 10.19x → 38.52x | 11.35x → 34.87x | 3.8x |
| DeepSeek-V4-Flash-0731 | 277,350 | 6.49x | 9.91x → 3.48x | 4.92x → 18.58x | 7.51x → 9.97x | 3.8x |
| DeepSeek-V4-Flash-0731 | 369,800 | 6.30x | 9.62x → 3.42x | 4.77x → 18.22x | 7.28x → 9.89x | 3.8x |
| DeepSeek-V4-Flash-0731 | 462,250 | 6.18x | 9.24x → 3.38x | 4.67x → 17.90x | 6.99x → 9.78x | 3.8x |
| DeepSeek-V4-Flash-0731 | 554,700 | 6.16x | 9.22x → 3.37x | 4.66x → 17.88x | 6.97x → 9.77x | 3.8x |
| DeepSeek-V4-Pro-0813 | 170,335 | 5.94x | 5.94x → 5.94x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 184,900 | 4.87x | 7.71x → 2.58x | 3.54x → 21.18x | 5.60x → 11.24x | 6.0x |
| DeepSeek-V4-Pro-0813 | 185,005 | 6.31x | 6.31x → 6.31x | 4.59x → 27.46x | 9.11x → 12.23x | 6.0x |
| DeepSeek-V4-Pro-0813 | 192,340 | 6.39x | 6.39x → 6.39x | 4.64x → 28.50x | — | 6.1x |
| DeepSeek-V4-Pro-0813 | 193,155 | 6.40x | 6.40x → 6.40x | 4.64x → 28.48x | 9.38x → 12.57x | 6.1x |
| DeepSeek-V4-Pro-0813 | 231,460 | 5.82x | 5.82x → 5.82x | 4.20x → 26.34x | 8.95x → 11.31x | 6.3x |
| DeepSeek-V4-Pro-0813 | 254,280 | 5.83x | 5.83x → 5.83x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 267,320 | 7.08x | 7.08x → 7.08x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 277,100 | 7.08x | 7.08x → 7.08x | 5.49x → 24.61x | 12.01x → 14.92x | 4.5x |
| DeepSeek-V4-Pro-0813 | 277,350 | 6.80x | 10.32x → 3.70x | 5.27x → 23.59x | 8.00x → 12.84x | 4.5x |
| DeepSeek-V4-Pro-0813 | 277,915 | 7.08x | 7.08x → 7.08x | 5.49x → 24.58x | 12.01x → 14.83x | 4.5x |
| DeepSeek-V4-Pro-0813 | 279,545 | 7.08x | 7.08x → 7.08x | 5.49x → 24.87x | 12.02x → 15.18x | 4.5x |
| DeepSeek-V4-Pro-0813 | 308,070 | 7.08x | 7.08x → 7.08x | 5.49x → 25.18x | 12.05x → 16.82x | 4.6x |
| DeepSeek-V4-Pro-0813 | 318,665 | 7.08x | 7.08x → 7.08x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 319,480 | 7.08x | 7.08x → 7.08x | 5.48x → 25.42x | 12.05x → 17.59x | 4.6x |
| DeepSeek-V4-Pro-0813 | 323,575 | 6.87x | 10.40x → 3.68x | 5.32x → 24.52x | 8.06x → 13.16x | 4.6x |
| DeepSeek-V4-Pro-0813 | 369,800 | 6.90x | 10.50x → 3.71x | 5.33x → 25.30x | 8.12x → 13.62x | 4.7x |
| DeepSeek-V4-Pro-0813 | 416,025 | 6.90x | 10.52x → 3.71x | 5.33x → 25.80x | 8.13x → 13.86x | 4.8x |
| DeepSeek-V4-Pro-0813 | 554,700 | 6.68x | 10.06x → 3.63x | 5.15x → 25.13x | 7.76x → 13.65x | 4.9x |
| DeepSeek-V4-Pro-0813 | 3,050,850 | 4.47x | 7.47x → 2.81x | 3.43x → 17.08x | 5.74x → 10.75x | 5.0x |
| Qwen3-8B | 4,075 | 19.00x | 19.00x → 19.00x | 17.26x → 28.08x | 18.86x → 23.11x | 1.6x |
| Qwen3-8B | 4,890 | 26.85x | 26.85x → 26.85x | 23.98x → 41.78x | 27.88x → 30.86x | 1.7x |
| Qwen3-8B | 5,705 | 29.99x | 29.99x → 29.99x | 26.36x → 48.85x | 32.01x → 35.93x | 1.9x |
| Qwen3-8B | 6,520 | 29.33x | 29.33x → 29.33x | 25.39x → 49.80x | 31.41x → 38.15x | 2.0x |
| Qwen3-8B | 8,965 | 34.48x | 34.48x → 34.48x | 29.42x → 71.50x | 38.04x → 45.42x | 2.4x |
| Qwen3-8B | 9,780 | 34.24x | 34.24x → 34.24x | 28.97x → 71.13x | 37.92x → 45.06x | 2.5x |
| Qwen3-8B | 13,040 | 33.33x | 33.33x → 33.33x | 27.39x → 69.64x | 37.31x → 41.61x | 2.5x |
| Qwen3-8B | 46,225 | 5.83x | 9.08x → 3.07x | 4.31x → 18.53x | 6.72x → 9.77x | 4.3x |
| Qwen3-8B | 46,455 | 13.39x | 13.39x → 13.39x | 9.91x → 42.57x | 17.64x → 20.26x | 4.3x |
| Qwen3-8B | 56,235 | 10.45x | 10.45x → 10.45x | 7.64x → 35.74x | 14.35x → 16.45x | 4.7x |
| Qwen3-8B | 57,865 | 10.44x | 10.44x → 10.44x | 7.62x → 35.42x | 14.35x → 16.27x | 4.6x |
| Qwen3-8B | 66,830 | 10.40x | 10.40x → 10.40x | 7.53x → 37.43x | — | 5.0x |
| Qwen3-8B | 70,905 | 10.38x | 10.38x → 10.38x | 7.49x → 36.71x | 14.41x → 16.65x | 4.9x |
| Qwen3-8B | 84,760 | 8.62x | 8.62x → 8.62x | 6.17x → 31.45x | 12.51x → 15.01x | 5.1x |
| Qwen3-8B | 92,095 | 8.60x | 8.60x → 8.60x | 6.14x → 31.86x | 12.52x → 14.70x | 5.2x |
| Qwen3-8B | 92,450 | 4.93x | 7.67x → 2.68x | 3.51x → 18.19x | 5.47x → 9.91x | 5.2x |
| Qwen3-8B | 112,470 | 8.55x | 8.55x → 8.55x | 6.05x → 32.85x | 12.50x → 15.02x | 5.4x |
| Qwen3-8B | 138,550 | 7.26x | 7.26x → 7.26x | 5.10x → 29.19x | 10.93x → 15.48x | 5.7x |
| Qwen3-8B | 138,675 | 4.60x | 7.40x → 2.51x | 3.24x → 18.51x | 5.20x → 10.08x | 5.7x |
| Qwen3-8B | 168,705 | 6.30x | 6.30x → 6.30x | 4.41x → 26.74x | 9.68x → 16.24x | 6.1x |
| Qwen3-8B | 184,900 | 4.52x | 7.27x → 2.38x | 3.16x → 19.41x | 5.07x → 10.23x | 6.2x |
| Qwen3-8B | 185,005 | 6.28x | 6.28x → 6.28x | 4.38x → 26.97x | 9.66x → 16.34x | 6.2x |
| Qwen3-8B | 224,940 | 5.54x | 5.54x → 5.54x | 3.85x → 24.97x | 8.64x → 17.07x | 6.5x |
| Qwen3-8B | 277,100 | 6.84x | 6.84x → 6.84x | 5.20x → 22.80x | 11.84x → 17.31x | 4.4x |
| Qwen3-8B | 277,350 | 5.62x | 9.32x → 3.04x | 4.27x → 18.72x | 7.08x → 10.12x | 4.4x |
| Qwen3-8B | 369,800 | 5.59x | 9.26x → 2.85x | 4.24x → 18.72x | 7.02x → 9.54x | 4.4x |
| Qwen3-8B | 554,700 | 5.20x | 8.95x → 2.80x | 3.93x → 17.54x | 6.77x → 9.45x | 4.5x |

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

| Fabric clock | GHz | In stated band | Qwen3-8B fixed latency/token | DeepSeek-V4-Flash-0731 @ 35,860 mm2 | DeepSeek-V4-Pro-0813 @ 170,335 mm2 | Qwen3-8B @ 5,705 mm2 |
|---|---:|---|---:|---:|---:|---:|
| `band_low` | 0.5000 | yes | 11.53 us | 11.12x | 5.75x | 27.86x |
| `stated` | 1.0000 | yes | 6.82 us | 11.94x | 5.94x | 29.99x |
| `band_high` | 2.0000 | yes | 4.46 us | 12.40x | 6.04x | 31.18x |
| `asap7_reduction_s8_g2` | 1.2874 | yes | 5.77 us | 12.14x | 5.99x | 30.51x |
| `asap7_add_bf16_sram_engine` | 0.2391 | **no** | 21.83 us | 9.69x | 5.38x | 24.15x |
| `asap7_matmul_bf16_sram_engine` | 0.0580 | **no** | 83.47 us | 5.72x | — | 13.67x |

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

| ROM cell ratio | Value | In stated band | ROM capacity | Full-array sweep | DeepSeek-V4-Flash-0731 @ 35,860 mm2 | DeepSeek-V4-Pro-0813 @ 170,335 mm2 | Qwen3-8B @ 5,705 mm2 |
|---|---:|---|---:|---:|---:|---:|---:|
| `band_low` | 0.1100 | yes | 21.886 MB/mm2 | 103.4 us | — | — | 29.99x |
| `stated` | 0.3300 | yes | 7.295 MB/mm2 | 34.5 us | 11.94x | 5.94x | 29.99x |
| `band_high` | 0.3300 | yes | 7.295 MB/mm2 | 34.5 us | 11.94x | 5.94x | 29.99x |
| `measured_ihp_sg13g2_130nm` | 0.1298 | yes | 18.553 MB/mm2 | 87.7 us | — | — | 29.99x |
| `measured_asap7_7nm_via_programmed` | 0.2500 | yes | 9.630 MB/mm2 | 45.5 us | — | — | 29.99x |
| `measured_asap7_7nm_shared_source_drain` | 0.1250 | yes | 19.259 MB/mm2 | 91.0 us | — | — | 29.99x |

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
| DeepSeek-V4-Flash-0731 | 19 | 15,694 | 142.0 | 818.6 | 642.7 | tensor | 841.69 | 68.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 22 | 18,172 | 141.9 | 853.6 | 711.4 | tensor | 841.69 | 71.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 24 | 19,824 | 141.8 | 873.3 | 754.0 | tensor | 841.69 | 73.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 28 | 23,128 | 141.6 | 900.4 | 688.1 | tensor | 848.73 | 76.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 34 | 28,084 | 141.3 | 933.9 | 673.4 | tensor | 852.96 | 79.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 39 | 32,214 | 141.0 | 957.5 | 738.9 | tensor | 852.96 | 81.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 35,518 | 140.8 | 970.3 | 696.9 | tensor | 855.78 | 83.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 52 | 42,952 | 140.8 | 995.5 | 712.8 | tensor | 857.79 | 85.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 53 | 43,778 | 140.8 | 998.0 | 721.9 | tensor | 857.79 | 85.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 54 | 44,604 | 140.8 | 1,000.5 | 731.0 | tensor | 857.79 | 85.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 140.8 | 1,005.1 | 748.7 | tensor | 857.79 | 86.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 63 | 52,038 | 140.8 | 1,017.8 | 739.7 | tensor | 859.30 | 87.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 69 | 56,994 | 140.8 | 1,026.6 | 725.5 | tensor | 860.47 | 88.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 78 | 64,428 | 140.8 | 1,038.0 | 732.5 | tensor | 861.41 | 89.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 80 | 66,080 | 140.8 | 1,040.5 | 744.7 | tensor | 861.41 | 89.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 81 | 66,906 | 140.8 | 1,040.8 | 703.9 | tensor | 862.18 | 89.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 82 | 67,732 | 140.8 | 1,041.9 | 709.7 | tensor | 862.18 | 89.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 86 | 71,036 | 140.8 | 1,046.3 | 732.4 | tensor | 862.18 | 90.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 87 | 71,862 | 140.8 | 1,047.3 | 737.9 | tensor | 862.18 | 90.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 98 | 80,948 | 140.8 | 1,055.9 | 712.6 | tensor | 863.36 | 91.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 104 | 85,904 | 140.8 | 1,060.5 | 740.8 | tensor | 863.36 | 91.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 111 | 91,686 | 140.8 | 1,064.8 | 735.2 | tensor | 863.83 | 92.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 140.8 | 1,065.4 | 739.5 | tensor | 863.83 | 92.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 117 | 96,642 | 140.8 | 1,068.0 | 726.2 | tensor | 864.23 | 92.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 138 | 113,988 | 140.8 | 1,077.4 | 714.5 | tensor | 865.17 | 93.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 156 | 128,856 | 140.8 | 1,083.7 | 720.1 | tensor | 865.64 | 93.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 140.8 | 1,087.2 | 730.6 | tensor | 865.84 | 94.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 140.8 | 1,098.4 | 721.9 | tensor | 866.85 | 95.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 234 | 193,284 | 140.8 | 1,099.8 | 708.0 | tensor | 867.05 | 95.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 312 | 257,712 | 140.8 | 1,108.1 | 708.6 | tensor | 867.70 | 96.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 335 | 276,710 | 140.8 | 799.8 | 703.8 | tensor | 1,217.01 | 97.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 140.8 | 799.9 | 705.1 | tensor | 1,217.01 | 97.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 140.8 | 802.9 | 703.9 | tensor | 1,217.52 | 97.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 560 | 462,560 | 140.8 | 804.7 | 703.9 | tensor | 1,217.82 | 98.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 140.8 | 805.9 | 703.9 | tensor | 1,218.02 | 98.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 39.2 | 564.7 | 261.2 | tensor | 1,300.52 | 73.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 100 | 82,600 | 39.2 | 630.7 | 251.9 | tensor | 1,314.36 | 82.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 39.2 | 641.2 | 260.0 | tensor | 1,315.51 | 84.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 125 | 103,250 | 39.2 | 650.3 | 254.6 | tensor | 1,317.39 | 85.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 166 | 137,116 | 39.2 | 670.8 | 256.3 | tensor | 1,320.51 | 88.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 39.2 | 671.6 | 258.8 | tensor | 1,320.51 | 88.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 173 | 142,898 | 39.2 | 673.3 | 255.0 | tensor | 1,320.96 | 88.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 177 | 146,202 | 39.2 | 674.7 | 250.3 | tensor | 1,321.38 | 89.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 206 | 170,156 | 39.2 | 683.5 | 255.9 | tensor | 1,322.43 | 90.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 39.2 | 687.9 | 257.6 | tensor | 1,323.01 | 91.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 233 | 192,458 | 39.2 | 689.7 | 251.1 | tensor | 1,323.51 | 91.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 234 | 193,284 | 39.2 | 689.9 | 252.0 | tensor | 1,323.51 | 91.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 39.2 | 698.0 | 256.4 | tensor | 1,324.51 | 92.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 308 | 254,408 | 39.2 | 701.7 | 253.0 | tensor | 1,325.12 | 93.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 324 | 267,624 | 39.2 | 521.8 | 252.8 | tensor | 1,820.70 | 95.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 335 | 276,710 | 39.2 | 522.4 | 254.6 | tensor | 1,820.83 | 95.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 39.2 | 522.5 | 255.2 | tensor | 1,820.83 | 95.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 338 | 279,188 | 39.2 | 522.6 | 251.4 | tensor | 1,820.94 | 95.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 373 | 308,098 | 39.2 | 524.4 | 252.7 | tensor | 1,821.36 | 95.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 386 | 318,836 | 39.2 | 525.0 | 250.9 | tensor | 1,821.54 | 95.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 387 | 319,662 | 39.2 | 525.0 | 251.4 | tensor | 1,821.54 | 95.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 392 | 323,792 | 39.2 | 525.3 | 254.0 | tensor | 1,821.54 | 95.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 39.2 | 527.3 | 252.8 | tensor | 1,822.07 | 96.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 504 | 416,304 | 39.2 | 529.0 | 252.0 | tensor | 1,822.49 | 96.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 574 | 474,124 | 39.2 | 530.6 | 251.3 | tensor | 1,822.91 | 96.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 39.2 | 532.3 | 252.0 | tensor | 1,823.32 | 97.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 3694 | 3,051,244 | 39.2 | 540.6 | 251.9 | tensor | 1,825.37 | 98.7% | link_latency |
| Qwen3-8B | 3 | 2,478 | 100.9 | 272.5 | — | tensor | 363.93 | 9.9% | weight_read |
| Qwen3-8B | 4 | 3,304 | 100.9 | 351.4 | — | tensor | 364.42 | 12.8% | weight_read |
| Qwen3-8B | 5 | 4,130 | 100.9 | 425.4 | — | tensor | 364.72 | 15.5% | weight_read |
| Qwen3-8B | 6 | 4,956 | 100.8 | 494.8 | — | tensor | 364.92 | 18.1% | weight_read |
| Qwen3-8B | 7 | 5,782 | 100.8 | 560.0 | — | tensor | 365.06 | 20.4% | weight_read |
| Qwen3-8B | 8 | 6,608 | 100.8 | 621.5 | — | tensor | 365.16 | 22.7% | weight_read |
| Qwen3-8B | 11 | 9,086 | 100.7 | 625.2 | 460.0 | tensor | 692.87 | 43.3% | weight_read |
| Qwen3-8B | 12 | 9,912 | 100.7 | 656.0 | 494.1 | tensor | 692.87 | 45.5% | link_latency |
| Qwen3-8B | 16 | 13,216 | 100.6 | 758.6 | 620.6 | tensor | 692.87 | 52.6% | link_latency |
| Qwen3-8B | 56 | 46,256 | 100.1 | 1,109.0 | 616.1 | tensor | 718.15 | 79.6% | link_latency |
| Qwen3-8B | 68 | 56,168 | 100.1 | 1,145.8 | 588.0 | tensor | 720.40 | 82.5% | link_latency |
| Qwen3-8B | 69 | 56,994 | 100.1 | 1,148.6 | 594.6 | tensor | 720.40 | 82.7% | link_latency |
| Qwen3-8B | 70 | 57,820 | 100.1 | 1,151.3 | 601.2 | tensor | 720.40 | 82.9% | link_latency |
| Qwen3-8B | 81 | 66,906 | 100.1 | 1,175.3 | 574.9 | tensor | 721.83 | 84.8% | link_latency |
| Qwen3-8B | 86 | 71,036 | 100.1 | 1,185.2 | 601.9 | tensor | 721.83 | 85.6% | link_latency |
| Qwen3-8B | 103 | 85,078 | 100.1 | 1,211.1 | 606.3 | tensor | 722.82 | 87.5% | link_latency |
| Qwen3-8B | 111 | 91,686 | 100.1 | 1,220.7 | 605.8 | tensor | 723.20 | 88.3% | link_latency |
| Qwen3-8B | 112 | 92,512 | 100.1 | 1,221.9 | 609.9 | tensor | 723.20 | 88.4% | link_latency |
| Qwen3-8B | 136 | 112,336 | 100.1 | 1,244.3 | 607.3 | tensor | 724.10 | 90.1% | link_latency |
| Qwen3-8B | 168 | 138,768 | 100.1 | 1,264.8 | 603.8 | tensor | 724.89 | 91.7% | link_latency |
| Qwen3-8B | 204 | 168,504 | 100.1 | 1,280.6 | 590.9 | tensor | 725.54 | 92.9% | link_latency |
| Qwen3-8B | 224 | 185,024 | 100.1 | 1,287.4 | 597.8 | tensor | 725.73 | 93.4% | link_latency |
| Qwen3-8B | 272 | 224,672 | 100.1 | 1,299.7 | 592.8 | tensor | 726.18 | 94.4% | link_latency |
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
| Qwen3-8B/a100_sxm_80gb-x11-pipeline | Qwen3-8B | 11 | pipeline | nvlink3 | infiniband_hdr | 10 | 25.10 us | 3,983.5 tok/s | 39,835.2 tok/s | 9 x point_to_point span 2 on nvlink3 (traversals 1.0) = 22.75 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x11-tensor | Qwen3-8B | 11 | tensor | nvlink3 | infiniband_hdr | 144 | 692.87 us | 144.3 tok/s | 1,443.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 327.71 us |
| Qwen3-8B/a100_sxm_80gb-x11-hybrid | Qwen3-8B | 11 | hybrid | nvlink3 | infiniband_hdr | 73 | 367.52 us | 272.1 tok/s | 2,721.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x12-pipeline | Qwen3-8B | 12 | pipeline | nvlink3 | infiniband_hdr | 11 | 27.63 us | 3,619.2 tok/s | 36,191.6 tok/s | 10 x point_to_point span 2 on nvlink3 (traversals 1.0) = 25.27 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| Qwen3-8B/a100_sxm_80gb-x12-tensor | Qwen3-8B | 12 | tensor | nvlink3 | infiniband_hdr | 144 | 692.87 us | 144.3 tok/s | 1,443.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 327.71 us |
| Qwen3-8B/a100_sxm_80gb-x12-hybrid | Qwen3-8B | 12 | hybrid | nvlink3 | infiniband_hdr | 73 | 367.52 us | 272.1 tok/s | 2,721.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
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
| Qwen3-8B/a100_sxm_80gb-x70-pipeline | Qwen3-8B | 70 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x70-tensor | Qwen3-8B | 70 | tensor | nvlink3 | infiniband_hdr | 144 | 720.40 us | 138.8 tok/s | 1,388.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 355.23 us |
| Qwen3-8B/a100_sxm_80gb-x70-hybrid | Qwen3-8B | 70 | hybrid | nvlink3 | infiniband_hdr | 80 | 384.02 us | 260.4 tok/s | 2,604.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| Qwen3-8B/a100_sxm_80gb-x81-pipeline | Qwen3-8B | 81 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x81-tensor | Qwen3-8B | 81 | tensor | nvlink3 | infiniband_hdr | 144 | 721.83 us | 138.5 tok/s | 1,385.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 356.66 us |
| Qwen3-8B/a100_sxm_80gb-x81-hybrid | Qwen3-8B | 81 | hybrid | nvlink3 | infiniband_hdr | 82 | 388.74 us | 257.2 tok/s | 2,572.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
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
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x82 | DeepSeek-V4-Flash-0731 | 82 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57 | DeepSeek-V4-Flash-0731 | 57 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.97 us | 1,667.4 tok/s | 16,674.4 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 15 on rom_board_serdes (traversals 6.6) = 57.86 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x83 | DeepSeek-V4-Flash-0731 | 83 | hybrid | rom_package_ucie | rom_board_serdes | 106 | 4.21 us | 23,768.2 tok/s | 237,681.5 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 20 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.09 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x81 | DeepSeek-V4-Flash-0731 | 81 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x40 | DeepSeek-V4-Flash-0731 | 40 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x55 | DeepSeek-V4-Flash-0731 | 55 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x88 | DeepSeek-V4-Flash-0731 | 88 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x79 | DeepSeek-V4-Flash-0731 | 79 | tensor | rom_package_ucie | rom_board_serdes | 172 | 78.91 us | 1,267.2 tok/s | 12,672.4 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 20 on rom_board_serdes (traversals 8.8) = 76.80 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x87 | DeepSeek-V4-Flash-0731 | 87 | hybrid | rom_package_ucie | rom_board_serdes | 107 | 4.31 us | 23,191.8 tok/s | 231,918.4 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 21 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.20 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x87 | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10 | DeepSeek-V4-Flash-0731 | 10 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x79 | DeepSeek-V4-Flash-0731 | 79 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x10 | DeepSeek-V4-Flash-0731 | 10 | tensor | on_wafer | rom_wafer_serdes | 172 | 222.63 us | 449.2 tok/s | 4,491.8 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 86 x all_reduce span 10 on rom_wafer_serdes (traversals 6.6) = 57.08 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x79 | DeepSeek-V4-Flash-0731 | 79 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10 | DeepSeek-V4-Flash-0731 | 10 | hybrid | on_wafer | rom_wafer_serdes | 95 | 166.46 us | 600.7 tok/s | 6,007.4 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 9 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.91 us |
| DSV4-Flash/a100_sxm_80gb-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 45.15 us | 2,214.7 tok/s | 22,147.3 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 40.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x19-expert | DeepSeek-V4-Flash-0731 | 19 | expert | nvlink3 | infiniband_hdr | 172 | 616.56 us | 162.2 tok/s | 1,621.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.48 us |
| DSV4-Flash/a100_sxm_80gb-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink3 | infiniband_hdr | 21 | 52.73 us | 1,896.3 tok/s | 18,963.0 tok/s | 19 x point_to_point span 2 on nvlink3 (traversals 1.0) = 48.02 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink3 | infiniband_hdr | 172 | 615.35 us | 162.5 tok/s | 1,625.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 182.27 us |
| DSV4-Flash/a100_sxm_80gb-x24-pipeline | DeepSeek-V4-Flash-0731 | 24 | pipeline | nvlink3 | infiniband_hdr | 23 | 57.79 us | 1,730.4 tok/s | 17,304.4 tok/s | 21 x point_to_point span 2 on nvlink3 (traversals 1.0) = 53.07 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x24-tensor | DeepSeek-V4-Flash-0731 | 24 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x24-hybrid | DeepSeek-V4-Flash-0731 | 24 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x24-expert | DeepSeek-V4-Flash-0731 | 24 | expert | nvlink3 | infiniband_hdr | 172 | 613.68 us | 163.0 tok/s | 1,629.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 432.05 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 181.63 us |
| DSV4-Flash/a100_sxm_80gb-x28-pipeline | DeepSeek-V4-Flash-0731 | 28 | pipeline | nvlink3 | infiniband_hdr | 27 | 67.73 us | 1,476.5 tok/s | 14,764.9 tok/s | 24 x point_to_point span 2 on nvlink3 (traversals 1.0) = 60.66 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| DSV4-Flash/a100_sxm_80gb-x28-tensor | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink3 | infiniband_hdr | 172 | 848.73 us | 117.8 tok/s | 1,178.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 412.57 us |
| DSV4-Flash/a100_sxm_80gb-x28-hybrid | DeepSeek-V4-Flash-0731 | 28 | hybrid | nvlink3 | infiniband_hdr | 89 | 443.24 us | 225.6 tok/s | 2,256.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| DSV4-Flash/a100_sxm_80gb-x28-expert | DeepSeek-V4-Flash-0731 | 28 | expert | nvlink3 | infiniband_hdr | 172 | 612.67 us | 163.2 tok/s | 1,632.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 432.05 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 180.62 us |
| DSV4-Flash/a100_sxm_80gb-x34-pipeline | DeepSeek-V4-Flash-0731 | 34 | pipeline | nvlink3 | infiniband_hdr | 33 | 82.72 us | 1,208.9 tok/s | 12,088.6 tok/s | 29 x point_to_point span 2 on nvlink3 (traversals 1.0) = 73.29 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x34-tensor | DeepSeek-V4-Flash-0731 | 34 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x34-hybrid | DeepSeek-V4-Flash-0731 | 34 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x34-expert | DeepSeek-V4-Flash-0731 | 34 | expert | nvlink3 | infiniband_hdr | 172 | 611.09 us | 163.6 tok/s | 1,636.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.55 us |
| DSV4-Flash/a100_sxm_80gb-x39-pipeline | DeepSeek-V4-Flash-0731 | 39 | pipeline | nvlink3 | infiniband_hdr | 38 | 95.36 us | 1,048.7 tok/s | 10,486.7 tok/s | 34 x point_to_point span 2 on nvlink3 (traversals 1.0) = 85.93 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x39-tensor | DeepSeek-V4-Flash-0731 | 39 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x39-hybrid | DeepSeek-V4-Flash-0731 | 39 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x39-expert | DeepSeek-V4-Flash-0731 | 39 | expert | nvlink3 | infiniband_hdr | 172 | 610.46 us | 163.8 tok/s | 1,638.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.92 us |
| DSV4-Flash/a100_sxm_80gb-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink3 | infiniband_hdr | 172 | 609.75 us | 164.0 tok/s | 1,640.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.51 us |
| DSV4-Flash/a100_sxm_80gb-x52-pipeline | DeepSeek-V4-Flash-0731 | 52 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x52-tensor | DeepSeek-V4-Flash-0731 | 52 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x52-hybrid | DeepSeek-V4-Flash-0731 | 52 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x52-expert | DeepSeek-V4-Flash-0731 | 52 | expert | nvlink3 | infiniband_hdr | 172 | 608.86 us | 164.2 tok/s | 1,642.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.83 us |
| DSV4-Flash/a100_sxm_80gb-x53-pipeline | DeepSeek-V4-Flash-0731 | 53 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x53-tensor | DeepSeek-V4-Flash-0731 | 53 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x53-hybrid | DeepSeek-V4-Flash-0731 | 53 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x53-expert | DeepSeek-V4-Flash-0731 | 53 | expert | nvlink3 | infiniband_hdr | 172 | 608.80 us | 164.3 tok/s | 1,642.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.77 us |
| DSV4-Flash/a100_sxm_80gb-x54-pipeline | DeepSeek-V4-Flash-0731 | 54 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x54-tensor | DeepSeek-V4-Flash-0731 | 54 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x54-hybrid | DeepSeek-V4-Flash-0731 | 54 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x54-expert | DeepSeek-V4-Flash-0731 | 54 | expert | nvlink3 | infiniband_hdr | 172 | 608.74 us | 164.3 tok/s | 1,642.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.71 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x56-expert | DeepSeek-V4-Flash-0731 | 56 | expert | nvlink3 | infiniband_hdr | 172 | 608.48 us | 164.3 tok/s | 1,643.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.60 us |
| DSV4-Flash/a100_sxm_80gb-x63-pipeline | DeepSeek-V4-Flash-0731 | 63 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x63-tensor | DeepSeek-V4-Flash-0731 | 63 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x63-hybrid | DeepSeek-V4-Flash-0731 | 63 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x63-expert | DeepSeek-V4-Flash-0731 | 63 | expert | nvlink3 | infiniband_hdr | 172 | 608.14 us | 164.4 tok/s | 1,644.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.26 us |
| DSV4-Flash/a100_sxm_80gb-x69-pipeline | DeepSeek-V4-Flash-0731 | 69 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x69-tensor | DeepSeek-V4-Flash-0731 | 69 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x69-hybrid | DeepSeek-V4-Flash-0731 | 69 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x69-expert | DeepSeek-V4-Flash-0731 | 69 | expert | nvlink3 | infiniband_hdr | 172 | 607.80 us | 164.5 tok/s | 1,645.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.03 us |
| DSV4-Flash/a100_sxm_80gb-x78-pipeline | DeepSeek-V4-Flash-0731 | 78 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x78-tensor | DeepSeek-V4-Flash-0731 | 78 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x78-hybrid | DeepSeek-V4-Flash-0731 | 78 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x78-expert | DeepSeek-V4-Flash-0731 | 78 | expert | nvlink3 | infiniband_hdr | 172 | 607.43 us | 164.6 tok/s | 1,646.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.75 us |
| DSV4-Flash/a100_sxm_80gb-x80-pipeline | DeepSeek-V4-Flash-0731 | 80 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x80-tensor | DeepSeek-V4-Flash-0731 | 80 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x80-hybrid | DeepSeek-V4-Flash-0731 | 80 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x80-expert | DeepSeek-V4-Flash-0731 | 80 | expert | nvlink3 | infiniband_hdr | 172 | 607.31 us | 164.7 tok/s | 1,646.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.69 us |
| DSV4-Flash/a100_sxm_80gb-x81-pipeline | DeepSeek-V4-Flash-0731 | 81 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x81-tensor | DeepSeek-V4-Flash-0731 | 81 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x81-hybrid | DeepSeek-V4-Flash-0731 | 81 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x81-expert | DeepSeek-V4-Flash-0731 | 81 | expert | nvlink3 | infiniband_hdr | 172 | 607.28 us | 164.7 tok/s | 1,646.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.67 us |
| DSV4-Flash/a100_sxm_80gb-x82-pipeline | DeepSeek-V4-Flash-0731 | 82 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x82-tensor | DeepSeek-V4-Flash-0731 | 82 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x82-hybrid | DeepSeek-V4-Flash-0731 | 82 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x82-expert | DeepSeek-V4-Flash-0731 | 82 | expert | nvlink3 | infiniband_hdr | 172 | 607.26 us | 164.7 tok/s | 1,646.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.64 us |
| DSV4-Flash/a100_sxm_80gb-x86-pipeline | DeepSeek-V4-Flash-0731 | 86 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x86-tensor | DeepSeek-V4-Flash-0731 | 86 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x86-hybrid | DeepSeek-V4-Flash-0731 | 86 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x86-expert | DeepSeek-V4-Flash-0731 | 86 | expert | nvlink3 | infiniband_hdr | 172 | 607.16 us | 164.7 tok/s | 1,647.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.55 us |
| DSV4-Flash/a100_sxm_80gb-x87-pipeline | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x87-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x87-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x87-expert | DeepSeek-V4-Flash-0731 | 87 | expert | nvlink3 | infiniband_hdr | 172 | 607.14 us | 164.7 tok/s | 1,647.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.52 us |
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
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x392 | DeepSeek-V4-Pro-0813 | 392 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x236 | DeepSeek-V4-Pro-0813 | 236 | tensor | rom_package_ucie | rom_board_serdes | 244 | 194.17 us | 515.0 tok/s | 5,150.1 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 59 on rom_board_serdes (traversals 15.4) = 190.75 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x392 | DeepSeek-V4-Pro-0813 | 392 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x391 | DeepSeek-V4-Pro-0813 | 391 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x9 | DeepSeek-V4-Pro-0813 | 9 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x209 | DeepSeek-V4-Pro-0813 | 209 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.73 us | 75.6 tok/s | 756.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 697.43 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | rom_wafer_serdes | 244 | 262.35 us | 381.2 tok/s | 3,811.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 27.50 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x328 | DeepSeek-V4-Pro-0813 | 328 | hybrid | nvlink3 | infiniband_hdr | 162 | 729.44 us | 137.1 tok/s | 1,370.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 40 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 104.14 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x7 | DeepSeek-V4-Pro-0813 | 7 | hybrid | on_wafer | rom_wafer_serdes | 128 | 235.46 us | 424.7 tok/s | 4,246.9 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 6 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.61 us |
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
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x112-expert | DeepSeek-V4-Pro-0813 | 112 | expert | nvlink3 | infiniband_hdr | 244 | 862.50 us | 115.9 tok/s | 1,159.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.09 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.41 us |
| DSV4-Pro/a100_sxm_80gb-x125-pipeline | DeepSeek-V4-Pro-0813 | 125 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x125-tensor | DeepSeek-V4-Pro-0813 | 125 | tensor | nvlink3 | infiniband_hdr | 244 | 1,317.39 us | 75.9 tok/s | 759.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 692.08 us |
| DSV4-Pro/a100_sxm_80gb-x125-hybrid | DeepSeek-V4-Pro-0813 | 125 | hybrid | nvlink3 | infiniband_hdr | 137 | 664.36 us | 150.5 tok/s | 1,505.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.05 us |
| DSV4-Pro/a100_sxm_80gb-x125-expert | DeepSeek-V4-Pro-0813 | 125 | expert | nvlink3 | infiniband_hdr | 244 | 862.04 us | 116.0 tok/s | 1,160.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.02 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.02 us |
| DSV4-Pro/a100_sxm_80gb-x166-pipeline | DeepSeek-V4-Pro-0813 | 166 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x166-tensor | DeepSeek-V4-Pro-0813 | 166 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.51 us | 75.7 tok/s | 757.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 695.20 us |
| DSV4-Pro/a100_sxm_80gb-x166-hybrid | DeepSeek-V4-Pro-0813 | 166 | hybrid | nvlink3 | infiniband_hdr | 142 | 677.37 us | 147.6 tok/s | 1,476.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| DSV4-Pro/a100_sxm_80gb-x166-expert | DeepSeek-V4-Pro-0813 | 166 | expert | nvlink3 | infiniband_hdr | 244 | 860.95 us | 116.2 tok/s | 1,161.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.77 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 250.19 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.51 us | 75.7 tok/s | 757.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 695.20 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 677.37 us | 147.6 tok/s | 1,476.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| DSV4-Pro/a100_sxm_80gb-x168-expert | DeepSeek-V4-Pro-0813 | 168 | expert | nvlink3 | infiniband_hdr | 244 | 860.89 us | 116.2 tok/s | 1,161.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.73 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 250.16 us |
| DSV4-Pro/a100_sxm_80gb-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.96 us | 75.7 tok/s | 757.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 695.66 us |
| DSV4-Pro/a100_sxm_80gb-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink3 | infiniband_hdr | 143 | 679.98 us | 147.1 tok/s | 1,470.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 54.67 us |
| DSV4-Pro/a100_sxm_80gb-x173-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink3 | infiniband_hdr | 244 | 860.82 us | 116.2 tok/s | 1,161.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.73 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 250.09 us |
| DSV4-Pro/a100_sxm_80gb-x177-pipeline | DeepSeek-V4-Pro-0813 | 177 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x177-tensor | DeepSeek-V4-Pro-0813 | 177 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.38 us | 75.7 tok/s | 756.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 696.07 us |
| DSV4-Pro/a100_sxm_80gb-x177-hybrid | DeepSeek-V4-Pro-0813 | 177 | hybrid | nvlink3 | infiniband_hdr | 144 | 682.58 us | 146.5 tok/s | 1,465.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 57.28 us |
| DSV4-Pro/a100_sxm_80gb-x177-expert | DeepSeek-V4-Pro-0813 | 177 | expert | nvlink3 | infiniband_hdr | 244 | 860.73 us | 116.2 tok/s | 1,161.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.70 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 250.03 us |
| DSV4-Pro/a100_sxm_80gb-x206-pipeline | DeepSeek-V4-Pro-0813 | 206 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x206-tensor | DeepSeek-V4-Pro-0813 | 206 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x206-hybrid | DeepSeek-V4-Pro-0813 | 206 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x206-expert | DeepSeek-V4-Pro-0813 | 206 | expert | nvlink3 | infiniband_hdr | 244 | 860.31 us | 116.2 tok/s | 1,162.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.61 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.70 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x224-expert | DeepSeek-V4-Pro-0813 | 224 | expert | nvlink3 | infiniband_hdr | 244 | 860.08 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.53 us |
| DSV4-Pro/a100_sxm_80gb-x233-pipeline | DeepSeek-V4-Pro-0813 | 233 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x233-tensor | DeepSeek-V4-Pro-0813 | 233 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.51 us | 75.6 tok/s | 755.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 30 on infiniband_hdr (traversals 2.0) = 698.20 us |
| DSV4-Pro/a100_sxm_80gb-x233-hybrid | DeepSeek-V4-Pro-0813 | 233 | hybrid | nvlink3 | infiniband_hdr | 151 | 700.80 us | 142.7 tok/s | 1,426.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 29 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.50 us |
| DSV4-Pro/a100_sxm_80gb-x233-expert | DeepSeek-V4-Pro-0813 | 233 | expert | nvlink3 | infiniband_hdr | 244 | 859.99 us | 116.3 tok/s | 1,162.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.53 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.46 us |
| DSV4-Pro/a100_sxm_80gb-x234-pipeline | DeepSeek-V4-Pro-0813 | 234 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x234-tensor | DeepSeek-V4-Pro-0813 | 234 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.51 us | 75.6 tok/s | 755.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 30 on infiniband_hdr (traversals 2.0) = 698.20 us |
| DSV4-Pro/a100_sxm_80gb-x234-hybrid | DeepSeek-V4-Pro-0813 | 234 | hybrid | nvlink3 | infiniband_hdr | 151 | 700.80 us | 142.7 tok/s | 1,426.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 29 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.50 us |
| DSV4-Pro/a100_sxm_80gb-x234-expert | DeepSeek-V4-Pro-0813 | 234 | expert | nvlink3 | infiniband_hdr | 244 | 859.98 us | 116.3 tok/s | 1,162.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.53 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.45 us |
| DSV4-Pro/a100_sxm_80gb-x280-pipeline | DeepSeek-V4-Pro-0813 | 280 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x280-tensor | DeepSeek-V4-Pro-0813 | 280 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.51 us | 75.5 tok/s | 755.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 699.20 us |
| DSV4-Pro/a100_sxm_80gb-x280-hybrid | DeepSeek-V4-Pro-0813 | 280 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/a100_sxm_80gb-x280-expert | DeepSeek-V4-Pro-0813 | 280 | expert | nvlink3 | infiniband_hdr | 244 | 859.60 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.44 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.16 us |
| DSV4-Pro/a100_sxm_80gb-x308-pipeline | DeepSeek-V4-Pro-0813 | 308 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x308-tensor | DeepSeek-V4-Pro-0813 | 308 | tensor | nvlink3 | infiniband_hdr | 244 | 1,325.12 us | 75.5 tok/s | 754.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 39 on infiniband_hdr (traversals 2.0) = 699.82 us |
| DSV4-Pro/a100_sxm_80gb-x308-hybrid | DeepSeek-V4-Pro-0813 | 308 | hybrid | nvlink3 | infiniband_hdr | 160 | 724.23 us | 138.1 tok/s | 1,380.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 38 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 98.93 us |
| DSV4-Pro/a100_sxm_80gb-x308-expert | DeepSeek-V4-Pro-0813 | 308 | expert | nvlink3 | infiniband_hdr | 244 | 859.43 us | 116.4 tok/s | 1,163.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.40 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.02 us |
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
| DSV4-Pro/a100_sxm_80gb-x338-pipeline | DeepSeek-V4-Pro-0813 | 338 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x338-tensor | DeepSeek-V4-Pro-0813 | 338 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.94 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 43 on infiniband_hdr (traversals 4.0) = 1,195.64 us |
| DSV4-Pro/a100_sxm_80gb-x338-hybrid | DeepSeek-V4-Pro-0813 | 338 | hybrid | nvlink3 | infiniband_hdr | 164 | 734.65 us | 136.1 tok/s | 1,361.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 109.34 us |
| DSV4-Pro/a100_sxm_80gb-x338-expert | DeepSeek-V4-Pro-0813 | 338 | expert | nvlink3 | infiniband_hdr | 244 | 859.27 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.36 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.90 us |
| DSV4-Pro/a100_sxm_80gb-x373-pipeline | DeepSeek-V4-Pro-0813 | 373 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x373-tensor | DeepSeek-V4-Pro-0813 | 373 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.36 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,196.05 us |
| DSV4-Pro/a100_sxm_80gb-x373-hybrid | DeepSeek-V4-Pro-0813 | 373 | hybrid | nvlink3 | infiniband_hdr | 168 | 745.06 us | 134.2 tok/s | 1,342.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 119.76 us |
| DSV4-Pro/a100_sxm_80gb-x373-expert | DeepSeek-V4-Pro-0813 | 373 | expert | nvlink3 | infiniband_hdr | 244 | 859.12 us | 116.4 tok/s | 1,164.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.33 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.79 us |
| DSV4-Pro/a100_sxm_80gb-x386-pipeline | DeepSeek-V4-Pro-0813 | 386 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x386-tensor | DeepSeek-V4-Pro-0813 | 386 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x386-hybrid | DeepSeek-V4-Pro-0813 | 386 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x386-expert | DeepSeek-V4-Pro-0813 | 386 | expert | nvlink3 | infiniband_hdr | 244 | 859.07 us | 116.4 tok/s | 1,164.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.32 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.75 us |
| DSV4-Pro/a100_sxm_80gb-x387-pipeline | DeepSeek-V4-Pro-0813 | 387 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x387-tensor | DeepSeek-V4-Pro-0813 | 387 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x387-hybrid | DeepSeek-V4-Pro-0813 | 387 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x387-expert | DeepSeek-V4-Pro-0813 | 387 | expert | nvlink3 | infiniband_hdr | 244 | 859.06 us | 116.4 tok/s | 1,164.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.32 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.74 us |
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
| Qwen3-8B | 1 | array | array | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill | 13,040 | 25,281.1 | 1.939 | 25,281.1 (13,040) | 6,464.4 (46,225) | 0.26x | link_latency |
| Qwen3-8B | 2 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x69-romfill | 56,235 | 10,488.6 | 0.187 | 10,488.6 (56,235) | 5,028.2 (369,800) | 0.48x | link_latency |
| Qwen3-8B | 4 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x82-romfill | 66,830 | 8,898.9 | 0.133 | 8,898.9 (66,830) | 4,531.9 (369,800) | 0.51x | link_latency |
| Qwen3-8B | 8 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x138 | 112,470 | 7,134.8 | 0.063 | 7,134.8 (112,470) | 4,325.6 (369,800) | 0.61x | link_latency |
| Qwen3-8B | 16 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69-romfill | 56,235 | 4,970.4 | 0.088 | 4,970.4 (56,235) | 3,846.9 (554,700) | 0.77x | kv_read |
| Qwen3-8B | 32 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x138-romfill | 112,470 | 5,059.0 | 0.045 | 5,059.0 (112,470) | 2,678.3 (554,700) | 0.53x | kv_read |
| Qwen3-8B | 64 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill | 224,940 | 5,125.0 | 0.023 | 5,125.0 (224,940) | 1,666.0 (554,700) | 0.33x | kv_read |
| Qwen3-8B | 256 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 1,773.0 | 0.006 | 1,773.0 (277,100) | 509.8 (554,700) | 0.29x | kv_read |
| Qwen3-8B | 1024 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 452.2 | 0.002 | 452.2 (277,100) | 137.6 (554,700) | 0.30x | kv_read |
| Qwen3-8B | 4096 | array | array | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 113.4 | 0.000 | 113.4 (277,100) | 34.4 (554,700) | 0.30x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x81 | 66,015 | 13,427.8 | 0.203 | 13,427.8 (66,015) | 5,458.9 (46,225) | 0.41x | compute |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x87 | 70,905 | 12,970.2 | 0.183 | 12,970.2 (70,905) | 4,970.0 (462,250) | 0.38x | compute |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x87 | 70,905 | 12,970.2 | 0.183 | 12,970.2 (70,905) | 4,970.0 (462,250) | 0.38x | compute |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x87 | 70,905 | 12,970.2 | 0.183 | 12,970.2 (70,905) | 4,970.0 (462,250) | 0.38x | compute |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x87 | 70,905 | 12,970.2 | 0.183 | 12,970.2 (70,905) | 4,659.2 (462,250) | 0.36x | compute |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x99 | 80,685 | 11,363.0 | 0.141 | 11,363.0 (80,685) | 3,993.4 (462,250) | 0.35x | compute |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x316-romfill | 257,540 | 10,757.0 | 0.042 | 10,757.0 (257,540) | 3,351.8 (554,700) | 0.31x | compute |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 4,112.9 | 0.015 | 4,112.9 (277,100) | 1,523.8 (554,700) | 0.37x | compute |
| DeepSeek-V4-Flash-0731 | 1024 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1,116.0 | 0.006 | 1,116.0 (185,005) | 519.4 (554,700) | 0.47x | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 423.3 | 0.002 | 423.3 (277,100) | 130.8 (554,700) | 0.31x | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | array | array | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227 | 185,005 | 4,341.7 | 0.023 | 4,341.7 (185,005) | 3,552.9 (277,350) | 0.82x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 0.001 | — (—) | 2,415.3 (3,050,850) | — | link_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 0.001 | — (—) | 2,415.3 (3,050,850) | — | link_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 0.001 | — (—) | 2,415.3 (3,050,850) | — | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 0.001 | — (—) | 2,415.3 (3,050,850) | — | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 0.001 | — (—) | 2,415.3 (3,050,850) | — | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 2,415.3 | 0.001 | — (—) | 2,415.3 (3,050,850) | — | link_latency |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 1,160.3 | 0.000 | — (—) | 1,160.3 (3,050,850) | — | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66 | 3,050,850 | 374.2 | 0.000 | — (—) | 374.2 (3,050,850) | — | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 103.4 | 0.000 | — (—) | 103.4 (3,050,850) | — | kv_read |

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
| Qwen3-8B | 1 | sram | 28,247.2 | 28,850.2 | 28,850.2 | 0.98x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 28,247.2 | 28,850.2 | 28,850.2 | 0.98x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 35,687.3 | 28,850.2 | 28,850.2 | 1.24x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 57,078.7 | 28,850.2 | 28,850.2 | 1.98x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 83,569.2 | 28,850.2 | 28,850.2 | 2.90x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 122,432.7 | 28,850.2 | 28,850.2 | 4.24x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 172,081.2 | 28,868.1 | 28,868.1 | 5.96x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 247,292.0 | 26,096.4 | 26,096.4 | 9.48x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1024 | sram | 374,687.0 | 26,107.0 | 26,107.0 | 14.35x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 4096 | sram | 462,949.4 | 26,111.3 | 26,111.3 | 17.73x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 459,793.9 | 110,891.5 | 110,891.5 | 4.15x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 459,793.9 | 110,891.5 | 110,891.5 | 4.15x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 459,793.9 | 110,891.5 | 110,891.5 | 4.15x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 459,793.9 | 110,891.5 | 110,891.5 | 4.15x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 459,793.9 | 110,891.5 | 110,891.5 | 4.15x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 459,793.9 | 110,891.5 | 110,891.5 | 4.15x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 459,793.9 | 110,891.5 | 110,891.5 | 4.15x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 459,793.9 | 111,701.4 | 111,701.4 | 4.12x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1024 | rom | 463,094.0 | 111,990.6 | 111,990.6 | 4.14x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4096 | rom | 464,336.4 | 112,063.1 | 112,063.1 | 4.14x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 384,602.4 | 26,092.0 | 26,092.0 | 14.74x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 384,602.4 | 26,092.0 | 26,092.0 | 14.74x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 384,602.4 | 26,092.0 | 26,092.0 | 14.74x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 384,602.4 | 26,092.0 | 43,575.4 | 14.74x | 1.67x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 384,602.4 | 26,092.0 | 71,301.6 | 14.74x | 2.73x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 384,602.4 | 26,092.0 | 109,459.0 | 14.74x | 4.20x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 510,884.3 | 26,092.0 | 156,156.1 | 19.58x | 5.98x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 822,341.8 | 26,092.0 | 288,242.2 | 31.52x | 11.05x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 1,192,139.8 | 26,103.1 | 359,492.6 | 45.67x | 13.77x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 1,733,692.1 | 26,110.2 | 438,541.1 | 66.40x | 16.80x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 1,096,516.4 | 441,218.7 | 441,218.7 | 2.49x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 1,096,516.4 | 441,218.7 | 441,218.7 | 2.49x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 1,096,516.4 | 441,218.7 | 441,218.7 | 2.49x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 1,096,516.4 | 441,218.7 | 441,218.7 | 2.49x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 1,096,516.4 | 441,218.7 | 441,218.7 | 2.49x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 1,096,516.4 | 441,218.7 | 441,218.7 | 2.49x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 1,096,516.4 | 441,218.7 | 441,218.7 | 2.49x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 1,096,516.4 | 441,218.7 | 441,218.7 | 2.49x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 1,129,894.1 | 443,927.9 | 443,927.9 | 2.55x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 1,142,863.5 | 446,489.2 | 446,489.2 | 2.56x | 1.00x | compute | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 423,449.9 | 26,108.6 | 26,108.6 | 16.22x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 423,449.9 | 26,108.6 | 26,108.6 | 16.22x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 423,449.9 | 26,108.6 | 26,108.6 | 16.22x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 423,449.9 | 26,108.6 | 26,108.6 | 16.22x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 423,449.9 | 26,108.6 | 27,666.3 | 16.22x | 1.06x | kv_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | sram | 423,449.9 | 26,108.6 | 50,929.1 | 16.22x | 1.95x | kv_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | sram | 423,449.9 | 26,108.6 | 90,040.4 | 16.22x | 3.45x | kv_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 256 | sram | 423,449.9 | 26,108.6 | 198,365.3 | 16.22x | 7.60x | kv_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 423,449.9 | 26,108.6 | 272,292.5 | 16.22x | 10.43x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 423,553.1 | 26,109.0 | 327,507.1 | 16.22x | 12.54x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 423,449.9 | 423,449.9 | 423,449.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 423,449.9 | 423,449.9 | 423,449.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 423,449.9 | 423,449.9 | 423,449.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 423,449.9 | 423,449.9 | 423,449.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 423,449.9 | 423,449.9 | 423,449.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 423,449.9 | 423,449.9 | 423,449.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 423,449.9 | 423,449.9 | 423,449.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 423,449.9 | 423,449.9 | 423,449.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 423,449.9 | 423,449.9 | 423,449.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 423,553.1 | 423,553.1 | 423,553.1 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,247.2 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 459,793.9 | 1.659 | kv_read | 16.28x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.02x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 3.93x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.02x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 3.93x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,247.2 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 459,793.9 | 1.659 | kv_read | 16.28x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.02x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 3.93x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.02x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 3.93x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x87 | 70,905 | 1.00 | 1.00 | 35,687.3 | 0.503 | link_latency | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 459,793.9 | 1.659 | kv_read | 12.88x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.81x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 3.11x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.81x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 3.11x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x138 | 112,470 | 1.00 | 1.00 | 57,078.7 | 0.508 | link_latency | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 459,793.9 | 1.659 | kv_read | 8.06x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.51x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 1.94x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.51x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 1.94x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x227 | 185,005 | 1.00 | 1.00 | 83,569.2 | 0.452 | link_latency | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 459,793.9 | 1.659 | kv_read | 5.50x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.35x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 1.33x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.35x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 1.33x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x340 | 277,100 | 1.00 | 1.00 | 122,432.7 | 0.442 | link_latency | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 459,793.9 | 1.659 | kv_read | 3.76x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.24x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 0.91x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.24x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 0.91x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x340 | 277,100 | 1.00 | 1.00 | 172,081.2 | 0.621 | link_latency | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 459,793.9 | 1.659 | kv_read | 2.67x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,868.1 | 0.625 | weight_read | 0.17x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 0.64x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 28,868.1 | 0.625 | weight_read | 0.17x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 1.00 | 110,891.5 | 1.659 | kv_read | 0.64x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-tensor-x340 | 277,100 | 1.00 | 1.00 | 247,292.0 | 0.892 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 459,793.9 | 1.659 | kv_read | 1.86x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream | 369,800 | 1.00 | 1.00 | 26,096.4 | 0.071 | weight_read | 0.11x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 3.12 | 111,701.4 | 1.671 | kv_read | 0.45x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion | 369,800 | 1.00 | 1.00 | 26,096.4 | 0.071 | weight_read | 0.11x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 3.12 | 111,701.4 | 1.671 | kv_read | 0.45x |
| Qwen3-8B | 1024 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276 | 224,940 | 1.00 | 1.00 | 374,687.0 | 1.666 | kv_read | 1.00x |
| Qwen3-8B | 1024 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 463,094.0 | 1.671 | kv_read | 1.24x |
| Qwen3-8B | 1024 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69-perstream | 56,235 | 1.00 | 14.84 | 26,107.0 | 0.464 | weight_read | 0.07x |
| Qwen3-8B | 1024 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 12.49 | 111,990.6 | 1.676 | kv_read | 0.30x |
| Qwen3-8B | 1024 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x69-perregion | 56,235 | 1.00 | 14.84 | 26,107.0 | 0.464 | weight_read | 0.07x |
| Qwen3-8B | 1024 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 12.49 | 111,990.6 | 1.676 | kv_read | 0.30x |
| Qwen3-8B | 4096 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 462,949.4 | 1.671 | kv_read | 1.00x |
| Qwen3-8B | 4096 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 50.24 | 1.00 | 464,336.4 | 1.676 | kv_read | 1.00x |
| Qwen3-8B | 4096 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perstream | 369,800 | 1.00 | 9.02 | 26,111.3 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 4096 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perstream-romfill | 66,830 | 43.05 | 49.95 | 112,063.1 | 1.677 | kv_read | 0.24x |
| Qwen3-8B | 4096 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x8-perregion | 369,800 | 1.00 | 9.02 | 26,111.3 | 0.071 | weight_read | 0.06x |
| Qwen3-8B | 4096 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-array-hw-pipeline-x82-perregion-romfill | 66,830 | 43.05 | 49.95 | 112,063.1 | 1.677 | kv_read | 0.24x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,096,516.4 | 3.957 | compute | 2.85x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,096,516.4 | 3.957 | compute | 2.85x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,096,516.4 | 3.957 | compute | 2.85x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,096,516.4 | 3.957 | compute | 2.85x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x79-perregion | 64,385 | 1.00 | 2.13 | 43,575.4 | 0.677 | link_latency | 0.11x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,096,516.4 | 3.957 | compute | 2.85x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x79-perregion | 64,385 | 1.00 | 2.88 | 71,301.6 | 1.107 | link_latency | 0.19x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,096,516.4 | 3.957 | compute | 2.85x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x79-perregion | 64,385 | 1.00 | 4.03 | 109,459.0 | 1.700 | weight_read | 0.28x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 1.15x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x119 | 96,985 | 1.00 | 1.00 | 510,884.3 | 5.268 | compute | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,096,516.4 | 3.957 | compute | 2.15x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 0.86x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x79-perregion | 64,385 | 1.00 | 5.83 | 156,156.1 | 2.425 | weight_read | 0.31x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 0.86x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 1.00 | 1.00 | 822,341.8 | 5.935 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,096,516.4 | 3.957 | compute | 1.33x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,092.0 | 0.056 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x10-perregion | 462,250 | 1.00 | 13.84 | 288,242.2 | 0.624 | kv_read | 0.35x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.00 | 441,218.7 | 0.955 | kv_read | 0.54x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x237 | 193,155 | 1.00 | 1.00 | 1,192,139.8 | 6.172 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,129,894.1 | 4.078 | compute | 0.95x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x79-perstream | 64,385 | 1.00 | 12.96 | 26,103.1 | 0.405 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 1.80 | 443,927.9 | 0.960 | kv_read | 0.37x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x10-perregion | 462,250 | 1.00 | 38.75 | 359,492.6 | 0.778 | kv_read | 0.30x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 1.10 | 443,927.9 | 0.960 | kv_read | 0.37x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 1,733,692.1 | 6.257 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.93 | 1.00 | 1,142,863.5 | 4.124 | compute | 0.66x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 7.21 | 26,110.2 | 0.056 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 31.86 | 7.21 | 446,489.2 | 0.966 | kv_read | 0.26x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 19.28 | 438,541.1 | 0.949 | kv_read | 0.25x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 31.86 | 2.06 | 446,489.2 | 0.966 | kv_read | 0.26x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x66-perregion | 3,050,850 | 1.00 | 2.54 | 27,666.3 | 0.009 | link_latency | 0.07x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x66-perregion | 3,050,850 | 1.00 | 3.49 | 50,929.1 | 0.017 | link_latency | 0.12x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x66-perregion | 3,050,850 | 1.00 | 4.92 | 90,040.4 | 0.030 | link_latency | 0.21x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x66-perregion | 3,050,850 | 1.00 | 10.96 | 198,365.3 | 0.065 | link_latency | 0.47x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.00 | 26,108.6 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x66-perregion | 3,050,850 | 1.00 | 28.90 | 272,292.5 | 0.089 | kv_read | 0.64x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.00 | 423,449.9 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66 | 3,050,850 | 1.00 | 1.00 | 423,553.1 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-romfill | 3,050,850 | 10.85 | 1.00 | 423,553.1 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream | 3,050,850 | 1.00 | 1.09 | 26,109.0 | 0.009 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perstream-romfill | 3,050,850 | 39.31 | 1.09 | 423,553.1 | 0.139 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66-perregion | 3,050,850 | 1.00 | 4.84 | 327,507.1 | 0.107 | weight_read | 0.77x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x66-perregion-romfill | 3,050,850 | 39.31 | 1.01 | 423,553.1 | 0.139 | kv_read | 1.00x |

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
| Qwen3-8B | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
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
| DeepSeek-V4-Flash-0731 | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4-Flash-0731 | 2 | 24 | 9.51 | 5.51 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 24 | 15.05 | 7.28 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 24 | 20.35 | 9.21 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 24 | 23.23 | 11.14 | 2.09x |
| DeepSeek-V4-Flash-0731 | 32 | 24 | 23.93 | 12.82 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 24 | 24.00 | 14.03 | 1.71x |
| DeepSeek-V4-Flash-0731 | 256 | 24 | 24.00 | 14.78 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 24 | 24.00 | 14.79 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 2 | 28 | 9.81 | 5.76 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 28 | 15.94 | 7.73 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 28 | 22.40 | 9.90 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 28 | 26.52 | 12.12 | 2.19x |
| DeepSeek-V4-Flash-0731 | 32 | 28 | 27.80 | 14.09 | 1.97x |
| DeepSeek-V4-Flash-0731 | 64 | 28 | 27.98 | 15.53 | 1.80x |
| DeepSeek-V4-Flash-0731 | 256 | 28 | 28.00 | 16.42 | 1.70x |
| DeepSeek-V4-Flash-0731 | 1024 | 28 | 28.00 | 16.43 | 1.70x |
| DeepSeek-V4-Flash-0731 | 1 | 34 | 5.58 | 4.44 | 1.26x |
| DeepSeek-V4-Flash-0731 | 2 | 34 | 10.14 | 6.09 | 1.66x |
| DeepSeek-V4-Flash-0731 | 4 | 34 | 16.97 | 8.30 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 34 | 24.92 | 10.80 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 34 | 30.96 | 13.41 | 2.31x |
| DeepSeek-V4-Flash-0731 | 32 | 34 | 33.42 | 15.79 | 2.12x |
| DeepSeek-V4-Flash-0731 | 64 | 34 | 33.91 | 17.56 | 1.93x |
| DeepSeek-V4-Flash-0731 | 256 | 34 | 33.98 | 18.68 | 1.82x |
| DeepSeek-V4-Flash-0731 | 1024 | 34 | 33.98 | 18.69 | 1.82x |
| DeepSeek-V4-Flash-0731 | 1 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 2 | 39 | 10.34 | 6.32 | 1.64x |
| DeepSeek-V4-Flash-0731 | 4 | 39 | 17.64 | 8.71 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 39 | 26.64 | 11.45 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 39 | 34.22 | 14.37 | 2.38x |
| DeepSeek-V4-Flash-0731 | 32 | 39 | 37.86 | 17.07 | 2.22x |
| DeepSeek-V4-Flash-0731 | 64 | 39 | 38.78 | 19.11 | 2.03x |
| DeepSeek-V4-Flash-0731 | 256 | 39 | 38.95 | 20.40 | 1.91x |
| DeepSeek-V4-Flash-0731 | 1024 | 39 | 38.95 | 20.41 | 1.91x |
| DeepSeek-V4-Flash-0731 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 43 | 10.47 | 6.49 | 1.61x |
| DeepSeek-V4-Flash-0731 | 4 | 43 | 18.07 | 9.00 | 2.01x |
| DeepSeek-V4-Flash-0731 | 8 | 43 | 27.82 | 11.92 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 43 | 36.58 | 15.07 | 2.43x |
| DeepSeek-V4-Flash-0731 | 32 | 43 | 41.25 | 18.02 | 2.29x |
| DeepSeek-V4-Flash-0731 | 64 | 43 | 42.61 | 20.26 | 2.10x |
| DeepSeek-V4-Flash-0731 | 256 | 43 | 42.89 | 21.69 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1024 | 43 | 42.90 | 21.70 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 52 | 10.70 | 6.83 | 1.57x |
| DeepSeek-V4-Flash-0731 | 4 | 52 | 18.84 | 9.55 | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | 52 | 29.98 | 12.84 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 52 | 41.18 | 16.47 | 2.50x |
| DeepSeek-V4-Flash-0731 | 32 | 52 | 48.30 | 19.94 | 2.42x |
| DeepSeek-V4-Flash-0731 | 64 | 52 | 50.93 | 22.62 | 2.25x |
| DeepSeek-V4-Flash-0731 | 256 | 52 | 51.64 | 24.35 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1024 | 52 | 51.64 | 24.37 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1 | 53 | 5.72 | 4.83 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 53 | 10.72 | 6.86 | 1.56x |
| DeepSeek-V4-Flash-0731 | 4 | 53 | 18.91 | 9.60 | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | 53 | 30.18 | 12.93 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 53 | 41.64 | 16.61 | 2.51x |
| DeepSeek-V4-Flash-0731 | 32 | 53 | 49.04 | 20.14 | 2.44x |
| DeepSeek-V4-Flash-0731 | 64 | 53 | 51.82 | 22.86 | 2.27x |
| DeepSeek-V4-Flash-0731 | 256 | 53 | 52.59 | 24.63 | 2.14x |
| DeepSeek-V4-Flash-0731 | 1024 | 53 | 52.60 | 24.65 | 2.13x |
| DeepSeek-V4-Flash-0731 | 1 | 54 | 5.73 | 4.85 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 54 | 10.74 | 6.89 | 1.56x |
| DeepSeek-V4-Flash-0731 | 4 | 54 | 18.98 | 9.65 | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | 54 | 30.38 | 13.02 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 54 | 42.08 | 16.75 | 2.51x |
| DeepSeek-V4-Flash-0731 | 32 | 54 | 49.76 | 20.33 | 2.45x |
| DeepSeek-V4-Flash-0731 | 64 | 54 | 52.71 | 23.10 | 2.28x |
| DeepSeek-V4-Flash-0731 | 256 | 54 | 53.54 | 24.90 | 2.15x |
| DeepSeek-V4-Flash-0731 | 1024 | 54 | 53.55 | 24.92 | 2.15x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 10.77 | 6.96 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 19.11 | 9.76 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 30.77 | 13.20 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 42.95 | 17.03 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 51.18 | 20.71 | 2.47x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 54.47 | 23.58 | 2.31x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 55.44 | 25.44 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1024 | 56 | 55.44 | 25.46 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1 | 63 | 5.77 | 4.97 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 63 | 10.89 | 7.17 | 1.52x |
| DeepSeek-V4-Flash-0731 | 4 | 63 | 19.51 | 10.08 | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | 63 | 31.96 | 13.78 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 63 | 45.72 | 17.93 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 63 | 55.87 | 21.98 | 2.54x |
| DeepSeek-V4-Flash-0731 | 64 | 63 | 60.43 | 25.16 | 2.40x |
| DeepSeek-V4-Flash-0731 | 256 | 63 | 61.94 | 27.24 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1024 | 63 | 61.95 | 27.26 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 69 | 10.97 | 7.34 | 1.49x |
| DeepSeek-V4-Flash-0731 | 4 | 69 | 19.80 | 10.33 | 1.92x |
| DeepSeek-V4-Flash-0731 | 8 | 69 | 32.83 | 14.23 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 69 | 47.80 | 18.64 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 69 | 59.55 | 22.98 | 2.59x |
| DeepSeek-V4-Flash-0731 | 64 | 69 | 65.27 | 26.42 | 2.47x |
| DeepSeek-V4-Flash-0731 | 256 | 69 | 67.34 | 28.68 | 2.35x |
| DeepSeek-V4-Flash-0731 | 1024 | 69 | 67.36 | 28.71 | 2.35x |
| DeepSeek-V4-Flash-0731 | 1 | 78 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 78 | 11.07 | 7.57 | 1.46x |
| DeepSeek-V4-Flash-0731 | 4 | 78 | 20.16 | 10.66 | 1.89x |
| DeepSeek-V4-Flash-0731 | 8 | 78 | 33.93 | 14.86 | 2.28x |
| DeepSeek-V4-Flash-0731 | 16 | 78 | 50.52 | 19.62 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 78 | 64.54 | 24.37 | 2.65x |
| DeepSeek-V4-Flash-0731 | 64 | 78 | 72.09 | 28.17 | 2.56x |
| DeepSeek-V4-Flash-0731 | 256 | 78 | 75.11 | 30.70 | 2.45x |
| DeepSeek-V4-Flash-0731 | 1024 | 78 | 75.13 | 30.72 | 2.45x |
| DeepSeek-V4-Flash-0731 | 1 | 80 | 5.82 | 5.14 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 80 | 11.09 | 7.62 | 1.45x |
| DeepSeek-V4-Flash-0731 | 4 | 80 | 20.23 | 10.73 | 1.89x |
| DeepSeek-V4-Flash-0731 | 8 | 80 | 34.14 | 14.99 | 2.28x |
| DeepSeek-V4-Flash-0731 | 16 | 80 | 51.06 | 19.83 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 80 | 65.57 | 24.66 | 2.66x |
| DeepSeek-V4-Flash-0731 | 64 | 80 | 73.53 | 28.54 | 2.58x |
| DeepSeek-V4-Flash-0731 | 256 | 80 | 76.78 | 31.12 | 2.47x |
| DeepSeek-V4-Flash-0731 | 1024 | 80 | 76.80 | 31.15 | 2.47x |
| DeepSeek-V4-Flash-0731 | 1 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 81 | 11.10 | 7.65 | 1.45x |
| DeepSeek-V4-Flash-0731 | 4 | 81 | 20.26 | 10.76 | 1.88x |
| DeepSeek-V4-Flash-0731 | 8 | 81 | 34.25 | 15.06 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 81 | 51.33 | 19.93 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 81 | 66.07 | 24.80 | 2.66x |
| DeepSeek-V4-Flash-0731 | 64 | 81 | 74.24 | 28.72 | 2.58x |
| DeepSeek-V4-Flash-0731 | 256 | 81 | 77.61 | 31.33 | 2.48x |
| DeepSeek-V4-Flash-0731 | 1024 | 81 | 77.63 | 31.36 | 2.48x |
| DeepSeek-V4-Flash-0731 | 1 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 82 | 11.10 | 7.67 | 1.45x |
| DeepSeek-V4-Flash-0731 | 4 | 82 | 20.29 | 10.79 | 1.88x |
| DeepSeek-V4-Flash-0731 | 8 | 82 | 34.35 | 15.12 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 82 | 51.59 | 20.03 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 82 | 66.57 | 24.94 | 2.67x |
| DeepSeek-V4-Flash-0731 | 64 | 82 | 74.94 | 28.90 | 2.59x |
| DeepSeek-V4-Flash-0731 | 256 | 82 | 78.43 | 31.54 | 2.49x |
| DeepSeek-V4-Flash-0731 | 1024 | 82 | 78.45 | 31.57 | 2.49x |
| DeepSeek-V4-Flash-0731 | 4096 | 82 | 78.45 | 31.57 | 2.49x |
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
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1 | 125 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 125 | 11.40 | 8.49 | 1.34x |
| DeepSeek-V4-Pro-0813 | 4 | 125 | 21.45 | 11.99 | 1.79x |
| DeepSeek-V4-Pro-0813 | 8 | 125 | 38.23 | 17.62 | 2.17x |
| DeepSeek-V4-Pro-0813 | 16 | 125 | 62.11 | 24.16 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 125 | 88.13 | 31.52 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 125 | 107.37 | 38.43 | 2.79x |
| DeepSeek-V4-Pro-0813 | 256 | 125 | 118.96 | 45.37 | 2.62x |
| DeepSeek-V4-Pro-0813 | 1 | 166 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 166 | 11.52 | 9.01 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 166 | 21.92 | 12.81 | 1.71x |
| DeepSeek-V4-Pro-0813 | 8 | 166 | 39.87 | 19.11 | 2.09x |
| DeepSeek-V4-Pro-0813 | 16 | 166 | 66.99 | 26.58 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 166 | 99.75 | 35.37 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 166 | 127.96 | 43.82 | 2.92x |
| DeepSeek-V4-Pro-0813 | 256 | 166 | 149.01 | 52.50 | 2.84x |
| DeepSeek-V4-Pro-0813 | 1024 | 166 | 149.69 | 52.87 | 2.83x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4-Pro-0813 | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4-Pro-0813 | 1 | 177 | 5.92 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 177 | 11.55 | 9.13 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 177 | 22.02 | 13.01 | 1.69x |
| DeepSeek-V4-Pro-0813 | 8 | 177 | 40.19 | 19.42 | 2.07x |
| DeepSeek-V4-Pro-0813 | 16 | 177 | 67.98 | 27.13 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 177 | 102.19 | 36.27 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 177 | 132.54 | 45.08 | 2.94x |
| DeepSeek-V4-Pro-0813 | 256 | 177 | 156.11 | 54.18 | 2.88x |
| DeepSeek-V4-Pro-0813 | 1024 | 177 | 156.90 | 54.57 | 2.88x |
| DeepSeek-V4-Pro-0813 | 1 | 206 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 206 | 11.60 | 9.39 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 206 | 22.21 | 13.48 | 1.65x |
| DeepSeek-V4-Pro-0813 | 8 | 206 | 40.88 | 20.13 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 206 | 70.13 | 28.48 | 2.46x |
| DeepSeek-V4-Pro-0813 | 32 | 206 | 107.69 | 38.46 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 206 | 143.12 | 48.15 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 206 | 173.13 | 58.27 | 2.97x |
| DeepSeek-V4-Pro-0813 | 1024 | 206 | 174.21 | 58.70 | 2.97x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1 | 233 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 233 | 11.63 | 9.59 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 233 | 22.35 | 13.89 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 233 | 41.38 | 20.66 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 233 | 71.72 | 29.63 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 233 | 111.83 | 40.28 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 233 | 151.37 | 50.69 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 233 | 187.00 | 61.70 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1024 | 233 | 188.32 | 62.18 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 234 | 11.63 | 9.60 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 234 | 22.35 | 13.91 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 234 | 41.39 | 20.68 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 234 | 71.77 | 29.67 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 234 | 111.96 | 40.35 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 234 | 151.65 | 50.78 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 234 | 187.48 | 61.82 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1024 | 234 | 188.81 | 62.30 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 280 | 11.68 | 9.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 280 | 22.53 | 14.53 | 1.55x |
| DeepSeek-V4-Pro-0813 | 8 | 280 | 42.03 | 21.42 | 1.96x |
| DeepSeek-V4-Pro-0813 | 16 | 280 | 73.81 | 31.44 | 2.35x |
| DeepSeek-V4-Pro-0813 | 32 | 280 | 117.46 | 42.98 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 280 | 162.98 | 54.48 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 280 | 207.38 | 66.94 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1024 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1 | 308 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 308 | 11.70 | 10.02 | 1.17x |
| DeepSeek-V4-Pro-0813 | 4 | 308 | 22.61 | 14.87 | 1.52x |
| DeepSeek-V4-Pro-0813 | 8 | 308 | 42.32 | 21.80 | 1.94x |
| DeepSeek-V4-Pro-0813 | 16 | 308 | 74.79 | 32.40 | 2.31x |
| DeepSeek-V4-Pro-0813 | 32 | 308 | 120.13 | 44.32 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 308 | 168.63 | 56.46 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 308 | 217.67 | 69.71 | 3.12x |
| DeepSeek-V4-Pro-0813 | 1024 | 308 | 219.65 | 70.30 | 3.12x |
| DeepSeek-V4-Pro-0813 | 1 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 324 | 11.71 | 10.09 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 324 | 22.65 | 15.05 | 1.50x |
| DeepSeek-V4-Pro-0813 | 8 | 324 | 42.47 | 22.00 | 1.93x |
| DeepSeek-V4-Pro-0813 | 16 | 324 | 75.27 | 32.91 | 2.29x |
| DeepSeek-V4-Pro-0813 | 32 | 324 | 121.48 | 45.03 | 2.70x |
| DeepSeek-V4-Pro-0813 | 64 | 324 | 171.53 | 57.52 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 324 | 223.03 | 71.21 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1024 | 324 | 225.14 | 71.81 | 3.14x |
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
| DeepSeek-V4-Pro-0813 | 1 | 338 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 338 | 11.72 | 10.14 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 338 | 22.68 | 15.20 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 338 | 42.59 | 22.17 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 338 | 75.66 | 33.33 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 338 | 122.57 | 45.60 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 338 | 173.89 | 58.43 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 338 | 227.45 | 72.49 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 338 | 229.66 | 73.10 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 373 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 373 | 11.73 | 10.27 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 373 | 22.75 | 15.57 | 1.46x |
| DeepSeek-V4-Pro-0813 | 8 | 373 | 42.85 | 22.57 | 1.90x |
| DeepSeek-V4-Pro-0813 | 16 | 373 | 76.52 | 34.31 | 2.23x |
| DeepSeek-V4-Pro-0813 | 32 | 373 | 124.98 | 46.94 | 2.66x |
| DeepSeek-V4-Pro-0813 | 64 | 373 | 179.17 | 60.59 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 373 | 237.50 | 75.51 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 373 | 239.95 | 76.15 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 386 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 386 | 11.74 | 10.32 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 386 | 22.77 | 15.69 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 386 | 42.93 | 22.71 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 386 | 76.81 | 34.64 | 2.22x |
| DeepSeek-V4-Pro-0813 | 32 | 386 | 125.78 | 47.40 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 386 | 180.94 | 61.36 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 386 | 240.90 | 76.58 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 386 | 243.44 | 77.23 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 387 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 387 | 11.74 | 10.32 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 387 | 22.78 | 15.70 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 387 | 42.94 | 22.72 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 387 | 76.83 | 34.66 | 2.22x |
| DeepSeek-V4-Pro-0813 | 32 | 387 | 125.84 | 47.44 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 387 | 181.07 | 61.42 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 387 | 241.16 | 76.66 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 387 | 243.71 | 77.31 | 3.15x |
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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 1.4% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 1.2% |
| gpu | Qwen3-8B | 1 | 6.82 | 0.9% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 17.2% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 9.4% |
| rom | Qwen3-8B | 1 | 6.82 | 23.5% |

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
| Qwen3-8B | 2 | 1 | 1.40% | 7.40 | 9.27 |
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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 408.2 | 28,168.3 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 408.2 | 28,168.3 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 408.2 | 28,168.3 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 408.2 | 28,168.3 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 408.2 | 28,168.3 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 408.2 | 28,168.3 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 408.2 | 28,168.3 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 367.4 | 94,044.0 |
| Qwen3-8B | 1024 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 92.0 | 94,248.8 |
| Qwen3-8B | 4096 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 23.0 | 94,300.2 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 3,676.4 | 290,438.6 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 3,676.4 | 290,438.6 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 3,676.4 | 290,438.6 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 3,676.4 | 290,438.6 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 3,676.4 | 290,438.6 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 3,676.4 | 290,438.6 |
| DeepSeek-V4-Flash-0731 | 64 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 3,676.4 | 290,438.6 |
| DeepSeek-V4-Flash-0731 | 256 | 7.40% | 18.7 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,175.5 | 300,927.9 |
| DeepSeek-V4-Flash-0731 | 1024 | 26.47% | 46.7 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 297.5 | 304,610.6 |
| DeepSeek-V4-Flash-0731 | 4096 | 70.76% | 111.9 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 74.6 | 305,545.3 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 113.1 | 423,449.9 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 113.1 | 423,449.9 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 113.1 | 423,449.9 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 113.1 | 423,449.9 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 113.1 | 423,449.9 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 113.1 | 423,449.9 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 113.1 | 423,449.9 |
| DeepSeek-V4-Pro-0813 | 256 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 113.1 | 423,449.9 |
| DeepSeek-V4-Pro-0813 | 1024 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 113.1 | 423,449.9 |
| DeepSeek-V4-Pro-0813 | 4096 | 1.71% | 40.9 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 103.4 | 423,553.1 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 52 |
| gpu | infeasible | 231 |
| gpu | kv_read | 105 |
| gpu | link_latency | 774 |
| gpu | weight_read | 2068 |
| rom | compute | 639 |
| rom | infeasible | 6709 |
| rom | kv_read | 1166 |
| rom | link_latency | 1852 |
| rom | weight_read | 1164 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 231 |
| rom | CAPACITY | 6709 |

## Mechanical consistency audit

**FAIL** over 258,817 checks.

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

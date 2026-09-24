# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 18x (ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream, 114 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 143 devices. On the GPU side the correction reaches 9x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 53 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash takes 126 x 815 mm2 (102,690 mm2, array, KV in SRAM) at 3,666 tok/s per user and 36 tok/s per 1,000 mm2, holding 1 session, against 124 copies of one unified HBM die at the same silicon: 10.0x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash on 278,730 mm2 of ROM silicon at 4,124 tok/s per user against 278,362 mm2 of a100_sxm_80gb-x337-hybrid at 355 tok/s: **11.6x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 136,267 resident sessions against the GPU cluster's 131,451. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on DeepSeek-V4.1-Flash at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 1,161 us of link latency per token; but the model has 40 layers, so at most 40 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 1,054 us. The iso-area per-user ratio at that point falls from 10.3x to 9.9x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 3.08x to it.** At 92,450 mm2 on DeepSeek-V4.1-Flash the pipeline-only GPU delivers 120.59 tok/s and the same silicon running hybrid delivers 371 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.01x (DeepSeek-V4.1-Flash, ROM binding on `link_latency`) to 10.41x (DeepSeek-V4.1-Flash, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 438 to 51,855 tok/s, and its rate with every slot occupied from 49,884 to 51,855. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 114 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 171.8 us and cap it at 5,821 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 9 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 47 of 3752 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 94.4x of aggregate throughput (DeepSeek-V4.1-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 16.45x, on DeepSeek-V4.1-Flash at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4.1-Flash at 200,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-hybrid-x126`** -- 126 x 815 mm2 reticle dies, 102,690 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **3,666.4 tok/s per user** (0.27 ms/token), binding on `layer_fixed_latency`
- **35.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,666 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 6,324 W at 0.062 W/mm2, 1,724.8 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 124 copies of one unified HBM die -- `a100_sxm_80gb-x124-hybrid`, 102,424 mm2, area ratio 1.0026 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 102,690 | 102,424 | 1.0026 |
| user tok/s | 3,666.4 | 366.3 | 10.01x |
| aggregate tok/s | 3,666 | 5,860 | 0.25x |
| resident sessions | 1 | 46,583 | -- |
| J/token | 1.7248 | 50.2586 | 29.1x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 46,583 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 375.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 116,545 | 3,972.5 | 34.1 | 56,977 | 10.84x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 4,144.8 | 19.5 | 103,993 | 11.56x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-hybrid-x109` | 88,835 | 2,507.9 | 28.2 | 1 | 6.84x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-hybrid-x126` | 102,690 | 3,666.4 | 35.7 | 1 | 10.01x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x126` | 102,690 | 3,666.4 | 35.7 | -- | 35.7 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x132` | 107,580 | 3,671.4 | 34.1 | 1.0 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 116,545 | 3,972.5 | 34.1 | 22.1 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x169` | 137,735 | 4,051.9 | 29.4 | 11.0 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x170` | 138,550 | 4,054.6 | 29.3 | 10.8 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x171` | 139,365 | 4,057.2 | 29.1 | 10.7 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x205-romfill` | 167,075 | 4,137.5 | 24.8 | 7.3 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 167,890 | 4,138.5 | 24.7 | 7.2 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 4,139.6 | 22.4 | 5.7 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,140.4 | 22.3 | 5.7 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x258` | 210,270 | 4,143.6 | 19.7 | 4.4 | 35.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 4,144.8 | 19.5 | 4.3 | 35.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x126` **<-- recommended** | 102,690 | 126 | 3,666.4 | 3,666 | 35.7 | 1 | `layer_fixed_latency` | 6,324 | 1,724.8 | `a100_sxm_80gb-x124-hybrid` | 10.01x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x132` | 107,580 | 132 | 3,671.4 | 3,671 | 34.1 | 1 | `layer_fixed_latency` | 6,833 | 1,861.3 | `a100_sxm_80gb-x130-hybrid` | 10.08x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 116,545 | 143 | 3,972.5 | 35,753 | 34.1 | 56,977 | `layer_fixed_latency` | 10,579 | 2,560.1 | `a100_sxm_80gb-x141-hybrid` | 10.84x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x169` | 137,735 | 169 | 4,051.9 | 44,571 | 29.4 | 67,336 | `layer_fixed_latency` | 14,129 | 3,358.3 | `a100_sxm_80gb-x167-hybrid` | 11.05x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x170` | 138,550 | 170 | 4,054.6 | 44,601 | 29.3 | 67,735 | `layer_fixed_latency` | 14,262 | 3,388.7 | `a100_sxm_80gb-x168-hybrid` | 11.03x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x171` | 139,365 | 171 | 4,057.2 | 44,629 | 29.1 | 68,133 | `layer_fixed_latency` | 14,394 | 3,419.1 | `a100_sxm_80gb-x169-hybrid` | 11.20x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x205-romfill` | 167,075 | 205 | 4,137.5 | 53,787 | 24.8 | 81,680 | `layer_fixed_latency` | 19,006 | 4,439.2 | `a100_sxm_80gb-x202-hybrid` | 11.45x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x206-romfill` | 167,890 | 206 | 4,138.5 | 53,801 | 24.7 | 82,079 | `layer_fixed_latency` | 19,138 | 4,470.0 | `a100_sxm_80gb-x203-hybrid` | 11.43x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 227 | 4,139.6 | 62,095 | 22.4 | 90,446 | `layer_fixed_latency` | 22,021 | 5,139.3 | `a100_sxm_80gb-x224-hybrid` | 11.38x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 228 | 4,140.4 | 62,106 | 22.3 | 90,845 | `layer_fixed_latency` | 22,153 | 5,170.3 | `a100_sxm_80gb-x225-hybrid` | 11.51x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x258` | 210,270 | 258 | 4,143.6 | 70,442 | 19.7 | 102,798 | `layer_fixed_latency` | 26,226 | 6,123.2 | `a100_sxm_80gb-x255-hybrid` | 11.47x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 261 | 4,144.8 | 70,461 | 19.5 | 103,993 | `layer_fixed_latency` | 26,623 | 6,217.3 | `a100_sxm_80gb-x258-hybrid` | 11.56x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 288 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x126` | 102,690 | 3,666.4 | 35.7 | 1 |
| array | 288 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 4,144.8 | 19.5 | 103,993 |
| array | 288 | smallest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x109` | 88,835 | 2,507.9 | 28.2 | 1 |
| wafer | 72 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2,443.2 | 26.4 | 1 |
| wafer | 72 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | 19.7 | 13,706 |
| wafer | 72 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2,443.2 | 26.4 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 4,144.8 | 70,461 | 103,993 | 26,623 | 6,217.3 | `layer_fixed_latency` | `a100_sxm_80gb-x258-hybrid` | 358.7 | 99,974 | 105,236.7 | 0.998 | 11.56x | 16.9x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | 105,465 | 13,706 | 19,867 | 5,102.6 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 363.9 | 86,427 | 90,262.6 | 0.999 | 9.99x | 17.7x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,140.4 | 62,106 | 90,845 | 22,153 | 5,170.3 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 359.8 | 86,825 | 91,672.4 | 1.000 | 11.51x | 17.7x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | -- | 13,706 | -- | 5,102.6 | -- | -- | -- | -- | -- | 1.005 | 0.88x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 4,144.8 | 70,461 | 103,993 | 26,623 | 3,115.1 | `layer_fixed_latency` | `a100_sxm_80gb-x258-hybrid` | 358.7 | 99,974 | 53,307.8 | 0.998 | 11.56x | 17.1x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | 105,465 | 13,706 | 19,867 | 2,557.7 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 363.9 | 86,427 | 45,820.8 | 0.999 | 9.99x | 17.9x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,140.4 | 62,106 | 90,845 | 22,153 | 2,591.6 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 359.8 | 86,825 | 46,525.7 | 1.000 | 11.51x | 18.0x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | -- | 13,706 | -- | 2,557.7 | -- | -- | -- | -- | -- | 1.005 | 0.88x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 4,144.8 | 70,461 | 103,993 | 26,623 | 1,564.0 | `layer_fixed_latency` | `a100_sxm_80gb-x258-hybrid` | 358.7 | 99,974 | 27,343.4 | 0.998 | 11.56x | 17.5x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | 105,465 | 13,706 | 19,867 | 1,285.3 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 363.9 | 86,427 | 23,599.9 | 0.999 | 9.99x | 18.4x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,140.4 | 62,106 | 90,845 | 22,153 | 1,302.2 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 359.8 | 86,825 | 23,952.3 | 1.000 | 11.51x | 18.4x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | -- | 13,706 | -- | 1,285.3 | -- | -- | -- | -- | -- | 1.005 | 0.88x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 4,144.8 | 70,461 | 103,993 | 26,623 | 788.4 | `layer_fixed_latency` | `a100_sxm_80gb-x258-hybrid` | 358.7 | 99,974 | 14,361.2 | 0.998 | 11.56x | 18.2x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | 105,465 | 13,706 | 19,867 | 649.1 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 363.9 | 86,427 | 12,489.4 | 0.999 | 9.99x | 19.2x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,140.4 | 62,106 | 90,845 | 22,153 | 657.6 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 359.8 | 86,825 | 12,665.6 | 1.000 | 11.51x | 19.3x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | -- | 13,706 | -- | 649.1 | -- | -- | -- | -- | -- | 1.005 | 0.88x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 4,144.8 | 70,461 | 103,993 | 26,623 | 400.6 | `layer_fixed_latency` | `a100_sxm_80gb-x258-hybrid` | 358.7 | 99,974 | 7,870.1 | 0.998 | 11.56x | 19.6x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | 105,465 | 13,706 | 19,867 | 331.0 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 363.9 | 86,427 | 6,934.2 | 0.999 | 9.99x | 21.0x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,092.3 | 65,477 | 90,845 | 22,186 | 338.8 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 359.8 | 86,825 | 7,022.3 | 1.000 | 11.37x | 20.7x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,636.7 | -- | 13,706 | -- | 331.0 | -- | -- | -- | -- | -- | 1.005 | 0.89x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 4,089.0 | 134,938 | 103,993 | 27,452 | 209.4 | `layer_fixed_latency` | `a100_sxm_80gb-x258-hybrid` | 358.7 | 99,974 | 4,624.5 | 0.998 | 11.40x | 22.1x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 3,582.7 | 154,058 | 20,559 | 34,139 | 293.3 | `layer_fixed_latency` | `a100_sxm_80gb-x336-hybrid` | 357.8 | 131,052 | 5,616.0 | 0.999 | 10.01x | 19.1x |
| 32 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 4,051.4 | 174,211 | 136,267 | 38,664 | 293.8 | `layer_fixed_latency` | `a100_sxm_80gb-x337-hybrid` | 355.5 | 131,451 | 5,656.5 | 1.001 | 11.40x | 19.3x |
| 32 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 3,582.7 | -- | 20,559 | -- | 293.3 | -- | -- | -- | -- | -- | 1.005 | 0.88x wafer/array | -- |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x261` | 212,715 | 3,982.2 | 262,822 | 103,993 | 29,098 | 113.8 | `layer_fixed_latency` | `a100_sxm_80gb-x258-hybrid` | 317.5 | 99,974 | 2,774.9 | 0.998 | 12.54x | 24.4x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,551.0 | 305,383 | 41,119 | 55,508 | 239.8 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 357.8 | 264,929 | 5,616.0 | 0.999 | 9.92x | 23.4x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 3,006.5 | 769,670 | 135,470 | 45,376 | 59.0 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 210.7 | 130,654 | 1,508.4 | 1.001 | 14.27x | 25.6x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,082.4 | 789,100 | 41,119 | 61,038 | 77.4 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 278.5 | 264,929 | 2,130.3 | 0.999 | 11.07x | 27.5x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | 1,196.0 | 1,224,692 | 136,267 | 50,003 | 40.8 | `compute` | `a100_sxm_80gb-x337-hybrid` | 94.1 | 131,451 | 1,023.7 | 1.001 | 12.71x | 25.1x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,667.0 | 1,707,059 | 41,119 | 72,029 | 42.2 | `compute` | `a100_sxm_80gb-x672-hybrid` | 144.9 | 264,929 | 1,265.6 | 0.999 | 11.51x | 30.0x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | 331.6 | 1,358,437 | 136,267 | 50,461 | 37.1 | `compute` | `a100_sxm_80gb-x337-hybrid` | 36.8 | 131,451 | 589.0 | 1.001 | 9.02x | 15.9x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 602.0 | 2,465,957 | 41,119 | 98,578 | 40.0 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 57.8 | 264,929 | 852.1 | 0.999 | 10.41x | 21.3x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x126` | 102,690 | array | SRAM | 1 |
| 2-16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 116,545 | array | HBM | 56,977 |
| 32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x169` | 137,735 | array | HBM | 67,336 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x205-romfill` | 167,075 | array | HBM | 81,680 |
| 256 | `ROM-N6-native-HBMKV-wafer-pipeline-x4` | 184,900 | wafer | HBM | 13,706 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | array | HBM | 136,267 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash | HBM | rom | 117, 119, 143, 169, 170, 171, 205, 206, 227, 228, 340, 342 |
| DeepSeek-V4.1-Flash | HBM | sram | 117, 119, 143, 169, 170, 171, 227, 228, 258, 261, 340, 342 |
| DeepSeek-V4.1-Flash | SRAM | rom | 109, 113, 115, 126, 132, 135, 158, 170, 210, 227, 315, 340 |
| DeepSeek-V4.1-Flash | SRAM | sram | 109, 113, 115, 126, 132, 135, 158, 170, 210, 227, 315, 340 |

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
| DeepSeek-V4.1-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x126` | 1 | 32 | 6.25 | hierarchical, one_shot | 201.24 | 48.77 | 27.17 | 48.82 | 3,666.4 |
| DeepSeek-V4.1-Flash | `a100_sxm_80gb-x124-hybrid` | 1 | 8 | 5.25 | measured_floor | 860.60 | 961.06 | 1,023.27 | 453.81 | 366.3 |
| DeepSeek-V4.1-Flash | `a100_sxm_80gb-x124-hybrid` | 64 | 8 | 5.25 | measured_floor | 860.60 | 1,091.80 | 2,062.79 | 493.75 | 264.2 |

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 10,802.5 tok/s | 0.64x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 77.8 W | 0.31x | within 2x | FAIL |

HC1 binds on `layer_fixed_latency`. Its component times are weight_read 34.47 us, kv_read 3.13 us, compute 34.47 us, link_latency 0.00 us, layer_fixed_latency 59.54 us.

The model **under**-predicts the shipping part by 1.57x. Rather than tune the densities until the anchor
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
| range low | 1,368.9 ns/layer | 43.81 us | 6.06 us | 13,014.5 | 0.77x | layer_fixed_latency |
| range stated | 1,860.6 ns/layer | 59.54 us | 6.06 us | 10,802.5 | 0.64x | layer_fixed_latency |
| range high | 3,206.3 ns/layer | 102.60 us | 6.06 us | 7,497.8 | 0.44x | layer_fixed_latency |

The per-layer serial cost that would land the model exactly on the
published figure is **810.3 ns/layer**. It is reported so the distance between the measured chain and the one the shipping part implies is visible. It is never used as an input: a chain longer than it means the hardwired datapath modelled here is serially slower than HC1's.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 10,783.7 | 0.64x | layer_fixed_latency |
| 3.5 | 10,802.5 | 0.64x | layer_fixed_latency |
| 4.0 | 10,783.7 | 0.64x | layer_fixed_latency |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 11,698.3 | 0.69x | layer_fixed_latency |
| 1,536 | 11,242.9 | 0.66x | layer_fixed_latency |
| 2,048 | 10,802.5 | 0.64x | layer_fixed_latency |

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
| Taalas HC1 card power | 200.0-250.0 W | 77.8 W | 0.31x | FAIL |

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
| **total** | 461.7 W | 77.8 W |

On HC1 the enumerated static power is 52.2 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 57.0 W | 0.23x | 0.28x |
| stated | 461.7 W | 1.15x | 77.8 W | 0.31x | 0.39x |
| high | 698.3 W | 1.75x | 339.3 W | 1.36x | 1.70x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.31x of the top of its published band, **3.21x low**, against 2.57x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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
| Taalas HC1 (modelled reconstruction) | 0.007199 J/token | 77.8 | 10,802.5 |
| A100 80GB, weight-bound gate, same model and batch | 1.537721 J/token | 336.2 | 218.6 |

That is a factor of 214 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 2.6-3.2x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

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

- **0 of 3,752 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 40 | 0 | 55.6% | 80.2% | 0.388 | 71% |
| gpu | wafer (>=40,000 mm2) | 1,240 | 0 | 51.5% | 79.8% | 0.387 | 85% |
| rom | wafer (>=40,000 mm2) | 2,472 | 0 | 20.2% | 36.2% | 0.181 | 96% |

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
| DeepSeek-V4.1-Flash | 1 | 116,545 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 2.560119 | 10,579.2 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-hybrid` | 56.921233 | 29,456.1 | link_latency | 22.23x |
| DeepSeek-V4.1-Flash | 2 | 116,545 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 1.286495 | 10,579.2 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-hybrid` | 29.150100 | 29,456.1 | link_latency | 22.66x |
| DeepSeek-V4.1-Flash | 4 | 116,545 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 0.649683 | 10,579.2 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-hybrid` | 15.264534 | 29,456.1 | link_latency | 23.50x |
| DeepSeek-V4.1-Flash | 8 | 116,545 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 0.331277 | 10,579.2 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-hybrid` | 8.321751 | 29,456.1 | link_latency | 25.12x |
| DeepSeek-V4.1-Flash | 16 | 137,735 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x169` | 0.228028 | 14,670.5 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x167-hybrid` | 5.487633 | 34,733.7 | link_latency | 24.07x |
| DeepSeek-V4.1-Flash | 32 | 167,075 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x205-romfill` | 0.156548 | 19,885.5 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x202-hybrid` | 3.810901 | 42,736.4 | link_latency | 24.34x |
| DeepSeek-V4.1-Flash | 64 | 185,005 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 0.098310 | 24,335.8 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid` | 2.498233 | 49,632.2 | weight_read | 25.41x |
| DeepSeek-V4.1-Flash | 256 | 277,100 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.058955 | 45,376.1 | weight_read | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid` | 1.508351 | 81,358.5 | weight_read | 25.58x |
| DeepSeek-V4.1-Flash | 1024 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.042195 | 72,028.6 | compute | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid` | 1.265621 | 187,763.7 | weight_read | 29.99x |
| DeepSeek-V4.1-Flash | 4096 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.039975 | 98,577.7 | kv_read | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid` | 0.852057 | 201,876.9 | weight_read | 21.31x |

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
| DeepSeek-V4.1-Flash | 200,000 | 552 B | 510.3 GB | 7.40 | 0.047 GB | 0.181 GB | 278.7 |

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
| DeepSeek-V4.1-Flash | 2 | 92,450 | 4,082.3 | wafer-pipeline | 2,443.2 | wafer-hybrid | 1.67x | 977.0 | pipeline | 371.2 | hybrid | 2.63x | 4.18x | 6.58x | 1.58x |
| DeepSeek-V4.1-Flash | 3 | 138,675 | 4,236.0 | wafer-pipeline | 3,503.7 | wafer-hybrid | 1.21x | 997.5 | pipeline | 367.5 | hybrid | 2.71x | 4.25x | 9.53x | 2.24x |
| DeepSeek-V4.1-Flash | 4 | 184,900 | 4,241.5 | wafer-pipeline | 3,636.7 | wafer-hybrid | 1.17x | 1,008.0 | pipeline | 363.9 | hybrid | 2.77x | 4.21x | 9.99x | 2.38x |
| DeepSeek-V4.1-Flash | 6 | 277,350 | 4,242.9 | wafer-pipeline | 3,582.7 | wafer-hybrid | 1.18x | 1,018.7 | pipeline | 357.8 | hybrid | 2.85x | 4.16x | 10.01x | 2.40x |
| DeepSeek-V4.1-Flash | 8 | 369,800 | 4,243.2 | wafer-pipeline | 3,552.7 | wafer-hybrid | 1.19x | 1,024.2 | pipeline | 357.8 | hybrid | 2.86x | 4.14x | 9.93x | 2.40x |
| DeepSeek-V4.1-Flash | 12 | 554,700 | 4,243.4 | wafer-pipeline | 3,551.0 | wafer-hybrid | 1.19x | 1,029.7 | pipeline | 357.8 | hybrid | 2.88x | 4.12x | 9.92x | 2.41x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.58x to 2.41x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash | 1 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x261 | 212,715 | 4,144.8 | 70,460.8 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-hybrid | 213,108 | 1.00x | hybrid | 1,026.87 | 358.7 | 11,836.3 | link_latency | 11.56x | 2.26x | 34.37x | 11.56x |
| DeepSeek-V4.1-Flash | 1 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x109 | 88,835 | 2,507.9 | 2,507.9 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x108-hybrid | 89,208 | 1.00x | hybrid | 953.29 | 366.8 | 5,134.6 | link_latency | 6.84x | 0.19x | 20.80x | 6.84x |
| DeepSeek-V4.1-Flash | 2 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x261 | 212,715 | 4,144.8 | 70,460.8 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-hybrid | 213,108 | 1.00x | hybrid | 1,026.87 | 358.7 | 11,836.3 | link_latency | 11.56x | 2.26x | 34.37x | 11.56x |
| DeepSeek-V4.1-Flash | 2 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 2,341.6 | 18,732.4 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 953.29 | 371.2 | 5,196.7 | link_latency | 6.31x | 1.39x | 19.42x | 6.31x |
| DeepSeek-V4.1-Flash | 4 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x261 | 212,715 | 4,144.8 | 70,460.8 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-hybrid | 213,108 | 1.00x | hybrid | 1,026.87 | 358.7 | 11,836.3 | link_latency | 11.56x | 2.26x | 34.37x | 11.56x |
| DeepSeek-V4.1-Flash | 4 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 2,341.6 | 18,732.4 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 953.29 | 371.2 | 5,196.7 | link_latency | 6.31x | 1.39x | 19.42x | 6.31x |
| DeepSeek-V4.1-Flash | 8 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x261 | 212,715 | 4,144.8 | 70,460.8 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-hybrid | 213,108 | 1.00x | hybrid | 1,026.87 | 358.7 | 11,836.3 | link_latency | 11.56x | 2.26x | 34.37x | 11.56x |
| DeepSeek-V4.1-Flash | 8 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 2,341.6 | 18,732.4 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 953.29 | 371.2 | 5,196.7 | link_latency | 6.31x | 1.39x | 19.42x | 6.31x |
| DeepSeek-V4.1-Flash | 16 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x261 | 212,715 | 4,144.8 | 70,460.8 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-hybrid | 213,108 | 1.00x | hybrid | 1,026.87 | 358.7 | 11,836.3 | link_latency | 11.56x | 2.26x | 34.37x | 11.56x |
| DeepSeek-V4.1-Flash | 16 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1,888.8 | 30,221.0 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 958.99 | 364.5 | 5,832.5 | link_latency | 5.18x | 2.24x | 15.66x | 5.18x |
| DeepSeek-V4.1-Flash | 32 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x261 | 212,715 | 4,089.0 | 134,938.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-hybrid | 213,108 | 1.00x | hybrid | 1,026.87 | 358.7 | 11,836.3 | link_latency | 11.40x | 4.34x | 33.91x | 11.40x |
| DeepSeek-V4.1-Flash | 32 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1,275.7 | 40,823.3 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 1,004.55 | 319.1 | 10,210.6 | weight_read | 4.00x | 3.02x | 10.58x | 4.00x |
| DeepSeek-V4.1-Flash | 64 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x261 | 212,715 | 3,982.2 | 262,822.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-hybrid | 213,108 | 1.00x | hybrid | 1,097.22 | 317.5 | 20,318.8 | weight_read | 12.54x | 8.45x | 33.02x | 12.54x |
| DeepSeek-V4.1-Flash | 64 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 735.9 | 47,094.5 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 1,095.69 | 256.6 | 16,421.3 | weight_read | 2.87x | 2.87x | 6.10x | 2.87x |
| DeepSeek-V4.1-Flash | 256 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,082.4 | 789,099.9 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,234.22 | 278.5 | 71,301.5 | weight_read | 11.07x | 9.74x | 25.56x | 11.51x |
| DeepSeek-V4.1-Flash | 256 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | 92,450 | 199.6 | 51,093.3 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 1,642.50 | 124.8 | 31,942.2 | weight_read | 1.60x | 1.60x | 2.31x | 1.60x |
| DeepSeek-V4.1-Flash | 1024 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,667.0 | 1,707,058.7 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,289.29 | 144.9 | 148,356.9 | weight_read | 11.51x | 11.51x | 16.08x | 12.28x |
| DeepSeek-V4.1-Flash | 1024 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | 92,450 | 50.6 | 51,796.5 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 3,616.63 | 51.7 | 52,955.9 | weight_read | 0.98x | 0.98x | 1.46x | 0.98x |
| DeepSeek-V4.1-Flash | 4096 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 602.0 | 2,465,956.8 | kv_read | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 2,026.60 | 57.8 | 236,928.9 | weight_read | 10.41x | 10.41x | 12.88x | 11.00x |
| DeepSeek-V4.1-Flash | 4096 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | 92,450 | 12.7 | 51,855.2 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 12,839.45 | 28.1 | 114,920.2 | weight_read | 0.45x | 0.45x | 1.05x | 0.45x |

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
| DeepSeek-V4.1-Flash | 18 | 14,868 | 121.5 | 274.1 | 339.6 | hybrid | 910.78 | 30.9% | weight_read |
| DeepSeek-V4.1-Flash | 53 | 43,778 | 120.6 | 287.3 | 368.1 | hybrid | 926.32 | 34.1% | weight_read |
| DeepSeek-V4.1-Flash | 56 | 46,256 | 120.6 | 287.6 | 375.0 | hybrid | 926.32 | 34.7% | link_latency |
| DeepSeek-V4.1-Flash | 57 | 47,082 | 120.6 | 287.2 | 359.9 | hybrid | 930.12 | 33.5% | weight_read |
| DeepSeek-V4.1-Flash | 59 | 48,734 | 120.6 | 287.4 | 364.2 | hybrid | 930.12 | 33.9% | weight_read |
| DeepSeek-V4.1-Flash | 108 | 89,208 | 120.6 | 258.0 | 366.8 | hybrid | 953.29 | 35.0% | link_latency |
| DeepSeek-V4.1-Flash | 111 | 91,686 | 120.6 | 257.9 | 370.1 | hybrid | 953.29 | 35.3% | link_latency |
| DeepSeek-V4.1-Flash | 112 | 92,512 | 120.6 | 257.8 | 371.2 | hybrid | 953.29 | 35.4% | link_latency |
| DeepSeek-V4.1-Flash | 113 | 93,338 | 120.6 | 257.6 | 363.3 | hybrid | 957.26 | 34.8% | link_latency |
| DeepSeek-V4.1-Flash | 115 | 94,990 | 120.6 | 257.5 | 365.5 | hybrid | 957.26 | 35.0% | link_latency |
| DeepSeek-V4.1-Flash | 117 | 96,642 | 120.6 | 257.4 | 367.6 | hybrid | 957.26 | 35.2% | link_latency |
| DeepSeek-V4.1-Flash | 124 | 102,424 | 120.6 | 256.9 | 366.3 | hybrid | 961.06 | 35.2% | link_latency |
| DeepSeek-V4.1-Flash | 130 | 107,380 | 120.6 | 256.4 | 364.1 | hybrid | 965.03 | 35.1% | link_latency |
| DeepSeek-V4.1-Flash | 133 | 109,858 | 120.6 | 256.2 | 366.9 | hybrid | 965.03 | 35.4% | link_latency |
| DeepSeek-V4.1-Flash | 141 | 116,466 | 120.6 | 255.6 | 366.5 | hybrid | 968.83 | 35.5% | link_latency |
| DeepSeek-V4.1-Flash | 156 | 128,856 | 120.6 | 254.4 | 365.0 | hybrid | 976.60 | 35.6% | link_latency |
| DeepSeek-V4.1-Flash | 167 | 137,942 | 120.6 | 253.6 | 366.8 | hybrid | 980.40 | 36.0% | link_latency |
| DeepSeek-V4.1-Flash | 168 | 138,768 | 120.6 | 253.5 | 367.5 | hybrid | 980.40 | 36.0% | link_latency |
| DeepSeek-V4.1-Flash | 169 | 139,594 | 120.6 | 253.4 | 362.1 | hybrid | 984.36 | 35.6% | link_latency |
| DeepSeek-V4.1-Flash | 202 | 166,852 | 120.6 | 250.7 | 361.4 | hybrid | 999.90 | 36.1% | link_latency |
| DeepSeek-V4.1-Flash | 203 | 167,678 | 120.6 | 250.7 | 362.0 | hybrid | 999.90 | 36.2% | link_latency |
| DeepSeek-V4.1-Flash | 207 | 170,982 | 120.6 | 250.4 | 364.3 | hybrid | 999.90 | 36.4% | link_latency |
| DeepSeek-V4.1-Flash | 224 | 185,024 | 120.6 | 249.0 | 363.9 | hybrid | 1,007.54 | 36.7% | link_latency |
| DeepSeek-V4.1-Flash | 225 | 185,850 | 120.6 | 248.9 | 359.8 | hybrid | 1,011.34 | 36.4% | link_latency |
| DeepSeek-V4.1-Flash | 255 | 210,630 | 120.6 | 246.5 | 361.4 | hybrid | 1,023.07 | 37.0% | link_latency |
| DeepSeek-V4.1-Flash | 258 | 213,108 | 120.6 | 246.2 | 358.7 | hybrid | 1,026.87 | 36.8% | link_latency |
| DeepSeek-V4.1-Flash | 311 | 256,886 | 120.6 | 242.0 | 357.9 | hybrid | 1,050.18 | 37.6% | link_latency |
| DeepSeek-V4.1-Flash | 335 | 276,710 | 120.6 | 204.4 | 357.5 | hybrid | 1,054.14 | 37.7% | link_latency |
| DeepSeek-V4.1-Flash | 336 | 277,536 | 120.6 | 204.4 | 357.8 | hybrid | 1,054.14 | 37.7% | link_latency |
| DeepSeek-V4.1-Flash | 337 | 278,362 | 120.6 | 204.3 | 355.5 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash | 448 | 370,048 | 120.6 | 198.1 | 357.8 | hybrid | 1,054.14 | 37.7% | link_latency |
| DeepSeek-V4.1-Flash | 672 | 555,072 | 120.6 | 186.6 | 357.8 | hybrid | 1,054.14 | 37.7% | link_latency |

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
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x135 | DeepSeek-V4.1-Flash | 135 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x115 | DeepSeek-V4.1-Flash | 115 | tensor | rom_package_ucie | rom_board_serdes | 160 | 91.38 us | 1,094.3 tok/s | 10,943.4 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 29 on rom_board_serdes (traversals 11.0) = 89.32 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x126 | DeepSeek-V4.1-Flash | 126 | hybrid | rom_package_ucie | rom_board_serdes | 111 | 5.34 us | 18,736.6 tok/s | 187,365.7 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 31 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.28 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x135 | DeepSeek-V4.1-Flash | 135 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x3 | DeepSeek-V4.1-Flash | 3 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-tensor-x109 | DeepSeek-V4.1-Flash | 109 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hybrid-x126 | DeepSeek-V4.1-Flash | 126 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4.1-Flash | 3 | hybrid | on_wafer | rom_wafer_serdes | 82 | 154.20 us | 648.5 tok/s | 6,484.9 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x261 | DeepSeek-V4.1-Flash | 261 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x119 | DeepSeek-V4.1-Flash | 119 | tensor | rom_package_ucie | rom_board_serdes | 160 | 91.38 us | 1,094.3 tok/s | 10,943.2 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 30 on rom_board_serdes (traversals 11.0) = 89.32 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x169 | DeepSeek-V4.1-Flash | 169 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-pipeline-x258 | DeepSeek-V4.1-Flash | 258 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4 | DeepSeek-V4.1-Flash | 4 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-tensor-x117 | DeepSeek-V4.1-Flash | 117 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hybrid-x143 | DeepSeek-V4.1-Flash | 143 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | DeepSeek-V4.1-Flash | 4 | hybrid | on_wafer | rom_wafer_serdes | 83 | 154.31 us | 648.1 tok/s | 6,480.7 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x18-pipeline | DeepSeek-V4.1-Flash | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 42.89 us | 2,331.5 tok/s | 23,314.8 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 38.01 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x18-tensor | DeepSeek-V4.1-Flash | 18 | tensor | nvlink3 | infiniband_hdr | 160 | 797.50 us | 125.4 tok/s | 1,253.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 390.34 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x18-hybrid | DeepSeek-V4.1-Flash | 18 | hybrid | nvlink3 | infiniband_hdr | 82 | 412.05 us | 242.7 tok/s | 2,426.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x18-expert | DeepSeek-V4.1-Flash | 18 | expert | nvlink3 | infiniband_hdr | 160 | 576.91 us | 173.3 tok/s | 1,733.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 403.58 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x53-pipeline | DeepSeek-V4.1-Flash | 53 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x53-tensor | DeepSeek-V4.1-Flash | 53 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x53-hybrid | DeepSeek-V4.1-Flash | 53 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x53-expert | DeepSeek-V4.1-Flash | 53 | expert | nvlink3 | infiniband_hdr | 160 | 567.30 us | 176.3 tok/s | 1,762.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 166.11 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-expert | DeepSeek-V4.1-Flash | 56 | expert | nvlink3 | infiniband_hdr | 160 | 566.93 us | 176.4 tok/s | 1,763.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x57-pipeline | DeepSeek-V4.1-Flash | 57 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x57-tensor | DeepSeek-V4.1-Flash | 57 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x57-hybrid | DeepSeek-V4.1-Flash | 57 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x57-expert | DeepSeek-V4.1-Flash | 57 | expert | nvlink3 | infiniband_hdr | 160 | 566.87 us | 176.4 tok/s | 1,764.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.85 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-pipeline | DeepSeek-V4.1-Flash | 59 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-tensor | DeepSeek-V4.1-Flash | 59 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-hybrid | DeepSeek-V4.1-Flash | 59 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-expert | DeepSeek-V4.1-Flash | 59 | expert | nvlink3 | infiniband_hdr | 160 | 566.76 us | 176.4 tok/s | 1,764.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.73 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x108-pipeline | DeepSeek-V4.1-Flash | 108 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x108-tensor | DeepSeek-V4.1-Flash | 108 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x108-hybrid | DeepSeek-V4.1-Flash | 108 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x108-expert | DeepSeek-V4.1-Flash | 108 | expert | nvlink3 | infiniband_hdr | 160 | 564.77 us | 177.1 tok/s | 1,770.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.55 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.22 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4.1-Flash | 111 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4.1-Flash | 111 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4.1-Flash | 111 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-expert | DeepSeek-V4.1-Flash | 111 | expert | nvlink3 | infiniband_hdr | 160 | 564.72 us | 177.1 tok/s | 1,770.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.55 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.17 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4.1-Flash | 112 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4.1-Flash | 112 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4.1-Flash | 112 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-expert | DeepSeek-V4.1-Flash | 112 | expert | nvlink3 | infiniband_hdr | 160 | 564.67 us | 177.1 tok/s | 1,771.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.16 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x113-pipeline | DeepSeek-V4.1-Flash | 113 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x113-tensor | DeepSeek-V4.1-Flash | 113 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x113-hybrid | DeepSeek-V4.1-Flash | 113 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x113-expert | DeepSeek-V4.1-Flash | 113 | expert | nvlink3 | infiniband_hdr | 160 | 564.65 us | 177.1 tok/s | 1,771.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x115-pipeline | DeepSeek-V4.1-Flash | 115 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x115-tensor | DeepSeek-V4.1-Flash | 115 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x115-hybrid | DeepSeek-V4.1-Flash | 115 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x115-expert | DeepSeek-V4.1-Flash | 115 | expert | nvlink3 | infiniband_hdr | 160 | 564.62 us | 177.1 tok/s | 1,771.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.11 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x117-pipeline | DeepSeek-V4.1-Flash | 117 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x117-tensor | DeepSeek-V4.1-Flash | 117 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x117-hybrid | DeepSeek-V4.1-Flash | 117 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x117-expert | DeepSeek-V4.1-Flash | 117 | expert | nvlink3 | infiniband_hdr | 160 | 564.59 us | 177.1 tok/s | 1,771.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x124-pipeline | DeepSeek-V4.1-Flash | 124 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x124-tensor | DeepSeek-V4.1-Flash | 124 | tensor | nvlink3 | infiniband_hdr | 160 | 824.13 us | 121.3 tok/s | 1,213.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 416.96 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x124-hybrid | DeepSeek-V4.1-Flash | 124 | hybrid | nvlink3 | infiniband_hdr | 95 | 443.76 us | 225.3 tok/s | 2,253.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.59 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x124-expert | DeepSeek-V4.1-Flash | 124 | expert | nvlink3 | infiniband_hdr | 160 | 564.46 us | 177.2 tok/s | 1,771.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.48 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-pipeline | DeepSeek-V4.1-Flash | 130 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-tensor | DeepSeek-V4.1-Flash | 130 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-hybrid | DeepSeek-V4.1-Flash | 130 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-expert | DeepSeek-V4.1-Flash | 130 | expert | nvlink3 | infiniband_hdr | 160 | 564.36 us | 177.2 tok/s | 1,771.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.91 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x133-pipeline | DeepSeek-V4.1-Flash | 133 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x133-tensor | DeepSeek-V4.1-Flash | 133 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x133-hybrid | DeepSeek-V4.1-Flash | 133 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x133-expert | DeepSeek-V4.1-Flash | 133 | expert | nvlink3 | infiniband_hdr | 160 | 564.33 us | 177.2 tok/s | 1,772.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.88 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-pipeline | DeepSeek-V4.1-Flash | 141 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-tensor | DeepSeek-V4.1-Flash | 141 | tensor | nvlink3 | infiniband_hdr | 160 | 824.81 us | 121.2 tok/s | 1,212.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 417.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-hybrid | DeepSeek-V4.1-Flash | 141 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-expert | DeepSeek-V4.1-Flash | 141 | expert | nvlink3 | infiniband_hdr | 160 | 564.22 us | 177.2 tok/s | 1,772.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-pipeline | DeepSeek-V4.1-Flash | 156 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-tensor | DeepSeek-V4.1-Flash | 156 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-hybrid | DeepSeek-V4.1-Flash | 156 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-expert | DeepSeek-V4.1-Flash | 156 | expert | nvlink3 | infiniband_hdr | 160 | 564.04 us | 177.3 tok/s | 1,772.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.66 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x167-pipeline | DeepSeek-V4.1-Flash | 167 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x167-tensor | DeepSeek-V4.1-Flash | 167 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x167-hybrid | DeepSeek-V4.1-Flash | 167 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x167-expert | DeepSeek-V4.1-Flash | 167 | expert | nvlink3 | infiniband_hdr | 160 | 563.94 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.36 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.58 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4.1-Flash | 168 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4.1-Flash | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4.1-Flash | 168 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-expert | DeepSeek-V4.1-Flash | 168 | expert | nvlink3 | infiniband_hdr | 160 | 563.91 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-pipeline | DeepSeek-V4.1-Flash | 169 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-tensor | DeepSeek-V4.1-Flash | 169 | tensor | nvlink3 | infiniband_hdr | 160 | 825.80 us | 121.1 tok/s | 1,210.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 418.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-hybrid | DeepSeek-V4.1-Flash | 169 | hybrid | nvlink3 | infiniband_hdr | 101 | 458.40 us | 218.2 tok/s | 2,181.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 51.23 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-expert | DeepSeek-V4.1-Flash | 169 | expert | nvlink3 | infiniband_hdr | 160 | 563.90 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.56 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x202-pipeline | DeepSeek-V4.1-Flash | 202 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x202-tensor | DeepSeek-V4.1-Flash | 202 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x202-hybrid | DeepSeek-V4.1-Flash | 202 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x202-expert | DeepSeek-V4.1-Flash | 202 | expert | nvlink3 | infiniband_hdr | 160 | 563.66 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.37 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x203-pipeline | DeepSeek-V4.1-Flash | 203 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x203-tensor | DeepSeek-V4.1-Flash | 203 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x203-hybrid | DeepSeek-V4.1-Flash | 203 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x203-expert | DeepSeek-V4.1-Flash | 203 | expert | nvlink3 | infiniband_hdr | 160 | 563.66 us | 177.4 tok/s | 1,774.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.37 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x207-pipeline | DeepSeek-V4.1-Flash | 207 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x207-tensor | DeepSeek-V4.1-Flash | 207 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x207-hybrid | DeepSeek-V4.1-Flash | 207 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x207-expert | DeepSeek-V4.1-Flash | 207 | expert | nvlink3 | infiniband_hdr | 160 | 563.64 us | 177.4 tok/s | 1,774.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.29 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.35 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-expert | DeepSeek-V4.1-Flash | 224 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.28 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-pipeline | DeepSeek-V4.1-Flash | 225 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-tensor | DeepSeek-V4.1-Flash | 225 | tensor | nvlink3 | infiniband_hdr | 160 | 826.88 us | 120.9 tok/s | 1,209.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 419.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-hybrid | DeepSeek-V4.1-Flash | 225 | hybrid | nvlink3 | infiniband_hdr | 108 | 475.48 us | 210.3 tok/s | 2,103.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 68.31 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-expert | DeepSeek-V4.1-Flash | 225 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.27 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x255-pipeline | DeepSeek-V4.1-Flash | 255 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x255-tensor | DeepSeek-V4.1-Flash | 255 | tensor | nvlink3 | infiniband_hdr | 160 | 827.20 us | 120.9 tok/s | 1,208.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 32 on infiniband_hdr (traversals 2.0) = 420.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x255-hybrid | DeepSeek-V4.1-Flash | 255 | hybrid | nvlink3 | infiniband_hdr | 111 | 482.80 us | 207.1 tok/s | 2,071.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 31 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.63 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x255-expert | DeepSeek-V4.1-Flash | 255 | expert | nvlink3 | infiniband_hdr | 160 | 563.40 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.23 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.17 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-pipeline | DeepSeek-V4.1-Flash | 258 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-tensor | DeepSeek-V4.1-Flash | 258 | tensor | nvlink3 | infiniband_hdr | 160 | 827.29 us | 120.9 tok/s | 1,208.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 33 on infiniband_hdr (traversals 2.0) = 420.13 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-hybrid | DeepSeek-V4.1-Flash | 258 | hybrid | nvlink3 | infiniband_hdr | 112 | 485.24 us | 206.1 tok/s | 2,060.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 32 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.07 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x258-expert | DeepSeek-V4.1-Flash | 258 | expert | nvlink3 | infiniband_hdr | 160 | 563.39 us | 177.5 tok/s | 1,775.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.22 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.16 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x311-pipeline | DeepSeek-V4.1-Flash | 311 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x311-tensor | DeepSeek-V4.1-Flash | 311 | tensor | nvlink3 | infiniband_hdr | 160 | 827.75 us | 120.8 tok/s | 1,208.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 39 on infiniband_hdr (traversals 2.0) = 420.58 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x311-hybrid | DeepSeek-V4.1-Flash | 311 | hybrid | nvlink3 | infiniband_hdr | 118 | 499.87 us | 200.1 tok/s | 2,000.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 38 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 92.70 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x311-expert | DeepSeek-V4.1-Flash | 311 | expert | nvlink3 | infiniband_hdr | 160 | 563.22 us | 177.6 tok/s | 1,775.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-pipeline | DeepSeek-V4.1-Flash | 335 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-tensor | DeepSeek-V4.1-Flash | 335 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid | DeepSeek-V4.1-Flash | 335 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-expert | DeepSeek-V4.1-Flash | 335 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-pipeline | DeepSeek-V4.1-Flash | 336 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-tensor | DeepSeek-V4.1-Flash | 336 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-hybrid | DeepSeek-V4.1-Flash | 336 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-expert | DeepSeek-V4.1-Flash | 336 | expert | nvlink3 | infiniband_hdr | 160 | 563.16 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-pipeline | DeepSeek-V4.1-Flash | 337 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-tensor | DeepSeek-V4.1-Flash | 337 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.79 us | 86.7 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 43 on infiniband_hdr (traversals 4.0) = 745.62 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-hybrid | DeepSeek-V4.1-Flash | 337 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-expert | DeepSeek-V4.1-Flash | 337 | expert | nvlink3 | infiniband_hdr | 160 | 563.15 us | 177.6 tok/s | 1,775.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.17 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.98 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4.1-Flash | 448 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4.1-Flash | 448 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.32 us | 86.7 tok/s | 867.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 746.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4.1-Flash | 448 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-expert | DeepSeek-V4.1-Flash | 448 | expert | nvlink3 | infiniband_hdr | 160 | 562.97 us | 177.6 tok/s | 1,776.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.13 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.84 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4.1-Flash | 672 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4.1-Flash | 672 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.90 us | 86.7 tok/s | 866.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 746.73 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4.1-Flash | 672 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-expert | DeepSeek-V4.1-Flash | 672 | expert | nvlink3 | infiniband_hdr | 160 | 562.78 us | 177.7 tok/s | 1,776.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.09 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 162.69 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash | 1 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x143 | 116,545 | 3,972.5 | 0.034 | 3,972.5 (116,545) | 3,503.7 (138,675) | 0.88x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 2 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x143 | 116,545 | 3,972.5 | 0.034 | 3,972.5 (116,545) | 3,503.7 (138,675) | 0.88x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 4 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x143 | 116,545 | 3,972.5 | 0.034 | 3,972.5 (116,545) | 3,503.7 (138,675) | 0.88x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 8 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x143 | 116,545 | 3,972.5 | 0.034 | 3,972.5 (116,545) | 3,503.7 (138,675) | 0.88x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 16 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x169 | 137,735 | 3,937.7 | 0.029 | 3,937.7 (137,735) | 3,503.7 (138,675) | 0.89x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 32 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x205-romfill | 167,075 | 3,969.5 | 0.024 | 3,969.5 (167,075) | 3,581.9 (184,900) | 0.90x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 64 | array | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 3,867.8 | 0.021 | 3,867.8 (185,005) | 3,454.5 (184,900) | 0.89x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 256 | array | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 3,006.5 | 0.011 | 3,006.5 (277,100) | 3,082.4 (554,700) | 1.03x | weight_read |
| DeepSeek-V4.1-Flash | 1024 | wafer | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,667.0 | 0.003 | 1,187.0 (277,100) | 1,667.0 (554,700) | 1.40x | compute |
| DeepSeek-V4.1-Flash | 4096 | wafer | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 602.0 | 0.001 | 328.9 (277,100) | 602.0 (554,700) | 1.83x | kv_read |

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
| DeepSeek-V4.1-Flash | 384 | 752.0 MB | 164.9 mm2 | 29.69 mm2 (18.0%) | 63,336 mm2 | 11,400 mm2 | 111,918 mm2 = 137.3 reticles |

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
| DeepSeek-V4.1-Flash | 1 | sram | 890,974.2 | 26,113.2 | 26,113.2 | 34.12x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | sram | 890,974.2 | 26,113.2 | 26,113.2 | 34.12x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | sram | 890,974.2 | 26,113.2 | 26,113.2 | 34.12x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | sram | 890,974.2 | 26,113.2 | 26,113.2 | 34.12x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | sram | 890,974.2 | 26,113.2 | 37,055.7 | 34.12x | 1.42x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | sram | 890,974.2 | 26,113.2 | 54,796.0 | 34.12x | 2.10x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | sram | 890,974.2 | 26,113.2 | 79,051.5 | 34.12x | 3.03x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 256 | sram | 890,974.2 | 26,113.2 | 180,592.0 | 34.12x | 6.92x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1024 | sram | 1,617,328.2 | 26,113.2 | 309,145.9 | 61.94x | 11.84x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | sram | 2,465,956.8 | 26,113.2 | 429,532.6 | 94.43x | 16.45x | kv_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash | 1 | rom | 1,545,091.5 | 81,182.0 | 81,182.0 | 19.03x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | rom | 1,545,091.5 | 81,182.0 | 81,182.0 | 19.03x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | rom | 1,545,091.5 | 81,182.0 | 81,182.0 | 19.03x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | rom | 1,545,091.5 | 81,182.0 | 81,182.0 | 19.03x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | rom | 1,545,091.5 | 81,182.0 | 81,182.0 | 19.03x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | rom | 1,545,091.5 | 81,182.0 | 81,182.0 | 19.03x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | rom | 1,545,091.5 | 81,182.0 | 123,793.8 | 19.03x | 1.52x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 256 | rom | 1,545,091.5 | 81,628.3 | 303,682.3 | 18.93x | 3.72x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1024 | rom | 1,707,058.7 | 81,628.3 | 555,094.6 | 20.91x | 6.80x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | rom | 2,007,684.9 | 81,628.3 | 654,875.1 | 24.60x | 8.02x | compute | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash | 1 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 890,974.2 | 1.606 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,545,091.5 | 2.785 | compute | 1.73x |
| DeepSeek-V4.1-Flash | 1 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 1 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 2 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 890,974.2 | 1.606 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 2 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,545,091.5 | 2.785 | compute | 1.73x |
| DeepSeek-V4.1-Flash | 2 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 2 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 4 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 890,974.2 | 1.606 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,545,091.5 | 2.785 | compute | 1.73x |
| DeepSeek-V4.1-Flash | 4 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 4 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 8 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 890,974.2 | 1.606 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 8 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,545,091.5 | 2.785 | compute | 1.73x |
| DeepSeek-V4.1-Flash | 8 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 8 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 16 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 890,974.2 | 1.606 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 16 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,545,091.5 | 2.785 | compute | 1.73x |
| DeepSeek-V4.1-Flash | 16 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 16 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 16 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion | 48,900 | 1.00 | 1.43 | 37,055.7 | 0.758 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 16 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 32 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 890,974.2 | 1.606 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 32 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,545,091.5 | 2.785 | compute | 1.73x |
| DeepSeek-V4.1-Flash | 32 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 32 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 32 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion | 48,900 | 1.00 | 1.99 | 54,796.0 | 1.121 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash | 32 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 64 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 890,974.2 | 1.606 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 64 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,545,091.5 | 2.785 | compute | 1.73x |
| DeepSeek-V4.1-Flash | 64 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x60-perstream | 48,900 | 1.00 | 1.07 | 26,113.2 | 0.534 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 64 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 1.00 | 81,182.0 | 0.585 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 64 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.54 | 79,051.5 | 0.855 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 64 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 3.13 | 1.74 | 123,793.8 | 0.893 | weight_read | 0.14x |
| DeepSeek-V4.1-Flash | 256 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 890,974.2 | 1.606 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 256 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,545,091.5 | 2.785 | compute | 1.73x |
| DeepSeek-V4.1-Flash | 256 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x60-perstream | 48,900 | 1.00 | 4.27 | 26,113.2 | 0.534 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 256 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 1.50 | 81,628.3 | 0.589 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash | 256 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.49 | 180,592.0 | 1.953 | weight_read | 0.20x |
| DeepSeek-V4.1-Flash | 256 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 3.13 | 2.24 | 303,682.3 | 2.190 | weight_read | 0.34x |
| DeepSeek-V4.1-Flash | 1024 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,617,328.2 | 2.916 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1024 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,707,058.7 | 3.077 | compute | 1.06x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x60-perstream | 48,900 | 1.00 | 17.07 | 26,113.2 | 0.534 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 5.99 | 81,628.3 | 0.589 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash | 1024 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 5.09 | 309,145.9 | 3.344 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash | 1024 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 3.13 | 3.08 | 555,094.6 | 4.003 | weight_read | 0.34x |
| DeepSeek-V4.1-Flash | 4096 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 2,465,956.8 | 4.446 | kv_read | 1.00x |
| DeepSeek-V4.1-Flash | 4096 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 2,007,684.9 | 3.619 | compute | 0.81x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x60-perstream | 48,900 | 1.00 | 68.27 | 26,113.2 | 0.534 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.13 | 23.95 | 81,628.3 | 0.589 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4096 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 7.62 | 429,532.6 | 4.646 | kv_read | 0.17x |
| DeepSeek-V4.1-Flash | 4096 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 3.13 | 4.25 | 654,875.1 | 4.722 | kv_read | 0.27x |

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
| DeepSeek-V4.1-Flash | 1 | 54 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 2 | 54 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 32 | 60 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 64 | 60 | 1.07 | 1.001 | 1.004 | 1.00x |
| DeepSeek-V4.1-Flash | 256 | 60 | 4.27 | 1.026 | 1.478 | 1.44x |
| DeepSeek-V4.1-Flash | 1024 | 60 | 17.07 | 1.131 | 2.623 | 2.32x |
| DeepSeek-V4.1-Flash | 4096 | 60 | 68.27 | 1.619 | 5.094 | 3.15x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4.1-Flash | 2 | 18 | 8.89 | 5.04 | 1.76x |
| DeepSeek-V4.1-Flash | 4 | 18 | 13.29 | 6.50 | 2.04x |
| DeepSeek-V4.1-Flash | 8 | 18 | 16.66 | 8.05 | 2.07x |
| DeepSeek-V4.1-Flash | 16 | 18 | 17.86 | 9.57 | 1.87x |
| DeepSeek-V4.1-Flash | 32 | 18 | 18.00 | 10.92 | 1.65x |
| DeepSeek-V4.1-Flash | 64 | 18 | 18.00 | 11.95 | 1.51x |
| DeepSeek-V4.1-Flash | 256 | 18 | 18.00 | 12.83 | 1.40x |
| DeepSeek-V4.1-Flash | 1024 | 18 | 18.00 | 12.86 | 1.40x |
| DeepSeek-V4.1-Flash | 4096 | 18 | 18.00 | 12.86 | 1.40x |
| DeepSeek-V4.1-Flash | 1 | 53 | 5.72 | 4.83 | 1.18x |
| DeepSeek-V4.1-Flash | 2 | 53 | 10.75 | 6.87 | 1.56x |
| DeepSeek-V4.1-Flash | 4 | 53 | 19.09 | 9.66 | 1.98x |
| DeepSeek-V4.1-Flash | 8 | 53 | 30.70 | 13.08 | 2.35x |
| DeepSeek-V4.1-Flash | 16 | 53 | 42.61 | 16.98 | 2.51x |
| DeepSeek-V4.1-Flash | 32 | 53 | 50.07 | 20.91 | 2.39x |
| DeepSeek-V4.1-Flash | 64 | 53 | 52.49 | 24.29 | 2.16x |
| DeepSeek-V4.1-Flash | 256 | 53 | 52.96 | 27.44 | 1.93x |
| DeepSeek-V4.1-Flash | 1024 | 53 | 52.96 | 27.57 | 1.92x |
| DeepSeek-V4.1-Flash | 4096 | 53 | 52.96 | 27.57 | 1.92x |
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
| DeepSeek-V4.1-Flash | 1 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4.1-Flash | 2 | 59 | 10.87 | 7.07 | 1.54x |
| DeepSeek-V4.1-Flash | 4 | 59 | 19.48 | 9.96 | 1.96x |
| DeepSeek-V4.1-Flash | 8 | 59 | 31.87 | 13.62 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 59 | 45.33 | 17.83 | 2.54x |
| DeepSeek-V4.1-Flash | 32 | 59 | 54.61 | 22.12 | 2.47x |
| DeepSeek-V4.1-Flash | 64 | 59 | 58.09 | 25.86 | 2.25x |
| DeepSeek-V4.1-Flash | 256 | 59 | 58.91 | 29.37 | 2.01x |
| DeepSeek-V4.1-Flash | 1024 | 59 | 58.92 | 29.52 | 2.00x |
| DeepSeek-V4.1-Flash | 4096 | 59 | 58.92 | 29.52 | 2.00x |
| DeepSeek-V4.1-Flash | 1 | 108 | 5.86 | 5.33 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 108 | 11.32 | 8.21 | 1.38x |
| DeepSeek-V4.1-Flash | 4 | 108 | 21.16 | 11.60 | 1.82x |
| DeepSeek-V4.1-Flash | 8 | 108 | 37.24 | 16.82 | 2.21x |
| DeepSeek-V4.1-Flash | 16 | 108 | 59.26 | 22.90 | 2.59x |
| DeepSeek-V4.1-Flash | 32 | 108 | 81.74 | 29.58 | 2.76x |
| DeepSeek-V4.1-Flash | 64 | 108 | 96.82 | 35.77 | 2.71x |
| DeepSeek-V4.1-Flash | 256 | 108 | 104.77 | 41.92 | 2.50x |
| DeepSeek-V4.1-Flash | 1024 | 108 | 104.97 | 42.18 | 2.49x |
| DeepSeek-V4.1-Flash | 4096 | 108 | 104.97 | 42.18 | 2.49x |
| DeepSeek-V4.1-Flash | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 111 | 11.34 | 8.26 | 1.37x |
| DeepSeek-V4.1-Flash | 4 | 111 | 21.22 | 11.67 | 1.82x |
| DeepSeek-V4.1-Flash | 8 | 111 | 37.44 | 16.97 | 2.21x |
| DeepSeek-V4.1-Flash | 16 | 111 | 59.81 | 23.14 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 111 | 82.95 | 29.94 | 2.77x |
| DeepSeek-V4.1-Flash | 64 | 111 | 98.78 | 36.26 | 2.72x |
| DeepSeek-V4.1-Flash | 256 | 111 | 107.35 | 42.56 | 2.52x |
| DeepSeek-V4.1-Flash | 1024 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4.1-Flash | 4096 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4.1-Flash | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4.1-Flash | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4.1-Flash | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4.1-Flash | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4.1-Flash | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4.1-Flash | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4.1-Flash | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4.1-Flash | 4096 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4.1-Flash | 1 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 113 | 11.35 | 8.30 | 1.37x |
| DeepSeek-V4.1-Flash | 4 | 113 | 21.26 | 11.72 | 1.81x |
| DeepSeek-V4.1-Flash | 8 | 113 | 37.56 | 17.07 | 2.20x |
| DeepSeek-V4.1-Flash | 16 | 113 | 60.17 | 23.29 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 113 | 83.74 | 30.18 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 113 | 100.07 | 36.59 | 2.74x |
| DeepSeek-V4.1-Flash | 256 | 113 | 109.05 | 42.97 | 2.54x |
| DeepSeek-V4.1-Flash | 1024 | 113 | 109.28 | 43.24 | 2.53x |
| DeepSeek-V4.1-Flash | 4096 | 113 | 109.28 | 43.24 | 2.53x |
| DeepSeek-V4.1-Flash | 1 | 115 | 5.87 | 5.36 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 115 | 11.36 | 8.33 | 1.36x |
| DeepSeek-V4.1-Flash | 4 | 115 | 21.29 | 11.77 | 1.81x |
| DeepSeek-V4.1-Flash | 8 | 115 | 37.68 | 17.16 | 2.20x |
| DeepSeek-V4.1-Flash | 16 | 115 | 60.51 | 23.44 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 115 | 84.51 | 30.41 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 115 | 101.33 | 36.90 | 2.75x |
| DeepSeek-V4.1-Flash | 256 | 115 | 110.73 | 43.38 | 2.55x |
| DeepSeek-V4.1-Flash | 1024 | 115 | 110.98 | 43.66 | 2.54x |
| DeepSeek-V4.1-Flash | 4096 | 115 | 110.98 | 43.66 | 2.54x |
| DeepSeek-V4.1-Flash | 1 | 117 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 117 | 11.37 | 8.36 | 1.36x |
| DeepSeek-V4.1-Flash | 4 | 117 | 21.33 | 11.81 | 1.81x |
| DeepSeek-V4.1-Flash | 8 | 117 | 37.80 | 17.26 | 2.19x |
| DeepSeek-V4.1-Flash | 16 | 117 | 60.85 | 23.59 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 117 | 85.27 | 30.64 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 117 | 102.57 | 37.22 | 2.76x |
| DeepSeek-V4.1-Flash | 256 | 117 | 112.41 | 43.79 | 2.57x |
| DeepSeek-V4.1-Flash | 1024 | 117 | 112.67 | 44.07 | 2.56x |
| DeepSeek-V4.1-Flash | 4096 | 117 | 112.67 | 44.07 | 2.56x |
| DeepSeek-V4.1-Flash | 1 | 124 | 5.88 | 5.40 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 124 | 11.40 | 8.47 | 1.35x |
| DeepSeek-V4.1-Flash | 4 | 124 | 21.44 | 11.97 | 1.79x |
| DeepSeek-V4.1-Flash | 8 | 124 | 38.18 | 17.58 | 2.17x |
| DeepSeek-V4.1-Flash | 16 | 124 | 61.96 | 24.09 | 2.57x |
| DeepSeek-V4.1-Flash | 32 | 124 | 87.79 | 31.41 | 2.79x |
| DeepSeek-V4.1-Flash | 64 | 124 | 106.78 | 38.28 | 2.79x |
| DeepSeek-V4.1-Flash | 256 | 124 | 118.15 | 45.18 | 2.62x |
| DeepSeek-V4.1-Flash | 1024 | 124 | 118.47 | 45.47 | 2.61x |
| DeepSeek-V4.1-Flash | 4096 | 124 | 118.47 | 45.47 | 2.61x |
| DeepSeek-V4.1-Flash | 1 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 130 | 11.42 | 8.56 | 1.33x |
| DeepSeek-V4.1-Flash | 4 | 130 | 21.53 | 12.10 | 1.78x |
| DeepSeek-V4.1-Flash | 8 | 130 | 38.48 | 17.83 | 2.16x |
| DeepSeek-V4.1-Flash | 16 | 130 | 62.84 | 24.50 | 2.57x |
| DeepSeek-V4.1-Flash | 32 | 130 | 89.81 | 32.05 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 130 | 110.22 | 39.16 | 2.81x |
| DeepSeek-V4.1-Flash | 256 | 130 | 122.94 | 46.32 | 2.65x |
| DeepSeek-V4.1-Flash | 1024 | 130 | 123.30 | 46.63 | 2.64x |
| DeepSeek-V4.1-Flash | 4096 | 130 | 123.30 | 46.63 | 2.64x |
| DeepSeek-V4.1-Flash | 1 | 133 | 5.89 | 5.44 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 133 | 11.43 | 8.60 | 1.33x |
| DeepSeek-V4.1-Flash | 4 | 133 | 21.57 | 12.17 | 1.77x |
| DeepSeek-V4.1-Flash | 8 | 133 | 38.62 | 17.96 | 2.15x |
| DeepSeek-V4.1-Flash | 16 | 133 | 63.26 | 24.69 | 2.56x |
| DeepSeek-V4.1-Flash | 32 | 133 | 90.77 | 32.35 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 133 | 111.88 | 39.59 | 2.83x |
| DeepSeek-V4.1-Flash | 256 | 133 | 125.28 | 46.88 | 2.67x |
| DeepSeek-V4.1-Flash | 1024 | 133 | 125.67 | 47.19 | 2.66x |
| DeepSeek-V4.1-Flash | 4096 | 133 | 125.67 | 47.19 | 2.66x |
| DeepSeek-V4.1-Flash | 1 | 141 | 5.89 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 141 | 11.46 | 8.71 | 1.31x |
| DeepSeek-V4.1-Flash | 4 | 141 | 21.67 | 12.33 | 1.76x |
| DeepSeek-V4.1-Flash | 8 | 141 | 38.97 | 18.27 | 2.13x |
| DeepSeek-V4.1-Flash | 16 | 141 | 64.29 | 25.19 | 2.55x |
| DeepSeek-V4.1-Flash | 32 | 141 | 93.21 | 33.14 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 141 | 116.14 | 40.69 | 2.85x |
| DeepSeek-V4.1-Flash | 256 | 141 | 131.38 | 48.33 | 2.72x |
| DeepSeek-V4.1-Flash | 1024 | 141 | 131.83 | 48.65 | 2.71x |
| DeepSeek-V4.1-Flash | 4096 | 141 | 131.83 | 48.65 | 2.71x |
| DeepSeek-V4.1-Flash | 1 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 156 | 11.50 | 8.90 | 1.29x |
| DeepSeek-V4.1-Flash | 4 | 156 | 21.83 | 12.63 | 1.73x |
| DeepSeek-V4.1-Flash | 8 | 156 | 39.54 | 18.79 | 2.10x |
| DeepSeek-V4.1-Flash | 16 | 156 | 66.00 | 26.05 | 2.53x |
| DeepSeek-V4.1-Flash | 32 | 156 | 97.31 | 34.51 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 156 | 123.48 | 42.62 | 2.90x |
| DeepSeek-V4.1-Flash | 256 | 156 | 142.21 | 50.89 | 2.79x |
| DeepSeek-V4.1-Flash | 1024 | 156 | 142.80 | 51.24 | 2.79x |
| DeepSeek-V4.1-Flash | 4096 | 156 | 142.80 | 51.24 | 2.79x |
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
| DeepSeek-V4.1-Flash | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4.1-Flash | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4.1-Flash | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4.1-Flash | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4.1-Flash | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4.1-Flash | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4.1-Flash | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4.1-Flash | 4096 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4.1-Flash | 1 | 169 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 169 | 11.53 | 9.04 | 1.27x |
| DeepSeek-V4.1-Flash | 4 | 169 | 21.95 | 12.86 | 1.71x |
| DeepSeek-V4.1-Flash | 8 | 169 | 39.96 | 19.20 | 2.08x |
| DeepSeek-V4.1-Flash | 16 | 169 | 67.27 | 26.73 | 2.52x |
| DeepSeek-V4.1-Flash | 32 | 169 | 100.44 | 35.62 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 169 | 129.24 | 44.17 | 2.93x |
| DeepSeek-V4.1-Flash | 256 | 169 | 150.98 | 52.97 | 2.85x |
| DeepSeek-V4.1-Flash | 1024 | 169 | 151.70 | 53.34 | 2.84x |
| DeepSeek-V4.1-Flash | 4096 | 169 | 151.70 | 53.34 | 2.84x |
| DeepSeek-V4.1-Flash | 1 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 202 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4.1-Flash | 4 | 202 | 22.19 | 13.42 | 1.65x |
| DeepSeek-V4.1-Flash | 8 | 202 | 40.79 | 20.04 | 2.04x |
| DeepSeek-V4.1-Flash | 16 | 202 | 69.87 | 28.30 | 2.47x |
| DeepSeek-V4.1-Flash | 32 | 202 | 107.00 | 38.17 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 202 | 141.77 | 47.74 | 2.97x |
| DeepSeek-V4.1-Flash | 256 | 202 | 170.93 | 57.73 | 2.96x |
| DeepSeek-V4.1-Flash | 1024 | 202 | 171.96 | 58.16 | 2.96x |
| DeepSeek-V4.1-Flash | 4096 | 202 | 171.96 | 58.16 | 2.96x |
| DeepSeek-V4.1-Flash | 1 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 203 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4.1-Flash | 4 | 203 | 22.19 | 13.44 | 1.65x |
| DeepSeek-V4.1-Flash | 8 | 203 | 40.82 | 20.06 | 2.03x |
| DeepSeek-V4.1-Flash | 16 | 203 | 69.94 | 28.35 | 2.47x |
| DeepSeek-V4.1-Flash | 32 | 203 | 107.17 | 38.24 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 203 | 142.11 | 47.84 | 2.97x |
| DeepSeek-V4.1-Flash | 256 | 203 | 171.48 | 57.86 | 2.96x |
| DeepSeek-V4.1-Flash | 1024 | 203 | 172.53 | 58.30 | 2.96x |
| DeepSeek-V4.1-Flash | 4096 | 203 | 172.53 | 58.30 | 2.96x |
| DeepSeek-V4.1-Flash | 1 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 207 | 11.60 | 9.40 | 1.23x |
| DeepSeek-V4.1-Flash | 4 | 207 | 22.22 | 13.50 | 1.65x |
| DeepSeek-V4.1-Flash | 8 | 207 | 40.90 | 20.15 | 2.03x |
| DeepSeek-V4.1-Flash | 16 | 207 | 70.20 | 28.53 | 2.46x |
| DeepSeek-V4.1-Flash | 32 | 207 | 107.85 | 38.53 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 207 | 143.45 | 48.25 | 2.97x |
| DeepSeek-V4.1-Flash | 256 | 207 | 173.68 | 58.40 | 2.97x |
| DeepSeek-V4.1-Flash | 1024 | 207 | 174.76 | 58.84 | 2.97x |
| DeepSeek-V4.1-Flash | 4096 | 207 | 174.76 | 58.84 | 2.97x |
| DeepSeek-V4.1-Flash | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4.1-Flash | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4.1-Flash | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4.1-Flash | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4.1-Flash | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4.1-Flash | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4.1-Flash | 4096 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4.1-Flash | 1 | 225 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 225 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4.1-Flash | 4 | 225 | 22.31 | 13.77 | 1.62x |
| DeepSeek-V4.1-Flash | 8 | 225 | 41.24 | 20.52 | 2.01x |
| DeepSeek-V4.1-Flash | 16 | 225 | 71.28 | 29.30 | 2.43x |
| DeepSeek-V4.1-Flash | 32 | 225 | 110.68 | 39.76 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 225 | 149.06 | 49.97 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 225 | 183.07 | 60.72 | 3.02x |
| DeepSeek-V4.1-Flash | 1024 | 225 | 184.32 | 61.18 | 3.01x |
| DeepSeek-V4.1-Flash | 4096 | 225 | 184.32 | 61.18 | 3.01x |
| DeepSeek-V4.1-Flash | 1 | 255 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash | 2 | 255 | 11.65 | 9.73 | 1.20x |
| DeepSeek-V4.1-Flash | 4 | 255 | 22.44 | 14.20 | 1.58x |
| DeepSeek-V4.1-Flash | 8 | 255 | 41.71 | 21.04 | 1.98x |
| DeepSeek-V4.1-Flash | 16 | 255 | 72.78 | 30.51 | 2.39x |
| DeepSeek-V4.1-Flash | 32 | 255 | 114.67 | 41.62 | 2.76x |
| DeepSeek-V4.1-Flash | 64 | 255 | 157.18 | 52.56 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 255 | 197.07 | 64.26 | 3.07x |
| DeepSeek-V4.1-Flash | 1024 | 255 | 198.60 | 64.78 | 3.07x |
| DeepSeek-V4.1-Flash | 4096 | 255 | 198.60 | 64.78 | 3.07x |
| DeepSeek-V4.1-Flash | 1 | 258 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash | 2 | 258 | 11.66 | 9.75 | 1.20x |
| DeepSeek-V4.1-Flash | 4 | 258 | 22.45 | 14.24 | 1.58x |
| DeepSeek-V4.1-Flash | 8 | 258 | 41.75 | 21.09 | 1.98x |
| DeepSeek-V4.1-Flash | 16 | 258 | 72.92 | 30.62 | 2.38x |
| DeepSeek-V4.1-Flash | 32 | 258 | 115.03 | 41.79 | 2.75x |
| DeepSeek-V4.1-Flash | 64 | 258 | 157.92 | 52.80 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 258 | 198.37 | 64.60 | 3.07x |
| DeepSeek-V4.1-Flash | 1024 | 258 | 199.93 | 65.12 | 3.07x |
| DeepSeek-V4.1-Flash | 4096 | 258 | 199.93 | 65.12 | 3.07x |
| DeepSeek-V4.1-Flash | 1 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 2 | 311 | 11.70 | 10.03 | 1.17x |
| DeepSeek-V4.1-Flash | 4 | 311 | 22.62 | 14.90 | 1.52x |
| DeepSeek-V4.1-Flash | 8 | 311 | 42.35 | 21.84 | 1.94x |
| DeepSeek-V4.1-Flash | 16 | 311 | 74.88 | 32.49 | 2.30x |
| DeepSeek-V4.1-Flash | 32 | 311 | 120.39 | 44.46 | 2.71x |
| DeepSeek-V4.1-Flash | 64 | 311 | 169.19 | 56.66 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 311 | 218.70 | 70.00 | 3.12x |
| DeepSeek-V4.1-Flash | 1024 | 311 | 220.71 | 70.59 | 3.13x |
| DeepSeek-V4.1-Flash | 4096 | 311 | 220.71 | 70.59 | 3.13x |
| DeepSeek-V4.1-Flash | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 335 | 11.71 | 10.13 | 1.16x |
| DeepSeek-V4.1-Flash | 4 | 335 | 22.67 | 15.17 | 1.49x |
| DeepSeek-V4.1-Flash | 8 | 335 | 42.57 | 22.14 | 1.92x |
| DeepSeek-V4.1-Flash | 16 | 335 | 75.58 | 33.24 | 2.27x |
| DeepSeek-V4.1-Flash | 32 | 335 | 122.34 | 45.48 | 2.69x |
| DeepSeek-V4.1-Flash | 64 | 335 | 173.40 | 58.23 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 335 | 226.52 | 72.22 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4.1-Flash | 4096 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4.1-Flash | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 336 | 11.71 | 10.14 | 1.16x |
| DeepSeek-V4.1-Flash | 4 | 336 | 22.68 | 15.18 | 1.49x |
| DeepSeek-V4.1-Flash | 8 | 336 | 42.57 | 22.15 | 1.92x |
| DeepSeek-V4.1-Flash | 16 | 336 | 75.61 | 33.27 | 2.27x |
| DeepSeek-V4.1-Flash | 32 | 336 | 122.42 | 45.52 | 2.69x |
| DeepSeek-V4.1-Flash | 64 | 336 | 173.56 | 58.30 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 336 | 226.83 | 72.31 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4.1-Flash | 4096 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4.1-Flash | 1 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 337 | 11.72 | 10.14 | 1.16x |
| DeepSeek-V4.1-Flash | 4 | 337 | 22.68 | 15.19 | 1.49x |
| DeepSeek-V4.1-Flash | 8 | 337 | 42.58 | 22.16 | 1.92x |
| DeepSeek-V4.1-Flash | 16 | 337 | 75.64 | 33.30 | 2.27x |
| DeepSeek-V4.1-Flash | 32 | 337 | 122.49 | 45.56 | 2.69x |
| DeepSeek-V4.1-Flash | 64 | 337 | 173.73 | 58.36 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 337 | 227.14 | 72.40 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 337 | 229.35 | 73.00 | 3.14x |
| DeepSeek-V4.1-Flash | 4096 | 337 | 229.35 | 73.00 | 3.14x |
| DeepSeek-V4.1-Flash | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 2 | 448 | 11.76 | 10.50 | 1.12x |
| DeepSeek-V4.1-Flash | 4 | 448 | 22.87 | 16.25 | 1.41x |
| DeepSeek-V4.1-Flash | 8 | 448 | 43.27 | 23.34 | 1.85x |
| DeepSeek-V4.1-Flash | 16 | 448 | 77.94 | 36.03 | 2.16x |
| DeepSeek-V4.1-Flash | 32 | 448 | 129.03 | 49.47 | 2.61x |
| DeepSeek-V4.1-Flash | 64 | 448 | 188.21 | 64.80 | 2.90x |
| DeepSeek-V4.1-Flash | 256 | 448 | 255.15 | 81.21 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4.1-Flash | 4096 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4.1-Flash | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash | 2 | 672 | 11.81 | 10.91 | 1.08x |
| DeepSeek-V4.1-Flash | 4 | 672 | 23.06 | 17.73 | 1.30x |
| DeepSeek-V4.1-Flash | 8 | 672 | 43.98 | 25.33 | 1.74x |
| DeepSeek-V4.1-Flash | 16 | 672 | 80.37 | 39.17 | 2.05x |
| DeepSeek-V4.1-Flash | 32 | 672 | 136.13 | 55.89 | 2.44x |
| DeepSeek-V4.1-Flash | 64 | 672 | 204.63 | 73.69 | 2.78x |
| DeepSeek-V4.1-Flash | 256 | 672 | 288.80 | 93.78 | 3.08x |
| DeepSeek-V4.1-Flash | 1024 | 672 | 292.67 | 94.67 | 3.09x |
| DeepSeek-V4.1-Flash | 4096 | 672 | 292.67 | 94.67 | 3.09x |

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
| gpu | DeepSeek-V4.1-Flash | 1 | 860.60 | 32.3% |
| rom | DeepSeek-V4.1-Flash | 1 | 227.38 | 94.2% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash | sram | interleaved | 128 B | 1.77x |
| DeepSeek-V4.1-Flash | hbm | interleaved | 32 B | 1.34x |

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
| DeepSeek-V4.1-Flash | 1 | 54 | 32.11% | 73.49 | 4.24 |
| DeepSeek-V4.1-Flash | 2 | 54 | 32.11% | 73.49 | 4.24 |
| DeepSeek-V4.1-Flash | 4 | 1 | 3.74% | 9.04 | 4.24 |
| DeepSeek-V4.1-Flash | 8 | 1 | 3.74% | 9.04 | 4.24 |
| DeepSeek-V4.1-Flash | 16 | 1 | 3.74% | 9.04 | 4.24 |

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
| DeepSeek-V4.1-Flash | 1 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 437.6 | 49,884.3 |
| DeepSeek-V4.1-Flash | 2 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 437.6 | 49,884.3 |
| DeepSeek-V4.1-Flash | 4 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 437.6 | 49,884.3 |
| DeepSeek-V4.1-Flash | 8 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 437.6 | 49,884.3 |
| DeepSeek-V4.1-Flash | 16 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 437.6 | 49,884.3 |
| DeepSeek-V4.1-Flash | 32 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 437.6 | 49,884.3 |
| DeepSeek-V4.1-Flash | 64 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 437.6 | 49,884.3 |
| DeepSeek-V4.1-Flash | 256 | 3.47% | 18.6 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 199.6 | 51,093.3 |
| DeepSeek-V4.1-Flash | 1024 | 13.19% | 46.6 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 50.6 | 51,796.5 |
| DeepSeek-V4.1-Flash | 4096 | 43.21% | 133.3 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 12.7 | 51,855.2 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 1 |
| gpu | link_latency | 738 |
| gpu | weight_read | 541 |
| rom | compute | 739 |
| rom | infeasible | 1988 |
| rom | kv_read | 47 |
| rom | layer_fixed_latency | 528 |
| rom | link_latency | 833 |
| rom | weight_read | 325 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 1988 |

## Mechanical consistency audit

**FAIL** over 119,083 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x109', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x115', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x126', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x132', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x135', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x158', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x210', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x315', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x109', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x115', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x126', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x132', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x135', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x158', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x210', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x315', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x109', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x115', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x126', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x132', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x135', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x158', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x210', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x315', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x109', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x115', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x126', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x132', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x135', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x158', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x210', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x315', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 48 |
| assumed | 77 |

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
- `serial_latency.hardware_links.rom_board_serdes`
- `serial_latency.hardware_links.rom_package_ucie`
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

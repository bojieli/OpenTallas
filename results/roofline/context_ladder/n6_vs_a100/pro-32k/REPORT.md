# Area-constrained roofline: n6_vs_a100-pro-32k

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Pro-0813 at 32,768 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 128x (ROM-N6-native-HBMKV-array-hw-pipeline-x208, 208 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 95 devices. On the GPU side the correction reaches 117x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 168 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Pro-0813 takes 195 x 815 mm2 (158,925 mm2, array, KV in SRAM) at 4,768 tok/s per user and 30 tok/s per 1,000 mm2, holding 1 session, against 192 copies of one unified HBM die at the same silicon: 7.0x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 306,440 mm2 of ROM silicon at 5,168 tok/s per user against 306,446 mm2 of a100_sxm_80gb-x371-tensor at 525 tok/s: **9.8x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 81,864 resident sessions against the GPU cluster's 78,075. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 17.03x to it.** At 242,055 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 41.23 tok/s and the same silicon running tensor delivers 702 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`) to 4.07x (DeepSeek-V4-Pro-0813, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Pro-0813 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 154 to 32,053 tok/s, and its rate with every slot occupied from 31,961 to 32,053. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 208 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,823 us over NVLink, capping per-user decode at 548 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 262.3 us and cap it at 3,812 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 7 to the array and 3 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 40 of 3531 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 53.7x of aggregate throughput (DeepSeek-V4-Pro-0813). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 18.90x, on DeepSeek-V4-Pro-0813 at batch 4096, where the busiest region carries 3.12x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4-Pro-0813 at 32,768 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x195`** -- 195 x 815 mm2 reticle dies, 158,925 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **4,767.8 tok/s per user** (0.21 ms/token), binding on `link_latency`
- **30.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,768 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 9,832 W at 0.062 W/mm2, 2,062.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 192 copies of one unified HBM die -- `a100_sxm_80gb-x192-tensor`, 158,592 mm2, area ratio 1.0021 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 158,925 | 158,592 | 1.0021 |
| user tok/s | 4,767.8 | 682.7 | 6.98x |
| aggregate tok/s | 4,768 | 683 | 0.60x |
| resident sessions | 1 | 39,103 | -- |
| J/token | 2.0622 | 44.7948 | 21.7x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 39,103 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x293-tensor` at 242,018 mm2 and 701.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill` | 295,030 | 4,952.2 | 16.8 | 78,815 | 9.44x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 16.9 | 81,864 | 9.84x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x193` | 157,295 | 4,654.5 | 29.6 | 1 | 6.82x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x195` | 158,925 | 4,767.8 | 30.0 | 1 | 6.98x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x195` | 158,925 | 4,767.8 | 30.0 | -- | 30.0 | ACCEPT |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 16.9 | 2.7 | 30.0 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x195` **<-- recommended** | 158,925 | 195 | 4,767.8 | 4,768 | 30.0 | 1 | `link_latency` | 9,832 | 2,062.2 | `a100_sxm_80gb-x192-tensor` | 6.98x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 376 | 5,167.5 | 485,749 | 16.9 | 81,864 | `compute` | 48,196 | 6,672.7 | `a100_sxm_80gb-x371-tensor` | 9.84x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 246 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x195` | 158,925 | 4,767.8 | 30.0 | 1 |
| array | 246 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 16.9 | 81,864 |
| array | 246 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x193` | 157,295 | 4,654.5 | 29.6 | 1 |
| wafer | 60 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 3,578.3 | 19.4 | 1 |
| wafer | 60 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 3,782.8 | 13.6 | 11,234 |
| wafer | 60 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 3,578.3 | 19.4 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 485,749 | 81,864 | 48,196 | 6,672.7 | `compute` | `a100_sxm_80gb-x371-tensor` | 525.2 | 78,075 | 106,172.2 | 1.000 | 9.84x | 15.9x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 3,782.8 | 22,697 | 11,234 | 26,222 | 6,789.2 | `link_latency` | `a100_sxm_80gb-x336-tensor` | 523.5 | 70,455 | 96,853.3 | 0.999 | 7.23x | 14.3x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 4,637.0 | 394,147 | 74,025 | 40,824 | 6,406.7 | `compute` | `a100_sxm_80gb-x335-tensor` | 523.5 | 70,237 | 96,587.8 | 1.001 | 8.86x | 15.1x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 3,782.8 | -- | 11,234 | -- | 6,789.2 | -- | -- | -- | -- | -- | 0.999 | 0.82x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 485,749 | 81,864 | 48,196 | 3,350.6 | `compute` | `a100_sxm_80gb-x371-tensor` | 466.1 | 78,075 | 60,228.9 | 1.000 | 11.09x | 18.0x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 3,782.8 | 22,697 | 11,234 | 26,222 | 3,408.9 | `link_latency` | `a100_sxm_80gb-x336-tensor` | 464.4 | 70,455 | 54,998.9 | 0.999 | 8.15x | 16.1x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 4,637.0 | 394,147 | 74,025 | 40,824 | 3,217.6 | `compute` | `a100_sxm_80gb-x335-tensor` | 464.3 | 70,237 | 54,850.3 | 1.001 | 9.99x | 17.0x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 3,782.8 | -- | 11,234 | -- | 3,408.9 | -- | -- | -- | -- | -- | 0.999 | 0.82x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 485,749 | 81,864 | 48,196 | 1,689.6 | `compute` | `a100_sxm_80gb-x371-tensor` | 380.6 | 78,075 | 37,228.9 | 1.000 | 13.58x | 22.0x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 3,782.8 | 22,697 | 11,234 | 26,222 | 1,718.7 | `link_latency` | `a100_sxm_80gb-x336-tensor` | 379.0 | 70,455 | 34,043.3 | 0.999 | 9.98x | 19.8x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 4,637.0 | 394,147 | 74,025 | 40,824 | 1,623.1 | `compute` | `a100_sxm_80gb-x335-tensor` | 378.9 | 70,237 | 33,953.1 | 1.001 | 12.24x | 20.9x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 3,782.8 | -- | 11,234 | -- | 1,718.7 | -- | -- | -- | -- | -- | 0.999 | 0.82x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 485,749 | 81,864 | 48,196 | 859.1 | `compute` | `a100_sxm_80gb-x371-tensor` | 278.7 | 78,075 | 25,674.2 | 1.000 | 18.54x | 29.9x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,782.5 | 30,260 | 14,979 | 35,249 | 1,164.9 | `link_latency` | `a100_sxm_80gb-x448-tensor` | 281.0 | 94,840 | 30,423.3 | 0.999 | 13.46x | 26.1x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 485,749 | 81,864 | 48,196 | 443.8 | `compute` | `a100_sxm_80gb-x371-hybrid` | 262.2 | 78,075 | 16,956.0 | 1.000 | 19.71x | 38.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,724.1 | 59,585 | 22,469 | 53,154 | 892.1 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 262.5 | 143,610 | 27,290.1 | 0.999 | 14.19x | 30.6x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 485,749 | 81,864 | 48,196 | 236.2 | `compute` | `a100_sxm_80gb-x371-hybrid` | 262.2 | 78,075 | 10,572.0 | 1.000 | 19.71x | 44.8x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,527.5 | 112,878 | 22,469 | 54,207 | 480.2 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 262.5 | 143,610 | 15,739.0 | 0.999 | 13.44x | 32.8x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | 5,167.5 | 485,749 | 81,864 | 48,196 | 132.4 | `compute` | `a100_sxm_80gb-x371-hybrid` | 239.0 | 78,075 | 6,937.5 | 1.000 | 21.62x | 52.4x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,315.7 | 212,205 | 22,469 | 71,106 | 335.1 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 262.5 | 143,610 | 9,963.5 | 0.999 | 12.63x | 29.7x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 2,292.1 | 586,777 | 86,218 | 50,701 | 86.4 | `compute` | `a100_sxm_80gb-x391-hybrid` | 125.7 | 82,430 | 3,618.6 | 0.999 | 18.23x | 28.7x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 2,379.9 | 609,252 | 22,469 | 78,721 | 129.2 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 170.3 | 143,610 | 4,497.8 | 0.999 | 13.97x | 27.3x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 607.5 | 622,075 | 86,218 | 51,527 | 82.8 | `compute` | `a100_sxm_80gb-x391-expert` | 91.9 | 78,618 | 705.6 | 0.999 | 6.61x | 8.5x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,086.9 | 1,112,948 | 22,469 | 87,153 | 78.3 | `kv_read` | `a100_sxm_80gb-x672-expert` | 110.0 | 136,878 | 967.1 | 0.999 | 9.88x | 12.4x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 153.2 | 627,668 | 86,218 | 50,000 | 79.7 | `compute` | `a100_sxm_80gb-x391-expert` | 63.8 | 78,618 | 256.5 | 0.999 | 2.40x | 3.2x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 342.5 | 1,402,911 | 22,469 | 90,373 | 64.4 | `kv_read` | `a100_sxm_80gb-x672-expert` | 84.2 | 136,878 | 321.7 | 0.999 | 4.07x | 5.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x195` | 158,925 | array | SRAM | 1 |
| 2 | `ROM-N6-native-HBMKV-array-hw-tensor-x227` | 185,005 | array | HBM | 49,423 |
| 4 | `ROM-N6-native-HBMKV-array-hw-tensor-x231` | 188,265 | array | HBM | 50,294 |
| 8 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | wafer | HBM | 7,489 |
| 16-64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x376` | 306,440 | array | HBM | 81,864 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | array | HBM | 86,218 |
| 1024 | `ROM-N6-native-HBMKV-wafer-pipeline-x8` | 369,800 | wafer | HBM | 14,979 |
| 4096 | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | wafer | HBM | 22,469 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro-0813 | HBM | rom | 208, 227, 231, 248, 287, 297, 340, 362, 363, 396 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 208, 227, 231, 248, 287, 297, 340, 374, 375, 376, 396 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 193, 195, 227, 230, 248, 265, 266, 276, 340, 368 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 193, 195, 227, 230, 248, 265, 266, 276, 340, 368 |

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

- **0 of 3,531 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 35%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 39 | 0 | 65.6% | 79.9% | 0.387 | 55% |
| gpu | wafer (>=40,000 mm2) | 1,200 | 0 | 70.4% | 79.8% | 0.386 | 67% |
| rom | wafer (>=40,000 mm2) | 2,292 | 0 | 19.6% | 37.6% | 0.188 | 93% |

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
| DeepSeek-V4-Pro-0813 | 1 | 295,030 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill` | 6.587914 | 45,343.9 | compute | `DSV4-Pro/a100_sxm_80gb-x357-tensor` | 102.444708 | 53,742.1 | link_latency | 15.55x |
| DeepSeek-V4-Pro-0813 | 2 | 295,030 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill` | 3.308226 | 45,343.9 | compute | `DSV4-Pro/a100_sxm_80gb-x357-tensor` | 58.136972 | 54,121.7 | link_latency | 17.57x |
| DeepSeek-V4-Pro-0813 | 4 | 295,030 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill` | 1.668381 | 45,343.9 | compute | `DSV4-Pro/a100_sxm_80gb-x357-tensor` | 35.954725 | 54,649.1 | link_latency | 21.55x |
| DeepSeek-V4-Pro-0813 | 8 | 295,030 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill` | 0.848459 | 45,343.9 | compute | `DSV4-Pro/a100_sxm_80gb-x357-tensor` | 24.808884 | 55,216.3 | link_latency | 29.24x |
| DeepSeek-V4-Pro-0813 | 16 | 295,030 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill` | 0.438498 | 45,343.9 | compute | `DSV4-Pro/a100_sxm_80gb-x357-hybrid` | 16.408238 | 101,226.7 | weight_read | 37.42x |
| DeepSeek-V4-Pro-0813 | 32 | 295,030 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill` | 0.233518 | 45,343.9 | compute | `DSV4-Pro/a100_sxm_80gb-x357-hybrid` | 10.298077 | 101,226.7 | weight_read | 44.10x |
| DeepSeek-V4-Pro-0813 | 64 | 295,030 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill` | 0.131028 | 45,343.9 | compute | `DSV4-Pro/a100_sxm_80gb-x357-hybrid` | 6.747857 | 102,258.3 | weight_read | 51.50x |
| DeepSeek-V4-Pro-0813 | 256 | 322,740 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 0.086407 | 50,701.4 | compute | `DSV4-Pro/a100_sxm_80gb-x391-hybrid` | 3.618622 | 116,458.2 | weight_read | 28.73x |
| DeepSeek-V4-Pro-0813 | 1024 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.078308 | 87,152.6 | kv_read | `DSV4-Pro/a100_sxm_80gb-x672-expert` | 0.967103 | 108,930.9 | weight_read | 12.35x |
| DeepSeek-V4-Pro-0813 | 4096 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.064418 | 90,373.3 | kv_read | `DSV4-Pro/a100_sxm_80gb-x672-expert` | 0.321656 | 110,940.0 | weight_read | 4.99x |

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
| DeepSeek-V4-Pro-0813 | 32,768 | 1,600 B | 892.7 GB | 4.46 | 0.110 GB | 0.331 GB | 359.0 |

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
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 31,487.3 | wafer-pipeline | 3,578.3 | wafer-hybrid | 8.80x | 3,592.2 | pipeline | 690.5 | tensor | 5.20x | 8.77x | 5.18x | 0.59x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 37,061.3 | wafer-pipeline | 3,782.8 | wafer-hybrid | 9.80x | 4,123.0 | pipeline | 523.5 | tensor | 7.88x | 8.99x | 7.23x | 0.80x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 37,757.9 | wafer-pipeline | 3,782.5 | wafer-hybrid | 9.98x | 4,451.9 | pipeline | 528.1 | tensor | 8.43x | 8.48x | 7.16x | 0.84x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 38,435.0 | wafer-pipeline | 3,776.7 | wafer-hybrid | 10.18x | 4,837.8 | pipeline | 532.8 | tensor | 9.08x | 7.94x | 7.09x | 0.89x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.59x to 0.89x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x376 | 306,440 | 5,167.5 | 485,749.3 | compute | DSV4-Pro/a100_sxm_80gb-x371-tensor | 306,446 | 1.00x | tensor | 1,821.36 | 525.2 | 525.2 | link_latency | 9.84x | 31.76x | 125.34x | 9.84x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x193 | 157,295 | 4,654.5 | 4,654.5 | link_latency | DSV4-Pro/a100_sxm_80gb-x190-tensor | 156,940 | 1.00x | tensor | 1,321.76 | 682.1 | 682.1 | link_latency | 6.82x | 0.59x | 112.90x | 6.82x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x376 | 306,440 | 5,167.5 | 485,749.3 | compute | DSV4-Pro/a100_sxm_80gb-x371-tensor | 306,446 | 1.00x | tensor | 2,042.07 | 466.1 | 932.2 | link_latency | 11.09x | 31.76x | 125.34x | 11.09x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x208 | 169,520 | 3,597.2 | 7,194.3 | link_latency | DSV4-Pro/a100_sxm_80gb-x205-tensor | 169,330 | 1.00x | tensor | 1,539.54 | 584.0 | 1,168.0 | link_latency | 6.16x | 0.85x | 87.25x | 6.16x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x376 | 306,440 | 5,167.5 | 485,749.3 | compute | DSV4-Pro/a100_sxm_80gb-x371-tensor | 306,446 | 1.00x | tensor | 2,483.51 | 380.6 | 1,522.3 | link_latency | 13.58x | 31.76x | 125.34x | 13.58x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x208 | 169,520 | 2,873.0 | 11,492.0 | link_latency | DSV4-Pro/a100_sxm_80gb-x205-tensor | 169,330 | 1.00x | tensor | 1,973.76 | 450.4 | 1,801.7 | link_latency | 6.38x | 1.36x | 69.68x | 6.38x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x376 | 306,440 | 5,167.5 | 485,749.3 | compute | DSV4-Pro/a100_sxm_80gb-x371-tensor | 306,446 | 1.00x | tensor | 3,366.38 | 278.7 | 2,229.6 | link_latency | 18.54x | 31.76x | 125.34x | 18.54x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x208 | 169,520 | 2,048.3 | 16,386.5 | compute | DSV4-Pro/a100_sxm_80gb-x205-tensor | 169,330 | 1.00x | tensor | 2,842.20 | 309.7 | 2,477.5 | link_latency | 6.61x | 1.94x | 49.68x | 6.61x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x376 | 306,440 | 5,167.5 | 485,749.3 | compute | DSV4-Pro/a100_sxm_80gb-x371-hybrid | 306,446 | 1.00x | hybrid | 745.06 | 262.2 | 12,323.8 | weight_read | 19.71x | 31.76x | 125.34x | 19.71x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x208 | 169,520 | 1,301.3 | 20,820.1 | compute | DSV4-Pro/a100_sxm_80gb-x205-hybrid | 169,330 | 1.00x | hybrid | 690.39 | 265.8 | 6,910.2 | weight_read | 4.90x | 2.46x | 31.56x | 4.90x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x376 | 306,440 | 5,167.5 | 485,749.3 | compute | DSV4-Pro/a100_sxm_80gb-x371-hybrid | 306,446 | 1.00x | hybrid | 745.06 | 262.2 | 12,323.8 | weight_read | 19.71x | 31.76x | 125.34x | 19.71x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x208 | 169,520 | 752.4 | 24,077.4 | compute | DSV4-Pro/a100_sxm_80gb-x205-hybrid | 169,330 | 1.00x | hybrid | 697.23 | 250.2 | 8,006.4 | weight_read | 3.01x | 2.85x | 18.25x | 3.01x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x376 | 306,440 | 5,167.5 | 485,749.3 | compute | DSV4-Pro/a100_sxm_80gb-x371-hybrid | 306,446 | 1.00x | hybrid | 760.14 | 239.0 | 15,294.7 | weight_read | 21.62x | 31.76x | 125.34x | 21.62x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x208 | 169,520 | 494.3 | 31,633.6 | compute | DSV4-Pro/a100_sxm_80gb-x205-hybrid | 169,330 | 1.00x | hybrid | 733.71 | 191.1 | 12,231.8 | weight_read | 2.59x | 2.59x | 11.99x | 2.59x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 2,379.9 | 609,251.5 | link_latency | DSV4-Pro/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 883.30 | 170.3 | 43,596.8 | weight_read | 13.97x | 13.97x | 57.72x | 14.18x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x208 | 169,520 | 124.9 | 31,979.5 | compute | DSV4-Pro/a100_sxm_80gb-x205-expert | 169,330 | 1.00x | expert | 1,538.56 | 83.1 | 21,279.3 | weight_read | 1.50x | 1.50x | 3.27x | 1.50x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,086.9 | 1,112,948.0 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-expert | 555,072 | 1.00x | expert | 1,683.85 | 110.0 | 112,636.3 | weight_read | 9.88x | 9.88x | 30.78x | 9.88x |
| DeepSeek-V4-Pro-0813 | 1024 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x208 | 169,520 | 31.3 | 32,038.2 | compute | DSV4-Pro/a100_sxm_80gb-x205-expert | 169,330 | 1.00x | expert | 3,581.24 | 69.4 | 71,051.3 | weight_read | 0.45x | 0.45x | 1.70x | 0.45x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 342.5 | 1,402,910.9 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-expert | 555,072 | 1.00x | expert | 4,162.42 | 84.2 | 344,902.7 | weight_read | 4.07x | 4.07x | 21.38x | 4.07x |
| DeepSeek-V4-Pro-0813 | 4096 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x208 | 169,520 | 7.8 | 32,052.9 | compute | DSV4-Pro/a100_sxm_80gb-x205-expert | 169,330 | 1.00x | expert | 11,751.99 | 37.3 | 152,652.4 | compute | 0.21x | 0.21x | 1.19x | 0.21x |

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
| DeepSeek-V4-Pro-0813 | 32 | 26,432 | 41.4 | 488.2 | 273.1 | tensor | 1,278.03 | 62.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 41.3 | 572.0 | 272.5 | tensor | 1,300.52 | 74.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 94 | 77,644 | 41.2 | 630.2 | 266.9 | tensor | 1,313.01 | 82.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 103 | 85,078 | 41.2 | 638.7 | 269.3 | tensor | 1,314.36 | 83.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 41.2 | 645.9 | 271.2 | tensor | 1,315.51 | 85.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 125 | 103,250 | 41.2 | 654.6 | 265.6 | tensor | 1,317.39 | 86.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 41.2 | 675.0 | 269.9 | tensor | 1,320.51 | 89.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 190 | 156,940 | 41.2 | 682.1 | 267.0 | tensor | 1,321.76 | 90.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 192 | 158,592 | 41.2 | 682.7 | 269.3 | tensor | 1,321.76 | 90.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 205 | 169,330 | 41.2 | 686.1 | 265.8 | tensor | 1,322.43 | 90.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 41.2 | 690.5 | 268.5 | tensor | 1,323.01 | 91.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 227 | 187,502 | 41.2 | 691.1 | 263.7 | tensor | 1,323.27 | 91.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 228 | 188,328 | 41.2 | 691.3 | 264.6 | tensor | 1,323.27 | 91.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 245 | 202,370 | 41.2 | 694.6 | 265.4 | tensor | 1,323.73 | 91.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 261 | 215,586 | 41.2 | 697.3 | 265.2 | tensor | 1,324.14 | 92.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 262 | 216,412 | 41.2 | 697.5 | 266.0 | tensor | 1,324.14 | 92.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 272 | 224,672 | 41.2 | 699.1 | 267.4 | tensor | 1,324.33 | 92.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 41.2 | 700.2 | 267.2 | tensor | 1,324.51 | 92.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 283 | 233,758 | 41.2 | 700.6 | 263.3 | tensor | 1,324.67 | 92.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 293 | 242,018 | 41.2 | 701.9 | 264.7 | tensor | 1,324.83 | 93.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 335 | 276,710 | 41.2 | 523.5 | 265.3 | tensor | 1,820.83 | 95.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 41.2 | 523.5 | 265.9 | tensor | 1,820.83 | 95.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 357 | 294,882 | 41.2 | 524.6 | 263.6 | tensor | 1,821.16 | 95.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 358 | 295,708 | 41.2 | 524.6 | 264.2 | tensor | 1,821.16 | 95.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 363 | 299,838 | 41.2 | 524.9 | 262.3 | tensor | 1,821.26 | 95.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 369 | 304,794 | 41.2 | 525.1 | 261.1 | tensor | 1,821.36 | 95.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 370 | 305,620 | 41.2 | 525.2 | 261.6 | tensor | 1,821.36 | 95.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 371 | 306,446 | 41.2 | 525.2 | 262.2 | tensor | 1,821.36 | 95.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 391 | 322,966 | 41.2 | 526.1 | 264.1 | tensor | 1,821.54 | 95.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 41.2 | 528.1 | 263.4 | tensor | 1,822.07 | 96.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 41.2 | 532.8 | 262.5 | tensor | 1,823.32 | 97.2% | link_latency |

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
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x266 | DeepSeek-V4-Pro-0813 | 266 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x195 | DeepSeek-V4-Pro-0813 | 195 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.32 us | 597.7 tok/s | 5,976.6 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 49 on rom_board_serdes (traversals 13.2) = 163.90 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x266 | DeepSeek-V4-Pro-0813 | 266 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x265 | DeepSeek-V4-Pro-0813 | 265 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x5 | DeepSeek-V4-Pro-0813 | 5 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x193 | DeepSeek-V4-Pro-0813 | 193 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.11 us | 75.6 tok/s | 756.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 696.80 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | rom_wafer_serdes | 244 | 262.35 us | 381.2 tok/s | 3,811.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 27.50 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x248 | DeepSeek-V4-Pro-0813 | 248 | hybrid | nvlink3 | infiniband_hdr | 152 | 703.41 us | 142.2 tok/s | 1,421.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.10 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer | rom_wafer_serdes | 126 | 235.26 us | 425.1 tok/s | 4,250.6 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.41 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x376 | DeepSeek-V4-Pro-0813 | 376 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x231 | DeepSeek-V4-Pro-0813 | 231 | tensor | rom_package_ucie | rom_board_serdes | 244 | 194.17 us | 515.0 tok/s | 5,150.2 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 58 on rom_board_serdes (traversals 15.4) = 190.74 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x375 | DeepSeek-V4-Pro-0813 | 375 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x374 | DeepSeek-V4-Pro-0813 | 374 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x6 | DeepSeek-V4-Pro-0813 | 6 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x208 | DeepSeek-V4-Pro-0813 | 208 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | rom_wafer_serdes | 244 | 262.35 us | 381.2 tok/s | 3,811.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 27.50 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x287 | DeepSeek-V4-Pro-0813 | 287 | hybrid | nvlink3 | infiniband_hdr | 157 | 716.42 us | 139.6 tok/s | 1,395.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 91.12 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer | rom_wafer_serdes | 126 | 235.26 us | 425.1 tok/s | 4,250.6 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.41 us |
| DSV4-Pro/a100_sxm_80gb-x32-pipeline | DeepSeek-V4-Pro-0813 | 32 | pipeline | nvlink3 | infiniband_hdr | 31 | 79.15 us | 1,263.5 tok/s | 12,634.5 tok/s | 28 x point_to_point span 2 on nvlink3 (traversals 1.0) = 71.34 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.81 us |
| DSV4-Pro/a100_sxm_80gb-x32-tensor | DeepSeek-V4-Pro-0813 | 32 | tensor | nvlink3 | infiniband_hdr | 244 | 1,278.03 us | 78.2 tok/s | 782.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 652.73 us |
| DSV4-Pro/a100_sxm_80gb-x32-hybrid | DeepSeek-V4-Pro-0813 | 32 | hybrid | nvlink3 | infiniband_hdr | 125 | 633.11 us | 157.9 tok/s | 1,579.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.81 us |
| DSV4-Pro/a100_sxm_80gb-x32-expert | DeepSeek-V4-Pro-0813 | 32 | expert | nvlink3 | infiniband_hdr | 244 | 874.60 us | 114.3 tok/s | 1,143.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 613.83 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 260.78 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,300.52 us | 76.9 tok/s | 768.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 675.22 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 640.92 us | 156.0 tok/s | 1,560.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink3 | infiniband_hdr | 244 | 867.34 us | 115.3 tok/s | 1,152.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 612.19 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 255.16 us |
| DSV4-Pro/a100_sxm_80gb-x94-pipeline | DeepSeek-V4-Pro-0813 | 94 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x94-tensor | DeepSeek-V4-Pro-0813 | 94 | tensor | nvlink3 | infiniband_hdr | 244 | 1,313.01 us | 76.2 tok/s | 761.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 687.71 us |
| DSV4-Pro/a100_sxm_80gb-x94-hybrid | DeepSeek-V4-Pro-0813 | 94 | hybrid | nvlink3 | infiniband_hdr | 133 | 653.94 us | 152.9 tok/s | 1,529.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| DSV4-Pro/a100_sxm_80gb-x94-expert | DeepSeek-V4-Pro-0813 | 94 | expert | nvlink3 | infiniband_hdr | 244 | 863.52 us | 115.8 tok/s | 1,158.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.39 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 252.13 us |
| DSV4-Pro/a100_sxm_80gb-x103-pipeline | DeepSeek-V4-Pro-0813 | 103 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x103-tensor | DeepSeek-V4-Pro-0813 | 103 | tensor | nvlink3 | infiniband_hdr | 244 | 1,314.36 us | 76.1 tok/s | 760.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 689.05 us |
| DSV4-Pro/a100_sxm_80gb-x103-hybrid | DeepSeek-V4-Pro-0813 | 103 | hybrid | nvlink3 | infiniband_hdr | 134 | 656.54 us | 152.3 tok/s | 1,523.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.24 us |
| DSV4-Pro/a100_sxm_80gb-x103-expert | DeepSeek-V4-Pro-0813 | 103 | expert | nvlink3 | infiniband_hdr | 244 | 863.01 us | 115.9 tok/s | 1,158.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.28 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.74 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x112-expert | DeepSeek-V4-Pro-0813 | 112 | expert | nvlink3 | infiniband_hdr | 244 | 862.50 us | 115.9 tok/s | 1,159.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.09 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.41 us |
| DSV4-Pro/a100_sxm_80gb-x125-pipeline | DeepSeek-V4-Pro-0813 | 125 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x125-tensor | DeepSeek-V4-Pro-0813 | 125 | tensor | nvlink3 | infiniband_hdr | 244 | 1,317.39 us | 75.9 tok/s | 759.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 692.08 us |
| DSV4-Pro/a100_sxm_80gb-x125-hybrid | DeepSeek-V4-Pro-0813 | 125 | hybrid | nvlink3 | infiniband_hdr | 137 | 664.36 us | 150.5 tok/s | 1,505.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.05 us |
| DSV4-Pro/a100_sxm_80gb-x125-expert | DeepSeek-V4-Pro-0813 | 125 | expert | nvlink3 | infiniband_hdr | 244 | 862.04 us | 116.0 tok/s | 1,160.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.02 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.02 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.51 us | 75.7 tok/s | 757.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 695.20 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 677.37 us | 147.6 tok/s | 1,476.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| DSV4-Pro/a100_sxm_80gb-x168-expert | DeepSeek-V4-Pro-0813 | 168 | expert | nvlink3 | infiniband_hdr | 244 | 860.89 us | 116.2 tok/s | 1,161.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.73 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 250.16 us |
| DSV4-Pro/a100_sxm_80gb-x190-pipeline | DeepSeek-V4-Pro-0813 | 190 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x190-tensor | DeepSeek-V4-Pro-0813 | 190 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x190-hybrid | DeepSeek-V4-Pro-0813 | 190 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x190-expert | DeepSeek-V4-Pro-0813 | 190 | expert | nvlink3 | infiniband_hdr | 244 | 860.53 us | 116.2 tok/s | 1,162.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.67 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.87 us |
| DSV4-Pro/a100_sxm_80gb-x192-pipeline | DeepSeek-V4-Pro-0813 | 192 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x192-tensor | DeepSeek-V4-Pro-0813 | 192 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x192-hybrid | DeepSeek-V4-Pro-0813 | 192 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x192-expert | DeepSeek-V4-Pro-0813 | 192 | expert | nvlink3 | infiniband_hdr | 244 | 860.48 us | 116.2 tok/s | 1,162.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.64 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.85 us |
| DSV4-Pro/a100_sxm_80gb-x205-pipeline | DeepSeek-V4-Pro-0813 | 205 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x205-tensor | DeepSeek-V4-Pro-0813 | 205 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x205-hybrid | DeepSeek-V4-Pro-0813 | 205 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x205-expert | DeepSeek-V4-Pro-0813 | 205 | expert | nvlink3 | infiniband_hdr | 244 | 860.32 us | 116.2 tok/s | 1,162.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.61 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.71 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x224-expert | DeepSeek-V4-Pro-0813 | 224 | expert | nvlink3 | infiniband_hdr | 244 | 860.08 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.53 us |
| DSV4-Pro/a100_sxm_80gb-x227-pipeline | DeepSeek-V4-Pro-0813 | 227 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x227-tensor | DeepSeek-V4-Pro-0813 | 227 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.27 us | 75.6 tok/s | 755.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 697.96 us |
| DSV4-Pro/a100_sxm_80gb-x227-hybrid | DeepSeek-V4-Pro-0813 | 227 | hybrid | nvlink3 | infiniband_hdr | 150 | 698.20 us | 143.2 tok/s | 1,432.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 72.90 us |
| DSV4-Pro/a100_sxm_80gb-x227-expert | DeepSeek-V4-Pro-0813 | 227 | expert | nvlink3 | infiniband_hdr | 244 | 860.06 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.51 us |
| DSV4-Pro/a100_sxm_80gb-x228-pipeline | DeepSeek-V4-Pro-0813 | 228 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x228-tensor | DeepSeek-V4-Pro-0813 | 228 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.27 us | 75.6 tok/s | 755.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 697.96 us |
| DSV4-Pro/a100_sxm_80gb-x228-hybrid | DeepSeek-V4-Pro-0813 | 228 | hybrid | nvlink3 | infiniband_hdr | 150 | 698.20 us | 143.2 tok/s | 1,432.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 72.90 us |
| DSV4-Pro/a100_sxm_80gb-x228-expert | DeepSeek-V4-Pro-0813 | 228 | expert | nvlink3 | infiniband_hdr | 244 | 860.05 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.50 us |
| DSV4-Pro/a100_sxm_80gb-x245-pipeline | DeepSeek-V4-Pro-0813 | 245 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x245-tensor | DeepSeek-V4-Pro-0813 | 245 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.73 us | 75.5 tok/s | 755.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 698.43 us |
| DSV4-Pro/a100_sxm_80gb-x245-hybrid | DeepSeek-V4-Pro-0813 | 245 | hybrid | nvlink3 | infiniband_hdr | 152 | 703.41 us | 142.2 tok/s | 1,421.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.10 us |
| DSV4-Pro/a100_sxm_80gb-x245-expert | DeepSeek-V4-Pro-0813 | 245 | expert | nvlink3 | infiniband_hdr | 244 | 859.88 us | 116.3 tok/s | 1,162.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.51 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.37 us |
| DSV4-Pro/a100_sxm_80gb-x261-pipeline | DeepSeek-V4-Pro-0813 | 261 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x261-tensor | DeepSeek-V4-Pro-0813 | 261 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.14 us | 75.5 tok/s | 755.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 33 on infiniband_hdr (traversals 2.0) = 698.84 us |
| DSV4-Pro/a100_sxm_80gb-x261-hybrid | DeepSeek-V4-Pro-0813 | 261 | hybrid | nvlink3 | infiniband_hdr | 154 | 708.61 us | 141.1 tok/s | 1,411.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 32 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 83.31 us |
| DSV4-Pro/a100_sxm_80gb-x261-expert | DeepSeek-V4-Pro-0813 | 261 | expert | nvlink3 | infiniband_hdr | 244 | 859.75 us | 116.3 tok/s | 1,163.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.48 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.27 us |
| DSV4-Pro/a100_sxm_80gb-x262-pipeline | DeepSeek-V4-Pro-0813 | 262 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x262-tensor | DeepSeek-V4-Pro-0813 | 262 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.14 us | 75.5 tok/s | 755.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 33 on infiniband_hdr (traversals 2.0) = 698.84 us |
| DSV4-Pro/a100_sxm_80gb-x262-hybrid | DeepSeek-V4-Pro-0813 | 262 | hybrid | nvlink3 | infiniband_hdr | 154 | 708.61 us | 141.1 tok/s | 1,411.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 32 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 83.31 us |
| DSV4-Pro/a100_sxm_80gb-x262-expert | DeepSeek-V4-Pro-0813 | 262 | expert | nvlink3 | infiniband_hdr | 244 | 859.74 us | 116.3 tok/s | 1,163.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.48 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.26 us |
| DSV4-Pro/a100_sxm_80gb-x272-pipeline | DeepSeek-V4-Pro-0813 | 272 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x272-tensor | DeepSeek-V4-Pro-0813 | 272 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.33 us | 75.5 tok/s | 755.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 699.03 us |
| DSV4-Pro/a100_sxm_80gb-x272-hybrid | DeepSeek-V4-Pro-0813 | 272 | hybrid | nvlink3 | infiniband_hdr | 155 | 711.22 us | 140.6 tok/s | 1,406.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.91 us |
| DSV4-Pro/a100_sxm_80gb-x272-expert | DeepSeek-V4-Pro-0813 | 272 | expert | nvlink3 | infiniband_hdr | 244 | 859.65 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.45 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.20 us |
| DSV4-Pro/a100_sxm_80gb-x280-pipeline | DeepSeek-V4-Pro-0813 | 280 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x280-tensor | DeepSeek-V4-Pro-0813 | 280 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.51 us | 75.5 tok/s | 755.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 699.20 us |
| DSV4-Pro/a100_sxm_80gb-x280-hybrid | DeepSeek-V4-Pro-0813 | 280 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/a100_sxm_80gb-x280-expert | DeepSeek-V4-Pro-0813 | 280 | expert | nvlink3 | infiniband_hdr | 244 | 859.60 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.44 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.16 us |
| DSV4-Pro/a100_sxm_80gb-x283-pipeline | DeepSeek-V4-Pro-0813 | 283 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x283-tensor | DeepSeek-V4-Pro-0813 | 283 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.67 us | 75.5 tok/s | 754.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 36 on infiniband_hdr (traversals 2.0) = 699.37 us |
| DSV4-Pro/a100_sxm_80gb-x283-hybrid | DeepSeek-V4-Pro-0813 | 283 | hybrid | nvlink3 | infiniband_hdr | 157 | 716.42 us | 139.6 tok/s | 1,395.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 91.12 us |
| DSV4-Pro/a100_sxm_80gb-x283-expert | DeepSeek-V4-Pro-0813 | 283 | expert | nvlink3 | infiniband_hdr | 244 | 859.58 us | 116.3 tok/s | 1,163.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.44 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.14 us |
| DSV4-Pro/a100_sxm_80gb-x293-pipeline | DeepSeek-V4-Pro-0813 | 293 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x293-tensor | DeepSeek-V4-Pro-0813 | 293 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.83 us | 75.5 tok/s | 754.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 37 on infiniband_hdr (traversals 2.0) = 699.53 us |
| DSV4-Pro/a100_sxm_80gb-x293-hybrid | DeepSeek-V4-Pro-0813 | 293 | hybrid | nvlink3 | infiniband_hdr | 158 | 719.03 us | 139.1 tok/s | 1,390.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 36 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 93.72 us |
| DSV4-Pro/a100_sxm_80gb-x293-expert | DeepSeek-V4-Pro-0813 | 293 | expert | nvlink3 | infiniband_hdr | 244 | 859.52 us | 116.3 tok/s | 1,163.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.43 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.09 us |
| DSV4-Pro/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Pro-0813 | 335 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Pro-0813 | 335 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Pro-0813 | 335 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x335-expert | DeepSeek-V4-Pro-0813 | 335 | expert | nvlink3 | infiniband_hdr | 244 | 859.29 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.37 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.91 us |
| DSV4-Pro/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Pro-0813 | 336 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Pro-0813 | 336 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Pro-0813 | 336 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x336-expert | DeepSeek-V4-Pro-0813 | 336 | expert | nvlink3 | infiniband_hdr | 244 | 859.27 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.36 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.91 us |
| DSV4-Pro/a100_sxm_80gb-x357-pipeline | DeepSeek-V4-Pro-0813 | 357 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x357-tensor | DeepSeek-V4-Pro-0813 | 357 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.16 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,195.86 us |
| DSV4-Pro/a100_sxm_80gb-x357-hybrid | DeepSeek-V4-Pro-0813 | 357 | hybrid | nvlink3 | infiniband_hdr | 166 | 739.86 us | 135.2 tok/s | 1,351.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 114.55 us |
| DSV4-Pro/a100_sxm_80gb-x357-expert | DeepSeek-V4-Pro-0813 | 357 | expert | nvlink3 | infiniband_hdr | 244 | 859.18 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.35 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.84 us |
| DSV4-Pro/a100_sxm_80gb-x358-pipeline | DeepSeek-V4-Pro-0813 | 358 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x358-tensor | DeepSeek-V4-Pro-0813 | 358 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.16 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,195.86 us |
| DSV4-Pro/a100_sxm_80gb-x358-hybrid | DeepSeek-V4-Pro-0813 | 358 | hybrid | nvlink3 | infiniband_hdr | 166 | 739.86 us | 135.2 tok/s | 1,351.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 114.55 us |
| DSV4-Pro/a100_sxm_80gb-x358-expert | DeepSeek-V4-Pro-0813 | 358 | expert | nvlink3 | infiniband_hdr | 244 | 859.18 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.35 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.83 us |
| DSV4-Pro/a100_sxm_80gb-x363-pipeline | DeepSeek-V4-Pro-0813 | 363 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x363-tensor | DeepSeek-V4-Pro-0813 | 363 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.26 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 1,195.96 us |
| DSV4-Pro/a100_sxm_80gb-x363-hybrid | DeepSeek-V4-Pro-0813 | 363 | hybrid | nvlink3 | infiniband_hdr | 167 | 742.46 us | 134.7 tok/s | 1,346.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 45 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 117.15 us |
| DSV4-Pro/a100_sxm_80gb-x363-expert | DeepSeek-V4-Pro-0813 | 363 | expert | nvlink3 | infiniband_hdr | 244 | 859.16 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.34 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.82 us |
| DSV4-Pro/a100_sxm_80gb-x369-pipeline | DeepSeek-V4-Pro-0813 | 369 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x369-tensor | DeepSeek-V4-Pro-0813 | 369 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.36 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,196.05 us |
| DSV4-Pro/a100_sxm_80gb-x369-hybrid | DeepSeek-V4-Pro-0813 | 369 | hybrid | nvlink3 | infiniband_hdr | 168 | 745.06 us | 134.2 tok/s | 1,342.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 119.76 us |
| DSV4-Pro/a100_sxm_80gb-x369-expert | DeepSeek-V4-Pro-0813 | 369 | expert | nvlink3 | infiniband_hdr | 244 | 859.13 us | 116.4 tok/s | 1,164.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.33 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.80 us |
| DSV4-Pro/a100_sxm_80gb-x370-pipeline | DeepSeek-V4-Pro-0813 | 370 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x370-tensor | DeepSeek-V4-Pro-0813 | 370 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.36 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,196.05 us |
| DSV4-Pro/a100_sxm_80gb-x370-hybrid | DeepSeek-V4-Pro-0813 | 370 | hybrid | nvlink3 | infiniband_hdr | 168 | 745.06 us | 134.2 tok/s | 1,342.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 119.76 us |
| DSV4-Pro/a100_sxm_80gb-x370-expert | DeepSeek-V4-Pro-0813 | 370 | expert | nvlink3 | infiniband_hdr | 244 | 859.13 us | 116.4 tok/s | 1,164.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.33 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.79 us |
| DSV4-Pro/a100_sxm_80gb-x371-pipeline | DeepSeek-V4-Pro-0813 | 371 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x371-tensor | DeepSeek-V4-Pro-0813 | 371 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.36 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,196.05 us |
| DSV4-Pro/a100_sxm_80gb-x371-hybrid | DeepSeek-V4-Pro-0813 | 371 | hybrid | nvlink3 | infiniband_hdr | 168 | 745.06 us | 134.2 tok/s | 1,342.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 119.76 us |
| DSV4-Pro/a100_sxm_80gb-x371-expert | DeepSeek-V4-Pro-0813 | 371 | expert | nvlink3 | infiniband_hdr | 244 | 859.12 us | 116.4 tok/s | 1,164.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.33 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.79 us |
| DSV4-Pro/a100_sxm_80gb-x391-pipeline | DeepSeek-V4-Pro-0813 | 391 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x391-tensor | DeepSeek-V4-Pro-0813 | 391 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x391-hybrid | DeepSeek-V4-Pro-0813 | 391 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x391-expert | DeepSeek-V4-Pro-0813 | 391 | expert | nvlink3 | infiniband_hdr | 244 | 859.05 us | 116.4 tok/s | 1,164.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.32 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.73 us |
| DSV4-Pro/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Pro-0813 | 448 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Pro-0813 | 448 | tensor | nvlink3 | infiniband_hdr | 244 | 1,822.07 us | 54.9 tok/s | 548.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,196.77 us |
| DSV4-Pro/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Pro-0813 | 448 | hybrid | nvlink3 | infiniband_hdr | 177 | 768.49 us | 130.1 tok/s | 1,301.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 143.19 us |
| DSV4-Pro/a100_sxm_80gb-x448-expert | DeepSeek-V4-Pro-0813 | 448 | expert | nvlink3 | infiniband_hdr | 244 | 858.87 us | 116.4 tok/s | 1,164.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.27 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.60 us |
| DSV4-Pro/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Pro-0813 | 672 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Pro-0813 | 672 | tensor | nvlink3 | infiniband_hdr | 244 | 1,823.32 us | 54.8 tok/s | 548.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,198.02 us |
| DSV4-Pro/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Pro-0813 | 672 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |
| DSV4-Pro/a100_sxm_80gb-x672-expert | DeepSeek-V4-Pro-0813 | 672 | expert | nvlink3 | infiniband_hdr | 244 | 858.47 us | 116.5 tok/s | 1,164.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.18 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.28 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Pro-0813 | 1 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill | 295,030 | 4,952.2 | 0.017 | 4,952.2 (295,030) | 3,733.8 (231,125) | 0.75x | compute |
| DeepSeek-V4-Pro-0813 | 2 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill | 295,030 | 4,952.2 | 0.017 | 4,952.2 (295,030) | 3,733.8 (231,125) | 0.75x | compute |
| DeepSeek-V4-Pro-0813 | 4 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill | 295,030 | 4,952.2 | 0.017 | 4,952.2 (295,030) | 3,733.8 (231,125) | 0.75x | compute |
| DeepSeek-V4-Pro-0813 | 8 | array | wafer | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill | 295,030 | 4,952.2 | 0.017 | 4,952.2 (295,030) | 3,612.6 (231,125) | 0.73x | compute |
| DeepSeek-V4-Pro-0813 | 16 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill | 295,030 | 4,952.2 | 0.017 | 4,952.2 (295,030) | 3,688.1 (369,800) | 0.74x | compute |
| DeepSeek-V4-Pro-0813 | 32 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill | 295,030 | 4,952.2 | 0.017 | 4,952.2 (295,030) | 3,468.6 (369,800) | 0.70x | compute |
| DeepSeek-V4-Pro-0813 | 64 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x362-romfill | 295,030 | 4,952.2 | 0.017 | 4,952.2 (295,030) | 3,315.7 (554,700) | 0.67x | compute |
| DeepSeek-V4-Pro-0813 | 256 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 2,292.1 | 0.007 | 2,292.1 (322,740) | 2,379.9 (554,700) | 1.04x | compute |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,086.9 | 0.002 | 607.5 (322,740) | 1,086.9 (554,700) | 1.79x | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 342.5 | 0.001 | 153.2 (322,740) | 342.5 (554,700) | 2.24x | kv_read |

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
| DeepSeek-V4-Pro-0813 | 1 | sram | 575,243.9 | 26,013.5 | 26,013.5 | 22.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 575,243.9 | 26,013.5 | 26,013.5 | 22.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 575,243.9 | 26,013.5 | 26,013.5 | 22.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 575,243.9 | 26,013.5 | 30,673.4 | 22.11x | 1.18x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | sram | 575,243.9 | 26,013.5 | 51,250.0 | 22.11x | 1.97x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | sram | 575,243.9 | 26,013.5 | 78,239.2 | 22.11x | 3.01x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | sram | 575,243.9 | 26,013.5 | 129,090.4 | 22.11x | 4.96x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 256 | sram | 609,251.5 | 26,059.3 | 279,066.6 | 23.38x | 10.71x | link_latency | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 1,112,948.0 | 26,098.3 | 351,720.4 | 42.64x | 13.48x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 1,402,910.9 | 26,109.0 | 493,389.6 | 53.73x | 18.90x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 1,030,870.6 | 46,341.8 | 46,341.8 | 22.24x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 1,030,870.6 | 46,341.8 | 46,341.8 | 22.24x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 1,030,870.6 | 46,341.8 | 46,341.8 | 22.24x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 1,030,870.6 | 46,341.8 | 46,341.8 | 22.24x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 1,030,870.6 | 46,341.8 | 54,285.0 | 22.24x | 1.17x | compute | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | rom | 1,030,870.6 | 46,341.8 | 83,991.2 | 22.24x | 1.81x | compute | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | rom | 1,030,870.6 | 46,341.8 | 145,146.1 | 22.24x | 3.13x | compute | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 256 | rom | 1,030,870.6 | 46,446.6 | 279,066.6 | 22.19x | 6.01x | compute | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 1,044,150.1 | 46,605.7 | 351,720.4 | 22.40x | 7.55x | compute | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 1,064,570.6 | 46,645.6 | 554,369.1 | 22.82x | 11.88x | compute | weight_read | weight_read |

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
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,030,870.6 | 1.858 | compute | 1.79x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,030,870.6 | 1.858 | compute | 1.79x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,030,870.6 | 1.858 | compute | 1.79x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,030,870.6 | 1.858 | compute | 1.79x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x104-perregion | 84,760 | 1.00 | 1.99 | 30,673.4 | 0.362 | link_latency | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,030,870.6 | 1.858 | compute | 1.79x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x104-perregion | 84,760 | 1.00 | 2.54 | 51,250.0 | 0.605 | link_latency | 0.09x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x127-perregion-romfill | 103,505 | 1.22 | 2.54 | 54,285.0 | 0.524 | link_latency | 0.09x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,030,870.6 | 1.858 | compute | 1.79x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x104-perregion | 84,760 | 1.00 | 3.49 | 78,239.2 | 0.923 | link_latency | 0.14x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x3-perregion-romfill | 138,675 | 1.79 | 3.49 | 83,991.2 | 0.606 | link_latency | 0.15x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 575,243.9 | 1.037 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,030,870.6 | 1.858 | compute | 1.79x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,013.5 | 0.188 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 1.00 | 46,341.8 | 0.334 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x2-perregion | 92,450 | 1.00 | 4.92 | 129,090.4 | 1.396 | link_latency | 0.22x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 1.79 | 2.93 | 145,146.1 | 1.047 | link_latency | 0.25x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 609,251.5 | 1.098 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,030,870.6 | 1.858 | compute | 1.69x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x104-perstream | 84,760 | 1.00 | 2.46 | 26,059.3 | 0.307 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 1.50 | 46,446.6 | 0.335 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 5.74 | 279,066.6 | 2.012 | kv_read | 0.46x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 1.79 | 5.74 | 279,066.6 | 2.012 | kv_read | 0.46x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,112,948.0 | 2.006 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,044,150.1 | 1.882 | compute | 0.94x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x104-perstream | 84,760 | 1.00 | 9.85 | 26,098.3 | 0.308 | weight_read | 0.02x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 5.99 | 46,605.7 | 0.336 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 13.22 | 351,720.4 | 2.536 | kv_read | 0.32x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 1.79 | 13.22 | 351,720.4 | 2.536 | kv_read | 0.32x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,402,910.9 | 2.529 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,064,570.6 | 1.919 | compute | 0.76x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 23.95 | 26,109.0 | 0.188 | weight_read | 0.02x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.79 | 23.95 | 46,645.6 | 0.336 | weight_read | 0.03x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x104-perregion | 84,760 | 1.00 | 8.13 | 493,389.6 | 5.821 | weight_read | 0.35x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x127-perregion-romfill | 103,505 | 1.22 | 7.20 | 554,369.1 | 5.356 | weight_read | 0.40x |

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
| DeepSeek-V4-Pro-0813 | 1 | 95 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 95 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 95 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 104 | 2.46 | 1.012 | 1.161 | 1.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 104 | 9.85 | 1.071 | 2.124 | 1.98x |
| DeepSeek-V4-Pro-0813 | 4096 | 104 | 39.38 | 1.331 | 3.860 | 2.90x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Pro-0813 | 2 | 32 | 10.07 | 6.00 | 1.68x |
| DeepSeek-V4-Pro-0813 | 4 | 32 | 16.80 | 8.16 | 2.06x |
| DeepSeek-V4-Pro-0813 | 8 | 32 | 24.44 | 10.62 | 2.30x |
| DeepSeek-V4-Pro-0813 | 16 | 32 | 29.88 | 13.24 | 2.26x |
| DeepSeek-V4-Pro-0813 | 32 | 32 | 31.74 | 15.73 | 2.02x |
| DeepSeek-V4-Pro-0813 | 64 | 32 | 31.99 | 17.76 | 1.80x |
| DeepSeek-V4-Pro-0813 | 256 | 32 | 32.00 | 19.56 | 1.64x |
| DeepSeek-V4-Pro-0813 | 1024 | 32 | 32.00 | 19.64 | 1.63x |
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
| DeepSeek-V4-Pro-0813 | 1 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 94 | 11.24 | 7.94 | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | 94 | 20.85 | 11.23 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 94 | 36.19 | 16.05 | 2.25x |
| DeepSeek-V4-Pro-0813 | 16 | 94 | 56.34 | 21.70 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 94 | 75.50 | 27.77 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 94 | 87.07 | 33.34 | 2.61x |
| DeepSeek-V4-Pro-0813 | 256 | 94 | 92.34 | 38.79 | 2.38x |
| DeepSeek-V4-Pro-0813 | 1024 | 94 | 92.45 | 39.02 | 2.37x |
| DeepSeek-V4-Pro-0813 | 4096 | 94 | 92.45 | 39.02 | 2.37x |
| DeepSeek-V4-Pro-0813 | 1 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 103 | 11.30 | 8.12 | 1.39x |
| DeepSeek-V4-Pro-0813 | 4 | 103 | 21.06 | 11.47 | 1.84x |
| DeepSeek-V4-Pro-0813 | 8 | 103 | 36.89 | 16.56 | 2.23x |
| DeepSeek-V4-Pro-0813 | 16 | 103 | 58.29 | 22.49 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 103 | 79.62 | 28.95 | 2.75x |
| DeepSeek-V4-Pro-0813 | 64 | 103 | 93.46 | 34.93 | 2.68x |
| DeepSeek-V4-Pro-0813 | 256 | 103 | 100.40 | 40.84 | 2.46x |
| DeepSeek-V4-Pro-0813 | 1024 | 103 | 100.57 | 41.08 | 2.45x |
| DeepSeek-V4-Pro-0813 | 4096 | 103 | 100.57 | 41.08 | 2.45x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4-Pro-0813 | 4096 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4-Pro-0813 | 1 | 125 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 125 | 11.40 | 8.49 | 1.34x |
| DeepSeek-V4-Pro-0813 | 4 | 125 | 21.45 | 11.99 | 1.79x |
| DeepSeek-V4-Pro-0813 | 8 | 125 | 38.23 | 17.62 | 2.17x |
| DeepSeek-V4-Pro-0813 | 16 | 125 | 62.11 | 24.16 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 125 | 88.13 | 31.52 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 125 | 107.37 | 38.43 | 2.79x |
| DeepSeek-V4-Pro-0813 | 256 | 125 | 118.96 | 45.37 | 2.62x |
| DeepSeek-V4-Pro-0813 | 1024 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4-Pro-0813 | 4096 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4-Pro-0813 | 4096 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4-Pro-0813 | 1 | 190 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 190 | 11.57 | 9.25 | 1.25x |
| DeepSeek-V4-Pro-0813 | 4 | 190 | 22.11 | 13.23 | 1.67x |
| DeepSeek-V4-Pro-0813 | 8 | 190 | 40.52 | 19.76 | 2.05x |
| DeepSeek-V4-Pro-0813 | 16 | 190 | 69.01 | 27.75 | 2.49x |
| DeepSeek-V4-Pro-0813 | 32 | 190 | 104.81 | 37.28 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 190 | 137.53 | 46.50 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 190 | 164.04 | 56.07 | 2.93x |
| DeepSeek-V4-Pro-0813 | 1024 | 190 | 164.96 | 56.48 | 2.92x |
| DeepSeek-V4-Pro-0813 | 4096 | 190 | 164.96 | 56.48 | 2.92x |
| DeepSeek-V4-Pro-0813 | 1 | 192 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 192 | 11.57 | 9.27 | 1.25x |
| DeepSeek-V4-Pro-0813 | 4 | 192 | 22.12 | 13.26 | 1.67x |
| DeepSeek-V4-Pro-0813 | 8 | 192 | 40.57 | 19.81 | 2.05x |
| DeepSeek-V4-Pro-0813 | 16 | 192 | 69.16 | 27.85 | 2.48x |
| DeepSeek-V4-Pro-0813 | 32 | 192 | 105.19 | 37.43 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 192 | 138.26 | 46.71 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 192 | 165.21 | 56.35 | 2.93x |
| DeepSeek-V4-Pro-0813 | 1024 | 192 | 166.15 | 56.77 | 2.93x |
| DeepSeek-V4-Pro-0813 | 4096 | 192 | 166.15 | 56.77 | 2.93x |
| DeepSeek-V4-Pro-0813 | 1 | 205 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 205 | 11.59 | 9.38 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 205 | 22.20 | 13.47 | 1.65x |
| DeepSeek-V4-Pro-0813 | 8 | 205 | 40.86 | 20.11 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 205 | 70.07 | 28.44 | 2.46x |
| DeepSeek-V4-Pro-0813 | 32 | 205 | 107.52 | 38.39 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 205 | 142.78 | 48.05 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 205 | 172.59 | 58.13 | 2.97x |
| DeepSeek-V4-Pro-0813 | 1024 | 205 | 173.65 | 58.57 | 2.96x |
| DeepSeek-V4-Pro-0813 | 4096 | 205 | 173.65 | 58.57 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4-Pro-0813 | 4096 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1 | 227 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 227 | 11.62 | 9.55 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 227 | 22.32 | 13.80 | 1.62x |
| DeepSeek-V4-Pro-0813 | 8 | 227 | 41.28 | 20.55 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 227 | 71.39 | 29.38 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 227 | 110.97 | 39.90 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 227 | 149.65 | 50.15 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 227 | 184.07 | 60.97 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1024 | 227 | 185.34 | 61.43 | 3.02x |
| DeepSeek-V4-Pro-0813 | 4096 | 227 | 185.34 | 61.43 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 228 | 5.93 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 228 | 11.63 | 9.56 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 228 | 22.32 | 13.82 | 1.62x |
| DeepSeek-V4-Pro-0813 | 8 | 228 | 41.29 | 20.57 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 228 | 71.45 | 29.43 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 228 | 111.12 | 39.96 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 228 | 149.94 | 50.24 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 228 | 184.56 | 61.09 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1024 | 228 | 185.84 | 61.56 | 3.02x |
| DeepSeek-V4-Pro-0813 | 4096 | 228 | 185.84 | 61.56 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 245 | 11.64 | 9.67 | 1.20x |
| DeepSeek-V4-Pro-0813 | 4 | 245 | 22.40 | 14.06 | 1.59x |
| DeepSeek-V4-Pro-0813 | 8 | 245 | 41.57 | 20.88 | 1.99x |
| DeepSeek-V4-Pro-0813 | 16 | 245 | 72.32 | 30.12 | 2.40x |
| DeepSeek-V4-Pro-0813 | 32 | 245 | 113.43 | 41.03 | 2.76x |
| DeepSeek-V4-Pro-0813 | 64 | 245 | 154.63 | 51.73 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 245 | 192.62 | 63.12 | 3.05x |
| DeepSeek-V4-Pro-0813 | 1024 | 245 | 194.06 | 63.62 | 3.05x |
| DeepSeek-V4-Pro-0813 | 4096 | 245 | 194.06 | 63.62 | 3.05x |
| DeepSeek-V4-Pro-0813 | 1 | 261 | 5.94 | 5.70 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 261 | 11.66 | 9.77 | 1.19x |
| DeepSeek-V4-Pro-0813 | 4 | 261 | 22.46 | 14.28 | 1.57x |
| DeepSeek-V4-Pro-0813 | 8 | 261 | 41.79 | 21.14 | 1.98x |
| DeepSeek-V4-Pro-0813 | 16 | 261 | 73.05 | 30.74 | 2.38x |
| DeepSeek-V4-Pro-0813 | 32 | 261 | 115.38 | 41.96 | 2.75x |
| DeepSeek-V4-Pro-0813 | 64 | 261 | 158.64 | 53.04 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 261 | 199.65 | 64.93 | 3.07x |
| DeepSeek-V4-Pro-0813 | 1024 | 261 | 201.23 | 65.45 | 3.07x |
| DeepSeek-V4-Pro-0813 | 4096 | 261 | 201.23 | 65.45 | 3.07x |
| DeepSeek-V4-Pro-0813 | 1 | 262 | 5.94 | 5.70 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 262 | 11.66 | 9.78 | 1.19x |
| DeepSeek-V4-Pro-0813 | 4 | 262 | 22.47 | 14.29 | 1.57x |
| DeepSeek-V4-Pro-0813 | 8 | 262 | 41.80 | 21.15 | 1.98x |
| DeepSeek-V4-Pro-0813 | 16 | 262 | 73.09 | 30.78 | 2.37x |
| DeepSeek-V4-Pro-0813 | 32 | 262 | 115.50 | 42.02 | 2.75x |
| DeepSeek-V4-Pro-0813 | 64 | 262 | 158.88 | 53.11 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 262 | 200.07 | 65.04 | 3.08x |
| DeepSeek-V4-Pro-0813 | 1024 | 262 | 201.67 | 65.56 | 3.08x |
| DeepSeek-V4-Pro-0813 | 4096 | 262 | 201.67 | 65.56 | 3.08x |
| DeepSeek-V4-Pro-0813 | 1 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 272 | 11.67 | 9.83 | 1.19x |
| DeepSeek-V4-Pro-0813 | 4 | 272 | 22.50 | 14.42 | 1.56x |
| DeepSeek-V4-Pro-0813 | 8 | 272 | 41.93 | 21.30 | 1.97x |
| DeepSeek-V4-Pro-0813 | 16 | 272 | 73.50 | 31.15 | 2.36x |
| DeepSeek-V4-Pro-0813 | 32 | 272 | 116.61 | 42.56 | 2.74x |
| DeepSeek-V4-Pro-0813 | 64 | 272 | 161.21 | 53.89 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 272 | 204.20 | 66.11 | 3.09x |
| DeepSeek-V4-Pro-0813 | 1024 | 272 | 205.88 | 66.65 | 3.09x |
| DeepSeek-V4-Pro-0813 | 4096 | 272 | 205.88 | 66.65 | 3.09x |
| DeepSeek-V4-Pro-0813 | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 280 | 11.68 | 9.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 280 | 22.53 | 14.53 | 1.55x |
| DeepSeek-V4-Pro-0813 | 8 | 280 | 42.03 | 21.42 | 1.96x |
| DeepSeek-V4-Pro-0813 | 16 | 280 | 73.81 | 31.44 | 2.35x |
| DeepSeek-V4-Pro-0813 | 32 | 280 | 117.46 | 42.98 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 280 | 162.98 | 54.48 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 280 | 207.38 | 66.94 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1024 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4-Pro-0813 | 4096 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1 | 283 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 283 | 11.68 | 9.89 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 283 | 22.54 | 14.56 | 1.55x |
| DeepSeek-V4-Pro-0813 | 8 | 283 | 42.06 | 21.46 | 1.96x |
| DeepSeek-V4-Pro-0813 | 16 | 283 | 73.93 | 31.54 | 2.34x |
| DeepSeek-V4-Pro-0813 | 32 | 283 | 117.77 | 43.13 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 283 | 163.62 | 54.70 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 283 | 208.54 | 67.25 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1024 | 283 | 210.31 | 67.81 | 3.10x |
| DeepSeek-V4-Pro-0813 | 4096 | 283 | 210.31 | 67.81 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 293 | 11.69 | 9.94 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 293 | 22.57 | 14.69 | 1.54x |
| DeepSeek-V4-Pro-0813 | 8 | 293 | 42.17 | 21.60 | 1.95x |
| DeepSeek-V4-Pro-0813 | 16 | 293 | 74.29 | 31.89 | 2.33x |
| DeepSeek-V4-Pro-0813 | 32 | 293 | 118.75 | 43.62 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 293 | 165.70 | 55.42 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 293 | 212.31 | 68.26 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1024 | 293 | 214.17 | 68.82 | 3.11x |
| DeepSeek-V4-Pro-0813 | 4096 | 293 | 214.17 | 68.82 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 335 | 11.71 | 10.13 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 335 | 22.67 | 15.17 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 335 | 42.57 | 22.14 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 335 | 75.58 | 33.24 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 335 | 122.34 | 45.48 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 335 | 173.40 | 58.23 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 335 | 226.52 | 72.22 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 336 | 11.71 | 10.14 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 336 | 22.68 | 15.18 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 336 | 42.57 | 22.15 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 336 | 75.61 | 33.27 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 336 | 122.42 | 45.52 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 336 | 173.56 | 58.30 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 336 | 226.83 | 72.31 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 357 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 357 | 11.73 | 10.22 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 357 | 22.72 | 15.40 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 357 | 42.74 | 22.39 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 357 | 76.15 | 33.88 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 357 | 123.93 | 46.35 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 357 | 176.86 | 59.62 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 357 | 233.07 | 74.16 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 357 | 235.42 | 74.78 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 357 | 235.42 | 74.78 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 358 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 358 | 11.73 | 10.22 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 358 | 22.72 | 15.41 | 1.47x |
| DeepSeek-V4-Pro-0813 | 8 | 358 | 42.74 | 22.40 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 358 | 76.17 | 33.90 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 358 | 124.00 | 46.38 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 358 | 177.01 | 59.68 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 358 | 233.36 | 74.24 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 358 | 235.71 | 74.87 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 358 | 235.71 | 74.87 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 363 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 363 | 11.73 | 10.24 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 363 | 22.73 | 15.47 | 1.47x |
| DeepSeek-V4-Pro-0813 | 8 | 363 | 42.78 | 22.46 | 1.90x |
| DeepSeek-V4-Pro-0813 | 16 | 363 | 76.29 | 34.04 | 2.24x |
| DeepSeek-V4-Pro-0813 | 32 | 363 | 124.33 | 46.57 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 363 | 177.75 | 59.99 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 363 | 234.76 | 74.67 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 363 | 237.15 | 75.30 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 363 | 237.15 | 75.30 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 369 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 369 | 11.73 | 10.26 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 369 | 22.74 | 15.53 | 1.46x |
| DeepSeek-V4-Pro-0813 | 8 | 369 | 42.82 | 22.53 | 1.90x |
| DeepSeek-V4-Pro-0813 | 16 | 369 | 76.43 | 34.20 | 2.23x |
| DeepSeek-V4-Pro-0813 | 32 | 369 | 124.73 | 46.79 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 369 | 178.61 | 60.35 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 369 | 236.41 | 75.18 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 369 | 238.84 | 75.81 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 369 | 238.84 | 75.81 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 370 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 370 | 11.73 | 10.26 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 370 | 22.75 | 15.54 | 1.46x |
| DeepSeek-V4-Pro-0813 | 8 | 370 | 42.83 | 22.54 | 1.90x |
| DeepSeek-V4-Pro-0813 | 16 | 370 | 76.46 | 34.23 | 2.23x |
| DeepSeek-V4-Pro-0813 | 32 | 370 | 124.79 | 46.83 | 2.66x |
| DeepSeek-V4-Pro-0813 | 64 | 370 | 178.75 | 60.41 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 370 | 236.69 | 75.26 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 370 | 239.12 | 75.90 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 370 | 239.12 | 75.90 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 371 | 11.73 | 10.27 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 371 | 22.75 | 15.55 | 1.46x |
| DeepSeek-V4-Pro-0813 | 8 | 371 | 42.84 | 22.55 | 1.90x |
| DeepSeek-V4-Pro-0813 | 16 | 371 | 76.48 | 34.25 | 2.23x |
| DeepSeek-V4-Pro-0813 | 32 | 371 | 124.86 | 46.87 | 2.66x |
| DeepSeek-V4-Pro-0813 | 64 | 371 | 178.89 | 60.47 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 371 | 236.96 | 75.34 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 371 | 239.40 | 75.98 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 371 | 239.40 | 75.98 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 391 | 11.74 | 10.33 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 391 | 22.78 | 15.74 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 391 | 42.96 | 22.76 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 391 | 76.91 | 34.76 | 2.21x |
| DeepSeek-V4-Pro-0813 | 32 | 391 | 126.08 | 47.58 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 391 | 181.60 | 61.65 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 391 | 242.17 | 76.98 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 391 | 244.74 | 77.64 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 391 | 244.74 | 77.64 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 448 | 11.76 | 10.50 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 448 | 22.87 | 16.25 | 1.41x |
| DeepSeek-V4-Pro-0813 | 8 | 448 | 43.27 | 23.34 | 1.85x |
| DeepSeek-V4-Pro-0813 | 16 | 448 | 77.94 | 36.03 | 2.16x |
| DeepSeek-V4-Pro-0813 | 32 | 448 | 129.03 | 49.47 | 2.61x |
| DeepSeek-V4-Pro-0813 | 64 | 448 | 188.21 | 64.80 | 2.90x |
| DeepSeek-V4-Pro-0813 | 256 | 448 | 255.15 | 81.21 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 448 | 258.06 | 81.95 | 3.15x |
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
| gpu | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 1.2% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 10.4% |

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
| DeepSeek-V4-Pro-0813 | 1 | 95 | 18.22% | 53.67 | 3.10 |
| DeepSeek-V4-Pro-0813 | 2 | 95 | 18.22% | 53.67 | 3.10 |
| DeepSeek-V4-Pro-0813 | 4 | 95 | 18.22% | 53.67 | 3.10 |
| DeepSeek-V4-Pro-0813 | 8 | 2 | 1.08% | 3.80 | 3.10 |
| DeepSeek-V4-Pro-0813 | 16 | 2 | 1.08% | 3.80 | 3.10 |
| DeepSeek-V4-Pro-0813 | 32 | 2 | 1.08% | 3.80 | 3.10 |
| DeepSeek-V4-Pro-0813 | 64 | 2 | 1.08% | 3.80 | 3.10 |

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
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 153.7 | 31,961.5 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 153.7 | 31,961.5 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 153.7 | 31,961.5 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 153.7 | 31,961.5 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 153.7 | 31,961.5 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 153.7 | 31,961.5 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 153.7 | 31,961.5 |
| DeepSeek-V4-Pro-0813 | 256 | 1.92% | 42.6 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 124.9 | 31,979.5 |
| DeepSeek-V4-Pro-0813 | 1024 | 7.46% | 88.1 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 31.3 | 32,038.2 |
| DeepSeek-V4-Pro-0813 | 4096 | 26.66% | 246.0 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 7.8 | 32,052.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 22 |
| gpu | infeasible | 1 |
| gpu | link_latency | 310 |
| gpu | weight_read | 907 |
| rom | compute | 880 |
| rom | infeasible | 1668 |
| rom | kv_read | 40 |
| rom | link_latency | 990 |
| rom | weight_read | 382 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 1 |
| rom | CAPACITY | 1668 |

## Mechanical consistency audit

**FAIL** over 110,801 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x193', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x230', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x248', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x265', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x266', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x276', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x368', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x193', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x230', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x248', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x265', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x266', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x276', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x368', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x193', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x230', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x248', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x265', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x266', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x276', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x368', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x193', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x230', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x248', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x265', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x266', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x276', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x368', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x5', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x193', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x230', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x248', 'DeepSeek-V4-Pro-0813', 1)

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

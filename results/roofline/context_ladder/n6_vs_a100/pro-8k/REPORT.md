# Area-constrained roofline: n6_vs_a100-pro-8k

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Pro-0813 at 8,192 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 14x (ROM-N6-native-SRAMKV-array-hw-pipeline-x187, 187 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 5 devices. On the GPU side the correction reaches 31x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 56 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Pro-0813 takes 4 x 46,225 mm2 (184,900 mm2, wafer, KV in HBM) at 2,048 tok/s per user and 11 tok/s per 1,000 mm2, holding 27,932 sessions, against 224 copies of one unified HBM die at the same silicon: 10.5x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 369,800 mm2 of ROM silicon at 2,260 tok/s per user against 370,048 mm2 of a100_sxm_80gb-x448-hybrid at 190 tok/s: **11.9x**, ROM binding on `layer_fixed_latency` and the GPU on `weight_read`. It holds 55,865 resident sessions against the GPU cluster's 353,706. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on DeepSeek-V4-Pro-0813 at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 1,962 us of link latency per token; but the model has 61 layers, so at most 61 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 1,902 us. The iso-area per-user ratio at that point falls from 12.0x to 11.9x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 4.69x to it.** At 178,485 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 41.49 tok/s and the same silicon running hybrid delivers 195 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`) to 17.96x (DeepSeek-V4-Pro-0813, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Pro-0813 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 63 to 12,957 tok/s, and its rate with every slot occupied from 12,778 to 12,957. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 202 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,823 us over NVLink, capping per-user decode at 548 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 291.6 us and cap it at 3,429 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 10 of 10 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 10 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 29 of 3494 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 57.3x of aggregate throughput (DeepSeek-V4-Pro-0813). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 16.31x, on DeepSeek-V4-Pro-0813 at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4-Pro-0813 at 8,192 tokens

**Recommended: `ROM-N6-native-HBMKV-wafer-hybrid-x4`** -- 4 x 46,225 mm2 wafers, 184,900 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **2,048.3 tok/s per user** (0.49 ms/token), binding on `layer_fixed_latency`
- **11.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 30,724 tok/s aggregate with every slot full, over 27,932 resident sessions (fill limited by `pipeline_slots`)
- 12,627 W at 0.068 W/mm2, 5,846.4 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 224 copies of one unified HBM die -- `a100_sxm_80gb-x224-hybrid`, 185,024 mm2, area ratio 0.9993 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 184,900 | 185,024 | 0.9993 |
| user tok/s | 2,048.3 | 194.6 | 10.52x |
| aggregate tok/s | 30,724 | 5,449 | 3.31x |
| resident sessions | 27,932 | 171,819 | -- |
| J/token | 5.8464 | 170.3619 | 29.1x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 27,932 sessions against one that holds 171,819 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x56-hybrid` at 46,256 mm2 and 198.1 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 2,227.5 | 9.6 | 34,915 | 11.51x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | 8.2 | 41,899 | 11.76x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-hybrid-x187` | 152,405 | 714.1 | 4.7 | 1 | 3.73x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,048.3 | 11.1 | 27,932 | 10.52x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,048.3 | 11.1 | -- | 11.1 | ACCEPT |
| `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 2,227.5 | 9.6 | 3.9 | 11.1 | stop |
| `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | 8.2 | 2.3 | 11.1 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-wafer-hybrid-x4` **<-- recommended** | 184,900 | 4 | 2,048.3 | 30,724 | 11.1 | 27,932 | `layer_fixed_latency` | 12,627 | 5,846.4 | `a100_sxm_80gb-x224-hybrid` | 10.52x |
| `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 5 | 2,227.5 | 40,096 | 9.6 | 34,915 | `layer_fixed_latency` | 19,664 | 8,440.7 | `a100_sxm_80gb-x280-hybrid` | 11.51x |
| `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 6 | 2,262.2 | 49,768 | 8.2 | 41,899 | `layer_fixed_latency` | 26,707 | 11,327.9 | `a100_sxm_80gb-x336-hybrid` | 11.76x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 252 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x224` | 182,560 | 1,360.4 | 7.5 | 1 |
| array | 252 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 322,740 | 1,630.8 | 5.1 | 321,551 |
| array | 252 | smallest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x187` | 152,405 | 714.1 | 4.7 | 1 |
| wafer | 54 | densest | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,048.3 | 11.1 | 27,932 |
| wafer | 54 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | 8.2 | 41,899 |
| wafer | 54 | smallest | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,048.3 | 11.1 | 27,932 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 322,740 | 1,630.8 | 161,452 | 321,551 | 39,519 | 22,002.2 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 191.0 | 307,423 | 299,782.4 | 0.999 | 8.54x | 13.6x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | 49,768 | 41,899 | 26,707 | 11,327.9 | `layer_fixed_latency` | `a100_sxm_80gb-x336-hybrid` | 192.4 | 262,763 | 256,388.9 | 0.999 | 11.76x | 22.6x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x351` | 286,065 | 1,607.3 | 141,441 | 285,011 | 34,249 | 19,328.3 | `layer_fixed_latency` | `a100_sxm_80gb-x346-hybrid` | 190.3 | 270,883 | 266,731.3 | 1.001 | 8.45x | 13.8x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | -- | 41,899 | -- | 11,327.9 | -- | -- | -- | -- | -- | 1.031 | 1.41x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 322,740 | 1,630.8 | 161,452 | 321,551 | 39,519 | 11,012.5 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 191.0 | 307,423 | 151,982.2 | 0.999 | 8.54x | 13.8x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | 49,768 | 41,899 | 26,707 | 5,675.3 | `layer_fixed_latency` | `a100_sxm_80gb-x336-hybrid` | 192.4 | 262,763 | 130,285.5 | 0.999 | 11.76x | 23.0x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x351` | 286,065 | 1,607.3 | 141,441 | 285,011 | 34,249 | 9,675.5 | `layer_fixed_latency` | `a100_sxm_80gb-x346-hybrid` | 190.3 | 270,883 | 135,456.7 | 1.001 | 8.45x | 14.0x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | -- | 41,899 | -- | 5,675.3 | -- | -- | -- | -- | -- | 1.031 | 1.41x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 322,740 | 1,630.8 | 161,452 | 321,551 | 39,519 | 5,517.6 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 191.0 | 307,423 | 78,082.2 | 0.999 | 8.54x | 14.2x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | 49,768 | 41,899 | 26,707 | 2,849.0 | `layer_fixed_latency` | `a100_sxm_80gb-x336-hybrid` | 192.4 | 262,763 | 67,233.8 | 0.999 | 11.76x | 23.6x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x351` | 286,065 | 1,607.3 | 141,441 | 285,011 | 34,249 | 4,849.2 | `layer_fixed_latency` | `a100_sxm_80gb-x346-hybrid` | 190.3 | 270,883 | 69,819.4 | 1.001 | 8.45x | 14.4x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | -- | 41,899 | -- | 2,849.0 | -- | -- | -- | -- | -- | 1.031 | 1.41x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 322,740 | 1,630.8 | 161,452 | 321,551 | 39,519 | 2,770.2 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 191.0 | 307,423 | 41,132.1 | 0.999 | 8.54x | 14.8x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | 49,768 | 41,899 | 26,707 | 1,435.9 | `layer_fixed_latency` | `a100_sxm_80gb-x336-hybrid` | 192.4 | 262,763 | 35,708.0 | 0.999 | 11.76x | 24.9x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x351` | 286,065 | 1,607.3 | 141,441 | 285,011 | 34,249 | 2,436.0 | `layer_fixed_latency` | `a100_sxm_80gb-x346-hybrid` | 190.3 | 270,883 | 37,000.8 | 1.001 | 8.45x | 15.2x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | -- | 41,899 | -- | 1,435.9 | -- | -- | -- | -- | -- | 1.031 | 1.41x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 322,740 | 1,630.8 | 161,452 | 321,551 | 39,519 | 1,396.5 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 191.0 | 307,423 | 22,657.1 | 0.999 | 8.54x | 16.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | 49,768 | 41,899 | 26,707 | 729.3 | `layer_fixed_latency` | `a100_sxm_80gb-x336-hybrid` | 192.4 | 262,763 | 19,945.0 | 0.999 | 11.76x | 27.3x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x351` | 286,065 | 1,607.3 | 141,441 | 285,011 | 34,249 | 1,229.4 | `layer_fixed_latency` | `a100_sxm_80gb-x346-hybrid` | 190.3 | 270,883 | 20,591.4 | 1.001 | 8.45x | 16.7x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 2,262.2 | -- | 41,899 | -- | 729.3 | -- | -- | -- | -- | -- | 1.031 | 1.41x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 322,740 | 1,630.8 | 161,452 | 321,551 | 39,519 | 709.6 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 191.0 | 307,423 | 13,419.6 | 0.999 | 8.54x | 18.9x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,249.4 | 96,724 | 83,798 | 53,779 | 739.3 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 189.4 | 535,594 | 20,194.2 | 0.999 | 11.88x | 27.3x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396-romfill` | 322,740 | 1,630.8 | 161,452 | 321,551 | 39,519 | 366.2 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 179.1 | 307,423 | 8,443.4 | 0.999 | 9.11x | 23.1x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,215.6 | 190,543 | 83,798 | 55,914 | 386.5 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 189.4 | 535,594 | 12,188.1 | 0.999 | 11.70x | 31.5x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,298.4 | 332,402 | 321,551 | 43,913 | 132.1 | `layer_fixed_latency` | `a100_sxm_80gb-x391-hybrid` | 100.8 | 307,423 | 4,046.4 | 0.999 | 12.88x | 30.6x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,712.5 | 438,392 | 83,798 | 60,338 | 137.6 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 131.0 | 535,594 | 5,159.3 | 0.999 | 13.07x | 37.5x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 521.2 | 533,756 | 321,551 | 46,377 | 86.9 | `compute` | `a100_sxm_80gb-x391-hybrid` | 38.5 | 307,423 | 2,739.9 | 0.999 | 13.55x | 31.5x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 949.3 | 972,074 | 83,798 | 80,918 | 83.2 | `weight_read` | `a100_sxm_80gb-x672-hybrid` | 56.3 | 535,594 | 3,165.2 | 0.999 | 16.86x | 38.0x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 147.6 | 604,458 | 321,551 | 46,026 | 76.1 | `compute` | `a100_sxm_80gb-x391-hybrid` | 14.5 | 307,423 | 1,750.5 | 0.999 | 10.14x | 23.0x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 365.4 | 1,496,632 | 83,798 | 87,693 | 58.6 | `compute` | `a100_sxm_80gb-x672-hybrid` | 20.3 | 535,594 | 2,423.0 | 0.999 | 17.96x | 41.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-32 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | wafer | HBM | 27,932 |
| 64 | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | wafer | HBM | 34,915 |
| 256 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | wafer | HBM | 41,899 |
| 1024 | `ROM-N6-native-HBMKV-wafer-pipeline-x8` | 369,800 | wafer | HBM | 55,865 |
| 4096 | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | wafer | HBM | 83,798 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro-0813 | HBM | rom | 202, 208, 227, 244, 248, 297, 340, 342, 359, 360, 396 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 202, 208, 227, 244, 248, 297, 340, 351, 365, 366, 396 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 187, 191, 219, 221, 224, 227, 230, 276, 340, 368 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 187, 191, 219, 221, 224, 227, 230, 276, 340, 368 |

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
| DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 1 | 16 on `rom_wafer_express` | 5.51 | one_shot | 333.62 | 67.19 | 101.97 | 43.31 | 2,048.3 |
| DeepSeek-V4-Pro-0813 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 64 | 4 on `rom_wafer_express` | 5.51 | one_shot | 341.28 | 24.77 | 435.06 | 28.49 | 1,288.3 |
| DeepSeek-V4-Pro-0813 | `a100_sxm_80gb-x224-hybrid` | 1 | 8 | 5.51 | measured_floor | 603.70 | 1,759.34 | 3,006.49 | 713.20 | 194.6 |
| DeepSeek-V4-Pro-0813 | `a100_sxm_80gb-x224-hybrid` | 64 | 8 | 5.51 | measured_floor | 603.70 | 2,006.84 | 4,239.67 | 752.79 | 153.3 |

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

- **0 of 3,494 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 32%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 40 | 0 | 63.1% | 80.2% | 0.389 | 72% |
| gpu | wafer (>=40,000 mm2) | 1,240 | 0 | 55.4% | 79.8% | 0.387 | 84% |
| rom | wafer (>=40,000 mm2) | 2,214 | 0 | 18.9% | 31.6% | 0.158 | 97% |

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
| DeepSeek-V4-Pro-0813 | 1 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5` | 8.440673 | 19,663.8 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x280-hybrid` | 213.130681 | 68,748.1 | weight_read | 25.25x |
| DeepSeek-V4-Pro-0813 | 2 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5` | 4.231716 | 19,663.8 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x280-hybrid` | 108.656394 | 68,748.1 | weight_read | 25.68x |
| DeepSeek-V4-Pro-0813 | 4 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5` | 2.127237 | 19,663.8 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x280-hybrid` | 56.419250 | 68,748.1 | weight_read | 26.52x |
| DeepSeek-V4-Pro-0813 | 8 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5` | 1.074998 | 19,663.8 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x280-hybrid` | 30.300679 | 68,748.1 | weight_read | 28.19x |
| DeepSeek-V4-Pro-0813 | 16 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5` | 0.548878 | 19,663.8 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x280-hybrid` | 17.241393 | 68,748.1 | weight_read | 31.41x |
| DeepSeek-V4-Pro-0813 | 32 | 277,350 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6` | 0.382976 | 27,745.5 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x336-hybrid` | 12.063570 | 82,299.8 | weight_read | 31.50x |
| DeepSeek-V4-Pro-0813 | 64 | 369,800 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 0.273357 | 37,371.9 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x448-hybrid` | 9.309763 | 109,857.7 | weight_read | 34.06x |
| DeepSeek-V4-Pro-0813 | 256 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.137635 | 60,338.0 | layer_fixed_latency | `DSV4-Pro/a100_sxm_80gb-x672-hybrid` | 5.159281 | 173,042.5 | weight_read | 37.49x |
| DeepSeek-V4-Pro-0813 | 1024 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.083243 | 80,918.0 | weight_read | `DSV4-Pro/a100_sxm_80gb-x672-hybrid` | 3.165241 | 182,465.8 | weight_read | 38.02x |
| DeepSeek-V4-Pro-0813 | 4096 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.058593 | 87,692.6 | compute | `DSV4-Pro/a100_sxm_80gb-x672-hybrid` | 2.423010 | 201,858.8 | weight_read | 41.35x |

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
| DeepSeek-V4-Pro-0813 | 8,192 | 1,600 B | 892.7 GB | 4.46 | 0.057 GB | 0.089 GB | 693.3 |

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
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 2,782.1 | wafer-pipeline | 2,048.3 | wafer-hybrid | 1.36x | 1,179.6 | pipeline | 194.6 | hybrid | 6.06x | 2.36x | 10.52x | 4.46x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 2,789.6 | wafer-pipeline | 2,262.2 | wafer-hybrid | 1.23x | 1,227.4 | pipeline | 192.4 | hybrid | 6.38x | 2.27x | 11.76x | 5.17x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 2,790.4 | wafer-pipeline | 2,260.0 | wafer-hybrid | 1.23x | 1,252.8 | pipeline | 190.1 | hybrid | 6.59x | 2.23x | 11.89x | 5.34x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 2,791.1 | wafer-pipeline | 2,249.4 | wafer-hybrid | 1.24x | 1,279.3 | pipeline | 189.4 | hybrid | 6.76x | 2.18x | 11.88x | 5.44x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 4.46x to 5.44x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 2,262.2 | 49,768.1 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x336-hybrid | 277,536 | 1.00x | hybrid | 1,819.88 | 192.4 | 8,078.9 | weight_read | 11.76x | 3.57x | 54.53x | 11.76x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x187 | 152,405 | 714.1 | 714.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x185-hybrid | 152,810 | 1.00x | hybrid | 1,742.04 | 191.4 | 4,592.5 | weight_read | 3.73x | 0.09x | 17.21x | 3.73x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 2,262.2 | 49,768.1 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x336-hybrid | 277,536 | 1.00x | hybrid | 1,819.88 | 192.4 | 8,078.9 | weight_read | 11.76x | 3.57x | 54.53x | 11.76x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x202 | 164,630 | 638.7 | 4,471.0 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x199-hybrid | 164,374 | 1.00x | hybrid | 1,746.37 | 194.6 | 4,864.6 | weight_read | 3.28x | 0.54x | 15.40x | 3.28x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 2,262.2 | 49,768.1 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x336-hybrid | 277,536 | 1.00x | hybrid | 1,819.88 | 192.4 | 8,078.9 | weight_read | 11.76x | 3.57x | 54.53x | 11.76x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x202 | 164,630 | 638.7 | 4,471.0 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x199-hybrid | 164,374 | 1.00x | hybrid | 1,746.37 | 194.6 | 4,864.6 | weight_read | 3.28x | 0.54x | 15.40x | 3.28x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 2,262.2 | 49,768.1 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x336-hybrid | 277,536 | 1.00x | hybrid | 1,819.88 | 192.4 | 8,078.9 | weight_read | 11.76x | 3.57x | 54.53x | 11.76x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x202 | 164,630 | 594.4 | 4,755.0 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x199-hybrid | 164,374 | 1.00x | hybrid | 1,746.37 | 194.6 | 4,864.6 | weight_read | 3.05x | 0.58x | 14.33x | 3.05x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 2,262.2 | 49,768.1 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x336-hybrid | 277,536 | 1.00x | hybrid | 1,819.88 | 192.4 | 8,078.9 | weight_read | 11.76x | 3.57x | 54.53x | 11.76x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x202 | 164,630 | 469.0 | 7,504.8 | compute | DSV4-Pro/a100_sxm_80gb-x199-hybrid | 164,374 | 1.00x | hybrid | 1,746.37 | 194.6 | 4,864.6 | weight_read | 2.41x | 0.91x | 11.31x | 2.41x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,249.4 | 96,724.3 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,902.05 | 189.4 | 15,906.4 | weight_read | 11.88x | 3.47x | 54.22x | 12.01x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x202 | 164,630 | 311.6 | 9,971.2 | compute | DSV4-Pro/a100_sxm_80gb-x199-hybrid | 164,374 | 1.00x | hybrid | 1,798.34 | 183.7 | 5,879.8 | weight_read | 1.70x | 1.21x | 7.51x | 1.70x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,215.6 | 190,543.2 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,902.05 | 189.4 | 15,906.4 | weight_read | 11.70x | 6.83x | 53.40x | 11.83x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x202 | 164,630 | 179.2 | 11,466.7 | compute | DSV4-Pro/a100_sxm_80gb-x199-hybrid | 164,374 | 1.00x | hybrid | 2,035.93 | 146.8 | 9,392.2 | weight_read | 1.22x | 1.22x | 4.32x | 1.22x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,712.5 | 438,392.2 | layer_fixed_latency | DSV4-Pro/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 2,451.25 | 131.0 | 33,540.0 | weight_read | 13.07x | 13.07x | 41.28x | 13.22x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x202 | 164,630 | 50.1 | 12,823.7 | compute | DSV4-Pro/a100_sxm_80gb-x199-hybrid | 164,374 | 1.00x | hybrid | 3,168.82 | 67.5 | 17,285.9 | weight_read | 0.74x | 0.74x | 1.32x | 0.74x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 949.3 | 972,073.7 | weight_read | DSV4-Pro/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 4,610.35 | 56.3 | 57,646.7 | weight_read | 16.86x | 16.86x | 26.67x | 17.06x |
| DeepSeek-V4-Pro-0813 | 1024 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x202 | 164,630 | 12.6 | 12,941.0 | compute | DSV4-Pro/a100_sxm_80gb-x199-hybrid | 164,374 | 1.00x | hybrid | 8,863.02 | 24.7 | 25,280.2 | weight_read | 0.51x | 0.51x | 0.70x | 0.51x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 365.4 | 1,496,631.7 | compute | DSV4-Pro/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 5,838.90 | 20.3 | 83,309.1 | weight_read | 17.96x | 17.96x | 22.66x | 18.35x |
| DeepSeek-V4-Pro-0813 | 4096 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x202 | 164,630 | 3.2 | 12,957.4 | compute | DSV4-Pro/a100_sxm_80gb-x199-hybrid | 164,374 | 1.00x | hybrid | 31,639.83 | 11.0 | 44,942.3 | weight_read | 0.29x | 0.29x | 0.49x | 0.29x |

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
| DeepSeek-V4-Pro-0813 | 18 | 14,868 | 41.6 | 138.3 | 167.9 | hybrid | 1,651.23 | 27.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 41.5 | 138.2 | 198.1 | hybrid | 1,668.53 | 33.1% | weight_read |
| DeepSeek-V4-Pro-0813 | 93 | 76,818 | 41.5 | 131.5 | 193.9 | hybrid | 1,690.15 | 32.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 103 | 85,078 | 41.5 | 129.9 | 196.1 | hybrid | 1,694.48 | 33.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 41.5 | 128.4 | 196.9 | hybrid | 1,698.80 | 33.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 41.5 | 112.0 | 195.8 | hybrid | 1,729.07 | 33.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 185 | 152,810 | 41.5 | 109.7 | 191.4 | hybrid | 1,742.04 | 33.3% | weight_read |
| DeepSeek-V4-Pro-0813 | 188 | 155,288 | 41.5 | 109.4 | 193.1 | hybrid | 1,742.04 | 33.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 199 | 164,374 | 41.5 | 108.0 | 194.6 | hybrid | 1,746.37 | 34.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 205 | 169,330 | 41.5 | 107.3 | 193.4 | hybrid | 1,750.69 | 33.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 216 | 178,416 | 41.5 | 106.0 | 194.8 | hybrid | 1,755.02 | 34.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 218 | 180,068 | 41.5 | 105.7 | 191.8 | hybrid | 1,759.34 | 33.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 221 | 182,546 | 41.5 | 105.4 | 193.2 | hybrid | 1,759.34 | 34.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 41.5 | 105.1 | 194.6 | hybrid | 1,759.34 | 34.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 227 | 187,502 | 41.5 | 104.7 | 192.2 | hybrid | 1,763.67 | 33.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 241 | 199,066 | 41.5 | 103.1 | 191.1 | hybrid | 1,772.31 | 33.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 245 | 202,370 | 41.5 | 102.7 | 192.9 | hybrid | 1,772.31 | 34.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 272 | 224,672 | 41.5 | 99.8 | 193.6 | hybrid | 1,785.29 | 34.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 41.5 | 98.9 | 193.5 | hybrid | 1,789.61 | 34.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 293 | 242,018 | 41.5 | 97.6 | 192.1 | hybrid | 1,798.26 | 34.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 335 | 276,710 | 41.5 | 83.0 | 192.0 | hybrid | 1,819.88 | 35.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 41.5 | 82.9 | 192.4 | hybrid | 1,819.88 | 35.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 337 | 278,362 | 41.5 | 82.8 | 190.1 | hybrid | 1,824.21 | 34.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 346 | 285,796 | 41.5 | 82.2 | 190.3 | hybrid | 1,828.53 | 34.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 354 | 292,404 | 41.5 | 81.6 | 190.2 | hybrid | 1,832.86 | 34.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 355 | 293,230 | 41.5 | 81.6 | 190.4 | hybrid | 1,832.86 | 34.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 360 | 297,360 | 41.5 | 81.2 | 191.9 | hybrid | 1,832.86 | 35.2% | weight_read |
| DeepSeek-V4-Pro-0813 | 361 | 298,186 | 41.5 | 81.1 | 189.8 | hybrid | 1,837.18 | 34.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 363 | 299,838 | 41.5 | 81.0 | 190.3 | hybrid | 1,837.18 | 35.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 391 | 322,966 | 41.5 | 79.1 | 191.0 | hybrid | 1,850.15 | 35.3% | weight_read |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 41.5 | 75.5 | 190.1 | hybrid | 1,880.42 | 35.8% | weight_read |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 41.5 | 64.1 | 189.4 | hybrid | 1,902.05 | 36.0% | weight_read |

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
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x224 | DeepSeek-V4-Pro-0813 | 224 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 6.93 us | 14,435.6 tok/s | 144,355.6 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.40 us; 30 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.52 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x191 | DeepSeek-V4-Pro-0813 | 191 | tensor | rom_package_ucie | rom_board_serdes | 244 | 511.25 us | 195.6 tok/s | 1,956.0 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 122 x all_reduce span 96 on rom_board_serdes (traversals 19.8) = 507.94 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x221 | DeepSeek-V4-Pro-0813 | 221 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 16.36 us | 6,113.0 tok/s | 61,130.2 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 13.05 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x224 | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4 | DeepSeek-V4-Pro-0813 | 4 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.59 us | 13,181.2 tok/s | 131,812.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x187 | DeepSeek-V4-Pro-0813 | 187 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | rom_wafer_serdes | 244 | 291.64 us | 342.9 tok/s | 3,428.9 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 56.79 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x219 | DeepSeek-V4-Pro-0813 | 219 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | DeepSeek-V4-Pro-0813 | 4 | hybrid | on_wafer | rom_wafer_serdes | 125 | 235.48 us | 424.7 tok/s | 4,246.6 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.63 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x366 | DeepSeek-V4-Pro-0813 | 366 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 6.93 us | 14,435.6 tok/s | 144,355.6 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.40 us; 30 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.52 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x208 | DeepSeek-V4-Pro-0813 | 208 | tensor | rom_package_ucie | rom_board_serdes | 244 | 567.34 us | 176.3 tok/s | 1,762.6 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 122 x all_reduce span 104 on rom_board_serdes (traversals 22.0) = 564.04 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x351 | DeepSeek-V4-Pro-0813 | 351 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 16.36 us | 6,113.0 tok/s | 61,130.2 tok/s | 122 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.31 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 13.05 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x365 | DeepSeek-V4-Pro-0813 | 365 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x6 | DeepSeek-V4-Pro-0813 | 6 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.59 us | 13,181.2 tok/s | 131,812.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x202 | DeepSeek-V4-Pro-0813 | 202 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | rom_wafer_serdes | 244 | 291.64 us | 342.9 tok/s | 3,428.9 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 56.79 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x244 | DeepSeek-V4-Pro-0813 | 244 | hybrid | nvlink3 | infiniband_hdr | 152 | 703.41 us | 142.2 tok/s | 1,421.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer | rom_wafer_serdes | 126 | 235.70 us | 424.3 tok/s | 4,242.7 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.85 us |
| DSV4-Pro/a100_sxm_80gb-x18-pipeline | DeepSeek-V4-Pro-0813 | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 43.42 us | 2,302.9 tok/s | 23,028.9 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 38.22 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 5.21 us |
| DSV4-Pro/a100_sxm_80gb-x18-tensor | DeepSeek-V4-Pro-0813 | 18 | tensor | nvlink3 | infiniband_hdr | 244 | 1,260.54 us | 79.3 tok/s | 793.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 635.24 us |
| DSV4-Pro/a100_sxm_80gb-x18-hybrid | DeepSeek-V4-Pro-0813 | 18 | hybrid | nvlink3 | infiniband_hdr | 124 | 630.51 us | 158.6 tok/s | 1,586.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 5.21 us |
| DSV4-Pro/a100_sxm_80gb-x18-expert | DeepSeek-V4-Pro-0813 | 18 | expert | nvlink3 | infiniband_hdr | 244 | 888.63 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 617.65 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 270.98 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,300.52 us | 76.9 tok/s | 768.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 675.22 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 640.92 us | 156.0 tok/s | 1,560.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink3 | infiniband_hdr | 244 | 867.34 us | 115.3 tok/s | 1,152.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 612.19 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 255.16 us |
| DSV4-Pro/a100_sxm_80gb-x93-pipeline | DeepSeek-V4-Pro-0813 | 93 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x93-tensor | DeepSeek-V4-Pro-0813 | 93 | tensor | nvlink3 | infiniband_hdr | 244 | 1,313.01 us | 76.2 tok/s | 761.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 687.71 us |
| DSV4-Pro/a100_sxm_80gb-x93-hybrid | DeepSeek-V4-Pro-0813 | 93 | hybrid | nvlink3 | infiniband_hdr | 133 | 653.94 us | 152.9 tok/s | 1,529.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| DSV4-Pro/a100_sxm_80gb-x93-expert | DeepSeek-V4-Pro-0813 | 93 | expert | nvlink3 | infiniband_hdr | 244 | 863.56 us | 115.8 tok/s | 1,158.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.39 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 252.17 us |
| DSV4-Pro/a100_sxm_80gb-x103-pipeline | DeepSeek-V4-Pro-0813 | 103 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x103-tensor | DeepSeek-V4-Pro-0813 | 103 | tensor | nvlink3 | infiniband_hdr | 244 | 1,314.36 us | 76.1 tok/s | 760.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 689.05 us |
| DSV4-Pro/a100_sxm_80gb-x103-hybrid | DeepSeek-V4-Pro-0813 | 103 | hybrid | nvlink3 | infiniband_hdr | 134 | 656.54 us | 152.3 tok/s | 1,523.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.24 us |
| DSV4-Pro/a100_sxm_80gb-x103-expert | DeepSeek-V4-Pro-0813 | 103 | expert | nvlink3 | infiniband_hdr | 244 | 863.01 us | 115.9 tok/s | 1,158.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.28 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.74 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x112-expert | DeepSeek-V4-Pro-0813 | 112 | expert | nvlink3 | infiniband_hdr | 244 | 862.50 us | 115.9 tok/s | 1,159.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.09 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.41 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.51 us | 75.7 tok/s | 757.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 695.20 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 677.37 us | 147.6 tok/s | 1,476.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| DSV4-Pro/a100_sxm_80gb-x168-expert | DeepSeek-V4-Pro-0813 | 168 | expert | nvlink3 | infiniband_hdr | 244 | 860.89 us | 116.2 tok/s | 1,161.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.73 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 250.16 us |
| DSV4-Pro/a100_sxm_80gb-x185-pipeline | DeepSeek-V4-Pro-0813 | 185 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x185-tensor | DeepSeek-V4-Pro-0813 | 185 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x185-hybrid | DeepSeek-V4-Pro-0813 | 185 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x185-expert | DeepSeek-V4-Pro-0813 | 185 | expert | nvlink3 | infiniband_hdr | 244 | 860.59 us | 116.2 tok/s | 1,162.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.67 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.93 us |
| DSV4-Pro/a100_sxm_80gb-x188-pipeline | DeepSeek-V4-Pro-0813 | 188 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x188-tensor | DeepSeek-V4-Pro-0813 | 188 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x188-hybrid | DeepSeek-V4-Pro-0813 | 188 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x188-expert | DeepSeek-V4-Pro-0813 | 188 | expert | nvlink3 | infiniband_hdr | 244 | 860.56 us | 116.2 tok/s | 1,162.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.67 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.89 us |
| DSV4-Pro/a100_sxm_80gb-x199-pipeline | DeepSeek-V4-Pro-0813 | 199 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x199-tensor | DeepSeek-V4-Pro-0813 | 199 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.11 us | 75.6 tok/s | 756.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 696.80 us |
| DSV4-Pro/a100_sxm_80gb-x199-hybrid | DeepSeek-V4-Pro-0813 | 199 | hybrid | nvlink3 | infiniband_hdr | 146 | 687.79 us | 145.4 tok/s | 1,453.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.48 us |
| DSV4-Pro/a100_sxm_80gb-x199-expert | DeepSeek-V4-Pro-0813 | 199 | expert | nvlink3 | infiniband_hdr | 244 | 860.41 us | 116.2 tok/s | 1,162.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.64 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.77 us |
| DSV4-Pro/a100_sxm_80gb-x205-pipeline | DeepSeek-V4-Pro-0813 | 205 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x205-tensor | DeepSeek-V4-Pro-0813 | 205 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x205-hybrid | DeepSeek-V4-Pro-0813 | 205 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x205-expert | DeepSeek-V4-Pro-0813 | 205 | expert | nvlink3 | infiniband_hdr | 244 | 860.32 us | 116.2 tok/s | 1,162.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.61 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.71 us |
| DSV4-Pro/a100_sxm_80gb-x216-pipeline | DeepSeek-V4-Pro-0813 | 216 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x216-tensor | DeepSeek-V4-Pro-0813 | 216 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.73 us | 75.6 tok/s | 756.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 697.43 us |
| DSV4-Pro/a100_sxm_80gb-x216-hybrid | DeepSeek-V4-Pro-0813 | 216 | hybrid | nvlink3 | infiniband_hdr | 148 | 692.99 us | 144.3 tok/s | 1,443.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 67.69 us |
| DSV4-Pro/a100_sxm_80gb-x216-expert | DeepSeek-V4-Pro-0813 | 216 | expert | nvlink3 | infiniband_hdr | 244 | 860.17 us | 116.3 tok/s | 1,162.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.57 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.60 us |
| DSV4-Pro/a100_sxm_80gb-x218-pipeline | DeepSeek-V4-Pro-0813 | 218 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x218-tensor | DeepSeek-V4-Pro-0813 | 218 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x218-hybrid | DeepSeek-V4-Pro-0813 | 218 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x218-expert | DeepSeek-V4-Pro-0813 | 218 | expert | nvlink3 | infiniband_hdr | 244 | 860.15 us | 116.3 tok/s | 1,162.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.57 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.59 us |
| DSV4-Pro/a100_sxm_80gb-x221-pipeline | DeepSeek-V4-Pro-0813 | 221 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x221-tensor | DeepSeek-V4-Pro-0813 | 221 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x221-hybrid | DeepSeek-V4-Pro-0813 | 221 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x221-expert | DeepSeek-V4-Pro-0813 | 221 | expert | nvlink3 | infiniband_hdr | 244 | 860.13 us | 116.3 tok/s | 1,162.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.57 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.56 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x224-expert | DeepSeek-V4-Pro-0813 | 224 | expert | nvlink3 | infiniband_hdr | 244 | 860.08 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.53 us |
| DSV4-Pro/a100_sxm_80gb-x227-pipeline | DeepSeek-V4-Pro-0813 | 227 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x227-tensor | DeepSeek-V4-Pro-0813 | 227 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.27 us | 75.6 tok/s | 755.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 697.96 us |
| DSV4-Pro/a100_sxm_80gb-x227-hybrid | DeepSeek-V4-Pro-0813 | 227 | hybrid | nvlink3 | infiniband_hdr | 150 | 698.20 us | 143.2 tok/s | 1,432.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 72.90 us |
| DSV4-Pro/a100_sxm_80gb-x227-expert | DeepSeek-V4-Pro-0813 | 227 | expert | nvlink3 | infiniband_hdr | 244 | 860.06 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.51 us |
| DSV4-Pro/a100_sxm_80gb-x241-pipeline | DeepSeek-V4-Pro-0813 | 241 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x241-tensor | DeepSeek-V4-Pro-0813 | 241 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.73 us | 75.5 tok/s | 755.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 698.43 us |
| DSV4-Pro/a100_sxm_80gb-x241-hybrid | DeepSeek-V4-Pro-0813 | 241 | hybrid | nvlink3 | infiniband_hdr | 152 | 703.41 us | 142.2 tok/s | 1,421.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.10 us |
| DSV4-Pro/a100_sxm_80gb-x241-expert | DeepSeek-V4-Pro-0813 | 241 | expert | nvlink3 | infiniband_hdr | 244 | 859.91 us | 116.3 tok/s | 1,162.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.51 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.40 us |
| DSV4-Pro/a100_sxm_80gb-x245-pipeline | DeepSeek-V4-Pro-0813 | 245 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x245-tensor | DeepSeek-V4-Pro-0813 | 245 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.73 us | 75.5 tok/s | 755.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 698.43 us |
| DSV4-Pro/a100_sxm_80gb-x245-hybrid | DeepSeek-V4-Pro-0813 | 245 | hybrid | nvlink3 | infiniband_hdr | 152 | 703.41 us | 142.2 tok/s | 1,421.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.10 us |
| DSV4-Pro/a100_sxm_80gb-x245-expert | DeepSeek-V4-Pro-0813 | 245 | expert | nvlink3 | infiniband_hdr | 244 | 859.88 us | 116.3 tok/s | 1,162.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.51 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.37 us |
| DSV4-Pro/a100_sxm_80gb-x272-pipeline | DeepSeek-V4-Pro-0813 | 272 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x272-tensor | DeepSeek-V4-Pro-0813 | 272 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.33 us | 75.5 tok/s | 755.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 699.03 us |
| DSV4-Pro/a100_sxm_80gb-x272-hybrid | DeepSeek-V4-Pro-0813 | 272 | hybrid | nvlink3 | infiniband_hdr | 155 | 711.22 us | 140.6 tok/s | 1,406.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.91 us |
| DSV4-Pro/a100_sxm_80gb-x272-expert | DeepSeek-V4-Pro-0813 | 272 | expert | nvlink3 | infiniband_hdr | 244 | 859.65 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.45 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.20 us |
| DSV4-Pro/a100_sxm_80gb-x280-pipeline | DeepSeek-V4-Pro-0813 | 280 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x280-tensor | DeepSeek-V4-Pro-0813 | 280 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.51 us | 75.5 tok/s | 755.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 699.20 us |
| DSV4-Pro/a100_sxm_80gb-x280-hybrid | DeepSeek-V4-Pro-0813 | 280 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/a100_sxm_80gb-x280-expert | DeepSeek-V4-Pro-0813 | 280 | expert | nvlink3 | infiniband_hdr | 244 | 859.60 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.44 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.16 us |
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
| DSV4-Pro/a100_sxm_80gb-x337-pipeline | DeepSeek-V4-Pro-0813 | 337 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x337-tensor | DeepSeek-V4-Pro-0813 | 337 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.94 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 43 on infiniband_hdr (traversals 4.0) = 1,195.64 us |
| DSV4-Pro/a100_sxm_80gb-x337-hybrid | DeepSeek-V4-Pro-0813 | 337 | hybrid | nvlink3 | infiniband_hdr | 164 | 734.65 us | 136.1 tok/s | 1,361.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 109.34 us |
| DSV4-Pro/a100_sxm_80gb-x337-expert | DeepSeek-V4-Pro-0813 | 337 | expert | nvlink3 | infiniband_hdr | 244 | 859.27 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.36 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.91 us |
| DSV4-Pro/a100_sxm_80gb-x346-pipeline | DeepSeek-V4-Pro-0813 | 346 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x346-tensor | DeepSeek-V4-Pro-0813 | 346 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.05 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 44 on infiniband_hdr (traversals 4.0) = 1,195.75 us |
| DSV4-Pro/a100_sxm_80gb-x346-hybrid | DeepSeek-V4-Pro-0813 | 346 | hybrid | nvlink3 | infiniband_hdr | 165 | 737.25 us | 135.6 tok/s | 1,356.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 43 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 111.95 us |
| DSV4-Pro/a100_sxm_80gb-x346-expert | DeepSeek-V4-Pro-0813 | 346 | expert | nvlink3 | infiniband_hdr | 244 | 859.23 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.36 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.87 us |
| DSV4-Pro/a100_sxm_80gb-x354-pipeline | DeepSeek-V4-Pro-0813 | 354 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x354-tensor | DeepSeek-V4-Pro-0813 | 354 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.16 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,195.86 us |
| DSV4-Pro/a100_sxm_80gb-x354-hybrid | DeepSeek-V4-Pro-0813 | 354 | hybrid | nvlink3 | infiniband_hdr | 166 | 739.86 us | 135.2 tok/s | 1,351.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 114.55 us |
| DSV4-Pro/a100_sxm_80gb-x354-expert | DeepSeek-V4-Pro-0813 | 354 | expert | nvlink3 | infiniband_hdr | 244 | 859.19 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.35 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.85 us |
| DSV4-Pro/a100_sxm_80gb-x355-pipeline | DeepSeek-V4-Pro-0813 | 355 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x355-tensor | DeepSeek-V4-Pro-0813 | 355 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.16 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,195.86 us |
| DSV4-Pro/a100_sxm_80gb-x355-hybrid | DeepSeek-V4-Pro-0813 | 355 | hybrid | nvlink3 | infiniband_hdr | 166 | 739.86 us | 135.2 tok/s | 1,351.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 114.55 us |
| DSV4-Pro/a100_sxm_80gb-x355-expert | DeepSeek-V4-Pro-0813 | 355 | expert | nvlink3 | infiniband_hdr | 244 | 859.19 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.35 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.84 us |
| DSV4-Pro/a100_sxm_80gb-x360-pipeline | DeepSeek-V4-Pro-0813 | 360 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x360-tensor | DeepSeek-V4-Pro-0813 | 360 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.16 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,195.86 us |
| DSV4-Pro/a100_sxm_80gb-x360-hybrid | DeepSeek-V4-Pro-0813 | 360 | hybrid | nvlink3 | infiniband_hdr | 166 | 739.86 us | 135.2 tok/s | 1,351.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 114.55 us |
| DSV4-Pro/a100_sxm_80gb-x360-expert | DeepSeek-V4-Pro-0813 | 360 | expert | nvlink3 | infiniband_hdr | 244 | 859.17 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.34 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.83 us |
| DSV4-Pro/a100_sxm_80gb-x361-pipeline | DeepSeek-V4-Pro-0813 | 361 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x361-tensor | DeepSeek-V4-Pro-0813 | 361 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.26 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 1,195.96 us |
| DSV4-Pro/a100_sxm_80gb-x361-hybrid | DeepSeek-V4-Pro-0813 | 361 | hybrid | nvlink3 | infiniband_hdr | 167 | 742.46 us | 134.7 tok/s | 1,346.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 45 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 117.15 us |
| DSV4-Pro/a100_sxm_80gb-x361-expert | DeepSeek-V4-Pro-0813 | 361 | expert | nvlink3 | infiniband_hdr | 244 | 859.16 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.34 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.82 us |
| DSV4-Pro/a100_sxm_80gb-x363-pipeline | DeepSeek-V4-Pro-0813 | 363 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x363-tensor | DeepSeek-V4-Pro-0813 | 363 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.26 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 1,195.96 us |
| DSV4-Pro/a100_sxm_80gb-x363-hybrid | DeepSeek-V4-Pro-0813 | 363 | hybrid | nvlink3 | infiniband_hdr | 167 | 742.46 us | 134.7 tok/s | 1,346.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 45 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 117.15 us |
| DSV4-Pro/a100_sxm_80gb-x363-expert | DeepSeek-V4-Pro-0813 | 363 | expert | nvlink3 | infiniband_hdr | 244 | 859.16 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.34 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.82 us |
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
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 2,227.5 | 0.010 | 1,597.2 (277,100) | 2,227.5 (231,125) | 1.39x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 2,227.5 | 0.010 | 1,597.2 (277,100) | 2,227.5 (231,125) | 1.39x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 2,227.5 | 0.010 | 1,597.2 (277,100) | 2,227.5 (231,125) | 1.39x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 2,227.5 | 0.010 | 1,597.2 (277,100) | 2,227.5 (231,125) | 1.39x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 2,227.5 | 0.010 | 1,597.2 (277,100) | 2,227.5 (231,125) | 1.39x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 2,218.7 | 0.008 | 1,597.2 (277,100) | 2,218.7 (277,350) | 1.39x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 2,136.2 | 0.006 | 1,591.0 (277,100) | 2,136.2 (369,800) | 1.34x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,712.5 | 0.003 | 1,298.4 (322,740) | 1,712.5 (554,700) | 1.32x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 949.3 | 0.002 | 521.2 (322,740) | 949.3 (554,700) | 1.82x | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 365.4 | 0.001 | 147.6 (322,740) | 365.4 (554,700) | 2.48x | compute |

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
| DeepSeek-V4-Pro-0813 | 1 | sram | 474,483.9 | 25,059.4 | 25,059.4 | 18.93x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 474,483.9 | 25,059.4 | 25,059.4 | 18.93x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 474,483.9 | 25,059.4 | 25,059.4 | 18.93x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 474,483.9 | 25,059.4 | 25,059.4 | 18.93x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 474,483.9 | 25,059.4 | 25,059.4 | 18.93x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 474,483.9 | 25,059.4 | 42,149.9 | 18.93x | 1.68x | weight_read | weight_read | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | sram | 474,483.9 | 25,059.4 | 68,367.4 | 18.93x | 2.73x | weight_read | weight_read | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 256 | sram | 474,483.9 | 26,003.3 | 158,068.1 | 18.25x | 6.08x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 972,073.7 | 26,113.2 | 269,072.0 | 37.23x | 10.30x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 1,496,631.7 | 26,113.2 | 425,907.8 | 57.31x | 16.31x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 754,937.3 | 29,413.6 | 29,413.6 | 25.67x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 754,937.3 | 29,413.6 | 29,413.6 | 25.67x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 754,937.3 | 29,413.6 | 29,413.6 | 25.67x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 754,937.3 | 29,413.6 | 29,413.6 | 25.67x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 754,937.3 | 29,413.6 | 29,413.6 | 25.67x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 754,937.3 | 29,413.6 | 43,553.3 | 25.67x | 1.48x | compute | weight_read | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | rom | 754,937.3 | 29,413.6 | 69,860.5 | 25.67x | 2.38x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 754,937.3 | 30,736.1 | 155,751.4 | 24.56x | 5.07x | compute | weight_read | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 848,760.2 | 31,106.0 | 290,504.7 | 27.29x | 9.34x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 1,040,138.7 | 31,106.0 | 430,040.2 | 33.44x | 13.82x | compute | weight_read | kv_read |

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
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 474,483.9 | 0.855 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 754,937.3 | 1.361 | compute | 1.59x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 474,483.9 | 0.855 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 754,937.3 | 1.361 | compute | 1.59x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 474,483.9 | 0.855 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 754,937.3 | 1.361 | compute | 1.59x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 474,483.9 | 0.855 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 754,937.3 | 1.361 | compute | 1.59x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 474,483.9 | 0.855 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 754,937.3 | 1.361 | compute | 1.59x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 474,483.9 | 0.855 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 754,937.3 | 1.361 | compute | 1.59x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.99 | 42,149.9 | 0.456 | layer_fixed_latency | 0.09x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.19 | 1.99 | 43,553.3 | 0.471 | layer_fixed_latency | 0.09x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 474,483.9 | 0.855 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 754,937.3 | 1.361 | compute | 1.59x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 25,059.4 | 0.271 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 1.00 | 29,413.6 | 0.318 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.54 | 68,367.4 | 0.740 | layer_fixed_latency | 0.14x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.19 | 1.99 | 69,860.5 | 0.756 | weight_read | 0.15x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 474,483.9 | 0.855 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 754,937.3 | 1.361 | compute | 1.59x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 2.25 | 26,003.3 | 0.281 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 2.25 | 30,736.1 | 0.332 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.49 | 158,068.1 | 1.710 | weight_read | 0.33x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.19 | 3.49 | 155,751.4 | 1.685 | layer_fixed_latency | 0.33x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 972,073.7 | 1.752 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 848,760.2 | 1.530 | compute | 0.87x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 8.98 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 8.98 | 31,106.0 | 0.336 | weight_read | 0.03x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 5.09 | 269,072.0 | 2.910 | weight_read | 0.28x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.19 | 5.09 | 290,504.7 | 3.142 | weight_read | 0.30x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,496,631.7 | 2.698 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 1,040,138.7 | 1.875 | compute | 0.69x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 35.93 | 26,113.2 | 0.282 | weight_read | 0.02x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.19 | 35.93 | 31,106.0 | 0.336 | weight_read | 0.02x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 7.62 | 425,907.8 | 4.607 | weight_read | 0.28x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.19 | 7.62 | 430,040.2 | 4.652 | kv_read | 0.29x |

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
| DeepSeek-V4-Pro-0813 | 1 | 94 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 94 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 114 | 2.25 | 1.010 | 1.128 | 1.12x |
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
| DeepSeek-V4-Pro-0813 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Pro-0813 | 2 | 18 | 8.89 | 5.04 | 1.76x |
| DeepSeek-V4-Pro-0813 | 4 | 18 | 13.29 | 6.50 | 2.04x |
| DeepSeek-V4-Pro-0813 | 8 | 18 | 16.66 | 8.05 | 2.07x |
| DeepSeek-V4-Pro-0813 | 16 | 18 | 17.86 | 9.57 | 1.87x |
| DeepSeek-V4-Pro-0813 | 32 | 18 | 18.00 | 10.92 | 1.65x |
| DeepSeek-V4-Pro-0813 | 64 | 18 | 18.00 | 11.95 | 1.51x |
| DeepSeek-V4-Pro-0813 | 256 | 18 | 18.00 | 12.83 | 1.40x |
| DeepSeek-V4-Pro-0813 | 1024 | 18 | 18.00 | 12.86 | 1.40x |
| DeepSeek-V4-Pro-0813 | 4096 | 18 | 18.00 | 12.86 | 1.40x |
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
| DeepSeek-V4-Pro-0813 | 1 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 93 | 11.23 | 7.92 | 1.42x |
| DeepSeek-V4-Pro-0813 | 4 | 93 | 20.82 | 11.20 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 93 | 36.11 | 16.00 | 2.26x |
| DeepSeek-V4-Pro-0813 | 16 | 93 | 56.11 | 21.60 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 93 | 75.02 | 27.64 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 93 | 86.34 | 33.16 | 2.60x |
| DeepSeek-V4-Pro-0813 | 256 | 93 | 91.42 | 38.56 | 2.37x |
| DeepSeek-V4-Pro-0813 | 1024 | 93 | 91.54 | 38.78 | 2.36x |
| DeepSeek-V4-Pro-0813 | 4096 | 93 | 91.54 | 38.78 | 2.36x |
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
| DeepSeek-V4-Pro-0813 | 1 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 185 | 11.56 | 9.20 | 1.26x |
| DeepSeek-V4-Pro-0813 | 4 | 185 | 22.07 | 13.14 | 1.68x |
| DeepSeek-V4-Pro-0813 | 8 | 185 | 40.40 | 19.63 | 2.06x |
| DeepSeek-V4-Pro-0813 | 16 | 185 | 68.63 | 27.52 | 2.49x |
| DeepSeek-V4-Pro-0813 | 32 | 185 | 103.84 | 36.90 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 185 | 135.66 | 45.96 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 185 | 161.05 | 55.36 | 2.91x |
| DeepSeek-V4-Pro-0813 | 1024 | 185 | 161.92 | 55.76 | 2.90x |
| DeepSeek-V4-Pro-0813 | 4096 | 185 | 161.92 | 55.76 | 2.90x |
| DeepSeek-V4-Pro-0813 | 1 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 188 | 11.57 | 9.23 | 1.25x |
| DeepSeek-V4-Pro-0813 | 4 | 188 | 22.10 | 13.19 | 1.67x |
| DeepSeek-V4-Pro-0813 | 8 | 188 | 40.47 | 19.71 | 2.05x |
| DeepSeek-V4-Pro-0813 | 16 | 188 | 68.86 | 27.66 | 2.49x |
| DeepSeek-V4-Pro-0813 | 32 | 188 | 104.43 | 37.13 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 188 | 136.79 | 46.29 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 188 | 162.85 | 55.79 | 2.92x |
| DeepSeek-V4-Pro-0813 | 1024 | 188 | 163.75 | 56.20 | 2.91x |
| DeepSeek-V4-Pro-0813 | 4096 | 188 | 163.75 | 56.20 | 2.91x |
| DeepSeek-V4-Pro-0813 | 1 | 199 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 199 | 11.59 | 9.33 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 199 | 22.17 | 13.37 | 1.66x |
| DeepSeek-V4-Pro-0813 | 8 | 199 | 40.73 | 19.97 | 2.04x |
| DeepSeek-V4-Pro-0813 | 16 | 199 | 69.66 | 28.17 | 2.47x |
| DeepSeek-V4-Pro-0813 | 32 | 199 | 106.47 | 37.95 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 199 | 140.74 | 47.44 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 199 | 169.24 | 57.32 | 2.95x |
| DeepSeek-V4-Pro-0813 | 1024 | 199 | 170.25 | 57.75 | 2.95x |
| DeepSeek-V4-Pro-0813 | 4096 | 199 | 170.25 | 57.75 | 2.95x |
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
| DeepSeek-V4-Pro-0813 | 1 | 216 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 216 | 11.61 | 9.47 | 1.23x |
| DeepSeek-V4-Pro-0813 | 4 | 216 | 22.26 | 13.64 | 1.63x |
| DeepSeek-V4-Pro-0813 | 8 | 216 | 41.08 | 20.34 | 2.02x |
| DeepSeek-V4-Pro-0813 | 16 | 216 | 70.76 | 28.92 | 2.45x |
| DeepSeek-V4-Pro-0813 | 32 | 216 | 109.31 | 39.16 | 2.79x |
| DeepSeek-V4-Pro-0813 | 64 | 216 | 146.33 | 49.12 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 216 | 178.48 | 59.58 | 3.00x |
| DeepSeek-V4-Pro-0813 | 1024 | 216 | 179.64 | 60.03 | 2.99x |
| DeepSeek-V4-Pro-0813 | 4096 | 216 | 179.64 | 60.03 | 2.99x |
| DeepSeek-V4-Pro-0813 | 1 | 218 | 5.93 | 5.64 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 218 | 11.61 | 9.48 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 218 | 22.28 | 13.67 | 1.63x |
| DeepSeek-V4-Pro-0813 | 8 | 218 | 41.11 | 20.38 | 2.02x |
| DeepSeek-V4-Pro-0813 | 16 | 218 | 70.88 | 29.00 | 2.44x |
| DeepSeek-V4-Pro-0813 | 32 | 218 | 109.62 | 39.29 | 2.79x |
| DeepSeek-V4-Pro-0813 | 64 | 218 | 146.95 | 49.31 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 218 | 179.51 | 59.83 | 3.00x |
| DeepSeek-V4-Pro-0813 | 1024 | 218 | 180.70 | 60.29 | 3.00x |
| DeepSeek-V4-Pro-0813 | 4096 | 218 | 180.70 | 60.29 | 3.00x |
| DeepSeek-V4-Pro-0813 | 1 | 221 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 221 | 11.62 | 9.51 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 221 | 22.29 | 13.72 | 1.63x |
| DeepSeek-V4-Pro-0813 | 8 | 221 | 41.17 | 20.44 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 221 | 71.05 | 29.13 | 2.44x |
| DeepSeek-V4-Pro-0813 | 32 | 221 | 110.08 | 39.50 | 2.79x |
| DeepSeek-V4-Pro-0813 | 64 | 221 | 147.87 | 49.60 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 221 | 181.05 | 60.21 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1024 | 221 | 182.27 | 60.67 | 3.00x |
| DeepSeek-V4-Pro-0813 | 4096 | 221 | 182.27 | 60.67 | 3.00x |
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
| DeepSeek-V4-Pro-0813 | 1 | 241 | 5.94 | 5.67 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 241 | 11.64 | 9.65 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 241 | 22.38 | 14.01 | 1.60x |
| DeepSeek-V4-Pro-0813 | 8 | 241 | 41.50 | 20.81 | 1.99x |
| DeepSeek-V4-Pro-0813 | 16 | 241 | 72.12 | 29.96 | 2.41x |
| DeepSeek-V4-Pro-0813 | 32 | 241 | 112.91 | 40.78 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 241 | 153.57 | 51.39 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 241 | 190.78 | 62.66 | 3.04x |
| DeepSeek-V4-Pro-0813 | 1024 | 241 | 192.18 | 63.15 | 3.04x |
| DeepSeek-V4-Pro-0813 | 4096 | 241 | 192.18 | 63.15 | 3.04x |
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
| DeepSeek-V4-Pro-0813 | 1 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 337 | 11.72 | 10.14 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 337 | 22.68 | 15.19 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 337 | 42.58 | 22.16 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 337 | 75.64 | 33.30 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 337 | 122.49 | 45.56 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 337 | 173.73 | 58.36 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 337 | 227.14 | 72.40 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 337 | 229.35 | 73.00 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 337 | 229.35 | 73.00 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 346 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 346 | 11.72 | 10.18 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 346 | 22.70 | 15.29 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 346 | 42.65 | 22.27 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 346 | 75.88 | 33.57 | 2.26x |
| DeepSeek-V4-Pro-0813 | 32 | 346 | 123.16 | 45.92 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 346 | 175.17 | 58.93 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 346 | 229.87 | 73.20 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 346 | 232.14 | 73.81 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 346 | 232.14 | 73.81 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 354 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 354 | 11.72 | 10.21 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 354 | 22.71 | 15.37 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 354 | 42.71 | 22.36 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 354 | 76.08 | 33.79 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 354 | 123.72 | 46.23 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 354 | 176.41 | 59.43 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 354 | 232.21 | 73.90 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 354 | 234.54 | 74.52 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 354 | 234.54 | 74.52 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 355 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 355 | 11.73 | 10.21 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 355 | 22.72 | 15.38 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 355 | 42.72 | 22.37 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 355 | 76.10 | 33.82 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 355 | 123.79 | 46.27 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 355 | 176.56 | 59.49 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 355 | 232.50 | 73.98 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 355 | 234.83 | 74.61 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 355 | 234.83 | 74.61 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 360 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 360 | 11.73 | 10.23 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 360 | 22.73 | 15.43 | 1.47x |
| DeepSeek-V4-Pro-0813 | 8 | 360 | 42.76 | 22.43 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 360 | 76.22 | 33.96 | 2.24x |
| DeepSeek-V4-Pro-0813 | 32 | 360 | 124.13 | 46.46 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 360 | 177.31 | 59.80 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 360 | 233.92 | 74.41 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 360 | 236.29 | 75.04 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 360 | 236.29 | 75.04 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 361 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 361 | 11.73 | 10.23 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 361 | 22.73 | 15.44 | 1.47x |
| DeepSeek-V4-Pro-0813 | 8 | 361 | 42.77 | 22.44 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 361 | 76.25 | 33.99 | 2.24x |
| DeepSeek-V4-Pro-0813 | 32 | 361 | 124.20 | 46.50 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 361 | 177.45 | 59.86 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 361 | 234.20 | 74.50 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 361 | 236.58 | 75.13 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 361 | 236.58 | 75.13 | 3.15x |
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
| gpu | DeepSeek-V4-Pro-0813 | 1 | 603.70 | 12.0% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 348.79 | 78.9% |

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
| DeepSeek-V4-Pro-0813 | 1 | 94 | 36.17% | 203.71 | 5.99 |
| DeepSeek-V4-Pro-0813 | 2 | 94 | 36.17% | 203.71 | 5.99 |
| DeepSeek-V4-Pro-0813 | 4 | 2 | 0.29% | 1.97 | 5.99 |
| DeepSeek-V4-Pro-0813 | 8 | 2 | 0.29% | 1.97 | 5.99 |
| DeepSeek-V4-Pro-0813 | 16 | 2 | 0.29% | 1.97 | 5.99 |
| DeepSeek-V4-Pro-0813 | 32 | 2 | 0.29% | 1.97 | 5.99 |
| DeepSeek-V4-Pro-0813 | 64 | 2 | 0.29% | 1.97 | 5.99 |
| DeepSeek-V4-Pro-0813 | 256 | 2 | 0.65% | 4.42 | 5.99 |

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
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 63.3 | 12,777.9 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 63.3 | 12,777.9 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 63.3 | 12,777.9 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 63.3 | 12,777.9 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 63.3 | 12,777.9 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 63.3 | 12,777.9 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 63.3 | 12,777.9 |
| DeepSeek-V4-Pro-0813 | 256 | 1.98% | 43.1 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 50.1 | 12,823.7 |
| DeepSeek-V4-Pro-0813 | 1024 | 7.67% | 89.9 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 12.6 | 12,941.0 |
| DeepSeek-V4-Pro-0813 | 4096 | 27.34% | 251.5 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 3.2 | 12,957.4 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 1 |
| gpu | link_latency | 483 |
| gpu | weight_read | 796 |
| rom | compute | 677 |
| rom | infeasible | 1566 |
| rom | kv_read | 29 |
| rom | layer_fixed_latency | 359 |
| rom | link_latency | 890 |
| rom | weight_read | 259 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 1566 |

## Mechanical consistency audit

**FAIL** over 109,115 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x187', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x191', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x219', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x221', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x224', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x230', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x276', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x368', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x187', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x191', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x219', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x221', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x224', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x230', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x276', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x368', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x187', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x191', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x219', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x221', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x224', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x230', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x276', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x368', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x187', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x191', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x219', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x221', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x224', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x230', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x276', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x368', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x187', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x191', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x219', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x221', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x224', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)

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
